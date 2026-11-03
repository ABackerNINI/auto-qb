# 4994 passed + 10 skipped(根) —— 整组迁移同盘证明误拒分析轮全量

> 摘要: 整组迁移同盘证明误拒分析轮全量
> 基线时间: 2026-11-03 22:25
**Refs:**

## 验收数字

`commands run test.full` 实测输出誊写：

```text
TOTAL                                                23292    187   7948    158    99%
4994 passed, 10 skipped, 3 warnings in 242.58s (0:04:02)
```

口径：仓库根全量；上一行为 test.full 的覆盖率 TOTAL 表原样誊写，下一行为 pytest 汇总行。本轮无代码改动，仅文档与知识库回写。

## 本改动面

文档面：新建计划 `memory-bank/plans/26-11-03-2212-plan-relocate-same-fs-proof.html`、任务档案 `memory-bank/tasks/26-11-03-backend-relocate-same-fs-proof.md`、切片 `memory-bank/activeContext/26-11-03-2225-relocate-same-fs-proof.md`、本基线切片；`kb.new` 自动补双向链并重建 `plans/_index.md`、`reports/_index.md`、`tasks/_index.md`、`plans/attachments/_archive.md`、`tasks/attachments/_archive.md`。

代码面：无改动（`src/`、`tests/`、`config.yml`、`auto-qb-data/` 均未触碰）。
