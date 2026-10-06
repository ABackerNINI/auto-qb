# 右对齐列表头/值几何错位 — 已实施完成(彻底方案), 待提交

> 摘要: 用户报「右对齐列没有真正对齐标题文字」—— 已实施完成(2026-10-06 10:37)。修法 = 取证报告
> [26-10-06-0945](../reports/26-10-06-0945-report-webui-column-alignment.html) §5 P0/C1「彻底方案」:
> 把手槽与列头文字排版解耦(省略号下移 `.h-label` / `.h-cell` 改 `flex + overflow:visible + padding-right:0`
> / 把手 `.resizer` `right:-5px` 跨进 10px grid 列间距) + 右对齐列箭头 `columns.js` 追加 `order:-1` +
> 三主题删「0 值居中」旧口径(第九轮 D4 已裁决取消、代码却留)。实测盒模型差 group/torrent **1px**、
> detail **0px**(改前 11/10), 排序后 ≤1(改前 21~22), 三主题一致; `dev.e2e` 6 passed; `test.full` 2676+4 / 99%。
> 完整落地记录已沉淀 [progress/implemented-webui.md](../progress/implemented-webui.md); 专题档案
> [tasks/26-09-29-webui-column-alignment.md](../tasks/26-09-29-webui-column-alignment.md) **Done**。
> 最后活动: 2026-10-06 10:37

**Refs:** memory-bank/tasks/26-09-29-webui-column-alignment.md, memory-bank/plans/26-10-06-1009-plan-webui-column-alignment.html, memory-bank/testing/baselines/26-10-06-1037-webui-column-alignment-fix.md

## 未决 / 下一步

- **本轮改动随实施提交入库(2026-10-06 提交轮)** —— 工作树 = 前端(模板/CSS/JS + e2e) + 知识库回写。
- 范围外但已知: 设置页 HR 表① 的 **14px**(报告 §5-B1)不在本计划内 —— 机制不同(`<table>` + `hrsCols()`,
  无列模型, 隐形箭头 `opacity:0` 仍占位), 计划 §7 给推荐处置(箭头绝对定位不占流, 三主题各 1 条), 待单独排期。
