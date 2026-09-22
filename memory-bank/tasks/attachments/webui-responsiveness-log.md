# 操作跟手性优化 · 较早的进度日志

> 摘要: `26-09-19-webui-responsiveness` 档案里**较早**的进度日志条目 —— 档案本体保留最近的部分。
> 触发: 跟手性, 进度日志, 历史条目, 三波次

> 迁移说明(2026-09-22 W7 `tasks/` 消肿): 原在 `../26-09-19-webui-responsiveness.md`, 因该档案总量超 24 KB 而体量集中在
> `## 进度日志`(18,522 字符)⇒ 把较早条目移到这里, **内容逐字未改**。

## 进度日志

- 2026-09-19 12:41 — 完成链路剖面诊断, 交付计划 `docs/plans/26-09-19-1241-webui-responsiveness-plan.html`
  (Native HTML 单文件, 冷峻技术方向; 基线按 testing.md 的 1041 passed); 立档。
- 2026-09-19 12:5x — 用户追问「命令即时唤醒会不会让 `max_tasks_per_tick` 语义失效」。核查 `taskqueue._pop_due`
  (per-call 预算)与两处自投递 `build_search_index`(web_view.py:513 / :699)后确认**会**, 且最坏形态是自激循环。
  P0-1 降级为 v2: 唤醒只触发命令消费; 加自投递命令白名单与 tick 频率不变量用例; 计划文档「红线」与
  「验收口径」同步补写; 新增 pitfalls 条目。**未动任何 src 代码。**
- 2026-09-19 13:0x — 用户改思路提出「主循环 50ms / 任务仍 2s / 状态刷新 50ms」。实测单轮成本后**否决**
  (3000 种子单轮 61.43ms 已超 50ms 预算; 空闲成本 ×40; 每 tick 预算 ×40; 收益被前端 2s 轮询截断)。
  改为 **P0-5: 命令执行后补一次刷新**(按次计费)。计划新增附录 A1、P0-5 条目、红线第 4 条;
  实测数字与判据入 pitfalls。**仍未动 src 代码。**
- 2026-09-19 13:2x — 用户追问「单独调 apply_sync 那新增/删除事件怎么处理」。核查 `store.apply_sync`(store.py:81)
  只更新 `by_hash` + `server_state`, 分组/任务/事件/搜索索引都不管 ⇒ **单独调用会留下半刷新态**
  (added 不建任务不归组、removed 丢弃导致 `on_torrent_deleted` 不触发且 `store.groups` 残留 hash、
  快照不推进导致事件时机错位)。**P0-5 修订为必须调完整 `_refresh_torrents()`**(天然幂等: 事件由快照 diff 消费一次),
  触发点改到 `_drain_web_commands()` **整批结束后一次**, 门控加"程序暂停不补 / dry_run 不补 / 白名单命令",
  并列入 5 条幂等红绿验收。备选 B: 改拉前下一轮 tick(需最小间隔下限)。已回写计划 + pitfalls。
- 2026-09-19 13:2x — 用户要求"重新梳理方案, 横向对比"。计划新增 **第 02 节「方案全景与横向对比」**:
  把 14 个候选方案按「①感知 ②命令 ③真实状态 ④规模」四层归类, 逐项对比 命令延迟 / 真实状态可见 / 成本 /
  语义风险 / 结论, 并给出「组合效果」表(现状 → B+H+I → +E/F+J → +P)。**核心结论: ③层收益被前端
  pollSec=2s 封顶, 这正是 C(50ms 主循环)被否决的根本原因。** 原 02~08 节顺延为 03~09。
- 2026-09-19 13:4x — 用户提第三种架构「刷新 50ms / 视图重建 1s / 任务 2s」。评估: **技术可行**(区别于 A1 的整轮 50ms ——
  单轮只剩刷新 14.52ms@3000 = 预算 29%; 3000 种子合计 ≈33.7% 核), 但**必须补两个门控**(漏了就出事):
  `_build_search_index` 归 2s+(否则 10000 次文件 API/秒)、`refresh_error_reasons` 归 2s(否则 100 次 tracker/秒);
  两处收益打折(重建 1s vs 前端 pollSec 2s ⇒ 一半白做; 状态 50ms 用户侧看不到) + 两个隐藏成本
  (qB 侧 sync 20/s 的 O(N) diff 打在 qB 进程上; GIL 争用可能"后台更快前台更卡")。
  **落地建议: 挂到已有 Web 活跃门控(`_web_last_seen`/`WEB_VIEW_TTL`)做成"快档", 取值 250~500ms(不给 50ms), 默认关闭。**
  计划新增附录 A2 + 目录项; 五项归档清单与判别法入 pitfalls; 守卫 8 passed。仍未动 src。
- 2026-09-19 13:5x — 用户接受"50ms 太快", 定档 **刷新 1s / WEB UI 1.5s / 任务 2s**(依据: qB 自带 WebUI 1500ms 一轮)。
  评估: **后端几乎免费**(3000 种子 ≈4.6% 核, 比现状 3.1% 只多 1.5 点; qB sync 1/s 与 qB 自身 0.67/s 同量级) ⇒ 可接受。
  **两点提醒**: ①`rebuild_views` **不需要单独配节拍** —— `ensure_group_state` 已是"请求驱动 + 脏门控",
  视图重建频率天然 = 前端轮询频率, 另配定时器只会白建; ②**风险全在前端** —— pollSec 2s→1.5s 把"全量回传 + 整树重渲染"
  频率提高 33%, 未做 P1-1/P1-2 前会**加剧**不跟手 ⇒ 顺序必须是 P0 → P0-0 埋点 → P1-1/P1-2 → 最后动 pollSec。
  取值建议成整数倍(1.5/1.5 推荐, 或 1/2)。计划新增附录 A3; 判据入 pitfalls; 守卫 8 passed。仍未动 src。
