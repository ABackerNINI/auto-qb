# WEB UI 产出口径与令牌

> 摘要: 菜单/入口分层、令牌分工、按钮体系、悬浮提示、选中摘要口径、HTML dark 主题 —— 前端产出口径的唯一出处。
> 触发: WEB UI 约定, 菜单分层, 令牌, 主题, dark, HTML 产出, tooltip, 悬浮提示, 选中摘要, occ_key, 实际占用

## WEB UI 菜单/入口分层原则 (2026-09-17 用户明确要求记入)

右键菜单(及同类动作入口)按**使用频率**分两层, 不是按功能族平铺:

- **一级 = PT 日常高频动作**: 开始 / 暂停 / 强制汇报 / 详细信息 / 限速 / 移动 / 重命名 / 重新校验 / 导出 .torrent / 打开目标文件夹 / 删除。
- **次级菜单(flyout) = qB 通用低频能力**: 队列(置顶·上移·下移·置底) · 自动种子管理 · 超级做种 · 强制开始 · 分享率限制 · 复制(名称/哈希/magnet) → 全部进「**更多操作**」(R10-14 由「高级能力」改名: 这些是 qB **常规**种子控制, 文案不该评价能力高低; 「更多操作」只表达层级, 后续增删子项也不会失准)。
  - ⚠ **一级只允许有一个次级菜单入口**(CTX-06, 2026-09-24): 复制族曾单列第二个子面板, 用户得先选"该进哪个" —— 已并入「更多操作」末尾。低频动作归堆, 不新开入口。
  - ⚠ **同一批动作的菜单分支项集必须一致**(2026-10-09): 多选批量(`menu.multi`)与单组(`v-else`)是**同一批动作的两条入口** —— 给一支加动作项必须同步补另一支(组菜单独有的 打开文件夹/流量图 除外), 否则用户在某条路径上「找不到该动作」(2026-10-09 用户报「单组右键菜单缺选项」)。组级入口**复用多选链路**(目标 = 该组全部成员, 走 `_groupTargets`), 不另开旁路。守阵 `test_ctx_menu_template_consumes_registry` + T4 动作族奇偶(读注册表定义序); 机理见 pitfalls/web-ui/ctx-menu-branch-parity.md。
- **菜单项是数据, 不是模板**(2026-10-20, 计划 26-10-20-0024): 四支的项集收敛到 `shared/ctx_menu.js` 的**注册表单点**(`CTX_ITEM_DEFS` / `CTX_SUB_ITEM_DEFS`), `ctx-menus.html` 只 `v-for` 消费 `ctxItems('<支>')` / `ctxSubItems('<支>')` 并 `ctxRun(it)` 分派 —— 模板里**不许再出现逐项 `@click="actTorrent(...)"` 这类直写**(守阵拦截回潮, 回潮 = 四支人肉奇偶复发)。加项 = 注册表加一行(含 `label`/`icon`/`act`/`gate`/`danger`; `label` 是函数时**必须**给 `labelText` 静态名, 定制面板求不出动态文案); 加支 = `CTX_BRANCHES` + 模板判据链 + `triggers.js` variant 三处同步。
  - 用户布局存在 `config.web.ctx_menu`(`{支: {order, hidden, sub: {order, hidden}}}`), 经 `/api/webui/flags` 下发; 解析语义(补尾 / 隐藏留槽位 / 跨层认领 / 分隔线一等公民 / 次级为空不显示入口)全在 `ctx_menu.js` 的纯函数里, **运行时与设置页定制块共用同一份**(`REG.ctxMergeLayout`) —— 不要在别处再写第二套合并逻辑。
  - 设置页「WebUI」卡(`shared/ctx_menu_custom.js` + `settings-detail.html` 的 `hub.view === 'webui'` 分支)是这条数据的编辑面: 编辑**直接写配置树**(整对象替换), 脏标记/保存/放弃走全局 actbar, 面板不另存草稿。
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
  i-traffic 组图标(内联 `var(--today-*)`) / **设置页限速曲线预览图**(`.ce-chart-up`/`.ce-chart-down`
  五处: 曲线线色 / 面积填充 / 悬停标记点 / 图例方向标 `.ce-lg-dir` / 档位组方向条 `.ce-dir-dot`;
  2026-10-11 归族, 此前误借状态色族 `--warn`/`--blue`)。取值 **上行 = `--indigo`(紫) / 下行 = `--teal`(蓝绿)**
  (2026-10-04 用户拍板交换)。⚠ 该族是**间接令牌**(指向 `--indigo`/`--teal`), 需要"同色软底"时**不能**借
  `--indigo-soft`/`--teal-soft`(主题换指向即脱族) —— 用 `color-mix(in srgb, var(--today-up) 16%, transparent)`
  从同一令牌现算, 或照直方图 `.hist-area.up|down` 的 `fill: var(--today-*)` + `opacity` 写法。
  ⚠ 速度组图标**不要**改全局 `.ico-up/.ico-down`(绿/蓝, 还喂顶栏「种子」等
  非流量位置), 只能按 `.sb-spd` 作用域覆盖。状态栏限速值(`.sb-spd .lim`)是**参考值**, 用中性灰 `--fg-dim`
  (与做种要求值 `.m-pair .req` 同款), 不随方向染色。
