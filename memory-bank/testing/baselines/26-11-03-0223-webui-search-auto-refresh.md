# 4919 passed + 2 skipped(根) —— WEBUI 搜索自动更新(P0-P4)收尾基线

> 摘要: WEBUI 搜索自动更新(P0-P4)收尾基线
> 基线时间: 2026-11-03 02:23
**Refs:** memory-bank/plans/26-11-03-0120-plan-webui-search-auto-refresh.html

## 验收数字

`commands run test.full`(2026-11-03 02:23 实测, 158.50s):

| 指标 | 值 |
|---|---|
| 通过 | 4919 passed |
| 跳过 | 2 skipped |
| 警告 | 3 warnings |
| 覆盖率 TOTAL | 134 行未覆盖 / 7736 分支部分 / 128 分支未覆盖 / 99% |

口径: 全量一轮(Memory Bank 守卫+HTML 守卫在内); 数字仅本切片为事实源。

## 本改动面

- 服务端: `src/auto_qb/webui/runtime.py`(S1 `search_rev` + `note_search_data_changed`)、`src/auto_qb/core/qbmanager.py`(S2 触发面 `_SEARCH_TRIGGER_FIELDS` + 主循环自增)、`src/auto_qb/webui/server/routes/state.py`(S3 status 回传)、`src/auto_qb/webui/views.py`(S4 响应 `rev`, 快照前取值)。
- 前端: `static/shared/state.js`(F1 自动刷新状态域)、`view.js`(F2 quiet 分支/rev 对齐/提示计数/冷却常量 2000ms)、`polling.js`(F3 `_maybeSearchRefresh`)、`tpl/topbar.html`(F4 `search-refresh-note` 提示)。
- 测试/桩: `tests/test_qbmanager.py`(+2 例)、`tests/test_web_hr.py`(+2 例, 2 处精确 dict 断言补 `rev`)、`tests/test_webui_static_skins_widget.py`(+1 静态守阵)、`tests/test_webui_static_dom_page_store.py`(doSearch 正则放宽)、`scripts/ui_harness.py`(桩控制端点 add/remove_torrent)、`e2e/search-auto-refresh.spec.mjs`(新建, 三皮肤 6 例)。
- 文档: 计划 `26-11-03-0120` 回填 §08 实测/§09 状态/§10 R1; 坑档 `pitfalls/web-ui/search-pending-collapse.md` 补静默刷新例外。

