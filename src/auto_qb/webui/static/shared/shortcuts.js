/* auto-qb WEB UI · 键盘快捷键引擎 + 动作注册表 + 自定义面板(计划 26-09-28-0354 W1-W7)
 *
 * 设计单点(计划 §05, 沿袭 0822 前案):
 *   - 注册表 AQB_SHORTCUT_DEFS 是**键位单一事实源**: 默认键表 / 面板(W6) / 冲突检测 / 守阵断言
 *     全部读这一张表, 表外无键位。
 *   - 匹配用 e.code 物理键位 + 固定修饰序 Ctrl,Alt,Shift,Meta 归一化串, 不用布局相关的 e.key
 *     (录制/重绑在任意布局下可往返; 显示名由 code 映射, 极端布局差异由"可重绑"兜底)。
 *   - 输入态屏蔽: isComposing/keyCode 229 双保险 -> 输入元素(input/textarea/select/contenteditable)
 *     -> 模态层(任一浮层/对话框打开时列表键位一律失效); 另有 repeat(默认丢弃, 仅标记条目
 *     放行长按连发) / 纯修饰键 / defaultPrevented 三道前置拦截。
 *   - Esc 是唯一固定键: 归 lifecycle.js 既有退栈链(FIX-07), 引擎永不接(监听注册序也排在其后,
 *     双保险)。链终端兜底已含清筛选(26-10-01-2108), 键表侧 clear-filters 仍空位(可自定义)。
 *     Delete 键是注册表**外**的"额外删除操作", 引擎直连 _deleteFlow(§08 决策 v4:
 *     删除双入口, 不占键表槽位、不进面板改键列表)。
 *   - 黑名单 KB_BLACKLIST = 浏览器不可拦组合(Ctrl+W/T/N/Q 及 Shift 变体 / 标签页族 / 开发者工具
 *     / Meta 全族), 依据 §3.3 经验边界: Ctrl+S/F/P 可拦不在名单; 面板(W6)拒绑 + 守阵断言默认键不碰。
 *   - 适配器 window.AQB_KEYS.load()/save() 是引擎唯一的存储出口(W6 起接 GET/PUT /api/keys 与
 *     后端 webui-keys.json, 仍保持 load 同步快照语义) —— 引擎对存储介质无感知, 反悔路径见计划 §4.6。
 *
 * !接线(三份 index.html 的 tpl-manifest 清单序, 守阵 test_webui_static_skins.py::_scan_mixin_wiring):
 *   - 本文件必须排在 app.js **之前**(app.js 末尾 app.mixin(window.AQB_SHORTCUTS))。
 *   - keydown 监听在 lifecycle.js mounted 里注册, 排在既有 Esc 退栈链**之后**; data 字段
 *     kbCursor / kbHelpOpen / 面板与录制器状态(kbDraft 等)在 state.js(根选项展开, 不许进
 *     app.mixin —— pitfalls web-ui/frontend-split)。
 *   - W5 局部作用域: scope 五值全量生效 —— settings(设置页 Ctrl+S, inputSafe 输入框内也放行) /
 *     modal(模态层白名单: 模态内只响应模态键位, 本期无条目, 引擎已留位); drawer 档自方案A W2
 *     (计划 26-10-03-0917)起无条目 —— 停靠面板是列表附属, Alt+1-4 改 list 作用域双态(_kbDrawerTab)。
 *     (2026-10-10)详情面板合并页签态: Alt+1~5 按位次重排到三张可见页签(见 KB_MERGE_TAB_REMAP)。
 *   - W6 自定义: 设置页「快捷键」分区(录制器 VS Code 按下即录模式 / 冲突三选一 / 黑名单拒绑 /
 *     单条与全部重置 / 保存 PUT 落盘) + ? 帮助浮层(只读速查)。Esc 是唯一 fixed 键, 面板不可改。
 *   - 流量图三入口(2026-10-05): 打开全局图 Ctrl+Backslash(run 内 qbTrafficOn 门控 + 未启用
 *     提示) / 详情面板流量页签 Alt+5(_kbDrawerTab 内同门控) / 窗口前后切换 [ ](新机制
 *     **when 条件绑定**: 仅 qbTrafficActive 时消费键位, 无流量图时留给浏览器 —— 见条目形状注
 *     与引擎派发处的 when 分流)。
 *   - 光标滚动跟随**禁用 scrollIntoView**(逐层滚动可滚祖先会连带滚整页, pitfalls
 *     web-ui/hover-keynav-fight): 渲染行用 getBoundingClientRect+scrollBy 差值, 窗口化未渲染行
 *     用 _rowWindow 前缀和换算(columns.js 已留存 this._rowPre[kind])。
 *   - 滚动跟随的**上下可见边界各有一个单点**(2026-10-09 首/末行只显示一半的报障收口):
 *     `_kbViewTop()` = 顶栏(_headH) + 吸顶列头(.group-head, 会盖住列表首行) /
 *     `_kbViewBottom()` = 固定状态栏(--statusbar-h) 与停靠面板顶缘取更紧者。
 *     凡"这一行/这个元素在视口里吗"的判定一律走这两个单点, 不许现写 _headH / innerHeight。
 *   - 可见性判定的**坐标口径**(2026-10-09 收口坐标错位): `_kbViewTop` / `_kbViewBottom` 返回
 *     **视口坐标**(与 getBoundingClientRect 同源, 渲染行直接比); 窗口化的前缀和 y 是**文档
 *     坐标**, 比较时显式加回 window.scrollY。两套坐标混用 = 滚动后渲染行全判「出视口」,
 *     无光标回落退化成跳极值行(down 回顶 / up 落底)。
 *   - 键鼠衔接(26-09-30-1806 方案 B): 鼠标点击入口(selection.js 五个 on*Click)按所在行回写
 *     kbCursor —— 落光标 ≠ 选中(focus 语义), 键盘从点击处出发; 无光标回落 = 视口就近行
 *     (_kbViewportRow), 不再落极值行。滚动跟随仍只发生在键盘路径(_kbApplyCursor)。
 *   - 起点统一(26-10-02-0608 方案 B): 区间起点(anchor)与光标一样纳入键鼠统一模型 —— 点击落
 *     起点在 selection.js, 键盘侧在 _kbExtend 移动光标**之前**用 _selSeedAnchorFromCursor 落
 *     "手势原点"(无有效起点时才落), 使 Shift+up/down 首次扩展即从当前光标起算, 不再从列表首行起。
 *     起点解析/写入单点在 selection.js(_selAnchor / _selSetAnchor)。
 *   - 收起语义(2026-10-09): <- 在**成员行**(展开组/展开集的成员)上收起**所属单元**并把光标
 *     带回其行 —— 成员行无自身展开态, 原实现只认 group/show/ep 三种 kind, 光标按 down 进组后
 *     <- 静默无反应(用户报)。父行解析单点 _kbParentRow, 判据复用 selection.js::_memberRangeList
 *     (与 _kbRows 渲染同源), 保证"屏幕上的成员行"与"收起目标"不错位。
 *   - 切换语义(2026-10-09, 报告 26-10-09-1731 §03/§04): 6 条「适合」条目(流量图 Ctrl+\ / 统计 \ /
 *     历史 Shift+\ / 详情面板 I / 帮助 Shift+/ / 列选择器 K)由「只打开」升级为「开/关双态」——
 *     再按一次同一键关掉自己打开的东西(关闭复用既有 closeX/closeDrawer, Esc 仍是唯一固定关闭
 *     出口, 两者不冲突)。抽屉类(流量图/详情面板)不在浮层屏蔽名单, 第二按直达; 浮层类(统计/
 *     历史/帮助/列选择器)靠 KB_SELF_TOGGLE_OVERLAY 自切换白名单放行(见 _kbOnKeyDown)。**只改
 *     键盘 run 路径**, 鼠标入口(状态栏按钮/右键菜单/双击)保持原语义。其余 4 条「有条件」与
 *     49 条「不适合」不动(报告 §05/§06)。
 */

