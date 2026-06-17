"""真实 JCVI `graphics.karyotype` 全局多物种总图 workflow(工作流)

与 `graphics_karyotype` 不同，这个 workflow(工作流) 不重新计算共线性，而是把
shell(外壳) 在 pairwise(两两比较) 阶段已经算好的 N 个物种轨道与各对 `.simple`
(简化区块) 边，一次性渲染成一张跨全部物种的核型总图。

manifest(清单) 用 `tracks` 列出物种轨道（每个含 name 与 BED），用 `edges` 列出
轨道间连接（每条含 i/j 下标与 pairwise 产出的 simple 文件）。"""

# region import
from __future__ import annotations

from pathlib import Path

from jcvi.graphics.karyotype import main as jcvi_graphics_karyotype
from jcvi_genomelens.manifest_models import EngineRunManifest
from jcvi_genomelens.runtime.command_runner import CommandAudit, run_python_step

# endregion


# 轨道默认配色，循环使用；与 pairwise karyotype 的青/赭主色保持一致


_TRACK_COLORS = ("#2f6f73", "#b85c38", "#5b8c5a", "#8c6bb1", "#c2914a", "#41699e")


def _assert_ok(command: CommandAudit) -> None:
    if command.returncode != 0:
        raise RuntimeError(command.stderr or command.stdout or f"{command.name} failed")


def _seqids_from_bed(path: Path) -> list[str]:
    """按出现顺序读取 BED 的 seqid(序列编号)，去重保序"""

    seen: set[str] = set()
    ordered: list[str] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip() or line.startswith("#"):
                continue
            seqid = line.split("\t", 1)[0].strip()
            if seqid and seqid not in seen:
                # 全局核型图要求每条轨道的 seqid 顺序稳定，这里按 BED 首次出现顺序保留。
                seen.add(seqid)
                ordered.append(seqid)
    if not ordered:
        raise RuntimeError(f"No seqids found in BED: {path}")
    return ordered


def _write_global_seqids(path: Path, manifest: EngineRunManifest) -> Path:
    """每条 track(轨道) 一行 seqids(序列编号)，行序与 tracks 一致"""

    # seqids 文件逐行对应 tracks 列表，供 JCVI 按轨道读取。
    lines = [",".join(_seqids_from_bed(track.bed)) for track in manifest.tracks]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _track_rows(manifest: EngineRunManifest) -> list[str]:
    """把 N 个轨道竖直均匀铺开，生成 karyotype layout(布局) 的 track 段"""

    count = len(manifest.tracks)
    # 顶部 0.85、底部 0.15 之间均匀分布；单轨时居中
    top, bottom = 0.85, 0.15
    rows: list[str] = []
    for index, track in enumerate(manifest.tracks):
        if count == 1:
            y = (top + bottom) / 2
        else:
            y = top - (top - bottom) * index / (count - 1)
        color = _TRACK_COLORS[index % len(_TRACK_COLORS)]
        rows.append(f"{y:.4f}, 0.10, 0.90, 0, {color}, {track.name}, top, {track.bed}")
    return rows


def _write_global_layout(path: Path, manifest: EngineRunManifest) -> Path:
    """生成 karyotype layout(布局)：track 段 + edges 段"""

    lines = ["# y, xstart, xend, rotation, color, label, va, bed"]
    lines.extend(_track_rows(manifest))
    lines.append("# edges")
    for edge in manifest.edges:
        # edge 的 i/j 直接引用 manifest.tracks 的下标，不再额外做名称映射。
        lines.append(f"e, {edge.i}, {edge.j}, {edge.simple}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def run(manifest: EngineRunManifest, outdir: str | Path) -> tuple[list[CommandAudit], dict[str, object]]:
    """把已算好的多物种 tracks/edges 渲染成一张全局核型总图"""

    root = Path(outdir).expanduser().resolve(strict=False)
    root.mkdir(parents=True, exist_ok=True)
    # 用户不提供 layout/seqids 时，直接从 shell 汇总好的 tracks/edges 自动生成。
    seqids = (
        manifest.options.seqids
        if manifest.options.seqids
        else _write_global_seqids(root / "karyotype_global.seqids", manifest)
    )
    layout = (
        manifest.options.layout
        if manifest.options.layout
        else _write_global_layout(root / "karyotype_global.layout", manifest)
    )
    commands: list[CommandAudit] = []
    figures: list[str] = []
    formats = manifest.options.formats or ["png"]
    for fmt in formats:
        figure = root / f"karyotype_global.{fmt}"
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
            raise RuntimeError(f"JCVI global karyotype figure was not created: {figure}")
        figures.append(str(figure))
    # 这里的 artifact 字段面向 shell 多物种摘要层，保留轨道/边数量便于 UI 展示。
    artifacts: dict[str, object] = {
        "figures": figures,
        "global_karyotype_figures": figures,
        "global_karyotype_seqids": str(seqids),
        "global_karyotype_layout": str(layout),
        "track_count": len(manifest.tracks),
        "edge_count": len(manifest.edges),
        "simplified_fallback": False,
        "backend": "jcvi.graphics.karyotype",
    }
    return commands, artifacts
