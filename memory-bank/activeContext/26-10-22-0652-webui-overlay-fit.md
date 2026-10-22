# webui-overlay-fit

> 摘要: 浮层定位几何(8px/12px 边距+视口夹取)12 处手写收敛为单点 shared/overlay_fit.js(window.AQB_OVERLAY_FIT: EDGE/clampAxis/probeRight/probeLeft/fitInViewport); hubAsk 与 speed-pop 的 12px 显式命名常量传参保留; 新增守阵 test_overlay_fit_single_point(单点存在性+装载序+7 消费文件接线对账+手写残留零容忍+12px 显式命名+跨文件顶层 const/let 撞名扫描+node 等价网格); 修复过程中发现并修复 classic script 顶层 let/const 跨文件撞名致整页瘫的坑(已入 pitfalls/web-ui/classic-script-top-level-const-collision.md); test.full 与 e2e 全量数字见 kb.baseline(本轮全量跑过, 逐位持平); 授权范围只含认领与修复两项
> 最后活动: 2026-10-22 06:52

**R0(2026-10-22 06:52):** 浮层定位几何(8px/12px 边距+视口夹取)12 处手写收敛为单点 shared/overlay_fit.js(window.AQB_OVERLAY_FIT: EDGE/clampAxis/probeRight/probeLeft/fitInViewport); hubAsk 与 speed-pop 的 12px 显式命名常量传参保留; 新增守阵 test_overlay_fit_single_point(单点存在性+装载序+7 消费文件接线对账+手写残留零容忍+12px 显式命名+跨文件顶层 const/let 撞名扫描+node 等价网格); 修复过程中发现并修复 classic script 顶层 let/const 跨文件撞名致整页瘫的坑(已入 pitfalls/web-ui/classic-script-top-level-const-collision.md); test.full 与 e2e 全量数字见 kb.baseline(本轮全量跑过, 逐位持平); 授权范围只含认领与修复两项
