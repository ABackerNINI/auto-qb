"""test_webui_static_dom_panel_traffic_wiring 测试计划: webui 前端静态守阵: 详情面板 / 弹窗 / 浮层

原 test_webui_static_dom_panel_traffic.py 按域拆分(move-only, 2026-11-27); 测试 ID/名称/断言零变化。

## 测试计划(每个测试函数一条)
- test_frontend_qb_traffic_chart_wiring: qB 口径流量图前端接线守阵(P5a+P5b, plan 26-10-03-0946 §07; 契约适配 26-11-18-0037 阶段 3) —— enabled=false 三挂点入口不渲染不请求(全局入口按钮 v-if="qbHistEntryOn" / 抽屉流量页签与组右键菜单项 v-if="qbTrafficOn", 门在 flags.qb_traffic_enabled, /api/webui/flags 下发 fail-closed)+ uPlot 双系列 spanGaps=false 断线不连线 + 点列->_qbPointsToData 直读 node 真跑(schema=2 样本分组点列每点带 t 直读(非等距真值 t/float 组距)/显式空值点 {t, dl:null, up:null} y=null 断线/尾组最新样本 ts 恒真值/anchor={xs} 全列真值时刻/空列与 interval 非法回落; agg 段窗旧「桶值|null」定长数组兼容面保留(D4 零改动): null 槽栅格重建/前导 null 推算/S3b 月行真值落点与空槽内插) + 轮询下界常量 1500(A4, S3b §05.5)+ 三挂点作用域表与低频轮询口径(sample_interval_s 夹取全窗统一(F7/26-11-15-1104 D6 反转旧「低频轮询=桶宽」口径) + immediate 首拍立即(F8/D4) + document.hidden 跳过 + 关闭/切走 clearInterval)+ 静默续拉(loading 空态只在「尚无落袋结果」时接管正文(qbCurPending = loading + 无数据 + 无错误) + 同宿主 setData 原地快路 + 换肤先销毁再重建 + 错误态由成功落袋清除, 2026-10-04 修轮询期闪烁 / 2026-10-05 补齐空态与错误态闪烁)+ FX-29 软切换落定登记(_qbLoad 落袋 _drawerDone("traffic") 与 _drawerWaitSources 成对, 2026-10-04 修流量页签单击换行遮罩挂死)+ 三主题登记链(tpl/vendor/mixin/manifest)+ escBusy 与 Esc 退栈链同步(含退栈顺序: 历史弹层遮罩 130 先于抽屉 80, 2026-10-06 两图同开报障)+ 建图后宿主 ResizeObserver 自适应与销毁断开(便签 26-10-04-0134)+ 缺口三态文案与空态钉住(P4, plan 26-10-04-0721 §05: 0 桶状态行/缺口合并文案/图例 hint 两处/单种空态收窄为从未传输 + node 三段混排回归(显式空值点形态)); T4a(plan 26-11-18-0037)追钉: openDrawerTraffic 打开路径改首拉 + _qbStreamStart(SSE 主路径, GET 轮询骨架退役为降级态取数)/drawer_store 流量页签同改 + _stopDrawerPoll 同收流; 名义窗头部修剪纯函数 _qbTrimStaleHead node 电池(2026-11-21, 修「SSE 步进列只增尾不剪头 -> auto range 跨度变宽 -> 整列 x 向压缩 + L0 min 恒驻左端不出窗」): 陈旧头部点按 尾t-span_s 剪除(修剪线含界 t>=line 保留)/纯函数不 mutate 入参(落地面在 _qbStreamFrame 数据入口面 —— store 列与显示列恒对齐, 悬停取值零错位; 见 SSE 电池 A7)/fresh 列与 span 覆盖全列原引用返回/列尾点恒存活不剪空/span_s 非法(0/负/缺参)与旧契约 null 元素(无 t 即停)防御
- test_frontend_qb_traffic_window_persist_and_single_source: 流量图「视图选择」持久化 + 窗口档位单点(2026-10-05) —— QB_WINDOW_NAMES 十三档与后端 traffic_qb.WINDOW_NAMES 逐字一致, 为展示(模板 v-for 走 qbWindowNames)/前后切换(qbCycleWindow)/持久化校验(qbInitialWindow)三处唯一来源(任一处硬编码即与后端 400 校验漂移); 持久化粒度 = 全局单独(autoqb.ui.qbWinGlobal)/组与种子共用(autoqb.ui.qbWinShared), 键按 scope 单点分派, 初值只认合法档位且坏值回落默认, 换窗即落盘并吞写入异常; 初值函数在 qb_traffic_chart.js 且全部皮肤(_UI_ALL)的 tpl-manifest 里排在 state.js 之前(否则 state data() 调它未定义 = 启动白屏); R8 追加 state.js 数值面板接线静态钉(fx: qbInitialFx() / fxPanel 显式建字段, plan 26-11-12-1139 §05.5), 修复轮追加状态行展示值 computed 落位钉(qbFxPeriodS/qbFxBeatMs 恰 1 次定义且夹在 computed: { 与 mounted() { 之间, fx-panel.html 保持裸插值不带括号 —— 落 methods 即复现 toDisplayString 函数源码渲染 blocker)
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

from webui_dom_panel_support import _NODE_STDIN_WRAPPER

# node 单测探针(P5a): 加载真实 qb_traffic_chart.js, 对模块级纯函数 _qbPointsToData 跑
# 点列直读 + 断线语义电池(26-11-18-0037 阶段 3 契约适配: schema=2 样本分组点列每点带 t 直读
# / 显式空值点 y=null / 变长真值 t / 空列与 interval 非法防御; agg 段窗旧「桶值 | null」定长
# 数组(D4 零改动)兼容面保留 —— null 槽内插/外推/月行真值落点)。无 node 静默跳过(同
# _scan_js_syntax_with_node 口径)。
_NODE_QB_TRAFFIC_PROBE = r"""
const fs = require("fs");
global.window = {};
eval(fs.readFileSync(process.argv[1], "utf8"));
const P = (t, up, dl) => ({ t, up, dl });
const G = (t) => ({ t, dl: null, up: null });   // schema=2 显式空值点(缺口标记)
const checks = [];
// —— schema=2 样本分组契约(26-11-18-0037 §03): 每点必带 t, 三列直读 ——
let pts = [P(1000, 1, 2), P(1015, 3, 4), P(1031, 5, 6)];
let d = _qbPointsToData(pts, 15);
checks.push(["点列直读 xs = 真值 t(非等距也按真值, 等距重建机器退役)",
  !!d && JSON.stringify(d.xs) === "[1000,1015,1031]"]);