- 2026-09-19 14:xx — **用户确认「按推荐取值, 开始实施」⇒ 波次一落地(首次动 src)**。定档 **刷新 1.5s / 轮询 1.5s
  (前端 pollSec 默认仍 2s, 待 P1 后再降) / 任务 2s**。已实施:
  1. **分层节拍**: 新增 `sync_interval`(默认 1.5s, 已进 models / validate / loaders / schema / impact=L0);
     主循环拆 `_sync_line`(刷新+视图)与 `_task_line`(tracker 预取+run_due+搜索索引), `_tick` 保留"完整一轮"语义。
     `refresh_error_reasons` 与 `_build_search_index` **仍跟 main_tick, 不跟快档**。等待用 `min(两线到期时间)`。
  2. **P0-1 命令唤醒**: `QbManager.wake()` + `_wake_event`; web `_enqueue` 投递后唤醒(**自投递命令除外**,
     新增 `SELF_POSTED_COMMANDS` 并有静态反向守卫); ui.py 停止路径一并 `manager.wake()` 使退出立即生效;
     等待原语换成 `_wait_next`(**以唤醒为主** + 分段非阻塞查停止)。
  3. **P0-5 命令后补刷新**: `_drain_web_commands()` 返回 changed(白名单 `RESYNC_COMMANDS`), 循环里
     `sync_due |= changed and not dry_run` ⇒ 整批只补一次完整 `_refresh_torrents()`(不是 `apply_sync`)。
  4. **P0-0 埋点**: 回执带 `wait_ms`/`exec_ms`(下划线前缀键为元数据, 不传 handler); 前端 `cmdStats` +
     单轮 `renderMs`(>50ms 留痕, 是 P1 行窗口化的判据)。
  5. **P0-2 首查退避**: `waitCmd` 改先查后退避(0→150→300→500 封顶), 强制汇报走宽松曲线(500→1000)。
  6. **P0-3 乐观 UI**: `applyOptimistic/resolveOptimistic/reapplyPending` + `isPending`(3s 回落真值, 失败立即回滚),
     白名单只做 pause/resume; 双 UI 模板加 `is-pending` 类 + 半透明样式。
  7. **P0-4 批量合单**: `bulkAct` 与 `actEpisode` 的 pause/resume/recheck 改单条 `/api/torrents/bulk`
     (后端已支持 keys+hashes 混合、一次 qB 调用), reannounce 仍逐目标(tracker 确认需逐个跟踪)。
  **测试**: 新增 5 项, 改写 3 项既有主循环守卫的判据(阻塞原语从 `time.sleep` → `_wait_next`;
  `test_main_loop_throttled_by_main_tick` 需把 sync_interval 一并设 0.2)。
  **实测基线 1041 → 1046 passed (Windows) / Linux WSL 1044 + 2 skipped**, WSL 复跑 5 次无抖动; 覆盖率总 92% 不变。
  坑(4 条)已入 pitfalls: 多事件等待顺序不能反 / 分层不能退化成单一 cadence 内部门控 / 改主循环会静默废掉
  节流守卫(表现为挂死) / yapf 会重排文件里本来就超宽的旧行。
  **已入库 `10e06a8`**(提交前落后主线 11 个提交 ⇒ 先 commit 再 rebase; 冲突 2 处均在知识库追加型文档, 用并集解;
  rebase 后重跑 1046 passed 与 rebase 前一致)。**Gitee `76e3623..10e06a8` 与 GitHub `ccedce8..10e06a8` 均推送成功。**
  **下一步**: 浏览器双 UI 冒烟(尤其 P0-3 的 pending 半透明与失败回滚) → 波次二(P1-1 按视图回传 / P1-2 行窗口化)。
- 2026-09-19 15:xx — **波次二实施完成(P1-5 / P1-1 / P1-4 / P1-3), 未提交**：
  1. **P1-5 qB 客户端请求超时**：`_new_client` 加 `REQUESTS_ARGS={"timeout": (3, 10)}`。此前**完全没设
     超时** ⇒ qB 假死时请求无限期挂起, 主循环线程被占住连重连退避都跑不起来("点一下界面再也不动")。
     读超时取 10s 宽松值：/files 在几千文件的种子上响应体很大, 截窄会误判成断连。
  2. **P1-1 按视图回传**：`/api/state?view=group|torrent|show` 只回该视图数组（`VIEW_ARRAYS`；
     group 视图要同时回 groups+singles，未归组单种子是同页兜底行）。未知/缺省 view ⇒ 四份全回（保守默认）。
     前端：赋值改"键不存在则保留原引用"（否则另两个视图每轮被抹空）；切视图置空 lastRid 并立即 refresh。
  3. **P1-4 只读端点短缓存**：files/trackers(2s)、peers(1s)、categories/tags(2s) 加 TTL 缓存，
     失效靠 `manager._web_write_seq`（**断连优先于缓存**、**写后失效** 两条硬约束，见 pitfalls）；
     前端抽屉轮询 3s → 5s。
  4. **P1-3 去布局抖动**：`updated()` 不再每次调 `_syncHeadHeight()`（getBoundingClientRect = 强制同步布局），
     改 ResizeObserver 观察 `.sticky-head` + rAF 合并写入；无 ResizeObserver 时降级为原行为。
  **测试 1046 → 1049 passed**（Windows）/ WSL 1047 + 2 skipped；覆盖 92% 不变。
  **下一步**：波次三 = P1-2 行窗口化（改动面最大，需单独提 + 双 UI 截图核对）；
  P1 全部落地后再按种子量放宽前端 `pollSec`（现在仍是 2s）。**P0-3 乐观 UI 仍待浏览器冒烟**。
