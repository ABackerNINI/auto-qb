# 26-10-03-backend-hr-hotreload-stale-display — HR 热重载后 WebUI 停留「本地·达标」修复

**Status:** Done
**Added:** 2026-10-03
**Updated:** 2026-10-03 07:28
**Summary:** 用户实报: 热重载开启站点 HR 在线核实后 WebUI 恒显「本地·达标」, 重启进程才显「在线·已达标」。计划 [plans/26-10-03-0436](../plans/26-10-03-0436-plan-hr-hotreload-webui-stale-display.html) 取证出两层根因(主因: 存量 `rec.tracker_conf` 不随热重载重绑 —— L2 判据只比绑定三元组 + full_round 只补 None, `hr_judgement()`/`_anchors()`/`hr` 规则段三个消费面全瘫; 辅因: HR 判定非快照字段, 取数发布新视图无置脏消费方, WebUI 快照挂旧值), 四阶段串行实施全过: P1 `TrackerModule.apply`(trackers 段变即重绑存量记录, `2a5d07a2`) / P2 `WebUIRuntime` 补 `hr.revision` 新鲜度置脏(`e4df1fc0`) / P3 桩走查 PASS / P4 收尾回写(坑档 hot-reload-stale-bindings-derived-views + 常青文档回写 + 基线)。全量回归见 `kb.baseline` 最新切片; 真机走查(P3 以桩代真机)待用户有空时复核。
**Topics:** backend-hr-hotreload-stale-display
**Refs:** memory-bank/plans/26-10-03-0436-plan-hr-hotreload-webui-stale-display.html

## 原始请求

用户实报: 热重载开启站点 HR 在线核实后, WEB UI 一直显示「本地·达标」; 重启进程后才显示「在线·已达标」。要求: 完整判定链路取证 → 分步修复计划 → 按阶段串行实施(代码每阶段独立提交)→ 收尾按 memory-bank DoD 回写。

## 思考过程与决策

- **两层根因**(计划轮取证, 逐时刻链路见计划文档 §1):
  1. **主因 —— 存量绑定陈旧**: 热重载只替换 `manager.config` 对象; 存量种子的 `TorrentRecord.tracker_conf` 仍指向旧 Config 的 `TrackerConfig`(其 `hr_check` 派生视图为 None)。重绑只有两条既有路径且都不覆盖: L2 结构重建判据 `_tracker_bindings_changed` 只比较绑定三元组 `(domains, rules, groups)`; full_round 补绑只认 `tracker_conf is None`。`hr_judgement()` 读旧对象恒返回 None(「站点未接入」语义)→ 本地兜底「本地·达标」。同病三个消费面: HR 判定 / `HrRuntime._anchors()` 锚点收集(对账管线瘫痪) / `hr` 规则段(改要求做种时长不生效)。
  2. **辅因 —— 判定变化不置脏**: 取数线程抓到数据后发布新视图(`HrViewPublisher.revision` 自增), 但 HR 判定结果不是 store 快照字段, `store.consume_view_changed()` 覆盖不到, 无任何代码路径翻译成 `mark_dirty()` —— 界面快照停在热重载那一刻。
- **方案取舍**(计划 §6): 不扩大 L2 重建判据(把配置值比较塞进结构语义单点, 会把开一个 HR 核实放大成全量重建); 不改判定端现读(只修一个入口, 修不到锚点收集与 hr 规则段)。选定「apply 显式重绑」: 一处修复覆盖三个消费面, 且不触碰 L2 结构语义。
- **置脏形态**: 仿库内「错误原因」先例(非快照字段由变化方显式置脏) —— 重建时记 `hr.revision` 基线, flush 时比对不等即置脏, 基线随重建前移, 无循环置脏。
- **走查形态**: 真机场景(P3)以桩走查代真机 —— 桩保真度局限已记录(判定桥手工接线、t2 取数为直推 publisher 模拟), 真机复核留给用户。

## 实现计划

计划文档 [plans/26-10-03-0436](../plans/26-10-03-0436-plan-hr-hotreload-webui-stale-display.html) 四步:

