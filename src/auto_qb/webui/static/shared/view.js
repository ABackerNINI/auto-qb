/* view.js — 视图切换与搜索域(onSearchInput/resetSearch/doSearch/persistUiPage/goView/
 * stashExpandState/restoreExpandState/setViewMode): W2b 自 app.js 拆出, 全局 mixin 方法域。 */
/* 搜索自动刷新参数(plan 26-11-03-0120 F1, 三皮肤共用单点):
 * SEARCH_REFRESH_MIN_MS —— 静默重查最小间隔(P0 实测 3000 种子库: 窄查询 p95 39.7ms/1.2KB,
 *   宽查询(全库命中) p95 150.1ms/3.48MB, 超闸门"p95<=50ms 且响应<=500KB" -> 按判据取 2000ms);
 *   只在 search_rev 变化时才请求, 无数据变化不空转, 冷却仅防高频变更风暴。
 * SEARCH_REFRESH_HINT_MS —— 「结果已更新(+N 个种子)」提示停留时长。 */
const SEARCH_REFRESH_MIN_MS = 2000;
const SEARCH_REFRESH_HINT_MS = 3000;
window.AQB_VIEW = {
  methods: {
    onSearchInput(event) {
      // 输入防抖: 停止输入 400ms 后触发搜索; 清空则立即恢复辅种管理视图(不等防抖)
      if (this.searchTimer) clearTimeout(this.searchTimer);
      // 查询一变, 上一轮「结果已更新(+N)」的窗口立即作废(计数基准也随之失效)
      this._clearSearchRefreshHint();
      if (!(event.target.value || "").trim()) {
        this.resetSearch();
        return;
      }
      // 待响应期从武装防抖这一刻起算(不是 doSearch 才算): 否则首词的防抖窗 400ms 里
      // 空命中集照样把列表接管成 0 行(整页塌高, 见 filters.js::_searchGateActive)
      this.searchPending = true;
      this.searchTimer = setTimeout(() => this.doSearch(), 400);
    },
    resetSearch() {
      // 清空搜索结果并复位展开态: 搜索结果与普通分组结构不同(含虚拟行), 展开状态不跨视图残留
      this.searchHits = new Set();
      this.searchUncovered = [];
      this.searchBuilding = false;
      this.searchNegativeOnly = false;
      this.searchError = "";
      this.searchPending = false;
      // 自动刷新域一并复位: 结果已不存在, 版本号/提示窗口/索引续查都没有载体了
      this.searchRevApplied = -1;
      this._clearSearchRefreshHint();
      if (this._searchRefreshTimer) clearTimeout(this._searchRefreshTimer);
      this._searchRefreshTimer = null;
      this._searchRetryFails = 0;  // R4 清池(row135): 新搜索会话从零起算退避, 不带上一轮残值
      this.expandedKey = null;
    },
    async doSearch(quiet = false) {
      const q = (this.searchQuery || "").trim();
      if (!q) {
        this.resetSearch();
        return;
      }
      const useQuiet = !!quiet;
      if (useQuiet) {
        // 静默刷新(plan 26-11-03-0120 F2): 不武装 searchPending(列表保持现状, 落袋整集替换),
        // 不打断提示窗口; 防重入用独立标志(与手动搜索的在途态分开)
        if (this._searchRefreshBusy) return;
        this._searchRefreshBusy = true;
      } else {
        this.searchPending = true;  // 直达入口(searchHelpFill)不经 onSearchInput, 在此补武装
        this._clearSearchRefreshHint();  // 手动搜索: 上一轮自动刷新提示作废
      }
      try {
        const data = await this.api(`/api/search?q=${encodeURIComponent(q)}`);
        // 请求代际守卫(query 戳, 同 drawer.js _drawerStale 收口式): 落袋前比对当前搜索框
        // 词 —— a->b 连续输入时 a 的慢响应后到不得把命中集覆写成 a 的(搜索框显示 b、高亮
        // 集却是 a, 且无轮询自动纠正; issue 26-10-06-0028 F2-03)。清空搜索也随 searchQuery
        // 复位自动失配, 在途旧响应同样丢弃
        if ((this.searchQuery || "").trim() !== q) return;  // 失配弃单不动 pending(新词的 doSearch 已接管)
        const results = data.results || [];
        const prevHits = this.searchHits;  // 整集替换前的命中集(自动刷新提示的计数基准)
        this.searchHits = new Set(results.map((r) => r.hash));
        // 实际归组的种子由分组筛选展示; 未归组的命中(分组未启用/文件列表不可读)单独兜底
        const grouped = new Set();
        for (const g of this.groups) for (const m of g.members) grouped.add(m.hash);
        if (!useQuiet) this.searchPending = false;  // 本词落袋: 待响应期结束(静默刷新从未武装)
        this.searchUncovered = results.filter((r) => !grouped.has(r.hash));
        this.searchBuilding = !!data.building;
        this.searchNegativeOnly = !!data.negative_only;
        this.searchError = "";
        // 版本对齐(plan 26-11-03-0120 S4/F2): 服务端在取快照前记 rev, 故落袋即"至少覆盖到
        // 该版本"; 响应缺 rev(旧服务端)时保持旧值, 下次轮询自然再试
        this.searchRevApplied = typeof data.rev === "number" ? data.rev : this.searchRevApplied;
        if (useQuiet) this._noteSearchRefresh(prevHits);
        if (this.searchBuilding) {
          // 文件索引构建中(增量限流可能需多轮): 用**独立**定时器续查, 绝不复用输入防抖的
          // searchTimer —— 复用会让续查取消用户刚输入的防抖, 首词/改词被吞
          this._searchRetryFails = 0;  // R4 清池(row135): 成功一轮退避计数清零(同轮询 pollFails 口径)
          if (this._searchRefreshTimer) clearTimeout(this._searchRefreshTimer);
          this._searchRefreshTimer = setTimeout(() => this.doSearch(true), 1000);
        }
      } catch (e) {
        if ((this.searchQuery || "").trim() !== q) return;  // 旧请求的错误不得写进新词的状态
        if (!e.auth) {
          if (useQuiet) {
            // 静默刷新失败: 保留旧结果(不塌列表), 不弹错误; 若索引仍在构建则维持续查,
            // 否则等到下一轮 search_rev 变化再试(错误风暴由轮询退避吸收)
            if (this.searchBuilding) {
              if (this._searchRefreshTimer) clearTimeout(this._searchRefreshTimer);
              // R4 清池(row135): 失败重试走退避(逐次翻倍夹 15s 上限, 与轮询失败退避
              // currentPollMs 同曲线口径: base*2**fails, 指数封顶 4), 服务端宕机/持续
              // 5xx 不再形成固定 1 req/s 的无限重试循环; 成功一轮即清零(见上方 building 块)。
              this._searchRetryFails = Math.min(4, (this._searchRetryFails || 0) + 1);
              this._searchRefreshTimer = setTimeout(() => this.doSearch(true), Math.min(15000, 1000 * 2 ** this._searchRetryFails));
            }
          } else {
            // 不再静默(否则与"无匹配结果"无法区分): 401 由 api() 回登录框, 其余在搜索框旁提示
            const msg = e.message || "搜索失败";
            this.resetSearch();
            this.searchError = msg;
          }
        }
      } finally {
        if (useQuiet) this._searchRefreshBusy = false;
      }
    },
    /* 自动刷新提示(plan 26-11-03-0120 F4): 计数口径 = 本次命中集相对**提示窗口起点**新增的
     * hash 数(窗口内累计, 多轮刷新不重复计数); "0 命中 -> 有命中"同样按此口径显示(+N)。
     * 只增不减: 纯删除/改名不提示(不打扰); 查询变更/清空/切视图/手动搜索立即收窗口。 */
    _noteSearchRefresh(prevHits) {
      const base = this._searchHintBase || prevHits;
      let added = 0;
      for (const h of this.searchHits) if (!base.has(h)) added += 1;
      if (!added) return;
      this._searchHintBase = base;  // 窗口内沿用起点基准, 累计计数不因多轮刷新重复
      this.searchRefreshDelta = added;
      this.searchRefreshNotice = true;
      if (this._searchHintTimer) clearTimeout(this._searchHintTimer);
      this._searchHintTimer = setTimeout(() => this._clearSearchRefreshHint(), SEARCH_REFRESH_HINT_MS);
    },
    _clearSearchRefreshHint() {
      if (this._searchHintTimer) clearTimeout(this._searchHintTimer);
      this._searchHintTimer = null;
      this.searchRefreshNotice = false;
      this.searchRefreshDelta = 0;
      this._searchHintBase = null;
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
     * 不动焦点, 而 Chromium 在 keydown 分发时把焦点元素重估为 :focus-visible => 旧页签画出残留
     * outline。分发期间 matches(":focus-visible") 已翻转(实测探针), 没法用它区分焦点来源 => 直接
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
      this._clearSearchRefreshHint();  // 提示属于"当前视图的结果变化", 切视图即收(计划 26-11-03-0120 F4)
      try { localStorage.setItem("autoqb.ui.view", mode); } catch { /* 持久化失败不影响功能 */ }
      this.restoreExpandState(mode);  // 切回原视图时把展开态还回去(在 lastRid 置空取全量之前, 用旧行验存活性)
      // P1-1: 服务端只回当前视图的数组, 切视图后本地持有的 rid 与新视图的数据不再对应
      // => 置空强制下一轮取全量(切页首帧多一次全量, 换来的是之后每轮只传 1/4)
      this.lastRid = null;
      // fx(S6 后半, plan 26-10-31-2316): 主表三页签方向感知滑动的消费点(flux 专属,
      // flux/fx-mount.js::tabDir), 其它皮肤零调用
      if (this.ui === "flux" && window.AQB_FX_MOUNT) window.AQB_FX_MOUNT.tabDir(mode);
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
