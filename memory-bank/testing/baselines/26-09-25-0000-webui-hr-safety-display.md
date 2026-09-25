# 1607 collected: 1606 passed + 1 skipped —— HR 删除安全档位 WEB UI 呈现落地

> 摘要: +4 条(safety_display 三档位派生 3 + 前端接线守阵 1); 双 UI 浏览器冒烟 94 项全过; 时分不可考; 当日序位第 17
> 基线时间: 2026-09-25 00:00
> 档案: 26-09-25-webui-hr-safety-display

- **1607 collected: 1606 passed + 1 skipped** —— 2026-09-25 **HR 删除安全档位 WEB UI 呈现落地**
  (计划 `26-09-25-1823-plan-webui-hr-safety-display`, 档案 `26-09-25-webui-hr-safety-display`)。**+4 条**:
  `test_hr_resolve.py` safety_display 三档位派生 3 条(站点档位即结论 / 身份层 / judged None 回落) +
  `test_web.py::test_frontend_hr_safety_wiring` 前端接线守阵(token 映射表逐字一致 / 做种时长列 6 处换绑 /
  新样式两套 CSS 成对 / `m.hr_*` 字段 ⊆ `_hr_view_fields` 键集); 另扩 `test_hr_view_fields_three_state`
  与 `_scan_filter_facets` 同查 `hrSrcOptions`。落地面: `hr/resolve.py::safety_display` 派生单点 +
  `views.py` 透出三字段(退役二值 `hr_satisfied_src`); 前端做种时长列按档位着色 + 来源徽标 + 悬停全文、
  删除确认框点名、H&R 筛选两档→四档 + 来源副筛选、批量条「含 N 个不能删」。
  TOTAL **91%**(10991 语句 / 791 未覆盖 / 3612 分支 / 327 partial; resolve.py 98% / views.py 97%);
  双 UI 浏览器冒烟 **94 项全过 0 失败**(桩服务 1500 种子)。
