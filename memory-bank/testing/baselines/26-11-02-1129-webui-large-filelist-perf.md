# 4837 passed + 10 skipped(根), 覆盖率 99.00%(22521 stmts/152 miss, 分支 7726/135 miss) —— WEBUI 首访量齐修复(issue 26-11-02-0902)后全量

> 摘要: WEBUI 首访量齐修复(issue 26-11-02-0902)后全量
> 基线时间: 2026-11-02 11:29
**Refs:** memory-bank/tasks/26-11-02-webui-large-filelist-perf.md, memory-bank/issues/26-11-02-0902-perf-webui-first-visit-rowh-measure.html

## 验收数字

`commands run test.full` 实测(2026-11-02 11:29, 工作区未入库态):

- 汇总行: `4837 passed, 10 skipped, 3 warnings in 213.95s (0:03:33)`
- 覆盖率: TOTAL 22521 stmts / 152 miss, 分支 7726/135 miss, **99%**(门槛 99% 达标)
- 零 failed(本轮新增的 issue / 坑档 / 基线切片均已被认领链机检接受, 无「提交后自愈」红)

e2e 数字(同一树, 不进本切片汇总行): `e2e/perf.spec.mjs` 默认 300 档 6 passed / 4 skipped; `E2E_TORRENTS=3000` 档 10 passed; `E2E_TORRENTS=3000` `e2e/window-invalidation.spec.mjs` 6 passed。

## 本改动面

- `webui/static/shared/app.js` — `ROW_WIN_EST_MIN=1000`(千级及以上首访估算开窗阈值; 千级以下精确冷启动不变)
- `webui/static/shared/columns.js` — `_rowWindow` 冷启动门控按行数分档 + gap 兜底; `_measureRowH` 去掉一次性 sum; 新增 `_rowHAvgOf(kind)`(未量行按已实测行全局均值兜底)
- `webui/static/shared/lifecycle.js` — `_winMeasured` 注释口径(首访窗口行已实测, 千级以上随滚动补齐)
- `tests/test_webui_static_dom_page.py` — node 探针补 `ROW_WIN_EST_MIN` / `ROW_WIN_EST_H` 全局(电池自给)
- `e2e/perf.spec.mjs` — 占位总高与滚到底两条判据按 `TORRENTS >= ROW_WIN_EST_MIN` 分档(千级档: 占位粗界 0.5~1.5 倍 / 滚到底只禁塌陷)
