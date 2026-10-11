# 3129 —— 开工同步口径改无豁免(问答/只读轮次不再跳过)基线

> 摘要: 纯文档轮, 零源码改动(数字与上片同量级属预期)。用户指定「开工前必须同步 —— 无论只读分析还是要修改文件; 禁止在落后的分支上工作」⇒ 开工同步口径改为**无豁免**: 任何轮次第一个动作前必须跑 `commands run my-commit-flow.sync`, 禁止在落后分支上工作。入口 4 处一次改全(`AGENTS.md` 会话协议①+黄金法则 7 子条 / memory-bank skill 第 1 步 / `.github/instructions/ai-lib.md`(并删已漂移的手工 fetch+ff-only 配方) / `conventions/collaboration.md`), 加 `conventions/process.md`(多入口清单同步更新)、`pitfalls/kb/request-boundary.md`(开工同步不在豁免之列)、`pitfalls/git/sync-pull.md`(新头节, 含只读轮次同步失败不代做 stash)与命令面(`.commands/my-commit-flow/config.toml` 的 `when` + 包 README)。
> 基线时间: 2026-10-11 21:31
> 档案: memory-bank/tasks/26-09-22-memory-bank-sync-rule-rework-check-started.md

**Refs:** memory-bank/tasks/26-09-22-memory-bank-sync-rule-rework-check-started.md,memory-bank/pitfalls/git/sync-pull.md

## test.full 实测

- 分支: `develop`(会话开工 `my-commit-flow.sync` 已同步 d7c5b351; 工作树含本专题全部改动时实测)
- 命令: `commands run test.full`
- **实测 (Windows)**: **3129 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16517 语句 / 151 未覆盖 / 5626 分支 / 134 partial; 门槛 98% 达标; 本轮 ~26s)
- 改动面(摘要): `AGENTS.md`(6962/8000) · `.agents/skills/memory-bank/SKILL.md` · `.github/instructions/ai-lib.md` · `memory-bank/conventions/{process,collaboration}.md` · `memory-bank/pitfalls/{kb/request-boundary,git/sync-pull}.md` · `.commands/my-commit-flow/{config.toml,README.md}` · 档案续作 + 本切片 —— 全部为文档/配置文本, 无 src / tests 改动。