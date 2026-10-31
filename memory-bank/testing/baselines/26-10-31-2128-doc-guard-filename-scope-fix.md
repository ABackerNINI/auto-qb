# 4303 passed + 10 skipped —— 新增面守卫圈面改文件名 stamp 前缀 + kb.new 命名不变量守卫 + RM 计划件头部修复

> 摘要: 新增面守卫圈面改文件名 stamp 前缀 + kb.new 命名不变量守卫 + RM 计划件头部修复
> 基线时间: 2026-10-31 21:28

## 验收数字

`commands run test.full` (2026-10-31 21:25, 143.06s): **4303 passed, 10 skipped**, 覆盖率 TOTAL 21806 stmts / 99%。定向三条先行 (`commands run test.one -- tests/test_memory_bank.py`): 圈面洞回归阵 + 冻结线豁免 + kb.new 建件守阵全绿。

## 本改动面

- `.agents/skills/memory-bank/scripts/check_doc_templates.py`: plan/report 扫描面圈定从「文件自身 doc-added meta」改为**文件名 stamp 前缀** (与 baseline/slice 同款) —— 堵「缺 doc-added 的手写新件整件逃逸」洞 (RM02-RM10 九件无状态计划事故, 豁免自噬); 模块 docstring 同步。
- `.agents/skills/memory-bank/scripts/new_doc.py`: 文件名派生后加族命名正则不变量守卫 (SLUG_RE 主闸已有, 此防建件端/守卫端正则失配漂移)。
- `tests/test_memory_bank.py`: 新增 `test_checker_catches_new_plan_missing_doc_added` (手写新 plan 缺 doc-added 必红); `test_checker_freeze_line_exempts_stock` docstring 与清单措辞随圈面判据更新。
- `memory-bank/plans/26-10-31-*plan-real-rm0*.html` ×9: RM02-RM10 排期计划回填 doc-type/doc-status=Done/doc-added/doc-updated + 删遗留 plan-slug/plan-stamp + 补可见状态行 + 文件名大写改小写; 引用点 9 处同步 (锚 issue 26-10-31-0641 等 5 个 issue 件 / manual-walkthrough / 3 个 real-baselines)。
- 坑档 ×2: `pitfalls/kb/handmade-doc-header-escape.md`、`pitfalls/git/windows-case-only-rename.md`。
- `.commands/my-commit-flow/.my-commit-flow.toml`: 闸门 note 补 26-10-31 修复注记。
- 守卫检查面 323 → 332 件 (9 件修复后进入检查面全绿); `kb.check` 全绿。
