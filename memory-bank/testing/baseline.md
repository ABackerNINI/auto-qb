# 测试基线 (单点事实源)

> 摘要: 全库的测试基线数字 (passed / skipped / 覆盖率 / 耗时) **只在本文件维护** ——
> README / AGENTS.md / progress.md / 各主题文档一律**引用**此处, 更新基线时只改这里。
> 触发: 基线, 测试数字, passed, skipped, 覆盖率, 耗时, 改了测试, 记基线, 数字对不上

## 当前基线

**1527 collected: 1526 passed + 1 skipped / Windows** —— 2026-09-25 **合流后实测**(树上同时含双侧本轮改动)
(合流前各自实测 ——
①对方 **+16 条: M3 判定联动**(1520 collected 那轮) —— 站点侧三态接进 `TorrentRecord`(`hr_link` 稳定引用 + 读取时现算),
四个消费点调用点未动; 新增用例: 收口判定 `judge_record` 7 条(`tests/test_hr_resolve.py`, 含「站点未接入 ⇒ None(不适用)
vs 未核实」「多 infohash 取更保守者」「站点侧达标结论与展示值」「mode=all 未列出恒受管束」) · 门面 `judge()` 3 条
(`tests/test_hr_runtime.py`) · 记录接入 4 条(`tests/test_torrents.py`: 转移种子 downloaded=0 也受管束 / 安全放行 /
回落本地三道门 / store 挂桥) · 锚点提供者 1 条(`test_qbmanager.py`) · WebUI 三态与站点侧值 1 条(`test_web.py`) ·
另加替身对齐(`FakeTracker` 补 `hr_check` / `FakeTorrent` 补 `hr_judgement`·`hr_anchor`)。
★红验(2 处反证, 共 4 红): 旁路判定桥 ⇒ 记录接入 2 条红; 「站点未接入返回判定而非 None」⇒ 不适用两条红。
②本轮 **+7 条: 运行日志按等级查看修复**(1384 collected 那轮) —— 生产 `config.yml` 的 `log.format` 是
`%(asctime)s - %(levelname)s - %(message)s`(无方括号), 旧 `/api/log` 过滤按字面量 `[WARNING` 捞 ⇒ 恒空。
`tests/test_logging.py` +4(`filter_log_lines` 格式形状矩阵 / 多行记录跟随 / "筛不了"提示语 / 字段宽度与 `%%` 变体) +
`tests/test_web.py` +3(生产格式按等级过滤 / 多行 traceback 跟随记录 / 两种"筛不了"回全部行 + `note`);
旧 `test_api_log_endpoint` 重写为**样本由被测配置渲染**(旧版手写语料 + 替身 format=`%(message)s` ⇒ 配置没被读到, 摆设断言)。
7 条新用例已做红验: 临时还原旧字面量实现 ⇒ 7 条全红。完整流水见 [baseline-history.md](baseline-history.md)。)
TOTAL **91%**(10581 语句 / 779 未覆盖 / 3512 分支 / 310~311 partial —— 合流后并行采样),
sidefx 台账 2469 条(并行汇总, 单次采样) / **越界 0**。
⚠ 另有 **47 条**包内脚本测试(`.commands/my-commit-flow/scripts/test_preflight.py`)—— 它们在
`testpaths(tests/)` **之外**, 走 `commands run test.pkg`, 已挂进提交闸门(`match = [".commands/", ".agents/skills/commands/"]`)。
⚠ `test_commands_engine.py` 两条 GBK 码页守阵在**本工具 shell 恒红**(注入 `PYTHONUTF8=1`, 见
[../pitfalls/testing/patching.md](../pitfalls/testing/patching.md)), `env -u PYTHONUTF8 -u PYTHONIOENCODING` 后全绿 —— 已有记载, 非回归。
Linux (WSL 沙箱) 未重测(仍是 1060 passed + 2 skipped)。

### 耗时(❗必须带区间)

**当前(2026-09-25 M3 判定联动)** —— 带覆盖率(即默认 `addopts`):
- **并行 `-n 4`(默认)**: **18.3 / 18.9 / 19.3s**(3 次采样)
- 串行 `-n 0 --no-cov`(对照): **35.25s**(上一态采样, 本轮未重测串行)

⚠ 扩展守阵真跑 node(现为一次运行覆盖四个场景) ⇒ 耗时比 M1 末态高约 5s, 属预期的环境成本。

⚠ M2 用例含真回环 socket、线程启停与「等扩展回传」场景 ⇒ 整体比 M1 末态(~9s)慢约一倍;
其中一处 10s 级浪费是**真缺陷**(关停时线程正阻塞等扩展回传, 白等到 `request_timeout`)——
已修为「先叫停队列再 join」, 并有 `test_stop_is_prompt_while_waiting_for_extension` 守死。

**上一态(2026-09-24 告警分档 + `--hr-status`)**: 并行 16.88–21.40s / 串行 30.93s。

> **本文件是这组数字的唯一枚举处** —— 其它文档只写量级与"见 baseline.md", 别再抄一遍(抄一份多一处漂移)。
> 上面的列表是**采样快照**, 不必随每次跑更新; 要更新的只是"范围 / 中位"这层结论。

- **单次数字没有意义** —— 报耗时必须带区间; 旧记录的"139.07s"同样是**单次采样**, 不宜再当基准。
- **覆盖率口径**: **当前**并行 `10581 语句 / 779 未覆盖 / 3512 分支 / 310~311 partial`, TOTAL **91%**(合流后采样)。
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
