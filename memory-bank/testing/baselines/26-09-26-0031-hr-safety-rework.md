# 1629 collected: 1628 passed + 1 skipped —— 两线合流: HR 未达标红档语义修正轮 × 扩展选项页终态

> 摘要: 合流树重测(HR 红档 +0 条改 4 处守阵 × 扩展选项页 +1 条); 时分取本轮制品 26-09-26-0031 计划时点, 与 ext-options-terminal 同点、文件名次级键定序; 当日序位第 4
> 基线时间: 2026-09-26 00:31
> 档案: 26-09-25-webui-hr-safety-display (修正1–3) · 26-09-22-backend-partial-hr-verify (v3.3)

(档案 `26-09-25-webui-hr-safety-display` 修正1–3 + `26-09-22-backend-partial-hr-verify` v3.3; 两轮并行开发, 本条为**合流树重测**)。

- **HR 红档轮 +0 条, 改 4 处断言/守阵**: test_hr_resolve C 档断言改 `SAFETY_FAILED`(「考核未通过」终态独立红档);
  test_web 接线守阵安全档位键集扩四档(danger/failed/safe/unknown)、CSS 成对清单加 `.m-pair.hr-fail`、
  考察中短语断言去「义务未了」。⚠ 合流时修入树缺陷: 远端 `hr/server.py` 的 `sites_fn` 注解用了 `List`
  但 typing 导入行没有 → 全库 import 级 NameError(89 errors), 合并解决里补 `List` 修复。
- **扩展选项页轮 +1 条**: `test_extension_proxy.py::test_background_events_ring_dual_write`(后台/日志同源
  双写事件环契约) + 三档接线守阵改写 `test_options_swiss_wiring`; 落地面 background.js 事件环 +
  选项页按样张 A 重写, 新增制品 [plans/26-09-26-0031-plan-hr-ext-options-style.html](../../plans/26-09-26-0031-plan-hr-ext-options-style.html)。
- **mockup 轮踩坑**: 新建 plans/ 制品缺五元 meta + 父计划未反链 → 文档守阵红(补齐即绿; 认领链同因)。

TOTAL **92%**(11064 语句 / 787 未覆盖 / 3640 分支 / 329 partial); dev.fmt 已跑。
