# 26-10-18-memory-bank-doc-topics-composite-split — 复合 Topics 键收敛单主键: 约定收紧 + 机检 + 存量 8 份回归

**Status:** In Progress
**Added:** 2026-10-18
**Updated:** 2026-10-18
**Summary:** 复合 Topics 键收敛单主键: 约定收紧 + 机检 + 存量 8 份回归
**Topics:** memory-bank-doc-topics-composite-split
**Refs:** memory-bank/issues/26-10-18-0858-question-doc-topics-composite-split.html

## 原始请求

1. 「认领 26-10-18-0858-question-doc-topics-composite-split.html, grilling」—— 认领该 question issue，以 grilling（设计树逐轮逼问）方式拍板，直到双方共识；认领机械面（状态/认领链/索引）随拍板执行。

## 思考过程与决策

**issue 二选一**：① 生成器拆键（`TASK_TOPICS_RE` 按英文逗号 split，一份档案 join 多个专题）· ② 维持单主键口径（约定收紧 + 存量另议）。

**取证（2026-10-18）**：存量复合键恰 8 份（全在 `tasks/`、全 Done、分三种形态——5 份 `webui-detail-panel-redesign, webui-drawer-templates`、1 份 `webui-detail-panel-redesign, webui-polling-cadence`、2 份标签串）；HTML 四形态 `doc-topic` 零逗号；`doc-forms.md` 现行约定本就写「Topics 单 kebab 主键，多对多走 Refs 链」；坑档 `doc-topics-comma-composite.md` 处置已按单值口径裁过（只把存量标为「属设计决策」）；`--topic webui-drawer-templates` / `webui-polling-cadence` / `drawer-tpl` / `a11y` 均「无此专题」，症状复现确认。

**Round 1 拍板（2026-10-18 09:56，用户四问全「是」）**：
1. **方案②**：维持 Topics 单主键，生成器不拆键。理由：①=推翻并重排全部 343 个专题的历史分组且不可逆；两份标签串证明多键 Topics 本质是拿主键当标签——拆键等于把坏数据制度化；多对多关系已有 `**Refs:**` 双向链这条正路。
2. **认领锚点 = 本任务档案**（`kb.new task --refs` 自动双向补链，issue `doc-refs` ↔ 本档 `**Refs:**`）。
3. **加机检**：`gen_doc_map --check` 新增「Topics/doc-topic 必须是单 kebab」（`^[a-z0-9]+(-[a-z0-9]+)*$`），逗号即判红，挂提交闸门。
4. **存量 8 份本轮一并回归**单主键，不留历史特例。

**Round 2 拍板（2026-10-18，用户三问全「是」）**：
1. **决策落点 = 直改，不另出计划件**：拍板即结论，本档案为「修到哪了」的唯一滚动权威（计划件冻结，不适合还有执行面要滚动的场景）。
2. **次要键处置**：无反声明目标的次要键从元数据整体消失——8 份的所有次要键（`webui-drawer-templates`/`webui-polling-cadence`/`drawer-tpl`/`a11y`/`roving-tabindex`/`keyboard-nav`/`search-pending`/`sticky-anchor`）无一作为制品主键存在，无法走 Refs 承载；分面信息留正文/Summary。不新增元数据槽位（`**Also:**` 之类 = 变相恢复多键，与②自相矛盾）。
3. **逐件归属**（子代理调研 + 关键锚点复核）：row-keyboard → `webui-detail-panel-redesign`（issue 0846 催生，Refs 已承载）；search-jump → `drawer-dock`（停靠面板行为流，与 collapse-removal 同键同组）；**六份 10-14 档案全部 → `webui-detail-table-rebuild`**（detail-table-rebuild 复查浪：计划 0811 + 报告 0136 + 档案 26-10-13 现存同键；关键反直觉点——复合键第一键 `webui-detail-panel-redesign` 本就写错，该专题 10-07/08 已随 0845/0846 收官）。

## 实现计划

1. `doc-forms.md` 补强：「主键形态」条（单 kebab + 逗号反例 + 指向机检）+ `--check` 行补主键形态越界。✅
2. `gen_doc_map.py --check` 新增主键形态校验（`KEBAB_RE`：档案 `**Topics:**` + 四形态 `doc-topic`，逗号判红）；`tests/test_docs_forms.py::test_doc_map_flags_composite_topic_key` 同源复验。✅（机检先红——8 件全捕获——后绿验证捕获力）
3. 8 份存量档案 Topics 行回归单主键 + `kb.bump` 留痕 + 进度日志日期行。✅（六份 → webui-detail-table-rebuild；row-keyboard → webui-detail-panel-redesign；search-jump → drawer-dock）
4. 坑档 `doc-topics-comma-composite.md` 触发/处置段重写（存量已清零，不再是「待设计决策」）。✅
5. 收尾：issue §01/§03 填定论 + 状态置 Done；`kb.index` 重建；`kb.check` 全绿。✅（720 份文档 / 340 专题 / 认领链闭环；test_docs_forms 17 passed）

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | doc-forms 补强「主键形态」条 + --check 行 | Done (2026-10-18) |
| 2 | gen_doc_map --check 机检 + pytest 同源复验 | Done (2026-10-18) |
| 3 | 8 份存量 Topics 回归单主键 + 留痕 | Done (2026-10-18) |
| 4 | 坑档 doc-topics-comma-composite 处置段重写 | Done (2026-10-18) |
| 5 | issue 填定论 + 置 Done + 索引 + kb.check | Done (2026-10-18) |

## 进度日志

### R0 · 立档 + 认领 + Round 1 拍板 (2026-10-18)

- 09:16 会话开始：读 issue + 取证（8 份存量清单、343 专题现状、症状复现、doc-forms 与坑档既有口径、认领链协议）。
- 09:48 用户 Round 1 四问全「是」：②单键口径 / 本档认领 / 加机检 / 存量本轮处理。
- 09:56 立本档（`kb.new task --refs` 指向 issue，双向补链自动完成）；issue-status `Open → In Progress`（直改 meta + 徽章 + 状态变更日志两行留痕；`kb.status` 不接 issue，按 create-issue 口径直改）。
- 子代理完成 8 份逐件归属调研，关键锚点已复核（`webui-detail-table-rebuild` 现存 3 件、issue 0846 doc-topic=webui-detail-panel-redesign、两份 10-07 档案 Refs 已承载原关联）。

### R1 · Round 2 拍板 + 执行落地 (2026-10-18)

- 10:0x 用户 Round 2 三问全「是」：不另出计划件 / 次要键消失（无反声明目标）/ 8 份逐件归属按调研提案（含 #6 classic-removal 保留意见被接受——归 rebuild 键）。
- 执行：gen_doc_map 加 `check_topic_key_shape`（机检先红 8 件后绿）；8 份 Topics 行改写 + kb.bump + 日志行；doc-forms「主键形态」条；坑档触发/处置重写；issue 三段定论 + 状态 Done。
- 分组变化（预期内）：`webui-detail-panel-redesign` 7→8 件、`webui-detail-table-rebuild` 3→9 件、`drawer-dock` 1→2 件；340 个专题零异形键。
- 收口：kb.check 全绿（720 份 / 340 专题 / 状态词表 / 认领链闭环）；test_docs_forms 17 passed（新增 test_doc_map_flags_composite_topic_key）。
