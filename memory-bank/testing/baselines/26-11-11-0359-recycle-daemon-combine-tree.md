# 5999 passed + 2 skipped —— rebase 合流组合树两侧测试合计全量绿(本分支 7 笔 + 远端 49 笔, 覆盖率 99%)

> 摘要: 5999 passed, 2 skipped (159.46s), 覆盖率 99% (26747 stmts) —— rebase 合流组合树(本分支 7 笔 rebase 后 + 远端 49 笔)两侧测试合计全量绿; 本切片为该组合树的测试数字权威
> 基线时间: 2026-11-11 03:59
**Refs:** memory-bank/issues/26-11-07-0528-feat-recycle-daemon-roster-machine-wide.html, memory-bank/plans/26-11-10-0318-plan-recycle-daemon-instance-evidence.html, memory-bank/tasks/26-11-10-backend-recycle-daemon-instance-evidence.md, memory-bank/pitfalls/backend/recycle-daemon-p7-evidence-chain.md

## 验收数字

```text
TOTAL                                                26747 (stmts, 覆盖率 99%)
5999 passed, 2 skipped in 159.46s (0:02:39)
```

(实测时点: rebase 合流组合树, `commands run test.full` 2026-11-11; 较实装批切片 26-11-11-0225 的 5939: +60 = 远端 49 笔合流带入的两侧合计新增用例, 2 skipped 为存量 skip 不变; 本切片为该组合树的测试数字权威, 其余处一律引用不手抄)

## 本改动面

- rebase 合流组合树(本分支 7 笔 rebase 后 + 远端 49 笔), 零新增代码面, 两侧测试合计; 测试数字权威=本切片。
- 合流 rebase 后提交对象重写(旧 hash 为 pre-rebase 引用, 新 hash 见 git log): fbcf4117→1f36dd18, a3c0fc1e→3fd8092c, 2ca40f43→eba5ba3b, 76c056ee→972d7cd5, 202c807e→2a26dd65, f3356c1f→9ae076de。

