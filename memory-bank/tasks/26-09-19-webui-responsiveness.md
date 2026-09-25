# 26-09-19-webui-responsiveness — WEB UI 操作跟手性优化

**Status:** In Progress
**Started:** 2026-09-19
**Updated:** 2026-09-19
**Owner:** 主线
**Plan doc:** [memory-bank/plans/26-09-19-1241-webui-responsiveness-plan.html](../plans/26-09-19-1241-webui-responsiveness-plan.html)
**Review doc:** [memory-bank/plans/26-09-19-1745-webui-responsiveness-review.html](../plans/26-09-19-1745-webui-responsiveness-review.html)
**Summary:** 用户报「WEBUI 操作不跟手」。链路剖面定位四类根因(命令要等 main_tick / waitCmd 首查固定睡 500ms / 每 2s 全量回传四视图 + 整树重渲染 / bulkAct 逐目标串行阻塞主循环)。计划 14 项(P0×5 / P1×5 / P2×4)三波次 + 红线与验收口径。**P0/P1 十二项已全部落地并入库**(`10e06a8` `5d1e52c` `366092d` `d83ea61` `021d75a`), 另有计划外补做的前端轮询按种子量分档。**2026-09-19 对抗性复核**(见 Review doc): 架构判断成立、命令延迟实测 wait_ms=0/首查即命中; 但查出 6 个缺陷(1 高 2 中 3 低: 棱镜行窗口占位总高 +2973px / 乐观 UI 只覆盖种子行 / 写后失效无接线用例)+ 3 处文档漂移。**复核缺陷修复第 1 批(报表 1~4 + 8~9)已实施并入库 `04cbc8e`**: 行间距改运行时实测(棱镜 Δ +2973 → **0**)、冒烟改同帧「窗口化 vs 全量」对照(34 → **36 项 0 失败**)、补两条写序号接线断言(**红绿双验**)、回执/失效顺序调换、`sync_interval` 落实钳制、文档漂移清理、harness 限回环、`cmdStats` 接消费者; **基线 1049 → 1051 passed / cov 92%**。**第 2 批(报表 5 = BUG-3)亦已实施并入库 `04cbc8e`**: 开工先做真浏览器实证, 推翻报表对 BUG-3 证据②的判断 —— 组行颜色**本来就是乐观变化的**(取自 `_aggStatus(成员 kind)` 的 computed), 真正缺的只有 `is-pending`; 集行则确实完全没有乐观调用, 新增 `epState(e)` 按同一张优先级表现算。过程中又查出并修掉 3 个报表漏报的缺陷: **BUG-8(高)** 追剧页刷新后**永久空白**(`VIEW_ARRAYS["show"]` 只回 shows, 而成员索引是 groups+singles 拼的 ⇒ 索引空 ⇒ 0 行, 且 rid 已记住不会自愈)、**BUG-9(中)** 复制磁力 100% 失败(`magnet_uri` 只在平铺数组里而 `memberByHash` 的兜底分支永不生效)、**BUG-7(低)** 前端/后端两张状态优先级表有 2 种混合态结论相反。另修掉冒烟自身 3 处缺陷(恒真断言 / error 模式恒红 / `FakeTorrent` 缺 `to_dict()` 导致详情链路从未被覆盖); **基线 1051 → 1052 passed / cov 92%, 冒烟 46 项(ok) / 44 项(error) 0 失败**。**续查又拿掉一处热路径白跑**: 动手做报表 §08 第 6 项(响应体裁剪)前先量「一轮 refresh 花在哪」, 结果**否决了第 6 项** —— 字段裁剪是死路(占比最大的字段仅 6.3%, 80% 字节需要 74 个字段里的 52 个), 客户端 `JSON.parse` 只占 4.1 ms、网络 5 MiB 走 uvicorn 只要 1.6 ms; 真正的开销是 FastAPI 对**普通 dict 返回值**先跑一遍 `jsonable_encoder` 递归遍历整个响应体(3000 种子实测 **161 ms**, 占端点耗时 **85%**, 全程占 GIL)。改成 `return JSONResponse(content=payload)` 即被 `fastapi/routing.py` 的 `isinstance(raw_response, Response)` 短路: 服务端 `view=torrent` 189 → **23.5 ms**(8.0×), **前端整轮 refresh ~240 → ~85 ms**(整轮本就在等服务端), 输出字节零变化(新旧并排四份响应长度全同)。**基线 1052 → 1053 passed / cov 92%, 冒烟 46 项 0 失败**。剩报表 §08 第 7 项(节拍对齐, 需先拍板方向)与同类端点的同样改法
**Topics:** webui-responsiveness

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

