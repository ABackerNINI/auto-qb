/* auto-qb WEB UI · 列模型交互(列宽/列序/列菜单/列持久化) + 行窗口化
 *
 * app.js 按域拆分出的片段(2026-09-20)。约定与 config_editor.js / config_rules.js 同一范式:
 * 挂到 window.AQB_COLUMNS, 由 app.js 末尾 app.mixin(window.AQB_COLUMNS) 注入同一个 Vue 实例 ——
 * 方法体里的 this 仍是那个组件实例, 跨模块互调与拆分前完全等价。
 *
 * !本文件在 HTML 里必须排在 app.js **之前**(app.js 末尾要读 window.AQB_COLUMNS);
 *   用到的列模型常量(TABLE_COLUMNS / MIN_COL_PX / STATE_RANK …)仍单点定义在 app.js 顶部。
 */
/* ============ 主表横滚指示条(计划 26-11-01-0553 S3) ============
 * 原生横条已被 shared/hscroll.css 彻底隐藏, 这里补回「拖动横滚」这一唯一会丢的能力:
 * 一根悬浮在状态栏上缘的胶囊(300x5, hover 7), 两条召唤路径:
 *   ① 指针伸进内容区底部 24px 带内(D5) —— 纵向带**不含状态栏**, 横向只认胶囊邻域(宽 + 左右各 40px);
 *   ② Shift+滚轮 / 触控板双指横滚时亮出, 停手 1.5s 自落(2026-11-01 用户追加)。
 * 可拖、可点轨道跳转。
 *
 * 为什么状态压在模块级闭包里: 本片段只有 methods(无 data / 无 mounted), 由 app.mixin 注入
 * **同一个** Vue 实例 —— 指示条是跨视图单例(三主表 v-if 互斥, 同时最多一个), 状态放进组件
 * data 反而要占命名空间、还得靠生命周期初始化。故一切状态在 HSCROLL_IND 里, DOM 惰性创建。
 * !变量名带 _IND 后缀: 各片段都是经典脚本, 顶层 const 共用全局词法作用域, 撞名即整页 SyntaxError。
 */
const HSCROLL_IND = {
  pill: null,      // 轨道单例(.hscroll-pill), 惰性创建
  thumb: null,     // 滑块(.hscroll-pill > i), 几何由 JS 写内联样式决定
  el: null,        // 最近一次 _hscrollSync 收到的主表容器(热区召唤时拿它重算)
  page: null,      // 该容器的表 id
  overflow: false, // 该容器当前是否有横向余量(热区 handler 只读这个布尔, 不读布局)
  hot: false,      // 指针是否在底部热区(纵向带内 **且** 横向落在胶囊邻域)
  bandIn: false,   // 指针是否已在纵向带内(每次入带只重算一次几何, 之后逐帧只做算术)
  pillW: 0,        // 胶囊实测宽(热区横向判据用; 由 _hscrollSync 量, 热路径上不读布局)
  wheelOn: false,  // Shift/触控板横滚召唤中(停手 1.5s 后自落)
  wheelT: 0,       // 上述停留定时器句柄
  drag: null,      // 拖拽会话 { id, x, left, maxThumb, maxScroll }
  bound: false,    // 文档级监听只挂一次
  ro: null,        // ResizeObserver(观察当前主表容器)
  roEl: null,
  raf: 0,
  sbH: -1,         // 状态栏实测高缓存; -1 = 未量(window resize 时清)
};

/* ---------------- P1-2 行窗口化 · 窗口源描述符(计划 26-11-02-0351 W2 参数化) ----------------
 * 窗口化的滚动几何原先散在方法里直读 window 全局(scrollY / innerHeight, 全页滚动硬编码);
 * 现抽成**按 kind 的窗口源描述符**: 滚动源 / 视口 / 容器顶偏移 / 滚动绑定 / 行键, 每 kind 一份。
 * - 主表三 kind(torrent/group/member)= 文档滚动型 WIN_SRC_DOC(原实现逐行搬入, 行为零变化);
 * - 容器型 winSrcContainer(预留, W3 接线 drawerContent): 滚动源 = 指定容器的 scrollTop,
 *   视口 = 容器 clientHeight, 绑定 = 元素 scroll 监听 + ResizeObserver(容器高变化不触发 window resize)。
 * 保守默认: kind 未在 WIN_SOURCES 注册时 _winSrc 回落 WIN_SRC_DOC —— 描述符缺失 = 现行为。
 * _winTop 的几何口径两型对称: 文档型 = rect.top + scrollY(相对文档内容顶), 容器型 =
 * rect.top - 滚动容器rect.top + scrollTop(相对容器内容顶) —— rel = scrollY - top 都是
 * 「已滚进行块的距离」, _rowWindow 的前缀和算式两型共用。
 * bindScroll/unbindScroll 是绑定契约: 文档型的实际挂载仍单点在 lifecycle.js(P1-2 原样, 描述符
 * 与其逐字同款); 容器型由接线方消费 —— handler 约定 = 事件到达后按描述符重读 scrollY/viewH
 * 写回引擎态(this._winScrollY / this._winViewH), 即 _onWinScroll/_onWinResize 的合帧写法。
 */
/* WIN-SOURCES-BEGIN: 窗口化几何对 window.scrollY / window.innerHeight 的直读只允许出现在这一段 */
const WIN_SRC_DOC = {
  scrollY: () => window.scrollY,
  viewH: () => window.innerHeight,
  topOffset(el) {
    return el.getBoundingClientRect().top + window.scrollY;
  },
  bindScroll(handler) {
    window.addEventListener("scroll", handler, { passive: true });
  },
  unbindScroll(handler) {
    window.removeEventListener("scroll", handler);
  },
  keyOf(item) {
    return item.hash;  // torrent/member 的行键; group 覆盖为 item.key(见 WIN_SOURCES)
  },
};
const WIN_SOURCES = {
  torrent: WIN_SRC_DOC,
  member: WIN_SRC_DOC,
  group: Object.assign({}, WIN_SRC_DOC, { keyOf: (item) => item.key }),
  /* 抽屉内容树两变体(W3 接线, 计划 26-11-02-0351): 滚动源 = .drawer-body(抽屉滚动容器,
   * sticky-scrollpad-inset 坑档确认), 行键 = 行对象 k(文件路径, 描述符 rowKey 字段)。
   * getEl 惰性求值 —— 抽屉 v-if 未渲染时各函数逐次判空(scrollY/viewH 0 = 零差异回退)。 */
  drawerContent: Object.assign(winSrcContainer(() => document.querySelector(".drawer-body")), {
    keyOf: (item) => item.k,
  }),
};
/* 容器滚动型描述符工厂(W2 只交付形态, 不接线任何 kind): getEl 返回滚动容器元素
 * (惰性求值 —— 容器可能 v-if 未渲染, 各函数逐次判空: 未渲染 = scrollY 0 / viewH 0, 走零差异回退)。 */
function winSrcContainer(getEl) {
  return {
    scrollY() {
      const el = getEl();
      return el ? el.scrollTop : 0;
    },
    viewH() {
      const el = getEl();
      return el ? el.clientHeight : 0;
    },
    topOffset(el) {
      const sc = getEl();
      if (!sc || !el) return 0;
      return el.getBoundingClientRect().top - sc.getBoundingClientRect().top + sc.scrollTop;
    },
    bindScroll(handler) {
      const el = getEl();
      if (!el) return;
      el.addEventListener("scroll", handler, { passive: true });
      // 容器视口高不随 window resize 变(抽屉抽成一条再撑回), 用 ResizeObserver 盯住:
      // 尺寸变化同 handler 一并通知(接线方合帧后重读 scrollY/viewH)。
      if (typeof ResizeObserver === "function") {
        this._ro = new ResizeObserver(() => handler());
        this._ro.observe(el);
      }
    },
    unbindScroll(handler) {
      const el = getEl();
      if (el) el.removeEventListener("scroll", handler);
      if (this._ro) {
        this._ro.disconnect();
        this._ro = null;
      }
    },
  };
}
/* WIN-SOURCES-END */

