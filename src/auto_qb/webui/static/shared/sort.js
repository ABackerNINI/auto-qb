/* auto-qb WEB UI · 排序(分组表/明细表/种子表)
 *
 * app.js 按域拆分出的片段(2026-09-20)。约定与 config_editor.js / config_rules.js 同一范式:
 * 挂到 window.AQB_SORT, 由 app.js 末尾 app.mixin(window.AQB_SORT) 注入同一个 Vue 实例 ——
 * 方法体里的 this 仍是那个组件实例, 跨模块互调与拆分前完全等价。
 *
 * ❗本文件在 HTML 里必须排在 app.js **之前**(app.js 末尾要读 window.AQB_SORT);
 *   用到的列模型常量(TABLE_COLUMNS / MIN_COL_PX / STATE_RANK …)仍单点定义在 app.js 顶部。
 */
window.AQB_SORT = {
  methods: {
    setSort(key, scope) {
      // 三态(想法.md): 首次点击按该列降序 -> 再点升序 -> 第三次恢复默认排序(最近添加时间降序);
      // 单种子/追剧视图操作独立排序键, 各视图互不干扰; scope="detail" 走展开明细表自己的键
      const { gk, gd } = this._sortKeys(scope);
      if (this[gk] !== key) {
        this[gk] = key;
        this[gd] = -1;
        return;
      }
      if (this[gd] === -1) {
        this[gd] = 1;
        return;
      }
      this._resetSort(scope);
    },
    /* 当前视图的排序键/方向(data 属性名) —— 分组/种子/追剧三视图各自独立;
     * scope="detail" = 展开明细表(与视图正交: 三视图的明细共用同一套排序键) */
    _sortKeys(scope) {
      if (scope === "detail") return { gk: "detailSortKey", gd: "detailSortDir" };
      if (this.viewMode === "torrents") return { gk: "torrentSortKey", gd: "torrentSortDir" };
      if (this.viewMode === "shows") return { gk: "showSortKey", gd: "showSortDir" };
      return { gk: "sortKey", gd: "sortDir" };
    },
    /* 恢复默认排序: 追剧视图 = 最近动静降序(后端同序); 明细表 = 后端原序(成员扫描顺序);
     * 其余 = 最近添加降序 */
    _resetSort(scope) {
      const { gk, gd } = this._sortKeys(scope);
      if (scope === "detail") {
        this[gk] = "";
        this[gd] = -1;
        return;
      }
      this[gk] = this.viewMode === "shows" ? "latest" : DEFAULT_SORT.key;
      this[gd] = DEFAULT_SORT.dir;
    },
    /* 明细表行序(展开的组明细 / 追剧集明细共用): 空键 = 后端原序, 点击列头后按该列三态排序;
     * 同值时按站点名稳定排序(与分组表"同值按名称"同思路, 避免刷新抖动)。
     * 数组字段(标签)先归并成字符串再比 —— 否则相减得到 NaN, 比较器语义失义。 */
    sortedMembers(list) {
      const key = this.detailSortKey;
      if (!key || !list) return list || [];
      const dir = this.detailSortDir;
      const val = (m) => {
        const v = m[key];
        return Array.isArray(v) ? v.join(",") : v;
      };
      return [...list].sort((a, b) => {
        const va = val(a);
        const vb = val(b);
        let r;
        if (typeof va === "string") r = (va || "").localeCompare(vb || "");
        else r = (va || 0) - (vb || 0);
        if (r === 0) r = (a.site || "").localeCompare(b.site || "");
        return dir * r;
      });
    },
  },
  computed: {
    sortedGroups() {
      const key = this.sortKey, dir = this.sortDir;
      return [...this.decoratedGroups].sort((a, b) => {
        const va = a[key], vb = b[key];
        let r;
        if (typeof va === "string") r = (va || "").localeCompare(vb || "");
        else r = (va || 0) - (vb || 0);
        // 同值时按名称稳定排序(avoid_on 同秒添加的组不会因排序抖动而互换位置)
        if (r === 0 && key !== "name") r = (a.name || "").localeCompare(b.name || "");
        return dir * r;
      });
    },
  },
};
