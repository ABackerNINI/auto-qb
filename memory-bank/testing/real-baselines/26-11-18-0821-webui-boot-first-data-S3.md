# S3 真机验收: 修复后复测 —— 提前发布落地生效, 空代窗口从「持续到管线结束」收缩为「落库前一瞬」(计划 26-11-18-0259 S3)

> 摘要: 计划 26-11-18-0259 的 S3 步(修复后复测, HEAD = e16527ab 含 S1 提前发布; 与 S0 修复前基线 011e1aeb 同口径对比)。环境2 副实例 56590, 沿用 S0 留存的同一批 210 枚 `real-fake` 假种子(复测前后均核对 210/210 stalledUP, 种子状态零扰动)。产品用派生配置(schema_version 8 / WEB 39000 免鉴权 / grouping on / 非 dry-run)经 `run_s0_boot.py` 受控重启, 三次启动: 标准轮 ×2(显式 `--interval 0.25 --fetch-timeout 10`, 与 S0 逐字对齐) + 探测轮 ×1(`--interval 0.03 --fetch-timeout 0.1`)。**标准轮: flat/singles/shows 首份数据 = 首响应(1.081s / 1.092s), groups 第二跳 1.859s / 1.871s** —— 形态与 S0 标准轮一致(该形态下首请求本就晚于落库, S1 不改变此形态)。**探测轮(修复试金石): 首响应仍是 0 行空代(竞态可复现), 但空窗只持续一拍 —— 基础代在 +0.941s(空代 +0.050s 后)即含 flat 210 / singles 210 超集 / shows 105, groups 由完整代 +2.187s 补齐; 代际恰三跳(空代 → 基础代 → 完整代)**。S0 同场景空代持续到 gen2(+2.421s, flat 空 1.49s)—— **「空窗持续到管线结束」被修复消灭, 空窗收缩为 0.050s(一拍)**。硬判据(flat/singles/shows ≤2s)三轮全 PASS; groups 第二跳时刻已记录并回写 issue ②。
> 复测时间: 2026-11-18 08:16-08:17(环境2; `real.env`→实例核验→`real.seed.list`→标准轮×2→探测轮×1→`real.seed.rm` 清种; 未跑 `real.guard`——避免 pause 改掉 S0 同口径的 stalledUP)
> 复测 commit: e16527ab(feat/webui-boot-first-data, 含 S1 提前发布 + S2 守阵; 本轮无提交动作)

**Refs:** memory-bank/plans/26-11-18-0259-plan-webui-boot-first-data.html

## 01 环境与造场(沿用 S0 留存, 复测前后核对)

- 环境2(C盘机), `real.env` 确认: 主 56589 / 副 56590, 均活(实测 `connection_status=firewalled`, §2.4 合规口径); 主实例 56589 全程 0 种子未动。
- **种子 = S0 留存的同一批**(S0 拍板留存至 S3 复测后清): 复测前 `real.seed.list` 核对 `共 210 个种子, 其中自造 210 个(标签 real-fake)`, 全部 `stalledUP`; 复测后再次核对状态未变(产品派生配置 `check_missing_files: false` / `missing_tag: ""` 零写路径, 三轮停机 relocate 停机 `tag_failures=0 resume_failures=0`)。
- 未跑 `real.guard`(本步拍板: guard 会无差别 pause 全部种子, 破坏 S0 同口径的 stalledUP 前置; 白名单安全由工具自身的端口钳制兜底 —— `run_s0_boot.py` `--qb-port` 只认白名单 56589/56590, 派生配置只写 `tests-real/.work/` 之下)。
- 清理(用户已拍板 S3 后清): 复测全做完后 `commands run real.seed.rm -- --all --yes` 批量删除, qB 内归零(`共 0 个种子` / maindata torrents=0), 数据文件全删净(`.work/seeds/boot/` 下 0 文件残留; 210 个空目录壳留在 gitignored 工作区, 非本轮授权清理面, 只报告)。未跑 `real.seed.clean`(.work 顶层测量证据目录会触发其拒跑守卫, 且证据要留)。

