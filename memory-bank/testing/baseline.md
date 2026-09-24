# 测试基线 (单点事实源)

> 摘要: 全库的测试基线数字 (passed / skipped / 覆盖率 / 耗时) **只在本文件维护** ——
> README / AGENTS.md / progress.md / 各主题文档一律**引用**此处, 更新基线时只改这里。
> 触发: 基线, 测试数字, passed, skipped, 覆盖率, 耗时, 改了测试, 记基线, 数字对不上

## 当前基线

**1468 collected: 1467 passed + 1 skipped / Windows** —— 2026-09-24 实测(**合流后**)
(本轮 **+91 条**: **HR 在线核实 M2 取数通道** —— 新增 `tests/test_hr_channel.py`(协议 / 密钥 /
origin 与 URL 白名单) / `test_hr_queue.py`(派发式队列 + 叫停与恢复) / `test_hr_server.py`(端点路由
与真 HTTP 往返、401/403/400/413/404、端口冲突 fail-fast) / `test_hr_fetcher_channel.py`(ChannelFetcher
超时 / 失败 / 白名单 / 叫停) / `test_hr_worker.py`(取数线程 + 视图只在变化时抬 revision + 告警节流) /
`test_hr_runtime.py`(运行时门面 + 热重载重挂 + 关停不必等满超时); 覆盖 `src/auto_qb/hr/` 全部模块
(**86–100%**; 新模块 server 90% / channel 92% / fetcher 93% / runtime 94% / worker 97% / queue 97%) +
`config/schema/hr.py` 100%; 逐次增量的完整流水见 [baseline-history.md](baseline-history.md));
**同日再 +2 条**由另一会话并行落地(合流前它基于 M1): WEB UI **多选右键菜单目标 = 整个选中集合**
(`test_web.py::test_frontend_ctx_menu_multi_select_targets_selection`) + **生成物重建提示指错命令**
(`test_memory_bank.py::test_gen_cmd_hints_name_real_tasks`) —— 两边改动有 3 个文件重叠, 按
「移出改动 → `merge --ff-only` → 施回改动」合流(细节见 [baseline-history.md](baseline-history.md))。
TOTAL **91%**(10217 语句 / 763 未覆盖 / 3382 分支 / 304 partial), sidefx 台账 2353 条 / **越界 0**。
⚠ 另有 **47 条**包内脚本测试(`.commands/my-commit-flow/scripts/test_preflight.py`)—— 它们在
`testpaths(tests/)` **之外**, 走 `commands run test.pkg`, 已挂进提交闸门(`match = [".commands/", ".agents/skills/commands/"]`)。
Linux (WSL 沙箱) 未重测(仍是 1060 passed + 2 skipped)。

### 耗时(❗必须带区间)

**当前(2026-09-24 M2 合流后: 新增 6 个文件 / 91 条 + 真 socket 与线程用例)** —— 带覆盖率(即默认 `addopts`):
- **并行 `-n 4`(默认)**: **17.61 / 17.18 / 17.64s**
- 串行 `-n 0 --no-cov`(对照): **30.16s**

⚠ M2 用例含真回环 socket、线程启停与「等扩展回传」场景 ⇒ 整体比 M1 末态(~9s)慢约一倍;
其中一处 10s 级浪费是**真缺陷**(关停时线程正阻塞等扩展回传, 白等到 `request_timeout`)——
已修为「先叫停队列再 join」, 并有 `test_stop_is_prompt_while_waiting_for_extension` 守死。

**上一态(2026-09-24 M1 末态)**: 并行 7.61–8.87s / 串行 21.15–21.56s / `-n 4 --no-cov` 5.00–5.17s。

> **本文件是这组数字的唯一枚举处** —— 其它文档只写量级与"见 baseline.md", 别再抄一遍(抄一份多一处漂移)。
> 上面的列表是**采样快照**, 不必随每次跑更新; 要更新的只是"范围 / 中位"这层结论。

- **单次数字没有意义** —— 报耗时必须带区间; 旧记录的"139.07s"同样是**单次采样**, 不宜再当基准。
- **覆盖率口径**: **当前**并行 `10217 语句 / 763 未覆盖 / 3382 分支 / 304 partial`, TOTAL **91%**。
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
