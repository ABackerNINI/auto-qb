"""test_webui_static_dom_panel_traffic_fx_store 测试计划: webui 前端静态守阵: 详情面板 / 弹窗 / 浮层

原 test_webui_static_dom_panel_traffic.py 按域拆分(move-only, 2026-11-27); 测试 ID/名称/断言零变化。

## 测试计划(每个测试函数一条)
- test_frontend_qb_fx_store_and_sanitize_battery: 数值面板持久化读路径与逐字段校验 node 电池(R8, plan 26-11-12-1139 §05.5, §09 脏值探针) —— qbInitialFx 桩 localStorage 钉四脏值场景(坏 JSON/v:0/数组根/空串)整体回落默认且键保留(全程零 removeItem) + _qbFxSanitize 逐字段: 错类型(数字字段 null/布尔/数组不得被 Number() 误收、布尔严格 ===true/false 且类型归位、合法 false 保真)/未知枚举与空串回落/clamp 边界(impact/particles [0,1]、shiftRatio [0.2,1] 双侧, 数字串"0.9"抢救)/未知键静默丢弃(旧版残留 scene/amp/tpl 清场)/合法值全字段保真 + layers 残缺(数组根/缺键)逐层补默认。无 node 静默跳过(同 _NODE_QB_TRAFFIC_PROBE 口径)
- test_frontend_qb_fx_panel_wiring_battery: 面板接线 S3 电池 + 接缝静态钉(S3, plan 26-11-12-1139 §05.3/§05.4/§05.9/§06 S3 行, D21) —— node 电池双发(真 mixin 方法 + 桩 uPlot/记账 ctx, 同节拍内核范式): 预览一拍六条语义逐条真跑(1) 不动窗口: needsShift=false/dx0=0 + 预览全程零 setScale("x") + xs/u.scales.x 逐帧零变化 + 末帧 setData 交还 auto; 2) 假 Δ 贴近真实量级: 相对 Δ 恰 clamp(0.18+0.35×密度,0.10,0.50) 且方向按轨 up 减/dl 加、密度 0->0.18 Lv.2 不固定拉满 Lv.3、target 钳 [0,yMax] 零跳轴(贴轴 Δ 被轴档压制 —— 计划伪代码值域钳的生产域适配)、零流量 up 减钳 0 诚实静默、死轨不造假复活; 3) 连点重启: previewToken 递增 + anim 携带当前 token(帧循环令牌门失效旧帧) + 从当前显示值接续不回跳 + 还原点继承首拍捕获; 4) 真值抢占: 真拍 setData 整组落袋 + 判定帧取消预览/镜像清/新拍以中断显示值接续照常收敛 + 对偶(真拍主区在途预览忽略、次区相位可被接管); 5) 不写 store: 预览三方法域零 persistQbFx/localStorage(静态钉) + 末帧还原真值 + 状态机复位真值对齐 + 在途重排走 _qbPreviewRestore 假 target 不落真值面; 6) 同预算: spawn 走真拍同一条 _qbFxSpawn(cap ≤32/半套 ≤16/切片 ≤5/梳齿 ≤7) + 记账 ctx 预览帧束体 ≤23、束+切片 ≤28(glitch 双开、分域计数合成 —— _qbDrawFx 内部调 scan 同 ctx 直数会重复计束) + 有墨量防空转(峰值 ≥19) + 连点 5 次单一 fx 粒子合计 ≤32)+ ease 消费(§05.3 ease 行 + D21 例外条款: _qbFxCurve 单点 out/linear/未知回落 + _qbFxLinear 恒等夹取 + _qbFxShown 单次施加(修正 S1 帧循环预 easeOut 的双重施加, 对齐计划 §03 公式与 §04 演示) + out vs linear 收敛序列形状不同(out 前载 clock200 帧 24.07 vs 16.67) + 拍中改 ease 当前拍不换式(冻结引用不变逐帧一致) + 下一拍起用(判定帧重读) + 预览同款冻结)+ 字段贯通收口(shift=instant 下一拍 L0 不播但 L1 照常收敛 + 拍中改档不中断; shiftRatio 拍中改在途时间线不变下一拍生效; enabled 面板全链 fxCheck 写唯一字段 -> persistQbFx 真落盘 -> _qbFxCfgSync 同步 on=false -> 下一拍装饰零绘制但 L0 照滚 + enabled=false 预览空操作; tail/impact/tear/echoSpan/layers/palette/particles/dual/neon 归 S2-a/S2-b 既有电池)+ 状态行镜像(fxBeatAt 只写当前 scope 真拍/预览不写 + fxPreviewing 翻转沿 + qbFxBeatAgeText 三态: —/4.2 s 前/时钟未追上钳 0.0)+ 缺省 scope=qbCurScope; 静态钉: 预览三方法域零持久化零定时器(不自动循环 —— D21)/ease 消费单点唯一(_qbFxCurve 定义1+调用2 恰两判定帧、cfg.ease 恰 2 处、S1 预折算行退场、L0 dx 行恒 easeOut)/shift=instant 消费点在判定帧(零消费字段补齐)/预览接缝(令牌门 + _qbPreviewEnd 先于 _qbBeatConverge + 重排预览支路 + _qbBeatCancel 清镜像 + 预览收口 x 显式重申 + y 成对钉在位钉 —— B 案例列与锚视口同形的行为电池盲区)/状态行(模板 qbFxBeatAgeText + v-if fxPreviewing「· 预览中」+ state.js 三镜像字段显式建 + 1s 时钟开面板装/关面板与 beforeUnmount 双清)/双入口单状态源(总开关唯一入口 :checked=fxOn + fxCheck('enabled') 唯一写入、chart 零 fx.enabled 赋值面、contextmenu 只 openFxPanel —— D24 终态); 行为面另含评审修正轮 4 断言: 连点早退(!moving/!n)同走还原核心(假值不留痕的早退面, minor1)/连点 rAF 单飞钉(删 _qbBeatCancel 变异即红)/令牌门兜底触发同步清镜像(minor2)/ease+shift+shiftRatio 处理器全链 fxPick/fxRange->store->CFG(minor4) + S4-a 轮追加: N 块字段闭环 15 控件(§05.9 第 1 项电池级: fxPick 六下拉/fxRange 三滑杆/fxCheck 六复选含 layers.* 四键, 逐控件 -> fx 写入 + 单键 JSON 落盘(fxRange 验 @change 落盘一次) + watch 等价 -> CFG 同步 + fxPick 非法枚举回落现值不落盘)/静态钉 g(fx-panel.html 15 控件绑定串全量 —— 处理器/字段键改名 = 死控件, 行为电池直接调方法测不到模板漂移)。无 node 静默跳过(同 _NODE_QB_TRAFFIC_PROBE 口径)
- test_frontend_qb_fx_overlay_close_registry_and_reduced_motion: 数值面板收层七处登记 + IO 兜底 + reduced-motion 红线静态守阵(R8 S0-b, plan 26-11-12-1139 §05.6/§05.7/§05.9) —— lifecycle 点空白名单与 Esc 退栈链(紧跟 drawerMenu 之后: 后开先关, 面板开着 Esc 只关面板)/dialogs_meta escBusy/closeDrawer/drawerTab/换目标收口六处在位(shortcuts _kbOverlayBusy 末尾项归 test_drawer_dock_keyboard_w2 书写序守阵) + IO 观察 .qb-chart-host 在 _qbFxListen 开面板支路建/关面板支路断(ratio===0 走 fxClose 单点, 不挂 _qbChartDestroy 防换肤误关; 七处直写 visible=false 的断开由 state.js 'fxPanel.visible' watcher 统一汇到 _qbFxListen(false)) + reduce 红线: 判定单点内联 matchMedia 不引用 AQB_FX.reduced(flux-only 三套旧皮肤 ReferenceError)/有效值单点 fxOn = enabled && !reduce/change 监听 mounted 装beforeUnmount 摘/AQB_FX_CFG._qbFxCfgSync 附加 on 且 fx+fxReduce 两 watcher 汇入/面板总开关 :checked=fxOn + :disabled=fxReduce 置灰与说明行/有效值 on 不进持久化形状(QB_FX_DEFAULTS 无 on 键) + S4-a 轮追加 section 5(§05.9 第 6 项/第 9 项的电池级等价): openFxPanel 经 overlay_fit 单点钳位 + 图宿主右缘钳位(右缘 >=8px)/重开复位 alt/Alt 看穿三路(keydown+keyup 同处理器按 e.altKey 写态 + 面板不可见早退 + blur 失焦复位)/四皮肤 .fx-panel CSS 成对(fixed 本体/max-height 兜底/fx-alt/120ms 仅 opacity/reduce 零动画)/D20 渗色禁令(fx CSS 段剥注释零 --today-up/--today-down)

## 皮肤档位口径
- 皮肤清单单点注记见 test_webui_static_dom_panel_traffic_wiring.py docstring「## 皮肤档位口径」节(单点保留处)。
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

# ============================================================================================
# S4-a 覆盖矩阵(S4-a 盘点轮 2026-11-14; plan 26-11-12-1139 §10「建议新增」九组探针 + §05.9
# 面板九项 -> 本文件电池映射; 三类结论: [已覆盖]=指认 / [本批补]=本轮新增断言 / [P8]=e2e 或真机):
# G1 逐帧探针: [已覆盖] 节拍内核电池 B/C(时间线 animEnd<=beat<=1000 全域扫) + S1/S2(起拍同帧/
#   I1 电池级/收敛序列单调无回跳) + 静态钉 a(快路逐字行后追加 _qbBeatStart); 帧级 <=16ms 采样
#   为真机面 -> P8。
# G2 左移连续性(R1): [已覆盖] S2(dx 单调收缩归零)/S9b(roll 恰边界)/0.75px 规则(D/S8) + S3 面板
#   电池 G(smooth 基线 + instant 下一拍不播 L0)/静态钉 b/c; 三档口径: smooth/instant 双档交付
#   (P6 拍板「不左移」生产不可选, instant 即对照档); 「连拍 30 次相邻两拍边界像素位移 <=1px」
#   为画布像素面 -> P8。
# G3 视觉引擎(R2): [已覆盖] 纯函数面 J/K(t=0 环与粒子同判定帧/0.55xbeat 后 null) + G1-G7(blur
#   预算/密度即时/切片门) + I9 常量钉; 三档配色 calm 零辉光零束体零切片(G3/S1 门面)、glitch 切片
#   (G7/S7); [裁决轮补, 评审 major 修正] calm 零粒子唯一闸 = 绘制面 eff 逐帧门(G10), spawn 恒
#   满额清单与配色档解耦(F1f 钉, F8 同款) —— plan §04 原型 partCap 的 isCalm 口径, §10「克制档
#   零粒子」原文补齐; 原型另有 leadLevel()<=1->0 门, Lv.1 发粒子系用户拍板维持现状(P9 未采纳,
#   生产只采纳 isCalm 的 calm 分量); 曲线像素对比度 -> P8(电池级等价 = 静态钉 b 层序)。
# G4 双轨(R3): [已覆盖] E/F(状态机独立/缺口轨/复活轨) + F1a/F2(三策略) + F7/G5/G8(缺口落位/
#   加亮不桥接/环心) + alloc 全域扫; [本批补] F1e(上轨真 0 的 act 门) + G9(绘制面真 0 轨零
#   粒子 16 vs 32) + S7b(F1 后: 零变化滚窗 fx 恒在场 lv=1 + 尾点零改写, L0 照滚)。
# G5 背景静态(R4): [已覆盖](电池级等价) 静态钉 c/b(fx/束体域 fillRect 恰 1 处且 1px 级) + S7
#   (切片几何/右端不越判定线); 「连拍 30 次固定两点 RGB 恒定」为画布采样面 -> P8。
# G6 N 层作用域(R4): [已覆盖] B(白/黑名单逐字零交集) + 静态钉 d(fx 三域零触碰 legend/cursor/
#   series) + V1 色表/_qbFxNeonQ(0.33xbeat 回落)/G4(neon=false 零落笔); 任一帧 strokeStyle
#   像素面 -> P8(电池级等价 = 曲线描边恒 uPlot 系列原生 + 黑名单钉)。
# G7 T6 组合(R4/R5): [已覆盖] S1-S8 + S6b(束体指令/行程/包络/回声/光带/切片/微震让位/grade 收口/
#   env 接线); 「与单独 T2-T5 逐帧对比」随 D25 只交付 T6 而 N/A, 不变量 I1/I4/I9/I10/I11 各自有钉。
# G8 扫描束(R5/R7): [已覆盖] S1(<=23 分窗恰值 + 整块 fillRect=0)/S2(相位 A 行程)/S3(不进绘图区 +
#   墨量可见)/S4(回声 alpha 硬停 + echoSpan 各档)/S5(梳齿冻结)/S6b(env 峰位); 第 8 项「full 扫得更远」
#   按 A2 回退 full 恢复整幅 s=w 落地(S4 电池逐档断言 full s=w, 模板 demo:1152-1158 对照档口径 ——
#   与计划 §10 第 8 项一致), 旧「生产降格 auto」注记退役。
# G9 周期参数化: [已覆盖] 节拍内核电池 A/B(multiplier 1/2/8 与 600s 夹顶 + tail 封顶非常驻 +
#   animEnd 全域扫)。
# G10 零变化静默/reduced-motion/四皮肤 rect/动画中悬停: 零变化静默 [本批补] S7b(F1 后 fx 恒在场 lv=1) + S12
#   (零变化连拍 10 次累积零绘制; F6/26-11-15-1104 后改钉: 值>0 连拍 fx 即抛即清零累积 —— S12/S12b
#   双面, 全静默面收窄真 0); reduced-motion [已覆盖](S5 短路/F1c 无 anim + 收层电池 3a-3e);
#   [本批补] S13(动画中悬停读数面行为化: points 真值/索引钳制/缺口区段); 四皮肤 rect 与滑杆可用
#   -> P8(静态面 [本批补] 收层电池 section 5: openFxPanel 钳位/Alt 三路接线/四皮肤 CSS 成对/渗色
#   禁令)。
# G11 横向线条(R6): [已覆盖] 纯函数面 E/E+/F(2/3/5 与 3/5/7/撕裂带公式逐条/钳边/三档对照) + S5
#   (同拍几何冻结/合计 12) + S7(绘制域/束+切片 28) + F9(spawn 侧紧断言)。
# 面板九项(§05.9 + §10 R8): 第 1 项字段闭环 [本批补] N(15 控件处理器闭环 store+CFG) + section g(模板
#   绑定全量) + 存储电池(回读保真); 第 2 项脏值回落 [已覆盖](存储电池四场景 + layers 数组根/缺键);
#   第 3 项预览不动数据/第 4 项真值抢占/第 5 项收层顺序/第 7 项总开关单状态源(§05.9 原文
#   「双向」因 D24 收敛为单状态源 —— 第二开关撤, contextmenu 只 openFxPanel, 静态钉 f)/
#   第 8 项 reduced-motion [已覆盖](面板电池
#   B-E/I-K/M1/M2 + 收层电池 1-3 + 静态钉 a-f); 第 6 项不遮挡/第 9 项四皮肤 rect -> P8(静态面 [本批补]
#   收层电池 section 5)。
# ============================================================================================

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
        [node, "-e", _NODE_STDIN_WRAPPER,
         os.path.join(STATIC_ROOT, "shared", "qb_traffic_chart.js")],
        input=_NODE_QB_FX_PROBE,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    assert proc.returncode == 0, f"qbFx 持久化 node 电池跑挂: {proc.stderr.strip()}"
    report = json.loads(proc.stdout.strip().splitlines()[-1])
    assert report["failed"] == [], \
        f"qbFx 持久化电池 {report['ok']}/{report['total']} 过, 失败: {report['failed']}"


# 面板接线 S3 调度器行为 node 电池(plan 26-11-12-1139 §05.4 六条语义 + §05.3 ease/shift 行 +
# D21): 真 mixin 方法 + 桩 uPlot(含 valToPos/bbox 全量, 提交语义同节拍调度器电池) —— 预览一拍
# 六条逐条真跑 + ease 消费(out/linear 形状差/拍内冻结/下一拍生效) + shift=instant 与 shiftRatio
# 下一拍语义 + enabled 面板操作链路 + 状态行镜像。无 node 静默跳过(同 _NODE_QB_TRAFFIC_PROBE 口径)。
_NODE_QB_FXPANEL_SCHED_PROBE = r"""
const fs = require("fs");
global.window = {};
const src = fs.readFileSync(process.argv[1], "utf8");
const { methods, computed, _qbFxCurve, _qbFxLinear, _qbFxEaseOut, _qbFxShown, QB_FX_STORE_KEY } =
  new Function(src + "\nreturn { methods: window.AQB_QB_TRAFFIC.methods, computed: window.AQB_QB_TRAFFIC.computed,"
  + " _qbFxCurve, _qbFxLinear, _qbFxEaseOut, _qbFxShown, QB_FX_STORE_KEY };")();
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);
const close = (a, b, eps) => Math.abs(a - b) <= (eps === undefined ? 1e-9 : eps);
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
    scales: { x: { min: xs[0], max: xs[xs.length - 1] }, y: { min: 0, max: 63 } },
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
      if (py) this.scales.y = { min: py.min, max: py.max };
      this.scales.x = { min: px.min, max: px.max };
    },
    destroy() { this.destroyed = true; },
  };
  return u;
}
function mkBeat(anchor, step, span, upShown, dlShown) {
  return {
    raf: 0, anim: null, anchor, step, span,
    tracks: {
      up: { prev: upShown, target: upShown, shown: upShown, delta: 0, level: 0, live: true },
      dl: { prev: dlShown, target: dlShown, shown: dlShown, delta: 0, level: 0, live: true },
    },
  };
}
const self = Object.assign({}, methods, { _qbPollMs: () => 3000, _qbCharts: {}, qbCurScope: "global",
  fxPreviewing: false, fxBeatAt: 0, fxNow: 0 });
