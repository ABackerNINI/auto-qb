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
 * !接线(三份 index.html 的 tpl-manifest 清单序, 守阵 test_web.py::_scan_mixin_wiring):
 *   - 本文件必须排在 app.js **之前**(app.js 末尾 app.mixin(window.AQB_SHORTCUTS))。
 *   - keydown 监听在 lifecycle.js mounted 里注册, 排在既有 Esc 退栈链**之后**; data 字段
 *     kbCursor / kbHelpOpen / 面板与录制器状态(kbDraft 等)在 state.js(根选项展开, 不许进
 *     app.mixin —— pitfalls web-ui/frontend-split)。
 *   - W5 局部作用域: scope 五值全量生效 —— settings(设置页 Ctrl+S, inputSafe 输入框内也放行) /
 *     modal(模态层白名单: 模态内只响应模态键位, 本期无条目, 引擎已留位); drawer 档自方案A W2
 *     (计划 26-10-03-0917)起无条目 —— 停靠面板是列表附属, Alt+1-4 改 list 作用域双态(_kbDrawerTab)。
 *   - W6 自定义: 设置页「快捷键」分区(录制器 VS Code 按下即录模式 / 冲突三选一 / 黑名单拒绑 /
 *     单条与全部重置 / 保存 PUT 落盘) + ? 帮助浮层(只读速查)。Esc 是唯一 fixed 键, 面板不可改。
 *   - 流量图三入口(2026-10-05): 打开全局图 Ctrl+Backslash(run 内 qbTrafficOn 门控 + 未启用
 *     提示) / 详情面板流量页签 Alt+5(_kbDrawerTab 内同门控) / 窗口前后切换 [ ](新机制
 *     **when 条件绑定**: 仅 qbTrafficActive 时消费键位, 无流量图时留给浏览器 —— 见条目形状注
 *     与引擎派发处的 when 分流)。
 *   - 光标滚动跟随**禁用 scrollIntoView**(逐层滚动可滚祖先会连带滚整页, pitfalls
 *     web-ui/hover-keynav-fight): 渲染行用 getBoundingClientRect+scrollBy 差值, 窗口化未渲染行
 *     用 _rowWindow 前缀和换算(columns.js 已留存 this._rowPre[kind])。
 *   - 键鼠衔接(26-09-30-1806 方案 B): 鼠标点击入口(selection.js 五个 on*Click)按所在行回写
 *     kbCursor —— 落光标 ≠ 选中(focus 语义), 键盘从点击处出发; 无光标回落 = 视口就近行
 *     (_kbViewportRow), 不再落极值行。滚动跟随仍只发生在键盘路径(_kbApplyCursor)。
 *   - 起点统一(26-10-02-0608 方案 B): 区间起点(anchor)与光标一样纳入键鼠统一模型 —— 点击落
 *     起点在 selection.js, 键盘侧在 _kbExtend 移动光标**之前**用 _selSeedAnchorFromCursor 落
 *     "手势原点"(无有效起点时才落), 使 Shift+↑↓ 首次扩展即从当前光标起算, 不再从列表首行起。
 *     起点解析/写入单点在 selection.js(_selAnchor / _selSetAnchor)。
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

