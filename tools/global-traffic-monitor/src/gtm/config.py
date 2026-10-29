"""工具配置: 加载 / 校验 / 热重载 (S3 实现).

配置主权: 工具自有 config.yml 置于工具数据目录; auto-qb WebUI 设置页经控制面
(PUT /config) 代理读写, last-writer-wins (多实例盲写风险由设置页「读后写」缓解,
计划 §03 S3 注)。运行循环每轮读 ConfigHolder.current —— 采样间隔/适配器过滤/
flush 节流参数热生效; http host/port 改动需重启生效 (改绑监听地址无法热切换)。

默认参数 (计划 §05): sample_interval=5S / flush=Δ>=1MiB 或 30S /
notify_threshold=100MiB / http=127.0.0.1 (http_port=0 由内核分配随机端口, S13/D9;
host 强制回环 —— 127.0.0.0/8 与 ::1, 校验层兑现「控制面不提供跨机访问面」承诺) /
lease_ttl=180S / heartbeat=60S / notify_timeout=3S / adapters 排除 loopback 与 down /
autostart=true (自启意图唯一裁决, S14/D13)。全部可经 WebUI 设置页调整。

**时间 / 大小的形态 (26-10-17-1737 S7/D13)**: 盘上与契约 (config.yml / PUT /config /
GET /status 的 config 回显) 一律是**复合串** —— ``"30S"`` / ``"10MiB"``，不留「数值 +
独立单位键」两种形态; 解析/回显单点在 gtm/units.py (文法镜像 auto-qb)。内存里的 Config
仍是运行期物理量 (秒 / 字节), 采样循环与存储层不必认识单位。**读侧兼容旧式裸数值**
(D13 之前的形态): ``sample_interval: 5.0`` 按秒、``flush_delta_bytes: 1048576`` 按字节
平移, 下次写盘即迁移成复合串 (启动时还会做一次显式一次性迁移, 见
migrate_legacy_config)。

校验 (黄金法则 4): fail-fast 全量校验并**聚合**所有错误 (未知键/类型不符/越界/串解析失败
一次性报齐, 不是见第一个错就停); 布尔陷阱: bool 是 int 子类, 数值字段显式拒
bool (sample_interval: true 不是 5S); 布尔字段 (autostart) 反向只收 true/false
(给 0/1 也拒, 免得把「显式关过」写成数字而丢失语义)。解析器与 auto-qb 同族 (PyYAML)。
"""

from __future__ import annotations

import ipaddress
import logging
import math
import re
from dataclasses import dataclass, fields, replace
from typing import Any, Mapping, Optional, Tuple

import yaml

from gtm.units import UnitError, format_duration, format_size, parse_duration, parse_size

logger = logging.getLogger("gtm.config")

# ---- 默认参数 (计划 §05) ----

DEFAULT_SAMPLE_INTERVAL_S = 5.0
DEFAULT_FLUSH_DELTA_MIB = 1
DEFAULT_FLUSH_INTERVAL_S = 30.0
DEFAULT_NOTIFY_THRESHOLD_MIB = 100
DEFAULT_HTTP_HOST = "127.0.0.1"
# S13/D9: 端口默认 0 = 请内核分配随机空闲端口 (server.start 回填真实端口并写发现指针);
# 随机端口后用户无从得知端口, 由 `endpoint` 子命令读指针告知 (见 __main__)。
DEFAULT_HTTP_PORT = 0
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
    http_host: str = DEFAULT_HTTP_HOST  # 强制回环 (127.0.0.0/8 或 ::1, 校验层限定; 见 _check_http_host)
    http_port: int = DEFAULT_HTTP_PORT
    lease_ttl_s: float = DEFAULT_LEASE_TTL_S
    heartbeat_interval_s: float = DEFAULT_HEARTBEAT_INTERVAL_S
    notify_timeout_s: float = DEFAULT_NOTIFY_TIMEOUT_S
    adapter_include: Tuple[str, ...] = ()
    adapter_exclude: Tuple[str, ...] = ()
    # S14/D13: 开机自启意图 (默认 true = 未显式关过即注册)。这是自启的**唯一裁决权**,
    # 由 POST /autostart 写; run --autostart 只表示「本次拉起顺带幂等注册」, 不带取值。
    # 用户显式关过 (false) 后, 再被拉起也不装回。
    autostart: bool = True


# ---- 校验 (黄金法则 4: 全量 + 聚合) ----

