# 3376 —— HR 通道「去端口+跨机」实施基线(计划 26-10-14-1241 S0–S7 落盘)

> 摘要: 实施计划 26-10-14-1241 全步完成后的全量基线: 配置面三新键(host/discovery_port/pairing)+ port 默认 0;
> 新发现端点与实例注册表(hr/discovery.py)+ 配对码门; 扩展 normalize 判据放开 + discovery.js + 发现/配对 UI。
> 新增 tests/test_hr_discovery.py + 扩展守阵扩充(discovery.js 双向协议守阵 / 发现流程 node 实跑)。
> 开工基线(同一工作树 S0 时点)为 3351 passed / 4 skipped —— 差值不在此抄, `commands run kb.baseline -n 2` 现列。
> 档案: memory-bank/tasks/26-10-15-backend-hr-channel-portless-remote.md
> 基线时间: 2026-10-15 13:24

**Refs:** memory-bank/tasks/26-10-15-backend-hr-channel-portless-remote.md, memory-bank/plans/26-10-14-1241-plan-hr-channel-portless-remote.html

## TOTAL

```
TOTAL                                               17287    180   5830    156    99%
3376 passed, 4 skipped in 133.11s (0:02:13)
```

- 语句 17287 / 未覆盖 180; 分支 5830 / partial 156; 覆盖率 **99%**(`commands run test.full` 实测, Windows 侧)。
- 耗时区间口径见 testing/baseline.md(单次采样, 带区间才有意义); 本次全量两次采样 132.29s / 133.11s。
- Linux(WSL) 侧未重测 —— 本轮无平台分支新代码(候选表/退避均为纯逻辑), 存量平台守阵未动。
