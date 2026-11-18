# T2/T3 真机复验: 验收轮 + 批量采样 20 轮 —— 21 连续优雅停未复现 38s 卡停, 判别面常驻 driver (issue 26-11-18-2350 复验判别, 计划 26-11-19-0054 S0-S2)

> 摘要: 计划 26-11-19-0054 的 S0-S2 步真机执行(HEAD = 9a28eebe 含 S0/S1 观测面落地, 只改 `tests-real/tools/run_s0_boot.py` 零产品改动)。环境2 副实例 56590 + 210 枚 `real-fake` 假种子(S0 证据档 §01 同口径造场, 留存口径维持); 验收轮(`--runs 1`, case `s0boot-obs`) + 批量采样(`--runs 20`, case `s0boot-obs-sampling`)共 **21 次受控优雅停**。**21 连续全绿: stop_s 0.45-1.24s(median 1.16, 全部 ≤1.3s 基线级), 0 个栈 dump 文件(15s 看门狗全程未 fire), polls 存活窗全密集 true 无断流 —— S0 基线观察到的 38.75s SIGTERM 卡停未复现**。boot 全部 error=null(19 轮标准形态 + r16 单代收场变体, 见 §04); r9/r15/r17 尾条 false 为 accept-then-die 退出沿变体(落账晚于进程死亡, 不计断流, §05)。复发率: 若为独立 per-stop 概率 1/6, 21 连净先验概率 ≈2%(不支持); 0/21 → 95% CI 上界 ≈14%; R5 口径不断言已修复, 判别面常驻 driver, 生产侧再报「退出卡顿」直接复用抓证, 复发即当场落栈。判据字面与落地实现的两处偏差(`dump_file`=武装路径语义非落盘事件标记; 快停轮 polls「全 true」结构性不可满足)已按证据等价处置, 判读口径单点在 §05。
> 复测时间: 2026-11-19 02:45-03:09(环境2; `real.env` → `real.up` 56590/56589 → `real.guard` 全绿 → `seed_bulk_boot.py` 210 枚 → 验收轮 `--runs 1` → 采样 `--runs 20` → 场终态核验; 非 `real.suite`)
> 复测 commit: 9a28eebe(plan-26-11-19-0054-sigterm-stall, 含 S0/S1 观测面; 本轮无提交动作)

**Refs:** memory-bank/issues/26-11-18-2350-bug-graceful-stop-sigterm-stall.html, memory-bank/plans/26-11-19-0054-plan-graceful-stop-sigterm-stall.html

## 01 目的与判别面(S0/S1 观测面口径)

- **目的**: issue 26-11-18-2350 的 38.75s SIGTERM→退出卡停(S0 静态排查排除面闭合七项后剩 H1 整进程冻 / H2 主线程不可中断 C 调用 / H3, 未分辨), 按复验计划 26-11-19-0054 三步执行: S0 停机窗轮询观测面 + S1 faulthandler 看门狗(均落地 9a28eebe)→ T2 单轮验收 → T3 ≥20 轮采样判复发率(D4 拍板 20)。
- **stop.polls**(计划 S0): `graceful_stop` 等待期独立 daemon 线程每 0.25s GET `/api/state?rid=-1`(单次超时 2s, 只取状态码不读 body 停机窗最小加压), (offset, ok) 序列进 measure.json `stop.polls`; offset 相对 stopfile touch; 既有 `exit_code`/`stop_s` 键与口径不变(stop_s 终点 = wait 返回时刻, 轮询线程 join 收尾不计入)。
- **看门狗**(计划 S1): RUNNER 模板 touch stopfile 后 arm `faulthandler.dump_traceback_later(15, file)`; dump 落 `<case>/stop_stack_dump_run<r>_<t0ms>.txt`(**按轮唯一名**, 每轮写自己从未存在过的名字, 截断在结构上不可能命中前轮证据); 正常退出 atexit 删 0 字节占位 —— **「文件存在且非空 == 栈真落过盘」**; arm 失败仅提示不阻断停机。
- **stop 子树键**: 既有 `exit_code`/`stop_s` + 新增 `touched_epoch`/`polls`/`dump_file`; 超时路径(>40s RuntimeError 报红)报红前把 polls 证据重写进 measure.json, 证据面不因报红丢失。
- **`dump_file` 键语义(实现单点)**: 键值 = **本轮看门狗武装路径**(若落盘会写哪), 恒为路径串非 null; 「真落过栈」的证据面 = 磁盘非空文件。与计划 §04 S1 行字面「正常轮 dump_file=null」的实现偏差 —— faulthandler API 只收文件对象不收路径, arm 即建 0 字节占位, 「null/非 null」表达不了落盘事件, 故按证据等价处置(键记路径 + 磁盘非空文件作真判据), 未改代码。

## 02 环境与造场

