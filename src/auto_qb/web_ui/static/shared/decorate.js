/* auto-qb WEB UI · 分组派生装饰(状态聚合/共同标签分类/图标文案)
 *
 * app.js 按域拆分出的片段(2026-09-20)。约定与 config_editor.js / config_rules.js 同一范式:
 * 挂到 window.AQB_DECORATE, 由 app.js 末尾 app.mixin(window.AQB_DECORATE) 注入同一个 Vue 实例 ——
 * 方法体里的 this 仍是那个组件实例, 跨模块互调与拆分前完全等价。
 *
 * ❗本文件在 HTML 里必须排在 app.js **之前**(app.js 末尾要读 window.AQB_DECORATE);
 *   用到的列模型常量(TABLE_COLUMNS / MIN_COL_PX / STATE_RANK …)仍单点定义在 app.js 顶部。
 */
window.AQB_DECORATE = {
  methods: {
    /* ------------------------------------------- 组级"共同值"计算(组级标签/分类列)
     *
     * 后端只透出成员原始值, 共同值(交集/一致值)在**前端**计算: 这类派生展示数据不参与
     * 后端视图重建判定, 且 computed 缓存后可复用, 无需让后端每轮做集合运算。
     */
    /* 组状态聚合口径(**单点**): 按 STATE_RANK 取"最该被看到"的成员状态 + 计数文案。
     *
     * `decoratedGroups` 与组行乐观补丁共用这一份 —— 两处各写一套必然漂移, 那就会出现
     * "点了暂停, 乐观算出的颜色和真值算出来的不一样"的抖动(见 STATE_RANK 注释)。
     */
    _aggStatus(members) {
      const counts = {};
      for (const m of members || []) counts[m.kind] = (counts[m.kind] || 0) + 1;
      const present = Object.keys(counts).sort((a, b) => this._rank(a) - this._rank(b));
      return {
        primary: present[0] || "other",
        // 计数文案按同一优先级排(与主色同序, 避免"颜色说 A、文案先说 B")
        text: present.map((k) => `${this.kindText(k)} ${counts[k]}`).join(" · "),
      };
    },
    /* kind -> 优先级数值(表里没有的 kind 排最后, 与后端 `_SHOW_STATE_RANK.get(k, 9)` 同口径) */
    _rank(kind) {
      return STATE_RANK[kind] === undefined ? STATE_RANK_LAST : STATE_RANK[kind];
    },
    /* 一组种子按同一张表聚合出的状态(供集行乐观补丁用: 与后端 e.state 同口径) */
    _aggKind(members) {
      let best = null;
      for (const m of members || []) {
        if (!m) continue;
        if (best === null || this._rank(m.kind) < this._rank(best)) best = m.kind;
      }
      return best;
    },
    _commonTags(members) {
      const sets = members.map((m) => new Set(m.tags || []));
      if (!sets.length) return { list: [], diff: false };
      const first = sets[0];
      let common = [...first];
      for (const s of sets.slice(1)) common = common.filter((t) => s.has(t));
      // 与站点名一致的标签(忽略大小写, 多为辅种工具自动打的"站点身份"标签)不展示: 站点列已有同名值, 纯冗余
      common = this._filterSiteTags(common, members);
      common.sort();
      // ± = 成员标签集合不完全相同(组级只显示共同标签, 差异提示避免误读为"全组一致")
      const diff = sets.some((s) => s.size !== first.size || [...s].some((t) => !first.has(t)));
      return { list: common, diff };
    },
    /* 过滤与成员站点名一致(忽略大小写)的标签 —— 组级共同标签与明细行共用 */
    _filterSiteTags(tags, members) {
      const names = new Set((members || []).map((m) => (m.site || "").toLowerCase()).filter(Boolean));
      return (tags || []).filter((t) => !names.has(t.toLowerCase()));
    },
    /* 明细行标签: 先滤掉与站点名一致的标签再展示(折叠计数/悬浮 title 口径一致) */
    mTags(m) {
      return this._filterSiteTags(m.tags, [m]);
    },
    /* 站点配色已改回状态色(2026-09-15, 字体与背景都表示种子状态): 原 siteHue djb2 函数与 .sc-0..7 一起删除, 站点身份由 chip 文字表达 */
    /* 站点专属配色已移除(2026-09-15 用户要求回退): 字体与背景都用状态色, 原 siteHue djb2
     * 哈希机制与 .sc-0..7 一起删除, 站点身份由 chip 文字表达(见 memory-bank/pitfalls.md 回写) */
    _commonCategory(members) {
      const vals = members.map((m) => m.category || "");
      if (!vals.length) return { value: "", diff: false };
      const diff = vals.some((v) => v !== vals[0]);
      return { value: diff ? "" : vals[0], diff };
    },
    kindText(kind) {
      return { seeding: "做种", downloading: "下载", checking: "校验中", paused: "已暂停", error: "错误", other: "其他" }[kind] || kind;
    },
    /* 单种子状态文案: 错误状态优先显示**后端算好的具体原因**(error_reason: "文件丢失" /
     * tracker 报错原文), 其余状态回落 kindText。原因文本一律由后端给出(取数单点), 前端不得
     * 按 state 猜原因。kindText 仍用于状态图例/筛选器/组级与集级聚合文案 —— 那里没有
     * "某一种子的原因"可言。 */
    stateText(m) {
      if (!m || !m.kind) return "";
      if (m.kind === "error" && m.error_reason) return m.error_reason;
      return this.kindText(m.kind);
    },
    kindIcon(kind) {
      // 状态图标(与 sprite symbol 一一对应): 校验中用 i-pulse(配合 CSS 呼吸动画, 语义=进行中)
      return {
        seeding: "#i-upload", downloading: "#i-download", checking: "#i-pulse",
        paused: "#i-pause", error: "#i-warn", other: "#i-info",
      }[kind] || "#i-info";
    },
    tagSlice(list, n) {
      // 标签 chip 最多显示 n 个(其余折叠为 +N), 保持行高与列宽稳定
      return (list || []).slice(0, n);
    },
    /* HR 标签分类色(与后端 qbmanager._hr_view_tags 对应)
     *
     * pending = 已触发 HR 条件但尚未满足做种时长/分享率(需关注, 用最鲜亮的颜色);
     * done    = 已满足(可以放宽, 用另一组镇静的颜色)。判定依据是后端解析后的标签文本
     * (已展开 ${required_seeding_time} 变量), 因此与真正写入 qB 的标签逐字相等。
     * 组级列展示的是"共同标签"——若某标签全组共有, 则组内 HR 状态必然一致, 故用代表成员即可。
     */
    tagClass(tag, member) {
      if (!member) return "";
      if (member.hr_tag && tag === member.hr_tag) return "hr-pending";
      if (member.hr_tag_done && tag === member.hr_tag_done) return "hr-done";
      return "";
    },
  },
  computed: {
    /* 组级派生展示数据(依赖 groups, 仅在分组数据变化时算一次; 渲染多帧不重算):
     * 保存路径(筛选器)、状态摘要(图标+配色+计数)、共同标签/分类(含差异标记)、大小一致性
     *
     * 交集/共同值在**前端**计算: 后端只透出成员原始值, 避免每次视图重建做集合运算。
     */
    decoratedGroups() {
      return this.groups.map((g) => {
        return {
          ...g,
          save_path: (g.members[0] && g.members[0].save_path) || "",
          status: this._aggStatus(g.members),
          commonTags: this._commonTags(g.members),
          commonCategory: this._commonCategory(g.members),
          sizeMismatch: new Set(g.members.map((m) => m.size)).size > 1,
        };
      });
    },
    totalTorrents() {
      // 种子页数据源到位后直接取平铺数组长度(权威口径); 旧响应缺 torrents 时回退 分组+未归组 合计
      if (this.torrents.length) return this.torrents.length;
      return this.groups.reduce((n, g) => n + g.count, 0) + this.singles.length;
    },
    totalDl() {
      return this.groups.reduce((n, g) => n + g.dlspeed, 0);
    },
    totalUl() {
      return this.groups.reduce((n, g) => n + g.upspeed, 0);
    },
    /* 成员索引: groups ∪ singles = 全量种子(shows 明细只带 hash, 从这里取完整成员视图,
     * 避免响应体重复成员数据; bulkDelete 摘要计数同源于此) */
    memberByHash() {
      const map = new Map();
      for (const g of this.groups) for (const m of g.members) map.set(m.hash, m);
      for (const r of this.singles) if (!map.has(r.hash)) map.set(r.hash, r);
      for (const r of this.torrents) if (!map.has(r.hash)) map.set(r.hash, r);  // SEED_ITEM 全量(magnet_uri 等扩展字段在这份)
      return map;
    },
    /* 未识别折叠区: hash → 成员解析, 过同一套筛选/搜索, 按种子名排序 */
    unrecognizedTorrents() {
      const q = (this.searchQuery || "").trim().toLowerCase();
      const hits = this.searchHits;
      const out = [];
      for (const h of this.shows.unrecognized) {
        const m = this.memberByHash.get(h);
        if (!m) continue;
        if (!this._memberPass(m)) continue;
        const hit = hits.has(h);
        if (q && !hit) continue;
        out.push({ ...m, hit: q ? hit : false });
      }
      out.sort((a, b) => (a.name || "").localeCompare(b.name || ""));
      return out;
    },
  },
};
