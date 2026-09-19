# 5000 种子仿真测试 · 使用手册

> **给谁看**：需要跑 / 判读 / 回溯这套测试的人与 AI。
> **做什么**：用一个**独立 HTTP 仿真服务端**冒充 qBittorrent，让**真实的 auto-qb 子进程**连上来跑，
> 在 5000 种子规模下测**安全**与**性能**。auto-qb 源码零改动、不进 CI、手动跑。
> **完整计划与全部实测数字**：[plans/26-09-19-1433-sim-client-5000-plan.html](plans/26-09-19-1433-sim-client-5000-plan.html)
> **已知缺陷与待办**：根目录 [`TODO.md`](../TODO.md)

---

## 1. 一句话心智模型

```
scripts/sim_run.py  ──起──>  scripts/sim_qb.py（假 qB，回环随机端口）
                    ──拉起─>  python -m auto_qb <本次生成的 config.yml>（真进程，经 sim_autoqb.py 包装）
                    ──收尾─>  统计层 summary.json/txt  +  完整层四路流水
```

- 仿真端实现的是 **qB WebUI 协议子集**（`sync/maindata` 的 rid 增量语义、写端点、虚拟文件树），
  客户端用的是**真实的 `qbittorrent-api`** —— 所以 JSON 序列化、HTTP 往返、rid 语义、Session 行为
  全都是真机成本。进程内替身测不到这些（实测：全量 205–240 ms vs 增量 3.3 ms，**差 62 倍**）。
- **auto-qb 是子进程、是黑盒**：所有结论只能从「它发了什么请求」和「服务端状态怎么变」推出来。

---

## 2. 前置条件

| 项 | 要求 |
|---|---|
| 依赖 | `uv sync`（仿真端只用标准库；子进程用项目 venv） |
| 工作根 | 默认 `R:\auto-qb-sim`，环境变量 `AUTOQB_SIM_ROOT` 可覆盖 |
| ⚠ R 盘 | **R 盘就是真实下载盘**。工作根必须含哨兵 `.auto-qb-sim-root`、不得是盘根目录或真实下载目录，否则**拒绝启动**（B1）。R 盘不存在时自动回退系统临时目录并记 `ROOT_FALLBACK` WARN，不硬崩。 |
| 文件树 | 每个种子物化 1 个 4 KiB 占位文件（辅种组共享）；5000 种子约 4400 文件 / 17 MB，建树数秒 |
| 端口 | 仿真端随机端口；auto-qb 自带 WEB UI 需显式 `--web-port`（另开一个，别撞 qB 的 16585） |

---

## 3. 如何运行

### 3.1 脚本清单

| 脚本 | 作用 |
|---|---|
| `scripts/sim_qb.py` | 仿真服务端。可独立运行供人工观察（`--self-test` 跑 8 项自检） |
| `scripts/sim_run.py` | **驱动器**：建树 → 生成配置 → 起服务 → 拉起 auto-qb → 注入场景 → 出两层日志 → 判 verdict |
| `scripts/sim_autoqb.py` | auto-qb 子进程启动包装（装 SIGBREAK 处理器）。**必须经它启动**，否则拿不到 `state.json` |
| `scripts/sim_baseline.py` | 一键跑 P1–P7 并固化阈值到 `plans/…baseline.json` |

### 3.2 最小示例

```bash
# 500 种子跑 40 秒，开 WEB 观测通道（强烈建议常开，见 4.4）
uv run python scripts/sim_run.py --scenario SMOKE --n 500 --duration 40 --web-port 18100
```

结束后打印 verdict + checks，并给出产物目录。**退出码 0 = OK，1 = FAIL**（WARN 目前不会产生）。

### 3.3 场景命令速查

