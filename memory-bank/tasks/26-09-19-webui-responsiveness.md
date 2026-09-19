# 26-09-19-webui-responsiveness — WEB UI 操作跟手性优化

**Status:** Pending (计划已交付, 待用户确认后实施)
**Started:** 2026-09-19
**Owner:** 主线
**Plan doc:** [docs/plans/26-09-19-1241-webui-responsiveness-plan.html](../../docs/plans/26-09-19-1241-webui-responsiveness-plan.html)
**Summary:** 用户报「WEBUI 操作不跟手」。链路剖面定位四类根因: ①命令要等主循环 main_tick(默认 2s)才被 drain ②waitCmd 首查前固定睡 500ms 且全程无即时反馈 ③每 2s 全量回传四视图 + 单个巨型 Vue 实例整树重渲染(种子页无虚拟化) ④bulkAct 逐目标 POST ⇒ 后端 N 次 qB 串行调用阻塞主循环。计划含 P0×5 / P1×5 / P2×4 共 14 项、三波次、验收口径与红线

## 原始请求

> 优化WEBUI操作不跟手的问题, 先列一个优化计划

## 思考过程与决策

- **决策 1(先拆链路再谈优化)**: 「不跟手」是主观描述, 直接猜优化点必然跑偏。先把一次「右键种子 → 暂停」
  拆成五段并逐段回源码找常量, 得到可度量剖面: 入队 1~5ms → **等主循环 main_tick 0~2s**(`_throttle` 无条件
  `time.sleep(main_tick)`) → qB 调用 10~300ms → **`waitCmd` 先睡 500ms 才首查** → 等下轮 sync + 下轮轮询 0~4s。
  合计 **0.5~6.5s 且中间零反馈**。
- **决策 2(主观延迟的主因是「沉默」不是「慢」)**: 因此收益最大的一项定为**乐观 UI**(P0-3), 而不是任何后端加速。
  后端加速(P0-1/2)只负责把真实状态对齐时间压到百毫秒级, 感知层由乐观 UI 兜住。
- **决策 3(排除视图重建这个假嫌疑)**: TASK017 已实测 200/1000/3000 种子重建四视图 = 4.97/25.22/79.36ms
  (占 tick 预算 ≤3.97%)。真开销在**传输 + 渲染**: 四视图每轮全量回传、单 Vue 实例整树重渲染、
  种子页无虚拟化、`updated()` 每次 `getBoundingClientRect` 强制布局。故 P1 全部打在传输与渲染侧。
- **决策 4(P0-1 设计 v2: 唤醒只触发「消费命令」, 不触发 tick)**: 初版设想「投递即跑下一轮」被自己否定 ——
  它会连坐三处: ①`max_tasks_per_tick` 承载的**速率语义**(默认 20 任务 / 2s = 10 任务/秒)失效;
  ②`_build_shows_view` / `search_torrents` 会**自投递** `build_search_index`(单轮 500 次文件 API),
  形成「唤醒 → drain → tick → 又投递 → 立刻再唤醒」的**自激循环**, 中间没有 main_tick 兜底;
  ③每 tick 预算(qB sync ×1、tracker 请求 ×5)被摊薄。
  改法: 命令线与 tick 线解耦 + 自投递命令不唤醒(白名单) + 汇报确认检查自带最小间隔。
  ⚠ 本次是**用户一句追问**问出了整个 P0 里唯一可能引发事故的点 —— 计划在写完后仍要接受"改频率类"质疑。
- **决策 6(否决「主循环 50ms」方案, 见附录 A1)**: 用户提出"主循环 50ms / 任务仍 2s(=50ms×40) / 状态刷新 50ms"。
  实测(helpers 替身, 纯 CPU 不含 qB 往返 ⇒ 下界): 单轮 `_refresh_torrents` + `rebuild_views` =
  200 种子 3.85ms / 1000 种子 18.65ms / **3000 种子 61.43ms(>50ms 预算)**。三条硬否决:
  ①3000 种子单轮就超预算 ⇒ 循环退化为无间隔连续跑(越忙越忙的正反馈); ②空闲成本 ×40(0.7% → 29% 核, 且永久);
  ③每 tick 预算 ×40(qB sync 0.5→20/s、tracker 2.5→100/s、搜索索引 250→10000 文件 API/s、任务吞吐 10→400/s)。
  **收益侧为 0**: 命令延迟 wake 事件已给 ≈0ms; 状态可见延迟被前端 `pollSec=2s` 截断 —— 50ms 只是把瓶颈从后端搬到前端。
  替代: **P0-5 命令执行后立即同步一次**(单次 14.52ms @3000, 按操作次数计费) + 乐观 UI; 彻底去 2s 下限走 SSE。
