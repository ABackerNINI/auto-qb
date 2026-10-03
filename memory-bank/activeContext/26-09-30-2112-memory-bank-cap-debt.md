# 26-09-30-2112-memory-bank-cap-debt — cap 守卫改债务制 (WARN 不拦提交 + 独立清理会话)

> 摘要: 用户命题: cap 守卫在任务后期触发, 当场改字数要带着满载会话历史反复返工、token 成本巨大 —— 要求改为「只提示 WARNING、不当场修改, 知识库清理单独开会话」。**守卫改造已实施完成 (2026-09-30 22:xx)**: 除 AGENTS.md 外的尺寸全部降级为**债务** (提交不拦、提交时派生输出并转告用户、清理另开会话), AGENTS.md 保持**硬规定** (超 8,000 且本次改动命中仍 STOP, 不入债务体系、不套 50%); 严重度单点在 skill 的 `HARD_CAP_ROLES`, `doc.caps` 为派生可见单一入口。**实测 cap 债务 0 项** (`doc.caps -- --strict` 绿), 全量 1874 passed + 3 skipped / 91%。剩余 = **AGENTS.md 削薄 (独立清理项, 余量 25)**, 待用户另开清理会话。
> 最后活动: 2026-09-30 22:35

## 状态

- 计划文档: `plans/26-09-30-2112-plan-memory-bank-cap-debt.html` (doc-status Open, 守卫改造段已实施); 档案: `tasks/26-09-30-memory-bank-cap-debt.md` (Status **In Progress**, 子任务 1–6/8–10 完成, 7 待清理会话)。
- **D1/D2/D3 全部拍板 (2026-09-30)**: D1/D3 —— AGENTS.md = **硬规定** (不能超 / 不套 50% 收缩 / 不入债务体系 / 无止损线; 削薄目标 = 回到 ≤ 8,000); D2 按推荐**①** —— 切片条数阈值**归债务通道** (`_common.SLICE_COUNT_LIMIT`, 由 `gen_active_recent` 报成债务, 不再判红)。
- **改造后的三档输出** (`commands run doc.caps`): ①**硬规定** AGENTS.md —— 超限即拦; ②**债务** 两份 SKILL.md / 包内阅读预算 / KB 角色 cap (由 skill 现算) —— `[债务]` 行 + 汇总行「请在回复中提醒用户: 文档数字已超标, 需另开新会话清理」, 不拦提交; ③`--strict` = 清理会话的收口开关 (债务非空即 rc=1), **闸门只用默认模式**。
- **当前债务 = 0 项**: `doc.caps -- --strict` 绿; KB 角色 cap 全在限内。唯一未清的是 AGENTS.md 的**结构性余量** 7,975/8,000 (余量 25) —— 它是独立清理项, 不是债务。
- **触发点二次修正 (2026-09-30 用户)**: 债务可见性**不放会话开始** —— agent 开不了新会话, 会话内清理与任务末尾修没区别(历史照样累积); 改为**提交时 WARN + 文案自带「提醒用户另开新会话清理」+ 用户自行开会话**。会话开始协议与 AGENTS.md 均不动; AGENTS.md 削薄降为**独立清理项** (与守卫改造解耦)。
- 根因二条: ①作用点错位 —— cap 是文档维护问题却被接成提交前置条件 (在最贵时刻索要最贵工作); ②2026-09-29「全表 50%」口径把机械外迁 (主题文件 → `attachments/`) 与入口文档手术 (AGENTS.md 砍 3,975 字符) 混为一谈, 导致债务「记了还不上」(切片 26-09-27-1812 待办① 记 3 天未清偿)。
- 债务归属已移交本专题: 原挂在切片 `26-09-27-1812-commit-msg-consume-delete.md` 待办① 的「AGENTS.md 削薄」现由本计划接管。
- **前序波次切片已蒸馏**: `26-09-30-0018-memory-bank-token-budget`(cap 全表翻倍 + `commands list` 平铺, 该波次已完结) 内容全在其档案 `tasks/26-09-30-memory-bank-token-budget.md` 内, 按切片计数守卫的处置口径 (「蒸馏进任务档案后删除」) 删除 —— 本切片接续该 cap 治理线, 本会话 +1 片恰好触顶 (71 > 70) 的处置记录见基线切片。

## 正在进行

- 无 —— 守卫改造已完成并收口。本轮改动落在: `scripts/check_context_caps.py`(重写为三档) · `.agents/skills/memory-bank/scripts/{check_kb_structure,_common,gen_active_recent,gen_baseline_recent}.py` · `tests/test_memory_bank.py`(净 +3 用例) · `.commands/doc/config.toml` · `.commands/my-commit-flow/.my-commit-flow.toml` · `.agents/skills/memory-bank/SKILL.md` · `memory-bank/testing/guards.md`; 新坑档 `pitfalls/kb/cap-debt.md`。

## 下一步

- **AGENTS.md 削薄 (唯一剩余项, 独立清理会话)**: 7,975 → 回到 ≤ 8,000 (不套 50%)。手法 = 路由手术 —— 细节下沉 `memory-bank/README.md` / `conventions/` / `pitfalls/`, 原位留指针; **必须仍在 AGENTS.md**: 7 条黄金法则、红线、git 硬约束三处纪律、提交口径 (常驻可见性语义, 不许下沉)。验收 = `doc.caps` 绿 + 人工对照清单。
- 平时: 提交时若出现 `[债务]` 行 → **在回复里提醒用户另开会话清理**, 不在本会话动手; 清理由用户在**新会话**里跑 `commands run doc.caps` 拿现算清单, 收口 `commands run doc.caps -- --strict`。
- 附带发现已随手收口: `_common.TASK_LOG_CAP`(无消费者) 删除; `ALL_ROLES` 改为 `DEFAULT_ROLES` 别名。

## 追加(2026-10-03): 切片计数债务清理 —— 104 → 68

- 用户另开会话清理「切片数 104 > 70」债务。按 [cap-counting 坑档](../pitfalls/kb/cap-counting.md)「切片计数触顶的合法出口」执行: **未抬 `SLICE_COUNT_LIMIT`、未删活跃片**。
- 删除 36 片 = 同专题重复片 9(kernel-module-refactor ×5 → 留 26-10-01-0359 / web-state-alias-disposal ×3 → 留 26-10-01-0800 / webui-delete-tag-scope-confusion ×1 → 留 26-10-03-0915; 三片保留件各加「前序波次切片已蒸馏」留痕段)+ 已完结波次片 27(全部有对应 `tasks/` 档案且内容已被档案覆盖)。
- 排除项: 8 片有入链(删则 `doc.links` 红 —— docs/hr-online-verify-docs.md · plans/26-09-26-0529 · baselines/26-09-28-0401 · progress/implemented-webui-history.md · tasks 档案 ×2 · issues/26-09-29-2142)+ 3 片仍有开放待办(docker-deploy W5 真机验收 / settings-back-nav 待拍板 / timekit 用户令暂不实施)+ 真机走查待用户的 3 片。
- 删前逐个 grep 入链; 删后 `kb.check`(主键纪律 357 文档 / 211 专题)与 `doc.links` 均绿。
- **结构性提示**: 104 片全在 9 天内产出 ⇒ 实测 ~11 片/日(多 clone 并行), 而上限按 5 片/日校准 ⇒ 会反复触顶; 长期处置走治理议题, 本会话未自行调数。
