# 26-11-03-memory-bank-code-review-3-s2 — 全量代码评审第三轮 S2（B1–B4 后端批次）

**Status:** Done
**Added:** 2026-11-03
**Updated:** 2026-11-03
**Summary:** 全量代码评审第三轮 S2：B1（18）/ B2（25）/ B3（9）/ B4（11）后端批次评审，区间 `bf9920d3..812ad785`，零代码改动
**Topics:** memory-bank-code-review-3-s2
**Refs:** memory-bank/plans/26-11-03-0557-plan-full-code-review-3.html, memory-bank/tasks/26-11-03-memory-bank-code-review-3-s3.md

## 原始请求

1. 执行第三次 code review 计划的 **S2 步骤**（B1–B4 后端批次评审），只做 S2，不进入 S3。
2. 必读计划 S2 段 + R1–R11 维度、S0 task、S1 task（附录 D 的 B1–B4 清单、配对表、坑档依赖）。
3. 范围 `bf9920d3..812ad785`，只审 B1（18）/ B2（25）/ B3（9）/ B4（11）；区间终点固定 `812ad785`，评审流程自身提交不纳入；评审阶段**零代码改动**。
4. 开工先 `commands run my-commit-flow.sync` 并把「已同步 <hash>」贴回复；只在 clone1 操作。
5. 按 plan 五步评审法逐批：全文件勾选（不得抽样）、七字段发现表（含三锚与可达性）、与 57 条 Open issue 去重、撞车检查、`commands run test.quick` 绿。
6. 维度用 R1–R11；每批先读该批依赖的坑档条目（走类索引，不整目录通读）。
7. 真实问题**当场 create-issue 入池**（类型/档位/三锚/可达性/建议）；连续同类 >5 条合并并注明覆盖数。
8. 过程与发现写进本步 task 文档；计划文档不写流水，只推进 S2 状态。
9. 触到 S1 标注「含区间改动」的拆分目标文件时按 R12 记录，留给 S3 等价核验。
10. 收尾 DoD 回写（kb.wrap/kb.index/kb.check），然后单独提交并推送（文档 only）。
11. 发现 P0 级立即停下单独报告。

## 思考过程与决策

- **D7 覆盖说明**：计划 D7 原定「P0/P1 不入池、S7 汇总后请用户确认」；本轮用户显式要求「发现的真实问题当场按 create-issue 入池」，属 AGENTS.md 要求的显式授权，按用户指令执行。
- **Open 底册**：用户口径 57 条 = S0 起点 54 + S0 四步 3；现场 `issues/_index.md` Open 为 61 条（S1 新增 3 + 评审流程 1 条 refchain 修复），去重以**现场 61 条**为准（多出的 4 条均非代码发现，不影响判定）。
- **评审方法**：新增/独立文件读全文；存量文件按区间 `git diff bf9920d3..812ad785` 逐件过目（只审区间增量，符合「实质增量文件 100% 过目」口径），回读关键上下文核验行为。
- **零代码改动**：本轮只写 task 文档与 issue 报告、推进计划状态，不动 `src/` 与 `tests/`。

## 实现计划

1. 同步 → 读计划/S0/S1 底册 → 读坑档类索引与 B1–B4 依赖条目。
2. B1 → 逐件全读 → 五步 → test.quick。
3. B2 → 逐件 diff 全过 → 五步 → test.quick。
4. B3 → 逐件 diff 全过 → 五步 → test.quick。
5. B4 → 逐件 diff 全过 → 五步 → test.quick。
6. 汇总发现→去重→create-issue 入池（当场逐条）→ 撞车矩阵。
7. 回写本档 + kb.wrap/kb.index/kb.check → ship.commit/ship.push。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S2-0 | 同步 + 底册/坑档入口 | Done(2026-11-03) |
| S2-1 | B1 评审（18 件） | Done(2026-11-03) |
| S2-2 | B2 评审（25 件） | Done(2026-11-03) |
| S2-3 | B3 评审（9 件） | Done(2026-11-03) |
| S2-4 | B4 评审（11 件） | Done(2026-11-03) |
| S2-5 | 发现入池 + 撞车检查 | Done(2026-11-03) |
| S2-6 | 收尾 DoD 回写 | Open |
| S2-7 | 单独提交与推送 | Open |

## 进度日志

### R0 · 立档与 B1/B2 完成 (2026-11-03)

