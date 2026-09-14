/* auto-qb WEB UI 前端(Vue 3 CDN, 无构建链): rid 增量轮询 + 命令投递 + 列宽记忆 */
/* global Vue, localStorage, confirm, alert */  // 声明浏览器全局, 消除编辑器 no-undef 红线
const { createApp } = Vue;

/* ---------------- 列表列模型(分组表 / 明细表) ----------------
 *
 * **单一来源**: 列头 / 行单元格 / grid 模板 / 列选择器 全部由这一份数组派生 —— 顺序天然一致。
 * (旧实现把"顺序"分散在表头、行内单元格与模板三处, 加列/改序极易错位, 且列宽按**索引**记忆,
 *  一旦支持隐藏列索引就会漂移。)
 *
 * locked: 不可隐藏(承载展开 caret / 组状态徽标 / 站点名, 隐藏后行就失去身份)
 * tpl:    默认列宽模板(minmax(最小px, 权重fr) 或 固定 px), 用于首次渲染与"恢复默认"
 */
const GROUP_COLUMNS = [
  { key: "name", label: "名称", tpl: "minmax(210px, 2.4fr)", sortable: true, locked: true },
  { key: "dlspeed", label: "下载", tpl: "minmax(88px, 1fr)", sortable: true },
  { key: "upspeed", label: "上传", tpl: "minmax(88px, 1fr)", sortable: true },
  { key: "uploaded", label: "总上传", tpl: "minmax(96px, 1fr)", sortable: true },
  { key: "size", label: "大小", tpl: "minmax(92px, 1fr)", sortable: true },
  { key: "total_size", label: "总大小", tpl: "minmax(100px, 1fr)", sortable: true },
  // 分类在标签之前(用户要求分组表/明细表口径一致); 列宽按**列 key**记忆 -> 换序不丢宽度
  { key: "category", label: "分类", tpl: "minmax(100px, 1.1fr)" },
  { key: "tags", label: "标签", tpl: "minmax(130px, 1.4fr)" },
  { key: "sites", label: "站点", tpl: "minmax(170px, 1.6fr)" },
  // H&R: 未满足做种时长/分享率的成员数 / 已触发 HR 的成员数(组级计数由后端算好, 见 qbmanager._build_group_view)
  { key: "hr", label: "H&R", tpl: "minmax(88px, 1fr)", sortable: true },
  { key: "count", label: "站数", tpl: "56px", sortable: true },
];
const DETAIL_COLUMNS = [
  { key: "site", label: "站点", tpl: "110px", locked: true },
  { key: "state", label: "状态", tpl: "76px" },
  { key: "dlspeed", label: "下载", tpl: "minmax(92px, 1fr)" },
  { key: "upspeed", label: "上传", tpl: "minmax(92px, 1fr)" },
  { key: "uploaded", label: "总上传", tpl: "minmax(92px, 1fr)" },
  { key: "size", label: "大小", tpl: "minmax(92px, 1fr)" },
  // 与分组表同序: 分类在标签之前
  { key: "category", label: "分类", tpl: "minmax(110px, 1.1fr)" },
  { key: "tags", label: "标签", tpl: "minmax(140px, 1.3fr)" },
  { key: "progress", label: "进度", tpl: "minmax(84px, 1fr)" },
  { key: "seeding_time", label: "做种时长", tpl: "minmax(124px, 1.1fr)" },
  // 分享率: 显示 实际/HR 要求(未配置分享率要求时只显示实际值)
  { key: "ratio", label: "分享率", tpl: "minmax(104px, 1fr)" },
  { key: "hash", label: "Hash", tpl: "80px" },
];
const TABLE_COLUMNS = { group: GROUP_COLUMNS, detail: DETAIL_COLUMNS };
const MIN_COL_PX = 56;    // 拖拽下限: 再窄列头就无法点击排序/再次拖拽了
const MAX_FIT_PX = 520;   // 双击自适应内容的上限(超长种子名不该把某一列撑爆)
const RESIZE_DRAG_THRESHOLD = 3;  // 拖列宽超过该位移(px)即视为"真拖拽", 释放时拦掉冒泡到 .h-cell 的 click(避免误触排序)
/* 列状态持久化: {widths:{page:{列key:"120px"}}, hidden:{page:[列key]}, manual:{page:bool}}
 * v2(按列索引的稀疏覆盖) -> v3(**按列 key** + 自适应策略变更) -> v4(新增 H&R/分享率列),
 * 结构或默认列集变更必须升版本(否则旧缓存里的 px 覆盖会与新列集错配)
 */
const COLS_STORE_KEY = "autoqb_cols_v4";

/* 默认排序: 辅种组按组内**最近添加**时间降序(新补进来的种子最需要被看到);
 * 其它列点击 3 次回到这里(见 setSort 的三态语义)
 */
const DEFAULT_SORT = { key: "added_on", dir: -1 };

const emptyColState = () => ({ widths: {}, hidden: {}, manual: {} });

function columnKeys(page) {
  return TABLE_COLUMNS[page].map((c) => c.key);
}

function columnDef(page, key) {
  return TABLE_COLUMNS[page].find((c) => c.key === key) || null;
}