```bash
# ---- 安全 ----
# S1 dry-run 零写
uv run python scripts/sim_run.py --scenario S1 --n 300 --duration 30 --dry-run --web-port 18101
# S5 断连降级（当前 FAIL = 已知缺陷 BUG-01）
uv run python scripts/sim_run.py --scenario S5 --n 300 --duration 45 \
    --abort-after 12 --abort-duration 10 --web-port 18111
# S6/S7/S8 一次跑齐（数据面只读 + WEB 并发只读 + 限速保护）
uv run python scripts/sim_run.py --scenario S6S7S8 --n 300 --duration 36 \
    --web-port 18120 --web-poll 4

# ---- 破坏性 ----
# D1 外部删种子（不带文件）     D2 带文件
uv run python scripts/sim_run.py --scenario D1 --n 300 --duration 30 --delete-torrents 3:20:no  --web-port 18201
uv run python scripts/sim_run.py --scenario D2 --n 300 --duration 30 --delete-torrents 3:20:yes --web-port 18202
# D3 auto-qb 主动删除（经其自带 WEB UI 投递命令）
uv run python scripts/sim_run.py --scenario D3 --n 300 --duration 40 --web-delete 4 --web-port 18203
# D4 外部删文件 → 缺文件保护（头号场景）
uv run python scripts/sim_run.py --scenario D4 --n 500 --duration 40 --delete-files 5:0 --web-port 18204
# D5 批量删除 + 重复投递 / 两相幂等
uv run python scripts/sim_run.py --scenario D5 --n 1000 --duration 48 \
    --delete-torrents 3:500:no --redeliver-removed 6 --web-port 18205
uv run python scripts/sim_run.py --scenario D5 --n 200 --duration 60 --interval 15 \
    --two-phase --with-rules --web-port 18206

# ---- 性能 / 基线 ----
uv run python scripts/sim_baseline.py                     # 全量 P1–P7（约 8 分钟）
uv run python scripts/sim_baseline.py --only P1,P3 --merge # 只跑部分并合并进已有基线
uv run python scripts/sim_baseline.py --dry                # 只打印将执行的命令
```

### 3.4 关键参数

| 参数 | 含义 |
|---|---|
| `--n` / `--beat` / `--active` / `--mode` | 种子数 / 每拍秒数 / 活跃比例 / `churn`（滚动换批，默认）或 `steady`（固定活跃池） |
| `--tick` | auto-qb 的 `main_tick`（写入生成的配置） |
| `--duration` | 运行时长（秒）；到点优雅停机 |
| `--web-port N` | **观测 + 命令通道**。开了才能拿到 auto-qb 自己的快照规模（判幽灵种子）、才能测 D3/S7 |
| `--delete-torrents K:N[:with-files]` | 第 K 拍删 N 个种子，可选连带删文件 |
| `--delete-files K:G` | 第 K 拍删第 G 个辅种组的文件 |
| `--redeliver-removed K` | 第 K 拍把已删 hash 重新投递一次（幂等） |
| `--abort-after/--abort-duration` | 第 N 秒断连 / 断多久（0 = 断到结束）。恢复时会把 rid 断层，逼客户端走全量自愈 |
| `--two-phase` / `--with-rules` | 连跑两轮 auto-qb 共用 `state_file` / 注入一条 `execute_once=once` 的规则（跨进程幂等的判据载体） |
| `--ramp N` | 渐进灌入：每拍新增 N 个种子（0 = 首轮全量） |
| `--baseline` / `--no-baseline` | 指定/禁用固化阈值文件 |
| `--stress` | 标记压力档：漂移等只观测不判红 |
| `--keep-last N` | 只保留最近 N 次运行目录（**默认 10，回溯前注意别被清理**） |

### 3.5 产物目录

