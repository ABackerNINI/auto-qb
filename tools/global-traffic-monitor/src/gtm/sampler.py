"""采样器: psutil 全适配器采样 + 当日累计 + 计数器重置/崩溃恢复 (S1 实现).

每次采样 (sample_once; 休眠循环随 S2 run 命令落地, 节奏取 sample_interval
默认 5s) 读全适配器计数器 (默认注入点经 nic.default_providers 平台决议: Windows 原生
GetIfTable2 整表单读, 非 Windows/回退为 psutil 两次调用, 见 issue 26-10-20-2345),
按 AdapterFilter 过滤后按**逐网卡基线**记账, 维护三条状态:

- 逐网卡基线 (_nic_base): {网卡名: (last_up, last_down)}; 每轮对选中卡逐卡做差
  delta = cur - last 后求和入账。新出现的卡只立基线 (历史累计不入账); 消失的卡
  **保留记忆**, 回来后按真实增量差分; 仅按 7 天 TTL 清理久未见条目 (_nic_seen)。
- 计数器重置: 单卡单方向 本次 < 上次 -> 该卡该侧 delta 记 0 并 WARNING, 不产生负
  流量; 只影响该卡该侧, 其他卡/另一侧正常计。
- 当日累计 (本地日界): 跨天 00:00 硬切 —— 累计清零, 新的一天从 0 起计
  (SampleResult.day_rolled=True 上报, 旧行的最终落盘属 S2 storage)。硬切带方向检查:
  只有日界**前进**才切; 挂钟回跳跨日界记 WARNING 且保持累计不清零 (采样日钉在原
  日界, 与 restore 的未来日期降级同一防线, 宁可少报不重置).

崩溃恢复 (S2 run 启动链路接入, 两步有序):
- restore(snapshot): 用 state.json 载荷 (本模块 snapshot() 产出, S2 负责读写)
  恢复逐卡基线与当日累计; 支持 v2 (逐卡基线) 与 v1 (仅当日累计, 逐卡基线置空 ->
  首轮每卡重新立基线, 少报不超过一个采样间隔) 两种载荷; 载荷缺失/损坏/版本不符/
  快照日期在未来 -> 降级路径 (告警说明 + 逐卡基线置空 -> 下次采样即 baseline,
  停机窗口丢流量).
- restore_from_dat(text): 降级路径的当日累计兜底 —— 从 TM 兼容 dat 文本取今天
  行的 KB 累计 (解析规则与 auto-qb curves.py parse_history_dat 逐字一致: 每行
  "YYYY/MM/DD 上传KB/下载KB", 首行 lines: 说明与空行忽略; 行序不敏感, 取最后
  一条匹配今天的行). 注意: 只恢复累计, 计数器基线仍取当前值 (计划 S1 口径).

可观测性: 每次采样返回 SampleResult (当日累计/本次 delta/是否重置/是否跨天/
是否 baseline/告警列表), 调用方 (S2 主循环) 无需窥探内部状态; 降级与重置同时
走 logger WARNING, 双通道可观测.

过滤集变化说明: 若某次采样没有任何网卡通过过滤 (include/exclude/loopback/down
配置变化或网卡全部 down), 本轮按 0 入账并告警, 但**不改写任何卡的记忆**; 过滤
条件恢复后按逐卡记忆差分, 缺失窗口的累计不会打进恢复后首个 delta。从未被观测过
的卡 (新插入/此前一直被过滤) 只立基线 —— 无法区分历史累计与缺口流量, 按 I6 少报.
"""

from __future__ import annotations

import logging
import math
import re
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Callable, Mapping, Optional, Protocol

import psutil

from .config import DEFAULT_SAMPLE_RATE_WARN_BPS
from .nic import default_providers

logger = logging.getLogger("gtm.sampler")

# 采样周期默认值 (s); 休眠循环在 S2 run 命令, 此处仅作为默认口径单点
DEFAULT_SAMPLE_INTERVAL = 5.0

# S5 (C-prime): 速率判定的 dt 钳制倍数 —— eff_dt = min(dt, 3 × 当前采样间隔).
# 长 gap (休眠/断连) 不把注入量摊薄到阈值以下 (计划 §06.3)。
WARN_DT_CLAMP_FACTOR = 3

