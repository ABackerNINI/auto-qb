/* auto-qb WEB UI · qB 口径流量图(uPlot 双系列组件 + 弹层方法域)
 *
 * plan 26-10-03-0946 方案C §07 P5a。一个「双系列(上行/下行)时间曲线」封装, 三图(全局/单种/分组)
 * 共用: uPlot options 样板(axes/series/scales/cursor)收在 _qbChartBuild 单点, 调用方只给
 * points + 容器; null 桶 = 断线不连线(uPlot spanGaps:false, §5.2 拍板语义)。
 *
 * 约定与 dialogs.js / hr_status.js 同范式: 挂到 window.AQB_QB_TRAFFIC, 由 app.js 末尾
 * app.mixin(window.AQB_QB_TRAFFIC) 注入同一个 Vue 实例 —— 方法体里的 this 仍是那个组件实例。
 * !本文件在 HTML 里必须排在 app.js **之前**; data 字段在 state.js(根选项, 不进 app.mixin,
 *   见 frontend-split 纪律), uPlot vendor 由三主题 tpl-manifest scripts 登记(boot.js 依序放行)。
 *
 * 令牌纪律: canvas 内色值(series stroke/grid/axis)无法引用 CSS 变量, 一律在建图时读
 * 三主题令牌(getComputedStyle(:root)); DOM 侧(十字线样式/uPlot 结构样式)由 _qbChartInjectCss
 * 注入 token 化样式(var(--fg-dim)), 换肤自动跟随 —— 禁止硬编码色值。
 * prism 五主题动态换肤派发 autoqb:themechange(theme.js), 图在建时读令牌, 换肤事件触发重建。
 */
/* global uPlot */

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