- 开工同步 `commands run my-commit-flow.sync` → 已同步 `f97ebba1`。
- B1（18 件，transfer 全链新增）逐件全读；B1 后 `test.quick` 绿（此前一次全绿记录）。
- B2（25 件，config 骨架 / core / torrents / finalize_watch）逐件 diff 过目。
- B2/B3 后 `test.quick` 出现 4 failed，全部为文档机械面（`test_claim_chain_is_bidirectional` / `test_doc_links_are_not_broken` / 索引与 `gen_doc_map --check` 未同步），根因为本 task 档新建后的**暂态**：Refs 写法与 `kb.index` 未对齐，非代码缺陷。修正 Refs 为仓库根相对路径、计划 meta 反向声明 S2、`commands run kb.index` 后，`tests/test_docs_forms.py` 19 项全绿。
- B3 完成（0 发现）；B4 完成（0 发现）；B4 后 `commands run test.quick` 全绿：**4927 passed, 10 skipped**（耗时约 3 分）。
- 发现入池：当场按 create-issue 生成 3 条（`26-11-03-0824` P2 · `26-11-03-0901` ×2 P3），均已登记到 `issues/_index.md` Open；跨批撞车矩阵与 61 条 Open 去重见附录 E。
- 五步第 4 步（工具提示源）：TRAE-code-review（B1–B4 区间）+ TRAE-security-review（transfer/认证面）各跑一轮，候选 4 条逐条复核：2 条成立并入池、2 条按设计驳回（详见附录 E「工具提示源复核」）。
- 收尾 DoD：`kb.wrap` / `kb.index` / `kb.check` + 单独提交推送（见 S2-6/S2-7）。

## 附录 A · B1 评审记录（transfer，18 件）

覆盖：`config/models.py`(transfer 段) · `config/validation/sections.py`(transfer 段) · `transfer/{__init__,adapters/{__init__,base,qb,tr},orchestrator}.py` · `webui/server/routes/transfer.py` · `static/shared/{transfer_flow.js,transfer_targets.js,tpl/transfer-targets.html}` · `tests/test_transfer_*.py`（6 件）。

全文件勾选：12 件新增文件全文过目；2 件 config 存量文件按 transfer 段主责全文过目；6 件测试全文过目。

| # | 位置（三锚） | 维度 | 档位 | 可达性 | 结论/建议 |
|---|---|---|---|---|---|
| B1-1 | `transfer/orchestrator.py:370`（`_transfer_one` 成功收口）→ `:443-445`（`_delete_source` 无异常兜底）→ `:293-299`（`run_batch` 逐 seed 兜底把异常判 UNEXPECTED） | R6 错误处理 / R2 状态一致性 | P2 | 可达：源 qB 删除 API 瞬时失败（网络抖动/token 失效）即触发 | 目标侧已加种并验证成功、仅源删除失败时，整条结果被记为「失败(未预期异常)」：前端提示转移失败、源种子保留（重复做种），用户可能重试（第二次只会 SKIPPED）。建议把源删除失败降级为「成功 + 备注源未删除」，不回滚整条结论。 |
| B1-2 | `webui/server/routes/transfer.py:58`（`api_transfer_run` 的 `hashes = [str(h) for h in (b.get("hashes") or []) if h]`） | R8 边界校验 / R1 输入契约 | P3 | 可达：持 token 直调 API 且把 hashes 传成字符串（前端恒传数组） | 字符串会被逐字符当 hash，产出 N 条 `SOURCE_READ_FAILED`，批次串行线性占用主循环。建议入口判 `isinstance(hashes, list)`，非列表 400（并入池）。 |

其余观察（不入池、备查）：

- 前端 `_transferExec` 的 `_transferRunning` 单飞闸不在 `finally` 内复位；收口代码抛异常才会卡死，实际不可达（P3 备查）。
- `QbApi.torrents_export` 复数返回 bytes（非上下文管理器），适配器 `bytes(data)` 正确；`torrents_add(torrent_files=bytes)` 受库支持（已核 `.venv` 源码），无隐患。
- 闸门白黑名单与 JS 预检表双份，有守卫测试钉同源；`skip_check` 默认 True 但进度 <1.0 自动降级为非跳检，保守默认成立。
- 路由无 hashes 数量上限（D6 拍板，前端 timeout 按批量线性放大），非缺陷。

**B1 结论：发现 2 条（P2 ×1、P3 ×1），无 P0/P1。**

