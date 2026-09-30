# commands-shipflow-output-contract — commands/shipflow 输出契约

> 摘要: v3(成功一行/失败=原因+下一步/退出码 0/1, 4ba6cb7f)与 W2 推广(W2-1 charset 半装 / W2-2 结论行必保 / W2-3 警告 6→0 / W2-4 silent_success)已验收。**2026-09-30 终态修订: 引擎 run 全文透传不做有损摘要** —— 「略过 N 行」提示逼 agent show→裸跑两步返工(token 税, 用户定调), W2-2 的 `_digest` 退役; 静默改**声明式** silent_success(test.full/quick/pkg 成功只出结论行, 失败照旧全文)。全量 1827 passed + 3 skipped / 91%(基线 26-09-30-0805)。修订记录: 档案 08:10 条; pitfalls/kb/scripts.md「输出摘要」条目处置已反写。
> 最后活动: 2026-09-30 08:10

## 正在进行

- 2026-09-30 方向修订(全文透传 + 声明式静默)代码/守阵/文档/基线全部落盘, **待「提交」入库**。
- 遗留观察: 6 条 starlette per-request cookies DeprecationWarning 回潮(pytest.ini 消息前缀过滤与本版 starlette 新消息不匹配, W2-3 机制仍在) —— 与修订无关, 待定调后入池; clone2 的 cd.pyd 混态(纯美容, 按档案 04:19 条配方重跑即修复)。

## 已完成

- v3 全量落地 + 真机验收(4ba6cb7f): 档案进度日志 03:21/03:30 条。
- W2 推广(含 W2-4 成功静默): 档案进度日志 04:07/04:19/04:32/04:45 条。
- 计划文档: memory-bank/plans/26-09-28-0157-plan-commands-shipflow-v3.html(status Done)。
- 2026-09-30 方向修订: 档案进度日志 08:10 条; 基线切片 testing/baselines/26-09-30-0805-commands-output-full-passthrough.md。
