/* state.js — 根组件状态单点(data/computed/watch): 26-09-27 W2b 自 app.js 拆出。
 * WARN: 不是 app.mixin!经 app.js 的 `...window.AQB_STATE` 展开进**根组件选项** ——
 * 全局 mixin 会波及 hub-field 等组件实例(watch/mounted 双份执行), 根选项只命中根。
 * 成员逐行原样搬运, 语义与拆分前一致; 接线形态4.由 _scan_mixin_wiring 钉住。 */
/* 皮肤判定单点: URL 首段路径 == 皮肤目录名(static/<名>/index.html, 目录即 UI, 后端零注册表)。
 * 未识别段回落 atlas(如直接以 / 访问时的边缘路径)。加第四套 UI 在这里扩一档。 */
function _aqbDetectUi() {
  const seg = location.pathname.split("/")[1];
  return seg === "prism" ? "prism" : seg === "console" ? "console" : "atlas";
}

/* 界面切换下拉的选项表(单一语义模板参数化差异的数据面): 三套 UI 全列, 键序即菜单序。
 * 加第四套 UI = 这里加一档 + _aqbDetectUi 加一档判定, 模板零改动(旧「环形互切」已废, 2026-09-27)。 */
const UI_HOME = {
  atlas: { icon: "#i-orbit", label: "星图", desc: "经典深色仪表盘" },
  prism: { icon: "#i-prism", label: "棱镜", desc: "工程仪器 · 五主题" },
  console: { icon: "#i-gauge", label: "控制台", desc: "Console Hub 仪表台" },
};

