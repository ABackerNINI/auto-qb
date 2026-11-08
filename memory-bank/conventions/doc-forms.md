# 文档形态与制品协议 (四工位 + 一套协议)

> 摘要: 计划 / 报告 / issue / 任务档案四类制品的「放哪、叫什么、状态怎么流转」—— 记一件事之前先读这张决策树。
> 触发: 写计划, 写报告, 入池, 立档, 制品放哪, 文档形态, doc-topic, 状态词, 计划入库, 报告入库, 认领链, 计划改版, 创建方式, kb.new, 命令化创建

## 四工位 (类型 token = 新件文件名的第二段)

| 工位 | 回答什么 | 目录 | 载体 | 寿命 | 唯一权威 |
|---|---|---|---|---|---|
| issue | 要不要修、什么时候修 | `memory-bank/issues/` | HTML | 终态即冻结 | 优先级与排期 |
| plan | 怎么修、为什么这么修 | `memory-bank/plans/` | HTML | **拍板后冻结** | 方案与取舍 |
| report | 当时现场是什么样 | `memory-bank/reports/` | HTML | 出厂即冻结 | 证据快照 |
| task | 实际怎么修、做到哪了 | `memory-bank/tasks/` | Markdown | **唯一滚动更新** | 执行与验证数字 |

> 每条事实**只在一个工位有权威** —— 同一件事的其余件只引用、不重写 (重写必然漂移)。
> 旧路径已废: `docs/plans/` → `memory-bank/plans/` · `docs/*.html`(报告) → `memory-bank/reports/` (2026-09-23 迁入)。

## 决策树: 要记一件事 → 放哪儿

写前先做两问(只做自检, 不建四象限目录): 读者是在**做事**还是**理解**? 在**获取技能**还是**应用技能**?
答案落成 **Form**: `reference`(事实/清单/参数) · `how-to`(按步骤完成任务) · `explanation`(为什么这样设计)。
Form 切**内容形态**, 与四工位(制品用途/寿命)**正交**, 四工位不改名。

| 这一轮做的事 | 放 | 形态判定 (Form) |
|---|---|---|
| 撞见计划外的问题, 暂不修 | `issues/<stamp>-<type>-<slug>.html` (create-issue skill; 入池/翻状态走 `kb.new issue`/`kb.status`) | `how-to`(复现) + `reference`(事实) |
| 要改动, 需方案与拍板 | `plans/<stamp>-plan-<topic>.html` | `explanation` |
| 审计 / 故障取证 / 可行性分析 | `reports/<stamp>-report-<topic>.html` | `explanation` |
| 跨会话推进的专题 (≥2 会话 / ≥5 轮指令 / 出现波次表述) | `tasks/YY-MM-DD-<领域>-<专题>.md` (memory-bank skill) | `explanation` |
| 本次会话做到哪 | `active-context/<stamp>-<topic>.md` | `reference` |
| 长期结论 / 已实现事实 | 主题文档(`architecture/` · `conventions/` · `projectbrief.md`; 演进叙事在 tasks/plans 原始件) | `explanation`(结论) / `reference`(事实表) |

## 命名 (新件强制; 存量豁免)

- 新件: `YY-MM-DD-HHMM-<type>-<topic>.html`(时间戳用 `commands run kb.time stamp` 取当前值), `<type>` ∈ `plan` / `report`。
- 存量计划与报告(2026-09-23 前)**不改名** —— 类型由所在目录 + `doc-type` meta 判定。
- 一篇一件事; **计划改版 = 同文件内 `## 变更记录` + 抬 `doc-updated`**, 禁止再堆 `-v2` / `-v3` / `-roundN` 新文件。

## meta 协议 (`doc-*`)

```html
<meta name="doc-type" content="plan">            <!-- plan | report -->
<meta name="doc-topic" content="<专题 kebab>">    <!-- 跨形态串联主键 -->
<meta name="doc-status" content="Open">           <!-- 5 词表, 见下 -->
<meta name="doc-added" content="26-09-23-1959">
<meta name="doc-updated" content="26-09-23-1959">
<meta name="doc-refs" content="认领链目标的仓库根相对路径 (逗号分隔, 见「认领链」)">
```

