# 3995 passed + 2 skipped —— 站点 chip 单点 + 进度百分比单点(模板层单元格碎片收敛)后全量基线

> 摘要: 站点 chip 单点 + 进度百分比单点(模板层单元格碎片收敛)后全量基线
> 基线时间: 2026-10-22 02:21

## 验收数字

`commands run test.full` 实测(裸数字只写本切片这一处):

- 汇总行: **3995 passed, 2 skipped in 110.84s**
- 覆盖率: TOTAL **99%**(过闸)

逐条口径注记:

- 本轮改动面守阵在 test.full 内全绿: `test_webui_static_skins.py`(`test_frontend_site_alert_icon_wiring` 比对面改扫单点模板 + `test_frontend_table_shell_single_point` comps 元组加 aq-site-chip, 同轮改版)+ `test_webui_static_dom_panel.py` + `test_webui_static_dom_page.py`
- 真浏览器复验(`commands run dev.e2e -- e2e/site-alerts.spec.mjs e2e/dt-table-face-bg.spec.mjs e2e/multiselect-shows.spec.mjs`): **64 passed**(三皮肤; chip 变色 / 图标槽位置 / 搜索命中让出底色 / search-hit 行首格镜像 / 集行站点格多选) —— 组件化后 DOM 与旧三份逐字同由既有断言原样通过实证
- 本轮**未新增测试函数**(仅改写既有守阵的比对面), passed 数与上一基线的差来自开工同步带入的上游提交, 与本改动无关

## 本改动面

- `src/auto_qb/webui/static/shared/tpl/xtpl-cells.html` —— 新增 `#tpl-aq-site-chip` 单点模板; group/torrent/ep 三处 11 行 chip 骨架收敛为 `<aq-site-chip :m>` 调用点(torrent 版顺带补 search-hit); `m-progress` 三处改调 `$root.progPct`; `.dur-body` 口径注释与 xtpl.html member 版互指; tag-chip/cat-chip 分歧点加注; m-progress 标注四处逐字同
- `src/auto_qb/webui/static/shared/tpl/xtpl.html` —— member 行 `m-progress` 改调 `$root.progPct`; `.dur-body` 注释互指
- `src/auto_qb/webui/static/shared/format.js` —— AQB_FORMAT 新增 `progPct(v)` 百分比单点(Math.min(100, v*100))
- `src/auto_qb/webui/static/shared/table.js` + `app.js` —— `AQ_SITE_CHIP_COMPONENT` 定义 + `app.component("aq-site-chip", ...)` 注册
- `src/auto_qb/webui/static/shared/tpl/torrents.html` —— 行级 class 补 `'search-hit': m.hit`(与 groups/shows 行级对齐; 种子页对象不带 hit, 绑定休眠, 取证见 issue 复验记录)
- `memory-bank/modules/attachments/webui-static-contract-details.md` —— 表格公共组件 六个→七个(补 aq-site-chip 单点)
- 未授权不做: commit/push
