/* auto-qb WEB UI · 表格公共组件(表壳 + 行模型单元格渲染器)
 *
 * 计划 26-10-11-1722 的 P1/P2/P3 落地。盘点结论: 四项列交互(拖拽换位 / 拖宽 / 点击排序 / 右键隐藏)
 * 的**行为**早已单点在 shared/columns.js(显隐/重排/调宽/对齐/持久化/行窗口化)与 shared/sort.js
 * (三态排序) —— **没单点的是模板**:
 *   · 表头块 5 份: groups.html 组头 + 明细头 · shows.html 剧头 + 明细头 · torrents.html 种子头;
 *   · 行模型单元格 v-if 分支链 127 条: 散在 groups.html(49) / torrents.html(28) / shows.html(剧+集)
 *     / 明细成员单元格 2 份逐字近似(groups.html / shows.html)。
 * 本文件把这两处收敛为**单份**:
 *   <aq-table>         表壳: 列名 + 排序箭头 + 拖宽把手 + 重排指示线 + 表头右键(三皮肤同名类);
 *                      两模式(P5): grid = div 网格表头(主视图 4 表) / thead = 原生 <table>
 *                      表头行(设置页 HR 详情表; 调用方以 `<tr is="vue:aq-table" mode="thead">` 占位)
 *   <aq-member-cells>  明细成员行的单元格渲染器(member 行模型; 28 个列分支只此一份)
 *   <aq-group-cells>   group 行模型单元格渲染器(49 个分支, 原 groups.html 内联)
 *   <aq-torrent-cells> torrent 行模型单元格渲染器(28 个分支, 原 torrents.html 内联)
 *   <aq-show-cells> / <aq-ep-cells>  show-ep 行模型单元格渲染器(剧行 / 集行, 原 shows.html 内联)
 * 以上都是**纯消费方**: 不搬行为、不持有状态 —— 表壳只渲染 + 回调, 行为仍在既有单点上。
 *
 * !与根实例的接线(本应用是「单根组件 + 全局 mixin」架构: state.js/lifecycle.js 经根选项展开,
 *   其余片段经 app.mixin 注入同一个根实例): 组件模板里的 `$root.xxx` 即根实例上的同一个方法 ——
 *   与模板内联时的 `xxx(...)` 逐字节等价(`this` 仍是根实例), 且**不复制**任何方法实现
 *   (复制会触发 `_scan_mixin_wiring` 的重名守阵: mixin 后者覆盖前者, 被盖掉的实现永不执行)。
 *   WARN: 组件实例自身虽有 mixin 方法, 但**根数据**(sortKey/colDrag/viewMode/timeFmt/filters…)
 *   只在根实例上 —— 直接 `this.xxx` 会读到 undefined(排序键恒空、筛选高亮失灵), 故一律走 `$root`。
 *
 * !行仍由调用方 v-for 内联渲染(表壳组件只包表头): 3000 行窗口化的 patch 开销不能因"每行一个
 *   组件实例"而回升(计划 §06 风险 4)。明细单元格渲染器是**每成员行一个实例**(多根片段),
 *   不是每格一个 —— 单成员行 28 格包 28 个实例会把明细展开的 patch 成本抬一个量级。
 *
 * !模板放 tpl/xtpl.html 的 <script type="text/x-template">(与 hub-field 同范式): 该分片由
 *   tpl-manifest 注入 **body**(在 #app 之外), 故不会被当作根模板编译, 也不多包一层 DOM。
 * !本文件在 HTML 里必须排在 app.js **之前**(app.js 末尾要 `app.component(...)` 读 window.AQ_*)。
 */
window.AQ_TABLE_COMPONENT = {
  name: "aq-table",
  props: {
    tableId: { type: String, required: true },   // 表 id(= TABLE_DEFS 键): group/detail/show/torrent/hrDetail
    cols: { type: Array, required: true },       // 可见列(顺序 = grid 模板序, 与值单元格同源)
    sortKey: { type: String, default: "" },      // 当前排序键(根数据, 由调用方传入)
    sortDir: { type: Number, default: 1 },
    drag: { type: Object, default: null },       // 根数据的 colDrag(本表命中时才画指示线/拖拽源类)
    /* 渲染模式(计划 26-10-11-1722 P5): grid = div 网格表头(主视图 4 表, 默认);
     * thead = 原生 <table> 表头行(设置页 HR 详情表借壳)。两者共用一个组件(一份表壳) —— 差异只在
     * markup 族(div.h-cell vs tr>th)与行为开关: thead 模式不挂拖宽/重排/右键(那些行为只在
     * grid 模式存在), 排序状态仍归调用方(D3=B: 只借壳不并引擎), 组件只 emit("sort", key)。 */
    mode: { type: String, default: "grid" },
  },
  emits: ["sort"],
  template: "#tpl-aq-table",
};

