# 1820 passed / 3 skipped —— 站点搜索命中改下拉浮层

> 摘要: trackers 二级页搜索命中展示由「列表居左+详情居右」分栏改为搜索框下挂下拉(hb-tr-drop, 视觉口径对齐 search-help-pop)+详情整栏宽(hb-tr-detail); 行为不变, JS 零改动。守阵 hb-tr-split/hits→hb-tr-drop 同步。纯前端静态资源改动, 增 0 测试。
> 基线时间: 2026-09-28 15:58

- test.full 首跑遇 throttle 计时假红 1 条(test_qbmanager.py::test_run_loop_throttles_without_stop_event, 单跑即过, 与本轮无关), 重跑一次通过: **1820 passed / 3 skipped**, 20.47s, TOTAL **91%**(12542 语句 / 918 未覆盖 / 4222 分支 / 389 partial); 与 26-09-28-0744 同数字 —— 本轮增 0 测试, 仅守阵类名替换。
- test.quick 首跑(改动当轮)全绿 1820 passed(18.5s)。
