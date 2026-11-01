"""网卡读数来源单点 (issue 26-10-20-2345, 方案 E): Windows 原生 GetIfTable2 整表读取.

背景: psutil 的 net_io_counters + net_if_stats 每轮两次调用实测约 149-177 次控制操作
(Windows 实现 = GetAdaptersAddresses 约 80 次 + 每适配器 GetIfEntry2 约 2 次), 5s 一轮
即 30-35 次/秒; 常驻进程任务管理器「I/O 其它」累计值因此单调巨大 (35h 实测 780 万),
排查时极易误读成磁盘活动.

替代读数的三条不变式 (违反任何一条即回退):
1. **接口全集口径不变**: 名单取 psutil.net_if_stats() 的键集 (与 psutil 同一个
   GetAdaptersAddresses 全集), 名单缓存复用; 每轮一次 GetIfTable2 整表读取 (实测约
   17 次控制操作), 按别名精确匹配把名单映射到表行. 候选全集与 psutil 路径完全一致,
   AdapterFilter 看到的键与键序语义不变.
2. **isup 判定同式**: OperStatus == IfOperStatusUp 且 AdminStatus == NET_IF_ADMIN_STATUS_UP
   (与 psutil net_if_stats 逐字同式).
3. **fail-safe 回退**: 布局断言不过 / 启动交叉校验不过 / 运行期读取异常 -> 当轮改走
   psutil 两次调用路径. 最坏情况回到现状, 不会更糟 (计数同源于 NSI, 跨源差分无碍).

拓扑感知: 表行 InterfaceLuid 集合相对上次整表读发生变化 (网卡插拔/驱动事件) -> 立即
重取名单 -> 新网卡下一轮即被感知; 表内别名无法唯一映射名单名时同样刷新后重试一次,
仍失败则当轮回退 psutil (此时每轮多一次名单刷新, 有限自愈, 见 NicMapper.read).

并发口径: 采样循环单线程 (黄金法则 5), 名单缓存与轮内 pending 快照不加锁.

平台口径: 本模块在 Linux/macOS 可安全导入 (布局常量与纯函数不触碰 win32 API);
WinDLL 懒加载, 只有 read_table_rows 及其上游是 win32 专属. 非Windows 平台
default_providers 直接返回 psutil 对 (无此病灶, 不优化).
"""

from __future__ import annotations

import ctypes
import logging
import sys
from dataclasses import dataclass
from typing import Callable, Iterable, Mapping, Optional

logger = logging.getLogger("gtm.nic")

# ---- SDK 常量 (值来自 Win32 头; 模块顶层不触碰 win32 API, 双平台可导入) ----

IF_OPER_STATUS_UP = 1
NET_IF_ADMIN_STATUS_UP = 1

# GetIfTable2 表缓冲: ULONG NumEntries + 4 字节对齐 (行数组按 8 对齐) -> 行起始偏移
_TABLE_ROWS_OFFSET = 8

# Alias/Description 字段字节宽: (IF_MAX_STRING_SIZE + 1) 个 wchar, 每 wchar 2 字节
_ALIAS_BYTES = 514

# 交叉校验容差: 原生读在 psutil 读之后 (计数只增), 差值 = 校验窗口内真实流量;
# 上界 max(16 MiB, 2%) —— 布局错位读出的是天文数字/错列, 远超此界
_VALIDATE_ABS_SLACK = 16 * 1024 * 1024
_VALIDATE_REL_SLACK = 0.02

# MIB_IF_ROW2 布局断言 (learn.microsoft.com ns-netioapi-mib-if-row2, Win Vista+):
# 1 字节位域 (8 个 BOOLEAN:1 打包 1 字节) + OperStatus 4 字节对齐补 3, 计数区 18 个
# ULONG64. Alias/Description 声明为等宽字节数组 —— ctypes.c_wchar 在 Linux 是 4 字节,
# 直接用 wchar 数组会把双平台布局改岔; 手工按 utf-16-le 解码保证 sizeof 恒等.
_MIB_IF_ROW2_SIZE = 1352


