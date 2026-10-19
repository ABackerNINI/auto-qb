# 3763 passed + 2 skipped(根) —— 站点 chip 两槽图标 + 统一 tracker 健康取数

> 摘要: 站点 chip 两槽图标 + 统一 tracker 健康取数
> 基线时间: 2026-10-19 21:23

## 验收数字

`commands run test.full` 实测:

```text
TOTAL                                                20575    376   6954    258    98%
3763 passed, 2 skipped in 133.28s (0:02:13)
```

口径注记:

- 覆盖率 98%(门限即 98%, 本轮无新增未覆盖面 —— 新增分支由 6 条单测 + 1 条 delta + 1 条契约 + 1 条静态守阵覆盖)。
- 2 skipped 为既有条件跳过(与本轮无关)。
- e2e 不在 pytest 口径内: `commands run dev.e2e` 的 @fast 子集实测 176 passed(含本轮新增 `e2e/site-alerts.spec.mjs` 4 条: 两皮肤 × 左槽/右槽)。

## 本改动面

- `src/auto_qb/torrents/record.py`: 新增 `tracker_health_msg` / `tracker_health_ts` / `tracker_suspect_since`(非快照展示缓存槽)。
- `src/auto_qb/webui/views.py`: `refresh_error_reasons` → `refresh_tracker_health`(统一取数器, 预算分桶 + 四档 TTL + 墙钟去抖); 新增 `_observe_tracker_health` / `_tracker_health_due` / `_site_alert`; `_fetch_tracker_error` 改三态返回; `_member_view` 与搜索 `_view` 加 `site_alert` / `site_alert_msg`; `ERROR_REASON_BUDGET` 退役。
- `src/auto_qb/webui/runtime.py`: `check_pending` 聚合带出 `truth.results`; 调用点与注释随改名。
- `src/auto_qb/webui/static/shared/tpl/xtpl-cells.html`: 三处站点 cell 各加左右两个图标槽。
- `src/auto_qb/webui/static/{atlas,console,prism}/css/views.css`: `.site-chip .sa` / `.sx` 一组规则 + 状态列错误图标呼吸 + reduced-motion 降级(atlas 落 views.css —— components.css 已顶 700 行 cap)。
- `src/auto_qb/webui/static/shared/state.js`: `alertIcons`(hash 键 map)。
- `src/auto_qb/webui/static/shared/commands.js`: `ALERT_ICON` / `ALERT_ICON_MS` 单点, `setRowIcon` / `rowIcon` / `alertIconHref` / `_jobHashes`; `_actCore` 的 reannounce job 带目标标识并按 `truth.results` 逐 hash 落终态; `_cmdRecToResult` 三态都带出 truth。
- `src/auto_qb/webui/static/shared/decorate.js`: 组行装饰指纹纳入 `site_alert` / `site_alert_msg`(R3)。
- `scripts/ui_harness.py`: `--site-alert`(默认 on)注入两态; 命令泵对 reannounce 回执带 `truth.results`。
- 测试: `tests/test_web_backend_misc.py`(+6)、`tests/test_webui_delta.py`(+1)、`tests/test_web_commands.py`(+1)、`tests/test_webui_static_skins.py`(+1)、`tests/helpers.py`(FakeTorrent 三字段)、`tests/test_torrents.py`(快照槽守卫)、`e2e/site-alerts.spec.mjs`(新增 4 条)。
