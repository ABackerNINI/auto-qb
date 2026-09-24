"""频控: 间隔 + 抖动 + 两级配额 + 失败退避与熔断 + 时间窗(计划 §7)。

对齐项目黄金法则: **幂等**(配额窗口以「窗口键」判定, 重启不重置、重放不重复消耗)、
**保守默认**(配额默认紧)、**fail-fast**(全部键在 validate_config 校验)。

关键约定:
- **抖动只向上**(+0~25%): 向下抖会让实测间隔低于配置下限, 与验收标准矛盾, 也更容易被站点
  看成机器节拍。故「相邻两次请求间隔 >= min_torrent_interval」是硬下限。
- **配额按站点独立计数**(小时/天两窗口), 到顶即返回空清单, **不报错**。
- **单一权威在后端**: 扩展不做任何频控判断, 它只按后端返回的「最早可取时间」干活。
"""
import logging
import random
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from ..infra.utils import time_in_range
from .model import HrFuse, HrQuota

logger = logging.getLogger(__name__)

#: 抖动上限(比例): 只向上, 保证实测间隔 >= min_torrent_interval
JITTER_RATIO = 0.25


@dataclass(frozen=True, slots=True)
class HrLimits:
    """一个站点的有效频控参数(全局默认与站点覆盖合并后的结果)"""

    min_interval: float
    max_per_hour: int
    max_per_day: int
    failure_threshold: int
    failure_cooldown: float
    allow_window: str = ""

    @classmethod
    def merge(cls, global_conf, site_conf) -> "HrLimits":
        """全局默认 + 站点覆盖(站点 max_torrents_per_hour 为 None 时回退全局)"""
        per_hour = site_conf.max_torrents_per_hour
        return cls(
            min_interval=global_conf.min_torrent_interval,
            max_per_hour=global_conf.max_torrents_per_hour if per_hour is None else per_hour,
            max_per_day=global_conf.max_torrents_per_day,
            failure_threshold=global_conf.failure_threshold,
            failure_cooldown=global_conf.failure_cooldown,
            allow_window=global_conf.allow_window,
        )


def hour_key(now: float) -> str:
    """小时窗口键(本地时区, 如 "2026-09-24T20")"""
    return datetime.fromtimestamp(now).strftime("%Y-%m-%dT%H")


def day_key(now: float) -> str:
    """天窗口键(本地时区, 如 "2026-09-24")"""
    return datetime.fromtimestamp(now).strftime("%Y-%m-%d")


def _roll_windows(quota: HrQuota, now: float) -> None:
    """窗口键变化即重置对应计数 —— 幂等靠窗口键, 不依赖进程存活(重启不重置配额)"""
    hk, dk = hour_key(now), day_key(now)
    if quota.hour_window != hk:
        quota.hour_window, quota.hour_count = hk, 0
    if quota.day_window != dk:
        quota.day_window, quota.day_count = dk, 0


def quota_left(quota: HrQuota, limits: HrLimits, now: float) -> int:
    """当前窗口还能消耗多少次配额(view 语义, 不修改状态)"""
    hk, dk = hour_key(now), day_key(now)
    hour_used = quota.hour_count if quota.hour_window == hk else 0
    day_used = quota.day_count if quota.day_window == dk else 0
    return max(0, min(limits.max_per_hour - hour_used, limits.max_per_day - day_used))


def try_consume(quota: HrQuota, limits: HrLimits, now: float, count: int = 1) -> bool:
    """尝试消耗配额; 成功则记账并返回 True, 到顶返回 False(调用方返回空清单, 不报错)"""
    _roll_windows(quota, now)
    if quota.hour_count + count > limits.max_per_hour or quota.day_count + count > limits.max_per_day:
        return False
    quota.hour_count += count
    quota.day_count += count
    return True


def next_hour_reset(now: float) -> float:
    """下一个整点(小时窗口重置时刻)"""
    dt = datetime.fromtimestamp(now)
    return dt.replace(minute=0, second=0, microsecond=0).timestamp() + 3600