checks.push(["点列直读值透传", !!d && d.up.join() === "1,3,5" && d.dl.join() === "2,4,6"]);
pts = [P(1000, 1, 2), G(1015), P(1030, 5, 6)];
d = _qbPointsToData(pts, 15);
checks.push(["显式空值点 x = 自带真值 t(缺口 = 折叠点, 位置不漂移)",
  !!d && JSON.stringify(d.xs) === "[1000,1015,1030]"]);
checks.push(["显式空值点 y=null(spanGaps=false 断线)", !!d && d.up[1] === null && d.dl[1] === null]);
checks.push(["尾组 = 最新样本 ts 恒真值点", !!d && d.xs[2] === 1030 && d.up[2] === 5]);
checks.push(["anchor = { xs } 全列真值时刻(悬停取值锚)", !!d && d.anchor.xs[1] === 1015
  && d.anchor.xs.length === 3 && d.anchor.k === undefined && d.anchor.t0 === undefined]);
// 变长点列(相位 ±1 + 缺口标记)与 float 组距: 契约只增, 直读对算术面无取整假设
pts = [P(1000.5, 1, 2), G(1002), P(1003, 3, 4)];
d = _qbPointsToData(pts, 1.5);
checks.push(["float 组距 + 缺口点真值直读", !!d && JSON.stringify(d.xs) === "[1000.5,1002,1003]"
  && d.up[1] === null]);
