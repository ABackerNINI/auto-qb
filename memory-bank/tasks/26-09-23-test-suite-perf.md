# 26-09-23-test-suite-perf — 全量测试耗时归因与三处实测优化

**Status:** In Progress
**Added:** 2026-09-23
**Updated:** 2026-09-23
**Summary:** 全量测试耗时 **75s → 默认并行 7.6s**。根因是**环境**: 本机每次文件操作曾收固定开销(写 20ms / 删 43ms, 与数据量无关、三盘一致), 一次全量建 577 个临时目录; 用户两次调整系统层排除项后四类操作全部 <1ms ⇒ 串行 19.4s。代码侧另修三处框架开销: sidefx 收尾 4.7~9.0s → 1.04s、JS 语法守阵 7.4s → 0.38s(语义 8/8 对齐 `node --check`)、三处临时目录泄漏。**已上并行**: 加 `pytest-xdist` + `pytest.ini` 的 `addopts = -n 4`(默认), 并补 `workeroutput` 台账回传(并行下「越界 0」不再消失)。代码侧改动已提交推送 `1bde85d`; 并行部分待提交。C 方案实测被推翻, 未实施。

## 原始请求

> 当前的测试运行时间过长, 分析原因

后续三轮「继续」(按 `AGENTS.md` 请求边界, **均不构成授权**, 只做只读复核), 然后:

> 授权A-E, 另外我已将R:/Temp/auto-qb加入排除项, 等会测试一下是否生效

被授权的 A–E 是我在只读分析轮里提出的候选清单:

| 项 | 内容 | 结果 |
|---|---|---|
| A | `tests/sidefx.py` 的 `report()` 把 `violations` 提到循环外只求值一次 | ✅ 已实施并验证 |
| B | `tests/test_web.py` 的 20 次 `node --check` 合并为单进程批量 | ✅ 已实施并验证 |
| C | 把 basetemp 钉进 TMPDIR 以省掉会话起始的清理 | ❌ **实测推翻, 未实施**(见下) |
| D | 修 `tempfile.mkdtemp()` 的临时目录泄漏 | ✅ 已实施, 且多找到**第三个**站点 |
| E | 修 `memory-bank/testing/run.md` 里过期的耗时画像 | ✅ 已实施(连带 2 份活文档的同类漂移) |

## 思考过程与决策

### 根因(本任务的核心结论)

**本机每次文件操作收一笔固定"过路费": 写约 20ms、删约 43ms, 与数据量无关。**

| 盘 | 写 512B | 写 512KB | 删 512B | 删 512KB |
|---|---|---|---|---|
| R: (项目 TMPDIR) | 20.19ms | 20.86ms | 43.02ms | 10.26ms |
| D: (仓库所在盘) | 20.34ms | 20.79ms | 42.55ms | 14.60ms |
| C: | 20.86ms | 21.03ms | 43.06ms | 20.53ms |

判据与推论:

1. **写 512B 与写 512KB 同价** ⇒ 开销是"每次操作"的固定代价, 不是带宽 ⇒ 健康 SSD 应 <1ms, 本机慢 40~400 倍。
2. **三块盘完全一致** ⇒ 不是 R 盘的问题。项目文档里"R: 慢 / C: 快"的旧印象**据此推翻**(已回写 `techContext.md`)。
3. **删 512KB 反而比删 512B 便宜** ⇒ 小文件删除更贵, 指纹指向**按访问扫描 / 文件系统过滤驱动**,
   与 [../pitfalls/testing/tmpdir.md](../pitfalls/testing/tmpdir.md) 记的"删除拦截层"疑为同一机制。
4. **全量一次要建 / 删约 577 个临时目录**(2026-09-23 探针实测)⇒ 单这一项就是几十秒量级。
   由此所有耗时现象都能对上: 用例中位 40ms ≈ 写 2~3 个文件; 会话起始清 292 个目录 = 19.85s。

