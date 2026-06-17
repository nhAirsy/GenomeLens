"""用于进度事件的小型同步 signal bus(信号总线)"""

# region import
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

# endregion


@dataclass(frozen=True)
class Event:
    """Event(事件)：状态或诊断通知"""

    name: str
    payload: dict[str, object]


class SignalBus:
    """SignalBus(事件总线)：供 CLI(命令行接口)、workbench(工作台) 和 plugin(插件) 复用的同步回调"""

    def __init__(self) -> None:
        self._subscribers: list[Callable[[Event], None]] = []

    def subscribe(self, callback: Callable[[Event], None]) -> None:
        """注册一个回调"""

        # 这里保持最轻量的同步模型，CLI/workbench/plugin 都可直接复用。
        self._subscribers.append(callback)

    def emit(self, name: str, **payload: object) -> None:
        """向所有回调发送事件"""

        event = Event(name=name, payload=payload)
        # 事件对象先组装一次，避免各订阅者看到不一致的 payload。
        for callback in self._subscribers:
            callback(event)
