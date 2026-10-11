/* auto-qb WEB UI · 详情面板四页签的 Vue 组件(计划 26-10-11-2106 W2)
 *
 * 与 <aq-table> 同范式: 组件**只贡献模板与最小实例态**, 数据与动作一律经 $root 回调根实例
 * (组件模板里的 $root.xxx 即根实例上的同一个方法, 与模板内联时逐字节等价; 且**不复制**任何
 * 方法实现 —— 复制会触发 _scan_mixin_wiring 的重名守阵: 后者覆盖前者, 被盖掉的永不执行)。
 * 模板放 tpl/drawer-tabs.html(x-template, tpl-manifest 注入 body); 本文件在 HTML 里必须排在
 * app.js **之前**(app.js 末尾要 app.component(...) 读 window.AQ_*), 并排在 drawer.js
 * 之后(其 dtHostOn 消费核心层的显隐判据, 运行时才求值)。
 *
 * !与旧字符串 DOM 的关系(历史): W2 双实现期(计划 §08 R7「单一挂载点 + 特性开关」)页签选中
 *   「经典」时由本组件渲染、选变体时走旧字符串插件(drawer_tpl/<NN>-*.js 挂 .dt-host), 两者
 *   v-if/v-else 互斥。W5(计划 26-10-11-2106)变体整体退役 —— 本组件成为页签**唯一**渲染实现,
 *   旧插件挂载锚(data-dt-host)随宿主退役; 本组件根仍带 .dt-host 类但不带 data-dt-host
 *   (防插件机械复活的结构性隔离, 见 tpl/drawer-tabs.html 头注)。
 *
 * !列表装配收在组件 computed(而非经 prop 从调用方传入): 旧插件的行装配只在「本页签被通知」
 * 时跑一次, 若改由 drawer.html 的模板绑定传参, 根实例每次重渲染(任意响应式依赖变化)都会跑一遍
 * drawerFileRows() 的构树+扁平化 —— 万级文件列表上是实打实的回归。computed 是惰性的且只在
 * 内容门为真(v-if)时才被求值, 频次与旧插件同界。成员名全局唯一(跨片段 mixin 重名守阵).
 */

/* 页签 UI 态: 原始字段折叠区展开态。旧实现放在插件文件的模块级(抽屉开合/换变体再回来都保留),
 * 这里同语义 —— data() 里放同一对象的引用, Vue 把它包成响应式代理(同一对象跨实例缓存同一代理),
 * 于是重建组件不丢展开态(与旧 ui.rawOpen 的寿命一致)。 */
var AQB_DRAWER_TAB_UI = { generalRaw: false };

window.AQ_DRAWER_GENERAL_COMPONENT = {
  name: "aq-drawer-general",
  props: {
    d: { type: Object, default: null },   // 详情(drawer.detail); 空值即空面板(显隐另由 dtHostOn 门)
  },
  template: "#tpl-aq-drawer-general",
  data() {
    return { ui: AQB_DRAWER_TAB_UI };
  },
};

window.AQ_DRAWER_TRACKERS_COMPONENT = {
  name: "aq-drawer-trackers",
  template: "#tpl-aq-drawer-trackers",
  computed: {
    /* 行装配单点在根实例 drawerTrackerRows()(W2 从本文件平移过去 —— 它是数据层职责, 与渲染无关);
     * 本 computed 只加一层**排序**(表头点击落到 dtrkSortKey, 见 DRAWER_TABLE_DEFS[*].sort)。
     * 空键 = 后端原序(三态排序第三击回空键, 排序永远可逆)。 */
    trkRows() {
      const ctx = this.$root;
      return ctx.sortedDrawer("drawerTracker", ctx.drawerTrackerRows());
    },
  },
};

window.AQ_DRAWER_PEERS_COMPONENT = {
  name: "aq-drawer-peers",
  template: "#tpl-aq-drawer-peers",
  computed: {
    /* 对端行装配单点在根实例 drawerPeerRows()(dict/array 双形态归一 + 速度键名适配),
     * 组件只消费 + 按 dpeerSortKey 排序 —— 结构逐列与经典链一致(9 列)。 */
    peerRows() {
      const ctx = this.$root;
      return ctx.sortedDrawer("drawerPeer", ctx.drawerPeerRows());
    },
  },
};

window.AQ_DRAWER_CONTENT_COMPONENT = {
  name: "aq-drawer-content",
  template: "#tpl-aq-drawer-content",
  computed: {
    /* 文件行装配单点在根实例 drawerFileRows()(构树/扁平化/缩进深度/优先级翻译), 组件只消费 +
     * 按 dfileSortKey 排序; 选中态是 app 级单点 drawerSelPath(rename-fs 的作用对象), 模板按行绑定。
     * !按大小/进度排一棵**已扁平化的树**是"顺序被打散"的语义 —— 但它是可逆的(第三击回空键 =
     *   原树序), 且与主视图"任何列都可排序"同口径, 故不另设闸门(计划 §07 表 D: features = sort)。 */
    fileRows() {
      const ctx = this.$root;
      return ctx.sortedDrawer("drawerFile", ctx.drawerFileRows());
    },
  },
};