### 实施后复核结论 (2026-09-19, 见 Review doc)

复核方式刻意不走"只读 diff": 起真 `create_app` + 3000 合成种子, 复跑 34 项浏览器冒烟(**34/0**),
再写三组计划从没量过的探针 —— ① 同页对比「窗口化 vs 关掉 `rowWin` 的全量」的 `scrollHeight` 与
真实 `gap`; ② 各 `view` 的 `/api/state` 字节数; ③ 直接读回执里的 `wait_ms`/`exec_ms`。

- **决策 7(结论: 架构判断成立, 缺陷在覆盖面与证据链)**: 12/12 项落地且落点与计划一致; 三个否决项
  (50ms 主循环 / 投递即跑 tick / 只调 apply_sync)的判据复核后**全部成立**。缺陷集中在"计划承诺的
  覆盖面"与"没人消费的埋点", 不在架构。
- **决策 8(行窗口的间距必须实测, 不能硬编码)**: `ROW_WIN_GAP = 6` 只对 atlas 成立 ——
  prism `.group-table{gap:5px}`、成员容器 `.detail` 是 block(gap=0)。实测 3000 行:
  `prism 窗口化 167043 vs 全量 164070 = +2973px`, `atlas 167071 vs 167071 = 0`。
  末行可达、无空白(占位与滚动解释共用同一套虚标尺 ⇒ 自洽), 属观感/一致性缺陷。
- **决策 9(冒烟断言的口径比断言本身更重要)**: 高度断言里的 `before` 是在 A/B 之后读的, 而 A/B 结束
  会把 `rowWin` 还原为 `true` ⇒ 两次比的都是窗口化高度, 天然测不到"占位算错"。这也是 BUG-1 逃逸的
  唯一原因, 同时说明提交信息里「滚动总高逐像素相同 (167043 → 167043)」是**两个窗口化值**。
- **决策 10(埋点不消费 = 埋点不存在)**: P0-0 链路是通的(后端两段耗时 → 回执 → 前端 `cmdStats`),
  但 `cmdStats` 全仓**只写不读** ⇒ 计划的"走查表"从未产出, 5 条量化验收只剩 3 条有数字,
  其中「响应体 ≤200KB」实测**未达成**(group 1.67MiB / torrent 4.31MiB —— 平铺数组本身就是全量里
  最大那份, 按视图切不掉它自己), 「单帧 ≤50ms」无任何数字。**下一轮立计划时必须给每条验收口径
  指派交付物(断言 / 报表字段 / 走查表), 否则等于没写。**
