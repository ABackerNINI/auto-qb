"""tests/clock.py(统一假钟 + wait_until 单点)的行为回归阵(计划 26-11-05-0118 S1/S3)

S2 注入 / S3 收敛全部依赖这两个单点, 语义漂移当场红。计时断言遵守
pitfalls/testing/timing-tolerance.md: 下界留刻度余量, 上界放宽到不可撞线。

## 测试计划

- test_fake_clock_satisfies_clock_protocol: FakeClock 满足生产 Clock protocol(构造期注入的契约)
- test_system_clock_reads_stdlib: SystemClock 两个读数与 stdlib 现值同窗
- test_fake_clock_advance_and_freeze: advance 相对推进/可负退, freeze 钉绝对时刻且之后可续走
- test_fake_clock_plugs_into_constructor_injection: src 组件构造期 clock 参数直接吃 FakeClock,
  now()/monotonic() 两个读数都随推进走( Clock protocol 注入口径的行为证明)
- test_fake_clock_swaps_module_single_point: 构造期缺省的组件经模块属性现取 SYSTEM_CLOCK,
  monkeypatch 换假钟同样生效(叶子兜底口径的行为证明)
- test_fake_clock_fixture_fresh: fake_clock 夹具每用例全新起点, 实例间互不共享(无模块级单例)
- test_wait_until_returns_fast_on_immediate_true: 条件立真零等待
- test_wait_until_times_out_without_oversleep: 超时返回 False, 不越过 deadline 多睡一拍以上
- test_wait_until_extra_check_on_timeout: 超时分支再判一次(旧 helpers 语义原样保留)
"""
from __future__ import annotations

import time

import pytest

from auto_qb.infra.clock import SYSTEM_CLOCK, Clock

import clock as clock_mod  # noqa: F401  (单点可导入性: 与 helpers 同层的裸名导入口径)
from clock import DEFAULT_CLOCK_START, FakeClock, wait_until
from platform_tolerance import SLEEP_LOWER_MARGIN_S


def test_fake_clock_satisfies_clock_protocol():
    """生产组件构造期收 clock: Clock 参数时, 测试传 FakeClock 必须即插即用"""
    assert isinstance(FakeClock(), Clock)
    assert isinstance(SYSTEM_CLOCK, Clock)


def test_system_clock_reads_stdlib():
    before_time = time.time()
    before_mono = time.monotonic()
    now = SYSTEM_CLOCK.now()
    mono = SYSTEM_CLOCK.monotonic()
    after_time = time.time()
    after_mono = time.monotonic()
    assert before_time <= now <= after_time
    assert before_mono <= mono <= after_mono


def test_fake_clock_advance_and_freeze():
    c = FakeClock()
    assert c.now() == DEFAULT_CLOCK_START
    assert c.advance(30.0) == DEFAULT_CLOCK_START + 30.0
    assert c.advance(-5.0) == DEFAULT_CLOCK_START + 25.0  # 负退合法(回拨场景)
    assert c.freeze(2_000_000_000.0) == 2_000_000_000.0  # 绝对时刻, 非相对量
    assert c.advance(1.0) == 2_000_000_001.0  # freeze 后续走


def test_fake_clock_plugs_into_constructor_injection():
    """构造期注入证明: src 组件(clock: Clock 参数)直接吃 FakeClock, 两个读数随推进走"""
    from auto_qb.core.taskqueue import Task, TaskQueue

    q = TaskQueue(clock=FakeClock(start=100.0))
    task = Task("internal", "maintenance", hash="h1", interval=60.0, handler=lambda t, dry: True)
    assert q.add_task(task)
    assert task.next_run == 100.0  # now() 读数来自注入钟(缺省 now=None 时现取)
    check = Task("check", "maintenance", hash="h2", interval=60.0, handler=lambda t, dry: True)
    assert q.add_task(check)
    assert q._active_checks["h2"] == 100.0  # monotonic() 读数同源(在途登记时刻)
    assert not q.add_task(
        Task("check", "maintenance", hash="h2", interval=60.0, handler=lambda t, dry: True)
    ), "同种子在途去重照常工作(读数面即注入钟)"


def test_fake_clock_swaps_module_single_point(monkeypatch):
    """叶子兜底口径证明: 构造期缺省的组件经模块属性现取 SYSTEM_CLOCK, 换假钟即整体接管"""
    from auto_qb.core import taskqueue as tq_mod
    from auto_qb.core.taskqueue import Task, TaskQueue

    monkeypatch.setattr(tq_mod, "SYSTEM_CLOCK", FakeClock(start=500.0))
    q = TaskQueue()  # 缺省钟在构造期经模块属性现取 -> 拿到的是假钟
    task = Task("internal", "maintenance", hash="h9", interval=60.0, handler=lambda t, dry: True)
    assert q.add_task(task)
    assert task.next_run == 500.0  # 读数随注入钟走


def test_fake_clock_fixture_fresh(fake_clock):
    assert fake_clock.now() == DEFAULT_CLOCK_START  # 每用例全新(函数级 = 自动复位)
    fake_clock.advance(123.0)
    assert FakeClock().now() == DEFAULT_CLOCK_START  # 自造实例不受影响(无模块级共享状态)


def test_wait_until_returns_fast_on_immediate_true():
    # S3 性能断言裁决(计划 26-11-05-0118): 挂钟上界按「被守回归的量级」定界(pitfalls/testing/
    # timing-tolerance)。被守回归 = 快路径混入一次节拍睡眠 —— interval 显式放大到 0.5s 后,
    # 一次真睡即 0.5s 必红; 上界 0.3s 对真实耗时(~0)余量 6x, 慢机/抢占不再撞线。
    t0 = time.perf_counter()
    assert wait_until(lambda: True, timeout=5.0, interval=0.5) is True
    assert time.perf_counter() - t0 < 0.3, "条件立真必须零等待快路径(混入一次 0.5s 节拍即红)"


def test_wait_until_times_out_without_oversleep():
    t0 = time.perf_counter()
    assert wait_until(lambda: False, timeout=0.1, interval=0.02) is False
    elapsed = time.perf_counter() - t0
    assert elapsed >= 0.1 - SLEEP_LOWER_MARGIN_S, "至少等满预算(下界余量 = 平台刻度容差单点, >=2 tick)"
    assert elapsed <= 0.1 + 0.02 + 0.3, "超时后一拍内收线(旧实现语义: 最多多睡一个 interval)"


def test_wait_until_extra_check_on_timeout():
    """轮询窗内恒 False、deadline 之外才翻真的条件: 仍返回 True —— 只更宽松不更严(旧语义)"""
    t0 = time.perf_counter()

    def _late():
        return time.perf_counter() - t0 >= 0.08

    assert wait_until(_late, timeout=0.05, interval=0.5) is True  # 单拍 0.5s 直接睡过窗, 靠终判命中
