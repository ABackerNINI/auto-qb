# memory-bank-dir-refactor — 生成物实时化 / 四工位专题目录化 可行性分析

> 摘要: 用户命题两项已出报告
> [reports/26-10-01-2125-report-kb-artifacts-realtime-and-layout.html](../reports/26-10-01-2125-report-kb-artifacts-realtime-and-layout.html):
> ①生成物(20 份 `_index.md` ≈135KB, 占库 1.7%)**不改全量实时生成** —— 落盘 + 生成器 + 三层守卫维持,
> 库已画对「路由骨干落盘 / 点查视图现算」分界线(docmap / active / baseline 先例);
> ②四工位**不做 pitfalls 式专题目录** —— doc-topic 开放集 162 键(69% 单件)、点查型访问,
> 逻辑归组已由 docmap 现算承担, 物理归堆 = `_doc-map.md` 物化退役路线的更重形态。
> 正在进行: 无(纯分析轮, 代码零改动)。两项低风险增强**待用户拍板**:
> issues 索引补 SUMMARY_MAX 截断; tasks 索引触顶(现 95%)时按状态归档 Done/Superseded(非按专题)。
> 已回写: 档案 26-09-22-memory-bank-dir-refactor 追加进度日志。
> 最后活动: 2026-10-01 21:25
