"""真实 JCVI `graphics.dotplot` workflow(工作流)"""

# region import
from __future__ import annotations

from pathlib import Path

from jcvi.graphics.dotplot import dotplot_main as jcvi_graphics_dotplot
from jcvi_genomelens.manifest_models import EngineRunManifest
from jcvi_genomelens.runtime.command_runner import CommandAudit, run_python_step
from jcvi_genomelens.workflows.mcscan_pairwise import run as run_pairwise

# endregion


def _assert_ok(command: CommandAudit) -> None:
    if command.returncode != 0:
        raise RuntimeError(command.stderr or command.stdout or f"{command.name} failed")


def draw_dotplots(
    manifest: EngineRunManifest,
    root: Path,
    artifacts: dict[str, object],
    *,
    output_prefix: str = "dotplot",
) -> tuple[list[CommandAudit], list[str]]:
    """基于现有 anchors(锚点) 与 BED 绘制 dotplot(点图)"""

    commands: list[CommandAudit] = []
    figures: list[str] = []
    formats = manifest.options.formats or ["png"]
    # dotplot 直接消费 pairwise 阶段生成的 anchors，不重复做同源搜索。
    anchors = str(artifacts["anchors"])
    for fmt in formats:
        figure = root / f"{output_prefix}.{fmt}"
        command = run_python_step(
            "jcvi.graphics.dotplot",
            jcvi_graphics_dotplot,
            [
                anchors,
                f"--qbed={manifest.query.bed}",
                f"--sbed={manifest.subject.bed}",
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
            raise RuntimeError(f"JCVI dotplot figure was not created: {figure}")
        figures.append(str(figure))
    return commands, figures


def run(manifest: EngineRunManifest, outdir: str | Path) -> tuple[list[CommandAudit], dict[str, object]]:
    """运行真实 pairwise MCscan(成对 MCscan) 后绘制 dotplot(点图)"""

    # 独立 dotplot 工作流本质上是“pairwise + 只画 dotplot”。
    commands, artifacts = run_pairwise(manifest, outdir)
    root = Path(outdir).expanduser().resolve(strict=False)
    dotplot_commands, figures = draw_dotplots(manifest, root, artifacts)
    commands.extend(dotplot_commands)
    artifacts["figures"] = figures
    artifacts["dotplot_figures"] = figures
    artifacts["backend"] = "jcvi.graphics.dotplot"
    return commands, artifacts
