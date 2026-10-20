# 26-10-20-test-coverage-uplift-2 — 覆盖率门槛清偿与 99% 冲刺 · 第二阶段 (97.7% → 99%)

**Status:** Open
**Added:** 2026-10-20
**Updated:** 2026-10-20
**Summary:** 承接 26-10-01-2157 (91%→96%, Done) 的第二轮: 清偿 `--cov-fail-under=98` 连续多轮飘红的存量欠账, 分 P0/P1/P2 三阶段推到 99% 区间; 防回沉在 M1–M4 之外补 watchlist、豁免治理、工具侧门禁评估
**Topics:** test-coverage-uplift-2
**Refs:** memory-bank/plans/26-10-20-2101-plan-test-coverage-uplift-2.html

## 原始请求

「制定一个测试覆盖率提升分阶段执行计划」——在已有测试体系(全套件 + `--cov-fail-under=98` 门槛 + 基线切片机制)之上, 给出可分段执行、可分段验收、带防回沉机制的覆盖率提升路线。

## 思考过程与决策

- **先实测再立计划**: 全量跑一遍拿最新缺口(2026-10-20 test.full, develop), 不用历史估值。本计划一切数字都是这一轮实测, 缺口地图与预估单位按 §1 换算口径推导。测试条数与耗时口径见 `commands run kb.baseline` 最新切片, 本档案不手抄。
- **发现了「门槛飘红」这个比数字本身更重要的事实**: `--cov-fail-under=98` 已连续多轮 FAIL(基线切片留痕, 属既有欠账非本轮引入, 全量用例 0 failed)。所以第二轮的核心目标不是「再涨几个点」, 而是**先把门槛真正脑血管绿, 且绿得有余量** —— 否则每轮全量都顶着一根红线, 阈值形同虚设。
- **为什么不一步到位抬到 99% 再冲**: heden 阶段闸门惯例(阈值恒低于当期实测约 0.3–1 个点, 给并行 `-n 8` 分支 partial ±1 的口径波动留余量)。本计划阈值阶梯: P0 后维持 98 → P1 后 98.5 → P2 后 99。与上一轮 M1 同一纪律, 只是把「低于 1 个点」细化为分档。
- **P0 主攻选 tool_client 而不是大文件**: `webui/tool_client.py` 行覆盖 79%, 全仓最低, 且缺的是 `call_tool` 整块 HTTP 契约(密度最高、一次能 +24); 大文件 relocate_mod (79 单位) 放 P1 —— 它散布错误路径, 单块密度低, 放快赢轮会拖慢验证节奏。
- **机制侧新增三项而不是重抄上一轮**: watchlist(单文件 <95% 清单进每轮基线复查)、豁免治理(pragma 行数进切片, 只减不增)、工具侧(gtm)门禁评估 —— 上一轮机制 M1–M4 保留延续, 不重复提案。

## 实现计划

1. 立本档案 + 计划制品(`plans/26-10-20-2101-plan-test-coverage-uplift-2.html`, Open) + 双向认领 + 索引重生成。
2. P0 清偿门槛: tool_client HTTP 契约 / commands.py 早退参数化 / finalize_watch 三证平台分支 / 零碎小件 → TOTAL ≥ 98.3% 且门槛转绿 → 基线切片。
3. P1 traffic 家族与 relocate 中坚: relocate_mod / traffic_store / traffic_sample_mod / traffic_source/agent / alias_fs / traffic_grid → TOTAL ≥ 98.7% → 阈值抬 98.5 → 基线切片。
4. P2 长尾与 watchlist 清零: validation/utils/grouping/hr/config 尾 + tray 残留 → TOTAL ≥ 99.2% → 阈值抬 99 → 计划转 Done。
5. P3 防回沉常态化: M1–M7 随阶段验收落地, watchlist 与豁免数字进每轮切片。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 0 | 立档 + 计划制品 + 认领链 + 索引重生成 | Done (2026-10-20) |
| 1 | P0 · 清偿 98% 门槛与快赢轮 | Done (2026-10-20, 98.33%) |
| 2 | P1 · traffic 家族与 relocate 中坚 | In Progress (T1.1/T1.2 已落地, TOTAL 98.80%) |
| 3 | P2 · 长尾清偿与 watchlist 清零 | Pending |
| 4 | P3 · 防回沉机制落地与常态化 | Pending |

