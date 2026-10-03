# 基线切片 26-10-04-0448 — WEBUI qB 流量图轮询闪烁修复

> 摘要: 用户报「WEBUI qb流量图每隔几秒闪烁一次」。根因 = 低频轮询续拉对用户可见:
> ①`_qbLoad` 一开始亮 `qbCurLoading` -> 模板 `v-if="qbCurLoading"` 把整块图换成加载空态再换回
> (图 DOM 每个轮询周期拆装一次); ②数据落袋后 `_qbChartBuild` 走 destroy + `new uPlot` 整图重建,
> canvas 清屏一帧。与坑档 [drawer-switch-flicker](../../pitfalls/web-ui/drawer-switch-flicker.md)
> 「加载态立即点亮 = 制造新闪烁」+「快中间态本身就是闪」同型(复发 +1)。
> 修法 = 静默续拉: 模板 loading 空态只在无数据时接管(`qbCurLoading && !qbCurPoints.length`);
> 同宿主上图还活着走 `u.setData` 原地换数据(不销毁重建), 完整重建仅首图/宿主被拆后/换肤三处
> (换肤处理器相应改先 `_qbChartDestroy` 再重建 —— canvas 色是建图时烘焙的令牌值, setData 不换色)。

- 时间: 2026-10-04 04:48 (GMT+8); 分支 develop, 实测时点 = 718b96f4(合并远端跨组交叉检测 7 笔之后)
- 改动: `tpl/drawer.html`(loading 空态门) / `shared/qb_traffic_chart.js`(setData 原地快路 + 换肤先销毁) /
  `tests/test_web.py`(守阵补三锚: 模板门 / setData 快路 / 换肤先销毁, docstring 两处同步)
- 命令: `commands run test.full`
- 实测: **2441 passed + 4 skipped, 31.35s, 覆盖率 TOTAL 99%**(14361 语句 / 135 未覆盖 / 4864 分支 / 106 partial)
- 相对上基线(26-10-04-0412: 2441 passed + 4 skipped)用例数持平(新增 3 条断言进既有守阵, 不增用例), 全绿零回归
- 未验证面: 真机走查(用户实测闪烁是否消失 / 换窗 / 换肤后图色正确)留待用户
