/* auto-qb WEB UI · qB 口径流量图(uPlot 双系列组件, 三挂点)
 *
 * plan 26-10-03-0946 方案C §07 P5a/P5b。一个「双系列(上行/下行)时间曲线」封装, 三图(全局/单种/
 * 分组)共用: uPlot options 样板(axes/series/scales/cursor)收在 _qbChartBuild 单点, 调用方只给
 * points + 容器; null 桶 = 断线不连线(uPlot spanGaps:false, §5.2 拍板语义)。
 *
 * 约定与 dialogs.js / hr_status.js 同范式: 挂到 window.AQB_QB_TRAFFIC, 由 app.js 末尾
 * app.mixin(window.AQB_QB_TRAFFIC) 注入同一个 Vue 实例 —— 方法体里的 this 仍是那个组件实例。
 * !本文件在 HTML 里必须排在 app.js **之前**; data 字段在 state.js(根选项, 不进 app.mixin,
 *   见 frontend-split 纪律), uPlot vendor 由三主题 tpl-manifest scripts 登记(boot.js 依序放行)。
 *
 * 三挂点(2026-10-04 起全部并入底部详情抽屉, 以 _QB_SCOPES 作用域表为单一描述源): ① global 全局
 * (/api/traffic/qb/global, 状态栏「qB 口径流量图」入口) ② group 分组(/api/traffic/qb/group/{key},
 * 组右键菜单入口; key = 分组视图 g.key, 即 encode_group_key 通道, 前端不自行编码) ③ torrent 单种
 * (/api/traffic/qb/torrent/{hash}, 种子详情抽屉「流量」页签)。全局/分组走 drawer.kind === "traffic"
 * (scope 记挂点), 单种走 drawer.kind === "seed" + drawer.tab === "traffic"; 三者共用同一抽屉壳、
 * 同一拖拽高度(drawerHeightPx)与同一段正文块(drawer.html qbTrafficActive), 故建图落点统一
 * ref="qbChartHost"(同一时刻只渲染一个流量形态)。
 *
 * 低频轮询(§07 表「轮询/取数」列): 打开期间按采样间隔续拉 —— 间隔从最近响应 meta.interval_s
 * 取(raw 段窗(1m-24h)即采样间隔; agg 段窗(3d/7d/30d/6mo/1y/all) meta 是桶宽(3600s/86400s/
 * 标称月长)而非采样间隔, 夹取到配置校验上界 600s), 取不到回退 30s 常量; document.hidden 跳过
 * (对齐 drawer.js _startDrawerPoll 先例); 关闭/切走形态由 _stopDrawerPoll / _qbTeardown 显式
 * clearInterval —— 只挂打开期间, 不后台常驻。
 * meta.stale=true 的响应照常渲染(读竞态兜底位, §08, 前端不特殊处理)。
 *
 * 静默续拉(2026-10-04 修「每隔几秒闪一次」): 续拉对用户不可见 —— 模板 loading 空态只在
 * 无数据时接管正文(drawer.html), 数据落袋走 _qbChartBuild 的 setData 原地快路(同一宿主上
 * 图还活着就不销毁重建; 完整重建仅首图/宿主被拆后/换肤三次)。
 *
 * 容器尺寸自适应(便签 26-10-04-0134 + 2026-10-04 高度跟随): 建图尺寸不是一次取定 —— 建图后对
 * 宿主挂 ResizeObserver, 宽/高任一变化即 u.setSize 重画(高度取自宿主 clientHeight, 随抽屉拖拽
 * 调高实时跟随; 未拖拽时 drawerPanelStyle 给流量形态一个确定高度, 见 drawer.js); 销毁在
 * _qbChartDestroy 断开, 自摘守卫见 _qbChartBuild 内注。
 *
 * 令牌纪律: canvas 内色值(series stroke/grid/axis)无法引用 CSS 变量, 一律在建图时读
 * 三主题令牌(getComputedStyle(:root)); DOM 侧(十字线样式/uPlot 结构样式)由 _qbChartInjectCss
 * 注入 token 化样式(var(--fg-dim)), 换肤自动跟随 —— 禁止硬编码色值。
 * prism 五主题动态换肤派发 autoqb:themechange(theme.js), 图在建时读令牌, 换肤事件触发重建。
 */
/* global uPlot */

