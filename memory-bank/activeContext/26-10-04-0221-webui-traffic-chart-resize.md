# uPlot 流量图 resize 不自适应 — issue 26-10-04-0134 修复置 Done

> 摘要: 认领修复三挂点 qB 流量图(全局弹层/单种抽屉流量页签/分组流量弹层)建图宽度一次取定、
> 窗口 resize 后画布不重算的问题, 按建议修法(ResizeObserver)一处修三处受益。
> 最后活动: 2026-10-04 02:21

## 已完成 (2026-10-04)

- **复验**: 基线 HEAD 4805f5f5 仍复现 —— `_qbChartBuild` 里 `host.clientWidth` 建图时一次取定,
  全文件无 `ResizeObserver`/`resize` 监听, 与 issue 建议一致。
- **修复**: `qb_traffic_chart.js` `_qbChartBuild` 建图后对宿主挂 `ResizeObserver`, 宽度变化即
  `u.setSize({width, height:300})` 重画并同步 `_qbChartWs`(悬停 flip 折算跟着对); 回调带双守卫
  (图已被重建/销毁即自摘 + 宿主脱离 DOM 或 0 宽不 setSize —— 后者覆盖 torrent 切页签只停轮询
  不销毁图、挂点 DOM 随 v-if 拆除的路径); `_qbChartDestroy` 断开 observer。宿主
  `.qb-chart-host` 为 `width:100%` 不依赖图内容, 观察不成环。文件头范式文档同步补一行。
- **守阵**: `tests/test_web.py::test_frontend_qb_traffic_chart_wiring` 并入四条断言
  (宿主 ResizeObserver 存在 / resize 回调走 uPlot setSize / `_qbChartDestroy` disconnect /
  自摘与 0 宽守卫), 文件头测试计划同步登记。
- **回写**: issue 置 Done(meta + 封面徽标 + 状态日志, 03 节补复验/实际修法/验证), issues/_index.md
  经 `kb.index` 重生成(20 生成物; 首跑 test.full 曾因索引漂移红 `test_gen_all_check_is_green`,
  重建后绿)。
- 收尾: 基线切片 [baselines/26-10-04-0221](../testing/baselines/26-10-04-0221-webui-traffic-chart-resize-done.md)
  (2419 passed + 3 skipped / 99% @ 4805f5f5; 本单 +0 用例, 守阵并入既有用例)。
  不满足立档阈值(单轮单 issue, 1 源文件 + 1 测试文件); 无新坑可记。

## 状态

任务完结, 改动留在工作树等用户显式「提交」指令(本轮未获提交授权)。
