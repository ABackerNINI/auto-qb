# webui-site-alerts

> 摘要: 站点健康 + 逐目标回执已落地(计划 S0-S7 Done); 上线后按观感反馈返工: 站点问题改走 chip 底色(两槽方案作废), 见 26-10-19-2206 计划(Open)
> 最后活动: 2026-10-19 22:08

**Refs:** memory-bank/plans/26-10-19-2007-plan-webui-site-alerts.html, memory-bank/tasks/26-10-19-webui-site-alerts.md, memory-bank/plans/26-10-19-2206-plan-webui-site-chip-color.html

**R0(2026-10-19 20:20):** grilling 四轮收口(11 项拍板), 落地站点列提醒与逐目标汇报回执的实施计划 S0-S7

**R1(2026-10-19 21:24):** S0-S7 实施完成: 统一 tracker 健康取数器 + 站点 chip 两槽图标 + 逐目标回执; 计划转 Done, 已立档

**R2(2026-10-19 22:08):** 站点 chip 观感返工: grilling 15 问收口, 出改色表达计划 26-10-19-2206(Open, 未实施)

## 本轮结论

- 四条 WEBUI 待办(种子出错 / tracker 报错 / 缺站点配置 / 汇报部分失败不可定位)收敛到**一个锚点**: 站点 chip 内两个图标槽 —— 左槽持久健康(`site_alert`: `no_site_conf` / `tracker_error`), 右槽临时命令结果(`alertIcons`: pending / ok / warn / error)。判定与取数全在后端单点, 前端只消费字符串与符号。
- **取数统一**: `refresh_error_reasons` 改造为 `refresh_tracker_health` —— 一次 `/trackers` 调用同时喂 `tracker_error_msg`(状态列原因)与 `tracker_health_msg`(站点健康), `ERROR_REASON_BUDGET` 退役; 预算 20/轮 + 四档 TTL(600 / 30 / 60 / 300)+ 墙钟去抖 30s。
- **S0 真机标定**: 生产 qB 5.2.3 / 151 种子库, 单连接 keep-alive 连发 50 次 → 均值 0.38ms / P95 0.53ms; 20 条/轮 ≈ 7.5ms = 1.5s tick 的 0.5%, 远低于 R2 的 5% 触发线 ⇒ 预算与 TTL 按计划原值定死, **不触发线程化**。
- **回执**: `check_pending` 聚合带出 `truth.results`(逐 hash 结论), 前端按它把结果落到行上; truth 缺失统一落 warn, 不谎称成功。聚合 toast 文案逐字不变。

## 下一步

- **站点 chip 改色返工待实施**: 计划 `plans/26-10-19-2206-plan-webui-site-chip-color.html`(Open) —— 站点问题改走 chip 底色(缺配置橙/报错红), 图标只留命令结果并固定放文字后; 档案 `tasks/26-10-19-webui-site-chip-color.md`。
- 第一阶段已收口; **第二阶段**(全局汇总徽章: 顶栏/状态栏「N 个问题种子」+ 点击切筛选; 缺配置 chip 跳转站点页)按 D11 另立计划件, 尚未排期。
- 真机走查(可选): 在生产实例观察一轮真实 tracker 报错 → 图标亮起/恢复即灭的节奏是否与 30s/60s 口径一致。
