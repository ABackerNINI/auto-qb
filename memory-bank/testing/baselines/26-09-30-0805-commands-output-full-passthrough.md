# 基线 · 1827 passed + 3 skipped / 91% —— commands 引擎全文透传(有损摘要退役)

> 摘要: 用户实贴 `commands run kb.baseline` 被截断的输出并定调: 截断逼 agent `show` → 裸跑两步返工,
> 会话后期每步都是带全量历史的整轮请求, token 税不可接受 —— **不能截断; 内部命令能静默的尽量静默**。
> 引擎 run.py: `_digest`/`_ANOMALY`/`ANOMALY_MAX`/`FAILURE_LINES` 退役, 成功/失败均**全文透传**
> (失败仅把 RESULT/WHY/NEXT/EVIDENCE 协议行剥出、紧跟 [FAIL] 转述一遍); 省 token 改**声明式**:
> silent_success 任务成功只出结论行(test.full/quick 保持, test.pkg 补旗标)。
> 引擎守阵两处重写(scripts/test_engine.py 15→17 项 / tests/test_commands_engine.py 摘要守阵 6→4);
> SKILL.md 与 pitfalls/kb/scripts.md 处置口径反写。单轮直改, 无计划文档。
> 基线时间: 2026-09-30 08:10
> 档案: memory-bank/tasks/26-09-28-commands-shipflow-output-contract.md(08:10 条)

TOTAL **1827 passed + 3 skipped / 91%**(12760 语句 / 1012 未覆盖 / 4320 分支 / 428 partial,
test.full 25.74s / 引擎墙钟 26.4s, rc=0) —— 较上基线 26-09-30-1210(1829 passed + 3 skipped)
**-2** = tests/test_commands_engine.py 摘要守阵 6 条换成全文透传守阵 4 条, 零用例语义变化。
语句 12650→12760 / partial 429→428 属覆盖率采样漂移(并行归因, 口径见 testing/baseline.md)。
⚠ 顺带观察: 6 条 starlette DeprecationWarning(per-request cookies)回潮 —— pytest.ini 的两条
消息前缀过滤与本版 starlette 新消息不匹配, 与本轮改动无关(未动 test_web/依赖), 待定调后入池。
⚠ 排序注: 存在一条内嵌/命名 12:10 的切片(26-09-30-1210, 本 clone 经同步见到它时 mtime 已是
07:4x) —— kb.baseline 按「基线时间」排序会把它排在本切片(08:10)之前; 成因未查(命名笔误或
写入方当时时钟偏移), 对比数字时以实际入库先后为准。

## 本轮改动面

- `.agents/skills/commands/scripts/run.py`: 全文透传 `_passthrough` + 声明式静默 `_conclusions`。
- `.agents/skills/commands/scripts/test_engine.py`: 15→17 项(透传/静默/失败全文)。
- `tests/test_commands_engine.py`: 摘要守阵重写 6→4; pick/wrapper/decode 守阵不动。
- `.commands/test/config.toml`: test.pkg 补 `silent_success = true`(真机验收: 72 passed 一行收尾)。
- `.agents/skills/commands/SKILL.md`: 输出契约段反写(2702/5200 字符)。
- 知识库: pitfalls/kb/scripts.md「输出摘要」条目处置反写 + 复发+1; 档案 26-09-28 08:10 条;
  activeContext 两切片(26-09-28-0203 / 26-09-23-2219)刷新。
