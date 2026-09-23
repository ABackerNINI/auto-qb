# 文档形态统一 (plans/reports 入库 + 四形态协议)
> 摘要: 四形态 (根报告 / plans / issues / tasks) 职责重叠、登记方式各异; 已拍板 plans + reports 收进 `memory-bank/`, 收敛为「四工位 + 一套协议」。**按波次实施中: W0 协议 (`75bb0ca`) · W1 迁入库 (`b96d0cf`) · W2 补 meta/统一状态词已提交** —— 47 份计划 + 8 份报告在 `memory-bank/plans|reports/` (含违规 md 转 dark HTML), 51 份计划/报告已带 `doc-*` meta; 39 issues + 35 档案状态统一为 5 词表, 档案补 `**Topics:**`; 专题归并 **77 topic / 25 个跨形态簇** (column-prefs 5 件 · optimistic-ui 8 件)。勘察要点: 计划与报告**零 meta / 零索引 / 零守卫**; 同一专题最多 5 份 (column-prefs / optimistic-ui); 决定**存量 51 份不改名**、状态词统一 5 词、主键 `doc-topic` + `_doc-map.md` 专题视图。
> 触发: 文档形态, 四形态, docs/plans, reports, 入库, 计划归档, 报告归档, doc-topic, doc-map, 状态词统一, 立档, 索引守卫, 重复文档
> 最后活动: 2026-09-23 20:49

## 状态

**计划**: [../plans/26-09-23-1959-memory-bank-doc-forms-plan.html](../plans/26-09-23-1959-memory-bank-doc-forms-plan.html)
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

1. **W3 生成器** (`gen_docs_index.py` / `gen_doc_map.py`) + README 索引登记 (随生成物一起落)
2. **W4 守卫** (`tests/test_docs_forms.py` + 闸门 + `check_doc_links.is_frozen` 增补) → **W5 回写收口**
3. 已提交: `dc9e832` (计划+立档) · `75bb0ca` (W0) · `b96d0cf` (W1); 每波次单独提交 + 推 Gitee (GitHub 镜像直连不通, 只报一次)

## 单点指针

- 计划全文(现场证据 · 目标形态 · 协议 · 波次 · 引用面 · 风险 · 决策点 · 验收判据) →
  [../plans/26-09-23-1959-memory-bank-doc-forms-plan.html](../plans/26-09-23-1959-memory-bank-doc-forms-plan.html)
- 上一个相邻重构(库内文档拆分, 与本次正交) → [../tasks/26-09-22-memory-bank-dir-refactor.md](../tasks/26-09-22-memory-bank-dir-refactor.md)
- 编辑 HTML 的坑(meta 注入时必读) → [../pitfalls/docs/html-edit.md](../pitfalls/docs/html-edit.md)
- 文档与代码冲突裁决 → [../pitfalls/docs/drift.md](../pitfalls/docs/drift.md)