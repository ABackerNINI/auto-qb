# 26-09-30-memory-bank-cap-debt — cap 守卫改债务制 (WARN 不拦提交 + 派生可见 + 独立清理会话)

**Status:** Done
**Added:** 2026-09-30
**Updated:** 2026-10-07
**Topics:** memory-bank-cap-debt
**Refs:** memory-bank/plans/26-09-30-2112-plan-memory-bank-cap-debt.html
**Summary:** 用户命题: cap 守卫在任务后期触发, 当场改字数要带着满载会话历史反复返工, token 成本巨大 —— 改为只 WARN 不拦提交, 知识库清理另开会话。分析结论: 合理, 但需三处补强 —— ①债务须在**提交时**派生输出并由 agent **转告用户** (agent 开不了新会话, 挂会话开始等于把返工留在同场; 清理由用户自行开会话); ②**AGENTS.md 是硬规定, 不入债务体系** (用户拍板: 不能超、不套 50% 收缩、不常改; 超 8,000 且本次改动命中仍 STOP, 无中间档); ③测试侧尺寸断言一起降级 (AGENTS.md 除外), 否则 test.full 照旧拦。拦截面盘点四处 (两处不在提交闸门里); AGENTS.md 削薄降为独立清理项; 方案见计划, D1/D3 已定, D2 (切片条数阈值去留) 已按推荐①拍板 (归债务通道)。**2026-09-30 22:xx 守卫改造实施完成**: 除 AGENTS.md 外的尺寸全部降级为债务 (提交不拦); AGENTS.md 保持硬规定 (超 8,000 且本次改动命中仍 STOP, 不入债务体系、不套 50%); 严重度单点落在 skill 的 `HARD_CAP_ROLES`, `doc.caps` 为派生可见的单一入口; 实测 cap 债务 0 项 (`doc.caps -- --strict` 绿), 全量 1874 passed + 3 skipped / 91%。**2026-10-07 全部闭合**: 子任务 7 (AGENTS.md 削薄) 已由后续清理轮落地, 实测 6,608/8,000; 全案 Done。

## 原始请求

「知识库cap守卫在任务后期, 此时触发字数限制修改成本无疑是巨大的, 因为每轮修改都会带着完整会话历史, 十分耗token, 需要更改机制, 让字数限制不再是提交的阻碍, 仅提示WARNING不当场修改, 知识库清理单独开会话。先分析是否合理, 写一个计划」

收尾口径: 本轮 = 分析 + 计划落盘 (计划 + 本档案 + 切片 + 基线); **实施待用户显式启动** —— 计划 §05 的实施会话即用户所述的「首场清理会话」。

## 思考过程与决策