- **决策 5(批量合单排在 P0)**: 后端已有 `/api/torrents/bulk`(单 qB 调用 + 聚合回执)而前端没用,
  100 目标 = 100 次串行 qB 调用阻塞主循环。这是"点批量后界面卡住"的真因, 不是优化而是纠错。

### 诊断要点(证据, 行号随改动漂移)

- 等节拍: `qbmanager.py` 主循环顶部 `_drain_web_commands()`, 节流 `_throttle` 无条件 `time.sleep(main_tick)`。
- 回执首查: `app.js` 的 `waitCmd()` 循环体第一行 `await sleep(500)`。
- 全量回传: `web_view.py` 的 `ensure_group_state()` 四视图同门控全量回; 前端 `refresh()` 整表替换。
- 渲染: 单 Vue 实例; `prism/index.html` 种子页 `v-for filteredTorrents` 无虚拟化;
  `updated()` → `_syncHeadHeight()` 内含 `getBoundingClientRect`。
- 批量: `app.js` 的 `bulkAct()` 逐目标 POST; `web.py` 的 `api_t_bulk` / `_cmd_bulk_torrents` 未被 pause/resume/recheck 使用。
- 最坏情形: `qbclient._new_client()` 未设超时 ⇒ qB 假死时命令/抽屉请求无限挂起。

## 实现计划

| # | 档 | 动作 | 文件 |
|---|---|---|---|
| P0-0 | P0 | 埋点: 命令三段时间戳 + 前端渲染耗时采样 | web_commands.py / app.js |
| P0-1 | P0 | 唤醒只触发命令消费(v2), tick 频率不变 | qbmanager.py / web.py |
| P0-2 | P0 | waitCmd 首查 0ms → 150/300/500ms 退避 | app.js |
| P0-3 | P0 | 乐观 UI: 白名单动作点击即变 + pending + 失败回滚 | app.js / 双 UI 模板 |
| P0-4 | P0 | 批量动作改走 `/api/torrents/bulk` | app.js |
| P0-5 | P0 | 命令执行后补一次**完整** `_refresh_torrents()`（按次计费，替代 50ms 提频） | web_commands.py / qbmanager.py |
| P1-1 | P1 | `/api/state?view=` 只回传当前视图 | web.py / web_view.py / app.js |
| P1-2 | P1 | 行窗口化(种子页 + 展开成员行) | app.js / 双 UI 模板 / CSS |
| P1-3 | P1 | `updated()` 去布局抖动(ResizeObserver + rAF) | app.js |
| P1-4 | P1 | 抽屉轮放宽 3s→5s + 服务端 1~2s 只读缓存 | app.js / web.py |
| P1-5 | P1 | qB 客户端加请求超时 | qbclient.py |
| P2-1~4 | P2 | 行组件化 / 增量 patch / SSE 推送 / SIMPLE_RESPONSES 评估 | 选做 |

## 子任务状态表

| 子任务 | 状态 | 备注 |
|---|---|---|
| 链路剖面诊断 | ✅ | 五段拆分 + 逐段源码证据 |
| 计划文档交付 | ✅ | `docs/plans/26-09-19-1241-webui-responsiveness-plan.html`(Native HTML) |
| P0-1 设计评审(用户追问) | ✅ | 发现自激循环风险, 降级为 v2 解耦方案, 已回写计划 + pitfalls |
| P0-0 ~ P0-5 实施(波次一) | ✅ | `10e06a8`, 1046 passed |
| P1-5 / P1-1 / P1-4 / P1-3(波次二) | ✅ | `5d1e52c`, 1049 passed |
| P1-2 行窗口化(波次三) | ✅ | 已入库 `366092d` |
| 浏览器双 UI 冒烟 | ✅ | `scripts/ui_harness.py` + `ui_smoke.cjs`, 28 项 0 失败 |
| 放宽前端轮询(按种子量分档) | ✅ | 1.5s / 2s / 3s 三档, 实测定档 |

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
- 2026-09-19 1x:xx — **攻破"Windows 上没法做浏览器冒烟"这个长期阻塞点**：确认本机有可用 Node +
  chromium 缓存，写了 `scripts/ui_harness.py`(真 `create_app` + 真 `QbManager` + `FakeClient` +
  合成种子 + 命令泵；`--torrents/--groups/--port/--cmd-result ok|error|hang`) 与
  `scripts/ui_smoke.cjs`(Playwright，prism/atlas 各若干项 + 内置 A/B 基准)。**28 项断言 0 失败**，
  终于把单测覆盖不到的交互验掉了：P0-3 乐观 + 失败回滚 / P1-1 视图切换 / P1-3 无逐帧强制布局 /
  P1-2 窗口化。踩坑 4 条已入 pitfalls：`playwright@1.63`↔chromium-1243 与本机 1234 不匹配(装
  `playwright-core@1.62` + 必须 CJS)、Vue 3.5.13 根实例走 `#app._vnode.component.proxy`、
  桩服务命令队列是 **2 元组** `(cmd, body)`、`taskkill //F //PID` 在 Git Bash 下无效。