/* 纯修饰键: 自身发 keydown, 匹配器等非修饰键落定才判定(录制器把"只按了 Shift"判无效) */
const KB_MODIFIER_CODES = new Set([
  "ShiftLeft", "ShiftRight", "ControlLeft", "ControlRight",
  "AltLeft", "AltRight", "MetaLeft", "MetaRight", "CapsLock",
]);

/* 事件 -> 归一化键位串: 修饰键固定序 Ctrl,Alt,Shift,Meta + e.code(§3.3 VS Code 展示序同族) */
function kbSerializeEvent(e) {
  const mods = [];
  if (e.ctrlKey) mods.push("Ctrl");
  if (e.altKey) mods.push("Alt");
  if (e.shiftKey) mods.push("Shift");
  if (e.metaKey) mods.push("Meta");
  mods.push(e.code);
  return mods.join("+");
}

/* 浏览器保留键黑名单: preventDefault 无效的组合, 面板(W6)当场拒绑; 引擎侧只作脏数据兜底
 * (§3.3: Ctrl+W/T/N/Q 及其 Shift 变体不可拦; Ctrl+S/F/P 可拦, 留给设置页保存等绑定) */
const KB_BLACKLIST = (() => {
  const bad = new Set();
  // 标签页 / 窗口族(浏览器接管)
  for (const c of ["KeyW", "KeyT", "KeyN", "KeyQ"]) {
    bad.add(`Ctrl+${c}`);
    bad.add(`Ctrl+Shift+${c}`);
  }
  bad.add("Ctrl+Tab");
  bad.add("Ctrl+Shift+Tab");
  for (let i = 1; i <= 8; i++) bad.add(`Ctrl+Digit${i}`);
  bad.add("Ctrl+Shift+KeyN");  // 隐身窗口(与 Ctrl+Shift+KeyT 重复覆盖, 保守再收一档)
  // 开发者工具
  for (const c of ["KeyI", "KeyJ", "KeyC"]) bad.add(`Ctrl+Shift+${c}`);
  bad.add("F12");
  // 系统级
  bad.add("F5");
  bad.add("F11");
  bad.add("Ctrl+Alt+Delete");
  return bad;
})();

