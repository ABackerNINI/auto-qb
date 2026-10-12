# 26-10-13-0538-seed-state-writeback — 种子状态双写通道：B 系立件与证否，方向回 A 系

> 摘要: 专题 `seed-state-writeback`。承接报告 26-10-12-2148。先按用户令对比 A 系四形态（裁定：分水岭只在 G4/G6 安全窗，推荐 A3 = A1 删合成回写 + 局部 deferral，可叠 A2 `pending_writes`）与 B 系三支（裁定：实际候选只剩 B′ = 真值回写 + 显式发射，B1/B3 与 26-10-12-2229 的源无关语义冲突）；随后按用户指定立 B2 实施计划 26-10-13-0413。立件后用户质疑「qB 返回信息并非实时、每 1.5s 才更新一次」→ 回 qB 源码（`D:/Projects/Else/qBittorrent`）**确认成立且更硬**：qB 服务端 torrent 状态按 `BitTorrent/Session/RefreshInterval` 节流刷新（默认 1500ms），写后直查 `torrents_info` 读到的是写前值 ⇒ B/B′ 值层退化为 no-op，R4 是**默认粒度**而非边界竞态。用户定调 RefreshInterval 保持默认、暂不改 qB 设置 ⇒ B2 计划置 Superseded；报告抬 26-10-13-0441 修订（上修 §3 R4、修正 §5 B/B′ 行）；另修正 `systemPatterns/main-loop.md` 与 `config-reference/keys.md` 两处「qB 自带 WebUI 1500ms」归因漂移。方向回到 **A 系 = A + 局部 deferral**。本轮零代码改动、未跑测试。
> 最后活动: 2026-10-13 05:38
> 状态: In Progress（方向已定 A 系，计划待另件立）

**Refs:** memory-bank/tasks/26-10-13-backend-seed-state-writeback.md

## 现在做到哪

B 系路线已否，方向回到 A 系。当前手上没有待实施的计划件 —— **下一步是另立 A 系实施计划**（`memory-bank/plans/`，单文件 HTML dark，doc-topic 沿用 `seed-state-writeback`）。

A 系计划的形态与落点已在本专题档案里钉死（`tasks/26-10-13-backend-seed-state-writeback.md`）：

- **形态**：A1 删合成回写（`qbapi._sync_paused_state` + 四入口写后同步 + `store.update_torrent_fields` 的 `state=` 形参 + `qbmanager.py:810-815` 与 `store.py:303-305` 两处注释/docstring）＋ 局部 deferral（G4/G5/G6/G7-8 与决策链 0/1，落点 `ops_mod.py:640/655`、`checking.py:88/94`、`TaskQueue.run_due` 单入口 `qbmanager.py:725`）；幂等可选叠 `pending_writes` 意图标记。
- **计划第一步必须含三项前置**：① **G4/G6 可达性确认** —— 同 task 批次内是否真能出现「先起下载方 D → 再对同组成员 C 跳检」（证明不可达则 A1 即够）；② `state_changed` **同名消歧**（`qbmanager.py:517` 局部变量 vs `store.state_changed` 字段）；③ **替身能力补齐** —— `FakeClient` 的 `torrents_start/stop/pause/resume`（`tests/helpers.py:332-343`）只记 `calls`、不翻转 state。
- **守阵改造面**：3 条直接守阵（`test_actions.py:157/179/210`）＋ 4 处 `state=` 直接调用点（`test_sync.py:439`、`test_torrents.py:854`、`test_webui_delta_mirror.py:404` 与 `:763`）。

## 本专题已落件

| 件 | 状态 | 说明 |
|---|---|---|
| `reports/26-10-12-2148-report-seed-state-writeback-removal-feasibility.html` | Done（doc-updated 26-10-13-0441） | 双写通道取证 + A/B 方案裁定；0441 修订上修 R4、修正 B/B′ 行 |
| `plans/26-10-13-0413-plan-seed-state-writeback-truth-emission.html` | **Superseded** | B2（B′）实施计划；值层前提被 qB 服务端节流证否；**发射层结论仍有效**，可另件叠加 |
| `tasks/26-10-13-backend-seed-state-writeback.md` | In Progress | 本专题档案 |
| `systemPatterns/main-loop.md` · `config-reference/keys.md` | 已修正 | 「qB 自带 WebUI 1500ms」→ 服务端 `RefreshInterval` 节流 |
