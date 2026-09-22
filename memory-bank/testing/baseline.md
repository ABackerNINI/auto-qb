# 测试基线 (单点事实源)

> 摘要: 全库的测试基线数字 (passed / skipped / 覆盖率 / 耗时) **只在本文件维护** ——
> README / AGENTS.md / progress.md / 各主题文档一律**引用**此处, 更新基线时只改这里。
> 触发: 基线, 测试数字, passed, skipped, 覆盖率, 耗时, 改了测试, 记基线, 数字对不上

## 当前基线

**1185 passed + 1 skipped (Windows 本地, --no-cov 实测; 覆盖率未随本次重测, 上一次实测 TOTAL 90% / 7542 语句 / 623 未覆盖) / Linux (WSL 沙箱) 未重测(仍是 1060 passed + 2 skipped)** —— 2026-09-22 实测(状态周期落盘 issue 26-09-21-1347, +9 守阵) 

> ⚠ **只测一侧就更新会立刻产生漂移** —— 改了基线就把 Windows 与 Linux 两侧**都重测**再落数字。
> 两侧**收集数相同**但 passed 可能不同(Windows 专属用例在 Linux 上 skip), 比较时别拿 passed 直接比。

## 变更流水

逐次增量的完整流水(最近在上)已外迁 → [baseline-history.md](baseline-history.md)。
