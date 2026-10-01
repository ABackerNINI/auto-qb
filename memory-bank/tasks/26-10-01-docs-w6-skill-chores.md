# 26-10-01-docs-w6-skill-chores — W6 技能清账: grill-me 删除收口 + hatch-pet 拍板回执

**Status:** Done
**Added:** 2026-10-01
**Updated:** 2026-10-01 23:37
**Summary:** 执行 issue 清偿路线图 W6 技能清账两条 chore。grill-me: 用户拍板删除占位, `git rm -r .agents/skills/grill-me` 实删 SKILL.md 与 agents/openai.yaml 共 2 个跟踪文件; issue 档案 Open→Done(徽章 + meta), 补仓库根相对 doc-refs 回指本档案, 状态日志记拍板与处置。hatch-pet: 用户拍板「不用管」, 未改任何 hatch-pet 文件; 现场复核 `.agents/skills/hatch-pet` 顶层挂载不存在(skill 已不在库内挂载面), 但原骨架 22 文件仍被 git 跟踪在被 EXCLUDED 的 autoclaw-design-capability 包内(不可达, 与入池时认知一致); 该 issue 收口写入被平台密钥守卫拦截(误判, 既有正文示例), 状态收口待用户定调后另笔完成。遗留: skills-lock.json 仍登记 grill-me 安装记录(仓库内无脚本消费), 按范围守恒不动只报告。
**Topics:** w6-skill-chores
**Refs:** memory-bank/issues/26-09-20-1427-chore-skill-grill-me-empty-stub.html

> 背景关联(不进机器认领链): 本任务是 issue 清偿路线图(memory-bank/plans/26-10-01-1758-plan-issue-clearance-roadmap.html)W6 波次的技能清账 2 条。 hatch-pet issue(memory-bank/issues/26-09-20-1427-chore-skill-hatch-pet-api-cost.html)的机器回指因平台写入守卫阻断暂缺, 见「进度日志」。

## 原始请求

用户执行 issue 清偿路线图(plans/26-10-01-1758-plan-issue-clearance-roadmap.html)W6 波次, 授权本 clone 处理其中 2 条 chore 及「全套立档文件」, 并显式授权完成后提交(commit + push 一次走完):

1. grill-me skill 移除(拍板=删除占位): 删除 `.agents/skills/grill-me/`(SKILL.md + agents/openai.yaml), 先 `git ls-files` 确认跟踪状态再 `git rm -r`; 两份 issue 档案状态收口 Open→Done, 状态变更日志追加拍板与处置, doc-refs 用仓库根相对口径, `commands run kb.index` 重建索引。
2. hatch-pet 成本标注(拍板「不用管」): 不改任何 hatch-pet 文件; 现场确认 `.agents/skills/` 下有无 hatch-pet 目录(此前列表未见), 不存在就在 issue 回执里如实记「skill 已不在库内」。

## 思考过程与决策

- **引用面实勘(与简报口径的出入)**: `git grep -l grill-me` 除目标目录与对应 issue 档案外, 还有 4 处: `skills-lock.json`(v1 安装锁, source=mattpocock/skills, 仓库内无脚本消费它, 仅 .dockerignore 提及文件名)、`memory-bank/issues/_index.md`(生成物, kb.index 链路会自愈)、`memory-bank/plans/26-10-01-1758-plan-issue-clearance-roadmap.html` / `memory-bank/progress/implemented-tooling.md` / `memory-bank/reports/26-09-20-1429-skill-vetter-audit.html`(三份记录件, 记录既有事实, 删除动作本身会让其中表述成为历史描述)。按范围守恒只动目标目录与 issue 档案, 其余只报告; `.codebuddy/` 全库 grep 无 grill-me(未挂载, 无需处理)。
- **hatch-pet 现场事实(两层分开陈述)**: 顶层 `.agents/skills/hatch-pet` 不存在 —— skill 已不在库内挂载面; 但入池所指原骨架仍以 git 跟踪文件形式存在 `.agents/skills/autoclaw-design-capability/审美相关skill/skills/hatch-pet/`(22 个文件, git ls-files 核实), 该父包在 `scripts/sync_agent_skills.py:54` 的 EXCLUDED(「18MB, 193 个嵌套预设」)中, 不会被同步为可用技能 —— 与入池时「当前不可达」认知一致。拍板「不用管」, 两层都不改。
- **doc-refs 口径**: 按 pitfalls/kb/refs-rename.md(已复发 3 次), meta 与正文 `<a href>` 两套口径: meta 用仓库根相对 `memory-bank/tasks/26-10-01-docs-w6-skill-chores.md`, 正文链接用文件相对 `../tasks/…`。两份 issue 的 Refs 反向声明同理, 双向闭环。
- **hatch-pet issue 收口被阻断的处置**: 平台密钥守卫对该档案的整文件写入判红(定位在既有正文「Authorization=[redacted]」凭据头示例的误报), 按守卫指引不绕过、交由用户定调。回退决策: 本档案机器 Refs 只挂 grill-me(已闭环), hatch-pet 以正文文字关联 —— 机器认领链要求双向, 挂单向声明会让 test_docs_forms 红, 不带入闸门。

