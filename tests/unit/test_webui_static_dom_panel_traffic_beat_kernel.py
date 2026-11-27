"""test_webui_static_dom_panel_traffic_beat_kernel 测试计划: webui 前端静态守阵: 详情面板 / 弹窗 / 浮层

原 test_webui_static_dom_panel_traffic.py 按域拆分(move-only, 2026-11-27); 测试 ID/名称/断言零变化。

## 测试计划(每个测试函数一条)
- test_frontend_qb_beat_kernel_battery: 节拍内核 S1 电池 + 接缝静态钉(plan 26-11-12-1139 §03 节奏模型/L0/L1, §06 S1 行; 尾锚显式视口换代 26-11-22-0858) —— node 电池双发(new Function 取出口径): 节奏公式四组(multiplier 1/2/8 与 600s 长窗 -> beat 600/夹顶 1000, 下限 320 与非法 period 防御) + 每拍时间线(impact 0.12/shift=shiftRatio×beat 防御夹取/converge [0,0.6](t=0 起步; impact 窗 shown 已移动 + ease 越界夹取 + I4 单调无 overshoot 全域扫 + 装饰帧保障零 Δ 兜底)/tail=min(period-beat,2000) 封顶非常驻, animEnd<=beat<=1000 全域扫 = I1) + easeOut 三次多项式单调无 overshoot(D9) + 0.75px 最小可见位移规则(短窗播平移/长窗瞬时/0.75 边界/量不到宽瞬时) + L1 双轨独立(上传 Δ=0 恒 Lv.1 下限(F1) + 下载 Lv.3/Δ 分档端点归属 0.005/0.05/0.30/真 0 与缺口轨恒静默/缺参向后兼容/复活轨直落真值/分母可视下限防爆炸/0->0 守卫) + 以显示值接续不回跳(I3) + 锚视口纯函数面 _qbAnchorJudge(J1-J10: 单调锚 anchor=max(st.anchor,tail) 旧窗响应晚到不回拖/组距标称与名义窗长变化 rewin/±2 组距滚动域恰边界 slide 保持/位移上界不含/J8 首拍锚起步/J9-J10 meta 缺席防御)+ _qbAnimAnchorAt(L1-L4: 在途锚现值单点 帧循环与打断续滑共用/clock=0=anchorFrom/clock>=shiftMs 钳 anchorTo/末帧 ulp 吸附/easeOut 特征值 0.875/零 mutate)+ _qbRetainHistory(L5-L7: t<新列头恰等不并入 与 keepLine 含界对称/keepLine 外弃/引用共享/防御空列与新头无 t)+ _qbTrimStaleHead 余量线(L8-L9c: 保留窗 span+margin=2 组距/尾点无 t 不剪/keepS 非法不剪/锚=视口锚优先 领先尾按锚修剪列仍覆盖视口左缘 无锚回落尾/摘要窗内桶数 余量列不计 缺 span_s/旧契约回落全列长) + 调度器面 S0-S20b(S0/S0b 桩忠实性含 redraw(false,true) 不重写 x pending —— 尾锚显式视口依赖此语义/S1-S2 平移全生命周期: 视口落滑动起点=上一收敛视口 左右缘双连续 + 逐帧锚单调不减两缘同步跨度恒名义窗 + 收敛帧 setData 后显式重申覆盖列全宽 auto + 锚记账落位/S3 打断接续 L1 值面与锚续滑面/S4 隐藏暂停恢复/S5 reduce 显式视口一次落笔(旧零 setScale 交 auto 随换代退役)/S6 enabled=false 不短路/S7 零变化拍 fx 在场 + 显式视口照常落笔/S7a 真 0 静默 + 显式视口照常/S7b 尾值不变滚窗平移照播尾点零改写/S8 长窗 gate 拒绝瞬时落地目标锚视口 恰一次 x+y —— 旧 auto 落地面退役 instant/长窗恒定压缩变体随补点退役消失/S9-S9c 换档瞬时(组距标称+名义窗长变化)/滚动域外(delta>2x step)/恰 2 组距边界仍平移/S10 销毁终止/S11 rescale 显式视口重申锚不动/S12-S12b 零变化连拍显式视口每拍同值落笔/S13-S13b 悬停读数面/S14 零位移打断续滑全链(在途锚直读 零回跳 —— 旧 _qbInheritedViewport 公式重建退役)/S15 真滚动打断单调锚到新尾/S16 rewin 打断瞬时落地新窗长锚视口/S17 单调锚尾回退不回拖/S18 instant 档瞬时落地目标锚视口 恒定压缩变体随补点退役消失/S19 建图拍底座 anchor=列尾真值 step=meta 组距标称 span=meta 名义窗长 + 建图初始视口播种 [锚-span,锚] 免首绘 auto 全列宽闪帧/S20b 余量列变异盲区封堵: 列含余量点 setData 的列全宽 auto 必须被收敛帧显式重申覆盖 重申行删除即红 —— 其余场景列恒真值无余量 auto 与锚视口同形拦不住/S20c 余量持峰: 余量列含真实峰值点 收敛帧 y 成对钉 终态 y == 全列钉值且动画期零泵动(y 钉行删除即红)) + 接缝静态钉 a-k(a 快路纯 setData 三列原样落袋->同帧 _qbBeatStart 补点构造/继承捕获退役/b 判定帧显式视口无条件落笔 vAnchor-j.span + y 成对钉 + 帧循环 anchor=a-_qbAnimAnchorAt(a) 单锚位守卫 + min=anchor-a.span max=anchor + y 成对 + 纯数值收敛帧先钉 y 再 redraw + yMax 全列扫描 + 收敛帧 setData+显式重申+y 成对钉+redraw(false,true)/c 右缘刻位过滤+标签逐帧现算+tick freeze 退役/d reduce 读有效值单点/e destroy 先 cancel/f beat 展示值复用单点/g BOM 纪律/h I3 反向钉/i tooltip 读数面接缝/j rescale 收口 setData 后 x 重申 + y 成对钉(y 紧跟 x, 按新 cap 全列重算 yMax, 钉 b 同款成对形态)/k 尾锚反向钉: 退役件 _qbRollJudge/_qbPadTailColumns/_qbInheritedViewport/_qbBeatVpRem/_qbPad 剥注释全文件零残留 + _qbAnchorJudge 单点消费 + st.anchor/step/span 记账 + 悬停索引直通 + yMax 全列 + anchorPrev/disp 单点 + 历史保留合并单点; 取数窗口分量钉在 wiring 电池)。无 node 静默跳过(同 _NODE_QB_TRAFFIC_PROBE 口径)
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

# 节拍内核 node 电池(S1, plan 26-11-12-1139 §03 节奏模型/L0/L1): 公式/时间线/easeOut/状态机/
# 0.75px 规则真跑。new Function 取出口径(模块级 const 不随 sloppy eval 外泄, 同 _NODE_QB_FX_PROBE);
# 无 node 静默跳过(同 _NODE_QB_TRAFFIC_PROBE 口径)。
_NODE_QB_BEAT_PROBE = r"""
const fs = require("fs");
global.window = {};
const src = fs.readFileSync(process.argv[1], "utf8");
const {
  _qbBeatMs, _qbBeatTimeline, _qbFxEaseOut, _qbFxCellPx, _qbFxShouldShift,
  _qbFxLevel, _qbFxTrackNext, _qbFxShown, _qbAnchorJudge, _qbAnimAnchorAt, _qbFxShiftGate,
  _qbRetainHistory, _qbTrimStaleHead, _qbDropRightEdgeSplits, _QB_X_SPLIT_EPS,
} = new Function(src + "\nreturn { _qbBeatMs, _qbBeatTimeline, _qbFxEaseOut, _qbFxCellPx,"
  + " _qbFxShouldShift, _qbFxLevel, _qbFxTrackNext, _qbFxShown, _qbAnchorJudge, _qbAnimAnchorAt,"
  + " _qbFxShiftGate, _qbRetainHistory, _qbTrimStaleHead, _qbDropRightEdgeSplits, _QB_X_SPLIT_EPS };")();
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
// —— B. 每拍时间线(§03 公式代码块: impact 0.12 / shift=shiftRatio×beat / converge [0,0.6]
//       (t=0 起步 —— B5/D1, 旧 [0.12,0.6] 退役) / tail = min(period-beat, 2000) 封顶非常驻) ——
let tl = _qbBeatTimeline(1500, 0.6);
ok("1.5s 拍: beat 600 / impact 72 / shift 360", tl.beat === 600 && close(tl.impactMs, 72) && close(tl.shiftMs, 360));
ok("1.5s 拍: 收敛窗 360ms(0-0.6 beat, t=0 起步), animEnd=360(I1 不变)",
  close(tl.convergeMs, 360) && close(tl.animEndMs, 360));
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
ok("长序列 2880 点/800px ~ 0.28px/格(旧 24h 形, F1 后生产不可达, 保留为内核行为钉) -> 瞬时落地", _qbFxCellPx(800, 2880) < 0.75
  && !_qbFxShouldShift(_qbFxCellPx(800, 2880)));
ok("边界 0.75px 恰好可播(>= 判据)", _qbFxShouldShift(0.75) && !_qbFxShouldShift(0.749));
ok("量不到宽/零点数 -> 瞬时(宁可不动画不可错动画)", !_qbFxShouldShift(_qbFxCellPx(0, 40))
  && !_qbFxShouldShift(_qbFxCellPx(800, 0)));
// —— E. L1 双轨独立(上传 Δ=0 恒 Lv.1 下限(F1: 值>0) + 下载 Lv.3 各自正确, 互不串味 —— I10/D2) ——
let up = _qbFxTrackNext({ prev: 100, target: 100, shown: 100, delta: 0, level: 0, live: true }, 100, 2);
let dl = _qbFxTrackNext({ prev: 50, target: 50, shown: 50, delta: 0, level: 0, live: true }, 100, 2);
ok("上传 Δ=0(值>0) -> Lv.1(F1 活跃轨恒 >=1 下限, 不再整段静默)", up.live && up.delta === 0 && up.level === 1);
ok("下载 50->100(delta=1.0) -> Lv.3", dl.level === 3 && close(dl.delta, 1) && dl.live);
ok("两轨 prev/shown 各自接续不串味", up.prev === 100 && up.shown === 100 && dl.prev === 50 && dl.shown === 50);
// —— F. Δ 分档阈值(0.005 静默线 / 0.05 / 0.30; 端点归属: >=0.005 起 Lv.1, >=0.05 起 Lv.2, >=0.3 Lv.3) ——
// F1(plan 26-11-14-1313): 值>0 的活跃轨恒 >=Lv.1(下限), 分档上限语义不变; 真 0(target==0)
// 与缺口轨(live=false)维持 Lv.0 静默。
const lvl = (prev, target, fl) => _qbFxTrackNext({ shown: prev }, target, fl === undefined ? 1 : fl).level;
ok("值>0 且 Δ<0.5% -> Lv.1(F1 下限; 旧静默线只降档不再归零)", lvl(1000, 1004.9) === 1);
ok("Δ=0.5% -> Lv.1", lvl(1000, 1005) === 1);
ok("Δ<5% Lv.1", lvl(1000, 1049.9) === 1);
ok("Δ=5% -> Lv.2", lvl(1000, 1050) === 2);
ok("Δ<30% Lv.2", lvl(1000, 1299.9) === 2);
ok("Δ=30% -> Lv.3", lvl(1000, 1300) === 3);
ok("真 0(target==0)恒 level 0(零流量静默 —— D2/A3; Δ 大也不升档)",
  _qbFxLevel(9, true, 0) === 0 && lvl(1000, 0) === 0 && _qbFxLevel(0.001, true, 0) === 0);
ok("live=false 恒 level 0(缺口轨静默; target 参不参与缺口判定)",
  _qbFxLevel(9, false) === 0 && _qbFxLevel(0.9, false, 100) === 0);
ok("target 缺参(旧 2 参调用形态)不炸且按 delta 分档(向后兼容 —— 缺参无值可判, 不吃 F1 下限)",
  _qbFxLevel(0.5, true) === 3 && _qbFxLevel(0.001, true) === 0);
