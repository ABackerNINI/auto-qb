# 26-11-03-test-hot-reload-group-index-step-c — 热重载分组索引修复 Step C 真机验证

**Status:** Done
**Added:** 2026-11-03
**Updated:** 2026-11-03
**Summary:** 环境2(56589/56590)真机非 dry-run 复现 L2 热重载后组视图不回落: PASS(27/27 采样组行保持、key 不变、成员不丢、files 重放 0)
**Topics:** test-hot-reload-group-index-step-c
**Refs:** memory-bank/plans/26-11-03-2223-plan-hot-reload-group-index.html, memory-bank/issues/26-11-03-2206-bug-webui-hotreload-group-index-vanish.html, memory-bank/issues/26-10-31-0641-test-real-machine-test-standing.html

## 原始请求

1. 执行热重载分组索引修复 Step C: 真机验证(测试环境, 非 dry-run), 在 `fix/hot-reload-group-index` 本地分支(HEAD `0efcdee1`)工作; 不切/建分支, 不跑 `my-commit-flow.sync`, 不推远端, 只普通 `git commit`。
2. 按 `memory-bank/testing/real-machine.md`、RM standing issue(归片 RM02 热重载, 断言口径复用 RM04)与计划 §04.2(R0–R6)/§04.3(环境判据)执行。
3. 环境二选一按本机实际存在决定; token 只经环境变量注入, 不入库/不入日志/不入回复; 真实种子全程非活跃, 严禁改动其它 qB 实例(可能是生产)。
4. `real.env` 定环境 + `real.guard` 过守卫并记录依据; 假种子须带 announce/domains 才进管线; 非 dry-run 起产品必须用测试配置(禁生产 `config.yml`)。
5. 核心断言: 组行仍存在、`groups` 非空、成员/尺寸一致; 旁证核对 `/torrents/files` 未因重建重放; 三态收尾(恢复配置/停进程/qB 复原)。
6. 结果按 PASS/FAIL/BLOCKED 记录并写本 task 文档、DoD 回写、本地提交; 回复含环境依据、R0–R6 数字、commit hash 与 Step D 输入。

## 思考过程与决策

- **环境选择(§04.3)**: `Test-Path` 实测 `D:\Programs\qBittorrent-testing*` 均不存在, 只有 `C:\Programs\qBittorrent-testing`(56589)与 `testing2`(56590) → 取**环境2**。token 分别注入 `QBT_TEST_56589` / `QBT_TEST_56590`, 全流程未落盘。
- **R0 守卫**: 首次 `real.guard` 失败——56589 未监听(56590 在跑)。按「测试 qB 允许启动」用 `real.up --port all` 拉起白名单实例, 复跑守卫绿; 两实例 torrents=0(无真实种子), 故不涉及暂停/恢复真实种子。收尾用 `real.down --port 56589` 回到「未运行」原状。
- **假种子构造偏离计划字面**: 计划 R1 写 `real.seed`, 但该 CLI 不暴露 announce, 而无 announce 的假种子不会命中 `trackers.domains`, `torrents_added` 整条被跳过(证据边界, 见 real-machine.md)。故复用 RM04 的做法: `lib.torrent` 造 1 个 256KiB 文件 + 两枚同文件表、异 `piece_len`(16384/32768)的 torrent, announce 指向 `http://192.168.110.130:1/announce`(死端口 RST, 零外联), 再 `qb.add_torrent(tag=real-fake)`。管线等价性由 R3 实际形成辅种组证明。
- **files 调用观测**: 在产品与 qB 之间插 `lib.proxy.TcpProxy` 计数 `/api/v2/torrents/files`, 以「重建后窗口内新请求数」判定是否重放, 不依赖日志埋点。
- **配置**: 临时 `config.yml`(schema_version 5, grouping.enabled=true, trackers.domains=[192.168.110.130], interval=60S, web 随机空闲口, qB 指向代理口), 写入时断言端口不等于主实例 56589、不引用生产配置; 全部位于 `tests-real/.work/step-c/`(.work 已 gitignore)。

## 实现计划

1. R0 环境/守卫: `real.env` + `real.guard`(+必要时 `real.up`)。
2. R1 造 2 枚带 announce 的假种子, 校验 progress=1。
3. R2 非 dry-run 起产品(经代理连 56590), 等 WEB 与首轮同步。
4. R3 基线: `/api/groups` 组行/key/members + files/sync 请求计数。
5. R4 L2 热重载: `PUT /api/config` 把 interval 60S→61S, 核对回执与重建日志。
6. R5 重建后 14s 连续采样(0.5s): 组行不回落/key 不变/成员不丢; 重建后 files 新请求=0; 跨 ≥1 完整同步拍; 日志无 Traceback。
7. R6 收尾: 停产品/代理, 删 2 枚假种子连数据, 标签定义保持原状, 清 case/seeds 目录, 停 R0 拉起的 56589。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| R0 | 环境定界 + 守卫(必要实例启停) | Done(2026-11-03) |
| R1 | 2 枚带 announce 假种子进管线 | Done(2026-11-03) |
| R2 | 非 dry-run 起产品(临时测试配置) | Done(2026-11-03) |
| R3 | 首轮基线: 组行/key/members/files 计数 | Done(2026-11-03) |
| R4 | L2 热重载 interval 60S→61S | Done(2026-11-03) |
| R5 | 重建后组视图稳定 + files 不重放 | Done(2026-11-03) |
| R6 | 三态收尾/qB 复原 | Done(2026-11-03) |