/* 轮询间隔边界(ms): 夹取下界 = 配置校验下限 1.5s(§06, A4: 采样间隔下限放宽后同步对齐,
 * 上界 = 配置校验上限 600s (hour 及以上段窗(3d/7d/30d/6mo/1y/all) meta.interval_s 是桶宽
 * 而非采样间隔(3600s/86400s/标称月长), 按它直拉等于一小时不刷新 —— 夹到上界保低频续拉
 * 语义); meta 缺失/非法回退 30s 常量(plan §07「采样间隔」基准值)。 */
const _QB_POLL_MIN_MS = 1500;
const _QB_POLL_MAX_MS = 600000;
const _QB_POLL_FALLBACK_MS = 30000;

/* 三挂点作用域表(模块级单一描述源): 字段名一律指到 state.js 根选项的字段(不进 app.mixin,
 * frontend-split 纪律); url(ctx, window) 组端点串, ctx = 单种 hash / 分组 key(经 this 取);
 * active = 该图此刻是否应显示/可拉(建图守卫 + 轮询 tick 跳过判据同源); stale = 在途响应
 * 回落时是否已过期(不落袋, 对齐 drawer.js _drawerStale 代际纪律)。
 * host 三挂点统一为 qbChartHost: 三形态互斥(同一时刻只渲染一个), 正文块共用(drawer.html)。 */
const _QB_SCOPES = {
  global: {
    host: "qbChartHost",
    window: "qbHistWindow", data: "qbHistData", loading: "qbHistLoading", error: "qbHistError",
    hoverIdx: "qbHistHoverIdx", hoverLeft: "qbHistHoverLeft",
    url: (_ctx, w) => "/api/traffic/qb/global?window=" + w,
    ctx: null,
    active: (t) => t.drawer.open && !t.drawer.collapsed
      && t.drawer.kind === "traffic" && t.drawer.scope === "global",
    stale: (t) => !(t.drawer.open && t.drawer.kind === "traffic" && t.drawer.scope === "global"),
  },
  torrent: {
    host: "qbChartHost",
    window: "qbTorrentWindow", data: "qbTorrentData", loading: "qbTorrentLoading", error: "qbTorrentError",
    hoverIdx: "qbTorrentHoverIdx", hoverLeft: "qbTorrentHoverLeft",
    url: (h, w) => "/api/traffic/qb/torrent/" + h + "?window=" + w,
    ctx: (t) => t.drawer.hash,
    // 抽屉打开 + 种子形态 + 流量页签 + 展开态 + 种子页种子视图(面板 DOM 随 drawerVisible 出入,
    // 不可见即跳过 —— 对齐 _startDrawerPoll 的页面守卫先例; 收起态图不可见, 省请求同停)
    active: (t) => !!(t.drawer.open && t.drawer.kind === "seed" && t.drawer.tab === "traffic"
      && !t.drawer.collapsed && t.page === "groups" && t.viewMode === "torrents"),
    stale: (t, h) => !(t.qbTrafficOn && t.drawer.open && t.drawer.kind === "seed"
      && t.drawer.tab === "traffic" && t.drawer.hash === h),
  },
  group: {
    host: "qbChartHost",
    window: "qbGroupWindow", data: "qbGroupData", loading: "qbGroupLoading", error: "qbGroupError",
    hoverIdx: "qbGroupHoverIdx", hoverLeft: "qbGroupHoverLeft",
    // key = 分组视图 g.key(服务端 encode_group_key 产物, base64url 天然 URL 安全),
    // 与 delete_flow/commands 的 /api/groups/${k} 同款原样内插 —— 前端不自行编码(§07 表③)
    url: (k, w) => "/api/traffic/qb/group/" + k + "?window=" + w,
    ctx: (t) => t.qbGroupKey,
    active: (t) => t.drawer.open && !t.drawer.collapsed
      && t.drawer.kind === "traffic" && t.drawer.scope === "group",
    stale: (t, k) => !(t.qbTrafficOn && t.drawer.open && t.drawer.kind === "traffic"
      && t.drawer.scope === "group" && t.qbGroupKey === k),
  },
};

/* 桶序 -> uPlot 数据(模块级纯函数, 供 node 单测探针, 同 hrsCompareRows 先例)。
 * API 响应 points 是「桶值 | null」定长数组, null 元素没有 t; 栅格按 meta.interval_s 等距
 * 重建(锚 = 首个非 null 点): xs[i] = t0 + (i - k) * interval, 再用非 null 点携带的真值 t
 * 覆写(等距视图恒等; all 视图月行按行间隔 28-31 天非等距, 必须按真值落点)。null 槽 y 置
 * null(uPlot spanGaps:false 断线), x 在两真值点之间线性内插、窗端外侧按 interval 等距外推
 * (等距视图下与栅格公式同值 —— 缺口位置不漂移)。
 * 全 null(后端已归一为 points: [], 防御)或 interval 非法 -> null(调用方回落空态)。 */
