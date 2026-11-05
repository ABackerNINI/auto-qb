# activeContext 切片归档 · 后端核心 / 规则 / 迁移

> 摘要: 2026-11-05 activeContext 蒸馏轮逐字外迁的 12 条切片原文(2026-10-13~11-03, 种子状态回写/迁移闸门/HR/热重载/任务队列/启动 fail-fast)。
> 触发: 后端, 种子状态, 迁移, relocate, HR, 热重载, taskqueue, 切片归档
> 本文件为逐字归档(attachments 不计 cap); 蒸馏结论与指针写在各 progress 主题文件。
> 归档说明: 原文中的相对链接已因换目录统一补一级 ../, 其余逐字未改。
> 归档说明之二: 仅**行首的 Refs 声明行**改题为「切片原文」以免被知识库认领链解析误读(正文中的 `doc-refs`/`Refs` 键名保持原样); 链接路径已补一级 ../; 其余逐字未改。

---

<!-- slice: 26-10-13-0538-seed-state-writeback.md; 最后活动: 2026-10-13 07:14 -->

# 26-10-13-0538-seed-state-writeback — 种子状态双写通道：A 系 S0/S1/S2/S3 全部落地（形态 A3）

> 摘要: 专题 `seed-state-writeback`。承接报告 26-10-12-2148。先按用户令对比 A 系四形态（裁定：分水岭只在 G4/G6 安全窗，推荐 A3 = A1 删合成回写 + 局部 deferral，可叠 A2 `pending_writes`）与 B 系三支（裁定：实际候选只剩 B′ = 真值回写 + 显式发射，B1/B3 与 26-10-12-2229 的源无关语义冲突）；随后按用户指定立 B2 实施计划 26-10-13-0413。立件后用户质疑「qB 返回信息并非实时、每 1.5s 才更新一次」→ 回 qB 源码（`D:/Projects/Else/qBittorrent`）**确认成立且更硬**：qB 服务端 torrent 状态按 `BitTorrent/Session/RefreshInterval` 节流刷新（默认 1500ms），写后直查 `torrents_info` 读到的是写前值 ⇒ B/B′ 值层退化为 no-op，R4 是**默认粒度**而非边界竞态。用户定调 RefreshInterval 保持默认 ⇒ B2 计划置 Superseded；报告抬 26-10-13-0441 修订；另修正两处归因漂移。收尾提交（`caa40a7e`）后**另立 A 系实施计划 26-10-13-0540**（形态 A3）并提交（`3f742233`）。**本轮执行 S0 前置三件**：P1 可达性确认按 **auto-qb 能力面**（非某份配置）判定 **可达 ⇒ 形态定 A3**；P2 `state_changed` 消歧改名；P3 `FakeClient` 四方法真实翻转 state。**随后完成 S1 值层**：删合成回写整段（`_sync_paused_state` + `update_torrent_fields(state=)`），快照语义收敛为「严格 = 最近一次同步的应用结果」，源无关发射天然获得；三条守阵按新契约重写（含一条契约翻面）、4 调用点迁移。全绿（基线切片 `baselines/attachments/26-10-13-0554-seed-state-writeback-s0.md`）。S0 落地随本专题入库。**S2 deferral 亦已完成**（见「现在做到哪」）：`own_writes` + TTL + D-1/D-2/D-3 三闸门，收回 G4/G6「陈旧-放行」窗口；S1 副产物「二次触发」已入池（`issues/26-10-13-0626`）。
> 最后活动: 2026-10-13 07:14
> 状态: In Progress（S0–S3 四个批次全部完成，计划已转 Done；本轮随本专题入库）

**Refs（切片原文）:** memory-bank/tasks/26-10-13-backend-seed-state-writeback.md

## 现在做到哪

**S0 前置三件已落地**（计划 §3），形态**定为 A3**：

