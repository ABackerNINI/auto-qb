/* auto-qb WEB UI · 列模型交互(列宽/列序/列菜单/列持久化) + 行窗口化
 *
 * app.js 按域拆分出的片段(2026-09-20)。约定与 config_editor.js / config_rules.js 同一范式:
 * 挂到 window.AQB_COLUMNS, 由 app.js 末尾 app.mixin(window.AQB_COLUMNS) 注入同一个 Vue 实例 ——
 * 方法体里的 this 仍是那个组件实例, 跨模块互调与拆分前完全等价。
 *
 * !本文件在 HTML 里必须排在 app.js **之前**(app.js 末尾要读 window.AQB_COLUMNS);
 *   用到的列模型常量(TABLE_COLUMNS / MIN_COL_PX / STATE_RANK …)仍单点定义在 app.js 顶部。
 */
/* ============ 主表横滚指示条(计划 26-11-01-0553 S3) ============
 * 原生横条已被 shared/hscroll.css 彻底隐藏, 这里补回「拖动横滚」这一唯一会丢的能力:
 * 一根悬浮在状态栏上缘的胶囊(300x5, hover 7), 两条召唤路径:
 *   ① 指针伸进内容区底部 24px 带内(D5) —— 纵向带**不含状态栏**, 横向只认胶囊邻域(宽 + 左右各 40px);
 *   ② Shift+滚轮 / 触控板双指横滚时亮出, 停手 1.5s 自落(2026-11-01 用户追加)。
 * 可拖、可点轨道跳转。
 *
 * 为什么状态压在模块级闭包里: 本片段只有 methods(无 data / 无 mounted), 由 app.mixin 注入
 * **同一个** Vue 实例 —— 指示条是跨视图单例(三主表 v-if 互斥, 同时最多一个), 状态放进组件
 * data 反而要占命名空间、还得靠生命周期初始化。故一切状态在 HSCROLL_IND 里, DOM 惰性创建。
 * !变量名带 _IND 后缀: 各片段都是经典脚本, 顶层 const 共用全局词法作用域, 撞名即整页 SyntaxError。
 */
const HSCROLL_IND = {
  pill: null,      // 轨道单例(.hscroll-pill), 惰性创建
  thumb: null,     // 滑块(.hscroll-pill > i), 几何由 JS 写内联样式决定
  el: null,        // 最近一次 _hscrollSync 收到的主表容器(热区召唤时拿它重算)
  page: null,      // 该容器的表 id
  overflow: false, // 该容器当前是否有横向余量(热区 handler 只读这个布尔, 不读布局)
  hot: false,      // 指针是否在底部热区(纵向带内 **且** 横向落在胶囊邻域)
  bandIn: false,   // 指针是否已在纵向带内(每次入带只重算一次几何, 之后逐帧只做算术)
  pillW: 0,        // 胶囊实测宽(热区横向判据用; 由 _hscrollSync 量, 热路径上不读布局)
  wheelOn: false,  // Shift/触控板横滚召唤中(停手 1.5s 后自落)
  wheelT: 0,       // 上述停留定时器句柄
  drag: null,      // 拖拽会话 { id, x, left, maxThumb, maxScroll }
  bound: false,    // 文档级监听只挂一次
  ro: null,        // ResizeObserver(观察当前主表容器)
  roEl: null,
  raf: 0,
  sbH: -1,         // 状态栏实测高缓存; -1 = 未量(window resize 时清)
};

/* ---------------- P1-2 行窗口化 · 窗口源描述符(计划 26-11-02-0351 W2 参数化) ----------------
 * 窗口化的滚动几何原先散在方法里直读 window 全局(scrollY / innerHeight, 全页滚动硬编码);
 * 现抽成**按 kind 的窗口源描述符**: 滚动源 / 视口 / 容器顶偏移 / 滚动绑定 / 行键, 每 kind 一份。
 * - 主表三 kind(torrent/group/member)= 文档滚动型 WIN_SRC_DOC(原实现逐行搬入, 行为零变化);
 * - 容器型 winSrcContainer(预留, W3 接线 drawerContent): 滚动源 = 指定容器的 scrollTop,
 *   视口 = 容器 clientHeight, 绑定 = 元素 scroll 监听 + ResizeObserver(容器高变化不触发 window resize)。
 * 保守默认: kind 未在 WIN_SOURCES 注册时 _winSrc 回落 WIN_SRC_DOC —— 描述符缺失 = 现行为。
 * 每个描述符带 family("doc" | "container")源族标记, _rowWindow 按它分流滚动坐标系(issue
 * 26-11-03-1035): 不做对象身份比较 —— 克隆描述符(Object.assign 换行键)身份不等但同族。
 * _winTop 的几何口径两型对称: 文档型 = rect.top + scrollY(相对文档内容顶), 容器型 =
 * rect.top - 滚动容器rect.top + scrollTop(相对容器内容顶) —— rel = scrollY - top 都是
 * 「已滚进行块的距离」, _rowWindow 的前缀和算式两型共用。
 * bindScroll/unbindScroll 是绑定契约: 文档型的实际挂载仍单点在 lifecycle.js(P1-2 原样, 描述符
 * 与其逐字同款); 容器型由接线方消费 —— handler 约定 = 事件到达后按描述符重读 scrollY/viewH
 * 写回引擎态(this._winScrollY / this._winViewH), 即 _onWinScroll/_onWinResize 的合帧写法。
 */
