"""test_webui_static_dom_panel_traffic_fx_anchor 测试计划: webui 前端静态守阵: 详情面板 / 弹窗 / 浮层

原 test_webui_static_dom_panel_traffic.py 按域拆分(move-only, 2026-11-27); 测试 ID/名称/断言零变化。

## 测试计划(每个测试函数一条)
- test_frontend_qb_fx_anchor_battery: F2 常驻菱形锚 node 电池 + 接缝静态钉(S2b, plan 26-11-14-1313 §03 F2/D2, §04 S2b 行, R3) —— DOM 常驻层真跑(桩 uPlot 域对象 + DOM 桩元素 + 假 rAF 时钟, 同节拍内核范式): ensure 幂等建(恰两枚 .qb-fx-anchor 挂 .u-wrap, 类名 up/dl 可寻址; 颜色 = tk 语义色内联 I10; 初始隐藏; 再调零操作 —— 与 _qbFxBound 同款纪律) + 同步单点位置公式(判定线 x = bbox 右缘 + 末点 y = yOf(shown) 对当前 y 轴档; 门全开复显; 同位置重同步零改写 —— 变值才写) + K RO 面等价(bbox 宽变判定线 x 立即跟随) + 门三态(enabled=false / reduce(on=false) 隐藏、翻回复显; root 拆走隐藏; 死轨该轨隐藏活性轨照显 —— I10 模板 live 门同款) + D calm 档 .qb-fx-anchor-calm 挂/摘随同步对齐(模板 isCalm 同款) + E 四处同步点行为面(判定帧=显示末点 shown/收敛帧=终值 target/zero-change 早退拍同步仍执行按新档重算/锚钩子逐帧跟提交帧且 yMax 读 anim.yMax 与画布钉档同尺 —— I4) + G 门面 _qbFxCfgSync(翻关即时隐藏/翻开复显) + 销毁清面(_qbChartDestroy 清 u._qbFxAnchors, 元件随 u.destroy 拆 root —— 换肤重建零残留); 静态钉: CSS 注入单点逐字(.u-wrap overflow:clip 把逐拍越界动画锚裁在装饰层, 不污染抽屉滚动几何/.qb-fx-anchor 本体/8px+margin 居中+2639ms linear infinite keyframes/calm border-radius:50%/prefers-reduced-motion display:none —— P2 隐藏不是静态方块) + 画布侧菱形本体移除(F2: 锚段零 ctx.fill() 本体 + N 锚辉光新式 6 边/r=(7+4q)*role*gapScale/rot=t/320/alpha=0.5*q*impact/位置 tipX + clip(F5)/lead 加亮保留) + 曲线宽/palette 联动(2.4/calm 2, _qbFxCfgSync 现写 series.width+redraw) + 曲线辉光常驻+视口裁剪(plan 26-11-26-0227 §3.1: 抽独立 _qbDrawFxCurveGlow, 无 t<beat 窗/无 tail 门, 严格绘图区 clip 不采 F5 放宽, blurCap 语义色, 缺口断段, calm 退化) + 四处同步点在位(判定帧在轨道推进后/收敛帧在 setData 后/锚钩子块首行/RO 在 setSize 后同回调) + 门面/建图/销毁接线(cfgSync 块内 sync、build 在 new uPlot 后 ensure、destroy 在 u.destroy 前清记录) + I3 反向钉扩锚 DOM 域(零 destroy/new uPlot/loading)。无 node 静默跳过(同 _NODE_QB_TRAFFIC_PROBE 口径)
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

# ==================== F2 常驻菱形锚 node 电池 + 接缝静态钉(S2b, plan 26-11-14-1313 §03 F2/D2,
# §04 S2b 行, R3) ====================
# DOM 常驻层(.qb-fx-anchor x2 挂 .u-wrap) + CSS keyframes 2639ms(注入单点) + 四处位置同步点 +
# 画布侧菱形本体移除(anchorHalo 改 C7 新式 tipX; 曲线辉光常驻段抽独立 _qbDrawFxCurveGlow)。无 node 静默跳过(同 _NODE_QB_TRAFFIC 口径)。
_NODE_QB_FX_ANCHOR_PROBE = r"""
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
function mkEl() {
  return {
    className: "", style: {}, isConnected: true, parentElement: null, children: [],
    classList: {
      _set: new Set(),
      toggle(cls, force) {
        const want = force === undefined ? !this._set.has(cls) : !!force;
        if (want) this._set.add(cls); else this._set.delete(cls);
        return want;
      },
      contains(cls) { return this._set.has(cls); },
    },
    remove() {
      if (this.parentElement) {
        const i = this.parentElement.children.indexOf(this);
        if (i >= 0) this.parentElement.children.splice(i, 1);
        this.parentElement = null;
      }
      this.isConnected = false;
    },
    appendChild(c) { c.parentElement = this; this.children.push(c); c.isConnected = true; },
  };
}
global.document = { hidden: false, createElement: () => mkEl() };
const TK = { up: "#UP", down: "#DN", grid: "#GRID", axis: "#AXIS" };
const CFG = { enabled: true, on: true, shiftRatio: 0.6, neon: true, particles: 1, tail: false,
  dual: "both", palette: "neon", layers: { band: true, particles: true, scan: true, grade: true } };
