# 测试基线 (单点事实源)

> 摘要: 全库的测试基线数字 (passed / skipped / 覆盖率 / 耗时) **只在本文件维护** ——
> README / AGENTS.md / progress.md / 各主题文档一律**引用**此处, 更新基线时只改这里。
> 触发: 基线, 测试数字, passed, skipped, 覆盖率, 耗时, 改了测试, 记基线, 数字对不上

## 当前基线

**1573 collected: 1570 passed + 1 skipped / Windows** —— 2026-09-25 **v2.6 通道时序与饿死残留修复实测**
(本条 **+11 条(1562 → 1573)**: 不完备窗口 ≥2×poll 参数化 3 条 + 页面失败仍补下载 1 条 + 下载阶段让位不计
tid 失败参数化 3 条(`test_hr_service.py`) · 扩展回传登录页 ⇒ HrLoginExpired 1 条(`test_hr_fetcher_channel.py`) ·
Retry-After 以 cooldown 封顶 1 条(`test_hr_ratelimit.py`) · 配额展示按窗口键折算 1 条(`test_hr_report.py`) ·
扩展 fetchBinary 登录页检测 1 条(`test_extension_proxy.py`, 真跑 node)。
★红验 7 条: 临时还原旧实现(60s 窗口 / 关页面失败补下载 / 吞让位异常计 tid 失败) ⇒ 上述 service 7 条全红, 还原后全绿。
扩展轮询 5 分钟 → 1 分钟(background.js)与 KIND_LOGIN_PAGE 全链路见计划 v2.6 变更行。
上一态(M4 多站点与打磨 +20 / 对方的 HR 取数实报修复 +15 · M3 判定联动 +16 · 日志等级修复 +7)
见 [baseline-history.md](baseline-history.md)。)
TOTAL **91%**(10872 语句 / 788 未覆盖 / 3574 分支 / 325 partial —— 并行采样; **HR 包 93%**:
2749 / 142 / 758 / 90), sidefx 台账并行汇总 / **越界 0**。
⚠ 本 AI shell 注入 `PYTHONUTF8=1` ⇒ `test_commands_engine` 两条 GBK 守阵在**本会话恒红**(2 failed);
`PYTHONUTF8=` 置空后复测 **2 passed** —— 已有记载的假红, 非回归(见下条 ⚠ 与 pitfalls/testing/patching.md)。
⚠ 另有 **47 条**包内脚本测试(`.commands/my-commit-flow/scripts/test_preflight.py`)—— 它们在
`testpaths(tests/)` **之外**, 走 `commands run test.pkg`, 已挂进提交闸门(`match = [".commands/", ".agents/skills/commands/"]`)。
⚠ `test_commands_engine.py` 两条 GBK 码页守阵在**本工具 shell 恒红**(注入 `PYTHONUTF8=1`, 见
[../pitfalls/testing/patching.md](../pitfalls/testing/patching.md)), `env -u PYTHONUTF8 -u PYTHONIOENCODING` 后全绿 —— 已有记载, 非回归。
Linux (WSL 沙箱) 未重测(仍是 1060 passed + 2 skipped)。

### 耗时(❗必须带区间)

**当前(2026-09-25 v2.6 通道时序修复)** —— 带覆盖率(即默认 `addopts`):
- **并行 `-n 4`(默认)**: **19.3 / 20.0 / 21.7s**(3 次采样: test.quick ×2 + test.full ×1)
- 串行 `-n 0 --no-cov`(对照): 本轮仅单文件抽查(≤1s), 未重测全量串行

⚠ 扩展守阵真跑 node(现为一次运行覆盖四个场景 + 登录页场景各一次) ⇒ 耗时比 M1 末态高约 5s, 属预期的环境成本。

**上一态(2026-09-25 M4 多站点与打磨)**: 并行 18.1 / 18.1 / 19.2s; 串行对照 35.25s(2026-09-24 采样)。

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
