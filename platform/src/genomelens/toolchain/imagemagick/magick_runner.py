"""ImageMagick 调用包装器"""

# region import
from __future__ import annotations

from pathlib import Path

from genomelens.toolchain.runtime.subprocess_runner import CommandResult, run_command

# endregion


def convert_image(magick: str | Path, source: str | Path, target: str | Path) -> CommandResult:
    """使用 ImageMagick 转换图像"""

    # 这里只做最薄的命令包装，把格式/参数决策留给更上层的业务代码。
    return run_command([magick, source, target])