function kbInBlacklist(serial) {
  if (serial.split("+").includes("Meta")) return true;  // mac Cmd 全族 OS 先拿
  return KB_BLACKLIST.has(serial);
}

/* 自切换白名单(2026-10-09「切换语义」, 报告 26-10-09-1731 §07.1): 条目 id -> 它自己控制的浮层状态字段。
 * 浮层打开时引擎默认屏蔽列表键位(_kbOverlayBusy), 而「再按一下关」需要第二次按键**抵达 run** ——
 * 若打开着的正是本键自己控制的浮层, 本键仍消费(交给 run 里的切换分支关掉); 其余浮层照旧屏蔽。
 * 只列「浮层类」四条: 抽屉类(流量图/详情面板)不在 _kbOverlayBusy 名单, 第二按本就能直达。
 * 键位唯一性不受影响 —— 这是**派发放行**名单, 不是键表(不新增注册表字段, §07.3)。 */
const KB_SELF_TOGGLE_OVERLAY = {
  "open-stats": "statsOpen",
  "open-history": "historyOpen",
  "help-panel": "kbHelpOpen",
  "col-picker": "colMenuOpen",
};

/* 合并页签态快捷键**位次重排**(2026-10-10 用户报「标签合并后没有同步修改快捷键」):
 * 详情面板合并页签开启且宽度门内时, 页签栏只剩 [常规&内容][Tracker&用户](+流量) 三张可见页签,
 * 注册表五档(Alt+1..5 -> general/trackers/peers/content/traffic)按**位次**重排到可见页签:
 *   第 1 档 -> 常规&内容(general) / 第 2 档 -> Tracker&用户(trackers) / 第 3 档 -> 流量(traffic);
 *   第 4/5 档(原 内容/流量 页) 合并态无独立页签 -> null(停用, 静默)。
 * key = 注册表条目 run 传入的原页签; value = 合并态实际落点(null = 该档停用)。只作用于键盘
 * run 路径(鼠标页签点击走 dtMergeTabPick / drawerTab, 不受影响)。未合并(开关关 / 宽度门外,
 * 页签栏回落四页签)时整张表不生效, 五档原样。 */
const KB_MERGE_TAB_REMAP = {
  general: "general", trackers: "trackers", peers: "traffic", content: null, traffic: null,
};

/* 条目生效键位 = 模板基准(def) ⊕ 草稿 overrides(恒胜出); 空串 = 显式禁用(§4.7) */
function kbSerialWithDraft(item, draft) {
  const ov = (draft && draft.overrides) || {};
  return Object.prototype.hasOwnProperty.call(ov, item.id) ? ov[item.id] : item.def;
}

