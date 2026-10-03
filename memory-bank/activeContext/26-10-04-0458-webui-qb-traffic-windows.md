# WEBUI qB 流量图十档时间窗

> 摘要: 用户要求 qb 流量图添加 1/5/30 分钟、3/6/12/24 小时视图(与 qB 行为对齐)外加 3/7 天视图, 组/种子同样。
> 实施完成: 后端 WINDOW_SPECS/WINDOW_NAMES 2→10 档(1m-24h raw 段 / 3d/7d/30d hour 段, 存储零改动),
> 前端抽屉窗口按钮组 2→10 档 + qbWindowLabel + _qbTickLabel 三族刻度。test.full 2442 passed + 4 skipped /
> 99%(基线 26-10-04-0458)。档案 [tasks/26-10-04-webui-qb-traffic-windows](../tasks/26-10-04-webui-qb-traffic-windows.md)(Done)。

> 最后活动: 2026-10-04 05:10

## 进行中

- (无 —— 已按用户「提交」指令入库: 提交前 sync 合入远端 f019ed9c(轮询闪烁修复, 自动合并零冲突)后复跑 test.full 全绿, **提交 7da54233 已推 Gitee develop**)

## 已完成

- 后端: `core/traffic_grid.py` WINDOW_SPECS 十档 + ValueError 文案动态拼; `webui/server/traffic_qb.py`
  WINDOW_NAMES 十档 + parse_window 400 detail 动态拼; `routes/state.py` docstring 口径。
- 前端: `tpl/drawer.html` 窗口按钮组十档(1分/5分/30分/3时/6时/12时/24时/3天/7天/30天);
  `qb_traffic_chart.js` qbWindowLabel + _qbTickLabel 三族(1m/5m 标到秒 / 3d+ 标日期 / 其余标时刻);
  `state.js` 三挂点 window 字段注释。
- 测试: `test_traffic_grid.py` +test_build_grid_extended_windows(ValueError 探针改 90d);
  `test_web.py` 窗口校验十档全放行。keys.md qb_traffic 段视图口径回写。
- 基线: [baselines/26-10-04-0458](../testing/baselines/26-10-04-0458-webui-qb-traffic-windows.md)。

## 未验证面

- 真机换窗走查(短窗桶数 / 刻度文案 / 轮询续拉 / 组+种子入口十档一致)待用户。
