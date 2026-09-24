# testing — 测试 / 冒烟 / 仿真纪律

> **本文件是生成物, 不要手改** —— 由 `commands run kb.index` 扫描本目录主题文件的三行头元数据生成; 新增 / 改名 / 改摘要后重跑即可, 冲突也只需重跑。
> 库内细路由见 [memory-bank/README.md](../../README.md)。
> **检索纪律**: 先读本索引定位, 再按需打开单个主题文件 —— **不要整读本目录**。
> **摘要**: 跑全量与临时目录、平台差异与打桩、断言有效性(恒真/恒红/量错对象)、浏览器冒烟、桩与仿真保真度、真机语料。
> **触发**: 测试, pytest, 跑全量, 临时目录, TMPDIR, 断言, 红验, 冒烟, 仿真, 语料, 脱敏

## 主题

| 主题 | 一句话 | 触发词 |
|---|---|---|
| [assertions.md](assertions.md) | 恒真 / 恒红 / 安慰剂 / 量错对象 —— 断言失去意义的所有已知形态, 以及红验与 A/B 归因的纪律。 | 写断言, 红验, 反向对照, 阈值, 恒真, 摆设断言, 顺序断言, 冒烟失败归因, flaky, 反查表长度, infohash v1 v2 |
| [corpus-capture.md](corpus-capture.md) | `scripts/qb_capture.py` 实施时实测的一批坑 —— 代理、rid 序列、秒分辨率时钟、伪名化撞车、判据空壳。 | 抓语料, 脱敏, qb_capture, 代理, rid, 伪名化, 等价类判据, 红验, argparse |
| [corpus-fs-mock.md](corpus-fs-mock.md) | 脱敏要连"藏在 .gz 里的第二层 key"一起做; 窗口合并必须按序推进; 回放 config 的 tracker 段不能只信权威映射。 | 语料回放, disk.json, fs mock, 窗口合并, tracker 段, 脱敏 key, 反查表, group_exact |
| [parallel-run.md](parallel-run.md) | **已设为默认**(`pytest.ini` 的 `addopts = -n 4`) —— 全量 21s → **7.6s**(带覆盖率); sidefx 台账已用 `workeroutput` 回传汇总, 「越界 0 条」不再消失; 串行排查用 `-n 0`。覆盖率分支 partial 与串行差 1。 | 并行, 并发跑测试, xdist, -n, 加速, 多进程, 跑得慢, 闸门, 端口冲突, 台账不打印 |
| [patching.md](patching.md) | 「Windows 全绿 / Linux 全红」的四类根因与"归错类比不修更危险"的教训 —— 平台相关测试必须以 `monkeypatch` 固定平台; 另记一条**本工具 shell 注入 `PYTHONUTF8=1` 造出的假红**。 | CI 红, Linux CI, 平台差异, monkeypatch, WSL, normcase, dir_fd, 平台专属模块, 码页, GBK, cp936, PYTHONUTF8, 假红 |
| [perf-measurement.md](perf-measurement.md) | 本机每次文件操作的**固定过路费**(初始 写 20ms / 删 43ms, 与数据量无关)曾支配全量耗时 —— **已由系统层排除项治好(全量 75s → 19.4s, 并行 5.0s)**; 另记"判断单项优化收益不能看全量总时"与"并发污染下的数字一律是假的"两条度量纪律。 | 测试慢, 耗时, 性能, 优化收益, 归因, 全量多久, 跑得慢, durations, 度量, 并发跑, 白名单, 排除项, 杀软, 沙箱 |
| [side-effects.md](side-effects.md) | 测试不得产生真实系统副作用, 由 `tests/sidefx.py` 记账 + 会话级守阵兜底 —— 收尾有越界项即让本次 pytest 失败。 | 加测试, 越界, 副作用, sidefx, subprocess, 落盘, state_file, 并发跑测试 |
| [smoke.md](smoke.md) | `ui_harness.py` + `ui_smoke.cjs` 是本仓库唯一能覆盖前端渲染的手段; 这里是它的环境坑与验证手法。 | 浏览器冒烟, ui_smoke, Playwright, Edge, 白屏, 前端改完, 时序复现, 聚合行状态色 |
| [stubs-sim.md](stubs-sim.md) | 测试替身"长得像"不等于"够用"; 仿真端最容易变成"自以为在测"的测假陷阱。 | 写替身, FakeClient, FakeTorrent, FakeQbServer, sim_qb, 仿真, 判据空壳, 反向对照, caplog, 日志断言, 回执判定, FakeConfig, 假配置, 新配置键 |
| [tmpdir.md](tmpdir.md) | 临时目录必须在 `tempfile.gettempdir()` 之下、覆盖率文件不能留仓库根、`TMPDIR` 不设会让会话收尾崩。 | 跑全量, basetemp, TMPDIR, 临时目录, 覆盖率文件, COVERAGE_FILE, pytest-current, 耗时 |
