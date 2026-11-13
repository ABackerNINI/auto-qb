"""test_webui_static_dom_panel_traffic 测试计划: webui 前端静态守阵: 详情面板 / 弹窗 / 浮层

## 测试计划(每个测试函数一条)
- test_frontend_qb_traffic_chart_wiring: qB 口径流量图前端接线守阵(P5a+P5b, plan 26-10-03-0946 §07) —— enabled=false 三挂点入口不渲染不请求(全局入口按钮 v-if="qbHistEntryOn" / 抽屉流量页签与组右键菜单项 v-if="qbTrafficOn", 门在 flags.qb_traffic_enabled, /api/webui/flags 下发 fail-closed)+ uPlot 双系列 spanGaps=false 断线不连线 + 桶序->_qbPointsToData 栅格重建与 null 语义 node 真跑(全 null 回落/前导 null 锚推算/interval 非法防御 + S3b 月行真值落点/空槽内插/anchor.xs) + 轮询下界常量 1500(A4, S3b §05.5)+ 三挂点作用域表与低频轮询口径(interval_s 夹取 + document.hidden 跳过 + 关闭/切走 clearInterval)+ 静默续拉(loading 空态只在「尚无落袋结果」时接管正文(qbCurPending = loading + 无数据 + 无错误) + 同宿主 setData 原地快路 + 换肤先销毁再重建 + 错误态由成功落袋清除, 2026-10-04 修轮询期闪烁 / 2026-10-05 补齐空态与错误态闪烁)+ FX-29 软切换落定登记(_qbLoad 落袋 _drawerDone("traffic") 与 _drawerWaitSources 成对, 2026-10-04 修流量页签单击换行遮罩挂死)+ 三主题登记链(tpl/vendor/mixin/manifest)+ escBusy 与 Esc 退栈链同步(含退栈顺序: 历史弹层遮罩 130 先于抽屉 80, 2026-10-06 两图同开报障)+ 建图后宿主 ResizeObserver 自适应与销毁断开(便签 26-10-04-0134)+ 缺口三态文案与空态钉住(P4, plan 26-10-04-0721 §05: 0 桶状态行/缺口合并文案/图例 hint 两处/单种空态收窄为从未传输 + node 三段混排回归)
- test_frontend_qb_traffic_window_persist_and_single_source: 流量图「视图选择」持久化 + 窗口档位单点(2026-10-05) —— QB_WINDOW_NAMES 十三档与后端 traffic_qb.WINDOW_NAMES 逐字一致, 为展示(模板 v-for 走 qbWindowNames)/前后切换(qbCycleWindow)/持久化校验(qbInitialWindow)三处唯一来源(任一处硬编码即与后端 400 校验漂移); 持久化粒度 = 全局单独(autoqb.ui.qbWinGlobal)/组与种子共用(autoqb.ui.qbWinShared), 键按 scope 单点分派, 初值只认合法档位且坏值回落默认, 换窗即落盘并吞写入异常; 初值函数在 qb_traffic_chart.js 且全部皮肤(_UI_ALL)的 tpl-manifest 里排在 state.js 之前(否则 state data() 调它未定义 = 启动白屏); R8 追加 state.js 数值面板接线静态钉(fx: qbInitialFx() / fxPanel 显式建字段, plan 26-11-12-1139 §05.5), 修复轮追加状态行展示值 computed 落位钉(qbFxPeriodS/qbFxBeatMs 恰 1 次定义且夹在 computed: { 与 mounted() { 之间, fx-panel.html 保持裸插值不带括号 —— 落 methods 即复现 toDisplayString 函数源码渲染 blocker)
- test_frontend_qb_fx_store_and_sanitize_battery: 数值面板持久化读路径与逐字段校验 node 电池(R8, plan 26-11-12-1139 §05.5, §09 脏值探针) —— qbInitialFx 桩 localStorage 钉四脏值场景(坏 JSON/v:0/数组根/空串)整体回落默认且键保留(全程零 removeItem) + _qbFxSanitize 逐字段: 错类型(数字字段 null/布尔/数组不得被 Number() 误收、布尔严格 ===true/false 且类型归位、合法 false 保真)/未知枚举与空串回落/clamp 边界(impact/particles [0,1]、shiftRatio [0.2,1] 双侧, 数字串"0.9"抢救)/未知键静默丢弃(旧版残留 scene/amp/tpl 清场)/合法值全字段保真 + layers 残缺(数组根/缺键)逐层补默认。无 node 静默跳过(同 _NODE_QB_TRAFFIC_PROBE 口径)
- test_frontend_qb_fx_overlay_close_registry_and_reduced_motion: 数值面板收层七处登记 + IO 兜底 + reduced-motion 红线静态守阵(R8 S0-b, plan 26-11-12-1139 §05.6/§05.7/§05.9) —— lifecycle 点空白名单与 Esc 退栈链(紧跟 drawerMenu 之后: 后开先关, 面板开着 Esc 只关面板)/dialogs_meta escBusy/closeDrawer/drawerTab/换目标收口六处在位(shortcuts _kbOverlayBusy 末尾项归 test_drawer_dock_keyboard_w2 书写序守阵) + IO 观察 .qb-chart-host 在 _qbFxListen 开面板支路建/关面板支路断(ratio===0 走 fxClose 单点, 不挂 _qbChartDestroy 防换肤误关; 七处直写 visible=false 的断开由 state.js 'fxPanel.visible' watcher 统一汇到 _qbFxListen(false)) + reduce 红线: 判定单点内联 matchMedia 不引用 AQB_FX.reduced(flux-only 三套旧皮肤 ReferenceError)/有效值单点 fxOn = enabled && !reduce/change 监听 mounted 装beforeUnmount 摘/AQB_FX_CFG._qbFxCfgSync 附加 on 且 fx+fxReduce 两 watcher 汇入/面板总开关 :checked=fxOn + :disabled=fxReduce 置灰与说明行/有效值 on 不进持久化形状(QB_FX_DEFAULTS 无 on 键)
- test_frontend_qb_beat_kernel_battery: 节拍内核 S1 电池 + 接缝静态钉(S1, plan 26-11-12-1139 §03 节奏模型/L0/L1, §06 S1 行) —— node 电池真跑(同 _NODE_QB_FX_PROBE 的 new Function 取出口径): 节奏公式四组(multiplier 1/2/8 与 600s 长窗 -> beat 600/夹顶 1000×3, 下限 320 与非法 period 防御) + 每拍时间线(impact 0.12/shift=shiftRatio×beat 防御夹取/converge [0.12,0.6]/tail=min(period-beat,2000) 封顶非常驻, animEnd<=beat<=1000 全域扫 = I1 真值落地可验证面) + easeOut 三次多项式 1000 采样单调无 overshoot(D9) + 0.75px 最小可见位移规则(短窗播 L0/24h 长窗 2880 点瞬时/0.75 边界/量不到宽瞬时) + L1 双轨独立(上传 Δ=0 静默 + 下载 Lv.3 各自正确/Δ 分档端点归属 0.005/0.05/0.30/缺口轨 live=false 不插值/复活轨直落真值不造斜坡/分母可视下限防爆炸/0->0 守卫) + 以显示值接续不回跳(打断中值作下一拍 prev, 上下行收敛序列单调落在 [prev,target] 终点恰真值 —— I3); 接缝静态钉: :426 逐字行后追加 _qbBeatStart(不改写既有字面量)/L0 判定帧摆回旧位与每帧 dx 归零成对/收敛帧 setData 交还 auto/ticks 冻结挂 pending 与清冻结先于 setData/reduce 短路读 AQB_FX_CFG.on 有效值(仅 reduce 分量短路, enabled=false 不短路)/_qbChartDestroy 先 _qbBeatCancel 再 destroy/面板 beat 展示值复用 _qbBeatMs 单点(内联 clamp 公式退场)/模块级头部零 BOM 触碰(rAF/performance.now/document.hidden 只准方法域)/调度器域零 destroy+new uPlot+零 loading(I3 反向钉)/tooltip 读数面接缝(_qbHoverOf 读 d.points[i] 不读 u.data, 与 L1 插值写面零交集 —— I4); y 钉成对(x 提交必配 setScale("y") 全窗真值档位, 纯数值收敛帧先钉 y 再 redraw, 钉值口径 _qbYRange x _qbYCapOf, 收敛帧不得再钉 —— 评审 #1 I4 纵轴定档)/ticks 冻结等长守卫在位(splits 数变化即解除缓存回落现算 —— 评审 #4)/_qbChartRescale 在途拍收口(落真值 + _qbBeatCancel + 清冻结先于 setData —— 评审 #6); S8 收敛帧补逐帧 ySeen 钉 y 恒 31.5(只记确有绘制的帧 —— S8 不播 L0, impact 窗静默帧零提交; 封 setScaleLog.every 在零钉时空转的盲区, 删纯数值帧 y 钉即红) + S9b roll 恰边界 dx0=2x step 仍播 L0(rAF=1 + 视口摆回旧位 [1000,1120], 判据改 < 即红)。无 node 静默跳过(同 _NODE_QB_TRAFFIC_PROBE 口径)

- test_frontend_qb_fx_visual_engine_battery: 视觉引擎 V + N 霓虹元素层 S2-a 电池 + 接缝静态钉(S2-a, plan 26-11-12-1139 §03 V 表/N 节/D1-D4, §06 S2 行) —— node 电池真跑(同节拍内核范式): I6 图层顺序常量逐字(geometry/neon 恒在 curve 前、anchor 在后)+ I11 N 层白名单五元素/黑名单八元素逐字且零交集 + V1 Lv 色表逐字(#7AD9FF/#FEFFA9/#FF6BD6; 四皮肤无 --qb-lv* 令牌已核查, 计划色值常量落 shared 层)+ 三档配色 blur 上限(neon 10/glitch 14/calm 0)+ V2 环边数映射(3/6/8)+ I9 预算常量(粒子 ≤32/每轨半套 ≤16/N 0.33×beat/粒子窗 0.55×beat/y 间距 26px/切片 ≤5/微震 3px/光点 ≤2/末段 6 桶) + D3 lead 仲裁(argmax 优先非缺口非静默轨/双轨静默 null/恰等取 up) + partCap(等级基数 16/24/32 x 密度, clamp 32, 密度 ≤0 零粒子) + D3 三策略分配(both 对半各 ≤16 合计守恒全域扫/lead 全套从属零/merge 中点一次/未知回落 both) + D4 y 间距缩小(线性 /26 下限 0.4 不合并不取消) + N 回落 0.33×beat + 冲击环(easeOut 扩张/alpha 线性回落/0.55×beat 后 null) + V3 粒子三阶段(爆发 ×4.5 闭式/拖尾 easeOut 减速位移步单调收缩/末态恰 dist/t=0 alpha=1 与判定线闪光同帧/carryPx 随 L0 末点滑动) + 喷射清单(三/四/五边非圆点/同种子恒同/左向 270° 弧避开右向扇区/尺寸行程界) + glitch 切片(≤5/|dy0| ≤3/同种子恒同) + 伪随机确定性; 调度器 fx 面(真 mixin 方法 + 桩 uPlot 含 valToPos/bbox 全量): 判定帧 fx 生成门(cfg.on=false fx null 但 L0/L1 照常/reduce 无 anim/缺口轨 lead 单轨/双轨静默零装饰)+ both/lead/merge 三策略落 fx 清单 + D4 y 间距实测缩小 + 装饰帧保障(无 shift 长窗 impact 窗零提交帧强制重绘 + y 钉 31.5 成对)+ 次区相位(收敛帧衔接/光点 ≤4 alpha ≤0.35 位置在绘图区内/1px 量化节流零提交/窗尽收尾 anim null/拍内关 tail 下一帧收尾)+ merge+缺口轨落位退 lead 末点 y(F7: specs.merge[0].y0 === yOf(lead.shown), 与底边的假中点即红 —— 评审修复2; 切片锚带中心同退且清单无条件生成)+ spawn 满额清单与密度解耦(F8: 密度 0.4 仍 16/16, cap=partCap(lv,1) —— 评审修复3); 绘制面 ctx 桩电池(G1-G8, 记账式 2d context 真 _qbDrawFx/_qbDrawFxAnchor): blur 预算(非零赋值恰 1 施加点/带 blur stroke = spots 数 ≤2/逐帧扫帧末 shadowBlur 恒 0/palette=calm 恒不赋非零 —— 评审修复7, 变异自证删 blur 清零行必红)+ neon=false 零白名单元素落笔(fillText/shadowBlur/Lv 色描边, 锚段同验)+ 密度拍内即时(0.4→13/1→32/0.1→3 粒)+ 切片 palette 逐帧门(neon 零切片/拍内切 glitch 下一帧即画 5 条 1px 级 —— 评审修复4)+ draw 侧 merge+缺口轨环心 = yOf(lead.shown)(x=tipX 顶点四点均值观测, 假中点即红)+ lead 加亮跨缺口重新 moveTo 不桥接([20,null,25] vs [20,22,25] 对照 —— 评审修复6); 静态钉: I6/I11/V1/I9 常量行逐字 + 钩子注册序 = 层序(vendor 1.6.32 源实证: 主渲染序 clearRect→drawClear→Pl.forEach[axes→series]→draw, Ci("drawAxes") 在 Dl.axes 末尾 = 网格后系列前 —— drawClear 斜纹恒最底/drawAxes fx(挂 drawClear 会被网格盖住违 I6)/draw 限速→锚)+ 背景零铺色(fx 域剥注释后 fillRect 恰 1 处且为切片 1px 级、锚/次区域零 fillRect)+ I11 黑名单(fx 域零触碰 legend/cursor/series)+ I3 反向钉(fx 四域零 destroy/new uPlot/loading)+ 生效条件门(spawn 与 fx 装饰段逐帧复核 cfg.on、tail 域复核 cfg.tail)+ 收敛帧次区衔接(phase tail/fxTail/cfg.tail 门)+ 装饰帧保障行 + 次区相位分支在 _qbBeatFrame(装饰帧挂调度器循环, 无独立循环)。无 node 静默跳过(同 _NODE_QB_TRAFFIC_PROBE 口径)
- test_frontend_qb_traffic_drawer_page_guard: 流量图抽屉的页面守卫(2026-10-06 修「qB 全局流量图出现在设置页」) —— drawerVisible 两形态先挡非主内容页且状态位不随切页翻(回页连数据/窗口选择一起回来) + 轮询与建图 active 同源含 page 判据(面板不在 DOM 还拉还画 = 对空气取数) + openDrawerTraffic 先切回主内容页 + state.js drawerVisible watcher 退场销毁图/进场补拉(种子详情支路 !s 的 $nextTick _dtSync 回页变体重挂, 归 test_drawer_seed_reentry_variant_remount)
- test_frontend_qb_traffic_yaxis_and_annotation: 流量图纵轴固定模式 + 画布注解层守阵(2026-10-08, issue 26-10-07-0149 认领一并做) —— _qbYRange/_qbGapRuns 纯函数 node 真跑(自动 = peak*1.05 / 固定上限取 max(cap, peak*1.05) 峰值超上限按峰值显示 / 缺口 = 上下行皆 null 才算); 限速三作用域同源 = qB 全局限速上下行**较大者**(_qbGlobalLimit -> speedLimitBytes); 上限派生单点 _qbYCapOf(limit×1.2 / manual MiB); 三作用域**各自独立**持久化(qbYAxisStoreKey 三键 + qbInitialYAxis 只认合法模式与正数 + persistQbYAxis 吞异常) + 切档落盘重排(qbSetYAxisMode/qbSetYAxisManual -> _qbChartRescale 走 setData 重算 scale 不重建) + 限速变化重排 watcher(mounted 注册, this.drawer 守卫剔除 BaseTransition 假实例); 建图 y range 接纯函数 + draw/drawClear 两钩子画限速虚线/缺口斜纹(共享图面三挂点全生效, uPlot.pxRatio 设备像素换算, 限速线只画落在可视值域内的); 模板 .qb-tools/.qb-seg 控件 + CSS 三皮肤成对 + **控件组唯一挂点**(图下统计栏 .qb-statctl; 2026-10-16 版式改: 流量形态头部不再挂控件, 全局/分组与种子流量图三挂点对齐, 上限读数 qbYAxisCapText/.qb-tools-hint 随 UI 移除退役) + P4 重启缝提示(plan 26-10-15-0829; 左端口径修订 2026-10-16, issue 26-10-16-0954): _qbSeamHint 判据纯函数 node 真跑(重启贴近链末->提示(含首采即链末桶的实测帧形态)/链到右沿或链确已接续或旧后端->null, 边界含尾区起点、右沿与左端前一桶三点) + computed qbCurSeamHint 消费单点 + drawer.html 提示行文案单源带重启时刻锚 + 断线语义不变(spanGaps:false ×2)
- test_frontend_qb_traffic_scope_stale_polarity: 流量图三挂点 stale 谓词极性守阵(2026-10-12 修「种子流量图加载不出来」) —— W2–W6 机械改名把 torrent/group 两处 `!(...)` 写成 `!!(...)`(取反变双重取反), 恰在本图活跃时判「响应已过期」⇒ 数据不落袋 + loading 不复位 + 早退不建图 ⇒ 种子「流量」页签恒停「正在加载流量数据…」且轮询被 loading 卡住不自愈(global 未中招, 故症状只在种子/分组图)。既有静态锚(源码字符串级)对单/双 bang 天然失明, 本守阵补两层: 1. node 电池用 `new Function(源码 + "return _QB_SCOPES;")` 取出作用域表, 对三挂点喂「活跃/切走/关闭/换目标/功能关」五类上下文断言 stale 真假 + `active => stale === false` 同向性; 2. 静态极性兜底钉 `!(...)` 书写形态、`!!(...)` 不得回潮
- test_frontend_qb_traffic_load_stall_fallback: 流量图轮询「在途悬挂」兜底守阵(issue 26-10-16-0954-bug-webui-chart-fetch-no-timeout 方案 #2, 2026-10-16) —— loading 是单向「请求在途」标志(_qbLoad 入口无条件置 true, 唯一复位路径是它的 finally), 请求悬挂时 finally 不执行 ⇒ tick 守卫把之后每一拍都挡掉, 图表永久停在旧帧且无提示(与 10-12 修的同链另一入口 stale 谓词取反不同)。三层静态锚: 1. 阈值常量 _QB_LOAD_STALL_MS(=30000, 请求级超时的两倍余量); 2. 判据单点 _qbLoadStalled 在且 tick 必须经它(合体写法 `document.hidden || this[def.loading]` 不得回潮); 3. _qbLoad 置位处写计时起点 _qbLoadAt[scope] 且 finally 不擦(擦会把换目标场景下新请求的起点抹成 0)。行为面 node 电池真跑(无 node 静默跳过): 真 _qbLoad + 永不 settle 的 api 桩 —— 在途未悬挂照旧挡拍 / 悬挂放行且只留一条警告 / 新起点生效故后续照常挡拍 / 图不活跃与页面隐藏照旧跳过 / 判据边界(29s 不判、31s 判、无起点不判); 附 R5#182 死代码反向锚(loadQbHistory 兼容别名零残留, 入口全走 openQbHistory/openDrawerTraffic)
- test_frontend_qb_tick_label_and_isolated_idxs: R5#192 —— x 轴刻度与孤点索引 node 电池(同文件其余纯函数均有电池, 唯这两处标着纯函数却零执行): _qbTickLabel 四族分支 13 档逐档断言(1m/5m 标到秒 / 30m-24h 只标时刻 / 3d/7d/30d 标日期 / 6mo/1y/all 标年月; 期望值由同一 Date 本地时区现算, 与机器时区无关)+ torrent 挂点读自己的窗口字段(三挂点窗口互不串) + _qbIsolatedIdxs 三态(两侧皆 null 的孤点收/任一侧非 null 的链中链端不收/贴边孤点与空系列边界)
- test_frontend_qb_themechange_event_pair: R5#194 —— theme.js↔qb_traffic_chart.js 换肤事件契约成对静态锚(此前 theme.js 全文件零测试, 事件名/派发点被改名或删除时流量图 canvas 换肤残旧色且无测试变红): theme.js 手动切换(set)与系统明暗跟随(onSys, R5#180 补)两路都必须派发 autoqb:themechange 且落在 documentElement 上, qb_traffic_chart.js 必须监听同名事件且挂在同一 target(documentElement) —— 成对断言, 单侧改名/换 target 即红

## 皮肤档位口径
- 皮肤清单单点在 webui_helpers._UI_ALL(atlas/prism/console/flux); flux(第四套, plan 26-10-31-2316 S5)
  fork 自 console, 按 _UI_ALL 枚举的接线守阵随常量自动收编; 单独点名的成对面(qb-tabs 生效面/
  --qb-gap-hatch 令牌/纵轴控件版式/.opt-pill.is-gated/.meta-dialog/ctx-item hover)已显式加 flux 档。
"""

import json

import os

import re

import shutil

import subprocess

from pathlib import Path

from auto_qb.webui.commands import REANNOUNCE_BLOCKED_STATES as _PY_BLOCKED_STATES

from auto_qb.webui.commands import REANNOUNCE_INACTIVE_SKIP as _PY_INACTIVE_SKIP

from webui_helpers import read_shared
from webui_helpers import (
    STATIC_ROOT,
    _UI_ALL,
    _ui_manifest,
    _ui_aggregate,
    _ui_css_aggregate,
    _ui_css_effective,
    _app_bundle_files,
    _app_bundle_text,
)

from webui_dom_panel_support import _tpl_body


def _tpl_top_level_tags(body: str):
    """返回模板体里 **depth-0** 的元素 (tag, attrs) 清单 —— 即该片段的根元素, 忽略注释/文本。

    为什么需要它(而不是数类名出现次数): W3(计划 26-10-11-2106)把档位/纵轴控件组收进**多根**
    片段 <aq-qb-ctl>(tpl/drawer-head.html), 其两根 `.qb-tabs` / `.qb-tools` 是**直接子元素**这件事
    被三皮肤 CSS 依赖 —— `.qb-statctl > .qb-tabs` / `.qb-statctl > .qb-tools` 与
    `.hist-summary > .qb-statctl`(atlas prism views.css / console dialogs.css)全是**直接子选择器**。
    一旦有人给片段包一层 wrapper(哪怕只是"顺手加个容器"),
    这些规则全部**静默**不命中: 类名 count 一个不变, 观感却错版。故这里按**结构**判根数 ——
    单个根 = 有人加了 wrapper, 立刻判红。
    """
    import html.parser as _hp  # 局部导入: 仅本助手需要, 不污染模块级命名空间

    class _Roots(_hp.HTMLParser):
        # HTML 空元素(不改变嵌套深度) —— 片段里出现的只有这些是无闭合标签的
        VOID = frozenset(
            [
                "area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track",
                "wbr"
            ]
        )

        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.depth = 0
            self.roots = []

        def handle_starttag(self, tag, attrs):
            if self.depth == 0:
                self.roots.append((tag, dict(attrs)))
            if tag not in self.VOID:
                self.depth += 1

        def handle_startendtag(self, tag, attrs):
            if self.depth == 0:
                self.roots.append((tag, dict(attrs)))

        def handle_endtag(self, tag):
            if tag not in self.VOID and self.depth > 0:
                self.depth -= 1

    parser = _Roots()
    parser.feed(body)
    return parser.roots


# node 单测探针(P5a): 加载真实 qb_traffic_chart.js, 对模块级纯函数 _qbPointsToData 跑
# 栅格重建 + null 断线语义电池(plan 26-10-03-0946 §5.1/§5.2: 桶键等距 / null 槽 y=null
# / 全 null 回落 / interval 非法防御)。无 node 静默跳过(与 _scan_js_syntax_with_node 同口径)。
_NODE_QB_TRAFFIC_PROBE = r"""
const fs = require("fs");
global.window = {};
eval(fs.readFileSync(process.argv[1], "utf8"));
const P = (t, up, dl) => ({ t, up, dl });
const checks = [];
let pts = [P(1000, 1, 2), P(1030, 3, 4), P(1060, 5, 6)];
let d = _qbPointsToData(pts, 30);
checks.push(["连续段 xs 等距", !!d && JSON.stringify(d.xs) === "[1000,1030,1060]"]);
checks.push(["连续段值透传", !!d && d.up.join() === "1,3,5" && d.dl.join() === "2,4,6"]);
pts = [P(1000, 1, 2), null, P(1060, 5, 6)];
d = _qbPointsToData(pts, 30);
checks.push(["null 桶 x 按栅格重建(缺口位置不漂移)", !!d && JSON.stringify(d.xs) === "[1000,1030,1060]"]);
checks.push(["null 桶 y=null(spanGaps=false 断线)", !!d && d.up[1] === null && d.dl[1] === null]);
checks.push(["锚取首点", !!d && d.anchor.k === 0 && d.anchor.t0 === 1000]);
pts = [null, P(1030, 3, 4), null, P(1090, 7, 8)];
d = _qbPointsToData(pts, 30);
checks.push(["前导 null 整列重建", !!d && JSON.stringify(d.xs) === "[1000,1030,1060,1090]"]);
checks.push(["前导/中断 null y=null", !!d && d.up[0] === null && d.up[2] === null && d.up[3] === 7]);
checks.push(["锚取首个非 null", !!d && d.anchor.k === 1 && d.anchor.t0 === 1030]);
checks.push(["全 null 回落(后端已归一 [])", _qbPointsToData([null, null], 30) === null]);
checks.push(["interval 非法回落", _qbPointsToData([P(1, 1, 1)], 0) === null]);
// P4 回归(plan 26-10-04-0721 §07): 停机/断连 = null 缺口(spanGaps:false 如实断线);
// 空闲 = (0,0) 真实观测点(0 平线, 不是缺口) —— 三段混排(活跃/缺口/空闲/活跃)一次钉住
pts = [P(1000, 5, 6), null, null, P(1090, 0, 0), P(1120, 0, 0), null, P(1180, 2, 3)];
d = _qbPointsToData(pts, 30);
checks.push(["三段混排 xs 等距(缺口位置不漂移)",
  !!d && JSON.stringify(d.xs) === "[1000,1030,1060,1090,1120,1150,1180]"]);
checks.push(["停机/断连 null 桶 y=null(如实断线)",
  !!d && d.up[1] === null && d.up[2] === null && d.up[5] === null && d.dl[5] === null]);
checks.push(["空闲段 (0,0) 是观测点不成缺口",
  !!d && d.up[3] === 0 && d.up[4] === 0 && d.dl[3] === 0 && d.dl[4] === 0]);
checks.push(["三段混排活跃值透传", !!d && d.up[0] === 5 && d.up[6] === 2 && d.dl[6] === 3]);
// S3b 月视图(plan 26-10-04-1957 §05.3): month 行按行间隔 28-31 天非等距 —— 非 null 点
// 按真值 t 落点(覆写), null 槽在两真值点间线性内插/窗端外推; anchor.xs 供 tooltip 真值
const jan = 1735689600, feb = 1738368000, mar = 1740787200;  // 2025-01/02/03-01(31d/28d)
pts = [P(jan, 1, 2), P(feb, 3, 4), P(mar, 5, 6)];
d = _qbPointsToData(pts, 2592000);
checks.push(["月行真值 x 落点(按行间隔非等距)", !!d && JSON.stringify(d.xs) === JSON.stringify([jan, feb, mar])]);
checks.push(["anchor.xs 悬停真值", !!d && d.anchor.xs[2] === mar && d.anchor.k === 0 && d.anchor.t0 === jan]);
pts = [P(jan, 1, 2), null, P(mar, 5, 6)];
d = _qbPointsToData(pts, 2592000);
checks.push(["月视图空槽真值内插", !!d && d.xs[1] === (jan + mar) / 2 && d.up[1] === null]);
checks.push(["月视图值透传", !!d && d.up[0] === 1 && d.dl[2] === 6]);
console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
"""