1. **P1 · G4/G6 可达性确认 → 可达**。判据按 **auto-qb 提供给用户的能力面**，**不按某份配置**（首轮误用本机 `config.yml` 当能力边界，26-10-13-0601 订正）。能力面：`start` 是一等规则动作（`schema/rules.py:227` + 示例 `test_yamls/test_actions/test_start.yml`）、`checking.auto_start` 是文档化选项（`schema/rules.py:185`）、规则 `actions` 顺序执行 ⇒ 三个可达 witness：**W1** `[{start},{checking}]` 顺序保证（纯配置）；**W2** `auto_start: true` 跨任务（纯配置）；**W3** WEB 命令线 resume + 同 tick 跳检（用户触发）。今日（有回写）该路径受 G4/G6 保护，**A1 会让它回归成放行窗口**，A3 用 deferral 保住保护 ⇒ 取 A3。证据链全文见任务档案「思考过程与决策」§6。
2. **P2 · `state_changed` 消歧改名** —— `qbmanager.py:517` 局部变量 → `cmd_changed_state`（连带 `:528/534/540/544` + 消歧注释）。
3. **P3 · 替身能力补齐** —— `tests/helpers.py` 新增 `FakeClient._apply_paused_state`，四暂停轴方法真实翻转 state（UP/DL 完成位语义，`None` = 全体）；`calls` 形状逐字不变。

**S1 值层已落地**（26-10-13-0620）：删除合成回写整段（`QbApi._sync_paused_state` + `store.update_torrent_fields` 的 `state=` 形参），四入口只调 raw client；快照语义收敛为「**严格 = 最近一次同步的应用结果**」⇒ 自家停/起与外部变更**源无关**（状态变化只经下一轮真实 delta 进 `state_changed`，被转移检测与状态事件看见）。三条守阵按新契约重写（`test_stop_preserves_completeness` 改钉「快照逐字不变」；`test_pause_resume_sync_store_snapshot` **契约翻面**并改名 `test_pause_resume_no_same_tick_writeback`；`test_start_stop_idempotent` 清过时注释）、4 处 `state=` 调用点迁移、`test_grouping` 两条承认「整组停种经同步回流再触发一次、一轮即收敛」。坑档 `concurrency` 补 `state` 例外、`guards.md` A-04 行按反转更新。

**S2 deferral 已落地**（26-10-13-0643）：新增 `store.own_writes`（hash → 登记时刻，纯内存不落盘；判据**含组维度**：目标或其组任一成员命中即让位）+ `note_own_write`/`own_write_pending` + TTL 兜底 `_OWN_WRITE_TTL=10s`；QbApi 四入口登记；`_apply` 状态变化时逐出（另种子删除 / 热重载两处清理）。三处闸门：**D-1** 队列级 `qbmanager._own_write_defer_gate` → `TaskQueue.run_due(defer_gate=)`（覆盖 task 线全体，命中者重排下一 tick）；**D-2** `ops.skip_check` 执行路径（WEB 路径不经 task 线）；**D-3** `CheckAction.execute` 决策链入口。两处相对计划字面的调整（已在代码注释与计划 §12 写明）：D-3 用 `skip` 而非 `pending`（避免丢任务）；D-2 落执行路径而非 `_skip_gates_detail`（保预检 cls 契约）。有界性双依据：同步逐出 + TTL 兜底。G4/G6「陈旧-放行」窗口**收回**。

**S3 收尾已落地**（26-10-13-0714）：§8.3 余下七条守阵全部补齐 —— **S1 静态**（剥注释扫描 `qbapi.py`/`store.py` 无合成 state 写点，三条判据）/ **V1 值层**（动作后快照逐字不变 → 下一轮同步落替身真值，含 `checkingUP`）/ **V2 值域**（可持有 `queued*/forced*/checking*/moving/missingFiles`，未被压平）/ **E1 发射**（自有停种经同步回流触发转移扫描，源无关且不重复）/ **E2 一致性**（qB WebUI 暂停 与 auto-qb WebUI 暂停 行为逐字一致）/ **D1 G6 端到端**（陈旧快照窗口存在 → deferral 让位 → 回流后 G6 保护恢复，证明 deferral 是「推迟到新鲜时」而非「放弃保护」）/ **I1 幂等**（同 tick 二次 stop/start 被拦下且不写任何假 state 值）。**可选件 A2 采纳，且「一次决定」的答案是「不新增容器」**：幂等门复用 `own_writes`（新增 `group=False` 自身维度），与 deferral 共用登记/清理单点 ⇒ 从根上无双轨；并确立**方向自洽性**（快照不动 ⇒ 反向操作由传统 `is_stopped` 判据先拦，幂等门只管同向重复）⇒ 判据无需方向字段。

