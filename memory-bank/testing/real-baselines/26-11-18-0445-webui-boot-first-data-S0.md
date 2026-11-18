# S0 真机取证: 重启后 WebUI 首份数据时间线 —— 发布被首轮管线挡住坐实 + 0 行空代竞态直接观测到 (计划 26-11-18-0259 S0)

> 摘要: 计划 26-11-18-0259 的 S0 步(修复前基线测量, HEAD = 011e1aeb 无任何提前发布改动)。环境2 副实例(56590, 空库草稿本)注入 210 枚 `real-fake` 假种子(256K random, 105 剧 × 每剧 2 集命名, 独立目录, announce = `http://127.0.0.1:1/announce` 死端口零外连, 全做种态); 产品用派生配置(schema_version 8 / 副实例免鉴权 / grouping on / trackers 命中假种子 / 非 dry-run / WEB 39000)经 `python runner_s0.py` 进程内 `cli.main` 起, 优雅停 = stopfile → 进程内 SIGTERM(零 taskkill)。受控重启标准测 2 轮 + 空代竞态探测轮 1 轮(共 3 次启动)。**标准轮实测: flat/singles/shows 首份数据 = 首响应(≈ spawn+1.1s), groups 首份数据 = gen2 = 管线完成时刻(spawn+1.6~1.9s)**; 代际恰两代(gen1 请求触发: flat 满/singles 全量超集/groups 空 → gen2 管线结束 flush: groups 210/singles 收缩 0)。**探测轮(fetch_timeout 0.1s)直接观测到 plan §02.2 第 3 点的 0 行空代**: 首请求落在 web bind + 0.07s(早于落库完成)→ gen1 = 四视图全 0(rid=启动时间戳秒)→ 空窗持续到 gen2(spawn+2.42s)—— 用户报告的「重启后界面空窗」机制坐实。两条形态(空代 / flat 满基础代)都进了产物, 落点由首请求时刻 vs 落库完成决定, 都被 S1「apply_sync 落库后立即发布基础视图」覆盖。本轮一个计划外观察项(run2 优雅停 SIGTERM→退出 38.75s, rc=0 优雅路径齐全, 见 §05)。
> 基线时间: 2026-11-18 04:45-05:26(环境2; `real.env`→`real.guard`→`real.up`→批量假种子→`run_s0_boot.py --runs 2`→竞态探测轮→微基准落盘; 非 `real.suite`)
> 基线 commit: 011e1aeb(feat/webui-boot-first-data, 修复前基线; 本轮无提交动作)

**Refs:** memory-bank/plans/26-11-18-0259-plan-webui-boot-first-data.html

## 01 环境与造场

- 环境2(C盘机), `QBT_REAL_ENV` 未设按 EXE 探测; **主实例 56589 本轮未用于产品连接**(本测产品连副实例); `real.up` 后 `real.guard` 全绿: 56589 pid=2036 / 56590 pid=13136, 均 vv5.2.3 `firewalled`(§2.4 已核非 disconnected), 真实种子 0。
- 产品连接目标 = **副实例 56590**(空库草稿本, `tests-real/lib/app.py` 安全口径): 210 枚 `real-fake` 假种子经 `tests-real/tools/seed_bulk_boot.py` 批量注入(单进程循环, 与 real.seed 同一套 guard/lib 安全边界), 实测 15.5s 注入完毕, `real.seed.list` 核对 `共 210 个种子, 其中自造 210 个(标签 real-fake)`, 全部 `stalledUP`。
- 种子形状: 256K random × 210, 每枚独立目录独立文件名(零数据互踩), 名字剧集形状 `Boot Show NNN S01E### 1080p.bin` → shows 视图 105 剧, groups 视图 210 单成员组(每枚自己的 dir+文件名 ⇒ 独立组键)。
- announce 统一 `http://127.0.0.1:1/announce`(死端口, 连接即拒, 零 DNS 零外连; RM10/RM08-14 同款先例)—— **必须命中派生配置 trackers 段**(domains=[127.0.0.1]): 否则 added 种子匹配不到 tracker conf 会在 qbmanager added 循环被跳过(qbmanager.py `matched_added` 门), 归组管线整段不跑, 被测对象消失。
- 种子留存口径(用户拍板): 210 枚留在 56590 实例里, S3 同批复测后才清 —— 本轮未跑 `real.seed.rm/clean`。