## 02 产品启动方式(与 S0 同款, case 目录换新)

- 驱动: `tests-real/tools/run_s0_boot.py`(S0 同款; 评审 minor 8 后驱动 `--interval` 缺省已改 0.15, 故标准轮**显式传** `--interval 0.25 --fetch-timeout 10` 与 S0 实跑口径逐字对齐)。派生配置由工具生成(RM08 基座形状): `schema_version: 8` / qb 127.0.0.1:56590 免凭据 / `grouping.enabled: true` / `interval: 60S`+`sync_interval: 1.5S` / `web: 127.0.0.1:39000 + skip_local_verify: true` / trackers `boot-fake` domains=[127.0.0.1] 命中假种子 announce / `fs.path_map` 不配(Windows 宿主直跑, 自检段 no-op, pathmap 基线口径不变)。
- case 目录换新不复用 S0 产物: 标准轮 `tests-real/.work/s3boot/`, 探测轮 `tests-real/.work/s3boot-race/`(S0 的 `s0boot/`、`s0boot-race/` 原样保留)。
- 起法: `runner_s0.py` 进程内 `cli.main` 非 dry-run(WEB 真启); 优雅停 = touch stopfile → 进程内 SIGTERM(§2.6 唯一优雅路径, 全程零 taskkill)。三轮 rc=0, 「停止」+「relocate 停机」日志齐全, stderr 全空。

## 03 测量结果(三次启动, t0 = 产品进程 spawn; 测量口径同 S0)

| 轮 | spawn(墙钟) | web 首响应 | flat(torrents) | singles | shows | groups | 全齐 | 优雅停 |
|---|---|---|---|---|---|---|---|---|
| run1(标准, 0.25/10) | 08:16:54.308 | +1.081s | **1.081s**(210) | **1.081s**(210→收缩 0) | **1.081s**(105) | **1.859s**(210) | 1.859s | rc=0 / 1.19s |
| run2(标准, 0.25/10) | 08:17:00.364 | +1.092s | **1.092s**(210) | **1.092s**(210→收缩 0) | **1.092s**(105) | **1.871s**(210) | 1.871s | rc=0 / 1.05s |
| 探测轮(0.03/0.1) | 08:17:21.334 | **+0.891s(0 行空代)** | **0.941s**(210) | **0.941s**(210→收缩 0) | **0.941s**(105) | **2.187s**(210) | 2.187s | rc=0 / 1.23s |

- 标准轮两轮 `error=None`(停条件「四视图全非空」满足), 探测轮也 `error=None` —— **S1 的基础代 singles=210 超集使探测轮停条件可满足**(S0 探测轮该停条件不可满足、跑满 150s error 收场的形态不复存在, 旁证修复生效)。
- 三轮优雅停 1.19s / 1.05s / 1.23s —— S0 run2 的「SIGTERM→退出 38.75s」计划外观察项本轮未复发(观测样本 +3, 仍未定位挂点, 维持只报告)。

代际序列(`rid_sequence`, rid = 启动时间戳秒起步):

- **标准轮形态**(首请求晚于落库, 与 S0 标准轮同形态): 恰两代。gen1(rid=启动时间戳秒, 首请求触发): flat 210 / **singles 210(全量超集)** / shows 105 / groups 0; gen2(rid+1, 管线结束): flat 210 / **singles 0(收缩)** / shows 105 / groups 210。gen1→gen2 间零新代。
- **探测轮形态**(首请求早于落库 = S0 §05 竞态原样复现): **恰三跳**。gen1(rid=启动时间戳秒): 四视图全 0 空代(首请求 web bind 后即刻, fetch_s 0.026)→ **gen2(rid+1): flat 210 / singles 210 超集 / shows 105 / groups 0 —— S1 基础代, 落库后立即发布, 距空代仅 +0.050s(一拍)** → gen3(rid+2): groups 210 / singles 收缩 0, 管线结束完整代。**S0 同场景的「空代持续到 gen2(+2.421s)」窗口不复存在** —— 空窗从 ≈1.49s(S0: +0.928→+2.421)收缩为 0.050s(+0.891→+0.941, 30ms 轮询粒度下仅一拍)。