- **决策 11(安全面无需返工)**: 全局鉴权依赖覆盖新端点; 只读缓存的写入点在 `_require_torrent()`
  **之后**(伪造 hash 进不了缓存); 断连判定刻意先于缓存; 超时把"永久挂死"变"有界失败"。
  低危 3 条(harness 可绑 0.0.0.0 且免鉴权 / `_cached_read` 锁外调 `fn()` 惊群 + `>128` 整表 clear /
  缓存不被主循环自身写失效)已入 pitfalls, 非阻塞项。

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
| 计划文档交付 | ✅ | `memory-bank/plans/26-09-19-1241-webui-responsiveness-plan.html`(Native HTML) |
| P0-1 设计评审(用户追问) | ✅ | 发现自激循环风险, 降级为 v2 解耦方案, 已回写计划 + pitfalls |
| P0-0 ~ P0-5 实施(波次一) | ✅ | `10e06a8`, 1046 passed |
| P1-5 / P1-1 / P1-4 / P1-3(波次二) | ✅ | `5d1e52c`, 1049 passed |
| P1-2 行窗口化(波次三) | ✅ | 已入库 `366092d` |
| 浏览器双 UI 冒烟 | ✅ | `scripts/ui_harness.py` + `ui_smoke.cjs`, 28 项 0 失败 |
| 放宽前端轮询(按种子量分档) | ✅ | 1.5s / 2s / 3s 三档, 实测定档 |
| 实施后对抗性复核(报表) | ✅ | `memory-bank/plans/26-09-19-1745-webui-responsiveness-review.html`; 34 项冒烟复跑 34/0, 另加三组自写探针 |
| 复核缺陷修复 · 第 1 批(报表 1~4 + 8~9) | ✅ | **已实施, 已入库 `04cbc8e`**; 1051 passed / cov 92%; 冒烟 36 项 0 失败; 详见下条进度日志 |
| 复核缺陷修复 · 第 2 批(报表 5 = BUG-3 组行/集行乐观) | ✅ | **已实施, 已入库 `04cbc8e`**; 1052 passed / cov 92%; 冒烟 46 项(ok) / 44 项(error) 0 失败。实证推翻报表对 BUG-3 证据②的判断(组行颜色本来就变, 只缺 `is-pending`) |
| 复核过程中新发现的缺陷(BUG-7 / BUG-8 / BUG-9) | ✅ | BUG-8 追剧页刷新后永久空白(**高**, 报表漏报的功能性回归) / BUG-9 复制磁力恒失败(中) / BUG-7 状态优先级表两页不一致(低); 均已修 + 补机械守阵 |
| 冒烟脚本自身缺陷(恒真断言 / error 模式恒红 / 详情端点从未覆盖) | ✅ | 三条全修; 详情端点 500 的根因是 `FakeTorrent` 缺 `to_dict()`(桩保真度) |
| 续查 · 热路径跳过 FastAPI `jsonable_encoder`(报表 §11) | ✅ | **已实施, 已入库 `04cbc8e`**; 服务端 `view=torrent` 189 → **23.5 ms**(8.0×), 前端整轮 refresh ~240 → **~85 ms**; 输出字节零变化; 1053 passed / 冒烟 46 项 0 失败 |
| 复核缺陷修复 · 第 3 批(报表 7 节拍对齐) | ⬜ | 需先拍板(让轮询跟上快档 vs 给快照刷新加 Web 活跃门控) |
| 同类端点同样改法(`/api/torrents/{hash}/files`、`/api/search` 等) | ⬜ | 收益取决于响应体大小; 用户触发型, 不在 1.5~3s 轮询路径上, 故未纳入本批 |
| 验收口径补齐(≤200KB 未达成 / 单帧 ≤50ms 无数字) | ⬜ | 报表 5.1 / 5.2; 建议先落 P2-2 增量回传或按可见列裁剪字段 |

## 进度日志

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
- 2026-09-19 1x:xx — **补上 P0-4 的浏览器验证**（此前 P0-1~P0-3 都有实证，唯独合单没有）: 冒烟新增
  两条断言 —— ①选 60 个目标点暂停 ⇒ **恰好 1 条** `POST /api/torrents/bulk` 且**零条**逐目标
  `/api/torrents/{hash}/pause`（靠 `page.on("request")` 数，单测写不出来）; ②乐观值要一次性贴到
  **全部**目标（pendingOps 60/60），不是只贴第一行。**红绿双验过**: 把 `bulkAct` 的合单分支短路成
  `if (false && …)` ⇒ 断言变红并如实报出 "bulk 0 次 / 逐目标 60 次"（正是优化前的形态），改回即绿。
  冒烟 **30 → 34 项，0 失败**。至此 P0 五项与 P1 五项**全部有浏览器实证并已入库**，
  计划里只剩真机走查与 P2 选做。