function _qbPointsToData(points, interval) {
  const n = points.length;
  let k = -1;
  for (let i = 0; i < n; i++) {
    if (points[i]) { k = i; break; }
  }
  if (k < 0 || !(interval > 0)) return null;
  const t0 = points[k].t;
  const xs = new Array(n);
  const up = new Array(n);
  const dl = new Array(n);
  const known = [];
  for (let i = 0; i < n; i++) {
    const p = points[i];
    if (p) known.push(i);
    up[i] = p ? p.up : null;
    dl[i] = p ? p.dl : null;
  }
  let seg = 0;  // 已消费的真值段游标(known 有序, 单遍推进)
  for (let i = 0; i < n; i++) {
    if (seg < known.length && known[seg] === i) {
      xs[i] = points[i].t;  // 真值覆写
      seg++;
    } else if (seg === 0) {
      xs[i] = t0 - (known[0] - i) * interval;  // 首个真值点前的外推
    } else if (seg >= known.length) {
      xs[i] = points[known[known.length - 1]].t + (i - known[known.length - 1]) * interval;  // 末尾外推
    } else {
      const a = known[seg - 1], b = known[seg];  // 两真值点之间线性内插
      xs[i] = points[a].t + (points[b].t - points[a].t) * (i - a) / (b - a);
    }
  }
  return { xs, up, dl, anchor: { k, t0, interval, xs } };
}

/* 孤点索引(两侧皆 null 的非 null 桶; uPlot points.filter 约定 = 返回要画点标的索引数组)。
 * §5.2 渲染完备性: spanGaps:false 下孤点是零长线段, 纯断线语义里会整点不可见(30d 单种
 * 稀疏活跃小时实测整幅空白)—— 仅对孤点补一枚小点标, 不跨 null 连线(不引入「最大跨越」)。 */
function _qbIsolatedIdxs(u, sIdx) {
  const v = u.data[sIdx];
  const out = [];
  for (let i = 0; i < v.length; i++) {
    if (v[i] != null && (i === 0 || v[i - 1] == null) && (i === v.length - 1 || v[i + 1] == null)) out.push(i);
  }
  return out;
}