window.AQ_MEMBER_CELLS_COMPONENT = {
  name: "aq-member-cells",
  props: {
    cols: { type: Array, required: true },       // 可见明细列(visibleDetailCols)
    m: { type: Object, required: true },         // 成员行(SEED_ITEM 的成员视角)
  },
  template: "#tpl-aq-member-cells",
};

/* ---------------- P3 行模型单元格渲染器(计划 26-10-11-1722) ----------------
 * 「渲染器注册表」= 下面四个组件 + 上面的 aq-member-cells 的 **app.component 注册块**(app.js 末尾)。
 * 行模型 → 组件单点:
 *   group      → <aq-group-cells>      (辅种组行)
 *   torrent    → <aq-torrent-cells>    (种子页平铺行)
 *   show-ep    → <aq-show-cells>       (追剧剧行) + <aq-ep-cells> (追剧集行; 同一列集两形态)
 *   member     → <aq-member-cells>     (展开明细成员行, P2 已落)
 * 每份渲染器内部按 `col.key` 查表(v-if 链), 列定义仍单点在 app.js 的 TABLE_DEFS[*].columns。
 * 模板放 tpl/xtpl-cells.html(member 在 xtpl.html, P2 先落) —— 同为 body 注入的 x-template。
 * WARN: 属性名保持各行的自然名(g/m/s/e)而非统一 row —— 分支体从页面模板**逐字搬入**,
 *   少改一字就少一处 DOM 等价风险(本轮的硬验收是渲染 DOM 逐字节等价)。
 */
window.AQ_GROUP_CELLS_COMPONENT = {
  name: "aq-group-cells",
  props: {
    cols: { type: Array, required: true },       // 可见辅种列(visibleGroupCols)
    g: { type: Object, required: true },         // 辅种组行(decoratedGroups 元素)
  },
  template: "#tpl-aq-group-cells",
};

window.AQ_TORRENT_CELLS_COMPONENT = {
  name: "aq-torrent-cells",
  props: {
    cols: { type: Array, required: true },       // 可见种子列(visibleTorrentCols)
    m: { type: Object, required: true },         // 平铺种子行(SEED_ITEM)
  },
  template: "#tpl-aq-torrent-cells",
};

window.AQ_SHOW_CELLS_COMPONENT = {
  name: "aq-show-cells",
  props: {
    cols: { type: Array, required: true },       // 可见追剧列(visibleShowCols)
    s: { type: Object, required: true },         // 剧行(decoratedShows 元素)
  },
  template: "#tpl-aq-show-cells",
};

window.AQ_EP_CELLS_COMPONENT = {
  name: "aq-ep-cells",
  props: {
    cols: { type: Array, required: true },       // 可见追剧列(visibleShowCols)
    e: { type: Object, required: true },         // 集行(decoratedShows 的 season.episodes 元素)
  },
  template: "#tpl-aq-ep-cells",
};

/* ---------------- 详情面板三表的行模型单元格渲染器(计划 26-10-11-2106 W2) ----------------
 * 「渲染器注册表」的第二组 —— 与上面四个同范式(纯消费方: 只渲染 + 回调 $root), 差别只在
 * **宿主是组件**: 三张表由 <aq-drawer-trackers>/<aq-drawer-peers>/<aq-drawer-content> 承载,
 * 故表头的 ref 够不到根实例(见 columns.js `_headEl` 的 DOM 兜底注释)。
 *   tracker-row → <aq-tracker-cells>   (Tracker 页签)
 *   peer-row    → <aq-peer-cells>      (用户页签)
 *   file-row    → <aq-file-cells>      (内容页签, 缩进树序 = 现行"树"形态)
 * 模板在 tpl/xtpl-cells.html 末尾(同为 body 注入的 x-template)。
 * !属性名保持各行的自然名(t/p/f)而非统一 row —— 与上面四个同理由: 分支体少改一字就少一处
 *   DOM 等价风险; 且列的 key 与行模型的字段同名, 排序取值才有落点(见 app.js 的列定义注释)。
 */
window.AQ_TRACKER_CELLS_COMPONENT = {
  name: "aq-tracker-cells",
  props: {
    cols: { type: Array, required: true },       // 可见列(visibleDrawerTrackerCols)
    t: { type: Object, required: true },         // tracker 行(drawerTrackerRows 元素)
  },
  template: "#tpl-aq-tracker-cells",
};

window.AQ_PEER_CELLS_COMPONENT = {
  name: "aq-peer-cells",
  props: {
    cols: { type: Array, required: true },       // 可见列(visibleDrawerPeerCols)
    p: { type: Object, required: true },         // 对端行(drawerPeerRows 元素)
  },
  template: "#tpl-aq-peer-cells",
};

window.AQ_FILE_CELLS_COMPONENT = {
  name: "aq-file-cells",
  props: {
    cols: { type: Array, required: true },       // 可见列(visibleDrawerFileCols)
    f: { type: Object, required: true },         // 文件行(drawerFileRows 元素)
  },
  template: "#tpl-aq-file-cells",
};
