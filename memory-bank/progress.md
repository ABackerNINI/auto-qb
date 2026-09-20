# Progress — 路线图与项目状态

> 来源: `想法.md` (设计草稿, 权威) + `README.md` 功能状态标注 + 源码 TODO + git log (截至 2026-09-12, commit d987015)。回答"XX 做了吗/计划怎么做"以此为准; 当前焦点与进行中事项见 [activeContext.md](activeContext.md)。

## 已实现 (✅, 有单测覆盖)

> 注意区分: 下表部分功能作者在 README 中标注 🚧 = "已实现但未严格测试(实盘验证)", 如规则引擎的条件/动作/checking/去重语义等 — 有单测但作者尚不认为经过严格验证; 此类 🚧 ≠ 未实现, 勿移除 (语义详见 pitfalls.md)。
- WEB UI 前端 `app.js` 按域拆分 (2026-09-20): 单个 **5045 行**的 `shared/app.js` 拆成 **1001 行内核 + 15 个域片段**(ui_feedback / filters / columns / format / decorate / hr / sort / menu / commands / add_torrent / selection / shows / delete_flow / drawer / dialogs), 293 个 methods 与 71 个 computed 按域搬走。机制沿用仓库既有范式(`window.AQB_*` 全局 mixin, app.js 末尾 `app.mixin` 注入), **未引入构建链与 ES module**, Vue 实例与两套模板**零改动**。验证: 静态守阵新增第 10 项「拆分接线」(漏挂 `<script>` / 漏 `app.mixin` / 跨片段重名, 已红验), 第 7/8/9 项改为按**整包**扫描; 单测 `1055 passed` 不变; 浏览器冒烟拆分前后各跑一遍均 **54 项 0 失败**。
- WEB UI 操作跟手性优化 (2026-09-19, 三波次全部入库): 用户报「WEBUI 操作不跟手」。**不直接猜优化点**, 先把一次「右键种子 → 暂停」拆成五段逐段回源码找常量: 入队 1~5ms → **等主循环 main_tick 0~2s** → qB 调用 10~300ms → **`waitCmd` 先睡 500ms 才首查** → 等下轮 sync + 下轮轮询 0~4s, 合计 **0.5~6.5s 且中间零反馈**。据此判定 **主因是"沉默"不是"慢"** ⇒ 收益最大的一项是**乐观 UI**, 后端加速只负责把真值对齐压到百毫秒级; 并实测排除"视图重建太慢"这个假嫌疑(3000 种子重建四视图仅 79ms)。
  **波次一 `10e06a8`**: 分层节拍(同步线 `sync_interval=1.5s` / 任务线 `main_tick=2s`, tracker 预取与搜索索引**不跟快档**)、P0-1 命令唤醒(`wake()` 只触发消费命令、**自投递命令不唤醒**否则自激循环)、P0-5 命令后整批补**一次完整** `_refresh_torrents()`(绝不单独 `apply_sync`, 那会留下半刷新态)、P0-0 埋点(回执 `wait_ms`/`exec_ms` + 前端 `renderMs`)、P0-2 首查退避(0→150→300→500)、P0-3 乐观 UI(pause/resume 白名单 + 3s 回落 + 失败立即回滚)、P0-4 批量合单(走 `/api/torrents/bulk`)。基线 1041 → **1046 passed**。
  **波次二 `5d1e52c`**: P1-5 qB 客户端加请求超时 `(3, 10)`(此前**完全没超时** ⇒ qB 假死时主循环被占住、连重连退避都跑不起来)、P1-1 `/api/state?view=` 按视图回传(前端赋值须"键不存在则保留原引用", 否则另两个视图每轮被抹空)、P1-4 只读端点 TTL 缓存(**断连检查必须在查缓存之前** + **写后失效**两条硬约束)、P1-3 `updated()` 去布局抖动(ResizeObserver + rAF)。基线 → **1049 passed**。
  **波次三 `366092d`**: P1-2 行窗口化 —— **逐行测高 + 前缀和 + 二分**(真实数据 43.7px 与 65.4px 混排, 等高假设会漂 218px ⇒ 滚到底够不着), 上下 `.row-pad` 占位只减 DOM 行数不改布局模型(`:nth-child` 列对齐与 `[data-table]` 保持有效), 展开分组时退避回全量; 顺手拆掉 `filteredTorrents` 的 `{ ...r, hit }` 复制(**单这一句 68ms**, 74 字段 × 3000 条 = 22 万次响应式 `get` 陷阱)。**实测(3000 种子, A/B 同进程 3 轮)**: DOM 行 3000 → 26, 滚动总高逐像素相同且末行可达, 整轮 refresh **1675 → 309ms**, 长任务 240~350ms/轮 → 0, `filteredTorrents` 115ms → 5ms。
  **顺带产出(长期有效)**: 浏览器冒烟脚本化 —— `scripts/ui_harness.py`(真 `create_app` + `FakeClient` + 合成种子 + 命令泵) + `scripts/ui_smoke.cjs`(Playwright, 双 UI 28 项断言 + 内置 A/B 基准), 攻破了"Windows 上没法做浏览器冒烟"这个长期卡点, 把 P0-3 回滚 / P1-1 视图切换 / P1-3 强制布局 / P1-2 滚动跳动这类"pytest 全绿但界面废掉"的故障挡在提交前。基线 **1049 passed / 覆盖 92%** 不变。
  **收尾一步**: 前端轮询按种子量分档 —— ≤1000 → 1.5s / 1000~3000 → 2s / >3000 → 3s。档位由实测单轮
  refresh 耗时(1000:143ms / 3000:353ms / 5000:~550ms)按"主线程占用率 ≈15%"反推, **下界 1.5s =
  服务端 `sync_interval`**(再快只是多拿一次"版本未变"的空响应)。`pollSec` 字段退役改 `basePollMs()`;
  冒烟新增分档断言 ⇒ 30 项 0 失败, 三档逐个实测通过。
  **2026-09-19 对抗性复核 (计划本身 + 实施情况, 重点 BUG/安全/性能)**: 报表
  [docs/plans/26-09-19-1745-webui-responsiveness-review.html](../docs/plans/26-09-19-1745-webui-responsiveness-review.html)。
  评级 计划 A− / 实施 A− / BUG B / 安全 A− / 性能 B+ / 测试 B−。**架构判断成立且实测坐实**:
  命令延迟 `wait_ms=0` / 首查即命中 / 端到端 2.7~34ms; 行窗口化 A/B 同进程 3 轮 —— refresh
  1384→244ms(prism) / 1569→246ms(atlas), `getBoundingClientRect` 9000→106, DOM 行 3000→26。
  **但查出 6 个缺陷 (1 高 2 中 3 低)**: ①**高** `ROW_WIN_GAP=6` 是硬编码常量, 而棱镜
  `.group-table { gap:5px }`(星图 6px)、`.detail` 是**块容器**(gap 0)⇒ 窗口化占位总高比全量
  **多 2973px**(棱镜 167043 vs 全量 164070; 星图 0)。自洽性尚在(占位与滚动数学用同一把"虚拟尺",
  末行仍可达、无空白洞), 但滚动条长度失真。②**中** 乐观 UI 只覆盖种子行 —— 分组行不 patch
  `g.status.primary` 也不加 `is-pending`, `actEpisode` 批量路径**根本没调** `applyOptimistic`。
  ③**中** `_drain_web_commands` 里回执先写、`_web_write_seq += 1` 在后 ⇒ 窗口内并发读会拿到
  写前缓存。另 3 低: `sync_interval` 帮助文案称"大于主循环间隔时按主循环间隔生效"但 `run()`
  **没有任何 clamp**; `_cached_read` 的 `fn()` 在锁外调用(惊群)+ 超 128 条整表清空;
  `web_view.py` 静态守卫是"正则扫源码"而非行为断言。**测试缺口 3 项**: 冒烟的高度基线读数
  时机错(`before` 在 `bench()` 恢复 `rowWin=true` 之后取 ⇒ 实际是"窗口化 vs 窗口化", 提交信息里
  "167043 → 167043" 两个都是窗口化值, 这正是 BUG-1 溜过冒烟的原因); 无任何用例断言
  `_web_write_seq` 自增; `ui_harness.py --host` 可绑 0.0.0.0 且带 `skip_local_verify`。
  **计划外实测数字**: `/api/state` 全量 6 405 735 B / group 1 746 319(27%) / torrent 4 524 992
  (**71%**) / show 134 808(2%) ⇒ 计划里"≤200KB"的验收口径在种子页差 ~22 倍,**P1-1 的实际收益
  主要在分组页**; 另发现固定 `sync_interval=1.5s` 与前端分档轮询(1.5/2/3s)在 >3000 种子时错配,
  约一半 `rebuild_views` 白做。**未改任何源码**, 修复清单 9 项待排期。
  **复核缺陷修复 · 第 1 批 (报表 1~4 + 8~9, 已实施未提交)**: ①**行窗口间距改运行时实测** —— 新增
  `_winGapOf/_winGapFor` 读 `getComputedStyle(container).rowGap`(块级容器 `normal`→0, 三层各存一份),
  删掉硬编码的 `ROW_WIN_GAP=6`; 修前 prism 占位总高 +2973px, 修后 **prism 164070==164070 / atlas
  167071==167071 (Δ0)**。②**冒烟断言改同帧「窗口化 vs 全量」对照**(新增 1 项 ⇒ 34 → **36 项 0 失败**),
  这个断言当场抓出了修复第一版的坑: 实测值在"容器未渲染"时被缓存成兜底 0 ⇒ 总高反而少 14855px ——
  「读一次就缓存」必须分清"值真是这个"与"现在读不到", 已入 pitfalls。③**补两条写序号接线断言**
  (`test_drain_web_commands_bumps_write_seq` + `..._before_writing_receipt`, 后者**红绿双验**: 旧顺序报
  "实际 0 vs 期望 1") —— 此前全仓只测缓存机制不测接线。④**回执与失效顺序调换**(先失效缓存再宣布成功)。
  ⑤**`sync_interval` 落实钳制** `min(sync_interval, main_tick)` —— 文案承诺此前是空话, 而 `_task_line`
  **不拉快照**, 配 5s 会让快照新鲜度掉到心跳之下。⑥**文档漂移清理**(窗口化头部注释仍是"行高必须齐"
  那稿被推翻的口径 / `renderMs` 警告仍写"需 P1 行窗口化" / 3 处测试计划重复行 / `web_commands.py`
  指向**不存在**的 `tests/test_web_commands.py`)。⑦**harness 限回环**(免鉴权服务绑 0.0.0.0 = 暴露给
  整个局域网, 实测非回环一律拒绝启动)。⑧**`cmdStats` 接上消费者**(超阈值打 `[perf]`, 此前只写不读的死字段)。
  ⑨顺带把 `memberWin` 改方法并接收成员数组, 修掉追剧页成员窗口是**死路径**的问题(原写死读 `expandedGroup`)。
  **基线 1049 → 1051 passed / cov 92%**。
  剩: 真机走查(真实 qB 数据下的观感) + 复核缺陷修复第 2 批(组行乐观 / 响应体裁剪 / 节拍对齐)。计划 [docs/plans/26-09-19-1241-webui-responsiveness-plan.html](../docs/plans/26-09-19-1241-webui-responsiveness-plan.html); 档案 [tasks/26-09-19-webui-responsiveness.md](tasks/26-09-19-webui-responsiveness.md)
  **复核缺陷修复 · 第 2 批 (报表 5 + 修复过程中新发现的 3 个缺陷, 已实施未提交)**: 开工先做了一次
  **真浏览器实证**, 结果推翻了报表自己的一条判断 —— 组行颜色**本来就是乐观变化的**(实测
  `s-checking → s-paused`, 因为它取自 `_aggStatus(成员 kind)` 的 computed, 而 `applyOptimistic` 改的正是
  成员 `kind`), 真正缺的只有 `is-pending` 绑定; 集行则确实完全没有乐观调用。据此把「组行」的工作量
  从"加一套补丁表"缩到"加一个绑定", 并顺手发现 3 个报表漏报的缺陷:
  ① **BUG-8(高)** `VIEW_ARRAYS["show"]` 只回 `shows`, 而 `shows[].members` 只是一串 hash、前端要靠
  `memberByHash`(groups+singles 拼出来)还原成成员对象 ⇒ **刷新后停在追剧页得到永久空表**(实测
  `groups=0 / memberByHash=0 / 0 行`), 且 `lastRid` 已记住 ⇒ 每轮都"版本未变不回传", **自己不会恢复**。
  修法 `("shows", "groups", "singles")`(仍不回 4.5MB 的 `torrents`); 响应体实测 134 808 → **1 880 935 B**
  (全量 6 405 735) —— 报表当初量到 134KB 却没问"这份响应够不够把页面渲染出来"。同时暴露出冒烟里
  一条**恒真断言**(`epRows >= 0`), 所以 34 项全绿也没拦住。② **BUG-9(中)** `magnet_uri` 只在平铺
  SEED_ITEM 里, 而 `memberByHash` 先无条件注册 groups、再用 `if (!map.has())` 注册 singles/torrents
  ⇒ 平铺数组**永远当不上兜底**, 索引条目恒无 magnet ⇒ 右键"复制磁力"**100% 失败**且提示误导
  ("该种子没有 magnet 链接")。改为点击时按需取详情(复用 `_editDetail`), **不给每轮响应体加字段**。
  ③ **BUG-7(低)** 同一概念两张状态优先级表: 后端 `_SHOW_STATE_RANK`(追剧页集行) vs 前端
  `decoratedGroups` 内联表(辅种页组行), 六种混合态里 **2 种结论相反** ⇒ 同一批种子两页不同色, 且
  乐观 UI 有"颜色弹回"风险。前端抽 `STATE_RANK` 单点表并对齐后端顺序(可见变化仅那 2 种混合态)。
  **BUG-3 落地**: 组行绑 `is-pending`(`isGroupPending`, 用 `pendingAny` computed 做 O(1) 短路);
  集行新增 `epState(e)` —— `e.state` 是后端回传的**标量拷贝**, 成员被补丁改过也不动, 故有成员在飞时
  按同一张 `STATE_RANK` 表现算; `actEpisode` 的 pause/resume 分支接入 `applyOptimistic`/`resolveOptimistic`
  (失败回滚)。**顺带修掉冒烟自身的 3 处缺陷**: 恒真断言、error 模式恒红(按模式分流为"覆盖全部目标"/
  "回滚干净")、以及 **`FakeTorrent` 缺 `to_dict()` 导致 `/api/torrents/{hash}` 恒 500** ⇒ 详情抽屉与
  四个编辑对话框在冒烟里**从未被跑过**(静默 500, 只有把 console.error 当判据才暴露)。
  **验证**: 单测 **1051 → 1052 passed / cov 92%**(新增 `test_ensure_group_state_show_view_carries_member_index`
  + 静态守阵第 8 项比对两张状态表 + 改写 `test_api_state_view_scoped_payload` 口径, 两条守阵**红绿双验**);
  冒烟 **36 → 46 项 0 失败**(ok 模式) / **44 项 0 失败**(error 模式回滚路径, 该模式此前必红所以没人跑)。
  未做: 报表 §08 第 6 项(响应体裁剪, 牵动 SEED_ITEM 契约)与第 7 项(节拍对齐, 需先定方向)。报表已追加
  [§10 复核修订与修复回执](../docs/plans/26-09-19-1745-webui-responsiveness-review.html)(含对 BUG-3 证据②的更正)。
  **续查 · 热路径白跑 85%: FastAPI `jsonable_encoder` (同日, 已实施未提交)**: 动手做第 6 项前先把
  「一轮 refresh 到底花在哪」量清楚 —— 量完发现**第 6 项要修的地方修错了**。四步定位(每步独立否决一个方向):
  ① **字节构成**: 3000 种子/74 字段里占比最大的 `magnet_uri` 仅 **6.3%**, 要覆盖 80% 字节需要 **52/74** 个字段
  ⇒ **字段裁剪是死路**(真裁掉一半字段也省不到 30%, 还要重走 SEED_ITEM 契约);
  ② **客户端拆分**(浏览器内): 单轮 237 ms = 网络+读文本 **224 ms** + `JSON.parse` **4.1 ms** + 赋值+patch **8.3 ms**
  ⇒ 前端只占 10 ms, 95% 是"在等服务端";
  ③ **网络对照**: 同尺寸 5.12 MiB JSON 走 uvicorn+StaticFiles 只要 **1.6 ms**(`http.server` 1.0 ms)
  ⇒ 排除网络与 uvicorn, **gzip 也无意义**(没有可省的东西);
  ④ **服务端端点内耗时**(加 5 行计时中间件): `view=torrent` **189 ms**, 而应用层可解释的只有 `json.dumps`
  25~50 ms(该轮未重建视图)⇒ 缺口 ~160 ms 在 FastAPI 响应管线里。
  **真因**: FastAPI 对**普通 dict 返回值**会先跑 `jsonable_encoder` **递归遍历整个响应体**(3000×74 = 22 万个值,
  实测 **161 ms**, 占端点耗时 **85%**), 而我们的视图本来就是 JSON 原生类型 ⇒ 纯白跑, 且**全程占着 GIL**
  (与主循环抢 CPU, 是大库下"点了没反应"的一个真实来源)。
  **修法(1 行)**: `web.py` 的 `/api/state` 与 `/api/groups` 改 `return JSONResponse(content=payload)` ——
  `fastapi/routing.py` 有 `if isinstance(raw_response, Response): response = raw_response` 直接短路,
  跳过整个 `serialize_response`。**实测**: 服务端 `view=torrent` 189 → **23.5 ms**(8.0×)、
  `view=show` 79.6 → **11.6 ms**(6.9×); **前端整轮 refresh 跟着掉**: prism 窗口化 239/233/234 → **95/84/84 ms**、
  atlas 268/266/267 → **74/83/83 ms**(整轮本来就在等服务端)。**输出零变化**: 新旧服务并排取
  torrent/group/show/full 四份响应, 字节长度全同(4 764 992 / 1 746 319 / 1 880 935 / 6 645 735),
  解析后除自增的 `rid` 外完全相同。**代价**: 日后往 payload 塞非 JSON 原生类型会直接 500(fail-fast)。
  **守阵**: `test_web.py::test_api_state_skips_jsonable_encoder` 用**计数替身**包住
  `fastapi.routing.jsonable_encoder`, 断言三个热路径调用次数为 0(**刻意用计数不用计时** —— 计时在 CI 不可靠;
  红绿双验: 注入 `return payload` → 报"走了 jsonable_encoder(1 次)")。**基线 1052 → 1053 passed / cov 92%**;
  冒烟 **46 项 0 失败**。**教训入 pitfalls**: 「载荷大」不等于「要裁字段」—— 只说明有开销, 不说明开销在哪;
  凭载荷大小直接开药方十有八九修错地方。同类端点(`/api/torrents/{hash}/files`、`/api/search` 等)同样的
  1 行改法**尚未做**(用户触发型、不在轮询路径上)。报表已追加 **§11**。
  **真机走查反馈 · 乐观 UI 反应 2-4s (2026-09-19, 已入库 `a8eb6e8`)**: 用户真机反馈「乐观 UI 已生效, 但反应
  时间太长, 估计 2-4 秒」([issue 26-09-19-1939](issues/26-09-19-1939-perf-webui-optimistic-latency.html))。
  **先量后改**: 桩服务回执是瞬时的, 本地复现不出来 —— 用 Playwright `page.route` 给命令 POST **注入人为
  延迟**, 钩住 `applyOptimistic` 量三个时刻(菜单项 click → 补丁贴上 → DOM `.is-pending`)。结果:
  注入 2000ms 时 `act()`(整组)补丁 **2012ms** / `actTorrent()`(单种子)**2004ms** 才贴, 而 `actEpisode()`
  (补丁先贴)恒 **0ms** 自带对照 ⇒ **POST 慢多少, 反馈就晚多少(1:1)**。
  **修法(方案 A + B)**: ①`act()`/`actTorrent()` 的 `applyOptimistic()` **提到 POST 之前**(与 `actEpisode`/bulk
  统一), POST 抛错时显式 `resolveOptimistic(hashes, false)` 回滚(补丁提前后这条路径才第一次真正存在);
  ②**3s 兜底改从「回执到达」起算**(成功时刷 `op.ts`), 否则慢 POST 会在命令刚完成时烧光窗口 ⇒ 弹回陈旧真值
  再等下一轮(hang 不刷新, 照旧 3s 回落); ③补埋点 `_newCmdStats/_markCmdPatch/_markCmdPost`, 把
  「点击→补丁」「点击→POST 返回」写进 `cmdStats`(`waitCmd` 由替换改合并), `[perf]` 阈值扩为
  补丁>50 / POST>400 / 排队>100 / 端到端>400 —— 这两段此前是**盲区**(只能靠用户肉眼报)。
  **验证**: 复测注入 2000ms → 补丁 **0ms**; 单测 **1053 passed** 不变; 冒烟 **46 → 48 项 0 失败**
  (新增「P0-3 补丁先于 POST(注入 800ms 仍 <400ms)」, 实测 4~5ms; error 模式加「慢投递 + 失败回执后
  回滚干净」)。**未追**: 真机 POST 为何慢到秒级(长 tick / GIL / 线程池)—— UI 已不依赖它, 复测看
  `[perf] … POST xxxms`, 持续 >400ms 再动服务端。
  **顺带发现另立 issue(未修)**: [整剧操作在剧行上无 `is-pending`](issues/26-09-19-1959-bug-webui-show-row-no-pending.html)
  —— 补丁 0ms 贴上但 `.show-row` 不绑 pending(剧行默认折叠), 与 BUG-3 同类的漏绑。
