"""工具配置: 加载 / 校验 / 热重载 (S3 实现).

配置主权: 工具自有 config.yml 置于工具数据目录; auto-qb WebUI 设置页经控制面
(PUT /config) 代理读写, last-writer-wins (多实例盲写风险由设置页「读后写」缓解,
计划 §03 S3 注)。运行循环每轮读 ConfigHolder.current —— 采样间隔/适配器过滤/
flush 节流参数热生效; http host/port 改动需重启生效 (改绑监听地址无法热切换)。

默认参数 (计划 §05): sample_interval=5s / flush=Δ>=1MiB 或 30s /
notify_threshold=100MiB / http=127.0.0.1:8099 / lease_ttl=180s / heartbeat=60s /
notify_timeout=3s / adapters 排除 loopback 与 down。全部可经 WebUI 设置页调整。

校验 (黄金法则 4): fail-fast 全量校验并**聚合**所有错误 (未知键/类型不符/越界
一次性报齐, 不是见第一个错就停); 布尔陷阱: bool 是 int 子类, 数值字段显式拒
bool (sample_interval: true 不是 5)。解析器与 auto-qb 同族 (PyYAML)。
"""

from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass, fields, replace
from typing import Any, Mapping, Optional, Tuple

import yaml

logger = logging.getLogger("gtm.config")

# ---- 默认参数 (计划 §05) ----

DEFAULT_SAMPLE_INTERVAL_S = 5.0
DEFAULT_FLUSH_DELTA_MIB = 1
DEFAULT_FLUSH_INTERVAL_S = 30.0
DEFAULT_NOTIFY_THRESHOLD_MIB = 100
DEFAULT_HTTP_HOST = "127.0.0.1"
DEFAULT_HTTP_PORT = 8099
DEFAULT_LEASE_TTL_S = 180.0
DEFAULT_HEARTBEAT_INTERVAL_S = 60.0
DEFAULT_NOTIFY_TIMEOUT_S = 3.0

MIB = 1024 * 1024


@dataclass(frozen=True)
class Config:
    """工具全量配置 (快照式; 热重载 = 整体换对象, 无原地字段漂移).

    适配器过滤: include 先于 exclude 应用, 空列表 = 不设限; loopback/down 排除
    的默认语义在 AdapterFilter (见 sampler), 本层只承载用户正则列表。
    """

    sample_interval: float = DEFAULT_SAMPLE_INTERVAL_S
    flush_delta_bytes: int = DEFAULT_FLUSH_DELTA_MIB * MIB
    flush_interval_s: float = DEFAULT_FLUSH_INTERVAL_S
    notify_threshold_bytes: int = DEFAULT_NOTIFY_THRESHOLD_MIB * MIB
    http_host: str = DEFAULT_HTTP_HOST
    http_port: int = DEFAULT_HTTP_PORT
    lease_ttl_s: float = DEFAULT_LEASE_TTL_S
    heartbeat_interval_s: float = DEFAULT_HEARTBEAT_INTERVAL_S
    notify_timeout_s: float = DEFAULT_NOTIFY_TIMEOUT_S
    adapter_include: Tuple[str, ...] = ()
    adapter_exclude: Tuple[str, ...] = ()


# ---- 校验 (黄金法则 4: 全量 + 聚合) ----

# 字段 -> (校验器名, 人读说明); 校验器只认"标量字段", 列表字段 (adapter_*)
# 单独处理 (元素全为 str 即可)
_INT_FIELDS = ("flush_delta_bytes", "notify_threshold_bytes", "http_port")
_FLOAT_FIELDS = (
    "sample_interval",
    "flush_interval_s",
    "lease_ttl_s",
    "heartbeat_interval_s",
    "notify_timeout_s",
)
_STR_FIELDS = ("http_host", )
_LIST_FIELDS = ("adapter_include", "adapter_exclude")
_KNOWN_FIELDS = frozenset(_INT_FIELDS + _FLOAT_FIELDS + _STR_FIELDS + _LIST_FIELDS)

# 正数下限 (含): 这些字段必须 > 0 (时间/字节/端口)
_POSITIVE_FIELDS = frozenset(_INT_FIELDS + _FLOAT_FIELDS) - {"http_port"}
_PORT_RANGE = (1, 65535)


def _reject_bool(name: str, value: Any) -> Optional[str]:
    """bool 是 int 子类 —— 数值字段收到 True/False 一律拒绝 (sample_interval: true 不是 5)."""
    if isinstance(value, bool):
        return f"{name}: 期望数值, 收到布尔 {value!r}"
    return None


def _check_int(name: str, value: Any, errors: list[str]) -> Optional[int]:
    bad = _reject_bool(name, value)
    if bad:
        errors.append(bad)
        return None
    if not isinstance(value, int):
        errors.append(f"{name}: 期望整数, 收到 {type(value).__name__} {value!r}")
        return None
    if name in _POSITIVE_FIELDS and value <= 0:
        errors.append(f"{name}: 期望正数 (>0), 收到 {value}")
        return None
    if name == "http_port" and not (_PORT_RANGE[0] <= value <= _PORT_RANGE[1]):
        errors.append(f"{name}: 期望端口 1-65535, 收到 {value}")
        return None
    return value


