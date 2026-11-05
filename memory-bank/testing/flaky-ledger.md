# flaky 台账

> 摘要: flaky / 恒红测试候选的**登记单点** —— 用例名 / 根因类目 / 状态 / 处置 / 日期; 每轮冒头先对表归因再修, retry 不是修复。
> 触发: flaky, 台账, 恒红, 日期炸弹, 端口碰撞, timing flake, 登记候选, 归因, 巡检, skip 清单, retries, 探测器

> 口径单点: 计划 [26-11-05-0118](../plans/26-11-05-0118-plan-flaky-test-governance.html) §03(根因类目十类)§06 D5/D9。
> **retry 不是修复**: pytest 主套件 reruns 恒 0; e2e CI `retries:1` 只是**探测器**(Playwright 报 flaky
> 的用例当场记进本台账并当场修)。修不了的走 skip(reason + issue 入池), 不养隔离区。
> **登记纪律**: 新增一行 = 用例名 + 根因类目(对 §03 十类; 冒出无主类目先补类目再登记) + 状态 + 处置 + 日期;
> 修完当场翻状态留一行去向( issue 链接/基线切片)。本台账只管**登记与状态**, 不承载修法细节(归计划/档案)。

## 台账

| 用例 | 根因类目 | 状态 | 处置 | 登记日期 |
|---|---|---|---|---|
| `e2e/gtm-alert.spec.mjs` gtm 弹窗双皮肤组 —— 硬编码日期 2026-11-03, 桩 TTL 24h 已过, **恒红**(非概率 flaky) | time(边界/粒度) | Open | 待入池/待修 | 2026-11-05 |
| `e2e/views.spec.mjs` 「种子页筛选器有数据」双皮肤**恒红** —— relocate kind 恒空(桩数据缺该类目), 不进 fast | 共享状态(桩数据缺口) | Open | 待入池/待修 | 2026-11-05 |
| `tests/test_hr_discovery.py` 生命周期层真绑定用例 —— `-n 8` 全量并行下偶发端口碰撞 | 端口/资源 | Open | 待入池/待修 | 2026-11-05 |
| `tests/test_hr_discovery.py::test_start_all_busy_returns_false_and_retries` —— 疑似 timing flake(退避重试窗口时序) | async-wait/时序(疑似) | Open | 待入池/待修 | 2026-11-05 |

> 状态词与四形态 5 词表同源: `Open` → `In Progress` → `Done` | `Dropped`。

## 巡检约定(S6 周巡检 job 引用)

**巡检入口单点**: `commands run test.random-order`(pytest-randomly 随机序采样; 主套件默认顺序
不受影响 —— 插件在 pytest.ini addopts 以 `-p no:randomly` 整体禁用, 只在该入口经 `-o addopts=`
替换加载)。每轮头部打印 `--randomly-seed=<N>` 可复现; 红灯固定 seed 复现归因后登记本台账,
reruns 不是修复(`-- --samples N` 多轮统计采样)。

周巡检(pytest-randomly 随机序采样)除随机序本身外, **顺带过两遍清单**, 偏离即红/登记:

1. **skip 清单**: 全库 `skip` 必须**带 reason + issue**(入池链接); 裸 skip(无 reason 或无 issue)按
   D5 口径当场补或当场修 —— 扫法: `grep -rn "test.skip\|pytest.skip\|skipif" tests/ e2e/` 对本台账与
   `issues/_index.md` 核对。
2. **本台账条目**: 逐条核状态 —— `Open` 超两周未动升优先级或显式 Dropped(写明理由);
   `Done` 的抽查一遍去向链接(基线切片/issue)未断; CI 探测器(retries:1)报出的 flaky 标记
   当场登记进台账并当场修(见上口径)。
