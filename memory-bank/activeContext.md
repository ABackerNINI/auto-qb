# Active Context — 当前焦点

> Memory Bank 核心文件之一: 回答"现在正在做什么 / 上次做到哪 / 下一步从哪继续"。**每次会话开始先读本文件。**
> 稳定事实在 projectbrief / productContext / systemPatterns / techContext 与各主题文档; 计划与完成状态在 [progress.md](progress.md); 本文件只放**易变的会话级状态**。
> 维护纪律 (完整规程见 [memory-bank skill](../.agents/skills/memory-bank/SKILL.md)): ①每次会话收尾更新本文件, 已完成条目沉淀到 [progress.md](progress.md) 或主题文档后**删除** — 本文件只放易变状态; ②命中立档阈值的任务在 [tasks/](tasks/_index.md) 立档并同步索引; ③**禁止**在本文件追加长流水账纪要 (会淹没真正的当前焦点)。

**最后更新**: 2026-09-19 (**上轮复核的第 1、2 批缺陷修复 + 续查的热路径优化均已实施未提交** ——
  第 1 批: 行窗口间距改运行时实测(棱镜占位总高 +2973 → **0**)、冒烟改同帧「窗口化 vs 全量」对照、
  两条写序号接线断言、回执/失效顺序调换、`sync_interval` 钳制、文档漂移、harness 限回环、`cmdStats` 接消费者;
  第 2 批: 组/集行乐观(BUG-3) + 修复过程中新发现的 **BUG-8 追剧页刷新后永久空白(高)** /
  **BUG-9 复制磁力恒失败(中)** / **BUG-7 两页状态色不一致(低)**;
  续查: 报表 §08 第 6 项(响应体裁剪)**经实测否决**, 真正的开销是 FastAPI 对裸 dict 返回值先跑一遍
  `jsonable_encoder`(占端点耗时 85%), 改 `return JSONResponse(...)` 后服务端 `view=torrent`
  189 → **23.5 ms**、**前端整轮 refresh ~240 → ~85 ms**。
  **基线 1049 → 1053 passed / cov 92%; 冒烟 34 → 46 项(ok) / 44 项(error) 0 失败**。
  **真机走查报的「乐观 UI 反应 2-4s」已修并推送主线(Gitee `a8eb6e8`)**: `act()`/`actTorrent()` 补丁提到 POST 之前 + 3s 兜底改从
  回执起算 + 补两段埋点; 受控复测注入 2000ms 时补丁 2012 → **0ms**, 1053 passed 不变, 冒烟 **48 项 0 失败**
  (详见「正在进行」① 第 3 条与 [progress.md](progress.md))。
  只剩报表 §08 第 7 项(节拍对齐, 需先拍板方向) —— 见下「正在进行」第 ① 条与
  [progress.md](progress.md) 三波次总条目 — 详见 [testing.md](testing.md))

## 正在进行


