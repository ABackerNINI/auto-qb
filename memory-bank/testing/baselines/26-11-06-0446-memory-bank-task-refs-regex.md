# 5465 passed + 2 skipped in 161.58s (TOTAL 24538 stmts, 99% cover; issue 26-11-06-0415 修复收口) —— TASK_REFS_RE 空行跨行捕获修复全量基线

> 摘要: TASK_REFS_RE 空行跨行捕获修复收口
> 基线时间: 2026-11-06 04:46
**Refs:** memory-bank/tasks/26-11-06-memory-bank-task-refs-regex.md

## 验收数字

- 汇总行: **5465 passed + 2 skipped** in 161.58s(0:02:41, TMPDIR 由 tests/_tmp_bootstrap.py 自举)。
- 覆盖率 TOTAL 表末行: **TOTAL 24538 stmts / 57 miss / 8396 branch / 36 partial / 99%**,Required 99.5% reached, Total coverage: 99.71%。
- 口径注记: 相对上基线(26-11-06-0427, 5462)净增 3 = 本轮 +1 守阵用例(test_empty_refs_line_is_not_a_ref)+ 会话开工同步合流面; 全绿, 副作用越界 0。
- 差值对比: `commands run kb.baseline -n 2`。

## 本改动面

- issue 26-11-06-0415 修复(认领档案 `tasks/26-11-06-memory-bank-task-refs-regex.md`):
  - `.agents/skills/memory-bank/scripts/gen_doc_map.py`: `TASK_REFS_RE` 的 `\s*` → `[^\S\n]*`(只吃同行空白, 空 Refs 行视为未声明, 不再吞下一行标题);
  - `.agents/skills/memory-bank/templates/task.md` / `baseline.md`: 删空 `**Refs:**` 行(与存量惯例一致);
  - `.agents/skills/memory-bank/scripts/_common.py`: `md_set_refs` docstring 过时表述同步(模板已不输出空 placeholder);
  - `tests/test_docs_forms.py`: 新增 `test_empty_refs_line_is_not_a_ref`(空行不吞下一行 / 带值行含 CRLF 正常取值 / 模板无空 Refs 行)+ 测试计划清单同步。