## 进度日志

### R0 · 立档 (2026-10-20)

实测 2026-10-20 test.full 全量(develop): 全套件 0 failed(条数与耗时见 kb.baseline 最新切片), TOTAL 97.66%, 门槛 98% FAIL —— 存量欠账, 非本轮代码引入。覆盖分母 = 语句 + 分支出口 ≈ 27,683 单位, 未覆盖 633 单位; 每单位 ≈ 0.0036%。

缺口集中度: core 244 / webui 206 / infra 61 / config 48 / hr 47 / tools 17 / rules 6 / tray 3 / torrents 1。单文件 Top13 合计 433 单位 = 68% 总缺口(relocate_mod 79 / tool_client 60 / commands.py 48 / traffic_store 40 / traffic_sample_mod 38 / …)。形态上: HTTP 契约整块空洞(tool_client.call_tool 89-112)、 commands.py 的 32 条 `->exit` 早退 partial、子进程·端口·`/proc`·网络探测类外部依赖。

计划按「先清偿门槛(P0, +130±40) → 中坚(P1, +180±50) → 长尾(P2, +180±60)」推进, 终点 99% 区间; 全部任务、落点测试文件与验收 DoD 见计划 §3; 纪律纪律见 §4(坑清单), 机制见 §5(M1–M7)。

- 2026-10-20 21:21 覆盖率第二轮计划制品入库: 立计划(plans Open) + 认领档案, 双向认领链与索引重生成

### R1 · P0 清偿门槛与快赢轮 (2026-10-20 23:59)

T0.1–T0.6 全部落地, 只补测试零产品码改动。test.full 全量: **3878 passed + 2 skipped, TOTAL 98.33%(272 miss + 185 partial = 457 单位)** —— `--cov-fail-under=98` **首次转绿**(基线 97.66% / 633 单位), 净清偿 176 单位 = +0.67 点, 计划预估 +130±40 的上沿之外但同量级。基线切片 `testing/baselines/26-10-20-2359-test-coverage-uplift-2-p0.md`。

- **T0.1** tool_client `call_tool` HTTP 契约整块: 新建 `test_tool_client.py`(14 例), 回环 `ThreadingHTTPServer` 收真 socket —— 该文件行覆盖 79% → 90.8%(余 21 行是工具侧进程管理面, P2 再议)。
- **T0.2** commands.py 早退守卫: 32 条 partial 收 16 条, 再加「无 cmd_id 一侧」全覆盖把**全部** `if cmd_id:` 假弧清完(16 处), 文件 94% → 98.03%(余 1 行 + 16 partial 均为批量回执的长文案分支, 语义重复)。
- **T0.3** finalize_watch 三证: 新建 `test_finalize_watch.py`(26 例), 90% → 97.8%(余 3 处为真机进程表竞态, 保守路径已覆盖)。
- **T0.4** routes/traffic_monitor: 5 例(5xx→502 三处 + 模块缺失 502 + notify 非 dict 体 400), 91% → 全绿。
- **T0.5** 零碎小件: events 满额 503 / lifecycle 超时分支 / auth Host 解析 / context 与 RoCache / relocate_journal —— 其中 lifecycle 与 state 两例在变异红验中发现**原断言假绿**(线程秒退 / 空快照), 已改写为真执行分支。
- **T0.6** 外部依赖收敛: hr/discovery 心跳与退避 / traffic_limits 空窗与 LRU / config/loaders 7 行 + 7 partial 全清 / migrations 6 partial 全清。
- **范围守恒**: 过程中发现 `_origin_allowed` 端口段非法抛未捕获 ValueError(应为 fail-closed 403), 按纪律入池 `issues/26-10-20-2230-bug-webui-origin-port-parse.html`, **不在本计划内修**(测试侧预留断言位)。
- **机制侧**: watchlist 10 → **3** 个(tool_client / traffic_qb / relocate_mod);豁免行数 8 行零新增;变异红验 12/12 全杀(≥10% 抽检);Linux 侧 `test.linux` 容器 900s 超时未取得数字(非用例失败), 真值以 CI 复跑为准。

