# 5163 passed + 10 skipped(根) —— WebUI 迁移可见性 P1 完成后全量

> 摘要: WebUI 迁移可见性 P1 完成后全量
> 基线时间: 2026-11-04 12:17
**Refs:** memory-bank/plans/26-11-04-1042-plan-webui-relocate-visibility.html

## 验收数字

- `commands run test.full` 实测(2026-11-04 12:29, 151.5s, P1 行内徽标/迁移筛选/详情段完成后): **5163 passed + 10 skipped(根)**
- 覆盖率 TOTAL 表(誊写): 24030 stmts / 226 miss / 8214 branches / 168 partial / **99%**
- 口径注记: `commands run test.quick` 首跑出现 1 例既有偶发失败(`test_qb_capture` 伪 hash 随机落回真值 "H1"), 单跑与复跑均通过; 与本改动无关, 未修改该测试。

## 本改动面

- `src/auto_qb/webui/static/shared/decorate.js`: 迁移状态词表/徽标/title/组级筛选桶/详情展示方法单点; `_relocateSig` 补 `src`/`armed_at`。
- `src/auto_qb/webui/static/shared/tpl/xtpl-cells.html`: 组行/种子行路径列加 `button.rel-badge`(Tab/Enter/Space/触屏可达, `@click.stop` 只开详情)。
- `src/auto_qb/webui/static/shared/state.js`/`filters.js`/`hr.js`/`auth.js`: 新增 `relocateFilter` 独立筛选; 选项走 `facetRows + _facetOptions("relocate")`; 路径筛仍按 qB `save_path` 不变; 登出清空。
- `src/auto_qb/webui/static/shared/tpl/topbar.html`: 筛选说明条补「迁移状态」摘要。
- `src/auto_qb/webui/static/shared/drawer_rows.js` + `drawer_tpl/02`/`03`: 详情 General 新增「迁移」段(状态/来源/auto-qb 设置/job/路径/别名/武装/更新时间/失败原因), 无 relocate 整段不渲染。
- `src/auto_qb/webui/static/shared/row_lang.css`: 徽标样式与 `has-rel` 路径列 flex 布局(皮肤令牌, console 用 999px 胶囊)。
- `src/auto_qb/webui/server/routes/torrent_detail.py`: 详情 payload 增补 `relocate` 投影。
- `tests/test_webui_relocate_visibility.py`(扩展 4 例): 徽标渲染/状态映射(node 探针)/筛选语义与路径筛不变/详情段与端点投影; `tests/webui_static_scan_js.py` 纳管 `relocateOptions` 走 `_facetOptions`。