# 字段按"契约形态"分组: 时间/大小是复合串 (盘上) 但内存是物理量 (秒/字节), 校验器负责
# 串洗 -> 数值 (读侧同时兼容旧式裸数值); 列表字段 (adapter_*) 单独处理 (元素全为 str 即可)。
_DURATION_FIELDS = (
    "sample_interval",
    "flush_interval_s",
    "lease_ttl_s",
    "heartbeat_interval_s",
    "notify_timeout_s",
)
_SIZE_FIELDS = ("flush_delta_bytes", "notify_threshold_bytes")
_INT_FIELDS = ("http_port", )
# http_host 独立于普通字符串字段: 校验不只查非空, 还强制回环 (见 _check_http_host)
_HOST_FIELDS = ("http_host", )
_LIST_FIELDS = ("adapter_include", "adapter_exclude")
_BOOL_FIELDS = ("autostart", )
_KNOWN_FIELDS = frozenset(_DURATION_FIELDS + _SIZE_FIELDS + _INT_FIELDS + _HOST_FIELDS + _LIST_FIELDS + _BOOL_FIELDS)

# 端口区间 (S13/D9): 0 合法 = 内核分配随机端口; 下限从 1 放开到 0
_PORT_RANGE = (0, 65535)


def _reject_bool(name: str, value: Any) -> Optional[str]:
    """bool 是 int 子类 —— 数值字段收到 True/False 一律拒绝 (sample_interval: true 不是 5S)."""
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
    if name == "http_port" and not (_PORT_RANGE[0] <= value <= _PORT_RANGE[1]):
        errors.append(f"{name}: 期望端口 0-65535 (0 = 内核分配随机端口), 收到 {value}")
        return None
    return value


def _check_duration(name: str, value: Any, errors: list[str]) -> Optional[float]:
    """时间字段: 复合串 ("30S"/"5M") 或旧式裸秒数 -> 秒 (D13 迁移语义在 units.parse_duration)."""
    bad = _reject_bool(name, value)
    if bad:
        errors.append(bad)
        return None
    try:
        seconds = parse_duration(value)
    except UnitError as e:
        errors.append(f"{name}: {e}")
        return None
    if not math.isfinite(seconds):
        errors.append(f"{name}: 期望有限数值, 收到 {value!r}")
        return None
    if seconds <= 0:
        errors.append(f"{name}: 期望正数 (>0), 收到 {value!r}")
        return None
    return seconds


def _check_size(name: str, value: Any, errors: list[str]) -> Optional[int]:
    """大小字段: 复合串 ("1MiB") 或旧式裸字节数 -> 字节."""
    bad = _reject_bool(name, value)
    if bad:
        errors.append(bad)
        return None
    try:
        nbytes = parse_size(value)
    except UnitError as e:
        errors.append(f"{name}: {e}")
        return None
    if nbytes <= 0:
        errors.append(f"{name}: 期望正数 (>0), 收到 {value!r}")
        return None
    return nbytes


def _check_str(name: str, value: Any, errors: list[str]) -> Optional[str]:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{name}: 期望非空字符串, 收到 {value!r}")
        return None
    return value.strip()


def _check_http_host(name: str, value: Any, errors: list[str]) -> Optional[str]:
    """http_host: 非空串 + **回环约束** (127.0.0.0/8 或 ::1, 及约定的 "localhost").

    「控制面强制绑定回环地址」是 server/storage docstring 明示的安全不变式 (token
    明文落盘, 不提供跨机访问面) —— 校验层必须兑现绑定承诺: 放开 0.0.0.0/局域网地址
    即对 LAN 暴露单因素 Bearer 控制面。约束在 validate_payload 一处生效, 启动加载
    (load_config) 与 PUT /config 两个入口共用, 配置者写了非回环地址就 fail-fast
    聚合报错, 不静默回落默认值 (黄金法则 4)。
    """
    text = _check_str(name, value, errors)
    if text is None:
        return None
    try:
        loopback = ipaddress.ip_address(text).is_loopback
    except ValueError:
        loopback = text.lower() == "localhost"  # RFC 6761 保留名, 按定义只解析到回环
    if not loopback:
        errors.append(f"{name}: 控制面强制绑定回环地址 (127.0.0.0/8 或 ::1), 收到 {value!r}")
        return None
    return text


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


