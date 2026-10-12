# 26-10-13-backend-seed-state-writeback — 种子状态双写通道：B 系立件与证否，方向回 A 系

**Status:** In Progress
**Added:** 2026-10-13
**Updated:** 2026-10-13 05:38
**Topics:** seed-state-writeback
**Summary:** 承接报告 26-10-12-2148（种子状态双写通道调查）。用户先令对比 A 系四形态（A1 纯透传 / A2 +幂等标记 / A3 +局部 deferral / A4 +全系统 deferral），再令对比 B 系（B1 纯真值回写 / B2=B′ 真值回写+显式发射 / B3=B+C 显式登记），随后指定按 B2 立实施计划（26-10-13-0413）。立件后用户质疑「qB 返回信息并非实时、每 1.5s 才更新」，要求回源码确认（qB 源码 `D:/Projects/Else/qBittorrent`）——**确认成立且比质疑更硬**：qB 服务端 torrent 状态按 `BitTorrent/Session/RefreshInterval` 节流刷新（默认 1500ms），写后直查 `torrents_info` 读到的是写前值 ⇒ B/B′ 的值层退化为 no-op。用户定调 RefreshInterval 保持默认、暂不改 qB 设置 ⇒ B2 计划值层无救，置 Superseded；报告上修 §3 R4、修正 §5 B/B′ 行；另修正 `systemPatterns/main-loop.md` 与 `config-reference/keys.md` 两处「qB 自带 WebUI 1500ms」归因漂移。方向回到 **A 系 = A + 局部 deferral**（报告原推荐，且被该证据强化），A 系计划待另件立。本轮零代码改动、未跑测试。
**Refs:** memory-bank/reports/26-10-12-2148-report-seed-state-writeback-removal-feasibility.html,memory-bank/plans/26-10-13-0413-plan-seed-state-writeback-truth-emission.html,memory-bank/activeContext/26-10-13-0538-seed-state-writeback.md

## 原始请求

> 26-10-12-2148-report-seed-state-writeback-removal-feasibility.html, 对比几个A系列方案, 该改动涉及到底层是一次重要的重构, 必须仔细

> 对比B系列方案

> 按照B2方案写一个实施计划

> 我记得之前有个报告说的是qb返回信息并不是实时的, 而是每1.5更新一次, 这可能动摇该方案的基础, 需要确认, qb的源码在D:\Projects\Else中

> 修正文档, RefreshInterval 为默认值, 暂不考虑改qB设置, 更新报告后转Superseded

> 提交, 然后另立A系计划

## 思考过程与决策

### 1. A 系对比（问答轮，对话内作答，零文件改动）

按报告 §5 拆出 A 系四形态，逐条回代码复核（报告论断全部对上）：

- **A1 纯透传移除**：删 `_sync_paused_state`（`qbapi.py:96-126`）与四入口（`128-148`）的写后同步；`store.update_torrent_fields` 的 `state=` 形参（`store.py:487/503/506/512-516/535-536/543-544`）随之删除。R1–R6 全消、源无关发射天然获得；**G4/G6 陈旧-放行窗口开出**（唯一实质安全缺口）。
- **A2 = A1 + `pending_writes` 意图标记**：只带「本 tick 发过停/起」的意图、不带假值 ⇒ 不犯 R1–R6 任一条，只补同 tick 幂等。四者中唯一「零副作用补偿件」。
- **A3 = A1 + 局部 deferral**：只对校验类决策（G4/G5/G6/G7-8 + 决策链 0/1）延迟到下一 tick，收回 G4/G6 窗口。消费点可枚举（`ops_mod.py:640/655`、`checking.py:88/94` + `TaskQueue.run_due` 单入口 `qbmanager.py:725`）。代价 = 引入跨切面不变量（纪律性安全）。
- **A4 = A1 + 全系统 deferral**：把该不变量推到全系统，换「同 tick 全决策新鲜」——非硬需求时性价比最差。

**裁定**：分水岭只有 G4/G6 一道；其余差异都是 ≤1 tick 滞后，且与外部变更今天已有的工作模式对称。推荐 **A3（可叠 A2）**。

**本轮增量（报告未写透的三点）**：① `state=` 的测试耦合比报告列的大 —— 除 3 条守阵（`test_actions.py:157/179/210`）外另有 4 处直接调用（`test_sync.py:439`、`test_torrents.py:854`、`test_webui_delta_mirror.py:404` 与 `:763`）；② `qbmanager.py:517` 的局部变量 `state_changed` 与 `store.state_changed` **同名不同义且同处一循环**，实施前须消歧；③ `transitions` 相位被刻意排在自有动作**之前**（`qbmanager.py:810-815`），故命令线（WEB）路径因 P0-5 补刷新可**同 tick**发射、而分组/task 线自有停种的发射落到**下一轮** —— 两条验收口径必须分开写。

