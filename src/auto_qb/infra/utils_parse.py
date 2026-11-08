"""utils_parse.py — R5 大文件拆分(计划 26-11-02-2342 §07)

解析/时间/布尔/数量/平台判定域。全部为纯函数, 原 `infra.utils` 的公开名由根模块重导出,
调用方 import 路径不变。只搬运定义, 实现逐行未改。
"""

import base64
import ipaddress
import json
import math
import os
import shutil
import tempfile
import hashlib
from functools import lru_cache
import re
import secrets
import subprocess
import sys
import threading
import time
import logging
from dataclasses import dataclass
from datetime import time as dtime
from functools import wraps
from urllib.parse import urlparse
from typing import Callable, List, Optional, Tuple


def parse_hm(text: str) -> "tuple[int, int]":
    """解析 "HH:MM" -> (时, 分); 非法格式或越界(须 00:00-23:59)抛 ValueError
    (date_time 条件与通知免打扰时段共用, 越界提早暴露防运行时静默失配)"""
    try:
        h, m = str(text).strip().split(":")
        hour, minute = int(h), int(m)
    except ValueError as e:
        raise ValueError(f"非法 HH:MM 格式: {text}") from e
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"时间越界(须 00:00-23:59): {text}")
    return hour, minute


def parse_time_range(spec: str) -> "tuple[dtime, dtime]":
    """解析 "HH:MM-HH:MM" -> (start, end) 端点时刻(支持跨午夜, 端点次序原样保留);
    非法格式/越界抛 ValueError。解析单点: date_time 条件构造期预解析(R2#20)与本函数的
    原消费方(通知 quiet_hours / HR 限速窗口)共用, 不得各写一份。"""
    start_s, end_s = str(spec).split("-", 1)
    return dtime(*parse_hm(start_s)), dtime(*parse_hm(end_s))


def time_within(now: dtime, start: dtime, end: dtime) -> bool:
    """已解析端点的时段判定(time_in_range 的比较半边; date_time 条件构造期预解析端点后
    按本函数逐轮比较)。

    **按分钟粒度比较**: 区间语法只写到分钟, 故先把秒/微秒截掉再比 —— 端点所在的整分钟都算在内
    (23:59:30 落在 "…-23:59" 之内)。2026-10-19 前按秒直比, 端点分钟的后 59 秒被判出界:
    "00:00-23:59"(用户表达"全天")每天漏掉 23:59:01-23:59:59, 且与表达式侧
    sys.time_of_day(hour*60+minute, 分钟口径)结论相反 —— 等价性用例在该分钟必红
    (issue 26-10-19-0013)。
    """
    now = now.replace(second=0, microsecond=0)
    if start <= end:
        return start <= now <= end
    return now >= start or now <= end  # 跨午夜: 不在 start-24:00 即在 00:00-end


def time_in_range(now: dtime, spec: str) -> bool:
    """当前时刻是否在 "HH:MM-HH:MM" 区间内(支持跨午夜, 如 "23:00-08:00"; 通知 quiet_hours /
    HR 限速窗口共用; date_time 条件已改为构造期预解析端点, 走 parse_time_range + time_within)

    解析与比较拆为 parse_time_range / time_within 单点, 本函数是二者的组合入口,
    三个消费方(规则条件 / 通知 quiet_hours / HR 限速窗口)口径一致。
    """
    return time_within(now, *parse_time_range(spec))


def is_loopback_host(host: str) -> bool:
    """回环地址判据(计划 26-10-14-1241): localhost 或 IPv4/IPv6 回环字面量(127/8、::1)

    config 校验(S1 5 危险组合)与 hr 配对门(pairing=auto 的生效逻辑)共用 —— 单点在此,
    两处不得各写一份; 无法解析为地址字面量的输入一律按非回环处理(保守)。
    """
    h = str(host or "").strip().lower()
    if not h:
        return False
    if h == "localhost":
        return True
    try:
        return ipaddress.ip_address(h).is_loopback
    except ValueError:
        return False


def parse_bool(value) -> bool:
    """将字符串或布尔值转换为布尔值"""
    if isinstance(value, bool):
        return value
    s = str(value).strip().lower()
    if s in ("true", "1", "yes", "on"):
        return True
    if s in ("false", "0", "no", "off"):
        return False
    raise ValueError(f"无效布尔值: {value}")


