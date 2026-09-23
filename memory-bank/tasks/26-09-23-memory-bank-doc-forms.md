# 26-09-23-memory-bank-doc-forms — 文档形态统一 (plans/reports 入库 + 四形态协议)

**Status:** Open
**Added:** 2026-09-23
**Updated:** 2026-09-23
**Summary:** 四形态 (docs 根报告 / docs/plans 计划 / issues / tasks) 职责重叠且登记方式各异 —— 计划与报告零 meta / 零索引 / 零守卫, 同一专题最多被讲述 5 遍; 已拍板 plans + reports 收进 memory-bank/, 收敛为「四工位 + 一套协议」(类型与命名 · `doc-*` meta · 5 词状态 · 双视图索引 · 生命周期与单一权威); **计划已出, W0–W5 待拍板后实施**
**Topics:** memory-bank-doc-forms

## 原始请求

> 目前有4种形态的doc职责相似或重复: docs/*.html, docs/plans, memory-bank/issues, memory-bank/tasks, 急需统一, 请先设计一个方案

> 将plans与reports都收入memory-bank中, 生成计划

## 思考过程与决策

### 现状实测 (2026-09-23, 只读勘察 @ 19fa6ee)

| 形态 | 位置 | 数量 | 载体 | 状态机 | 索引 / 守卫 |
|---|---|---|---|---|---|
| 报告 | `docs/*.html` | 7 | HTML | 无 | 无 / 无 |
| 计划 | `docs/plans/` | 44 html + 1 md 违规 + 2 json | HTML | 无 (靠 v2/v3 堆版本) | 无 / 无 |
| issue | `memory-bank/issues/` | 39 | HTML | 5 态 | 生成物索引 + 守卫 + 闸门 |
| 档案 | `memory-bank/tasks/` | 34 (18 非终态) | Markdown | 4 态 | 生成物索引 + 守卫 + 闸门 |

- **引用面**: `docs/plans` 全仓 **209 处 / 90 个文件** (tasks 27 · plans 自引 15 · progress 10 · issues 9 ·
  activeContext 5 · src 3 · testing 3 · scripts 6 · 其余 12); `docs/` 根报告 17 个引用文件。
- **零登记的两类**: 44 份计划只有 `viewport` 一行 meta (机读不了类型 / 状态 / 专题); 无 `_index.md`、
  无守卫、无闸门 —— 存量 `.md` 违规 (`docs/plans/26-09-15-1150-dependency-lock-report.md`) 无人拦。
- **职责重复实证**: column-prefs = 报告 1 + 计划 2 + issue 1 + 档案 1 (5 份);
  optimistic-ui = 报告 2 + 计划 2 + issue 1 (5 份); 版本靠堆文件 (`optimization-plan` v1/v2/v3,
  `fix-plan-round9/10` 与档案 `round9/10/11` 并存)。
- **发现路径**: 根报告 3 份入链 ≤ 2, `26-09-21-0408-seed-group-status-mapping.html` 为 0 引用孤儿。
- **运行时耦合仅一处**: `scripts/sim_baseline.py:27` 的 `BASELINE_PATH` 与 `sim_run.py --baseline` 默认值
  (语料基线 json 随迁); 其余 `src/` · `scripts/` 命中都是 docstring 里的「见计划 X」。
- **机检盲区**: `check_doc_links.py` 只扫 `.md`, `is_frozen` 按 `plans`/`issues` + `.html` 判定 ——
  迁移后 HTML 仍不在扫描面, 但新生成物 (`_index.md` ×2 · `_doc-map.md`) 在。

### 决策 (写进计划的判据)

1. **用户已拍板**: plans 与 reports 都收进 `memory-bank/` —— 报告不再另建 `docs/reports/`, 直接落
   `memory-bank/reports/`; `docs/` 只保留用户文档 (`configuration.md` / `sim-client-test-howto.md`) 与
   `context7/` 第三方缓存。
2. **统一的是协议, 不是目录**: 四工位物理性质不同 (HTML 交付物 vs MD 滚动档; tasks 不带时分靠撞名暴露
   重复、activeContext 带时分避撞名, 意图相反必须分目录) —— 合并目录会破坏既有收口机制。
3. **类型 4 token** (`issue` / `plan` / `report` / `task`), 新件 `YY-MM-DD-HHMM-<type>-<topic>.html`;
   **存量 51 份不改名** (125 条唯一路径被引用, 改名引用面远超收益)。
4. **状态词统一 5 词** (`Open` / `In Progress` / `Done` / `Dropped` / `Superseded`), 存量脚本改写
   (39 issues + 34 档案); **字段名不做无收益改名** —— 漂移源是状态词不是字段名, 生成器里一张映射表即可。
5. **主键 `doc-topic`** 串联四形态; **双视图**: 各目录 `_index.md` + 跨形态 `memory-bank/_doc-map.md`
   (一行一专题, 含陈旧标记)。
6. **生成器落 memory-bank skill 的 `scripts/`** (与 tasks/issues 同模式: 新目录走 `EXCLUDED_DIRS`
   + `role_of() → index-auto`, 不写 `_about.md` 以免被 `gen_kb_index` 当索引目录)。
7. **生命周期**: plan 拍板后冻结 (改版 = 同文件内变更记录, 禁止再堆 `-v2/-v3`); report 出厂冻结;
   档案是唯一滚动更新点; 认领链靠 `doc-refs` 双向可查 (仅校验新件)。
8. **留档 HTML 只做路径串机械修正** (不改任何成文内容, 与 2026-09-18 档案改名的处置同款)。

## 实现计划

波次与判据见计划 §04 / §08, 五步: W0 协议落地 (目录 + conventions/doc-forms.md + `_common.py` 三处 +
细路由) → W1 迁入库 (**`git mv` 与引用面修正必须同一提交**, 含运行时 `BASELINE_PATH`) → W2 补 meta +
状态词改写 → W3 两个生成器与双视图 → W4 守卫 (`tests/test_docs_forms.py` + 闸门 + `is_frozen` 增补) →
W5 回写收口 (AGENTS 产出口径 / skill 阈值 #4 / create-issue 措辞 / TODO / `.codebuddy` 自动同步)。

计划全文 → [../plans/26-09-23-1959-memory-bank-doc-forms-plan.html](../plans/26-09-23-1959-memory-bank-doc-forms-plan.html)
(本计划自身随 W1 迁入 `memory-bank/plans/`)。

## 子任务状态表

| 波次 | 内容 | 状态 |
|---|---|---|
| W0 | 协议落地: 两目录 + `conventions/doc-forms.md` + `_common.py` 三处 + README 细路由 | Done |
| W1 | 迁入库: 51 份 HTML + 2 json 迁入; md 违规件转 HTML; 引用面同提交修正 | Done |
| W2 | 补 meta (51 份) + 存量状态词改写 (73 件) + 档案补 `**Topics:**` | Done |
| W3 | `gen_docs_index.py` + `gen_doc_map.py` + 双视图落地 | Pending |
| W4 | `tests/test_docs_forms.py` + 提交闸门 + `check_doc_links.is_frozen` 增补 | Pending |
| W5 | 回写收口 (AGENTS / skill ×2 / TODO / 镜像同步 / 本计划自身) | Pending |

## 进度日志

- 2026-09-23 19:59 **只读勘察完成**: 四形态盘点 (44 / 7 / 39 / 34)、引用面实测 (209 处 / 90 文件)、
  运行时耦合定位 (`sim_baseline.py`)、零守卫盲区确认; 方案与 5 个决策点呈报。
- 2026-09-23 用户拍板: **plans 与 reports 都收进 memory-bank/**; 其余决策点按推荐默认取值。
- 2026-09-23 **W1 已提交** `b96d0cf` (搬运 + 228 处引用 + 2 处运行时路径 + md 转 HTML; 全量 1191 passed)。
- 2026-09-23 **W2 已落**: 51 份计划/报告注入 `doc-*` meta (含把一份 ad-hoc `doc-type=fix-plan` 归一为 `plan`);
  39 issues 补 `doc-topic` + 徽标/meta 状态改写; 35 档案状态改写 (**Completed→Done ×15 · Pending→Open ×2 ·
  In Progress 保持 ×17**) + 补 `**Topics:**`; 状态词查表单点同步 (`create-issue/_common.STATUSES` ·
  `gen_tasks_index.STATUSES/STATUS_RE/EMPTY_HINT` · `tests/test_memory_bank.STATUS_RE` · 两份 SKILL.md ·
  `pitfalls/kb/tasks-archive.md`); 专题归并 **77 个 topic / 25 个跨形态簇** (column-prefs 5 件 · optimistic-ui 8 件 —— 正是勘察里点名的两处重复)。
- 待办: 用户拍板 (D1–D5 默认取值) 已按默认执行; W3 → W5 继续。
- 2026-09-23 **W0 已提交** `75bb0ca` (协议单点 + `_common.py` 接线 + README 指针; 索引登记整行随 W3 生成物).
- 2026-09-23 **W1 已落**: `git mv` 47 份计划 (44 html + 2 语料 json + 1 md 违规件) + 7 份根报告 →
  `memory-bank/plans|reports/`; 引用面 **86 + 6 个文件 / 228 处** 机械改路径 (相对链接按深度重算,
  根相对文本改 `memory-bank/…`); 12 处 `.py` 文本 + **运行时路径两处** (`sim_baseline.BASELINE_PATH` ·
  `sim_run.BASELINE_PATH`/`--baseline` 帮助文案) 同步; 违规 md 转单文件 dark HTML 并入 reports;
  迁移记录类 4 份文档 (计划/档案/切片/doc-forms) 的旧路径叙述保留不改。
- 待办: ① 用户拍板 (D1–D5 默认取值) ② W0 起实施; 实施前重跑一次 `git fetch gitee develop` 确认不落后。