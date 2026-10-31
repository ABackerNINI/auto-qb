# 2676 —— 设置页 HR 表① 排序箭头改绝对定位不占流(三主题 CSS + 静态守阵)

> 摘要: 按计划 [26-10-06-1009](../../plans/26-10-06-1009-plan-webui-column-alignment.html) §7 给「单独排期」的
> 推荐处置, 补修报告 [26-10-06-0945](../../reports/26-10-06-0945-report-webui-column-alignment.html) §5-B1 的
> 设置页 HR 表①(4 个 num 列表头文字左偏 14px): 三主题 `.hr-detail-table th .arrow` 由
> `display:inline-block` 改 `position:absolute`(无偏移 = 取静态位置, 仍紧贴标签右缘)+ `th.sortable` 补
> `position:relative` —— 零模板 / 零 JS 改动。`tests/test_web.py` 加静态守阵(红绿双验)。
> **Python 生产代码零改动**; 唯一 `tests/` 改动 = 在既有用例内加断言(不新增测试函数) ⇒ 数字应与上一条
> [26-10-06-1037](26-10-06-1037-webui-column-alignment-fix.md) 的 2676 + 4 逐位持平。
> 基线时间: 2026-10-06 11:19

**Refs:** memory-bank/tasks/26-09-29-webui-column-alignment.md, memory-bank/plans/26-10-06-1009-plan-webui-column-alignment.html, memory-bank/pitfalls/web-ui/header-cell-gutter.md

- 分支: develop @ **cdacf51a**(开工 `my-commit-flow.sync` 后; 工作树含本次前端/测试改动未提交)
- 命令: `commands run test.full`(Windows —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测 (Windows)**: **2676 passed + 4 skipped, 覆盖率 TOTAL 99%**
  - 语句 **16021** / 未覆盖 **163** / 分支 **5472** / partial **143**。
  - 耗时: 本轮单次采样 **58.4s**(含覆盖率报表; wall 58.4s)。
- 相对上一条基线 [26-10-06-1037](26-10-06-1037-webui-column-alignment-fix.md)
  (2676 + 4 / 16021 / 163 / 5472 / 143): **逐位持平**(passed ±0 / 语句 ±0 / 未覆盖 ±0 / 分支 ±0 / partial ±0)
  —— 与「三主题 CSS + 既有用例内加断言(无新测试函数、无 Python 改动)」预期一致。
- 前端验证(真浏览器, 桩服务 `scripts/ui_harness.py`; 表① 在桩里**不渲染** —— 桩不灌 HR 条目, 故用
  **真实主题 CSS + 逐字抄模板 DOM** 在真页面里复现同款 DOM 量真实盒模型, 与报告 §5-B1 取证同法):
  - `commands run dev.e2e`: **6 passed**(prism / atlas × {渲染健康, 数据契约, 几何守卫})。
  - 盒模型差(表头标签文字右缘 − 值文字右缘, 4 个 num 列): **14px -> 0px**, 三主题 atlas/console/prism 一致;
    改前对照 **14**(报告 26-10-06-0945 实测同值)。左对齐列不变; 表头行高 27.89px 不变; 箭头仍渲染(width 11px)。
  - 守阵**红绿双验**: 把 console 该规则改回 `display:inline-block` 时
    `test_frontend_hr_table_sort_filter_reorg_wiring` **红**(报 `position:absolute` 缺失), 复原即 **绿**。
- 旁证: `commands run kb.check` / `kb.index` 绿(认领链 OK / 主键 OK); `commands run doc.caps` 无新增债务
  (既有 1 项 `issues/_index.md` 超 cap, 与本轮无关)。
- 改动面(前端静态资产 3 文件 + `tests/` 1 文件 + 知识库; 无 Python 生产代码改动):
  - `src/auto_qb/webui/static/{atlas/css/dialogs,console/css/dialogs,prism/css/views}.css`
    (`.hr-detail-table th.sortable` 补 `position:relative`; `th .arrow` 改 `position:absolute`, 去 `display:inline-block`)
  - `tests/test_web.py`(`test_frontend_hr_table_sort_filter_reorg_wiring` 内加三主题箭头脱流断言 + 头清单/docstring 同步)
  - `memory-bank/{pitfalls/web-ui/header-cell-gutter.md, modules/webui-static-contract.md, tasks/26-09-29-webui-column-alignment.md, activeContext/26-10-06-0958-webui-column-alignment.md, plans/26-10-06-1009-plan-webui-column-alignment.html}`
