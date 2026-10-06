# 右对齐列表头/值几何错位 — 修法已定(彻底方案), 实施计划已出, 待开工

> 摘要: 用户报「右对齐列没有真正对齐标题文字」—— 实测属实。主视图 4 表(分组 / 种子 / 追剧 / 组内明细)
> 全部右对齐列偏 **11px**(明细表 10px): 根因 `.h-cell { padding-right: 10px }` 是给拖拽把手留的命中区
> (因 `.h-cell` 有 `overflow: hidden`, 把手不能外伸), 而值格子 `padding-right: 0`; 多的 1px 来自数据行
> 1px 侧边框。设置页 HR 在线核实表① 的 4 个 num 列偏 **14px**: 排序箭头 SVG 恒在 DOM、只用 `opacity: 0`
> 隐藏(11px + `margin-left` 3px 仍占布局)。当前排序列再 +11px(箭头内联占位)。三主题 atlas / console / prism
> 数值完全一致; 抽屉 3 表 / HR 表②③ / 全站左对齐列不受影响。取证报告 `reports/26-10-06-0945`。
> **2026-10-06 10:09 进展**: 用户拍板 —— ①修法取**彻底方案**(报告 §5 P0/C1: 把手槽与文字排版解耦, 非最小方案 A),
> ②`0 值居中` 判为**旧口径/文档漂移**(第九轮 D4 已裁决取消、代码与知识库仍留), 正式实施时**一并修复**。
> 分步实施计划已出: `plans/26-10-06-1009-plan-webui-column-alignment.html`(doc-status **Open**, PHASE 0-7)。
> 最后活动: 2026-10-06 10:09

**Refs:** memory-bank/tasks/26-09-29-webui-column-alignment.md, memory-bank/testing/baselines/26-10-06-0958-webui-column-alignment-header-offset.md, memory-bank/plans/26-10-06-1009-plan-webui-column-alignment.html, memory-bank/testing/baselines/26-10-06-1022-webui-column-alignment-plan.md

## 现状

- **零代码改动**: 取证轮只出报告 + 坑档 + 回写知识库; 计划轮只出计划。**修法与 `0 值居中` 口径已定**, 但代码未动。
- 实测环境: `scripts/ui_harness.py`(真 `create_app` + 合成种子 300 / 40 组) + headless Chromium,
  取证基线 develop@295bb226; 计划轮开工 sync 到 **develop@c2e43cf9**。
  复跑脚本留在 `.workbuddy-ai/tmp/`(`measure2.cjs` 主表+抽屉 / `measure_shows.cjs` 追剧 /
  `measure_hr.cjs` HR 表① / `measure-align.cjs` 逐列几何 / `probe.cjs`), 已 gitignore。
- 判据: 右对齐列的**盒模型**差(表头内容盒右缘 − 值内容盒右缘)必须 0(允许 ±1)。改前 11 / 10 / 14。
  ⚠ 别拿「值文字墨迹右缘」当判据 —— 值宽于列宽时会被省略号截断, 墨迹量值偏出 10px。

## 已定(原「待拍板」, 2026-10-06 用户裁决)

1. **修法 = 彻底方案**(报告 §5 P0/C1): 省略号下移到内层标签 `<span class="h-label">` → `.h-cell` 自身
   `overflow: visible; padding-right: 0` → 把手挪进**既有的** 10px grid 列间距(半进半出, 不新增宽度开销);
   右对齐列的 `.arrow` 取 `order: -1` 排到标签左侧(消 P3 的 +11px 跳动)。
   落点 = 5 个表头块 / 3 模板 + 3 主题 CSS + `shared/columns.js::colAlignCss()`。
   ⚠ **不可**只把 `.h-cell` 的 `padding-right` 归 0 而不挪把手(右对齐表头末 10px 会变成拖拽命中区)。
2. **`0 值居中` = 归正**: 删三主题的 `.g-stat.zero, .m-stat.zero { text-align: center }`(2026-09-15 引入、
   2026-09-17 第九轮 D4 已裁决取消的旧口径), 让 0 值格回落列模型 align(右对齐)。`.zero` 的淡化配色保留。
   同步回写漂移表述: `modules/webui-static-contract.md` · `pitfalls/web-ui/header-cell-gutter.md` · `shared/app.js` 注释。

## 未决 / 下一步

- **等用户显式「开工」指令** 才动代码(计划 doc-status = Open 待拍板 → 拍板后转 In Progress)。
- 范围外但已知: 设置页 HR 表① 的 **14px**(报告 §5-B1) 不在本计划内 —— 机制不同(`<table>` + `hrsCols()`,
  无列模型), 报告已判「可分开做」; 计划 §7 给了推荐处置(箭头绝对定位不占流, 三主题各 1 条)。
- 计划新增的常驻守卫: `e2e/smoke.spec.mjs` 加「右对齐列 表头↔值 盒模型差 ≤1px 且值格不居中」用例(红绿双验)。
