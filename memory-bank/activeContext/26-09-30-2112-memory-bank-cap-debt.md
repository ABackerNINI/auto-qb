# 26-09-30-2112-memory-bank-cap-debt — cap 守卫改债务制 (WARN 不拦提交 + 独立清理会话)

> 摘要: 用户命题: cap 守卫在任务后期触发, 当场改字数要带着满载会话历史反复返工、token 成本巨大 —— 要求改为「只提示 WARNING、不当场修改, 知识库清理单独开会话」。**守卫改造已实施完成 (2026-09-30 22:xx)**: 除 AGENTS.md 外的尺寸全部降级为**债务** (提交不拦、提交时派生输出并转告用户、清理另开会话), AGENTS.md 保持**硬规定** (超 8,000 且本次改动命中仍 STOP, 不入债务体系、不套 50%); 严重度单点在 skill 的 `HARD_CAP_ROLES`, `doc.caps` 为派生可见单一入口。**实测 cap 债务 0 项** (`doc.caps -- --strict` 绿), 全量 1874 passed + 3 skipped / 91%。剩余 = **AGENTS.md 削薄 (独立清理项, 余量 25)**, 待用户另开清理会话。
> 最后活动: 2026-10-06 10:55

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

## 追加(2026-10-05): 三项 cap 债务一次清理 —— 切片 128 → 67 · issues 索引 26,260 → 20,620 · implemented-webui 21,172 → 9,407

- 用户开清理会话报三项债务: 切片数 128 > 70、`issues/_index.md` 超 cap、`progress/implemented-webui.md` 超 cap。三项一次收口, `commands run doc.caps` 债务清零。
- **① 切片 128 → 67**: 按 [cap-counting 坑档](../pitfalls/kb/cap-counting.md)「切片计数触顶的合法出口」删 61 片 —— 判据 = ①无入链(逐片 grep 精确文件名, 删后 `doc.links` 绿) 且 ②非「待拍板 / 待指派 / 待决策 / 待商榷」的开放决策片。未抬 `SLICE_COUNT_LIMIT`、未删活跃片。保留 = 有入链 51 + 开放决策 12 + 显式保留 4(`tracker-url-source-sanitize` 计划未开工·决策点待批 / `memory-bank-dir-refactor` 待拍板 / `ops-recheck-false-success` 等指派 / `qb-traffic-decimal-interval` 最新片) + `_about.md`。本轮 14 天规则**零命中**(最老片 26-09-23, 仅 12 天)。
- **② `issues/_index.md` 26,260 → 20,620**: 走**渲染口径**而非外迁条目 —— 给 `gen_issues_index.py` 补 `SUMMARY_MAX = 40`(摘要截断, 与 `gen_tasks_index.SUMMARY_MAX` 同款), 正是切片 [26-10-01-2125-memory-bank-dir-refactor](26-10-01-2125-memory-bank-dir-refactor.md) 记的待拍板项。判据: 133 条**无摘要**也才 14,790 字符 < cap ⇒ 是摘要(11,470 字符)把索引顶爆的, 条目数本身没撑爆 cap ⇒ 按坑档「先查渲染口径」不搬条目(外迁会打坏外部引用)。未达 50% 线(12,600)属该文件性质(index-auto 无可行收缩路径, 见 `CAP_POLICY` 注释), 现余量 4,580。
- **③ `progress/implemented-webui.md` 21,172 → 9,407**: 按 `log` 轮转口径把最老 13 条(2026-10-02~10-04)原文外迁 → `implemented-webui-history.md`(44,494/48,000), 原位留一行指针; 顺带把历史文件**混合行尾归一 LF**(`.gitattributes` = `eol=lf`, 消掉 git 的「CRLF will be replaced」警告)。
- 收口: `doc.caps` 债务 0 项 / `kb.check` / `doc.links` / `test.full` 全绿。**未提交**(等用户显式「提交」指令)。

## 追加(2026-10-06): 清理轮 —— 切片 92 → 68 · issues 索引 25,598 → 23,170 · 第三项系口径误报