# 重启后单调钟断代, 用 state 的 last_sample_wall 兜底时允许的最大差值 (7 天);
# 超出视为时钟跳变/陈旧 state, 跳过本轮速率判定 (只影响告警, 不影响入账)。
_MAX_RESTART_DT_S = 7 * 24 * 3600.0

# state.json 快照载荷版本 (S2 storage 消费; 升级载荷时 +1 并在此注明差异)
# v2: 新增 nic_baseline (逐卡基线); last_up/last_down 降级为各卡求和 (兼容/观测);
#     v1 载荷仍被接受 (保留当日累计, 逐卡基线置空 -> 首轮每卡重新立基线)
SNAPSHOT_VERSION = 2

# 逐卡记忆 TTL (天): 超过此天数未被选中的条目清理, 避免 state 无界增长
# (8 天后回来的卡按新卡处理, delta 0; 见计划 §12.1 R7)
_NIC_BASE_TTL_DAYS = 7

# 回环网卡名判别: Linux "lo" / macOS "lo0" / Windows "Loopback Pseudo-Interface 1"
_LOOPBACK_RE = re.compile(r"^(lo|lo\d+|loopback\b.*)$", re.IGNORECASE)

# dat 行格式单点 (本模块 restore_from_dat 与 storage.DatStore.load 共用):
# "YYYY/MM/DD 上传KB/下载KB", 与 auto-qb curves.py parse_history_dat 的正则逐字一致
DAT_ROW_RE = re.compile(r"^(\d{4})/(\d{1,2})/(\d{1,2})\s+(\d+)/(\d+)$")

# dat 数值单位: KB, 按 1024 字节换算 (与 curves.py 的 KB 常量同值)
_KB = 1024


class NicIo(Protocol):
    """psutil snetio 的结构性子集 (本模块只用这两个字段)."""

    bytes_sent: int
    bytes_recv: int


class NicStats(Protocol):
    """psutil snicstats 的结构性子集 (isup 判定 down 网卡)."""

    isup: bool


def is_loopback(name: str) -> bool:
    """网卡名是否为回环: Linux lo / macOS lo0 / Windows Loopback Pseudo-Interface N."""
    return bool(_LOOPBACK_RE.match(name))


def _compile_optional(pattern: Optional[str]) -> Optional[re.Pattern[str]]:
    return re.compile(pattern) if pattern else None


def _opt_int(value: object) -> Optional[int]:
    """可选非负整数: None 原样; 其余必须可转 int 且非负 (否则抛, 由调用方归为损坏)."""
    if value is None:
        return None
    iv = int(value)  # type: ignore[call-overload]
    if iv < 0:
        raise ValueError(f"负值: {value!r}")
    return iv


def _parse_epoch(raw: object) -> Optional[float]:
    """state 的 epoch 秒 (last_sample_wall): 非法/缺失/非正 -> None (降级而非报错)."""
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return None
    value = float(raw)
    if not math.isfinite(value) or value <= 0:
        return None
    return value


def _parse_last_spike(raw: object) -> Optional[dict[str, object]]:
    """state 的 last_spike: 结构非法 -> None (旧 v2 载荷缺该键、或手工改坏都走这里).

    只接受本模块写出的结构 (ts/dt_s/eff_dt_s/threshold_bps/items), 逐项重建而不是
    原样回填 —— state 文件是外部可改的输入面, 不把未知键/非法数值带进 /status。
    """
    if not isinstance(raw, Mapping):
        return None
    ts = raw.get("ts")
    if not isinstance(ts, str) or not ts.strip():
        return None
    try:
        dt_s = float(raw["dt_s"])
        eff_dt_s = float(raw["eff_dt_s"])
        threshold_bps = int(raw["threshold_bps"])
    except (KeyError, TypeError, ValueError):
        return None
    if not (math.isfinite(dt_s) and math.isfinite(eff_dt_s)) or dt_s <= 0 or eff_dt_s <= 0 or threshold_bps <= 0:
        return None
    items_raw = raw.get("items")
    if not isinstance(items_raw, list) or not items_raw:
        return None
    items: list[dict[str, object]] = []
    for entry in items_raw:
        if not isinstance(entry, Mapping):
            return None
        nic, direction = entry.get("nic"), entry.get("dir")
        if not isinstance(nic, str) or not nic or not isinstance(direction, str) or direction not in ("up", "down"):
            return None
        try:
            cur = int(entry["cur"])
            last = int(entry["last"])
            delta = int(entry["delta"])
            rate_bps = int(entry["rate_bps"])
        except (KeyError, TypeError, ValueError):
            return None
        if cur < 0 or last < 0 or delta < 0 or rate_bps < 0:
            return None
        items.append({"nic": nic, "dir": direction, "cur": cur, "last": last, "delta": delta, "rate_bps": rate_bps})
    return {
        "ts": ts,
        "dt_s": dt_s,
        "eff_dt_s": eff_dt_s,
        "threshold_bps": threshold_bps,
        "items": items,
    }