/* code -> 人类键名(显示用, §3.3): 命中表直接用; Key/Digit/Numpad 前缀取后缀; F 键原样 */
const KB_CODE_NAMES = {
  Escape: "Esc", Delete: "Del", Insert: "Ins",
  ArrowUp: "↑", ArrowDown: "↓", ArrowLeft: "←", ArrowRight: "→",
  Comma: ",", Period: ".", Slash: "/", Backslash: "\\", Semicolon: ";", Quote: "'",
  BracketLeft: "[", BracketRight: "]", Minus: "-", Equal: "=", Backquote: "`",
};

function kbDisplayName(serial) {
  return String(serial).split("+").map((part) => {
    if (part === "Ctrl" || part === "Alt" || part === "Shift" || part === "Meta") return part;
    if (KB_CODE_NAMES[part]) return KB_CODE_NAMES[part];
    const m = part.match(/^(?:Key|Digit|Numpad)(.+)$/);
    if (m) return m[1];
    return part;
  }).join(" + ");
}

/* 默认键位归一化串合法形态: 修饰键按固定序出现至多一次 + 单个 e.code(守阵逐条断言)
 * 与后端 routes/keys.py _KEYS_SERIAL_RE 同一正则, 逐字一致由 tests/webui_static_scan_js.py
 * _scan_keys_serial_re 机械守阵(issue 26-10-11-0310) —— 改一边必须改另一边 */
const KB_DEF_RE = /^(Ctrl\+)?(Alt\+)?(Shift\+)?(Meta\+)?[A-Z][A-Za-z0-9]*$/;

/* ---------------- 动作注册表(单一事实源) ----------------
 * 条目形状: { id, group, label, def, scope, danger?, fixed?, repeat?, when?, run }
 *   def  = 默认键位归一化串; "" = 默认不绑定(空位, 可被自定义); fixed = 不可改键(Esc)。
 *   when = 条件绑定(vm) => bool: 假则本次按键**不消费**(不 preventDefault, 键位留给浏览器/
 *          其它 handler), 用于只在特定界面存在的动作(如流量图窗口切换 [ / ] —— 无流量图时
 *          这两键不该被吞)。条件项照常进面板与冲突检测(键位唯一性不受条件影响)。
 *   repeat = 长按连发: e.repeat 自动重复事件默认被引擎丢弃, 标记后放行(只给光标/选择扩展
 *   上下键族 —— 每按一次就发一条后端命令的键位(队列移动)不开, 免得长按刷爆命令)。
 *   scope = global(任何非输入态) | list(三数据视图) | drawer(抽屉内; 方案A W2 起注册表无条目,
 *           机制留位 —— 停靠面板是列表附属不是作用域, 见 _kbScope) | settings(设置页)
 *           | modal(模态层内, 本期无条目, 引擎已留位)。
 *   danger = 危险档(§08 清单): 键盘路径必经确认框, 面板行内标 WARN; 危险档默认键一律二键组合。
 *   run(vm) = 动作出口, 只映射既有方法不另写实现; W5 全波接线完成(E/F/G/H/I 组激活)。
 * A-D 组为第一波(计划 §06 拍板(5)), E-H 第二波接线; 2026-09-30 决策(3)保留 Shift 族全部进默认表。 */