window.AQB_STATE = {
  data() {
    return {
      token: "",  // 已验证通过的密钥(唯一可信身份); 仅 bootstrap 验证成功后提交
      l10nGroup: L10N_GROUP,  // FX-10: 模板里的业务名词(单点, 见文件顶部常量)
      pendingToken: "",  // 验证中的候选密钥(不参与渲染门控/请求头); 服务不可达时供"重试连接"复用
      tokenInput: "",
      authRequired: true,  // 遮罩唯一开关: 仅在密钥验证成功后置 false —— 与 token 赋值解耦, 防错误密钥瞬间主界面闪现
      authPending: false,  // 密钥验证中: 禁用提交、按钮显示"验证中…", 防重复提交
      authError: "",
      authErrorKind: "",   // "auth" = 密钥被拒(401); "unavailable" = 服务不可达(保留候选密钥供重试)
      // R10-01: 鉴权模式显式化 —— 旧实现把"有身份"与"有密钥串"绑死, 本机免鉴权时 token 为空串,
      // 于是进主界面后首个请求就被自己的守卫判成无凭证 -> 登出回密钥页("必须先输一次才进得去")。
      // 现在守卫一律看 authMode: "local" = 本机免鉴权(直接放行, 且不发空 Bearer), "token" = 密钥流程。
      authMode: "token",
      page: initialPage(),  // 顶层页面: "groups" | "settings"(持久化, 见 initialPage)
      // 单一语义模板的皮肤开关(26-09-27 收敛, plans/26-09-26-2233 W3): 各套 UI 共用 shared/tpl 一份分片,
      // 模板级差异只允许 `v-if="ui === '...'"` 条件块(带 ui-diff 注释, 守阵收集为活差异清单)。
      // 皮肤判定: URL 首段路径(目录即 UI); 2026-09-27 起第三套 console(控制台)并列, 未识别段回落 atlas。
      ui: _aqbDetectUi(),
      uiMenuOpen: false,  // 顶栏界面切换下拉的展开态(点空白/Esc 收起, 挂在 lifecycle.js 既有浮层关闭链)
      groups: [],
      singles: [],            // 未归组种子(后端与 groups 同快照同门控回传, 供搜索兜底/总数回退)
      torrents: [],           // 种子页数据源: 全量种子平铺数组(SEED_ITEM, 与 groups 同门控回传)
      shows: { list: [], unrecognized: [] },  // 追剧视图(剧→季→集聚合, 与 groups 同门控回传)
      // 辅种页视图: groups(分组表) | torrents(单种子平铺) | shows(追剧); 列模型/列宽/排序独立, 筛选与搜索共用
      viewMode: initialViewMode(),
      status: {},
      // WARN: 轮询间隔不在这里 —— 见 computed.basePollMs(): 前端是服务端状态的**封顶**
      // (后端数据再快也要等下一轮轮询才可见), P1 落地后改成按种子量分档。
      // P0-0 埋点(排查用, 不参与渲染): 单次命令端到端耗时与单轮视图赋值耗时
      cmdStats: null,  // { cmdId, totalMs, waitMs, execMs } —— waitMs 排队等主循环, execMs 执行
      renderMs: 0,  // 单轮 refresh() 中"赋值 + 多选交集"的耗时(不含网络)
      /* FX-28: 各**时间点列**的显示口径 { 列key: "rel" | "abs" } —— 由该列表头右键菜单切换并持久化
       * (见 TIME_FMT_STORE_KEY); 键集合 = TIME_FMT_KEYS, 未登记的列不受影响 */
      timeFmt: loadTimeFmt(),
      /* 相对时间时钟(FX-27): 只喂"最近活动"这类相对时间显示(fmtRelTime), 30s 一跳 ——
       * 为什么必须有: 后端 last_activity 按分钟量化且只在**活动发生时**才变, 暂停的种子行对象
       * 长期不变 ⇒ Vue 不重渲染 ⇒ 相对值会永久停在渲染那一刻("刚刚"挂一整天)。粒度只到分钟,
       * 不必比 30s 更密(更密只会白付整表 patch, 与 P1-2 的窗口化成果相抵)。 */
      nowSec: Math.floor(Date.now() / 1000),
      pendingOps: {},  // P0-3 乐观 UI: hash -> { patch, prev, ts }, 见 isPending/applyOptimistic
      /* 本轮 /api/state 的**真值快照**: hash -> { 补丁键: 服务端原始值 }。
       * 判"真值是否已对齐"必须比这个, 不能比行上的当前值 —— 见 _snapshotTruth。 */
      truthSnapshot: null,
      /* P0-3 组行乐观: 组 key -> { primary, ts }。与 pendingOps 同一套语义, 但**只存"结果"**
       * 不存 prev —— 组对象是 decoratedGroups 的**拷贝**(非响应式), 直接改 g.status 不会触发
       * 重渲染, 所以补丁走这个响应式覆盖表, 由 groupPrimary(g) 现问现用; 回滚 = 删掉覆盖,
       * 真值本来就没被改过(比成员行的 prev 回滚更不容易留假状态)。 */
      pendingGroupOps: {},
      // P1-2 行窗口化(常量与原理见文件顶部 ROW_WIN_* 注释)
      rowWin: true,          // 总开关(诊断用): 关掉即全量渲染。窗口的"退避"不走这里 ——
                             // 展开分组/行数不足阈值时由 _rowWindow 直接返回 inactive(见其注释)
      _winScrollY: 0,        // 最近一次窗口滚动位置(rAF 合帧写入; 响应式 -> 触发窗口重算)
      _winViewH: 0,          // 视口高度
      _winResize: 0,         // resize 计数(签名里带上它, 让窗口/列宽变化后重算)
      // 实测行高**均值**(未量过的行的兜底值; 逐行真值在 _rowHs); 响应式 —— 变了要重排窗口
      _rowH: { torrent: 0, group: 0, member: 0 },
      _rowHVer: 0,       // 行高表版本: 每量到新高度就 +1, 触发窗口重算(逐行真值是非响应式的)
      expandedKey: null,
      // 展开态的**跨视图记忆**(切走收进桶 / 切回还回去, 见 stashExpandState·restoreExpandState):
      // 只有分组(单键)与追剧(剧键列表 + 集键)两个视图有展开态; 种子视图没有展开概念, 不占桶。
      // 纯内存 —— 刷新后不还原(展开是临时意图, 与 page/view 这类"停在哪"的意图不同, 不落盘)。
      expandMemo: { groups: null, shows: null },
      // 排序: 默认 = 组内最近添加时间降序(见 DEFAULT_SORT); 点击列头按 降序->升序->恢复默认 三态循环
      sortKey: DEFAULT_SORT.key,
      sortDir: DEFAULT_SORT.dir,
      // 展开明细表排序(与三视图正交, 三个视图的明细共用): 空键 = 后端原序
      detailSortKey: "",
      detailSortDir: -1,
      // 单种子视图独立排序键(与分组表互不干扰, 同三态语义)
      torrentSortKey: DEFAULT_SORT.key,
      torrentSortDir: DEFAULT_SORT.dir,
      // 追剧视图: 默认按最近动静降序(后端同序); 剧展开列表与集明细展开键(Vue 内存态)
      showSortKey: "latest",
      showSortDir: -1,
      expandedShows: [],
      expandedShowEp: null,
      unrecognizedOpen: false,  // 未识别折叠区展开态(追剧视图)
      groupColumns: GROUP_COLUMNS,
      detailColumns: DETAIL_COLUMNS,
      // 底部详情抽屉(R1B): 各 tab 数据与加载态; _drawerTimer 轮询句柄挂实例(非响应式)
      // kind(2026-10-04 双形态): "seed" = 种子详情(五页签) / "traffic" = qB 口径流量图(全局/分组,
      //   scope 记挂点); 两形态共用同一抽屉壳与同一拖拽高度(drawerHeightPx) —— 原模态弹层已并入。
      drawer: {
        open: false, hash: "", tab: "general", loading: false, error: "",
        detail: null, trackers: [], files: [], peers: { peers: [] },
        trackersLoading: false, filesLoading: false, peersLoading: false,
        // FX-29 切换目标期的遮罩态: 保留旧内容撑住面板几何, 遮罩盖住旧值防误读, 新数据到手才撤
        switching: false,
        kind: "seed", scope: "",  // scope ∈ "" | "global" | "group"(kind === "traffic" 时有效)
      },
      drawerLastTab: initialDrawerTab(),  // 记住上次停留的 tab(跨种子打开 + 刷新保持); 见 initialDrawerTab()
      // 面板高度记忆(W3 方案A): 用户拖拽调高后的 px; null = 未拖拽过, 走 CSS 默认上限 42vh。
      // D1 拍板: 首屏默认关闭(drawer.open 初值 false 不回读 drawerOpen 键), 高度记忆仍生效
      drawerHeightPx: initialDrawerHeight(),
      // 详情面板模板选择(plan 26-10-06-0838 S1, P-01 初装全 classic): 按页签记模板 id;
      // 读侧白名单在核心层 readSel, 脏值/缺失/写失败一律回落 classic —— 字段必须显式建(vue-reactivity 坑)
      drawerTplSel: initialDrawerTpl(),
      // 页签合并开关(R2 计划 26-10-09-2219 S2 · R3 名单模型): "off" | "on"。开启且宽度门内时
      // 页签栏收敛为两对合并页签[常规&内容][Tracker&用户], 正文双列并排(列组按当前页签所属对)。
      // 抽屉级布局意图, 不随页签/种子/开关面板丢失; 独立于 drawerTplSel(模板选择 × 合并两个
      // 自由度解耦)。读侧白名单同族: 脏值一律回落 "off"; R2 旧值 gc/tp 迁移为 "on"。
      // 生效还受宽度门约束(dtSplitOn/dtMergeTabsOn 单点判据)。
      drawerMerge: initialDrawerMerge(),
      // 视口宽回写(核心层 resize 防抖 150ms): 门是暂态遮蔽 —— 缩窗过门双列回落单栏(标志不动),
      // 拉宽自动恢复。显式建字段供 dtSplitOn computed 响应式消费。
      dtWinW: typeof window !== "undefined" ? window.innerWidth : 0,
      // 抽屉右键菜单(R2 S3): 合并开关入口(正文/页签栏 @contextmenu), 种子详情形态才弹
      drawerMenu: { visible: false, x: 0, y: 0 },
      torrentColumns: TORRENT_COLUMNS,  // 单种子视图列模型(列选择器第三段)
      showColumns: SHOW_COLUMNS,        // 追剧视图列模型(列选择器第四段)
      // 列状态双轨(plan 26-09-21-1551): 意图态(唯一持久化对象)与生效态(易变, 绝不落盘)分开
      colHidden: initialColState.hidden,  // 意图: {page: [列key]}
      colOrder: initialColState.order,    // 意图: {page: [列key]} (TBL-05 表头拖动重排; 空 = 定义顺序)
      colW: initialColState.w,            // 意图: {page: null | {列key: "Npx"}} —— null/缺失 = 全自动页
      colWidths: initialEffectiveWidths,  // 生效: 固化页 = 意图, 全自动页 = recomputeEffective 现算
      colMenuOpen: false,                 // 列选择器弹层开关
      colMenuAt: null,                    // 列选择器 fixed 锚点(表头右键路径 {x,y,mh}; null = 按钮路径走 CSS 定位)
      colDrag: null,                      // 表头拖动重排进行中(TBL-05): {page, key, idx, x} — idx=可视列插入边界, x=指示线位置
      // FX-25: 拖动虚影(跟随光标的列名胶囊)。刻意不用 HTML5 draggable 的原生拖影 —— 它会与
      // "点击排序"与"列宽拖拽"互相干扰; 自绘虚影与现有 mousedown 阈值手势完全解耦。
      colGhost: null,                     // {label, x, y} | null
      menu: { visible: false, x: 0, y: 0, key: null, hash: null, multi: false },
      // R2 跳检菜单开关(计划 26-10-02-1955 W1, 默认 false = fail-closed): 字段必须显式建
      // (v-if 对 undefined 恰好也隐藏, 但 undefined 是非响应式盲区, 呼应 vue-reactivity 静默坑);
      // 登录后 loadWebFlags 从 /api/webui/flags 取真值, 设置页保存配置后同步刷新(免重登)。
      // qb_traffic_enabled(P5a, plan 26-10-03-0946 §07): qB 口径流量图入口旗标, 同一 fail-closed 口径
      flags: { skip_check_menu: false, qb_traffic_enabled: false },
      // FX-15: 右键菜单的次级菜单(flyout)展开态与翻转态 —— 一级只有一个「更多操作」子面板,
      // 队列/TMM/超级做种/强制开始/分享率限制/复制族 都在它里面(见 conventions/webui.md)
      subMenu: "",        // "" | "advanced"
      subFlip: false,     // 子面板向左翻(父项靠右, 右展会伸出视口)
      // CTX-05: 移出后延迟收起的定时器句柄(0 = 无挂起); 延迟只用于跨过父项与子面板之间的缝隙
      _subCloseTimer: 0,
      // 表头右键菜单(TBL-05): 针对**该列**的操作 —— 隐藏「列名」(隐藏单列)/升序/降序/打开列选择器
      headMenu: { visible: false, x: 0, y: 0, page: "", key: "", label: "", sortable: false, locked: false },
      // 内容页签文件优先级小菜单(复用 .ctx-menu 视觉): 锚定单元格, 视口吸附; index = 文件在种子内的原始下标
      filePrio: { visible: false, x: 0, y: 0, index: -1 },
      drawerSelPath: "",    // 内容页签选中行(文件/目录完整相对路径); 顶部"重命名…"的作用对象
      serviceDown: false,  // 服务不可达(程序退出): 显示全局横幅, 轮询继续以便恢复后自动接上
      pollFails: 0,        // 连续失败次数(轮询退避: 2s→4s→8s→15s 上限)
      pollTimer: null,     // setTimeout 链式轮询句柄(上一轮结束后再计时, 不堆叠请求)
      lastRid: null,       // 已持有的分组视图版本(服务端 rid); null = 尚未取到(强制全量)
      searchQuery: "",       // 搜索关键字
      searchHits: new Set(),  // 命中种子 hash 集合(服务端匹配裁决: 名字/站点/分类/路径/标签/文件)
      searchUncovered: [],    // 未归组的命中种子(分组未启用/文件列表不可读), 以虚拟行兜底展示
      searchBuilding: false,  // 文件索引构建中(增量限流可能多轮, 需稍后重查)
      searchNegativeOnly: false,  // 查询只含排除词(无正判据, 服务端返回空, 前端据此提示)
      searchError: "",        // 搜索请求失败提示(不再静默)
      searchPending: false,   // 搜索待响应(防抖武装起/请求在途, 落袋或复位即翻回): 待响应期空命中集不得接管列表
      searchTimer: null,      // 防抖 + 索引构建自动重查定时器
      searchHelpOpen: false,  // 搜索语法浮卡开合(计划 26-09-28-0201 方案A; 临时浮层, 点空白/Esc/导航收起)
      kindFilter: "",         // 状态筛选(seeding/downloading/... ; 空 = 不筛选)
      // 多选筛选(组内任一成员命中任一选中值即保留该组; 同一筛选器内多选为"或")
      // pathFilter 与其它筛选器同形(数组多选) —— 四个筛选器共用一份 filterDefs 与渲染模板
      pathFilter: [],
      tagFilter: [],
      categoryFilter: [],
      siteFilter: [],
      hrFilter: [],          // H&R 筛选(不能删/考核未通过/可删/疑似辅种; 与其它多选筛选器同形, 口径见 _hrBuckets)
      hrSrcFilter: [],       // HR 来源筛选(在线核实/本地兜底/策略; 口径见 hr.js hrSrcOptions)
      filterMenu: "",         // 当前展开的筛选弹层: "" | "tag" | "category" | "site" | "hr" | "hr-src" | "path"
      popFlip: false,         // 筛选弹层视口翻转(锚点靠右时改为右对齐, 避免伸出屏幕)
      colFlip: false,         // 列选择器弹层视口翻转(同上)
      toasts: [],             // 站内提示条(替代 alert)
      modal: {                // 站内确认/输入框(替代 confirm/prompt); 结构见 _modalInit
        visible: false, title: "", body: "", okText: "", cancelText: "",
        danger: false, input: false, value: "", placeholder: "",
      },
      _toastSeq: 0,           // 提示条自增 id
      // 通知(会话内环形缓冲, WEBUI 通知 S1 数据层; 收集钩子在 ui_feedback.js):
      // error/timeout 类 toast **发出即收**(不是退场时收 —— auth.js 登录/重连的 this.toasts = []
      // 整表清空绕过 _dropToast, 退场钩子会漏)。纯内存不持久化(零 localStorage / 不进 state_file);
      // auth 清 toasts 不清历史 —— 历史跨重连存活(既定设计)。面板 UI 与后端条目合并是后续步骤。
      _errHistory: [],        // 新在上; 条目 { id, seq, ts, kind, text, source }, source: 'toast' | 'backend'
      _errSeq: 0,             // toast 条目自增序号(展示排序兜底; 后端条目用后端环的 seq)
      _errUnread: 0,          // 面板关闭期新增的错误数(徽标); 打开面板时清零(见下方 watch.errPanelOpen)
      errPanelOpen: false,    // 通知面板开合(本步只立数据字段, 面板 UI 后续步骤接)
      _modalResolve: null,    // 模态 Promise 的 resolve(单例, 关闭时结算)
      _colAlignCss: "",       // 已注入的列对齐 CSS(值未变不重写 <style>)
      _headH: 0,              // 顶栏+状态条实测高度(写 :root --head-h, 供左栏吸顶定位; 含批量段, FIX-06)
      // P1-3 顶栏尺寸观察器: 元素引用 / 观察器 / rAF 句柄(字段名避开同名方法 _headEl)
      _headObsEl: null,
      _headObs: null,
      _headRaf: 0,
      // 多选(分组表/明细表): Ctrl/⌘+点击切换, Shift+点击锚点范围; 普通点击行为不变(组=展开)
      // 双向联动(2026-10-09, 取代 FX-11 互斥): 组选中 <=> 该组成员全选 —— 两者可同时非空,
      // 写入口单点在 selection.js 的 _selAddGroup/_selDropGroup/_selSyncGroups。
      selGroups: [],          // 选中组 key(其成员必在 selMembers 内)
      selMembers: [],         // 选中成员 hash(含"组选中"带来的那部分)
      // 键盘光标行(计划 26-09-28-0354 W2; 26-09-30 方案 B 起鼠标点击同样落光标 —— 键鼠衔接):
      // {kind, id} —— kind ∈ group|torrent|show|ep, 按身份不按下标(轮询整表替换/排序后由
      // _kbMove 按身份重定位); 视觉为虚线描边, 与选中底色是两套语义, 不合并(0822 §04)
      kbCursor: null,
      // 键盘快捷键 W6(计划 26-09-28-0354): 帮助浮层 + 设置页自定义面板/录制器(方法在 shortcuts.js)
      kbHelpOpen: false,      // ? 帮助浮层(只读速查, Shift+Slash 打开; Esc/导航关闭 —— 归退栈链)
      kbDraft: null,          // 面板工作副本 {schema_version, template, overrides}(null = 未初始化)
      kbSaved: null,          // 最近一次保存的服务端真值副本(面板脏检测基准)
      kbRecId: "",            // 正在录制的 action id("" = 不在录制态)
      kbConflict: null,       // 录制冲突待决 {id, serial, other, otherLabel}(三选一: 交换/覆盖/取消)
      kbKeysLoading: false,   // 面板打开/重载时拉取服务端真值中
      // 区间起点(anchor)三字段(计划 26-10-02-0608 方案 B 起与光标同属键鼠统一模型):
      // 由鼠标普通/Ctrl(⌘)点击或键盘 Shift 手势原点落定(落起点 ≠ 选中, 只写这里);
      // **Shift 扩展期间不更新**(便于同一起点多次扩段)。解析/写入单点在 selection.js
      // (_selAnchor 兜底链: 显式锚点 -> 当前光标 -> [group: 展开的组] -> 列表首行 / _selSetAnchor)
      selAnchorGroup: null,   // 分组表 Shift 锚点(组 key)
      selAnchorMember: null,  // 明细表/平铺种子表 Shift 锚点(成员 hash)
      selAnchorUnit: null,    // FX-12: 追剧页 Shift 锚点(剧/集单元 id)
      // 历史流量弹层(今日流量面板入口; 数据源 /api/traffic/history, 按日原始行)
      historyOpen: false,
      historyGran: "day",     // day | month | year
      historyData: [],
      historyLoading: false,
      historyError: "",
      histHoverIdx: -1,       // 悬停柱桶索引(-1 = 无)
      // qB 口径流量图 · 全局挂点(P5a, plan 26-10-03-0946 §07; 数据源 /api/traffic/qb/global,
      // 时序速率, 响应三域同形 { points, totals, meta }; 组件在 qb_traffic_chart.js)。
      // 2026-10-04: 三挂点并入底部详情抽屉(开合 = drawer.open + drawer.kind === "traffic"
      // + drawer.scope), 不再各持独立 open 字段。
      qbHistWindow: qbInitialWindow("global"),  // 十三档; 持久化 autoqb.ui.qbWinGlobal(全局单独一份)
      qbHistData: null,       // 最近一次成功响应(null = 无数据/失败, 空态分支接管)
      qbHistLoading: false,
      qbHistError: "",
      qbHistHoverIdx: -1,     // 悬停桶索引(-1 = 无; uPlot setCursor 钩子写回)
      qbHistHoverLeft: 0,     // 悬停十字线 px(tooltip 水平定位)
      // 纵轴固定模式(2026-10-08): {mode: auto|limit|manual, manual: MiB/s}; 三作用域各自独立
      // 落盘(autoqb.ui.qbYAxisGlobal), 初值函数 qbInitialYAxis 在 qb_traffic_chart.js
      qbHistYAxis: qbInitialYAxis("global"),
      // qB 口径流量图 · 单种挂点(S5b, plan §07 表②): 种子详情抽屉「流量」页签; 开合由
      // drawer.kind === "seed" + drawer.tab === "traffic" 表达, 不设独立 open 字段(正文块在 drawer.html)
      qbTorrentWindow: qbInitialWindow("torrent"), // 十三档; 持久化 autoqb.ui.qbWinShared(与组共用)
      qbTorrentData: null,    // 最近一次成功响应(null = 无数据/失败, 空态分支接管)
      qbTorrentLoading: false,
      qbTorrentError: "",
      qbTorrentHoverIdx: -1,  // 悬停桶索引(-1 = 无; uPlot setCursor 钩子写回)
      qbTorrentHoverLeft: 0,  // 悬停十字线 px(tooltip 水平定位)
      qbTorrentYAxis: qbInitialYAxis("torrent"),  // 纵轴固定模式(三作用域各自独立: autoqb.ui.qbYAxisTorrent)
      // qB 口径流量图 · 分组挂点(S5b, §07 表③): 分组形态(与全局同挂抽屉, scope="group"),
      // 入口 = 组右键菜单「qB 口径流量图」; key = 分组视图 g.key(encode_group_key 通道)
      qbGroupKey: "",         // 打开时刻锁定的组 key(慢响应不污染下一次打开)
      qbGroupName: "",        // 弹层标题用(经 _findGroup 取, 找不到留空)
      qbGroupWindow: qbInitialWindow("group"),  // 十三档; 持久化 autoqb.ui.qbWinShared(与种子共用)
      qbGroupData: null,      // 最近一次成功响应(null = 无数据/失败, 空态分支接管)
      qbGroupLoading: false,
      qbGroupError: "",
      qbGroupHoverIdx: -1,    // 悬停桶索引(-1 = 无; uPlot setCursor 钩子写回)
      qbGroupHoverLeft: 0,    // 悬停十字线 px(tooltip 水平定位)
      qbGroupYAxis: qbInitialYAxis("group"),  // 纵轴固定模式(三作用域各自独立: autoqb.ui.qbYAxisGroup)
      // 登录"验证中"加载态(本地密钥 bootstrap 期间 true): 修复刷新时闪现输入密钥界面。
      // FX-01: 初值必须为 true —— 首帧状态**未知**, 不能当作"未授权"渲染密钥表单。
      // 离开该状态只有三条明确路径(见 mounted/bootstrap): 本机免鉴权 / 密钥验证通过 / 无密钥或验证被拒。
      bootstrapping: true,
      // 添加种子对话框(R1B): 来源 = .torrent 多选 + magnet/URL 文本域混合; 提交走 JSON(base64 文件)
      addOpen: false,
      addDragOver: false,     // 全局拖拽遮罩(拖 .torrent 文件/链接进页面任意位置时点亮, drop/拖离即灭)
      addSubmitting: false,   // 提交中(按钮 loading, 阻止重复提交与误关闭)
      addFiles: [],           // 已选 .torrent File 对象(展示用元信息; 前端读为 base64 随 JSON 上送)
      addUrls: "",            // magnet / http(s) 链接, 每行一条
      addShowUrls: false,     // DLG-03: 链接输入框展开态(默认隐藏, 「添加链接」按钮切换)
      addSavePath: "",        // 保存路径(空 = qB 默认)
      addCategory: "",        // 分类(可空; combobox = 下拉候选 + 自由输入)
      addTags: "",            // 标签(逗号分隔, 可空; combobox)
      addStart: false,        // DLG-03: 添加后开始(勾选 = 立即开始; 默认不勾 = paused 添加)
      addSkipCheck: false,    // 跳过校验(危险选项: 勾选后选项区下出警告行)
      addSequential: false,   // 顺序下载
      addFirstLast: false,    // 首末块优先
      addTmm: false,          // 自动种子管理(TMM)
      addCatOptions: [],      // DLG-03: 分类候选(GET /api/categories, 打开窗口时拉取)
      addTagOptions: [],      // DLG-03: 标签候选(GET /api/tags?exclude_auto=1 剔程序标签, 打开窗口时拉取)
      addCatMenu: false,      // 分类下拉展开态
      addTagMenu: false,      // 标签下拉展开态
      addCatHi: -1,           // 分类下拉键盘高亮
      addTagHi: -1,           // 标签下拉键盘高亮
      addCatMouseAt: null,    // 悬停接管门限坐标(comboHoverIdx, 治上下键选中项闪烁 26-09-29-2142)
      addTagMouseAt: null,    // 同上(标签下拉)
      addPathOptions: [],     // DLG-04: 保存路径候选(GET /api/paths, 已排序去重)
      addPathPop: false,      // DLG-04: 选择位置面板展开态
      addPathHi: -1,          // 位置面板键盘高亮
      // R10-11 路径选择器(决策 D2-A): 服务端目录浏览 —— 浏览器拿不到本地绝对路径
      // (目录上传控件只暴露相对路径), 所以"像选 .torrent 那样"只能由服务端给路径。
      // 只列目录 + 上遒 + 新建文件夹; 安全边界(允许根白名单/.. 穿越/符号链接逃逸)在后端。
      dirBrowse: {
        open: false, path: "", parent: "", roots: [], dirs: [],
        loading: false, error: "", newName: "", busy: false,
      },
      // 统计面板(FE-2C): /api/stats → {server: qB server_state | null}; 打开时取一次, 卡内可手动刷新
      statsOpen: false,
      statsLoading: false,
      statsError: "",
      statsServer: null,
      // 日志页(FE-2C): /api/log 只读 tail; 无自动轮询(等级/行数变更与刷新按钮均手动触发)
      logs: {
        loading: false, error: "", loaded: false,
        lines: [], file: "",
        open: false,          // 「常规」页尾运行日志块默认折叠(2026-09-28), 首次展开才拉数据
        note: "",             // 后端"筛不了"的说明(格式无等级字段 / 已存行与格式不符)
        level: "",            // ""=全部 | INFO | WARNING | ERROR(后端按配置格式串定位等级字段)
        num: 300,             // tail 行数(后端钳制 10..2000)
      },
      // 「站点状态」块折叠态(计划 26-10-02-1936 阶段2): 默认折叠, 「展开」即打开覆盖式全屏弹窗
      // (两态之间无内嵌展开); 不持久化、每次进分区回折叠(同上 logs.open 先例); 取数时机在
      // hr_status.js hrsToggle(首次展开才拉, 决策点⑤a)。数据本体 hrs 在 hr_status.js mixin data
      hrsOpen: false,
      // 限速托管状态(FE-2C D2): /api/speed/mode 展示 + /api/speed/override 临时覆盖
      // ALT-01: altOn/altCurrent 随同一端点回传(备用速度模式 + 备用限速值 KiB/s)
      speedMode: { loaded: false, curveEnabled: false, target: null, current: null, altOn: false, altCurrent: null, error: "" },
      speedOverride: { up: "", down: "", busy: false },  // 两方向都必填数字(后端语义: 两方向都设置, 0=不限)
      // ALT-01(计划 26-09-28-0037): 备用速度 —— 弹窗第二组输入(与主速 speedOverride 平行, 0=不限);
      // altToggling = 状态栏乌龟按钮切换进行中(防重复点击 + 图标旋转)
      speedAlt: { up: "", down: "", busy: false },
      altToggling: false,
      speedOpen: false,  // SPD-04: 限速修改浮层(qB 式「点击限速 → 弹窗」, 表单从信息栏收进窗内)
      // FX-08: 浮层锚点 —— left 由点击坐标算出(状态栏"限制速度"按钮左缘 - 12), dir 为预聚焦方向
      speedAt: { left: 0, dir: "up" },
      // 分类/标签管理对话框(FE-2C2): GET /api/categories|tags 拉列表 + 新建行; 行级改路径/删除走既有确认/输入原语
      mgrOpen: "",           // "" | "category" | "tag"(同一时刻只开一个)
      mgrLoading: false,
      mgrError: "",
      mgrCategories: [],     // [{name, save_path}](GET /api/categories 的 map 展平)
      mgrTags: [],           // [名字...](GET /api/tags 原样)
      mgrNewCatName: "",     // 新建分类行: 名称
      mgrNewCatPath: "",     // 新建分类行: 保存路径(可空)
      mgrNewTags: "",        // 新建标签行: 逗号分隔可批量
      mgrBusy: false,        // 写操作回执等待中(防重复提交 + 关闭窗口误触)
      // 标签/分类编辑对话框: 对选中集合(或单种子)**即时**增删标签/改分类
      // 写操作走 /api/torrents/bulk(add_tags/remove_tags/set_category), 每次点击独立命令独立回执;
      // 目标集合在打开时刻锁定(对话框有遮罩, 期间选择不会变化), 打开时另拉一次分类/标签候选。
      metaOpen: false,
      metaTargets: { groupKeys: [], memberHashes: [] },  // 打开时刻锁定的目标(groupKeys 为 URL 编码态)
      metaCount: 0,          // 打开时刻的目标种子数(展示用)
      metaCategories: [],    // 分类候选(GET /api/categories, 打开时拉)
      metaTags: [],          // 标签候选(GET /api/tags?exclude_auto=1 剔程序标签 + 共同携带的并回 + 输入的新标签并入)
      metaCommonTags: [],    // 打开时刻选中集合的**共同标签**(胶囊勾选态基准; 不过滤站点同名标签)
      metaCat: "",           // 打开时刻的共同分类("" = 无分类)
      metaCatDiff: false,    // 选中集合分类不一致(混合态: 输入框置空 + 提示覆盖语义)
      metaCatInput: "",      // 分类输入框(自由输入 + 下拉候选; 回车/候选点击应用)
      metaCatMenu: false,    // 分类下拉展开态
      metaCatHi: -1,         // 分类下拉键盘高亮
      metaCatMouseAt: null,  // 悬停接管门限坐标(comboHoverIdx, 同 addCatMouseAt)
      metaNewTags: "",       // 新标签输入(逗号分隔可批量)
      metaBusy: false,       // 有命令在飞(防误关 + 防重复投递)
    };
  },
  computed: {
    /* 界面切换下拉(单一语义模板的参数化差异): 按钮档 uiCurrent + 菜单全档 uiOptions,
     * 数据面 = UI_HOME 单点 —— 三套 UI 直选, 不再环切。 */
    uiCurrent() {
      return { id: this.ui, href: `/${this.ui}/`, ...(UI_HOME[this.ui] || UI_HOME.atlas) };
    },
    uiOptions() {
      return Object.entries(UI_HOME).map(([id, o]) => ({ id, href: `/${id}/`, ...o }));
    },
    pollLabel() {
      // 顶栏展示当前轮询间隔(自适应: 按种子量分档 + 服务不可达时退避)
      return Math.round(this.currentPollMs() / 1000);
    },
    statusBadge() {
      if (this.status.paused) return { text: "已暂停", kind: "warn" };
      if (this.status.connected === false) return { text: "qB 断开", kind: "error" };
      if (this.status.connected === true) return { text: "运行中", kind: "ok" };
      return { text: "连接中…", kind: "warn" };
    },
    /* R10-01 鉴权判据单点: 所有"能不能发请求"的守卫(api/轮询续排/标签页可见性)都用它,
     * 避免"改两处漏一处"导致轮询静默停摆。本机免鉴权下 token 为空是合法状态。 */
    authOk() {
      return this.authMode === "local" || !!this.token;
    },
    /* 通知模板别名(S4): `_` 前缀 data 字段不对模板代理暴露(Vue 保留域,
     * issue 26-10-03-1412), 面板与徽标经这两个无前缀 computed 读; 写入仍走
     * ui_feedback.js 的下划线单点(_recordErrorToast / _clearErrorHistory)。 */
    errHistory() {
      return this._errHistory;
    },
    errUnread() {
      return this._errUnread;
    },
  },
  watch: {
    // 切回辅种页时表格 DOM 是新建的, 需要重新实体化列宽(设置页期间表格不存在)
    page() {
      this.persistUiPage();  // 位置即用户意图: 落盘后才经得起 F5(见 initialPage)
      this.$nextTick(() => {
        this._syncHeadHeight();
        this.recomputeEffective();
      });
    },
    /* 未保存改动防护(U1-b, 报告 26-10-02-0508): 原生 beforeunload 兜底**随脏态**挂载 / 摘除 ——
     * 常驻挂载会让 Firefox 放弃 bfcache, 且没改动也弹框 = 弹框疲劳(报告 §6)。判据与挂载点
     * 都在 config_editor.js(cfgGuardSync), 这里只负责把脏态变化喂过去。 */
    cfgDirty(v) {
      this.cfgGuardSync(v);
    },
    /* 停靠面板 DOM 出入门(drawerVisible: 两形态都限主内容页, 种子详情另限种子视图) ——
     * Vue 的 v-if 拆装会**换掉建图宿主**: uPlot 的 root/canvas 挂在被拆走的旧 .qb-chart-host 上,
     * 回来时 body 重建的是另一个空宿主 —— 旧实例既不可见也不自愈(要到下一次轮询落袋才重画,
     * 而轮询间隔可能是夹取上限 600s), 症状就是「回页后面板里有文字没图」。故在这里显式接管:
     *   退场 -> _qbChartDestroy(拆野引用, ResizeObserver 一并断开);
     *   进场 -> 补拉一发(_qbReloadOnEnter -> _qbLoad 内含 $nextTick 建图): 隐藏期轮询被 active
     *           守卫跳过, 数据与宿主都已陈旧, 这一发同时刷新数据并对新宿主重建图。
     * 流量形态认 qbCurScope 非空。种子详情形态(2026-10-07 报障)的变体宿主(dt-host)同样被拆装
     * 换掉 —— _dtMounted 持有的是被拆走的旧节点, general/content 页签又没有轮询与通知源
     * (trackers/peers 靠下一拍轮询的 _dtNotify 自愈), 变体不会重挂: .dt-host:empty 藏住空宿主 +
     * 经典包裹层 v-show 为 false(选中变体时) = 整幅正文空白。故进场补一发重挂(_dtSync 卸旧
     * 挂新, $nextTick 等 Vue 把新 aside 补进 DOM 再定位宿主); 经典渲染层无此缺口(包裹层是
     * Vue 响应式, aside 重建时按 drawer.* 现值直接重渲染)。 */
    drawerVisible(v) {
      const s = this.qbCurScope;
      if (!s) {
        if (v) this.$nextTick(() => this._dtSync());
        return;
      }
      if (!v) {
        this._qbChartDestroy(s);
        return;
      }
      this._qbReloadOnEnter(s);  // 内含在途不叠加守卫(打开路径首发的那一发不被翻倍)
    },
    // CTX-02: 任一浮层菜单关闭 -> 撤掉触发源强调(浮层可以多种方式关闭: Esc/点空白/执行动作)
    "menu.visible"(v) {
      if (!v) {
        this._clearCtxSource();
        this.keepSub();     // CTX-05: 撤掉挂起的延迟收起(否则一级关了之后还会再触发一次)
        this.subMenu = "";  // FX-15: 一级菜单关闭时子面板一并收起
      }
    },
    "headMenu.visible"(v) {
      if (!v) this._clearCtxSource();
    },
    "filePrio.visible"(v) {
      if (!v) this._clearCtxSource();
    },
    /* 开层后按实测尺寸重钳位(issue 26-10-06-1717): 三个浮层菜单的开层初值都来自 _menuPos 的
     * 常量估算, 而菜单真实高度随分支差一倍以上(批量菜单实测 393px vs 估算 222)—— 锚点落在
     * 视口下部时菜单底越过下缘, 底部项(导出/批量删除)真实点击不可达。
     * 判据用**对象替换**而不是 visible 翻转: 三个菜单的开层入口一律写 `this.X = {…}`
     * (menu.js 的 openMenu/openMemberMenu/openHeadMenu · shows.js 的整集/整剧两入口 ·
     * drawer.js 的 openFilePrio), 关层与执行动作只改字段(X.visible = false) ⇒ 每次开层恰好
     * 触发一次, 连"菜单还开着又右键另一行"(visible 不变、只是换了对象)也覆盖; 钳位回写的是
     * x/y 字段而非整个对象, 不会自触发。量测在 $nextTick(见 ui_feedback.js::_menuFitRefit)。 */
    menu() {
      this.$nextTick(() => this._menuFitRefit("menu", "ctxMenu"));
    },
    headMenu() {
      this.$nextTick(() => this._menuFitRefit("headMenu", "headMenuEl"));
    },
    filePrio() {
      this.$nextTick(() => this._menuFitRefit("filePrio", "filePrioEl"));
    },
    // 抽屉右键菜单(R2 S3): 与三浮层同范式 —— 开层对象替换触发重钳位
    drawerMenu() {
      this.$nextTick(() => this._menuFitRefit("drawerMenu", "drawerMenuEl"));
    },
    // 通知(S1): 打开面板即视为已读, 未读徽标清零 —— 后续面板 UI 直接绑 _errUnread/errPanelOpen。
    // 写入单点在 ui_feedback.js 的 _recordErrorToast / _clearErrorHistory; watcher 放根组件选项
    // 而非 AQB_FEEDBACK mixin —— 见文件顶部 WARN(watch 进全局 mixin 会波及子组件实例)。
    errPanelOpen(v) {
      if (v) this._errUnread = 0;
    },
  },
};
