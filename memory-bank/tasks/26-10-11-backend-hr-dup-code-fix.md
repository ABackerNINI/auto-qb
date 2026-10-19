# 26-10-11-backend-hr-dup-code-fix — hr 重复代码重构(三轮共 9 条 refactor issue 认领与修复)

**Status:** Done
**Added:** 2026-10-11
**Updated:** 2026-10-15
**Summary:** 用户指令「修复 hr 部分问题: `26-10-11-0033-report-dup-code-audit.html`, 相关 issue 一并认领」。滚动报告 §14–§17(轮 11–14)对 hr 全包入池 **9 条 refactor issue**; 本轮按用户拍板**只做低风险高收益子集(5 条)+ 保守口径(只做无行为变化的收口)**: ① `hr-adapter-parse-boilerplate-dup`(parse_counters 上收 `parse_header_counters` / ADAPTERS 工厂抽 `_standard_kwargs` / URL 参数提取抽 `query_param`); ② `hr-report-cli-boilerplate-dup`(三入口抽 `_gate_enabled_sites` + `_build_service` / `_scope_of` 收单点 / 删死件 `stamp_text_ts`); ③ `hr-lane-transition-boilerplate-dup`(档位截断/失效骨架抽 `_settle_lane`); ④ `hr-warn-dedup-throttle-dup`(三个 `_warn_*` 抽 `_warn_once` / 波级异常收尾抽 `_abort_wave` / 节流窗口算法抽 `warn_gap_floor`); ⑤ `hr-model-serialize-helper-dup`(仅 `_as_int/_as_float` 收单点; to_json/from_json dataclass 驱动属评估型, 保守跳过)。**零行为变化**(仅表意等价的结构收口 + 删一处死件)。余下 4 条(`hr-store-recover-lock-family` / `hr-token-persist-convention` / `hr-site-derive-convention` / `hr-thread-lifecycle`)按用户口径**暂缓**, 留 `Open`。**2026-10-13 续轮(R2)**: 用户指令「认领并修复hr相关的3个refactor issues」, 认领并修复 ⑥ `hr-site-derive-convention-dup`(派生单点上收 `Config.hr_site_confs()`, runtime/report 改走单点; webui 半留轮 15) ⑦ `hr-token-persist-convention-dup`(抽 `infra.utils.resolve_or_create_token`, hr/webui 两端一行委托, logger 身份经参保持, 4 条 patch 地址随迁) ⑧ `torrents-hr-entry-guard-dup`(抽 `TorrentRecord._hr_guard`, 三判定入口守卫收口; `hr_judgement` 语义不同不并入), 各配 1 条静态守阵, 仍**零行为变化**。余 store-recover(与轮 18 合并)/thread-lifecycle(机制不同收益低)/fetchable(待拍板)留 `Open`。 **2026-10-15 续轮(R3)**: 用户「认领并修复」第 9 条 `hr-thread-lifecycle-boilerplate-dup` —— 抽 `HrThreadHandle`(`hr/threadlifecycle.py`) 骨架单点(幂等 start + stop/join(timeout) + 退出/未退出日志 + started), 机制差异(Condition vs shutdown)经 request_stop 回调, worker/server 两调用点降为句柄调用, 日志文案字节同零行为变化; 余 store-recover/fetchable 留 `Open`。
**Topics:** dup-code-audit

**Refs:** memory-bank/issues/26-10-11-0240-refactor-hr-adapter-parse-boilerplate-dup.html, memory-bank/issues/26-10-11-0240-refactor-hr-model-serialize-helper-dup.html, memory-bank/issues/26-10-11-0240-refactor-hr-lane-transition-boilerplate-dup.html, memory-bank/issues/26-10-11-0240-refactor-hr-warn-dedup-throttle-dup.html, memory-bank/issues/26-10-11-0240-refactor-hr-report-cli-boilerplate-dup.html, memory-bank/issues/26-10-11-0240-refactor-hr-site-derive-convention-dup.html, memory-bank/issues/26-10-11-0240-refactor-hr-token-persist-convention-dup.html, memory-bank/issues/26-10-11-0352-refactor-torrents-hr-entry-guard-dup.html, memory-bank/issues/26-10-11-0240-refactor-hr-thread-lifecycle-boilerplate-dup.html, memory-bank/testing/baselines/26-10-11-1555-backend-hr-dup-code-fix.md, memory-bank/testing/baselines/26-10-13-2150-backend-hr-dup-code-fix.md, memory-bank/testing/baselines/26-10-15-0311-backend-hr-dup-code-fix.md
## 原始请求

