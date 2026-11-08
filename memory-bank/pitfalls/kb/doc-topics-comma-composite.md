# Topics 行英文逗号不拆主键

> 摘要: Topics 行英文逗号不拆主键
> 触发: Topics, 专题主键, docmap, 跨形态视图, 名录

### 档案(任务/切片)的 `**Topics:**` 行写成英文逗号分隔的多专题时, 整串被当成**一个**复合主键

- **触发**: 在任务档案/切片的 `**Topics:**` 行按 `**Refs:**` 的逗号习惯写多个专题(如 `**Topics:** webui-detail-panel-redesign, webui-polling-cadence`); `gen_doc_map` 的 `TASK_TOPICS_RE` 用 `(.+)$` 整串捕获, 不拆键。存量曾有 8 份档案踩过(如 26-10-14-webui-drawer-cadence-main-beat, 2026-10-18 已回归单主键); 2026-10-18 起 `--check` 机检拦截新犯。
- **判别**: `kb.docmap --topic <单专题名>` 找不到明明相关的档案; 专题视图名录里出现带空格/逗号的"异形主键"(如 `topic-alpha, topic-beta`); `gen.collect` 的 group 键含逗号。
- **处置**: 主键单值口径以 doc-forms「主键形态」为准(Topics 是**一个** kebab 主键, 多对多关系用 `**Refs:**` 双向链表达, 不是逗号); `gen_doc_map --check` 已加机检(单 kebab 正则, 逗号判红, 挂提交闸门, 2026-10-18 随 issue 26-10-18-0858 拍板落地)。**存量 8 份复合键件已于 2026-10-18 全部回归单主键**(拍板②: 生成器不拆键、约定收紧; 六份 10-14 档案归 `webui-detail-table-rebuild`——原复合键第一键 `webui-detail-panel-redesign` 本就写错, row-keyboard 归 `webui-detail-panel-redesign`, search-jump 归 `drawer-dock`; 次要键无反声明目标, 从元数据消失, 关联由同键分组 / 已引 Refs 承载)。新件写单个 kebab 主键。附带的坑: 含空格的复合键曾被 `_name_list` 按字节位折行撕断(2026-10-18 已修, 折行改以专题名为原子)。
- **守阵**: `tests/test_docs_forms.py::test_doc_map_name_list_never_splits_keys`(折行不撕键); `test_doc_topics_complete`(不缺主键)
- **复发**: 1 (2026-10-18, auto-qb-clone1): issue 26-10-18-0858 的机检与本条约定在 **10:39 才由另一会话落库**, 而本会话的同日 Phase 2 档案回写仍按旧版 `doc-forms` 与 `**Refs:**` 的逗号习惯写成 `**Topics:** backend-traffic-snapshot-merge, webui-traffic-limit-card` —— 机检**捕获力实证**(`ship.commit` 是「先提交 → rebase 远端 → 在合并后的树上复跑闸门」, 所以是**自己那一笔已入库后才被判红**, 修复按管线口径作为新提交, 不 amend、不撤)。**为什么没命中**: 会话在机检落地前就开工, 回写时读到的约定是旧版; 「新件写单个 kebab 主键」这条在本地根本不存在, 靠回忆也救不了。**处置**: 主键只留本件自身身份键, 次要专题由 `**Refs:**` 双向链与 Summary 措辞承载(本条即把 `webui-traffic-limit-card` 从元数据移除, 关联改由 Refs 指向合并卡计划/基线切片)。**收敛口径**: 跨会话长任务的收尾回写前, 若中间有别的会话可能落库, 回写与提交之间必跑一次同步(`ship.commit` 内含 rebase 但不替你改文档) —— 新机检与新约定就是在这个窗口里进来的。
