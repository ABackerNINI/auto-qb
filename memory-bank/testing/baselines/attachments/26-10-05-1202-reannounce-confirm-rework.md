# 基线切片 26-10-05-1202 — 强制汇报确认重构实施完成(S1-S3 三笔提交 + S5 收尾)

> 摘要: 计划 26-10-05-0923 全部落地 —— reannounce 确认判定重构为 `_verdict_reannounce` 五分支纯函数
> (epoch 前跳主判据 + min 窗口假瞬态守卫 + legacy 回退), check_pending 三桶聚合 + reannounce_background
> 后台核实, 前端 warn 第三态终结与三桶分流(delete_flow 保守口径); §05 十一组用例全落地, 净增 +7,
> T4 核验首跑即绿零涟漪。
> 基线时间: 2026-10-05 12:02

**Refs:** memory-bank/tasks/26-10-05-backend-reannounce-confirm-rework.md, memory-bank/plans/26-10-05-0923-plan-reannounce-confirm-rework.html

- 分支: feat/reannounce-confirm-rework @ 04b5899f(三笔实施提交 f251e301(S0+立档)/8873c889(S1+S2)/
  04b5899f(S3); 工作树仅含 S5 收尾文档, src/tests 无未提交改动)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2610 passed + 4 skipped, 30.23s / 30.53s(T4 核验轮) / 30.80s(S5 收尾终态轮, 三次采样),
  覆盖率 TOTAL 98%**(15705 语句 / 169 未覆盖 / 5358 分支 / 141 partial; 门槛 98% 达标)
- 增量构成: 相对上基线 (26-10-05-0947: 2589 passed + 4 skipped / 99% / develop @ 86441e54): passed **+21** =
  ① HR 稳态降频守阵 **+14**(另一 clone 实施后经 develop 同步并入分支基点 ef93db56, 见切片 26-10-05-0905)
  + ② 本计划净增 **+7**(test_web.py +8 新 −1 删 +2 原位重写, = §05 十一组用例: 判定矩阵 epoch/legacy、
  min 窗口守卫、停止直判、推迟早回执、后台核实、item 级窗口、三桶聚合、状态与前缀双契约等);
  语句 15576→15705 (+129), 未覆盖 162→169, 覆盖率 98.94%→98.92% 持平; skip 集合不变(Windows 侧 4 条 POSIX 专属)。
- **跨 clone 口径漂移注记**(T4 结论): 分支线自己的上一条基线 26-10-05-0905(2581+4)实测于**另一 clone**
  (feat/hr-steady-throttle @ 9f096c09), 与本 clone 树存在 **22 项**并行会话用例漂移(2589−2567), 数字**不可直接对齐**
  —— 本切片对照基准取同 clone 的 26-10-05-0947; 2610−2589−14(HR)与 test_web.py 净增 +7 吻合, 增量全部可归因。
- 耗时 30.2~30.8s 较上几条切片(27.5~36.7s 噪声带)居中, 非回归。
