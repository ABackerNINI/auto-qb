# 文档形态统一 (plans/reports 入库 + 四形态协议)
> 摘要: 四形态 (根报告 / plans / issues / tasks) 职责重叠、登记方式各异; 已拍板 plans + reports 收进 `memory-bank/`, 收敛为「四工位 + 一套协议」。**计划已出, 待拍板, 未开工, 未提交**。勘察要点: 计划与报告**零 meta / 零索引 / 零守卫**（44 份计划只有 `viewport` 一行）; 同一专题最多 5 份 (column-prefs / optimistic-ui); `docs/plans` 引用面 **209 处 / 90 文件**; 唯一运行时耦合 = `scripts/sim_baseline.py:27` 的 `BASELINE_PATH`; 决定**存量 51 份不改名**、状态词统一 5 词、主键 `doc-topic` + `_doc-map.md` 专题视图。
> 触发: 文档形态, 四形态, docs/plans, reports, 入库, 计划归档, 报告归档, doc-topic, doc-map, 状态词统一, 立档, 索引守卫, 重复文档
> 最后活动: 2026-09-23 19:59

## 状态

**计划**: [../../docs/plans/26-09-23-1959-memory-bank-doc-forms-plan.html](../../docs/plans/26-09-23-1959-memory-bank-doc-forms-plan.html)
(只读勘察基树 `19fa6ee`; 计划自身随 W1 迁入 `memory-bank/plans/`)。
**档案**: [../tasks/26-09-23-memory-bank-doc-forms.md](../tasks/26-09-23-memory-bank-doc-forms.md)

**已定的口径**:

- **四工位职责互斥**: issue = 要不要修 / plan = 怎么修 (拍板后冻结) / report = 现场快照 (出厂冻结) /
  档案 = 唯一滚动更新点。「每条事实只在一个工位有权威」。
- **统一协议五件套**: ① 4 个类型 token + 新件命名 `YY-MM-DD-HHMM-<type>-<topic>.html`（存量不改名）
  ② `doc-type / doc-topic / doc-status / doc-added / doc-updated / doc-refs` meta（tasks 用现有字段 +
  `**Topics:**`，issues 保留 `issue-*` 并新增 topic/refs；**不做无收益的字段改名**）
  ③ 状态词 5 词 `Open / In Progress / Done / Dropped / Superseded`
  ④ 双视图: 各目录 `_index.md` + `memory-bank/_doc-map.md`（一行一专题 + 陈旧标记）
  ⑤ 认领链 `doc-refs` 双向一致（仅校验新件）。
- **目录落位**: `memory-bank/plans/`（← `docs/plans/`）· `memory-bank/reports/`（← `docs/` 根）；
  `docs/` 只留用户文档与 `context7/`。新目录走 tasks/issues 模式：无 `_about.md`、自带生成器、
  `EXCLUDED_DIRS` + `role_of → index-auto`。
- **不做的事**: 不合并四目录；不加第五形态；不动 tasks/activeContext 两条命名规则；不改存量文件名；
  只修 `TODO.md` / `想法.md` 的路径串、不碰其内容。

## 待办(下一步从这里接)

1. **拍板 D1–D5**（计划 §07, 均给默认取值, 未否决即按默认执行）。
2. **W0 → W5 实施**（计划 §04）; W1 是高风险步 —— `git mv` 与引用面修正**必须同一提交**。
3. **提交**: 计划文档 + 档案 + 本切片均为新建, **用户尚未说「提交」**。

## 单点指针

- 计划全文(现场证据 · 目标形态 · 协议 · 波次 · 引用面 · 风险 · 决策点 · 验收判据) →
  [../../docs/plans/26-09-23-1959-memory-bank-doc-forms-plan.html](../../docs/plans/26-09-23-1959-memory-bank-doc-forms-plan.html)
- 上一个相邻重构(库内文档拆分, 与本次正交) → [../tasks/26-09-22-memory-bank-dir-refactor.md](../tasks/26-09-22-memory-bank-dir-refactor.md)
- 编辑 HTML 的坑(meta 注入时必读) → [../pitfalls/docs/html-edit.md](../pitfalls/docs/html-edit.md)
- 文档与代码冲突裁决 → [../pitfalls/docs/drift.md](../pitfalls/docs/drift.md)