def _check_bool_field(name: str, value: Any, errors: list[str]) -> Optional[bool]:
    """布尔字段 (autostart): 只收真 bool —— 0/1/"true" 一律拒。

    与数值字段的 `_reject_bool` 反向对称: 那边拒 bool 混进数值, 这边只认 bool。
    刻意不收 0/1: 「用户显式关过」是一个语义事件, 写成数字会让读侧猜不透是不是
    被别的工具顺手改的 (黄金法则 4: 不静默猜测)。
    """
    if not isinstance(value, bool):
        errors.append(f"{name}: 期望布尔 true/false, 收到 {type(value).__name__} {value!r}")
        return None
    return value


def validate_payload(payload: Mapping[str, Any]) -> Tuple[Optional[Config], Tuple[str, ...]]:
    """全量校验配置载荷: 成功返回 (Config, ()); 失败返回 (None, 聚合错误元组).

    校验面: 未知键 (黄金法则 4 口径 —— 拒绝拼写错误/过期键, 不静默忽略) /
    类型 (时间/大小为复合串或旧式裸数值, 端口整数, 数值字段显式拒 bool) / 范围 (正数、
    端口 0-65535、有限数值、字节为整数、http_host 强制回环 —— 见 _check_http_host)。
    逐键独立校验, 错误聚合一次报齐 (不止第一个错)。
    """
    if not isinstance(payload, Mapping):
        return None, (f"配置载荷必须是映射, 收到 {type(payload).__name__}", )
    errors: list[str] = []
    overrides: dict[str, Any] = {}
    for key in payload:
        if key not in _KNOWN_FIELDS:
            errors.append(f"未知配置键: {key!r} (已知: {', '.join(sorted(_KNOWN_FIELDS))})")
    for name in _DURATION_FIELDS:
        if name in payload:
            ok = _check_duration(name, payload[name], errors)
            if ok is not None:
                overrides[name] = ok
    for name in _SIZE_FIELDS:
        if name in payload:
            ok = _check_size(name, payload[name], errors)
            if ok is not None:
                overrides[name] = ok
    for name in _INT_FIELDS:
        if name in payload:
            ok = _check_int(name, payload[name], errors)
            if ok is not None:
                overrides[name] = ok
    for name in _HOST_FIELDS:
        if name in payload:
            ok = _check_http_host(name, payload[name], errors)
            if ok is not None:
                overrides[name] = ok
    for name in _LIST_FIELDS:
        if name in payload:
            ok = _check_str_list(name, payload[name], errors)
            if ok is not None:
                overrides[name] = ok
    for name in _BOOL_FIELDS:
        if name in payload:
            ok = _check_bool_field(name, payload[name], errors)
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
    """Config -> config.yml/契约载荷 (PUT /config 回显与 save_config 共用).

    S7/D13: 时间/大小**只写复合串** (``"30S"`` / ``"10MiB"``) —— 写侧凭空数值, 盘上因此
    不会出现「数值 + 独立单位」的第二形态; 内存里的物理量在这一次转换里唯一地格式化成串。
    """
    payload: dict[str, Any] = {}
    for f in fields(config):
        value = getattr(config, f.name)
        if f.name in _DURATION_FIELDS:
            payload[f.name] = format_duration(value)
        elif f.name in _SIZE_FIELDS:
            payload[f.name] = format_size(value)
        else:
            payload[f.name] = value
    return payload


def migrate_legacy_config(path: str) -> Optional[str]:
    """把旧式裸数值一次性改写成复合串 (S7/D13 的"一次性迁移"落点).

    触发条件很窄: 盘上确有**时间/大小键处于非字符串形态** (D13 之前的 ``5.0`` / ``1048576``)。
    此时重新校验 -> 原子重写整份 config.yml -> 返回一句人读消息 (调用方打进启动日志)。

    刻意只写这一种情况: 没有旧值就**不碰文件** —— 不能借着"迁移"把用户的部分配置写成
    全量默认值, 也不能让每次启动都重写一遍 (那会把 mtime 变成无信息的时间戳噪声)。

    解析/校验失败 -> 返回 None 并保持文件原样: fail-fast 由调用方 (启动路径的
    `_load_config_or_fail`) 负责逐条报错, 本函数不吞错也不试图"修好"坏配置。
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    except (FileNotFoundError, OSError, yaml.YAMLError):
        return None
    if not isinstance(raw, Mapping):
        return None
    legacy = [name for name in _DURATION_FIELDS + _SIZE_FIELDS if name in raw and not isinstance(raw[name], str)]
    if not legacy:
        return None
    config, errors = validate_payload(raw)
    if config is None:
        return None  # 坏配置留给启动路径报错 (不在这里二次改写磁盘)
    save_config(path, config)
    return f"旧式数值配置已迁移为复合串 ({', '.join(sorted(legacy))}) -> {path}"


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
