# HTML 制品的 `doc-status` 取值: 不在 5 词表 ⇒ 索引**静默漏收**

> 摘要: `plans/` `reports/` 的 `<meta name="doc-status">` 不在 5 词表(`Open`/`In Progress`/`Done`/`Dropped`/`Superseded`)时, `kb.index` 会**静默跳过该件** —— 仍打印「已生成 N 个生成物」、零警告, 且 `kb.check` / `kb.docmap --check` / `doc.links` **全绿**; 只有 `test.full`(`test_docs_forms.py::test_status_vocabulary`)才红。新件漏收最典型的诱因是写了「语义上像状态、但不在表里」的词(如 `Draft`)。
> 触发: 新建计划/报告, doc-status, 状态词, 索引漏收, kb.index 已生成但件不在索引, Draft, test_status_vocabulary

## 判别

- **触发**: 新建 `plans/*.html` 或 `reports/*.html`, 手写 `<meta name="doc-status">`。
- **判别**: 2026-10-16 实测 —— 新计划写了 `doc-status: Draft`(语义上是"待实施", 不在 5 词表),
  于是:
  - `kb.index` 报 `[ok] 已生成 21 个生成物`, **但 `plans/_index.md` 里没有这一条**(静默漏收);
  - `kb.docmap --check` 报「主键纪律 OK: 680 份文档」并**把这个件计入文档数**(它读的是 `doc-topic`, 不是
    `doc-status`), 认领链也 OK ⇒ **看不出异常**;
  - `test_docs_index_is_regenerated` 也**不红** —— 生成器跳过该件, 索引 == 生成结果, 自洽;
  - 唯一红的闸门是 `tests/test_docs_forms.py::test_status_vocabulary`(它直接校验 `doc-status` ∈ 5 词表)。
  对照: md 档案的 `**Status:**` 是 4 词表(`In Progress`/`Open`/`Done`/`Dropped`, 见
  [tasks-archive.md](tasks-archive.md)), **两张表不同**, 别互相套用。
- **处置**: 计划待拍板/待实施一律用 **`Open`**(实施中 = `In Progress`; report 恒 `Done`); 改完**重跑**
  `commands run kb.index`, 并**当场确认件已进索引**(`grep <时间戳前缀> memory-bank/plans/_index.md`)——
  "已生成 N 个生成物"这句**不能**当作收录成功的证据。防复发: 新建 HTML 制品后把
  `doc-status` 与本条 5 词表逐个对照, 再跑一次 `test.full`(别只跑 `kb.check`, 它查不到这一族)。
