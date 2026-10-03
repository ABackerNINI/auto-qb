# WEBUI qB 流量图轮询闪烁修复 (待用户提交)

> 摘要: 用户报「WEBUI qb流量图每隔几秒闪烁一次」—— 上一切片(26-10-04-0405)真机走查的发现。
> 根因 = 低频轮询续拉对用户可见, 两处叠加: ①`_qbLoad` 一开始亮 `qbCurLoading` -> 模板
> `v-if="qbCurLoading"` 把整块图换成「正在加载流量数据…」空态再换回(图 DOM 每个轮询周期拆装一次);
> ②数据落袋后 `_qbChartBuild` 走 destroy + `new uPlot` 整图重建, canvas 清屏一帧。
> 与坑档 [drawer-switch-flicker](../pitfalls/web-ui/drawer-switch-flicker.md) 两条同型(复发 +1 已记:
> 组件新写时对齐的是 drawer.js 竞态纪律, 没回头过渲染闪烁清单)。

> 最后活动: 2026-10-04 04:48

**修法(静默续拉)**: ①模板 loading 空态门改 `qbCurLoading && !qbCurPoints.length`(已有数据时
续拉不接管正文, loading 只在首载/无数据时显示; `qbCurLoading` 本体语义不变 —— 轮询 tick 在途
互斥判据不受影响); ②`_qbChartBuild` 加 setData 原地快路 —— 同一宿主上 uPlot 实例还活着
(`prev.root.isConnected && prev.root.parentElement === host`)只 `setData` 换数据 + 更新悬停锚,
完整重建仅首图/宿主被 v-if 拆后/换肤; ③换肤处理器相应改先 `_qbChartDestroy` 再重建(canvas 色
是建图时烘焙的令牌值, setData 快路不换色)。守阵 `test_frontend_qb_traffic_chart_wiring` 补三锚。

**验证**: test.full **2441 passed + 4 skipped / 99%** @ 718b96f4(合并远端跨组交叉检测 7 笔之后;
stash -> sync -> stash pop 合流无冲突), 基线切片 [26-10-04-0448](../testing/baselines/26-10-04-0448-webui-qb-chart-poll-flicker.md)。

**待办**: 用户真机走查(闪烁消失 / 换窗 24h<->30d / 换肤后图色正确)。
