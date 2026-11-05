# activeContext 切片归档 · 流量图 / 全局流量监视器

> 摘要: 2026-11-05 activeContext 蒸馏轮逐字外迁的 13 条切片原文(2026-10-04~11-03, 流量图视图/聚合数据面/GTM 工具与来源集成)。
> 触发: 流量图, qb traffic, 聚合, 活尾, GTM, global traffic monitor, 切片归档
> 本文件为逐字归档(attachments 不计 cap); 蒸馏结论与指针写在各 progress 主题文件。
> 归档说明: 原文中的相对链接已因换目录统一补一级 ../, 其余逐字未改。
> 归档说明之二: 原文中的 Refs 声明行改题为「切片原文」以免被知识库认领链解析误读; 链接路径已补一级 ../; 其余逐字未改。

---

<!-- slice: 26-10-04-0405-webui-qb-traffic-drawer-merge.md; 最后活动: 2026-10-04 04:20 -->

# WEBUI qB 流量图三挂点并入底部详情抽屉 (待用户提交)

> 摘要: 用户要求「qb流量图复用种子流量(详情)的模式/样式/高度, 特别是高度跟随详情窗, 替换当前的弹出窗口」。
> 四项拍板: ①并入详情抽屉 ②与详情抽屉**共用高度**(drawerHeightPx) ③**全部三挂点** ④抽屉**提升为全局**(任意页可开)。
> 落地: 删除 `tpl/qb-traffic.html` 两个模态弹层(全局/分组) -> 抽屉新增 `kind === "traffic"` 形态(`drawer.scope`
> 记挂点 global/group), 与种子详情的「流量」页签**共用同一段正文块**(`qbTrafficActive` -> `qbCur*`, 建图落点统一
> `ref="qbChartHost"`); `.drawer-dock` 落点自 `tpl/torrents.html` 上提为 app 级分片 `tpl/dock.html`(三清单同步),
> 可见性改由 `drawer.js::drawerVisible` 把守(种子详情限种子页 / 流量图全局)。图高改量 `host.clientHeight` 并让
> ResizeObserver **宽高双观察** -> 拖拽抽屉顶缘调高, 图实时跟着长(实测 378px 抽屉 -> 图 194px; 拉到 620px -> 图 436px)。
> 去掉 `qbHistOpen` / `qbGroupOpen` 两个独立开合字段(统一 `drawer.open + kind + scope`), Esc 退栈/escBusy/登出清理
> 归一到 `closeDrawer` + `_qbTeardown`。三主题 CSS 成对改。**test.full 2423 passed + 3 skipped / 99%**;
> 浏览器冒烟(Playwright + ui_harness)三形态实测: 全局流量图渲染 + 高度跟随 + 种子详情流量页签 + 默认页布局未坏, 零 pageerror。
> 未验证面: 真机(真实 qB 数据/24h 与 30d 换窗/轮询续拉)待用户走查; 原「弹窗滚轮穿透」报告里的 12 遮罩模态现为 10。

> 最后活动: 2026-10-04 04:20

**正在进行**: 无 —— 实现 + 测试 + 浏览器冒烟均完成, **已提交 `659eada8`(Gitee develop, 已推)**。
提交前远端已推进到 800ccba2(另一 clone 的 .modal-members 死类移除, 同改 atlas/console views.css),
按 sync 失败行配方 stash -u -> sync -> stash pop 合流(无冲突), 改动落在 800ccba2 之上; 合并后复跑
test.full 2423 passed + 3 skipped / 99%。

**待办**: ①用户真机走查(高度跟随 / 三形态 / Esc / 切页后流量图仍在); ②原弹窗滚轮穿透报告(26-10-04-0128)的遮罩计数
与弹窗清单需随之更新(该报告停在拍板, 未开工, 实施时一并核对); ③主 issue 26-09-27-1248 真机观察期后收口;
④`kb.check` 报的切片数债务(91 > 70)待另开会话清理; ⑤`scripts/ui_smoke.cjs` 头注的 NODE_PATH
(`.workbuddy-ai/binaries/node/workspace/node_modules`)在本 clone 不存在, 属文档漂移, 未顺手改(范围守恒)。

---

<!-- slice: 26-10-05-1759-webui-qb-traffic-window-persist-shortcuts.md; 最后活动: 2026-10-05 17:59 -->

# 流量图窗口选择持久化 + 三条快捷键 (qB 口径流量图 UX 补完)

> 摘要: 用户动议三项 —— ①流量图「视图选择」(时间窗口 13 档)记入 localStorage; ②种子流量图并入种子详情面板;
> ③发现的缺口 = 缺快捷键。**②经核对当前代码已实现**(种子详情抽屉已有「流量」页签, 全局/分组/种子三挂点共用同一段
> 正文块与同一拖拽高度, 2026-10-04 并入), 本轮实施 ①③:
> ① 持久化粒度按用户拍板 = **全局单独一份 / 分组与种子共用一份**(`autoqb.ui.qbWinGlobal` / `autoqb.ui.qbWinShared`),
> 换窗即落盘、刷新后保持; 档位清单收成单点 `QB_WINDOW_NAMES`(与后端 `traffic_qb.WINDOW_NAMES` 逐字一致), 供
> 展示(模板 `v-for="w in qbWindowNames"`, 原先硬编码 13 档字面量)、前后切换、持久化校验三处共用。
> ③ 三条快捷键: **打开全局图 `Ctrl+Backslash`**(状态栏入口的键盘对应, run 内 `qbTrafficOn` 门控 + 未启用提示) /
> **详情面板流量页签 `Alt+5`**(补 Alt+1~4 缺口, `_kbDrawerTab` 内补流量门控, 未启用不许切到无按钮的隐形页签) /
> **窗口前后切换 `[` `]`**(新增引擎机制 **`when` 条件绑定**: 仅 `qbTrafficActive` 时消费键位, 无流量图时不
> preventDefault、键位留给浏览器)。
> 验证: 新增守阵 2 条(两文件)红验通过 + 一次性 node 探针 22/22 过(持久化粒度/校验/夹取/`when` 分流/三条新入口/未撞旧键);
> test.full **2619 passed + 4 skipped / 99% / 44.2s**(基线切片 26-10-05-1759)。
> 未验证面: 真浏览器交互(本 clone node 侧 Playwright 缺失, `dev.harness`/`ui_smoke.cjs` 跑不了; 桩 harness 亦未开
> `qb_traffic`, 图表本身不在冒烟覆盖内)—— 待用户真机走查。
> 最后活动: 2026-10-05 17:59

**Refs（切片原文）:** memory-bank/tasks/26-10-05-webui-qb-traffic-window-persist-shortcuts.md

## 现状

- **实施完成, 待用户提交**。改动面 6 文件(4 源码 + 2 测试):
  - `shared/qb_traffic_chart.js` — `QB_WINDOW_NAMES`/`QB_WINDOW_DEFAULT` 单点 + 两个存储键 + `qbWinStoreKey`
    + `qbInitialWindow`(初值读取, 定义在此因三份 tpl-manifest 里本文件均排在 state.js 之前)+ `qbWindowNames` computed
    + `persistQbWindow` + `qbCycleWindow`(端点夹取不环绕, 走 `qbSetWindow` 单点); `_qbSetWindow` 加落盘;
    `openQbHistory` 补未启用提示。
  - `shared/state.js` — 三窗口字段初值改 `qbInitialWindow("global"/"torrent"/"group")`。
  - `shared/tpl/drawer.html` — 窗口按钮 `v-for="w in qbWindowNames"`(去 13 档硬编码)。
  - `shared/shortcuts.js` — 注册表 4 条新条目(`open-qb-traffic` / `drawer-tab-traffic` / `traffic-win-prev` /
    `traffic-win-next`); 引擎加 `when` 条件绑定分流(preventDefault **之前**); `_kbDrawerTab` 补流量门控。
  - `tests/test_web.py::test_frontend_qb_traffic_window_persist_and_single_source`(新) ·
    `tests/test_web_shortcuts.py::test_qb_traffic_shortcuts`(新, 并给 `_registry()` 加 `when` 字段解析)。
- 关键判据/取舍:
  - **档位单点**同时喂三处(展示/切换/校验) —— 与后端 `WINDOW_NAMES` 逐字断言, 避免任一处硬编码漂移成 400。
  - **`when` 条件绑定**是引擎新机制(条目形状注释已补): 条件假 → 不消费按键(不 preventDefault), 区别于
    `_kbDrawerTab` 那类"消费键位后 toast 忽略"的既有先例 —— 流量图窗口键在无图时不该被吞。
  - 端点**夹取不环绕**(从「全部」跳回「1分」是惊扰)。
- 验证:
  - 新增守阵红验: 摘 `when` 分流 → `test_qb_traffic_shortcuts` 红; 摘 `persistQbWindow` 调用 →
    `test_frontend_qb_traffic_window_persist_and_single_source` 红; 恢复后绿。
  - 一次性 node 探针(`tmp-analysis/`, 已删)22/22: 持久化粒度三向 + 非法/无存储回落 + `qbCycleWindow`
    步进/两端夹取/无形态零副作用 + `persistQbWindow` 键分派 + `when=false` 不消费 / `when=true` 消费且动作正确
    + Ctrl+Backslash→openQbHistory / Alt+5→tab:traffic / Shift+Backslash 与裸 Backslash 未撞键。
  - `commands run test.full` → 2619 passed + 4 skipped / 99% / 44.2s(增量 +9 = reannounce 重构守阵 +7 经开工同步并入
    + 本轮 +2)。
