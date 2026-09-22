# 测试基线 (单点事实源)

> 摘要: 全库的测试基线数字 (passed / skipped / 覆盖率 / 耗时) **只在本文件维护** ——
> README / AGENTS.md / progress.md / 各主题文档一律**引用**此处, 更新基线时只改这里。
> 触发: 基线, 测试数字, passed, skipped, 覆盖率, 耗时, 改了测试, 记基线, 数字对不上

## 当前基线

**1177 passed + 1 skipped (Windows 本地, 覆盖率 TOTAL 90%, 7541 语句 / 624 未覆盖) / Linux (WSL 沙箱) 未重测(仍是 1060 passed + 2 skipped)** —— 2026-09-22 实测(热重载 L2 state 回滚修复后: +1 守阵 `test_apply_new_config_l2_preserves_runtime_state`; 删 1 条已覆盖语句, 语句 7542→7541; miss ±1 的逐次抖动判为 server 线程路径的度量噪声, 见变更流水) 

> ⚠ **只测一侧就更新会立刻产生漂移** —— 改了基线就把 Windows 与 Linux 两侧**都重测**再落数字。
> 两侧**收集数相同**但 passed 可能不同(Windows 专属用例在 Linux 上 skip), 比较时别拿 passed 直接比。

## 变更流水

逐次增量的完整流水(最近在上)已外迁 → [baseline-history.md](baseline-history.md)。
