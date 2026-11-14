/* lifecycle.js — 根组件生命周期(created/mounted/unmounted/updated): W2b 自 app.js 拆出。
 * WARN: 同 state.js: 走根选项展开, 不走 app.mixin —— 否则 hub-field 实例也会跑 mounted
 * (监听器/fetch 双份)。成员逐行原样搬运。 */
/* 通知 · 后端条目合并与补拉(WEBUI 通知 S3) --------------------------------
 * 后端在 /api/errlog 挂了 auto_qb logger 的 WARNING+ 内存环(条目 {seq, ts, level, msg},
 * seq 进程内单调、重启归零)。本段把它并进根组件 _errHistory(S1 数据层, cap 常量
 * ERR_HISTORY_CAP 单点在 ui_feedback.js, 加载序先于本文件):
 *   - boot 全量合并: 密钥验证成功(auth.js bootstrap)/ 本机免鉴权(lifecycle mounted)两条
 *     启动路径各拉一次 after=0, 不计未读(开页即见, 不算"错过");
 *   - 补拉: 60s 定时增量合并(after=已持游标), 面板关闭期每条计未读(对齐 _recordErrorToast
 *     的记账语义); 回包 last < 已持游标 = 后端重启过(seq 归零), 清游标重拉全量;
 *   - 拉取失败一律静默(后端不可达不打扰用户, 下轮补拉自愈), 零持久化、零新配置键。 */
const ERR_POLL_INTERVAL_MS = 60000;  // 补拉节拍(写常量; 不进配置 —— 纯前端体验参数)

/* 键位提示常驻开关的本机偏好键(计划 26-11-14-0041 S5/W2, D6): 沿用既有 autoqb.ui.* 口径,
 * 不新造通道。"1" = 常驻(body.kbd-persist, 全落点显示) / 其余 = 仅按住反引号显影
 * (body.kbd-reveal)。两态互斥, 共用共享 CSS 的同一条显示规则 —— 这里只存一个开关值。 */
const KBD_PERSIST_KEY = "autoqb.ui.kbdPersist";

/* 密钥字段名与空值占位(本文件单点): 本文件只在本机免鉴权分支采纳一次本地旧密钥。
 * (1) 空值占位: token 字段**恒为字符串** —— 导出下载会把它无条件插值进 Bearer 头, 置 null 会拼出
 *    "Bearer null"(与「不带密钥」不是一回事);
 * (2) 属性名走常量: 工作区写入判据会把「凭据族字段名 + 赋值」的行误报成凭据字面量(误判实例与处置
 *    见 memory-bank/pitfalls/ops/agent-write-guard-secret-false-positive.md) —— 走常量后语义不变、
 *    该行不再带那种字面形态; 本等价形态经属主授权采用(2026-10-16), 回潮即触发守阵。 */
const AQB_TOKEN_FIELD = "token";
const AQB_BLANK = "";

/* 后端日志级别 -> 前端 kind(环只收 WARNING+, 不存在更低档) */
function _errLevelKind(level) {
  return level === "WARNING" ? "warn" : "error";
}

/* 后端 epoch 秒 -> 完整 HH:MM:SS(通知要看秒位, 不走 fmtTime 的日期省略口径) */
function _errBackendClock(sec) {
  const d = new Date((sec || 0) * 1000);
  const p = (n) => String(n).padStart(2, "0");
  return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}

/* 后端重启判定(纯函数, 探针真跑): 回包 last 低于已持游标 —— seq 进程内只增,
 * 唯一可能倒退的路径是后端重启归零; cursor 0 = 尚无游标, 不判重启。 */
function _errlogReseed(last, cursor) {
  return cursor > 0 && last < cursor;
}