## 02 产品启动方式(派生配置单点)

- 驱动: `tests-real/tools/run_s0_boot.py`(--runs N; --qb-port 只认白名单 56589/56590; --case-dir resolve 后必须在 tests-real/.work/ 之下, 越界拒跑; 目录里已有 config.yml 但无 s0_meta.json 伴生 = 非本工具产物, 拒写); 配置: `tests-real/.work/s0boot/config.yml`(由驱动生成, shape 对齐 RM08 基座):
  - `schema_version: 8`(infra.versioning.CURRENT_VERSIONS 现行版, 无迁移改写); qbittorrent → 127.0.0.1:56590 空凭据 + `api_key: ""`(token 落盘红线);
  - `grouping.enabled: true`(被测管线开关), `check_missing_files: false` / `missing_tag: ""`(零写路径, RM08 同款);
  - `interval: 60S`(任务线开 —— 不用 dev.webui 的 86400S 形态; 被测管线在同步线)+ `sync_interval: 1.5S` + `main_tick: 2S`;
  - `web: 127.0.0.1:39000 + skip_local_verify: true`(免鉴权口径, 轮询零凭据零 Bearer);
  - `fs.path_map` 不配(Windows 宿主直跑形态, 校验要求 to 为 / 开头容器挂载点; path_map 空 = 现状 ⇒ `path_map_selfcheck` 短路 no-op, 见 §04 pathmap 基线口径)。
- 起法: `<venv>/python.exe runner_s0.py <cfg> <stopfile>`(进程内 `cli.main`, 与 `python -m auto_qb` 等价), **非 dry-run**(WEB 真启); 收尾优雅停 = touch stopfile → runner 线程进程内 `signal.raise_signal(SIGTERM)` → cli handler → KeyboardInterrupt → 优雅退出(real-machine.md §2.6 唯一优雅路径; 全程零 taskkill)。三轮均 rc=0, 日志「停止 + relocate 停机」齐全。

## 03 测量结果(三次启动, t0 = 产品进程 spawn)

测量脚本 = `tests-real/tools/measure_boot_first_data.py`(--url/--out/--t0/--t0-mono/--interval/--fetch-timeout 全参数化; `/api/state?rid=-1` 轮询, offset 用 time.monotonic, 另记响应完成绝对 epoch 对齐产品日志)。**S0 实跑口径: 标准两轮 `--interval 0.25 --fetch-timeout 10`(缺省), 探测轮 `--interval 0.03 --fetch-timeout 0.1`; S3 修复后复测须显式传标准轮同值(`--interval 0.25 --fetch-timeout 10`)**(评审 minor 8: 驱动 --interval 缺省已改 0.15, 与 S0 实跑值不同, 故 S3 必须显式传)。

| 轮 | spawn epoch | web 首响应 | flat(torrents) | singles | shows | groups | 全齐 | 优雅停 |
|---|---|---|---|---|---|---|---|---|
| run1(热身, 0.25/10) | …302.054 | +1.113s | **1.113s**(210) | **1.113s**(210→收缩 0) | **1.113s**(105) | **1.893s**(210) | 1.893s | rc=0 / 0.99s |
| run2(复测, 0.25/10) | …307.945 | +1.101s | **1.101s**(210) | **1.101s**(210→收缩 0) | **1.101s**(105) | **1.639s**(210) | 1.639s | rc=0 / 38.75s ⚠§05 |
| 探测轮(0.03/0.1) | …550.191 | **+0.928s(0 行空代)** | **2.421s**(210) | 恒 0(全归组库正当稳态¹) | **2.421s**(105) | **2.421s**(210) | —(停条不满足¹) | rc=0 / 0.72s |

¹ 探测轮 gen1 = 0 行空代(无 singles 超集代), gen2 起全部 210 种子已单成员成组 ⇒ singles = ∅ 是该库形态的**正当稳态**而非缺陷 —— 测量脚本「四视图全非空才停」的停条件在此形态下不可满足, 该轮如实跑满 --timeout 150s 后报 error 收场(`run1.measure.json` 的 error 字段为原文; rid 尾部 33s 起的多次小代 = 死端口 announce 失败引发的 tracker 状态派生变更, 与管线无关)。S3 修复后库形态不变, 但 S1 的基础代 singles=210 超集使停条件可满足, 不受此影响。

