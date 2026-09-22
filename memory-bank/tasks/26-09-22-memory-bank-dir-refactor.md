# 26-09-22-memory-bank-dir-refactor — 知识库目录化重构 (分类 + 二级指针)

**Status:** In Progress
**Added:** 2026-09-22
**Updated:** 2026-09-22
**Summary:** 全库 8 份超标文档 → 分类目录 + 索引指针 + 五步配方 (含 cap 分级与存根); 脚本统一落 memory-bank skill; W0–W6 已完成 —— **8 份超标文档全部拆完**(9 个目录 / 40 主题文件), 10 条结构性守卫, 续做 W7 tasks 消肿

## 原始请求

> 当前的 memory-bank 组织形式有很多缺陷, 比如 pitfalls, 全部的 pitfalls 都写入一个文件, 实际上 agent 已多次重复犯里面已记录的坑, 所以急需重构, 暂定使用分类+二级指针的方式, 比如 git 操作分一个类, 在做计划时 agent 本就不需要知道 git 的坑, 同时也需要细分, 比如 git 分为 pull, push 等, 需要精细, 暂定结构为 `memory-bank/pitfalls/_index.md`, `pitfalls/git/...`, 指针就简单概括, 类似此类。不光 pitfalls, 其它的也有类似的问题, 根据我的想法完善并写一个重构计划。

### 增补请求 (同日)

1. 「将脚本放入 memory-bank skill 的 scripts 目录下, 增加通用性, `gen_tasks_index.py` 似乎也应该放到 skill 目录, 更新计划。」
2. 「似乎只做了 pitfalls 的重构计划, 其它 memory-bank 中的大文件也需要类似的重构。」

⇒ 计划已按此两条重写: 脚本统一落 skill (含通用生成器与 cap 策略), 并给出全库逐文档落位。

## 思考过程与决策

### 现状实测 (2026-09-22, 本次会话普查)

| 文档 | 字符 | 行 | 顶层条目 |
|---|---|---|---|
| `pitfalls.md` | 62,362 | 449 | 253 |
| ├ 前端 / WEB UI 纪律 | 37,202 | 110 | 76 |
| ├ 测试 / 冒烟 / 仿真 | 33,390 | 160 | 74 |
| ├ Git / 提交推送 | 13,517 | 74 | 31 |
| └ 其余 7 节 | 18,000+ | — | 72 |
| `activeContext.md` | 55,990 | 447 | — |
| `progress.md` | 80,704 | 361 | — |
| `testing.md` | 61,468 | 458 | — |
| `systemPatterns.md` / `modules.md` / `conventions.md` | 49,328 / 44,192 / 26,070 | — | — |

其它关键事实:
- `pitfalls.md` 被 **48 个文件 / 113 处** 引用 (含 12 份历史计划 HTML、8 份任务档案、3 处源码注释)。
- `AGENTS.md` 现 **7,653 / 8,000 字符**(`check_context_caps.py` 实测), 余量仅 347 —— 新增路由必须先精简。
- 机械守卫现状: `tasks/` 8 条 (`tests/test_memory_bank.py`) + 闸门 8 条 (`.commit-flow.toml`); **pitfalls 零守卫**。
- 反向实证: 已被机检化的两条坑 (提交后核 ref → `verify_ref.py`;脚本未定义名 → `test_preflight.py`) 未再复发;
  只靠文本记录的 `git rebase` 禁令在工具 shell 已出 3 次事故 (09-21 ×2 / 09-22 ×1, 第三次照通用 skill 踩)。

### 决策 (写进计划的判据)

1. **分类 + 二级指针**胜出, 另三种排法被排除: 单文件 + TOC (体量没降)、按日期归档 (检索键错位)、
   一坑一文件 (253 文件无归类)。
2. **七个类固定枚举**: `git` / `web-ui` / `backend` / `testing` / `ops` / `kb` / `docs`; 扩类须三处同步
   (生成器枚举 / 守卫常量 / L1 `_about.md`)。
3. **条目字段化**: `触发` / `判别` / `处置` 必填, `守阵` / `复发` 选填; 叙事降级为一句「为什么」。
   253 条内容不重写, 只做归位与字段化。
4. **cap**: L1 2.5 KB / 类索引 3 KB / 主题文件 6 KB (下限建议 1.5 KB, 仅 WARN)。
5. **索引是生成物**: `scripts/gen_pitfalls_index.py` (collect/render/--check) + 守卫 8 条 + 提交闸门。
6. **接线才是治本**: AGENTS.md 加「开工读 L1」、`.commit-flow.toml` 增 `pitfalls_index` 键供预检打印指针、
   memory-bank skill DoD ⑤ 改为「写入类目录 + 重跑生成器」并新增「复发 +1 / 写明为什么没命中」闭环。
