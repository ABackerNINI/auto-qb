# WEB UI 菜单、按钮与弹窗组件

> 摘要: `conventions/webui.md` 的菜单/入口分层、按钮体系 `.bt`、弹窗语义配色分级、三皮肤共用规则族、busy 骨架单点 —— 整段逐字外迁, 本节是该主题的现行权威。
> 触发: 菜单分层, 更多操作, 右键菜单, 按钮, .bt, 弹窗配色, modal, tone, strip, busy, 骨架, 共用规则族, .ctx-item

## WEB UI 菜单/入口分层原则 (2026-09-17 用户明确要求记入)

右键菜单(及同类动作入口)按**使用频率**分两层, 不是按功能族平铺:

- **一级 = PT 日常高频动作**: 启动 / 停止 / 强制汇报 / 详细信息 / 限速 / 移动 / 重命名 / 重新校验 / 导出 .torrent / 打开目标文件夹 / 删除。(「开始 / 暂停」是 2026-10-05 退役的浮动操作栏术语, 已随 2026-10-10 `webui-wording-unify` 全面对齐 qB 的 启动/停止, 不再使用。)
- **次级菜单(flyout) = qB 通用低频能力**: 队列(置顶·上移·下移·置底) · 自动种子管理 · 超级做种 · 强制开始 · 分享率限制 · 复制(名称/哈希/magnet) → 全部进「**更多操作**」(R10-14 由「高级能力」改名: 这些是 qB **常规**种子控制, 文案不该评价能力高低; 「更多操作」只表达层级, 后续增删子项也不会失准)。
  - ⚠ **次级菜单入口由注册表声明, 骨架单份**(口径修订 2026-11-07, 存量评审 R5#30; 原 CTX-06「一级只允许有一个次级菜单入口」已随「转移到」入口(计划 26-10-31-0306)过期): 复制族曾单列第二个子面板, 用户得先选"该进哪个" —— 已并入「更多操作」末尾(CTX-06 原判例仍成立: 低频动作归堆, 不新开入口)。现状一级次级入口 = 「更多操作」(`subName: "advanced"`, 单种子支)+「转移到」(`subName: "transfer"`, 动态目标列表, 四支各一)两个, 全部走注册表 `kind: "submenu"` 声明、共用 `ctx-menus.html` 一条 `.ctx-item.has-sub` 骨架 —— 静态骨架份数与一级入口数已脱钩, 守阵从 `AQB_CTX_MENU_REG` 渲染层计数(`test_frontend_ctx_submenu_single_entry_and_hover_close`)。要加第三个次级入口 = 有意的层级决策: 同步注册表 + `state.js` subMenu 名集合 + 回写本节口径。
  - ⚠ **同一批动作的菜单分支项集必须一致**(2026-10-09): 多选批量(`menu.multi`)与单组(`ctxMenuKind()` 兜底返回的 `group`)是**同一批动作的两条入口** —— 给一支加动作项必须同步补另一支(组菜单独有的 打开文件夹/流量图 除外), 否则用户在某条路径上「找不到该动作」(2026-10-09 用户报「单组右键菜单缺选项」)。组级入口**复用多选链路**(目标 = 该组全部成员, 走 `_groupTargets`), 不另开旁路。守阵 `test_ctx_menu_template_consumes_registry` + T4 动作族奇偶(读注册表定义序); 机理见 pitfalls/web-ui/ctx-menu-branch-parity.md。
- **菜单项是数据, 不是模板**(2026-10-20, 计划 26-10-20-0024): 四支的项集收敛到 `shared/ctx_menu.js` 的**注册表单点**(`CTX_ITEM_DEFS` / `CTX_SUB_ITEM_DEFS`), `ctx-menus.html` 只 `v-for` 消费 `ctxItems(ctxMenuKind())` / `ctxSubItems(ctxMenuKind())` 并 `ctxRun(it)` 分派 —— 模板里**不许再出现逐项 `@click="actTorrent(...)"` 这类直写**(守阵拦截回潮, 回潮 = 四支人肉奇偶复发)。加项 = 注册表加一行(含 `label`/`icon`/`act`/`gate`/`danger`; `label` 是函数时**必须**给 `labelText` 静态名, 定制面板求不出动态文案); 加支 = `CTX_BRANCHES` + `menu.js::ctxMenuKind()` + `triggers.js` variant 三处同步。
  - **渲染骨架也只有一条**(2026-10-22, issue `26-10-20-2231-refactor-fe-tpl-ctx-item-branch-dup`): 四支曾各写一份 `.ctx-item` 骨架(5 份, 其中 4 份逐字同) —— 给项加属性漏改一支就是同族缺陷。现模板里 `.ctx-item` 骨架恰 **2 份**(一级项 + 次级面板项), 支名由 `menu.js::ctxMenuKind()` 单点给出(容器 `:data-kind` 与 `v-for` 同读它), 模板**不许出现 `ctxItems('multi')` 这类支名字面量** —— 字面量要分四支, 分四支就要四份骨架(守阵 `test_ctx_menu_template_consumes_registry` 拦)。
  - 用户布局存在 `config.web.ctx_menu`(`{支: {order, hidden, sub: {order, hidden}}}`), 经 `/api/webui/flags` 下发; 解析语义(补尾 / 隐藏留槽位 / 跨层认领 / 分隔线一等公民 / 次级为空不显示入口)全在 `ctx_menu.js` 的纯函数里, **运行时与设置页定制块共用同一份**(`REG.ctxMergeLayout`) —— 不要在别处再写第二套合并逻辑。
  - 设置页「WebUI」卡(`shared/ctx_menu_custom.js` + `settings-detail.html` 的 `hub.view === 'webui'` 分支)是这条数据的编辑面: 编辑**直接写配置树**(整对象替换), 脏标记/保存/放弃走全局 actbar, 面板不另存草稿。
- **动作文案口径 = 动词 + 灰色种子数**(2026-10-20, 计划 26-10-20-0145): 四支菜单的 启动/停止/删除 一律 `label = 动词`(或「删除…」保留省略号), 后面跟行内灰色 `N 个种子`(`.ctx-note`, 规格同 `.strip-note`; 标签与后缀由 `.ctx-text` 圈成同一个 flex 项, 否则会被 `gap` 拉开)。
  - **scope 词(批量 / 该种子 / 整组 / 整剧 / 整集)一律不进文案** —— 右键位置已经说明作用范围, 作用对象终究是 N 个种子; 需要区分分支的地方(测试、触发器口径)挂 `data-kind` / `data-count`, 不挂可见文案。
  - **N = 实际受作用的种子总数**(组/剧/批量选择全部展开), 不是"目标条目数" —— 组 key 算 1 个目标但可能是 47 个种子。计数单点 `selection.js::_seedCountOf`(类型展开走 `_scopeResolve` 的 C1 描述符), 菜单后缀(`menu.js::ctxSeedCount`)、删除确认框构成式(`delete_flow.js::bulkCountText`)、动作回执 toast(`commands.js::_actCore`)三处同源。
  - 回执 toast 同形: `已执行: 启动(42 个种子)` / `启动失败: <原因>` —— 不再有「整组/该种子/整剧(N 个种子)/(N 个目标)」四种形态, `_actCore` 也不收 `what`/`countSuffix` 参数(收 = 给"同动作不同叫法"留门)。
  - 不在口径内: 需逐目标现值/状态开关的项(强制启动/超级做种/自动种子管理)、无 scope 变体的动作(强制重新汇报/重新检查/限速/移动/导出)、快捷键面板的通用词。
- **判据**: 该动作是否"每天都要点" —— 不是则下沉。菜单项数增长时**先问能否归入既有次级菜单**, 不要直接往一级追加。
- 实现: `.ctx-item.has-sub` + `.ctx-sub`(锚在父项右缘, 靠右时 `.flip-x` 向左翻); hover 与点击都能展开; 状态的唯一权威是 `app.js` 的 `subMenu`(随 `menu.visible` 关闭一并复位); 移出**父项**后延迟 ~180ms 收起(见 pitfalls/web-ui/overlays.md「flyout 次级菜单」—— 延迟只为跨过 4px 缝隙, 且收起只能挂父项)。

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
- **CSS 落点**(2026-10-21 改): 本族**整组**(框级 tone / strip 标题条 / 行级 `.is-*` / 框级兜底 / 强调行)在 `shared/console_hub.css` 的「三皮肤共用规则族单点」段 —— 三皮肤逐字节同 ⇒ 单点一份(issue 26-10-20-2231)。本皮肤只留弹窗**基础语言**(`.modal-title` / `.modal.danger .modal-title .ico`), 那部分三皮肤本就不同。⚠ **atlas `css/components.css` 已满 700 行**, 单 CSS 体量守阵(`test_frontend_template_split_wiring`)卡 ≤700, 追加前先量行数。

## WEB UI 三皮肤共用规则族 (2026-10-21, issue 26-10-20-2231)

三份皮肤 CSS(prism / atlas / console)历史上互相克隆, 同一组件写三遍且逐字节相同 —— 这类**规则族**收敛到共用层单点:

- **判据**: 同一族规则在三皮肤里**逐字节相同** ⇒ 搬进 `shared/console_hub.css` 尾段「三皮肤共用规则族单点」(A/B/C/D 四段)。三皮肤 `index.html` 都挂该文件且排在各自 CSS **之后** ⇒ 级联序天然就是收敛点, **不需要 `!important`**; 改共用层 = 三皮肤同改。
- **已收敛**: `.qb-tabs` 组件本体(容器/按钮/激活态) · `.drawer-tabs` 容器与按钮底形 · 弹窗语义配色分级 ①②③④ · HR 表① 件(表头过滤栏 · 档位徽章 · 失踪行弱化 · 排序头 · 名称列限宽)。
- **留皮肤内的是真差异, 不许顺手抹平**(守阵反向钉): `.drawer-tabs button.active` 令牌(atlas/console `--accent` vs prism `--accent-hi/--accent-line`) / `.hr-vsrc`·`.hr-pres` 描边(prism `--border-soft` vs 另两皮肤 `--border`) / `.hr-sub` 字体(prism `--font-mono` vs 字面等宽栈)。`test_frontend_hr_detail_table_wiring` 断言这三条**必须在各皮肤自己的 CSS 里**。
- **守阵量程**: 判「三皮肤成对」用 `_ui_css_effective(ui)`(= 皮肤聚合 + shell 挂的 shared CSS, link 序), **不是** `_ui_css_aggregate(ui)`(只含本皮肤) —— 后者在规则搬走后恒红。判据原理见 `pitfalls/testing/assertions.md`「守阵的量程」条。
- **新族入共用层的顺序**: 先搬逐字同的(最安全), 差异多的最后; 一族一改一回归, 不整文件对拷。
- **共用层不止 `console_hub.css`**: 按主题独立成文件的共用层同样成立 —— 现有 `shared/row_lang.css`(行语言)与 `shared/hscroll.css`(主表横滚: 原生横条隐藏 + 底部指示条)。挂载位置同样是各皮肤 `views.css` **之后**(link 序即级联序), 皮肤自有 CSS 内**不得**写第二份同类规则(副本 = 日后各自漂移, 静态守阵反向钉住)。
- 新增此类文件的门槛与判据、以及 `.group-table` 横条几何 / 两条隐藏声明 / 指示条契约与三个静默故障, 见 `pitfalls/web-ui/hscroll-indicator.md`(本文件不复述)。

## WEB UI busy 骨架单点 (2026-10-21, issue 26-10-20-2231)

「置 busy → try 请求 → 失败反馈 → finally 复位」的前端骨架收敛为 `shared/dialogs.js` 三个单点(config_hub.js 经同一根实例混入调用), **新面板/对话框代码一律走单点, 不许再手抄骨架**(漏 finally = 面板永久转圈, 见 pitfalls/web-ui/inflight-flag-no-timeout):

- **`_mgrRun(fn, okMsg, errMsg)`**: 管理对话框写操作(成功 toast → 重拉列表; 失败 toast, auth 静默)。
- **`_panelLoad(obj, fn, opts)`**: 面板加载与槽回执(loading 位可选; 失败走错误槽 `err` 或 toast 通道 `errToast`; `authGated: false` = tm 族失败恒上屏; `keepErr` = 不预清旧错; `onOk/onErr/onFinally` 承接成功收尾/失败回滚/完成置位)。
- **`_postWaitCmd(busyObj, busyKey, url, body, opts)`**: POST+waitCmd **三态 toast 判据单点**(ok / 命令回执失败 cmdFail / 发送失败 sendFail); POST 调用点唯一 ⇒ triggers.js 的 TRIGGER_DEFS.calls 只登记它一行(scope = 调用方并集 sel|anchor|none)。
- **刻意不收编**: tmShutdownTool(保存失败回滚内存态)骨架形状不同, 保持手写; 各调用点差异(槽名/文案/时长/成功收尾)以参数与回调留在调用点。
- **守阵**: `test_frontend_busy_skeleton_single_point`(三单点在册 + 19 处接线数对账 + finally 保底 + 裸 busy 置位反向断言) · `test_trigger_registry_call_sites_exact`(POST 出口登记双向相等)。
