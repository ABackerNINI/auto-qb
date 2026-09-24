# 测试基线 (单点事实源)

> 摘要: 全库的测试基线数字 (passed / skipped / 覆盖率 / 耗时) **只在本文件维护** ——
> README / AGENTS.md / progress.md / 各主题文档一律**引用**此处, 更新基线时只改这里。
> 触发: 基线, 测试数字, passed, skipped, 覆盖率, 耗时, 改了测试, 记基线, 数字对不上

## 当前基线

**1225 collected: 1224 passed + 1 skipped / Windows** —— 2026-09-24 实测
(计划/报告入库 W4: +10 条文档形态守阵 `tests/test_docs_forms.py` —— 命名 / meta / 状态词 /
索引自洽 / dark / 主键覆盖 / 认领链双向; 五条均已红验; 同日再 **+1**:
`test_frontend_cols_empty_hint_names_browser_clear_cause` —— 空存储提示必须点名浏览器站点级
"关闭窗口时清除"这条通道; 同日再 **+5**: WEB 事件循环断连噪音守阵 ——
降级为 INFO / 窗口节流 / 真 bug 不吞 / 判定矩阵 / 处理器装载(`lifecycle.py` 96%);
同日再 **+8**: `tests/test_commands_engine.py` —— commands 引擎的输出摘要与 id 解析
(异常行必须留在摘要里 / 短输出不截断 / 异常行封顶 / 小写 warnings 不算异常 / 截断提示 /
包路径限定 id / 未知 id 提示), 均已在还原版上红验;
同日再 **+9**: 同文件的 wrapper 守阵 —— 平台差异 / 归属标记 / 批处理写法约束 / CRLF 无 BOM / 幂等 /
拒改同名文件 / 向上找仓库根 / PATH 落点选择 / **端到端真跑 wrapper 转发参数**,
详见 [baseline-history.md](baseline-history.md));
TOTAL **91%**(7768 语句 / 623 未覆盖 / 2646 分支), sidefx 台账 2051 条 / **越界 0**。
⚠ 另有 **47 条**包内脚本测试(`.commands/my-commit-flow/scripts/test_preflight.py`)—— 它们在
`testpaths(tests/)` **之外**, 走 `commands run test.pkg`, 已挂进提交闸门(`match = [".commands/", ".agents/skills/commands/"]`)。
Linux (WSL 沙箱) 未重测(仍是 1060 passed + 2 skipped)。

### 耗时(❗必须带区间)

**当前(2026-09-23 末态: 系统层排除项调好 + 默认并行)** —— 带覆盖率(即默认 `addopts`):
- **并行 `-n 4`(默认)**: **7.61 / 7.79 / 8.87s**
- 串行 `-n 0`(对照): **21.15 / 21.56s**
- `-n 4 --no-cov`: 5.00 / 5.06 / 5.17s

**同日更早**(留档对照, 同一台机器 / 同一份代码 / 同一条命令, 均串行):
- 排除项调好之前: **19.37 / 19.38 / 19.81 / 20.16s**
- 只加文件安全白名单后: **53.51 / 56.37 / 60.06 / 62.41 / 73.66 / 80.68s**(中位 ~61s)
- 白名单前: **62.87 / 71.12 / 72.71 / 74.36 / 74.99 / 77.32 / 84.36 / 102.12 / 114.49s**(中位 ~75s)

> **本文件是这组数字的唯一枚举处** —— 其它文档只写量级与"见 baseline.md", 别再抄一遍(抄一份多一处漂移)。
> 上面的列表是**采样快照**, 不必随每次跑更新; 要更新的只是"范围 / 中位"这层结论。

- **单次数字没有意义** —— 报耗时必须带区间; 旧记录的"139.07s"同样是**单次采样**, 不宜再当基准。
- **覆盖率口径**: 并行 `7729 语句 / 623 未覆盖 / **219** 分支` vs 串行 `623 / **218**`, TOTAL 都是 **91%**
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