- **画布注解层限速线(plan 26-10-12-0535)**: qB 流量图的限速虚线自 2026-10-12 起按**当时值分段**——
  后端主循环采样点把 qB 全局限速生效值(上/下行分开, 0 = 不限速)按「有变化才记」落
  `<data_dir>/qb-traffic-v4/limits/<日期>.dat`(分天, 00:00 硬切 + 新天首行基线 carry, 不淘汰对齐
  day/month 全保留; 记录器在 `core/traffic_limits.py`, 挂点 `traffic_sample_mod._sample_global`),
  三端点 payload 统一附 `limits: [[ts,up,down],...]`(首元素 = 窗口起点合成事件, 记录起点前无值);
  前端 `_qbDrawLimits` 从图记录 `u._qbLimits` 走 `_qbLimitSegs` 纯函数构段(每段画各自区间, 末段到
  图右沿; 逐段可见性 0 < v < ymax; 快路 setData 同步换 limits), 悬停 tooltip 增补「当时限速」行
  (`_qbLimitAt` 二分, 记录起点前不给)。变体 13 无注解层照旧不显示; 14/15 走共享钩子自动生效。
- **表面/底色族**: 状态栏用专用 `--statusbar-bg`(与页底形成可见层级); **不要改 `--glass`** —— 它同时管顶栏,
  改它会连带改顶栏。
- **尺寸族**: 弹窗宽度取 `--modal-w-narrow/base/form/add`/`--modal-wide-w`(各套 UI 同值同族); 新增弹窗只选档,
  不写新数字(这正是此前"第 N 次调大"的成因)。
- **单点口径原则(通用)**: 同一数据/口径在两个以上地方出现时, 收成 computed/method 单点(如 `speedLimitBytes`
  限速取数、`cellSeedingTime/cellRatio/cellPeers/cellAvailability/cellTime` 单元格口径、`_deleteDetails` 删除详情行、`selSizeSummaryOf` 选中摘要大小、`colAlignCss` 列对齐),
  模板里只引用不重算。新增展示口径时先问"它是否已被别处实现"。

## WEB UI 按钮体系 .bt (2026-09-26 第十一轮)

全部动作按钮收敛一族 `.bt`, 各套 UI 同一套语义类名、外观各按其设计语言(方案定案与全状态陈列见 `plans/26-09-26-0538-plan-webui-button-3-proposals.html`):