/* 模板里的最小宽度(minmax 首参 或 固定 px) —— 新显示的列/自适应失败时用它兜底 */
function templateMinPx(tpl) {
  const m = String(tpl).match(/^minmax\((\d+(?:\.\d+)?)px/) || String(tpl).match(/^(\d+(?:\.\d+)?)px$/);
  return m ? Math.round(parseFloat(m[1])) : MIN_COL_PX;
}

function loadColState() {
  try {
    const raw = JSON.parse(localStorage.getItem(COLS_STORE_KEY));
    if (!raw || typeof raw !== "object") return emptyColState();
    const out = emptyColState();
    for (const page of ["group", "detail"]) {
      const keys = columnKeys(page);
      const w = (raw.widths || {})[page];
      if (w && typeof w === "object") {
        const clean = {};
        for (const [k, v] of Object.entries(w)) {
          if (keys.includes(k) && /^\d+px$/.test(v)) clean[k] = v;
        }
        if (Object.keys(clean).length) out.widths[page] = clean;
      }
      const h = (raw.hidden || {})[page];
      if (Array.isArray(h)) {
        // locked 列即使被写进存储也忽略(列定义变更后可能残留)
        out.hidden[page] = h.filter((k) => keys.includes(k) && !(columnDef(page, k) || {}).locked);
      }
      out.manual[page] = !!(raw.manual || {})[page];
    }
    return out;
  } catch {
    return emptyColState();
  }
}

const initialColState = loadColState();  // 模块级只读一次(data() 的初值来源)


const app = createApp({
  data() {
    return {
      token: "",  // 已验证通过的密钥(唯一可信身份); 仅 bootstrap 验证成功后提交
      pendingToken: "",  // 验证中的候选密钥(不参与渲染门控/请求头); 服务不可达时供"重试连接"复用
      tokenInput: "",
      authRequired: true,  // 遮罩唯一开关: 仅在密钥验证成功后置 false —— 与 token 赋值解耦, 防错误密钥瞬间主界面闪现
      authPending: false,  // 密钥验证中: 禁用提交、按钮显示"验证中…", 防重复提交
      authError: "",
      authErrorKind: "",   // "auth" = 密钥被拒(401); "unavailable" = 服务不可达(保留候选密钥供重试)
      page: "groups",
      groups: [],
      status: {},
      pollSec: 2,
      expandedKey: null,
      // 排序: 默认 = 组内最近添加时间降序(见 DEFAULT_SORT); 点击列头按 降序->升序->恢复默认 三态循环
      sortKey: DEFAULT_SORT.key,
      sortDir: DEFAULT_SORT.dir,
      groupColumns: GROUP_COLUMNS,
      detailColumns: DETAIL_COLUMNS,
      // 列状态(定义见文件顶部列模型; 列宽按**列 key** 记忆, 隐藏列由列选择器管理)
      colWidths: initialColState.widths,  // {page: {列key: "120px"}}
      colHidden: initialColState.hidden,  // {page: [列key]}
      colManual: initialColState.manual,  // {page: bool}: 是否手动调过列宽(调过则不再随窗口自适应)
      colMenuOpen: false,                 // 列选择器弹层开关
      menu: { visible: false, x: 0, y: 0, key: null, hash: null },
      serviceDown: false,  // 服务不可达(程序退出): 显示全局横幅, 轮询继续以便恢复后自动接上
      pollFails: 0,        // 连续失败次数(轮询退避: 2s→4s→8s→15s 上限)
      pollTimer: null,     // setTimeout 链式轮询句柄(上一轮结束后再计时, 不堆叠请求)
      lastRid: null,       // 已持有的分组视图版本(服务端 rid); null = 尚未取到(强制全量)
      idlePolls: 0,        // 连续无更新轮数(无变化退避: 2s→5s→10s; 有更新立即归零)
      searchQuery: "",       // 搜索关键字
      searchHits: new Set(),  // 命中种子 hash 集合(名称/文件匹配)
      searchUncovered: [],    // 未归组的命中种子(分组未启用/文件列表不可读), 以虚拟行兜底展示
      searchBuilding: false,  // 文件索引构建中(增量限流可能多轮, 需稍后重查)
      searchError: "",        // 搜索请求失败提示(不再静默)
      searchTimer: null,      // 防抖 + 索引构建自动重查定时器
      kindFilter: "",         // 状态筛选(seeding/downloading/... ; 空 = 不筛选)
      // 多选筛选(组内任一成员命中任一选中值即保留该组; 同一筛选器内多选为"或")
      // pathFilter 与其它筛选器同形(数组多选) —— 四个筛选器共用一份 filterDefs 与渲染模板
      pathFilter: [],
      tagFilter: [],
      categoryFilter: [],
      siteFilter: [],
      filterMenu: "",         // 当前展开的筛选弹层: "" | "tag" | "category" | "site" | "path"
      popFlip: false,         // 筛选弹层视口翻转(锚点靠右时改为右对齐, 避免伸出屏幕)
      colFlip: false,         // 列选择器弹层视口翻转(同上)
      toasts: [],             // 站内提示条(替代 alert)
      modal: {                // 站内确认/输入框(替代 confirm/prompt); 结构见 _modalInit
        visible: false, title: "", body: "", okText: "", cancelText: "",
        danger: false, input: false, value: "", placeholder: "",
      },
      _toastSeq: 0,           // 提示条自增 id
      _modalResolve: null,    // 模态 Promise 的 resolve(单例, 关闭时结算)
      _headH: 0,              // 顶栏+状态条实测高度(写 :root --head-h, 供左栏吸顶定位)
    };
  },
  computed: {
    pollLabel() {
      // 顶栏展示当前轮询间隔(自适应: 无变化/服务不可达时放慢)
      return Math.round(this.currentPollMs() / 1000);
    },
    statusBadge() {
      if (this.status.paused) return { text: "已暂停", kind: "warn" };
      if (this.status.connected === false) return { text: "qB 断开", kind: "error" };
      if (this.status.connected === true) return { text: "运行中", kind: "ok" };
      return { text: "连接中…", kind: "warn" };
    },
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
    /* 组级派生展示数据(依赖 groups, 仅在分组数据变化时算一次; 渲染多帧不重算):
     * 保存路径(筛选器)、状态摘要(图标+配色+计数)、共同标签/分类(含差异标记)、大小一致性
     *
     * 交集/共同值在**前端**计算: 后端只透出成员原始值, 避免每次视图重建做集合运算。
     */
    decoratedGroups() {
      const order = ["error", "checking", "downloading", "seeding", "paused", "other"];
      return this.groups.map((g) => {
        const counts = {};
        for (const m of g.members) counts[m.kind] = (counts[m.kind] || 0) + 1;
        const present = order.filter((k) => counts[k]);
        return {
          ...g,
          save_path: (g.members[0] && g.members[0].save_path) || "",
          status: {
            primary: present[0] || "other",
            text: present.map((k) => `${this.kindText(k)} ${counts[k]}`).join(" · "),
          },
          commonTags: this._commonTags(g.members),
          commonCategory: this._commonCategory(g.members),
          sizeMismatch: new Set(g.members.map((m) => m.size)).size > 1,
        };
      });
    },
    /* 保存路径筛选选项(按组数排序) —— 与标签/分类/站点同形, 供统一的 filterDefs 直接取用 */
    pathOptions() {
      const counts = new Map();
      for (const g of this.decoratedGroups) counts.set(g.save_path, (counts.get(g.save_path) || 0) + 1);
      return [...counts.entries()].map(([value, count]) => ({ value, count })).sort((a, b) => b.count - a.count);
    },
    filtersActive() {
      return !!(this.kindFilter || this.pathFilter.length || this.tagFilter.length || this.categoryFilter.length ||
        this.siteFilter.length || (this.searchQuery || "").trim());
    },
    /* 四个筛选器的定义(模板只遍历这一份, 不再手写四块相同结构)
     * 路径筛选器与其它三个同形(多选数组): 选中项存 field 指向的数组, 计数口径 = 组数
     */
    filterDefs() {
      return [
        { kind: "tag", label: "标签", icon: "i-tag", options: this.tagOptions, selected: this.tagFilter, field: "tagFilter" },
        { kind: "category", label: "分类", icon: "i-folder", options: this.categoryOptions, selected: this.categoryFilter, field: "categoryFilter" },
        { kind: "site", label: "站点", icon: "i-globe", options: this.siteOptions, selected: this.siteFilter, field: "siteFilter" },
        { kind: "path", label: "路径", icon: "i-folder-open", options: this.pathOptions, selected: this.pathFilter, field: "pathFilter" },
      ];
    },
    tagOptions() {
      return this._memberValueOptions((m) => m.tags || []);
    },
    categoryOptions() {
      return this._memberValueOptions((m) => (m.category ? [m.category] : []));
    },
    siteOptions() {
      return this._memberValueOptions((m) => (m.site ? [m.site] : []));
    },
    /* 列模板: computed 缓存(列宽/列显隐变化才变), 行渲染只取同一引用, 不再每行拼字符串 */
    groupGrid() {
      return { gridTemplateColumns: this._gridTemplate("group") };
    },
    detailGrid() {
      return { gridTemplateColumns: this._gridTemplate("detail") };
    },
    // 搜索是辅种管理的筛选: 在真实辅种组上筛选——组内任一成员命中即保留整组(组行沿用真实 key,
    // 组级操作可用), 仅命中成员 search-hit 高亮; 未归组的命中种子(分组未启用/文件列表不可读等)
    // 以单种子虚拟行兜底展示(虚拟行无组级操作, 右键退化为该种子的单种子菜单)。
    // 状态筛选(kindFilter)与之叠加: 先按成员状态筛组(组内任一成员为该状态即保留), 再做搜索匹配。
    filteredGroups() {
      const q = (this.searchQuery || "").trim();
      let base = this.sortedGroups;
      if (this.kindFilter) base = base.filter((g) => g.members.some((m) => m.kind === this.kindFilter));
      // 多选筛选: 同一筛选器内为"或"(任一命中), 不同筛选器之间为"且"
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
    expandedGroup() {
      return this.groups.find((g) => g.key === this.expandedKey) || null;
    },
    totalTorrents() {
      return this.groups.reduce((n, g) => n + g.count, 0);
    },
    totalDl() {
      return this.groups.reduce((n, g) => n + g.dlspeed, 0);
    },
    totalUl() {
      return this.groups.reduce((n, g) => n + g.upspeed, 0);
    },
    /* 状态分布(纯前端聚合 members[].kind): 供顶栏下方堆叠条与可点击图例使用 */
    distSegments() {
      const order = ["seeding", "downloading", "checking", "paused", "error", "other"];
      const count = {};
      for (const g of this.groups) for (const m of g.members) count[m.kind] = (count[m.kind] || 0) + 1;
      const total = order.reduce((n, k) => n + (count[k] || 0), 0);
      if (!total) return [];
      return order.filter((k) => count[k]).map((k) => ({
        kind: k, count: count[k], pct: (count[k] / total) * 100, text: this.kindText(k),
      }));
    },
    distTotal() {
      return this.distSegments.reduce((n, s) => n + s.count, 0);
    },
    distTitle() {
      return this.distSegments.map((s) => `${s.text} ${s.count}`).join(" · ");
    },
    /* ---------------- 限速/流量快照(后端 SpeedCurveMixin 发布, 随 status 恒回传) ----------------
     * state: disabled(未启用限速曲线) / ok / dry_run / stale(数据源不可用)
     * periods[].up|down 为**字节**; limit.target|actual 为 **KiB/s**(0 = 不限速, null = 该方向不管理)
     */
    traffic() {
      return this.status.traffic || { state: "disabled", periods: [], limit: {} };
    },
    trafficOn() {
      return this.traffic.state !== "disabled";
    },
    todayTraffic() {
      return (this.traffic.periods || []).find((p) => p.period === "day") || null;
    },
    /* 限速对照行: 每个受管方向一行(该方向无曲线则不显示该行);
     * mismatch = 实际值已知且与命中目标不同 -> 前端据此"显示两个 + 原因"
     * tip 在**这里**算好(按方向取原因), 避免每个 pill 都展示全部方向的原因
     */
    limitRows() {
      const lim = this.traffic.limit || {};
      const target = lim.target || {}, actual = lim.actual || {}, reasons = lim.reasons || [];
      // 无方向特定原因时的默认说明(按快照状态区分: 试运行/数据不可用/正常)。
      // 必须在此内联为局部量 —— 本区段是 computed, 任何"看似方法的辅助函数"都会变成属性,
      // 在 computed 内以 this.xxx() 调用会抛 TypeError 导致整块渲染失败(2026-09-14 实测)。
      const fallback = this.traffic.state === "dry_run"
        ? "试运行(dry_run): 只显示命中限速, 不读取/不写入 qB"
        : this.traffic.state === "stale"
          ? "流量数据暂不可用, 限速沿用上一轮生效值"
          : "命中 = 曲线目标值, 实际 = qB 当前生效值";
      const rows = [];
      for (const [dir, label] of [["up", "上传"], ["down", "下载"]]) {
        const tg = target[dir];
        if (tg === null || tg === undefined) continue;
        const ac = actual[dir];
        const reason = reasons.find((r) => r.dir === dir) || null;
        const known = ac !== null && ac !== undefined;
        rows.push({
          dir,
          label,
          target: tg,
          actual: ac,
          mismatch: known && ac !== tg,
          reason,
          tip: reason ? reason.text : fallback,
        });
      }
      return rows;
    },
    /* 可见列(列选择器只改 colHidden; 顺序始终取自列定义) —— 表头/行/grid 模板共用 */
    visibleGroupCols() {
      return this._visibleCols("group");
    },
    visibleDetailCols() {
      return this._visibleCols("detail");
    },
  },
  async mounted() {
    // 点击页面空白处: 关闭右键菜单与列选择器(两者都是临时浮层)
    window.addEventListener("click", () => {
      this.menu.visible = false;
      this.colMenuOpen = false;
      this.filterMenu = "";
    });
    // Esc: 优先关闭确认框, 其次右键菜单/列选择器(都是临时浮层)
    document.addEventListener("keydown", (e) => {
      if (e.key !== "Escape") return;
      if (this.modal.visible) this.resolveModal(false);
      else if (this.menu.visible) this.menu.visible = false;
      else if (this.colMenuOpen) this.colMenuOpen = false;
      else if (this.filterMenu) this.filterMenu = "";
    });
    // 列宽: 未手动调过时"实体化"为当前渲染 px(见 materializeColumns); 窗口变化后重新实体化,
    // 保持"填满容器 + 自适应"的观感; 手动调过则冻结(拖一列不再影响其它列)
    let resizeTimer = null;
    window.addEventListener("resize", () => {
      if (resizeTimer) clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => {
        this._syncHeadHeight();
        this.materializeColumns();
      }, 120);
    });
    this.$nextTick(() => {
      this._syncHeadHeight();
      this.materializeColumns();
    });
    // 页面可见性(与 qB 自带 WebUI 同策略): 后台标签停止轮询; 恢复可见立即刷新并续排
    document.addEventListener("visibilitychange", () => {
      if (document.hidden) this.stopPolling();
      else if (this.token) this.refresh();  // 登出态切回标签不发空 Bearer(由登录成功后自行启动轮询)
    });
    // 本地存储密钥必须重新验证后才放行遮罩; 密钥已轮换则由 401 收口清除
    const savedToken = localStorage.getItem("autoqb_token");
    if (savedToken) this.bootstrap(savedToken);
  },
  watch: {
    // 切回辅种页时表格 DOM 是新建的, 需要重新实体化列宽(设置页期间表格不存在)
    page() {
      this.$nextTick(() => {
        this._syncHeadHeight();
        this.materializeColumns();
      });
    },
  },
  updated() {
    // 顶栏高度会随"状态分布条是否渲染/窄屏折行"变化 -> 每帧后同步(值未变时内部直接返回)
    this._syncHeadHeight();
  },
  methods: {
    async api(path, options = {}) {
      if (!this.token) {
        // 无密钥不出网: 否则会发出 "Bearer " 空头(被 HTTP 层裁剪成裸 "Bearer"),
        // 后端白记一次 401。调用方按 401 同路径处理(回密钥输入界面/静默)。
        this._logout();
        const noAuth = new Error("unauthorized");
        noAuth.auth = true;
        throw noAuth;
      }
      return this._request(path, options, this.token);
    },
    async _request(path, options, token) {
      const resp = await fetch(path, {
        ...options,
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json", ...(options.headers || {}) },
      });
      if (resp.status === 401) {
        this._logout("密钥无效或已更换");
        const err = new Error("unauthorized");
        err.auth = true;
        throw err;
      }
      if (!resp.ok) {
        const detail = await resp.json().catch(() => ({}));
        throw new Error(detail.detail || `HTTP ${resp.status}`);
      }
      return resp.json();
    },
    _logout(message = "") {
      // 鉴权失败唯一收口: 遮罩、凭证、定时器与所有已加载的受保护数据一并清空——
      // 防错误密钥提交瞬间主界面(含上一会话残留的分组/设置)闪现, 也避免数据滞留内存视图
      this.authRequired = true;
      this.authPending = false;
      this.pendingToken = "";
      this.token = "";
      localStorage.removeItem("autoqb_token");
      this.stopPolling();
      if (this.searchTimer) clearTimeout(this.searchTimer);  // 登出后停掉搜索防抖/重试, 防空头竞态
      this.searchTimer = null;
      this.groups = [];
      this.status = {};
      this.lastRid = null;
      this.idlePolls = 0;
      this.pollFails = 0;
      this.serviceDown = false;
      this.expandedKey = null;
      this.kindFilter = "";
      this.pathFilter = [];
      this.tagFilter = [];
      this.categoryFilter = [];
      this.siteFilter = [];
      this.filterMenu = "";
      this.colMenuOpen = false;
      this.toasts = [];
      this.modal = this._modalInit();
      this._modalResolve = null;
      this.cfgReset();  // 配置树同样是受保护内容, 一并清除(编辑器状态复位)
      this.page = "groups";
      this.searchQuery = "";
      this.resetSearch();
      if (message) {
        this.authError = message;
        this.authErrorKind = "auth";
      }
    },
    /* ---------------------------------------------------------- 站内提示条(toast) */
    toast(text, kind = "info", ms = 4000) {
      const id = ++this._toastSeq;
      this.toasts.push({ id, text, kind });
      setTimeout(() => this._dropToast(id), ms);
    },
    _dropToast(id) {
      this.toasts = this.toasts.filter((t) => t.id !== id);
    },
    /* ------------------------------------------- 站内确认/输入框(替代 confirm/prompt) */
    _modalInit() {
      return {
        visible: false, title: "", body: "", okText: "", cancelText: "",
        danger: false, input: false, value: "", placeholder: "",
        checkbox: "", checked: false,  // 额外选项勾选框(如删除时"同时删除磁盘文件")
      };
    },
    confirmDialog(title, body, opts = {}) {
      // 返回 Promise<boolean>; 取消/遮罩/Esc 均结算为 false(不做任何写操作)
      return this._openModal({
        title, body, input: false,
        okText: opts.okText || "确认", cancelText: opts.cancelText || "取消", danger: !!opts.danger,
      });
    },
    /* 带"额外选项勾选框"的确认框: 返回 Promise<{checked:boolean}|null>(取消 = null)
     *
     * 与 confirmDialog 的**布尔契约分开**, 互不影响 —— 删除类操作需要"一个确认动作 + 一个可选附加项"
     * (是否连带磁盘文件), 拆成两个菜单项(保留文件/含文件)反而需要用户先判断自己点的是哪个。
     */
    confirmWithOption(title, body, opts = {}) {
      return this._openModal({
        title, body, checkbox: opts.checkbox || "", checked: !!opts.checked,
        okText: opts.okText || "确认", cancelText: opts.cancelText || "取消", danger: !!opts.danger,
      });
    },
    promptDialog(title, value, opts = {}) {
      // 返回 Promise<string|null>; 取消返回 null(与原生 prompt 语义一致)
      return this._openModal({
        title, body: opts.body || "", input: true, value: value || "", placeholder: opts.placeholder || "",
        okText: opts.okText || "确定", cancelText: opts.cancelText || "取消", danger: !!opts.danger,
      });
    },
    _openModal(cfg) {
      if (this.modal.visible) this.resolveModal(false);  // 单例: 上一个悬空 Promise 先结算为取消
      return new Promise((resolve) => {
        this._modalResolve = resolve;
        this.modal = { ...this._modalInit(), ...cfg, visible: true };
        this.$nextTick(() => {
          if (this.modal.input && this.$refs.modalInput) {
            this.$refs.modalInput.focus();
            this.$refs.modalInput.select();
          }
        });
      });
    },
    resolveModal(ok) {
      if (!this.modal.visible) return;
      const { input, value, checkbox, checked } = this.modal;
      const resolve = this._modalResolve;
      this._modalResolve = null;
      this.modal = this._modalInit();
      if (!resolve) return;
      if (ok) resolve(input ? value : checkbox ? { checked } : true);
      else resolve(input || checkbox ? null : false);
    },
    /* ------------------------------------------- 筛选(状态/路径/标签/分类/站点)与搜索清除 */
    /* 成员值 -> 选项(带计数, 按出现组数降序): 标签/分类/站点三个筛选器共用
     * 计数口径 = "包含该值的组数"(与保存路径筛选一致), 而非成员总数 —— 筛选针对的是组。
     */
    _memberValueOptions(pick) {
      const counts = new Map();
      for (const g of this.groups) {
        const seen = new Set();
        for (const m of g.members) {
          for (const v of pick(m)) {
            if (!seen.has(v)) {
              seen.add(v);
              counts.set(v, (counts.get(v) || 0) + 1);
            }
          }
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
    toggleColMenu(ev) {
      this.colMenuOpen = !this.colMenuOpen;
      if (this.colMenuOpen) this.colFlip = this._menuOverflowsRight(ev && ev.currentTarget, 300);
    },
    /* 锚点左缘 + 弹层宽度是否超出视口(留 8px 边距); ev.currentTarget 在同步代码内有效 */
    _menuOverflowsRight(anchor, menuW) {
      if (!anchor || !anchor.getBoundingClientRect) return false;
      return anchor.getBoundingClientRect().left + menuW > window.innerWidth - 8;
    },
    clearFilters() {
      this.kindFilter = "";
      this.pathFilter = [];
      this.tagFilter = [];
      this.categoryFilter = [];
      this.siteFilter = [];
      this.filterMenu = "";
      this.expandedKey = null;
    },
    clearSearch() {
      if (this.searchTimer) clearTimeout(this.searchTimer);
      this.searchTimer = null;
      this.searchQuery = "";
      this.resetSearch();
    },
    /* 右键菜单定位: 视口边界吸附(菜单尺寸取常量估算, 避免先渲染再测量造成的抖动) */
    _menuPos(event, w = 214, h = 222) {
      const x = Math.min(event.clientX, Math.max(8, window.innerWidth - w - 8));
      const y = Math.min(event.clientY, Math.max(8, window.innerHeight - h - 8));
      return { x: Math.max(8, x), y: Math.max(8, y) };
    },
    async bootstrap(candidate) {
      if (this.authPending) return;  // 防重复提交(验证中按钮已禁用, 双保险)
      this.authPending = true;
      this.authError = "";
      this.authErrorKind = "";
      this.pendingToken = candidate;
      this.lastRid = null;  // 重新鉴权/换密钥: 强制全量取一次分组视图
      this.idlePolls = 0;
      try {
        // 用候选密钥直接验证: 成功前 this.token 不提交、authRequired 不解除, 主界面 DOM 绝不渲染
        const state = await this._request("/api/state", {}, candidate);
        this.status = state.status;
        this.groups = state.groups || [];
        if (typeof state.rid === "number") this.lastRid = state.rid;
        this.serviceDown = false;
        this.token = candidate;  // 验证通过才提交为当前身份
        this.authRequired = false;  // 唯一放行点
        localStorage.setItem("autoqb_token", candidate);
        this.pendingToken = "";
        this.tokenInput = "";
        this.startPolling();
      } catch (e) {
        if (!e.auth) {
          // 服务不可达 ≠ 密钥错误: 不否定候选密钥(本地存储亦保留), 给出重试入口, 防误清凭证
          this.authError = "服务不可用, 请确认 auto-qb 程序正在运行";
          this.authErrorKind = "unavailable";
        }
        // e.auth(401/无凭证): _request 已走 _logout() 完成遮罩/数据/文案收口
      } finally {
        this.authPending = false;
      }
    },
    saveToken() {
      const candidate = this.tokenInput.trim();
      if (!candidate || this.authPending) return;  // 空提交/验证中拦截: 不触发任何请求与界面切换
      this.bootstrap(candidate);
    },
    retryAuth() {
      // 仅"服务不可达"分支保留候选密钥; 401 已清空, 重试按钮不渲染
      if (this.pendingToken && !this.authPending) this.bootstrap(this.pendingToken);
    },
    startPolling() {
      this.stopPolling();
      this.refresh();
    },
    stopPolling() {
      if (this.pollTimer) clearTimeout(this.pollTimer);
      this.pollTimer = null;
    },
    scheduleNext() {
      // 用 setTimeout 链式续排(而非 setInterval): 保证上一轮请求结束后再计时, 不堆叠请求
      this.stopPolling();
      if (document.hidden || !this.token) return;
      this.pollTimer = setTimeout(() => this.refresh(), this.currentPollMs());
    },
    currentPollMs() {
      // 失败退避: 连续失败翻倍至上限 15s(减少服务不可达时的空转)
      if (this.pollFails) return Math.min(15000, this.pollSec * 1000 * 2 ** this.pollFails);
      // 无变化退避: 连续多轮无更新逐步放慢(2s→5s→10s); 一旦有更新立即回到 2s
      if (this.idlePolls >= 6) return 10000;
      if (this.idlePolls >= 2) return 5000;
      return this.pollSec * 1000;
    },
    async refresh() {
      try {
        // rid 增量: 带上已持有的视图版本, 服务端版本未变时不回传 groups(响应体趋近于零)
        const query = this.lastRid === null ? "" : `?rid=${this.lastRid}`;
        const state = await this.api("/api/state" + query);
        this.status = state.status;
        if (state.updated !== false) {
          // 视图有变化: 整表替换并记录新版本; 无变化时保留原数组, 不触发重渲染
          this.groups = state.groups || [];
          if (typeof state.rid === "number") this.lastRid = state.rid;
          this.idlePolls = 0;
        } else {
          this.idlePolls += 1;
        }
        this.serviceDown = false;
        this.pollFails = 0;
      } catch (e) {
        // 服务不可达(程序退出/网络失败): 置 serviceDown 显示横幅; 轮询继续, 服务恢复后自动消失。
        // 401(密钥无效): 停止轮询并回到密钥输入界面(防无谓空转)。
        if (e.auth) {
          this.stopPolling();
          return;
        }
        this.serviceDown = true;
        this.pollFails = Math.min(4, this.pollFails + 1);
      }
      this.scheduleNext();
    },
    onSearchInput(event) {
      // 输入防抖: 停止输入 400ms 后触发搜索; 清空则立即恢复辅种管理视图(不等防抖)
      if (this.searchTimer) clearTimeout(this.searchTimer);
      if (!(event.target.value || "").trim()) {
        this.resetSearch();
        return;
      }
      this.searchTimer = setTimeout(() => this.doSearch(), 400);
    },
    resetSearch() {
      // 清空搜索结果并复位展开态: 搜索结果与普通分组结构不同(含虚拟行), 展开状态不跨视图残留
      this.searchHits = new Set();
      this.searchUncovered = [];
      this.searchBuilding = false;
      this.searchError = "";
      this.expandedKey = null;
    },
    async doSearch() {
      const q = (this.searchQuery || "").trim();
      if (!q) {
        this.resetSearch();
        return;
      }
      try {
        const data = await this.api(`/api/search?q=${encodeURIComponent(q)}`);
        const results = data.results || [];
        this.searchHits = new Set(results.map((r) => r.hash));
        // 实际归组的种子由分组筛选展示; 未归组的命中(分组未启用/文件列表不可读)单独兜底
        const grouped = new Set();
        for (const g of this.groups) for (const m of g.members) grouped.add(m.hash);
        this.searchUncovered = results.filter((r) => !grouped.has(r.hash));
        this.searchBuilding = !!data.building;
        this.searchError = "";
        if (this.searchBuilding) {
          // 文件索引构建中(增量限流可能需多轮): 1s 后自动重查, 直至 building 消除
          if (this.searchTimer) clearTimeout(this.searchTimer);
          this.searchTimer = setTimeout(() => this.doSearch(), 1000);
        }
      } catch (e) {
        // 不再静默(否则与"无匹配结果"无法区分): 401 由 api() 回登录框, 其余在搜索框旁提示
        if (!e.auth) {
          const msg = e.message || "搜索失败";
          this.resetSearch();
          this.searchError = msg;
        }
      }
    },
    fmtSpeed(v) {
      if (!v) return "0 B/s";
      for (const [unit, div] of [["GiB/s", 1073741824], ["MiB/s", 1048576], ["KiB/s", 1024]]) {
        if (v >= div) return (v / div).toFixed(2) + " " + unit;
      }
      return v + " B/s";
    },
    fmtSize(v) {
      if (v === null || v === undefined) return "-";
      if (!v) return "0 B";
      for (const [unit, div] of [["PiB", 2 ** 50], ["TiB", 2 ** 40], ["GiB", 2 ** 30], ["MiB", 2 ** 20], ["KiB", 2 ** 10]]) {
        if (v >= div) return (v / div).toFixed(2) + " " + unit;
      }
      return v + " B";
    },
    /* 0 值不显示 "0 B/s"/"0 B"(满屏零值噪声): 只留极淡占位符, 列对齐不受影响 */
    fmtSpeedOrDash(v) {
      return v ? this.fmtSpeed(v) : "—";
    },
    fmtSizeOrDash(v) {
      return v ? this.fmtSize(v) : "—";
    },
    fmtDuration(sec) {
      // 做种时长: 后端已按分钟取整(torrents._VIEW_QUANTUM), 故不展示秒位
      sec = Math.floor(sec || 0);
      if (sec < 3600) return `${Math.floor(sec / 60)}分钟`;
      if (sec < 86400) return `${Math.floor(sec / 3600)}时${String(Math.floor((sec % 3600) / 60)).padStart(2, "0")}分`;
      return `${Math.floor(sec / 86400)}天${String(Math.floor((sec % 86400) / 3600)).padStart(2, "0")}时`;
    },
    /* ------------------------------------------- 组级"共同值"计算(组级标签/分类列)
     *
     * 后端只透出成员原始值, 共同值(交集/一致值)在**前端**计算: 这类派生展示数据不参与
     * 后端视图重建判定, 且 computed 缓存后可复用, 无需让后端每轮做集合运算。
     */
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
    /* 站点专属配色索引: 站点名确定性哈希 -> 0..7(对应样式 .sc-0..7), 同一站点永远同色。
     * 2026-09-14 第五轮: 改用 djb2(((h<<5)+h+c)|0, 起始 5381)。
     * 原算法 ((h<<5)-h+c)|0 起始 0 在 BTSchool 与 MuXueGe 上碰撞(都落 2 -> 黄);
     * djb2 已验证两者分离(BTSchool→3, MuXueGe→5), 不再加绝对值兜底(直接 &0x7 桶) */
    siteHue(site) {
      const s = String(site || "");
      let h = 5381;
      for (let i = 0; i < s.length; i++) h = (((h << 5) + h) + s.charCodeAt(i)) | 0;
      return (h & 0x7FFFFFFF) % 8;
    },
    _commonCategory(members) {
      const vals = members.map((m) => m.category || "");
      if (!vals.length) return { value: "", diff: false };
      const diff = vals.some((v) => v !== vals[0]);
      return { value: diff ? "" : vals[0], diff };
    },
    kindText(kind) {
      return { seeding: "做种", downloading: "下载", checking: "校验中", paused: "已暂停", error: "错误", other: "其他" }[kind] || kind;
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
    /* ---------------- HR 展示辅助(布尔/阈值均由后端算好, 前端只做比较与着色) ----------------
     * hr_triggered / hr_satisfied: 是否触发 HR / 是否已达成要求
     * hr_req_time: 要求做种时长(秒); hr_req_ratio: 要求分享率(0 = 不要求)
     * 绝不在前端重算模板或阈值(自定义标签格式与要求值会立即失效), 见 ai/08-pitfalls。
     */
    hrTimeReached(m) {
      return m.hr_req_time > 0 && m.seeding_time >= m.hr_req_time;
    },
    hrRatioReached(m) {
      return m.hr_req_ratio > 0 && (m.ratio || 0) >= m.hr_req_ratio;
    },
    /* 对照列配色: **按列各自的要求**判定 —— 未配要求的列(如只要求时长不要求分享率)必须
     * 保持中性色, 否则会给一个"本来就没要求的数值"染上警示色, 反而是误读。
     */
    hrTimeClass(m) {
      if (!m.hr_triggered || !(m.hr_req_time > 0)) return "";
      return this.hrTimeReached(m) ? "reached" : "pending";
    },
    hrRatioClass(m) {
      if (!m.hr_triggered || !(m.hr_req_ratio > 0)) return "";
      return this.hrRatioReached(m) ? "reached" : "pending";
    },
    hrGroupClass(g) {
      if (!g.hr_triggered) return "";
      return g.hr_pending ? "pending" : "done";
    },
    hrGroupTitle(g) {
      if (!g.hr_triggered) return "该组没有成员触发 HR 条件";
      if (!g.hr_pending) return `已触发 HR 的 ${g.hr_triggered} 个成员均已满足做种时长/分享率要求`;
      return `已触发 HR ${g.hr_triggered} 个, 其中 ${g.hr_pending} 个尚未满足做种时长/分享率要求`;
    },
    /* 限速显示: 后端单位 KiB/s(0 = 不限速, null = 该方向不管理) */
    fmtLimit(kib) {
      if (kib === null || kib === undefined) return "—";
      if (!kib) return "不限速";
      return this.fmtSpeed(kib * 1024);
    },
    setSort(key) {
      // 三态(想法.md): 首次点击按该列降序 -> 再点升序 -> 第三次恢复默认排序(最近添加时间降序)
      if (this.sortKey !== key) {
        this.sortKey = key;
        this.sortDir = -1;
        return;
      }
      if (this.sortDir === -1) {
        this.sortDir = 1;
        return;
      }
      this.sortKey = DEFAULT_SORT.key;
      this.sortDir = DEFAULT_SORT.dir;
    },
    sortArrow(key) {
      if (this.sortKey !== key) return "";
      return this.sortDir === 1 ? "▲" : "▼";
    },
    /* 分组表横向滚动时同步表头位移(表头已脱离 .group-table 容器做纵向 sticky,
       横向滚动靠 JS 桥接避免列头与列体错位)。用 transform 而非 scrollLeft,
       避免反向触发自身 scroll 事件形成回环; 不带 transition 跟手不滞后 */
    syncGroupHeadScroll(ev) {
      const head = this.$refs.groupHead;
      if (!head) return;
      head.style.transform = `translateX(${-ev.target.scrollLeft}px)`;
    },
    toggleExpand(key, event) {
      // 仅左键触发展开: 右键菜单不应连带展开明细(旧实现在 openMenu 里主动展开, 已移除)
      if (event && event.button !== 0) return;
      this.expandedKey = this.expandedKey === key ? null : key;
      this.menu.visible = false;
    },
    openMenu(event, group) {
      event.preventDefault();
      if (group.virtual) {
        // 虚拟行(未归组命中种子): 无真实组 key(组级路由会解析失败), 退化为该种子的单种子菜单
        this.openMemberMenu(event, group.members[0]);
        return;
      }
      // 仅弹菜单, **不展开明细**(用户需要看明细时自己左键点行)
      this.menu = { visible: true, ...this._menuPos(event), key: group.key, hash: null };
    },
    openMemberMenu(event, member) {
      event.preventDefault();
      event.stopPropagation();
      this.menu = { visible: true, ...this._menuPos(event), key: null, hash: member.hash };
    },
    // 命令 => 中文动作名(用于投递成功/失败的提示文案)
    _actionText(action) {
      return { pause: "暂停", resume: "开始", reannounce: "强制汇报", delete: "删除" }[action] || action;
    },
    async act(action) {
      this.menu.visible = false;
      if (!this.menu.key) return;
      try {
        await this.api(`/api/groups/${this.menu.key}/${action}`, { method: "POST" });
        this.toast(`已投递: ${this._actionText(action)}整组`, "ok", 2500);
      } catch (e) {
        if (!e.auth) this.toast("命令发送失败: " + e.message, "error");
      }
    },
    /* 删除整组: **单一菜单项** + 确认框里勾选"是否连带磁盘文件"(默认不删文件)
     * 而非"保留文件/含文件"两个菜单项 —— 后者需要用户先判断自己点的是哪个, 风险更高。
     */
    async delGroup() {
      this.menu.visible = false;
      const key = this.menu.key;
      if (!key) return;
      const res = await this.confirmWithOption(
        "删除整组",
        "将删除该组全部种子(保留磁盘文件)。如需连同磁盘文件一起删除, 请勾选下方选项。",
        { okText: "删除", danger: true, checkbox: "同时删除磁盘文件(不可恢复)", checked: false }
      );
      if (!res) return;
      try {
        await this.api(`/api/groups/${key}/delete`, {
          method: "POST",
          body: JSON.stringify({ delete_files: res.checked }),
        });
        this.toast(`已投递: 删除整组${res.checked ? "(含文件)" : ""}`, "ok", 2500);
      } catch (e) {
        if (!e.auth) this.toast("删除命令发送失败: " + e.message, "error");
      }
    },
    async actTorrent(action) {
      this.menu.visible = false;
      if (!this.menu.hash) return;
      try {
        await this.api(`/api/torrents/${this.menu.hash}/${action}`, { method: "POST" });
        this.toast(`已投递: ${this._actionText(action)}该种子`, "ok", 2500);
      } catch (e) {
        if (!e.auth) this.toast("命令发送失败: " + e.message, "error");
      }
    },
    /* 删除单个种子: 同 delGroup, 一个菜单项 + 确认框内勾选是否连带磁盘文件 */
    async delTorrent() {
      this.menu.visible = false;
      const hash = this.menu.hash;
      if (!hash) return;
      const res = await this.confirmWithOption(
        "删除该种子",
        "将删除该种子(保留磁盘文件)。如需连同磁盘文件一起删除, 请勾选下方选项。",
        { okText: "删除", danger: true, checkbox: "同时删除磁盘文件(不可恢复)", checked: false }
      );
      if (!res) return;
      try {
        await this.api(`/api/torrents/${hash}/delete`, {
          method: "POST",
          body: JSON.stringify({ delete_files: res.checked }),
        });
        this.toast(`已投递: 删除该种子${res.checked ? "(含文件)" : ""}`, "ok", 2500);
      } catch (e) {
        if (!e.auth) this.toast("删除命令发送失败: " + e.message, "error");
      }
    },
    gridStyle(page) {
      // 列模板由 computed 缓存(见 groupGrid/detailGrid): 行渲染只取同一引用, 不每行拼字符串
      return page === "group" ? this.groupGrid : this.detailGrid;
    },

    /* ------------------------------------------------ 列状态(宽/隐/自适应) */

    _visibleCols(page) {
      const hidden = this.colHidden[page] || [];
      return TABLE_COLUMNS[page].filter((c) => !hidden.includes(c.key));
    },
    /* 列模板: 有 px 覆盖用覆盖值, 否则用默认模板(仅首次渲染会出现这种混合态) */
    _gridTemplate(page) {
      const w = this.colWidths[page] || {};
      return this._visibleCols(page).map((c) => w[c.key] || c.tpl).join(" ");
    },
    /* 从列头行(真正的 grid 容器)读取**当前渲染**的列宽 px; 列数不符(渲染未完成)返回 null */
    _renderedWidths(headEl, page) {
      const rendered = (getComputedStyle(headEl).gridTemplateColumns || "")
        .split(" ")
        .map((v) => parseFloat(v))
        .filter((v) => !isNaN(v) && v > 0);
      const vis = this._visibleCols(page);
      if (rendered.length !== vis.length) return null;
      const out = {};
      vis.forEach((c, i) => {
        out[c.key] = Math.round(rendered[i]) + "px";
      });
      return out;
    },
    _headEl(page) {
      const ref = this.$refs[page === "group" ? "groupHead" : "detailHead"];
      return Array.isArray(ref) ? ref[0] : ref || null;
    },
    /* 顶栏(+状态分布条)的实测高度写入 :root 的 --head-h: 辅种页左栏 .rail 的吸顶偏移与最大可用
     * 高度都依赖它。**不写死数值** —— 高度会随媒体查询、状态条是否渲染、窄屏折行而变化;
     * 值未变时直接返回, 避免每帧都写一次 CSS 变量(updated 会频繁触发)。
     */
    _syncHeadHeight() {
      const el = document.querySelector(".sticky-head");
      const h = el ? Math.round(el.getBoundingClientRect().height) : 0;
      if (h === this._headH) return;
      this._headH = h;
      document.documentElement.style.setProperty("--head-h", h + "px");
    },
    /* 把默认模板"实体化"为 px:
     * - 未手动调过 -> 每次窗口变化后重新实体化(保留"填满容器 + 自适应"的观感)
     * - 手动调过   -> 跳过(冻结, 拖一列不再动其它列)
     */
    materializeColumns() {
      for (const page of ["group", "detail"]) {
        if (this.colManual[page]) continue;
        const headEl = this._headEl(page);
        if (!headEl) continue;
        const widths = this._renderedWidths(headEl, page);
        if (widths) this.colWidths = { ...this.colWidths, [page]: widths };
      }
    },
    saveColState() {
      localStorage.setItem(
        COLS_STORE_KEY,
        JSON.stringify({ widths: this.colWidths, hidden: this.colHidden, manual: this.colManual })
      );
    },
    colVisible(page, key) {
      return !(this.colHidden[page] || []).includes(key);
    },
    toggleColumn(page, key) {
      const col = columnDef(page, key);
      if (!col || col.locked) return;  // locked 列不可隐藏(模板中不渲染其勾选框, 这里是双保险)
      const cur = this.colHidden[page] || [];
      const hidden = cur.includes(key) ? cur.filter((k) => k !== key) : [...cur, key];
      this.colHidden = { ...this.colHidden, [page]: hidden };
      // 已手动调过: 新显示的列需要一个 px 宽度才能维持"只改一列"的策略
      if (this.colManual[page] && !hidden.includes(key)) {
        const widths = { ...(this.colWidths[page] || {}) };
        if (!widths[key]) {
          widths[key] = templateMinPx(col.tpl) + "px";
          this.colWidths = { ...this.colWidths, [page]: widths };
        }
      }
      this.saveColState();
      this.$nextTick(() => this.materializeColumns());
    },
    resetAllColumnWidths(page) {
      // 恢复默认列宽: 清空 px 覆盖与手动标记 -> 回到默认弹性模板并重新实体化
      const widths = { ...(this.colWidths[page] || {}) };
      for (const c of TABLE_COLUMNS[page]) delete widths[c.key];
      this.colWidths = { ...this.colWidths, [page]: widths };
      this.colManual = { ...this.colManual, [page]: false };
      this.saveColState();
      this.$nextTick(() => this.materializeColumns());
    },
    fitColumnsToWindow(page) {
      // 适应窗口宽度: 先回到默认弹性模板(它会重新填满容器), 下一帧固化 —— 等价按比例缩放填满
      this.colWidths = { ...this.colWidths, [page]: {} };
      this.colManual = { ...this.colManual, [page]: false };
      this.$nextTick(() => {
        this.materializeColumns();
        this.colManual = { ...this.colManual, [page]: true };
        this.saveColState();
      });
    },

    /* 列宽拖拽: 拖某列**只改该列**
     *
     * 关键在于起始时把**全部可见列**固化为当前渲染 px —— 它们原本可能是 minmax/fr 弹性值,
     * 不固化的话被拖列会把余量从邻居那儿抢走(表现为"调一列, 其它列跟着变")。
     * 按住 Shift 拖拽 = 与相邻列互相挤占(总宽不变), 对应主流表格的 shift-resize。
     *
     * 拖拽抑制误触排序: resizer 与 .h-cell 共父级, mouseup 后浏览器仍派发 click 冒泡到
     * .h-cell 触发 setSort(用户感知为"调列宽顺手把排序变了")。这里累计位移超过阈值时,
     * 在 capture 阶段拦截下一次 click(stopPropagation+preventDefault), 拦完即注销。
     * 未拖动(纯点击 resizer)不拦截, 保持原行为。
     */
    startResize(event, page, key) {
      const headEl = event.target.closest(".group-head") || event.target.closest(".detail-head");
      if (!headEl) return;
      const widths = this._renderedWidths(headEl, page);
      if (!widths) return;
      const vis = this._visibleCols(page);
      const idx = vis.findIndex((c) => c.key === key);
      if (idx < 0) return;
      const startX = event.clientX;
      const startVal = parseFloat(widths[key]);
      const neighbor = event.shiftKey ? vis[idx + 1] : null;
      const startNeighbor = neighbor ? parseFloat(widths[neighbor.key]) : 0;
      let dragged = false;  // 位移超过 RESIZE_DRAG_THRESHOLD 即置真, up 时用于决定是否拦 click
      const move = (e) => {
        if (!dragged && Math.abs(e.clientX - startX) > RESIZE_DRAG_THRESHOLD) dragged = true;
        const w = Math.max(MIN_COL_PX, Math.round(startVal + e.clientX - startX));
        const next = { ...widths, [key]: `${w}px` };
        if (neighbor) {
          next[neighbor.key] = `${Math.max(MIN_COL_PX, Math.round(startNeighbor - (w - startVal)))}px`;
        }
        this.colWidths = { ...this.colWidths, [page]: next };
      };
      const up = () => {
        document.removeEventListener("mousemove", move);
        document.removeEventListener("mouseup", up);
        this.colManual = { ...this.colManual, [page]: true };  // 手动调过 -> 不再随窗口自适应
        this.saveColState();
        if (!dragged) return;  // 未拖动 = 纯点击 resizer, 不拦 click(保持原行为)
        // 拖拽尾处浏览器会冒泡一次 click 到 .h-cell 触发 setSort —— capture 阶段拦掉即停
        const swallow = (ev) => {
          ev.stopPropagation();
          ev.preventDefault();
          document.removeEventListener("click", swallow, true);
        };
        document.addEventListener("click", swallow, true);
      };
      document.addEventListener("mousemove", move);
      document.addEventListener("mouseup", up);
    },
    /* 双击分隔线 = 按内容自适应宽度(表头 + 当前已渲染行), 夹在 [最小宽, MAX_FIT_PX] */
    autoFitColumn(event, page, key) {
      const headEl = event.target.closest(".group-head") || event.target.closest(".detail-head");
      if (!headEl) return;
      const vis = this._visibleCols(page);
      const idx = vis.findIndex((c) => c.key === key);
      if (idx < 0) return;
      const container = headEl.parentElement;
      const rowSel = page === "group" ? ".group-row" : ".member-row";
      let max = headEl.children[idx] ? headEl.children[idx].scrollWidth : MIN_COL_PX;
      for (const row of container.querySelectorAll(rowSel)) {
        const cell = row.children[idx];
        if (cell) max = Math.max(max, cell.scrollWidth);
      }
      const width = Math.min(MAX_FIT_PX, Math.max(MIN_COL_PX, Math.ceil(max) + 18));
      const widths = this._renderedWidths(headEl, page) || {};
      this.colWidths = { ...this.colWidths, [page]: { ...widths, [key]: `${width}px` } };
      this.colManual = { ...this.colManual, [page]: true };
      this.saveColState();
    },
  },
});

// 图形化配置编辑器以全局 mixin 注入(设置页控件/状态/接口全在其中)
app.mixin(window.CONFIG_EDITOR);
app.mixin(window.CONFIG_RULES);
app.component("ce-field", window.CE_FIELD_COMPONENT);
app.mount("#app");
