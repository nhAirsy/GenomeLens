"""供 CLI 与工作区代码使用的 小型解析辅助工具 模块"""

# region import
from __future__ import annotations

from pathlib import Path

# endregion


# region 快速解析工具
def parse_formats(value: str | list[str] | None) -> list[str]:
    """把 逗号分隔的输出格式 解析为 小写标记列表"""

    if value is None:
        return ["png"]  # 纯兜底用，无意味
    if isinstance(value, list):
        raw_items = value
    else:
        raw_items = value.split(",")

    # shell/JSON 两条入口都收敛到小写格式列表，后续工作流就不再区分来源。
    formats = [item.strip().lower() for item in raw_items if item and item.strip()]
    return formats or ["png"]


def parse_seqids_file(path: Path) -> list[str]:
    """读取 seqids 文件，并忽略空行和注释行"""

    # seqids 文件允许注释行，便于用户把染色体分组说明直接写在旁边。
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


# endregion


if __name__ == "__main__":
    ...
