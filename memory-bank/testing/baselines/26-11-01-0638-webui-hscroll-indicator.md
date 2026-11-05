# 4370 passed + 2 skipped —— 主表原生横条隐藏 + 底部横滚指示条首个全量回归快照

> 摘要: 计划 26-11-01-0553 的横滚指示条收尾全量回归快照 —— 主表原生横条改共用层隐藏 + 底部指示条后, 静态守阵与 e2e 行为守阵双落, 全量 pytest 无红用例
> 基线时间: 2026-11-01 06:38
**Refs:** memory-bank/plans/26-11-01-0553-plan-webui-hscroll-indicator.html, memory-bank/pitfalls/web-ui/hscroll-indicator.md

## 验收数字

`commands run test.full` (153.31s, 2026-11-01 实测):

```text
4370 passed, 2 skipped (共 4372 条) in 153.31s
coverage: 99% (21840 stmts / 144 miss)
```

- 口径见 [baseline.md](../baseline.md)。

## 本改动面

- `src/auto_qb/webui/static/shared/hscroll.css`（新建）+ 三皮肤 `src/auto_qb/webui/static/{atlas,console,prism}/index.html` + `tests/test_webui_static_skins.py`（commit 84946dd0）: 新增三皮肤共用层 —— 原生横条隐藏 + 底部横滚指示条外观, 三处 `index.html` 各挂一条 link 引用; 静态守阵的 shell 行数 cap 218→220 容下新增两行。
- `src/auto_qb/webui/static/shared/columns.js`（commit e4aeeab4）: 接指示条逻辑 +200 行 —— 11 个 `_hscroll*` 方法与模块级 `HSCROLL_IND` 状态, 覆盖热区召唤 / 拖动 / 点轨道 / 白名单挡抽屉面。
- `src/auto_qb/webui/static/shared/columns.js`（commit ef734485）: 监听挂错位置的返工 —— 文档级 `mousemove` 监听从惰性建 DOM 路径挪到 `_ensureHeadObserver()` 挂载即绑; 不修则从未横滚过的用户永远见不到指示条。
- `tests/test_webui_static_skins.py`（commit 96298985）: 新增 `test_frontend_hscroll_indicator_wiring` 9 条判据, 三次红绿双验钉住规则单点 / 挂载级联 / 接线三族静默故障。
- `e2e/hscroll-indicator.spec.mjs`（新建, commit b54e8630）: 10 用例真浏览器钉住三视图无条槽 / 可横滚 / 热区淡入 + 辅种表拖动同步 + 宽窗负例; 顺带发现 overlay 滚动条会让条槽断言成安慰剂。
