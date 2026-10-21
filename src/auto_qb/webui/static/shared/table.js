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
 *   <aq-row-pad> / <aq-empty>  列表外壳两件套(行窗口上下占位 / 空态块, 收敛 issue 26-10-20-2231,
 *                              见文件末尾段注释; 它们在「行 · 单元格」这套之外, 但同属列表表面)
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
 *
 * ============================ 对外契约(P6) ============================
 * 1722 P6 欠账于计划 26-10-12-0527 U0 交付(26-10-12-0533)。接入承诺的完整表述:
 * 「新增一个表格表面 = 注册一行描述符 + (新行模型才需)一个行渲染器;
 *   表壳 / 交互引擎 / 持久化 / 对齐 CSS 零改动」。
 *
 * ① 描述符(TABLE_DEFS / DRAWER_TABLE_DEFS 各一行; ALL_TABLE_DEFS 聚合, columns.js / sort.js
 *    按 table-id 消费 —— 列态 / grid / 对齐 / 持久化 / 排序 scope 全部 id 驱动):
 *      columns   列定义数组 { key, label, tpl(grid track), sortable, locked, align }
 *                —— 列能力与持久化的唯一事实源; 变体列子集 = 以经典列数组为底裁剪/追加(数据声明)
 *      label     面向用户的表名(列选择器分组标题)
 *      headRef   吸顶表头 ref 名; 表头渲染在**子组件内部**时恒 null → columns.js `_headEl` 走
 *                DOM 兜底(按 `.group-head[data-table="<id>"]` 查, 表头根自带 data-table)
 *      tableRef  行容器 ref 名(行窗口化测量消费); null = 无独立滚动容器
 *      grid      grid-template computed 名(_gridTemplate(id) 出 {gridTemplateColumns})
 *      cols      可见列 computed 名
 *      window    行窗口化 kind; 面板级数据量(数十~数百行)恒 null
 *      sort      { gk, gd, defKey, defDir } —— 根实例排序键/方向 data 字段名 + 三态第三击
 *                恢复目标; gk/gd 指向的字段须在 state.js **显式建字段**(后补属性不进响应式)
 *    [变体表扩展字段, 计划 26-10-12-0527 §3.2, U1 起生效]:
 *      rowModel  行模型名 → 渲染器组件(优先复用经典; 变体专属格新增单份渲染器)
 *      features  行为开关 { sort, resize, hide, window }
 *      hostAnchor  Teleport 锚选择器(见 ④)
 * ② 表壳 <aq-table>: props = tableId / cols / sortKey / sortDir / drag / mode("grid"|"thead")。
 *    只渲染表头 + emit("sort", key) —— 行为归调用方: 列头点击接 `setSort(key, tableId)`
 *    (表 id 即 scope, 无视图推断)。thead 模式不挂拖宽/重排/右键(借壳模式, HR 先例)。
 * ③ 行渲染器(aq-*-cells): **纯消费方** —— props = 可见列 cols + 行模型自然名属性(g/m/s/e/t/p/f);
 *    内部按 col.key 查表(v-if 链); 回调一律 `$root.xxx`(组件数据只有 props, 根数据走 $root,
 *    复制方法实现会触发 _scan_mixin_wiring 重名守阵); 模板走 xtpl-cells.html 的 x-template
 *    分片 + 三份 index.html manifest 行。
 * ④ 变体表格体锚约定(计划 26-10-12-0527 D1=M1): 变体外壳 dtHtml 在表格区输出空锚
 *    `<div data-dt-table-anchor="<tableId>"></div>`; drawer.html 以 `<Teleport :to>` 把表壳 +
 *    行渲染器传送进锚内(单一 Vue 应用, 非 createApp 子应用); 锚存在性由挂载机械在变体挂载后
 *    置响应式标志(W7 $nextTick 时序教训面 —— U1 四路径硬闸门: 初开/切页签/软切换/合并双列)。
 * ⑤ 接入 checklist: 描述符一行 → (新行模型才需)渲染器一份 → 列偏好键 = table-id(新增即隔离,
 *    绝不升 COLS_STORE_KEY 版本) → 三皮肤 CSS(对齐吃引擎 colAlignCss, 不手写列宽) →
 *    manifest 行 → 守阵计数锚同轮改版。
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
  /* 表头 a11y 件套单点(issue 26-10-12-0800, 计划 26-10-12-2330 方案 C) —— grid 与 thead 两模式
   * 共用一份, 不散在各调用方。语义载体用 role="columnheader"(**不是** button): aria-sort 只对该
   * role 生效, 挂 button 上读屏会忽略(那正是 issue 摘要里「读屏不知排序态」那一半的修法)。
   * 取值与箭头渲染判据同源(sortKey === col.key 才出方向), 保证任一时刻属性与箭头一致。 */
  methods: {
    headAriaSort(col) {
      if (!col.sortable || this.sortKey !== col.key) return null;   // 未命中列不输出(与 arrow 的 v-if 同源)
      return this.sortDir === 1 ? "ascending" : "descending";
    },
    headActivate(col) {
      if (!col.sortable) return;
      if (this.mode === "thead") this.$emit("sort", col.key);       // 借壳模式: 排序归调用方(D3=B)
      else this.$root.setSort(col.key, this.tableId);               // grid: 直连引擎排序单点
    },
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

/* ---------------- 站点 chip 单点(收敛 issue 26-10-20-2231 / 台账 R23-B-09) ----------------
 * group / torrent / ep 三处站点单元格此前各抄一份 11 行 chip 骨架(torrent 版还漏了 search-hit),
 * 只此一份。chip 是**单元格内**元素 —— 组件根即 span.site-chip, 渲染 DOM 与旧三份逐字同,
 * 不违反"单元格必须是行的直接子元素"(grid :nth-child 列对齐零影响)。
 * 与行渲染器同范式: 只贡献模板, 行为/格式化一律经 $root 回调根实例(不在本组件补方法)。 */
window.AQ_SITE_CHIP_COMPONENT = {
  name: "aq-site-chip",
  props: {
    m: { type: Object, required: true },         // 成员行(站点 chip 的数据源)
  },
  template: "#tpl-aq-site-chip",
};

/* ---------------- 变体表格体桥(计划 26-10-12-0527 U1, 拍板 D1 = Teleport 锚) ----------------
 * 变体外壳(字符串 DOM)在表格区输出空锚 `<div data-dt-table-anchor="<tableId>">`, 本组件把
 * 表壳 + 行渲染器传送进锚内 —— 单一 Vue 应用, 外壳零感知引擎, 引擎零感知外壳。
 * 锚代数(dtBridge, state.js)由挂载机械维护: 挂载自增/卸载清零, drawer.html 以 :key=代数
 * 强制宿主重建后重挂进当前锚(Vue 3 Teleport 目标被移除后不会自行迁回 —— 游离残留)。
 * 全部行为(排序/拖宽/右键隐藏/偏好/对齐)经 $root 走既有引擎单点, 本组件是纯声明:
 * 描述符(app.js DRAWER_TABLE_DEFS 变体行)声明 rows/rowKey/rowModel/rowProp 四件即接入。
 * !挂载时序四路径(U1 硬闸门): 初开 / 页签切换 / 软切换换目标 / 合并双列 —— e2e 钉死。 */
window.AQ_DT_BRIDGE_COMPONENT = {
  name: "aq-dt-bridge",
  props: {
    tab: { type: String, required: true },       // 桥归属页签(反查选中变体的 tableId)
  },
  template: "#tpl-aq-dt-bridge",
};

/* ---------------- U2 变体格渲染器(计划 26-10-12-0527, 用户表 07/08/09) ----------------
 * 「渲染器注册表」第三组 —— 与经典 aq-peer-cells 同范式(纯消费方: props = 可见列 cols +
 * 行模型自然名 p, 内部按 col.key 查表, 行为一律 $root.xxx)。行对象由变体注册条目的 rowsFn
 * 装配(drawer_templates.js dtTplRows 回调): 显示值 + _raw 原始值(排序走 _sortVal) + 变体
 * 修饰字段(flagToks 徽章数组 / up·down 微条宽度 / bad·lan·hand 行修饰) —— 渲染器只做
 * 声明式呈现, 判据零复制。行级修饰类(bad/lan/hand)不在这里: 走描述符 rowCls 绑 .group-row。
 *   dt07 四卡仪表 → <aq-dt07-cells>   dt08 五区分组 → <aq-dt08-cells>   dt09 密度雷达 → <aq-dt09-cells>
 * !issue 26-10-20-2231(三族重复收敛): 三变体值格模板合一为 tpl-aq-dt-peer-cells —— dt07 与
 * dt08 原本逐字同(仅 CSS 类名前缀), dt09 密度雷达三处特化(upspeed 占用条 / dlspeed 平铺 /
 * 列模型无 files)。差异经 pfx(类名前缀, 渲染结果与旧逐字同, 不撞三皮肤 CSS) + occ(占用条)
 * 两个 prop 表达; 三组件**同名不变**(动态名 'aq-' + rowModel + '-cells' 接线不动), 各自
 * 带默认 prop —— 加一个 peer 列只改模板一处, 漏一处 = 三变体该列齐空白(守阵盯并集)。
 * 模板在 tpl/xtpl-cells.html(同为 body 注入的 x-template, 无需 manifest 行)。 */
window.AQ_DT07_CELLS_COMPONENT = {
  name: "aq-dt07-cells",
  props: {
    cols: { type: Array, required: true },       // 可见列(visibleColsOf("drawerPeerV07"))
    p: { type: Object, required: true },         // dt07 行(rowsFn 装配)
    pfx: { type: String, default: "dt07" },      // CSS 类名前缀(渲染结果与旧逐字同)
    occ: { type: Boolean, default: false },      // 密度雷达特化(占用条/dlspeed 平铺); 四卡仪表 = false
  },
  template: "#tpl-aq-dt-peer-cells",
};

window.AQ_DT08_CELLS_COMPONENT = {
  name: "aq-dt08-cells",
  props: {
    cols: { type: Array, required: true },       // 可见列(visibleColsOf("drawerPeerV08"))
    p: { type: Object, required: true },         // dt08 行(rowsFn 装配)
    pfx: { type: String, default: "dt08" },
    occ: { type: Boolean, default: false },      // 五区分组 = false
  },
  template: "#tpl-aq-dt-peer-cells",
};

window.AQ_DT09_CELLS_COMPONENT = {
  name: "aq-dt09-cells",
  props: {
    cols: { type: Array, required: true },       // 可见列(visibleColsOf("drawerPeerV09"))
    p: { type: Object, required: true },         // dt09 行(rowsFn 装配)
    pfx: { type: String, default: "dt09" },
    occ: { type: Boolean, default: true },       // 密度雷达: upspeed 出占用条, dlspeed 平铺
  },
  template: "#tpl-aq-dt-peer-cells",
};

/* ---------------- U3 变体格渲染器(计划 26-10-12-0527, Tracker 04/05/06) ----------------
 *   dt04 状态卡片栅格 → <aq-dt04-cells>(卡片整体 = 单格满宽, 列头 CSS 隐藏)
 *   dt05 健康分组     → <aq-dt05-cells>(行三形态: 失败处置块/普通行/off 组 chips 合成行)
 *   dt06 增强表格     → <aq-dt06-cells>(8 列, 与经典用户列同范式) */
window.AQ_DT04_CELLS_COMPONENT = {
  name: "aq-dt04-cells",
  props: {
    cols: { type: Array, required: true },       // 可见列(visibleColsOf("drawerTrackerV04"))
    p: { type: Object, required: true },         // dt04 行(rowsFn 装配)
  },
  template: "#tpl-aq-dt04-cells",
};

window.AQ_DT05_CELLS_COMPONENT = {
  name: "aq-dt05-cells",
  props: {
    cols: { type: Array, required: true },
    p: { type: Object, required: true },
  },
  template: "#tpl-aq-dt05-cells",
};

window.AQ_DT06_CELLS_COMPONENT = {
  name: "aq-dt06-cells",
  props: {
    cols: { type: Array, required: true },
    p: { type: Object, required: true },
  },
  template: "#tpl-aq-dt06-cells",
};

/* ---------------- U4 变体格渲染器(计划 26-10-12-0527, 内容树 10/11) ----------------
 * 新行模型 drawerFileTree(D4=A 树缩进格进渲染器)的落点: 树缩进格(折叠钮/勾选框/缩进/
 * 图标/名称/徽章)两段同构单份口径 —— 列集 D2 各表声明, 分片按 col.key 查表(与经典
 * 同范式)。行对象由变体 rowsFn 装配(树聚合判据全在变体, 判据零复制); 行级修饰类
 * (dir/file/sel/is-chk/empty-row)走描述符 rowCls 绑 .group-row; 行级键盘(data-dt-key
 * 身份锚 + tabindex)归桥模板 U4 扩展, 本组件不感知。
 *   dt10 树 + 详情 → <aq-dt10-cells>   dt11 树表批量 → <aq-dt11-cells> */
window.AQ_DT10_CELLS_COMPONENT = {
  name: "aq-dt10-cells",
  props: {
    cols: { type: Array, required: true },       // 可见列(visibleColsOf("drawerContentV10"))
    p: { type: Object, required: true },         // dt10 行(rowsFn 装配)
  },
  template: "#tpl-aq-dt10-cells",
};

window.AQ_DT11_CELLS_COMPONENT = {
  name: "aq-dt11-cells",
  props: {
    cols: { type: Array, required: true },       // 可见列(visibleColsOf("drawerContentV11"))
    p: { type: Object, required: true },         // dt11 行(rowsFn 装配)
  },
  template: "#tpl-aq-dt11-cells",
};

/* ==================== 列表外壳两件套(收敛 issue 26-10-20-2231 / R23-A-05 · R23-B-06) ====================
 * <aq-row-pad>  P1-2 行窗口化的上下占位撑高件。此前四处逐字手写(groups 组行 / groups 明细成员 /
 *               torrents 种子行 / shows 集明细成员), 占位撑总高是滚动条长度与「滚到底」的契约 ——
 *               四处分散写法意味着改 aria-hidden 或 px 口径只改一处也不报错, 静默让两视图滚动几何
 *               分叉。**上下必须是两个实例**(占位要夹住中间的 v-for 行, 单个实例的渲染结果只能是
 *               连续的一段), 故每份列表实例化两个, 行本身仍由调用方 v-for 内联 —— 行窗口化
 *               「不引入逐行组件实例」的性能纪律不变(计划 26-10-11-1722 §06 风险 4)。
 * <aq-empty>    空态块。此前 12 处手写同一个三件套(`<div class="empty">` + svg.ico + span),
 *               其中设置页 HR 明细表三态与变体表兜底空态**连 svg 都没写**(视觉不一致)。
 *               **必须保留 `<div class="empty">` 根 + svg.ico + span 的子结构**: 三皮肤 CSS 按
 *               `.empty` 与 `.empty .ico` 选择(flex 纵列居中 + gap + 大 padding + 28px 图标),
 *               多包一层包裹或改类名会让整条空态样式失效且零报错。
 *               图标语义口径(此前无文档, 现单点写在 tpl/list-shell.html 头注):
 *                 inbox = 集合本身为空 / hourglass = 正在加载 / warn = 出错。
 * 两者都是**纯模板件**(零 methods): 组件只贡献 markup, 文案与数据全在调用方(列表三件套的
 * 嵌套三元已收敛到 filters.js 的 listEmptyText 单点)。
 * !模板在 tpl/list-shell.html 的两个 x-template, 注的是 body(与 combo-input/traffic-card 同范式)。
 */
window.AQ_ROW_PAD_COMPONENT = {
  name: "aq-row-pad",
  props: {
    height: { type: Number, default: 0 },   // 占位高度(px); 窗口外那段行的合计高, 由调用方的 Pad* 给
  },
  template: "#tpl-aq-row-pad",
};

window.AQ_EMPTY_COMPONENT = {
  name: "aq-empty",
  props: {
    /* 图标 sprite href —— 语义三选一, 缺省 inbox(集合确实是空的):
     *   #i-inbox 空 / #i-hourglass 加载中 / #i-warn 出错。三者互不替代, 见上面的口径注。 */
    icon: { type: String, default: "#i-inbox" },
    text: { type: String, default: "" },    // 空态文案(列表空态由调用方的 *EmptyText computed 给)
  },
  template: "#tpl-aq-empty",
};