const AQB_SHORTCUT_DEFS = [
  // ---- A · 视图与全局导航 ----
  { id: "view-groups", group: "视图与导航", label: "切到辅种页",
    def: "Digit1", scope: "global",
    run: (vm) => vm.goView("groups") },
  { id: "view-torrents", group: "视图与导航", label: "切到种子页",
    def: "Digit2", scope: "global",
    run: (vm) => vm.goView("torrents") },
  { id: "view-shows", group: "视图与导航", label: "切到追剧页",
    def: "Digit3", scope: "global",
    run: (vm) => vm.goView("shows") },
  { id: "open-settings", group: "视图与导航", label: "打开设置",
    def: "Ctrl+Comma", scope: "global",
    run: (vm) => vm.openSettings() },
  { id: "add-torrent", group: "视图与导航", label: "添加种子",
    def: "KeyN", scope: "list",
    run: (vm) => vm.openAddTorrent() },
  { id: "focus-search", group: "视图与导航", label: "聚焦搜索框",
    def: "Slash", scope: "list",
    run: (vm) => vm._kbFocusSearch() },
  { id: "open-stats", group: "视图与导航", label: "统计面板",
    def: "Backslash", scope: "global",
    run: (vm) => vm._kbToggleStats() },  // 切换语义: 已开 => closeStats(报告 26-10-09-1731 §03)
  { id: "open-history", group: "视图与导航", label: "历史流量",
    def: "Shift+Backslash", scope: "global",
    run: (vm) => vm._kbToggleHistory() },  // 切换语义: 已开 => closeHistory
  { id: "open-qb-traffic", group: "视图与导航", label: "qB 口径流量图",
    def: "Ctrl+Backslash", scope: "global",
    run: (vm) => vm._kbToggleQbTraffic() },  // 切换语义: 已开同目标 => 关; 未开走 openQbHistory(内含 qbTrafficOn 门 + 未启用提示)
  { id: "speed-down", group: "视图与导航", label: "限速(下载方向)",
    def: "KeyL", scope: "list",
    run: (vm) => vm.openSpeedAt(null, "down") },
  { id: "speed-up", group: "视图与导航", label: "限速(上传方向)",
    def: "Shift+KeyL", scope: "list",
    run: (vm) => vm.openSpeedAt(null, "up") },
  // ---- B · 光标与导航(追剧页走 剧/集 单元; 辅种页走 组行 -> 展开组成员行 的线性链) ----
  { id: "cursor-up", group: "光标与导航", label: "光标上移一行",
    def: "ArrowUp", scope: "list", repeat: true,
    run: (vm) => vm._kbMove(-1) },
  { id: "cursor-down", group: "光标与导航", label: "光标下移一行",
    def: "ArrowDown", scope: "list", repeat: true,
    run: (vm) => vm._kbMove(1) },
  { id: "row-expand", group: "光标与导航", label: "展开当前行",
    def: "ArrowRight", scope: "list",
    run: (vm) => vm._kbExpandRow() },
  // 成员行(展开组/展开集的成员)自身无展开态: <- 改收起**所属单元**并把光标带回其行(_kbParentRow)
  { id: "row-collapse", group: "光标与导航", label: "收起当前行",
    def: "ArrowLeft", scope: "list",
    run: (vm) => vm._kbCollapseRow() },
  { id: "cursor-first", group: "光标与导航", label: "跳到首行",
    def: "Home", scope: "list",
    run: (vm) => vm._kbMoveTo(0) },
  { id: "cursor-last", group: "光标与导航", label: "跳到末行",
    def: "End", scope: "list",
    run: (vm) => vm._kbMoveTo(-1) },
  { id: "page-up", group: "光标与导航", label: "上翻一屏",
    def: "PageUp", scope: "list",
    run: (vm) => vm._kbMovePage(-1) },
  { id: "page-down", group: "光标与导航", label: "下翻一屏",
    def: "PageDown", scope: "list",
    run: (vm) => vm._kbMovePage(1) },
  { id: "row-open", group: "光标与导航", label: "打开当前行(组行=展开明细, 种子行=详情面板)",
    def: "Enter", scope: "list",
    run: (vm) => vm._kbOpenRow() },
  // ---- C · 选择 ----
  { id: "toggle-select", group: "选择", label: "切换当前行选中",
    def: "Space", scope: "list",
    run: (vm) => vm._kbToggleSelect() },
  { id: "extend-up", group: "选择", label: "向上扩展选择",
    def: "Shift+ArrowUp", scope: "list", repeat: true,
    run: (vm) => vm._kbExtend(-1) },
  { id: "extend-down", group: "选择", label: "向下扩展选择",
    def: "Shift+ArrowDown", scope: "list", repeat: true,
    run: (vm) => vm._kbExtend(1) },
  { id: "select-all", group: "选择", label: "全选当前视图",
    def: "Ctrl+KeyA", scope: "list",
    run: (vm) => vm._kbSelectAll() },
  { id: "clear-esc", group: "选择", label: "清除选择 / 逐层退栈 / 清筛选",
    def: "Escape", scope: "global", fixed: true,
    run: null },  // 既有 lifecycle.js 退栈链(FIX-07)实现, 引擎永不接(注册表登记只为守阵与面板展示)
  // ---- D · 一级动作(§08 决策 v4: 危险档一律二键组合; 裸键 D/C/F 释放为空位) ----
  { id: "act-pause", group: "一级动作", label: "停止",
    def: "KeyP", scope: "list",
    run: (vm) => vm._kbAct("pause") },
  { id: "act-resume", group: "一级动作", label: "启动",
    def: "KeyS", scope: "list",
    run: (vm) => vm._kbAct("resume") },
  { id: "act-reannounce", group: "一级动作", label: "强制重新汇报",
    def: "Shift+KeyA", scope: "list", danger: true,
    run: (vm) => vm._kbAct("reannounce") },
  { id: "act-recheck", group: "一级动作", label: "强制重新检查",
    def: "Shift+KeyY", scope: "list", danger: true,
    run: (vm) => vm._kbAct("recheck") },
  { id: "act-detail", group: "一级动作", label: "详细信息(详情面板)",
    def: "KeyI", scope: "list",
    run: (vm) => vm._kbOpenDrawer() },
  { id: "act-meta", group: "一级动作", label: "标签 / 分类",
    def: "KeyM", scope: "list",
    run: (vm) => vm._kbMeta() },
  { id: "act-open-folder", group: "一级动作", label: "打开目标文件夹",
    def: "KeyO", scope: "list",
    run: (vm) => vm._kbOpenFolder() },
  { id: "act-delete", group: "一级动作", label: "删除所选",
    def: "Shift+KeyD", scope: "list", danger: true,
    run: (vm) => vm._kbDelete() },
  // ---- E · 次要动作(Shift 族, §08 决策(3)保留; 单目标动作: 目标解析须唯一 hash, §5.2) ----
  { id: "edit-move", group: "次要动作", label: "移动位置",
    def: "Shift+KeyV", scope: "list",
    run: (vm) => vm._kbEditAct("editMove") },
  { id: "edit-rename", group: "次要动作", label: "重命名",
    def: "Shift+KeyR", scope: "list",
    run: (vm) => vm._kbEditAct("editRename") },
  { id: "export-torrent", group: "次要动作", label: "导出 .torrent",
    def: "Shift+KeyE", scope: "list",
    run: (vm) => vm._kbEditAct("exportTorrent") },
  { id: "copy-name", group: "次要动作", label: "复制名称",
    def: "Shift+KeyC", scope: "list",
    run: (vm) => vm._kbEditAct("copyTorrentInfo", "name") },
  { id: "copy-hash", group: "次要动作", label: "复制哈希",
    def: "Shift+KeyH", scope: "list",
    run: (vm) => vm._kbEditAct("copyTorrentInfo", "hash") },
  // copy-magnet(Shift+KeyG)已退役(issue 26-11-09-0639): magnet_uri 入库即掩码(26-11-08-0043),
  // 复制出的是 tr= 已掩的废链接, 与右键菜单入口同批移除。
  { id: "col-picker", group: "次要动作", label: "列选择器",
    def: "KeyK", scope: "list",
    run: (vm) => vm.toggleColMenu(null) },  // toggleColMenu 本身即切换函数; 浮层开着时靠自切换白名单放行第二次按键(报告 26-10-09-1731 §04.4)
  // ---- F · 队列与开关(§08 决策(3): F5/F6 保留默认键; 均为单种子命令, 复用右键菜单同链) ----
  { id: "queue-up", group: "队列与开关", label: "向上移动队列",
    def: "Ctrl+ArrowUp", scope: "list",
    run: (vm) => vm._kbTorrentCmd("queue", () => ({ action: "up" }), "向上移动队列") },
  { id: "queue-down", group: "队列与开关", label: "向下移动队列",
    def: "Ctrl+ArrowDown", scope: "list",
    run: (vm) => vm._kbTorrentCmd("queue", () => ({ action: "down" }), "向下移动队列") },
  { id: "queue-top", group: "队列与开关", label: "队列顶部",
    def: "Ctrl+Home", scope: "list",
    run: (vm) => vm._kbTorrentCmd("queue", () => ({ action: "top" }), "队列顶部") },
  { id: "queue-bottom", group: "队列与开关", label: "队列底部",
    def: "Ctrl+End", scope: "list",
    run: (vm) => vm._kbTorrentCmd("queue", () => ({ action: "bottom" }), "队列底部") },
  { id: "auto-tmm", group: "队列与开关", label: "自动种子管理(TMM)切换",
    def: "Shift+KeyT", scope: "list",
    run: (vm) => vm._kbTorrentToggle("auto-tmm", "auto_tmm", "自动种子管理") },
  { id: "force-start", group: "队列与开关", label: "强制启动切换",
    def: "Shift+KeyF", scope: "list",
    run: (vm) => vm._kbTorrentToggle("force-start", "force_start", "强制启动") },  // 可逆故不入危险档(§08)
  // ---- G · 局部作用域(设置页局部键位, W5; 方案A W2 起详情面板四条独立成组, 双态见 _kbDrawerTab;
  //      2026-10-10 起合并页签态下五档按位次重排到三张可见页签, 见 KB_MERGE_TAB_REMAP / _kbMergeTabsOn) ----
  { id: "drawer-tab-general", group: "详情面板", label: "详情面板 · 打开/切到常规页",
    def: "Alt+Digit1", scope: "list",
    run: (vm) => vm._kbDrawerTab("general") },
  { id: "drawer-tab-trackers", group: "详情面板", label: "详情面板 · 打开/切到 Tracker 页",
    def: "Alt+Digit2", scope: "list",
    run: (vm) => vm._kbDrawerTab("trackers") },
  { id: "drawer-tab-peers", group: "详情面板", label: "详情面板 · 打开/切到用户页",
    def: "Alt+Digit3", scope: "list",
    run: (vm) => vm._kbDrawerTab("peers") },
  { id: "drawer-tab-content", group: "详情面板", label: "详情面板 · 打开/切到内容页",
    def: "Alt+Digit4", scope: "list",
    run: (vm) => vm._kbDrawerTab("content") },
  { id: "drawer-tab-traffic", group: "详情面板", label: "详情面板 · 打开/切到流量页",
    def: "Alt+Digit5", scope: "list",
    run: (vm) => vm._kbDrawerTab("traffic") },  // 功能未启用时 _kbDrawerTab 内提示后忽略(页签按钮 v-if=qbTrafficOn 不渲染)
  // ---- J · 流量图(2026-10-05): 窗口前后切换 —— when 条件绑定, 仅流量图可见时消费 [ / ]
  // (无流量图时键位不消费, 留给浏览器; 端点由 qbCycleWindow 夹取, 走 qbSetWindow 单点重拉+落盘) ----
  { id: "traffic-win-prev", group: "流量图", label: "流量图 · 前一档窗口",
    def: "BracketLeft", scope: "global", when: (vm) => vm.qbTrafficActive,
    run: (vm) => vm.qbCycleWindow(-1) },
  { id: "traffic-win-next", group: "流量图", label: "流量图 · 后一档窗口",
    def: "BracketRight", scope: "global", when: (vm) => vm.qbTrafficActive,
    run: (vm) => vm.qbCycleWindow(1) },
  { id: "settings-save", group: "局部作用域", label: "设置页 · 保存配置",
    def: "Ctrl+KeyS", scope: "settings", inputSafe: true,
    run: (vm) => vm.cfgSave() },  // inputSafe: 输入框内也放行; 浏览器保存网页可拦, §3.3
  // 设置页"放弃改动"(G6)危险且无撤销, 默认不绑定也不注册(§08: 默认留给鼠标)
  // ---- H · 面板(W6) ----
  { id: "help-panel", group: "面板", label: "打开快捷键帮助面板",
    def: "Shift+Slash", scope: "global",
    run: (vm) => vm._kbToggleKbHelp() },  // 切换语义: 已开 => closeKbHelp(只读速查浮层, 附「前往设置自定义」; 面板内 Esc 关闭归退栈链)
  // ---- I · 默认不绑定空位(可自定义) ----
  { id: "super-seeding", group: "更多动作", label: "超级做种切换",
    def: "", scope: "list", danger: true,
    run: (vm) => vm._kbTorrentToggle("super-seeding", "super_seeding", "超级做种") },  // 静默改变做种语义故标危险(§08; 切换可逆, 无确认框, 面板标 WARN:)
  { id: "share-limits", group: "更多动作", label: "分享率限制",
    def: "", scope: "list",
    run: (vm) => vm._kbEditAct("editShareLimits") },
  { id: "clear-filters", group: "更多动作", label: "清除全部筛选",
    def: "", scope: "list",
    run: (vm) => vm.clearFilters() },  // Esc 触发路径走退栈链兜底(lifecycle), 不走键表; 此处保持空位供自定义其它键
  { id: "invert-select", group: "更多动作", label: "反选当前视图",
    def: "", scope: "list",
    run: (vm) => vm._kbInvertSel() },  // 大库反选代价高, 默认不给键(0822 I6)
];

