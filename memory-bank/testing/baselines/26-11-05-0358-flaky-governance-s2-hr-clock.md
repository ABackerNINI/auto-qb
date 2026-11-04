# 5364 passed, 2 skipped —— S2 hr 域时钟注入后全量基线

> 摘要: S2 hr 域时钟注入后全量基线
> 基线时间: 2026-11-05 03:58
**Refs:**

## 验收数字

`commands run test.full` 实测(2026-11-05, 8 worker 并行, 覆盖率门开启):

- 汇总行: `5364 passed, 2 skipped, 1 warning in 117.42s (0:01:57)`
- 覆盖率 TOTAL: `TOTAL 24491 52 8388 34 99%`
- 口径注记: passed/skipped 与上一基线持平(5364/2, 零新增零丢失); 耗时为本次实测瞬时值
  (本机波动面, 不作判据)。守阵四条(tests/test_flaky_timing_guards.py)全绿 ——
  src/ 裸取时白名单 71→59 处(S2 hr 域 5 文件 12 处条目删净, 只减不涨)。

## 本改动面

flaky 治理计划 26-11-05-0118 S2 第 2/4 域提交: hr 域生产时钟注入(与既有
runtime.sleeper 等待注入口径对齐)。

- 生产 5 文件 12 点(src/auto_qb/hr/**): runtime.sleeper(2 处等待预算)/queue.wait(2 处
  等待预算)/channel.ChannelStatus.silent_for(1 处展示叶子)/ratelimit.now_ts(1 处叶子)/
  report(6 处 CLI 报告叶子: run_hr_once 起止计时 2 / run_hr_status now 1 /
  run_hr_confirm_empty 对账戳+提交戳 2 / _print_site ago_text 1)。
- 注入口径: **等待预算(runtime.sleeper / queue.wait)走 `SYSTEM_CLOCK.monotonic()` 单点**
  —— 保真实单调钟, 与 queue.wait 既有纪律「阻塞预算不入假钟(假钟只服务 now_fn 的 TTL 与
  频控)」一致, 也与 runtime.sleeper 的可调用注入形态对齐(sleeper= 注入面原样不动, 中断
  语义只靠 _sleep_stop 事件, 不另设第二套等待注入; 同构于 core 域 _wait_next 等待原语的
  叶子处理)。**挂钟叶子走 `SYSTEM_CLOCK.now()` 单点**(channel.silent_for /
  ratelimit.now_ts / report 六点) —— 挂钟语义逐点保源(与落盘 ts 同侧相减/落盘戳), 行为
  零漂移。hr 既有可注入面(queue/service/worker/server/fetcher/discovery 的 now_fn 与
  service 的 sleeper)原样不动; 组件构造签名不变(未加 clock 参数 —— 本域 12 点全部为
  等待预算与叶子, 无需可替换挂钟面, S3 如需假钟控制 TTL/频控走既有 now_fn)。
- tests/: flaky_allowlist.py 删 5 文件 12 处条目 + 头部计数 71→59(22 文件)更新;
  测试零改动(无用例依赖这 12 点的模块 time 寻址面, 定向 hr 套件 434 用例先行全绿)。