> 用户(2026-10-11): 「修复hr部分问题:26-10-11-0033-report-dup-code-audit.html, 相关issue一并认领」

> 追问下两处拍板(AskUserQuestion): 修复范围 = **仅低风险高收益子集**(adapter-parse / report-cli / lane-transition / warn-dedup / model 的 `_as_int/_as_float`); 重构力度 = **保守**(只做无行为变化的收口)。

## 思考过程与决策

- **请求边界判定**: 这是**执行任务**(改代码 + 认领 issue), 不是纯问答。用户显式给了「修复」与「认领」两项指令 —— 认领(用户指派)与改代码都在授权内; 但「修复范围」与「重构力度」两处歧义由 AskUserQuestion 收口(9 条里 3 条跨包、报告自标「可暂缓/与轮 18 合并」)。
- **保守口径的落地判据**: 「无行为变化」= 只抽公共助手/单点、**不改数据形状与序列化格式**、**不合并有语义差异的分支**。据此把两处「评估型」条目挡在门外: model 的 to_json/from_json 改 dataclass 驱动(动数据形状)、线程生命周期抽 `_ThreadHandle`(机制不同, 收益低)。
- **报告口径要复核, 不照抄**: 报告把档位处置三处判为 A 类「仅 detail 文案不同」, 实读发现 **fail_streak 推进与升级告警三处各不相同**(结构失效推进+告警 / 取数失败推进 / 预算截断不推进)。故 `_settle_lane` 用 `count_failure` 显式参数承载该差异 —— 若照报告抽成 `_fail_or_truncate(st, detail)`, 会**静默改行为**(给预算截断也计连续失效)。这是「A 类也可含细微差异」的实例。
- **节流窗口口径(③)改道**: 报告建议「收敛 6h 常量为单点」, 但 4 处窗口**值并不相同**(service/worker 用 `max(60, CHANNEL_SILENCE_WARN)`、server 用 6h 字面量、core/traffic_store 用 3600s), 且 worker 侧有 16 条单测**按模块常量打补丁**(`monkeypatch.setattr(worker_module, "CHANNEL_SILENCE_WARN", ...)`)。故只把**重复的算法**(`max(60.0, float(阈值))`)抽成 `warn_gap_floor(threshold)` 单点, 阈值仍留各模块常量 —— 既消重又不动补丁面。server 的 6h 与 core/traffic_store 的 1h 属跨包/不同语义, 不动。
- **删死件的判据**: `stamp_text_ts` 全仓仅被自己的单测引用(报告标「疑死件」属实 —— 生产侧零调用)。它与 `status.stamp_text` **同体异格式**(`%Y-%m-%d` vs `%m-%d`), 无法「改复用」, 故按 issue 的「删除」侧执行, 并同删其单测与测试计划清单行。
- **跨包三条暂缓的理由**(留 Open): `hr-token-persist-convention` 要动 webui/server/common; `hr-store-recover-lock-family` 要动 core/state + infra/locking(报告自标「与轮 18 infra 合并考量」); `hr-site-derive-convention` 的 webui 半属轮 15; `hr-thread-lifecycle` 报告自标「收益低, 可暂缓」。与用户「低风险高收益子集」口径一致。

## 实现计划

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | 开工同步(`my-commit-flow.sync`: `ca2606fe`→`c0038049`) | Done |
| S2 | 修 `hr-adapter-parse-boilerplate-dup` | Done |
| S3 | 修 `hr-report-cli-boilerplate-dup` | Done |
| S4 | 修 `hr-lane-transition-boilerplate-dup` | Done |
| S5 | 修 `hr-warn-dedup-throttle-dup` | Done |
| S6 | 修 `hr-model-serialize-helper-dup`(仅强转助手) | Done |
| S7 | 5 条 issue 置 `Done` + 填 `doc-refs` 认领链 | Done |
| S8 | 收尾: `dev.fmt` / `test.full` 基线切片 / 本档案 + 切片 / `kb.index` + `kb.check` | Done |

