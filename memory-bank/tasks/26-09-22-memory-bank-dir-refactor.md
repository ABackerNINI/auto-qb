# 26-09-22-memory-bank-dir-refactor — 知识库目录化重构 (分类 + 二级指针)

**Status:** Pending
**Added:** 2026-09-22
**Updated:** 2026-09-22
**Summary:** 全库 8 份超标文档 → 分类目录 + 索引指针 + 五步配方 (含 cap 分级与存根); 脚本统一落 memory-bank skill; 计划已产出, 待确认后按 W0–W8 分波实施

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
- **W7** `tasks/` 档案消肿: 超 24 KB 的 4 份把纪要段 / 分波明细移 `tasks/attachments/`。
- **W8** 机检化 + 回归演练 (检索演练 ×3) + 重写 `memory-bank.instructions.md` 的旧结构与旧命名。

## 子任务状态表

| ID | 内容 | 状态 | 更新 | 备注 |
|----|------|------|------|------|
| 0.1 | 现状普查 (体积 / 结构 / 引用面 / 守卫 / cap 余量) | Complete | 2026-09-22 | 数字见上表, 均为实测 |
| 0.2 | 产出重构计划 (`docs/plans/26-09-22-1248-…plan.html`) | Complete | 2026-09-22 | 单文件 dark HTML, 11 节 |
| 0.3 | 立档 + 重建 tasks 索引 + 更新 activeContext | Complete | 2026-09-22 | 本轮不做 commit/push |
| 0.4 | 计划增补: 脚本统一落 memory-bank skill 的 `scripts/` | Complete | 2026-09-22 | 含 `gen_tasks_index.py` 迁入与 11 处引用改写清单 (计划 §07) |
| 0.5 | 计划增补: 全库逐文档落位 + 五步配方 + cap 分级 | Complete | 2026-09-22 | 8 份超标文档 → 9 目录 / ≈45 主题文件 + 8 存根; 波次扩为 W0–W8 (计划 §03/§04/§05/§06) |
| W0 | 基线冻结与守恒清单 | Not Started | — | 待用户确认后开工 |
| W1 | pitfalls 目录化 (含守卫 / 闸门 / 接线) | Not Started | — | 收益最大, 须一次做完并尽快推送 |
| W2 | testing.md 拆分 | Not Started | — | |
| W3 | activeContext 瘦身 + progress 拆分 | Not Started | — | |
| W4 | modules / systemPatterns / conventions 按 cap 处置 | Not Started | — | |
| W5 | 文本坑 → 守阵 (5 候选) | Not Started | — | 治本波; 复发 ≥2 的条目优先 |
| W6 | 回归 + 演练 + instructions 漂移修复 | Not Started | — | |

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