# 3763 passed + 2 skipped(根) —— 站点 chip 改色表达: 站点问题走颜色 + 命令结果图标收口

> 摘要: 站点 chip 改色表达: 站点问题走颜色 + 命令结果图标收口
> 基线时间: 2026-10-19 22:43
**Refs:** memory-bank/plans/26-10-19-2206-plan-webui-site-chip-color.html

## 验收数字

`commands run test.full` 实测:

```text
TOTAL                                                20575    376   6954    258    98%
3763 passed, 2 skipped in 137.85s (0:02:17)
```

口径注记:

- 覆盖率 98%(门限即 98%, 本轮无新增未覆盖面 —— 本轮是纯前端表现层返工, 未改任何 `src/**.py` 逻辑)。
- 2 skipped 为既有条件跳过(与本轮无关)。
- e2e 不在 pytest 口径内: `npm run test:e2e:fast`(@fast 子集)实测 **184 passed**(含本轮重写的 `e2e/site-alerts.spec.mjs` 4 条 × 2 皮肤 = 8 条)。
- 首跑曾因 `memory-bank` 索引未重建而红 4 条索引守卫(`test_docs_index_is_regenerated` / `test_memory_bank.py` 3 条), `commands run kb.index` 重建后复跑全绿 —— 数字取自重建后的那一次。

## 本改动面

- `src/auto_qb/webui/static/shared/tpl/xtpl-cells.html`: 三处站点 cell 删左槽 `.sa`, chip 加 `siteAlertClass` / `chipAlertTip` / `siteAlertAria`; 图标上的 `title` 移除(提示上移整块 chip)。
- `src/auto_qb/webui/static/shared/commands.js`: 新增 `siteAlertClass` / `chipAlertTip` / `siteAlertAria`; `ALERT_ICON` 收窄为命令结果四态(`pending/ok/warn/error`)。
- `src/auto_qb/webui/static/{atlas,console,prism}/css/views.css`: `.site-chip.sa-no-conf`(橙底 + 虚线底边)/ `.sa-tracker`(红底)/ `.m-site.sa-*`(只染文字色)/ `.site-chip.sa-* .sx`(currentColor); `.search-hit` 改 `background: transparent` + `inset 0 0 0 1px var(--accent-line)`; 删旧 `.sa` 图标组。
- `src/auto_qb/webui/static/shared/tpl/xtpl.html` / `shows.html`: 明细成员行与追剧未识别行的 `.m-site` 同语义染色 + 同款 tooltip。
- `src/auto_qb/webui/static/shared/state.js`: `alertIcons` 注释随通道收窄更新。
- 测试: `tests/test_webui_static_skins.py::test_frontend_site_alert_icon_wiring` 按新契约重写(键集 / `.sa` 零残留 / 虚线底边 / search-hit 让出底色 / `.m-site` 染色 / `ALERT_ICON` 只含四态), `e2e/site-alerts.spec.mjs` 重写为 4 条 × 2 皮肤, `tests/helpers.py` 与 `tests/test_torrents.py` 仅更新注释措辞。
