# 6460 passed + 6 skipped / TOTAL 99% (99.74%, 语句 28864 / 未覆盖 43) —— qbmanager 启动序列 reload 挪前修复批基线

> 摘要: qbmanager 启动序列 reload 挪前修复批基线
> 基线时间: 2026-11-18 07:21

## 验收数字

```
6460 passed, 6 skipped in 182.52s (0:03:02)
TOTAL  28864  43  10304  60  99%
Required test coverage of 99.5% reached. Total coverage: 99.74%
```

- 对上一切片(26-11-18-0616 issues-26-11-17-2339-batch-fix)差值: passed +1(新增守阵 2 条: test_w6_reload_precedes_start_all_wiring / test_w6_startup_state_write_survives_run), skipped 不变; 修复轮前首跑曾 1 failed(test_kb_pitfall_entries_have_required_fields, 新坑档条目缺三必填字段), 坑档改写后本切片为干净重跑。

## 本改动面

- src/auto_qb/core/qbmanager.py: run() 启动序列 _reload_state / materialize_migration / next_flush_at 起点整体挪到 host.start_all 之前(issue 26-11-17-0214); _reload_state docstring 补摆位判据。
- src/auto_qb/core/modules/relocate_mod.py: 接管面写穿两处注释改口「接管即持久」语义面(代码零行为变化)。
- tests/test_qbmanager_w6.py: 新增守阵 2 条(顺序接线 + 行为), 文件头测试计划清单同步; 回归摆位红验双红后绿验。
- memory-bank 三面回写: 新坑档 pitfalls/backend/startup-state-write-reload-discard.md + kb.index; 架构 main-loop-queue.md 启动序列行; issue 26-11-17-0214 翻 Done + 复验/修复后补充; 任务档案 26-11-18-backend-qbmanager-startup-reload-discard.md 立档。