- **真机复测反馈 · 「乐观后 2-4s 才恢复正常」(2026-09-19, 已入库 `32f531d`)**: 上一条修的是「点击 → 变灰」,
  用户实际报的是**第二段**「变灰 → 真值」([issue 26-09-19-2024](issues/26-09-19-2024-bug-webui-truth-convergence.html))。
  根因: `systemPatterns` 写的「真值匹配即清」**从未实现**(只有 3s 超时与失败回滚两个出口) + 回执后
  **不刷新**、真值要等下一轮轮询(>3000 种子 3s)。**修法 A+B1**: `refresh()` 里 `_snapshotTruth()`
  记本轮 payload 原始值 ⇒ `reapplyPending()` 比它、对齐即清; 回执成功后 `_pullTruthAfterCmd()`
  立即 refresh + 200→400ms 退避重试(窗口 1.5s, 超时仍 3s 兜底)。**验收入库前必做的一步**:
  给 `ui_harness.py` 加 `_apply_truth()`(pause/resume 真改 `tor.state` 并 `rebuild_views()`),
  且**先回执后改状态**(+120ms)复刻真机"补刷新在回执之后"的错位 —— 否则任何"何时消失"的断言
  都只测到"走满 3s"。❗**踩坑**: 第一版判定拿"行上的当前值"比 ⇒ **被自己的补丁骗了**
  (`updated===false` 时行对象没被换掉), 22ms 就假清除, 连"落回的是真值(s-paused)"都照样 PASS
  ⇒ 断言改为**带下界**(80~1000ms)才抓得住。**实测**: 清除 28ms(假) → **272ms**(真); 冒烟双 UI
  **54 项 0 失败**(ok, 真值落回 259~267ms / 组行 239~248ms / 集行 316~319ms)、error **54 项 0 失败**
  (失败立即回滚 21~22ms; 单 UI 各 27 项 —— 与「剧行 is-pending + 节拍对齐」两笔合流后重测);
  单测 **1054 passed**(基线随新增守阵从 1053 上移); 红绿双验 22ms 红 / 263ms 绿。
  ⚠ 合流时撞到一次**窗口化副作用**: 前面的块批量暂停 60 个种子 + 整剧暂停, 窗口内 26 行组行
  **全是 s-paused** ⇒ 「整组乐观」报"找不到可暂停的组行"(prism 过、atlas 挂, 只因窗口落点不同)。
  已把该块的选行改为 `pausableRow(…, "开始整组")`(带"全暂停了就先恢复一行"的兜底)。
  **未走**: 方案 B2(把回执推迟到服务端补刷新之后)—— 它会让"已执行"提示晚 0.2~1s, 属产品取舍未拍板。
