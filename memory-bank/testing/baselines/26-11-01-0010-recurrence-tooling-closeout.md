# 4339 passed + 2 skipped(根) —— 堆3四件机械化收尾基线 (e2e自检/写盘守卫/doc-refs/ui-map)

> 摘要: 堆3四件机械化收尾基线 (e2e自检/写盘守卫/doc-refs/ui-map)
> 基线时间: 2026-11-01 00:10
**Refs:** memory-bank/tasks/26-10-31-memory-bank-recurrence-tooling.md

## 验收数字

- TOTAL: 4339 passed, 2 skipped (182.73s, 0:03:02)
- 覆盖率 TOTAL: 21812 语句 / 145 miss / 7400 branch / 122 partial / **99%** (门槛 99% 达标)
- 口径: `commands run test.full` 实测 (2026-11-01 00:05, 本 clone, -n 8 并行); 2 skipped 与上基线同源 (跳检场景类, 非本轮引入)

## 本改动面

- 新增: `scripts/e2e_selfcheck.py` (e2e 环境自检) · `scripts/ui_content_map.py` (聚合内容映射) ·
  `.agents/skills/memory-bank/scripts/set_doc_refs.py` (kb.ref 认领链回填) ·
  `tests/test_kb_writeform.py` (写盘形态守卫 4 用例) · `tests/test_kb_docrefs_tools.py` (doc-refs 机械化 8 用例)
- 挂接: `.commands/dev/config.toml` (dev.e2e run 首条 + dev.e2e-check + dev.ui-map) · `.commands/kb/config.toml` (kb.ref)
- 机械化: memory-bank skill 模板 7 族补 doc-refs/**Refs:** 空占位 · `_common.md_set_refs` 空值占位原位并值 ·
  `gen_doc_map --check` 增重复声明检测
- 存量收敛: 3 件重复声明 (第二处均为首处子集) · tasks/26-10-13 档案头部 5 裸 CR ·
  两条被塌缩声明掩住的单向链补齐反向声明 (基线外迁件走 attachments 解析)
- 测试期望更新: test_memory_bank 的 D4 用例「无 --refs ⇒ 无 doc-refs meta」改为「空值占位 meta」
  (契约随本专题变更: 建件即带占位, 回填原位改值)
