# 基线 · 2419 passed + 3 skipped / 99% —— uPlot 流量图 resize 自适应修复轮(issue 26-10-04-0134)

> 摘要: 单 issue 修复轮: 三处 qB 流量图(全局弹层/单种抽屉流量页签/分组流量弹层)建图宽度一次取定,
> 浏览器窗口 resize 后画布不重算。修法 = 建图后对宿主挂 `ResizeObserver`, 宽度变化即
> `u.setSize` 重画并同步 `_qbChartWs`(悬停 flip 同步对); 回调带自摘/0 宽双守卫, `_qbChartDestroy`
> 断开 observer。守阵断言并入既有 `test_frontend_qb_traffic_chart_wiring`(ResizeObserver/setSize/
> destroy disconnect/自摘守卫四条)。
> 基线时间: 2026-10-04 02:21, develop @ 4805f5f5(工作区含本轮修复与回写件); 提交前同步合流
> 远端 d323d261 后复测同数(2419 passed + 3 skipped / 99%, 29.6s, src/ 零变化)。
> Linux 侧: 待补(仅 Windows 侧重测, 见 baseline.md 常驻警告)。

TOTAL **2419 passed + 3 skipped / 99%**(14,395 语句 / 131 未覆盖 / 4,810 分支 / 104 partial,
test.full 26.6s, rc=0)。
相对上一记录点(26-10-04-0115 qb-traffic-p6: 2418 passed + 3 skipped / 99%): **本单 +0 用例**
(守阵断言并入既有用例, 不新增 test 函数); passed 2418→2419 的 +1 来自 4805f5f5
(keys-update CRLF 修复, 其提交时自测即 2419), 非本单。语句/分支增长同源, 均非本单。
