/* lifecycle.js — 根组件生命周期(created/mounted/unmounted/updated): W2b 自 app.js 拆出。
 * WARN: 同 state.js: 走根选项展开, 不走 app.mixin —— 否则 hub-field 实例也会跑 mounted
 * (监听器/fetch 双份)。成员逐行原样搬运。 */
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
    this._winMeasured = { torrent: false, group: false, member: false };  // 该 kind 是否量齐
    /* 行间距(px)**实测**缓存: 三个容器的真实 gap 不同(atlas .group-table 6px / prism 5px /
     * 成员容器 .detail 是块级容器 = 0), 硬编码会让占位总高失真(见文件头 BUG-1 注释)。 */
    this._winGap = {};
    this._winRaf = 0;      // 滚动合帧句柄
    this._winListening = false;
    // 键盘快捷键(计划 26-09-28-0354 W1): 生效键表缓存(非响应式, W6 改键时失效)与
    // _rowWindow 前缀和留存(光标滚动进视口用, 见 columns.js)都是纯缓存, 刻意不进 data
    this._kbTableCache = null;
    this._rowPre = {};
  },
  async mounted() {
    /* P1-2: 视口高度 + 页面滚动监听(被动 + rAF 合帧, 滚动本身不做任何布局读取) */
    this._winViewH = window.innerHeight;
    window.addEventListener("scroll", this._onWinScroll, { passive: true });
    window.addEventListener("resize", this._onWinResize);
    this._winListening = true;
    // 点击页面空白处: 关闭右键菜单与列选择器(两者都是临时浮层)
    window.addEventListener("click", () => {
      this.menu.visible = false;
      this.headMenu.visible = false;   // 表头右键菜单(TBL-05)与右键菜单同层
      this.colMenuOpen = false;
      this.filterMenu = "";
      this.uiMenuOpen = false;  // 顶栏界面切换下拉(与列选择器/筛选器同层的临时浮层)
      this.searchHelpOpen = false;  // 搜索语法浮卡(触发钮自身 @click.stop 已拦截, 点空白 = 收起)
      this.filePrio.visible = false;
      this.addCatMenu = false;  // 添加种子对话框内浮层: 点空白处统一收起(触发元素自身已 @click.stop 拦截)
      this.addTagMenu = false;
      this.addPathPop = false;
      // FX-08: 限速浮层无遮罩 -> 点空白视为"放弃本次修改"直接收起(与 Esc 同语义)
      if (this.speedOpen) this.closeSpeedDialog();
    });
    // Esc: 逐层退栈(FIX-07) —— 确认框/弹窗 → 抽屉内浮层/抽屉 → 筛选器下拉/弹层(pop) → 右键菜单 → 清选择/收展开兜底
    // WARN: 本链与 dialogs.js::escBusy 是同一份浮层名单(后者给 config_hub 的「Esc 返回设置首页」守门),
    //   新增浮层两处同步; config_hub.js::hubOnKey 的 Esc 分支排在本链之后(链上有层时它不动)
    document.addEventListener("keydown", (e) => {
      if (e.key !== "Escape") return;
      if (this.modal.visible) this.resolveModal(false);
      else if (this.addOpen) this.escAddTorrent();  // 添加种子对话框: 先收内部浮层(分类/标签下拉 → 位置面板), 再关对话框
      else if (this.statsOpen) this.closeStats();  // 统计面板对话框: 与添加对话框同层(先后于确认框)
      else if (this.speedOpen) this.closeSpeedDialog();  // 限速弹窗(SPD-04): 与统计面板同层
      else if (this.mgrOpen) this.closeMgr();  // 分类/标签管理对话框: 与添加对话框同层(内部确认框仍最优先)
      else if (this.metaOpen) this.closeMeta();  // 标签/分类编辑对话框: 与管理对话框同层
      else if (this.filePrio.visible) this.filePrio.visible = false;  // 文件优先级小菜单: 抽屉内浮层先于抽屉关闭
      else if (this.drawer.open) this.closeDrawer();  // 详情抽屉: 确认框优先, 其后于其它浮层
      else if (this.historyOpen) this.historyOpen = false;  // 历史弹层(pop): 弹层先于右键菜单关闭
      else if (this.headMenu.visible) this.headMenu.visible = false;  // 表头右键菜单(TBL-05)
      else if (this.colMenuOpen) this.colMenuOpen = false;  // 列选择器弹层(pop)
      else if (this.uiMenuOpen) this.uiMenuOpen = false;  // 顶栏界面切换下拉(pop)
      else if (this.searchHelpOpen) this.searchHelpOpen = false;  // 搜索语法浮卡(pop)
      else if (this.kbHelpOpen) this.kbHelpOpen = false;  // 快捷键帮助浮层(W6, H 组 Shift+Slash 打开)
      else if (this.filterMenu) this.filterMenu = "";  // 筛选器下拉(pop)
      else if (this.menu.visible) this.menu.visible = false;  // 右键菜单: pop 层之后
      else if (this.selGroups.length || this.selMembers.length) this.clearSelection();  // 兜底: 清除行/组选择(复用现有逻辑)
      else if (this.expandedKey) this.expandedKey = null;  // 兜底: 收起分组展开
      else if (this.expandedShowEp) this.expandedShowEp = null;  // 兜底: 收起追剧集展开
      else if (this.expandedShows.length) this.expandedShows = [];  // 兜底: 收起追剧剧展开
    });
    // 键盘快捷键引擎(计划 26-09-28-0354 W1): 必须注册在 Esc 退栈链**之后**(注册序 = 触发序);
    // 引擎自身对 Escape 也直接放行, 双保险。句柄存实例, unmounted 撤掉防热重载堆叠。
    this._kbKeyDown = (e) => this._kbOnKeyDown(e);
    document.addEventListener("keydown", this._kbKeyDown);
    // 生效宽度: 全自动页按当前渲染现算(见 recomputeEffective); 窗口变化后重算, 保持
    // "填满容器 + 自适应"的观感; 固化页(colW 非空)用意图值, 不随窗口变(拖一列不再影响其它列)
    let resizeTimer = null;
    window.addEventListener("resize", () => {
      if (resizeTimer) clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => {
        this._syncHeadHeight();
        this.recomputeEffective();
      }, 120);
    });
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
     * storage 事件**只在其它标签**触发(写入方自己收不到) ⇒ 无需去重, 也不会自激。 */
    this._onColStore = (e) => {
      if (e.key === COLS_STORE_KEY) this.adoptColState();
    };
    window.addEventListener("storage", this._onColStore);
    /* FX-28: 时间口径跨标签同步(F2) —— 与列偏好同一套机制(整份采用存储值), 但**独立监听**:
     * 两个 key 的生命周期不同(列集合/列宽 vs 显示口径), 塞进同一个监听只会让判据互相纠缠。
     * 写入方自己收不到 storage 事件 ⇒ 无需去重, 也不会自激。 */
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
    document.addEventListener("visibilitychange", () => {
      if (document.hidden) this.stopPolling();
      else {
        this.adoptColState();  // F3: 补漏 —— 标签被冻结 / storage 事件丢失时, 回到可见即对齐一次
        this.adoptTimeFmt();   // 同上(FX-28): 时间口径也在回到可见时补对齐一次
        if (this.authOk) this.refresh();  // 登出态切回标签不发空 Bearer; R10-01: 判据 = 鉴权模式
      }
    });
    // 全局右键屏蔽(CTX-03): 除顶部导航栏(header.topbar, atlas/prism 两套 UI 共用类名)与输入类
    // 元素(input/textarea/contenteditable, 保留复制粘贴的原生菜单)外, 一律阻止原生右键菜单;
    // 各处 .ctx-menu 自定义菜单由 Vue @contextmenu.prevent 触发, 与本监听器共存(preventDefault 幂等无害)
    document.addEventListener("contextmenu", (e) => {
      const t = e.target;
      if (t && t.closest && (t.closest("header.topbar") || t.closest("input, textarea, [contenteditable]"))) return;
      e.preventDefault();
    });
    // 本地存储密钥必须重新验证后才放行遮罩; 密钥已轮换则由 401 收口清除。
    // 验证期间显示"验证中"加载态(bootstrapping)而非密钥输入表单 —— 修复刷新时闪现输入界面。
    // 跳过本地验证: 先读公开只读标志, 本机免鉴权则直接进入, 不弹登录表单
    const savedToken = localStorage.getItem("autoqb_token");
    fetch("/api/config/public").then((r) => (r.ok ? r.json() : null)).then((pub) => {
      if (pub && pub.web && pub.web.skip_local_verify) {
        this.authRequired = false;  // 唯一放行点(与 bootstrap 成功后语义一致)
        this.bootstrapping = false;  // FX-01: 本机免鉴权 -> 直接离开"验证中", 不经过密钥表单
        this.authMode = "local";  // R10-01: 身份来源 = 本机免鉴权(不再要求非空密钥串)
        this.token = savedToken || "";  // 有旧密钥仍留着: 关掉开关后无需重新输入
        this.lastRid = null;
        this.startPolling();
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
    // 键盘快捷键引擎(计划 26-09-28-0354 W1): keydown 监听随组件销毁撤掉(同上, 防堆叠)
    if (this._kbKeyDown) {
      document.removeEventListener("keydown", this._kbKeyDown);
      this._kbKeyDown = null;
    }
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
    // 旧实现每次渲染都调 _syncHeadHeight() → getBoundingClientRect 是**强制同步布局**,
    // 在大 DOM(3000 行)下每次渲染都要付一次, 是"不跟手"的直接来源之一。
    // 这里只做"元素换没换"的引用比较(不触发布局), 换了才重新挂观察器并立即量一次。
    this._ensureHeadObserver();
    this._syncColAlignCss();  // 列对齐规则(R10-08): 值未变时内部直接返回
    // P1-2: 行高/容器偏移都只在签名变化时量(见 _measureRowH / _ensureWinTop), 不是每渲染一次
    this._measureRowH();
    this._ensureWinTop();
  },
};