| 阶段 | 范围 | 提交 |
|---|---|---|
| P1 | `TrackerModule` 新增 `apply(old,new)`: trackers 段按值变化即重绑存量记录(回执 `tracker:rebound N`, client=None 防御) + test_tracker 三用例(红验过) | `2a5d07a2` |
| P2 | `WebUIRuntime` 记 `_hr_rev_at_build` 基线(挂 `_publish_locked` 末尾), `flush_views` 比对 `hr.revision` 不等即 `mark_dirty()` + test_web 两用例(红验过) | `e4df1fc0` |
| P3 | 桩走查: t0「本地·达标」→ t1 回执 `tracker:rebound 6` + `hr_check` 就位 → t2 revision 1→2 置脏重建 → t3「在线·已达标」; 回归: 无关段热重载无 rebound、重启路径正确 | (无代码) |
| P4 | 收尾回写: 坑档 / 常青文档 / activeContext+progress / 基线切片 / 计划标 Done | (本轮, 未提交) |

## 子任务状态表

| # | 子任务 | 状态 |
|---|---|---|
| 1 | P1 TrackerModule.apply + 单测 + 提交 | Done (`2a5d07a2`) |
| 2 | P2 hr.revision 置脏 + 单测 + 提交 | Done (`e4df1fc0`) |
| 3 | P3 桩走查(四时刻链路 + 回归两场景) | Done (PASS, 桩保真度局限已记) |
| 4 | P4 收尾回写(pitfalls / 常青文档 / 切片 / 基线 / 计划标 Done) | Done (留工作区) |
| 5 | 真机复核(需真实 qB 与扩展在线, 走计划 Step 4 场景) | Open |

## 进度日志

- **2026-10-03 计划轮**: 判定链路取证(record/rules_mod/tracker_mod/resolve/views/webui runtime + hr runtime/worker/service), 排除项六条逐一验证(热重载时序 / HrRuntime.apply / worker 冷启动发布 / loaders 派生填充 / WebUI 无字段缓存 / 热重载当下置脏均已正常), 计划文档产出, 未动代码。
- **2026-10-03 P1**: `TrackerModule.apply(old,new)` 落地 —— `old.trackers != new.trackers`(整段按值比较)即遍历 `store.by_hash` 中 `tracker_conf is not None` 的记录执行 `rec.tracker_conf = self.match(rec)`; 相等短路零动作; `ctx.api.client is None` 跳过不抛(留给下轮 full_round / L2 兑现)。test_tracker.py 三新用例(存量绑定重绑+回执 / client=None 防御 / 相等短路), 红验过。提交 `2a5d07a2`。顺带修好: `hr` 规则段热重载生效 + `_anchors()` 锚点收集恢复。
- **2026-10-03 P2**: `WebUIRuntime` 补 HR 判定新鲜度机关 —— 重建完成时记 `self._hr_rev_at_build = hr.revision`(挂 `_publish_locked` 末尾, 判空防御); `flush_views` 比对当前 `hr.revision` 与基线, 不等即 `mark_dirty()`; 基线随重建前移, 无循环置脏。test_web.py 两新用例(直推 publisher 抬 revision → flush 置位 group_view_dirty / 重建后基线前移不再置脏), 红验过。提交 `e4df1fc0`。
- **2026-10-03 P3**: 桩走查四时刻链路 PASS —— t0 不重启「本地·达标」→ t1 热重载回执 `tracker:rebound 6` + `hr_check` 就位 → t2 revision 1→2 触发置脏重建 → t3「在线·已达标」; 回归: 无关段热重载无 rebound(短路生效)、重启路径正确。test.quick 2314 passed / 3 skipped / 0 failed。桩保真度局限: 判定桥手工接线、t2 取数为直推 publisher 模拟。
- **2026-10-03 P4**: 收尾回写 —— 新坑档 [pitfalls/backend/hot-reload-stale-bindings-derived-views.md](../pitfalls/backend/hot-reload-stale-bindings-derived-views.md)(两教训合写: 换 Config ≠ 存量绑定自动更新 + 非快照字段派生值要显式置脏); 常青文档回写(systemPatterns/web-runtime.md 置脏源两处 / modules/core-runtime.md TrackerModule 职责); activeContext 完成条目迁 progress; 基线切片新建(数字见 kb.baseline); 计划标 Done; 本档案立档 + 索引重建。
