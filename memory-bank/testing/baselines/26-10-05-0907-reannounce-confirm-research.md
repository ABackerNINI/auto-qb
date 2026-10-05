# 基线切片 26-10-05-0907 — 强制汇报确认机制调研收尾(纯文档轮)

> 摘要: 调研轮无代码/测试改动, 跑全量测试落收尾基线。develop @ 911af7ef(会话开工同步);
> 数字相对上基线的增量全部来自并行会话已入库 develop 的用例, 与本轮无关。
> 基线时间: 2026-10-05 09:07

**Refs:** memory-bank/tasks/26-10-05-backend-reannounce-confirm.md

- 分支: develop @ 911af7ef(工作树仅含本轮新增文档: 报告/档案/切片, 无 src 与 tests 改动)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2589 passed + 4 skipped, 36.78s, 覆盖率 TOTAL 99%**
  (15576 语句 / 162 未覆盖 / 5296 分支 / 137 partial)
- 相对上基线 (26-10-05-0737: 2576 passed + 4 skipped / 27.48s+28.13s / 99%): passed **+13**,
  语句 +606 / 分支 +258 / partial +23 —— 本轮零代码改动, 增量全部来自并行会话合入 develop
  的实施(webui-danger-guards 等后续批次), 非本轮产物。
- 耗时 36.78s 高于近几条切片的 ~27-29s 噪声带: 单次采样, 会话同期开着浏览器取证(后台负载),
  未排查; 纯文档轮无回归面, 不计警报。