- 2026-09-19 17:45 — **实施后对抗性复核(用户: "评估上轮计划本身以及实施情况, 重点在 BUG/安全/性能")**，
  交付报表 `memory-bank/plans/26-09-19-1745-webui-responsiveness-review.html`（Native HTML 单文件，暖纸 + 赭石方向）。
  复核动作与结论：
  1. **复跑而非引用**: 起 `ui_harness.py`(3000 合成种子) 跑完整冒烟 = **34 项 0 失败**（与提交自述一致）；
     单测默认 basetemp 下 **1049 passed / cov 92%**（与 testing.md 一致）。
  2. **BUG-1（高）行窗口间距硬编码**：`ROW_WIN_GAP=6` 只对 atlas 成立（prism `gap:5px`、`.detail` 块级 gap=0）。
     同页 A/B 实测 `prism 167043(窗口化) vs 164070(全量) = +2973px`；`atlas 0`。末行可达无空白 ⇒ 观感缺陷。
     冒烟测不到的根因是断言口径（`before` 在 A/B 后读 ⇒ 窗口化 vs 窗口化），已入 pitfalls。
  3. **BUG-3（中）乐观 UI 只覆盖种子行**：整组只补丁成员（组行 `s-<g.status.primary>` 与 `is-pending` 都不变，
     不展开就没反馈）；`actEpisode`（整集/整剧）**完全没有**乐观调用 —— 而用户最初的抱怨场景正是辅种页。
  4. **TEST-1（中）P1-4「写后失效」只测机制不测接线**：全仓无一条断言 `_drain_web_commands` 会自增
     `_web_write_seq`（测试里是手动 `+= 1`）⇒ 字段改名/挪走自增 ⇒ 缓存永不失效而套件全绿。
  5. **性能实测（计划里没有的数字）**：`/api/state` 全量 6.11MiB / group 1.67MiB(27%) / **torrent 4.31MiB(71%)**
     / show 132KiB ⇒ 计划的 ≤200KB 验收在种子页差 22 倍；命令延迟 `wait_ms=0 / exec_ms=1`、wall ≤34ms、
     首查即命中（P0-1/P0-2 双证）；A/B 稳态 refresh 1384→244ms，但**提交里「长任务 → 0」未重现**（181→147ms）。
  6. **DOC-1（中）**：`app.js:161-167` 头部注释仍是被推翻的第一稿口径（「行高必须齐 / 差异>2px 关闭窗口化」），
     而全仓无任何 `rowWin=false` 写点（两处引用都是读）。
  7. **安全无新增漏洞**（见决策 11）；低危 3 条入 pitfalls。
  8. **计划本身评级 A−**：先量化 / 否决带判据 / 红线被遵守 / 波次切分正确；扣分在"验收口径没配交付物"
     与"P0-3 白名单收窄未回写计划"。
  **未动任何 src 代码**；报表 + 知识库回写是本次全部改动。**下一步**：按报表 08 节修复（1~4 与 8 可合一个提交）。