- 用户开清理会话报三项债务; 用守卫口径现算后实为**两项真债务 + 一项误报**, `commands run doc.caps` 债务清零。
- **① 切片 92 → 68**: 按 [cap-counting 坑档](../pitfalls/kb/cap-counting.md)「切片计数触顶的合法出口」删 24 片。判据 = ①**无入链**(逐片用 `git grep` 精确文件名核外部引用, 删前复检 0 处命中) 且 ②**非开放决策片**(无「待拍板/待指派/待决策」) 且 ③内容已被 `tasks/` 档案 · `reports/` 报告 · 坑档 · `progress/` 全量覆盖。**未抬 `SLICE_COUNT_LIMIT`、未删活跃片**。14 天规则**零命中**(最老片 26-09-23, 仅 13 天) —— 与坑档「可能一个都没有」的预判一致, 合法对象只能取「已完结波次片」。
  - **删 24 片 = full-code-review 族 13**(S0-S1 + 批 A/B1/B2/C/D/E/F1/F2/G/H + S5 + S6; 内容全在报告 `reports/26-10-05-1036` §2/§3 与计划 `plans/26-10-05-0951`, 该族 S6 切片**自述**「事实源已全部沉淀, 到期蒸馏后删除」)**+ 实施/取证完结片 11**(`test-throttle-timing-flaky` · `settings-help-rewrite` · `open-path-foreground-round2` · `backend-issues-clearance` · `ops-recheck-false-success` · `hr-fetch-verify-forensics` · `webui-danger-guards` · `hr-steady-throttle-impl` · `backend-reannounce-confirm` · `reannounce-confirm-rework-impl` · `webui-qb-traffic-drawer-page-guard`)。
  - **断链处置**: 保留片 `26-10-05-0555-hr-steady-throttle-plan` 原指向被删实施片的链接**改指任务档案**(原文保留「原实施切片已蒸馏」注记); 其余被删片**外部入链 0 处**(逐片核过)。删后 `doc.links` 绿。
- **② `issues/_index.md` 25,598 → 23,170(余量 2,030)**: 仍走**渲染口径** —— `gen_issues_index.SUMMARY_MAX` 40 → 24。判据同 10-05 轮且仍成立: 163 条**无摘要**口径才 18,744 字符 < cap(25,200) ⇒ 是**摘要**(6,854 字符)顶爆的, 条目数本身没撑爆 ⇒ **不搬条目**(外迁会打坏 `**Refs:**` 外部引用)。未达 50% 线(12,600)属 index-auto 性质(见 `CAP_POLICY` 注释), 不强行凑数。
  - **⚠ 新增长期信号**: 无摘要口径占 cap 的比例 10-05 是 59%(14,790/25,200), **本轮已 74%**(18,744/25,200), 而 Done 条目只增不减 ⇒ 条目数本身正逼近病根; 下一两轮大入池后应改走坑档记的后备出口(按状态归档老条目), 别条件反射抬 cap。
- **③ `pitfalls/web-ui/layout-css.md` —— 误报, 未动**: 用户报「17.6KB 超 12KB cap」用的是**字节数**, 而 cap 口径是**字符数**。实测 17,661 字节 = **9,717 字符** < 12,000(角色 `pitfall`), `doc.caps` 与 `check_kb_structure` 均判 PASS ⇒ **本该一行都不改**(范围守恒)。已把该形态记为坑档新条目「量 cap 的第三种形态: 拿「KB / 字节」去比「字符数」的 cap」。
- 收口: `doc.caps` 债务 **0 项** / `kb.check` 绿(459 文档 · 250 专题, 认领链闭环) / `doc.links` 绿 / `kb.active --check` 绿 / `tests/test_memory_bank.py` 33 passed / `test.full` 2677 passed + 4 skipped / 99%(数字单点见基线切片)。**已入库 `4236975c`**(本切片 + `26-10-05-0555` 断链修 + 坑档 2 条 + 生成物 20 个 + 两条新基线切片同笔)。
- **构造性提示(与 10-03 轮同源)**: 68 片距上限仅余 2 —— 多 clone 并行实测 ~5–15 片/日, 而上限按 5 片/日校准 ⇒ 仍会反复触顶。本轮**未自行调数**(治理议题不在清理会话范围)。
- **同源缺陷: CLI 汇总行把「债务」与「下限提示」混作一堆 —— 已修 (用户点名「修 check_kb_structure.py」)**:
  `check_kb_structure.py` 的汇总行原用 `len(warns)` 计「cap 债务 N 项」, 而 `warns` 里混着 `CAP_MIN_WARN` 的
  「过小」提示(不带 `DEBT_MARK`)⇒ 该行**恒报 ~40 项、永远清不了零**(实测 40 项 vs 真实 0), 与
  [cap-debt 坑档](../pitfalls/kb/cap-debt.md)第 1 条「债务数必须能清零」相悖。修法 = 把分类收成**单点**
  `split_warns(warns) -> (债务, 提示)`, CLI 只数债务侧 + 两类**分开贴标签**(`[WARN]` / `[提示]`); 顺带订正两处
  把 warns 当「债务清单」的注释(`check_caps` docstring · `run_all` 内注释)。守卫
  `test_kb_debt_count_excludes_min_size_hints`(造「只有过小文件」的 tmp 库 → 必须报 `cap 债务 0 项`;
  再加一个超限文件 → 报 `1 项`), **红验已过**(退回 `len(warns)` 即红, 实测报 `1 项` 并断言失败)。
  **注**: 提交闸门从来不受影响(`check_context_caps.py` 一直按 `DEBT_MARK` 过滤)。