@dataclass
class AdapterFilter:
    """适配器过滤: 固定顺序判定, 任一环命中即剔除 (顺序即优先级, 文档明示).

    顺序: include (非空时白名单) -> exclude (黑名单) -> exclude_loopback ->
    exclude_down. include 只收窄候选, 不翻案后两个开关 (要收 loopback/down 网卡
    须显式关对应开关, 保守默认优先, 黄金法则 2).
    """

    include: Optional[str] = None
    exclude: Optional[str] = None
    exclude_loopback: bool = True
    exclude_down: bool = True

    def __post_init__(self) -> None:
        self._include_re = _compile_optional(self.include)
        self._exclude_re = _compile_optional(self.exclude)

    def selects(self, name: str, stats: Optional[NicStats]) -> bool:
        """单网卡判定 (stats 缺省按 up 处理: psutil 给了计数器却没给状态的网卡不收编)."""
        if self._include_re is not None and not self._include_re.search(name):
            return False
        if self._exclude_re is not None and self._exclude_re.search(name):
            return False
        if self.exclude_loopback and is_loopback(name):
            return False
        if self.exclude_down and stats is not None and not stats.isup:
            return False
        return True

    def select(
        self,
        counters: Mapping[str, NicIo],
        stats: Optional[Mapping[str, NicStats]] = None,
    ) -> dict[str, NicIo]:
        """从 psutil pernic 读数中筛出计入合计的网卡 (保持插入序)."""
        if stats is None:
            stats = {}
        return {name: io for name, io in counters.items() if self.selects(name, stats.get(name))}


@dataclass(frozen=True)
class SampleResult:
    """单次采样的可观测结果 (S2 主循环据此决定落盘/通知, 不窥探 Sampler 内部)."""

    day: date  # 本次累计所属自然日 (本地)
    day_up_bytes: int  # 当日上行累计 (含本次 delta)
    day_down_bytes: int  # 当日下行累计 (含本次 delta)
    delta_up_bytes: int  # 本次上行增量
    delta_down_bytes: int  # 本次下行增量
    counter_reset: bool  # 本次是否判定计数器重置 (delta 记 0)
    day_rolled: bool  # 本次是否跨天硬切 (累计已清零)
    baseline: bool  # 本次是否为基线样本 (无上次快照, delta 恒 0)
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def day_total_bytes(self) -> int:
        """当日上下行合计累计 (含本次 delta)."""
        return self.day_up_bytes + self.day_down_bytes


def read_counters() -> dict[str, NicIo]:
    """psutil 回退读数: 全适配器 net_io_counters (注入点, 单测替身; 生产默认经 nic 平台决议)."""
    return psutil.net_io_counters(pernic=True)  # type: ignore[no-any-return]


def read_stats() -> dict[str, NicStats]:
    """psutil 回退读数: 网卡状态 isup (注入点, 单测替身; 生产默认经 nic 平台决议)."""
    return psutil.net_if_stats()  # type: ignore[no-any-return]