- 未验证面 / 遗留: ①真浏览器走查(窗口切换后刷新是否保持 / `[` `]` 是否跟手 / Alt+5 与 Ctrl+Backslash 实际手感);
  ②`dev.harness` 桩未开 `qb_traffic`, 流量图不在既有浏览器冒烟覆盖内 —— 若后续要给图表做冒烟, 需先给 harness 加
  开 `qb_traffic` 的桩开关(本轮未做, 范围守恒); ③`kb.active` 报的切片数债务(126 > 70)非本轮引入, 转告用户另开会话清理。

---

<!-- slice: 26-10-08-0713-webui-qb-traffic-head-layout.md; 最后活动: 2026-10-08 07:13 -->

# webui-qb-traffic-head-layout — 流量图版式改(控件上提头部 + 图例并入统计栏)

> 摘要: 用户报「流量图被其它元素占用了高度, 主要信息(图本身)被压缩」。拍板四条: ①时间档位(13 档)
> 与纵轴设置自正文工具条**上提到「qB流量图」头部标题栏**; ②两处注释(正文工具条「qB 口径 · 程序
> 运行期间…」+ 图下行「…· 悬停查看详情」)**全部移除**; ③上行/下行图例**并入统计栏**(窗口 N 桶
> 之前); ④统计栏与状态栏间距减小。标题缩短为「qB流量图」。**只改经典 UI**, `shared/drawer_tpl/`
> 15 个变体零改动。三挂点(全局/分组/单种)共用头部/正文, 同改全生效。已闭环。
> 最后活动: 2026-10-08 07:13

**Refs（切片原文）:** memory-bank/tasks/26-10-08-webui-qb-traffic-head-layout.md,memory-bank/testing/baselines/attachments/26-10-08-0713-webui-qb-traffic-head-layout.md

- 任务档案: [26-10-08-webui-qb-traffic-head-layout](../../tasks/26-10-08-webui-qb-traffic-head-layout.md) —— 拍板记录、改动面、关键判据与实测数字都在档案, 本切片只留指针。
- 落地(纯前端静态层 + 测试侧, Python 产品代码零改动): `shared/tpl/drawer.html` 流量形态头部插入 `.qb-tabs`(13 档)+ `.qb-tools`(纵轴三态/手动输入/上限读数), 正文删 `.drawer-toolbar` 与 `.qb-tools` 与独立 `.hist-legend`, 统计栏首部加 `.hs-leg`(上/下行图例); `qb_traffic_chart.js` `qbTrafficTitle` 全局标题改 `"qB流量图"`; 三皮肤 `views.css` 新增 `.hs-leg` + 头部 `:has(> .qb-tabs)` 换行/不收缩规则 + `.hist-summary` 间距 10→6px。
- 关键判据(易被后人改坏): 控件落点=头部标题栏(挪回正文即压缩图高 = 本改动被回退); 独立 `.hist-legend` 行在本面板**必须不存在**(历史流量弹层 popovers.html 仍用, 属另一处); 头部仍 44px 未新增行(真浏览器实测)。
- 实测: test.full 全绿、0 failed、TOTAL 99%(基线切片 [26-10-08-0713](../../testing/baselines/attachments/26-10-08-0713-webui-qb-traffic-head-layout.md), 相对上基线 passed ±0 —— 只改断言口径未新增测试函数; 精确数字见 kb.baseline); 旁证真浏览器三皮肤目检: 头部 44px / 图 266px(吃满余量) / 统计栏贴面板底缘 / 零 pageerror / `.hist-legend` 计数 0 而 `.hs-leg` 计数 2。
- 未验证面: 窄视口(≤900px)头部换行的逐档观感未走查(规则已写, 靠 `:has` + `flex-wrap` 抗挤压); 面板默认高度语义(42vh)未动 —— 本次只把正文占用的高度还给图。

---

<!-- slice: 26-10-09-0740-webui-qb-traffic-seed-header-controls.md; 最后活动: 2026-10-16 03:00 -->

# webui-qb-traffic-seed-header-controls — 种子流量图的档位/纵轴控件落点 + 统计栏口径注解形态

> 摘要: 本专题三轮同日落定 —— ①上一轮: 控件补进种子头部(修「控件消失」); ②第 2 轮: 用户否决头部落点
> (「太挤、小窗口下会变形」)⇒ 改落**图下统计栏**(`.hist-summary` 内 `.qb-statctl`, 排在「下载累计」之后),
> 统计栏本体门放宽为 `qbCurSummary || qbCurScope === 'torrent'`; ③第 3 轮: 统计栏常驻口径注解
> 「累计为窗口内增量(断线期不计)」退场, 改为**上传累计 / 下载累计两个读数的悬浮提示**(`:title="qbCurSummaryHint"`,
> 走全局断供管道 → `data-aq-tip`)。第 3 轮顺带把统计栏从两行收回**单行**(33px), 图由 235px 回到 259px ——
> 第 2 轮「图少约 31px」的代价随之消失。**全局/分组流量形态全程零改动**; 零 JS 改动; 守阵只改写既有断言
> 口径(零新增测试函数); 真浏览器三皮肤 + 四档窄视口实测不越界、tooltip 正常、零 pageerror。已闭环。
> 最后活动: 2026-10-16 03:00

**Refs（切片原文）:** memory-bank/tasks/26-10-09-webui-qb-traffic-seed-header-controls.md,memory-bank/testing/baselines/attachments/26-10-09-1207-webui-qb-traffic-seed-hint-tooltip.md,memory-bank/testing/baselines/attachments/26-10-16-0300-webui-qb-traffic-statbar-align.md

- 任务档案: [26-10-09-webui-qb-traffic-seed-header-controls](../../tasks/26-10-09-webui-qb-traffic-seed-header-controls.md) —— 三轮的根因/取舍/实测数字都在档案, 本切片只留指针。
- 落地(纯前端静态层 + 测试侧, Python 产品代码零改动): `shared/tpl/drawer.html` —— 种子头部不挂控件组;
  统计栏 `.hist-summary` 内「下载累计」之后挂 `.qb-statctl`(内含与流量形态头部**逐字同源**的 `.qb-tabs` +
  `.qb-tools`, 门 `v-if="qbCurScope === 'torrent'"`); 两个累计读数各挂 `:title="qbCurSummaryHint"`。
  三皮肤 `views.css` 只加了 4 行 `.hist-summary > .qb-statctl`(成组 / 内层不收缩 / 紧凑档) —— 第 3 轮**零 CSS 改动**。
- 关键判据(易被后人改坏): ①控件是**两处挂点**(流量形态头部 / 统计栏), 改一处必须同步另一处 —— 守阵把两块
  内层(空白归一后)比对, 不同步即红; ②统计栏内那组的门必须是 `qbCurScope === 'torrent'`; ③统计栏本体必须门在
  `qbCurSummary || qbCurScope === 'torrent'` 上(只写 `qbCurSummary` = 首载/错误态控件整组消失);
  ④落点次序 = 图例 → 窗口 N 桶 → 上传累计 → 下载累计 → 控件组, 由守阵按下标单调钉住; ⑤种子头部**不得**再出现
  `.qb-statctl`/`.qb-headctl`(该头部回归单行 44px); ⑥口径注解必须是**两个**累计读数上的 `:title`
  (守阵钉 `count(':title="qbCurSummaryHint"') == 2`)且抽屉里**不得**再有 `.hist-hint` span。
- ⚠ 别顺手删 `.hist-hint` 的 CSS: 抽屉里那处用法已退场, 但 `shared/tpl/popovers.html`(今日流量弹层
  「悬停查看详情」)仍在消费同一条规则 —— 三皮肤各一行, 删了那边就裸奔。
- 版式实测(真浏览器, 三皮肤 1440x900): 头部 44px(单行)/ 统计栏 31~33px(**第 3 轮起单行**, 第 2 轮为 54~57px
  两行)/ 控件组 821px 起于「下载累计」右侧不越界 / 图 259~261px(第 2 轮 235~238px)。窄视口 1180/980/820:
  头部恒 44px、横向溢出 0。tooltip: 悬停两个累计读数均弹「累计为窗口内增量(断线期不计)」, 分组作用域自动带
  「 · 组口径 = 当前成员集聚合」尾注。
- 未验证面: ①15 个 `drawer_tpl/` 变体下统计栏的观感未逐变体走查; ②折叠态(`drawer.collapsed`)与统计栏同屏时
  的观感未走查(2026-10-09 起**不再适用** —— 折叠状态已整体移除, 见档案 26-10-09-webui-drawer-collapse-removal); ③tooltip 在抽屉贴近屏幕底缘时的弹层避让未专项走查(全站 tooltip 共用同一避让实现)。

## R4(2026-10-16) 三挂点对齐: 流量形态头部控件退役 + 上限读数移除 + 统计栏贴底

> 摘要: 用户动议「全局流量图的视图/纵轴按钮改到下方, 与种子流量图对齐; 调小统计栏与下方元素的间隔; 移除纵轴上限字样(全局同样跟进)」。落地: ①`tpl/drawer.html` 流量形态头部调用点摘掉 `<aq-qb-ctl>`(头部回归纯标题), 统计栏 `.hist-summary` 与 `.qb-statctl` 去掉 scope 门(恒渲染, 三挂点统一, 旧「torrent 专属门」口径作废); ②上限读数整链退役 —— `qb_traffic_chart.js` 删 `qbYAxisCapText` computed、`tpl/drawer-head.html` 删 `.qb-tools-hint` span、三皮肤 CSS 删该规则; ③三皮肤 CSS: 删头部挂点四条死规则(`.drawer-head:has(> .qb-tabs)` 族), `.drawer-body.is-traffic` 加 `padding-bottom: 8px`(原 20px)收紧统计栏与抽屉底缘的间隔; ④守阵同步改写(traffic head 调用点改钉「不得含 aq-qb-ctl」+ `<aq-qb-ctl>` 挂点数 2→1 + 上限读数反回潮锚 + statctl 恒渲染), 零新增测试函数。
> 最后活动: 2026-10-16 00:55

