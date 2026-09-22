# 路线图 (规划中 + 已定案口径)

> 摘要: 尚未实现的功能线、仍敞着的设计取舍, 以及「已定案、别改回去」的方向性口径。
> 触发: 规划中, 下一步做什么, 路线图, 已定案口径, 别改回去, 未实现

## 规划中 (🚧, 尚未实现)

(以下 WEB UI 核心已于 2026-09-13 实现, 见 productContext.md/modules.md; **2026-09-14 已补图形化配置编辑** —— 设置页每项配置均可增删改, 含站点/规则集(16 条件 + 12 动作)/限速曲线的结构化编辑与只读 YAML 预览, 直接编辑模式已移除; 剩余: WebSocket 推送/多用户)

### 真机 qB 语料抓取 / 脱敏 / 离线回放 (2026-09-21, **W0–W5 已实施, W6 未开工**)

> 计划 [docs/plans/26-09-21-0024-qb-corpus-capture-replay-plan.html](../docs/plans/26-09-21-0024-qb-corpus-capture-replay-plan.html) (v3 已拍板) · 任务档案 [tasks/26-09-21-qb-corpus-capture-replay.md](tasks/26-09-21-qb-corpus-capture-replay.md)

把 `scripts/sim_qb.py` 的种子来源从"人造合成"换成"真机 qB 抓取 + 脱敏 + 离线回放"; 合成档保留为对照。
语料 = **一条原始流**(首帧即 T0 / 末帧必是一份全量)+ 流里没有的按 hash 元数据(files / trackers)+ 真值分组(groups.json)。

- ✅ **W0 真机实测已出数(7 项)**: 全量抓取 174 请求 **207 ms**; 第二 session **不干扰**增量流(各自独立 rid);
  100 ms 采样负载**判否不成立**(rtt max 2.86 ms, 0 次超 100 ms)⇒ perf 档保留; 磁盘探测 11457 文件 1303 ms;
  全局限速两来源单位一致。**真实语料画像**: 87 种子 → 63 组, 11457 文件里 9673 缺(全在 R: 盘)⇒ D4 天然样本充足。
  ⚠ **一处推翻计划前提**: 命令后 `maindata` 反映延迟 mean 733 ms, 但 **Δ(info − maindata) = +1 ms** ⇒
  issue 2145 那条"info 比 maindata 新"在真机上**不成立**, 真实滞后是 qB 命令处理延迟(两端共享)。
  处置: 拆成 `--command-latency-ms`(默认 750)+ `--maindata-lag-ms`(默认 0)两个旋钮, 默认档忠实复现真机,
  同时保留计划要求的红验。❓ R 盘(虚拟盘)持久性待用户确认。
- ✅ **W1/W2 已落地**: 新增 `scripts/qb_capture.py`(capture / snapshot / record / self-test)+ `tests/test_qb_capture.py`(12 条);
  `src/auto_qb/mixins/grouping.py` 抽出 `group_key_of()`(**本计划唯一一处 src/ 改动**, 纯抽取零行为变更 + 守阵 1 条)。
  真机端到端跑通, **6 项自检全 PASS**(字段完整性 / 映射单射 / **分组守恒** / 首尾闭合 / 流级脱敏一致 / 无凭据泄漏),
  检查点对齐率 1.0000, warnings 0; 语料确认**真脱敏**(名字/路径/tags/tracker 均伪名化, 路径用 `<FSROOT>` 占位符)。
  **反向对照(红验)通过**; 测试基线 1098 → **1111 passed**。