/* 默认键位归一化串合法形态: 修饰键按固定序出现至多一次 + 单个 e.code(守阵逐条断言) */
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
 * A-D 组为第一波(计划 §06 拍板⑤), E-H 第二波接线; 2026-09-30 决策③保留 Shift 族全部进默认表。 */
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
    run: (vm) => vm.openStats() },
  { id: "open-history", group: "视图与导航", label: "历史流量",
    def: "Shift+Backslash", scope: "global",
    run: (vm) => vm.openHistory() },
  { id: "open-qb-traffic", group: "视图与导航", label: "qB 口径流量图",
    def: "Ctrl+Backslash", scope: "global",
    run: (vm) => vm.openQbHistory() },  // 状态栏入口的键盘对应(openQbHistory 内含 qbTrafficOn 门 + 未启用提示)
  { id: "speed-down", group: "视图与导航", label: "限速(下载方向)",
    def: "KeyL", scope: "list",
    run: (vm) => vm.openSpeedAt(null, "down") },
  { id: "speed-up", group: "视图与导航", label: "限速(上传方向)",
    def: "Shift+KeyL", scope: "list",
    run: (vm) => vm.openSpeedAt(null, "up") },
  // ---- B · 光标与导航(追剧页走 剧/集 单元; 辅种页只走组行线性链, 成员行 vNext, §08 决策②) ----
  { id: "cursor-up", group: "光标与导航", label: "光标上移一行",
    def: "ArrowUp", scope: "list", repeat: true,
    run: (vm) => vm._kbMove(-1) },
  { id: "cursor-down", group: "光标与导航", label: "光标下移一行",
    def: "ArrowDown", scope: "list", repeat: true,
    run: (vm) => vm._kbMove(1) },
  { id: "row-expand", group: "光标与导航", label: "展开当前行",
    def: "ArrowRight", scope: "list",
    run: (vm) => vm._kbExpandRow() },
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
  { id: "act-pause", group: "一级动作", label: "暂停",
    def: "KeyP", scope: "list",
    run: (vm) => vm._kbAct("pause") },
  { id: "act-resume", group: "一级动作", label: "开始",
    def: "KeyS", scope: "list",
    run: (vm) => vm._kbAct("resume") },
  { id: "act-reannounce", group: "一级动作", label: "强制汇报",
    def: "Shift+KeyA", scope: "list", danger: true,
    run: (vm) => vm._kbAct("reannounce") },
  { id: "act-recheck", group: "一级动作", label: "重新校验",
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
  // ---- E · 次要动作(Shift 族, §08 决策③保留; 单目标动作: 目标解析须唯一 hash, §5.2) ----
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
  { id: "copy-magnet", group: "次要动作", label: "复制 magnet",
    def: "Shift+KeyG", scope: "list",
    run: (vm) => vm._kbEditAct("copyTorrentInfo", "magnet") },
  { id: "col-picker", group: "次要动作", label: "列选择器",
    def: "KeyK", scope: "list",
    run: (vm) => vm.toggleColMenu(null) },  // 按钮路径(常规 CSS 定位); 键盘再按被浮层屏蔽, 关闭走 Esc
  // ---- F · 队列与开关(§08 决策③: F5/F6 保留默认键; 均为单种子命令, 复用右键菜单同链) ----
  { id: "queue-up", group: "队列与开关", label: "队列上移",
    def: "Ctrl+ArrowUp", scope: "list",
    run: (vm) => vm._kbTorrentCmd("queue", () => ({ action: "up" }), "队列上移") },
  { id: "queue-down", group: "队列与开关", label: "队列下移",
    def: "Ctrl+ArrowDown", scope: "list",
    run: (vm) => vm._kbTorrentCmd("queue", () => ({ action: "down" }), "队列下移") },
  { id: "queue-top", group: "队列与开关", label: "队列置顶",
    def: "Ctrl+Home", scope: "list",
    run: (vm) => vm._kbTorrentCmd("queue", () => ({ action: "top" }), "队列置顶") },
  { id: "queue-bottom", group: "队列与开关", label: "队列置底",
    def: "Ctrl+End", scope: "list",
    run: (vm) => vm._kbTorrentCmd("queue", () => ({ action: "bottom" }), "队列置底") },
  { id: "auto-tmm", group: "队列与开关", label: "自动种子管理(TMM)切换",
    def: "Shift+KeyT", scope: "list",
    run: (vm) => vm._kbTorrentToggle("auto-tmm", "auto_tmm", "自动种子管理") },
  { id: "force-start", group: "队列与开关", label: "强制开始切换",
    def: "Shift+KeyF", scope: "list",
    run: (vm) => vm._kbTorrentToggle("force-start", "force_start", "强制开始") },  // 可逆故不入危险档(§08)
  // ---- G · 局部作用域(设置页局部键位, W5; 方案A W2 起详情面板四条独立成组, 双态见 _kbDrawerTab) ----
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
    run: (vm) => vm.kbOpenHelp() },  // 只读速查浮层(附「前往设置自定义」); 面板内 Esc 关闭归退栈链
  // ---- I · 默认不绑定空位(可自定义) ----
  { id: "super-seeding", group: "更多动作", label: "超级做种切换",
    def: "", scope: "list", danger: true,
    run: (vm) => vm._kbTorrentToggle("super-seeding", "super_seeding", "超级做种") },  // 静默改变做种语义故标危险(§08; 切换可逆, 无确认框, 面板标 ⚠)
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
      const headers = {};
      if (token) headers.Authorization = `Bearer ${token}`;
      const r = await fetch("/api/keys", { headers });
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
      const headers = { "Content-Type": "application/json" };
      if (token) headers.Authorization = `Bearer ${token}`;
      const r = await fetch("/api/keys", { method: "PUT", headers, body: JSON.stringify(doc) });
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
    /* ---------------- 引擎: 匹配与屏蔽 ---------------- */
    /* 生效键表(模板基准 ⊕ overrides): 序列 -> 注册表条目。fixed(Esc)不进匹配表;
     * 黑名单串/空串(显式禁用)跳过 —— 后端脏数据在引擎层也不生效(守阵另断言默认键全干净)。 */
    _kbTable() {
      if (this._kbTableCache) return this._kbTableCache;
      const cfg = window.AQB_KEYS.load();
      const overrides = (cfg && cfg.overrides) || {};
      const map = new Map();
      for (const item of AQB_SHORTCUT_DEFS) {
        if (item.fixed || !item.run) continue;
        const serial = Object.prototype.hasOwnProperty.call(overrides, item.id) ? overrides[item.id] : item.def;
        if (!serial || kbInBlacklist(serial) || map.has(serial)) continue;
        map.set(serial, item);
      }
      this._kbTableCache = map;
      return map;
    },
    /* 当前作用域(五值之三取二; modal 在派发处单独分流):
     * 方案A W2(计划 26-10-03-0917 §3.2): 停靠面板**不再是键盘作用域** —— 它是种子列表的附属
     * 面板而非浮层, 面板开着时列表键位保持存活(§2.2 矩阵), scope 落 "list"(Delete 直连同样依赖
     * 此判定)。W1 曾临时让 drawer.open 判成 "drawer" 保逐键零回归, 随 _kbOverlayBusy 摘名单
     * 一并取消; "drawer" 值与下方浮层放行分支的 scope==="drawer" 判定机制保留(条目清空, 引擎留位)。 */
    _kbScope() {
      if (this.page === "settings") return "settings";
      return "list";
    },
    /* 模态层名单: 与 dialogs.js escBusy 的**浮层名单**同形, 但不含选择/展开兜底段
     * (有选中时快捷键必须照常可用 —— 目标解析走选中集合; escBusy 是 Esc 退栈专用, 不能混用)。
     * 方案A W2: 名单摘除 drawer.open —— 停靠面板不是浮层, Delete 等注册表外绑定与列表键在面板
     * 开着时保持可用; escBusy(退栈链)仍含 drawer.open(Esc 关面板), 两名单自此职责分叉。 */
    _kbOverlayBusy() {
      return !!(this.modal.visible || this.addOpen || this.statsOpen || this.speedOpen || this.mgrOpen ||
        this.metaOpen || this.filePrio.visible || this.historyOpen || this.headMenu.visible ||
        this.colMenuOpen || this.uiMenuOpen || this.searchHelpOpen || this.filterMenu || this.menu.visible ||
        this.kbHelpOpen);
    },
    /* 引擎入口(lifecycle.js mounted 注册在 Esc 退栈链之后; unmounted 撤除) */
    _kbOnKeyDown(e) {
      if (e.key === "Escape") return;                  // 固定键归退栈链, 引擎永不接(§08 C5)
      if (e.defaultPrevented) return;                  // 多 handler 礼仪: 先到先得
      if (e.isComposing || e.keyCode === 229) return;  // IME 组合期双保险(§3.4)
      if (KB_MODIFIER_CODES.has(e.code)) return;       // 纯修饰键不判定
      if (!this.authOk) return;                        // 登录遮罩期不响应
      const item = this._kbTable().get(kbSerializeEvent(e));
      if (e.repeat && !(item && item.repeat)) return;  // 长按自动重复默认丢弃; repeat 条目(上下键族)放行连发
      const t = e.target;
      const inInput = !!(t && t.closest && t.closest("input, textarea, select, [contenteditable]"));
      if (!item) {
        // Delete 键是注册表**外**的"额外删除操作"(§08 决策 v4): 直连删除链(_kbDelete 内部走
        // _deleteFlow 的确认框 + HR 风险点名, 与批量删除同链), 不占键表槽位、不进面板改键列表。
        // 上游 qB WebUI 习惯对齐(Delete 删除所选); Shift+Delete 同走确认框, 无"永久删"分支。
        if (!inInput && e.code === "Delete" && !e.ctrlKey && !e.altKey && !e.metaKey &&
            !this._kbOverlayBusy() && this._kbScope() === "list") {
          e.preventDefault();
          this._kbDelete();
        }
        return;
      }
      if (inInput && !item.inputSafe) return;          // 输入元素内只放行显式标记 inputSafe 的绑定
      const scope = this._kbScope();
      if (item.scope === "modal") {
        if (!this.modal.visible) return;               // 模态键位仅在模态层内响应(§5.1 三段之三)
      } else if (this.modal.visible) {
        return;                                        // 模态层打开: 只响应模态键位, 其余一律失效
      } else if (!inInput && this._kbOverlayBusy()) {
        // 浮层打开: 只放行焦点局部(设置页 Ctrl+S)自身的键位 —— 列表键位在浮层下仍然失效(同 W1-W4)。
        // 方案A W2: drawer.open 已摘出浮层名单 —— 停靠面板是列表附属不是浮层, 面板开着列表键位
        // 全部存活(§2.2 矩阵); scope==="drawer" 判定随名单摘除不再可达, 机制保留(条目清空)。
        if (item.scope !== scope || (scope !== "drawer" && scope !== "settings")) return;
      } else if (item.scope !== "global" && item.scope !== scope) {
        return;                                        // 非焦点页不串扰
      }
      // 条件绑定(表头 when, 见注册表条目形状注): 条件不成立即**不消费**本次按键 ——
      // 不 preventDefault, 键位留给浏览器/其它 handler(流量图窗口键 [ / ] 无图时不该被吞)
      if (item.when && !item.when(this)) return;
      e.preventDefault();
      item.run(this);
    },
    /* ---------------- W2: 光标模型(按身份不按下标) ---------------- */
    /* 光标线性链: 辅种页=组行; 种子页=平铺行; 追剧页=剧/集单元(决策②: 成员行 vNext)。
     * 每次移动时现取现定位 —— 轮询整表替换/排序/筛选后身份重定位天然成立, 不需刷新钩子。 */
    _kbRows() {
      if (this.page !== "groups") return [];
      if (this.viewMode === "torrents") return this.filteredTorrents.map((m) => ({ kind: "torrent", id: m.hash }));
      if (this.viewMode === "shows") {
        const out = [];
        for (const s of this.decoratedShows) {
          out.push({ kind: "show", id: s.key });
          if (this.expandedShows.includes(s.key)) {
            for (const sn of s.seasons) {
              for (const e of sn.episodes) out.push({ kind: "ep", id: this.showEpRowId(s.key, sn.season, e.epKeyStr) });
            }
          }
        }
        return out;
      }
      return this.filteredGroups.map((g) => ({ kind: "group", id: g.key }));
    },
    isKbCursor(kind, id) {
      const c = this.kbCursor;
      return !!c && c.kind === kind && c.id === id;
    },
    _kbApplyCursor(rows, idx) {
      this.kbCursor = rows[idx];
      this._kbScrollRowIntoView(rows, idx);
      this._kbFollowDrawer();  // 方案A W2 跟随单点(§2.3; page+kind 守卫在方法内, 相邻视图零开销返回)
    },
    _kbMove(delta) {
      const rows = this._kbRows();
      if (!rows.length) {
        this.kbCursor = null;
        return;
      }
      const cur = this.kbCursor ? rows.findIndex((r) => r.kind === this.kbCursor.kind && r.id === this.kbCursor.id) : -1;
      // 光标失效(无光标/刷新换人/切视图/点击的明细行不在链上): 回落**视口就近行**(26-09-30-1806
      // 方案 B) —— 下移落视口内首行, 上移落视口内末行, 一次按键落在眼前, 不再跳极值行(大库上
      // 即「鼠标在顶部按一下 ↑ 视口跳到底」); 解析不出视口信息才退回旧口径(下移首行/上移末行)。
      // 找得到光标则裁剪夹取(就近步进口径)。
      const idx = cur < 0
        ? this._kbViewportRow(rows, delta)
        : Math.max(0, Math.min(rows.length - 1, cur + delta));
      if (idx === cur) return;
      this._kbApplyCursor(rows, idx);
    },
    /* 无光标回落: 视口就近行(报告 26-09-30-1806 方案 B)。↓(delta>0) 落视口内首行, ↑ 落视口内
     * 末行。两条解析路: ①窗口化视图(group/torrent)用 _rowPre 前缀和换算文档 y(与
     * _kbScrollRowIntoView 同源, 长度不符视为失效, 沿用 P1-2 退避口径); ②其余情形(追剧页全量
     * 渲染 / 小列表不开窗 / 前缀和失效)扫渲染行可见性 —— 视图切换是 v-if, DOM 里只有当前视图。
     * 都解析不出 → 退回旧口径: ↓ 首行 / ↑ 末行(保守, 不猜错)。只读几何, 滚动仍归 _kbApplyCursor。 */
    _kbViewportRow(rows, delta) {
      const headH = this._headH || 0;
      const vTop = window.scrollY + headH + 4;
      const vBot = window.scrollY + this._kbViewBottom() - 4;  // 面板开着时下界让位面板顶缘(W4)
      const kind = rows[0].kind === "torrent" || rows[0].kind === "group" ? rows[0].kind : null;
      const pre = kind && this._rowPre && this._rowPre[kind];
      if (pre && pre.length === rows.length + 1) {
        const top = this._winTop[kind] || 0;
        if (delta > 0) {
          for (let i = 0; i < rows.length; i++) {
            if (pre[i + 1] + top > vTop) return i;  // 首个底边伸进视口的行
          }
        } else {
          for (let i = rows.length - 1; i >= 0; i--) {
            if (pre[i] + top < vBot) return i;  // 末个顶边伸进视口的行
          }
        }
        return delta > 0 ? 0 : rows.length - 1;
      }
      const byId = new Map(rows.map((r, i) => [r.id, i]));
      let first = -1;
      let last = -1;
      for (const el of document.querySelectorAll("[data-key], [data-hash]")) {
        const dk = el.getAttribute("data-key");
        const i = byId.get(dk !== null ? dk : el.getAttribute("data-hash"));
        if (i === undefined) continue;
        const rect = el.getBoundingClientRect();
        if (rect.bottom <= vTop || rect.top >= vBot) continue;  // 完全出视口(display:none 恒 0 也被挡)
        if (first < 0 || i < first) first = i;
        if (i > last) last = i;
      }
      if (delta > 0) return first >= 0 ? first : 0;
      return last >= 0 ? last : rows.length - 1;
    },
    _kbMoveTo(idx) {
      const rows = this._kbRows();
      if (!rows.length) return;
      this._kbApplyCursor(rows, idx < 0 ? rows.length - 1 : Math.max(0, Math.min(rows.length - 1, idx)));
    },
    _kbMovePage(dir) {
      const rows = this._kbRows();
      if (!rows.length) return;
      const kind = this.kbCursor ? this.kbCursor.kind : rows[0].kind;
      const est = this._rowH[kind === "torrent" ? "torrent" : kind === "group" ? "group" : "member"] ||
        ROW_WIN_EST_H[kind === "torrent" ? "torrent" : "group"] || 44;
      const per = Math.max(1, Math.floor((this._winViewH || window.innerHeight) / est));
      this._kbMove(dir * per);
    },
    /* 列表行可见下界(W4 几何走查产出, 计划 26-10-03-0917): 停靠面板开着时它 sticky 吸在视口底
     * (收起态只剩头部条也一样), 底部一段列表行被面板盖住 —— 行可见下界不再是 window.innerHeight,
     * 而是面板顶缘(getBoundingClientRect().top 实测, 滚到文档底面板落回文档流时该值自然上移)
     * 减去 dock 的 8px 呼吸距。关闭(面板不在 DOM)或窄屏全屏态(D3, position:fixed —— 列表整幅被
     * 覆盖, 没有"部分可见"可言, 也避免 top 内插出退化区间)回落整窗高; fixed 判定走计算样式,
     * 断点单点在各皮肤 CSS 的 @media(max-width:900px), JS 不复制断点数。 */
    _kbViewBottom() {
      let bot = window.innerHeight;
      if (this.drawer.open) {
        const panel = document.querySelector(".drawer-dock > .drawer");
        // 出入过渡在途: 面板顶缘的 DOM 实量是高度插值中间值, 读登记的落定顶缘(drawer.js 钩子写入);
        // 入场动画中切走视图时面板随视图卸载、leave 钩子不点火, 登记值悬空 —— 面板已不在 DOM 即作废
        if (this._drawerAnimTop) {
          if (panel) return Math.min(bot, this._drawerAnimTop - 8);
          this._drawerAnimTop = 0;
          return bot;
        }
        if (panel && getComputedStyle(panel).position !== "fixed") {
          bot = Math.min(bot, panel.getBoundingClientRect().top - 8);
        }
      }
      return bot;
    },
    /* 滚动进视口: 目标已可见则不动(避免每次按键都跳)。渲染行用 getBoundingClientRect 差值;
     * 窗口化未渲染行用 _rowWindow 前缀和换算 y(计划 W2; 禁 scrollIntoView, 见文件头)。 */
    _kbScrollRowIntoView(rows, idx) {
      this.$nextTick(() => {
        const r = rows[idx];
        if (!r) return;
        const sel = r.kind === "group" || r.kind === "show" || r.kind === "ep"
          ? `[data-key="${CSS.escape(r.id)}"]`
          : `[data-hash="${CSS.escape(r.id)}"]`;
        const el = document.querySelector(sel);
        const headH = this._headH || 0;
        const vBot = this._kbViewBottom();  // 面板开着时下界让位面板顶缘(W4 几何走查)
        if (el) {
          const rect = el.getBoundingClientRect();
          if (rect.top < headH + 4) window.scrollBy(0, rect.top - headH - 8);
          else if (rect.bottom > vBot - 4) window.scrollBy(0, rect.bottom - vBot + 8);
          return;
        }
        // 窗口化把该行折叠了: 用前缀和算它的文档 y。前缀和与当前列表不同源(长度不符)则放弃
        // 本次滚动 —— 宁可暂时看不见, 也不能滚到错位处(P1-2 的退避口径)。
        const kind = r.kind === "torrent" ? "torrent" : r.kind === "group" ? "group" : null;
        const pre = kind && this._rowPre && this._rowPre[kind];
        if (!pre || pre.length !== rows.length + 1) return;
        const y = pre[idx] + (this._winTop[kind] || 0);
        const h = pre[idx + 1] - pre[idx];
        if (y < window.scrollY + headH + 4) window.scrollTo(0, y - headH - 8);
        else if (y + h > window.scrollY + vBot - 4) window.scrollTo(0, y + h - vBot + 8);
      });
    },
    /* 显式打开路径的行让位(2026-10-03 报障: 双击列表最后几行, 停靠面板一开把被点行盖住) ——
     * W4 下界单点只接了键盘跟随, drawer.js openTorrentDrawer(双击/右键/Enter/Alt+数字 共用
     * 的显式打开)挂上状态后调本方法一次补让位。面板 DOM 随 open 状态 v-if 挂载, 同帧还量不到
     * 面板 —— nextTick 后再测; 目标行下缘低于可视下界才 scrollBy, 本来可见就不动(不抢用户的
     * 滚轮位置); 行不在 DOM(窗口化折叠)静默放弃, 滚动位置宁可不动也不猜(P1-2 退避口径)。 */
    _kbRevealRow(hash) {
      this.$nextTick(() => {
        if (!this.drawer.open) return;
        const el = document.querySelector(`[data-hash="${CSS.escape(hash)}"]`);
        if (!el) return;
        const rect = el.getBoundingClientRect();
        const vBot = this._kbViewBottom();  // 面板开着时下界 = 面板顶缘(W4 单点); 关闭/窄屏全屏态回落整窗高
        if (rect.bottom > vBot - 4) window.scrollBy(0, rect.bottom - vBot + 8);
      });
    },
    /* ---------------- W2: 展开 / 收起 / 打开 ---------------- */
    _kbParseEpId(id) {
      const parts = String(id).split("|");
      if (parts.length < 3) return null;
      return { showKey: parts[0], season: parts[1] === "~" ? null : Number(parts[1]), epKeyStr: parts.slice(2).join("|") };
    },
    _kbExpandRow() {
      const c = this.kbCursor;
      if (!c) return;
      if (c.kind === "group") {
        if (this.expandedKey !== c.id) {
          this.expandedKey = c.id;
          this.selAnchorGroup = c.id;  // 展开的组作为 Shift 多选默认起点(与 toggleExpand 同口径)
        }
        return;
      }
      if (c.kind === "show") {
        if (!this.expandedShows.includes(c.id)) this.expandedShows.push(c.id);
        return;
      }
      if (c.kind === "ep") {
        const p = this._kbParseEpId(c.id);
        if (p && this.expandedShowEp !== c.id) this.expandedShowEp = c.id;
      }
    },
    _kbCollapseRow() {
      const c = this.kbCursor;
      if (!c) return;
      if (c.kind === "group") {
        if (this.expandedKey === c.id) this.expandedKey = null;
        return;
      }
      if (c.kind === "show") {
        const i = this.expandedShows.indexOf(c.id);
        if (i >= 0) this.expandedShows.splice(i, 1);
        return;
      }
      if (c.kind === "ep" && this.expandedShowEp === c.id) this.expandedShowEp = null;
    },
    _kbOpenRow() {
      const c = this.kbCursor;
      if (!c) {
        this._kbHint();
        return;
      }
      if (c.kind === "group" || c.kind === "show" || c.kind === "ep") {
        // 组行/剧行/集行: 展开明细(与鼠标左键同语义, 0822 B9); 已展开则收起
        const open = c.kind === "group" ? this.expandedKey === c.id
          : c.kind === "show" ? this.expandedShows.includes(c.id)
            : this.expandedShowEp === c.id;
        if (open) this._kbCollapseRow();
        else this._kbExpandRow();
        return;
      }
      // 种子行: 详情面板。D2 拍板(计划 26-10-03-0917 §05): 面板已开时 Enter 仅跟随不关面板 ——
      // openTorrentDrawer 即换目标打开(不走 close), 关面板只走 Esc 与关闭钮
      this.openTorrentDrawer(c.id);
    },
    /* Alt+1~5 双态(方案A W2, §2.2): 面板关 = 开面板并定位该页签; 面板开 = 切页签(现行为)。
     * W3 收起态(半开)视同开态先展开再切页签 —— 页签在收起态不可见, 切了等于没切。
     * "开态"只对种子形态(kind=seed)成立: 流量形态(全局/分组流量图, 26-10-05 三挂点并入抽屉)
     * 的抽屉 hash 恒空 —— 直接走切页签会把空 hash 打进 /api/torrents//trackers 等端点(404,
     * toast "tracker/peer 列表获取失败"), Alt+1 又因流量形态 tab 恒为 general 早退(按了没反应)。
     * 流量形态视同关态: 解析目标后 openTorrentDrawer 整体重建为种子形态并落在该页签。
     * 目标解析: 光标行(kind=torrent)优先, 其次单选种子(_kbSingleHash, 选中恰一个 hash);
     * 非种子页(停靠落点 .drawer-dock 只在种子视图)或解析不出目标时 toast 提示后忽略 —— 不猜目标。
     * drawer 作用域条目已清空(§3.2), 四条改 list 作用域由此单点分流双态。 */
    _kbDrawerTab(tab) {
      if (this.page !== "groups" || this.viewMode !== "torrents") {
        this.toast("详情面板只在种子页可用", "info", 2500);
        return;
      }
      // 流量页签受功能门控: 页签按钮 v-if=qbTrafficOn 不渲染, 切到隐形页签 = 卡在一个没有
      // 按钮可切回的页(与 openTorrentDrawer 的 initialTab 归一同一口径), 未启用时提示后忽略
      if (tab === "traffic" && !this.qbTrafficOn) {
        this.toast("qB 口径流量图未启用", "info", 2500);
        return;
      }
      if (this.drawer.open && this.drawer.kind === "seed") {
        if (this.drawer.collapsed) this.toggleDrawerCollapse();  // W3: 收起态先展开(Alt+N 本就要看该页签)
        this.drawerTab(tab);  // 开态: 切页签(现行为)
        return;
      }
      // 面板关着或开着流量形态: 都走"开面板并定位该页签"(流量形态由 openTorrentDrawer 换形)
      const c = this.kbCursor;
      const hash = c && c.kind === "torrent" ? c.id : this._kbSingleHash();
      if (!hash) {
        this._kbHint();
        return;
      }
      this.drawerLastTab = tab;      // openTorrentDrawer 以 drawerLastTab 为初始页签
      this.persistDrawerTab();       // 与 drawerTab 切页同口径(下一个种子默认停在相同页签)
      this.openTorrentDrawer(hash);
    },
    /* ---------------- W2/W3: 选择与目标解析 ---------------- */
    _kbHint() {
      this.toast("先点选一行, 或用 ↑↓ / Home / End 定位目标(空列表无动作)", "info", 2500);
    },
    /* 追剧页与 _kbRows 同序的单元链(剧单元 + 展开的集单元), 供 _toggleUnit/_extendUnit */
    _kbShowUnits() {
      const out = [];
      for (const s of this.decoratedShows) {
        out.push({ id: "show|" + s.key, hashes: this._showHashes(s) });
        if (this.expandedShows.includes(s.key)) {
          for (const sn of s.seasons) {
            for (const e of sn.episodes) {
              out.push({ id: this.showEpRowId(s.key, sn.season, e.epKeyStr), hashes: this.memberHashesOf(e.members) });
            }
          }
        }
      }
      return out;
    },
    _kbUnitOf(c) {
      if (c.kind !== "show" && c.kind !== "ep") return null;
      const want = c.kind === "show" ? "show|" + c.id : c.id;
      return this._kbShowUnits().find((u) => u.id === want) || null;
    },
    _kbToggleSelect() {
      const c = this.kbCursor;
      if (!c) {
        this._kbHint();
        return;
      }
      if (c.kind === "group") {
        const g = this._findGroup(c.id);
        if (g) this.toggleGroupSel(g);
        return;
      }
      if (c.kind === "torrent") {
        this.toggleMemberSel({ hash: c.id });
        return;
      }
      this._toggleUnit(this._kbUnitOf(c));  // 剧/集单元: 整单元切换(与鼠标 Ctrl+点击同语义)
    },
    /* Shift 手势原点(计划 26-10-02-0608 W3): 首次 Shift 扩展前, 若当前上下文没有有效起点,
     * 以当前光标落起点。**必须在 _kbMove 之前**调用 —— 否则光标已移动, 区间会塌成单行(G2)。
     * 已有有效起点(点击 / Ctrl 点击 / 上次手势落定)一律不动 —— 保证"同一起点多次 Shift 扩展"
     * (法则 2)。光标为 null 时不落, 由 _selAnchor 最后兜底列表首行。 */
    _selSeedAnchorFromCursor() {
      const ctx = this._selContext();
      if (!ctx) return;
      const field = this._selAnchorField(ctx.kind);
      if (ctx.ids.includes(this[field])) return;
      const fromCursor = this._selCursorId(ctx.kind);
      if (fromCursor !== null && ctx.ids.includes(fromCursor)) this[field] = fromCursor;
    },
    _kbExtend(delta) {
      this._selSeedAnchorFromCursor();  // 先落起点(手势原点), 再移动光标 —— 顺序不可换(否则区间塌成单行)
      this._kbMove(delta);  // 移动光标, 再把锚点到新光标整段并入选择(锚点语义沿用既有实现)
      const c = this.kbCursor;
      if (!c) return;
      if (c.kind === "group") {
        this.shiftGroupSel({ key: c.id });
        return;
      }
      if (c.kind === "torrent") {
        this.shiftTorrentSel({ hash: c.id });
        return;
      }
      const units = this._kbShowUnits();
      this._extendUnit(units.find((u) => u.id === (c.kind === "show" ? "show|" + c.id : c.id)), units);
    },
    _kbSelectAll() {
      if (this.viewMode === "torrents") {
        this.selGroups = [];
        this.selAnchorGroup = null;
        this.selMembers = this.filteredTorrents.map((m) => m.hash);
        return;
      }
      if (this.viewMode === "shows") {
        const hashes = [];
        for (const u of this._kbShowUnits()) hashes.push(...u.hashes);
        this.selGroups = [];
        this.selAnchorGroup = null;
        this.selMembers = [...new Set(hashes)];
        return;
      }
      this.selMembers = [];  // FX-11: 两类选择口径互斥
      this.selAnchorMember = null;
      this.selGroups = this.filteredGroups.map((g) => g.key);
    },
    /* 目标解析(计划 W3): 有选中走选中集合(_bulkTargets 同口径), 无选中用光标行;
     * 虚拟组行(未归组命中)无组 key, 转为单种子命令(与 _bulkTargets 同处理)。 */
    _kbTargets() {
      if (this.selGroups.length || this.selMembers.length) return this._bulkTargets();
      const c = this.kbCursor;
      if (!c) return { groupKeys: [], memberHashes: [] };
      if (c.kind === "group") {
        const g = this._findGroup(c.id);
        if (!g) return { groupKeys: [], memberHashes: [] };
        if (g.virtual) return { groupKeys: [], memberHashes: g.members[0] ? [g.members[0].hash] : [] };
        return { groupKeys: [c.id], memberHashes: [] };
      }
      if (c.kind === "torrent") return { groupKeys: [], memberHashes: [c.id] };
      const unit = this._kbUnitOf(c);
      return { groupKeys: [], memberHashes: unit ? [...new Set(unit.hashes)] : [] };
    },
    _kbTargetText(t) {
      const n = t.groupKeys.length + t.memberHashes.length;
      if (t.groupKeys.length === 1 && !t.memberHashes.length) return "整组";
      if (t.memberHashes.length === 1 && !t.groupKeys.length) return "该种子";
      return `${n} 个目标`;
    },
    /* ---------------- W4: 一级动作(危险档先确认; S3 起鼠标路径同文案确认, 计划 26-10-05-0314) ---------------- */
    async _kbAct(action) {
      const t = this._kbTargets();
      if (!t.groupKeys.length && !t.memberHashes.length) {
        this._kbHint();
        return;
      }
      const what = this._kbTargetText(t);
      if (action === "recheck") {
        /* 确认框文案与调用形态单点在 commands.js _recheckConfirm(S3 抽出共用), 本路径的
         * what 文案/时序/取消语义与抽出前逐位一致。 */
        const ok = await this._recheckConfirm(what);
        if (!ok) return;
      } else if (action === "reannounce") {
        const ok = await this.confirmDialog("强制汇报",
          `将向 tracker 强制汇报${what}。频繁误触可能触发站点限流或警告。`, { okText: "确定" });
        if (!ok) return;
      }
      return this._actCore(action, { keys: t.groupKeys, hashes: t.memberHashes });
    },
    /* 删除: 与批量删除(bulkDelete)同一条 _deleteFlow 链(确认框 + HR 风险点名 + 汇报前置),
     * 键盘双入口之二(D8 默认键 Shift+D 与本 Delete 直连, 注册表外, §08 决策 v4)。 */
    async _kbDelete() {
      const t = this._kbTargets();
      if (!t.groupKeys.length && !t.memberHashes.length) {
        this._kbHint();
        return;
      }
      const parts = [];
      if (t.groupKeys.length) parts.push(`${t.groupKeys.length} 个${this.l10nGroup}`);
      if (t.memberHashes.length) parts.push(`${t.memberHashes.length} 个种子`);
      const countText = parts.join("、");
      const seen = new Set();  // 种子数(组展开去重)与批量删除同口径
      for (const k of t.groupKeys) {
        const g = this._findGroup(k);
        if (!g) continue;
        if (g.virtual) {
          if (g.members[0]) seen.add(g.members[0].hash);
        } else {
          for (const m of g.members || []) seen.add(m.hash);
        }
      }
      for (const h of t.memberHashes) seen.add(h);
      await this._deleteFlow({
        keys: t.groupKeys,
        hashes: t.memberHashes,
        title: `删除 ${countText}`,
        body: `将删除选中目标内的全部种子, 共 ${seen.size} 个。建议删除前先向 tracker 汇报, 避免留下未汇报的 H&R 记录。`,
        countText,
        label: countText,
      });
    },
    _kbOpenDrawer() {
      const c = this.kbCursor;
      if (!c) {
        this._kbHint();
        return;
      }
      if (c.kind === "torrent") {
        this.openTorrentDrawer(c.id);
        return;
      }
      if (c.kind === "group") {
        const g = this._findGroup(c.id);
        const h = g && g.members && g.members[0] ? g.members[0].hash : "";
        if (h) this.openTorrentDrawer(h);
      }
    },
    _kbMeta() {
      if (this.selGroups.length || this.selMembers.length) {
        this.openMetaDialog(null);  // 有选中传 null = 整个选中集合(与批量动作同口径)
        return;
      }
      const c = this.kbCursor;
      if (!c) {
        this._kbHint();
        return;
      }
      if (c.kind === "torrent") {
        this.openMetaDialog(c.id);
        return;
      }
      const unit = this._kbUnitOf(c);
      if (unit && unit.hashes.length) {
        this.openMetaDialog({ groupKeys: [], memberHashes: [...new Set(unit.hashes)] });
        return;
      }
      const g = c.kind === "group" ? this._findGroup(c.id) : null;
      if (g && !g.virtual) this.openMetaDialog({ groupKeys: [c.id], memberHashes: [] });
    },
    _kbOpenFolder() {
      const c = this.kbCursor;
      if (!c) {
        this._kbHint();
        return;
      }
      if (c.kind === "group") {
        const g = this._findGroup(c.id);
        if (g && !g.virtual) this.openTargetPath("group", c.id);
        return;
      }
      if (c.kind === "torrent") this.openTargetPath("torrent", c.id);
    },
    _kbFocusSearch() {
      const el = this.$refs.searchInput;
      if (el) {
        el.focus();
        el.select();
      }
    },
    /* ---------------- W5: 单目标动作的键盘目标解析 ----------------
     * E/F/I 组的编辑/复制/导出/队列族都是**单种子**动作(右键菜单只在单目标上提供):
     * 目标解析要求恰有一个 hash —— 多选/整组/剧集单元一律提示, 不猜第一个(静默错目标
     * 比不动作更糟)。选中集合走 _kbTargets 同一口径, 无选中用光标行。 */
    _kbSingleHash() {
      const t = this._kbTargets();
      if (t.groupKeys.length || t.memberHashes.length !== 1) return "";
      return t.memberHashes[0];
    },
    /* 单目标编辑/复制族: 既有方法读 menu.hash(与右键菜单同一入口), 这里只做解析与挂载 */
    _kbEditAct(fn, arg) {
      const h = this._kbSingleHash();
      if (!h) {
        this._kbHint();
        return;
      }
      this.menu.hash = h;
      if (arg === undefined) return this[fn]();
      return this[fn](arg);
    },
    /* 单目标种子命令族(队列/TMM/强制开始/超级做种): 复用 torrentCmd 回执链(右键菜单同链) */
    _kbTorrentCmd(action, makeBody, okText) {
      const h = this._kbSingleHash();
      if (!h) {
        this._kbHint();
        return;
      }
      this.menu.hash = h;
      return this.torrentCmd(action, makeBody(), okText);
    },
    _kbTorrentToggle(action, field, label) {
      const h = this._kbSingleHash();
      if (!h) {
        this._kbHint();
        return;
      }
      const m = this.memberByHash.get(h) || {};
      this.menu.hash = h;
      return this.torrentCmd(action, { enable: !m[field] }, `${m[field] ? "关闭" : "开启"}${label}`);
    },
    /* 反选当前视图(空位动作, 默认不绑键): 三视图各自的全集做差; FX-11 两类选择口径互斥 */
    _kbInvertSel() {
      if (this.viewMode === "torrents") {
        const sel = new Set(this.selMembers);
        this.selGroups = [];
        this.selAnchorGroup = null;
        this.selMembers = this.filteredTorrents.map((m) => m.hash).filter((h) => !sel.has(h));
        return;
      }
      if (this.viewMode === "shows") {
        const sel = new Set(this.selMembers);
        const all = new Set();
        for (const u of this._kbShowUnits()) for (const h of u.hashes) all.add(h);
        this.selGroups = [];
        this.selAnchorGroup = null;
        this.selMembers = [...all].filter((h) => !sel.has(h));
        return;
      }
      const sel = new Set(this.selGroups);
      this.selMembers = [];  // FX-11: 两类选择口径互斥
      this.selAnchorMember = null;
      this.selGroups = this.filteredGroups.map((g) => g.key).filter((k) => !sel.has(k));
    },
    /* ---------------- W6: 服务端键位装载 ----------------
     * startPolling 是两条鉴权放行路径(密钥验证/本机免鉴权)的唯一汇合点, 键位真值在那里拉;
     * 失败不阻塞主流程(默认表可用), 只提示。拉完/换稿后必须失效 _kbTableCache(引擎缓存)。 */
    async _kbReloadKeys(quiet = false) {
      const ok = await window.AQB_KEYS.reload(this.token);
      this._kbTableCache = null;
      if (!ok && !quiet) this.toast("快捷键配置加载失败, 已用默认键位", "warn");
      return ok;
    },
    /* ---------------- W6: 帮助浮层(H 组, Shift+Slash) ---------------- */
    kbOpenHelp() {
      this.kbHelpOpen = true;
    },
    kbGoSettings() {
      this.kbHelpOpen = false;
      this.openSettings();
      this.hubGo("keys");
    },
    /* ---------------- W6: 自定义面板(设置页「快捷键」分区) ----------------
     * 面板语义(计划 §5.2): 改动先本地生效(即时试用) → 「保存」PUT 落盘; 离开未保存 → 提示。
     * 草稿 = kbDraft(工作副本), 基准 = kbSaved(最近保存的服务端真值); 每次改稿同步进
     * AQB_KEYS(引擎即时生效)并失效 _kbTableCache。 */
    kbPanelEnter() {
      this.kbRecId = "";
      this.kbConflict = null;
      this.kbKeysLoading = true;
      return this._kbReloadKeys(true).then(() => {
        this.kbSaved = JSON.parse(JSON.stringify(window.AQB_KEYS.load()));
        this.kbDraft = JSON.parse(JSON.stringify(this.kbSaved));
        this.kbKeysLoading = false;
      });
    },
    /* 面板离开守卫(config_hub hubGo/hubBack 调): 未保存先确认; 确认后回滚再继续导航 */
    kbGuardLeave(target) {
      if (this.hub.view !== "keys" || target === "keys" || !this.kbDirty()) return false;
      this.confirmDialog("快捷键改动还未保存",
        "离开将放弃本次试用的改动; 点「保存」才会写入服务端(所有浏览器共享)。",
        { okText: "放弃并离开", cancelText: "留在此页" }).then((ok) => {
        if (!ok) return;
        this.kbDraftRevert();
        if (target === "hub") this.hubBack();
        else {
          this.hubCloseHelp();
          this.hub.view = target;
          window.scrollTo({ top: 0 });
        }
      });
      return true;
    },
    kbDirty() {
      if (!this.kbDraft || !this.kbSaved) return false;
      return JSON.stringify(this.kbDraft) !== JSON.stringify(this.kbSaved);
    },
    /* 注册表按 group 分组(保持声明序, 面板与帮助浮层共用) */
    kbGroups() {
      const out = [];
      for (const it of AQB_SHORTCUT_DEFS) if (!out.includes(it.group)) out.push(it.group);
      return out;
    },
    kbEntriesOf(group) {
      return AQB_SHORTCUT_DEFS.filter((it) => it.group === group);
    },
    /* 条目当前生效键位(草稿 ⊕ 模板基准): 与引擎 _kbTable 同口径, 空串 = 显式禁用 */
    kbSerialOf(item) {
      return kbSerialWithDraft(item, this.kbDraft);
    },
    kbIsOverridden(item) {
      return !!(this.kbDraft && this.kbDraft.overrides && Object.prototype.hasOwnProperty.call(this.kbDraft.overrides, item.id));
    },
    /* danger 条目的确认框标注: 三条确认框兜底动作标注"(有确认框)", 其余(超级做种)只标 ⚠(§08) */
    kbHasConfirm(item) {
      return ["act-delete", "act-recheck", "act-reannounce"].includes(item.id);
    },
    _kbApplyOverrides(overrides) {
      this.kbDraft = {
        schema_version: 1,
        template: (this.kbDraft && this.kbDraft.template) || "aqb-default",
        overrides,
      };
      window.AQB_KEYS.apply(JSON.parse(JSON.stringify(this.kbDraft)));  // 即时试用(引擎可见)
      this._kbTableCache = null;
    },
    /* 落一条键位: 回到模板默认即删掉 override(草稿最小化, 重置语义与之合一);
     * danger 条目绑裸键提示但允许(§08 v4: 确认框兜底)。 */
    _kbCommitSerial(item, serial) {
      const ov = { ...((this.kbDraft && this.kbDraft.overrides) || {}) };
      if (serial === item.def) delete ov[item.id];
      else ov[item.id] = serial;
      this._kbApplyOverrides(ov);
      if (item.danger && serial && !serial.includes("+")) {
        this.toast(`「${item.label}」已绑定为裸键 —— 该动作是危险操作, 触发时有确认框兜底`, "warn", 5000);
      }
    },
    /* ---------------- W6: 录制器(VS Code 按下即录模式, §3.3/§5.2) ----------------
     * 捕获段(capture)监听: 录制态按键 preventDefault + stopPropagation, 引擎/退栈链/hubOnKey
     * 都收不到(§5.2 "引擎屏蔽层保证录制态不触发其它动作")。纯修饰键拒收; Esc 取消;
     * 黑名单当场拒绑; 冲突进三选一(交换/覆盖对方置空/取消)。 */
    kbRecord(id) {
      if (this.kbRecId === id) {
        this.kbRecordCancel();
        return;
      }
      this.kbConflict = null;
      this.kbRecId = id;
      if (this._kbRecHandler) document.removeEventListener("keydown", this._kbRecHandler, true);
      this._kbRecHandler = (e) => this._kbOnRecordKey(e);
      document.addEventListener("keydown", this._kbRecHandler, true);
    },
    kbRecordCancel() {
      this.kbRecId = "";
      if (this._kbRecHandler) {
        document.removeEventListener("keydown", this._kbRecHandler, true);
        this._kbRecHandler = null;
      }
    },
    _kbOnRecordKey(e) {
      e.preventDefault();
      e.stopPropagation();
      if (e.isComposing || e.keyCode === 229) return;  // IME 组合期不判定(§3.4)
      if (KB_MODIFIER_CODES.has(e.code)) return;       // 纯修饰键拒收(§3.3)
      if (e.key === "Escape") {
        this.kbRecordCancel();
        return;
      }
      if (e.repeat) return;
      const serial = kbSerializeEvent(e);
      const item = AQB_SHORTCUT_DEFS.find((it) => it.id === this.kbRecId);
      this.kbRecordCancel();
      if (!item) return;
      if (kbInBlacklist(serial)) {
        this.toast(`浏览器保留该组合键(Ctrl+W/T/N/Q 等), 无法绑定: ${kbDisplayName(serial)}`, "error", 6000);
        return;
      }
      const other = AQB_SHORTCUT_DEFS.find((it) => it.id !== item.id && !it.fixed && kbSerialWithDraft(it, this.kbDraft) === serial);
      if (other) {
        this.kbConflict = { id: item.id, serial, other: other.id, otherLabel: other.label };
        return;
      }
      this._kbCommitSerial(item, serial);
    },
    /* 冲突三选一(§5.2): 交换 = 对方拿我原来的键位; 覆盖 = 对方置空(显式禁用); 取消 = 不动 */
    kbConflictResolve(mode) {
      const c = this.kbConflict;
      if (!c) return;
      const item = AQB_SHORTCUT_DEFS.find((it) => it.id === c.id);
      const other = AQB_SHORTCUT_DEFS.find((it) => it.id === c.other);
      this.kbConflict = null;
      if (!item || !other) return;
      const ov = { ...((this.kbDraft && this.kbDraft.overrides) || {}) };
      if (mode === "swap") {
        const mine = kbSerialWithDraft(item, this.kbDraft);
        ov[item.id] = c.serial;
        if (mine === other.def) delete ov[other.id];
        else ov[other.id] = mine;
      } else if (mode === "steal") {
        ov[item.id] = c.serial;
        ov[other.id] = "";  // 对方置空 = 显式禁用(语义保留, 不能当缺省丢)
      } else {
        return;
      }
      this._kbApplyOverrides(ov);
    },
    kbDisableRow(item) {
      this._kbCommitSerial(item, "");  // 空串 = 显式禁用该动作(计划 §5.2)
    },
    kbResetRow(item) {
      this._kbCommitSerial(item, item.def);
    },
    kbResetAll() {
      this.kbRecordCancel();
      this.kbConflict = null;
      this._kbApplyOverrides({});  // 全部重置 = 清空派生, 回到纯模板(§4.7)
    },
    async kbSaveKeys() {
      const doc = JSON.parse(JSON.stringify(this.kbDraft));
      const r = await window.AQB_KEYS.save(doc, this.token);
      if (!r.ok) {
        this.toast("快捷键保存失败: " + r.error + "(本地已回滚)", "error", 8000);
        this.kbDraftRevert();
        return;
      }
      this.kbSaved = JSON.parse(JSON.stringify(doc));
      window.AQB_KEYS.apply(JSON.parse(JSON.stringify(doc)));
      this._kbTableCache = null;
      this.toast("快捷键已保存(其它浏览器/标签刷新后生效)", "ok", 3500);
    },
    kbDraftRevert() {
      this.kbRecordCancel();
      this.kbConflict = null;
      const base = this.kbSaved || AQB_KEYS_DEFAULT();
      this.kbDraft = JSON.parse(JSON.stringify(base));
      window.AQB_KEYS.apply(JSON.parse(JSON.stringify(base)));  // 回滚到最近保存的服务端真值
      this._kbTableCache = null;
    },
    /* 键位显示名(物理 code -> 人类键名, §3.3): 录制/面板/帮助浮层共用 */
    kbDisplayName(serial) {
      return kbDisplayName(serial);
    },
  },
};
