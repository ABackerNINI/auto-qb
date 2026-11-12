# 6012 passed, 2 skipped —— webui 组行 hash 引用式联合计划批次全量基线

> 摘要: 6012 passed, 2 skipped (194.31s), 覆盖率 99% (26747 stmts / 55 miss / 9362 br / 67 partial) —— webui 组行 hash 引用式联合计划(26-11-11-0630)S0-S5 批次收尾全量绿(S6 收尾切片)
> 基线时间: 2026-11-13 00:27
**Refs:** memory-bank/tasks/26-11-11-webui-group-hash-ref.md, memory-bank/plans/26-11-11-0630-plan-webui-group-hash-ref.html

## 验收数字

- 汇总行: `6012 passed, 2 skipped in 194.31s (0:03:14)`(commands run test.full 实测誊写)
- 覆盖率 TOTAL 表: `26747 stmts / 55 miss / 9362 br / 67 partial -> 99%`
- 与上一切片 [26-11-11-0659](26-11-11-0659-memory-bank-nav-pull-retry.md)(6007/2)差值: +5 passed —— 区间 73b99d09..a139dedd(S0-S5 五批)新增测试面(tests/ 12 件 +604/-120, 新增 5 个测试函数: S1/S2 守阵电池与协议形状单测为主), 明细随各批提交信息

## 本改动面

- 本切片 = 联合计划 26-11-11-0630 全批次(S0-S5)收尾: 生产代码改动集中在 S1-S3 三批(22a35b18 / f58b4a05 / de1fe327), S4 守阵(e2e 协议形状用例, d7e6bc23), S5 复评与裁决(纯文档, a139dedd); 改动面明细单点 = 任务档案 26-11-11-webui-group-hash-ref.md(本切片零生产代码改动, 纯文档/记账/issue 面)
- S6 收尾批本切片覆盖的记忆库面: `memory-bank/architecture/webui.md`(组行 hash 引用式 / 载荷结论 / ingestion 物化缝 / version-reload 四处增量回写); 两 issue 26-10-07-1420 / 26-10-08-0411 补「修复后补充」+ 翻 Done; 新坑三条(pitfalls/testing/fake-seed-injection.md, pitfalls/ops/dev-run-background-shutdown.md, pitfalls/ops/seed-clean-vs-evidence.md)+ kb.index 重建; 载荷/耗时等测量数字单点 = 任务档案 S0/S5 两节(不在此复抄)
