# 文档形态与制品协议 (四工位 + 一套协议)

> 摘要: 计划 / 报告 / issue / 任务档案四类制品的「放哪、叫什么、状态怎么流转、索引谁生成」—— 记一件事之前先读这张决策树。
> 触发: 写计划, 写报告, 入池, 立档, 制品放哪, 文档形态, doc-topic, 状态词, 计划入库, 报告入库, 认领链, 计划改版

## 四工位 (类型 token = 新件文件名的第二段)

| 工位 | 回答什么 | 目录 | 载体 | 寿命 | 唯一权威 |
|---|---|---|---|---|---|
| issue | 要不要修、什么时候修 | `memory-bank/issues/` | HTML | 终态即冻结 | 优先级与排期 |
| plan | 怎么修、为什么这么修 | `memory-bank/plans/` | HTML | **拍板后冻结** | 方案与取舍 |
| report | 当时现场是什么样 | `memory-bank/reports/` | HTML | 出厂即冻结 | 证据快照 |
| task | 实际怎么修、做到哪了 | `memory-bank/tasks/` | Markdown | **唯一滚动更新** | 执行与验证数字 |

> 每条事实**只在一个工位有权威** —— 同一件事的其余件只引用、不重写 (重写必然漂移)。
> 旧路径已废: `docs/plans/` → `plans/` · `docs/*.html`(报告) → `reports/` (2026-09-23 迁入)。

## 决策树: 要记一件事 → 放哪儿

| 这一轮做的事 | 放 |
|---|---|
| 撞见计划外的问题, 暂不修 | `issues/<stamp>-<type>-<slug>.html` (create-issue skill) |
| 要改动, 需方案与拍板 | `plans/<stamp>-plan-<topic>.html` |
| 审计 / 故障取证 / 可行性分析 | `reports/<stamp>-report-<topic>.html` |
| 跨会话推进的专题 (≥2 会话 / ≥5 轮指令 / 出现波次表述) | `tasks/YY-MM-DD-<领域>-<专题>.md` (memory-bank skill) |
| 本次会话做到哪 | `activeContext/<stamp>-<topic>.md` |
| 长期结论 / 已实现事实 | `progress/` 与主题文档 |

## 命名 (新件强制; 存量 51 份豁免)

- 新件: `YY-MM-DD-HHMM-<type>-<topic>.html`(时间戳用命令取当前值), `<type>` ∈ `plan` / `report`。
- 存量计划与报告(2026-09-23 前)**不改名** —— 类型由所在目录 + `doc-type` meta 判定。
- 一篇一件事; **计划改版 = 同文件内 `## 变更记录` + 抬 `doc-updated`**, 禁止再堆 `-v2` / `-v3` / `-roundN` 新文件。

## meta 协议 (`doc-*`)

```html
<meta name="doc-type" content="plan">            <!-- plan | report -->
<meta name="doc-topic" content="<专题 kebab>">    <!-- 跨形态串联主键 -->
<meta name="doc-status" content="Open">           <!-- 5 词表, 见下 -->
<meta name="doc-added" content="26-09-23-1959">
<meta name="doc-updated" content="26-09-23-1959">
<meta name="doc-refs" content="同专题其它件的相对路径 (逗号分隔)">
```

- 档案 (md): `**Status:**` / `**Added:**` / `**Updated:**` / `**Summary:**` 承载同义字段 + `**Topics:** <专题>` 主键, 引用他件写 `**Refs:**`。
- issue: 保留 `issue-*` meta (生成器数据源), 新增 `doc-topic` / `doc-refs`。
- **不做字段改名** —— 漂移源是状态词, 不是字段名; 生成器里一张映射表 (单点)。

## 状态词 (5 词, 四形态共用)

`Open` → `In Progress` → `Done` | `Dropped` | `Superseded`

映射: issue `Fixed`→Done · `WontFix`→Dropped · `Duplicate`→Superseded; 档案 `Pending`→Open · `Completed`→Done · `Abandoned`→Dropped; plan 待拍板 = Open / 实施中 = In Progress / 被新版取代 = Superseded; report 恒 `Done` (快照完成即终态)。

## 索引与专题视图 (生成物, 不要手改)

- `plans/_index.md` · `reports/_index.md` —— `gen_docs_index.py` 按状态分区生成 (行 = 类型 · 简述 · 链接)。
- `_doc-map.md` —— `gen_doc_map.py`: **一行一专题**, 列出该专题名下的 issue / 计划 / 报告 / 档案及状态; `In Progress` 超 30 天打陈旧标记。
- `issues/_index.md` · `tasks/_index.md` —— 各自生成器; 合并冲突的解法一律是**重跑脚本**。

## 认领链

issue 被认领 → 两侧都记引用 (issue 的 `doc-refs` ↔ 档案的 `**Refs:**`), 生成器校验双向一致, 缺链即闸门红。
「要修吗 / 什么时候修」的答案永远在 issue 侧; 「修到哪了」在档案侧。