- **① 上轮计划复核的收尾(只剩第 7 项) (2026-09-19)**: 复核报表
  [docs/plans/26-09-19-1745-webui-responsiveness-review.html](../docs/plans/26-09-19-1745-webui-responsiveness-review.html)
  (评级 计划 A− / 实施 A− / BUG B / 安全 A− / 性能 B+ / 测试 B−), 报表已追加 **§10 复核修订与修复回执** +
  **§11 热路径白跑 85%**(FastAPI `jsonable_encoder`)。**第 1、2 批与 §11 均已实施未提交**
  (明细见 [progress.md](progress.md) 三波次总条目末段 + 档案进度日志)。
  **已全部完成(两条 issue 均 Fixed, 见 [issues/_index.md](issues/_index.md)) —— 均尚未提交**:
  1. **[webui-poll-cadence-mismatch](issues/26-09-19-1900-webui-poll-cadence-mismatch.html)**(Fixed) ——
     `sync_interval`(1.5s)与前端分档轮询(1.5/2/3s)在 >3000 种子时错配, 约一半 `rebuild_views` 无人消费。
     **需先拍板方向**: 让轮询跟上快档(降 `basePollMs` 下界) vs 给快照刷新加 Web 活跃门控(无人看就不刷)。
     ⚠ 这条是**频率类**改动, 拍板前先按 pitfalls 「主循环分层节拍」与「把 main_tick 缩短来换响应速度」两条判据过一遍。
     ⚠ 另注: 第 1 批给 `sync_interval` 加的钳制(`min(sync_interval, main_tick)`)只兜住了"快照新鲜度
     掉到心跳之下", **没有**解决"重建了没人消费"这一半 —— 两件事别混。
     **已按方案 B 实施**(用户拍板): `_web_pending_ver` 记"已发布但还没被取走的版本号", `_flush_views()`
     只在没欠账时重建; 实测 20 周期 **40 → 20 次(省 50%)**。两个边界由
     `test_view_rebuild_waits_for_client_consume` 钉住: 脏标记必须保留、`force=True`(命令改状态)必须绕过。
     顺带发现: 方案 B **不需要新契约** —— 客户端本来就在轮询时发 `rid`, "有没有人取走"现有参数即可表达。
     ~~**整剧(剧行)操作没有 is-pending**~~ —— **已修并验证, issue 已置 Fixed**
     ([webui-show-row-no-pending](issues/26-09-19-1959-webui-show-row-no-pending.html)):
     `app.js` 新增 `isShowPending(s)`(复用 `isEpPending`), prism/atlas 的 `.show-row` 各加一行绑定;
     冒烟补了剧行断言(双 UI × 双模式)。⚠ 两个排查坑: ① **8099 端口被别的 worktree 的桩服务占着**,
     探针一度在测别人的代码 —— 起桩服务后先 `curl` 确认服务的就是本 worktree 的文件, 并改用专属端口;
     ② **冒烟别用固定睡 N 毫秒采样**(成功路径会因补丁是逐 hash 贴而假失败, 失败路径会因补丁在 POST
     之前而假阳性), 改成"等条件成立"。**尚未提交。**
  2. ~~**热端点改 JSONResponse 直返**~~ —— **已修并验证, issue 已置 Fixed**
     ([webui-hot-endpoints-jsonable-encoder](issues/26-09-19-1900-webui-hot-endpoints-jsonable-encoder.html)):
     `/api/search` 服务端 **82.6 → 23.3~30.1 ms**(输出字节与基线逐字节一致), 详情族
     (`/api/torrents/{hash}` + `/trackers`、`/files`、`/peers`)一并统一写法(桩里 payload 太小测不出收益,
     为真实数据预置)。⚠ **例外**: `/api/config/schema` 载荷含 dataclass(`Group`/`Field`/`Plugin`),
     直返会 `TypeError: Object of type Group is not JSON serializable` ⇒ 500, **必须保留 jsonable_encoder**,
     已回退并在端点留注释 —— 判据见 pitfalls 该条目。守阵清单扩到 8 条 URL(7 个端点)并红绿双验。**尚未提交。**
  3. **[webui-optimistic-latency](issues/26-09-19-1939-webui-optimistic-latency.html)** —— ✅ **已修(本提交)**
     (2026-09-19): 真机走查报「乐观 UI 反应 2-4s」。受控测量(Playwright 给命令 POST 注入延迟)
     证明 POST 慢多少反馈就晚多少: 注入 2000ms 时补丁 **2012ms** 才贴(`actEpisode` 对照 0ms)。
     已把 `act()`/`actTorrent()` 的 `applyOptimistic()` 提到 POST 之前 + 3s 兜底改从回执起算 +
     补「点击→补丁/POST」两段埋点; 复测 **0ms**。1053 passed 不变, 冒烟 **48 项 0 失败**(新增 2 条守阵)。
     **未追**: 真机 POST 为何慢到秒级(长 tick / GIL / 线程池)—— 修法已让 UI 不依赖它, 复测时看新的
     `[perf] … POST xxxms`, 持续 >400ms 再按方案 C 追。
     ⚠ 顺带发现并**另立 issue**(未修): [整剧操作在剧行上无 is-pending](issues/26-09-19-1959-webui-show-row-no-pending.html)
     —— 补丁 0ms 贴上但 `.show-row` 不绑 pending(剧行默认折叠), 与 BUG-3 同类的漏绑。