## 实现计划

- grill-me: `git ls-files` 确认跟踪 → `git rm -r` → issue 档案收口(徽章/meta/doc-refs/状态日志)。
- hatch-pet: 现场复核两层事实 → 不改文件 → 回执写入 grill-me 同批 issue 收口与档案(实际: 该 issue 写入被守卫拦, 记录阻断)。
- 档案: 查重(本 clone + 跨工作区 ../auto-qb-*) → 新建本文档, Refs 双向一致。
- 索引: `commands run kb.index` → 补跑 `gen_issues_index.py`(迁移 issues 状态分区, kb.index 不含)。
- 校验: 守卫测试 test_memory_bank / test_docs_forms(同层校验, 不跑 test.full)。
- 提交: 消息入 `.git/COMMIT_MSG_AI.txt` → `commands run ship.commit`(内含同步/闸门/逐路径暂存/ref 核对/推送)。

## 子任务状态表

| 子任务 | 状态 | 备注 |
|---|---|---|
| grill-me 跟踪确认 + git rm -r | ✅ 完成 | 2 文件实删(SKILL.md + agents/openai.yaml) |
| grill-me issue 收口(Done + doc-refs + 日志) | ✅ 完成 | 徽章/meta/日志三处, 仓库根相对口径 |
| hatch-pet 现场复核(不改文件) | ✅ 完成 | 顶层不存在; 原骨架在被 EXCLUDED 包内仍跟踪 |
| hatch-pet issue 收口写入 | ⛔ 阻断 | 平台密钥守卫拦截(误判), 待用户定调 |
| 任务档案(查重 + 新建) | ✅ 完成 | 跨工作区无同名 slug |
| kb.index + issues 索引重建 | ✅ 完成 | 无红, 输出见进度日志 |
| 守卫测试 + ship.commit | ✅ 完成 | 数字见进度日志 |

## 进度日志

- **2026-10-01 23:28** 同步成功 826f25e6(工作区净)。读 AGENTS.md / memory-bank SKILL / my-commit-flow README+config.toml+pipeline.md / pitfalls kb 索引 / gitmoji skill。grill-me: git ls-files 确认 2 文件跟踪, `git rm -r` 实删(rc=0); 全仓引用面实勘(4 处额外命中, 处置见思考过程); .codebuddy 无引用。hatch-pet: 顶层不存在, 原骨架 22 文件在 autoclaw-design-capability 包内被 git 跟踪, EXCLUDED 核实(sync_agent_skills.py:54)。跨工作区查重 5 个 clone 无同名 slug, 建本档案。
- **2026-10-01 23:34** grill-me issue 收口: 徽章 + `<meta name="issue-status">` Open→Done + 补 `<meta name="doc-refs">`(仓库根相对) + 状态日志记拍板与处置。hatch-pet issue 同批收口写入被平台密钥守卫拦截(artifact_secret_detected, 定位既有正文凭据头示例误判), 按守卫指引不绕过, 状态仍 Open 待用户定调。
- **2026-10-01 23:37** 建本档案。 `commands run kb.index` 重建无红; 补跑 `uv run python .agents/skills/create-issue/scripts/gen_issues_index.py` 迁移 issues 状态分区(grill-me 入 Done 区); 守卫 `commands run test.one -- tests/test_memory_bank.py tests/test_docs_forms.py` 全过(数字见提交信息); `commands run ship.commit` 一次走完(暂存范围: grill-me 删除 + grill-me issue + 本档案 + 生成物; hash 见下条)。