### 2. B 系对比（问答轮，对话内作答，零文件改动）

把 B 系拆成**两层**：值层（真值回写）三支相同；发射层三分支决定成败。

- **B1 纯真值回写**：只修值失真，**吸收盲点原样保留** ⇒ 隐含站回 26-10-12-2229 之前的立场（「吸收是对的」），与已拍板的源无关语义冲突。淘汰。
- **B2 = B′**：值层 + `pending_self_state: {hash: 动作前基线}` 显式发射通道。B 系唯一完整形态。
- **B3 = B + C**：state 的 `self_caused_fields` 同款期望值登记 —— 只买到 R3 可观测化，**设计目的就是吸收**，压制照旧。淘汰。

**B2 对撞 A3**：A3 把「新鲜」降级为纪律（保「快照严格 = sync 结果」）；B2 把「干净」降级为成本（保「同 tick 全决策新鲜」）。

**B2 落地两处易错点（本轮增量）**：① **不许污染 `store.state_changed`**（其语义是「本轮 qB 上报的变化」），发射须走独立登记集合；② **登记只改 `prev`、不改基线** —— 改基线会污染真值基线，真值下轮落地时又判成「外部变化」⇒ 双重触发。另给出零签名改动捷径：相位表起点把登记 hash 的 prev 写进独立只读视图（两消费点都读 `store.state_snapshot`，可直接覆写它；轮末 `update_state_snapshot` 整体重建自然复位），唯一边界是**失败轮不重建** → 覆写残留一轮。

### 3. B2 实施计划立件（26-10-13-0413）

按 `delivery-artifact` 落 `memory-bank/plans/`，单文件 HTML dark。相对报告原文收紧四处：① 值层收为「**只回写 `state` 单字段**」窄口径（`torrents_info` 返回整对象，全字段回写会把 `tags`/`category` 带进快照，与既有 `self_caused_fields` 撞成双轨）；② 发射层两条纪律写死；③ 补齐替身缺口（`FakeClient` 的 `torrents_start/stop/pause/resume`（`tests/helpers.py:332-343`）**只记 `calls`、不翻转 state**，B2 的「快照 == 真值」守阵无从断言）；④ 把「同 tick 幂等降为真值节拍」写成显式守阵而非按报告口径声称「全保留」。

### 4. qB 源码取证（本轮最关键的一段）

用户质疑「qB 返回信息并非实时、每 1.5s 才更新」。回 `D:/Projects/Else/qBittorrent` 取证，**确认成立且比质疑更硬**：

| 事实 | 锚点 |
|---|---|
| 状态刷新间隔默认 **1500 ms**，配置键 `BitTorrent/Session/RefreshInterval` | `sessionimpl.cpp:575`（宏 `:481`） |
| `enqueueRefresh()` 用 `QTimer::singleShot(refreshInterval(), …)` **延迟**投递 `post_torrent_updates()` + `post_session_stats()` | `sessionimpl.cpp:6009-6027` |
| alert 侧每轮重挂 ⇒ 自维持 ~1500 ms 循环 | `sessionimpl.cpp:6557-6560`、`:6736-6739` |
| `stop()/start()` **只翻 `m_isStopped`、不调 `updateState()`**；`setAutoManaged` 只动 flags、`handleQueueingModeChanged` 不在暂停路径 | `torrentimpl.cpp:2014-2060`（逐条排除即时路径） |
| `m_state` 只在 alert 路径的 `updateStatus()` 里重算 | `torrentimpl.cpp:1289`、`:2690-2700` |
| WebAPI 的 `state` = `torrentStateToString(torrent.state())`；`/sync/maindata` 同源 | `serialize_torrent.cpp:141`、`synccontroller.cpp:492` |
| 可在 GUI 改：高级设置 “Refresh interval”，**最小 30 ms** | `advancedsettings.cpp:327/829-834` |

**结论**：写后 ≤1.5 s 内直查 `torrents_info` 读到的仍是**写前值** ⇒ 值层写回退化为 no-op，「同 tick 新鲜」在暂停轴上**结构性不可得**；R4 是**默认粒度**而非边界竞态。**该证据封顶所有「真值回写」类方案**，同时**强化 A 系**（真实「新鲜」在 qB 侧本就不存在，删合成回写不损失真实新鲜度，只损失自造的假新鲜；G4/G6 安全窗与 qB 节流无关）。

