"""生产时钟单点: Clock protocol + SystemClock(flaky 治理计划 26-11-05-0118 S1)

取时纪律: 生产代码一律不裸调 time.time()/time.monotonic() —— 全仓取时点从这里走(守阵
tests/test_flaky_timing_guards.py 扫 src/ 裸取时, 本模块是唯一路径豁免)。组件需要时间时:
- 组件/类: 构造期收 ``clock: Clock`` 参数, 默认值用 :data:`SYSTEM_CLOCK`(D8 拍板: 构造期
  注入统一制, 默认系统时钟, 无全局可变时钟) —— 测试构造时传入 tests/clock.py 的假钟即可
  完全控制时间, 不真睡、不受跨零点/时钟粒度抖动影响;
- 叶子纯函数(不便改签名): 直接读 :data:`SYSTEM_CLOCK`(``from auto_qb.infra import clock``),
  或同样加 clock 参数 —— 能注入就注入, 单点是兜底不是常态。

两种读数的语义边界(选错是 flaky 根因, 见 pitfalls/testing/timing-tolerance.md 等):
- ``now()`` 挂钟 epoch 秒: 落盘时间戳 / 按天切块 / 对外展示 —— 受用户调钟影响, 跨零点、
  跨 DST、同秒重复等语义都挂在这一侧;
- ``monotonic()`` 单调秒: 时长测量 / 超时预算 / 节流间隔 —— 不受调钟影响; 0 点是机器
  开机时刻不是"很久以前", 拿 0.0 当"从未发生"哨兵是已知坑
  (pitfalls/testing/monotonic-warn-sentinel.md), 注入 Clock 后哨兵改用 None。

依赖纪律: infra 只被依赖 —— 本模块只 import 标准库, 不 import 任何包内模块。
"""
from __future__ import annotations

import time
from typing import Protocol, runtime_checkable

__all__ = ["Clock", "SystemClock", "SYSTEM_CLOCK"]


@runtime_checkable
class Clock(Protocol):
    """时钟协议: 生产组件构造期注入的唯一时间面

    只承诺两个读数, 不承诺推进控制 —— "把时间拨快 N 秒"是测试侧假钟(tests/clock.py
    FakeClock)的专属能力, 生产代码对时钟只有读权限。实现方须同时提供挂钟与单调钟两个
    读数(测试假钟两者返回同一可推进值, 语义边界由调用方按上面的纪律把握)。
    """
    def now(self) -> float:
        """挂钟 epoch 秒(time.time() 语义): 时间戳 / 按天切块 / 对外展示用。"""
        ...

    def monotonic(self) -> float:
        """单调秒(time.monotonic() 语义): 时长测量 / 超时预算 / 节流用, 不受调钟影响。"""
        ...


class SystemClock:
    """系统时钟(Clock 的生产实现): 直接读 stdlib, 无状态、可任意共享"""

    __slots__ = ()

    def now(self) -> float:
        return time.time()

    def monotonic(self) -> float:
        return time.monotonic()


#: 进程级共享单点: 无状态只读, 各组件默认参数统一用它, 不必每组件各造一个实例。
#: 仅当某组件测试需要独立假钟时才由调用方传入替身 —— 那是构造期注入, 不是替换本单点。
SYSTEM_CLOCK = SystemClock()