- 2026-09-19 18:0x — **复核缺陷修复 · 第 1 批(报表 08 节的 1~4 + 8~9)已实施**（未提交）。逐项与实测：
  1. **BUG-1/BUG-2 行间距改为运行时实测**：新增 `_winGapOf(kind)` / `_winGapFor(kind)`（读
     `getComputedStyle(container).rowGap`，块级容器 `normal`→0，三层各存一份），删掉 `ROW_WIN_GAP=6`。
     **冒烟新增断言当场抓到自己第一版的坑**：`_winGap` 只在 `_measureRowH` 里读一次，而它对三个 kind 都跑
     —— 在分组页问种子页的容器拿到 null ⇒ 把种子页间距**永久缓存成 0** ⇒ 总高反而少 14855px。
     改为"取不到就返回 null、不缓存、本轮退回全量"后：**prism 164070 == 164070 (Δ0, gap 5px)、
     atlas 167071 == 167071 (Δ0, gap 6px)**（修前 prism +2973）。
  2. **TEST-2 冒烟断言改为同帧「窗口化 vs 全量」对照**：在同一个 `page.evaluate` 里来回切 `rowWin` 各读一次
     并等两帧，同时打出实测 gap；断言 `|Δ| < 50px`。新增 1 项 ⇒ 冒烟 34 → **36 项 0 失败**。
  3. **TEST-1 补两条接线断言**（`test_qbmanager.py`）：`test_drain_web_commands_bumps_write_seq`
     （写命令 +1 / 自投递不变）与 `test_drain_bumps_write_seq_before_writing_receipt`（spy 观察回执写入
     时刻的序号）。后者**红绿双验**：还原旧顺序即报 `实际 0 vs 期望 1`。基线 1049 → **1051 passed / cov 92%**。
  4. **BUG-5 顺序调换**：`_web_write_seq += 1` 提到 `_set_web_result()` 之前（先失效缓存，再宣布成功）；
     顺带把延迟回执命令收成模块常量 `DEFERRED_RECEIPT_COMMANDS`。
  5. **BUG-6 `sync_interval` 落实钳制**：`run()` 改 `min(self.config.sync_interval, main_tick)` ——
     文案承诺"大于主循环间隔时按主循环间隔生效"此前是空话（`_task_line` **不拉快照**，配 5s 会让快照
     新鲜度掉到心跳之下）。既有用例的取值都成对（0.05/0.2、5.0/5.0）故钳制为 no-op，无回归。
  6. **DOC-1~3**：改写 `app.js` 窗口化头部注释（删掉"行高必须齐 / >2px 回退全量"这稿被推翻的口径，
     改为"逐行实测 + 前缀和"）+ `rowWin` 的 data 注释；`renderMs` 警告文案不再写"需 P1 行窗口化"
     （改为"稳态应远低于此，首帧超属预期"）；删掉 3 处测试计划清单重复行（`test_torrents.py` 1 处、
     `test_web.py` 2 处）；`web_commands.py` 的守卫路径 `tests/test_web_commands.py`（**不存在**）改为
     `tests/test_web.py::test_api_enqueue_wakes_main_loop`。
  7. **SEC harness 限回环**：`--host` 非回环直接拒绝启动（退出码 2）—— 该服务免鉴权，绑 0.0.0.0 等于
     把 WEB UI 交给整个局域网。实测 `0.0.0.0`/`192.168.1.10`/域名/空串全部拒绝，回环四写法放行。
  8. **TEST-3 `cmdStats` 接上消费者**：命令排队 >100ms 或端到端 >400ms 时打一条 `[perf]`（冒烟会收集打印）
     —— 此前全仓只写不读，是死字段。
  9. **顺带**: `memberWin` 由 computed 改为**方法并接收成员数组**（分组页传 `g.members` / 追剧页传 `e.members`），
     修掉 BUG-2 的"追剧页成员窗口是死路径"（原先写死读 `expandedGroup`，而追剧页展开态是 `expandedShowEp`
     ⇒ 占位恒为 0，与模板注释相反）；两套 UI 共 8 处调用点同步；随之删除已无引用的 `expandedGroup` computed。
  10. **环境**: 仓内 `.coverage` 会在开跑时被 coverage 擦除而撞上删除拦截层（**开局 1 秒即退出**），
      与 basetemp 那条是**同一个拦截层的两个时点**；根治写法 `COVERAGE_FILE=H:/Temp/….coverage` +
      `--basetemp=H:/Temp/…`，已入 pitfalls。
  **仍未提交**；下一步按报表 08 节做第 2 批（5~7），其中第 7 项需先拍板方向。

