# 26-10-16-memory-bank-doc-status-vocab-guard — doc-status 词表检查提前到根因(生成器 fail-fast + 闸门同源)

**Status:** Done
**Added:** 2026-10-16
**Updated:** 2026-10-16
**Summary:** 另一会话报告: 计划首版 `doc-status: Draft`(不在 5 词表)被 `kb.index` **静默漏收**(仍打印「已生成 21 个生成物」、零警告), `kb.check` / `kb.docmap --check` / `doc.links` 全绿, 只有 `test.full` 的 `test_status_vocabulary` 才红。按「检查提前到哪个环节」分析后实施: 根因侧 `gen_docs_index` fail-fast(`StatusVocabularyError`, kb.index/kb.check 响亮报错) + 闸门侧 `gen_doc_map --check` 同源词表校验(纯文档轮即拦) + 5 词表单点化到 `_common.DOC_STATUSES`。
**Topics:** doc-status-vocab-guard
**Refs:** memory-bank/pitfalls/kb/doc-status-meta.md
## 原始请求

用户转述另一会话报告(2026-10-16 00:14): 计划首版写了 `doc-status: Draft` —— 不在 5 词表, 后果是 `kb.index` **静默漏收**该件(仍打印「已生成 21 个生成物」、零警告), `kb.check` / `kb.docmap --check` / `doc.links` 全部照绿, 只有 `test.full` 的 `test_status_vocabulary` 才红; 该会话已改 `Open`、重跑索引并写进 `pitfalls/kb/doc-status-meta.md`。用户指令:「拟定将 status_vocabulary 检查提前, 分析加到哪个环节合适」。分析定案后用户拍板:「直接实施, 按推荐+B 补强」。

## 思考过程与决策

- **只读分析(先)**: 定位静默漏收根因 —— `gen_docs_index.render()` 只按 5 词表逐个分区取件, 表外状态不落任何分区 ⇒ 被无声丢弃; `--check` 重算后再比磁盘, 两边都丢 ⇒ 自洽 ⇒ 绿。`kb.check` / 提交闸门 `gen_docs_index --check` / `test_docs_index_is_regenerated` 全是同一条自洽路径, 天然抓不到; `kb.docmap --check` 读 `doc-topic` 非 `doc-status`, `doc.links` 只查链接。
- **落点选型**: 四候选(生成器 fail-fast / `gen_doc_map --check` 下沉 / `kb.check` 新增 / 制件时模板)。定案**生成器为主**(根因处消除整类缺陷、零新增接线、最早环节), `gen_doc_map --check` 为 **B 补强**(复刻 2026-10-03 认领链从 pytest 下沉闸门的先例, 给提交闸门一条逐件清单的人话报错)。
- **单点化**: 5 词表原有两份副本(`gen_docs_index.STATUSES` 与 `test_docs_forms.STATUSES`, 顺序还不同), 提到 `_common.DOC_STATUSES`; `TERMINAL_STATUSES` 同步为 `_common.TERMINAL_DOC_STATUSES`。
- **异常类放 `_common`**: `StatusVocabularyError` 由 `gen_docs_index` 抛, `gen_docs_index` 与 `gen_all` 两个 CLI 入口都能 import 捕获 —— 覆盖 kb.index 与 kb.check 两条路径。
- **范围守恒**: 未动 tasks 的 4 词表(另一张表, 与本次无关); 未动 `nav_data.py`(无 doc-status 依赖)。
- **顺序保稳**: `DOC_STATUSES` 沿用 gen_docs_index 现有分区序(In Progress/Open/Done/Dropped/Superseded), 故 `_index.md` 分区不重排、生成内容逐字不变。

## 实现计划

A. `_common.py` 单点(5 词表 + 完结子集 + 异常类)→ B. `gen_docs_index` fail-fast + 入口接住 → C. `gen_all` 接住(kb.index/kb.check)→ D. `gen_doc_map --check` 同源校验 → E. `test_docs_forms` 4 条守阵 + 单点导入 → F. 验证(test.one / test.full / kb.check)+ 收尾回写。

## 子任务状态表

| # | 任务 | 状态 |
|---|---|---|
| A | `_common.py` 单点化 + `StatusVocabularyError` | Done |
| B | `gen_docs_index` fail-fast + main 干净报错 | Done |
| C | `gen_all` 接住异常(kb.index/kb.check) | Done |
| D | `gen_doc_map --check` 词表校验(B 补强) | Done |
| E | `test_docs_forms` 守阵同步 | Done |
| F | 全量验证 + 收尾回写(坑档/约定/切片/基线) | Done |

## 进度日志

- 2026-10-16 00:14 — 只读分析轮: 开工同步 `de7dcafb→b17c671d`; 摸清四段流水线与静默漏收根因; 出「环节对比表 + 推荐(A 为主 / B 补强 / 单点化配套)」。
- 2026-10-16 00:19 — 实施轮开工同步 `已同步 b17c671d`; 落 A–E: `_common.py` 加 `DOC_STATUSES`/`TERMINAL_DOC_STATUSES`/`StatusVocabularyError`; `gen_docs_index.build()` 聚合两份目录表外值并抛异常、`main()` 捕获后 rc=1; `gen_all.main()` 捕获同一异常(kb.index/kb.check 两条入口); `gen_doc_map.check_status_vocabulary()` 挂 `--check`; `test_docs_forms` 改 import 单点 + 新增 4 条守阵。
- 2026-10-16 00:23 — 验证: `test.one tests/test_docs_forms.py tests/test_memory_bank.py` 全绿; 当前库 `gen_docs_index --check` / `gen_all --check` / `gen_doc_map --check` 全绿(表外值在真库不存在, 未误拦); 临时目录实测表外值 fail-fast 与 docmap 校验退码 1。
- 2026-10-16 00:26 — 收尾: 全量数字见基线切片(单点, `commands run kb.baseline`); 回写坑档 `pitfalls/kb/doc-status-meta.md` 处置段与 `conventions/doc-forms.md` 状态词/索引节; kb.check / kb.docmap --check / doc.links 全绿; kb.index 已重建。
