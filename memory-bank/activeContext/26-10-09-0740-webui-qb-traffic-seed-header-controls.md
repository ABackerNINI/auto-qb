# webui-qb-traffic-seed-header-controls — 种子流量图的档位/纵轴控件落点 + 统计栏口径注解形态

> 摘要: 本专题三轮同日落定 —— ①上一轮: 控件补进种子头部(修「控件消失」); ②第 2 轮: 用户否决头部落点
> (「太挤、小窗口下会变形」)⇒ 改落**图下统计栏**(`.hist-summary` 内 `.qb-statctl`, 排在「下载累计」之后),
> 统计栏本体门放宽为 `qbCurSummary || qbCurScope === 'torrent'`; ③第 3 轮: 统计栏常驻口径注解
> 「累计为窗口内增量(断线期不计)」退场, 改为**上传累计 / 下载累计两个读数的悬浮提示**(`:title="qbCurSummaryHint"`,
> 走全局断供管道 → `data-aq-tip`)。第 3 轮顺带把统计栏从两行收回**单行**(33px), 图由 235px 回到 259px ——
> 第 2 轮「图少约 31px」的代价随之消失。**全局/分组流量形态全程零改动**; 零 JS 改动; 守阵只改写既有断言
> 口径(零新增测试函数); 真浏览器三皮肤 + 四档窄视口实测不越界、tooltip 正常、零 pageerror。已闭环。
> 最后活动: 2026-10-16 03:00

**Refs:** memory-bank/tasks/26-10-09-webui-qb-traffic-seed-header-controls.md,memory-bank/testing/baselines/attachments/26-10-09-1207-webui-qb-traffic-seed-hint-tooltip.md,memory-bank/testing/baselines/attachments/26-10-16-0300-webui-qb-traffic-statbar-align.md

- 任务档案: [26-10-09-webui-qb-traffic-seed-header-controls](../tasks/26-10-09-webui-qb-traffic-seed-header-controls.md) —— 三轮的根因/取舍/实测数字都在档案, 本切片只留指针。
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