// —— G. 缺口轨(live=false)与复活轨(D4/I10: 单列 null 该轨断线不插值, 另一轨照常) ——
let dead = _qbFxTrackNext({ prev: 42, target: 42, shown: 42, delta: 0, level: 1, live: true }, null, 2);
ok("尾桶 null -> 轨死: live=false/level 0/shown null(不插值)", !dead.live && dead.level === 0
  && dead.shown === null && dead.prev === null);
let rev = _qbFxTrackNext({ prev: null, target: null, shown: null, delta: 0, level: 0, live: false }, 500, 2);
ok("复活轨: 无从接续直落真值(不造 0->500 斜坡撒谎, delta=0 零插值), 值>0 恒 >=Lv.1(F1 下限 —— 复活即活跃轨)",
  rev.live && rev.prev === 500 && rev.shown === 500 && rev.delta === 0 && rev.level === 1);
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
// —— I-bis. converge 起步 t=0(模板保真二轮 S5/B5/D1): p=clock/convergeMs(convergeMs=0.6×beat),
//      impact 窗不再钉 prev; ease 越界夹取保留; I4 单调无 overshoot 全域扫(含 p>1 段) ——
ok("I-bis t=0 起步: convergeMs=0.6×beat(非 0.48), clock=0 shown=prev 但 clock>0 立即离开 prev", (() => {
  const tl = _qbBeatTimeline(1500, 0.6);   // beat 600, impact 72
  if (!close(tl.convergeMs, 360)) return false;
  const tr = _qbFxTrackNext({ shown: 10 }, 30, 1);
  const shownAt = (clock) => _qbFxShown(tr, clock / tl.convergeMs);
  return close(shownAt(0), 10) && shownAt(50) > 10 && shownAt(50) < 30;
})());
ok("I-bis impact 窗内(clock=0.06×beat<impact 0.12×beat)shown 已移动, 不再钉 prev", (() => {
  const tl = _qbBeatTimeline(3000, 0.6);   // beat 1000, impact 120
  const tr = _qbFxTrackNext({ shown: 10 }, 30, 1);
  const v = _qbFxShown(tr, 60 / tl.convergeMs);   // 60ms 在 impact 窗内
  return v > 10 && v < 30 && tl.impactMs === 120;
})());
ok("I-bis ease 越界夹取(p>1 shown=target, p=0 shown=prev)且无 overshoot", (() => {
  const tl = _qbBeatTimeline(1500, 0.6);
  const tr = _qbFxTrackNext({ shown: 10 }, 30, 1);
  return close(_qbFxShown(tr, (tl.convergeMs + 100) / tl.convergeMs), 30)
    && close(_qbFxShown(tr, 0), 10);
})());
ok("I-bis I4 单调无 overshoot 全域扫(clock 0..1.2×beat 含 p>1 段, 上行+下行恒在 [prev,target])", (() => {
  const tl = _qbBeatTimeline(1500, 0.6);
  for (const [a, b] of [[10, 30], [30, 10]]) {
    const tr = _qbFxTrackNext({ shown: a }, b, 1);
    let prev = a;
    for (let clock = 0; clock <= tl.beat * 1.2; clock += 5) {
      const v = _qbFxShown(tr, clock / tl.convergeMs);
      if ((b > a ? v < prev - 1e-12 : v > prev + 1e-12)
        || v < Math.min(a, b) - 1e-12 || v > Math.max(a, b) + 1e-12) return false;
      prev = v;
    }
  }
  return true;
})());
// —— J. 锚视口判定单点(计划 26-11-22-0858 换代; 旧 _qbRollJudge/_qbPadTailColumns 退役) ——
// 判据: anchor = max(st.anchor, tail)(单调 —— 旧窗响应晚到不回拖), 组距标称/名义窗长变化
// 或锚位移 > 2 组距滚动域 -> rewin 瞬时落地(防假 morph 语义承袭); 其余位移拍 slide;
// 位移 <= 2 组距恰边界 slide 保持(上界承袭 <= 口径)。
{
  const st0 = { anchor: 1000, step: 1.5, span: 60 };
  ok("J1 锚滑动拍: anchor=max(1000,1001.5)=1001.5 / delta=1.5 / slide / 不 rewin",
    (() => { const j = _qbAnchorJudge(st0, 1001.5, 1.5, 60);
      return j.anchor === 1001.5 && j.delta === 1.5 && j.slide === true && j.rewin === false
        && j.step === 1.5 && j.span === 60; })());
  ok("J2 锚单调(尾回退不回拖 —— 旧窗响应晚到与取数窗口分量构成双防线): anchor 恒 1000 / 零位移",
    (() => { const j = _qbAnchorJudge(st0, 999, 1.5, 60);
      return j.anchor === 1000 && j.delta === 0 && j.slide === false && j.rewin === false; })());
  ok("J3 滚动域外(delta 10 > 2x step) -> rewin 瞬时(缺口折叠多格补拍/停摆补齐不假 morph)",
    (() => { const j = _qbAnchorJudge(st0, 1010, 1.5, 60);
      return j.rewin === true && !j.slide && j.anchor === 1010; })());
  ok("J4 恰 2 组距边界(delta=3)不 rewin(上界承袭 <= 口径)",
    (() => { const j = _qbAnchorJudge(st0, 1003, 1.5, 60); return !j.rewin && j.slide; })());
  ok("J5 组距标称变化 -> rewin(换窗/采样档变更/分组口径上调)",
    (() => { const j = _qbAnchorJudge(st0, 1001.5, 3, 60); return j.rewin === true && j.step === 3; })());
  ok("J6 名义窗长变化 -> rewin(换窗跨段)",
    (() => { const j = _qbAnchorJudge(st0, 1001.5, 1.5, 300); return j.rewin === true && j.span === 300; })());
  ok("J7 位移 3.1 > 3 -> rewin(上界不含, 变异面: 判据改 <= 即红)",
    (() => { const j = _qbAnchorJudge(st0, 1003.1, 1.5, 60); return j.rewin === true; })());
  ok("J8 首拍(st 无 anchor 记账): anchor=tail / delta=0 / 不滑不换档(建图锚起步)",
    (() => { const j = _qbAnchorJudge(null, 1000, 1.5, 60);
      return j.anchor === 1000 && j.delta === 0 && !j.slide && !j.rewin; })());
  ok("J9 meta 缺席防御: step/span 回落 st 记账(判据照常)",
    (() => { const j = _qbAnchorJudge(st0, 1001.5, NaN, NaN);
      return j.step === 1.5 && j.span === 60 && j.slide === true; })());
  ok("J10 全缺参防御: step/span 恒 0(调用方退 auto, 不动画)",
    (() => { const j = _qbAnchorJudge({ anchor: 1000, step: 0, span: 0 }, 1001.5, 0, 0);
      return j.step === 0 && j.span === 0; })());
}
// —— K. x 轴右缘刻位过滤(issue 26-11-17-0936 第三次纠正, 模块级纯函数真跑) ——
{
  const max = 1794896895;   // 5s 整点, 1.5s 桶网格可精确落在其上
  const eps = _QB_X_SPLIT_EPS(max);
  ok("K1 eps 口径: max(1e-9, |vMax|×1e-12), 小域走绝对下限",
    close(eps, max * 1e-12, 1e-18) && _QB_X_SPLIT_EPS(0) === 1e-9
    && _QB_X_SPLIT_EPS(1e-6) === 1e-9);
  // 复刻 vendor $e: 固定 5s 网格, 把 <= vMax 的刻位全算进来(含恰好压在 vMax 的那一条)
  const gridGen = (u, i, min, mx) => {
    const out = [];
    for (let v = Math.ceil(min / 5) * 5; v <= mx; v += 5) out.push(v);
    return out;
  };
  const wrapped = _qbDropRightEdgeSplits(gridGen);
  const interior = [max - 10, max - 5];
  ok("K2 右缘整点被丢, 内部刻位全留(最右纵线不随 vMax 压整点进出)",
    JSON.stringify(wrapped(null, 0, max - 10, max, [], 0, false))
      === JSON.stringify(interior));
  ok("K3 vMax 未压整点时不过滤(vMax 与整点差 > eps)",
    JSON.stringify(wrapped(null, 0, max - 10, max + 1.5 - 1e-3, [], 0, false))
      === JSON.stringify([...interior, max]));
  ok("K4 eps 内微越界也丢(钳零后 1e-3 秒级残差不回潮)",
    JSON.stringify(wrapped(null, 0, max - 10, max + eps / 2, [], 0, false))
      === JSON.stringify(interior));
  ok("K5 透传生成器全部实参 + 返回新数组(不改生成器原结果)",
    (() => {
      const seen = [];
      const ret = [max];
      const spy = function () { seen.push([...arguments]); return ret; };
      const out = _qbDropRightEdgeSplits(spy)("u", 3, 0, max, [1, 5], 2, true);
      return out !== ret && seen.length === 1 && seen[0][0] === "u" && seen[0][1] === 3
        && seen[0][4][1] === 5 && seen[0][5] === 2 && seen[0][6] === true && out.length === 0;
    })());
  ok("K6 生成器返回 null 时回落空数组(不抛)",
    Array.isArray(_qbDropRightEdgeSplits(() => null)(null, 0, 0, max, [], 0, false))
    && _qbDropRightEdgeSplits(() => null)(null, 0, 0, max, [], 0, false).length === 0);
}
// —— L. 在途锚现值 + 历史保留合并 + 余量修剪(尾锚显式视口纯函数面, 计划 26-11-22-0858;
//       旧 _qbBeatVpRem/_qbInheritedViewport 打断继承重建随三不变量退役) ——
{
  const mkAnim = (over) => Object.assign({ needsShift: true, clock: 0, preview: undefined,
    anchorFrom: 1000, anchorTo: 1030, tl: { shiftMs: 600 } }, over || {});
  ok("L1 在途锚: clock=0 = anchorFrom(滑动起点), clock>=shiftMs = anchorTo(目标), [from,to] 单调",
    _qbAnimAnchorAt(mkAnim({ clock: 0 })) === 1000
    && _qbAnimAnchorAt(mkAnim({ clock: 600 })) === 1030
    && _qbAnimAnchorAt(mkAnim({ clock: 5000 })) === 1030
    && (() => { let prev = 999; for (let c = 0; c <= 600; c += 25) {
      const v = _qbAnimAnchorAt(mkAnim({ clock: c }));
      if (!(v >= prev && v <= 1030)) return false; prev = v; } return true; })());
  ok("L2 末帧吸附(clock=599: rem 约 1e-6 < 1e-3 阈值 -> 恰 anchorTo —— issue 26-11-17-0936 口径)",
    _qbAnimAnchorAt(mkAnim({ clock: 599 })) === 1030);
  ok("L3 中段 easeOut 三次曲线特征值(clock=300: e=0.875 -> 锚 = 1000 + 30x0.875)",
    Math.abs(_qbAnimAnchorAt(mkAnim({ clock: 300 })) - (1000 + 30 * 0.875)) < 1e-9);
  ok("L4 纯函数: anim 零 mutate(打断续滑捕获不得污染在途拍状态面)",
    (() => { const a = mkAnim({ clock: 200 }); const snap = JSON.stringify(a);
      _qbAnimAnchorAt(a); return JSON.stringify(a) === snap; })());
  // 历史保留合并(GET 落地清空余量列 -> 旧列真值点回填左缘裁剪数据; F5 补点携带的数据层等价替代)
  const newPts = [{ t: 1100, up: 1, dl: 2 }, { t: 1101.5, up: 1, dl: 2 }];
  const oldPts = [{ t: 1094, up: 1, dl: 2 }, { t: 1096, up: 1, dl: 2 }, { t: 1097.5, up: 1, dl: 2 }, { t: 1099, up: 1, dl: 2 }, { t: 1100, up: 1, dl: 2 }];
  ok("L5 保留合并: t < 新列头(1100, 恰等不并入 —— 与 keepLine 含界 >= 对称)且 >= 余量线(1096)"
    + "的真值点并入, 升序不破",
    (() => { const r = _qbRetainHistory(oldPts, newPts, 1096);
      return r.length === 3 && r[0].t === 1096 && r[2].t === 1099; })());
  ok("L6 保留线外旧点弃(1094 < 1096)且引用共享(点 dict 只读直传)",
    (() => { const r = _qbRetainHistory(oldPts, newPts, 1096); return r[0] === oldPts[1]; })());
  ok("L7 防御: 旧列空/新列空/null/新头无 t -> 空数组(调用方 concat 零操作)",
    _qbRetainHistory([], newPts, 1096).length === 0 && _qbRetainHistory(oldPts, [], 1096).length === 0
    && _qbRetainHistory(null, newPts, 1096).length === 0
    && _qbRetainHistory(oldPts, [{ up: 1 }], 1096).length === 0);
  // 余量修剪(列不变量: [anchor − (span+margin), anchor], margin = 2 组距; 修剪线视口锚优先、
  // 尾点回落 —— 左缘裁剪数据面)
  const pts = Array.from({ length: 45 }, (_, i) => ({ t: 1000 + i * 1.5, up: 1, dl: 2 }));
  const kept = _qbTrimStaleHead(pts, 60 + 3);   // tail=1066, 线=1003 -> 剪 2 点(1000/1001.5)
  ok("L8 余量修剪: 保留窗 = span+margin(63s) -> 列首 1003, 窗内点全留",
    kept.length === 43 && kept[0].t === 1003 && kept[kept.length - 1].t === 1066);
  ok("L9 防线: 尾点无 t 不剪 / keepS 非法不剪(调用方门已滤, 纯函数面零假设)",
    _qbTrimStaleHead([{ up: 1 }], 60).length === 1 && _qbTrimStaleHead(pts, 0) === pts);
  ok("L9b 锚优先: anchorT 领先尾时修剪线按锚(列仍覆盖视口左缘 —— G-B 防回潮; 锚=尾时同形)",
    (() => {
      const ptsA = Array.from({ length: 45 }, (_, i) => ({ t: 1000 + i * 1.5, up: 1, dl: 2 }));
      // 锚 1080 领先尾 1066: 线 = 1080 − 63 = 1017 -> 保留 t >= 1017: 列首 1018(首格 1016.5
      // 落线外), 33 点; 无锚回落尾 1066 -> 线 1003 -> 列首 1003, 43 点
      const keptA = _qbTrimStaleHead(ptsA, 63, 1080);
      return keptA.length === 33 && keptA[0].t === 1018
        && _qbTrimStaleHead(ptsA, 63).length === 43;  // 无锚回落尾 1066 -> 线 1003 -> 列首 1003
    })());

}
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
const { methods, _qbAnimAnchorAt } = new Function(src
  + "\nreturn { methods: window.AQB_QB_TRAFFIC.methods, _qbAnimAnchorAt: _qbAnimAnchorAt };")();
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);
const close_ = (a, b) => Math.abs(a - b) < 1e-9;
// —— 桩环境: 假 rAF 队列 + 可拨动的毫秒时钟 + 可开关的页面可见性 ——
let rafId = 0;
const rafMap = new Map();
global.requestAnimationFrame = (cb) => { rafMap.set(++rafId, cb); return rafId; };
global.cancelAnimationFrame = (id) => { rafMap.delete(id); };
let nowMs = 0;
Object.defineProperty(global, "performance", { value: { now: () => nowMs }, configurable: true });
global.document = { hidden: false };
/* 桩 uPlot 域对象, 提交语义按 vendor qn 忠实复刻: setScale 只写 pending(Kl), commit 消费;
 * redraw(l, e) 按 vendor 语义建模(l !== false 才写 x pending = current —— redraw(false, true)
 * 只提交既有 pending 并强制轴重算, 不写 x scale; 尾锚显式视口下收敛帧 setData(auto 全列宽)后
 * 的显式 setScale pending 必须由 redraw(false, true) 原样提交, 桩不忠实即把显式视口吃掉)。 */
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
      this.pending = { x: { min: d[0][0], max: d[0][d[0].length - 1] } };  // resetScales=true: x auto 全列
      this.commit();
    },
    redraw(l, e) {
      this.redrawCount++;
      if (l !== false) this.pending.x = { min: this.scales.x.min, max: this.scales.x.max };
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
      const xs2 = this.data[0];
      let lo = 0;
      let hi = xs2.length - 1;
      while (lo < hi && xs2[lo] < px.min) lo++;
      while (hi > lo && xs2[hi] > px.max) hi--;
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
/* 拍记账底座(尾锚显式视口换代): anchor = 上一收敛锚(单调跨拍记账), step/span = 组距标称/名义窗长
 * (meta 缺席时 judge 回落本记账 —— 场景不设 qbHistData 即走此路)。 */
function mkBeat(anchor, step, span, upShown, dlShown) {
  return {
    raf: 0, anim: null, anchor, step, span,
    tracks: {
      up: { prev: upShown, target: upShown, shown: upShown, delta: 0, level: 0, live: true },
      dl: { prev: dlShown, target: dlShown, shown: dlShown, delta: 0, level: 0, live: true },
    },
  };
}
const self = Object.assign({}, methods, {
  _qbPollMs: () => 3000,  // multiplier=2: period 3s -> beat 1000 / shift 600 / converge [0,600](t=0 起步)
  _qbCharts: {},
});
const CFG_ON = { enabled: true, on: true, shiftRatio: 0.6 };
global.window.AQB_FX_CFG = CFG_ON;
const XS1 = [1030, 1060, 1090, 1120, 1150];   // 5 点 x 30, 尾 1150
const SPAN1 = 120;                            // 名义窗长(场景不设 meta -> judge 回落 st.span)
const pump = () => {
  const fns = [...rafMap.values()];
  rafMap.clear();
  fns.forEach((f) => f());
  const cu = self._qbCharts.global;
  if (cu && cu.commit) cu.commit();  // 微任务渲染等价(同步块内 setScale 攒 pending, 帧末提交)
};
const drain = () => { let g = 0; while (rafMap.size && g++ < 200) { nowMs += 50; pump(); } return g; };
// —— S0: 桩忠实性对照 —— 无 y 钉的裸 x 提交确实按可视窗重推 y + redraw(false,true) 不写 x pending ——
{
  const u = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u.setScale("x", { min: 1000, max: 1120 });  // 判定帧显式视口
  u.commit();
  ok("S0 桩忠实性: 无 y 钉的 x 提交重推 y(峰值出窗 -> dmax=0 -> top=1, 复现 vendor 漂移)",
    u.scales.y.max === 1);
  const u2 = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u2.setData([XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]]);  // setData 交还 auto(全列宽, 复刻收敛帧)
  u2.setScale("x", { min: 1000, max: 1120 });   // 显式视口 pending(复刻 setData 后的显式重申)
  ok("S0b 桩忠实性: setData 的 auto 与显式视口不同值(auto 全列宽 vs 锚窗), redraw(false,true)"
    + " 只提交既有 pending 不重写 x(尾锚显式视口依赖此语义 —— 桩吃掉 pending 即收敛态回 auto 全列宽)",
    (() => { const before = u2.setScaleLog.length;
      u2.redraw(false, true);
      return u2.scales.x.min === 1000 && u2.scales.x.max === 1120
        && u2.setScaleLog.length === before; })());
}
// —— S1/S2: 完整一拍 —— 起拍视口落滑动起点(上一收敛视口, 左缘连续) + 尾点摆回显示值 + 逐帧锚
//            平移(两缘同步) + 收敛帧真值写回 + 显式视口重申(I1/I3/I4/I8 电池级) ——
{
  const u = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1120, 30, SPAN1, 10, 55);  // 上一收敛锚 1120(旧尾), 尾 1150 -> delta=30 滑动
  self._qbCharts = { global: u };
  const t0 = nowMs;
  self._qbBeatStart("global", u);
  u.commit();
  ok("S1 起拍: rAF 已挂 + 尾点摆回显示值(10/55) + 视口落滑动起点 [1000,1120](= 上一收敛视口,"
    + " 左/右缘双连续 —— 尾锚平移的连续性锚) + y 钉成对(63)", rafMap.size === 1
    && u.data[1][4] === 10 && u.data[2][4] === 55
    && u.setScaleLog.length === 2 && u.setScaleLog[0][0] === "x"
    && u.setScaleLog[0][1] === 1000 && u.setScaleLog[0][2] === 1120
    && u.setScaleLog[1][0] === "y" && u.setScaleLog[1][2] === 63);
  ok("S1 anim 记账: anchorFrom=1120/anchorTo=1150/span=120/needsShift+needsTail 双在场",
    u._qbBeat.anim !== null && u._qbBeat.anim.anchorFrom === 1120
    && u._qbBeat.anim.anchorTo === 1150 && u._qbBeat.anim.span === SPAN1
    && u._qbBeat.anim.needsShift === true && u._qbBeat.anim.needsTail === true);
  const tails = [];
  const ySeen = [];
  while (rafMap.size) {
    nowMs += 50;
    pump();
    if (u._qbBeat.anim && u._qbBeat.anim.phase !== "tail") {
      tails.push([u.data[1][4], u.data[2][4]]);
      ySeen.push(u.scales.y.max);
    }
  }
  ok("S2 I1 电池级: 动画结束时刻 - 判定时刻 <= beat(1000ms)", nowMs - t0 <= 1000);
  ok("S2 尾点序列单调收敛(10->30 与 55->60 无回跳无 overshoot)", tails.length > 3
    && tails.every((v, i) => i === 0 || (v[0] >= tails[i - 1][0] - 1e-12 && v[1] >= tails[i - 1][1] - 1e-12))
    && tails[0][0] >= 10 && tails[tails.length - 1][0] <= 30);
  const xLog = u.setScaleLog.filter((r) => r[0] === "x");
  ok("S2 锚位单调不减滑向目标(min 单调 -> 1150-120=1030, 两缘同步平移跨度恒 120 —— 尾锚平移"
    + "几何; 收敛帧显式重申与末帧锚位同值故取不减), 末笔 max = anchorTo 1150(ulp 吸附落锚)",
    xLog.length > 3
    && xLog.every((r, i) => i === 0 || r[1] >= xLog[i - 1][1] - 1e-9)
    && xLog.every((r) => close_(r[2] - r[1], SPAN1))
    && xLog[xLog.length - 1][2] === 1150);
  ok("S2 I4 纵轴定档: 每帧 y 恒 63(动画全程零漂移), 收敛帧成对钉同值(终态与全列钉值同尺)",
    ySeen.length > 3 && ySeen.every((v) => v === 63) && u.scales.y.max === 63);
  ok("S2 每个 x 提交都成对补 y(x 后紧跟 y; impact 首帧装饰帧保障允许一笔无 x 的独立 y 钉 ——"
    + " 成对面钉的是「x 不单独出现」; 收敛帧末笔显式重申也成对钉 —— 终态不吃锚窗可视重推)",
    u.setScaleLog.every((r, i) => r[0] === "x"
      ? (i + 1 < u.setScaleLog.length && u.setScaleLog[i + 1][0] === "y") : true)
    && u.setScaleLog.filter((r) => r[0] === "y").length >= xLog.length - 1);
  ok("S2 收敛: setData 真值写回 + 显式锚视口重申 [1030,1150](auto 全列宽被覆盖 —— 不变量(1))"
    + " + 锚记账落位 1150", u._qbBeat.anim === null && u.setDataCount === 1
    && u.data[1][4] === 30 && u.data[2][4] === 60
    && u.scales.x.min === 1030 && u.scales.x.max === 1150
    && u._qbBeat.anchor === 1150 && u.redrawCount > 0);
}
// —— S3: 打断接续(L1 值面: 上拍未收敛即被新拍打断, 中断值作新拍 prev; 锚面 = 打断位续滑) ——
{
  const u = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1120, 30, SPAN1, 10, 55);
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  for (let i = 0; i < 5; i++) { nowMs += 50; pump(); }  // clock 200: 尾点已越过 impact 窗
  const midUp = u.data[1][4];
  u.data = [[1060, 1090, 1120, 1150, 1180], [0, 0, 0, 0, 80], [0, 0, 0, 0, 60]];
  self._qbBeatStart("global", u);
  ok("S3 打断: 新拍以当前显示值接续(prev=中断值, 不回跳到 10), 旧 rAF 已摘 + 锚续滑(打断在途"
    + "位 -> 新目标 1180)", rafMap.size === 1
    && midUp > 10 && u._qbBeat.tracks.up.prev === midUp && u.data[1][4] === midUp
    && u._qbBeat.anim.anchorFrom > 1120 && u._qbBeat.anim.anchorTo === 1180);
  drain();
  ok("S3 新拍照常收敛到新真值(80) + 显式视口落 [1060,1180]", u.data[1][4] === 80
    && u._qbBeat.anim === null && u.scales.x.min === 1060 && u.scales.x.max === 1180);
}
// —— S4: 页面隐藏暂停 + 恢复从当前显示值接续(不重播整拍) ——
{
  const u = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1120, 30, SPAN1, 10, 55);
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
  pump();  // 恢复首帧: dt 从 0 起算(不吞隐藏 5s), 锚位与 shown 均无变化 -> 不提交
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
  u._qbBeat = mkBeat(1120, 30, SPAN1, 10, 55);
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  ok("S5 reduce 短路: 零 rAF/真值直落 + 显式锚视口一次落笔 [1030,1150](目标锚 —— 列含余量后"
    + " auto 恒偏宽, reduce 拍的瞬时平移也走显式视口; 旧「零 setScale 交 auto」随显式视口换代)",
    rafMap.size === 0 && u.data[1][4] === 30 && u.data[2][4] === 60
    && u._qbBeat.tracks.up.shown === 30
    && u.setScaleLog.length === 2 && u.setScaleLog[0][0] === "x"
    && u.setScaleLog[0][1] === 1030 && u.setScaleLog[0][2] === 1150);
  // S6 换一份新落袋数据(尾点 +1 格 + 尾值变化), enabled=false 时 L0/L1 必须照常执行
  global.window.AQB_FX_CFG = { enabled: false, on: false, shiftRatio: 0.6 };
  u.data = [[1060, 1090, 1120, 1150, 1180], [0, 0, 0, 0, 40], [0, 0, 0, 0, 60]];
  const xBefore6 = u.setScaleLog.filter((r) => r[0] === "x").length;
  self._qbBeatStart("global", u);
  const xw6 = u.setScaleLog.filter((r) => r[0] === "x").slice(xBefore6);
  ok("S6 enabled=false 不短路: L0/L1 照常执行(数据刷新语义, 不是装饰) + 视口落滑动起点"
    + " [1030,1150](锚 1150 - span 120, S5 reduce 拍已落目标锚; 判定帧新增笔迹)", rafMap.size === 1
    && xw6.length === 1 && xw6[0][1] === 1030 && xw6[0][2] === 1150
    && u.data[1][4] === 30);
  drain();
  ok("S6 enabled=false 收敛落地 + 显式视口 [1060,1180]", u.data[1][4] === 40
    && u._qbBeat.anim === null && u.scales.x.max === 1180);
  global.window.AQB_FX_CFG = CFG_ON;
}
// —— S7/S7a/S7b: 零变化拍(锚零位移)F6 环境层解绑后只跑 fx / 双轨真 0 静默(显式视口照常落笔) /
//            尾值不变滚窗(尾点 +1 格) L0 照常 ——
{
  // F6/D3(plan 26-11-15-1104): 零变化拍 spawn 与早退门解绑 —— 值>0 恒 >=Lv.1(D1)贯彻全窗,
  // 数据面零动画(L0/L1 零 rAF 保留), 只跑 fx 的 impact 窗。显式视口无条件落笔(不变量(1):
  // setData 的列全宽 auto 必须被锚视口覆盖 —— 零变化拍也如此, 旧「零 setScale」随换代退役)。
  const u = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1150, 30, SPAN1, 30, 60);  // 锚已收敛(=尾), 零位移 + 尾值无变化
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  ok("S7 零变化拍(F6 环境层解绑): anim.fx 在场 lv=1 且 anim 不带 shift/tail, 显式视口照常落笔"
    + " [1030,1150](零位移 -> vAnchor=目标), 数据零改写", u._qbBeat.anim !== null
    && u._qbBeat.anim.fx !== null && u._qbBeat.anim.fx.lv === 1
    && u._qbBeat.anim.needsShift === false && u._qbBeat.anim.needsTail === false
    && u.setScaleLog.length === 2 && u.setScaleLog[0][1] === 1030 && u.setScaleLog[0][2] === 1150
    && u.data[1][4] === 30 && u.data[2][4] === 60);
  drain();
  ok("S7 零变化拍收敛: 只跑 fx impact 窗(装饰帧保障 redraw 在场)+ 收敛帧 setData 清场 +"
    + " 显式视口重申", u.redrawCount > 0 && u.setDataCount === 1 && u._qbBeat.anim === null
    && u.scales.x.min === 1030 && u.scales.x.max === 1150 && u.data[1][4] === 30);
}
{
  // F6 收窄后的「双静默」面: 双轨真 0(值恒 0)零变化拍 lead=null -> spawn null -> 零 anim
  // 零 rAF 零数据提交(I10/D2); 显式视口照常落笔(视口面不是数据提交)。
  const u = mkU(XS1, [0, 0, 0, 0, 0], [0, 0, 0, 0, 0]);
  u._qbBeat = mkBeat(1150, 30, SPAN1, 0, 0);
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  ok("S7a 双轨真 0 零变化拍: spawn null 零 rAF 零 anim 零数据提交(I10/D2) + 显式视口照常落笔",
    rafMap.size === 0 && u._qbBeat.anim === null && u.setDataCount === 0 && u.redrawCount === 0
    && u.setScaleLog.length === 2 && u.setScaleLog[0][1] === 1030 && u.setScaleLog[0][2] === 1150);
}
{
  // 尾值不变滚窗(尾点 +1 格, 值不变): 锚平移照播(delta=si) + 尾点零改写(L0 与数据驱动解耦)。
  // 旧「头切驱动摆回」形态(F5 dx0)随尾锚平移退役 —— 头切不动视口, 视口只随尾锚走。
  const u = mkU([1060, 1090, 1120, 1150, 1180], [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1150, 30, SPAN1, 30, 60);  // 锚 1150(旧尾), 尾 1180 -> delta=30 滑动
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  ok("S7b 尾值不变滚窗: L0 锚平移起拍(rAF=1 + 视口落滑动起点 [1030,1150] + y 钉成对) + fx 在场"
    + " lv=1(F1 下限)", rafMap.size === 1
    && u.setScaleLog.length === 2 && u.setScaleLog[0][0] === "x"
    && u.setScaleLog[0][1] === 1030 && u.setScaleLog[0][2] === 1150
    && u.setScaleLog[1][0] === "y"
    && u._qbBeat.anim !== null && u._qbBeat.anim.fx !== null && u._qbBeat.anim.fx.lv === 1);
  const tailAtStart = [u.data[1][4], u.data[2][4]];
  drain();
  ok("S7b 收敛: 尾点零改写(L0 滚动与数据驱动解耦不变) + 显式锚视口重申 [1060,1180]"
    + " + impact 窗装饰帧保障补 redraw", u.data[1][4] === tailAtStart[0]
    && u.data[2][4] === tailAtStart[1] && u.redrawCount > 0 && u.setDataCount === 1
    && u._qbBeat.anim === null && u.scales.x.min === 1060 && u.scales.x.max === 1180);
}
// —— S8: 长窗 0.75px 规则(gate 拒绝 -> 瞬时落地到目标锚视口, 尾点真变化仍收敛) ——
{
  const xs = Array.from({ length: 2880 }, (_, i) => 1000 + i * 30);
  const up = new Array(2880).fill(0);
  up[2879] = 30;
  const dl = new Array(2880).fill(0);
  const u = mkU(xs, up, dl);
  // 上一收敛锚 = 旧尾 87340(= 1000 + 2878x30), 尾 87370 -> delta=30; nWin = span/step = 2880
  // -> cellPx = 800/2880 约 0.28 < 0.75 -> gate 拒绝 -> 瞬时落地目标锚视口 [970, 87370]
  u._qbBeat = mkBeat(87340, 30, 86400, 10, 0);
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  ok("S8 长窗 0.75px 规则: gate 拒绝不播平移(零滑动帧), 显式目标视口一次落笔 [970,87370]"
    + "(瞬时落地也有真值视口 —— 旧 auto 落地面退役, instant/长窗恒定压缩变体随补点退役消失)",
    u.setScaleLog.length === 2 && u.setScaleLog[0][0] === "x"
    && u.setScaleLog[0][1] === 970 && u.setScaleLog[0][2] === 87370
    && rafMap.size === 1 && u.data[1][2879] === 10);
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
    && u.redrawCount > 3 && u.setScaleLog.every((r) => r[0] !== "x" || (r[1] === 970 && r[2] === 87370))
    && ySeen.length > 3 && ySeen.every((v) => v === 31.5));
}
// —— S9/S9b/S9c: 跨窗换档瞬时(组距标称/名义窗长变化 -> rewin)/滚动域外(delta > 2x step)瞬时/
//            恰 2 组距边界仍平移 ——
{
  // 真换档: 组距标称 30 -> 60 + 名义窗长 120 -> 240(meta 显式传入 —— 生产 meta 恒在场,
  // 场景经 qbHistData 提供)。数据/视口面瞬时落地到新窗长锚视口(不造假 morph), fx 照常在场。
  self.qbHistData = { meta: { interval_s: 60, span_s: 240 } };
  const u = mkU([1120, 1180, 1240], [0, 0, 50], [0, 0, 70]);
  u._qbBeat = mkBeat(1000, 30, 120, 10, 55);
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  ok("S9 真换档(组距 30->60 + 窗长 120->240 -> rewin): 瞬时落地新窗长锚视口 [1000,1240]"
    + "(尾桶已非同一桶, 不造假 morph) + shown 直落真值 + fx 环境层在场(F6 解绑)",
    rafMap.size === 1 && u.setScaleLog.length === 2 && u.setScaleLog[0][0] === "x"
    && u.setScaleLog[0][1] === 1000 && u.setScaleLog[0][2] === 1240
    && u._qbBeat.tracks.up.shown === 50 && u._qbBeat.anim !== null
    && u._qbBeat.anim.fx !== null && u._qbBeat.anim.needsShift === false
    && u._qbBeat.anim.needsTail === false && u._qbBeat.step === 60 && u._qbBeat.span === 240);
  drain();
  self.qbHistData = undefined;
}
{
  // 滚动域外: delta = 210 > 2x step(60) -> rewin 瞬时(停摆多拍补齐不假 morph)
  const u = mkU([1090, 1120, 1150, 1180, 1210], [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1000, 30, SPAN1, 30, 60);
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  ok("S9b 滚动域外(delta=210 > 2x step): 瞬时落地目标锚视口 [1090,1210] + fx 照常在场",
    rafMap.size === 1 && u.setScaleLog.length === 2 && u.setScaleLog[0][1] === 1090
    && u.setScaleLog[0][2] === 1210 && u._qbBeat.tracks.up.shown === 30
    && u._qbBeat.anim !== null && u._qbBeat.anim.needsShift === false);
  drain();
}
{
  // 恰 2 组距边界(delta = 60 = 2x step 30): 仍在滚动语义内, 照播锚平移(判据改 < 即红)
  const u = mkU([1060, 1090, 1120, 1150, 1180], [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1120, 30, SPAN1, 30, 60);  // 锚 1120(旧尾), 尾 1180 -> delta=60=2x step
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  ok("S9c 恰边界(delta=2x step): 仍播锚平移(rAF=1 + 视口落滑动起点 [1000,1120] + y 钉成对)",
    rafMap.size === 1 && u.setScaleLog.length === 2 && u.setScaleLog[0][0] === "x"
    && u.setScaleLog[0][1] === 1000 && u.setScaleLog[0][2] === 1120
    && u.setScaleLog[1][0] === "y");
  drain();
  ok("S9c 恰边界收敛落地: 尾值无变化(数据面零改写), setData + 显式视口重申 [1060,1180]",
    u._qbBeat.anim === null && u.redrawCount > 0 && u.setDataCount === 1
    && u.data[1][4] === 30 && u.data[2][4] === 60
    && u.scales.x.min === 1060 && u.scales.x.max === 1180);
}
// —— S10: 销毁终止(换肤/关抽屉路径) ——
{
  const u = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1120, 30, SPAN1, 10, 55);
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
// —— S11: 在途拍内 _qbChartRescale(y 切档/限速变化入口): 终止在途拍直接落真值 + 显式视口重申 ——
{
  const u = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1120, 30, SPAN1, 10, 55);
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  for (let i = 0; i < 4; i++) { nowMs += 50; pump(); }  // clock 150: 插值中
  ok("S11 前置: 在途拍插值中(尾点偏离真值)", u._qbBeat.anim !== null && u.data[1][4] > 10
    && u.data[1][4] < 30);
  self._qbChartRescale("global");
  ok("S11 rescale: 在途拍终止 + 真值直接落袋 + setData + 显式锚视口重申 [1030,1150]"
    + "(锚记账不动 —— y 重排不搬窗口)", rafMap.size === 0 && u._qbBeat.anim === null
    && u.data[1][4] === 30 && u.data[2][4] === 60 && u.setDataCount === 1
    && u.scales.x.min === 1030 && u.scales.x.max === 1150);
  pump();
  ok("S11 rescale 后无残余帧", u.setDataCount === 1 && u._qbBeat.anim === null);
}
// —— S12: 零变化连拍(plan §03 I6 行验收列「Δ≈0 连拍 10 次叠加层零绘制(静态网格不计)」
//          的电池级等价)。F6/D3 后口径: 连拍不整拍静默 —— 值>0 每拍出 fx 的 impact 窗,
//          每拍 fx 即抛即清(收敛帧清场零残留)、数据面零改写、显式视口每拍落笔(静止态同值)、
//          setData 恰收敛帧一笔; 全静默半边(真 0)归 S12b。 ——
{
  const u = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1150, 30, SPAN1, 30, 60);  // 锚已收敛 = 尾: 每一拍都是零变化拍
  self._qbCharts = { global: u };
  const d0 = u.setDataCount;
  let clean = true;
  for (let i = 0; i < 10; i++) {
    const xBefore = u.setScaleLog.filter((r) => r[0] === "x").length;
    self._qbBeatStart("global", u);
    if (!(u._qbBeat.anim !== null && u._qbBeat.anim.fx !== null && u._qbBeat.anim.fx.lv === 1
      && u._qbBeat.anim.needsShift === false && u._qbBeat.anim.needsTail === false)) clean = false;
    const xw = u.setScaleLog.filter((r) => r[0] === "x").slice(xBefore);
    if (!(xw.length === 1 && xw[0][1] === 1030 && xw[0][2] === 1150)) clean = false;
    drain();
    if (!(u._qbBeat.anim === null && u.setDataCount === d0 + i + 1
      && u.data[1][4] === 30 && u.data[2][4] === 60
      && u.scales.x.min === 1030 && u.scales.x.max === 1150)) clean = false;
  }
  ok("S12 零变化连拍 10 次(F6 口径): 每拍 fx 在场即抛即清(收敛帧清场零残留), 数据面零改写,"
    + " 显式视口每拍同值落笔(零位移 -> 目标锚), setData 恰收敛帧一笔(叠加层零累积 —— I6)", clean);
}
{
  // 真 0 连拍(F6 后全静默面只属于真 0/缺口): 双轨恒 0 -> lead=null -> spawn null ->
  // 连拍 10 次每拍零 rAF 零 anim 零数据提交; 显式视口照常落笔(视口面非数据面)。
  const u = mkU(XS1, [0, 0, 0, 0, 0], [0, 0, 0, 0, 0]);
  u._qbBeat = mkBeat(1150, 30, SPAN1, 0, 0);
  self._qbCharts = { global: u };
  const at0 = { scale: u.setScaleLog.length, data: u.setDataCount, redraw: u.redrawCount };
  let silent = true;
  for (let i = 0; i < 10; i++) {
    self._qbBeatStart("global", u);
    if (rafMap.size !== 0 || u._qbBeat.anim !== null) silent = false;
    if (u.setDataCount !== at0.data || u.redrawCount !== at0.redraw) silent = false;
    if (u.setScaleLog.length !== at0.scale + 2 * (i + 1)) silent = false;
  }
  ok("S12b 双轨真 0 零变化连拍 10 次: 每拍零 rAF 零 anim 零数据提交(I10/D2) + 显式视口照常"
    + " 落笔(静止态)", silent);
}
// —— S13: 动画中悬停读数面(I4 行为化, 静态钉 i 的运行时等价): tooltip 读 points 真值,
//          与 L1 插值写面(u.data)零交集; 索引钳制(越界/负值 -> null) ——
{
  const u = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1120, 30, SPAN1, 10, 55);
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  for (let i = 0; i < 4; i++) { nowMs += 50; pump(); }  // clock 200: 尾点插值中(收敛窗内)
  ok("S13 前置: 动画在途且 u.data 尾点已偏离真值(插值写面有假值)", u._qbBeat.anim !== null
    && u.data[1][4] > 10 && u.data[1][4] < 30);
  self.qbHistData = { points: [{ t: 1030, up: 30, dl: 60 }, null, { t: 1090, up: 28, dl: 58 },
      { t: 1120, up: 29, dl: 59 }, { t: 1150, up: 30, dl: 60 }],
    limits: [], meta: { interval_s: 30 } };
  self.qbHistHoverIdx = 4;
  self.qbHistHoverLeft = 0;
  self._qbChartWs = { global: 800 };
  self.fmtTime = (ts) => "T" + ts;
  const h = self._qbHoverOf("global");
  ok("S13 动画中悬停: 读 points 真值 30/60(不读 u.data 插值面 —— tooltip 与已落袋真值逐字一致)",
    !!h && h.up === 30 && h.dl === 60 && h.gap === undefined && h.flip === false);
  self.qbHistHoverIdx = 99;
  ok("S13 索引越界 -> null(I8 钳制: 不越界读不造 undefined)", self._qbHoverOf("global") === null);
  self.qbHistHoverIdx = -1;
  ok("S13 负索引 -> null", self._qbHoverOf("global") === null);
  self.qbHistHoverIdx = 1;
  const hg = self._qbHoverOf("global");
  ok("S13 缺口桶悬停: gap=true + 区段 mid(链中间的洞走区段判据 —— 链 [0,4] 内 idx1 的洞), 同样零 u.data 触碰",
    !!hg && hg.gap === true && hg.zone === "mid");
  self.qbHistData = { points: [{ t: 1030, up: 30, dl: 60 }, { t: 1060, dl: null, up: null },
      { t: 1090, up: 28, dl: 58 }, { t: 1120, up: 29, dl: 59 }, { t: 1150, up: 30, dl: 60 }],
    limits: [], meta: { interval_s: 30 } };
  self.qbHistHoverIdx = 1;
  const hg2 = self._qbHoverOf("global");
  ok("S13b 显式空值点悬停(schema=2): gap=true + 区段 mid(双 null 分支真执行 —— 不按数据点渲染"
    + " null 速率, 零 u.data 触碰)",
    !!hg2 && hg2.gap === true && hg2.zone === "mid" && hg2.up === undefined && hg2.dl === undefined);
  self.qbHistHoverIdx = 0;
  const ht2 = self._qbHoverOf("global");
  ok("S13b 对照: 空值点列的真值点照常出速率(gap 分支不误吞真值点)",
    !!ht2 && ht2.up === 30 && ht2.dl === 60 && ht2.gap === undefined);
  self.qbHistData = undefined;
  drain();
}
// —— S14: 打断续滑(统一语义, 计划 26-11-22-0858; 旧方向B S21/S24/S25/S26 四场景随「在途锚
//          直读」统一为一族): 在途平移拍被零位移对账拍打断(GET 落袋撞滑动窗)—— 新拍从在途锚
//          续滑剩余位移(视口连续零回跳; 旧形态此处视口会跳回列全宽 auto) ——
{
  global.window.AQB_FX_CFG = CFG_ON;
  const u = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1120, 30, SPAN1, 30, 60);   // 拍 A: 锚 1120 -> 1150 平移
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  for (let i = 0; i < 3; i++) { nowMs += 50; pump(); }   // clock 150: 平移中段
  const hold = _qbAnimAnchorAt(u._qbBeat.anim);
  ok("S14 捕获: 在途平移拍取消瞬间锚位(自身状态直读 —— 旧 _qbInheritedViewport 公式重建退役)",
    hold > 1120 && hold < 1150);
  // 零位移对账拍打断(GET 落袋, 列同形同值: 尾 1150 == st.anchor -> delta=0)
  const logLenA = u.setScaleLog.length;
  self._qbBeatStart("global", u);
  const jx = u.setScaleLog[logLenA];
  const jy = u.setScaleLog[logLenA + 1];
  ok("S14 判定帧: 零位移打断照续滑(剩余位移 > 0 -> slide), 视口落打断瞬间锚位(零回跳 —— 旧形态"
    + " 此处会落到列全宽 auto)+ x/y 钉成对 + anim anchorFrom = 在途锚",
    rafMap.size === 1 && !!jx && jx[0] === "x"
    && Math.abs(jx[1] - (hold - SPAN1)) < 1e-9 && Math.abs(jx[2] - hold) < 1e-9
    && !!jy && jy[0] === "y"
    && u._qbBeat.anim !== null && u._qbBeat.anim.needsShift === true
    && Math.abs(u._qbBeat.anim.anchorFrom - hold) < 1e-9
    && u._qbBeat.anim.anchorTo === 1150);
  const logLenB = u.setScaleLog.length;
  drain();
  const xLog14 = u.setScaleLog.slice(logLenB).filter((r) => r[0] === "x");
  ok("S14 收敛: 剩余位移滑完(min 从打断位单调滑向 1030, 全程无回跳) + 显式视口重申 [1030,1150]"
    + " + 锚记账落位", u._qbBeat.anim === null && u.setDataCount === 1
    && xLog14.length > 2
    && xLog14.every((r, i) => i === 0 || r[1] >= xLog14[i - 1][1] - 1e-9)
    && xLog14[0][1] >= hold - SPAN1 - 1e-9 && xLog14[xLog14.length - 1][2] === 1150
    && u.scales.x.min === 1030 && u._qbBeat.anchor === 1150);
}
// —— S15: 真滚动打断(新样本拍打断在途平移拍: 尾点 +1 格真推进)—— 新拍从打断位续滑到新目标
//          (单调锚 max(旧目标, 新尾)), 不回跳旧锚 ——
{
  global.window.AQB_FX_CFG = CFG_ON;
  const u = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1120, 30, SPAN1, 30, 60);
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  for (let i = 0; i < 3; i++) { nowMs += 50; pump(); }
  const hold15 = _qbAnimAnchorAt(u._qbBeat.anim);
  // 新样本拍打断(尾点 t 1180 推进一格 + 尾值真变化)
  u.data = [[1060, 1090, 1120, 1150, 1180], [0, 0, 0, 0, 80], [0, 0, 0, 0, 60]];
  const logLenC = u.setScaleLog.length;
  self._qbBeatStart("global", u);
  const jx15 = u.setScaleLog[logLenC];
  ok("S15 真滚动打断: 视口落打断位(min/max 都从打断位续滑 —— 不回跳旧锚 1120) + anim"
    + " anchorTo = 1180(单调锚 max(旧目标 1150, 新尾 1180))+ 尾值真变化 needsTail 同拍",
    rafMap.size === 1 && !!jx15 && jx15[0] === "x"
    && Math.abs(jx15[1] - (hold15 - SPAN1)) < 1e-9 && Math.abs(jx15[2] - hold15) < 1e-9
    && u._qbBeat.anim.anchorTo === 1180 && u._qbBeat.anim.needsTail === true
    && u._qbBeat.anim.needsShift === true);
  const logLenD = u.setScaleLog.length;
  drain();
  const xLog15 = u.setScaleLog.slice(logLenD).filter((r) => r[0] === "x");
  ok("S15 收敛: 平移滑过旧目标 1150 滑向新尾 1180(帧循环 x 提交末笔 max > 1150)"
    + " + 尾值 80 真值写回 + 显式视口 [1060,1180]",
    u._qbBeat.anim === null && u.data[1][4] === 80
    && xLog15.length >= 2 && xLog15[xLog15.length - 1][2] > 1150
    && u.scales.x.min === 1060 && u.scales.x.max === 1180);
}
// —— S16: 换窗(rewin)打断在途平移拍不续滑 —— 几何不连续瞬时落地到新窗长锚视口(继承位让位
//          原生锚形; 旧继承门 !rewin 语义承袭) ——
{
  global.window.AQB_FX_CFG = CFG_ON;
  const u = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1120, 30, SPAN1, 30, 60);
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  for (let i = 0; i < 3; i++) { nowMs += 50; pump(); }
  const logLenE = u.setScaleLog.length;
  // 换窗打断(组距标称 30 -> 60 + 窗长 120 -> 240 = 真换档) —— meta 在拍 A 起拍之后才落,
  // 拍 A 走 st 回落正常滑动, 打断拍读新 meta 判 rewin(生产换窗 = 新 meta 随响应落袋)。
  self.qbHistData = { meta: { interval_s: 60, span_s: 240 } };
  u.data = [[1000, 1060, 1120, 1180, 1240], [7, 0, 0, 0, 80], [9, 0, 0, 0, 60]];
  self._qbBeatStart("global", u);
  const jx16 = u.setScaleLog[logLenE];
  ok("S16 rewin 打断不续滑: 瞬时落地新窗长锚视口 [1000,1240](尾 1240 - span 240, 不落打断位)"
    + " + anim 无 needsShift + step/span 重定标", rafMap.size === 1 && !!jx16 && jx16[0] === "x"
    && jx16[1] === 1000 && jx16[2] === 1240
    && u._qbBeat.anim !== null && u._qbBeat.anim.needsShift === false
    && u._qbBeat.step === 60 && u._qbBeat.span === 240);
  drain();
  ok("S16 rewin 打断收敛: fx-only 拍照常收口 + 显式视口保持", u._qbBeat.anim === null
    && u.scales.x.min === 1000 && u.scales.x.max === 1240);
  self.qbHistData = undefined;
}
// —— S17: 旧窗响应晚到(tail < 锚)不回拖 —— 单调锚(不变量(1))调度器面: 视口静止在当前锚 ——
{
  global.window.AQB_FX_CFG = CFG_ON;
  const u = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1150, 30, SPAN1, 30, 60);   // 锚已收敛 1150
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);   // 先落一笔目标视口 [1030,1150]
  drain();
  const minBefore = u.scales.x.min;
  // 旧窗响应(尾 1120 < 锚 1150)落袋: delta=0 -> 视口静止(不回拖)
  u.data = [[1000, 1030, 1060, 1090, 1120], [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]];
  self._qbBeatStart("global", u);
  ok("S17 单调锚: 尾回退(delta<0 -> j.anchor=max=1150)零位移 -> 视口静止 [1030,1150](不回拖)"
    + " + 锚记账保持", u.setScaleLog.filter((r) => r[0] === "x").slice(-1)[0][1] === 1030
    && u.scales.x.min === minBefore && u._qbBeat.anchor === 1150
    && u._qbBeat.anim !== null && u._qbBeat.anim.needsShift === false);
  drain();
  ok("S17 收敛: 视口恒 [1030,1150]", u._qbBeat.anim === null
    && u.scales.x.min === 1030 && u.scales.x.max === 1150);
}
// —— S18: instant 档(gate 拒绝)瞬时落地目标锚视口 —— 旧方向A「auto 落地含补点全宽 = 恒定压缩」
//          变体随补点退役结构性消失: 显式目标视口恒等名义窗 ——
{
  global.window.AQB_FX_CFG = { enabled: true, on: true, shiftRatio: 0.6, shift: "instant" };
  const u = mkU([1060, 1090, 1120, 1150, 1180], [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1150, 30, SPAN1, 30, 60);   // delta=30 滑动候选
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  ok("S18 instant 档: gate 拒绝 -> 瞬时落地目标锚视口 [1060,1180](跨度恰名义窗 —— 压缩不可表达)"
    + " + 零滑动帧 + fx 照常在场", rafMap.size === 1
    && u.setScaleLog.filter((r) => r[0] === "x").length === 1
    && u.setScaleLog[0][1] === 1060 && u.setScaleLog[0][2] === 1180
    && u._qbBeat.anim !== null && u._qbBeat.anim.needsShift === false
    && u._qbBeat.anim.fx !== null);
  drain();
  ok("S18 instant 档收敛: 显式视口保持 [1060,1180]", u._qbBeat.anim === null
    && u.scales.x.min === 1060 && u.scales.x.max === 1180);
  global.window.AQB_FX_CFG = CFG_ON;
}
// —— S19: 建图拍底座: 真 _qbChartBuild + 桩 uPlot/DOM 全链跑通 —— 拍底座 anchor/step/span
//          初值取列尾/meta 组距标称/名义窗长 + 建图初始视口播种(免首绘 auto 全列宽闪帧) ——
{
  global.document.getElementById = () => null;
  global.document.createElement = () => ({});
  global.document.head = { appendChild() {} };
  global.document.documentElement = { addEventListener() {} };
  global.getComputedStyle = () => ({ getPropertyValue: () => "" });
  global.ResizeObserver = function () { return { observe() {}, disconnect() {} }; };
  let builtOpts = null;
  global.uPlot = function (opts, data) {
    builtOpts = opts;
    return { root: { isConnected: true, querySelector: () => null }, data,
      scales: { x: { min: data[0][0], max: data[0][data[0].length - 1] }, y: { min: 0, max: 1 } },
      bbox: { left: 60, top: 10, width: 800, height: 300 },
      setData() {}, redraw() {}, setScale() {}, destroy() {} };
  };
  const host19 = { isConnected: true, clientWidth: 800, clientHeight: 300, addEventListener() {} };
  self.$refs = { qbChartHost: host19 };
  self.drawerIsTraffic = true;
  self.drawer = { open: true, scope: "global" };
  self.page = "groups";
  self._qbCharts = {};
  self._qbChartRos = {};
  self._qbThemeBound = false;
  // schema=2 相位抖动列(真值 t 间距 29/2/29/30 浮动) + meta 组距标称 30 / 名义窗长 150
  self.qbHistData = { points: [{ t: 1000, up: 1, dl: 2 }, { t: 1029, up: 3, dl: 4 },
      { t: 1031, up: 5, dl: 6 }, { t: 1060, up: 7, dl: 8 }, { t: 1090, up: 9, dl: 10 }],
    totals: [], limits: [],
    meta: { interval_s: 30, span_s: 150, sample_interval_s: 1.5, schema: 2, stride: 1 } };
  self._qbChartBuild("global");
  const u19 = self._qbCharts.global;
  ok("S19 建图拍底座(anchor = 列尾真值 1090 / step = meta 组距标称 30(非 xs[1]-xs[0]=29) /"
    + " span = meta 名义窗长 150) + 悬停锚 anchor.xs 全列真值",
    !!u19 && u19._qbBeat.anchor === 1090 && u19._qbBeat.step === 30 && u19._qbBeat.span === 150
    && !!self._qbAnchors.global && self._qbAnchors.global.xs.length === 5);
  ok("S19 建图初始视口播种: opts.scales.x.min/max = [锚-span, 锚] = [940,1090](免首绘 auto 全列宽"
    + " 闪帧 —— 旧 auto 起步随显式视口换代)",
    !!builtOpts && builtOpts.scales.x.min === 940 && builtOpts.scales.x.max === 1090);
  self.qbHistData = undefined;
  self.$refs = undefined;
  self.drawerIsTraffic = false;
  self.drawer = { open: false, scope: "" };
  self.page = "";
  self._qbThemeBound = false;
}
// —— S20b: 收敛帧显式视口重申的变异盲区封堵(列含余量): 列 = [余量点 1000] + 窗内 [1030..1150]
//          —— setData 交还的 auto = 列全宽 [1000,1150](跨度 150 != 名义窗 120), 收敛帧必须重申
//          锚视口 [1030,1150] —— 重申行删除即本用例红(其余场景列恒真值无余量, auto 与锚视口
//          同形拦不住) ——
{
  const u = mkU([1000].concat(XS1), [0, 0, 0, 0, 0, 30], [0, 0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1120, 30, SPAN1, 0, 0);   // 锚 1120, 尾 1150 -> delta=30 平移; 双轨有收敛面(shown=0 vs 尾值 30/60 经 _qbFxTrackNext -> needsTail=true), 断言面不变
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  ok("S20b 起拍: 视口落滑动起点 [1000,1120](余量点 1000 恰贴视口左缘 —— 左缘裁剪数据在位)",
    u.setScaleLog.length === 2 && u.setScaleLog[0][1] === 1000 && u.setScaleLog[0][2] === 1120);
  drain();
  ok("S20b 收敛: setData 交还列全宽 auto [1000,1150] 被显式锚视口 [1030,1150] 覆盖(跨度恰名义窗)"
    + " —— 收敛帧重申行删除即本断言红(变异盲区封堵)",
    u._qbBeat.anim === null && u.scales.x.min === 1030 && u.scales.x.max === 1150
    && u.scales.x.max - u.scales.x.min === SPAN1);
}
// —— S20c: 余量持峰(收敛帧 y 成对钉的变异盲区封堵): 余量列含真实峰值点(80 > 可视窗峰 60)——
//          判定帧全列扫描钉 y=84, 收敛帧 setData 后 x 重申的 pending 被 redraw(false,true) 消费
//          时 vendor 按锚窗可视数据重推 y(余量峰值剔出 -> 63), 不成对钉即终态 y=63 != 全列钉值
//          84 —— 每拍纵轴泵动两次(收敛帧掉档/下拍判定帧弹回), 峰值滑出余量才止 ——
{
  const u = mkU([1000].concat(XS1), [80, 0, 0, 0, 0, 30], [0, 0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1120, 30, SPAN1, 0, 0);   // 锚 1120, 尾 1150 -> delta=30 平移
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  ok("S20c 起拍: 全列扫描钉 y=84(余量峰值 80 入档 —— 全列真值基准, 非可视窗) + 视口落滑动起点"
    + " [1000,1120]",
    u.setScaleLog.length === 2 && u.setScaleLog[0][0] === "x"
    && u.setScaleLog[0][1] === 1000 && u.setScaleLog[0][2] === 1120
    && u.setScaleLog[1][0] === "y" && u.setScaleLog[1][2] === 84);
  const ySeen20c = [];
  let guard20c = 0;
  while (rafMap.size && guard20c++ < 200) {
    nowMs += 50;
    pump();
    if (u._qbBeat.anim) ySeen20c.push(u.scales.y.max);
  }
  ok("S20c 收敛: 终态 y == 全列钉值 84 且动画期零泵动(可视窗基准 63 被成对钉盖住 —— 收敛帧 y"
    + " 钉行删除即红)",
    u._qbBeat.anim === null && ySeen20c.length > 0 && ySeen20c.every((v) => v === 84)
    && u.scales.y.max === 84 && u.scales.x.min === 1030 && u.scales.x.max === 1150);
}
  ok("L9c 摘要窗内桶数(schema=2): 余量列不计(t >= 尾t − span_s 现数), 缺 span_s/旧契约回落全列长"
    + " —— 变异面: 比较符/线常数/回落分支各自变异即红",
    (() => {
      const mkVmL = (data) => Object.assign(Object.create(self), { qbHistData: data });
      const win = { points: [{ t: 1000, up: 1, dl: 2 }, { t: 1010, up: 1, dl: 2 }, { t: 1020, up: 1, dl: 2 }],
        totals: [], limits: [], meta: { schema: 2, interval_s: 10, span_s: 20 } };
      const margin = { points: [{ t: 995, up: 1, dl: 2 }].concat(win.points),
        totals: [], limits: [], meta: { schema: 2, interval_s: 10, span_s: 20 } };
      const agg = { points: [null, { up: 5 }, null, { up: 7 }], totals: [], limits: [],
        meta: { interval_s: 3600 } };
      const r1 = mkVmL(margin)._qbSummaryOf("global");   // 余量点 995 < 1020-20=1000 -> 不计
      const r2 = mkVmL(agg)._qbSummaryOf("global");      // 旧契约回落全列长 4
      return !!r1 && r1.buckets === 3 && !!r2 && r2.buckets === 4
        && mkVmL(win)._qbSummaryOf("global").buckets === 3;
    })());
console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));

"""


def test_frontend_qb_beat_kernel_battery():
    """节拍内核 S1 电池 + 接缝静态钉(plan 26-11-12-1139 §03 节奏模型/L0/L1, §06 S1 行)

    行为面(node 电池, 无 node 静默跳过, 同 _NODE_QB_TRAFFIC_PROBE 口径):
    1. 节奏公式四组(I1/I2): multiplier 1(1.5s->600ms)/2(3s->夹顶 1000)/8(12s->夹顶)/600s 长窗
      (夹顶); beat 下限 320 与非法 period 防御;
    2. 每拍时间线(§03 公式代码块): impact 0.12 / shift=shiftRatio×beat(防御夹取 [0.2,1] 与
      缺省 0.6)/ converge [0,0.6](t=0 起步 —— B5/D1; impact 窗 shown 已移动不再钉 prev) /
      tail = min(period-beat, 2000) 封顶非常驻(P5);
      animEnd <= beat <= 1000 全域扫(I1 真值在 t<=beat<=1s 完全落地的可验证面, 公式
      max(shiftRatio,0.6)×beat 不变);
    3. easeOut 单调无 overshoot(D9 禁 spring): 1000 采样单调不减、恒在 [0,1]、端点/特征值;
      越界夹取保留(p=clock/convergeMs 越界自然落 prev/target 端点); I4 全域 clock 扫
      (0..1.2×beat, 含 p>1 段)单调无 overshoot 且值恒 [prev,target];
    4. 0.75px 最小可见位移规则: 短窗播 L0 / 长序列(旧 2880 点 24h 形, F1 后生产不可达, 保留为内核行为钉)瞬时 / 0.75 边界(>=)/ 量不到宽瞬时;
    5. L1 双轨独立(I10/D2): 上传 Δ=0 恒 Lv.1 下限(F1 值>0) + 下载 Lv.3 各自正确; Δ 分档端点归属(0.005/0.05/0.30, 上限不变); 真 0/缺口轨恒静默;
      缺口轨 live=false 不插值(D4)/复活轨直落真值不造斜坡/分母可视下限防爆炸/0->0 守卫;
    6. 以显示值接续不回跳(I3): 打断中值作下一拍 prev, 上下行收敛序列单调落在 [prev,target] 内、
      终点恰真值;
    7. 调度器行为面(_NODE_QB_BEAT_SCHED_PROBE: 真 mixin 方法 + **提交语义忠实 vendor 的桩 uPlot**
      (setScale 攒 pending、x 提交即 An(!0)、y 无钉按可视窗重算/有钉原样拷贝, S0 对照用例先证桩
      会漂移) + 假 rAF/时钟, 逐帧断言): 完整一拍(起拍视口摆回旧位 [xs0-old] + 尾点摆回显示值
      -> 逐帧 dx 单调收缩归零 + 两轨尾点单调收敛 + 收敛帧 setData 交还 auto/真值写回/强制轴重算,
      动画结束-判定 <= beat = I1 电池级)/打断接续(中断值作新拍 prev 不回跳, 旧 rAF 已摘)/页面
      隐藏暂停(时钟冻结零变化)与恢复接续(不吞隐藏时长不重播)/reduce 短路(零 rAF 零 setScale
      真值面) vs enabled=false 不短路(L0/L1 照常)/零变化拍 F6 环境层解绑(只跑 fx 的 impact
      窗, 数据面零 x 提交零改写; 真 0 全静默归 S7a)/长窗 0.75px(零 setScale 但尾点
      真变化仍收敛)/跨窗换档瞬时(数据/视口面 —— fx 照常在场, F6)/多桶滚动(roll 上界
      dx0>2x step)瞬时(同 F6 口径)/_qbChartDestroy 先摘 rAF
      后销毁无残余帧;
    8. I4 纵轴定档电池级(评审 #1 回归钉): 起拍与每个 shift 帧 setScale("x") 成对补 setScale("y",
      全窗真值档位 yMax = _qbYRange x _qbYCapOf 口径) —— 动画全程 y 恒定零漂移(桩忠实复刻下,
      无钉时 y 会随偏置窗剔出窗沿峰值垂直跳), 收敛帧与 x 重申成对钉同值(终态与全列钉值同尺
      —— 余量列持峰时 auto 重推按锚窗可视基准会泵动, S20c 封堵); x/y 提交计数相等;
      零变化滚窗(S7b)与纯数值收敛帧(S8)的 y 钉面各自覆盖;
    9. rescale 在途拍收口(评审 #6 回归钉): _qbChartRescale 在插值中触发 -> 在途拍终止 + 真值
      直接落袋 + setData 交还(不留半帧), 后续无残余帧;
    10. S4-a 盘点轮补三面(plan §10 探针的电池级等价; F1 后 S7b 改钉 fx 恒在场 lv=1 —— 值>0 恒 >=Lv.1, 原「双轨静默零装饰」面收窄为真 0/缺口轨(
      调度器面 —— L0 窗口滚动照滚); F6/D3 后 S7 改钉零变化拍只跑 fx 的 impact 窗(数据面零
      x 提交零改写)+ S7a 真 0 全静默 + S12 零变化连拍 10 次 fx 即抛即清(叠加层零累积)/S12b
      真 0 连拍全静默; S13 动画中悬停读数面行为化(_qbHoverOf 读 Vue points 真值 30/60 不读 u.data 插值面 +
      索引越界与负值 null(I8 钳制) + 链中洞 gap=true 区段 mid —— 静态钉 i 的运行时等价,
      「动画中悬停 tooltip 取值用例」不再依赖真浏览器) + S13b 显式空值点对照(schema=2 洞位
      {t, dl:null, up:null}: _qbHoverOf 双 null 分支真执行, 空值点不出速率出缺口文案 + 真值点
      照常出速率对照 —— 该分支回退成 !p 时全电池仍绿的变异盲区封堵, 评审 T3-R2)。
    11. 尾锚显式视口(计划 26-11-22-0858 换代; 旧 F5 补尾格/_qbRollJudge/_qbPadTailColumns/
      方向B打断继承四层退役): 纯函数面 _qbAnchorJudge(锚 = max(st.anchor, tail) 单调 —— 旧窗
      响应晚到不回拖; 组距标称/名义窗长变化 或 锚位移 > 2 组距滚动域 -> rewin 瞬时; 恰边界
      slide 保持)+ _qbAnimAnchorAt(在途锚现值单点 —— 帧循环与打断续滑共用, 公式漂移即续滑回跳)
      + _qbRetainHistory(GET 落地历史保留合并)+ _qbTrimStaleHead 余量线(span+2 组距) + 调度器面
      S14(零位移打断续滑全链)/S15(真滚动打断 —— 单调锚到新尾)/S16(rewin 打断瞬时落地)/S17
      (单调锚不回拖)/S18(instant 档瞬时落地目标锚视口 —— 方向A恒定压缩变体随补点退役消失)/
      S19(建图拍底座: anchor/step/span 初值 + 建图初始视口播种)/S20b(余量列盲区封堵 —— 收敛帧
      显式重申行删除即红)/S20c(余量持峰 —— 收敛帧 y 成对钉行删除即红, 终态 y == 全列钉值)。
    接缝面(静态钉):
    a. 续拉快路逐字序(尾锚显式视口): 纯 setData 落袋三列原样 -> 同帧 _qbBeatStart(补点构造/
      继承捕获退役 —— 打断续滑由判定帧读自身在途锚, 锚不依赖列形状, 无捕获时序约束);
    b. 显式视口无条件落笔(判定帧 setScale("x", 锚视口) + y 成对钉档)与每帧锚平移
      (_qbAnimAnchorAt 单点)与收敛帧 setData + 显式视口重申的成对在位;
    c. x 轴右缘刻位过滤 + 标签逐帧现算(issue 26-11-17-0936 三次纠正): 模块级
      _qbDropRightEdgeSplits 建图后挂 axes[0].splits 丢掉 >= vMax-eps 的右缘刻位;
      tick freeze 整体退役, 收敛帧 u.redraw(false, true) 强制轴重算保留;
    d. reduce 短路判据读 AQB_FX_CFG 的 on 有效值(on=false 的 reduce 分量才短路, I7);
    e. _qbChartDestroy 先 _qbBeatCancel 再 u.destroy()(换肤/关抽屉终止在途动画不留半帧);
    f. 面板 beat 展示值复用 _qbBeatMs 单点(第二份 clamp 公式退场);
    g. BOM 纪律: rAF/performance.now/document.hidden 只出现在 mixin 方法域, 模块级头部零触碰
      (node 探针 eval 本文件的顶层约束);
    h. I3 反向钉: 调度器域零 destroy/new uPlot/零 loading 触碰(逐帧 commit 只走 setScale/redraw);
    i. tooltip 读数面接缝(I4): _qbHoverOf 读 Vue points(d.points[i]) 不读 u.data —— 与 L1 尾点
      插值写面(u.data 绘制面)零交集, 动画期 tooltip 与已落袋真值逐字一致。
    k. 尾锚显式视口反向钉(计划 26-11-22-0858): 剥注释后 _qbRollJudge/_qbPadTailColumns/
      _qbInheritedViewport/_qbBeatVpRem/_qbPad 全文件零残留(四层退役件不得旁路回潮)/ 判定帧
      _qbAnchorJudge 单点消费(meta 组距标称/名义窗长)+ st.anchor/step/span 记账 / 收敛帧显式
      视口重申(dropPad slice 退役) / rescale 显式视口重申 / 悬停索引直通(单列恒等 —— 补点扣减
      退役) / yMax 全列扫描 + _qbLoad 取数窗口分量(stale 判据双路 + w0 快照)+ 历史保留合并
      单点(_qbRetainHistory 调用)。"""
    shared = os.path.join(STATIC_ROOT, "shared")
    js = open(os.path.join(shared, "qb_traffic_chart.js"), encoding="utf-8").read()
    # —— 接缝静态钉 ——
    # a. 快路逐字序(F5; 变长点列适配 26-11-18-0037 阶段 3; 方向B打断继承 2026-11-22):
    #    补尾格判定单点(stepNom = meta 组距标称)-> 打断继承捕获(先于 setData —— setData 会
    #    把视口重置成含补点全宽 auto, 之后再读只剩全宽态; 读的是 prev.data[0] = 拍 A 显示列
    #    补点在内)-> setData 落袋 -> _qbPad 记账 -> 同帧起拍带第三参(既有 setData/_qbBeatStart
    #    相邻语义保持)
    assert re.search(r"prev\.setData\(\[data\.xs, data\.up, data\.dl\]\);\n\s*"
                     r"this\._qbBeatStart\(scope, prev\);", js), \
        "续拉快路必须纯 setData 三列原样落袋 -> 同帧 _qbBeatStart(尾锚显式视口: 补点构造/继承" \
        "捕获退役 —— 打断续滑由判定帧读自身在途锚, 无捕获时序约束)"
    # b. L0 成对: 判定帧摆回旧位 + 每帧 dx 归零 + 收敛帧 setData 交还 auto 后显式重申;
    #    y 钉成对(I4 纵轴瞬时定档): x 提交会让 uPlot 按偏置可视窗重推 y(vendor qn: Kl.x 非 null
    #    -> An(!0) -> y.auto 重算) —— 起拍/每个 shift 帧/收敛帧重申的 setScale("x") 必须成对补
    #    setScale("y", 全窗真值档位), 纯数值收敛帧(y 钉 + redraw)同样要盖; 钉值口径 = 建图
    #    range 单点(_qbYRange x _qbYCapOf), 不是显示尾值。
    #    F5 摆回锚在真窗口上(min = xs[pad] - dxMin0(显示列首点真值实距, 补点不计入真窗口),
    #    max = xs[n-1] - dxN —— 尾组推进拍 dx0=0 max 滑 si)
    start_blk = re.search(r"_qbBeatStart\(scope, u\) \{\n(.*?)\n    \},", js, re.S)
    assert start_blk, "qb_traffic_chart.js 缺 _qbBeatStart(判定帧开工单点)"
    assert 'u.setScale("x", { min: vAnchor - j.span, max: vAnchor });' in start_blk.group(1), \
        "判定帧必须无条件显式落笔锚视口(尾锚显式视口不变量(1): setData 的列全宽 auto 恒偏宽," \
        "显式视口是唯一真值 —— 含零变化早退拍/reduce 拍; vAnchor = 滑动起点或目标锚)"
    frame_blk = re.search(r"_qbBeatFrame\(scope\) \{\n(.*?)\n    \},", js, re.S)
    assert frame_blk, "qb_traffic_chart.js 缺 _qbBeatFrame(每帧推进单点)"
    assert 'u.setScale("x", { min: anchor - a.span, max: anchor });' in frame_blk.group(1) \
        and "const anchor = _qbAnimAnchorAt(a);" in frame_blk.group(1) \
        and "if (anchor !== a.lastAnchor)" in frame_blk.group(1), \
        "L0 每帧按真实毫秒推进: anchor = anchorFrom + easeOut(clock/shiftMs) x 位移(两缘同步" \
        "平移 —— 尾锚显式视口; 提交守卫单锚位; 在途锚单点 _qbAnimAnchorAt 与打断续滑共用)"
    # issue 26-11-17-0936 12:35 根因纠正 + 第五次取证上调阈值: 末帧 rem 极小令 x.min 落在
    # 刻度整数边界前一丁点, uPlot splits 首刻位低一格单帧回跳。帧循环必须把 rem 低于阈值的
    # 残差精确钳零, 且 dx/min/max 三个方向都用钳零后的 r 派生(只钳 dx 会让 min/max 仍带残差)。
    # 真机捕获 clock=425 rem=1.71e-4 越过旧阈值 1e-4 未钳零, 残差 0.011px 却令整条网格线跳
    # 一格 —— 阈值上调 1e-3 覆盖末段两帧(4.05e-4/1.71e-4)提前钳零, 几何偏差 <0.01px。
    fb2 = frame_blk.group(1)
    assert "const anchor = _qbAnimAnchorAt(a);" in fb2 \
        and "if (anchor !== a.lastAnchor)" in fb2, \
        "L0 末帧 ulp 吸附: 锚位须取自单点 _qbAnimAnchorAt(钳零在单点内, issue 26-11-17-0936 " \
        "口径承袭 —— 残差视口令 splits 首刻位单帧回跳)"
    vpfn = re.search(r"function _qbAnimAnchorAt\(a\) \{\n(.*?)\n\}", js, re.S)
    assert vpfn and "_qbFxEaseOut(a.clock / a.tl.shiftMs)" in vpfn.group(1) \
        and "a.anchorFrom + (a.anchorTo - a.anchorFrom) * e" in vpfn.group(1) \
        and "_QB_FX_L0_SNAP_REM" in vpfn.group(1), \
        "在途锚现值必须单点 _qbAnimAnchorAt(easeOut + 末帧 ulp 吸附钳在单点内 —— 帧循环与打断" \
        "续滑共用, 两处公式漂移即续滑回跳)"
    assert "const _QB_FX_L0_SNAP_REM = 1e-3;" in js, \
        "L0 末帧 ulp 吸附阈值常量 _QB_FX_L0_SNAP_REM 缺位或未按第五次取证上调到 1e-3" \
        "(1e-4 不足: 真机 rem=1.71e-4 帧未钳零令 splits 首刻位单帧换格)"
    for name, blk in (("_qbBeatStart", start_blk.group(1)), ("_qbBeatFrame", frame_blk.group(1))):
        assert 'u.setScale("y", { min: 0, max: yMax });' in blk or 'u.setScale("y", { min: 0, max: a.yMax });' in blk, \
            f"{name} 缺 y 钉成对(x 提交不配 y 钉 = 动画期纵轴按偏置可视窗重推, I4 纵轴瞬时定档被破)"
    sb, fb = start_blk.group(1), frame_blk.group(1)
    assert sb.index('u.setScale("x", { min: vAnchor - j.span') \
        < sb.index('u.setScale("y", { min: 0, max: yMax });'), \
        "_qbBeatStart 的 y 钉必须紧跟 x 显式视口(同一提交批, 缺 y = 该提交按可视窗重推 y)"
    assert fb.index('u.setScale("x", { min: anchor - a.span') \
        < fb.index('u.setScale("y", { min: 0, max: a.yMax });'), \
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
    assert "u.setData([u.data[0], u.data[1], u.data[2]]);" in conv_blk.group(1) \
        and 'u.setScale("x", { min: st.anchor - st.span, max: st.anchor });' in conv_blk.group(1), \
        "收敛帧必须 setData 真值写回 + 显式锚视口重申(尾锚显式视口: setData 的 resetScales 交还" \
        "列全宽 auto 恒偏宽非真值, 必须重申 [st.anchor - st.span, st.anchor] —— 旧 dropPad slice" \
        " 摘补点随单列恒等退役)"
    assert 'u.setScale("y", { min: 0, max: a.yMax });' in conv_blk.group(1) \
        and conv_blk.group(1).index('u.setScale("x", { min: st.anchor - st.span, max: st.anchor });') \
        < conv_blk.group(1).index('u.setScale("y", { min: 0, max: a.yMax });'), \
        "收敛帧必须成对钉 y(setData 后 x 重申的 pending 被 redraw(false,true) 消费时 vendor qn 按" \
        "锚窗可视数据重推 y —— 余量列持峰即纵轴泵动两次, 峰值滑出余量才止; 成对钉 a.yMax 终态与" \
        "判定帧全列钉值同尺, 行为面 = S20c 余量持峰用例)"
    # c. x 轴右缘刻位过滤 + 标签逐帧现算(issue 26-11-17-0936 第三次纠正): 模块级包装单点
    conv_body = conv_blk.group(1)
    #    建图后挂 axes[0].splits, 丢掉 >= vMax - eps 的右缘刻位; tick freeze 整体退役。
    assert "const _QB_X_SPLIT_EPS = (max) => Math.max(1e-9, Math.abs(max) * 1e-12);" in js, \
        "右缘刻位容差必须模块级单点 eps=max(1e-9, |vMax|×1e-12)"
    assert "function _qbDropRightEdgeSplits(generator) {" in js \
        and "return raw.filter((v) => v < max - eps);" in js, \
        "x 轴 splits 包装必须丢掉 >= vMax - eps 的右缘刻位(最右纵线每两拍进出根治)"
    assert "u.axes[0].splits = _qbDropRightEdgeSplits(u.axes[0].splits);" in js, \
        "建图后必须把包装挂到 x 轴 splits(uPlot 建图时已把默认 generator 规范化进 axes[0].splits)"
    assert "_qbTickFreeze" not in js, \
        "tick freeze 必须整体退役(只冻文字不冻刻位 -> 标签与纵线错相跳)"
    assert "{ ...axis, values: (u, splits) => splits.map((ts) => this._qbTickLabel(ts, scope)) }," in js, \
        "x 轴标签必须每帧从实时 splits 现算(不得缓存/冻结)"
    # issue 26-11-17-0936 二次纠正(保留): L0 末帧钳零后收敛帧 scale 与末帧逐位相同, uPlot
    # 不置轴重算脏标记 -> 本次轴值不刷新。收敛帧必须在 setData 之后强制 mt=true 重算一次。
    assert "u.redraw(false, true);" in conv_body \
        and conv_body.index("u.setData([u.data[0], u.data[1], u.data[2]]);") \
        < conv_body.index("u.redraw(false, true);"), \
        "收敛帧 setData 后必须 u.redraw(false, true) 强制重算 axes(scale 未变时 uPlot 不会" \
        "重算 _values, 轴值刷新慢一拍 = issue 26-11-17-0936 二次根因回潮)"
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
    #    必须先落真值 + 终止拍, 再 setData 重排(否则动画帧的 y 钉盖过新档位
    #    一拍、偏置视口与新档位错配一帧); x 重申 + y 成对钉在位(钉 b 同款成对形态 ——
    #    静态钉面: 列与锚窗同形时行为电池拦不住 y 钉行被删); 行为面 = 调度器电池 S11
    rescale_blk = re.search(r"_qbChartRescale\(scope\) \{\n(.*?)\n    \},", js, re.S)
    assert rescale_blk, "qb_traffic_chart.js 缺 _qbChartRescale(y 轴重排单点)"
    rb = rescale_blk.group(1)
    assert "st.anim" in rb and "_qbBeatCancel(" in rb, \
        "_qbChartRescale 必须收口在途拍(落真值 + _qbBeatCancel), 再 setData 重排"
    assert rb.index("_qbBeatCancel(") < rb.index("u.setData([u.data[0], u.data[1], u.data[2]]);"), \
        "_qbChartRescale 必须先终止在途拍再 setData(重排不改数据, 终止即落真值不留半帧)"
    assert 'u.setScale("x", { min: stR.anchor - stR.span, max: stR.anchor });' in rb \
        and rb.index("u.setData([u.data[0], u.data[1], u.data[2]]);") \
        < rb.index('u.setScale("x", { min: stR.anchor - stR.span'), \
        "rescale 的 setData 交还列全宽 auto 后必须重申显式锚视口(尾锚显式视口不变量(1); 旧" \
        " dropPad slice/_qbPad 归零随单列恒等退役)"
    assert 'u.setScale("y", { min: 0, max: yMax });' in rb \
        and rb.index('u.setScale("x", { min: stR.anchor - stR.span') \
        < rb.index('u.setScale("y", { min: 0, max: yMax });') \
        and "const yMax = _qbYRange(dmax, this._qbYCapOf(scope))[1];" in rb, \
        "rescale 的 y 钉必须紧跟 x 重申成对(setData 后 x 重申的 pending 被消费时 vendor qn 按" \
        "锚窗可视数据重推 y —— 余量列持峰即两把尺; 重排的动机就是换档位, 按新 cap 全列重算" \
        " yMax 与判定帧基准同尺, 终态不成对钉即回退旧档一拍)"
    # k. 尾锚显式视口反向钉(计划 26-11-22-0858): 四层退役件剥注释后全文件零残留(不得旁路
    #    回潮) + 判定帧 _qbAnchorJudge 单点消费 + st.anchor/step/span 记账 + 悬停索引直通
    #    (单列恒等)+ yMax 全列扫描 + _qbLoad 取数窗口分量 + 历史保留合并单点。
    js_code = re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", js, flags=re.S))
    assert "_qbRollJudge" not in js_code and "_qbPadTailColumns" not in js_code \
        and "_qbInheritedViewport" not in js_code and "_qbBeatVpRem" not in js_code, \
        "尾锚显式视口退役件(_qbRollJudge/_qbPadTailColumns/_qbInheritedViewport/_qbBeatVpRem)" \
        "剥注释后全文件零残留(回潮即绕过三不变量)"
    assert "_qbPad" not in js_code, \
        "补点记账 u._qbPad 剥注释后零残留(单列恒等: store 列 == 显示列, 补点面不得回潮)"
    assert "const j = _qbAnchorJudge(st, xs[n - 1]," in start_blk.group(1) \
        and "st.anchor = j.anchor;" in start_blk.group(1) \
        and "st.step = j.step;" in start_blk.group(1) and "st.span = j.span;" in start_blk.group(1), \
        "判定帧必须走 _qbAnchorJudge 单点(meta 组距标称/名义窗长入参)+ st.anchor/step/span " \
        "跨拍记账(单调锚与换档判据的单点消费面)"
    assert "this[def.hoverIdx] = idx;" in js \
        and "idx - (u._qbPad" not in js_code, \
        "悬停索引必须直通(单列恒等: store 列 == 显示列, 补点扣减面随补点退役)"
    assert "for (let i = 0; i < n; i++)" in start_blk.group(1), \
        "yMax 扫描必须全列(单列恒等: 列即真值, 无补点格跳过面)"
    assert "const anchorPrev = anchorHold != null ? anchorHold : anchorTo - j.delta;" in start_blk.group(1) \
        and "const disp = anchorTo - anchorPrev;" in start_blk.group(1), \
        "判定帧视口锚三态必须经 anchorPrev/disp 单点(打断续滑 anchorHold 与上一收敛锚统一" \
        " —— 全新位移拍与打断续滑拍同路, 旧 roll 伪真继承特判退役)"
    # 取数窗口分量钉(不变量(3))在 test_frontend_qb_traffic_chart_wiring(_qbLoad 块在该电池钉)。
    assert "_qbRetainHistory(oldPoints, d.points, keepLine)" in js \
        and "const oldPoints = this[def.data] && Array.isArray(this[def.data].points)" in js, \
        "GET 落地必须走历史保留合并单点(旧列快照先于整列替换捕获 —— 余量列回填, G-B 防回潮)"
    # —— 行为面 node 电池(纯函数面 + 调度器行为面各一发) ——
    node = shutil.which("node")
    if not node:
        return
    for probe, tag in ((_NODE_QB_BEAT_PROBE, "节拍内核"), (_NODE_QB_BEAT_SCHED_PROBE, "节拍调度器")):
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
