"""测试侧时间控制单点: 统一假钟 FakeClock + 条件轮询 wait_until(flaky 治理计划 26-11-05-0118 S1/S3)

生产时钟单点在 ``src/auto_qb/infra/clock.py``(Clock protocol + SYSTEM_CLOCK); 本文件是它的
测试侧对偶: S3 已把全部旧假钟迁删, tests/ 的时间控制只走本单点 —— 新用例禁止再造假钟类
或裸 time.sleep 轮询(守阵 tests/test_flaky_timing_guards.py 拦)。

## 用法规范

1. **拿假钟**: 夹具 ``fake_clock`` 每用例发一个全新实例(函数级自动复位 —— 用例间零共享,
   xdist 每 worker 是独立进程, 本就没有跨 worker 状态; 也因此**不做模块级共享**, 想跨用例
   复用状态就是制造顺序依赖)。要特定起点就 ``FakeClock(start=...)`` 自造, 常量起点优于
   ``time.time()`` 实测值(跨零点/分钟戳类 flaky 的根)。
2. **注入**: 生产组件构造期收 ``clock: Clock`` 参数的, 直接把 FakeClock 传进去 ——
   ``now()`` / ``monotonic()`` 与生产 Clock protocol 同形, 挂钟与单调钟返回同一可推进值。
   既有 callable 口径的注入位(如 hr 域 ``now_fn=``)传绑定的读数 ``clock.now`` 即可;
   经模块级 SYSTEM_CLOCK 单点取时的叶子, 测试期 ``monkeypatch.setattr(模块, "SYSTEM_CLOCK",
   fake_clock)`` 整体换钟(旧"monkeypatch 模块内 time 名"形态已随旧假钟一并退役)。
3. **推进时间**: ``fake_clock.advance(30.0)`` 相对推进(可负退), ``fake_clock.freeze(at)``
   钉死到绝对时刻(下一拍再 advance 继续)。断言**区间不精确值**: 冻结后断言">= 起点",
   推进后断言"落在 [a, b) 窗口" —— 完全冻结 + 精确相等对实现内部细节太脆(业界共识)。
4. **等线程/后台副作用**: 只用 ``wait_until(cond)``, 不裸 time.sleep 固定睡等 —— 睡短了
   flaky、睡长了慢。条件轮询命中即返回, 快路径零等待; 超时返回 False 让断言给可读信息。
   能用 Event/Queue 事件同步的优先事件同步, wait_until 是轮询兜底不是首选。
5. **真睡的唯一合法位**: wait_until 自身的节拍睡眠(白名单单点 tests/flaky_allowlist.py
   里带理由登记, 机器可清点); 其余 tests/ 裸 time.sleep 守阵即红。

依赖纪律: 只 import 标准库与 pytest —— 不 import helpers(方向反过来: 调用点一律直连
``from clock import ...``, helpers 不再再导出本模块符号)。
"""
from __future__ import annotations

import time
from typing import Callable

import pytest

__all__ = ["DEFAULT_CLOCK_START", "FakeClock", "fake_clock", "wait_until"]

#: 假钟默认起点: 一个远离零点/遥远离今的整值 epoch —— 天数/月份/分钟戳都确定,
#: 且 Windows 上 datetime.timestamp() 安全(负 epoch/1970 附近有 OSError 坑,
#: 见 pitfalls/testing/win-fake-clock-timestamp-oserror.md)。
DEFAULT_CLOCK_START = 1_700_000_000.0


class FakeClock:
    """统一假钟: 可推进的 Clock 替身(生产 SystemClock 的测试对偶) —— Clock protocol 单一形态

    ``now()`` / ``monotonic()`` 与生产 Clock protocol 同形(构造期 ``clock=`` 参数直接传入,
    test_clock.py 有构造期注入的行为证明); ``advance()`` / ``freeze()`` 是测试侧专属的
    推进控制(生产代码对时钟只读, 见 infra/clock.py 的取时纪律)。旧假钟时代的属性/可调用
    形态已在 S3 迁移中改写, 单一形态不再并存: ``clock.now`` 读 -> ``clock.now()``;
    ``clock.now = t`` -> ``clock.freeze(t)``; ``now_fn=clock`` -> ``now_fn=clock.now``。
    """

    __slots__ = ("_now", )

    def __init__(self, start: float = DEFAULT_CLOCK_START) -> None:
        self._now = float(start)

    def now(self) -> float:
        """挂钟 epoch 秒(Clock protocol): 与 monotonic() 返回同一可推进值"""
        return self._now

    def monotonic(self) -> float:
        """单调秒(Clock protocol): 与 now() 返回同一可推进值"""
        return self._now

    def advance(self, seconds: float) -> float:
        """相对推进(可负退), 返回推进后的时刻 —— 便于链式断言区间"""
        self._now += float(seconds)
        return self._now

    def freeze(self, at: float) -> float:
        """钉死到绝对时刻(非相对量), 返回该时刻; 之后 advance 照常继续走"""
        self._now = float(at)
        return self._now


@pytest.fixture
def fake_clock() -> FakeClock:
    """每用例一个全新假钟(函数级 = 自动复位; 不做模块级共享, 理由见模块 docstring)"""
    yield FakeClock()


def wait_until(
    cond: Callable[[], bool],
    timeout: float = 3.0,
    interval: float = 0.02,
) -> bool:
    """条件轮询等待: cond() 命中即返回 True, 超时返回 False(收编单点, 计划 26-11-05-0118 S3)

    tests/ 等线程/后台副作用的**唯一**等待入口(旧 helpers.wait_until 与 drive_skip 的
    内联轮询循环均已收编至此; 既有调用点已全部直连本实现, helpers 不再再导出)。

    - 轮询节奏: 每 ``interval`` 秒试一次, 快路径(cond 立即为真)零等待; 逐字保留旧实现的
      睡眠节奏(不按剩余预算截断), 既有调用点的等待语义零漂移。
    - 超时分支**再判一次** cond(): 最后一拍窗口内条件刚好翻转时多给一次机会 —— 方向只会
      更宽松, 不放宽任何断言语义(旧实现的抗 flake 语义, 原样保留)。
    - 预算用 time.monotonic() 计, 不受系统调钟影响。
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if cond():
            return True
        time.sleep(interval)
    return cond()  # 超时分支再判一次: 只更宽松, 不更严