## 04 首轮管线时间窗(产品日志锚点 ↔ HTTP 时间线对照)

run1 日志锚点(spawn 08:16:54.308; `tests-real/.work/s3boot/data/logs/auto-qb.log`):

```text
08:16:54.308  spawn(t0)                    [driver t0_epoch]
08:16:55.048  日志初始化完成                +0.74
08:16:55.052  启动 qB 管理器                +0.74
08:16:55.126  WEB UI 已启动 :39000          +0.82   ← web bind
08:16:55.360  WEB 跳过本地验证…免密钥放行     +1.05   ← 首个 /api/state 请求到达
08:16:55.390  gen1 响应完成                  +1.08   [HTTP 时间线: 210/210/105/0(基础代)]
08:16:55.629  全量轮补建种子级任务 210 个     +1.32
08:16:55.630  检测到新增种子 210 个          +1.32   ← apply_sync + path_map 自检(no-op) + full_round(210 tracker 单发) 完成
08:16:56.168  gen2 发布(HTTP 观测)           +1.86   ← 归组 files 单发 + post 冲突检查 + flush_views 完成时刻
```

探测轮日志锚点(spawn 08:17:21.334; `tests-real/.work/s3boot-race/data/logs/auto-qb.log`): 日志初始化 +0.73 → WEB up +0.83(22.165) → **首请求到达 +0.88(22.218, 早于落库)→ gen1 = 0 行空代(HTTP +0.891)** → **gen2 基础代(HTTP 观测 22.276, +0.941; S1 提前发布点在 apply_sync 落库后、full_round 尾段前)** → 检测到新增种子 210 个 +1.53(22.868) → gen3 完整代 +2.187(23.521)。

| 窗 | S3 run1 | S3 run2 | S3 探测轮 | S0 run1 | S0 run2 | S0 探测轮 |
|---|---|---|---|---|---|---|
| [WEB up → 检测到新增种子] | 0.504s | 0.501s | 0.703s | 0.489s | —(未单列) | 0.831s |
| [检测到新增种子 → 完整代 HTTP 观测] | 0.538s | 0.611s | 0.653s | 0.596s | 0.506s | 0.734s |

- 管线窗与 S0 同量级 —— S1 只**提前**发布基础代, 不移动管线本身; [检测到新增 → 完整代] 段(files 单发 210 次 + post + flush)原样保留, 就是 issue ② 的残差代价面(0.51-0.65s, files ×210 ≈ 0.45s 占主体, S0 微基准口径不变)。
- 探测轮新增分解面(S0 无此中间代可分): [首请求空代 → 基础代] = **0.050s**(apply_sync 落库 + 提前发布 —— 这就是「空窗」的全部残存); [基础代 → 检测到新增] = 0.592s(full_round 210 tracker 单发尾段, 非 issue ② 范围); [检测到新增 → 完整代] = 0.653s(issue ② 残差窗)。基础代→完整代全程 1.245s = 0.592 + 0.653(基础代 22.276 → 完整代 23.521, 日志 epoch 口径; HTTP offset 显示值端点相减为 1.246, ±0.001 舍入差)。
- `path_map_selfcheck`: 派生配置 fs.path_map 依旧不配, 自检段照旧 no-op ≈ 0ms —— 与 S0 基线一致, **issue ③ 无新增面**(窗量级与 S0 相同), 未回写。

## 05 修复前后对比与硬判据判定(plan §04 S3 / §01 D9)

标准轮(S0 修复前 vs S3 修复后; 同种子同配置同口径, 分视图首份数据, t0=spawn):