代际序列(两种形态都进了产物, `rid_sequence`):
- **标准轮形态**(首请求晚于落库完成): gen1 rid=启动时间戳秒(首个请求触发发布): flat 210 / **singles 210(全量超集)** / shows 105 / **groups 0**; gen2 rid+1(管线结束 flush_views 发布): flat 210 / **singles 0(第二跳收缩)** / shows 105 / **groups 210**; gen1→gen2 间零新代 —— 管线期间轮询全命中 gen1(同 rid)。
- **探测轮形态**(首请求早于落库完成 = plan §02.2 第 3 点原样): **gen1 = 四视图全 0 的空代**(rid=启动时间戳秒, 首请求 web bind + 0.07s 触发)→ 空窗内轮询全命中空代 → gen2 rid+1 = flat 210 / shows 105 / groups 210 / singles 0。

## 04 首轮管线时间窗(产品日志锚点 ↔ HTTP 时间线对照)

run1 日志锚点(spawn 04:45:02.054; 派生数据目录 `tests-real/.work/s0boot/data/logs/auto-qb.log`):

```text
04:45:02.054  spawn(t0)                    [driver t0_epoch]
04:45:02.771  日志初始化完成                +0.72
04:45:02.774  启动 qB 管理器                +0.72
04:45:02.862  WEB UI 已启动 :39000          +0.81   ← web bind
04:45:03.134  WEB 跳过本地验证…免密钥放行     +1.08   ← 首个 /api/state 请求到达(轮询端)
04:45:03.167  gen1 响应完成                  +1.11   [HTTP 时间线: 210/210/105/0]
04:45:03.351  检测到新增种子 210 个           +1.30   ← apply_sync + path_map 自检 + full_round(210 tracker 单发) 完成
04:45:03.947  gen2 发布(HTTP 观测)           +1.89   ← 归组 files 单发 + post 冲突检查 + flush_views 完成时刻
```

探测轮日志锚点(spawn 05:22:30.191; `tests-real/.work/s0boot-race/data/logs/auto-qb.log`): 日志初始化 +0.76 → WEB up +0.86(31.047) → **首请求到达 +0.92(31.109, 此时 store 未落库)→ gen1 = 0 行空代** → 检测到新增种子 210 个 +1.69(31.878) → gen2 +2.42(32.612, HTTP 观测)。

- **[WEB up → 检测到新增种子] = 0.489s**(run1)= apply_sync(全量 maindata 落库) + path_map_selfcheck(空表 no-op) + full_round(210 次 tracker 重匹配)。
- **[检测到新增种子(日志锚点) → gen2(HTTP 观测, 轮询粒度 ±interval)] = 0.596s**(run2: 09.078→09.584 = **0.506s**; 探测轮 31.878→32.612 = **0.734s**, 含 30ms 高频轮询负载)= 归组 files 单发 210 次 + post 冲突检查 + flush 发布 —— files 段占主体。
- **微基准(已落盘, 见 §06; 产品同款 qbittorrentapi 客户端 keep-alive 对 56590 串行)**: `torrents_files` × 210 = **0.445s(2.12ms/次)**; `torrents_trackers` × 210 = **0.467s(2.22ms/次)** —— 与日志窗吻合(0.45s files + post/flush ≈ 0.5-0.7s)。对照: tests-real/lib/qb._call 无连接复用口径 ×210 = **3.660s(17.43ms/次)** —— 每次新建 TCP 的连接开销上限, 与 issue ② 估值「单次 10-30ms」的连接级口径一致; 产品 requests 客户端连接复用后单次 ~2.1ms。
- **path_map_selfcheck 基线(pathmap issue)**: 派生配置 fs.path_map 空(Windows 宿主直跑, `MappedFileAccess._table` 空 ⇒ file_access.py:380 短路 return) ⇒ **自检段 no-op ≈ 0ms**。探测段(挂载点 isdir + mkdir/rmdir 可写探测)只在使用 fs.path_map 的容器形态存在; 网络挂载(NAS/SMB)秒级超时放大面在真机轨(本地盘)不可复现 —— 基线数字 = 本地板 + 空映射 = 0, 放大面口径见 issue 正文。
- **根因链吻合判定: 吻合, 且两形态都直接观测到**。① groups 首份数据 = gen2 = flush_views 发布时刻 = 管线完成时刻(逐点相等); ② gen1→gen2 间零新代 —— 含落库数据的发布被挡在整条管线之后(plan §02.2 第 2 点); ③ singles 超集第二跳收缩 / groups 首代空 = D6 代价面预演(标准轮); ④ **§02.2 第 3 点原样命中**(探测轮): 首请求早于落库完成 → ensure_state 发布 0 行空代(rid=启动时间戳秒)并压住 dirty → 空窗内轮询全命中空代直到管线结束 —— 用户报告的「重启后界面空窗」机制坐实。首请求落点决定形态: 早于落库完成 ⇒ 空代形态(探测轮), 晚于 ⇒ flat 满基础代形态(标准轮, 落库完成在首请求之前由 gen1 含 210 行直接证实, 窗口上界 0.27s)。两形态都被 S1 的「apply_sync 落库后立即发布基础视图」覆盖。

