# 2961 —— WEBUI 非活跃种子禁强制汇报(qB 口径四入口接线)基线

> 摘要: 用户要求「WEBUI 非活跃状态的种子不允许强制汇报, 包括右键/详情面板, 按钮变灰不可点击, 与 qb 的行为保持一致」。口径(用户三项拍板)= ①「非活跃」与 qB 完全一致(qB commit `aa189a7` 关闭 issue #12080: `isPaused` / `isChecking` / `isQueued` 时 `actionForceReannounce->setEnabled(false)`, tooltip 原文 "Can not force reannounce if torrent is Paused/Queued/Errored/Checking" ⇒ 暂停/停止 · 排队 · 校验中 · 错误/文件丢失); ②多选/整组/整集**全部目标都非活跃才置灰**(与 qB `oneCanForceReannounce` 的"任一活跃即可用"同口径); ③键盘快捷键一并拦截。落点: 判定单点 `shared/decorate.js` 新增两张表 + `reannounceBlocked/reannounceTargetsGate/reannounceMenuGate/drawerReannounceGate`; 显示层 `tpl/ctx-menus.html` 四支置灰(`.is-gated` + title 原因)+ `drawer_tpl/04|05|06` 重报钮置灰 + 三处 `.is-gated` CSS; 行为层 `commands.js::_guardReannounce`(接在 `_actCore` 的 reannounce 前置)+ `shortcuts.js::_kbAct`(早于确认框)+ `drawer.js::torrentCmd` 兜底。9 个源文件 + 1 个测试文件(新增守阵 1 个测试函数, 含 node 电池真跑 24 项)。命中立档阈值(改动 ≥3 源文件), 已立档 `tasks/26-10-10-webui-reannounce-inactive-gate.md`。
> 基线时间: 2026-10-10 20:04

**Refs:** memory-bank/tasks/26-10-10-webui-reannounce-inactive-gate.md,memory-bank/activeContext/26-10-10-2004-webui-reannounce-inactive-gate.md,memory-bank/pitfalls/web-ui/reannounce-inactive-gate.md

## test.full 实测

- 分支: `develop`(会话开工 `my-commit-flow.sync` 核验 `206eb7d6`; 工作树含本轮改动 + 回写件时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测 (Windows)**: **2961 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16568 语句 / 165 未覆盖 / 5716 分支 / 142 partial; 门槛 98% 达标; 三次采样 28.28s / 29.09s / 39.50s,
  后一次是收尾轮机器同时跑 e2e 桩的负载差异 —— 单次采样波动大, 只作量级参考)
- 增量明细(本轮真正新增): `src/auto_qb/webui/static/shared/decorate.js`(判定单点 + 四入口共用闸门方法)/ `commands.js`(`_guardReannounce` + `_actCore` 前置)/ `shortcuts.js`(`_kbAct` 先拦后确认)/ `drawer.js`(`torrentCmd` 兜底)/ `tpl/ctx-menus.html`(四支置灰)/ `drawer_templates.js`(核心注入的 `.is-gated` 并集 `> .ico`)/ `drawer_tpl/04|05|06`(重报钮置灰 + 各自 `.is-gated` CSS); `tests/test_webui_static_dom_panel.py` 新增守阵 `test_frontend_reannounce_inactive_gate_wiring`(收集面 +1); `e2e/menus.spec.mjs` 新增「块E 强制汇报可用性」(`@fast`, 双皮肤 2 条); 回写件 `progress/implemented-webui.md` 新条目、`pitfalls/web-ui/reannounce-inactive-gate.md`(新条)、切片/档案/本基线切片。
- 静态守阵红验: 临时删掉 `decorate.js` 状态表的 `queuedDL`/`queuedUP` 两项 → 守阵报
  `AssertionError: decorate.js 非活跃状态集缺 qB 状态 queuedDL(qB 口径漏项)`(1 failed, 1 passed);
  还原即绿(2 passed) ⇒ 守卫有效。
- 真浏览器冒烟(`@fast` 门禁): `commands run dev.e2e -- --grep @fast` **48 passed(1.2m)** ——
  含两皮肤「渲染健康: Vue 挂载成功、分组行渲染、无运行时错误」(置灰判据从模板与变体 JS 里调方法,
  渲染期报错会被这条抓住)+ 新增块E 双皮肤(非活跃行置灰 + 提示给原因 + **真实点击零 reannounce 请求** +
  error toast; 活跃行对照不置灰, 行状态用真实 DOM 类 `.torrent-row.s-paused` 选, 不借 vm 造数据)。
- e2e 红验(行为层): 临时摘掉 `commands.js` 的 `_actCore` 闸门行 → 块E 两皮肤各报
  `非活跃种子点击强制汇报不得发出任何 reannounce 请求: Expected 0 / Received 1`(2 failed);
  还原即绿(2 passed) ⇒ "置灰只改样式、行为层才是真闸"这层断言有牙。
