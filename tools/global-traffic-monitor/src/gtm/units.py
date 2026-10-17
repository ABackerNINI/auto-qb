"""时间 / 大小的复合串解析与回显单点 (计划 26-10-17-1737 S7/D13).

**为什么有这个模块**: 设置页把工具参数（采样间隔 / 落盘阈值 / 订阅租约 …）渲染成「数值框 +
单位下拉」，而盘上与控制面契约里只留**一个复合串**（``"30S"`` / ``"10MiB"``）—— 不留「数值 +
独立单位键」两种形态（D13）。于是「串 <-> 物理量」的换算必须**只有一处**，否则校验（PUT
/config）、回显（GET /status 的 config）、落盘（config.yml）、迁移（旧裸数值）四处各写一遍，
迟早互相漂移成「界面显示 30S、实际按 30 秒以外的口径跑」。

**文法镜像 auto-qb**（`auto_qb.infra.utils.parse_time` / `parse_fsize` 与
`auto_qb.config.schema.fields.TIME_UNITS` / `SIZE_UNITS`）:

- 时间: ``^([\\d.]+)\\s*([SMHD])$``，单位 S/M/H/D（大小写不敏感，写回统一大写）
- 大小: ``^([\\d.]+)\\s*([KMGTP]?i?B)$``，单位只认二进制阶梯 B/KiB/MiB/GiB/TiB
  （与设置页下拉的 SIZE_UNITS 逐字一致 —— 多认一个 PiB 就会出现「界面选不出来的值被回显」）

**回显（format_*）走「最大且能整除的单位」**: 1048576 -> ``"1MiB"``、30.0 -> ``"30S"``、
5400 -> ``"90M"``；除不尽就退到下一级，最后落到 ``"<n>B"`` / ``"<n>S"``，保证
``parse(format(x)) == x``（往返无损，旧数值迁移与配置回读都靠它）。
"""

from __future__ import annotations

import math
import re
from typing import Union

#: 时间单位（与 auto-qb TIME_UNITS 逐字一致；写回时总是大写）
TIME_UNITS = ("S", "M", "H", "D")

#: 大小单位（与 auto-qb SIZE_UNITS 逐字一致；只认二进制阶梯）
SIZE_UNITS = ("B", "KiB", "MiB", "GiB", "TiB")

_DURATION_SCALE = {"S": 1.0, "M": 60.0, "H": 3600.0, "D": 86400.0}

_SIZE_SCALE = {"B": 1, "KIB": 1024, "MIB": 1024**2, "GIB": 1024**3, "TIB": 1024**4}

# 文法与 auto-qb 同形（大小那条忽略大小写，但单位键仍按大写查表 —— "1kib" 也认）
_DURATION_RE = re.compile(r"^([\d.]+)\s*([SMHD])$", re.IGNORECASE)
_SIZE_RE = re.compile(r"^([\d.]+)\s*([KMGTP]?i?B)$", re.IGNORECASE)


class UnitError(ValueError):
    """复合串解析失败（值形态不对 / 单位不在白名单 / 非有限值 / 非正数）。

    继承 ValueError: 调用方（config 校验）只需要 ``except ValueError`` 就能收口，
    不必知道工具内部有这个类；单测也能按 ValueError 断言。
    """


def _parse_number(text: str, what: str) -> float:
    """取数值部分并做有限性检查（``"nanS"`` 这类串过不了正则，这里只防 ``"1..2"`` 之类的脏值）。"""
    try:
        value = float(text)
    except ValueError as e:  # pragma: no cover - 正则只放行 [\d.]，这里属防御
        raise UnitError(f"{what}: 数值部分无法解析: {text!r}") from e
    if not math.isfinite(value):
        raise UnitError(f"{what}: 期望有限数值, 收到 {text!r}")
    return value


def parse_duration(value: Union[str, int, float]) -> float:
    """时间复合串 -> 秒（``"30S"`` -> 30.0 / ``"5M"`` -> 300.0）。

    **兼容旧值**: 裸数值（int/float，D13 之前的盘上形态）按「秒」语义平移 —— 这是
    「读侧接受旧数值」的那一半，写侧只会写出复合串。bool 显式拒绝（Python 里 bool
    是 int 子类，``True`` 不该被当成 1 秒）。
    """
    if isinstance(value, bool):
        raise UnitError(f"期望时间串 (如 30S / 5M), 收到布尔 {value!r}")
    if isinstance(value, (int, float)):
        seconds = _parse_number(str(value), "时间")
        return seconds
    if not isinstance(value, str):
        raise UnitError(f"期望时间串 (如 30S / 5M), 收到 {type(value).__name__} {value!r}")
    text = value.strip()
    match = _DURATION_RE.match(text)
    if not match:
        raise UnitError(f"期望时间串 (如 30S / 5M / 2H / 1D), 收到 {value!r}")
    number, unit = match.groups()
    return _parse_number(number, "时间") * _DURATION_SCALE[unit.upper()]


def parse_size(value: Union[str, int, float]) -> int:
    """大小复合串 -> 字节（``"10MiB"`` -> 10485760）。

    与 parse_duration 同口径：裸数值按「字节」语义平移（旧值兼容），bool 拒绝；
    非 iB 单位的缩写（``"10MB"``）拒绝 —— auto-qb 全程二进制阶梯，混进十进制单位会
    在限速/阈值上产生 4.8% 的静默偏差。
    """
    if isinstance(value, bool):
        raise UnitError(f"期望大小串 (如 10MiB), 收到布尔 {value!r}")
    if isinstance(value, (int, float)):
        return _as_int_bytes(_parse_number(str(value), "大小"), value)
    if not isinstance(value, str):
        raise UnitError(f"期望大小串 (如 10MiB), 收到 {type(value).__name__} {value!r}")
    text = value.strip()
    match = _SIZE_RE.match(text)
    if not match:
        raise UnitError(f"期望大小串 (如 1MiB / 100GiB), 收到 {value!r}")
    number, unit = match.groups()
    key = unit.upper()
    if key not in _SIZE_SCALE:
        raise UnitError(f"大小须用二进制单位 (B/KiB/MiB/GiB/TiB), 收到 {value!r}")
    return _as_int_bytes(_parse_number(number, "大小") * _SIZE_SCALE[key], value)


def _as_int_bytes(raw: float, original: object) -> int:
    """字节量取整：非整字节拒绝（静默截断会让「1.5B」变成 1B，校验期就该响亮）。"""
    if not math.isfinite(raw) or raw != int(raw):
        raise UnitError(f"大小须为整数字节, 收到 {original!r}")
    return int(raw)


def format_duration(seconds: float) -> str:
    """秒 -> 时间复合串（取「能整除的最大单位」，除不尽退到秒）。"""
    value = float(seconds)
    for unit in ("D", "H", "M"):
        scale = _DURATION_SCALE[unit]
        if value >= scale and value % scale == 0:
            return f"{int(value // scale)}{unit}"
    return f"{_fmt_number(value)}S"


def format_size(nbytes: int) -> str:
    """字节 -> 大小复合串（取「能整除的最大单位」，除不尽退到 B）。"""
    value = int(nbytes)
    for unit in ("TiB", "GiB", "MiB", "KiB"):
        scale = _SIZE_SCALE[unit.upper()]
        if value >= scale and value % scale == 0:
            return f"{value // scale}{unit}"
    return f"{value}B"


def _fmt_number(value: float) -> str:
    """数值回显：整数不带小数点（30.0 -> "30"），小数去掉浮点尾巴（2.500 -> "2.5"）。"""
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.6f}".rstrip("0").rstrip(".")
