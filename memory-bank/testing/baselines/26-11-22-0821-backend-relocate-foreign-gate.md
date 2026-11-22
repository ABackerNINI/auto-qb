# 6789 —— 6789 passed, 6 skipped —— backend-relocate-foreign-gate S4 验收⑥基线(计划 26-11-21-1600)

> 摘要: 6789 passed, 6 skipped —— backend-relocate-foreign-gate S4 验收⑥基线(计划 26-11-21-1600)
> 基线时间: 2026-11-22 08:21
**Refs:** memory-bank/tasks/26-11-22-backend-relocate-foreign-gate.md

## 验收数字

`commands run test.full` 实测(2026-11-22 08:16, Windows, 2m42s, 树 = 41000b0c, 分支 relocate-foreign-gate-s4):

```
TOTAL                                                30681     85  10942     87    99%
6789 passed, 6 skipped, 8 warnings in 161.67s (0:02:41)
```

覆盖率闸门通过(99% 线 rc=0)。与上基线(26-11-22-0533, 6789P/6S)相比 passed/skipped 持平; 两基线树间仅两笔纯文档/issue 提交(7fb43e91/41000b0c)零代码变更, TOTAL 表 miss 83→85 / partial 86→87 为字节级漂移, 覆盖率同为 99% 无回退。

## 本改动面

本轮 = 计划 26-11-21-1600 S4 真机验收判据⑥(test.full 全绿 + 基线切片), 纯验收轮零代码变更:

- 树 = 41000b0c(分支 relocate-foreign-gate-s4), 代码与上基线(树 4e0c6662)完全一致, 其后仅 7fb43e91(S1-S3 收尾回写)与 41000b0c(范围外两件入池)两笔纯文档/issue 提交。
- S4 真机验收(计划验收⑤六条, 完整整组迁移全链复验)由主会话真机窗口执行, 不在本切片范围; 本切片只承载判据⑥(test.full 全绿 + 基线切片)。