⚠ **杀软假设未被直接证据证实**: 想查 Defender 状态时 `sc.exe` 被沙箱的 Program Blacklist 拦掉,
PowerShell 的 `Get-MpComputerStatus` / `Get-MpPreference` 也无输出 ⇒ **只有性能指纹, 没有配置证据**。

### 关键取舍

1. **不引入 xdist 并行**(曾评估, 只读): 它未安装; 且项目文档里"绑固定端口不能并行"这条**事实有误**
   (`FakeQbServer` 用的是 `ThreadingHTTPServer(("127.0.0.1", 0))`, 端口是 0 = 由内核分配)。
   真正的拦路虎是另外两条: ①sidefx 守卫按**会话**记账, 分 worker 后**跨 worker 的越界不可见**
   ②一堆"睡眠容差"型守阵在并行负载下更易假红。⇒ 本轮不做, 记为后续候选。
2. **C 方案撤回(实测推翻)**: 原设想"把 basetemp 钉在 TMPDIR 内以省掉会话起始的清理"。
   实测 RUN G(basetemp 全新)= 56.56s 看着很美, 但 RUN H(**同路径再跑一次**)= 76.18s,
   其中 **setup 段 19.85s** —— 因为 `_pytest/tmpdir.py` 对**显式给定且已存在**的 basetemp 会先 `rm_rf`。
   ⇒ 只是把删除从"会话收尾"挪到"会话起始", **总量不变**。**未实施**, 并把这个反直觉点写进坑档。
3. **优化收益一律不看全量总时**: 见下「诚实结论」。
4. **B 的语义必须逐样本对齐**: 批量校验若用裸 `new vm.Script(src)` 会**凭空变严**
   (按经典脚本解析, 顶层 `return` 判错)。必须 `Module.wrap`。见
   [../pitfalls/testing/perf-measurement.md](../pitfalls/testing/perf-measurement.md) 第 4 条。

### 诚实结论: 别把 139s → 63s 全算成本次优化的功劳

改动后实测 **62~114s**(同一条命令多次, 中位约 75s), 而记录基线是 **139.07s**(单次采样)。但:

- A + B 两项**可归因**的收益只有约 **11~13s**(B 约 3.8s + A 约 3.5~7.8s)。
- 早期那几次大数字(124.48s 带 cov / 94.77s 不带)**是在我自己有并发负载时测的** ——
  对照两次 `--durations` 可见 sleep 型用例数字几乎不变(节流 1.53→1.54s), 而 CPU/IO 型整体膨胀。
  ⇒ **那些数字是被负载放大的**, 不能当作"改动前"的对照基线。
- 本机跨次波动可达 **±25%**, 偶发到 114s(同一条命令 20 分钟内两次跑出 71s 与 114s)。
- 所以基线数字必须带**区间**, 且必须**单进程空载**测 —— 已写进坑档与 `run.md`。

## 实现计划

- **A** `tests/sidefx.py`: `report()` 内 `violations` 提到 `for` 循环外(原写法每种 kind 重算一次 = 8 次,
  每次约 1600 条路径 × `os.path.realpath` 0.18~0.48ms ⇒ 约 1.4 万次 realpath)。
- **B** `tests/test_web.py`: 新增模块常量 `_NODE_SYNTAX_CHECK`, 把逐文件 `node --check` 改成
  `node -e <脚本> <文件...>` 单进程批量; 解析 stderr 按文件归位到 `problems`。
- **C** ❌ 撤回(见上)。
- **D** 三处临时目录泄漏改为"挂到 mgr 上"作生命周期锚点。
- **E** 三份活文档的过期耗时画像改为"量级 + 指向 `baseline.md` 单点"。
- **收尾** 新坑入 `pitfalls/testing/`、`tmpdir.md` 复发闭环、立档、基线回写、跑闸门。

## 子任务状态表