/* 全字段 CFG(与 §05.5 存储形状一致; S3 消费面: ease/shift/shiftRatio/particles/tail/on) */
const CFG = { v: 1, enabled: true, on: true, impact: 0.7, ease: "out", palette: "neon",
  particles: 0.7, neon: true, tail: false, shift: "smooth", shiftRatio: 0.6, dual: "both",
  tear: "linked", echoSpan: "auto", layers: { band: true, particles: true, scan: true, grade: true } };
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
// —— A. ease 曲线选择单点(§05.3 ease 行; 数值插值单次施加, L0/装饰不随 ease 变) ——
ok("A _qbFxCurve: out -> easeOut / linear -> _qbFxLinear / 未知回落 out",
  _qbFxCurve("out") === _qbFxEaseOut && _qbFxCurve("linear") === _qbFxLinear && _qbFxCurve("bogus") === _qbFxEaseOut);
ok("A _qbFxLinear 恒等且越界夹取(与 out 同口径)", _qbFxLinear(0.5) === 0.5 && _qbFxLinear(-1) === 0 && _qbFxLinear(2) === 1);
ok("A _qbFxShown 单次施加(修正 S1 双重 easeOut): out(0.5)=0.875 / linear(0.5)=0.5",
  close(_qbFxShown({ prev: 0, target: 1 }, 0.5), 0.875) && close(_qbFxShown({ prev: 0, target: 1 }, 0.5, _qbFxLinear), 0.5));
ok("A 收敛插值终点/起点与曲线无关(p=1 -> target, p<0 -> prev)",
  close(_qbFxShown({ prev: 2, target: 7 }, 1, _qbFxLinear), 7) && close(_qbFxShown({ prev: 2, target: 7 }, -3, _qbFxLinear), 2));
