/* auto-qb WEB UI · qB 口径流量图(uPlot 双系列组件 + 弹层方法域, 三挂点)
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
 * 三挂点(S5b 起以 _QB_SCOPES 作用域表为单一描述源, 字段名/容器 ref/端点/活跃与竞态判定
 * 各一份): ① global 全局弹层(/api/traffic/qb/global, 今日流量面板入口) ② torrent 种子详情
 * 抽屉「流量」页签(/api/traffic/qb/torrent/{hash}, drawer.js _loadDrawerTab 进) ③ group 分组
 * 弹层(/api/traffic/qb/group/{key}, 组右键菜单入口; key = 分组视图 g.key, 即 encode_group_key
 * 通道与 /api/groups/{key} 同款, 前端不自行编码)。
 *
 * 低频轮询(§07 表「轮询/取数」列): 打开期间按采样间隔续拉 —— 间隔从最近响应 meta.interval_s
 * 取(24h 窗即采样间隔; 30d 窗 meta 是 3600s 桶宽而非采样间隔, 夹取到配置校验上界 600s),
 * 取不到回退 30s 常量; document.hidden 跳过(对齐 drawer.js _startDrawerPoll 先例); 关闭/
 * 切走页签由各 close/switch 路径 _qbPollStop 显式 clearInterval —— 只挂打开期间, 不后台常驻。
 * meta.stale=true 的响应照常渲染(读竞态兜底位, §08, 前端不特殊处理)。
 *
 * 容器 resize 自适应: 建图宽度不是一次取定 —— 建图后对宿主挂 ResizeObserver, 宽度变化即
 * u.setSize 重画(高度恒 300); 销毁在 _qbChartDestroy 断开, 自摘守卫见 _qbChartBuild 内注。
 *
 * 令牌纪律: canvas 内色值(series stroke/grid/axis)无法引用 CSS 变量, 一律在建图时读
 * 三主题令牌(getComputedStyle(:root)); DOM 侧(十字线样式/uPlot 结构样式)由 _qbChartInjectCss
 * 注入 token 化样式(var(--fg-dim)), 换肤自动跟随 —— 禁止硬编码色值。
 * prism 五主题动态换肤派发 autoqb:themechange(theme.js), 图在建时读令牌, 换肤事件触发重建。
 */
/* global uPlot */

/* 轮询间隔边界(ms): 夹取下界 = 配置校验下限 15s(§06), 上界 = 配置校验上限 600s
 * (30d 窗 meta.interval_s=3600 是桶宽, 按它直拉等于一小时不刷新 —— 夹到上界保低频续拉语义);
 * meta 缺失/非法回退 30s 常量(plan §07「采样间隔」基准值)。 */
const _QB_POLL_MIN_MS = 15000;
const _QB_POLL_MAX_MS = 600000;
const _QB_POLL_FALLBACK_MS = 30000;

/* 三挂点作用域表(模块级单一描述源): 字段名一律指到 state.js 根选项的字段(不进 app.mixin,
 * frontend-split 纪律); url(ctx, window) 组端点串, ctx = 单种 hash / 分组 key(经 this 取);
 * active = 该图此刻是否应显示/可拉(建图守卫 + 轮询 tick 跳过判据同源); stale = 在途响应
 * 回落时是否已过期(不落袋, 对齐 drawer.js _drawerStale 代际纪律)。 */
const _QB_SCOPES = {
  global: {
    host: "qbChartHost",
    window: "qbHistWindow", data: "qbHistData", loading: "qbHistLoading", error: "qbHistError",
    hoverIdx: "qbHistHoverIdx", hoverLeft: "qbHistHoverLeft",
    url: (_ctx, w) => "/api/traffic/qb/global?window=" + w,
    ctx: null,
    active: (t) => !!t.qbHistOpen,
    stale: (t) => !t.qbHistOpen,
  },
  torrent: {
    host: "qbTorrentChartHost",
    window: "qbTorrentWindow", data: "qbTorrentData", loading: "qbTorrentLoading", error: "qbTorrentError",
    hoverIdx: "qbTorrentHoverIdx", hoverLeft: "qbTorrentHoverLeft",
    url: (h, w) => "/api/traffic/qb/torrent/" + h + "?window=" + w,
    ctx: (t) => t.drawer.hash,
    // 抽屉打开 + 流量页签 + 展开态 + 种子页种子视图(面板 DOM 随种子视图 v-if 出入,
    // 不可见即跳过 —— 对齐 _startDrawerPoll 的页面守卫先例; 收起态图不可见, 省请求同停)
    active: (t) => !!(t.drawer.open && t.drawer.tab === "traffic" && !t.drawer.collapsed
      && t.page === "groups" && t.viewMode === "torrents"),
    stale: (t, h) => !t.qbTrafficOn || !t.drawer.open || t.drawer.tab !== "traffic" || t.drawer.hash !== h,
  },
  group: {
    host: "qbGroupChartHost",
    window: "qbGroupWindow", data: "qbGroupData", loading: "qbGroupLoading", error: "qbGroupError",
    hoverIdx: "qbGroupHoverIdx", hoverLeft: "qbGroupHoverLeft",
    // key = 分组视图 g.key(服务端 encode_group_key 产物, base64url 天然 URL 安全),
    // 与 delete_flow/commands 的 /api/groups/${k} 同款原样内插 —— 前端不自行编码(§07 表③)
    url: (k, w) => "/api/traffic/qb/group/" + k + "?window=" + w,
    ctx: (t) => t.qbGroupKey,
    active: (t) => !!t.qbGroupOpen,
    stale: (t, k) => !t.qbTrafficOn || !t.qbGroupOpen || t.qbGroupKey !== k,
  },
};

