# 基线: WEBUI 选中×触发一致性 S4(运行时审计环)

- 主题: [../../activeContext/26-10-10-2103-webui-selection-trigger-parity.md](../../activeContext/26-10-10-2103-webui-selection-trigger-parity.md) · 计划 26-10-10-2001(S4, R4)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测 (Windows)**: **3112 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16586 语句 / 156 未覆盖 / 5724 分支 / 143 partial; 门槛 98% 达标; 本轮 28.6s)
- 与 S3 基线(26-10-10-2245, 3111 passed)的差 **+1 条**: 新增 T6 运行时审计接线守阵(`tests/test_webui_trigger_registry.py`)。
- 浏览器门禁: `npm run test:e2e:fast` **50 passed**(三皮肤装载 scope_audit.js 正常)。
- 审计红验(node 直跑): 正常载荷 ok / 重复目标 dup+按签名 warn 一次 / 形状越界 shape / 空载荷 empty(含 `{groupKeys,memberHashes}` 形状兼容) / 60 条挤出到 50 / 关态 O(1) 不碰环 —— 全部符合设计; 正式 e2e 红验(审计模式造不一致 → 环里出现记录)归 S5 矩阵。
