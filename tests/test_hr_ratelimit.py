"""test_hr_ratelimit 测试计划: 频控(间隔 + 只向上抖动 + 两级配额 + 失败退避熔断 + 时间窗)

## 测试计划(每个测试函数一条)
- test_jitter_only_goes_up: 抖动只向上 —— 实测间隔恒 >= min_torrent_interval(验收硬下限)
- test_try_consume_respects_hour_and_day_quota: 小时/天两级配额, 到顶不再消耗
- test_windows_roll_resets_counts: 窗口键变化即重置(幂等靠窗口键, 重启不重置配额)
- test_quota_left_is_a_view: quota_left 是只读视图, 不修改状态
- test_next_allowed_interval_gate: 间隔门槛: 上次请求后不足最小间隔 -> 等到间隔满
- test_next_allowed_fuse_and_quota: 熔断冷却与配额窗口重置都参与「最早可取时刻」
- test_allow_window_gates_fetching: 时间窗限制(含跨午夜); 留空 = 全天不限制
- test_record_failure_fuses_after_threshold: 连续失败达阈值进入冷却, 成功后退避清零
- test_record_failure_honours_retry_after: 站点给出 Retry-After 时按它退避(未达阈值也生效)
- test_record_failure_caps_retry_after_at_cooldown: Retry-After 以 failure_cooldown 封顶(回传值不可信)
- test_limits_merge_site_overrides_global: 站点 max_torrents_per_hour 覆盖全局, 未配置回退全局
"""
from datetime import datetime

from auto_qb.hr.model import HrFuse, HrQuota
from auto_qb.hr.ratelimit import (
    HrLimits,
    bucket_left,
    fuse_active,
    hour_key,
    jittered_interval,
    next_allowed_at,
    next_hour_reset,
    quota_left,
    record_failure,
    record_success,
    split_next_allowed_at,
    split_try_consume,
    try_consume,
)
from hr_helpers import global_conf, site_conf


def now_hour_end(ts: float) -> float:
    """下一个整点(小时配额窗口重置时刻)"""
    return next_hour_reset(ts)


# 固定在 2026-09-24 20:30 便于验证窗口与时间窗
NOW = datetime(2026, 9, 24, 20, 30, 0).timestamp()


def _limits(**overrides) -> HrLimits:
    conf = global_conf(**overrides)
    return HrLimits.merge(conf, site_conf())


def test_jitter_only_goes_up():
    """抖动只向上(+0~25%): 实测间隔恒 >= min_torrent_interval, 且不超过 1.25 倍"""
    for _ in range(200):
        got = jittered_interval(90.0)
        assert 90.0 <= got <= 112.5


def test_try_consume_respects_hour_and_day_quota():
    """小时/天两级配额, 到顶不再消耗(返回 False, 调用方返回空清单而不报错)"""
    limits = _limits(max_torrents_per_hour=2)
    quota = HrQuota()
    assert try_consume(quota, limits, NOW) is True
    assert try_consume(quota, limits, NOW) is True
    assert try_consume(quota, limits, NOW) is False
    assert (quota.hour_count, quota.day_count) == (2, 2)

    day_limits = _limits(max_torrents_per_hour=10, max_torrents_per_day=3)
    quota = HrQuota()
    assert [try_consume(quota, day_limits, NOW) for _ in range(4)] == [True, True, True, False]


def test_windows_roll_resets_counts():
    """窗口键变化即重置(重启不重置配额 —— 幂等靠窗口键而非进程状态)"""
    limits = _limits(max_torrents_per_hour=1, max_torrents_per_day=2)
    quota = HrQuota()
    assert try_consume(quota, limits, NOW) is True
    assert try_consume(quota, limits, NOW) is False
    later = NOW + 3600  # 下一个小时窗口
    assert hour_key(later) != hour_key(NOW)
    assert try_consume(quota, limits, later) is True
    assert quota.hour_count == 1 and quota.day_count == 2


def test_quota_left_is_a_view():
    """quota_left 是只读视图(不修改状态, 供 Web 展示剩余额度)"""
    limits = _limits(max_torrents_per_hour=5, max_torrents_per_day=8)
    quota = HrQuota(hour_window=hour_key(NOW), hour_count=2, day_window=hour_key(NOW)[:10], day_count=7)
    assert quota_left(quota, limits, NOW) == 1
    assert quota.hour_count == 2 and quota.day_count == 7


def test_next_allowed_interval_gate():
    """间隔门槛: 上次请求后不足最小间隔 -> 等到间隔满(基准是上一次请求时刻)"""
    limits = _limits(min_torrent_interval=90.0)
    quota = HrQuota(last_fetch_ts=NOW)
    fuse = HrFuse()
    due, why = next_allowed_at(quota, limits, fuse, NOW)
    assert why == "间隔"
    assert NOW + 90.0 <= due <= NOW + 112.5

    # 已经等够: 立即可取, 原因不再适用(空串)
    due, why = next_allowed_at(quota, limits, fuse, NOW + 200)
    assert (due, why) == (NOW + 200, "")