- **语义变体**: `.bt`(次钮, 默认) / `.bt.primary`(主) / `.bt.ghost`(幽灵) / `.bt.danger`(危险·描边) / `.bt.danger-solid`(危险·实心, 用于确认框的危险确认) / `.bt.icon`(图标钮) / `.bt.sm`(小档 28px)。标准档: 星图/棱镜均 34px。
- **两套配方**: 星图 B(胶囊 999px, 主钮=品牌渐变+inset 高光, hover 泛 accent 柔光) / 棱镜 C(圆角 5px 强声明, 主钮=实心 accent+深色字, 按下 scale(.98))。
- **状态纪律**: hover 换 accent-line 描边 / 按下反馈 / `:focus-visible` ring / 禁用 .45 / 加载中 `.spin` 图标; `<button>` 一律显式 `color`(UA 默认色坑见 pitfalls/web-ui/layout-css.md)。
- **双色令牌族**(`--on-accent/--on-accent-ink/--on-error`): 实心 accent/error 底上的前景色, 星图 `:root` 一处 + 棱镜五主题各一处成对声明(亮色主题翻转为白字), 改值必须全处同改 —— 与状态色族同纪律。
- **存量家族归属**: ce-btn/ce-icon 已退役(守阵 `test_frontend_button_system_paired` 钉零残留); bulk-btn 随批量控制条退役(2026-10-05, 守阵 `test_frontend_bulk_bar_retired` 钉模板/三套 CSS/JS 助手零残留); row-btn/prio-btn 保持紧凑尺寸只并入配色与状态语言; 登录页与页签/筛选 chip 不入族(各自视觉语言), 设置页 hb-*(Ash Thorp)保留其形。

## WEB UI 弹窗语义配色分级 (2026-10-19, 计划 26-10-19-2341)

通用确认框(`shared/tpl/popovers.html` 的单例 modal)按**动作后果等级**染色, 不再只有"危险/不危险"一个布尔维度:

- **框级 `modal.tone`**: `error`(不可逆, 如删除) / `warn`(有代价可重来, 如跳检)。**派生单点在 `_openModal`** —— 显式 `cfg.tone` 优先, 缺省 `danger→error`、否则 `warn`; 两种推导都与历史着色一致, 故既有调用点零变化。**新对话框不要自己判 danger**, 显式传 tone。
- **标题区警示条 `modal.strip`**: 缺省 `false` = 外观零变化, 只有**带行式明细清单**的框才开启(落地时仅删除确认框与跳检预检框)。`-soft` 底 + `box-shadow: inset 3px 0 0 <line>` 左侧色条 —— 走 inset 而非 `border-left`, 不占布局宽度, 避开 `.modal-title` 的 flex 排列与弹窗 `overflow-y:auto` 下的溢出。
- **行级 `row.tone`**: `details` / `verdict` 行对象挂 `tone` → `.is-error` / `.is-warn` / `.is-ok`, **只染 `.ico` + `.d-label`**, value 保持 `--fg-soft` 中性(长句可读性)。**不要改全局 `.modal-detail-row .ico` 的灰** —— 它是共用同一行式范式的中性基线(限速/移动/重命名/分享率都走它); 此前正是这条规则把 `#i-warn` 与「禁止」一并抹平。
- **未标 tone 的行在 strip 框内继承框级 tone**(2026-10-20 追加): 写在选择器 `:where(.modal.strip.tone-error|warn)` 里 —— `:where()` 把特异性压到 0-2-0, 与基础置灰规则同级、靠**源序**胜出; 行级 `.is-*`(0-3-0)作为例外值因此仍能盖过它。用来消掉「整框已是危险语境、下面一整片明细行图标全灰」的割裂(删除框的 目标/成员/站点/保存路径/总大小、跳检框的 busy 行都属此列)。**无 strip 的框完全不生效**, 故其它弹窗依旧零变化 —— 这是它比"直接放宽基础规则"更适合做兜底的原因。
- **`is-error` 行额外加淡底 + 左侧 2px 色条**: 上一条的兜底铺开后, error 行与周围同色, 颜色本身已拉不开层级 —— 靠这个让 HR 风险点名 / 跳检「禁止」行仍能跳出来(与 error 文字色同源令牌)。
- **三级层次由此为: 默认继承(框 tone) < 行自报(`.is-*`) < 强调加底(`.is-error` 独有)**, 越往后越醒目; 新增 popped-out 强调力度时按这个台阶往上加, 别直接全书对/加新色值。
- **颜色一律引状态色令牌**(`--error/--warn/--green` 及其 `-soft/-line`), 三套 UI + 棱镜五主题均已声明, 不新增色值。
- **按钮不参与本族**: `.bt.danger-solid` 保持实心红 —— 按钮表达「这个动作有后果」, 标题 tone 表达「整框语境等级」, 两层语义不合并(e2e `menus.spec.mjs` 依赖该类名)。
- **CSS 落点**: 三组规则各自紧跟本皮肤的基线规则组 —— atlas / console 放 `css/views.css`(框级基线在 `components.css`), prism 放 `css/components.css`。⚠ **atlas `css/components.css` 已满 700 行**, 单 CSS 体量守阵(`test_frontend_template_split_wiring`)卡 ≤700, 追加前先量行数。

