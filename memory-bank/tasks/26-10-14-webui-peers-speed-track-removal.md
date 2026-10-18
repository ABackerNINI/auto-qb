# 26-10-14-webui-peers-speed-track-removal — 种子详情用户页速度数值下方多余暗色条: 行级速度微条 track 退役(07/08)

**Status:** Done
**Added:** 2026-10-14
**Updated:** 2026-10-18
**Summary:** 用户报「种子详情面板用户页四卡仪表/五区分组表中上传/下载速度数值下方有多余的暗色条, 移除」。Root cause = 行级速度微条 track(.dt07-spd/.dt08-spd .track, 3px 全宽 background --bg-sunken)里的填充 `<i>` 无任何 background —— 模板只置 inline width, 变体 CSS 里对 `.track i` 无 background ⇒ 填充恒透明, track 即全宽暗色条不论速度(用户所报的"多余暗色条"= 这条失填充的微条, 不是设计元素)。修法按用户字「移除」= 整 track 退役: 两份单元格删 `<span class="track">` + 两变体删 `.track` CSS + 一并退役死字段 upBar/downBar 与 rowsFn 里的 maxUp/maxDown 满刻度求值(grep 无其它消费点); 速度数值文字保持方向色(--today-up/--today-down), 卡 1 flowbar/dirbar(有 background)不动。验证 = 真浏览器 DOM 探针(两变体速度格零 track)+ 截图 + e2e @fast 全绿 + 静态守阵绿 + test.full 全绿, 数字见 Refs 基线切片。

**Refs:** memory-bank/testing/baselines/26-10-14-1615-webui-peers-speed-track-removal.md
**Topics:** webui-detail-table-rebuild

## 原始请求

> 种子详情面板用户页四卡仪表/五区分组表中上传/下载速度数值下方有多余的暗色条, 移除, 截图让我验收

## 思考过程与决策

- 「用户页」= 抽屉 peers 页签; 「四卡仪表/五区分组」= 变体 07/08; 速度单元格呈现在 `tpl/xtpl-cells.html` 分片 `tpl-aq-dt07-cells`/`tpl-aq-dt08-cells`, 暗色条 = `.track` 微条容(track 全宽 3px background --bg-sunken, 填充 `<i>` inline width 仅)。
- 填充失色定案: 变体 CSS `.dt07-spd .track i`/`.dt08-spd .track i` 无 background 且模板无 inline background ⇒ 填充恒透明, track 即全宽暗色条无论速度 —— 与卡 1 flowbar(`.dt07-flowbar i` 有 background)对照, 行级微条是失填充形态, 用户字「多余暗色条」即现机形态。
- 用户拍「移除」(改色不拍)⇒ 整 track 退役三件: 单元格删 track span(两变体) · 变体 CSS删 `.track` 两规则(两变体) · 死数据 upBar/downBar 与 rowsFn maxUp/maxDown 求值一并退役 —— grep 全面无其它消费点(守阵/e2e 不钉 them), 死字段留即 slop 不即契约.
- 边界: 卡 1 上传去向分段(flowbar)/方向五桶(dirbar)/进度条(prog .bar)各有 background 真渲染, 不动; 变体 09 占用列条另一判据不动(用户只字 07/08).
- e2e 断走 `.dt07-spd` textContent(速度实时守阵), track 删不影响; 静态守阵(test_webui_static_skins/dom_panel)钉 cell renderer 与列集但 not track, 同轮绿.

## 实现计划

1. xtpl-cells.html: dt07/dt08 upspeed/dlspeed 四单元格删 track span.
2. 07/08 变体: 删 `.track` CSS 两规则 + 退役 upBar/downBar 字段与 maxUp/maxDown 求值 + 卡 1 tip 文案「与列表行内速度微条同色」引用摘(track  gone).
3. 验证: 真浏览器(桩 harness)两变体 DOM 探针零 track + 截图; e2e @fast; 静态守阵 targeted; test.full.
4. KB 回写: 基线切片 + 立档档案 + activeContext 切片 + kb.index 重建.

## 子任务状态表

| 子任务 | 状态 |
|---|---|
| xtpl-cells.html 四速度格删 track span | ✅ |
| 07/08 变体 CSS 删 track 规则 + 死字段/满刻度求值退役 | ✅ |
| 真浏览器两变体零 track + 截图验收件 | ✅ |
| e2e @fast + 静态守阵 + test.full 绿 + KB 回写 | ✅ |

## 进度日志

- **2026-10-14**: 开工先 `my-commit-flow.sync` → 已同步 `2e3a4372`. 定位: grep 速度格 → xtpl-cells.html 两分片 + 两变体 CSS; Root cause 定案 = track 填充失 background(对照卡 1 flowbar 有).
- **改动**: 3 源文件(xtpl-cells.html · 07-peers-dashboard-tall.js · 08-peers-groups-low.js)—— 命中立档阈值(>=3 源文件).
- **验证**: 桩 harness 起, 真浏览器双击开抽屉→用户页签两变体 DOM 探针速度格零 track + 两截图(验收件); e2e @fast 全绿(端口 8137 残留走 `dev.port-kill` 再跑); 静态守阵 targeted 绿; test.full 全绿(数字见 Refs 基线切片).
- **KB 回写**: 基线切片 26-10-14-1615 + 本档案 + activeContext 切片 26-10-14-1615 + kb.index 重建.
- 2026-10-18 10:1x: Topics 复合键回归单主键(issue 26-10-18-0858 拍板: 维持单主键口径): 原 "webui-detail-panel-redesign, webui-drawer-templates" 第一键写错——本档(用户页 07/08 速度微条退役, 波浪症状②)属 10-14 detail-table-rebuild 复查浪, 归 webui-detail-table-rebuild; 次要键无反声明目标, 从元数据消失, 关联由同键分组承载。