- 2026-09-19 19:0x — **复核缺陷修复 · 第 2 批（报表 5 = BUG-3）已实施（未提交）**，并顺带修掉 3 个
  复核时漏报的缺陷。开工第一件事是**真浏览器实证**，结果推翻了报表自己的一条判断：

  0. **实证先行（推翻了报表 BUG-3 证据②）**：用 `--cmd-result hang` 的桩（回执永不返回）实测，
     整组暂停后组行 class 由 `s-checking` 变 `s-paused`（`pendingOps` 2 条）—— **颜色本来就是变的**。
     原因：组行状态色取自 `decoratedGroups.status.primary`，而它是 `_aggStatus(成员 kind)` 的 `computed`，
     `applyOptimistic` 改的正是成员 `kind` ⇒ 自动重算。真正缺的只有 `is-pending` 绑定。
     集行则**确实**完全没有乐观调用（`actEpisode('pause')` 后 `pendingOps` 0 / class 不变 / `e.state` 不变）。
     ⇒ 组行的工作量从"加一套补丁表"缩到"加一个绑定"。教训入 pitfalls（只读调用点区分不了
     "机制没工作"与"没绑 class"）。
  1. **BUG-3 落地**：组行绑 `is-pending`（`isGroupPending`，先过 `pendingAny` computed 做 O(1) 短路 ——
     集行动辄上百成员，无补丁时不该逐个查）；集行新增 `epState(e)`：`e.state` 是后端回传的**标量拷贝**，
     成员被补丁改过也不会动，故有成员在飞时按同一张 `STATE_RANK` 表现算，没有在飞时一律用后端真值
     （不碰"筛选后成员子集"与后端全量成员口径不一致的语义）。`actEpisode` 的 pause/resume 分支
     接入 `applyOptimistic` / `resolveOptimistic`（发送失败同样回滚）。两套 UI 共 4 处 class 绑定同步。
  2. **BUG-8（高，报表漏报）**：`VIEW_ARRAYS["show"]` 只回 `shows`，而 `shows[].members` 只是一串 hash，
     前端要靠 `memberByHash`（由 groups+singles+torrents 拼出来）还原成成员对象 ⇒ 索引为空则每个集的
     成员都被 `filter(Boolean)` 丢掉 ⇒ **刷新后停在追剧页得到永久空表**（实测 `groups=0 / singles=0 /
     memberByHash=0 / decoratedShows=0 / 0 行`），且 `lastRid` 已记住 ⇒ 之后每轮都是"版本未变不回传"，
     **自己不会恢复**，必须手动切一次视图。修法 `("shows", "groups", "singles")`（仍不回 4.5MB 的
     `torrents`）；响应体实测 134,808 → **1,880,935 B**（全量 6,405,735 / 辅种页 1,746,319 / 种子页 4,524,992）。
     报表当初量到 134KB 却没问"这份响应够不够把页面渲染出来" —— 同时暴露冒烟里一条**恒真断言**
     （`epRows >= 0`），所以 34 项全绿也没拦住。
  3. **BUG-9（中，报表漏报）**：`magnet_uri` 只在种子页的平铺 SEED_ITEM 里（`web_view.py:305`），
     而 `memberByHash` 先无条件注册 groups、再用 `if (!map.has(hash))` 注册 singles/torrents ⇒
     平铺数组**永远当不上兜底**，索引条目恒无 magnet ⇒ 右键"复制磁力"**100% 失败**，提示还是误导性的
     "该种子没有 magnet 链接"。实测（种子页，平铺数组已加载）：`flatHasMagnet=true` 但 `idxHasMagnet=false`。
     修法：点击时按需取一次详情（复用 `_editDetail`，抽屉已开则零请求），**不给每 1.5~3s 一轮的响应体加字段**。
  4. **BUG-7（低，报表漏报）**：同一概念两张状态优先级表 —— 后端 `_SHOW_STATE_RANK`
     （决定追剧页集行 `e.state`）vs 前端 `decoratedGroups` 内联表（决定辅种页组行颜色），
     六种混合态里 **2 种结论相反**（`{downloading,checking}` / `{paused,seeding}`）⇒ 同一批种子两页不同色；
     更危险的是乐观 UI 有"颜色弹回"风险（前端按自己的表算点击后的色，回执按后端的表算真值）。
     修法：前端抽 `STATE_RANK` 单点表并**对齐后端顺序**，组行/集行共用 `_aggStatus`；可见变化仅那 2 种混合态
     （6 组样例实测：2 组变、4 组不变）。
  5. **冒烟脚本自身的 3 处缺陷（一并修掉）**：① **恒真断言** `epRows >= 0`（BUG-8 就是这么溜过去的）；
     ② **error 模式恒红** —— 批量乐观断言在 `--expect-cmd error` 下 `pendingOps` 恒 0（回执瞬间返回，
     乐观窗口在采样前就关了）⇒ 该模式必红 ⇒ 实际上没人跑 error 模式；按模式分流为
     "ok/hang 断言覆盖全部目标" / "error 断言回滚干净"；③ **详情端点从未被覆盖** ——
     `FakeTorrent` 缺 `to_dict()` 使 `/api/torrents/{hash}` **恒 500**，于是详情抽屉、限速/分享率/移动/
     重命名四个编辑对话框、复制磁力在冒烟里从未被跑过（静默 500，只有把 console.error 当判据才暴露）。
     给 `FakeTorrent` 补 `to_dict()`（与真实现同形：不导出 `tor` 自引用与不可 JSON 化的 `tracker_conf`）。
  6. **验证**：单测 **1051 → 1052 passed / cov 92%**（新增
     `test_web.py::test_ensure_group_state_show_view_carries_member_index`；静态守阵新增第 8 项机械比对
     前后端两张状态表；改写 `test_api_state_view_scoped_payload` 的 view=show 口径）——
     两条新守阵均**红绿双验**（注入 `STATE_RANK` 漂移 → 报"前端 {…'paused':4,'seeding':3…} / 后端
     {…'paused':3,'seeding':4…}"；把 `VIEW_ARRAYS["show"]` 改回只回 shows → 报"追剧页必须连带成员索引"）。
     冒烟 **36 → 46 项 0 失败**（ok 模式）/ **44 项 0 失败**（error 模式回滚路径）。
  7. **环境坑（新，已入 pitfalls）**：仓外 `--basetemp` 目录**本身必须不存在** —— pytest 开跑前会 `rm_rf`
     已存在的 basetemp，而本机沙箱的删除拦截层会拉起回收站助手进程，被 `tests/sidefx.py` 记成越界 POPEN
     ⇒ **点号全过、`1052 passed`，却在某个用例 teardown 报 ERROR**（守阵按用例累积判定，谁先跑到挂谁头上）。
     实测对照：复用旧目录 → `1052 passed + 1 error`；换全新路径 → `1052 passed / EXIT=0`。
  8. **未做**：报表 §08 第 6 项（响应体按可见列裁剪 / P2-2 增量回传，牵动 SEED_ITEM 字段契约）与
     第 7 项（`sync_interval` 与分档轮询对齐，需先拍板"让轮询跟上快档"还是"给快照刷新加 Web 活跃门控"）。
  9. 报表已追加 **§10 复核修订与修复回执**（含对 BUG-3 证据②的更正、BUG-7/8/9 的完整记录、
     §08 逐项回执、冒烟自身缺陷表、复跑基线对照）。
  **仍未提交**；下一步：第 3 批（报表 6 / 7），其中第 7 项需先拍板方向。