- **分析结论: 方向合理, 三处补强** (详见计划 §01 结论 callout): 派生可见是「不靠自觉」纪律的替代牙齿; AGENTS.md 的 8000 不是预算而是截断点, 必须单列; 只改提交闸门不生效 —— 测试侧尺寸断言会在 test.full 上再拦一次。
- **拦截面四处实测盘点**: ①`check_context_caps.py` 提交闸门 (命中 AGENTS.md / .agents/skills/ 才跑) + `doc.caps`; ②`check_kb_structure.check_caps` 角色 cap **只经 pytest 四条用例消费** (无闸门接线, 但收尾 DoD 必跑 test.full); ③`gen_active_recent --check` 切片尺寸 (提交闸门); ④`gen_baseline_recent --check` 基线切片尺寸 (kb.check)。2026-09-30 实测: KB 角色全绿, 唯一结构性欠债 = AGENTS.md **7,975/8,000 (余量 25)**, 即「任何一次编辑必触」。
- **根因二条**: ①作用点错位 (文档维护问题接成提交前置条件, 在最贵时刻索要最贵工作); ②2026-09-29 的「全表 50%」口径把机械外迁 (KB 主题文件 → attachments/) 与入口文档手术 (AGENTS.md 砍 3,975 字符) 混为一谈 —— 后者实战不可执行, 于是债务记了还不上 (切片 26-09-27-1812 待办①, 记 3 天未清偿)。
- **AGENTS.md 拍板 (2026-09-30, 用户)**: **硬规定, 不纳入债务体系** —— ①不能超: 超 8,000 且本次改动命中仍 STOP (硬闸门不降级); ②不套 50% 收缩动作 (它是常驻注入入口, 内容「外迁」= 硬约束降为按需读, 是设计回退), 削薄只需回到 ≤ 8,000 并按需留一次追加余量; ③不常改, 无需挂账等下一次会话。**取消原设计的 1.25× 止损线** —— 它恒为硬闸门, 不需要中间档。
- **债务通道触发点二次修正 (2026-09-30, 用户)**: 原设计的「会话开始跑 `doc.caps` + 该会话首件清理」不成立 —— **agent 无法自行新建会话**, 在同一场会话里清理与在任务末尾清理没有区别(历史照样累积), 只是把返工挪个位置。改为: **提交时 WARN** (闸门输出) + **警告文案自带「提醒用户: 文档数字已超标, 需另开新会话清理」** + **用户自行新开会话清理**。因此**会话开始协议与 `AGENTS.md` 均不动**; AGENTS.md 削薄从「本计划主活」降为**独立清理项**(与守卫改造解耦)。
- **修正口径 (其余角色)**: KB 角色维持 cap×50% (`TRIM_KEEP`); 两份 SKILL.md 与包内阅读预算降级为债务 (它们超限只多花加载 token, 无截断问题)。
- **附带发现** (同批 cap 资产, 建议实施会话随手收口, 否则入池): `_common.py:66` `TASK_LOG_CAP=16000` **无任何消费者**; `ALL_ROLES = DEFAULT_ROLES + ("volatile","task")` 为重复项。
- **顺带实测缺陷**: `commands run doc.caps -- --strict` 被引擎拒 (run 缺 `<args>` 占位符) —— 清理会话的收口依赖它, 已列进改动清单。

## 实现计划

方案、改动清单与执行顺序单点在 [plans/26-09-30-2112-plan-memory-bank-cap-debt.html](../plans/26-09-30-2112-plan-memory-bank-cap-debt.html) (本节只放概要): 顺序敏感 —— ①sync ②降级守卫 (脚本/测试/闸门口径; **AGENTS.md 除外**) ③机检 ④协议回写 (SKILL.md cap 表注 + 收尾 DoD 一行; **会话开始协议与 AGENTS.md 不动**) ⑤kb.index + doc.caps --strict / kb.check / doc.links / doc.drift 收口 ⑥收尾 DoD ⑦**AGENTS.md 削薄 (独立清理项, 可并入任意一次用户开启的清理会话)**。

## 子任务状态表

| # | 子任务 | 状态 |
|---|---|---|
| 1 | 决策点拍板: D1/D3 已定 (AGENTS.md 硬规定 —— 不入体系 / 不套 50% / 无止损线), D2 (切片条数阈值归债务通道) | ✅ 全定 (D2 按推荐①: 归债务通道, 常量迁入 `_common.SLICE_COUNT_LIMIT`) |
| 2 | 降级: `check_context_caps.py` — AGENTS.md 保持 STOP (硬), SKILL/阅读预算降债务 + 追加 KB 角色 cap 组 (剔除 agents) + 汇总行 + `--strict` 语义 | ✅ |
| 3 | 降级: `check_kb_structure.check_caps` — 除 `agents` 外尺寸 → warns; `agents` 保持 problems (硬) | ✅ (含 `volatile` 同口径; 债务行加 `DEBT_MARK` 前缀) |
| 4 | 降级: `gen_active_recent` / `gen_baseline_recent` 尺寸 → warn (条数阈值按 D2) | ✅ `collect()` 改返回三元组 (行, 问题, 债务) |
| 5 | 测试: 删除 KB 角色 live 尺寸断言 (保留 AGENTS.md ≤8,000 硬断言), 换「债务可发现性」断言 + docstring 清单同步 | ✅ 净 +3 用例 (1871 → 1874) |
| 6 | 接线: `doc.caps` 补 `<args>` + note; 提交闸门 note 改写 | ✅ (闸门 `match` 补 `memory-bank/`, 否则债务触发点等于没接线) |
| 7 | AGENTS.md 削薄 (独立清理项: 回到 ≤ 8,000, 不套 50%, 路由手术; 与守卫改造解耦, 可并入任意一次用户开启的清理会话) | ✅ 已在后续清理轮完成 (fa918a67 / 376dda34 / cba7c4f6 / 295bb226 等), 2026-10-07 实测 6,608/8,000 (余量 1,392) |
| 8 | 协议回写: SKILL.md cap 表注 + 收尾 DoD 一行「债务 → 提醒用户另开会话清理」 (会话开始协议不动; AGENTS.md 无必改项) | ✅ (DoD 第 7 条) |
| 9 | 收口: kb.index + doc.caps --strict + kb.check + doc.links + doc.drift + test.full 基线 | ✅ 全绿; 1874 passed + 3 skipped / 91% |
| 10 | 附带发现收口 (TASK_LOG_CAP 死条目 / ALL_ROLES 重复) 或入池 | ✅ 随手收口 (删 `TASK_LOG_CAP`; `ALL_ROLES` 改为 `DEFAULT_ROLES` 别名并注明) |

