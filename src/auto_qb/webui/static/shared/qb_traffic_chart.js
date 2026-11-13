/* auto-qb WEB UI · qB 口径流量图(uPlot 双系列组件, 三挂点)
 *
 * plan 26-10-03-0946 方案C §07 P5a/P5b。一个「双系列(上传/下载)时间曲线」封装, 三图(全局/单种/
 * 分组)共用: uPlot options 样板(axes/series/scales/cursor)收在 _qbChartBuild 单点, 调用方只给
 * points + 容器; null 桶 = 断线不连线(uPlot spanGaps:false, §5.2 拍板语义)。
 *
 * 约定与 dialogs.js / hr_status.js 同范式: 挂到 window.AQB_QB_TRAFFIC, 由 app.js 末尾
 * app.mixin(window.AQB_QB_TRAFFIC) 注入同一个 Vue 实例 —— 方法体里的 this 仍是那个组件实例。
 * !本文件在 HTML 里必须排在 app.js **之前**; data 字段在 state.js(根选项, 不进 app.mixin,
 *   见 frontend-split 纪律), uPlot vendor 由三主题 tpl-manifest scripts 登记(boot.js 依序放行)。
 *
 * 三挂点(2026-10-04 起全部并入底部详情抽屉, 以 _QB_SCOPES 作用域表为单一描述源): (1) global 全局
 * (/api/traffic/qb/global, 状态栏「qB 口径流量图」入口) (2) group 分组(/api/traffic/qb/group/{key},
 * 组右键菜单入口; key = 分组视图 g.key, 即 encode_group_key 通道, 前端不自行编码) (3) torrent 单种
 * (/api/traffic/qb/torrent/{hash}, 种子详情抽屉「流量」页签)。全局/分组走流量形态(drawerIsTraffic,
 * W6 起吃 drawer.js 的形态判据单点, scope 记挂点), 单种走种子形态(drawerIsSeed) + drawer.tab ===
 * "traffic"; 三者共用同一抽屉壳、
 * 同一拖拽高度(drawerHeightPx)与同一段正文块(drawer.html qbTrafficActive), 故建图落点统一
 * ref="qbChartHost"(同一时刻只渲染一个流量形态)。
 *
 * 低频轮询(§07 表「轮询/取数」列): 打开期间按采样间隔续拉 —— 间隔从最近响应 meta.interval_s
 * 取(raw 段窗(1m-24h)即采样间隔; agg 段窗(3d/7d/30d/6mo/1y/all) meta 是桶宽(3600s/86400s/
 * 标称月长)而非采样间隔, 夹取到配置校验上界 600s), 取不到回退 30s 常量; 页面隐藏跳过由轮询
 * 骨架(polling.js::startPoll)恒等守卫兜; 关闭/切走形态由 _stopDrawerPoll / _qbTeardown 显式
 * stopPoll —— 只挂打开期间, 不后台常驻。
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
 * 节拍内核(S1, plan 26-11-12-1139): 判定帧 = 续拉快路 setData 落袋时刻, 同帧起每拍 rAF 动画
 * —— L0 视口偏置左移(真窗口已落袋, 绘制视口先摆回旧位置再 ≤beat 归零交还 auto)+ L1 双轨数值
 * 收敛(两列独立插值尾部 1 点, 收敛帧写回真值)。纯函数(公式/时间线/状态机)在模块级「节奏内核」
 * 节, 调度器在 methods 域 _qbBeat*; 动画期 x 轴 ticks 冻结与 tooltip 真值接缝等判据见各处注。
 *
 * 视觉引擎 V + N 霓虹元素层(S2-a, plan §03 V 表/N 节/D1-D4): 同画布装饰面 —— V1 分级色相
 * (Lv 色表常量, 四皮肤无 --qb-lv* 令牌已核查)/V2 多边形扩张环 + 旋转菱形锚 + glitch 切片/
 * V3 三阶段多边形粒子(两轨合计 ≤32)+ 次区流动光点; N 层白名单五元素(Lv 色相, cfg.neon 独立
 * 开关), D3 双轨仲裁(both/lead/merge)与 D4 末点 y 间距缩小。图层顺序 I6 单点
 * _QB_FX_LAYER_ORDER, 背景零铺色(I11/G7), 曲线描边恒语义色一行不动(I10/D1); 纯函数(仲裁/
 * 预算/粒子运动/回落阈值)在模块级「视觉引擎」节, 绘制在 methods 域 _qbDrawFx/_qbDrawFxAnchor
 * (drawAxes/draw 钩子, 不新增 canvas), 装饰帧挂节拍调度器循环内(无独立循环)。
 *
 * 窗口档位单点(QB_WINDOW_NAMES)与「视图选择」持久化(2026-10-05, 用户拍板): 十三档清单、
 * 前后切换(qbCycleWindow)与落盘校验(qbInitialWindow)共用同一份常量 —— 展示面模板走
 * qbWindowNames computed, 不再各自硬编码。持久化粒度 = **全局单独一份 / 分组与种子共用一份**
 * (autoqb.ui.qbWinGlobal / autoqb.ui.qbWinShared, 键单点 qbWinStoreKey): 全局图与单对象图
 * 观察尺度习惯不同, 而组与种子常被当作同类"单对象"视图对照着看。初值读取 qbInitialWindow
 * 定义在本文件(全部皮肤(atlas/prism/console/flux)的 tpl-manifest 里本文件均排在 state.js 之前),
 * 由 state.js 的 data() 调用 —— 档位域归流量图模块所有。落盘纪律与 persistDrawerTab 同款:
 * 只落"选了哪档"这个用户意图, 写失败吞异常(刷新后回落默认), 不打断换窗。
 * 快捷键三入口(shortcuts.js): 打开全局图 Ctrl+Backslash / 详情面板流量页签 Alt+5(无条件,
 * 功能未启用时提示后忽略) / 窗口前后切换 [ ](两条走 when 条件绑定, 仅流量形态可见时消费)。
 *
 * 纵轴固定模式 + 画布注解层(2026-10-08, 用户拍板; 三挂点通用, issue 26-10-07-0149 认领一并做):
 * 纵轴三态 auto(默认, 随数据峰值) / limit(全局限速 ×1.2) / manual(手动 MiB/s)。限速一律取
 * **qB 全局限速上下载较大者**(三作用域同源); 峰值超出固定上限时**按峰值显示**(上限只保底,
 * 不裁剪数据 —— _qbYRange)。偏好**三作用域各自独立**落 localStorage(qbYAxisStoreKey)。
 * 注解层走 uPlot draw/drawClear 钩子画在**同一张画布**上(共享图面, 三挂点 + 经典/所有变体
 * 全生效): 限速虚线(上下载各一条, 只画落在可视值域内的限速 —— 自动模式下峰值未超限速时线在
 * 顶沿之上, 自然不画)+ 缺口斜纹(null 桶游程铺 45 度斜纹, 画在系列之下)。
 * !2026-10-08 修「缺口斜纹几乎不可分辨」: 斜纹原走 tk.grid(--hairline, alpha 仅 0.05~0.08 的
 * 装饰性 1px 发丝线令牌), 再叠 globalAlpha 0.5 => 有效不透明度约 3%, 深色底上等于没画(亮主题
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
 * 定义在本文件(全部皮肤的 tpl-manifest 里本文件均排在 state.js 之前)由 state.js 的 data() 调用;
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
 * / "manual" 手动 MiB/s。限速一律取 **qB 全局限速**(三作用域同源, 用户拍板), 方向取上下载
 * 限速的**较大者** —— 纵轴上下载共用一条, 取大者两条曲线都落在固定上限内。峰值超出固定上限
 * 时**按峰值显示**(上限只保底, 不裁剪数据; 见 _qbYRange)。 */
const QB_YAXIS_MODES = ["auto", "limit", "manual"];
const QB_YAXIS_DEFAULT = "auto";
/* 纵轴三态的按钮文案(26-10-20-2231 R23-B-17): 此前只活在模板里(硬编码三个 <button>), 与上面的
 * 合法值清单 QB_YAXIS_MODES 隔了一层 —— 改一档名时两处都对不上号。现在文案挂在模式清单旁边,
 * 清单仍是唯一的合法值来源(label 缺失即回落到模式名本身, 不会静默渲出空钮)。 */
const QB_YAXIS_LABELS = { auto: "自动", limit: "限速+20%", manual: "手动" };
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

/* ---------------- 动效参数持久化三件套(R8, plan 26-11-12-1139 §05.5) ----------------
 * 键 autoqb.ui.qbFx(与 qbWin/qbYAxis 同族 autoqb.ui.* 前缀); 四皮肤共用一份、不分 scope ——
 * 动效是个人观感偏好, 分三份会让用户遇到"为什么换个图动效不一样"(§05.5 拍板), 也不进
 * config.qb_traffic(不写后端、不动 KNOWN_QB_TRAFFIC_KEYS/fail-fast 校验/迁移)。本模块 =
 * 唯一属主: 默认值(QB_FX_DEFAULTS) + 枚举白名单(QB_FX_ENUMS) + 初值读取(qbInitialFx, 由
 * state.js 的 data() 调用 —— 清单装载序里本文件排在 state.js 之前) + 落盘(persistQbFx, 方法域)
 * 都在这里; state.js 只显式建 fx / fxPanel 字段(watch.fx 把整对象 JSON 克隆进 window.AQB_FX_CFG,
 * 绘制热路径只读普通对象, 不逐帧读 Vue —— §05.3)。
 * !localStorage 访问只在函数体内(本文件会被 node 探针 eval, 顶层不得碰 DOM/BOM —— 同
 *   qbInitialWindow/qbInitialYAxis 纪律, 见文件头注)。
 * 量纲(§05.3 量纲统一): impact / particles / shiftRatio **显示 0-100、存储 0-1**, 换算单点在
 *   面板处理器 fxRange(/100)与 fxPct(*100), 存储面与持久化 JSON 恒见 0-1。 */
const QB_FX_STORE_KEY = "autoqb.ui.qbFx";
/* 默认值(唯一来源; 字段名与默认值和计划 §05.5 JSON 逐字一致): 15 个可调项(impact/ease/
 * palette/particles/neon/tail/shift/shiftRatio/dual/tear/echoSpan + layers.band/particles/
 * scan/grade) + 1 个总开关(enabled) + 版本号 v。复制配置片段(fxCopy)输出同形状。 */
const QB_FX_DEFAULTS = {
  v: 1,
  enabled: true,
  impact: 0.7, ease: "out",
  palette: "neon", particles: 0.7, neon: true, tail: true,
  shift: "smooth", shiftRatio: 0.6,
  dual: "both", tear: "linked", echoSpan: "auto",
  layers: { band: true, particles: true, scan: true, grade: true },
};
/* 枚举白名单(读校验用; select 面板候选拿同一份防止两处漂移)。echoSpan 的 "full" 是 R5 整幅
 * 旧观感对照档(NOT FOR SHIP) —— 白名单放行存储面, 观感降格语义在 S2 动效引擎里区分。 */
const QB_FX_ENUMS = {
  ease: ["out", "linear"],
  palette: ["neon", "calm", "glitch"],
  shift: ["smooth", "instant"],
  dual: ["both", "lead", "merge"],
  tear: ["linked", "random", "fixed"],
  echoSpan: ["auto", "100", "150", "200", "full"],
};
/* 面板盒常量(§05.1): 宽 320 固定、不可拖拽 resize; 开层初值的高度估算(高级折叠态实测约 500),
 * 精确收口在 fxPanel watcher 的 $nextTick 实测重钳位(_qbFxRefit)。 */
const QB_FX_PANEL_W = 320;
const QB_FX_PANEL_H_EST = 500;
/* 深克隆成**普通**对象(JSON 往返): 默认值下发与 watch.fx -> AQB_FX_CFG 同步共用同一手法 ——
 * 斩断 Vue 响应式代理, 热路径读普通字段不再触发依赖追踪。 */
function _qbFxClone(v) {
  return JSON.parse(JSON.stringify(v));
}
/* 逐字段白名单校验(§05.5 读纪律): 数值 clamp 到存储量纲 / 枚举白名单 / 布尔严格 === true|false;
 * 未知键静默丢弃(现建新对象, 旧版本键里残留的已删字段如 scene/amp/tpl 自然清场)。入参假定
 * 已是对象且 v === 1(qbInitialFx 先行把关)。
 * !数值只认真数字与数字串("0.9" 可抢救) —— null/布尔/对象/空串一律回落默认: Number(null) === 0,
 *   直收会把「没给值」误读成「最小动效」(缺省即默认, §05.5 aside)。 */
function _qbFxSanitize(v) {
  const d = QB_FX_DEFAULTS;
  const num = (raw, lo, hi, def) => {
    if (raw === null || raw === undefined || typeof raw === "boolean" || raw === ""
      || typeof raw === "object") return def;
    const n = Number(raw);
    return Number.isFinite(n) ? Math.min(hi, Math.max(lo, n)) : def;
  };
  const enu = (raw, key) => (QB_FX_ENUMS[key].indexOf(raw) >= 0 ? raw : d[key]);
  const bl = (raw, def) => (raw === true || raw === false ? raw : def);
  const ls = v.layers && typeof v.layers === "object" && !Array.isArray(v.layers) ? v.layers : {};
  return {
    v: 1,
    enabled: bl(v.enabled, d.enabled),
    impact: num(v.impact, 0, 1, d.impact),
    ease: enu(v.ease, "ease"),
    palette: enu(v.palette, "palette"),
    particles: num(v.particles, 0, 1, d.particles),
    neon: bl(v.neon, d.neon),
    tail: bl(v.tail, d.tail),
    shift: enu(v.shift, "shift"),
    shiftRatio: num(v.shiftRatio, 0.2, 1, d.shiftRatio),
    dual: enu(v.dual, "dual"),
    tear: enu(v.tear, "tear"),
    echoSpan: enu(v.echoSpan, "echoSpan"),
    layers: {
      band: bl(ls.band, d.layers.band),
      particles: bl(ls.particles, d.layers.particles),
      scan: bl(ls.scan, d.layers.scan),
      grade: bl(ls.grade, d.layers.grade),
    },
  };
}
/* 动效参数初值(持久化偏好; 与 qbInitialWindow 同纪律: 坏值/无存储回落默认且**不清键** ——
 * §05.5: JSON.parse 失败/非对象/v !== 1 整体回落默认, 保留原始串供诊断)。定义在本文件由
 * state.js 的 data() 调用。 */
function qbInitialFx() {
  try {
    const raw = localStorage.getItem(QB_FX_STORE_KEY);
    if (raw) {
      const v = JSON.parse(raw);
      if (v && typeof v === "object" && !Array.isArray(v) && v.v === 1) return _qbFxSanitize(v);
    }
  } catch (e) {
    /* 无存储/坏 JSON: 回落默认(偏好类读取失败不该影响启动), 不清键 */
  }
  return _qbFxClone(QB_FX_DEFAULTS);
}

/* reduced-motion 判定(R8, plan 26-11-12-1139 §05.6): 判定单点在本模块 —— 内联 matchMedia,
 * **不引用共享 fx 域的 reduced 助手**(window.AQB_FX 只在 flux 皮肤挂载, shared/fx/fx.js:189;
 * 三套旧皮肤页面上引用即 ReferenceError, 而 test_frontend_fx_wiring 只查 shell 的 link/script
 * 照绿不报 —— 自觉约束, 守阵钉住本文件零该引用)。
 * 返回值进 state.js 的 fxReduce 字段(响应式, 面板置灰/说明行/AQB_FX_CFG.on 消费面都吃它),
 * 运行期变化由 mounted 里的 matchMedia change 监听跟随。函数体内取 BOM(node 探针 eval 本文件,
 * 顶层不得碰 —— 同 qbInitialWindow 纪律); 无 matchMedia(node/旧环境)回落 false。 */