7. **能机检的下沉为守阵** (W5 候选 5 条), 文本只留一行指针 —— 这是「反复重踩」的唯一治本路径。
8. **兼容层**: 保留 `pitfalls.md` 存根 (≤1 KB, 指向 L1), 历史计划 HTML / issue 报告 / 任务档案正文一行不改。
9. **脚本落位 (2026-09-22 用户增补)**: 索引生成器与结构检查脚本统一落 memory-bank skill 的 `scripts/`
   (`_common.py` + `gen_tasks_index.py`(从根 `scripts/` 迁入) + `gen_pitfalls_index.py` + `check_kb_structure.py`),
   理由是它们实现的是 Memory Bank **模式**本身、不是本项目业务, 放 skill 才能跨 clone / 跨项目共用一份。
   边界: 项目专属值不进 skill (哪些文件受 8000 字符上限仍留 `scripts/check_context_caps.py`);
   脚本内部找仓库根用 `find_root()` 向上找 `.git`(不按 skill 深度反推 `parents[n]`), 文档路径一律写 `<skill-dir>/scripts/...`。
10. **全库范围 (2026-09-22 用户增补)**: 不止 `pitfalls`, 全库 13 份顶层文档里 8 份超标, 一律按同一套
   **五步配方** 处理。定案要点: ①**层级由规模决定**(pitfalls 7 类两级; testing 一级), 不强制两级;
   ②主题文件统一三行头元数据 (`# 标题` / `> 摘要:` / `> 触发:`), 条目型与叙述型共用, 生成器一套通吃;
   ③**cap 分级**: 索引 3 KB / pitfalls 条目集 6 KB / 常青主题 10 KB / 参考速查与易变层 12 KB /
   任务档案 24 KB(纪要段 ≤8 KB) —— `AGENTS.md` 8000 仍归项目脚本;
   ④`activeContext.md` **不拆但硬顶 12 KB**(超了即内容该外迁); ⑤被拆文档一律留 ≤1 KB 存根,
   活文档改指目标文件、历史只靠存根; ⑥`tasks/` 超 24 KB 的档案把「历史会话纪要」段移 `tasks/attachments/`
   (索引守卫按 `tasks/*.md` 不递归, 天然兼容); ⑦路由分两层: `AGENTS.md` 粗路由(≤6.5 KB, 现 7,653) +
   `memory-bank/README.md` 库内细路由(≤3 KB, 守卫保证无孤儿目录)。

### 决策补记 (2026-09-22 W1 实测后修正)

11. **索引 cap 拆出 `index-auto` 档 (12 KB)**: 计划 §03 把"索引"一律定 3,000 字符, 但 `tasks/_index.md`
    实测 **10,790**、`issues/_index.md` **6,937** 字符 —— 它们是**自动生成、一行一条、行数随条目数增长**的,
    套 3,000 必然常红且没有可行的收缩路径(缩摘要就是丢信息)。故单列 `index-auto` 12 KB:
    仍有守卫防无限膨胀, 但不假装它们是一屏索引。手写的 `<文档>/_index.md` 与 `memory-bank/README.md`
    仍守 3,000。
12. **W7 范围按实测收窄**: 计划称 `tasks/` 有 4 份 >20 KB; 实测只有 `26-09-19-webui-responsiveness.md`
    (27,260 字符)超 24 KB 档 ⇒ W7 只需处理这一份 + 复核各档案的「历史会话纪要」段 ≤8,000。

详见 [docs/plans/26-09-22-1248-memory-bank-dir-refactor-plan.html](../../docs/plans/26-09-22-1248-memory-bank-dir-refactor-plan.html) (11 节: 问题 / 备选对比 / 判据 G1–G6 / 目标结构 / 格式规范 / 三条入口 / 机械后果 / 迁移映射 / 分波 / 守恒验收 / 风险与验证)。

## 实现计划

- **W0** 基线冻结: 全库 13 份文档的段级字节 + 条目 dump 成 `(md5, 字节, 段名)` 清单 (gitignore)。
- **W1** 基础设施: `gen_tasks_index.py` 迁进 skill 的 `scripts/`; 新增 `_common.py` / `gen_kb_index.py`
  (通用索引生成) / `check_kb_structure.py` (cap 策略 + 元数据 + 双向一致 + 无孤儿); 改写 11 个活文档引用;
  闸门改 `<skill-dir:memory-bank>` 整目录一条。**后面每波都依赖它**。
- **W2** `pitfalls/` 两级指针 (7 类 + 约 30 主题文件 + 存根 + 接线)。
- **W3** `testing/` (≈9 文件 + 存根): `baseline.md` 成为基线唯一手改处; 新增 `guards.md`; techContext 的
  浏览器自动化迁入 `browser-env.md`。
- **W4** `activeContext.md` 瘦身 (≤12 KB + cap 守卫) + `progress/` (5+4 份 + 存根); 走查清单迁 `checklists/`。
- **W5** `systemPatterns/` (≈8) + `modules/` (≈7) + 存根; 纠正「任务队列」名下的 WEB UI 内容归属。
- **W6** `conventions/` (≈5) + `config-reference/` (≈3) + `rule-system/` (≈4) + 存根; `checking` 单独成篇。
- **W7** `tasks/` 档案消肿: 超 24 KB 的档案把「历史会话纪要」段移 `tasks/attachments/`
  (**实测 2026-09-22: 只有 `26-09-19-webui-responsiveness.md` 27,260 字符 > 24,000** ——
  计划里"4 份 >20 KB"是旧数, 已按 W0 实测修正)。
