# 测试基线 (单点事实源)

> 摘要: 全库的测试基线数字 (passed / skipped / 覆盖率 / 耗时) **只在本文件维护** ——
> README / AGENTS.md / progress.md / 各主题文档一律**引用**此处, 更新基线时只改这里。
> 触发: 基线, 测试数字, passed, skipped, 覆盖率, 耗时, 改了测试, 记基线, 数字对不上

## 当前基线

**1596 collected: 1595 passed + 1 skipped / Windows** —— 2026-09-25 **HR 超龄豁免(判定侧豁免 + 翻页早停)**
(本条 **+17 条(1579 → 1596)**: 判定收口超龄豁免 7 条(`test_hr_resolve.py`)+ 取数侧行过滤与翻页早停 8 条
(`test_hr_service.py`)+ 门面透传 1 条(`test_hr_runtime.py`)+ 配置解析与取值范围 1 条(`test_hr_config.py`);
新键 `trackers.<站>.hr_check.completed_age_limit`(0=关闭, 默认不变)。动机与取舍见档案
`26-09-22-backend-partial-hr-verify` 与计划 v2.8; 上一态见 [baseline-history.md](baseline-history.md)。)
TOTAL **91%**(10849 语句 / 791 未覆盖 / 3598 分支 / 327 partial —— 并行采样), sidefx 台账并行汇总 / **越界 0**。
⚠ 本 AI shell 注入 `PYTHONUTF8=1` ⇒ `test_commands_engine` 两条 GBK 守阵在**本会话恒红**(2 failed);
`PYTHONUTF8=0` 后复测 **2 passed** —— 已有记载的假红, 非回归(见 [../pitfalls/testing/patching.md](../pitfalls/testing/patching.md))。
⚠ 另有 **47 条**包内脚本测试(`.commands/my-commit-flow/scripts/test_preflight.py`)—— 它们在
`testpaths(tests/)` **之外**, 走 `commands run test.pkg`, 已挂进提交闸门(`match = [".commands/", ".agents/skills/commands/"]`)。
Linux (WSL 沙箱) 未重测(仍是 1060 passed + 2 skipped)。

### 耗时(❗必须带区间)

**当前(2026-09-25 HR 超龄豁免)** —— 带覆盖率(即默认 `addopts`):
- **并行 `-n 4`(默认)**: **19.9 / 36.8s**(2 次采样; 后者为同机其它 clone 并行工作时的负载离群, 前者为常态)

**上一态(2026-09-25 扩展运行日志)**: 并行 17.6 / 19.8 / 19.9 / 20.5s(test.quick ×1 + test.full ×3)。

**更早(2026-09-25 v2.8 明细表改版)**: 并行 18.3 / 18.7 / 19.1s(test.quick ×1 + test.full ×2)。

**更早(2026-09-25 v2.6/v2.7 通道时序 + 增量落盘 / M4 多站点)**: 并行 19.3 / 20.0 / 21.7s 与 18.1 / 18.1 / 19.2s。
⚠ 扩展守阵真跑 node(现为一次运行覆盖四个场景 + 登录页场景各一次) ⇒ 耗时比 M1 末态高约 5s, 属预期的环境成本。

⚠ M2 用例含真回环 socket、线程启停与「等扩展回传」场景 ⇒ 整体比 M1 末态(~9s)慢约一倍;
其中一处 10s 级浪费是**真缺陷**(关停时线程正阻塞等扩展回传, 白等到 `request_timeout`)——
已修为「先叫停队列再 join」, 并有 `test_stop_is_prompt_while_waiting_for_extension` 守死。

**上一态(2026-09-24 告警分档 + `--hr-status`)**: 并行 16.88–21.40s / 串行 30.93s。

> **本文件是这组数字的唯一枚举处** —— 其它文档只写量级与"见 baseline.md", 别再抄一遍(抄一份多一处漂移)。
> 上面的列表是**采样快照**, 不必随每次跑更新; 要更新的只是"范围 / 中位"这层结论。

- **单次数字没有意义** —— 报耗时必须带区间; 旧记录的"139.07s"同样是**单次采样**, 不宜再当基准。
- **覆盖率口径**: **当前**并行 `10872 语句 / 788 未覆盖 / 3574 分支 / 325 partial`, TOTAL **91%**(HR 包 93%)。
  下面这组"并行 vs 串行"的对照取自 2026-09-23 采样(结论不变, 数字不再逐轮重采):
  并行 `7729 语句 / 623 未覆盖 / **219** 分支` vs 串行 `623 / **218**`, TOTAL 都是 **91%**
  ⇒ 换默认并行后**分支 partial 多 1**(语句数一致)。
- **成因(单点: [../pitfalls/testing/perf-measurement.md](../pitfalls/testing/perf-measurement.md))**: 本机每次文件操作
  曾收一笔**固定开销**(初始 写 20ms / 删 43ms, 三盘一致、与数据量无关; 一次全量建 577 个临时目录 ⇒ 约 26s)。
  **已由系统层排除项治好** —— 现 `mkdir` 0.13ms / 写 0.21ms / `remove` 0.16ms / `rmdir` 0.14ms(全部 <1ms)。
  ⇒ 这 3.8× 来自**环境**, 不是代码优化。
- **并行**: 已是**默认**(`pytest.ini` 的 `addopts = -n 4`, dev 依赖 `pytest-xdist==3.8.0`);
  单文件排查用 `-n 0`。台账回传与覆盖率差异见
  [../pitfalls/testing/parallel-run.md](../pitfalls/testing/parallel-run.md)。

⚠ throttle 守阵(`test_run_loop_throttles_without_stop_event`)文件级/全量跑偶发假红(Windows sleep(50ms) 精度 46ms < 0.05 下限, 容差无余量), 单跑恒绿 —— 已入池 [issues/26-09-22-2052-test-throttle-test-sleep-tolerance.html](../issues/26-09-22-2052-test-throttle-test-sleep-tolerance.html), 稳态数字取自 deselect 该用例的全量。

> ⚠ **只测一侧就更新会立刻产生漂移** —— 改了基线就把 Windows 与 Linux 两侧**都重测**再落数字。
> 两侧**收集数相同**但 passed 可能不同(Windows 专属用例在 Linux 上 skip), 比较时别拿 passed 直接比。

## 变更流水

逐次增量的完整流水(最近在上)已外迁 → [baseline-history.md](baseline-history.md)。