## 进度日志

### R0–R6 执行结果 (2026-11-03 23:47–23:48, 环境2)

- **R0 环境**: 环境2(56589/56590); 依据: D 盘两目录不存在、C 盘两目录存在。首跑守卫失败因 56589 未监听; `real.up --port all` 后守卫绿; 两实例 torrents=0(真实种子 0 枚, 无需暂停)。未触碰环境2之外任何实例。
- **R1 假种子**: 文件 256KiB; 两枚 torrent(异 piece_len)hash `dc7ce27ade4e…`、`cf270751cbbd…`; 状态 `stalledUP` / progress `1.0`; tag `real-fake`(该 tag 定义本已存在, 收尾保持原状)。announce `http://192.168.110.130:1/announce` 命中 `trackers.stepc.domains`。
- **R2 产品**: 非 dry-run 启动 pid 11700, WEB 端口 39001, qB 经代理口 39000 → 56590; 临时配置, 未用生产 `config.yml`。
- **R3 基线**: `/api/groups` = **1 组行**, 组名 `step-c-seed.bin`, key `WyJDOi9Vc2Vycy8xMTA1OS9E…`(save_path+文件表派生), members = 两枚假种子; 期间 `/torrents/files` 累计 **2 次**(每枚一次, 首归组), sync 1 次。
- **R4 热重载**: `PUT /api/config` → `applied=true`, `changes=["interval"]`, `restart_required=[]`, PUT→重建日志 **0.22s**; 唯一一行 `应用结构级配置变更: 重建任务队列/规则, 全部记录重匹配 tracker`。
- **R5 核心断言(全绿)**: 重建后 14s 内 **27 次采样**; 组行回落 **0**, key 变化 **0**, 成员集丢失 **0**; 重建后 `/torrents/files` 新请求 **0**(旧代码重放反证点); 重建后 sync 请求 10 次(≥1 完整拍, rid 失效后 full round 正常续跑); 进程存活; 日志 `Traceback` 0、`Unknown` 0。
- **判定**: **PASS**。组视图 `groups` 非空且 `member_to_key` 与 `group_sizes` 一致性由「key 稳定 + 组行成员数恒 2 + 组名(文件表签名)不漂」外部等价观测; 索引内部不变量另有 Step B 单测(见 `memory-bank/testing/baselines/26-11-03-2329-hot-reload-group-index-step-b.md`)。总耗时 20.5s。
- **R6 收尾**: 产品停(Windows terminate rc=1, 预期)、代理停; 删 2 枚假种子并连数据, 标签定义集与开跑前完全一致; 副实例 torrents=0; `case/`、`seeds/` 目录已删; `real.seed.list` 无残留(`real.seed.rm` 因无可删对象返回非零, 属预期); 56589 用 `real.down --port 56589` 停回「未运行」原状(56590 保持运行)。
- **非致命噪声**: 启动时 2 条空 qB 流量快照 WARN, 与本问题无关且重建前后各一(非新建)。

### 留给 Step D 的输入 (2026-11-03)

1. **issue 结论(26-11-03-2206)**: 新机制下症状可复现、修复后真机 PASS; Step D 可据此写「实际修法/验证方式/实测数字」并置 Done。
2. **26-10-01-2129 更正**: 该 issue 的 Superseded 理由称「辅种消失为新机制下无对应路径」——与本轮实测不符: 新机制 `reset_runtime` 确有清索引路径且已复现; Superseded 仍成立(计数机制已换代), 但理由句需更正并回链 26-11-03-2206。
3. **`rules_mod.py` docstring 漂移**: `rebuild_runtime` 上方 docstring 仍写「store.reset_runtime: 清分组索引/缓存」, 与 D1=B 后的新语义不符, 需在 Step D 一并更正。
4. **复用件**: 驱动脚本与证据在 `tests-real/.work/step-c/`(`drive.py` + `evidence.json`, 已 gitignore, 不入库); 如要长期守阵, 可考虑把 R0–R6 提炼为 RM02 用例(本轮未做, 计划未要求)。

- 2026-11-03 23:52 Step C 真机验证 PASS: 环境2(56589/56590)非 dry-run, L2 改 interval 后 27/27 采样组行保持、key 不变、成员不丢、files 重建后 0 次重放; 收尾种子/进程/qB 复原