- 档案 (md): `**Status:**` / `**Added:**` / `**Updated:**` / `**Summary:**` 承载同义字段 + `**Topics:** <专题>` 主键, 引用他件写 `**Refs:**`。
- **主键形态 (单值, 2026-10-18 收紧)**: 档案 `**Topics:**` 与四形态 `doc-topic` 只能是**一个** kebab 主键 (`^[a-z0-9]+(-[a-z0-9]+)*$`)。逗号写多专题(沿袭 `**Refs:**` 的逗号习惯)会把整串当成单一复合键 —— `--topic <单专题名>` 检索不到、跨形态视图按复合键分组、名录出现异形键 (issue 26-10-18-0858; 坑档 [doc-topics-comma-composite](../pitfalls/kb/doc-topics-comma-composite.md))。多对多关系一律走 `**Refs:**` 双向链 (见「认领链」), 不占主键; `gen_doc_map --check` 对逗号 / 非 kebab 判红 (机检单点)。**反例**: `**Topics:** webui-detail-panel-redesign, webui-drawer-templates`。
- issue: 保留 `issue-*` meta (生成器数据源), 新增 `doc-topic` / `doc-refs`。
- **不做字段改名** —— 漂移源是状态词, 不是字段名; 生成器里一张映射表 (单点)。

## 状态词 (5 词, 四形态共用)

`Open` → `In Progress` → `Done` | `Dropped` | `Superseded`

映射: issue `Fixed`→Done · `WontFix`→Dropped · `Duplicate`→Superseded; 档案 `Pending`→Open · `Completed`→Done · `Abandoned`→Dropped; plan 待拍板 = Open / 实施中 = In Progress / 被新版取代 = Superseded; report 恒 `Done` (快照完成即终态)。

> **单点**: 5 词表定义在 `_common.DOC_STATUSES`(校验器 `gen_doc_map` 与守卫
> `test_docs_forms` import 同源, 不手抄)。表外值 → `kb.status` 词表校验直接拒绝 +
> `gen_doc_map --check` 同源校验 (2026-10-16, 见 [pitfalls/kb/doc-status-meta.md](../pitfalls/kb/doc-status-meta.md))。
> 与档案的 4 词表 (`**Status:**` = In Progress/Open/Done/Dropped) **不同**, 别互相套用。

## 索引与检索 (2026-11-08 重构后)

- 记录层(四工位)**零索引**: `plans/` `reports/` `issues/` `tasks/` 的 `_index` 全部退役 ——
  人走 `commands run kb.nav`(台账/专题视图**现算, 不落盘**; 默认只展**活跃**专题, `--topic <key>` 单专题下钻),
  agent 走 `grep -rn "<词>" memory-bank/`。
- **pitfalls 的 8 个 `_index.md` 是全库唯一生成索引例外**(触发词聚合 = 改码前扫陷阱载体,
  grep 替代不了「扫到不知道的坑」); 重建 = `commands run kb.index`, 不要手改。
- 机检(无物化文件): 缺主键 / **主键形态越界(逗号·非 kebab)** / 状态词表越界 / 单向认领链
  = `gen_doc_map.py --check`(挂 `kb.check` 与提交闸门, 纯文档轮也覆盖)。

## 认领链

issue 被认领 → 两侧都记引用 (issue 的 `doc-refs` ↔ 档案的 `**Refs:**`), 生成器校验双向一致, 缺链即闸门红。
「要修吗 / 什么时候修」的答案永远在 issue 侧; 「修到哪了」在档案侧。

- **声明方式**: HTML 用 `<meta name="doc-refs">`, md (任务档案 / active-context 切片 / 基线切片 / 坑档) 用正文 `**Refs:**` 行 —— 生成器对任何 md 只认**首个** `**Refs:**` 行; 值 = **仓库根相对路径**, **多目标一律英文逗号、全部目标写在这一行** —— `·`/`、`/`;`/`|` 等视觉分隔符会把整串当成单一路径, 判「目标不存在」。只校验**声明过**的件, 未声明天然豁免。
- **合法目标**: 任何能反向声明的文件 —— 四形态件、基线切片、坑档、active-context 切片都合法。**反向声明 = 在目标件里写一行 `**Refs:** <引用方的仓库根相对路径>`** (md 建议放三行头/状态行之后); 引向无法反向声明的文件即单向链, 判红。
- **导航页口径 (2026-11-07)**: `kb.nav` 把每条 ref 解析成五态后渲染 —— `ok`(落在四形态件里, 可下钻) /
  `ext`(文件在 `memory-bank/` 内但不在台账扫描面, 如坑档 / 基线 / 切片, 可打开) / `repo`(文件在仓库根下,
  如 `resources/`, 存在但导航页静态路由不代理, 只标示不可点) / `basename`(声明路径失效, 按 basename 在
  `testing/baselines/attachments/` 找回) / `dead`(真失效)。**解析只在导航层** (`nav_data`), 不改
  `collect()` 的扫描面与「台账件」定义 (`kb.check` 与 `kb.nav` 共用该单点)。
  判据与 `kb.check` 的 `check_claim_chain` 对齐: ref 是**仓库根相对**路径; 归档回退只对
  `memory-bank/testing/baselines/` 开头的 ref 生效 (否则台账件被删而同名基线切片还在时, 会把真死链说成可打开)。
  实测 1215 件 / 1856 条 ref: `ok` 1267 · `ext` 299 · `basename` 253 · `repo` 2 · `dead` **35**
  (全为历史件指向 26-11-08 已删路径, 计划 §07 R1 明示预期, 非机检故障) ——
  页面上的「未入库」从来不是丢了件。
