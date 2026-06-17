"""工作区创建门面"""

# region import
from __future__ import annotations

from pathlib import Path

from genomelens.data.workspace.output_layout import OutputLayout, create_output_layout

# endregion


class WorkspaceManager:
    """WorkspaceManager(工作区管理器)：创建并返回标准运行布局"""

    def prepare_run(self, outdir: str | Path, *, force: bool = False) -> OutputLayout:
        """准备一次运行的输出目录"""

        # manager 目前只是薄封装，但保留这个入口便于以后接入更多 workspace 策略。
        return create_output_layout(outdir, force=force)