/* 桶序 -> uPlot 数据(模块级纯函数, 供 node 单测探针, 同 hrsCompareRows 先例)。
 * API 响应 points 是「桶值 | null」定长数组, null 元素没有 t; 但栅格是等距的
 * (§5.1 桶键 = first + i*interval), 任取一个非 null 点作锚即可整列重建时刻:
 *   xs[i] = points[k].t + (i - k) * interval
 * null 桶 y 置 null(uPlot spanGaps:false 断线), x 保持等距 —— 缺口位置不漂移。
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
  for (let i = 0; i < n; i++) {
    xs[i] = t0 + (i - k) * interval;
    const p = points[i];
    up[i] = p ? p.up : null;
    dl[i] = p ? p.dl : null;
  }
  return { xs, up, dl, anchor: { k, t0, interval } };
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
     * 分组弹层入口全部 v-if 在它上; 各 _qbLoad 里再兜一道(关闭后无任何请求路径)。 */
    qbTrafficOn() {
      return !!(this.flags && this.flags.qb_traffic_enabled);
    },
    /* 全局弹层入口门(P5a): qbTrafficOn 且今日流量面板在(statusbar 挂点本体, plan §07 表①)。 */
    qbHistEntryOn() {
      return !!(this.flags && this.flags.qb_traffic_enabled && this.todayTraffic);
    },
    /* points 捷径(模板空态判据; 未启用/无数据后端回 points: []) */
    qbHistPoints() {
      return (this.qbHistData && this.qbHistData.points) || [];
    },
    qbTorrentPoints() {
      return (this.qbTorrentData && this.qbTorrentData.points) || [];
    },
    qbGroupPoints() {
      return (this.qbGroupData && this.qbGroupData.points) || [];
    },
    /* 悬停取值(对齐 dialogs.js histHover 十字先例): 时刻 + 上/下行速率(fmtSpeed 同源);
     * 断线桶(null)不出速率, 出「断线」文案 —— §5.2 语义直读。left/flip 由十字线 px 折算。
     * 三挂点同一实现(_qbHoverOf), 这里是全局弹层的一份。 */
    qbHover() {
      return this._qbHoverOf("global");
    },
    qbTorrentHover() {
      return this._qbHoverOf("torrent");
    },
    qbGroupHover() {
      return this._qbHoverOf("group");
    },
    /* 窗口内累计(totals 非空桶求和; 断线/重置桶本就 null 不计 —— §5.1 差分语义) */
    qbHistSummary() {
      return this._qbSummaryOf("global");
    },
    qbTorrentSummary() {
      return this._qbSummaryOf("torrent");
    },
    qbGroupSummary() {
      return this._qbSummaryOf("group");
    },
  },
  methods: {
    /* ---------------- 弹层开关(打开拉取一次 + 起低频轮询; 关闭 clearInterval) ---------------- */
    async openQbHistory() {
      this.qbHistOpen = true;
      this._qbPollStart("global");
      await this._qbLoad("global");
    },
    closeQbHistory() {
      this.qbHistOpen = false;
      this.qbHistHoverIdx = -1;
      this._qbPollStop("global");
      this._qbChartDestroy("global");
    },
    /* 分组弹层(S5b, §07 表③): 入口 = 组右键菜单「qB 口径流量图」(ctx-menus.html, v-if=qbTrafficOn)。
     * key 直用分组视图 g.key(encode_group_key 通道); 组名经 _findGroup 取(decoratedGroups 同 key)。 */
    async openQbGroup(key) {
      if (!this.qbTrafficOn || !key) return;  // fail-closed 双保险(菜单项 v-if 之外的加载路径兜底)
      const g = this._findGroup(key);
      this.menu.visible = false;  // 右键菜单入口先收菜单(与 openMetaDialog 同口径)
      this.qbGroupKey = key;
      this.qbGroupName = (g && g.name) || "";
      this.qbGroupOpen = true;
      this._qbPollStart("group");
      await this._qbLoad("group");
    },
    closeQbGroup() {
      this.qbGroupOpen = false;
      this.qbGroupHoverIdx = -1;
      this._qbPollStop("group");
      this._qbChartDestroy("group");
    },
    /* 窗口切换(24h/30d): 换窗即重拉重画; 打开中的轮询定时器由 _qbPollResync 按新窗重排 */
    qbHistSetWindow(w) {
      return this._qbSetWindow("global", w);
    },
    qbTorrentSetWindow(w) {
      return this._qbSetWindow("torrent", w);
    },
    qbGroupSetWindow(w) {
      return this._qbSetWindow("group", w);
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
      // 等 v-if 分支进 DOM 再建图(uPlot 要量容器宽); 轮询间隔随新 meta 重排(换窗/间隔变更)
      this.$nextTick(() => this._qbChartBuild(scope));
      this._qbPollResync(scope);
    },
    /* 悬停桶的时刻(null 桶也能定位: 栅格等距, 用建图时的锚推算) */
    _qbBucketTs(scope, i) {
      const a = this._qbAnchors && this._qbAnchors[scope];
      if (!a) {
        const d = this[_QB_SCOPES[scope].data];
        const p = d && d.points ? d.points[i] : null;
        return p ? p.t : 0;
      }
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
    /* meta.interval_s 变化(换窗 24h<->30d)时按新间隔重排; 定时器本就停着则不动 */
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
        up: pick("--today-up", "--teal", "--fg"),
        down: pick("--today-down", "--indigo", "--fg"),
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
      if (!this._qbAnchors) this._qbAnchors = {};
      this._qbChartDestroy(scope);
      this._qbChartInjectCss();
      this._qbAnchors[scope] = data.anchor;  // 悬停取值用(非响应式实例字段, 同 _drawerTimer 先例)
      const tk = this._qbChartTokens();
      const H = 300;
      const W = this._qbChartWs[scope] = host.clientWidth || 860;
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
      // 容器 resize 自适应(便签 26-10-04-0134): 建图宽度一次取定后画布不重算 —— 对宿主挂
      // ResizeObserver, 宽度变了 setSize 重画(高度恒 300 不参与); 宿主 width:100% 不依赖图
      // 内容(三主题 views.css .qb-chart-host), 观察不会成环。自摘守卫: 图被重建/销毁
      // (下次 build 先走 _qbChartDestroy 断开)或宿主 DOM 已随 v-if 拆除(torrent 切页签只停
      // 轮询不销毁图, 脱离 DOM 后 RO 报 0 宽)即断开, 不留对旧宿主的观察。
      if (!this._qbChartRos) this._qbChartRos = {};
      const ro = new ResizeObserver(() => {
        if (this._qbCharts[scope] !== u || !host.isConnected) {
          ro.disconnect();
          return;
        }
        const w = host.clientWidth;
        if (w > 0 && w !== this._qbChartWs[scope]) {
          this._qbChartWs[scope] = w;
          u.setSize({ width: w, height: H });
        }
      });
      ro.observe(host);
      this._qbChartRos[scope] = ro;
      // prism 五主题动态换肤(theme.js 派发 autoqb:themechange): 令牌值变了就重建(canvas 色不认 CSS 变量)
      if (!this._qbThemeBound) {
        this._qbThemeBound = true;
        this._qbOnThemeChange = () => {
          for (const s of Object.keys(_QB_SCOPES)) {
            if (_QB_SCOPES[s].active(this)) this._qbChartBuild(s);
          }
        };
        document.documentElement.addEventListener("autoqb:themechange", this._qbOnThemeChange);
      }
    },
    /* x 轴刻度文案: 24h 只标时刻(日期由 tooltip 补全), 30d 标日期(窗口按挂点各读各的) */
    _qbTickLabel(ts, scope) {
      const d = new Date(ts * 1000);
      const p = (n) => String(n).padStart(2, "0");
      if (this[_QB_SCOPES[scope].window] === "30d") return `${p(d.getMonth() + 1)}-${p(d.getDate())}`;
      return `${p(d.getHours())}:${p(d.getMinutes())}`;
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
