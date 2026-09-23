# WEB UI 长叙事留档

> 摘要: 4 条 WEB UI 优化/修复的**原始详述** —— 首行与结论留在 [implemented-webui.md](../implemented-webui.md), 这里是被压掉的叙事部分。
> 触发: 跟手性, 乐观 UI, 轮询节拍, 筛选器, 视图重建, 替代 qB 界面, 长叙事

> 迁移说明(2026-09-22 W4): 这 4 条合计 ~15 KB, 逐条单拎出来都超 10 KB 的主题文件 cap ⇒
> 按「超了就外迁」把它们的过程叙事移到这里, **内容逐字未改**。


---

## 原「已实现」第 4 条

- 种子页筛选器无数据 + 辅种组暂停后状态色闪烁修复 (2026-09-21): 用户一次报两个 WEB UI 缺陷, 两个都**先复现再改**。
  · **① 种子页筛选器无数据**: 筛选弹层选项(标签/分类/站点/路径)原先一律遍历 `groups` 计算, 而种子页按视图分片**不回 `groups`**(`VIEW_ARRAYS["torrent"]=("torrents",)`) ⇒ 四个弹层恒空、只剩"暂无数据"(H&R 是固定两档, 表现为 0/0, 更隐蔽)。**这是"跨视图的常驻消费者依赖按视图裁剪的阵列"的第三次**(前两次: 状态栏速度 issue 26-09-20-1646 / 追剧页成员索引 BUG-8)。修法 = **取数面单点** `facetRows`(种子页=`torrents`, 其余=`decoratedGroups`) + `_facetOptions(kind)`; 计数口径随行走(**组视图=含该值的组数, 种子页=含该值的种子数**), 旧的 `_memberValueOptions`(按组算的第二条口径)删除并由守阵钉住不许复活。实测(桩 300 种子): 组视图计数不变(150 组), 种子页标签/分类/站点/路径 3/3/1/1 条且与 `vm.torrents` 现数的真值逐项相等(HHan 150 / seed-3D 150 / low-ratio 148 / 站点 300 / 路径 300), 点选 HHan 行数 300 → 150。
  · **② 辅种组暂停整组后颜色 灰→绿→灰**: 真值走 `torrents/info` **直查**, 比我们自己的 `/sync/maindata` **快照**新 ≤ `sync_interval`(1.5s); `onTruthEvent` 一到就 `delete pendingOps[h]`(撤掉"值覆盖") ⇒ 这 1.5s 内任何一次**视图发布**(任何种子任何字段变化都会让 rid 前进、整表重发)都带着**命令前**的 kind 覆盖行对象 ⇒ 行被打回命令前的做种绿, 快照追上再变灰。修法 = 真值事件**只改覆盖的值**(`op.patch`/`op.prev` 都写成已落地真值, resume 的"落地态 6 种 vs 预测 2 种"顺带收敛), **不结束覆盖** —— 收尾判据保持"服务端快照同意"(`_optimisticSettled`)或 8s 兜底; `prev` 一起改是必须的(兜底回滚要回"最后已知真值", 回命令前的旧值 = 把已暂停的种子显示成做种中)。
  · **验证**: 两个缺陷都做了确定性复现(桩服务 + Playwright; ②用"逐步喂时序 + `page.route` 注入陈旧 payload"复现, 手法已写进 pitfalls)。**新增守阵**: 冒烟两条(种子页筛选器计数=种子数 / 真值事件后不被陈旧快照打回, 各 UI +1)+ 静态守阵 `tests/test_web.py::_scan_filter_facets`(5 种注入违例红验, 含"把调用注释掉"); **冒烟断言也做了红验**(撤掉 `commands.js` 的修复重跑 ⇒ 报"陈旧快照 seeding / 覆盖保持=0 条")。单测 **1142 passed**(基线不变, 只加断言); 冒烟 ok 68/2 / error 68/0 / hang 8/0 —— ok 模式那 2 项是**既有失败**(`P0-3 乐观态及时落回真值` 的 80ms 下界已随 D2 过时, 本次定性并留待定夺, 详见 testing.md 与 pitfalls)。档案 [tasks/26-09-21-webui-filter-data-and-color-flicker.md](../../tasks/26-09-21-webui-filter-data-and-color-flicker.md)。


---

