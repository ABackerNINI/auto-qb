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
 * 静默续拉(2026-10-04 修「每隔几秒闪一次」; 2026-10-05 补齐空态/错误态): 续拉对用户不可见 ——
 * 模板 loading 空态只在「本作用域尚无任何落袋结果」时接管正文(drawer.html qbCurPending =
 * loading + 无数据 + 无错误), 数据落袋走 _qbChartBuild 的 setData 原地快路(同一宿主上图还活着
 * 就不销毁重建; 完整重建仅首图/宿主被拆后/换肤三次)。2026-10-04 那版只门了「有图」一态
 * (!qbCurPoints.length), 空数据集的空态文案与错误文案仍会被每个轮询周期的 loading 顶掉一帧 ——
 * 判据因此改为按「有无落袋结果」而不是按「有无点」。
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
 *
 * 窗口档位单点(QB_WINDOW_NAMES)与「视图选择」持久化(2026-10-05, 用户拍板): 十三档清单、
 * 前后切换(qbCycleWindow)与落盘校验(qbInitialWindow)共用同一份常量 —— 展示面模板走
 * qbWindowNames computed, 不再各自硬编码。持久化粒度 = **全局单独一份 / 分组与种子共用一份**
 * (autoqb.ui.qbWinGlobal / autoqb.ui.qbWinShared, 键单点 qbWinStoreKey): 全局图与单对象图
 * 观察尺度习惯不同, 而组与种子常被当作同类"单对象"视图对照着看。初值读取 qbInitialWindow
 * 定义在本文件(三份 tpl-manifest 里本文件均排在 state.js 之前, 见 prism/atlas/console),
 * 由 state.js 的 data() 调用 —— 档位域归流量图模块所有。落盘纪律与 persistDrawerTab 同款:
 * 只落"选了哪档"这个用户意图, 写失败吞异常(刷新后回落默认), 不打断换窗。
 * 快捷键三入口(shortcuts.js): 打开全局图 Ctrl+Backslash / 详情面板流量页签 Alt+5 /
 * 窗口前后切换 [ ](后两条走 when 条件绑定, 仅流量图可见时消费键位)。
 *
 * 纵轴固定模式 + 画布注解层(2026-10-08, 用户拍板; 三挂点通用, issue 26-10-07-0149 认领一并做):
 * 纵轴三态 auto(默认, 随数据峰值) / limit(全局限速 ×1.2) / manual(手动 MiB/s)。限速一律取
 * **qB 全局限速上下行较大者**(三作用域同源); 峰值超出固定上限时**按峰值显示**(上限只保底,
 * 不裁剪数据 —— _qbYRange)。偏好**三作用域各自独立**落 localStorage(qbYAxisStoreKey)。
 * 注解层走 uPlot draw/drawClear 钩子画在**同一张画布**上(共享图面, 三挂点 + 经典/所有变体
 * 全生效): 限速虚线(上下行各一条, 只画落在可视值域内的限速 —— 自动模式下峰值未超限速时线在
 * 顶沿之上, 自然不画)+ 缺口斜纹(null 桶游程铺 45 度斜纹, 画在系列之下)。
 * !2026-10-08 修「缺口斜纹几乎不可分辨」: 斜纹原走 tk.grid(--hairline, alpha 仅 0.05~0.08 的
 * 装饰性 1px 发丝线令牌), 再叠 globalAlpha 0.5 ⇒ 有效不透明度约 3%, 深色底上等于没画(亮主题
 * 同理)。改走**专用高对比令牌 --qb-gap-hatch**(0.18~0.25), 并去掉多余的 globalAlpha 折半;
 * 几何(斜纹覆盖区间)经逐条线段比对与代数验证**与原式恒等**, 未变。
 * 画布坐标口径见 _qbCanvasScale 注(uPlot 1.6.x ctx 无 transform, 坐标 = 设备像素)。
 */
/* global uPlot */

/* 轮询间隔边界(ms): 夹取下界 = 配置校验下限 1.5s(§06, A4: 采样间隔下限放宽后同步对齐,
 * 上界 = 配置校验上限 600s (hour 及以上段窗(3d/7d/30d/6mo/1y/all) meta.interval_s 是桶宽
 * 而非采样间隔(3600s/86400s/标称月长), 按它直拉等于一小时不刷新 —— 夹到上界保低频续拉
 * 语义); meta 缺失/非法回退 30s 常量(plan §07「采样间隔」基准值)。 */
