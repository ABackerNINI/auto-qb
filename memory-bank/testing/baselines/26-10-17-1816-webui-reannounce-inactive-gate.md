# 3537 passed + 4 skipped(根) —— webui 删除链接入 reannounce-inactive-gate(issue 26-10-17-1703)

> 摘要: webui 删除链接入 reannounce-inactive-gate(issue 26-10-17-1703)
> 基线时间: 2026-10-17 18:16
**Refs:** memory-bank/tasks/26-10-10-webui-reannounce-inactive-gate.md, memory-bank/issues/26-10-17-1703-bug-webui-delete-reannounce-paused.html

## 验收数字

`commands run test.full` 实测(2026-10-17 18:1x, 本机):

- 汇总行: **3537 passed, 4 skipped**(50.87s)
- TOTAL 覆盖率: 17987 statements / 263 missed / 6098 branches / 190 partial / **98%**(闸门要求 98%, 达标)

## 本改动面

- 前端: `static/shared/delete_flow.js`(闸门 `_deleteReannounceGate` + `_confirmDelete` 接 gate + `_deleteFlow` 按 `reannouncePlan` 收敛 + `_reannounceAll` skip 桶 D4/D6 + 模块级 `_reannounceWarnInactive`); `static/shared/tpl/popovers.html`(opt-pill `is-gated`/title/点击短路); `static/shared/ui_feedback.js`(checks 形状注释); 三套皮肤 `components.css` + atlas `dialogs.css`(`.opt-pill.is-gated` 置灰, 压过 `:hover`)。
- 后端: 无(第二道闸判据/回执原样正确, 见 issue §05 已排除项)。
- 测试: `tests/test_webui_static_dom_panel.py::test_frontend_reannounce_inactive_gate_wiring` 扩段(⑦ 删除链静态接线 + node 电池 +46 项含闸门/skip 分型); `scripts/ui_harness.py` 命令泵按 state 判活跃(非活跃 reannounce 回 warn); `e2e/menus.spec.mjs` 块E 新增两条(@fast: 全暂停零请求且删除成功 / 混选只投活跃)。
- 验证: node 桩重放(修复前复现/修复后转绿)+ 三轮红验(静态 JS 关键词 / 模板 is-gated / e2e 投递收敛)+ e2e 双皮肤 4/4 + 本文件级 46/46 + KB 守卫 120/120。