**下一步 = 提交本轮**（需用户显式指令）。计划 26-10-13-0540 状态已流转 Open → Done。

**S1 副产物已入池**：`issues/26-10-13-0626-question-grouping-transition-reflow-retrigger.html`（Open）—— 自有整组停种经下一轮同步回流，会再命中 `_handle_state_transitions` 的「上传转暂停」谓词（`grouping_mod.py:206`），追加一次缺文件扫描+停种。幂等、一轮收敛，属无谓重复；待拍板「接受 / 跨轮去重」，跨轮去重容器与 S2 `own_writes` 有合并空间。

**计划内两条口径纪律**（别在实现时丢掉）：① 发射时机**不得写「WEB 路径同 tick 必达」**——自家与外部变更同受 qB 节流约束，完全对称；② `own_writes` 的**有界性不能只押「qB 缓存一定会前进」**，必须有 TTL 兜底（否则任务饿死）。

**形态回退条件**：若团队判定 WEB 命令路径的窗口可接受，S2（deferral 层）可整省 ⇒ 回落 A1。

## 本专题已落件

| 件 | 状态 | 说明 |
|---|---|---|
| `reports/26-10-12-2148-report-seed-state-writeback-removal-feasibility.html` | Done（doc-updated 26-10-13-0441） | 双写通道取证 + A/B 方案裁定；0441 修订上修 R4、修正 B/B′ 行 |
| `plans/26-10-13-0413-plan-seed-state-writeback-truth-emission.html` | **Superseded** | B2（B′）实施计划；值层前提被 qB 服务端节流证否；**发射层结论仍有效**，可另件叠加 |
| `plans/26-10-13-0540-plan-seed-state-writeback-removal-local-deferral.html` | **Done** | A 系实施计划（形态 A3）；S0/S1/S2/S3 全部完成 |
| `testing/baselines/attachments/26-10-13-0714-seed-state-writeback-s3.md` | 基线切片 | S3 收尾落地后的全量基线（数字见 `kb.baseline`，不手抄） |
| `testing/baselines/attachments/26-10-13-0554-seed-state-writeback-s0.md` | 基线切片 | S0 落地后的全量基线（数字见 `kb.baseline`，不手抄） |
| `testing/baselines/attachments/26-10-13-0620-seed-state-writeback-s1.md` | 基线切片 | S1 值层落地后的全量基线（数字见 `kb.baseline`，不手抄） |
| `testing/baselines/attachments/26-10-13-0643-seed-state-writeback-s2.md` | 基线切片 | S2 deferral 落地后的全量基线（数字见 `kb.baseline`，不手抄） |
| `issues/26-10-13-0626-question-grouping-transition-reflow-retrigger.html` | **Open** | S1 副产物入池：自有整组停种经同步回流触发二次缺文件扫描（幂等、一轮收敛）；待拍板 接受 / 跨轮去重 |
| `tasks/26-10-13-backend-seed-state-writeback.md` | In Progress | 本专题档案（含 A/B 系对比、qB 源码证据链、S0 证据链） |
| `systemPatterns/main-loop.md` · `config-reference/keys.md` | 已修正 | 「qB 自带 WebUI 1500ms」→ 服务端 `RefreshInterval` 节流 |

---

<!-- slice: 26-10-22-0235-skip-check-arch.md; 最后活动: 2026-10-22 03:09 -->

# skip-check-arch

> 摘要: 核查 libtorrent 2.1.2 seed_mode 语义(上传前整片哈希 / 失败 force_recheck / verified 自毁), 判定 fastresume 标记不可替代 zSkipChecked, 出报告 26-10-22-0234
> 最后活动: 2026-10-22 03:09