- 落地面(9 文件): `shared/tpl/drawer.html` / `shared/tpl/drawer-head.html` / `shared/qb_traffic_chart.js` / 三皮肤 `views.css` ×3 / atlas+console `dialogs.css`(`.drawer-body.is-traffic` 各住一处) / `tests/test_webui_static_dom_panel.py`。
- 关键判据变更(覆盖 R1–R3 的③②①): ①控件组**唯一挂点** = 统计栏, 头部**不得**再接 `<aq-qb-ctl>`; ②`<aq-qb-ctl></aq-qb-ctl>` 在 drawer.html 恰 1 处; ③统计栏与 statctl 均**恒渲染**(不得再门 `qbCurScope === 'torrent'`); ④上限读数(`qbYAxisCapText` / `.qb-tools-hint`)反回潮 —— ⚠源码注释里也不能再写该标识符(反回潮锚按字面量扫全文本, 见 pitfalls/testing/guard-literal-comment-trip)。
- 截图验收桩: 旗标与流量数据用 Playwright route 拦截 `/api/webui/flags` + `/api/traffic/qb/**` 造出(桩服务 FakeConfig 无 qb_traffic 段, 天然空态)—— 截图脚手架在仓外临时目录, 未入库。
- 实测: `test.full` 全绿 + `npm run test:e2e:fast` 全绿 + 包内脚本零触碰(数字见 `commands run kb.baseline` 最新切片); prism 皮肤全局/种子两形态截图比对: 控件同排同位、上限字样消失、统计栏贴底。

## R5(2026-10-16) 统计栏子项垂直对齐(三挂点)

> 摘要: 用户动议「流量图统计栏未对齐, 比如『上传/下载图例』与『窗口 xxx桶』后者更高; 还有后面的视图切换按钮与纵轴切换按钮; 所有流量图都对齐」。根因(真浏览器量布局, 非推断): `.hist-summary` 是 flex 但**没写** `align-items` ⇒ 默认 `stretch` —— 纯文本读数(窗口 N 桶/两个累计)被拉长到与控件组同高、文字**贴顶**(墨迹 y=832), 而自带 `align-items:center` 的图例 `.hs-leg`(y=835.7)与控件组 `.qb-statctl` 的档位/纵轴按钮(y=836)内容居中 ⇒ 三族文字落成两条线。修法 = 三皮肤 `.hist-summary` 显式 `align-items: center`; 三挂点(全局/分组/单种)共用同一段模板, 一处规则全覆盖, 顺带修好 `popovers.html` 今日流量弹层的同款统计栏。
> 最后活动: 2026-10-16 03:00

- 落地面(4 文件): 三皮肤 `views.css`(`.hist-summary` 各一行 + 口径注释) / `tests/test_webui_static_dom_panel.py`(CSS 三皮肤成对段 +1 条断言)。
- 关键判据(易被后人改坏): ①`.hist-summary` 必须 `align-items: center` —— 删掉即回到「文本贴顶 vs 图例/控件居中」的两条线, 而**类名/结构/模板守阵全绿**(只有真浏览器量文字墨迹 y 才现形); ②三皮肤**成对改**(已有断言钉住, 只改一处判红); ③不要改用 `align-items: baseline` 替代 —— 档位/纵轴按钮组是带边框胶囊, 基线对齐会把整组按钮框抬上去, 跑出另一种错位。
- 实测(真浏览器 1440x900, 三皮肤 × 三挂点 × 纵轴 auto/manual = 18 组): 图例 / 窗口桶 / 两个累计四族文字墨迹 y **逐组同值**(prism·atlas 835.7); 档位按钮与纵轴按钮同线(prism·atlas 836 = 差 0.3px 子像素, console 838 全等); manual 模式输入框出现后统计栏行高仍 33px(不串行、不换行)。修前同量: 文本 832 / 图例 835.7 / 按钮 836。
- 取证脚手架(未入库, `tmp-analysis/` 已 gitignore): 桩服务 FakeConfig 无 `qb_traffic` 段 ⇒ 流量图天然空态, 故用 Playwright `route` 拦截 `/api/webui/flags`(放行 `qb_traffic_enabled`) + `/api/traffic/qb/**`(回同形人造响应体), 之后走**真实入口**(`openDrawerTraffic` / `openTorrentDrawer` + 流量页签)与真实模板/CSS —— 与 R4 同一套桩法。
- 实测数字见 `commands run kb.baseline` 最新切片; 新坑(静态守阵全绿而版式错行)已记 `pitfalls/web-ui/layout-css.md`。

---

<!-- slice: 26-10-12-0815-webui-traffic-limit-history.md; 最后活动: (无, 以文件名时间戳为准) -->

# webui-traffic-limit-history — qB 流量图限速线按当时值分段

> 摘要: 计划 [26-10-12-0535](../../plans/26-10-12-0535-plan-webui-traffic-limit-history.html) **W1-W3 全部实施完成** —— W1 后端(记录器/读侧/payload)、W2 前端(分段绘制/悬停读数/守阵)、W3 回写与基线; 验收与细节见任务档案与基线切片 [26-10-12-0815](../../testing/baselines/attachments/26-10-12-0815-webui-traffic-limit-history-w1w3.md)。**CI 红已修**(GitHub 上两条 caplog 断言, 根因 = 节流哨兵 `0.0` 在开机不满 1 小时的 CI 全新 VM 上吞掉首次告警, `0.0` → `None` + 1 条守阵, 见坑档 [monotonic-warn-sentinel](../../pitfalls/testing/monotonic-warn-sentinel.md) 与基线 [26-10-12-1806](../../testing/baselines/attachments/26-10-12-1806-traffic-limits-warn-sentinel-ci-fix.md))。真机走查(改限速 → 看历史段)待用户。

**创建:** 2026-10-12 06:19
**最后活动:** 2026-10-13 07:22
**主题:** webui-traffic-limit-history
**摘要:** 计划 [26-10-12-0535](../../plans/26-10-12-0535-plan-webui-traffic-limit-history.html) **W1-W3 全部实施完成**: W1 后端 —— 新增 `core/traffic_limits.py`(SpeedLimitRecorder 采样点变化才记生效值, 00:00 硬切 + 新天基线 carry + 重启去重 + OSError 降级不上抛 + 病态翻转护栏; LimitsCache mtime+size 键控; 装配层合成首事件 + 同值去重), `traffic_sample_mod._sample_global` 顺带观测(dry_run 同门), `traffic_qb.py` 三 payload 统一附 `limits`(首元素 = 窗口起点合成事件, 记录起点前无值); W2 前端 —— `_qbLimitSegs`/`_qbLimitAt` 纯函数 + `_qbDrawLimits` 分段化(逐段可见性, 末段到图右沿, 快路同步换 limits)+ 悬停「当时限速」行 + D4 文案; W3 回写 conventions/modules 两处。**验收**: `test.full` **3144 passed + 3 skipped** / 覆盖率 `TOTAL 16708 161 5688 140 99%`(+12 = 新测试逐条对账); 全量 e2e **166 passed + 10 skipped**(前两轮失败全为另一 clone 并行 e2e 抢 8137 端口, 非代码缺陷); 红验三条均注入即红/还原即绿。基线 [26-10-12-0815](../../testing/baselines/attachments/26-10-12-0815-webui-traffic-limit-history-w1w3.md)。真机走查(改限速 → 看历史段)待用户。**2026-10-12 18:07 后续: GitHub CI 两条红已修** —— `SpeedLimitRecorder._oswarn_ts`/`_guard_ts` 哨兵 `0.0` → `None`(`time.monotonic()` 原点是开机时刻, 开机不满节流间隔 3600s 的 CI 全新 VM 上 `now - 0.0 >= GAP` 判假 ⇒ 首次告警被吞, 本机 uptime 数十小时故恒绿); 新增守阵把时钟钉在开机 2 分钟, 旧写法本机即红。数字见 `commands run kb.baseline`, 坑档 [monotonic-warn-sentinel](../../pitfalls/testing/monotonic-warn-sentinel.md)。**2026-10-13 07:22 后续: 跨零点 flaky 两条用例已修** —— `test_recorder_patological_flip_guard` / `test_recorder_warn_first_fire_on_fresh_boot` 在距本地零点约 34 分钟内跑必红(循环 `ts+i` 跨天把 `SpeedLimitRecorder._guard_count` 的按天计数 `_day_events` 清零, 2000 阈值永不达, 生产按天语义正确): 两条用例把循环起点 `ts` 锚当日 00:01 走仓库现单点 `v4_day_epoch`(本地口径, 与 `v4_epoch_date_str` 一致; 别 `//86400*86400` UTC 对齐即新 flaky), 跨度 &lt;86400 恒同日。时刻无关证把 `time.time()` 钉距零点 1359s 跑两用用例绿(修复前同时刻直读探针 `day_events=672` 即红验锚点)。数字见 `commands run kb.baseline`, 坑档 [flaky-midnight-daycount](../../pitfalls/testing/flaky-midnight-daycount.md), issue [26-10-12-2338](../../issues/26-10-12-2338-test-traffic-limits-guard-midnight-flaky.html)。
**Refs（切片原文）:** memory-bank/plans/26-10-12-0535-plan-webui-traffic-limit-history.html,memory-bank/tasks/26-10-12-webui-traffic-limit-history.md,memory-bank/testing/baselines/attachments/26-10-12-0815-webui-traffic-limit-history-w1w3.md,memory-bank/testing/baselines/attachments/26-10-12-1806-traffic-limits-warn-sentinel-ci-fix.md,memory-bank/pitfalls/testing/monotonic-warn-sentinel.md,memory-bank/issues/26-10-12-2338-test-traffic-limits-guard-midnight-flaky.html,memory-bank/pitfalls/testing/flaky-midnight-daycount.md,memory-bank/testing/baselines/attachments/26-10-13-0722-traffic-limits-midnight-flaky-fix.md