### 5. 修正与状态流转（用户指令）

- 两处归因漂移修正：`systemPatterns/main-loop.md:59`、`config-reference/keys.md:12` 把服务端节流误述为「qB 自带 WebUI 1500ms 更新一次」。
- 报告 26-10-12-2148 抬修订号 **26-10-13-0441**：新增头部修订记录；§1 摘要「推荐路径」补证；**§3 R4 上修为「默认粒度」**并补全证据链；**§5 B/B′ 两行删掉被证否的「同 tick 新鲜度全保留」**；§5 裁定框与升级条件框补记（推荐 ① 维持并加强）；尾注记明计划已立件并置 Superseded。
- 计划 26-10-13-0413 置 **Superseded**（`doc-status` + 顶部废弃横幅 + 变更记录 + footer），并明确保留有效部分：**发射层 `pending_self_state` 不依赖新鲜度，成立，可独立叠加在 A 系之上**。用户定调：`RefreshInterval` 保持默认、暂不考虑改 qB 设置。

## 实现计划

本专题当前无代码改动。后续按 A 系推进（另件立计划）：

1. **A 系计划立件**（`memory-bank/plans/`，单文件 HTML dark，沿用 doc-topic `seed-state-writeback`）：形态 = **A1 删合成回写 + 局部 deferral（可选叠 A2 `pending_writes`）**。
2. **计划第一步须含三项前置**：① G4/G6 可达性确认（同 task 批次内是否真能出现「先起下载方 D → 再对同组成员 C 跳检」—— 证明不可达则 A1 即够）；② `state_changed` 同名消歧；③ 替身能力补齐（`FakeClient` 四方法真实翻转 state）。
3. **落地批次**：值层删除（`_sync_paused_state` + `state=` 形参 + 3 条守阵重写 + 4 个调用点迁移）→ 自写集 `own_writes` + 局部 deferral 闸门 → 收尾（守阵/红验/坑档口径/基线切片）。

## 子任务状态表

| # | 子任务 | 状态 |
|---|---|---|
| 1 | A 系四形态对比（对话内） | 已完成 |
| 2 | B 系三支对比（对话内） | 已完成 |
| 3 | B2 实施计划立件（26-10-13-0413） | 已完成 |
| 4 | qB 源码取证：服务端状态节流（RefreshInterval 1500ms） | 已完成 |
| 5 | 两处归因漂移修正（main-loop.md / keys.md） | 已完成 |
| 6 | 报告 26-10-12-2148 抬 26-10-13-0441 修订 | 已完成 |
| 7 | B2 计划置 Superseded | 已完成 |
| 8 | 本专题立档 + 切片 | 已完成 |
| 9 | **A 系计划另件立** | **待办** |
| 10 | A 系计划实施（含三项前置） | 待办 |

## 进度日志

- **2026-10-13** — 会话开工同步 `8d7585d7 → 412ae4dd`（远端领先 3 笔，快进）。
- **2026-10-13** — A 系四形态对比完成（对话内作答，零文件改动）；产出裁定：分水岭只在 G4/G6，推荐 A3（可叠 A2）。
- **2026-10-13** — B 系三支对比完成（对话内作答，零文件改动）；裁定 B 系实际候选只剩 B′（B1/B3 与 2229 源无关语义冲突）。补 B2 两处落地易错点与一条零签名捷径。
- **2026-10-13 04:13** — 按用户指令立 B2 实施计划 `plans/26-10-13-0413-plan-seed-state-writeback-truth-emission.html`（`doc-status=Open`）；报告侧补反向 `doc-refs`；`kb.index` 重建 21 个生成物；`kb.docmap --check` 认领链双向闭环。
- **2026-10-13 04:41** — 回 qB 源码取证状态节流（见「思考过程与决策」§4）；**确认成立**，值层前提被证否。
- **2026-10-13 05:38** — 按用户指令修正两处归因漂移、报告抬 26-10-13-0441 修订、B2 计划置 Superseded；本专题立档 + 切片；`kb.index` 重建、`kb.docmap --check` 通过（专题 `seed-state-writeback` 2 件·已完结：计划 Superseded ↔ 报告 Done）。用户指令「提交, 然后另立A系计划」——本轮回写随本专题入库，A 系计划随后另立。