- **W8** 机检化 + 回归演练 (检索演练 ×3) + 重写 `memory-bank.instructions.md` 的旧结构与旧命名。

## 子任务状态表

| ID | 内容 | 状态 | 更新 | 备注 |
|----|------|------|------|------|
| 0.1 | 现状普查 (体积 / 结构 / 引用面 / 守卫 / cap 余量) | Complete | 2026-09-22 | 数字见上表, 均为实测 |
| 0.2 | 产出重构计划 (`docs/plans/26-09-22-1248-…plan.html`) | Complete | 2026-09-22 | 单文件 dark HTML, 11 节 |
| 0.3 | 立档 + 重建 tasks 索引 + 更新 activeContext | Complete | 2026-09-22 | 本轮不做 commit/push |
| 0.4 | 计划增补: 脚本统一落 memory-bank skill 的 `scripts/` | Complete | 2026-09-22 | 含 `gen_tasks_index.py` 迁入与 11 处引用改写清单 (计划 §07) |
| 0.5 | 计划增补: 全库逐文档落位 + 五步配方 + cap 分级 | Complete | 2026-09-22 | 8 份超标文档 → 9 目录 / ≈45 主题文件 + 8 存根; 波次扩为 W0–W8 (计划 §03/§04/§05/§06) |
| W0 | 基线冻结 (42 份 / 508,487 字符 / 352 段 / 1,613 条目) | Complete | 2026-09-22 | 清单在 `.workbuddy-ai/tmp/kb-baseline/` (gitignore) |
| W1 | 基础设施: 脚本落位 + 通用生成器 + cap 策略 + 9 条守卫 | Complete | 2026-09-22 | 全量 1169 passed + 1 skipped (+9) |
| W2 | `pitfalls/` 两级指针 (7 类 + 35 主题文件 + 存根 + 接线) | Complete | 2026-09-22 | 守恒: 真丢失 0 (973 token 核对); 1169 passed 不变 |
| W3 | `testing/` (9 文件 + 存根; `baseline.md` 成唯一手改处) | Complete | 2026-09-22 | 守恒: 真丢失 4 处已补; 1169 passed 不变 |
| W4 | `activeContext` 瘦身 (≤12 KB + cap 守卫) + `progress/` | Complete | 2026-09-22 | 40,553 → 4,783 字符; progress 51,717 → 11 文件; 1170 passed (+1) |
| W5 | `systemPatterns/` + `modules/` (8 + 7 主题文件) | Complete | 2026-09-22 | 守恒 596/743 token 全中; 顺带纠正 WEB UI 三节归属 |
| W6 | `conventions/` + `config-reference/` + `rule-system/` (4+2+3 主题文件) | Complete | 2026-09-22 | 守恒 232/226/282 token; 8 份超标文档至此全拆完 |
| W7 | `tasks/` 档案消肿 (超 24 KB 的移 `attachments/`) | Not Started | — | |
| W8 | 机检化 + 回归演练 ×3 + instructions 漂移修复 | Not Started | — | 候选见下「W8 候选清单」 |

## 进度日志

### 2026-09-22 (计划产出)
- 普查 memory-bank 12 份文档的体积、章节分布、顶层条目数; 统计 `pitfalls.md` 的引用面 (48 文件 / 113 处);
  查 `AGENTS.md` 的字符预算 (7,653/8,000) 与现有机械守卫覆盖范围 (pitfalls 零守卫)。
- 定案: 七类枚举 + 条目三必填字段 + 三级 cap + 生成物索引 + 三条入口接线 + 兼容存根。
- 产出计划文档并立档。**本轮未动 `src/`、未动 `pitfalls.md`、未 commit / push**;
  测试基线不受影响 (仍是 1152 passed + 1 skipped, 2026-09-22 实测), 故未改 `testing.md` 顶部。
- 待用户确认: 第 04 节的类切分与第 05 节的 cap 值; 确认后从 W0 开工。

### 2026-09-22 (计划增补: 脚本落位)
- 用户要求「脚本放进 memory-bank skill 的 scripts 目录, 增加通用性; `gen_tasks_index.py` 似乎也应该放到 skill 目录」。
- 核查结论: 该脚本全仓 **36 处**提及 (活文档 11 个文件 + 历史档案 5 处不动);
  `.codebuddy/skills/memory-bank` 实测是 junction (新增文件立即生效, 不必重跑 `sync_agent_skills.py`);
  `create-issue/scripts/_common.py::find_root()` 是现成范型 (向上找 `.git`, 不按安装深度反推 `parents[n]`, 允许 `--root` 覆盖)。
