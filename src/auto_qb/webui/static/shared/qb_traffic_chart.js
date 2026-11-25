/* auto-qb WEB UI · qB 口径流量图(uPlot 双系列组件, 三挂点)
 *
 * plan 26-10-03-0946 方案C §07 P5a/P5b。一个「双系列(上传/下载)时间曲线」封装, 三图(全局/单种/
 * 分组)共用: uPlot options 样板(axes/series/scales/cursor)收在 _qbChartBuild 单点, 调用方只给
 * points + 容器; 缺口点(旧契约 null 桶 / schema=2 显式空值点) = 断线不连线(uPlot spanGaps:false, §5.2 拍板语义)。
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
 * SSE 主路径 + 低频对账(T4a, plan 26-11-18-0037 阶段 3; D7/D9/E1/E4/E7): 打开期间 per-scope
 * 一条 SSE 流(/api/traffic/qb/stream?scope=…&ticket=…, 事件驱动判定帧)—— 每帧 {seq, scope,
 * points} 为 per-tick 样本真值, 显示列 = GET 组点列 + 事件尾点替代推进(步进); 30s 对账 GET
 * (E4)与断档/静默重拉(D9)把列折叠归位到组粒度。列与视口几何由**尾锚显式视口三不变量**承载
 * (计划 26-11-22-0858 换代, 根治三轮 x 向压缩补丁的类问题):
 *   (1) 视口恒等式 viewport = [anchor − span_s, anchor] —— 锚 = 末样本时刻、单调递增; 视口
 *      永不从数据跨度现推(auto x range 全窗退役, 判定帧/收敛帧/rescale 一律显式 setScale
 *      重申), 压缩在结构上不可表达;
 *   (2) 单列恒等 —— store 列 == 显示列(补点/_qbPad 记账/悬停扣减/收敛 slice 退役), 列 =
 *      [锚 − (span_s + margin), 锚](margin = 2×组距; 修剪线锚 = 视口锚优先、尾点回落 ——
 *      锚领先尾时列仍覆盖视口左缘, G-B 防回潮; GET 落地经 _qbStreamOnLoad 历史保留合并回填,
 *      keepLine 同锚优先);
 *   (3) 取数有效性 —— _qbLoad 发射时快照窗口名, 落袋前比对(stale 判据窗口分量), 旧窗口在途
 *      响应不得覆盖新窗数据(换窗竞态的 R3 取证根因)。
 * 对账 GET 落袋撞上在途滑动拍时按**打断续滑**消费(判定帧从在途锚 _qbAnimAnchorAt 续滑到
 * 本拍目标 —— 自身状态直读, 零回跳); GET 轮询骨架(_qbPollStart, 间隔从
 * meta.sample_interval_s 夹取)保留为**降级态**取数路径(E7: 票据满额 503 / 连续重连失败);
 * 页面隐藏不停流(帧照常合并, 渲染节流 —— 见 SSE 节头注); 关闭/切走形态/登出由
 * _stopDrawerPoll / _qbTeardown 显式收流收轮询 —— 只挂打开期间, 不后台常驻。
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
 * —— L0 锚平移(视口 [anchor − span, anchor] 两缘同步, 锚从旧值 easeOut 滑向新值; 打断从
 * 在途锚续滑)+ L1 双轨数值收敛(两列独立插值尾部 1 点, 收敛帧写回真值)。纯函数(公式/时间线/
 * 状态机/锚判定)在模块级「节奏内核」节, 调度器在 methods 域 _qbBeat*; 动画期 x 轴右缘刻位
 * 过滤与 tooltip 真值接缝等判据见各处注。
 *
 * 视觉引擎 V + N 霓虹元素层(S2-a, plan §03 V 表/N 节/D1-D4): 同画布装饰面 —— V1 分级色相
 * (Lv 色表常量, 四皮肤无 --qb-lv* 令牌已核查)/V2 多边形扩张环 + 旋转菱形锚 + glitch 切片/
 * V3 三阶段多边形粒子(两轨合计 ≤32)+ 次区流动光点; N 层白名单(Lv 色相, cfg.neon 独立开关),
 * D3 双轨仲裁(both/lead/merge)与 D4 末点 y 间距缩小。图层顺序 I6 单点
 * _QB_FX_LAYER_ORDER, 背景零铺色(I11/G7), 曲线描边恒语义色一行不动(I10/D1); 纯函数(仲裁/
 * 预算/粒子运动/回落阈值)在模块级「视觉引擎」节, 绘制在 methods 域 _qbDrawFx/_qbDrawFxCurveGlow/
 * _qbDrawFxAnchor(drawAxes/draw 钩子, 不新增 canvas), 装饰帧挂节拍调度器循环内(无独立循环)。
 *
 * T6 综合表现层(S2-b, plan §03 T6 行/D17-D19 + §02 R5/R6/R7): 在 S2-a 引擎上补齐 T6 五层 ——
 * T2 光带爬升(cfg.layers.band: 末点插值 shown 的渐变光带两轨各自画, 读数过渡不占装饰预算;
 * N 数值光带辉光 bandHalo 仅 lead 一道, 同帧 blur 描边 <=5: 环外圈 <=2 + 光带 1 + 曲线辉光 2
 * (_qbDrawFxCurveGlow 全程常驻 + 视口裁剪))+ T4 扫描束
 * (_qbDrawFxScan: 双相位六层束 —— 亚像素硬核/六层晕/色散/彗尾/梳齿/回声, 束体逐帧 ≤23 指令,
 * 回声越线 span=clamp(0.22×绘图宽,100,200) px 按 pow(1−d/span,0.85) 距离衰减、到点几何硬停;
 * 束体 clip 放宽到画布右缘 —— 判定线右侧留白是相位 A「滑入」与右向结构的可见域, 段尾自含
 * save/scale 落笔不嵌绘图区 clip)+ R6 横向线条(撕裂切片 2/3/5 条与梳齿 3/5/7 条按 lead 等
 * 级, hash01(拍序号,槽位) 分层采样定长相, 色池故障色为主)+ T5 分级联动收口(grade 层关 =
 * N 层/扫描束恒 Lv.1 色, 束宽度感按等级 ×0.9/1/1.1); 抽屉入场 rAF 追赶循环在途时切片与微震
 * 暂停(§09 让位)。
 *
 * 常驻菱形锚(F2, plan 26-11-14-1313 §03 F2/D2): 末点旋转方块的**常驻环境层**改走 CSS 合成器
 * —— 两枚 .qb-fx-anchor DOM 方块挂 uPlot .u-wrap, keyframes 2639ms linear infinite(模板 rot=t/420
 * 是弧度/ms, 一圈 2*pi*420=2639ms; 旧 420ms/圈系单位误读, 快约 6.3 倍 —— D6/C1), 零 rAF/零重绘
 * (D2: 旋转走合成器, 不进 draw 循环; 背景恒静态, 菱形是 DOM 元件不引入
 * 画布铺底 —— G5/R4); 画布侧菱形本体移除(避免双画), N 锚辉光(anchorHalo)保留画布侧拍内脉冲
 * (C7 改 tipX 末点滑动 x, 与 DOM 常驻锚短暂分离属预期)。位置同步点收敛四处(R3): 判定帧 _qbBeatStart /
 * 收敛帧 _qbBeatConverge / 锚钩子 _qbDrawFxAnchor 顶部(每次画布提交顺路重写)/ ResizeObserver;
 * _qbFxCfgSync 汇入门面(cfg.on / palette 变化即时生效; D4 曲线宽 2.4/calm 2 也在该面现写)。
 * 门 = cfg.on===true 且图活跃, 缺口轨
 * 隐藏(I10 模板 live 门同款); reduced-motion 双保险(cfg.on 已含 !reduce + CSS 媒体查询隐藏
 * —— P2: 隐藏不是静态方块); calm 档 border-radius 退化圆点(模板 isCalm 同款)。CSS 经
 * _qbChartInjectCss 单点注入(四皮肤零侵入); 元件随图建/随图清(_qbChartDestroy 显式清记录,
 * 元件本体在 u.root 内随 u.destroy 拆除 —— 换肤/重建零残留)。
 *
 * 列余量与左缘连续性(尾锚显式视口换代, 计划 26-11-22-0858; F5 补尾格机制退役): 视口左缘
 * (anchor − span)滑动期由**余量列**承担裁剪数据 —— 列 = [anchor − (span+margin), anchor]
 * (margin = 2×组距; 修剪线视口锚优先、尾点回落 —— _qbStreamFrame 修剪线), GET 落地清空余量
 * 时由 _qbStreamOnLoad 历史保留合并回填(旧 store 列 < 新列头且 ≥ 余量线的真值点并入)。消灭
 * G-B「左缺口瞬移」不再靠显示层补点/摆回(26-11-21-1704 数据面剪 + F5 显示层补的双层结构合成
 * 单层数据不变量), 视口左缘滑动期恒有真实历史可裁。伴随判定换代(_qbAnchorJudge 单点): 跨窗
 * 换档 = 组距标称/名义窗长变化 或 锚位移 > 2 组距滚动域(防假 morph 语义承袭) —— 其余位移拍
 * 一律锚滑动(打断续滑同路, 旧「roll 伪真继承」特判退役); instant/reduce 档的恒定压缩变体
 * (补点永不摘)随补点退役自然消失(上档案 26-11-22-0626 D4 就此收口)。
 *
 * 面板接线(S3, plan §05.3/§05.4/§06 S3 行 + D21): cfg.ease 消费端 —— 数值插值曲线选择单点
 * _qbFxCurve, 判定帧冻结进 anim.easeF(拍内不换式, 下一拍起用), 帧循环经 _qbFxShown 单次施加
 * (L1 专用; L0 与装饰运动曲线恒 easeOut); cfg.shift 消费端 —— instant 对照档判定帧跳过 L0
 * 过渡(数据语义不变); 「预览一拍」—— _qbPreviewBeat/Restore/End 与真实拍同构但不动窗口
 * (dx ≡ 0), 假 Δ 贴真实量级、连点重启令牌、真值抢占、不写 store、同 I9 预算、不自动循环;
 * 状态行「上次真实拍 Xs 前」(fxBeatAt/fxNow + 1s 步进时钟, 仅面板开着走)与「· 预览中」
 * (fxPreviewing 镜像, 翻转沿写 —— 动画态本体在图记录, Vue 只留显示镜像)。
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
 * 顶沿之上, 自然不画)+ 缺口斜纹(缺口点游程铺 45 度斜纹, 画在系列之下)。
 * !2026-10-08 修「缺口斜纹几乎不可分辨」: 斜纹原走 tk.grid(--hairline, alpha 仅 0.05~0.08 的
 * 装饰性 1px 发丝线令牌), 再叠 globalAlpha 0.5 => 有效不透明度约 3%, 深色底上等于没画(亮主题
 * 同理)。改走**专用高对比令牌 --qb-gap-hatch**(0.18~0.25), 并去掉多余的 globalAlpha 折半;
 * 几何(斜纹覆盖区间)经逐条线段比对与代数验证**与原式恒等**, 未变。
 * 画布坐标口径见 _qbCanvasScale 注(uPlot 1.6.x ctx 无 transform, 坐标 = 设备像素)。
 */
/* global uPlot */

/* 轮询间隔边界(ms): 夹取下界 = 配置校验下限 1.5s(§06, A4: 采样间隔下限放宽后同步对齐),
 * 上界 = 配置校验上限 600s(纯防御夹取 —— 正常配置恒不触界)。F7(plan 26-11-15-1104 D6)
 * 起轮询读 meta.sample_interval_s(生效采样间隔, 后端 _meta 装配单点全窗携带)全窗统一,
 * 「低频轮询 = 桶宽」旧口径(interval_s, 长窗一拍迟钝至 30s~174s)正式反转 —— 上界不再是
 * hour 段窗桶宽的续拉语义, 只防后端异常值; meta 缺失/非法回退 30s 常量(plan §07「采样
 * 间隔」基准值)。 */
const _QB_POLL_MIN_MS = 1500;
const _QB_POLL_MAX_MS = 600000;
const _QB_POLL_FALLBACK_MS = 30000;

/* SSE 主路径常量(plan 26-11-18-0037 T4a; D9/E4/E7 —— 模块常量不进配置, D5 硬切无配置键):
 *   对账 30s(_QB_STREAM_RECONCILE_MS): 流活着也低频 GET 全量校准一次, 事件尾点(瞬态样本
 *     粒度)由 GET 折叠归位到组粒度(D9/E4);
 *   静默 _QB_STREAM_SILENCE_X x si: 流开着但无新帧超过 3 个采样间隔 -> 徽标「滞后 Ns」
 *     (诚实等待, R7: 主循环停顿不是故障, 不谎报断连)+ 静默沿立即 GET 重拉一次;
 *   重连 3s(_QB_STREAM_RETRY_MS, 照 polling.js 一次性票据换新票重开同拍)+ 连续失败上限
 *     _QB_STREAM_FAIL_MAX(=3 轮票据/握手/建流, ~9s): 连续失败即降级 GET 轮询(E7);
 *   降级恢复 _QB_STREAM_RETRY_DEGRADE_MS(60s, 保守侧): 降级期 GET 轮询在供数, 每分钟静默
 *     重试一次流, 成功即回 SSE 主路径(轮询退役); 页面重开抽屉(重入 _qbStreamStart)亦可;
 *   事件尾点预算(_QB_RAW_POINTS_MAX + _QB_STREAM_TAIL_HEADROOM): 事件样本点是「未折叠」的
 *     瞬态粒度(显示列 = GET 组点列 + 事件尾点), 正常态 30s 对账折叠归位(30s/si <= 20 点,
 *     远触不到); 双通道同故障(GET 死而流活)时从头截断防无界增长(防御面, 窗口大幅滑动走
 *     _qbAnchorJudge 的滚动域外 rewin 瞬时落地, 无动画假象);
 *   watchdog 1s 步进(_QB_STREAM_WATCHDOG_MS): 徽标文案秒级刷新 + 静默沿判定(经骨架
 *     startPoll, document.hidden 恒等守卫兜隐藏期零更新)。 */
const _QB_STREAM_RECONCILE_MS = 30000;
const _QB_STREAM_SILENCE_X = 3;
const _QB_STREAM_RETRY_MS = 3000;
const _QB_STREAM_FAIL_MAX = 3;
const _QB_STREAM_RETRY_DEGRADE_MS = 60000;
const _QB_STREAM_WATCHDOG_MS = 1000;
const _QB_RAW_POINTS_MAX = 500;
const _QB_STREAM_TAIL_HEADROOM = 64;

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
 * 旧观感对照档(模板保真二轮 A2 回退恢复整幅口径 —— 模板 demo:1152-1158; 面板提示行标
 * 「旧观感对照」, 枚举面不改)。 */
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
 * stream(t) = SSE 订阅 scope 串(/api/traffic/qb/stream?scope=…, T4a: global 原样 /
 * torrent: 前缀 + hash / group: 前缀 + key —— 与后端 _parse_scope 三形态同语法, 前端不自行
 * 编码); active = 该图此刻是否应显示/可拉(建图守卫 + 轮询 tick 跳过判据同源); stale = 在途响应
 * 回落时是否已过期(不落袋, 对齐 drawer.js _drawerStale 代际纪律)。
 * host 三挂点统一为 qbChartHost: 三形态互斥(同一时刻只渲染一个), 正文块共用(drawer.html)。 */
const _QB_SCOPES = {
  global: {
    host: "qbChartHost",
    window: "qbHistWindow", data: "qbHistData", loading: "qbHistLoading", error: "qbHistError",
    hoverIdx: "qbHistHoverIdx", hoverLeft: "qbHistHoverLeft", yaxis: "qbHistYAxis",
    url: (_ctx, w) => "/api/traffic/qb/global?window=" + w,
    stream: () => "global",
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
    stream: (t) => "torrent:" + (t.drawer.hash || ""),
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
    stream: (t) => "group:" + (t.qbGroupKey || ""),
    ctx: (t) => t.qbGroupKey,
    // page 守卫与 global 同(drawerVisible 单点): 非主内容页面板不在 DOM, 不拉不画
    active: (t) => t.drawerIsTraffic && t.drawer.open && t.page === "groups"
      && t.drawer.scope === "group",
    // 同 torrent: 谓词是否定式, 同一波改名里一并被写成 `!!(...)`(同一处缺陷, 一并修复)
    stale: (t, k) => !(t.qbTrafficOn && t.drawerIsTraffic && t.drawer.open
      && t.drawer.scope === "group" && t.qbGroupKey === k),
  },
};

/* 点列 -> uPlot 数据(模块级纯函数, 供 node 单测探针, 同 hrsCompareRows 先例)。
 * schema=2 样本分组契约(raw 段窗, 26-11-18-0037 D6/E3): points = [{t, dl, up}, ...] 升序
 * 每点必带 t(组末样本 ts; 缺口 = 显式空值点 {t, dl:null, up:null}; 尾组 = 最新样本 ts, 恒
 * 真值)—— 三列**直读**: xs[i] = points[i].t, 空值点 y = null(uPlot spanGaps:false 断线)。
 * 旧「桶值 | null」定长数组(agg 段窗 3d+, D4 零改动)仍兼容: null 元素没有 t, 沿旧栅格
 * 重建(锚 = 首个非 null 点, 真值点按 t 落点覆写; null 槽 x 在两真值点之间线性内插、窗端
 * 外侧按 interval 等距外推 —— all 月行按行间隔非等距, 真值点恒按真值落点)。
 * 空列(后端已归一为 points: [], 防御)或 interval 非法(旧契约内插需要; 新契约纯直读也一并
 * 防御) -> null(调用方回落空态)。anchor = { xs } 全列真值时刻(悬停取值锚, _qbBucketTs 消费)。 */
function _qbPointsToData(points, interval) {
  const n = points.length;
  if (!n || !(interval > 0)) return null;
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
  if (!known.length) return null;
  let seg = 0;  // 已消费的真值段游标(known 有序, 单遍推进)
  for (let i = 0; i < n; i++) {
    if (seg < known.length && known[seg] === i) {
      xs[i] = points[i].t;  // 真值直读(新契约每点必带 t; 旧契约非 null 桶按真值落点)
      seg++;
    } else if (seg === 0) {
      // 旧契约(agg 段窗)首个真值点前的外推(新契约无 null 元素, 本支不达)
      xs[i] = points[known[0]].t - (known[0] - i) * interval;
    } else if (seg >= known.length) {
      // 旧契约末尾外推(同上)
      xs[i] = points[known[known.length - 1]].t + (i - known[known.length - 1]) * interval;
    } else {
      const a = known[seg - 1], b = known[seg];  // 旧契约两真值点之间线性内插(同上)
      xs[i] = points[a].t + (points[b].t - points[a].t) * (i - a) / (b - a);
    }
  }
  return { xs, up, dl, anchor: { xs } };
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

/* 缺口游程(连续缺口点的 [起, 止] 索引对; 模块级纯函数供 node 单测)。
 * 判据 = **上下载皆 null**(schema=2 显式空值点 {t, dl:null, up:null} 与旧契约 null 桶经
 * _qbPointsToData/_qbPointsColumns 转列后同为双 null; 单列 null 防御性不误判成缺口)。 */
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

/* 数据链边界: 首/末个非空点下标(全系列无观测 -> [-1, -1]) —— 「数据链」= 本帧实际
 * 有观测的那段连续区间(显式空值点/旧契约 null 桶转列后皆双 null, 不算观测)。
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
/* points([{t, dl, up} | null]) -> 画布同形状的两列([up], [dl]); hover 侧因此能直接复用
 * _qbChainBounds/_qbGapZone(与 _qbDrawGaps 直读 u.data[1]/u.data[2] 同判据)。
 * schema=2 样本分组契约下 points 元素恒为字典(显式空值点 = 双 null 列位); 旧契约 null 桶
 * 元素照旧转双 null —— 两种形态共用同一缺口判据(E3)。 */
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
 * issue 26-10-16-0954; 右沿改真值 t 直读 26-11-18-0037 阶段 3): 「数据链末点早于右沿且重启
 * 贴近链末」 -> 返回 { startedAt }, 否则 null。
 * - 数据链末点 = 最后一个**有真值**的点(schema=2 显式空值点 {t, dl:null, up:null} 与旧契约
 *   null 桶都不算观测 —— 按列值判, 不按元素真值判); 尾部未观测区存在 <=> 末非空下标
 *   < n-1(链已到右沿 = 无尾区, 不提示 —— 正常尾组观测不是缝);
 * - 重启贴近链末 <=> meta.server_started_at(后端进程出生时刻, traffic_qb._SERVER_STARTED_AT)
 *   ∈ [链末点前一个组距起点 t-interval, 右沿] 内(左端含)。原口径左端 = 链末覆盖端 t+interval,
 *   其隐含前提「链末晚于重启时刻 => 链已接续、无误读面」在「重启后首采已入账、随后立即
 *   进入开放零游程」形态下不成立(实测帧: 重启 04:45:01 -> 首采 04:45:02, 04:45:04 起整片
 *   缺口到右沿却零提示): 首采(恒落在重启后 <= 一个 main_tick)总归进链末组, 但尾区仍在 ——
 *   「链在重启处断」与「重启后首采即链末」在组粒度上不可分, 左端须放宽一个组距; 反方向
 *   链末点起点晚于重启 + 1 个组距以上 = 链确已接续, 不提示。重启晚于右沿(末点真值 t)=
 *   链在重启前已断/重启尚未产生观测, 不提示属预期(断连语义走徽标面, 不混读 —— D3);
 * - 右沿 = 末点真值 t(schema=2 每点必带 t, 尾部显式空值点的 t 即缺口折叠位 —— 旧等距外推
 *   (n-last)*interval 退役); 旧契约末桶无 t(agg 段窗 null 元素)时按 interval 等距外推承袭;
 * - meta 无新键(旧后端)/全空/interval 非法 -> null(不猜, 向后兼容: 旧前端忽略新键,
 *   新前端遇旧后端也不提示)。all 月视图非等距, 端点用标称月长近似 —— 但月视图
 *   末桶(当前月)由活尾 pending 行常态覆盖(last == n-1), 实际不达判据面。 */