- **机检单点**: `gen_doc_map.py --check` (挂提交闸门 `memory-bank/` 与 `kb.check`, 纯文档轮也覆盖; 2026-10-03 自 tests/test_docs_forms.py 下沉, 该测试同函数复验), 声明方 = 四形态全量。

## 创建/更新方式 (命令化, 2026-10-17)

一次逻辑动作 = **一条命令 + 一次填空**: 时间戳 / 命名 / 头部字段等**派生面零手写** ——
命令是上面各节规范单点的**执行器**, 不是第二套规范 (词表 / 命名 / cap 仍以本节与 `_common` 为准;
计划 [26-10-17-0527](../plans/26-10-17-0527-plan-memory-bank-doc-pipeline.html), `commands run kb.new` 等四条
已随 P1/P2/P3 落地)。文档里**只写 task id, 不抄命令本体** (`commands run doc.drift` 判红手抄)。

| 动作 | 命令 (task id) | 派生 (零手写) |
|---|---|---|
| 新建计划 | `commands run kb.new plan --title ".." --topic <kebab>` | 戳 / 命名 / 头部 / SLOT |
| 新建任务档案 | `commands run kb.new task --title ".." --topic <领域>-<专题>` | 同上 + Summary 预填 (裁定 A1) + 查重 (含跨 clone) |
| 新建报告 | `commands run kb.new report --title ".." --topic <kebab>` | 同上; **出厂即 Done** (快照终态) |
| 新建 issue | `commands run kb.new issue <slug> --type <8 类之一> --title ".." --summary ".." [--tier|--module|--reporter|--topic]` | 戳 / 命名 / 头部 / badge; 流程语义见 create-issue skill |
| 新建坑档 | `commands run kb.new pitfall --class <7 类之一> --title ".." --topic <slug> --triggers "词, 词"` | 三行头 (摘要预填; **触发词走参数** —— 路由判断不可派生, 裁定 A7 参数分支) |
| 新建基线切片 | `commands run kb.new baseline --title ".." --topic <slug> --total "N passed + M skipped"` | 戳 / 基线时间 / 命名; **`--total` 由 test.full 实测誊写** (裁定 A4: 命令不编造数字) |
| 翻转状态 | `commands run kb.status <path> <to>` | 词表校验 (单点 import) / 抬 doc-updated 或 Updated |
| 改版落盘 | `commands run kb.bump <path> --note ".."` | 抬 doc-updated + 变更记录追加 R 行 (档案抬 Updated / 切片抬最后活动) |
| 收尾机械面 | `commands run kb.wrap --topic <slug> --did ".."` | 切片抬活动 + R 行 / 档案 Updated + 进度日志日期行 (D6: 蒸馏与判断仍是 agent 的活) |

- 命令建后留 `<!-- SLOT: -->` 填空标记 (判断面), **头部区零 SLOT** (机器字段由命令填); 填完前
  新增面守卫 (冻结线之后新建件) 判红 (坑档 / 进展件命名无时间戳, 不在扫描面, 由既有守卫兜底)。
- `--refs` 走 D4 双向补链: 目标件自动反向声明, 只动元数据行, 幂等 (见上「认领链」)。
- **切片不由 `kb.new` 建** (拍板: 统一 `kb.wrap` 收尾处理); issues 已入列 (2026-11-07 翻案 [26-10-17-0527](../plans/26-10-17-0527-plan-memory-bank-doc-pipeline.html) D2): 入池 `commands run kb.new issue` / 翻状态 `commands run kb.status`, 流程语义见 create-issue skill。
- **伞形档案与派生计划各持不同 key 时用档案锚点**: `kb.wrap --topic <切片 slug> --archive <档案 Topics 键>`
  一次同时命中两侧 (切片仍由 `--topic` 落, 档案按 `--archive` 精确匹配; 不传时沿用 `--topic` 匹配,
  行为不变)。**不要为此改档案 Topics** —— 档案键是件自身身份, 不随派生计划变。
- 剩余人工步骤的量化口径 (判断 / 条件 / **机械 0**) 与输出契约: 计划 §05。