**R0(2026-10-22 02:35):** 核查 libtorrent 2.1.2 seed_mode 语义(上传前整片哈希 / 失败 force_recheck / verified 自毁), 判定 fastresume 标记不可替代 zSkipChecked, 出报告 26-10-22-0234

**R1(2026-10-22 02:57):** R1 按用户复核重写报告 §2.4/§2.10: 补校验读与服务读合并的 I/O 账, 收益按完整/残缺分档, 纠正'零块外传'说法

**R2(2026-10-22 03:01):** R2 补残缺档下载量成本: 全量校验零流量/跳检把发现缺口推迟到最坏时点/整片放大; partial 闸门价值重述为保护不可逆下载量

**R3(2026-10-22 03:09):** 立 issue 26-10-22-0308: 跳检缺『不完整数据触发重新下载』防线(抽样校验/下载限速保险丝/结构性收紧三层), 与报告 §2.10 双向认领

---

<!-- slice: 26-10-29-0216-backend-hr-ext-site-permission.md; 最后活动: 2026-10-29 02:16 -->

# backend-hr-ext-site-permission

> 摘要: HR 扩展缺站点权限(MV3 可选权限重装后丢失)取证到修复: 扩展侧预检+拒发+逐站授权态+徽标第五态, 后端两 kind 归通道层并落盘通道痕, 通道态与病因文案两侧可见, zero_rows 改全档有效口径并补接页面层升级告警, 文档/坑档/18 例守阵/基线齐
> 最后活动: 2026-10-29 02:16

**R0(2026-10-29 02:16):** HR 扩展缺站点权限(MV3 可选权限重装后丢失)取证到修复: 扩展侧预检+拒发+逐站授权态+徽标第五态, 后端两 kind 归通道层并落盘通道痕, 通道态与病因文案两侧可见, zero_rows 改全档有效口径并补接页面层升级告警, 文档/坑档/18 例守阵/基线齐

---

<!-- slice: 26-10-30-0647-full-code-review-2.md; 最后活动: 2026-10-30 07:54 -->

# full-code-review-2

> 摘要: 认领并修复 issue 26-10-30-0550: HR 三处位置覆盖判据在 cutoff_done<=0 时退化恒通过(终态冻结/观察期出口/批量签发三条路全签永续放行)。新增共享纯函数 _lane_covers_done 作为单档覆盖证明唯一口径, 三处调用方收敛到它; 补守阵 test_position_proof_cutoff_zero_is_unprovable 并红验通过; test.full 实测数字见 kb.baseline
> 最后活动: 2026-10-30 07:54

**R0(2026-10-30 06:47):** 认领并修复 issue 26-10-30-0550: HR 三处位置覆盖判据在 cutoff_done<=0 时退化恒通过(终态冻结/观察期出口/批量签发三条路全签永续放行)。新增共享纯函数 _lane_covers_done 作为单档覆盖证明唯一口径, 三处调用方收敛到它; 补守阵 test_position_proof_cutoff_zero_is_unprovable 并红验通过; test.full 实测数字见 kb.baseline

**R1(2026-10-30 07:54):** 认领并修复 issue 26-10-30-0616(moving-phase-issue-restore): RelocateJob 新增持久化 move_issued(下发成功即落账), _load_jobs 对 MOVING 打 recover 标记, 新增 _recover 接线 recover_exec_phase 三分流(仍在搬⇒轮询/数据已到 dst⇒进 moved/未下发过⇒补发一次 setLocation), 补发路径同样落账; 三条重启恢复守阵红验通过(既有 test_restart_does_not_reissue_setlocation 保持绿); test.full 实测数字见 kb.baseline

**R2(2026-10-30 07:49):** 认领并修复 issue 26-10-30-0616(defer-due-budget): _pop_due 接过 defer_gate 并返回 (可执行批次, 让位批次) —— max_tasks 只约束可执行名额, 让位者留在堆外由 run_due 事后回填, 扫描面以 _DEFER_SCAN_FACTOR=5 封顶; run_due 返回值改为实际执行数; 两条新守阵(预算面/扫描上界)红验通过; issue 置 Done + 坑档 concurrency D-1 补预算面; test.full 实测数字见 kb.baseline

---