const _QB_POLL_MIN_MS = 1500;
const _QB_POLL_MAX_MS = 600000;
const _QB_POLL_FALLBACK_MS = 30000;

/* 窗口档位(13 档, 顺序即展示序: 短窗 -> 长窗; 与后端 webui/server/traffic_qb.py 的
 * WINDOW_NAMES 逐字一致) —— 展示(drawer.html v-for 走 qbWindowNames computed)、前后切换
 * (qbCycleWindow)、持久化校验(qbInitialWindow)三处共用同一份, 不再各自硬编码。 */
const QB_WINDOW_NAMES = ["1m", "5m", "30m", "3h", "6h", "12h", "24h", "3d", "7d", "30d", "6mo", "1y", "all"];
const QB_WINDOW_DEFAULT = "24h";

/* 窗口选择持久化键(2026-10-05 用户拍板粒度: 全局单独一份, 分组/种子共用一份) ——
 * 全局图看的是"整机吞吐尺度", 种子/组图看的是"单对象活跃尺度", 两者习惯常不同故分开;
 * 而组与种子常被当作同一类"单对象"视图对照着看, 故共用一份。 */
const QB_WIN_STORE_KEY_GLOBAL = "autoqb.ui.qbWinGlobal";
const QB_WIN_STORE_KEY_SHARED = "autoqb.ui.qbWinShared";
function qbWinStoreKey(scope) {
  return scope === "global" ? QB_WIN_STORE_KEY_GLOBAL : QB_WIN_STORE_KEY_SHARED;
}
/* 窗口初值(持久化偏好; 与 initialDrawerTab 同纪律: 只认合法档位, 坏值/无存储回落默认)。
 * 定义在本文件(三份 tpl-manifest 里本文件均排在 state.js 之前)由 state.js 的 data() 调用;
 * localStorage 访问只在函数体内(本文件会被 test_webui_static_dom_panel.py 的 node 探针 eval, 顶层不得碰 DOM/BOM)。 */
function qbInitialWindow(scope) {
  try {
    const v = localStorage.getItem(qbWinStoreKey(scope));
    if (QB_WINDOW_NAMES.includes(v)) return v;
  } catch (e) {
    /* 无存储/坏数据: 回落默认(偏好类读取失败不该影响启动) */
  }
  return QB_WINDOW_DEFAULT;
}

/* 纵轴固定模式(2026-10-08 用户拍板, 三挂点通用): "auto" 自动(随数据峰值) / "limit" 限速+20%
 * / "manual" 手动 MiB/s。限速一律取 **qB 全局限速**(三作用域同源, 用户拍板), 方向取上下行
 * 限速的**较大者** —— 纵轴上下行共用一条, 取大者两条曲线都落在固定上限内。峰值超出固定上限
 * 时**按峰值显示**(上限只保底, 不裁剪数据; 见 _qbYRange)。 */
const QB_YAXIS_MODES = ["auto", "limit", "manual"];
const QB_YAXIS_DEFAULT = "auto";
const QB_YAXIS_LIMIT_FACTOR = 1.2;
const QB_YAXIS_MIB = 1024 * 1024;

/* 纵轴偏好存储键(2026-10-08 用户拍板粒度: **三作用域各自独立一份**, 与窗口档位「全局单独/
 * 组种共用」不同) —— 全局图与单对象图的观察尺度习惯不同, 组与种子也各有偏好。 */
const QB_YAXIS_STORE_KEYS = {
  global: "autoqb.ui.qbYAxisGlobal",
  torrent: "autoqb.ui.qbYAxisTorrent",
  group: "autoqb.ui.qbYAxisGroup",
};
function qbYAxisStoreKey(scope) {
  return QB_YAXIS_STORE_KEYS[scope] || QB_YAXIS_STORE_KEYS.global;
}
/* 纵轴初值(与 qbInitialWindow 同纪律: 只认合法模式与正数手动值, 坏值/无存储回落默认;
 * localStorage 访问只在函数体内 —— 本文件会被 node 探针 eval, 顶层不得碰 DOM/BOM)。
 * 返回 { mode, manual }: manual 单位 MiB/s, 0 = 未设值。 */
