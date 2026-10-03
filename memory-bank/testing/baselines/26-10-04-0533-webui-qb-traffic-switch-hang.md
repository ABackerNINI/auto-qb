# 基线切片 26-10-04-0533 — WEBUI 流量页签单击换行遮罩挂死修复

> 摘要: 修「qB 流量图页签下单击换行, 抽屉一直显示加载中(遮罩挂死), 需关抽屉重开; 双击正常」。
> 根因 = FX-29 软切换协议只在 drawer.js 侧接了一半: `_drawerWaitSources` 通用分支把流量页签归入
> 待到集合(["detail", "traffic"]), 但落定登记 `_drawerDone` 只有 detail/trackers/files/peers 四个
> fetcher 在调 —— 流量取数单点 `_qbLoad`(qb_traffic_chart.js, 跨模块)落袋从不登记 "traffic",
> 集合永不清空 -> `drawer.switching` 遮罩「正在加载…」挂死。修法 = `_qbLoad` 落袋(成功/失败都算)
> 且 scope==="torrent" 时登记 `_drawerDone("traffic", ctx, 0)`(seq=0 只走 hash 戳守卫, 与
> def.stale 的 hash 判定同源)。双击走 openTorrentDrawer 整体重置不经待到集合, 故只有单击跟随路径踩中。

- 时间: 2026-10-04 05:33 (GMT+8); 会话起点 sync 至 f019ed9c, 提交轮再 sync 合入 7da54233+43c8f94a
  (另一 clone 的「流量图十档窗口」两笔, stash pop 零冲突)
- 分支: develop @ 43c8f94a(+ 本轮未提交改动: static/shared/qb_traffic_chart.js / tests/test_web.py +
  memory-bank 回写件)
- 命令: `commands run test.full`
- 实测: **2442 passed + 4 skipped, 30.87s, 覆盖率 TOTAL 99%**(14361 语句 / 135 未覆盖 / 4864 分支 / 106 partial)
- 相对上基线(26-10-04-0458: 2442 passed + 4 skipped)**净增 0 用例**: 本轮只给既有守阵
  `test_frontend_qb_traffic_chart_wiring` 补两锚(_qbLoad 落袋登记 _drawerDone("traffic") /
  _drawerWaitSources 通用分支与登记成对), 用例数不变断言数 +2。
- 未验证面: 真机走查待用户 —— 流量页签开着单击换行(应无挂死遮罩, 新数据落袋静默换图)、
  换到无数据种子(应落「暂无流量数据」空态)、双击路径回归。
