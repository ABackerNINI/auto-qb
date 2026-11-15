/* columns_grid.js — R4 大文件拆分(计划 26-11-02-2342 §07)
 * 列模型 · 可见列派生 / 网格样式 / 表头同步 / 窗口虚拟。
 * 只搬方法定义, 实现逐行未改; 根文件已定义该域, 本片段在其后原地扩充(Object.assign)。
 * 加载序 = 四套皮肤 index.html 清单里紧跟根文件之后(与拆分前同一迭代替换序)。
 */
/* 渲染自查的面级豁免(计划 26-11-10-0027 W2(1), D4 例外清单的 assert 侧落点): 这些面的
 * 「数据行子格数 == 列数」计数语义不成立, assertLayout 对它们豁免 —— 逐面写明原因, 不静默放宽:
 *   drawerTrackerV04  04 卡片形态面: 行是卡片(display:block, 卡内 header/stats/msg 三块)非
 *                     列状数据, 行子格数与列数(1)无等值语义; 表头也被变体有意隐藏
 *                     (parity e2e 另有「卡片形态规格」守阵钉它, 不回潮成表格)。
 *   drawerStubV0      桥验证 fixture(?dtstub 查询参数才注册, 生产零观感): 行模型 peer 的
 *                     渲染器 aq-peer-cells 已随经典链整体退役, 行是空壳 —— 它只验证
 *                     「锚 -> Teleport -> 引擎手势」挂载链, 不验证值格。 */
var ASSERT_SKIP_FACES = {
  drawerTrackerV04: "04 卡片形态面(D4 例外): 行是卡片非列状数据, 行子格数与列数无等值语义",
  drawerStubV0: "桥验证 fixture(?dtstub 测试专用): 行渲染器已随经典链退役, 行恒空壳",
};

/* 行高探测位(主表三 kind): _measureRowH 与「出窗最后一探」共用同一份选择器 ——
 * 两处各写一份, 改一处漏一处 = 那个 kind 又留一批永不修正的陈旧行高(issue 26-11-15-0332)。
 * !必须按 data-table 收窄: 剧集页的 .group-row.show-row / .ep-row 也带 data-key, 裸写
 * `.group-row:not(.torrent-row)[data-key]` 会把**别座表的行**记成 group 行高(键还可能撞车),
 * 并污染 _rowHAvgOf("group") —— 冻结后的占位基准正是从这个均值来的, 脏了就一直脏。
 * 三座表的行容器各自带 data-table="torrent" / "group" / "detail"(见 tpl/torrents.html、
 * groups.html、shows.html)。抽屉桥行**也**带 data-table(:data-table="dtBridgeTbl(tab)"),
 * 但取值恒是 peers / trackers / content, 且没有 data-hash / data-key、也不是 .torrent-row /
 * .member-row —— 三重条件都不满足, 天然不落进这三个探测位(别以为 data-table 一条就够)。 */
var ROW_H_MAIN_PROBES = [
  ["torrent", '.torrent-row[data-table="torrent"][data-hash]'],
  ["group", '.group-row[data-table="group"][data-key]'],
  ["member", '.member-row[data-table="detail"][data-hash]'],
];
/* 0553 换键携带的待领池 TTL(ms): 换键的加/删两半可能隔几拍才在键集上到齐(delta 交付序),
 * 短窗内跨拍配对; 超时即弃 —— 防删除组的高度被无关新组误领(后果轻微: 行进窗口即被实测
 * 校正, 见 _measureRowH 内注释)。 */
var ROWH_CARRY_TTL = 30000;
/* 0553 携带面模块级状态(单页面单引擎, 与 relocate_pop.js 的调度定时器同款非实例态):
 * 上一拍 group 活键集 + 两侧待领池。刻意不挂 this —— 实例属性经公共代理存取, 换键窗口
 * 的跨拍读写在实例面上不可靠(实测 prev 回读滞后一拍, e2e 取证 26-11-11-0553), 模块级
 * 原生 Set/Map 无此歧义。 */
var ROWH_LIVE = null;        // Set<组键> 上一拍活键集
var ROWH_ORPHANS = new Map(); // Map<旧键, {h, ts}> 待领孤儿(带实测高)
var ROWH_FRESH = new Map();   // Map<新键, ts> 待测新键

