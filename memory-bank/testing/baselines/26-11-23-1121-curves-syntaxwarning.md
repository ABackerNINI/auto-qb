# 7025P/6S 覆盖率 99% —— curves.py docstring raw 前缀修复后基线

> 摘要: issue 26-11-22-0604 修复批后基线 —— period_sort_key docstring 加 r 前缀消除 `\d` 存量 SyntaxWarning, 纯字面修改零行为变化, 用例数不变
> 基线时间: 2026-11-23 11:21

## 验收数字

`commands run test.full` 实测:

```
TOTAL                                                31412    108  11190     93    99%
7025 passed, 6 skipped, 1 warning in 124.16s (0:02:04)
```

## 本改动面

- `src/auto_qb/core/curves.py`: `period_sort_key` docstring 起始 `"""` → `r"""`, 一行覆盖 docstring 内两处 `\d`; `__doc__` 值逐字节不变, 函数运行时零行为变化。第 40/83 行正则字面量本就是 raw string, 未动。
- `memory-bank/issues/26-11-22-0604-refactor-curves-syntaxwarning-invalid-escape.html`: 修复后补充落 §04, 状态 Open → Done。
- 相对 26-11-23-0131(7025P/6S): 用例数与覆盖率全不变 —— 纯 docstring 语法修复, 无新增守阵。
- 唯一目标验证: `python -W error::SyntaxWarning py_compile` 由原报错转通过; 全库逐文件 `compile()` 捕获 SyntaxWarning 命中 0。全量 1 条残留 warning 是 `test_repo_text_subprocess_calls_pin_utf8` 故意构造的 `<unknown>:28` 的 `\P`, 与本 issue 无关(范围外未动)。
- 真机准入: 纯 docstring 字面修复, 无运行时/真机可验面(零行为变化), 免真机轨。