- **② WEB UI 操作跟手性优化 (2026-09-19)**: 三波次全部入库(`10e06a8` 分层节拍 + 命令唤醒 + 乐观 UI + 批量合单
  / `5d1e52c` 请求超时 + 视图分片回传 + 只读缓存 / `366092d` 行窗口化)。计划
  [docs/plans/26-09-19-1241-webui-responsiveness-plan.html](../docs/plans/26-09-19-1241-webui-responsiveness-plan.html); 档案 [tasks/26-09-19-webui-responsiveness.md](tasks/26-09-19-webui-responsiveness.md)。
  **剩**: 真机走查(真实 qB 数据下的观感)。
- **③ 前端轮询按种子量分档 (2026-09-19, 待提交)**: 计划里唯一排在 P1 之后的项 —— 降轮询间隔会**放大**全量回传 + 整树重渲染, 顺序错了会加剧不跟手。档位实测而定: 1000 种子单轮 143ms / 3000 种子 353ms / 5000 种子 ~550ms ⇒ **≤1000 → 1.5s / 1000~3000 → 2s / >3000 → 3s**(主线程占用率 10%/15%/17%); 下界 1.5s = 服务端 `sync_interval`(再快只是多拿空响应)。实现: `pollSec` 字段退役(不留死字段), 新增 `basePollMs()`; 冒烟新增分档断言 ⇒ 30 项 0 失败。
- **④ WEB UI 视图重建范围收口 · 种子速度刷新滞后修复 (2026-09-18, 未提交)**: 真因是两条重建路径**范围不一致**(主循环 `_tick` 只重建 `_group_view` 却清掉共享脏标记 ⇒ singles/shows/flat 被饿死, 版本号照常自增 ⇒ 前端换上陈旧数组)。已改为唯一入口 `rebuild_views()` + 置脏移出门控 + 前端取消 idle 退避并把 `server_state` 并入 `/api/state`。基线 1018 → **1021 passed**。剩用户真机走查 → [tasks/26-09-18-webui-view-rebuild-scope.md](tasks/26-09-18-webui-view-rebuild-scope.md)
- **⑤ 浏览器冒烟能力 (2026-09-19, dev-only, 长期有效)**: `scripts/ui_harness.py`(真 `create_app` + `FakeClient` + 合成种子 + 命令泵 `ok|error|hang`)+ `scripts/ui_smoke.cjs`(Playwright, 双 UI **46 项断言** + 内置 A/B 基准)。**Windows 上可跑**, 攻破了"单测测不到前端交互"这个长期卡点。⚠ `--host` 现在只接受回环(免鉴权服务不得暴露到局域网)。⚠ **两种模式都要跑**: `ok` 看正向、`--expect-cmd error` 看回滚 —— 后者此前必红所以没人跑, 已按模式分流断言。