- 计划已更新: §03 G4 判据 / §06(b) 命令路径 / §07 新增「脚本落位」与「迁移引用面」两节、闸门改
  `<skill-dir:memory-bank>` 占位符 / §09 W1 拆成 W1.1–W1.3 / §10 增脚本落位验收 / §11 增风险与两条验证步骤。
- **仍未动代码、未 commit / push。**

### 2026-09-22 (计划重写: 全库范围)
- 用户指出「只做了 pitfalls 的重构计划, 其它大文件也需要类似重构」。补量了全库: 13 份顶层文档里
  **8 份超标** (progress 80,704 / pitfalls 62,362 / testing 61,468 / activeContext 55,990 /
  systemPatterns 49,328 / modules 44,192 / conventions 26,070 / rule-system 23,607 / config-reference 17,421),
  以及 `tasks/` 28 份 305,097 字符 (最大 44,927, 4 份 >20 KB, 纪要段合计 35,256)。
- 计划重写为 11 节 (62,644 字节): 新增 §03 统一配方 (五步 + 三行头元数据 + cap 分级 + 存根规则)、
  §04 全库落位总览、§05/§06 逐文档落位 (两份), 并把 §08 的生成器改为**通用** `gen_kb_index.py`
  (pitfalls 两级与 testing 一级同一实现)、守卫 8 → 9 条、§09 波次扩为 W0–W8、§10 验收增
  「入口链不随库体量变长」。
- 定案: `systemPatterns` 的 WEB UI 三节 (21,406 字符) 本就挂错在「任务队列」名下, 拆开即纠错;
  modules 的「在哪里改」速查并入 `_index.md`; `tasks/attachments/` 不破坏索引守卫 (不递归)。

### 2026-09-22 (W4 `activeContext` 瘦身 + `progress/` 拆分)
- **`activeContext.md` 40,553 → 4,783 字符**(cap 12,000): 原「正在进行」15 条里 **13 条已完成**,
  按既有纪律「沉淀到 progress/ 或主题文档后**删除**」处置 —— 但**只删真的在别处有记载的**:
  5 条(平台语义守阵 / 列设置双轨 / 规则表达式化 / skills 安全审查 / 知识库瘦身)**搬进 `progress/implemented-*.md`**,
  其余在主题文档已有记载(语料→roadmap 小节、乐观 UI→implemented-webui-perf、冒烟→testing/smoke.md、
  仿真→testing/sim-5000.md)。「待用户真机走查」整段(约 15 KB)迁 `checklists/manual-walkthrough.md`;
  「定案口径」逐条归位到 `pitfalls/web-ui/` 与 `AGENTS.md` 后改为指针(「多 clone 并行」那条的存档细节
  原句搬回 —— token 核对查出换成指针时丢了 `MANIFEST.md` / `sha256.txt` 等)。**只留 2 条未完成**:
  本次目录化重构本身 + 「上轮计划复核的收尾」。
- **`progress.md` 51,717 字符 / 367 行 → `progress/` 11 个文件 + ≤1 KB 存根**: 已实现 48 条按域拆 6 份
  (implemented-webui · implemented-webui-perf · implemented-core · implemented-rules · implemented-testing ·
  implemented-tooling), 其余 5 份(roadmap / known-bugs / evolution / suggestions + `_about`)。
  ⚠ **两处按实测调整计划**: ①implemented 拆 **6** 份(计划 5)—— `implemented-webui.md` 一度 12,883 字符,
  超 cap, 按「跟手性/性能/状态色」与「界面/视图」再分一刀; ②4 条超长叙事(单条最大 **10,225** 字符,
  逐条都超 cap)移 `progress/attachments/webui-longform.md`, 原位留首行 + 指针(首行本就带结论 / sha / 实测数字)。
- **新增 `checklists/`**(`_about.md` + `manual-walkthrough.md`)—— 走查清单是**清单**, 读的时机是
  「做走查时」而不是「每次会话开始」, 故从易变层移出。
- **启用 `test_kb_active_context_within_cap`**(10 条知识库守卫): 它是 W1 就写好、**按波次未启用**的那条;
  本波把 `activeContext.md` 压到 cap 之下才纳入 `check_kb_structure` 的默认角色集。
  ⇒ 全量 **1169 → 1170 passed + 1 skipped**。
- **守恒核对**: `progress.md → progress/` **928 个 token 全部命中(missing = 0)** —— 条目是原样搬运, 所以干净。
  `activeContext.md → memory-bank/` 657 个 token 里 93 个"找不到", 逐条判后 **5 处真丢失已补**
  (state.json 条目未沉淀 / 真机语料条目未沉淀 / 乐观 UI 条目未沉淀 / 多 clone 存档细节 / 顶部滚动链),
  余 7 个是**顶部「最后更新」滚动链里的 commit sha** —— 那条按设计每轮替换, 已在文件头写明
  「它是滚动状态不是档案, 回查请看 tasks/ 档案的进度日志」, 不再当丢失。
