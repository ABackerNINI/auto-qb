# HTML 制品的 `doc-status` 取值: 不在 5 词表 ⇒ 索引**静默漏收**

> 摘要: `plans/` `reports/` 的 `<meta name="doc-status">` 不在 5 词表(`Open`/`In Progress`/`Done`/`Dropped`/`Superseded`)时, 该件不落任何分区 ⇒ **静默漏收**。修复前 `kb.index` 仍打印「已生成 N 个生成物」、零警告, `kb.check` / `kb.docmap --check` / `doc.links` 全绿, 只有 `test.full`(`test_docs_forms.py::test_status_vocabulary`)才红。2026-10-16 已把检查**提前到根因**(生成器 fail-fast + 闸门同源校验, 见处置)。诱因通常是写了「语义上像状态、但不在表里」的词(如 `Draft`)。
> 等级: L0
> 触发: 新建计划/报告, doc-status, 状态词, 索引漏收, kb.index 已生成但件不在索引, Draft, test_status_vocabulary

**Refs:** memory-bank/tasks/26-10-16-memory-bank-doc-status-vocab-guard.md

## 判别

- **触发**: 新建 `plans/*.html` 或 `reports/*.html`, 手写 `<meta name="doc-status">`。
- **判别**: 2026-10-16 实测 —— 新计划写了 `doc-status: Draft`(语义上是"待实施", 不在 5 词表),
  于是:
  - `kb.index` 报 `[ok] 已生成 21 个生成物`, **但 `plans/_index.md` 里没有这一条**(静默漏收);
  - `kb.docmap --check` 报「主键纪律 OK: 680 份文档」并**把这个件计入文档数**(它读的是 `doc-topic`, 不是
    `doc-status`), 认领链也 OK ⇒ **看不出异常**;
  - `test_docs_index_is_regenerated` 也**不红** —— 生成器跳过该件, 索引 == 生成结果, 自洽;
  - 修复前唯一能红的闸门是 `tests/test_docs_forms.py::test_status_vocabulary`(直接校验 `doc-status` ∈ 5 词表),
    但它只在 `test.full` 跑 —— 纯文档轮提交时看不到。
  对照: md 档案的 `**Status:**` 是 4 词表(`In Progress`/`Open`/`Done`/`Dropped`, 见
  [tasks-archive.md](tasks-archive.md)), **两张表不同**, 别互相套用。
- **处置**: 计划待拍板/待实施一律用 **`Open`**(实施中 = `In Progress`; report 恒 `Done`); 改完**重跑**
  `commands run kb.index`。**2026-10-16 起已机械守住**, 不再依赖人眼:
  - **根因侧**: `gen_docs_index.build()` 遇表外值即抛 `StatusVocabularyError`, `kb.index` / `kb.check`
    两条入口都响亮报错并列出台外件(不再用「已生成 N 个」蒙混) —— 索引从此不再静默漏收。
  - **闸门侧**: `gen_doc_map --check` 加同源词表校验, 提交闸门 `memory-bank/` 轮次即判红并给出逐件清单
    (纯文档轮也覆盖, 与 2026-10-03 认领链下沉同款)。
  - 5 词表单点在 `_common.DOC_STATUSES`(生成器与守卫 import 同源, 不手抄)。
- **守阵**: `tests/test_docs_forms.py` —— `test_docs_index_rejects_unknown_status`(fail-fast) /
  `test_docs_index_indexes_valid_status`(防过严) / `test_doc_map_flags_unknown_status`(闸门侧) /
  `test_status_vocabulary_is_single_point`(单点)。