<!-- slice: 26-11-01-0229-qbmanager-disconnect-no-reconnect.md; 最后活动: 2026-11-01 02:29 -->

# qbmanager-disconnect-no-reconnect

> 摘要: 断连稳态守卫落地(issue 26-10-31-1029): 主循环 client=None+_last_conn_ok=False 跳请求线走重连, 恢复检测改 _ran_line 门; 全量绿
> 最后活动: 2026-11-01 02:29
**Refs（切片原文）:**

**R0(2026-11-01 02:29):** 断连稳态守卫落地(issue 26-10-31-1029): 主循环 client=None+_last_conn_ok=False 跳请求线走重连, 恢复检测改 _ran_line 门; 全量绿

---

<!-- slice: 26-11-02-0044-webui-move-relocate-qbtemp.md; 最后活动: 2026-11-02 00:44 -->

# webui-move-relocate-qbtemp

> 摘要: WEBUI 移动种子报「已移动失败」取证: relocate.enabled=true 时单种子移动走整组迁移闸门(计划 26-10-18-1604 P5 三入口接线为现行决策, 非实现走样; P2 原表「WebUI 单个直调 setLocation」已被 P5 改版), 误报根因 = qb_temp 闸门把内容根里外组种子的 .!qB 也计入拦截(relocate_mod 事实收集 + relocate_units GATE_QB_TEMP), 对 direct/file_links 形态属误报、待拍板是否收窄; 顺手改 drawer.js 单种子移动 okText「已移动」→「移动」(失败 toast 随变「移动失败」, 用户口径); 全量绿数字见 kb.baseline
> 最后活动: 2026-11-02 00:44
**Refs（切片原文）:**

**R0(2026-11-02 00:44):** WEBUI 移动种子报「已移动失败」取证: relocate.enabled=true 时单种子移动走整组迁移闸门(计划 26-10-18-1604 P5 三入口接线为现行决策, 非实现走样; P2 原表「WebUI 单个直调 setLocation」已被 P5 改版), 误报根因 = qb_temp 闸门把内容根里外组种子的 .!qB 也计入拦截(relocate_mod 事实收集 + relocate_units GATE_QB_TEMP), 对 direct/file_links 形态属误报、待拍板是否收窄; 顺手改 drawer.js 单种子移动 okText「已移动」→「移动」(失败 toast 随变「移动失败」, 用户口径); 全量绿数字见 kb.baseline

---

<!-- slice: 26-11-03-0032-rule-engine-redesign.md; 最后活动: 2026-11-03 01:06 -->

# rule-engine-redesign

> 摘要: 核实 issue 1304 与 2211 对 rule-engine-redesign 的落地情况: 1304 与 2211 均完全解决翻 Done; 自愈落盘缺陷按正确主题另入池 26-11-03-0104
> 最后活动: 2026-11-03 01:06
**Refs（切片原文）:**

**R0(2026-11-03 00:32):** 核实 issue 1304 与 2211 对 rule-engine-redesign 的落地情况: 1304 完全解决翻 Done, 2211 部分解决置 In Progress(G-05 未落); 双向补链与索引重建

**R1(2026-11-03 01:06):** 纠正 2211 错误归类: 两键语义梳理完全解决翻 Done; G-05 自愈 pop 缺 state.save 按原归类另入池 26-11-03-0104 bug 便签

---

<!-- slice: 26-11-03-0227-full-checking-selfheal.md; 最后活动: 2026-11-03 02:27 -->

# full-checking-selfheal

> 摘要: 认领并修复 issue 26-11-03-0104: full_checking 假失败自愈 pop 后补 state.save 落盘, 新增自愈发生/未发生两路径用例
> 最后活动: 2026-11-03 02:27
**Refs（切片原文）:** memory-bank/issues/26-11-03-0104-bug-full-checking-selfheal-state-save.html

**R0(2026-11-03 02:27):** 认领并修复 issue 26-11-03-0104: full_checking 假失败自愈 pop 后补 state.save 落盘, 新增自愈发生/未发生两路径用例

---

<!-- slice: 26-11-02-0146-relocate-qbtemp-narrow.md; 最后活动: 2026-11-03 03:17 -->

