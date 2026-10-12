# 26-10-13-0538-seed-state-writeback — 种子状态双写通道：A 系 S0 前置已落地，形态定 A3

> 摘要: 专题 `seed-state-writeback`。承接报告 26-10-12-2148。先按用户令对比 A 系四形态（裁定：分水岭只在 G4/G6 安全窗，推荐 A3 = A1 删合成回写 + 局部 deferral，可叠 A2 `pending_writes`）与 B 系三支（裁定：实际候选只剩 B′ = 真值回写 + 显式发射，B1/B3 与 26-10-12-2229 的源无关语义冲突）；随后按用户指定立 B2 实施计划 26-10-13-0413。立件后用户质疑「qB 返回信息并非实时、每 1.5s 才更新一次」→ 回 qB 源码（`D:/Projects/Else/qBittorrent`）**确认成立且更硬**：qB 服务端 torrent 状态按 `BitTorrent/Session/RefreshInterval` 节流刷新（默认 1500ms），写后直查 `torrents_info` 读到的是写前值 ⇒ B/B′ 值层退化为 no-op，R4 是**默认粒度**而非边界竞态。用户定调 RefreshInterval 保持默认 ⇒ B2 计划置 Superseded；报告抬 26-10-13-0441 修订；另修正两处归因漂移。收尾提交（`caa40a7e`）后**另立 A 系实施计划 26-10-13-0540**（形态 A3）并提交（`3f742233`）。**本轮执行 S0 前置三件**：P1 可达性确认按 **auto-qb 能力面**（非某份配置）判定 **可达 ⇒ 形态定 A3**；P2 `state_changed` 消歧改名；P3 `FakeClient` 四方法真实翻转 state。**随后完成 S1 值层**：删合成回写整段（`_sync_paused_state` + `update_torrent_fields(state=)`），快照语义收敛为「严格 = 最近一次同步的应用结果」，源无关发射天然获得；三条守阵按新契约重写（含一条契约翻面）、4 调用点迁移。全绿（基线切片 `baselines/26-10-13-0554-seed-state-writeback-s0.md`）。S0 落地随本专题入库。
> 最后活动: 2026-10-13 06:26
> 状态: In Progress（S1 值层已完成，二次触发已入池，下一步 S2 deferral）

**Refs:** memory-bank/tasks/26-10-13-backend-seed-state-writeback.md

## 现在做到哪

**S0 前置三件已落地**（计划 §3），形态**定为 A3**：

1. **P1 · G4/G6 可达性确认 → 可达**。判据按 **auto-qb 提供给用户的能力面**，**不按某份配置**（首轮误用本机 `config.yml` 当能力边界，26-10-13-0601 订正）。能力面：`start` 是一等规则动作（`schema/rules.py:227` + 示例 `test_yamls/test_actions/test_start.yml`）、`checking.auto_start` 是文档化选项（`schema/rules.py:185`）、规则 `actions` 顺序执行 ⇒ 三个可达 witness：**W1** `[{start},{checking}]` 顺序保证（纯配置）；**W2** `auto_start: true` 跨任务（纯配置）；**W3** WEB 命令线 resume + 同 tick 跳检（用户触发）。今日（有回写）该路径受 G4/G6 保护，**A1 会让它回归成放行窗口**，A3 用 deferral 保住保护 ⇒ 取 A3。证据链全文见任务档案「思考过程与决策」§6。
2. **P2 · `state_changed` 消歧改名** —— `qbmanager.py:517` 局部变量 → `cmd_changed_state`（连带 `:528/534/540/544` + 消歧注释）。
3. **P3 · 替身能力补齐** —— `tests/helpers.py` 新增 `FakeClient._apply_paused_state`，四暂停轴方法真实翻转 state（UP/DL 完成位语义，`None` = 全体）；`calls` 形状逐字不变。

