"""由 BLAST+ / LAST / Diamond 和 vendored JCVI(随包 JCVI) 支撑的真实 pairwise MCscan workflow(成对 MCscan 工作流)"""

# region import
from __future__ import annotations

import shutil
from pathlib import Path

from jcvi.compara.synteny import mcscan as jcvi_mcscan
from jcvi.compara.synteny import scan as jcvi_scan
from jcvi.compara.synteny import simple as jcvi_simple
from jcvi.formats.bed import merge as jcvi_bed_merge
from jcvi_genomelens.manifest_models import EngineRunManifest
from jcvi_genomelens.runtime.command_runner import CommandAudit, run_command, run_python_step
from jcvi_genomelens.workflows import catalog_ortholog

# endregion


def _required_tool(path: Path | None, label: str) -> str:
    """返回必需 executable(可执行文件) 路径，或抛出清晰错误"""

    if path is None or not path.is_file():
        raise FileNotFoundError(f"{label} executable not found: {path}")
    return str(path)


def _assert_ok(command: CommandAudit) -> None:
    """类命令步骤失败时中止 workflow(工作流)"""

    if command.returncode != 0:
        message = command.stderr or command.stdout or f"{command.name} failed"
        raise RuntimeError(message)


def _write_default_layout(path: Path, query_label: str, subject_label: str) -> Path:
    """写出适用于 JCVI `graphics.synteny` 的双轨 layout(布局)"""

    path.write_text(
        "\n".join(
            [
                "# x, y, rotation, ha, va, color, ratio, label",
                f"0.50, 0.70, 0, center, top, #2f6f73, 1, {query_label}",
                f"0.50, 0.30, 0, center, bottom, #b85c38, 1, {subject_label}",
                "e, 0, 1, #c8c8c8",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _normalize_simple_name(generated_simple: Path, expected_simple: Path) -> Path:
    """JCVI 写出 `<prefix>.simple`；GenomeLens 发布 `<prefix>.anchors.simple`"""

    if generated_simple.is_file() and generated_simple != expected_simple:
        # JCVI 默认文件名与 GenomeLens 对外发布名不同，这里补一份稳定别名。
        shutil.copy2(generated_simple, expected_simple)
    if expected_simple.is_file():
        return expected_simple
    return generated_simple


def _ensure_nonempty(path: Path, label: str) -> None:
    """确认产物文件非空，否则抛出明确错误"""

    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"{label} output is empty: {path}")


def _run_makeblastdb(
    manifest: EngineRunManifest,
    root: Path,
    db_prefix: Path,
) -> CommandAudit:
    """为 subject CDS 建立 BLAST nucleotide 数据库"""

    # BLAST 路径在 manifest 阶段允许为空，这里到真正执行时再转成硬错误。
    makeblastdb = _required_tool(manifest.toolchain.makeblastdb, "makeblastdb")
    cmd = run_command(
        [
            makeblastdb,
            "-in",
            str(manifest.subject.cds),
            "-dbtype",
            "nucl",
            "-out",
            str(db_prefix),
        ],
        cwd=root,
    )
    _assert_ok(cmd)
    return cmd


def _run_blastn(
    manifest: EngineRunManifest,
    root: Path,
    db_prefix: Path,
    blast_table: Path,
) -> CommandAudit:
    """用 blastn 比对 query CDS 到 subject 数据库"""

    blastn = _required_tool(manifest.toolchain.blastn, "blastn")
    threads = max(1, manifest.options.threads)
    cmd = run_command(
        [
            blastn,
            "-query",
            str(manifest.query.cds),
            "-db",
            str(db_prefix),
            "-out",
            str(blast_table),
            "-outfmt",
            "6",
            "-num_threads",
            str(threads),
        ],
        cwd=root,
        timeout=3600,
    )
    _assert_ok(cmd)
    _ensure_nonempty(blast_table, "BLAST")
    return cmd


def _run_scan(
    manifest: EngineRunManifest,
    root: Path,
    blast_table: Path,
    anchors: Path,
) -> CommandAudit:
    """从 blast 表生成 anchors"""

    # min_size/dist 在 engine 边界再做一次下限保护，避免异常配置穿透到 JCVI。
    min_size = max(1, manifest.options.min_block_size)
    dist = max(1, manifest.options.dist)
    cmd = run_python_step(
        "jcvi.compara.synteny.scan",
        jcvi_scan,
        [
            str(blast_table),
            str(anchors),
            f"--qbed={manifest.query.bed}",
            f"--sbed={manifest.subject.bed}",
            f"--min_size={min_size}",
            f"--dist={dist}",
            "--no_strip_names",
        ],
        cwd=root,
    )
    _assert_ok(cmd)
    _ensure_nonempty(anchors, "JCVI anchors")
    return cmd


def _run_simple(
    manifest: EngineRunManifest,
    root: Path,
    anchors: Path,
    generated_simple: Path,
    simple: Path,
) -> CommandAudit:
    """从 anchors 生成 simple 文件"""

    cmd = run_python_step(
        "jcvi.compara.synteny.simple",
        jcvi_simple,
        [
            str(anchors),
            f"--qbed={manifest.query.bed}",
            f"--sbed={manifest.subject.bed}",
        ],
        cwd=root,
    )
    _assert_ok(cmd)
    actual_simple = _normalize_simple_name(generated_simple, simple)
    _ensure_nonempty(actual_simple, "JCVI simple")
    return cmd


def _run_mcscan(
    manifest: EngineRunManifest,
    root: Path,
    anchors: Path,
    blocks: Path,
) -> CommandAudit:
    """从 anchors 生成 blocks"""

    iter_count = max(1, manifest.options.iter)
    cmd = run_python_step(
        "jcvi.compara.synteny.mcscan",
        jcvi_mcscan,
        [str(manifest.query.bed), str(anchors), f"--iter={iter_count}", "-o", str(blocks)],
        cwd=root,
    )
    _assert_ok(cmd)
    _ensure_nonempty(blocks, "JCVI blocks")
    return cmd


def _run_merge_bed(
    manifest: EngineRunManifest,
    root: Path,
    merged_bed: Path,
) -> CommandAudit:
    """合并 query 与 subject bed 为 all.bed"""

    cmd = run_python_step(
        "jcvi.formats.bed.merge",
        jcvi_bed_merge,
        [str(manifest.query.bed), str(manifest.subject.bed), "-o", str(merged_bed)],
        cwd=root,
    )
    _assert_ok(cmd)
    _ensure_nonempty(merged_bed, "Merged BED")
    return cmd


def _run_with_blast(manifest: EngineRunManifest, root: Path) -> tuple[list[CommandAudit], dict[str, object]]:
    """使用 BLAST+ 运行 pairwise MCscan 并返回标准 artifacts"""

    prefix = f"{manifest.query.name}.{manifest.subject.name}"
    db_prefix = root / f"{manifest.subject.name}.blastdb"
    blast_table = root / f"{prefix}.blast.tsv"
    anchors = root / f"{prefix}.anchors"
    generated_simple = root / f"{prefix}.simple"
    simple = root / f"{prefix}.anchors.simple"
    blocks = root / f"{prefix}.blocks"
    merged_bed = root / "all.bed"

    # BLAST 路径走原生命令，scan/simple/mcscan 走进程内 JCVI 函数，最后统一归档。
    commands: list[CommandAudit] = []
    commands.append(_run_makeblastdb(manifest, root, db_prefix))
    commands.append(_run_blastn(manifest, root, db_prefix, blast_table))
    commands.append(_run_scan(manifest, root, blast_table, anchors))
    commands.append(_run_simple(manifest, root, anchors, generated_simple, simple))
    commands.append(_run_mcscan(manifest, root, anchors, blocks))
    commands.append(_run_merge_bed(manifest, root, merged_bed))

    return commands, {
        "blast_table": str(blast_table),
        "anchors": str(anchors),
        "simple": str(simple),
        "blocks": str(blocks),
        "merged_bed": str(merged_bed),
    }


def _run_with_catalog(manifest: EngineRunManifest, root: Path) -> tuple[list[CommandAudit], dict[str, object]]:
    """使用 JCVI catalog.ortholog（支持 LAST / Diamond）运行 pairwise 并返回标准 artifacts"""

    # LAST / Diamond 直接复用 catalog workflow，避免在这里重复维护同源搜索细节。
    catalog_commands, catalog_artifacts = catalog_ortholog.run(manifest, root)
    prefix = f"{manifest.query.name}.{manifest.subject.name}"
    merged_bed = root / "all.bed"
    merge_cmd = run_python_step(
        "jcvi.formats.bed.merge",
        jcvi_bed_merge,
        [str(manifest.query.bed), str(manifest.subject.bed), "-o", str(merged_bed)],
        cwd=root,
    )
    _assert_ok(merge_cmd)
    if not merged_bed.is_file() or merged_bed.stat().st_size == 0:
        raise RuntimeError(f"Merged BED output is empty: {merged_bed}")

    blast_table = catalog_artifacts.get("blast_table") or str(root / f"{prefix}.last")
    anchors = catalog_artifacts.get("anchors") or str(root / f"{prefix}.anchors")
    blocks = catalog_artifacts.get("blocks") or str(root / f"{prefix}.1x1.blocks")
    simple = catalog_artifacts.get("lifted_anchors") or anchors

    return catalog_commands + [merge_cmd], {
        "blast_table": str(blast_table),
        "anchors": str(anchors),
        "simple": str(simple),
        "blocks": str(blocks),
        "merged_bed": str(merged_bed),
    }


def run(manifest: EngineRunManifest, outdir: str | Path) -> tuple[list[CommandAudit], dict[str, object]]:
    """运行真实 pairwise MCscan 步骤

    workflow(工作流)：
    - align_soft == "blast" 时：makeblastdb -> blastn -> scan -> simple -> mcscan。
    - align_soft 为 "last" 或 "diamond_blastp" 时：复用 JCVI catalog.ortholog。
    """

    root = Path(outdir).expanduser().resolve(strict=False)
    root.mkdir(parents=True, exist_ok=True)
    # graphics.synteny 需要 layout；用户没给时这里生成一个稳定的默认双轨布局。
    layout = manifest.options.layout if manifest.options.layout else root / "synteny.layout"
    if manifest.options.layout is None:
        _write_default_layout(layout, manifest.query.name, manifest.subject.name)

    align_soft = manifest.options.align_soft or "blast"
    if align_soft == "blast":
        commands, pairwise_artifacts = _run_with_blast(manifest, root)
    elif align_soft in {"last", "diamond_blastp"}:
        commands, pairwise_artifacts = _run_with_catalog(manifest, root)
    else:
        raise ValueError(f"unsupported align_soft: {align_soft}")

    # pairwise 结果先收敛为统一 artifact 字典，供 graphics/local 等后续 workflow 继续消费。
    artifacts = {
        **pairwise_artifacts,
        "layout": str(layout),
        "figures": [],
        "simplified_fallback": False,
        "backend": "jcvi",
    }
    return commands, artifacts