---

<!-- slice: 26-10-14-0528-webui-qb-traffic-agg-live-tail.md; 最后活动: 2026-10-14 05:28 -->

# 26-10-14-0528-webui-qb-traffic-agg-live-tail — qB 流量图 agg 段活尾合流(S7)已落地

> 摘要: 用户报「3 天及以上的流量图视图有真空: 目前仅显示到 14 日 0 点, 实际上现在已经 14 日 1 点了」。根因 = agg.dat 只含封口行, 未封口的开放小时/当日/当月桶只活在采样写侧累计器, 读侧无通道(S6 活尾只接了 raw 段窗)。修法 = S6 活尾口径平移到 agg 段: `LiveTail.pending_agg` 发布写侧累计器未封口部分行, 读侧 `v4_agg_obs_live` 按 epoch 与磁盘封口行合流(开放桶直映 / 已封桶残余走 `v4_merge_agg` 不双计), month 段铺格计入活尾当月行, 组端点空态判据与逐成员 obs 计入活尾, 前端零改动。小于 3 天的 7 档(raw 段)经核查无此问题(S6 已修), 缺陷分界即数据源分界。实测数字见基线切片(引 `commands run kb.baseline`)。
> 最后活动: 2026-10-14 05:28
> 状态: Open(实现+守阵+回归全绿, 待真机走查)

**Refs（切片原文）:** memory-bank/tasks/26-10-14-webui-qb-traffic-agg-live-tail.md

## 现在做到哪

S7 五步全部落地, 守阵与全量回归全绿(数字见基线切片 `baselines/attachments/26-10-14-0528-webui-qb-traffic-agg-live-tail.md`):

1. **`LiveTail` 第 8 字段 `pending_agg`**(`core/traffic_store.py`): 缺省空 = 纯磁盘 agg 读, 向后兼容既有 7 参位置构造; docstring 与模块头补 S7 口径。
2. **写侧发布**(`core/modules/traffic_sample_mod.py`): 模块级纯函数 `_pending_agg_rows(agg, now)` 产出未封口部分行 —— 开放小时(dt 加权)+ 当日(`day_hours` ∪ 开放小时部分行 rollup)+ 当月(`month_days` ∪ 当日部分行 rollup); `_publish_live_tail` 发布面从 raw 键扩到 agg 键。day/month 两级包 try/except 三型(Windows 假时钟 OSError, 坑档已记)。
3. **读侧合流**(`core/traffic_grid.py`): `v4_agg_obs_live(rows, live_rows, grid)` 按 epoch 合流; 已封桶残余走 `v4_merge_agg`(与写侧迟到补记同判据, 竞态窗不双计不出尖峰); 窗外 epoch 不消费。
4. **端点装配**(`webui/server/traffic_qb.py`): `_live_agg_rows(key, kind)` 按段过滤; 单系列 agg 分支合流 + month 铺格(`build_month_grid` 数据面计入活尾当月行, 否则当月桶不在栅格被丢弃); 组端点逐成员取活尾 + 空态判据计入活尾 + 逐成员 obs 合流; degraded(read_agg OSError)路径不融合活尾保 last-good 兜底。
5. **守阵 6 个**(均带修复前形态对照): 端点 4 个(3d 开放小时补尾 / 6mo 当日补尾 / all 当月入栅格 / 组 30d 成员部分行+空态) + 底层 2 个(发布与封口清除 / 残余合流不双计)。

## 关键口径(别改回去)

- **活尾部分行走 S6 同一快照通道**: 主循环线程发布、`AggRow` 冻结、Web 线程只读 —— 不破单一写线程。
- **month 段铺格必须计入活尾当月行**: 漏了这步, all 窗的当月桶整个不在栅格, 合流被窗外过滤丢弃(修复前连 null 都没有)。
- **组 totals 是逐成员先差分再求和**: 基线缺失不出洞 = 0; 同一成员跨接缝(磁盘上行 → 活尾当前行)差分链不断 —— 写测试预期时别把单系列相邻桶差分预期搬过来。
- **前端不动**: points 末桶出值后 uPlot 数据驱动 x 轴自然延伸到当前桶, 与 raw 段活尾同形态。

## 下一步 / 移交

- **真机走查**: 单元测试已覆盖用户所报形态, 真机 qB 端到端待用户重启后观察(图尾实时延伸到当前开放桶)。
- **入池 issue 26-10-05-1015-feat-qb-traffic-agg-live-buckets 正是本缺陷(候选 S7)**: 按请求边界未认领未置 Done, 待用户显式确认后补认领与复验记录。
- **窗口档位全景**: 13 档中 raw 段 7 档(<3 天)S6 已修无此问题; agg 段 6 档(≥3 天)由本单修复 —— 用户追问「小于3天的是否有此问题」的结论。

---

<!-- slice: 26-10-15-0728-qb-traffic-restart-spike-gap.md; 最后活动: 2026-10-17 04:44 -->

# qb-traffic-restart-spike-gap — WEBUI 流量图重启尖峰/无采样区取证

> 摘要: 用户报「WEBUI 流量图 10-15 06:36 重启后异常峰值 + 超出重启时间的无采样区」。取证结论: ①尖峰 = qB alltime 在 payload 速率恒 0 时持续增长(seed↔seed 短命连接握手字节, ~500 B/s 双向, 不落种子 payload), 采样器按 (0,0) 开 z 游程, z 快照冻结 6.6h(+15.3MB dl/+16.5MB up)且磁盘零痕迹; 重启后首样读入新鲜 totals, 读侧 delta/w 把整段陈旧差打进 06:36:08 单桶(2s 桶 6.9MB/s, 约 11,000×)。②无采样区 = 重启缝 ~10s(2s 视图 3 个 null 桶)+ 投递黑障(旧 WEBUI 06:36:01.5 死→新服务 06:36:08.1 起→~06:36:10 首活尾响应), null 区视觉延伸到观察时刻。细流来源与排除项见报告 §04.5; 分步实施 P0–P6 与验收 E2E1–E5 在计划 0829, agg 归属形态 D 在计划 1509。实施面已全部收口, 唯一未兑现 = E2E5 真机人工验收; 本切片只留结论、证据坐标与轮次索引, 明细在档案/计划/报告。
> 最后活动: 2026-10-17 04:44

**Refs（切片原文）:** memory-bank/reports/26-10-15-0728-report-qb-traffic-restart-spike-gap.html, memory-bank/reports/26-10-07-2031-report-qb-traffic-rate-basis.html, memory-bank/plans/26-10-15-0829-plan-qb-traffic-restart-spike-gap.html, memory-bank/testing/baselines/attachments/26-10-15-0845-qb-traffic-restart-spike-gap-plan.md, memory-bank/testing/baselines/attachments/26-10-15-1135-qb-traffic-restart-spike-gap-p2.md, memory-bank/testing/baselines/attachments/26-10-15-1247-qb-traffic-restart-spike-gap-p3.md, memory-bank/testing/baselines/attachments/26-10-15-1418-qb-traffic-restart-spike-gap-p4.md, memory-bank/testing/baselines/attachments/26-10-16-0454-qb-traffic-restart-spike-gap-p3-rev.md, memory-bank/testing/baselines/attachments/26-10-16-1057-qb-traffic-seam-fixes.md, memory-bank/testing/baselines/attachments/26-10-16-1126-qb-traffic-seam-fixes-r2.md, memory-bank/tasks/26-10-15-webui-qb-traffic-restart-spike-gap.md, memory-bank/issues/26-10-16-0020-bug-agg-hour-totals-frozen-run.html, memory-bank/issues/26-10-16-0020-question-agg-rate-lane-invisible-bytes.html, memory-bank/issues/26-10-16-0954-bug-traffic-seam-short-gap-spike.html, memory-bank/issues/26-10-16-0954-bug-traffic-seam-zero-bucket-isolated-marker.html, memory-bank/issues/26-10-16-0954-bug-traffic-seam-hint-missed-after-first-sample.html, memory-bank/testing/baselines/attachments/26-10-16-1204-qb-traffic-restart-spike-gap-p4-rev.md, memory-bank/plans/26-10-16-1509-plan-agg-hour-totals-attribution.html, memory-bank/testing/baselines/attachments/26-10-16-1628-qb-traffic-restart-spike-gap-agg-attribution-d.md, memory-bank/pitfalls/backend/traffic-row-format-extension.md