- **5000 种子仿真客户端 · 独立安全/性能测试 (2026-09-19, W0 已出数, W1 未开工)**: 用户要"独立测试 + 仿真客户端 + 5000 种子 + 每 1.5s 活跃 10%, 主要测安全/性能"。**计划已产出** [docs/plans/26-09-19-1433-sim-client-5000-plan.html](../../docs/plans/26-09-19-1433-sim-client-5000-plan.html); 已立档 [tasks/TASK018](tasks/26-09-19-sim-client-5000.md)。**评审四项口径**: ①负载两种语义都做可切换(`churn` 滚动换批默认 / `steady` 固定活跃池) ②形态**独立 HTTP 仿真服务**为主(进程内 Fake 仅 W5 归因用, 不出性能数字) ③**不进 CI**, 手动跑 ④**先纯外部观测, W5 前不动 `src/`**。**W0 探针实测**(真实 `qbittorrent-api` + 回环, 5000×70 字段): 全量载荷 8.77 MB / 端到端 205–240 ms, 增量(500×8)107 KB / **3.3 ms**(差 62×); 朴素全量 diff 22.6 ms vs 脏集合 0.34 ms(67×); 单次回环请求 2.27 ms。**踩坑**: `sync/maindata` 的 **`rid` 在 POST body**, 只解析 query 恒得 `rid=0` ⇒ 永远退化全量(已定为 W1 单测回归点)。**两个产品级发现**(推算, 待 W4 实测): 首轮灌入约 **34 s 主循环停摆**(5000 次 `torrents/files` ≈ 11.4 s + maintenance 立即执行 ≈ 1 万次写 ≈ 22.7 s); `max_tasks_per_tick=20` 下 5000 种子 +2 规则时**规则实际执行周期 ≈ 25 min**(名义 60s)。**二轮补充(同日)**: ①日志分**两层** —— 统计层 `summary.json` 每项 check 自带 `值/op/阈值/result` + 一行 `verdict`(OK/WARN/FAIL), 供 AI 扫读判断有无问题; 完整层 trace/writes/sim-events/fs 快照/子进程日志四路统一 `time.time()` 时间戳对齐供回溯; 阈值未固化时记 `BASELINE` 而非 FAIL ②新增**破坏性场景 D1–D5**(删种子/删文件), 关键是引入**真实落盘的虚拟文件树**(`--fs-root`, 默认物化 300 个种子且必含全部辅种群) —— 否则"文件删没删"只是记账、测不出真实行为; **D4 外部删文件 → 缺文件保护**为头号场景, 判据是组内成员停止率 **== 100%**(漏一个即上传垃圾数据被封号)+ 响应 ≤3 轮, 且必须由磁盘扫描自己发现、不能由 sim 直接改 state ③性能矩阵扩到 P7 删除风暴, 波次加 W3b。计划文档已重排为 12 节。**三轮补充(同日)**: ①新增 **`--root` 工作根**(默认 `R:\auto-qb-sim`, 环境变量覆盖), 文件树/配置/data_dir/两层日志全部落在 `<root>/runs/<时间戳-场景ID>/`; R 盘不存在时回退临时目录并 WARN ②**R 盘即真实下载盘**, 加 **B1–B4 四道边界校验**(哨兵根 `.auto-qb-sim-root` / 删除前 realpath 逃逸判定 / 单次删除数量上限 / 收尾 `unexpected_removals` 核账), 任一不过即拒绝, W1 带单测 ③**修正**: 文件树由"只物化 300"改为**默认全量物化** —— 未物化种子会被缺文件扫描误判丢失并整组误暂停, 会让 D4 判据失效。**第四轮(同日)· W1+W2 已实施并跑通**: 落地 `scripts/sim_qb.py`(仿真服务端) 与 `scripts/sim_run.py`(驱动器, 一键场景 + 两层日志), 端到端跑通(真实 `qbittorrent-api` + auto-qb 子进程)。**实测**: 首轮 5000 种子 **17.19 s 停摆**(2000 种子 7.46 s, 约 3.7 ms/种子线性), 稳态 **2.017 s / 漂移 19 ms 完全跟得上**; S1 dry-run 写台账 **0 条**; D4 组内**停止率 1.0、响应 0.77 tick**; 高风险端点全程 0 命中; `--self-test` 8 项全绿。**修正 W0 推算** 34 s → 17.19 s(差额: 1/3 种子未配置站点被跳过 + 回环比真 qB 快, 真实 qB 只会更久); 判据改为**首轮/稳态分离**(混算会每次假红)。**踩到四个"测假"陷阱**已修并入 pitfalls: ①`"errored"` 非合法 qB 状态(应 `"error"`, 否则缺文件扫描完全不触发) ②辅种组内成员必须共享**完全相同**的文件相对路径(否则根本没归成组) ③未配置站点种子不归组 ⇒ D4 停止率基准失真 ④首轮/稳态必须分开统计; 另实测到 `qbittorrent-api` 每次写请求前额外查一次 `app/webapiVersion`(库内无缓存) ⇒ 写请求量翻倍, 归入 W5 归因候选。全量 **1041 passed 不变**。**第五轮(同日)· W3b 已完成 + W3 挖到真缺陷**: **D1–D5 五个破坏性场景全部 verdict OK** —— D1 外部删 20 个种子: 快照 300→280、跌幅 20 == 20; D2 带文件删除: 267→262(少 5, 整组共享文件)、unexpected=0; D3 经 WEB UI 删 4 个: 4/4 投递成功、hash 集合与 `deleteFiles` 逐条全等、`torrents/delete` 请求数 4 == 命令数 4; D4 组内**停止率 1.0 / 响应 0.42 tick**; D5 批量删 500(跌幅 500==500、重复投递 removed 不崩) + 两相运行 `exec_history` **71 → 71 零增长**(跨进程幂等成立)。**D3 改定义**: 静态核查 `rules.registry.ACTIONS` **没有 delete**, 全仓唯一 `torrents_delete` 在 `mixins/web_commands.py`(WEB UI 命令触发) ⇒ auto-qb **不存在任何自动删除路径**(保守默认), 原计划"配置一条删除规则"无法成立, 改测 WEB 命令路径。**又修四处"测假"**(已入 pitfalls): ①`torrents_removed` 曾硬编码 `[]` ⇒ 外部删除 auto-qb 永远看不到(反向对照: 抹掉后 `snapshot_drop` 由 20 变 **0**, 快照全是幽灵) ②只盯写台账看不出幽灵(打标签一次性) ⇒ 新增 WEB `/api/status` 的**快照数**观测通道(不开 `--web-port` 该项记 BASELINE 提示空转) ③**硬 kill 拿不到 `state.json`**(Windows `terminate()` = TerminateProcess, `finally` 不跑; `CTRL_BREAK_EVENT` 也只得到 0xC000013A, Python 不转成 KeyboardInterrupt) ⇒ 新增 `scripts/sim_autoqb.py` 启动包装(装 SIGBREAK 处理器), 并加 `RUN.graceful_exit` 判据(反向对照: 硬 kill 时 `state_file_present` 必红) ④两相运行的**相位重启间隔**被算成稳态漂移(1.84 s 假红) ⇒ 传入相位边界剔除。**S5 实测 FAIL(真缺陷, 未修)**: `--abort-after 12 --abort-duration 10` 断连 10 秒后 auto-qb **永久停在断连态** —— 重连只在 `except APIConnectionError` 分支触发, 而该分支第一步 `self.client = None`; client 为 None 后 `api.sync_maindata()` 抛的是 **AttributeError** 而非 APIConnectionError ⇒ 落进 `except Exception`(只打日志、**不重连**) ⇒ 死循环, 30 秒 28 条异常栈、sync 轮次 22→5、全量自愈从未发生, 只能重启进程。修复方向(不在本轮范围): 断连期间跳过 `_tick` + 独立重连分支, 或让 `QbApi` 在 `_client is None` 时抛 `APIConnectionError`。**本轮未动 `src/`**。**第六轮(同日)· W3 收口 + W4 基线固化完成**: **S6/S7/S8 全绿** —— S6 `data_dir` 跑前后快照只允许
`state.json`/`.bak`/日志/`web.token`/锁(实测 0 越界); S7 并发轮询 500 次 4xx/5xx **0**;
S8 奇数 KiB/s 手设限速 30 个**一个没被改写**、`setUploadLimit` **0** 命中(初版造了偶数 KiB 导致 21/30 假红 ——
项目约定奇数值才是"手动限速不覆盖")。**W4 跑齐 P1–P7 并固化阈值**: 新增 `scripts/sim_baseline.py`
(`--only` / `--merge`), `sim_run.py` 启动时读 `…baseline.json` 填阈值(未固化记 BASELINE)。
实测 P1 首轮 **14.37 s**(修正 W0 推算 34 s)、P3 tick2 14.20 s、P3b tick1.5 13.52 s、P4 steady 14.37 s、
P7 删除风暴 9.56 s —— 稳态全部跟得上(漂移 < 0.35 s); **P2 渐进灌入掉拍**(稳态 2.87 s vs tick 2.0 s);
**P6x 4 线程轮询时主循环近乎停摆**(45 s 只 1 轮 sync、`torrents/files` 一次没拉、`/api/state` p95 1.28 s;
单线程轮询也已把漂移从 0.33 s 顶到 0.95 s)。固化阈值 `first_round ≤ 22.68` / `写速率 ≤ 6210.49` /
`p95 ≤ 1218.4` / `稳态漂移 ≤ 1.0`(纯主循环; ramp 与压力档**不进**稳态阈值候选集)。
顺带实现 `--ramp`(渐进灌入, 新暴露种子须整条进脏集合)。修掉三处工具问题: 停机掐断轮询 ⇒
uvicorn/h11 异常栈污染 `LOG.tracebacks`(加 `quiesce` 事件)、`--tick 1.5` 漂移仍按写死 2.0 算、
阈值硬编码在调用处 ⇒ 固化值用不上。**新建 `TODO.md`**(BUG-01 断连无法自愈 + PERF-01/02 + 剩余波次)。
**第七轮(同日)· W5 归因 + W6 收尾完成(计划 W0–W6 全部走完)**: 计划文档新增 §13 归因四条 ——
① 首轮灌入 = 请求数 bound(5000 种子第一轮 **15 754 次请求 ≈ 0.96 ms/次**)
② 稳态吞吐被 `max_tasks_per_tick=20` 卡死(**实测 10.6 任务/s**)
③ WEB 全量视图(PERF-01) ④ 写请求放大一倍(`app/webapiVersion` 命中数恒等于写请求数)。
**纠正 W0 两处推算**: 首轮 34 s → **14.4 s**;「R=2 → 25 min」→ 按实测吞吐重算 **16.7 min**(多算一档规则)。
**⚠ 框架性误判已纠正**: 首轮与稳态是两条互不相干的路径 —— 首轮新种子在 `_refresh_torrents` 里
对 `matched_added` **逐个内联**跑(拉 trackers + files), **不经任务队列**, 故 `max_tasks_per_tick` 对它无效;
只有稳态周期任务走 `TaskQueue.run_due(max_tasks=20)`。P5 的「队列深度」需进程内剖面, 未出数。
**W6**: 基线 + 5 条判据设计约定写入 `memory-bank/testing.md` 新增一节。
**全量 1041 passed 不变, `src/` 全程未动**。**遗留**: BUG-01(断连不自愈)按用户决定**暂不修**, 已立档在 `TODO.md`

