# 2962 —— WEBUI 强制汇报混选投递收敛(非活跃目标不再投递, 也不再假报「未确认」)基线

> 摘要: 承 20:04 那轮的后续轮。用户追问「多选时"任一可汇报即可用", 目前的方案会不会导致混选时汇报非活跃种子?」—— 查证后**成立**, 但危害不在"汇报"(qB 引擎本来就空转), 而在**我们自己的确认层**: 闸门是集合级全有全无(`_reannounceVerdict` 的 `rows.some(...)`), 混选放行后 `_actCore` 对集合内**全部**目标投递, 非活跃目标进 `_register_reannounce_pending` 后引擎空转 ⇒ tracker 永不前跳 ⇒ 白等到 item deadline(上限 600s)落「未确认」, 前端三桶聚合把一次干净的成功报成 `成功 1, 未确认 3`。qB 的 GUI 没有 per-target 回执, 故 qB 上不会显出这个问题。**用户三项拍板**: ①收敛为活跃子集; ②前后端双保险; ③回执体现跳过数。落点: 前端新单点 `decorate.js::reannouncePlan`(解析面与闸门同源 `_findGroup`/`memberByHash`, 组目标展开为活跃成员 hash; 组/hash 解析不出则原样交回, 不静默丢目标)+ `commands.js::_actCore` 按计划投递(目标计数改用实际投递数, 文案在跳过数非零时缀「跳过 N 个非活跃」; 空投递显式收口, 不再落成功分支报「成功 0 个目标」)+ 后端模块级 `REANNOUNCE_BLOCKED_STATES` 与 `reannounce_blocked()`(`commands.py`, 第二道闸: `_reannounce_active` 过滤 + 全非活跃给显式 warn 回执 + 单种非活跃即回执不发指令)。⚠ 关键坑: 后端**不能**拿 `state_enum` 谓词当判据 —— 实测 `queuedDL/queuedUP` 命中 `is_downloading/is_uploading`(只有 `paused*/stopped*` 是 `is_stopped`、`error/missingFiles` 是 `is_errored`), 必须判 qB 原始 `state` 串。测试桩 `helpers.py` 补 `reannounce_hashes_calls`(同 `recheck_hashes_calls` 模式, `calls` 里 `("reannounce", None)` 旧约定不动)。
> 基线时间: 2026-10-10 20:32

**Refs:** memory-bank/tasks/26-10-10-webui-reannounce-inactive-gate.md,memory-bank/activeContext/26-10-10-2004-webui-reannounce-inactive-gate.md,memory-bank/pitfalls/web-ui/reannounce-inactive-gate.md

## test.full 实测

- 分支: `develop`(工作树含本轮改动 + 回写件时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测 (Windows)**: **2962 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16586 语句 / 165 未覆盖 / 5724 分支 / 144 partial; 门槛 98% 达标; 本轮 25.0s)
- 增量明细(本轮真正新增): `src/auto_qb/webui/static/shared/decorate.js`(`reannouncePlan` 投递计划单点)/
  `commands.js`(`_actCore` 按计划投递 + 跳过数文案 + 空投递收口)/ `src/auto_qb/webui/commands.py`
  (模块级 `REANNOUNCE_BLOCKED_STATES` + `reannounce_blocked()` + `REANNOUNCE_INACTIVE_SKIP` +
  `_reannounce_active()` + 两个 `_cmd_reannounce_*` 过滤 + `_register_reannounce_pending` 的 `is_stopped`
  直判降级注记)/ `tests/helpers.py`(`reannounce_hashes_calls` 平行记录); `tests/test_web_commands.py`
  新增 `test_reannounce_skips_inactive_targets` + 改造 `test_reannounce_register_immediate_verdicts_and_deadline`
  (收集面 +1); `tests/test_webui_static_dom_panel.py` 守阵扩段(投递收敛接线 + 前后端同表 + node 电池项
  +10)/ `e2e/menus.spec.mjs` 新增「块E 混选放行但只汇报活跃目标」(`@fast`, 双皮肤) 且 `reannounceTap`
  增采目标 hash; 回写件 `progress/implemented-webui.md` 新条目、坑档新增一节、切片/档案/本基线切片。
- 静态守阵红验(三轮, 均还原即绿):
  - 摘掉后端 `_reannounce_active` 的过滤(改 `return list(hashes)`) → `test_reannounce_skips_inactive_targets`
    报 `AssertionError: 组汇报未收敛为活跃子集: [['HA', 'HB']](排队成员也被投递了)`。
  - 只在前端表多加一项 `fooDL`(①覆盖断言仍过, 专门验漂移守卫) → 报
    `AssertionError: 前后端非活跃判据表不一致(... fooDL ...)`。
  - 从前端表删掉 `stoppedUP` → 报 `AssertionError: decorate.js 非活跃状态集缺 qB 状态 stoppedUP(qB 口径漏项)`。
- node 电池: 直接跑 `_NODE_REANNOUNCE_GATE_PROBE` = **34/34 过**(上轮 24 项 + 本轮 10 项投递计划用例:
  组混合只投活跃成员/跳过计数/组解析不出交回组端点/单种非活跃收敛/hash 解析不出照发/组内成员与 hashes
  重叠去重/空成员组计划为空/空入参不抛)。
- 真浏览器(`@fast` 门禁): `commands run dev.e2e -- --grep @fast` **50 passed(1.1m)**(上轮 48, +本轮混选
  双皮肤 2 条)。桩 `ui_harness` 是 300 种子 / 150 组 ⇒ **选中两行会落在同一组**, 这正是混选断言必须按
  **hash** 落而不能数请求条数的原因(组目标会被展开为整组的活跃成员)。
- e2e 红验(行为层): 把 `_actCore` 的 `this.reannouncePlan({ keys, hashes })` 临时退化为
  `{ keys, hashes, skipped: 0 }`(复刻收敛前形态) → 混选用例双皮肤各报
  `Expected value: not "…012b" / Received array: ["…012b", "…012a"]` —— 非活跃目标确实被投递了。
  还原即绿。
- 未纳入本轮的相邻面(刻意不越界): 规则侧 `rules/actions/transfer.py::ReannounceAction` 只跳
  `is_stopped`(不跳排队/校验中/错误), 与 qB 口径不一致 —— 属另一入口, 未改, 见档案「后续候选」。