- **踩坑记录**: 用 `python -c "..."` 往测试文件里插含**反引号 + `\n`** 的代码, 被 bash 当命令替换吃掉反引号、
  `\n` 被路径归一化层写成 `/n` ⇒ 文件语法错误。**正是 W2 刚迁进 `pitfalls/git/editing-traps.md` 的那条坑**
  (heredoc / 反斜杠转义); 改用**脚本文件** + 显式 UTF-8 即好。⇒ 该坑的适用范围要写宽: 不只 heredoc,
  `python -c` 的双引号串同样中招。
- **实测**: 全量 **1170 passed + 1 skipped**, sidefx 越界 0; `check_kb_structure.py` 全过。

### 2026-09-22 (W6 `conventions/` + `config-reference/` + `rule-system/` 目录化)
- **`conventions.md`(15,283 字符 / 202 行 / 20 节)→ 4 个主题文件**: collaboration(协作约定 + 跨仓库红线 +
  生产配置禁令)· code-style(函数设计 / 可测试性 / 模块职责 / 命名 / 类型注解 / 性能 / 注释 / 日志 / 格式化 /
  dataclass / 其它工程约定)· process(dry_run / 幂等 / Git / 闸门)· webui(菜单分层 / 令牌分工 / HTML dark 主题)。
  ⚠ 原先 18 节挤一份, **单节最大 5,458 都合规, 但一次要读 15 KB** —— 这正是"检索键错位"的典型。
- **`config-reference.md`(11,779 / 142)→ 2 个**: loading-and-write(加载 / 写回 / fail-fast 校验)· keys(全部键 +
  trackers + 曲线 + 规则集段 + 变量语法 + 运行时文件 + 测试样例)。
- **`rule-system.md`(15,964 / 205)→ 3 个**: rules-and-triggers · conditions-and-actions(含 `expr` 速查)·
  **checking 单独成篇** —— 高风险动作独立, 并与 [../pitfalls/backend/high-risk-ops.md](../pitfalls/backend/high-risk-ops.md) **互指**。
- **做法**: 三个源文件的章节与目标文件同样**几乎 1:1** ⇒ 全部**按行区间原样抽取**;
  `code-style.md` 由 **11 个不连续区间**拼成(20 节里散落的风格类小节归拢到一处)。
- **守恒核对**: conventions **232 个 token 全中**、config-reference **226 个全中**、rule-system **282 个里 1 个** ——
  唯一那个是源引言里的 `config/validation.py`, 而它**2026-09-15 已由单文件转包**(见
  [../modules/core-config.md](../modules/core-config.md) 的 `config/validation/ (包)`), 故我在目标文件里写成
  `config/validation/` —— 属**有意纠正的过期写法**, 不是丢失。
- ❗**第二次踩同一个坑**: 与 W5 一样, 三个源文件的**引言块**(抽取时被存根取代)里含全库性事实 ——
  ①`内容基线 2026-09-05 @ 51374bd`(config-reference / rule-system)②rule-system 的**代码模块清单**
  (`rules/base.py` / `conditions.py` / `actions/` / `registry.py` / `mixins/rule_engine.py` / `config/loaders.py` …)
  ③conventions 的「以代码为准并回写」通用声明 —— 均已补进各目录的第一个主题文件。
  ⇒ **五步配方该加一条**: 抽取类迁移前先**单独把"标题 + 引言"列出来核对** —— 两次都栽在区间之外。
- **实测**: 全量 **1170 passed + 1 skipped**(与 W4/W5 持平 —— 本波未增删用例), sidefx 越界 0;
  `check_kb_structure.py` 全过; `AGENTS.md` 预算仍 PASS。
- **里程碑**: 计划 §04 点名的 **8 份超标顶层文档至此全部拆完**(pitfalls / testing / progress / activeContext /
  systemPatterns / modules / conventions / config-reference / rule-system —— 其中 activeContext 是瘦身不拆)。
  剩 W7(`tasks/` 档案消肿)与 W8(机检化 + 回归演练 + instructions 漂移修复)。

### 2026-09-22 (W5 `systemPatterns/` + `modules/` 目录化)
- **`systemPatterns.md`(31,678 字符 / 308 行)→ 8 个主题文件**: overview · main-loop · data-layer · taskqueue ·
  web-runtime · web-responsiveness · web-config-editor · client-and-state。
  ⚠ **顺带纠正一处归属错误**: 原先「WEB UI 线程模型」(`###` 挂在「任务队列」下)「WEB UI 前端渲染与响应性」
  「WEB UI 图形化配置编辑」三节合计约 **21 KB** 挂在**任务队列**名下 —— 它们属于 **WEB UI 运行时**, 不属于队列。
  拆开即纠错, 这本来就是本波的动因之一。
- **`modules.md`(30,324 字符 / 126 行)→ 7 个主题文件**: overview(包入口 + 「在哪里改」速查) ·
  core-config · core-runtime · core-domain(核心模块 30 行表按包切三份)· webui-static-contract · mixins ·
  rules-and-deps。
- **⚠ 两处按实测偏离计划**: 计划让「组件总览」与「包入口 + 在哪里改速查」**并入 `_index.md`** ——
  但我们的 `_index.md` 是**生成物**(只渲染三行头元数据), 放不了手写正文 ⇒ 各起一个 `overview.md`。
