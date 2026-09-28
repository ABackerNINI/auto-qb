"""频控(单模型, 计划 26-09-28-1932 §5.1): 最小间隔 + 日额保险 + 时间窗。

对齐项目黄金法则: **幂等**(日额窗口以「窗口键」判定, 重启不重置、重放不重复消耗)、
**保守默认**、**fail-fast**。

三个机制, 全部站点级独立计数:
- **相邻请求最小间隔 min_interval**(默认 90S): 页面与 .torrent 下载统一适用; 抖动只向上
  +0~25%(实测间隔恒 >= 配置下限), 隐含 40 请求/时 的硬顶。
- **日额保险 max_requests_per_day**(默认 240): 全部请求(页面 + 下载)合计, 零点重置;
  只防长跑超量, 不是节奏工具。
- **allow_window**(可选): 仅该时段取数。

被删除的旧概念: legacy/split 双账本与令牌桶(quota_model)、小时配额、burst、熔断与退避
(§5.2: 失败 = 档位截断 + 周期自然重试, 无独立机制)。Retry-After 是**站点明确指令**,
由 service 单独存 retry_after_until 并参与「下次可取时刻」计算, 不算退避。

关键约定:
- **单一权威在后端**: 扩展不做任何频控判断, 它只按后端返回的「最早可取时间」干活。
"""
import random
import time
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple

from ..infra.utils import time_in_range
from .model import HrSiteData

#: 抖动上限(比例): 只向上, 保证实测间隔 >= min_interval
JITTER_RATIO = 0.25


@dataclass(frozen=True, slots=True)
class HrLimits:
    """一个站点的有效频控参数(v3: 全部来自全局配置, 站点级不再有频控键)"""

    min_interval: float
    max_requests_per_day: int
    allow_window: str = ""

    @classmethod
    def merge(cls, global_conf, site_conf=None) -> "HrLimits":
        """全局默认(站点级频控键已随 v3 模型删除; site_conf 参数保留为兼容占位)"""
        return cls(
            min_interval=global_conf.min_interval,
            max_requests_per_day=global_conf.max_requests_per_day,
            allow_window=global_conf.allow_window,
        )


def day_key(now: float) -> str:
    """天窗口键(本地时区, 如 "2026-09-24")"""
    return datetime.fromtimestamp(now).strftime("%Y-%m-%d")


def _day_count(data: HrSiteData, now: float) -> int:
    """本自然日已发生的请求数(窗口键翻篇即视为 0 —— 幂等靠窗口键, 不依赖进程存活)"""
    return 0 if data.rate.day_window != day_key(now) else data.rate.day_count


def quota_left(data: HrSiteData, limits: HrLimits, now: float) -> int:
    """当前自然日还能发起多少请求(view 语义, 不修改状态)"""
    return max(0, limits.max_requests_per_day - _day_count(data, now))


def try_consume(data: HrSiteData, limits: HrLimits, now: float, count: int = 1) -> bool:
    """尝试消耗日额; 成功则记账并返回 True, 到顶返回 False(调用方截断, 不报错)"""
    used = _day_count(data, now)
    if used + count > limits.max_requests_per_day:
        return False
    data.rate.day_window = day_key(now)
    data.rate.day_count = used + count
    return True


def jittered_interval(min_interval: float, rng: Optional[random.Random] = None) -> float:
    """相邻两次请求的**实际**最小间隔: 只向上抖动 → 恒 >= min_interval"""
    r = rng or random
    return min_interval * (1.0 + r.random() * JITTER_RATIO)


def window_start_on(now: float, spec: str) -> float:
    """把 "HH:MM-HH:MM" 的起点映射到 now 当天(或次日)的时间戳"""
    start_s = spec.split("-", 1)[0].strip()
    hh, mm = (int(x) for x in start_s.split(":"))
    dt = datetime.fromtimestamp(now).replace(hour=hh, minute=mm, second=0, microsecond=0)
    ts = dt.timestamp()
    return ts if ts > now else ts + 86400


def next_day_reset(now: float) -> float:
    """次日零点(日额窗口重置时刻)"""
    dt = datetime.fromtimestamp(now)
    return dt.replace(hour=0, minute=0, second=0, microsecond=0).timestamp() + 86400


def next_allowed_at(
    data: HrSiteData,
    limits: HrLimits,
    now: float,
    rng: Optional[random.Random] = None,
) -> Tuple[float, str]:
    """下一次允许发起请求的时刻 + 原因(供报告与日志)。

    取最晚: ① 间隔门槛(上次请求 + 抖动后的最小间隔) ② 日额重置(到顶时) ③ Retry-After
    ④ allow_window(不在时段内则等到时段起点)。熔断/停用/退避已随 v3 模型删除(§5.2)。
    """
    candidates: List[Tuple[float, str]] = []
    if limits.min_interval > 0 and data.rate.last_fetch_ts > 0:
        candidates.append((data.rate.last_fetch_ts + jittered_interval(limits.min_interval, rng), "间隔"))
    if data.retry_after_until > now:
        candidates.append((data.retry_after_until, "Retry-After"))
    if data.rate.day_window == day_key(now) and data.rate.day_count >= limits.max_requests_per_day:
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
