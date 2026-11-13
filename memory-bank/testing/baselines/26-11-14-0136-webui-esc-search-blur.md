# 6085 passed, 19 skipped, 覆盖 99%(27113 语句缺 219) —— test.full 基线切片: webui Esc 退焦档批次

> 摘要: test.full 基线切片: webui Esc 退焦档批次
> 基线时间: 2026-11-14 01:36

## 验收数字

`commands run test.full` 实测(2026-11-14 01:34, 109.93s):

```text
TOTAL                                                27113    219   9480     89    99%
6085 passed, 19 skipped in 109.93s (0:01:49)
```

较上一基线 26-11-14-0005(6084 passed + 19 skipped) +1: 新守阵 `test_esc_chain_search_input_blur`。

## 本改动面

- `src/auto_qb/webui/static/shared/lifecycle.js`: Esc 退栈链补「退出搜索框聚焦」档(浮层名单走空后焦点在顶栏搜索框 -> `inputEl.blur()`; IME 双保险 `isComposing`/keyCode 229; 排在清选择兜底之前; 仅钉死 `inputEl === this.$refs.searchInput` 不清词) + 链头摘要注释同步。
- `src/auto_qb/webui/static/shared/shortcuts.js`: clear-esc 固定键 label 改「退出搜索框 / 清除选择 / 逐层退栈 / 清筛选」。
- `tests/test_web_shortcuts_engine.py`: 新守阵 `test_esc_chain_search_input_blur`(钉分支序/仅搜索框/IME 门/档内无 clearSearch; 排序锚点钉清选择兜底长特征串防将来误红) + docstring 测试计划同步。
- `e2e/views.spec.mjs`: 新真机回归 @fast(焦点归还 / 搜索词保留 / Digit2 键位复活)。