function qbInitialYAxis(scope) {
  try {
    const raw = localStorage.getItem(qbYAxisStoreKey(scope));
    if (raw) {
      const v = JSON.parse(raw);
      if (v && QB_YAXIS_MODES.includes(v.mode)) {
        const manual = Number(v.manual);
        return { mode: v.mode, manual: Number.isFinite(manual) && manual > 0 ? manual : 0 };
      }
    }
  } catch (e) {
    /* 无存储/坏 JSON: 回落默认(偏好类读取失败不该影响启动) */
  }
  return { mode: QB_YAXIS_DEFAULT, manual: 0 };
}

/* 三挂点作用域表(模块级单一描述源): 字段名一律指到 state.js 根选项的字段(不进 app.mixin,
 * frontend-split 纪律); url(ctx, window) 组端点串, ctx = 单种 hash / 分组 key(经 this 取);
 * active = 该图此刻是否应显示/可拉(建图守卫 + 轮询 tick 跳过判据同源); stale = 在途响应
 * 回落时是否已过期(不落袋, 对齐 drawer.js _drawerStale 代际纪律)。
 * host 三挂点统一为 qbChartHost: 三形态互斥(同一时刻只渲染一个), 正文块共用(drawer.html)。 */
const _QB_SCOPES = {
  global: {
    host: "qbChartHost",
    window: "qbHistWindow", data: "qbHistData", loading: "qbHistLoading", error: "qbHistError",
    hoverIdx: "qbHistHoverIdx", hoverLeft: "qbHistHoverLeft", yaxis: "qbHistYAxis",
    url: (_ctx, w) => "/api/traffic/qb/global?window=" + w,
    ctx: null,
    // 面板 visible 同源守卫(drawerVisible): 面板只在主内容页渲染, 隐藏期还拉 = 对着不在 DOM 里的
    // 面板取数(纯浪费 + 回页数据陈旧), 故 tick/建图一律跳过 —— 回到主内容页由 watch(drawerVisible)
    // 补拉一发接着续(见 state.js)
    active: (t) => t.drawer.open && t.page === "groups"
      && t.drawer.kind === "traffic" && t.drawer.scope === "global",
    stale: (t) => !(t.drawer.open && t.drawer.kind === "traffic" && t.drawer.scope === "global"),
  },
  torrent: {
    host: "qbChartHost",
    window: "qbTorrentWindow", data: "qbTorrentData", loading: "qbTorrentLoading", error: "qbTorrentError",
    hoverIdx: "qbTorrentHoverIdx", hoverLeft: "qbTorrentHoverLeft", yaxis: "qbTorrentYAxis",
    url: (h, w) => "/api/traffic/qb/torrent/" + h + "?window=" + w,
    ctx: (t) => t.drawer.hash,
    // 抽屉打开 + 种子形态 + 流量页签 + 主内容页(面板 DOM 随 drawerVisible 出入,
    // 不可见即跳过 —— 对齐 _startDrawerPoll 的页面守卫先例)。
    // 2026-10-08(计划 26-10-08-1217): 视图守卫解除 —— 面板三视图共用, 从辅种页/追剧页成员行
    // 打开的种子详情其流量页签同样要拉要画。
    active: (t) => !!(t.drawer.open && t.drawer.kind === "seed" && t.drawer.tab === "traffic"
      && t.page === "groups"),
    stale: (t, h) => !(t.qbTrafficOn && t.drawer.open && t.drawer.kind === "seed"
      && t.drawer.tab === "traffic" && t.drawer.hash === h),
  },
  group: {
    host: "qbChartHost",
    window: "qbGroupWindow", data: "qbGroupData", loading: "qbGroupLoading", error: "qbGroupError",
    hoverIdx: "qbGroupHoverIdx", hoverLeft: "qbGroupHoverLeft", yaxis: "qbGroupYAxis",
    // key = 分组视图 g.key(服务端 encode_group_key 产物, base64url 天然 URL 安全),
    // 与 delete_flow/commands 的 /api/groups/${k} 同款原样内插 —— 前端不自行编码(§07 表③)
    url: (k, w) => "/api/traffic/qb/group/" + k + "?window=" + w,
    ctx: (t) => t.qbGroupKey,
    // page 守卫与 global 同(drawerVisible 单点): 非主内容页面板不在 DOM, 不拉不画
    active: (t) => t.drawer.open && t.page === "groups"
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

/* y 轴值域(模块级纯函数, 供 node 单测探针): 默认 [0, peak*1.05](无数据回落 1);
 * 固定上限 cap>0 时取 max(cap, peak*1.05) —— 峰值超出固定上限**按峰值显示**(用户拍板:
 * 固定上限只保底, 绝不裁剪数据; 峰值低于上限时上限即顶, 曲线高度可跨窗口对照)。 */
function _qbYRange(dmax, cap) {
  const peak = dmax > 0 ? dmax : 0;
  const top = peak > 0 ? peak * 1.05 : 1;
  return [0, cap > 0 ? Math.max(cap, top) : top];
}

/* 缺口游程(连续 null 桶的 [起, 止] 索引对; 模块级纯函数供 node 单测)。
 * 判据 = **上下行皆 null**(后端整桶 null 时两列同 null; 单列 null 防御性不误判成缺口)。 */
function _qbGapRuns(up, dl) {
  const out = [];
  let s = -1;
  for (let i = 0; i < up.length; i++) {
    const gap = up[i] == null && dl[i] == null;
    if (gap && s < 0) s = i;
    if (!gap && s >= 0) {
      out.push([s, i - 1]);
      s = -1;
    }
  }
  if (s >= 0) out.push([s, up.length - 1]);
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
    /* 流量形态头部标题(kind === "traffic" 时用; 单种走种子详情头部, 不消费本值)。
     * 2026-10-08 用户要求标题缩短为「qB流量图」—— 头部同排要容纳 13 档窗口档位与纵轴控件,
     * 长标题会把档位挤出去。分组/种子保留各自名称(它们本就短, 且要区分对象)。 */
    qbTrafficTitle() {
      const s = this.qbCurScope;
      if (s === "global") return "qB流量图";
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
    /* 首载空态判据(2026-10-05 修「空态每隔一个轮询周期闪一次」): loading 空态只在**本作用域
     * 尚无任何落袋结果**时接管正文。判据三合一 = 在途 loading + 无数据 + 无错误 ——
     * ① 空态响应落袋后 data 是非 null 对象(空 points 也是对象, 只有出错才置 null), 续拉不再接管;
     * ② 错误态落袋后 error 非空, 同样不接管(错误文案由下一次成功落袋清除, 见 _qbLoad);
     * 已有结果时续拉一律不动正文 —— 图/空态文案/错误文案都是「既有状态」(同 drawer-switch-flicker
     * 的「加载态立即点亮 = 制造新闪烁」)。 */
    qbCurPending() {
      return !!(this.qbCurLoading && !this.qbCurData && !this.qbCurError);
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
    /* 窗口档位清单(模板 v-for 的唯一来源, 与前后切换/持久化校验同源 QB_WINDOW_NAMES) */
    qbWindowNames() {
      return QB_WINDOW_NAMES;
    },
    /* ---------------- 纵轴固定模式(2026-10-08; 三挂点各自独立) ---------------- */
    /* 当前作用域的纵轴设置 {mode, manual}(字段名见 _QB_SCOPES.yaxis; 非流量形态返回 null) */
    qbCurYAxis() {
      const s = this.qbCurScope;
      return s ? this[_QB_SCOPES[s].yaxis] : null;
    },
    qbYAxisMode() {
      const y = this.qbCurYAxis;
      return y ? y.mode : QB_YAXIS_DEFAULT;
    },
    qbYAxisManual() {
      const y = this.qbCurYAxis;
      return y ? y.manual : 0;
    },
    /* 工具条读数(当前生效上限, 自解释): 固定模式报上限值; 缺值/自动报回退说明 */
    qbYAxisCapText() {
      const s = this.qbCurScope;
      if (!s) return "";
      const mode = this[_QB_SCOPES[s].yaxis].mode;
      const cap = this._qbYCapOf(s);
      if (mode === "limit") {
        return cap > 0 ? "上限 " + this.fmtSpeed(cap) + "(全局限速 ×1.2)" : "无全局限速 · 按自动";
      }
      if (mode === "manual") return cap > 0 ? "上限 " + this.fmtSpeed(cap) : "未设值 · 按自动";
      return "自动(随数据峰值)";
    },
  },
  /* 限速值变化(首次到手 / qB 重连 / 运行中改限速)时重排一次 y 轴 —— 长窗轮询间隔可夹到
   * 600s, 不重排则「限速+20%」迟迟不生效。注册走根实例 mounted(与 drawer_templates.js
   * 同款): 本 mixin 经 app.mixin 全局注入, <transition> 的 BaseTransition 假实例没有数据面,
   * 写成 watch 选项会在其上求值即抛; mounted 里先按 this.drawer 守卫剔除假实例。 */
  mounted() {
    if (!this.drawer) return;  /* BaseTransition 等假实例无数据面: 跳过(真根实例恒有 drawer) */
    this._qbLimitUnwatch = this.$watch(() => this._qbGlobalLimit(), () => {
      for (const s of Object.keys(_QB_SCOPES)) {
        if (_QB_SCOPES[s].active(this) && this._qbYCapOf(s) > 0) this._qbChartRescale(s);
      }
    });
  },
  beforeUnmount() {
    if (this._qbLimitUnwatch) {
      this._qbLimitUnwatch();
      this._qbLimitUnwatch = null;
    }
  },
  methods: {
    /* ---------------- 流量形态开关(三挂点并入抽屉; 打开 = 把抽屉切到流量形态) ----------------
     * 全局/分组: openDrawerTraffic(scope, key) 整体重置抽屉状态并拉数 + 起低频轮询
     * (同目标重入短路: 已开着同一目标时幂等返回, 不收图不重拉 —— 重复按键不闪);
     * 单种: 走 drawer.js openTorrentDrawer + drawerTab('traffic')(页签本体, 不在本模块)。
     * 关闭统一走 drawer.js closeDrawer()(Esc/关闭钮/切页三路同口), 收轮询与图见 _qbTeardown。 */
    async openQbHistory() {
      // 状态栏入口本身 v-if 在 qbHistEntryOn 上(关闭时无按钮), 这里补的是**键盘入口**
      // (shortcuts.js open-qb-traffic): 功能关闭时按了键要给出反馈, 不静默
      if (!this.qbTrafficOn) {
        this.toast("qB 口径流量图未启用", "info", 2500);
        return;
      }
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
      // 入口不止在主内容页: 状态栏按钮与全局快捷键(shortcuts.js open-qb-traffic)任意页可达,
      // 而面板只在主内容页渲染 —— 不先回主内容页就是「点了没反应」(状态翻了、面板不在 DOM)。
      // 显式触发权 > 停留位置: 用户点图就是想看图, 与 goView 同款切页(抽屉状态不清)
      if (this.page !== "groups") this.page = "groups";
      // 同目标幂等短路: 已开着同一形态同一目标(分组再比 key)时重按入口(Ctrl+\ / 状态栏钮)不重建
      // —— 走下方全量路径等于把收图销毁+抽屉重建+首拉各闪一遍(pitfalls drawer-switch-flicker:
      // 快中间态本身就是闪); 右键菜单入口仍收菜单
      if (this.drawer.open && this.drawer.kind === "traffic" && this.drawer.scope === scope
          && (scope !== "group" || this.qbGroupKey === key)) {
        this.menu.visible = false;
        return;
      }
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
        open: true, hash: "", tab: "general", loading: false, error: "",
        detail: null, trackers: [], files: [], peers: { peers: [] },
        trackersLoading: false, filesLoading: false, peersLoading: false, switching: false,
        kind: "traffic", scope,
      };
      this.persistDrawerOpen();  // W3 开合态记录(D1: 只写不回读)
      this._qbLoad(scope);
      this._qbPollStart(scope);
    },
    /* 面板重新进场后的补拉(state.js watch(drawerVisible) 的可见分支): 隐藏期(非主内容页)轮询被
     * active 守卫跳过, 数据与宿主都已陈旧 —— 这里补一发同时在 $nextTick 里对新宿主重建图
     * (_qbLoad 内含建图单点)。**在途不叠加**: 打开路径本已经先发了一发(面板进场与 _qbLoad 在
     * 同一个 flush 前后脚走), 叠加等于把首次打开的请求翻倍(同轮询 tick 的 loading 互斥口径)。 */
    _qbReloadOnEnter(scope) {
      const def = _QB_SCOPES[scope];
      if (!def || this[def.loading]) return;
      this._qbLoad(scope);
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
      this.persistQbWindow(scope, w);  // 视图选择是用户意图: 换窗即落盘, 刷新后保持(见文件头)
      return this._qbLoad(scope);
    },
    /* 窗口选择落盘(与 persistDrawerTab 同纪律: 只落"选了哪档"这个意图, 写失败吞异常)。
     * 键单点 qbWinStoreKey: 全局一份 / 分组与种子共用一份。 */
    persistQbWindow(scope, w) {
      try {
        localStorage.setItem(qbWinStoreKey(scope), w);
      } catch { /* 写入失败: 本轮仍生效, 刷新后回落默认 */ }
    },
    /* ---------------- 纵轴固定模式(2026-10-08; 三挂点各自独立持久化) ---------------- */
    /* 全局限速(上下行**较大者**, bytes/s; 0 = 无限速或字段未知) —— 三作用域同源(用户拍板)。
     * 取值单点 speedLimitBytes(dialogs.js, 与状态栏/速度染色同源; null = 未知, 0 = 不限速)。 */
    _qbGlobalLimit() {
      const { up, down } = this.speedLimitBytes || {};
      let best = 0;
      if (typeof up === "number" && up > best) best = up;
      if (typeof down === "number" && down > best) best = down;
      return best;
    },
    /* 该作用域的固定上限(bytes/s; 0 = 不固定, 回落自动)。"limit" = 全局限速 ×1.2(无全局限速
     * 时回落 0); "manual" = 手动 MiB/s 换算(bytes/s, 未设值回落 0)。 */
    _qbYCapOf(scope) {
      const def = _QB_SCOPES[scope];
      const y = def && this[def.yaxis];
      if (!y) return 0;
      if (y.mode === "limit") {
        const lim = this._qbGlobalLimit();
        return lim > 0 ? lim * QB_YAXIS_LIMIT_FACTOR : 0;
      }
      if (y.mode === "manual") return y.manual > 0 ? y.manual * QB_YAXIS_MIB : 0;
      return 0;
    },
    /* 切纵轴模式(自动/限速+20%/手动): 落盘 + 立即重排 y 轴。不动数据/不重建图 —— 上限只改
     * scale 值域, 重取数等于白拉一发(与换窗的 _qbLoad 路径刻意分开)。 */
    qbSetYAxisMode(mode) {
      const s = this.qbCurScope;
      if (!s || !QB_YAXIS_MODES.includes(mode)) return;
      const y = this[_QB_SCOPES[s].yaxis];
      if (y.mode === mode) return;
      y.mode = mode;  // Vue 3 深层响应式: 对象属性赋值即触发(根 data 里是普通对象)
      this.persistQbYAxis(s);
      this._qbChartRescale(s);
    },
    /* 改手动上限值(MiB/s; <=0 或非法 = 未设值, 按自动): 落盘 + 立即重排 */
    qbSetYAxisManual(v) {
      const s = this.qbCurScope;
      if (!s) return;
      const num = Number(v);
      const manual = Number.isFinite(num) && num > 0 ? num : 0;
      const y = this[_QB_SCOPES[s].yaxis];
      if (y.manual === manual) return;
      y.manual = manual;
      this.persistQbYAxis(s);
      this._qbChartRescale(s);
    },
    /* 纵轴偏好落盘(与 persistQbWindow 同纪律: 只落用户意图, 写失败吞异常; 键按 scope 分派) */
    persistQbYAxis(scope) {
      try {
        const y = this[_QB_SCOPES[scope].yaxis];
        localStorage.setItem(qbYAxisStoreKey(scope), JSON.stringify({ mode: y.mode, manual: y.manual }));
      } catch { /* 写入失败: 本轮仍生效, 刷新后回落默认 */ }
    },
    /* y 轴重排(上限变更/限速到手): 只重算 scale 并重画注解层, 不销毁重建、不重取数。
     * setData(resetScales 默认 true) 会重跑 y range 与全部 draw 钩子(注解层随之上新)。 */
    _qbChartRescale(scope) {
      const u = this._qbCharts && this._qbCharts[scope];
      if (!u || !u.root || !u.root.isConnected || !u.data) return;
      u.setData([u.data[0], u.data[1], u.data[2]]);
    },
    /* 窗口前后切换(快捷键落点, 见 shortcuts.js traffic-win-prev/next): 按 QB_WINDOW_NAMES
     * 声明序步进, 端点夹取(不环绕 —— 从"全部"跳到"1分"是惊扰); 无流量形态(qbCurScope 空)时
     * 零副作用。走 qbSetWindow 单点: 重拉重画 + 轮询重排 + 落盘三事一体。 */
    qbCycleWindow(delta) {
      const s = this.qbCurScope;
      if (!s) return;
      const cur = this[_QB_SCOPES[s].window];
      let i = QB_WINDOW_NAMES.indexOf(cur);
      if (i < 0) i = QB_WINDOW_NAMES.indexOf(QB_WINDOW_DEFAULT);
      const next = QB_WINDOW_NAMES[Math.max(0, Math.min(QB_WINDOW_NAMES.length - 1, i + delta))];
      if (next !== cur) this.qbSetWindow(next);
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
      // error **不在此清空**(2026-10-05 修「空态/错误态每隔一个轮询周期闪一次」): 请求前清错误 =
      // 续拉把错误文案换成一帧 loading/空态再换回, 与「清空旧数据把等待渲染成空态」同型; 错误态
      // 改由**下一次成功落袋**清除(见下), 期间的旧文案由 FX-29 遮罩在换目标时兜住(160ms 延迟点亮)。
      let stale = true;  // 保守初值: 只有确认未过期才落袋/清 loading(在途竞态纪律, 同 _drawerStale)
      try {
        const data = await this.api(def.url(ctx, this[def.window]));
        stale = def.stale(this, ctx);
        if (!stale) {
          this[def.data] = data;
          this[def.error] = "";  // 成功落袋才清错误态(见上: 在途期不动既有状态)
        }
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
        // 缺口斜纹底纹专用色(2026-10-08): --hairline 是 0.05~0.08 alpha 的发丝线令牌, 当底纹
        // 用几乎不可见(用户报障根因), 故单列一枚**高对比中性**令牌; 无该令牌的旧皮肤回退
        // --fg-muted 链条(仍比 hairline 可见), 绝不落回 grid 的极低 alpha。
        gap: pick("--qb-gap-hatch", "--border-strong", "--fg-muted"),
        axis: pick("--fg-dim", "--fg-muted"),
      };
    },
    /* ---------------- 画布注解层(限速虚线 + 缺口斜纹; 2026-10-08 用户拍板: 共享图面, 三挂点全生效) ----------------
     * uPlot 1.6.x 画布口径(读 vendor 源码确认): ctx **无 transform**, 坐标是**设备像素**
     * (u.bbox 已是设备像素; valToPos(v, scale) 默认回 CSS 像素且**相对绘图区**) —— 这里统一
     * ctx.scale(pxRatio) 转成 CSS 像素坐标系, 绝对坐标 = 绘图区左上(bbox/pxRatio) + valToPos
     * (相对值), 线宽/虚线/间距用 CSS 值。色值一律走建图时读到的令牌(tk, 与系列同源), 不硬编码
     * (换肤走整图重建, 新令牌随之生效)。 */
    _qbCanvasScale(u) {
      const px = (typeof uPlot !== "undefined" && uPlot.pxRatio) || 1;
      u.ctx.save();
      u.ctx.scale(px, px);
      return px;
    },
    /* 缺口斜纹(drawClear 钩子 = 画在系列**之下**): 采样缺口区间(null 桶游程)铺 45 度斜纹底纹,
     * 图面自解释(与图例「缺口 = 无采样」文案同义)。
     *
     * 【几何硬约束, 别改坏 —— 2026-10-08 二次修复】缺口必须被铺成**以缺口区间为左右边的竖矩形**
     * (x ∈ [xa, xb] 全高), 而不是"沿 45 度平移的一条斜带": 45 度线段的水平跨度恒为 H(图高), 若
     * 只按底端 x 扫 [xa-H, xb+H] 再让外层 clip 收到**整个绘图区**, 涂出来的并集是"宽 H 的斜向
     * 平行四边形"(左/右边界都是斜边) —— 缺口右段下半部留白、左段上半部越界到缺口左侧, 用户报
     * 「未落到正确的区域, 且其倾斜超出了范围」即此。**必须逐 run 追加一次 clip 到缺口矩形**
     * (ctx.rect(xa, T, xb-xa, H), 与绘图区 clip 求交), 斜纹才被裁成竖矩形。
     * 上一次修复(颜色令牌)只治了"看不清", 几何缺陷当时被误判为"颜色不可见导致无法判读落点"。 */
    _qbDrawGaps(u, tk) {
      const up = u.data && u.data[1];
      const dl = u.data && u.data[2];
      if (!up || !dl || !u.bbox || !u.ctx) return;
      const runs = _qbGapRuns(up, dl);
      if (!runs.length) return;
      const px = this._qbCanvasScale(u);
      const ctx = u.ctx;
      const L = u.bbox.left / px;
      const T = u.bbox.top / px;
      const W = u.bbox.width / px;
      const H = u.bbox.height / px;
      // 外层 clip = 绘图区(不越 y 轴/时间轴); 每个 run 再叠一层缺口矩形 clip(见上「几何硬约束」)。
      ctx.beginPath();
      ctx.rect(L, T, W, H);
      ctx.clip();
      // 斜纹色走**专用高对比令牌**(tk.gap), 不复用 tk.grid(--hairline 仅 0.05~0.08 alpha, 是
      // 装饰性 1px 发丝线令牌; 当缺口底纹用有效不透明度只剩约 3%, 深色底上几乎不可见 —— 用户
      // 2026-10-08 报「颜色几乎不可分辨」的根因)。令牌缺失回退 tk.grid 兜底不裸色。
      ctx.strokeStyle = tk.gap || tk.grid;
      ctx.globalAlpha = 1;
      ctx.lineWidth = 1;
      ctx.setLineDash([]);
      const step = 8;  // 斜纹间距(CSS px)
      for (const [a, b] of runs) {
        const xa = L + u.valToPos(u.data[0][a], "x");
        const xb = L + u.valToPos(u.data[0][b], "x");
        if (!(xb > xa)) continue;
        // 逐 run 裁到缺口矩形 [xa, xb] x [T, T+H]: 把 45 度斜带裁成竖矩形(缺口左右边界为**竖直边**)。
        ctx.save();
        ctx.beginPath();
        ctx.rect(xa, T, xb - xa, H);
        ctx.clip();
        // 扫线范围须覆盖整条缺口带: 每条线段右下角在 x、左上角在 (x-H, T); x 从 xa 起步(首条盖住
        // 缺口左上)到 xb+H(末条盖住缺口右下), 越出缺口矩形的部分由上一步 clip 收掉。
        for (let x = xa; x < xb + H; x += step) {
          ctx.beginPath();
          ctx.moveTo(x - H, T + H);
          ctx.lineTo(x, T);
          ctx.stroke();
        }
        ctx.restore();
      }
      ctx.restore();
    },
    /* 限速虚线(draw 钩子 = 画在系列**之上**): qB 全局限速上下行各一条水平虚线(色随方向, 与
     * 系列同色义)。只画**落在可视值域内**的限速 —— 自动模式下峰值未超限速时该线在顶沿之上
     * 不可见, 自然不画(用户拍板: 自动模式最大值超过限速才画); 固定模式下限速恒在顶沿之下,
     * 恒画。0(不限速)/null(未知)一律不画。 */
    _qbDrawLimits(u, tk) {
      const ymax = u.scales && u.scales.y && u.scales.y.max;
      if (!(ymax > 0) || !u.bbox || !u.ctx) return;
      const lim = this.speedLimitBytes || {};
      const lines = [];
      if (typeof lim.up === "number" && lim.up > 0 && lim.up < ymax) lines.push([lim.up, tk.up]);
      if (typeof lim.down === "number" && lim.down > 0 && lim.down < ymax) lines.push([lim.down, tk.down]);
      if (!lines.length) return;
      const px = this._qbCanvasScale(u);
      const ctx = u.ctx;
      const x0 = u.bbox.left / px;
      const x1 = (u.bbox.left + u.bbox.width) / px;
      ctx.setLineDash([5, 4]);
      ctx.lineWidth = 1;
      for (const [val, color] of lines) {
        const y = u.bbox.top / px + u.valToPos(val, "y");
        ctx.strokeStyle = color;
        ctx.beginPath();
        ctx.moveTo(x0, y);
        ctx.lineTo(x1, y);
        ctx.stroke();
      }
      ctx.restore();
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
        legend: { show: false },  // 图例由模板渲染(2026-10-08 版式改后并入统计栏 .hs-leg, 色义同源)
        cursor: { x: true, y: false, drag: { x: false, y: false } },  // 观察用途: 只留十字线, 不做框选缩放
        scales: {
          x: { time: true },
          // 速率从 0 起(口径: 无流量也是真值); 固定上限走 _qbYCapOf(0 = 不固定), 峰值超出固定
          // 上限时按峰值显示(上限只保底不裁剪, 见 _qbYRange)
          y: { range: (u, dmin, dmax) => _qbYRange(dmax, this._qbYCapOf(scope)) },
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
          // 注解层(共享图面, 三挂点全生效): drawClear = 系列之下(缺口斜纹), draw = 系列之上
          // (限速虚线)。tk 由本次建图捕获 —— 令牌换肤走整图重建, 钩子随新图换新 tk。
          drawClear: [(u) => this._qbDrawGaps(u, tk)],
          draw: [(u) => this._qbDrawLimits(u, tk)],
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
