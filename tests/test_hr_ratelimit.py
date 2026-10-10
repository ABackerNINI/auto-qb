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

### hr 首轮变异审计轮: 频控窗口 / 端点 / 取值守阵(issue 26-10-10-1108-judgment-core)
- test_hr_limits_merge_carries_allow_window: merge 三字段原样搬自全局配置(allow_window 不得丢)
- test_day_key_exact_local_date_format: 天窗口键格式钉死 "%Y-%m-%d"(持久化契约)
- test_next_day_reset_is_exact_next_midnight: 日额重置 = 次日零点整
- test_window_start_on_pins_start_endpoint_and_rollover: 窗口起点取起点端 + 顺延 + 精确归零
- test_next_allowed_at_takes_latest_gate_and_reason: 多门槛取最晚者 + 对应原因
- test_next_allowed_at_clear_returns_empty_reason: 候选存在但都 <= now -> now + 空原因
- test_next_allowed_at_exact_due_equals_now_is_clear: due 恰等 now 视为已满足(<= 而非 <)
"""
import random

from auto_qb.hr.model import HrSiteData
from auto_qb.hr.ratelimit import (
    HrLimits,
    day_key,
    jittered_interval,
    next_allowed_at,
    next_day_reset,
    quota_left,
    try_consume,
    window_start_on,
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


# ==================== hr 首轮变异审计轮: 频控窗口 / 端点 / 取值守阵 ====================

import datetime as _dt


def _ts(y, mo, d, h, mi, s=0):
    return _dt.datetime(y, mo, d, h, mi, s).timestamp()


class _GlobalConf:
    """HrLimits.merge 的最小入参桩(只取三个字段)"""

    min_interval = 90.0
    max_requests_per_day = 240
    allow_window = "08:00-20:00"


def test_hr_limits_merge_carries_allow_window():
    """merge 三字段原样搬自全局配置(allow_window 不得丢成 None / 默认空串)"""
    lim = HrLimits.merge(_GlobalConf())
    assert lim.min_interval == 90.0
    assert lim.max_requests_per_day == 240
    assert lim.allow_window == "08:00-20:00"


def test_day_key_exact_local_date_format():
    """天窗口键格式钉死 "%Y-%m-%d"(它是 state.json 持久化契约, 换格式 = 窗口静默重置)"""
    assert day_key(_ts(2026, 3, 7, 15, 30)) == "2026-03-07"
    assert day_key(_ts(2026, 12, 31, 23, 59)) == "2026-12-31"


def test_next_day_reset_is_exact_next_midnight():
    """日额重置 = 次日零点整(hour/minute/second/microsecond 全归零 + 86400)"""
    now = _dt.datetime(2026, 3, 7, 15, 30, 45, 123456).timestamp()
    assert next_day_reset(now) == _ts(2026, 3, 8, 0, 0)
    assert next_day_reset(_ts(2026, 3, 7, 0, 0)) == _ts(2026, 3, 8, 0, 0)


def test_window_start_on_pins_start_endpoint_and_rollover():
    """窗口起点: 取 spec 的**起点**端, 当天已过则顺延次日; 时分秒/微秒精确归零"""
    now = _dt.datetime(2026, 3, 7, 15, 30, 45, 123456).timestamp()
    # 15:30 已过 08:00 -> 顺延次日 08:00
    assert window_start_on(now, "08:00-20:00") == _ts(2026, 3, 8, 8, 0)
    # 03:00 未到 08:00 -> 当天 08:00
    assert window_start_on(_ts(2026, 3, 7, 3, 0), "08:00-20:00") == _ts(2026, 3, 7, 8, 0)
    # 起点恰为 now: 仍顺延次日(严格 ts > now)
    assert window_start_on(_ts(2026, 3, 7, 8, 0), "08:00-20:00") == _ts(2026, 3, 8, 8, 0)


def test_next_allowed_at_takes_latest_gate_and_reason():
    """多个门槛并存: 取最晚者, 原因取对应门槛(不是先到 / 按原因字符串排)"""
    d = data_with(last_ts=NOW, retry_after=NOW + 500)
    due, why = next_allowed_at(d, limits(min_interval=90.0), NOW)
    assert due == NOW + 500 and why == "Retry-After"


def test_next_allowed_at_clear_returns_empty_reason():
    """门槛都已满足(候选存在但都 <= now): 返回 now 且原因为空串(不是占位串)"""
    d = data_with(last_ts=NOW - 1000)
    due, why = next_allowed_at(d, limits(min_interval=90.0), NOW)
    assert due == NOW and why == ""


def test_next_allowed_at_exact_due_equals_now_is_clear():
    """due 恰等于 now 视为已满足(<= 而非 <): 原因空串"""
    j = 90.0 * (1.0 + random.Random(7).random() * 0.25)
    last = NOW - 1000.0
    now = last + j
    d = data_with(last_ts=last)
    due, why = next_allowed_at(d, limits(min_interval=90.0), now, rng=random.Random(7))
    assert due == now and why == ""