pts = [P(1000, 1, 2), G(1015)];
d = _qbPointsToData(pts, 15);
checks.push(["尾点即缺口点(断连尾面)照实直读", !!d && JSON.stringify(d.xs) === "[1000,1015]"
  && d.up[1] === null && d.dl[1] === null]);
checks.push(["空列回落(后端已归一 [])", _qbPointsToData([], 30) === null]);
checks.push(["interval 非法回落", _qbPointsToData([P(1, 1, 1)], 0) === null]);
// P4 回归(plan 26-10-04-0721 §07): 停机/断连 = 显式空值点(spanGaps:false 如实断线);
// 空闲 = (0,0) 真实观测点(0 平线, 不是缺口) —— 三段混排(活跃/缺口/空闲/活跃)一次钉住
pts = [P(1000, 5, 6), G(1030), G(1045), P(1090, 0, 0), P(1120, 0, 0), G(1150), P(1180, 2, 3)];
d = _qbPointsToData(pts, 15);
checks.push(["三段混排 xs 全按真值 t", !!d && JSON.stringify(d.xs) === "[1000,1030,1045,1090,1120,1150,1180]"]);
checks.push(["停机/断连显式空值点 y=null(如实断线)",
  !!d && d.up[1] === null && d.up[2] === null && d.up[5] === null && d.dl[5] === null]);
checks.push(["空闲段 (0,0) 是观测点不成缺口",
  !!d && d.up[3] === 0 && d.up[4] === 0 && d.dl[3] === 0 && d.dl[4] === 0]);
checks.push(["三段混排活跃值透传", !!d && d.up[0] === 5 && d.up[6] === 2 && d.dl[6] === 3]);
// —— agg 段窗旧契约兼容面(D4 零改动): 「桶值 | null」定长数组, null 槽无 t 走栅格重建 ——
pts = [P(1000, 1, 2), null, P(1060, 5, 6)];
d = _qbPointsToData(pts, 30);
checks.push(["旧契约 null 槽 x 栅格重建(缺口位置不漂移)", !!d && JSON.stringify(d.xs) === "[1000,1030,1060]"]);
checks.push(["旧契约 null 槽 y=null", !!d && d.up[1] === null && d.dl[1] === null]);
pts = [null, P(1030, 3, 4), null, P(1090, 7, 8)];
d = _qbPointsToData(pts, 30);
checks.push(["旧契约前导 null 整列重建", !!d && JSON.stringify(d.xs) === "[1000,1030,1060,1090]"]);
checks.push(["旧契约前导/中断 null y=null", !!d && d.up[0] === null && d.up[2] === null && d.up[3] === 7]);
checks.push(["旧契约全 null 回落", _qbPointsToData([null, null], 30) === null]);
// S3b 月视图(plan 26-10-04-1957 §05.3): month 行按行间隔 28-31 天非等距 —— 非 null 点
// 按真值 t 落点, null 槽在两真值点间线性内插; anchor.xs 供 tooltip 真值
const jan = 1735689600, feb = 1738368000, mar = 1740787200;  // 2025-01/02/03-01(31d/28d)
pts = [P(jan, 1, 2), P(feb, 3, 4), P(mar, 5, 6)];
d = _qbPointsToData(pts, 2592000);
checks.push(["月行真值 x 落点(按行间隔非等距)", !!d && JSON.stringify(d.xs) === JSON.stringify([jan, feb, mar])]);
checks.push(["anchor.xs 悬停真值", !!d && d.anchor.xs[2] === mar]);
pts = [P(jan, 1, 2), null, P(mar, 5, 6)];
d = _qbPointsToData(pts, 2592000);
checks.push(["月视图空槽真值内插", !!d && d.xs[1] === (jan + mar) / 2 && d.up[1] === null]);
checks.push(["月视图值透传", !!d && d.up[0] === 1 && d.dl[2] === 6]);
// —— 名义窗头部修剪 _qbTrimStaleHead(2026-11-21; SSE 步进列左缘锚 = 尾t - span_s)——
let tr = [P(940, 1, 1), P(1000, 2, 2), P(1030, 3, 3)];
let trCut = _qbTrimStaleHead(tr, 60);   // 修剪线 = 1030-60 = 970: P(940) 陈旧
checks.push(["陈旧头部点按名义窗剪除(xs[0] 前移到修剪线右侧首点)", !!trCut && trCut.length === 2
  && trCut[0].t === 1000 && trCut[1].t === 1030]);
