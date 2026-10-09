# WEB UI 产出口径与令牌

> 摘要: 菜单/入口分层、令牌分工、按钮体系、悬浮提示、HTML dark 主题 —— 前端产出口径的唯一出处。
> 触发: WEB UI 约定, 菜单分层, 令牌, 主题, dark, HTML 产出, tooltip, 悬浮提示

## WEB UI 菜单/入口分层原则 (2026-09-17 用户明确要求记入)

右键菜单(及同类动作入口)按**使用频率**分两层, 不是按功能族平铺:

- **一级 = PT 日常高频动作**: 开始 / 暂停 / 强制汇报 / 详细信息 / 限速 / 移动 / 重命名 / 重新校验 / 导出 .torrent / 打开目标文件夹 / 删除。
- **次级菜单(flyout) = qB 通用低频能力**: 队列(置顶·上移·下移·置底) · 自动种子管理 · 超级做种 · 强制开始 · 分享率限制 · 复制(名称/哈希/magnet) → 全部进「**更多操作**」(R10-14 由「高级能力」改名: 这些是 qB **常规**种子控制, 文案不该评价能力高低; 「更多操作」只表达层级, 后续增删子项也不会失准)。
  - ⚠ **一级只允许有一个次级菜单入口**(CTX-06, 2026-09-24): 复制族曾单列第二个子面板, 用户得先选"该进哪个" —— 已并入「更多操作」末尾。低频动作归堆, 不新开入口。
  - ⚠ **同一批动作的菜单分支项集必须一致**(2026-10-09): `shared/tpl/ctx-menus.html` 的 `menu.multi`(多选批量)与 `v-else`(单组)是**同一批动作的两条入口** —— 给一支加动作项必须同步补另一支(组菜单独有的 打开文件夹/流量图 除外), 否则用户在某条路径上「找不到该动作」(2026-10-09 用户报「单组右键菜单缺选项」)。组级入口**复用多选链路**(目标 = 该组全部成员, 走 `_groupTargets`), 不另开旁路。守阵 `test_frontend_ctx_menu_group_actions_parity`; 机理见 pitfalls/web-ui/ctx-menu-branch-parity.md。
- **判据**: 该动作是否"每天都要点" —— 不是则下沉。菜单项数增长时**先问能否归入既有次级菜单**, 不要直接往一级追加。
- 实现: `.ctx-item.has-sub` + `.ctx-sub`(锚在父项右缘, 靠右时 `.flip-x` 向左翻); hover 与点击都能展开; 状态的唯一权威是 `app.js` 的 `subMenu`(随 `menu.visible` 关闭一并复位); 移出**父项**后延迟 ~180ms 收起(见 pitfalls/web-ui/overlays.md「flyout 次级菜单」—— 延迟只为跨过 4px 缝隙, 且收起只能挂父项)。

## WEB UI 令牌分工 (2026-09-17 第十轮)

同名语义只允许有一个令牌族, 新增值先找族再考虑加令牌:

- **状态色族**(`--green/--blue/--error/--warn` + `--paused-*`): 表达**种子/行状态**。只染有语义的状态; 0 值/
  "—"占位不染; 芯片(站点/标签/分类)保持自身语义色不跟随行色(决策 D6-A —— 芯片表达**成员级**语义, 跟随行色会抹平这层信息)。
  `--paused` 是唯一"无色相"的成员, 取值 = `--fg-muted`(中性中间调), 配 `--paused-soft: transparent` + `--paused-line: var(--border-strong)`
  —— **暂停/其它一律"不铺底 + 中性描边"**, 不许落回 `--surface-2`(暗底 = 白 6%, 读作"太白/没颜色")。该族**各套 UI 各声明一处**(atlas/prism/console)
  (星图 `:root` / 棱镜 `themes/*.css` 五主题), 改值必须两处同改。
- **选中态族**(`--sel-bg/--sel-line/--sel-bar`, 五主题均取**非绿**的靖蓝族): 只用于"用户选中"语义; **不得**再引用
  `--accent`/`--accent-soft` —— 品牌主题(orbit)下 `--accent` 与做种 `--green` 同族且明度接近, 用户分不出"选中"与"做种"。
