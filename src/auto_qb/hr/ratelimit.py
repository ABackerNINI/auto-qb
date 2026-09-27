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
    """一个站点的有效频控参数(全局默认与站点覆盖合并后的结果)

    legacy 字段(min_interval/max_per_hour/max_per_day)在 quota_model=legacy 下语义不变;
    split 字段(page_*/torrent_*)只在 quota_model=split 下消费(计划 26-09-27-1815 §2 3.2):
    页面桶与下载桶独立令牌桶, min_interval(legacy 键)在 split 下改义为「仅 .torrent 下载间隔」。
    """

    min_interval: float
    max_per_hour: int
    max_per_day: int
    failure_threshold: int
    failure_cooldown: float
    allow_window: str = ""
    #: 激活门(计划 §2 3.2, D6): 站点级显式 opt-in split 才切双桶; 默认 legacy 行为逐字节一致
    quota_model: str = "legacy"
    page_rate_per_hour: int = 40
    page_burst: int = 10
    torrent_rate_per_hour: int = 20
    torrent_burst: int = 5
    pages_per_day_max: int = 400
    torrents_per_day_max: int = 200
    page_min_interval: float = 90.0

    @property
    def split(self) -> bool:
        return self.quota_model == "split"

    @classmethod
    def merge(cls, global_conf, site_conf) -> "HrLimits":
        """全局默认 + 站点覆盖(站点 max_torrents_per_hour 为 None 时回退全局)

        split 激活门: site_conf.quota_model 显式配 split 才切双桶; 站点覆盖键在 split 下的映射 ——
        max_torrents_per_hour(现键)⇒ 下载桶速率覆盖(用户已有配置不失效),
        page_rate_per_hour / torrent_rate_per_hour(新键)⇒ 页面/下载桶速率覆盖。
        天级上限不提供站点覆盖(与现状一致)。
        """
        per_hour = site_conf.max_torrents_per_hour
        model = getattr(site_conf, "quota_model", "legacy") or "legacy"
        torrent_rate = None
        if model == "split":
            torrent_rate = site_conf.torrent_rate_per_hour if site_conf.torrent_rate_per_hour is not None else per_hour
        # 下载天顶: 全局未显式配置时按模型取默认(legacy 60 / split 200, 计划 §2 3.1)
        day_raw = global_conf.max_torrents_per_day
        day_max = day_raw if day_raw is not None else (200 if model == "split" else 60)
        return cls(
            min_interval=global_conf.min_torrent_interval,
            max_per_hour=global_conf.max_torrents_per_hour if per_hour is None else per_hour,
            max_per_day=day_max,
            failure_threshold=global_conf.failure_threshold,
            failure_cooldown=global_conf.failure_cooldown,
            allow_window=global_conf.allow_window,
            quota_model=model,
            page_rate_per_hour=(
                global_conf.page_rate_per_hour
                if getattr(site_conf, "page_rate_per_hour", None) is None else site_conf.page_rate_per_hour
            ),
            torrent_rate_per_hour=(global_conf.torrent_rate_per_hour if torrent_rate is None else torrent_rate),
            page_burst=global_conf.page_burst,
            torrent_burst=global_conf.torrent_burst,
            pages_per_day_max=global_conf.max_pages_per_day,
            torrents_per_day_max=day_max,
            page_min_interval=global_conf.min_page_interval,
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


# ---------- split 模型(计划 26-09-27-1815 §2 M5.3): 页面 / 下载双令牌桶 ----------
# 激活门(D6): 只有站点显式 quota_model=split 才走这组函数; legacy 路径一行不改。
# 令牌桶状态 (tokens, refill_ts) 持久化在站点文件里: 补充按「上次补充时刻 + 速率」现算 ——
# 天然幂等(同一时刻重复计算结果一致)、跨重启不重置、消除整点突发(补充是连续的, 不按整点归零)。


def _bucket_of(quota: HrQuota, limits: HrLimits, kind: str) -> Tuple[Optional[float], float, int, int, int, float]:
    """(tokens, refill_ts, burst, rate, day_count, day_max) —— kind ∈ {page, torrent}

    页面账本 = quota(站点文件的 quota 字段), 下载账本 = torrent_quota(调用方传对账本即可);
    本函数只按 kind 取 limits 侧参数与账本上的桶状态。
    """
    if kind == "page":
        return quota.tokens, quota.refill_ts, limits.page_burst, limits.page_rate_per_hour, \
            quota.day_count, limits.pages_per_day_max
    return quota.tokens, quota.refill_ts, limits.torrent_burst, limits.torrent_rate_per_hour, \
        quota.day_count, limits.torrents_per_day_max


def bucket_left(quota: HrQuota, limits: HrLimits, now: float, kind: str) -> float:
    """当前桶里的令牌数(view 语义, 不修改状态) —— 展示层与 --hr-status 用"""
    tokens, refill_ts, burst, rate, _day, _max = _bucket_of(quota, limits, kind)
    if tokens is None:
        return float(burst)
    if refill_ts <= 0:
        return float(burst)
    return min(float(burst), tokens + max(0.0, now - refill_ts) * rate / 3600.0)


def split_next_allowed_at(
    quota: HrQuota,
    limits: HrLimits,
    fuse: HrFuse,
    now: float,
    kind: str,
    rng: Optional[random.Random] = None
) -> Tuple[float, str]:
    """split 模型下一次允许发起 kind 类请求的时刻 + 原因

    门槛取最晚: ① 该类请求的最小间隔(min_page_interval / min_torrent_interval) ② 桶令牌不足时
    的补充等待 ③ 天级硬顶重置 ④ 熔断冷却 ⑤ allow_window。tokens 未初始化(None)按满桶计。
    """
    candidates: List[Tuple[float, str]] = []
    if kind == "page":
        interval = limits.page_min_interval
        day_max = limits.pages_per_day_max
    else:
        interval = limits.min_interval
        day_max = limits.torrents_per_day_max
    if interval > 0 and quota.refill_ts > 0:
        candidates.append((quota.refill_ts + jittered_interval(interval, rng), "间隔"))
    if fuse_active(fuse, now):
        candidates.append((fuse.until_ts, "熔断冷却"))
    _roll_windows(quota, now)
    if quota.day_count >= day_max:
        candidates.append((next_day_reset(now), "日配额"))
    if limits.allow_window and not time_in_range(datetime.fromtimestamp(now).time(), limits.allow_window):
        candidates.append((window_start_on(now, limits.allow_window), "时间窗"))
    tokens, refill_ts, burst, rate, _day, _dmax = _bucket_of(quota, limits, kind)
    if rate > 0:
        # 按**补充后**的桶量判断(消费/等待发生时都会先补充, 门槛判断必须同口径)
        current = bucket_left(quota, limits, now, kind)
        if current < 1.0:
            need = (1.0 - current) * 3600.0 / rate
            candidates.append((now + need, "令牌补充"))
    if not candidates:
        return now, ""
    due, reason = max(candidates, key=lambda item: item[0])
    if due <= now:
        return now, ""
    return due, reason


def split_try_consume(quota: HrQuota, limits: HrLimits, now: float, kind: str, count: int = 1) -> bool:
    """split 模型尝试消耗 kind 桶的 1 个令牌 + 天级硬顶记账; 到顶返回 False(不报错)

    天顶复用 day_window/day_count(窗口键幂等); 令牌桶按连续速率补充, 消费即把 refill_ts
    推进到 now(它同时是下一发的间隔门槛基准, 与 legacy 的 last_fetch_ts 同一角色)。
    """
    _roll_windows(quota, now)
    _tokens, _refill, burst, rate, _day, day_max = _bucket_of(quota, limits, kind)
    if quota.day_count + count > day_max:
        return False
    tokens = burst if quota.tokens is None else min(float(burst), quota.tokens)
    if quota.refill_ts > 0:
        tokens = min(float(burst), tokens + max(0.0, now - quota.refill_ts) * rate / 3600.0)
    if tokens < count:
        return False
    quota.tokens = tokens - count
    quota.refill_ts = now
    quota.day_count += count
    return True


def now_ts() -> float:
    """当前 epoch 秒(单独抽出便于测试替换)"""
    return time.time()