checks.push(["修剪返回新数组, 入参列零改写(纯函数不 mutate)", trCut !== tr && tr.length === 3]);
checks.push(["恰在修剪线上的点保留(t >= line 含界)", _qbTrimStaleHead([P(970, 1, 1), P(1030, 2, 2)], 60)[0].t === 970]);
const fresh = [P(1000, 1, 1), P(1030, 2, 2)];
checks.push(["fresh 列(全部点 >= 修剪线)原引用返回(零拷贝零重建)", _qbTrimStaleHead(fresh, 60) === fresh]);
checks.push(["span 覆盖全列跨度(短窗大 span)不剪", _qbTrimStaleHead([P(1000, 1, 1), P(1030, 2, 2)], 300)[0].t === 1000]);
checks.push(["列尾点恒存活(修剪线由尾点定义, 列不剪空)", _qbTrimStaleHead([P(100, 1, 1), P(200, 2, 2), P(1030, 3, 3)], 60).length === 1]);
checks.push(["span_s 非法(0/负/缺参)不剪(旧后端/agg 段窗门)", (() => {
  const a = [P(100, 1, 1), P(1030, 2, 2)];
  return _qbTrimStaleHead(a, 0) === a && _qbTrimStaleHead(a, -5) === a && _qbTrimStaleHead(a, undefined) === a;
})()]);
checks.push(["旧契约 null 元素防御(无 t 即停, 不越界剪)", (() => {
  const a = [null, P(1030, 2, 2)];
  const r = _qbTrimStaleHead(a, 60);
  return r.length === 2 && r[0] === null && r[1].t === 1030;
})()]);
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
      menu.key 的 encode_group_key 通道(不自行编码); 轮询三挂点统一: 间隔从
      meta.sample_interval_s 夹取(F7/26-11-15-1104 D6 起读生效采样间隔全窗统一; 旧口径
      interval_s=桶宽, [15s,600s] 夹到上界保续拉的形态已反转) + document.hidden 跳过
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
    # 入口按钮: v-if 门 + 面板内并列(TM 历史入口同组)。类名自 S6(计划 26-11-14-0041)起带
    # 键帽挂点类(.aq-kbd-host 角标定位 + .sb-top/.sb-left 栏顶空带落位) —— 断言按前缀匹配, 别再写死整串
    assert 'v-if="qbHistEntryOn"' in statusbar and re.search(r'class="sb-qb\b', statusbar), \
        "statusbar 缺 qB 入口按钮(v-if 门是 P5 验收的静态锚)"
    today_blk = re.search(r'<template v-if="todayTraffic">(.*?)</template>', statusbar, re.S)
    assert today_blk and re.search(r'class="sb-qb\b', today_blk.group(1)), \
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
            [node, "-e", _NODE_STDIN_WRAPPER,
             os.path.join(shared, "qb_traffic_chart.js")],
            input=_NODE_QB_TRAFFIC_PROBE,
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
    assert 'tab === "traffic" && this.qbTrafficOn' in store_js and 'this._qbStreamStart("torrent")' in store_js, \
        "drawer_store.js _loadDrawerTab 缺流量页签分支(加载 + 起 SSE 流; W1 起取数在数据层; T4a 起主路径为流)"
    assert 'this._qbPollStop("torrent")' in store_js and 'this._qbStreamStop("torrent")' in store_js, \
        "drawer_store.js _stopDrawerPoll 缺流量轮询/流收口(关抽屉/切页签/换目标全走这里 = 关闭即停; W1 起在数据层)"
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
    assert 'this._qbLoad(scope);' in js and 'this._qbStreamStart(scope);' in js, \
        "openDrawerTraffic 缺打开拉取 + 起 SSE 流(T4a: 主路径为流 + 30s 对账; GET 轮询骨架保留为降级态取数)"
    assert 'if (!this.qbTrafficOn || !key) return;' in js, "openQbGroup 缺 fail-closed 兜底门(入口 v-if 之外的加载路径)"
    # 低频轮询(§07; F7/26-11-15-1104 D6 起读 meta.sample_interval_s 生效采样间隔全窗统一,
    # 「低频轮询=桶宽」旧口径反转): [1.5s,600s] 夹取(配置校验界, A4 下界对齐 v3 采样间隔放宽
    # 后的真实下界; 上界自此纯防御) + 30s 兜底(缺键/非法 —— 旧缓存降级响应) + document.hidden
    # 跳过(对齐 drawer.js _startDrawerPoll 先例) + 关闭路径显式 clearInterval
    assert "_QB_POLL_FALLBACK_MS = 30000" in js and "_QB_POLL_MIN_MS = 1500" in js and "_QB_POLL_MAX_MS = 600000" in js, \
        "轮询间隔常量漂移(30s 兜底 / [1.5s,600s] 夹取界 = §06 配置校验边界, A4: 15000 -> 1500)"
    assert "Number(d && d.meta && d.meta.sample_interval_s)" in js, \
        "轮询节奏必须读 meta.sample_interval_s(F7/D6 全窗统一 —— 读回 interval_s(桶宽)即旧口径回潮)"
    assert "Math.min(_QB_POLL_MAX_MS, Math.max(_QB_POLL_MIN_MS, s * 1000))" in js, \
        "轮询间隔必须经 [1.5s,600s] 夹取(防御界)"
    assert "immediate: true," in js, \
        "流量轮询缺 immediate 首拍立即(F8/D4 —— 冷开首拍不再 arm 成 30s fallback 干等)"
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
    # 定时器白名单(S3 起唯一例外 = 面板状态行 1s 时钟 _qbFxClock: 开面板装 / 关面板与
    # beforeUnmount 双清 —— 非轮询定时器, 显示面专用; 轮询定时器仍一律收口骨架 _polls 表,
    # 文件内出现第二处裸写定时器即回潮):
    assert js.count("setInterval(") == 1 and js.count("clearInterval(") == 2 \
        and "setInterval(() => { this.fxNow = Date.now(); }, 1000)" in js \
        and js.count("clearInterval(this._qbFxClock)") == 2, \
        "qb_traffic_chart.js 定时器白名单: 唯一裸写 = 面板状态行 1s 时钟(_qbFxClock, 配对启停); " \
        "轮询启停收口到骨架, 手柄在 _polls 表, 第二处裸写定时器即回潮"
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
    # 取数有效性不变量(3)(计划 26-11-22-0858): 发射时快照窗口名, 成败两路 stale 判据都带窗口
    # 分量 —— 旧窗口在途响应不得覆盖新窗数据(换窗竞态: 1m 选择下整列呈旧窗跨度 = x 向压缩)。
    assert "const w0 = this[def.window];" in load_body \
        and load_body.index("const w0 = this[def.window];") < load_body.index("await this.api(") \
        and load_body.count("def.stale(this, ctx) || this[def.window] !== w0") == 2, \
        "_qbLoad 必须发射时快照窗口名(先于 await —— 快照挪 await 后 stale 恒等判真)且成败两路" \
        " stale 判据都带窗口分量(旧窗口在途响应落袋 = 换窗竞态回潮)"
    assert "prev.setData([data.xs, data.up, data.dl]);" in js and "prev.root.parentElement === host" in js, \
        "qb_traffic_chart.js 缺 setData 原地快路(每次轮询 destroy+new uPlot 清屏 = 每隔一个轮询周期闪一次; 尾锚显式视口: 三列原样落袋 + 判定帧显式视口)"
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
    # 落点次序(用户口径「即『下载累计』后」): 图例 → 窗口 N 点 → 上传累计 → 下载累计 → 控件组
    _order = [stat_blk.index(k) for k in ("hs-leg", "窗口", "上传累计", "下载累计", "qb-statctl")]
    assert _order == sorted(_order), \
        "统计栏次序必须为 图例 → 窗口 N 点 → 上传累计 → 下载累计 → 档位/纵轴控件组"
    assert 'hs-leg' in stat_blk and '上传' in stat_blk and '下载' in stat_blk, \
        "统计栏(.hist-summary)必须含上传/下载图例(.hs-leg), 且排在「窗口 N 点」之前"
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
    # R8 修复轮: 状态行展示值必须住 computed 块 —— fx-panel.html 裸插值展示值不加括号, 落
    # methods 域会被 toDisplayString 渲染成函数源码字符串(首轮 blocker 的回潮形态, 静态面零
    # 引用即无测试变红, 故钉落位)。判据 = 定义名恰出现 1 次且夹在 computed: { 与 mounted() {
    # 之间(mixin 结构里 methods 在 mounted 之后, 落 methods 即越过 mounted 界)。
    # F6(plan 26-11-14-1313): 采样显示改走 qbFxSampleText 两值口径(sample_interval_s ≠
    # interval_s 时「X s · 桶宽 Y s」), qbFxPeriodS 退居其相等/缺失回落值 —— 两者同钉落位。
    comp_start = js.index("computed: {")
    mounted_at = js.index("mounted() {")
    for name in ("qbFxPeriodS", "qbFxBeatMs", "qbFxSampleText"):
        n_def = js.count(name + "()")
        assert n_def == 1, f"qb_traffic_chart.js 里 {name}() 应恰出现 1 次(现 {n_def} 次, 多半是模板/注释带出了带括号引用)"
        assert comp_start < js.index(name + "()") < mounted_at, \
            f"{name} 不在 computed 块(computed: {{ 与 mounted() {{ 之间) —— 回潮到 methods 即复现" \
            "「状态行渲染函数源码」blocker"
    assert "{{ qbFxSampleText }}" in fx_tpl and "{{ qbFxBeatMs }}" in fx_tpl, \
        "fx-panel.html 状态行必须裸插值展示值 computed(不加括号; F6 采样两值口径走 qbFxSampleText)"
    assert "qbFxPeriodS(" not in fx_tpl.replace("{{ qbFxPeriodS }}", "") \
        and "qbFxBeatMs(" not in fx_tpl.replace("{{ qbFxBeatMs }}", "") \
        and "qbFxSampleText(" not in fx_tpl.replace("{{ qbFxSampleText }}", ""), \
        "fx-panel.html 不得带括号调用展示值(qbFxSampleText/qbFxBeatMs 是 computed 不是方法)"

    # 3. 装载序: qb_traffic_chart.js 必须排在 state.js 之前(初值函数在 state data() 时可用)
    for ui in _UI_ALL:
        scripts = _ui_manifest(ui)["scripts"]
        assert scripts.index("/shared/qb_traffic_chart.js") < scripts.index("/shared/state.js"), \
            f"{ui}: qb_traffic_chart.js 必须排在 state.js 之前(qbInitialWindow 定义处, 否则启动白屏)"


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
