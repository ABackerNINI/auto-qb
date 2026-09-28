# 1831 passed / 3 skipped —— WEBUI 表格列对齐审计口径实施(5 文件 +24/-17)

> 摘要: 按 [reports/26-09-28-2345](../../reports/26-09-28-2345-report-webui-column-alignment.html) 推荐实施 —— P1 app.js DETAIL/TORRENT 列模型 completion_on + time_active 共 4 处 align right→left(时间/时长族 R4 统一左, 两列均默认隐藏); P2 抽屉 3 表数值列 9 字段 th/td 挂 .num 类 + 三主题 CSS 各补一条 `.drawer-table th.num, td.num { text-align: right }`。纯前端静态文件改动, 无 Python 侧变化。
> 基线时间: 2026-09-29 02:40

- test.full 一次通过: **1831 passed / 3 skipped**, 24.03s, TOTAL **91%**(12462 语句 / 917 未覆盖 / 4246 分支 / 391 partial); 较 26-09-29-0044 基线 passed 数持平, 本轮增 0 测试(纯对齐值与模板类名改动, 无新逻辑分支)。