def test_frontend_qb_traffic_chart_wiring():
    """qB 口径流量图前端接线守阵(P5a+P5b, plan 26-10-03-0946 §07)

    五类"漏一处 = 静默失效 / P5 验收被破坏"的故障形态机械钉住:
    1. enabled=false 三挂点入口不渲染不请求(P5 验收): 全局入口按钮 v-if="qbHistEntryOn" 挂今日
       流量面板内; 抽屉「流量」页签按钮 v-if="qbTrafficOn"; 组右键「qB 口径流量图」菜单项
       (W3 计划 26-10-20-0024 起改注册表单点) gate: "qb_traffic" -> flags.qb_traffic_enabled;
       门单点在 flags.qb_traffic_enabled(/api/webui/flags 下发, fail-closed 默认 false,
       state.js 显式建字段 + lifecycle.loadWebFlags 写入), _qbLoad 里再兜一道 —— 无旗标无入口,
       无入口无触发路径 = 三挂点零请求;
    2. uPlot 双系列断线语义(§5.2): 两 series 显式 spanGaps=false(纯断线, 无最大跨越);
      桶序 -> uPlot 数据的栅格重建 _qbPointsToData 用 node 真跑(null 槽 y=null + x 等距
      不漂移 / 前导 null 锚推算 / 全 null 与 interval 非法回落), 无 node 静默跳过;
      容器尺寸自适应(便签 26-10-04-0134 + 2026-10-04 高度跟随): 建图后宿主挂 ResizeObserver,
      宽/高任一变化 u.setSize 重画(高度取宿主 clientHeight, 随抽屉拖拽调高), _qbChartDestroy
      断开 + 回调自摘/0 尺寸守卫;
    3. 三主题登记链(§07): tpl 分片 + uPlot vendor + 组件 mixin 在三份 index.html 的
      tpl-manifest 同步登记(逐份断言, 三清单一致性另由 test_frontend_template_split_wiring
      钉住), app.mixin 注入 + 抽屉/Esc 退栈/escBusy 名单同步 + _logout 清理;
    4. 挂点形态(2026-10-04 三挂点并入底部详情抽屉): 今日流量面板入口(TM 历史入口旁并列按钮),
      图层/取值 CSS 三套 UI 成对(.qb-* 结构类 + .sb-qb 入口类 + .drawer-body.is-traffic 撑满段;
      tooltip 与图例复用 .hist-* 同源色义);
    5. 三挂点并入抽屉与低频轮询(§07 表): 全局/分组 = drawer.kind === "traffic"(scope 记挂点),
      单种 = drawer.kind === "seed" + drawer.tab === "traffic"(drawer.js _loadDrawerTab 进,
      关抽屉/切页签/换形态由 _stopDrawerPoll + _qbTeardown 统一收); 三挂点建图落点统一
      ref="qbChartHost"、共用同一段正文块(qbTrafficActive -> qbCur*); 组右键菜单项直用
      menu.key 的 encode_group_key 通道(不自行编码); 轮询三挂点统一: 间隔从 meta.interval_s
      夹取([15s,600s] 配置校验界, 30d 窗桶宽 3600s 被夹到上界保续拉语义) + document.hidden 跳过
      (对齐 _startDrawerPoll 先例)+ _qbPollStop 显式 clearInterval(只挂打开期间, 不后台常驻)。
      静默续拉(2026-10-04 修「每隔几秒闪一次」; 2026-10-05 补齐空态/错误态): loading 空态只在
      「本作用域尚无任何落袋结果」时接管正文(qbCurPending = loading + 无数据 + 无错误), 落袋走
      setData 原地快路(不 destroy+new 清屏), 换肤先销毁再整图重建; 错误态改由下一次成功落袋清除
      (发请求前清 = 续拉把错误文案换成 loading/空态再换回 = 每个轮询周期闪一次)。FX-29 软切换落定登记
      (2026-10-04 修「流量页签单击换行『正在加载…』挂死」): _qbLoad 落袋登记
      _drawerDone("traffic"), 与 _drawerWaitSources 成对, 缺一边遮罩等永不到手的源。
      drawer-dock 落点已自种子视图上提为 app 级分片(dock.html), 入口任意页可达(触发即切回主内容
      页), 面板本体由 drawerVisible 限主内容页 —— 见 test_frontend_qb_traffic_drawer_page_guard。
    6. 缺口文案与空态(plan 26-10-04-0721 §05, P4; 2026-10-30 按区段改): 悬停 0 桶状态行(空闲段
      z 派生 (0,0) 真实观测点, 与 null 缺口可辨)/ 悬停缺口按「区段 × 作用域」出文案 —— 数据链
      之外(首次采样之前 / 最后一次之后)只陈述「该时段无此种子(该分组/无)数据」, 链中间的洞才
      说「采样中断 · 该时段无数据」; 判据单点 _qbChainBounds/_qbGapZone 只认本帧 points, **不**
      用种子 added_on 推算(跳检 = 删同 hash 再重加且流量按 infohash 留存, 拿 added_on 切一刀会
      把早期真实数据误判成「尚未添加」); 文案收进 computed qbCurGapText 单点(模板只引用不重算)
      且旧的「一律归因」合并文案必须退场; 单种空态改为「从未产生传输采样」。三皮肤共用 shared
      分片与 mixin(tpl-manifest 登记链见上面第 3 点), 文案单点钉住即可。2026-10-08 版式改(用户
      动议)推翻「图例 hint 两处」旧口径:
      窗口档位/纵轴控件上提流量形态头部标题栏, 图例(上行/下行)并入统计栏, 两处 hint 与独立
      图例行全退场 —— 这里改为钉上提/并入/退场三条新结构口径。"""
    shared = os.path.join(STATIC_ROOT, "shared")
    js = open(os.path.join(shared, "qb_traffic_chart.js"), encoding="utf-8").read()
    state_js = open(os.path.join(shared, "state.js"), encoding="utf-8").read()
    lifecycle_js = open(os.path.join(shared, "lifecycle.js"), encoding="utf-8").read()
    auth_js = open(os.path.join(shared, "auth.js"), encoding="utf-8").read()
    dialogs_js = read_shared("dialogs.js")
    app_js = open(os.path.join(shared, "app.js"), encoding="utf-8").read()
    drawer_js = read_shared("drawer.js")
    store_js = open(os.path.join(shared, "drawer_store.js"), encoding="utf-8").read()  # W1: 数据/行为层
    statusbar = open(os.path.join(shared, "tpl", "statusbar.html"), encoding="utf-8").read()
    drawer_tpl = open(os.path.join(shared, "tpl", "drawer.html"), encoding="utf-8").read()
    # W3(计划 26-10-11-2106): 头部外壳与流量档位/纵轴控件组自 drawer.html 收进组件模板
    head_tpl = open(os.path.join(shared, "tpl", "drawer-head.html"), encoding="utf-8").read()
    dock_tpl = open(os.path.join(shared, "tpl", "dock.html"), encoding="utf-8").read()
    ctx_menus = open(os.path.join(shared, "tpl", "ctx-menus.html"), encoding="utf-8").read()

    # 1. enabled 门(fail-closed 单点; 三挂点共用 qbTrafficOn, 全局入口另挂今日流量面板本体)
    # ctx_menu(计划 26-10-20-0024 W2/W3): 行右键菜单布局下发键, 与两个旗标同一通道同一显式建字段口径
    assert 'flags: { skip_check_menu: false, qb_traffic_enabled: false, relocate_enabled: false, ctx_menu: null }' in state_js, \
        "state.js flags 默认缺 qb_traffic_enabled/relocate_enabled: false(fail-closed 初值必须显式建)或 ctx_menu: null"
    assert "qb_traffic_enabled: !!(f && f.qb_traffic_enabled)" in lifecycle_js, \
        "loadWebFlags 必须写回 qb_traffic_enabled(缺了旗标恒 false = 功能永不可见)"
    assert "ctx_menu: (f && f.ctx_menu) || null" in lifecycle_js, \
        "loadWebFlags 必须透传 ctx_menu(漏写 = 布局数据到不了前端, 用户重排静默失效)"
    assert "qb_traffic_enabled: false" in lifecycle_js, "loadWebFlags 失败分支必须保持 fail-closed"
    # boot 韧性(issue 26-11-11-0633): flagsLoaded 态显式建 + 键盘入口"未取到先补拉再判"
    assert "flagsLoaded: false" in state_js, \
        "state.js 缺 flagsLoaded 显式建字段(非响应式盲区, 且'未取到'与'未启用'的判据单点)"
    mo = re.search(r"async openQbHistory\(\) \{\n(.*?)\n    \},", js, re.S)
    assert mo and "ensureWebFlags" in mo.group(1) and "flagsLoaded" in mo.group(1), \
        "openQbHistory 缺'flags 未取到先补拉一次再判'(boot 期偶发失败会把'没取到'误报成'没启用')"
    assert "await this.ensureWebFlags()" in mo.group(1), \
        "openQbHistory 补拉必须 await 落地再落门控(fire-and-forget 会在补拉未落地时就误报'没启用')"
    # boot 韧性(issue 26-11-11-0633): 两条 boot 入口(lifecycle 本机免鉴权 / auth bootstrap)必须走
    # loadWebFlagsBoot(带有限重试), 回退成裸 loadWebFlags = boot 韧性丢失
    assert "this.loadWebFlagsBoot()" in lifecycle_js and "this.loadWebFlagsBoot()" in auth_js, \
        "boot 入口必须调 loadWebFlagsBoot(lifecycle 本机免鉴权路径 + auth bootstrap 成功路径)"
    mo = re.search(r"qbTrafficOn\(\) \{\n(.*?)\n    \},", js, re.S)
    assert mo and "this.flags.qb_traffic_enabled" in mo.group(1), \
        "qb_traffic_chart.js 缺 qbTrafficOn 功能总门单点(抽屉流量页签/组右键菜单项的 v-if 门)"
    mo = re.search(r"qbHistEntryOn\(\) \{\n(.*?)\n    \},", js, re.S)
    assert mo, "qb_traffic_chart.js 缺 qbHistEntryOn 入口门单点"
    body = mo.group(1)
    assert "this.flags.qb_traffic_enabled" in body and "this.todayTraffic" in body, \
        "入口门必须同时消费 flags.qb_traffic_enabled 与今日流量面板(挂点本体)"
    # 入口按钮: v-if 门 + 面板内并列(TM 历史入口同组)
    assert 'v-if="qbHistEntryOn"' in statusbar and 'class="sb-qb"' in statusbar, \
        "statusbar 缺 qB 入口按钮(v-if 门是 P5 验收的静态锚)"
    today_blk = re.search(r'<template v-if="todayTraffic">(.*?)</template>', statusbar, re.S)
    assert today_blk and 'class="sb-qb"' in today_blk.group(1), \
        "qB 入口必须挂在今日流量面板组内(挂点 = 今日流量面板, plan §07 表)"

    # 2. uPlot 断线语义 + 悬停取值对齐
    assert js.count("spanGaps: false") == 2, "上行/下行两 series 都必须显式 spanGaps=false(§5.2)"
    assert "setCursor" in js and "qbHistHoverIdx" in js, "缺 uPlot setCursor -> 悬停取值通道"
    assert "_qbPointsToData" in js and "function _qbPointsToData" in js, \
        "缺栅格重建纯函数(模块级单例, 供 node 单测)"
    # 容器 resize 自适应(便签 26-10-04-0134): 建图宽度一次取定后画布不重算 —— 宿主必须挂
    # ResizeObserver, 宽度变了 uPlot setSize 重画; _qbChartDestroy 必须断开(不留对旧宿主的观察);
    # 回调要有自摘/0 宽守卫(挂点 DOM 随 v-if 拆除后 RO 报 0 宽, setSize(0) 会把图画没)
    assert "new ResizeObserver(" in js, "qb_traffic_chart.js 缺宿主 ResizeObserver(resize 后画布不重算)"
    assert "u.setSize(" in js, "qb_traffic_chart.js resize 回调缺 uPlot setSize 重画"
    destroy_blk = re.search(r"_qbChartDestroy\(scope\) \{\n(.*?)\n    \},", js, re.S)
    assert destroy_blk and "disconnect()" in destroy_blk.group(1), \
        "_qbChartDestroy 必须断开 ResizeObserver(图已销毁还观察旧宿主)"
    assert "host.isConnected" in js and "w > 0" in js, \
        "ResizeObserver 回调缺自摘/0 宽守卫(挂点拆除后 RO 报 0 宽, 不得对旧宿主 setSize)"
    # 有 node 时真跑 null 断线语义电池(无 node 静默跳过, 不引入 skip)
    node = shutil.which("node")
    if node:
        proc = subprocess.run(
            [node, "-e", _NODE_QB_TRAFFIC_PROBE,
             os.path.join(shared, "qb_traffic_chart.js")],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        assert proc.returncode == 0, f"_qbPointsToData node 电池跑挂: {proc.stderr.strip()}"
        report = json.loads(proc.stdout.strip().splitlines()[-1])
        assert report["failed"] == [], f"null 断线语义电池 {report['ok']}/{report['total']} 过, 失败: {report['failed']}"

    # 3. 三主题登记链 + 接线(2026-10-04: 抽屉落点上提 app 级 -> dock.html 分片)
    for ui in _UI_ALL:
        mf = _ui_manifest(ui)
        assert "/shared/tpl/dock.html" in [p["src"] for p in mf["parts"]], f"{ui} 清单缺 dock.html 分片"
        assert "/shared/tpl/drawer.html" in [p["src"] for p in mf["parts"]], f"{ui} 清单缺 drawer.html 分片"
        assert "/shared/vendor/uPlot.iife.min.js" in mf["scripts"], f"{ui} 清单缺 uPlot vendor"
        assert "/shared/qb_traffic_chart.js" in mf["scripts"], f"{ui} 清单缺组件 mixin"
        assert os.path.isfile(os.path.join(STATIC_ROOT, "shared", "vendor", "uPlot.iife.min.js")), \
            "uPlot.iife.min.js 不在盘上(404 = 整页停在错误占位)"
    assert 'class="drawer-dock"' in dock_tpl, "dock.html 缺 .drawer-dock 落点(boot 会 fail-fast)"
    assert "app.mixin(window.AQB_QB_TRAFFIC)" in app_js, "app.js 未注入 AQB_QB_TRAFFIC(整块功能静默消失)"
    # 三挂点并入抽屉后, Esc/escBusy 单点写 drawerVisible(dialogs.js + lifecycle.js 两处同步):
    # 面板 DOM 已退场(不在主内容页)时不吃 Esc —— 那条 Esc 要留给当前页面(设置页退回首页)
    assert "this.drawerVisible ||" in dialogs_js, \
        "escBusy 名单缺抽屉项(drawerVisible; 抽屉承载流量图, 与 Esc 退栈链两处同步纪律)"
    assert "else if (this.drawerVisible) this.closeDrawer();" in lifecycle_js, \
        "Esc 退栈链缺抽屉分支(种子详情与流量图共用 closeDrawer; 判据必须是 drawerVisible)"
    # 两图同开时的退栈顺序: 历史流量弹层(.modal-mask, z-index 130)盖在停靠抽屉(80)之上,
    # 视觉最上层必须**先**被 Esc 关掉, 否则那次 Esc 会穿过遮罩去关底下被盖住的抽屉
    # (2026-10-06 报障: qB 口径流量图与历史流量图同开时 Esc 先关了抽屉 —— 顺序即视觉层叠)
    hist_at = lifecycle_js.find("else if (this.historyOpen) this.historyOpen = false;")
    drawer_at = lifecycle_js.find("else if (this.drawerVisible) this.closeDrawer();")
    assert 0 <= hist_at < drawer_at, \
        "Esc 退栈链顺序错误: 历史弹层(遮罩 130)必须先于抽屉(80)关闭, 否则两图同开时 Esc 穿过遮罩关错层"
    assert "this.drawer.open = false" in auth_js and "this._qbTeardown()" in auth_js, \
        "_logout 必须收起抽屉并 _qbTeardown(不留对 /api/traffic/qb/* 的后台请求)"
    assert "this.qbHistData = null" in auth_js and "this.qbGroupData = null" in auth_js \
        and "this.qbTorrentData = null" in auth_js, \
        "_logout 必须清三挂点数据(受保护内容同 historyOpen 先例)"

    # 4. CSS 三套 UI 成对(.qb-* 结构类 + .sb-qb 入口; tooltip/图例复用 .hist-* 不在此列)
    # 判据落在**最终生效面**(皮肤聚合 + shared 共用层, link 序): .qb-tabs 组件本体自
    # issue 26-10-20-2231 起收敛进 shared/console_hub.css(三皮肤逐条同, 单点一份),
    # 只读皮肤聚合会恒红; 用共用层兜住「三皮肤都吃到」这件事, 而 .qb-note/.qb-chart
    # 等仍由各皮肤自带(未收敛) —— 两处断言的语义因此都还是「三皮肤成对」。
    for css, name in (
        (_ui_css_effective("atlas"), "atlas 生效样式面(聚合 + shared)"),
        (_ui_css_effective("console"), "console 生效样式面(聚合 + shared)"),
        (_ui_css_effective("prism"), "prism 生效样式面(聚合 + shared)"),
        (_ui_css_effective("flux"), "flux 生效样式面(聚合 + shared)"),
    ):
        for rule, what in (
            (".qb-tabs button.active", "窗口切换激活态"),
            (".qb-note", "加载/空态"),
            (".qb-chart {", "图表容器(悬停 tooltip 定位锚)"),
            (".sb-qb {", "今日流量面板入口按钮"),
            (".drawer-body.is-traffic { display: flex;", "抽屉流量形态正文 flex 纵列"),
            (".drawer-body.is-traffic .qb-chart-host { height: 100%; }", "图高撑满抽屉可用高"),
        ):
            assert rule in css, f"{name} 缺 {rule}({what}) —— 三套 UI 必须成对改"

    # 5. 三挂点并入抽屉 + 低频轮询(plan §07 表 1/2/3 + 「轮询/取数」列)
    # 作用域表 = 三挂点单一描述源: 三作用域齐全, 各持 state 字段名/容器 ref/端点 url;
    # 2026-10-04 并入抽屉后三挂点建图落点统一 qbChartHost(同一时刻只渲染一个流量形态)
    assert js.count('host: "qbChartHost"') == 3, \
        "_QB_SCOPES 三挂点必须统一建图落点 ref=qbChartHost(抽屉内共用一段正文块)"
    assert 'url: (h, w) => "/api/traffic/qb/torrent/" + h + "?window=" + w' in js, \
        "单种作用域端点串漂移(/api/traffic/qb/torrent/{hash})"
    assert 'url: (k, w) => "/api/traffic/qb/group/" + k + "?window=" + w' in js, \
        "分组作用域端点串漂移(/api/traffic/qb/group/{key}; key 原样内插 = encode_group_key 通道, 不自行编码)"
    # 单种挂点(§07 表 2): 种子详情头部「流量」页签 v-if 门 + drawer.js 接线三处
    assert 'v-if="qbTrafficOn"' in drawer_tpl and 'drawerTab(\'traffic\')' in drawer_tpl, \
        "drawer.html 缺「流量」页签按钮(v-if=qbTrafficOn 门 + drawerTab 入口)"
    assert 'tab === "traffic" && this.qbTrafficOn' in store_js and 'this._qbPollStart("torrent")' in store_js, \
        "drawer_store.js _loadDrawerTab 缺流量页签分支(加载 + 起轮询; W1 起取数在数据层)"
    assert 'this._qbPollStop("torrent")' in store_js, \
        "drawer_store.js _stopDrawerPoll 缺流量轮询收口(关抽屉/切页签/换目标全走这里 = 关闭即停; W1 起在数据层)"
    assert 'last === "traffic" && !this.qbTrafficOn' in drawer_js, \
        "drawer.js 打开抽屉缺流量页签初值归一(功能关闭时上次停留页签须落回常规页)"
    # 全局/分组挂点: 组右键菜单项(v-if 门) + 抽屉流量形态(共用正文块/建图落点/关闭/窗口切换)
    # W3(计划 26-10-20-0024)起组右键菜单项改注册表单点(ctx_menu.js group 支): 门控与分派
    # 从模板文本搬到注册表定义(gate: "qb_traffic" / act: vm.openQbGroup(vm.menu.key))
    reg = open(os.path.join(shared, "ctx_menu.js"), encoding="utf-8").read()
    assert 'gate: "qb_traffic"' in reg and "vm.openQbGroup(vm.menu.key)" in reg, \
        "ctx_menu.js 缺组右键「qB 口径流量图」菜单项(注册表 gate: qb_traffic + menu.key 直用的 encode_group_key 通道)"
    assert reg.count("vm.openQbGroup(vm.menu.key)") == 1, "组右键菜单项只能挂在单组菜单(多选/剧集菜单不得出现)"
    assert 'ctxItems(ctxMenuKind())' in ctx_menus, \
        "ctx-menus.html 行菜单必须 v-for 消费注册表(支名走 menu.js::ctxMenuKind() 单点; 回退静态直写 = 四支人肉奇偶复发)"
    assert 'v-if="qbTrafficActive"' in drawer_tpl and 'ref="qbChartHost"' in drawer_tpl \
        and 'qbCurSummary' in drawer_tpl, \
        "drawer.html 缺流量形态正文块(三挂点共用: qbTrafficActive 门 / 建图落点 / 汇总)"
    # W3(计划 26-10-11-2106): 头部外壳与「档位 + 纵轴」控件组自 drawer.html 收进组件模板 ——
    # 口径一字不变(三挂点控件齐全 / 标题取 qbTrafficTitle), 断言面换到组件模板与调用点。
    # !建图落点 ref="qbChartHost" 仍**必须**留在 drawer.html(壳模板): _qbChartBuild 取宿主走
    #   this.$refs[def.host], 而该 this 恒是根实例(Vue 的 $refs 只在声明它的实例上登记) ——
    #   搬进组件 = 图永远不画且无报错, 见 tpl/drawer.html 流量正文段的长注与计划 §05 W3「落地」。
    # 26-10-20-2231: 两组分段钮改 <aq-seg> 数据驱动, 按钮本体不再逐个写死在模板里 ——
    # 判据从「模板里有这几个回调」升级为「模板把两组的 items/value/pick 都接到 $root 单点」。
    assert ':on-pick="$root.qbSetWindow"' in head_tpl and ':on-pick="$root.qbSetYAxisMode"' in head_tpl, \
        "tpl/drawer-head.html 的 <aq-qb-ctl> 缺档位/纵轴控件(三挂点控件必须齐全)"
    assert '<aq-qb-ctl></aq-qb-ctl>' in drawer_tpl, \
        "drawer.html 缺 <aq-qb-ctl> 挂点(流量形态头部中部与种子流量页签统计栏各一个)"
    assert 'drawerIsTraffic' in drawer_tpl and 'qbTrafficTitle' in drawer_tpl, \
        "drawer.html 缺流量形态头部调用点(形态判据 drawerIsTraffic + 标题取 qbTrafficTitle)"
    assert 'this.openDrawerTraffic("global", "")' in js and 'this.openDrawerTraffic("group", key)' in js, \
        "openQbHistory/openQbGroup 必须归一到 openDrawerTraffic(打开流量形态抽屉)"
    assert 'this._qbLoad(scope);' in js and 'this._qbPollStart(scope);' in js, \
        "openDrawerTraffic 缺打开拉取 + 起轮询(§07 表 3「打开弹层拉取」)"
    assert 'if (!this.qbTrafficOn || !key) return;' in js, "openQbGroup 缺 fail-closed 兜底门(入口 v-if 之外的加载路径)"
    # 低频轮询(§07): 间隔取 meta.interval_s 夹取([1.5s,600s] 配置校验界, A4 下界对齐
    # v3 采样间隔放宽后的真实下界) + 30s 兜底 + document.hidden 跳过(对齐 drawer.js
    # _startDrawerPoll 先例) + 关闭路径显式 clearInterval
    assert "_QB_POLL_FALLBACK_MS = 30000" in js and "_QB_POLL_MIN_MS = 1500" in js and "_QB_POLL_MAX_MS = 600000" in js, \
        "轮询间隔常量漂移(30s 兜底 / [1.5s,600s] 夹取界 = §06 配置校验边界, A4: 15000 -> 1500)"
    assert "Math.min(_QB_POLL_MAX_MS, Math.max(_QB_POLL_MIN_MS, s * 1000))" in js, \
        "轮询间隔必须经 [1.5s,600s] 夹取(agg 段窗 meta.interval_s=3600 是桶宽, 直拉 = 一小时不刷新)"
    # 三判据(不活跃 / 页面隐藏 / 在途未落袋)语义不变, 书写形态 2026-10-22 再变一次: 轮询生命周期
    # 收敛进 polling.js 骨架(startPoll)—— 页面隐藏由骨架的**恒等守卫**兜(不再每处手写 document.hidden),
    # 在途互斥 + 悬挂兜底改为声明 `stall` / `mutex` 两个键。故这里按语义钉: 声明齐全 + 文件内零裸
    # 定时器(启停一律经骨架); 细分行为(未悬挂挡拍 / 悬挂放行 / 抽屉侧同口径)由
    # test_frontend_qb_traffic_load_stall_fallback 与 test_frontend_poll_skeleton_single_point 逐拍钉住。
    assert "this.startPoll(`qb:${scope}`, {" in js, \
        "流量轮询必须走骨架 startPoll 单点(文件内不得再手写 setInterval/clearInterval 启停)"
    assert "guard: () => _QB_SCOPES[scope].active(this)," in js, \
        "流量轮询缺「图还活跃」守卫声明(页面隐藏由骨架恒等守卫兜, 但活跃判据要自己声明)"
    assert "stall: () => this[_QB_SCOPES[scope].loading]," in js and "mutex: true," in js, \
        "流量轮询缺在途互斥 / 悬挂兜底声明(判据退回裸早退 = loading 卡死即永久挡拍, issue 26-10-16-0954)"
    assert "setInterval(" not in js and "clearInterval(" not in js, \
        "qb_traffic_chart.js 不得再裸写定时器(启停收口到骨架, 手柄在 _polls 表)"
    # 关闭路径统一收口(2026-10-04): closeDrawer 收抽屉即 _qbTeardown(停三挂点轮询 + 销毁三挂点图)
    assert "this._qbTeardown();" in drawer_js, \
        "drawer.js 缺 _qbTeardown 调用(关抽屉/换形态时轮询与图不停, P5 验收)"
    teardown_blk = re.search(r"_qbTeardown\(\) \{\n(.*?)\n    \},", js, re.S)
    assert teardown_blk and "this._qbPollStop(s)" in teardown_blk.group(1) \
        and "this._qbChartDestroy(s)" in teardown_blk.group(1), \
        "_qbTeardown 必须停三挂点轮询并销毁三挂点图(单点收口)"
    # 静默续拉(2026-10-04 修「每隔几秒闪一次」; 2026-10-05 补齐空态/错误态): 续拉对用户不可见 ——
    # loading 空态只在「本作用域尚无任何落袋结果」时接管正文(判据 qbCurPending 三合一 = loading +
    # 无数据 + 无错误), 数据落袋走 setData 原地快路(destroy+new uPlot 清屏一帧), 换肤因 canvas 色
    # 烘焙必须先销毁再整图重建(setData 不换色)。2026-10-04 那版只门了「有图」一态
    # (!qbCurPoints.length): 空数据集的空态文案与错误文案仍被每个轮询周期的 loading 顶掉一帧
    # (真机报「流量图闪烁 暂无…」), 判据因此改为按「有无落袋结果」而不是按「有无点」。
    assert 'v-if="qbCurPending"' in drawer_tpl, \
        "drawer.html loading 空态必须门在 qbCurPending 上(按有无落袋结果而不是有无点: 空态/错误态被接管 = 每个轮询周期闪一次)"
    pending_blk = re.search(r"qbCurPending\(\) \{\n(.*?)\n    \},", js, re.S)
    assert pending_blk and "this.qbCurLoading && !this.qbCurData && !this.qbCurError" in pending_blk.group(1), \
        "qbCurPending 必须三合一(loading + 无数据 + 无错误): 少任一项都有一种既有状态(图/空态/错误)被续拉顶掉"
    load_blk = re.search(r"async _qbLoad\(scope\) \{\n(.*?)\n    \},", js, re.S)
    assert load_blk, "qb_traffic_chart.js 缺 _qbLoad(取数单点)"
    # R5#182: loadQbHistory「P5a 兼容别名」零调用死代码已删(全快照 grep 仅定义一处, 入口全走
    # openQbHistory/openDrawerTraffic) —— 反向钉防复活: 复活即与 _qbLoad 双写取数入口
    assert "loadQbHistory" not in js, \
        "qb_traffic_chart.js 残留 loadQbHistory 兼容别名(R5#182 已删的死代码, 复活即双写取数入口)"
    load_body = load_blk.group(1)
    assert load_body.index("await this.api(") < load_body.index('this[def.error] = "";') \
        and load_body.index("this[def.data] = data;") < load_body.index('this[def.error] = "";'), \
        "错误态只允许在**成功落袋**分支清(发请求前清 = 续拉把错误文案换成 loading/空态再换回 = 每个轮询周期闪一次)"
    assert "prev.setData([data.xs, data.up, data.dl]);" in js and "prev.root.parentElement === host" in js, \
        "qb_traffic_chart.js 缺 setData 原地快路(每次轮询 destroy+new uPlot 清屏 = 每隔一个轮询周期闪一次)"
    theme_blk = re.search(r"_qbOnThemeChange = \(\) => \{\n(.*?)\n        \};", js, re.S)
    assert theme_blk and theme_blk.group(1).find("this._qbChartDestroy(s)") < theme_blk.group(1).find("this._qbChartBuild(s)"), \
        "换肤处理器必须先 _qbChartDestroy 再 _qbChartBuild(canvas 色建图时烘焙, setData 快路不换色)"
    # FX-29 软切换落定登记(2026-10-04 修「流量页签单击换行『正在加载…』挂死」): 换目标软切换的
    # 待到集合含 "traffic"(_drawerWaitSources 通用分支), 但 _drawerDone 只有 detail/trackers/
    # files/peers 四个 fetcher 在调 —— _qbLoad 落袋不登记则集合永不清空, drawer.switching 遮罩
    # 挂死盖住图(双击走 openTorrentDrawer 整体重置不经待到集合, 只有单击跟随软切换踩中)
    assert 'if (scope === "torrent") this._drawerDone("traffic", ctx, 0);' in js, \
        "qb_traffic_chart.js _qbLoad 落袋必须登记 FX-29 落定(_drawerDone('traffic')), 否则软切换遮罩等一个永不到手的源挂死"
    wait_blk = re.search(r"_drawerWaitSources\(tab\) \{\n(.*?)\n    \},", store_js, re.S)
    assert wait_blk and 'return ["detail", tab]' in wait_blk.group(1), \
        "drawer_store.js _drawerWaitSources 通用分支必须覆盖 traffic 页签(与 _qbLoad 的落定登记成对, 拆开即挂死; W1 起在数据层)"
    # state.js 根选项显式建字段(Vue 响应式前置, frontend-split 纪律)
    for field in (
        "qbTorrentWindow", "qbTorrentData", "qbTorrentLoading", "qbTorrentError", "qbTorrentHoverIdx",
        "qbTorrentHoverLeft", "qbGroupKey", "qbGroupName", "qbGroupWindow", "qbGroupData", "qbGroupLoading",
        "qbGroupError", "qbGroupHoverIdx", "qbGroupHoverLeft"
    ):
        assert re.search(rf"^\s+{field}: ", state_js, re.M), f"state.js 缺 {field} 初值(根选项显式建字段)"
    assert 'kind: "seed", scope: ""' in state_js, \
        "state.js drawer 缺 kind/scope 初值(抽屉双形态, vue-reactivity 前置)"

    # 6. 缺口三态文案与空态(plan 26-10-04-0721 §05, P4): 三皮肤共用 shared/tpl/drawer.html 与
    # shared/qb_traffic_chart.js(登记链已在上面第 3 点逐皮肤钉住), 文案单点改动三皮肤同时
    # 生效 —— 这里钉文案本体 + 触发判据 + 旧文案退场, 不逐皮肤重复
    assert 'v-if="qbCurHover.up + qbCurHover.dl === 0">0 B/s · 空闲/做种</span>' in drawer_tpl, \
        "悬停 0 桶缺状态行(空闲段 z 派生 (0,0) 真实观测点, 必须与 null 缺口可辨; 速率行照旧)"
    # 2026-10-30 按区段改: 文案离开模板收进 computed 单点 qbCurGapText(按「区段 × 作用域」
    # 输出)。plan 26-10-04-0721 §05 当年「两态区分依赖可选 API 形状增强, 拍板不做」随之作废
    # —— 新判据不需要任何 API 增强, 只用本帧 points 的数据链边界。
    for gap_txt in ("该时段无此种子数据", "该时段无该分组数据", "该时段无数据", "采样中断 · 该时段无数据"):
        assert gap_txt in js, f"缺口悬停文案缺: {gap_txt}(应在 qbCurGapText 单点内)"
    assert "<span>{{ qbCurGapText }}</span>" in drawer_tpl, \
        "悬停缺口文案必须引用 qbCurGapText 单点(webui.md 单点口径: 模板不得内联重算)"
    assert "无采样 · 程序未运行或 qB 断连" not in drawer_tpl and "无采样 · 程序未运行或 qB 断连" not in js, \
        "旧合并文案必须退场(对所有 null 一视同仁归因为「qB 断联」; 评注里也不得留原文, 免得 grep 误命中)"
    assert "断线 · 无数据" not in drawer_tpl, "旧缺口文案「断线 · 无数据」必须退场"
    # 2026-10-08 版式改(用户动议): 两处 hint 全移除 —— 图下那行独立图例(含口径注释)并入统计栏,
    # 口径说明不再以常驻文案出现(信息在悬停 tooltip 里给)。原「两处 hint 同步」的守阵随之退役,
    # 改为钉「文案已退场」+「图例已入统计栏」+「档位/纵轴控件已上提头部」三条新口径。
    assert "缺口 = 无采样" not in drawer_tpl and "悬停查看详情" not in drawer_tpl, \
        "图例 hint 两处(工具条 + 图例)已按用户要求全部移除(2026-10-08 版式改), 不得复现"
    assert "断线处不连线" not in drawer_tpl, "旧图例 hint「断线处不连线」必须退场"
    # 版式改结构钉住: 1. 图例(上行/下行)在统计栏 .hist-summary 内, 不再是独立的 .hist-legend 行;
    # 2. 档位/纵轴控件在图下统计栏 .qb-statctl 内(2026-10-16 版式改: 流量形态头部不再挂控件,
    # 全局/分组与种子流量图对齐 —— 头部调用点必须**不再**接 <aq-qb-ctl>)
    # W3(计划 26-10-11-2106): 头部外壳收进 <aq-drawer-head>; 2026-10-16 起控件组唯一挂点 =
    # 统计栏, 头部调用点退回空插槽(仅标题 + 关闭钮)。
    traffic_call = re.search(r'<aq-drawer-head v-if="drawerIsTraffic"[^>]*>(.*?)</aq-drawer-head>', drawer_tpl, re.S)
    assert traffic_call and '<aq-qb-ctl>' not in traffic_call.group(1), \
        "流量形态头部不得再挂档位/纵轴控件组(2026-10-16 版式改: 与种子流量图对齐, 控件统一落图下统计栏)"
    assert 'class="qb-tabs"' in head_tpl and 'class="qb-tools"' in head_tpl, \
        "<aq-qb-ctl> 缺 .qb-tabs/.qb-tools(控件组的唯一实现)"
    # 2026-10-09 第 2 轮(用户动议): 种子流量图(kind === "seed" + tab === "traffic")的档位/纵轴
    # 控件组**从种子头部挪走** —— 头部已承载五页签导航 + 模板切换器, 13 档再并进去太挤、窄视口下
    # 会变形; 改落**图下统计栏** .hist-summary, 排在「下载累计」之后(用户: 「即『下载累计』后」)。
    seed_call = re.search(r'<aq-drawer-head v-else[^>]*>(.*?)</aq-drawer-head>', drawer_tpl, re.S)
    assert seed_call and 'qb-statctl' not in seed_call.group(1) \
        and 'qb-headctl' not in seed_call.group(1) and 'aq-qb-ctl' not in seed_call.group(1), \
        "种子头部不得再挂流量档位/纵轴控件组(2026-10-09 第 2 轮: 已改落图下统计栏, 头部保持单行 44px)"
    stat_blk = drawer_tpl[drawer_tpl.index('class="hist-summary"'):drawer_tpl.index('种子详情形态正文(五页签)')]
    assert 'class="qb-statctl"' in stat_blk and '<aq-qb-ctl></aq-qb-ctl>' in stat_blk, \
        "档位/纵轴控件组必须落在图下统计栏 .hist-summary 内(2026-10-09 第 2 轮; 2026-10-16 起为唯一挂点; W3 起经 <aq-qb-ctl>)"
    # 2026-10-16 版式改: 控件组不再按 scope 分叉 —— 三挂点(全局/分组/单种)统一落统计栏且恒渲染
    # (本段整体已在 qbTrafficActive 正文内), 「torrent 专属门」不得回潮。
    assert '<div v-if="qbCurScope === \'torrent\'" class="qb-statctl">' not in drawer_tpl \
        and '<div class="qb-statctl">' in stat_blk, \
        "统计栏控件组必须恒渲染(2026-10-16 三挂点统一), 不得再门在 qbCurScope === 'torrent'"
    # 落点次序(用户口径「即『下载累计』后」): 图例 → 窗口 N 桶 → 上传累计 → 下载累计 → 控件组
    _order = [stat_blk.index(k) for k in ("hs-leg", "窗口", "上传累计", "下载累计", "qb-statctl")]
    assert _order == sorted(_order), \
        "统计栏次序必须为 图例 → 窗口 N 桶 → 上传累计 → 下载累计 → 档位/纵轴控件组"
    assert 'hs-leg' in stat_blk and '上传' in stat_blk and '下载' in stat_blk, \
        "统计栏(.hist-summary)必须含上传/下载图例(.hs-leg), 且排在「窗口 N 桶」之前"
    # 口径注解(2026-10-09 第 3 轮, 用户动议): 常驻文案退场, 改为两个累计读数的悬浮提示。
    # title 走全局断供管道(ui_feedback.js 落 DOM 即迁 data-aq-tip), 文案单点仍是 qbCurSummaryHint。
    assert stat_blk.count(':title="qbCurSummaryHint"') == 2, \
        "「上传累计 / 下载累计」两处都要挂口径注解的悬浮提示(文案单一来源 qbCurSummaryHint)"
    assert 'class="hist-hint"' not in drawer_tpl, \
        "统计栏常驻口径文案(.hist-hint)必须退场(已改为两个累计读数的 tooltip; 弹层 popovers.html 里那处是另一用途)"

    # W3(计划 26-10-11-2106): 「两处控件组逐字同源」升级为「只有一处实现」—— 旧写法是两份复写
    # + 本处的字符串比对守阵(坑档 drawer-multi-form-hosts 的处置条: 无 partial 机制只能复写,
    # 复写必须逐字同源并加守阵); 本仓库现在有 partial 了(Vue 组件), 故改钉单点: 控件组标记在
    # 面板模板层只出现一次(在 tpl/drawer-head.html 的 <aq-qb-ctl> 里), drawer.html 只剩一个挂点
    # (图下统计栏; 2026-10-16 起头部挂点退役)——
    # 谁把控件抄回 drawer.html(复写回潮)即红, 覆盖强度不降反升(单点强于同源)。
    assert drawer_tpl.count('class="qb-tabs"') == 0 and drawer_tpl.count('class="qb-tools"') == 0, \
        "drawer.html 仍手写档位/纵轴控件组(复写回潮: 控件组只有 <aq-qb-ctl> 一份实现)"
    assert head_tpl.count('class="qb-tabs"') == 1 and head_tpl.count('class="qb-tools"') == 1, \
        "<aq-qb-ctl> 模板必须恰一份 .qb-tabs 与 .qb-tools(控件组的唯一实现)"
    assert drawer_tpl.count("<aq-qb-ctl></aq-qb-ctl>") == 1, \
        "控件组唯一挂点(图下统计栏)必须接 <aq-qb-ctl>(2026-10-16 起头部挂点退役, 恰此一处)"
    assert 'class="hist-legend"' not in drawer_tpl, \
        "独立的图例行(.hist-legend)必须退场: 上行/下行图例已并入统计栏 .hist-summary"
    assert '暂无该种子的 qB 口径流量数据(从未产生传输采样)' in js, \
        "单种空态文案未收窄为「从未产生传输采样」(plan §03.3 拍板: 空闲不再产生空态; " \
        "2026-10-30 起与缺口悬停同口径 —— 只陈述采样条件, 不替用户归因)"
    assert "暂无该分组的 qB 口径流量数据(成员产生传输采样期间才有数据)" in js, \
        "分组空态文案未改中性口径(旧句归因于「成员活跃传输期间」)"
    assert "暂无 qB 口径流量数据(该时段无任何采样)" in js, \
        "全局空态文案未改中性口径(旧句归因于「程序运行期间」, 程序在跑而该作用域无数据时是错的)"
    assert "累计为窗口内增量(无数据期不计)" in js, \
        "累计注解未改中性口径(「断线期」是归因, 「无数据期」是事实)"
    assert "仅活跃传输期间有采样" not in js, \
        "旧单种空态文案必须退场(空闲段现在是 0 平线, 空态语义只剩从未传输)"


def test_frontend_qb_traffic_window_persist_and_single_source():
    """流量图「视图选择」持久化 + 窗口档位单点(2026-10-05, 拍板粒度: 全局单独 / 组与种子共用)

    背景: 窗口档位(13 档)此前只活在 state.js 根 data 里, 刷新即回默认 24h —— 视图选择是
    用户意图, 该像 drawerTab / view / page 一样落 localStorage。三条**静默**失效形态钉住:
    1. 档位清单单点: QB_WINDOW_NAMES 十三档(与后端 traffic_qb.WINDOW_NAMES 逐字一致)是
       展示(模板 v-for 走 qbWindowNames computed)/ 前后切换(qbCycleWindow)/ 持久化校验
       (qbInitialWindow)三处唯一来源 —— 任一处再硬编码就会与后端校验漂移(非法档 400);
    2. 持久化粒度: 全局一份(autoqb.ui.qbWinGlobal), 分组与种子共用一份(autoqb.ui.qbWinShared);
       键按 scope 单点分派(qbWinStoreKey); 初值 qbInitialWindow 只认合法档位(坏值/无存储回落
       默认); 换窗即落盘(_qbSetWindow -> persistQbWindow)且写失败吞异常(与 persistDrawerTab
       同纪律);
    3. 装载序: 初值函数定义在 qb_traffic_chart.js, 该文件在全部皮肤(_UI_ALL)的 tpl-manifest 里
       均排在 state.js 之前(逐份断言)—— 否则 state.js 的 data() 调它时未定义, 整页启动即白屏。"""
    from auto_qb.webui.server.traffic_qb import WINDOW_NAMES  # noqa: PLC0415

    shared = os.path.join(STATIC_ROOT, "shared")
    js = open(os.path.join(shared, "qb_traffic_chart.js"), encoding="utf-8").read()
    state_js = open(os.path.join(shared, "state.js"), encoding="utf-8").read()
    drawer_tpl = open(os.path.join(shared, "tpl", "drawer.html"), encoding="utf-8").read()
    # W3(计划 26-10-11-2106): 档位/纵轴控件组的唯一实现(<aq-qb-ctl>)与头部外壳住在这里
    head_tpl = open(os.path.join(shared, "tpl", "drawer-head.html"), encoding="utf-8").read()
    # R8(修复轮): 数值面板分片(状态行展示值的裸插值消费面, 见下方 computed 落位守阵)
    fx_tpl = open(os.path.join(shared, "tpl", "fx-panel.html"), encoding="utf-8").read()

    # 1. 档位清单单点 + 与后端逐字一致 + 展示面走 computed(模板不再硬编码)
    m = re.search(r"const QB_WINDOW_NAMES = \[(.*?)\];", js, re.S)
    assert m, "qb_traffic_chart.js 缺 QB_WINDOW_NAMES 单点(档位清单)"
    names = re.findall(r'"([^"]+)"', m.group(1))
    assert tuple(names) == tuple(WINDOW_NAMES), \
        f"前端档位清单与后端 traffic_qb.WINDOW_NAMES 漂移: 前端 {names} / 后端 {list(WINDOW_NAMES)}"
    assert 'QB_WINDOW_DEFAULT = "24h"' in js, "缺 QB_WINDOW_DEFAULT(初值 / 非法档回落值)"
    assert re.search(r"qbWindowNames\(\) \{\n\s*return QB_WINDOW_NAMES;", js), \
        "qbWindowNames computed 必须直返 QB_WINDOW_NAMES(模板 v-for 的唯一来源)"
    # W3(计划 26-10-11-2106): 档位按钮自 drawer.html 收进 <aq-qb-ctl> 组件模板(两挂点共用一份
    # 实现), 故登记面换成组件模板 —— 口径不变(展示面走 computed, 不硬编码档位清单)。
    # 26-10-20-2231: 模板侧再降一层 —— 按钮本体也交给 <aq-seg>, 模板只交 items/value/pick;
    # 展示面仍只吃 computed(qbWindowTabs 投影自 QB_WINDOW_NAMES + qbWindowLabel), 零硬编码。
    assert ':items="$root.qbWindowTabs"' in head_tpl and ':value="$root.qbCurWindow"' in head_tpl, \
        "tpl/drawer-head.html 的 <aq-qb-ctl> 窗口按钮必须吃 qbWindowTabs + qbCurWindow(经 $root 回调根实例)"
    assert re.search(r"qbWindowTabs\(\) \{\n\s*return QB_WINDOW_NAMES\.map\(", js), \
        "qbWindowTabs 必须投影自 QB_WINDOW_NAMES(档位展示面仍只有一份清单)"
    assert 'v-for="w in qbWindowNames"' not in drawer_tpl and "v-for=\"w in ['1m'" not in drawer_tpl, \
        "drawer.html 仍手写档位按钮/硬编码档位清单(复写回潮: 控件组只有 <aq-qb-ctl> 一份实现)"
    # 前后切换: 按单点序定位(非法档回落默认) + 端点夹取不环绕 + 走 qbSetWindow 单点
    cyc = re.search(r"qbCycleWindow\(delta\) \{\n(.*?)\n    \},", js, re.S)
    assert cyc, "qb_traffic_chart.js 缺 qbCycleWindow(窗口前后切换落点)"
    cb = cyc.group(1)
    assert "QB_WINDOW_NAMES.indexOf(cur)" in cb and "QB_WINDOW_NAMES.indexOf(QB_WINDOW_DEFAULT)" in cb, \
        "切换必须按 QB_WINDOW_NAMES 定位当前档(非法档回落默认)"
    assert "Math.min(QB_WINDOW_NAMES.length - 1, i + delta)" in cb and "Math.max(0," in cb, \
        "切换必须端点夹取(从「全部」环绕回「1分」是惊扰)"
    assert "this.qbSetWindow(next)" in cb, "切换必须走 qbSetWindow 单点(重拉 + 轮询重排 + 落盘一体)"
    assert "if (!s) return;" in cb, "无流量形态(qbCurScope 空)必须零副作用"

    # 2. 持久化粒度 + 键单点 + 初值校验 + 换窗落盘
    assert 'QB_WIN_STORE_KEY_GLOBAL = "autoqb.ui.qbWinGlobal"' in js, "缺全局窗口存储键"
    assert 'QB_WIN_STORE_KEY_SHARED = "autoqb.ui.qbWinShared"' in js, "缺共用窗口存储键(组/种子)"
    key_fn = re.search(r"function qbWinStoreKey\(scope\) \{\n(.*?)\n\}", js, re.S)
    assert key_fn and 'scope === "global" ? QB_WIN_STORE_KEY_GLOBAL : QB_WIN_STORE_KEY_SHARED' in key_fn.group(1), \
        "qbWinStoreKey 必须按 scope 分派(全局单独 / 其余共用一份)"
    init_fn = re.search(r"function qbInitialWindow\(scope\) \{\n(.*?)\n\}", js, re.S)
    assert init_fn, "缺 qbInitialWindow(窗口初值读取)"
    ib = init_fn.group(1)
    assert "localStorage.getItem(qbWinStoreKey(scope))" in ib and "QB_WINDOW_NAMES.includes(v)" in ib, \
        "初值必须读存储且只认合法档位(坏值回落默认)"
    assert "return QB_WINDOW_DEFAULT;" in ib and "catch" in ib, "初值读取失败必须吞异常回落默认"
    setw = re.search(r"async _qbSetWindow\(scope, w\) \{\n(.*?)\n    \},", js, re.S)
    assert setw and "this.persistQbWindow(scope, w);" in setw.group(1), \
        "换窗必须落盘(_qbSetWindow -> persistQbWindow)"
    persist = re.search(r"persistQbWindow\(scope, w\) \{\n(.*?)\n    \},", js, re.S)
    assert persist and "localStorage.setItem(qbWinStoreKey(scope), w)" in persist.group(1) \
        and "catch" in persist.group(1), "persistQbWindow 必须写键单点且吞写入异常(与 persistDrawerTab 同纪律)"
    # state.js 三字段按 scope 取初值(全局单独 / 组与种子共用同一键)
    assert 'qbHistWindow: qbInitialWindow("global")' in state_js, "state.js 全局窗口初值未接持久化"
    assert 'qbTorrentWindow: qbInitialWindow("torrent")' in state_js, "state.js 种子窗口初值未接持久化"
    assert 'qbGroupWindow: qbInitialWindow("group")' in state_js, "state.js 分组窗口初值未接持久化"
    # 数值面板持久化(R8, plan 26-11-12-1139 §05.5): state.js 显式建 fxPanel/fx 字段(根选项显式建
    # 字段纪律, undefined 是非响应式盲区)并接 qbInitialFx 初值 —— 默认值/逐字段校验/键单点在
    # qb_traffic_chart.js 属主三件套(同 qbInitialWindow 范式), 行为面由 test_frontend_qb_fx_store_and_sanitize_battery 真跑
    assert "fx: qbInitialFx()" in state_js, "state.js fx 初值未接 qbInitialFx(持久化 autoqb.ui.qbFx 未接线)"
    assert "fxPanel: { visible: false, x: 0, y: 0, alt: false }" in state_js, \
        "state.js 缺 fxPanel 显式建字段(右键浮层视图态, 非响应式盲区)"
    # R8 修复轮: 状态行展示值必须住 computed 块 —— fx-panel.html 裸插值 {{ qbFxPeriodS }} 不加
    # 括号, 落 methods 域会被 toDisplayString 渲染成函数源码字符串(首轮 blocker 的回潮形态,
    # 静态面零引用即无测试变红, 故钉落位)。判据 = 定义名恰出现 1 次且夹在 computed: { 与
    # mounted() { 之间(mixin 结构里 methods 在 mounted 之后, 落 methods 即越过 mounted 界)。
    comp_start = js.index("computed: {")
    mounted_at = js.index("mounted() {")
    for name in ("qbFxPeriodS", "qbFxBeatMs"):
        n_def = js.count(name + "()")
        assert n_def == 1, f"qb_traffic_chart.js 里 {name}() 应恰出现 1 次(现 {n_def} 次, 多半是模板/注释带出了带括号引用)"
        assert comp_start < js.index(name + "()") < mounted_at, \
            f"{name} 不在 computed 块(computed: {{ 与 mounted() {{ 之间) —— 回潮到 methods 即复现" \
            "「状态行渲染函数源码」blocker"
    assert "{{ qbFxPeriodS }}" in fx_tpl and "{{ qbFxBeatMs }}" in fx_tpl, \
        "fx-panel.html 状态行必须裸插值展示值 computed(不加括号)"
    assert "qbFxPeriodS(" not in fx_tpl.replace("{{ qbFxPeriodS }}", "") \
        and "qbFxBeatMs(" not in fx_tpl.replace("{{ qbFxBeatMs }}", ""), \
        "fx-panel.html 不得带括号调用展示值(qbFxPeriodS/qbFxBeatMs 是 computed 不是方法)"

    # 3. 装载序: qb_traffic_chart.js 必须排在 state.js 之前(初值函数在 state data() 时可用)
    for ui in _UI_ALL:
        scripts = _ui_manifest(ui)["scripts"]
        assert scripts.index("/shared/qb_traffic_chart.js") < scripts.index("/shared/state.js"), \
            f"{ui}: qb_traffic_chart.js 必须排在 state.js 之前(qbInitialWindow 定义处, 否则启动白屏)"


# 数值面板持久化 node 电池(R8, plan 26-11-12-1139 §05.5): qbInitialFx 读路径 + _qbFxSanitize
# 逐字段校验真跑(桩 localStorage; §09 四脏值场景: 错类型/未知枚举/v:0/空串)。无 node 静默跳过
# (与 _NODE_QB_TRAFFIC_PROBE 同口径, 不引入 skip)。
_NODE_QB_FX_PROBE = r"""
const fs = require("fs");
global.window = {};
const store = {};
const removed = [];
global.localStorage = {
  getItem: (k) => (k in store ? store[k] : null),
  setItem: (k, v) => { store[k] = String(v); },
  removeItem: (k) => { removed.push(k); delete store[k]; },
};
// 模块级 const 不随 sloppy eval 外泄(同 test_frontend_qb_traffic_scope_stale_polarity 的
// new Function 取出口径), 函数声明 qbInitialFx 可直接取
const { qbInitialFx, QB_FX_DEFAULTS, QB_FX_STORE_KEY } = new Function(
  fs.readFileSync(process.argv[1], "utf8") + "\nreturn { qbInitialFx, QB_FX_DEFAULTS, QB_FX_STORE_KEY };"
)();
const checks = [];
const D = QB_FX_DEFAULTS;
const KEY = QB_FX_STORE_KEY;
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);
// —— 读路径(qbInitialFx, §05.5): 坏 JSON / v:0 / 非对象根 / 空串 -> 整体回落默认 且 键保留 ——
checks.push(["无存储回落默认", eq(qbInitialFx(), D)]);
store[KEY] = "{oops";
checks.push(["坏 JSON 整体回落默认", eq(qbInitialFx(), D)]);
checks.push(["坏 JSON 键保留(不清键, 供诊断)", KEY in store && removed.length === 0]);
store[KEY] = JSON.stringify({ v: 0, impact: 1 });
let fx = qbInitialFx();
checks.push(["v:0 整体回落默认(不按缺省合并个别字段)", fx.impact === D.impact && fx.v === 1]);
checks.push(["v:0 键保留", KEY in store && removed.length === 0]);
store[KEY] = "[1,2]";
checks.push(["数组根整体回落", eq(qbInitialFx(), D)]);
store[KEY] = "";
checks.push(["空串整体回落", eq(qbInitialFx(), D)]);
checks.push(["读路径零 removeItem(永不删键)", removed.length === 0]);
// —— 逐字段校验(_qbFxSanitize): 场景 A 错类型 ——
// 数字字段给 null/布尔/数组: Number(null)===0 / Number(true)===1 的误收必须被拦下(缺省即默认)
store[KEY] = JSON.stringify({ v: 1, impact: null, particles: true, shiftRatio: [0.5],
  neon: "no", tail: 0, enabled: false, layers: { band: 1, scan: false } });
fx = qbInitialFx();
checks.push(["数值 null 回落默认(不得误收成 0)", fx.impact === D.impact]);
checks.push(["数值布尔回落默认", fx.particles === D.particles]);
checks.push(["数值数组回落默认", fx.shiftRatio === D.shiftRatio]);
checks.push(["布尔字符串/数字严格回落(类型也归位)", typeof fx.neon === "boolean" && fx.neon === D.neon
  && typeof fx.tail === "boolean" && fx.tail === D.tail]);
checks.push(["显式合法 false 保真(用户意图不被洗回)", fx.enabled === false && fx.layers.scan === false]);
// 场景 B 未知枚举与空串: 白名单外/空串一律逐字段回落
store[KEY] = JSON.stringify({ v: 1, ease: "bogus", palette: 42, shift: "", dual: "solo",
  tear: "chaos", echoSpan: "999" });
fx = qbInitialFx();
checks.push(["未知枚举/空串逐字段回落默认", fx.ease === "out" && fx.palette === "neon"
  && fx.shift === "smooth" && fx.dual === "both" && fx.tear === "linked" && fx.echoSpan === "auto"]);
// 场景 C clamp 边界: impact/particles 钳 [0,1], shiftRatio 钳 [0.2,1]; 边界值与数字串的取值面
store[KEY] = JSON.stringify({ v: 1, impact: 5, particles: -3, shiftRatio: 0.05 });
fx = qbInitialFx();
checks.push(["越界钳位(impact->1, particles->0, shiftRatio->0.2)", fx.impact === 1 && fx.particles === 0 && fx.shiftRatio === 0.2]);
store[KEY] = JSON.stringify({ v: 1, shiftRatio: 9 });
fx = qbInitialFx();
checks.push(["shiftRatio 越上界钳 1", fx.shiftRatio === 1]);
store[KEY] = JSON.stringify({ v: 1, impact: 0, particles: 1, shiftRatio: 0.2 });
fx = qbInitialFx();
checks.push(["clamp 边界值保真(0/1/0.2 合法)", fx.impact === 0 && fx.particles === 1 && fx.shiftRatio === 0.2]);
store[KEY] = JSON.stringify({ v: 1, impact: "0.9" });
checks.push(["数字串抢救(Number 可解析)", qbInitialFx().impact === 0.9]);
// 场景 D 未知键丢弃: 旧版本键残留的已删字段(如 scene/amp/tpl)读时清场
store[KEY] = JSON.stringify({ v: 1, scene: "x", amp: 2, tpl: 3 });
fx = qbInitialFx();
checks.push(["未知键静默丢弃(现建新对象)", !("scene" in fx) && !("amp" in fx) && !("tpl" in fx) && eq(fx, D)]);
// 合法值全字段保真(防校验器把合法手改值洗回默认)
store[KEY] = JSON.stringify({ v: 1, enabled: false, impact: 0.35, ease: "linear", palette: "glitch",
  particles: 0.5, neon: false, tail: false, shift: "instant", shiftRatio: 1, dual: "lead",
  tear: "random", echoSpan: "200", layers: { band: false, particles: false, scan: true, grade: false } });
fx = qbInitialFx();
checks.push(["合法值全字段保真", fx.enabled === false && fx.impact === 0.35 && fx.ease === "linear"
  && fx.palette === "glitch" && fx.particles === 0.5 && fx.neon === false && fx.tail === false
  && fx.shift === "instant" && fx.shiftRatio === 1 && fx.dual === "lead" && fx.tear === "random"
  && fx.echoSpan === "200" && fx.layers.band === false && fx.layers.particles === false
  && fx.layers.scan === true && fx.layers.grade === false]);
// layers 残缺(数组/缺键) -> 逐层回落默认(缺省即默认合并, §05.5 aside)
store[KEY] = JSON.stringify({ v: 1, layers: [] });
fx = qbInitialFx();
checks.push(["layers 数组根逐层回落默认", eq(fx.layers, D.layers)]);
store[KEY] = JSON.stringify({ v: 1, layers: { band: false } });
fx = qbInitialFx();
checks.push(["layers 缺键逐层补默认(其余三层)", fx.layers.band === false && fx.layers.particles === D.layers.particles
  && fx.layers.scan === D.layers.scan && fx.layers.grade === D.layers.grade]);
console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
"""


def test_frontend_qb_fx_store_and_sanitize_battery():
    """数值面板持久化读路径 + 逐字段校验 node 电池(R8, plan 26-11-12-1139 §05.5)

    动效参数是单键 JSON 观感偏好, 手改/旧版本残留/隐私模式都会喂进脏值 —— §05.5 读纪律
    与 §09 面板探针(脏值回落)钉成行为面(无 node 静默跳过, 同 _NODE_QB_TRAFFIC_PROBE 口径):
    1. 读路径(qbInitialFx): 坏 JSON / v:0 / 数组根 / 空串 -> **整体**回落默认 且 **键保留**
      (不清键, 原始串留诊断; 全程零 removeItem —— 重置语义是写回默认不删键, 读路径更不许删);
    2. 逐字段校验(_qbFxSanitize): §09 四脏值场景 —— 错类型(数字字段喂 null/布尔/数组不得被
      Number() 误收成 0/1, 布尔字段喂字符串/数字类型也归位; 显式合法 false 保真)/未知枚举与
      空串逐字段回落/clamp 边界(impact/particles [0,1] 与 shiftRatio [0.2,1] 双侧越界, 边界值
      保真, 数字串 "0.9" 抢救)/未知键静默丢弃(旧版残留 scene/amp/tpl 现建新对象自然清场);
    3. 合法值全字段保真 + layers 残缺(数组根/缺键)逐层补默认(缺省即默认合并)。
    state.js 接线面(fx: qbInitialFx() / fxPanel 显式建字段)由
    test_frontend_qb_traffic_window_persist_and_single_source 静态钉住。"""
    node = shutil.which("node")
    if not node:
        return
    proc = subprocess.run(
        [node, "-e", _NODE_QB_FX_PROBE,
         os.path.join(STATIC_ROOT, "shared", "qb_traffic_chart.js")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    assert proc.returncode == 0, f"qbFx 持久化 node 电池跑挂: {proc.stderr.strip()}"
    report = json.loads(proc.stdout.strip().splitlines()[-1])
    assert report["failed"] == [], \
        f"qbFx 持久化电池 {report['ok']}/{report['total']} 过, 失败: {report['failed']}"


# 节拍内核 node 电池(S1, plan 26-11-12-1139 §03 节奏模型/L0/L1): 公式/时间线/easeOut/状态机/
# 0.75px 规则真跑。new Function 取出口径(模块级 const 不随 sloppy eval 外泄, 同 _NODE_QB_FX_PROBE);
# 无 node 静默跳过(同 _NODE_QB_TRAFFIC_PROBE 口径)。
_NODE_QB_BEAT_PROBE = r"""
const fs = require("fs");
global.window = {};
const src = fs.readFileSync(process.argv[1], "utf8");
const {
  _qbBeatMs, _qbBeatTimeline, _qbFxEaseOut, _qbFxCellPx, _qbFxShouldShift,
  _qbFxLevel, _qbFxTrackNext, _qbFxShown,
} = new Function(src + "\nreturn { _qbBeatMs, _qbBeatTimeline, _qbFxEaseOut, _qbFxCellPx,"
  + " _qbFxShouldShift, _qbFxLevel, _qbFxTrackNext, _qbFxShown };")();
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);
const close = (a, b, eps) => Math.abs(a - b) <= (eps === undefined ? 1e-9 : eps);
// —— A. 节奏公式四组(I1/I2, §03 自适应示例表: multiplier 1/2/8 与 600s 长窗) ——
ok("multiplier=1 (period 1.5s) -> beat 600ms", _qbBeatMs(1500) === 600);
ok("multiplier=2 (period 3s) -> beat 夹顶 1000ms", _qbBeatMs(3000) === 1000);
ok("multiplier=8 (period 12s) -> beat 夹顶 1000ms", _qbBeatMs(12000) === 1000);
ok("600s 长窗 -> beat 夹顶 1000ms", _qbBeatMs(600000) === 1000);
ok("beat 下限 320(period 800ms)", _qbBeatMs(800) === 320);
ok("period 非法(NaN/0/负)回落下限 320", _qbBeatMs(NaN) === 320 && _qbBeatMs(0) === 320 && _qbBeatMs(-5) === 320);
// —— B. 每拍时间线(§03 公式代码块: impact 0.12 / shift=shiftRatio×beat / converge [0.12,0.6]
//       / tail = min(period-beat, 2000) 封顶非常驻) ——
let tl = _qbBeatTimeline(1500, 0.6);
ok("1.5s 拍: beat 600 / impact 72 / shift 360", tl.beat === 600 && close(tl.impactMs, 72) && close(tl.shiftMs, 360));
ok("1.5s 拍: 收敛窗 288ms(0.12-0.6 beat), animEnd=360", close(tl.convergeMs, 288) && close(tl.animEndMs, 360));
ok("1.5s 拍: 次区 tail 900ms", tl.tailMs === 900);
tl = _qbBeatTimeline(3000, 0.6);
ok("3s 拍: beat 夹顶 1000 / impact 120 / shift 600", tl.beat === 1000 && close(tl.impactMs, 120) && close(tl.shiftMs, 600));
tl = _qbBeatTimeline(12000, 0.6);
ok("12s 拍: tail 封顶 2000(绝不常驻)", tl.tailMs === 2000 && tl.beat === 1000);
tl = _qbBeatTimeline(600000, 0.6);
ok("600s 长窗: tail 2000 / beat 1000 / period 夹取保持", tl.tailMs === 2000 && tl.beat === 1000 && tl.period === 600000);
ok("timeline period 下限夹取(800 -> 1500)", _qbBeatTimeline(800, 0.6).period === 1500);
ok("animEnd <= beat <= 1000(I1 真值落地保证; period x shiftRatio 全域扫)", (() => {
  for (const period of [1500, 3000, 12000, 600000]) {
    for (const sr of [0.2, 0.6, 1]) {
      const t = _qbBeatTimeline(period, sr);
      if (!(t.animEndMs <= t.beat + 1e-9 && t.beat <= 1000)) return false;
    }
  }
  return true;
})());
ok("shiftRatio 防御夹取(0 与越下界钳 0.2/越上界钳 1/缺省 undefined 回落 0.6)", _qbBeatTimeline(3000, 0).shiftMs === 200
  && _qbBeatTimeline(3000, 0.05).shiftMs === 200 && _qbBeatTimeline(3000, 5).shiftMs === 1000
  && _qbBeatTimeline(3000, undefined).shiftMs === 600);
// —— C. easeOut(D9: 三次多项式, 严格单调无 overshoot, 值域 [0,1]) ——
ok("端点 f(0)=0 f(1)=1; 越界夹取 f(-1)=0 f(2)=1", _qbFxEaseOut(0) === 0 && _qbFxEaseOut(1) === 1
  && _qbFxEaseOut(-1) === 0 && _qbFxEaseOut(2) === 1);
ok("f(0.5)=0.875(三次多项式特征值)", close(_qbFxEaseOut(0.5), 0.875));
ok("1000 采样单调不减且恒在 [0,1]", (() => {
  let prev = -1;
  for (let i = 0; i <= 1000; i++) {
    const v = _qbFxEaseOut(i / 1000);
    if (v < prev || v < 0 || v > 1) return false;
    prev = v;
  }
  return true;
})());
// —— D. 0.75px 最小可见位移规则(单格像素 = 绘图宽/点数) ——
ok("短窗 40 点/800px = 20px/格 -> 播 L0 过渡", _qbFxCellPx(800, 40) === 20 && _qbFxShouldShift(20));
ok("24h 长窗 2880 点/800px ~ 0.28px/格 -> 瞬时落地", _qbFxCellPx(800, 2880) < 0.75
  && !_qbFxShouldShift(_qbFxCellPx(800, 2880)));
ok("边界 0.75px 恰好可播(>= 判据)", _qbFxShouldShift(0.75) && !_qbFxShouldShift(0.749));
ok("量不到宽/零点数 -> 瞬时(宁可不动画不可错动画)", !_qbFxShouldShift(_qbFxCellPx(0, 40))
  && !_qbFxShouldShift(_qbFxCellPx(800, 0)));
// —— E. L1 双轨独立(上传 Δ=0 静默 + 下载 Lv.3 各自正确, 互不串味 —— I10/D2) ——
let up = _qbFxTrackNext({ prev: 100, target: 100, shown: 100, delta: 0, level: 0, live: true }, 100, 2);
let dl = _qbFxTrackNext({ prev: 50, target: 50, shown: 50, delta: 0, level: 0, live: true }, 100, 2);
ok("上传 Δ=0 -> level 0 静默", up.live && up.delta === 0 && up.level === 0);
ok("下载 50->100(delta=1.0) -> Lv.3", dl.level === 3 && close(dl.delta, 1) && dl.live);
ok("两轨 prev/shown 各自接续不串味", up.prev === 100 && up.shown === 100 && dl.prev === 50 && dl.shown === 50);
// —— F. Δ 分档阈值(0.005 静默线 / 0.05 / 0.30; 端点归属: >=0.005 起 Lv.1, >=0.05 起 Lv.2, >=0.3 Lv.3) ——
const lvl = (prev, target, fl) => _qbFxTrackNext({ shown: prev }, target, fl === undefined ? 1 : fl).level;
ok("Δ<0.5% 静默(level 0)", lvl(1000, 1004.9) === 0);
ok("Δ=0.5% -> Lv.1", lvl(1000, 1005) === 1);
ok("Δ<5% Lv.1", lvl(1000, 1049.9) === 1);
ok("Δ=5% -> Lv.2", lvl(1000, 1050) === 2);
ok("Δ<30% Lv.2", lvl(1000, 1299.9) === 2);
ok("Δ=30% -> Lv.3", lvl(1000, 1300) === 3);
ok("live=false 恒 level 0(缺口轨静默)", _qbFxLevel(9, false) === 0 && _qbFxLevel(0.9, false) === 0);
// —— G. 缺口轨(live=false)与复活轨(D4/I10: 单列 null 该轨断线不插值, 另一轨照常) ——
let dead = _qbFxTrackNext({ prev: 42, target: 42, shown: 42, delta: 0, level: 1, live: true }, null, 2);
ok("尾桶 null -> 轨死: live=false/level 0/shown null(不插值)", !dead.live && dead.level === 0
  && dead.shown === null && dead.prev === null);
let rev = _qbFxTrackNext({ prev: null, target: null, shown: null, delta: 0, level: 0, live: false }, 500, 2);
ok("复活轨: 无从接续直落真值(不造 0->500 斜坡撒谎), delta=0 静默", rev.live && rev.prev === 500
  && rev.shown === 500 && rev.delta === 0 && rev.level === 0);
// —— H. 分母可视下限(防 prev≈0 相对爆炸)与 0->0 守卫 ——
let tiny = _qbFxTrackNext({ shown: 0 }, 1, 2);
ok("prev=0: 分母=max(0,floor)=2, delta 有界(0.5)", close(tiny.delta, 0.5) && tiny.level === 3);
let zero = _qbFxTrackNext({ shown: 0 }, 0, 0);
ok("0->0: 分母 0 守卫 delta=0 -> level 0(零流量静默)", zero.delta === 0 && zero.level === 0 && zero.live);
// —— I. 以显示值接续不回跳(I3): 打断中值作为下一拍 prev, 收敛序列单调落在 [prev, target] ——
const seq = (prevShown, target, p) => _qbFxShown(_qbFxTrackNext({ shown: prevShown }, target, 0.01), p);
ok("上拍打断在 0.7, 新拍 target 1.0: prev=0.7 接续(禁止回跳)", _qbFxTrackNext({ shown: 0.7 }, 1.0, 0.01).prev === 0.7);
ok("上行收敛单调不回跳不越界(0.7 -> 1.0, 终点恰真值)", (() => {
  let prev = -1;
  for (let i = 0; i <= 100; i++) {
    const v = seq(0.7, 1.0, i / 100);
    if (v < prev - 1e-12 || v < 0.7 - 1e-12 || v > 1.0 + 1e-12) return false;
    prev = v;
  }
  return close(seq(0.7, 1.0, 0), 0.7) && close(seq(0.7, 1.0, 1), 1.0);
})());
ok("下行收敛同样单调(0.7 -> 0.3, 不回跳不上穿)", (() => {
  let prev = 2;
  for (let i = 0; i <= 100; i++) {
    const v = seq(0.7, 0.3, i / 100);
    if (v > prev + 1e-12 || v < 0.3 - 1e-12 || v > 0.7 + 1e-12) return false;
    prev = v;
  }
  return true;
})());
ok("收敛终点恒为真值(shown(p=1) === target)", close(seq(0.7, 1.0, 1), 1.0) && close(seq(10, 20, 1), 20));
console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
"""

# 节拍调度器行为面 node 电池(S1): 真 mixin 方法 + 桩 uPlot 域对象 + 假 rAF/performance 时钟,
# 逐帧断言判定帧语义(起拍摆回/单调收敛/打断接续/隐藏暂停/reduce 短路/0.75px/跨窗/销毁终止)。
# 无 node 静默跳过(同 _NODE_QB_TRAFFIC_PROBE 口径)。
_NODE_QB_BEAT_SCHED_PROBE = r"""
const fs = require("fs");
global.window = {};
const src = fs.readFileSync(process.argv[1], "utf8");
const { methods } = new Function(src + "\nreturn { methods: window.AQB_QB_TRAFFIC.methods };")();
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);
// —— 桩环境: 假 rAF 队列 + 可拨动的毫秒时钟 + 可开关的页面可见性 ——
let rafId = 0;
const rafMap = new Map();
global.requestAnimationFrame = (cb) => { rafMap.set(++rafId, cb); return rafId; };
global.cancelAnimationFrame = (id) => { rafMap.delete(id); };
let nowMs = 0;
Object.defineProperty(global, "performance", { value: { now: () => nowMs }, configurable: true });
global.document = { hidden: false };
/* 桩 uPlot 域对象, 提交语义按 vendor qn 忠实复刻: setScale 只写 pending(Kl), commit 消费 ——
 * x 提交即 An(!0)(可视窗重定), y 无手动钉时按可视窗重算(偏置窗会剔出窗沿峰值), 有钉原样拷贝。
 * y 重推面不忠实复刻的话, y 钉断言就是空转, 故先有 S0 对照用例证明桩会漂移。 */
function mkU(xs, up, dl) {
  const u = {
    root: { isConnected: true },
    data: [xs, up, dl],
    scales: { x: { min: xs[0], max: xs[xs.length - 1] }, y: { min: 0, max: 1 } },
    bbox: { width: 800 },
    yCap: 0,
    pending: {},
    setScaleLog: [], setDataCount: 0, redrawCount: 0, destroyed: false,
    setScale(k, r) {
      this.pending[k] = { min: r.min, max: r.max };
      this.setScaleLog.push([k, r.min, r.max]);
    },
    setData(d) {
      this.data = d;
      this.setDataCount++;
      this.pending = { x: { min: d[0][0], max: d[0][d[0].length - 1] } };  // resetScales=true: x auto 全窗
      this.commit();
    },
    redraw() {
      this.redrawCount++;
      this.pending.x = { min: this.scales.x.min, max: this.scales.x.max };  // vendor redraw(true) 走 setScale(x, current)
      this.commit();
    },
    commit() {
      const px = this.pending.x;
      const py = this.pending.y;
      this.pending = {};
      if (!px) {
        if (py) this.scales.y = { min: py.min, max: py.max };
        return;
      }
      const xs = this.data[0];
      let lo = 0;
      let hi = xs.length - 1;
      while (lo < hi && xs[lo] < px.min) lo++;
      while (hi > lo && xs[hi] > px.max) hi--;
      if (py) {
        this.scales.y = { min: py.min, max: py.max };  // Kl.y 非 null: 原样拷贝, 跳过重推(vendor Bl)
      } else {
        let dmax = 0;  // y.auto: 按可视窗重算(vendor An(!0) + bn) —— 偏置窗会剔出窗沿峰值
        for (const col of [this.data[1], this.data[2]]) {
          for (let i = lo; i <= hi; i++) {
            const v = col[i];
            if (v != null && v > dmax) dmax = v;
          }
        }
        const top = dmax > 0 ? dmax * 1.05 : 1;
        this.scales.y = { min: 0, max: this.yCap > 0 ? Math.max(this.yCap, top) : top };
      }
      this.scales.x = { min: px.min, max: px.max };
    },
    destroy() { this.destroyed = true; },
  };
  return u;
}
function mkBeat(xs0, n, upShown, dlShown) {
  return {
    raf: 0, anim: null, xs0, n,
    tracks: {
      up: { prev: upShown, target: upShown, shown: upShown, delta: 0, level: 0, live: true },
      dl: { prev: dlShown, target: dlShown, shown: dlShown, delta: 0, level: 0, live: true },
    },
  };
}
const self = Object.assign({}, methods, {
  _qbPollMs: () => 3000,  // multiplier=2: period 3s -> beat 1000 / shift 600 / converge [120,600]
  _qbCharts: {},
});
const CFG_ON = { enabled: true, on: true, shiftRatio: 0.6 };
global.window.AQB_FX_CFG = CFG_ON;
const XS1 = [1030, 1060, 1090, 1120, 1150];
const pump = () => {
  const fns = [...rafMap.values()];
  rafMap.clear();
  fns.forEach((f) => f());
  const cu = self._qbCharts.global;
  if (cu && cu.commit) cu.commit();  // 微任务渲染等价(同步块内 setScale 攒 pending, 帧末提交)
};
const drain = () => { let g = 0; while (rafMap.size && g++ < 200) { nowMs += 50; pump(); } return g; };
// —— S0: 桩忠实性对照 —— 无 y 钉的裸 x 提交确实按偏置可视窗重推 y(窗沿峰值出窗) ——
{
  const u = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u.setScale("x", { min: 1000, max: 1120 });  // 判定帧偏置视口(尾峰 60 出窗)
  u.commit();
  ok("S0 桩忠实性: 无 y 钉的 x 提交重推 y(峰值出窗 -> dmax=0 -> top=1, 复现 vendor 漂移)",
    u.scales.y.max === 1);
}
// —— S1/S2: 完整一拍 —— 起拍摆回旧位 + y 钉恒定 + 逐帧归零 + 收敛真值(I1/I3/I4/I8 电池级) ——
{
  const u = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1000, 5, 10, 55);  // 上拍窗起点 1000(旧窗 [1000,1120]), 尾显示值 10/55
  self._qbCharts = { global: u };
  const t0 = nowMs;
  self._qbBeatStart("global", u);
  u.commit();
  ok("S1 起拍: rAF 已挂 + 尾点摆回显示值(10/55) + 视口摆回旧位 [1000,1120]", rafMap.size === 1
    && u.data[1][4] === 10 && u.data[2][4] === 55
    && u.setScaleLog.length === 2 && u.setScaleLog[0][0] === "x"
    && u.setScaleLog[0][1] === 1000 && u.setScaleLog[0][2] === 1120);
  ok("S1 y 钉成对(x 提交必配 y) + 钉值 = 全窗真值档位 63(真峰 60 x1.05, 非显示尾值)",
    u.setScaleLog[1][0] === "y" && u.setScaleLog[1][1] === 0 && u.setScaleLog[1][2] === 63
    && u.scales.y.max === 63);
  const tails = [];
  const ySeen = [];
  let guard = 0;
  while (rafMap.size && guard++ < 100) {
    nowMs += 50;
    pump();
    if (u._qbBeat && u._qbBeat.anim) {
      tails.push([u.data[1][4], u.data[2][4]]);
      ySeen.push(u.scales.y.max);
    }
  }
  ok("S2 收敛帧: setData 交还 auto + 两轨真值写回(30/60) + 冻结清除 + anim 收口", u.setDataCount === 1
    && u.data[1][4] === 30 && u.data[2][4] === 60 && u._qbBeat.anim === null
    && u._qbTickFreeze === null && u._qbTickFreezePending === false && u._qbBeat.raf === 0);
  ok("S2 I1 电池级: 动画结束时刻 - 判定时刻 <= beat(1000ms)", nowMs - t0 <= 1000);
  ok("S2 尾点序列单调收敛(10->30 与 55->60 无回跳无 overshoot)", tails.length > 3
    && tails.every((v, i) => i === 0 || (v[0] >= tails[i - 1][0] - 1e-12 && v[1] >= tails[i - 1][1] - 1e-12))
    && tails[0][0] >= 10 && tails[tails.length - 1][0] <= 30);
  const xsLog = u.setScaleLog.filter((r) => r[0] === "x");
  ok("S2 视口偏置逐帧归零(dx 单调收缩, 末帧逼近真窗起点 1030)", xsLog.length > 3
    && xsLog.every((r, i) => i === 0 || r[1] > xsLog[i - 1][1]) && xsLog[xsLog.length - 1][1] > 1020);
  ok("S2 I4 纵轴定档: 每帧 y 恒 63(动画全程零漂移), 收敛帧 auto 重推同值(交还无跳变)",
    ySeen.length > 3 && ySeen.every((v) => v === 63) && u.scales.y.max === 63);
  ok("S2 每个 x 提交都成对补 y(计数相等)", xsLog.length === u.setScaleLog.filter((r) => r[0] === "y").length);
}
// —— S3: 打断接续(隐藏恢复竞态形态: 上拍未收敛即被新拍打断) ——
{
  const u = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1000, 5, 10, 55);
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  for (let i = 0; i < 5; i++) { nowMs += 50; pump(); }  // clock 200: 尾点已越过 impact 窗
  const midUp = u.data[1][4];
  u.data = [[1060, 1090, 1120, 1150, 1180], [0, 0, 0, 0, 80], [0, 0, 0, 0, 60]];
  self._qbBeatStart("global", u);
  ok("S3 打断: 新拍以当前显示值接续(prev=中断值, 不回跳到 10), 旧 rAF 已摘", rafMap.size === 1
    && midUp > 10 && u._qbBeat.tracks.up.prev === midUp && u.data[1][4] === midUp);
  drain();
  ok("S3 新拍照常收敛到新真值(80)", u.data[1][4] === 80 && u._qbBeat.anim === null);
}
// —— S4: 页面隐藏暂停 + 恢复从当前显示值接续(不重播整拍) ——
{
  const u = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1000, 5, 10, 55);
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  for (let i = 0; i < 3; i++) { nowMs += 50; pump(); }  // clock 100
  const before = { scale: u.setScaleLog.length, tail: u.data[1][4] };
  global.document.hidden = true;
  nowMs += 5000;
  pump(); pump(); pump();  // 隐藏期 rAF 照常回调但时钟不推进
  ok("S4 隐藏暂停: 拍内时钟冻结(clock 恒 100, 视口/尾点零变化)", u._qbBeat.anim !== null
    && u._qbBeat.anim.clock === 100 && u.setScaleLog.length === before.scale
    && u.data[1][4] === before.tail);
  global.document.hidden = false;
  nowMs += 50;
  pump();  // 恢复首帧: dt 从 0 起算(不吞隐藏 5s), dx 与 shown 均无变化 -> 不提交
  ok("S4 恢复接续: 不重播整拍(clock 仍 100 续跑, 未吞 5s 未归 0)", u._qbBeat.anim !== null
    && u._qbBeat.anim.clock === 100);
  nowMs += 50;
  pump();  // 下一帧 clock 150: 正常推进
  ok("S4 恢复后正常推进(clock 150)", u._qbBeat.anim !== null && u._qbBeat.anim.clock === 150);
  drain();
  ok("S4 恢复后照常收敛至真值", u.data[1][4] === 30 && u._qbBeat.anim === null);
}
// —— S5/S6: reduce 短路(I7) vs enabled=false 不短路(§05.6) ——
{
  global.window.AQB_FX_CFG = { enabled: true, on: false, shiftRatio: 0.6 };
  const u = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1000, 5, 10, 55);
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  ok("S5 reduce 短路: 零 rAF/零 setScale/u.data 恒真值(退回原快路 + 瞬时左移)", rafMap.size === 0
    && u.setScaleLog.length === 0 && u.data[1][4] === 30 && u.data[2][4] === 60
    && u._qbBeat.tracks.up.shown === 30);
  // S6 换一份新落袋数据(窗口滚一格 + 尾值变化), enabled=false 时 L0/L1 必须照常执行
  global.window.AQB_FX_CFG = { enabled: false, on: false, shiftRatio: 0.6 };
  u.data = [[1060, 1090, 1120, 1150, 1180], [0, 0, 0, 0, 40], [0, 0, 0, 0, 60]];
  self._qbBeatStart("global", u);
  ok("S6 enabled=false 不短路: L0/L1 照常执行(数据刷新语义, 不是装饰)", rafMap.size === 1
    && u.setScaleLog.length === 2 && u.setScaleLog[0][0] === "x" && u.setScaleLog[0][1] === 1030
    && u.data[1][4] === 30);
  drain();
  ok("S6 enabled=false 收敛落地", u.data[1][4] === 40 && u._qbBeat.anim === null);
  global.window.AQB_FX_CFG = CFG_ON;
}
// —— S7/S7b: 零变化拍(同网格)静默 / 零变化滚窗(dx0=step>0 尾值不变) L0 照常 ——
{
  const u = mkU([1000, 1030, 1060, 1090, 1120], [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1000, 5, 30, 60);  // 同网格(dx0=0) + 尾值无变化
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  ok("S7 零变化拍: 零 rAF 零提交(D2 静默)", rafMap.size === 0 && u.setScaleLog.length === 0
    && u.setDataCount === 0 && u.redrawCount === 0);
}
{
  // §06 S1 验收「零变化连拍零装饰但窗口仍滚一格」: dx0=step>0 且尾值与上拍显示值相同 ——
  // L0 由窗口滚动驱动照常播放, 尾点零改写零 redraw(窗口滚动与数据驱动解耦的另一半)
  const u = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1000, 5, 30, 60);
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  ok("S7b 零变化滚窗: L0 照常起拍(rAF=1 + 视口摆回旧位 [1000,1120] + y 钉成对)", rafMap.size === 1
    && u.setScaleLog.length === 2 && u.setScaleLog[0][0] === "x"
    && u.setScaleLog[0][1] === 1000 && u.setScaleLog[0][2] === 1120
    && u.setScaleLog[1][0] === "y");
  const tailAtStart = [u.data[1][4], u.data[2][4]];
  drain();
  ok("S7b 零变化滚窗: 全程尾点零改写零 redraw, 收敛帧 setData 交还 auto", u.data[1][4] === tailAtStart[0]
    && u.data[2][4] === tailAtStart[1] && u.redrawCount === 0 && u.setDataCount === 1
    && u._qbBeat.anim === null);
}
// —— S8: 长窗 0.75px 规则(不播 L0, 尾点真变化仍收敛) ——
{
  const xs = Array.from({ length: 2880 }, (_, i) => 1000 + i * 30);
  const up = new Array(2880).fill(0);
  up[2879] = 30;
  const dl = new Array(2880).fill(0);
  const u = mkU(xs, up, dl);
  u._qbBeat = mkBeat(970, 2880, 10, 0);  // dx0=30(滚一格) 但 cellPx=800/2880 约 0.28 < 0.75
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  ok("S8 长窗 0.75px 规则: 不播 L0(零 setScale), 尾点真变化仍走收敛", u.setScaleLog.length === 0
    && rafMap.size === 1 && u.data[1][2879] === 10);
  // ySeen 口径同 S2(逐帧记在途帧 scales.y.max), 差异: S8 不播 L0, impact 窗帧(clock<120)
  // 尾点未动零提交(逐帧提交守卫), y 还是 mkU 初值 —— 只记「本帧确有绘制」的帧, 静默帧不混入。
  const drawn = () => u.setScaleLog.length + u.redrawCount + u.setDataCount;
  const ySeen = [];
  let guard = 0;
  let lastDrawn = drawn();
  while (rafMap.size && guard++ < 100) {
    nowMs += 50;
    pump();
    if (u._qbBeat && u._qbBeat.anim && drawn() > lastDrawn) {
      lastDrawn = drawn();
      ySeen.push(u.scales.y.max);
    }
  }
  ok("S8 长窗尾点收敛落地(逐帧 y 钉 + redraw 重画)", u.data[1][2879] === 30 && u._qbBeat.anim === null
    && u.redrawCount > 3 && u.setScaleLog.every((r) => r[0] === "y" && r[2] === 31.5)
    && ySeen.length > 3 && ySeen.every((v) => v === 31.5));
}
// —— S9/S9b: 跨窗换档瞬时 / 多桶滚动(roll 上界)瞬时 ——
{
  const u = mkU([1000, 1030, 1060], [0, 0, 50], [0, 0, 70]);  // n 5 -> 3: 跨窗换档重定标
  u._qbBeat = mkBeat(1000, 5, 10, 55);
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  ok("S9 跨窗换档(n 变化): 不播过渡瞬时落地(尾桶已非同一桶, 不造假 morph)", rafMap.size === 0
    && u.setScaleLog.length === 0 && u._qbBeat.tracks.up.shown === 50);
}
{
  const u = mkU([1090, 1120, 1150, 1180, 1210], [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1000, 5, 30, 60);  // dx0 = 90 = 3x step(30) > 2x step: 多桶滚动非滚动语义
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  ok("S9b 多桶滚动(dx0=3x step 超 roll 上界): 瞬时落地零 rAF 零 setScale", rafMap.size === 0
    && u.setScaleLog.length === 0 && u._qbBeat.tracks.up.shown === 30);
}
{
  // roll 判据 `dx0 <= step * 2` 的恰边界: 2 格滚动仍在滚动语义内, 照播 L0 过渡(判据改 < 即红)
  const u = mkU([1060, 1090, 1120, 1150, 1180], [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1000, 5, 30, 60);  // dx0 = 1060-1000 = 60 = 2x step(30): 恰落 roll 上界
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  ok("S9b roll 恰边界(dx0=2x step): 仍播 L0 过渡(rAF=1 + 视口摆回旧位 [1000,1120] + y 钉成对)",
    rafMap.size === 1 && u.setScaleLog.length === 2 && u.setScaleLog[0][0] === "x"
    && u.setScaleLog[0][1] === 1000 && u.setScaleLog[0][2] === 1120
    && u.setScaleLog[1][0] === "y");
  drain();  // 收敛落地清 rAF, 不给后续块留残余帧
  ok("S9b roll 恰边界收敛落地: 尾值无变化零 redraw, setData 交还 auto", u._qbBeat.anim === null
    && u.redrawCount === 0 && u.setDataCount === 1 && u.data[1][4] === 30 && u.data[2][4] === 60);
}
// —— S10: 销毁终止(换肤/关抽屉路径) ——
{
  const u = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1000, 5, 10, 55);
  self._qbCharts = { global: u };
  self._qbChartRos = { global: { disconnect() { } } };
  self._qbBeatStart("global", u);
  ok("S10 起拍就绪", rafMap.size === 1);
  const atStart = { scale: u.setScaleLog.length, data: u.setDataCount };
  self._qbChartDestroy("global");
  ok("S10 销毁终止: rAF 先摘 + 图已销毁(不留半帧)", rafMap.size === 0 && u.destroyed === true
    && self._qbCharts.global === null);
  pump();  // 已摘的回调不得再跑
  ok("S10 销毁后无残余帧(提交数停在起拍时刻)", u.setScaleLog.length === atStart.scale
    && u.setDataCount === atStart.data);
}
// —— S11: 在途拍内 _qbChartRescale(y 切档/限速变化入口): 终止在途拍直接落真值 ——
{
  const u = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1000, 5, 10, 55);
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  for (let i = 0; i < 4; i++) { nowMs += 50; pump(); }  // clock 150: 插值中
  u._qbTickFreeze = ["10:00", "10:01"];  // 模拟冻结已挂(状态面预设, 验 rescale 清冻结)
  ok("S11 前置: 在途拍插值中(尾点偏离真值)", u._qbBeat.anim !== null && u.data[1][4] > 10
    && u.data[1][4] < 30);
  self._qbChartRescale("global");
  ok("S11 rescale: 在途拍终止 + 真值直接落袋 + ticks 冻结清除 + setData 交还(不留半帧)",
    rafMap.size === 0 && u._qbBeat.anim === null && u.data[1][4] === 30 && u.data[2][4] === 60
    && u._qbTickFreeze === null && u.setDataCount === 1);
  pump();
  ok("S11 rescale 后无残余帧", u.setDataCount === 1 && u._qbBeat.anim === null);
}
console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
"""


def test_frontend_qb_beat_kernel_battery():
    """节拍内核 S1 电池 + 接缝静态钉(plan 26-11-12-1139 §03 节奏模型/L0/L1, §06 S1 行)

    行为面(node 电池, 无 node 静默跳过, 同 _NODE_QB_TRAFFIC_PROBE 口径):
    1. 节奏公式四组(I1/I2): multiplier 1(1.5s->600ms)/2(3s->夹顶 1000)/8(12s->夹顶)/600s 长窗
      (夹顶); beat 下限 320 与非法 period 防御;
    2. 每拍时间线(§03 公式代码块): impact 0.12 / shift=shiftRatio×beat(防御夹取 [0.2,1] 与
      缺省 0.6)/ converge [0.12,0.6] / tail = min(period-beat, 2000) 封顶非常驻(P5);
      animEnd <= beat <= 1000 全域扫(I1 真值在 t<=beat<=1s 完全落地的可验证面);
    3. easeOut 单调无 overshoot(D9 禁 spring): 1000 采样单调不减、恒在 [0,1]、端点/特征值;
    4. 0.75px 最小可见位移规则: 短窗播 L0 / 24h 长窗(2880 点)瞬时 / 0.75 边界(>=)/ 量不到宽瞬时;
    5. L1 双轨独立(I10/D2): 上传 Δ=0 静默 + 下载 Lv.3 各自正确; Δ 分档端点归属(0.005/0.05/0.30);
      缺口轨 live=false 不插值(D4)/复活轨直落真值不造斜坡/分母可视下限防爆炸/0->0 守卫;
    6. 以显示值接续不回跳(I3): 打断中值作下一拍 prev, 上下行收敛序列单调落在 [prev,target] 内、
      终点恰真值;
    7. 调度器行为面(_NODE_QB_BEAT_SCHED_PROBE: 真 mixin 方法 + **提交语义忠实 vendor 的桩 uPlot**
      (setScale 攒 pending、x 提交即 An(!0)、y 无钉按可视窗重算/有钉原样拷贝, S0 对照用例先证桩
      会漂移) + 假 rAF/时钟, 逐帧断言): 完整一拍(起拍视口摆回旧位 [xs0-old] + 尾点摆回显示值
      -> 逐帧 dx 单调收缩归零 + 两轨尾点单调收敛 + 收敛帧 setData 交还 auto/真值写回/冻结清除,
      动画结束-判定 <= beat = I1 电池级)/打断接续(中断值作新拍 prev 不回跳, 旧 rAF 已摘)/页面
      隐藏暂停(时钟冻结零变化)与恢复接续(不吞隐藏时长不重播)/reduce 短路(零 rAF 零 setScale
      真值面) vs enabled=false 不短路(L0/L1 照常)/零变化拍零提交/长窗 0.75px(零 setScale 但尾点
      真变化仍收敛)/跨窗换档瞬时/多桶滚动(roll 上界 dx0>2x step)瞬时/_qbChartDestroy 先摘 rAF
      后销毁无残余帧;
    8. I4 纵轴定档电池级(评审 #1 回归钉): 起拍与每个 shift 帧 setScale("x") 成对补 setScale("y",
      全窗真值档位 yMax = _qbYRange x _qbYCapOf 口径) —— 动画全程 y 恒定零漂移(桩忠实复刻下,
      无钉时 y 会随偏置窗剔出窗沿峰值垂直跳), 收敛帧 setData auto 重推同值(交还无跳变); x/y
      提交计数相等; 零变化滚窗(S7b)与纯数值收敛帧(S8)的 y 钉面各自覆盖;
    9. rescale 在途拍收口(评审 #6 回归钉): _qbChartRescale 在插值中触发 -> 在途拍终止 + 真值
      直接落袋 + ticks 冻结清除 + setData 交还(不留半帧), 后续无残余帧。
    接缝面(静态钉):
    a. 续拉快路 :426 逐字行后**追加** _qbBeatStart(不改写既有字面量 —— §09「守阵逐字断言」行);
    b. L0 视口偏置(t=0 摆回旧位 + 每帧 dx 归零)与收敛帧 setData 交还 auto 的成对在位;
    c. ticks 冻结: needsShift 支路挂 pending、收敛帧清冻结先于 setData(一次性刷新序);
    d. reduce 短路判据读 AQB_FX_CFG 的 on 有效值(on=false 的 reduce 分量才短路, I7);
    e. _qbChartDestroy 先 _qbBeatCancel 再 u.destroy()(换肤/关抽屉终止在途动画不留半帧);
    f. 面板 beat 展示值复用 _qbBeatMs 单点(第二份 clamp 公式退场);
    g. BOM 纪律: rAF/performance.now/document.hidden 只出现在 mixin 方法域, 模块级头部零触碰
      (node 探针 eval 本文件的顶层约束);
    h. I3 反向钉: 调度器域零 destroy/new uPlot/零 loading 触碰(逐帧 commit 只走 setScale/redraw);
    i. tooltip 读数面接缝(I4): _qbHoverOf 读 Vue points(d.points[i]) 不读 u.data —— 与 L1 尾点
      插值写面(u.data 绘制面)零交集, 动画期 tooltip 与已落袋真值逐字一致。"""
    shared = os.path.join(STATIC_ROOT, "shared")
    js = open(os.path.join(shared, "qb_traffic_chart.js"), encoding="utf-8").read()
    # —— 接缝静态钉 ——
    # a. 快路逐字行 + 同帧起拍(追加不改写)
    assert re.search(r"prev\.setData\(\[data\.xs, data\.up, data\.dl\]\);\n\s*this\._qbBeatStart\(scope, prev\);", js), \
        "续拉快路 setData 逐字行后必须同帧追加 _qbBeatStart(S1 判定帧; 既有字面量不得改写)"
    # b. L0 成对: 判定帧摆回旧位 + 每帧 dx 归零 + 收敛帧 setData 交还 auto;
    #    y 钉成对(I4 纵轴瞬时定档): x 提交会让 uPlot 按偏置可视窗重推 y(vendor qn: Kl.x 非 null
    #    -> An(!0) -> y.auto 重算) —— 起拍与每个 shift 帧的 setScale("x") 必须成对补
    #    setScale("y", 全窗真值档位), 纯数值收敛帧(y 钉 + redraw)同样要盖; 钉值口径 = 建图
    #    range 单点(_qbYRange x _qbYCapOf), 不是显示尾值
    start_blk = re.search(r"_qbBeatStart\(scope, u\) \{\n(.*?)\n    \},", js, re.S)
    assert start_blk, "qb_traffic_chart.js 缺 _qbBeatStart(判定帧开工单点)"
    assert 'u.setScale("x", { min: xs[0] - dx0, max: xs[n - 1] - dx0 });' in start_blk.group(1), \
        "L0 判定帧必须把视口摆回旧位置(setScale x 偏置 dx0, 时间量纲)"
    frame_blk = re.search(r"_qbBeatFrame\(scope\) \{\n(.*?)\n    \},", js, re.S)
    assert frame_blk, "qb_traffic_chart.js 缺 _qbBeatFrame(每帧推进单点)"
    assert 'u.setScale("x", { min: xs[0] - dx, max: xs[n - 1] - dx });' in frame_blk.group(1) \
        and "_qbFxEaseOut(a.clock / tl.shiftMs)" in frame_blk.group(1), \
        "L0 每帧按真实毫秒推进: dx = (1 - easeOut(clock/shiftMs)) * dx0 归零式"
    for name, blk in (("_qbBeatStart", start_blk.group(1)), ("_qbBeatFrame", frame_blk.group(1))):
        assert 'u.setScale("y", { min: 0, max: yMax });' in blk or 'u.setScale("y", { min: 0, max: a.yMax });' in blk, \
            f"{name} 缺 y 钉成对(x 提交不配 y 钉 = 动画期纵轴按偏置可视窗重推, I4 纵轴瞬时定档被破)"
    sb, fb = start_blk.group(1), frame_blk.group(1)
    assert sb.index('u.setScale("x", { min: xs[0] - dx0') < sb.index('u.setScale("y", { min: 0, max: yMax });'), \
        "_qbBeatStart 的 y 钉必须紧跟 x 摆回(同一提交批, 缺 y = 该提交按偏置窗重推 y)"
    assert fb.index('u.setScale("x", { min: xs[0] - dx') < fb.index('u.setScale("y", { min: 0, max: a.yMax });'), \
        "_qbBeatFrame 的 y 钉必须紧跟 x 提交(同一提交批)"
    # 纯数值收敛帧必须先钉 y 再 redraw(S2-a 起 _qbBeatFrame 前段还有次区相位的清理 redraw,
    # 全方法体首现下标比对失真 —— 改在 tailChanged 块内定位, 守的是同一对不变量)
    tail_conv = re.search(r"if \(tailChanged && !dxChanged\) \{\n(.*?)\n      \}", frame_blk.group(1), re.S)
    assert tail_conv and 'u.setScale("y", { min: 0, max: a.yMax });' in tail_conv.group(1) \
        and tail_conv.group(1).index('u.setScale("y", { min: 0, max: a.yMax });') \
        < tail_conv.group(1).index("u.redraw();"), \
        "纯数值收敛帧必须先钉 y 再 redraw(redraw 内部 setScale(x, current) 同样触发 y 重推)"
    assert "_qbYRange(dmax, this._qbYCapOf(scope))[1]" in sb, \
        "y 钉值必须复用建图 range 单点口径(_qbYRange x _qbYCapOf = 真窗档位 yMax, 不是显示尾值)"
    conv_blk = re.search(r"_qbBeatConverge\(scope, u\) \{\n(.*?)\n    \},", js, re.S)
    assert conv_blk, "qb_traffic_chart.js 缺 _qbBeatConverge(收敛帧单点)"
    assert "u.setData([u.data[0], u.data[1], u.data[2]]);" in conv_blk.group(1), \
        "收敛帧必须 setData 交还 auto range(uPlot 无持久手动 range, resetScales 默认即重推 auto)"
    assert 'setScale("y"' not in conv_blk.group(1), \
        "收敛帧不得再钉 y(setData 交还 auto 重推的正是真窗档位, 与钉值同值 —— 双钉反而挡住 auto 交还)"
    # c. ticks 冻结序: needsShift 支路挂 pending; 收敛帧清冻结先于 setData(一次性刷新);
    #    等长守卫在位(过渡中 splits 数变化即解除缓存回落现算, 防 uPlot _splits/_values 对位错位)
    assert "u._qbTickFreezePending = true;" in start_blk.group(1), \
        "L0 起拍必须挂 ticks 冻结 pending(判定帧渲染时缓存标签)"
    conv_body = conv_blk.group(1)
    assert conv_body.index("u._qbTickFreeze = null;") < conv_body.index("u.setData([u.data[0]"), \
        "收敛帧必须先清 ticks 冻结再 setData(同一次提交内完成一次性刷新)"
    assert "u._qbTickFreeze.length === splits.length" in js, \
        "ticks 冻结必须带等长守卫(过渡中 splits 数变化即解除缓存回落现算, 防标签与刻位错位)"
    # d. reduce 短路读有效值单点(on = enabled && !reduce 的 S0-b 产物)
    assert "cfg.enabled === true && cfg.on === false" in start_blk.group(1) \
        and "window.AQB_FX_CFG" in start_blk.group(1), \
        "reduce 短路必须读 AQB_FX_CFG.on 有效值(只有 reduce 分量短路, enabled=false 不短路 —— §05.6)"
    # e. 销毁终止: _qbBeatCancel 先于 u.destroy()(换肤/关抽屉不留半帧)
    destroy_blk = re.search(r"_qbChartDestroy\(scope\) \{\n(.*?)\n    \},", js, re.S)
    assert destroy_blk and "_qbBeatCancel(" in destroy_blk.group(1) \
        and destroy_blk.group(1).index("_qbBeatCancel(") < destroy_blk.group(1).index("u.destroy()"), \
        "_qbChartDestroy 必须先摘节拍 rAF 再销毁图(终止在途动画, 不留半帧)"
    # f. 面板 beat 展示值复用单点(第二份公式退场)
    assert "Math.round(_qbBeatMs(this._qbFxCurPeriodMs()))" in js \
        and "Math.min(1000, Math.max(320" not in js, \
        "beat 展示值必须复用 _qbBeatMs 单点(内联 clamp 公式不得回潮 —— 双写即漂移)"
    # g. BOM 纪律: 模块级头部(window.AQB_QB_TRAFFIC 之前)**代码**零 BOM 触碰(注释先剥掉 ——
    #    注释里提到这些 API 是纪律说明不是调用)
    head = js.split("window.AQB_QB_TRAFFIC = {")[0]
    head_code = re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", head, flags=re.S))
    for bom in ("requestAnimationFrame", "performance.now", "document.hidden", "cancelAnimationFrame"):
        assert bom not in head_code, f"模块级头部代码不得触碰 BOM: {bom}(node 探针 eval 约束, 只准方法域惰性取)"
    # h. I3 反向钉: 调度器域零销毁重建/零 loading 触碰(逐帧 commit 只走 setScale/redraw)
    for blk in (start_blk.group(1), frame_blk.group(1), conv_blk.group(1)):
        assert "new uPlot" not in blk and "destroy(" not in blk and "loading" not in blk, \
            "节拍调度器域不得 destroy/new uPlot/触碰 loading 空态(I3 不闪; 逐帧 commit 只走 setScale/redraw)"
    assert "u.redraw();" in frame_blk.group(1), \
        "纯数值收敛帧(视口未动)必须显式 redraw 重建路径(尾点插值才可见)"
    # i. tooltip 读数面接缝(I4): hover 读 Vue points, 与 L1 插值写面(u.data)零交集
    hover_blk = re.search(r"_qbHoverOf\(scope\) \{\n(.*?)\n    \},", js, re.S)
    assert hover_blk and "d.points[i]" in hover_blk.group(1) and "u.data" not in hover_blk.group(1), \
        "悬停取值必须读 Vue points 真值(d.points[i]), 不得读 u.data —— L1 尾点插值写在 u.data 绘制面, 两面零交集"
    # j. rescale 在途拍收口(发现 #6): _qbChartRescale(y 切档/限速变化两入口)在在途拍内触发
    #    必须先落真值 + 终止拍 + 清 ticks 冻结, 再 setData 重排(否则动画帧的 y 钉盖过新档位
    #    一拍、偏置视口与新档位错配一帧); 行为面 = 调度器电池 S11
    rescale_blk = re.search(r"_qbChartRescale\(scope\) \{\n(.*?)\n    \},", js, re.S)
    assert rescale_blk, "qb_traffic_chart.js 缺 _qbChartRescale(y 轴重排单点)"
    rb = rescale_blk.group(1)
    assert "st.anim" in rb and "_qbBeatCancel(" in rb and "u._qbTickFreeze = null;" in rb, \
        "_qbChartRescale 必须收口在途拍(落真值 + _qbBeatCancel + 清冻结), 再 setData 重排"
    assert rb.index("_qbBeatCancel(") < rb.index("u.setData([u.data[0]"), \
        "_qbChartRescale 的拍收口必须先于 setData(先落真值清冻结, 再按新档位重排)"
    # —— 行为面 node 电池(纯函数面 + 调度器行为面各一发) ——
    node = shutil.which("node")
    if not node:
        return
    for probe, tag in ((_NODE_QB_BEAT_PROBE, "节拍内核"), (_NODE_QB_BEAT_SCHED_PROBE, "节拍调度器")):
        proc = subprocess.run(
            [node, "-e", probe, os.path.join(shared, "qb_traffic_chart.js")],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        assert proc.returncode == 0, f"{tag} node 电池跑挂: {proc.stderr.strip()}"
        report = json.loads(proc.stdout.strip().splitlines()[-1])
        assert report["failed"] == [], \
            f"{tag}电池 {report['ok']}/{report['total']} 过, 失败: {report['failed']}"


# 视觉引擎 V + N 层 node 电池(S2-a, plan 26-11-12-1139 §03 V 表/N 节/D1-D4): 常量/仲裁/预算/
# 粒子运动/清单确定性真跑。new Function 取出口径(同 _NODE_QB_BEAT_PROBE); 无 node 静默跳过。
_NODE_QB_FXVIS_PROBE = r"""
const fs = require("fs");
global.window = {};
const src = fs.readFileSync(process.argv[1], "utf8");
const {
  _QB_FX_LAYER_ORDER, _QB_FX_N_WHITELIST, _QB_FX_N_BLACKLIST, _QB_FX_LV_COLORS,
  _QB_FX_BLUR_CAPS, _QB_FX_RING_SIDES, _QB_FX_PART_MAX, _QB_FX_SHARD_MAX,
  _QB_FX_NEON_RATIO, _QB_FX_PART_RATIO, _QB_FX_Y_GAP_PX, _QB_FX_SLICES_MAX,
  _QB_FX_SLICE_SHAKE_PX, _QB_FX_TAIL_PTS_MAX, _QB_FX_TAIL_SPAN_BUCKETS,
  _qbFxLead, _qbFxPartCap, _qbFxAlloc, _qbFxGapScale, _qbFxNeonQ, _qbFxRingAt,
  _qbFxParticleAt, _qbFxSpawnSpecs, _qbFxSlices, _qbFxRand,
} = new Function(src + "\nreturn { _QB_FX_LAYER_ORDER, _QB_FX_N_WHITELIST, _QB_FX_N_BLACKLIST,"
  + " _QB_FX_LV_COLORS, _QB_FX_BLUR_CAPS, _QB_FX_RING_SIDES, _QB_FX_PART_MAX, _QB_FX_SHARD_MAX,"
  + " _QB_FX_NEON_RATIO, _QB_FX_PART_RATIO, _QB_FX_Y_GAP_PX, _QB_FX_SLICES_MAX,"
  + " _QB_FX_SLICE_SHAKE_PX, _QB_FX_TAIL_PTS_MAX, _QB_FX_TAIL_SPAN_BUCKETS,"
  + " _qbFxLead, _qbFxPartCap, _qbFxAlloc, _qbFxGapScale, _qbFxNeonQ, _qbFxRingAt,"
  + " _qbFxParticleAt, _qbFxSpawnSpecs, _qbFxSlices, _qbFxRand };")();
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);
// —— A. I6 图层顺序常量(违反即判失败的单点描述) ——
ok("I6 层序七层逐字", JSON.stringify(_QB_FX_LAYER_ORDER)
  === JSON.stringify(["bg", "grid", "geometry", "neon", "curve", "anchor", "hud"]));
ok("I6 层序: geometry/neon 恒在 curve 之前(装饰不压曲线), anchor 在 curve 之后",
  _QB_FX_LAYER_ORDER.indexOf("geometry") < _QB_FX_LAYER_ORDER.indexOf("curve")
  && _QB_FX_LAYER_ORDER.indexOf("neon") < _QB_FX_LAYER_ORDER.indexOf("curve")
  && _QB_FX_LAYER_ORDER.indexOf("anchor") > _QB_FX_LAYER_ORDER.indexOf("curve"));
// —— B. I11 N 层白名单/黑名单 ——
ok("I11 白名单五元素逐字(判定线短亮段/环外圈/粒子外圈/锚辉光/Lv 徽标)",
  JSON.stringify(_QB_FX_N_WHITELIST)
  === JSON.stringify(["judgeFlash", "ringOuter", "partOuter", "anchorHalo", "lvBadge"]));
ok("I11 黑名单八元素逐字(曲线/绘图区背景/右缘/网格/tooltip/图例/限速虚线恒静态)",
  JSON.stringify(_QB_FX_N_BLACKLIST)
  === JSON.stringify(["curveUp", "curveDl", "plotBg", "edgeBg", "grid", "tooltip", "legend", "limitDash"]));
ok("I11 白名单与黑名单零交集", _QB_FX_N_WHITELIST.every((w) => _QB_FX_N_BLACKLIST.indexOf(w) < 0));
// —— C. V1 Lv 色表(plan §03 V1 行逐字; 四皮肤无令牌已核查, 计划色值常量) ——
ok("V1 Lv 色表: Lv.1 蓝 #7AD9FF / Lv.2 金 #FEFFA9 / Lv.3 品红 #FF6BD6",
  _QB_FX_LV_COLORS[1] === "#7AD9FF" && _QB_FX_LV_COLORS[2] === "#FEFFA9" && _QB_FX_LV_COLORS[3] === "#FF6BD6");
ok("V1 三档配色 shadowBlur 上限: neon 10 / glitch 14 / calm 0",
  _QB_FX_BLUR_CAPS.neon === 10 && _QB_FX_BLUR_CAPS.glitch === 14 && _QB_FX_BLUR_CAPS.calm === 0);
ok("V2 环边数映射: Lv.1 三边 / Lv.2 六边 / Lv.3 八边",
  _QB_FX_RING_SIDES[1] === 3 && _QB_FX_RING_SIDES[2] === 6 && _QB_FX_RING_SIDES[3] === 8);
// —— D. I9 预算常量(全部两轨合计) ——
ok("I9 预算常量: 粒子 32 / 半套 16 / N 0.33 / 粒子窗 0.55 / y 间距 26 / 切片 5 / 微震 3px / 光点 2 / 末段 6 桶",
  _QB_FX_PART_MAX === 32 && _QB_FX_SHARD_MAX === 16 && _QB_FX_NEON_RATIO === 0.33
  && _QB_FX_PART_RATIO === 0.55 && _QB_FX_Y_GAP_PX === 26 && _QB_FX_SLICES_MAX === 5
  && _QB_FX_SLICE_SHAKE_PX === 3 && _QB_FX_TAIL_PTS_MAX === 2 && _QB_FX_TAIL_SPAN_BUCKETS === 6);
// —— E. D3 lead 仲裁(argmax, 优先非缺口非静默轨) ——
const mkTr = (delta, level, live) => ({ prev: 100, target: 100, shown: 100, delta, level, live: live !== false });
ok("lead = argmax: up 0.5 > dl 0.3 -> up", _qbFxLead(mkTr(0.5, 3), mkTr(0.3, 2)) === "up");
ok("lead: dl 更大 -> dl", _qbFxLead(mkTr(0.1, 1), mkTr(0.4, 3)) === "dl");
ok("双轨皆静默(level 0) -> null(零装饰, L0/L1 照常 —— I10/D2)", _qbFxLead(mkTr(0.001, 0), mkTr(0.002, 0)) === null);
ok("缺口轨(live=false)不参与仲裁, 另一轨全量照常(D4)", _qbFxLead(mkTr(0.9, 3, false), mkTr(0.1, 1)) === "dl");
ok("delta 大但 level 0(静默)不参与(优先非静默轨)", _qbFxLead({ delta: 0.9, level: 0, live: true }, mkTr(0.1, 1)) === "dl");
ok("恰等 delta 取 up(稳定序)", _qbFxLead(mkTr(0.3, 2), mkTr(0.3, 2)) === "up");
// —— F. partCap(lead 等级 + 密度参数, 两轨合计上限) ——
ok("partCap 密度 0.7: Lv1 16x0.7=11 / Lv2 24x0.7=17 / Lv3 32x0.7=22",
  _qbFxPartCap(1, 0.7) === 11 && _qbFxPartCap(2, 0.7) === 17 && _qbFxPartCap(3, 0.7) === 22);
ok("partCap 密度 1: Lv3 恰 32(合计上限) / Lv1 16 / Lv2 24",
  _qbFxPartCap(3, 1) === 32 && _qbFxPartCap(1, 1) === 16 && _qbFxPartCap(2, 1) === 24);
ok("partCap 密度 0/负/NaN = 0 粒子(密度关到底即无粒子)",
  _qbFxPartCap(3, 0) === 0 && _qbFxPartCap(3, -0.5) === 0 && _qbFxPartCap(3, NaN) === 0);
ok("partCap 密度 >1 钳 1 / level 0 = 0", _qbFxPartCap(3, 1.7) === 32 && _qbFxPartCap(0, 1) === 0);
// —— G. D3 三策略分配(两轨合计守恒, 各轨 ≤16) ——
ok("both cap22: 11/11 合计守恒", (() => {
  const a = _qbFxAlloc("both", 22, "up");
  return a.up === 11 && a.dl === 11 && a.up + a.dl === 22 && a.merge === 0;
})());
ok("both cap23: ceil 给 up(12/11)", (() => {
  const a = _qbFxAlloc("both", 23, "up");
  return a.up === 12 && a.dl === 11;
})());
ok("both cap32: 各 16 恰半套上限(双轨预算不翻倍 —— I9)", (() => {
  const a = _qbFxAlloc("both", 32, "up");
  return a.up === 16 && a.dl === 16;
})());
ok("lead 策略: 主导轨全套从属零(双向)", (() => {
  const a = _qbFxAlloc("lead", 32, "up");
  const b = _qbFxAlloc("lead", 32, "dl");
  return a.up === 32 && a.dl === 0 && b.up === 0 && b.dl === 32;
})());
ok("merge 策略: 两轨 y 中点一次 merge=cap", (() => {
  const a = _qbFxAlloc("merge", 22, "up");
  return a.merge === 22 && a.up === 0 && a.dl === 0;
})());
ok("未知策略回落 both(保守默认 —— D3-b)", (() => {
  const a = _qbFxAlloc("what", 10, "up");
  return a.up === 5 && a.dl === 5;
})());
ok("cap 0 = 全零", (() => {
  const a = _qbFxAlloc("both", 0, "up");
  return a.up === 0 && a.dl === 0 && a.merge === 0;
})());
ok("全域扫 cap 1..32: both 分配合计守恒且各 ≤16", (() => {
  for (let c = 1; c <= 32; c++) {
    const a = _qbFxAlloc("both", c, "up");
    if (a.up + a.dl !== c || a.up > 16 || a.dl > 16) return false;
  }
  return true;
})());
// —— H. D4 末点 y 间距缩小(<26px 按比例, 下限 0.4 不合并不取消) ——
ok("gapScale: 30px->1 / 26px->1(不放大) / 13px->0.5 / 5px->0.4(下限) / 0 与 NaN->0.4(保留)",
  _qbFxGapScale(30) === 1 && _qbFxGapScale(26) === 1 && _qbFxGapScale(13) === 0.5
  && _qbFxGapScale(5) === 0.4 && _qbFxGapScale(0) === 0.4 && _qbFxGapScale(NaN) === 0.4);
// —— I. N 层回落 0.33×beat(≈20 帧) ——
ok("neonQ: t=0 -> 1 / 半窗 -> 0.5 / >=0.33×beat -> 0 / 负 t -> 0",
  _qbFxNeonQ(0, 1000) === 1 && Math.abs(_qbFxNeonQ(165, 1000) - 0.5) <= 1e-9
  && _qbFxNeonQ(330, 1000) === 0 && _qbFxNeonQ(400, 1000) === 0 && _qbFxNeonQ(-1, 1000) === 0);
// —— J. 冲击扩张环(V2) ——
ok("ring t=0: r=0 alpha=1(判定帧同帧起步)", (() => {
  const r = _qbFxRingAt(0, 1000, 29);
  return r && r.r === 0 && r.alpha === 1;
})());
ok("ring 半窗: r = rMax x easeOut(0.5)=0.875 / alpha 0.5", (() => {
  const r = _qbFxRingAt(275, 1000, 29);
  return r && Math.abs(r.r - 29 * 0.875) <= 1e-9 && Math.abs(r.alpha - 0.5) <= 1e-9;
})());
ok("ring >=0.55×beat -> null(零绘制 —— I9 冲击类叠加层窗)",
  _qbFxRingAt(550, 1000, 29) === null && _qbFxRingAt(600, 1000, 29) === null && _qbFxRingAt(-1, 1000, 29) === null);
// —— K. V3 粒子三阶段(爆发 x4.5 / 拖尾减速透明 / 0.55×beat 后零绘制) ——
const spec = { x0: 100, y0: 50, ang: Math.PI, dist: 100, size: 2, sides: 4, rot0: 0.3, vr: 0.01 };
const V = 100 / (4.5 * 120 + 430);   // beat 1000 / burst 120 / T 550: v = dist/(4.5×burst + trail)
ok("粒子 t=0: 原点起喷 alpha=1(首帧最亮与判定线闪光同帧 —— I9), rot=rot0", (() => {
  const p = _qbFxParticleAt(0, 1000, 120, spec, 0);
  return p && p.x === 100 && p.y === 50 && p.alpha === 1 && Math.abs(p.rot - 0.3) <= 1e-9;
})());
ok("爆发期速度 ×4.5: d(60) = 4.5v×60", (() => {
  const p = _qbFxParticleAt(60, 1000, 120, spec, 0);
  const dExp = 4.5 * V * 60;
  return p && Math.abs(p.d - dExp) <= 1e-9 && Math.abs(p.x - (100 + Math.cos(Math.PI) * dExp)) <= 1e-9;
})());
ok("爆发/拖尾交接连续: d(burst) 恒 4.5v×burst", (() => {
  const p = _qbFxParticleAt(120, 1000, 120, spec, 0);
  return p && Math.abs(p.d - 4.5 * V * 120) <= 1e-9;
})());
ok("拖尾期减速: 等距采样位移步单调收缩(easeOut 减速)", (() => {
  let prevStep = Infinity;
  let prevD = null;
  for (let t = 120; t < 550; t += 30) {
    const p = _qbFxParticleAt(t, 1000, 120, spec, 0);
    if (prevD != null) {
      const step = p.d - prevD;
      if (step > prevStep + 1e-12) return false;
      prevStep = step;
    }
    prevD = p.d;
  }
  return true;
})());
ok("末态: d(T-1) 收敛到 dist / alpha(T/2)=0.5 / t>=T -> null(0.55×beat 后零绘制)", (() => {
  const near = _qbFxParticleAt(549, 1000, 120, spec, 0);
  const mid = _qbFxParticleAt(275, 1000, 120, spec, 0);
  return near && Math.abs(near.d - 100) <= 1e-6 && mid && Math.abs(mid.alpha - 0.5) <= 1e-9
    && _qbFxParticleAt(550, 1000, 120, spec, 0) === null && _qbFxParticleAt(551, 1000, 120, spec, 0) === null;
})());
ok("carryPx: 粒子随 L0 末点滑动(x 平移, 与曲线不脱钩)", (() => {
  const p = _qbFxParticleAt(60, 1000, 120, spec, -7);
  const q = _qbFxParticleAt(60, 1000, 120, spec, 0);
  return p && q && Math.abs((q.x - p.x) - 7) <= 1e-9;
})());
// —— L. 喷射清单(V3 多边形碎片) ——
ok("清单长度 = cap; 同种子恒同清单(同拍重绘不闪变)", (() => {
  const a = _qbFxSpawnSpecs(11, 0, 0, 29, 12345);
  const b = _qbFxSpawnSpecs(11, 0, 0, 29, 12345);
  return a.length === 11 && JSON.stringify(a) === JSON.stringify(b);
})());
ok("碎片三/四/五边(非圆点), 尺寸 1.5-3.5px",
  _qbFxSpawnSpecs(16, 0, 0, 29, 7).every((s) => s.sides >= 3 && s.sides <= 5 && s.size >= 1.5 && s.size <= 3.5));
ok("喷射角铺左向 270° 弧(避开右向 90° 扇区 —— 末点贴判定线, 右向碎片全被裁白费)", (() => {
  return _qbFxSpawnSpecs(32, 0, 0, 29, 99).every((s) => {
    let deg = (s.ang * 180) / Math.PI;
    deg = ((deg % 360) + 360) % 360;
    return deg >= 40 && deg <= 320;
  });
})());
ok("行程 = 1.1-1.6 x 环最大半径",
  _qbFxSpawnSpecs(16, 0, 0, 40, 3).every((s) => s.dist >= 40 * 1.1 - 1e-9 && s.dist <= 40 * 1.6 + 1e-9));
ok("不同种子清单不同(跨拍随尾桶时刻自然变化)",
  JSON.stringify(_qbFxSpawnSpecs(8, 0, 0, 29, 1)) !== JSON.stringify(_qbFxSpawnSpecs(8, 0, 0, 29, 2)));
// —— M. glitch 水平切片(V2) ——
ok("切片 5 条, |dy0| <= 3px(微震 <=5px 上限), len 24-64, alpha0 0.2-0.5, 同种子恒同", (() => {
  const a = _qbFxSlices(5, 100, 42);
  const b = _qbFxSlices(5, 100, 42);
  return a.length === 5 && JSON.stringify(a) === JSON.stringify(b)
    && a.every((s) => Math.abs(s.dy0) <= 3 && s.len >= 24 && s.len <= 64 && s.alpha0 >= 0.2 && s.alpha0 <= 0.5);
})());
// —— N. 伪随机确定性 ——
ok("同种子同序列 / 异种子异序列", (() => {
  const r1 = _qbFxRand(7);
  const r2 = _qbFxRand(7);
  const r3 = _qbFxRand(8);
  for (let i = 0; i < 10; i++) {
    const v = r1();
    if (v !== r2() || v === r3()) return false;
  }
  return true;
})());
console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
"""

# 视觉引擎调度器 fx 面 node 电池(S2-a): 真 mixin 方法 + 桩 uPlot(含 valToPos/bbox 全量, 提交语义
# 同节拍调度器电池) —— fx 生成门 / 三策略落 fx / D4 实测 / 装饰帧保障 / 次区相位全生命周期。
# 无 node 静默跳过(同 _NODE_QB_TRAFFIC_PROBE 口径)。
_NODE_QB_FXVIS_SCHED_PROBE = r"""
const fs = require("fs");
global.window = {};
const src = fs.readFileSync(process.argv[1], "utf8");
const { methods } = new Function(src + "\nreturn { methods: window.AQB_QB_TRAFFIC.methods };")();
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);
let rafId = 0;
const rafMap = new Map();
global.requestAnimationFrame = (cb) => { rafMap.set(++rafId, cb); return rafId; };
global.cancelAnimationFrame = (id) => { rafMap.delete(id); };
let nowMs = 0;
Object.defineProperty(global, "performance", { value: { now: () => nowMs }, configurable: true });
global.document = { hidden: false };
function mkU(xs, up, dl) {
  const u = {
    root: { isConnected: true },
    data: [xs, up, dl],
    scales: { x: { min: xs[0], max: xs[xs.length - 1] }, y: { min: 0, max: 1 } },
    bbox: { left: 60, top: 10, width: 800, height: 300 },
    yCap: 0,
    pending: {},
    setScaleLog: [], setDataCount: 0, redrawCount: 0, destroyed: false,
    setScale(k, r) {
      this.pending[k] = { min: r.min, max: r.max };
      this.setScaleLog.push([k, r.min, r.max]);
    },
    setData(d) {
      this.data = d;
      this.setDataCount++;
      this.pending = { x: { min: d[0][0], max: d[0][d[0].length - 1] } };
      this.commit();
    },
    redraw() {
      this.redrawCount++;
      this.pending.x = { min: this.scales.x.min, max: this.scales.x.max };
      this.commit();
    },
    valToPos(v, k) {
      const s = this.scales[k];
      return k === "x" ? ((v - s.min) / (s.max - s.min)) * 800 : (1 - (v - s.min) / (s.max - s.min)) * 300;
    },
    commit() {
      const px = this.pending.x;
      const py = this.pending.y;
      this.pending = {};
      if (!px) {
        if (py) this.scales.y = { min: py.min, max: py.max };
        return;
      }
      const xs = this.data[0];
      let lo = 0;
      let hi = xs.length - 1;
      while (lo < hi && xs[lo] < px.min) lo++;
      while (hi > lo && xs[hi] > px.max) hi--;
      if (py) {
        this.scales.y = { min: py.min, max: py.max };
      } else {
        let dmax = 0;
        for (const col of [this.data[1], this.data[2]]) {
          for (let i = lo; i <= hi; i++) {
            const v = col[i];
            if (v != null && v > dmax) dmax = v;
          }
        }
        const top = dmax > 0 ? dmax * 1.05 : 1;
        this.scales.y = { min: 0, max: this.yCap > 0 ? Math.max(this.yCap, top) : top };
      }
      this.scales.x = { min: px.min, max: px.max };
    },
    destroy() { this.destroyed = true; },
  };
  return u;
}
function mkBeat(xs0, n, upShown, dlShown) {
  return {
    raf: 0, anim: null, xs0, n,
    tracks: {
      up: { prev: upShown, target: upShown, shown: upShown, delta: 0, level: 0, live: true },
      dl: { prev: dlShown, target: dlShown, shown: dlShown, delta: 0, level: 0, live: true },
    },
  };
}
const self = Object.assign({}, methods, { _qbPollMs: () => 3000, _qbCharts: {} });
/* tail=false 基准配置(次区相位单独在 F5/F6 开): period 3s -> beat 1000 / impact 120 / animEnd 600 */
const CFG = { enabled: true, on: true, shiftRatio: 0.6, neon: true, particles: 1, tail: false,
  dual: "both", palette: "neon", layers: { band: true, particles: true, scan: true, grade: true } };
global.window.AQB_FX_CFG = CFG;
const XS1 = [1030, 1060, 1090, 1120, 1150];
const pump = () => {
  const fns = [...rafMap.values()];
  rafMap.clear();
  fns.forEach((f) => f());
  const cu = self._qbCharts.global;
  if (cu && cu.commit) cu.commit();
};
const drain = () => { let g = 0; while (rafMap.size && g++ < 200) { nowMs += 50; pump(); } return g; };
// —— F1a: 正常拍(双轨活性, both 默认) ——
{
  const u = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1000, 5, 10, 55);
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  const fx = u._qbBeat.anim && u._qbBeat.anim.fx;
  ok("F1a 判定帧起 fx(phase=impact) + lead=up Lv.3", u._qbBeat.anim && u._qbBeat.anim.phase === "impact"
    && fx && fx.lead === "up" && fx.lv === 3);
  ok("F1a both 分配: cap 32 -> 16/16, 清单各 16(两轨合计不翻倍 —— I9)",
    fx && fx.cap === 32 && fx.alloc.up === 16 && fx.alloc.dl === 16
    && fx.specs.up.length === 16 && fx.specs.dl.length === 16);
  ok("F1a 两轨皆活性(次区资格双轨) + y 间距 214px>26 gapScale 1",
    fx && fx.act.up && fx.act.dl && fx.tail.length === 2 && fx.gapScale === 1);
  ok("F1a 粒子原点 = t=0 显示末点像素位(yOf(prev) 对钉档 yMax=63)",
    fx && Math.abs(fx.specs.up[0].y0 - (10 + 300 * (1 - 10 / 63))) <= 1e-9);
  drain();
  ok("F1a 收敛落地 + tail=false 无次区相位", u.data[1][4] === 30 && u._qbBeat.anim === null);
}
// —— F1b: enabled=false(on=false): L0/L1 照常但 fx null ——
{
  global.window.AQB_FX_CFG = Object.assign({}, CFG, { enabled: false, on: false });
  const u = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1000, 5, 10, 55);
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  ok("F1b enabled=false: 起拍照常但 fx null(装饰零绘制, §05.6)", rafMap.size === 1
    && u._qbBeat.anim && u._qbBeat.anim.fx === null);
  drain();
  ok("F1b 收敛落地", u.data[1][4] === 30 && u._qbBeat.anim === null);
  global.window.AQB_FX_CFG = CFG;
}
// —— F1c: reduce(on=false, enabled=true): 无 anim 即无装饰(V 全关, I7) ——
{
  global.window.AQB_FX_CFG = Object.assign({}, CFG, { on: false });
  const u = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1000, 5, 10, 55);
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  ok("F1c reduce 短路: 零 rAF 零 anim(退回快路)", rafMap.size === 0 && u._qbBeat.anim === null);
  global.window.AQB_FX_CFG = CFG;
}
// —— F1d: 缺口轨(dl null): lead 单轨, 另一轨零反馈(D4/I10) ——
{
  const u = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, null]);
  u._qbBeat = mkBeat(1000, 5, 10, 55);
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  const fx = u._qbBeat.anim && u._qbBeat.anim.fx;
  ok("F1d 缺口轨: lead=up, dl 零反馈(act false), 次区资格只 up",
    fx && fx.lead === "up" && fx.act.up === true && fx.act.dl === false
    && fx.tail.length === 1 && fx.tail[0] === "up");
  ok("F1d 单轨活性不套 D4 缩小(gapScale 1)", fx && fx.gapScale === 1);
  drain();
  ok("F1d 收敛落地(dl 保持 null)", u.data[1][4] === 30 && u.data[2][4] === null && u._qbBeat.anim === null);
}
// —— F2: D3 三策略落 fx 清单 ——
{
  global.window.AQB_FX_CFG = Object.assign({}, CFG, { dual: "lead" });
  const u = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1000, 5, 10, 55);
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  let fx = u._qbBeat.anim.fx;
  ok("F2 lead 策略: 主导轨全套 32, 从属零清单", fx && fx.alloc.up === 32 && fx.alloc.dl === 0
    && fx.specs.up.length === 32 && fx.specs.dl === undefined);
  drain();
  global.window.AQB_FX_CFG = Object.assign({}, CFG, { dual: "merge" });
  const u2 = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u2._qbBeat = mkBeat(1000, 5, 10, 55);
  self._qbCharts = { global: u2 };
  self._qbBeatStart("global", u2);
  fx = u2._qbBeat.anim.fx;
  ok("F2 merge 策略: 中点一次 merge=32(原点 y = 两轨 y 中点), 双轨零清单",
    fx && fx.alloc.merge === 32 && fx.alloc.up === 0 && fx.specs.merge.length === 32
    && fx.specs.up === undefined
    && Math.abs(fx.specs.merge[0].y0 - (10 + 300 * (1 - ((10 + 55) / 2) / 63))) <= 1e-9);
  drain();
  global.window.AQB_FX_CFG = CFG;
}
// —— F3: D4 末点 y 间距缩小(实测) ——
{
  const u = mkU(XS1, [0, 0, 0, 0, 32.73], [0, 0, 0, 0, 35]);
  u._qbBeat = mkBeat(1000, 5, 30, 32.73);
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  const fx = u._qbBeat.anim.fx;
  const yMax = 35 * 1.05;
  const yUp = 10 + 300 * (1 - 30 / yMax);
  const yDl = 10 + 300 * (1 - 32.73 / yMax);
  const exp = Math.max(0.4, Math.min(1, Math.abs(yUp - yDl) / 26));
  ok("F3 D4: y 间距 <26px 反馈按比例缩小(与 _qbFxGapScale 同式现算, 两轨各自保留)",
    fx && Math.abs(fx.gapScale - exp) <= 1e-9 && fx.gapScale < 1 && fx.act.up && fx.act.dl);
  drain();
}
// —— F4: 装饰帧保障(无 shift 长窗 impact 窗零提交帧强制重绘) ——
{
  const xs = Array.from({ length: 2880 }, (_, i) => 1000 + i * 30);
  const up = new Array(2880).fill(0);
  up[2879] = 30;
  const dl = new Array(2880).fill(0);
  const u = mkU(xs, up, dl);
  u._qbBeat = mkBeat(970, 2880, 10, 0);
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  ok("F4 前置: 无 shift 长窗起拍(零 setScale) + fx 在", u.setScaleLog.length === 0
    && u._qbBeat.anim && !!u._qbBeat.anim.fx);
  for (let i = 0; i < 2; i++) { nowMs += 50; pump(); }   // clock 0/50: impact 窗(120)内尾点冻结
  ok("F4 装饰帧保障: impact 窗内 L0/L1 零提交帧强制重绘(粒子不冻结在 t=0) + y 钉成对 31.5",
    u.redrawCount === 2 && u.setScaleLog.length === 2
    && u.setScaleLog.every((r) => r[0] === "y" && r[2] === 31.5));
  drain();
  ok("F4 收敛落地(cfg.tail=false 无次区)", u.data[1][2879] === 30 && u._qbBeat.anim === null);
}
// —— F5: 次区相位全生命周期(衔接/光点/节流/收尾) ——
{
  global.window.AQB_FX_CFG = Object.assign({}, CFG, { tail: true });
  const xs = Array.from({ length: 2880 }, (_, i) => 1000 + i * 30);
  const up = new Array(2880).fill(0);
  up[2879] = 30;
  const dl = new Array(2880).fill(0);
  dl[2879] = 20;
  const u = mkU(xs, up, dl);
  u._qbBeat = mkBeat(970, 2880, 10, 5);
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  for (let i = 0; i < 13; i++) { nowMs += 50; pump(); }   // clock 600: 收敛帧
  ok("F5 收敛帧转次区相位(tail=true + 双轨活性) + 真值已落袋", u._qbBeat.anim
    && u._qbBeat.anim.phase === "tail" && u.data[1][2879] === 30 && u.data[2][2879] === 20);
  const seen = { pts: 0, skips: 0, lastRedraw: u.redrawCount, bad: false };
  let guard = 0;
  while (rafMap.size && guard++ < 200) {
    nowMs += 50;
    pump();
    const a = u._qbBeat.anim;
    if (a && a.phase === "tail" && a.fxTail.pts && a.fxTail.pts.length) {
      if (a.fxTail.pts.length > seen.pts) seen.pts = a.fxTail.pts.length;
      if (u.redrawCount === seen.lastRedraw) seen.skips++;
      seen.lastRedraw = u.redrawCount;
      for (const pt of a.fxTail.pts) {
        if (!(pt.alpha > 0 && pt.alpha <= 0.35)) seen.bad = true;
        if (!(pt.x >= 60 && pt.x <= 860 && pt.y >= 10 && pt.y <= 310)) seen.bad = true;
      }
    }
  }
  ok("F5 次区光点: <=2/轨 合计 <=4, alpha <=0.35, 位置在绘图区内(极轻 —— I9/G2)",
    seen.pts > 0 && seen.pts <= 4 && !seen.bad);
  ok("F5 1px 量化节流: 位置无可见变化的帧不提交(长窗光点每帧位移 <1px —— I9 R8 帧成本)",
    seen.skips > 3);
  ok("F5 次区收尾: 窗尽 anim null(下一拍前静默, tail=min(period-beat,2000) 非常驻)",
    u._qbBeat.anim === null && rafMap.size === 0);
  global.window.AQB_FX_CFG = CFG;
}
// —— F6: 拍内关 tail: 下一帧收尾 ——
{
  global.window.AQB_FX_CFG = Object.assign({}, CFG, { tail: true });
  const u = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1000, 5, 10, 55);
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  for (let i = 0; i < 13; i++) { nowMs += 50; pump(); }
  ok("F6 前置: 次区相位已挂", u._qbBeat.anim && u._qbBeat.anim.phase === "tail");
  global.window.AQB_FX_CFG = CFG;   // tail 回 false(拍内改参, 下一帧生效)
  nowMs += 50;
  pump();
  ok("F6 拍内关 tail: 下一帧收尾(anim null + 清理提交)", u._qbBeat.anim === null);
  global.window.AQB_FX_CFG = CFG;
}
// —— F7: merge + 缺口轨(评审修复2): 落位退 lead 末点 y, 不发「与底边的假中点」——
//    缺口轨 shown=null 会被 yOf 换算成绘图区底边 T+H, 中点成了与真实末点无关的假落位(I10/D4) ——
{
  global.window.AQB_FX_CFG = Object.assign({}, CFG, { dual: "merge" });
  const u = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, null]);
  u._qbBeat = mkBeat(1000, 5, 10, 55);
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  const fx = u._qbBeat.anim && u._qbBeat.anim.fx;
  const yMax = 31.5;   // dl 缺口 -> 全窗真值峰 30 x1.05
  const yMerge = 10 + 300 * (1 - 10 / yMax);   // yOf(up.shown=10)
  ok("F7 merge+缺口轨: specs.merge[0].y0 === yOf(lead.shown)(假中点 = (yMerge+310)/2 即红)",
    fx && fx.specs.merge && fx.specs.merge.length === 32
    && Math.abs(fx.specs.merge[0].y0 - yMerge) <= 1e-9
    && Math.abs(fx.specs.merge[0].y0 - (yMerge + 310) / 2) > 1);
  ok("F7 切片锚带中心同退 lead 末点 y(±14px 带内) + 清单无条件生成(palette=neon 也有 —— 修复4)",
    fx && fx.slices && fx.slices.length === 5
    && fx.slices.every((s) => Math.abs(s.y - yMerge) <= 14 + 1e-9));
  drain();
  global.window.AQB_FX_CFG = CFG;
}
// —— F8: 密度解耦(评审修复3): spawn 满额清单(= partCap(lv,1)), 与拍内 cfg.particles 无关 ——
//    密度/dual 拍内改参由绘制侧逐帧重算 + 钳制生效, cap 冻结会让改密度整拍失效(违 §05.3/D21) ——
{
  global.window.AQB_FX_CFG = Object.assign({}, CFG, { particles: 0.4 });
  const u = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1000, 5, 10, 55);
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  const fx = u._qbBeat.anim && u._qbBeat.anim.fx;
  ok("F8 密度 0.4 仍满额清单 16/16(cap 32 = partCap(lv,1), 清单长度与密度解耦)",
    fx && fx.cap === 32 && fx.specs.up.length === 16 && fx.specs.dl.length === 16);
  drain();
  global.window.AQB_FX_CFG = CFG;
}
console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
"""

# 视觉引擎绘制面 node 电池(S2-a 评审修复 2/3/4/6/7): 真 mixin 方法 + 记账式 2d ctx 桩(记录
# shadowBlur 赋值/带 blur 的 stroke/路径落笔 ops/fill/fillRect)直接调 _qbDrawFx/_qbDrawFxAnchor ——
# blur 预算(同帧带 blur stroke <= spots 数/帧末清零/calm 恒不赋非零)、neon=false 零白名单元素落笔、
# 密度拍内即时、切片 palette 逐帧门、draw 侧 merge+缺口轨落位、lead 加亮缺口不桥接。
# 无 node 静默跳过(同 _NODE_QB_TRAFFIC_PROBE 口径)。
_NODE_QB_FXVIS_DRAW_PROBE = r"""
const fs = require("fs");
global.window = {};
const src = fs.readFileSync(process.argv[1], "utf8");
const { methods, _qbFxSpawnSpecs, _qbFxSlices, _qbFxRingAt } =
  new Function(src + "\nreturn { methods: window.AQB_QB_TRAFFIC.methods,"
  + " _qbFxSpawnSpecs, _qbFxSlices, _qbFxRingAt };")();
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);
/* 记账式 2d ctx: 只记不画。shadowBlur 用 getter/setter 截获每次赋值(含清零), stroke 时若
 * _blur > 0 记一次「带 blur 的 stroke」(I9 同帧 <=3 次预算的观测面), ops 记路径点(M/L)。 */
function mkCtx() {
  const ctx = {
    blurSets: [], strokeVals: [], fillRects: [], fillTexts: [], ops: [],
    strokesWhileBlur: 0, fillCnt: 0,
    _blur: 0, shadowColor: "", globalAlpha: 1,
    strokeStyle: "", fillStyle: "", lineWidth: 1, font: "", textAlign: "", textBaseline: "",
    beginPath() {}, closePath() {}, rect() {}, clip() {}, arc() {},
    scale() {}, save() {}, restore() {}, setLineDash() {},
    moveTo(x, y) { this.ops.push([x, y, "M"]); },
    lineTo(x, y) { this.ops.push([x, y, "L"]); },
    stroke() { if (this._blur > 0) this.strokesWhileBlur++; this.strokeVals.push(this.strokeStyle); },
    fill() { this.fillCnt++; },
    fillRect(x, y, w, h) { this.fillRects.push([x, y, w, h]); },
    fillText(s) { this.fillTexts.push(String(s)); },
  };
  Object.defineProperty(ctx, "shadowBlur", {
    get() { return ctx._blur; },
    set(v) { ctx._blur = v; ctx.blurSets.push(v); },
    configurable: true,
  });
  return ctx;
}
const YMAX = 63;
const yOfT = (v) => 10 + 300 * (1 - Math.min(v, YMAX) / YMAX);
function mkDrawU(up, dl) {
  const xs = [1030, 1060, 1090, 1120, 1150];
  const u = {
    root: { isConnected: true },
    data: [xs, up, dl],
    scales: { x: { min: xs[0], max: xs[4] }, y: { min: 0, max: YMAX } },
    bbox: { left: 60, top: 10, width: 800, height: 300 },
    valToPos(v, k) {
      const s = this.scales[k];
      return k === "x" ? ((v - s.min) / (s.max - s.min)) * 800 : (1 - (v - s.min) / (s.max - s.min)) * 300;
    },
  };
  u.ctx = mkCtx();
  return u;
}
const LIVE_UP = { prev: 10, target: 30, shown: 10, delta: 2, level: 3, live: true };
const LIVE_DL = { prev: 55, target: 60, shown: 55, delta: 0.09, level: 2, live: true };
const GAP_DL = { prev: null, target: null, shown: null, delta: 0, level: 0, live: false };
function mkBeatSt(up, dl) {
  return { raf: 0, anim: null, xs0: 1030, n: 5, tracks: { up: up, dl: dl } };
}
function mkAnim(fx, over) {
  return Object.assign({ dx0: 0, needsShift: false, needsTail: false, n: 5,
    tl: { beat: 1000, impactMs: 120, shiftMs: 600, convergeMs: 480, animEndMs: 600, tailMs: 0 },
    yMax: YMAX, clock: 100, lastT: 0, lastDx: null, fx: fx, phase: "impact" }, over || {});
}
function mkFx(over) {
  return Object.assign({
    lead: "up", lv: 3, gapScale: 1, rMax: 29, cap: 32,
    alloc: { up: 16, dl: 16, merge: 0 },
    specs: { up: _qbFxSpawnSpecs(16, 860, yOfT(10), 29, 11), dl: _qbFxSpawnSpecs(16, 860, yOfT(55), 29, 12) },
    slices: _qbFxSlices(5, yOfT(10), 13),
    tail: ["up", "dl"],
    act: { up: true, dl: true },
    pxPerT: 0.5, dx0: 0, beatMs: 1000, burstMs: 120,
  }, over || {});
}
const TK = { up: "#UP", down: "#DN", grid: "#GRID", gap: "#GAP", axis: "#AXIS" };
const CFG0 = { enabled: true, on: true, shiftRatio: 0.6, neon: true, particles: 1, tail: false,
  dual: "both", palette: "neon", layers: { band: true, particles: true, scan: true, grade: true } };
global.window.AQB_FX_CFG = CFG0;
const draw = (u) => methods._qbDrawFx.call(methods, u, TK);
const drawAnchor = (u) => methods._qbDrawFxAnchor.call(methods, u, TK);
const at = (u, t) => { u._qbBeat.anim.clock = t; draw(u); };
// —— G1/G2: blur 预算(修复7): 同帧带 blur 的 stroke <= spots 数(<=2), 帧末 shadowBlur 恒清 0 ——
{
  const u = mkDrawU([0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeatSt(LIVE_UP, LIVE_DL);
  u._qbBeat.anim = mkAnim(mkFx());
  at(u, 100);   // 环扩张中 + neon 窗内: 辉光块必经
  ok("G1 blur 预算: 非零赋值恰 1 个施加点 + 带 blur 的 stroke 恰 = spots 数(both 双活性轨 = 2)",
    u.ctx.blurSets.filter((v) => v > 0).length === 1 && u.ctx.strokesWhileBlur === 2);
  ok("G1 帧末态: shadowBlur 用后即清 0(末次赋值 = 0)",
    u.ctx.shadowBlur === 0 && u.ctx.blurSets[u.ctx.blurSets.length - 1] === 0);
}
{
  let endOk = true;
  let budgetOk = true;
  for (const t of [0, 50, 100, 200, 300, 400, 500]) {
    const u = mkDrawU([0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
    u._qbBeat = mkBeatSt(LIVE_UP, LIVE_DL);
    u._qbBeat.anim = mkAnim(mkFx(), { clock: t });
    draw(u);
    if (u.ctx.shadowBlur !== 0) endOk = false;
    if (u.ctx.strokesWhileBlur > 2 || u.ctx.blurSets.filter((v) => v > 0).length > 1) budgetOk = false;
  }
  ok("G2 逐帧扫 t=0..500: 帧末 shadowBlur 恒 0 + 带 blur stroke <=2 + 非零赋值点 <=1(每帧)",
    endOk && budgetOk);
}
// —— G3: palette=calm 恒不赋非零 blur(V1 上限 calm=0) ——
{
  let calmOk = true;
  global.window.AQB_FX_CFG = Object.assign({}, CFG0, { palette: "calm" });
  for (const t of [50, 100, 200, 300]) {
    const u = mkDrawU([0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
    u._qbBeat = mkBeatSt(LIVE_UP, LIVE_DL);
    u._qbBeat.anim = mkAnim(mkFx(), { clock: t });
    draw(u);
    if (!u.ctx.blurSets.every((v) => v === 0)) calmOk = false;
  }
  global.window.AQB_FX_CFG = CFG0;
  ok("G3 palette=calm: shadowBlur 赋值恒 0(恒不赋非零)", calmOk);
}
// —— G4: cfg.neon=false 零白名单元素落笔(judgeFlash/ringOuter/partOuter/anchorHalo/lvBadge) ——
{
  global.window.AQB_FX_CFG = Object.assign({}, CFG0, { neon: false });
  const lv = "#FF6BD6";   // Lv.3
  const u = mkDrawU([0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeatSt(LIVE_UP, LIVE_DL);
  u._qbBeat.anim = mkAnim(mkFx());
  draw(u);
  ok("G4 neon=false: 零 lvBadge(fillText)/零环外圈辉光(shadowBlur)/零 Lv 色描边",
    u.ctx.fillTexts.length === 0 && u.ctx.blurSets.every((v) => v === 0)
    && u.ctx.strokeVals.every((s) => s !== lv));
  // 锚段同验(dual=lead 让从属轨语义色加亮照画, 只有白名单 anchorHalo 不落笔)
  global.window.AQB_FX_CFG = Object.assign({}, CFG0, { neon: false, dual: "lead" });
  const u2 = mkDrawU([0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u2._qbBeat = mkBeatSt(LIVE_UP, LIVE_DL);
  u2._qbBeat.anim = mkAnim(mkFx({ lead: "up", alloc: { up: 32, dl: 0, merge: 0 },
    specs: { up: _qbFxSpawnSpecs(32, 860, yOfT(10), 29, 14) } }));
  drawAnchor(u2);
  ok("G4 锚段 neon=false: 语义色加亮照画 + 零 Lv 色描边(anchorHalo 不落笔)",
    u2.ctx.strokeVals.every((s) => s !== lv) && u2.ctx.fillTexts.length === 0);
  global.window.AQB_FX_CFG = CFG0;
}
// —— G5: lead 从属轨加亮跨缺口不桥接(修复6): null 处断段重新 moveTo, 与 spanGaps:false 一致 ——
{
  global.window.AQB_FX_CFG = Object.assign({}, CFG0, { dual: "lead" });
  const fxLead = mkFx({ lead: "up", alloc: { up: 32, dl: 0, merge: 0 },
    specs: { up: _qbFxSpawnSpecs(32, 860, yOfT(10), 29, 14) } });
  const u = mkDrawU([0, 0, 0, 0, 30], [null, null, 20, null, 25]);
  u._qbBeat = mkBeatSt(LIVE_UP, LIVE_DL);
  u._qbBeat.anim = mkAnim(fxLead);
  drawAnchor(u);
  const hi = [yOfT(20), yOfT(25)];   // 加亮段只落这两桶(末 3 桶窗)
  const seg = u.ctx.ops.filter((o) => hi.some((y) => Math.abs(o[1] - y) < 1e-6));
  ok("G5 加亮缺口 [20,null,25]: moveTo+moveTo 零 lineTo 桥接(gap 后重新起笔)",
    seg.length === 2 && seg.every((o) => o[2] === "M"));
  const u2 = mkDrawU([0, 0, 0, 0, 30], [null, null, 20, 22, 25]);
  u2._qbBeat = mkBeatSt(LIVE_UP, LIVE_DL);
  u2._qbBeat.anim = mkAnim(fxLead);
  drawAnchor(u2);
  const hi2 = [yOfT(20), yOfT(22), yOfT(25)];
  const seg2 = u2.ctx.ops.filter((o) => hi2.some((y) => Math.abs(o[1] - y) < 1e-6));
  ok("G5 对照连续 [20,22,25]: moveTo + lineTo x2(逐段描边原样)",
    seg2.length === 3 && seg2[0][2] === "M" && seg2[1][2] === "L" && seg2[2][2] === "L");
  global.window.AQB_FX_CFG = CFG0;
}
// —— G6: 密度拍内即时(修复3): 逐帧 partCap 现算, 拍内改 cfg.particles 下一帧粒子数即变 ——
{
  const u = mkDrawU([0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeatSt(LIVE_UP, LIVE_DL);
  u._qbBeat.anim = mkAnim(mkFx());   // 满额清单 16/16
  global.window.AQB_FX_CFG = Object.assign({}, CFG0, { particles: 0.4 });
  at(u, 100);
  const low = u.ctx.fillCnt;   // round(32x0.4)=13 -> both 7+6
  u.ctx = mkCtx();
  global.window.AQB_FX_CFG = Object.assign({}, CFG0, { particles: 1 });
  at(u, 100);
  const full = u.ctx.fillCnt;   // 满额清单 16+16 = 32(不再被 spawn cap 冻结)
  u.ctx = mkCtx();
  global.window.AQB_FX_CFG = Object.assign({}, CFG0, { particles: 0.1 });
  at(u, 100);
  const lower = u.ctx.fillCnt;   // round(3.2)=3 -> both 2+1
  global.window.AQB_FX_CFG = CFG0;
  ok("G6 密度即时: 同拍内 0.4 -> 13 粒 / 1 -> 32 粒 / 0.1 -> 3 粒(下一帧生效)",
    low === 13 && full === 32 && lower === 3);
}
// —— G7: 切片 palette 逐帧门(修复4): neon 零切片, 拍内切 glitch 下一帧即画(清单已在) ——
{
  const u = mkDrawU([0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeatSt(LIVE_UP, LIVE_DL);
  u._qbBeat.anim = mkAnim(mkFx());
  at(u, 100);
  ok("G7 palette=neon: 零切片 fillRect(绘制门逐帧复核)", u.ctx.fillRects.length === 0);
  u.ctx = mkCtx();
  global.window.AQB_FX_CFG = Object.assign({}, CFG0, { palette: "glitch" });
  at(u, 100);
  ok("G7 拍内切 glitch: 下一帧即画 5 条 1px 级切片(切入口整拍无切片回潮即红)",
    u.ctx.fillRects.length === 5 && u.ctx.fillRects.every((r) => r[3] === 1));
  global.window.AQB_FX_CFG = CFG0;
}
// —— G8: draw 侧 merge + 缺口轨(修复2): 环心 = yOf(lead.shown), 非与底边的假中点 ——
//    观测面 = 环/辉光八边形在 x=tipX 处的一对顶点(90°/270°), y = 环心 ± r, 四点均值即环心 ——
{
  global.window.AQB_FX_CFG = Object.assign({}, CFG0, { dual: "merge" });
  const u = mkDrawU([0, 0, 0, 0, 30], [0, 0, 0, 0, null]);
  u._qbBeat = mkBeatSt(LIVE_UP, GAP_DL);
  u._qbBeat.anim = mkAnim(mkFx({ alloc: { up: 0, dl: 0, merge: 32 },
    specs: { merge: _qbFxSpawnSpecs(32, 860, yOfT(10), 29, 15) }, act: { up: true, dl: false } }));
  at(u, 100);
  const r = _qbFxRingAt(100, 1000, 29).r;
  const ys = u.ctx.ops.filter((o) => Math.abs(o[0] - 860) < 1e-6).map((o) => o[1]);
  const avg = ys.reduce((a, b) => a + b, 0) / ys.length;
  ok("G8 draw merge+缺口: 环心 = yOf(lead.shown)(假中点 = (yOf+310)/2 即红 —— I10/D4)",
    ys.length === 4 && Math.abs(avg - yOfT(10)) <= 1e-6 && Math.abs(avg - (yOfT(10) + 310) / 2) > 1);
  const u2 = mkDrawU([0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u2._qbBeat = mkBeatSt(LIVE_UP, LIVE_DL);
  u2._qbBeat.anim = mkAnim(mkFx({ alloc: { up: 0, dl: 0, merge: 32 },
    specs: { merge: _qbFxSpawnSpecs(32, 860, (yOfT(10) + yOfT(55)) / 2, 29, 15) } }));
  u2.ctx = mkCtx();
  at(u2, 100);
  const ys2 = u2.ctx.ops.filter((o) => Math.abs(o[0] - 860) < 1e-6).map((o) => o[1]);
  const avg2 = ys2.reduce((a, b) => a + b, 0) / ys2.length;
  ok("G8 对照双轨 live: 环心 = (yUp+yDl)/2 中点(D3-c)", ys2.length === 4
    && Math.abs(avg2 - (yOfT(10) + yOfT(55)) / 2) <= 1e-6);
  global.window.AQB_FX_CFG = CFG0;
}
console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
"""


def test_frontend_qb_fx_visual_engine_battery():
    """视觉引擎 V + N 层 S2-a 电池 + 接缝静态钉(plan 26-11-12-1139 §03 V 表/N 节/D1-D4, §06 S2 行)

    行为面(node 电池, 无 node 静默跳过, 同节拍内核口径):
    1. I6 图层顺序常量逐字 + 序断言(geometry/neon 恒在 curve 之前, anchor 之后);
    2. I11 N 层白名单五元素/黑名单八元素逐字且零交集;
    3. V1 Lv 色表逐字(#7AD9FF/#FEFFA9/#FF6BD6) + 三档配色 blur 上限(10/14/0) + V2 环边数(3/6/8);
    4. I9 预算常量(32/16/0.33/0.55/26/5/3px/2/6 桶, 全部两轨合计口径);
    5. D3 lead 仲裁(argmax 优先非缺口非静默/双轨静默 null/恰等取 up);
    6. partCap(等级基数 16/24/32 x 密度 clamp 32, 密度 <=0 零粒子);
    7. D3 三策略分配(both 对半各 <=16 合计守恒全域扫/lead 全套从属零/merge 中点一次/未知回落 both);
    8. D4 y 间距缩小(线性 /26 下限 0.4, 不合并不取消);
    9. N 回落 0.33×beat + 冲击环(easeOut 扩张/alpha 回落/0.55×beat 后 null);
    10. V3 粒子三阶段(爆发 x4.5 闭式/拖尾 easeOut 减速/末态恰 dist/t=0 alpha=1 与判定线闪光
        同帧/carryPx 随 L0 末点滑动) + 喷射清单(三/四/五边/同种子恒同/左向 270° 弧/尺寸行程界);
    11. glitch 切片(<=5/|dy0|<=3/同种子恒同) + 伪随机确定性;
    12. 调度器 fx 面: fx 生成门(on=false fx null 但 L0/L1 照常/reduce 无 anim/缺口轨 lead 单轨/
        D4 实测缩小)/三策略落 fx 清单/装饰帧保障(impact 窗强制重绘 + y 钉成对)/次区相位全生命周期
        (衔接/光点 <=4 alpha<=0.35 位置在绘图区/1px 量化节流/窗尽收尾/拍内关 tail 下一帧收尾)
        + merge+缺口轨落位退 lead 末点 y(F7, specs.merge[0].y0 === yOf(lead.shown), 假中点即红
        —— 评审修复2; 切片锚带中心同退且清单无条件生成)/spawn 满额清单与密度解耦(F8, 密度 0.4
        仍 16/16 —— 评审修复3);
    13. 绘制面 ctx 桩电池(G1-G8, 记账式 2d context 真 _qbDrawFx/_qbDrawFxAnchor): blur 预算
        (非零赋值恰 1 施加点/带 blur stroke = spots 数 <=2/逐帧扫帧末 shadowBlur 恒 0/palette=calm
        恒不赋非零 —— 评审修复7)/neon=false 零白名单元素落笔(fillText/shadowBlur/Lv 色描边, 锚段
        同验)/密度拍内即时(0.4->13/1->32/0.1->3 粒)/切片 palette 逐帧门(neon 零切片, 拍内切
        glitch 下一帧即画 5 条 1px 级)/draw 侧 merge+缺口轨环心 = yOf(lead.shown)(x=tipX 顶点
        四点均值观测, 假中点即红)/lead 加亮跨缺口重新 moveTo 不桥接([20,null,25] vs [20,22,25]
        对照)。
    接缝面(静态钉):
    a. I6/I11/V1/I9 常量行逐字(单点漂移即红);
    b. 钩子注册序 = 层序(vendor 1.6.32 源实证: 主渲染序 clearRect -> drawClear -> Pl.forEach
       [axes -> series] -> draw, Ci("drawAxes") 在 Dl.axes 末尾 = 网格后、系列前 —— drawClear:
       斜纹恒最底; drawAxes: fx(挂 drawClear 会被网格盖住违 I6); draw: 限速 -> 锚; 曲线描边 =
       uPlot 系列原生);
    c. 背景零铺色(I11/G7): fx 绘制域剥注释后 fillRect 恰 1 处且为切片 1px 级(高度字面量 1),
       锚段/次区段零 fillRect;
    d. I11 黑名单: fx 三域零触碰 legend/cursor/series(黑名单元素恒静态基线);
    e. I3 反向钉: fx 四域(spawn/fx 装饰段/锚段/次区段)零 destroy/new uPlot/零 loading;
    f. 生效条件门: spawn 与 fx 装饰段(drawAxes)逐帧复核 cfg.on(拍内改参下一帧生效), 次区帧复核
       cfg.tail;
    g. 收敛帧次区衔接(phase: "tail" + fxTail + cfg.tail === true 门);
    h. 装饰帧保障行(impact 窗零提交帧强制重绘)与次区相位分支在 _qbBeatFrame(装饰帧挂调度器
       循环内, 无独立循环)。"""
    shared = os.path.join(STATIC_ROOT, "shared")
    js = open(os.path.join(shared, "qb_traffic_chart.js"), encoding="utf-8").read()
    # —— a. 常量单点逐字 ——
    assert '_QB_FX_LAYER_ORDER = ["bg", "grid", "geometry", "neon", "curve", "anchor", "hud"]' in js, \
        "缺/漂移 I6 图层顺序常量(违反即判失败的单点)"
    assert '_QB_FX_N_WHITELIST = ["judgeFlash", "ringOuter", "partOuter", "anchorHalo", "lvBadge"]' in js, \
        "缺/漂移 I11 N 层白名单"
    assert '_QB_FX_N_BLACKLIST = ["curveUp", "curveDl", "plotBg", "edgeBg", "grid", "tooltip", "legend", "limitDash"]' in js, \
        "缺/漂移 I11 N 层黑名单"
    assert '_QB_FX_LV_COLORS = { 1: "#7AD9FF", 2: "#FEFFA9", 3: "#FF6BD6" }' in js, \
        "缺/漂移 V1 Lv 色表(plan §03 V1 行逐字)"
    assert "_QB_FX_BLUR_CAPS = { neon: 10, glitch: 14, calm: 0 }" in js, \
        "缺/漂移 V1 三档配色 blur 上限"
    assert "_QB_FX_RING_SIDES = { 1: 3, 2: 6, 3: 8 }" in js, "缺/漂移 V2 环边数映射"
    for line in (
        "_QB_FX_PART_MAX = 32;", "_QB_FX_SHARD_MAX = 16;", "_QB_FX_NEON_RATIO = 0.33;", "_QB_FX_PART_RATIO = 0.55;",
        "_QB_FX_Y_GAP_PX = 26;"
    ):
        assert line in js, f"缺/漂移 I9 预算常量 {line}"
    # —— b. 钩子注册序 = I6 层序(vendor 1.6.32 源实证: 主渲染序 clearRect -> Ci("drawClear") ->
    #      Pl.forEach(axes -> series) -> Ci("draw"), 且 Ci("drawAxes") 在 Dl.axes 函数末尾 = 网格
    #      之后、系列之前 —— fx 挂 drawClear 会被网格盖住, 必须挂 drawAxes) ——
    assert "drawClear: [(u) => this._qbDrawGaps(u, tk)]" in js, \
        "drawClear 只挂缺口斜纹(恒最底, 与网格相互独立)"
    assert "drawAxes: [(u) => this._qbDrawFx(u, tk)]" in js, \
        "fx 装饰段必须挂 drawAxes(uPlot 网格之后、系列原生之前 —— 挂 drawClear 被网格盖住违 I6)"
    assert "draw: [(u) => this._qbDrawLimits(u, tk), (u) => this._qbDrawFxAnchor(u, tk)]" in js, \
        "draw 锚段必须紧跟限速虚线(层序: 曲线描边(系列原生) -> 末点菱形锚)"
    # —— c. 背景零铺色(I11/G7) ——
    fxb = re.search(r"_qbDrawFx\(u, tk\) \{\n(.*?)\n    \},", js, re.S)
    assert fxb, "缺 _qbDrawFx(drawClear 装饰段)"
    fxb_code = re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", fxb.group(1), flags=re.S))
    assert fxb_code.count("fillRect") == 1 and re.search(r"fillRect\([^;]*, 1\);", fxb_code), \
        "fx 装饰段 fillRect 必须 = glitch 切片 1px 级横条恰一处(整块铺底回潮即红 —— I11/G7)"
    anb = re.search(r"_qbDrawFxAnchor\(u, tk\) \{\n(.*?)\n    \},", js, re.S)
    assert anb, "缺 _qbDrawFxAnchor(draw 锚段)"
    tlb = re.search(r"_qbTailFrame\(u, a\) \{\n(.*?)\n    \},", js, re.S)
    assert tlb, "缺 _qbTailFrame(次区相位帧)"
    assert "fillRect" not in anb.group(1), "锚段不得有 fillRect(1px 级以外零铺底)"
    assert "fillRect" not in tlb.group(1), "次区光点域不得有 fillRect"
    # —— d. I11 黑名单: fx 三域零触碰图例/十字线/系列 ——
    for blk in (fxb.group(1), anb.group(1), tlb.group(1)):
        assert "legend" not in blk and "cursor" not in blk and "u.series" not in blk, \
            "fx 绘制域不得触碰图例/十字线/系列(黑名单元素恒静态基线 —— I11)"
    # —— e. I3 反向钉: fx 四域零销毁重建/零 loading ——
    spb = re.search(r"_qbFxSpawn\(u, tl, dx0, needsShift, yMax\) \{\n(.*?)\n    \},", js, re.S)
    assert spb, "缺 _qbFxSpawn(判定帧装饰状态生成单点)"
    for blk in (spb.group(1), fxb.group(1), anb.group(1), tlb.group(1)):
        assert "new uPlot" not in blk and "destroy(" not in blk and "loading" not in blk, \
            "fx 域不得 destroy/new uPlot/触碰 loading(I3 不闪; 装饰帧只经调度器提交)"
    # —— f. 生效条件门(逐帧复核) ——
    assert "cfg.on !== true" in spb.group(1), "spawn 缺 cfg.on 门(有效值单点 —— I7/§05.6)"
    assert "window.AQB_FX_CFG" in fxb.group(1) and "cfg.on !== true" in fxb.group(1), \
        "fx 装饰段(drawAxes)必须逐帧读 AQB_FX_CFG 并复核 on(拍内改参下一帧生效 —— §05.3)"
    assert "cfg.tail !== true" in tlb.group(1), "次区帧缺 cfg.tail 门(拍内关闭下一帧收尾)"
    # —— g. 收敛帧次区衔接 ——
    conv_blk = re.search(r"_qbBeatConverge\(scope, u\) \{\n(.*?)\n    \},", js, re.S)
    assert conv_blk and 'phase: "tail"' in conv_blk.group(1) and "fxTail" in conv_blk.group(1) \
        and "cfg.tail === true" in conv_blk.group(1), \
        "收敛帧缺次区相位衔接(tail 开启且有活性轨才挂, 非常驻)"
    # —— h. 装饰帧保障 + 次区分支挂调度器循环 ——
    frame_blk = re.search(r"_qbBeatFrame\(scope\) \{\n(.*?)\n    \},", js, re.S)
    assert frame_blk, "qb_traffic_chart.js 缺 _qbBeatFrame"
    assert (
        'if (a.fx && !dxChanged && !tailChanged && a.clock < a.fx.beatMs * _QB_FX_PART_RATIO) {' in frame_blk.group(1)
    ), "缺装饰帧保障(无 shift 长窗 impact 段零提交帧须强制重绘 —— I5)"
    assert 'if (a.phase === "tail") {' in frame_blk.group(1), \
        "缺次区相位分支(装饰帧必须挂调度器循环内, 无独立循环)"
    # —— 行为面 node 电池(纯函数面 + 调度器 fx 面各一发) ——
    node = shutil.which("node")
    if not node:
        return
    for probe, tag in (
        (_NODE_QB_FXVIS_PROBE, "视觉引擎纯函数"), (_NODE_QB_FXVIS_SCHED_PROBE, "视觉引擎调度器"),
        (_NODE_QB_FXVIS_DRAW_PROBE, "视觉引擎绘制面")
    ):
        proc = subprocess.run(
            [node, "-e", probe, os.path.join(shared, "qb_traffic_chart.js")],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        assert proc.returncode == 0, f"{tag} node 电池跑挂: {proc.stderr.strip()}"
        report = json.loads(proc.stdout.strip().splitlines()[-1])
        assert report["failed"] == [], \
            f"{tag}电池 {report['ok']}/{report['total']} 过, 失败: {report['failed']}"


def test_frontend_qb_fx_overlay_close_registry_and_reduced_motion():
    """数值面板收层七处登记 + IntersectionObserver 兜底 + reduced-motion 红线(R8 S0-b, plan 26-11-12-1139 §05.6/§05.7)

    非模态浮层的收层登记散在五个文件里, 任一处漏/被重构掉都是「面板浮死在页面上」的静默故障
    (遮住内容/跟随到别的图上), 前端无 JS 测试框架只能静态钉住:
    1. 七处登记(§05.7 表逐行): lifecycle 点空白名单(与 drawerMenu 同组) + Esc 退栈链(紧跟
      drawerMenu 之后 —— 面板比菜单"重"一层, 后开先关: 面板开着按 Esc 只关面板, 再按 Esc 才轮到
      抽屉) + dialogs_meta escBusy(两处同步 WARN 的另一处) + closeDrawer(面板不能比抽屉活得久)
      + drawerTab(切页签图宿主被替换) + drawer_store 换目标收口(与 drawerTab/closeDrawer 同口径;
      IO 只在宿主被真拆掉时兜底, 光靠 IO 会漏)。shortcuts_engine _kbOverlayBusy **末尾**追加项
      由 test_drawer_dock_keyboard_w2 钉住(书写序守阵在那边, 不在此重复); 面板根
      @keydown.esc="fxEsc" —— 面板可见才 stop+prevent+fxClose(焦点在面板控件内按 Esc 也只关
      面板, 一次 Esc 只关一层), 退场过渡期放行 Esc 给 document 退栈链(.stop/.prevent 修饰符与
      无处理器两种回潮形态都钉住, §05.1/§05.9);
    2. IO 兜底: 观察 .qb-chart-host, 开面板时装(_qbFxListen(true), 与宿主 RO 同点)、关面板时断
      (装卸对称防泄漏; 七处登记直写 visible=false 不经 fxClose, 断开统一由 state.js 的
      'fxPanel.visible' watcher 汇到 _qbFxListen(false)), ratio===0 即 fxClose —— 一条机制覆盖
      「滚出视口」「切页签」「抽屉关闭」; **不得挂 _qbChartDestroy**(换肤也走 destroy->build,
      会把面板误关; 系统明暗变化宿主不重挂不触发, 面板保留);
    3. reduced-motion 红线(§05.6): 判定单点在 qb_traffic_chart.js —— 内联 matchMedia + change
      监听, **不引用 AQB_FX.reduced()**(它只在 flux 皮肤挂载, 三套旧皮肤引用即 ReferenceError,
      而 test_frontend_fx_wiring 只查 shell 照绿不报); 有效值单点 fxOn = enabled && !reduce
      (面板任何操作都写不出有效值打开, enabled 只存用户意图、reduce 自动置位永不回写 store);
      matchMedia change 监听 mounted 装 / beforeUnmount 摘(系统设置恢复后有效值立即回到手动值);
      AQB_FX_CFG 同步单点 _qbFxCfgSync 附加 on 字段且 fx/fxReduce 两 watcher 都汇入(reduce 翻转
      on 必须立即跟着翻); 面板总开关显示有效值并置灰(:checked="fxOn" + :disabled="fxReduce"),
      顶部说明行「系统要求减弱动效，当前不生效」; 有效值 on 不进持久化形状(QB_FX_DEFAULTS 无 on)。"""
    shared = os.path.join(STATIC_ROOT, "shared")
    js = open(os.path.join(shared, "qb_traffic_chart.js"), encoding="utf-8").read()
    state_js = open(os.path.join(shared, "state.js"), encoding="utf-8").read()
    lifecycle_js = open(os.path.join(shared, "lifecycle.js"), encoding="utf-8").read()
    dialogs_meta_js = open(os.path.join(shared, "dialogs_meta.js"), encoding="utf-8").read()
    drawer_general_js = open(os.path.join(shared, "drawer_general.js"), encoding="utf-8").read()
    store_js = open(os.path.join(shared, "drawer_store.js"), encoding="utf-8").read()
    fx_tpl = open(os.path.join(shared, "tpl", "fx-panel.html"), encoding="utf-8").read()

    # 1a. lifecycle 点空白名单(与 drawerMenu 同组; 面板根 @click.stop 已拦截, 不误收面板内点击)
    click_m = re.search(r"this\._onDocClick = \(\) => \{(.*?)\n    \};", lifecycle_js, re.S)
    assert click_m, "lifecycle.js 缺 _onDocClick(点空白收层名单)"
    click_body = click_m.group(1)
    assert "this.fxPanel.visible = false;" in click_body, "点空白收层名单缺动效数值面板(§05.7 第 1 处)"
    assert click_body.index("this.drawerMenu.visible = false;") < click_body.index("this.fxPanel.visible = false;"), \
        "点空白名单上面板项应与 drawerMenu 同组(同层临时浮层, §05.7)"
    # 1b. Esc 退栈链: 紧跟 drawerMenu 之后(后开先关), 且先于历史弹层与抽屉分支
    fx_esc = "else if (this.fxPanel.visible) this.fxPanel.visible = false;"
    assert fx_esc in lifecycle_js, "Esc 退栈链缺动效数值面板分支(§05.7 第 2 处)"
    menu_esc = lifecycle_js.index("else if (this.drawerMenu.visible) this.drawerMenu.visible = false;")
    fx_at = lifecycle_js.index(fx_esc)
    hist_esc = lifecycle_js.index("else if (this.historyOpen) this.historyOpen = false;")
    drawer_esc = lifecycle_js.index("else if (this.drawerVisible) this.closeDrawer();")
    assert menu_esc < fx_at < hist_esc, "Esc 退栈顺序错: 面板必须紧跟 drawerMenu 之后(面板比菜单重一层, 后开先关)"
    assert fx_at < drawer_esc, "Esc 退栈顺序错: 面板开着按 Esc 只关面板, 再按 Esc 才轮到抽屉"
    # 1c. escBusy(config_hub「Esc 返回设置首页」守门的同一份浮层名单; WARN 明写新增浮层两处同步)
    busy_m = re.search(r"escBusy\(\) \{(.*?)\n    \},", dialogs_meta_js, re.S)
    assert busy_m and "this.fxPanel.visible" in busy_m.group(1), "escBusy 缺动效数值面板项(与 Esc 退栈链两处同步, §05.7 第 3 处)"
    # 1d. closeDrawer / drawerTab(面板不能比抽屉活得久; 切页签图宿主被替换, 面板会浮在新内容上)
    cd_m = re.search(r"closeDrawer\(\) \{\n(.*?)\n    \},", drawer_general_js, re.S)
    assert cd_m and "this.fxPanel.visible = false;" in cd_m.group(1), "closeDrawer 缺收面板(面板不能比抽屉活得久, §05.7 第 4 处)"
    dt_m = re.search(r"drawerTab\(tab\) \{\n(.*?)\n    \},", drawer_general_js, re.S)
    assert dt_m and "this.fxPanel.visible = false;" in dt_m.group(1), "drawerTab 缺收面板(切页签图宿主被替换, §05.7 第 5 处)"
    # 1e. 换目标/换 kind 收口单点(与 drawerTab/closeDrawer 同口径; 宿主不一定被真拆, 光靠 IO 会漏)
    sw_m = re.search(r"_switchDrawerTarget\(hash\) \{(.*?)\n    \},", store_js, re.S)
    assert sw_m and "this.fxPanel.visible = false;" in sw_m.group(1), \
        "换目标收口单点缺收面板(与 drawerTab/closeDrawer 同口径, §05.7 第 6 处; shortcuts 末尾项第 7 处在 test_drawer_dock_keyboard_w2)"

    # 2. IO 兜底: _qbFxListen 开面板支路建/观察, 关面板支路断(装卸对称); 不挂 _qbChartDestroy
    listen_m = re.search(r"_qbFxListen\(on\) \{\n(.*?)\n    \},", js, re.S)
    assert listen_m, "qb_traffic_chart.js 缺 _qbFxListen(窗口级监听装卸)"
    listen_body = listen_m.group(1)
    assert "new IntersectionObserver(" in listen_body, "IO 兜底缺位(滚出视口/切页签/抽屉关闭三路无收口, §05.7)"
    assert "en.intersectionRatio === 0" in listen_body, "IO 回调缺 ratio===0 关面板判据(§05.9 收层探针)"
    assert "this.fxClose();" in listen_body, "IO 回调必须走 fxClose 单点收层(整对象替换 + 监听断开一体)"
    assert "this._qbFxHostIo.observe(host)" in listen_body, "IO 必须观察图宿主(.qb-chart-host ref)"
    assert listen_body.count("this._qbFxHostIo.disconnect()") == 1, "IO 必须在关面板支路断开(装卸对称防泄漏)"
    destroy_m = re.search(r"_qbChartDestroy\(scope\) \{\n(.*?)\n    \},", js, re.S)
    assert destroy_m and "IntersectionObserver" not in destroy_m.group(1), \
        "IO 不得挂 _qbChartDestroy(换肤也走 destroy->build, 会把面板误关)"
    # 断开兜底的汇入点: 七处登记直写 visible=false 不经 fxClose -> state.js watcher 统一汇到
    # _qbFxListen(false), 否则点空白/Esc/抽屉关闭那几路收层后监听与 IO 永不摘(泄漏 + Alt 卡死面)
    visw_m = re.search(r'"fxPanel\.visible"\(v\) \{(.*?)\n    \},', state_js, re.S)
    assert visw_m and "this._qbFxListen(false)" in visw_m.group(1), \
        "state.js 缺 'fxPanel.visible' watcher(七处登记直写 visible 不经 fxClose, 监听/IO 断开必须统一汇到 _qbFxListen(false))"

    # 3a. reduced-motion 判定单点在本模块: 内联 matchMedia, 不引用 AQB_FX.reduced()
    assert "AQB_FX.reduced" not in js, "不得引用 AQB_FX.reduced()(只在 flux 皮肤挂载, 三套旧皮肤 ReferenceError; §05.6)"
    init_m = re.search(r"function qbInitialFxReduce\(\) \{\n(.*?)\n\}", js, re.S)
    assert init_m and "matchMedia" in init_m.group(1) and "catch" in init_m.group(1), \
        "缺 qbInitialFxReduce(reduced-motion 判定单点; matchMedia 函数体内惰性取, node 探针顶层不碰 BOM)"
    # 3b. 有效值单点: effectiveOn = enabled && !reduce(两因子缺一即红线失守)
    fxon_m = re.search(r"fxOn\(\) \{\n(.*?)\n    \},", js, re.S)
    assert fxon_m and "this.fx.enabled" in fxon_m.group(1) and "this.fxReduce" in fxon_m.group(1), \
        "缺有效值单点 fxOn = enabled && !reduce(面板任何操作都写不出有效值打开, §05.6)"
    assert "fxReduce: qbInitialFxReduce()" in state_js, "state.js 缺 fxReduce 显式建字段(undefined 是非响应式盲区)"
    # 3c. matchMedia change 监听: mounted 装 / beforeUnmount 摘(成对; 系统设置恢复 -> 有效值立即回手动值)
    mo_m = re.search(r"mounted\(\) \{\n(.*?)\n  \},\n  beforeUnmount\(\) \{", js, re.S)
    assert mo_m and 'matchMedia("(prefers-reduced-motion: reduce)")' in mo_m.group(1) \
        and 'addEventListener("change"' in mo_m.group(1), \
        "mounted 缺 matchMedia change 监听(系统设置恢复后有效值回不到用户手动值, §05.6)"
    bu_m = re.search(r"beforeUnmount\(\) \{\n(.*?)\n  \},", js, re.S)
    assert bu_m and 'removeEventListener("change"' in bu_m.group(1), \
        "beforeUnmount 缺 matchMedia change 监听摘除(MediaQueryList 持实例引用, 泄漏)"
    # 3d. AQB_FX_CFG 同步单点: 附加有效值 on; fx/fxReduce 两 watcher 都汇入(reduce 翻转 on 立即跟着翻)。
    # fxOn 是 computed, 同步面只允许 getter 读取形态(this.fxOn 不带括号 —— 带括号即把 getter 的值
    # 当函数调, TypeError 整页白屏, 守阵 test_frontend_computed_not_invoked_as_function 同口径)
    sync_m = re.search(r"_qbFxCfgSync\(\) \{\n(.*?)\n    \},", js, re.S)
    assert sync_m and "cfg.on = this.fxOn;" in sync_m.group(1), \
        "AQB_FX_CFG 缺有效值 on 字段(S1/S3 引擎侧开关消费面, §05.6); fxOn 是 computed 只许 getter 读取"
    assert "this.fxOn(" not in js, "computed fxOn 不得以 this.fxOn() 调用(getter 值再调即 TypeError 白屏)"
    assert "handler() { this._qbFxCfgSync(); }" in state_js, "state.js fx watcher 未汇入 _qbFxCfgSync 单点"
    redw_m = re.search(r"fxReduce\(\) \{\n(.*?)\n    \},", state_js, re.S)
    assert redw_m and "this._qbFxCfgSync()" in redw_m.group(1), \
        "state.js 缺 fxReduce watcher(reduce 翻转时 on 必须立即跟着翻, 只挂 fx watcher 会漏)"
    # 有效值不进持久化形状: QB_FX_DEFAULTS 无 on 键(persistQbFx 只写 fx; reduce 态的强关是
    # 运行期事实不是用户意图, 落盘会把红线值带进 store)
    defaults_m = re.search(r"const QB_FX_DEFAULTS = \{(.*?)\n\};", js, re.S)
    assert defaults_m and not re.search(r"\bon:", defaults_m.group(1)), \
        "QB_FX_DEFAULTS 不得含 on 键(有效值不进持久化形状, store 只存 15+1 字段)"
    # 3e. 面板面: 总开关显示有效值并置灰 + 顶部说明行
    assert ':checked="fxOn"' in fx_tpl and ':disabled="fxReduce"' in fx_tpl, \
        "总开关必须显示有效值且 reduce 态置灰(:checked=fxOn + :disabled=fxReduce, §05.6)"
    assert ':checked="fx.enabled"' not in fx_tpl, \
        "总开关不得直接显示 fx.enabled(那是用户意图; reduce 态必须显示有效值为关, 灰而不能是勾着不生效)"
    assert 'v-if="fxReduce"' in fx_tpl and "系统要求减弱动效，当前不生效" in fx_tpl, \
        "缺 reduce 说明行(置灰读不出原因是系统层可访问性红线, 用户会当故障报; §05.6)"

    # 4. 面板根 Esc(§05.1 关闭路径 + §05.9 探针): 根处理器走 fxEsc —— 面板可见才 stopPropagation
    # + preventDefault + fxClose(焦点在面板控件内如刚拖完滑杆按 Esc 也只关面板, 同一次 Esc 不再
    # 推进抽屉退栈链, 一次 Esc 只关一层); 退场过渡(fx-pop-leave-active 120ms)期 visible 已翻
    # false 而焦点仍在面板控件里时**放行**该次 Esc 给 document 退栈链 —— 与面板外二次 Esc 关
    # 抽屉行为一致。.stop/.prevent 修饰符不得回潮: 修饰符的阻断先于处理器表达式, 退场期那次
    # Esc 被整体吞掉(两处行为不一致, 评审 nit 轮裁决); 无处理器形态(只拦不关)同样不得回潮。
    assert '@keydown.esc="fxEsc"' in fx_tpl, \
        "面板根 Esc 缺 fxEsc 处理器(只拦不关或修饰符吞 Esc 均破坏 §05.1/§05.9 关闭语义)"
    assert "@keydown.esc.stop" not in fx_tpl and "@keydown.esc.prevent" not in fx_tpl, \
        "面板根 Esc 不得用 .stop/.prevent 修饰符(阻断先于处理器, 退场过渡期吞掉本应放行的 Esc)"
    fxe_m = re.search(r"fxEsc\(e\) \{\n(.*?)\n    \},", js, re.S)
    assert fxe_m, "qb_traffic_chart.js 缺 fxEsc(面板根 Esc 处理器)"
    fxe_body = fxe_m.group(1)
    assert "this.fxPanel.visible" in fxe_body and "return;" in fxe_body, \
        "fxEsc 缺可见性早退(退场过渡期须放行该次 Esc 给 document 退栈链)"
    assert "stopPropagation" in fxe_body and "preventDefault" in fxe_body and "this.fxClose();" in fxe_body, \
        "fxEsc 可见分支必须 stopPropagation + preventDefault + fxClose(同一次 Esc 只关面板一层)"


# 纵轴固定模式 + 缺口游程 + 重启缝判据 node 电池(2026-10-08; P4 追加 _qbSeamHint, plan 26-10-15-0829):
# 模块级纯函数 _qbYRange/_qbGapRuns/_qbChainBounds/_qbGapZone/_qbPointsColumns/_qbSeamHint 真跑。无 node 静默跳过(与 _NODE_QB_TRAFFIC_PROBE 同口径)。
_NODE_QB_YAXIS_PROBE = r"""
const fs = require("fs");
global.window = {};
eval(fs.readFileSync(process.argv[1], "utf8"));
const checks = [];
const eq = (n, got, want) => checks.push([n, JSON.stringify(got) === JSON.stringify(want)]);
const ok = (n, cond) => checks.push([n, !!cond]);
// 值域: 自动 = peak*1.05(无数据回落 1); 固定上限取 max(cap, peak*1.05) —— 峰值超上限按峰值显示
eq("auto 无数据回落 1", _qbYRange(0, 0), [0, 1]);
eq("auto 峰值", _qbYRange(100, 0), [0, 105]);
eq("固定上限高于峰值(上限即顶)", _qbYRange(100, 120), [0, 120]);
eq("峰值超固定上限按峰值显示", _qbYRange(200, 120), [0, 210]);
eq("手动上限无峰值(上限即顶)", _qbYRange(0, 50), [0, 50]);
// 缺口游程: 上下行皆 null 才算缺口(单列 null 防御性不误判)
eq("缺口游程 中段+尾段", _qbGapRuns([1, null, null, 4, null], [1, null, null, 4, null]), [[1, 2], [4, 4]]);
eq("缺口游程 前导", _qbGapRuns([null, 2, 3], [null, 2, 3]), [[0, 0]]);
eq("缺口游程 全 null", _qbGapRuns([null, null], [null, null]), [[0, 1]]);
eq("缺口游程 无缺口", _qbGapRuns([1, 2, 3], [1, 2, 3]), []);
eq("单列 null 不算缺口", _qbGapRuns([null, 2], [1, 2]), []);

// 缺口**区段归类**(2026-10-30): 数据链之外只陈述「没有数据」, 链中间的洞才谈「中断」。
// 边界只认本帧 points, 不用种子 added_on —— 跳检是删同 hash 再重加且流量按 infohash 留存,
// 拿 added_on 切一刀会把早期真实数据误判成「尚未添加」(与本次要修的失真同型反向)。
eq("数据链边界 前导空洞", _qbChainBounds([null, null, 3, 4], [null, null, 3, 4]), [2, 3]);
eq("数据链边界 尾随空洞", _qbChainBounds([3, 4, null], [3, 4, null]), [0, 1]);
eq("数据链边界 全空", _qbChainBounds([null, null], [null, null]), [-1, -1]);
eq("数据链边界 无缺口", _qbChainBounds([1, 2], [1, 2]), [0, 1]);
eq("数据链边界 单列有点即算观测", _qbChainBounds([null, 3], [5, null]), [0, 1]);
eq("区段 链首之前->outside", _qbGapZone(0, 2, 3), "outside");
eq("区段 链尾之后->outside", _qbGapZone(3, 0, 1), "outside");
eq("区段 全空->outside(>-1 恒真)", _qbGapZone(0, -1, -1), "outside");
eq("区段 链中间的洞->mid", _qbGapZone(2, 0, 4), "mid");
eq("区段 恰在链首->mid(首桶有观测)", _qbGapZone(0, 0, 3), "mid");
// hover 侧把 points 转成 uPlot 同形状两列, 与画布侧共用上面同一判据
eq("转列 对齐 uPlot 形状", _qbPointsColumns([null, { t: 10, up: 1, dl: 2 }]), [[null, 1], [null, 2]]);
eq("转列 全空", _qbPointsColumns([null, null]), [[null, null], [null, null]]);

// 重启缝提示判据(P4, plan 26-10-15-0829; 左端口径修订 2026-10-16, issue 26-10-16-0954): _qbSeamHint 真跑
// —— 数据链末点早于右沿 + 重启贴近链末(∈ [链末桶前一桶起点, 右沿]) -> 提示; 链到右沿/链确已接续/旧后端不提示
// 场景重建: 链止于 t=130 桶(覆盖端 160), 尾区 [160, 250], 服务 178 起 -> 提示
const mkP = (t, dl, up) => ({ t, dl, up });
const seamPts = [mkP(100, 5, 5), mkP(130, 6, 6), null, null, null];
eq("重启缝 尾区含重启->提示", _qbSeamHint(seamPts, 30, { server_started_at: 178 }), { startedAt: 178 });
eq("重启缝 边界 恰在尾区起点->提示", _qbSeamHint(seamPts, 30, { server_started_at: 160 }), { startedAt: 160 });
eq("重启缝 边界 恰在右沿->提示", _qbSeamHint(seamPts, 30, { server_started_at: 250 }), { startedAt: 250 });
eq("重启缝 链到右沿->null(末桶观测/当前桶未采完是常态)", _qbSeamHint([mkP(100, 5, 5), mkP(130, 6, 6)], 30, { server_started_at: 178 }), null);
eq("重启缝 重启落在链末桶覆盖窗->提示(修订: 链末桶晚于重启时刻不再是豁免)", _qbSeamHint(seamPts, 30, { server_started_at: 140 }), { startedAt: 140 });
eq("重启缝 边界 恰在链末前一桶起点->提示", _qbSeamHint(seamPts, 30, { server_started_at: 100 }), { startedAt: 100 });
eq("重启缝 早于链末前一桶->null(链确已接续)", _qbSeamHint(seamPts, 30, { server_started_at: 99 }), null);
eq("重启缝 重启远早于链末->null(链确已接续)", _qbSeamHint(seamPts, 30, { server_started_at: 40 }), null);
eq("重启缝 晚于右沿->null(防御)", _qbSeamHint(seamPts, 30, { server_started_at: 300 }), null);
eq("重启缝 旧后端无新键->null(不猜)", _qbSeamHint(seamPts, 30, {}), null);
eq("重启缝 meta缺失->null", _qbSeamHint(seamPts, 30, null), null);
eq("重启缝 interval非法->null", _qbSeamHint(seamPts, 0, { server_started_at: 178 }), null);
eq("重启缝 全null->null(空态面)", _qbSeamHint([null, null], 30, { server_started_at: 178 }), null);
eq("重启缝 空数组->null", _qbSeamHint([], 30, { server_started_at: 178 }), null);
// 反例回归(issue 26-10-16-0954 实测帧重建): 1m 窗 interval=2s —— 04:45:00 记 100, 04:45:01 重启(101),
// 首采桶 04:45:02(102, 全窗唯一非 null; 左侧停机洞 + 右侧开放零游程读侧未交付均 null), 右沿 140;
// 修订前判据在 started < 链末桶覆盖端(104) 处恒返回 null(现场 04:45:40 帧零提示的机制)
const seamFrame = new Array(30).fill(null);
seamFrame[11] = mkP(102, 0, 0);
eq("重启缝 实测帧 首采即链末桶->提示(旧口径恒 null)", _qbSeamHint(seamFrame, 2, { server_started_at: 101 }), { startedAt: 101 });
eq("重启缝 实测帧 边界 恰在链末前一桶起点->提示", _qbSeamHint(seamFrame, 2, { server_started_at: 100 }), { startedAt: 100 });
eq("重启缝 实测帧 早一桶宽->null", _qbSeamHint(seamFrame, 2, { server_started_at: 99 }), null);

/* ---------- 缺口斜纹**配色 + 几何**真跑(2026-10-08 两轮) ----------
 * 用记账式假 ctx 调**真实的** AQB_QB_TRAFFIC.methods._qbDrawGaps, 断言:
 *   1. 配色: 写进画布的 strokeStyle/globalAlpha 是高对比专用令牌而非 --hairline 系极低 alpha;
 *   2. 几何: 逐 run 追加的**缺口矩形 clip** 恰好等于 [xa, xb] x [T, T+H], 且每条斜纹线段都被该
 *      矩形包含(端点 x 落在 [xa, xb])—— 钉死"斜纹铺成竖矩形"的语义: 若有人删掉 per-run clip
 *      (退回只裁绘图区), 斜带(宽 H 的平行四边形)的端点会越出 [xa, xb], 断言立刻变红。
 * 这条电池的价值: 把"颜色够不够看得见""斜纹落在哪"从"读源码字符串"升级为"实跑取真值并做数值/
 * 几何判定" —— 静态锚可能被同步改掉, 数值下界与几何包含判定不会。 */
function _mkCtx2() {
  const noop = () => {};
  return {
    style: null, alpha: null, segCount: 0, _x0: 0,
    clips: [], _pendingRect: null, _segs: [],
    save: noop, restore: noop, beginPath: noop, setLineDash: noop,
    rect(x, y, w, h) { this._pendingRect = { x, y, w, h }; },
    clip() { if (this._pendingRect) this.clips.push(this._pendingRect); },
    moveTo(x, y) { this._sx = x; },
    lineTo(x, y) { this.segCount++; this._segs.push([this._sx, x]); },
    stroke() {},
    set strokeStyle(v) { this.style = v; },
    get strokeStyle() { return this.style; },
    set globalAlpha(v) { this.alpha = v; },
    get globalAlpha() { return this.alpha; },
    set lineWidth(v) {}, get lineWidth() { return 1; },
  };
}
(function () {
  const AQB2 = global.window.AQB_QB_TRAFFIC;
  const fn = AQB2 && AQB2.methods && AQB2.methods._qbDrawGaps;
  ok("_qbDrawGaps 可取(配色电池)", !!fn);
  if (!fn) return;
  const xs2 = [0, 60, 120, 180, 240];
  const ctx2 = _mkCtx2();
  const u2 = {
    data: [xs2, [5, 5, null, null, 5], [5, 5, null, null, 5]],
    bbox: { left: 50, top: 17, width: 825, height: 233 },
    ctx: ctx2,
    valToPos: (v) => (xs2.indexOf(v) / 4) * 825,
  };
  /* tk.gap = 高对比专用令牌值; tk.grid = 旧的 --hairline 极低 alpha 值 —— 必须选前者 */
  fn.call({ _qbCanvasScale: (uu) => { uu.ctx.save(); return 1; } }, u2,
    { grid: "rgba(255,255,255,.055)", gap: "rgba(255,255,255,.22)" });
  eq("斜纹取 gap 专用令牌(不取 --hairline)", ctx2.style, "rgba(255,255,255,.22)");
  eq("斜纹不再叠 globalAlpha 折半", ctx2.alpha, 1);
  ok("斜纹确实画了线段(>0 条)", ctx2.segCount > 0);
  /* 数值下界: 令牌 alpha 必须 >= 0.15(--hairline 系 0.055 量级的 3 倍以上才算"看得见") */
  const m2 = /rgba\(\s*[\d.]+\s*,\s*[\d.]+\s*,\s*[\d.]+\s*,\s*([\d.]+)\s*\)/.exec(
    "rgba(255,255,255,.22)");
  ok("专用令牌 alpha 量级 >= 0.15(0.05 级别等同不可见)", m2 && parseFloat(m2[1]) * ctx2.alpha >= 0.15);

  // ---- 几何: per-run 缺口矩形 clip + 扫线覆盖 ----
  // 注: 真实 ctx 的 clip 是**画布操作**, 不会改写我们记账到的原始端点 —— 故原始 moveTo/lineTo
  // 端点本就会越出 [xa, xb](越界部分由 canvas clip 收掉)。几何正确性由两点钉死:
  //   1. per-run 缺口矩形 clip 存在且 == [xa, xb] x [T, T+H](删掉它即退回"只裁绘图区"= 平行四边形缺陷);
  //   2. 扫线范围**覆盖**缺口带(有线段右下端 >= xb, 有线段左上端 <= xa)—— 保证裁剪后左/右竖直边都铺满, 无半边留白。
  const xa = 50 + (xs2.indexOf(120) / 4) * 825;   // 缺口 = 桶 2..3
  const xb = 50 + (xs2.indexOf(180) / 4) * 825;
  const T = 17, H = 233;
  const gapClips = ctx2.clips.filter((c) => Math.abs(c.x - xa) < 1e-6 && Math.abs(c.w - (xb - xa)) < 1e-6
    && Math.abs(c.y - T) < 1e-6 && Math.abs(c.h - H) < 1e-6);
  ok("存在逐 run 缺口矩形 clip(ctx.rect(xa, T, xb-xa, H))", gapClips.length >= 1);
  ok("缺口矩形 clip 与绘图区 clip 并存(外层仍收在绘图区)",
    ctx2.clips.some((c) => Math.abs(c.w - 825) < 1e-6));
  const segs = ctx2._segs || [];
  // 扫线覆盖: 每条线段 = [左上端 x0, 右下端 x1](x0 = x-H, x1 = x); 需有 x1 >= xb(右端铺满)
  // 且有 x0 <= xa(左端铺满)。
  ok("扫线覆盖缺口左边界(有线段左上端 <= xa)", segs.some((s) => s[0] <= xa + 1e-6));
  ok("扫线覆盖缺口右边界(有线段右下端 >= xb)", segs.some((s) => s[1] >= xb - 1e-6));
  // 扫线步长恒定 8px(斜纹间距), 且每条线段水平跨度 = H(45 度硬约束)
  ok("每条斜纹线段跨度 = H(45 度)", segs.every((s) => Math.abs((s[1] - s[0]) - H) < 1e-6));
})();

(function () {
  /* ---------- 缺口斜纹**只给数据链中段**(2026-10-30) ----------
   * 斜纹是「中断」的视觉记号; 链外的空白(首次采样之前 / 最后一次之后 / 全帧无观测)同样是
   * 「不知道原因的没有数据」, 铺斜纹等于在视觉上重复一遍 tooltip 已纠掉的归因错误。
   * 用同一份记账式假 ctx 实跑真 _qbDrawGaps, 断言那些段**一笔都没画**。 */
  const fn3 = global.window.AQB_QB_TRAFFIC && global.window.AQB_QB_TRAFFIC.methods._qbDrawGaps;
  ok("_qbDrawGaps 可取(区段电池)", !!fn3);
  if (!fn3) return;
  const xs3 = [0, 60, 120, 180];
  const paint = (up, dl) => {
    const c = _mkCtx2();
    fn3.call({ _qbCanvasScale: (z) => { z.ctx.save(); return 1; } }, {
      data: [xs3, up, dl],
      bbox: { left: 50, top: 17, width: 825, height: 233 },
      ctx: c,
      valToPos: (v) => (xs3.indexOf(v) / 3) * 825,
    }, { grid: "rgba(255,255,255,.055)", gap: "rgba(255,255,255,.22)" });
    return c;
  };
  const head = paint([null, null, 5, 6], [null, null, 5, 6]);     // 链首之前的空白
  ok("链首之外的空白不铺斜纹(0 条线段)", head.segCount === 0);
  ok("链首之外不落逐 run 缺口 clip", head.clips.length === 0);
  const tail = paint([5, 6, null, null], [5, 6, null, null]);     // 链尾之后的空白
  ok("链尾之外的空白不铺斜纹(0 条线段)", tail.segCount === 0);
  const none = paint([null, null, null, null], [null, null, null, null]);
  ok("全帧无观测不铺斜纹(0 条线段)", none.segCount === 0);
  const inner = paint([5, null, null, 6], [5, null, null, 6]);    // 链中间的洞
  ok("链中间的洞照旧铺斜纹", inner.segCount > 0);
  ok("链中间的洞仍落逐 run 缺口 clip", inner.clips.length >= 2);
})();

(function () {
  /* ---------- 限速分段(plan 26-10-12-0535 D4/D7)真跑: _qbLimitSegs/_qbLimitAt ----------
   * 用真实的模块级纯函数断言: 每段几何(区间/末段到 tEnd)/退化段不画/悬停二分取值
   * (含记录起点前 null)。若有人把分段改回单值画满整窗, 本电池立刻红。 */
  ok("_qbLimitSegs 可取", typeof _qbLimitSegs === "function");
  ok("_qbLimitAt 可取", typeof _qbLimitAt === "function");
  const EV = [[100, 1024, 2048], [200, 0, 4096], [300, 512, 512]];
  eq("分段几何: 每段 = 相邻事件区间", _qbLimitSegs(EV, 400),
    [{ t0: 100, t1: 200, up: 1024, down: 2048 }, { t0: 200, t1: 300, up: 0, down: 4096 }, { t0: 300, t1: 400, up: 512, down: 512 }]);
  eq("分段: 末段延伸到 tEnd", _qbLimitSegs(EV.slice(0, 1), 250), [{ t0: 100, t1: 250, up: 1024, down: 2048 }]);
  eq("分段: 空事件空段", _qbLimitSegs([], 400), []);
  eq("分段: 非法输入空段", _qbLimitSegs(null, 400), []);
  eq("分段: tEnd 非法空段", _qbLimitSegs(EV, 0), []);
  eq("分段: 越出右沿的退化段不画", _qbLimitSegs([[500, 1, 1]], 400), []);
  eq("悬停二分: 取 <= ts 最近事件", _qbLimitAt(EV, 250), [0, 4096]);
  eq("悬停二分: 精确命中", _qbLimitAt(EV, 200), [0, 4096]);
  eq("悬停二分: 记录起点前 null(D5 不猜)", _qbLimitAt(EV, 50), null);
  eq("悬停二分: 空事件 null", _qbLimitAt([], 100), null);
  eq("悬停二分: 末事件之后仍取末值", _qbLimitAt(EV, 999), [512, 512]);
})();
console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
"""

# _QB_SCOPES 是模块级 `const`, sloppy 模式下的直接 eval 不会把它漏到外层作用域(只有 function/var
# 声明会漏) —— 故这里用 `new Function(源码 + "return _QB_SCOPES;")` 把它从函数体内部取出来,
# 再对三个作用域的 `stale` 谓词喂真值上下文做**行为**断言(不读源码字符串)。
_NODE_QB_SCOPE_STALE_PROBE = r"""
const fs = require("fs");
global.window = {};
const src = fs.readFileSync(process.argv[1], "utf8");
const SCOPES = new Function(src + "\nreturn _QB_SCOPES;")();
const checks = [];
const ok = (n, cond) => checks.push([n, !!cond]);

/* stale 谓词语义(见 qb_traffic_chart.js 文件头): stale=true = 在途响应**已过期** -> 丢弃
 * (不落袋 + loading 不清)。故「本图正在被看」必须 stale=false, 其余一律 stale=true。
 * 2026-10-12 修: W2–W6 机械改名把 torrent/group 两处 `!(...)` 写成 `!!(...)`, 语义整个翻转
 * (恰在本图活跃时判过期) -> 数据永不落袋、loading 卡死 -> 种子流量页签恒停「正在加载…」。
 * 本电池就是那个漏网的运行时判据: 取反写反(单/双 bang 互换)立刻红。 */
const G = (over) => Object.assign(
  { drawer: { open: true, scope: "global" }, drawerIsTraffic: true, drawerIsSeed: false, page: "groups" },
  over || {});
ok("global: 正看全局图 stale=false(数据必须落袋)", SCOPES.global.stale(G()) === false);
ok("global: 已切到分组图 stale=true(旧响应丢弃)",
  SCOPES.global.stale(G({ drawer: { open: true, scope: "group" } })) === true);
ok("global: 面板已关 stale=true", SCOPES.global.stale(G({ drawer: { open: false, scope: "global" } })) === true);

const H = "a".repeat(40);
const T = (over) => Object.assign(
  { drawer: { open: true, tab: "traffic", hash: H }, drawerIsSeed: true, qbTrafficOn: true }, over || {});
ok("torrent: 正看该种子流量页签 stale=false(本次报障点: 恒 true 即卡在加载态)",
  SCOPES.torrent.stale(T(), H) === false);
ok("torrent: 已换目标(hash 不符) stale=true", SCOPES.torrent.stale(T(), "b".repeat(40)) === true);
ok("torrent: 已切到别的页签 stale=true",
  SCOPES.torrent.stale(T({ drawer: { open: true, tab: "general", hash: H } }), H) === true);
ok("torrent: 面板已关 stale=true",
  SCOPES.torrent.stale(T({ drawer: { open: false, tab: "traffic", hash: H } }), H) === true);
ok("torrent: 非种子形态(流量形态) stale=true",
  SCOPES.torrent.stale(T({ drawerIsSeed: false }), H) === true);
ok("torrent: 功能未启用 stale=true", SCOPES.torrent.stale(T({ qbTrafficOn: false }), H) === true);

const K = "Z3JvdXA";  // 分组 key(base64url 形态, 内容无关)
const R = (over) => Object.assign(
  { drawer: { open: true, scope: "group" }, drawerIsTraffic: true, qbGroupKey: K, qbTrafficOn: true },
  over || {});
ok("group: 正看分组流量图 stale=false", SCOPES.group.stale(R(), K) === false);
ok("group: 已换分组 stale=true", SCOPES.group.stale(R(), "other") === true);
ok("group: 面板已关 stale=true", SCOPES.group.stale(R({ drawer: { open: false, scope: "group" } }), K) === true);
ok("group: 已切到全局图 stale=true",
  SCOPES.group.stale(R({ drawer: { open: true, scope: "global" } }), K) === true);

/* active 与 stale 必须**同向**: active=true(该图应显示/可拉)时 stale 必须=false —— 两谓词
 * 若各自漂移(本次根因), 这一条把「图该显示但数据被判过期」的组合直接钉死。 */
ok("同向性: global active 时 stale=false",
  !SCOPES.global.active(G()) || SCOPES.global.stale(G()) === false);
ok("同向性: torrent active 时 stale=false",
  !SCOPES.torrent.active(T()) || SCOPES.torrent.stale(T(), H) === false);
ok("同向性: group active 时 stale=false",
  !SCOPES.group.active(R()) || SCOPES.group.stale(R(), K) === false);

/* ---------- 消费端真跑: _qbLoad 落袋 + loading 复位(用户可见症状的判据) ----------
 * 只钉谓词还不够 —— 真正让用户看到「加载不出来」的是 _qbLoad 里 stale=true 触发的
 * 「数据不落袋 + loading 不复位 + 早退不建图」。这里用真实的方法体配一个假 vm 跑一遍,
 * 断言成功响应确实落进 qbTorrentData/qbGroupData 且 loading 归位(即图会画)。 */
const M = global.window.AQB_QB_TRAFFIC.methods;
const mkVm = (scope) => ({
  qbTrafficOn: true,
  drawer: { open: true, tab: "traffic", hash: H, scope: scope === "torrent" ? undefined : "group" },
  drawerIsSeed: scope === "torrent",
  drawerIsTraffic: scope !== "torrent",
  page: "groups",
  qbGroupKey: K,
  qbTorrentWindow: "24h", qbTorrentLoading: false, qbTorrentData: null, qbTorrentError: "",
  qbGroupWindow: "24h", qbGroupLoading: false, qbGroupData: null, qbGroupError: "",
  api: async () => ({ points: [{ t: 1000, up: 10, dl: 20 }], totals: [{ up: 10, dl: 20 }], limits: [],
    meta: { interval_s: 30 } }),
  $nextTick: (fn) => { if (fn) fn(); },
  _qbChartBuild: () => {}, _qbPollResync: () => {}, _drawerDone: () => {},
});
(async () => {
  const vt = mkVm("torrent");
  await M._qbLoad.call(vt, "torrent");
  ok("落袋: 种子流量响应进入 qbTorrentData(非 null)", vt.qbTorrentData !== null);
  ok("落袋: 种子 loading 已复位(false)", vt.qbTorrentLoading === false);
  ok("落袋: 无错误态", vt.qbTorrentError === "");

  const vg = mkVm("group");
  await M._qbLoad.call(vg, "group");
  ok("落袋: 分组流量响应进入 qbGroupData(非 null)", vg.qbGroupData !== null);
  ok("落袋: 分组 loading 已复位(false)", vg.qbGroupLoading === false);

  console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
    failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
})();
"""


def test_frontend_qb_traffic_scope_stale_polarity():
    """流量图三挂点 stale 谓词极性守阵(2026-10-12 修「种子流量图加载不出来」)

    缺陷: W2–W6 抽屉重构的机械改名(``drawer.kind === "seed"`` -> ``drawerIsSeed``)把 torrent 与
    group 两处 ``stale`` 谓词从 ``!(...)`` 写成 ``!!(...)`` —— 取反变双重取反, 语义**整个翻转**:
    恰在本图活跃时判「响应已过期」。后果链: ``_qbLoad`` 里 ``stale=true`` -> 数据不落袋 + loading
    不复位 + 早退不建图 -> ``qbCurPending``(loading && 无数据 && 无错误)恒真 -> 种子「流量」页签
    永远停在「正在加载流量数据…」; 轮询 tick 又被 ``loading`` 卡住 -> 不会自愈。global 挂点未中招
    (仍是 ``!(...)``), 故症状只在种子/分组图。

    为什么既有守阵没拦住: 本文件对 ``_QB_SCOPES`` 的断言全是**源码字符串**级的(字段名/字面量
    在不在), 而 ``!!`` 与 ``!`` 的差别只在运行时语义 —— 静态锚对它天然失明。

    本守阵两层:
    1. **运行时行为**(node 电池, 主判据): 用 ``new Function(源码 + "return _QB_SCOPES;")`` 取出
       作用域表, 对三挂点喂「本图活跃 / 已切走 / 已关闭 / 换目标 / 功能关闭」五类真值上下文, 断言
       ``stale`` 取假/取真与契约一致, 并钉 ``active => stale === false`` 同向性;
    2. **静态极性**(无 node 兜底, 也钉书写形态): 两处 ``stale`` 谓词必须是否定式 ``!(``, ``!!(``
       形态不得回潮(本次根因的书写面)。
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    js = open(os.path.join(shared, "qb_traffic_chart.js"), encoding="utf-8").read()

    # 1. 静态极性: stale 谓词是否定式(`!(`), 禁双重取反 `!!(`
    scopes = re.search(r"const _QB_SCOPES = \{\n(.*?)\n\};", js, re.S)
    assert scopes, "缺 _QB_SCOPES 作用域表(三挂点单一描述源)"
    sb = "\n" + scopes.group(1)
    for scope in ("torrent", "group"):
        seg = sb.split("\n  %s: {" % scope)[1].split("stale:")[1]
        expr = seg.split("),")[0]
        assert re.search(r"=>\s*!\(t", expr), \
            f"{scope}.stale 必须是否定式 `!(...)`(stale=true 表示响应已过期丢弃; " \
            f"写成 `!!(...)` 语义翻转 -> 图恒不加载), 实测: stale:{expr[:60]}"
        assert "!!(" not in expr, \
            f"{scope}.stale 出现双重取反 `!!(...)`(2026-10-12 事故书写形态: 恰在活跃时判过期)"

    # 2. 运行时行为(node 电池; 无 node 静默跳过, 静态极性仍已生效)
    node = shutil.which("node")
    if node:
        proc = subprocess.run(
            [node, "-e", _NODE_QB_SCOPE_STALE_PROBE,
             os.path.join(shared, "qb_traffic_chart.js")],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        assert proc.returncode == 0, f"stale 极性 node 电池跑挂: {proc.stderr.strip()}"
        rep = json.loads(proc.stdout.strip().splitlines()[-1])
        assert rep["failed"] == [], f"stale 极性电池 {rep['ok']}/{rep['total']} 过, 失败: {rep['failed']}"


def test_frontend_qb_traffic_yaxis_and_annotation():
    """流量图纵轴固定模式 + 画布注解层守阵(2026-10-08, issue 26-10-07-0149 认领一并做)

    用户需求: 纵轴最大值可固定(自动 / 限速+20% / 手动 MiB/s), 峰值超出固定上限时**按峰值显示**;
    附限速虚线 + 缺口斜纹注解层(共享图面, 三挂点 + 经典/所有变体全生效)。钉住四条静默失效面:
    1. 值域语义(_qbYRange 纯函数 node 真跑): 自动 = peak*1.05(无数据回落 1); 固定上限取
       max(cap, peak*1.05) —— **上限只保底不裁剪**(峰值超上限按峰值显示, 用户拍板); 限速三
       作用域同源 = qB 全局限速上下行**较大者**(单点 _qbGlobalLimit -> speedLimitBytes);
    2. 缺口游程(_qbGapRuns node 真跑): 上下行**皆** null 才算缺口(单列 null 防御性不误判);
    3. 持久化粒度 = **三作用域各自独立**(qbYAxisStoreKey 三键, 与窗口档位的「全局单独/组种
       共用」不同); 初值 qbInitialYAxis 只认合法模式 + 正数手动值, 坏值/无存储回落默认;
    4. 接线与三皮肤成对: 切模式/改值/落盘/重排四件 + 建图 y range 走 _qbYRange(_qbYCapOf(scope))
       + draw/drawClear 两钩子画注解层(uPlot 1.6.x ctx 无 transform = 设备像素, 按 uPlot.pxRatio
       换算; 限速线只画落在可视值域内的)+ 模板控件(.qb-seg 三态 + 手动输入 + 生效上限读数) +
       CSS .qb-seg/.qb-yaxis-input 三皮肤成对。
    5. 缺口斜纹**配色**(2026-10-08 修用户报「颜色几乎不可分辨」): 斜纹色原走 tk.grid =
       --hairline(装饰性 1px 发丝线令牌, 实测 alpha 仅 0.05~0.08)再叠 globalAlpha 0.5 ⇒ 有效
       不透明度约 3%, 深浅底上**都**等于没画。守阵 = node 电池实跑 _qbDrawGaps 取真值断言
       strokeStyle 走专用令牌 --qb-gap-hatch 且不叠 alpha 折半 + 令牌量级下界 >=0.15; 静态锚
       钉令牌在三皮肤 + prism 五主题成对定义、亮主题(frost/golden)不得用白色(镜面缺陷)。
       附: 斜纹**几何**经逐条线段比对与代数验证与原式恒等, 故**不设**"位移"类锚(该说法经实测
       证伪, 设了就是假锚)。
    6. 重启缝提示(P4, plan 26-10-15-0829; 左端口径修订 2026-10-16, issue 26-10-16-0954): 判据单点
       _qbSeamHint 纯函数 node 真跑(重启贴近链末 -> 提示, 含「重启后首采即链末桶」的实测帧形态 /
       链到右沿或链确已接续(重启早于链末前一桶)或旧后端无新键 -> null, 边界含尾区起点、右沿与
       左端「链末桶前一桶起点」三点) + computed qbCurSeamHint 消费单点 + drawer.html 提示行(三挂点
       共用正文块一处, 文案单源, 带服务重启时刻锚 fmtTime) + null 不连线 spanGaps:false 原样。
    7. 缺口的**区段分治**(2026-10-30, 用户报「种子添加之前的时间提示说成 qB 断联不符合实际」):
       判据 _qbChainBounds/_qbGapZone node 真跑(数据链 = 首/末个非空桶; outside = 链首之前 /
       链尾之后 / 全帧无观测, 判据**只认本帧 points**、不碰种子 added_on —— 跳检即删同 hash
       再重加且流量按 infohash 留存, 用 added_on 切一刀会把早期真实数据误判成「尚未添加」);
       斜纹只给链中段的洞(node 电池实跑 _qbDrawGaps: 链外段线段数与 clip 数皆 0, 链中段照旧
       铺), 链外空白由 tooltip 用中性文字陈述; 文案按「区段 × 作用域」收在 computed 单点
       qbCurGapText(全局态没有"种子"这一主语, 一律套「此种子」是又一次瞎编)。"""
    shared = os.path.join(STATIC_ROOT, "shared")
    js = open(os.path.join(shared, "qb_traffic_chart.js"), encoding="utf-8").read()
    state_js = open(os.path.join(shared, "state.js"), encoding="utf-8").read()
    drawer_tpl = open(os.path.join(shared, "tpl", "drawer.html"), encoding="utf-8").read()
    # W3(计划 26-10-11-2106): 档位/纵轴控件组的唯一实现住在这里(<aq-qb-ctl>)
    head_tpl = open(os.path.join(shared, "tpl", "drawer-head.html"), encoding="utf-8").read()

    # 1. 常量单点(模式清单 / 默认 / 倍率 / MiB 换算)
    assert 'const QB_YAXIS_MODES = ["auto", "limit", "manual"];' in js, "缺 QB_YAXIS_MODES 三态单点"
    assert 'QB_YAXIS_DEFAULT = "auto"' in js, "缺 QB_YAXIS_DEFAULT(初值/坏值回落)"
    assert "QB_YAXIS_LIMIT_FACTOR = 1.2" in js, "缺限速倍率 1.2 单点"
    assert "QB_YAXIS_MIB = 1024 * 1024" in js, "缺手动值 MiB 换算单点"

    # 2. 值域 + 缺口游程 node 真跑(无 node 静默跳过)
    node = shutil.which("node")
    if node:
        proc = subprocess.run(
            [node, "-e", _NODE_QB_YAXIS_PROBE,
             os.path.join(shared, "qb_traffic_chart.js")],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        assert proc.returncode == 0, f"纵轴值域/缺口游程 node 电池跑挂: {proc.stderr.strip()}"
        rep = json.loads(proc.stdout.strip().splitlines()[-1])
        assert rep["failed"] == [], f"纵轴/缺口电池 {rep['ok']}/{rep['total']} 过, 失败: {rep['failed']}"

    # 3. 限速来源单点(三作用域同源): qB 全局限速上下行较大者
    lim = re.search(r"_qbGlobalLimit\(\) \{\n(.*?)\n    \},", js, re.S)
    assert lim, "缺 _qbGlobalLimit(全局限速单点)"
    lb = lim.group(1)
    assert "this.speedLimitBytes" in lb, "_qbGlobalLimit 必须取 speedLimitBytes 单点(与状态栏/速度染色同源)"
    # 2026-10-08 版式改后常驻说明区退役; D4 文案挂在统计栏悬浮说明单点(qbCurSummaryHint)
    assert "限速虚线 = 当时生效的 qB 全局限速" in js and "记录起点前不显示" in js, \
        "缺 D4 文案(限速线取值口径 + 记录起点前不显示, qbCurSummaryHint 单点)"
    assert "up" in lb and "down" in lb and "best" in lb, \
        "全局限速必须取上下行**较大者**(纵轴上下行共用一条, 取大者两条曲线都落在上限内)"

    # 4. 上限派生单点: limit = 全局限速×1.2 / manual = MiB 换算 / auto = 0(不固定)
    cap = re.search(r"_qbYCapOf\(scope\) \{\n(.*?)\n    \},", js, re.S)
    assert cap, "缺 _qbYCapOf(固定上限派生单点)"
    cb = cap.group(1)
    assert 'y.mode === "limit"' in cb and "* QB_YAXIS_LIMIT_FACTOR" in cb, "limit 模式必须 = 全局限速 ×1.2"
    assert 'y.mode === "manual"' in cb and "* QB_YAXIS_MIB" in cb, "manual 模式必须按 MiB 换算"

    # 5. 建图接线: y range 走纯函数 + 两钩子画注解层(共享图面)
    assert "y: { range: (u, dmin, dmax) => _qbYRange(dmax, this._qbYCapOf(scope)) }" in js, \
        "建图 y range 未接 _qbYRange/_qbYCapOf(固定上限不生效)"
    # S2-a 起钩子序即 I6 图层序(vendor 1.6.32 实证: drawAxes 在 Dl.axes 末尾 = 网格后、系列前):
    # drawClear = 斜纹(恒最底), drawAxes = 几何/N 层(网格后系列前), draw = 限速线 → 锚(系列之上)
    assert "drawClear: [(u) => this._qbDrawGaps(u, tk)]" in js, \
        "缺缺口斜纹 drawClear 钩子(恒最底, 与网格相互独立)"
    assert "drawAxes: [(u) => this._qbDrawFx(u, tk)]" in js, \
        "缺 fx 装饰段 drawAxes 钩子(网格之后、系列原生之前 —— 挂 drawClear 会被网格盖住, I6 层序)"
    assert "draw: [(u) => this._qbDrawLimits(u, tk), (u) => this._qbDrawFxAnchor(u, tk)]" in js, \
        "缺限速虚线 draw 钩子(画在系列之上; S2-a 起锚段紧随其后)"

    # 6. 重启缝提示(P4, plan 26-10-15-0829): 判据单点 + computed 消费单点 + 模板提示行
    #    (node 真跑在上面第 2 段电池里; 这里钉接线与文案单源)
    assert js.count("function _qbSeamHint") == 1, "缺/多 _qbSeamHint 判据定义(重启缝 vs 停机洞区分判据必须单点)"
    # 左端口径活性锚(issue 26-10-16-0954): 左端必须为「链末桶前一桶起点」而非链末桶覆盖端 —— 旧口径
    # 把「重启后首采已入账」形态静默漏判; 整行匹配, 改口径须同步 node 电池(判据语义由电池钉住)
    assert "if (started < chainPrevStart || started > rightEdge) return null;" in js, \
        "缺 重启缝判据左端行(chainPrevStart = 链末桶前一桶起点; 修订见 issue 26-10-16-0954)"
    seam_cmp = re.search(r"qbCurSeamHint\(\) \{\n(.*?)\n    \},", js, re.S)
    assert seam_cmp and "_qbSeamHint(d.points" in seam_cmp.group(1), \
        "缺 qbCurSeamHint computed(模板消费单点, 必须经 _qbSeamHint 判据)"
    assert 'v-if="qbCurSeamHint"' in drawer_tpl and "qb-seam" in drawer_tpl, \
        "drawer.html 缺重启缝提示行(数据接缝中, 三挂点共用正文块)"
    assert drawer_tpl.count("数据接缝中") == 1, "接缝文案必须单源(只此一处)"
    assert "fmtTime(qbCurSeamHint.startedAt)" in drawer_tpl, "接缝提示必须带服务重启时刻锚(fmtTime)"
    # 断线语义不变(P4 纪律): null 不连线与斜纹钩子原样, 提示只是追加状态行
    assert js.count("spanGaps: false") == 2, "断线语义不得变(spanGaps:false 上下载两系列都在)"
    for member in ("_qbCanvasScale(u)", "_qbDrawGaps(u, tk)", "_qbDrawLimits(u, tk)"):
        assert member in js, f"缺画布注解层成员 {member}"
    assert "uPlot.pxRatio" in js, "画布注解层必须按 uPlot.pxRatio 换算设备像素(uPlot ctx 无 transform)"
    dl = re.search(r"_qbDrawLimits\(u, tk\) \{\n(.*?)\n    \},", js, re.S)
    assert dl, "缺 _qbDrawLimits(限速虚线注解)"
    dlb = dl.group(1)
    # D4(plan 26-10-12-0535)分段化: 取值改图记录上的事件序列(不再读 speedLimitBytes 单值),
    # 段几何走纯函数, 可见性逐段(0 < v < ymax), 末段延伸到图右沿
    assert "u._qbLimits" in dlb, "_qbDrawLimits 必须取图记录上的限速事件序列(u._qbLimits, D4 分段)"
    assert "speedLimitBytes" not in dlb, "_qbDrawLimits 不得再读单点当前值(旧「单值画满整窗」回潮)"
    assert "_qbLimitSegs(" in dlb, "限速段必须走 _qbLimitSegs 纯函数(段几何 node 电池同源)"
    assert "seg.up < ymax" in dlb and "seg.down < ymax" in dlb, \
        "限速虚线可见性必须逐段判(每段每方向 0 < v < ymax)"
    assert "seg.up > 0" in dlb and "seg.down > 0" in dlb, "0(不限速)/缺值段不画"
    # 快路/建图两路都要把 limits 暂存在图记录上(否则限速变更要等整图重建才可见)
    assert js.count("prev._qbLimits =") == 1 and js.count("u._qbLimits =") == 1, \
        "limits 暂存必须同时接在 setData 快路(prev._qbLimits)与整图重建(u._qbLimits)两路"
    # D7: 悬停读数走纯函数 _qbLimitAt + 模板两支(正常/缺口)都接当时限速行
    assert "_qbLimitAt(d.limits || [], ts)" in js, "悬停读数必须走 _qbLimitAt(当时值, D7)"
    assert drawer_tpl.count('v-if="qbCurHover.lim"') == 2, \
        "当时限速行必须在正常/缺口两支 tooltip 各接一处(限速是时间真值, 缺口也读)"
    assert 'class="h-limit"' in drawer_tpl, "当时限速行缺 h-limit 类(样式挂点)"

    # 5b. 缺口斜纹**配色 + 几何**守阵(2026-10-08 两轮: 先修「颜色几乎不可分辨」, 再修「未落到
    # 正确区域 / 倾斜超出范围」)
    # 配色根因: 斜纹色原走 tk.grid = --hairline(装饰性 1px 发丝线令牌, 实测 alpha 仅 0.05~0.08),
    # 再叠 globalAlpha 0.5 ⇒ 有效不透明度约 3%, 深/亮底色上**都**等于没画。修法 = 专用高对比
    # 令牌 --qb-gap-hatch + 去掉多余的 globalAlpha 折半。
    # 几何根因(第二轮, 首轮曾误判为"颜色不可见导致无法判读落点"): 斜纹原只按底端 x 扫
    # [xa-H, xb+H] 再让外层 clip 收到**整个绘图区** —— 45 度线段水平跨度恒为 H, 并集是"宽 H 的
    # **斜向平行四边形**"(左右边界皆斜边), 缺口右段下半留白、左段上半越界到缺口左侧, 即用户报
    # 「未落到正确区域, 倾斜超出范围」。修法 = **逐 run 追加一次 clip 到缺口矩形**(见 _qbDrawGaps
    # 内「几何硬约束」注释), 斜纹被裁成以缺口区间为左右竖直边的竖矩形。
    gp = re.search(r"_qbDrawGaps\(u, tk\) \{\n(.*?)\n    \},", js, re.S)
    assert gp, "缺 _qbDrawGaps(缺口斜纹注解)"
    gb = gp.group(1)
    assert "ctx.strokeStyle = tk.gap || tk.grid;" in gb, \
        "缺口斜纹色必须走专用令牌 tk.gap(回退 tk.grid 兜底), 不得直用极低 alpha 的 tk.grid"
    assert "ctx.globalAlpha = 1;" in gb, \
        "缺口斜纹不得再叠 globalAlpha <1(--hairline 已是 0.055, 再砍半等于不可见)"
    assert "ctx.moveTo(x - H, T + H)" in gb and "ctx.lineTo(x, T)" in gb, \
        "斜纹线段必须为 (x-H, T+H) -> (x, T)(45 度, 右下角在 x)"
    assert "ctx.rect(L, T, W, H)" in gb and "ctx.clip()" in gb, \
        "缺口斜纹必须裁剪在绘图区内(两端超出部分不得越 y 轴/时间轴)"
    # 几何硬约束: 逐 run 裁到**缺口矩形** [xa, xb] x [T, T+H](把斜带裁成竖矩形)
    assert "ctx.rect(xa, T, xb - xa, H)" in gb, \
        "缺口斜纹必须逐 run 裁到缺口矩形 ctx.rect(xa, T, xb-xa, H) —— 否则 45 度斜带铺成" \
        "平行四边形: 缺口右段留白、斜边越出缺口带(用户报「未落到正确区域/倾斜超出范围」)"
    assert "if (!(xb > xa)) continue;" in gb, \
        "缺口宽度非正(退化 run)必须跳过, 不得画零宽/负宽矩形"
    tkb = re.search(r"_qbChartTokens\(\) \{\n(.*?)\n    \},", js, re.S)
    assert tkb, "缺 _qbChartTokens(建图令牌单点)"
    assert 'gap: pick("--qb-gap-hatch"' in tkb.group(1), \
        "建图令牌必须产出 gap = --qb-gap-hatch(缺口斜纹专用高对比令牌)"
    # 令牌各皮肤 + prism 五主题必须各自定义(缺一个就是那套皮肤下斜纹不可见; flux 收编 S5)
    for css, name in (
        (_ui_css_aggregate("atlas"), "atlas"),
        (_ui_css_aggregate("console"), "console"),
        (_ui_css_aggregate("prism"), "prism"),
        (_ui_css_aggregate("flux"), "flux"),
    ):
        assert "--qb-gap-hatch:" in css, f"{name} 皮肤缺 --qb-gap-hatch 令牌(缺口斜纹不可见)"
    for theme in ("ocean", "galaxy", "orbit", "frost", "golden"):
        tf = os.path.join(STATIC_ROOT, "prism", "css", "themes", f"{theme}.css")
        tt = open(tf, encoding="utf-8").read()
        assert "--qb-gap-hatch:" in tt, f"prism 主题 {theme} 缺 --qb-gap-hatch 令牌"
        # 亮主题必须用深墨色而非白色(白纹在白底/米底上等于无 —— 与深主题同式的镜面缺陷)
        if theme in ("frost", "golden"):
            hx = re.search(r"--qb-gap-hatch:\s*([^;]+);", tt).group(1)
            assert "255, 255, 255" not in hx, f"亮主题 {theme} 的斜纹色不得用白色(底纹不可见)"

    # 6. 持久化: 三作用域各自独立 + 键单点 + 初值校验 + 落盘吞异常 + 切档重排(不重取数)
    for scope, key in (
        ("global", "autoqb.ui.qbYAxisGlobal"), ("torrent", "autoqb.ui.qbYAxisTorrent"),
        ("group", "autoqb.ui.qbYAxisGroup")
    ):
        assert f'{scope}: "{key}"' in js, f"缺 {scope} 纵轴存储键(三作用域各自独立一份)"
    yk = re.search(r"function qbYAxisStoreKey\(scope\) \{\n(.*?)\n\}", js, re.S)
    assert yk and "QB_YAXIS_STORE_KEYS[scope]" in yk.group(1), "qbYAxisStoreKey 必须按 scope 单点分派"
    yi = re.search(r"function qbInitialYAxis\(scope\) \{\n(.*?)\n\}", js, re.S)
    assert yi, "缺 qbInitialYAxis(纵轴初值读取)"
    yib = yi.group(1)
    assert "localStorage.getItem(qbYAxisStoreKey(scope))" in yib and "QB_YAXIS_MODES.includes(v.mode)" in yib, \
        "初值必须读存储且只认合法模式(坏值回落默认)"
    assert "catch" in yib, "初值读取失败必须吞异常回落默认"
    ps = re.search(r"persistQbYAxis\(scope\) \{\n(.*?)\n    \},", js, re.S)
    assert ps and "localStorage.setItem(qbYAxisStoreKey(scope)" in ps.group(1) and "catch" in ps.group(1), \
        "persistQbYAxis 必须写键单点且吞写入异常(与 persistQbWindow 同纪律)"
    for sig in ("qbSetYAxisMode(mode)", "qbSetYAxisManual(v)"):
        blk = re.search(rf"{re.escape(sig)} \{{\n(.*?)\n    \}},", js, re.S)
        assert blk, f"缺 {sig}(纵轴切换入口)"
        bd = blk.group(1)
        assert "this.persistQbYAxis(s);" in bd and "this._qbChartRescale(s);" in bd, \
            f"{sig} 必须落盘 + 立即重排 y 轴(不改数据/不重建图, 重取数等于白拉一发)"
    rs = re.search(r"_qbChartRescale\(scope\) \{\n(.*?)\n    \},", js, re.S)
    assert rs and "u.setData([u.data[0], u.data[1], u.data[2]])" in rs.group(1), \
        "_qbChartRescale 必须走 setData 重算 scale(重跑 range 与 draw 钩子), 不重建图"
    # 限速随主轮询变化重排(mounted 注册; 全局 mixin 必须先按 this.drawer 守卫剔除假实例)
    assert "this._qbLimitUnwatch = this.$watch(() => this._qbGlobalLimit()" in js, \
        "缺限速变化重排 watcher(长窗轮询可夹到 600s, 不重排则固定上限迟迟不生效)"
    assert "if (!this.drawer) return;" in js, \
        "mounted 注册必须先按 this.drawer 守卫剔除 BaseTransition 假实例(全局 mixin 会注入它)"

    # 7. 作用域表三挂点各持 yaxis 字段(单一描述源)
    scopes = re.search(r"const _QB_SCOPES = \{\n(.*?)\n\};", js, re.S)
    assert scopes, "缺 _QB_SCOPES 作用域表"
    sb = scopes.group(1)
    for field in ('yaxis: "qbHistYAxis"', 'yaxis: "qbTorrentYAxis"', 'yaxis: "qbGroupYAxis"'):
        assert field in sb, f"_QB_SCOPES 缺 {field}(三挂点各自独立纵轴字段)"

    # 8. state.js 三字段按 scope 取初值 + computed 单点
    for field in (
        'qbHistYAxis: qbInitialYAxis("global")', 'qbTorrentYAxis: qbInitialYAxis("torrent")',
        'qbGroupYAxis: qbInitialYAxis("group")'
    ):
        assert field in state_js, f"state.js 缺 {field}(根选项显式建字段)"
    for comp in ("qbCurYAxis()", "qbYAxisMode()", "qbYAxisManual()"):
        assert comp in js, f"缺纵轴 computed {comp}"
    # 2026-10-16(用户动议): 工具条上限读数 qbYAxisCapText(「上限 …(全局限速 ×1.2)」)随 UI 移除,
    # computed 退役不得回潮(图面自解释, 不再要常驻读数)。
    assert "qbYAxisCapText" not in js, "qbYAxisCapText 已随 2026-10-16 上限字样移除退役, 不得回潮"

    # 9. 模板控件(2026-10-16 版式改: 三挂点统一落图下统计栏 .qb-statctl, 头部不再挂控件)
    # W3(计划 26-10-11-2106): 控件组收进 <aq-qb-ctl>(**唯一实现**), 故旧口径
    # 「三态 × 2 处 = 6」改为「实现里三态各一(3) + drawer.html 零复写 + 唯一挂点接它」——
    # 覆盖强度不降反升(单点强于同源): 谁把按钮抄回 drawer.html, 下面的 == 0 与挂点断言同时判红。
    # 26-10-20-2231(R23-B-17): 纵轴三态改 <aq-seg> —— 模板不再有 3 个按钮, 判据换成
    # 「模板一处接 qbYAxisTabs + 三档合法值与文案在 JS 单点各一份」: 覆盖强度不降(谁把档位
    # 写回模板, 下面的 count == 0 与 qbYAxisTabs 投影断言同时判红), 且「加一档要改几处」从
    # 3 处(清单/文案/模板)降到 2 处(清单/文案, 同域相邻)。
    assert head_tpl.count("qbSetYAxisMode(") == 0, \
        "<aq-qb-ctl> 不应手写纵轴三态按钮(应交 <aq-seg>, 清单单点在 qbYAxisTabs)"
    assert ':items="$root.qbYAxisTabs"' in head_tpl and ':on-pick="$root.qbSetYAxisMode"' in head_tpl, \
        "<aq-qb-ctl> 纵轴三态必须吃 qbYAxisTabs + 回调 qbSetYAxisMode"
    assert re.search(r"qbYAxisTabs\(\) \{\n\s*return QB_YAXIS_MODES\.map\(", js), \
        "qbYAxisTabs 必须投影自 QB_YAXIS_MODES(合法值仍只有一份清单)"
    assert drawer_tpl.count("qbSetYAxisMode(") == 0, \
        "drawer.html 仍手写纵轴按钮(复写回潮: 控件组只有 <aq-qb-ctl> 一份实现)"
    traffic_call = re.search(r'<aq-drawer-head v-if="drawerIsTraffic"[^>]*>(.*?)</aq-drawer-head>', drawer_tpl, re.S)
    assert traffic_call and '<aq-qb-ctl>' not in traffic_call.group(1), \
        "纵轴控件不得落在流量形态头部内(2026-10-16 版式改: 三挂点统一落图下统计栏)"
    assert 'class="qb-tools"' in head_tpl and 'class="qb-seg"' in head_tpl, \
        "<aq-qb-ctl> 缺纵轴控件本体(.qb-tools/.qb-seg)"
    # 9b. **结构**守阵(数类名探不到 wrapper): <aq-qb-ctl> 必须恰两根(.qb-tabs / .qb-tools), 无 wrapper。
    # 三皮肤 CSS 的 `.qb-statctl > .qb-tabs` / `.qb-statctl > .qb-tools` 与
    # `.hist-summary > .qb-statctl` 全是**直接子选择器**(2026-10-16 起统计栏是唯一挂点,
    # 头部侧的 `.drawer-head > .qb-*` 选择器已随挂点退役删除) —— 片段被包一层
    # (任何理由的容器)即全部静默失配(类名 count 不变, 观感错版)。Vue 3 片段不留 wrapper 元素,
    # 唯二会破坏它的就是源模板里自己写一个, 故此处在源文本上钉根数。
    ctl_roots = _tpl_top_level_tags(_tpl_body(head_tpl, "tpl-aq-qb-ctl"))
    assert len(ctl_roots) == 2, (
        f"<aq-qb-ctl> 必须是**多根**片段(恰两根), 实测 {len(ctl_roots)} 根 —— "
        "包 wrapper 会隔开 .qb-statctl > .qb-tabs 这些直接子选择器, "
        "三皮肤下控件错版且无报错(静默失效)"
    )
    assert [t for t, _ in ctl_roots] == ["div", "div"], \
        "<aq-qb-ctl> 两个根必须是 div(.qb-tabs 档位 / .qb-tools 纵轴)"
    ctl_classes = [a.get("class") for _, a in ctl_roots]
    assert ctl_classes == ["qb-tabs", "qb-tools"], \
        f"<aq-qb-ctl> 两根的类必须依序为 qb-tabs/qb-tools(直接子选择器按类名命中), 实测 {ctl_classes}"
    # 头部壳片段同理: 恰一个根 <header class="drawer-head">(两形态共用一处; 再长出第二个 = 复写回潮)
    head_roots = _tpl_top_level_tags(_tpl_body(head_tpl, "tpl-aq-drawer-head"))
    assert len(head_roots) == 1 and head_roots[0][0] == "header" \
        and head_roots[0][1].get("class") == "drawer-head", \
        f"<aq-drawer-head> 必须恰一个根 <header class=\"drawer-head\">(两形态共用的唯一头部壳), 实测 {head_roots}"
    assert "v-if=\"$root.qbYAxisMode === 'manual'\"" in head_tpl \
        and "$root.qbSetYAxisManual($event.target.value)" in head_tpl, \
        "<aq-qb-ctl> 手动模式必须给输入框且 @change 走 qbSetYAxisManual(经 $root 回调根实例)"
    # 2026-10-16(用户动议): 生效上限读数(qb-tools-hint / qbYAxisCapText)已随 UI 移除, 不得回潮。
    assert "qb-tools-hint" not in head_tpl and "$root.qbYAxisCapText" not in head_tpl, \
        "纵轴工具条的上限读数字样已移除(2026-10-16), 不得回潮"
    # 2026-10-09 第 2 轮: 种子「流量」页签同款控件组改落图下统计栏(.qb-statctl; 2026-10-16 起为唯一挂点)
    stat_hdr = drawer_tpl[drawer_tpl.index('class="hist-summary"'):drawer_tpl.index('种子详情形态正文(五页签)')]
    assert 'class="qb-statctl"' in stat_hdr and '<aq-qb-ctl></aq-qb-ctl>' in stat_hdr, \
        "纵轴/档位控件组必须落在图下统计栏 .hist-summary 内(2026-10-09 第 2 轮; 2026-10-16 起为唯一挂点; W3 起经 <aq-qb-ctl>)"

    # 10. CSS 各皮肤成对(纵轴控件 + 图下统计栏控件组版式; flux 收编 S5)
    for css, name in (
        (_ui_css_aggregate("atlas"), "atlas css 聚合"),
        (_ui_css_aggregate("console"), "console css 聚合"),
        (_ui_css_aggregate("prism"), "prism css 聚合"),
        (_ui_css_aggregate("flux"), "flux css 聚合"),
    ):
        for rule in (
            ".qb-tools {",
            ".qb-seg button.active",
            ".qb-yaxis-input",
            ".hist-summary > .qb-statctl {",
        ):
            assert rule in css, f"{name} 缺 {rule}(纵轴控件/图下统计栏控件组三套 UI 必须成对改)"
        # 2026-10-16(用户动议「统计栏未对齐」): 统计栏 .hist-summary 各子项必须**垂直居中**。
        # 判据: flex 默认 align-items:stretch 把纯文本读数(「窗口 N 桶」/上下载累计)拉到与
        # 控件组同高、文字贴顶(实测比中线高 3.7px), 而图例(.hs-leg)与控件组(.qb-statctl)
        # 自带 align-items:center 使内容居中 —— 三族文字因此落成三条线, 真浏览器量布局才现形
        # (类名/结构断言全绿)。三皮肤成对钉住, 只改一处即判红。
        assert re.search(r"\.hist-summary\s*\{[^}]*align-items:\s*center", css), \
            f"{name} 的 .hist-summary 缺 align-items:center(统计栏子项错行: 文本贴顶 vs 图例/控件居中)"


def test_frontend_qb_traffic_drawer_page_guard():
    r"""流量图抽屉的页面守卫(2026-10-06 修「qB 全局流量图错误地出现在设置页」)

    抽屉是 app 级 sticky 吸底的停靠面板(.drawer-dock), 而 drawerVisible 原先对流量形态无条件为真
    (口径「任意页可开」) —— 在设置页(整幅配置工作台, 自己的滚动容器铺满)面板会压住页面底部内容,
    看着像设置页自带的一块。四类**守不全就复发**的形态钉住:
    1. 可见性单点 drawerVisible: 两形态一律先挡非主内容页(page !== "groups"); **状态位不随切页翻**
       (面板 DOM 退场、抽屉状态保住 —— 回主内容页连数据/窗口选择一起回来 = 方案A W1 验收项);
    2. 轮询与建图的 active 同源守卫: 三挂点一律含 page 判据 —— 面板不在 DOM 还拉还画 = 对着空气取数
       (同 pitfalls/web-ui/dock-panel「停靠面板隐藏后轮询要随可见性收口」);
    3. 入口可达性: 状态栏按钮与全局快捷键(Ctrl+Backslash)任意页可达 —— openDrawerTraffic 必须先把页
       切回主内容页, 否则「点了没反应」(状态翻了、面板不在 DOM);
    4. 图的生命周期(state.js watch drawerVisible): Vue 的 v-if 拆装会**换掉建图宿主**, uPlot 的
       root/canvas 挂在被拆走的旧 .qb-chart-host 上且不自愈(要等下一拍轮询, 而间隔可能夹到 600s)
       ⇒ 症状「回主内容页后面板里有文字没图」—— 退场销毁图、进场补拉一发(_qbLoad 内含建图);
       种子详情支路(!s)的变体宿主回页重挂归 test_drawer_seed_reentry_variant_remount。
    5. 同目标幂等短路(2026-10-07 修「再按 Ctrl+\ 闪烁」): 抽屉已开着同一形态同一目标时重按入口
       (快捷键/状态栏钮)必须短路返回 —— 全量路径会把收图销毁 + 抽屉重建 + 首拉 loading 各闪一遍
       (pitfalls/web-ui/drawer-switch-flicker「快中间态本身就是闪」)。"""
    shared = os.path.join(STATIC_ROOT, "shared")
    js = open(os.path.join(shared, "qb_traffic_chart.js"), encoding="utf-8").read()
    state_js = open(os.path.join(shared, "state.js"), encoding="utf-8").read()
    drawer_js = read_shared("drawer.js")

    # 1. 可见性单点: 守卫在形态分支之前, 状态位不被改写
    vis = re.search(r"drawerVisible\(\) \{\n(.*?)\n    \},", drawer_js, re.S)
    assert vis, "drawer.js 缺 drawerVisible(面板可见性单点, 移动了就同步本守阵)"
    vb = vis.group(1)
    assert "if (!this.drawer.open) return false;" in vb, "抽屉可见性必须先挡 drawer.open"
    assert 'if (this.page !== "groups") return false;' in vb, \
        "drawerVisible 缺主内容页守卫(设置页会浮着一张不属于它的流量图/种子详情面板)"
    assert 'return this.viewMode === "torrents";' not in vb, \
        "种子详情不得再限种子视图(2026-10-08 计划 26-10-08-1217: 三视图共用面板, 成员行三视图同源)"
    assert re.search(r"^      return true;", vb, re.M), \
        "drawerVisible 末尾必须无条件 return true(过了主内容页守卫即显示; 形态分支已收归页面级)"
    assert "this.drawer.open = false" not in vb, \
        "可见性不得改写抽屉状态位(面板 DOM 退场 ≠ 关闭: 回主内容页状态还要回来)"

    # 2. 三挂点 active 同源守卫(轮询 tick / 建图判据同宽)
    scopes = re.search(r"const _QB_SCOPES = \{\n(.*?)\n\};", js, re.S)
    assert scopes, "qb_traffic_chart.js 缺 _QB_SCOPES 作用域表(三挂点单一描述源)"
    body = "\n" + scopes.group(1)  # 还原段首换行(正则捕获从 `  global: {` 起), 便于按段切分
    for scope in ("global", "group", "torrent"):
        seg = body.split("\n  %s: {" % scope)[1].split("stale:")[0]
        assert 'page === "groups"' in seg, \
            f"{scope} 挂点 active 缺主内容页守卫(面板已退场仍拉 /api/traffic/qb/* 且继续画不可见的图)"

    # 3. 入口可达(状态栏/快捷键任意页可达): 触发即切回主内容页
    op = re.search(r"async openDrawerTraffic\(scope, key\) \{\n(.*?)\n    \},", js, re.S)
    assert op, "qb_traffic_chart.js 缺 openDrawerTraffic(打开流量形态抽屉的单点)"
    ob = op.group(1)
    assert 'if (this.page !== "groups") this.page = "groups";' in ob, \
        "openDrawerTraffic 缺页面归一: 在设置页点状态栏入口/按 Ctrl+Backslash 会「点了没反应」"
    assert ob.index('this.page !== "groups"') < ob.index("this._stopDrawerPoll()"), \
        "页面归一必须在重置抽屉状态之前(切页会引发重排, 先于所有副作用)"

    # 5. 同目标幂等短路: 已开着同一形态同一目标(分组再比 key)时重按入口不重建(否则收图销毁+
    #    抽屉重建+首拉各闪一遍); 短路必须落在 _stopDrawerPoll 等副作用之前才算短路
    assert 'this.drawerIsTraffic' in ob and "this.qbGroupKey === key" in ob, \
        "openDrawerTraffic 缺同目标幂等短路: 再按 Ctrl+\\ 会把收图+重建+首拉各闪一遍(W6 起形态判据走单点)"
    assert ob.index('this.drawerIsTraffic') < ob.index("this._stopDrawerPoll()"), \
        "同目标短路必须在收图/重建副作用之前(落在后面 = 短路失效, 闪烁回归)"

    # 4. watch(drawerVisible): 退场销毁图 / 进场补拉重建(uPlot 宿主随 v-if 拆装被换掉)
    #    种子详情支路(!s)W7 恢复进场补挂($nextTick 等 aside 补进 DOM 再 _dtSync; 见
    #    test_drawer_seed_reentry_variant_remount 全套钉法, 此处只钉挂点存在)
    wt = re.search(r"drawerVisible\(v\) \{\n(.*?)\n    \},", state_js, re.S)
    assert wt, "state.js 缺 watch(drawerVisible)(换宿主后图不自愈 = 回页只剩文字)"
    wb = wt.group(1)
    assert "const s = this.qbCurScope;" in wb and "if (!s) {" in wb and "$nextTick(() => this._dtSync())" in wb, \
        "watcher 缺种子详情支路进场补挂(!s 分支 $nextTick -> _dtSync; W7 随变体层恢复)"
    assert "this._qbChartDestroy(s);" in wb and "this._qbReloadOnEnter(s);" in wb, \
        "drawerVisible watcher 必须退场销毁图 + 进场补拉重画(补拉内含 $nextTick 建图单点)"
    re_b = re.search(r"_qbReloadOnEnter\(scope\) \{\n(.*?)\n    \},", js, re.S)
    assert re_b, "qb_traffic_chart.js 缺 _qbReloadOnEnter(面板进场补拉单点)"
    rb = re_b.group(1)
    assert "this._qbLoad(scope);" in rb, "_qbReloadOnEnter 必须走 _qbLoad 单点(内含建图, 不另写请求)"
    assert 'this[def.loading]' in rb, \
        "_qbReloadOnEnter 缺在途不叠加守卫(打开路径已先发一发, 进场 watcher 会把首次请求翻倍)"


# node 单测探针(issue 26-10-16-0954 方案 #2; 2026-10-22 随轮询骨架改写): 加载真实 polling.js +
# qb_traffic_chart.js, 用**真骨架 + 真 _qbLoad** 驱动「在途悬挂」兜底路线 —— api 桩返回永不 settle 的
# promise(悬挂), 断言: 在途未悬挂照旧挡拍 / 悬挂(超阈值)放行且只留一条警告 / 补偿后重新计时故后续
# 照常挡拍 / 图不活跃与页面隐藏照旧跳过 / 停止后句柄摘除。无 node 静默跳过(同 _NODE_QB_TRAFFIC_PROBE)。
_NODE_QB_POLL_STALL_PROBE = r"""
const fs = require("fs");
global.window = {};
global.document = { hidden: false };
eval(fs.readFileSync(process.argv[1], "utf8"));   // polling.js(骨架)
eval(fs.readFileSync(process.argv[2], "utf8"));   // qb_traffic_chart.js
const P = window.AQB_POLL.methods;
const M = window.AQB_QB_TRAFFIC.methods;
const checks = [];
let tick = null;
global.setTimeout = (fn) => { tick = fn; return 1; };   // 捕获下一拍, 不真跑定时器
global.clearTimeout = () => {tick = null;};
const realNow = Date.now; let off = 0;
Date.now = () => realNow() + off;                       // 可控时钟: 免得真睡 30s
const warns = [];
console.warn = (...a) => { warns.push(a.join(" ")); };
const mk = (over) => {
  const t = Object.assign({
    qbTrafficOn: true,
    drawerIsTraffic: true,
    drawer: { open: true, scope: "global" },
    page: "groups",
    qbHistData: { meta: { interval_s: 30 } },
    qbHistLoading: false,
    apiCalls: 0,
  }, over || {});
  t.api = () => { t.apiCalls += 1; return new Promise(() => {}); };  // 悬挂: await 永不返回
  t.startPoll = P.startPoll;
  t.stopPoll = P.stopPoll;
  t._qbPollStop = M._qbPollStop;
  t._qbPollMs = M._qbPollMs;
  t._qbLoad = M._qbLoad;
  return t;
};
const run = (t) => { M._qbPollStart.call(t, "global"); tick(); };
// 1. 在途未悬挂(刚置位): 照旧挡拍(骨架记下计时起点后 mutex 挡住)
off = 0;
let t = mk({ qbHistLoading: true });
run(t);
checks.push(["在途未悬挂照旧挡拍", t.apiCalls === 0 && warns.length === 0]);
// 2. 悬挂(起点记下后时钟跳过 60s): 放行 + 一条警告; 补偿后重新计时 => 后续拍照常挡、警告只一条
warns.length = 0;
t = mk({ qbHistLoading: true });
run(t);          // 第一拍只记起点
off = 60000;     // 时钟跳过阈值
tick();
checks.push(["悬挂放行(强制续拉)", t.apiCalls === 1 && warns.length === 1 && t.qbHistLoading === true]);
for (let i = 0; i < 5; i++) tick();
checks.push(["补偿后重新计时: 后续照常挡拍且警告只一条", t.apiCalls === 1 && warns.length === 1]);
// 3. 图不活跃(切走页面) / 页面隐藏: 照旧跳过(兜底不越界)
t = mk({ qbHistLoading: true, page: "settings" });
run(t);
checks.push(["图不活跃跳过", t.apiCalls === 0]);
global.document.hidden = true;
t = mk({ qbHistLoading: true });
run(t);
checks.push(["页面隐藏跳过", t.apiCalls === 0]);
global.document.hidden = false;
// 4. 停止收口: _qbPollStop 后句柄从表里摘掉(不再有拍)
t = mk({ qbHistLoading: false });
run(t);
t._qbPollStop("global");
checks.push(["停止后句柄摘除", !t._polls["qb:global"]]);
console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
"""


def test_frontend_qb_traffic_load_stall_fallback():
    """流量图轮询「在途悬挂」兜底守阵(issue 26-10-16-0954-bug-webui-chart-fetch-no-timeout 方案 #2)

    故障链(2026-10-16 复验实测): loading 是单向「请求在途」标志 —— `_qbLoad` 入口无条件置 true,
    唯一复位路径是它的 finally; 请求悬挂时 finally 不执行 ⇒ 轮询 tick 的守卫(`this[def.loading]`)
    把之后每一拍都挡掉, 图表永久停在旧帧、无提示也不自愈(10-12 修的是同链另一入口: stale 谓词取反)。

    2026-10-22(issue 26-10-20-2231-refactor-fe-polling-family-dup): 兜底随轮询生命周期收进
    polling.js 骨架, 阈值常量上提为 `AQB_POLL_STALL_MS`(抽屉侧自此同口径 —— 此前同一类卡死只修了
    流量图一边)。本守阵改钉三层, 任一层被拆即红:
      1. 阈值常量 `AQB_POLL_STALL_MS` 在 polling.js(30000 = 请求级超时 15s 的两倍余量);
      2. 流量侧**声明**齐全: `stall: () => this[_QB_SCOPES[scope].loading]` + `mutex: true`
         (合体式早退 `document.hidden || this[def.loading]` 不得回潮 —— 那正是本 issue 的成因形态);
      3. 抽屉侧必有同口径兜底(`stall` + `onStall`), 否则「同一类卡死只修一边」复发。
    行为面走 node 电池真跑(无 node 静默跳过): 真骨架 + 真 `_qbLoad` + 永不 settle 的 api 桩。
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    js_path = os.path.join(shared, "qb_traffic_chart.js")
    store_path = os.path.join(shared, "drawer_store.js")
    poll_path = os.path.join(shared, "polling.js")
    js = open(js_path, encoding="utf-8").read()
    store_js = open(store_path, encoding="utf-8").read()
    poll_js = open(poll_path, encoding="utf-8").read()

    m = re.search(r"^const AQB_POLL_STALL_MS = (\d+);", poll_js, re.M)
    assert m, "polling.js 缺 AQB_POLL_STALL_MS 常量(悬挂兜底阈值, 骨架单点)"
    assert int(m.group(1)) == 30000, \
        "兜底阈值应 = 请求级超时(15s)的两倍余量 30000 —— 改它必须同步本守阵与常量注释里的依据"
    assert "document.hidden || this[def.loading]" not in js, \
        "tick 跳过判据回潮成 loading 合体式 —— loading 卡死即永久挡拍(issue 26-10-16-0954 的成因)"
    assert "stall: () => this[_QB_SCOPES[scope].loading]," in js and "mutex: true," in js, \
        "流量轮询缺在途悬挂兜底声明(stall)或在途互斥(mutex)"
    # 抽屉侧同口径(2026-10-22 补的实质缺陷面): 卡死判据 + 补偿动作都在, 否则面板仍可能永久冻结
    dp = re.search(r"_startDrawerPoll\(\) \{\n(.*?)\n    \},", store_js, re.S)
    assert dp, "drawer_store.js 缺 _startDrawerPoll(结构漂移? 同步本守阵)"
    assert "stall: () => this._drawerPollStuck()," in dp.group(1) and "onStall:" in dp.group(1), \
        "抽屉页签轮询缺悬挂兜底声明 —— 同一类卡死只修了流量图一边(issue 26-10-20-2231 的实质缺陷面)"

    node = shutil.which("node")
    if node:
        proc = subprocess.run(
            [node, "-e", _NODE_QB_POLL_STALL_PROBE, poll_path, js_path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert proc.returncode == 0, f"悬挂兜底 node 电池跑挂: {proc.stderr.strip()}"
        report = json.loads(proc.stdout.strip().splitlines()[-1])
        assert report["failed"] == [], \
            f"悬挂兜底电池 {report['ok']}/{report['total']} 过, 失败: {report['failed']}"


# R5#192: x 轴刻度四族 + 孤点索引三态(同文件其余纯函数均有 node 电池, 唯这两处一直零执行)。
# _qbTickLabel 是 methods 上的方法(消费 this[_QB_SCOPES[scope].window]) —— 经导出面真跑;
# _QB_WINDOW_NAMES/_QB_SCOPES 是模块级 const 不随 sloppy eval 外泄, 用 new Function 取出(同
# _NODE_QB_SCOPE_STALE_PROBE 口径); _qbIsolatedIdxs 是顶层 function 声明, eval 后可直接取用。
_NODE_QB_TICK_ISOLATED_PROBE = r"""
const fs = require("fs");
global.window = {};
const src = fs.readFileSync(process.argv[1], "utf8");
eval(src);
const M = window.AQB_QB_TRAFFIC.methods;
const CST = new Function(src + "\nreturn { WN: QB_WINDOW_NAMES, SCOPES: _QB_SCOPES };")();
const checks = [];
const ok = (n, c) => checks.push([n, !!c]);
const p2 = (n) => String(n).padStart(2, "0");
const ts = 1767225600;  // 任意固定时刻; 期望值按同一 Date 本地时区现算, 与机器时区无关
const d = new Date(ts * 1000);
// 四族期望(与 _qbTickLabel 的分支一一对应; 错档 = 族与 QB_WINDOW_NAMES 对应写错, 这里逐档钉死)
const SEC = `${p2(d.getHours())}:${p2(d.getMinutes())}:${p2(d.getSeconds())}`;
const TIME = `${p2(d.getHours())}:${p2(d.getMinutes())}`;
const DATE = `${p2(d.getMonth() + 1)}-${p2(d.getDate())}`;
const MONTH = `${d.getFullYear()}-${p2(d.getMonth() + 1)}`;
const FAM = {
  "1m": SEC, "5m": SEC,
  "30m": TIME, "3h": TIME, "6h": TIME, "12h": TIME, "24h": TIME,
  "3d": DATE, "7d": DATE, "30d": DATE,
  "6mo": MONTH, "1y": MONTH, "all": MONTH,
};
ok("QB_WINDOW_NAMES 恰 13 档", CST.WN.length === 13 && CST.WN.every((w) => FAM[w] !== undefined));

const vm = { qbHistWindow: "24h", qbTorrentWindow: "24h", qbGroupWindow: "24h" };
for (const w of CST.WN) {
  vm.qbHistWindow = w;
  ok(`刻度 ${w} -> ${FAM[w]}`, M._qbTickLabel.call(vm, ts, "global") === FAM[w]);
}
// 三挂点窗口互不串: torrent 挂点读自己的窗口字段(换 global 的档不影响)
vm.qbHistWindow = "24h";
vm.qbTorrentWindow = "3d";
ok("torrent 挂点读 qbTorrentWindow(作用域窗口不串)", M._qbTickLabel.call(vm, ts, "torrent") === DATE);

// _qbIsolatedIdxs 三态(u.data = [xs, up, dl]; 断言走 up 列)
const iso = (up) => _qbIsolatedIdxs({ data: [up.map((_, i) => i), up, up] }, 1);
ok("孤点(两侧皆 null): 收点标", JSON.stringify(iso([null, 5, null, null, 7, 7, null])) === "[1]");
ok("链中/链端(任一侧非 null): 不收", JSON.stringify(iso([null, 5, 6, 7, null])) === "[]");
ok("贴边孤点(一侧出界视作 null): 收", JSON.stringify(iso([5, null, 7])) === "[0,2]");
ok("单元素系列: 收(零长线段不可见, 靠点标可见)", JSON.stringify(iso([9])) === "[0]");
ok("空系列: 空", JSON.stringify(iso([])) === "[]");
console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
"""


def test_frontend_qb_tick_label_and_isolated_idxs():
    """R5#192: _qbTickLabel 四族 13 档逐档 + _qbIsolatedIdxs 三态 node 电池(无 node 静默跳过)"""
    shared = os.path.join(STATIC_ROOT, "shared")
    node = shutil.which("node")
    if not node:
        return
    proc = subprocess.run(
        [node, "-e", _NODE_QB_TICK_ISOLATED_PROBE,
         os.path.join(shared, "qb_traffic_chart.js")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0, f"刻度/孤点 node 电池跑挂: {proc.stderr.strip()}"
    report = json.loads(proc.stdout.strip().splitlines()[-1])
    assert report["failed"] == [], \
        f"刻度/孤点电池 {report['ok']}/{report['total']} 过, 失败: {report['failed']}"


def test_frontend_qb_themechange_event_pair():
    """R5#194(+R5#180): theme.js 与 qb_traffic_chart.js 的换肤事件契约成对静态锚

    事件契约: prism 主题引擎在主题变化处派发 ``autoqb:themechange``(documentElement 上),
    流量图监听同名事件整图重建(canvas 色建图时烘焙令牌值, setData 快路不换色)。
    theme.js 全文件此前零测试 —— 事件名/派发点被改名或删除时, 换肤残旧色且无测试变红。
    成对断言: 派发侧两路(手动 set + 系统明暗跟随 onSys)与监听侧一落点, 任何一侧缺失/
    改名/换 target 即红。
    """
    theme_js = open(os.path.join(STATIC_ROOT, "prism", "js", "theme.js"), encoding="utf-8").read()
    chart_js = open(os.path.join(STATIC_ROOT, "shared", "qb_traffic_chart.js"), encoding="utf-8").read()

    # 派发侧: 手动切换 set() 与系统跟随 onSys() 两路都派发, 且都落在 documentElement
    set_blk = re.search(r"set: function \(id\) \{(.*?)\n    \},", theme_js, re.S)
    assert set_blk and 'document.documentElement.dispatchEvent' in set_blk.group(1) \
        and 'CustomEvent("autoqb:themechange"' in set_blk.group(1), \
        "theme.js set(手动切换)必须在 documentElement 上派发 autoqb:themechange(流量图换肤重建契约)"
    onsys_blk = re.search(r"var onSys = function \(\) \{(.*?)\n    \};", theme_js, re.S)
    assert onsys_blk and 'document.documentElement.dispatchEvent' in onsys_blk.group(1) \
        and 'CustomEvent("autoqb:themechange"' in onsys_blk.group(1), \
        "theme.js onSys(系统明暗跟随)必须在 data-theme 实际变化时派发 autoqb:themechange" \
        "(R5#180: 只 apply 不派发 = OS 切明暗后流量图 canvas 残旧主题)"
    assert theme_js.count('CustomEvent("autoqb:themechange"') == 2, \
        "theme.js 派发点应恰两处(set + onSys); 增删派发路须同步本守阵"

    # 监听侧: 流量图监听同名事件, 且挂在同一 target(documentElement) —— 换 target 即收不到
    assert 'document.documentElement.addEventListener("autoqb:themechange"' in chart_js, \
        "qb_traffic_chart.js 必须监听 autoqb:themechange(派发在 documentElement, 挂别处收不到)"
    on_change = re.search(r"_qbOnThemeChange = \(\) => \{\n(.*?)\n        \};", chart_js, re.S)
    assert on_change and on_change.group(1).find("this._qbChartDestroy(s)") \
        < on_change.group(1).find("this._qbChartBuild(s)"), \
        "换肤处理器必须先 _qbChartDestroy 再 _qbChartBuild(canvas 色建图时烘焙, setData 快路不换色)"

    # 卸载对称(池条目 R5#181): beforeUnmount 内必须按同一引用摘监听并复位 _qbThemeBound,
    # 只挂不摘则 documentElement 持 mixin 实例引用一起泄漏(静态锚: 成对 API + 复位同在卸载点)
    unmount_blk = re.search(r"beforeUnmount\(\) \{(.*?)\n  \},", chart_js, re.S)
    assert unmount_blk, "qb_traffic_chart.js 必须有 beforeUnmount 卸载钩子"
    ub = unmount_blk.group(1)
    assert 'document.documentElement.removeEventListener("autoqb:themechange", this._qbOnThemeChange)' in ub \
        and "_qbThemeBound = false" in ub, \
        "beforeUnmount 必须对称摘除 autoqb:themechange 监听(removeEventListener + _qbThemeBound 复位)"
