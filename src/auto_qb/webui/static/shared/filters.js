/* auto-qb WEB UI · 筛选器(状态/标签/分类/站点/路径)
 *
 * app.js 按域拆分出的片段(2026-09-20)。约定与 config_editor.js / config_rules.js 同一范式:
 * 挂到 window.AQB_FILTERS, 由 app.js 末尾 app.mixin(window.AQB_FILTERS) 注入同一个 Vue 实例 ——
 * 方法体里的 this 仍是那个组件实例, 跨模块互调与拆分前完全等价。
 *
 * ❗本文件在 HTML 里必须排在 app.js **之前**(app.js 末尾要读 window.AQB_FILTERS);
 *   用到的列模型常量(TABLE_COLUMNS / MIN_COL_PX / STATE_RANK …)仍单点定义在 app.js 顶部。
 */
window.AQB_FILTERS = {
  methods: {
    /* ------------------------------------------- 筛选(状态/路径/标签/分类/站点)与搜索清除 */
    /* 一行的候选值(标签/分类/站点/路径) —— 组行取**全体成员值**, 种子行取自身。
     * 组内同一值只算一次(计数口径见 _facetOptions: 组视图 = 含该值的**组数**, 不是成员总数)。
     * 空值(未设分类/站点)不计入选项 —— 与改造前 `_memberValueOptions` 的口径一致。 */
    _facetPick(row, kind) {
      const rows = row.members || [row];
      const out = [];
      for (const r of rows) {
        if (kind === "tag") out.push(...(r.tags || []));
        else if (kind === "category" && r.category) out.push(r.category);
        else if (kind === "site" && r.site) out.push(r.site);
        else if (kind === "path") out.push(r.save_path || "");
      }
      return out;
    },
    /* 选项(带计数, 按出现行数降序, 同数按值排序): 四个筛选器共用一份实现 */
    _facetOptions(kind) {
      const counts = new Map();
      for (const row of this.facetRows) {
        const seen = new Set();
        for (const v of this._facetPick(row, kind)) {
          if (seen.has(v)) continue;
          seen.add(v);
          counts.set(v, (counts.get(v) || 0) + 1);
        }
      }
      return [...counts.entries()]
        .map(([value, count]) => ({ value, count }))
        .sort((a, b) => b.count - a.count || a.value.localeCompare(b.value));
    },
    toggleFilterValue(field, value) {
      const cur = this[field] || [];
      this[field] = cur.includes(value) ? cur.filter((v) => v !== value) : [...cur, value];
      this.expandedKey = null;  // 筛选后组集合变化, 复位展开态
    },
    isFilterOn(field, value) {
      return (this[field] || []).includes(value);
    },
    clearFilter(field) {
      this[field] = [];
      this.expandedKey = null;
    },
    toggleKindFilter(kind) {
      this.kindFilter = this.kindFilter === kind ? "" : kind;
      this.expandedKey = null;  // 筛选后组集合变化, 复位展开态
    },
    /* 筛选弹层互斥展开(同一时刻只开一个: 避免多个浮层叠在一起);
     * 打开时测量锚点位置: 靠右(左对齐会伸出视口)则翻转成右对齐 —— 消除横向滚动条 */
    toggleFilterMenu(kind, ev) {
      if (this.filterMenu === kind) { this.filterMenu = ""; return; }
      this.filterMenu = kind;
      this.popFlip = this._menuOverflowsRight(ev && ev.currentTarget, 260);
    },
    clearFilters() {
      this.kindFilter = "";
      this.pathFilter = [];
      this.tagFilter = [];
      this.categoryFilter = [];
      this.siteFilter = [];
      this.hrFilter = [];
      this.hrSrcFilter = [];
      this.filterMenu = "";
      this.expandedKey = null;
    },
    clearSearch() {
      if (this.searchTimer) clearTimeout(this.searchTimer);
      this.searchTimer = null;
      this.searchQuery = "";
      this.resetSearch();
    },
  },
  computed: {
    /* 筛选器选项的取数面(**单点**): 必须与当前视图真正在筛的那一行集合一致 ——
     * 组视图 / 追剧视图按**组**(计数 = 含该值的组数), 种子页按**种子**(计数 = 含该值的种子数)。
     *
     * ❗不能一律按组算: 种子页按视图分片**不回 groups**(`VIEW_ARRAYS["torrent"] = ("torrents",)`),
     *   而筛选弹层的选项原先只遍历 groups ⇒ 四个筛选器恒空、弹层显示"暂无数据"
     *   (2026-09-21 用户报「种子页筛选器无数据」)。
     * ❗也不能一律按种子算: 组视图同理不回 torrents, 且组级筛选的语义是"含该值的组"。
     * · 追剧视图回传 groups(VIEW_ARRAYS), 明细成员就在组里 ⇒ 与组视图同源, 不必单列一支。
     * · 种子页平铺数组还没到时回落组视图口径(首轮/旧服务端): 那时两处都是空, 不会给出错的计数。 */
    facetRows() {
      if (this.viewMode === "torrents" && this.torrents.length) return this.torrents;
      return this.decoratedGroups;
    },
    filtersActive() {
      return !!(this.kindFilter || this.pathFilter.length || this.tagFilter.length || this.categoryFilter.length ||
        this.siteFilter.length || this.hrFilter.length || this.hrSrcFilter.length || (this.searchQuery || "").trim());
    },
    /* 四个筛选器的定义(模板只遍历这一份, 不再手写四块相同结构)
     * 路径筛选器与其它三个同形(多选数组): 选中项存 field 指向的数组, 计数口径见 facetRows
     */
    filterDefs() {
      return [
        { kind: "tag", label: "标签", icon: "i-tag", options: this.tagOptions, selected: this.tagFilter, field: "tagFilter" },
        { kind: "category", label: "分类", icon: "i-folder", options: this.categoryOptions, selected: this.categoryFilter, field: "categoryFilter" },
        { kind: "site", label: "站点", icon: "i-globe", options: this.siteOptions, selected: this.siteFilter, field: "siteFilter" },
        // H&R 筛选(2026-09-25 起四档: 不能删/可删/未核实, 口径见 hr.js hrOptions); 三个视图共用同一条筛选状态
        { kind: "hr", label: "H&R", icon: "i-hr", options: this.hrOptions, selected: this.hrFilter, field: "hrFilter" },
        // HR 来源副筛选(在线核实/本地兜底/策略): 结论来自优先级链哪一档 —— "只看本地兜底"
        // 正是最需要等在线核实结果的一批种子(计划 webui-hr-safety-display §5 P3)
        { kind: "hr-src", label: "HR 来源", icon: "i-hr", options: this.hrSrcOptions, selected: this.hrSrcFilter, field: "hrSrcFilter" },
        { kind: "path", label: "路径", icon: "i-folder-open", options: this.pathOptions, selected: this.pathFilter, field: "pathFilter" },
      ];
    },
    /* 标签/分类/站点/路径四个筛选器的选项 —— 一律走 _facetOptions(单点), 不各自遍历集合:
     * 分头遍历正是"种子页筛选器无数据"的成因(见 facetRows)。 */
    tagOptions() {
      return this._facetOptions("tag");
    },
    categoryOptions() {
      return this._facetOptions("category");
    },
    siteOptions() {
      return this._facetOptions("site");
    },
    pathOptions() {
      return this._facetOptions("path");
    },
    // 搜索是辅种管理的筛选: 在真实辅种组上筛选——组内任一成员命中即保留整组(组行沿用真实 key,
    // 组级操作可用), 仅命中成员 search-hit 高亮; 未归组的命中种子(分组未启用/文件列表不可读等)
    // 以单种子虚拟行兜底展示(虚拟行无组级操作, 右键退化为该种子的单种子菜单)。
    // 状态筛选(kindFilter)与之叠加: 先按成员状态筛组(组内任一成员为该状态即保留), 再做搜索匹配。
    filteredGroups() {
      const q = (this.searchQuery || "").trim();
      let base = this.sortedGroups;
      if (this.kindFilter) base = base.filter((g) => g.members.some((m) => m.kind === this.kindFilter));
      // 多选筛选: 同一筛选器内为"或"(任一命中), 不同筛选器之间为"且";
      // H&R 见 _hrBuckets 口径(组内任一成员落该档即保留整组)
      if (this.hrFilter.length) {
        base = base.filter((g) => this.hrFilter.some((b) => this._hrBuckets(g).includes(b)));
      }
      if (this.hrSrcFilter.length) {
        base = base.filter((g) => this.hrSrcFilter.some((b) => this._hrSrcBuckets(g).includes(b)));
      }
      if (this.pathFilter.length) {
        base = base.filter((g) => this.pathFilter.includes(g.save_path));
      }
      if (this.tagFilter.length) {
        base = base.filter((g) => g.members.some((m) => (m.tags || []).some((t) => this.tagFilter.includes(t))));
      }
      if (this.categoryFilter.length) {
        base = base.filter((g) => g.members.some((m) => this.categoryFilter.includes(m.category || "")));
      }
      if (this.siteFilter.length) {
        base = base.filter((g) => g.members.some((m) => this.siteFilter.includes(m.site)));
      }
      if (!q) return base;
      const hits = this.searchHits;
      const kept = [];
      for (const g of base) {
        let hit = false;
        const members = g.members.map((m) => {
          const isHit = hits.has(m.hash);
          if (isHit) hit = true;
          return { ...m, hit: isHit };
        });
        if (hit) kept.push({ ...g, members: members, virtual: false, hit: true });
      }
      for (const r of this.searchUncovered) {
        if (this.kindFilter && r.kind !== this.kindFilter) continue;
        if (this.hrFilter.length && !this.hrFilter.includes(this._hrBucketMember(r))) continue;
        if (this.hrSrcFilter.length && !this.hrSrcFilter.includes(this._hrSrcBucketMember(r))) continue;
        if (this.pathFilter.length && !this.pathFilter.includes(r.save_path || "")) continue;
        if (this.tagFilter.length && !(r.tags || []).some((t) => this.tagFilter.includes(t))) continue;
        if (this.categoryFilter.length && !this.categoryFilter.includes(r.category || "")) continue;
        if (this.siteFilter.length && !this.siteFilter.includes(r.site)) continue;
        kept.push({
          key: "u-" + r.hash, name: r.name, count: 1, virtual: true,
          dlspeed: r.dlspeed, upspeed: r.upspeed, uploaded: r.uploaded, size: r.size,
          total_size: r.size, save_path: r.save_path || "",
          // 未归组种子同样携带排序与 HR 字段, 保证搜索视图内排序/列显示与真实组一致
          added_on: r.added_on || 0,
          hr_triggered: r.hr_triggered ? 1 : 0,
          hr_pending: r.hr_triggered && !r.hr_satisfied ? 1 : 0,
          status: { primary: r.kind, text: this.kindText(r.kind) },
          commonTags: { list: this.mTags(r), diff: false },
          commonCategory: { value: r.category || "", diff: false },
          sizeMismatch: false,
          members: [{ ...r, hit: true }],
        });
      }
      return kept;
    },
    /* 种子页(R1A, 原 R08 单种子视图升级): 数据源 = state.torrents 全量平铺数组(SEED_ITEM),
     * 每个种子独立过同一套筛选(与分组视图的"组内任一命中保留整组"语义不同: 这里逐种子判定);
     * 搜索为**客户端文本过滤**(名称/站点/分类/标签/保存路径, 子串不区分大小写), 不依赖服务端
     * 文件搜索结果 —— 文件命中(searchHits)仅用作高亮; 排序独立(三态同分组表) */
    filteredTorrents() {
      const q = (this.searchQuery || "").trim().toLowerCase();
      const out = [];
      for (const r of this.torrents) {
        if (!this._memberPass(r)) continue;
        if (q && !this._torrentTextMatch(r, q)) continue;
        /* ❗刻意**不复制**成 { ...r, hit }: 每条 74 个字段, 复制要经一遍响应式代理的 get 陷阱
         * (3000 条 = 22 万次), 实测**仅这一句就 68ms** —— 比整个窗口渲染还贵。
         * 命中高亮改由模板问 searchHits(见 isHit), 语义不变; 顺带每轮少建 3000 个临时对象。 */
        out.push(r);
      }
      const key = this.torrentSortKey;
      const dir = this.torrentSortDir;
      out.sort((a, b) => {
        const va = a[key];
        const vb = b[key];
        let r;
        if (typeof va === "string") r = (va || "").localeCompare(vb || "");
        else r = (va || 0) - (vb || 0);
        if (r === 0 && key !== "name") r = (a.name || "").localeCompare(b.name || "");
        return dir * r;
      });
      return out;
    },
  },
};