window.AQB_COLUMNS = {
  methods: {
    toggleColMenu(ev) {
      this.colMenuAt = null;  // 按钮路径: 清掉右键锚点, 弹层回到 .col-picker 下的常规 CSS 定位
      this.colMenuOpen = !this.colMenuOpen;
      if (this.colMenuOpen) this.colFlip = this._menuOverflowsRight(ev && ev.currentTarget, 300);
    },
    /* 表头右键(TBL-05): 就地打开列选择器弹层(复用 col-menu 与 colHidden 勾选逻辑),
     * fixed 定位锚在右键坐标; 右/下边界自钳制(宽 300 与 .col-menu 一致, 高度按剩余空间截断
     * 由 colMenuStyle 给 maxHeight+滚动), 不走 flip-x(inline left 优先级高于类, 翻转不生效)。
     * page 参数当前仅区分语义(弹层四段全量展示), 留作按视图段落定位的扩展点 */
    openColMenuAt(ev, page) {
      const FIT = window.AQB_OVERLAY_FIT; /* 几何单点(issue 26-10-20-2231), 方法内取别名 */
      const W = 300;
      const y = Math.max(FIT.EDGE, ev.clientY);
      this.colFlip = false;
      this.colMenuAt = {
        x: FIT.clampAxis(ev.clientX, W, window.innerWidth),
        y,
        mh: Math.max(160, window.innerHeight - y - FIT.EDGE),
      };
      this.colMenuOpen = true;
    },
    /* 弹层内联样式: 仅右键路径给 fixed 坐标与视口内最大高度; 按钮路径返回 null 走原 CSS */
    colMenuStyle() {
      const at = this.colMenuAt;
      if (!at) return null;
      return { position: "fixed", left: at.x + "px", top: at.y + "px", maxHeight: at.mh + "px", overflowY: "auto" };
    },
    /* 变体表格体桥(计划 26-10-12-0527 D1)的公共取列口: drawer.html 的 Teleport 块按 tableId
     * 动态取可见列(经典链走描述符 cols 指名的 computed, 变体表同样可用 —— 本方法只是模板
     * 动态 id 的取法, 语义与 _visibleCols 逐位一致)。 */
    visibleColsOf(page) {
      return this._visibleCols(page);
    },

    gridStyle(page) {
      // 列模板由 computed 缓存(见 *_Grid): 行渲染只取同一引用, 不每行拼字符串
      // 表 id -> grid computed 名的映射在注册表(主视图 TABLE_DEFS / 抽屉表 DRAWER_TABLE_DEFS,
      // 计划 26-10-11-2106 W2: 抽屉三表接壳后同吃本函数, 故查并集)
      const def = ALL_TABLE_DEFS[page];
      return def ? this[def.grid] : null;
    },

    /* 表头横滚同步(计划 26-10-11-1722 P4 收敛): 三视图共用一份。
     * 表头已脱离 .group-table 容器做纵向 sticky(overflow 上下文), 横向滚动靠 JS 桥接:
     * 用 transform 而非 scrollLeft, 避免反向触发自身 scroll 事件形成回环; 不带 transition 跟手不滞后。
     * 三件事(缺一即静默坏): ①表头位移 = 容器 scrollLeft 反向; ②--head-pin-x 供首列吸左首格反向抵消;
     * ③.is-hscrolled 打标(容器 + 表头)供 CSS 画右缘落影 —— CSS 无法感知 scrollLeft, 丢标 = 边界落影永不出现。
     * 调用点: groups.html(container ref=groupTable, page=group) / torrents.html(torrentTable, torrent)
     *        / shows.html(showTable, show) —— 三个容器都是 .group-table, 表头元素经 _headEl(page) 取。 */
    syncHeadScroll(ev, page) {
      const head = this._headEl(page);
      if (!head) return;
      const x = ev.target.scrollLeft;
      head.style.transform = `translateX(${-x}px)`;
      // 首列吸左(issue 26-10-06-1717): 首格反向位移抵消容器滚动, 与行内 sticky 同形(规则在 CSS)
      head.style.setProperty("--head-pin-x", `${x}px`);
      // 首列吸左边界提示(见皮肤 CSS 的 .is-hscrolled 规则): 横滚非零 = 有列滑进吸左首格下方
      ev.target.classList.toggle("is-hscrolled", x > 0);
      head.classList.toggle("is-hscrolled", x > 0);
      this._hscrollSync(ev.target, page);  // 第四个消费方(计划 26-11-01-0553 S3): 底部横滚指示条
    },

    /* ---------------- 主表横滚指示条(计划 26-11-01-0553 S3) ----------------
     * 几何入口是 syncHeadScroll 尾部(容器 scroll 天然覆盖拖动 / 滚轮 / 键盘 / 程序化 scrollLeft);
     * 但**发现容器**的入口是热区 mousemove(_hscrollHot -> _hscrollTarget), 不依赖曾经滚过 ——
     * 文档级监听由 _ensureHeadObserver 在挂载时绑上, 纯鼠标用户第一次伸进底部热区就能召唤出胶囊。
     * 只认主表三视图: 抽屉变体面(shared/tpl/xtpl.html:360)也走 syncHeadScroll, 但传的是抽屉表 id ——
     * 抽屉列集窄、横滚罕见, 不配指示条(D4/R5)。这条判定必须留在**建 DOM 之前**,
     * 否则抽屉面滚一下就在 body 里留下一个永远不用的胶囊。
     *
     * !重算时机只有四个: ①容器 scroll(本函数) ②热区进入那一刻 ③ResizeObserver(容器盒变)
     *   ④window resize(清状态栏高缓存 + 重算)。
     * 刻意**不**在列应用路径(6 处 colWidths 写入点)显式触发, 也不挂 MutationObserver:
     * 改列宽 / 隐藏列会让 scrollWidth 变而容器盒子不变(RO 观察不到), 但那一刻指示条必然不可见
     * (它只在热区里显示), 陈旧几何没人观察得到; 下一次进入热区时 ② 用同一份本函数修正。
     * 为一个观察不到的瞬时值挂 MutationObserver = 每次行 DOM 变更都付一次回调, 不值。
     */
    _hscrollSync(el, page) {
      if (page !== "group" && page !== "torrent" && page !== "show") return;
      if (!el) return;
      HSCROLL_IND.el = el;
      HSCROLL_IND.page = page;
      const sw = el.scrollWidth;
      const cw = el.clientWidth;
      HSCROLL_IND.overflow = sw > cw;
      if (!HSCROLL_IND.overflow) {  // 无横向余量: 不写几何, 也不该留任何痕迹
        this._hscrollShow();
        return;
      }
      /* !建 DOM 挪到溢出判定**之后**: 宽窗无溢出是常态, 那时连隐形节点都不多留一个
       * (D10 保守默认: 常态下指示条完全不可见); 也免得热区每次进入都白建一次。
       * trackW 要读 pill.clientWidth, 故 _hscrollPill() 必须排在量 trackW 之前。 */
      const pill = this._hscrollPill();
      // 轨道宽实测(不硬编码): CSS 是 min(300px, 48vw), 窄屏会缩
      const trackW = pill.clientWidth;
      HSCROLL_IND.pillW = trackW;  // 热区横向判据的输入: 在这里量一次, 逐帧 mousemove 只做算术
      const thumbW = Math.min(trackW, Math.max(32, Math.round((trackW * cw) / sw)));
      const maxScroll = sw - cw;
      const maxThumb = Math.max(0, trackW - thumbW);
      const at = maxScroll > 0 ? (el.scrollLeft / maxScroll) * maxThumb : 0;
      const thumb = HSCROLL_IND.thumb;
      thumb.style.width = thumbW + "px";
      thumb.style.transform = "translateX(" + Math.round(at) + "px)";
      this._hscrollObserve(el);
      this._hscrollShow();
    },
    /* 惰性单例: 首次**量到横向余量**才建 DOM(模块加载时、宽窗无溢出时, 一个节点都不多)。
     * 结构固定为 CSS 契约里的 <div class="hscroll-pill"><i></i></div>, 挂 body 末尾(shared/hscroll.css 注释钉死)。 */
    _hscrollPill() {
      if (HSCROLL_IND.pill) return HSCROLL_IND.pill;
      const pill = document.createElement("div");
      pill.className = "hscroll-pill";
      const thumb = document.createElement("i");
      pill.appendChild(thumb);
      document.body.appendChild(pill);
      HSCROLL_IND.pill = pill;
      HSCROLL_IND.thumb = thumb;
      /* pill 级监听就地绑(与建 DOM 同生共死); 文档级监听(热区 + resize)与 pill 无关,
       * 已改为挂载即绑 —— 见 _hscrollBind 的注释。 */
      pill.addEventListener("pointerdown", (ev) => this._hscrollDown(ev));
      pill.addEventListener("pointermove", (ev) => this._hscrollMove(ev));
      pill.addEventListener("pointerup", (ev) => this._hscrollUp(ev));
      pill.addEventListener("pointercancel", (ev) => this._hscrollUp(ev));
      return pill;
    },
    /* 状态栏实测高: 优先量 .statusbar(状态条可能不渲染 -> 量不到时回落令牌), 再回落 34。
     * 值缓存到 window resize(④) —— 热区 handler 每次 mousemove 都要用它, 不能每次都量。 */
    _hscrollStatusbarH() {
      if (HSCROLL_IND.sbH >= 0) return HSCROLL_IND.sbH;
      let h = 0;
      const bar = document.querySelector(".statusbar");
      if (bar) h = bar.getBoundingClientRect().height;
      if (!h) {
        const tok = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--statusbar-h"));
        h = Number.isFinite(tok) ? tok : 0;
      }
      HSCROLL_IND.sbH = h > 0 ? h : 34;
      return HSCROLL_IND.sbH;
    },
    /* 文档级监听只挂一次(守卫 bound): 热区 mousemove + window resize。
     * !必须**挂载即绑**, 不能等第一次横向滚动: 纯鼠标用户没有拖拽入口(D7), 正是最需要指示条的人;
     *   若仍挂在 _hscrollPill() 里, 他们永远等不到 —— 不横滚 -> 不建 DOM -> 不挂监听 -> 永远不建。
     * 调用点: _ensureHeadObserver 第一行(shared/lifecycle.js 每次渲染都走), 自带 bound 守卫,
     *   重复调用零成本; 放在其 ResizeObserver 早退分支**之前**, 老浏览器降级路径也能绑上。
     * 热区只在 pointer: fine 下挂(R10): 触屏没有 hover 语义, 触摸横滚本就原生可用, 不退化。 */
    _hscrollBind() {
      if (HSCROLL_IND.bound) return;
      HSCROLL_IND.bound = true;
      if (window.matchMedia && window.matchMedia("(pointer: fine)").matches) {
        document.addEventListener("mousemove", (ev) => this._hscrollHot(ev), { passive: true });
        document.addEventListener("wheel", (ev) => this._hscrollWheel(ev), { passive: true });
      }
      window.addEventListener("resize", () => {
        HSCROLL_IND.sbH = -1;  // 状态栏高随媒体查询变(窄屏折行 / 状态条隐藏)
        if (HSCROLL_IND.el) this._hscrollSync(HSCROLL_IND.el, HSCROLL_IND.page);
        this._hscrollShow();
      }, { passive: true });
    },
    /* Shift+滚轮 / 触控板双指横滚的召唤路径(2026-11-01 用户追加): 这类用户不需要把指针伸到
     * 底部带, 但横滚时同样缺位置反馈 —— 横滚期间把胶囊亮出来, 停手 1.5s 后自落。
     * 判据 = 指针落在那张主表上 且 有横向意图(shiftKey 或 |deltaX| > |deltaY|)。
     * !不在每次 wheel 里重算几何: 紧随其后的容器 scroll 事件会走 syncHeadScroll 更新;
     *   这里只在「胶囊还没建出来」或「换了张表」时补一次, 免得每次滚轮都读一遍布局。 */
    _hscrollWheel(ev) {
      const horiz = ev.shiftKey || Math.abs(ev.deltaX) > Math.abs(ev.deltaY);
      if (!horiz) return;
      const t = this._hscrollTarget();
      if (!t) return;
      // 指针要在这张表上: contains 走节点关系, 不读布局(wheel 频率不低)
      if (!(ev.target instanceof Node) || !t.el.contains(ev.target)) return;
      if (!HSCROLL_IND.pill || HSCROLL_IND.el !== t.el) this._hscrollSync(t.el, t.page);
      if (!HSCROLL_IND.overflow) return;
      HSCROLL_IND.wheelOn = true;
      this._hscrollShow();
      if (HSCROLL_IND.wheelT) clearTimeout(HSCROLL_IND.wheelT);
      HSCROLL_IND.wheelT = setTimeout(() => {
        HSCROLL_IND.wheelT = 0;
        HSCROLL_IND.wheelOn = false;
        this._hscrollShow();
      }, 1500);
    },
    /* 当前可见的主表容器。三视图 v-if 互斥, 最多命中一个; 三个 ref 都是普通 div.group-table
     * (groups.html:18 groupTable / torrents.html:4 torrentTable / shows.html:5 showTable),
     * 不是组件实例, 无需取 $el。
     * !不依赖「曾经滚过」: 热区召唤是首次发现容器的唯一时机, 读 HSCROLL_IND.el 在这里恒为 null。
     * 判定用 getClientRects().length(本文件 _headEl 的既有口径): 未渲染 / display:none 的元素
     * 按未渲染处理, 不会误取到一个量不出宽度的空壳。 */
    _hscrollTarget() {
      const refs = [
        ["groupTable", "group"],
        ["torrentTable", "torrent"],
        ["showTable", "show"],
      ];
      for (const [name, page] of refs) {
        const el = this.$refs[name];
        if (el && el.getClientRects().length) return { el, page };
      }
      return null;
    },
    /* 热区纵向带 = [状态栏上缘 - 24px, 状态栏上缘) —— **不含状态栏本身**(D5)。
     * !早先写成单边 `clientY >= innerHeight - 状态栏高 - 24`, 少了上界 ⇒ 状态栏那 34px 也落在带内
     * (状态栏是常用控件区, 不该召唤滚动条)。2026-11-01 用户验收指出后补上上界。 */
    _hscrollBand(ev) {
      const bottom = window.innerHeight - this._hscrollStatusbarH();  // 状态栏上缘
      return ev.clientY >= bottom - 24 && ev.clientY < bottom;
    },
    /* 横向判据: 指针要落在胶囊**本身**的邻域内(左右各放 40px 余量), 不是全屏宽都算。
     * !早先只判 clientY ⇒ 鼠标扫过底部右侧的速度/限速区也召唤胶囊(2026-11-01 用户验收指出)。
     * 只读缓存(HSCROLL_IND.pillW), 热路径上不量布局。 */
    _hscrollInPillSpan(ev) {
      const w = HSCROLL_IND.pillW;
      if (!w) return false;
      return Math.abs(ev.clientX - window.innerWidth / 2) <= w / 2 + 40;
    },
    /* 热区 handler(R1: 落在热路径上, 每次 mousemove 都跑): 纵向两次比较 + 横向一次减法,
     * 不读布局、不写 DOM; 状态没变立刻返回。**入带那一刻**才重算几何(重算时机 ②)。 */
    _hscrollHot(ev) {
      if (!this._hscrollBand(ev)) {
        HSCROLL_IND.bandIn = false;  // 出带: 下次入带要重新量一次几何
        if (HSCROLL_IND.hot) {
          HSCROLL_IND.hot = false;
          this._hscrollShow();
        }
        return;
      }
      if (!HSCROLL_IND.bandIn) {
        HSCROLL_IND.bandIn = true;
        // 进入那一刻重算: 列宽 / 可见列变化后 scrollWidth 可能已变, 陈旧几何在这里被修正
        /* !每次入带都重新解析容器, 不复用 HSCROLL_IND.el: 视图切换后旧容器已 detach,
         * scrollWidth 归零 -> overflow 被误判为假(同源 bug, 一并修掉)。
         * 顺带把 pillW 刷成最新(视口变了轨道宽会变)。 */
        const t = this._hscrollTarget();
        if (t) this._hscrollSync(t.el, t.page);
      }
      const hot = HSCROLL_IND.overflow && this._hscrollInPillSpan(ev);
      if (hot === HSCROLL_IND.hot) return;
      HSCROLL_IND.hot = hot;
      this._hscrollShow();
    },
    /* 可见性单点: 有横向余量 且 (在热区 或 拖拽中 或 横滚召唤中) 才 .on。拖动期间不淡出(D7)。
     * 淡入淡出过渡全由 CSS 给, 这里只切 class。**热区路径不加停留定时器**(D5);
     * 唯一的时间驱动来源是 Shift+滚轮的 1.5s 自落(2026-11-01 用户拍板, 见 _hscrollWheel)。 */
    _hscrollShow() {
      const pill = HSCROLL_IND.pill;
      if (!pill) return;
      const on = HSCROLL_IND.overflow && (HSCROLL_IND.hot || !!HSCROLL_IND.drag || HSCROLL_IND.wheelOn);
      pill.classList.toggle("on", on);
    },
    /* 按下: 落在滑块上 -> 直接拖; 落在轨道其余位置 -> 先把滑块中心移到点击处
     * (标准映射的逆运算), 再进入拖动 —— 点完就能接着拖, 与原生条同手感(D7)。 */
    _hscrollDown(ev) {
      const pill = HSCROLL_IND.pill;
      const el = HSCROLL_IND.el;
      const thumb = HSCROLL_IND.thumb;
      if (!pill || !el || !thumb || !HSCROLL_IND.overflow) return;
      if (ev.button) return;  // 只认主键(右键 / 中键不接管)
      const maxScroll = el.scrollWidth - el.clientWidth;
      if (maxScroll <= 0) return;
      const trackW = pill.clientWidth;
      const thumbW = thumb.offsetWidth;
      const maxThumb = Math.max(0, trackW - thumbW);
      let left = el.scrollLeft;
      const box = pill.getBoundingClientRect();
      const tb = thumb.getBoundingClientRect();
      // 滑块是 pointer-events: none, 事件恒落在轨道上 —— 只能按几何判「点在不在滑块里」
      if (!(ev.clientX >= tb.left && ev.clientX <= tb.right)) {
        const ratio = maxThumb > 0 ? (ev.clientX - box.left - thumbW / 2) / maxThumb : 0;
        el.scrollLeft = Math.max(0, Math.min(1, ratio)) * maxScroll;
        left = el.scrollLeft;
      }
      HSCROLL_IND.drag = { id: ev.pointerId, x: ev.clientX, left, maxThumb, maxScroll };
      pill.classList.add("drag");
      if (pill.setPointerCapture) pill.setPointerCapture(ev.pointerId);
      this._hscrollShow();  // .drag 已置 -> 即便此刻热区判定为假也保持可见
      ev.preventDefault();
    },
    /* 拖动: ΔclientX 反算 scrollLeft(标准映射的逆运算)。**不手工调 syncHeadScroll** ——
     * 程序化写 scrollLeft 同样触发原生 scroll 事件, 表头位移 / --head-pin-x / is-hscrolled 照常同步;
     * 手工再调一次 = 双份逻辑, 迟早漂移(R2)。 */
    _hscrollMove(ev) {
      const d = HSCROLL_IND.drag;
      const el = HSCROLL_IND.el;
      if (!d || !el || ev.pointerId !== d.id) return;
      if (!d.maxThumb) return;  // 滑块占满轨道 = 无处可拖
      el.scrollLeft = d.left + ((ev.clientX - d.x) / d.maxThumb) * d.maxScroll;
    },
    /* 抬起 / 取消: 摘 .drag、释放 capture, 然后**重新**按热区判定是否保留 .on ——
     * 抬起时指针很可能已经离开热区(拖到视口外 / 向下滑出), 沿用旧 hot 会让胶囊留在屏上。 */
    _hscrollUp(ev) {
      const d = HSCROLL_IND.drag;
      if (!d || ev.pointerId !== d.id) return;
      HSCROLL_IND.drag = null;
      const pill = HSCROLL_IND.pill;
      if (pill) {
        pill.classList.remove("drag");
        if (pill.hasPointerCapture && pill.hasPointerCapture(ev.pointerId)) pill.releasePointerCapture(ev.pointerId);
      }
      /* 抬起后重判热区: 拖到视口外再松手时指针往往已不在带内, 沿用旧 hot 会让胶囊留在屏上。
       * 纵向按带判(不含状态栏); 横向**不再判胶囊邻域** —— 刚拖完手可能停在轨道两端之外,
       * 那时摘掉会显得"一松手就没了", 交给下一次 mousemove 按正常判据收。 */
      const inBand = this._hscrollBand(ev);
      HSCROLL_IND.bandIn = inBand;
      HSCROLL_IND.hot = inBand && HSCROLL_IND.overflow;
      this._hscrollShow();
    },
    /* 照 _ensureHeadObserver 的范式(本文件 L186 一带): 只观察当前主表容器, 元素换了才重挂;
     * 回调 rAF 合并(同一帧多次变化只重算一次); 无 ResizeObserver 时降级为不挂 ——
     * 此时容器盒变化仍会在下一次进入热区(②)或容器 scroll(①)时被修正。 */
    _hscrollObserve(el) {
      if (typeof ResizeObserver === "undefined") return;
      if (el === HSCROLL_IND.roEl) return;  // 元素没换: 什么都不做(不触发任何布局读取)
      HSCROLL_IND.roEl = el;
      if (HSCROLL_IND.ro) {
        HSCROLL_IND.ro.disconnect();
        HSCROLL_IND.ro = null;
      }
      HSCROLL_IND.ro = new ResizeObserver(() => this._hscrollQueue());
      HSCROLL_IND.ro.observe(el);
    },
    _hscrollQueue() {
      if (HSCROLL_IND.raf) return;  // 同一帧内多次变化合并为一次
      HSCROLL_IND.raf = requestAnimationFrame(() => {
        HSCROLL_IND.raf = 0;
        if (HSCROLL_IND.el) this._hscrollSync(HSCROLL_IND.el, HSCROLL_IND.page);
      });
    },

    /* ------------------------------------------------ 列状态(宽/隐/自适应) */

    _visibleCols(page) {
      const hidden = this.colHidden[page] || [];
      const defs = TABLE_COLUMNS[page];
      const order = this.colOrder[page];
      let out;
      if (!order || !order.length) out = defs.filter((c) => !hidden.includes(c.key));  // 无自定义序 = 定义序(向后兼容)
      else {
        // 按 colOrder 输出; 未入序的列(新增/残留 key)按定义序补尾 —— 宽/隐仍按列 key 对应, 换序不丢宽度
        const rest = new Map(defs.map((c) => [c.key, c]));
        out = [];
        for (const k of order) {
          const c = rest.get(k);
          if (!c) continue;
          rest.delete(k);
          if (!hidden.includes(k)) out.push(c);
        }
        for (const c of defs) if (rest.has(c.key) && !hidden.includes(c.key)) out.push(c);
      }
      return this._colsOmitEmpty(page, out);
    },
    /* 渐进列(U2, 计划 26-10-12-0527 D2): 列定义声明 omitEmpty 的列(07/08 的 qB files 字段
     * —— 随 qB 版本浮动, 原变体口径「无任何对端携带时整列省略」)在**当前所有行都无该字段
     * 值**时整列省略。行来源走描述符 rows(变体表 = dtTplRows → rowsFn; 经典表无 omitEmpty
     * 列, 零开销短路)。行未落袋(加载中)按声明全集保守显示。
     * !放在 _visibleCols 尾部单点: 表头/行/grid 模板/colAlignCss/列选择器全走同一条路,
     *   省略态下 :nth-child 列对齐天然一致(nofiles 9 列错位 bug 类的结构性根除)。 */
    _colsOmitEmpty(page, cols) {
      const def = ALL_TABLE_DEFS[page];
      if (!def || !def.columns.some((c) => c.omitEmpty)) return cols;
      if (typeof this[def.rows] !== "function") return cols;
      let rows = this[def.rows](def.variantTab) || [];
      if (def.segs) rows = rows.flatMap((s) => (s && s.rows) || []);
      if (!rows.length) return cols;
      return cols.filter((c) => !c.omitEmpty || rows.some((r) => r && r[c.key]));
    },
    /* 列模板: 有 px 覆盖用覆盖值, 否则用默认模板(仅首次渲染会出现这种混合态) */
    _gridTemplate(page) {
      const w = this.colWidths[page] || {};
      return this._visibleCols(page).map((c) => w[c.key] || c.tpl).join(" ");
    },
    /* 从列头行(真正的 grid 容器)读取**当前渲染**的列宽 px; 列数不符(渲染未完成)返回 null。
     * !2026-10-18(用户报障「用户表格隐藏一列其它列坍塌」根治): 逐 token 严格校验
     * ^\d+px$ —— display:none 的表头(08 五区分组的折叠组/空组, 表头在 .dt08-rows 内)
     * getComputedStyle 返回的是**指定形**(minmax(170px, 1.6fr) ...), 旧的 parseFloat 兜底
     * 会把 "1.6fr)" 解析成 1.6px 混进宽度表, 全组列宽随即坍成最小宽; 严格校验后这种
     * 量不到的表头只会得到"数量不符 → null"(调用方按未渲染处理), 垃圾值进不了引擎。 */
    _renderedWidths(headEl, page) {
      const rendered = (getComputedStyle(headEl).gridTemplateColumns || "")
        .split(" ")
        .filter((v) => /^\d+(\.\d+)?px$/.test(v))
        .map((v) => parseFloat(v));
      const vis = this._visibleCols(page);
      if (rendered.length !== vis.length) return null;
      const out = {};
      vis.forEach((c, i) => {
        out[c.key] = Math.round(rendered[i]) + "px";
      });
      return out;
    },
    _headEl(page) {
      const def = ALL_TABLE_DEFS[page];
      const ref = def && def.headRef ? this.$refs[def.headRef] : null;
      const el = Array.isArray(ref) ? ref[0] : ref;
      if (el) {
        // 表头现由表壳组件 <aq-table> 渲染(计划 26-10-11-1722 P1): ref 拿到的是**组件实例**,
        // 取它的根元素(单根组件, 即 .group-head / .detail-head); 组件化前 ref 即元素, 原样返回。
        return el.$el || el;
      }
      /* DOM 兜底(计划 26-10-11-2106 W2): 抽屉三表的表头渲染在**页签组件内部**, 子组件模板里的
       * ref 只登记在子组件上 —— 根实例的 $refs 永远取不到它。表壳根自带 data-table(它就是
       * colAlignCss 注入的锚), 故按它查即可。主视图的 ref 路径优先命中, 本条对它们零影响;
       * 抽屉未打开 / 该页签未激活时查不到 -> 返回 null(调用方全都已按 null 处理)。 */
      if (!def) return null;
      /* !2026-10-18(用户报障「隐藏一列其它列坍塌」根治, 与 _renderedWidths 严格校验配套):
       * 分段表(08 五区分组)每组一座表头 —— 折叠组(.dt08-rows display:none)与空组
       * (.dt08-hide)里的表头**不可量**: display:none 下 computed grid 保留 minmax 指定形、
       * 格宽实测为 0。旧口径 querySelector 恒取 DOM 首座, 首组恰好折叠/为空时量出垃圾宽度
       * 直接落进引擎(recomputeEffective / 三态排序复位后的现算路径都吃它)。现取**首个有盒
       * (getClientRects 非空)的表头**; 全都不可量返回 null(调用方按未渲染处理, 列宽保持
       * 现状, 不把垃圾值落盘)。主视图的 ref 路径优先命中, 本条对它们零影响。 */
      const found = document.querySelectorAll('.group-head[data-table="' + page + '"]');
      for (const el of found) {
        if (el.getClientRects().length) return el;
      }
      return null;
    },
    /* 列对齐规则注入(单例 <style id="col-align-css">): 首次创建后只改 textContent ——
     * 不能重建元素: 重建会让它排到 <head> 末尾的其它运行时样式之后, 层叠顺序不再稳定。 */
    _syncColAlignCss() {
      const css = this.colAlignCss;
      if (css === this._colAlignCss) return;
      this._colAlignCss = css;
      let el = document.getElementById("col-align-css");
      if (!el) {
        el = document.createElement("style");
        el.id = "col-align-css";
        document.head.appendChild(el);
      }
      el.textContent = css;
    },
    /* 顶栏(+状态分布条)的实测高度写入 :root 的 --head-h: 吸顶元素的偏移与最大可用
     * 高度都依赖它。**不写死数值** —— 高度会随媒体查询、状态条是否渲染、窄屏折行而变化;
     * 值未变时直接返回, 避免每帧都写一次 CSS 变量(updated 会频繁触发)。
     */
    _syncHeadHeight() {
      const el = document.querySelector(".sticky-head");
      const h = el ? Math.round(el.getBoundingClientRect().height) : 0;
      if (h === this._headH) return;
      this._headH = h;
      document.documentElement.style.setProperty("--head-h", h + "px");
    },
    /* P1-3: 用 ResizeObserver 取代"每次渲染量一次顶栏"。
     * - 观察 .sticky-head 的**盒尺寸**: 状态条是否渲染 / 窄屏折行 / 批量段并入都会改高度, 都会被捕获;
     * - 回调用 rAF 合并写入(同一帧多次变化只量一次);
     * - 元素被 v-if 换掉时(引用变化)重新挂观察器并立即量一次 —— 这是唯一仍走同步路径的时机,
     *   而且只在元素真的换了才发生, 不是每帧。
     * 降级: 无 ResizeObserver(很老的浏览器)时退回"每次渲染同步一次", 行为与改动前一致。 */
    _ensureHeadObserver() {
      this._hscrollBind();  // 挂载即绑横滚指示条的文档级监听(自带 bound 守卫); 必须早于下方早退分支
      if (typeof ResizeObserver === "undefined") {
        this._syncHeadHeight();
        return;
      }
      const el = document.querySelector(".sticky-head");
      // 字段名不能叫 _headEl: 与下方取表头元素的方法 `_headEl(page)` 同名(data 与 methods 共命名空间)
      if (el === this._headObsEl) return;  // 元素没换: 什么都不做(不触发任何布局读取)
      this._headObsEl = el;
      if (this._headObs) {
        this._headObs.disconnect();
        this._headObs = null;
      }
      if (!el) return;
      this._headObs = new ResizeObserver(() => this._queueHeadSync());
      this._headObs.observe(el);
      this._queueHeadSync();  // 新元素: 立刻量一次拿到初值
    },
    _queueHeadSync() {
      if (this._headRaf) return;  // 同一帧内多次变化合并为一次
      this._headRaf = requestAnimationFrame(() => {
        this._headRaf = 0;
        this._syncHeadHeight();
      });
    },
    /* ---------------- P1-2 行窗口化 ----------------
     * 模板只消费三个产物: 可见切片、上占位高、下占位高。窗口关闭时 == 全量渲染(零差异回退)。
     * 滚动几何按 kind 走窗口源描述符(模块顶 WIN_SOURCES, 计划 26-11-02-0351 W2 参数化):
     * 本节方法体零 window 全局直读(scrollY / innerHeight 都经描述符)。 */
    _winContainer(kind, refName) {
      if (refName) return this.$refs[refName] || null;
      if (kind === "drawerContent") {
        // 抽屉内容桥(W3)的行容器 = 变体锚里的 .group-table(桥模板单点输出; content 页签
        // 同一时刻只有一座桥表在场, 经 dtBridgeTbl 反查当前选中变体的表 id)。锚未挂
        // (抽屉没开 / 非 content 页签)返回 null —— 调用方按「容器未渲染」零差异回退。
        const tid = this.dtBridgeTbl("content");
        return (tid && typeof document !== "undefined")
          ? document.querySelector(`[data-dt-table-anchor="${tid}"] .group-table`)
          : null;
      }
      // 成员行: 容器 = .detail —— 明细表头(注册表 detail.headRef)的父元素。表头组件化后
      // 走 _headEl 取根元素(计划 26-10-11-1722 P1), 不能再直接读 $refs(那是组件实例)。
      const head = this._headEl("detail");
      return head && head.parentElement ? head.parentElement : null;
    },
    /* 行容器的**真实**行间距(px): 三个容器并不相同 —— atlas `.group-table` 是 6px、
     * prism 是 5px、成员容器 `.detail` 是块级容器(没有 flex gap = 0)。硬编码任何一个值
     * 都会让另外两层的占位总高失真, 所以一律读计算样式实测(见文件头 BUG-1 注释)。
     * 块级容器的 rowGap 计算值是 "normal" ⇒ parseFloat 得 NaN ⇒ 回落 0, 正是我们要的值。
     * !返回 **null = 容器当前没渲染**(如种子页未打开时问 .group-table) —— 调用方**不得**
     * 把它当 0 缓存: 否则在分组页问一次就把种子页的间距永久记成 0(实测占位总高少 5px×2999)。 */
    _winGapOf(kind) {
      // 容器 ref 由注册表给(group/torrent 有 tableRef; member 无 -> null, 走 .detail 父容器)
      const def = TABLE_DEFS[kind];
      const el = this._winContainer(kind, def ? def.tableRef : null);
      if (!el) return null;
      if (typeof getComputedStyle !== "function") return ROW_WIN_GAP_FALLBACK;
      const g = parseFloat(getComputedStyle(el).rowGap);
      return Number.isFinite(g) ? g : 0;
    },
    /* 取该层的行间距(带缓存)。容器未渲染时返回 null, 由调用方决定回退策略。 */
    _winGapFor(kind) {
      if (this._winGap[kind] === undefined) {
        const g = this._winGapOf(kind);
        if (g === null) return null;
        this._winGap[kind] = g;
      }
      return this._winGap[kind];
    },
    _winSigExtra() {
      // 会改变"容器上方内容高度"的因子: 状态分布条是否渲染 / 搜索态 / 筛选态
      return `${this.distTotal ? 1 : 0}${this.searchQuery && this.searchQuery.trim() ? 1 : 0}${this.filtersActive ? 1 : 0}`;
    },
    /* 窗口源描述符解析(计划 26-11-02-0351 W2): kind 未注册回落文档型 —— 描述符缺失 = 现行为。 */
    _winSrc(kind) {
      return WIN_SOURCES[kind] || WIN_SRC_DOC;
    },
    /* ---------------- 容器型滚动源的引擎态(W3 接线, 计划 26-11-02-0351) ----------------
     * 与文档型 _winScrollY/_winViewH **分家**, 不共用一对: 主表与抽屉同屏可见(停靠面板),
     * 两个滚动源是两套坐标系 —— 抽屉滚一把就把文档对写掉, 主表窗口(轮询每拍按 _winScrollY
     * 重算)跟着漂移。容器态惰性建一次; Vue.reactive 让滚动写回能触发桥模板重渲(node 探针
     * 无 Vue 时退化普通对象 —— 电池只验证几何, 不验证响应式)。 */
    _winCtnState() {
      if (!this._winCtn) {
        const V = typeof window !== "undefined" ? window.Vue : null;
        this._winCtn = (V && typeof V.reactive === "function") ? V.reactive({ y: 0, h: 0 }) : { y: 0, h: 0 };
      }
      return this._winCtn;
    },
    /* 容器几何写回单点: scroll 事件(rAF 合帧后)与键盘跨窗滚动(W3 dtWinKbd)都走这里。
     * 几何读取 = 强制同步布局, 故只挂两处低频口(事件拍/按键), 不进渲染路径。宽度变化另
     * bump _winResize(行高随列宽变, 需一轮全量重量) —— 高度动画(抽屉抽成一条再撑回)不 bump,
     * 否则开抽屉动画每帧都付一次千行全量渲染。 */
    _winCtnSync() {
      if (typeof document === "undefined") return;
      // 收场期(drawer.open 已翻 false, 面板还在 leave 动画)的 .drawer-body 宽度**不可采信**:
      // .drawer-leave-active 转 absolute 出流(三皮肤 dialogs.css), clientWidth 实测跳 1894->1918
      // —— 采信就假 bump _winResize, 而那是与主表**共用**的宽度代, 下一拍 updated 钩子的
      // _measureRowH 按签名失配把主表行高全表作废, 3000 行下走一轮全量重渲(实测 5.5s 长任务,
      // 用户所见「关抽屉后卡死几秒; 能滚不能点」—— 滚轮走合成器不进主线程, 鼠标事件被长任务饿死)。
      // 真重开会经 _ensureWinCtnBind 重新绑定并 sync, 此处短路不丢状态。
      if (!this.drawer || !this.drawer.open) return;
      const el = document.querySelector(".drawer-body");
      if (!el) return;
      const st = this._winCtnState();
      st.y = el.scrollTop;
      st.h = el.clientHeight;
      if (this._winCtnW !== undefined && Math.abs(el.clientWidth - this._winCtnW) > 0.5) this._winResize++;
      this._winCtnW = el.clientWidth;
    },
    _onWinCtnScroll() {
      if (this._winRafC) return;
      this._winRafC = requestAnimationFrame(() => {
        this._winRafC = 0;
        this._winCtnSync();
      });
    },
    /* 容器滚动监听惰性绑定: 文档型的挂载单点在 lifecycle.js mounted(window 监听, 常驻),
     * 容器型的滚动源 .drawer-body 是动态元素 —— 每轮签名检查时按元素引用比对, 换了就摘旧
     * 挂新(ResizeObserver 随 bindScroll/unbindScroll 成对重挂); 抽屉从未打开就永不绑定。
     * 绑定后立即 _winCtnSync 写回初值 —— 不等第一次滚动/尺寸事件, 否则开抽屉后窗口在用户
     * 滚动前不激活。 */
    _ensureWinCtnBind() {
      if (typeof document === "undefined") return;
      const el = document.querySelector(".drawer-body");
      if (this._winCtnBoundEl === el) return;
      const src = this._winSrc("drawerContent");
      if (this._winCtnBoundEl) src.unbindScroll(this._onWinCtnScroll);
      this._winCtnBoundEl = el || null;
      if (!el) return;
      src.bindScroll(this._onWinCtnScroll);
      this._winCtnW = undefined;  // 新容器: 宽度基线重建(绑定拍不 bump)
      this._winCtnSync();
    },
    /* 容器顶边相对滚动内容顶的偏移(按 kind 走描述符): 只在签名变化时读一次(getBoundingClientRect
     * = 强制同步布局, 每帧读会把 P1-3 的收益又吐回去)。签名含 lastRid ⇒ 每轮数据最多读一次。 */
    _ensureWinTop() {
      this._ensureWinCtnBind();  // 容器型滚动源惰性绑定(元素引用比对, 常态零开销)
      const base = `${this.viewMode}|${this.page}|${this._winResize}|${this._winSigExtra()}|${this.lastRid}`;
      for (const kind of ["torrent", "group", "member", "drawerContent"]) {
        const sig = `${base}|${kind}`;
        if (this._winTopSig[kind] === sig) continue;
        const def = TABLE_DEFS[kind];
        const el = this._winContainer(kind, def ? def.tableRef : null);
        this._winTop[kind] = el ? this._winSrc(kind).topOffset(el) : 0;
        this._winTopSig[kind] = sig;
      }
    },
    /* 行高: **逐行实测**(不是采样几行取均值)。行高本就不齐(带 H&R 要求的行多一行),
     * 用"等高"近似会在几千行上累积成上百像素漂移 —— 表现为滚到底够不着、滚动条长度不对。
     * 首次(或列集合变化后)由一轮**全量渲染**量齐所有行, 之后每轮只更新当前窗口里的行。 */
    _measureRowH() {
      if (!this.rowWin) return;
      // 签名取三个有窗口的层(与 _rowWindow 的 kind 对齐; 顺序 group/torrent/detail 与旧字面量一致)
      const winDefs = [TABLE_DEFS.group, TABLE_DEFS.torrent, TABLE_DEFS.detail];
      // !签名不含 viewMode(2026-11-02 关抽屉/切页卡死取证): 三 kind 行宽几何都不随 viewMode 变
      // —— 列集合由 colcounts 因子独立盯住、视口宽由 _winResize 盯住, 行本身只在固定列集的
      // 同宽表区渲染。旧签名含 viewMode = 每次切页把三 kind 行高全表作废 + _winMeasured 翻 false
      // ⇒ 下一轮 _rowWindow 走全量渲染量齐, 3000 行实测 5.9~8.4s 长任务(切页卡死的根因)。
      const sig = `${this._winResize}|${winDefs.map((d) => this[d.cols].length).join("|")}`;
      // !用 getBoundingClientRect().height 而不是 offsetHeight: 后者取整, 0.4px 的误差 ×
      // 3000 行就是 1200px 的漂移。
      const probes = [["torrent", ".torrent-row[data-hash]"], ["group", ".group-row:not(.torrent-row)[data-key]"], ["member", ".member-row[data-hash]"]];
      for (const [kind, sel] of probes) {
        if (this._rowHSig[kind] !== sig) {
          // 列集合/窗口宽变了: 旧高度作废, 下一轮走全量重新量齐(只多付一次全量渲染)
          for (const k of Object.keys(this._rowHs)) {
            if (k.startsWith(kind + ":")) delete this._rowHs[k];
          }
          this._rowHSig[kind] = sig;
          this._winMeasured[kind] = false;
          this._rowHVer++;
          continue;
        }
        const rows = document.querySelectorAll(sel);
        if (!rows.length) continue;
        let sum = 0, changed = false;
        for (const r of rows) {
          const h = r.getBoundingClientRect().height;
          const key = kind + ":" + (r.getAttribute("data-hash") || r.getAttribute("data-key") || "");
          if (this._rowHs[key] === undefined || Math.abs(this._rowHs[key] - h) > 0.5) {
            this._rowHs[key] = h;
            changed = true;
          }
          sum += h;
        }
        const avg = sum / rows.length;  // 未量过的行(新种子)用它兜底
        if (this._rowH[kind] === undefined || Math.abs(this._rowH[kind] - avg) > 0.01) {
          this._rowH = { ...this._rowH, [kind]: avg };
          changed = true;
        }
        if (!this._winMeasured[kind]) {
          this._winMeasured[kind] = true;  // 这一轮是全量渲染, 高度已量齐
          changed = true;
        }
        if (changed) this._rowHVer++;  // 响应式: 让窗口按新高度重算
      }
      // 抽屉内容桥(第四探测位, 计划 26-11-02-0351 W3): 行高逐行实测同法。选择器不能裸扫
      // .group-row[data-dt-key] —— 桥行都带该属性, 合并态同屏还有 peers/trackers 的桥行;
      // 按当前在场变体锚现拼(同 kind 两变体 V10/V11 同时只有一座在场), 行键 = data-dt-key
      // (rowKey "k" 的值, 与 _rowKeyOf 的描述符 keyOf 同源)。签名 = 窗宽代 + 可见列数。
      const dtDefs = (typeof window !== "undefined" && window.AQB_DRAWER_TPL_DEFS) || {};
      for (const tid of Object.keys(dtDefs)) {
        const ddef = dtDefs[tid];
        if (ddef.window !== "drawerContent" || ddef.segs) continue;  // segs 描述符显式不接窗
        if (this.dtBridgeTbl(ddef.variantTab) !== tid) continue;     // 未选中/未在场: 不量
        const dcols = (this[ddef.cols] || []).length;
        const sigD = `${this._winResize}|${dcols}`;
        if (this._rowHSig["drawerContent"] !== sigD) {
          // 列集合/窗口宽变了: 旧高度作废, 下一轮走全量重新量齐(只多付一次全量渲染)
          for (const k of Object.keys(this._rowHs)) {
            if (k.startsWith("drawerContent:")) delete this._rowHs[k];
          }
          this._rowHSig["drawerContent"] = sigD;
          this._winMeasured["drawerContent"] = false;
          this._rowHVer++;
          continue;
        }
        const block = typeof document === "undefined" ? null
          : document.querySelector(`[data-dt-table-anchor="${tid}"] .group-table`);
        const drows = block ? block.querySelectorAll(".group-row[data-dt-key]") : [];
        if (!drows.length) continue;
        let dsum = 0, dChanged = false;
        for (const r of drows) {
          const h = r.getBoundingClientRect().height;
          const key = "drawerContent:" + (r.getAttribute("data-dt-key") || "");
          if (this._rowHs[key] === undefined || Math.abs(this._rowHs[key] - h) > 0.5) {
            this._rowHs[key] = h;
            dChanged = true;
          }
          dsum += h;
        }
        const davg = dsum / drows.length;  // 未量过的行(新种子)用它兜底
        if (this._rowH["drawerContent"] === undefined || Math.abs(this._rowH["drawerContent"] - davg) > 0.01) {
          this._rowH = { ...this._rowH, drawerContent: davg };
          dChanged = true;
        }
        if (!this._winMeasured["drawerContent"]) {
          this._winMeasured["drawerContent"] = true;  // 这一轮是全量渲染, 高度已量齐
          dChanged = true;
        }
        if (dChanged) this._rowHVer++;
      }
    },
    /* 行键提取按 kind 走描述符(计划 26-11-02-0351 W2): 主表 = item.hash / group = item.key
     * (WIN_SRC_DOC.keyOf 与 group 覆盖); 抽屉行(W3 接线)两者皆无, 键字段名由该 kind 的
     * 描述符给(如 rowKey 字段 "k" 的值)。未注册 kind 回落文档型 = 现行为。 */
    _rowKeyOf(kind, item) {
      return kind + ":" + this._winSrc(kind).keyOf(item);
    },
    /* 前缀和 y(i) = 第 i 行的顶边偏移(含行间距)。每帧重算: 3000 次加法 ≈ 0.03ms,
     * 比维护"失效缓存 + 增量更新"简单得多, 也不会因为漏失效而算错。 */
    _rowWindow(kind, list, refName) {
      const n = list.length;
      const off = { active: false, start: 0, end: n, padTop: 0, padBottom: 0 };
      void this._rowHVer;  // 依赖: 行高表更新后重算
      // 滚动几何按**源族**分流(计划 26-11-02-0351 W3): 文档型 = 主表三 kind 共用一对
      // _winScrollY/_winViewH; 容器型 = 抽屉 .drawer-body 自己一对(_winCtnState)。
      // 两套坐标系混用会让主表窗口跟着抽屉滚动漂移(主表与抽屉同屏可见)。
      const doc = this._winSrc(kind) === WIN_SRC_DOC;
      const st = doc ? null : this._winCtnState();
      const sy = doc ? this._winScrollY : st.y;
      const vh = doc ? this._winViewH : st.h;
      if (!this.rowWin || n < ROW_WIN_MIN || vh <= 0) return off;
      // 行高还没量齐 -> 这一轮先全量渲染(首轮/改列之后各一次), 下次就走窗口了
      if (!this._winMeasured[kind]) return off;
      const est = this._rowH[kind] || ROW_WIN_EST_H[kind];
      // 行间距实测(见 _winGapFor); 容器还没渲染时本轮先全量, 免得按错的间距撑占位
      const gap = this._winGapFor(kind);
      if (gap === null) return off;
      const hs = this._rowHs;
      const pre = new Array(n + 1);
      pre[0] = 0;
      let y = 0;
      for (let i = 0; i < n; i++) {
        const h = hs[this._rowKeyOf(kind, list[i])];
        y += (h === undefined ? est : h) + gap;
        pre[i + 1] = y;
      }
      // 前缀和留存(计划 26-09-28-0354 W2): 键盘光标滚到窗口化未渲染行时按它换算文档 y
      // (shortcuts.js _kbScrollRowIntoView)。纯缓存, created 里初始化, 不进 data。
      this._rowPre[kind] = pre;
      const rel = sy - (this._winTop[kind] || 0);
      let start = this._prefixFloor(pre, rel) - ROW_WIN_OVERSCAN;
      let end = this._prefixFloor(pre, rel + this._winViewH) + 1 + ROW_WIN_OVERSCAN;
      if (!(start >= 0) || start > n) start = 0;
      if (!(end > 0) || end > n) end = n;
      if (start >= end) return off;  // 数值异常: 宁可全渲染, 也不渲染"空窗口"
      // 占位两侧各多出一个 gap(顶替了行块内部原有的间距), 故减一个 gap 对齐
      return {
        active: true, start, end,
        padTop: start > 0 ? pre[start] - gap : 0,
        padBottom: end < n ? pre[n] - gap - pre[end] : 0,
      };
    },
    _prefixFloor(pre, y) {
      // 最大的 i 使 pre[i] <= y(pre 单调不减, 二分)
      let lo = 0, hi = pre.length - 1;
      while (lo < hi) {
        const mid = (lo + hi + 1) >> 1;
        if (pre[mid] <= y) lo = mid;
        else hi = mid - 1;
      }
      return lo;
    },
    /* 滚动/resize 的合帧写回: 几何一律经文档型描述符读(WIN-SOURCES 段是唯一直读点)。
     * 容器型 kind(W3 接线)的事件路径由其描述符 bindScroll 挂到容器元素上, 写回同一对引擎态。 */
    _onWinScroll() {
      if (this._winRaf) return;
      this._winRaf = requestAnimationFrame(() => {
        this._winRaf = 0;
        this._winScrollY = WIN_SRC_DOC.scrollY();
      });
    },
    _onWinResize() {
      this._winResize++;
      this._winViewH = WIN_SRC_DOC.viewH();
      this._winScrollY = WIN_SRC_DOC.scrollY();
    },
    /* 模板用: 成员行切片(展开明细)。窗口未启用时原样返回, 与改动前完全等价 */
    winMembers(list) {
      const rows = this.sortedMembers(list);
      const w = this.memberWin(list);
      return w.active ? rows.slice(w.start, w.end) : rows;
    },
    /* 生效宽度现算(双轨模型的"生效轨", plan 26-09-21-1551 §3.1):
     * - 全自动页(colW 为空) -> 每次窗口变化后按当前渲染实测(保留"填满容器 + 自适应"的观感)
     * - 固化页(colW 非空)   -> 用意图值(冻结, 拖一列不再动其它列)
     * !只写易变态 colWidths, **绝不落盘** —— persistPage 只收意图(colHidden/colOrder/colW),
     *   "派生值没有资格落盘"是双轨模型唯一铁律(守阵 test_frontend_persist_page_takes_intent_only)。
     */
    recomputeEffective() {
      for (const page of ALL_TABLE_PAGES) {
        if (this.colW[page]) {
          this.colWidths = { ...this.colWidths, [page]: { ...this.colW[page] } };
          continue;
        }
        const headEl = this._headEl(page);
        if (!headEl) continue;
        const widths = this._renderedWidths(headEl, page);
        if (widths) this.colWidths = { ...this.colWidths, [page]: widths };
      }
    },

    /* 空存储提示(W4 origin 隔离 + W5 浏览器"关闭时清除站点数据"): 本 origin 没有列偏好记录时
     * 记一次 —— 进**通知面板**(状态栏铃铛, 未读徽标)而不是页面浮层。
     * !出口口径(2026-10-09 用户实报): 早期版本运行时往 body 里插一条 fixed 横幅, 它压在页面内容上,
     *   且**每次自动化测试都触发**(测试用全新浏览器上下文 ⇒ 没有"已提示"去重标记), 把每张截图都
     *   盖掉一截。改为只进通知面板(ui_feedback.js::_recordNotice): 面板默认收起, 不占版面、
     *   不进截图, 入口徽标提示"有话要说"。文案本身一字不改 —— 陈述事实与排查路径的价值不变。
     *
     * !为什么只陈述"本地址没有偏好记录"、不做精确判定(2026-09-24 取证): 站点级"关闭窗口时清除
     * Cookie 和站点数据"(Chromium cookie 例外 setting=4 = SESSION_ONLY)会在关浏览器时把该 host 的
     * Cookie 与 localStorage **一起**清掉 ⇒ "被清过"与"首次访问"在客户端**完全同形**: 任何能当跨会话
     * 记忆用的东西(包括本函数的"已提示"标记)都躺在被清掉的那份数据里, 没有服务端就无法区分。
     * 故这里给"事实 + 两种成因 + 自查路径", 不下结论(取证: Edge/Chrome 的 cookie 例外里都有
     * `127.0.0.1,*` setting=4, 于是"浏览器重启后偏好全回默认"被当成应用 bug 追了多轮)。 */
    _showColsOriginHint() {
      if (this._colsOriginHintShown) return;
      this._colsOriginHintShown = true;
      // 同一次标签会话只记一次: 清站点数据的环境下 localStorage 里的"已提示"标记也一起没了,
      // 只靠它会在每次关浏览器重开后又记一条; sessionStorage 随标签关闭失效, 正好只兜"同一次会话"。
      try {
        if (sessionStorage.getItem(COLS_ORIGIN_HINT_KEY)) return;
        sessionStorage.setItem(COLS_ORIGIN_HINT_KEY, "1");
      } catch { /* 私隐模式等: 退回下面 localStorage 那层标记 */ }
      try {
        if (localStorage.getItem(COLS_ORIGIN_HINT_KEY)) return;
        localStorage.setItem(COLS_ORIGIN_HINT_KEY, "1");
      } catch { /* 私隐模式: 写失败也继续记, 本会话内由 _colsOriginHintShown 挡住 */ }
      this._recordNotice(
        "本地址还没有列偏好记录。常见成因: 1. 偏好按站点隔离存储, 换地址/端口"
        + "(127.0.0.1 ↔ localhost、38080 ↔ 38081)各存一份; 2. 浏览器在本地址上开了"
        + "「关闭窗口时清除 Cookie 和站点数据」→ 每次关掉浏览器偏好都会回默认"
        + "(Edge 可在 edge://settings/content/all 里查该地址)。可固定用同一地址, "
        + "或改用 http://localhost:<端口> 打开。"
      );
    },

    /* 唯一持久化漏斗(plan 26-09-21-1551 §3.4): 全仓对 COLS_STORE_KEY 的 setItem **只允许这一处**
     * (静态守阵钉住)。写 v5 按页子树: 以存储为底(RMW, 防"同一毫秒两边写"), 只覆盖本次涉及的
     * page, 其余 page 取存储最新值。!只收意图态(colHidden/colOrder/colW) —— 生效宽度 colWidths
     * 是按窗口现算的派生值, 到不了这里; 旧模型"先存后算/先算后存"的顺序约束在本模型下不存在
     * (派生根本不在持久化路径上)。 */
    persistPage(page) {
      const prev = readColStateRaw();
      const base = prev && prev.pages && typeof prev.pages === "object"
        ? { v: 5, origin: location.origin, pages: { ...prev.pages } }
        : { v: 5, origin: location.origin, pages: {} };
      base.pages[page] = {
        hidden: this.colHidden[page] || [],
        order: this.colOrder[page] || [],
        w: this.colW[page] || null,
      };
      // 写失败(私隐模式/配额满)不得影响功能: 本次会话内的调整仍在内存里生效
      try {
        localStorage.setItem(COLS_STORE_KEY, JSON.stringify(base));
      } catch { /* 忽略: 仅失去跨会话记忆 */ }
    },
    /* 跨标签同步(F2): 别的标签改了列 -> 本标签**整份采用**存储里的意图(与"刷新一次"等价)。
     * 双轨模型下采纳永远安全: 采纳的是纯意图, 生效宽度随后由 recomputeEffective 按本窗口现算,
     * 不存在"采纳了别的窗口算出的 px"这回事。不做逐列合并 —— 那需要给每段加"谁更新"的时间戳
     * 语义, 代价远大于收益(同页同秒并发仍最后写赢, 固有且可接受)。
     * !调用方只能是 storage 事件(它**只在其它标签**触发, 写入方自己收不到, 故无需去重)
     *   与 visibilitychange 的"回到可见"分支(补漏: 标签被冻结 / 事件丢失)。 */
    adoptColState() {
      const next = loadColState();
      this.colHidden = next.hidden;
      this.colOrder = next.order;
      this.colW = next.w;
      this.$nextTick(() => this.recomputeEffective());
    },
    colVisible(page, key) {
      return !(this.colHidden[page] || []).includes(key);
    },
    toggleColumn(page, key) {
      const col = columnDef(page, key);
      if (!col || col.locked) return;  // locked 列不可隐藏(模板中不渲染其勾选框, 这里是双保险)
      const cur = this.colHidden[page] || [];
      const hidden = cur.includes(key) ? cur.filter((k) => k !== key) : [...cur, key];
      this.colHidden = { ...this.colHidden, [page]: hidden };
      // 固化页: 新显示的列需要一个 px 宽度才能维持"只改一列"的策略(全自动页交给现算)
      if (this.colW[page] && !hidden.includes(key)) {
        const w = { ...(this.colW[page] || {}) };
        if (!w[key]) {
          w[key] = templateMinPx(col.tpl) + "px";
          this.colW = { ...this.colW, [page]: w };
        }
      }
      this.persistPage(page);
      this.$nextTick(() => this.recomputeEffective());
    },
    resetAllColumnWidths(page) {
      // 恢复默认列宽: 清空意图宽度(w=null) -> 回全自动, 该页重新随窗口自适应
      this.colW = { ...this.colW, [page]: null };
      this.colWidths = { ...this.colWidths, [page]: {} };  // 立即回弹性模板, 下一帧按新渲染实测
      this.persistPage(page);
      this.$nextTick(() => this.recomputeEffective());
    },
    fitColumnsToWindow(page) {
      // 适应窗口宽度(2026-09-21 D2 拍板): 回**全自动** —— 清空意图宽度与生效覆盖, 让默认弹性
      // 模板重新填满容器, 且此后继续随窗口自适应。旧实现把"当前窗口算出的快照"固化为偏好,
      // 正是"派生值当意图"的残留(换窗口即过拟合); 想固定某一列 -> 拖它(见 startResize)。
      this.colW = { ...this.colW, [page]: null };
      this.colWidths = { ...this.colWidths, [page]: {} };
      this.persistPage(page);
      this.$nextTick(() => this.recomputeEffective());
    },
    /* 列选择器底部两个动作的"全表"入口(计划 26-10-11-1722 P4): 遍历注册表, 取代模板里逐页手写的
     * 四条调用(加一张表不用再改模板)。W2 起取**全集** —— 列选择器既然列出抽屉三表的列, 两个
     * "全表"动作就必须覆盖它们, 否则会出现"能勾选但恢复不了"的半截能力(见 computed `tableDefs`)。 */
    resetAllColumnWidthsAll() {
      for (const page of ALL_TABLE_PAGES) this.resetAllColumnWidths(page);
    },
    fitColumnsToWindowAll() {
      for (const page of ALL_TABLE_PAGES) this.fitColumnsToWindow(page);
    },

    /* 列宽拖拽: 拖某列**只改该列**
     *
     * 关键在于起始时把**全部可见列**固化为当前渲染 px —— 它们原本可能是 minmax/fr 弹性值,
     * 不固化的话被拖列会把余量从邻居那儿抢走(表现为"调一列, 其它列跟着变")。
     * 按住 Shift 拖拽 = 与相邻列互相挤占(总宽不变), 对应主流表格的 shift-resize。
     *
     * 拖拽抑制误触排序: resizer 与 .h-cell 共父级, mouseup 后浏览器仍派发 click 冒泡到
     * .h-cell 触发 setSort(用户感知为"调列宽顺手把排序变了")。这里累计位移超过阈值时,
     * 在 capture 阶段拦截下一次 click(stopPropagation+preventDefault), 拦完即注销。
     * 未拖动(纯点击 resizer)不拦截, 保持原行为。
     */
    startResize(event, page, key) {
      const headEl = event.target.closest(".group-head") || event.target.closest(".detail-head");
      if (!headEl) return;
      const widths = this._renderedWidths(headEl, page);
      if (!widths) return;
      const vis = this._visibleCols(page);
      const idx = vis.findIndex((c) => c.key === key);
      if (idx < 0) return;
      const startX = event.clientX;
      const startVal = parseFloat(widths[key]);
      const neighbor = event.shiftKey ? vis[idx + 1] : null;
      const startNeighbor = neighbor ? parseFloat(widths[neighbor.key]) : 0;
      let dragged = false;  // 位移超过 RESIZE_DRAG_THRESHOLD 即置真, up 时用于决定是否拦 click
      let lastWidths = null;  // 拖拽中的最新整页 px(up 时升格为意图)
      const move = (e) => {
        if (!dragged && Math.abs(e.clientX - startX) > RESIZE_DRAG_THRESHOLD) dragged = true;
        const w = Math.max(MIN_COL_PX, Math.round(startVal + e.clientX - startX));
        const next = { ...widths, [key]: `${w}px` };
        if (neighbor) {
          next[neighbor.key] = `${Math.max(MIN_COL_PX, Math.round(startNeighbor - (w - startVal)))}px`;
        }
        this.colWidths = { ...this.colWidths, [page]: next };  // 只动生效态, 意图在 up 时一次性升格
        lastWidths = next;
      };
      const up = () => {
        document.removeEventListener("mousemove", move);
        document.removeEventListener("mouseup", up);
        // 意图升格: 以既有 colW 为底 merge(!隐藏列的 px 在这里保住 —— 渲染快照只含可见列,
        // 旧实现整段替换正是"隐藏列宽度被抹"的根因), 再叠本次拖拽终值; 整页自此固化
        const intent = { ...(this.colW[page] || {}), ...widths, ...(lastWidths || {}) };
        this.colW = { ...this.colW, [page]: intent };
        this.persistPage(page);
        this.$nextTick(() => this.recomputeEffective());
        if (!dragged) return;  // 未拖动 = 纯点击 resizer, 不拦 click(保持原行为)
        // 拖拽尾处浏览器会冒泡一次 click 到 .h-cell 触发 setSort —— capture 阶段拦掉即停
        const swallow = (ev) => {
          ev.stopPropagation();
          ev.preventDefault();
          document.removeEventListener("click", swallow, true);
        };
        document.addEventListener("click", swallow, true);
      };
      document.addEventListener("mousemove", move);
      document.addEventListener("mouseup", up);
    },
    /* 双击分隔线 = 按内容自适应宽度(表头 + 当前已渲染行), 夹在 [最小宽, MAX_FIT_PX] */
    autoFitColumn(event, page, key) {
      const headEl = event.target.closest(".group-head") || event.target.closest(".detail-head");
      if (!headEl) return;
      const vis = this._visibleCols(page);
      const idx = vis.findIndex((c) => c.key === key);
      if (idx < 0) return;
      const container = headEl.parentElement;
      const rowSel = page === "detail" ? ".member-row" : ".group-row";
      let max = headEl.children[idx] ? headEl.children[idx].scrollWidth : MIN_COL_PX;
      for (const row of container.querySelectorAll(rowSel)) {
        const cell = row.children[idx];
        if (cell) max = Math.max(max, cell.scrollWidth);
      }
      const width = Math.min(MAX_FIT_PX, Math.max(MIN_COL_PX, Math.ceil(max) + 18));
      const widths = this._renderedWidths(headEl, page) || {};
      // 意图升格: 以既有 colW 为底 merge(隐藏列 px 保住, 同 startResize), 再叠可见列冻结 + 本列适配备
      const intent = { ...(this.colW[page] || {}), ...widths, [key]: `${width}px` };
      this.colW = { ...this.colW, [page]: intent };
      this.colWidths = { ...this.colWidths, [page]: { ...intent } };  // 同步生效态, 免一帧跳变
      this.persistPage(page);
    },

    /* ------------------------------------------------ 列序(表头拖动重排 TBL-05) */

    /* 当前生效的全列序(可见+隐藏): colOrder 优先, 未入序的列(新增/残留)按定义序补尾 */
    _orderedKeys(page) {
      const defs = TABLE_COLUMNS[page].map((c) => c.key);
      const order = this.colOrder[page];
      if (!order || !order.length) return [...defs];
      const head = order.filter((k) => defs.includes(k));
      return [...head, ...defs.filter((k) => !head.includes(k))];
    },

    /* 落点换算: dropIdx 是**可视列空间**的插入边界(表头只渲染可见列), 存储的 colOrder 是
     * **全序列**(含隐藏列) —— 移除自身后按"第 b 个可见列之前"折算插入点, 隐藏列的相对
     * 次序不动(之后取消隐藏时插回原相对位)。落库后下一帧 recomputeEffective 重算生效宽度。 */
    applyColOrder(page, key, dropIdx) {
      const full = this._orderedKeys(page);
      const vis = full.filter((k) => this.colVisible(page, k));
      const fromVis = vis.indexOf(key);
      if (fromVis < 0 || dropIdx < 0 || dropIdx > vis.length) return;
      const at = dropIdx > fromVis ? dropIdx - 1 : dropIdx;  // 移除自身后的插入边界(可视空间)
      full.splice(full.indexOf(key), 1);
      let inserted = false;
      for (let i = 0, seen = 0; i < full.length; i++) {
        if (!this.colVisible(page, full[i])) continue;
        if (seen++ === at) { full.splice(i, 0, key); inserted = true; break; }
      }
      if (!inserted) full.push(key);  // 边界在末个可见列之后
      this.colOrder = { ...this.colOrder, [page]: full };
      this.persistPage(page);
      this.$nextTick(() => this.recomputeEffective());
    },

    /* 表头拖动重排手势: mousedown 阈值方案(与列宽拖拽 startResize 同款) —— 不用 HTML5
     * draggable, 避免原生拖影/文本选择与"点击排序""列宽拖拽"互相干扰。resizer 的
     * mousedown 已 .stop(不会进到这里); 位移超阈值才进入重排, 释放时若真拖过用 capture
     * 阶段 swallow 拦掉冒泡 click(防误触排序, 同 startResize 手法)。
     * 指示线: head 容器内绝对定位 .col-drop-line(不占 grid 轨道), left 由 move 实时更新。 */
    startColDrag(event, page, key) {
      if (event.button !== 0) return;  // 仅左键; 右键 = openColMenuAt(contextmenu), 中键不劫持
      const headEl = event.target.closest(".group-head") || event.target.closest(".detail-head");
      if (!headEl) return;
      if (this._visibleCols(page).length < 2) return;  // 单列无从重排
      event.preventDefault();  // 抑制表头文本选择(拖拽手势的先决条件; 纯点击不受影响)
      const startX = event.clientX, startY = event.clientY;
      const TH = 6;  // 位移阈值(px): 之内视为普通点击(排序照旧), 超过才进入重排
      const label = (columnDef(page, key) || {}).label || key;  // FX-25 虚影文案
      let dragging = false;
      const cells = () => Array.from(headEl.children).filter((el) => el.classList.contains("h-cell"));
      const move = (e) => {
        if (!dragging) {
          if (Math.abs(e.clientX - startX) <= TH && Math.abs(e.clientY - startY) <= TH) return;
          dragging = true;
          headEl.classList.add("col-dragging");
          document.body.style.cursor = "col-resize";
        }
        const list = cells();
        const base = headEl.getBoundingClientRect();
        let idx = list.length;  // 默认插到末尾之后
        for (let i = 0; i < list.length; i++) {
          const cr = list[i].getBoundingClientRect();
          if (e.clientX < cr.left + cr.width / 2) { idx = i; break; }
        }
        // 指示线落在插入边界的列间隙中线(idx<len 取该列左缘-半间隙; 末尾取末列右缘+半间隙)
        const edge = idx < list.length ? list[idx].getBoundingClientRect().left : list[list.length - 1].getBoundingClientRect().right;
        this.colDrag = { page, key, idx, x: edge - base.left - headEl.clientLeft + (idx < list.length ? -5 : 5) };
        // FX-25: 虚影只更新 x/y(走 transform, 不触发重排); 无虚影时鼠标无处可依, 用户分不清"拖的是什么"
        this.colGhost = { label, x: e.clientX, y: e.clientY };
      };
      const up = () => {
        document.removeEventListener("mousemove", move);
        document.removeEventListener("mouseup", up);
        headEl.classList.remove("col-dragging");
        document.body.style.cursor = "";
        const drag = this.colDrag;
        this.colDrag = null;
        this.colGhost = null;   // FX-25: 松手即消失
        if (!dragging) return;  // 未过阈值 = 普通点击, click 正常冒泡(排序不受影响)
        if (drag && drag.page === page) this.applyColOrder(page, key, drag.idx);
        // 拖拽尾冒泡 click 会触发 setSort(同列释放时) —— capture 阶段拦掉即停(同 startResize)
        const swallow = (ev) => {
          ev.stopPropagation();
          ev.preventDefault();
          document.removeEventListener("click", swallow, true);
        };
        document.addEventListener("click", swallow, true);
      };
      document.addEventListener("mousemove", move);
      document.addEventListener("mouseup", up);
    },

    /* 落点指示线内联样式(仅本 page 的表头渲染; top/height 走 CSS 全高, left 相对 head 盒) */
    colDropLineStyle(page) {
      const d = this.colDrag;
      if (!d || d.page !== page) return {};
      return { left: d.x + "px" };
    },
    /* 成员行(展开明细)窗口: 与 group/torrent 不同, 三个成员窗口都要按"当前展开单元"
     * 的成员数组计算占位 —— 故**带参数**。Vue 3 computed 是无参 getter, 这里必须放
     * methods(否则模板里 memberPadTop(g.members) 触发 this.memberWin 当 getter 调用,
     * 拿到的是对象而不是函数 → "this.memberWin is not a function", 整表就地白屏)。
     * 该 bug 由拆分前的同一段代码继承而来, 之前未塌是因为它走的是追剧页的成员行(整表
     * 不白)还是其它原因未复现, 现在辅种页展开一行即 100% 触发, 必须正名。 */
    memberWin(list) {
      return this._rowWindow("member", list || [], null);
    },
    memberPadTop(list) {
      return this.memberWin(list).padTop;
    },
    memberPadBottom(list) {
      return this.memberWin(list).padBottom;
    },
  },
  computed: {
    /* 表注册表的**有序数组视图**(计划 26-10-11-1722 P4): 列选择器按它 v-for(四段硬编码收敛为一段),
     * 每项 { id, label, columns } —— label 即列选择器的分组标题, columns 即列定义单点。
     * 注册表是模块常量(非响应式), 故本 computed 只在首帧算一次, 引用稳定(不引起重渲染抖动)。
     * !W2 取舍(计划 26-10-11-2106): 取**全集**, 抽屉三表在列选择器里各占一个分组 —— 与计划 §07
     * 的括注("不进 TABLE_PAGES 否则列选择器多出分组")**有意偏差**, 理由: 抽屉表头的右键隐藏
     * (`headMenuHide` -> `toggleColumn`)是**不可逆**操作, 没有选择器这一档就没有恢复入口
     * (只剩改 localStorage)。用户 26-10-11 拍板「以与主视图一致为准则」(D 组 Q2), 故取全集。
     * 计划 §11 变更记录已登记本偏差。 */
    tableDefs() {
      /* 变体表格体(26-10-12-0527): 带 variantTab 的表只在**对应变体被选中**时进选择器
       * (dtBridgeTbl 是 drawer_templates.js mixin 的桥反查; 经典选中时该变体表不出现 ——
       * 八个变体表恒列出会把生产选择器撑爆, 且全部隐藏列无意义)。恢复入口不变式保持:
       * 变体选中期间右键隐藏的列仍可在选择器勾回。 */
      const out = [];
      for (const id of ALL_TABLE_PAGES) {
        const def = ALL_TABLE_DEFS[id];
        if (def.variantTab && this.dtBridgeTbl(def.variantTab) !== id) continue;
        out.push({ id, label: def.label, columns: def.columns });
      }
      return out;
    },
    /* 列模板: computed 缓存(列宽/列显隐变化才变), 行渲染只取同一引用, 不再每行拼字符串 */
    groupGrid() {
      return { gridTemplateColumns: this._gridTemplate("group") };
    },
    detailGrid() {
      return { gridTemplateColumns: this._gridTemplate("detail") };
    },
    torrentGrid() {
      return { gridTemplateColumns: this._gridTemplate("torrent") };
    },
    showGrid() {
      return { gridTemplateColumns: this._gridTemplate("show") };
    },
    /* 变体表格体(计划 26-10-12-0527 U1 stub): 与主视图同一条 _gridTemplate 路径 ——
     * 列宽/列序/隐藏任一变化即换引用; U2 起每变体表一行(声明式追加, 形态同此)。
     * (2026-10-14: 经典三表的 drawerTracker/Peer/FileGrid 随经典渲染链一并退役。) */
    drawerStubV0Grid() {
      return { gridTemplateColumns: this._gridTemplate("drawerStubV0") };
    },
    /* 列对齐规则(R10-08): align 定义在列模型里, 这里按**当前可见列**生成 :nth-child 规则注入 <head>。
     *
     * 为何生成而非在模板里逐格挂类: 值单元格共 67 个 × 4 视图 × 2 套 UI, 逐格挂类必然漏改;
     * 生成则"列模型改一处, 表头与值同源"(表头同样按可见列索引渲染, 顺序天然一致)。
     *
     * 选择器用 :where() 把特异性压到 0,1,0(只剩 :nth-child 那一位), 于是:
     *   - 胜过 .g-stat/.m-stat(0,1,0, 同权重靠源顺序: 注入的 <style> 在样式表之后) -> 非默认对齐生效;
     *   - 与 .h-cell .arrow(0,2,0) 同权, 靠同一套源顺序胜出(见下方箭头 order 规则)。
     * 同时写 text-align 与 justify-content: 值单元格有的是块级文本, 有的是 flex(进度条/
     * 分享率对/芯片组), 只写 text-align 会漏掉后者。
     * 右对齐列的排序箭头取 order:-1 排到标签**左侧**(表头 .h-cell 已是 flex): 否则箭头作为标签的
     * 同行兄弟会把标题整块左顶 11px —— 用户看到的就是"点一下排序, 标题跳一下"。值格没有 .arrow,
     * 不受此规则影响。2026-10-06 起 "0 值居中"(.g-stat.zero/.m-stat.zero) 已删, 0 值格回落本规则注入
     * 的 right, 与同列表头同缘。
     * WARN: **left 也必须生成**: 数值列的值格子带 .g-stat/.m-stat(right), 若因为"left 是默认值"就跳过,
     *    左对齐的口径会被这两条通用规则盖掉(实测: 添加于列表头左、值右)。
     */
    colAlignCss() {
      const out = [];
      // 遍历全集(含抽屉三表, 计划 26-10-11-2106 W2): 对齐规则靠 [data-table] 锚命中表头与值格,
      // 抽屉表头根带 data-table="drawer*"、行容器同挂, 故与主视图同一条注入路径。
      for (const page of ALL_TABLE_PAGES) {
        const cols = this._visibleCols(page);
        for (let i = 0; i < cols.length; i++) {
          const align = cols[i].align || "left";
          const just = align === "right" ? "flex-end" : align === "center" ? "center" : "flex-start";
          out.push(`:where([data-table="${page}"]) > :nth-child(${i + 1}) { text-align: ${align}; justify-content: ${just}; }`);
          if (align === "right") out.push(`:where([data-table="${page}"]) > :nth-child(${i + 1}) .arrow { order: -1; }`);
        }
      }
      return out.join("\n");
    },
    /* ---------------- P1-2 行窗口: 只决定"渲染哪一段", 不参与任何业务语义 ----------------
     * 三个窗口共用 _rowWindow(); 未启用时 win.active=false, 切片 = 全量、上下占位 = 0,
     * 模板与不开窗时完全等价(因此关掉开关就是老行为, 回退路径零成本)。 */
    torrentWin() {
      return this._rowWindow("torrent", this.filteredTorrents, TABLE_DEFS.torrent.tableRef);
    },
    visibleTorrents() {
      const w = this.torrentWin;
      return w.active ? this.filteredTorrents.slice(w.start, w.end) : this.filteredTorrents;
    },
    torrentPadTop() {
      return this.torrentWin.padTop;
    },
    torrentPadBottom() {
      return this.torrentWin.padBottom;
    },
    /* 分组页: **有展开面板时退避** —— .detail 高度不定(含明细表头 + N 行成员), 会让后续行的
     * 位置偏离"第 i 行在 i×step"的假设(硬约束 2.); 此时回退全量渲染, 宁可慢也不能错位。 */
    groupWin() {
      const n = this.filteredGroups.length;
      // !退避判据必须是"**当前真的有面板**", 不能只看 expandedKey 非空: 展开态现在会跨视图带回
      // (切回分组页时原组可能已被删/被筛掉, 见 app.js restoreExpandState), 为一个不存在的面板退避
      // = 大库上永久退化成全量渲染, 且用户完全看不出原因(界面一切正常, 只是滚动变卡)。
      if (this.expandedKey && this.filteredGroups.some((g) => g.key === this.expandedKey)) {
        return { active: false, start: 0, end: n, padTop: 0, padBottom: 0 };
      }
      return this._rowWindow("group", this.filteredGroups, TABLE_DEFS.group.tableRef);
    },
    visibleGroups() {
      const w = this.groupWin;
      return w.active ? this.filteredGroups.slice(w.start, w.end) : this.filteredGroups;
    },
    groupPadTop() {
      return this.groupWin.padTop;
    },
    groupPadBottom() {
      return this.groupWin.padBottom;
    },
    /* 可见列(列选择器只改 colHidden; 顺序取 colOrder(表头拖动重排 TBL-05), 无自定义序时按列定义序) —— 表头/行/grid 模板共用 */
    visibleGroupCols() {
      return this._visibleCols("group");
    },
    visibleDetailCols() {
      return this._visibleCols("detail");
    },
    visibleTorrentCols() {
      return this._visibleCols("torrent");
    },
    visibleShowCols() {
      return this._visibleCols("show");
    },
    /* 变体表格体(26-10-12-0527 U1 stub): 表壳 :cols 与渲染器 :cols 同引用(列序天然一致)
     * (2026-10-14: 经典三表的 visibleDrawerTracker/Peer/FileCols 随经典渲染链一并退役。) */
    visibleDrawerStubV0Cols() {
      return this._visibleCols("drawerStubV0");
    },
    /* 变体表格体(U2): 07/08/09 三表, 同一条 _gridTemplate / _visibleCols 路径(omitEmpty
     * 渐进列在 _visibleCols 尾部单点生效 —— 0621 注: cols computed 主要供经典链同名消费
     * 惯例与守阵对齐面, 桥模板实际取 visibleColsOf)。 */
    drawerPeerV07Grid() {
      return { gridTemplateColumns: this._gridTemplate("drawerPeerV07") };
    },
    drawerPeerV08Grid() {
      return { gridTemplateColumns: this._gridTemplate("drawerPeerV08") };
    },
    drawerPeerV09Grid() {
      return { gridTemplateColumns: this._gridTemplate("drawerPeerV09") };
    },
    visibleDrawerPeerV07Cols() {
      return this._visibleCols("drawerPeerV07");
    },
    visibleDrawerPeerV08Cols() {
      return this._visibleCols("drawerPeerV08");
    },
    visibleDrawerPeerV09Cols() {
      return this._visibleCols("drawerPeerV09");
    },
    /* 变体表格体(U3): Tracker 04/05/06 三表, 同一条 _gridTemplate / _visibleCols 路径 */
    drawerTrackerV04Grid() {
      return { gridTemplateColumns: this._gridTemplate("drawerTrackerV04") };
    },
    drawerTrackerV05Grid() {
      return { gridTemplateColumns: this._gridTemplate("drawerTrackerV05") };
    },
    drawerTrackerV06Grid() {
      return { gridTemplateColumns: this._gridTemplate("drawerTrackerV06") };
    },
    visibleDrawerTrackerV04Cols() {
      return this._visibleCols("drawerTrackerV04");
    },
    visibleDrawerTrackerV05Cols() {
      return this._visibleCols("drawerTrackerV05");
    },
    visibleDrawerTrackerV06Cols() {
      return this._visibleCols("drawerTrackerV06");
    },
    /* U4 内容树两变体(10/11): 同一条 _gridTemplate / _visibleCols 路径(11 可用性列
     * omitEmpty 渐进在 _colsOmitEmpty 单点生效 —— 原 hasav/noav 双 grid 手搓退役)。 */
    drawerContentV10Grid() {
      return { gridTemplateColumns: this._gridTemplate("drawerContentV10") };
    },
    drawerContentV11Grid() {
      return { gridTemplateColumns: this._gridTemplate("drawerContentV11") };
    },
    visibleDrawerContentV10Cols() {
      return this._visibleCols("drawerContentV10");
    },
    visibleDrawerContentV11Cols() {
      return this._visibleCols("drawerContentV11");
    },
  },
};