- **做法**: 两个源文件的章节与目标文件**几乎 1:1**, 故**全部按行区间原样抽取**(不通读、不重写)——
  `taskqueue.md` 与 `data-layer.md` / `client-and-state.md` 各由 2–3 个不连续区间拼成;
  三处原为 `###` 的 WEB UI 小节在目标文件里**提升为 `##`**。只有「核心模块」30 行表按包切三份要人工判归属。
- **守恒核对**: systemPatterns **596 个 token 全中**、modules **743 个全中(missing = 0)**;
  唯一查出的缺口是**两个源文件的引言块**(抽取时被存根取代)里的两条全库性事实 ——
  ①`内容基线 2026-09-05 @ 51374bd` ②`行数为 2026-09-05 快照, 路径相对 src/auto_qb/` —— 已补进各 `overview.md`
  与 modules 的四份带表文件。⇒ **教训: "按行区间抽取"容易漏掉区间之外的引言/元信息, 核对时要把它们单列。**
- **实测**: 全量 **1170 passed + 1 skipped**(与 W4 持平 —— 本波未增删用例), sidefx 越界 0;
  `check_kb_structure.py` 全过。

### W8 候选清单(两处 skill 缺口, 2026-09-22 记)

1. **`<each:GLOB>` 闸门只展开"已跟踪的改动文件"** ⇒ **新增(untracked)**的 skill 脚本拿不到 `--help` 冒烟
   (W1 新增 4 个 memory-bank 脚本时实测: 闸门只跑了 1 条 `create-issue` 的)。修点在 `preflight.py` 的改动清单。
2. **`test_preflight.py` 的 `undefined_names` 静态检查只覆盖 my-commit-flow 自己的 5 个脚本**,
   memory-bank skill 的 4 个脚本不在内(与"改名漏改的未定义名只在冷门分支炸"同一类风险)。
3. `run.md` 的 TMPDIR 一档还留着与「用 `--basetemp=H:/Temp/<新目录>`」**互相冲突**的旧建议(既有漂移)。

### 2026-09-22 (W3 `testing/` 目录化)
- **产出**: `testing.md`(6,706 字符 / 489 行)→ **9 个主题文件 + ≤1 KB 存根**(存根实测 **322 字符**):
  `run` · `baseline` · `baseline-history` · `file-conventions` · **`guards`(新增)** · `helpers` · `sim-5000` ·
  `smoke` · `browser-env`。另从 `techContext.md` 剥出浏览器自动化两条轨道(techContext **6,706 → 3,542 字符**)。
- **新增 `guards.md`**: 把散落各处的机械守阵收成一张表(**守阵名 / 钉住的结论 / 红验方式**), 五组共 70+ 条 ——
  知识库结构(16) · 前端 WEB UI(14) · 主循环与命令链路(11) · 后端高风险与状态持久化(14) · 仿真语料与平台语义(15)。
  这是本波唯一**新写**的内容(其余是重组 + 字段化), 也是"能变成红的就从文本搬进守阵"这条主线的目录。
- **基线数字单点迁移**: 从 `testing.md` 顶部迁到 `testing/baseline.md`(其它文档一律引用它);
  **逐次增量的 222 行流水用脚本原样外迁**到 `testing/baseline-history.md` —— 手抄等于把"守恒"变成
  "我保证没抄错"; 抽取时只把 bash 注释标记(`#` / `#   `)转成 markdown 列表缩进, **内容逐字未改**。
- **守恒核对**: 674 个硬事实 token 里 26 个"找不到", 逐条判后**真丢失 4 处**已补回 ——
  ①覆盖率逐模块明细 ②档案命名的两种形态(`YY-MM-DD-<slug>.md` + 兼容 `TASKnnn-<slug>.md`)
  ③主犯那条的具体修法(`auto_qb.cli.notify_fatal`)④副作用台账规模(1742 条 / 越界 0)。
  其余 12 个是**故意压缩的过期数字**(如 `1062 条` 改指 `baseline.md` 单点)或正则跨反引号的假阳性。
- **⚠ 按实测新增 `log` 角色(cap 24 KB)**: `baseline-history.md` 实测 **18,749 字符**, 是 **append-only**
  流水、按设计就会一直长 ⇒ 套"常青主题 10 KB"必常红且**没有可行的收缩路径**(删历史就是丢"数字怎么来的")。
  与任务档案同档 24 KB, 并已把 `log` 加进 `check_kb_structure` 的默认角色集。
- **接线**: `memory-bank/README.md` 细路由改指 `testing/_index.md`(并点明基线单点在 `testing/baseline.md`)。
- **实测**: 全量 **1169 passed + 1 skipped**(与 W1/W2 持平 —— 本波未增删用例), sidefx 越界 0;
  `check_kb_structure.py` 全过; `testing/` 合计 57,439 字符。
