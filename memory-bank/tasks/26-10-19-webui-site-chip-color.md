# 26-10-19-webui-site-chip-color — 站点问题改色表达与 chip 图标收口

**Status:** In Progress
**Added:** 2026-10-19
**Updated:** 2026-10-19
**Summary:** 站点问题(缺配置/tracker 报错)改由 chip 底色表达, 图标通道只留命令结果并固定在站点名之后; tooltip 挂整块 chip, 明细行文字染色
**Topics:** webui-site-chip-color
**Refs:** memory-bank/plans/26-10-19-2206-plan-webui-site-chip-color.html

## 原始请求

1. 站点图标位置没有统一, 有的在前面有的在后面。
2. 站点状态色没有一起更改(站点有问题时 chip 本体不变色)。
3. tracker 错误的 tooltip 只能在图标上触发。
4. 强制重新汇报的出错图标与 tracker 出错图标一样, 只是位置不同。
5. 先 grilling(已三轮 15 问收口), 然后先出计划; 计划已出, **尚未实施**。

## 思考过程与决策

计划 §06 的 D1-D11 全部沿用。这轮的关键是把"通道分工"定死 —— 站点问题走**颜色**、命令结果走**图标**, 于是"位置不统一"与"两类错误撞脸"同时消失(不是分别打补丁):

- 位置: 图标只剩一种(命令结果), 固定放在站点名之后 —— 不需要"左健康右结果"的双槽语义。
- 撞脸: tracker 报错不再有图标, 红叉只剩命令失败一种含义。
- 颜色: 缺配置=橙底(+虚线底边做非颜色通道), 报错=红底; 与"种子错误"红底不做额外区分(错误态整行已红, chip 再红无信息增量)。
- 变色后的可读性: chip 文字与图标统一 `currentColor`, 图标不再写死语义色。
- 叠加态: 站点问题 > 搜索命中(改描边) > 种子状态色。
- 明细行没有 chip 底色, 用文字染色 + 同款 tooltip 承载同一语义。

## 实现计划

计划 §04 的 S0-S5:

- S0 复验锚点(不改代码)
- S1 结构与 helper(模板三处去左槽 + `siteAlertClass` / `chipAlertTip`)
- S2 三皮肤样式(底色/虚线/`currentColor`/搜索命中描边)
- S3 明细行 `.m-site` 染色 + tooltip
- S4 静态守阵与 e2e 改断言(先红验)
- S5 收口(全量/基线/文档回写/计划转 Done)

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S0 | 复验三处 chip / 两槽 / `ALERT_ICON` / `.search-hit` / `.m-site` 锚点 | Open |
| S1 | 模板去左槽 + `siteAlertClass` / `chipAlertTip`; tooltip 从 svg 挪到 chip | Open |
| S2 | 三皮肤 `views.css`: 底色/虚线/`currentColor`/搜索命中描边 | Open |
| S3 | 明细行 `.m-site` 染色 + 同款 tooltip | Open |
| S4 | 静态守阵改钉 + `e2e/site-alerts.spec.mjs` 改断言(先红验) | Open |
| S5 | 全量测试 / 基线切片 / 文档回写 / 计划转 Done | Open |

## 进度日志

### R0 · 立档 (2026-10-19)

grilling 三轮 15 问收口, 计划件 `memory-bank/plans/26-10-19-2206-plan-webui-site-chip-color.html` 已出(Open), **尚未实施**。