**R1(2026-10-15 07:28):** 用户报故障, 要求只读取证并出报告 → `reports/26-10-15-0728-report-qb-traffic-restart-spike-gap.html`(Done)。
**R2(2026-10-15 08:08):** 用户要求定位细流 qB 侧来源并更新报告 → 就地增补 §04.5(计数器级定位, 未新建文件)。
**R3(2026-10-15 08:29):** 报告转分步计划 → `plans/26-10-15-0829-plan-qb-traffic-restart-spike-gap.html`(P0–P6, E2E1–E5)。
**R4(2026-10-15 09:45):** 实施 P0 → 尖峰走活尾合流分支(`core/traffic_grid.py:412-415` 显式跳过真空判定), 非链断点; 生产仍处开放 z 游程(天文件 mtime 06:36:01、速率恒 0)。P1 降级可选, P2 升级唯一必要环。
**R5(2026-10-15 11:35):** 实施 P2(读侧接缝摊配 + 观测缝 > 60s 洞判 + 24h 回看) → E2E1 三窗 PASS, 接缝桶 (1068, 1526) B/s 逐位一致; 基线 26-10-15-1135。
**R6(2026-10-15 12:47):** 实施 P3(同步层速率键新鲜度告警, 范围拍板只做①缺席告警) → 基线 26-10-15-1247。
**R7(2026-10-15 14:22):** 实施 P4(meta `server_started_at` + `_qbSeamHint` + drawer「数据接缝中」提示) → 触 5 源文件立档; 基线 26-10-15-1418。
**R8(2026-10-15 15:02):** P5/P6 收口(零改码): 口径入 progress 单点; 端口建议 qB 侧手工归 0/给足余量(低优先级)。
**R9(2026-10-16 00:20):** 评估 P1 收益 → 四形态全不实施(1A 否决/1B 不可行/z 封口被用户否决); 派生两条 agg issue 入池。
**R10(2026-10-16 04:54):** P3 判据修订(per-key 语义, 修纯做种启动误报) → 基线 26-10-16-0454(当前事实源)。
**R11(2026-10-16 10:57):** 修复两条 26-10-16-0954 issue(短缝尖峰/断链首桶孤点) → 基线 26-10-16-1057。
**R12(2026-10-16 11:26):** 残余边界收口(活尾与磁盘同判块间真空) → 基线 26-10-16-1126。
**R13(2026-10-16 12:04):** 修 P4 接缝提示漏判(左端放宽一桶宽) → 基线 26-10-16-1204。
**R14(2026-10-16 15:09):** 认领 agg totals 归属错位(复验仍复现)并出三形态对照件 → `plans/26-10-16-1509-plan-agg-hour-totals-attribution.html`。
**R15(2026-10-16 16:28):** 用户拍板形态 D 落地(z 行扩末端快照对 + 两路共用摊配, raw 面零触碰) → issue Done; 基线 26-10-16-1628。
**R16(2026-10-17 04:44):** 文档收口: 计划 0829 → Done, §07 五项拍板全闭, 档案 Status → Done; 唯一未兑现 E2E5。

## 正在进行

- 计划与档案均 Done(R16); 唯一未兑现 = E2E5 真机人工验收(判据链 + 实测帧回归守阵已就位, 待真实重启补记)。
- 未决: `issues/26-10-16-0020-question-agg-rate-lane-invisible-bytes`(agg rate lane 口径)= Open / 未认领, 待拍板; 不影响 raw 面。
- 观测面: 细流仍在累积, 下次重启同型尖峰属设计口径; P2 后为夜均平线 + 观测缝 null, P4 后另有「数据接缝中」提示。

## 本专题关键坐标

- 交付物: 报告 0728(doc-status Done) / 计划 0829(Done) / 派生计划 1509(Done) / 档案 `tasks/26-10-15-webui-qb-traffic-restart-spike-gap.md`(Done)。
- 细流实体: `alltime_dl = net.recv_bytes + net.recv_ip_overhead_bytes`(qB `sessionimpl.cpp:6571/6625`); WebUI 只暴露 payload 速率(`synccontroller.cpp:164-167`); IP 开销量化双向各记(`libtorrent session_impl.cpp:3466-3483`); seed↔seed 断开(`bt_peer_connection.cpp:2123-2129` / `peer_connection.cpp:2344-2350`)。DHT/PeX、uTP 报文开销、tracker 字节均已排除。
- 本仓读侧: `core/traffic_grid.py:412-415`(活尾合流/真空判定) / `traffic_sample_mod.py:602-605`(z/r 判据=速率字段) / `traffic_store.py:19-20`(z 行快照语义) / `torrents/store.py:184-186`(server_state 合并 + 新鲜度挂载) / `traffic_qb.py`(活尾装配, `server_started_at`) / `qb_traffic_chart.js`(轮询节拍 + `_qbSeamHint`)。
- 运行实例快照(2026-10-15 07:47–08:05, 只读): qB v5.2.3 / BT 监听 61323 / WebUI 16585; `dht=pex=lsd=False`、`bittorrent_protocol=0`、`encryption=1`、`outgoing_ports 61234–65000`、`connection_speed=30`; 180 种子 = 120 stalledUP / 36 stoppedDL / 24 missingFiles。
- 坑档: `pitfalls/ops/console-encoding.md`(中文表头探针静默读 0) / `pitfalls/backend/traffic-row-format-extension.md`(z 行扩列位次与回滚) / `pitfalls/web-ui/bucket-granularity-boundary.md`(桶粒度边界) / `pitfalls/testing/credential-shape-write-guard.md`(不可写文件收敛) / `pitfalls/testing/no-uv-fallback.md`。
- 复跑探针(scratch 未入库): `.openclaw/tmp/probe_p0_seam_path.py` / `e2e1_replay_p2.py` / `redverify_p2.py` / `probe_tail_vacuum.py` / `probe1.js`; 报告 §08 另有五条只读复跑清单。

---

<!-- slice: 26-10-29-0243-qb-traffic-agg-idle-zero.md; 最后活动: 2026-10-29 02:51 -->

# qb-traffic-agg-idle-zero

> 摘要: 3d+ 流量图空闲零值区修复: 活尾发布补开放游程合成段(_open_run_hour_samples + _pending_agg_rows 副本), 8 条守阵(含端到端发布), 全量绿
> 最后活动: 2026-10-29 02:51

**R0(2026-10-29 02:43):** 3d+ 流量图空闲零值区修复: 活尾发布补开放游程合成段(_open_run_hour_samples + _pending_agg_rows 副本), 8 条守阵(含端到端发布), 全量绿

**R1(2026-10-29 02:51):** 收尾补齐: 端到端发布守阵(空闲游程经 handler 后快照即带 0 值 hour 行)、`_open_run_hour_samples` 去掉无用 `now` 形参、计划文档 R1 记录两处实现期偏差(doc-status 置 Done)、基线切片数字按最终一跑誊写

---

<!-- slice: 26-10-16-0541-global-traffic-monitor.md; 最后活动: 2026-11-03 06:32 -->

---
summary: 全局流量监视小工具(TM 替代)实施 — 计划 26-10-16-0541(Open); S0–S9 落地, S10 由 26-10-17-0339 S15–S19 承接; 2026-10-18 日志降级、2026-10-20 I/O 入池
---

> 摘要: grilling 三轮 16 问收敛(两次纠正: TM 替代、多实例共享), 计划 26-10-16-0541(Open); S0–S9 已落地(骨架/采样/落盘/控制面/通知/自启/配置面/接收面/过渡文档/守阵); S10 待授权
> 最后活动: 2026-11-03 06:32

# activeContext · global-traffic-monitor(26-10-16-0541)

用户要求: 自写独立监视全局流量小工具 —— 独立于 auto-qb 主进程、开机自启、超阈值通知 auto-qb、设置进 auto-qb WebUI(前置报告 26-10-13-1034 指数据源滞后)。**两次范围纠正**: ①定位 = TrafficMonitor 替代(只记整机流量历史, 不做限速/provider 抽象); ②工具是共享服务, auto-qb 是其配置方与消费者之一, 须支持多实例并发接入。

拍板口径: 整机全适配器排回环; 独立包+独立 venv; psutil 采集; TM 兼容 dat 原子写; 控制面 127.0.0.1:8099+token; Δ≥100MiB 通知+启动补发; 工具自有 config、auto-qb WebUI 代理 PUT; 多实例订阅+心跳租约+各自冷却; 通知→auto-qb 重发快照刷新历史图; dat_path 双支持; 三平台自启由 WebUI 开关幂等注册。

