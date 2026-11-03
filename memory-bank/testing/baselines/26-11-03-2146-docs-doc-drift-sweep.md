# 4994 passed + 10 skipped(根) —— 文档漂移 7 条修复收尾全量基线

> 摘要: 文档漂移 7 条（评审计划 0557 + 端口口径）修复收尾，零源码改动全量基线
> 基线时间: 2026-11-03 21:46
**Refs:** memory-bank/tasks/26-11-03-docs-doc-drift-sweep.md, memory-bank/plans/26-11-03-0557-plan-full-code-review-3.html

## 验收数字

`commands run test.full` 实测(零源码改动, 套件 214.7s; 索引重建后终跑):

```text
TOTAL                                                23292    185    7948    158    99%
4994 passed, 10 skipped, 3 warnings in 210.93s (0:03:30)
```

口径注记:
- 3 条 warning 与 10 条 skipped 均为既有存量, 口径见前一条基线切片;
- 本轮零源码改动, 未新增/删除用例; passed/skipped/TOTAL 与前一条切片完全一致, 通过面未退化。

## 本改动面

- 纯文档, 零源码: 计划 `26-11-03-0557` 回写域表/基线引用/在途清单/底册数字; 0221 计划与 1036 报告
  清理 9 条 v.Nu error 并恢复与 0557 的双向 doc-refs; `minimal.yml` 端口示例 16585→8080;
  `config-reference/loading-and-write.md`、`docs/sim-client-test-howto.md` 端口口径修正。
- 未改 `src/`、`tests/`、`scripts/`、`config.yml`、`auto-qb-data/`。
- 录制于收尾提交前的工作树; 提交随本轮单笔完成。