def convert_bool_in_dict(d):
    """递归地将字典中的字符串布尔值转换为bool类型(纯数字字符串保持原样)"""
    if isinstance(d, str):
        try:
            d = parse_bool(d)
        except ValueError:
            pass

    if isinstance(d, dict):
        for k, v in d.items():
            if isinstance(v, str) and not v.isdecimal():
                d[k] = convert_bool_in_dict(v)
            elif isinstance(v, dict):
                d[k] = convert_bool_in_dict(v)
            elif isinstance(v, list):
                # 列表元素与字典分支同口径(26-10-06-0028 H-03): 纯数字串跳过, 其余递归 ——
                # 无条件递归会把列表里的 "1"/"on" 改写成 True/False(导出模板回填类型漂移)
                d[k] = [
                    item if isinstance(item, str) and item.isdecimal() else convert_bool_in_dict(item) for item in v
                ]

    return d


def _parse_quantity(
    raw,
    pattern: str,
    units: dict,
    *,
    cast: Callable[[float], float],
    empty_zero: bool,
    err: str,
    err_unit: Optional[str] = None,
):
    """数量解析骨架: 正则 -> 单位白名单兜底 -> 乘数(issue 26-10-29-1252 单点)

    parse_time/parse_fsize/parse_speed 是「regex -> 单位表 -> 乘数」的三份同构副本(B 类分歧
    重复), 单位白名单记在两处(正则字符类 + dict 键) —— 此前只有 fsize 在两表之间补了
    `unit not in units` 兜底, speed 的正则比表宽一格: "1iB/s" 命中正则但不在表里,
    units[unit] 直接下标抛 KeyError, 而 KeyError 不是 ValueError 子类, 逃出校验层 _try
    (只接 ValueError)与 load_config「任何配置问题统一抛 ConfigError」的契约, 用户只见裸
    traceback。骨架把白名单兜底收进必经路径, 「正则比单位表宽」这类同构副本演化分歧在结构上
    不可能再以 KeyError 形态发生; 三个公有函数各自保留单位表 / 正则 / 报错文案 / 返回类型 /
    空串语义(带 mode 参数合一的做法被 issue 否决: 返回类型与空串语义三份都不同, 参数化后每个
    调用点都要记 mode 语义, 可读性净损)。

    - empty_zero: 空串语义 —— True 空串返回 0(time/speed); False 空串落进正则不命中按 err
      报错(fsize);
    - err / err_unit: 正则不命中 / 单位不在表里的报错文案(fsize 与 speed 两条文案不同, 各自
      传入; err_unit 缺省同 err —— time 的正则与单位表精确同宽, 白名单分支不可达);
    - 白名单检查先于数值转换(fsize 旧序): speed 的 "1.5.5iB/s" 这类双重非法输入的报错文案
      由 float 转换错变为单位白名单错, 异常类不变(仍 ValueError);
    - 输入先 .upper() 再匹配, flags 恒 re.IGNORECASE: time 旧实现无 flag, 但大写化之后该
      flag 无可观测差异。
    """
    if not raw and empty_zero:
        return 0
    m = re.match(pattern, str(raw).strip().upper(), re.IGNORECASE)
    if not m:
        raise ValueError(f"{err}: {raw}")
    value, unit = m.groups()
    if unit not in units:
        raise ValueError(f"{err_unit or err}: {raw}")
    return cast(float(value) * units[unit])


def parse_time(time_str: str) -> float:
    """时间字符串(如 '3D', '12H', '10M') -> 秒; 空串返回0"""
    return _parse_quantity(
        time_str,
        r"^([\d.]+)\s*([SMHD])$",
        {
            "S": 1,
            "M": 60,
            "H": 3600,
            "D": 86400
        },
        cast=float,
        empty_zero=True,
        err="无效时间格式",
    )


def parse_fsize(fsize_str: str) -> int:
    """大小字符串(如 '10.5 GiB') -> 字节; 仅支持二进制单位: B, KiB, MiB, GiB, TiB, PiB"""
    return _parse_quantity(
        fsize_str,
        r"^([\d.]+)\s*([KMGTP]?i?B)$",
        {
            "B": 1,
            "KIB": 1024,
            "MIB": 1024**2,
            "GIB": 1024**3,
            "TIB": 1024**4,
            "PIB": 1024**5
        },
        cast=int,
        empty_zero=False,
        err="无效大小格式",
        err_unit="无效大小格式(需使用iB单位, 如 10MiB)",
    )


