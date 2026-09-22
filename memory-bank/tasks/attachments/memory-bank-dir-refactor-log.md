# memory-bank 目录化重构 · 较早的进度日志

> 摘要: `26-09-22-memory-bank-dir-refactor` 档案里**较早**的进度日志(W0–W5 各波)—— 档案本体保留最近的部分。
> 触发: 目录化重构, 进度日志, W0, W1, W2, W3, W4, W5, 历史条目

> 迁移说明(2026-09-22 W8): 原在 `../26-09-22-memory-bank-dir-refactor.md`, 该档案因每波都追加日志而超 24 KB ⇒
> 把较早条目移到这里, **内容逐字未改**。

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
