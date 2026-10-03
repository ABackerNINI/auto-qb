# WEBUI 流量页签单击换行遮罩挂死(已修)

> 摘要: 用户报「WEBUI qB 流量图切换时一直显示加载中, 需关闭详情抽屉重新打开才正常; 双击切换正常」。
> 根因 = FX-29 软切换的落定登记只接了 drawer.js 四 fetcher, 流量页签的取数单点 `_qbLoad` 在
> qb_traffic_chart.js 跨模块不知协议 —— 待到集合 {"detail","traffic"} 永不清空, `drawer.switching`
> 遮罩挂死盖住图; 双击走 openTorrentDrawer 整体重置不经待到集合, 所以双击正常(现象自洽)。
> 修法: `_qbLoad` 落袋(成功/失败都算)且 scope==="torrent" 时 `_drawerDone("traffic", ctx, 0)`。
> 实测 test.full 2442 passed + 4 skipped / 99%(基线 26-10-04-0533)。

> 最后活动: 2026-10-04 05:33

## 进行中

- (无 —— 修复已完成并过全量, 等用户「提交」指令; 提交轮已 sync 合入远端 43c8f94a 并在新基线复跑)

## 已完成

- `qb_traffic_chart.js` `_qbLoad`: 落袋后(含 error 路径)且 `scope === "torrent"` 登记
  `_drawerDone("traffic", ctx, 0)`(seq=0 只走 hash 戳守卫, 与 def.stale 同源; `_drawerWait` 为
  null 的场景[点页签/轮询/换窗]是空操作, 无副作用)。
- `test_web.py` `test_frontend_qb_traffic_chart_wiring` +2 锚: 落袋登记语句存在 /
  `_drawerWaitSources` 通用分支与登记成对(拆开即挂死); 头部「测试计划」清单同步。

## 未验证面

- 真机: 流量页签开着单击换行(不挂死、新数据静默换图)、换到无流量数据的种子(落空态文案)、
  双击路径回归不破。
