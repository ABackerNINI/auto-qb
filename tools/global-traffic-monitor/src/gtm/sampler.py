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
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Callable, Mapping, Optional, Protocol

import psutil

from .nic import default_providers

logger = logging.getLogger("gtm.sampler")

# 采样周期默认值 (s); 休眠循环在 S2 run 命令, 此处仅作为默认口径单点
DEFAULT_SAMPLE_INTERVAL = 5.0

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
                name: {"up": up, "down": down} for name, (up, down) in self._nic_base.items()
            },
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
        if not self._restore_day(day_raw, snapshot.get("day_up_bytes"), snapshot.get("day_down_bytes"), warnings,
                                 today):
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
        if not self._restore_day(day_raw, snapshot.get("day_up_bytes"), snapshot.get("day_down_bytes"), warnings,
                                 now.date()):
            return False
        self._nic_base = parsed
        self._nic_seen = {name: now for name in parsed}
        warnings.extend(entry_warnings)
        return True

    def _restore_day(self, day_raw: object, day_up: object, day_down: object, warnings: list[str],
                     today: date) -> bool:
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

    def sample_once(self) -> SampleResult:
        """单次采样: 读 -> 过滤 -> 逐卡差分 (回绕归零) -> 求和入账 -> 当日累计 (跨天硬切)."""
        now = self._clock()
        day = now.date()
        counters = self._counters_provider()
        stats = self._stats_provider()
        selected = self.filter.select(counters, stats)
        total_up = sum(io.bytes_sent for io in selected.values())
        total_down = sum(io.bytes_recv for io in selected.values())
        warnings: list[str] = []

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
            next_base[name] = cur

        # 合并而不是替换: 消失卡的记忆保留 (回来后按真实增量差分), 仅清 7 天未见条目
        self._nic_base.update(next_base)
        for name in next_base:
            self._nic_seen[name] = now
        self._prune_nic_base(now)
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