## 子任务状态表

| 子任务 | 状态 | 说明 |
| --- | --- | --- |
| hr-adapter-parse-boilerplate-dup | Done | `parse_header_counters`(nexusphp) + `_standard_kwargs`(adapters/`__init__`) + `query_param`(fetcher) |
| hr-report-cli-boilerplate-dup | Done | `_gate_enabled_sites` + `_build_service`(report) + `_scope_of` 复用 `query_param` + 删 `stamp_text_ts`(含单测) |
| hr-lane-transition-boilerplate-dup | Done | `_settle_lane(st, *, failed_detail, truncated_detail, count_failure)`; B 类摘要串仍只登记 |
| hr-warn-dedup-throttle-dup | Done | `_warn_once` + `_abort_wave` + `warn_gap_floor` |
| hr-model-serialize-helper-dup | Done | 仅 `_as_int/_as_float` 收单点(channel 复用 model); to_json/from_json 保守跳过 |
| hr-site-derive-convention-dup | Done | 派生单点上收 `Config.hr_site_confs()`; runtime/report 改走单点; webui 半留轮 15 |
| hr-token-persist-convention-dup | Done | `infra.utils.resolve_or_create_token` 单点; 两端一行委托; logger 经参保持; 4 条 patch 地址随迁 |
| torrents-hr-entry-guard-dup | Done | `TorrentRecord._hr_guard()`; 三入口守卫收口; `hr_judgement` 不并入(排除返回 None 语义不同) |
| hr-thread-lifecycle-boilerplate-dup | Done | 抽 `HrThreadHandle`(hr/threadlifecycle.py); worker/server 降为句柄调用; 日志文案字节同(R3) |
| 认领链 | Done | R1 5 条 + R2 3 条 issue `doc-refs` ↔ 本档案 `**Refs:**` 双向闭环 |
| 收尾(测试 / 索引 / 基线) | Done | R1/R2 各有基线切片, 见进度日志 |

## 进度日志

### 2026-10-11 R1 — hr 低风险子集重构(5 条 issue)

- **开工同步**: `commands run my-commit-flow.sync` → 远端领先 16 笔, 快进 `ca2606fe`→`c0038049`。
- **① adapter 解析样板**(`hr-adapter-parse-boilerplate-dup`): `nexusphp.py` 新增 `parse_header_counters(html, arity, lanes)`; carpt / btschool 的 `parse_counters` 由逐字同的双份降为一行委托(仍保留各自的 `COUNTER_ARITY/COUNTER_LANES` 样张实证常量与校准 docstring)。`adapters/__init__.py` 抽 `_standard_kwargs(conf)`(三工厂共用, carpt 追加 4 个 kwarg)。`fetcher.py` 抽 `query_param(url, *names, default="")`,`_scope_of` / `_tid_of` 与报告层 `_scope_of` 共用。
- **② CLI 入口样板**(`hr-report-cli-boilerplate-dup`): `report.py` 抽 `_gate_enabled_sites(config, out, *, what)`(总开关 + 至少一站点启用的前置门, `what` 只进文案 → 走查/查看 措辞不变)与 `_build_service(config, *, fetcher, persist, allow_fetch, **extra)`(三入口共用构造); `_scope_of` 改为 `query_param(..., default="?")` 一行; 删死件 `stamp_text_ts`(及 `tests/test_hr_report.py` 的 `test_stamp_text_ts_zero_is_dash` 与测试计划清单行)。
- **③ 档位状态机样板**(`hr-lane-transition-boilerplate-dup`): `service.py` 新增模块级 `_settle_lane(st, *, failed_detail, truncated_detail, count_failure) -> bool`; `_truncate_lane`(预算截断, 不计连续失效)、`_mark_fetch_failed_lane`(取数失败, 计)与 `_run_pages` 的 `_LaneAbort` 分支(结构失效, 计 + 升级告警)三处骨架收口。**行为逐项等价**: 三处的 detail 文案与 fail_streak/告警差异全部由参数显式承载。
- **④ 告警去重与节流**(`hr-warn-dedup-throttle-dup`): `service.py` 新增 `_warn_once(seen, site, *, dup_level, dup_msg, level, msg, event, silent=False)`, `_warn_no_channel` / `_warn_login` / `_warn_ext_quota` 三方法降为参数化调用(去重日志级别/文案、告警级别/事件/silent 全部保留); `_do_wave` 三处异常收尾(配额/无通道/Retry-After)抽嵌套 `_abort_wave()`(盖时间戳→记历史→落盘); 新增模块级 `warn_gap_floor(threshold)`, service 与 worker 的节流窗口共用(阈值仍留各模块常量)。
- **⑤ 强转助手**(`hr-model-serialize-helper-dup`): 删 `channel.py` 自抄的 `_as_int/_as_float`, 改 `from .model import _as_float, _as_int`(hr 内单点)。to_json/from_json dataclass 驱动按「保守」跳过。
- **验证**: `dev.fmt` 格式化 10 个改动文件; hr 相关 9 个测试文件 462 passed; 全量 `commands run test.full` → **3112 passed + 4 skipped / 0 failed / 覆盖率 TOTAL 99%**(见基线切片)。数字较上基线 3113 少 1 = 删掉的死件单测。
- **认领链**: 5 条 issue 置 `In Progress`→`Done`(徽标 + meta 双改), 补「实际修法 / 验证方式 / 测试数字」段, 填 `doc-refs` 指向本档案; 本档案 `**Refs:**` 反向列 5 条 + 切片。
- **零改动确认**: 未触碰 `config.yml` / `auto-qb-data/`; 跨包(webui/core/infra)零改动。