### R2 · P1-T1.1 relocate_mod 守卫与容错簇 (2026-10-21 00:40)

relocate_mod 缺口 **79 → 29 单位**(50 miss + 29 partial → 13 miss + 16 partial), 文件行覆盖 92.6% → 97%; 全量 TOTAL 98.33% → **98.52%**。定向跑(`test_relocate_exec/units/paths/config/web_relocate/grouping_relocate`)136 passed。

- 新增 17 例(`tests/test_relocate_exec.py` 头部「### P1-T1.1 守卫与容错簇」计划 17 条): 解析兜底 / 状态盒缺失 / 旧式 store 注册表重建 / 终态忽略 / mover 消失 / 停滞首样本 / dst 探测保守 / verify 不匹配 / 穿透校验 / regroup 失败不阻断 / 负探测缓存 / reconcile 四动作 / 未知动作 debug-only / 末块跳过已走成员。
- 新增 `_bare_mod(...)` 助手: 裸 `RelocateModule` + `SimpleNamespace` 上下文(store/api/config/state), 默认 `data_dir=tmp_path`(journal 落盘不落 CWD —— 否则 sidefx 拦)。
- 顺带修上游 KB 结构红: `tasks/26-10-20-frontend-dup-code-audit.md` 缺 4 个必备章节(远端 `790df0ef` 引入, 非本会话引入), 按最小结构补记, 正文事实取该档案自身陈述。

### R3 · P1-T1.2 traffic_store + traffic_sample_mod (2026-10-21 01:10)

两个文件在本档测试集下**均达 100%**(单文件 `-n 0` 口径复核: `traffic_store.py` 740 语句 / 238 分支零缺口, `traffic_sample_mod.py` 727 语句 / 278 分支零缺口)。全量 TOTAL 98.52% → **98.80%**(190 miss + 139 partial = 329 单位, 3918 passed + 2 skipped), 净清偿 82 单位。

- **traffic_store(42 单位, `tests/test_traffic_store.py` +11 例)**: 纯函数守卫簇(空列 null 语义与 `_parse_nn_int` 空列判坏 / 未知块记录型 TypeError / `v4_next_month_epoch` 跨年 / 月行桶宽 28 天保底 / 跨块 gap 判定 250ms 边界 / agg 头行门闩与坏行 / z 行须基线块)、存储边界(series_has_data 三档 / evict 非 infohash 与非目录条目 / agg 缓存条目数 LRU / `_write_text_payload` 四条失败清理路径)。
- **traffic_sample_mod(40 单位, `tests/test_traffic_sample.py` +13 例)**: 活尾 pending 行空桶与零覆盖跳过 / main_tick=0 不取整 / 改间隔关块的两条空操作 / 活跃种子缺字段走 n 游程 / 零速过滤与读数漂移防御支(`_FlipSpeedTorrent` 首读 0 次读 512) / z 游程须 totals / 末端锚点三级兜底 / n-only 前缀拆块(3 列 B + 5 列 B 二态并存) / 纯 z 块跨 flush 块头只写一次 / 恢复跨天末槽上下文接力(文件在场 vs 缺失的覆盖差)/ catch-up 开放小时重建 pending / 离线记账空块与 n 槽 / stop() 前置闸。
- **两处「到不了的支」的处理**: ① `_agg_credit_day_file` 的空块零槽 —— 解析层不会产出空块, 直接构造 `V4Block(records=())` 走防御支并在 docstring 注明; ② catch-up 的空桶 —— `_agg_credit_hours` 不产空列表, 用替身 `_agg_credit_day_file` 注入空桶。
- **未新增任何产品码改动**; 无新 `# pragma: no cover`。