def test_next_allowed_fuse_and_quota():
    """熔断冷却与配额窗口重置都参与「最早可取时刻」(取三者最晚)"""
    limits = _limits(min_torrent_interval=0.0, max_torrents_per_hour=1, failure_cooldown=600.0)
    quota = HrQuota(hour_window=hour_key(NOW), hour_count=1, day_window=hour_key(NOW)[:10], day_count=1)
    fuse = HrFuse(failures=3, until_ts=NOW + 120)
    due, why = next_allowed_at(quota, limits, fuse, NOW)
    assert why == "小时配额"  # 小时窗口重置晚于熔断冷却 -> 由窗口决定
    assert due >= NOW + 120  # 不小于熔断冷却
    assert due == now_hour_end(NOW)

    assert fuse_active(fuse, NOW) is True
    assert fuse_active(fuse, NOW + 121) is False


def test_allow_window_gates_fetching():
    """时间窗限制(含跨午夜); 留空 = 全天不限制"""
    limits = _limits(min_torrent_interval=0.0, allow_window="23:00-08:00")
    due, why = next_allowed_at(HrQuota(), limits, HrFuse(), NOW)
    assert why == "时间窗"
    assert due == datetime(2026, 9, 24, 23, 0, 0).timestamp()

    in_window = datetime(2026, 9, 25, 7, 0, 0).timestamp()  # 跨午夜后仍在窗内
    due, why = next_allowed_at(HrQuota(), limits, HrFuse(), in_window)
    assert (due, why) == (in_window, "")

    limits = _limits(min_torrent_interval=0.0, allow_window="")
    due, why = next_allowed_at(HrQuota(), limits, HrFuse(), NOW)
    assert (due, why) == (NOW, "")


def test_record_failure_fuses_after_threshold():
    """连续失败达阈值进入冷却(返回 True 供告警去重), 成功后退避清零"""
    limits = _limits(failure_threshold=3, failure_cooldown=1800.0)
    fuse = HrFuse()
    assert record_failure(fuse, limits, NOW) is False
    assert record_failure(fuse, limits, NOW) is False
    assert record_failure(fuse, limits, NOW) is True
    assert fuse.until_ts == NOW + 1800.0
    assert fuse_active(fuse, NOW) is True
    record_success(fuse)
    assert fuse.failures == 0 and fuse.until_ts == 0.0


def test_record_failure_honours_retry_after():
    """站点给出 Retry-After 时按它退避(未达阈值也生效, 不死循环烧配额)"""
    limits = _limits(failure_threshold=5, failure_cooldown=1800.0)
    fuse = HrFuse()
    assert record_failure(fuse, limits, NOW, retry_after=429.0) is False
    assert fuse.until_ts == NOW + 429.0


def test_record_failure_caps_retry_after_at_cooldown():
    """Retry-After 以本站冷却时长封顶 —— 回传值不可信(畸形/恶意值可把熔断推到天荒地老)"""
    limits = _limits(failure_threshold=5, failure_cooldown=1800.0)
    fuse = HrFuse()
    assert record_failure(fuse, limits, NOW, retry_after=10**12) is False
    assert fuse.until_ts == NOW + 1800.0, "超大的 Retry-After 被钳到 failure_cooldown"


def test_limits_merge_site_overrides_global():
    """站点 max_torrents_per_hour 覆盖全局; 未配置(None)回退全局"""
    g = global_conf(max_torrents_per_hour=12, max_torrents_per_day=60)
    assert HrLimits.merge(g, site_conf()).max_per_hour == 12
    assert HrLimits.merge(g, site_conf(max_torrents_per_hour=3)).max_per_hour == 3
    assert HrLimits.merge(g, site_conf()).max_per_day == 60


# ---------- split 模型(计划 26-09-27-1815 §2 M5.3): 双令牌桶 + 激活门 ----------


def _split_limits(**overrides):
    base = dict(min_interval=0.0, max_per_hour=12, max_per_day=60, failure_threshold=3, failure_cooldown=3600.0)
    base.update(overrides)
    return HrLimits(**base)


def test_split_bucket_starts_full_and_consumes():
    """tokens 未初始化(None)⇒ 首次按满桶计, 消费递减(不饿死旧文件迁移来的站点)"""
    quota = HrQuota()
    limits = _split_limits(page_burst=5, page_rate_per_hour=40)
    assert bucket_left(quota, limits, NOW, "page") == 5.0
    assert split_try_consume(quota, limits, NOW, "page") is True
    assert quota.tokens == 4.0 and quota.day_count == 1


