# 1636 collected: 1635 passed + 1 skipped —— webui 一键导入缺失站点

> 摘要: 再合流远端 9 笔后的合并树重测; +7 条(后端 5 + 前端接线 1 + exporter 1); 当日序位第 5
> 基线时间: 2026-09-26 02:34
> 档案: 26-09-26-webui-sites-import

(档案 `26-09-26-webui-sites-import`; 数字为**再合流远端 9 笔[HR 未达标红档/扩展选项页终态/webui 修复/docker 验收]后的合并树重测**)。
**+7 条**: test_web.py +6(后端 5:
`test_sites_missing_scans_and_builds_defaults` 缺失域名生成默认条目且已配置域名不重复 /
`test_sites_missing_name_conflict_suffix` 站点名冲突 `_N` 后缀 / `test_sites_missing_all_covered_returns_empty`
全覆盖空返回 / `test_sites_missing_requires_connected_client` 断连 503 / `test_sites_missing_api_failure_maps_502`
扫描失败 502 带原因; 前端接线 1: `test_frontend_sites_import_wiring`); test_exporter.py +1
(`test_gen_tracker_name` 新提取的站点名生成单测); 金清单 `_GOLDEN_ROUTES` +1
(`GET /api/sites/missing`, 合并树 62 条)。落地面: `core/exporter.py` 提取 `gen_tracker_name`
(export_yaml_template 改调, 行为不变) + 新路由模块 `webui/server/routes/sites.py` + 前端
`config_hub.js::hubImportSites()` 与两套 UI「⤓ 导入缺失站点」按钮。
TOTAL **92%**(10993 语句 / 787 未覆盖 / 3642 分支 / 328 partial)。
