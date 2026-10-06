# 右对齐列表头/值几何错位 — 主表彻底方案 + HR 表① 补修, 均已实施

> 摘要: 用户报「右对齐列没有真正对齐标题文字」—— 主表彻底方案已实施完成(2026-10-06 10:37),
> HR 表① 补修完成(2026-10-06 11:19)。修法 = 取证报告
> [26-10-06-0945](../reports/26-10-06-0945-report-webui-column-alignment.html) §5 P0/C1「彻底方案」:
> 把手槽与列头文字排版解耦(省略号下移 `.h-label` / `.h-cell` 改 `flex + overflow:visible + padding-right:0`
> / 把手 `.resizer` `right:-5px` 跨进 10px grid 列间距) + 右对齐列箭头 `columns.js` 追加 `order:-1` +
> 三主题删「0 值居中」旧口径(第九轮 D4 已裁决取消、代码却留)。实测盒模型差 group/torrent **1px**、
> detail **0px**(改前 11/10), 排序后 ≤1(改前 21~22), 三主题一致; `dev.e2e` 6 passed; `test.full` 2676+4 / 99%。
> **HR 表① 补修**(计划 §7 推荐处置): 三主题 `.hr-detail-table th .arrow` 由 `display:inline-block` 改
> `position:absolute`(无偏移取静态位置, 仍紧贴标签右缘)+ `th.sortable` 补 `position:relative` —— 零模板/零 JS
> 改动; 实测 **14px → 0px**(三主题一致, 改前 14 与报告同值); `tests/test_web.py` 静态守阵红绿双验;
> `dev.e2e` 6 passed; `test.full` 2676+4 / 99%(与主表轮逐位持平)。
> 完整落地记录已沉淀 [progress/implemented-webui.md](../progress/implemented-webui.md); 专题档案
> [tasks/26-09-29-webui-column-alignment.md](../tasks/26-09-29-webui-column-alignment.md) **Done**。
> 最后活动: 2026-10-06 11:19

**Refs:** memory-bank/tasks/26-09-29-webui-column-alignment.md, memory-bank/plans/26-10-06-1009-plan-webui-column-alignment.html, memory-bank/testing/baselines/26-10-06-1037-webui-column-alignment-fix.md, memory-bank/testing/baselines/26-10-06-1119-webui-hr-table-arrow.md

## 未决 / 下一步

- **本轮改动随实施提交入库(2026-10-06 提交轮)** —— 工作树 = 前端(模板/CSS/JS + e2e) + HR 表① 三主题 CSS +
  `tests/test_web.py` 守阵 + 知识库回写。
- 报告 §2 已判**无需动作**的面: 左对齐列(全站 ≤1px) · 居中列(H&R / 站数 / 版本) · 数值溢出截断(列宽/省略号问题);
  抽屉 3 表与 HR 表②/③ 实测 0px。**本专题无遗留待办。**
- ⚠ 表① 在桩服务里**不渲染**(桩不灌 HR 条目) ⇒ 几何验证只能用「真实主题 CSS + 逐字抄模板 DOM」复现;
  若要把几何守卫做成常驻用例, 需走同样的 DOM 注入法(当前只落了静态守阵, 见坑档
  [header-cell-gutter](../pitfalls/web-ui/header-cell-gutter.md))。