## 待用户真机走查 (代码/测试均已完, 只差真实 qB 数据下的观感确认)

- **跟手性优化三波次** —— 右键菜单响应 / 切视图首帧 / 3000+ 种子滚动流畅度
- **本轮新修的 4 处(建议顺路走查)** —— ① 刷新页面时若上次停在**追剧页**, 现在应正常显示(修复前是永久空白);
  ② 右键**复制磁力**在辅种页/追剧页应真能复制(修复前 100% 提示"没有 magnet 链接");
  ③ 整组/整集暂停后**行本身**应立刻变灰(半透明 `is-pending`)且颜色即时切换;
  ④ 混合状态组的颜色可能与修复前不同(状态优先级已统一到后端口径, 只影响 2 种混合态)
- **热路径提速(§11, 建议重点体感)** —— 3000+ 种子库下切视图/滚动时数据到达更快(服务端 189 → 23.5 ms)。
  重点看: 种子页在**数据变化那几轮**是否还有"迟一拍"的观感; 若大库仍觉卡, 下一步就是报表 §08 第 7 项
- **追剧页剧/集右键「打开目标文件夹」** (`c888fba`) —— 剧 → 集 → 种子三级各点一次; 顺带确认整剧开始/暂停/删除已恢复
- **视图重建范围收口** (`1021 passed`, 未提交) —— 种子速度是否已随轮询刷新
- **TASK015 错误种子原因** (`9723a76`) —— 错误态状态列是否显示 tracker 原文
- **TASK013 / TASK012 / TASK011**(第九/十/十一轮修复) —— 逐轮走查反馈
- **TASK014 UI 组件库 20 式** (`fae019a`) —— 挑选与按需迭代