**产出**: 计划 `memory-bank/plans/26-10-16-0541-plan-global-traffic-monitor.html`(Open; S0–S10, 参数/依赖/黄金法则, 验收 E1–E6); 档案 `memory-bank/tasks/26-10-16-backend-global-traffic-monitor.md`(阈值 #4)。

**R1 · S0 已实施(2026-10-16 06:01, clone 46d2ea11)**: 新建 `tools/global-traffic-monitor/` 骨架 11 文件(独立 venv、仅 psutil+filelock、入口 gtm), 零 auto-qb 触碰。出口: `gtm --version`=0.1.0、根环境 import psutil 仍失败、冒烟过。坑: 工具内 pytest 拾取根 pytest.ini → pyproject 补 `[tool.pytest.ini_options]`。基线 s0。

**R2 · S1 已实施(2026-10-16 08:15, 开工同步 @ febac58e)**: sampler.py ~430 行(过滤固定顺序 include→exclude→loopback→down; 重置归零告警不产负流量; 跨天 00:00 硬切; restore state 四形态降级 + dat 今天行 KB→字节兜底[行序不敏感, 与 curves.py 正则逐字一致, 不 import auto-qb])。守阵过; 红验全红; 真机只读冒烟过。坑: redverify 复发+1 形态十(LF write_text 反向污染 + read_text 探针洗白; 改 bytes 层+恒等还原)。基线 s1。

**R3 · S2 已实施(2026-10-16 08:55, 开工同步 @ b688437c)**: storage.py ~430 行(atomic_write_text[tmp+fsync+os.replace]; DatStore[lines 头+新日在前+KB 取整+坏行跳过]; StateStore; FlushPolicy[Δ≥1MiB 或 ≥30s]; SingleInstanceLock[filelock+PID]) + __main__ run(单轮失败不退出)。守阵过; 红验全红; 并发读只见完整文件; kill -9 双恢复; 双实例 fail-fast。坑: platform-fs 两节(Windows os.replace 瞬时拒绝; Git Bash `$!`=MSYS pid)。基线 s2。

**R4 · S3 已实施(2026-10-16 09:46, 开工同步 9d9ec930 后)**: config.py ~240(参数+校验) + server.py ~360(Token urlsafe(32) 启动即生成; 强制 127.0.0.1; /status /config / 订阅三端点[租约 180s]) + storage 订阅表+事件号(RLock) + _run_loop 抽出 + pyyaml 6.0.3。守阵过; 红验全红; 真机冒烟过。真缺陷已修: ①热重载静默杀循环(正则列表误传 list; 修=| 并入+校验层拒+线程存活断言); ②token 惰性生成(start 即生成)。坑: redverify 复发+1 形态三/十一(解释器漂移假红; 钉 venv 解释器)。基线 s3。

**R5 · S4 已实施(2026-10-16 10:16, 开工同步 a3ec82ef 后)**: notifier.py ~230(累计基数=上次事件时刻当日合计, **仅派发成功后推进**[首版踩已修]; 跨天/回退只重置基数; 每订阅者一线程; 先落盘→事件号+1→派发) + bump_event_id + 守阵过; 真机 12s 193 帧而假死端点占满 3s; 红验过。发现: ①基数推进纪律; ②红验 M2 未判红(被 total<_last_total 兜底掩盖; red-verify-must-hit-behavior 新形态「兜底分支掩盖」); ③PUT /config 全量覆盖实锤 → S6 读后写。坑: redverify 复发+1 形态十二(TimeoutExpired 未接住)。基线 s4。

**R6 · S5 已实施(2026-10-16 11:09, 开工同步 5654b778 后)**: installer.py ~460(AutostartPlan 解释器=sys.executable; Win schtasks ONLOGON / Linux systemd user / macOS launchd plist; 注入式 Runner; 只信退出码)。幂等判据严格化: 期望态达成才 no-op, Linux/macOS 须「文件一致且已启用」, 只查存在会误判。红验过。真机降级: schtasks.exe 被 Program Blacklist 拦(真判据 stderr PROGRAM BLOCKED) ⇒ 计划任务真注册+登录自起未跑(缺口待补); 其余 PASS。新坑 session-program-blacklist。顺序: 先落命令面, S6 后消费, 无倒挂。基线 s5。

**R7 · S6 已实施(2026-10-16 11:45, 开工同步 3473aa9a 后)**: 首个触碰 auto-qb 步骤; 计划改版(拍板 B 案): 工具控制面新增 POST /autostart, auto-qb 经 HTTP 代理。落点: ①配置段 4 点同步(schema i-traffic; 6 键 enabled/tool_url/token_path/subscribe/cooldown/autostart); ②POST /autostart(200/501/500/400); ③代理 /status、/config(400 透传, 不可达→502)、/autostart(501); ④设置页分区(读后写)。新键过守卫(键面 160→167); 守阵过; 红验过。发现: ①parse_time 须带单位("0S"); ②前端 v-if 链跨分片, 新分区只能链尾→frontend-split。坑: single-file-coverage-gate 复发+1(裸跑单文件假红; 加 --no-cov -n 0)。基线 s6。

**R8 · S7 已实施(2026-10-16 14:04, 开工同步 16d66653→fd26c4e7 快进)**: 接收面 POST /api/traffic/monitor/notify(六键体校验 400; 事件号+冷却双闸 per app 实例; 闸门/未启用 200+action, 体非法 400) + `webui/tool_client.py`(控制面 I/O 全在订阅线程、主循环只置期望态、stop 有界 join、心跳 404 自愈) + module 三时刻接线 + refresh_traffic + speed_curve_mod 只读刷新(不查档/不读写限速)。守阵含端到端; 红验过。发现: ①注销须用注册时地址/密钥路径; ②期望态按恒等 True 判(MagicMock 桩段会起线程); ③stop() 超时不摘引用(否则双订阅); ④写入判据拦下四文件, 授权改写。未闭合 E2。基线 s7。

**R9 · S8 已实施(2026-10-16 17:37, 开工同步 22f0dad8→1ae16235 快进)**: 纯文档轮: `docs/configuration.md` 新段(定位/目录/参数表覆盖语义/自启/6 键/迁移检查单/24h 对照[容差 ≤5%]/双写者禁令)。出口: 文档守卫全绿, links/drift/caps 过; 检查单可跑部分实跑(gtm run 45s: 30s 节流/token 43 字符/401+200)。发现: 3 文档被写入判据拦下, 授权等价改写; 「整文件级探针」并入坑档(复发+1)。未闭合 E1 24h 与自启真机。基线 s8。

**R10 · S9 已实施(2026-10-16 18:24, 开工同步 f8db7019)**: 只补缺口: 新增 `tests/test_traffic_monitor_dat.py` 2 条(工具 DatStore 真写者产出 dat → dat_path 只读刷新读回: 历史行升序/KB 取整/累计重算/更早月份只进历史; 格式单点同值) + notify 补「错 Bearer 也 401」。写法约束: 根测试禁止起子进程 ⇒ 进程内按源码路径加载工具写者(只替 import psutil)。红验过。发现: ①跨侧守阵不能起子进程; ②test.full 踩无 uv on PATH(复发+1); ③窄池假存活(mutation-pool-artifact 复发+1)。未闭合 S10。基线 s9。

**待办(截至 2026-10-20)**: S0–S9 已落地, S10 待逐项授权。①S5 真机缺口(计划任务真注册+登录自起, 需解锁 schtasks), 同缺口在 S8 检查单第 3 步再现; ②S7/S8 真机联调(E2); ③E1 24h 并行对照。档案 2026-10-30 记: S6–S8/S10 已由计划 26-10-17-0339 S15–S19 承接, 本计划口径收口。

**R11(2026-10-18 19:48)**: 通知链路三级日志 INFO→DEBUG: 用户报大流量日(事件 #1200)刷屏, 拍板降级; 消息文本不变, 触发与两条 WARNING 不降; 新增 2 条日志级守阵。提交 318617c9 已推 Gitee develop; 合并后闸门被远端 d7fc97ae(别会话 alias_fs P0)的 6 条环境性红挡下(WinError 1314 无 symlink 权限, 无关本轮), 按补推口径 ship.push 收尾; 未替别会话改码。基线 26-10-18-1947。

**R12(2026-10-20 23:49)**: 只读排查 gtm 常驻进程「I/O 其它」偏高: 实测 72.42 次/秒(累计 782 万)= psutil 网卡枚举控制操作(每轮 177 次), 读 0 次/秒、写 0.42 次/秒=设计值; 入池 perf issue 26-10-20-2345(Open), 未改码。

**引用**(`mb/` = `memory-bank/`): `mb/reports/26-10-13-1034-report-global-traffic-source-lag.html`; `mb/plans/26-10-17-0339-plan-global-traffic-source-integration.html`; 基线 `mb/testing/baselines/attachments/`: s0–s9 = `26-10-16-{0601|0815|0855|0946|1016|1109|1145|1404|1737|1824}-global-traffic-monitor-s{0..9}.md` + `26-10-18-1947-notify-log-debug.md`; 坑档 `mb/pitfalls/`: `testing/{nested-pytest-config,redverify-anchor-lineendings,red-verify-must-hit-behavior,single-file-coverage-gate,mutation-pool-artifact}.md`、`backend/platform-fs.md`、`ops/session-program-blacklist.md`、`web-ui/frontend-split.md`; issue `mb/issues/26-10-20-2345-perf-gtm-sampler-other-io.html`; 文档 `docs/configuration.md`、`mb/config-reference/keys.md`、根 `README.md`。

**R13(2026-11-03 06:16):** 修复 gtm 跨进程单实例锁用例在英文 Windows runner(cp1252)下 print 中文 UnicodeEncodeError 失败: 子进程注入 PYTHONIOENCODING=utf-8 + 捕获端 encoding=utf-8, 同文件另一子进程用例与 manual_e2e_relay 同因加固; 被拒信号(BUSY+PID)断言提到退出码之前; cp1252 复现改前红改后绿, test.gtm 全绿; 坑档并入 testing/ci-only-guard.md

**R14(2026-11-03 06:32):** 生产侧 stdio 编码兜底: gtm __main__ 入口新增 _utf8_stdio() 把非 UTF-8 的 stdout/stderr reconfigure 成 UTF-8(errors=replace, 中文不丢, 退出码语义不变), 覆盖 print/argparse/logging 出口; 新增 3 条守阵(cp1252 TextIOWrapper 整行中文 / python -m gtm 帮助 exit 0 / endpoint stderr 中文 exit 1); 修复 test_module_main_guard_runs_cli 的 RuntimeWarning(runpy 前临时摘除 gtm.__main__ 再还原, 不压制警告); test.gtm 全绿且 0 warning; 同因并入 pitfalls/ops/console-encoding.md

---

<!-- slice: 26-10-17-0339-global-traffic-source-integration.md; 最后活动: 2026-10-31 10:36 -->

---
summary: 全局流量来源改版(一键切换 + 自动拉起) — grilling 五轮收敛, 产出独立计划 26-10-17-0339(Open); 推翻旧计划 26-10-16-0541 的配置落点/发现机制/自启触发/用户可见命名四组拍板; R1 就地改版(26-10-17-0429): 拉起改走工具侧启动器(D19) + D13 收敛为工具侧唯一裁决; 工具侧 S11–S14 已实施(目录定位/数据落点/启动器 · 发现指针与锁锚点 · 随机端口与 endpoint · 自启意图/全称改名/gitignore); S15(auto-qb 配置面合并 + v4→v5 升级链)已实施; S16(auto-qb 探测-拉起-订阅编排: agent 联动单点 + 订阅方向改读发现指针)已实施; S17(auto-qb 侧设置页合并: 旧过渡 stub 段退休 + 「全局流量来源」单卡[provider 单选 + 五态状态区 + 立即拉起/自启 + 文件选择器] + 曲线卡删来源)已实施; S18(守阵补口 4 条 + 文档四处回写 + 三条新坑 + 新基线切片)已实施; R2 就地改版(26-10-17-1447, 真机事故驱动): 删 `global_traffic_monitor.data_dir` 配置键与设置页字段, 取数路径收归工具发现指针(新单点 `core/traffic_source/paths.py`, 旧 `active_dat_path()` 退休, D20/S20), 自启提权缺陷入池 issue 26-10-17-1455; S19 待逐项授权
---

> 摘要: 用户诉求「全局流量监视器设计不成熟, 特别是与 auto-qb 的联动」: ①auto-qb 一键自动拉起工具(免配端口/密钥) ②工具同时配置 Traffic Monitor 时怎么办 ③两处配置(限速曲线卡的 dat_path 与独立段 global_traffic_monitor)合并为一处, 来源一键切换。经 grilling 五轮 36 问收敛(用户四次纠正), 产出独立计划 `memory-bank/plans/26-10-17-0339-plan-global-traffic-source-integration.html`(doc-status Open, doc-topic `global-traffic-source-integration`)。**R1 就地改版**(26-10-17-0429): 用户指出「把 `--autostart` 固化进启动器」与 D13 冲突 ⇒ 启动器契约(D10 改写 + 新增 D19) + D13 收敛为「启动器恒定携带意图, 工具 config 唯一裁决」。
> 最后活动: 2026-10-31 10:36

# activeContext · global-traffic-source-integration(26-10-17-0339)

**用户诉求(原话要点)**: 全局流量监视器目前设计不成熟, 特别是与 auto-qb 的联动; 设想是 auto-qb 能**一键自动拉起**全局流量监视器, 不需要过多配置、不需要写端口/密钥; 同时要考虑**如果同时配置了 Traffic Monitor 怎么办**; 目前配置全局流量监视器与 Traffic Monitor 在**两个不同的地方**, 需要改为一处, 设想是**全局流量信息来源一键切换**。

**关键事实(实施前须复核漂移)**:
- 现联动只经工具控制面 HTTP, 端口来自 `tool_url`、密钥来自 `tool_token_path`(或镜像平台默认数据目录); **工具没在跑时 auto-qb 什么都做不了** —— 连 `autostart` 开关本身都要 `POST /autostart` 打到控制面(鸡生蛋), 故「一键拉起」在旧设计下逻辑上不可能。
- 工具 = 独立 venv 的包(psutil/filelock), auto-qb venv **刻意不装 psutil** ⇒ auto-qb 只能起子进程, 解释器须指向工具环境; 工具 CLI 旧只有 `run [--data-dir]`。
- auto-qb **已有 config schema 迁移链**(`MIGRATIONS["config"][n]` + 启动物化原子写回/备份), 「配置升级路线」落在它上面(现到 v4)。
- `tests/sidefx.py` 的 POPEN 白名单只放行 `node` 与临时 wrapper ⇒ auto-qb 侧「拉起工具」必须做成**可注入单点**。
- 生产 `config.yml` 目前**只用 TM**, **未配** `global_traffic_monitor` 段 ⇒ 迁移痛点小。

**产出计划拍板 19 条(D1–D19, 见计划 §02)**: 单一来源开关(`traffic_source.provider`, 严格互斥不静默回退) / 配置落点合并(顶层 `global_traffic_monitor` 退休, 曲线段只留 curves; 不含 auto-qb 侧 `autostart` 键) / 迁移走 v4→v5 升级链 / 工具进程形态不削减(独立 + 开机自启 + 多实例共享) / auto-qb 只做「探测 → 缺席一次性引导拉起 → 控制面订阅」**不当守护者** / 发现指针 `endpoint.json` 落**用户级平台目录**且与 `--data-dir` 解耦 / **就绪判据只认探活** / 单实例锁锚指针旁且抢输不占端口 / **随机端口**(`http_port` 默认 0 + `endpoint` 子命令) / 拉起解析(`tool_exe` 显式覆盖 → `tool_dir` 走**工具侧启动器**, auto-qb 不拼 uv、不认识入口名与子命令 = D19) / 双模目录定位(frozen 用 `sys.executable`, 否则 `__file__`) / 数据默认落「工具安装目录/data」(旧用户目录数据一次性搬迁) / **自启意图恒定写死在启动器, 是否注册由工具 config `autostart` 唯一裁决**(用户关过不被装回), 设置页开关走 `POST /autostart` / 多实例竞争靠锁前置 + 退避 / 设置页并成一张卡 / **改名只限用户可见面**(包名与内部文档继续用 gtm = D16) / 删 `tool_url`/`tool_token_path`/`subscribe`/`autostart`。

**计划步骤**: S11 工具侧目录定位 + 数据落点 + 启动器 → S12 发现指针与锁锚点 → S13 随机端口与 `endpoint` 子命令 → S14 启动器自启意图/改名/gitignore → S15 auto-qb 配置面与升级链 → S16 探测-拉起(零参执行启动器)-订阅编排(可注入单点) → S17 设置页合并 → S18 守阵/基线/文档 → S19 真机验收(并入旧 S10)。每步需用户**逐项显式授权**, 「继续」不算。

**与旧计划的关系**: 旧计划 26-10-16-0541 的**工具本体 S0–S9 全有效、不追改**; 其旧 S6/S7/S8 被本计划 S15–S17 取代, 旧 S10 并入本计划 S19。本计划用**独立 doc-topic** 以避 docmap 分叉, 未改动旧计划文件。

**已实施(S11–S16; 每步详解见 `tasks/26-10-17-backend-global-traffic-source-integration.md` 进度日志)**:
- **S11**(26-10-17-0534): `storage.resolve_tool_root()` 单点(frozen 取 `sys.executable` 所在目录, 源码态由 `__file__` 上溯到含 pyproject.toml 的工具根) + `default_data_dir()` 改判「<工具安装目录>/data」+ env 改名 `GLOBAL_TRAFFIC_MONITOR_DATA_DIR` + 旧用户目录一次性搬迁(幂等; 显式 `--data-dir` 不搬迁) + 启动器 `launch.cmd`/`launch.sh`(恒定 `--autostart`、不传 `--data-dir`、优先自带 venv 解释器、uv 兜底)。
- **S12**(26-10-17-0623): 发现指针 `endpoint.json`(`_platform_data_home()` 单点 + 十字段 schema + 原子写/幂等删) + 锁锚点从 `data_dir` 迁到指针目录 `instance.lock`(与 `--data-dir` 解耦); `ControlServer.start()` bind 后写指针、`stop()` 删; 写失败只 WARNING 不阻断。
- **S13**(26-10-17-0721): `http_port` 默认 8099 → `0`(内核分配随机空闲端口, `_PORT_RANGE` 下限放开到 0) + `endpoint` 子命令读**同一**指针打印 host:port/token_path/data_dir(端口随机后手工调试唯一出口)。
- **S14**(26-10-17-0825): ①`config` 新增 `autostart` **布尔键**(默认 `true`, 只收真 bool, 进 `_BOOL_FIELDS` 全量校验) + `run --autostart` **布尔开关**(`store_true`, 不承载取值) 顺带幂等注册 —— 裁决权在 config `autostart`(false → 本次 no-op, 用户关过不被装回), 注册排在锁 acquire 后、`server.start()` 前(指针现货探测与真值一致), 失败只 WARNING 不阻断; ②`POST /autostart` 成功回写 config `autostart`(= install/卸载); ③**用户可见面全称改名**(CLI 脚本名/`prog`/`version`/CLI 文案前缀/锁冲突文案/注册项 task·unit·label/systemd Description/启动器兜底命令/工具 README; **包名 `gtm` 与 `-m gtm` 模块名不动**); ④`.gitignore` 增 `tools/global-traffic-monitor/data/` 与 `run/`。
- **S15**(26-10-17-1007): auto-qb 配置面合并 + v4→v5 升级链 —— 删顶层 `global_traffic_monitor` 段、新增顶层 `traffic_source` 段(`provider` + `traffic_monitor.dat_path` + `global_traffic_monitor.{tool_dir,tool_exe,data_dir,notify_cooldown_s}`), 曲线段只留 curves/interval/enabled; `GlobalTrafficMonitorConfig` 降**过渡 stub**(S16/S17 重接后删); config schema 抬 v5 + 注册 v4→v5 迁移(曲线内联 dat_path 上移、旧 gtm 段仅迁 notify_cooldown_s 并整段删、provider 推导、逐键 note、幂等); 取数单点 `TrafficSourceConfig.active_dat_path()`(D1 严格互斥)被 `speed_curve_mod` 与 expr 门控共用; 键面基线抬 v5。
- **S16**(26-10-17-1113): auto-qb 侧**探测 → 引导拉起 → 订阅编排** —— 新增联动单点 `core/traffic_source/agent.py`(`probe()` 读发现指针 + `GET /status` 探活[只认 200]; `ensure_running()` 缺席时**零参数执行启动器**并 detached 拉起、首次引导窗口 120s/常态 10s、失败固定 30s 退避[D14]; `status()` 供 UI 读五态[未安装/未运行/拉起中/已就绪/拉起失败]); **拉起做成模块级可注入单点** `agent.launch_tool`(生产真 `Popen`[Windows `DETACHED_PROCESS`], 测试注入假动作以绕开 sidefx POPEN 白名单); 编排挂**既有订阅线程**(每轮先确保可达再注册, 不占主循环); **密钥与端口全来自指针**(删 `tool_url`/`tool_token_path` 读路径, D6)。
- **S17**(26-10-17-1311): auto-qb 侧**设置页合并**(D15) —— ①旧过渡 stub 段退休: 删 `GlobalTrafficMonitorConfig` 与 `Config.global_traffic_monitor`, `WebUIModule.sections()` 收缩为 `("web",)`, 路由 `_tm_conf` 改读 `traffic_source.global_traffic_monitor`; **「联动是否启用」由 `provider` 派生**(修 `conf.enabled` 属性缺失的生产级隐患), notify 闸门同判; ②新增写端点 `POST /api/traffic/monitor/relaunch`(409 = 无订阅线程可促) + `WebUIModule.agent`/`request_relaunch`; ③设置页新增一张卡「全局流量来源」: provider 单选 + 选中面展开(TM 仅 `dat_path`; 工具面 `tool_dir`/`tool_exe`/`data_dir`/`notify_cooldown_s`) + 底部**五态**状态区 + 「立即拉起/重试」(前端有界轮询)/「打开工具设置」+ 自启开关(状态读指针 `autostart_registered`, 拨动走 `POST /autostart`, 失败回滚) + 找不到工具时的文件选择器(写 `tool_dir`/`tool_exe`, 受 `/api/fs/dirs` 白名单限制) + 工具参数(高级折叠, 经控制面读后写); ④**曲线卡删来源字段**(来源只在设置页一处)。

**待办**: ①S11–S18 已实施; S19(真机验收) **显式授权**后实施(独立收尾+提交); ②旧计划 26-10-16-0541 的 S10 与本计划 S19 归并方式待拍板; ③`docs/configuration.md` 与根 README 回写已在 S18 完成(工具章节整段改版到随机端口/指针/启动器/自启裁决现实); ④S18 只补了 §08 仍缺的 4 条守阵, 工具侧五类(S11–S14)与 auto-qb 侧三类(S15–S17)既有守阵已逐条核过、不重复造。

**R1(2026-10-17 13:53):** S18 实施: 守阵补口 4 条(拉起不拼 uv/入口名 · 指针跨侧镜像 · 工具运行期目录 gitignore · provider 取数互斥) + docs/configuration.md 工具章节整段改版 + README + keys.md 两处口径修正 + 三条新坑 + S18 基线切片; 全量 `test.full` 绿(数字见 kb.baseline)

**R2(2026-10-17 14:47, 真机事故驱动):** 现象「工具已就绪但顶栏/历史图全空」定位为**取数路径有两个来源** —— 14:00 的 v4→v5 迁移按「旧 gtm 段存在」把 `provider` 推到 `global_traffic_monitor`, 而旧段里根本没有 `data_dir` 可迁, 于是 `active_dat_path()` 返回空串(日志 `读取流量数据失败(): No such file or directory: ''`), 状态区却显示指针里的真实目录。用户拍板: **数据目录既然已在 `endpoint.json` 里, 就不该再显示/配置**。改法(计划 R2 + 新增 D20/S20): 删 `traffic_source.global_traffic_monitor.data_dir` 配置键与设置页字段; 取数改走**运行期单点** `core/traffic_source/paths.py::dat_path(config)`(tm 读配置 / gtm 读指针 `data_dir` + 契约文件名, 只读不探活、无缓存), `unavailable_reason()` 让报错文案与分支同源; **删** `active_dat_path()` 不留第二入口; `_expr_gate` 对 gtm 恒放行(路径是运行期事实); 残留 `data_dir` 键按**通用未知键报错**; **不做 v6 迁移**(测试期未上线, 手工清理)。已改: models / schema / validation(sections+rules) / loaders / 新增 paths.py / speed_curve_mod 两处 / expr env / 键面基线 + 8 条新用例(删 4 条旧 `active_dat_path` 用例) / docs/configuration.md / keys.md / 计划 R2 / 新坑 `pitfalls/backend/config-duplicates-runtime-fact.md` / 基线切片 26-10-17-1457。自启 `schtasks ONLOGON` 需提权且失败静默 → 独立入池 `issues/26-10-17-1455-bug-gtm-autostart-elevation.html`(Open, 未认领)。

**R3(2026-10-31 04:24):** 计划 26-10-17-0339 文档漂移三修(头部状态补 S20 / §01 旧计划已 Done / 变更记录 R1-R2 行序归位)并补 R4; 状态保持 In Progress —— S19 真机验收四场景仍待逐项授权(现网指针 + /status 探活 + 订阅在跑, 但无逐项验收记录)。本切片文件名由缩短 slug traffic-source-integration 归位为专题主键 global-traffic-source-integration(原 26-10-31-0421 重复切片已删)

**R4(2026-10-31 05:41):** S19 真机验收完成(桩测·Windows 侧), 计划收口 Done, P3 发现入池 issue 26-10-31-0537

**R5(2026-10-31 10:36):** 认领修复 issue 26-10-31-0537: gtm _autostart 成功路径新增 _patch_endpoint_autostart() 即时 patch 发现指针 autostart 字段(建议修法①; autostart_registered 现货态改写 + autostart_error 清空; 指针缺失静默/读坏只 WARNING 不阻断, Windows 下 FileNotFoundError 不可辨缺失/父路径异常已入坑档 platform-fs); 回归三案落 test_server.py, test.gtm 与 test.full 全绿(数字见 kb.baseline 切片 26-10-31-1018); issue 置 Done, 发现指针坑档补写点事实(⑤)

---

<!-- slice: 26-10-30-0650-backend-gtm-review-t-fixes.md; 最后活动: 2026-10-30 06:50 -->

# backend-gtm-review-t-fixes

> 摘要: T-01/T-02/T-03 三缺陷收口: sampler day_rolled 方向检查+钉日界, config http_host 回环约束, server config 写临界区 _config_write_lock; 三 issue 翻 Done, 守阵 +9 条, 全量 test.full 全绿与覆盖率见 kb.baseline 最新切片(26-10-30-0649)
> 最后活动: 2026-10-30 06:50

**R0(2026-10-30 06:50):** T-01/T-02/T-03 三缺陷收口: sampler day_rolled 方向检查+钉日界, config http_host 回环约束, server config 写临界区 _config_write_lock; 三 issue 翻 Done, 守阵 +9 条, 全量 test.full 全绿与覆盖率见 kb.baseline 最新切片(26-10-30-0649)

---

<!-- slice: 26-11-03-2151-gtm-day-total-inflation.md; 最后活动: 2026-11-03 21:51 -->

# gtm-day-total-inflation

> 摘要: S9 收尾：修正 issue 斜杠日期与 fetch_last_spike 失败矩阵前置；sampler/docs 文档回写；plan/issue 置 Done；全量实测基线入切片；kb.check 全绿（未合 develop、未 push）
> 最后活动: 2026-11-03 21:51
**Refs（切片原文）:** memory-bank/tasks/26-11-03-backend-gtm-day-total-inflation.md, memory-bank/plans/26-11-03-1102-plan-gtm-day-total-inflation.html, memory-bank/issues/26-11-03-1039-bug-gtm-day-total-inflation.html, memory-bank/testing/baselines/26-11-03-2148-gtm-day-total-inflation.md

**R0(2026-11-03 21:51):** S9 收尾：修正 issue 斜杠日期与 fetch_last_spike 失败矩阵前置；sampler/docs 文档回写；plan/issue 置 Done；全量实测基线入切片；kb.check 全绿（未合 develop、未 push）

---

<!-- slice: 26-11-03-2354-backend-gtm-day-total-inflation.md; 最后活动: 2026-11-03 23:54 -->

# backend-gtm-day-total-inflation

> 摘要: code review 整批 GTM 虚高修复(通过, 无阻塞缺陷): 3 条次要发现当轮修复(取数专用 3s 超时/interval_hint 入口守卫/overlay 保存幂等), 1 条评审误判撤回; 补 4 条守阵测试; 评审报告 26-11-03-2346 与新基线切片入库
> 最后活动: 2026-11-03 23:54
**Refs（切片原文）:**

**R0(2026-11-03 23:54):** code review 整批 GTM 虚高修复(通过, 无阻塞缺陷): 3 条次要发现当轮修复(取数专用 3s 超时/interval_hint 入口守卫/overlay 保存幂等), 1 条评审误判撤回; 补 4 条守阵测试; 评审报告 26-11-03-2346 与新基线切片入库

