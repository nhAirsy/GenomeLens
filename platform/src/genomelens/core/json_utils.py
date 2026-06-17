"""JSON 安全提取工具：把 dict[str, object] 的值窄化为具体 Python 类型"""

# region import
from __future__ import annotations

import warnings
from typing import Any, Protocol, Self

# endregion


class _SupportsFromJson(Protocol):
    """支持 from_json 的 dataclass 协议，让 _nested 的泛型绑定更精确"""

    @classmethod
    def from_json(cls, data: dict[str, object]) -> Self: ...


def _warn(value: object, expected: str) -> None:
    """对无法收窄的值发出警告，调用方可通过 -W error 转为异常或捕获日志"""

    # 这里选择“告警并回退”而不是直接抛错，是为了兼容宽松的外部 JSON 协议。
    warnings.warn(
        f"忽略不可识别的 JSON 值 {value!r}，期望类型 {expected}",
        RuntimeWarning,
        stacklevel=3,
    )


def _str(value: object, default: str = "") -> str:
    """把 value 转成 str，None 时回退 default"""

    if value is None:
        return default
    # 字符串字段默认走最宽松转换，避免上层为展示型字段反复判型。
    return str(value)


def _int(value: object, default: int = 0) -> int:
    """把 value 转成 int，仅接受 int/float/可解析 str，否则回退 default 并警告"""

    if value is None:
        return default
    # 需要“带默认值的整数”时统一走这里，失败分支集中在 _optional_int 之后处理。
    result = _optional_int(value)
    if result is None:
        _warn(value, "int")
        return default
    return result


def _optional_int(value: object) -> int | None:
    """把 value 转成 int | None，非法时回退 None"""

    if value is None:
        return None
    if isinstance(value, bool):
        # bool 是 int 子类，这里显式处理可以把意图写清楚。
        return int(value)
    if isinstance(value, int):
        # 这里保留原始 dict，不做深拷贝，让调用方自己决定是否需要隔离修改。
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            _warn(value, "int | None")
            return None
    return None


def _optional_str(value: object) -> str | None:
    """把 value 转成 str | None，None 时回退 None"""

    if value is None:
        return None
    return str(value)


def _float(value: object, default: float = 0.0) -> float:
    """把 value 转成 float，仅接受 int/float/可解析 str，否则回退 default 并警告"""

    if value is None:
        return default
    result = _optional_float(value)
    if result is None:
        _warn(value, "float")
        return default
    return result


def _optional_float(value: object) -> float | None:
    """把 value 转成 float | None，非法时回退 None"""

    if value is None:
        return None
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, int | float):
        # 数字类型直接收敛为 float，避免上层再分 int/float 分支。
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            _warn(value, "float | None")
            return None
    return None


def _bool(value: object, default: bool = False) -> bool:
    """把 value 转成 bool，None 时回退 default"""

    if value is None:
        return default
    # 保持 Python 原生 truthy/falsy 语义，避免在多个摘要模型里重复约定。
    return bool(value)


def _dict(value: object) -> dict[str, object]:
    """把 value 安全转成 dict[str, object]，失败返回空 dict 并警告"""

    if value is None:
        return {}
    if isinstance(value, dict):
        # 与 _dict 一样保持浅层宽松策略，避免辅助函数偷偷改变对象语义。
        return value
    _warn(value, "dict[str, object]")
    return {}


def _list(value: object) -> list[Any]:
    """把 value 安全转成 list[Any]，失败返回空 list 并警告"""

    if value is None:
        return []
    if isinstance(value, list):
        # _any_list 给 truly-generic 列表字段使用，不额外做元素级收窄。
        return value
    _warn(value, "list")
    return []


def _str_list(value: object, default: list[str] | None = None) -> list[str]:
    """把 value 安全转成 list[str]，None 或类型不符时回退 default（默认空 list）并警告"""

    if value is None:
        return list(default) if default is not None else []
    if not isinstance(value, list):
        _warn(value, "list[str]")
        return list(default) if default is not None else []
    # 对外协议里的列表字段一律压成字符串列表，方便 UI / CLI 直接显示
    return [str(item) for item in value]


def _dict_list(value: object) -> list[dict[str, object]]:
    """把 value 安全转成 list[dict[str, object]]，非列表项跳过并警告"""

    if value is None:
        return []
    if not isinstance(value, list):
        _warn(value, "list[dict[str, object]]")
        return []
    # 忽略杂项元素，保证 artifact/species/job 这些集合字段可直接遍历
    return [item for item in value if isinstance(item, dict)]


def _any_list(value: object) -> list[Any]:
    """把 value 安全转成 list[Any]，失败返回空 list"""

    if value is None:
        return []
    if isinstance(value, list):
        return value
    _warn(value, "list[Any]")
    return []


def _str_dict(value: object) -> dict[str, str]:
    """把 value 安全转成 dict[str, str]，失败返回空 dict 并警告"""

    if value is None:
        return {}
    if not isinstance(value, dict):
        _warn(value, "dict[str, str]")
        return {}
    # 日志和错误块最终都会走文本展示，这里先统一做字符串化
    return {str(k): str(v) for k, v in value.items()}


def _nested[T: _SupportsFromJson](cls: type[T], value: object) -> T:
    """安全调用 dataclass.from_json，非 dict 时构造默认对象"""

    # 嵌套 dataclass 一律走同一个入口，保证“宽松 dict -> 强类型对象”的路径一致。
    return cls.from_json(_dict(value))