function _qbSeamHint(points, interval, meta) {
  if (!meta || !(Number(meta.server_started_at) > 0) || !(interval > 0)) return null;
  const n = points.length;
  let last = -1;
  for (let i = n - 1; i >= 0; i--) {
    const p = points[i];
    if (p && (p.up != null || p.dl != null)) {
      last = i;
      break;
    }
  }
  if (last < 0 || last >= n - 1) return null;  // 全空(空态面)/链已到右沿: 无尾部未观测区
  const started = Number(meta.server_started_at);
  const chainPrevStart = points[last].t - interval;  // 链末点前一个组距起点 = 判据左端(重启与链末不可分带下界)
  const lastP = points[n - 1];
  const rightEdge = lastP && Number(lastP.t) > 0
    ? lastP.t  // 右沿 = 末点真值 t(新契约每点必带 t —— 26-11-18-0037 阶段 3)
    : points[last].t + (n - last) * interval;  // 旧契约末桶无 t: 等距外推承袭(agg 段窗)
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
 * 图记录(u._qbBeat = 拍时钟/视口偏置/双轨 tracks), 不进 Vue state —— 同
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
const _QB_FX_CONV_END_RATIO = 0.60; /* converge 收敛窗 = 0 .. 0.60 × beat(t=0 起步, impact 窗不再钉 prev; B5/D1) */
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
    convergeMs: convEnd,   // 0.6×beat: p=clock/convergeMs 自 t=0 起步(impact 窗不再钉 prev)
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
/* linear 缓动(ease 枚举 "linear" 的曲线单点, S3): 恒等映射, 越界夹取口径与 out 一致 ——
 * 数值插值直线收敛(对照档: 用户想看不受减速塑形的原始插值)。 */
function _qbFxLinear(p) {
  const q = p <= 0 ? 0 : p >= 1 ? 1 : p;
  return q;
}
/* ease 曲线选择单点(S3, plan 26-11-12-1139 §05.3 ease 行 + D21 唯一例外条款): 数值插值曲线
 * 按 cfg.ease 选取 —— "out" = _qbFxEaseOut / "linear" = _qbFxLinear, 未知值防御回落 out(与
 * _qbFxSanitize 枚举白名单同口径)。拍内不换式: 判定帧(真拍 _qbBeatStart / 预览 _qbPreviewBeat)
 * 读一次 cfg.ease, 曲线引用冻结进 anim.easeF, 帧循环与收敛插值只消费冻结引用 —— 拍中改值
 * 下一拍起用, 当前拍不换式(避免中途换曲线造成位置跳变)。消费域只限 L1 尾点数值收敛
 * (§05.3 ease=数值插值曲线): L0 视口左移与环/粒子/束等装饰运动曲线恒 _qbFxEaseOut, 不随
 * ease 变。 */
function _qbFxCurve(ease) {
  return ease === "linear" ? _qbFxLinear : _qbFxEaseOut;
}
/* L0 最小可见位移规则: 单格像素 = 绘图宽(CSS px) / 点数, < 0.75px 的位移肉眼不可辨 —— 该拍
 * 直接瞬时落地(等同 instant), 只短窗播放 L0 过渡(24h 长窗 2880 点 × ~800px ≈ 0.28px/格恒瞬时,
 * 省掉每帧全量路径重建的帧成本, 见 §09「逐帧性能」与 I9 R8 复核)。量不到绘图宽(首绘前)按 0
 * 处理 = 瞬时, 宁可不动画不可错动画。 */
const _QB_FX_CELL_MIN_PX = 0.75;
/* L0 末帧视口吸附阈值(rem 剩余比例): easeOut 三次曲线在 p→1 时 rem=(1-p)^3 缓慢趋零,
 * dx=rem×位移 令 x.min=锚−dx 停在刻度整数边界前一丁点。uPlot time splits 按该残差
 * 视口取整, 首刻位低一格(1850→1849), 下一帧钳零精确落锚点又恢复(1849→1850) —— 单帧
 * 刻位/网格线回跳(issue 26-11-17-0936)。
 * 阈值 1e-3(2026-11-17 第五次取证上调, 原 1e-4 不足): 真机捕获 clock=425 帧 rem=1.71e-4
 * 越过 1e-4 未钳零, 残差仅 0.00026s(0.011px)却令 splits 首刻位换一格(整条网格线跳 ~106px)。
 * 根因是「残差是否跨刻位边界」的二值问题, 非残差大小 —— 0.011px 的残差肉眼不可见, 但足以
 * 让 splits 换格。1e-3 覆盖该帧(1.71e-4)及前一帧(4.05e-4)提前钳零, 几何偏差
 * 上限 1e-3×位移(30m 最坏 4.5s=4.5ms, 24h 174s=0.174s)在各自视口下均 <0.01px。
 * 单点消费面 = _qbAnimAnchorAt(锚视口重构后帧循环与打断续滑共用, 旧 dx0/dxMin0 分离记账退役)。 */
const _QB_FX_L0_SNAP_REM = 1e-3;
/* x 轴右缘刻位容差(issue 26-11-17-0936 第三次纠正): 绝对下限 1e-9 兼容小时间域, 相对项
 * |vMax|×1e-12 覆盖 1.7e9 秒级挂钟上钳零后 1e-3 秒量级微越界。splits 末位 < vMax - eps
 * 才画 —— 恰好压在 vMax 上的整点不再多出一条最右纵线。 */
const _QB_X_SPLIT_EPS = (max) => Math.max(1e-9, Math.abs(max) * 1e-12);
/* x 轴 splits 生成器包装(建图后挂, 模块级纯函数供 node 电池): uPlot 1.6.x 未导出默认
 * splits generator, 但建图时已把默认生成器规范化写进 axes[0].splits —— 取来包一层即可。
 * 丢掉 >= vMax - eps 的右缘刻位, 让网格线数不随 vMax 是否精确压整点而 12↔13 翻转
 * (L0 钳零令收敛帧 vMax 偶尔精确落 5s 整点, 下一拍退 1.5s 又消失 = 每两拍跳一次)。
 * 透传全部原签名实参, 不碰 uPlot 内部; 返回新数组, 不修改生成器原结果。 */
function _qbDropRightEdgeSplits(generator) {
  return function (u, axisIdx, min, max, incrs, foundSpace, forceDelta) {
    const raw = generator.call(this, u, axisIdx, min, max, incrs, foundSpace, forceDelta) || [];
    const eps = _QB_X_SPLIT_EPS(max);
    return raw.filter((v) => v < max - eps);
  };
}
/* 拍内单帧 dt 上限(ms): 掉帧/长停顿吞进一帧不跳变过半拍(隐藏暂停另有 document.hidden 判定,
 * 时钟在隐藏期根本不累计 —— 见 _qbBeatFrame)。 */
const _QB_FX_FRAME_MAX_DT_MS = 100;
function _qbFxCellPx(plotCssWidth, nPoints) {
  return nPoints > 0 && plotCssWidth > 0 ? plotCssWidth / nPoints : 0;
}
function _qbFxShouldShift(cellPx) {
  return cellPx >= _QB_FX_CELL_MIN_PX;
}
/* 锚视口判定单点(尾锚显式视口重构, 计划 26-11-22-0858; 模块级纯函数供 node 电池)。
 * 三不变量: (1)视口恒等式 viewport = [anchor − span, anchor](anchor = 末样本时刻, 单调递增;
 * auto x range 全窗退役 —— 视口跨度恒等名义窗, 压缩在结构上不可表达); (2)单列恒等(store 列 ==
 * 显示列, 列 = [anchor − (span + margin), anchor], margin = 2 组距; 修剪线视口锚优先、
 * 尾点回落); (3)取数有效性(_qbLoad stale 判据窗口分量)。本 judge 把「数据位移判定」收敛为
 * **锚位移**: 组距标称或名义窗长变化(换窗/采样档变更/重定标)或锚位移超出 2 组距滚动域(缺口
 * 折叠多格补拍/停摆补齐) -> rewin 瞬时落地(防假 morph 语义承袭); 其余位移拍 slide(锚滑动
 * 动画候选 —— 是否真滑再由 cellPx/shift 档决定, 见 _qbFxShiftGate)。
 * 入参 st = 图记录 _qbBeat(anchor/step/span 跨拍记账), tail = 新列末样本 t, stepNom/spanNom =
 * meta 组距标称/名义窗长(缺/非法回落 st 记账 —— 防御, meta 恒在场时不达)。
 * 输出: anchor = max(st.anchor, tail)(单调 —— 旧窗响应晚到不回拖视口, 与取数窗口分量互为
 * 双防线) / delta = anchor − st.anchor / rewin / slide = !rewin && delta > 0。 */
function _qbAnchorJudge(st, tail, stepNom, spanNom) {
  const step = Number(stepNom) > 0 ? Number(stepNom)
    : (st && st.step > 0 ? st.step : 0);
  const span = Number(spanNom) > 0 ? Number(spanNom)
    : (st && st.span > 0 ? st.span : 0);
  const anchor = st && st.anchor > 0 ? Math.max(st.anchor, tail) : tail;
  const delta = st && st.anchor > 0 ? anchor - st.anchor : 0;
  const rewin = !!(st && st.anchor > 0
    && ((st.step > 0 && step > 0 && st.step !== step)
      || (st.span > 0 && span > 0 && st.span !== span)
      || (step > 0 && delta > step * 2)));
  return { anchor, delta, step, span, rewin, slide: !rewin && delta > 0 };
}
/* 在途锚现值单点(打断续滑; 模块级纯函数供 node 电池): 滑动拍在 anim.clock 时刻的锚位 =
 * anchorFrom + easeOut(clock/shiftMs) × 位移, 末帧 ulp 吸附钳(rem < 阈值精确落锚 ——
 * issue 26-11-17-0936 口径承袭: 残差视口令 uPlot time splits 首刻位低一格的单帧回跳)。
 * 消费面两处共用本单点(公式漂移即打断续滑回跳): _qbBeatFrame 逐帧提交 + _qbBeatStart 打断
 * 捕获(新拍 anchorFrom = 在途锚现值 —— 自身状态直读, 不读 uPlot scales: setScale 攒 pending
 * 滞后一帧的 vendor qn 语义与本面无关, 旧 _qbInheritedViewport 公式重建随列亲和约束一并退役
 * —— 锚不依赖列形状, 捕获时机无 setData 约束)。 */
function _qbAnimAnchorAt(a) {
  const e = _qbFxEaseOut(a.clock / a.tl.shiftMs);
  const anchor = a.anchorFrom + (a.anchorTo - a.anchorFrom) * e;
  return (1 - e) < _QB_FX_L0_SNAP_REM ? a.anchorTo : anchor;
}
/* L0 滑动门(模块级纯函数): 滑动 = 锚位移拍且单格像素达可见阈值且非 instant 对照档 ——
 * cellPx 按**名义窗点数**(span/step)计, 与列余量解耦(余量点不参与像素密度, 24h 长窗恒
 * 瞬时的判据面承袭)。reduce 分量在调用方先行短路(判定帧 reduce 早退在门之前)。 */
function _qbFxShiftGate(cfg, u, nWin) {
  const px = (typeof uPlot !== "undefined" && uPlot.pxRatio) || 1;
  const cellPx = _qbFxCellPx(u.bbox && u.bbox.width > 0 ? u.bbox.width / px : 0, nWin);
  return _qbFxShouldShift(cellPx) && !(cfg && cfg.shift === "instant");
}
/* GET 落地历史保留合并(左缘裁剪数据面; 模块级纯函数供 node 电池):
 * GET 整列替换会把余量列清空(后端响应 = 名义窗 [t0, t1], 窗外前缀不产组点), 下一笔滑动若恰
 * 被本 GET 打断在途, 视口左缘落在列首左侧 -> 左缺口(G-B)。保留: 旧 store 列中小于新列头且
 * >= 余量线的真值点(真实历史观测, 与后端窗首回看同源, 不造数)并入列头 —— 数据层等价替代
 * 补点携带(F5 退役), 无状态无门; 未打断(锚已收敛)时新列头 == 视口左缘, 保留集恒空(零成本)。
 * 返回保留点数组(引用旧列点对象 —— 点 dict 只读共享); 调用方 concat 在新列头部(保留点 t 全
 * 小于新列头, 升序不破)。 */
function _qbRetainHistory(oldPts, newPts, keepLine) {
  if (!oldPts || !oldPts.length || !newPts || !newPts.length) return [];
  const head = Number(newPts[0] && newPts[0].t);
  if (!(head > 0)) return [];
  const out = [];
  for (const p of oldPts) {
    const t = Number(p && p.t);
    if (t > 0 && t < head && t >= keepLine) out.push(p);
  }
  return out;
}
/* L1 双轨状态机(R3, §03 L1 底座; 纯函数面供 node 电池)。每轨 {prev, target, shown, delta,
 * level, live}, 两轨独立推进(D2), 状态本体存 u._qbBeat.tracks:
 *   prev   = 上拍显示值(shown 接续, 禁止回跳 —— I3); 上拍轨死(shown null)即复活, 无从接续
 *            直落真值(不造斜坡 —— 从 0 缓升是撒谎)
 *   target = 本拍尾桶真值; null = 缺口 -> live=false, 轨静默不插值(D4)
 *   shown  = 当前显示值(动画期按 cfg.ease 选定的曲线向 target 收敛, 缺省 easeOut —— S3; 收敛帧
 *            = target)
 *   delta  = |target − prev| / max(prev, 可视下限) —— 可视下限由调用方按 y 轴可视尺度传入
 *            (floor = y 轴顶值 × _QB_FX_VIS_FLOOR_RATIO), 防 prev≈0 时相对变化爆炸
 *   level  = Δ 分档: live 且 target>0 时恒 ≥Lv.1(F1/D1, plan 26-11-14-1313: 生产尾桶是未完成
 *            桶, 同桶内相邻轮询速率漂移恒 <0.5%, 旧「Δ<0.5% 静默」让稳态流整段静默 —— 下限
 *            只是把既有视觉预算用起来, Δ 分档上限语义不变: <5% Lv.1 / <30% Lv.2 / 其余 Lv.3);
 *            真 0(target==0, 零流量)与缺口轨(live=false)维持 Lv.0 静默(D2/A3) */
const _QB_FX_DELTA_SILENT = 0.005;
const _QB_FX_LEVEL1_DELTA = 0.05;
const _QB_FX_LEVEL2_DELTA = 0.30;
/* 可视下限占 y 轴可视顶值的比例(S1 状态机无装饰消费面, 数值 S2 联调时可调) */
const _QB_FX_VIS_FLOOR_RATIO = 0.02;
function _qbFxLevel(delta, live, target) {
  if (!live) return 0;   // 缺口轨(live=false)静默(D2)
  if (target != null && !(target > 0)) return 0;   // 真 0(target==0)与异常负值静默(D2/A3)
  const hasTarget = target != null;   // 生产形态(_qbFxTrackNext/预览拍恒传); 缺参回落旧口径(向后兼容)
  if (!(delta >= _QB_FX_DELTA_SILENT)) return hasTarget ? 1 : 0;   // F1(D1): 活跃轨(值>0)恒 ≥Lv.1 下限
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
    level: _qbFxLevel(delta, true, target),
    live: true,
  };
}
/* 收敛插值(纯函数): prev -> target 按曲线 ease(p) 收敛(单次应用 —— p 由调用方传**原始进度**,
 * 曲线选择单点 _qbFxCurve 在判定帧冻结后经 anim.easeF 传入, 缺省 out), 恒落在
 * [min(prev,target), max(prev,target)] 内, 单调无 overshoot(I4/D9)。ease 只在这里施加一次
 * (S3 接线: 帧循环不再预折算 —— 与计划 §03 公式 shown = prev + (target−prev)·easeOut(p)
 * 同构); ease 越界夹取让 impact 窗(原始进度为负)与超窗帧自然落在 prev/target 端点。 */
function _qbFxShown(track, p, ease) {
  return track.prev + (track.target - track.prev) * (ease || _qbFxEaseOut)(p);
}

/* ---------------- 视觉引擎 V + N 霓虹元素层 + T6 表现层(S2-a/S2-b, plan 26-11-12-1139 §03 V 表/N 节/T6 行/D1-D4/D17-D19) ----------------
 * 本节是装饰面的常量与模块级纯函数单点(node 电池直接真跑, 同节奏内核先例); 带副作用的绘制面在
 * methods 域: _qbDrawFx(drawAxes 钩子 = uPlot 网格之后、系列原生之前: T2 光带 → 几何环/粒子/
 * 撕裂切片 → N 霓虹元素层, 段尾 restore 后再调 _qbDrawFxScan 扫描束 —— 束体自含 save/scale
 * 且 clip 放宽到画布右缘, 判定线右侧留白是相位 A「滑入」的可见域, 层序仍先于系列(I6))与
 * _qbDrawFxCurveGlow(draw 钩子 = 系列之上: 曲线辉光全程常驻 + 严格绘图区视口裁剪, 无时间窗
 * 无 tail 门)与 _qbDrawFxAnchor(draw 钩子 = 系列之上: 末点菱形锚 + lead 策略从属轨描边加亮), 装饰帧挂在
 * 节拍调度器的 rAF 循环内(无独立循环 —— 调度器每帧提交即重跑钩子, L0/L1 提交帧顺路带出装饰)。
 * !clip 口径(F5, plan 26-11-14-1313): _qbDrawFx 与 _qbDrawFxAnchor 的 clip 右缘放宽到画布右缘
 * (rect(L, T, max(W, canvasW-L), H), 同 _qbDrawFxScan 评审 blocker 修复先例 —— 判定线右侧留白
 * 是环/粒子/菱形锚的可见域, 无轴面内容); 曲线辉光 _qbDrawFxCurveGlow 例外用严格绘图区
 * rect(L,T,W,H) clip(不放宽 —— R2 裁剪口径: 不画进判定线右留白); 左缘/上缘/下缘不动, 近底由环心上抬钳制与粒子底缘
 * 镜像反弹承接(P3 拍板), 菱形锚(数据标记)保持真位不钳。
 * 生效条件(I7/§05.6): cfg.on === true(有效值单点 = enabled && !reduce)且该轨 level ≥ 1 ——
 * 真 0(target==0)/缺口轨零装饰但 L0/L1 照常(D2/I10); 值>0 的活跃轨恒 ≥Lv.1(F1/D1, plan
 * 26-11-14-1313 —— 只是让既有预算被用到, 上限不抬); N 层独立开关 cfg.neon(I11), T6 四层开关
 * cfg.layers.band/particles/scan/grade(逐帧读, 拍内改参下一帧生效), 次区光点 cfg.tail,
 * 三策略 cfg.dual, 密度 cfg.particles, 配色 cfg.palette, 束强度 cfg.impact, 回声行程
 * cfg.echoSpan, 对照档 cfg.tear(spawn 判定帧定型 —— 清单冻结面, 非逐帧)。 */

/* I6 图层顺序常量(违反即判失败; 单点描述, 绘制落位已读 vendor 1.6.32 源实证: 主渲染序
 * clearRect → drawClear → axes(网格) → drawAxes → series → draw, 其中 Ci("drawAxes") 在
 * Dl.axes 末尾 = 网格之后、系列之前): bg = 零铺色恒由 CSS 提供, grid/判定线 = uPlot 网格 +
 * _qbDrawGaps 缺口斜纹(drawClear 段), geometry/neon = _qbDrawFx(drawAxes 段 = 网格后系列前),
 * curve = uPlot 系列原生(画在 drawAxes 之后 = 装饰永不压曲线, 语义色一行不动), anchor =
 * _qbDrawFxAnchor(draw 段), hud = DOM tooltip/图例(本引擎零触碰)) */
const _QB_FX_LAYER_ORDER = ["bg", "grid", "geometry", "neon", "curve", "anchor", "hud"];

/* I11 N 层白名单(可着 Lv 色的局部元素; bandHalo = T2 数值光带辉光, S2-b 随光带层接入)/
 * 黑名单(恒与静态基线逐像素一致, 本引擎零触碰 —— 曲线描边恒 --today-up/down 由
 * _qbChartTokens 现读; 背景/网格/tooltip/图例/限速虚线不染) */
const _QB_FX_N_WHITELIST = ["judgeFlash", "ringOuter", "partOuter", "anchorHalo", "lvBadge", "bandHalo"];
const _QB_FX_N_BLACKLIST = ["curveUp", "curveDl", "plotBg", "edgeBg", "grid", "tooltip", "legend", "limitDash"];

/* V1 Lv 色表(plan §03 V1 色彩行逐字: Lv.1 蓝 #7AD9FF / Lv.2 金 #FEFFA9 / Lv.3 品红 #FF6BD6,
 * 沿用 Phigros AP 金 / FC 蓝)。!四皮肤均无 --qb-lv* 令牌(落表前已核查 atlas/prism/console/
 * flux 全部样式面), canvas 热路径也不逐帧 getComputedStyle —— 故按计划色值常量落 shared 层
 * (来源 = plan §03 V 表 V1 行); 色相语义是「这一拍多强」的分级反馈色, 不属皮肤语义色面,
 * 换肤不变; 绝不替代曲线语义色(I10/D1)。 */
const _QB_FX_LV_COLORS = { 1: "#7AD9FF", 2: "#FEFFA9", 3: "#FF6BD6" };

/* V1 三档配色 shadowBlur 上限(I9): glitch 14 / neon(常规) 10 / calm 0。同帧辉光(blur)描边
 * 修订预算 <=5(S3 口径): 扩张环外圈(至多 2 次) + T2 数值光带辉光 bandHalo(仅 lead 轨 1 道)
 * + 曲线辉光 2 道(_qbDrawFxCurveGlow, 全程常驻 + 视口裁剪, 轨语义色); 锚辉光用无 blur 低透明外圈六边环
 * (白名单 anchorHalo), 粒子外圈/判定线短亮段不加 blur。 */
const _QB_FX_BLUR_CAPS = { neon: 10, glitch: 14, calm: 0 };

/* V2 冲击环边数映射(由 lead 等级决定): Lv.1 三边 / Lv.2 六边 / Lv.3 八边 */
const _QB_FX_RING_SIDES = { 1: 3, 2: 6, 3: 8 };

/* C1/D6 常驻菱形锚旋转周期(2*pi*420 取整 —— 模板 rot=t/420 是弧度/ms, 一圈 = 2*pi*420 ~ 2639ms;
 * 旧 CSS 420ms/圈系单位误读, 快约 6.3 倍)。本常量为 CSS 注入与注释的单点来源(S3 已接线:
 * _qbChartInjectCss 用本常量现算动画周期, 不再写死 420ms)。 */
const _QB_FX_ANCHOR_SPIN_MS = 2639;

/* I9 视觉预算常量(R3: 全部按 up + dl 两轨合计, 不每轨各配一套): 粒子 ≤32 / 每轨半套 ≤16 /
 * N 层 ≤0.33×beat 回落 / 粒子活跃窗 ≤0.55×beat / 末点 y 间距 <26px 反馈按比例缩小(下限 0.4
 * —— 不合并不取消, D4) / 切片 ≤5 条(R6)且微震 ≤5px(实际 ±3px) / 次区光点每轨 ≤2(合计 ≤4)。
 * 冲击类窗 I9 逐元素窗改判(模板保真二轮, plan §01 修订表): 旧「>0.55×beat 冲击类叠加层零
 * 绘制」单一判据退役, 改逐元素窗 —— 粒子 0.55(不动) / 环 0.6(B3) / 切片 0.25(C2) / 束体+
 * 彗尾+梳齿 0.7(B2) / 光带 0.7 顶门内画 alpha 0.6×beat 后自然归零(B1); 顶层门 0.7×beat 只做
 * 「最大窗」粗滤, 逐元素窗在各自块内。 */
const _QB_FX_PART_MAX = 32;
const _QB_FX_SHARD_MAX = 16;
const _QB_FX_NEON_RATIO = 0.33;
const _QB_FX_PART_RATIO = 0.55;
/* 冲击环窗(B3 模板保真二轮): 0.6×beat(模板 demo:1294; 粒子仍 0.55 不动 —— I9 逐元素窗改判) */
const _QB_FX_RING_RATIO = 0.6;
/* 顶层门最大窗(B 类改判): 0.7×beat —— 三个装饰段(_qbDrawFx/_qbDrawFxScan/_qbDrawFxAnchor)
 * 共用的粗滤门, 只做「最大窗」, 各元素窗在各自块内(I9 逐元素窗改判) */
const _QB_FX_TOP_RATIO = 0.7;
/* 撕裂切片独立窗(C2 模板保真二轮): 0.25×beat(模板 demo:1091 同式), q 由绘制侧现算 */
const _QB_FX_SLICE_RATIO = 0.25;
/* 束体 fade 窗(B2 模板保真二轮): 0.7×beat(模板 demo:1173 fade=(1−t/(0.7beat))^1.4 同式) */
const _QB_FX_BEAM_RATIO = 0.7;
const _QB_FX_Y_GAP_PX = 26;
const _QB_FX_Y_GAP_MIN_SCALE = 0.4;
const _QB_FX_SLICES_MAX = 5;
const _QB_FX_SLICE_SHAKE_PX = 3;
const _QB_FX_TAIL_PTS_MAX = 2;

/* ---- T4 扫描束 + R6 横向线条 + T2 光带(S2-b, plan §03 T4/T6 行 + R6 节/D17-D19) ---- */
/* R6 横向线条条数按 lead 等级(T5 联动): 撕裂切片 2/3/5(≤5 = _QB_FX_SLICES_MAX)/梳齿 3/5/7
 * —— 横向细线条合计 ≤12 条/帧(I9-R6: 切片 ≤5 + 梳齿 ≤7), 束体+切片合计 ≤28 条/帧 */
const _QB_FX_TEAR_COUNT = { 1: 2, 2: 3, 3: 5 };
const _QB_FX_COMB_COUNT = { 1: 3, 2: 5, 3: 7 };
/* 撕裂切片配色池(色序 = Lv 色 / 品红 / lead 语义色, 约 45%/35%/20% —— 故障色为主, 语义色为主
 * 会与 lead 曲线同色隐身, §03 R6 色义行; 品红同时是扫描束色散第二色, 共用一常量) */
const _QB_FX_TEAR_MAGENTA = "#FF4D9D";
/* T4 束体六层晕(宽 -> 窄递进, 低 alpha 叠层逼近高斯 —— R5 重做束; 宽 px × 晕 alpha)。
 * 模板保真二轮(A2 回退): 束「宽度感」等级系数(Lv.1 0.9/Lv.2 1/Lv.3 1.1)退役 —— 模板无
 * 宽度感系数, 六层晕恒按表内宽度落笔; T5 分级联动只剩色相(lvColor)与梳齿条数。 */
const _QB_FX_BEAM_HALO = [[34, 0.035], [24, 0.05], [16, 0.08], [10, 0.13], [5, 0.22], [2.5, 0.38]];
/* T6 内束强度 ×0.78(R5 D17: 与 T2/T3/T5/T1 共享同一判定帧, 五层叠加需守合计预算), 再乘
 * cfg.impact 滑杆(面板冲击强度 0-1, 本参数的引擎消费面自 S2-b 起在束上) */
const _QB_FX_BEAM_INTENSITY = 0.78;
/* T4 双侧色散色(青/品红, ±1.6px, 仅前 0.5beat —— R5: 替代旧「青->品红整条渐变」) */
const _QB_FX_DISPERSION = ["#5CF2E8", "#FF4D9D"];
/* T2 光带(plan §03 T2 行): 峰值 alpha 基数 ×(1−pConv)×cfg.impact / 描边宽 px / N 辉光
 * (bandHalo)alpha 基数 ×q */
const _QB_FX_BAND_ALPHA = 0.7;
const _QB_FX_BAND_WIDTH = 4;
const _QB_FX_BAND_HALO_ALPHA = 0.5;
/* R7/D19 回声行程: span = clamp(0.22 × 绘图宽, 100, 200) px; 相位窗 0.18–0.45beat 匀速;
 * 距离衰减 pow(1 − d/span, 0.85); d ≥ span 几何硬停(零绘制, 不是 alpha 逼近 0); alpha ≤0.20 */
const _QB_FX_ECHO_SPAN_RATIO = 0.22;
const _QB_FX_ECHO_SPAN_MIN = 100;
const _QB_FX_ECHO_SPAN_MAX = 200;
const _QB_FX_ECHO_PHASE_LO = 0.18;
const _QB_FX_ECHO_PHASE_HI = 0.45;
const _QB_FX_ECHO_FADE_POW = 0.85;
const _QB_FX_ECHO_ALPHA_CAP = 0.2;
/* 回声 9px 淡晕 alpha(B4 模板保真二轮): 0.34×fall(模板 demo:1246 同式 —— 旧 0.20 上限对晕
 * 退役, I9 修订表已记; 1px 包络核仍 ≤0.20×fall×a0 即 _QB_FX_ECHO_ALPHA_CAP 不变) */
const _QB_FX_ECHO_HALO_ALPHA = 0.34;

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
 * 基数按等级 6+7×lv = 13/20/27(D5 模板保真二轮: 模板 demo:911 同式; Lv.1 仍发射 —— P9 拍板
 * 兼容; clamp 32 预算保留, 基数 27 触顶); density ≤ 0 或非法 = 0 粒子(密度关到底即无粒子)。 */