function qbInitialFxReduce() {
  try {
    return !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  } catch (e) {
    return false;
  }
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
    active: (t) => t.drawerIsTraffic && t.drawer.open && t.page === "groups"
      && t.drawer.scope === "global",
    stale: (t) => !(t.drawerIsTraffic && t.drawer.open && t.drawer.scope === "global"),
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
    active: (t) => !!(t.drawerIsSeed && t.drawer.open && t.drawer.tab === "traffic"
      && t.page === "groups"),
    // !stale 才是「可落袋」: 谓词 = **否定式**(响应此刻已不属于本图 = 丢弃)。W2–W6 机械改名
    // 时这里被写成 `!!(...)`(把取反写成双重取反), 语义整个翻转 —— 恰在本图活跃时判「过期」,
    // 数据永不落袋、loading 卡死不清 -> 种子流量页签恒停在「正在加载流量数据…」(2026-10-12 修)。
    stale: (t, h) => !(t.qbTrafficOn && t.drawerIsSeed && t.drawer.open
      && t.drawer.tab === "traffic" && t.drawer.hash === h),
  },
  group: {
    host: "qbChartHost",
    window: "qbGroupWindow", data: "qbGroupData", loading: "qbGroupLoading", error: "qbGroupError",
    hoverIdx: "qbGroupHoverIdx", hoverLeft: "qbGroupHoverLeft", yaxis: "qbGroupYAxis",
    // key = 分组视图 g.key(服务端 encode_group_key 产物, base64url 天然 URL 安全),
    // 与 delete_flow/commands 的 /api/groups/${k} 同款原样内插 —— 前端不自行编码(§07 表(3))
    url: (k, w) => "/api/traffic/qb/group/" + k + "?window=" + w,
    ctx: (t) => t.qbGroupKey,
    // page 守卫与 global 同(drawerVisible 单点): 非主内容页面板不在 DOM, 不拉不画
    active: (t) => t.drawerIsTraffic && t.drawer.open && t.page === "groups"
      && t.drawer.scope === "group",
    // 同 torrent: 谓词是否定式, 同一波改名里一并被写成 `!!(...)`(同一处缺陷, 一并修复)
    stale: (t, k) => !(t.qbTrafficOn && t.drawerIsTraffic && t.drawer.open
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
 * 判据 = **上下载皆 null**(后端整桶 null 时两列同 null; 单列 null 防御性不误判成缺口)。 */
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

/* 数据链边界: 首/末个非空桶下标(全系列无观测 -> [-1, -1]) —— 「数据链」= 本帧实际
 * 有观测的那段连续区间。
 * !这条边界**只认本次取到的 points**, 不用种子 added_on 推算: added_on 是「最近一次
 *   被加进 qB」的时刻(跳检即删同 hash 再重加 —— core/modules/ops_mod.py 的 delete ->
 *   add, hr/resolve.py 据 added_on 变化识别该语义), 而流量按 infohash 长期留存
 *   (core/traffic_store.py, 删种不清理、只按龄淘汰)。拿 added_on 切一刀会把早于最新
 *   added_on 的那段**真实历史数据**误判成「尚未添加」—— 与本轮要修的失真同型反向。
 * hover 侧经 _qbPointsColumns 转成同形状两列再过本函数, 与画布侧同判据。 */
function _qbChainBounds(up, dl) {
  const n = Math.min(up.length, dl.length);
  let first = -1;
  let last = -1;
  for (let k = 0; k < n; k++) {
    if (up[k] != null || dl[k] != null) {
      if (first < 0) first = k;
      last = k;
    }
  }
  return [first, last];
}
/* 缺口桶所在区段(纯函数供 node 单测):
 *   "outside" = 数据链之外(链首之前 / 链尾之后 / 全系列无观测) —— 系统只知道这段时间没有
 *               该对象的采样, **不知道为什么**, 故文案只陈述事实、不替用户归因;
 *   "mid"     = 数据链中间的洞(前后都有观测) —— 只有这一段谈得上「中断」, 且它是可观测
 *               事实而非推断。
 * first = -1(全空)时 i > last 恒真 -> 一律 outside, 无需额外分支。
 * !2026-10-30 前的实现不分区段: 所有 null 桶一律出「程序未运行或 qB 断联」式的归因文案
 *   (plan 26-10-04-0721 §05 首版合并文案) —— 刚添加不久的种子, 图左侧那一整段历史空白
 *   因此全被断言成断联, 即用户报障「不符合实际情况」的口径。 */
function _qbGapZone(i, first, last) {
  return i < first || i > last ? "outside" : "mid";
}
/* points([{t, up, dl} | null]) -> 画布同形状的两列([up], [dl]); hover 侧因此能直接复用
 * _qbChainBounds/_qbGapZone(与 _qbDrawGaps 直读 u.data[1]/u.data[2] 同判据)。 */
function _qbPointsColumns(points) {
  const up = [];
  const dl = [];
  for (let k = 0; k < points.length; k++) {
    const p = points[k];
    up.push(p ? p.up : null);
    dl.push(p ? p.dl : null);
  }
  return [up, dl];
}

/* 重启缝提示判据(plan 26-10-15-0829 P4, 模块级纯函数供 node 单测; 左端口径修订 26-10-16,
 * issue 26-10-16-0954): 「数据链末点早于右沿且重启贴近链末」 -> 返回 { startedAt }, 否则 null。
 * - 数据链末点 = 最后一个非 null 桶; 尾部未观测区存在 <=> 末非 null 下标 < n-1(链已到
 *   右沿 = 无尾区, 不提示 —— 正常尾桶观测/当前桶未采完都不是缝);
 * - 重启贴近链末 <=> meta.server_started_at(后端进程出生时刻, traffic_qb._SERVER_STARTED_AT)
 *   ∈ [链末桶前一桶起点 t-interval, 右沿] 内(左端含)。原口径左端 = 链末桶覆盖端 t+interval,
 *   其隐含前提「链末桶晚于重启时刻 => 链已接续、无误读面」在「重启后首采已入账、随后立即
 *   进入开放零游程」形态下不成立(实测帧: 重启 04:45:01 -> 首采桶 04:45:02, 04:45:04 起整片
 *   斜纹到右沿却零提示): 首采(恒落在重启后 <= 一个 main_tick)总归进链末桶, 但尾区仍在 ——
 *   「链在重启处断」与「重启后首采桶即链末」在桶粒度上不可分, 左端须放宽一桶宽; 反方向
 *   链末桶起点晚于重启 + 1 个桶宽以上 = 链确已接续, 不提示。重启晚于右沿不可能(右沿 = 响应
 *   构建时刻, 防御);
 * - meta 无新键(旧后端)/全 null/interval 非法 -> null(不猜, 向后兼容: 旧前端忽略新键,
 *   新前端遇旧后端也不提示)。all 月视图非等距, 端点用标称月长近似 —— 但月视图
 *   末桶(当前月)由活尾 pending 行常态覆盖(last == n-1), 实际不达判据面。 */
function _qbSeamHint(points, interval, meta) {
  if (!meta || !(Number(meta.server_started_at) > 0) || !(interval > 0)) return null;
  const n = points.length;
  let last = -1;
  for (let i = n - 1; i >= 0; i--) {
    if (points[i]) {
      last = i;
      break;
    }
  }
  if (last < 0 || last >= n - 1) return null;  // 全 null(空态面)/链已到右沿: 无尾部未观测区
  const started = Number(meta.server_started_at);
  const chainPrevStart = points[last].t - interval;  // 链末桶前一桶起点 = 判据左端(重启与链末不可分带下界)
  const rightEdge = points[last].t + (n - last) * interval;  // 末桶覆盖端 = 右沿(等距栅格)
  if (started < chainPrevStart || started > rightEdge) return null;
  return { startedAt: started };
}

/* 限速事件 -> 绘图段(plan 26-10-12-0535 D4, 模块级纯函数供 node 单测)。
 * events = [[ts, up, down], ...] 升序(后端装配产物, 首元素可为窗口起点的合成事件);
 * 段 = 相邻事件对的时间区间, 末段延伸到 tEnd(图数据右沿 = 当前时刻) —— 限速是阶梯函数,
 * 每段画在各自时间区间内。返回 [{t0, t1, up, down}, ...]。 */
function _qbLimitSegs(events, tEnd) {
  if (!events || !events.length || !(tEnd > 0)) return [];
  const segs = [];
  for (let i = 0; i < events.length; i++) {
    const ts = events[i][0];
    const next = i + 1 < events.length ? events[i + 1][0] : tEnd;
    if (!(next > ts)) continue;  // 退化段(事件晚于图右沿等)不画
    segs.push({ t0: ts, t1: next, up: events[i][1], down: events[i][2] });
  }
  return segs;
}

/* 悬停时刻的生效限速(D7, 模块级纯函数供 node 单测): events 升序, 二分取 <= ts 的
 * 最近事件值; 记录起点晚于悬停时刻(无 <= ts 事件)返回 null —— 「当时值未知」不猜。 */
function _qbLimitAt(events, ts) {
  if (!events || !events.length) return null;
  let lo = 0;
  let hi = events.length - 1;
  let ans = -1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (events[mid][0] <= ts) {
      ans = mid;
      lo = mid + 1;
    } else {
      hi = mid - 1;
    }
  }
  return ans >= 0 ? [events[ans][1], events[ans][2]] : null;
}

/* ---------------- 节奏内核(S1, plan 26-11-12-1139 §03 节奏模型 / L0 / L1) ----------------
 * 本节全部是模块级纯函数(node 电池探针直接真跑, 同 _qbPointsToData 先例); 带副作用的调度器
 * (_qbBeatStart/_qbBeatFrame/_qbBeatConverge/_qbBeatCancel)在 methods 域。运行期状态本体存
 * 图记录(u._qbBeat = 拍时钟/视口偏置/双轨 tracks/ticks 冻结缓存), 不进 Vue state —— 同
 * u._qbLimits 款。 */
/* 节奏公式单点(I1/I2): beat = clamp(period × 0.4, 320, 1000) —— 「真值在 t ≤ beat ≤ 1s 完全
 * 落地」的可验证保证。period = clamp(_qbPollMs() 实算, 1500, 600000) 每拍重算(_qbPollMs 已
 * 夹取 [1.5s, 600s], 调用方直传)。面板状态行 beat 展示值 computed 复用本单点(2026-11-13 起消掉
 * 第二份公式; 注: 该 computed 名不得带括号出现在本文件, 见 test_frontend_qb_traffic_window_
 * persist_and_single_source 的恰 1 次钉)。 */
const _QB_FX_BEAT_MIN_MS = 320;
const _QB_FX_BEAT_MAX_MS = 1000;
const _QB_FX_BEAT_RATIO = 0.4;
function _qbBeatMs(period) {
  const p = Number(period);
  if (!(p > 0)) return _QB_FX_BEAT_MIN_MS;
  return Math.min(_QB_FX_BEAT_MAX_MS, Math.max(_QB_FX_BEAT_MIN_MS, p * _QB_FX_BEAT_RATIO));
}
/* 段内时间线常量单点(§03 节奏公式代码块逐字语义; S1 只消费 impact/左移/收敛三段, 余辉与次区
 * tail 是 S2 装饰面的预算, 常量一并在此单点) */
const _QB_FX_IMPACT_RATIO = 0.12;   /* impact = 0 .. 0.12 × beat */
const _QB_FX_CONV_END_RATIO = 0.60; /* converge 收敛窗 = 0.12 × beat .. 0.60 × beat */
const _QB_FX_TAIL_MAX_MS = 2000;    /* tail = min(period − beat, 2000): 长窗 600s 也只铺 2s(P5) */
/* 每拍时间线(纯函数, 供 node 电池): period 每拍重算(I2); shiftRatio 读面板存储值(校验域
 * [0.2,1], 此处再防御夹取一次), 缺省回落 QB_FX_DEFAULTS.shiftRatio。 */
function _qbBeatTimeline(period, shiftRatio) {
  const beat = _qbBeatMs(period);
  const r = Number(shiftRatio);
  const ratio = Number.isFinite(r) ? Math.min(1, Math.max(0.2, r)) : QB_FX_DEFAULTS.shiftRatio;
  const impact = beat * _QB_FX_IMPACT_RATIO;
  const convEnd = beat * _QB_FX_CONV_END_RATIO;
  const pr = Number(period);
  return {
    period: Number.isFinite(pr) && pr > 0 ? Math.min(_QB_POLL_MAX_MS, Math.max(_QB_POLL_MIN_MS, pr)) : _QB_POLL_FALLBACK_MS,
    beat,
    impactMs: impact,
    shiftMs: ratio * beat,
    convergeMs: convEnd - impact,
    animEndMs: Math.max(ratio * beat, convEnd),
    tailMs: beat < pr ? Math.min(pr - beat, _QB_FX_TAIL_MAX_MS) : 0,
  };
}
/* ease-out 单点(D9: --ease-out 禁 spring —— 三次多项式, 严格单调递增且无 overshoot, 值域
 * 恒 [0,1]): p ∈ [0,1] 越界夹取。 */
function _qbFxEaseOut(p) {
  const q = p <= 0 ? 0 : p >= 1 ? 1 : p;
  const r = 1 - q;
  return 1 - r * r * r;
}
/* L0 最小可见位移规则: 单格像素 = 绘图宽(CSS px) / 点数, < 0.75px 的位移肉眼不可辨 —— 该拍
 * 直接瞬时落地(等同 instant), 只短窗播放 L0 过渡(24h 长窗 2880 点 × ~800px ≈ 0.28px/格恒瞬时,
 * 省掉每帧全量路径重建的帧成本, 见 §09「逐帧性能」与 I9 R8 复核)。量不到绘图宽(首绘前)按 0
 * 处理 = 瞬时, 宁可不动画不可错动画。 */
const _QB_FX_CELL_MIN_PX = 0.75;
/* 拍内单帧 dt 上限(ms): 掉帧/长停顿吞进一帧不跳变过半拍(隐藏暂停另有 document.hidden 判定,
 * 时钟在隐藏期根本不累计 —— 见 _qbBeatFrame)。 */
const _QB_FX_FRAME_MAX_DT_MS = 100;
function _qbFxCellPx(plotCssWidth, nPoints) {
  return nPoints > 0 && plotCssWidth > 0 ? plotCssWidth / nPoints : 0;
}
function _qbFxShouldShift(cellPx) {
  return cellPx >= _QB_FX_CELL_MIN_PX;
}
/* L1 双轨状态机(R3, §03 L1 底座; 纯函数面供 node 电池)。每轨 {prev, target, shown, delta,
 * level, live}, 两轨独立推进(D2), 状态本体存 u._qbBeat.tracks:
 *   prev   = 上拍显示值(shown 接续, 禁止回跳 —— I3); 上拍轨死(shown null)即复活, 无从接续
 *            直落真值(不造斜坡 —— 从 0 缓升是撒谎)
 *   target = 本拍尾桶真值; null = 缺口 -> live=false, 轨静默不插值(D4)
 *   shown  = 当前显示值(动画期按 easeOut 向 target 收敛; 收敛帧 = target)
 *   delta  = |target − prev| / max(prev, 可视下限) —— 可视下限由调用方按 y 轴可视尺度传入
 *            (floor = y 轴顶值 × _QB_FX_VIS_FLOOR_RATIO), 防 prev≈0 时相对变化爆炸
 *   level  = Δ 分档: <0.5% 静默(0) / <5% Lv.1 / <30% Lv.2 / 其余 Lv.3(阈值常量单点可调);
 *            live=false 或 Δ≈0 一律 0(D2: 零变化静默指零反馈, 左移与数值收敛照常执行) */
const _QB_FX_DELTA_SILENT = 0.005;
const _QB_FX_LEVEL1_DELTA = 0.05;
const _QB_FX_LEVEL2_DELTA = 0.30;
/* 可视下限占 y 轴可视顶值的比例(S1 状态机无装饰消费面, 数值 S2 联调时可调) */
const _QB_FX_VIS_FLOOR_RATIO = 0.02;
function _qbFxLevel(delta, live) {
  if (!live || !(delta >= _QB_FX_DELTA_SILENT)) return 0;
  if (delta < _QB_FX_LEVEL1_DELTA) return 1;
  if (delta < _QB_FX_LEVEL2_DELTA) return 2;
  return 3;
}
function _qbFxTrackNext(prevTrack, target, floor) {
  if (target == null) {
    return { prev: null, target: null, shown: null, delta: 0, level: 0, live: false };
  }
  const prevShown = prevTrack && prevTrack.shown != null ? prevTrack.shown : target;
  const denom = Math.max(prevShown, floor);
  const delta = denom > 0 ? Math.abs(target - prevShown) / denom : 0;
  return {
    prev: prevShown,
    target,
    shown: prevShown,
    delta,
    level: _qbFxLevel(delta, true),
    live: true,
  };
}
/* 收敛插值(纯函数): prev -> target 按 easeOut(p), 恒落在 [min(prev,target), max(prev,target)]
 * 内, 单调无 overshoot(I4/D9)。 */
function _qbFxShown(track, p) {
  return track.prev + (track.target - track.prev) * _qbFxEaseOut(p);
}

/* ---------------- 视觉引擎 V + N 霓虹元素层(S2-a, plan 26-11-12-1139 §03 V 表/N 节/D1-D4) ----------------
 * 本节是装饰面的常量与模块级纯函数单点(node 电池直接真跑, 同节奏内核先例); 带副作用的绘制面在
 * methods 域: _qbDrawFx(drawAxes 钩子 = uPlot 网格之后、系列原生之前: 几何环/粒子/切片 →
 * N 霓虹元素层)与 _qbDrawFxAnchor(draw 钩子 = 系列之上: 末点菱形锚 + lead 策略从属轨描边加亮),
 * 装饰帧挂在节拍调度器的 rAF 循环内(无独立循环 —— 调度器每帧提交即重跑钩子, L0/L1 提交帧顺路
 * 带出装饰)。
 * 生效条件(I7/§05.6): cfg.on === true(有效值单点 = enabled && !reduce)且该轨 level ≥ 1 ——
 * Δ≈0/零流量/缺口轨零装饰但 L0/L1 照常(D2/I10); N 层独立开关 cfg.neon(I11), 粒子层
 * cfg.layers.particles, 次区光点 cfg.tail, 三策略 cfg.dual, 密度 cfg.particles, 配色 cfg.palette。 */

/* I6 图层顺序常量(违反即判失败; 单点描述, 绘制落位已读 vendor 1.6.32 源实证: 主渲染序
 * clearRect → drawClear → axes(网格) → drawAxes → series → draw, 其中 Ci("drawAxes") 在
 * Dl.axes 末尾 = 网格之后、系列之前): bg = 零铺色恒由 CSS 提供, grid/判定线 = uPlot 网格 +
 * _qbDrawGaps 缺口斜纹(drawClear 段), geometry/neon = _qbDrawFx(drawAxes 段 = 网格后系列前),
 * curve = uPlot 系列原生(画在 drawAxes 之后 = 装饰永不压曲线, 语义色一行不动), anchor =
 * _qbDrawFxAnchor(draw 段), hud = DOM tooltip/图例(本引擎零触碰)) */
const _QB_FX_LAYER_ORDER = ["bg", "grid", "geometry", "neon", "curve", "anchor", "hud"];

/* I11 N 层白名单(可着 Lv 色的局部元素)/黑名单(恒与静态基线逐像素一致, 本引擎零触碰 ——
 * 曲线描边恒 --today-up/down 由 _qbChartTokens 现读; 背景/网格/tooltip/图例/限速虚线不染) */
const _QB_FX_N_WHITELIST = ["judgeFlash", "ringOuter", "partOuter", "anchorHalo", "lvBadge"];
const _QB_FX_N_BLACKLIST = ["curveUp", "curveDl", "plotBg", "edgeBg", "grid", "tooltip", "legend", "limitDash"];

/* V1 Lv 色表(plan §03 V1 色彩行逐字: Lv.1 蓝 #7AD9FF / Lv.2 金 #FEFFA9 / Lv.3 品红 #FF6BD6,
 * 沿用 Phigros AP 金 / FC 蓝)。!四皮肤均无 --qb-lv* 令牌(落表前已核查 atlas/prism/console/
 * flux 全部样式面), canvas 热路径也不逐帧 getComputedStyle —— 故按计划色值常量落 shared 层
 * (来源 = plan §03 V 表 V1 行); 色相语义是「这一拍多强」的分级反馈色, 不属皮肤语义色面,
 * 换肤不变; 绝不替代曲线语义色(I10/D1)。 */
const _QB_FX_LV_COLORS = { 1: "#7AD9FF", 2: "#FEFFA9", 3: "#FF6BD6" };

/* V1 三档配色 shadowBlur 上限(I9): glitch 14 / neon(常规) 10 / calm 0。同帧辉光(blur)描边
 * 另有 ≤3 次预算: 本引擎只把 blur 施于扩张环外圈(至多 2 次), 锚辉光用无 blur 低透明外圈菱形
 * 替代(白名单 anchorHalo), 粒子外圈/判定线短亮段恒纯描边。 */
const _QB_FX_BLUR_CAPS = { neon: 10, glitch: 14, calm: 0 };

/* V2 冲击环边数映射(由 lead 等级决定): Lv.1 三边 / Lv.2 六边 / Lv.3 八边 */
const _QB_FX_RING_SIDES = { 1: 3, 2: 6, 3: 8 };

/* I9 视觉预算常量(R3: 全部按 up + dl 两轨合计, 不每轨各配一套): 粒子 ≤32 / 每轨半套 ≤16 /
 * N 层 ≤0.33×beat 回落 / 粒子活跃窗 ≤0.55×beat / 末点 y 间距 <26px 反馈按比例缩小(下限
 * 0.4 —— 不合并不取消, D4) / glitch 切片 ≤5 条(R6)且微震 ≤5px(实际 ±3px) / 次区光点每轨 ≤2
 * (合计 ≤4)沿末段 6 桶缓动 */
const _QB_FX_PART_MAX = 32;
const _QB_FX_SHARD_MAX = 16;
const _QB_FX_NEON_RATIO = 0.33;
const _QB_FX_PART_RATIO = 0.55;
const _QB_FX_Y_GAP_PX = 26;
const _QB_FX_Y_GAP_MIN_SCALE = 0.4;
const _QB_FX_SLICES_MAX = 5;
const _QB_FX_SLICE_SHAKE_PX = 3;
const _QB_FX_TAIL_PTS_MAX = 2;
const _QB_FX_TAIL_SPAN_BUCKETS = 6;

/* 确定性伪随机(线性同余; 数值域: int32 种子 × 1664525 < 2^53 无精度丢失) —— 粒子/切片清单
 * 同拍重绘恒同形(不闪变), 跨拍随尾桶时刻自然变化 */
function _qbFxRand(seed) {
  let s = (seed | 0) || 1;
  return () => {
    s = (s * 1664525 + 1013904223) | 0;
    return ((s >>> 8) & 0xffffff) / 0x1000000;
  };
}

/* 多边形路径(V2/V3 共用; stroke/fill 由调用方定 —— 1px 级 stroke 与小多边形 fill, 零整块铺底) */
function _qbFxPolyPath(ctx, x, y, r, sides, rot) {
  if (!(r > 0) || !(sides >= 3)) return;
  ctx.beginPath();
  for (let i = 0; i < sides; i++) {
    const ang = rot + (Math.PI * 2 * i) / sides;
    const px2 = x + Math.cos(ang) * r;
    const py2 = y + Math.sin(ang) * r;
    if (i === 0) ctx.moveTo(px2, py2);
    else ctx.lineTo(px2, py2);
  }
  ctx.closePath();
}

/* D3 主导轨仲裁: lead = argmax(delta_up, delta_dl), 优先非缺口(live)且非静默(level>0)轨;
 * 双轨皆缺口/静默 -> null(零装饰, L0/L1 照常 —— D2/I10); 恰等时取 up(稳定序)。 */
function _qbFxLead(up, dl) {
  const a = up && up.live && up.level > 0 ? up.delta : -1;
  const b = dl && dl.live && dl.level > 0 ? dl.delta : -1;
  if (a < 0 && b < 0) return null;
  return b > a ? "dl" : "up";
}

/* partCap(lead 等级 + 密度参数 cfg.particles): 两轨合计上限 = min(32, round(基数 × density)),
 * 基数按等级 16/24/32(Lv.1/Lv.2/Lv.3); density ≤ 0 或非法 = 0 粒子(密度关到底即无粒子)。 */
function _qbFxPartCap(level, particles) {
  const d = Number(particles);
  if (!(level >= 1) || !Number.isFinite(d) || d <= 0) return 0;
  const base = level >= 3 ? 32 : level === 2 ? 24 : 16;
  return Math.min(_QB_FX_PART_MAX, Math.round(base * Math.min(1, d)));
}

/* D3 三策略粒子分配(both 各轨 ≤16; lead 单轨全套 ≤32; 合计恒 ≤32): both = 双轨各发半套
 * (默认) / lead = 主导轨全套从属轨零粒子(只描边加亮 + 小锚点) / merge = 两轨 y 中点一次
 * (色取 lead Lv 色 —— D3-c)。未知策略回落 both(保守默认 —— D3-b)。 */
function _qbFxAlloc(strategy, cap, lead) {
  if (!(cap > 0)) return { up: 0, dl: 0, merge: 0 };
  if (strategy === "merge") return { up: 0, dl: 0, merge: cap };
  if (strategy === "lead") {
    return lead === "dl" ? { up: 0, dl: cap, merge: 0 } : { up: cap, dl: 0, merge: 0 };
  }
  const up = Math.min(_QB_FX_SHARD_MAX, Math.ceil(cap / 2));
  return { up, dl: Math.min(_QB_FX_SHARD_MAX, cap - up), merge: 0 };
}

/* D4 末点 y 间距缩小: spacing < 26px 时 scale = spacing/26 线性缩小(下限 0.4 —— 反馈按比例
 * 缩小但两轨各自保留, 不合并不取消); 间距 ≥26px 恒 1(不放大)。 */
function _qbFxGapScale(spacingPx) {
  const s = Number(spacingPx);
  if (!Number.isFinite(s) || s <= 0) return _QB_FX_Y_GAP_MIN_SCALE;
  return Math.max(_QB_FX_Y_GAP_MIN_SCALE, Math.min(1, s / _QB_FX_Y_GAP_PX));
}

/* N 层回落系数(I9/I11): q = 1 − t/(0.33×beat) ∈ [0,1], t ≥ 0.33×beat 恒 0(零绘制) */
function _qbFxNeonQ(t, beat) {
  const end = beat * _QB_FX_NEON_RATIO;
  if (!(t >= 0) || !(t < end)) return 0;
  return 1 - t / end;
}

/* 冲击扩张环状态(V2): r(t) = rMax × easeOut(t/0.55beat) 快速扩张, alpha ∝ (1 − t/0.55beat);
 * t ≥ 0.55×beat -> null(零绘制 —— I9 冲击类叠加层窗)。 */
function _qbFxRingAt(t, beat, rMax) {
  const T = beat * _QB_FX_PART_RATIO;
  if (!(t >= 0) || !(t < T)) return null;
  return { r: rMax * _qbFxEaseOut(Math.min(t / T, 1)), alpha: 1 - t / T };
}

/* V3 粒子三阶段运动/亮度(纯函数): 爆发期 [0, burstMs) 速度 ×4.5(= impact 窗), 拖尾期
 * [burstMs, 0.55×beat) 名义速度 ×1 并 easeOut 减速; t ≥ 0.55×beat -> null(零绘制)。
 * 速度 v 由末态行程反解: 4.5v×burstMs + v×trailMs = dist(easeOut(1)=1); 亮度 ∝ (1 − t/T),
 * t=0 首帧最亮(与判定线闪光同帧 —— I9); carryPx = L0 视口回摆带来的末点位移(粒子随末点滑动,
 * 与曲线不脱钩)。 */
function _qbFxParticleAt(t, beat, burstMs, spec, carryPx) {
  const T = beat * _QB_FX_PART_RATIO;
  if (!(t >= 0) || !(t < T)) return null;
  const trailMs = Math.max(T - burstMs, 1e-9);
  const v = spec.dist / (4.5 * burstMs + trailMs);
  const d = t <= burstMs
    ? 4.5 * v * t
    : 4.5 * v * burstMs + v * trailMs * _qbFxEaseOut((t - burstMs) / trailMs);
  return {
    x: spec.x0 + Math.cos(spec.ang) * d + carryPx,
    y: spec.y0 + Math.sin(spec.ang) * d,
    alpha: 1 - t / T,
    d,
    rot: spec.rot0 + spec.vr * t,
  };
}

/* 粒子喷射清单(V3): n 个三/四/五边多边形碎片(非圆点 —— Beat Saber 碎片/Phigros 几何碎片),
 * 喷射角均匀铺满左向 270° 弧(45°..315°, 0°=+x 指向右缘外 —— 末点贴判定线, 右向碎片全被绘图
 * 区裁剪白费)加 ±5° 抖动, 尺寸 1.5-3.5px / 行程 1.1-1.6 × 环最大半径 / 自旋伪随机。
 * 确定性: 同种子恒同清单(node 电池真跑)。 */
function _qbFxSpawnSpecs(n, x0, y0, rMax, seed) {
  const rnd = _qbFxRand(seed);
  const out = [];
  for (let i = 0; i < n; i++) {
    const ang = (45 + (270 * (i + 0.5)) / n + (rnd() - 0.5) * 10) * Math.PI / 180;
    out.push({
      x0, y0, ang,
      sides: 3 + Math.floor(rnd() * 3),
      size: 1.5 + rnd() * 2,
      dist: rMax * (1.1 + 0.5 * rnd()),
      rot0: rnd() * Math.PI * 2,
      vr: (rnd() - 0.5) * 0.03,
    });
  }
  return out;
}

/* glitch 水平切片清单(V2, palette=glitch 专用; R6: ≤5 条): y 在锚带 ±14px 内伪随机, dy0 为
 * ±3px 正弦微震幅值(I9 上限 ≤5px), len 24-64px 右缘对齐, alpha0 0.2-0.5。 */
function _qbFxSlices(n, yCenter, seed) {
  const rnd = _qbFxRand(seed);
  const out = [];
  for (let i = 0; i < n; i++) {
    out.push({
      y: yCenter + (rnd() * 2 - 1) * 14,
      dy0: (rnd() * 2 - 1) * _QB_FX_SLICE_SHAKE_PX,
      len: 24 + rnd() * 40,
      alpha0: 0.2 + rnd() * 0.3,
      ph: rnd() * Math.PI * 2,
    });
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
    /* 全局入口门(P5a): qbTrafficOn 且今日流量面板在(statusbar 挂点本体, plan §07 表(1))。 */
    qbHistEntryOn() {
      return !!(this.flags && this.flags.qb_traffic_enabled && this.todayTraffic);
    },
    /* 当前流量形态的作用域("" = 非流量形态) —— 三挂点正文块(drawer.html qbTrafficActive)与
     * 抽屉流量形态高度判据(drawer.js drawerPanelStyle)的单一派生点。 */
    qbCurScope() {
      if (!this.drawer.open) return "";
      if (this.drawerIsTraffic) return this.drawer.scope || "";
      if (this.drawerIsSeed && this.drawer.tab === "traffic" && this.qbTrafficOn) return "torrent";
      return "";
    },
    qbTrafficActive() {
      return !!this.qbCurScope;
    },
    /* 流量形态头部标题(kind === "traffic" 时用; 单种走种子详情头部, 不消费本值)。
     * 2026-10-08 用户要求标题缩短为「qB流量图」(原「qB 口径流量图 · 全局」太长)。分组/种子
     * 保留各自名称(它们本就短, 且要区分对象)。 */
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
     * (1) 空态响应落袋后 data 是非 null 对象(空 points 也是对象, 只有出错才置 null), 续拉不再接管;
     * (2) 错误态落袋后 error 非空, 同样不接管(错误文案由下一次成功落袋清除, 见 _qbLoad);
     * 已有结果时续拉一律不动正文 —— 图/空态文案/错误文案都是「既有状态」(同 drawer-switch-flicker
     * 的「加载态立即点亮 = 制造新闪烁」)。 */
    qbCurPending() {
      return !!(this.qbCurLoading && !this.qbCurData && !this.qbCurError);
    },
    qbCurWindow() {
      const s = this.qbCurScope;
      return s ? this[_QB_SCOPES[s].window] : "24h";
    },
    /* 悬停取值(对齐 dialogs.js histHover 十字先例): 时刻 + 上/下载速率(fmtSpeed 同源);
     * null 桶不出速率, 出缺口文案(qbCurGapText, 按区段 × 作用域 —— 2026-10-30 起不再对
     * 所有缺口一视同仁地归因); 0 桶状态行在 drawer.html 模板侧(up+dl==0)。left/flip 由
     * 十字线 px 折算。 */
    qbCurHover() {
      const s = this.qbCurScope;
      return s ? this._qbHoverOf(s) : null;
    },
    /* 缺口悬停文案单点(webui.md「同一口径收成 computed 单点」, 模板只引用不重算):
     * 口径 = **不得替用户归因** —— 系统能观测到的只有「这里有/没有数据」, 为什么没有它不知道。
     *   - mid(数据链中间的洞): 前后都有观测 => 「中断」是可观测事实, 三挂点同句;
     *   - outside(数据链之外: 链首之前 / 链尾之后 / 全帧无观测): 只陈述「该时段没有这个
     *     对象的数据」, 主语按作用域取(种子态才是「此种子」, 全局态没有种子概念 —— 一律套
     *     「此种子」在全局图上又是一次瞎编)。
     * !旧文案对两类缺口通吃、一律断言成「程序未运行或 qB 断联」: 刚添加不久的种子, 图左侧那
     *   一整段历史空白(那时确实还没这个种子的数据, 与断联无关)全被断言成断联。 */
    qbCurGapText() {
      const h = this.qbCurHover;
      if (!h || !h.gap) return "";
      if (h.zone === "mid") return "采样中断 · 该时段无数据";
      const s = this.qbCurScope;
      if (s === "torrent") return "该时段无此种子数据";
      if (s === "group") return "该时段无该分组数据";
      return "该时段无数据";
    },
    /* 窗口内累计(totals 非空桶求和; 断线/重置桶本就 null 不计 —— §5.1 差分语义) */
    /* 重启缝提示(P4, plan 26-10-15-0829; 左端口径修订 26-10-16, issue 26-10-16-0954):
     * 数据链末点早于右沿且重启贴近链末(meta 新键 server_started_at ∈ [链末桶前一桶起点, 右沿])
     * 时给「数据接缝中」提示, 不与停机洞混读; 判据单点 _qbSeamHint(纯函数, node 单测),
     * null = 非缝(纯停机洞/链确已接续/旧后端)。
     * 断线语义不变: null 桶照旧断线不连线 + 斜纹, 提示只是追加一行状态注解。 */
    qbCurSeamHint() {
      const d = this.qbCurData;
      if (!d || !d.points || !d.points.length) return null;
      return _qbSeamHint(d.points, Number(d.meta && d.meta.interval_s), d.meta);
    },
    qbCurSummary() {
      const s = this.qbCurScope;
      return s ? this._qbSummaryOf(s) : null;
    },
    /* 空态/汇总口径文案(按作用域微调; 其余文案三挂点一致)。
     * !2026-10-30 起与缺口悬停同口径: 只陈述事实不归因 —— 空态要说的只是「这份数据为空」
     *   加上「有传输才会产生采样」这条采样条件; 旧版 global 那句「程序运行期间无采样」在
     *   程序明明在跑、只是该作用域无数据时, 读起来是错的。 */
    qbCurEmptyText() {
      const s = this.qbCurScope;
      if (s === "torrent") return "暂无该种子的 qB 口径流量数据(从未产生传输采样)";
      if (s === "group") return "暂无该分组的 qB 口径流量数据(成员产生传输采样期间才有数据)";
      return "暂无 qB 口径流量数据(该时段无任何采样)";
    },
    qbCurSummaryHint() {
      const s = this.qbCurScope;
      const base = "累计为窗口内增量(无数据期不计)";
      const scoped = s === "group" ? base + " · 组口径 = 当前成员集聚合" : base;
      // D4(plan 26-10-12-0535)文案: 限速线取值口径 + 记录起点前不显示(挂点 = 悬浮说明,
      // 常驻说明区已随 2026-10-08 版式改退役)
      return scoped + " · 限速虚线 = 当时生效的 qB 全局限速(记录起点前不显示)";
    },
    /* 窗口档位清单(模板 v-for 的唯一来源, 与前后切换/持久化校验同源 QB_WINDOW_NAMES) */
    qbWindowNames() {
      return QB_WINDOW_NAMES;
    },
    /* R23-B-17(26-10-20-2231): 上面两份清单各自投影成 <aq-seg> 要的形状 [{v, label}] —— 投影
     * 自既有单点(QB_WINDOW_NAMES + qbWindowLabel / QB_YAXIS_MODES + QB_YAXIS_LABELS), 不新建
     * 第二份清单; 模板里不再手写这批按钮(它们的布局各自为政, 见 tpl/ctl-bits.html 头注)。 */
    qbWindowTabs() {
      return QB_WINDOW_NAMES.map((w) => ({ v: w, label: this.qbWindowLabel(w) }));
    },
    qbYAxisTabs() {
      return QB_YAXIS_MODES.map((m) => ({ v: m, label: QB_YAXIS_LABELS[m] || m }));
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
    /* 注: 纵轴工具条的「上限 …(全局限速 ×1.2)」常驻读数已于 2026-10-16 随 UI 移除
     * (用户要求去掉上限字样, 图面自解释), computed 与 .qb-tools-hint 一并退役。 */
    /* ---------------- 数值面板状态行只读两项(R8 §05.3 不可编辑项表) ----------------
     * 展示值落 computed(范式同 qbCurGapText): fx-panel.html 裸插值 {{ qbFxPeriodS }} 不加括号,
     * 落 methods 域会被 toDisplayString 渲染成函数源码字符串(Vue 3 对非字符串一律 String())。
     * period 取 _qbPollMs 实算值(不是面板自己估的), 恒一位小数("3.0"/"30.0", §05.3 规格行
     * 「采样 3.0 s」); beat 为派生量(可调即允许突破 I1 的 1s 硬上限, 故只读), 公式单点在
     * _qbBeatMs(S1 起面板与调度器共用一份, 不再各写一遍 clamp)。「上次真实拍」S3 接节拍状态
     * 后回填, 现显示 —。 */
    qbFxPeriodS() {
      return (this._qbFxCurPeriodMs() / 1000).toFixed(1);
    },
    qbFxBeatMs() {
      return Math.round(_qbBeatMs(this._qbFxCurPeriodMs()));
    },
    /* 有效值单点(§05.6 reduced-motion 红线): effectiveOn = enabled && !reduce —— 系统要求减弱
     * 动效时可访问性红线(I7 强退)压过面板总开关, 面板置灰/强制关与 AQB_FX_CFG.on 引擎消费面
     * 一律吃这里; fx.enabled 只存用户意图, reduce 态的自动置位**永不回写 store**(否则系统设置
     * 恢复后用户手动开过的动效回不来)。面板任何操作(含重置为默认)都写不出有效值打开 —— 结构上
     * 有效值恒过本单点的 && !reduce, 不是靠各处理器自觉。 */
    fxOn() {
      return this.fx.enabled === true && !this.fxReduce;
    },
  },
  /* 限速值变化(首次到手 / qB 重连 / 运行中改限速)时重排一次 y 轴 —— 长窗轮询间隔可夹到
   * 600s, 不重排则「限速+20%」迟迟不生效。注册走根实例 mounted(与各 AQB_* 片段同款):
   * 本 mixin 经 app.mixin 全局注入, <transition> 的 BaseTransition 假实例没有数据面,
   * 写成 watch 选项会在其上求值即抛; mounted 里先按 this.drawer 守卫剔除假实例。 */
  mounted() {
    if (!this.drawer) return;  /* BaseTransition 等假实例无数据面: 跳过(真根实例恒有 drawer) */
    this._qbLimitUnwatch = this.$watch(() => this._qbGlobalLimit(), () => {
      for (const s of Object.keys(_QB_SCOPES)) {
        if (_QB_SCOPES[s].active(this) && this._qbYCapOf(s) > 0) this._qbChartRescale(s);
      }
    });
    /* reduced-motion 跟随(§05.6): matchMedia change 监听 app 常驻(mounted 装 / beforeUnmount
     * 摘, 同 _qbLimitUnwatch 装卸纪律) —— 系统设置恢复后有效值**立即**回到 enabled 的用户手动
     * 值(fxReduce 翻转 -> state.js 的 fxReduce watcher 重同步 AQB_FX_CFG.on + 面板控件解除
     * 置灰), 不能等下次用户操作才生效。初值 data() 已由 qbInitialFxReduce 取过, 这里补监听并
     * 再对齐一次(mounted 前系统设置变了也吃得到)。处理器提为实例字段(unmounted 按同一引用摘,
     * R4 清池纪律)。 */
    if (window.matchMedia) {
      this._qbFxMql = window.matchMedia("(prefers-reduced-motion: reduce)");
      this._qbFxOnReduce = () => { this.fxReduce = this._qbFxMql.matches === true; };
      this._qbFxOnReduce();
      this._qbFxMql.addEventListener("change", this._qbFxOnReduce);
    }
  },
  beforeUnmount() {
    if (this._qbLimitUnwatch) {
      this._qbLimitUnwatch();
      this._qbLimitUnwatch = null;
    }
    /* matchMedia change 监听对称摘除(与 _qbLimitUnwatch 同纪律): MediaQueryList 持实例引用,
     * 不摘则热重载后旧句柄堆叠; 假实例 mounted 早退未挂, 守卫恒过。 */
    if (this._qbFxMql) {
      this._qbFxMql.removeEventListener("change", this._qbFxOnReduce);
      this._qbFxMql = null;
      this._qbFxOnReduce = null;
    }
    /* themechange 监听对称摘除(池条目 R5#181): 挂载在 _qbChartBuild 里由 _qbThemeBound 保证
     * 只挂一次, 卸载不同步摘除则 documentElement 持实例引用一起泄漏; 处理器在挂载点已提为
     * 实例字段 _qbOnThemeChange, 此处按同一引用摘, 并复位 _qbThemeBound 让重挂可重绑。 */
    if (this._qbThemeBound) {
      document.documentElement.removeEventListener("autoqb:themechange", this._qbOnThemeChange);
      this._qbThemeBound = false;
      this._qbOnThemeChange = null;
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
      // (shortcuts.js open-qb-traffic): 功能关闭时按了键要给出反馈, 不静默。
      // issue 26-11-11-0633: flags 未取到(boot 期偶发失败落 fail-closed)先补拉一次再判,
      // 不把"没取到"当"没启用"误报; 已取到的真未启用原样提示
      if (!this.qbTrafficOn && !this.flagsLoaded) await this.ensureWebFlags();
      if (!this.qbTrafficOn) {
        this.toast("功能未启用: qB 口径流量图, 请先在设置里打开", "info", 2500);
        return;
      }
      return this.openDrawerTraffic("global", "");
    },
    /* 分组入口(S5b, §07 表(3)): 入口 = 组右键菜单「qB 口径流量图」(ctx-menus.html, v-if=qbTrafficOn)。
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
      if (this.drawer.open && this.drawerIsTraffic && this.drawer.scope === scope
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
    /* 窗口切换(十三档, 单点 QB_WINDOW_NAMES): 换窗即重拉重画; 打开中的轮询由骨架每拍重读间隔自动重排 */
    qbSetWindow(w) {
      const s = this.qbCurScope;
      return s ? this._qbSetWindow(s, w) : undefined;
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
    /* 全局限速(上下载**较大者**, bytes/s; 0 = 无限速或字段未知) —— 三作用域同源(用户拍板)。
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
    /* ================= 数值面板(R8, plan 26-11-12-1139 §05): 图区右键的非模态锚定浮层 =================
     * 模板分片 shared/tpl/fx-panel.html(四皮肤共享, into=app —— .drawer-dock 的**兄弟**节点:
     * 不进 .drawer 子树, flux 的 transform containing-block 会把 fixed 定位劫持成相对抽屉, §09
     * 风险行); 视图态 fxPanel/fxReduce 与参数值 fx 在 state.js(根选项显式建字段), 本模块只管
     * 行为与持久化。
     * 收层面(S0-b, §05.7): 七处登记(lifecycle 点空白 + Esc 退栈链 / dialogs_meta escBusy /
     * shortcuts _kbOverlayBusy 末尾 / closeDrawer / drawerTab / drawer_store 换 kind 收口)+
     * IO 宿主可见性兜底(_qbFxListen 内, 换肤不误关); 七处登记直接写 visible = false 不经
     * fxClose, 监听与 IO 的断开由 state.js 的 'fxPanel.visible' watcher 统一汇到 _qbFxListen(false)。
     * !命名: 模板触达的处理器不得带 _ 前缀(commands_send.js:347-350 前科 —— Vue 模板解析不到
     *   _ 前缀成员, 整块渲染失败); 对外 fxClose/fxReset/fxCopy/fxPreview/fxCheck/fxPick/fxRange,
     *   模块内部才 _qb*。 */
    /* 开层(入口在 _qbChartBuild 的宿主 contextmenu 监听): 定位 = 右键点右侧、图右缘内缩 8px
     * (FIT.EDGE, 复用 overlay_fit 单点范式, 不发明第二套定位), 垂直以点击 y 为锚; 初值尺寸按
     * 常量估算(宽 320 固定 / 高按高级折叠态实测约 500), 精确收口在 fxPanel watcher 的
     * $nextTick 实测重钳位(_qbFxRefit, 与菜单 _menuPos 估 + _menuFitRefit 实测两级同范式)。
     * 总开关关掉也照开(§05.6: 否则用户失去重新打开的入口)。 */
    openFxPanel(px, py) {
      const FIT = window.AQB_OVERLAY_FIT;
      const host = this.$refs.qbChartHost;
      let x = Number(px) || 0;
      if (host && host.isConnected) {
        x = Math.min(x, host.getBoundingClientRect().right - FIT.EDGE - QB_FX_PANEL_W);
      }
      const at = FIT.fitInViewport(null, x, Number(py) || 0, { w: QB_FX_PANEL_W, h: QB_FX_PANEL_H_EST });
      this.fxPanel = { visible: true, x: at.x, y: at.y, alt: false };  // 对象整体替换 -> watcher 重钳位
      this._qbFxListen(true);
    },
    /* 面板根 Esc(fx-panel.html @keydown.esc="fxEsc"): 面板**可见**才拦 —— stopPropagation +
     * preventDefault + fxClose, 焦点在面板控件内(如刚拖完滑杆)按 Esc 也只关面板, 同一次 Esc
     * 不再推进抽屉退栈链(一次 Esc 只关一层)。可见性早退是行为面不是防御: 退场过渡
     * (fx-pop-leave-active 120ms)期 visible 已翻 false 而焦点仍在面板控件里, 那次 Esc 必须
     * **放行**给 document 退栈链 —— 若用 .stop 修饰符, 阻断先于处理器表达式, 该次 Esc 被整体
     * 吞掉, 与「面板外按 Esc 二次关抽屉」的行为不一致(评审 nit 轮裁决)。
     * !模板触达, 不得带 _ 前缀(commands_send.js:347-350 前科)。 */
    fxEsc(e) {
      if (!this.fxPanel.visible) return;
      e.stopPropagation();
      e.preventDefault();
      this.fxClose();
    },
    /* 关层(面板右上 x 钮 / 面板根 Esc 经 fxEsc / IO 兜底; 七处收层登记走各自位置的
     * visible = false 直写, 监听断开统一由 state.js 的 'fxPanel.visible' watcher 汇到
     * _qbFxListen(false) —— 本方法的显式断开与它重入幂等, 先到先断; 已关面板再入走首行
     * 早退, 重入安全) */
    fxClose() {
      if (!this.fxPanel.visible) return;
      this.fxPanel = { visible: false, x: 0, y: 0, alt: false };
      this._qbFxListen(false);
    },
    /* 开/关层的窗口级监听装卸(resize / 页面滚动 / Alt 看穿 / 宿主高度观察, §05.1 跟随行)。
     * !处理器一律提为实例字段(lifecycle.js R4 清池纪律: removeEventListener 需要同一引用);
     *   装卸与 open/close 配对, 页面卸载随 window 消亡(不另挂 unmounted —— AQB_QB_TRAFFIC 走
     *   app.mixin, 生命周期钩子会波及全部组件实例, 见 state.js/lifecycle.js 头 WARN)。 */
    _qbFxListen(on) {
      if (on) {
        if (!this._qbFxOnResize) {
          this._qbFxOnResize = () => this._qbFxRefitSoon();
          this._qbFxOnScroll = () => this._qbFxRefitSoon();
          this._qbFxOnBlur = () => { this.fxPanel.alt = false; };  // Alt+Tab 离场 keyup 丢失, 失焦复位防卡在看穿态
          this._qbFxOnAltKey = (e) => {
            if (!this.fxPanel.visible) return;
            this.fxPanel.alt = e.altKey === true;  // 按住 Alt 看穿(opacity 0.22 + pointer-events:none), 松开恢复(§05.1)
          };
        }
        window.addEventListener("resize", this._qbFxOnResize);
        window.addEventListener("scroll", this._qbFxOnScroll, { passive: true });
        window.addEventListener("keydown", this._qbFxOnAltKey);
        window.addEventListener("keyup", this._qbFxOnAltKey);
        window.addEventListener("blur", this._qbFxOnBlur);
        // 抽屉拖拽调高 -> 图宿主高变(.qb-chart-host height:100%): RO 触发节流重钳位。宿主被拆
        // (抽屉关/换 kind/切页签)时 RO 报空盒 —— 跳过即可, 收口由下面的 IO 兜底(§05.7)。
        if (!this._qbFxHostRo) {
          this._qbFxHostRo = new ResizeObserver(() => {
            const host = this.$refs.qbChartHost;
            if (!host || !host.isConnected || host.clientWidth === 0) return;
            this._qbFxRefitSoon();
          });
        }
        const host = this.$refs.qbChartHost;
        if (host && host.isConnected) this._qbFxHostRo.observe(host);
        // 宿主可见性兜底(R8, plan 26-11-12-1139 §05.7): 观察 .qb-chart-host, intersectionRatio
        // === 0 即关面板 —— 一条机制覆盖「滚出视口」「切页签」「抽屉关闭」三路(宿主是 v-if 分支,
        // 被真拆后 IO 对已卸载元素报 ratio 0)。!不挂 _qbChartDestroy: 换肤也走 destroy->build
        // (themechange), 会把面板误关; 系统明暗变化(theme.js 派发 autoqb:themechange)宿主不重挂,
        // IO 不触发, 面板保留。生命周期与面板开关对称: 开面板建/观察(与 RO 同点), 关面板断(见
        // 下面 off 支), 装卸配对防泄漏(七处登记直接写 visible = false 不经 fxClose 的那路, 由
        // state.js 的 'fxPanel.visible' watcher 统一汇到这里断)。
        if (!this._qbFxHostIo) {
          this._qbFxHostIo = new IntersectionObserver((entries) => {
            for (const en of entries) {
              if (en.intersectionRatio === 0) {
                this.fxClose();
                return;
              }
            }
          }, { threshold: 0 });
        }
        if (host && host.isConnected) this._qbFxHostIo.observe(host);
        return;
      }
      window.removeEventListener("resize", this._qbFxOnResize);
      window.removeEventListener("scroll", this._qbFxOnScroll);
      window.removeEventListener("keydown", this._qbFxOnAltKey);
      window.removeEventListener("keyup", this._qbFxOnAltKey);
      window.removeEventListener("blur", this._qbFxOnBlur);
      if (this._qbFxHostRo) this._qbFxHostRo.disconnect();
      if (this._qbFxHostIo) this._qbFxHostIo.disconnect();
    },
    /* 节流重钳位(≤60ms 一次, §05.1 跟随行): resize / 页面滚动 / 抽屉高度变化共用的唯一入口。
     * leading + trailing 两段 —— 抽屉入场 rAF 逐帧改高只换来 60ms 一次的钳位, 不与
     * ResizeObserver -> u.setSize 连锁成逐帧抖动; 事件停了也要补一跳, 停在最终位置。 */
    _qbFxRefitSoon() {
      if (!this.fxPanel.visible) return;
      const now = Date.now();
      if (now - (this._qbFxRefitAt || 0) >= 60) {
        if (this._qbFxRefitTimer) { clearTimeout(this._qbFxRefitTimer); this._qbFxRefitTimer = 0; }
        this._qbFxRefitAt = now;
        this._qbFxRefit();
        return;
      }
      if (this._qbFxRefitTimer) return;
      this._qbFxRefitTimer = setTimeout(() => {
        this._qbFxRefitTimer = 0;
        this._qbFxRefitAt = Date.now();
        this._qbFxRefit();
      }, 60);
    },
    /* 实测重钳位: 量真实面板盒(offsetWidth/offsetHeight)后两轴夹取进视口(FIT.fitInViewport,
     * 只夹视口、**不压缩尺寸** —— 尺寸大于视口由 CSS max-height + 正文内部滚动兜底, §05.9),
     * 且保持右缘不越过图宿主右缘内缩 8px(首次定位的锚定约束在重钳位时同样成立)。 */
    _qbFxRefit() {
      const s = this.fxPanel;
      if (!s || !s.visible) return;
      const el = this.$refs.fxPanelEl;
      if (!el || !el.isConnected) return;
      const FIT = window.AQB_OVERLAY_FIT;
      let x = s.x;
      const host = this.$refs.qbChartHost;
      if (host && host.isConnected) {
        x = Math.min(x, host.getBoundingClientRect().right - FIT.EDGE - el.offsetWidth);
      }
      const p = FIT.fitInViewport(el, x, s.y);
      s.x = p.x;  // 回写 x/y 字段而非整对象: 不会自触发 fxPanel watcher(同 _menuFitRefit 口径)
      s.y = p.y;
    },
    /* ---------------- 面板控件处理器(§05.3 字段表; 模板触达, 不得带 _ 前缀) ----------------
     * 持久化时机(§05.5「只在用户操作时写」): 滑杆 @input 逐值写内存(即改即用)、@change 落盘
     * 一次 —— 拖拽全程不逐 tick 写 localStorage; 复选框/下拉只有 change 事件, 处理器内直接落盘。 */
    /* 百分比读数(存储 0-1 -> 显示 0-100; 消费面: impact/particles/shiftRatio 三根滑杆的 value 与读数) */
    fxPct(key) {
      const n = Number(this.fx[key]);
      return Number.isFinite(n) ? Math.round(n * 100) : 0;
    },
    /* 滑杆(显示 0-100 -> 存储 /100; shiftRatio 滑杆 min=20 => 存储域 [0.2,1] 天然成立)。 */
    fxRange(key, ev) {
      const el = ev && ev.target;
      if (!el) return;
      const n = Number(el.value);
      if (!Number.isFinite(n)) return;
      const v = Math.min(1, Math.max(0, n / 100));
      if (this.fx[key] === v) return;
      this.fx[key] = v;
    },
    /* 下拉(select 的 value 恒来自模板静态候选, 白名单兜一道防脏 —— 非法回落现值, 不落盘不生效) */
    fxPick(key, ev) {
      const el = ev && ev.target;
      if (!el) return;
      const wl = QB_FX_ENUMS[key];
      if (!wl || wl.indexOf(el.value) < 0) {
        el.value = String(this.fx[key]);
        return;
      }
      if (this.fx[key] === el.value) return;
      this.fx[key] = el.value;
      this.persistQbFx();
    },
    /* 复选框(总开关 enabled / 视觉 neon/tail / 高级四层开关 layers.*; 布尔严格 === true|false) */
    fxCheck(key, ev) {
      const el = ev && ev.target;
      if (!el) return;
      const on = el.checked === true;
      if (key.indexOf("layers.") === 0) {
        const lk = key.slice(7);
        if (!this.fx.layers || !(lk in this.fx.layers) || this.fx.layers[lk] === on) return;
        this.fx.layers[lk] = on;
      } else {
        if (this.fx[key] === on) return;
        this.fx[key] = on;
      }
      this.persistQbFx();
    },
    /* 重置为默认(§05.5: 写回默认值并立即生效, **不删键** —— 用户可能只想回到默认, 不想让旧值
     * 在下次启动时"复活")。reduced-motion 红线(§05.6)结构上成立: reduce 态下 enabled 写回
     * 默认 true 是用户操作落 store, 有效值仍经 fxOn 单点被 !reduce 压住为关 —— 任何面板操作
     * (含本重置)都写不出有效值打开。 */
    fxReset() {
      this.fx = _qbFxClone(QB_FX_DEFAULTS);  // 对象整体替换 -> watch.fx 同步 AQB_FX_CFG
      this.persistQbFx();
    },
    /* 复制配置片段(§05.5: 走既有复制通道 _copyText —— 非安全上下文 execCommand 降级 + toast
     * 反馈, qB WebUI 常走局域网 http, 自建 clipboard 调用会静默失败; 输出可直接粘进源码默认
     * 常量的 JS 片段, 含全部存储字段 + 只读两项的去处注释)。 */
    fxCopy() {
      const snip = "var QB_FX_DEFAULTS = " + JSON.stringify(this.fx, null, 2) + ";\n"
        + "// 只读两项不进本片段: 采样周期 period(属后端与数据文件) / 拍长 beat(派生量)。";
      this._copyText(snip, "动效配置片段");
    },
    /* 预览一拍(占位): 语义六条(§05.4 不动窗口/假 Δ 贴近真实量级/连点重启/真值抢占/不写 store/
     * 同预算)在 S3 接真值链路 —— 本阶段按钮在、处理器在、零副作用。 */
    fxPreview() {
      /* S3: _qbPreviewBeat 按 §05.4 伪代码接, 预览令牌/真值抢占/预算同 I9。 */
    },
    /* fx 落盘(§05.5: 只在用户操作时写 —— 调用点全在面板处理器; try/catch 静默失败, 隐私模式/
     * 配额满不得让调参崩; 重置也走这里 = 写回默认不删键)。有效值 on 不落盘: store 只存 15+1
     * 个字段(v + enabled + 14 项), reduce 态的有效关是运行期事实不是用户意图。 */
    persistQbFx() {
      try {
        localStorage.setItem(QB_FX_STORE_KEY, JSON.stringify(this.fx));
      } catch { /* 写入失败: 本轮仍生效, 刷新后回落默认 */ }
    },
    /* AQB_FX_CFG 同步单点(§05.3 + §05.6): fx 整对象 JSON 克隆(斩响应式代理, 绘制热路径只读
     * 普通对象) + 附加有效值 **on**(= fxOn, = enabled && !reduce) —— S1/S3 引擎侧的开关消费面。
     * state.js 的 fx 与 fxReduce 两个 watcher 都汇到这里: reduce 翻转时 on 必须立即跟着翻
     * (系统设置恢复 -> 有效值立即回到 enabled 的手动值), 不能只靠 fx watcher(它只看 fx 自身)。
     * !fxOn 是 computed, 读它不带括号(getter 语义; 带括号 = 把 getter 的值当函数调, TypeError
     *   整页白屏, 守阵 test_frontend_computed_not_invoked_as_function 钉此形态)。
     * on 只进运行期配置对象, 不进持久化键(persistQbFx 只写 fx)。 */
    _qbFxCfgSync() {
      const cfg = JSON.parse(JSON.stringify(this.fx));
      cfg.on = this.fxOn;
      window.AQB_FX_CFG = cfg;
    },
    /* 状态行只读两项的周期实算单点(展示值 qbFxPeriodS/qbFxBeatMs 在 computed 块 —— 模板裸
     * 插值不加括号, 落 methods 会被 toDisplayString 渲染成函数源码字符串; §05.3 不可编辑项表) */
    _qbFxCurPeriodMs() {
      const s = this.qbCurScope;
      return s ? this._qbPollMs(s) : _QB_POLL_FALLBACK_MS;
    },
    /* y 轴重排(上限变更/限速到手): 只重算 scale 并重画注解层, 不销毁重建、不重取数。
     * setData(resetScales 默认 true) 会重跑 y range 与全部 draw 钩子(注解层随之上新)。
     * S1: 在途拍内触发(y 切档/限速变化两入口)先终止在途拍并**直接落真值**(尾点插值中的值
     * 写回真值、清 ticks 冻结)再重排 —— 否则动画帧的 y 钉会盖过新档位一拍、偏置视口与新
     * 档位错配一帧; 收口语义与收敛帧同款, 不留半帧。 */
    _qbChartRescale(scope) {
      const u = this._qbCharts && this._qbCharts[scope];
      if (!u || !u.root || !u.root.isConnected || !u.data) return;
      const st = u._qbBeat;
      if (st && st.anim) {
        const a = st.anim;
        const tr = st.tracks;
        if (tr.up.live) u.data[1][a.n - 1] = tr.up.target;
        if (tr.dl.live) u.data[2][a.n - 1] = tr.dl.target;
        tr.up.shown = tr.up.live ? tr.up.target : null;
        tr.dl.shown = tr.dl.live ? tr.dl.target : null;
        this._qbBeatCancel(u);
        u._qbTickFreeze = null;
        u._qbTickFreezePending = false;
      }
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
      // 悬挂兜底的计时起点已随骨架上提(polling.js 的 st.stallAt, 由 tick 观测到 loading 置位的
      // 那一刻起算)—— 换目标场景下旧请求的 finally 晚于新请求的置位到达时不再有"擦起点"的坑。
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
      const ts = this._qbBucketTs(scope, i);
      const tip = this.fmtTime(ts);
      const W = (this._qbChartWs && this._qbChartWs[scope]) || 0;
      const flip = W > 0 && this[def.hoverLeft] > W * 0.62;
      const lim = _qbLimitAt(d.limits || [], ts);  // D7: 悬停时刻生效的当时限速(缺口也给 —— 时间真值)
      if (!p) {
        // 缺口: 交付**区段判据**(数据链之外 vs 链中间的洞); 文案由 qbCurGapText 按
        // 「区段 × 作用域」给 —— webui.md 单点口径, 模板只引用不重算原因
        const [first, last] = _qbChainBounds(..._qbPointsColumns(d.points));
        const zone = _qbGapZone(i, first, last);
        return { tip, gap: true, zone, lim, left: this[def.hoverLeft], flip };
      }
      return { tip, up: p.up, dl: p.dl, lim, left: this[def.hoverLeft], flip };
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
    /* 低频轮询走长驻骨架(polling.js::startPoll 单点, 2026-10-22): 这里只声明差异 ——
     *   - 节拍 = 采样间隔夹取(_qbPollMs); 骨架每拍重读间隔 => 换窗跨段(raw <-> hour)自动重排,
     *     不再需要单独的 resync 钩子(旧 _qbPollResync 随本轮收敛删除)。
     *   - 守卫 = 图还活跃(def.active); 页面隐藏由骨架恒等守卫兜, 不再手写。
     *   - 在途互斥(loading, 在 _qbLoad finally 归位)+ 悬挂兜底: 骨架统一做 —— 卡死判据就是
     *     loading 本身, 未超时前挡拍(mutex), 超阈值强制续拉并留一次警告痕(issue 26-10-16-0954
     *     的成因: 旧实现 loading 卡死即永久挡拍, 图表停在旧帧且无提示也不自愈)。
     *     阈值常量随骨架上提为 AQB_POLL_STALL_MS(polling.js), 抽屉侧自此同口径。 */
    _qbPollStart(scope) {
      this._qbPollStop(scope);
      this.startPoll(`qb:${scope}`, {
        ms: () => this._qbPollMs(scope),
        fn: () => this._qbLoad(scope),
        guard: () => _QB_SCOPES[scope].active(this),
        stall: () => this[_QB_SCOPES[scope].loading],
        mutex: true,
      });
    },
    _qbPollStop(scope) {
      this.stopPoll(`qb:${scope}`);
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
      // 语义: 上/下载与今日流量卡同源(--today-up/down); 兜底仍走令牌链, 不硬编码色值
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
    /* 缺口斜纹(drawClear 钩子 = 画在系列**之下**): 只给**数据链中间**的缺口(null 桶游程,
     * _qbGapZone === "mid")铺 45 度斜纹 —— 斜纹是「中断」的视觉记号, 只配给中断。
     * !2026-10-30: 链外的空白(该对象第一次采样之前 / 最后一次之后)留白不铺 —— 它同样是「不
     *   知道原因的没有数据」, 铺斜纹等于在视觉上重复一遍 tooltip 已经纠掉的归因错误。
     *   (旧注释称「与图例『缺口 = 无采样』文案同义」; 该图例随 2026-10-08 版式改退场, 且
     *   旧钩子对两类缺口通吃 —— 同为「标出这里没有数据」的性质, 但斜纹比中性文字更强硬。)
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
      // 只留数据链中间的洞(前后都有观测); 链外的空白交给 tooltip 用中性文字陈述, 不铺记号
      const [first, last] = _qbChainBounds(up, dl);
      const inner = runs.filter((r) => _qbGapZone(r[0], first, last) === "mid");
      if (!inner.length) return;
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
      for (const [a, b] of inner) {
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
    /* 限速虚线(draw 钩子 = 画在系列**之上**): 按**当时值**分段(plan 26-10-12-0535 D4,
     * 取代旧「拉取那一刻单值画满整窗」) —— 从图记录的 u._qbLimits(后端 limits 事件序列,
     * 建图/快路同步暂存)构段 _qbLimitSegs, 每段画在各自时间区间(经 valToPos), 最后一段
     * 延伸到图数据右沿; 缺口(无流量采样)处照画 —— 限速是时间真值, 独立于流量存在与否。
     * 可见性判据逐段化(延续 2026-10-08 拍板的逐段版本): 每段每方向 0 < v < ymax 才画
     * (0 = 不限速/缺值不画, 自动模式下峰值未超限速的段自然在顶沿之上不可见)。 */
    _qbDrawLimits(u, tk) {
      const ymax = u.scales && u.scales.y && u.scales.y.max;
      if (!(ymax > 0) || !u.bbox || !u.ctx) return;
      const events = u._qbLimits || [];
      const xs = u.data && u.data[0];
      const tEnd = xs && xs.length ? xs[xs.length - 1] : 0;
      const segs = _qbLimitSegs(events, tEnd);
      if (!segs.length) return;
      const px = this._qbCanvasScale(u);
      const ctx = u.ctx;
      const xL = u.bbox.left / px;
      const xR = (u.bbox.left + u.bbox.width) / px;
      const yTop = u.bbox.top / px;
      ctx.setLineDash([5, 4]);
      ctx.lineWidth = 1;
      for (const seg of segs) {
        const dirLines = [];
        if (seg.up > 0 && seg.up < ymax) dirLines.push([seg.up, tk.up]);
        if (seg.down > 0 && seg.down < ymax) dirLines.push([seg.down, tk.down]);
        if (!dirLines.length) continue;
        let x0 = xL + u.valToPos(seg.t0, "x");
        let x1 = xL + u.valToPos(seg.t1, "x");
        x0 = Math.max(x0, xL);
        x1 = Math.min(x1, xR);
        if (!(x1 > x0)) continue;  // 段越出可视窗(防御)不画
        for (const [val, color] of dirLines) {
          const y = yTop + u.valToPos(val, "y");
          ctx.strokeStyle = color;
          ctx.beginPath();
          ctx.moveTo(x0, y);
          ctx.lineTo(x1, y);
          ctx.stroke();
        }
      }
      ctx.restore();
    },
    /* ================= 视觉引擎 V + N 层绘制面(S2-a, plan §03 V 表/N 节/D1-D4) =================
     * 图层顺序(I6, 单点 _QB_FX_LAYER_ORDER; 挂点层序已读 vendor 1.6.32 源实证 —— drawAxes 在
     * Dl.axes 末尾 = 网格之后、系列之前): drawClear 段(恒最底)= _qbDrawGaps 缺口斜纹;
     * drawAxes 段(网格后系列前)= 几何环 → 粒子 → glitch 切片 → N 霓虹元素层(判定线短亮段/
     * 环外圈辉光/粒子外圈/角落徽标); draw 段(系列之上)= lead 策略从属轨描边加亮 → 末点菱形锚
     * (+N 锚辉光)。曲线描边由 uPlot 系列原生画在 drawAxes 之后 = 装饰永不压曲线(语义色一行
     * 不动 —— I10/D1); 背景/右缘/网格/tooltip/图例/限速虚线本引擎零触碰(I11 黑名单), 背景零
     * 铺色(I11/G7)。逐帧读 window.AQB_FX_CFG —— 拍内改参下一帧即生效(§05.3); 装饰帧全部经
     * 节拍调度器提交, 本域零 destroy/new uPlot/零 loading(I3)。 */
    /* 装饰面几何(CSS px; uPlot 1.6.x ctx 无 transform, 坐标 = 设备像素 —— 与 _qbDrawGaps 同口径) */
    _qbFxGeom(u) {
      const px = (typeof uPlot !== "undefined" && uPlot.pxRatio) || 1;
      return {
        px,
        L: u.bbox.left / px,
        T: u.bbox.top / px,
        W: u.bbox.width / px,
        H: u.bbox.height / px,
      };
    },
    /* 判定帧装饰状态生成(t=0 一次性; D3 仲裁 + V3 粒子清单): 返回 null = 本拍零装饰。
     * 时机 = _qbBeatStart 的尾点摆回之后(粒子原点 = t=0 显示末点像素位, y 由钉档 yMax 线性
     * 换算 —— 与钉住的纵轴刻度逐像素一致, 不依赖 valToPos 时序); 粒子/切片清单确定性伪随机
     * (种子取尾桶时刻) —— 同拍重绘恒同形, 跨拍随数据自然变化。生效条件: cfg.on === true 且
     * lead 等级 ≥ 1(双轨皆缺口/静默 -> null, L0/L1 照常 —— D2/I10)。 */
    _qbFxSpawn(u, tl, dx0, needsShift, yMax) {
      const cfg = window.AQB_FX_CFG;
      if (!cfg || cfg.on !== true) return null;
      const tr = u._qbBeat.tracks;
      const lead = _qbFxLead(tr.up, tr.dl);
      if (!lead) return null;
      const g = this._qbFxGeom(u);
      if (!(g.W > 0) || !(g.H > 0) || !(yMax > 0)) return null;
      const xs = u.data[0];
      const n = xs.length;
      const span = n > 1 ? xs[n - 1] - xs[0] : 0;
      const pxPerT = span > 0 ? g.W / span : 0;
      const dxPx = (needsShift ? dx0 : 0) * pxPerT;   // t=0 末点越出右缘的像素距(L0 偏置量)
      const yOf = (v) => g.T + g.H * (1 - Math.min(v, yMax) / yMax);
      const yUp = yOf(tr.up.shown);
      const yDl = yOf(tr.dl.shown);
      const bothLive = tr.up.live && tr.dl.live;
      const gapScale = bothLive ? _qbFxGapScale(Math.abs(yUp - yDl)) : 1;  // D4 y 间距缩小
      const lv = tr[lead].level;
      const rMax = (14 + 5 * lv) * gapScale;
      // 粒子清单按**满额**生成(密度恒取 1 的 partCap, 与拍内 cfg.particles 解耦): 密度/dual
      // 拍内改参由绘制侧逐帧重算 alloc 并钳制到清单长度(m = min(specs.length, n)) —— 下一帧即
      // 生效; cap 冻结在 spawn 会让拍内改密度整拍失效(违 §05.3/D21: partCap 即时生效)。策略
      // 形状(both/lead/merge 各自的清单落位与半套上限)仍按 spawn 时 cfg.dual 定型。
      const cap = _qbFxPartCap(lv, 1);
      const alloc = _qbFxAlloc(cfg.dual, cap, lead);
      const seed = Math.floor(xs[n - 1]) || 1;
      const tipX0 = g.L + g.W + dxPx;
      // merge 落位 y: 两轨皆 live 才取中点; 任一缺口退 lead 轨末点 y —— 缺口轨 shown=null 会被
      // yOf 换算成绘图区底边 T+H, 中点成了「与真实末点无关的假落位」(I10/D4)
      const yMerge = bothLive ? (yUp + yDl) / 2 : yOf(tr[lead].shown);
      const specs = {};
      if (alloc.up > 0) specs.up = _qbFxSpawnSpecs(alloc.up, tipX0, yUp, rMax, seed);
      if (alloc.dl > 0) specs.dl = _qbFxSpawnSpecs(alloc.dl, tipX0, yDl, rMax, seed ^ 0x9E3779B9);
      if (alloc.merge > 0) {
        specs.merge = _qbFxSpawnSpecs(alloc.merge, tipX0, yMerge, rMax, seed ^ 0x5BD1E995);
      }
      // glitch 水平切片清单(V2): **无条件**生成 5 条, 绘制侧按 cfg.palette === "glitch" 逐帧
      // 门控 —— palette 拍内切入/切出下一帧生效(清单冻结 palette 会让切入口整拍无切片); 锚带
      // 中心 = merge 时两轨 y 中点(缺口退 lead 末点 y, 同上), 否则 lead 末点 y
      const slices = _qbFxSlices(_QB_FX_SLICES_MAX,
        alloc.merge > 0 ? yMerge : yOf(tr[lead].shown), seed ^ 0x85EBCA6B);
      // 次区光点资格(每轨: live 且 level ≥ 1 —— Δ≈0/零流量/缺口轨零装饰, I10/D2)
      const tail = [];
      if (tr.up.live && tr.up.level > 0) tail.push("up");
      if (tr.dl.live && tr.dl.level > 0) tail.push("dl");
      return {
        lead, lv, gapScale, rMax, cap, alloc, specs, slices, tail,
        act: { up: tr.up.live && tr.up.level > 0, dl: tr.dl.live && tr.dl.level > 0 },
        pxPerT,
        dx0: needsShift ? dx0 : 0,
        beatMs: tl.beat,
        burstMs: tl.impactMs,
      };
    },
    /* drawAxes 装饰段(uPlot 网格之后、系列原生之前 —— 装饰压网格不压曲线, I6)。生效条件逐帧
     * 复核(cfg.on !== true 即零绘制 —— 拍内关总开关下一帧生效); 背景零铺色(I11/G7): 本钩子
     * 唯一的 fillRect 是 glitch 切片的 1px 级横条(R6 明示「切片是 1px 级 fillRect, 不构成铺底」),
     * 其余全部 stroke / 小多边形 fill。 */
    _qbDrawFx(u, tk) {
      const st = u._qbBeat;
      const a = st && st.anim;
      if (!a) return;
      if (a.phase === "tail") {
        // 次区相位: 流动光点落笔(像素位置由 _qbTailFrame 现算; 轨道语义色, 极轻不着 Lv —— I10)
        const pts = a.fxTail && a.fxTail.pts;
        if (!pts || !pts.length) return;
        this._qbCanvasScale(u);
        const ctx = u.ctx;
        for (const pt of pts) {
          ctx.globalAlpha = pt.alpha;
          ctx.fillStyle = pt.k === "up" ? tk.up : tk.down;
          ctx.beginPath();
          ctx.arc(pt.x, pt.y, 2, 0, Math.PI * 2);
          ctx.fill();
        }
        ctx.restore();
        return;
      }
      const fx = a.fx;
      if (!fx) return;
      const cfg = window.AQB_FX_CFG;
      if (!cfg || cfg.on !== true) return;
      const t = a.clock;
      if (!(t < fx.beatMs * _QB_FX_PART_RATIO)) return;   // 0.55×beat 后冲击类零绘制(I9)
      const px = this._qbCanvasScale(u);
      const ctx = u.ctx;
      const L = u.bbox.left / px;
      const T = u.bbox.top / px;
      const W = u.bbox.width / px;
      const H = u.bbox.height / px;
      ctx.beginPath();
      ctx.rect(L, T, W, H);
      ctx.clip();   // 装饰不出绘图区(与缺口斜纹同口径)
      const dx = a.needsShift ? (a.lastDx || 0) : 0;
      const tipX = L + W + dx * fx.pxPerT;      // 末点像素 x(随 L0 视口回摆滑动)
      const carry = (dx - fx.dx0) * fx.pxPerT;  // 粒子随末点一起滑动(L0 同步)
      const yOf = (v) => T + H * (1 - Math.min(v, a.yMax) / a.yMax);
      const tr = st.tracks;
      const yUp = yOf(tr.up.shown);
      const yDl = yOf(tr.dl.shown);
      const lvColor = _QB_FX_LV_COLORS[fx.lv] || _QB_FX_LV_COLORS[3];
      const blurCap = _QB_FX_BLUR_CAPS[cfg.palette] != null
        ? _QB_FX_BLUR_CAPS[cfg.palette] : _QB_FX_BLUR_CAPS.neon;
      const q = _qbFxNeonQ(t, fx.beatMs);        // N 层回落系数(≤0.33×beat —— I9/I11)
      const neon = cfg.neon === true && q > 0;
      const ens = Math.max(0, 1 - t / (fx.beatMs * _QB_FX_PART_RATIO));
      // 本帧落位清单(D3 逐帧仲裁: dual/密度拍内改参下一帧生效 —— 密度逐帧经 partCap 现算,
      // 配合 spawn 满额清单 + 下方 m 钳制; merge = 两轨皆 live 取 y 中点、缺口退 lead 末点 y
      // (与 spawn 同式 —— 缺口轨 shown=null 会落底边假中点, I10/D4), 单反馈色取 lead Lv 色
      // —— D3-c; lead = 只主导轨; both(默认) = 各活性轨一落位, 环不占粒子预算故 eff 为 0 也
      // 保留环落位)
      const eff = _qbFxAlloc(cfg.dual, _qbFxPartCap(fx.lv, cfg.particles), fx.lead);
      const spots = [];
      if (eff.merge > 0) {
        spots.push({ y: tr.up.live && tr.dl.live ? (yUp + yDl) / 2 : yOf(tr[fx.lead].shown),
          color: lvColor, specs: fx.specs.merge, n: eff.merge });
      } else if (cfg.dual === "lead") {
        spots.push({ y: fx.lead === "up" ? yUp : yDl, color: fx.lead === "up" ? tk.up : tk.down,
          specs: fx.specs[fx.lead], n: eff[fx.lead] });
      } else {
        if (fx.act.up) spots.push({ y: yUp, color: tk.up, specs: fx.specs.up, n: eff.up });
        if (fx.act.dl) spots.push({ y: yDl, color: tk.down, specs: fx.specs.dl, n: eff.dl });
      }
      const sides = _QB_FX_RING_SIDES[fx.lv] || _QB_FX_RING_SIDES[3];
      const ringT = _qbFxRingAt(t, fx.beatMs, fx.rMax);
      // —— 几何环(V2: 多边形扩张环, 边数 = lead 等级 3/6/8; 环心跟随末点; 轨道语义色) ——
      if (ringT && ringT.r > 0) {
        ctx.lineWidth = 1.5;
        ctx.globalAlpha = ringT.alpha;
        for (const sp of spots) {
          ctx.strokeStyle = sp.color;
          _qbFxPolyPath(ctx, tipX, sp.y, ringT.r, sides, 0);
          ctx.stroke();
        }
      }
      // —— N 环外圈辉光(白名单 ringOuter; blur = 配色上限 × q ≤ 上限, 同帧 ≤2 次 ≤ I9 的 3 次) ——
      if (neon && ringT && ringT.r > 0) {
        ctx.globalAlpha = q * ringT.alpha;
        ctx.strokeStyle = lvColor;
        ctx.lineWidth = 1;
        ctx.shadowBlur = Math.round(blurCap * q);
        ctx.shadowColor = lvColor;
        for (const sp of spots) {
          _qbFxPolyPath(ctx, tipX, sp.y, ringT.r + 3, sides, 0);
          ctx.stroke();
        }
        ctx.shadowBlur = 0;
        ctx.shadowColor = "transparent";
      }
      // —— 粒子(V3: 三/四/五边碎片本体轨道语义色, N 外圈描边着 Lv 色 —— 白名单 partOuter;
      //     三阶段: 爆发 ×4.5 / 拖尾减速透明 / 0.55×beat 后零绘制; t=0 首帧最亮与判定线同帧) ——
      if (cfg.layers.particles === true) {
        for (const sp of spots) {
          if (!sp.specs || !(sp.n > 0)) continue;
          const m = Math.min(sp.specs.length, sp.n);
          for (let i = 0; i < m; i++) {
            const ps = _qbFxParticleAt(t, fx.beatMs, fx.burstMs, sp.specs[i], carry);
            if (!ps || !(ps.alpha > 0)) continue;
            ctx.globalAlpha = ps.alpha;
            ctx.fillStyle = sp.color;
            _qbFxPolyPath(ctx, ps.x, ps.y, sp.specs[i].size, sp.specs[i].sides, ps.rot);
            ctx.fill();
            if (neon) {   // N 外圈描边(Lv 色, 纯描边不占辉光 blur 预算)
              ctx.globalAlpha = ps.alpha * q;
              ctx.strokeStyle = lvColor;
              ctx.lineWidth = 1;
              ctx.stroke();
            }
          }
        }
      }
      // —— glitch 水平切片(V2 glitch 档; palette 逐帧门控, 拍内切入/切出下一帧生效; ≤5 条
      //     1px 级 fillRect 右缘对齐, ±3px 正弦微震 ≤5px) ——
      if (fx.slices && cfg.palette === "glitch" && ens > 0) {
        ctx.fillStyle = eff.merge > 0 ? lvColor : (fx.lead === "up" ? tk.up : tk.down);
        for (const sl of fx.slices) {
          ctx.globalAlpha = sl.alpha0 * ens;
          ctx.fillRect(L + W - sl.len, sl.y + sl.dy0 * Math.sin(t / 45 + sl.ph), sl.len, 1);
        }
      }
      // —— N 判定线短亮段(白名单 judgeFlash: 活性轨末点 y ±10px; ≤0.33×beat 回落) ——
      if (neon) {
        ctx.globalAlpha = q;
        ctx.strokeStyle = lvColor;
        ctx.lineWidth = 2;
        for (const k of ["up", "dl"]) {
          if (!fx.act[k]) continue;
          const y = k === "up" ? yUp : yDl;
          ctx.beginPath();
          ctx.moveTo(L + W - 0.5, y - 10);
          ctx.lineTo(L + W - 0.5, y + 10);
          ctx.stroke();
        }
        // —— N 角落 Lv 徽标(白名单 lvBadge; 与环边数/粒子数同源的第三种分级信号 —— T5 联动) ——
        ctx.globalAlpha = 0.85 * q;
        ctx.fillStyle = lvColor;
        ctx.font = "9px ui-monospace, Consolas, monospace";
        ctx.textAlign = "right";
        ctx.textBaseline = "top";
        ctx.fillText("Lv." + fx.lv, L + W - 4, T + 4);
      }
      ctx.restore();
    },
    /* draw 装饰段(系列之上): lead 策略从属轨描边加亮(D3-a: 只加亮描边 + 小锚点; 语义色加宽
     * 半透明短段, 不着 Lv —— I10) -> 末点菱形锚(每活性轨一枚; D4 y 间距 <26px 时缩小但两轨
     * 各自保留; N 锚辉光 = 白名单 anchorHalo, 无 blur 低透明外圈菱形 —— blur 预算让给环外圈)。 */
    _qbDrawFxAnchor(u, tk) {
      const st = u._qbBeat;
      const a = st && st.anim;
      if (!a || a.phase === "tail" || !a.fx) return;
      const cfg = window.AQB_FX_CFG;
      if (!cfg || cfg.on !== true) return;
      const fx = a.fx;
      const t = a.clock;
      if (!(t < fx.beatMs * _QB_FX_PART_RATIO)) return;
      const px = this._qbCanvasScale(u);
      const ctx = u.ctx;
      const L = u.bbox.left / px;
      const T = u.bbox.top / px;
      const W = u.bbox.width / px;
      const H = u.bbox.height / px;
      ctx.beginPath();
      ctx.rect(L, T, W, H);
      ctx.clip();
      const dx = a.needsShift ? (a.lastDx || 0) : 0;
      const tipX = L + W + dx * fx.pxPerT;
      const yOf = (v) => T + H * (1 - Math.min(v, a.yMax) / a.yMax);
      const tr = st.tracks;
      const yUp = yOf(tr.up.shown);
      const yDl = yOf(tr.dl.shown);
      const q = _qbFxNeonQ(t, fx.beatMs);
      const neon = cfg.neon === true && q > 0;
      const ens = Math.max(0, 1 - t / (fx.beatMs * _QB_FX_PART_RATIO));
      const lvColor = _QB_FX_LV_COLORS[fx.lv] || _QB_FX_LV_COLORS[3];
      const rot = Math.PI / 4 + (Math.PI * 2 * t) / fx.beatMs;   // 旋转菱形(每拍一圈)
      // lead 策略从属轨: 末段描边加亮(读绘制面尾点插值 shown; y 钉定档下 yOf 与 uPlot 像素对位)
      if (cfg.dual === "lead") {
        const sub = fx.lead === "up" ? "dl" : "up";
        if (fx.act[sub]) {
          const col = u.data[sub === "up" ? 1 : 2];
          const xs = u.data[0];
          const i0 = Math.max(0, a.n - 3);
          ctx.globalAlpha = 0.45 * ens;
          ctx.strokeStyle = sub === "up" ? tk.up : tk.down;
          ctx.lineWidth = 3.5;
          ctx.beginPath();
          let started = false;
          for (let i = i0; i < a.n; i++) {
            if (col[i] == null) {
              started = false;   // 缺口断段: 与 spanGaps:false 逐段一致, gap 后重新 moveTo 不桥接
              continue;
            }
            const x = L + u.valToPos(xs[i], "x");
            const y = yOf(col[i]);
            if (!started) {
              ctx.moveTo(x, y);
              started = true;
            } else {
              ctx.lineTo(x, y);
            }
          }
          if (started) ctx.stroke();
        }
      }
      // 末点菱形锚(数据语义; D4: 重叠时缩小但两轨各自保留; lead 策略从属轨小锚)
      for (const k of ["up", "dl"]) {
        if (!fx.act[k]) continue;
        const y = k === "up" ? yUp : yDl;
        const role = cfg.dual === "lead" && k !== fx.lead ? 0.6 : 1;
        const r = 5 * role * fx.gapScale;
        ctx.globalAlpha = ens;
        ctx.fillStyle = k === "up" ? tk.up : tk.down;
        _qbFxPolyPath(ctx, tipX, y, r, 4, rot);
        ctx.fill();
        if (neon) {   // N 锚辉光(白名单 anchorHalo): 无 blur 低透明外圈菱形
          ctx.globalAlpha = 0.35 * q;
          ctx.strokeStyle = lvColor;
          ctx.lineWidth = 1;
          _qbFxPolyPath(ctx, tipX, y, r * 1.8, 4, rot);
          ctx.stroke();
        }
      }
      ctx.restore();
    },
    /* ================= 节拍调度器(S1, plan 26-11-12-1139 §03 L0/L1 + §06) =================
     * 判定帧 = 每次 _qbLoad 成功落袋(续拉快路 setData 之后同帧触发, 见 _qbChartBuild 快路)。
     * 每拍两件事, 驱动源解耦(D2):
     *   L0 视口偏置左移(I8, 数据刷新语义): 真窗口已 setData 落袋(data / _qbAnchors / tooltip
     *     全部真值), 绘制视口先摆回旧位置 setScale("x", {min: xs[0]-dx0, max: xs[n-1]-dx0}),
     *     再按 easeOut 在 shiftMs 内归零; 过渡期不重建 xs、不改 up/dl、不碰 _qbAnchors;
     *     收敛帧 setData(resetScales 默认 true) 显式交还 auto range。
     *   L1 双轨数值收敛(纯数据语义, 非装饰): 两列独立 {prev,target,shown,delta,level,live},
     *     尾点 n-1 在收敛窗(0.12-0.6 beat)内按 easeOut 从 prev 收敛到 target(u.data 绘制面,
     *     tooltip/悬停锚仍读 Vue points 真值 —— I4, 读数面与本插值面零交集), 收敛帧写回真值。
     * 短路: reduced-motion(AQB_FX_CFG.on === false 的 reduce 分量)退回原 setData 快路 + 瞬时
     * 左移, 无 rAF(I7); 总开关 enabled=false 不短路 —— L0/L1 照常执行(§05.6: 那是数据刷新
     * 语义, 不是装饰); 零变化拍(同网格滚动 + 两轨无真变化)零 rAF 瞬时落地。
     * 时间线常量与公式单点在模块级「节奏内核」节; 逐帧 commit 用 setScale/redraw(不 destroy/
     * new、不碰 loading 空态、不触发 ResizeObserver 连锁 —— I3)。
     * !rAF/performance.now/document 一律函数内惰性取(node 探针 eval 本文件, 顶层不得碰 BOM)。 */
    /* 判定帧开工(快路 setData 之后同帧调用): 打断在途旧拍(新拍以当前显示值接续, 禁止回跳 ——
     * I3) -> 推进双轨状态机(每拍必推, 不论动不动效 —— 状态机推进是数据面) -> 按需起 rAF。 */
    _qbBeatStart(scope, u) {
      if (!u || !u.root || !u.root.isConnected || !u.data || !u.data.length) return;
      const st = u._qbBeat;
      if (!st) return;  // 建图时初始化(见 _qbChartBuild); 无记录 = 异常旧图, 不动画
      this._qbBeatCancel(u);
      const xs = u.data[0];
      const n = xs.length;
      if (!n) return;
      const cfg = window.AQB_FX_CFG;
      // reduce 判定单点读 AQB_FX_CFG(S0-b 已带有效值 on = enabled && !reduce): on 为假有
      // 两个分量 —— reduce(系统要求减弱动效)才短路, enabled=false(用户关总开关)不短路
      const reduce = !!(cfg && cfg.enabled === true && cfg.on === false);
      // L0 几何: dx0 = 新窗起点 - 旧窗起点(uPlot distr=1 时间量纲, 已读 vendor 确认 setScale
      // min/max 走时间戳)。等距窗滚动 = 一格; 月行非等距/跨月按实差; 同网格(agg 桶未进新桶) = 0。
      // 跨窗换档(点数变化 = 重定标, 尾桶已不是同一个桶, 不播过渡)与多桶滚动(>2 格)瞬时落地。
      const rewin = st.n != null && st.n !== n;
      const dx0 = st.xs0 != null ? xs[0] - st.xs0 : 0;
      const step = n >= 2 ? xs[1] - xs[0] : 0;
      const roll = !rewin && dx0 > 0 && step > 0 && dx0 <= step * 2;
      st.xs0 = xs[0];
      st.n = n;
      // L1 判定推进(D2 双轨独立): 尾桶真值 -> {prev,target,shown,delta,level,live}
      const yTop = u.scales && u.scales.y && u.scales.y.max > 0 ? u.scales.y.max : 1;
      const floor = yTop * _QB_FX_VIS_FLOOR_RATIO;
      const tr = st.tracks;
      const tl = _qbBeatTimeline(this._qbPollMs(scope), cfg ? cfg.shiftRatio : undefined);
      tr.up = _qbFxTrackNext(tr.up, u.data[1] ? u.data[1][n - 1] : null, floor);
      tr.dl = _qbFxTrackNext(tr.dl, u.data[2] ? u.data[2][n - 1] : null, floor);
      if (reduce) {
        // I7: 真值已由快路 setData 落袋(u.data 即真值), 瞬时左移 = auto range 原生行为, 无 rAF
        tr.up.shown = tr.up.target;
        tr.dl.shown = tr.dl.target;
        return;
      }
      const px = (typeof uPlot !== "undefined" && uPlot.pxRatio) || 1;
      const cellPx = _qbFxCellPx(u.bbox && u.bbox.width > 0 ? u.bbox.width / px : 0, n);
      const needsShift = roll && _qbFxShouldShift(cellPx);
      const needsTail = !rewin && ((tr.up.live && tr.up.prev !== tr.up.target)
        || (tr.dl.live && tr.dl.prev !== tr.dl.target));
      if (!needsShift && !needsTail) {
        // 零变化拍/不可见位移拍: 瞬时落地(u.data 未被改写本就是真值), 零 rAF(D2 静默)
        tr.up.shown = tr.up.target;
        tr.dl.shown = tr.dl.target;
        return;
      }
      // I4 纵轴瞬时定档: 动画期每次提交都会让 uPlot 重推 y(vendor qn: Kl.x 非 null -> An(!0)
      // 重置 series.min/max -> y.auto 按可视窗重算) —— 可视窗随偏置滑动/显示尾值变化, y 会逐帧
      // 漂移(窗沿峰值出窗即整条曲线垂直跳)。按**新数据全窗真值**先算 yMax 钉住(与建图 range
      // 单点同口径: _qbYRange × _qbYCapOf, 不是显示尾值), 起拍与每个 shift 帧的 setScale("x")
      // 成对补 setScale("y")(Kl.y 非 null 时 qn 原样拷贝、跳过重推); 收敛帧 setData 交还 auto
      // 重推出的正是同一 yMax(真窗真值), 交还无跳变。须在尾点摆回显示值**之前**扫描(尾值真值
      // 参与峰值)。
      let dmax = 0;
      for (let c = 1; c <= 2; c++) {
        const col = u.data[c];
        if (!col) continue;
        for (let i = 0; i < n; i++) {
          const v = col[i];
          if (v != null && v > dmax) dmax = v;
        }
      }
      const yMax = _qbYRange(dmax, this._qbYCapOf(scope))[1];
      // t=0 同帧: 尾点摆回显示值(仅绘制面) + 视口摆回旧位置。两处写入都发生在 setData 的
      // 微任务渲染之前(同个同步块), 判定帧首绘即「旧位旧值」—— 与上一拍收敛帧逐像素接续(I3,
      // uPlot 同步块内多次 commit 会被 Un 标志合并成一次渲染, 已读 vendor 确认)。
      if (needsTail) {
        if (tr.up.live && tr.up.prev !== tr.up.target) u.data[1][n - 1] = tr.up.prev;
        if (tr.dl.live && tr.dl.prev !== tr.dl.target) u.data[2][n - 1] = tr.dl.prev;
      }
      if (needsShift) {
        u._qbTickFreezePending = true;  // 判定帧渲染时冻结 x 轴 ticks(§09「x 轴刻度每帧重算」)
        u.setScale("x", { min: xs[0] - dx0, max: xs[n - 1] - dx0 });
        u.setScale("y", { min: 0, max: yMax });  // 与 x 成对: 该提交不得按偏置可视窗重推 y
      }
      // S2-a 装饰状态(V1 色彩/V2 形状/V3 粒子/N 层/D3 仲裁, plan §03): t=0 一次性生成, 粒子/
      // 切片清单确定性伪随机(同拍重绘恒同形)。拍内改参的生效口径(§05.3/D21): neon/layers.
      // particles/tail/palette/dual 逐帧读 AQB_FX_CFG 下一帧生效; 密度(particles)经满额清单 +
      // 绘制侧逐帧钳制下一帧生效; 唯一例外 ease(消费点 S3 阶段接线, 当前改值无效果)。生效
      // 条件: cfg.on === true(有效值单点)且 lead 等级 ≥ 1 —— reduce 已在上方短路(I7);
      // enabled=false 与 Δ≈0/零流量/缺口轨零装饰但 L0/L1 照常(§05.6/D2/I10)。
      const fx = this._qbFxSpawn(u, tl, dx0, needsShift, yMax);
      st.anim = { dx0, needsShift, needsTail, n, tl, yMax, clock: 0, lastT: 0,
        lastDx: needsShift ? dx0 : null, fx, phase: "impact" };
      st.raf = requestAnimationFrame(() => this._qbBeatFrame(scope));
    },
    /* 每帧推进(判定帧同帧触发 I5; 每帧按真实毫秒推进): 页面隐藏 rAF 不触发 = 拍内时钟自然
     * 冻结(clock 只累计观察到的帧间隔), 恢复可见后从当前显示值接续, 不重播整拍。 */
    _qbBeatFrame(scope) {
      const u = this._qbCharts && this._qbCharts[scope];
      const st = u && u._qbBeat;
      if (!u || !st || !st.anim) return;
      st.raf = 0;
      if (!u.root || !u.root.isConnected) {
        this._qbBeatCancel(u);  // 宿主被拆(页签切走): 终止不留半帧; 回场走整图重建落真值
        return;
      }
      const a = st.anim;
      if (document.hidden) {
        a.lastT = 0;  // 隐藏期不推进; 置 0 让恢复后的首帧不吞隐藏时长(dt 从 0 起算)
        st.raf = requestAnimationFrame(() => this._qbBeatFrame(scope));
        return;
      }
      const now = performance.now();
      const dt = a.lastT > 0 ? Math.min(now - a.lastT, _QB_FX_FRAME_MAX_DT_MS) : 0;
      a.lastT = now;
      a.clock += dt;
      const tl = a.tl;
      if (a.phase === "tail") {
        // S2-a 次区相位: 流动光点逐帧推进(位置 1px 量化, 无可见变化不提交 —— 极轻面不逐帧
        // 全量重绘, I9 R8 复核); 页面隐藏已在上方冻结时钟, 光点随钟暂停
        if (this._qbTailFrame(u, a)) {
          st.anim = null;
          st.raf = 0;
          u.redraw();  // 末帧清理: 光点层随本次提交归零(钩子见 anim 已清 -> 零装饰)
          return;
        }
        st.raf = requestAnimationFrame(() => this._qbBeatFrame(scope));
        return;
      }
      if (a.clock >= tl.animEndMs) {
        this._qbBeatConverge(scope, u);
        return;
      }
      const xs = u.data[0];
      const n = a.n;
      // 逐帧提交守卫: dx 与尾点 shown 都没变的帧不提交(t=0 同帧已写过同值, 时钟未推进的恢复
      // 首帧亦然) —— setScale/redraw 每笔都是全量路径重建 + 钩子重跑(I9 R8 复核的帧成本),
      // 重复同值提交纯浪费。
      let dxChanged = false;
      let tailChanged = false;
      // L0: dx = (1 − easeOut(p)) × dx0, p = clamp(clock / shiftMs, 0, 1) —— 视口整体往过去
      // 偏置, p→1 时 dx→0(数据/锚/tooltip 全程真值, 只动视口 —— I4/I8)
      if (a.needsShift) {
        const dx = (1 - _qbFxEaseOut(a.clock / tl.shiftMs)) * a.dx0;
        if (dx !== a.lastDx) {
          a.lastDx = dx;
          dxChanged = true;
          u.setScale("x", { min: xs[0] - dx, max: xs[n - 1] - dx });
          u.setScale("y", { min: 0, max: a.yMax });  // 与 x 成对: 该提交不得按偏置可视窗重推 y
        }
      }
      // L1: 尾点收敛窗(0.12-0.6 beat)内 shown = prev + (target − prev) × easeOut(p), 单调
      // 无 overshoot(I4/D9); impact 窗(0-0.12 beat)内 shown 恒 = prev(冲击留给 S2 装饰)
      if (a.needsTail) {
        const p = _qbFxEaseOut((a.clock - tl.impactMs) / tl.convergeMs);
        const tr = st.tracks;
        if (tr.up.live && tr.up.prev !== tr.up.target) {
          const shown = _qbFxShown(tr.up, p);
          if (shown !== tr.up.shown) {
            tr.up.shown = shown;
            u.data[1][n - 1] = shown;
            tailChanged = true;
          }
        }
        if (tr.dl.live && tr.dl.prev !== tr.dl.target) {
          const shown = _qbFxShown(tr.dl, p);
          if (shown !== tr.dl.shown) {
            tr.dl.shown = shown;
            u.data[2][n - 1] = shown;
            tailChanged = true;
          }
        }
      }
      if (tailChanged && !dxChanged) {
        // 纯数值收敛帧(视口未动): redraw 内部的 setScale(x, current) 同样触发 y 重推 —— 显示
        // 尾值若是窗口唯一峰值, 重推出的 y 随插值逐帧缩、收敛帧再弹回(垂直跳); 先钉 y 再
        // redraw 成对盖住(钉值 = 真窗档位 yMax, 与收敛帧 auto 重推同值)。
        u.setScale("y", { min: 0, max: a.yMax });
        u.redraw();
      }
      // S2-a 装饰帧保障: 冲击窗(≤0.55×beat)内 L0/L1 都没提交的帧(无 shift 长窗的 impact 段,
      // 尾点显示值冻结在 prev)强制重绘一次, 否则粒子/环/切片冻结在 t=0 帧(I5: 冲击 t=0 同帧
      // 触发); y 钉成对同上(显示尾值参与可视窗重推会垂直跳)。
      if (a.fx && !dxChanged && !tailChanged && a.clock < a.fx.beatMs * _QB_FX_PART_RATIO) {
        u.setScale("y", { min: 0, max: a.yMax });
        u.redraw();
      }
      st.raf = requestAnimationFrame(() => this._qbBeatFrame(scope));
    },
    /* 次区相位帧(S2-a: tail 光点推进): 沿末段 _QB_FX_TAIL_SPAN_BUCKETS 个桶的折线缓动, 每轨
     * ≤2 个错峰光点(合计 ≤4, 轨道语义色, 极轻 alpha ≤0.35); 位置 1px 量化 —— 无可见变化不
     * 提交(全量路径重建是帧成本大头, 极轻面不逐帧重绘 —— I9 R8 复核)。返回 true = 次区结束
     * (窗尽/拍内关闭), 调用方清 anim 并补一帧清理提交。 */
    _qbTailFrame(u, a) {
      const tl = a.tl;
      if (!(a.clock < tl.beat + tl.tailMs)) return true;
      const cfg = window.AQB_FX_CFG;
      if (!cfg || cfg.on !== true || cfg.tail !== true) return true;
      const K = Math.min(_QB_FX_TAIL_SPAN_BUCKETS, a.n - 1);
      const pts = [];
      if (K >= 1 && a.clock >= tl.beat) {
        const p = Math.min(1, (a.clock - tl.beat) / tl.tailMs);
        const px = (typeof uPlot !== "undefined" && uPlot.pxRatio) || 1;
        const L = u.bbox.left / px;
        const T = u.bbox.top / px;
        const H = u.bbox.height / px;
        const xs = u.data[0];
        for (const k of a.fx.tail) {
          const col = u.data[k === "up" ? 1 : 2];
          for (let j = 0; j < _QB_FX_TAIL_PTS_MAX; j++) {
            const pj = p + j * 0.45;
            if (pj > 1) continue;   // 走完即隐(不循环 —— 次区是余韵, 不是常驻动画)
            const b = (a.n - 1 - K) + pj * K;
            const i = Math.floor(b);
            const f = b - i;
            const v0 = col[i];
            const v1 = col[i + 1];
            if (v0 == null || v1 == null) continue;   // 缺口段跳过(曲线断线处无光点 —— D4)
            const alpha = 0.35 * Math.min(1, p * 8) * Math.min(1, (1 - p) * 6);
            if (!(alpha > 0)) continue;   // 淡入前/淡出后零绘制
            const x0 = L + u.valToPos(xs[i], "x");
            const x1 = L + u.valToPos(xs[i + 1], "x");
            pts.push({
              k,
              x: x0 + (x1 - x0) * f,
              y: T + H * (1 - (v0 + (v1 - v0) * f) / a.yMax),
              alpha,
            });
          }
        }
      }
      const ft = a.fxTail;
      const sig = pts.map((pt) => pt.k + ":" + Math.round(pt.x) + "," + Math.round(pt.y)).join("|");
      if (sig === ft.sig) return false;   // 位置无可见变化: 时钟照常推进, 不提交
      ft.sig = sig;
      ft.pts = pts;
      u.redraw();
      return false;
    },
    /* 收敛帧: 真值写回 + 显式交还 auto range + x 轴 ticks 一次性刷新, 一次提交完成。
     * 交还方式已读 uPlot 1.6.x vendor 源确认: 无持久手动 range —— setScale 只往 pending 表
     * (Kl)写一次、下次提交即消费, setData(resetScales 默认 true) 走 xn() 从数据重推 x range
     * (auto 路径真实存在)并重算 y, 无需额外释放调用。 */
    _qbBeatConverge(scope, u) {
      const st = u._qbBeat;
      const a = st.anim;
      st.anim = null;
      st.raf = 0;
      const tr = st.tracks;
      const n = a.n;
      if (tr.up.live) u.data[1][n - 1] = tr.up.target;
      if (tr.dl.live) u.data[2][n - 1] = tr.dl.target;
      tr.up.shown = tr.up.live ? tr.up.target : null;
      tr.dl.shown = tr.dl.live ? tr.dl.target : null;
      u._qbTickFreeze = null;        // ticks 冻结清除: 本次提交即用真窗口现算标签(一次性刷新)
      u._qbTickFreezePending = false;
      u.setData([u.data[0], u.data[1], u.data[2]]);
      // S2-a 次区相位衔接(tail 开启且有活性轨): 主区装饰在本帧已全部回落(环/粒子 ≤0.55×beat、
      // N ≤0.33×beat —— 收敛帧零残留), 此处转入 tail 相位让次区光点沿末段曲线缓动到下一拍前
      // (窗长 tail = min(period − beat, 2000), 600s 长窗也只铺 2s, 非常驻)。拍内 cfg 在
      // _qbTailFrame 逐帧重读 —— 关闭即下一帧收尾(补一帧清理提交)。
      const tl = a.tl;
      const cfg = window.AQB_FX_CFG;
      if (a.fx && a.fx.tail.length && tl.tailMs > 0 && cfg && cfg.on === true && cfg.tail === true
        && u.root && u.root.isConnected) {
        st.anim = { phase: "tail", n: a.n, tl, yMax: a.yMax, clock: a.clock, lastT: 0,
          dx0: 0, needsShift: false, needsTail: false, fx: a.fx, fxTail: { pts: null, sig: "" } };
        st.raf = requestAnimationFrame(() => this._qbBeatFrame(scope));
      }
    },
    /* 终止在途拍(rAF 句柄先摘): _qbBeatStart 打断旧拍 / _qbChartDestroy 销毁 / 宿主被拆三条
     * 路共用的收口。「终止即落真值不留半帧」由各路径原生满足: 打断路新拍 setData 已落真值;
     * 销毁/换肤路整图重建即真窗口 auto range —— 不存在残留偏置的半帧。 */
    _qbBeatCancel(u) {
      if (!u || !u._qbBeat) return;
      const st = u._qbBeat;
      if (st.raf) {
        cancelAnimationFrame(st.raf);
        st.raf = 0;
      }
      st.anim = null;
    },
    _qbChartDestroy(scope) {
      if (!this._qbCharts) return;
      const u0 = this._qbCharts[scope];
      if (u0 && u0._qbBeat) this._qbBeatCancel(u0);  // S1: 终止在途节拍动画(rAF 先摘, 不留半帧)
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
      // 图区右键入口(R8 §05.2): 独立处理器 —— preventDefault + stopPropagation 拦住冒泡到
      // drawer.html:66 的 @contextmenu.prevent(四皮肤同验一次「图区右键只有一个面板」)。
      // !不碰 menu.js:223 的 openDrawerMenu 早退判据: 改了会让整片正文右键都弹出「只有一个
      //   模板选项」的半残菜单, 并撞 e2e/drawer-merge.spec.mjs 的 .ctx-menu strict-mode 计数。
      // 总开关关掉也照开(§05.6: 否则用户失去重新打开的入口)。
      // !宿主跨重建复用而 _qbChartDestroy 只断 RO/destroy uPlot、不摘 host 监听 -> _qbFxBound
      //   标记幂等绑定(换肤 N 次不弹 N 个面板, §05.7); 宿主 DOM 随 v-if 拆走时标记随节点消亡,
      //   重建的新宿主会重新走到这里再绑。
      if (!host._qbFxBound) {
        host._qbFxBound = true;
        host.addEventListener("contextmenu", (ev) => {
          ev.preventDefault();
          ev.stopPropagation();
          this.openFxPanel(ev.clientX, ev.clientY);
        });
      }
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
        prev._qbLimits = (d && d.limits) || [];  // 限速事件随快路同步换(否则变更要等整图重建才可见)
        prev.setData([data.xs, data.up, data.dl]);
        this._qbBeatStart(scope, prev);  // S1 判定帧: 真窗口已落袋, 同帧起拍(L0 左移 + L1 收敛)
        return;
      }
      this._qbChartDestroy(scope);
      this._qbChartInjectCss();
      this._qbAnchors[scope] = data.anchor;  // 悬停取值用(非响应式实例字段, 同 _qbAnchors 自身先例)
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
          { ...axis, values: (u, splits) => {
            // S1 动画期 x 轴 ticks 冻结(§09「x 轴刻度每帧重算」): L0 过渡期每帧 setScale 重算
            // splits + 标签(轴标抖动 + 每帧 Date 格式化开销) —— 判定帧渲染时把标签缓存进
            // u._qbTickFreeze, 过渡期恒返缓存; 收敛帧清除冻结, 一次性现算刷新。
            // 等长守卫: 过渡中 splits 数变化(视口跨刻度边界进/出一条刻度)即解除缓存回落现算,
            // 防标签与刻位错位(uPlot 绘制侧按同一索引对位 _splits 与 _values)。
            if (u._qbTickFreeze) {
              if (u._qbTickFreeze.length === splits.length) return u._qbTickFreeze;
              u._qbTickFreeze = null;
            }
            const labels = splits.map((ts) => this._qbTickLabel(ts, scope));
            if (u._qbTickFreezePending) {
              u._qbTickFreeze = labels;
              u._qbTickFreezePending = false;
            }
            return labels;
          } },
          // y 轴槽宽 84: fmtSpeed 轴标最长形("999.9 KiB/s"/"3.86 MiB/s" = 11 字符 x 10px 等宽
          // + 内边距), 60 会把标签左缘截掉(实测 "3.86 MiB/s" 只剩 "86 MiB/s") —— 三主题截图自查发现
          { ...axis, size: 84, values: (u, splits) => splits.map(fmtAxisSpeed) },
        ],
        series: [
          { label: "时刻", value: (u, ts) => this.fmtTime(ts) },
          {
            label: "上传", stroke: tk.up, width: 2,
            spanGaps: false,  // null 桶断线不连线(§5.2 拍板: 纯断线, 无最大跨越)
            points: { show: false, size: 6, filter: (u, sIdx) => _qbIsolatedIdxs(u, sIdx) },
            value: (u, v) => this.fmtSpeed(v),
          },
          {
            label: "下载", stroke: tk.down, width: 2,
            spanGaps: false,
            points: { show: false, size: 6, filter: (u, sIdx) => _qbIsolatedIdxs(u, sIdx) },
            value: (u, v) => this.fmtSpeed(v),
          },
        ],
        hooks: {
          // 注解层 + S2-a 视觉引擎(共享图面, 四挂点全生效, 不新增 canvas)。挂点层序已读 vendor
          // 1.6.32 源实证: 主渲染序 clearRect → Ci("drawClear") → Pl.forEach(axes → series) →
          // Ci("draw"), 且 Ci("drawAxes") 在 Dl.axes 函数**末尾**(网格/刻度/轴标画完之后)——
          // 即 drawAxes = **网格之后、系列原生之前**。故: drawClear = 缺口斜纹(恒最底, 与网格
          // 相互独立), drawAxes = 几何环/粒子/切片 → N 霓虹元素层(I6 层序: 装饰压网格不压曲线
          // —— 挂 drawClear 会被网格盖住, 评审 blocker 实证), draw = 系列之上(限速虚线 → lead
          // 从属轨加亮 + 末点菱形锚)。曲线描边由 uPlot 系列原生画在 drawAxes 之后 = 装饰永远
          // 不压曲线(语义色一行不动 —— I10/D1)。tk 由本次建图捕获 —— 令牌换肤走整图重建,
          // 钩子随新图换新 tk。
          drawClear: [(u) => this._qbDrawGaps(u, tk)],
          drawAxes: [(u) => this._qbDrawFx(u, tk)],
          draw: [(u) => this._qbDrawLimits(u, tk), (u) => this._qbDrawFxAnchor(u, tk)],
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
      u._qbLimits = (d && d.limits) || [];  // 限速事件暂存在图记录上(u.data 只有三列, D4 数据通路)
      // S1 节拍底座初值(图记录面, 同 _qbLimits 款不进 Vue state): 拍时钟/视口偏置空, 双轨以
      // 建图数据尾点为显示值(首拍 prev 接续 = 建图尾值, 领先沿不回跳), ticks 冻结未挂
      u._qbBeat = {
        raf: 0,
        anim: null,
        xs0: data.xs[0],
        n: data.xs.length,
        tracks: {
          up: _qbFxTrackNext(null, data.up[data.up.length - 1], 0),
          dl: _qbFxTrackNext(null, data.dl[data.dl.length - 1], 0),
        },
      };
      u._qbTickFreeze = null;
      u._qbTickFreezePending = false;
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