window.AQB_LIFECYCLE = {
  created() {
    /* P1-2 窗口化的**非响应式**缓存: 刻意不放进 data —— 容器偏移与签名每轮都会写,
     * 放进 data 会让它参与依赖追踪, 每次写入都额外触发一轮重渲染(白付一次整表 patch)。
     * 窗口重算真正需要的响应式输入只有 _winScrollY / _winViewH / _winResize / _rowH。 */
    this._winTop = { torrent: 0, group: 0, member: 0 };        // 容器顶边相对文档的偏移
    this._winTopSig = { torrent: "", group: "", member: "" };
    this._rowHSig = { torrent: "", group: "", member: "" };    // 行高签名(列集合/窗口宽变化才重量)
    /* 逐行实测高度 {kind:hash -> px}: 行高**本来就不齐** —— 带 H&R 要求的行多渲染一行
     * ("22时00分 / 3天12时"), 实测 3000 种子里 27% 是 65.4px、其余 43.7px。按"等高"算占位
     * 会在几千行上累积成**上百像素**的漂移(滚到底够不着 / 滚动条长度不对), 必须逐行记。 */
    this._rowHs = {};
    // 该 kind 的首访窗口行是否已实测(千级以下 = 全表量齐; 千级以上只会量到视口内那批, 随滚动补齐)
    this._winMeasured = { torrent: false, group: false, member: false };
    /* 行间距(px)**实测**缓存: 三个容器的真实 gap 不同(atlas .group-table 6px / prism 5px /
     * 成员容器 .detail 是块级容器 = 0), 硬编码会让占位总高失真(见文件头 BUG-1 注释)。 */
    this._winGap = {};
    this._winRaf = 0;      // 滚动合帧句柄
    this._winListening = false;
    // 键盘快捷键(计划 26-09-28-0354 W1): 生效键表缓存(非响应式, W6 改键时失效)与
    // _rowWindow 前缀和留存(光标滚动进视口用, 见 columns.js)都是纯缓存, 刻意不进 data
    this._kbTableCache = null;
    this._rowPre = {};
    // 通知 S3(非响应式: 游标与定时器句柄无渲染依赖, 刻意不进 data —— 同上 P1-2 口径)
    this._errLogCursor = 0;  // /api/errlog 已持游标(环内最大已拉 seq; 后端重启时清零重拉)
    this._errPollTimer = 0;  // 60s 补拉定时器句柄(unmounted 撤除防热重载堆叠)
    // 键位提示显影态(计划 26-11-14-0041 S1/W1): body.kbd-reveal 的有无。纯显示态缓存,
    // 刻意不进 data —— 每次 keydown 都要写它, 进 data 会平白触发整表重渲染(P1-2 口径)。
    this._kbdRevealOn = false;
    // 键位提示常驻态(S5/W2 单开关): body.kbd-persist 的有无。同上刻意不进 data —— 状态
    // 显示全交给 CSS(body.kbd-persist 驱动开关高亮), 切换零重绘(D4); 初值由 mounted 从本机
    // 偏好恢复(见 _kbdPersistStored)。
    this._kbdPersistOn = false;
  },
  async mounted() {
    /* P1-2: 视口高度 + 页面滚动监听(被动 + rAF 合帧, 滚动本身不做任何布局读取) */
    this._winViewH = window.innerHeight;
    window.addEventListener("scroll", this._onWinScroll, { passive: true });
    window.addEventListener("resize", this._onWinResize);
    this._winListening = true;
    // 点击页面空白处: 关闭右键菜单与列选择器(两者都是临时浮层)
    // R4 清池(row117): 匿名处理器提为实例字段 —— unmounted 里 removeEventListener 需要同一
    // 引用, 匿名函数永远摘不掉(热重载后旧句柄堆叠, 操作已死实例)。下面五支监听同此。
    this._onDocClick = () => {
      this.menu.visible = false;
      this.headMenu.visible = false;   // 表头右键菜单(TBL-05)与右键菜单同层
      this.colMenuOpen = false;
      this.filterMenu = "";
      this.uiMenuOpen = false;  // 顶栏界面切换下拉(与列选择器/筛选器同层的临时浮层)
      this.searchHelpOpen = false;  // 搜索语法浮卡(触发钮自身 @click.stop 已拦截, 点空白 = 收起)
      this.filePrio.visible = false;
      this.drawerMenu.visible = false;  // 抽屉右键菜单(R2 S3): 与右键菜单同层的临时浮层
      // 动效数值面板(R8, plan 26-11-12-1139 §05.7): 非模态浮层同族 —— 点空白收层(面板根
      // @click.stop 已拦截, 与通知面板 .err-panel 同一套口径); 图区右键重开即用
      this.fxPanel.visible = false;
      this.addCatMenu = false;  // 添加种子对话框内浮层: 点空白处统一收起(触发元素自身已 @click.stop 拦截)
      this.addTagMenu = false;
      this.addPathPop = false;
      /* meta 对话框(标签与分类)的分类下拉: 同族浮层, 原本漏在名单外 —— 点对话框别处只靠
       * @focusout(2026-10-03 补)收, 这里补兜底。WARN: 有它才必须给 meta 的字段 label 挂
       * @click.stop —— 否则点 label 走"window click 收层 -> label 转发 click 重开" = 闪烁。 */
      this.metaCatMenu = false;
      this.movePathMenu = false;  // 设定位置对话框(2026-10-13)保存路径下拉: 同族浮层, 与 meta 同套收层口径
      // 通知面板(S4): 非模态浮层同族 —— 点空白收层(面板根与入口钮 .sb-err 都已 @click.stop 拦截)
      this.errPanelOpen = false;
      // FX-08: 限速浮层无遮罩 -> 点空白视为"放弃本次修改"直接收起(与 Esc 同语义)
      if (this.speedOpen) this.closeSpeedDialog();
    };
    window.addEventListener("click", this._onDocClick);
    // Esc: 逐层退栈(FIX-07) —— 确认框/弹窗 -> 抽屉内浮层 -> 历史弹层 -> 抽屉 -> 筛选器下拉/其余弹层(pop) -> 右键菜单 -> 退出搜索框聚焦(仅顶栏搜索框, 2026-11-13) -> 清选择/收展开兜底 -> 清筛选兜底(仅数据页+非输入态, 26-10-01-2108)
    // 收展开兜底档(2026-10-22 起)**顺便把键盘光标退回被收起的父行**, 不再让它悬空指向已卸载的明细行。
    // WARN: 本链与 dialogs.js::escBusy 是同一份浮层名单(后者给 config_hub 的「Esc 返回设置首页」守门),
    //   新增浮层两处同步; config_hub.js::hubOnKey 的 Esc 分支排在本链之后(链上有层时它不动)
    this._onEscKey = (e) => {
      if (e.key !== "Escape") return;
      // 输入元素判据与引擎同式(先取元素后取布尔: 退出搜索框档要拿元素本体比对)
      const inputEl = e.target && e.target.closest &&
        e.target.closest("input, textarea, select, [contenteditable]");
      const inInput = !!inputEl;  // 仅清筛选兜底与退出搜索框档消费(既有分支行为不变)
      if (this.modal.visible) this.resolveModal(false);
      else if (this.addOpen) this.escAddTorrent();  // 添加种子对话框: 先收内部浮层(分类/标签下拉 -> 位置面板), 再关对话框
      else if (this.statsOpen) this.closeStats();  // 统计面板对话框: 与添加对话框同层(先后于确认框)
      else if (this.speedOpen) this.closeSpeedDialog();  // 限速弹窗(SPD-04): 与统计面板同层
      else if (this.mgrOpen) this.closeMgr();  // 分类/标签管理对话框: 与添加对话框同层(内部确认框仍最优先)
      else if (this.metaOpen) this.closeMeta();  // 标签/分类编辑对话框: 与管理对话框同层
      else if (this.moveOpen) this.closeMove();  // 设定位置对话框(2026-10-13): 与 meta 同层
      else if (this.hrsOpen) this.hrsCollapse();  // HR 站点状态全屏覆盖层(计划 26-10-02-1936 阶段2): 对话框层级, 先于清筛选兜底; escBusy 已同步(dialogs.js)
      else if (this.kbFullOpen) this.kbFullClose();  // 键位编辑全屏覆盖层(2026-11-03 改版): 对话框层级, 同 hrsOpen 档; 未保存由 kbFullClose 确认; escBusy 已同步(dialogs_meta.js)
      else if (this.relChain.open) this.relChainClose();  // 路径链浮窗(P2): 浮于抽屉(40)/历史(130)之上, 先于抽屉内浮层与抽屉本身关闭
      else if (this.filePrio.visible) this.filePrio.visible = false;  // 文件优先级小菜单: 抽屉内浮层先于抽屉关闭
      else if (this.drawerMenu.visible) this.drawerMenu.visible = false;  // 抽屉右键菜单(R2 S3): 同为抽屉内浮层
      // 动效数值面板(R8, plan 26-11-12-1139 §05.7): 比抽屉菜单"重"一层(浮于图宿主之上, z-index 90),
      // 后开先关 —— 面板开着按 Esc 只关面板, 再按 Esc 才轮到抽屉(位置紧跟 drawerMenu 之后, §05.7 表)
      else if (this.fxPanel.visible) this.fxPanel.visible = false;
      // 历史流量弹层: 遮罩层(z-index 130)盖在停靠抽屉(80)之上, 与 qB 口径流量图(drawerVisible)
      // 同时存在时它才是视觉上的**最上层** —— 必须先关它, 否则 Esc 会穿过遮罩去关底下被盖住的抽屉
      // (退栈顺序 = 视觉层叠顺序: 弹层 -> 抽屉; 2026-10-06 报障: 两图同开时 Esc 先关错了抽屉)
      else if (this.historyOpen) this.historyOpen = false;
      // 详情抽屉(种子详情 / qB 口径流量图): 确认框优先, 其后于其它浮层。判据用 drawerVisible
      // 而非 drawer.open —— 面板 DOM 随 drawerVisible 退场(非主内容页), 看不见的面板不吃 Esc:
      // 在设置页第一次 Esc 应该做的事是退回设置首页, 而不是关掉一张不在屏幕上的面板
      else if (this.drawerVisible) this.closeDrawer();
      else if (this.headMenu.visible) this.headMenu.visible = false;  // 表头右键菜单(TBL-05)
      else if (this.colMenuOpen) this.colMenuOpen = false;  // 列选择器弹层(pop)
      else if (this.uiMenuOpen) this.uiMenuOpen = false;  // 顶栏界面切换下拉(pop)
      else if (this.searchHelpOpen) this.searchHelpOpen = false;  // 搜索语法浮卡(pop)
      else if (this.kbHelpOpen) this.kbHelpOpen = false;  // 快捷键帮助浮层(W6, H 组 Shift+Slash 打开)
      else if (this.errPanelOpen) this.errPanelOpen = false;  // 通知面板(S4): pop 层, escBusy 已同步
      // 迁移悬停浮窗(plan 26-11-07-2344 S3): pop 层 tooltip, 收卡即短路 —— 该次 Esc 不再往下走。
      // 数据页专属(hover 触发), 设置页不可能在屏, 故不进 dialogs_meta.js::escBusy 名单
      else if (this.relPop.open) this.relPopHideNow();
      else if (this.filterMenu) this.filterMenu = "";  // 筛选器下拉(pop)
      else if (this.menu.visible) this.menu.visible = false;  // 右键菜单: pop 层之后
      /* 退出搜索框聚焦(2026-11-13 报障): 输入态不是浮层, 但浮层名单走空后 Esc 若还压着输入焦点
       * 就是死键 —— 焦点在顶栏搜索框时退焦, 把键位还给列表。搜索词不清(归 clearSearch, 与清筛选
       * 兜底的「搜索词保留」同口径); IME 组词中的 Esc 归输入法(同引擎 §3.4 / hubOnKey 口径,
       * 只取消组词不退焦)。排在清选择兜底之前: 打字中按 Esc 的语境是"离开输入框", 不该顺手动
       * 列表状态 —— 第二次 Esc 才轮到清选择/清筛选。设置页各输入框不接(站点搜索层有自己的
       * Esc 路径 hubOnKey, 清词收层退聚焦), 本档只钉死顶栏搜索框这一个元素。 */
      else if (inInput && !(e.isComposing || e.keyCode === 229) &&
               inputEl === this.$refs.searchInput) {
        inputEl.blur();
      }
      else if (this.selGroups.length || this.selMembers.length) this.clearSelection();  // 兜底: 清除行/组选择(复用现有逻辑)
      /* 兜底: 收起分组展开。**收起不"清光标", 光标退回被收起的父行**(2026-10-22):
       *   明细行随收起一起卸载, 光标却仍指着那个已不在链上的成员 hash —— 虚线框被宿主连坐带走,
       *   观感就是"锚点丢了", 下一次 up/down 还得走无光标回落(_kbViewportRow)重新猜落点。
       *   归位口径与 <- (shortcuts.js::_kbCollapseRow) 一致: 成员行 -> 所属组行。就地赋值不调
       *   引擎内部方法 —— 退栈链自成一体, 不反向依赖快捷键引擎; 父行紧邻被收起的明细块, 本就在
       *   视口内, 无需滚动跟随(也避开禁 scrollIntoView 的红线)。 */
      else if (this.expandedKey) {
        const k = this.expandedKey;
        this.expandedKey = null;
        this.kbCursor = { kind: "group", id: k };
      }
      else if (this.expandedShowEp) {  // 兜底: 收起追剧集展开(与辅种页同构: 版本行 -> 所属集行)
        const k = this.expandedShowEp;
        this.expandedShowEp = null;
        this.kbCursor = { kind: "ep", id: k };
      }
      else if (this.expandedShows.length) {  // 兜底: 收起追剧剧展开(集行 -> 所属剧行)
        // 剧可多支同时展开: 优先退回**光标所在那一支**(注意力所在, 不横跳到别的剧), 否则退回首支
        const c = this.kbCursor;
        const p = c && c.kind === "ep" ? this._kbParseEpId(c.id) : null;
        const k = p && this.expandedShows.includes(p.showKey) ? p.showKey
          : c && c.kind === "show" && this.expandedShows.includes(c.id) ? c.id
            : this.expandedShows[0];
        this.expandedShows = [];
        this.kbCursor = { kind: "show", id: k };
      }
      // 兜底最深一档: 清全部面筛(26-10-01-2108 拍板) —— 仅数据页 + 非输入态 + 无 hrPop 卡;
      // 搜索词不清(归 clearSearch); 触发即 toast 点名, 不静默。门条件缺一不可:
      // page 挡设置页(escBusy 无需同步), inInput 挡搜索框, hrPop 让"收卡"独占该次按键
      else if (this.authOk && this.page === "groups" && !this.hrPop.open && !inInput && this.facetsActive) {
        this.clearFilters();
        this.toast("已清除全部筛选: 搜索词保留", "ok", 2500);
      }
    };
    document.addEventListener("keydown", this._onEscKey);
    // 键盘快捷键引擎(计划 26-09-28-0354 W1): 必须注册在 Esc 退栈链**之后**(注册序 = 触发序);
    // 引擎自身对 Escape 也直接放行, 双保险。句柄存实例, unmounted 撤掉防热重载堆叠。
    this._kbKeyDown = (e) => this._kbOnKeyDown(e);
    document.addEventListener("keydown", this._kbKeyDown);
    // 未保存改动防护(U1-b, 报告 26-10-02-0508): 键盘刷新(F5 / Ctrl+R 族)拦截, 排在快捷键
    // 引擎**之后** —— 引擎不接管这两个键(键位黑名单且不注册), 两条链不打架; 录制器是捕获
    // 阶段 + stopPropagation, 录制态天然先手, 不会误弹守卫框。
    this._cfgGuardKey = (e) => this._cfgOnReloadKey(e);
    document.addEventListener("keydown", this._cfgGuardKey);
    // 键位提示显影链(计划 26-11-14-0041 S1/W1, I4 生命周期闭环): 按住反引号 Backquote 给
    // <body> 加 kbd-reveal class, 松开移除。冒泡阶段注册且排引擎之后, 捕获段录制器
    // _kbOnRecordKey 对所有 keydown 全吞, 天然先手; 再判 kbRecId 双保险。绝不 preventDefault /
    // stopPropagation(I5) —— 引擎的 defaultPrevented 礼仪会让组合键整条动作被跳过。
    this._onKbdRevealDown = (e) => {
      // 每次任意(非反引号) keydown 自愈: Alt+Tab 切窗 / 点进 iframe 丢 keyup 卡住的 class,
      // 下一次按键立即纠正(I4)。不跟踪按键状态; 反引号自身 keydown 不在这里清。
      if (e.code !== "Backquote") {
        this._setKbdReveal(false);
        return;
      }
      // 反引号长按的 repeat 维持现状(不 add 也不清): 约束 1 要求 !repeat 才 add, 但把 repeat
      // 当「其它 keydown」清掉会让按住超过自动重复阈值后键帽消失, 违背「按住显影」语义。
      if (e.repeat) return;
      const reveal = !(e.isComposing || e.keyCode === 229)  // IME 组合期(与 shortcuts_engine.js:47 同式)
        && !this.kbRecId                                    // 录制态避开(state.js:311)
        && !(e.target && e.target.closest &&
          e.target.closest("input, textarea, select, [contenteditable]"));  // 输入态跳过(与 :53 同式): 不吞字符, 键帽不闪
      this._setKbdReveal(reveal);
    };
    this._onKbdRevealUp = (e) => {
      if (e.code === "Backquote") this._setKbdReveal(false);  // keyup 移除
    };
    this._onKbdRevealBlur = () => this._setKbdReveal(false);   // window blur 兜底丢 keyup
    document.addEventListener("keydown", this._onKbdRevealDown);
    document.addEventListener("keyup", this._onKbdRevealUp);
    window.addEventListener("blur", this._onKbdRevealBlur);
    // 键位提示常驻开关(S5/W2, D6 刷新保留): 读本机偏好恢复开关态 —— 只挂 body class,
    // 不重绘键帽(D4)。偏好非法/读取失败一律回落「关」= 仅按住反引号显影(保守默认)。
    // class 立刻生效(别等下一拍, 否则常驻用户每次开页多闪一帧); aria 态等模板挂上后再同步。
    this._applyKbdPersist(this._kbdPersistStored());
    this.$nextTick(() => this._syncKbdSwAria());
    // 生效宽度: 全自动页按当前渲染现算(见 recomputeEffective); 窗口变化后重算, 保持
    // "填满容器 + 自适应"的观感; 固化页(colW 非空)用意图值, 不随窗口变(拖一列不再影响其它列)
    this._resizeDebounceTimer = 0;
    this._onWinResizeDebounced = () => {
      if (this._resizeDebounceTimer) clearTimeout(this._resizeDebounceTimer);
      this._resizeDebounceTimer = setTimeout(() => {
        this._syncHeadHeight();
        this.recomputeEffective();
      }, 120);
    };
    window.addEventListener("resize", this._onWinResizeDebounced);
    this.$nextTick(() => {
      this._syncHeadHeight();
      this.recomputeEffective();
    });
    /* W4(origin 提示, plan 26-09-21-1551): localStorage 按 origin 隔离, 换地址/端口 = 另一个
     * 独立存储。客户端唯一能观测到的信号是"本 origin 从没有任何列偏好"(空存储) —— 指纹跨站
     * 比对不可达(别的 origin 的存储读不到)。命中即提示一次, 把看不见的隔离变成可见。 */
    if (!readColStateRaw()) this._showColsOriginHint();
    /* 跨标签同步(F2, issue 26-09-20-1800): 别的标签改了列 -> 本标签整份采用存储值。
     * 若不同步, 本标签下一次 persistPage 会以旧底整段覆盖该页, 把别的标签的改动静默吞掉
     * (用户感知 = "列设置被重置")。双轨模型下采纳的是意图, 采纳永远安全。
     * storage 事件**只在其它标签**触发(写入方自己收不到) => 无需去重, 也不会自激。 */
    this._onColStore = (e) => {
      if (e.key === COLS_STORE_KEY) this.adoptColState();
    };
    window.addEventListener("storage", this._onColStore);
    /* FX-28: 时间口径跨标签同步(F2) —— 与列偏好同一套机制(整份采用存储值), 但**独立监听**:
     * 两个 key 的生命周期不同(列集合/列宽 vs 显示口径), 塞进同一个监听只会让判据互相纠缠。
     * 写入方自己收不到 storage 事件 => 无需去重, 也不会自激。 */
    this._onTimeFmtStore = (e) => {
      if (e.key === TIME_FMT_STORE_KEY) this.adoptTimeFmt();
    };
    window.addEventListener("storage", this._onTimeFmtStore);
    // FX-27: 相对时间时钟(30s 一跳) —— 见 data.nowSec 注释; 不挂 visibilitychange:
    // 后台标签本来就不会重排渲染, 回到可见时 refresh() 一并刷新, 无需额外开关
    this._clockTimer = setInterval(() => {
      this.nowSec = Math.floor(Date.now() / 1000);
    }, 30000);
    // 页面可见性(与 qB 自带 WebUI 同策略): 后台标签停止轮询; 恢复可见立即刷新并续排
    this._onVisChange = () => {
      if (document.hidden) {
        this._setKbdReveal(false);  // 切后台强制清显影 class(I4): visibilitychange(hidden) 兜底
        this.stopPolling();
      } else {
        this.adoptColState();  // F3: 补漏 —— 标签被冻结 / storage 事件丢失时, 回到可见即对齐一次
        this.adoptTimeFmt();   // 同上(FX-28): 时间口径也在回到可见时补对齐一次
        if (this.authOk) this.refresh();  // 登出态切回标签不发空 Bearer; R10-01: 判据 = 鉴权模式
      }
    };
    document.addEventListener("visibilitychange", this._onVisChange);
    // 全局右键屏蔽(CTX-03): 除顶部导航栏(header.topbar, atlas/prism 两套 UI 共用类名)与输入类
    // 元素(input/textarea/contenteditable, 保留复制粘贴的原生菜单)外, 一律阻止原生右键菜单;
    // 各处 .ctx-menu 自定义菜单由 Vue @contextmenu.prevent 触发, 与本监听器共存(preventDefault 幂等无害)
    this._onCtxMenu = (e) => {
      // 惰性补拉(issue 26-11-11-0633): flags 未取到时借右键交互补一发(已取到/在途时零副作用),
      // 成功后菜单门控项(跳检/流量图/菜单布局)按响应式在上下文里亮起; 放在早退分支之前,
      // 任意右键都算一次探测时机
      this.ensureWebFlags();
      const t = e.target;
      if (t && t.closest && (t.closest("header.topbar") || t.closest("input, textarea, [contenteditable]"))) return;
      e.preventDefault();
    };
    document.addEventListener("contextmenu", this._onCtxMenu);
    // 本地存储密钥必须重新验证后才放行遮罩; 密钥已轮换则由 401 收口清除。
    // 验证期间显示"验证中"加载态(bootstrapping)而非密钥输入表单 —— 修复刷新时闪现输入界面。
    // 跳过本地验证: 先读公开只读标志, 本机免鉴权则直接进入, 不弹登录表单
    const savedToken = localStorage.getItem("autoqb_token");
    // !走低层带超时单点 aqbFetch(issue 26-10-16-1303): 裸 fetch 悬挂时 await 永不返回 => 既不进
    //   免鉴权分支也不进 catch, 界面永久停在"正在验证本地密钥…"; 挂上限后悬挂落到下面 catch,
    //   与"公开标志读取失败"同一条兜底跳转(退密钥表单, 不让加载卡永久占位)。
    aqbFetch("/api/config/public").then((r) => (r.ok ? r.json() : null)).then((pub) => {
      if (pub && pub.web && pub.web.skip_local_verify) {
        this.authRequired = false;  // 唯一放行点(与 bootstrap 成功后语义一致)
        this.bootstrapping = false;  // FX-01: 本机免鉴权 -> 直接离开"验证中", 不经过密钥表单
        this.authMode = "local";  // R10-01: 身份来源 = 本机免鉴权(不再要求非空密钥串)
        this[AQB_TOKEN_FIELD] = savedToken || AQB_BLANK;  // 有旧密钥仍留着: 关掉开关后无需重新输入
        this.lastRid = null;
        this.startPolling();
        this.loadWebFlagsBoot();  // R2(计划 26-10-02-1955 W1): 登录后取一次功能旗标(跳检菜单开关); boot 期带有限重试(issue 26-11-11-0633)
        this.transferTargetsReload();  // T6(计划 26-10-31-0306): 预拉转移目标缓存(右键菜单「转移到」读侧; 方法在 transfer_flow.js)
        this._pullErrlogBoot();  // 通知 S3: 本机免鉴权路径的开页全量合并(密钥路径在 auth.js bootstrap)
        return;
      }
      if (savedToken) {
        this.bootstrapping = true;
        this.bootstrap(savedToken);  // 成功/失败均由 bootstrap 的 finally 落 bootstrapping = false
        return;
      }
      this.bootstrapping = false;  // FX-01: 无本地密钥 -> 才渲染密钥表单
    }).catch(() => {
      // 公开标志读取失败(服务未就绪/网络异常): 退到密钥表单, 不能让加载卡永久占位
      this.bootstrapping = false;
    });
  },
  unmounted() {
    this.stopEvents();  // P2: 断开 SSE(否则热重载后句柄堆叠)
    this.stopPolling();  // R4 清池(row117): 主轮骨架一并收(同上, 防热重载句柄堆叠)
    // R4 清池(row117): mounted 挂的五支浮层/退栈/防抖/可见性/右键监听提为实例字段后在此撤除
    // (原先匿名函数摘不掉, 热重载后旧句柄堆叠、操作已死实例)。防抖定时器一并清。
    if (this._onDocClick) {
      window.removeEventListener("click", this._onDocClick);
      this._onDocClick = null;
    }
    if (this._onEscKey) {
      document.removeEventListener("keydown", this._onEscKey);
      this._onEscKey = null;
    }
    if (this._onWinResizeDebounced) {
      window.removeEventListener("resize", this._onWinResizeDebounced);
      this._onWinResizeDebounced = null;
    }
    if (this._resizeDebounceTimer) {
      clearTimeout(this._resizeDebounceTimer);
      this._resizeDebounceTimer = 0;
    }
    if (this._onVisChange) {
      document.removeEventListener("visibilitychange", this._onVisChange);
      this._onVisChange = null;
    }
    if (this._onCtxMenu) {
      document.removeEventListener("contextmenu", this._onCtxMenu);
      this._onCtxMenu = null;
    }
    // 键盘快捷键引擎(计划 26-09-28-0354 W1): keydown 监听随组件销毁撤掉(同上, 防堆叠)
    if (this._kbKeyDown) {
      document.removeEventListener("keydown", this._kbKeyDown);
      this._kbKeyDown = null;
    }
    // 键位提示显影链(S1/W1): keydown/keyup/blur 监听随组件销毁撤掉, 并清掉可能残留的
    // body class(同上, 防热重载后旧句柄堆叠 / 显影态卡在 body 上)。
    if (this._onKbdRevealDown) {
      document.removeEventListener("keydown", this._onKbdRevealDown);
      this._onKbdRevealDown = null;
    }
    if (this._onKbdRevealUp) {
      document.removeEventListener("keyup", this._onKbdRevealUp);
      this._onKbdRevealUp = null;
    }
    if (this._onKbdRevealBlur) {
      window.removeEventListener("blur", this._onKbdRevealBlur);
      this._onKbdRevealBlur = null;
    }
    this._setKbdReveal(false);
    this._applyKbdPersist(false);  // 常驻态同清(同上: 防热重载后 body class 卡住); 本机偏好保留
    // 未保存改动防护(U1-b): 键盘拦截与原生 beforeunload 兜底一并撤掉(同上, 防热重载后句柄堆叠)
    if (this._cfgGuardKey) {
      document.removeEventListener("keydown", this._cfgGuardKey);
      this._cfgGuardKey = null;
    }
    this.cfgGuardRelease();
    // P1-2: 滚动/缩放监听随组件销毁撤掉(否则热重载后句柄堆叠, 滚动一次算 N 次)
    if (this._winListening) {
      window.removeEventListener("scroll", this._onWinScroll);
      window.removeEventListener("resize", this._onWinResize);
      this._winListening = false;
    }
    if (this._winRaf) {
      cancelAnimationFrame(this._winRaf);
      this._winRaf = 0;
    }
    // 跨标签同步(F2): storage 监听随组件销毁撤掉(否则热重载后句柄堆叠, 一次改动 adopt 多次)
    if (this._onColStore) {
      window.removeEventListener("storage", this._onColStore);
      this._onColStore = null;
    }
    // FX-28: 时间口径跨标签监听随组件销毁撤掉(同上, 防热重载后句柄堆叠)
    if (this._onTimeFmtStore) {
      window.removeEventListener("storage", this._onTimeFmtStore);
      this._onTimeFmtStore = null;
    }
    // FX-27: 相对时间时钟随组件销毁撤销(同上, 防热重载后句柄堆叠)
    if (this._clockTimer) {
      clearInterval(this._clockTimer);
      this._clockTimer = 0;
    }
    // 通知 S3: 60s 补拉定时器随组件销毁撤掉(同上, 防热重载后句柄堆叠)
    if (this._errPollTimer) {
      clearInterval(this._errPollTimer);
      this._errPollTimer = 0;
    }
    // P1-3: 顶栏尺寸观察器随组件销毁断开(ResizeObserver 不随元素消失自动停)
    if (this._headObs) {
      this._headObs.disconnect();
      this._headObs = null;
    }
    if (this._headRaf) {
      cancelAnimationFrame(this._headRaf);
      this._headRaf = 0;
    }
  },
  updated() {
    // P1-3: 顶栏高度改由 ResizeObserver 驱动 —— **只在尺寸真变时量一次**。
    // 旧实现每次渲染都调 _syncHeadHeight() -> getBoundingClientRect 是**强制同步布局**,
    // 在大 DOM(3000 行)下每次渲染都要付一次, 是"不跟手"的直接来源之一。
    // 这里只做"元素换没换"的引用比较(不触发布局), 换了才重新挂观察器并立即量一次。
    this._ensureHeadObserver();
    this._syncColAlignCss();  // 列对齐规则(R10-08): 值未变时内部直接返回
    // P1-2: 行高/容器偏移都只在签名变化时量(见 _measureRowH / _ensureWinTop), 不是每渲染一次
    this._measureRowH();
    this._ensureWinTop();
    // 渲染自查(计划 26-11-10-0027 W2(1), 拍板 D3 常驻): 主视图四面三处 O(1) 计数, 不一致只
    // console.error 不打断渲染; ref 不在场(视图未渲染)零 DOM 扫描。updated 是后置队列 —— 到
    // 这里时同批 flush 的子组件(aq-table)都已 patch 完, 即「主视图渲染后」。抽屉桥九变体面
    // 走桥模板自己的渲染钩子(dtAssertLayout), 不在此覆盖(桥是独立组件, 抽屉列态变更不触发根重渲)。
    this._assertLayouts();
  },
  methods: {
    /* 键位提示显影态开关(计划 26-11-14-0041 S1/W1, I2 纯 CSS class): 只在状态翻转时写一次
     * body.classList, 不碰任何几何、不重绘键位文本(取数链零改动, I1)。显/隐全交给共享 CSS
     * 的 opacity/visibility, 这里只负责挂/摘 body 上的 kbd-reveal。 */
    _setKbdReveal(on) {
      // 常驻态优先(S5/W2 两态互斥): 常驻开着时按住反引号不再叠加显影 class ——
      // 显示规则本就共用同一条, 但 body 上只允许一态, 免得 CSS/断言出现两套口径。
      if (on && this._kbdPersistOn) return;
      if (this._kbdRevealOn === on) return;  // 幂等: 同一态不重复写 DOM
      this._kbdRevealOn = !!on;
      document.body.classList.toggle("kbd-reveal", !!on);
    },
    /* 键位提示常驻态 / 全局开关(计划 26-11-14-0041 S5/W2, D2/D4/D6/D11)。
     * 两态互斥 = 开走 body.kbd-persist(常驻) / 关走 body.kbd-reveal(仅按住反引号);
     * D4: 切换只写 body class 与本机偏好, **零 JS 重绘**(开关高亮由 body.kbd-persist 的纯 CSS
     * 驱动), 取数链一行不动(I1)。D6: 偏好落 localStorage autoqb.ui.kbdPersist, 刷新由 mounted
     * 读回。D11: 开关 title 是控件自身功能说明, 不属「键位提示不走 title」的 I4 约束面。
     * 状态同步用 $refs 直写 aria-pressed(不引响应式字段 = 不触发渲染), refs 缺失时静默跳过
     * (node 电池/子组件上下文无 DOM 时保持纯 class 行为)。 */
    kbPersistToggle() {
      const on = !this._kbdPersistOn;
      try {
        localStorage.setItem(KBD_PERSIST_KEY, on ? "1" : "0");
      } catch (e) { /* 隐私模式等: 写入失败仅降级为本次会话内生效 */ }
      this._applyKbdPersist(on);
    },
    /* 常驻态落地: 幂等写 class + 必要时摘掉显影态(互斥) + 同步开关 aria-pressed。 */
    _applyKbdPersist(on) {
      const want = !!on;
      if (want) this._setKbdReveal(false);
      this._kbdPersistOn = want;
      document.body.classList.toggle("kbd-persist", want);
      this._syncKbdSwAria();
    },
    /* 开关按钮 aria-pressed 同步(纯属性写, 不触发渲染): refs 未挂/上下文无 DOM 时静默跳过。 */
    _syncKbdSwAria() {
      const sw = this.$refs && this.$refs.kbdSw;
      if (sw && sw.setAttribute) sw.setAttribute("aria-pressed", this._kbdPersistOn ? "true" : "false");
    },
    /* 本机偏好读侧: 只有显式 "1" 才算开; 其余(缺失/非法/读取异常)一律回落「关」(保守默认)。 */
    _kbdPersistStored() {
      try {
        return localStorage.getItem(KBD_PERSIST_KEY) === "1";
      } catch (e) {
        return false;
      }
    },
    /* ------------------------------------- 通知 S3(后端条目合并与补拉, 见文件头块注释) */
    /* 后端环条目 -> _errHistory 合并单点: id = "b"+后端 seq(按 seq 稳定去重), kind 映射
     * WARNING->warn / ERROR 及以上->error, ts 转完整 HH:MM:SS, source 固定 "backend"。
     * 已存在的 id 不重复入列(刷新重拉不产生重复); 新条目 unshift 到顶部(照 _errHistory
     * 新在上的排序, 与 toast 条目混排同式); 超 ERR_HISTORY_CAP 挤掉最旧(同 _recordErrorToast
     * 的环形语义)。opts.countUnread: boot 合并不计未读; 补拉计未读 —— 面板关闭期每条 +1,
     * 记账口径对齐 _recordErrorToast(打开时由 state.js 的 errPanelOpen watcher 清零)。 */
    _mergeBackendErrlog(items, last, opts = {}) {
      const countUnread = !!opts.countUnread;
      for (const it of items || []) {
        const id = "b" + it.seq;
        if (this._errHistory.some((e) => e.id === id)) continue;  // 去重: 同 seq 重拉不再入列
        this._errHistory.unshift({
          id,
          seq: it.seq,
          ts: _errBackendClock(it.ts),
          kind: _errLevelKind(it.level),
          text: it.msg,
          source: "backend",
        });
        if (this._errHistory.length > ERR_HISTORY_CAP) this._errHistory.pop();
        if (countUnread && !this.errPanelOpen) this._errUnread++;
      }
      if (typeof last === "number" && last > (this._errLogCursor || 0)) {
        this._errLogCursor = last;  // 游标只进不退(倒退走 _pullErrlog 的重启重拉路径)
      }
    },
    /* 拉一次 /api/errlog(以实例游标为 after)并合并。boot 全量(after=0)与 60s 增量共用;
     * 失败静默 —— 网络/鉴权异常不弹 toast, 下一轮补拉自愈。回包 last 低于已持游标 =
     * 后端重启过(seq 归零): 撤掉旧 backend 条目(否则同 seq 新条目会被去重吞掉)后
     * 清游标重拉全量; toast 条目不受影响(它们来自本会话前端, 与后端环无关)。 */
    async _pullErrlog(countUnread) {
      if (!this.authOk) return;  // 无凭证不出网(照 api() 门口径, 免得登出后定时器空转触发 _logout)
      try {
        const r = await this.api(`/api/errlog?after=${this._errLogCursor || 0}`);
        const last = (r && r.last) || 0;
        if (_errlogReseed(last, this._errLogCursor || 0)) {
          this._errHistory = this._errHistory.filter((e) => e.source !== "backend");
          this._errLogCursor = 0;
          const full = await this.api("/api/errlog?after=0");
          this._mergeBackendErrlog((full && full.items) || [], (full && full.last) || 0, { countUnread });
          return;
        }
        this._mergeBackendErrlog((r && r.items) || [], last, { countUnread });
      } catch (e) { /* 静默: 后端不可达不打扰用户, 下轮补拉自愈 */ }
    },
    /* boot 全量合并入口: 两条启动路径(auth.js bootstrap 成功 / 本机免鉴权)各调一次;
     * 不计未读(开页即见), 拉完(或失败)即起 60s 补拉定时器 —— 首拉失败也照起, 靠自愈。 */
    async _pullErrlogBoot() {
      this._errLogCursor = 0;
      await this._pullErrlog(false);
      this._startErrPoll();
    },
    _startErrPoll() {
      if (this._errPollTimer) return;  // 幂等: 双路径/重入不叠定时器
      this._errPollTimer = setInterval(() => this._pullErrlog(true), ERR_POLL_INTERVAL_MS);
    },
    /* R2 跳检菜单开关(计划 26-10-02-1955 W1): 登录后取一次 /api/webui/flags 写入 flags
     * (调用点: lifecycle 本机免鉴权路径 + auth.js bootstrap 成功路径, 两条 boot 入口走
     * loadWebFlagsBoot 带有限重试; 设置页 cfgSave 成功后再调刷新, 免重登)。请求失败保持
     * false = fail-closed(菜单不显示, 后端端点 403 兜底)。整对象替换赋值(非原地改键),
     * 保证 Vue 响应式触发。
     * boot 韧性(issue 26-11-11-0633): 原先单发失败 = 整会话静默 fail-closed(跳检菜单/
     * 流量页签/迁移提示/ctx_menu 布局全部消失, 仅刷新或设置保存可恢复)。现分三层:
     *   - 有限重试(loadWebFlagsBoot): boot 期失败后 1s/3s 各补一发(共 3 发), 覆盖偶发抖动;
     *   - flagsLoaded 态(state.js 显式建): 至少成功一次才置 true —— "未启用"(真值 false)
     *     与"未取到"(loaded=false)从此可分;
     *   - 惰性补拉(ensureWebFlags): 未取到时借入口交互(右键/开抽屉/流量图快捷键)补一发,
     *     成功后消费面按 Vue 响应式亮起。
     * 三层全部不改变 fail-closed 语义: 未取到/失败时 flags 恒 false/null, 后端 403 兜底不动。
     * qb_traffic_enabled(P5a, plan 26-10-03-0946 §07): qB 口径流量图入口旗标, 同一
     * fail-closed 口径 —— false 时入口不渲染、不请求(P5 验收)。
     * relocate_enabled(计划 26-11-07-1300 R6a): 整组迁移入口旗标(relocate.enabled 原样透传),
     * 同一 fail-closed 口径 —— false 时设定位置对话框不出「整组迁移已启用」常驻提示。
     * ctx_menu(计划 26-10-20-0024 W2): 行右键菜单四支用户布局原样透传(后端只存不发解析,
     * 合并语义在前端 ctx_menu.js 单点); 缺键/取失败 = null = 默认布局(注册表定义序)。
     * !四个键都必须显式写回: 漏一个 = 该功能恒取不到真值(旗标恒 false / 布局恒默认)。 */
    loadWebFlags(retryDelays) {
      // 单飞(分档): 在途请求按重试档(链长)分槽复用 —— boot 重试/设置页保存后重拉/惰性补拉
      // 并发时同档不叠发(issue 26-11-11-0633 防并发面)。分档而非单槽: 惰性单发不骑 boot 退避链
      // (await 方不必等重试穷尽才落门控), boot 的 3 发保障也不被在途惰性单发静默降级; 各档
      // 独立持槽互不挤占, 先结算的一方不清掉仍在途另一方的槽(否则后续同档调用会叠发)。
      // 异档并行窗口内双请求都收敛到同一 flags 写回(后到者为准), 仅出现在失败窗口期。
      // !本方法**不加 async**: async 包装会把 return 的 promise 再包一层外层 promise,
      // 并发方拿到的就不再是同一个对象(单飞判等失效)。普通函数直返槽内 promise。
      const len = (retryDelays || []).length;
      const slot = this._flagsLoadSlots || (this._flagsLoadSlots = {});
      if (slot[len]) return slot[len];
      const p = (async () => {
        const delays = retryDelays || [];
        for (let attempt = 0; ; attempt++) {
          try {
            const f = await this.api("/api/webui/flags");
            this.flags = {
              skip_check_menu: !!(f && f.skip_check_menu),
              qb_traffic_enabled: !!(f && f.qb_traffic_enabled),
              relocate_enabled: !!(f && f.relocate_enabled),
              ctx_menu: (f && f.ctx_menu) || null,
            };
            this.flagsLoaded = true;  // "未取到"收口: 之后惰性补拉停止, 真未启用不再重复探测
            return true;
          } catch (e) {
            this.flags = { skip_check_menu: false, qb_traffic_enabled: false, relocate_enabled: false, ctx_menu: null };
            this.flagsLoaded = false;
            // 登出态(api 已收口 _logout)不重试: 再发只会重复 401; 其余失败按 delays 退避续试
            if ((e && e.auth) || attempt >= delays.length) return false;
            await new Promise((resolve) => setTimeout(resolve, delays[attempt]));
          }
        }
      })();
      slot[len] = p;
      // 归置带槽主判等: 链结算时只清自己占的槽(链内全捕获不 reject, finally 派生 promise 无人消费)
      p.finally(() => { if (slot[len] === p) delete slot[len]; });
      return p;
    },
    /* boot 期入口专用(lifecycle 本机免鉴权路径 + auth.js bootstrap 成功路径): 失败后 1s/3s
     * 各补一发(共 3 发)。设置页保存后的重拉(config_editor)与惰性补拉不带重试 —— 前者自带
     * 2s 补拉, 后者靠反复交互天然形成间隔。 */
    loadWebFlagsBoot() {
      return this.loadWebFlags([1000, 3000]);
    },
    /* 惰性补拉(issue 26-11-11-0633): flags 未取到时补一发(单发不带重试 —— 入口交互触发面
     * 频繁, 带重试链会让 await 方等满退避才落门控; 未取到期间反复交互天然连续探测)。
     * 已取到或在途时零网络副作用(在途时复用单飞 promise)。调用方两种用法:
     * fire-and-forget(右键/开抽屉/设定位置框, 成功后消费面按响应式亮起)与 await(流量图
     * 快捷键, 补拉完再落门控, 不把"没取到"当"没启用"误报)。 */
    ensureWebFlags() {
      if (this.flagsLoaded) return null;
      return this.loadWebFlags();
    },
  },
};
