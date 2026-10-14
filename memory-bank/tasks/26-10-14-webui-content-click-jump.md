# 26-10-14-webui-content-click-jump — 内容页树表点击跳动: 整帧换滚动位自保

**Status:** Done
**Added:** 2026-10-14
**Updated:** 2026-10-14
**Summary:** 用户三复查(报告 26-10-14-0136 §02)「点击跳动」—— 内容页树表两变体(dt10 树+详情 / dt11 树表批量)整帧换把宿主子树清, 滚动容器按新内容现算把 scrollTop 先落 0 再回; 徽章小菜单提交这类走 rerender 单点重渲后, 用户滚到中间再点后整列表跳. 修法 = 与 01-09 变体同口径, 把整帧换收进 withScroll 成对恢复单点 helper. 验证 = pytest 全量 + e2e @fast 全绿, 数字见 Refs 基线.

**Refs:** memory-bank/reports/26-10-14-0136-report-webui-detail-table-rebuild-review.html,memory-bank/testing/baselines/26-10-14-1202-webui-content-click-jump.md,memory-bank/pitfalls/web-ui/frame-swap-scroll-reset.md
**Topics:** webui-detail-panel-redesign, webui-drawer-templates

## 原始请求

> 修复: 种子详情内容页表格点击跳动的问题
> 附录: 26-10-14-0136-report-webui-detail-table-rebuild-review.html

## 思考过程与决策

- 报告 §02
- §02 问题面: 点击跳动(atlas 85px).
- §3.1 归因: 数据回路全帧重建.
- 行身份 ref-stable(_dtMergeRows).
- 缺口: 10/11 缺 withScroll(01-09 有).
- 修法: 整帧换收进 withScroll.
- 未复现: 探针 maxRowDev=0, scrollVals=[300].
- 结论: 缺口收, 真机形态分账未命中.

## 实现计划

1. 10/11 变体 js: replaceChildren + anchFill 收进 H.withScroll.
2. 既有守阵/e2e 不变(列集/几何/交互件不改).
3. test.full + e2e @fast 全量验, 基线切片, KB回写.

## 子任务状态表

| 子任务 | 状态 |
|---|---|
| 10/11 整帧换收进 withScroll | ✅ |
| 探针复前形态取证 | ✅ |
| test.full + e2e @fast 全绿 | ✅ |
| 基线切片 + KB回写 | ✅ |

## 进度日志

- 26-10-14 11:5x: sync 已同步 de83fbe8. 读报告 §02/§3.1, 定位缺口(10/11 缺 withScroll).
- 26-10-14 12:0x: 修两变体 js; 探针(40文件桩, 滚300, 屏内徽章, rAF)复前形态仍 maxRowDev=0 —— 85px 未复现, 缺口收为事实; test.full 3205+4 skip 99%, e2e @fast 134 绿; 基线切片落, KB回写随本专题入库.