def parse_speed(speed_str: str) -> int:
    """速度字符串(如 '10MiB/s', '1000KiB/s') -> 字节/秒; 空串返回0

    单位白名单兜底在 _parse_quantity 单点(issue 26-10-29-1252): 无前缀 iB/s 与十进制前缀
    KB/s, MB/s, GB/s 命中正则但不在单位表里, 一律 ValueError(旧实现 KeyError)。
    """
    return _parse_quantity(
        speed_str,
        r"^([\d.]+)\s*([KMG]?i?B/S)$",
        {
            "B/S": 1,
            "KIB/S": 1024,
            "MIB/S": 1024**2,
            "GIB/S": 1024**3
        },
        cast=int,
        empty_zero=True,
        err="无效速度格式",
        err_unit="无效速度格式(需使用iB单位, 如 10MiB/s)",
    )


def parse_hr_condition(cond_str) -> tuple:
    """解析HR触发条件字符串 -> ('dlratio', ratio) 或 ('dlsize', bytes)

    示例: "80%" -> ('dlratio', 0.8), "10MiB" -> ('dlsize', 字节); 缺省默认80%
    边界在解析单点拦下(校验层经 _try 复用): 百分比须 (0, 100] —— "0%"/负数会让条件立即满足
    (种子一入站就打 HR 标), ">100%" 永不触发, 均与配置意图相反; 下载量须 > 0("0MiB" 同样立即满足)
    """
    cond_str = str(cond_str).strip()
    if not cond_str:
        return ("dlratio", 0.8)  # 默认80%触发
    if cond_str.endswith("%"):  # 百分比, 如 "70%"
        ratio = float(cond_str[:-1]) / 100.0
        if not math.isfinite(ratio) or not 0 < ratio <= 1:
            raise ValueError(f"HR 百分比条件须 (0, 100]: {cond_str}")
        return ("dlratio", ratio)
    size = parse_fsize(cond_str)  # 下载量绝对值, 如 "10MiB"
    if size <= 0:
        raise ValueError(f"HR 下载量条件须 > 0: {cond_str}")
    return ("dlsize", size)


def is_windows() -> bool:
    """判断当前操作系统是否为 Windows"""
    return sys.platform.startswith("win")


def is_linux() -> bool:
    """判断当前操作系统是否为 Linux"""
    return sys.platform.startswith("linux")


def is_mac() -> bool:
    """判断当前操作系统是否为 MacOS"""
    return sys.platform.startswith("darwin")


def is_posix() -> bool:
    """判断当前操作系统是否为 Unix 类系统(包含 Linux、macOS、BSD 等)"""
    return sys.platform.startswith(('linux', 'darwin', 'freebsd', 'aix'))


def add_long_path_prefix_for_win(path: str) -> str:
    """为 Windows 文件路径添加长路径支持前缀(\\\\?\\ 或 UNC), 非Windows系统则返回原路径

    已绝对的 Windows 路径(已有 \\\\?\\ 前缀 / UNC \\\\ / 盘符 X:\\)直接加前缀,
    不经 os.path.abspath — 后者在 Linux CI 上(monkeypatch 模拟 win32 时)会用 Linux 语义
    把 Windows 路径当相对路径并拼上 cwd, 导致测试失败。仅对真正相对的路径才走 abspath。
    """
    if not is_windows():
        return path

    norm = path.replace("/", "\\")
    # 已有 \\?\ 前缀 -> 原样返回
    if norm.startswith("\\\\?\\"):
        return norm
    # UNC 路径 (\\server\share\...) -> \\?\UNC\server\share\...
    if norm.startswith("\\\\"):
        return "\\\\?\\UNC" + norm[1:]
    # 盘符路径 (C:\...) -> 已绝对, 直接加前缀
    if re.match(r"^[A-Za-z]:[\\/]", norm):
        return "\\\\?\\" + norm
    # 相对路径 -> 先转绝对路径再加前缀
    abs_path = os.path.abspath(norm).replace("/", "\\")
    return "\\\\?\\" + abs_path


def parse_compare(spec: str, value_parser):
    """解析比较表达式: '>=100MiB' -> ('>=', 字节); '<24H' -> ('<', 秒); 缺省为 '=='"""
    m = re.match(r"^\s*(>=|<=|>|<|==|=|!=)?\s*(.+?)\s*$", str(spec))
    if not m:
        raise ValueError(f"无效比较表达式: {spec}")
    op, rest = m.group(1), m.group(2)
    if op in (None, "="):
        op = "=="
    return op, value_parser(rest)


def compare(op: str, left, right) -> bool:
    """执行比较: op 为 >, <, >=, <=, !=, =="""
    if op == ">":
        return left > right
    if op == "<":
        return left < right
    if op == ">=":
        return left >= right
    if op == "<=":
        return left <= right
    if op == "!=":
        return left != right
    return left == right