// —— B. 预览一拍 §05.4 第 1 条: 不动窗口(dx ≡ 0, xs / u.scales.x 零变化) ——
{
  const u = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1150, 30, 120, 30, 60);  // 收敛稳态 + 同网格(无真位移可借道)
  self._qbCharts = { global: u };
  const xsBefore = JSON.stringify(u.data[0]);
  const xScaleBefore = { min: u.scales.x.min, max: u.scales.x.max };
  const yMaxBefore = u.scales.y.max;
  self._qbPreviewBeat("global");
  const a = u._qbBeat.anim;
  ok("B 预览起拍: anim.preview=token(1) + needsShift=false + 锚零位移(anchorFrom === anchorTo"
    + " —— 窗口搬运整体跳过)",
    !!a && a.preview === 1 && u._qbBeat.previewToken === 1 && a.needsShift === false
    && a.anchorFrom === a.anchorTo);
  ok("B 起拍零 setScale(\"x\") + y 钉在当前档位(零跳轴)", u.setScaleLog.length === 0
    && a.yMax === yMaxBefore);
  ok("B 镜像 fxPreviewing 翻 true(状态行「· 预览中」)", self.fxPreviewing === true);
  const xLogs = [];
  let frames = 0;
  let guard = 0;
  while (rafMap.size && guard++ < 200) {
    nowMs += 50;
    pump();
    frames++;
    if (u._qbBeat && u._qbBeat.anim) xLogs.push(...u.setScaleLog.filter((r) => r[0] === "x"));
  }
  ok("B 预览全程 xs / u.scales.x 零变化(§05.9 预览拍探针口径)", JSON.stringify(u.data[0]) === xsBefore
    && u.scales.x.min === xScaleBefore.min && u.scales.x.max === xScaleBefore.max);
  ok("B 预览全程零 setScale(\"x\")(dx ≡ 0 —— L0 块整体跳过)", xLogs.length === 0);
  ok("B 预览多帧插值后末帧还原真值 + anim 收口 + 镜像清",
    u.data[1][4] === 30 && u.data[2][4] === 60 && u._qbBeat.anim === null && self.fxPreviewing === false);
  ok("B 末帧 setData 交还 auto(与收敛帧同款; 预览帧数与真实拍主区同窗)", u.setDataCount === 1 && frames >= 8);
  ok("B 双轨状态机复位到真值对齐(假值不留痕, 下一真拍从真值接续)",
    u._qbBeat.tracks.up.target === 30 && u._qbBeat.tracks.up.delta === 0 && u._qbBeat.tracks.up.level === 0
    && u._qbBeat.tracks.dl.target === 60 && u._qbBeat.tracks.dl.shown === 60);
}
// —— C. §05.4 第 2 条: 假 Δ 贴近真实量级 + 方向按轨(up 减 / dl 加), 不固定拉满 Lv.3 ——
{
  const run = (particles) => {
    global.window.AQB_FX_CFG = Object.assign({}, CFG, { particles });
    const u = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
    u._qbBeat = mkBeat(1150, 30, 120, 30, 60);
    self._qbCharts = { global: u };
    self._qbPreviewBeat("global");
    const snap = {
      upT: u._qbBeat.tracks.up.target, upD: u._qbBeat.tracks.up.delta, upL: u._qbBeat.tracks.up.level,
      dlT: u._qbBeat.tracks.dl.target, dlD: u._qbBeat.tracks.dl.delta,
    };
    drain();
    return snap;
  };
  const mag = (particles) => Math.min(0.5, Math.max(0.1, 0.18 + 0.35 * particles));
  const s07 = run(0.7);
  ok("C 密度 0.7: mag=0.425, up 减(dl 加)且相对 Δ 恰 mag(Lv.3)",
    close(s07.upD, mag(0.7)) && s07.upT < 30 && s07.upL === 3);
  ok("C 密度 0.7: dl target 贴轴钳 63(yMax) —— 预览零跳轴优先, Δ 被轴档压制(计划伪代码值域钳的生产域适配)",
    close(s07.dlT, 63) && close(s07.dlD, 0.05));
  const s0 = run(0);
  ok("C 密度 0: mag=0.18(下限保护) -> Δ 0.18 Lv.2 —— 不固定拉满 Lv.3(密度低预览就低)",
    close(s0.upD, 0.18) && s0.upL === 2);
  const s1 = run(1);
  ok("C 密度 1: mag 钳上限 0.50 -> Lv.3(钳上界生效)", close(s1.upD, 0.5) && s1.upL === 3);
  // 尾值 0: up 减被钳 0(诚实静默 —— 数值域非负), dl 加照发(Δ 恰 mag)
  global.window.AQB_FX_CFG = Object.assign({}, CFG, { particles: 0.7 });
  const u2 = mkU(XS1, [0, 0, 0, 0, 0], [0, 0, 0, 0, 0]);
  u2._qbBeat = mkBeat(1150, 30, 120, 0, 0);
  self._qbCharts = { global: u2 };
  self._qbPreviewBeat("global");
  ok("C 零流量: up target 钳 0 静默(delta 0), dl 加发 Δ=mag(单轨照常)",
    u2._qbBeat.tracks.up.target === 0 && u2._qbBeat.tracks.up.delta === 0
    && close(u2._qbBeat.tracks.dl.delta, mag(0.7)) && u2._qbBeat.tracks.dl.target > 0);
  drain();
  // 缺口/死轨: 预览不造斜坡(复活直落真值语义, 预览不造假复活)
  const u3 = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, null, 60]);
  u3._qbBeat = mkBeat(1150, 30, 120, 30, 60);
  u3._qbBeat.tracks.up = { prev: null, target: null, shown: null, delta: 0, level: 0, live: false };
  self._qbCharts = { global: u3 };
  self._qbPreviewBeat("global");
  ok("C 死轨不参与预览(live=false 跳过, 状态原样), 活轨照常起拍",
    u3._qbBeat.tracks.up.target === null && u3._qbBeat.tracks.up.live === false
    && u3._qbBeat.tracks.dl.target > 60 && u3._qbBeat.anim !== null);
  drain();
  global.window.AQB_FX_CFG = CFG;
}
// —— D. §05.4 第 3 条: 连点重启(previewToken 递增令旧帧失效, 从当前显示值重起, 不排队不叠加) ——
{
  const u = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1150, 30, 120, 30, 60);
  self._qbCharts = { global: u };
  for (let i = 1; i <= 5; i++) {
    self._qbPreviewBeat("global");
    ok("D 连点 " + i + " rAF 单飞(旧帧已摘, 不与新回调并存 —— 不排队不叠加)", rafMap.size === 1);
    const a = u._qbBeat.anim;
    ok("D 连点 " + i + ": token=" + i + " 且 anim 携带当前 token(旧帧被令牌门失效)",
      u._qbBeat.previewToken === i && a.preview === i && self.fxPreviewing === true
      && a.fx.cap <= 32 && a.fx.specs.up.length <= 16 && a.fx.specs.dl.length <= 16);
    nowMs += 50;
    pump();
  }
  const a5 = u._qbBeat.anim;
  ok("D 重启从当前显示值接续(禁止回跳 —— I3), 还原点继承首拍捕获(中途假值不落还原点)",
    a5.restore.up === 30 && a5.restore.dl === 60 && a5.preview === 5);
  drain();
  ok("D 连点 5 次末态: 单一 fx(粒子合计 <=32, 无两套叠加)+ 原真值还原 + 镜像清",
    u._qbBeat.anim === null && u.data[1][4] === 30 && u.data[2][4] === 60 && self.fxPreviewing === false);
}
// —— E. §05.4 第 4 条: 真值抢占(判定帧先取消预览态, 真实拍走正常链路 —— 真值永远优先) ——
{
  const u = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1150, 30, 120, 30, 60);
  self._qbCharts = { global: u };
  self._qbPreviewBeat("global");
  for (let i = 0; i < 5; i++) { nowMs += 50; pump(); }  // clock 200: 收敛窗内, 假值已上屏
  const midShown = u.data[1][4];
  ok("E 前置: 预览在途(尾点已偏离真值)", u._qbBeat.anim !== null && u._qbBeat.anim.preview !== undefined
    && midShown < 30 && midShown > 17.25);
  // 真实拍到达 = 快路 setData 整组落真窗口(预览假值随数组替换消亡) -> 判定帧 _qbBeatStart
  u.data = [[1060, 1090, 1120, 1150, 1180], [0, 0, 0, 0, 40], [0, 0, 0, 0, 60]];
  self._qbBeatStart("global", u);
  ok("E 抢占: 判定帧取消预览(anim.preview undefined) + 镜像清 + 真拍正常起(rAF 在)",
    u._qbBeat.anim !== null && u._qbBeat.anim.preview === undefined && self.fxPreviewing === false
    && rafMap.size === 1);
  ok("E 抢占: 新拍以当前显示值接续(prev = 预览中断值, 禁止回跳 —— I3) + target 新真值",
    u._qbBeat.tracks.up.prev === midShown && u._qbBeat.tracks.up.target === 40);
  drain();
  ok("E 真实拍照常收敛到新真值(链路无残扰)", u.data[1][4] === 40 && u._qbBeat.anim === null);
  // 对偶: 真拍主区在途时预览点击被忽略(§05.4 第 4 条的对偶面)
  const u2 = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u2._qbBeat = mkBeat(1120, 30, 120, 10, 55);
  self._qbCharts = { global: u2 };
  self._qbBeatStart("global", u2);
  self._qbPreviewBeat("global");
  ok("E 对偶: 真拍主区在途预览忽略(真值优先, 零令牌零镜像)", u2._qbBeat.anim.preview === undefined
    && u2._qbBeat.previewToken === undefined && self.fxPreviewing === false);
  drain();
  // 次区装饰相位无真值语义: 可被预览接管
  global.window.AQB_FX_CFG = Object.assign({}, CFG, { tail: true });
  const u3 = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u3._qbBeat = mkBeat(1120, 30, 120, 10, 55);
  self._qbCharts = { global: u3 };
  self._qbBeatStart("global", u3);
  for (let i = 0; i < 14; i++) { nowMs += 50; pump(); }  // 有界推进: 过收敛帧(600)入次区相位, 不抽干
  ok("E 前置: 真拍收敛后转入次区相位(tail=true)", u3._qbBeat.anim !== null
    && u3._qbBeat.anim.phase === "tail");
  self._qbPreviewBeat("global");
  ok("E 次区相位可被预览接管(anim 换成 preview + 镜像翻 true)",
    u3._qbBeat.anim !== null && u3._qbBeat.anim.preview === 1 && self.fxPreviewing === true);
  drain();
  ok("E 接管后预览照常收口(还原真值, 无次区相续)", u3.data[1][4] === 30 && u3._qbBeat.anim === null
    && self.fxPreviewing === false);
  global.window.AQB_FX_CFG = CFG;
}
// —— F. ease 消费(§05.3 ease 行 + D21 例外条款): out vs linear 形状差 / 拍内不换式 / 下一拍起用 ——
{
  const runBeat = (ease, easeFlipAt) => {
    const u = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
    u._qbBeat = mkBeat(1120, 30, 120, 10, 55);
    self._qbCharts = { global: u };
    global.window.AQB_FX_CFG = Object.assign({}, CFG, { ease });
    self._qbBeatStart("global", u);
    const easeF0 = u._qbBeat.anim.easeF;
    const seq = [];
    let frozen = true;
    for (let i = 0; i < 20; i++) {
      if (easeFlipAt === i) global.window.AQB_FX_CFG = Object.assign({}, CFG, { ease: "linear" });
      nowMs += 50;
      pump();
      seq.push(u.data[1][4]);
      if (u._qbBeat.anim && u._qbBeat.anim.easeF !== easeF0) frozen = false;
    }
    return { easeF0, seq, frozen };
  };
  const out = runBeat("out", -1);
  const lin = runBeat("linear", -1);
  ok("F 判定帧冻结曲线引用(anim.easeF): out 拍恒 _qbFxEaseOut / linear 拍恒 _qbFxLinear",
    out.easeF0 === _qbFxEaseOut && lin.easeF0 === _qbFxLinear);
  ok("F out vs linear 收敛序列形状不同(out 前载): clock 200 帧 out 24.07 vs linear 16.67(p=200/600)",
    out.seq[4] > lin.seq[4] && close(out.seq[4], 10 + 20 * (1 - Math.pow(1 - 200 / 600, 3)), 1e-6)
    && close(lin.seq[4], 10 + 20 * (200 / 600), 1e-6));
  ok("F 两序列都单调收敛且终点恰真值(I4/D9 不变)",
    out.seq.every((v, i) => i === 0 || v >= out.seq[i - 1] - 1e-12)
    && lin.seq.every((v, i) => i === 0 || v >= lin.seq[i - 1] - 1e-12)
    && out.seq[out.seq.length - 1] === 30 && lin.seq[lin.seq.length - 1] === 30);
  const flip = runBeat("out", 4);  // clock 200(收敛窗内)切 linear
  ok("F 拍中改 ease 当前拍不换式(D21 唯一例外条款): 冻结引用不变 + 逐帧序列与全程 out 参考拍一致",
    flip.frozen && flip.seq.length === out.seq.length
    && flip.seq.every((v, i) => close(v, out.seq[i], 1e-9)));
  global.window.AQB_FX_CFG = Object.assign({}, CFG, { ease: "linear" });
  const u2 = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u2._qbBeat = mkBeat(1120, 30, 120, 10, 55);
  self._qbCharts = { global: u2 };
  self._qbBeatStart("global", u2);
  ok("F 下一拍起用: 新拍 anim.easeF = linear(判定帧重读 cfg.ease)",
    u2._qbBeat.anim.easeF === _qbFxLinear);
  const seq2 = [];
  for (let i = 0; i < 6; i++) { nowMs += 50; pump(); seq2.push(u2.data[1][4]); }
  ok("F 下一拍 linear 数值形状(clock 200 帧: 10 + 20×(200/600), Δ=target30−prev10)",
    close(seq2[4], 10 + 20 * (200 / 600), 1e-6));
  drain();
  // 预览同样消费 cfg.ease(起拍冻结)
  const u3 = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u3._qbBeat = mkBeat(1150, 30, 120, 30, 60);
  self._qbCharts = { global: u3 };
  self._qbPreviewBeat("global");
  ok("F 预览起拍同款冻结(anim.easeF = linear)", u3._qbBeat.anim.easeF === _qbFxLinear);
  drain();
  global.window.AQB_FX_CFG = CFG;
}
// —— G. §05.3 shift 行消费端(S3 补齐): instant = 退回瞬时跳变(对照), 下一拍起 ——
{
  const u = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1120, 30, 120, 10, 55);
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  ok("G smooth 基线: L0 过渡在播(x 提交在 + rAF 在)", rafMap.size === 1
    && u.setScaleLog.some((r) => r[0] === "x"));
  const xAt = u.setScaleLog.filter((r) => r[0] === "x").length;
  global.window.AQB_FX_CFG = Object.assign({}, CFG, { shift: "instant" });
  nowMs += 50;
  pump();
  nowMs += 50;
  pump();  // 两帧: 首帧 dt=0 时钟未动(dx 同 t=0 不提交), 第二帧 clock 50 dx 收缩 -> x 提交继续涨
  ok("G 拍中改 instant 当前拍不中断(x 提交继续涨 —— 读点在判定帧 = 下一拍起)",
    u.setScaleLog.filter((r) => r[0] === "x").length > xAt);
  drain();
  ok("G smooth 拍照常收敛", u.data[1][4] === 30 && u._qbBeat.anim === null);
  u.data = [[1060, 1090, 1120, 1150, 1180], [0, 0, 0, 0, 40], [0, 0, 0, 0, 60]];
  const yBefore = u.setScaleLog.length;
  self._qbBeatStart("global", u);
  const xwG = u.setScaleLog.slice(yBefore).filter((r) => r[0] === "x");
  ok("G instant 下一拍: gate 拒绝 -> 瞬时落地目标锚视口恰一笔 x 提交([1060,1180] —— 旧 auto"
    + " 落地面随显式视口退役) + 数据语义不变(真值已落袋, L1 照跑)",
    xwG.length === 1 && xwG[0][1] === 1060 && xwG[0][2] === 1180
    && rafMap.size === 1 && u._qbBeat.anim.needsShift === false);
  drain();
  ok("G instant 拍尾点照常收敛(L1 不受左移策略影响)", u.data[1][4] === 40 && u._qbBeat.anim === null);
  global.window.AQB_FX_CFG = CFG;
}
// —— H. §05.3 shiftRatio 行: 下一拍起(拍中改不影响在途拍时间线) ——
{
  const u = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1120, 30, 120, 10, 55);
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  ok("H shiftRatio 0.6 -> 本拍 shiftMs 600", u._qbBeat.anim.tl.shiftMs === 600);
  global.window.AQB_FX_CFG = Object.assign({}, CFG, { shiftRatio: 0.2 });
  nowMs += 50;
  pump();
  ok("H 拍中改 0.2 在途拍时间线不变(600)", u._qbBeat.anim !== null && u._qbBeat.anim.tl.shiftMs === 600);
  drain();
  u.data = [[1060, 1090, 1120, 1150, 1180], [0, 0, 0, 0, 40], [0, 0, 0, 0, 60]];
  self._qbBeatStart("global", u);
  ok("H 下一拍 shiftMs 200(判定帧重读)", u._qbBeat.anim.tl.shiftMs === 200);
  drain();
  global.window.AQB_FX_CFG = CFG;
}
// —— I. §05.3 enabled 行 + §06 S3 行: 面板操作 -> 单一状态源 -> 下一拍装饰零绘制但 L0 照滚 ——
{
  const store = {};
  global.localStorage = {
    getItem: (k) => (k in store ? store[k] : null),
    setItem: (k, v) => { store[k] = String(v); },
    removeItem: () => {},
  };
  // 真处理器链: fxCheck(写 fx.enabled) -> persistQbFx(真方法, 写 store) -> _qbFxCfgSync(watcher
  // 等价, 真方法; fxOn 走 getter = enabled && !reduce) -> AQB_FX_CFG -> 下一拍
  const s2 = Object.assign({}, methods, { _qbPollMs: () => 3000, _qbCharts: {}, qbCurScope: "global",
    fxReduce: false, fx: JSON.parse(JSON.stringify(CFG)),
    fxPreviewing: false, fxBeatAt: 0, fxNow: 0 });
  Object.defineProperty(s2, "fxOn", { get() { return this.fx.enabled === true && !this.fxReduce; } });
  s2._qbFxCfgSync();
  ok("I 面板链前置: CFG.on = true(单一状态源同步面)", global.window.AQB_FX_CFG.on === true
    && global.window.AQB_FX_CFG.enabled === true);
  const u = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1120, 30, 120, 10, 55);
  s2._qbCharts = { global: u };
  s2._qbBeatStart("global", u);
  ok("I 开关开: 真拍 fx 在(装饰面启用)", u._qbBeat.anim.fx !== null);
  drain();
  s2.fxCheck("enabled", { target: { checked: false } });  // 面板总开关关闭(唯一写入入口)
  ok("I fxCheck 写唯一字段 fx.enabled + 真落盘(单键 JSON, enabled=false)",
    s2.fx.enabled === false && Object.keys(store).length === 1
    && JSON.parse(store[Object.keys(store)[0]]).enabled === false);
  s2._qbFxCfgSync();  // state.js watch.fx 的等价步(单点同步)
  ok("I CFG 同步: on=false(有效值 = enabled && !reduce 单点)", global.window.AQB_FX_CFG.on === false
    && global.window.AQB_FX_CFG.enabled === false);
  u.data = [[1060, 1090, 1120, 1150, 1180], [0, 0, 0, 0, 40], [0, 0, 0, 0, 60]];
  s2._qbBeatStart("global", u);
  ok("I 下一拍: L0 照滚(x 提交在, 数据刷新语义不是装饰 —— §05.6)",
    u.setScaleLog.some((r) => r[0] === "x" && r[1] === 1030) && rafMap.size === 1);
  ok("I 下一拍: 装饰零绘制(spawn 门 cfg.on !== true -> fx null)", u._qbBeat.anim.fx === null);
  drain();
  ok("I 关总开关收敛落地", u.data[1][4] === 40 && u._qbBeat.anim === null);
  // enabled=false 下预览空操作(没有动效可预览 —— §05.6/I7 同门)
  const before = { anim: u._qbBeat.anim, mirror: s2.fxPreviewing };
  s2._qbPreviewBeat("global");
  ok("I enabled=false 预览空操作(anim 不建, 镜像不动)", u._qbBeat.anim === before.anim
    && s2.fxPreviewing === false);
  // 处理器全链(评审 minor4): ease/shift/shiftRatio 与 enabled 同款端到端 —— 面板处理器 ->
  // store 单键 -> watch 等价(_qbFxCfgSync) -> CFG(绘制面唯一读点)
  s2.fxPick("ease", { target: { value: "linear" } });   // 下拉: change 直落盘
  s2._qbFxCfgSync();
  ok("I ease 处理器全链: fxPick 白名单放行 -> store.ease=linear -> CFG.ease=linear",
    s2.fx.ease === "linear" && JSON.parse(store[Object.keys(store)[0]]).ease === "linear"
    && global.window.AQB_FX_CFG.ease === "linear");
  s2.fxPick("shift", { target: { value: "instant" } });  // 左移策略对照档
  s2._qbFxCfgSync();
  ok("I shift 处理器全链: store.shift=instant -> CFG.shift=instant",
    JSON.parse(store[Object.keys(store)[0]]).shift === "instant"
    && global.window.AQB_FX_CFG.shift === "instant");
  s2.fxRange("shiftRatio", { target: { value: "40" } });  // 滑杆: input 写内存(显示 40 -> 存储 0.4)
  s2.persistQbFx();  // @change 落盘一次(拖拽全程不逐 tick 写 —— §05.5)
  s2._qbFxCfgSync();
  ok("I shiftRatio 处理器全链: /100 量纲 -> 0.4 + store + CFG",
    s2.fx.shiftRatio === 0.4 && JSON.parse(store[Object.keys(store)[0]]).shiftRatio === 0.4
    && global.window.AQB_FX_CFG.shiftRatio === 0.4);
  global.window.AQB_FX_CFG = CFG;  // 复原(本块 _qbFxCfgSync 已把 CFG 换成 on=false, 污染后续块)
}
// —— J. 状态行镜像(§05.3 状态行格式): fxBeatAt 只写当前 scope 的真拍; 预览不写 ——
{
  const s3 = Object.assign({}, methods, { _qbPollMs: () => 3000, _qbCharts: {}, qbCurScope: "",
    fxPreviewing: false, fxBeatAt: 0, fxNow: 0 });
  const u = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1120, 30, 120, 10, 55);
  s3._qbCharts = { global: u };
  s3._qbBeatStart("global", u);
  ok("J scope 不对齐不写镜像(qbCurScope=\"\")", s3.fxBeatAt === 0);
  drain();
  s3.qbCurScope = "global";
  s3._qbBeatStart("global", u);
  ok("J 真拍判定帧写 fxBeatAt(墙钟, 当前 scope)", s3.fxBeatAt > 0);
  drain();
  const at = s3.fxBeatAt;
  const u2 = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u2._qbBeat = mkBeat(1150, 30, 120, 30, 60);
  s3._qbCharts = { global: u2 };
  s3._qbPreviewBeat("global");
  drain();
  ok("J 预览不是真拍: fxBeatAt 不动(「上次真实拍」只吃真实拍)", s3.fxBeatAt === at
    && s3.fxPreviewing === false);
  // computed 展示面: 无真拍 — / 有真拍 X.X s 前 / 时钟未追上钳 0.0
  const age = computed.qbFxBeatAgeText;
  ok("J qbFxBeatAgeText: 无真拍显示 —", age.call({ fxBeatAt: 0, fxNow: 0 }) === "—");
  ok("J qbFxBeatAgeText: 4.2s 前", age.call({ fxBeatAt: 10000, fxNow: 14200 }) === "4.2 s 前");
  ok("J qbFxBeatAgeText: 时钟未追上钳 0.0(fxNow < fxBeatAt 不回 —)",
    age.call({ fxBeatAt: 14200, fxNow: 14000 }) === "0.0 s 前");
}
// —— K. 预览在途重排(_qbChartRescale): 假 target 不得当真值写回 ——
{
  const u = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1150, 30, 120, 30, 60);
  self._qbCharts = { global: u };
  self._qbPreviewBeat("global");
  for (let i = 0; i < 5; i++) { nowMs += 50; pump(); }  // clock 200: 收敛窗内, 假值已上屏
  ok("K 前置: 预览在途(假值已上屏)", u._qbBeat.anim !== null && u.data[1][4] !== 30
    && u.data[1][4] < 30);
  self._qbChartRescale("global");
  ok("K 重排走预览还原核心: 尾点回真值 + 状态机复位 + 镜像清(假值不落真值面)",
    u.data[1][4] === 30 && u.data[2][4] === 60 && self.fxPreviewing === false
    && u._qbBeat.tracks.up.target === 30 && u._qbBeat.tracks.up.delta === 0);
  ok("K 重排 setData 落真值 + anim 清", u.setDataCount >= 1 && u._qbBeat.anim === null);
}
// —— L. 面板缺省 scope: fxPreview() 无参走 qbCurScope(处理器面) ——
{
  const u = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1150, 30, 120, 30, 60);
  self._qbCharts = { global: u };
  self._qbPreviewBeat();
  ok("L 缺省 scope = qbCurScope(面板浮在当前图上)", u._qbBeat.anim !== null
    && u._qbBeat.anim.preview === 1);
  drain();
}
// —— M1. 假值不留痕的早退面(评审 minor1): 双轨钳在界(up 钳 0 + dl 钳轴顶)连点 -> !moving 早退,
//          取消的是在途预览(假值已上屏)必须走还原核心再退, 不滞留到下次真值落袋 ——
{
  const u = mkU(XS1, [0, 0, 0, 0, 0], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1150, 30, 120, 0, 60);
  self._qbCharts = { global: u };
  self._qbPreviewBeat("global");  // dl 60->63(贴轴钳, Δ0.05), up 0->0 钳 0 静默
  for (let i = 0; i < 5; i++) { nowMs += 50; pump(); }
  ok("M1 前置: 预览在途(假值已上屏, up 恒 0)", u._qbBeat.anim !== null
    && u._qbBeat.anim.preview === 1 && u.data[2][4] > 60);
  u._qbBeat.tracks.dl.shown = 63;  // 状态面预设(S11 同口径): dl 恰轴顶 —— 自然收敛仅 p=1 可达,
  u.data[2][4] = 63;               // 连点此刻起 target=63=shown -> moving=0 早退
  self._qbPreviewBeat("global");
  ok("M1 连点早退(!moving): 假值还原真值(尾点回 0/60) + 状态机复位 + 镜像清 + 不起新 anim",
    u.data[1][4] === 0 && u.data[2][4] === 60 && self.fxPreviewing === false
    && u._qbBeat.anim === null && u._qbBeat.tracks.dl.target === 60
    && u._qbBeat.tracks.dl.delta === 0);
}
// —— M2. 令牌失效门的兜底触发(评审 minor2): 门置空 anim 即同步清镜像, 「· 预览中」不卡常亮 ——
{
  const u = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1150, 30, 120, 30, 60);
  self._qbCharts = { global: u };
  self._qbPreviewBeat("global");
  u._qbBeat.previewToken = 99;  // 病理预设(状态面, S11 同口径): 令牌已走而 anim 未换 —— 门即触发
  nowMs += 50;
  pump();
  ok("M2 令牌门触发: anim 清 + 镜像清(兜底路径不把「· 预览中」卡成 true)",
    u._qbBeat.anim === null && self.fxPreviewing === false);
}
// —— N. 字段闭环 15 控件(§05.9 探针 第 1 项的电池级等价): 处理器逐个改 -> this.fx 写入 -> 单键 JSON
//          落盘 -> watch 等价(_qbFxCfgSync) -> CFG 同步。enabled(总开关, 第 16 个)已由块 I 端到端
//          覆盖; 「刷新后回读一致」面由 test_frontend_qb_fx_store_and_sanitize_battery 的
//          「合法值全字段保真」真跑 ——
{
  const store = {};
  global.localStorage = {
    getItem: (k) => (k in store ? store[k] : null),
    setItem: (k, v) => { store[k] = String(v); },
    removeItem: () => {},
  };
  const s4 = Object.assign({}, methods, { _qbPollMs: () => 3000, _qbCharts: {}, qbCurScope: "global",
    fxReduce: false, fx: JSON.parse(JSON.stringify(CFG)) });
  Object.defineProperty(s4, "fxOn", { get() { return this.fx.enabled === true && !this.fxReduce; } });
  s4._qbFxCfgSync();
  const stored = () => JSON.parse(store[QB_FX_STORE_KEY]);
  const cases = [
    ["pick", "ease", "linear", (fx) => fx.ease === "linear"],
    ["pick", "palette", "glitch", (fx) => fx.palette === "glitch"],
    ["pick", "shift", "instant", (fx) => fx.shift === "instant"],
    ["pick", "dual", "lead", (fx) => fx.dual === "lead"],
    ["pick", "tear", "random", (fx) => fx.tear === "random"],
    ["pick", "echoSpan", "200", (fx) => fx.echoSpan === "200"],
    ["range", "impact", 35, (fx) => fx.impact === 0.35],
    ["range", "particles", 50, (fx) => fx.particles === 0.5],
    ["range", "shiftRatio", 80, (fx) => fx.shiftRatio === 0.8],
    ["check", "neon", false, (fx) => fx.neon === false],
    ["check", "tail", true, (fx) => fx.tail === true],
    ["check", "layers.band", false, (fx) => fx.layers.band === false],
    ["check", "layers.particles", false, (fx) => fx.layers.particles === false],
    ["check", "layers.scan", false, (fx) => fx.layers.scan === false],
    ["check", "layers.grade", false, (fx) => fx.layers.grade === false],
  ];
  let bad = "";
  for (const [kind, key, val, expect] of cases) {
    const ev = kind === "check" ? { target: { checked: val } } : { target: { value: String(val) } };
    if (kind === "pick") s4.fxPick(key, ev);
    else if (kind === "range") s4.fxRange(key, ev);
    else s4.fxCheck(key, ev);
    if (kind === "range") s4.persistQbFx();  // 模板 @change 落盘一次(input 只写内存 —— §05.5)
    s4._qbFxCfgSync();                        // state.js watch.fx 的等价步
    if (!expect(s4.fx)) { bad = key + "(fx 未写)"; break; }
    if (!expect(stored())) { bad = key + "(store 未落盘)"; break; }
    if (!expect(global.window.AQB_FX_CFG)) { bad = key + "(CFG 未同步)"; break; }
  }
  ok("N 字段闭环 15 控件: 处理器逐个改 -> fx 写入 + 单键 JSON 落盘 + watch 等价 -> CFG 同步"
    + (bad ? " —— 失败于 " + bad : ""), bad === "");
  // 白名单兜一道: 非法枚举回落现值, 不落盘不生效(fxPick 的第二道防线)
  const before = stored();
  s4.fxPick("ease", { target: { value: "bogus" } });
  ok("N fxPick 非法枚举: 回落现值且 store 不动(白名单外的值写不进去)",
    s4.fx.ease === "linear" && JSON.stringify(stored()) === JSON.stringify(before));
}
console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
"""

# 面板接线 S3 预览同预算 node 电池(§05.4 第 6 条 + I9): 记账式 2d ctx 真 _qbDrawFx/_qbDrawFxScan
# 跑预览帧 —— 预览与真实拍共用同一 spawn/绘制代码路径, I9 预算(束体 ≤23 / 束+切片 ≤28 / 粒子
# ≤32)不为预览放宽。无 node 静默跳过(同 _NODE_QB_TRAFFIC_PROBE 口径)。
_NODE_QB_FXPANEL_BUDGET_PROBE = r"""
const fs = require("fs");
global.window = {};
const src = fs.readFileSync(process.argv[1], "utf8");
const { methods } =
  new Function(src + "\nreturn { methods: window.AQB_QB_TRAFFIC.methods };")();
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);
let rafId = 0;
const rafMap = new Map();
global.requestAnimationFrame = (cb) => { rafMap.set(++rafId, cb); return rafId; };
global.cancelAnimationFrame = (id) => { rafMap.delete(id); };
let nowMs = 0;
Object.defineProperty(global, "performance", { value: { now: () => nowMs }, configurable: true });
global.document = { hidden: false };
/* 记账式 2d ctx(同 S2-b 绘制电池口径: 只记不画) */
function mkCtx() {
  const ctx = {
    strokes: [], fillRects: [], ops: [], grads: [],
    _blur: 0, shadowColor: "", globalAlpha: 1,
    strokeStyle: "", fillStyle: "", lineWidth: 1, font: "", textAlign: "", textBaseline: "",
    canvas: { width: 900 },
    beginPath() {}, closePath() {}, arc() {},
    rect() {}, clip() {},
    fillText() {},
    scale() {}, save() {}, restore() {}, setLineDash() {},
    moveTo(x, y) { this.ops.push([x, y, "M"]); },
    lineTo(x, y) { this.ops.push([x, y, "L"]); },
    stroke() {
      this.strokes.push({ x: this.ops.length ? this.ops[0][0] : NaN, alpha: this.globalAlpha });
      this.ops.length = 0;
    },
    fill() {},
    fillRect(x, y, w, h) { this.fillRects.push([x, y, w, h, this.globalAlpha]); },
    createLinearGradient(x0, y0, x1, y1) {
      const g = { coords: [x0, y0, x1, y1], stops: [],
        addColorStop(p, c) { g.stops.push([p, String(c)]); } };
      this.grads.push(g);
      return g;
    },
  };
  return ctx;
}
const self = Object.assign({}, methods, { _qbPollMs: () => 3000, _qbCharts: {}, qbCurScope: "global",
  fxPreviewing: false, fxBeatAt: 0, fxNow: 0 });
