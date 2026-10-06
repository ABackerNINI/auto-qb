# 2676 —— WEBUI 列对齐彻底方案实施计划(纯文档轮, 零代码改动)

> 摘要: 用户按取证报告 [26-10-06-0945](../../reports/26-10-06-0945-report-webui-column-alignment.html) 的
> 「彻底方案」(报告 §5 P0/C1) 要分步实施计划, 并明示「`0 值居中`是旧口径 / 文档漂移, 正式实施时一并修复」。
> 产物全为文档 —— 计划 HTML(新增) · 报告 `doc-refs` 补反向引用(仅 meta 机械面) · 专题档案追加裁决与计划
> · activeContext 切片更新 · 索引重建。**零 Python 与测试改动** ⇒ 数字应与上一条
> [26-10-06-0958](26-10-06-0958-webui-column-alignment-header-offset.md) 的 2676 + 4 逐位持平 —— 实测一致。
> 基线时间: 2026-10-06 10:22

**Refs:** memory-bank/tasks/26-09-29-webui-column-alignment.md, memory-bank/activeContext/26-10-06-0958-webui-column-alignment.md

- 分支: develop @ **c2e43cf9**(开工 `my-commit-flow.sync` 后; 工作树含本次文档改动未提交)
- 命令: `commands run test.full`(Windows —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测 (Windows)**: **2676 passed + 4 skipped, 覆盖率 TOTAL 99%**
  - 语句 **16021** / 未覆盖 **163** / 分支 **5472** / partial **143**。
  - 耗时: 本轮两次采样 **62.92s / 51.69s**(均含覆盖率报表; wall 64.6s / 53.2s) ⇒ 区间约 **52~63s**。
- 相对上一条基线 [26-10-06-0958](26-10-06-0958-webui-column-alignment-header-offset.md)
  (2676 + 4 / 16021 / 163 / 5472 / 143): **逐位持平**(passed ±0 / 语句 ±0 / 未覆盖 ±0 / 分支 ±0 / partial ±0)
  —— 与「纯文档轮」预期一致。
- 旁证: `commands run kb.check` 主键纪律与认领链 OK; `commands run kb.docmap -- --check` 无断链;
  `commands run kb.index` 生成 20 个生成物; `tests/test_docs_forms.py` **11 passed**。
- 改动面(全部为文档, 无 `src/` 与 `tests/` 改动):
  - `memory-bank/plans/26-10-06-1009-plan-webui-column-alignment.html`(新增, 专题 `webui-column-alignment`, doc-status Open)
  - `memory-bank/reports/26-10-06-0945-report-webui-column-alignment.html`(`doc-refs` 补本计划反向引用)
  - `memory-bank/tasks/26-09-29-webui-column-alignment.md`(追加裁决 + 计划; 子任务 #8 待拍板→完成, #9 计划已出)
  - `memory-bank/activeContext/26-10-06-0958-webui-column-alignment.md`(更新; 「待拍板」→「已定」)
  - `memory-bank/plans/_index.md`(生成物重建)
