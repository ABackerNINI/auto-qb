# 26-10-11-2129-memory-bank-sync-no-exemption — 开工同步口径改无豁免(问答/只读轮次不再跳过)

> 摘要: 用户指定「开工前必须同步 —— 无论只读分析还是要修改文件, 禁止在落后的分支上工作; 与之冲突的口径都要改」⇒ **开工同步口径改为无豁免**: 任何轮次(含只答问题 / 只做只读分析)第一个动作前必须 `commands run my-commit-flow.sync`, 禁止在落后分支上工作。改写活文档 6 处(`AGENTS.md` 会话协议①+黄金法则7 子条 / memory-bank skill 第 1 步 / `.github/instructions/ai-lib.md` / `conventions/process.md` / `conventions/collaboration.md` / `pitfalls/kb/request-boundary.md`)+ 命令面 2 处(`.commands/my-commit-flow/config.toml` 的 `when` 与包 README)+ 坑档新头节 `pitfalls/git/sync-pull.md`「开工同步无豁免」(含**只读轮次同步失败贴失败行停下、不代做 stash** 的处置); ai-lib.md 里已漂移的手工 `git fetch + merge --ff-only` 配方一并删除, 单点回到 `commands run my-commit-flow.sync`。`test.full` 全绿(数字见 `commands run kb.baseline`)。
> 最后活动: 2026-10-11 21:29
> 状态: Done(本专题本轮完结)

## 现在做到哪

口径已全线落地: 会话开工(任何轮次, 含只答问题 / 只做只读分析)第一个动作前必须 `commands run my-commit-flow.sync`;
**禁止在落后的分支上工作 —— 只读分析同样禁止**。口径文档只陈述当前规则; 历史件(归档档案 / 冻结制品)不改写。

- **入口 4 处一次改全** (该规则的多入口纪律仍在 `conventions/process.md` 里明记): `AGENTS.md`(单点定义) / `.agents/skills/memory-bank/SKILL.md` 第 1 步 / `.github/instructions/ai-lib.md` / `conventions/collaboration.md`
- **口径冲突面清零**: `AGENTS.md` 黄金法则 7 增「开工同步不受本条豁免」(同步是协议硬步骤, 不扩大本轮动作范围); `pitfalls/kb/request-boundary.md` 加同旨条; `pitfalls/git/sync-pull.md` 新头节给出可执行处置(含只读轮次失败不代做 stash)
- **命令面**: `.commands/my-commit-flow/config.toml` 的 `when` 与 `.commands/my-commit-flow/README.md` 同步改(任何轮次含只读分析)
- **历史件不改写**: 09-22 档案只追加本轮续作节; 冻结的 plans / reports / issues 一律不动

## 产物

- 档案(续作): `memory-bank/tasks/26-09-22-memory-bank-sync-rule-rework-check-started.md`
- 坑档: `memory-bank/pitfalls/git/sync-pull.md`(新头节) · `memory-bank/pitfalls/kb/request-boundary.md`(例外条)
- 基线: `memory-bank/testing/baselines/26-10-11-2129-memory-bank-sync-no-exemption.md`

## 下一步 / 遗留

- 无遗留项。**用例**: 下次会话(含只答问题 / 只读分析)第一个动作即为 `commands run my-commit-flow.sync`, 结果行「已同步 <hash>」贴进回复; 若同步失败且本轮只读 ⇒ 贴失败行并停下, 不代做 stash。

**Refs:** memory-bank/tasks/26-09-22-memory-bank-sync-rule-rework-check-started.md