class _MibIfRow2(ctypes.Structure):
    # 全部字段用显式定宽类型 (c_uint32/c_uint64): c_ulong 在 LP64 Linux 是 8 字节而
    # Windows 是 4, 用它会把双平台布局改岔 (import 期断言会拦, 2026-11-01 WSL 实证)
    _fields_ = [
        ("InterfaceLuid", ctypes.c_uint64),
        ("InterfaceIndex", ctypes.c_uint32),
        ("InterfaceGuid", ctypes.c_ubyte * 16),
        ("Alias", ctypes.c_ubyte * _ALIAS_BYTES),
        ("Description", ctypes.c_ubyte * _ALIAS_BYTES),
        ("PhysicalAddressLength", ctypes.c_uint32),
        ("PhysicalAddress", ctypes.c_ubyte * 32),
        ("PermanentPhysicalAddress", ctypes.c_ubyte * 32),
        ("Mtu", ctypes.c_uint32),
        ("Type", ctypes.c_uint32),
        ("TunnelType", ctypes.c_uint32),
        ("MediaType", ctypes.c_uint32),
        ("PhysicalMediumType", ctypes.c_uint32),
        ("AccessType", ctypes.c_uint32),
        ("DirectionType", ctypes.c_uint32),
        ("InterfaceAndOperStatusFlags", ctypes.c_ubyte * 1),
        ("OperStatus", ctypes.c_uint32),
        ("AdminStatus", ctypes.c_uint32),
        ("MediaConnectState", ctypes.c_uint32),
        ("NetworkGuid", ctypes.c_ubyte * 16),
        ("ConnectionType", ctypes.c_uint32),
        ("TransmitLinkSpeed", ctypes.c_uint64),
        ("ReceiveLinkSpeed", ctypes.c_uint64),
        ("InOctets", ctypes.c_uint64),
        ("InUcastPkts", ctypes.c_uint64),
        ("InNUcastPkts", ctypes.c_uint64),
        ("InDiscards", ctypes.c_uint64),
        ("InErrors", ctypes.c_uint64),
        ("InUnknownProtos", ctypes.c_uint64),
        ("InUcastOctets", ctypes.c_uint64),
        ("InMulticastOctets", ctypes.c_uint64),
        ("InBroadcastOctets", ctypes.c_uint64),
        ("OutOctets", ctypes.c_uint64),
        ("OutUcastPkts", ctypes.c_uint64),
        ("OutNUcastPkts", ctypes.c_uint64),
        ("OutDiscards", ctypes.c_uint64),
        ("OutErrors", ctypes.c_uint64),
        ("OutUcastOctets", ctypes.c_uint64),
        ("OutMulticastOctets", ctypes.c_uint64),
        ("OutBroadcastOctets", ctypes.c_uint64),
        ("OutQLen", ctypes.c_uint64),
    ]


# 布局守卫: 字段增删/对齐变化在 import 期即 fail-fast (双平台同值)
assert ctypes.sizeof(_MibIfRow2) == _MIB_IF_ROW2_SIZE, (
    f"MIB_IF_ROW2 布局漂移: sizeof={ctypes.sizeof(_MibIfRow2)} (期望 {_MIB_IF_ROW2_SIZE})"
)
assert _MibIfRow2.OperStatus.offset == 1156, f"OperStatus.offset={_MibIfRow2.OperStatus.offset} (期望 1156)"
assert _MibIfRow2.AdminStatus.offset == 1160, f"AdminStatus.offset={_MibIfRow2.AdminStatus.offset} (期望 1160)"
assert _MibIfRow2.InOctets.offset == 1208, f"InOctets.offset={_MibIfRow2.InOctets.offset} (期望 1208)"
assert _MibIfRow2.OutOctets.offset == 1280, f"OutOctets.offset={_MibIfRow2.OutOctets.offset} (期望 1280)"


