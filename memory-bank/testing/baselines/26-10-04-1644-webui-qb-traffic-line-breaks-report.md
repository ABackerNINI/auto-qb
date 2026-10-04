# 基线切片 26-10-04-1644 — qB流量图折线断裂取证轮(纯文档): 报告+档案+切片+pitfalls 入库

> 摘要: 本轮零代码改动(取证报告 26-10-04-1639 + tasks 档案 + activeContext 切片 +
> pitfalls/backend/task-interval-tick-quantization 新坑 + 生成索引), 基线数字与上一条
> (26-10-04-1039)之间隔 5 笔 qB流量存储 v2 代码提交(P1b~P5, 会话开工同步带入), 全绿。

> 基线时间: 2026-10-04 16:44
> 档案: memory-bank/tasks/26-10-04-webui-qb-traffic-line-breaks.md

**Refs:** memory-bank/tasks/26-10-04-webui-qb-traffic-line-breaks.md, memory-bank/reports/26-10-04-1639-report-webui-qb-traffic-line-breaks.html

- 分支: develop @ 3d1e1665 (+ 本轮未提交文档改动)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2507 passed + 4 skipped, 30.95s (引擎计 31.8s), 覆盖率 TOTAL 99%**
  (14677 语句 / 152 未覆盖 / 4964 分支 / 112 partial; 门槛 98% 达标, 98.63%)
- 相对上基线 (26-10-04-1039: 2471 passed + 4 skipped / 99% / 29.98s @ 7bee8847+彼侧未提交改动):
  passed **+36, 全部可归因** —— 会话开工同步带入 qB流量存储 v2 五笔提交(6540d0f3 P1b /
  03a6798b P2 / 122779c1 P3 / f446ef0a P4 / 3d1e1665 P5 收尾)各自新增的验收用例。skip 集合不变。
- 首跑红 1 条(本人新档案缺行首精确 `## 实现计划` 章节, 标题带括注被守卫判缺) —— 修正档案标题后
  复跑全绿; 非代码回归。
- 未验证面: Linux 侧本轮未重测(纯文档轮, 与代码态无关)。