### 2026-10-13 R2 — hr 去重续轮(用户指名 3 条)

- **开工同步**: `commands run my-commit-flow.sync` → 已同步 `af0b5747`。
- **认领范围裁定**: Open 的 hr 相关 refactor 共 6 条; 本轮认领 3 条 —— site-derive(hr 半) / token-persist / torrents-hr-entry-guard(均为无行为变化、报告评级风险低的收口)。不认领: `hr-store-recover-lock-family`(报告自标跨包风险中、与轮 18 infra 合并考量) / `hr-thread-lifecycle`(报告标收益低可暂缓; 机制不同 Condition vs shutdown, 强抽象违审计「宁少勿滥」) / `hr-fetchable-dead-config`(建议本身「二选一待拍板」, 修复需用户定方向)。
- **⑥ site-derive**: `Config.hr_site_confs()` 新增(config/models.py, docstring 承载绑定视图语义); `runtime.site_confs()` 一行委托; `report.py` 删 `_site_confs`、`_gate_enabled_sites`/`_build_service` 改走单点。改道说明: 报告建议 HrRuntime 作单点, 但 report 是无 runtime 的 CLI 入口(反向依赖拉进 server 栈), Config 聚合根才是两侧共同既有依赖。
- **⑦ token-persist**: `infra/utils.py` 新增 `resolve_or_create_token(configured, path, *, what, logger)`(读文件/生成/原子写/INFO 只提示路径 + rationale); `channel.resolve_token` / `common.ensure_web_token` 一行委托(公开名不变); `what` 承载日志措辞差异, logger 经参保持两侧身份(守阵按 record.name 钉密钥不进日志); 4 条 monkeypatch 单测 patch 地址迁 `infra.utils.atomic_write`; common/channel 的 `secrets`/`atomic_write` import 随之清理。
- **⑧ torrents-hr-entry-guard**: `record.py` 新增 `_hr_guard() -> bool`(`not tracker_conf.hr or hr_excluded()`), 三入口顶部逐字同两行守卫降为一行; `hr_judgement` 不并入(排除返回 None 走本地逻辑, 语义不同); `hr_excluded` docstring 消费关系同步。
- **守阵 ×3**: `test_hr_site_confs_derivation_single_point`(推导全仓白名单) / `test_token_resolve_single_point_in_infra`(token_hex(32) 全仓唯一 + 两侧委托) / `test_hr_entry_guard_single_point`(record.py 守卫表达式唯一), 各含红验语义; 三个测试文件 docstring 测试计划同步。
- **连锁修正(首跑 test.quick 捕获 8 红全修)**: infra docstring 里的「O_TRUNC」字面量被 `test_no_o_trunc_write` 判红(STRING token 不豁免, 原修复注释是 `#` 注释才豁免) → 措辞改写; `p.relative_to(root)` 在 Windows 产生反斜杠 → `as_posix()`; 认领链要求档案 Refs 与 issue doc-refs 同轮互填。
- **验证**: test.quick 全绿后收口; test.full 见基线切片 `baselines/26-10-13-2150-backend-hr-dup-code-fix.md`。
- **零改动确认**: 未触碰 `config.yml` / `auto-qb-data/`; webui 半(routes/hr.py)与 core/state 零改动。