Object.assign(window.AQB_COLUMNS.methods, {

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
     * 值**时整列省略。2026-10-13-0811 起声明全删, 本机制现无声明者、恒短路保留。行来源走
     * 描述符 rows(变体表 = dtTplRows -> rowsFn; 经典表无 omitEmpty 列, 零开销短路)。行未落袋
     * (加载中)按声明全集保守显示。
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
    /* 列模板: 几何单点委托 DT_TABLE.layout(计划 26-11-10-0027 W1(2), 拍板 D1/D2)—— 轨道串
     * 从内核同一个返回值取(gridTemplate = tracks.join(" ")), 本处不再旁路拼接。轨道取序
     * 固化宽 > tpl > width > 缺省轨道; 真实列定义全列声明 tpl(等价性探针钉住该前提),
     * 缺 tpl 的缺省轨道分支在生产输入面上不可达。dt_table.js 在四皮肤清单里先于本文件
     * 之后的首次调用(渲染期 computed)加载, 无初始化时序问题。 */
    _gridTemplate(page) {
      return window.DT_TABLE.layout(this._visibleCols(page), this.colWidths[page] || {}).gridTemplate;
    },
    /* ---------------- 渲染自查挂载(计划 26-11-10-0027 W2(1), 拍板 D3 = 常驻生产) ----------------
     * assertLayout 进生产渲染: 每个在场表格面在「渲染完成」后做三处 O(1) 计数(网格轨道数 /
     * 列头格数 / 首个数据行子格数), 不一致 console.error(消息含 tableId 与三方计数)但**不打断
     * 渲染**。挂载点实证选定(两个, 与计划 §03 点名的两个时机一一对应):
     *   主视图四面(group/detail/torrent/show) -> 根实例 updated()(lifecycle.js):
     *     Vue 的 updated 钩子是**后置队列**(post-flush cbs), 触发时同一次 flush 里的子组件
     *     (aq-table / 桥)都已 patch 完 —— 即「主视图渲染后」的严格语义。表头经 def.headRef
     *     取 ref(v-if 未渲染的视图 ref 不在场 = 零 DOM 扫描), 行在表头父容器内按
     *     data-table 现查(容器作用域, 只走到首个匹配)。
     *   抽屉桥九变体面(drawerStubV0/07/08/09/04/05/06/10/11) -> 桥模板 .group-table 的
     *     @vue:mounted / @vue:updated 钩子(dtAssertLayout, xtpl.html tpl-aq-dt-bridge):
     *     桥是独立组件, 列宽/隐藏等抽屉列态变更不触发根重渲, 根 updated() 盖不住;
     *     .group-table 的 vnode 钩子恰在「Teleport 完成后 / 每次桥 patch 后」触发, 拿到的
     *     $event.el 就是行容器 —— 表头/行都在同一座锚内, 配对零 document 扫描。
     * 开销: 每面 O(1)(一次 computed 样式读 + 两个 childElement 计数; computed 读的强制布局
     * 与同拍 _measureRowH 的读取合流, 不新增布局趟)。R4 窗口化面: 窗口只切行不切格, 任一
     * 渲染行的子格数都等于列数, 计数语义在窗口化下成立(e2e parity/face-bg 实证零误报)。
     * 豁免语义: 表头/行未渲染(面不在场/空态)一律不算不一致 —— 与内核「未挂载豁免」同口径;
     * 面级豁免见 ASSERT_SKIP_FACES, 行级豁免见 _assertLayoutPair 的 empty-row 分支。 */
    _assertLayouts() {
      if (typeof document === "undefined") return;
      const DT = window.DT_TABLE;
      if (!DT || typeof DT.assertLayout !== "function") return;
      for (const id of Object.keys(ALL_TABLE_DEFS)) {
        const def = ALL_TABLE_DEFS[id];
        /* 抽屉桥面(headRef 恒 null)的挂载点在桥模板钩子, 不在此逐面扫 DOM */
        if (!def || !def.headRef) continue;
        const ref = this.$refs[def.headRef];
        if (!(Array.isArray(ref) ? ref.length : ref)) continue;  /* 视图 v-if 未渲染 */
        const headEl = this._headEl(id);
        if (!headEl) continue;
        const parent = headEl.parentElement;
        const rowEl = parent
          ? parent.querySelector('.group-row[data-table="' + id + '"], .member-row[data-table="' + id + '"]')
          : null;
        this._assertLayoutPair(id, headEl, rowEl);
      }
    },
    /* 单面配对自查: headEl + 首个数据行 -> DT_TABLE.assertLayout; 有问题 console.error 不打断。
     * rowEl 允许 null(空态/未渲染 = 豁免); empty-row(10/11 筛选空的占位行, 单格提示非列状
     * 数据)同样豁免 —— 行级豁免与面级豁免(ASSERT_SKIP_FACES)分开记, 各自写明原因。 */
    _assertLayoutPair(tableId, headEl, rowEl) {
      if (typeof document === "undefined") return;
      if (ASSERT_SKIP_FACES[tableId]) return;
      if (!headEl || !rowEl) return;
      if (rowEl.classList && rowEl.classList.contains("empty-row")) return;
      const DT = window.DT_TABLE;
      if (!DT || typeof DT.assertLayout !== "function") return;
      const problems = DT.assertLayout(headEl, rowEl, this.visibleColsOf(tableId), tableId);
      if (problems.length) {
        console.error("[dt_table.assertLayout] " + problems.join("; ")
          + " —— 三处计数不一致(多一格/少一列类缺陷), 渲染未打断(D3 常驻自查)");
      }
    },
    /* 从列头行(真正的 grid 容器)读取**当前渲染**的列宽 px; 列数不符(渲染未完成)返回 null。
     * !2026-10-18(用户报障「用户表格隐藏一列其它列坍塌」根治): 逐 token 严格校验
     * ^\d+(\.\d+)?px$(放行小数 px —— getComputedStyle 量出的是布局精确值, 拒小数会把
     * 合法宽度误判不合法; 拒 fr/minmax 才是要点) —— display:none 的表头(08 五区分组的
     * 折叠组/空组, 表头在 .dt08-rows 内)
     * getComputedStyle 返回的是**指定形**(minmax(170px, 1.6fr) ...), 旧的 parseFloat 兜底
     * 会把 "1.6fr)" 解析成 1.6px 混进宽度表, 全组列宽随即坍成最小宽; 严格校验后这种
     * 量不到的表头只会得到"数量不符 -> null"(调用方按未渲染处理), 垃圾值进不了引擎。 */
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
     * 块级容器的 rowGap 计算值是 "normal" => parseFloat 得 NaN => 回落 0, 正是我们要的值。
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
        if (g === null) {
          /* 抽屉内容桥(W3)首渲时锚里的 .group-table 还没落 DOM(同一次 patch 的 Teleport 子节点),
           * 首拍只能按兜底间距开窗。**不能**借主表缓存: 主表挂 .rl-scope, row_lang.css 会把它的
           * rowGap 清零(抽屉不挂该类, 恒为皮肤基值 5/6px) —— 实测借来 0px, 千行占位总高少
           * ~18%(滚到底差一大截)。故首拍照旧兜底, 并安排一个逐帧收敛: 桥表落 DOM 后实测到
           * 真值就作废本轮估算, 让窗口按真间距重算一次(上限约 12 帧; 锚比首帧晚一两拍才落也
           * 能等到, 有 pending 守卫不重排)。 */
          if (kind === "drawerContent" && !this._winGapPending
              && typeof this.$nextTick === "function") {
            this._winGapPending = true;
            const raf = typeof requestAnimationFrame === "function"
              ? requestAnimationFrame
              : (fn) => setTimeout(fn, 16);
            let tries = 0;
            const settle = () => {
              // 已实测到(其他路径先量到) / 面板关了: 收敛结束
              if (this._winGap[kind] !== undefined || !this.drawer || !this.drawer.open) {
                this._winGapPending = false;
                return;
              }
              if (this._winGapOf(kind) !== null) {
                this._winGapPending = false;
                this._rowHVer++;  // 真值到手: 作废首拍估算, 让窗口按实测间距重算一次
                /* 行高也有首拍落定问题: 抽屉行挂 content-visibility:auto, 首拍(抽屉入场
                 * 动画/首布局未完成时)量到的是 contain-intrinsic-size 内容盒 27+边框=28,
                 * 真正渲染后是 27。收窗后再补两拍实测, 把均值从 28 拉回 27 —— 否则下一次
                 * 实测(用户点勾选/数据回路那拍)才发现差 1px, 又收一窗(可见勾选跳动)。 */
                let post = 0;
                const remeasure = () => {
                  if (post++ >= 2 || !this.drawer || !this.drawer.open) return;
                  this._rowHVer++;
                  raf(remeasure);
                };
                raf(remeasure);
                return;
              }
              // 锚(Teleport 目标)可能比首帧晚一两拍才落 DOM: 逐帧探到为止, 上限约 200ms
              if (++tries > 12) {
                this._winGapPending = false;
                return;
              }
              raf(settle);
            };
            raf(settle);
          }
          return null;
        }
        this._winGap[kind] = g;
      }
      return this._winGap[kind];
    },
    _winSigExtra() {
      // 会改变"容器上方内容高度"的因子: 状态分布条是否渲染 / 搜索态 / 筛选态 / 根缩放。
      // !根缩放必须进签名(issue 26-11-14-0844): zoom!=1 把全部视觉几何按 z 缩放, 表顶文档偏移
      // (_winTop = rect.top + scrollY, 视觉空间)随之变 —— 不进签名的话 zoom 切换后 _winTop 沿用
      // 旧值, rel 偏 (1-z)×表顶, 窗口选行整体错位约一行。比值实测(body 的 gBR/offsetWidth)而非
      // 读 computed zoom: Chrome 不把 zoom 报成继承, html 设 0.9 时 body/子孙 computed 恒 "1"。
      // 代价: 这让 _winSigExtra 从纯字符串变成每次 _ensureWinTop(每拍 updated)读一次 body gBR
      // (强制同步布局) —— 换取 zoom 切换后的 winTop 重量; 增量 = 每拍一次 body gBR, 量级被
      // 同帧既有的逐行 gBR 探测(_measureRowH)淹没。
      const b = typeof document !== "undefined" ? document.body : null;
      const rz = (b && b.offsetWidth) ? b.getBoundingClientRect().width / b.offsetWidth : 1;
      const zTok = Number.isFinite(rz) && rz > 0 ? rz.toFixed(4) : "1";
      return `${this.distTotal ? 1 : 0}${this.searchQuery && this.searchQuery.trim() ? 1 : 0}${this.filtersActive ? 1 : 0}${zTok}`;
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
     * = 强制同步布局, 每帧读会把 P1-3 的收益又吐回去)。签名含 lastRid => 每轮数据最多读一次。 */
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
     * 首访策略按规模二分(issue 26-11-02-0902): 千级以下仍由一轮**全量渲染**一次量齐(百毫秒级);
     * 千级及以上首帧就用 ROW_WIN_EST_H 开窗, 只量视口行, 未量行沿用全局均值兜底、随滚动逐步实测
     * 替换 —— 否则 3000 行首访要付「全量 patch + 逐行 gBR + 每行监听增删」一发 8.4s 长任务。 */
    _measureRowH() {
      if (!this.rowWin) return;
      // 签名取三个有窗口的层(与 _rowWindow 的 kind 对齐; 顺序 group/torrent/detail 与旧字面量一致)
      const winDefs = [TABLE_DEFS.group, TABLE_DEFS.torrent, TABLE_DEFS.detail];
      // !签名不含 viewMode(2026-11-02 关抽屉/切页卡死取证): 三 kind 行宽几何都不随 viewMode 变
      // —— 列集合由 colcounts 因子独立盯住、视口宽由 _winResize 盯住, 行本身只在固定列集的
      // 同宽表区渲染。旧签名含 viewMode = 每次切页把三 kind 行高全表作废 + _winMeasured 翻 false
      // => 下一轮 _rowWindow 走全量渲染量齐, 3000 行实测 5.9~8.4s 长任务(切页卡死的根因)。
      const sig = `${this._winResize}|${winDefs.map((d) => this[d.cols].length).join("|")}`;
      // !用 getBoundingClientRect().height 而不是 offsetHeight: 后者取整, 0.4px 的误差 ×
      // 3000 行就是 1200px 的漂移。
      for (const [kind, sel] of ROW_H_MAIN_PROBES) {
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
        // 0553 组键换键携带(issue 26-11-11-0553, 计划 26-11-15-2340 §03.6): 组键 =
        // (规范化 save_path, 文件) —— 整组迁移收官/接管瞬间 save_path 变更 -> 组行 data-key
        // 换键, 旧键实测值成孤儿、新键无实测, 该行在窗口前缀和按 est 兜底一拍, 占位/滚动
        // 总高短暂失真(列表跳一下; issue §06 建议修法其一「键替换时沿用旧键实测值」)。
        // 配对在两侧待领池之间做: 消失键(孤儿, 带实测高) x 新出现且未实测的键, 两侧各恰一个
        // 活着才确定性配对(多孤儿/多新键 = 歧义, 维持 est 兜底不猜)。池条目带 TTL(ROWH_CARRY_TTL)
        // —— 换键的加/删两半可能隔了几拍才到齐(delta 交付序), 短窗内跨拍配对; 超时即弃,
        // 防删除组的高度被 30s 后无关的新组误领(误领后果轻微: 行进窗口即被实测校正, 高度族
        // 本就贴近均值)。
        // 仅 group kind: torrent/member 行键是 hash(迁移全程稳定), 无换键面。
        if (kind === "group") {
          const now = Date.now();
          const live = new Set(this.filteredGroups.map((g) => g.key));
          const prev = ROWH_LIVE;
          // 池维护三清: TTL 超时 / 孤儿键回到活集(交付回摆) / 待测键已被实测(无需携带)
          for (const [k, rec] of Array.from(ROWH_ORPHANS)) {
            if (now - rec.ts > ROWH_CARRY_TTL || live.has(k)) ROWH_ORPHANS.delete(k);
          }
          for (const [k, ts] of Array.from(ROWH_FRESH)) {
            if (now - ts > ROWH_CARRY_TTL || this._rowHs["group:" + k] !== undefined) ROWH_FRESH.delete(k);
          }
          if (prev && prev.size) {
            for (const k of prev) {
              if (live.has(k)) continue;
              const h = this._rowHs["group:" + k];
              if (h !== undefined && !ROWH_ORPHANS.has(k)) ROWH_ORPHANS.set(k, { h, ts: now });
            }
            for (const k of live) {
              if (!prev.has(k) && this._rowHs["group:" + k] === undefined && !ROWH_FRESH.has(k)) ROWH_FRESH.set(k, now);
            }
          }
          ROWH_LIVE = live;
          if (ROWH_FRESH.size === 1 && ROWH_ORPHANS.size === 1) {
            const freshKey = ROWH_FRESH.keys().next().value;
            const orphan = ROWH_ORPHANS.values().next().value;
            /* 与行窗口化 pad 修复(issue 26-11-15-0332)的共存关系:
             * 其一, 携带值 = 旧键实测高的转记, 写进 _rowHs 后即满足「已实测」判据(键在即已实测)
             *   —— _reprobeRenderedRowH 把它当已有键、行进窗口后照常按真值修正(真值优先于
             *   转记, |差|>0.5 才覆盖), 不会把携带值当陈旧值清掉;
             * 其二, 远端冻结的 _rowHAvgOf 基准不受携带干扰: 携带发生在 updated() 拍, 主表基准
             *   首校后已冻结(门恒关), 携带值只进 _rowHs 不触发均值重校, 不搬 pad;
             * 其三, 出窗最后一探在 render 拍(reprobe 旧键)、携带在 updated() 拍, 时序天然错开:
             *   旧键被顶掉陈旧值后才入孤儿池(孤儿高反而更准), 携带键是新键、reprobe 只修
             *   已有键不会顶掉它。 */
            this._rowHs["group:" + freshKey] = orphan.h;
            ROWH_ORPHANS.clear();
            ROWH_FRESH.delete(freshKey);
            this._rowHVer++;  // 让窗口按携带高度重算, 消掉那一拍 est 跳变(与 _measureRowH/
                              // 签名作废同款 updated() 拍响应式收敛, 不踩 reprobe 的 render
                              // 途中改响应式态自激坑 —— 那条约束只限 render 途中)
          }
        }
        const rows = document.querySelectorAll(sel);
        if (!rows.length) continue;
        let changed = false;
        for (const r of rows) {
          const h = r.getBoundingClientRect().height;
          const key = kind + ":" + (r.getAttribute("data-hash") || r.getAttribute("data-key") || "");
          if (this._rowHs[key] === undefined || Math.abs(this._rowHs[key] - h) > 0.5) {
            this._rowHs[key] = h;
            changed = true;
          }
        }
        // 未量过的行(新种子 / 千级首访尚未滚到的行)用它兜底。取**已实测行的全局均值**而非
        // 当前窗口均值: 后者随窗口切换每帧跳变, 会让占位总高与滚动条长度跟着抖(issue 26-11-02-0902)。
        // !全局均值只在「首访量齐那一拍」校准, 之后**冻结**(issue 26-11-15-0332 第二根因):
        // 每量到一行新行, 均值都会微动 δ; 而 pad 区里可能有上百行从未渲染、全按这个均值估高,
        // 于是 padTop 被整体搬 δ×未量行数 —— 取证 flux 深滚后 106 行未量、均值 65.770→65.806
        // (δ=0.036) 就把渲染行整体推了 +3.8px, 与「陈旧存值」是同症不同因。冻结后新量行只把
        // 自己那一项从估算换成真值, 不再连坐搬动整段 pad。
        // !已知边界(刻意不做): 冻结之后基准不再随「行集变了 / 数据刷新了」重算。想重算就得
        // 把 _rowHs 里上一批行的键剔掉(否则均值仍是被旧population稀释的混合值 —— 那才是假的
        // 「重校」), 而按 kind 剔键对 member 是灾难(成员列表是逐组子集, 换组剔一次 = 每次展开
        // 都重新实测)。权衡后选稳定: 估偏只影响「从未渲染过的行」的占位与滚动条长度 ——
        // 单调收敛的是**未量行数**(随滚动递减), 不是估偏本身: 某行真值比基准高时把它换成真值
        // 会让总偏变大, 所以别指望「误差单调下降」; 而基准一动, 滚动中的内容就整段跳
        // (本 issue 要修的正病)。
        // 列集合/窗宽变化仍会翻 _winMeasured=false, 下一拍照常重新校准, 不残留旧几何。
        // !但**运行时改 root zoom 不在此列**(issue 26-11-16-0716 已入池): 基准存的是 gBR 视觉
        // 量值, 而这条重校签名只看布局宽度代与可见列数 —— zoom 只改渲染尺度、不动布局宽, 于是
        // _winMeasured 恒 true、门恒关, 缩放 1→0.9 后未量行仍按旧缩放估高(偏大 ~11%)。影响面
        // 限于 pad 总高/滚动条长度/可达底端, **不搬已渲染内容**(所以不是本 issue 那个跳变病),
        // 刷新即恢复。修法要么按 zNew/zOld 原地重标 _rowHs+_rowH(不删键不翻量齐态), 要么把基准
        // 改存布局 px; 两条都动到 _winZoomOf 的换算面, 故不随本批做。
        // 例外: 抽屉内容桥**不冻结**(见下面第四探测位) —— 它挂 content-visibility:auto,
        // 首拍量到的是 intrinsic 占位高 28, 必须靠后续均值收敛拉回真值 27。
        const avg = this._rowHAvgOf(kind);
        /* !`!(this._rowH[kind] > 0)` 这一支是「冻结不许冻结在无效值上」的兜底: 只要有一拍
         * 量到的 gBR 全是 0(行在 DOM 但祖先 display:none / 行刚插入尚未布局 / 将来某个视图
         * 改用 v-show —— 三个主视图现在是 v-if, 切页时行直接被摘掉, 走的是 rows.length===0
         * 那条早退, 所以这条**是**安全网而非当前热路径), 均值就校准成 0; 若就此冻住, 下次
         * 真量到时 est 会一直回落成 ROW_WIN_EST_H 常量(42/44) 而不是真实行高 —— 未量行的
         * pad 恒短。存值非正一律当作「还没校准」, 下次量到真值就重校(与修复前的自愈行为
         * 等价)。别因为「现在走不到」就删: 删了以后一旦某视图换成 v-show, 冻结就会把 0
         * 钉死, 且症状(未量行 pad 恒短、滚到底够不着)与本 issue 极像, 极难反查。 */
        if (!this._winMeasured[kind] || !(this._rowH[kind] > 0)) {
          if (this._rowH[kind] === undefined || Math.abs(this._rowH[kind] - avg) > 0.01) {
            this._rowH = { ...this._rowH, [kind]: avg };
            changed = true;
          }
        }
        if (!this._winMeasured[kind]) {
          this._winMeasured[kind] = true;  // 首访窗口行已实测(千级以下即全表, 千级以上随滚动补齐)
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
        let dChanged = false;
        let dMeasured = 0;
        for (const r of drows) {
          /* !抽屉行挂 content-visibility:auto(视图外延迟渲染), 被跳过时 gBR 返回的是
           * contain-intrinsic-size(27px 内容盒)+边框, 比真正渲染的行恒多 1px; 抽屉开场
           * 动画期整表被判在视口外 -> 首拍量到全 28, 动画落定后真渲染 27, 下一轮实测
           * 因此必变 -> 已收窗的窗口再收一窗(用户可见勾选/滚动跳动, 量具记成多余变异)。
           * 只量**确实已渲染**的行; 本轮一行都没量到(整表在动画/视口外)就不动均值与
           * _winMeasured, 留给下一拍(容器间距收敛那拍必然还有一次渲染)。 */
          if (typeof r.checkVisibility === "function"
              && !r.checkVisibility({ contentVisibilityAuto: true })) continue;
          const h = r.getBoundingClientRect().height;
          const key = "drawerContent:" + (r.getAttribute("data-dt-key") || "");
          dMeasured++;
          if (this._rowHs[key] === undefined || Math.abs(this._rowHs[key] - h) > 0.5) {
            this._rowHs[key] = h;
            dChanged = true;
          }
        }
        if (!dMeasured) continue;
        // 未量过的行(新文件)用它兜底; 口径同主表 = 已实测行的全局均值而非当前窗口均值
        const davg = this._rowHAvgOf("drawerContent");
        if (this._rowH["drawerContent"] === undefined || Math.abs(this._rowH["drawerContent"] - davg) > 0.01) {
          this._rowH = { ...this._rowH, drawerContent: davg };
          dChanged = true;
        }
        if (!this._winMeasured["drawerContent"]) {
          this._winMeasured["drawerContent"] = true;  // 首访窗口行已实测(小列表即全表, 大列表随滚动补齐)
          dChanged = true;
        }
        if (dChanged) this._rowHVer++;
      }
    },
    /* 该 kind 已实测行的**全局均值**(遍历 _rowHs 的 kind: 前缀)。
     * 为什么不用「当前窗口均值」: 窗口随滚动换一批行, 窗口均值会跟着跳变(如 49.7 <-> 71.4),
     * 占位总高与滚动条长度每帧抖一下; 全局均值跨窗口稳定, 只随新实测行缓慢收敛。
     * !本函数只负责算, **冻结与否由调用方定**: 三个主 kind 首校后即冻结(_measureRowH 的
     * 「已知边界」), 所以那个「缓慢收敛」在主表上不成立 —— 首访千级列表此刻只有视口那几十行,
     * 冻结后基准不再随滚动更新, 未量行就一直按首校均值估, 直到它自己滚进窗口被实测。
     * 抽屉内容桥不冻结(首拍量到 intrinsic 占位高 28, 必须靠后续均值拉回真值 27)。 */
    _rowHAvgOf(kind) {
      const prefix = kind + ":";
      let sum = 0, n = 0;
      for (const k in this._rowHs) {
        if (!k.startsWith(prefix)) continue;
        sum += this._rowHs[k];
        n++;
      }
      return n ? sum / n : 0;
    },
    /* 行键提取按 kind 走描述符(计划 26-11-02-0351 W2): 主表 = item.hash / group = item.key
     * (WIN_SRC_DOC.keyOf 与 group 覆盖); 抽屉行(W3 接线)两者皆无, 键字段名由该 kind 的
     * 描述符给(如 rowKey 字段 "k" 的值)。未注册 kind 回落文档型 = 现行为。 */
    _rowKeyOf(kind, item) {
      return kind + ":" + this._winSrc(kind).keyOf(item);
    },
    /* 有效缩放(布局 px -> 视觉 px 的乘子, zoom=1 时恒 1): 盒子自身 gBR.height(视觉)与
     * getComputedStyle().height 的 used 值(布局空间, **分数精度**)的比值实测。!布局高分母
     * 不能用 offsetHeight —— 取整误差在容器上按比例放大: 容器 ~2 万 px 高时 ±0.5px 取整给
     * 同量级的 padTop 带来最多 ~6px 误差(flux 像素带判据实测被撞红, 2026-11-14); computed
     * used 值无取整, zoom=1 时比值恒 1(±1e-7, pad 上 <0.01px)。!也不能读 computed zoom ——
     * Chrome 不把 zoom 报成继承(html 设 0.9 时 body/子孙 computed 恒 "1", 实测 2026-11-14),
     * 读出来恒 1 会把换算整个关掉; 比值实测对任意祖先上的 zoom 都成立。窗口化产物里只有 pad
     * 写进 style.height(布局空间), 换算单点在 _rowWindow 的两个 pad 出口(issue
     * 26-11-14-0844); 容器不在场/computed 高非正(不在场 = "auto")回落 1 = 关闭换算, 与
     * zoom=1 行为一致。 */
    _winZoomOf(kind, refName) {
      const el = this._winContainer(kind, refName);
      if (!el || typeof getComputedStyle !== "function") return 1;
      const layoutH = parseFloat(getComputedStyle(el).height);
      const z = layoutH > 0 ? el.getBoundingClientRect().height / layoutH : 0;
      return Number.isFinite(z) && z > 0 ? z : 1;
    },
    /* 出窗最后一探的探测位解析(issue 26-11-15-0332): 只取**此刻还在 DOM 里**的该 kind 行。
     * 主表走 ROW_H_MAIN_PROBES(与 _measureRowH 同源); 抽屉内容桥按当前在场变体锚现拼,
     * 口径与 _measureRowH 的第四探测位一致 —— 合并态同屏还有 peers/trackers 的桥行, 裸扫
     * .group-row[data-dt-key] 会把别座表的行混进来。 */
    _rowHProbeRows(kind) {
      if (typeof document === "undefined" || typeof document.querySelectorAll !== "function") return null;
      const main = ROW_H_MAIN_PROBES.find((p) => p[0] === kind);
      if (main) return { rows: document.querySelectorAll(main[1]), drawer: false };
      if (kind !== "drawerContent" || typeof document.querySelector !== "function") return null;
      const dtDefs = (typeof window !== "undefined" && window.AQB_DRAWER_TPL_DEFS) || {};
      for (const tid of Object.keys(dtDefs)) {
        const ddef = dtDefs[tid];
        if (ddef.window !== "drawerContent" || ddef.segs) continue;
        if (this.dtBridgeTbl(ddef.variantTab) !== tid) continue;
        const block = document.querySelector(`[data-dt-table-anchor="${tid}"] .group-table`);
        if (block) return { rows: block.querySelectorAll(".group-row[data-dt-key]"), drawer: true };
      }
      return null;
    },
    /* 出窗最后一探(issue 26-11-15-0332): 行高逐行实测表 _rowHs 只在「行渲染在场」时由
     * updated() 的 _measureRowH 刷新; 首渲量过的行若之后变矮/变高(字体交换 / 内容重排,
     * 这些是异步布局变化, 不一定伴随 Vue 重渲)且已滚出窗口, 存值就永不修正 —— 窗口下滑越过
     * 它时 padTop 按陈旧存值超量替换, 渲染行整体跳 ±数px(取证: 存值 69.609 vs 实际 65.781,
     * 单行 +3.828px)。本方法在 _rowWindow 重建前缀和**之前**调用: 此刻旧窗口的行还在 DOM
     * (render 还没 patch), 把它们量最后一发真值顶掉陈旧存值, 同一拍的 pre[] 就按真值累加,
     * pad 顶替的是等高真值 —— 视觉不再跳。
     * !只刷新**已有键**, 且不动 _rowH / _winMeasured / _rowHVer / _rowHSig / 签名:
     *   - 新增键、全局均值、响应式版本一律留给 updated() 的 _measureRowH(它量的是新窗口行);
     *   - 在 render 途中改响应式态会自激重渲; 扩签名或删表 = 踩 rowh-sig-and-transition-geometry
     *     的全表作废坑(3000 行全量重渲 5.9~8.4s 长任务, 切页/关抽屉卡死复发)。
     * !sig 去重: 一拍里 _rowWindow 会被多次调用(memberPadTop / memberPadBottom / winMembers
     *   各一次), 同一滚动几何只量一次; 几何不变的重渲(如 _rowHVer 收敛拍)不重复付 gBR。
     * !去重签名只在**真的量到行**之后才落盘: 抽屉锚换座/整表被 content-visibility 跳过的
     *   那一拍量不到任何行, 若先把签名记下, 同一几何的后续渲染就再也不重探了(漏一次 = 留一批
     *   陈旧存值)。空探不记账, 下一拍自然重试。 */
    _reprobeRenderedRowH(kind, sig) {
      if (!this.rowWin || typeof document === "undefined"
          || typeof document.querySelectorAll !== "function") return;
      const cache = this._rowProbeSig || (this._rowProbeSig = {});
      if (cache[kind] === sig) return;
      const probe = this._rowHProbeRows(kind);
      if (!probe) return;
      const hs = this._rowHs;
      let probed = 0;
      for (const r of probe.rows) {
        /* 抽屉行挂 content-visibility:auto: 被跳过时 gBR 返回 contain-intrinsic-size
         * (27px 内容盒 + 边框 = 28), 比真渲染恒多 1px —— 采信会把真值改坏(与 _measureRowH
         * 同一条守卫, 见该处 2026-11-15 的动画期取证)。 */
        if (probe.drawer && typeof r.checkVisibility === "function"
            && !r.checkVisibility({ contentVisibilityAuto: true })) continue;
        const key = kind + ":" + (probe.drawer
          ? (r.getAttribute("data-dt-key") || "")
          : (r.getAttribute("data-hash") || r.getAttribute("data-key") || ""));
        const old = hs[key];
        if (old === undefined) continue;  // 新键归 _measureRowH, 本方法只修旧值
        const h = r.getBoundingClientRect().height;
        /* !h 非正不采信: 行在 DOM 但 gBR 报 0 的那一瞬(祖先 display:none / 行刚插入尚未
         * 布局 / 容器正被换掉), 写进 _rowHs 就等于把这一行的真值抹成 0, 同一拍 padTop 立刻
         * 少一整行(比留旧值更糟)。与 _measureRowH 的 `_rowH[kind] > 0` 兜底同一口径:
         * 量不到有效值就当没量过 —— 所以 probed++ 必须在有效性检查**之后**(它记的是
         * 「这一拍真量到了几行」, 全零探不能算量到, 否则去重签名会被空探烧掉)。 */
        if (!(h > 0)) continue;
        probed++;
        if (Math.abs(old - h) > 0.5) hs[key] = h;
      }
      if (probed) cache[kind] = sig;
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
      // 分流判据 = 描述符的 family 标记(issue 26-11-03-1035): 身份比较对克隆描述符恒假 ——
      // group 是 Object.assign 换行键的克隆, 曾被误判进容器分支(抽屉关 = 窗口化关闭全量渲染,
      // 抽屉开 = 切片跟抽屉滚动漂移)。缺 family 一律按文档型 = 保守默认(未注册 kind 同口径)。
      const doc = this._winSrc(kind).family !== "container";
      const st = doc ? null : this._winCtnState();
      const sy = doc ? this._winScrollY : st.y;
      const vh = doc ? this._winViewH : st.h;
      if (!this.rowWin || n < ROW_WIN_MIN || vh <= 0) return off;
      // 行高还没量齐(首访/改列之后): 直接估算开窗(issue 26-11-02-0902; 阈值 ROW_WIN_EST_MIN
      // 与 ROW_WIN_MIN 合并取 200 —— 精确冷启动在 200 行即单发 334ms longtask, 不可接受),
      // 只渲染视口行, 未量行按 _rowH 全局均值/EST_H 兜底, 事后随滚动收敛。
      if (!this._winMeasured[kind] && n < ROW_WIN_EST_MIN) return off;
      const est = this._rowH[kind] || ROW_WIN_EST_H[kind];
      // 行间距实测(见 _winGapFor); 容器还没渲染时本轮先全量, 免得按错的间距撑占位。
      // 首访冷启动例外: 首帧容器通常还没挂(挂载后才量得到), 先按兜底间距开窗,
      // 下一拍容器一挂上就实测真值并重算 —— 否则又退回一次全量渲染, 等于白改。
      let gap = this._winGapFor(kind);
      if (gap === null) {
        if (!this._winMeasured[kind] && n >= ROW_WIN_EST_MIN) gap = ROW_WIN_GAP_FALLBACK;
        else return off;
      }
      /* issue 26-11-15-0332: 前缀和必须用「出窗行最后一发真值」累加。调用点放在所有早退
       * 之后、pre[] 之前 —— 此刻 render 尚未 patch, 旧窗口的行还在 DOM, 重探来得及顶掉
       * 陈旧存值; 早退的那些分支(未开窗/未量齐/容器不在场)本来就不产出 pad, 无需重探。
       * 签名只取本拍的滚动几何/规模/宽度代/表顶偏移(全是本次开窗已读过的量), 不新增
       * 行高签名因子 —— 见 _reprobeRenderedRowH 的「不踩全表作废坑」注释。 */
      this._reprobeRenderedRowH(
        kind, `${sy}|${vh}|${n}|${this._winResize}|${this._winTop[kind] || 0}`,
      );
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
      let end = this._prefixFloor(pre, rel + vh) + 1 + ROW_WIN_OVERSCAN;
      if (!(start >= 0) || start > n) start = 0;
      if (!(end > 0) || end > n) end = n;
      if (start >= end) return off;  // 数值异常: 宁可全渲染, 也不渲染"空窗口"
      // 占位两侧各多出一个 gap(顶替了行块内部原有的间距), 故减一个 gap 对齐。
      // !pads 必须除以有效缩放换算成布局 px(issue 26-11-14-0844): 前缀和/rel 一族是视觉空间
      // (根 zoom!=1 时 gBR/scrollY 全按视觉报数), 而占位件 style.height 是布局 px —— 直接写
      // 视觉值会再被 zoom 缩一遍, pad 恒短 (1-z) 倍, 贴文档底后 padTop 差约 (1-z)×总高(实测
      // flux ~1900px), 渲染行整体落在视口上方。gap 本就是布局空间(computed rowGap), 放在除法
      // 之后同单位相减。zoom=1 时 z 数值等价于 1(至多浮点重结合 1ulp 差, ~1e-11px), 行为零变化。
      const z = this._winZoomOf(kind, refName);
      return {
        active: true, start, end,
        padTop: start > 0 ? pre[start] / z - gap : 0,
        padBottom: end < n ? (pre[n] - pre[end]) / z - gap : 0,
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
    /* 模板用: 成员行切片(展开明细)。窗口未启用时原样返回, 与改动前完全等价。
     * !窗口切片/占位/前缀和必须按**渲染同一序**(R4 存量评审 R5#35): memberWin 内部的
     * 前缀和(_rowPre.member)与切片都吃传入的 list —— 旧实现按未排序 list 开窗、却对
     * sortedMembers 的排序结果做 slice, 明细列排序激活且展开组成员 >= ROW_WIN_EST_MIN
     * 时切片行错位、padTop/padBottom 错排列计高, 键盘视口回落(shortcuts 按 _rowPre.member
     * 换算文档 y, 行序与 _kbRows 同走 sortedMembers)也取错行。先排好序再交给窗口引擎,
     * 切片/占位/前缀和/键盘行序四者同源同序。 */
    winMembers(list) {
      const rows = this.sortedMembers(list);
      const w = this.memberWin(rows);
      return w.active ? rows.slice(w.start, w.end) : rows;
    },
});