function _qbFxPartCap(level, particles) {
  const d = Number(particles);
  if (!(level >= 1) || !Number.isFinite(d) || d <= 0) return 0;
  const base = 6 + 7 * Math.min(3, level);
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

/* 冲击扩张环(V2 -> 模板保真二轮 C3+B3 重写): pf = t/(0.6×beat) 线性推进(不 easeOut —— 模板
 * demo:1294 同式), r = (4+24×pf)×rScale×gapScale(起步半径 4 线性扩到 28), alpha =
 * 0.85×(1−pf)×impact×rScale×gapScale; pf ≥ 1 -> null(环窗 0.6×beat —— B3 放宽)。
 * rScale = 半套系数(both 0.5 各轨半套 / lead 1 / merge 1 —— 模板 demo:1388-1390);
 * gapScale = D4 y 间距缩小(生产保留, 模板无); impact = cfg.impact 面板冲击强度(模板
 * S.impact 同源)。返回 { r, alpha, pf } —— pf 供绘制侧外圈独立扩张(S2 接线)复用。 */
function _qbFxRingAt(t, beat, rScale, gapScale, impact) {
  const T = beat * _QB_FX_RING_RATIO;
  if (!(t >= 0) || !(t < T)) return null;
  const pf = t / T;
  const s = Math.max(0, Number(rScale) || 0) * Math.max(0, Number(gapScale) || 0);
  const imp = Math.min(1, Math.max(0, Number(impact) || 0));
  return { r: (4 + 24 * pf) * s, alpha: 0.85 * (1 - pf) * imp * s, pf };
}

/* V3 粒子三阶段运动/亮度(纯函数): 爆发期 [0, burstMs) 速度 ×4.5(= impact 窗), 拖尾期
 * [burstMs, 0.55×beat) 名义速度 ×1 并 easeOut 减速; t ≥ 0.55×beat -> null(零绘制)。
 * 速度 v 由末态行程反解: 4.5v×burstMs + v×trailMs = dist(easeOut(1)=1)。亮度(C8 模板式)
 * 0.78×(1 − t/T)×impact(模板 demo:1073 同式, t=0 首帧最亮与判定线闪光同帧 —— I9); 自旋
 * t/260+idx 匀速单向(模板同式; rot0/vr 伪随机双向自旋字段退役 —— C8); carryPx = L0 视口
 * 回摆带来的末点位移(粒子随末点滑动, 与曲线不脱钩); idx = 粒子在清单中的序号(绘制侧
 * specs[i] 的 i, 自旋相位的唯一来源)。 */
function _qbFxParticleAt(t, beat, burstMs, spec, carryPx, idx, impact) {
  const T = beat * _QB_FX_PART_RATIO;
  if (!(t >= 0) || !(t < T)) return null;
  const trailMs = Math.max(T - burstMs, 1e-9);
  const v = spec.dist / (4.5 * burstMs + trailMs);
  const d = t <= burstMs
    ? 4.5 * v * t
    : 4.5 * v * burstMs + v * trailMs * _qbFxEaseOut((t - burstMs) / trailMs);
  const imp = Math.min(1, Math.max(0, Number(impact) || 0));
  return {
    x: spec.x0 + Math.cos(spec.ang) * d + carryPx,
    y: spec.y0 + Math.sin(spec.ang) * d,
    alpha: 0.78 * (1 - t / T) * imp,
    d,
    rot: t / 260 + (idx | 0),
  };
}

/* 粒子喷射清单(V3): n 个三/四/五边多边形碎片(非圆点 —— Beat Saber 碎片/Phigros 几何碎片),
 * 喷射角均匀铺满左向 270° 弧(45°..315°, 0°=+x 指向右缘外 —— 末点贴判定线, 右向碎片全被绘图
 * 区裁剪白费; D2 拍板保留左弧)加 ±5° 抖动, 尺寸 1.6-4.2px(C8 模板式 1.6+rnd×2.6)/ 行程
 * 1.1-1.6 × 环最大半径。自旋不进清单: rot = t/260+idx 绘制侧现算(C8 匀速单向, rot0/vr
 * 伪随机双向自旋字段退役)。确定性: 同种子恒同清单(node 电池真跑)。 */
function _qbFxSpawnSpecs(n, x0, y0, rMax, seed) {
  const rnd = _qbFxRand(seed);
  const out = [];
  for (let i = 0; i < n; i++) {
    const ang = (45 + (270 * (i + 0.5)) / n + (rnd() - 0.5) * 10) * Math.PI / 180;
    out.push({
      x0, y0, ang,
      sides: 3 + Math.floor(rnd() * 3),
      size: 1.6 + rnd() * 2.6,
      dist: rMax * (1.1 + 0.5 * rnd()),
    });
  }
  return out;
}

/* ---- R6 横向线条 + T4 束体数学(S2-b, plan §03 R6 节/D18 + §02 R5/R7; 纯函数 node 电池真跑) ---- */
/* hex(#RRGGBB) -> rgba() 串: 渐变 stop 与低 alpha 描边需要带 alpha 的色值(Lv 色表与语义色都是
 * hex 常量); a 钳 [0,1], 非 hex 输入原样返回(语义令牌万一非 hex 不炸装饰层)。 */
function _qbFxFade(hex, a) {
  const m = /^#([0-9a-fA-F]{6})$/.exec(hex);
  const al = Math.min(1, Math.max(0, Number(a) || 0));
  if (!m) return hex;
  const n = parseInt(m[1], 16);
  return "rgba(" + ((n >> 16) & 255) + "," + ((n >> 8) & 255) + "," + (n & 255) + "," + al.toFixed(3) + ")";
}
/* 确定性伪随机(R6/D18): 同一(拍序号, 槽位)永远同一 [0,1) 值 —— 每拍长相不重复但可复现可断言。
 * 整数乘法哈希 + 雪崩终混; 与 plan §04 原型公式的差异 = Math.imul(真 32 位乘)与无符号 >>>:
 * 原型的带符号 >> 版本实测输出 90% 落 [0,0.5)(乘法只向下混合, 低 16 位弱), 45/35/20 色池配比
 * 失真 —— 本式分布 45.1/35.0/19.8, 电池分布断言守。 */
function _qbFxHash01(a, b) {
  let h = (Math.imul(a | 0, 374761393) + Math.imul(b | 0, 668265263)) | 0;
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  h ^= h >>> 16;
  return (h >>> 0) / 4294967296;
}
/* 分层采样(R6): 第 i 条落在第 i~i+1 层内 —— 每拍不重复、又不会聚成一堆或飞出带外 */
function _qbFxStrat(i, n, r) {
  return (i + r) / Math.max(1, n);
}
/* tear 横向线条随机源单点(R6/D18): linked(生产默认) = hash01(拍序号, 槽位) / fixed = 恒 0.5
 * (每拍同形 —— R5 常量几何对照) / random = Math.random(每拍乱跳且不可复现 —— 仅对照档,
 * NOT reproducible; 消费点在 spawn 判定帧一次, 清单冻结故拍内不闪)。 */
function _qbFxTearRnd(mode, bi, slot) {
  if (mode === "fixed") return 0.5;
  if (mode === "random") return Math.random();
  return _qbFxHash01(bi, slot);
}
/* T5 分级联动色相单点(S2-b 收口): grade 层开 = N 层/扫描束/切片池的 Lv 色随 lead 等级;
 * grade 关 = 恒 Lv.1 色(§04 原型 lvColor() 语义: S.grade === false 返回 pal()[1] —— 分级
 * 只留边数/粒子数, 不再变色)。 */
function _qbFxLvColor(lv, gradeOn) {
  if (gradeOn !== true) return _QB_FX_LV_COLORS[1];
  return _QB_FX_LV_COLORS[lv] || _QB_FX_LV_COLORS[3];
}
/* 回声行程(R7/D19): span = clamp(0.22 × 绘图宽, 100, 200) px 且不超绘图宽; echoSpan="full"
 * (R5 整幅扫掠对照档, 存储白名单放行)恢复模板口径整幅 s=w(模板 demo:1152-1158; 面板标
 * 「旧观感对照」, 仅对照档观感 —— QB_FX_ENUMS 注)。 */
function _qbFxEchoSpan(mode, plotW) {
  const w = Number(plotW);
  if (!Number.isFinite(w) || !(w > 0)) return _QB_FX_ECHO_SPAN_MIN;
  let s;
  if (mode === "full") {
    s = w;   // A2 回退: 整幅对照档恢复模板口径(降格 auto 语义退役 —— 模板 demo:1152-1158)
  } else if (mode === "100" || mode === "150" || mode === "200") {
    s = Number(mode);
  } else {
    s = Math.min(_QB_FX_ECHO_SPAN_MAX, Math.max(_QB_FX_ECHO_SPAN_MIN, w * _QB_FX_ECHO_SPAN_RATIO));
  }
  return Math.max(1, Math.min(s, w));
}
/* 回声距离衰减(D19): ∝ pow(1 − d/span, 0.85); d ≥ span 恒 0 —— 几何硬停信号(调用方零绘制,
 * 不是把 alpha 压到看不见)。负 d 钳 0(越线前不产生 >1 的反放大量; 起拍窗由 echoQ > 0 门控)。 */
function _qbFxEchoFall(d, span) {
  const dd = Math.max(0, Number(d));
  const sp = Number(span);
  if (!Number.isFinite(dd) || !Number.isFinite(sp) || !(sp > 0) || dd >= sp) return 0;
  return Math.pow(1 - dd / sp, _QB_FX_ECHO_FADE_POW);
}
/* 回声相位进度(D19): 0.18–0.45 beat 匀速(原 easeOut 会把位移先冲完、淡出挤在最后几十毫秒)
 * -> q ∈ [0,1], 行程 d = span × q。 */
function _qbFxEchoQ(t, beat) {
  const b = Number(beat);
  if (!Number.isFinite(b) || !(b > 0)) return 0;
  const q = (t / b - _QB_FX_ECHO_PHASE_LO) / (_QB_FX_ECHO_PHASE_HI - _QB_FX_ECHO_PHASE_LO);
  return Math.min(1, Math.max(0, q));
}
/* 扫描束纵向包络分档(R5): 亮度在两轨末点 y 处最强(峰值 1)、上下渐隐(端点 0.07 底噪) —— 束
 * 不是「全高一条杠」, 而是穿过数据的扫描光刃; lo/hi = 末点 y 的归一化位置, 输入钳 [0.02,0.98],
 * 两峰贴近(<0.08)合并单峰。返回 {p, a} 升序 stop 表(渐变构建在绘制侧 —— 纯函数可断言)。 */
function _qbFxBeamStops(lo, hi) {
  const l = Number(lo);
  const h = Number(hi);
  const cl = Number.isFinite(l) ? Math.min(0.98, Math.max(0.02, l)) : 0.5;
  const ch = Number.isFinite(h) ? Math.min(0.98, Math.max(0.02, h)) : 0.5;
  const pts = [{ p: 0, a: 0.07 }, { p: 1, a: 0.07 }];
  if (Math.abs(cl - ch) < 0.08) {
    pts.push({ p: (cl + ch) / 2, a: 1 });
  } else {
    pts.push({ p: cl, a: 1 });
    pts.push({ p: ch, a: 1 });
  }
  pts.sort((x, y) => x.p - y.p);
  return pts;
}
/* R6 撕裂切片清单(plan §03 R6 节/D18; 模板保真二轮 C2/D3 改判): n = 2/3/5 按 lead 等级
 * (≤ _QB_FX_SLICES_MAX); 撕裂带中心 yCenter(lead 末点 y; merge 取中点/缺口退 lead —— spawn
 * 侧已仲裁), 半带宽 = (0.08 + 0.30 × min(1, Δ/0.5)) × 绘图高(Δ 小 ≈末点一道裂纹, Δ 大 ≈整片
 * 拉开); 长度 10–80px 随 Δ; alpha = 0.10+0.08×lv(C2 线性式, Lv.1/2/3 = 0.18/0.26/0.34;
 * q×impact 由绘制侧逐帧乘 —— 冻结清单不含逐帧因子, 拍内改 impact 下一帧生效); 右端 0–18px
 * 伪随机缩进(否则一排平齐「信号柱」而非撕裂); 层内相位 = strat(i,n,r) × hash01(拍序号,
 * 槽位)(每拍不重复、不聚集、可复现); ci 配色池 0=Lv 色(约45%) / 1=品红(约35%) / 2=lead
 * 语义色(约20%) —— 故障色为主(语义色为主会与曲线同色隐身); offX = ±3px x 向微震方向
 * (C2/D3 模板式: offX×q 绘制侧乘 —— 替换旧 y 向正弦 dy0/ph, 幅值 ≤5px I9; 抽屉入场期间
 * 暂停)。判定帧一次生成, 同拍逐像素冻结(只判定帧重算 —— §03 R6 冻结纪律)。 */
function _qbFxTearSlices(lv, yCenter, halfBand, powD, bi, mode, tTop, tBot) {
  const n = Math.min(_QB_FX_SLICES_MAX, _QB_FX_TEAR_COUNT[lv] || 2);
  const alpha = 0.10 + 0.08 * lv;
  const out = [];
  for (let i = 0; i < n; i++) {
    const r = _qbFxTearRnd(mode, bi, i * 13 + 3);
    out.push({
      y: Math.max(tTop + 2, Math.min(tBot - 3,
        yCenter + (_qbFxStrat(i, n, r) - 0.5) * 2 * halfBand)),
      len: 10 + 70 * powD * (0.45 + 0.55 * _qbFxTearRnd(mode, bi, i * 7 + 11)),
      inset: mode === "fixed" ? 0 : 18 * _qbFxTearRnd(mode, bi, i * 17 + 9),
      ci: r < 0.45 ? 0 : (r < 0.8 ? 1 : 2),
      alpha,
      offX: (_qbFxTearRnd(mode, bi, i * 5 + 1) * 2 - 1) * _QB_FX_SLICE_SHAKE_PX,
    });
  }
  return out;
}
/* R6 梳齿清单(§03 R6 节): n = 3/5/7 按 lead 等级, y 沿两轨末点包络带 [yLo, yHi] 分层采样
 * (带高 <28px 由调用方展开到 ±14), 长度 4–24px 随 Δ(powD), 横向偏移 0–3px —— 相位由
 * hash01(拍序号, 槽位) 决定, spawn 判定帧冻结(同拍逐像素恒同; random 对照档也不闪)。
 * y 输出侧照撕裂切片同式钳 [tTop+2, tBot-3](末点贴边时带展开会越出绘图区 —— 越界齿计入
 * 预算却被裁零墨, 评审 minor 修复)。 */
function _qbFxComb(n, yLo, yHi, powD, bi, mode, tTop, tBot) {
  const out = [];
  for (let c = 0; c < n; c++) {
    out.push({
      y: Math.max(tTop + 2, Math.min(tBot - 3,
        yLo + (yHi - yLo) * _qbFxStrat(c, n, _qbFxTearRnd(mode, bi, c * 11 + 5)))),
      len: 4 + (8 + 12 * powD) * _qbFxTearRnd(mode, bi, c * 3 + 2),
      dx: 3 * _qbFxTearRnd(mode, bi, c * 9 + 4),
    });
  }
  return out;
}

/* ---------------- SSE 事件合并(T4a, plan 26-11-18-0037; 模块级纯函数供 node 电池) ----------------
 * 数据合并语义(D9/任务钉面): 事件点 = per-tick 样本真值 -> 显示列**尾点更新/追加** ——
 * 显示列 = GET 组点列 + 事件样本点作为「最新测量」尾点; 每 tick 尾点被新事件点替代推进
 * (这就是「步进」); 事件点不折叠组, 由 30s 对账 GET 与断档重拉把列折叠归位到组粒度。
 * _qbStreamAppend 的三条分支:
 *   t === 列末 t  -> 尾点替代(同 tick 重发/尾组刷新); 同值重发 = 零变化(返回 false, 不触发重画);
 *   t >  列末 t   -> 追加「最新测量」尾点(步进); 超预算从头截断(见常量注 —— 防御面);
 *   t <  列末 t   -> 丢弃(GET 竞态纪律: 快照晚于事件时按 ts 归并, 不得回退)。
 * tail = 未折叠事件尾点缓冲(GET 落袋时按 t > GET 列末 t 归并回显示列, 其余视为已被
 * GET 组粒度列折叠); 缓冲与显示列同容量界。空值点(dl/up = null)照事件原样透传(缺口真值)。
 * !本函数只增尾不剪头 —— 头部陈旧点由调用面(_qbStreamFrame)按保留窗剪(修剪线 = 视口锚 −
 * (span_s + 2×组距), 锚缺/无效回落尾点, _qbTrimStaleHead 单点 —— 尾锚显式视口不变量(2):
 * 余量由数据层承担, GET 落地经 _qbStreamOnLoad 历史保留合并回填); 降级 GET 轮询/对账落袋
 * 整列替换 + 保留合并, 不经修剪面。 */
function _qbPointEq(a, b) {
  return a.t === b.t
    && (a.dl == null ? b.dl == null : a.dl === b.dl)
    && (a.up == null ? b.up == null : a.up === b.up);
}
function _qbStreamAppend(points, tail, p, cap, book) {
  const q = {
    t: Number(p && p.t),
    dl: p && p.dl == null ? null : Number(p.dl),
    up: p && p.up == null ? null : Number(p.up),
  };
  if (!(q.t > 0)) return false;
  const n = points.length;
  const last = n ? points[n - 1] : null;
  if (last && q.t === last.t) {
    if (_qbPointEq(last, q)) return false;
    points[n - 1] = q;
  } else if (!last || q.t > last.t) {
    points.push(q);
    if (points.length > cap) points.splice(0, points.length - cap);  // 预算防御(常量注)
  } else {
    return false;  // 乱序旧点: 不得回退
  }
  if (book !== false) {
    const lt = tail.length ? tail[tail.length - 1] : null;
    if (lt && q.t === lt.t) tail[tail.length - 1] = q;
    else if (!lt || q.t > lt.t) {
      tail.push(q);
      if (tail.length > cap) tail.splice(0, tail.length - cap);
    }
  }
  return true;
}

/* ---------------- 保留窗头部修剪(SSE 步进列的列不变量, 计划 26-11-22-0858 换代) ----------------
 * 列不变量(尾锚显式视口三不变量之(2)): store 列 == 显示列(单列恒等 —— 无补点无记账), 列 =
 * [anchor − (span_s + margin), anchor](margin = 2×组距; 修剪线视口锚优先、尾点回落 —— 锚
 * 领先尾时列仍覆盖视口左缘, G-B 防回潮)。缺陷史: SSE 主路径步进列只增尾不剪头
 * (26-11-21-1704 根治面), 该轮按**名义窗**剪(trim 线 = 尾t − span_s)把左缘裁剪余量一并剪掉
 * —— 滑动期视口左缘贴列首, GET 打断在途滑动时左缺口(G-B)只能靠显示层补点(F5)回补; 本轮
 * 补点随单列恒等退役, 裁剪余量改由**数据层余量列**承担: 修剪线 = 视口锚 − (span_s + margin)
 * (锚缺/无效回落尾点 —— 函数体行注), 视口左缘([anchor − span, anchor] 的 min)滑动时列内
 * 恒有真实历史可裁。
 *
 * 语义锚(承袭 26-11-21-1704):
 *   - 修剪线锚**数据面锚**(视口锚优先、尾点回落)而非墙钟: 主循环停顿期锚(单调, 随尾点)
 *     冻结 -> 修剪线冻结 -> 视图诚实冻结(停顿面走「滞后 Ns」徽标, D3/R7 —— 挂钟锚会在
 *     停顿期把左缘滑走, 与冻结语义相悖);
 *   - 门 = meta.schema === 2 且 span_s > 0: raw 段窗(1m-24h)是唯一点列每点带 t 的契约
 *     (旧契约 null 元素无 t 不可判), agg 段窗(3d+)跨度增长 ≤ 对账周期/窗宽 不可见;
 *     month 段窗(all)是数据面跨度(无固定窗长), 旧契约门同样排除 —— 历史整列本就该
 *     随尾点增长; agg/month 的视口由锚恒等式独立承担(与列修剪解耦);
 *   - 修剪线恒 ≤ 修剪点列尾(锚领先尾有界 —— 视口含尾), 列不会被剪空; margin = 2×组距取 meta
 *     .interval_s(调用方换算 keepS 传入 —— 本函数不读 meta, 纯函数面);
 *   - 修剪落地在**数据入口面**(_qbStreamFrame 帧合并处): store 列与建图显示列逐点恒等
 *     —— 悬停取值(_qbHoverOf 读 d.points[i])与缺口区段(_qbGapZone 链界)索引零记账;
 *     tail 缓冲与对账归并(_qbStreamOnLoad)零触碰, 模块级纯函数(node 电池真跑)。 */
function _qbTrimStaleHead(points, keepS, anchorT) {
  const s = Number(keepS);
  if (!(s > 0) || !points || points.length < 2) return points;
  const tailT = Number(points[points.length - 1] && points[points.length - 1].t);
  if (!(tailT > 0)) return points;  // 尾点无 t(旧契约形): 修剪线无处锚, 不剪(调用方门已滤)
  // 修剪线锚 = 视口锚(anchorT, 单调)优先, 尾点回落 —— 单列恒等的列不变量实为
  // [anchor − (span + margin), anchor]: 锚领先尾时(旧窗响应落袋后重放尾滞后), 尾锚修剪会
  // 把列头剪到视口左缘右侧 = G-B 左缺口回潮(e2e A2-24h 实证); 锚=尾时两者同形。
  const line = (Number(anchorT) > 0 ? Number(anchorT) : tailT) - s;
  let cut = 0;
  for (let i = 0; i < points.length - 1; i++) {
    const t = Number(points[i] && points[i].t);
    if (!(t > 0) || t >= line) break;  // 无 t 点(防御)与首个窗内点即停 —— 其后一概保留
    cut = i + 1;
  }
  return cut > 0 ? points.slice(cut) : points;
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
     * 缺口点不出速率, 出缺口文案(qbCurGapText, 按区段 × 作用域 —— 2026-10-30 起不再对
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
    /* 窗口内累计(totals 真值点求和, 与 points 等长同构; 缺口/断线/重置向本就 null 不计 —— §5.1 差分语义) */
    /* 重启缝提示(P4, plan 26-10-15-0829; 左端口径修订 26-10-16, issue 26-10-16-0954):
     * 数据链末点早于右沿且重启贴近链末(meta 新键 server_started_at ∈ [链末点前一个组距起点, 右沿])
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
    /* ---------------- 数值面板状态行(R8 §05.3 不可编辑项表 + 状态行格式, S3 回填) ----------------
     * 展示值落 computed(范式同 qbCurGapText): fx-panel.html 裸插值 {{ qbFxPeriodS }} 不加括号,
     * 落 methods 域会被 toDisplayString 渲染成函数源码字符串(Vue 3 对非字符串一律 String())。
     * period 取 _qbPollMs 实算值(不是面板自己估的), 恒一位小数("3.0"/"30.0", §05.3 规格行
     * 「采样 3.0 s」); beat 为派生量(可调即允许突破 I1 的 1s 硬上限, 故只读), 公式单点在
     * _qbBeatMs(S1 起面板与调度器共用一份, 不再各写一遍 clamp)。「上次真实拍 Xs 前」S3 回填:
     * fxBeatAt(真拍判定帧写入) + fxNow(1s 步进时钟)双依赖, 无真拍过/时钟未起显示 —。 */
    qbFxPeriodS() {
      return (this._qbFxCurPeriodMs() / 1000).toFixed(1);
    },
    /* F6 显示口径(plan 26-11-14-1313; 组距语义 26-11-18-0037 阶段 3): 「采样」读
     * meta.sample_interval_s(生效采样间隔), 与 meta.interval_s 不等时两值形态。schema=2
     * 样本分组契约(raw 段窗)下 interval_s = 组距标称 k x si(桶面已退役)—— 二值出
     * 「X s · 组距 Y s」; agg 段窗(D4 零改动)无 schema 键, 二值仍是「X s · 桶宽 Y s」。
     * 相等或缺失回落现状单值(qbFxPeriodS = _qbPollMs 实算)。两值面读 raw meta(采样间隔/
     * 组距·桶宽都是事实值, 不吃轮询夹取)。F7(plan 26-11-15-1104 D6)后 beat/轮询派生量
     * 单点锚 _qbFxCurPeriodMs 同读 sample_interval_s 夹取 —— 状态行两组值(采样/beat·周期)
     * 同源一致, 本 computed 只改显示文案不改节律。 */
    qbFxSampleText() {
      const s = this.qbCurScope;
      const d = s ? this[_QB_SCOPES[s].data] : null;
      const m = d && d.meta;
      const si = Number(m && m.sample_interval_s);
      const iv = Number(m && m.interval_s);
      if (!(si > 0) || !(iv > 0) || Math.abs(si - iv) < 1e-9) return this.qbFxPeriodS + " s";
      if (Number(m && m.schema) === 2) return si.toFixed(1) + " s · 组距 " + iv.toFixed(1) + " s";
      return si.toFixed(1) + " s · 桶宽 " + iv.toFixed(1) + " s";
    },
    qbFxBeatMs() {
      return Math.round(_qbBeatMs(this._qbFxCurPeriodMs()));
    },
    qbFxBeatAgeText() {
      if (!(this.fxBeatAt > 0) || !(this.fxNow > 0)) return "—";
      // fxNow 是 1s 步进时钟, 拍落在两次步进之间时差值为负 —— 钳 0 显示「0.0 s 前」,
      // 不回 —(— 只保留给「还没开过面板时钟 / 没来过真拍」)
      return (Math.max(0, (this.fxNow - this.fxBeatAt) / 1000)).toFixed(1) + " s 前";
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
    /* 状态行 1s 时钟对称摘除(S3, 同清池纪律): 面板开着时组件卸载(登出/热重载)走这里,
     * 正常关面板已由 _qbFxListen(false) 清过(幂等)。 */
    if (this._qbFxClock) {
      clearInterval(this._qbFxClock);
      this._qbFxClock = 0;
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
      // SSE 主路径(T4a, plan 26-11-18-0037): 开图即连(per-scope 订阅, E1)+ 30s 对账定时;
      // GET 轮询骨架(_qbPollStart)保留, 仅降级态(_qbStreamDegrade)接管取数(E7)。
      this._qbStreamStart(scope);
    },
    /* 面板重新进场后的补拉(state.js watch(drawerVisible) 的可见分支): 隐藏期(非主内容页)轮询被
     * active 守卫跳过, 数据与宿主都已陈旧 —— 这里补一发同时在 $nextTick 里对新宿主重建图
     * (_qbLoad 内含建图单点)。**在途不叠加**: 打开路径本已经先发了一发(面板进场与 _qbLoad 在
     * 同一个 flush 前后脚走), 叠加等于把首次打开的请求翻倍(同轮询 tick 的 loading 互斥口径)。
     * T4a: 进场顺路核对流在场(_qbStreamResume —— 流活着则零操作不重连; 被 teardown 收过的
     * 异常路径则重连), 与 _qbLoad 的 loading 早退解耦(流在场核对不受在途守卫挡)。 */
    _qbReloadOnEnter(scope) {
      const def = _QB_SCOPES[scope];
      if (!def) return;
      this._qbStreamResume(scope);
      if (this[def.loading]) return;
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
    /* 高级折叠开合后的实测重钳位(fx-panel.html details @toggle): 折叠改变面板真实高度, 而
     * refit 的触发面(watcher/resize/scroll/宿主 RO)都不含它 —— 不重钳位, 贴底钳位过的面板
     * 展开后底边越出视口(§05.9「底边不得超出视口」), 底栏按钮点不到。公开名转发节流单点
     * (模板触达的处理器不得带 _ 前缀 —— commands_send.js:347-350 前科); 收起(高度变小)
     * 走同一入口幂等重钳, 位置只松不紧, 无副作用。 */
    fxRefitSoon() {
      this._qbFxRefitSoon();
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
        // 状态行「上次真实拍 Xs 前」的 1s 步进时钟(§05.3 状态行格式, S3): 仅面板开着才走
        // (关面板即停, 无常驻定时器), 每跳写 fxNow 让 qbFxBeatAgeText computed 重估;
        // fxBeatAt 由 _qbBeatStart 在真拍判定帧写入(qbCurScope 对齐)。
        if (!this._qbFxClock) {
          this._qbFxClock = setInterval(() => { this.fxNow = Date.now(); }, 1000);
          this.fxNow = Date.now();  // 开面板立即对齐一次(不等首跳, 打开即显示正确)
        }
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
      if (this._qbFxClock) {
        clearInterval(this._qbFxClock);  // 关面板即停(状态行不再可见, 无需续跳)
        this._qbFxClock = 0;
      }
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
    /* 复选框(总开关 enabled / 视觉 neon/tail / 高级四层开关 layers.*; 布尔严格 === true|false)。
     * 总开关单一状态源(§05.3 enabled 行 + §06 S3 行, S3 落点说明): 「启用动效」只有一个入口
     * —— 本处理器写唯一字段 fx.enabled(P4 右键勾选项已被 R8 关闭, D24: 右键入口就是面板本身,
     * 不存在第二个勾选项); 图区右键监听只做 openFxPanel, 零开关语义。若未来要加第二个开关
     * 入口(§05.3「双向同步」的预留面), 必须读写同一字段 fx.enabled —— 状态单向流 fx ->
     * watch.fx -> _qbFxCfgSync -> window.AQB_FX_CFG(引擎只读 CFG), 双向同步由该单链自动完成,
     * 不允许出现第二个状态源(否则两边各存一份必然漂移)。 */
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
    /* 预览一拍(§05.4 六条语义, S3 已接线): 交调度器域 _qbPreviewBeat —— 预览动画态在图记录
     * (u._qbBeat.anim.preview + previewToken), Vue 只留 fxPreviewing 布尔镜像供状态行
     * 「· 预览中」(翻转沿写, 绘制热路径不读 Vue —— §05.3); 本处理器零持久化副作用。 */
    fxPreview() {
      this._qbPreviewBeat();  // 缺省 scope = qbCurScope(面板浮在当前图上)
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
    /* D4 曲线宽单点(plan 26-11-22-2330 §3.3): 常规 2.4 / calm 2(克制档细线, 模板 isCalm 同款)。
     * palette 切换经 _qbFxCfgSync 现写 u.series[1/2].width + redraw(uPlot 每帧读 series.width, 不
     * 重建、不 destroy、不碰 loading) —— 若等下一拍才生效, 面板改档与曲线视觉会错拍一整个节拍,
     * 故走配置同步面而非拍内钩子。入参显式 palette 供 cfgSync 用(避免二次读已改写的 CFG); 缺省
     * 先读运行期 CFG(建图时 immediate watcher 已落初值), 再回落 fx 持久化值(桩/首帧防御)。 */
    _qbFxCurveWidth(palette) {
      const p = palette != null ? palette
        : ((window.AQB_FX_CFG && window.AQB_FX_CFG.palette) != null
          ? window.AQB_FX_CFG.palette : (this.fx && this.fx.palette));
      return p === "calm" ? 2 : 2.4;
    },
    _qbFxCfgSync() {
      const cfg = JSON.parse(JSON.stringify(this.fx));
      cfg.on = this.fxOn;
      window.AQB_FX_CFG = cfg;
      // F2 常驻菱形锚门面(cfg.on / palette 变化即时生效, 不等下一拍): 总开关翻关/reduce 翻入
      // 隐藏、翻开复显, calm 切档类即时对齐 —— 位置不在本面(四处同步点单管位置, R3 收敛口径)。
      // D4 曲线宽与锚同步同面落笔: 宽度变化才 redraw(避免无关 fx 改动触发无谓重画), 不重建图。
      const w = this._qbFxCurveWidth(cfg.palette);
      if (this._qbCharts) {
        for (const s of Object.keys(this._qbCharts)) {
          const uc = this._qbCharts[s];
          if (uc && uc.root && uc.root.isConnected) {
            this._qbFxAnchorSync(uc);
            if (uc.series && uc.series[1] && uc.series[1].width !== w) {
              uc.series[1].width = w;
              if (uc.series[2]) uc.series[2].width = w;
              uc.redraw(false, true);
            }
          }
        }
      }
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
     * 写回真值)再重排 —— 否则动画帧的 y 钉会盖过新档位一拍、偏置视口与新
     * 档位错配一帧; 收口语义与收敛帧同款, 不留半帧。 */
    _qbChartRescale(scope) {
      const u = this._qbCharts && this._qbCharts[scope];
      if (!u || !u.root || !u.root.isConnected || !u.data) return;
      const st = u._qbBeat;
      if (st && st.anim) {
        if (st.anim.preview !== undefined) {
          // 预览在途(S3): 假 target 不得当真值写回 —— 走预览还原核心(尾点写回预览前真值 +
          // 状态机复位), 提交交给下方 setData(还原值 = 真值, 重推档位一致)。
          this._qbPreviewRestore(u, st.anim);
        } else {
          const a = st.anim;
          const tr = st.tracks;
          if (tr.up.live) u.data[1][a.n - 1] = tr.up.target;
          if (tr.dl.live) u.data[2][a.n - 1] = tr.dl.target;
          tr.up.shown = tr.up.live ? tr.up.target : null;
          tr.dl.shown = tr.dl.live ? tr.dl.target : null;
        }
        this._qbBeatCancel(u);
      }
      // 尾锚显式视口(计划 26-11-22-0858): setData 的 resetScales 把 x 交还列全宽 auto(列含
      // 余量 —— 恒偏宽, 不是真值), 显式锚视口必须重申(单列恒等下无补点 slice 面 —— 旧
      // dropPad 随补点退役); 视口锚不动(y 重排不搬窗口)。span 缺席(防御)退回 auto。
      // y 成对钉档: 重排的动机就是换档位(y 切档/限速变化), 旧钉值(判定帧按旧 cap 钉的)已
      // 失效 —— 按新 cap 对全列重算 yMax(与判定帧扫描同口径), 与 x 重申成对钉档, 终态与
      // 判定帧基准同尺(不成对钉时 x 重申的 pending 消费按锚窗可视数据重推, 余量持峰即两把尺)。
      u.setData([u.data[0], u.data[1], u.data[2]]);
      let dmax = 0;
      for (let c = 1; c <= 2; c++) {
        const col = u.data[c];
        if (!col) continue;
        for (let i = 0; i < col.length; i++) {
          const v = col[i];
          if (v != null && v > dmax) dmax = v;
        }
      }
      const yMax = _qbYRange(dmax, this._qbYCapOf(scope))[1];
      const stR = u._qbBeat;
      if (stR && stR.span > 0 && stR.anchor > 0) {
        u.setScale("x", { min: stR.anchor - stR.span, max: stR.anchor });
        u.setScale("y", { min: 0, max: yMax });  // 与 x 成对: 该提交不得按锚窗可视数据重推 y
      }
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
    /* 三挂点统一收尾(关抽屉 / 形态切换 / 登出): 停三挂点轮询 + 停 SSE 流(T4a)+ 销毁三挂点图,
     * 单点防漏 */
    _qbTeardown() {
      for (const s of Object.keys(_QB_SCOPES)) {
        this._qbPollStop(s);
        this._qbStreamStop(s);
        this._qbChartDestroy(s);
      }
    },
    /* ---------------- 取数单点(三挂点同形: 开门 -> 拉取 -> 竞态判 -> 落袋/回落) ---------------- */
    async _qbLoad(scope) {
      const def = _QB_SCOPES[scope];
      if (!this.qbTrafficOn) return;  // P5 验收: enabled=false 不发请求(入口 v-if 已门, 这里兜底)
      const ctx = def.ctx ? def.ctx(this) : "";
      // 窗口快照(取数有效性不变量(3), 计划 26-11-22-0858): def.stale 三谓词只核对作用域上下文
      // (全局/种子 hash/组 key), 不含窗口名 —— 换窗时旧窗口的在途响应会落袋覆盖新窗数据
      // (用户报障面: 1m 选择下整列呈旧窗跨度 = x 向压缩)。发射时快照 w0, 落袋前比对当前
      // 窗口, 不等即弃(成败两路同判 —— 旧窗的失败面也不得清新窗数据/亮错误态)。
      const w0 = this[def.window];
      this[def.loading] = true;
      // 悬挂兜底的计时起点已随骨架上提(polling.js 的 st.stallAt, 由 tick 观测到 loading 置位的
      // 那一刻起算)—— 换目标场景下旧请求的 finally 晚于新请求的置位到达时不再有"擦起点"的坑。
      // error **不在此清空**(2026-10-05 修「空态/错误态每隔一个轮询周期闪一次」): 请求前清错误 =
      // 续拉把错误文案换成一帧 loading/空态再换回, 与「清空旧数据把等待渲染成空态」同型; 错误态
      // 改由**下一次成功落袋**清除(见下), 期间的旧文案由 FX-29 遮罩在换目标时兜住(160ms 延迟点亮)。
      let stale = true;  // 保守初值: 只有确认未过期才落袋/清 loading(在途竞态纪律, 同 _drawerStale)
      try {
        const data = await this.api(def.url(ctx, w0));
        stale = def.stale(this, ctx) || this[def.window] !== w0;
        if (!stale) {
          // 旧列快照(GET 落地历史保留合并的原料 —— 余量列真实历史, 见 _qbStreamOnLoad):
          // 必须在 this[def.data] 被整列替换**之前**捕获。
          const oldPoints = this[def.data] && Array.isArray(this[def.data].points)
            ? this[def.data].points : null;
          this[def.data] = data;
          this[def.error] = "";  // 成功落袋才清错误态(见上: 在途期不动既有状态)
          this._qbStreamOnLoad(scope, data, oldPoints);  // SSE 主路径: GET 落袋 = 对账基准, 事件尾点按 ts 归并
        }
      } catch (e) {
        stale = def.stale(this, ctx) || this[def.window] !== w0;
        if (!stale) {
          // SSE 主路径(T4a): 流活着(未降级)且列里有数据时, 对账 GET 失败不清数据不亮错误态
          // —— 显示列仍由事件帧推进(数据是新鲜的), 清空等于把好数据换成空态闪一帧; 失败面
          // 记 pullFail(徽标: 静默叠加时「已断连」)。降级态(GET 轮询是唯一取数路径)与
          // 无流态保持旧语义: 清数据 + 错误文案(e.auth 的 401 已走 _logout 清场, 数据照清)。
          const st = this._qbStreams && this._qbStreams[scope];
          const feeding = !!(st && st.want && !st.degraded && this[def.data]);
          if (feeding) {
            st.pullFail = true;
          } else {
            if (!e.auth) this[def.error] = e.message || "加载失败";
            this[def.data] = null;
          }
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
    /* 悬停点的时刻(锚面 = _qbPointsToData 产出的全列真值 xs —— schema=2 每点带 t 直读,
     * 旧契约 null 槽由内插/外推补齐; 锚缺席(防御)回落该点真值 t, 旧契约 null 槽无 t = 0) */
    _qbBucketTs(scope, i) {
      const a = this._qbAnchors && this._qbAnchors[scope];
      if (a && a.xs) return a.xs[i];
      const d = this[_QB_SCOPES[scope].data];
      const p = d && d.points ? d.points[i] : null;
      return p ? p.t : 0;
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
      // 缺口判据(E3, 26-11-18-0037 阶段 3): 旧契约 null 槽与 schema=2 显式空值点({t,
      // dl:null, up:null})同判 —— 双 null 即缺口, 不出速率不出「0 B/s 空闲」(空闲 = (0,0)
      // 真实观测点, 与缺口可辨)。
      if (!p || (p.up == null && p.dl == null)) {
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
      // 窗内桶数(保住 26-11-21-1704 恢复的「摘要桶数 = 窗内桶数」语义): 余量列(不变量(2),
      // 列 = [anchor − (span+margin), anchor], 修剪线视口锚优先、尾点回落)的 2 组距历史点
      // 不计 —— 按 t ≥ 尾t − span_s 现数; span_s 缺席(旧契约形/防御)回落全列长。
      const pts = (d.points && d.points.length) ? d.points : null;
      let n = 0;
      if (pts) {
        const spanS = Number(d.meta && d.meta.span_s);
        const tail = Number(pts[pts.length - 1] && pts[pts.length - 1].t);
        // 窗内桶数按 t 现数仅限 schema=2(点列每点带 t, 显式空值点也带 t 照计); agg 旧契约
        // (定长桶数组, null 槽无 t)回落全列长 —— 两族窗的缺口计数口径统一(评审轮1 minor:
        // 裸 span_s 门会让 agg 缺口槽掉出计数)。
        const schema2 = !!(d.meta && d.meta.schema === 2);
        if (schema2 && spanS > 0 && tail > 0) {
          const line = tail - spanS;
          for (const p of pts) if (Number(p && p.t) >= line) n++;
        } else {
          n = pts.length;
        }
      }
      return { buckets: n, up: sum("up"), down: sum("dl") };
    },
    /* ---------------- 低频轮询(§07; 打开期间挂, 关闭/切走即清) ----------------
     * F7(plan 26-11-15-1104 D6): 节拍 = meta.sample_interval_s(生效采样间隔)夹取, 全窗统一
     * —— 「低频轮询 = 桶宽」旧口径(读 meta.interval_s)正式反转: 桶宽加宽后长窗一拍迟钝至
     * 30s~174s, 与毫秒级读侧能力错配(G-F)。sample_interval_s 是后端 _meta 装配单点全窗携带
     * 的键(26-11-14-1313 F6 只增键, 后端零改); 面板「采样」行(qbFxSampleText)与 beat/周期
     * 派生量(qbFxPeriodS/qbFxBeatMs -> _qbFxCurPeriodMs)自此同源。缺键/非法(旧缓存降级响应,
     * 只带 interval_s 的旧形状)回退 30s。 */
    _qbPollMs(scope) {
      const def = _QB_SCOPES[scope];
      const d = this[def.data];
      const s = Number(d && d.meta && d.meta.sample_interval_s);
      if (!(s > 0)) return _QB_POLL_FALLBACK_MS;
      return Math.min(_QB_POLL_MAX_MS, Math.max(_QB_POLL_MIN_MS, s * 1000));
    },
    /* 低频轮询走长驻骨架(polling.js::startPoll 单点, 2026-10-22): 这里只声明差异 ——
     *   !T4a(plan 26-11-18-0037)起本方法不再是打开路径的取数主路 —— SSE 主路径(_qbStreamStart)
     *   接管事件驱动判定帧, 本骨架只在**降级态**(_qbStreamDegrade, E7: 票据满额/连续重连失败)
     *   被 _qbStreamDegrade 拉起, 语义与旧「打开期间按 si 续拉」完全一致(同契约轮询级延迟)。
     *   - 节拍 = 采样间隔夹取(_qbPollMs, F7/26-11-15-1104 D6 起读 meta.sample_interval_s);
     *     骨架每拍重读间隔 => 换窗跨段(raw <-> hour)自动重排, 不再需要单独的 resync 钩子
     *     (旧 _qbPollResync 随本轮收敛删除)。
     *   - 首拍立即(F8/D4, immediate: true): 打开路径 = _qbLoad 直拉 + _qbPollStart 同拍先后
     *     脚 —— 起拍时 meta 多半未落袋, 旧骨架首拍 arm 成 30s fallback 干等一整个周期; 首拍
     *     立即后该拍与直拉经 loading 互斥兜底(在途被 mutex 跳过, 按短重试重排到直拉落定),
     *     不双发; 冷开 30s 干等消失。 R6: loading 互斥 + 骨架 stall 兜底保留不变。
     *   - 守卫 = 图还活跃(def.active); 页面隐藏由骨架恒等守卫兜, 不再手写。
     *   - 在途互斥(loading, 在 _qbLoad finally 归位)+ 悬挂兜底: 骨架统一做 —— 卡死判据就是
     *     loading 本身, 未超时前挡拍(mutex), 超阈值强制续拉并留一次警告痕(issue 26-10-16-0954
     *     的成因: 旧实现 loading 卡死即永久挡拍, 图表停在旧帧且无提示也不自愈)。
     *     阈值常量随骨架上提为 AQB_POLL_STALL_MS(polling.js), 抽屉侧自此同口径。 */
    _qbPollStart(scope) {
      this._qbPollStop(scope);
      this.startPoll(`qb:${scope}`, {
        immediate: true,
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
    /* ---------------- SSE 主路径(T4a, plan 26-11-18-0037 阶段 3 子波 2; D7/D9/E1/E4/E7) ----------------
     * 判定帧节拍源换轴(D7): 「轮询落袋」->「SSE 事件到达」。per-scope 一条流(图表打开期间):
     *   票据 POST /api/events/ticket -> EventSource(/api/traffic/qb/stream?scope=…&ticket=…)
     *   (照 polling.js::startEvents 范式: EventSource 发不出 Authorization 头, 一次性短时票据
     *   以 ?ticket= 连流; 单次消费 => 重连必换新票 —— EventSource 自带重连拿旧票撞 401,
     *   onerror 一律关旧连换票重开, 3s 与 EventSource 默认重连同拍)。
     * 事件面: `hello`(开流标记)+ `traffic` 帧 {seq, scope, points:[{t, dl, up}]}(per-tick
     *   样本粒度真值, 每 tick 每 scope 恰 1 帧)+ 心跳注释帧(EventSource 自动吞, 不入 JS 面)。
     * 状态机(st.state): connecting(票据/握手在途) -> live(onopen/hello) -> retry(onerror,
     *   3s 换票重开; 连续 _QB_STREAM_FAIL_MAX 轮失败) -> degraded(GET 轮询接管, E7; 每
     *   60s 保守重试一次流, 成功即回 live 且轮询退役) / stopped(关抽屉/登出 teardown)。
     *   失败计数语义(评审 T4a-R2): onerror +1, 清零只认「本连产出过数据帧」(_qbStreamFrame)
     *   —— 握手成功不清(空闪连可累计降级), 来帧即归零(正常瞬断不积累)。会话代际(st.gen,
     *   评审 T4a-R1): stop/restart 翻代, 在途换票 continuation 落票即弃, 监听器核验来连。
     * seq 连续性(D9): 首帧基线(订阅归零即重计, 后端契约「断档检测在基线之后」), 之后期望
     *   seq+1; 断档(队列满丢弃留痕)/回退(服务端重计)都立即 GET 重拉(_qbStreamPullNow,
     *   3s 节流防断档风暴)并把 seq 重基线。静默(>3 x si, R7)是另一条停流信号: 流活着但无
     *   新帧(主循环停顿)不虚增 seq —— watchdog 判「末样本 ts vs 墙钟」出「滞后 Ns」徽标,
     *   静默沿立即 GET 重拉一次(30s 对账兜后续); 恢复(seq 续上/新帧到)徽标自动消。
     * 数据合并: 见模块级 _qbStreamAppend 注(尾点替代/追加/竞态不回退 + tail 缓冲 GET 归并)。
     * 对账(E4): startPoll("qb-acc:<scope>") 30s 一次 _qbLoad —— 流活着也全量校准(缓冲归位
     *   组粒度); 降级态取数归 GET 轮询(qb:<scope>), 对账 guard 停摆。
     * 页面隐藏(照 ver 通道先例, polling.js): EventSource **不停流**(后台标签保持连接, 拆了
     *   重连的 churn 比 1.5s 一帧的合并贵得多), 帧照常合并进显示列(纯数据面), 但 **跳过
     *   $nextTick 建图**(渲染面节流; 对账/watchdog 走骨架恒等守卫隐藏期零拍) —— 回到前台由
     *   下一帧(si <= 1.5s)或 30s 对账补上渲染, 徽标隐藏期不更新(不可见)。
     * 清理面(照 stopEvents 四件): _qbStreamStop 清 EventSource/重试定时器/两张对账与
     *   watchdog 定时器(经骨架)/状态与缓冲, 幂等(重复开连不泄漏)。 */
    _qbStreamEnsure(scope) {
      if (!this._qbStreams) this._qbStreams = {};
      let st = this._qbStreams[scope];
      if (!st) {
        st = this._qbStreams[scope] = {
          want: false, es: null, busy: false, retry: null, state: "stopped", degraded: false,
          gen: 0, failRun: 0, seq: null, tail: [], lastT: 0, pullFail: false,
          silentPull: false, reconcileAt: 0, streamScope: "",
        };
      }
      return st;
    },
    /* 开流(打开路径 / 降级重试 / 进场补挂的唯一入口): 先停后起(幂等 —— 重复开连不泄漏),
     * 挂对账与 watchdog 两张骨架定时器, 再换票建流。torrent/group 的目标未就绪(无 hash/key)
     * 不开(防御: 空目标流 URL 必 400, 不发无意义请求)。 */
    _qbStreamStart(scope) {
      const def = _QB_SCOPES[scope];
      if (!def || !this.qbTrafficOn) return;
      const sScope = def.stream ? def.stream(this) : "";
      if (!sScope || (scope !== "global" && sScope === (scope + ":"))) return;
      this._qbStreamStop(scope);  // 先停后起(幂等; 降级态残留的 GET 轮询一并收)
      const st = this._qbStreamEnsure(scope);
      st.want = true;
      st.streamScope = sScope;
      st.state = "connecting";
      st.degraded = false;
      st.failRun = 0;
      st.seq = null;          // seq 基线随连接会话归置(首帧重取)
      st.tail = [];
      st.lastT = 0;
      st.pullFail = false;
      st.silentPull = false;
      st.reconcileAt = 0;
      // 30s 对账 GET(E4/D9): 流活着也低频全量校准(缓冲归位组粒度); 降级态由 GET 轮询承担
      // 取数(对账 guard 停摆); 在途/loading 互斥(在途 GET 本身就是一次对账)。
      this.startPoll(`qb-acc:${scope}`, {
        ms: () => _QB_STREAM_RECONCILE_MS,
        fn: () => this._qbReconcile(scope),
        guard: () => {
          const s = this._qbStreams && this._qbStreams[scope];
          return !!(s && s.want && !s.degraded) && !this[_QB_SCOPES[scope].loading]
            && _QB_SCOPES[scope].active(this);
        },
      });
      // 停流/断连徽标 watchdog(1s 步进): 静默(>3 x si)起显「滞后 Ns」+ 静默沿立即 GET 重拉;
      // 活跃守卫随骨架恒等守卫兜(页面隐藏零拍, 徽标不可见也无需更新)。
      this.startPoll(`qb-wd:${scope}`, {
        ms: () => _QB_STREAM_WATCHDOG_MS,
        fn: () => this._qbStallTick(scope),
        guard: () => _QB_SCOPES[scope].active(this),
      });
      this._qbStreamConnect(scope);
    },
    /* 关流(照 polling.js::stopEvents 清四件纪律): EventSource / 重试定时器 / 两张骨架定时器 /
     * 状态与缓冲全收, 幂等(未开也安全); 降级期接管的 GET 轮询一并收(qb:<scope>), 关闭后
     * 零请求路径(「不打开 = 0 请求」契约的流面延伸)。
     * 会话代际(评审 T4a-R1): stop 翻代(gen+1)—— 在途换票 continuation 落票后代际不符即整体
     * 丢弃(连票带连), 不再只靠 want 复查(重开抽屉会把 want 置回 true, 旧 continuation 会
     * 建出第二条 ES 且 st.es 后写覆盖前写 = 旧连泄漏); busy 复位仍归 stop(代际不符的旧
     * continuation 不得触碰 busy —— busy 已归新会话所有)。 */
    _qbStreamStop(scope) {
      const st = this._qbStreams && this._qbStreams[scope];
      if (!st) return;
      st.want = false;
      st.gen = (st.gen || 0) + 1;  // 会话代际翻新: 在途换票/建流 continuation 一律作废
      if (st.retry) { clearTimeout(st.retry); st.retry = null; }
      if (st.es) { st.es.close(); st.es = null; }
      st.busy = false;
      st.state = "stopped";
      st.degraded = false;
      st.seq = null;
      st.tail = [];
      st.lastT = 0;
      st.pullFail = false;
      st.silentPull = false;
      this.stopPoll(`qb-acc:${scope}`);
      this.stopPoll(`qb-wd:${scope}`);
      this.stopPoll(`qb:${scope}`);  // 降级态的 GET 轮询同收(非降级态 no-op, 幂等)
      this._qbStallBadgeSyncChart(scope);  // 图还在(异常路径)时徽标立即归位隐藏; 拆图随 u.destroy
    },
    /* 进场核对(stream alive 则零操作, 不重连): _qbReloadOnEnter 消费; 正常路径流全程在场
     * (页面切走不停流), 这是 teardown 后异常路径的重连兜底。 */
    _qbStreamResume(scope) {
      const st = this._qbStreams && this._qbStreams[scope];
      if (st && st.want) return;
      this._qbStreamStart(scope);
    },
    /* 换票建流(照 polling.js::startEvents 形态): busy 防重入(换票是异步的); 落票后复查
     * 代际/want/authOk(await 期间可能已登出/关抽屉/重开抽屉 —— polling.js #7 同款竞态窗口的
     * 闭端, 代际判据见 _qbStreamStop 注)。监听器一律核验来连 === st.es: 被顶掉的旧连
     * (onerror/onopen/hello/帧)不得改写新会话 st(不误伤也不自救)。 */
    async _qbStreamConnect(scope) {
      const st = this._qbStreams && this._qbStreams[scope];
      if (!st || !st.want || st.es || st.busy) return;
      const myGen = st.gen || 0;  // 会话代际快照: stop/restart 即翻代, 本 continuation 作废
      st.busy = true;
      let ticket = "";
      try {
        const r = await this.api("/api/events/ticket", { method: "POST" });
        ticket = (r && r.ticket) || "";
      } catch (e) {
        if (st.gen !== myGen) return;  // 代际已翻: 旧 continuation 整体丢弃(busy 已归新会话)
        st.busy = false;
        if (e && e.auth) return;  // 401 已走 _logout 清场(want 已清), 不重试
        this._qbStreamRetry(scope);  // 票据失败(含满额 503)按连接失败计(连续计数 -> 降级, E7)
        return;
      }
      if (st.gen !== myGen) return;  // 落票后复查之一(代际): 重开竞态下带票丢弃, 不建流
      st.busy = false;
      if (!st.want || !this.authOk) return;  // 落票后复查之二(照 polling.js #7)
      if (!ticket) { this._qbStreamRetry(scope); return; }
      let es = null;
      try {
        es = new EventSource("/api/traffic/qb/stream?scope=" + encodeURIComponent(st.streamScope)
          + "&ticket=" + encodeURIComponent(ticket));
      } catch (e) {
        this._qbStreamRetry(scope);  // 不支持就用降级路径, 不报错(推送是加速手段, 不是必需)
        return;
      }
      st.es = es;
      es.onopen = () => { if (st.es === es) this._qbStreamOnOpen(scope); };
      es.addEventListener("hello", () => { if (st.es === es) this._qbStreamOnOpen(scope); });
      es.addEventListener("traffic", (e) => {
        if (st.es !== es) return;  // 旧连帧不得改写新会话 st(评审 T4a-R1)
        // 数据帧: {seq, scope, points} —— 坏帧忽略(照 polling.js 事件监听纪律)
        try { this._qbStreamFrame(scope, JSON.parse((e && e.data) || "null")); } catch (_) { /* 坏帧忽略 */ }
      });
      es.onerror = () => {
        if (st.es !== es) return;  // 旧连 onerror: 不误伤新会话也不自救(新会话 own retry 面)
        // 一次性票据在重连时必失效(服务端取即删) —— EventSource 自带重连会拿旧票撞 401,
        // 必须关旧连换新票重开(3s); 连续 _QB_STREAM_FAIL_MAX 轮失败降级 GET 轮询(E7)。
        es.close();
        st.es = null;
        this._qbStreamRetry(scope);
      };
    },
    /* 开流确认(onopen / hello 双源汇一, 来连核验在监听器侧): live 落位; 失败计数**不在此清**
     * (评审 T4a-R2: 握手成功 ≠ 可用 —— 空闪连(代理掐流/握手后秒断)onopen 清零会让计数恒
     * 0/1 振荡, _QB_STREAM_FAIL_MAX 永不达成 = E7 降级不可达; 清零单点移到 _qbStreamFrame
     * 「本连确实产出过数据帧」处)。降级恢复 = 流回来即让 GET 轮询退役(数据面回 SSE 主路径)
     * 并立即对账一次(轮询期可能积了滞后)。 */
    _qbStreamOnOpen(scope) {
      const st = this._qbStreams && this._qbStreams[scope];
      if (!st || !st.want) return;
      st.state = "live";
      if (st.degraded) {
        st.degraded = false;
        this._qbPollStop(scope);
        this._qbStreamPullNow(scope, true);
      }
      this._qbStallBadgeSyncChart(scope);
    },
    /* 重试轮(票据/握手/建流任一失败汇入): 连续失败计数, 未达上限 3s 后换票重开(照
     * polling.js 重试纪律), 达上限降级(E7)。重试定时器单柄(st.retry)防堆叠。 */
    _qbStreamRetry(scope) {
      const st = this._qbStreams && this._qbStreams[scope];
      if (!st || !st.want || st.retry || st.es) return;
      st.state = "retry";
      st.failRun += 1;
      if (st.failRun >= _QB_STREAM_FAIL_MAX) { this._qbStreamDegrade(scope); return; }
      st.retry = setTimeout(() => {
        st.retry = null;
        this._qbStreamConnect(scope);
      }, _QB_STREAM_RETRY_MS);
    },
    /* 降级(E7): 票据满额 503 / 连续 3 轮建流失败 -> GET 轮询兜底(同契约轮询级延迟);
     * 降级态徽标「已断连」照显; 恢复 = 60s 静默重试一次流(保守侧)或页面重开抽屉。 */
    _qbStreamDegrade(scope) {
      const st = this._qbStreams && this._qbStreams[scope];
      if (!st || !st.want) return;
      if (st.es) { st.es.close(); st.es = null; }
      st.state = "degraded";
      if (!st.degraded) {
        st.degraded = true;
        this._qbPollStart(scope);  // GET 轮询接管(immediate 首拍; loading 互斥/悬挂兜底同口径)
      }
      this._qbStallBadgeSyncChart(scope);
      if (!st.retry) {
        st.retry = setTimeout(() => {
          st.retry = null;
          if (!st.want || st.es) return;
          st.failRun = 0;
          st.state = "connecting";
          this._qbStreamConnect(scope);
        }, _QB_STREAM_RETRY_DEGRADE_MS);
      }
    },
    /* 立即 GET 重拉(D9 断档/静默/降级恢复共用): loading 在途即是对账(竞态纪律);
     * 3s 节流(reconcileAt)防断档风暴(持续过载下每帧断档 -> 至多 1 次/3s); force 支路
     * (降级恢复)不受节流挡 —— 恢复后需要对一次账, 且距上次重拉必然已远。 */
    _qbStreamPullNow(scope, force) {
      const st = this._qbStreams && this._qbStreams[scope];
      if (!st || !st.want || st.degraded) return;
      if (this[_QB_SCOPES[scope].loading]) return;
      const now = Date.now();
      if (!force && st.reconcileAt && now - st.reconcileAt < _QB_STREAM_RETRY_MS) return;
      st.reconcileAt = now;
      this._qbLoad(scope);
    },
    /* 对账(E4): 30s 对账定时器的执行面 —— 就是节流版立即重拉 */
    _qbReconcile(scope) {
      this._qbStreamPullNow(scope);
    },
    /* 数据帧到达(seq 连续性判定 + 尾点合并 + 徽标消显): 见模块级 _qbStreamAppend 注与
     * 本节头注。帧合并不折叠组(组粒度归位 = 30s 对账 GET / 断档重拉); 合并后走既有
     * $nextTick -> _qbChartBuild 链(判定帧照常: L0/L1/F5 补点/roll 均按变长点列适配)。 */
    _qbStreamFrame(scope, fr) {
      const st = this._qbStreams && this._qbStreams[scope];
      if (!st || !st.want) return;
      const pts = fr && Array.isArray(fr.points) ? fr.points : null;
      if (!pts || !pts.length) return;  // 坏帧/空帧忽略(空帧 = 静默信号, 不是数据面事件)
      const seq = Number(fr.seq);
      if (!Number.isFinite(seq)) return;
      st.failRun = 0;  // 本连产出过数据帧: 失败计数清零(评审 T4a-R2 单点 —— onopen 不清,
      // 空闪连可累计到上限降级; 正常瞬断在来帧后照常归零)
      if (st.seq == null) {
        st.seq = seq;  // 首帧基线: 断档检测在基线之后(后端契约 —— 订阅归零 seq 重计)
      } else if (seq === st.seq + 1) {
        st.seq = seq;  // 连续
      } else {
        // 断档(队列满丢弃留痕)或回退(服务端重计): seq 重基线 + 立即 GET 重拉(D9)
        st.seq = seq;
        this._qbStreamPullNow(scope);
      }
      const d = this[_QB_SCOPES[scope].data];
      let advanced = false;
      // 隐藏节流单点(渲染与数据面同门): 页面隐藏只合并不重建 —— 修剪门与渲染门共用本值,
      // 同拍不齐会让 store 列与冻结显示列失恒等(回场悬停错位一拍, 评审轮2 minor)。隐藏期
      // 不剪不建, 回场后下一可见帧修剪与重建同拍完成(追加不动既有索引, 隐藏期 store 与
      // 冻结显示列恒对齐; 长度界有 cap 截断兜底)。
      const live = !document.hidden;
      if (d && Array.isArray(d.points)) {
        const cap = _QB_RAW_POINTS_MAX + _QB_STREAM_TAIL_HEADROOM;
        for (const p of pts) advanced = _qbStreamAppend(d.points, st.tail, p, cap) || advanced;
        // 保留窗头部修剪(详 _qbTrimStaleHead 节注): 列不变量 = [anchor − (span+margin), anchor]
        // (修剪线视口锚优先、尾点回落; margin = 2×组距 —— 视口左缘滑动期恒有真实历史可裁,
        // G-B 防回潮; 26-11-21-1704 的名义窗剪把余量一并剪掉, 左缺口只能靠显示层补点回补 ——
        // 本轮补点退役, 余量改由数据层承担)。修剪在**数据入口面**落地(单列恒等: store 列 ==
        // 显示列, 悬停/缺口索引零记账); 降级 GET 轮询与对账落袋不在此面(整列替换 + 历史保留
        // 合并, 见 _qbStreamOnLoad)。
        if (live) {
          const spanS = d.meta && d.meta.schema === 2 ? Number(d.meta.span_s) : 0;
          if (spanS > 0) {
            const stepS = Number(d.meta && d.meta.interval_s);
            // 修剪线锚 = 视口锚(单调, 领先尾时列仍覆盖视口左缘 —— G-B 防回潮; 平常锚=尾同形)
            const uB = this._qbCharts && this._qbCharts[scope];
            const aT = uB && uB._qbBeat && uB._qbBeat.anchor > 0 ? uB._qbBeat.anchor : 0;
            const trimmed = _qbTrimStaleHead(d.points, spanS + (stepS > 0 ? stepS * 2 : 0), aT);
            if (trimmed !== d.points) d.points = trimmed;
          }
        }
      }
      const tEnd = Number(pts[pts.length - 1] && pts[pts.length - 1].t);
      if (tEnd > 0) st.lastT = Math.max(st.lastT, tEnd);  // 徽标量纲: 末样本 ts vs 墙钟
      if (advanced) {
        st.silentPull = false;  // 新帧到 = 静默解除
        // 页面隐藏: 合并照常(纯数据面), 渲染等回场(下一帧/对账补上 —— 节流最小化, 见节头注)
        if (live) this.$nextTick(() => this._qbChartBuild(scope));
        this._qbStallBadgeSyncChart(scope);  // 恢复(新帧到)即消显, 不等 watchdog 下一跳
      }
    },
    /* GET 落袋 = 对账基准单点(_qbLoad 成功落袋处调用): 事件尾点按 ts 归并(不得回退) ——
     * 只保留 t > GET 列末 t 的点追加回显示列(其余已被本次 GET 的组粒度列折叠), 缓冲同步
     * 收窄; 末样本 t / 沉默基线 / pullFail 随真值落袋归位。
     * 历史保留合并(尾锚显式视口不变量(2)的左缘数据面, 计划 26-11-22-0858): GET 整列替换会把
     * 余量列清空(后端响应 = 名义窗 [t0, t1], 窗外前缀不产组点), 若本 GET 恰打断在途滑动,
     * 下一拍视口左缘落在列首左侧 -> 左缺口(G-B)。旧 store 列(_qbLoad 替换前快照)中小于
     * 新列头且 ≥ 余量线的真值点并入列头(真实历史观测, 与后端窗首回看同源) —— 数据层等价
     * 替代补点携带(F5 退役), 无状态无门; 未打断时新列头 == 视口左缘, 保留集恒空(零成本)。 */
    _qbStreamOnLoad(scope, data, oldPoints) {
      const st = this._qbStreams && this._qbStreams[scope];
      if (!st || !st.want) return;
      st.pullFail = false;
      const pts = (data && Array.isArray(data.points)) ? data.points : [];
      const cut = pts.length ? Number(pts[pts.length - 1].t) : 0;
      if (cut > 0) st.lastT = Math.max(st.lastT, cut);
      st.tail = st.tail.filter((p) => p.t > cut);
      const d = this[_QB_SCOPES[scope].data];
      if (d && Array.isArray(d.points) && st.tail.length) {
        const cap = _QB_RAW_POINTS_MAX + _QB_STREAM_TAIL_HEADROOM;
        for (const p of st.tail) {
          // 缓冲升序且恒 > cut, 逐点严格前推(不折叠组); book=false: 缓冲就是迭代源, 不回写
          if (_qbStreamAppend(d.points, st.tail, p, cap, false) && d.points.length > cap) {
            d.points.splice(0, d.points.length - cap);
          }
        }
      }
      if (d && Array.isArray(d.points) && d.points.length && oldPoints && oldPoints.length) {
        const spanS = Number(d.meta && d.meta.span_s);
        const stepS = Number(d.meta && d.meta.interval_s);
        if (spanS > 0) {
          // 余量线 = 视口锚 − (span + margin)(margin = 2×组距, 与 _qbStreamFrame 修剪线同式;
          // 锚领先尾时按锚 —— 保留合并必须覆盖视口左缘的裁剪数据面)
          const tailT = Number(d.points[d.points.length - 1] && d.points[d.points.length - 1].t);
          const stL = this._qbCharts && this._qbCharts[scope] && this._qbCharts[scope]._qbBeat;
          const aT = stL && stL.anchor > 0 ? Math.max(stL.anchor, tailT) : tailT;
          const keepLine = aT - spanS - (stepS > 0 ? stepS * 2 : 0);
          const retained = _qbRetainHistory(oldPoints, d.points, keepLine);
          if (retained.length) d.points = retained.concat(d.points);
        }
      }
      this._qbStallBadgeSyncChart(scope);
    },
    /* watchdog 1s 跳(徽标文案步进 + 静默沿重拉): 静默起显沿立即 GET 一次(D9), 之后由 30s
     * 对账兜周期; 静默解除沿复位 silentPull(下一次静默重新判)。徽标同步随跳走。 */
    _qbStallTick(scope) {
      const st = this._qbStreams && this._qbStreams[scope];
      if (!st || !st.want) return;
      const def = _QB_SCOPES[scope];
      if (!def.active(this)) return;
      const si = this._qbPollMs(scope) / 1000;
      const lag = st.lastT > 0 ? Date.now() / 1000 - st.lastT : 0;
      if (lag > si * _QB_STREAM_SILENCE_X) {
        if (!st.silentPull && st.state === "live" && !st.degraded) {
          st.silentPull = true;
          this._qbStreamPullNow(scope);
        }
      } else {
        st.silentPull = false;
      }
      this._qbStallBadgeSyncChart(scope);
    },
    /* ---------------- 停流/断连徽标(D3, plan 26-11-18-0037; 冻结可见 ≠ 无数据) ----------------
     * 尾点旁 DOM 常驻层内联小字: 挂点复用 _qbFxAnchorEnsure 同款幂等建面(.u-wrap 末位)+ 同步位
     * (判定线 x = L+W 一带, 绘图区顶沿 —— 菱形在末点 y, 顶沿不遮; pointer-events:none /
     * z-index 照 tooltip 惯例 views.css .hist-tip)。样式单点 _qbChartInjectCss(四皮肤零侵入)。
     * 两文案两态(D3/R7):
     *   冻结 = 「滞后 Ns」 —— 流活着(live)但末样本 ts 落后墙钟超过 3 x si(N = 滞后秒数取整);
     *     主循环停顿/断流未恢复的诚实等待, 不谎报断连; pullFail(对账 GET 也在失败)时升格
     *     「已断连」(两条取数路径都断了)。
     *   断连 = 「已断连」 —— 流断开且重连中(retry)/降级态(degraded, E7 徽标照显);
     *     connecting(票据/握手在途, 亚秒级)不惊扰, 失败即入 retry。
     * 恢复自动消显: 新帧到(_qbStreamFrame 改 lastT)/seq 续上/降级恢复(_qbStreamOnOpen)都
     *   顺路调徽标同步, 不等 watchdog 下一跳。文本/位置均变值才写(逐秒跳不制造无谓布局)。
     * 同步点: _qbFxAnchorSync 顶部搭车(四处几何同步点覆盖面一致 —— 徽标不受 FX 门控, 放
     *   anc 早退之前)+ watchdog 每跳 + 帧到达 + 状态迁移。 */
    _qbStallText(scope, st) {
      if (st.degraded || st.state === "retry") return "已断连";
      if (st.state !== "live") return "";  // connecting: 票据/握手在途(亚秒级), 不惊扰
      const si = this._qbPollMs(scope) / 1000;
      const lag = st.lastT > 0 ? Math.floor(Date.now() / 1000 - st.lastT) : 0;
      if (!(lag > si * _QB_STREAM_SILENCE_X)) return "";
      return st.pullFail ? "已断连" : "滞后 " + lag + "s";
    },
    _qbStallBadgeEnsure(u) {
      const wrap = u.root && typeof u.root.querySelector === "function"
        ? u.root.querySelector(".u-wrap") : null;
      if (!wrap) return;
      // 幂等建(与 _qbFxAnchorEnsure 同款纪律): 图记录活着且元件还在(快路 setData 复用)就零操作;
      // 残留防御: 摘掉孤儿再建。元件随 u.destroy 拆 root 一并拆除(换肤/重建零残留)。
      if (u._qbStallBadge && u._qbStallBadge.isConnected) return;
      if (u._qbStallBadge && u._qbStallBadge.parentElement) u._qbStallBadge.remove();
      const el = document.createElement("div");
      el.className = "qb-stall-badge";
      el.style.display = "none";  // 初始隐藏: 首次同步(文案 + 位置)前不显形
      wrap.appendChild(el);       // 挂 .u-wrap 末位: 画布与 .u-over 之上, 随 u.destroy 一并拆除
      u._qbStallBadge = el;
    },
    _qbStallBadgeSync(u) {
      const el = u && u._qbStallBadge;
      if (!el) return;
      const scope = u._qbScope;
      const st = scope && this._qbStreams && this._qbStreams[scope];
      const text = st && st.want ? this._qbStallText(scope, st) : "";
      if (el._aqbStallText !== text) {
        el._aqbStallText = text;
        el.textContent = text;
        el.classList.toggle("qb-stall-down", text === "已断连");
      }
      const hide = () => { if (el.style.display !== "none") el.style.display = "none"; };
      if (!text) { hide(); return; }
      const px = (typeof uPlot !== "undefined" && uPlot.pxRatio) || 1;
      const bb = u.bbox;
      if (!bb || !(bb.width > 0) || !(bb.height > 0)) { hide(); return; }
      const x = bb.left / px + bb.width / px;  // 判定线 x = L + W(菱形/画布 tipX 同源) —— 文字右缘
      const y = bb.top / px + 3;               // 绘图区顶沿(尾点旁; 菱形在末点 y, 顶沿不遮)
      el.style.display = "";
      if (el._aqbStallX !== x || el._aqbStallY !== y) {
        el._aqbStallX = x;
        el._aqbStallY = y;
        el.style.left = x + "px";
        el.style.top = y + "px";
      }
    },
    _qbStallBadgeSyncChart(scope) {
      const u = this._qbCharts && this._qbCharts[scope];
      if (u) this._qbStallBadgeSync(u);
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
    /* 缺口斜纹(drawClear 钩子 = 画在系列**之下**): 只给**数据链中间**的缺口(缺口点游程,
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
     * lead 等级 ≥ 1(双轨皆缺口/真 0 -> null, L0/L1 照常 —— D2/I10; 值>0 恒 ≥Lv.1 —— F1)。 */
    _qbFxSpawn(u, tl, dxTip, needsShift, yMax) {
      const cfg = window.AQB_FX_CFG;
      if (!cfg || cfg.on !== true) return null;
      const tr = u._qbBeat.tracks;
      const lead = _qbFxLead(tr.up, tr.dl);
      if (!lead) return null;
      const g = this._qbFxGeom(u);
      if (!(g.W > 0) || !(g.H > 0) || !(yMax > 0)) return null;
      const xs = u.data[0];
      const n = xs.length;
      // 尾锚显式视口(计划 26-11-22-0858): span = 名义窗长(st.span —— 列含余量后列跨度不再是
      // 窗长, 旧「xs[n-1] − xs[pad]」随补点退役), pxPerT 与锚滑动同尺; dxTip = 锚位移
      // (anchorTo − anchorFrom) —— t=0 末点越出判定线的像素距(新样本自右缘滑入, 视口两缘
      // 同步平移), 与帧循环 L0 位移同源。
      const spanVp = u._qbBeat && u._qbBeat.span > 0 ? u._qbBeat.span : 0;
      const pxPerT = spanVp > 0 ? g.W / spanVp : 0;
      const dxPx = (needsShift ? dxTip : 0) * pxPerT;   // t=0 末点越出判定线的像素距(锚滑动偏置)
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
      // 清单恒满额、与配色档解耦(评审 major): calm 档零粒子的唯一闸在绘制侧 eff 逐帧门 ——
      // spawn 侧冻 palette 会让「calm 判定帧 specs 全不建 -> 拍内切出 calm」余下冲击窗零粒子
      // 到下一拍才恢复(违 §05.3「立即; 粒子池重建」), 且 alloc.merge=0 把切片带 yCenter 退
      // lead 末点 y(带中心漂移)。密度满额解耦(F8)与切片无条件生成同款先例。
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
      // R6 横向线条清单(撕裂切片 + 梳齿): **判定帧一次生成, 同拍逐像素冻结**(只判定帧重算 ——
      // §03 R6 冻结纪律; random 对照档也因此拍内不闪)。强度(n/带宽/长度/alpha)由 lead 等级
      // 与 Δ 确定性决定, 长相(层内相位/缩进/配色)由 hash01(拍序号, 槽位) 分层采样 —— 拍序号
      // 取尾桶时间戳(每拍唯一且单调, 同拍重绘共用本清单); cfg.tear 对照档在 spawn 定型, 拍内
      // 切换下一拍生效(对照档非逐帧面)。清单**无条件**生成, 绘制侧按 cfg.palette === "glitch"
      // 逐帧门控(palette 拍内切入/切出下一帧生效 —— 清单冻结 palette 会让切入口整拍无切片)。
      // 撕裂带中心 = merge 时两轨 y 中点(缺口退 lead 末点 y, 同上), 否则 lead 末点 y;
      // 梳齿带 = 两轨末点 y 包络(缺口退 lead), 带高 <28px 展开到 ±14(与切片锚带同源)。
      const powD = Math.min(1, Math.max(0, tr[lead].delta / 0.5));
      const tearMode = cfg.tear;
      const yCenter = alloc.merge > 0 ? yMerge : yOf(tr[lead].shown);
      const halfBand = (0.08 + 0.30 * powD) * g.H;
      const slices = _qbFxTearSlices(lv, yCenter, halfBand, powD, seed, tearMode, g.T, g.T + g.H);
      const yLeadC = yOf(tr[lead].shown);
      let cLo = Math.min(tr.up.live ? yUp : yLeadC, tr.dl.live ? yDl : yLeadC);
      let cHi = Math.max(tr.up.live ? yUp : yLeadC, tr.dl.live ? yDl : yLeadC);
      if (cHi - cLo < 28) {
        const cm = (cLo + cHi) / 2;
        cLo = cm - 14;
        cHi = cm + 14;
      }
      const comb = _qbFxComb(tearMode === "fixed" ? 7 : (_QB_FX_COMB_COUNT[lv] || 3),
        cLo, cHi, powD, seed, tearMode, g.T, g.T + g.H);   // C11: fixed 对照档恒 7(模板 demo:1212)
      // 次区光点资格(每轨: live 且 level ≥ 1 —— 真 0/缺口轨零装饰, I10/D2; 值>0 恒 ≥Lv.1 后
      // 资格行自动满足, 无需改判据 —— F1 消费面核查结论 26-11-14-1313)
      const tail = [];
      if (tr.up.live && tr.up.level > 0) tail.push("up");
      if (tr.dl.live && tr.dl.level > 0) tail.push("dl");
      return {
        lead, lv, gapScale, rMax, cap, alloc, specs, slices, comb, tail,
        act: { up: tr.up.live && tr.up.level > 0, dl: tr.dl.live && tr.dl.level > 0 },
        pxPerT,
        dxTip: needsShift ? dxTip : 0,   // t=0 末点越出判定线的锚位移(新样本自右缘滑入)
        beatMs: tl.beat,
        burstMs: tl.impactMs,
      };
    },
    /* drawAxes 装饰段(uPlot 网格之后、系列原生之前 —— 装饰压网格不压曲线, I6)。生效条件逐帧
     * 复核(cfg.on !== true 即零绘制 —— 拍内关总开关下一帧生效); 背景零铺色(I11/G7): 本钩子
     * 唯一的 fillRect 是撕裂切片的 1px 级横条(R6 明示「切片是 1px 级 fillRect, 不构成铺底」;
     * 梳齿的 1px 级 fillRect 在 _qbDrawFxScan), 其余全部 stroke / 小多边形 fill。 */
    _qbDrawFx(u, tk) {
      const st = u._qbBeat;
      const a = st && st.anim;
      if (!a) return;
      if (a.phase === "tail") {
        // 次区相位: 判定线余晖线(C6) + 全宽巡回光点(C5)。像素位置由 _qbTailFrame 现算;
        // 光点走轨道语义色极轻不着 Lv(I10), 余晖线走 Lv 表联动单点且不挂 neon 门(D7)。
        const px = this._qbCanvasScale(u);
        const ctx = u.ctx;
        const tl = a.tl;
        const qt = tl && tl.tailMs > 0
          ? Math.min(1, Math.max(0, (a.clock - tl.beat) / tl.tailMs)) : 0;
        // —— 余晖线(C6 模板保真二轮照补, demo:1395-1399 同式): 判定线全高 stroke lw1,
        //     rgba(lvColor, 0.14×(1−qt)) 线性回落; 不挂 neon 门且 calm 档亦显 —— D7/I11 例外
        //     注记, 色走 Lv 表联动单点 _qbFxLvColor(fx.lv, grade); I9 装饰指令修订注记:
        //     新增余晖线 +1 stroke 仅 tail 窗内(与冲击闪光 +1 同理), 束体 ≤23 / 束+切片 ≤28 /
        //     横线 ≤12 预算原样不抬 ——
        const fx = a.fx;
        if (fx && fx.lv && qt < 1) {
          const cfg = window.AQB_FX_CFG;
          const lvColor = _qbFxLvColor(fx.lv, !!(cfg && cfg.layers && cfg.layers.grade === true));
          const aLine = 0.14 * (1 - qt);
          if (aLine > 0) {
            const L = u.bbox.left / px;
            const T = u.bbox.top / px;
            const W = u.bbox.width / px;
            const H = u.bbox.height / px;
            ctx.globalAlpha = 1;
            ctx.strokeStyle = _qbFxFade(lvColor, aLine);
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(L + W - 0.5, T);
            ctx.lineTo(L + W - 0.5, T + H);
            ctx.stroke();
          }
        }
        // 光点: 4 边菱形 r2.2 rot=t/500(C5 模板同式)复用 _qbFxPolyPath 单点; 颜色仍轨道
        // 语义色 tk.up/tk.down, 极轻不着 Lv(I10)。每轨 ≤2 错峰由 _qbTailFrame 落位。
        const pts = a.fxTail && a.fxTail.pts;
        if (pts && pts.length) {
          const rot = a.clock / 500;
          for (const pt of pts) {
            ctx.globalAlpha = pt.alpha;
            ctx.fillStyle = pt.k === "up" ? tk.up : tk.down;
            _qbFxPolyPath(ctx, pt.x, pt.y, 2.2, 4, rot);
            ctx.fill();
          }
        }
        ctx.restore();
        return;
      }
      const fx = a.fx;
      if (!fx) return;
      const cfg = window.AQB_FX_CFG;
      if (!cfg || cfg.on !== true) return;
      const t = a.clock;
      // I9 逐元素窗改判(模板保真二轮): 顶门改 0.7×beat「最大窗」粗滤 —— 粒子(0.55)/N(0.33)/
      // 切片(0.25)/环(0.6)/束(0.7)各自保留独立窗检查(在各自块内), 光带无独立窗(顶门内画,
      // alpha 0.6×beat 后自然归零 —— B1)。
      if (!(t < fx.beatMs * _QB_FX_TOP_RATIO)) return;
      const px = this._qbCanvasScale(u);
      const ctx = u.ctx;
      const L = u.bbox.left / px;
      const T = u.bbox.top / px;
      const W = u.bbox.width / px;
      const H = u.bbox.height / px;
      // F5(plan 26-11-14-1313): clip 右缘放宽到画布右缘(同 _qbDrawFxScan 评审 blocker 修复先例
      // —— 判定线右侧留白是环/粒子/菱形锚的可见域, 无轴面内容); 左/上/下缘不动。
      const canvasW = ctx.canvas && ctx.canvas.width ? ctx.canvas.width / px : L + W;
      ctx.beginPath();
      ctx.rect(L, T, Math.max(W, canvasW - L), H);
      ctx.clip();   // 装饰不出绘图区(右缘放宽到画布右缘 —— F5; 与缺口斜纹同口径仅左/上/下缘)
      // 尾锚显式视口(计划 26-11-22-0858): tip 位移 = 剩余锚位移(anchorTo − 在途锚, _qbAnimAnchorAt
      // 单点) —— 视口两缘同步平移下末点自判定线右侧滑入, 装饰原点与曲线末点同尺(旧 lastDxMax
      // /lastDx 分离记账随双锚退役)。
      const dxTip = a.needsShift ? (a.anchorTo - _qbAnimAnchorAt(a)) : 0;
      const tipX = L + W + dxTip * fx.pxPerT;      // 末点像素 x(随锚平移滑动)
      const carry = (dxTip - fx.dxTip) * fx.pxPerT;  // 粒子随末点一起滑动(L0 同步)
      const yOf = (v) => T + H * (1 - Math.min(v, a.yMax) / a.yMax);
      const tr = st.tracks;
      const yUp = yOf(tr.up.shown);
      const yDl = yOf(tr.dl.shown);
      const lvColor = _qbFxLvColor(fx.lv, cfg.layers.grade === true);   // T5 联动单点(S2-b)
      const blurCap = _QB_FX_BLUR_CAPS[cfg.palette] != null
        ? _QB_FX_BLUR_CAPS[cfg.palette] : _QB_FX_BLUR_CAPS.neon;
      const q = _qbFxNeonQ(t, fx.beatMs);        // N 层回落系数(≤0.33×beat —— I9/I11)
      const neon = cfg.neon === true && q > 0;
      // —— T2 光带爬升层(cfg.layers.band; S2-b, plan §03 T2 行 + L1 aside): 末点插值 shown
      //     的视觉表达 —— 末点从 prev 爬向 shown 的渐变光带(轨道语义色, 底透明 -> 顶峰值),
      //     **两轨都必须画**(读数过渡, 不占 I9 装饰预算; 无独立窗 —— 顶门 0.7×beat 内画,
      //     alpha 随收敛进度 pConv 在 0.6×beat 处自然归零, B1 模板保真二轮)。
      //     impact 窗 shown=prev 时光带零长, <0.75px 不落笔。N 数值光带辉光
      //     bandHalo(白名单)只 lead 轨一道 —— 同帧 blur 描边 = 环外圈(<=2) + 光带(1), I9 辉光
      //     预算修订 <=5(环外圈 <=2 + bandHalo 1 + 曲线辉光 2 已于 S3 落地; blurCap×q, calm 档上限
      //     0 自然退化为纯描边)。cfg.impact 滑杆(0-1)是峰值 alpha 的强度源(原型 S.impact
      //     同式)。 ——
      if (cfg.layers.band === true) {
        const pConv = Math.min(1, t / (fx.beatMs * _QB_FX_CONV_END_RATIO));
        const bandA = _QB_FX_BAND_ALPHA * (1 - pConv)
          * Math.min(1, Math.max(0, Number(cfg.impact)));
        if (bandA > 0.01) {
          for (const k of ["up", "dl"]) {
            if (!fx.act[k]) continue;
            const yOld = yOf(tr[k].prev);
            const yNew = yOf(tr[k].shown);
            if (!(Math.abs(yNew - yOld) >= 0.75)) continue;   // 零长/亚可见不落笔
            const grad = ctx.createLinearGradient(0, yOld, 0, yNew);
            grad.addColorStop(0, _qbFxFade(k === "up" ? tk.up : tk.down, 0));
            grad.addColorStop(1, _qbFxFade(k === "up" ? tk.up : tk.down, bandA));
            ctx.globalAlpha = 1;
            ctx.strokeStyle = grad;
            ctx.lineWidth = _QB_FX_BAND_WIDTH;
            ctx.beginPath();
            ctx.moveTo(tipX, yOld);
            ctx.lineTo(tipX, yNew);
            ctx.stroke();
            if (neon && k === fx.lead) {   // bandHalo: 同路径再描一道 blur 辉光(仅 lead —— 计入同帧 ≤5 次预算)
              ctx.globalAlpha = _QB_FX_BAND_HALO_ALPHA * q;
              ctx.strokeStyle = lvColor;
              ctx.shadowBlur = Math.round(blurCap * q);
              ctx.shadowColor = lvColor;
              ctx.stroke();
              ctx.shadowBlur = 0;
              ctx.shadowColor = "transparent";
            }
          }
        }
      }
      // 本帧落位清单(D3 逐帧仲裁: dual/密度拍内改参下一帧生效 —— 密度逐帧经 partCap 现算,
      // 配合 spawn 满额清单 + 下方 m 钳制; merge = 两轨皆 live 取 y 中点、缺口退 lead 末点 y
      // (与 spawn 同式 —— 缺口轨 shown=null 会落底边假中点, I10/D4), 单反馈色取 lead Lv 色
      // —— D3-c; lead = 只主导轨; both(默认) = 各活性轨一落位, 环不占粒子预算故 eff 为 0 也
      // 保留环落位)
      // calm 档零粒子逐帧门(plan §04 原型 partCap 的 isCalm 口径; §10「克制档零粒子」原文)。
      // 这是 calm 零粒子的唯一闸: spawn 恒满额清单(与密度解耦同款), 故 palette 两个方向都
      // 下一帧生效(§05.3「立即; 粒子池重建」) —— 切入 calm 零粒、切出 calm 恢复, 与切片
      // glitch 门类比对称; eff=0 经 m=min(specs.length, n) 钳制落零粒。isCalm 的 reduce 分量
      // 由 spawn 顶门 cfg.on !== true 承接(on=false 时根本不进绘制面)。原型 partCap 另有
      // leadLevel()<=1->0 门, Lv.1 发粒子系用户拍板维持现状(P9 未采纳), 生产只采纳 calm 分量。
      const effCap = cfg.palette === "calm" ? 0 : _qbFxPartCap(fx.lv, cfg.particles);
      const eff = _qbFxAlloc(cfg.dual, effCap, fx.lead);
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
      // C3 模板半套系数(rScale): both 各轨半套 0.5 / lead 1 / merge 1(模板 demo:1388-1390);
      // 未知策略回落 both 同 alloc 口径(D3-b) -> 0.5。imp = 面板冲击强度(环 alpha 与切片共用)。
      const ringScale = cfg.dual === "lead" || cfg.dual === "merge" ? 1 : 0.5;
      const imp = Math.min(1, Math.max(0, Number(cfg.impact)));
      const ringT = _qbFxRingAt(t, fx.beatMs, ringScale, fx.gapScale, imp);
      // —— 几何环(C3 模板式 demo:1294-1300): 线性扩张 r=(4+24pf)×rScale×gapScale, alpha 联
      //     impact, lw2, **rot = t/300 旋转**(S2 接线 —— 模板同式); 近底/近顶钳制(P3 拍板,
      //     F5): 环心 y clamp 进 [T+终态半径, T+H-终态半径], 终态半径 = (4+24)×rScale×gapScale
      //     (保真二轮: 半径源由 rMax 改环终态值) —— 环完整可见, 允许与末点轻微分离; 钳的是
      //     绘制面, 菱形锚(数据标记)仍走真位。终态值冻结现算(不随帧生长)避免环心在扩张期
      //     抖动; 绘图区过矮(上下界反转)退中点。
      const ringRMax = 28 * ringScale * fx.gapScale;
      const ringY = (sp) => {
        const yLo = T + ringRMax;
        const yHi = T + H - ringRMax;
        return yHi > yLo ? Math.min(Math.max(sp.y, yLo), yHi) : T + H / 2;
      };
      if (ringT && ringT.r > 0) {
        ctx.lineWidth = 2;   // C3: 模板 lw2(旧 1.5 -> 2, 保真二轮)
        ctx.globalAlpha = ringT.alpha;
        const ringRot = t / 300;   // C3 模板 demo:1297 同式
        for (const sp of spots) {
          ctx.strokeStyle = sp.color;
          _qbFxPolyPath(ctx, tipX, ringY(sp), ringT.r, sides, ringRot);
          ctx.stroke();
        }
      }
      // —— N 环外圈辉光(白名单 ringOuter; blur 结构不动 —— A 类 ringOuter: blur = 配色上限 ×
      //     q ≤ 上限)。C3 外圈新式(S2): 半径 (9+31×pf)×rScale×gapScale 独立扩张(替换旧恒
      //     +3px), alpha 0.55×(1−pf)×impact×rScale×gapScale(模板 demo:1298 outer(9+31pf,...,
      //     0.55) 同式, ×gapScale 为生产 D4 适配; 旧 q×ringT.alpha 衰减退役), rot+0.4 与主环
      //     错相 —— 同帧 blur 描边 = 环外圈 ≤2 + T2 bandHalo 1, I9 辉光预算 ≤5(曲线辉光
      //     2 预留 S3) ——
      if (neon && ringT && ringT.r > 0) {
        const os = ringScale * fx.gapScale;
        ctx.globalAlpha = 0.55 * (1 - ringT.pf) * imp * os;
        ctx.strokeStyle = lvColor;
        ctx.lineWidth = 1;
        ctx.shadowBlur = Math.round(blurCap * q);
        ctx.shadowColor = lvColor;
        const outerRot = t / 300 + 0.4;   // C3 模板 outer() rot+0.4 同式
        for (const sp of spots) {
          _qbFxPolyPath(ctx, tipX, ringY(sp), (9 + 31 * ringT.pf) * os, sides, outerRot);
          ctx.stroke();
        }
        ctx.shadowBlur = 0;
        ctx.shadowColor = "transparent";
      }
      // —— 粒子(V3: 三/四/五边碎片本体轨道语义色, N 外圈描边着 Lv 色 —— 白名单 partOuter;
      //     三阶段: 爆发 ×4.5 / 拖尾减速透明 / 0.55×beat 后零绘制; t=0 首帧最亮与判定线同帧) ——
      //     近底镜像反弹(P3 拍板, F5): y 越绘图区底缘按 2*(T+H) - y 折回 —— 末点贴底的低流量
      //     拍粒子不再集体被底缘裁没; 只反弹底缘, 左/上缘维持裁剪(与 clip 口径一致)。
      if (cfg.layers.particles === true) {
        const yFloor = T + H;
        for (const sp of spots) {
          if (!sp.specs || !(sp.n > 0)) continue;
          const m = Math.min(sp.specs.length, sp.n);
          for (let i = 0; i < m; i++) {
            const ps = _qbFxParticleAt(t, fx.beatMs, fx.burstMs, sp.specs[i], carry, i, imp);
            if (!ps || !(ps.alpha > 0)) continue;
            const py = ps.y > yFloor ? 2 * yFloor - ps.y : ps.y;
            ctx.globalAlpha = ps.alpha;
            ctx.fillStyle = sp.color;
            _qbFxPolyPath(ctx, ps.x, py, sp.specs[i].size, sp.specs[i].sides, ps.rot);
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
      // —— R6 撕裂切片(C2 模板保真二轮: 门 = 非 calm 且 (glitch || lv>=2) —— 不再 glitch
      //     唯一门, 默认霓虹档 Lv>=2 即画(模板 demo:1088); calm 排除系评审修复裁决: 模板
      //     demo:1086 isCalm() 早退在门表达式之前, 计划 §02 C2「不限配色」系只抄 :1088 漏看
      //     :1086 的引用疏漏 —— 按用户既定「C 类按模板修」拍板以模板为准, 计划侧修订记录
      //     留 S6 回写; 厚 1.5(Lv.3 2.0; fixed 对照档 3, demo:1096); 独立窗 0.25×beat q 现算
      //     (demo:1091); ≤5 条细 fillRect, 长度/色池/缩进按 R6 清单, x 向 ±3q 微震 ≤5px(S1
      //     已落); 抽屉入场 rAF 追赶循环在途时暂停 —— §09「故障微震与抽屉动画耦合」: 逐帧改
      //     dock 高会经 ResizeObserver -> u.setSize 连锁重画近似「闪」, 让位检测读
      //     drawer_general.js 挂在同一 Vue 实例上的 _drawerAnimRaf(入场/收场循环句柄, 在途
      //     非零 —— 全局入场态可读, 无需时间窗近似)) ——
      const sq = Math.max(0, 1 - t / (fx.beatMs * _QB_FX_SLICE_RATIO));   // C2 独立窗 q
      if (fx.slices && fx.slices.length && cfg.palette !== "calm"
        && (cfg.palette === "glitch" || fx.lv >= 2) && sq > 0 && !this._drawerAnimRaf) {
        const pool = [lvColor, _QB_FX_TEAR_MAGENTA, fx.lead === "up" ? tk.up : tk.down];
        const th = cfg.tear === "fixed" ? 3 : (fx.lv >= 3 ? 2 : 1.5);   // C2 厚度(模板 demo:1096)
        for (const sl of fx.slices) {
          ctx.globalAlpha = sl.alpha * sq * imp;
          ctx.fillStyle = pool[sl.ci] || pool[0];
          ctx.fillRect(L + W - sl.len - sl.inset + sl.offX * sq, sl.y, sl.len, th);
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
        // —— N 判定线小菱形(C10 模板保真二轮照补, demo:1053 同式 poly(xJudge,y,2.2q+1,4,
        //     t/300) alpha 0.7q×impact; neon 门内 —— 模板同门; 大半被 F2 DOM 常驻锚覆盖属
        //     预期(D3 拍板), 锚间隙/滑入期可见) ——
        for (const k of ["up", "dl"]) {
          if (!fx.act[k]) continue;
          const y = k === "up" ? yUp : yDl;
          ctx.globalAlpha = 0.7 * q * imp;
          ctx.fillStyle = lvColor;
          _qbFxPolyPath(ctx, L + W, y, 2.2 * q + 1, 4, t / 300);
          ctx.fill();
        }
      }
      // —— 角落 Lv 徽标(C9/D7 模板保真二轮: 移出 neon 门常显 —— 门 = cfg.on 且 fx 在场(本
      //     方法顶门), alpha 0.85 恒定无 q 衰减, 11px, 文案 "Lv.X · lead 上传/下载"(模板
      //     demo:1446-1449 同式); 色走 Lv 表(grade 联动)—— I11 例外注记: 非 N 局部装饰不挂
      //     neon 门, neon=false 白名单断言面相应收窄) ——
      ctx.globalAlpha = 0.85;
      ctx.fillStyle = lvColor;
      ctx.font = "11px ui-monospace, Consolas, monospace";
      ctx.textAlign = "right";
      ctx.textBaseline = "top";
      ctx.fillText("Lv." + fx.lv + " · lead " + (fx.lead === "up" ? "上传" : "下载"), L + W - 4, T + 4);
      // —— 判定帧全高冲击闪光(C4 模板保真二轮照补, demo:1373-1377 同式: t < impactMs 时
      //     判定线全高 stroke, lw2, alpha 0.75×(1−t/impactMs)×impact 线性回落; 不挂 neon 门
      //     且 calm 档亦显 —— D7/I11 例外注记, 色走 Lv 表; I9 装饰指令修订注记: 新增冲击
      //     闪光 +1 stroke 仅 impact 窗内(0.12×beat), 束体 ≤23 / 束+切片 ≤28 / 横线 ≤12
      //     预算原样不抬) ——
      if (t < fx.burstMs) {
        const flA = 0.75 * (1 - t / fx.burstMs) * imp;
        if (flA > 0) {
          ctx.globalAlpha = 1;
          ctx.strokeStyle = _qbFxFade(lvColor, flA);
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.moveTo(L + W - 0.5, T);
          ctx.lineTo(L + W - 0.5, T + H);
          ctx.stroke();
        }
      }
      ctx.restore();
      // —— T4 扫描束(双相位六层束; cfg.layers.scan 逐帧门, 方法内自含 save/scale/clip) ——
      // !必须在本钩子自身 restore **之后**调用(评审 blocker 修复): 束体 clip 放宽到画布右缘
      // —— 判定线右侧是画布边距区(无曲线/网格/轴标), 相位 A 的「从右侧留白滑入」与硬核/右侧
      // 色散/彗尾/梳齿必须落在留白内才有墨量, 而嵌套 clip 只收不放, 在上方绘图区 clip 内无法
      // 放宽。层序不变: drawAxes 整段(含 restore 之后的自含落笔)先于系列原生 —— 装饰仍不压
      // 曲线(I6); 回声行程语义不变(从判定线向左 ≤span, 全程在绘图区右缘内, I9-R7)。
      this._qbDrawFxScan(u, tk);
    },
    /* T4 扫描束(S2-b, plan §03 T4 行/D17/D19 + §02 R5/R7): 双相位六层束 —— 相位 A(0–0.12beat
     * = 冲击窗, 与之同长)细束从右侧留白 1.2 格滑入判定线(easeOut 收敛, t=0 首帧即有晕光探入);
     * 相位 B 亮束钉在判定线按幂 fade 衰减, 回声(1px 包络核 + 淡晕双笔)在 0.18–0.45beat 匀速
     * 越线 span = clamp(0.22×绘图宽, 100, 200) px, 按 pow(1 − d/span, 0.85) 距离衰减, d ≥ span
     * 几何硬停(该帧零回声指令, 不是把 alpha 压到看不见 —— D19; 束体仍在)。束体结构(R5):
     * 亚像素 1px 硬核(x+0.5 对齐) + 34/24/16/10/5/2.5px 六层晕(低 alpha 叠层逼近高斯; 宽度感
     * 分级已退役 A2 —— 恒按表) + 双侧 ±1.6px 青/品红色散(仅前 0.5beat) + 5 段非
     * 对称彗尾(只在来向=右拖) + 梳齿 3/5/7 条(R6, spawn 冻结清单); 纵向亮度按两轨末点 y 包络
     * 起落(渐变, 峰贴近 <0.08 合并单峰; 缺口轨退 lead 末点 y)。T6 内束强度 = cfg.impact ×
     * 0.78(R5 D17), 双轨共享同一道束。色相走 T5 联动单点(grade 关恒 Lv.1 色)。
     * 预算(I9-R5/R6): 束体逐帧 ≤23 条绘制指令(6 晕 + 1 核 + 2 色散 + 5 彗尾 + ≤7 梳齿 +
     * 2 回声); 零整块 fillRect 铺底(梳齿是 1px 级 fillRect, 高度字面量 1); 束 fade 窗
     * 0.7×beat(B2 模板保真二轮改判 —— 旧 0.55×beat 提前消失), 顶门最大窗 0.7×beat(I9 逐
     * 元素窗改判); calm 配色零束体(plan §10 束体探针第 6 条); cfg.layers.scan 逐帧门
     * (拍内改参下一帧生效); 回声按曲线包络着色(扫过曲线时最亮)。亮束止于判定线不横穿数据:
     * 除回声外全部竖笔 x ≥ 绘图区右缘(晕/彗尾以 lineWidth 向两侧渗, 探针断言的是落笔 x)。
     * !clip 口径(评审 blocker 修复): 本方法**自含** save + scale(pxRatio) + clip + restore,
     * 且 clip 放宽到画布右缘 —— 判定线右侧是画布边距区(无曲线/网格/轴标), 相位 A「从右侧留白
     * 滑入」与硬核/右侧色散/彗尾/梳齿落在留白内才有墨量(x0 恒 ≥ 判定线, 若钳在绘图区 [L,R]
     * 内则这批竖笔逐帧零渲染); 调用点在 _qbDrawFx 自身 restore 之后(嵌套 clip 只收不放)。
     * 层序不变: drawAxes 整段先于系列原生(I6); 回声从判定线向左 ≤span, 仍在绘图区右缘内。 */
    _qbDrawFxScan(u, tk) {
      const st = u._qbBeat;
      const a = st && st.anim;
      if (!a || a.phase === "tail" || !a.fx) return;
      const cfg = window.AQB_FX_CFG;
      if (!cfg || cfg.on !== true || cfg.layers.scan !== true) return;
      if (cfg.palette === "calm") return;   // 克制档束体零绘制(plan §10 束体探针第 6 条)
      const fx = a.fx;
      const t = a.clock;
      if (!(t < fx.beatMs * _QB_FX_TOP_RATIO)) return;   // 顶门最大窗 0.7×beat(I9 逐元素窗改判)
      const px = (typeof uPlot !== "undefined" && uPlot.pxRatio) || 1;
      const L = u.bbox.left / px;
      const T = u.bbox.top / px;
      const W = u.bbox.width / px;
      const H = u.bbox.height / px;
      const imp = Math.min(1, Math.max(0, Number(cfg.impact)));
      const a0 = imp * _QB_FX_BEAM_INTENSITY;
      if (!(a0 > 0.02)) return;   // impact 关到底: 全零 alpha 不落笔
      const ctx = u.ctx;
      const xs = u.data[0];
      const stepT = xs && xs.length > 1 ? xs[1] - xs[0] : 0;
      const cellPx = Math.max(0, stepT * fx.pxPerT);   // 一格像素宽(1.2 格行程的「格」)
      const R = L + W;
      // 画布右缘(CSS px): 束体 clip 的右界 —— 判定线右侧留白对束体可见性必需(见方法头注)
      const canvasW = u.ctx.canvas && u.ctx.canvas.width ? u.ctx.canvas.width / px : L + W;
      const lvColor = _qbFxLvColor(fx.lv, cfg.layers.grade === true);   // T5 联动单点
      const pEnt = Math.min(1, t / Math.max(1, fx.burstMs));   // 相位 A: 与冲击窗同长(0.12beat)
      const x0 = R + cellPx * 1.2 * (1 - _qbFxEaseOut(pEnt));
      // B2 束 fade 窗(模板保真二轮): 0.7×beat(模板 demo:1173 fade=(1−t/(0.7beat))^1.4 同式
      // —— 旧 0.55×beat 提前消失改判; 束/彗尾/梳齿同窗)
      const fade = Math.pow(1 - Math.min(1, t / (fx.beatMs * _QB_FX_BEAM_RATIO)), 1.4);
      const tr = st.tracks;
      const yOf = (v) => T + H * (1 - Math.min(Math.max(v, 0), a.yMax) / a.yMax);
      const yLeadS = yOf(tr[fx.lead].shown);
      const yUpS = tr.up.live ? yOf(tr.up.shown) : yLeadS;    // 缺口轨退 lead 末点 y(I10/D4)
      const yDlS = tr.dl.live ? yOf(tr.dl.shown) : yLeadS;
      const stops = _qbFxBeamStops((yUpS - T) / H, (yDlS - T) / H);
      const env = ctx.createLinearGradient(0, T, 0, T + H);
      const envPeak = fade * a0;
      for (const s2 of stops) {
        env.addColorStop(s2.p, _qbFxFade(lvColor, Math.min(1, s2.a * envPeak)));
      }
      ctx.save();
      ctx.scale(px, px);   // 自含 CSS px 坐标系(与 _qbCanvasScale 同式; 不嵌调用方状态 —— 调用点已 restore)
      ctx.beginPath();
      ctx.rect(L, T, Math.max(W, canvasW - L), H);   // 放宽到画布右缘(评审 blocker 修复 —— 见方法头注)
      ctx.clip();
      // —— 六层晕(宽 -> 窄): 低 alpha 多层叠加逼近高斯衰减, 避免「一道硬边光条」;
      //     宽度恒按表(A2 回退: 束宽度感分级退役 —— 模板无宽度感系数) ——
      ctx.strokeStyle = env;
      for (const hw of _QB_FX_BEAM_HALO) {
        ctx.lineWidth = hw[0];
        ctx.globalAlpha = hw[1];
        ctx.beginPath();
        ctx.moveTo(x0, T);
        ctx.lineTo(x0, T + H);
        ctx.stroke();
      }
      // —— 亚像素 1px 硬核(x+0.5 对齐 —— 1x DPR 下不被抗锯齿糊掉) ——
      ctx.globalAlpha = 1;
      ctx.strokeStyle = _qbFxFade("#F2FFFF", 0.86 * fade * a0);
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(x0 + 0.5, T);
      ctx.lineTo(x0 + 0.5, T + H);
      ctx.stroke();
      // —— 双侧色散(青左/品红右, ±1.6px; 仅前 0.5beat —— 替代旧「青->品红整条渐变」) ——
      if (t < fx.beatMs * 0.5) {
        const dfade = (1 - t / (fx.beatMs * 0.5)) * a0;
        ctx.lineWidth = 1;
        ctx.strokeStyle = _qbFxFade(_QB_FX_DISPERSION[0], 0.3 * dfade);
        ctx.beginPath();
        ctx.moveTo(x0 - 1.6, T);
        ctx.lineTo(x0 - 1.6, T + H);
        ctx.stroke();
        ctx.strokeStyle = _qbFxFade(_QB_FX_DISPERSION[1], 0.26 * dfade);
        ctx.beginPath();
        ctx.moveTo(x0 + 1.6, T);
        ctx.lineTo(x0 + 1.6, T + H);
        ctx.stroke();
      }
      // —— 非对称彗尾(只在来向=右拖, 5 段宽度/alpha 逐段递减 -> 有方向感) ——
      ctx.strokeStyle = env;
      for (let j = 0; j < 5; j++) {
        ctx.globalAlpha = 0.42 * Math.pow(0.7, j) * fade;
        ctx.lineWidth = 1.2 * Math.pow(0.68, j);
        const tx = x0 + 2.5 + j * 3.2;
        ctx.beginPath();
        ctx.moveTo(tx, T);
        ctx.lineTo(tx, T + H);
        ctx.stroke();
      }
      // —— 梳齿(R6: 3/5/7 条按 lead 等级, spawn 冻结清单 —— 同拍逐像素恒同; 1px 级 fillRect,
      //     不构成铺底; 相位随拍序号变化) ——
      if (fx.comb && fx.comb.length) {
        ctx.globalAlpha = 0.26 * fade * a0;
        ctx.fillStyle = lvColor;
        for (const ct of fx.comb) {
          ctx.fillRect(x0 + 2.5 + ct.dx, ct.y, ct.len, 1);
        }
      }
      // —— 相位 B 回声(R7/D19): 0.18–0.45beat 匀速越线 span px, pow(1 − d/span, 0.85) 距离
      //     衰减, d ≥ span 几何硬停(fall 恒 0 -> 该帧零回声指令; epsilon 0.004 只免掉不可见
      //     残笔, 硬停判据仍是 d ≥ span 的几何门) ——
      const span = _qbFxEchoSpan(cfg.echoSpan, W);
      const eq = _qbFxEchoQ(t, fx.beatMs);
      const d = span * eq;
      const fall = eq > 0 ? _qbFxEchoFall(d, span) : 0;   // 0.18beat 前回声未起拍(q=0 不落笔)
      if (fall > 0.004) {
        const ex = R - d;
        const echoEnv = ctx.createLinearGradient(0, T, 0, T + H);
        for (const s2 of stops) {
          echoEnv.addColorStop(s2.p,
            _qbFxFade(lvColor, Math.min(1, s2.a * _QB_FX_ECHO_ALPHA_CAP * fall * a0)));
        }
        ctx.globalAlpha = 1;
        ctx.strokeStyle = echoEnv;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(ex + 0.5, T);
        ctx.lineTo(ex + 0.5, T + H);
        ctx.stroke();
        ctx.globalAlpha = _QB_FX_ECHO_HALO_ALPHA * fall;   // B4: 淡晕 0.34×fall(模板 demo:1246;
        //  旧 0.20 上限对 9px 晕退役 —— I9 修订表已记), 否则残影拖半条带
        ctx.lineWidth = 9;
        ctx.beginPath();
        ctx.moveTo(ex + 0.5, T);
        ctx.lineTo(ex + 0.5, T + H);
        ctx.stroke();
      }
      ctx.globalAlpha = 1;
      ctx.restore();
    },
    /* ================= 常驻菱形锚 DOM 层(F2, plan 26-11-14-1313 §03 F2/D2) =================
     * 末点旋转方块的常驻环境层: 两枚 .qb-fx-anchor DOM 方块挂 uPlot .u-wrap, 旋转走 CSS
     * keyframes(2639ms linear infinite, 注入单点 _qbChartInjectCss; 模板 rot=t/420 弧度/ms,
     * 一圈 2*pi*420=2639ms, 旧 420ms 系单位误读) —— 合成器动画, 零 rAF/
     * 零重绘(D2: 不进 draw 循环; 背景恒静态, 菱形是 DOM 元件不引入画布铺底 —— G5/R4)。
     * 位置 = 判定线 x(bbox 右缘, 与画布 tipX 静止位/模板 xJudge 同源) + 末点 y(双轨 shown 的
     * 显示面换算, 公式与画布 yOf 同源; 动画期 yMax 读 anim.yMax 与画布钉档一致, 静止期读当前
     * y 轴档 —— I4: 显示面与钉档换算恒同一把尺)。同步点收敛四处(R3):
     *   1 判定帧  _qbBeatStart(轨道推进后同帧写 —— 覆盖零变化拍/早退拍, 锚位不落旧值)
     *   2 收敛帧  _qbBeatConverge(setData 交还 auto 后 x 重申锚视口 + y 成对钉档)
     *   3 锚钩子  _qbDrawFxAnchor 顶部(每次画布提交顺路重写 —— L0 左移/L1 收敛的逐帧位置与
     *     提交帧对齐; 挂钩子顶部而非门后, 无拍间隙的重绘也能带上锚)
     *   4 ResizeObserver(宿主尺寸变 -> 判定线 x 与绘图区几何变, u.setSize 后立即重写)
     * 另有门面单点: _qbFxCfgSync(cfg.on/palette 变化即时生效, 不等下一拍)。
     * 门 = cfg.on === true 且图活跃且该轨活性(live && shown != null —— 缺口轨隐藏, I10 模板
     * live 门同款); reduced-motion 双保险: cfg.on 已含 !reduce 分量 + CSS 媒体查询 display:none
     * (P2: 隐藏, 不是静态方块); calm 档 .qb-fx-anchor-calm 退化圆点(模板 isCalm 同款, 类切换
     * 随同步逐次对齐)。颜色 = tk 语义色内联(建图时捕获, 换肤重建即新令牌 —— I10)。 */
    _qbFxAnchorEnsure(u, tk) {
      const wrap = u.root && typeof u.root.querySelector === "function"
        ? u.root.querySelector(".u-wrap") : null;
      if (!wrap) return;
      // 幂等建(与 _qbFxBound 同款纪律): 图记录活着且元件还在(快路 setData 复用)就零操作;
      // 完整重建走 _qbChartDestroy -> u.destroy 拆 root(元件随拆)后新建。残留防御: 摘掉孤儿再建。
      if (u._qbFxAnchors && u._qbFxAnchors.up && u._qbFxAnchors.up.isConnected
        && u._qbFxAnchors.dl && u._qbFxAnchors.dl.isConnected) return;
      if (u._qbFxAnchors) {
        for (const k of ["up", "dl"]) {
          const old = u._qbFxAnchors[k];
          if (old && old.parentElement) old.remove();
        }
      }
      const mk = (k) => {
        const el = document.createElement("div");
        el.className = "qb-fx-anchor qb-fx-anchor-" + k;
        el.style.background = k === "up" ? tk.up : tk.down;   // 语义色内联(I10/D1)
        el.style.display = "none";   // 初始隐藏: 首次同步(位置+门)前不显形
        wrap.appendChild(el);        // 挂 .u-wrap 末位: 画布与 .u-over 之上, 随 u.destroy 一并拆除
        return el;
      };
      u._qbFxAnchors = { up: mk("up"), dl: mk("dl") };
    },
    /* 位置/门同步单点(四处同步点与门面共用的唯一落笔处): 只写变值(left/top/display/class),
     * 逐帧调用不制造无谓布局; 几何/门任一不满足即隐藏, 不猜位置。u._qbFxAnchors 不存在(建图
     * 前的提交/桩环境)零操作。
     * D3 停流/断连徽标(T4a)同步搭车: 放 anc 早退**之前** —— 徽标不受 FX 门控(cfg.on 关也照
     * 显), 同步点覆盖面与锚一致(判定帧/收敛帧/锚钩子/RO)。 */
    _qbFxAnchorSync(u) {
      this._qbStallBadgeSync(u);
      const anc = u && u._qbFxAnchors;
      if (!anc) return;
      const cfg = window.AQB_FX_CFG;
      const st = u._qbBeat;
      const geomOk = !!(cfg && cfg.on === true && st && u.root && u.root.isConnected
        && u.bbox && u.bbox.width > 0 && u.bbox.height > 0);
      const calm = !!(cfg && cfg.palette === "calm");
      const pos = {};
      if (geomOk) {
        const px = (typeof uPlot !== "undefined" && uPlot.pxRatio) || 1;
        const L = u.bbox.left / px;
        const T = u.bbox.top / px;
        const W = u.bbox.width / px;
        const H = u.bbox.height / px;
        const a = st.anim && st.anim.phase !== "tail" ? st.anim : null;
        const yMax = a && a.yMax > 0 ? a.yMax
          : (u.scales && u.scales.y && u.scales.y.max > 0 ? u.scales.y.max : 1);
        const x = L + W;   // 判定线 x
        const yOf = (v) => T + H * (1 - Math.min(v, yMax) / yMax);
        for (const k of ["up", "dl"]) {
          const tr = st.tracks && st.tracks[k];
          if (tr && tr.live && tr.shown != null) pos[k] = [x, yOf(tr.shown)];
        }
      }
      for (const k of ["up", "dl"]) {
        const el = anc[k];
        if (!el) continue;
        el.classList.toggle("qb-fx-anchor-calm", calm);
        const p = pos[k];
        if (!p) {
          if (el.style.display !== "none") el.style.display = "none";
          continue;
        }
        if (el.style.display !== "") el.style.display = "";
        if (el._aqbAnchorX !== p[0] || el._aqbAnchorY !== p[1]) {
          el._aqbAnchorX = p[0];
          el._aqbAnchorY = p[1];
          el.style.left = p[0] + "px";
          el.style.top = p[1] + "px";
        }
      }
    },
    /* 曲线辉光(draw 钩子 = 系列原生描边之后、_qbDrawFxAnchor 之前): 常驻 + 视口裁剪(缺陷一+二
     * 重构, plan 26-11-26-0227 §3.1)。判据 = cfg.on===true 且 up/dl 轨 u._qbBeat.tracks[k].level>0
     * —— level 拍间仍在, 不依赖 a.fx / anim 缺席亦画; 无 t<beat 时间窗、无 phase==="tail" 门:
     * 生产 draw 钩子是事件驱动重绘(非模板 demo 连续 rAF), 旧「拍内窗」在拍间必然留空导致辉光
     * 每拍闪现; 常驻后每次重绘都重描, 拍间画布保留末帧像素, 视觉常驻(模板 demo:1407-1409 观感)。
     * 自身 ctx.save() + rect(L,T,W,H) 严格绘图区 clip(不采 F5 右缘放宽 —— R2: 不画进判定线右
     * 留白; 缺陷二根因: 遍历全列而视口外点在 valToPos 下落到绘图区左缘外, 无自身 clip 时带 blur
     * 画到图例上方) —— 遍历仍走全列 xs.length, 视口外点由 clip 裁除; 缺口 null 段 gStarted=false
     * 断段重新 moveTo(spanGaps:false 语义, 与系列原生同款, 禁止桥接); shadowColor=轨语义色
     * (tk 单源, 同旧 A1), shadowBlur = blurCap x (dual lead/both ? 1 : 0.45), 帧末清 0(帧内
     * 非零赋值点恰 1 —— I9 预算峰值 <=5 不叠加); 曲线宽仍 _qbFxCurveWidth(常规 2.4 / calm 2,
     * calm blurCap=0 自然退化普通描边)。yMax: 动画期取 anim.yMax(L1 收敛插值面钉档), 拍间/tail
     * 回落 u.scales.y.max(同 _qbFxAnchorSync 口径)。双轨 level 均 <=0(真 0/缺口轨)早退零操作
     * (不 touch ctx 状态)。 */
    _qbDrawFxCurveGlow(u, tk) {
      const cfg = window.AQB_FX_CFG;
      if (!cfg || cfg.on !== true || !u.bbox || !u.ctx || !u.data || !u.data.length) return;
      const st = u._qbBeat;
      const tracks = st && st.tracks;
      if (!tracks || (!(tracks.up.level > 0) && !(tracks.dl.level > 0))) return;
      const a = st.anim && st.anim.phase !== "tail" ? st.anim : null;
      const yMax = a && a.yMax > 0 ? a.yMax
        : (u.scales && u.scales.y && u.scales.y.max > 0 ? u.scales.y.max : 1);
      const px = this._qbCanvasScale(u);
      const ctx = u.ctx;
      const L = u.bbox.left / px;
      const T = u.bbox.top / px;
      const W = u.bbox.width / px;
      const H = u.bbox.height / px;
      const yOf = (v) => T + H * (1 - Math.min(v, yMax) / yMax);
      const xs = u.data[0];
      const blurCap = _QB_FX_BLUR_CAPS[cfg.palette] != null
        ? _QB_FX_BLUR_CAPS[cfg.palette] : _QB_FX_BLUR_CAPS.neon;
      const glowBlur = Math.round(blurCap * ((cfg.dual === "lead" || cfg.dual === "both") ? 1 : 0.45));
      ctx.save();
      ctx.beginPath();
      ctx.rect(L, T, W, H);
      ctx.clip();
      ctx.shadowBlur = glowBlur;   // 单一施加点(两轨共用), 帧末清零 —— I9 非零赋值点恰 1
      for (const k of ["up", "dl"]) {
        if (!(tracks[k].level > 0)) continue;
        const col = u.data[k === "up" ? 1 : 2];
        const trackCol = k === "up" ? tk.up : tk.down;
        ctx.strokeStyle = trackCol;
        ctx.shadowColor = trackCol;
        ctx.lineWidth = this._qbFxCurveWidth(cfg.palette);
        ctx.globalAlpha = 1;
        ctx.beginPath();
        let gStarted = false;
        for (let i = 0; i < xs.length; i++) {
          const v = col[i];
          if (v == null) { gStarted = false; continue; }
          const x = L + u.valToPos(xs[i], "x");
          const y = yOf(v);
          if (!gStarted) {
            ctx.moveTo(x, y);
            gStarted = true;
          } else {
            ctx.lineTo(x, y);
          }
        }
        if (gStarted) ctx.stroke();
      }
      ctx.shadowBlur = 0;
      ctx.globalAlpha = 1;
      ctx.restore();
    },
    /* draw 装饰段(系列之上): lead 策略从属轨描边加亮(D3-a: 只加亮描边 + 小锚点; 语义色加宽半透明
     * 短段, 不着 Lv —— I10) -> N 锚辉光(白名单
     * anchorHalo, C7 模板式 6 边环随末点 tipX 滑动; 辉光色走 T5 联动单点, grade 关恒 Lv.1 —— S2-b)。
     * 曲线辉光已抽独立常驻函数 _qbDrawFxCurveGlow(draw 钩子接线在系列原生之后、本方法之前 ——
     * 缺陷一+二重构, plan 26-11-26-0227 §3.1), 不再在本方法内重描。
     * F2(plan 26-11-14-1313): 末点菱形**本体**移除画布侧(常驻层交 DOM .qb-fx-anchor, 本方法
     * 顶部顺路重写其位置 —— 避免双画); 画布只留拍内脉冲辉光, 与 DOM 常驻锚短暂分离属预期(C7 位置
     * 改 tipX 随末点滑, DOM 锚仍钉判定线 x —— 模板亦如此, 二者不要求逐帧同位置)。clip 放宽
     * (F5)与 lead 从属轨加亮原样保留 —— 加亮段仍画在画布。 */
    _qbDrawFxAnchor(u, tk) {
      this._qbFxAnchorSync(u);   // F2 同步点之锚钩子: 每次画布提交顺路重写 DOM 锚位(位置/门/类)
      const st = u._qbBeat;
      const a = st && st.anim;
      if (!a || a.phase === "tail" || !a.fx) return;
      const cfg = window.AQB_FX_CFG;
      if (!cfg || cfg.on !== true) return;
      const fx = a.fx;
      const t = a.clock;
      const px = this._qbCanvasScale(u);
      const ctx = u.ctx;
      const L = u.bbox.left / px;
      const T = u.bbox.top / px;
      const W = u.bbox.width / px;
      const H = u.bbox.height / px;
      const yOf = (v) => T + H * (1 - Math.min(v, a.yMax) / a.yMax);
      if (!(t < fx.beatMs * _QB_FX_TOP_RATIO)) return;   // 顶门最大窗 0.7xbeat(仅锚段装饰)
      // F5(plan 26-11-14-1313): clip 右缘放宽到画布右缘(同 _qbDrawFx/_qbDrawFxScan 口径) ——
      // 末点在绘图区右缘的 N 锚辉光右半不再被切(F2 后画布只留辉光, 菱形本体在 DOM 常驻层);
      // 辉光位置取末点滑动 x(tipX, C7 改判); 与 DOM 常驻锚短暂分离属预期, 近底不钳。
      const canvasW = ctx.canvas && ctx.canvas.width ? ctx.canvas.width / px : L + W;
      ctx.beginPath();
      ctx.rect(L, T, Math.max(W, canvasW - L), H);
      ctx.clip();
      const tr = st.tracks;
      const yUp = yOf(tr.up.shown);
      const yDl = yOf(tr.dl.shown);
      const q = _qbFxNeonQ(t, fx.beatMs);
      const neon = cfg.neon === true && q > 0;
      const ens = Math.max(0, 1 - t / (fx.beatMs * _QB_FX_PART_RATIO));
      const lvColor = _qbFxLvColor(fx.lv, cfg.layers.grade === true);   // T5 联动单点(S2-b)
      const imp = Math.min(1, Math.max(0, Number(cfg.impact)));
      const xs = u.data[0];
      const tipX = L + u.valToPos(xs[a.n - 1], "x");   // 末点滑动 x(x 轴真值换算, 同 lead 加亮段)
      // lead 策略从属轨: 末段描边加亮(读绘制面尾点插值 shown; y 钉定档下 yOf 与 uPlot 像素对位)
      if (cfg.dual === "lead") {
        const sub = fx.lead === "up" ? "dl" : "up";
        if (fx.act[sub]) {
          const col = u.data[sub === "up" ? 1 : 2];
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
      // N 锚辉光(白名单 anchorHalo, C7 模板式): 6 边低透明外圈环拍内脉冲 —— F2 后画布侧只留辉光,
      // 菱形本体在 DOM 常驻层; 几何 r=(7+4q)xrolexgapScale / rot=t/320 / alpha=0.5xqximpact,
      // 位置 tipX(末点滑动 x)。与 DOM 常驻锚短暂分离属预期(模板同款), 不要求逐帧同位。
      const haloRot = t / 320;
      for (const k of ["up", "dl"]) {
        if (!fx.act[k]) continue;
        const y = k === "up" ? yUp : yDl;
        const role = cfg.dual === "lead" && k !== fx.lead ? 0.6 : 1;
        const r = (7 + 4 * q) * role * fx.gapScale;
        if (neon) {
          ctx.globalAlpha = 0.5 * q * imp;
          ctx.strokeStyle = lvColor;
          ctx.lineWidth = 1;
          _qbFxPolyPath(ctx, tipX, y, r, 6, haloRot);
          ctx.stroke();
        }
      }
      ctx.restore();
    },
    /* ================= 节拍调度器(S1, plan 26-11-12-1139 §03 L0/L1 + §06) =================
     * 判定帧 = 每次 _qbLoad 成功落袋(续拉快路 setData 之后同帧触发, 见 _qbChartBuild 快路)。
     * 尾锚显式视口(计划 26-11-22-0858 换代, 三不变量): (1)视口恒等式 viewport = [anchor − span,
     * anchor](锚 = 末样本时刻单调递增; auto x range 全窗退役 —— setData 的 resetScales 把 x
     * 交还列全宽 auto(列含余量恒偏宽), 判定帧**无条件**显式 setScale 重申锚视口, 压缩在结构上
     * 不可表达); (2)单列恒等(store 列 == 显示列, 列 = [anchor − (span+margin), anchor] margin=2
     * 组距; 修剪线视口锚优先、尾点回落 —— F5 补点/_qbPad 记账/收敛 slice/悬停扣减整套退役,
     * G-B 左缺口由余量列承担); (3)取数窗口分量(_qbLoad)。左移动画 = 锚点滑动: 锚从旧值 easeOut
     * 滑向新值(shiftMs 时间线承袭), min/max 两缘同步平移 —— 最老一格滑出左缘、新样本自右缘滑入;
     * 打断在途拍从自身存储的在途锚(_qbAnimAnchorAt)续滑, 打断重建零回跳, 旧 _qbInheritedViewport
     * 公式重建退役。
     * 每拍两件事, 驱动源解耦(D2):
     *   L0 视口平移(I8, 数据刷新语义): 真值已 setData 落袋(data / _qbAnchors / tooltip 全部
     *     真值), 绘制视口从滑动起点([anchorPrev − span, anchorPrev] —— 上一收敛视口或打断在途
     *     位)按 easeOut 平移到 [anchorTo − span, anchorTo]; 过渡期不重建 xs、不改 up/dl、
     *     不碰 _qbAnchors; rewin(换窗/重定标/滚动域外)瞬时落地不播动画。
     *   L1 双轨数值收敛(纯数据语义, 非装饰): 两列独立 {prev,target,shown,delta,level,live},
     *     尾点 n-1 在收敛窗(0-0.6 beat, t=0 起步 —— B5/D1)内按 easeOut 从 prev 收敛到 target(u.data 绘制面,
     *     tooltip/悬停锚仍读 Vue points 真值 —— I4, 读数面与本插值面零交集), 收敛帧写回真值。
     * 短路: reduced-motion(AQB_FX_CFG.on === false 的 reduce 分量)显式视口一次落笔 + 瞬时
     * 左移, 无 rAF(I7); 总开关 enabled=false 不短路 —— L0/L1 照常执行(§05.6: 那是数据刷新
     * 语义, 不是装饰); 零变化拍(锚零位移 + 两轨无真变化)零 rAF(显式视口照常落笔)。
     * 时间线常量与公式单点在模块级「节奏内核」节; 逐帧 commit 用 setScale/redraw(不 destroy/
     * new、不碰 loading 空态、不触发 ResizeObserver 连锁 —— I3)。
     * !rAF/performance.now/document 一律函数内惰性取(node 探针 eval 本文件, 顶层不得碰 BOM)。 */
    /* 判定帧开工(快路 setData 之后同帧调用): 打断在途旧拍(新拍以当前视口锚续滑, 禁止回跳 ——
     * I3) -> 推进双轨状态机(每拍必推, 不论动不动效 —— 状态机推进是数据面) -> 按需起 rAF。 */
    _qbBeatStart(scope, u) {
      if (!u || !u.root || !u.root.isConnected || !u.data || !u.data.length) return;
      const st = u._qbBeat;
      if (!st) return;  // 建图时初始化(见 _qbChartBuild); 无记录 = 异常旧图, 不动画
      const xs = u.data[0];
      const n = xs.length;
      if (!n) return;
      const cfg = window.AQB_FX_CFG;
      // reduce 判定单点读 AQB_FX_CFG(S0-b 已带有效值 on = enabled && !reduce): on 为假有
      // 两个分量 —— reduce(系统要求减弱动效)才短路, enabled=false(用户关总开关)不短路
      const reduce = !!(cfg && cfg.enabled === true && cfg.on === false);
      // 打断续滑捕获(先于 cancel): 在途滑动拍(_qbAnimAnchorAt 单点)的当前锚位 = 用户正看到
      // 的视口锚 —— 本拍 anchorFrom 取它, 打断重建零回跳; 非滑动在途态(预览/fx-only/次区)
      // 与已收敛拍(anim 缺席)取 null 走原生锚形。锚不依赖列形状 —— 旧方向B捕获的「先于
      // setData 列亲和」时序约束不复存在。
      const animPrev = st.anim;
      const anchorHold = animPrev && animPrev.needsShift && animPrev.preview === undefined
        ? _qbAnimAnchorAt(animPrev) : null;
      this._qbBeatCancel(u);
      // 锚视口判定单点: 锚 = max(上拍锚, 新尾)(单调 —— 旧窗响应晚到不回拖), 组距/窗长变化
      // 或锚位移 > 2 组距 -> rewin 瞬时落地(防假 morph 语义承袭); step/span 取 meta
      // (interval_s/span_s —— schema=2 = k×si / 名义窗长), 缺席回落 st 记账(防御)。
      const dSrc = this[_QB_SCOPES[scope].data];
      const j = _qbAnchorJudge(st, xs[n - 1],
        Number(dSrc && dSrc.meta && dSrc.meta.interval_s),
        Number(dSrc && dSrc.meta && dSrc.meta.span_s));
      // 跨拍记账先行(单调锚 / 组距 / 窗长) —— 收敛帧与本拍所有消费面同源。
      st.anchor = j.anchor;
      st.step = j.step;
      st.span = j.span;
      // 面板状态行「上次真实拍 Xs 前」镜像(§05.3 状态行格式, S3): 真拍判定帧到达即写当前 scope
      // 的墙钟时间(每拍一笔, 非热路径); 只镜像面板浮着的图(scope 对齐 qbCurScope), 其余挂点
      // 的拍不写。Date.now 而非 performance.now: 展示面要墙钟语义(隐藏期冻结的动画时钟不参与)。
      if (scope === this.qbCurScope) this.fxBeatAt = Date.now();
      // 纵轴档位扫描(全列真值 —— 单列恒等下无补点格, 扫描域 = 全列): floor 可视下限按本
      // yMax 换算 —— 不能读 u.scales.y.max(setData 后 auto-y 按列全宽可视窗重算, 与钉档
      // 两把尺 —— I4 一致性)。
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
      // L1 判定推进(D2 双轨独立): 尾桶真值 -> {prev,target,shown,delta,level,live}
      const floor = yMax * _QB_FX_VIS_FLOOR_RATIO;
      const tr = st.tracks;
      const tl = _qbBeatTimeline(this._qbPollMs(scope), cfg ? cfg.shiftRatio : undefined);
      tr.up = _qbFxTrackNext(tr.up, u.data[1] ? u.data[1][n - 1] : null, floor);
      tr.dl = _qbFxTrackNext(tr.dl, u.data[2] ? u.data[2][n - 1] : null, floor);
      // F2 常驻菱形锚 · 同步点 1/4(判定帧): 轨道推进后同帧写锚位 —— 摆在 reduce/零变化早退
      // 之前, 早退拍(瞬时落地)锚位也跟新值/新档走, 不落旧值(显示面 —— I4/I8, 真值面零触碰)。
      this._qbFxAnchorSync(u);
      // 视口锚三态(尾锚显式视口核心):
      //   anchorTo = j.anchor(本拍目标 —— 单调); anchorPrev = 本帧视口锚 = 打断在途位
      //   (anchorHold)或上一收敛锚(j.anchor − delta); disp = anchorTo − anchorPrev(恒 ≥ 0
      //   —— j.anchor ≥ 上拍锚 ≥ 在途锚)。滑动(slide) = 非换窗且有剩余位移 —— 全新位移拍
      //   与打断续滑拍(零 delta 打断: 剩余位移照滑)统一走同一条路, 旧「roll 伪真继承」
      //   特判随统一语义退役; rewin 或零位移 -> 视口一次落笔到目标(瞬时/静止)。
      //   gate 拒绝(instant 档/亚可见长窗)同落瞬时: 显式目标视口(方向A的 auto 落地面退役
      //   —— instant/reduce 档恒定压缩变体随补点退役自然消失, 上档案 D4 就此收口)。
      const haveVp = j.span > 0;
      const anchorTo = j.anchor;
      const anchorPrev = anchorHold != null ? anchorHold : anchorTo - j.delta;
      const disp = anchorTo - anchorPrev;
      const nWin = j.step > 0 && j.span > 0 ? Math.max(1, Math.round(j.span / j.step)) : n;
      // reduce 拍不播滑动(瞬时落地目标锚 —— I7): slide 分量含 !reduce, 否则 reduce 早退前
      // 显式视口会落在滑动起点, 剩余位移滞留到下一拍(电池 S5 钉面)。
      const slide = !reduce && !j.rewin && disp > 0 && haveVp && _qbFxShiftGate(cfg, u, nWin);
      const vAnchor = slide ? anchorPrev : anchorTo;
      const needsTail = !j.rewin && ((tr.up.live && tr.up.prev !== tr.up.target)
        || (tr.dl.live && tr.dl.prev !== tr.dl.target));
      // 显式视口无条件落笔(不变量(1)): setData 已把 x 交还列全宽 auto(含余量, 非真值) ——
      // 判定帧一律重申锚视口(含零变化早退拍/reduce 拍), y 成对钉档(该提交不得按可视窗重推
      // y —— 列全宽 auto 与锚视口的可视窗差异同样会重推)。span 缺席(防御)退回 auto。
      if (haveVp) {
        u.setScale("x", { min: vAnchor - j.span, max: vAnchor });
        u.setScale("y", { min: 0, max: yMax });
      }
      if (reduce) {
        // I7: 真值已由快路 setData 落袋(u.data 即真值), 瞬时平移 = 显式锚视口一次落笔(上方),
        // 无 rAF(旧 auto 落地随显式视口换代)
        tr.up.shown = tr.up.target;
        tr.dl.shown = tr.dl.target;
        return;
      }
      // 零变化拍/不可见位移拍: 数据面瞬时落地(u.data 未被改写本就是真值), L0/L1 零 rAF
      // 优化保留(不播锚滑动/数值收敛 —— D2 的数据静默半边); 显式视口已在上方落笔(静止态)。
      if (!slide && !needsTail) {
        // F6 环境层解绑(plan 26-11-15-1104 D3): fx spawn 判据 = lead 等级 >=1, 与本早退门
        // 解绑 —— 26-11-14-1313 D1(值>0 恒 >=Lv.1)贯彻到全窗。spawn 返回 null(双轨真 0/
        // 缺口, lead=null)仍零装饰零 anim(I10/D2); 带 fx 的拍只跑 fx 的 impact 窗: anim 不带
        // shift/tail, 帧循环 L0/L1 块整体跳过(数据面零 rAF), 收敛帧照常清场(锚同步/次区衔接
        // 全走既有单点 —— anchorFrom/anchorTo 在 needsShift=false 下为惰性, 恒锚直传保持
        // anim 形态与主路同构)。
        tr.up.shown = tr.up.target;
        tr.dl.shown = tr.dl.target;
        const fx = this._qbFxSpawn(u, tl, disp, false, yMax);
        if (fx) {
          st.anim = { anchorFrom: anchorTo, anchorTo, span: j.span, needsShift: false,
            needsTail: false, n, tl, yMax, clock: 0, lastT: 0, lastAnchor: null, fx,
            phase: "impact", easeF: _qbFxCurve(cfg ? cfg.ease : undefined) };
          st.raf = requestAnimationFrame(() => this._qbBeatFrame(scope));
        }
        return;
      }
      // I4 纵轴瞬时定档: 动画期每次提交都会让 uPlot 重推 y(vendor qn: Kl.x 非 null -> An(!0)
      // 重置 series.min/max -> y.auto 按可视窗重算) —— 可视窗随锚平移/显示尾值变化, y 会逐帧
      // 漂移(窗沿峰值出窗即整条曲线垂直跳)。按**新数据全列真值**先算 yMax 钉住(与建图 range
      // 单点同口径: _qbYRange × _qbYCapOf, 不是显示尾值), 起拍与每个平移帧的 setScale("x")
      // 成对补 setScale("y")(Kl.y 非 null 时 qn 原样拷贝、跳过重推); 收敛帧同样成对钉(setData
      // 后 x 重申的 pending 被 redraw 消费时按锚窗可视数据重推, 余量列持峰即泵动 —— 详
      // _qbBeatConverge 节注)。已在上方扫描前置, 此处直接复用同一 yMax。
      // t=0 同帧: 尾点摆回显示值(仅绘制面) + 视口落滑动起点。两处写入都发生在 setData 的
      // 微任务渲染之前(同个同步块), 判定帧首绘即「旧位旧值」—— 与上一拍收敛帧逐像素接续(I3,
      // uPlot 同步块内多次 commit 会被 Un 标志合并成一次渲染, 已读 vendor 确认)。
      if (needsTail) {
        if (tr.up.live && tr.up.prev !== tr.up.target) u.data[1][n - 1] = tr.up.prev;
        if (tr.dl.live && tr.dl.prev !== tr.dl.target) u.data[2][n - 1] = tr.dl.prev;
      }
      // S2 装饰状态(V1 色彩/V2 形状/V3 粒子/N 层/D3 仲裁 + S2-b T2 光带/T4 扫描束/R6 横向
      // 线条, plan §03): t=0 一次性生成, 粒子/切片/梳齿清单确定性伪随机(同拍重绘恒同形)。
      // 拍内改参的生效口径(§05.3/D21): neon/layers.band/layers.particles/layers.scan/
      // layers.grade/tail/palette/dual/echoSpan/impact 逐帧读 AQB_FX_CFG 下一帧生效; 密度
      // (particles)经满额清单 + 绘制侧逐帧钳制下一帧生效; tear 对照档与切片/梳齿清单在
      // spawn 判定帧定型(拍内切档下一拍生效 —— 对照档非逐帧面, 清单冻结=拍内不闪); ease
      // 同为判定帧定型(S3 已接线): 曲线引用冻结进 anim.easeF(_qbFxCurve 单点), 拍内不换式、
      // 下一拍起用 —— D21 唯一例外条款, 避免中途换曲线造成位置跳变。
      // 条件: cfg.on === true(有效值单点)且 lead 等级 ≥ 1 —— reduce 已在上方短路(I7);
      // enabled=false 与 Δ≈0/零流量/缺口轨零装饰但 L0/L1 照常(§05.6/D2/I10)。F6/D3 起
      // 零变化拍(slide/needsTail 双 false)的 spawn 已前置到早退门内(本行只接至少一真的拍)。
      const fx = this._qbFxSpawn(u, tl, disp, slide, yMax);   // tip 位移按锚位移(新样本自右缘滑入)
      // easeF = 判定帧冻结的数值插值曲线(S3, _qbFxCurve 单点): 本拍全程只用它, 拍中改 ease
      // 不换式(D21 例外条款) —— L1 帧循环经 _qbFxShown(track, 原始进度, easeF) 消费。
      st.anim = { anchorFrom: slide ? anchorPrev : anchorTo, anchorTo, span: j.span,
        needsShift: slide, needsTail, n, tl, yMax, clock: 0, lastT: 0,
        lastAnchor: slide ? anchorPrev : null, fx, phase: "impact",
        easeF: _qbFxCurve(cfg ? cfg.ease : undefined) };
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
      // 预览令牌失效门(§05.4 连点重启, S3): anim.preview 携带起拍时的 previewToken, 与状态
      // 本体不一致 = 旧预览残帧(新预览已递增令牌接管调度), 直接失效不动作 —— 结构上
      // _qbBeatCancel 已摘旧 rAF + st.anim 整体替换, 本门是把「令牌递增即令旧帧失效」钉成
      // 可执行契约(调度病理下的兜底), 也给电池一个直接断言面。门能触发即 anim 是**过期**
      // 预览(新预览 anim 的 token 必与当前令牌一致, 走不到这里), 置空后拍内无在途预览 ——
      // 同步清「· 预览中」镜像, 兜底路径不得把它卡成常亮(评审 minor2)。
      if (a.preview !== undefined && a.preview !== st.previewToken) {
        st.anim = null;
        this.fxPreviewing = false;
        return;
      }
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
        if (a.preview !== undefined) {
          this._qbPreviewEnd(scope, u);  // 预览拍末帧: 还原真值显示面(假值不落任何真值面 —— §05.4)
          return;
        }
        this._qbBeatConverge(scope, u);
        return;
      }
      const n = a.n;
      // 逐帧提交守卫: 锚位与尾点 shown 都没变的帧不提交(t=0 同帧已写过同值, 时钟未推进的恢复
      // 首帧亦然) —— setScale/redraw 每笔都是全量路径重建 + 钩子重跑(I9 R8 复核的帧成本),
      // 重复同值提交纯浪费。
      let dxChanged = false;
      let tailChanged = false;
      // L0 锚平移: anchor(t) = anchorFrom + easeOut(clock/shiftMs) × 位移 —— 视口两缘同步
      // 平移([anchor(t) − span, anchor(t)]), 最老一格滑出左缘、新样本自右缘滑入(数据/锚/
      // tooltip 全程真值, 只动视口 —— I4/I8); 打断续滑与逐帧共用 _qbAnimAnchorAt 单点
      // (公式漂移即续滑回跳)。
      if (a.needsShift) {
        // 末帧 ulp 吸附: rem 逼近 0 时把锚精确钳到 anchorTo, 避免残差视口令 uPlot splits
        // 首刻位低一格的单帧回跳(issue 26-11-17-0936; 阈值见 _QB_FX_L0_SNAP_REM —— 单点在
        // _qbAnimAnchorAt)
        const anchor = _qbAnimAnchorAt(a);
        if (anchor !== a.lastAnchor) {
          a.lastAnchor = anchor;
          dxChanged = true;
          u.setScale("x", { min: anchor - a.span, max: anchor });
          u.setScale("y", { min: 0, max: a.yMax });  // 与 x 成对: 该提交不得按平移可视窗重推 y
        }
      }
      // L1: 尾点收敛窗(0-0.6 beat, t=0 起步 —— B5/D1 模板口径)内 shown = prev + (target − prev)
      // × ease(p), 单调无 overshoot(I4/D9); impact 窗(0-0.12 beat)不再钉 prev —— 数值插值
      // 自 t=0 起爬升, 冲击窗只留给 S2 装饰(环/粒子/闪光)。ease 越界夹取保留: p 越界自然
      // 落 prev/target 端点, 不破坏 I4。
      // p 传**原始进度**(S3 接线: 曲线在 _qbFxShown 内单次施加, 判定帧冻结的 anim.easeF 选式
      // —— 修正 S1 遗留的「帧循环预 easeOut + _qbFxShown 再 easeOut」双重施加, 与计划 §03
      // 公式及 §04 演示单次口径对齐); ease 只作用于数值收敛, L0 与装饰运动曲线不随 ease 变。
      if (a.needsTail) {
        const p = a.clock / tl.convergeMs;
        const tr = st.tracks;
        if (tr.up.live && tr.up.prev !== tr.up.target) {
          const shown = _qbFxShown(tr.up, p, a.easeF);
          if (shown !== tr.up.shown) {
            tr.up.shown = shown;
            u.data[1][n - 1] = shown;
            tailChanged = true;
          }
        }
        if (tr.dl.live && tr.dl.prev !== tr.dl.target) {
          const shown = _qbFxShown(tr.dl, p, a.easeF);
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
        // redraw 成对盖住(钉值 = 真窗档位 yMax, 与判定帧/收敛帧钉档同一把尺)。
        u.setScale("y", { min: 0, max: a.yMax });
        u.redraw();
      }
      // S2-a 装饰帧保障(零 Δ 拍兜底, 保留): L0/L1 都无提交的帧(无 shift 长窗且两轨 prev==target
      // 的零变化拍, 或 setScale/shown 同值的恢复首帧)强制重绘一次, 否则粒子/环/切片冻结在 t=0
      // 帧(I5: 冲击 t=0 同帧触发)。converge 改 t=0 起步后 impact 窗内 L1 通常已在逐帧提交,
      // 本分支只守零变化拍(含 0.75px gate 拒绝的 L0), 不再是「尾点冻结在 prev」的常规路径;
      // y 钉成对同上(显示尾值参与可视窗重推会垂直跳)。
      if (a.fx && !dxChanged && !tailChanged && a.clock < a.fx.beatMs * _QB_FX_PART_RATIO) {
        u.setScale("y", { min: 0, max: a.yMax });
        u.redraw();
      }
      st.raf = requestAnimationFrame(() => this._qbBeatFrame(scope));
    },
    /* 次区相位帧(C5 模板保真二轮: tail 光点全宽巡回): ph=(t/1000×0.12+i/2+轨偏移) mod 1
     * (t=相位时钟 a.clock ms, i=每轨光点序号 0/1), 映射整条 u.data[0] 全列(非旧末段 6 桶);
     * 轨偏移取模板 demo:1124 口径 up=0.31/dl=0 —— 同轨两点由 i/2 错峰半周期, 双轨再错 0.31
     * 周期(四路错峰; 若取 0.5 会与 i/2 回绕重合, 四点塌成两相位)。两轨 y 分离。每轨 ≤2(合计 ≤4, 轨道语义色); alpha 0.3×(1−qt)
     * 线性衰减(qt=相位进度, 峰值 ≤0.3; qt→1 归零自然退场, ph 回绕重生即循环淡入 —— 不常驻)。
     * 资格门 live && level>0 沿用 spawn 的 a.fx.tail; 缺口段跳过, 位置 1px 量化 —— 无可见变化
     * 不提交(全量路径重建是帧成本大头, 极轻面不逐帧重绘 —— I9 R8 复核)。返回 true = 次区结束
     * (窗尽/拍内关闭), 调用方清 anim 并补一帧清理提交。 */
    _qbTailFrame(u, a) {
      const tl = a.tl;
      if (!(a.clock < tl.beat + tl.tailMs)) return true;
      const cfg = window.AQB_FX_CFG;
      if (!cfg || cfg.on !== true || cfg.tail !== true) return true;
      const pts = [];
      const xs = u.data[0];
      if (xs && xs.length > 1) {
        const t = a.clock;
        const qt = Math.min(1, Math.max(0, (t - tl.beat) / tl.tailMs));
        const alpha = 0.3 * (1 - qt);
        if (alpha > 0) {
          const px = (typeof uPlot !== "undefined" && uPlot.pxRatio) || 1;
          const L = u.bbox.left / px;
          const T = u.bbox.top / px;
          const H = u.bbox.height / px;
          const xOf = (idx) => L + u.valToPos(xs[idx], "x");
          for (const k of a.fx.tail) {
            const col = u.data[k === "up" ? 1 : 2];
            const off = k === "up" ? 0.31 : 0;   // 轨偏移: up=0.31 / dl=0(模板 demo:1124, 四路错峰)
            for (let i = 0; i < _QB_FX_TAIL_PTS_MAX; i++) {
              const ph = (t / 1000 * 0.12 + i / 2 + off) % 1;
              const idx = ph * (xs.length - 1);
              const i0 = Math.floor(idx);
              const f = idx - i0;
              const i1 = Math.min(i0 + 1, xs.length - 1);
              const v0 = col[i0];
              const v1 = col[i1];
              if (v0 == null || v1 == null) continue;   // 缺口段跳过(曲线断线处无光点 —— D4)
              const x0 = xOf(i0);
              const x1 = xOf(i1);
              pts.push({
                k,
                x: x0 + (x1 - x0) * f,
                y: T + H * (1 - (v0 + (v1 - v0) * f) / a.yMax),
                alpha,
              });
            }
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
    /* 收敛帧: 真值写回 + 显式锚视口重申 + y 成对钉档 + 强制轴重算一次, 一次提交完成。
     * x 视口语义(尾锚显式视口换代): setData(resetScales 默认 true) 会把 x 交还列全宽 auto
     * (列含余量恒偏宽, 非真值), 随后必须显式 setScale 重申锚视口 [st.anchor − st.span,
     * st.anchor](st.anchor 已在判定帧记账到本拍目标 —— 滑动末帧 _qbAnimAnchorAt 的 ulp 吸附
     * 已精确落锚, 重申同值零跳变); 旧「交还 auto + dropPad 摘补点」随单列恒等退役(列不再
     * 有补点可摘, auto 恒偏宽不可作视口)。y 成对钉 a.yMax(I4): x 重申的 pending 由下方
     * redraw(false, true) 消费时 vendor qn(Kl.x 非 null)按锚窗可视数据重推 y, 余量列(左缘
     * 裁剪历史)持峰时峰值被剔出可视窗 —— auto 重推出的可视窗基准 ≠ 判定帧全列钉值, 每拍
     * 纵轴泵动两次(收敛帧掉档/下拍判定帧弹回), 峰值滑出余量才止; 显式钉与本拍判定帧同一
     * 把尺, 终态零跳变。 */
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
      u.setData([u.data[0], u.data[1], u.data[2]]);
      if (st.span > 0 && st.anchor > 0) {
        u.setScale("x", { min: st.anchor - st.span, max: st.anchor });
        u.setScale("y", { min: 0, max: a.yMax });  // 与 x 成对: 该提交不得按锚窗可视数据重推 y
      }
      // 根因二次纠正(issue 26-11-17-0936): uPlot 只在 scale 变化时置轴重算脏标记(mt), 走 Dn()
      // 重算 _splits/_values。收敛帧 setData 的 auto 与显式视口重申可能在数值上相同(span 缺席
      // 防御路/余量恰空的退化列) —— scale 未变 -> 轴不重算 -> 标签慢一拍。这里强制 mt=true 让
      // 本次提交重算一次轴值; 第一参 false 只让 redraw 走 Jn() 提交, 不再写 x scale。
      u.redraw(false, true);
      // F2 常驻菱形锚 · 同步点 2/4(收敛帧): 真值落袋后把锚位写到终值(shown=target), 拍间常驻
      // 位置与曲线尾点对齐 —— setData 提交本会经锚钩子带上, 此处显式落笔钉住计划四处之一(R3)。
      this._qbFxAnchorSync(u);
      // S2-a 次区相位衔接(tail 开启且有活性轨): 主区装饰在本帧已全部回落(粒子 ≤0.55×beat、
      // 环 0.6×beat、N ≤0.33×beat —— 收敛帧零残留)。束 fade 窗 0.7×beat 与调度 animEnd 的
      // 交界(S5 核实结论): animEnd = max(shiftRatio,0.6)×beat 不变(I1); 缺省 shiftRatio=0.6
      // 即 animEnd=0.6×beat, 束 fade 残余 = (1−0.6/0.7)^1.4 ≈ 0.0656, 乘强度 a0=0.78×0.7
      // =0.546 后晕峰 ≈0.036 / 1px 硬核 ≈0.031(绝对 alpha ≈3%, 肉眼不可见), 收敛帧提交即
      // 自然收口无可见截断; shiftRatio≥0.7 时 animEnd 已越 0.7×beat, fade 自然归零。故不改
      // 调度(不动 I1/拍长), 此处转入 tail 相位让次区光点沿整条曲线全宽巡回到下一拍前
      // (窗长 tail = min(period − beat, 2000), 600s 长窗也只铺 2s, 非常驻)。拍内 cfg 在
      // _qbTailFrame 逐帧重读 —— 关闭即下一帧收尾(补一帧清理提交)。n 取落袋后显示列长。
      const tl = a.tl;
      const cfg = window.AQB_FX_CFG;
      if (a.fx && a.fx.tail.length && tl.tailMs > 0 && cfg && cfg.on === true && cfg.tail === true
        && u.root && u.root.isConnected) {
        st.anim = { phase: "tail", n: u.data[0].length, tl, yMax: a.yMax,
          clock: a.clock, lastT: 0,
          anchorFrom: st.anchor, anchorTo: st.anchor, span: st.span,
          needsShift: false, needsTail: false, fx: a.fx, fxTail: { pts: null, sig: "" } };
        st.raf = requestAnimationFrame(() => this._qbBeatFrame(scope));
      }
    },
    /* 终止在途拍(rAF 句柄先摘): _qbBeatStart 打断旧拍 / _qbChartDestroy 销毁 / 宿主被拆三条
     * 路共用的收口。「终止即落真值不留半帧」由各路径原生满足: 打断路新拍 setData 已落真值;
     * 销毁/换肤路整图重建即真窗口 auto range —— 不存在残留偏置的半帧。预览拍(§05.4 真值抢占
     * 的接缝, S3)被终止时假值不在 data 里残留: 抢占路新拍 setData 已整组替换真窗口; 重排路
     * (_qbChartRescale)在取消前先走 _qbPreviewRestore 还原真值显示面。取消预览必须同步清
     * 「· 预览中」镜像(仅翻转沿写, 非热路径)。 */
    _qbBeatCancel(u) {
      if (!u || !u._qbBeat) return;
      const st = u._qbBeat;
      if (st.raf) {
        cancelAnimationFrame(st.raf);
        st.raf = 0;
      }
      if (st.anim && st.anim.preview !== undefined) this.fxPreviewing = false;
      st.anim = null;
    },
    /* ================= 预览一拍(S3, plan 26-11-12-1139 §05.4 六条语义 + D21) =================
     * 与真实拍同构但去掉窗口搬运: 不 shift、不 push、dx ≡ 0(xs / u.scales.x 零变化), 只跑
     * 尾部插值 + 装饰。语义逐条落位:
     *   1 不动窗口   — anim.needsShift=false(锚零位移), 帧循环 L0 块整体跳过(零 setScale("x"));
     *   2 假 Δ 贴近真实量级 — mag = clamp(0.18 + 0.35×粒子密度, 0.10, 0.50)(相对量, 生产数值
     *     域是字节率, 计划伪代码的归一化 ±mag 换算为 shown ± mag×max(shown, 可视下限), 相对
     *     Δ 恒等于 mag —— 与真拍 delta 口径同构), 方向按轨 up 减 / dl 加(伪代码
     *     k === 'dl' ? mag : -mag), 不固定拉满 Lv.3(密度 0.7 -> Δ0.425 Lv.3 / 0 -> 0.10 Lv.2);
     *   3 连点重启   — previewToken 递增令旧帧失效(_qbBeatFrame 令牌门), 从当前显示值重新起拍,
     *     不排队不叠加;
     *   4 真值抢占   — 真拍判定帧 _qbBeatStart 首行 _qbBeatCancel 先取消预览态, 新真值 setData
     *     已整组落袋, 真实拍走正常链路(真值永远优先);
     *   5 不写 store — 零持久化副作用(persistQbFx/localStorage 不出现在预览路径), 真值字段
     *     零改写: 假值只进 u.data 尾点显示面, 末帧 _qbPreviewEnd 还原 + 双轨状态机复位到真值
     *     对齐(下一真拍从真值接续, 假值不留痕);
     *   6 同预算     — spawn 与绘制钩子走真拍同一条代码路径(_qbFxSpawn/_qbDrawFx/_qbDrawFxScan),
     *     I9 预算(粒子 ≤32/束体 ≤23/束+切片 ≤28)不放宽。
     * 生效门: cfg.on === true —— reduce(I7 强退)与 enabled=false 下没有动效可预览, 预览空操作;
     * 真拍主区在途时真值优先同样忽略(§05.4 第 4 条的对偶), 次区装饰相位无真值语义可被接管。
     * 不自动循环: 仅面板「预览一拍」显式点击触发, 无任何定时器(与真实拍撞车且真假不可辨 —— D21)。 */
    _qbPreviewBeat(scope) {
      const s = scope || this.qbCurScope;
      const u = this._qbCharts && this._qbCharts[s];
      const st = u && u._qbBeat;
      if (!u || !st || !u.root || !u.root.isConnected || !u.data || !u.data.length) return;
      const cfg = window.AQB_FX_CFG;
      if (!cfg || cfg.on !== true) return;
      // 真值链路主区在途: 真值优先, 忽略预览(预览/次区装饰相位才可重启/接管 —— §05.4 第 4 条)
      if (st.anim && st.anim.preview === undefined && st.anim.phase !== "tail") return;
      const old = st.anim;
      if (old) this._qbBeatCancel(u);  // 连点重启(作废当前预览)/接管次区相位: 装饰性在途态
      const xs = u.data[0];
      const n = xs.length;
      if (!n) {
        // 早退也须不留痕(评审 minor1, §05.4 第 5 条): 取消的是在途预览时假值已上屏显示面,
        // 走预览还原核心再退(双轨钳在界/数据面清空等角点的连点, 假值不得滞留到下次真值)
        if (old && old.preview !== undefined) this._qbPreviewRestore(u, old);
        return;
      }
      const yMax = u.scales.y && u.scales.y.max > 0 ? u.scales.y.max : 1;
      const floor = yMax * _QB_FX_VIS_FLOOR_RATIO;
      const tr = st.tracks;
      const mag = Math.min(0.5, Math.max(0.1, 0.18 + 0.35 * Math.min(1,
        Math.max(0, Number(cfg.particles)))));
      let moving = 0;
      for (const k of ["up", "dl"]) {
        const c = tr[k];
        if (!c || !c.live || c.shown == null) continue;  // 缺口/死轨不造斜坡(复活直落真值语义)
        c.prev = c.shown;  // 以显示值接续, 禁止回跳(I3; 连点重启亦从当前显示值起 —— §05.4 第 3 条)
        const target = c.prev + (k === "dl" ? mag : -mag) * Math.max(c.prev, floor);
        c.target = Math.max(0, Math.min(target, yMax));  // 非负 + 不越预览钉住的轴(零裁切零跳轴)
        c.delta = Math.abs(c.target - c.prev) / Math.max(c.prev, floor);
        c.level = _qbFxLevel(c.delta, true, c.target);   // 预览拍与真拍同构(同走 target 参 —— F1)
        if (c.prev !== c.target) moving++;
      }
      if (!moving) {
        // 同上(评审 minor1): 双轨钳在界(prev==target, 如 up 钳 0 + dl 钳轴顶)的连点早退,
        // 旧预览假值已上屏 —— 还原真值显示面再退, 不滞留到下次真值落袋(长窗分钟级)
        if (old && old.preview !== undefined) this._qbPreviewRestore(u, old);
        return;
      }
      const token = (st.previewToken || 0) + 1;
      st.previewToken = token;
      // 末帧还原值 = 预览前真值显示面; 连点重启继承首拍捕获值(中途假值永不落还原点)
      const restore = old && old.restore ? old.restore
        : { up: u.data[1] ? u.data[1][n - 1] : null, dl: u.data[2] ? u.data[2][n - 1] : null };
      if (tr.up.live && tr.up.prev !== tr.up.target) u.data[1][n - 1] = tr.up.prev;
      if (tr.dl.live && tr.dl.prev !== tr.dl.target) u.data[2][n - 1] = tr.dl.prev;
      const tl = _qbBeatTimeline(this._qbPollMs(s), cfg.shiftRatio);
      const fx = this._qbFxSpawn(u, tl, 0, false, yMax);  // dxTip=0 + needsShift=false: 不动窗口
      st.anim = {
        preview: token, restore, anchorFrom: st.anchor, anchorTo: st.anchor, span: st.span,
        needsShift: false, needsTail: true, n, tl, yMax,
        clock: 0, lastT: 0, lastAnchor: null, fx, phase: "impact",
        easeF: _qbFxCurve(cfg.ease),
      };
      this.fxPreviewing = true;  // 状态行「· 预览中」镜像(翻转沿写, 绘制热路径不读 Vue)
      st.raf = requestAnimationFrame(() => this._qbBeatFrame(s));
    },
    /* 预览还原核心(不提交): 尾点显示面写回预览前真值 + 双轨状态机复位到真值对齐(delta/level
     * 归零 —— 下一真拍从真值接续, 预览假值不留痕) + 「· 预览中」镜像清。_qbPreviewEnd(末帧)
     * 与 _qbChartRescale(预览在途重排)共用; 提交面由调用方决定(末帧 setData 交还 auto / 重排
     * 走自己的 setData)。不走 _qbBeatConverge: 那是把 target 当真值写回, 预览的 target 是假值。 */
    _qbPreviewRestore(u, a) {
      const n = a.n;
      const rst = a.restore || {};
      if (rst.up != null && u.data[1]) u.data[1][n - 1] = rst.up;
      if (rst.dl != null && u.data[2]) u.data[2][n - 1] = rst.dl;
      const tr = u._qbBeat.tracks;
      for (const k of ["up", "dl"]) {
        const c = tr[k];
        if (!c) continue;
        const v = rst[k];
        c.prev = v;
        c.target = v;
        c.shown = v;
        c.delta = 0;
        c.level = 0;
        c.live = v != null;
      }
      this.fxPreviewing = false;
    },
    /* 预览拍末帧收口(§05.4 第 5 条): 还原真值显示面 + setData + 显式锚视口重申 + y 成对钉档
     * (把预览起拍从当前轴档读到的 yMax 原样钉回 —— setData 交还 auto 后 x 重申的 pending 消费
     * 时 vendor 按锚窗可视数据重推 y, 余量列持峰即与预览钉档两把尺; 成对钉终态零跳变),
     * xs / u.data[0] 全程零变化。 */
    _qbPreviewEnd(scope, u) {
      const st = u._qbBeat;
      const a = st.anim;
      st.anim = null;
      st.raf = 0;
      this._qbPreviewRestore(u, a);
      u.setData([u.data[0], u.data[1], u.data[2]]);
      // 尾锚显式视口(不变量(1)): setData 的 resetScales 交还列全宽 auto(含余量, 非真值) ——
      // 预览收口与收敛帧/rescale 同款显式重申(评审轮1 major: 该写点漏网 = 预览收场视口跳
      // 全列宽一拍, 退役的 auto 落地面从预览路回潮); y 成对钉回起拍读到的 yMax(同一把尺,
      // 不吃锚窗可视重推 —— 与收敛帧同款)。
      if (st.span > 0 && st.anchor > 0) {
        u.setScale("x", { min: st.anchor - st.span, max: st.anchor });
        u.setScale("y", { min: 0, max: a.yMax });
      }
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
        // F2 常驻菱形锚随图清: 元件本体挂 u.root 的 .u-wrap 内, u.destroy 拆 root 时一并拆除;
        // 图记录引用在此显式清(换肤/重建零残留, 与 _qbFxBound 幂等纪律对偶的清面)。
        u._qbFxAnchors = null;
        u._qbStallBadge = null;  // D3 停流/断连徽标随图清(同款纪律; 状态本体在 _qbStreams 不受影响)
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
      //   同时拦 lifecycle._onCtxMenu 的 flags 惰性补拉 —— 图宿主右键不探测(ensureWebFlags 收窄,
      //   S0-a 评审留痕 → 收口档案留痕七), 其余右键面照旧。
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
        // 尾锚显式视口(计划 26-11-22-0858 换代): 快路 = 纯 setData 落袋 + 判定帧 —— F5 补点
        // 构造/携带门/_qbPad 记账与方向B继承捕获整套退役(单列恒等: store 列 == 显示列, 列含
        // 余量; 打断续滑由判定帧读自身在途锚 _qbAnimAnchorAt —— 锚不依赖列形状, 无捕获时序
        // 约束; setData 交还的列全宽 auto 由判定帧显式视口无条件覆盖)。
        prev.setData([data.xs, data.up, data.dl]);
        this._qbBeatStart(scope, prev);  // S1 判定帧: 真值已落袋, 同帧起拍(L0 锚平移 + L1 收敛)
        return;
      }
      this._qbChartDestroy(scope);
      this._qbChartInjectCss();
      this._qbAnchors[scope] = data.anchor;  // 悬停取值用(非响应式实例字段, 同 _qbAnchors 自身先例)
      const tk = this._qbChartTokens();
      const curveW = this._qbFxCurveWidth();   // D4: 建图初值即对齐当前 palette(常规 2.4 / calm 2)
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
          // x 轴标签每帧从实时 splits 现算(issue 26-11-17-0936 第三次纠正): 旧 tick freeze
          // 只冻文字不冻刻位 —— 文字补刷新只跟 sp0 跨刻度走, 与右缘纵线进出事件错相, 两个
          // 独立跳变叠加成用户看到的「数字也跳、但不同时」。去掉冻结后标签与 _splits 同帧
          // 同源; 右缘多线已由建图后挂在 axes[0].splits 的 _qbDropRightEdgeSplits 根除。
          { ...axis, values: (u, splits) => splits.map((ts) => this._qbTickLabel(ts, scope)) },
          // y 轴槽宽 84: fmtSpeed 轴标最长形("999.9 KiB/s"/"3.86 MiB/s" = 11 字符 x 10px 等宽
          // + 内边距), 60 会把标签左缘截掉(实测 "3.86 MiB/s" 只剩 "86 MiB/s") —— 三主题截图自查发现
          { ...axis, size: 84, values: (u, splits) => splits.map(fmtAxisSpeed) },
        ],
        series: [
          { label: "时刻", value: (u, ts) => this.fmtTime(ts) },
          {
            label: "上传", stroke: tk.up, width: curveW,
            spanGaps: false,  // null 桶断线不连线(§5.2 拍板: 纯断线, 无最大跨越)
            points: { show: false, size: 6, filter: (u, sIdx) => _qbIsolatedIdxs(u, sIdx) },
            value: (u, v) => this.fmtSpeed(v),
          },
          {
            label: "下载", stroke: tk.down, width: curveW,
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
          // —— 挂 drawClear 会被网格盖住, 评审 blocker 实证), draw = 系列之上(限速虚线 → 曲线辉光
          // 常驻段 _qbDrawFxCurveGlow → lead 从属轨加亮 + 末点菱形锚)。曲线描边由 uPlot 系列原生画在 drawAxes 之后 = 装饰永远
          // 不压曲线(语义色一行不动 —— I10/D1)。tk 由本次建图捕获 —— 令牌换肤走整图重建,
          // 钩子随新图换新 tk。
          drawClear: [(u) => this._qbDrawGaps(u, tk)],
          drawAxes: [(u) => this._qbDrawFx(u, tk)],
          draw: [(u) => this._qbDrawLimits(u, tk), (u) => this._qbDrawFxCurveGlow(u, tk), (u) => this._qbDrawFxAnchor(u, tk)],
          // 悬停取值通道: uPlot 算好 idx/px, Vue 侧渲染 tooltip(数据/格式化走组件既有成员);
          // 尾锚显式视口(计划 26-11-22-0858)下单列恒等(store 列 == 显示列)—— 索引直通,
          // 旧补点扣减(setCursor 按 _qbPad 扣回真值索引)随补点退役。
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
      // 尾锚显式视口: 建图初始视口 = 锚视口(免首绘 auto 全列宽闪帧); opts min/max 经 vendor
      // 初始化只播种一次 pending(配置 min/max 随后归 null, auto 语义不持久) —— 后续每次
      // 数据落袋由判定帧显式重申。span 缺席(防御)不给 min/max, 退回 auto。
      const spanNom0 = Number(d.meta && d.meta.span_s);
      const anchor0 = data.xs[data.xs.length - 1];
      if (spanNom0 > 0) opts.scales.x.min = anchor0 - spanNom0;
      if (spanNom0 > 0) opts.scales.x.max = anchor0;
      const u = this._qbCharts[scope] = new uPlot(opts, [data.xs, data.up, data.dl], host);
      u._qbScope = scope;  // 停流/断连徽标同步经图记录反查流状态(同步点无 scope 参数, D3)
      // 右缘刻位过滤(issue 26-11-17-0936 第三次纠正): 建图后包 x 轴 splits —— uPlot 建图时
      // 已把默认生成器规范化写进 axes[0].splits, 这里取来包一层, 后续每次轴重算都会走它。
      // 守卫兼容无 axes 的测试桩; 生产图必有可调用的 splits。
      if (u.axes && u.axes[0] && typeof u.axes[0].splits === "function") {
        u.axes[0].splits = _qbDropRightEdgeSplits(u.axes[0].splits);
      }
      u._qbLimits = (d && d.limits) || [];  // 限速事件暂存在图记录上(u.data 只有三列, D4 数据通路)
      // S1 节拍底座初值(图记录面, 同 _qbLimits 款不进 Vue state): 锚 = 建图列尾样本 t(单调
      // 跨拍记账的起点), 双轨以建图数据尾点为显示值(首拍 prev 接续 = 建图尾值, 领先沿不回跳);
      // step/span = 组距标称 meta.interval_s / 名义窗长 meta.span_s(schema=2 = k x si /
      // WINDOW_SPECS 窗长; meta 缺席回落列实距防御 —— 判据跨拍对照值)。
      const stepNom0 = Number(d.meta && d.meta.interval_s);
      u._qbBeat = {
        raf: 0,
        anim: null,
        anchor: anchor0,
        step: stepNom0 > 0 ? stepNom0 : (data.xs.length >= 2 ? data.xs[1] - data.xs[0] : 0),
        span: spanNom0 > 0 ? spanNom0
          : (data.xs.length >= 2 ? data.xs[data.xs.length - 1] - data.xs[0] : 0),
        tracks: {
          up: _qbFxTrackNext(null, data.up[data.up.length - 1], 0),
          dl: _qbFxTrackNext(null, data.dl[data.dl.length - 1], 0),
        },
      };
      // F2 常驻菱形锚(F2, plan 26-11-14-1313): 两枚 DOM 方块挂 .u-wrap(幂等建, 颜色 = 本次
      // 建图捕获的 tk 语义色内联 —— 换肤重建即新令牌), 随后首次位置/门同步; 旋转走 CSS
      // keyframes(注入单点 _qbChartInjectCss), 同步点四处收敛见 _qbFxAnchorSync 注(R3)。
      this._qbFxAnchorEnsure(u, tk);
      this._qbFxAnchorSync(u);
      // D3 停流/断连徽标(F2 同款常驻 DOM 层): 幂等建 + 首次同步(建图拍流状态可能已冻结/断连)
      this._qbStallBadgeEnsure(u);
      this._qbStallBadgeSync(u);
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
          // F2 常驻菱形锚 · 同步点 4/4(ResizeObserver): 宿主尺寸变 -> 判定线 x 与绘图区几何变,
          // u.setSize 后立即重写锚位(setSize 重绘本会经锚钩子带上, 显式落笔钉住计划四处之一
          // —— R3 同步点遗漏即像素漂移)。
          this._qbFxAnchorSync(u);
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
     * 图例/标题规则不注入(本组件 legend 关闭/无标题)。
     * 同单点追加常驻菱形锚(F2, plan 26-11-14-1313)的类样式: 旋转 = keyframes 2639ms linear
     * infinite(模板 rot=t/420 弧度/ms, 一圈 2*pi*420=2639ms; 旧 420ms 系单位误读), 合成器动画
     * 零 rAF/零重绘(D2); reduced-motion 媒体查询隐藏
     * (P2 拍板: 隐藏, 不是静态方块 —— 与 JS 门 cfg.on 的 !reduce 分量双保险);
     * calm 档退化为圆点(.qb-fx-anchor-calm, border-radius 50% —— 模板 isCalm 同款)。
     * 颜色不走这里: 语义色由 _qbFxAnchorEnsure 按 tk 内联(换肤重建即新令牌 —— I10)。 */
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
        "/* aqb: 常驻菱形锚(F2, plan 26-11-14-1313) —— 位置(left/top)由 JS 在四处同步点写入,",
        "   旋转走 keyframes 合成器动画(零 rAF/零重绘 —— D2); left/top 变值才写(逐帧同步点不制造无谓布局)。 */",
        `.qb-fx-anchor { position: absolute; width: 8px; height: 8px; margin: -4px 0 0 -4px; pointer-events: none; will-change: transform; animation: aqb-fx-anchor-spin ${_QB_FX_ANCHOR_SPIN_MS}ms linear infinite; }`,
        ".qb-fx-anchor.qb-fx-anchor-calm { border-radius: 50%; }",
        "@keyframes aqb-fx-anchor-spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }",
        "@media (prefers-reduced-motion: reduce) { .qb-fx-anchor { display: none; } }",
        "/* aqb: 停流/断连徽标(D3, plan 26-11-18-0037) —— 常驻 DOM 层内联小字: 位置(left/top)由 JS 在同步点",
        "   写入(判定线 x = L+W 一带, 绘图区顶沿; transform 右收不越判定线), 文案两态: 滞后 Ns(流活但",
        "   无新帧 >3 x si, 诚实等待)/ 已断连(重连中/降级/对账失败叠加静默); pointer-events:none 与",
        "   z-index 照 tooltip 惯例(views.css .hist-tip) —— 悬停/FX 不受徽标层干扰。 */",
        ".qb-stall-badge { position: absolute; transform: translateX(-100%); padding-right: 6px; pointer-events: none; font: 10px ui-monospace, Consolas, monospace; line-height: 1.5; color: var(--fg-dim); white-space: nowrap; z-index: 2; }",
        ".qb-stall-badge.qb-stall-down { color: var(--warn); }",
      ].join("\n");
      document.head.appendChild(el);
    },
  },
};