window.AQB_QB_TRAFFIC = {
  computed: {
    /* 功能总门(P5 验收, fail-closed 单点): flags.qb_traffic_enabled(/api/webui/flags 下发,
     * fail-closed 默认 false)。抽屉「流量」页签按钮 / 组右键「qB 口径流量图」菜单项 /
     * 状态栏入口全部 v-if 在它上; 各 _qbLoad 里再兜一道(关闭后无任何请求路径)。 */
    qbTrafficOn() {
      return !!(this.flags && this.flags.qb_traffic_enabled);
    },
    /* 全局入口门(P5a): qbTrafficOn 且今日流量面板在(statusbar 挂点本体, plan §07 表①)。 */
    qbHistEntryOn() {
      return !!(this.flags && this.flags.qb_traffic_enabled && this.todayTraffic);
    },
    /* 当前流量形态的作用域("" = 非流量形态) —— 三挂点正文块(drawer.html qbTrafficActive)与
     * 抽屉流量形态高度判据(drawer.js drawerPanelStyle)的单一派生点。 */
    qbCurScope() {
      if (!this.drawer.open) return "";
      if (this.drawer.kind === "traffic") return this.drawer.scope || "";
      if (this.drawer.kind === "seed" && this.drawer.tab === "traffic" && this.qbTrafficOn) return "torrent";
      return "";
    },
    qbTrafficActive() {
      return !!this.qbCurScope;
    },
    /* 流量形态头部标题(kind === "traffic" 时用; 单种走种子详情头部, 不消费本值) */
    qbTrafficTitle() {
      const s = this.qbCurScope;
      if (s === "global") return "qB 口径流量图";
      if (s === "group") return "分组流量图 · " + (this.qbGroupName || "未命名分组");
      if (s === "torrent") return "种子流量图 · " + this.drawerTitle();
      return "";
    },
    /* 当前作用域取值族(三挂点共用同一段正文块, 模板零分支) */
    qbCurData() {
      const s = this.qbCurScope;
      return s ? this[_QB_SCOPES[s].data] : null;
    },
    qbCurPoints() {
      const d = this.qbCurData;
      return (d && d.points) || [];
    },
    qbCurLoading() {
      const s = this.qbCurScope;
      return s ? !!this[_QB_SCOPES[s].loading] : false;
    },
    qbCurError() {
      const s = this.qbCurScope;
      return s ? this[_QB_SCOPES[s].error] : "";
    },
    qbCurWindow() {
      const s = this.qbCurScope;
      return s ? this[_QB_SCOPES[s].window] : "24h";
    },
    /* 悬停取值(对齐 dialogs.js histHover 十字先例): 时刻 + 上/下行速率(fmtSpeed 同源);
     * 断线桶(null)不出速率, 出「无采样」文案(plan 26-10-04-0721 §05); 0 桶状态行在
     * drawer.html 模板侧(up+dl==0)。left/flip 由十字线 px 折算。 */
    qbCurHover() {
      const s = this.qbCurScope;
      return s ? this._qbHoverOf(s) : null;
    },
    /* 窗口内累计(totals 非空桶求和; 断线/重置桶本就 null 不计 —— §5.1 差分语义) */
    qbCurSummary() {
      const s = this.qbCurScope;
      return s ? this._qbSummaryOf(s) : null;
    },
    /* 空态/汇总口径文案(按作用域微调; 其余文案三挂点一致) */
    qbCurEmptyText() {
      const s = this.qbCurScope;
      if (s === "torrent") return "暂无该种子的 qB 口径流量数据(从未有传输记录)";
      if (s === "group") return "暂无该分组的 qB 口径流量数据(成员活跃传输期间才有采样)";
      return "暂无 qB 口径流量数据(程序运行期间无采样)";
    },
    qbCurSummaryHint() {
      const s = this.qbCurScope;
      const base = "累计为窗口内增量(断线期不计)";
      return s === "group" ? base + " · 组口径 = 当前成员集聚合" : base;
    },
  },
  methods: {
    /* ---------------- 流量形态开关(三挂点并入抽屉; 打开 = 把抽屉切到流量形态) ----------------
     * 全局/分组: openDrawerTraffic(scope, key) 整体重置抽屉状态并拉数 + 起低频轮询;
     * 单种: 走 drawer.js openTorrentDrawer + drawerTab('traffic')(页签本体, 不在本模块)。
     * 关闭统一走 drawer.js closeDrawer()(Esc/关闭钮/切页三路同口), 收轮询与图见 _qbTeardown。 */
    async openQbHistory() {
      return this.openDrawerTraffic("global", "");
    },
    /* 分组入口(S5b, §07 表③): 入口 = 组右键菜单「qB 口径流量图」(ctx-menus.html, v-if=qbTrafficOn)。
     * key 直用分组视图 g.key(encode_group_key 通道); 组名经 _findGroup 取(decoratedGroups 同 key)。 */
    async openQbGroup(key) {
      if (!this.qbTrafficOn || !key) return;  // fail-closed 双保险(菜单项 v-if 之外的加载路径兜底)
      return this.openDrawerTraffic("group", key);
    },
    /* 打开流量形态抽屉(全局/分组共用; 单种走 openTorrentDrawer + 流量页签):
     * 与 drawer.js openTorrentDrawer 同口径 —— 先收上一次的轮询/跟随/图, 再整体重置抽屉状态为
     * 流量形态(kind/scope), 持久化开合态, 最后拉数 + 起低频轮询。 */
    async openDrawerTraffic(scope, key) {
      if (!this.qbTrafficOn || !_QB_SCOPES[scope]) return;  // fail-closed 兜底
      if (scope === "group") {
        if (!key) return;
        const g = this._findGroup(key);
        this.menu.visible = false;  // 右键菜单入口先收菜单(与 openMetaDialog 同口径)
        this.qbGroupKey = key;
        this.qbGroupName = (g && g.name) || "";
      }
      this._stopDrawerPoll();   // 种子详情页签轮询(trackers/peers/torrent 流量)一并收
      this._stopDrawerFollow();
      this._drawerSwitchEnd();  // 形态整体重建 -> 无"旧内容可保留"
      this._qbTeardown();       // 三挂点轮询与图全收(形态切换不残留旧图)
      this.drawer = {
        open: true, collapsed: false, hash: "", tab: "general", loading: false, error: "",
        detail: null, trackers: [], files: [], peers: { peers: [] },
        trackersLoading: false, filesLoading: false, peersLoading: false, switching: false,
        kind: "traffic", scope,
      };
      this.persistDrawerOpen();  // W3 开合态记录(D1: 只写不回读)
      this._qbLoad(scope);
      this._qbPollStart(scope);
    },
    /* 窗口切换(1m-30d 十档): 换窗即重拉重画; 打开中的轮询定时器由 _qbPollResync 按新窗重排 */
    qbSetWindow(w) {
      const s = this.qbCurScope;
      return s ? this._qbSetWindow(s, w) : undefined;
    },
    /* 兼容别名(P5a 公开名; 现归一到 _qbLoad 单点) */
    loadQbHistory() {
      return this._qbLoad("global");
    },
    async _qbSetWindow(scope, w) {
      const def = _QB_SCOPES[scope];
      if (this[def.window] === w) return;
      this[def.window] = w;
      return this._qbLoad(scope);
    },
    /* 三挂点统一收尾(关抽屉 / 形态切换 / 登出): 停三挂点轮询 + 销毁三挂点图, 单点防漏 */
    _qbTeardown() {
      for (const s of Object.keys(_QB_SCOPES)) {
        this._qbPollStop(s);
        this._qbChartDestroy(s);
      }
    },
    /* ---------------- 取数单点(三挂点同形: 开门 -> 拉取 -> 竞态判 -> 落袋/回落) ---------------- */
    async _qbLoad(scope) {
      const def = _QB_SCOPES[scope];
      if (!this.qbTrafficOn) return;  // P5 验收: enabled=false 不发请求(入口 v-if 已门, 这里兜底)
      const ctx = def.ctx ? def.ctx(this) : "";
      this[def.loading] = true;
      this[def.error] = "";
      let stale = true;  // 保守初值: 只有确认未过期才落袋/清 loading(在途竞态纪律, 同 _drawerStale)
      try {
        const data = await this.api(def.url(ctx, this[def.window]));
        stale = def.stale(this, ctx);
        if (!stale) this[def.data] = data;
      } catch (e) {
        stale = def.stale(this, ctx);
        if (!stale) {
          if (!e.auth) this[def.error] = e.message || "加载失败";
          this[def.data] = null;
        }
      } finally {
        if (!stale) this[def.loading] = false;
      }
      if (stale) return;
      // FX-29 软切换落定登记(修「流量页签单击换行遮罩挂死」): 换目标软切换的待到集合含
      // "traffic"(_drawerWaitSources), 流量数据到手(成功/失败都算, 见 _drawerDone)必须登记,
      // 否则集合永不清空 -> drawer.switching 遮罩「正在加载…」挂死盖住图(双击走
      // openTorrentDrawer 整体重置不经待到集合, 故只有单击跟随这条软切换路径踩中)。
      // seq 传 0 只走 hash 戳守卫: 落袋前 def.stale 已确认 drawer.hash === ctx, 同源一致。
      if (scope === "torrent") this._drawerDone("traffic", ctx, 0);
      // 等 v-if 分支进 DOM 再建图(uPlot 要量容器宽); 轮询间隔随新 meta 重排(换窗/间隔变更)
      this.$nextTick(() => this._qbChartBuild(scope));
      this._qbPollResync(scope);
    },
    /* 悬停桶的时刻(null 桶也能定位: 建图时的锚携带整列真值 xs(月行按行间隔非等距);
     * 旧锚形状无 xs 时回退等距公式推算) */
    _qbBucketTs(scope, i) {
      const a = this._qbAnchors && this._qbAnchors[scope];
      if (!a) {
        const d = this[_QB_SCOPES[scope].data];
        const p = d && d.points ? d.points[i] : null;
        return p ? p.t : 0;
      }
      if (a.xs) return a.xs[i];
      return a.t0 + (i - a.k) * a.interval;
    },
    _qbHoverOf(scope) {
      const def = _QB_SCOPES[scope];
      const d = this[def.data];
      const i = this[def.hoverIdx];
      if (!d || !d.points || i < 0 || i >= d.points.length) return null;
      const p = d.points[i];
      const tip = this.fmtTime(this._qbBucketTs(scope, i));
      const W = (this._qbChartWs && this._qbChartWs[scope]) || 0;
      const flip = W > 0 && this[def.hoverLeft] > W * 0.62;
      if (!p) return { tip, gap: true, left: this[def.hoverLeft], flip };
      return { tip, up: p.up, dl: p.dl, left: this[def.hoverLeft], flip };
    },
    _qbSummaryOf(scope) {
      const def = _QB_SCOPES[scope];
      const d = this[def.data];
      if (!d) return null;
      const sum = (key) => (d.totals || []).reduce((a, p) => a + ((p && p[key]) || 0), 0);
      const n = (d.points && d.points.length) || 0;
      return { buckets: n, up: sum("up"), down: sum("dl") };
    },
    /* ---------------- 低频轮询(§07; 打开期间挂, 关闭/切走即清) ---------------- */
    _qbPollMs(scope) {
      const def = _QB_SCOPES[scope];
      const d = this[def.data];
      const s = Number(d && d.meta && d.meta.interval_s);
      if (!(s > 0)) return _QB_POLL_FALLBACK_MS;
      return Math.min(_QB_POLL_MAX_MS, Math.max(_QB_POLL_MIN_MS, s * 1000));
    },
    _qbPollStart(scope) {
      this._qbPollStop(scope);
      if (!this._qbPollTimers) this._qbPollTimers = {};
      if (!this._qbPollPeriods) this._qbPollPeriods = {};
      const ms = this._qbPollMs(scope);
      this._qbPollPeriods[scope] = ms;
      // 页面隐藏/图不活跃/上一拍未到齐: 跳过不拆表(回页/恢复后下一拍自动续, 对齐 drawer.js
      // _startDrawerPoll 先例); 在途请求未落袋前不叠加(loading 在 _qbLoad finally 归位)
      this._qbPollTimers[scope] = setInterval(() => {
        const def = _QB_SCOPES[scope];
        if (!def.active(this) || document.hidden || this[def.loading]) return;
        this._qbLoad(scope);
      }, ms);
    },
    _qbPollStop(scope) {
      if (!this._qbPollTimers) return;
      const t = this._qbPollTimers[scope];
      if (t) {
        clearInterval(t);
        this._qbPollTimers[scope] = null;
      }
    },
    /* meta.interval_s 变化(换窗跨段: raw 段窗 <-> hour 段窗)时按新间隔重排; 定时器本就停着则不动 */
    _qbPollResync(scope) {
      if (!this._qbPollTimers || !this._qbPollTimers[scope]) return;
      if (this._qbPollMs(scope) !== this._qbPollPeriods[scope]) this._qbPollStart(scope);
    },
    /* ---------------- uPlot 封装单点(options 样板一次配齐, §07) ---------------- */
    _qbChartTokens() {
      const cs = getComputedStyle(document.documentElement);
      const pick = (...names) => {
        for (const nm of names) {
          const v = (cs.getPropertyValue(nm) || "").trim();
          if (v) return v;
        }
        return "";
      };
      // 语义: 上/下行与今日流量卡同源(--today-up/down); 兜底仍走令牌链, 不硬编码色值
      return {
        up: pick("--today-up", "--indigo", "--fg"),
        down: pick("--today-down", "--teal", "--fg"),
        grid: pick("--hairline", "--border"),
        axis: pick("--fg-dim", "--fg-muted"),
      };
    },
    _qbChartDestroy(scope) {
      if (!this._qbCharts) return;
      if (this._qbChartRos && this._qbChartRos[scope]) {
        this._qbChartRos[scope].disconnect();
        this._qbChartRos[scope] = null;
      }
      const u = this._qbCharts[scope];
      if (u) {
        u.destroy();
        this._qbCharts[scope] = null;
      }
    },
    _qbChartBuild(scope) {
      const def = _QB_SCOPES[scope];
      const host = this.$refs[def.host];
      const d = this[def.data];
      if (!def.active(this) || !host || !d || !d.points || !d.points.length) return;
      const data = _qbPointsToData(d.points, Number(d.meta && d.meta.interval_s));
      if (!data) return;
      if (!this._qbCharts) this._qbCharts = {};
      if (!this._qbChartWs) this._qbChartWs = {};
      if (!this._qbChartHs) this._qbChartHs = {};
      if (!this._qbAnchors) this._qbAnchors = {};
      // 静默续拉快路(修「每隔几秒闪一次」): 同一宿主上图还活着就 setData 原地换数据, 不走
      // 销毁重建 —— destroy + new uPlot 会清屏一帧, 每次轮询落袋都闪一次(同 drawer-switch-flicker
      // 「快中间态本身就是闪」型)。宿主被 v-if 拆过/换过(root 已脱离本宿主)或首次建图才走完整重建。
      const prev = this._qbCharts[scope];
      if (prev && prev.root && prev.root.isConnected && prev.root.parentElement === host) {
        this._qbAnchors[scope] = data.anchor;  // 悬停取值锚随新数据换新
        prev.setData([data.xs, data.up, data.dl]);
        return;
      }
      this._qbChartDestroy(scope);
      this._qbChartInjectCss();
      this._qbAnchors[scope] = data.anchor;  // 悬停取值用(非响应式实例字段, 同 _drawerTimer 先例)
      const tk = this._qbChartTokens();
      const W = this._qbChartWs[scope] = host.clientWidth || 860;
      // 高度跟随宿主(流量形态里 .qb-chart-host 撑满抽屉可用高): 量到就用, 量不到(布局未定)回落 300;
      // 抽屉拖拽调高 -> 宿主高度变 -> ResizeObserver 重画, 见下
      const H = this._qbChartHs[scope] = host.clientHeight || 300;
      const fmtAxisSpeed = (v) => this.fmtSpeed(v).replace(" B/s", "");
      const axis = {
        stroke: tk.axis,
        grid: { stroke: tk.grid, width: 1 },
        ticks: { stroke: tk.grid, width: 1 },
        font: "10px ui-monospace, Consolas, monospace",
      };
      const opts = {
        width: W,
        height: H,
        legend: { show: false },  // 图例由模板渲染(.hist-legend 复用, 色义同源)
        cursor: { x: true, y: false, drag: { x: false, y: false } },  // 观察用途: 只留十字线, 不做框选缩放
        scales: {
          x: { time: true },
          y: { range: (u, dmin, dmax) => [0, dmax > 0 ? dmax * 1.05 : 1] },  // 速率从 0 起(口径: 无流量也是真值)
        },
        axes: [
          { ...axis, values: (u, splits) => splits.map((ts) => this._qbTickLabel(ts, scope)) },
          // y 轴槽宽 84: fmtSpeed 轴标最长形("999.9 KiB/s"/"3.86 MiB/s" = 11 字符 x 10px 等宽
          // + 内边距), 60 会把标签左缘截掉(实测 "3.86 MiB/s" 只剩 "86 MiB/s") —— 三主题截图自查发现
          { ...axis, size: 84, values: (u, splits) => splits.map(fmtAxisSpeed) },
        ],
        series: [
          { label: "时刻", value: (u, ts) => this.fmtTime(ts) },
          {
            label: "上行", stroke: tk.up, width: 2,
            spanGaps: false,  // null 桶断线不连线(§5.2 拍板: 纯断线, 无最大跨越)
            points: { show: false, size: 6, filter: (u, sIdx) => _qbIsolatedIdxs(u, sIdx) },
            value: (u, v) => this.fmtSpeed(v),
          },
          {
            label: "下行", stroke: tk.down, width: 2,
            spanGaps: false,
            points: { show: false, size: 6, filter: (u, sIdx) => _qbIsolatedIdxs(u, sIdx) },
            value: (u, v) => this.fmtSpeed(v),
          },
        ],
        hooks: {
          // 悬停取值通道: uPlot 算好 idx/px, Vue 侧渲染 tooltip(数据/格式化走组件既有成员)
          setCursor: [(u) => {
            const idx = u.cursor.idx;
            if (idx == null || idx < 0) {
              this[def.hoverIdx] = -1;
              return;
            }
            this[def.hoverIdx] = idx;
            this[def.hoverLeft] = u.cursor.left;
          }],
        },
      };
      const u = this._qbCharts[scope] = new uPlot(opts, [data.xs, data.up, data.dl], host);
      // 容器尺寸自适应(便签 26-10-04-0134 + 高度跟随): 建图尺寸一次取定后画布不重算 —— 对宿主挂
      // ResizeObserver, 宽/高任一变化即 setSize 重画(抽屉拖拽调高 -> 宿主高变 -> 图跟着长);
      // 宿主 width:100%/height:100% 不依赖图内容(三主题 views.css .qb-chart-host), 观察不会成环。
      // 自摘守卫: 图被重建/销毁(下次 build 先走 _qbChartDestroy 断开)或宿主 DOM 已随 v-if 拆除
      // (流量形态切走只停轮询不销毁图, 脱离 DOM 后 RO 报 0 尺寸)即断开, 不留对旧宿主的观察。
      if (!this._qbChartRos) this._qbChartRos = {};
      const ro = new ResizeObserver(() => {
        if (this._qbCharts[scope] !== u || !host.isConnected) {
          ro.disconnect();
          return;
        }
        const w = host.clientWidth;
        const h = host.clientHeight;
        if (w > 0 && h > 0 && (w !== this._qbChartWs[scope] || h !== this._qbChartHs[scope])) {
          this._qbChartWs[scope] = w;
          this._qbChartHs[scope] = h;
          u.setSize({ width: w, height: h });
        }
      });
      ro.observe(host);
      this._qbChartRos[scope] = ro;
      // prism 五主题动态换肤(theme.js 派发 autoqb:themechange): 令牌值变了就重建(canvas 色不认 CSS 变量)
      if (!this._qbThemeBound) {
        this._qbThemeBound = true;
        this._qbOnThemeChange = () => {
          for (const s of Object.keys(_QB_SCOPES)) {
            if (_QB_SCOPES[s].active(this)) {
              // 先销毁再建: canvas 色是建图时烘焙的令牌值, setData 快路不换色, 换肤必须整图重建
              this._qbChartDestroy(s);
              this._qbChartBuild(s);
            }
          }
        };
        document.documentElement.addEventListener("autoqb:themechange", this._qbOnThemeChange);
      }
    },
    /* x 轴刻度文案(窗口四族): 1m/5m 短窗标到秒(桶可落在同分钟内, HH:MM 会重标);
     * 6mo/1y/all(agg day/month 段窗, §05.3)标年月 —— 月/年视图一格一格看月;
     * 3d/7d/30d(hour 段窗)标日期; 其余 raw 段窗只标时刻(日期由 tooltip 补全) */
    _qbTickLabel(ts, scope) {
      const d = new Date(ts * 1000);
      const p = (n) => String(n).padStart(2, "0");
      const w = this[_QB_SCOPES[scope].window];
      if (w === "6mo" || w === "1y" || w === "all") return `${d.getFullYear()}-${p(d.getMonth() + 1)}`;
      if (w === "3d" || w === "7d" || w === "30d") return `${p(d.getMonth() + 1)}-${p(d.getDate())}`;
      if (w === "1m" || w === "5m") return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
      return `${p(d.getHours())}:${p(d.getMinutes())}`;
    },
    /* 窗口按钮文案(drawer.html 窗口组; 紧凑两字格, 13 档不挤工具条) */
    qbWindowLabel(w) {
      const m = { "1m": "1分", "5m": "5分", "30m": "30分", "3h": "3时", "6h": "6时", "12h": "12时", "24h": "24时", "3d": "3天", "7d": "7天", "30d": "30天", "6mo": "6月", "1y": "1年", "all": "全部" };
      return m[w] || w;
    },
    /* uPlot 1.6.x 必要基础样式(官方 uPlot.min.css 的结构性子集; 不 vendor css 文件, 按计划
     * 以 token 化样式注入一次): 色值两处(十字虚线)走 --fg-dim 令牌, 换肤自动跟随;
     * 图例/标题规则不注入(本组件 legend 关闭/无标题)。 */
    _qbChartInjectCss() {
      if (document.getElementById("aqb-uplot-css")) return;
      const el = document.createElement("style");
      el.id = "aqb-uplot-css";
      el.textContent = [
        "/* aqb: uPlot 基础样式注入(结构性子集, 色值 token 化; 见 qb_traffic_chart.js) */",
        ".uplot, .uplot *, .uplot *::before, .uplot *::after { box-sizing: border-box; }",
        ".uplot { font-family: ui-monospace, Consolas, monospace; line-height: 1.5; width: min-content; }",
        ".u-wrap { position: relative; user-select: none; }",
        ".u-over, .u-under { position: absolute; }",
        ".uplot canvas { display: block; position: relative; width: 100%; height: 100%; }",
        ".u-axis { position: absolute; }",
        ".u-select { position: absolute; pointer-events: none; }",
        ".u-cursor-x, .u-cursor-y { position: absolute; left: 0; top: 0; pointer-events: none; will-change: transform; }",
        ".u-hz .u-cursor-x, .u-vt .u-cursor-y { height: 100%; border-right: 1px dashed var(--fg-dim); }",
        ".u-hz .u-cursor-y, .u-vt .u-cursor-x { width: 100%; border-bottom: 1px dashed var(--fg-dim); }",
        ".u-cursor-pt { position: absolute; top: 0; left: 0; border-radius: 50%; border: 0 solid; pointer-events: none; will-change: transform; background-clip: padding-box !important; }",
        ".u-axis.u-off, .u-select.u-off, .u-cursor-x.u-off, .u-cursor-y.u-off, .u-cursor-pt.u-off { display: none; }",
      ].join("\n");
      document.head.appendChild(el);
    },
  },
};
