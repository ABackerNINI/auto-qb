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
      // 种子详情抽屉(R1B): 各 tab 数据与加载态; _drawerTimer 轮询句柄挂实例(非响应式)
      // collapsed(W3 方案A): 收起态 = 只留头部(~44px), 展开恢复; 字段必须显式建(vue-reactivity 坑)
      drawer: {
        open: false, collapsed: false, hash: "", tab: "general", loading: false, error: "",
        detail: null, trackers: [], files: [], peers: { peers: [] },
        trackersLoading: false, filesLoading: false, peersLoading: false,
        // FX-29 切换目标期的遮罩态: 保留旧内容撑住面板几何, 遮罩盖住旧值防误读, 新数据到手才撤
        switching: false,
      },
      drawerLastTab: initialDrawerTab(),  // 记住上次停留的 tab(跨种子打开 + 刷新保持); 见 initialDrawerTab()
      // 面板高度记忆(W3 方案A): 用户拖拽调高后的 px; null = 未拖拽过, 走 CSS 默认上限 42vh。
      // D1 拍板: 首屏默认收起(drawer.open 初值 false 不回读 drawerOpen 键), 高度记忆仍生效
      drawerHeightPx: initialDrawerHeight(),
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
      flags: { skip_check_menu: false },
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
      _modalResolve: null,    // 模态 Promise 的 resolve(单例, 关闭时结算)
      _colAlignCss: "",       // 已注入的列对齐 CSS(值未变不重写 <style>)
      _headH: 0,              // 顶栏+状态条实测高度(写 :root --head-h, 供左栏吸顶定位; 含批量段, FIX-06)
      // P1-3 顶栏尺寸观察器: 元素引用 / 观察器 / rAF 句柄(字段名避开同名方法 _headEl)
      _headObsEl: null,
      _headObs: null,
      _headRaf: 0,
      // 多选(分组表/明细表): Ctrl/⌘+点击切换, Shift+点击锚点范围; 普通点击行为不变(组=展开)
      selGroups: [],          // 选中组 key
      selMembers: [],         // 选中成员 hash
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
  },
};