- WEB UI 追剧页 剧/集右键「打开目标文件夹」报"种子不存在" (2026-09-19, 已入库 `c888fba`): 用户报追剧页**剧右键与集右键**失败, 种子右键正常。**真因**: 后端 shows 视图的 `members` 是 **hash 数组**, 前端 `decoratedShows` 把它换成**成员对象**, 而 `openShowEpMenu`/`openShowMenu` 直接把 members 当 hash 用 ⇒ 拼进 URL/JSON 时字符串化成 `[object Object]` ⇒ 后端 404。**同一根因还让整集/整剧的开始/暂停/强制汇报报 Not Found、删除静默无反应**(用户尚未察觉)。**修法**: `shared/app.js` 新增 `memberHashesOf(list)`(两种形态都收)统一取 hash, 菜单与选中态(`_showHashes`/`_epUnits`/`epSelState`)一律走它; 双 UI 共用该文件 ⇒ 一次修两处。**验证**: 用 node 桩掉 `Vue.createApp`/`window`/`document` 直接加载**真 app.js** 断言产出是字符串 hash —— 新版 9/9 通过, 旧版挂 5 项(**红绿双验**); 守阵固化进 `tests/test_web.py::test_frontend_static_bundle_health` 第 7 项; 端到端冒烟(桩服务 + 无头浏览器)同样红绿验证。基线 1041 不变。
- WEB 跳过本地验证日志降为 INFO (2026-09-18, 已入库 `7ce54e9`): `web.py` 里"本机免密钥放行"提示原为 `logger.warning` ⇒ 改 `logger.info`(免鉴权是用户**显式开的配置**而非异常, WARNING 会经 notify 推送扰民); 变量 `_local_skip_warned` → `_local_skip_logged` 对齐; `test_web.py::test_skip_local_verify_loopback_bypass` 断言同步改为 INFO 级 + 断言不再产生 WARNING。
- 导出 .torrent 中文名 500 已修 (2026-09-17, 已入库 `4de0953`): `/api/torrents/{hash}/export` 把种子名直拼进 `Content-Disposition`, 而 HTTP 头只能 latin-1 ⇒ 中文名触发 `UnicodeEncodeError` 500。修法: 新增 `web.content_disposition(filename, fallback, ext)` 双段头(`filename=` ASCII 回退 + `filename*=UTF-8''<百分号编码>`)并清洗控制字符; 测试 `test_content_disposition_encoding` + 导出端点非 ASCII 用例。
- UI 组件库 20 式 · 设计风格库落地为可挑选的组件库 (2026-09-17, 已入库 `fae019a`): 按设计哲学风格库 5 流派 × 20 preset 各出一套自包含组件库单页 + 挑选索引 + 目录 README(`resources/ui-component-libraries/modelscope.dsv4.1flash/`); 四轮自检(文本层/渲染层/功能探针/390px 断点)+ 7 项缺陷修复; 基线 996 passed。剩用户挑选与按需迭代。
- 追剧视图 (tvshows) (2026-09-15, 已合入 develop): 剧/季/集解析 + 缺集计算 + atlas 三态视图。遗留: **prism 模板欠账**(棱镜侧追剧模板未做)。
- Memory Bank 任务档案命名重构 · 去序号化与索引生成化 (2026-09-18): `tasks/TASKnnn-<slug>.md` → `tasks/YY-MM-DD-<slug>.md`。**动因**: 全局单调序号在 9 个并行 worktree 下必然撞号 —— 实测 TASK014/TASK015 同一专题两份且 md5 一致、zcode 分支把同一提交 `fae019a` 编成 TASK012 而主线编成 TASK014(**同题异号**)。**方案**: 文件名 = 日期到天(不带时分) + 专题 slug, 由专题派生而非发号; 同日同专题必然撞同一路径, 重复当场暴露为显式 add/add 冲突; 跨天同专题由新增守卫 `test_slug_is_unique_ignoring_date_prefix`(比对时忽略日期前缀)拦下。**索引生成化**: 新增 `scripts/gen_tasks_index.py` 扫 `Status` / `Summary` / 标题按四状态分区生成(分区内按 `Updated` 倒序, 活跃度不靠创建日), `_index.md` 降级为**生成物**, 合并冲突只需重跑脚本; 新增守卫 `test_index_is_regenerated` 保证没人手改。**迁移**: 17 个档案 `git mv` 改名 + 补 `**Summary:**`(摘要由旧索引迁入) 与 `**Legacy-ID:**`(旧号回溯) + 标题行同步; 全仓 9 个文件的路径引用同步修正(只改路径, 历史叙述中的旧编号保留, 靠 Legacy-ID 回溯)。**规范同步**: 两份 `SKILL.md`(`.agents` / `.codebuddy`)、`AGENTS.md`、`.github/copilot-instructions.md`、`.github/instructions/memory-bank.instructions.md`、`memory-bank/README.md`。**基线 1021 → 1022 passed / 0 failed**。计划 [docs/plans/26-09-18-1928-memory-bank-task-id-plan.html](../docs/plans/26-09-18-1928-memory-bank-task-id-plan.html); 阶段 3(把三个 `webui-fix-roundN` 合并为一份 `webui-polish`)按计划默认**未做**
- WEB UI 视图重建范围收口 · 种子速度刷新滞后修复 (2026-09-18): 用户报"WEBUI 种子的下载/上传速度更新慢, 但状态栏速度更新正常"。**根因(探针确定性复现)**: `qbmanager._tick` 与 `web_view.ensure_group_view` 是两条重建路径, 共享同一个 `_group_view_dirty`, 但主循环**只**重建 `_group_view` 就把标记清掉 ⇒ `_singles_view`/`_shows_view`/`_flat_view`(种子页数据源)长期拿不到重建, 版本号却每 tick 自增 ⇒ 前端把陈旧数组整表换上去; 状态栏"速度合计"取 groups 求和故一直新鲜。**同源第二坑**: 置脏语句在 `if grouping.enabled` 块内而 `consume_view_changed()` 在块外 ⇒ 分组关闭时标记被吞(版本号不再变化 ⇒ 前端退避轮询)。**实施**: ①新增 `WebviewMixin.rebuild_views()` 作**唯一重建入口**(四视图 + 版本号 + 清标记一次完成), 主循环与 Web 线程都只调它; ②置脏移出 grouping 门控(脏标记服务全部视图); ③前端 `currentPollMs()` 取消 `idlePolls` 无变化退避(只留失败退避), 并把 `store.server_state` 作为 `status.server` 并入 `/api/state` ⇒ 状态栏与行数据**同源同轮**, 每轮仍 1 条请求。**测试**: 改写 2 条把缺陷固化成预期的用例 + 新增 3 条(含端到端 `test_flat_view_refreshed_by_main_loop_tick`: 主循环 tick 后 Web 请求必须拿到新速度), 全部**红绿验证**; 基线 1018 → **1021 passed / 0 failed**。计划 [docs/plans/26-09-18-1743-webui-speed-refresh-fix-plan.html](../docs/plans/26-09-18-1743-webui-speed-refresh-fix-plan.html); 档案 [tasks/TASK017](tasks/26-09-18-webui-view-rebuild-scope.md); **未提交**
- 副作用普查能力固化进测试 (2026-09-18): 那次普查用的探针是临时脚本(在 `%TEMP%`, 随会话消失), 于是把它固化成常驻守卫 —— 新增 `tests/sidefx.py`(记账器: patch `subprocess.Popen` / `winreg.*` / `os.remove|unlink|rmdir` + `shutil.rmtree` / `os.symlink` / `socket.bind` / `os.startfile`·`os.system`·`webbrowser.open` / `socket.connect`·`create_connection` 七类入口**只记账不阻断**; 放行清单 + `is_violation` 判定) + `tests/conftest.py` 第三道会话级 autouse 夹具(**收尾有越界项即让本次 pytest 失败**, 报告含分类计数与逐条明细) + `tests/test_sidefx.py` 策略单测 10 项。**放行清单**: `node` 子进程 / autostart 的 Run 键与 `auto-qb` 值 / 临时目录内删除与建链 / 回环监听 —— 其余一律越界。**已做反向验证**: 注入一条越界记录后 pytest 退出码 1 并打出明细台账(确认守卫不是摆设), 验证文件用完即删。**细节**: ①`StubRegKey` 放在 `sidefx.py` 而非 conftest, 让记账器能识别"被 AUMID 守卫拦下的调用" ⇒ 两个夹具**安装顺序无关**(否则 AUMID 键一会儿被判越界一会儿不判); ②`is_temp_path` 显式剥掉 Windows `\\?\` 前缀(普查 157 条假阳性的根因, 已有单测锁定); ③模块 docstring 用 raw 字符串以免 `\` 触发 `SyntaxWarning`。**实测 1018 passed / 0 failed**(基线 1007 + 11); 手法与放行清单详见 [pitfalls.md](pitfalls.md) 与 [testing.md](testing.md) 约定 10
- 测试期真实系统副作用普查 (2026-09-18): 通知只是**已知的一种**副作用, 于是写探针把**所有**真实副作用记下来逐类判定 —— patch `subprocess.Popen` / `winreg.*` / `os.remove|unlink|rmdir` + `shutil.rmtree` / `os.symlink` / `socket.bind` 五类入口, 输出**写文件**(写 stderr 会被 pytest 按用例捕获丢弃 ⇒ 假阴性), 跑全量后按类别 `sort | uniq -c` 归类。**结论(全量 1007 项)**: 外部进程 **0**(通知夹具生效); **唯一真问题 = AUMID 注册表键** —— `PlatformChannel("win32")` 构造时会真写 `HKCU\Software\Classes\AppUserModelId\AutoQB.UI` 且**写完不清理**(与 autostart 的 Run 键不同, 后者在 `finally` 里 `disable()` 自清理), 触发用例 `test_notify_legacy_shortcut_cleanup`(同一个文件里另两个构造 win32 渠道的用例都显式 patch 了注册环节 —— 正是"逐用例 patch 容易漏"的实证); 其余全部干净 —— 文件删除 157 条**全在** `C:\TEMP\pytest-of-*`(仓库内 0、仓库外 0)、建符号链接 117 条全是 pytest 自己的 `pytest-current` 与逃逸用例(全在临时目录)、网络监听 161 条全为 `127.0.0.1` 随机端口(`FakeQbServer`)+ 2 条同端口重启复现且自清理。**处置**: `tests/conftest.py` 加**第二道会话级守卫**, 只把 **AUMID 前缀**的 `CreateKeyEx`/`SetValueEx` 变成空操作 —— 静默成功**不抛异常**(`_ensure_appid_registered()` 只 catch `OSError`, 抛异常会让 `channel._appid` 回退成 `WINDOWS_TOAST_APPID_FALLBACK` 打乱既有断言), 替身需支持 `with` 语句; 其余注册表写入放行 ⇒ autostart 的 Run 键测试行为完全不变。**复核**: 全量注册表台账只剩 Run 键(写 + 删), **AUMID 归零**; 1007 passed / 0 failed。**手法坑**: 用 `tempfile.gettempdir()` 做 `abspath` 前缀过滤"临时目录"会被 Windows 长路径前缀 `\\?\` 绕过 ⇒ 157 条"仓库外删除"全是假阳性。手法与结论详见 [pitfalls.md](pitfalls.md)
- 测试期禁止真实系统通知 (2026-09-18): 用户报"测试时会弹出系统通知框"。**主犯**: `test_cli.py::test_main_qb_compat_error_clean_exit` 把 `manager` 设成 `MagicMock` ⇒ `cli.py` 致命退出路径的 `notify_fatal(msg, manager.config.notify)` 拿到**恒真 MagicMock**, 守卫 `if not config or not config.enabled` 放行 ⇒ 真的构造 `PlatformChannel()` 发一条 Windows toast(**诊断探针实测抓到, 标题 `auto-qb 已停止`**)。**从犯**: 测试里写 `PlatformChannel("linux")` 只是换后端, `NotifyHandler` 后台 daemon 线程照样真跑 `notify-send`(装了通知器的机器/CI 上就是真弹)。**两层处置**: ①根源 —— 该用例 mock `auto_qb.cli.notify_fatal` 并断言调用(顺带覆盖"致命退出补发通知"); ②安全网 —— 新增 `tests/conftest.py` 会话级 autouse 夹具, 把通知器命令名(`notify-send`/`osascript`/`powershell`/`pwsh`)拦在 `subprocess.run` 之前(抛 `OSError` = "机器上没装通知器"), `send()` 仍返回 False; 命令**构造**与 `node --check` 等非通知器子进程不受影响。**实测**: 全量真实 send **4 → 0**(win32 1 → 0); 基线 1006 → **1007 passed**(+`test_notify_real_send_blocked_under_pytest`)。**方法论坑(差点误判)**: 探针输出写 stderr 会被 pytest 按用例捕获、通过的用例直接丢弃 ⇒ 统计得 0 的**假阴性**, 必须写**文件**; 且统计一律用 **ASCII 标记**(中文串 grep 会误报 0); **已入库 `7ae21a1`**
- 测试环境假失败清理 (2026-09-18): 全量测试在本机曾有 **2 个稳定失败**, 排查确认都是**环境能力**差异、生产代码无问题。① `test_notify.py::test_notify_legacy_shortcut_cleanup` —— `PlatformChannel._legacy_shortcut_paths()` 在 `APPDATA` 未设时直接返回 `[]`, 用例里 `os.path.exists` 的 monkeypatch 因此从未被问到, `removed` 恒空 ⇒ 补 `monkeypatch.setenv("APPDATA", ...)`(顺带真正覆盖了路径拼接分支, 此前等于空跑); ② `test_web.py::test_api_fs_dirs_endpoint` 第⑤条"符号链接逃逸" —— 本机 `os.symlink(dir, link, target_is_directory=True)` **返回成功却落成真实目录**(实测 `islink=False` / `lstat mode=0o40777`), 根本不存在逃逸链接, 断言无意义 ⇒ 建链后补一道 `os.path.islink()` 判定再断言(与用例原有"Windows 无权限建链 -> 跳过"同口径; 真机能建真链接时照常断言, 覆盖率不减); ③ 顺带修噪声: `.gitignore` 补 `.coverage.*`(原 `.coverage` 是**精确名**不含通配, 覆盖率并行数据 `.coverage.<host>.<pid>.<rand>` 会漏进 `git status`); ④ `test_notify.py` 头部测试计划清单补齐 4 项漏登记(`test_notify_emit_exception_swallowed` / `test_notify_close_twice_safe` / `test_notify_fatal_channel_error_swallowed` / `test_notify_legacy_shortcut_cleanup`)。**实测 1007 passed / 0 failed**(修前 1006 passed + 1 failed); 判据("单跑通过+全量失败" ⇒ 先查环境, 排除环境前不动 `src/`)入 [pitfalls.md](pitfalls.md); **已入库 `7ae21a1`**
- WEB UI 第十二轮·状态色收口 (2026-09-18): 用户两点要求 ——「进度/状态两列文字改状态色」+「暂停的种子状态色还是太白」。①**进度/状态两列文字纳入行状态色**(此前只有名称/数值/文本格子着色, 这两列恒为 `--fg-muted` 灰): `.m-progress .val` 与 `.state-text` 加进既有 `.group-row.s-*` / `.member-row.<kind>` 两组规则(两套 UI 同口径; 特异性 0,3,0~0,4,0 稳胜 `.torrent-row .state-text` 的 0,2,0)。②**星图补齐 FX-06 暂停令牌族**(棱镜第九轮已落地, 星图漏改 ⇒ "还是太白"的真因): 星图 `:root` 新增 `--paused: var(--fg-muted)` / `--paused-soft: transparent` / `--paused-line: var(--border-strong)`(与棱镜 `themes/*.css` 同值), `.k-paused/.k-other` 字色 `--fg-dim` → `--paused`, 并补 `.g-status.k-paused/.k-other`、`.site-chip.paused/.other` 的"**不铺底 + 中性描边**"(原先无修饰符 ⇒ 落回 `--surface-2` 的**白 6% 底**, 即"太白"); `.member-row.paused .m-state`/`.m-site .dot` 同步到 `--paused`。③**paused/other 行文字不再保持默认前景(近白)**: 反转第十轮"整行灰字伤可读性"的取舍 —— 该理由针对更暗的 `--fg-dim`, 改用中性中间调后整行仍可读, "暂停 = 去强调"一眼可见。**双 UI × 六主题(星图 + 棱镜五主题)浏览器截图逐张核对**, 基线 1006 passed(**不变**, 纯 CSS 改动由静态守阵覆盖)
- WEB UI 错误种子显示具体原因 (2026-09-18): 状态列不再只显示笼统「错误」—— `missingFiles` → 「文件丢失」(零 API, 状态自明), `error` → tracker 报错原文(如 `torrent not registered with this tracker`, 过长省略 + `title` 全文)。**前提核实**: qB `torrents/info` **不含**任何错误文本字段, 原因只在 `/torrents/trackers` 的 `msg` ⇒ 只能派生或另取。实现: 后端 `WebviewMixin.refresh_error_reasons` 在**主循环**按 TTL(300s)+单轮预算(5 条)预取, 写进 `TorrentRecord` 的**非快照**缓存槽 `tracker_error_msg`/`tracker_error_ts`(不进 `_SNAPSHOT_FIELDS`/`_raw`), 视图组装**只读缓存**(视图可能每 tick 重建, 不得发 API); 原因非快照字段 ⇒ 变化时由预取方**显式置 `_group_view_dirty`**; `missingFiles` 排除在拉取分支外(原因自明, 且"成片文件丢失"正是最需保住预算的场景); 预取与视图重建/搜索索引同门控(网页关掉不发请求); 断连时保持现值不清空。原因文本**取数单点** `_error_reason`, 视图透出 `error_reason`, 前端 `stateText(m)` 仅错误态采用(双 UI 共用逻辑层, 一处改两套生效; 模板各 4 处状态格 + 两套 CSS 省略规则)。基线 1001 → **1006 passed**(+5 项: tracker msg 提取/缺失文件零 API/预算与 TTL/恢复清空/断连跳过), 假 qB 服务(真实 `create_app`+uvicorn)双 UI DOM 与截图实测; 档案 [tasks/TASK015](tasks/26-09-18-webui-error-reason.md); **已入库 `9723a76`**
- WEB UI 第十一轮修复 (2026-09-17): 7 项 (`想法.md` 待办)。①图标语义色补齐: 导航「追剧」(新挂 `ico-tv`)与「添加种子」(新挂 `ico-add`)、状态栏「空间剩余」(`.ico-disk` 原继承 `--fg-dim` 观感无色 -> indigo)与两处「限制速度」仪表盘(-> `--limit-hit`, "不限速"只弱化数值); ②状态栏历史入口**去文字只留图标**(图标改取 today-up 族色, 否则只剩灰点); ③**明细表接入点击排序** —— 明细与三视图正交, 故新增独立 `detailSortKey/detailSortDir` + `setSort(key,'detail')` scope 分支(表头右键排序项同源), 明细列模型补 `sortable` 标记到 14 列(Hash 除外), 行序由 `sortedMembers(list)` 派生(空键=后端原序, 标签为数组故先 join 再比); ④**保存路径列迁移**: 辅种表新增(组级取首位成员值 = 路径筛选器同口径), 明细表删除(组内成员路径本就一致); ⑤**横向滚动条(三项根因, 两轮才定位)**: `.group-head` 脱离滚动容器 => 表头比 `.content` 宽时把整页撑宽(实测表头写 3000px, `documentElement.scrollWidth` 1872→3012) -> `.content { overflow-x: clip }`(clip 不建滚动容器, sticky 与表头 transform 跟随不受影响); `.detail` 自带 `overflow-x: auto` => 与外层各滚各的 -> 去掉内层滚动; **"列没溢出却常驻横滚条"的真因是单元格自动最小尺寸**(表格层 `white-space: nowrap` + 单元格 `min-width: auto` = 文本全长, 13 列累加把行 `min-content` 顶到容器之上) -> 行内单元格统一 `min-width: 0`, 行/表头保持 `fit-content`(**底色跟内容**); 中途曾用"行定宽 100%"治假滚动条, 但那会让**溢出段没有行底色/边框**(用户实测反馈"滚动后右边无背景条"), 已回退。 ⑥**标签/分类芯片改状态色**(原"分类恒蓝/标签恒灰"无语义且蓝色与"下载中"撞色), 跟随所在行状态语义色, HR 标签用 `:not()` 排除保住橙/青语义。基线 999 passed(**不变**, 前端改动由静态守阵 + 双 UI 浏览器冒烟覆盖), 档案 [tasks/TASK013](tasks/26-09-17-webui-fix-round11.md)
- WEB UI 第十轮修复 (2026-09-17): 16 项 (R10-01~R10-16) 按成因归 7 类实施, 计划 [docs/plans/26-09-17-0901-webui-fix-plan-round10.html](../docs/plans/26-09-17-0901-webui-fix-plan-round10.html)。三条硬 bug: ①**状态栏限速读了不存在的字段名**(前端读 `server_state.dl_limit/up_limit`, qB 真键是 `dl_rate_limit/up_rate_limit`; 该字段还兼作速度染色分母 ⇒ 色阶从未生效) -> `speedLimitBytes` 取数单点, 状态栏与染色分母同源; ②**星图点一次限速开两个窗口**(`.speed-pop` 与 SPD-04 旧模态共用 `speedOpen`, 第九轮漏删星图) -> 删旧模态 + 静态断言; ③**本机免鉴权仍被弹回密钥页**(前端把"有身份"绑死"密钥串非空") -> `authMode`/`authOk` 单点判据 + 不带空 Bearer。结构性: **列对齐进列模型**(`align` + `colAlignCss` 按可见列生成 `:nth-child` 规则注入 `<head>`, `data-table` 标记表头与值, 一处改两套生效; `:where()` 压特异性以保留既有"0 值居中")与**列偏好不再重置**(跨版本迁移 `LEGACY_COLS_KEYS` + 不再用升版本应对列集变更 + 写盘容错; origin 隔离作为限制入 pitfalls)。服务端新增能力: `/api/fs/dirs`(只列目录, 允许根白名单 + realpath 边界 + 符号链接逃逸防护) 与 `/api/fs/mkdir`(单层名字 + 幂等 + 同名文件 409), `open-path` 对单文件种子改为**定位选中**; 前端新增服务端目录浏览器对话框替代自绘下拉。其余: 状态栏底色专用令牌 `--statusbar-bg` + 去文字标签 + 历史入口并入今日流量组、选中态令牌族 `--sel-*`(五主题靖蓝族, 与做种绿分家)、文本列(站数/保存路径/hash/tracker)加入行状态色、弹窗尺寸令牌族(窄/标准/表单/宽/超宽; 添加窗口两 UI 统一 860px)、值行"单行省略 + title + 复制按钮"、菜单「高级能力」→「更多操作」、抽屉目录/文件分色、删除详情行由 `_deleteDetails` 由目标集合统一派生(四入口同构); 基线 996 → **999 passed**(+open_path 平台用例 + `/api/fs/dirs` + `/api/fs/mkdir`); 双 UI 浏览器冒烟逐项实测通过(假 qB + 临时 data_dir, 完事清理)
- WEB UI 第九轮修复 (2026-09-17): 25 项 (FX-01~FX-25) 按成因归 8 类实施, 计划 [docs/plans/26-09-17-0847-webui-fix-plan-round9.html](../docs/plans/26-09-17-0847-webui-fix-plan-round9.html)。三条公共底座: ①**单元格口径单点化**(做种时长/分享率/用户·做种三列此前在模板里各写三份 -> `cellSeedingTime`/`cellRatio`/`cellPeers`, 两套 UI 共用); ②**浮层锚定契约**(`.add-dialog-pathrow` 缺定位祖先导致面板渲染到视口之外 = "点了没反应"; 退役原生 `<datalist>`; 面板锚点下沉到 `.add-input-row`); ③**暂停态中性令牌族**(五个主题各补 `--paused/--paused-soft/--paused-line`, D8=方案B 无色相)。结构性重构: **选择模型**改"互斥 + 单一权威 + 派生集合"(`selHashSet` 三视图打通 + 半选态 + 追剧页修饰键选择), **删除链**四条入口统一到 `_deleteFlow`(汇报前置 + 等待聚合回执 + 收尾清选择)。其它: 启动鉴权首帧(`bootstrapping` 初值 = 未知)、底部状态栏重排(今日流量 + 复活历史流量入口 + 速度·限速配对 + 无遮罩就近浮层)、右键菜单分层(flyout, 一级只留 PT 高频)、追剧页整剧菜单、添加窗口 760px + 选项胶囊化 + 警告行常驻占位、抽屉常规页重构(分组卡片化 + 图标色调 + 长值块行 + 行内值操作)、列头拖动虚影、文案"分组"→"辅种"(`L10N_GROUP` 单点)。新增后端只读端点 `POST /api/open-path`(路径一律服务端派生, 不接受客户端传路径)。基线 995 → **996 passed**; 浏览器冒烟 25 项全过、0 控制台错误
- Memory Bank 触发机制修复 (2026-09-17): 补建真正的 skill 载体 `.agents/skills/memory-bank/SKILL.md` (会话开始 3 步 / 收尾 DoD 5 步 / 立档阈值 4 条 / 档案规范 / 反模式; 先建于 `.github/skills/`, 同日按仓库技能根惯例搬入 `.agents/skills/`), always-on 入口 (`AGENTS.md` + `.github/copilot-instructions.md` + `ai-lib.md`) 声明**可判定阈值**并指向 skill, `memory-bank.instructions.md` 顶部标注"本文件不负责触发 (applyTo 限定 memory-bank/**)"; 按**专题粒度**回填 `tasks/TASK001`~`TASK010` (30 条历史会话纪要原文按专题归档) 并重写 `_index.md`; `activeContext.md` 68 行 → 26 行 (恢复易变层定位); 新增守卫 `tests/test_memory_bank.py` (6 项, 红绿验证: 幽灵任务与纪要回流两类违例均被拦截); 基线 989 → **995 passed**
- WEB UI 替代 qB 界面 · 波次三 (2026-09-17 收口完成): 32 工作项 (FIX7/TBL8/DLG4/CTX3/SPD4/NAV3/RFB2/PRS1) 全部落地, **星图(atlas)与棱镜(prism)双 UI 同构**。后端: peers 端点修复(`sync_torrent_peers`)/`/api/paths` 已知目录聚合/bulk 组键模式/成员与单种透出 num_seeds·num_leechs·num_complete·num_incomplete/SPD-01 末档 clamp 回归锁定/SPD-03 `global_speed_limit_curve.enabled` 全管线(models+validation+loaders+设置页开关)。前端: 表格层(空值留白与"不限速"文案退役、状态底与七列三档数值色阶、去名称状态图标、列拖动重排+右键列选择器、补列、全宽布局、rail 退役改底部状态栏、批量段并入筛选行)、弹窗(删除确认框加宽+计数语义、添加种子改版与位置选择)、右键(彩色图标集/触发源强调/原生右键屏蔽)、限速(预览末档压缩、点击弹窗修改)、导航 IA(分组/种子/追剧升一级导航、设置右移、统计入状态栏、日志并入设置页、动态 logo)、详情抽屉纯展示重构、设置页重构(栅格令牌化/宽度放开/文案用户化/风险注记统一)。计划 [docs/plans/26-09-16-1128-webui-qb-replace-wave3-plan.html](../docs/plans/26-09-16-1128-webui-qb-replace-wave3-plan.html) + 派工契约 `.cluster/webui-w3/` + 交接 [docs/plans/26-09-17-0346-webui-qb-replace-wave3-handover.html](../docs/plans/26-09-17-0346-webui-qb-replace-wave3-handover.html); 基线 971→**988 passed**; 待人工: 浏览器 CDP 双 UI 走查 + 真机 dry-run。- tracker 分组·站点 groups 字段 + tracker_group 条件 (2026-09-15): 站点段新增可选 groups(字符串列表, 配置层声明不写种子, 组名自由命名无需预定义), 规则条件新增 tracker_group(镜像 TrackersCondition, 或关系, regex:/ignore_case, 无 tracker_conf 恒 False); 校验经 _check_str_list(非列表/纯空白项报错; 空串项被 _strip_none 统一视为未配置剔除, 项目既有约定), spec 校验走 _validate_pattern_list_spec; schema 双登记(TRACKER_FIELDS str_list + CONDITION_PLUGINS, 守卫自动 15→16); 热重载 groups=LEVEL_L2(S0 核实: record.tracker_conf 仅 added 流程绑定一次, L2 reset_runtime 置空重匹配才见新值, 与 domains/rules 同级; L0 会读到旧 conf 对象); Web UI 设置页借 str_list 控件零前端改动即可编辑保存; 测试 +4(test_conditions 条件 2 + test_config 校验/加载 2, helpers.FakeTracker 加 groups 参数), 基线 884 passed; 真机 dry-run 冒烟通过(119 种子同步/规则加载/决策链, 动作被 dry_run 抑制); 计划 docs/plans/26-09-15-1504-tracker-group-plan.html(D1=方案 B 站点字段/D2=tracker_group 已拍板); 后续阶段 2/3 前端: 设置页 groups 下拉快捷追加 + 辅种管理页按组筛选; README(5 处 15→16 种)/docs/configuration.md(示例+条件表)/memory-bank(rule-system 16 条件+config-reference+testing 基线)/想法.md 回写; 已随本提交入库
- TorrentRecord 全字段缓存 (2026-09-15): 快照 21 → 70 字段(必需 21 + 重加升格 6 + 可选扩展 43, 字段定稿参照用户提供的真机 TorrentDictionary 样例 + 真机冒烟补 4 字段), 为 WebUI 后续功能供数; D1-D5 决策见 [docs/plans/26-09-15-1302-record-full-fields-plan.html](../docs/plans/26-09-15-1302-record-full-fields-plan.html): slots 全量声明(_raw 降为前向兼容兜底)/RE_ADD_FIELDS 升格进快照(变化开始计入变化集)/新字段全可选(默认值取 qB 哨兵 -1/-2/8640000, REQUIRED 校验面不变)/缓存≠展示(新字段不进 _VIEW_FIELDS, 视图重建成本零变化, 测试锁死)/哨兵原样透传; 新增 `to_dict()` 全字段导出; 真机只读冒烟(119 种子)响应字段全声明 _raw 无残留; 测试 +9 净 +7, 基线 879 passed; 视图/规则/HR/分组消费字段全在旧集合内零行为变化
- WEB UI 双界面命名与目录化 (2026-09-15): 旧 UI 迁 `atlas/`(星图)、`newui/` 改名 `prism/`(棱镜), 共享逻辑层三件套+vendor+icon 收进 `static/shared/` 单一来源; web.py 加 `/`→307 `/atlas/`(默认 UI)与 `/newui/*`→307 `/prism/*` 书签兼容, 鉴权范围显式限定 `/api/*`(require_token 加 Request 路径判断, 行为等价 —— 原静态免鉴权靠 StaticFiles 不经依赖系统的副作用, 重定向真实路由后必须显式放行); atlas 顶栏切换器类 `.newui-entry`→`.ui-switch`, 互切链接文案改「星图/棱镜」; test_web 静态缓存测试路径更新 + 新增 test_ui_root_and_legacy_newui_redirect; 命名原则沉淀(身份名不代际名/目录名=URL 英文小写/中文两字/成组不撞车); 计划 docs/plans/26-09-15-1241-webui-naming-plan.html
- 依赖管理现代化 (2026-09-15): pyproject.toml(PEP 621 + hatchling, 12 直接依赖 == 锁死含 filelock 3.32.6 / uvicorn 0.53.0 最新, dev 走 PEP 735 依赖组, entry point `auto-qb = auto_qb.cli:main`) + uv.lock 全量锁 41 包 + `uv sync` editable 安装(清除旧壳 venv 与约 20 个无关包); CI 切 astral-sh/setup-uv@v10(enable-cache) + checkout@v6 + setup-python@v7 + uv sync/uv run; `uv build` sdist/wheel 打包就绪; 前置调研 docs/plans/26-09-15-1150-dependency-lock-report.md; requirements-dev.txt 已被 pyproject 取代(随提交删除); README/AGENTS/testing/techContext 同步, 基线 872 passed (uv 环境)
- WEB UI 旧版第八轮优化 (2026-09-15): 吸顶贴合(批量条/表头零缝堆叠, --bulk-h 剔除 margin)、筛选器幽灵空位消除(清除chip 常驻可见降透明)、删除确认框修复+扩容(`_findGroup` 优先查 decoratedGroups 修保存路径恒"—"; 批量删除补成员明细含路径; wide 560→720)、H&R 筛选(达标/未达标)、单种子视图(TORRENT_COLUMNS + 后端 `_build_singles_view` 未归组种子与 groups 同快照同版本门控)、信息栏双模式(左栏↔顶栏紧凑双排条持久化)、令牌中性化视觉刷新; 冒烟 10/10(修复包/筛选/视图/双模式全断言)+ pytest 872 全绿; 计划 docs/plans/26-09-15-1042-webui-optimization-plan-v3.html; 详见 pitfalls 第八轮条目
- WEB UI 新版界面与多主题 (2026-09-15): `newui/` 独立目录并存可切换(`/newui/` 零后端路由, 旧 UI 原样保留仅顶栏 +1 链接, 共享逻辑层单一来源)；令牌化五主题(深海机房/暗夜星云/极地晨霜/麦秋/品牌轨道, data-theme + localStorage + 系统明暗跟随, theme.js 首帧前同步防 FOUC)；Edge headless CDP 冒烟 34/34(双 UI 功能等价/主题切换持久化/五主题 WCAG 对比度全达标/移动宽/无控制台错误), pytest 871 全绿；设计计划见 docs/plans/26-09-15-0956-webui-redesign-plan.html；详见 pitfalls 新版 UI 条目
- 标签/分类管理: 站点标签加/删、相似标签清理、`delete_tags`/`delete_tags_if_has_no_torrents` 全局清理、集数标签
- HR 管理: 触发标签/分类 + satisfied 标签/分类, 站点覆盖全局
- 辅种分组: 增量归组、大小一致性、缺文件事件驱动扫描 (删除/上传转暂停/路径变化)、下载冲突检查
- 规则引擎: interval 触发 + 15 条件 + 12 动作 + execute_once/cooldown 去重 + 断点续跑 + stop_following_rules_if; 事件触发 (interval/on_* 四值 trigger + 事件分派引擎 + rule-event 断点续跑 + on_torrent_deleted 动作白名单 `print_torrent_details`, 2026-09-12 落地, 设计细节见下"事件触发(规则)规划")
- checking 动作: filelist/piecehashes/custom 三种参考判定 + full-checking (异步轮询) + skip-checking (导出→删除→重加, 同日去重+备份)
- tracker 单种限速 (奇数保护)
- 全局限速曲线: Traffic Monitor 数据源, DAY/MONTH/ND 聚合, 全程分档覆盖, 取最严 (2026-09 最近的大功能, commit ee88bc8..20481f3)
- 托盘常驻 UI (2026-09-12, --tray): `ui.py` —— CustomTkinter 深色窗口(状态卡片/最近日志/暂停恢复/通知热切换/开机自启)+ pystray 托盘(6 项菜单, 勾选态实时); 运行时暂停/恢复 = pause_event 完全旁观, 恢复后增量 diff 补上; 双开唤起 = 单实例锁 + localhost IPC(ui.port, 第二实例静默退出 0); 托管模式主循环移入后台线程(单一写线程约束保持), 首连失败重试常驻; GUI 栈仅 tray 分支加载; 通知开关支持从未配置状态热挂载(setup_notify force, 会话级); toast 点击激活唤起窗口(launch_arguments 经 AUMID 快捷方式 Arguments); 窗口图标 CTk iconbitmap 防 CTk 默认覆盖(assets/icon.ico); 打开日志目录前绝对化路径并确保目录存在, 托盘事件单点失败不中断 UI 轮询链; 新依赖 pystray/Pillow/customtkinter
- 主动通知 (2026-09-12): `notify.py` 零第三方依赖 —— NotifyHandler 挂 `auto_qb` logger 复用日志规范, PlatformChannel 按平台分派(win32=PowerShell WinRT toast / linux=notify-send / darwin=osascript), quiet_hours 免打扰(与 date_time 共用 utils.time_in_range) + 每小时上限 + 同键去重窗(内存态); CLI 致命退出补发 notify_fatal; dry-run 不挂载; toast 来源显示 "AutoQB" —— 首次运行幂等注册开始菜单快捷方式 AutoQB.lnk(%APPDATA% Programs 目录, 隐式 AppUserModelID), 注册失败回退 PowerShell 来源
- 任务队列: 单 heapq 队列 + `add_task(keep_progress=...)` 断点语义 + check 轮询在途去重 (12f3b46 重构完成)
- 数据层: TorrentStore 快照+惰性缓存+分组索引; QbApi Facade写后同步
- YAML 导出 (`--export-yaml`, `--only-missing`), qB 5.0 API 适配
- fail-fast 全量配置校验 (2026-09-05): `config.validate_config` 聚合校验未知键/必填项/值格式/规则 spec/引用存在性; 留空(空串/None)走默认值; Rule 构造报错带规则名上下文; `load_*` 解析函数已剥离全部检查(先验证再解析, 解析假定配置正确)
- 单实例锁 (2026-09-05): 基于第三方 `filelock`, 锁文件 `<state_file 去扩展名>.lock` + 伴生 `.meta.json`; 仅正常 `run()` 模式持锁, `--export-yaml` 等只读模式通过 `no_lock=True` 跳过; 失败抛 `SingleInstanceLockError(AutoQbError)`, CLI 单点捕获 AutoQbError 体系干净退出 (退出码 1, stderr 无堆栈); 陈旧锁不接管 (OS 句柄随进程退出自动释放, 必要时手动删除)
- 测试: 基线数字单点维护于 [testing.md](testing.md) 顶部 (2026-09-14 起, 此处不再手抄; ui.py GUI 本体真机冒烟)

## 规划中 (🚧, 尚未实现)

(以下 WEB UI 核心已于 2026-09-13 实现, 见 productContext.md/modules.md; **2026-09-14 已补图形化配置编辑** —— 设置页每项配置均可增删改, 含站点/规则集(15 条件 + 12 动作)/限速曲线的结构化编辑与只读 YAML 预览, 直接编辑模式已移除; 剩余: WebSocket 推送/多用户)

### 规则系统
- ~~触发时机: `on_torrent_added` / `on_torrent_deleted` / `on_torrent_state_enum_changed`~~ — 已实现 (2026-09-12, 落地现状见下"事件触发(规则)规划": 事件分派引擎/断点续跑/测试全部完成)。**注**: 设计已把 `on_torrent_state_changed` 收敛为 `on_torrent_state_enum_changed` (与 `TorrentState` 枚举命名对齐)。
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

## 已知 BUG (来自 想法.md)

- ~~新加的种子无法触发 skip-checking~~ (2026-09-06 已修复): 生产日志实锤 —— 跳检删除→重加同 hash 种子后, `store.remove_torrent` 保留 `_known_hashes` 导致重加种子**不进 added 列表**, 下轮 refresh 重建记录 `tracker_conf=None` 永久未匹配; `log_repr → tracker_name` 回退 `self.tor.client`(真实 TorrentDictionary 无此属性) AttributeError。修复: ①跳检重加成功后恢复删除前快照记录(tracker_conf/惰性缓存保留) ②tracker_name 无 conf 返回 "Unknown"(与 FakeTorrent 对齐, 不再回退 tor.client)
- 复杂限速规则 (tracker+时段组合等)
- 性能: 主循环拆分平滑占用、全面优化 (想法.md 标注) —— **2026-09-14 已修其中一处严重回归**: 非托管模式下主循环完全不节流(空转约 2800 tick/s, 详见 08 陷阱); 其余优化(如 `update_state_snapshot` 增量化)经评估风险大于收益, 暂不做

### 代码内待办 (TODO 清单, 2026-09-09 核对; 位置用函数/方法名锚定, 行号易漂移)
| 位置 | 内容 |
|------|------|
| ~~qbmanager.py `_get_torrent`~~ | 兼容方法已删除, 统一用 `store.get(hash)` |
| ~~rules/base.py 多 tracker 匹配~~ | 已处理 2026-09-05: `_match_tracker_conf` 命中多个打 ERROR 用第一个 |
| ~~rules/base.py HR 判定迁移~~ | 已迁移 2026-09-05: check_hr_* 移至 TorrentRecord, replace_vars 移至 utils |
| ~~rules/conditions.py (tags/category/trackers 三处 `# TODO: 支持:ignore_case`)~~ | 已完成 2026-09-12: 三条件改走 `utils.match_value` 统一匹配, `:ignore_case` 全支持; config 阶段补 regex 可编译校验 |
| ~~recheck 失败冷却~~ | 已实现 2026-09-05: 连续失败3次当日冷却, recheck_fails |
| rules/actions/checking.py `CheckAction.execute` 闸门 0 上方 | 未完成且暂停的种子 recheck 后仍未完成, 下一轮会再次校验 (3 次失败冷却兜底, TODO 未销) |
| rules/actions/checking.py `_find_reference` 上方 | 优化为 `has_reference() -> bool` 提前返回 |
| rules/actions/checking.py 分段执行处 | 重新设计自定义 (custom) 校验流程 |
| ~~mixins/tags.py `_add_hr_tag_or_category`~~ | 已完成 2026-09-12 (commit d987015): HR 条件/satisfied 判定改委托 `TorrentRecord.check_hr_condition/check_hr_satisfied` 单点判定 |
| config/loaders.py `load_global_hr` / `load_tracker_hr` | 函数上方 `# TODO: optimize` |
| ~~reannounce 限频~~ | 已实现 2026-09-05: 运行时最小间隔10M + 加载告警 |
| ~~episodes.py 集数标签格式~~ | 已实现 2026-09-05: add_episode_tags 段 add_tag_single/add_tag_multi 模板 |

## 近期演进脉络 (git log 提炼, 有助于理解"为什么现在是这样")

1. 任务队列驱动重构 (12f3b46, 528 passed) — 双队列合并为单 heapq 队列, `add_task` 断点语义 (keep_progress 续跑/默认重置) 建立
2. 全局限速曲线落地 (ee88bc8 → 20481f3) — SpeedCurveMixin + curves 纯逻辑模块 + qB5.0 transfer 端点适配 (f402eaf)
3. 跳检稳健性 (5ab17c5, e5ea9e7) — 修复删除种子后访问属性/后续任务报错
4. 覆盖率补齐 (6f60a5a) — config/qbapi/qbmanager/logging/cli/tracker/speed_curve 缺口
5. 主循环 × WebUI 解耦 (5691c6f, 1057 passed) — `web_runtime.WebUIRuntime` 门面收走 19 个表现层状态字段
   与全部节拍判据, 主循环只剩 6 条语义调用、不再有 `web_active` 门控; `web_view` 降为纯构建器、
   `web_commands` 降为命令处理器 + 命令表。兼容层(`_WEB_STATE_ALIAS` + 8 个转发)让既有调用零改动,
   由两条守阵看住防回潮。结构改动、行为等价: 冒烟 ok/error 双模式各 48 项 0 失败, 且「3000 目标撤下
   3073ms」经 A/B(改动前 3072/3049ms)证明非本次引入

## 给 AI 的实现建议 (基于现有架构的延伸方向)

- **新触发时机** (`on_torrent_added`): `_refresh_torrents` 的 added 循环已经是事件点; 按 09 事件触发规划, `_dispatch_events` 同步分派 added 事件规则 (不建周期任务), 复用 `_apply_event_rule` + rule-event origin 机制。
- **状态变化触发** (`on_torrent_state_enum_changed`): `store.state_snapshot` 已保存上一轮枚举状态, `_handle_state_transitions` 是现成的"状态转移检测"参考实现 (grouping 内部用); 事件分派用它对比上轮/本轮状态枚举筛选触发。
- **删除触发** (`on_torrent_deleted`): 用 `store.refresh` 返回的 removed 及其删除前快照副本触发; 白名单只允许 `print_torrent_details` 只读留档。
- **新流量源**: `curves.py` 保持无项目内依赖; 数据源解析独立成函数返回 `List[HistoryRow]` 即可复用 aggregate/curve_speed 全链路。

### 工程化 / 知识库（2026-09-20）

- **create-issue skill 类型化改造（已实施）**: 计划 [26-09-20-0941](../docs/plans/26-09-20-0941-issue-typing-plan.html)。
  ① 8 类类型进文件名第二段 `<时间>-<type>-<slug>.html`（bug / perf / docs / test / refactor / feat / chore / question，
  枚举单点在 `scripts/_common.py` 的 `TYPES`）；② 表单分两档 —— `light` 便签（现象一句话 + 位置，≤2 分钟）与
  `standard` 标准（现象 / 证据 / 影响面 / 定位锚点，≤10 分钟），根因与建议修法一律降为可选、默认"待查"；
  ③ 防过期五条（只记事实不记结论 / 行号标"当时"+ 符号 + grep 词 / 不为填单做分析 / 证据标取证时间 / 开工先复验）；
  ④ 通用化 —— meta 去 `aqb-` 前缀改 `issue-*`，目录 `--dir`（不传按 memory-bank/issues → issues → docs/issues 探测）、
  仓库根改 `.git` 向上探测（不再 `parents[4]`）、品牌 `--project` 可选注入、索引 HEADER 链接动态计算；
  ⑤ 存量 8 份报告已迁移（bug 4 / perf 3 / docs 1），17 处外链同步，索引顶部有 Open 按类型计数表。
  文件名与状态取值由生成器守卫（`--check` 可挂 CI）。单测 **1057 passed** 不变。
- **提交推送流水线 skill（已实施，2026-09-20）**: 提案 [26-09-20-1128](../docs/plans/26-09-20-1128-git-ship-skill-proposal.html)，
  落地 `.agents/skills/my-commit-flow/`（七步：预检 → 闸门 → 逐路径暂存 → 提交并核 ref 三处 → 推 Gitee 主线
  → 尝试一次 GitHub 直连 → 查幽灵 diff）。脚本 `preflight.py`（只读预检）/ `commit.py`（逐路径 add + commit，
  **拒 `-A` / `.` / `*` 与红线文件**）/ `verify_ref.py`（ref 三处一致）/ `push.py`（先 fetch → 推主线 → 核对远端
  → 镜像直连只尝试一次），配置单点 `scripts/_ship_config.py`。
  停手点：rebase / 混入他人在途改动 / staged > 200 / ref 不一致 / 镜像失败 / 闸门未过 —— 脚本只报不碰。
  已回写指针：AGENTS.md 提交节 + 环境硬约束 + 路由表、memory-bank/README.md 路由表、memory-bank skill 会话开始第 1 步。
  **通用性有限**（依赖本仓环境：工具 shell 拦截层 / Gitee+GitHub 双远端 / 9 worktree 并行），换项目先改 `_ship_config.py`。
  提交 `0c0bf1e`，用它自己的流水线提交（dogfooding），Gitee 与 GitHub 均推成功。
