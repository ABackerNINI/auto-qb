"""测试侧平台容差单点: 平台相关容差常量 + 跨平台断言规范(flaky 治理计划 26-11-05-0118 S6/D6)

D6 拍板: 平台差异**机制化、不做生产抽象层** —— 本文件只是测试侧的容差常量与规范单点,
不含任何生产平台分支; 生产代码的平台差异归 src/ 各模块自身(如 PlatformChannel)。

## 规范(正文单点: memory-bank/testing/file-conventions.md「跨平台断言规范」节)

1. **挂钟"下界"计时断言**(sleep/wait/退避真发生类守阵的 elapsed >= X): 余量一律用
   ``SLEEP_LOWER_MARGIN_S``, 禁止手写 0.02 / 0.05 类刻度魔数。依据: Windows 等待原语按
   15.6ms 定时器刻度取整, 50ms 等待实测可提前到 46.8ms(2026-09-22 假红); 余量 >= 2 tick
   覆盖取整方向翻转(Win11 timer coalescing / 其它进程 timeBeginPeriod)。被守回归
   (空转/跳过/归零)是微秒级, 30ms 级余量不损失判别力。判别与实证:
   memory-bank/pitfalls/testing/timing-tolerance.md。
2. **挂钟"上界"不做对称刻度余量**: 合法负载 / CI 抢占直接撞线(2026-10-05 实测 4.01s 撞
   3.0s 上界)。性能上界优先换 ``time.process_time``(CPU 时间); 非用挂钟不可时放宽到
   不可撞线的量级(如"至少几十倍于被测量")。
3. **平台分支测试主体用 monkeypatch 固定平台**, 不依赖运行环境; "本地全量绿"不构成
   跨平台成立的证据(本机 Windows, CI 跑 Linux)。判别与实例:
   memory-bank/pitfalls/testing/patching.md 与 ci-only-guard.md。
4. **平台相关 skipif 强制带理由 + 负责人**: reason 写明平台语义依据(不是"仅 Windows"一句话,
   而是"该断言依赖的语义在另一侧为何不成立"); 装饰器行范围(或其上一行)带 ``# owner: <名>``;
   skip 的处置按 flaky 台账口径(flaky-ledger.md「巡检约定」)留 issue 链接。
   守阵: tests/test_platform_tolerance_guards.py(缺 owner / 缺 reason 即红)。
5. **跨平台断言禁写死仅一侧成立的形状**: 前缀切片长度 / 路径分隔符 / 大小写折叠语义 /
   仅一侧存在的模块常量 —— 按平台分支分别断言, 不写"两侧共用的单一期望值"。

依赖纪律: 只 import 标准库 —— 不 import pytest/helpers(与 clock.py 同口径)。
"""
from __future__ import annotations

__all__ = ["SLEEP_LOWER_MARGIN_S", "WIN_TIMER_TICK_S"]

#: Windows 等待原语(Event.wait / Sleep)的定时器刻度: 15.6ms(64Hz 系统定时器)。
#: 实测与判别法见 memory-bank/pitfalls/testing/timing-tolerance.md。
WIN_TIMER_TICK_S: float = 0.0156

#: 挂钟"下界"计时断言的统一余量: >= 2 tick(31.2ms)。
#: 用法: ``assert elapsed >= nominal - SLEEP_LOWER_MARGIN_S``。
#: 上界断言**不**用它(规范第 2 条) —— 挂钟上界的假红来自负载不是刻度, 加余量治不了。
SLEEP_LOWER_MARGIN_S: float = 2 * WIN_TIMER_TICK_S
