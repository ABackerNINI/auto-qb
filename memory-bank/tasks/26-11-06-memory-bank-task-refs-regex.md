# 26-11-06-memory-bank-task-refs-regex — TASK_REFS_RE 空行跨行捕获修复

**Status:** Done
**Added:** 2026-11-06
**Updated:** 2026-11-06
**Summary:** issue 26-11-06-0415 已修: TASK_REFS_RE 只吃同行空白, 空 Refs 行视为未声明; 五个 md 模板去空 Refs 行, 守阵用例落地
**Topics:** memory-bank-task-refs-regex
**Refs:** memory-bank/issues/26-11-06-0415-bug-kb-refs-regex-blank-line.html, memory-bank/testing/baselines/26-11-06-0446-memory-bank-task-refs-regex.md

## 本篇只回答

issue 26-11-06-0415 的认领修复:md 档案留空 `**Refs:**` 行时,`gen_doc_map.py` 的 `TASK_REFS_RE` 用 `\s*` 跨行把下一行标题吞成 ref,认领链机检误红;本档案记录正则修复 + 模板去空行 + 守阵用例三步。

## 原始请求

1. 用户:「认领并修复 memory-bank/issues/26-11-06-0415-bug-kb-refs-regex-blank-line.html」

## 思考过程与决策

- 复验通过(2026-11-06):对含空 `**Refs:**` 行 + 后随 `## 原始请求` 的文本跑正则,`group(1)` 捕获到 `'## 原始请求'`——与 issue 证据一致。
- 修法采纳 issue 建议的 ①+② 同做:①正则 `\s*` 改 `[^\S\n]*`(只吃同行空白,空行后无捕获 → 视为未声明);②模板(task/baseline)不再输出空 `**Refs:**` 行,与存量惯例(不声明就整行不写)一致。
- `md_set_refs`(`_common.py:682`)已有插入锚点链(有 `**Topics:**` → 其后插),模板去掉占位行后插行路径仍在,安全;其 docstring「模板自带空 placeholder」的表述随本次改动同步修正。
- 平台细节:`[^\S\n]` 仍匹配 `\r`,CRLF 场景行为不变;`read_text` 通用换行下亦无差。

## 实现计划

1. `gen_doc_map.py` `TASK_REFS_RE`:`\s*` → `[^\S\n]*`,注释记一句为什么。
2. 五个 md 模板 `.agents/skills/memory-bank/templates/{task,baseline,progress,slice,pitfall}.md` 删空 `**Refs:**` 行。
3. `tests/test_docs_forms.py` 补守阵:空 Refs 行不产生 ref;带值行仍正常取值。
4. `test.full` 全绿后回填 issue 修复后补充、置 Done、重建索引。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 复验锚点 + 立档 + 双向补链 | Done(2026-11-06) |
| 2 | 正则修复 + 模板去空行 + 守阵用例 | Done(2026-11-06) |
| 3 | test.full 全绿 + issue 置 Done + kb.index | Done(2026-11-06) |

## 进度日志

### R0 · 立档 (2026-11-06)

认领(issue 置 In Progress)、复验仍复现、立档并双向补链;修法按 issue 建议 ①+②。

### R1 · 修复完成 (2026-11-06)

正则 `\s*`→`[^\S\n]*`、五个 md 模板(task/baseline/progress/slice/pitfall)删空 Refs 行、`md_set_refs` docstring 同步、守阵 `test_empty_refs_line_is_not_a_ref` 落地(五模板防护);issue 置 Done 并回填修复后补充;全量全绿(基线切片 26-11-06-0446)。

### R2 · 收口评审 (2026-11-06)

review: blocker 清零, 修 4, 入池 0(全能档 145 行, 单只读子代理)。4 条 minor/nit 全为文档面一致性(修复后补充/档案 R1 两模板→五模板口径、新切片残留空 Refs 行、守阵扩五模板防护), 当场全修; 核心修复与守阵有效性经 reviewer 实测确认(旧正则下新测试真红)。

- 2026-11-06 04:47 issue 26-11-06-0415 修复收口: TASK_REFS_RE 同行空白修复+模板去空 Refs 行+守阵用例, 全量全绿(基线 26-11-06-0446)
