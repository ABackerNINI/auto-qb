# 2621 —— memory-bank 三项 cap 债务清理 (切片 128→67 · issues 索引截断 · webui 已实现轮转)

> 摘要: 清理会话一次收口三项 cap 债务 —— ①`activeContext/` 切片 128 → 67(删 61 片: 无入链 + 已完结)
> ②`issues/_index.md` 26,260 → 20,620(`gen_issues_index` 补 `SUMMARY_MAX = 40` 摘要截断) ③
> `progress/implemented-webui.md` 21,172 → 9,407(最老 13 条原文外迁 `implemented-webui-history.md`)。
> **本轮零 src/tests 改动**, 测试数字与上基线持平。
> 基线时间: 2026-10-05 18:30

**Refs:** memory-bank/activeContext/26-09-30-2112-memory-bank-cap-debt.md

- 分支: develop @ f98385a5 + 工作区改动(未提交, 等用户提交指令)
- 命令: `commands run test.full`(Windows)
- **实测 (Windows)**: **2621 passed + 4 skipped, 40.32s / 40.62s(两次采样), 覆盖率 TOTAL 99%**
  (15813 语句 / 167 未覆盖 / 5398 分支 / 140 partial; 门槛 98% 达标)
- 相对上一基线 [26-10-05-1814](26-10-05-1814-qb-traffic-v3-decimal-interval.md)(2619 passed + 4 skipped):
  passed **+2**, 而语句 / 分支计数**逐字相同**(15813/167/5398/140) ⇒ 非新增用例(应为 sync 合入的参数化
  重排, 该上基线记的是 c2ba6054 + 工作区, 与 f98385a5 之间夹着另一 clone 的提交)。本轮是知识库维护轮,
  **零 src/tests 改动**, 该 +2 非本轮引入。
- 本轮改动面: `.agents/skills/create-issue/scripts/gen_issues_index.py`(新增 `SUMMARY_MAX` 截断 +
  头部说明) / `memory-bank/progress/implemented-webui.md` 与 `implemented-webui-history.md`(cap 轮转 +
  行尾归一 LF) / `memory-bank/activeContext/`(删 61 片) / `activeContext/26-09-30-2112-memory-bank-cap-debt.md`
  (记录本轮清理) / 生成物 `_index.md` 族。
- 守卫: `commands run doc.caps` 债务 **0 项** / `commands run kb.check` 绿 / `commands run doc.links` 绿 /
  `tests/test_memory_bank.py` 32 passed。
