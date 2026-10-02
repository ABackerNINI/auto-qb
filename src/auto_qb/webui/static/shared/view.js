/* view.js — 视图切换与搜索域(onSearchInput/resetSearch/doSearch/persistUiPage/goView/
 * stashExpandState/restoreExpandState/setViewMode): W2b 自 app.js 拆出, 全局 mixin 方法域。 */
window.AQB_VIEW = {
  methods: {
    onSearchInput(event) {
      // 输入防抖: 停止输入 400ms 后触发搜索; 清空则立即恢复辅种管理视图(不等防抖)
      if (this.searchTimer) clearTimeout(this.searchTimer);
      if (!(event.target.value || "").trim()) {
        this.resetSearch();
        return;
      }
      this.searchTimer = setTimeout(() => this.doSearch(), 400);
    },
    resetSearch() {
      // 清空搜索结果并复位展开态: 搜索结果与普通分组结构不同(含虚拟行), 展开状态不跨视图残留
      this.searchHits = new Set();
      this.searchUncovered = [];
      this.searchBuilding = false;
      this.searchNegativeOnly = false;
      this.searchError = "";
      this.expandedKey = null;
    },
    async doSearch() {
      const q = (this.searchQuery || "").trim();
      if (!q) {
        this.resetSearch();
        return;
      }
      try {
        const data = await this.api(`/api/search?q=${encodeURIComponent(q)}`);
        const results = data.results || [];
        this.searchHits = new Set(results.map((r) => r.hash));
        // 实际归组的种子由分组筛选展示; 未归组的命中(分组未启用/文件列表不可读)单独兜底
        const grouped = new Set();
        for (const g of this.groups) for (const m of g.members) grouped.add(m.hash);
        this.searchUncovered = results.filter((r) => !grouped.has(r.hash));
        this.searchBuilding = !!data.building;
        this.searchNegativeOnly = !!data.negative_only;
        this.searchError = "";
        if (this.searchBuilding) {
          // 文件索引构建中(增量限流可能需多轮): 1s 后自动重查, 直至 building 消除
          if (this.searchTimer) clearTimeout(this.searchTimer);
          this.searchTimer = setTimeout(() => this.doSearch(), 1000);
        }
      } catch (e) {
        // 不再静默(否则与"无匹配结果"无法区分): 401 由 api() 回登录框, 其余在搜索框旁提示
        if (!e.auth) {
          const msg = e.message || "搜索失败";
          this.resetSearch();
          this.searchError = msg;
        }
      }
    },
    /* 搜索语法浮卡(计划 26-09-28-0201 方案A): 开合 + 示例回填。
     * 语法语义单点在服务端 views.py::_parse_query —— 本卡只做入口, 不做任何匹配实现。 */
    toggleSearchHelp() {
      this.searchHelpOpen = !this.searchHelpOpen;
    },
    searchHelpFill(q) {
      // 示例行点击: 填入即搜(不等防抖), 收起浮卡并把焦点还给输入框(方便继续改词)
      this.searchHelpOpen = false;
      this.searchQuery = q;
      this.doSearch();
      this.$nextTick(() => { if (this.$refs.searchInput) this.$refs.searchInput.focus(); });
    },
    /* ---------------- 单种子视图交互(R08)与信息栏模式(R09) ---------------- */
    /* 顶层页面持久化(**唯一写入口**, 与列偏好同纪律): 只落"用户切到哪一页"这个意图,
     * 不落任何派生值; 读侧白名单在 initialPage()。写入失败(隐私模式/配额满)只影响
     * 刷新后的落点, 不该打断切页 —— 故吞掉异常。
     * WARN: 方法名不能叫 persistPage —— columns.js 已占用该名(列状态漏斗), 同名会互相覆盖。 */
    persistUiPage() {
      try {
        localStorage.setItem("autoqb.ui.page", this.page === "settings" ? "settings" : "groups");
      } catch { /* 写入失败: 本轮仍生效, 刷新后回落辅种页 */ }
    },
    /* W4: 顶栏一级导航(分组/种子/追剧)入口 — 复用 viewMode 三态; 从设置页点击时先回到辅种页,
     * 列宽重实体化契约由 watch(page) 与 setViewMode 内的 $nextTick 各自兜底, 路径与既有切页一致 */
    goView(mode) {
      if (this.page !== "groups") this.page = "groups";
      this.searchHelpOpen = false;  // 离开搜索框所在顶栏态: 浮卡跟着收起, 不带残留到其它视图
      this.setViewMode(mode);
      this.syncNavFocus(mode);
    },
    /* 切页后同步导航焦点(键盘切页旧页签残留高亮框, 用户报): 鼠标点过的页签持有焦点, 键盘切页
     * 不动焦点, 而 Chromium 在 keydown 分发时把焦点元素重估为 :focus-visible ⇒ 旧页签画出残留
     * outline。分发期间 matches(":focus-visible") 已翻转(实测探针), 没法用它区分焦点来源 ⇒ 直接
     * 维护不变式: 切页后导航焦点要么恰在新活动页签上(点击/Tab+Enter 路径同值, 保留 —— 不打断
     * 键盘 Tab 序), 要么归还 body(鼠标残留焦点)。设置页签无 data-view, 不受影响。 */
    syncNavFocus(mode) {
      const el = document.activeElement;
      if (!el || el.tagName !== "BUTTON" || !el.hasAttribute("data-view")) return;
      if (el.getAttribute("data-view") === mode) return;
      el.blur();
    },
    /* ---------------- 展开态的跨视图记忆 ----------------
     * 用户报「辅种页切到种子页再切回, 展开的组收起来了」: 旧实现在 setViewMode 里一律置空,
     * 展开态随切页丢掉。改法是**按视图分桶暂存** —— 切走时收进 expandMemo 并清空实时字段
     * (展开态仍不串台到别的视图), 切回时还回该视图最后一次的展开。
     * !还回前必须验"那一行还在": 组可能已被删或被筛掉, 为一个不存在的面板留着 expandedKey
     *   会让 groupWin 永久退避行窗口(见 columns.js)—— 大库上等于悄悄关掉 P1-2 优化。 */
    stashExpandState() {
      if (this.viewMode === "groups") this.expandMemo.groups = this.expandedKey;
      else if (this.viewMode === "shows") {
        this.expandMemo.shows = { shows: this.expandedShows.slice(), ep: this.expandedShowEp };
      }
      this.expandedKey = null;
      this.expandedShows = [];
      this.expandedShowEp = null;
    },
    restoreExpandState(mode) {
      if (mode === "groups") {
        const key = this.expandMemo.groups;
        this.expandMemo.groups = null;  // 一次性: 还回去即空桶, 不留过期残值
        if (key && this.groups.some((g) => g.key === key)) this.expandedKey = key;
        return;
      }
      if (mode === "shows") {
        const memo = this.expandMemo.shows;
        this.expandMemo.shows = null;
        if (!memo) return;
        // shows 是 {list, unrecognized}(不是数组) —— 取数别写成 this.shows.map
        const alive = new Set((this.shows.list || []).map((s) => s.key));
        this.expandedShows = memo.shows.filter((k) => alive.has(k));
        // 集键形如 "<剧键>|季|集键"(showEpRowId): 剧还在才还回; 剧没了整条记忆一起丢
        const epShow = memo.ep ? String(memo.ep).split("|")[0] : "";
        this.expandedShowEp = epShow && alive.has(epShow) ? memo.ep : null;
      }
    },
    setViewMode(mode) {
      if (this.viewMode === mode) return;
      this.stashExpandState();
      this.viewMode = mode;
      try { localStorage.setItem("autoqb.ui.view", mode); } catch { /* 持久化失败不影响功能 */ }
      this.restoreExpandState(mode);  // 切回原视图时把展开态还回去(在 lastRid 置空取全量之前, 用旧行验存活性)
      // P1-1: 服务端只回当前视图的数组, 切视图后本地持有的 rid 与新视图的数据不再对应
      // ⇒ 置空强制下一轮取全量(切页首帧多一次全量, 换来的是之后每轮只传 1/4)
      this.lastRid = null;
      this.$nextTick(() => {
        this._syncHeadHeight();
        this.recomputeEffective();
      });
      // 立刻取一次新视图的数据, 不等下轮轮询(否则首次切到某视图要空/旧 ≤2s)。
      // scheduleNext 内部先 stopPolling 再排下一次, 所以这里不会造成双份轮询。
      if (this.authOk) this.refresh();
    },
  },
};