| ID | 内容 | 状态 | 更新 | 备注 |
|----|------|------|------|------|
| A | `sidefx.report()` 单次求值 `violations` | Complete | 2026-09-23 | teardown 4.71~8.97s → **1.04~1.20s**(A/B 插件 + 闸门跑双证) |
| B | 前端 JS 语法守阵改单进程批量 | Complete | 2026-09-23 | 7.375s → **0.378s**; `test_frontend_static_bundle_health` 4.06s → **0.27s**; POPEN 记录 20 → 1 |
| B′ | B 的语义等价验证 | Complete | 2026-09-23 | 8 个样本(6 故障 + 1 正常 + 1 顶层 `return` 边界)与 `node --check` **8/8 一致**; 入库常量再验 6/6 报错 + 0 误报 |
| C | basetemp 钉进 TMPDIR | Abandoned | 2026-09-23 | **实测推翻**: 只把删除从收尾挪到起始(RUN H setup 19.85s), 未实施 |
| D | 修 `tempfile.mkdtemp()` 泄漏 | Complete | 2026-09-23 | 3 处: `test_web.py` / `test_expr_eval.py` / **新发现** `test_trigger_events.py` |
| D′ | 泄漏量的机器判据 | Complete | 2026-09-23 | 探针实测: 每次全量建 **577** 个临时目录, 收尾残留 **2 → 1**; 剩下的 1 个是模块级持有者, 进程退出即回收 |
| E | 修过期耗时画像 | Complete | 2026-09-23 | `run.md` + 连带 `pitfalls/testing/tmpdir.md` / `techContext.md` |
| F | 用户加的排除项是否生效 | Complete | 2026-09-23 | 第一次(只加 `R:/Temp/auto-qb`)**未生效**; 第二次(**三盘 Temp**)写 20.19 → **0.58ms** 生效 |
| G | 跑闸门 + 回写基线 | Complete | 2026-09-23 | 最终树闸门 **1191 passed + 1 skipped / TOTAL 91% / 72.71s**, 越界 0; 耗时基线已改**区间**口径 |
| I | 白名单后复测 + 逐操作分解 | Complete | 2026-09-23 | 建 0.64 / 写 0.58 / `remove` 14.6 / `rmdir` 52.7ms; **沙箱外复测没变快** ⇒ 拦截在沙箱之外 |
| J | 临时目录 churn 量化 | Complete | 2026-09-23 | 577 个目录 × 45.5ms = **26.2s**, 占全量 **44%**(当前最大单项) |
| K | 并行评估(xdist) | Complete | 2026-09-23 | 最终: `-n 4` **5.00 / 5.06s** vs 串行 19.6s(约 4×), 波动极小 |
| M | 设置调整后复测(第三轮) | Complete | 2026-09-23 | 四类操作全部 **<1ms**; 串行 **19.37~20.16s**; 沙箱假设彻底排除 |
| L | 落地并行(`-n 4` 设为默认) | Complete | 2026-09-23 | 加 `pytest-xdist==3.8.0` + `pytest.ini` 加 `-n 4` + conftest 补台账回传; 默认 **7.6s**(串行 `-n 0` 21s) |
| N | 提交并推送 | Complete | 2026-09-23 | `1bde85d`; Gitee 与 GitHub `develop` 均一致; 无幽灵 diff |
| O | 闸门命令自带 `TMPDIR` | Complete | 2026-09-23 | `.commit-flow.toml` 的 pytest 闸门改为 `set "TMPDIR=…" && uv run pytest …`; **不导出 TMPDIR 跑预检 7 条全过** |

## 进度日志

### 2026-09-23 (只读分析三轮 → 授权实施 A-E)

- **第一轮(只读)**: 摸清"慢"的分布 —— `--durations` 里大项与用例数, 定位到测试框架自身开销
  (sidefx 收尾、会话起始 basetemp 清理、20 次 node 进程启动)占 64~84s 总时的 **约 27~36%**。
- **第二轮(只读)**: 怀疑"R 盘慢", 于是写探针 `pa_fs_probe.py` 实测三盘 —— **推翻该假设**,
  并发现真正的根因是"每次文件操作的固定开销"(上表)。
