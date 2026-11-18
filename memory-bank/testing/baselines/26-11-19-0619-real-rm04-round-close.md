# 6373 —— RM04 真机复验轮收口全量基线

> 摘要: RM04 真机复验轮收口全量基线(relocate-rm-r2 tip 3bef94ae + 收口文档回写工作树)
> 基线时间: 2026-11-19 06:19

## 验收数字

`commands run test.full` 实测(2026-11-19 06:16, Windows; 3m04s):

```
TOTAL                                                28371     37  10100     54    99%
Required test coverage of 99.5% reached. Total coverage: 99.76%
6373 passed, 2 skipped, 1 warning in 184.02s (0:03:04)
```

包内守阵: `commands run test.pkg` **520 passed + 15 subtests**(2026-11-19 05:5x 实测)。
稳定性: 收口轮 test.full 实跑 4 次(修坑档守阵前 2 次 + 修后 2 次)passed/skip/TOTAL 逐位一致。

## 本改动面

- **树**: 分支 `relocate-rm-r2`(本地无远端)tip `3bef94ae`(片G), 工作树含本收口轮文档回写(零 pytest 面改动)。
- **相对上基线(26-11-17-0447, 树 ≈ 12ff9a1e)的入库面**(12ff9a1e..HEAD 19 笔): ①relocate 重构第一批 pytest 侧守阵随线性重放入库(S1a~S4 + 收尾追修 24e8d063; test_relocate_supersede 重写 / test_relocate_units / test_relocate_startup_reconcile / test_web_commands_bulk / webui relocate 系等); ②覆盖率补测到闸门绿(2b78e9d7, 44 用例 +1362 行, 零 src 改动); ③port-kill 克隆域归属硬闸守阵(db098311); ④RM04 真机复验轮 9 笔(923f2e32 片A 记账切片+坑档 / 1a6b57c9 片A-fix 18 条适配 / 8bf6ffc5 链浮窗 issue 入池 / 5a6ae255..3bef94ae 片B~G 13 条新增用例)—— 真机轨在 tests-real/rm04_relocate/, 不进 pytest 收集面(testpaths=tests/), 逐遍数字单点在 testing/real-baselines/ 八份切片(26-11-17-0756 → 26-11-19-0505)。
  - tests/ 合计口径(①~④ 全范围): 23 文件 +4204/-472(git diff 12ff9a1e HEAD --stat -- tests/), 非①单条子范围。
- **收口轮文档面(零测试代码)**: issue 七条翻 Done(0528/0326/0535/0711/0553/0420/0401); 两计划回写(26-11-17-0636 §10 R3 + §03.4 RM04-25 卡勘误 / 26-11-15-2340 §03.6 状态列 + §10 R3); 任务档案 R2 段; 坑档新立 2(state-file-lag-and-journal-absence / restart-transient-and-offline-cmd-window)+ 追加 2(seed-clean-vs-evidence 复发+1 / bg-process-cleanup 孤儿证伪); kb.index 重建; 基线切片(本件)。
