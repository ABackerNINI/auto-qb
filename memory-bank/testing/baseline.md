# 测试基线 (口径与警告)

> 摘要: 测试基线数字**一条基线一个切片**存放在 `baselines/`, 最新一条 = 单点事实源, `commands run kb.baseline` 列最近 3 条;
> 本文件只承载记录体例 / 常驻警告 / 耗时与覆盖率口径, **不存任何基线数字**。
> 触发: 基线, 测试数字, passed, skipped, 覆盖率, 耗时, 改了测试, 记基线, 数字对不上

## 口径 (2026-09-26 切片化定案: ①每文件一条基线 ②脚本列最近 3 条 ③不设 _index)

- **记录新基线 = 新建切片文件**: `baselines/YY-MM-DD-HHMM-<slug>.md`, 三行头
  `# <数字> —— <事件>` / `> 摘要:` / `> 基线时间: YYYY-MM-DD HH:MM`(排序键, 选填 `> 档案:`),
  正文放 TOTAL / 耗时 / 增量明细 —— 体例照最新一条切片抄。**切片写完不改**(不可变的一次性快照)。
- **看基线**: `commands run kb.baseline`(默认最近 3 条, 最新一条恒为当前事实源; 排障 `--all` / `-n N` 看全量)。
- **无 `_index.md` 是特性, 也不许补** —— 时间戳文件名即索引, 缓存式索引比没有更危险。
- **其它文档一律引用不手抄**: README / AGENTS.md / progress / 各主题文档只写量级与"见 kb.baseline",
  数字抄一份多一处漂移。
- **更早流水**: 2026-09-24 及更早的逐轮条目已一并切片化入 `baselines/`(按 `--all` 查);
  append-only 时代轮转出去的最老段在 [attachments/baseline-history-archive.md](attachments/baseline-history-archive.md)
  (冷库, 仅供深排障)。

## 常驻警告 (看数字前先读)

⚠ 另有 **47 条**包内脚本测试(`.commands/my-commit-flow/scripts/test_preflight.py`)—— 它们在
`testpaths(tests/)` **之外**, 走 `commands run test.pkg`, 已挂进提交闸门(`match = [".commands/", ".agents/skills/commands/"]`)。
Linux (WSL 沙箱) 未重测(仍是 1060 passed + 2 skipped)。

⚠ throttle 守阵(`test_run_loop_throttles_without_stop_event`)文件级/全量跑偶发假红(Windows sleep(50ms) 精度 46ms < 0.05 下限, 容差无余量), 单跑恒绿 —— 已入池 [issues/26-09-22-2052-test-throttle-test-sleep-tolerance.html](../issues/26-09-22-2052-test-throttle-test-sleep-tolerance.html), 稳态数字取自 deselect 该用例的全量。

> ⚠ **只测一侧就更新会立刻产生漂移** —— 改了基线就把 Windows 与 Linux 两侧**都重测**再落数字。
> 两侧**收集数相同**但 passed 可能不同(Windows 专属用例在 Linux 上 skip), 比较时别拿 passed 直接比。

## 耗时与覆盖率口径 (❗报耗时必须带区间)

- **单次数字没有意义** —— 报耗时必须带区间; 旧记录的"139.07s"同样是**单次采样**, 不宜再当基准。
  每轮的采样快照随该轮切片存档(见 `baselines/` 各条的"耗时"行), 不必随每次跑更新; 要更新的是"范围 / 中位"这层结论。
- **覆盖率口径**(方法示例, 数字为 2026-09-23 采样): 并行 `10853 语句 / 789 未覆盖 / 3598 分支 / 326 partial`,
  TOTAL **91%**(HR 包 93%); "并行 vs 串行"对照: 并行 `7729 语句 / 623 未覆盖 / **219** 分支` vs 串行 `623 / **218**`,
  TOTAL 都是 **91%** ⇒ 换默认并行后**分支 partial 多 1**(语句数一致; 结论不变, 数字不再逐轮重采)。
- **成因(单点: [../pitfalls/testing/perf-measurement.md](../pitfalls/testing/perf-measurement.md))**: 本机每次文件操作
  曾收一笔**固定开销**(初始 写 20ms / 删 43ms, 三盘一致、与数据量无关; 一次全量建 577 个临时目录 ⇒ 约 26s)。
  **已由系统层排除项治好** —— 现 `mkdir` 0.13ms / 写 0.21ms / `remove` 0.16ms / `rmdir` 0.14ms(全部 <1ms)。
  ⇒ 这 3.8× 来自**环境**, 不是代码优化。
- **并行**: 已是**默认**(`pytest.ini` 的 `addopts = -n 4`, dev 依赖 `pytest-xdist==3.8.0`);
  单文件排查用 `-n 0`。台账回传与覆盖率差异见
  [../pitfalls/testing/parallel-run.md](../pitfalls/testing/parallel-run.md)。