/* WIN-SOURCES-BEGIN: 窗口化几何对 window.scrollY / window.innerHeight 的直读只允许出现在这一段 */
const WIN_SRC_DOC = {
  /* 源族标记(issue 26-11-03-1035): _rowWindow 按它分流坐标系, 不做对象身份比较 ——
   * group 等克隆描述符(Object.assign 换行键)与 WIN_SRC_DOC 身份不等但同族, 身份比较会把
   * 文档型 kind 误判进容器分支(读抽屉滚动坐标)。 */
  family: "doc",
  scrollY: () => window.scrollY,
  viewH: () => window.innerHeight,
  topOffset(el) {
    return el.getBoundingClientRect().top + window.scrollY;
  },
  bindScroll(handler) {
    window.addEventListener("scroll", handler, { passive: true });
  },
  unbindScroll(handler) {
    window.removeEventListener("scroll", handler);
  },
  keyOf(item) {
    return item.hash;  // torrent/member 的行键; group 覆盖为 item.key(见 WIN_SOURCES)
  },
};
const WIN_SOURCES = {
  torrent: WIN_SRC_DOC,
  member: WIN_SRC_DOC,
  group: Object.assign({}, WIN_SRC_DOC, { keyOf: (item) => item.key }),
  /* 抽屉内容树两变体(W3 接线, 计划 26-11-02-0351): 滚动源 = .drawer-body(抽屉滚动容器,
   * sticky-scrollpad-inset 坑档确认), 行键 = 行对象 k(文件路径, 描述符 rowKey 字段)。
   * getEl 惰性求值 —— 抽屉 v-if 未渲染时各函数逐次判空(scrollY/viewH 0 = 零差异回退)。 */
  drawerContent: Object.assign(winSrcContainer(() => document.querySelector(".drawer-body")), {
    keyOf: (item) => item.k,
  }),
};
/* 容器滚动型描述符工厂(W2 只交付形态, 不接线任何 kind): getEl 返回滚动容器元素
 * (惰性求值 —— 容器可能 v-if 未渲染, 各函数逐次判空: 未渲染 = scrollY 0 / viewH 0, 走零差异回退)。 */
function winSrcContainer(getEl) {
  return {
    family: "container",  // 源族标记(issue 26-11-03-1035): _rowWindow 按它分流, 见 WIN_SRC_DOC
    scrollY() {
      const el = getEl();
      return el ? el.scrollTop : 0;
    },
    viewH() {
      const el = getEl();
      return el ? el.clientHeight : 0;
    },
    topOffset(el) {
      const sc = getEl();
      if (!sc || !el) return 0;
      return el.getBoundingClientRect().top - sc.getBoundingClientRect().top + sc.scrollTop;
    },
    bindScroll(handler) {
      const el = getEl();
      if (!el) return;
      el.addEventListener("scroll", handler, { passive: true });
      // 容器视口高不随 window resize 变(抽屉抽成一条再撑回), 用 ResizeObserver 盯住:
      // 尺寸变化同 handler 一并通知(接线方合帧后重读 scrollY/viewH)。
      if (typeof ResizeObserver === "function") {
        this._ro = new ResizeObserver(() => handler());
        this._ro.observe(el);
      }
    },
    unbindScroll(handler) {
      const el = getEl();
      if (el) el.removeEventListener("scroll", handler);
      if (this._ro) {
        this._ro.disconnect();
        this._ro = null;
      }
    },
  };
}
/* WIN-SOURCES-END */

window.AQB_COLUMNS = {
  methods: {
  },
};