## 定案口径 (别改回去; 完整判据见 [pitfalls.md](pitfalls.md))

- **列偏好"升版本"**: 列集变更(加列/减列/重排)与存储结构扩展**一律不升版本**, 只有"旧缓存结构已无法被 `loadColState()` 正确解释"才升(如 v2 按列索引存), 且升版本必须同时挂 `LEGACY_COLS_KEYS` 迁移。当前键冻结在 `autoqb_cols_v4`, 无 v5 计划。历史计划 `docs/plans/26-09-15-1042-webui-optimization-plan-v3.html` 里"重排列集则升 v4→v5"是当时口径, 已被第十轮计划取代 —— 存档未改动, **别照抄**。
- **第十轮两处已知限制**(非待办): ① 列偏好受 localStorage **origin 隔离** 影响(`localhost` 与 `127.0.0.1`/换端口 = 不同站点各存一份) —— 用户明确要求只存浏览器, 不做服务端化; ② 目录浏览器只能浏览**已有保存路径及其子目录**(安全边界), 全新位置需在输入框手填。
- **第十一轮定案**: 行/表头一律 `fit-content; min-width: 100%`(**底色跟内容**), **行内单元格必须 `min-width: 0`**(否则 nowrap 文本把行顶宽 ⇒ 列没溢出却常驻横滚条); 曾用"行定宽 100%"治假滚动条, 会让**溢出段没有底色**(用户实测"滚动后右边无背景条"), 已回退。
- **`想法.md`**: 工作区**干净**(最后一次入库 `3bface9`)。它属于红线文件(与 `config.yml` / `auto-qb-data/` 同级), 提交前照例用 `git status --short` 确认一遍是否又有改动, 不进暂存区。