- ✅ **W3 已落地**: `scripts/sim_fsmock.py`(进程内 FS mock: 按路径前缀限定 / 剥 `\\?\` + 大小写不敏感 /
  时间源归播放器)+ `sim_qb.py` 语料档(`--source=corpus:<dir>` 等 7 个新参数)+ 补齐
  `sync/torrentPeers` / `torrents/export` / `torrents/pieceHashes` / `_fsmock/state` 四个路由
  + `sim_run.py` 透传与环境变量注入。**端到端 `verdict OK`**(87 种子 / 63 组 / 0 物化文件, 漂移 0.578s, 0 traceback)。
  守阵: `CORPUS.fs_mock_coverage` 静态守阵 + 红验、两层状态模型红验。测试 1111 → **1128 passed**。
  顺带修掉两个真 bug: ①`disk.json.gz` 内层相对路径未脱敏(隐私 P0)②`disk_table()` 没读 disk.json
  ⇒ 抹掉 9673 个缺失样本(D4 假绿)。
- ✅ **W4 已落地**: 录播游标(可交付时刻 = 各帧 `dt_ms` 累积和, 按墙钟 × `--replay-speed` 推进)+ 窗口合并
  + `--latency-mode`(recorded / p50 / p95 / const)+ `fs_delta` 按 t_seq 叠到 mock 磁盘状态。端到端 3× 倍速:
  14/14 帧吐完、游标滞后 1402 ms(预算 9144 ms); 4 条 `CORPUS.*` 判据全 PASS。测试 1128 → **1133 passed**。
- ✅ **W5 已落地**: 头号判据 `CORPUS.group_exact`(走 auto-qb `GET /api/state?view=group` 取它**实际**分的组,
  与真值分组逐组逐 hash 比 —— **实测 63/63 组、未分出 0、多分出 0**, 静态与 3× 时间轴都绿;
  三道反向对照红验: 串组 / 拆组 / 缺组), `CORPUS.maindata_lag_modeled`(滞后全 0 则转红),
  基线两套分离(`corpus.*` vs 裸 id, 合成档另存 `…synthetic.json`)+ `sim_baseline.py --corpus`,
  `docs/sim-client-test-howto.md` 第 7 节, **issue 26-09-20-2145 置 Fixed**。测试 1133 → **1137 passed**。
- ✅ **W6 已落地(真机走查闭环, 按计划 §11 收窄)**: 对 `activeContext.md`「待用户真机走查」清单
  (~15 条)做了**数据面 / 观感**分档。只有 2 条是数据面:
  · **视图重建范围收口**(种子速度是否随轮询刷新)→ **语料回放已闭环, 迁出清单**。实测: 2× 倍速时间轴回放下
    周期性拉 `GET /api/state?rid=-1&view=torrent`, 15 次相邻比对中 **5 次**观测到速度随回放推进而变化、
    流吐完后稳定 ⇒ 视图确实随轮询刷新(局限: 该版语料只有 1 个种子在动, 机制已证、幅度未证)。
  · **TASK015 错误种子原因** → **语料验不了, 仍需真机**: 该版语料 `error` 态 **0 条**, 走不到原因预取分支;
    要验需重抓一份含 error 态种子的语料。
  · 其余约 13 条(Console Hub / 跟手性 / 热路径体感 / TASK011-014 / 状态栏速度 / 今日流量 / 列设置 / 可用性列 …)
    是**前端观感**, 回放数据面测不到 ⇒ **明确标注"仍需真机目视, 不得计入闭环"**。
  语料计划 W0–W6 全部落地。
- ⬜ **残留**: 真机走查清单里约 13 条观感项待用户目视(不得计入闭环); TASK015 待含 error 态种子的语料。

### 规则系统
- 条件取反 (`!` / 非 logic) — `:ignore_case` 支持已完成 (2026-09-12, 见 08 TODO 段)
- tracker 分组 (规则按组筛选)

#### 事件触发(规则)规划 (2026-09-12 设计定论, 已实现)

**核心原则** — 区分"触发(瞬时)"与"结果(异步/状态式)"两种调度, 事件两者都要支持:

| 环节 | 触发方式 | 依据 |
|------|---------|------|
| 事件检测 + 事件规则动作入口 | 同步即时 (当拍快照, 不排队) | 事件是对瞬时状态转移的反应, 延后失真 |
| checking 动作的提交判断 (execute 决策链) | 同步即时 (随事件入口执行) | 判断"该不该校验"读瞬时状态 |
| checking 动作的结果轮询/组内等待 | 走队列 (现状 check / check-wait) | 轮询异步终态, 延后无害 |
| 校验成功后事件规则断点续跑 | 走队列 (`add_task(origin, keep_progress=True)`) | 复用现有 origin 恢复机制 |

**为事件造"可恢复 origin" (关键机制)**: 事件触发时 `_apply_event_rule` 传入真正的 `Task` 对象 (kind="rule-event", 一次性任务) 作 `ctx.task`, 而非 None。这样 `_execute_full_checking` 的 `origin = ctx.task` 就是该 rule-event 任务: 校验成功 → `on_success()` + `tq.add_task(origin, keep_progress=True)` → 断点保留 → 下 tick `_handle_event_rule` 从断点续跑事件后续动作; 失败/删除 → `add_task(origin)` 默认重置重走完整决策链 (删除由事件 handler 的删除守卫判死)。

**rule-event 任务的可恢复但一次性双重性质**: 它从不被 `run_due` 主动弹出 (事件分派时**不 add_task**, 避免被当周期任务弹掉/占 max_tasks 计数); 只在两条路径出现 — (A) 事件分派即时执行: `_apply_event_rule` 拿到 process 返回后持有 Task 对象作 origin, 不接 `_fast`; (B) 断点续跑: 轮询子任务 `add_task(origin, keep_progress=True)` 把它入 `_fast`, 下 tick `_handle_event_rule` 执行并从断点续跑后**返回 FINISHED 消亡** (恒不自我周期循环, 除非再遇 pending)。

**落地现状** (2026-09-12): 全部实现 — `Rule.trigger` 解析、`RuleContext.snapshot` 快照回退 + `torrent` 属性、`TRIGGER_VALUES` 四值、`_validate_trigger_action_compat` 白名单 (`DELETED_TRIGGER_ALLOWED_ACTIONS = {"print_torrent_details"}`)、`print_torrent_details` 动作、事件分派引擎 (`_dispatch_events`/`_apply_event_rule`/`_handle_event_rule`/`_rules_by_trigger`/`_torrent_event_rules`)、`_refresh_torrents` 分派点接线 + 删除前快照捕获 (`removed_snapshots`)、`taskqueue` rule-event kind 语义、`tests/test_trigger_events.py` (13 个测试, 覆盖四触发器/checking 断点续跑三态/混用/白名单/dry_run)。

**⚠️ 已修复的潜在缺陷 (2026-09-12)**: `_create_rule_task` 对非 interval 规则返回 `None`, 原 `_create_torrent_tasks` 直接 `tasks.append(...)` 并 `add_tasks` → 遇到 `trigger: on_*` 规则时 `add_task(None)` 会在 `None.resume_index` 处 AttributeError 崩溃。已修复: `_create_torrent_tasks` 过滤 None 条目后再入队。

**触发时机 × 动作白名单** (`_validate_trigger_action_compat`, config 阶段 fail-fast):

| trigger | 允许动作 | 特别说明 |
|---------|----------|---------|
| `interval` | 全部 12 | 现状 |
| `on_torrent_added` | 全部 12 含 checking | 事件入口 + origin 续跑 |
| `on_torrent_state_enum_changed` | 全部 12 含 checking | 事件入口 + origin 续跑 |
| `on_torrent_deleted` | **仅 `print_torrent_details`** | 删除后 store 无该种子, `ctx.torrent` 回退删除前快照副本; 需活种子的动作 (启停/校验/限速/移动/汇报) 都无意义 → 拒绝; 只读留档动作适用。**此即"唯一待确认"的答案**: 因新增 `print_torrent_details`, 原空集白名单放宽为只读动作集 |

**触发点接线** (`qbmanager._refresh_torrents`): 在 `store.refresh` 之后、自有动作之前、`update_state_snapshot` 之前的分派点同步执行各事件规则 (即时), 遇 checking 内部建 rule-event origin → pending → 轮询子任务走队列 → 结果恢复续跑。

**性能与副作用**: 事件分派同步执行拉长单 tick (数千种子大库 + 大量事件时, 与 grouping 缺文件扫描同模式, 已被接受); `max_tasks_per_tick` 只约束队列里的轮询/恢复任务, 不约束事件即时分派。

### 其它功能
- 通知多渠道: webhook/邮件/Telegram 等(channels 配置结构已按列表预留, 与 traffic_source 同款演进路径); Windows 自定义图标(当前快捷方式图标为 Python 解释器图标, AUMID 来源名已实现); toast 交互按钮(需 winsdk)
- 插件系统: 直接支持自定义 Python plugin
- 根据流量接入更多数据源 (traffic_source 当前仅 traffic_monitor 单源, 代码已按列表预留)
- 与 PTD-cli 合作: 自动分析 HR 标签 / 暂停低分享率非免费种子 (想法.md 标注"需可行性验证")