def next_day_reset(now: float) -> float:
    """次日零点(天窗口重置时刻)"""
    dt = datetime.fromtimestamp(now)
    return dt.replace(hour=0, minute=0, second=0, microsecond=0).timestamp() + 86400


def window_start_on(now: float, spec: str) -> float:
    """把 "HH:MM-HH:MM" 的起点映射到 now 当天(或次日)的时间戳"""
    start_s = spec.split("-", 1)[0].strip()
    hh, mm = (int(x) for x in start_s.split(":"))
    dt = datetime.fromtimestamp(now).replace(hour=hh, minute=mm, second=0, microsecond=0)
    ts = dt.timestamp()
    return ts if ts > now else ts + 86400


def jittered_interval(min_interval: float, rng: Optional[random.Random] = None) -> float:
    """相邻两次请求的**实际**最小间隔: 只向上抖动 → 恒 >= min_interval"""
    r = rng or random
    return min_interval * (1.0 + r.random() * JITTER_RATIO)


def fuse_active(fuse: HrFuse, now: float) -> bool:
    """熔断是否仍在生效(冷却未过)"""
    return fuse.until_ts > now


def record_failure(fuse: HrFuse, limits: HrLimits, now: float, retry_after: float = 0.0) -> bool:
    """记一次失败; 连续失败达阈值则进入冷却。返回是否新进入熔断(供告警去重)。

    退避: 站点给出 Retry-After 时按它; 否则指数退避(min_interval 不可得, 用 cooldown 的
    1/2^n 粒度不合适, 故直接以 cooldown 为上限、以失败次数翻倍)。
    """
    #: 回传来的 Retry-After 不可信(畸形/恶意值能把熔断推到天荒地老): 以本站冷却时长封顶
    retry_after = max(0.0, min(float(retry_after), limits.failure_cooldown))
    fuse.failures += 1
    fuse.reason = "连续失败"
    newly_fused = False
    if fuse.failures >= limits.failure_threshold:
        backoff = retry_after if retry_after > 0 else limits.failure_cooldown
        fuse.until_ts = now + backoff
        newly_fused = fuse.until_ts > now
    elif retry_after > 0:
        fuse.until_ts = now + retry_after
    return newly_fused


def record_success(fuse: HrFuse) -> None:
    """成功后清空失败计数与冷却"""
    fuse.failures = 0
    fuse.until_ts = 0.0
    fuse.reason = ""


def next_allowed_at(quota: HrQuota,
                    limits: HrLimits,
                    fuse: HrFuse,
                    now: float,
                    rng: Optional[random.Random] = None) -> Tuple[float, str]:
    """下一次允许发起请求的时刻 + 原因(供报告与日志)。

    取三者最晚: ① 间隔门槛(上次请求 + 抖动后的最小间隔) ② 配额窗口重置 ③ 熔断冷却。
    另叠加 allow_window(不在时段内则等到时段起点)。
    """
    candidates: List[Tuple[float, str]] = []
    if limits.min_interval > 0 and quota.last_fetch_ts > 0:
        candidates.append((quota.last_fetch_ts + jittered_interval(limits.min_interval, rng), "间隔"))
    if fuse_active(fuse, now):
        candidates.append((fuse.until_ts, "熔断冷却"))
    _roll_windows(quota, now)
    if quota.hour_count >= limits.max_per_hour:
        candidates.append((next_hour_reset(now), "小时配额"))
    if quota.day_count >= limits.max_per_day:
        candidates.append((next_day_reset(now), "日配额"))
    if limits.allow_window and not time_in_range(datetime.fromtimestamp(now).time(), limits.allow_window):
        candidates.append((window_start_on(now, limits.allow_window), "时间窗"))
    if not candidates:
        return now, ""
    due, reason = max(candidates, key=lambda item: item[0])
    if due <= now:  # 各门槛都已满足: 立即可取, 原因不适用
        return now, ""
    return due, reason


def now_ts() -> float:
    """当前 epoch 秒(单独抽出便于测试替换)"""
    return time.time()
