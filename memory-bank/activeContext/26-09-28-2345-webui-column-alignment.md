# WEBUI 表格列对齐审计(逐表逐字段盘点 + 推荐口径)

> 摘要: 盘点全部 7 张表(分组/明细/种子/追剧主表 + 抽屉 Tracker/用户/内容)列对齐现状出报告。结论: 主表机制健康(align 单点在 app.js 列模型, colAlignCss 表头/值同源注入); 真实混乱两处 —— ①时间/时长族口径分裂(完成于/活跃时间右 vs 添加于/最近活动/做种时长左, 4 字段×2 表, 建议 align 改 left); ②抽屉 3 表数值列 9 字段全落默认左(无列模型所致, 建议 th/td 挂类 + 三主题 CSS 各一条)。分享率左对齐为 2026-09-26 已拍板例外, 不动。报告 reports/26-09-28-2345-report-webui-column-alignment.html。
> 最后活动: 2026-09-28 23:45

## 进行中 / 待办

- P1 修复(最小 diff): app.js DETAIL/TORRENT 列模型 completion_on + time_active 共 4 处 align right→left —— 等用户确认口径后再动手。
- P2 修复: 抽屉表数值列右对齐(模板挂类 + 三主题 CSS), 涉及 9 字段, 待与 P1 一并排期。