def test_split_bucket_refills_by_rate_not_by_wallclock():
    """补充按「上次补充时刻 + 速率」连续计算 —— 幂等、消除整点突发"""
    quota = HrQuota()
    limits = _split_limits(page_burst=10, page_rate_per_hour=40)
    for _ in range(10):  # 打空桶
        assert split_try_consume(quota, limits, NOW, "page") is True
    assert split_try_consume(quota, limits, NOW, "page") is False, "burst 用尽后同轮不再发"
    # 900s 后按 40/时 = 10 个补充 ⇒ 桶里正好回到 10
    later = NOW + 900.0
    assert bucket_left(quota, limits, later, "page") == 10.0
    assert split_try_consume(quota, limits, later, "page") is True


def test_split_buckets_are_independent():
    """页面桶与下载桶互不影响(各自的账本 + 各自的 rate/burst/天顶)"""
    page = HrQuota()
    torrent = HrQuota()
    limits = _split_limits(page_burst=2, torrent_burst=8)
    assert split_try_consume(page, limits, NOW, "page") is True
    assert split_try_consume(torrent, limits, NOW, "torrent") is True
    assert bucket_left(page, limits, NOW, "page") == 1.0
    assert bucket_left(torrent, limits, NOW, "torrent") == 7.0


def test_split_day_cap_uses_window_key():
    """天级硬顶复用窗口键: 窗口翻篇即重置, 幂等不依赖进程存活"""
    quota = HrQuota()
    limits = _split_limits(page_burst=100, pages_per_day_max=3)
    for _ in range(3):
        assert split_try_consume(quota, limits, NOW, "page") is True
    assert split_try_consume(quota, limits, NOW, "page") is False
    due, why = split_next_allowed_at(quota, limits, HrFuse(), NOW, "page")
    assert "日配额" in why


def test_split_quota_survives_restart():
    """令牌桶跨重启不重置: (tokens, refill_ts) 持久化后 from_json 原样恢复, 补充按时刻现算"""
    quota = HrQuota()
    limits = _split_limits(page_burst=10, page_rate_per_hour=40)
    for _ in range(7):
        split_try_consume(quota, limits, NOW, "page")
    restored = HrQuota.from_json(quota.to_json())
    assert restored.tokens == quota.tokens and restored.refill_ts == quota.refill_ts
    # 重启 5 分钟后: 40/时 ⇒ 补充 ~3.33 个(桶里 3+3.33=6.33, 未满 10)—— 状态与速率一致
    later = NOW + 300.0
    assert 6.0 < bucket_left(restored, limits, later, "page") < 6.5


def test_split_next_allowed_respects_interval_and_tokens():
    """间隔门槛(min_page_interval / min_torrent_interval)与令牌补充等待都参与「最早可取时刻」"""
    quota = HrQuota()
    quota.tokens = 0.0
    quota.refill_ts = NOW
    limits = _split_limits(page_min_interval=90.0, page_rate_per_hour=40, page_burst=10)
    due, why = split_next_allowed_at(quota, limits, HrFuse(), NOW, "page")
    assert "间隔" in why, "刚消费过 ⇒ 间隔门槛先生效"
    # 桶几乎空 + 间隔已过 ⇒ 等令牌补充(下载桶 20/时: 90s 只补 0.5 个, 不足 1)
    torrent = HrQuota()
    torrent.tokens = 0.0
    torrent.refill_ts = NOW - 90.0
    tlimits = _split_limits(min_interval=90.0, torrent_rate_per_hour=20, torrent_burst=5)
    due, why = split_next_allowed_at(torrent, tlimits, HrFuse(), NOW, "torrent")
    assert "令牌补充" in why


def test_split_limits_merge_maps_site_overrides():
    """merge 的 split 映射: 站点 page_rate_per_hour / torrent_rate_per_hour 覆盖;
    旧覆盖键 max_torrents_per_hour 在 split 下映射为下载桶速率(用户已有配置不失效)"""
    glob = global_conf()
    site = site_conf(quota_model="split", max_torrents_per_hour=6)
    limits = HrLimits.merge(glob, site)
    assert limits.split is True
    assert limits.torrent_rate_per_hour == 6, "旧键 max_torrents_per_hour 继续作下载速率覆盖"
    assert limits.page_rate_per_hour == 40
    site2 = site_conf(quota_model="split", torrent_rate_per_hour=9, page_rate_per_hour=30)
    limits2 = HrLimits.merge(glob, site2)
    assert limits2.torrent_rate_per_hour == 9 and limits2.page_rate_per_hour == 30
    legacy = HrLimits.merge(glob, site_conf())
    assert legacy.split is False and legacy.quota_model == "legacy", "激活门: 未 opt-in 保持 legacy"
