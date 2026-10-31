# 2840 —— 空存储提示改道通知面板 + 面板改名「通知」

> 摘要: 列偏好空存储提示的出口由"运行时注入 body 的 fixed 横幅"改为**通知面板条目**(新单点 `ui_feedback.js::_recordNotice`), 面板可见文案统一改「通知」。改动: `shared/columns.js`(去 DOM 注入, 文案与两层去重标记不动)、`shared/ui_feedback.js`(新增 `_recordNotice`)、`shared/tpl/overlays.html` + `shared/tpl/statusbar.html`(可见文案)、前端 static 注释统一(仅注释)。守阵: 新增 2 个静态测试函数 + 既有入口守阵补 3 条文案断言; 真浏览器 1 皮肤验证 + `dev.e2e` fast 子集。
> 档案: memory-bank/tasks/26-10-09-webui-notice-panel-exit.md
> 基线时间: 2026-10-09 11:37

**Refs:** memory-bank/tasks/26-10-09-webui-notice-panel-exit.md

## test.full 实测

- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测**: **2840 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**(16553 语句 / 169 未覆盖 / 5708 分支 / 145 partial; 门槛 98% 达标)
- **耗时**: 28.75s(命令总耗时 30.7s)
- **新增测试**: 2 个静态守阵函数 —— `tests/test_webui_error_history.py::test_frontend_notice_push_wired`(通知单点三处接线: 写 `_errHistory` / cap 裁剪引用 `ERR_HISTORY_CAP` / 计未读 + `source`/`kind` 标记 + **不得建 DOM**)、`tests/test_webui_static_dom_page.py::test_frontend_cols_empty_hint_is_not_a_floating_banner`(提示体内禁 `document.createElement` / `appendChild` / `position:fixed` / `z-index:9999`), 两者均已登记进各自文件头部「测试计划」; 另**改写**既有入门守阵 `test_frontend_error_history_entry_wired`(补面板标题/入口 title/空态三处「通知」文案断言)。
- **e2e**: `commands run dev.e2e`(fast 子集) **18 passed**(含 `views.spec.mjs` 的"Vue 挂载成功、无运行时错误"断言)—— 该新链路(空存储提示 → 面板条目)在浏览器侧的落点由一次性桩验证覆盖(浮层横幅计数 0 / 徽标 1 / 面板标题「通知」/ 行 `err-row info` / 文案逐字一致 / 零 pageerror), 未固化为 e2e 用例。

## 说明

- 提示文案、两层去重标记(sessionStorage + localStorage)、面板收集时机(emit 即收 + settle upsert)、cap、后端错误环(`/api/errlog`)与补拉定时器**全部未动** —— 本基线只测"出口形态 + 可见文案"这一处改动面。
- 内部标识符(`err-panel` / `.sb-err` / `_errHistory` / `errPanelOpen` / `ERR_HISTORY_CAP`)刻意未改名, 守阵与后端语义仍钉旧名。