def _check_float(name: str, value: Any, errors: list[str]) -> Optional[float]:
    bad = _reject_bool(name, value)
    if bad:
        errors.append(bad)
        return None
    if not isinstance(value, (int, float)):
        errors.append(f"{name}: 期望数值, 收到 {type(value).__name__} {value!r}")
        return None
    if not math.isfinite(float(value)):
        errors.append(f"{name}: 期望有限数值, 收到 {value!r}")
        return None
    fval = float(value)
    if name in _POSITIVE_FIELDS and fval <= 0:
        errors.append(f"{name}: 期望正数 (>0), 收到 {value}")
        return None
    return fval


def _check_str(name: str, value: Any, errors: list[str]) -> Optional[str]:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{name}: 期望非空字符串, 收到 {value!r}")
        return None
    return value.strip()


def _check_str_list(name: str, value: Any, errors: list[str]) -> Optional[Tuple[str, ...]]:
    if not isinstance(value, list) or any(not isinstance(x, str) for x in value):
        errors.append(f"{name}: 期望字符串数组 (正则列表), 收到 {type(value).__name__} {value!r}")
        return None
    cleaned = tuple(x for x in value if x.strip())
    for pattern in cleaned:
        try:
            re.compile(pattern)
        except re.error as e:
            errors.append(f"{name}: 非法正则 {pattern!r}: {e}")
    return cleaned


def validate_payload(payload: Mapping[str, Any]) -> Tuple[Optional[Config], Tuple[str, ...]]:
    """全量校验配置载荷: 成功返回 (Config, ()); 失败返回 (None, 聚合错误元组).

    校验面: 未知键 (黄金法则 4 口径 —— 拒绝拼写错误/过期键, 不静默忽略) /
    类型 (int/float/str, bool 显式拒) / 范围 (正数、端口 1-65535、有限数值)。
    逐键独立校验, 错误聚合一次报齐 (不止第一个错)。
    """
    if not isinstance(payload, Mapping):
        return None, (f"配置载荷必须是映射, 收到 {type(payload).__name__}", )
    errors: list[str] = []
    overrides: dict[str, Any] = {}
    for key in payload:
        if key not in _KNOWN_FIELDS:
            errors.append(f"未知配置键: {key!r} (已知: {', '.join(sorted(_KNOWN_FIELDS))})")
    for name in _INT_FIELDS:
        if name in payload:
            ok = _check_int(name, payload[name], errors)
            if ok is not None:
                overrides[name] = ok
    for name in _FLOAT_FIELDS:
        if name in payload:
            ok = _check_float(name, payload[name], errors)
            if ok is not None:
                overrides[name] = ok
    for name in _STR_FIELDS:
        if name in payload:
            ok = _check_str(name, payload[name], errors)
            if ok is not None:
                overrides[name] = ok
    for name in _LIST_FIELDS:
        if name in payload:
            ok = _check_str_list(name, payload[name], errors)
            if ok is not None:
                overrides[name] = ok
    if errors:
        return None, tuple(errors)
    return replace(Config(), **overrides), ()


def load_config(path: str) -> Tuple[Optional[Config], Tuple[str, ...]]:
    """从 config.yml 加载并校验: 文件缺失 -> 默认配置 (空载荷语义);
    解析失败/顶层非映射/校验失败 -> (None, 错误)."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    except FileNotFoundError:
        return Config(), ()
    except yaml.YAMLError as e:
        return None, (f"config.yml 解析失败 (YAML): {e}", )
    except OSError as e:
        return None, (f"config.yml 读取失败: {e}", )
    if raw is None:
        return Config(), ()  # 空文件 = 全部默认
    return validate_payload(raw)


def save_config(path: str, config: Config) -> None:
    """配置落盘: YAML (与 auto-qb 同族解析器, S6 WebUI 经 PUT /config 代理读写).

    写盘用 storage.atomic_write_text 工具内原子写单点 (同目录 tmp -> fsync ->
    replace): 读侧 (auto-qb 设置页 / 工具重启加载) 任何时刻见到完整文件。
    """
    from gtm.storage import atomic_write_text  # 延迟 import: config 单测不强制拉起 storage/filelock 链

    atomic_write_text(path, yaml.safe_dump(config_to_payload(config), allow_unicode=True, sort_keys=True))


def config_to_payload(config: Config) -> dict[str, Any]:
    """Config -> config.yml 载荷 (PUT /config 回显与 save_config 共用)."""
    return {f.name: getattr(config, f.name) for f in fields(config)}


class ConfigHolder:
    """配置热重载持有者: PUT /config 校验通过后整体换 Config 对象 (原子引用赋值),
    采样循环每轮读 current —— 热生效不丢采样。锁仅为防御性 (CPython 下属性赋值
    本身原子), 换取显式的 happens-before。"""
    def __init__(self, config: Config) -> None:
        self._config = config

    @property
    def current(self) -> Config:
        return self._config

    def replace(self, config: Config) -> None:
        self._config = config