```
R:\auto-qb-sim\runs\<时间戳-场景ID>\
├── summary.json / summary.txt    # 统计层：verdict + 每项 check（值/op/阈值/结论）—— 先看这个
├── trace.jsonl                   # 完整层①：每个 HTTP 请求（ts / 端点 / 参数 / 响应字节）
├── writes.jsonl                  # 完整层②：写端点台账（ts / endpoint / params）
├── sim-events.jsonl              # 完整层③：仿真端注入事件（删种子 / 删文件 / 断连 / ramp）
├── fs-before.txt / fs-after.txt  # 完整层④：文件树快照（相对路径 + 大小）
├── autoqb.log                    # auto-qb 子进程输出全文（已含 traceback）
├── config.yml                    # 本次运行生成的配置（可直接复现）
└── data\                         # auto-qb 的 state.json / 锁 / web.token / 程序日志
```

---

## 4. 如何甄别错误

### 4.1 只看统计层（10 秒判生死）

`summary.txt` 第一行就是 `verdict: OK | FAIL`。下面是 checks 表：

```
PASS     S2.risky_endpoints           value=0 == 0
FAIL     LOG.tracebacks               value=28 == 0
BASELINE S3.write_rate_per_min        value=4777.3 <= —
```

| result | 含义 | 处理 |
|---|---|---|
| `PASS` | 达标 | — |
| `FAIL` | 越过硬阈值 | **必须查**，从完整层回溯（见第 5 节） |
| `BASELINE` | 值或阈值缺失（阈值未固化 / 未观测到） | 不是失败；要么跑 `--web-port` 补观测，要么跑 `sim_baseline.py` 固化阈值 |
| `WARN` | 预留，目前不产生 | — |

### 4.2 红项对照表（按 id 定位）

| 红了的 id | 说明什么 | 第一反应 |
|---|---|---|
| `LOG.tracebacks` / `LOG.critical` | auto-qb 进程抛异常 | 直接翻 `autoqb.log` 找栈。**先排除停机噪音**（见 5.4） |
| `RUN.graceful_exit` | auto-qb 没优雅退出 ⇒ `state.json` **没落盘** | 多半是被硬 kill 或启动失败；看 `autoqb.log` 头部有没有「配置校验失败」 |
| `B4.fs_unexpected_removals` | 出现了预期外的文件删除 | **安全红线**。看 `fs-before/after` 差集，再对 `writes.jsonl` 里 `torrents/delete` 的 hashes |
| `S2.risky_endpoints` | 默认配置下命中了 delete / setLocation / reannounce / recheck / add | 安全红线。定位是哪个端点、谁触发的 |
| `D1.snapshot_final_match` / `D1.snapshot_drop` | auto-qb 快照与仿真端对不上（**幽灵种子**或漏同步） | 检查 `--web-port` 是否开了；再对 `torrents_removed` 是否上报 |
| `D1.writes_to_removed` | 对已删种子还在发写请求 | 同上；注意这条**单独看会空转**（打标签是一次性的） |
| `D3.delete_hashes_exact` / `delete_files_flag_match` / `delete_count` | 删错了对象 / `deleteFiles` 没透传 / 重复删 | 对 `writes.jsonl` 的 `torrents/delete` 记录 |
| `D4.group_stop_rate` < 1.0 | **辅种组没停全** = 会向站点上传垃圾数据（封号风险） | 最高优先级。看组内成员的 state 与缺文件扫描日志 |
| `D4.group_stop_lag_ticks` > 3 | 响应太慢 | 看该 tick 在干什么（trace 里按时间窗过滤） |
| `D5.exec_history_growth` > 0 | 跨进程幂等失效（`state_file` 去重没生效或没落盘） | 先确认 `D5.state_file_present` 是否也红 |
| `D5.state_file_present` | 第一相结束时 `state.json` 不存在/损坏 | 几乎总是**被硬 kill**（见 5.4） |
| `S6.data_dir_unexpected` | auto-qb 往 data_dir 写了白名单外的东西 | 看 `summary.data_dir_new` |
| `S7.http_errors` > 0 | WEB 只读端点返回 4xx/5xx | 看 `autoqb.log` 与 WEB 端口是否被占 |
| `S8.manual_limits_intact` | 手设限速被改写 | **先确认测试数据是奇数 KiB/s**（见 5.4 假红清单） |
| `SYNC.full_rounds` 超阈值 | rid 语义失效，退化成每轮全量（每轮多 200 ms） | 检查 rid 是否走 POST body |
| `SYNC.drift_max_s` 超阈值 | 主循环掉拍 | 先排除是灌入期 / WEB 轮询 / 压力档（这些另记 `P2.drift_max_s` 观测） |
| `P1.first_round_s` 超阈值 | 首轮灌入变慢 | 看 trace 里 `torrents/files` / `trackers` 的请求数与耗时 |