- 环境2(C盘机), `real.env` → `real.up --port 56590` / `--port 56589` → `real.guard` 全绿: **56589 pid=5984 / 56590 pid=5932**, 均 vv5.2.3 `firewalled`, 真实种子 0。**产品只作 API 客户端连副实例 56590**(主实例全程未用于产品连接, pid 未变)。
- 210 枚 `real-fake` 假种子经 `tests-real/tools/seed_bulk_boot.py --count 210 --yes` 批量注入(15.2s; announce = `http://127.0.0.1:1/announce` 死端口, 命中派生配置 trackers 段 domains=[127.0.0.1]); `real.seed.list` 核对 `共 210 个种子, 其中自造 210 个(标签 real-fake)`, 检查收敛后全部 `stalledUP`。留存口径维持, 未清。
- **种子态差异(如实记)**: 验收轮起跑时种子为基线同款 `stalledUP`; 其后经 `real.guard` 保护性暂停转为 **`stoppedUP`, 20 轮采样全程 stoppedUP** —— 机制 = `cmd_guard` 调 `guard.snapshot` 不带 skip_tags, 把实例全部种子算保护面并 `qb.pause`(护面口径, 非产品写路径副作用; 产品 relocate 停机段 tag_failures=0 无标签污染, 21 次产品轮后精确核验 tags 恰为 `real-fake` ×210)。`tests-real/seed.py` 子命令仅 add/list/rm/clean, 无 resume/start, 未恢复; **boot 存在性口径不受影响**: 采样首响应 torrents 20 轮全 210; 行数形态 19 轮 210/210/105(与 S0/S3 基线一致)+ r16 过渡代(singles=139/groups=71, 见 §04), r1 冒烟即证。
- 派生配置(驱动生成, shape 对齐 RM08 基座): `schema_version: 8` / qb `127.0.0.1:56590` 空凭据 + `api_key: ""` / `grouping.enabled: true` / `check_missing_files: false` + `missing_tag: ""`(零写路径)/ `interval: 60S` + `sync_interval: 1.5S` + `main_tick: 2S` / web `127.0.0.1:39000` + `skip_local_verify: true` / `fs.path_map` 不配。
- 驱动参数口径: 两轮均任务指示形态(**不传 `--interval`/`--timeout`**, 用驱动缺省 interval 0.15 / fetch_timeout 10 / timeout 150 / quiesce 3.0)—— 非 S0 档标准轮的显式 `--interval 0.25 --fetch-timeout 10` 形态(S0 档 §03 已注明驱动缺省与实跑值不同); stop.polls 间隔为驱动常量 `POLL_INTERVAL_S=0.25`, 不受 measure interval 影响。

## 03 验收轮(T2, 单轮, case `s0boot-obs`)

- **boot**: 标准形态 —— 首响应 1.126s {torrents 210 / singles 210 / shows 105 / groups 0}(gen1 全量超集), gen2 groups 2.061s 全齐(singles 收缩 0 / groups 210), rid_sequence 恰两代, error=null; 与 S0 基线标准轮同形态(flat 1.113s / groups 1.893s 同级)。
- **stop**: touch + **1.17s** 退出, `exit_code=0`; polls `[0.031 true, 0.287 true, 0.541 true, 0.8 true, 1.16 false]` —— 存活窗 4 true(间隔 0.256/0.254/0.259s ≈4 条/s), 末条 = 退出沿(socket 已关); **0 dump 文件**。
- 产品日志: `02:56:34,693 停止` / `02:56:34,694 relocate | 停机: tag_failures=0 resume_failures=0`; stderr 空(看门狗 arm 成功)。`流量快照 | 读取流量数据失败` WARNING 为既有噪音面, 与本测无关。
- **判据字面 vs 实现(如实, 未改代码)**: ① `stop.dump_file` = 武装路径串非 null(语义见 §01, 真证据面满足: 磁盘 0 个 dump 文件); ② polls「全 true」对 1.3s 级快停**结构性不可满足**(在飞末条设计入列), 按断流定义(§05)本轮无断流。

## 04 批量采样(T3, 20 轮, case `s0boot-obs-sampling`)

