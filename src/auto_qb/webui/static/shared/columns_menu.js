/* columns_menu.js — R4 大文件拆分(计划 26-11-02-2342 §07)
 * 列模型 · 列菜单 / 横向滚动胶囊。
 * 只搬方法定义, 实现逐行未改; 根文件已定义该域, 本片段在其后原地扩充(Object.assign)。
 * 加载序 = 四套皮肤 index.html 清单里紧跟根文件之后(与拆分前同一迭代替换序)。
 */
Object.assign(window.AQB_COLUMNS.methods, {
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
     * 三件事(缺一即静默坏): (1)表头位移 = 容器 scrollLeft 反向; (2)--head-pin-x 供首列吸左首格反向抵消;
     * (3).is-hscrolled 打标(容器 + 表头)供 CSS 画右缘落影 —— CSS 无法感知 scrollLeft, 丢标 = 边界落影永不出现。
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
     * !重算时机只有四个: (1)容器 scroll(本函数) (2)热区进入那一刻 (3)ResizeObserver(容器盒变)
     *   (4)window resize(清状态栏高缓存 + 重算)。
     * 刻意**不**在列应用路径(6 处 colWidths 写入点)显式触发, 也不挂 MutationObserver:
     * 改列宽 / 隐藏列会让 scrollWidth 变而容器盒子不变(RO 观察不到), 但那一刻指示条必然不可见
     * (它只在热区里显示), 陈旧几何没人观察得到; 下一次进入热区时 (2) 用同一份本函数修正。
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
     * 值缓存到 window resize((4)) —— 热区 handler 每次 mousemove 都要用它, 不能每次都量。 */
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
     * !早先写成单边 `clientY >= innerHeight - 状态栏高 - 24`, 少了上界 => 状态栏那 34px 也落在带内
     * (状态栏是常用控件区, 不该召唤滚动条)。2026-11-01 用户验收指出后补上上界。 */
    _hscrollBand(ev) {
      const bottom = window.innerHeight - this._hscrollStatusbarH();  // 状态栏上缘
      return ev.clientY >= bottom - 24 && ev.clientY < bottom;
    },
    /* 横向判据: 指针要落在胶囊**本身**的邻域内(左右各放 40px 余量), 不是全屏宽都算。
     * !早先只判 clientY => 鼠标扫过底部右侧的速度/限速区也召唤胶囊(2026-11-01 用户验收指出)。
     * 只读缓存(HSCROLL_IND.pillW), 热路径上不量布局。 */
    _hscrollInPillSpan(ev) {
      const w = HSCROLL_IND.pillW;
      if (!w) return false;
      return Math.abs(ev.clientX - window.innerWidth / 2) <= w / 2 + 40;
    },
    /* 热区 handler(R1: 落在热路径上, 每次 mousemove 都跑): 纵向两次比较 + 横向一次减法,
     * 不读布局、不写 DOM; 状态没变立刻返回。**入带那一刻**才重算几何(重算时机 (2))。 */
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
    /* 照 columns_grid.js::_ensureHeadObserver 的范式: 只观察当前主表容器, 元素换了才重挂;
     * 回调 rAF 合并(同一帧多次变化只重算一次); 无 ResizeObserver 时降级为不挂 ——
     * 此时容器盒变化仍会在下一次进入热区((2))或容器 scroll((1))时被修正。 */
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
});
