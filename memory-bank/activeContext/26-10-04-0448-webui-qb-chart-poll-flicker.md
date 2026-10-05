# WEBUI qB 流量图轮询期闪烁(两轮: 有图态 / 空态与错误态)

> 摘要: 用户报「WEBUI qb流量图每隔几秒闪烁一次」的两轮修复。第一轮(2026-10-04, 已提交 f019ed9c) =
> 静默续拉: loading 空态门在「无点」上(`qbCurLoading && !qbCurPoints.length`) + 同宿主 setData 原地
> 快路(不 destroy+new uPlot 清屏) + 换肤先销毁再重建 —— 覆盖「已有图」一态。第二轮(2026-10-05, 本轮) =
> 用户真机走查回报**空数据集下仍闪**(「暂无 qB 口径流量数据(程序运行期间无采样)」/「暂无该种子的
> qB 口径流量数据(从未有传输记录)」): 空态文案与错误文案也是既有状态, 「无点」判据把「空态」
> 「首载」混成了一个状态, 每个轮询周期仍被「正在加载流量数据…」顶掉一帧。
> 根因/判别/处置单点在坑档 [drawer-switch-flicker](../pitfalls/web-ui/drawer-switch-flicker.md) 复发 +1(第三次)。

> 最后活动: 2026-10-05 08:00

**本轮修法**: 判据改「本作用域**有无落袋结果**」—— `qbCurPending = qbCurLoading && !qbCurData && !qbCurError`
(空态响应落袋后 `data` 是非 null 对象, 只有出错才置 null; 错误态落袋后 `error` 非空), 模板 loading 空态
门从 `qbCurLoading && !qbCurPoints.length` 换到 `v-if="qbCurPending"`; 配套 `_qbLoad` **不再在发请求前清
error**, 改由**成功落袋**清除(在途期不动既有状态, 换目标期的旧文案由 FX-29 遮罩兜住)。

**改动面**: `shared/qb_traffic_chart.js`(qbCurPending 新判据 + `_qbLoad` 的 error 清除点后移 + 文件头
静默续拉段重写) · `shared/tpl/drawer.html`(loading 空态门 `v-if="qbCurPending"` + 注释) ·
`tests/test_web.py`(守阵四锚: 模板门 / 三合一判据 / `error` 清除只允许在 `await this.api(` 与
`this[def.data] = data;` 之后 / setData 原地快路; docstring 两处同步)。

**验证**: ①机检(Playwright + 真 `create_app` 桩, 空数据目录 / 恒 500 两场景, 逐 20ms 采抽屉正文文本):
修前空态↔loading 每 2s 翻一次(14s 内 11 次), 修后 **0 次**; 错误态修前 `boom`↔loading, 修后恒为错误文案。
②`commands run test.full` **2567 passed + 4 skipped / 99%**(15477 语句 / 162 未覆盖 / 5240 分支 /
136 partial, 与上一条基线五组数字完全相同), 基线切片
[26-10-05-0800](../testing/baselines/26-10-05-0800-webui-qb-chart-empty-flicker.md)。

**待办**: 用户真机走查(空数据集下空态不再闪 / 有图态、换窗 24h<->30d、换肤后图色仍正常)。
