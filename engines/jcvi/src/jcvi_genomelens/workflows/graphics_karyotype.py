"""真实 JCVI `graphics.karyotype` workflow(工作流)"""

# region import
from __future__ import annotations

from pathlib import Path

from jcvi.graphics.karyotype import main as jcvi_graphics_karyotype
from jcvi_genomelens.manifest_models import EngineRunManifest
from jcvi_genomelens.runtime.command_runner import CommandAudit, run_python_step
from jcvi_genomelens.workflows.mcscan_pairwise import run as run_pairwise

# endregion


def _assert_ok(command: CommandAudit) -> None:
    if command.returncode != 0:
        raise RuntimeError(command.stderr or command.stdout or f"{command.name} failed")


def _seqids_from_bed(path: Path) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip() or line.startswith("#"):
                continue
            seqid = line.split("\t", 1)[0].strip()
            if seqid and seqid not in seen:
                # karyotype 需要稳定染色体顺序，这里按 BED 首次出现顺序保留。
                seen.add(seqid)
                ordered.append(seqid)
    if not ordered:
        raise RuntimeError(f"No seqids found in BED: {path}")
    return ordered


def _write_default_seqids(path: Path, manifest: EngineRunManifest) -> Path:
    query_seqids = ",".join(_seqids_from_bed(manifest.query.bed))
    subject_seqids = ",".join(_seqids_from_bed(manifest.subject.bed))
    path.write_text(f"{query_seqids}\n{subject_seqids}\n", encoding="utf-8")
    return path


def _write_default_layout(path: Path, manifest: EngineRunManifest, simple: str) -> Path:
    path.write_text(
        "\n".join(
            [
                "# y, xstart, xend, rotation, color, label, va, bed",
                f"0.65, 0.10, 0.90, 0, #2f6f73, {manifest.query.name}, top, {manifest.query.bed}",
                f"0.35, 0.10, 0.90, 0, #b85c38, {manifest.subject.name}, top, {manifest.subject.bed}",
                "# edges",
                f"e, 0, 1, {simple}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def run(manifest: EngineRunManifest, outdir: str | Path) -> tuple[list[CommandAudit], dict[str, object]]:
    """运行 pairwise MCscan(成对 MCscan) 后绘制 karyotype(核型共线性图)"""

    commands, artifacts = run_pairwise(manifest, outdir)
    root = Path(outdir).expanduser().resolve(strict=False)
    # 用户未提供 seqids/layout 时，这里按 pairwise 输入自动生成最小可用版本。
    seqids = (
        manifest.options.seqids
        if manifest.options.seqids
        else _write_default_seqids(root / "karyotype.seqids", manifest)
    )
    layout = (
        manifest.options.layout
        if manifest.options.layout
        else _write_default_layout(root / "karyotype.layout", manifest, str(artifacts["simple"]))
    )
    figures: list[str] = []
    formats = manifest.options.formats or ["png"]
    for fmt in formats:
        figure = root / f"karyotype.{fmt}"
        command = run_python_step(
            "jcvi.graphics.karyotype",
            jcvi_graphics_karyotype,
            [
                str(seqids),
                str(layout),
                "--format",
                fmt,
                "--notex",
                "-o",
                str(figure),
            ],
            cwd=root,
        )
        commands.append(command)
        _assert_ok(command)
        if not figure.is_file() or figure.stat().st_size == 0:
            raise RuntimeError(f"JCVI karyotype figure was not created: {figure}")
        figures.append(str(figure))
    # 统一 figures 入口供 shell 归档，细分字段保留给 UI/后处理使用。
    artifacts["figures"] = figures
    artifacts["karyotype_figures"] = figures
    artifacts["karyotype_seqids"] = str(seqids)
    artifacts["karyotype_layout"] = str(layout)
    artifacts["backend"] = "jcvi.graphics.karyotype"
    return commands, artifacts