- **第三轮(只读)**: 据此撤回原方案 C(实测 RUN G/H 对照, 见上)。
- **第四轮(用户授权 A-E)**:
  - **A 落地**: `violations` 提到循环外。docstring 写明"为什么必须单次求值"。
  - **B 落地**: 新增 `_NODE_SYNTAX_CHECK` 常量 + 重写 `_scan_js_syntax_with_node`。
    ⚠ 中途踩坑: 第一版用裸 `new vm.Script(src)` 做等价验证, 发现与 `node --check` 在顶层 `return` 上**判定不同**
    ⇒ 改 `Module.wrap` 后 8/8 一致。**该坑是"优化顺手把判据改严"的典型, 已入坑档。**
  - **D 落地**: 三处。第三处 `test_trigger_events.py` 的 `_event_mgr` 是**探针查出来的**,
    不是读代码看出来的 —— 它的形态比前两处隐蔽: 用了 `with TemporaryDirectory()`,
    但 `mgr.state_file` 仍指向该路径, 后续 `seed_store` 写 state.json 会把目录**重新建出来**, 而持有者已销毁。
  - **E 落地**: 顺手发现 `pitfalls/testing/tmpdir.md`(32s/25s)与 `techContext.md`(1143 passed / "C 盘最快")
    是同一处漂移的三个副本 ⇒ 一并改成"量级 + 指向 `baseline.md`", 并把"C 盘更快"的旧印象标注为**已被实测推翻**。
- **踩到已记的坑(复发 +1)**: 用 `--basetemp=R:/Temp/auto-qb/pa_bt`(在 TMPDIR **之外**)跑全量,
  又是 4 failed + 1 error —— 与 2026-09-22 同形。**为什么没命中: 路由到了但文件没读** ——
  本轮读过 `testing/run.md`, 该文件末行明确指向 `pitfalls/testing/tmpdir.md`, 但没顺着点开就自己开测。
  已在 `tmpdir.md` 记 `复发: 2` 并补一句复核结论: **只要 basetemp 落在 `tempfile.gettempdir()` 之内就不假红**
  (`--basetemp=R:/Temp/auto-qb/tests/bt` 实测越界 0 条、守卫全绿)。
- **新坑入档**: [../pitfalls/testing/perf-measurement.md](../pitfalls/testing/perf-measurement.md) 四条 ——
  ①本机文件操作固定开销是耗时支配项 ②判断单项优化收益不能看全量总时 ③并发污染下的数字一律是假的
  ④批量替换 `node --check` 的语义坑。
- **实测(空载单进程, 未提交)**: 全量 `1191 passed + 1 skipped`(与基线收集数一致, 未增删用例),
  TOTAL 91%; 同一条命令多次实测得 **62~114s**(中位约 75s, 极差 1.8 倍)⇒
  **耗时基线改为区间口径**, 逐次数字只枚举在 `baseline.md` 一处。
  sidefx 台账 2036 条 / **越界 0**; 探针实测临时目录"建 577 个, 收尾残留 2 → 1";
  `check_kb_structure.py` 全部通过。
- **未做**: 提交 / 推送(等用户说「提交」); 杀软排除项复测(用户加完后**未生效**, 见 F 行)。

### 2026-09-23 (第二轮: 白名单复测 + 并行评估)

用户反馈"文件操作过路费可能是 WorkBuddy 的 sandbox / file security / auto-backup 导致", 并已把
**三盘 Temp 目录**加入文件安全白名单、关闭 auto-backup, 要求复测; 同时问"测试可以改为并行吗"。

**白名单复测 —— 部分生效, 且幅度很大**:

| 操作 | 加白名单前 | 加白名单后 | 结论 |
|---|---|---|---|
| `os.mkdir` | — | 0.64ms | ✅ 正常 |
| 写 512B | 20.19ms | **0.58ms** | ✅ **34×** |
| `os.remove`(文件) | 43.02ms | **14.60ms** | ❌ 仍被拦 |
| `os.rmdir`(空目录) | — | **52.72ms** | ❌ 仍被拦(**最贵**) |