- 2026-09-19 1x:xx — **波次三实施完成（P1-2 行窗口化）**：种子页 / 分组页 / 展开成员行三层窗口，
  `ROW_WIN_MIN=200` + `OVERSCAN=10` + `GAP=6` + `EST_H` 兜底；**逐行测高 + 前缀和 + 二分**
  （真实数据行高不齐：2179 行 43.7px + 821 行 65.4px，等高假设会漂 218px ⇒ 滚到底够不着）；
  测高用 `getBoundingClientRect().height`（`offsetHeight` 取整 ×3000 漂 ~1200px）；
  上下 `.row-pad` 占位保持"每行渲染完整单元格序列"，不破坏 `:nth-child` 列对齐与 `data-table`；
  有 `expandedKey` 时 group 窗口退避回全量（成员行插队会打断边界）。
  顺手拆掉 `filteredTorrents` 里的 `{ ...r, hit }` 复制 —— 74 字段 × 3000 条 = 22 万次响应式
  `get` 陷阱，**单这一句 68ms**，改由模板现问 `isHit(m)`。
  **实测（3000 种子，1440×900，A/B 同进程 3 轮）**：DOM 行 3000 → **26**；滚动总高逐像素相同
  （167043 → 167043）且末行可达；整轮 refresh **1675 → 309ms（prism）/ 1780 → 301ms（atlas）**；
  主线程长任务 **240~350ms/轮 → 0**；`filteredTorrents` 重算 115ms → **5ms**。
  唯一代价：首次切视图仍 ~2.08s（要先全量渲染一帧测高），刻意接受。
  **测试 1049 passed 不变**，覆盖 92% 不变（含静态前端守卫 `test_frontend_static_bundle_health`）。
- 2026-09-19 1x:xx — **波次三已入库 `366092d`**（Gitee `5d1e52c..366092d` 与 GitHub `4cf7a67..366092d`
  本次**均推送成功**）。知识库回写完成：pitfalls 新增「P1-2 行窗口化」与「Windows 上跑真浏览器冒烟」
  两条、testing.md 记基线不变的原因与冒烟用法、systemPatterns.md 新增「WEB UI 前端渲染与响应性」节、
  progress.md 立三波次总条目、activeContext 清掉已解除的卡点。
- 2026-09-19 1x:xx — **P1 全部落地 ⇒ 最后一步: 前端轮询按种子量分档**（计划里唯一排在 P1 之后的项，
  因为"降轮询间隔"会**放大**全量回传 + 整树重渲染，顺序错了会加剧不跟手）。
  档位是**实测**定的不是拍的 —— 用桩服务 A/B 量出窗口化后单轮 refresh 的真实耗时：
  **800 种子 ~120ms / 1000 种子 143ms / 3000 种子 353ms / 5000 种子 ~550ms**，再按"主线程占用率
  ≈15%"反推间隔 ⇒ **≤1000 → 1.5s / 1000~3000 → 2s / >3000 → 3s**（占用率 10% / 15% / 17%）。
  两条边界: ①**下界 1.5s = 服务端 `sync_interval`** —— 后端每 1.5s 才刷一次数据，再快只是多拿一次
  "版本未变"的空响应; ②仍然是**恒定间隔**，不做"无变化退避"（那个曾把行数据新鲜度卖掉）。
  实现: `pollSec` 数据字段退役（避免死字段），新增 computed `basePollMs()`，`currentPollMs()`
  的失败退避改以它为基数; 顶栏 `pollLabel` 因此真正自适应。冒烟新增断言
  「轮询间隔按种子量分档」⇒ **28 → 30 项，0 失败**，三档逐个实测通过（800→1500ms / 3000→2000ms / 5000→3000ms）。
  **下一步**: 真机走查（真实 qB 数据下观感）→ P2 选做（行组件化 / 增量 patch / SSE）。