@dataclass(frozen=True)
class IoRow:
    """gtm.sampler.NicIo 协议的结构化实现 (计数器)."""

    bytes_sent: int
    bytes_recv: int


@dataclass(frozen=True)
class StatsRow:
    """gtm.sampler.NicStats 协议的结构化实现 (状态)."""

    isup: bool


@dataclass(frozen=True)
class IfRowView:
    """表行的语言无关视图 (read_table_rows 从 ctypes 行提取; 测试可直接构造)."""

    luid: int
    name: str
    isup: bool  # OperStatus==Up 且 AdminStatus==Up (psutil net_if_stats 同式)
    out_octets: int
    in_octets: int


@dataclass(frozen=True)
class NicSnapshot:
    """一次整表读取的完整产出 (counters/stats 同源同拍, 供轮内 pending 复用)."""

    counters: Mapping[str, IoRow]
    stats: Mapping[str, StatsRow]
    luids: frozenset[int]


class MappingError(Exception):
    """表行无法唯一映射到接口名单 (拓扑漂移或别名失配) —— 调用方刷新重试/回退."""


def decode_alias(raw: bytes) -> str:
    """utf-16-le 定长字节数组 -> 去尾部 NUL 的名称 (纯函数)."""
    return bytes(raw).decode("utf-16-le", errors="replace").split("\x00")[0]


def row_views(rows: Iterable[object]) -> tuple[list[IfRowView], frozenset[int]]:
    """表行序列 (ctypes 行或同构替身) -> 视图列表 + LUID 集合 (纯函数, 双平台可测)."""
    views = [
        IfRowView(
            luid=int(row.InterfaceLuid),
            name=decode_alias(row.Alias),
            isup=(row.OperStatus == IF_OPER_STATUS_UP and row.AdminStatus == NET_IF_ADMIN_STATUS_UP),
            out_octets=int(row.OutOctets),
            in_octets=int(row.InOctets),
        ) for row in rows
    ]
    return views, frozenset(v.luid for v in views)


# ---- win32 专属: 整表读取 (Linux/macOS 不进入) ----

_iphlpapi: Optional[ctypes.WinDLL] = None


def _iph() -> ctypes.WinDLL:
    """Iphlpapi 懒加载; x64 直调必须显式 argtypes/restype (pitfalls/backend/ctypes-x64-argtypes)."""
    global _iphlpapi
    if _iphlpapi is None:
        lib = ctypes.WinDLL("Iphlpapi.dll")
        lib.GetIfTable2.restype = ctypes.c_uint32
        lib.GetIfTable2.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
        lib.FreeMibTable.restype = None
        lib.FreeMibTable.argtypes = [ctypes.c_void_p]
        _iphlpapi = lib
    return _iphlpapi


def read_table_rows() -> tuple[list[IfRowView], frozenset[int]]:
    """GetIfTable2 一次整表读取 (生产 win32 路径; 实测约 17 次控制操作/次)."""
    lib = _iph()
    table = ctypes.c_void_p()
    rc = lib.GetIfTable2(ctypes.byref(table))
    if rc != 0 or not table.value:
        raise OSError(f"GetIfTable2 失败: rc={rc}")
    try:
        num = ctypes.cast(table, ctypes.POINTER(ctypes.c_uint32)).contents.value
        row_size = ctypes.sizeof(_MibIfRow2)
        rows = [
            ctypes.cast(ctypes.c_void_p(table.value + _TABLE_ROWS_OFFSET + i * row_size),
                        ctypes.POINTER(_MibIfRow2)).contents for i in range(num)
        ]
        return row_views(rows)
    finally:
        lib.FreeMibTable(table)


# ---- 名单缓存与映射 (纯 Python, 双平台可测) ----