- **粒度教训**: 第一次只加 `R:/Temp/auto-qb` **没用**; 按**三盘 Temp 目录**加才生效。
- **量化**: 一次全量建 **577 个临时目录**, churn 实测 **45.5ms/目录** ⇒ 删除类合计 **约 26.2s**,
  占全量 ~60s 的 **44%**。**这是当前最大单项, 比并行更该先修**(零框架风险)。
- **"不是沙箱"已用实测排除**: 关掉工具沙箱跑同一探针, `remove` 13.09ms / `rmdir` 111.73ms **没变快**
  ⇒ 拦截在沙箱**之外**。(`rmdir` 两次测得 52.72 / 111.73ms, 本机波动大, 别按单次下结论。)
- **串行全量**: 6 次 **53.51 / 56.37 / 60.06 / 62.41 / 73.66 / 80.68s**(中位 ~61s);
  白名单前是 62~114s(中位 75s)⇒ **中位 75 → 61s, 约 1.2×**。提升幅度**远小于 syscall 的 34×**,
  因为**删除仍是瓶颈**(写已经快了, 但删除类占全量 44%)。

**并行评估 —— 能用, 但结论是"先别纳入闸门"**:

- 数据(32 逻辑核, `--no-cov`, 每条都 `1191 passed + 1 skipped`): 串行中位 ~61s;
  `-n 4` 8 次 15.94 ~ **209.77s**(中位 ~31s); `-n 8` 73.96 / 118.47(**更差**); `-n 16` 35.42。
  ⇒ 中位 **约 2×**(最好 3.4×), 但**尾部更差**(最坏 210s > 串行最坏 80s)。
- **上限低的原因(实测)**: 新增探针 `pa_parallel_probe.py` 测**纯文件操作**的跨进程扩展性 ——
  N=1/2/4/8 吞吐 50.5 / 72.8 / 137.3 / 186.2 op/s ⇒ N=8 只有 **2.17×**, 底层有一层部分串行的拦截。
- **sidefx 守卫: 只失去打印, 没失去拦截**(用新插件 `pa_violate.py` 注入一条越界删除来验证)——
  串行与 `-n 4` **都**报 `AssertionError: 测试期出现 1 条越界的真实系统副作用`;
  但 `pytest_terminal_summary` 在 worker 上不输出 ⇒ 并行跑**看不到**「越界 0 条」那行。
- `--cov` 与 xdist 可共存(TOTAL 仍 91%), 但**分支计数与串行差 1**(218 vs 219)⇒ 换并行要重刷覆盖率基线。
- **纠正既有错误**: 文档里"`FakeQbServer` 绑固定端口所以不能并行"**事实有误** ——
  `tests/helpers.py:388` 用的是 `ThreadingHTTPServer(("127.0.0.1", 0), ...)`, 端口由内核分配。
- **决定(未改仓库)**: `-n 4` 记为**本地迭代快车道**; **闸门保持串行**; 若要把并行当闸门, 先补
  控制器侧台账聚合。**未加 `pytest-xdist` 依赖、未改 `.commit-flow.toml`** —— 等用户拍板。
- **新坑档**: `memory-bank/pitfalls/testing/parallel-run.md`(3 条); `perf-measurement.md` 第 1 条
  按白名单前后重写。

### 2026-09-23 (第三轮: 用户继续调整设置 → 删除也被治好, 全量 75s → 19.6s)

用户反馈"我已调整 WorkBuddyAI 设置, 再测试一下"。

**四类文件操作全部进入健康区间(<1ms)**:

| 操作 | ① 初始 | ② 只加白名单 | ③ 本轮(调整设置后) |
|---|---|---|---|
| `os.mkdir` | — | 0.64ms | **0.13ms** |
| 写 512B | 20.19ms | 0.58ms | **0.21ms** |
| `os.remove`(文件) | 43.02ms | 14.60ms | **0.16ms** |
| `os.rmdir`(空目录) | — | 52.72ms | **0.14ms** |

