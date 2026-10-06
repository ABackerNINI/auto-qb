# 右对齐列表头/值几何错位 — 取证完成, 待拍板修法

> 摘要: 用户报「右对齐列没有真正对齐标题文字」—— 实测属实(只读轮次, 零代码改动)。主视图 4 表
> (分组 / 种子 / 追剧 / 组内明细)全部右对齐列偏 **11px**(明细表 10px): 根因 `.h-cell { padding-right: 10px }`
> 是给拖拽把手留的命中区(因 `.h-cell` 有 `overflow: hidden`, 把手不能外伸), 而值格子 `padding-right: 0`;
> 多的 1px 来自数据行 1px 侧边框。设置页 HR 在线核实表① 的 4 个 num 列偏 **14px**: 排序箭头 SVG 恒在 DOM、
> 只用 `opacity: 0` 隐藏(11px + `margin-left` 3px 仍占布局)。当前排序列再 +11px(箭头内联占位)。
> 三主题 atlas / console / prism 数值完全一致; 抽屉 3 表 / HR 表②③ / 全站左对齐列不受影响。
> 取证报告 `reports/26-10-06-0945`; 专题档案 `tasks/26-09-29-webui-column-alignment.md`(已由 Done 重开为 Open)。
> 待用户拍板: ①修法 A(值格子补同宽右槽, 代价 = 右对齐列内容宽 −10px) vs 彻底方案(把手槽与文字排版解耦);
> ②`0 值居中` 既有口径(与「标题右对齐」冲突, 用户截图里的「可用性 0.00」即此)是否翻案。
> 最后活动: 2026-10-06 09:58

**Refs:** memory-bank/tasks/26-09-29-webui-column-alignment.md, memory-bank/testing/baselines/26-10-06-0958-webui-column-alignment-header-offset.md

## 现状

- **零代码改动**: 本轮只出报告 + 坑档 + 回写知识库。修法与 `0 值居中` 口径均待用户拍板后才动代码。
- 实测环境: `scripts/ui_harness.py`(真 `create_app` + 合成种子 300 / 40 组) + headless Chromium,
  基线 develop@295bb226。复跑脚本留在 `.workbuddy-ai/tmp/`(`measure2.cjs` 主表+抽屉 / `measure_shows.cjs`
  追剧 / `measure_hr.cjs` HR 表① / `probe.cjs` 逐列几何), 已 gitignore。
- 判据: 右对齐列的**盒模型**差(表头内容盒右缘 − 值内容盒右缘)必须 0(允许 ±1)。改前 11 / 10 / 14。
  ⚠ 别拿「值文字墨迹右缘」当判据 —— 值宽于列宽时会被省略号截断, 墨迹量值偏出 10px。

## 待拍板(阻塞修法)

1. **修法选型**: A = `shared/columns.js::colAlignCss()` 对 right 列补 `padding-right: 10px`(单文件、
   三主题全好, 代价是右对齐列内容宽 −10px) vs 彻底方案 = 把把手槽与文字排版解耦(动 5 个表头块 / 3 模板
   + 3 主题 CSS)。**不可**直接把 `.h-cell` 的 `padding-right` 归 0(右对齐表头末 10px 会变成拖拽命中区)。
2. **`0 值居中` 口径**: `.g-stat.zero { text-align: center }` 是 2026-09-17 拍板的既有口径, 与
   「右对齐列标题要对齐」直接冲突 —— 要么 0 值也右对齐, 要么接受 0 值列看起来没对齐。

## 关键决策(本轮已定)

- 本轮**只取证不修**: 用户原话「先确定修改范围, 写一个报告」⇒ 属只读轮次, 不入池 issue、不动代码。
- 报告与上一份列对齐审计(26-09-28-2345)**同专题** `webui-column-alignment`, 且需修正其推论:
  该审计的「表头与值同源注入 ⇒ 不会错位」只保证**口径一致**, 不保证**几何对齐**。
- 新增坑档 `pitfalls/web-ui/header-cell-gutter.md`(未并入 `layout-css.md` —— 后者已 17.6KB 超 12KB cap)。