### 4.3 判定顺序（建议）

1. `verdict` 是不是 OK；不是就挑出所有 `FAIL`。
2. **先排除工具自身问题**（5.4 的假红清单），再怀疑 auto-qb。
3. 安全类红项（`B4.*` / `S2.*` / `D3.*` / `D4.*`）优先于性能类。
4. `BASELINE` 不是失败，但如果**本该有值却成了 BASELINE**（例如开了 `--web-port` 却还是 `D1.snapshot_final_match = None`），说明观测通道没通 —— 要查。

### 4.4 为什么强调 `--web-port`

它是**唯一的非空观测通道**：auto-qb 快照里到底还有几个种子，只能问 `/api/status`（读的是 `len(store.by_hash)`）。
不开它就拿不到 `D1.snapshot_*`，那两条会退化成 BASELINE —— **D1 的判据随之空转**。

---

## 5. 如何回溯

### 5.1 四路流水时间戳对齐

`trace.jsonl` / `writes.jsonl` / `sim-events.jsonl` **统一用 `time.time()`**，`autoqb.log` 用本地挂钟。
拿到一个可疑时刻 `T`，用 `sim-events.jsonl` 当锚点（注入事件），再按 `T ± 几秒` 去另外三路里捞。

```bash
# 注入了什么、什么时候
cat "R:\auto-qb-sim\runs\<run>\sim-events.jsonl"

# 某时刻之后发了哪些写请求
uv run python -c "
import json,sys
T=float(sys.argv[1])
for l in open(r'R:\auto-qb-sim\runs\<run>\writes.jsonl',encoding='utf-8'):
    r=json.loads(l)
    if r['ts']>T: print(r['endpoint'], r['params'])
" <T>
```

### 5.2 三个常用剧本

**A. 「快照里有幽灵种子」** —— 种子在仿真端删了，auto-qb 还在管它
1. `sim-events.jsonl` 找到 `delete_torrents` 的 `ts`；
2. `trace.jsonl` 只记**请求**不记响应体，所以先看客户端后续轮次带的 `rid` 是否正常递增；
   要确认服务端有没有真的上报 `torrents_removed`，去 `sim_qb.py` 的 `sync_maindata` 看逻辑，
   或临时给它加一行响应体日志（改前先备份，这是唯一需要动代码的排查手段）；
3. `writes.jsonl` 里该时刻 + 宽限后是否仍有这些 hash 的写请求；
4. 对照 `summary.snapshot_series`（观测到的 auto-qb 种子数曲线）—— 该跌未跌就是没上报。

**B. 「误删文件」** —— `B4.fs_unexpected_removals > 0`
1. `diff fs-before.txt fs-after.txt`，拿到缺失的相对路径；
2. 反查这些文件属于哪些种子（路径在 `<run>/fs/` 下，目录名即 save_path）；
3. 在 `writes.jsonl` 里找 `torrents/delete` 且 `deleteFiles=true` 的记录，比对 hashes；
4. 若不是 `torrents/delete` 造成的，去看 `torrents/setLocation` / 缺文件扫描相关日志。

