# flaky 根因类目覆盖表

> 摘要: 每轮 flaky 冒头**先对表归因再修**的静态参照系 —— 十类根因 × 本仓库证据(坑档/实测) × 治理动作 × 治理阶段; 冒出无主类目先补类目再登记; tests-real 真时序轨的职责边界也在这里。
> 触发: flaky 归因, 根因类目, 覆盖表, 分类学, 十类, async-wait, 时序, 并发竞态, 顺序依赖, 平台差异, 随机数, 端口资源, 共享状态, 网络, UI randomness, 无主类目

> 口径单点: 计划 [26-11-05-0118](../plans/26-11-05-0118-plan-flaky-test-governance.html) §03(十类, 分类学参照 Tahir et al. 2023)。
> 动态登记(用例名/状态/处置)不在这里 —— 在 [flaky-ledger.md](flaky-ledger.md); 本文件是**类目参照系**, 两者
> 一次登记配合用: 新 flaky 先对下表归入类目, 再进台账记行(台账纪律见其头部)。

## 用法

- **每轮 flaky 先对表归因再修** —— 按证据链选类目, 修法随治理动作列走; retry 不是修复(台账口径)。
- **冒出无主类目再立条**: 现象对不上任何一类 → 先在下面表格补一行类目(写明本仓库首例证据), 再进台账; 不许硬塞进相近类目凑数。
- 归因先于修: 「真 bug 被误标 flaky」的风险口在计划 §07(产品侧竞态走 issue 修产品, 不改测试迁就)。

## 覆盖表

| 类目 | 本仓库证据(坑档/实测) | 治理动作 | 治理阶段 |
|---|---|---|---|
| async-wait/时序 | src 161 取时点 / tests 裸 sleep 63 处 / e2e 91 处 waitForTimeout(治理前实测) | 时钟注入(infra/clock 单点+构造期注入) + wait_until 条件轮询 + expect.poll | S2/S3/S4 |
| time(边界/粒度) | flaky-midnight-daycount / flaky-minute-stamp-dup / time-tick-collapse-strict-advance | 统一假钟(tests/clock.py)固定时间+区间断言 | S2/S3 |
| 并发/竞态 | poll-last-round-race / cross-thread-teardown-assert | 事件同步/条件轮询替代末值断言 | S3 |
| 顺序依赖 | xdist-worker-global-snapshot / hr-registry-pollution(已治) | pytest-randomly 周巡检(test.random-order)暴露 | S5 |
| platform | timing-tolerance(15.6ms 刻度) / ci-only-guard / coverage-floor-platform | platform_tolerance 容差单点+跨平台断言规范+守阵 | S5 |
| 随机数 | flaky-random-salt-hash-identity | 种子纪律(pytest-randomly 顺带重置 seed)+断言避开恒等映射 | S5 |
| 端口/资源 | fixed-port-test-collision(已治) / tests/_test_ports 单点 | 绑定位固定口守阵(.bind( 位 + 构造位绑定族, 配置值位不拦) | S1 |
| 共享状态 | fake-config-shared-mutables / importlib-sys-modules-dataclass(已治) | conftest 隔离单点+巡检暴露新例 | S5 |
| 网络 | 仅 tests-real 真网络面 | 真机轨职责, 不改造(见下「边界」) | — |
| UI randomness | iab-click-rerender-flake(已治) | 归入 e2e 清理与台账 | S4 |

## tests-real 真时序轨职责边界

**真实时序是 tests-real 的存在意义** —— 真机轨不做时钟改造、不注入假钟、不消灭真实等待:
那边 flaky 的处置只有两件事: **记台账**(对上表归入类目+状态+日期)与**按台账排期**, 修法仍回
本表治理动作列(改的是用例自身的等待/断言形态, 不是给被测系统换时钟)。把真时序轨也时钟化等于
取消第四条测试轨, 明令不做(计划 §06 D7)。

## 守阵与巡检(归因的机器面)

- 四类守阵(tests/test_flaky_timing_guards.py + tests/test_platform_tolerance_guards.py): 裸 sleep / waitForTimeout / 裸取时 / 绑定位固定口(bind 调用位 + ThreadingHTTPServer/socket.create_server 等构造位, 配置值位不拦), 新增即红 —— 防回潮, 不替代归因。
- 周巡检 `commands run test.random-order`(pytest-randomly 随机序采样): 顺序依赖/共享状态新例的探测器, 红灯固定 seed 复现归因后进台账; 巡检约定见 [flaky-ledger.md](flaky-ledger.md) 巡检段。