- **流量方向色族**(`--today-up/--today-down`, 星图 `:root` 一处 + 棱镜五主题各一处, 改值必须全处同改):
  表达**上下行流量方向**, 消费面 = 历史流量图 SVG / qB 流量图(uPlot 经 `_qbChartTokens()` 现读令牌;
  2026-10-08 起同源还喂**画布注解层**: 限速虚线随方向取 `up/down`, 缺口斜纹取 `grid` 令牌) /
  状态栏今日统计(`.sb-item.sb-today .v-up/.v-down`) / 状态栏速度组方向图标(`.sb-spd .ico-up/.ico-down`) /
  i-traffic 组图标(内联 `var(--today-*)`)。取值 **上行 = `--indigo`(紫) / 下行 = `--teal`(蓝绿)**
  (2026-10-04 用户拍板交换)。⚠ 速度组图标**不要**改全局 `.ico-up/.ico-down`(绿/蓝, 还喂顶栏「种子」等
  非流量位置), 只能按 `.sb-spd` 作用域覆盖。状态栏限速值(`.sb-spd .lim`)是**参考值**, 用中性灰 `--fg-dim`
  (与做种要求值 `.m-pair .req` 同款), 不随方向染色。
- **表面/底色族**: 状态栏用专用 `--statusbar-bg`(与页底形成可见层级); **不要改 `--glass`** —— 它同时管顶栏,
  改它会连带改顶栏。
- **尺寸族**: 弹窗宽度取 `--modal-w-narrow/base/form/add`/`--modal-wide-w`(各套 UI 同值同族); 新增弹窗只选档,
  不写新数字(这正是此前"第 N 次调大"的成因)。
- **单点口径原则(通用)**: 同一数据/口径在两个以上地方出现时, 收成 computed/method 单点(如 `speedLimitBytes`
  限速取数、`cellSeedingTime/cellRatio/cellPeers/cellAvailability/cellTime` 单元格口径、`_deleteDetails` 删除详情行、`colAlignCss` 列对齐),
  模板里只引用不重算。新增展示口径时先问"它是否已被别处实现"。

## WEB UI 按钮体系 .bt (2026-09-26 第十一轮)

全部动作按钮收敛一族 `.bt`, 各套 UI 同一套语义类名、外观各按其设计语言(方案定案与全状态陈列见 `plans/26-09-26-0538-plan-webui-button-3-proposals.html`):

- **语义变体**: `.bt`(次钮, 默认) / `.bt.primary`(主) / `.bt.ghost`(幽灵) / `.bt.danger`(危险·描边) / `.bt.danger-solid`(危险·实心, 用于确认框的危险确认) / `.bt.icon`(图标钮) / `.bt.sm`(小档 28px)。标准档: 星图/棱镜均 34px。
- **两套配方**: 星图 B(胶囊 999px, 主钮=品牌渐变+inset 高光, hover 泛 accent 柔光) / 棱镜 C(圆角 5px 强声明, 主钮=实心 accent+深色字, 按下 scale(.98))。
- **状态纪律**: hover 换 accent-line 描边 / 按下反馈 / `:focus-visible` ring / 禁用 .45 / 加载中 `.spin` 图标; `<button>` 一律显式 `color`(UA 默认色坑见 pitfalls/web-ui/layout-css.md)。
- **双色令牌族**(`--on-accent/--on-accent-ink/--on-error`): 实心 accent/error 底上的前景色, 星图 `:root` 一处 + 棱镜五主题各一处成对声明(亮色主题翻转为白字), 改值必须全处同改 —— 与状态色族同纪律。
- **存量家族归属**: ce-btn/ce-icon 已退役(守阵 `test_frontend_button_system_paired` 钉零残留); bulk-btn 随批量控制条退役(2026-10-05, 守阵 `test_frontend_bulk_bar_retired` 钉模板/三套 CSS/JS 助手零残留); row-btn/prio-btn 保持紧凑尺寸只并入配色与状态语言; 登录页与页签/筛选 chip 不入族(各自视觉语言), 设置页 hb-*(Ash Thorp)保留其形。