**C. 「主循环掉拍 / 首轮太慢」**
1. `summary.sync` 的 `first_round_s` / `avg_interval_s` / `drift_max_s` 定位是哪一段慢；
2. `trace.jsonl` 按 sync 轮次切段，数每段内各端点命中数（首轮慢通常是 `torrents/files` + `trackers` 的请求数 bound）；
3. 若同时开了 `--web-poll`，对照一次**不开轮询**的相同参数运行 —— WEB 负载是首要嫌疑（见 PERF-01）。

### 5.3 复现

配置、文件树、负载全部由 `--seed`（默认 7）决定，同参数两次运行结论一致。
每次运行的 `config.yml` 都留在产物目录里，可直接：

```bash
uv run python scripts/sim_autoqb.py "R:\auto-qb-sim\runs\<run>\config.yml"
```

注意产物只保留最近 `--keep-last`（默认 10）次 —— **要留证据先加大这个值或把目录拷走**。

### 5.4 假红清单（先排除这些再怀疑 auto-qb）

| 现象 | 真因 | 处置 |
|---|---|---|
| `LOG.tracebacks` 红，栈里只有 uvicorn / h11 / asyncio，时间正好在停机那一刻 | 驱动器停机时掐断了正在飞的请求 | 已修（停机前 `quiesce` 先让观测收手）。若复现，检查是否在用 `sim_autoqb.py` 之外的方式启动 |
| `D5.state_file_present` 红 / `state.json` 不存在 | 被硬 kill（Windows `terminate()` = TerminateProcess，`finally` 不跑）。原生 `CTRL_BREAK_EVENT` 也只得到 0xC000013A | 必须经 `sim_autoqb.py` 启动 |
| `S8.manual_limits_intact` 红 | 测试数据造了**偶数** KiB/s。项目约定**奇数 KiB/s** 才算「用户手设、程序不覆盖」（`utils.is_manual_speed_limit`） | 改造数据 |
| `SYNC.drift_max_s` 在 `--ramp` / `--web-poll` / `--stress` 下红 | 这些场景的漂移本就是**观测对象**，不该用稳态阈值判 | 已改记 `P2.drift_max_s`（BASELINE）；确认参数 |
| 稳态漂移在 `--tick 1.5` 下恒红 | 老版本按写死的 2.0 基准算漂移 | 已修（按本次 `main_tick` 算） |
| 配置校验失败，auto-qb 秒退 | 生成的 config 有未知键。规则块必须在 `config:` **之内**且键名以 `_rules` 结尾；规则内没有 `log_level` 键 | 看 `autoqb.log` 首行，它会聚合列出全部错处 |
| `D1.snapshot_*` 是 BASELINE | 没开 `--web-port`，没观测通道 | 加上 `--web-port` |

---

## 6. AI 调用约定

**先读**：本文件 → 根目录 `TODO.md`（已知缺陷/待办） → `plans/…baseline.json`（当前阈值）。
**不要**：改 `src/`（本套测试定位是黑盒；要改代码另立任务档案并先跑红再跑绿）；把 `BASELINE` 当失败；只用写台账判断「种子还在不在」。

**标准流程**：

1. **跑** —— 按第 3 节选场景；**默认加 `--web-port`**（否则关键判据空转）。
   不确定规模就先小：`--n 300 --duration 30`。
2. **判** —— 读 `summary.txt`：`verdict` → 挑 `FAIL` → 对照 4.2 表 → **先过一遍 5.4 假红清单**。
3. **溯** —— 有 FAIL 才翻完整层：按 5.1 用 `sim-events.jsonl` 当时间锚点，按 5.2 选剧本。
4. **改** —— 只改 `scripts/` 或造数逻辑；改完**重跑同一条命令**确认 verdict 翻转。
5. **记** —— 新坑写进 `memory-bank/pitfalls.md`；新缺陷/待办写进 `TODO.md`；
   阈值变化跑 `scripts/sim_baseline.py --merge` 重新固化。

**给结论时请带上**：场景命令、`verdict`、红了的 check id 与值、产物目录路径。
只说「测试通过了」没有意义 —— 要说清**哪些判据真的测到了东西**。
