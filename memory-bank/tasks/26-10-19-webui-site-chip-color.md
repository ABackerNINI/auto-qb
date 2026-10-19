# 26-10-19-webui-site-chip-color — 站点问题改色表达与 chip 图标收口

**Status:** Done
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
| S0 | 复验三处 chip / 两槽 / `ALERT_ICON` / `.search-hit` / `.m-site` 锚点 | Done |
| S1 | 模板去左槽 + `siteAlertClass` / `chipAlertTip`; tooltip 从 svg 挪到 chip | Done |
| S2 | 三皮肤 `views.css`: 底色/虚线/`currentColor`/搜索命中描边 | Done |
| S3 | 明细行 `.m-site` 染色 + 同款 tooltip | Done |
| S4 | 静态守阵改钉 + `e2e/site-alerts.spec.mjs` 改断言(先红验) | Done |
| S5 | 全量测试 / 基线切片 / 文档回写 / 计划转 Done | Done |

## 进度日志

### R0 · 立档 (2026-10-19)

grilling 三轮 15 问收口, 计划件 `memory-bank/plans/26-10-19-2206-plan-webui-site-chip-color.html` 已出(Open), **尚未实施**。

### R1 · S0-S5 实施完成 (2026-10-19 22:34)

**S0 锚点复验**: 三处 chip(`xtpl-cells.html` 组行/种子页/集行)、两槽、`ALERT_ICON`、`.search-hit`、`.m-site` 行号与计划 §02 一致, 无未知渲染点; 三皮肤 + 棱镜五主题的 `--warn-soft/--error-soft/--warn/--error/--accent-line` 齐全(零新增令牌)。

**S1 结构与 helper**: 三处 chip 删左槽 `.sa`, chip 上加 `siteAlertClass(m)` / `chipAlertTip(m)` / `siteAlertAria(m)`; 图标上的 `title` 移除(提示上移整块 chip); `ALERT_ICON` 收窄为 `pending/ok/warn/error`(站点问题不再有图标映射)。

**S2 三皮肤样式**: `.sa-no-conf`(橙底 + `1px dashed` 底边)/ `.sa-tracker`(红底)/ `.m-site.*`(只染文字色)/ `.site-chip .sx` 尺寸; `.search-hit` 改 `background: transparent` + `inset 0 0 0 1px var(--accent-line)`(atlas 原写死 `rgba(59,130,246,.55)` 一并换成令牌)。源顺序: 站点问题 > 搜索命中 > 种子状态。

**S3 明细行**: `xtpl.html` 的 `.m-site` 与 `shows.html` 未识别行同语义染色 + 同款合并 tooltip。

**S4 守阵与 e2e**: `test_frontend_site_alert_icon_wiring` 改钉新契约(键集相等 / `.sa` 零残留 / 虚线底边 / search-hit 让出底色 / `.m-site` 染色 / `ALERT_ICON` 只含四态); `e2e/site-alerts.spec.mjs` 重写为 4 条 × 2 皮肤。**双向红验**: 静态 dashed→solid 即红; e2e 把 atlas 缺配置底改成 `--error-soft` 即红(prism 仍绿)。

**口径澄清(D5)**: `currentColor` 落地为**只作用于变色 chip**(`.site-chip.sa-* .sx`), 而非计划 §3.2 字面的 `.site-chip .sx` —— 后者会让正常 chip 的失败红叉继承种子状态绿字, 失败语义消失。R1 的可读性诉求同样满足, 且 e2e 双向断言(变色 chip 图标 == chip 前景 / 健康 chip 图标 == `--green`)。