## 05 空代竞态探测(已命中)与计划外观察项

- **空代竞态(首响应 0 行): 已观测到**(探测轮, fetch_timeout 0.1s)。机制: fetch_timeout=0.1 时 connect 挂起被超时切断、快速重试, 首个成功请求落在 web bind + 0.07s(+0.928s 响应完成, fetch_s 仅 0.048)—— 早于落库完成 ⇒ ensure_state 发布 0 行空代; 标准轮(fetch_timeout 10s)首个请求被 SYN 重传/连接时序拖到 web bind + ~0.27s, 晚于落库 ⇒ flat 满基础代。**首请求早/晚于落库完成 ⇒ 两种形态, 都是真实可发生路径**(探测轮 = 浏览器重启前已开、自动重连抢先的形态; 标准轮 = 刷新稍晚的形态)。探测轮产物原文: `tests-real/.work/s0boot-race/run1.measure.json`(first_response_counts 全 0 + error 字段为停条件不满足的如实记录)。勘误: 探测轮首跑因驱动透传缺失(fetch_timeout 实为缺省 10.0)未构成区分轮 —— 已修透传并以 0.1 真重跑, 本节为重跑后产物(旧产物已被重跑覆盖)。
- ⚠ **计划外观察项(scope-guard, 只报告不修)**: run2 优雅停 SIGTERM → 进程退出 **38.75s**(run1 0.99s / 探测轮 0.72s, 均为驱动 stop_info 口径), rc=0, 「停止」「relocate 停机」日志齐全 —— SIGTERM(转 KeyboardInterrupt)在主线程 ~38s 后才生效, 疑似主线程被某个阻塞中的调用拖住(挂点未定位; 复现面 = 管线跑完 3s 内优雅停, 210 死端口 announce 的 qB 会话在场)。与 S0 测量结论无耦合(测量在停机前已完成), 建议另议是否入池。

## 06 产物与复用

- 测量脚本: `tests-real/tools/measure_boot_first_data.py`(S3 同口径复测用: `--url http://127.0.0.1:<web> --out <json> --t0/--t0-mono <spawn 双时钟> --interval 0.25 --fetch-timeout 10`, 与 S0 标准轮同值); 驱动: `tests-real/tools/run_s0_boot.py`(起/停/重启编排 + 派生配置生成); 批量造种: `tests-real/tools/seed_bulk_boot.py`(--count/--port/--yes)。
- 本轮原始证据(gitignored 工作区, 本文件为其蒸馏): `tests-real/.work/s0boot/`(config.yml / run1·run2 的 measure.json+logslice.txt+stdout / s0_summary.json / **microbench-product-client.log + microbench-libqb.log**(微基准原始输出, 2026-11-18 05:2x 实测))与 `tests-real/.work/s0boot-race/`(竞态探测轮, fetch_timeout 0.1: measure.json+logslice.txt+stdout / s0_summary.json)。
- 喂数字: issue `26-11-18-0259-perf-first-round-grouping-files-serial`(files 单发次数 + 段总耗时 + 微基准)与 `26-11-18-0259-perf-first-round-pathmap-selfcheck-critical-path`(自检段 no-op 基线)各自正文 + 变更记录。