## WEB UI 悬浮提示 .aq-tip (2026-09-28)

全局 tooltip 收敛为自绘单例, **新元素一律继续写原生 `title` 属性**(模板侧零成本接入), 不许再自造浮层:

- **触发面**: 一切带 `title` 的元素(含 Vue `:title` 绑定); 调度单点在 `shared/ui_feedback.js` 尾部的纯 DOM 委托层(不进 mixin)。机制(2026-10-04 二轮定稿, **原生 tooltip 断供式**): MutationObserver 盯全文档, title 属性在任何时刻出现(模板渲染 / Vue `:title` 写回 / 新插入节点)即刻迁进 `data-aq-tip` 并删掉原属性 —— DOM 里不存在 title, 原生气泡无从弹出; 浮层触发 = document 级委托 mouseover / focusin 命中 `[data-aq-tip]`, 350ms 后弹 `.aq-tip`, 文案 show() 时现读最新值。前两轮的「hover 时摘 + 离开还原 + 悬浮期补摘」被废弃 —— Vue 轮询把指针下节点整个换掉时指针不动、mouseover 不触发, 新节点带 title 还魂叠出双 tooltip(见 pitfalls/web-ui/aq-tip-nested-title-double.md)。代价: title 不再还原(原生悬浮语义由 `.aq-tip` 承接)。点击 / 滚动 / 窗口失焦立即收起。
- **定位**(2026-10-04 修): 上方优先 → 上方放不下转下方 → 两侧都放不下才允许溢出视口; **任何分支都不越过锚点**。旧版末尾无条件把浮层夹回视口内, 状态栏这类底缘锚点一旦走「转下方」分支就会被拉回状态栏上, 正好盖住它自己描述的元素。锚点在 350ms 延时窗口内被 Vue 整个换掉时已脱离文档(rect 全 0), 按记录的指针坐标 `elementFromPoint` 重解析当前锚点, 解析不到就收起(否则浮层落到视口左上角)。
- **样式单点**: `shared/console_hub.css` 的 `.aq-tip` 段(三皮肤同载)。视觉复刻设置页发光按钮配方: 描边 `--accent-line` + 负 spread 微光 `0 0 16px -8px`(同 `.hb-card` 静息 `--glow-soft`), 底 `--bg-elev` 字 `--fg`, 圆角随 `--radius-sm`(控制台自动方角)。⚠ 发光要在 `.aq-tip` 本层用 `--accent` 现算 —— `.hb-*` 的 `--glow-soft` 只声明在 hub 控件上, body 级单例继承不到(console_hub.css 文件头硬知识③)。
- **例外**: 需要富内容(仪表/表格/交互)的悬浮走既有专用浮层(hr-pop / hb-pop / search-help-pop), 不挤 `title` 通道。

## WEB UI 选中摘要口径 (2026-10-18, 计划 26-10-18-2013)

选中种子时筛选行显示「已选 N 个种子 · 合计 X · 实际占用 Y」——**纯展示**(零按钮, 清除走 Esc; 批量动作仍归右键菜单, 不复活 2026-10-05 退役的控制条):

