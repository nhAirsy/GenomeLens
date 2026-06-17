"""同步任务调度门面"""

# region import
from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

# endregion


T = TypeVar("T")


class TaskScheduler:
    """TaskScheduler(任务调度器)：让调度逻辑与业务逻辑分离"""

    def run(self, func: Callable[[], T]) -> T:
        """为 1.0.0 CLI(命令行接口) 工作流同步运行一个任务"""

        # 当前版本还是同步执行，保留 scheduler 门面是为了后续切换调度模型时不改业务层。
        return func()