# relocate-qbtemp-narrow

> 摘要: qb_temp 闸门按归属收窄落地(plan 26-11-02-0134): relocate_mod 收集层把 ext 的 .!qB 剥后缀归属三分(own 对回本组→硬拦面; foreign/unowned 与普通条目同走归属分类降 notes), relocate_units 文案与 docstring 同步(gate id 不变), 守阵三案(foreign/unowned/own-matched)+全量绿数字见 kb.baseline 切片 26-11-02-0144; 依据 = lt RC_1_2/RC_2_0 aux::move_storage 逐文件搬运源码核实; S5 真机复验已通过(2026-11-03 RM04-10, 环境1, 1 passed; 切片 26-11-03-0316-real-RM04-qbtemp)
> 最后活动: 2026-11-03 03:17
**Refs（切片原文）:**

**R0(2026-11-02 01:46):** qb_temp 闸门按归属收窄落地(plan 26-11-02-0134): relocate_mod 收集层把 ext 的 .!qB 剥后缀归属三分(own 对回本组→硬拦面; foreign/unowned 与普通条目同走归属分类降 notes), relocate_units 文案与 docstring 同步(gate id 不变), 守阵三案(foreign/unowned/own-matched)+全量绿数字见 kb.baseline 切片 26-11-02-0144; 依据 = lt RC_1_2/RC_2_0 aux::move_storage 逐文件搬运源码核实; S5 真机复验留 Open(计划与档案)

**R1(2026-11-02 02:22):** R1 同族第二例收口(用户复测报 GATE_SPACE 误拦, 拍板按方案A+B修复): relocate_mod 新增 _volume_free_resolved(空间祖先回退)/_same_volume_resolved(同卷上溯, 实施中发现同根因一并收口), 全链不可达维持硬拦; relocate_units same_fs 单成员 note 文案对齐(方案B); 守阵四案+定向 69 passed+全量绿数字见 kb.baseline 切片 26-11-02-0222; 计划 R1(26-11-02-0220)/档案 S6-S8 已并入

**R2(2026-11-02 03:18):** R2 全闸门同族扫描三项处置落地(用户拍板按建议处置): #1 同卷空间豁免(same_volume=True 时空间预检不适用, rename 不占额外空间); #2 目标冲突去 names[:50] 截断改全量(漏拦致进度清零的反向风险); #3 新增 target_type 闸门(目标存在但不是目录); 另补覆盖率退化面守阵四处(首跑 98.86% 红后回 99%); 全量绿数字见 kb.baseline 切片 26-11-02-0317; 计划 R2(26-11-02-0316)/档案 S9-S11 已并入

**R3(2026-11-03 03:17):** S5 真机复验通过(RM04-10, 环境1 qB 5.2.3): 内容根含外组 .!qB 时单种子迁移放行且外组 .!qB/普通条目原地不动; 本组 .!qB 仍 qb_temp 硬拦; R1 目标叶子未建可上溯 + R2 同卷 note/target_type 真跑绿(1 passed); 计划与档案翻 Done

---

<!-- slice: 26-11-03-0424-taskqueue-dry-run-chain.md; 最后活动: 2026-11-03 04:24 -->

# taskqueue-dry-run-chain

> 摘要: 认领并复验 issue 26-10-31-0449(taskqueue dry_run 传递守阵缺口): 守阵已由 R25 S5 补入并实测通过, 本轮红验两变异形态(run_due 传 None / _run_one 传 None)全红、还原后绿, 登记 guards.md; src 零改动
> 最后活动: 2026-11-03 04:24
**Refs（切片原文）:** memory-bank/issues/26-10-31-0449-bug-taskqueue-dry-run-chain.html

**R0(2026-11-03 04:24):** 认领并复验 issue 26-10-31-0449(taskqueue dry_run 传递守阵缺口): 守阵已由 R25 S5 补入并实测通过, 本轮红验两变异形态(run_due 传 None / _run_one 传 None)全红、还原后绿, 登记 guards.md; src 零改动

---

<!-- slice: 26-11-03-1119-webui-bind-fail-fast.md; 最后活动: 2026-11-03 22:23 -->

