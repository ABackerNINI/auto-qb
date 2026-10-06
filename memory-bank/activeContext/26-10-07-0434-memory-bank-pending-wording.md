# 回写措辞: 禁时点相对的状态断言 + 机械守卫 (Done)

> 摘要: 用户问「任务档案与 activeContext 切片里仍写着『`待提交`』—— 提交时点 commit hash 尚不可知, 有什么方法解决」, 拍板「实施方案①(时不变措辞) + 机械守卫」。根因 = **自指不可能**: commit 的 hash 由 tree + parent + 时间戳决定, 想写进文件就改了 tree ⇒ 一个提交永远无法包含自己的 hash; 而收尾 DoD 要求回写件随主提交一并暂存, 于是那句断言写在 hash 尚不存在的时点。落地 = 口径单点进 skill「回写措辞」节 + 新守卫 `check_wording.py` 挂 `kb.check` + 存量清洗 88 处 / 64 文件。test.full **2693 passed + 4 skipped / 99%**(基线切片 26-10-07-0434)。
> 最后活动: 2026-10-07 04:34

**Refs:** memory-bank/tasks/26-10-07-memory-bank-pending-wording.md

## 现状

- **改动完成**。改动面: `.agents/skills/memory-bank/SKILL.md`(新节「回写措辞」) · `.agents/skills/memory-bank/scripts/check_wording.py`(新) · `.commands/kb/config.toml`(`kb.check` 加一步) · `tests/test_memory_bank.py`(3 条守阵 + docstring 测试计划 + import 名单) · `memory-bank/tasks/` + `memory-bank/activeContext/` 存量 64 文件(88 处措辞)。
- 验证: `commands run kb.check` 6 步全绿(含新守卫「回写措辞守卫: 无违规」); `commands run test.full` **2693 passed + 4 skipped / 0 failed / 99% / 49.02s**(16021 语句 / 163 未覆盖 / 5472 分支 / 143 partial) —— 较上一条基线 26-10-07-0346 的 2690 **passed +3**(本轮新增 3 条用例), 覆盖四指标逐位相同。
- 未验证面 / 残留风险: 守卫只覆盖 `tasks/` + `activeContext/`, **`testing/baselines/` 不入扫描面**(冻结快照, 其 `未提交` 是测量元数据); 该目录仍有 38 处 `等…指令` 形态的状态语 —— 属**有意保留**, 若日后判定也该清, 是另一件事(会改冻结件)。
- 判据沉淀: ①一个提交不能包含自己的 hash ⇒ 回填设计要么换时不变措辞、要么第二笔提交、要么接受滞后一笔; ②守卫与清洗脚本共用同一判据(清洗脚本 `import` 守卫的 `scan_text`), 不做第二份; ③匹配 markdown 粗体按"配对段"取, `[^*]*` 会横跨相邻粗体段误报。
- 债务转告(非本轮): activeContext 切片数 83 > 70 —— **不拦提交**, 需另开会话把 14 天未动的切片蒸馏进 `progress/` 或任务档案后删除(`commands run doc.caps` 现算)。
