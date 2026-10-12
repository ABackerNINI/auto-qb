# 26-10-13-0538-seed-state-writeback — 种子状态双写通道：B 系证否转 A 系，A 系计划已立

> 摘要: 专题 `seed-state-writeback`。承接报告 26-10-12-2148。先按用户令对比 A 系四形态（裁定：分水岭只在 G4/G6 安全窗，推荐 A3 = A1 删合成回写 + 局部 deferral，可叠 A2 `pending_writes`）与 B 系三支（裁定：实际候选只剩 B′ = 真值回写 + 显式发射，B1/B3 与 26-10-12-2229 的源无关语义冲突）；随后按用户指定立 B2 实施计划 26-10-13-0413。立件后用户质疑「qB 返回信息并非实时、每 1.5s 才更新一次」→ 回 qB 源码（`D:/Projects/Else/qBittorrent`）**确认成立且更硬**：qB 服务端 torrent 状态按 `BitTorrent/Session/RefreshInterval` 节流刷新（默认 1500ms），写后直查 `torrents_info` 读到的是写前值 ⇒ B/B′ 值层退化为 no-op，R4 是**默认粒度**而非边界竞态。用户定调 RefreshInterval 保持默认、暂不改 qB 设置 ⇒ B2 计划置 Superseded；报告抬 26-10-13-0441 修订（上修 §3 R4、修正 §5 B/B′ 行）；另修正 `systemPatterns/main-loop.md` 与 `config-reference/keys.md` 两处「qB 自带 WebUI 1500ms」归因漂移。本轮收尾已提交（`caa40a7e`），随后**另立 A 系实施计划 26-10-13-0540**（形态 A3，含 P1 G4/G6 可达性确认作为决定形态的第一步）。零代码改动、未跑测试。
> 最后活动: 2026-10-13 05:42
> 状态: In Progress（A 系计划已立件，待拍板开工）

**Refs:** memory-bank/tasks/26-10-13-backend-seed-state-writeback.md

## 现在做到哪

B 系路线已否，**A 系实施计划已立**：`plans/26-10-13-0540-plan-seed-state-writeback-removal-local-deferral.html`（`doc-status=Open`，待拍板）。

**开工第一步是 S0 前置**（计划 §3），三项都必须先做：

1. **P1 · G4/G6 可达性确认** —— 同 `run_due` 批次内是否真能出现「先起下载方 D → 再对同组成员 C 跳检」。**这是本计划唯一的形态分岔点**：不可达 ⇒ 形态取 A1（deferral 整层可省）；可达 ⇒ 取 A3（deferral 必需）。
2. **P2 · `state_changed` 同名消歧** —— `qbmanager.py:517` 局部变量 vs `store.state_changed` 字段同名不同义且同处一个主循环体。
3. **P3 · 替身能力补齐** —— `FakeClient` 的四个暂停轴方法（`tests/helpers.py:332-343`）只记 `calls`、不翻转 state。

**计划内两条口径纪律**（本轮取证换来的，别在实现时丢掉）：① 发射时机**不得写「WEB 路径同 tick 必达」**——自家与外部变更同受 qB 节流约束，完全对称；② `own_writes` 的**有界性不能只押「qB 缓存一定会前进」**，必须有 TTL 兜底（否则任务饿死）。

## 本专题已落件

| 件 | 状态 | 说明 |
|---|---|---|
| `reports/26-10-12-2148-report-seed-state-writeback-removal-feasibility.html` | Done（doc-updated 26-10-13-0441） | 双写通道取证 + A/B 方案裁定；0441 修订上修 R4、修正 B/B′ 行 |
| `plans/26-10-13-0413-plan-seed-state-writeback-truth-emission.html` | **Superseded** | B2（B′）实施计划；值层前提被 qB 服务端节流证否；**发射层结论仍有效**，可另件叠加 |
| `plans/26-10-13-0540-plan-seed-state-writeback-removal-local-deferral.html` | **Open** | A 系实施计划（形态 A3）；含 P1/P2/P3 前置与守阵/分期/回退 |
| `tasks/26-10-13-backend-seed-state-writeback.md` | In Progress | 本专题档案（含 A/B 系对比的完整论证与 qB 源码证据链） |
| `systemPatterns/main-loop.md` · `config-reference/keys.md` | 已修正 | 「qB 自带 WebUI 1500ms」→ 服务端 `RefreshInterval` 节流 |
