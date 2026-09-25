/* auto-qb WEB UI · 列模型交互(列宽/列序/列菜单/列持久化) + 行窗口化
 *
 * app.js 按域拆分出的片段(2026-09-20)。约定与 config_editor.js / config_rules.js 同一范式:
 * 挂到 window.AQB_COLUMNS, 由 app.js 末尾 app.mixin(window.AQB_COLUMNS) 注入同一个 Vue 实例 ——
 * 方法体里的 this 仍是那个组件实例, 跨模块互调与拆分前完全等价。
 *
 * ❗本文件在 HTML 里必须排在 app.js **之前**(app.js 末尾要读 window.AQB_COLUMNS);
 *   用到的列模型常量(TABLE_COLUMNS / MIN_COL_PX / STATE_RANK …)仍单点定义在 app.js 顶部。
 */
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
      const W = 300, PAD = 8;
      const y = Math.max(PAD, ev.clientY);
      this.colFlip = false;
      this.colMenuAt = {
        x: Math.max(PAD, Math.min(ev.clientX, window.innerWidth - W - PAD)),
        y,
        mh: Math.max(160, window.innerHeight - y - PAD),
      };
      this.colMenuOpen = true;
    },
    /* 弹层内联样式: 仅右键路径给 fixed 坐标与视口内最大高度; 按钮路径返回 null 走原 CSS */
    colMenuStyle() {
      const at = this.colMenuAt;
      if (!at) return null;
      return { position: "fixed", left: at.x + "px", top: at.y + "px", maxHeight: at.mh + "px", overflowY: "auto" };
    },
    gridStyle(page) {
      // 列模板由 computed 缓存(见 *_Grid): 行渲染只取同一引用, 不每行拼字符串
      return { group: this.groupGrid, detail: this.detailGrid, torrent: this.torrentGrid, show: this.showGrid }[page];
    },

    /* ------------------------------------------------ 列状态(宽/隐/自适应) */

    _visibleCols(page) {
      const hidden = this.colHidden[page] || [];
      const defs = TABLE_COLUMNS[page];
      const order = this.colOrder[page];
      if (!order || !order.length) return defs.filter((c) => !hidden.includes(c.key));  // 无自定义序 = 定义序(向后兼容)
      // 按 colOrder 输出; 未入序的列(新增/残留 key)按定义序补尾 —— 宽/隐仍按列 key 对应, 换序不丢宽度
      const rest = new Map(defs.map((c) => [c.key, c]));
      const out = [];
      for (const k of order) {
        const c = rest.get(k);
        if (!c) continue;
        rest.delete(k);
        if (!hidden.includes(k)) out.push(c);
      }
      for (const c of defs) if (rest.has(c.key) && !hidden.includes(c.key)) out.push(c);
      return out;
    },
    /* 列模板: 有 px 覆盖用覆盖值, 否则用默认模板(仅首次渲染会出现这种混合态) */
    _gridTemplate(page) {
      const w = this.colWidths[page] || {};
      return this._visibleCols(page).map((c) => w[c.key] || c.tpl).join(" ");
    },
    /* 从列头行(真正的 grid 容器)读取**当前渲染**的列宽 px; 列数不符(渲染未完成)返回 null */
    _renderedWidths(headEl, page) {
      const rendered = (getComputedStyle(headEl).gridTemplateColumns || "")
        .split(" ")
        .map((v) => parseFloat(v))
        .filter((v) => !isNaN(v) && v > 0);
      const vis = this._visibleCols(page);
      if (rendered.length !== vis.length) return null;
      const out = {};
      vis.forEach((c, i) => {
        out[c.key] = Math.round(rendered[i]) + "px";
      });
      return out;
    },
    _headEl(page) {
      const ref = this.$refs[{ group: "groupHead", detail: "detailHead", torrent: "torrentHead", show: "showHead" }[page]];
      return Array.isArray(ref) ? ref[0] : ref || null;
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
     * 模板只消费三个产物: 可见切片、上占位高、下占位高。窗口关闭时 == 全量渲染(零差异回退)。 */
    _winContainer(kind, refName) {
      if (refName) return this.$refs[refName] || null;
      // 成员行: 容器 = .detail —— 明细表头(ref="detailHead")的父元素
      const head = this.$refs.detailHead;
      return head && head.parentElement ? head.parentElement : null;
    },
    /* 行容器的**真实**行间距(px): 三个容器并不相同 —— atlas `.group-table` 是 6px、
     * prism 是 5px、成员容器 `.detail` 是块级容器(没有 flex gap = 0)。硬编码任何一个值
     * 都会让另外两层的占位总高失真, 所以一律读计算样式实测(见文件头 BUG-1 注释)。
     * 块级容器的 rowGap 计算值是 "normal" ⇒ parseFloat 得 NaN ⇒ 回落 0, 正是我们要的值。
     * ❗返回 **null = 容器当前没渲染**(如种子页未打开时问 .group-table) —— 调用方**不得**
     * 把它当 0 缓存: 否则在分组页问一次就把种子页的间距永久记成 0(实测占位总高少 5px×2999)。 */
    _winGapOf(kind) {
      const el = kind === "torrent" ? this._winContainer(kind, "torrentTable")
        : kind === "group" ? this._winContainer(kind, "groupTable")
          : this._winContainer(kind, null);
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
    /* 容器顶边相对文档的偏移: 只在签名变化时读一次(getBoundingClientRect = 强制同步布局,
     * 每帧读会把 P1-3 的收益又吐回去)。签名含 lastRid ⇒ 每轮数据最多读一次。 */
    _ensureWinTop() {
      const base = `${this.viewMode}|${this.page}|${this._winResize}|${this._winSigExtra()}|${this.lastRid}`;
      for (const kind of ["torrent", "group", "member"]) {
        const sig = `${base}|${kind}`;
        if (this._winTopSig[kind] === sig) continue;
        const el = kind === "torrent" ? this._winContainer(kind, "torrentTable")
          : kind === "group" ? this._winContainer(kind, "groupTable")
            : this._winContainer(kind, null);
        this._winTop[kind] = el ? el.getBoundingClientRect().top + window.scrollY : 0;
        this._winTopSig[kind] = sig;
      }
    },
    /* 行高: **逐行实测**(不是采样几行取均值)。行高本就不齐(带 H&R 要求的行多一行),
     * 用"等高"近似会在几千行上累积成上百像素漂移 —— 表现为滚到底够不着、滚动条长度不对。
     * 首次(或列集合变化后)由一轮**全量渲染**量齐所有行, 之后每轮只更新当前窗口里的行。 */
    _measureRowH() {
      if (!this.rowWin) return;
      const sig = `${this.viewMode}|${this._winResize}|${this.visibleGroupCols.length}|${this.visibleTorrentCols.length}|${this.visibleDetailCols.length}`;
      // ❗用 getBoundingClientRect().height 而不是 offsetHeight: 后者取整, 0.4px 的误差 ×
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
    },
    _rowKeyOf(kind, item) {
      return kind + ":" + (kind === "group" ? item.key : item.hash);
    },
    /* 前缀和 y(i) = 第 i 行的顶边偏移(含行间距)。每帧重算: 3000 次加法 ≈ 0.03ms,
     * 比维护"失效缓存 + 增量更新"简单得多, 也不会因为漏失效而算错。 */
    _rowWindow(kind, list, refName) {
      const n = list.length;
      const off = { active: false, start: 0, end: n, padTop: 0, padBottom: 0 };
      void this._rowHVer;  // 依赖: 行高表更新后重算
      if (!this.rowWin || n < ROW_WIN_MIN || this._winViewH <= 0) return off;
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
      const rel = this._winScrollY - (this._winTop[kind] || 0);
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
    _onWinScroll() {
      if (this._winRaf) return;
      this._winRaf = requestAnimationFrame(() => {
        this._winRaf = 0;
        this._winScrollY = window.scrollY;
      });
    },
    _onWinResize() {
      this._winResize++;
      this._winViewH = window.innerHeight;
      this._winScrollY = window.scrollY;
    },
    /* 搜索命中高亮: 种子页不再逐条复制出 hit 字段(见 filteredTorrents), 高亮由模板现问现用 */
    isHit(row) {
      return !!row && this.searchHits.has(row.hash);
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
     * ❗只写易变态 colWidths, **绝不落盘** —— persistPage 只收意图(colHidden/colOrder/colW),
     *   "派生值没有资格落盘"是双轨模型唯一铁律(守阵 test_frontend_persist_page_takes_intent_only)。
     */
    recomputeEffective() {
      for (const page of ["group", "detail", "torrent", "show"]) {
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

    /* 空存储提示(W4 origin 隔离 + W5 浏览器"关闭时清除站点数据"): 本 origin 没有列偏好记录时弹一次
     * (点击关闭 / 15s 自灭)。运行时注入 DOM, 两套模板零改动。
     *
     * ❗为什么只陈述"本地址没有偏好记录"、不做精确判定(2026-09-24 取证): 站点级"关闭窗口时清除
     * Cookie 和站点数据"(Chromium cookie 例外 setting=4 = SESSION_ONLY)会在关浏览器时把该 host 的
     * Cookie 与 localStorage **一起**清掉 ⇒ "被清过"与"首次访问"在客户端**完全同形**: 任何能当跨会话
     * 记忆用的东西(包括本函数的"已提示"标记)都躺在被清掉的那份数据里, 没有服务端就无法区分。
     * 故这里给"事实 + 两种成因 + 自查路径", 不下结论(取证: Edge/Chrome 的 cookie 例外里都有
     * `127.0.0.1,*` setting=4, 于是"浏览器重启后偏好全回默认"被当成应用 bug 追了多轮)。 */
    _showColsOriginHint() {
      if (this._colsOriginHintShown) return;
      this._colsOriginHintShown = true;
      // 同一次标签会话只弹一次: 清站点数据的环境下 localStorage 里的"已提示"标记也一起没了,
      // 只靠它会在每次关浏览器重开后都弹; sessionStorage 随标签关闭失效, 正好只兜"同一次会话"。
      try {
        if (sessionStorage.getItem(COLS_ORIGIN_HINT_KEY)) return;
        sessionStorage.setItem(COLS_ORIGIN_HINT_KEY, "1");
      } catch { /* 私隐模式等: 退回下面 localStorage 那层标记 */ }
      try {
        if (localStorage.getItem(COLS_ORIGIN_HINT_KEY)) return;
        localStorage.setItem(COLS_ORIGIN_HINT_KEY, "1");
      } catch { /* 私隐模式: 写失败也继续弹, 本会话内由 _colsOriginHintShown 挡住 */ }
      const el = document.createElement("div");
      el.textContent = "本地址还没有列偏好记录。常见成因: ① 偏好按站点隔离存储, 换地址/端口"
        + "(127.0.0.1 ↔ localhost、38080 ↔ 38081)各存一份; ② 浏览器在本地址上开了"
        + "「关闭窗口时清除 Cookie 和站点数据」→ 每次关掉浏览器偏好都会回默认"
        + "(Edge 可在 edge://settings/content/all 里查该地址)。可固定用同一地址, "
        + "或改用 http://localhost:<端口> 打开。";
      el.title = "点击关闭";
      el.style.cssText = "position:fixed;left:50%;bottom:18px;transform:translateX(-50%);z-index:9999;"
        + "background:#1c252d;color:#e4eaef;border:1px solid #26313a;border-left:3px solid #5cc0cf;"
        + "padding:10px 16px;font:13px/1.5 'Segoe UI','Microsoft YaHei',sans-serif;"
        + "max-width:min(560px,90vw);cursor:pointer;border-radius:4px;";
      el.addEventListener("click", () => el.remove());
      document.body.appendChild(el);
      setTimeout(() => el.remove(), 15000);
    },

    /* 唯一持久化漏斗(plan 26-09-21-1551 §3.4): 全仓对 COLS_STORE_KEY 的 setItem **只允许这一处**
     * (静态守阵钉住)。写 v5 按页子树: 以存储为底(RMW, 防"同一毫秒两边写"), 只覆盖本次涉及的
     * page, 其余 page 取存储最新值。❗只收意图态(colHidden/colOrder/colW) —— 生效宽度 colWidths
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
     * ❗调用方只能是 storage 事件(它**只在其它标签**触发, 写入方自己收不到, 故无需去重)
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
        // 意图升格: 以既有 colW 为底 merge(❗隐藏列的 px 在这里保住 —— 渲染快照只含可见列,
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
    /* 列对齐规则(R10-08): align 定义在列模型里, 这里按**当前可见列**生成 :nth-child 规则注入 <head>。
     *
     * 为何生成而非在模板里逐格挂类: 值单元格共 67 个 × 4 视图 × 2 套 UI, 逐格挂类必然漏改;
     * 生成则"列模型改一处, 表头与值同源"(表头同样按可见列索引渲染, 顺序天然一致)。
     *
     * 选择器用 :where() 把特异性压到 0,1,0(只剩 :nth-child 那一位), 于是:
     *   - 胜过 .g-stat/.m-stat(0,1,0, 同权重靠源顺序: 注入的 <style> 在样式表之后) -> 非默认对齐生效;
     *   - 输给 .g-stat.zero/.m-stat.zero(0,2,0) -> 保留既有"0 值居中"口径。
     * 同时写 text-align 与 justify-content: 值单元格有的是块级文本, 有的是 flex(进度条/
     * 分享率对/芯片组), 只写 text-align 会漏掉后者。
     * ⚠ **left 也必须生成**: 数值列的值格子带 .g-stat/.m-stat(right), 若因为"left 是默认值"就跳过,
     *    左对齐的口径会被这两条通用规则盖掉(实测: 添加于列表头左、值右)。
     */
    colAlignCss() {
      const out = [];
      for (const page of ["group", "detail", "torrent", "show"]) {
        const cols = this._visibleCols(page);
        for (let i = 0; i < cols.length; i++) {
          const align = cols[i].align || "left";
          const just = align === "right" ? "flex-end" : align === "center" ? "center" : "flex-start";
          out.push(`:where([data-table="${page}"]) > :nth-child(${i + 1}) { text-align: ${align}; justify-content: ${just}; }`);
        }
      }
      return out.join("\n");
    },
    /* ---------------- P1-2 行窗口: 只决定"渲染哪一段", 不参与任何业务语义 ----------------
     * 三个窗口共用 _rowWindow(); 未启用时 win.active=false, 切片 = 全量、上下占位 = 0,
     * 模板与不开窗时完全等价(因此关掉开关就是老行为, 回退路径零成本)。 */
    torrentWin() {
      return this._rowWindow("torrent", this.filteredTorrents, "torrentTable");
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
     * 位置偏离"第 i 行在 i×step"的假设(硬约束 ②); 此时回退全量渲染, 宁可慢也不能错位。 */
    groupWin() {
      const n = this.filteredGroups.length;
      // ❗退避判据必须是"**当前真的有面板**", 不能只看 expandedKey 非空: 展开态现在会跨视图带回
      // (切回分组页时原组可能已被删/被筛掉, 见 app.js restoreExpandState), 为一个不存在的面板退避
      // = 大库上永久退化成全量渲染, 且用户完全看不出原因(界面一切正常, 只是滚动变卡)。
      if (this.expandedKey && this.filteredGroups.some((g) => g.key === this.expandedKey)) {
        return { active: false, start: 0, end: n, padTop: 0, padBottom: 0 };
      }
      return this._rowWindow("group", this.filteredGroups, "groupTable");
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
  },
};
