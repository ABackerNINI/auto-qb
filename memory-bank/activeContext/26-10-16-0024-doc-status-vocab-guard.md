# 26-10-16-0024-doc-status-vocab-guard — doc-status 词表检查提前到根因(生成器 fail-fast + 闸门同源)

> 摘要: 另一会话报告新坑 —— 计划首版写了 `doc-status: Draft`(不在 5 词表), `kb.index` **静默漏收**该件(仍打印「已生成 21 个生成物」、零警告), `kb.check` / `kb.docmap --check` / `doc.links` 全绿, 只有 `test.full` 的 `test_status_vocabulary` 才红。用户指令「拟定将 status_vocabulary 检查提前, 分析加到哪个环节合适」→ 只读分析定案后「直接实施, 按推荐+B 补强」。落地: ①根因侧生成器 fail-fast(`gen_docs_index.build` 抛 `StatusVocabularyError`, `kb.index`/`kb.check` 响亮报错); ②闸门侧 `gen_doc_map --check` 加同源词表校验(纯文档轮提交即拦); ③5 词表单点化到 `_common.DOC_STATUSES`。细节单点在档案 `tasks/26-10-16-memory-bank-doc-status-vocab-guard.md`。
> 最后活动: 2026-10-16 00:24
> 状态: Done(改动随本专题入库)

**Refs:** memory-bank/tasks/26-10-16-memory-bank-doc-status-vocab-guard.md

## 本轮落点(细节单点在档案, 此处只留入口)

- 定案「加到哪个环节」: 落**生成器**(根因), 而非再加一条独立检查 —— 生成器是唯一"丢信息"处, fail-fast 后 kb.index / kb.check / 提交闸门 / pytest / sync 自动化解全部自动继承, 零新增接线。
- 改动面 5 源文件: `_common.py`(单点 + 异常类) · `gen_docs_index.py`(fail-fast + 入口接住) · `gen_all.py`(kb.index/kb.check 入口接住) · `gen_doc_map.py`(闸门侧校验) · `tests/test_docs_forms.py`(4 条守阵 + 单点导入)。
- 坑档 `pitfalls/kb/doc-status-meta.md` 处置段改写(记录机械守卫); 约定 `conventions/doc-forms.md` 状态词/索引节补单点与 fail-fast。

## 下一步 / 移交

- 无待办; 若将来 5 词表要增删词, 只改 `_common.DOC_STATUSES` 一处(生成器/闸门/守卫同源)。
- 闸门状态: 见 `commands run kb.baseline` 最新切片; kb.check / kb.docmap --check / doc.links 全绿; kb.index 已重建。