# webui-bind-fail-fast

> 摘要: 启动期 fail-fast + 跨平台占用者诊断已合入 develop; 回写 main-loop/web-runtime/core-runtime/overview 事实; 本轮 R2 修其测试面 CI 副作用(启动失败用例真跑 ss -ltnp → 注入探针替身 + 接线断言), 零 src 改动
> 最后活动: 2026-11-03 22:23
**Refs（切片原文）:** [计划](../../plans/26-11-03-0930-plan-webui-bind-fail-fast.html) · [档案](../../tasks/26-11-03-webui-bind-fail-fast.md) · [全量基线](../../testing/baselines/26-11-03-2158-webui-bind-fail-fast-ci-sidefx.md) · [真机 RM01-06](../../testing/real-baselines/26-11-03-1045-real-rm01-webui-bind.md) · [issue In Progress](../../issues/26-11-03-0316-bug-webui-bind-failure-silent.html)

**当前状态**: S1-S6b 已完成并合入 develop(档案已标 Done); 本轮 R2 只动测试面(消除 CI 侧真实外部命令副作用), `src/` 零改动; 全量实测数字见 `commands run kb.baseline`。

**R0(2026-11-03 11:19):** S6b 收尾: 新建全量基线切片(4971 passed + 2 skipped / 99%); 回写 main-loop/web-runtime/core-runtime/overview 的启动期 fail-fast、port_owner、WebUIBindError、lifecycle_ready 事实; 新建 task 档案 26-11-03-webui-bind-fail-fast; issue 保持 In Progress

**R1(2026-11-03 11:45):** 收口 issue 与计划状态，标记已交付

**R2(2026-11-03 21:59):** 修复 CI sidefx 越界(越界项 POPEN ss -ltnp): 启动失败用例只验文案、未注入端口探针替身, Linux 上真跑 ss -ltnp; 改为注入 describe_port_owner 替身 + 断言探针仍被调用(host/port), 另补 ss argv 精确守阵; 零 src 改动, 未登记放行清单; 数字见 kb.baseline

**R3(2026-11-03 22:23):** 追加: tests/test_tmp_bootstrap.py 模块 docstring 改 raw 前缀清掉 \\T 无效转义(编译期 SyntaxWarning 归零, 字面语义与判据未动); notifier 按命令名拦截 PowerShell 的耦合入池(bug/light, Open, 未挂本档案); 全量数字见 kb.baseline

---

<!-- slice: 26-11-03-2227-hot-reload-group-index.md; 最后活动: 2026-11-03 23:58 -->

# hot-reload-group-index

> 摘要: 已完成：方案 B 保留分组索引（删 reset_runtime 3 个 clear、保留 group_key_migrations）+ 3 条守阵/回归测试 + 环境2 真机 R0–R6 PASS（0.22s / 27 次采样零回落 / files 零重放）；issue 2206 Done、2129 更正回链、计划 Done，待合并进 develop
> 最后活动: 2026-11-03 23:58
**Refs（切片原文）:**

**R0(2026-11-03 22:27):** 写修复计划 26-11-03-2223（推荐方案B保留分组索引）并用 grilling 拷问，结论落 §07/§08；未改代码

**R1(2026-11-03 22:57):** 计划推进至实施就绪：D1-D6 拍板落 §05/§06，新增实施拆分·真机验证方案·环境选择判据·回滚与验证判据·证据边界；建本地分支 fix/hot-reload-group-index（基于 6ffa85a3）

**R2(2026-11-03 23:52):** Step C 真机验证 PASS: 环境2(56589/56590)非 dry-run, L2 改 interval 后 27/27 采样组行保持、key 不变、成员不丢、files 重建后 0 次重放; 收尾种子/进程/qB 复原

**R3(2026-11-03 23:58):** Step D 收尾: issue 26-11-03-2206 置 Done(方案B 保留分组索引, 3 条守阵/回归测试, 真机 0.22s/27 次采样零回落/files 零重放); 26-10-01-2129 更正 Superseded 理由并回链; rules_mod 注释对齐新语义; 计划置 Done

