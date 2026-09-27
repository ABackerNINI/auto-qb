# 1818 passed / 3 skipped —— 控制台皮肤进度条填充改绿色语义

> 摘要: 用户反馈(承接 dc581a9b): 进度条填充单白色会被误读成"空", 语义不正确。console/css/components.css 的 `.m-progress .bar > i` LED 填充由 `currentColor`(实际继承行前景白)改 `var(--green)`(#3fd699, 有量语义); 0% 自然无填充, 弱轨道即"空"态。注释同步改正 —— 原注释称"行状态色规则已把 .m-progress 随行染 currentColor"与事实不符(实际只有 `.val` 被染), 按新实现重写。ui_harness(400 种子/200 组)+ Playwright 实渲染: 种子页/辅种页组行/明细行填充均 rgb(63,214,153), 0% 行空轨道对比清晰。
> 基线时间: 2026-09-28 04:53
> 档案: (无 —— 未达立档阈值, 沿用切片 26-09-28-0421-webui-console-progress-bar)

- 纯静态前端 CSS 一处改动(+注释), 用例总数不变: 1818 passed / 3 skipped。
- ⚠ 本轮首跑 test.full 曾出 1 failed(未截到用例名), 连续 3 轮复跑全绿未复现, 疑瞬态; 下轮基线若再现按名字立档。
- TOTAL **91%**(12512 语句 / 917 未覆盖 / 4204 分支 / 389 partial), 耗时 19.5s。