## 下一步候选 (来源: `想法.md` 待办 + progress.md 规划中)

- **上轮复核的收尾**(见「正在进行」第 ① 条) —— 只剩报表 §08 第 7 项(节拍对齐, **需先拍板方向**)
  与同类端点的同样改法(低优先); 第 1、2 批与 §11 已实施未提交
- WEB UI: WebSocket 推送; 多用户; **设置页全面重构**(`想法.md` 现存最大一条未做项)
- WEB UI: 窗口日志等级可选; 星图侧补齐第九轮的纯版式项(棱镜已做: FX-05/06/09/17~25)
- 规则系统: 条件取反 (`!`/非 logic); 重新梳理 ignore_next_action_error / stop_following_rules_if
- tracker 分组前端增强 (阶段 2/3, 2026-09-15 拍板后续): 设置页 groups 下拉快捷追加 (rules_ref 风格); 辅种管理页按组筛选 (web_view 透出 conf.groups + app.js filterDefs)
- 其它: 切分大文件; 种子未变动时不触发内置维护任务; 版本管理; 命中限速曲线强调显示; 插件系统
- 🚧 实机验证: README 标注 🚧 的功能 (alpha 阶段), 生产使用前先 `--dry-run` 观察

## 历史归档 (已迁出本文件)

2026-09-14 ~ 2026-09-19 的全部会话纪要已按专题迁移到 [tasks/](tasks/_index.md) 各档案的"历史会话纪要 (原文归档)"段 (原文未删改), 或已沉淀进 [progress.md](progress.md) 的「已实现」段。需要回查历史请走 `tasks/_index.md` 定位专题档案, 本文件只保留**当前焦点**。