## 附录 B · B2 评审记录（25 件）

覆盖：`cli.py` · `config/{__init__,compat,loaders,writer,validation/__init__,schema/{__init__,fields,groups}}`（按件） · `core/{qbapi,qbmanager,state,taskqueue,traffic_store,tvshows,traffic_source/agent}.py` · `core/modules/{ops_mod,relocate_mod,relocate_units,rules_mod,traffic_sample_mod}.py` · `tools/finalize_watch.py` · `torrents/{compat,record,store}.py`。

逐件 diff 全过（存量件按区间增量），新增 `config/compat.py` 全文过目。

| # | 位置（三锚） | 维度 | 档位 | 可达性 | 结论/建议 |
|---|---|---|---|---|---|
| B2-1 | `config/validation/sections.py:869`（`_validate_transfer_path_map` 的 `str(item.get(side, "") or "")`）→ `config/loaders.py:128`（同形强转） | R7 配置校验完备性 | P3 | 可达：手写 YAML 把 path_map.from/to 写成 dict/list/bool | 非标量经 `str()` 转成垃圾串即静默通过，装载后映射永不命中且无报错。建议校验层要求 `isinstance(value, str)`（同 base_url 口径），并入池。 |

重点核验项（均通过）：

- `config/compat.py` 归一单点：幂等（二次归一形态稳定）、非 dict/多键形原样透传交校验器、retired 伪动作只剔除不注入 on_error、就地改写仅限 `*_rules` 组内 spec。
- `config/writer.py` targets 定向掩码/还原：name 唯一键配对 + 改名二轮「数量相等才配对」，旧值缺失保哨兵；非 targets 列表不递归（与既有口径一致）。
- `core/taskqueue.py` 让位不占预算 + `_DEFER_SCAN_FACTOR` 有界扫描；retry 推迟只改 `next_run`、保留断点，无 run 内 sleep（单写线程不破）。
- `core/state.py` `_evict_oldest` 单点复用；rule_traces 环形 + 保留期 + 总量上限（300×2KiB ≤ 600KiB < 1MiB 红线）；空维度/当日逐出路径逐一验算。
- `core/qbmanager.py` 断连稳态守卫（`_ran_line` 门）与期望落地追平（`expect_due_at` 恒返回未来时刻，无 0 超时空转）。
- `torrents/store.py` 期望落地登记/结算/清空生命周期；热重载 clear。
- `qbapi.torrents_set_share_limits` 显式缺省发 `Default`（5.3 必填、5.2 未知参数忽略）；`ops_mod` 重加 `shareLimitsMode` camelCase 透传与 None 不发键（5.2 wire 不变）。
- `relocate_mod` 恢复判据 `move_issued` 账先落、指令后发；`_recover` 三分流；重建/重拉退避；dry-run 闸落在相位机入口；`_finalize_members` 先零成本预筛再取文件表。
- `relocate_units` 同卷时空间闸不适用、目标非目录新增 `target_type` 闸；`finalize_members` 判定单点抽取保持等价。
- `traffic_store` cov_s 下限 1 与 `v4_merge_agg` fail-closed；`tvshows` 尾括号保留逻辑逐例验算；`finalize_watch` 拒写即退休。

**B2 结论：发现 1 条（P3 ×1）。**

## 附录 C · B3 评审记录（rules / config 规则段，9 件）

覆盖：`rules/base.py` · `rules/conditions.py` · `rules/registry.py` · `rules/actions/{basic,checking,full_checking,transfer}.py` · `config/schema/rules.py` · `config/validation/rules.py`。

逐件 diff 全过；`rules/base.py` 为区间实质重写（+522/-94），按全文结构过目。

| # | 位置（三锚） | 维度 | 档位 | 可达性 | 结论/建议 |
|---|---|---|---|---|---|
| — | — | — | — | — | 本轮未发现真实缺陷。 |

重点核验项（均通过）：