global.window.AQB_FX_CFG = CFG;
const XS1 = [1030, 1060, 1090, 1120, 1150];
const YMAX = 63;
function mkWrapRoot() {
  const wrap = mkEl();
  return { wrap, root: { isConnected: true, querySelector: (s) => (s === ".u-wrap" ? wrap : null) } };
}
function mkU(up, dl) {
  const { wrap, root } = mkWrapRoot();
  const u = {
    root, _wrap: wrap,
    data: [XS1, up, dl],
    scales: { x: { min: XS1[0], max: XS1[4] }, y: { min: 0, max: YMAX } },
    bbox: { left: 60, top: 10, width: 800, height: 300 },
    yCap: 0, pending: {}, setScaleLog: [], setDataCount: 0, redrawCount: 0, destroyed: false,
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
      const px2 = this.pending.x;
      const py = this.pending.y;
      this.pending = {};
      if (!px2) {
        if (py) this.scales.y = { min: py.min, max: py.max };
        return;
      }
      const xs = this.data[0];
      let lo = 0;
      let hi = xs.length - 1;
      while (lo < hi && xs[lo] < px2.min) lo++;
      while (hi > lo && xs[hi] > px2.max) hi--;
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
      this.scales.x = { min: px2.min, max: px2.max };
    },
    destroy() { this.destroyed = true; },
  };
  return u;
}
function mkBeat(upShown, dlShown) {
  return {
    raf: 0, anim: null, xs0: 1000, n: 5,
    tracks: {
      up: { prev: upShown, target: upShown, shown: upShown, delta: 0, level: 0, live: true },
      dl: { prev: dlShown, target: dlShown, shown: dlShown, delta: 0, level: 0, live: true },
    },
  };
}
const yOfT = (v, yMax) => 10 + 300 * (1 - Math.min(v, yMax || YMAX) / (yMax || YMAX));
const num = (s) => parseFloat(String(s));
const self = Object.assign({}, methods, { _qbPollMs: () => 3000, _qbCharts: {} });
const pump = () => {
  const fns = [...rafMap.values()];
  rafMap.clear();
  fns.forEach((f) => f());
};
const drain = () => { let g = 0; while (rafMap.size && g++ < 200) { nowMs += 50; pump(); } return g; };
function mkCtx() {
  return {
    globalAlpha: 1, strokeStyle: "", fillStyle: "", lineWidth: 1, canvas: { width: 900 },
    shadowColor: "", shadowBlur: 0,
    save() {}, restore() {}, scale() {}, beginPath() {}, closePath() {}, rect() {}, clip() {},
    moveTo() {}, lineTo() {}, stroke() {}, fill() {},
  };
}
// —— A: ensure 幂等建(挂 .u-wrap / 语义色内联 / 初始隐藏) ——
{
  const u = mkU([0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(10, 55);
  self._qbCharts = { global: u };
  self._qbFxAnchorEnsure(u, TK);
  ok("A ensure: 恰两枚 .qb-fx-anchor 挂 .u-wrap(类名 up/dl 可寻址)", u._wrap.children.length === 2
    && u._wrap.children[0].className === "qb-fx-anchor qb-fx-anchor-up"
    && u._wrap.children[1].className === "qb-fx-anchor qb-fx-anchor-dl");
  ok("A 颜色 = tk 语义色内联(I10) + 初始隐藏(首次同步前不显形)",
    u._wrap.children[0].style.background === TK.up && u._wrap.children[1].style.background === TK.down
    && u._wrap.children[0].style.display === "none" && u._wrap.children[1].style.display === "none");
  const first = [u._wrap.children[0], u._wrap.children[1]];
  self._qbFxAnchorEnsure(u, TK);
  ok("A ensure 幂等(再调零操作 —— 与 _qbFxBound 同款纪律)",
    u._wrap.children.length === 2 && u._wrap.children[0] === first[0]
    && u._qbFxAnchors.up === first[0] && u._qbFxAnchors.dl === first[1]);
}
// —— B: 同步单点位置公式(判定线 x + 末点 y, 静止期读当前 y 轴档) + 变值才写 ——
{
  const u = mkU([0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(10, 55);
  self._qbCharts = { global: u };
  self._qbFxAnchorEnsure(u, TK);
  self._qbFxAnchorSync(u);
  const eu = u._qbFxAnchors.up;
  const ed = u._qbFxAnchors.dl;
  ok("B 位置 = 判定线 x(bbox 右缘 60+800=860) + 末点 y(yOf(shown) 对当前 y 轴档 63)",
    Math.abs(num(eu.style.left) - 860) < 1e-9 && Math.abs(num(eu.style.top) - yOfT(10)) < 1e-9
    && Math.abs(num(ed.style.top) - yOfT(55)) < 1e-9
    && eu.style.left.indexOf("px") > 0 && eu.style.top.indexOf("px") > 0);
  ok("B 门全开: 双轨活性 display 复显(空串 = 类默认)", eu.style.display === "" && ed.style.display === "");
  ok("B calm 类默认不在(palette=neon)", !eu.classList.contains("qb-fx-anchor-calm"));
  eu.style.left = "keep";
  self._qbFxAnchorSync(u);
  ok("B 同位置重同步零改写(变值才写 —— 逐帧同步点不制造无谓布局)", eu.style.left === "keep");
  // —— K(RO 面等价): 宿主尺寸变 -> 判定线 x 跟随新 bbox ——
  u.bbox = { left: 60, top: 10, width: 700, height: 300 };
  self._qbFxAnchorSync(u);
  ok("K bbox 宽变(RO 面): 判定线 x 860 -> 760 立即跟随", Math.abs(num(eu.style.left) - 760) < 1e-9);
}
// —— B2(P5, 26-11-26-0227 §03.3): 动画期锚 x = tipX(末点像素 x, 与画布装饰/N 锚辉光同源),
//          静止期回落判定线 x。复用同步单点 _qbFxAnchorSync(无新 rAF —— 静态钉在测试尾部)。
//          clock=0 时在途锚 = anchorFrom(easeOut(0)=0, 不触吸附), 期望值可从 anim 字段直算。 ——
{
  const u = mkU([0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(10, 55);
  self._qbCharts = { global: u };
  self._qbFxAnchorEnsure(u, TK);
  u._qbBeat.anim = { dx0: 0, needsShift: true, needsTail: false, n: 5, clock: 0, lastT: 0,
    lastDx: null, phase: "impact", anchorFrom: 1000, anchorTo: 1100, span: 120,
    tl: { beat: 1000, impactMs: 120, shiftMs: 600, convergeMs: 480, animEndMs: 600, tailMs: 0 },
    yMax: YMAX, easeF: null, fx: { pxPerT: 0.5 } };
  self._qbFxAnchorSync(u);
  const eu2 = u._qbFxAnchors.up;
  ok("B2 动画期(P5): 锚 x = tipX = L+W+(anchorTo-在途锚)*pxPerT = 860+100*0.5 = 910(与画布装饰同源)",
    Math.abs(num(eu2.style.left) - (60 + 800 + (1100 - 1000) * 0.5)) < 1e-9
    && Math.abs(num(eu2.style.top) - yOfT(10)) < 1e-9);
  u._qbBeat.anim.phase = "tail";
  self._qbFxAnchorSync(u);
  ok("B2 tail 相位(P5): 回落判定线 x = 860(动画期口径只对非 tail 的 anim)",
    Math.abs(num(eu2.style.left) - 860) < 1e-9);
  u._qbBeat.anim = { dx0: 0, needsShift: false, needsTail: true, n: 5, clock: 100, lastT: 0,
    lastDx: null, phase: "impact", anchorFrom: 1000, anchorTo: 1100, span: 120,
    tl: { beat: 1000, impactMs: 120, shiftMs: 600, convergeMs: 480, animEndMs: 600, tailMs: 0 },
    yMax: YMAX, easeF: null, fx: null };
  self._qbFxAnchorSync(u);
  ok("B2 fx-only 拍(needsShift=false): 恒判定线 x = 860(锚不滑动, 零位移面)",
    Math.abs(num(eu2.style.left) - 860) < 1e-9);
  u._qbBeat.anim.clock = 300;   // 拍中帧: needsShift=false 下在途锚不进公式, 仍恒 860
  self._qbFxAnchorSync(u);
  ok("B2 拍中帧(needsShift=false): 仍恒判定线 x(口径不逐帧漂移)",
    Math.abs(num(eu2.style.left) - 860) < 1e-9);
  u._qbBeat.anim.needsShift = true;
  u._qbBeat.anim.clock = 300;   // 拍中帧 needsShift 翻真 + 补回同源 fx(pxPerT): 在途锚 = 1000+100*easeOut(0.5)
  u._qbBeat.anim.fx = { pxPerT: 0.5 };
  self._qbFxAnchorSync(u);
  const at300 = 1000 + 100 * (1 - Math.pow(1 - 300 / 600, 3));   // easeOut 三次多项式(节拍内核 D9)
  ok("B2 拍中帧(needsShift=true): 锚 x = L+W+(anchorTo-在途锚)*pxPerT, 在途锚随时钟推进(与 L0 同源)",
    Math.abs(num(eu2.style.left) - (60 + 800 + (1100 - at300) * 0.5)) < 1e-6);
}
// —— C: 门三态(enabled=false / reduce) + 图不活跃 + 死轨 ——
{
  const u = mkU([0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(10, 55);
  self._qbCharts = { global: u };
  self._qbFxAnchorEnsure(u, TK);
  self._qbFxAnchorSync(u);
  global.window.AQB_FX_CFG = Object.assign({}, CFG, { enabled: false, on: false });
  self._qbFxAnchorSync(u);
  ok("C enabled=false(on=false): 双锚隐藏(有效值单点门)", u._qbFxAnchors.up.style.display === "none"
    && u._qbFxAnchors.dl.style.display === "none");
  global.window.AQB_FX_CFG = Object.assign({}, CFG, { enabled: true, on: false });   // reduce 分量
  self._qbFxAnchorSync(u);
  ok("C reduce(on=false): 双锚隐藏(reduced-motion 隐藏 —— P2; CSS 媒体查询为第二道)",
    u._qbFxAnchors.up.style.display === "none");
  global.window.AQB_FX_CFG = CFG;
  self._qbFxAnchorSync(u);
  ok("C 翻回 on=true: 复显(门面即时生效, 不等下一拍)", u._qbFxAnchors.up.style.display === "");
  u.root.isConnected = false;
  self._qbFxAnchorSync(u);
  ok("C 图不活跃(root 拆走): 隐藏", u._qbFxAnchors.up.style.display === "none");
  u.root.isConnected = true;
  u._qbBeat.tracks.dl = { prev: null, target: null, shown: null, delta: 0, level: 0, live: false };
  self._qbFxAnchorSync(u);
  ok("C 死轨(缺口 shown=null): 该轨锚隐藏, 活性轨照显(I10 模板 live 门同款)",
    u._qbFxAnchors.dl.style.display === "none" && u._qbFxAnchors.up.style.display === "");
  // B4 评审 minor 补例: 真 0 与缺口分义 —— live=true 且 shown=0(零流量活性轨)必须显形,
  // top = yOf(0) = T+H(门判据是 shown != null 而非 shown 真值 —— A3「0 流量: 菱形旋转仍在」
  // 的门面 closure; 门真值化变异为 tr.shown 即红)
  u._qbBeat.tracks.dl = { prev: 0, target: 0, shown: 0, delta: 0, level: 0, live: true };
  self._qbFxAnchorSync(u);
  ok("C 真 0(live=true, shown=0): 该轨锚显形且 top = yOf(0) = T+H(A3 门面 closure)",
    u._qbFxAnchors.dl.style.display === ""
    && Math.abs(num(u._qbFxAnchors.dl.style.top) - yOfT(0)) < 1e-9);
}
// —— D: calm 档 border-radius 退化圆点(类切换随同步对齐) ——
{
  const u = mkU([0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(10, 55);
  self._qbCharts = { global: u };
  self._qbFxAnchorEnsure(u, TK);
  global.window.AQB_FX_CFG = Object.assign({}, CFG, { palette: "calm" });
  self._qbFxAnchorSync(u);
  ok("D palette=calm: 双锚挂 .qb-fx-anchor-calm(CSS border-radius:50% 退化圆点)",
    u._qbFxAnchors.up.classList.contains("qb-fx-anchor-calm")
    && u._qbFxAnchors.dl.classList.contains("qb-fx-anchor-calm"));
  global.window.AQB_FX_CFG = Object.assign({}, CFG, { palette: "glitch" });
  self._qbFxAnchorSync(u);
  ok("D palette=glitch: calm 类即时摘除(类随同步逐次对齐)",
    !u._qbFxAnchors.up.classList.contains("qb-fx-anchor-calm"));
  global.window.AQB_FX_CFG = CFG;
}
// —— E: 判定帧同步点(轨道推进后同帧写; 早退拍也跟新值) ——
{
  const u = mkU([0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(10, 55);
  self._qbCharts = { global: u };
  self._qbFxAnchorEnsure(u, TK);
  self._qbBeatStart("global", u);   // 滚窗拍: target 30/60, shown 仍 prev 10/55
  ok("E 判定帧: 锚位 = 显示末点(shown=prev 10/55) x=判定线 860",
    Math.abs(num(u._qbFxAnchors.up.style.left) - 860) < 1e-9
    && Math.abs(num(u._qbFxAnchors.up.style.top) - yOfT(10)) < 1e-9
    && Math.abs(num(u._qbFxAnchors.dl.style.top) - yOfT(55)) < 1e-9);
  drain();
  ok("E 收敛帧: 锚位跟终值(target 30/60 —— 同步点 2/4)", u._qbBeat.anim === null
    && Math.abs(num(u._qbFxAnchors.up.style.top) - yOfT(30)) < 1e-9
    && Math.abs(num(u._qbFxAnchors.dl.style.top) - yOfT(60)) < 1e-9);
  global.window.AQB_FX_CFG = Object.assign({}, CFG, { enabled: false, on: false });
  u.data = [[1060, 1090, 1120, 1150, 1180], [0, 0, 0, 0, 35], [0, 0, 0, 0, 60]];
  self._qbBeatStart("global", u);
  ok("E 早退拍(enabled=false): 门关锚隐藏(位置不猜 —— 显示面让位给门; L0/L1 照滚不影响门)",
    u._qbFxAnchors.up.style.display === "none" && u._qbFxAnchors.dl.style.display === "none");
  global.window.AQB_FX_CFG = CFG;
  // 零变化早退拍(on=true, dx0=0 + 双轨无真变化 -> 数据面零动画): 判定帧同步仍执行 ——
  // y 轴档位变(窗内出现新高 120 -> 档 126)后锚位按新档重算, 不落旧档值。F6/D3(26-11-15-1104)
  // 后该拍带 fx-only anim(needsShift/needsTail 双 false —— 只跑 fx impact 窗), 不再整拍静默。
  u.data = [[1030, 1060, 1090, 1120, 1150], [0, 0, 0, 0, 30], [0, 120, 0, 0, 60]];
  u.scales.y = { min: 0, max: 126 };   // 快路 setData 已重推的 y 轴档(模拟真序: setData 先行)
  self._qbBeatStart("global", u);
  ok("E 零变化早退拍(on=true): 判定帧同步仍执行, 锚位按新 y 轴档 126 重算(不落旧档值);"
    + " F6 后该拍带 fx-only anim(双 false)", u._qbBeat.anim !== null
    && u._qbBeat.anim.fx !== null && u._qbBeat.anim.needsShift === false
    && u._qbBeat.anim.needsTail === false
    && Math.abs(num(u._qbFxAnchors.up.style.top) - yOfT(30, 126)) < 1e-9);
  drain();
}
// —— F: 锚钩子同步点(每次画布提交顺路重写; 动画期 yMax 读 anim.yMax 与画布钉档同尺) ——
{
  const u = mkU([0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(10, 55);
  self._qbCharts = { global: u };
  self._qbFxAnchorEnsure(u, TK);
  u._qbBeat.anim = { dx0: 0, needsShift: false, needsTail: true, n: 5, clock: 100, lastT: 0,
    lastDx: null, phase: "impact",
    tl: { beat: 1000, impactMs: 120, shiftMs: 600, convergeMs: 480, animEndMs: 600, tailMs: 0 },
    yMax: YMAX, easeF: null, fx: null };
  u._qbBeat.tracks.up.shown = 20;   // L1 收敛中的显示面
  u.ctx = mkCtx();
  methods._qbDrawFxAnchor.call(self, u, TK);
  ok("F 锚钩子: 提交帧顺路重写, y = yOf(shown=20) 对 anim.yMax=63(与画布钉档同尺 —— I4)",
    Math.abs(num(u._qbFxAnchors.up.style.top) - yOfT(20, YMAX)) < 1e-9);
  u._qbBeat.tracks.up.shown = 25;
  methods._qbDrawFxAnchor.call(self, u, TK);
  ok("F 锚钩子逐帧: shown 20 -> 25 位置跟帧",
    Math.abs(num(u._qbFxAnchors.up.style.top) - yOfT(25, YMAX)) < 1e-9);
}
// —— G: 门面 _qbFxCfgSync(cfg 翻变即时生效) + 销毁清面(换肤重建零残留) ——
{
  const u = mkU([0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(10, 55);
  const s2 = Object.assign({}, methods, { _qbPollMs: () => 3000, _qbCharts: { global: u },
    fxReduce: false, fx: JSON.parse(JSON.stringify(CFG)) });
  Object.defineProperty(s2, "fxOn", { get() { return this.fx.enabled === true && !this.fxReduce; } });
  self._qbCharts = { global: u };
  self._qbFxAnchorEnsure(u, TK);
  s2.fx.enabled = false;
  s2._qbFxCfgSync();
  ok("G _qbFxCfgSync 门面: enabled=false -> CFG.on=false -> 锚隐藏(即时, 不等下一拍)",
    global.window.AQB_FX_CFG.on === false && u._qbFxAnchors.up.style.display === "none"
    && u._qbFxAnchors.dl.style.display === "none");
  s2.fx.enabled = true;
  s2._qbFxCfgSync();
  ok("G 门面翻回: 复显", global.window.AQB_FX_CFG.on === true && u._qbFxAnchors.up.style.display === "");
  self._qbChartRos = { global: { disconnect() {} } };
  self._qbChartDestroy("global");
  ok("G 销毁清面: 图记录 _qbFxAnchors 清(元件本体在 u.root 内随 u.destroy 拆 —— 换肤重建零残留)",
    self._qbCharts.global === null && u._qbFxAnchors === null && u.destroyed === true);
}
// —— H: 曲线宽 palette 联动(D4): cfgSync 现写 series.width + redraw(不重建/destroy/loading) ——
{
  const u = mkU([0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(10, 55);
  u.series = [{}, { width: 2 }, { width: 2 }];
  const s3 = Object.assign({}, methods, { _qbPollMs: () => 3000, _qbCharts: { global: u },
    fxReduce: false, fx: JSON.parse(JSON.stringify(CFG)) });
  Object.defineProperty(s3, "fxOn", { get() { return this.fx.enabled === true && !this.fxReduce; } });
  self._qbCharts = { global: u };
  self._qbFxAnchorEnsure(u, TK);
  const beforeRedraw = u.redrawCount;
  s3._qbFxCfgSync();
  ok("H 曲线宽默认档: neon -> 2.4 两轨 + 恰一次 redraw(不重建/destroy)",
    u.series[1].width === 2.4 && u.series[2].width === 2.4
    && u.redrawCount === beforeRedraw + 1 && !u.destroyed);
  s3.fx.palette = "calm";
  s3._qbFxCfgSync();
  ok("H palette=calm: series.width 即时 2(不等下一拍) + 变化才 redraw",
    u.series[1].width === 2 && u.series[2].width === 2 && u.redrawCount === beforeRedraw + 2);
  global.window.AQB_FX_CFG = CFG;
}
const okCount = checks.filter((c) => c[1]).length;
console.log(JSON.stringify({
  total: checks.length, ok: okCount,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]),
}));
"""


def test_frontend_qb_fx_anchor_battery():
    """F2 常驻菱形锚 node 电池 + 接缝静态钉(S2b, plan 26-11-14-1313 §03 F2/D2, §04 S2b 行, R3)

    行为面(node 电池, 无 node 静默跳过, 同 _NODE_QB_TRAFFIC_PROBE 口径; DOM 桩 + 真 mixin 方法):
    A ensure 幂等建(恰两枚 .qb-fx-anchor 挂 .u-wrap, 类名 up/dl 可寻址; 颜色 = tk 语义色内联
    I10; 初始隐藏; 再调零操作 —— 与 _qbFxBound 同款纪律)
    + 同步单点位置公式(P5: 动画期 x = tipX = L+W+剩余锚位移x pxPerT 与画布装饰同源, 静止期回落
    判定线 x = bbox 右缘 860 + 末点 y = yOf(shown) 对当前 y 轴档; px 后缀;
    门全开复显; calm 类默认不在; 同位置重同步零改写 —— 变值才写)
    + K RO 面等价(bbox 宽 800->700 判定线 x 860->760 立即跟随)
    + B2 P5 动画期面(clock=0 tipX=910 / tail 相位回落 860 / fx-only 拍恒 860 / 拍中在途锚随时钟
    推进 —— 与 L0 同源) + 四处同步点全覆盖且无新 rAF(c2 静态钉)
    + C 门三态(enabled=false / reduce(on=false) 隐藏, 翻回复显; root 拆走隐藏; 死轨该轨隐藏
    活性轨照显 —— I10 模板 live 门同款; 真 0(live=true, shown=0)显形且 top=yOf(0)=T+H
    —— A3 零流量菱形旋转仍在的门面 closure, 门真值化变异即红)
    + D calm 档 .qb-fx-anchor-calm 挂/摘随同步对齐(模板 isCalm 同款)
    + E 判定帧同步点(滚窗拍锚位 = 显示末点 shown=prev; 收敛帧跟终值 target; enabled=false
    早退拍门关锚隐藏; 零变化早退拍(on=true, F6 后带 fx-only anim)判定帧同步仍执行 —— y 轴
    档位变后锚位按新档重算不落旧档值)
    + F 锚钩子同步点(每次画布提交顺路重写; 动画期 yMax 读 anim.yMax 与画布钉档同尺 —— I4;
    shown 变位置跟帧)
    + G 门面 _qbFxCfgSync(enabled 翻关锚即时隐藏/翻回复显, 不等下一拍) + 销毁清面
    (_qbChartDestroy 清 u._qbFxAnchors, 元件随 u.destroy 拆 root —— 换肤重建零残留)。

    接缝面(静态钉):
    a. CSS 注入单点(_qbChartInjectCss 逐字): .u-wrap overflow:clip(动画锚越出图根时裁在装饰层,
    不把 scrollable overflow 传给抽屉)/.qb-fx-anchor 本体(8px 方块 + margin 居中 +
    pointer-events:none + will-change:transform + animation ${_QB_FX_ANCHOR_SPIN_MS}ms linear infinite)/
    .qb-fx-anchor-calm(border-radius:50% —— 模板 isCalm 同款)/@keyframes aqb-fx-anchor-spin
    (rotate 0->360deg —— 模板 rot=t/420 是弧度/ms, 一圈 2*pi*420=2639ms; 旧 420ms 系单位误读)/@media(prefers-reduced-motion: reduce) display:none
    (P2: 隐藏不是静态方块; 与 cfg.on 的 !reduce 分量双保险);
    b. 画布侧菱形本体移除(F2 避免双画): 锚段零 ctx.fill() 本体填充面, 旧 "_qbFxPolyPath(ctx, L + W, y, r * 1.8, 4, rot)" 回潮即红;
    N 锚辉光新式(C7): "_qbFxPolyPath(ctx, tipX, y, r, 6, haloRot)" 6 边 + "r = (7 + 4 * q) * role * fx.gapScale"
    + "haloRot = t / 320" + "ctx.globalAlpha = 0.5 * q * imp" + tipX = L + valToPos(xs[a.n - 1], "x")(末点滑动 x, 同 lead 加亮段 x 轴换算);
    锚段 clip 放宽(F5)与 lead 从属轨加亮保留(ctx.clip() 在位);
    b2. 曲线宽/palette 联动(D4): 建图两轨 width 走 _qbFxCurveWidth()(常规 2.4 / calm 2),
    _qbFxCfgSync 现写 u.series[1/2].width + redraw(不重建/destroy/碰 loading —— 下一拍才生效会与面板即时契约错拍);
    曲线辉光(plan 26-11-26-0227 §3.1 缺陷一+二重构): 独立函数 _qbDrawFxCurveGlow(锚段内零辉光残留),
    判据 cfg.on===true 且 tracks[k].level>0(无 t<beat 拍内窗 / 无 phase==="tail" 门), "ctx.shadowColor = trackCol"
    + shadowBlur=blurCap*(lead/both?1:0.45)(calm 0 自然退化) + 缺口 "gStarted = false; continue;" 断段不桥接 + 帧末 shadowBlur=0;
    c. 四处同步点在位: 判定帧(_qbBeatStart 块内 sync 在轨道推进之后)/收敛帧(_qbBeatConverge
    setData 之后)/锚钩子(_qbDrawFxAnchor 块首行)/ResizeObserver(u.setSize 之后同回调内);
    d. 门面接线: _qbFxCfgSync 块内 _qbFxAnchorSync(on/palette 变化即时生效) + _qbChartBuild
    建 ensure+首同步(new uPlot 之后) + _qbChartDestroy 清 u._qbFxAnchors;
    e. I3 反向钉扩锚 DOM 域: ensure/sync 两方法域零 destroy(/new uPlot/loading。
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    js = open(os.path.join(shared, "qb_traffic_chart.js"), encoding="utf-8").read()
    # —— a. CSS 注入单点(四皮肤零侵入 —— 经既有 _qbChartInjectCss) ——
    for line in (
        ".u-wrap { position: relative; user-select: none; overflow: clip; }",
        '.qb-fx-anchor { position: absolute; width: 8px; height: 8px; margin: -4px 0 0 -4px;'
        ' pointer-events: none; will-change: transform; animation: aqb-fx-anchor-spin ${_QB_FX_ANCHOR_SPIN_MS}ms linear infinite; }',
        ".qb-fx-anchor.qb-fx-anchor-calm { border-radius: 50%; }",
        "@keyframes aqb-fx-anchor-spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }",
        "@media (prefers-reduced-motion: reduce) { .qb-fx-anchor { display: none; } }",
    ):
        assert line in js, f"缺/漂移常驻菱形锚注入 CSS: {line}"
    assert "animation: aqb-fx-anchor-spin ${_QB_FX_ANCHOR_SPIN_MS}ms linear infinite;" in js, \
        "CSS 周期必须走 _QB_FX_ANCHOR_SPIN_MS 现算单点(2639ms; 旧 420ms 单位误读不得回潮)"
    assert "animation: aqb-fx-anchor-spin 420ms" not in js, "旧 420ms 字面周期残留(单位误读回潮即红)"
    inject_blk = re.search(r"_qbChartInjectCss\(\) \{\n(.*?)\n    \},", js, re.S)
    assert inject_blk and "aqb-fx-anchor-spin" in inject_blk.group(1), \
        "锚 CSS 必须经 _qbChartInjectCss 单点注入(四皮肤零侵入)"
    # —— b. 画布侧菱形本体移除 + 辉光同源保留 ——
    anb = re.search(r"_qbDrawFxAnchor\(u, tk\) \{\n(.*?)\n    \},", js, re.S)
    assert anb, "缺 _qbDrawFxAnchor(draw 锚段)"
    anb_code = re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", anb.group(1), flags=re.S))
    assert "ctx.fill()" not in anb_code, \
        "画布侧菱形本体必须移除(F2 避免双画 —— 常驻层交 DOM .qb-fx-anchor; 辉光只用 stroke)"
    assert "_qbFxPolyPath(ctx, L + W, y, r * 1.8, 4, rot);" not in anb_code, \
        "N 锚辉光旧式(4 边/r*1.8/L+W)必须退场(C7 新式回潮即红)"
    for frag in (
        "_qbFxPolyPath(ctx, tipX, y, r, 6, haloRot);",
        "const r = (7 + 4 * q) * role * fx.gapScale;",
        "const haloRot = t / 320;",
        "ctx.globalAlpha = 0.5 * q * imp;",
        'const tipX = L + u.valToPos(xs[a.n - 1], "x");',
    ):
        assert frag in anb_code, f"N 锚辉光新式(C7)缺/漂移: {frag}"
    assert "ctx.clip();" in anb_code, "锚段 clip 放宽(F5)必须保留(lead 加亮/N 锚辉光仍画在画布)"
    assert 'cfg.dual === "lead"' in anb_code, "lead 策略从属轨描边加亮(D3-a)必须保留"
    # —— b2. 曲线宽/palette 联动(D4) + 曲线辉光常驻+视口裁剪(plan 26-11-26-0227 §3.1) ——
    assert 'return p === "calm" ? 2 : 2.4;' in js, \
        "曲线宽单点 _qbFxCurveWidth 必须常规 2.4 / calm 2(D4)"
    assert js.count("width: curveW,") == 2, \
        "建图两轨 width 必须走当前 palette 的 curveW(建图初值即对齐 —— D4)"
    cfg_blk = re.search(r"_qbFxCfgSync\(\) \{\n(.*?)\n    \},", js, re.S)
    assert cfg_blk and "uc.series[1].width = w;" in cfg_blk.group(1) \
        and "uc.series[2].width = w;" in cfg_blk.group(1) \
        and "uc.redraw(false, true);" in cfg_blk.group(1), \
        "palette 切换必须经 _qbFxCfgSync 现写 series.width + redraw(不重建/destroy/碰 loading —— D4)"
    # 曲线辉光已抽独立常驻函数: 锚段内不得残留旧拍内窗/辉光段(缺陷一+二重构回潮即红) ——
    assert "if (t < fx.beatMs)" not in anb_code, \
        "锚段不得残留拍内辉光独立窗(顶门 0.7 粗滤保留 —— 曲线辉光已抽独立常驻函数, 旧窗式回潮即红)"
    assert "shadowBlur" not in anb_code and "gStarted" not in anb_code, \
        "锚段不得残留曲线辉光重描段(blur/gStarted 面已全部迁出)"
    glow_blk = re.search(r"_qbDrawFxCurveGlow\(u, tk\) \{\n(.*?)\n    \},", js, re.S)
    assert glow_blk, "缺 _qbDrawFxCurveGlow(曲线辉光常驻独立函数)"
    glow_code = re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", glow_blk.group(1), flags=re.S))
    assert "t < fx.beatMs" not in glow_code and 'phase === "tail"' not in glow_code, \
        "曲线辉光必须全程常驻: 无拍内时间窗、无 tail 门(缺陷一: level 判据不依赖 anim/窗)"
    assert "if (!(tracks[k].level > 0)) continue;" in glow_code, \
        "曲线辉光判据必须逐轨 level>0(拍间仍在, 不依赖 a.fx)"
    assert "ctx.save();" in glow_code and "ctx.restore();" in glow_code \
        and "ctx.rect(L, T, W, H);" in glow_code \
        and "Math.max(W, canvasW" not in glow_code, \
        "曲线辉光必须自身 save + 严格绘图区 rect(L,T,W,H) clip(缺陷二: 不采 F5 右缘放宽 —— R2)"
    assert "const glowBlur = Math.round(blurCap * (" in glow_code, \
        "曲线辉光 blur 上限必须走 blurCap 派生(语义色同源, calm 0 自然退化)"
    for frag in (
        "ctx.shadowColor = trackCol;",
        "ctx.shadowBlur = glowBlur;",
        "gStarted = false; continue;",
        "if (gStarted) ctx.stroke();",
        "ctx.shadowBlur = 0;",
    ):
        assert frag in glow_code, f"曲线辉光(常驻)缺/漂移: {frag}"
    # —— c. 四处同步点 ——
    bsb = re.search(r"_qbBeatStart\(scope, u\) \{\n(.*?)\n    \},", js, re.S)
    assert bsb and "this._qbFxAnchorSync(u);" in bsb.group(1), \
        "缺判定帧同步点(_qbBeatStart: 轨道推进后同帧写 —— 覆盖零变化/早退拍)"
    assert bsb.group(1).index("_qbFxTrackNext(tr.dl") < bsb.group(1).index("this._qbFxAnchorSync(u);"), \
        "判定帧同步必须在双轨推进之后(锚位读推进后的显示面)"
    conv_blk = re.search(r"_qbBeatConverge\(scope, u\) \{\n(.*?)\n    \},", js, re.S)
    assert conv_blk and conv_blk.group(1).index("u.setData([u.data[0], u.data[1], u.data[2]]);") \
        < conv_blk.group(1).index("this._qbFxAnchorSync(u);"), \
        "缺收敛帧同步点(_qbBeatConverge: setData 真值写回之后写终值)"
    assert anb.group(1).lstrip().startswith("this._qbFxAnchorSync(u);"), \
        "缺锚钩子同步点(_qbDrawFxAnchor 块首行: 每次画布提交顺路重写)"
    ro_m = re.search(r"u\.setSize\(\{ width: w, height: h \}\);.*?this\._qbFxAnchorSync\(u\);", js, re.S)
    assert ro_m and len(ro_m.group(0)) < 600, \
        "缺 ResizeObserver 同步点(u.setSize 之后同回调内重写锚位 —— R3 resize 遗漏即像素漂移)"
    # —— c2. P5 锚 x 新口径 + 无新 rAF(R5): 动画期 tipX 在同步单点内实现, 四处同步点原位搭车 ——
    sync_m = re.search(r"_qbFxAnchorSync\(u\) \{\n(.*?)\n    \},", js, re.S)
    assert sync_m, "缺 _qbFxAnchorSync(位置/门同步单点)"
    sync_code = re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", sync_m.group(1), flags=re.S))
    for frag in (
        "a.needsShift === true ? a.anchorTo - _qbAnimAnchorAt(a) : 0",
        "a.fx && a.fx.pxPerT != null ? a.fx.pxPerT",
    ):
        assert frag in sync_code, f"P5 动画期 tipX 口径缺/漂移: {frag}(静止期 L+W 回落 + 与画布装饰同源)"
    assert "requestAnimationFrame" not in sync_code, \
        "P5/R5: 锚同步不得新增独立 rAF(动画期 tipX 只在四处既有同步点内顺路重写)"
    # —— d. 门面/建图/销毁接线 ——
    cfg_blk = re.search(r"_qbFxCfgSync\(\) \{\n(.*?)\n    \},", js, re.S)
    assert cfg_blk and "_qbFxAnchorSync" in cfg_blk.group(1), \
        "缺门面接线(_qbFxCfgSync: on/palette 变化即时生效, 不等下一拍)"
    assert "this._qbFxAnchorEnsure(u, tk);" in js and "this._qbFxAnchorSync(u);" in js, \
        "缺建图接线(_qbChartBuild: ensure 幂等建 + 首次同步)"
    assert js.index("new uPlot(opts") < js.index("this._qbFxAnchorEnsure(u, tk);"), \
        "锚元件必须建在 uPlot 之后(挂 .u-wrap 需 root 在场)"
    dest_blk = re.search(r"_qbChartDestroy\(scope\) \{\n(.*?)\n    \},", js, re.S)
    assert dest_blk and "u._qbFxAnchors = null;" in dest_blk.group(1), \
        "缺销毁清面(_qbChartDestroy 清锚记录 —— 换肤/重建零残留, 与 _qbFxBound 幂等纪律对偶)"
    assert dest_blk.group(1).index("u._qbFxAnchors = null;") < dest_blk.group(1).index("u.destroy()"), \
        "销毁清面必须在 u.destroy 之前落笔(清记录 -> 拆 root)"
    # —— e. I3 反向钉扩锚 DOM 域 ——
    ens_blk = re.search(r"_qbFxAnchorEnsure\(u, tk\) \{\n(.*?)\n    \},", js, re.S)
    sync_blk = re.search(r"_qbFxAnchorSync\(u\) \{\n(.*?)\n    \},", js, re.S)
    assert ens_blk and sync_blk, "缺 _qbFxAnchorEnsure/_qbFxAnchorSync(锚 DOM 层方法域)"
    for blk in (ens_blk.group(1), sync_blk.group(1)):
        assert "new uPlot" not in blk and "destroy(" not in blk and "loading" not in blk, \
            "锚 DOM 域不得 destroy/new uPlot/触碰 loading(I3 反向钉)"
    assert 'el.style.background = k === "up" ? tk.up : tk.down;' in ens_blk.group(1), \
        "锚颜色必须 = tk 语义色内联(建图时捕获, 换肤重建即新令牌 —— I10)"
    # —— 行为面 node 电池 ——
    node = shutil.which("node")
    if not node:
        return
    proc = subprocess.run(
        [node, "-e", _NODE_STDIN_WRAPPER, os.path.join(shared, "qb_traffic_chart.js")],
        input=_NODE_QB_FX_ANCHOR_PROBE,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    assert proc.returncode == 0, f"F2 常驻菱形锚 node 电池跑挂: {proc.stderr.strip()}"
    report = json.loads(proc.stdout.strip().splitlines()[-1])
    assert report["failed"] == [], \
        f"F2 菱形锚电池 {report['ok']}/{report['total']} 过, 失败: {report['failed']}"
