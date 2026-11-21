# 6795 —— 方向B打断继承收口基线: test.full 全绿

> 摘要: 方向B打断继承收口基线: test.full 全绿
> 基线时间: 2026-11-22 06:28
**Refs:** memory-bank/tasks/26-11-22-webui-traffic-interrupt-inherit.md

## 验收数字

- 汇总行: `6789 passed, 6 skipped, 8 warnings in 160.29s (0:02:40)`
- TOTAL 表: `TOTAL 30681 85 10942 87 99%`(语句 30681 / 缺 85 / 分支 10942 / 部分分支 87)
- 覆盖率线: 本切片实算 99% 档(30681 语句缺 85 → 99.72%); 99.5% 达标线对照上一切片 26-11-21-1704(99.60%)—— 本轮语句增量(+131)摊薄了表显 99% 整数档, 实算线在达标线上方(评审轮内 ship.gate/test.quick 全绿佐证)。
- 上一切片对照: 26-11-21-1704(webui-traffic-window-head-trim)`6757 passed + 6 skipped` → 本轮 +32 passed(其中本批新增: 纯函数电池 L1-L8 八断言 + 调度器场景 S21/S24/S25/S26 + 静态钉改判; 其余为评审期间并合的远端 6 笔 relocate 专题新测试), 6 skipped 持平。

## 本改动面

- `src/auto_qb/webui/static/shared/qb_traffic_chart.js` — 模块级纯函数 `_qbBeatVpRem`(L0 rem 单点: easeOut + 末帧 ulp 吸附钳, 帧循环与打断继承重建共用)+ `_qbInheritedViewport`(取消瞬间视口重建: t=0 完整摆回锚/clock>=shiftMs 真窗口/中段按 rem 比例/预览与非摆回拍 null/防御 NaN-Inf 空列/纯函数零 mutate); 帧循环 rem 行改消费 `_qbBeatVpRem`(行为逐位不变); 快路 `_qbChartBuild` setData 前捕获继承视口(列亲和约束)交 `_qbBeatStart` 第三参; 判定帧继承逻辑(摆回锚 dxMin0/dxN 换算剩余位移, 锚恒真窗口四处公式不动; 继承拍零变化 roll 伪真进同一 `_qbFxShiftGate`; rewin 不继承)+ 注释面三处回写(文件头 SSE 节/_qbBeatStart 节注/快路捕获注)。
- `tests/test_webui_static_dom_panel_traffic.py` — 纯函数电池 L1-L8(rem 单点单调与钳零/重建三态/门与防御/缺参回落/零 mutate)+ 调度器场景 S21(零变化打断继承全链: 捕获 -> 摆回继承位零回跳 -> 剩余位移滑完 -> 收敛摘补点)/S24(真滚动打断: max 侧从打断位续滑)/S25(rewin 打断不继承)/S26(纯 min 侧剩余位移行为化, 评审轮1 nit)+ 静态钉更新六处(快路逐字序带捕获/签名正则三处/rem 单点与 easeOut 计数钉/摆回门 jShift/继承锚换算)+ 测试计划 docstring 同步。
- `memory-bank/conventions/attachments/webui-traffic-beat.md` — 权威附件「读侧契约换代收口」节新增「打断继承视口」条目(残余根因/修法/列亲和约束/instant-reduce 恒定压缩变体待拍板边界)。
