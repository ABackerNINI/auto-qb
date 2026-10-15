# 3406 —— HR 测试夹具发现端口隔离(并行偶发 WARNING 污染 INFO 断言修复)

> 摘要: 修「`-n 8` 并行下 `test_hr_runtime.py` 两条「生命周期消息只记 INFO」断言偶发判红」——
> 根因是 `make_config` 未覆盖 `discovery_port`, 沿用模型默认**固定端口 18788**(候选表
> 18788/18789/18790 连号同样固定): 并行 worker 同绑 + 本机真实实例常驻 18788(netstat 实测
> PID 19168)⇒ 三个候选全被占 ⇒ `HrDiscoveryServer.start()` 记 WARNING「候选端口全部被占」⇒
> 污染 INFO 断言。**入池时猜的 `_free_port` TOCTOU 被反证推翻**(同样中招的用例用 `port=0`,
> 全程不调 `_free_port`, 能吐 WARNING 的唯一路径就是发现端点)。修法(纯测试侧, 产品代码零改动):
> `make_config` 默认 `discovery_port=0`(0 = 关闭发现) + `test_hr_discovery.py` 唯一依赖旧默认值的
> 用例显式自选端口 + 新增 1 条守卫用例防默认值回流。
> 坑档: memory-bank/pitfalls/testing/fixed-port-test-collision.md
> 基线时间: 2026-10-16 04:27

## TOTAL

```
TOTAL                                               17334    185   5842    160    98%
3406 passed, 4 skipped in 143.90s (0:02:23)
```

- 语句 17334 / 未覆盖 185; 分支 5842 / partial 160; 覆盖率 **98%**(`commands run test.full` 实测,
  Windows 侧; 提交闸门线 98%, 余量 0.49pp)。
- 连跑两次 TOTAL 逐位一致(148.75s / 143.90s 两次, 覆盖率数字相同)⇒ 本快照稳定, 非单次抖动。
- 相对上基线(26-10-16-0144): passed +1(新增守卫用例), 语句持平, 未覆盖 +3 / partial +2。
  已归因: 本轮**未减少任何 src/ 覆盖面** —— `test_hr_runtime.py` 不再启发现服务后,
  `HrDiscoveryServer` 的构造/start/bind/心跳路径由 `test_hr_discovery.py` 独立支撑(该文件是
  `HrDiscoveryServer` 的唯一直接构造方); `discovery.py` 现缺的 10 行(85/167/178/299-300/359/
  459/463/477-478)全是 XDG 路径、URL 边界、`status()`、退避重试、心跳异常等**故障注入路径**,
  与本次改动无关(±3 抖动带纪律见 [../../pitfalls/testing/parallel-run.md](../../pitfalls/testing/parallel-run.md))。
- 耗时: 143.90 ~ 148.75s(两次干净采样; 上基线 124.76s 为单次采样, 区间口径见
  [../baseline.md](../baseline.md) —— 本机有真实 auto-qb 实例常驻, 负载波动属正常, 不做单次差值结论)。
- **稳定性取证**(原问题就是并行偶发): 出问题的原始场景 `test.quick`(-n 8 并行全量)连跑两次
  3406 passed / 4 skipped; `test.full` 连跑两次同上; 确定性复验(占光三个候选端口后**串跑**两条
  锚点用例)修复前必红、修复后转绿。
- Linux(WSL) 侧未重测 —— 本轮纯测试侧改动, 无平台分支新代码, 存量平台守阵未动。