- 20 轮全部 `exit_code=0`、error=null、**0 废轮**(150s 空库 error 形态零出现); 驱动自然跑完 exit 0, 无 >40s 报红。
- **stop_s 全列表**(r1→r20): 1.17 / 1.15 / 1.21 / 1.21 / 1.15 / 1.19 / 1.23 / 1.14 / 1.17 / 1.10 / 1.07 / 1.19 / 1.12 / 1.19 / 1.24 / 0.45 / 1.18 / 1.15 / 1.12 / 1.12。
- **分布**: min 0.45(r16)/ max 1.24(r15)/ median **1.16**(全 20 轮; 排除 r16 后 median 1.17, 区间 1.07-1.24)/ 均值 1.13; 全部 ≤1.3s 基线级(基线正常样本 0.99/0.72)。boot 全部 ~2s 级(all_nonempty 1.719-2.501s)。
- **r16 单代收场变体(单列说明, 有效轮非废轮)**: web_up=2.108s(首请求连接时序慢 ~1s), 首请求命中**管线中代**(singles=139 / groups=71 过渡态, torrents 210 / shows 105), 四视图当即全非空 → 测量停条件即满足, rid_sequence 单代收场 all_nonempty=2.108s; 停机 0.45s 干净退出(exit_code=0, 停机日志齐全)。即首请求落点在管线中段时, 消费方可观测到过渡代 —— 与计划问题陈述(数据可见性随请求时点变化)一致, 如实记录不过度解读。
- **看门狗/断流**: 20 轮磁盘 **0 个** `stop_stack_dump_run*` 文件(0 字节占位全被 runner atexit 自清); 无任何存活窗断流(所有 false 均为退出沿末条, §05)。

## 05 polls 判读口径(单点, 后续轮复用)

- **断流定义**: 存活窗内**连续 false** 或 **2s 稀疏 false**(WEB accept 后无响应/冻结)= WEB 停摆 → **H1 方向**(全进程冻); 密集 true(≈4 条/s)= WEB 线程活着 → **H2 方向**(仅主线程卡)。
- **退出沿末条 false = 正常停机结构性签名, 不算断流**: 轮询线程设计为 stop_evt 置位后在飞请求收尾即退、最后一条仍入列 —— 对 1.3s 级快停, polls「全 true」结构性不可满足; 判读看存活窗密度, 不看末条。
- **accept-then-die 变体**: r9/r15/r17 尾条 false 落账 +3.02-3.04s(客户端单次 2s 超时口径)而进程 +1.17-1.24s(1.17/1.24/1.18)已 rc=0 退出 —— poll 在退出前 ~0.1-0.2s 已连上(accept), 响应被进程退出截断, 客户端按自身超时落账, **落账时刻晚于进程死亡**; rc=0 + 完整停机日志排除冻结, **不计断流**。与「2s 稀疏 false → H1」判据文字的边界: 该签名只出现在末条且落账晚于死亡时刻, 非存活窗事件。
- **dump 判读**: 非空文件 = 栈真落过盘(读主线程首行定挂点); 0 字节 = armed 未 fire, 不作证据(正常轮被 atexit 自清, 磁盘无文件)。
- **`dump_file` 键 = 武装路径语义**(measure.json 里恒为路径串), 真证据 = 磁盘非空文件 —— 计划字面「正常轮 null」与实现不符已按证据等价处置(§01), 后续轮判读以本节为准。

## 06 复发率结论(R5 口径)

- **21 连续次优雅停全部干净**(1 验收 + 20 采样), 且采样如实复现了原异常触发窗口: 每轮 touch = 管线结束 + quiesce 3.0s, 即「管线跑完 ~3s 内优雅停」(S0 档 §05 的复现面描述), 20/20 命中 —— 触发窗口在场而异常未现。
- 若 38.75s 为独立 per-stop 概率 1/6 的现象, 21 连净的先验概率 ≈ (5/6)^21 ≈ **2%** —— 数据不支持 1/6 独立复发率; 按 0/21 计, 复发率 95% CI 上界 ≈ 3/21 ≈ **14%**(rule of three)。
- **R5 口径不断言已修复**: 历史仅 1 次发生、本轮场条件有细微差异(种子 stoppedUP vs 基线 stalledUP; 连跑节奏更密), 机制问题(H1/H2)本轮未获新证据 —— 无复发即无栈无 polls 冻结样本可判。判别面(15s 看门狗 + stop.polls)**常驻 driver**, 生产侧再报「退出卡顿」直接复用抓证, 复发即当场落栈定挂点。

## 07 产物与复用

- 驱动: `tests-real/tools/run_s0_boot.py`(S0/S1 观测面所在, HEAD 9a28eebe; `--runs N --case-dir <tests-real/.work/ 之下>`; 停机 >40s RuntimeError 报红不降级强杀, polls 证据先落盘)。批量造种: `tests-real/tools/seed_bulk_boot.py`(--count/--port/--yes)。
- 本轮原始证据(gitignored 工作区, 本文件为其蒸馏): `tests-real/.work/s0boot-obs/`(验收轮: run1.measure.json 含 stop 子树 + run1.stdout/stderr/logslice + s0_summary.json)与 `tests-real/.work/s0boot-obs-sampling/`(20 轮全套 runN.* + s0_summary.json)。
- 场状态(采样后核验): 56589 pid=5984 / 56590 pid=5932 在线; 210 枚 tags 恰为 `real-fake` ×210(21 次产品轮后精确核验), 状态全 `stoppedUP`; 39000 端口无残留, 21 个产品进程全部 rc=0 自灭, 零 taskkill。
