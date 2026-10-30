# 4185 passed + 2 skipped(根) —— kb.nav 搜索框清词按钮与 / 快捷键后全量

> 摘要: kb.nav 搜索框加清词按钮(有词显形, syncGclear 单点同步)+ placeholder 移除「(Esc 清空)」+ `/` 快捷键聚焦搜索框(输入态 / IME / 修饰键不劫); 新守阵两条, test.full 全绿
> 基线时间: 2026-10-31 00:29

## 验收数字

`commands run test.full`(pytest `-n 4 --cov=src --cov-branch --cov-fail-under=99`(pytest.ini addopts); 2026-10-31 实测, 全量 114.63s, 建档 00:29):

```
  TOTAL                                                21144     96   7160    100    99%
  4185 passed, 2 skipped in 114.63s (0:01:54)
```

- 汇总行: **4185 passed + 2 skipped(根)**; 覆盖率门槛 99% 通过(TOTAL 行 99%)。
- 逐条口径注记: 本轮新增守阵 2 条(test_gsearch_clear_button / test_slash_focuses_search),
  均为壳文本结构断言, 无网络 / 子进程副作用。

## 本改动面

- `.agents/skills/memory-bank/scripts/nav_page.html`: ①`#gq` 加清词按钮 `#gclear`(内联 SVG ×,
  有词才显形, 显隐走 `syncGclear()` 单点 —— input / Esc / 按钮点击 / boot 回填四处共用), 点击清词
  后焦点还给输入框; ②placeholder 移除「(Esc 清空)」(只涉 gq, 控制台 `#cq` 不动); ③`/` 快捷键
  `slashFocus` 命名函数注册 document 级 keydown, 非输入态聚焦 `#gq` 并挡默认行为(IME / 修饰键 /
  输入态不劫; 调用点不含 Esc 关键词, 不撞 Esc 单点守阵)。
- `tests/test_kb_nav.py`: 新增 `test_gsearch_clear_button` / `test_slash_focuses_search` 两条守阵,
  测试计划 docstring 同步两行。
