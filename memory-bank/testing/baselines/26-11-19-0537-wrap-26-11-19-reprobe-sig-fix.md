# 6477 passed + 6 skipped —— reprobe 去重签名去 _winTop 修复批收尾基线(issue 26-11-19-0258 修复 + 守阵新增 _winTop 断言)

> 摘要: reprobe 去重签名去 _winTop 修复批收尾基线(issue 26-11-19-0258 修复 + 守阵新增 _winTop 断言)
> 基线时间: 2026-11-19 05:37

## 验收数字

实测树: 7d88fee1(远端 develop 同步后) + 本批未提交改动。`commands run test.full` 实测(2026-11-19 05:4x, 168.8s):

```
TOTAL                                                28896     44  10314     61    99%
6477 passed, 6 skipped, 6 warnings in 166.26s (0:02:46)
```

e2e 侧(本轮手工面, 数字随轮即弃不建档): perf A/B 600 档 off 侧 gBCR prism 34 / atlas 35(修前 34/68, 2 passed); 相邻守阵六 spec 72 passed / 11 skipped / 0 failed。

## 本改动面

- `src/auto_qb/webui/static/shared/columns_grid.js`: `_rowWindow` reprobe 去重签名去掉 `_winTop[kind]` 项(假失配根因, 注释含机理)。
- `tests/test_webui_static_dom_page_layout.py`: `test_frontend_outgoing_rowh_reprobe_guard` 新增「签名不含 _winTop」断言(修前该守阵因签名变单行误挂过一次, 已恢复多行调用形态并钉住新面)。
- KB: issue 26-11-19-0258 翻 Done + 根因/修法回写; issue 26-11-19-0258-test-e2e-perf-3000-first-visit-fingerprint-drift 补 600 档证据; 新入池 26-11-19-0534-test-e2e-relocate-carry-600-red; 新坑档 pitfalls/web-ui/rowwin-reprobe-sig-top-drift.md。
