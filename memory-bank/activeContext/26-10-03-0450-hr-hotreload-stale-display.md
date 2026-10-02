# HR 热重载后 WebUI 停留「本地·达标」根因分析

> 摘要: 用户实报「热重载开启站点 HR 在线核实后 WebUI 仍显示本地·达标, 重启才显示在线·已达标」。计划轮完成: 两层根因取证(存量 `rec.tracker_conf` 不随热重载重绑——L2 判据只比绑定三元组 + full_round 只补 None; HR 判定变化无置脏机关, 视图快照挂旧值), 分步修复计划 [plans/26-10-03-0436](../plans/26-10-03-0436-plan-hr-hotreload-webui-stale-display.html)。
> 最后活动: 2026-10-03 04:50

## 正在进行

- **待实施**: 计划四步——① TrackerModule 新增 apply(trackers 段变即重绑存量记录, 顺带修好 hr 规则段热重载与 `_anchors` 锚点收集) ② WebUI 补 `hr.revision` 新鲜度置脏 ③ test_tracker / test_web 单测 ④ 真机验收(不重启验证场景复原)+ 收尾 DoD(pitfalls/backend 入坑: 热重载换对象 ≠ 存量绑定对象自动更新)。
- 实施前先读计划文档 04 节「已排除项」避免误修(热重载时序 / HrRuntime.apply / worker 冷启动发布均已验证正常)。

## 已完成

- 2026-10-03 计划轮: 判定链路取证(record/rules_mod/tracker_mod/resolve/views/webui runtime + hr runtime/worker/service)+ 计划文档产出, 未动代码。