## 进度日志

- **2026-09-30 21:12**: 用户命题「cap 守卫改 WARN + 清理独立成会话」→ 要求先分析合理性再出计划。本轮只读探索结论: 拦截面四处盘点完毕; AGENTS.md 7,975/8,000 (余量 25) 实测; KB 角色 cap 全绿; 债务既有记录 (切片 26-09-27-1812 待办①) 未被清偿。分析判定「合理 + 三处补强」, 计划落盘 (plans/26-09-30-2112), 决策点 D1~D3 待拍板; 实施未启动。
- **2026-09-30 21:21 (收尾轮)**: test.full 首跑红于 `test_kb_active_context_slices_are_valid`(切片数 71 > 70, 本会话 +1 恰好顶破): 处置 = 按守卫消息自身口径蒸馏**已完结波次切片** 26-09-30-0018(token-budget, 内容全在其档案), **未抬守卫数字、未动他人活跃切片**; 该实例与「上限按 ~5 片/日校准 vs 多 clone 日 15 片」一并构成 D2 的现场依据。另记两条坑档 (pitfalls/kb/cap-counting.md): 新增「切片计数触顶的合法出口」条目 + 行尾坑复发 5(本轮新建四件 Write 全落 LF, 收口断言一次捕获后归一)。收口实测(合并远端 P3 ed514e30 后复测, 先合并再收尾): test.full 1871 passed + 3 skipped / 91%, kb.index / kb.check / doc.caps / doc.links / doc.drift 全绿; 基线切片 26-09-30-2212。
- **2026-09-30 21:36 (用户拍板 D1/D3)**: AGENTS.md = **硬规定**: 不能超、不套 50% 收缩动作、不常改所以**不进债务体系** —— 超 8,000 且本次改动命中仍 STOP; 取消原设计的 1.25× 止损线; 削薄目标改为「回到 ≤ 8,000」(按需留一次追加余量)。计划 §3.1/§3.3/§3.4/§3.7、§04 改动清单、§05 步骤、§06 AC-4/AC-8 与 §07 风险 1 同步改写 (doc-updated → 26-09-30-2136); D2 (切片条数阈值) 仍待拍板。
- **2026-09-30 21:59 (用户二次修正: 触发点)**: 债务通道触发点从「会话开始」改「**提交时**」—— agent 开不了新会话, 会话开始查 + 当场清与任务末尾修没有区别 (历史照样累积); 改为提交时 WARN + 警告文案自带「提醒用户另开新会话清理」+ 用户自行开会话清理。计划 §01 补强一 / §02 G2 / §3.1 / §3.2 / §3.5 / §3.6 / §04 / §05 / §06(AC-1) / §07(风险 1·3) 与 §08 变更记录同步改写 (doc-updated → 26-09-30-2159); **会话开始协议与 AGENTS.md 均不动**, AGENTS.md 削薄从「本场主活」降为**独立清理项** (与守卫改造解耦)。
- **2026-09-30 22:20 (实施轮 · 用户「按推荐」启动)**: 开工同步 e3936326 后按计划 §05 推进。**D2 按推荐①拍板** —— 切片条数阈值归债务通道, 常量从 `tests/test_memory_bank.py` 迁入 `_common.SLICE_COUNT_LIMIT` (`gen_active_recent.collect` 报成债务)。
  ①**降级守卫**: `check_context_caps.py` 重写为三档输出 (硬规定 AGENTS.md / SKILL+阅读预算 债务 / KB 角色 cap 债务由 skill 现算), `--strict` 语义改「债务非空即 rc=1」; `check_kb_structure.py` 加 `HARD_CAP_ROLES = ("agents",)` 与 `DEBT_MARK`, 除 `agents` 外尺寸进 warns (`volatile` 同口径); 两个切片脚本 `collect()` 改返回 (行, 问题, 债务) 三元组。
  ②**测试**: 删 `test_kb_task_archives_within_cap` 等 live 尺寸断言, 新增 4 条 (债务可发现性 / AGENTS.md 硬规定 / 切片尺寸+条数 / `check_context_caps` 分档), docstring 清单同步 —— 净 +3 (1871 → 1874)。
  ③**接线**: `doc.caps` 补 `<args>` (今天传 `--strict` 会被引擎拒); 闸门 `match` 补 `memory-bank/` —— 否则债务的触发点只在改 AGENTS.md / skill 时才跑, 等于没接线 (G2 要求「提交时必然可见」); note 钉死「闸门只用默认模式」。
  ④**协议回写**: SKILL.md cap 表注加债务制段落 + AGENTS.md 例外三条, 收尾 DoD 加第 7 条「cap 债务转告」; `testing/guards.md` 守阵表同步; **会话开始协议与 AGENTS.md 未动**。
  ⑤**附带发现随手收口**: 删死条目 `_common.TASK_LOG_CAP`; `ALL_ROLES` 改为 `DEFAULT_ROLES` 别名并注明重复项的来历。
