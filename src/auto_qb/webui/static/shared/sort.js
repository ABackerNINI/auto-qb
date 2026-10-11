/* auto-qb WEB UI · 排序(分组表/明细表/种子表)
 *
 * app.js 按域拆分出的片段(2026-09-20)。约定与 config_editor.js / config_rules.js 同一范式:
 * 挂到 window.AQB_SORT, 由 app.js 末尾 app.mixin(window.AQB_SORT) 注入同一个 Vue 实例 ——
 * 方法体里的 this 仍是那个组件实例, 跨模块互调与拆分前完全等价。
 *
 * !本文件在 HTML 里必须排在 app.js **之前**(app.js 末尾要读 window.AQB_SORT);
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
    /* 当前表的排序键/方向(data 字段名 + 恢复默认序目标值) —— 全部取自表注册表。
     * scope 语义(计划 26-10-11-2106 W2 收敛): **表 id 即 scope** —— 表壳 <aq-table> 的列头点击
     * 直接把自己的 tableId 传下来(`setSort(col.key, tableId)`), 于是"点哪张表的头就排哪张表"
     * 不需要任何视图推断。传进来的不是已知表 id(含 undefined)时回落"当前视图的表"(VIEW_TABLE;
     * 未知/默认回落 group), 与 W2 之前的语义逐位一致 —— 主视图的 tableId 恒等于该视图的表 id,
     * 故那次改动对主视图是**零行为变化**。抽屉三表(W2 接壳)因此各有一座独立的排序键。 */
    _sortKeys(scope) {
      const id = ALL_TABLE_DEFS[scope] ? scope : (VIEW_TABLE[this.viewMode] || "group");
      return ALL_TABLE_DEFS[id].sort;
    },
    /* 恢复默认排序(三态第三击): 目标值随表走 —— 分组/种子 = 最近添加降序(DEFAULT_SORT),
     * 追剧 = 最近动静降序(后端同序), 明细 = 后端原序(空键)。见 TABLE_DEFS[*].sort.defKey/defDir */
    _resetSort(scope) {
      const { gk, gd, defKey, defDir } = this._sortKeys(scope);
      this[gk] = defKey;
      this[gd] = defDir;
    },
    /* 抽屉列表的行序(计划 26-10-11-2106 W2): 三张表各按**自己的**排序键(表壳列头点击落到
     * `dtrkSortKey` / `dpeerSortKey` / `dfileSortKey`, 见 DRAWER_TABLE_DEFS[*].sort)。
     * 空键 = 后端原序(与明细表同口径): 三态排序第三击回到空键即"恢复原序", 故排序永远可逆。
     * !取值走 `_sortVal`: 抽屉行模型带"显示值 + 原始值"两份(dlspeed 是 `fmtSpeedOrDash` 出的
     *   字符串), 直接按显示值比会把 "1.2 MiB" 按字典序排成 "12 MiB" 之后 —— 静默的错序。
     * !空值恒末位(两个方向都不反转): 与 HR 表 hrsCompareRows 同口径 —— 否则升序时 "—" 会窜到
     *   最前面, 用户一按升序看到的就是一屏无数据的行。 */
    sortedDrawer(tableId, list) {
      const rows = list || [];
      const def = DRAWER_TABLE_DEFS[tableId];
      const key = def ? this[def.sort.gk] : "";
      if (!def || !key) return rows;      // 空键 = 后端原序
      const dir = this[def.sort.gd];
      const val = (row) => {
        const v = this._sortVal(row, key);
        return Array.isArray(v) ? v.join(",") : v;
      };
      return [...rows].sort((a, b) => {
        const va = val(a), vb = val(b);
        const ea = va === null || va === undefined || va === "";
        const eb = vb === null || vb === undefined || vb === "";
        if (ea || eb) return ea && eb ? 0 : (ea ? 1 : -1);
        let r;
        if (typeof va === "string" || typeof vb === "string") r = String(va).localeCompare(String(vb));
        else r = va - vb;
        return r === 0 ? 0 : dir * r;
      });
    },
    /* 抽屉行的排序取值: 优先 `_raw` 侧(行装配时挂在行对象上), 没有则回落同名显示字段。
     * 主视图的行模型没有 `_raw` 这一层 —— 但它们不走本函数(各有自己的 comparator)。 */
    _sortVal(row, key) {
      if (!row || typeof row !== "object") return row;
      const raw = row._raw;
      if (raw && typeof raw === "object" && key in raw) return raw[key];
      return row[key];
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
