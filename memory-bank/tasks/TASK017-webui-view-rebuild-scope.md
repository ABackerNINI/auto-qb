# TASK017 — WEB UI 视图重建范围收口 (种子速度刷新滞后)

**Status:** In Progress (代码/测试/文档已完, **未提交**; 剩用户真机走查)
**Started:** 2026-09-18
**Owner:** 主线 (单会话连续实施)
**Plan doc:** [docs/plans/26-09-18-1743-webui-speed-refresh-fix-plan.html](../../docs/plans/26-09-18-1743-webui-speed-refresh-fix-plan.html)

## 原始请求

> WEBUI种子的下载/上传速度更新慢, 但状态栏速度更新正常, 分析原因, 列一个修复计划

用户随后下令「实施」—— 本档案覆盖诊断 + 实施全过程。

## 思考过程与决策

- **先把"速度"这个数字的全链路出口列全(关键第一步)**: 同一屏上的"速度"其实有**两个数据源** ——
  ①状态栏「下载/上传速度合计」= `Σ groups[].dlspeed`(`app.js` 的 `totalDl`/`totalUl`);
  ②种子页行内速度 = `state.torrents[].dlspeed`(后端 `_flat_view`);
  另有统计面板的 `server_state.dl_info_speed`(走 `/api/stats`, **不受 rid 门控**)。
  列完表后立刻看出: ①与②分属**不同视图对象**, 而二者的门控方式完全不同 —— 这解释了"同一屏上一个新鲜一个滞后"。
- **探针实测(确定性复现, 不靠猜)**: 用仓库既有替身 `tests/helpers.make_manager` + `FakeClient`
  起真 `QbManager`, 每轮 tick 前改 `FakeTorrent.dlspeed`, 交替执行「`mgr._tick()` → `mgr.ensure_group_state(rid)`」,
  打印 `_group_view_ver` / `_group_view_dirty` / `_flat_view` / `store.by_hash` 四路真值。结果:
  ```
  grouping.enabled=True   t2: ver 自增 updated=True  回传 flat=[]  | store 真值 dlspeed=999/888
  grouping.enabled=False  t2: ver 不变 updated=False 回传 flat=[]  | store 真值 dlspeed=999/888
  ```
  **判据**: 版本号在自增但回传数组没变 ⇒ 该视图被"饿死"。
- **根因(主因)**: 两条重建路径**范围不一致** ——
  `QbManager._tick` 只 `_build_group_view()` 就把**共享**的 `_group_view_dirty` 清掉;
  `WebviewMixin.ensure_group_view` 会重建全部四份(groups/singles/shows/flat), 但前置条件是"标记仍为真",
  而主循环已把它清了 ⇒ 兜底永不触发。
- **同源第二坑**: `_tick` 里 `consume_view_changed()` 在 `if grouping.enabled` **块外**读走标记,
  唯一的置脏语句却在**块内** ⇒ 分组关闭时标记被吞, 版本号不再变化 ⇒ 前端 `updated=false` 并退避轮询。
  本质是**把"分组是否启用"错当成"Web 视图是否需要维护"** —— 种子页的平铺视图与分组功能无关。
- **放大器**: 前端 `currentPollMs()` 按 `idlePolls`(连续 `updated=false`)退避 2s→5s→10s,
  而状态栏走 `/api/stats` 恒回传 ⇒ 两个速度来源刷新频率被解耦, 观感被放大成"只有种子行慢"。
- **决策 1(修法)**: 收敛为**唯一重建入口** `WebviewMixin.rebuild_views()`, 两条路径都只调它;
  而不是在两处各打补丁 —— 否则新增第五份视图还会漏。
- **决策 2(门控)**: 置脏移出 `grouping.enabled` 门控(脏标记是共享状态), 门控只留给"要不要在主循环花 CPU 重建"这一个决策。
- **决策 3(前端)**: 取消 idle 退避(版本未变时响应体本就趋近于零, 退避省不下什么却牺牲新鲜度),
  并把 `server_state` 并入 `/api/state.status.server` ⇒ 状态栏与行数据**同源同轮**, 请求数不升反降(每轮 1 条)。

## 实现计划

| # | 动作 | 文件 |
|---|---|---|
| P0-1 | 新增 `rebuild_views()`(四视图 + 版本号 + 清标记一次完成)作唯一入口 | `mixins/web_view.py` |
| P0-2 | `ensure_group_view` 改调 `rebuild_views` | `mixins/web_view.py` |
| P0-3 | `_tick` 置脏移出 grouping 门控, 重建改调 `rebuild_views` | `qbmanager.py` |
| P1-1 | 取消 `idlePolls` 退避, 只留失败退避 | `shared/app.js` |
| P1-2 | `status.server` 并入 `/api/state`, `syncStats()` 退役 | `web.py` + `shared/app.js` |
| P2-1 | 改写 2 条固化缺陷的用例 + 新增 3 条回归用例(红绿验证) | `tests/test_qbmanager.py` / `tests/test_web.py` |
| P2-2 | pitfalls / systemPatterns / modules / testing / activeContext / progress 回写 + 立档 | `memory-bank/` |

## 子任务状态表

| 子任务 | 状态 | 备注 |
|---|---|---|
| P0-1 ~ P0-3 视图重建收敛 | ✅ | `rebuild_views()` 已落地, 两条路径同源 |
| P1-1 取消 idle 退避 | ✅ | 轮询恒定 `pollSec` |
| P1-2 `server_state` 并入 `/api/state` | ✅ | 每轮 1 条请求, 状态栏与行数据同源同轮 |
| P2-1 测试(改写 2 + 新增 3) | ✅ | 旧代码上 5 条全红, 修复后全绿 |
| P2-2 文档与立档 | ✅ | 基线 1018 → **1021 passed / 0 failed** |
| 用户真机走查 | ⏳ | 种子页速度应每 2s 连续变化; 关分组再走查一次 |

## 进度日志

- 2026-09-18 17:43 — 诊断完成并交付修复计划 `docs/plans/26-09-18-1743-webui-speed-refresh-fix-plan.html`。
- 2026-09-18 19:2x — 用户下令实施; P0/P1 改动完成, `node --check` 通过。
- 2026-09-18 19:3x — P2 测试完成: 改写 `test_tick_rebuilds_all_views_when_changed` /
  `test_tick_rebuilds_views_when_grouping_disabled`; 新增 `test_flat_view_refreshed_by_main_loop_tick` /
  `test_rebuild_views_single_entry_point` / `test_api_state_status_carries_server_state`。
  **红绿验证**: 把 `_tick` 临时还原成旧写法后 5 条新/改用例全部失败(如 `(0,0,0,0) != (1,1,1,1)`、
  `assert [] == [100, 200]`), 恢复后全绿。
- 2026-09-18 — 全量 `uv run pytest tests -q --no-cov` → **1021 passed / 0 failed**; 知识库回写 + 立档完成; **未提交**。
- 2026-09-18 — **CPU 风险实测(计划里点名的唯一顾虑: 去掉 grouping 门控后主循环每 tick 多建 3 份视图)**:
  用 `helpers` 造 200/1000/3000 个种子跑 `rebuild_views()`, 单次耗时 **4.97 / 25.22 / 79.36 ms**,
  占 2s tick 预算 **0.25% / 1.26% / 3.97%**(且仅在"Web 活跃 + 视图真有变化"时才发生)。
  ⇒ 门控可以安全去掉, 不需要给 shows/flat 单独加节流。
