# 26-10-08-webui-perf-issues-closing — 三条 perf issue 定案 / 重归因（含 e2e 与仿真复测）

**Status:** In Progress
**Added:** 2026-10-08
**Updated:** 2026-10-08
**Summary:** 用户命题「最近进行了重构, 分析这三个性能相关 issues 是否已经解决」→ 只读裁定 → 用户指令「按照建议执行 1/2/3」。本轮落地三条: ①`26-10-01-2218-perf-webui-api-state-full-scan` 定案 **Done**（方向①②由增量同步计划 26-10-07-0414 兑现并有实测数字；方向③分页/按需字段未实施，转新件 `26-10-08-0411-perf-webui-api-state-pagination`）；②`26-09-21-1408-perf-webui-shows-view-full-rebuild` 定案 **Done**（补跑全量 `dev.e2e` **94 passed / 10 skipped / 0 failed**，S10 记录的 6 条存量失败已清零，三点现象复验均为已消失）；③`26-10-01-2218-perf-mainloop-max-tasks-adaptive` **未解决但已重归因 + 复测**：P2 同场景重跑稳态间隔 2.87→**2.139 s**、最大漂移 1.22→**0.801 s**（已进 `SYNC.drift_max_s ≤ 1.0` 稳态门限内），且认定原方案「给 `max_tasks_per_tick` 做自适应」指向的旋钮不承载该成本（灌入期每新种子 2 次内联请求跑在同步线 `_refresh_torrents`，不受任务线配额约束），改道为「灌入期每拍请求预算」并给出「倾向不做 / 走 Dropped」的判断 —— **状态保持 Open，等用户拍板**。
**Topics:** webui-perf-issues-closing

## 进度日志引用点

增量收益数字与 S10 归档结论的单点在 `memory-bank/tasks/26-10-07-webui-delta-sync-feasibility.md`（其 **Refs:** 已对本件反向声明）与 `memory-bank/plans/26-10-07-0414-plan-webui-delta-sync.html`，不在此复述。
**Refs:** memory-bank/issues/26-10-01-2218-perf-webui-api-state-full-scan.html, memory-bank/issues/26-09-21-1408-perf-webui-shows-view-full-rebuild.html, memory-bank/issues/26-10-01-2218-perf-mainloop-max-tasks-adaptive.html, memory-bank/issues/26-10-08-0411-perf-webui-api-state-pagination.html, memory-bank/tasks/26-10-07-webui-delta-sync-feasibility.md, memory-bank/testing/baselines/26-10-08-0427-webui-perf-issues-closing.md

## 原始请求

用户: 「最近进行了重构, 分析这三个性能相关 issues 是否已经解决: 26-10-01-2218-perf-webui-api-state-full-scan.html / 26-09-21-1408-perf-webui-shows-view-full-rebuild.html / 26-10-01-2218-perf-mainloop-max-tasks-adaptive.html」
随后指令: 「按照建议执行 1/2/3」。

## 思考过程与决策

- **裁定前先重锚**：三条 issue 的锚点整体漂移（`runtime.py:775→1124`、`views.py:412→800`、`state.py:33→35`），按「符号名 + grep」重定位后再比对，不凭行号下结论。
- **"已解决"要拿实测数字，不能看代码像不像**：增量同步计划 S10 基线切片里已有桩口径实测（delta 载荷 1,809 B ≈ 全量 1/4800、HTTP delta ~4 ms / 零回传 ~2 ms vs 全量 93.8 ms@3000、前端 delta 29-43 ms vs 全量 562-816 ms@3000），直接引用而不重造。
- **范围守恒**：api-state 的方向③（分页/按需字段）没做，不塞进"已解决"的结论里 —— 单独入池新件，并在原件的状态日志里写明"转新件跟踪"，避免"状态 Done 但残留项无人认领"。
- **e2e 复跑是第 2 条的定案前置**：S10 归档时 6 条存量失败的根因 A/B 分别在 `312165f8`、`17dc0fc7` 修掉，但**修在归档之后**，归档里只有"修复后应回 92"。故本轮补跑全量 `dev.e2e` 取实数（实测 **94 passed**，比预期多 2 —— 期间另有新增用例）。
- **第 3 条不做"自适应"，改做重归因**：先查 `max_tasks_per_tick` 是否已被改（没有，仍是静态 20 / 校验 1..500），再查它是不是有效旋钮 —— `memory-bank/testing/sim-5000.md` 的实测原文已写明灌入期每新种子 2 次内联请求**不受它约束**。于是把"实施"换成"重归因 + 取新数字"，由用户按新数字拍板值不值得做。
- **仿真复测绕开固化基线**：`sim_baseline.py` 不带 `--merge` 会**整体覆写** `plans/…baseline.json`（只跑 P2 会把 `P1.first_round_s` 阈值按 ramp 数字重算，污染硬判据）。故改为直接跑它 dry 打印出的那条 `sim_run.py` 命令 —— 同数字、零副作用。
- **沙箱**：仿真工作根固定 `R:\auto-qb-sim`（工作区外），首次被沙箱拦（PermissionError WinError 5），经用户放行后跑通 —— 下次同场景复测直接申请放行即可。
- **不编数字 / 不过度归因**：P2 复测只说明"同一场景同一 main_tick=2s 下漂移从 1.22 降到 0.801"，**不**断言是某次重构带来的（分层节拍等提交与取证同日，无法定因果）；残留 0.801 s 的构成拆分列入"仍待查"。