class NicMapper:
    """接口名单 (psutil 全集, 缓存) -> 表行映射.

    名单重取时机: 表行 LUID 集合变化 (拓扑漂移) 或映射失败 (刷新后重试一次).
    """
    def __init__(self, universe_provider: Callable[[], Mapping[str, object]]) -> None:
        self._universe_provider = universe_provider
        self._names: tuple[str, ...] = ()
        self._luids: Optional[frozenset[int]] = None

    def refresh(self) -> None:
        """重取接口名单 (一次 psutil.net_if_stats, 实测约 85 次控制操作)."""
        self._names = tuple(str(name) for name in self._universe_provider().keys())
        self._luids = None

    def read(self, rows: list[IfRowView], luids: frozenset[int]) -> NicSnapshot:
        """一次整表读 -> 名单口径的 NicSnapshot; 映射失败刷新重试一次, 仍败抛 MappingError."""
        if self._luids is None or luids != self._luids:
            self.refresh()
            self._luids = luids
        try:
            return self._map(rows)
        except MappingError:
            pass
        # 名单可能过期 (拓扑刚变): 重取后重试一次; 仍失败则本轮由调用方回退 psutil,
        # _luids 留 None 使下一轮继续刷新 (有限自愈, 名单与表一致后停止)
        self.refresh()
        snap = self._map(rows)  # 可能抛 MappingError
        self._luids = luids
        return snap

    def _map(self, rows: list[IfRowView]) -> NicSnapshot:
        by_name: dict[str, IfRowView] = {}
        for v in rows:
            if v.name in by_name:
                if v.name in self._names:  # 名单名命中多行: 映射不可信 (表内别名撞车)
                    raise MappingError(f"表内别名重复: {v.name!r}")
            by_name[v.name] = v
        counters: dict[str, IoRow] = {}
        stats: dict[str, StatsRow] = {}
        for name in self._names:
            view = by_name.get(name)
            if view is None:
                raise MappingError(f"名单网卡缺表行: {name!r}")
            counters[name] = IoRow(bytes_sent=view.out_octets, bytes_recv=view.in_octets)
            stats[name] = StatsRow(isup=view.isup)
        return NicSnapshot(counters=counters, stats=stats, luids=frozenset(v.luid for v in rows))


# ---- 启动交叉校验 (纯函数) ----


def _pair_consistent(native: NicSnapshot, ps_counters: Mapping[str, object], ps_stats: Mapping[str, object]) -> bool:
    """原生快照 vs psutil 读数逐接口核对: 键集相等 / isup 相等 / 计数单调不减且增量有界."""
    if set(native.counters) != set(ps_counters) or set(native.stats) != set(ps_stats):
        return False
    for name, pio in ps_counters.items():
        nio = native.counters[name]
        for p_val, n_val in ((pio.bytes_recv, nio.bytes_recv), (pio.bytes_sent, nio.bytes_sent)):
            if n_val < p_val:  # 原生读在后, 只允许不减 (中途计数器重置属罕见, 回退即可)
                return False
            if n_val - p_val > max(_VALIDATE_ABS_SLACK, _VALIDATE_REL_SLACK * p_val):
                return False
    for name, ps in ps_stats.items():
        if native.stats[name].isup != ps.isup:
            return False
    return True


# ---- 生产 provider 对 (轮内单次整表读 + 运行期回退) ----


