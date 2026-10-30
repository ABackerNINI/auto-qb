# 4183 passed + 10 skipped —— kb.nav 多选验收返工(Shift 防文字选中)后全量

> 摘要: kb.nav 多选验收返工第三处 —— Shift 连选挡浏览器原生文字选中(mousedown 期 preventDefault + click 分支双保险, 普通点击不挡); 守阵断言同步扩, test.full 全绿
> 基线时间: 2026-10-31 03:33

## 验收数字

`commands run test.full`(pytest `-n 4 --cov=src --cov-branch --cov-fail-under=99`(pytest.ini addopts); 2026-10-31 实测, 全量 65.29s, 建档 03:33):

```
  TOTAL                                                20891     114   7160    105    99%
  4183 passed, 10 skipped in 65.29s (0:01:05)
```

- 汇总行: **4183 passed + 10 skipped(Windows)**; 覆盖率门槛 99% 通过(TOTAL 行 99%)。
- 逐条口径注记: 守阵条数不变, test_shell_has_multiselect_state_and_gestures 扩三处断言
  (aRows/pinZone 两容器的 mousedown shift 守卫在位 + 两处 click shift 分支含 preventDefault);
  语句数 / miss 与 26-10-31-0318 逐位相同(改动面仍在壳 HTML 与守阵)。
- 真机冒烟(Playwright 无头, file:// 静态件): 25 项全过 —— 原轮全项 + 新增一条
  (Shift 连选后 `window.getSelection()` 必须为空串, 实测 ""); 其余断言不受 mousedown
  preventDefault 影响(Ctrl/Shift/普通单击路径全数复验)。

## 本改动面

- `.agents/skills/memory-bank/scripts/nav_page.html`: ①wire() 给 #aRows / #pinZone 挂 mousedown
  守卫(`if (e.shiftKey) e.preventDefault()` —— 浏览器在 mousedown 期扩展原生选区, click 挡已晚);
  ②两处 click 的 shift 分支补 `e.preventDefault()`(双保险)。普通点击路径零改动。
- `tests/test_kb_nav.py`: test_shell_has_multiselect_state_and_gestures 扩三处断言 + docstring 同步。
