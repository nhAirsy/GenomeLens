"""json_utils 安全提取 helper 的单元测试"""

# region import
from __future__ import annotations

from dataclasses import dataclass

import pytest

from genomelens.core.json_utils import (
    _any_list,
    _bool,
    _dict,
    _dict_list,
    _float,
    _int,
    _list,
    _nested,
    _optional_float,
    _optional_int,
    _str,
    _str_dict,
    _str_list,
)

# endregion


class TestStr:
    """测试 _str"""

    def test_none_returns_default(self) -> None:
        assert _str(None) == ""
        assert _str(None, default="fallback") == "fallback"

    def test_non_str_values_are_stringified(self) -> None:
        assert _str(42) == "42"
        assert _str(3.14) == "3.14"
        assert _str(True) == "True"

    def test_str_preserved(self) -> None:
        assert _str("hello") == "hello"


class TestInt:
    """测试 _int"""

    def test_none_returns_default(self) -> None:
        assert _int(None) == 0
        assert _int(None, default=7) == 7

    def test_int_and_float_accepted(self) -> None:
        assert _int(42) == 42
        assert _int(3.9) == 3

    def test_numeric_string_accepted(self) -> None:
        assert _int("123") == 123

    def test_bool_converted(self) -> None:
        assert _int(True) == 1
        assert _int(False) == 0

    def test_invalid_warns_and_returns_default(self) -> None:
        with pytest.warns(RuntimeWarning):
            assert _int("abc", default=-1) == -1
        with pytest.warns(RuntimeWarning):
            assert _int([1, 2], default=-1) == -1


class TestOptionalInt:
    """测试 _optional_int"""

    def test_none_returns_none(self) -> None:
        assert _optional_int(None) is None

    def test_valid_returns_int(self) -> None:
        assert _optional_int(5) == 5
        assert _optional_int("10") == 10

    def test_invalid_returns_none_with_warning(self) -> None:
        with pytest.warns(RuntimeWarning):
            assert _optional_int("xyz") is None


class TestFloat:
    """测试 _float"""

    def test_none_returns_default(self) -> None:
        assert _float(None) == 0.0
        assert _float(None, default=1.5) == 1.5

    def test_int_and_float_accepted(self) -> None:
        assert _float(3) == 3.0
        assert _float(2.5) == 2.5

    def test_numeric_string_accepted(self) -> None:
        assert _float("1.25") == 1.25

    def test_invalid_warns_and_returns_default(self) -> None:
        with pytest.warns(RuntimeWarning):
            assert _float("abc", default=-1.0) == -1.0


class TestOptionalFloat:
    """测试 _optional_float"""

    def test_none_returns_none(self) -> None:
        assert _optional_float(None) is None

    def test_invalid_returns_none_with_warning(self) -> None:
        with pytest.warns(RuntimeWarning):
            assert _optional_float("xyz") is None


class TestBool:
    """测试 _bool"""

    def test_none_returns_default(self) -> None:
        assert _bool(None) is False
        assert _bool(None, default=True) is True

    def test_truthy_and_falsy_values(self) -> None:
        assert _bool(True) is True
        assert _bool(False) is False
        assert _bool("yes") is True
        assert _bool("") is False
        assert _bool(1) is True
        assert _bool(0) is False


class TestDict:
    """测试 _dict"""

    def test_none_returns_empty_dict(self) -> None:
        assert _dict(None) == {}

    def test_dict_preserved(self) -> None:
        payload = {"a": 1}
        assert _dict(payload) is payload

    def test_invalid_warns_and_returns_empty(self) -> None:
        with pytest.warns(RuntimeWarning):
            assert _dict("not a dict") == {}


class TestList:
    """测试 _list"""

    def test_none_returns_empty_list(self) -> None:
        assert _list(None) == []

    def test_list_preserved(self) -> None:
        payload = [1, 2, 3]
        assert _list(payload) is payload

    def test_invalid_warns_and_returns_empty(self) -> None:
        with pytest.warns(RuntimeWarning):
            assert _list("not a list") == []


class TestStrList:
    """测试 _str_list"""

    def test_none_returns_default(self) -> None:
        assert _str_list(None) == []
        assert _str_list(None, default=["png"]) == ["png"]

    def test_elements_stringified(self) -> None:
        assert _str_list([1, True, "x"]) == ["1", "True", "x"]

    def test_invalid_warns_and_returns_default(self) -> None:
        with pytest.warns(RuntimeWarning):
            assert _str_list("abc", default=["fallback"]) == ["fallback"]


class TestDictList:
    """测试 _dict_list"""

    def test_none_returns_empty(self) -> None:
        assert _dict_list(None) == []

    def test_non_dict_items_skipped(self) -> None:
        assert _dict_list([{"a": 1}, "skip", {"b": 2}]) == [{"a": 1}, {"b": 2}]

    def test_invalid_warns_and_returns_empty(self) -> None:
        with pytest.warns(RuntimeWarning):
            assert _dict_list("abc") == []


class TestAnyList:
    """测试 _any_list"""

    def test_none_returns_empty(self) -> None:
        assert _any_list(None) == []

    def test_list_preserved(self) -> None:
        payload = [1, "two"]
        assert _any_list(payload) is payload


class TestStrDict:
    """测试 _str_dict"""

    def test_none_returns_empty(self) -> None:
        assert _str_dict(None) == {}

    def test_keys_and_values_stringified(self) -> None:
        assert _str_dict({1: True}) == {"1": "True"}

    def test_invalid_warns_and_returns_empty(self) -> None:
        with pytest.warns(RuntimeWarning):
            assert _str_dict("abc") == {}


@dataclass(frozen=True)
class _SampleNested:
    """仅用于测试 _nested 的样例 dataclass"""

    name: str = ""
    count: int = 0

    @classmethod
    def from_json(cls, data: dict[str, object]) -> _SampleNested:
        return cls(name=_str(data.get("name")), count=_int(data.get("count")))


class TestNested:
    """测试 _nested"""

    def test_dict_deserializes(self) -> None:
        result = _nested(_SampleNested, {"name": "demo", "count": "5"})
        assert result == _SampleNested(name="demo", count=5)

    def test_none_returns_default_instance(self) -> None:
        result = _nested(_SampleNested, None)
        assert result == _SampleNested()

    def test_non_dict_warns_and_returns_default(self) -> None:
        with pytest.warns(RuntimeWarning):
            result = _nested(_SampleNested, "abc")
        assert result == _SampleNested()
