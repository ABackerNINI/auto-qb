"""S7 守阵: 时间/大小复合串的解析与回显 (计划 26-10-17-1737 §04 S7 / D12-D13).

单点: gtm/units.py —— 文法镜像 auto-qb (TIME_UNITS / SIZE_UNITS + parse_time / parse_fsize),
盘上与契约只留复合串 ("30S" / "10MiB"), 不留「数值 + 独立单位」两种形态。
全部用例纯函数级, 不碰文件/网络。
"""

from __future__ import annotations

import pytest

from gtm.units import (
    SIZE_UNITS,
    TIME_UNITS,
    UnitError,
    format_duration,
    format_size,
    parse_duration,
    parse_size,
)

# ---- 解析: 每个单位都认 ----


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("30S", 30.0),
        ("5M", 300.0),
        ("2H", 7200.0),
        ("1D", 86400.0),
        ("2.5S", 2.5),
        (" 30 s ", 30.0),  # 首尾空白 + 小写单位照认 (写回仍统一大写)
    ]
)
def test_parse_duration_all_units(text: str, expected: float) -> None:
    assert parse_duration(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1B", 1),
        ("2KiB", 2 * 1024),
        ("10MiB", 10 * 1024**2),
        ("1GiB", 1024**3),
        ("1TiB", 1024**4),
        ("1.5MiB", int(1.5 * 1024**2)),
        ("10 mib", 10 * 1024**2),  # 大小写不敏感, 空白容错
    ]
)
def test_parse_size_all_units(text: str, expected: int) -> None:
    assert parse_size(text) == expected


def test_unit_tables_mirror_auto_qb() -> None:
    """单位表与 auto-qb schema 逐字一致 —— 多认/少认一个单位都会让「界面选不出来的值」出现."""
    assert TIME_UNITS == ("S", "M", "H", "D")
    assert SIZE_UNITS == ("B", "KiB", "MiB", "GiB", "TiB")


# ---- 解析: 旧式裸数值按语义平移 (读侧兼容, D13) ----


def test_legacy_numbers_are_migrated_by_semantics() -> None:
    """D13 之前的盘上是裸数值: 时间按「秒」、大小按「字节」平移 (不是按 0 或默认值)."""
    assert parse_duration(5.0) == 5.0
    assert parse_duration(30) == 30.0
    assert parse_size(1048576) == 1024**2
    assert parse_size(1048576.0) == 1024**2


# ---- 解析: 非法形态一律报错 (不静默取 0) ----


@pytest.mark.parametrize("bad", ["30", "30X", "S30", "", "1.2.3S"])
def test_parse_duration_rejects_bad_strings(bad: str) -> None:
    with pytest.raises(UnitError):
        parse_duration(bad)


def test_parse_duration_tolerates_surrounding_spaces() -> None:
    """手输空格不该报错(设置页的数值框接的就是用户原样输入)."""
    assert parse_duration("  30S ") == 30.0


@pytest.mark.parametrize("bad", ["10", "10MB", "10Mi", "MiB", "10MiB/s"])
def test_parse_size_rejects_bad_strings(bad: str) -> None:
    with pytest.raises(UnitError):
        parse_size(bad)


def test_parse_rejects_bool_and_non_scalar() -> None:
    """bool 是 int 子类 —— True 不该被当成 1 秒 / 1 字节 (与 config 的 bool 陷阱同口径)."""
    for fn in (parse_duration, parse_size):
        with pytest.raises(UnitError):
            fn(True)
        with pytest.raises(UnitError):
            fn(None)


def test_parse_size_requires_integral_bytes() -> None:
    """非整字节拒绝: 静默截断会让 "1.5B" 悄悄变成 1B."""
    with pytest.raises(UnitError):
        parse_size("1.5B")
    assert parse_size("1.5KiB") == 1536  # 换到更大单位后仍是整数就合法


# ---- 回显: 取能整除的最大单位, 且与解析互逆 ----


@pytest.mark.parametrize(
    ("seconds", "expected"), [
        (30.0, "30S"),
        (2.5, "2.5S"),
        (60.0, "1M"),
        (5400.0, "90M"),
        (7200.0, "2H"),
        (86400.0, "1D"),
        (172800.0, "2D"),
    ]
)
def test_format_duration(seconds: float, expected: str) -> None:
    assert format_duration(seconds) == expected
    assert parse_duration(expected) == seconds


@pytest.mark.parametrize(
    ("nbytes", "expected"),
    [
        (1, "1B"),
        (1024, "1KiB"),
        (1280, "1280B"),  # 除不尽 KiB -> 退到字节, 不编造小数
        (1024**2, "1MiB"),
        (100 * 1024**2, "100MiB"),
        (1536 * 1024, "1536KiB"),  # 能整除 KiB 但除不尽 MiB -> KiB
        (1024**4, "1TiB"),
    ]
)
def test_format_size(nbytes: int, expected: str) -> None:
    assert format_size(nbytes) == expected
    assert parse_size(expected) == nbytes