## WEB UI 悬浮提示 .aq-tip (2026-09-28)

全局 tooltip 收敛为自绘单例, **新元素一律继续写原生 `title` 属性**(模板侧零成本接入), 不许再自造浮层:

- **触发面**: 一切带 `title` 的元素(含 Vue `:title` 绑定); 调度单点在 `shared/ui_feedback.js` 尾部的纯 DOM 委托层(不进 mixin)。机制(2026-10-04 二轮定稿, **原生 tooltip 断供式**): MutationObserver 盯全文档, title 属性在任何时刻出现(模板渲染 / Vue `:title` 写回 / 新插入节点)即刻迁进 `data-aq-tip` 并删掉原属性 —— DOM 里不存在 title, 原生气泡无从弹出; 浮层触发 = document 级委托 mouseover / focusin 命中 `[data-aq-tip]`, 350ms 后弹 `.aq-tip`, 文案 show() 时现读最新值。前两轮的「hover 时摘 + 离开还原 + 悬浮期补摘」被废弃 —— Vue 轮询把指针下节点整个换掉时指针不动、mouseover 不触发, 新节点带 title 还魂叠出双 tooltip(见 pitfalls/web-ui/aq-tip-nested-title-double.md)。代价: title 不再还原(原生悬浮语义由 `.aq-tip` 承接)。点击 / 滚动 / 窗口失焦立即收起。
- **定位**(2026-10-04 修): 上方优先 → 上方放不下转下方 → 两侧都放不下才允许溢出视口; **任何分支都不越过锚点**。旧版末尾无条件把浮层夹回视口内, 状态栏这类底缘锚点一旦走「转下方」分支就会被拉回状态栏上, 正好盖住它自己描述的元素。锚点在 350ms 延时窗口内被 Vue 整个换掉时已脱离文档(rect 全 0), 按记录的指针坐标 `elementFromPoint` 重解析当前锚点, 解析不到就收起(否则浮层落到视口左上角)。
- **样式单点**: `shared/console_hub.css` 的 `.aq-tip` 段(三皮肤同载)。视觉复刻设置页发光按钮配方: 描边 `--accent-line` + 负 spread 微光 `0 0 16px -8px`(同 `.hb-card` 静息 `--glow-soft`), 底 `--bg-elev` 字 `--fg`, 圆角随 `--radius-sm`(控制台自动方角)。⚠ 发光要在 `.aq-tip` 本层用 `--accent` 现算 —— `.hb-*` 的 `--glow-soft` 只声明在 hub 控件上, body 级单例继承不到(console_hub.css 文件头硬知识③)。
- **例外**: 需要富内容(仪表/表格/交互)的悬浮走既有专用浮层(hr-pop / hb-pop / search-help-pop), 不挤 `title` 通道。

## HTML 文档一律 dark 主题 (2026-09-20 用户指定)

- **适用**: 所有产出的单文件 HTML —— 计划文档 / issue 报告 / 交付物 / 演示页。**一律深色底 + 浅色字, 禁止浅底黑字**。
- **配色口径**: `--bg` / `--paper` 亮度 ≈ `#0f…`~`#18…`, `--ink` 亮度 ≥ `#d8…`; 样式里**必须**写 `color-scheme: dark` —— 缺这条, 浏览器原生滚动条与表单控件不会跟着变深。
- **存量**: `memory-bank/plans/` 25 份与 `memory-bank/issues/` 9 份已全部深色; 新产出若不是深色即为违规。
- **例外**: `resources/`(ui-component-libraries 设计观摩稿 + settings-page-templates 候选稿)**不套用** —— 那批白底极简(kenya-hara / pentagram / muller-brockmann)是设计本体。⚠ 遇到"统一主题"类要求, 先分清**交付物 vs 参考素材**, 别一把梭。
- **命名**: 放 `memory-bank/plans/` 时命名 `YY-MM-DD-HHMM-<slug>.html`, 日期时间**用 `commands run kb.time stamp` 取当前值**, 不靠记忆。