- **残留(非阻塞)**: `run.md` 的 TMPDIR 一档还留着 testing.md 里那条与"用 `--basetemp=H:/Temp/<新目录>`"
  **互相冲突**的旧建议(既有漂移, 本轮只按 W1 记的候选保留), 归入 W8。

### 2026-09-22 (W2 `pitfalls/` 目录化)
- **产出**: 旧 `pitfalls.md`(64,491 字符 / 255 条) → **7 类 / 35 个主题文件 / 236 条字段化条目**;
  最大文件 `web-ui/contract-api.md` **5,582 字符**(cap 6,000); `pitfalls/` 合计 99,510 字符(含 8 个生成物索引 + 8 个 `_about.md`)。
- **条目格式**: `### <一句话结论>` + `触发` / `判别` / `处置` **三必填**, `守阵` / `复发` 选填 ——
  由守卫 `check_pitfall_entries` 机械校验。原句照搬 + 压叙事, 规则 / 判别法 / 实测数字一个不删。
- **类切分**: git(6 文件) / web-ui(8) / backend(5) / testing(8) / ops(1) / kb(6) / docs(1)。
  ⚠ 两处相对计划调整: ①web-ui 8 份(计划 7)②testing 8 份(计划 8) —— web-ui 因 `contract-api.md` 条目多而拆出
  `overlays.md`, 属 cap 驱动的必要拆分。
- **守恒核对(方法换了, 必须记)**: 本轮是**字段化重写**(触发/判别/处置 + 压叙事), **不是逐字搬家** ⇒
  计划 §10 的"规范化行文本 md5 比对"**不适用**(原句被重新分配, md5 必然大面积假红)。
  改用**硬事实 token 覆盖**: 抽旧版每条目的反引号标识符 / 路径 / 带单位数字, 逐个在新树里找 ——
  **973 个 token, 17 个"找不到", 逐条人工判后全部是正则跨反引号的假阳性**(如 `), 容器给` / `。**ESM 的`),
  **真丢失 0**。⚠ 该法**真查出** 2 条被我漏掉的条目(「Markdown 表格被自动格式化器改坏」/
  「Bash heredoc 反斜杠转义被路径归一化层改成正斜杠」), 已补进 `git/editing-traps.md`;
  另补回 3 处被压掉的标识符(`hasUnit()` / `decoratedShows` / 被取代的旧守阵名)。
  ⇒ **教训: token 核对能抓"整条丢失", 但抓不到"条目内的叙述性规则丢失"; 它是必要不充分的代理判据。**
- **接线**: ①`AGENTS.md` **7,580 → 6,117 / 8,000**(粗路由改成指向 `memory-bank/README.md` 细路由 +
  三条动作级提示; 「跨仓库操作」「提交 / PR」「命令」三节精简为指针)②`memory-bank/README.md` 重建
  **库内细路由表**(任务 → 入口, 含 `pitfalls/_index.md`)③skill 收尾 **DoD ⑤** 改为"按动作写进
  `pitfalls/<类>/<主题>.md` + 重跑 `gen_kb_index.py`", 并新增**复发闭环**(踩到已记的坑 ⇒ `复发` +1 +
  档案里写"为什么没命中")④`.commit-flow.toml` 增 `pitfalls_index` 决策点指针, 预检表尾打印
  (为支持该键, `_ship_config.KEY_DEFAULTS` 与 `preflight.py` 各加一处; `test_preflight.py` 26 项全过)。
- **守卫**: 9 条从"空转"变成**真跑**; `check_kb_structure.py --quiet` 全部通过。
- **实测**: 全量 **1169 passed + 1 skipped**(与 W1 持平 —— 本轮未增删用例), sidefx 越界 0。
- **残留(非阻塞)**: 11 个主题文件落在 1.5 KB **建议下限**之下(计划 §03 明示该下限**只 WARN 不红**,
  且 `ops/` `docs/` 是单文件类无从合并); 已把 `--quiet` 修为**同时抑制 WARN**(原实现只抑制 PASS)。

### 2026-09-22 (W0 基线冻结 + W1 基础设施)
- **W0**: 按五步配方第 1 步量全库 —— 13 份顶层文档 + `tasks/*.md` + `AGENTS.md` 共 **42 份 / 508,487 字符 /
  352 段 / 1,613 条目**; 段级与条目级 `(md5, 字节, 段名)` 清单落 `.workbuddy-ai/tmp/kb-baseline/`(gitignore),
  比对工具 `.workbuddy-ai/tmp/kb_baseline.py --verify`。**不动任何文档。**
  ⚠ 计划 §01 的体积数字是旧测量, 实测已全面变小: pitfalls 63,430(计划 62,362 基本持平) / progress 51,292
  (计划 80,704) / testing 39,988(61,468) / activeContext 37,636(55,990) / systemPatterns 31,370(49,328) /
  modules 30,198(44,192); `tasks/` 只有 **1** 份 >24 KB(计划称 4 份 >20 KB)。结论不变(仍全部超标), 但 W7 的
  工作量比计划小得多。