- **实施轮实测 (2026-09-30 22:xx)**: AC-1/AC-3/AC-4 用 tmp 仓库逐条验过 (AGENTS.md 未改动 + KB 超限 → rc=0; AGENTS.md 8,001 且改动命中 → rc=1; 仅债务非空 + `--strict` → rc=1, 默认模式 → rc=0)。全量 1874 passed + 3 skipped / 91%, test.pkg 74 passed, `doc.caps --strict` / `kb.check` / `doc.links` / `doc.drift` 全绿; 当前 cap 债务 **0 项**。
- **实施轮踩到的坑 (新档 `pitfalls/kb/cap-debt.md`)**: ①`check_caps` 的 warns 里混着下限 `CAP_MIN_WARN` 的「文件过小」提示 —— 直接当债务累计, 实测一次报 26 项假债务 (真超限 0), `doc.caps --strict` 永远红 ⇒ 债务行加 `DEBT_MARK` 前缀, 消费者只挑带标记的; ②`_kb_checker()` 找不到 skill 时抬成 STOP —— 降级不彻底 (与本次改动无关的环境状况拦住提交), 改 WARN; ③删尺寸断言而**不补**「可发现性」断言 = 把守卫撤掉 (降级后没有任何用例会红) ⇒ 判据一句话: 降级一条守卫时要问「降级之后它靠什么变红」。- **2026-10-07 07:55 (状态收口轮)**: 用户确认两计划已完成, 简单验证后翻状态。验证: ①AGENTS.md 实测 6,608/8,000 (余量 1,392, 削薄已由 fa918a67/376dda34/cba7c4f6/295bb226 等清理轮落地) → 子任务 7 闭合; ②`doc.caps` 现跑无阻塞项、cap 债务 0 项; ③test.quick 2705 passed + 4 skipped 全绿。档案 Status → Done; 计划 doc-status Open → Done (doc-updated 26-10-07-0755), kb.index 重建。
