# 基线: WEBUI 选中×触发一致性 S3(descriptor 单点 + M3 拆借道)

- 主题: [../../activeContext/26-10-10-2103-webui-selection-trigger-parity.md](../../activeContext/26-10-10-2103-webui-selection-trigger-parity.md) · 计划 26-10-10-2001(S3, R3)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测 (Windows)**: **3111 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16586 语句 / 156 未覆盖 / 5724 分支 / 143 partial; 门槛 98% 达标; 本轮 23.7s)
- 与 S2 基线(26-10-10-2103, 3064 passed)的差 **+47 条**: S3 同步既有 4 条字面量守阵时无净增, 增量全部来自会话期间上游带入的测试与登记表守阵在 `kb.index` 重建后的计数重算 —— 数字以本切片为准。
- e2e 行为不变式(计划 §6 S3 硬约束): `commands run dev.e2e` 全量 **136 passed / 10 skipped**(2.9m), 与改前基线(26-10-10-2104 会话切片记录)**逐位一致**。
- 红验: 登记表守阵 6 条 + 红验 2 条(S3 后复测, 出口外展开 / 未登记投递点均判红, 还原即绿)。
