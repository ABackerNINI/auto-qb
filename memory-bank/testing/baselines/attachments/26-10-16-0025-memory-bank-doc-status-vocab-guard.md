# 3392 —— doc-status 词表检查提前到根因(生成器 fail-fast + 闸门同源)

> 摘要: 另一会话报告计划首版 `doc-status: Draft`(不在 5 词表)被 `kb.index` **静默漏收**、只有 `test.full` 才红。按「检查提前到哪个环节」分析后实施: `_common.py` 单点化 5 词表 + `StatusVocabularyError`; `gen_docs_index.build()` fail-fast(kb.index/kb.check 响亮报错); `gen_all` 接住异常; `gen_doc_map --check` 加同源词表校验(B 补强); `test_docs_forms` 加 4 条守阵并改 import 单点。本轮为**代码轮**(4 skill 脚本 + 1 测试文件)。
> 档案: memory-bank/tasks/26-10-16-memory-bank-doc-status-vocab-guard.md
> 基线时间: 2026-10-16 00:25

**Refs:** memory-bank/tasks/26-10-16-memory-bank-doc-status-vocab-guard.md, memory-bank/pitfalls/kb/doc-status-meta.md

## TOTAL

```
TOTAL                                               17337    182   5846    158    99%
3392 passed, 4 skipped in 125.19s (0:02:05)
```

- 语句 17337 / 未覆盖 182; 分支 5846 / partial 158; 覆盖率 **99%**(`commands run test.full` 实测, Windows 侧)。
- 本轮相对上一基线 +4 passed(新增 `test_docs_forms.py` 4 条状态词表守阵); 语句/分支/覆盖率与上基线持平 —— 逐位差值不在此抄(要看差值 `commands run kb.baseline -n 2` 现列)。
- Linux(WSL) 侧未重测 —— 本轮无平台相关改动。