## 实现计划

1. 开工同步（`cb0fd149`→`0a46b58d`，远端领先 2 笔快进）。
2. 装前端依赖（`npm install`，`@playwright/test` 缺失导致 `dev.e2e` 直接 ERR_MODULE_NOT_FOUND）→ 跑全量 `dev.e2e`。
3. 入池方向③残留件（create-issue skill，standard 档）+ 填五段正文。
4. api-state 原件定案 Done：改徽标 + meta + 追加状态日志 + 补"实际修法 / 验证方式 / 测试数字" + 重锚。
5. shows-view 原件定案 Done：同上，附本轮 e2e 实数。
6. mainloop 原件重归因：改标题 / 摘要 / 现象 / 证据（贴复测原文 + 新旧对照表）/ 影响面（严重度中→低）/ 锚点 / 根因（写"已排除"）/ 建议修法（改道 + 值不值得做判断）/ 状态日志与待拍板。
7. P2 场景同参数重跑取数（`sim_run.py`，不碰 baseline.json）。
8. `kb.index` + `kb.check`；跑 `test.full` 出基线切片；立本档案 + activeContext 切片。

## 子任务状态表

| 子任务 | 状态 | 备注 |
|---|---|---|
| 1 开工同步 | ✅ 完成 | `0a46b58d` |
| 2 前端依赖 + 全量 e2e | ✅ 完成 | **94 passed / 10 skipped / 0 failed**（3.5m） |
| 3 方向③残留件入池 | ✅ 完成 | `26-10-08-0411-perf-webui-api-state-pagination`，Open |
| 4 api-state 定案 | ✅ 完成 | → **Done** |
| 5 shows-view 定案 | ✅ 完成 | → **Done** |
| 6 mainloop 重归因改写 | ✅ 完成 | 状态仍 Open，等拍板 |
| 7 P2 仿真复测 | ✅ 完成 | 稳态 2.139 s / 漂移 0.801 s，verdict OK |
| 8 收尾（索引 / 机检 / 基线 / 档案 / 切片） | ✅ 完成 | 见进度日志 |
| 9 第 3 条 Dropped 拍板 | ⏳ 待用户 | 拍板后由 agent 改状态 + `kb.index` |

## 进度日志

- **2026-10-08 04:10** 同步 → `0a46b58d`。`dev.e2e` 首跑失败（`@playwright/test` 未装）；`npm install`（5 包）后重跑：**94 passed / 10 skipped / 0 failed**（3.5m）—— S10 归档记录的 6 条存量失败（根因 A 桩 `FakeTorrent.to_dict` 未跳过 `hr_link` ⇒ 详情端点恒 500 ×4，已由 `312165f8` 修；根因 B S7 WeakMap 令 `applyOptimistic` 原地变更不传导 ⇒ ×2，已由 `17dc0fc7` 修）已清零。
- **2026-10-08 04:11** 入池 `26-10-08-0411-perf-webui-api-state-pagination`（perf / standard / topic `webui-polling`），正文五段 + 建议三案（B 按需字段 / C hash 引用式 / A 分页）与"先做全量轮成本构成拆分再选"的前置。
- **2026-10-08 04:15** 两条 issue 定案 Done（徽标 + meta 双改 + 状态日志 + 修复后补充段），api-state 的 §05 锚点节补 2026-10-08 重锚行。
- **2026-10-08 04:19** P2 复测（`uv run python scripts/sim_run.py --scenario P2 --n 5000 --duration 50 --ramp 200 --web-port 18201`；生成 config `main_tick: 2S` / `max_tasks_per_tick: 20`，与原取证同口径）：verdict OK，rounds=24 / full=1 / avg_interval=**2.139 s** / drift_max=**0.801 s** / avg_bytes=487202，写 4299.6/min（`≤6210.49` PASS），`P1.first_round_s` 2.174（`≤22.68` PASS），tracebacks=0 / critical=0。产物 `R:\auto-qb-sim\runs\20261008-041959-P2`。据此改写 mainloop 件（严重度中→低，改道"灌入期每拍请求预算"，给出"倾向不做 / 走 Dropped"判断）。
- **2026-10-08 04:27** `kb.index`（20 个生成物）+ `kb.check` 全绿（主键纪律 / 认领链双向闭环 / 回写措辞 / 日期守卫均 OK；切片数 93 > 70 的 cap 债务为存量，按范围守恒本轮不修）；`test.full` 见基线切片；立本档案 + activeContext 切片。

## 待办（下一轮）

- 用户拍板：mainloop 件走 **Dropped**（理由：复测已进稳态门限 + 原方案无效 + 症状为一次性代价）还是维持 Open 做"灌入期每拍请求预算"。
- api-state 残留件（分页）与 `26-10-07-1420` 组行 hash 引用式的先后拍板 —— 两者都要动响应体形状，建议一起排。