- **retry 计数生命周期**：`_dispatch_result` 仅在动作明确失败且 `attempt < retries` 时返 `retry`；`rules_mod` 在 REJECT 分支 `attempt += 1` 再入队；`_process` 正常收口 `attempt = 0`；PENDING/维护路径不烧次数；`_requeue` 见 `retry_delay > 0` 保留断点并清零 —— 无「重试次数只减不还」与断点复位错路。
- **choose 语义**：分支 when 求值异常 → `VERDICT_ERROR` 且不再尝试后续分支；块内 pending 记 `si + 1` 续跑（块内剩余动作不细跑）为文档明示口径，不按缺陷记。
- **条件树**：`None` 树等价旧 `all([])`；叶子多键/空树在校验器判红；`not` 节点 trace 只映内叶结果（P3 展示口径，备查）。
- **registry 派生面**：`FIELD_WATCH_ALLOWED_ACTIONS` / `DELETED_ALLOWED_ACTIONS` 与 `schema/fields.py` 冻结基线一致（tags/category；仅 print_torrent_details 允许删除态），无收窄导致的启动判红。
- **校验器**：动作深校验回退不传 `gate` —— 现无动作校验器消费 gate，等价；条件侧逐叶传 gate。
- **trace 写放大实测**：`record_rule_trace` 在 300 条饱和时实测 144µs/次（脚本 1200 次 172.8ms）；规则任务受 `max_tasks_per_tick` 节拍约束（每拍约数十次），折算 <10ms/拍，不构成性能缺陷，不入池。
- `full_checking` 自愈路径按 hash `state.save()`：受同组自愈成员数（通常 2–5）约束，频次低；P3 备查（可改循环后单次落盘）。

**B3 结论：发现 0 条。**

## 附录 D · B4 评审记录（webui py，11 件）

覆盖：`webui/commands.py` · `module.py` · `runtime.py` · `server/common.py` · `server/routes/{__init__,state,torrent_cmds,torrent_detail,traffic_monitor}.py` · `tool_client.py` · `views.py`。

逐件 diff 全过；`commands.py`（+197/-46）与 `views.py` 按全文结构过目。

| # | 位置（三锚） | 维度 | 档位 | 可达性 | 结论/建议 |
|---|---|---|---|---|---|
| — | — | — | — | — | 本轮未发现真实缺陷。 |

重点核验项（均通过）：

- **transfer 命令契约**：`transfer_run` 由 handler 自写回执（成功/失败两路都写），`DEFERRED_RECEIPT_COMMANDS` + `RESYNC_COMMANDS` 双登记；`transfer_test` 仅 `cmd_id` 有值才写回执，无 cmd 的直调路径不会造孤儿回执。
- **认证面**：`server/factory.py` 的全局依赖挂载覆盖按 `ROUTE_BUILDERS` 新登记的 transfer 路由（含 `/api/transfer/run`、`/test`），无裸路由绕过。
- **单写线程口径**：`_cmd_transfer_run` 在主循环消费，验证轮询期间占用主循环已在计划 §03 记为已知形态，与整组迁移同量级；不按缺陷记。
- **期望落地**：`_expect_landing` 只取 Mapping 响应里的 `added_torrent_ids` 列表，异常/空值不登记；snake/camel 双处理与 qB 分支一致。
- **搜索版本**：`search_rev` 的 bump 覆盖 added/removed/full_round/触发字段（`_SEARCH_TRIGGER_FIELDS`），`views.search_rows` 先读 rev 再取快照，与「无锁首发」注释一致。
- **路由与入参**：`routes/__init__` 调整后路由清单/顺序无冲突；`common.int_param` 的 bool→int 直接 API 面可接受。

**B4 结论：发现 0 条。**

## 附录 E · 撞车矩阵与去重结论

### 跨批同文件/同模式

| 契约面 | 涉及批 | 结论 |
|---|---|---|
| transfer 路由 ↔ factory 全局认证 | B1 ↔ B4 | 一致（新路由被全局依赖覆盖） |
| `QbApi.torrents_delete` ↔ transfer 删源 | B1 ↔ B2 | 一致（删后立即摘 store 记录，无陈旧行） |
| 配置 targets 掩码哨兵 ↔ transfer 目标编辑器 | B1 ↔ B2 | 一致（哨兵=已设置，改名二轮按数量配对） |
| `rules_mod` REJECT 计数 ↔ `Rule._process` attempt/断点 | B2 ↔ B3 | 一致（正常收口清零，断点保留） |
| `qbmanager.search_rev` ↔ `views`/`routes/state` | B2 ↔ B4 | 一致（增删/轮完/触发字段全 bump） |
| registry 派生允许集 ↔ schema 冻结基线/校验器 | B2 ↔ B3 | 一致（守卫测试钉同源） |
| `TransferStatus`/notes 文本 ↔ `transfer_flow.js` 结果映射 | B1 ↔ B4 | 一致（成功/跳过/失败三分支；未知标签按跳过提示） |

