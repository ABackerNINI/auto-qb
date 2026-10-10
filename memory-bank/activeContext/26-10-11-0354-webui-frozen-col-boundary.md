# WEBUI 首列吸左边界提示(横滚残根 + 高行徽标漏出)

> 摘要: 用户报「WEBUI 向右滚动时状态栏会被名称栏遮挡」, 截图+追问后改判 = 表格「状态」列横滚时被吸左名称列盖住、尾字残根读成渲染错乱。根因 = 吸左边界无视觉线索, 修 = sync*HeadScroll 三处打 .is-hscrolled + 三皮肤边界落影/发丝线。**用户复报「小窗时站点徽标不会被名称列挡住」**: 根因 = 行 align-items:center 首格不拉伸(22px), 多 chip 格换行撑高行(71px)后徽标上下漏出, 修 = 首格 align-self: stretch。守阵 `test_frontend_frozen_column_boundary_wiring` 红验通过, e2e fast 60 passed ×2 轮, 基线 26-10-11-0354 全绿(04:07 复测持平)。
> 最后活动: 2026-10-11 04:07

**Refs:** memory-bank/tasks/26-10-11-webui-frozen-col-boundary.md

## 正在进行

- (无 —— 本轮已闭环, 等用户显式说「提交」)