## 原「已实现」第 8 条

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
  [memory-bank/plans/26-09-19-1745-webui-responsiveness-review.html](../../plans/26-09-19-1745-webui-responsiveness-review.html)。
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
  剩: 真机走查(真实 qB 数据下的观感) + 复核缺陷修复第 2 批(组行乐观 / 响应体裁剪 / 节拍对齐)。计划 [memory-bank/plans/26-09-19-1241-webui-responsiveness-plan.html](../../plans/26-09-19-1241-webui-responsiveness-plan.html); 档案 [tasks/26-09-19-webui-responsiveness.md](../../tasks/26-09-19-webui-responsiveness.md)
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
  [§10 复核修订与修复回执](../../plans/26-09-19-1745-webui-responsiveness-review.html)(含对 BUG-3 证据②的更正)。
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
  时间太长, 估计 2-4 秒」([issue 26-09-19-1939](../../issues/26-09-19-1939-perf-webui-optimistic-latency.html))。
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
  **顺带发现另立 issue(未修)**: [整剧操作在剧行上无 `is-pending`](../../issues/26-09-19-1959-bug-webui-show-row-no-pending.html)
  —— 补丁 0ms 贴上但 `.show-row` 不绑 pending(剧行默认折叠), 与 BUG-3 同类的漏绑。


---

## 原「已实现」第 9 条

- **真机复测反馈 · 「乐观后 2-4s 才恢复正常」(2026-09-19, 已入库 `32f531d`)**: 上一条修的是「点击 → 变灰」,
  用户实际报的是**第二段**「变灰 → 真值」([issue 26-09-19-2024](../../issues/26-09-19-2024-bug-webui-truth-convergence.html))。
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


---

## 原「已实现」第 27 条

- WEB UI 替代 qB 界面 · 波次三 (2026-09-17 收口完成): 32 工作项 (FIX7/TBL8/DLG4/CTX3/SPD4/NAV3/RFB2/PRS1) 全部落地, **星图(atlas)与棱镜(prism)双 UI 同构**。后端: peers 端点修复(`sync_torrent_peers`)/`/api/paths` 已知目录聚合/bulk 组键模式/成员与单种透出 num_seeds·num_leechs·num_complete·num_incomplete/SPD-01 末档 clamp 回归锁定/SPD-03 `global_speed_limit_curve.enabled` 全管线(models+validation+loaders+设置页开关)。前端: 表格层(空值留白与"不限速"文案退役、状态底与七列三档数值色阶、去名称状态图标、列拖动重排+右键列选择器、补列、全宽布局、rail 退役改底部状态栏、批量段并入筛选行)、弹窗(删除确认框加宽+计数语义、添加种子改版与位置选择)、右键(彩色图标集/触发源强调/原生右键屏蔽)、限速(预览末档压缩、点击弹窗修改)、导航 IA(分组/种子/追剧升一级导航、设置右移、统计入状态栏、日志并入设置页、动态 logo)、详情抽屉纯展示重构、设置页重构(栅格令牌化/宽度放开/文案用户化/风险注记统一)。计划 [memory-bank/plans/26-09-16-1128-webui-qb-replace-wave3-plan.html](../../plans/26-09-16-1128-webui-qb-replace-wave3-plan.html) + 派工契约 `.cluster/webui-w3/` + 交接 [memory-bank/plans/26-09-17-0346-webui-qb-replace-wave3-handover.html](../../plans/26-09-17-0346-webui-qb-replace-wave3-handover.html); 基线 971→**988 passed**; 待人工: 浏览器 CDP 双 UI 走查 + 真机 dry-run。- tracker 分组·站点 groups 字段 + tracker_group 条件 (2026-09-15): 站点段新增可选 groups(字符串列表, 配置层声明不写种子, 组名自由命名无需预定义), 规则条件新增 tracker_group(镜像 TrackersCondition, 或关系, regex:/ignore_case, 无 tracker_conf 恒 False); 校验经 _check_str_list(非列表/纯空白项报错; 空串项被 _strip_none 统一视为未配置剔除, 项目既有约定), spec 校验走 _validate_pattern_list_spec; schema 双登记(TRACKER_FIELDS str_list + CONDITION_PLUGINS, 守卫自动 15→16); 热重载 groups=LEVEL_L2(S0 核实: record.tracker_conf 仅 added 流程绑定一次, L2 reset_runtime 置空重匹配才见新值, 与 domains/rules 同级; L0 会读到旧 conf 对象); Web UI 设置页借 str_list 控件零前端改动即可编辑保存; 测试 +4(test_conditions 条件 2 + test_config 校验/加载 2, helpers.FakeTracker 加 groups 参数), 基线 884 passed; 真机 dry-run 冒烟通过(119 种子同步/规则加载/决策链, 动作被 dry_run 抑制); 计划 memory-bank/plans/26-09-15-1504-tracker-group-plan.html(D1=方案 B 站点字段/D2=tracker_group 已拍板); 后续阶段 2/3 前端: 设置页 groups 下拉快捷追加 + 辅种管理页按组筛选; README(5 处 15→16 种)/docs/configuration.md(示例+条件表)/memory-bank(rule-system 16 条件+config-reference+testing 基线)/想法.md 回写; 已随本提交入库
