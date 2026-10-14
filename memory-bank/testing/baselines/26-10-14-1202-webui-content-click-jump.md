# 3205 —— 内容页树表点击跳动: 整帧换滚动位自保(dt10/dt11 缺 withScroll 补齐)

**Refs:** memory-bank/tasks/26-10-14-webui-content-click-jump.md

> 摘要: 失修 26-10-14 用户三复查(报告 26-10-14-0136 §02)「点击跳动」—— 内容页树表两变体(10 树+详情 / 11 树表批量)整帧换把宿主子树清, 内容页签滚动容器(.drawer-body, 宿主父)按新内容现算把 scrollTop 先落 0 再回; 徽章小菜单提交这类走 rerender 单点重渲后, 用户滚到中间再点后整列表跳. 修法 = 与 01-09 变体同口径, 把整帧换收进 withScroll 成对恢复单点 helper. 验证 = pytest 全量 + e2e @fast 全量(134 例).
> 基线时间: 2026-10-14 12:02
> 档案: memory-bank/tasks/26-10-14-webui-content-click-jump.md

## 验收数字

- test.full: 3205 passed + 4 skipped / TOTAL 16824 158 5724 140 99%(99%, 过 98% 闸门).
- 耗时: 121.6s(单次采样, 口径见 baseline.md).
- e2e @fast 全量(本机 8137 起桩串行): 134 passed(含本专题三份 spec: drawer-content-variant-tables / dt-table-layout-parity / dt-live-update; 未跑全量矩阵轮, 口径同前基线).
- 包内脚本测试(commands run test.pkg): 本轮未触 .commands/ 与 .agents/skills/commands/, 闸门 match 不命中, 未跑.
- Linux(WSL)侧未重测 —— 改动为纯前端(静态 JS 整帧换收进 helper), 无平台分支; 本条 Windows 侧数字为事实源.

## 本改动面

- 源(2 文件): drawer_tpl/10-content-tree-detail-tall.js(整帧换 replaceChildren + anchFill 收进 H.withScroll(host, ...)) · drawer_tpl/11-content-treegrid-batch-low.js(同口径).
- 测试: 本轮零测试文件改动 —— 既有守阵/e2e 三份 spec 不变(本修不改列集/几何/交互件, 只把整帧换收进既有成对恢复 helper; 既有 dt-live-update #8「check-no-jump」守阵仍绿).
- 文档: 本切片 · 任务档案 tasks/26-10-14-webui-content-click-jump.md · activeContext 切片 26-10-14-1202-webui-content-click-jump.md · 坑档 pitfalls/web-ui/frame-swap-scroll-reset.md · 报告 26-10-14-0136 doc-refs 追加本档案反声明 · kb.index 生成物重建.

## 已知偏差 / 移交

- 85px 跳动未复现: 探针把修复前形态仍 maxRowDev=0、scrollVals=[300]、changedFrames=0 —— 桩把整帧换把 scrollTop 不落 0. 本修即「01-09 同口径」的缺口收, 85px 即用户真机形态, 桩未命中该路径; 修随专题入库, 若用户四复查仍跳动需另复探针(真机形态分账).