**S1 值层已落地**（26-10-13-0620）：删除合成回写整段（`QbApi._sync_paused_state` + `store.update_torrent_fields` 的 `state=` 形参），四入口只调 raw client；快照语义收敛为「**严格 = 最近一次同步的应用结果**」⇒ 自家停/起与外部变更**源无关**（状态变化只经下一轮真实 delta 进 `state_changed`，被转移检测与状态事件看见）。三条守阵按新契约重写（`test_stop_preserves_completeness` 改钉「快照逐字不变」；`test_pause_resume_sync_store_snapshot` **契约翻面**并改名 `test_pause_resume_no_same_tick_writeback`；`test_start_stop_idempotent` 清过时注释）、4 处 `state=` 调用点迁移、`test_grouping` 两条承认「整组停种经同步回流再触发一次、一轮即收敛」。坑档 `concurrency` 补 `state` 例外、`guards.md` A-04 行按反转更新。

**下一步 = S2 deferral**：`store.own_writes`（hash → 登记时刻）+ TTL 兜底 + 三处闸门（D-1 `TaskQueue.run_due` 队列级 / D-2 `ops_mod._skip_gates_detail` 的 G4–G8 / D-3 `checking.py` 决策链 0/1），并定 D-1 的任务 hash 取法（`Task.hash` 已确认存在）。

**S1 副产物已入池**：`issues/26-10-13-0626-question-grouping-transition-reflow-retrigger.html`（Open）—— 自有整组停种经下一轮同步回流，会再命中 `_handle_state_transitions` 的「上传转暂停」谓词（`grouping_mod.py:206`），追加一次缺文件扫描+停种。幂等、一轮收敛，属无谓重复；待拍板「接受 / 跨轮去重」，跨轮去重容器与 S2 `own_writes` 有合并空间。

**计划内两条口径纪律**（别在实现时丢掉）：① 发射时机**不得写「WEB 路径同 tick 必达」**——自家与外部变更同受 qB 节流约束，完全对称；② `own_writes` 的**有界性不能只押「qB 缓存一定会前进」**，必须有 TTL 兜底（否则任务饿死）。

**形态回退条件**：若团队判定 WEB 命令路径的窗口可接受，S2（deferral 层）可整省 ⇒ 回落 A1。

## 本专题已落件

| 件 | 状态 | 说明 |
|---|---|---|
| `reports/26-10-12-2148-report-seed-state-writeback-removal-feasibility.html` | Done（doc-updated 26-10-13-0441） | 双写通道取证 + A/B 方案裁定；0441 修订上修 R4、修正 B/B′ 行 |
| `plans/26-10-13-0413-plan-seed-state-writeback-truth-emission.html` | **Superseded** | B2（B′）实施计划；值层前提被 qB 服务端节流证否；**发射层结论仍有效**，可另件叠加 |
| `plans/26-10-13-0540-plan-seed-state-writeback-removal-local-deferral.html` | **Open** | A 系实施计划（形态 A3）；S0 已完成，待 S1 |
| `testing/baselines/26-10-13-0554-seed-state-writeback-s0.md` | 基线切片 | S0 落地后的全量基线（数字见 `kb.baseline`，不手抄） |
| `testing/baselines/26-10-13-0620-seed-state-writeback-s1.md` | 基线切片 | S1 值层落地后的全量基线（数字见 `kb.baseline`，不手抄） |
| `issues/26-10-13-0626-question-grouping-transition-reflow-retrigger.html` | **Open** | S1 副产物入池：自有整组停种经同步回流触发二次缺文件扫描（幂等、一轮收敛）；待拍板 接受 / 跨轮去重 |
| `tasks/26-10-13-backend-seed-state-writeback.md` | In Progress | 本专题档案（含 A/B 系对比、qB 源码证据链、S0 证据链） |
| `systemPatterns/main-loop.md` · `config-reference/keys.md` | 已修正 | 「qB 自带 WebUI 1500ms」→ 服务端 `RefreshInterval` 节流 |
