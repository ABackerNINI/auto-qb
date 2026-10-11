/* auto-qb WEB UI · 表格公共组件(表壳 + 行模型单元格渲染器)
 *
 * 计划 26-10-11-1722 的 P1/P2 落地。盘点结论: 四项列交互(拖拽换位 / 拖宽 / 点击排序 / 右键隐藏)
 * 的**行为**早已单点在 shared/columns.js(显隐/重排/调宽/对齐/持久化/行窗口化)与 shared/sort.js
 * (三态排序) —— **没单点的是模板**:
 *   · 表头块 5 份: groups.html 组头 + 明细头 · shows.html 剧头 + 明细头 · torrents.html 种子头;
 *   · 明细成员单元格 2 份逐字近似: groups.html(辅种页展开明细) / shows.html(追剧集成员)。
 * 本文件把这两处收敛为**单份**:
 *   <aq-table>        表壳: 列名 + 排序箭头 + 拖宽把手 + 重排指示线 + 表头右键(三皮肤同名类)
 *   <aq-member-cells> 明细成员行的单元格渲染器(member 行模型; 28 个列分支只此一份)
 * 两者都是**纯消费方**: 不搬行为、不持有状态 —— 表壳只渲染 + 回调, 行为仍在既有单点上。
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
    tableId: { type: String, required: true },   // 表 id(= TABLE_DEFS 键): group/detail/show/torrent
    cols: { type: Array, required: true },       // 可见列(顺序 = grid 模板序, 与值单元格同源)
    sortKey: { type: String, default: "" },      // 当前排序键(根数据, 由调用方传入)
    sortDir: { type: Number, default: 1 },
    drag: { type: Object, default: null },       // 根数据的 colDrag(本表命中时才画指示线/拖拽源类)
  },
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
