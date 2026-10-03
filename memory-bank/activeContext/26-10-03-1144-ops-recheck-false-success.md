# ops-recheck-false-success — full-checking 轮询首跳误判校验成功

> 摘要: 用户报 WEB UI 批量 recheck 后 1.1s 即显示「校验成功」而实际仍在校验, 排查确认 ops poll 成功分支缺陷: `OpsModule.recheck` 闭包 `poll`(ops_mod.py) 的成功分支 `if rec.progress >= 1.0` 未要求 `seen_checking` 前置, 已完成种子提交 recheck 后首跳(入队即到期)读到校验前快照(progress=1.0、不在 checking)即误判成功并消亡。规则源同路径更重: 假成功会 on_success 假晋升 verified_references + origin keep_progress 续跑。已入池 [issue 26-10-03-1140](../issues/26-10-03-1140-bug-ops-recheck-false-success.html)(bug/standard, Open, 含完整证据/锚点/建议修法与取舍), **未认领未修, 等用户指派**。

> 最后活动: 2026-10-03 11:44