- **位置与样式**: `shared/tpl/topbar.html` 的 `.sel-summary`(退役控制条原槽位), `v-if="selectedCount"`; 整行复用 `.strip-note` 既有规则(三套皮肤逐字同款) —— **零新 CSS**, `.sel-summary` 仅作 e2e 选择器钩子。
- **三个量的口径**: N = `selectedCount`(`selHashSet` 去重成员数, 选 1 组 = 全组成员); X = Σ 选中成员 `size`(每个种子各算一份, 与删除框既有「总大小」行同口径); Y = 按 `occ_key` 内容单元去重、**单元取选中成员最大 size**(最完整副本, 与后端 progress=max/availability=max 同族)。Y 仅在 `Y < X` 时显示(⇔ 选中了同一单元的 ≥2 个副本)。
- **occ_key 载荷契约**(后端 `views.py::_member_view`): 归组种子带其辅种组 key(`encode_group_key`, 与组行 `key` **同键空间** —— 守阵不变量), 未归组为 `null`(字段恒在、null = 不适用, 与 `availability` 同族契约; 前端按 `m.occ_key || ("self:"+m.hash)` 兜成自单元)。种子页平铺行经 `_seed_view` 的 `{**_member_view(r), ...}` 继承; 追剧页成员经 `memberByHash` 解析, 三视图同源。语义根: 组内成员指向**同一份文件**, 磁盘只占一份(组行 `size`/`total_size` 双口径的选中版)。
- **不去重的两层**: 跨组文件交叉(`cross_group_conflict`)不再去重(后端另有风险标记); 追剧页同集多版本不额外去重(「同一份文件」判据是 save_path = 组, 不是集; 不同版本是不同字节)。
- **算法单点**: `selection.js::selSizeSummaryOf(members)` —— 筛选行(`selectedSize` computed, 无选中早退)与删除确认框(`delete_flow.js::_deleteDetails` 的条件行)共用, 不另写求和。删除框那行仅 `Y < X` 时追加, 口径说明走 `d.hint`(popovers 详情行 `:title` 吃 `d.hint || String(d.value)`; 原生 title 由 .aq-tip 层迁移成 `data-aq-tip`)。
- **守阵**: `tests/test_web_backend_misc.py::test_member_view_occ_key`(契约三条) · `tests/test_webui_static_dom_page.py::test_frontend_selection_size_summary_wiring`(模板/JS/删除行三层接线) · `e2e/multiselect-shows.spec.mjs`「选中摘要」两条(双皮肤)。

## HTML 文档一律 dark 主题 (2026-09-20 用户指定)

- **适用**: 所有产出的单文件 HTML —— 计划文档 / issue 报告 / 交付物 / 演示页。**一律深色底 + 浅色字, 禁止浅底黑字**。
- **配色口径**: `--bg` / `--paper` 亮度 ≈ `#0f…`~`#18…`, `--ink` 亮度 ≥ `#d8…`; 样式里**必须**写 `color-scheme: dark` —— 缺这条, 浏览器原生滚动条与表单控件不会跟着变深。
- **制品模板正文区**(2026-10-17): skill `templates/{plan,report}.html` 的 `.sheet` = `max-width: 1280px; padding: 48px clamp(18px, 3.2vw, 44px) 80px` —— **版面自适应**: sheet 随视口流动、侧距随宽度伸缩, 正文/列表/表格/代码块同宽 (prose 不设 ch 上限, 右缘对齐); 窄视口 (≤1180px) 表格内代码允许断行防页面横向溢出。规格单点在模板自身(带注释), 存量 51 份自带内联 CSS 按冻结线豁免。
- **存量**: `memory-bank/plans/` 25 份与 `memory-bank/issues/` 9 份已全部深色; 新产出若不是深色即为违规。
- **例外**: `resources/`(ui-component-libraries 设计观摩稿 + settings-page-templates 候选稿)**不套用** —— 那批白底极简(kenya-hara / pentagram / muller-brockmann)是设计本体。⚠ 遇到"统一主题"类要求, 先分清**交付物 vs 参考素材**, 别一把梭。
- **命名**: 放 `memory-bank/plans/` 时命名 `YY-MM-DD-HHMM-<slug>.html`, 日期时间**用 `commands run kb.time stamp` 取当前值**, 不靠记忆。