window.AQB_QB_TRAFFIC = {
  computed: {
    /* 入口门(P5 验收): flags.qb_traffic_enabled(/api/webui/flags 下发, fail-closed 默认 false)
     * 且今日流量面板在(statusbar 挂点本体, plan §07 表「今日流量面板」)。false = 入口不渲染,
     * openQbHistory 无触发路径 = 不发请求。 */
    qbHistEntryOn() {
      return !!(this.flags && this.flags.qb_traffic_enabled && this.todayTraffic);
    },
    /* points 捷径(模板空态判据; 未启用/无数据后端回 points: []) */
    qbHistPoints() {
      return (this.qbHistData && this.qbHistData.points) || [];
    },
    /* 悬停取值(对齐 dialogs.js histHover 十字先例): 时刻 + 上/下行速率(fmtSpeed 同源);
     * 断线桶(null)不出速率, 出「断线」文案 —— §5.2 语义直读。left/flip 由十字线 px 折算。 */
    qbHover() {
      const d = this.qbHistData;
      const i = this.qbHistHoverIdx;
      if (!d || !d.points || i < 0 || i >= d.points.length) return null;
      const p = d.points[i];
      const tip = this.fmtTime(this._qbBucketTs(i));
      const flip = this._qbChartW > 0 && this.qbHistHoverLeft > this._qbChartW * 0.62;
      if (!p) return { tip, gap: true, left: this.qbHistHoverLeft, flip };
      return { tip, up: p.up, dl: p.dl, left: this.qbHistHoverLeft, flip };
    },
    /* 窗口内累计(totals 非空桶求和; 断线/重置桶本就 null 不计 —— §5.1 差分语义) */
    qbHistSummary() {
      const d = this.qbHistData;
      if (!d) return null;
      const sum = (key) => (d.totals || []).reduce((a, p) => a + ((p && p[key]) || 0), 0);
      return { buckets: this.qbHistPoints.length, up: sum("up"), down: sum("dl") };
    },
  },
  methods: {
    /* ---------------- 弹层开关(打开时拉取一次; 低频轮询 S5b 统一补齐) ---------------- */
    async openQbHistory() {
      this.qbHistOpen = true;
      await this.loadQbHistory();
    },
    closeQbHistory() {
      this.qbHistOpen = false;
      this.qbHistHoverIdx = -1;
      this._qbChartDestroy();
    },
    /* 窗口切换(24h/30d): 换窗即重拉重画 */
    qbHistSetWindow(w) {
      if (this.qbHistWindow === w) return;
      this.qbHistWindow = w;
      return this.loadQbHistory();
    },
    async loadQbHistory() {
      this.qbHistLoading = true;
      this.qbHistError = "";
      try {
        const data = await this.api("/api/traffic/qb/global?window=" + encodeURIComponent(this.qbHistWindow));
        this.qbHistData = data;
      } catch (e) {
        if (!e.auth) this.qbHistError = e.message || "加载失败";
        this.qbHistData = null;
      } finally {
        this.qbHistLoading = false;
      }
      // 等 v-if 分支进 DOM 再建图(uPlot 要量容器宽)
      this.$nextTick(() => this._qbChartBuild());
    },
    /* 悬停桶的时刻(null 桶也能定位: 栅格等距, 用建图时的锚推算) */
    _qbBucketTs(i) {
      const a = this._qbAnchor;
      if (!a) {
        const p = this.qbHistPoints[i];
        return p ? p.t : 0;
      }
      return a.t0 + (i - a.k) * a.interval;
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
    _qbChartDestroy() {
      if (this._qbChart) {
        this._qbChart.destroy();
        this._qbChart = null;
      }
    },
    _qbChartBuild() {
      const host = this.$refs.qbChartHost;
      const d = this.qbHistData;
      if (this.qbHistOpen === false || !host || !d || !this.qbHistPoints.length) return;
      const data = _qbPointsToData(d.points, Number(d.meta && d.meta.interval_s));
      if (!data) return;
      this._qbChartDestroy();
      this._qbChartInjectCss();
      this._qbAnchor = data.anchor;  // 悬停取值用(非响应式实例字段, 同 _drawerTimer 先例)
      const tk = this._qbChartTokens();
      const H = 300;
      const W = this._qbChartW = host.clientWidth || 860;
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
          { ...axis, values: (u, splits) => splits.map((ts) => this._qbTickLabel(ts)) },
          { ...axis, size: 60, values: (u, splits) => splits.map(fmtAxisSpeed) },
        ],
        series: [
          { label: "时刻", value: (u, ts) => this.fmtTime(ts) },
          {
            label: "上行", stroke: tk.up, width: 2,
            spanGaps: false,  // null 桶断线不连线(§5.2 拍板: 纯断线, 无最大跨越)
            points: { show: false },  // 高密度下 uPlot 默认点标抖动, 十字线+tooltip 取值已对齐既有弹层
            value: (u, v) => this.fmtSpeed(v),
          },
          {
            label: "下行", stroke: tk.down, width: 2,
            spanGaps: false,
            points: { show: false },
            value: (u, v) => this.fmtSpeed(v),
          },
        ],
        hooks: {
          // 悬停取值通道: uPlot 算好 idx/px, Vue 侧渲染 tooltip(数据/格式化走组件既有成员)
          setCursor: [(u) => {
            const idx = u.cursor.idx;
            if (idx == null || idx < 0) {
              this.qbHistHoverIdx = -1;
              return;
            }
            this.qbHistHoverIdx = idx;
            this.qbHistHoverLeft = u.cursor.left;
          }],
        },
      };
      this._qbChart = new uPlot(opts, [data.xs, data.up, data.dl], host);
      // prism 五主题动态换肤(theme.js 派发 autoqb:themechange): 令牌值变了就重建(canvas 色不认 CSS 变量)
      if (!this._qbThemeBound) {
        this._qbThemeBound = true;
        this._qbOnThemeChange = () => {
          if (this.qbHistOpen) this._qbChartBuild();
        };
        document.documentElement.addEventListener("autoqb:themechange", this._qbOnThemeChange);
      }
    },
    /* x 轴刻度文案: 24h 只标时刻(日期由 tooltip 补全), 30d 标日期 */
    _qbTickLabel(ts) {
      const d = new Date(ts * 1000);
      const p = (n) => String(n).padStart(2, "0");
      if (this.qbHistWindow === "30d") return `${p(d.getMonth() + 1)}-${p(d.getDate())}`;
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