class _NativePair:
    """counters/stats 两个 provider 共享一次整表读; 任何读取异常当轮回退 psutil.

    轮内节拍: sample_once 先调 counters() (触发整表读, 快照入 pending), 再调 stats()
    (消费 pending, 不再读表). 单独调 stats() 也会自读一次. 告警限频: 首错必告,
    此后连续失败每 _REPEAT_WARNING_EVERY 轮重复一次 (默认约 1 小时), 成功即清零.
    """

    _REPEAT_WARNING_EVERY = 720  # 5s/轮 -> 约 1 小时

    def __init__(
        self,
        source: Callable[[], NicSnapshot],
        psutil_pair: tuple[Callable[[], Mapping[str, object]], Callable[[], Mapping[str, object]]],
    ) -> None:
        self._source = source
        self._ps_counters, self._ps_stats = psutil_pair
        self._pending: Optional[NicSnapshot] = None
        self._fails = 0

    def counters(self) -> Mapping[str, IoRow]:
        try:
            snap = self._source()
        except Exception as exc:
            self._fails += 1
            self._warn_if_due(exc)
            return self._ps_counters()  # type: ignore[return-value]
        self._fails = 0
        self._pending = snap
        return snap.counters

    def stats(self) -> Mapping[str, StatsRow]:
        pending, self._pending = self._pending, None
        if pending is not None:
            return pending.stats
        try:
            snap = self._source()
        except Exception as exc:
            self._fails += 1
            self._warn_if_due(exc)
            return self._ps_stats()  # type: ignore[return-value]
        self._fails = 0
        return snap.stats

    def _warn_if_due(self, exc: Exception) -> None:
        if self._fails == 1 or self._fails % self._REPEAT_WARNING_EVERY == 0:
            logger.warning("原生整表读取失败, 本轮回退 psutil (累计 %d 次): %s", self._fails, exc)


def _native_pair(
    psutil_pair: tuple[Callable[[], Mapping[str, object]], Callable[[], Mapping[str, object]]],
) -> Optional[tuple[Callable[[], Mapping[str, IoRow]], Callable[[], Mapping[str, StatsRow]]]]:
    """构建并校验原生对; 任何失败返回 None (调用方回退 psutil 并记决策日志)."""
    try:
        mapper = NicMapper(psutil_pair[1])
        pair = _NativePair(lambda: mapper.read(*read_table_rows()), psutil_pair)
        # 校验顺序: psutil 先读, 原生后读 -> 原生计数只增不减 (单调校验的前提)
        ps_c = psutil_pair[0]()
        ps_s = psutil_pair[1]()
        snap = mapper.read(*read_table_rows())
    except Exception:
        return None
    if not _pair_consistent(snap, ps_c, ps_s):
        return None
    return pair.counters, pair.stats


_RESOLVED: Optional[tuple[Callable[[], Mapping[str, object]], Callable[[], Mapping[str, object]]]] = None


def _resolve(win32: bool, psutil_pair: tuple) -> tuple:
    """平台决议: win32 走原生对 (校验不过回退), 其余平台直接 psutil (无此病灶)."""
    native = _native_pair(psutil_pair) if win32 else None
    if native is not None:
        logger.info("网卡读数走原生 GetIfTable2 整表路径 (每轮一次整表读, 约 17 次控制操作)")
        return native
    if win32:
        logger.warning("原生整表路径不可用或启动校验未过, 网卡读数回退 psutil 两次调用路径")
    else:
        logger.info("网卡读数走 psutil 路径 (非 Windows 平台无此病灶)")
    return psutil_pair


def _resolved(psutil_pair: tuple) -> tuple:
    global _RESOLVED
    if _RESOLVED is None:
        _RESOLVED = _resolve(sys.platform.startswith("win"), psutil_pair)
    return _RESOLVED


def default_providers(
    psutil_pair: tuple[Callable[[], Mapping[str, object]], Callable[[], Mapping[str, object]]],
) -> tuple[Callable[[], Mapping[str, object]], Callable[[], Mapping[str, object]]]:
    """Sampler 默认注入点 (懒决议, 进程内只决议一次).

    返回的两个包装在**首次被调用**时才做平台决议与启动校验 —— 构造 Sampler 本身
    不触碰真实系统 API, restore-only 场景与全部注入替身的单测保持 hermetic.
    """
    def counters() -> Mapping[str, object]:
        return _resolved(psutil_pair)[0]()

    def stats() -> Mapping[str, object]:
        return _resolved(psutil_pair)[1]()

    return counters, stats