/* glitch 档: 切片绘制门开 —— 束体+切片合计预算才有观测面(neon 档切片零绘制) */
const CFG = { v: 1, enabled: true, on: true, impact: 0.7, ease: "out", palette: "glitch",
  particles: 0.7, neon: true, tail: false, shift: "smooth", shiftRatio: 0.6, dual: "both",
  tear: "linked", echoSpan: "auto", layers: { band: true, particles: true, scan: true, grade: true } };
global.window.AQB_FX_CFG = CFG;
const XS1 = [1030, 1060, 1090, 1120, 1150];
const TK = { up: "#8B93F8", down: "#2FD4BF", grid: "#GRID", gap: "#GAP", axis: "#AXIS" };
function mkU(up, dl) {
  const u = {
    root: { isConnected: true },
    data: [XS1, up, dl],
    scales: { x: { min: XS1[0], max: XS1[4] }, y: { min: 0, max: 63 } },
    bbox: { left: 60, top: 10, width: 800, height: 300 },
    yCap: 0,
    pending: {},
    setScale(k, r) { this.pending[k] = { min: r.min, max: r.max }; },
    setData(d) { this.data = d; this.pending = { x: { min: d[0][0], max: d[0][d[0].length - 1] } }; this.commit(); },
    redraw() { this.pending.x = { min: this.scales.x.min, max: this.scales.x.max }; this.commit(); },
    valToPos(v, k) {
      const s = this.scales[k];
      return k === "x" ? ((v - s.min) / (s.max - s.min)) * 800 : (1 - (v - s.min) / (s.max - s.min)) * 300;
    },
    commit() {
      const px = this.pending.x, py = this.pending.y;
      this.pending = {};
      if (px) this.scales.x = { min: px.min, max: px.max };
      if (py) this.scales.y = { min: py.min, max: py.max };
    },
  };
  return u;
}
const pump = () => { const fns = [...rafMap.values()]; rafMap.clear(); fns.forEach((f) => f()); };
function mkBeatConv() {
  return { raf: 0, anim: null, xs0: 1000, n: 5, tracks: {
    up: { prev: 30, target: 30, shown: 30, delta: 0, level: 0, live: true },
    dl: { prev: 60, target: 60, shown: 60, delta: 0, level: 0, live: true } } };
}
// —— B1. 预览 spawn 预算面(与真拍同一 _qbFxSpawn/常量: 粒子 ≤32 / 半套 ≤16 / 切片 ≤5 / 梳齿 ≤7) ——
{
  const u = mkU([0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeatConv();
  self._qbCharts = { global: u };
  self._qbPreviewBeat("global");
  const fx = u._qbBeat.anim && u._qbBeat.anim.fx;
  ok("B1 预览 spawn 走真拍同一条 _qbFxSpawn(fx 非 null, lead/等级在)",
    !!fx && fx.lead === "up" && fx.lv === 3);
  ok("B1 I9 预算面: cap <= 32 / 半套各 <= 16 / 合计守恒 / 清单长度 = alloc",
    !!fx && fx.cap <= 32 && fx.alloc.up <= 16 && fx.alloc.dl <= 16
    && fx.alloc.up + fx.alloc.dl + fx.alloc.merge <= 32
    && fx.specs.up.length === fx.alloc.up && fx.specs.dl.length === fx.alloc.dl);
  ok("B1 R6 清单预算: 切片 <= 5 / 梳齿 <= 7(横向细线合计 <= 12)",
    !!fx && fx.slices.length <= 5 && fx.comb.length <= 7 && fx.slices.length + fx.comb.length <= 12);
}
// —— B2. 预览帧记账: 束体逐帧 <=23, 束体+切片 <=28(glitch 双开) —— 与真拍同预算不为预览放宽 ——
{
  const u = mkU([0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeatConv();
  self._qbCharts = { global: u };
  self._qbPreviewBeat("global");
  let capScan = 0;
  let capTotal = 0;
  for (let t = 0; t <= 570; t += 30) {
    u._qbBeat.anim.clock = t;
    // 分域计数(S2-b S7 同款合成): _qbDrawFx 内部会调 _qbDrawFxScan, 同 ctx 直数会重复计束体
    // —— 束体段独立 ctx 计数(<=23), 切片在 scan=false 的 fx 段专数 fillRect(切片是 fx 域唯一
    // fillRect, 其余层全 stroke/fill)
    u.ctx = mkCtx();
    methods._qbDrawFxScan.call(methods, u, TK);
    const scanN = u.ctx.strokes.length + u.ctx.fillRects.length;
    global.window.AQB_FX_CFG = Object.assign({}, CFG,
      { layers: Object.assign({}, CFG.layers, { scan: false }) });
    u.ctx = mkCtx();
    methods._qbDrawFx.call(methods, u, TK);
    global.window.AQB_FX_CFG = CFG;
    const sliceN = u.ctx.fillRects.length;
    capScan = Math.max(capScan, scanN);
    capTotal = Math.max(capTotal, scanN + sliceN);
  }
  ok("B2 预览帧束体逐帧 <=23(与真拍 I9-R5 同一上限)", capScan <= 23);
  ok("B2 预览帧束体+切片逐帧 <=28(glitch 切片门开 —— §05.4 第 6 条同预算)", capTotal <= 28);
  ok("B2 预览帧确有装饰墨量(预算面不是空转: 束体峰值 >= 19 —— 与真拍分窗恰值同源)", capScan >= 19);
  pump();
}
// —— B3. 连点 5 次: 每次整 anim 替换(单一 fx 集, 无两套叠加), 预算不随重启放大 ——
{
  const u = mkU([0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeatConv();
  self._qbCharts = { global: u };
  let allOk = true;
  for (let i = 0; i < 5; i++) {
    self._qbPreviewBeat("global");
    nowMs += 30;
    pump();
    const fx = u._qbBeat.anim && u._qbBeat.anim.fx;
    const parts = fx ? fx.specs.up.length + fx.specs.dl.length
      + (fx.specs.merge ? fx.specs.merge.length : 0) : -1;
    if (!(fx && fx.cap <= 32 && parts <= 32)) allOk = false;
  }
  ok("B3 连点 5 次全程单一 fx 且粒子合计 <=32(§05.9 连点探针口径 —— 不出现两套叠加)", allOk);
  pump();
}
console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
"""


def test_frontend_qb_fx_panel_wiring_battery():
    """面板接线 S3 电池 + 接缝静态钉(plan 26-11-12-1139 §05.3/§05.4/§05.9/§06 S3 行, D21)

    行为面(node 电池 x2, 无 node 静默跳过, 同节拍内核口径):
    1. 调度器行为电池 —— §05.4 预览一拍六条语义逐条真跑:
       1) 不动窗口: anim.needsShift=false/dx0=0, 预览全程零 setScale("x")(dx ≡ 0), xs 与
         u.scales.x 逐帧零变化(§05.9 预览拍探针口径); 末帧 setData 交还 auto;
       2) 假 Δ 贴近真实量级: mag=clamp(0.18+0.35×密度, 0.10, 0.50) 相对 Δ 恰 mag, 方向按轨
         up 减/dl 加(计划伪代码 k === 'dl' ? mag : -mag), 密度 0 -> 0.18 Lv.2(不固定拉满
         Lv.3)/0.7 -> 0.425 Lv.3/1 -> 0.50 钳上界 Lv.3; 生产域适配: target 钳 [0, yMax]
         (贴轴 Δ 被轴档压制 —— 预览零跳轴优先, 对应计划伪代码 clamp(.., 0.06, 0.94) 值域钳);
         零流量 up 减钳 0 诚实静默; 死轨(live=false)不参与预览不造假复活;
       3) 连点重启: previewToken 逐次递增且 anim 携带当前 token(旧帧被 _qbBeatFrame 令牌门
         失效), 从当前显示值接续(禁止回跳 —— I3), 还原点继承首拍捕获(中途假值不落还原点),
         不排队不叠加 + 连点 rAF 单飞钉(旧帧已摘, 删 _qbBeatCancel 的变异即红);
       4) 真值抢占: 预览在途真拍到达(快路 setData 整组落真窗口 -> 判定帧) -> 预览取消/镜像清/
         新拍以预览中断显示值接续(prev=中断值, target=新真值)并照常收敛; 对偶: 真拍主区在途
         预览忽略(真值优先), 次区装饰相位无真值语义可被预览接管;
       5) 不写 store: 预览零持久化(静态钉 persistQbFx/localStorage 不在预览域), 末帧还原
         真值显示面 + 双轨状态机复位到真值对齐(假值不留痕); 预览在途 _qbChartRescale 走
         _qbPreviewRestore(假 target 不得当真值写回) + 连点早退(!moving/!n)同走还原核心
         (双轨钳在界的连点, 假值不滞留到下次真值落袋 —— 评审 minor1);
       6) 同预算: 见 2;
       附加: 预览不自动循环(静态钉零定时器)/enabled=false(与 reduce 同门 cfg.on)预览空操作/
       状态行镜像(fxBeatAt 只写当前 scope 真拍、预览不写; fxPreviewing 翻转沿; qbFxBeatAgeText
       三态: — / 4.2 s 前 / 时钟未追上钳 0.0)/缺省 scope = qbCurScope(处理器面 fxPreview)/
       令牌门兜底触发同步清镜像(「· 预览中」不卡常亮 —— 评审 minor2)。
    2. 预览同预算电池(记账式 2d ctx 真 _qbDrawFx/_qbDrawFxScan): 预览 spawn 走真拍同一条
       _qbFxSpawn(I9 面逐条: cap ≤32/半套 ≤16/合计守恒/清单=alloc/R6 切片 ≤5+梳齿 ≤7) +
       预览帧逐帧束体 ≤23、束体+切片 ≤28(glitch 双开)且有装饰墨量(峰值 ≥19 防空转)+ 连点
       5 次全程单一 fx 集粒子合计 ≤32(§05.9 连点探针)。
    3. ease 消费(§05.3 ease 行 + D21 唯一例外条款): _qbFxCurve 选择单点(out/linear/未知回落)/
       _qbFxLinear 恒等夹取/_qbFxShown 单次施加(out(0.5)=0.875 —— 修正 S1 遗留的帧循环预
       easeOut + _qbFxShown 再 easeOut 双重施加, 与计划 §03 公式及 §04 演示单次口径对齐);
       真拍 out vs linear 收敛序列形状不同(out 前载, clock 200 帧 24.07 vs 16.67, p=200/600)且都单调
       收敛终点恰真值; 拍中改 ease 当前拍不换式(冻结引用不变 + 逐帧序列与全程 out 参考拍
       逐帧一致); 下一拍起用(判定帧重读, linear 数值形状断言); 预览起拍同款冻结。
    4. 字段贯通收口(§05.9 字段闭环的「改值 -> 行为变化」面):
       shift: instant 下一拍 L0 过渡不播(零 x 提交)但数据语义不变(L1 照常收敛), 拍中改档
         当前拍不中断; shiftRatio: 拍中改 0.2 在途拍时间线不变(600), 下一拍 200;
       enabled: 面板操作全链(fxCheck 写唯一字段 fx.enabled -> persistQbFx 真落盘单键 ->
       _qbFxCfgSync 单点同步 on=false) -> 下一拍装饰零绘制(fx null)但 L0 照滚(x 提交在 ——
       §05.6 数据刷新语义不是装饰); ease/shift/shiftRatio 处理器全链同款端到端
       (fxPick/fxRange -> store 单键 -> CFG, shiftRatio 验 /100 量纲与 @change 落盘一次 ——
       评审 minor4);
       tail(=false 无次区相位/t=true 收敛帧衔接/拍内关下一帧收尾)由视觉引擎电池 F1a/F5/F6
       覆盖, impact/tear/echoSpan/layers/palette/particles/dual/neon 由 S2-a/S2-b 电池覆盖;
    5. S4-a 盘点轮补字段闭环面(§05.9 探针 第 1 项电池级): N 块 15 控件逐个改(fxPick 六下拉/
       fxRange 三滑杆/fxCheck 六复选含 layers.* 四键) -> this.fx 写入 + 单键 JSON 落盘
       (fxRange 验 @change 落盘一次/input 只写内存) + watch 等价(_qbFxCfgSync) -> CFG 同步 +
       fxPick 非法枚举回落现值不落盘(白名单兜一道); enabled(总开关)已由块 I 端到端覆盖,
       「刷新后回读一致」面由存储电池「合法值全字段保真」真跑; 接缝 g: fx-panel.html 15 控件
       绑定串全量钉住(处理器/字段键改名 = 面板死控件, 行为电池直接调方法测不到模板漂移)。
    接缝面(静态钉):
    a. 预览三方法域(_qbPreviewBeat/_qbPreviewRestore/_qbPreviewEnd)剥不出 persistQbFx/
       localStorage(不写 store)/零 setInterval 与 setTimeout(不自动循环 —— 与真实拍撞车且
       真假不可辨, D21);
    b. ease 消费单点唯一: function _qbFxCurve 定义恰 1 + 调用恰 2(真拍 _qbBeatStart 与预览
       _qbPreviewBeat 两个判定帧)、cfg.ease 恰 2 处、S1 的帧循环预折算行
       `_qbFxEaseOut((a.clock` 已退场、L1 两轨经 _qbFxShown(track, p, a.easeF) 消费冻结曲线、
       L0 每帧 dx 行恒 easeOut(经单点 _qbFxEaseOut(_qbAnimAnchorAt 内, a.clock / a.tl.shiftMs) —— 插值曲线只作用于数值收敛);
    c. shift 消费点: cfg.shift === "instant" 在 _qbBeatStart 判定帧(零消费字段补齐);
    d. 预览接缝: _qbBeatFrame 令牌失效门(a.preview !== st.previewToken) + 末帧分支
       _qbPreviewEnd(scope, u) 先于 _qbBeatConverge + 预览收口显式锚视口在位钉(_qbPreviewEnd
       域内 setScale("x", 锚视口) —— 不变量(1)第四个写点, 列与锚视口同形时行为电池拦不住
       重申行被删)+ y 成对钉在位(y 紧跟 x 重申, rescale 静态钉 j 同款形态) +
       _qbChartRescale 预览支路
       _qbPreviewRestore(u, st.anim) + _qbBeatCancel 清镜像(真值抢占/销毁/宿主被拆三路覆盖);
    e. 状态行: fx-panel.html 状态行含 qbFxBeatAgeText 回填与 v-if="fxPreviewing"「· 预览中」
       后缀(§05.3 状态行格式), state.js 显式建 fxPreviewing/fxBeatAt/fxNow 三镜像字段
       (undefined 是非响应式盲区), 1s 步进时钟装在 _qbFxListen 开面板支路/关面板与
       beforeUnmount 双清(无常驻定时器);
    f. 双入口单状态源(§06 S3 行「两个开关入口状态一致」的 R8 终态): P4 右键勾选项已被 D24
       关闭 —— 面板总开关是唯一入口, 图宿主 contextmenu 监听只 openFxPanel 零开关语义,
       qb_traffic_chart.js 零 fx.enabled 赋值面(第二状态源无从产生); fx-panel.html 总开关
       :checked="fxOn"(显示有效值)+ @change="fxCheck('enabled')"(唯一写入入口)。"""
    shared = os.path.join(STATIC_ROOT, "shared")
    js = open(os.path.join(shared, "qb_traffic_chart.js"), encoding="utf-8").read()
    tpl = open(os.path.join(shared, "tpl", "fx-panel.html"), encoding="utf-8").read()
    stjs = open(os.path.join(shared, "state.js"), encoding="utf-8").read()
    # —— a. 预览三方法域零持久化零定时器(§05.4 第 5 条 + 不自动循环) ——
    pvb = re.search(r"_qbPreviewBeat\(scope\) \{\n(.*?)\n    \},", js, re.S)
    pvr = re.search(r"_qbPreviewRestore\(u, a\) \{\n(.*?)\n    \},", js, re.S)
    pve = re.search(r"_qbPreviewEnd\(scope, u\) \{\n(.*?)\n    \},", js, re.S)
    assert pvb and pvr and pve, "缺预览三方法(_qbPreviewBeat/_qbPreviewRestore/_qbPreviewEnd)"
    for name, blk in (
        ("_qbPreviewBeat", pvb.group(1)), ("_qbPreviewRestore", pvr.group(1)), ("_qbPreviewEnd", pve.group(1))
    ):
        assert "persistQbFx" not in blk and "localStorage" not in blk, \
            f"{name} 域不得触碰持久化面(预览不写 store —— §05.4 第 5 条)"
        assert "setInterval" not in blk and "setTimeout" not in blk, \
            f"{name} 域不得有定时器(预览不自动循环 —— D21: 与真拍撞车且真假不可辨)"
    assert "this._qbPreviewBeat();" in js, "面板 fxPreview 处理器必须交调度器域 _qbPreviewBeat"
    # —— b. ease 消费单点唯一(§05.3 ease=数值插值曲线; D21 拍内不换式) ——
    # 计数面剥注释(注释里的口径描述不计 —— 只钉代码事实)
    js_code = re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", js, flags=re.S))
    assert js.count("function _qbFxCurve(ease)") == 1, "ease 曲线选择单点 _qbFxCurve 必须恰 1 处定义"
    assert js_code.count("_qbFxCurve(") == 4, \
        "_qbFxCurve 恰 定义1+调用3(真拍 _qbBeatStart 主路 + 零变化拍 F6/D3 环境层解绑支路 + 预览" \
        " _qbPreviewBeat 三个判定帧), 第四处读点回潮即双写漂移"
    assert js_code.count("cfg.ease") == 3, \
        "cfg.ease 读点必须恰 3 处(三个判定帧冻结), 帧循环/绘制面直读 cfg.ease 回潮即拍内换式"
    assert "_qbFxEaseOut((a.clock" not in js, \
        "S1 的帧循环预折算(预 easeOut 后 _qbFxShown 再 easeOut 的双重施加)必须退场 —— ease 单次施加于 _qbFxShown(计划 §03 公式/§04 演示口径)"
    assert "_qbFxShown(tr.up, p, a.easeF)" in js and "_qbFxShown(tr.dl, p, a.easeF)" in js, \
        "L1 两轨收敛必须消费判定帧冻结的 anim.easeF(拍内不换式 —— D21)"
    assert js.count("_qbFxEaseOut(a.clock / a.tl.shiftMs)") == 1, \
        "L0 每帧 dx 行恒 easeOut 恰 1 处(单点 _qbAnimAnchorAt 内 —— 帧循环与打断捕获续滑共用," \
        " 第二处 easeOut 时钟行回潮即 rem 漂移/打断回潮; ease 只作用于数值收敛, L0 位移不随 ease 变 —— §05.3)"
    # —— c. shift 消费点(S3 补齐零消费字段; instant 判据随滑动门 _qbFxShiftGate 单点,
    #    消费仍在判定帧链路 —— 门内判据 + 判定帧调用双钉) ——
    gate_blk = re.search(r"function _qbFxShiftGate\(cfg, u, nWin\) \{\n(.*?)\n\}", js, re.S)
    assert gate_blk and 'cfg.shift === "instant"' in gate_blk.group(1), \
        "滑动门缺 cfg.shift === instant 消费(面板左移策略对照档零消费即字段贯通缺口)"
    bsb = re.search(r"_qbBeatStart\(scope, u\) \{\n(.*?)\n    \},", js, re.S)
    assert bsb, "缺 _qbBeatStart(判定帧)"
    assert "const slide = !reduce && !j.rewin && disp > 0 && haveVp && _qbFxShiftGate(cfg, u, nWin);" in bsb.group(1), \
        "判定帧缺滑动门消费(instant 判据不在判定帧链路 = 字段贯通缺口; 尾锚显式视口下滑动门 = " \
        " _qbFxShiftGate(cfg, u, nWin), reduce/rewin/零位移/亚可见四分量在位 —— 打断续滑同门)"
    # —— d. 预览接缝(令牌门/末帧分支/重排支路/取消清镜像) + 预览收口 x 重申 + y 成对钉在位 ——
    frb = re.search(r"_qbBeatFrame\(scope\) \{\n(.*?)\n    \},", js, re.S)
    assert frb, "缺 _qbBeatFrame"
    frb_body = frb.group(1)
    assert "a.preview !== undefined && a.preview !== st.previewToken" in frb_body, \
        "帧循环缺预览令牌失效门(previewToken 递增即令旧帧失效 —— §05.4 第 3 条)"
    assert frb_body.find("this._qbPreviewEnd(scope, u);") < frb_body.find("this._qbBeatConverge(scope, u);") \
        and "this._qbPreviewEnd(scope, u);" in frb_body, \
        "预览末帧必须走 _qbPreviewEnd(还原真值显示面)且先于 _qbBeatConverge 分支(那是把 target 当真值写回)"
    assert 'u.setScale("x", { min: st.anchor - st.span, max: st.anchor });' in pve.group(1), \
        "预览收口缺显式锚视口在位钉(不变量(1)第四个 setData 写点: B 案例列与锚视口同形, 交还" \
        " auto 与重申值相等、xLogs 只采 anim 在途帧 —— 重申行被删行为电池拦不住, rescale 静态钉" \
        " j 同款形态)"
    assert 'u.setScale("y", { min: 0, max: a.yMax });' in pve.group(1) \
        and pve.group(1).index('u.setScale("x", { min: st.anchor - st.span, max: st.anchor });') \
        < pve.group(1).index('u.setScale("y", { min: 0, max: a.yMax });'), \
        "预览收口的 y 钉必须紧跟 x 重申成对(setData 交还 auto 后 pending 消费按锚窗可视数据重推" \
        " y —— 预览起拍读到的 yMax 原样钉回终态零跳变, rescale 静态钉 j 同款形态)"
    rsb = re.search(r"_qbChartRescale\(scope\) \{\n(.*?)\n    \},", js, re.S)
    assert rsb and "this._qbPreviewRestore(u, st.anim);" in rsb.group(1), \
        "重排收口缺预览支路(预览在途假 target 不得走真值落袋路)"
    ccb = re.search(r"_qbBeatCancel\(u\) \{\n(.*?)\n    \},", js, re.S)
    assert ccb and "st.anim.preview !== undefined" in ccb.group(1) and "this.fxPreviewing = false;" in ccb.group(1), \
        "取消在途拍必须同步清「· 预览中」镜像(真值抢占/销毁/宿主被拆三路覆盖)"
    assert "easeF: _qbFxCurve(cfg ? cfg.ease : undefined)" in bsb.group(1), \
        "真拍判定帧缺 ease 冻结进 anim(_qbFxCurve 单点)"
    assert "easeF: _qbFxCurve(cfg.ease)" in pvb.group(1), \
        "预览判定帧缺 ease 冻结进 anim(与真拍同款 —— §05.4 预览与真实拍同构)"
    # —— e. 状态行(§05.3 格式: 三值 + 预览中后缀)与镜像字段/1s 时钟 ——
    assert "qbFxBeatAgeText" in tpl and 'v-if="fxPreviewing"' in tpl and "· 预览中" in tpl, \
        "面板状态行缺「上次真实拍 Xs 前」回填与「· 预览中」后缀(§05.3 状态行格式)"
    assert "fxPreviewing: false" in stjs and "fxBeatAt: 0" in stjs and "fxNow: 0" in stjs, \
        "state.js 缺状态行镜像显式建字段(undefined 是非响应式盲区)"
    assert "setInterval(() => { this.fxNow = Date.now(); }, 1000)" in js \
        and js.count("clearInterval(this._qbFxClock)") == 2, \
        "1s 步进时钟必须装在开面板支路且关面板/beforeUnmount 双清(无常驻定时器)"
    assert "if (scope === this.qbCurScope) this.fxBeatAt = Date.now();" in bsb.group(1), \
        "判定帧缺「上次真实拍」镜像写入(仅当前 scope —— 面板浮着的图)"
    # —— f. 双入口单状态源(R8 终态: 面板总开关唯一入口, D24) ——
    assert ':checked="fxOn"' in tpl and "@change=\"fxCheck('enabled', $event)\"" in tpl, \
        "面板总开关必须显示有效值 fxOn 并经 fxCheck('enabled') 唯一写入"
    assert re.search(r"fx\.enabled\s*=(?!=)", js_code) is None, \
        "qb_traffic_chart.js 不得出现 fx.enabled 赋值面(enabled 只经 fxCheck/fxReset 通用路径写 —— 第二状态源无从产生)"
    assert "this.openFxPanel(ev.clientX, ev.clientY);" in js, \
        "图宿主 contextmenu 监听只开面板(右键勾选项已被 R8 D24 关闭 —— 无第二开关入口)"
    # —— g. 15 控件模板绑定全量(§05.9 探针 第 1 项的接线面: 处理器/字段键被改名 = 面板死控件,
    #        行为电池直接调方法测不到模板漂移, 故逐条钉绑定串) ——
    for bind in (
        "@input=\"fxRange('impact', $event)\"",
        "@input=\"fxRange('particles', $event)\"",
        "@input=\"fxRange('shiftRatio', $event)\"",
        "@change=\"fxPick('ease', $event)\"",
        "@change=\"fxPick('palette', $event)\"",
        "@change=\"fxPick('shift', $event)\"",
        "@change=\"fxPick('dual', $event)\"",
        "@change=\"fxPick('tear', $event)\"",
        "@change=\"fxPick('echoSpan', $event)\"",
        "@change=\"fxCheck('enabled', $event)\"",
        "@change=\"fxCheck('neon', $event)\"",
        "@change=\"fxCheck('tail', $event)\"",
        "@change=\"fxCheck('layers.band', $event)\"",
        "@change=\"fxCheck('layers.particles', $event)\"",
        "@change=\"fxCheck('layers.scan', $event)\"",
        "@change=\"fxCheck('layers.grade', $event)\"",
        # 滑杆落盘面(fx-panel.html impact/particles/shiftRatio 三行): @input 只写内存,
        # @change 落盘一次(§05.5) —— 与 fxRange 输入绑定的成对串逐条钉(漏一条 = 拖完不落盘)
        "@input=\"fxRange('impact', $event)\" @change=\"persistQbFx()\"",
        "@input=\"fxRange('particles', $event)\" @change=\"persistQbFx()\"",
        "@input=\"fxRange('shiftRatio', $event)\" @change=\"persistQbFx()\"",
    ):
        assert bind in tpl, f"fx-panel.html 缺控件绑定 {bind}(15 控件逐个接线, 任一漂移 = 死控件)"
    # —— 行为面 node 电池(调度器行为 + 预览同预算各一发) ——
    node = shutil.which("node")
    if not node:
        return
    for probe, tag in (
        (_NODE_QB_FXPANEL_SCHED_PROBE, "S3 面板接线调度器行为"),
        (_NODE_QB_FXPANEL_BUDGET_PROBE, "S3 预览同预算"),
    ):
        proc = subprocess.run(
            [node, "-e", _NODE_STDIN_WRAPPER,
             os.path.join(shared, "qb_traffic_chart.js")],
            input=probe,
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
      顶部说明行「系统要求减弱动效，当前不生效」; 有效值 on 不进持久化形状(QB_FX_DEFAULTS 无 on)。
    4. S4-a 盘点轮补 §05.9 探针 第 6 项/第 9 项的电池级等价(section 5): openFxPanel 经 overlay_fit 单点
      钳位 + 图宿主右缘钳位(面板右缘距宿主右缘 >= 8px, QB_FX_PANEL_W 单点) + 重开复位 alt;
      Alt 看穿三路接线(keydown/keyup 同处理器按 e.altKey 写态 + 面板不可见早退 + blur 失焦
      复位防卡看穿态); 四皮肤 .fx-panel CSS 成对(fixed 本体/max-height 视口兜底/fx-alt 看穿/
      120ms 仅 opacity/reduce 零动画) + D20 渗色禁令(fx CSS 段剥注释后零 --today-up/
      --today-down)。rect 实测(底边不出视口/滑杆可用/Alt 穿透到画布)仍归 e2e(P8)。S4-b 轮追加
      5b(评审 major1/minor3): 面板实高变化的三条 refit 触发面静态钉 —— details @toggle="fxRefitSoon"
      恰 1 处 + fxRefitSoon 转发定义恰 1 处 + state.js fxPreviewing/fxReduce 两翻转沿汇 fxRefitSoon
      恰 2 处(高级折叠/预览中后缀/reduce 说明行改变面板高度, 不重钳位则贴底面板底边越出视口)。"""
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
    # 恢复面处理器极性(§05.9 第 8 项「恢复 no-preference 后总开关回到用户手动值」的单步):
    # change 处理器必须按 matches === true 写 fxReduce(极性写反 = 恢复后有效值不跟手)
    assert "this.fxReduce = this._qbFxMql.matches === true" in mo_m.group(1), \
        "mounted 的 reduce change 处理器缺极性行(this.fxReduce = _qbFxMql.matches === true —— " \
        "恢复 no-preference 后 fxReduce 翻回 false, 有效值回到用户手动值)"
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
    # fxReduce 是双 watcher 数组(S4-b 评审轮 2: pre 沿管 CFG 同步, 重钳沿必须 flush post ——
    # pre 在重渲染前触发, leading 分支读旧高且单次调用不排 trailing, 贴底面板底边越出视口)
    redw_m = re.search(r"fxReduce: \[(.*?)\n    \],", state_js, re.S)
    assert redw_m and "this._qbFxCfgSync()" in redw_m.group(1) \
        and 'flush: "post"' in redw_m.group(1) and "this.fxRefitSoon();" in redw_m.group(1), \
        "state.js fxReduce 缺双 watcher(pre 沿 _qbFxCfgSync + post 沿 fxRefitSoon 重钳 —— " \
        "reduce 翻转 on 必须立即跟翻, 且实高变化的重钳沿不得用默认 pre)"
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

    # 5. 不遮挡与看穿(§05.9 探针 第 6 项/第 9 项的电池级等价): openFxPanel 钳位(面板右缘距图宿主右缘
    #    >= 8px, overlay_fit 单点只夹视口不压缩尺寸) + Alt 看穿三路接线(keydown/keyup/blur) +
    #    四皮肤 .fx-panel CSS 成对(中性令牌) + D20 渗色禁令(--today-up/down 不进面板 CSS 段)。
    #    rect 实测(底边不出视口/滑杆可用)仍归 e2e(P8), 这里钉的是接线与令牌面。
    open_blk = re.search(r"openFxPanel\(px, py\) \{\n(.*?)\n    \},", js, re.S)
    assert open_blk, "qb_traffic_chart.js 缺 openFxPanel(右键开面板单点)"
    ob = open_blk.group(1)
    assert "window.AQB_OVERLAY_FIT" in ob and "FIT.fitInViewport(null, x" in ob, \
        "openFxPanel 必须经 overlay_fit 单点钳位(手写夹取回潮即红 —— 几何单点纪律)"
    assert "host.getBoundingClientRect().right - FIT.EDGE - QB_FX_PANEL_W" in ob, \
        "openFxPanel 缺图宿主右缘钳位(面板右缘距宿主右缘 >= 8px —— §05.9 不遮挡探针的静态面)"
    assert "alt: false" in ob, "openFxPanel 必须复位 alt(重开不残留看穿态)"
    assert "window.addEventListener(\"keydown\", this._qbFxOnAltKey)" in listen_body \
        and "window.addEventListener(\"keyup\", this._qbFxOnAltKey)" in listen_body, \
        "Alt 看穿缺 keydown/keyup 监听(按住 Alt 临时透明, 松开恢复 —— §05.9 第 6 项)"
    assert "this.fxPanel.alt = e.altKey === true;" in listen_body \
        and "if (!this.fxPanel.visible) return;" in listen_body, \
        "Alt 处理器必须按 e.altKey 写看穿态且面板不可见早退"
    assert "this._qbFxOnBlur = () => { this.fxPanel.alt = false; };" in listen_body \
        and "window.addEventListener(\"blur\", this._qbFxOnBlur)" in listen_body, \
        "Alt+Tab 离场 keyup 丢失必须 blur 复位(防卡在看穿态 —— §05.1)"
    for css, name in (
        (_ui_css_aggregate("atlas"), "atlas"),
        (_ui_css_aggregate("console"), "console"),
        (_ui_css_aggregate("prism"), "prism"),
        (_ui_css_aggregate("flux"), "flux"),
    ):
        for rule, what in (
            (".fx-panel { position: fixed", "面板浮层本体(fixed 非模态, z-index 90)"),
            ("max-height: calc(100vh - 16px)", "视口内兜底(底边不出视口 + 正文内部滚动)"),
            (".fx-panel.fx-alt { opacity: .22; pointer-events: none; }", "Alt 看穿(临时透明 + 放行指针)"),
            (
                ".fx-pop-enter-active, .fx-pop-leave-active { transition: opacity 120ms var(--ease); }",
                "开合 120ms 仅 opacity(零位移)"
            ),
            (
                "@media (prefers-reduced-motion: reduce) { .fx-pop-enter-active, .fx-pop-leave-active"
                " { transition: none; } }", "reduce 零动画(面板不能成为动效后门)"
            ),
        ):
            assert rule in css, f"{name} 缺 {rule}({what}) —— 四皮肤 CSS 必须成对改"
        # 渗色禁令(D20): fx 面板 CSS 段剥注释后零 --today-up/--today-down(曲线语义色冒用到设置件
        # 会让人以为滑杆调的是某条曲线; 段从块头注释起, 先剥 /* */ 再查 —— 注释里的禁令原文不计)
        seg = css[css.index("/* ================= 动效数值面板"):]
        seg_code = re.sub(r"/\*.*?\*/", "", seg, flags=re.S)
        assert "--today-up" not in seg_code and "--today-down" not in seg_code, \
            f"{name} 的 fx 面板 CSS 段出现曲线语义色令牌(D20 渗色禁令)"

    # 5b. 实高变化的 refit 触发面(S4-b): 高级折叠开合 / 状态行「· 预览中」后缀翻转 / reduce
    #     说明行翻转三者都改变面板真实高度, 而 _qbFxRefitSoon 的既有触发面(fxPanel watcher/
    #     resize/scroll/宿主 RO)都不含它们 —— 不重钳位, 贴底钳位过的面板底边越出视口(§05.9),
    #     底栏按钮点不到。两条静态钉钉「接线在位」: rect 实测归 e2e(traffic-fx-panel 的
    #     四皮肤 rect 用例展开高级后 poll 底边)。Vue 生产构建(vue.global.prod.js 3.5.13)对模板缺
    #     失处理器**完全静默**(警告仅 dev 构建 —— 无 console.warn, e2e 的 installRuntimeErrorGuard
    #     只收 console.error/pageerror, 对此同样零捕获) —— 接线断掉没有任何运行时报错面, 这里是
    #     fxRefitSoon 的**接线面唯一闸**
    #     (行为面另由 traffic-fx-panel 四皮肤 rect 展开例覆盖, 但其判红依赖贴底钳位几何成立,
    #     点击点不在贴底区时不会红 —— 两层闸互补, 各管各的面)。
    #     计数面剥 HTML 注释(注释里的口径描述不计 —— 只钉代码事实)。
    fx_tpl_code = re.sub(r"<!--.*?-->", "", fx_tpl, flags=re.S)
    assert fx_tpl_code.count('@toggle="fxRefitSoon"') == 1, \
        "fx-panel.html 高级折叠缺 @toggle=\"fxRefitSoon\" 恰 1 处(开合改变面板实高, 不重钳位则贴底面板底边越出视口)"
    assert fx_tpl_code.count("fxRefitSoon") == 1, \
        "fx-panel.html 出现多余 fxRefitSoon 引用(模板只负责 details 开合一处, 其余高度变化走 state.js 翻转沿)"
    refit_m = re.search(r"fxRefitSoon\(\) \{\n(.*?)\n    \},", js, re.S)
    assert refit_m and refit_m.group(1).strip() == "this._qbFxRefitSoon();", \
        "qb_traffic_chart.js 缺 fxRefitSoon 公开转发单点或转发面变了(必须原样转 _qbFxRefitSoon 节流单点 —— 模板触达不得带 _ 前缀)"
    assert js.count("fxRefitSoon() {") == 1, "fxRefitSoon 定义恰 1 处(第二定义 = 钳位节奏分叉)"
    assert state_js.count("this.fxRefitSoon();") == 2, \
        "state.js 缺 fxPreviewing/fxReduce 两翻转沿的 fxRefitSoon 重钳(预览中后缀/reduce 说明行改变面板实高 —— §05.9)"