| 视图 | S0 run1 | S0 run2 | S3 run1 | S3 run2 |
|---|---|---|---|---|
| flat | 1.113s | 1.101s | **1.081s** | **1.092s** |
| singles | 1.113s(210→0) | 1.101s(210→0) | 1.081s(210→0) | 1.092s(210→0) |
| shows | 1.113s | 1.101s | 1.081s | 1.092s |
| groups | 1.893s | 1.639s | **1.859s** | **1.871s** |

- 标准轮形态本就「首请求晚于落库」, S1 不改变该形态(首响应即含数据) —— 数字同量级吻合, 亦验证 S1 对非竞态路径零行为变化。

探测轮(修复试金石, 首请求早于落库):

| 观测面 | S0(修复前) | S3(修复后) |
|---|---|---|
| 首响应 | +0.928s, 0 行空代(竞态命中) | +0.891s, 0 行空代(**竞态仍可复现 —— 符合预期, 空代=落库前请求, 非缺陷**) |
| **空窗持续** | **到 gen2 = +2.421s(≈1.49s 全空)** | **到基础代 = +0.941s(0.050s, 一拍)** ← **修复目标命中** |
| flat 首份 | 2.421s | **0.941s** |
| singles 首份 | 恒 0(全归组库正当稳态, 停条件不可满足 → 150s error 收场) | 0.941s(210 超集→收缩; 停条件可满足, error=None) |
| shows 首份 | 2.421s | **0.941s** |
| groups 首份 | 2.421s | 2.187s(第二跳补齐, 残差=issue ②) |
| 代际 | 空 → 完整(两跳) | 空 → 基础 → 完整(三跳, rid 逐代 +1) |

**硬判据逐项判定(flat/singles/shows 首份数据 ≤2s, 真机轨环境)**:

| 判据项 | 轮 | 实测 | 判定 |
|---|---|---|---|
| flat ≤2s | run1 / run2 / 探测 | 1.081s / 1.092s / 0.941s | **PASS / PASS / PASS** |
| singles ≤2s | run1 / run2 / 探测 | 1.081s / 1.092s / 0.941s | **PASS / PASS / PASS** |
| shows ≤2s | run1 / run2 / 探测 | 1.081s / 1.092s / 0.941s | **PASS / PASS / PASS** |
| groups | run1 / run2 / 探测 | 1.859s / 1.871s / 2.187s | **记录数字, 无硬判据(D9)** —— 第二跳残差回写 issue ② |

- **判定: 计划 §04 S3 验收判据全过, 最苛刻形态(探测轮, 空代竞态在先)亦 PASS** —— flat/singles/shows 全部在落库后立即出现(≤1.1s), 空代只存在落库前一瞬(0.050s); groups 仍由管线结束第二跳补齐(1.86-2.19s), 与 D9「groups 提速指向 issue ②」口径一致。其中「回写两条 issue」实际仅回写 ②(files-serial, 残差数字喂排期), ③(pathmap)无新增面未回写 —— 自检段照旧 no-op ≈0ms、窗量级与 S0 相同, 理由见 §04/§06。

## 06 产物与复用

- 本轮原始证据(gitignored 工作区, 本文件为其蒸馏): `tests-real/.work/s3boot/`(标准轮 run1·run2: measure.json + logslice.txt + stdout/stderr + s0_summary.json + 派生 config.yml)与 `tests-real/.work/s3boot-race/`(探测轮同件)。S0 产物(`s0boot/`、`s0boot-race/`)原样保留未复用。
- 测量口径与工具(S0/S3 共用): `tests-real/tools/measure_boot_first_data.py` / `run_s0_boot.py`(标准轮显式 `--interval 0.25 --fetch-timeout 10`) / `seed_bulk_boot.py`(本轮未用 —— 种子沿用 S0)。
- 喂数字: issue `26-11-18-0259-perf-first-round-grouping-files-serial`(groups 第二跳时刻 + 残差窗 0.538/0.611/0.653s); issue ③(pathmap)无新增面未回写。
- 计划 HTML 未动(收口统一处理); 档案 `memory-bank/tasks/26-11-18-webui-boot-first-data.md` S3 置 Done。
