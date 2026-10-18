# Topics 行英文逗号不拆主键

> 摘要: Topics 行英文逗号不拆主键
> 触发: Topics, 专题主键, docmap, 跨形态视图, 名录

### 档案(任务/切片)的 `**Topics:**` 行写成英文逗号分隔的多专题时, 整串被当成**一个**复合主键

- **触发**: 在任务档案/切片的 `**Topics:**` 行按 `**Refs:**` 的逗号习惯写多个专题(如 `**Topics:** webui-detail-panel-redesign, webui-polling-cadence`); `gen_doc_map` 的 `TASK_TOPICS_RE` 用 `(.+)$` 整串捕获, 不拆键。存量有 8+ 份档案踩过(如 26-10-14-webui-drawer-cadence-main-beat)。
- **判别**: `kb.docmap --topic <单专题名>` 找不到明明相关的档案; 专题视图名录里出现带空格/逗号的"异形主键"(如 `topic-alpha, topic-beta`); `gen.collect` 的 group 键含逗号。
- **处置**: 主键单值口径以 doc-forms 为准(Topics 是**一个** kebab 主键, 多对多关系用 `**Refs:**` 双向链表达, 不是逗号)。存量复合键件不要顺手改(会改跨形态分组, 属设计决策); 新件写单个 kebab 主键。附带的坑: 含空格的复合键曾被 `_name_list` 按字节位折行撕断(2026-10-18 已修, 折行改以专题名为原子)。
- **守阵**: `tests/test_docs_forms.py::test_doc_map_name_list_never_splits_keys`(折行不撕键); `test_doc_topics_complete`(不缺主键)
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)