- **W1**: ①`gen_tasks_index.py` 从仓根 `scripts/` 迁进 memory-bank skill 的 `scripts/`(仓根文件删除),
  路径走 `find_root()` 向上找 `.git`(不按 skill 安装深度反推), 新增 `--root` / `--mb-dir`;
  ②新增 `_common.py`(`find_root` / `CAP_POLICY` / `PITFALL_CLASSES` / 三行头 `read_meta` / `role_of`) —
  cap 与类枚举的**单点**; ③新增通用 `gen_kb_index.py`(任意目录 → `_index.md`; 有子目录出类指针, 无则出文件指针;
  **索引目录自发现** = 含 `_about.md` 的目录, 故 `tasks/` `issues/` 天然不在内);
  ④新增 `check_kb_structure.py`(9 条检查, 供守卫进程内 import);
  ⑤11 个活文档引用改写(AGENTS / README / copilot-instructions / memory-bank.instructions / SKILL / pitfalls×2 /
  progress / create-issue 的 docstring / tests 守卫 / `.commit-flow.toml`), 历史计划与 issue 报告一行未动;
  ⑥闸门由 `memory-bank/tasks/` 一条改为 `memory-bank/` 整目录一条, 命令走 `<skill-dir:memory-bank>` 占位符
  (实测 `preflight --show-config` 已展开)。
- **守卫 9 条**(`tests/test_memory_bank.py`, 8 → 17 passed): 索引 == 生成结果 / 索引↔目录双向一致 /
  三行头元数据 / cap 策略 / 类名与文件名 / 无孤儿索引 / 存根合法 / pitfalls 条目三字段 / 4 脚本可 import。
  它们是**结构性**的 —— 目录未建时空转通过, 某个 `<文档>/` 一落地就自动生效, 故 W1 只增不减。
- **实测**: 全量 **1169 passed + 1 skipped**(基线 1160, +9), 覆盖率 TOTAL 90% / 7523 语句 / 623 未覆盖;
  `check_kb_structure.py --all` 正好只报两条**按波次待办**的项(`activeContext.md` 12 KB 硬顶 → W4;
  `tasks/26-09-19-webui-responsiveness.md` 24 KB → W7), 即 `check_caps` 默认角色集之外的两档。
- **两处按实测修正计划**(见「决策」补记): ①索引 cap 拆出 `index-auto` 12 KB 档; ②W7 只 1 份超标。
- **环境**: 跑全量时踩到已记录的 `H:\Temp\pytest-of-11059\pytest-current` 损坏 reparse point
  (会话收尾 `cleanup_dead_symlinks` 抛 `PermissionError` ⇒ **退出码 1, 测试本身全过**)。该条目 `readlink` /
  `rmdir` / `icacls` 全被拒(用户态不可修), 处置: 把整个 pytest 临时根 `rename` 成
  `H:\Temp\pytest-of-11059-broken`(**未删除任何东西**) ⇒ 默认路径恢复可用。后续按 testing.md 的约定
  改用 `TMPDIR=R:/Temp/auto-qb/tests`。⚠ testing.md 里「用 `--basetemp=H:/Temp/<新目录>`」与顶部「设 TMPDIR」
  两条建议互相冲突(前者会触发 `tests/sidefx.py` 的临时目录判定失效), 属既有漂移, **本轮未动**, 记入 W8 候选。

### 2026-09-22 (提交与推送)
- 本轮四处改动: 计划文档 + 本档案 + `tasks/_index.md` + `activeContext.md`。
- 提交那刻远端 `gitee/develop` 已多 1 个提交 (`e11df80` 修 state.json 损坏静默清空), 与本轮在
  `activeContext.md` 上重叠 ⇒ `git merge-tree` 只读判定 **CONFLICT**(仅此一个文件)。
  按仓库纪律**不用 rebase**(工具 shell 里必炸), 走替代流程: ①`cp -a .git` 备份到
  `R:/Temp/auto-qb/git-backup-20260922-kbplan` ②建锚点 `refs/heads/tmp-kbplan-anchor` 保住我方提交
  ③`git reset --hard e11df80`(工作区干净, 全程不走 stash / merge) ④`git checkout <锚点> -- <三份无重叠文件>`
  ⑤`activeContext.md` 手工合并(取远端原文, 把本轮两条块插到「最新」处, 远端那条降为「其前一条状态」)
  ⑥复测 → 提交 → 推送。
- ⚠ 手工合并时又踩到行尾: `core.autocrlf=true` ⇒ `reset` / `checkout` 之后**工作区文件变成 CRLF**
  (blob 仍是 LF), 于是按 `\n` 写的老式多行匹配全部落空(patch 命中 0 次)。
  处置: 读入先归一化成 LF 做替换, 回写时整份恢复 CRLF; 提交时 git 归一化回 LF, blob 行尾不变。
- 全量实测(并入上游后的新树, 提交那一刻): **1156 passed + 1 skipped in 29.91s**(覆盖率 TOTAL 90%,
  7500 语句 / 623 未覆盖 —— 基线随上游从 1152 上移到 1156), sidefx 越界 0。