### 与 Open issue 去重（底册 61 条）

- 新增 3 条（见附录 F）与 61 条均无重复（3 条同属 topic `torrent-transfer`，互不重叠：删源结果归类 / 路由入参 / 配置校验）。
- 邻近但不同机制（不合并）：`26-10-22-0308-feat-ops-skip-check-download-cost`、`26-10-05-0402-bug-skip-check-self-fail-gate`、`26-10-11-2045-bug-ops-skipcheck-dedup-shadowed-by-g3` 均属**跳检质量防线**；本条属**删源失败的结果归类**，修法/证据/锚点互不覆盖。
- `26-10-01-2147-feat-group-move-atomicity` 是整组迁移原子性（relocate 域），与本条 transfer 删源无关。

### 工具提示源复核（plan 五步第 4 步）

- **TRAE-code-review**（限 B1–B4 区间 diff，子代理执行）：回报 3 条候选；逐条人工复核后 **2 条成立并入池**（与 B1-1 / B1-2 同一锚点），另 1 条（`routes/transfer.py` 批量无上限）与计划 D6「不设上限」冲突，按设计意图驳回。
- **TRAE-security-review**（限 transfer 凭据/路由/认证面）：回报 1 条——`config/writer.py:141-142` 哨兵还原 + 既有 `POST /api/config/preview`（`routes/config.py:174-177`）会把 targets 真实口令返回前端。人工复核后**驳回不入池**：preview 的既定语义是「显示将写入的真实生效值」（代码注释明示，否则占位符与实际写入不符）；调用方本就持有 web token，可直接下发 qB 命令，不构成提权；且泄漏通道为既有设计（主 qB 口令同理），非本次引入。若需加固属独立的安全加固计划，不在本步展开。

## 附录 F · 新增 issue 清单（3 条，topic `torrent-transfer`）

1. `memory-bank/issues/26-11-03-0824-bug-transfer-source-delete-misreport.html` — bug/standard（P2）：transfer 源删除失败被误判为整条转移失败；三锚 `orchestrator.py:370` / `:443-445` / `:293-299`（取证 2026-11-03 08:24），可达性=源删除 API 单次失败；建议降级为「成功 + 源未删除」注记。
2. `memory-bank/issues/26-11-03-0901-bug-transfer-hashes-input-type.html` — bug/light（P3）：`/api/transfer/run` 的 `hashes` 未校验为数组，字符串会被逐字符拆成多条伪 hash；三锚 `routes/transfer.py:58`（取证 2026-11-03 09:01）。
3. `memory-bank/issues/26-11-03-0901-bug-transfer-pathmap-nonscalar.html` — bug/light（P3）：path_map 的 from/to 仅 `str()` 判空，非标量静默通过；三锚 `validation/sections.py:869` / `loaders.py:128`（取证 2026-11-03 09:01）。

## 附录 G · 交给 S3 的输入清单

1. **本步新增 issue（3 条，均 Open 未认领，S7 汇总时一并呈现）**：`26-11-03-0824-bug-transfer-source-delete-misreport`（P2）、`26-11-03-0901-bug-transfer-hashes-input-type`（P3）、`26-11-03-0901-bug-transfer-pathmap-nonscalar`（P3）。
2. **R12 记录（不在本步展开）**：B1 的 `tests/test_transfer_targets_editor.py` 是 S1 附录 C 标注「含区间改动（3 笔，M → 共享支撑件）」的拆分目标 → 需 S3 扩大等价核验；B1–B4 其余 47 件均为新增/纯实质文件，无 R12 项。
3. **S3 等价核验可复用结论**：`TransferStatus` 三分支与前端映射一致；`QbApi.torrents_delete` 即时摘 store 的契约可作为删除路径等价基线。
4. **无 P0/P1**：本步无「需立即停下单独报告」的发现；B1-1 为 P2，按用户指令当场入池。
5. **评审证据**：区间 `bf9920d3..812ad785` 零代码改动；`commands run test.quick` 收尾复跑全绿（见进度日志）。

- 2026-11-03 09:03 S2 完成 B1-B4 共 53 件评审(零代码改动): 入池 3 条(1 P2 + 2 P3), test.quick 4927 passed/10 skipped, 计划 S2 已推进 Done