- 2026-09-19 19:3x — **续查：热路径白跑 85%（FastAPI `jsonable_encoder`）已实施（未提交）**。
  起因是动手做报表 §08 第 6 项（响应体裁剪）前先把「一轮 refresh 花在哪」量清楚，结果发现
  **第 6 项要修的地方修错了**，真正的开销在别处、而且一行就能拿掉。

  0. **四步定位（每步都能独立否决一个方向，避免在错误方向上做优化）**：
     ① **字节构成**（3000 种子 / 74 字段）：占比最大的 `magnet_uri` 仅 **6.3%**，要覆盖 80% 字节需要
        **52/74** 个字段 ⇒ **字段裁剪是死路**（真裁掉一半字段也省不到 30%，还要重走 SEED_ITEM 契约）；
     ② **客户端拆分**（浏览器内实测）：单轮 237 ms = 网络+读文本 **224 ms** + `JSON.parse` **4.1 ms**
        + 赋值+patch **8.3 ms** ⇒ 前端只占 10 ms，95% 是「在等服务端」；
     ③ **网络对照**：同尺寸 5.12 MiB JSON 走 uvicorn + StaticFiles 只要 **1.6 ms**
        （`python -m http.server` 1.0 ms；首轮 71 ms 是冷读盘）⇒ 排除网络与 uvicorn，
        **gzip 也无意义**（没有可省的东西）；
     ④ **服务端端点内耗时**（加 5 行计时中间件实测）：`view=torrent` **189 ms**，而应用层可解释的只有
        `json.dumps` 的 25~50 ms（该轮未重建视图）⇒ 缺口 ~160 ms 在 FastAPI 的响应管线里。
  1. **真因**：FastAPI 对**普通 dict 返回值**会先跑 `jsonable_encoder` **递归遍历整个响应体**
     （3000×74 = 22 万个值，实测 **161 ms**，占端点总耗时 **85%**），而我们的视图本来就是 JSON 原生类型
     （`str/int/float/bool/None/dict/list`）⇒ 这趟遍历纯属白跑，且**全程占着 GIL**（与主循环抢 CPU，
     是大库下「点了没反应」的一个真实来源）。
     关键在 `fastapi/routing.py` 的一行短路：`if isinstance(raw_response, Response): response = raw_response`
     ⇒ **返回 `Response` 实例即跳过整个 `serialize_response`**。
  2. **修法（1 行）**：`web.py` 的 `/api/state`（`web.py:263`）与 `/api/groups` 由 `return payload` 改为
     `return JSONResponse(content=payload)`，并在注释里写清代价：日后往 payload 塞非 JSON 原生类型
     （`datetime`/`set`/`Decimal`）会**直接 500（fail-fast）**，不会被静默转成字符串。
  3. **实测**：服务端 `view=torrent` 189.0 → **23.5 ms**（8.0×）、`view=show` 79.6 → **11.6 ms**（6.9×）；
     **前端整轮 refresh 跟着掉**（整轮本来就在等服务端）：prism 窗口化 239/233/234 → **95/84/84 ms**、
     atlas 268/266/267 → **74/83/83 ms**。
  4. **输出零变化（关键验证）**：新旧两个服务并排取 `torrent/group/show/full` 四份响应，字节长度完全一致
     （4 764 992 / 1 746 319 / 1 880 935 / 6 645 735），解析后 JSON 除自增的 `rid` 外完全相同。
  5. **守阵**：`test_web.py::test_api_state_skips_jsonable_encoder` —— 用**计数替身**包住
     `fastapi.routing.jsonable_encoder`，断言三个热路径调用次数为 **0**。**刻意不用计时断言**
     （计时在 CI 上不可靠，计数是确定性的）；**红绿双验**过（注入 `return payload` → 报
     「走了 jsonable_encoder(1 次)」）。
  6. **验证**：单测 **1052 → 1053 passed / cov 92%**；冒烟 **46 项 0 失败**（ok 模式，双 UI）。
  7. **报表**：§08 第 6 项标记为**已被实测否决**并指向新增的 **§11**（含四步定位表、改动实测表、
     输出一致性验证、守阵说明、三条教训）。同类端点（`/api/torrents/{hash}/files`、`/api/search`、
     `/api/torrents/{hash}/trackers`、`/api/log`）同样的 1 行改法**尚未做** —— 用户触发型、不在
     1.5~3 s 轮询路径上，故未纳入本批。
  8. **教训入 pitfalls**（两条新条目）：① 热路径返回裸 dict 会被 FastAPI 白跑一遍 `jsonable_encoder`；
     ② 「载荷大」不等于「要裁字段」—— 只说明有开销，不说明开销在哪，凭载荷大小直接开药方十有八九修错地方
     （这次就是）；而「加一层 5 行计时中间件对账」成本极低。
  **仍未提交**；下一步只剩报表 §08 第 7 项（节拍对齐，需先拍板方向）。

> 较早的进度日志(5,429 字符)**已外迁** → [attachments/webui-responsiveness-log.md](attachments/webui-responsiveness-log.md)