- **② → ③ 的差别不在沙箱**: 两轮复测**都**报 "Sandbox bypassed", 条件相同 ⇒ 差别来自用户的设置调整。
  (对照 ① 阶段同样是沙箱外, `remove` 13.09 / `rmdir` 111.73ms —— 那时慢。)⇒ **沙箱这条假设可以彻底排除**。
- **全量耗时(每条都 `1191 passed + 1 skipped`)**:
  | 方式 | 耗时 |
  |---|---|
  | 串行 | 19.37 / 19.38 / 19.81 / 20.16s |
  | `-n 2` | 8.56s |
  | **`-n 4`** | **5.00 / 5.06s** |
  | `-n 8` | 4.88s |
  | `-n 16` | 6.82s(更差, worker 启动成大头) |
  | `-n 4` + 覆盖率 | 7.61s(TOTAL 仍 91%) |
  ⇒ 相较最初的 75s 量级: **串行 3.8×, 并行 `-n 4` 约 15×**。
- **并行结论翻转(重要)**: 同日早些时候 `-n 4` 在 **15.94~209.77s** 乱跳(中位 ~31s, 尾部比串行最坏还差),
  当时判定"闸门保持串行"; 底层文件操作修好后同一命令变成 **5.00 / 5.06 / 4.88s**, **波动几乎消失**。
  ⇒ 那条否决理由**已不成立**, 改为**建议 `-n 4`**。教训: **"并行划不划算"取决于底层是否串行, 底层一改就要重测**。
- **仍存在的两个行为差异(未解决)**: ①sidefx **台账在并行下不打印**(拦截仍在, 前一轮已用注入实测);
  ②覆盖率与串行差 1 个单位(并行 `623 未覆盖 / 219 分支` vs 串行 `622 / 218`, TOTAL 都是 91%)
  ⇒ 若把并行设成默认要**重刷覆盖率基线**。
- **剩余耗时画像(串行 19.4s)**: 最慢条目已全是**真实睡眠**型
  (`test_main_loop_throttled_by_main_tick` 1.52s、两条 checking 各 0.91s、`test_local_qb_service` 一串 ~0.51s),
  3383 条 <5ms。⇒ **没有明显可再挖的大项**; 想更快只能上并行。
- **未改仓库**: 仍未加 `pytest-xdist` 依赖、未改 `.commit-flow.toml`(等用户拍板)。
  文档已按末态更新: `perf-measurement.md` 第 1 条重写为"已治好 + 定位三步"、`parallel-run.md` 整篇重写、
  `baseline.md` / `baseline-history.md` / `run.md` / `tmpdir.md` 同步。

### 2026-09-23 (第四轮: 提交 + 上并行)

用户: 「先提交然后上并行」。

**① 提交**: `1bde85d` ⚡️「全量测试耗时 75s → 19s: 修三处框架开销 + 修临时目录泄漏, 并回写知识库」
—— 15 个路径(4 份 `tests/` + 11 份 `memory-bank/`), 走 my-commit-flow 七步: 预检 → 闸门 7 条全过 →
逐路径暂存 → 提交并核 ref 三处一致 → 推 Gitee → 尝试一次 GitHub 镜像 → 查幽灵 diff(空)。
**Gitee 与 GitHub 的 `develop` 都是 `1bde85d`**(`ls-remote` 核对), 本地 HEAD 一致。

