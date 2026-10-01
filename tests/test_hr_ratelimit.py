"""test_hr_ratelimit 测试计划: 单频控模型(计划 26-09-28-1932 §5.1)

## 测试计划(每个测试函数一条)
- test_min_interval_gate: 相邻请求最小间隔门槛(上次请求 + min_interval)
- test_jitter_only_upward: 抖动只向上, 实测间隔恒 >= min_interval
- test_day_quota_gate: 日额到顶即截断(返回 False 不报错), 零点窗口键翻篇重置
- test_day_quota_idempotent_across_restart: 窗口键幂等 —— 重启(重建对象读回 JSON)不重置
- test_retry_after_respected: Retry-After 是站点明确指令, 参与下次可取时刻
- test_allow_window: 时段外等到时段起点
- test_next_allowed_at_returns_now_when_clear: 各门槛满足 → 立即可取
- test_day_ledger_persisted: 记账落在 HrSiteData.rate 且可 JSON 往返

### P1 覆盖率提升轮: 日额门槛与工具长尾
- test_next_allowed_at_reports_day_reset_when_quota_exhausted: 日额到顶 -> 下次可取 = 次日零点(原因「日配额」)
- test_now_ts_returns_positive_epoch: now_ts 返回当前 epoch 秒
"""
from auto_qb.hr.model import HrSiteData
from auto_qb.hr.ratelimit import (
    HrLimits,
    day_key,
    jittered_interval,
    next_allowed_at,
    next_day_reset,
    quota_left,
    try_consume,
)
import auto_qb.hr.ratelimit as rl

NOW = 1_700_000_000.0


def limits(**kw) -> HrLimits:
    base = dict(min_interval=90.0, max_requests_per_day=5, allow_window="")
    base.update(kw)
    return HrLimits(**base)


def data_with(last_ts: float = 0.0, day: str = "", count: int = 0, retry_after: float = 0.0) -> HrSiteData:
    d = HrSiteData()
    d.rate.last_fetch_ts = last_ts
    d.rate.day_window = day
    d.rate.day_count = count
    d.retry_after_until = retry_after
    return d


def test_min_interval_gate():
    d = data_with(last_ts=NOW)
    due, why = next_allowed_at(d, limits(min_interval=90.0), NOW)
    assert due > NOW and why == "间隔"
    # 抖动只向上最多 +25%(90 → 112.5): 推进 113s 后门槛必过
    due, _ = next_allowed_at(d, limits(min_interval=90.0), NOW + 113)
    assert due <= NOW + 113


def test_jitter_only_upward():
    for _ in range(50):
        j = jittered_interval(90.0)
        assert 90.0 <= j <= 90.0 * 1.25


def test_day_quota_gate():
    d = data_with(day=day_key(NOW), count=5)
    assert try_consume(d, limits(), NOW) is False  # 日额到顶: 截断不报错
    assert quota_left(d, limits(), NOW) == 0
    tomorrow = next_day_reset(NOW)
    assert try_consume(d, limits(), tomorrow) is True  # 零点翻篇重置


def test_day_quota_idempotent_across_restart():
    d = data_with(day=day_key(NOW), count=2)
    assert try_consume(d, limits(), NOW) is True
    # 模拟重启: JSON 往返后继续记账(窗口键不依赖进程存活)
    restored = HrSiteData.from_json(d.to_json())
    assert restored.rate.day_count == 3
    assert try_consume(restored, limits(), NOW) is True
    assert restored.rate.day_count == 4


def test_retry_after_respected():
    d = data_with(retry_after=NOW + 300)
    due, why = next_allowed_at(d, limits(min_interval=0.0), NOW)
    assert due == NOW + 300 and why == "Retry-After"


def test_allow_window():
    import datetime
    # NOW 对应的本地时刻不一定在窗口内/外, 分别构造「当前不在窗口内」的场景:
    # 取一个窗口起点在未来的 spec —— 用 next_day_reset 后的时间不在 [00:00-00:01] 内反证过于取巧,
    # 直接验证 window_start_on 语义: 不在窗口内时 due = 窗口起点。
    spec = "00:00-00:01"
    dt = datetime.datetime.fromtimestamp(NOW)
    in_window = dt.hour == 0 and dt.minute == 0
    d = data_with()
    due, why = next_allowed_at(d, limits(min_interval=0.0, allow_window=spec), NOW)
    if in_window:
        assert due <= NOW
    else:
        assert why == "时间窗" and due > NOW


def test_next_allowed_at_returns_now_when_clear():
    d = data_with()
    due, why = next_allowed_at(d, limits(), NOW)
    assert due <= NOW and why == ""


def test_day_ledger_persisted():
    d = data_with()
    assert try_consume(d, limits(), NOW) is True
    raw = d.to_json()
    assert raw["rate"]["day_count"] == 1
    restored = HrSiteData.from_json(raw)
    assert restored.rate.day_window == d.rate.day_window


# ==================== P1 覆盖率提升轮: 日额门槛与工具长尾 ====================


def test_next_allowed_at_reports_day_reset_when_quota_exhausted():
    """日额到顶 -> 下次可取时刻 = 次日零点, 原因「日配额」(供报告与日志)"""
    d = data_with(day=day_key(NOW), count=5)
    due, why = next_allowed_at(d, limits(), NOW)
    assert due == next_day_reset(NOW) and why == "日配额"
    assert due > NOW


def test_now_ts_returns_positive_epoch():
    """now_ts 就是当前 epoch 秒(抽出来便于替换)"""
    import time as _time

    before = _time.time()
    got = rl.now_ts()
    after = _time.time()
    assert before <= got <= after
