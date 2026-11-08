# ui-harness-relocate-inject

> 摘要: 修桩补灌 relocate job 快照: issue 26-11-06-0330 恒红转绿(views.spec 36 全绿), 坑档 stubs-sim 记第 4 例
> 最后活动: 2026-11-06 05:40
**Refs:**

**R0(2026-11-06 05:12):** 修桩补灌 relocate job 快照: issue 26-11-06-0330 恒红转绿(views.spec 36 全绿), 坑档 stubs-sim 记第 4 例
- 真机自检: 豁免 —— 改动仅在 dev-only 桩脚本(scripts/ui_harness.py), 无产品代码路径, 纯桩可验。
- 验证面: views.spec.mjs 36 全绿; 全量 e2e 430 passed(2 failed = gtm-alert 存量, stash 对照 HEAD 同红, 非本轮引入); pytest 全绿(见 kb.baseline)。
- 计划外发现: gtm-alert 双皮肤存量恒红(@fast 标签), 按范围守恒未动, 已报告待用户裁决处置。
- 后续闭环: gtm-alert 确认 = issue 26-11-06-0330-test-e2e-gtm-alert-date-bomb(日期炸弹), 远端 33b43d0d 已修; 同步 f0883292→fa1aff30 后复跑双皮肤 2 passed 转绿。

**R1(2026-11-06 05:40):** 收口评审(全能档): blocker 0, 修 2(minor 加 len<4 守卫 + nit 切片措辞改组级聚合语义), 入池 0; 引文校验 1 PASS 1 REFUTE(行号偏移弃)
