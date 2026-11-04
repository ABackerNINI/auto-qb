# 5364 passed, 2 skipped —— S2 其余叶子域时钟注入后全量基线

> 摘要: 5364 passed, 2 skipped —— S2 其余叶子域时钟注入后全量基线
> 基线时间: 2026-11-05 04:35
**Refs:**

## 验收数字

`commands run test.full` 实测(2026-11-05, 8 worker 并行, 覆盖率门开启):

- 汇总行: `5364 passed, 2 skipped, 1 warning in 122.28s (0:02:02)`
- 覆盖率 TOTAL: `TOTAL 24496 52 8388 34 99%`
- 口径注记: passed/skipped 与上一基线持平(5364/2, 零新增零丢失); 耗时为本次实测瞬时值
  (本机波动面, 不作判据)。守阵四条(tests/test_flaky_timing_guards.py)全绿 ——
  src/ 裸取时白名单清空(24→0 处, S2 其余叶子域 11 文件 24 处条目删净, 只减不涨),
  **src/ 裸取时归零(除 clock.py 单点本体豁免), S2 收口判据达成**。

## 本改动面

flaky 治理计划 26-11-05-0118 S2 第 4/4 域提交(收口): 其余叶子域(cli/rules/infra/tools 口径下的
存量尾段)生产时钟注入(D8), 白名单 ALLOW_TIME_SRC 清空。

- 构造期注入(1 文件): TorrentStore 收 `clock: Optional[Clock] = None`(缺省 SYSTEM_CLOCK,
  模块属性现取) —— expect 追平调度 4 点与 state_since 基准/state_age 2 点走 `self._clock.now()`
  (与主循环调度 now 及落盘 ts 同侧, 挂钟语义), own_writes 登记与 TTL 逐出 2 点走
  `self._clock.monotonic()`(纯内存时长, 单调语义)。
- 叶子单点(10 文件 16 点, SYSTEM_CLOCK): 挂钟侧 `now()` —— alias_fs 探测记录戳 1 点,
  relocate_journal 心跳/心跳年龄/pid 锁戳 3 点, store_recovery 留证文件名戳 1 点,
  transfer reannounce 限频(与 state_file 落盘历史戳同侧)1 点, record HR 判定锚点 1 点,
  tray uptime 起点/展示 2 点; 单调侧 `monotonic()` —— port_owner 探针预算 deadline/剩余 2 点,
  utils 资源管理器置前等待预算 2 点, full_checking 组内校验等待超时 2 点,
  base 条件求值错误同因节流 1 点(等待预算/节流间隔按取时纪律归单调侧, 阻塞预算不入假钟)。
- 白名单: tests/flaky_allowlist.py 删 ALLOW_TIME_SRC 全部 11 条目(24 处, src 组清空)。
- 测试面(仅修被本任务破坏的用例): test_port_owner 预算耗尽用例的 `port_owner.time.monotonic`
  打桩改 patch `port_owner.SYSTEM_CLOCK`(刻度替身, 语义不变); test_store_recovery 静态守阵
  单点指纹 `.bad-{int(time.time())}` 随单点实现更新为 `.bad-{int(SYSTEM_CLOCK.now())}`。