### 2026-10-15 R3 — hr 线程生命周期骨架抽(用户指名第 9 条)

- **开工同步**: `commands run my-commit-flow.sync` → 已同步 `c2330fb0`.
- **复验**: worker.py start/stop 骨架 ↔ server.py stop + HrEndpointHandle.wait 各自写 join(timeout)/退出判定/退出与未退出日志 —— 仍复现(取证 2026-10-15 03:02).
- **改道说明**: R1/R2 按「保守口径」暂缓该条(机制不同, 收益低); 用户 2026-10-15 显式「认领并修复」lifted the deferral → 抽执行. 命名 `HrThreadHandle`(Hr 前缀仓惯例) not 建议 `_ThreadHandle`.
- **抽面**: `hr/threadlifecycle.py` 新增 `HrThreadHandle`: 幂等 start(已在跑则 False) + stop(request_stop 回调 -> join(timeout) -> 按退出/未退出记 log -> 退出清/未退出留句柄) + started. 告口纪律(cancel_all/shutdown 先再 join) stays in caller stop per pitfalls/backend/concurrency.md —— 骨架里只 join+判定+日志.
- **worker.py**: `_thread` 降为 `_handle = HrThreadHandle()`; start 置停止位复位+节拍基准 under cond then handle.start; stop cancel_all 先(告口纪律)→ cond 置停止位 notify → handle.stop(subject/stuck_note 承载文案); started 委托.
- **server.py**: `HrEndpointHandle` 持 `HrThreadHandle` + `stop(timeout)` 全收口(request_stop=server.shutdown 注入, server_close 保持吞掉); `HrChannelServer.stop` 降为清句柄+委托. 日志文案字节同(已停止/未退出四条 + close debug).
- **行为差审计(零行为变化 claim 的 two micro-diffs)**: ① server stop 日志 order: 原 shutdown→join→server_close→INFO/ERROR, 新 shutdown→join→INFO/ERROR→server_close —— close-error debug 与 exit-status 日志 swap order, 文案同; ② worker start 线程起 moved out of cond block (flags still reset under cond first) —— only main thread writes `_thread`(单写线程不变), loop thread never touches it, equivalent.
- **测试同步**: worker 5 用例 `_thread` poke → `_handle._thread`(idempotent reuse / stuck inject / name+daemon / clean clear / not-exit keep); server `test_stop_timeout_and_close_error_are_contained` stub 改真 `HrEndpointHandle`(假 SimpleNamespace server + stuck `HrThreadHandle`) —— close-error containment 仍走真 code path(原 stub bypassed it).
- **验证**: hr 两文件 101 passed; dev.fmt 6 files; full test.full 全绿见基线切片 `baselines/26-10-15-0311-backend-hr-dup-code-fix.md`.
- **kb 回写**: 本档案 R3 段 + 第 9 条 issue 置 Done(doc-refs 认领链) + activeContext 切片更新 + kb.index 重建.

## 待办（下一轮）

- 仍 `Open` 的 hr 相关 1 条: `hr-fetchable-dead-config`(「接上强制 vs 删死字段」二选一待拍板)。〔2026-10-15 R12 续记〕`hr-store-recover-lock-family-dup` 已由 infra 轮(R18)合并考量收口 —— 恢复链与文件锁收 infra 单点, 见主档案 `26-10-10-backend-dup-code-audit.md` R12 与档案 `26-10-15-backend-store-recover-lock-dedup.md`。
- webui 半合流: token(R15-C01) / 站点派生(R15-C03) 随 webui 轮 15 改走 infra/Config 单点(守阵白名单已预留)。
- `hr-lane-transition-boilerplate-dup` 的 B 类子项(各档摘要串 service ↔ status, `(全深度)` vs `(全)`)仍未合 —— 需先钉文案差异点 + 回归保护, 本轮按报告口径只登记。