class Sampler:
    """采样单元: 读 -> 过滤 -> 合计 -> delta (重置归零) -> 当日累计 (跨天硬切).

    依赖注入 (clock/counters_provider/stats_provider) 的默认路径即生产路径 (默认对经
    nic.default_providers 平台决议, 懒解析 —— 构造不触碰真实系统 API);
    休眠节拍不在本模块 (S2 run), sample_once 是单步计算, 可反复驱动.
    """
    def __init__(
        self,
        adapter_filter: Optional[AdapterFilter] = None,
        clock: Optional[Callable[[], datetime]] = None,
        counters_provider: Optional[Callable[[], Mapping[str, NicIo]]] = None,
        stats_provider: Optional[Callable[[], Mapping[str, NicStats]]] = None,
    ) -> None:
        self.filter = adapter_filter or AdapterFilter()
        self._clock = clock or datetime.now
        if counters_provider is None and stats_provider is None:
            # 生产默认: nic 平台决议 (Windows 原生 GetIfTable2 整表 / 回退 psutil), 懒解析
            counters_provider, stats_provider = default_providers(
                (read_counters, read_stats)
            )  # type: ignore[assignment]
        self._counters_provider = counters_provider or read_counters  # 单侧注入缺侧直接落 psutil 回退对
        self._stats_provider = stats_provider or read_stats
        self._day: Optional[date] = None
        self._day_up = 0
        self._day_down = 0
        # 逐网卡基线 {网卡名: (last_up, last_down)} 与最近被选中的时刻 (仅 TTL 用)
        self._nic_base: dict[str, tuple[int, int]] = {}
        self._nic_seen: dict[str, datetime] = {}
        # restore() 是否接受了合法载荷 (含 v1): S2 recover 据此决定是否走 dat 兜底
        self._state_restored = False
        # S5 (C-prime): 速率判定时间基线。_last_mono 不落盘 (单调钟跨进程断代);
        # _last_sample_wall 落盘, 供重启后首轮 dt 兜底; _last_spike 只留最近一轮越界记录
        self._last_mono: Optional[float] = None
        self._last_sample_wall: Optional[float] = None
        self._last_spike: Optional[dict[str, object]] = None

    # ---- 状态出口 (S2 storage / S3 status 消费) ----

    @property
    def day(self) -> Optional[date]:
        return self._day

    @property
    def day_up_bytes(self) -> int:
        return self._day_up

    @property
    def day_down_bytes(self) -> int:
        return self._day_down

    @property
    def day_total_bytes(self) -> int:
        """当日上下行合计累积 (S4 notifier 的阈值累计以此为基数)."""
        return self._day_up + self._day_down

    @property
    def has_baseline(self) -> bool:
        """逐卡记忆是否非空 (False -> 下次采样所有选中卡都按新卡只立基线)."""
        return bool(self._nic_base)

    @property
    def state_restored(self) -> bool:
        """restore() 是否接受了合法载荷 (含 v1 升级); False -> 需走 dat 兜底 (S2 判据)."""
        return self._state_restored

    @property
    def last_spike(self) -> Optional[dict[str, object]]:
        """最近一轮越界记录 (S7 供 /status 透出); 无越界历史为 None."""
        return self._last_spike

    def _nic_base_sums(self) -> tuple[Optional[int], Optional[int]]:
        """逐卡基线的合计 (v2 载荷 last_up/last_down 的兼容/观测口径); 空表为 (None, None)."""
        if not self._nic_base:
            return None, None
        return (sum(up for up, _ in self._nic_base.values()), sum(down for _, down in self._nic_base.values()))

    def snapshot(self) -> dict[str, object]:
        """state.json 载荷 v2 (S2 负责原子读写; 未采样时逐卡基线为空表)."""
        last_up, last_down = self._nic_base_sums()
        return {
            "version": SNAPSHOT_VERSION,
            "day": self._day.isoformat() if self._day else None,
            "day_up_bytes": self._day_up,
            "day_down_bytes": self._day_down,
            "last_up_bytes": last_up,
            "last_down_bytes": last_down,
            "nic_baseline": {
                name: {
                    "up": up,
                    "down": down
                }
                for name, (up, down) in self._nic_base.items()
            },
            "last_sample_wall": self._last_sample_wall,
            "last_spike": self._last_spike,
        }

    # ---- 崩溃恢复 ----

    def restore(self, snapshot: Optional[Mapping[str, object]]) -> tuple[str, ...]:
        """从 state.json 载荷恢复 (v2 逐卡基线 / v1 兼容); 任何不合法 -> 降级路径.

        合法载荷的日期语义: 昨天 -> 当日累计从 0 起 (跨天停机, 告警一次);
        今天 -> 累计接续; 未来 -> 判损坏走降级 (时钟偏差, 宁丢不虚增).
        v1 载荷保留当日累计, 逐卡基线置空 (首轮每卡重新立基线, 不虚高).
        """
        warnings: list[str] = []
        self._day = None
        self._day_up = 0
        self._day_down = 0
        self._nic_base = {}
        self._nic_seen = {}
        self._state_restored = False
        # 速率基线不随 restore 复活: _last_mono 属本进程 (单调钟跨进程断代);
        # wall/spike 由 v2 载荷恢复, v1/降级载荷一律置 None
        self._last_mono = None
        self._last_sample_wall = None
        self._last_spike = None

        if snapshot is None:
            warnings.append("state 快照缺失: 当日累计从 dat 恢复(若有), 计数器基线取当前值, 停机窗口丢流量")
            return tuple(warnings)
        if not isinstance(snapshot, Mapping):
            warnings.append(f"state 快照损坏: 不是映射 (type={type(snapshot).__name__}), 走降级恢复")
            return tuple(warnings)

        now = self._clock()
        version = snapshot.get("version")
        if version == 1:
            accepted = self._restore_v1(snapshot, warnings, now.date())
        elif version == SNAPSHOT_VERSION:
            accepted = self._restore_v2(snapshot, warnings, now)
        else:
            warnings.append(f"state 快照版本不受支持: {version!r} (期望 1/{SNAPSHOT_VERSION}), 走降级恢复")
            return tuple(warnings)
        if not accepted:
            return tuple(warnings)

        self._state_restored = True
        if self._day is not None:
            last_up, last_down = self._nic_base_sums()
            logger.info(
                "state 快照恢复 | day=%s 累计 up=%d down=%d, 基线 up=%s down=%s", self._day.isoformat(), self._day_up,
                self._day_down, last_up, last_down
            )
        return tuple(warnings)

    def _restore_v1(self, snapshot: Mapping[str, object], warnings: list[str], today: date) -> bool:
        """v1 载荷: 只恢复当日累计, 忽略合计基线 (逐卡记忆置空); 返回是否被接受."""
        try:
            last_up_i = _opt_int(snapshot.get("last_up_bytes"))
            last_down_i = _opt_int(snapshot.get("last_down_bytes"))
        except (TypeError, ValueError) as exc:
            warnings.append(f"state 快照损坏: 字段非法 ({exc}), 走降级恢复")
            return False
        day_raw = snapshot.get("day")
        if day_raw is None:
            # 未采样过的空快照: 只有合计基线同时为 None 才自洽; day 丢了却留基线属损坏
            if last_up_i is not None or last_down_i is not None:
                warnings.append("state 快照损坏: 字段非法 (day 为 None 但基线字段有值), 走降级恢复")
                return False
            warnings.append("state v1 升级: 逐卡基线重建, 本轮 delta 记 0")
            return True
        if not self._restore_day(
            day_raw, snapshot.get("day_up_bytes"), snapshot.get("day_down_bytes"), warnings, today
        ):
            return False
        warnings.append("state v1 升级: 逐卡基线重建, 本轮 delta 记 0")
        return True

    def _restore_v2(self, snapshot: Mapping[str, object], warnings: list[str], now: datetime) -> bool:
        """v2 载荷: 恢复当日累计 + 逐卡基线 (非法条目丢弃告警, 其余保留)."""
        parsed, entry_warnings = self._parse_nic_baseline(snapshot.get("nic_baseline"))
        day_raw = snapshot.get("day")
        if day_raw is None:
            if parsed:
                warnings.append("state 快照损坏: 字段非法 (day 为 None 但逐卡基线有值), 走降级恢复")
                return False
            warnings.extend(entry_warnings)
            return True
        if not self._restore_day(
            day_raw, snapshot.get("day_up_bytes"), snapshot.get("day_down_bytes"), warnings, now.date()
        ):
            return False
        self._nic_base = parsed
        self._nic_seen = {name: now for name in parsed}
        self._last_sample_wall = _parse_epoch(snapshot.get("last_sample_wall"))
        self._last_spike = _parse_last_spike(snapshot.get("last_spike"))
        warnings.extend(entry_warnings)
        return True

    def _restore_day(self, day_raw: object, day_up: object, day_down: object, warnings: list[str], today: date) -> bool:
        """校验并落当日累计 (日界方向检查); 返回 False 表示损坏/未来日期 (调用方降级)."""
        try:
            snap_day = date.fromisoformat(str(day_raw))
            day_up_i = int(day_up)  # type: ignore[call-overload]
            day_down_i = int(day_down)  # type: ignore[call-overload]
            if day_up_i < 0 or day_down_i < 0:
                raise ValueError("当日累计为负")
        except (TypeError, ValueError) as exc:
            warnings.append(f"state 快照损坏: 字段非法 ({exc}), 走降级恢复")
            return False
        if snap_day > today:
            warnings.append(f"state 快照日期 {snap_day.isoformat()} 晚于今天 {today.isoformat()}: 时钟偏差, 走降级恢复")
            return False
        if snap_day == today:
            self._day = snap_day
            self._day_up, self._day_down = day_up_i, day_down_i
        else:
            self._day = today
            warnings.append(f"state 快照日期 {snap_day.isoformat()} 早于今天 {today.isoformat()}: 当日累计从 0 起 (跨天停机)")
        return True

    def _parse_nic_baseline(self, raw: object) -> tuple[dict[str, tuple[int, int]], list[str]]:
        """解析 v2 nic_baseline: 非法条目丢弃并告警, 其余保留 (局部损坏不拖垮恢复)."""
        if raw is None:
            return {}, []
        if not isinstance(raw, Mapping):
            return {}, [f"state 快照损坏: nic_baseline 不是映射 (type={type(raw).__name__}), 逐卡基线忽略"]
        parsed: dict[str, tuple[int, int]] = {}
        warnings: list[str] = []
        for name, entry in raw.items():
            try:
                if not isinstance(name, str):
                    raise ValueError("网卡名非字符串")
                if not isinstance(entry, Mapping):
                    raise ValueError(f"不是映射 (type={type(entry).__name__})")
                up = _opt_int(entry.get("up"))
                down = _opt_int(entry.get("down"))
                if up is None or down is None:
                    raise ValueError("up/down 缺失")
            except (TypeError, ValueError) as exc:
                warnings.append(f"state 快照损坏: nic_baseline 条目非法 ({name!r}: {exc}), 已丢弃")
                continue
            parsed[name] = (up, down)
        return parsed, warnings

    def restore_from_dat(self, text: str) -> bool:
        """降级路径的当日累计兜底: 从 TM 兼容 dat 文本恢复今天行的累计.

        只恢复累计, 计数器基线仍取当前值 (停机窗口丢流量, restore() 的告警已
        说明). 行序不敏感 (TM 倒序/工具顺序均可), 取最后一条匹配今天的行;
        无今天行 (新装/首日) 返回 False, 当日累计保持 0.
        """
        today = (self._clock()).date()
        found: Optional[tuple[int, int]] = None
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.lower().startswith("lines:"):
                continue
            m = DAT_ROW_RE.match(line)
            if not m:
                continue
            y, mo, d, up_kb, down_kb = m.groups()
            try:
                row_day = date(int(y), int(mo), int(d))
            except ValueError:
                continue
            if row_day == today:
                found = (int(up_kb) * _KB, int(down_kb) * _KB)
        if found is None:
            logger.info("dat 恢复 | 无今天 (%s) 的行, 当日累计从 0 开始", today.isoformat())
            return False
        self._day = today
        self._day_up, self._day_down = found
        logger.info("dat 恢复 | 今天 (%s) 累计 up=%d down=%d", today.isoformat(), self._day_up, self._day_down)
        return True

    # ---- 采样 ----

    def sample_once(
        self,
        interval_hint: float = DEFAULT_SAMPLE_INTERVAL,
        rate_warn_bps: int = DEFAULT_SAMPLE_RATE_WARN_BPS,
    ) -> SampleResult:
        """单次采样: 读 -> 过滤 -> 逐卡差分 (回绕归零) -> 求和入账 -> 当日累计 (跨天硬切).

        S5 (C-prime): interval_hint 由主循环每轮传入当前 ``config.sample_interval``
        (不缓存 -> 热改立即生效), rate_warn_bps 同理由配置每轮现读。速率判定是旁路:
        只写 WARNING 与 ``last_spike``, 不改 delta/day (计划 §06.1)。
        """
        now = self._clock()
        day = now.date()
        counters = self._counters_provider()
        stats = self._stats_provider()
        now_mono = time.monotonic()  # 与计数器读取同一时刻 (单调钟优先, 不受对时影响)
        now_wall = time.time()
        selected = self.filter.select(counters, stats)
        total_up = sum(io.bytes_sent for io in selected.values())
        total_down = sum(io.bytes_recv for io in selected.values())
        warnings: list[str] = []
        dt_info = self._dt_since_last(now_mono, now_wall, interval_hint)

        # 日界方向检查 (与 restore 的未来日期降级同一防线): 只有日界**前进**才硬切清零。
        # 挂钟回跳跨日界 (NTP 大步校正/手动改钟) 不清零 —— 回跳侧的"新日"其实是历史日,
        # 清零会让 dat 今日行被低值 upsert 覆盖且当日不可自愈 (宁可少报, 不重置);
        # 采样日钉在原日界 (累计与 dat upsert 目标保持一致, 不写历史行), 日界追平后自愈。
        day_rolled = self._day is not None and day > self._day
        if day_rolled:
            logger.info("跨天切换 | %s -> %s, 当日累计清零", self._day.isoformat(), day.isoformat())  # type: ignore[union-attr]
            self._day_up = 0
            self._day_down = 0
        elif self._day is not None and day < self._day:
            warnings.append(
                f"挂钟回跳: {self._day.isoformat()} -> {day.isoformat()}, 当日累计不清零 (继续按 {self._day.isoformat()} 累计)"
            )
            day = self._day  # type: ignore[assignment]
        self._day = day

        if not selected:
            warnings.append("无适配器通过过滤: 合计按 0 计 (检查 include/exclude/loopback/down 配置与网卡状态)")

        # baseline = 本轮开始时逐卡记忆是否为空 (为空 -> 全部选中卡都按新卡只立基线)
        baseline = not self._nic_base
        counter_reset = False
        delta_up = delta_down = 0
        if baseline:
            logger.info("采样基线 | 上次快照不可用, 本次读数作为基线 (up=%d down=%d)", total_up, total_down)

        next_base: dict[str, tuple[int, int]] = {}
        per_nic_delta: list[tuple[str, int, int, tuple[int, int], tuple[int, int]]] = []
        for name, io in selected.items():
            cur = (io.bytes_sent, io.bytes_recv)
            prev = self._nic_base.get(name)
            if prev is None:
                # 新卡 (含 v1 升级后的首轮): 只立基线, 历史累计不入账 (I6 少报不虚高)
                next_base[name] = cur
                continue
            du = cur[0] - prev[0]
            dd = cur[1] - prev[1]
            if du < 0:
                counter_reset = True
                warnings.append(f"上行计数器重置 | nic={name} cur={cur[0]} last={prev[0]} delta 记 0")
                du = 0
            if dd < 0:
                counter_reset = True
                warnings.append(f"下行计数器重置 | nic={name} cur={cur[1]} last={prev[1]} delta 记 0")
                dd = 0
            delta_up += du
            delta_down += dd
            per_nic_delta.append((name, du, dd, cur, prev))
            next_base[name] = cur

        # 合并而不是替换: 消失卡的记忆保留 (回来后按真实增量差分), 仅清 7 天未见条目
        self._nic_base.update(next_base)
        for name in next_base:
            self._nic_seen[name] = now
        self._prune_nic_base(now)
        # 时间基线在本轮读完后推进 (下一轮 dt 才以本轮读数为起点)
        self._last_mono = now_mono
        self._last_sample_wall = now_wall
        # C-prime: 只算速率/只告警, 不改 delta/day
        self._evaluate_rate(per_nic_delta, dt_info, now_wall, rate_warn_bps)
        self._day_up += delta_up
        self._day_down += delta_down

        for w in warnings:
            logger.warning("采样告警 | %s", w)
        logger.debug(
            "采样 | day=%s 当日 up=%d down=%d, delta=(%d, %d), reset=%s, rolled=%s, baseline=%s", day.isoformat(),
            self._day_up, self._day_down, delta_up, delta_down, counter_reset, day_rolled, baseline
        )
        return SampleResult(
            day=day,
            day_up_bytes=self._day_up,
            day_down_bytes=self._day_down,
            delta_up_bytes=delta_up,
            delta_down_bytes=delta_down,
            counter_reset=counter_reset,
            day_rolled=day_rolled,
            baseline=baseline,
            warnings=tuple(warnings),
        )

    def _dt_since_last(
        self,
        now_mono: float,
        now_wall: float,
        interval_hint: float,
    ) -> Optional[tuple[float, float]]:
        """本轮 dt 与钳制后的 eff_dt (计划 §06.3); 无可用基线/非法 -> None (跳过判定).

        来源优先级: 进程内 ``_last_mono`` (单调钟) -> 重启后 state 的 ``_last_sample_wall``。
        wall 兜底额外要求 ``0 < dt <= 7 天``: 陈旧 state 或时钟跳变不制造虚假速率。
        eff_dt = min(dt, 3 × interval_hint) —— 长 gap 不把注入量摊薄到阈值以下。
        """
        if self._last_mono is not None:
            dt = now_mono - self._last_mono
            source = "mono"
        elif self._last_sample_wall is not None:
            dt = now_wall - self._last_sample_wall
            source = "wall"
        else:
            logger.debug("速率判定跳过 | 无上一轮时间基线 (首轮/state 缺失)")
            return None
        if not math.isfinite(dt) or dt <= 0:
            logger.debug("速率判定跳过 | dt 非法: %.6fs (来源 %s)", dt, source)
            return None
        if source == "wall" and dt > _MAX_RESTART_DT_S:
            logger.debug("速率判定跳过 | 重启 wall 差值 %.1fs 超过 7 天上限", dt)
            return None
        return dt, min(dt, WARN_DT_CLAMP_FACTOR * interval_hint)

    def _evaluate_rate(
        self,
        per_nic_delta: list[tuple[str, int, int, tuple[int, int], tuple[int, int]]],
        dt_info: Optional[tuple[float, float]],
        now_wall: float,
        threshold_bps: int,
    ) -> None:
        """C-prime 速率判定: 单卡单方向 ``delta / eff_dt > threshold`` 才告警 (严格大于).

        只记 WARNING 与 ``last_spike`` (只留最近一轮); delta/day 已在调用方照常入账,
        本方法不读写累计 (计划 T11)。回绕方向 delta=0 -> 速率为 0, 另一方向独立判定。
        """
        if dt_info is None:
            return
        dt, eff_dt = dt_info
        hits: list[dict[str, object]] = []
        for name, du, dd, cur, prev in per_nic_delta:
            for direction, delta, cur_val, last_val in (
                ("up", du, cur[0], prev[0]),
                ("down", dd, cur[1], prev[1]),
            ):
                rate = delta / eff_dt
                if rate <= threshold_bps:
                    continue
                logger.warning(
                    "单轮速率超阈值 | nic=%s dir=%s cur=%d last=%d delta=%d dt=%.3fs eff_dt=%.3fs rate=%.1fB/s threshold=%dB/s (仅告警, 照常入账)",
                    name,
                    direction,
                    cur_val,
                    last_val,
                    delta,
                    dt,
                    eff_dt,
                    rate,
                    threshold_bps,
                )
                hits.append(
                    {
                        "nic": name,
                        "dir": direction,
                        "cur": cur_val,
                        "last": last_val,
                        "delta": delta,
                        "rate_bps": int(rate),
                    }
                )
        if not hits:
            return
        self._last_spike = {
            "ts": datetime.fromtimestamp(now_wall).astimezone().isoformat(timespec="seconds"),
            "dt_s": dt,
            "eff_dt_s": eff_dt,
            "threshold_bps": threshold_bps,
            "items": hits,
        }

    def _prune_nic_base(self, now: datetime) -> None:
        """清理 7 天未被选中的逐卡记忆 (避免 state 无界增长; 8 天后回来按新卡处理)."""
        cutoff = now - timedelta(days=_NIC_BASE_TTL_DAYS)
        stale = sorted(name for name, seen in self._nic_seen.items() if seen < cutoff)
        if not stale:
            return
        for name in stale:
            self._nic_base.pop(name, None)
            self._nic_seen.pop(name, None)
        logger.info("逐卡基线清理 | 超过 %d 天未见: %s", _NIC_BASE_TTL_DAYS, ", ".join(stale))