- ⚠ **踩到已记的坑**: 预检第一次跑闸门**红了** —— `uv run pytest tests -q --no-cov` 没带 `TMPDIR`,
  落回 `H:\Temp`, 撞上那个损坏的 `pytest-of-11059\pytest-current` reparse point(`PermissionError [WinError 5]`)。
  即 [../pitfalls/testing/tmpdir.md](../pitfalls/testing/tmpdir.md) 里那条**假红**。
  处置: 带 `TMPDIR="R:/Temp/auto-qb/tests"` 重跑预检即全绿。
  ⇒ **遗留**: `.commit-flow.toml` 的闸门命令**自己不设 TMPDIR**, 依赖调用者导出 —— 从工具 shell 跑
  `preflight.py` / `commit.py` 而忘了导出就会**假红**。本轮未改(属配置改动, 待拍板)。

**② 上并行(已落地)**:
- `pyproject.toml` dev 组加 **`pytest-xdist==3.8.0`**; `uv sync` 更新 `uv.lock`(带出 execnet 2.1.2)。
- `pytest.ini` 的 `addopts` 加 **`-n 4`** ⇒ **并行成为默认**; 注释里写明串行逃生口 `-n 0` 与两条注意。
- **`tests/conftest.py` 补台账回传**(并行下唯一真问题): worker 侧把台账写进 `config.workeroutput`,
  控制器侧用 xdist 钩子 `pytest_testnodedown` 从 `node.workeroutput` 收, 在 `pytest_terminal_summary` 里
  **汇总成一行**: `副作用台账(4 个并行 worker 汇总): 共 2034 条, 越界 0 条`。
  **有越界时**把该 worker 的全文打出来(比串行更好: 能看出是哪个 worker)。
- **实测**: 默认(并行, 带覆盖率)**7.61 / 7.79 / 8.87s**; 串行 `-n 0` **21.15 / 21.56s**;
  `-n 4 --no-cov` 5.00 / 5.06 / 5.17s。全部 `1191 passed + 1 skipped`。
- **守卫验证(注入法, 两次)**: 用 `pa_violate.py` 往仓库根注入一条越界删除 ——
  串行与 `-n 4` **都**报 `AssertionError: 测试期出现 1 条越界的真实系统副作用`(拦截没丢);
  且汇总行正确打出「越界 4 条」+ 四个 `--- worker N 有越界 ---`(可读性也回来了)。
- **覆盖率口径**: 并行 `7729 / 623 / 2636 / **219**` vs 串行 `623 / **218**`, TOTAL 都是 91%
  ⇒ **分支 partial 多 1, 语句数一致**(早先记的"623 vs 622"有误, 已改正)。

**③ 闸门自带 TMPDIR(用户: 「将TMPDIR加入.commit-flow.toml, 然后提交」)**:
- `.commit-flow.toml` 的 pytest 闸门改为
  `set "TMPDIR=R:/Temp/auto-qb/tests" && uv run pytest tests -q --no-cov`(TOML **字面串**写法,
  免得为内层双引号转义)。
- **踩坑与判据(都实测过)**: ①预检用 `subprocess.run(shell=True)`, Windows 上解析到 **COMSPEC → cmd.exe**
  (`echo %COMSPEC%` → `C:\WINDOWS\System32\cmd.exe`), 所以 POSIX 的 `TMPDIR=x cmd` 前缀**不生效**(实测 rc=1);
  ②cmd 的 `set VAR=value && cmd` 会把 `&&` 前的空格**并进 value** —— 实测 TMPDIR 变成
  `'R:/Temp/auto-qb/tests '`(带尾随空格), 必须写成 `set "VAR=value" && cmd`;
  ③查过闸门 schema 无 `env` 键(`GATE_KEYS = {match, run, note, auto, timeout}`, 未知键即 STOP),
  所以只能走 shell 写法。
- **验证**: **不导出 TMPDIR** 直接跑 `preflight.py` → 7 条闸门全过(pytest 那条 **5.7s**)。
- **提交**: `f469492` ⚡️「测试改为默认并行(-n 4): 全量 21s → 7.6s, 并让闸门自带 TMPDIR」——
  13 个路径。Gitee `develop` = `f469492` ✅; **GitHub 镜像滞后一个提交**(`1bde85d`),
  按纪律只报一次、不重试。无幽灵 diff。
