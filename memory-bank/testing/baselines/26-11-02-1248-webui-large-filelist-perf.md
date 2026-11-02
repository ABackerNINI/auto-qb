# 4837 passed + 10 skipped(根), 覆盖率 99.00%(22521 stmts/152 miss, 分支 7726/135 miss) —— 首访估算开窗阈值二轮调优(1000→200, issue 26-11-02-0902)后全量

> 摘要: 首访估算开窗阈值二轮调优(1000→200, issue 26-11-02-0902)后全量
> 基线时间: 2026-11-02 12:48
**Refs:** memory-bank/tasks/26-11-02-webui-large-filelist-perf.md, memory-bank/issues/26-11-02-0902-perf-webui-first-visit-rowh-measure.html

## 验收数字

`commands run test.full` 实测(2026-11-02 12:48, 工作区未入库态):

- 汇总行: `4837 passed, 10 skipped, 3 warnings in 239.14s (0:03:59)`(test.quick 同树先跑: 4837 passed, 10 skipped in 123.71s)
- 覆盖率: TOTAL 22521 stmts / 152 miss, 分支 7726/135 miss, **99%**(门槛 99% 达标)
- 零 failed

e2e 数字(同一树, 不进本切片汇总行, 均零 failed):

- `e2e/perf.spec.mjs` 默认 300 档(估算开窗档): 8 passed / 4 skipped(30s 内; 指纹用例双皮肤实跑通过)
- `E2E_TORRENTS=199`(边界下档, off 精确口径): 6 passed / 6 skipped(指纹用例正确 skip)
- `E2E_TORRENTS=200`(边界上档, 估算开窗): 8 passed / 4 skipped(指纹用例双皮肤实跑通过)
- 负向验证: 门控临时恒 off(强制精确冷启动)→ 指纹用例 2 failed(gBR 325/行数 300, 与拐点曲线预测一致), 还原后回绿; 单测边界断言同法验证(恒 off → 恰红 n=200 两条, 还原回绿)

## 本改动面

- `webui/static/shared/app.js` — `ROW_WIN_EST_MIN` 1000→200(与 `ROW_WIN_MIN` 合并, 精确冷启动档消失); 注释更新定值依据(拐点曲线 150 行 215ms / 200 行 334ms, 250ms 线)
- `webui/static/shared/columns.js` — `_rowWindow` 首访门控 `n < ROW_WIN_EST_MIN` 口径随阈值; 注释去「千级」措辞
- `e2e/perf.spec.mjs` — 镜像常量 200; 新增「首访路径指纹」用例(gBR<150, 空档1: 防误退回精确冷启动); 「滚动到底」估算档判据改按比例禁塌陷(|Δ|<before×25%; 原 Directions「只会增长」假设被 300 档实测 -1296px 证伪); 占位总高/滚到底分档注释更新(严格口径仅 <200 off 档可达)
- `tests/test_webui_static_dom_page.py` — node 探针电池加边界两断言(n=199 off / n=200 估算开窗, 空档2) + `ROW_WIN_EST_MIN=200` + fallback 电池未量齐期望改估算开窗; 头部测试计划同步
- 坑档 `pitfalls/web-ui/est-cold-start-vs-absolute-threshold.md` — 分档口径与滚到底方向不定教训回写(复发 +1)