/* ---------------- 存储适配器(单一出口, 计划 §4.4; W6 接通 GET/PUT /api/keys) ----------------
 * 后端 auto-qb-data/webui-keys.json(web 线程独占, 与 state.json 互不干扰); 结构按 §4.7 预埋:
 * { schema_version, template, overrides } —— overrides 只存用户改过的条目, 未提及的 action 用
 * 当前模板基准; 空串 = 显式禁用。
 * 语义: load() 保持**同步快照**(引擎在 keydown 里现取, 不 await); 服务端真值由 reload() 异步
 * 拉进来后由调用方失效 _kbTableCache; save() 整份 PUT, 失败返回 {ok:false} 由调用方本地回滚。
 * !两处请求走低层带超时单点 aqbFetch(issue 26-10-16-1303): 裸 fetch 悬挂时 await 永不返回 =>
 *   reload 恒不返回 false(启动拉取卡住)、save 恒不返回 {ok:false}(面板永不复位)—— 无提示也不自愈。
 * (先 const 后挂 window: 它是被本文件 _kbTable 直接消费的适配器单例, 不是 Vue mixin 片段 ——
 *  不走 app.mixin, 也别写成 `window.X = {` 字面量形态, 那会被片段接线守阵当漏注入。) */
const AQB_KEYS_DEFAULT = () => ({ schema_version: 1, template: "aqb-default", overrides: {} });
const AQB_KEYS_ADAPTER = {
  _doc: null,  // 最近一次生效的配置(服务端真值或面板即时试用稿); null = 用默认表
  /* 引擎唯一同步出口: 未拉到/拉取失败一律回默认表(启动失败由调用方 toast 提示, 不阻塞按键) */
  load() {
    return this._doc || AQB_KEYS_DEFAULT();
  },
  /* 面板即时试用/回滚单点: 换稿后由调用方失效 this._kbTableCache */
  apply(doc) {
    this._doc = doc;
  },
  /* 启动/打开面板时拉服务端真值; 网络失败/非 2xx 返回 false(不炸, 维持现有内存稿) */
    async reload(token) {
      try {
        const headers = { ...aqbAuthHeaders(token) };
        const r = await aqbFetch("/api/keys", { headers });
      if (!r.ok) return false;
      this._doc = this._sanitize(await r.json());
      return true;
    } catch {
      return false;
    }
  },
  /* PUT 整份替换; 失败返回 {ok:false, error}(调用方本地回滚 + 报错, 计划 §4.4) */
    async save(doc, token) {
      try {
        const headers = { "Content-Type": "application/json", ...aqbAuthHeaders(token) };
        const r = await aqbFetch("/api/keys", { method: "PUT", headers, body: JSON.stringify(doc) });
      if (!r.ok) {
        const detail = await r.json().catch(() => ({}));
        return { ok: false, error: detail.detail || `HTTP ${r.status}` };
      }
      return { ok: true };
    } catch (e) {
      return { ok: false, error: e.message || "网络错误" };
    }
  },
  /* 服务端脏数据第二道兜底(后端读时已兜一层): 版本不识别/结构不符回默认, 非法值条目丢弃 */
  _sanitize(doc) {
    if (!doc || typeof doc !== "object" || doc.schema_version !== 1) return AQB_KEYS_DEFAULT();
    const overrides = {};
    if (doc.overrides && typeof doc.overrides === "object") {
      for (const k of Object.keys(doc.overrides)) {
        const v = doc.overrides[k];
        if (typeof v === "string" && (!v || KB_DEF_RE.test(v))) overrides[k] = v;
      }
    }
    return {
      schema_version: 1,
      template: typeof doc.template === "string" && doc.template ? doc.template : "aqb-default",
      overrides,
    };
  },
};
window.AQB_KEYS = AQB_KEYS_ADAPTER;

window.AQB_SHORTCUTS = {
  methods: {
  },
};
