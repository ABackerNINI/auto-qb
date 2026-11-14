# 6086 passed + 2 skipped(根) —— 流量图节拍动效 S5 收口基线

> 摘要: 流量图节拍动效 S0-S4 八批 + S5 收口(终树)入库基线
> 基线时间: 2026-11-14 09:49
**Refs:** memory-bank/tasks/26-11-14-webui-traffic-beat-motion.md

## 验收数字

```text
TOTAL                                                27113     65   9480     69    99%
6086 passed, 2 skipped in 177.62s (0:02:57)
```

(实测时点: S5 收口轮 `commands run test.full` 2026-11-14, 收口全部改动(文档回写/任务档案/坑档/基线切片 + 测试注释修正)落定后的**终树**; 首测(注释修正后、KB 建件前)6086/2 同数字 185.06s, 终树复跑逐位一致 —— 记录取终树那轮。2 skipped 为存量 skip; 合并口径覆盖率 = (27048+9411)/36593 ≈ 99.63%, 与 S4-b 批实测同口径。本切片为本专题组合树的测试数字权威, 其余处一律引用不手抄)

## 本改动面

- **功能面(S0-S4 八批, 逐批明细见各提交 message 与计划 26-11-12-1139 §06)**: `src/auto_qb/webui/static/shared/` 下 qb_traffic_chart.js(节拍内核/视觉引擎/T6 表现层/面板接线)、state.js(fx/fxPanel 字段与 watcher)、tpl/fx-panel.html(数值面板模板)、shortcuts_engine.js/lifecycle.js/dialogs_meta.js/drawer_store.js/drawer_general.js(收层七处登记) + 四皮肤 index.html 与 dialogs.css(.fx-panel 登记段)。
- **测试面**: tests/test_webui_static_dom_panel_traffic.py(节拍内核/接线/收层/面板电池 + 静态钉)、test_webui_static_dom_panel_misc.py、test_web_shortcuts_drawer.py、test_webui_error_history.py、test_webui_static_r4_static_batteries.py + e2e/traffic-fx-panel.spec.mjs、e2e/traffic-fx-frames.spec.mjs(均入 @fast) + e2e/perf-serial.mjs/shard-run.mjs/playwright.config.mjs。
- **S5 收口面(本切片测的树新增)**: memory-bank 回写(conventions/webui.md 主题地图加行 + 新附件 webui-traffic-beat.md、计划 26-11-12-1139 收口 Done、pitfalls/testing/static-guard-mutation.md 复发 +1、任务档案、本切片) + 根 README Web UI 节补流量图节拍动效条 + tests/test_webui_static_dom_panel_traffic.py:4312 注释失实修正(纯注释行, Vue 生产构建对模板缺失处理器完全静默的如实表述; 行为断言零变化)。
