# 手写计划/报告绕过 kb.new: 缺 doc-* 头部整件逃出新增面守卫

> 摘要: 手写计划/报告绕过 kb.new: 缺 doc-* 头部整件逃出新增面守卫
> 触发: 计划件无状态, (无状态), 手写头部, doc-status, doc-added, 缺状态, 排期计划, 新建计划

### 手写 plans/reports 抄冻结线前旧件头部, 缺 doc-status 整件逃出新增面守卫 (RM02-RM10 九件事故)

- **触发**: 直接手写 `plans/` 或 `reports/` 的 HTML 并手工拼头部 (抄冻结线前旧体例, 带 `plan-slug`/`plan-stamp` 旧 meta), 不走 `commands run kb.new plan/report`; 文件名 topic 带大写 (如 `plan-real-RM02.html`) 同时违 `PLAN_FILE_RE` (只认小写)。事例: 26-10-31 RM02-RM10 九份真机排期计划全部缺 doc-status/doc-added/doc-type/doc-updated, kb.nav 归进「(无状态)」桶。
- **判别**: ①守卫视角: `commands run kb.check` 全绿但件缺头部 —— 旧圈面按**文件自身 doc-added** 决定扫不扫, 缺 doc-added 的新件整件跳过 (豁免自噬: 越缺字段越查不到; 26-10-31 已修: 圈面 = 文件名 stamp 前缀, 不读文件内部 meta)。②人工视角: `kb.nav` 出现「(无状态)」件; `gen_docs_index` 把缺状态**默认记 Open** (与 nav 口径不一致, 别拿索引状态当真)。
- **处置**: 建件一律 `commands run kb.new plan/report` (模板自带 doc-status; SLUG_RE 拒大写 topic, 建件端还有命名正则不变量守卫); 已入库的残缺件回填四 meta (doc-type/doc-status/doc-added/doc-updated) + 文件名改小写 (Windows 大小写改名见 `pitfalls/git/windows-case-only-rename.md`) + 同步全部引用点 + `kb.index`。守卫侧 26-10-31 起缺头部新件必红, 不再需要人工兜底。
- **守阵**: tests/test_memory_bank.py::test_checker_catches_new_plan_missing_doc_added (圈面洞回归阵) + test_checker_freeze_line_exempts_stock (存量豁免方向仍绿)
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)
