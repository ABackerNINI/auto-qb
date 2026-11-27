"""test_webui_static_dom_panel_traffic_fx_scan 测试计划: webui 前端静态守阵: 详情面板 / 弹窗 / 浮层

原 test_webui_static_dom_panel_traffic.py 按域拆分(move-only, 2026-11-27); 测试 ID/名称/断言零变化。

## 测试计划(每个测试函数一条)
- test_frontend_qb_fx_scan_band_battery: T6 综合表现层 S2-b 电池 + 接缝静态钉(S2-b, plan 26-11-12-1139 §03 T4/T6 行/R6 节/D17-D19, §02 R5/R6/R7) —— node 电池真跑(同视觉引擎范式): R6 确定性伪随机(_qbFxHash01 同(拍,槽)恒同且恒 [0,1)/分布 45/35/20 ±0.05 —— plan §04 原型带符号 >> 版本实测 90% 落 [0,0.5) 色池失真, 生产改 Math.imul+>>> 雪崩, 分布断言守)/strat 分层采样恒 [0,1) 且第 i 条只在第 i 层内不聚集/tearRnd 三档(fixed 恒 0.5/random 连续调用不恒同/linked=hash01)/撕裂切片(2/3/5 按等级且 ≤5/长 10-80 随 Δ/alpha 线性式 (0.10+0.08×lv)×q×impact —— q/impact 由绘制侧逐帧乘, 表常量退役 C2/y 在撕裂带 ±(0.08+0.30×min(1,Δ/0.5))×H 内且钳绘图区/同参数恒同/fixed 跨拍序号同形/linked 跨拍序号异形)+ 梳齿(3/5/7 按等级/长 4-24 随 Δ/带内/fixed 等距恒长) + 回声数学(D19/R7: span=clamp(0.22×绘图宽,100,200) 且不超绘图宽/full 恢复整幅 s=w —— A2 回退, 模板 demo:1152-1158 对照档口径/100-150-200 直取; fall=pow(1−d/span,0.85) 且 d≥span 恒 0 几何硬停/单调不增; echoQ 0.18-0.45beat 匀速且 q=1 即到点) + 束包络 stops(双峰分立/贴近 <0.08 合并单峰/钳 [0.02,0.98]/NaN 退 0.5) + T5 联动单点(lvColor: grade 关恒 Lv.1, 开随等级, 非法等级退 Lv.3; beamWScale 已退役 A2 —— 六层晕恒 hw[0], 行为面 S9) + 束体指令计数(_qbDrawFxScan 记账 ctx: 逐帧扫 t=0..beat 步 30 ≤23 且 Lv.3 色散+回声双开窗恰 23/回声窗止 450ms 恰 21/色散窗止 500ms 恰 19/束 fade 窗 0.7×beat(B2 模板保真二轮 —— 550-690ms 恰 19, 700ms 起零)/palette=calm 0/layers.scan=false 0/impact=0 0; 相位 A 行程: x0 从判定线+1.2 格 easeOut 单调收敛、0.12beat(冲击窗)内抵达; 除回声外全部竖笔 x ≥ 判定线不横穿数据、回声 x ≥ 判定线−200(I9-R7 探针); 回声 1px 核 alpha ≤0.20 不变 + 9px 晕 0.34×fall(B4 模板保真二轮, 旧 0.20 晕上限退役)且 d=span 帧零回声指令而束体仍在)+ T2 光带(_qbDrawFx 记账 ctx: layers.band=true 双轨各一道渐变 stroke 于末点 x/shown=prev 零长不落笔/band=false 零渐变笔/bandHalo 仅 lead 一道 blur 描边 —— 同帧 blur stroke = 环外圈 2 + 光带 1 = 3 ≤ 5(I9 辉光预算修订 ≤5: 曲线辉光 2 预留 S3, S2 实测 3)/非零 blur 赋值点 ≤2/帧末 shadowBlur 恒清零)+ 横向线条(C2 门 glitch 下切片 5 条 2px 级且 x<右缘、束体+切片 5+23=28 合计(观测帧 t=210 = 切片窗 0.25×beat 与回声窗双开)、横向细线 5+7=12)+ 微震让位(_drawerAnimRaf 非零时切片零落笔, 归零恢复 —— §09)+ T5 grade=false 全域(描边/填充/渐变 stop/阴影色)无 Lv.3 色 + 冲击闪光白名单(S10, C4/D7: t<impactMs 判定线全高 lw2 alpha 0.75×(1−t/impactMs)×impact 恰 1 笔/窗外零笔/neon=false 仍在/calm 档亦显/impact=0 零笔 —— I9 装饰指令修订注记 +1 stroke 仅 impact 窗内, 几何面由视觉引擎电池 G13 ops 钉); 静态钉: 层开关接线点(cfg.layers.band/scan/grade 字面量 + _qbDrawFx 调用 _qbDrawFxScan 行在位)/束体绘制域(_qbDrawFxScan)剥注释后 fillRect 恰 1 处且为梳齿 1px 级、光带块零 fillRect/I3 反向钉扩 scan 域(零 destroy/new uPlot/loading)/切片微震让位门(!this._drawerAnimRaf 在切片条件内)/_qbFxLvColor(fx.lv, cfg.layers.grade === true) 恰 3 处(fx/锚/束)/束体常量行逐字(六层晕表/强度 0.78/条数表/回声八常量含 _QB_FX_ECHO_HALO_ALPHA=0.34; 束宽度感表与切片 alpha 表退役缺残留断言 —— A2/C2)。无 node 静默跳过(同 _NODE_QB_TRAFFIC_PROBE 口径)
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

# T6 综合表现层 S2-b 纯函数面 node 电池: R6 确定性伪随机/分层采样/撕裂切片/梳齿清单 +
# 回声行程数学(D19) + 束包络分档 + T5 联动单点。无 node 静默跳过(同 _NODE_QB_TRAFFIC_PROBE 口径)。
_NODE_QB_FXVIS_SCAN_PROBE = r"""
const fs = require("fs");
global.window = {};
const src = fs.readFileSync(process.argv[1], "utf8");
const {
  _QB_FX_TEAR_COUNT, _QB_FX_COMB_COUNT, _QB_FX_TEAR_MAGENTA,
  _QB_FX_BEAM_HALO, _QB_FX_BEAM_INTENSITY, _QB_FX_DISPERSION,
  _QB_FX_BAND_ALPHA, _QB_FX_BAND_WIDTH, _QB_FX_BAND_HALO_ALPHA,
  _QB_FX_ECHO_SPAN_RATIO, _QB_FX_ECHO_SPAN_MIN, _QB_FX_ECHO_SPAN_MAX,
  _QB_FX_ECHO_PHASE_LO, _QB_FX_ECHO_PHASE_HI, _QB_FX_ECHO_FADE_POW, _QB_FX_ECHO_ALPHA_CAP,
  _QB_FX_SLICES_MAX, _QB_FX_LV_COLORS,
  _qbFxHash01, _qbFxStrat, _qbFxTearRnd, _qbFxLvColor, _qbFxFade,
  _qbFxEchoSpan, _qbFxEchoFall, _qbFxEchoQ, _qbFxBeamStops, _qbFxTearSlices, _qbFxComb,
} = new Function(src + "\nreturn { _QB_FX_TEAR_COUNT, _QB_FX_COMB_COUNT,"
  + " _QB_FX_TEAR_MAGENTA, _QB_FX_BEAM_HALO, _QB_FX_BEAM_INTENSITY,"
  + " _QB_FX_DISPERSION, _QB_FX_BAND_ALPHA, _QB_FX_BAND_WIDTH, _QB_FX_BAND_HALO_ALPHA,"
  + " _QB_FX_ECHO_SPAN_RATIO, _QB_FX_ECHO_SPAN_MIN, _QB_FX_ECHO_SPAN_MAX, _QB_FX_ECHO_PHASE_LO,"
  + " _QB_FX_ECHO_PHASE_HI, _QB_FX_ECHO_FADE_POW, _QB_FX_ECHO_ALPHA_CAP, _QB_FX_SLICES_MAX,"
  + " _QB_FX_LV_COLORS, _qbFxHash01, _qbFxStrat, _qbFxTearRnd, _qbFxLvColor,"
  + " _qbFxFade, _qbFxEchoSpan, _qbFxEchoFall, _qbFxEchoQ, _qbFxBeamStops, _qbFxTearSlices,"
  + " _qbFxComb };")();
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);
// —— A. 常量单点(R6/T4/T2/D19) ——
ok("R6 条数表: 切片 2/3/5(<=5) / 梳齿 3/5/7, 横向细线条合计上限 5+7=12(I9-R6)",
  _QB_FX_TEAR_COUNT[1] === 2 && _QB_FX_TEAR_COUNT[2] === 3 && _QB_FX_TEAR_COUNT[3] === 5
  && _QB_FX_TEAR_COUNT[3] <= _QB_FX_SLICES_MAX
  && _QB_FX_COMB_COUNT[1] === 3 && _QB_FX_COMB_COUNT[2] === 5 && _QB_FX_COMB_COUNT[3] === 7
  && _QB_FX_TEAR_COUNT[3] + _QB_FX_COMB_COUNT[3] === 12);
ok("T4 六层晕表: 34/24/16/10/5/2.5 px 宽->窄递进, alpha 0.035..0.38", (() => {
  const w = _QB_FX_BEAM_HALO.map((h) => h[0]);
  return w.length === 6 && w.every((x, i) => i === 0 || w[i - 1] > x)
    && JSON.stringify(_QB_FX_BEAM_HALO) === JSON.stringify([[34, 0.035], [24, 0.05], [16, 0.08], [10, 0.13], [5, 0.22], [2.5, 0.38]]);
})());
ok("T4 束强度 0.78(T6) + 色散色 青/品红 ±1.6px 用色(束宽度感分级已退役 —— 模板无宽度感系数, A2)",
  _QB_FX_BEAM_INTENSITY === 0.78
  && _QB_FX_DISPERSION[0] === "#5CF2E8" && _QB_FX_DISPERSION[1] === "#FF4D9D"
  && _QB_FX_TEAR_MAGENTA === "#FF4D9D");
ok("D19 回声七常量: span 比 0.22 / 界 [100,200] / 相位窗 [0.18,0.45] / 衰减幂 0.85 / alpha 上限 0.20",
  _QB_FX_ECHO_SPAN_RATIO === 0.22 && _QB_FX_ECHO_SPAN_MIN === 100 && _QB_FX_ECHO_SPAN_MAX === 200
  && _QB_FX_ECHO_PHASE_LO === 0.18 && _QB_FX_ECHO_PHASE_HI === 0.45
  && _QB_FX_ECHO_FADE_POW === 0.85 && _QB_FX_ECHO_ALPHA_CAP === 0.2);
ok("T2 光带常量: alpha 基数 0.7 / 描边宽 4px / bandHalo 辉光基数 0.5",
  _QB_FX_BAND_ALPHA === 0.7 && _QB_FX_BAND_WIDTH === 4 && _QB_FX_BAND_HALO_ALPHA === 0.5);
// —— B. hash01 确定性 + 均匀分布(R6/D18; 45/35/20 色池配比依赖它) ——
ok("hash01 同(拍,槽)恒同值(可复现可断言), 恒落 [0,1)",
  _qbFxHash01(42, 7) === _qbFxHash01(42, 7) && _qbFxHash01(0, 0) >= 0 && _qbFxHash01(0, 0) < 1
  && (() => { for (let a = -5; a < 3000; a += 97) { const v = _qbFxHash01(a, 3); if (!(v >= 0 && v < 1)) return false; } return true; })());
ok("hash01 分布 45/35/20 ±0.05(色池配比; 原型带符号 >> 版本 90% 落 [0,0.5) 失真, 生产式守)", (() => {
  let c = [0, 0, 0], n = 0;
  for (let bi = 0; bi < 3000; bi++) {
    for (let s = 0; s < 16; s++) {
      const r = _qbFxHash01(bi, s);
      n++;
      if (r < 0.45) c[0]++; else if (r < 0.8) c[1]++; else c[2]++;
    }
  }
  const p = c.map((x) => x / n);
  return Math.abs(p[0] - 0.45) <= 0.05 && Math.abs(p[1] - 0.35) <= 0.05 && Math.abs(p[2] - 0.20) <= 0.05;
})());
// —— C. 分层采样(R6) ——
ok("strat 恒 [0,1) 且第 i 条只落第 i 层内(不聚集不越界)", (() => {
  for (let n = 1; n <= 7; n++) {
    for (let i = 0; i < n; i++) {
      for (const r of [0, 0.31, 0.5, 0.77, 0.999]) {
        const v = _qbFxStrat(i, n, r);
        if (!(v >= i / n && v < (i + 1) / n && v >= 0 && v < 1)) return false;
      }
    }
  }
  return true;
})());
// —— D. tearRnd 三档(R6/D18 对照档) ——
ok("tearRnd: fixed 恒 0.5(旧常量几何对照) / linked = hash01(bi, slot) / random 连续调用不恒同(不可复现对照)",
  _qbFxTearRnd("fixed", 1, 2) === 0.5 && _qbFxTearRnd("fixed", 99, 2) === 0.5
  && _qbFxTearRnd("linked", 42, 7) === _qbFxHash01(42, 7)
  && (() => {
    const seen = new Set();
    for (let i = 0; i < 20; i++) seen.add(_qbFxTearRnd("random", 1, 1));
    return seen.size > 1;
  })());
// —— E. 撕裂切片清单(R6) ——
const sliceCount = (lv) => _qbFxTearSlices(lv, 200, 100, 0.5, 7, "linked", 10, 310).length;
ok("切片 2/3/5 按 lead 等级(Lv.1 2 / Lv.2 3 / Lv.3 5)",
  sliceCount(1) === 2 && sliceCount(2) === 3 && sliceCount(3) === 5);
ok("切片长 10-80 随 Δ(pow=0 -> 10; pow=1 -> 10+70x(0.45..1) <= 80)",
  _qbFxTearSlices(3, 200, 100, 0, 7, "linked", 10, 310).every((s) => s.len === 10)
  && _qbFxTearSlices(3, 200, 100, 1, 7, "linked", 10, 310).every((s) => s.len >= 10 && s.len <= 80));
ok("切片 alpha 线性式 0.10+0.08xlv(C2: 0.18/0.26/0.34 同值不同源 —— q/impact 由绘制侧逐帧乘, 冻结清单不含逐帧因子)",
  _qbFxTearSlices(1, 200, 100, 0.5, 7, "linked", 10, 310).every((s) => Math.abs(s.alpha - (0.10 + 0.08 * 1)) <= 1e-12)
  && _qbFxTearSlices(2, 200, 100, 0.5, 7, "linked", 10, 310).every((s) => Math.abs(s.alpha - (0.10 + 0.08 * 2)) <= 1e-12)
  && _qbFxTearSlices(3, 200, 100, 0.5, 7, "linked", 10, 310).every((s) => Math.abs(s.alpha - (0.10 + 0.08 * 3)) <= 1e-12));
ok("切片 y 在撕裂带 [yC-半带, yC+半带] 内且钳绘图区 [T+2, B-3]", (() => {
  const yC = 200, half = 100, T = 10, B = 310;
  const out = _qbFxTearSlices(3, yC, half, 0.5, 7, "linked", T, B);
  return out.every((s) => s.y >= Math.max(T + 2, yC - half - 1e-9) && s.y <= Math.min(B - 3, yC + half + 1e-9));
})());
ok("切片带越界钳边: 半带 1000(超出绘图区)时 y 恒钳 [T+2, B-3]",
  _qbFxTearSlices(3, 200, 1000, 1, 7, "linked", 10, 310).every((s) => s.y >= 12 && s.y <= 307));
ok("切片右端缩进 0-18px(fixed 恒 0 齐平 —— R5 旧观感), ci ∈ {0,1,2}",
  _qbFxTearSlices(3, 200, 100, 0.5, 7, "linked", 10, 310).every((s) => s.inset >= 0 && s.inset < 18)
  && _qbFxTearSlices(3, 200, 100, 0.5, 7, "fixed", 10, 310).every((s) => s.inset === 0)
  && _qbFxTearSlices(3, 200, 100, 0.5, 7, "linked", 10, 310).every((s) => s.ci >= 0 && s.ci <= 2));
ok("切片同参数恒同(拍内冻结可复现) / fixed 跨拍同形(旧常量几何对照) / linked 跨拍异形(每拍不重复)",
  JSON.stringify(_qbFxTearSlices(3, 200, 100, 0.5, 7, "linked", 10, 310))
    === JSON.stringify(_qbFxTearSlices(3, 200, 100, 0.5, 7, "linked", 10, 310))
  && JSON.stringify(_qbFxTearSlices(3, 200, 100, 0.5, 1, "fixed", 10, 310))
    === JSON.stringify(_qbFxTearSlices(3, 200, 100, 0.5, 999, "fixed", 10, 310))
  && JSON.stringify(_qbFxTearSlices(3, 200, 100, 0.5, 1, "linked", 10, 310))
    !== JSON.stringify(_qbFxTearSlices(3, 200, 100, 0.5, 999, "linked", 10, 310)));
// —— F. 梳齿清单(R6; y 输出侧钳 [tTop+2, tBot-3] —— 评审 minor5) ——
ok("梳齿 3/5/7 条按等级, 长 4-24 随 Δ, y 在包络带内且钳绘图区 [T+2, B-3]",
  _qbFxComb(3, 100, 260, 0.5, 7, "linked", 10, 310).length === 3
  && _qbFxComb(5, 100, 260, 0.5, 7, "linked", 10, 310).length === 5
  && _qbFxComb(7, 100, 260, 0.5, 7, "linked", 10, 310).length === 7
  && _qbFxComb(7, 100, 260, 0, 7, "linked", 10, 310).every((c) => c.len >= 4 && c.len < 12)
  && _qbFxComb(7, 100, 260, 1, 7, "linked", 10, 310).every((c) => c.len >= 4 && c.len <= 24)
  && _qbFxComb(7, 100, 260, 0.5, 7, "linked", 10, 310).every((c) => c.y >= 100 && c.y <= 260 && c.dx >= 0 && c.dx <= 3)
  && _qbFxComb(7, 100, 260, 0.5, 7, "linked", 10, 310).every((c) => c.y >= 12 && c.y <= 307));
ok("梳齿越界钳边: 带 [-50, 400](越出绘图区)时 y 恒钳 [T+2, B-3](越界齿零墨回潮即红 —— 评审 minor5)",
  _qbFxComb(7, -50, 400, 1, 7, "linked", 10, 310).every((c) => c.y >= 12 && c.y <= 307));
ok("梳齿 fixed 档等距恒长(strat(c,n,0.5)) + 同参数恒同",
  (() => {
    const f = _qbFxComb(5, 100, 260, 0.5, 7, "fixed", 10, 310);
    const f2 = _qbFxComb(5, 100, 260, 0.5, 99, "fixed", 10, 310);
    return JSON.stringify(f) === JSON.stringify(f2)
      && f.every((c, i) => Math.abs(c.y - (100 + (260 - 100) * ((i + 0.5) / 5))) <= 1e-9);
  })());
// —— E+. 撕裂切片逐条公式紧断言(评审 minor4: 双端对称钉死 —— 分层采样/槽位/半带宽使用变异即红) ——
ok("切片 y 逐条 = yC + (strat(i,n,hash01(bi,slot))-0.5) x 2 x halfBand(首末双端对称, 全带内无钳)",
  (() => {
    const yC = 200, half = 100, bi = 7, tTop = 10, tBot = 310;
    const out = _qbFxTearSlices(3, yC, half, 0.5, bi, "linked", tTop, tBot);
    const n = 5;
    for (let i = 0; i < n; i++) {
      const exp = yC + (_qbFxStrat(i, n, _qbFxHash01(bi, i * 13 + 3)) - 0.5) * 2 * half;
      if (Math.abs(out[i].y - exp) > 1e-9) return false;
      if (!(out[i].y >= tTop + 2 && out[i].y <= tBot - 3)) return false;
    }
    return Math.abs(out[0].y - (yC + (_qbFxStrat(0, n, _qbFxHash01(bi, 3)) - 0.5) * 2 * half)) <= 1e-9
      && Math.abs(out[n - 1].y - (yC + (_qbFxStrat(n - 1, n, _qbFxHash01(bi, (n - 1) * 13 + 3)) - 0.5) * 2 * half)) <= 1e-9;
  })());
// —— G. 回声行程数学(D19/R7) ——
ok("echoSpan: auto = clamp(0.22x宽,100,200) — 800 宽 176 / 400 宽抬到 100 / 1000 宽钳 200",
  _qbFxEchoSpan("auto", 800) === 176 && _qbFxEchoSpan("auto", 400) === 100 && _qbFxEchoSpan("auto", 1000) === 200);
ok("echoSpan: 100/150/200 直取 + full 恢复整幅 s=w(A2 回退 —— 模板 demo:1152-1158 对照档口径) + 不超绘图宽",
  _qbFxEchoSpan("150", 800) === 150 && _qbFxEchoSpan("200", 300) === 200
  && _qbFxEchoSpan("full", 800) === 800 && _qbFxEchoSpan("full", 80) === 80
  && _qbFxEchoSpan("auto", 80) === 80 && _qbFxEchoSpan("auto", 0) === 100 && _qbFxEchoSpan("auto", NaN) === 100);
ok("echoFall: d=0 -> 1 / pow 衰减 / d>=span 恒 0(几何硬停, 含恰等) / 负 d 钳 0(不反放大) / 单调不增 / 非法 span 0",
  _qbFxEchoFall(0, 176) === 1 && Math.abs(_qbFxEchoFall(88, 176) - Math.pow(0.5, 0.85)) <= 1e-12
  && _qbFxEchoFall(176, 176) === 0 && _qbFxEchoFall(177, 176) === 0 && _qbFxEchoFall(-1, 176) === 1
  && _qbFxEchoFall(10, 0) === 0 && _qbFxEchoFall(NaN, 176) === 0
  && (() => {
    let prev = Infinity;
    for (let d = 0; d <= 176.001; d += 4) {
      const v = _qbFxEchoFall(d, 176);
      if (v > prev + 1e-12) return false;
      prev = v;
    }
    return true;
  })());
ok("echoQ: 0.18beat 前恒 0 / 窗内匀速(等时等距) / 0.45beat 起恒 1(到点)",
  _qbFxEchoQ(0, 1000) === 0 && _qbFxEchoQ(179, 1000) === 0 && _qbFxEchoQ(180, 1000) === 0
  && Math.abs(_qbFxEchoQ(315, 1000) - 0.5) <= 1e-12 && _qbFxEchoQ(450, 1000) === 1 && _qbFxEchoQ(500, 1000) === 1
  && (() => {
    const q1 = _qbFxEchoQ(200, 1000) - _qbFxEchoQ(180, 1000);
    const q2 = _qbFxEchoQ(420, 1000) - _qbFxEchoQ(400, 1000);
    return Math.abs(q1 - q2) <= 1e-12;
  })());
// —— H. 束包络分档(R5) ——
ok("beamStops: 双峰分立(0.2/0.8 各 a=1, 端点 0.07 底噪, 升序)",
  (() => {
    const s = _qbFxBeamStops(0.2, 0.8);
    return s.length === 4 && s[0].p === 0 && s[0].a === 0.07 && s[3].p === 1 && s[3].a === 0.07
      && Math.abs(s[1].p - 0.2) <= 1e-12 && s[1].a === 1 && Math.abs(s[2].p - 0.8) <= 1e-12 && s[2].a === 1;
  })());
ok("beamStops: 两峰贴近(<0.08)合并单峰 / 输入钳 [0.02,0.98] / NaN 退 0.5",
  (() => {
    const m = _qbFxBeamStops(0.5, 0.53);
    const cl = _qbFxBeamStops(-1, 2);
    const nan = _qbFxBeamStops(NaN, NaN);
    return m.length === 3 && Math.abs(m[1].p - 0.515) <= 1e-12 && m[1].a === 1
      && cl[1].p === 0.02 && cl[2].p === 0.98 && nan[1].p === 0.5;
  })());
// —— I. T5 联动单点(grade 收口; 束宽度感联动已退役 A2 —— 色相联动保留) ——
ok("lvColor: grade 开随等级 / grade 关恒 Lv.1(§04 lvColor 语义) / 非法等级退 Lv.3",
  _qbFxLvColor(3, true) === "#FF6BD6" && _qbFxLvColor(1, true) === "#7AD9FF"
  && _qbFxLvColor(3, false) === "#7AD9FF" && _qbFxLvColor(3, undefined) === "#7AD9FF"
  && _qbFxLvColor(9, true) === "#FF6BD6");
// —— J. fade 助手 ——
ok("fade: hex -> rgba 串 / a 钳 [0,1] / 非 hex 原样返回(语义令牌兜底不炸)",
  _qbFxFade("#7AD9FF", 0.5) === "rgba(122,217,255,0.500)"
  && _qbFxFade("#7AD9FF", 2) === "rgba(122,217,255,1.000)" && _qbFxFade("#7AD9FF", -1) === "rgba(122,217,255,0.000)"
  && _qbFxFade("rgb(1,2,3)", 0.5) === "rgb(1,2,3)");
ok("Lv 色表沿用 S2-a 常量(联动色相同源)",
  _QB_FX_LV_COLORS[1] === "#7AD9FF" && _QB_FX_LV_COLORS[2] === "#FEFFA9" && _QB_FX_LV_COLORS[3] === "#FF6BD6");
console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
"""

# T6 综合表现层 S2-b 绘制面 node 电池: 真 mixin 方法 + 记账式 2d ctx 桩直接调 _qbDrawFxScan
# /_qbDrawFx —— 束体指令计数(I9-R5/R6 电池级证据)/相位 A 行程/回声硬停与 alpha 上限/横向线条
# 合计/切片域计数/T2 光带双轨/bandHalo 辉光预算/微震让位/T5 grade 全域色断言。
# 无 node 静默跳过(同 _NODE_QB_TRAFFIC_PROBE 口径)。
_NODE_QB_FXVIS_SCAN_DRAW_PROBE = r"""
const fs = require("fs");
global.window = {};
const src = fs.readFileSync(process.argv[1], "utf8");
const { methods, _qbFxTearSlices, _qbFxComb } =
  new Function(src + "\nreturn { methods: window.AQB_QB_TRAFFIC.methods,"
  + " _qbFxTearSlices, _qbFxComb };")();
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);
/* 记账式 2d ctx(stroke 记逐笔元数据: 首笔 x/alpha/宽/blur/渐变 stop/渐变构造坐标; fillRect 记
 * 样式与 alpha; rect/clip 记实参 —— 评审 major: 束体 clip 域断言的观测面; canvas 宽 900 =
 * 绘图区右缘 860 + 判定线右侧留白 40px —— 束体宽 clip 可见域)。 */
function mkCtx() {
  const ctx = {
    strokes: [], fillRects: [], fillTexts: [], ops: [], grads: [],
    rects: [], clips: [],
    strokesWhileBlur: 0, fillCnt: 0, blurSets: [],
    _blur: 0, shadowColor: "", globalAlpha: 1,
    strokeStyle: "", fillStyle: "", lineWidth: 1, font: "", textAlign: "", textBaseline: "",
    canvas: { width: 900 },
    beginPath() {}, closePath() {}, arc() {},
    rect(x, y, w, h) { this.rects.push([x, y, w, h]); },
    clip() { this.clips.push(this.rects[this.rects.length - 1] || null); },
    scale() {}, save() {}, restore() {}, setLineDash() {},
    moveTo(x, y) { this.ops.push([x, y, "M"]); },
    lineTo(x, y) { this.ops.push([x, y, "L"]); },
    stroke() {
      this.strokes.push({ x: this.ops.length ? this.ops[0][0] : NaN,
        alpha: this.globalAlpha, w: this.lineWidth, blur: this._blur,
        style: this.strokeStyle, stops: this.strokeStyle && this.strokeStyle.stops ? this.strokeStyle.stops : null,
        gcoords: this.strokeStyle && this.strokeStyle.coords ? this.strokeStyle.coords : null });
      this.ops.length = 0;
      if (this._blur > 0) this.strokesWhileBlur++;
    },
    fill() { this.fillCnt++; },
    fillRect(x, y, w, h) { this.fillRects.push([x, y, w, h, this.fillStyle, this.globalAlpha]); },
    fillText(s) { this.fillTexts.push({ s: String(s), style: this.fillStyle }); },
    createLinearGradient(x0, y0, x1, y1) {
      const g = { coords: [x0, y0, x1, y1], stops: [],
        addColorStop(p, c) { g.stops.push([p, String(c)]); } };
      this.grads.push(g);
      return g;
    },
  };
  Object.defineProperty(ctx, "shadowBlur", {
    get() { return ctx._blur; },
    set(v) { ctx._blur = v; ctx.blurSets.push(v); },
    configurable: true,
  });
  return ctx;
}
const instr = (ctx) => ctx.strokes.length + ctx.fillRects.length + ctx.fillCnt;
const YMAX = 63;
const yOfT = (v) => 10 + 300 * (1 - Math.min(v, YMAX) / YMAX);
const XS = [1030, 1060, 1090, 1120, 1150];
const R = 860, T = 10, B = 310, W = 800;
const PX_PER_T = W / (XS[4] - XS[0]);   // 800/120 -> cellPx = 30x800/120 = 200
const LIVE_UP_M = { prev: 10, target: 30, shown: 20, delta: 2, level: 3, live: true };
const LIVE_DL_M = { prev: 55, target: 60, shown: 58, delta: 0.09, level: 2, live: true };
const STILL_UP = { prev: 10, target: 30, shown: 10, delta: 2, level: 3, live: true };
const STILL_DL = { prev: 55, target: 60, shown: 55, delta: 0.09, level: 2, live: true };
/* 语义色用 hex 桩(console 皮肤同源 --indigo/--teal)—— fade 助手只对 #RRGGBB 施 alpha */
const TK = { up: "#8B93F8", down: "#2FD4BF", grid: "#GRID", gap: "#GAP", axis: "#AXIS" };
const CFG = { enabled: true, on: true, shiftRatio: 0.6, neon: true, particles: 1, tail: false,
  dual: "both", palette: "neon", impact: 0.7, echoSpan: "auto", tear: "linked",
  layers: { band: true, particles: true, scan: true, grade: true } };
global.window.AQB_FX_CFG = CFG;
const COMB = _qbFxComb(7, 2, 320, 0.5, 7, "linked", T, B);   // 带越出绘图区 -> 钳边真实生效(评审 minor5 的夹具面)
const SLICES = _qbFxTearSlices(3, yOfT(10), 40, 0.5, 7, "linked", T, B);
const CFG_NO_SCAN = Object.assign({}, CFG, { layers: Object.assign({}, CFG.layers, { scan: false }) });
function mkU(upT, dlT) {
  const u = {
    root: { isConnected: true },
    data: [XS, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]],
    scales: { x: { min: XS[0], max: XS[4] }, y: { min: 0, max: YMAX } },
    bbox: { left: 60, top: T, width: W, height: 300 },
    valToPos(v, k) {
      const s = this.scales[k];
      return k === "x" ? ((v - s.min) / (s.max - s.min)) * W : (1 - (v - s.min) / (s.max - s.min)) * 300;
    },
  };
  u._qbBeat = { raf: 0, anim: null, xs0: XS[0], n: 5, tracks: { up: upT, dl: dlT } };
  u._qbBeat.anim = { dx0: 0, needsShift: false, needsTail: false, n: 5,
    tl: { beat: 1000, impactMs: 120, shiftMs: 600, convergeMs: 480, animEndMs: 600, tailMs: 0 },
    yMax: YMAX, clock: 300, lastT: 0, lastDx: null, phase: "impact",
    fx: { lead: "up", lv: 3, gapScale: 1, rMax: 29, cap: 32, alloc: { up: 16, dl: 16, merge: 0 },
      specs: { up: [], dl: [] }, slices: SLICES, comb: COMB, tail: ["up", "dl"],
      act: { up: true, dl: true }, pxPerT: PX_PER_T, dx0: 0, beatMs: 1000, burstMs: 120 } };
  u.ctx = mkCtx();
  return u;
}
const scan = (u) => methods._qbDrawFxScan.call(methods, u, TK);
const scanAt = (u, t) => { u._qbBeat.anim.clock = t; u.ctx = mkCtx(); scan(u); return u.ctx; };
const drawFx = (u, t, cfg) => {
  const saved = global.window.AQB_FX_CFG;
  if (cfg) global.window.AQB_FX_CFG = cfg;
  u._qbBeat.anim.clock = t;
  u.ctx = mkCtx();
  methods._qbDrawFx.call(methods, u, TK);
  global.window.AQB_FX_CFG = saved;
  return u.ctx;
};
/* 回声落笔 = 竖笔 x < 判定线-2(色散在 x0-1.6 属束体, 不混入); d = R + 0.5 - echo.x(亚像素对齐) */
const echoStrokes = (ctx) => ctx.strokes.filter((s) => s.x < R - 2);
const echoD = (ctx) => R + 0.5 - echoStrokes(ctx)[0].x;
// —— S1. 束体指令计数(I9-R5/R6 电池级证据): 逐帧 <=23, 分窗恰值 ——
{
  let cap = 0;
  const at = {};
  for (let t = 0; t <= 990; t += 30) {
    const n = instr(scanAt(mkU(STILL_UP, STILL_DL), t));
    cap = Math.max(cap, n);
    at[t] = n;
  }
  ok("S1 束体逐帧指令 <=23(6 晕+1 核+2 色散+5 彗尾+<=7 梳齿+2 回声 = 23 上限, I9-R5)", cap <= 23);
  ok("S1 Lv.3 回声窗(180,450ms)+色散窗(<500ms)双开恰 23(预算全用不虚设); 180ms 起拍点回声尚未起(q=0)恰 21",
    at[210] === 23 && at[300] === 23 && at[420] === 23 && at[180] === 21);
  {
    const c1 = scanAt(mkU(STILL_UP, STILL_DL), 300);
    ok("S1 束体 clip 实参记账(评审 major): 自含一次 clip 且 = [绘图区左缘, 画布右缘] 宽矩形(宽 840 >= 绘图区 800 > 0, 高 300 > 0 —— 放宽到判定线右侧留白, 非 no-op)",
      c1.clips.length === 1 && JSON.stringify(c1.clips[0]) === JSON.stringify([60, 10, 840, 300]));
  }
  ok("S1 回声窗止(450ms, d=span)恰 21(几何硬停少 2 笔) / 色散窗止(500ms)恰 19",
    at[450] === 21 && at[480] === 21 && at[510] === 19 && at[540] === 19);
  ok("S1 束 fade 窗 0.7xbeat(B2 模板保真二轮, I9 逐元素窗改判): 550-690ms 束体仍画"
    + "(色散/回声均已止 -> 恰 19), 700ms(0.7xbeat)起零绘制",
    at[570] === 19 && at[600] === 19 && at[690] === 19 && at[720] === 0 && at[990] === 0);
}
// —— S9. 六层晕宽度恒 hw[0](A2 回退: 束宽度感分级退役 —— 模板无宽度感系数; T5 色相联动保留):
//         Lv.3 grade 开也不再乘 1.1 系数, 宽度感分级回潮即红 ——
{
  const ctx = scanAt(mkU(STILL_UP, STILL_DL), 300);
  const haloW = ctx.strokes.slice(0, 6).map((s) => s.w);
  ok("S9 六层晕宽度恒 hw[0](34/24/16/10/5/2.5 递进 —— Lv.3 grade 开不乘系数)",
    JSON.stringify(haloW) === JSON.stringify([34, 24, 16, 10, 5, 2.5]));
}
{
  const calm = mkU(STILL_UP, STILL_DL);
  global.window.AQB_FX_CFG = Object.assign({}, CFG, { palette: "calm" });
  const c1 = scanAt(calm, 300);
  global.window.AQB_FX_CFG = CFG_NO_SCAN;
  const c2 = scanAt(calm, 300);
  global.window.AQB_FX_CFG = Object.assign({}, CFG, { impact: 0 });
  const c3 = scanAt(calm, 300);
  global.window.AQB_FX_CFG = Object.assign({}, CFG, { on: false });
  const c4 = scanAt(calm, 300);
  global.window.AQB_FX_CFG = CFG;
  ok("S1 门面: palette=calm / layers.scan=false / impact=0 / cfg.on=false 各自零束体绘制",
    instr(c1) === 0 && instr(c2) === 0 && instr(c3) === 0 && instr(c4) === 0);
}
// —— S2. 相位 A 行程(1.2 格 / 0.12beat, 与冲击窗同长) ——
{
  const xs = [];
  for (let t = 0; t <= 130; t += 10) {
    const ctx = scanAt(mkU(STILL_UP, STILL_DL), t);
    const core = ctx.strokes.find((s) => s.w === 1 && !s.stops && s.alpha === 1
      && s.style.indexOf("242,255,255") >= 0);
    xs.push([t, core ? core.x : NaN]);
  }
  ok("S2 t=0 硬核在判定线右 1.2 格(R+0.5+cellPx x 1.2 = 1100.5)", Math.abs(xs[0][1] - 1100.5) <= 1e-9);
  ok("S2 相位 A 内 x0 单调收敛(easeOut)且 0.12beat(120ms 冲击窗)内抵达判定线",
    xs.every(([t, x], i) => i === 0 || (t > 120 ? x === R + 0.5 : x < xs[i - 1][1]))
    && Math.abs(xs[xs.length - 1][1] - (R + 0.5)) <= 1e-9 && Math.abs(xs[12][1] - (R + 0.5)) <= 1e-9);
}
// —— S3. 亮束不横穿数据: 除回声外竖笔 x >= 判定线, 回声 x >= 判定线-200(I9-R7 探针) ——
{
  let minX = Infinity;
  let echoMin = Infinity;
  for (let t = 0; t <= 540; t += 30) {
    const ctx = scanAt(mkU(STILL_UP, STILL_DL), t);
    for (const s of ctx.strokes) {
      minX = Math.min(minX, s.x);
      if (s.x < R - 2) echoMin = Math.min(echoMin, s.x);
    }
    for (const r of ctx.fillRects) minX = Math.min(minX, r[0]);
  }
  ok("S3 全部束体落笔 x >= 判定线-200(亮束止于判定线, 不横穿数据 —— I9-R7 探针)", minX >= R - 200 - 1e-9);
  ok("S3 回声落笔 x >= 判定线-span(176 < 200)", echoMin >= R - 176 - 1e-9);
  // —— 墨量可见防回潮(评审 blocker): 抵达后(t >= 0.12beat, x0 = 判定线)束体每笔落笔区间
  //    [x-w/2, x+w/2](fillRect 取 [x, x+len])必须与束体 clip [L, 画布右缘] 求交 > 0 ——
  //    「按死指令计满却零墨」的 clip 失明回潮即红 ——
  {
    const arr = scanAt(mkU(STILL_UP, STILL_DL), 300);
    const hit = (x0, x1) => x0 < 900 && x1 > 60;
    const vis = arr.strokes.filter((s) => hit(s.x - s.w / 2, s.x + s.w / 2)).length
      + arr.fillRects.filter((r) => hit(r[0], r[0] + r[2])).length;
    const visComb = arr.fillRects.filter((r) => hit(r[0], r[0] + r[2])).length;
    const visCore = arr.strokes.some((s) => s.w === 1 && !s.stops
      && s.style.indexOf("242,255,255") >= 0 && hit(s.x - 0.5, s.x + 0.5));
    const visDispR = arr.strokes.some((s) => s.w === 1 && !s.stops
      && s.style.indexOf("255,77,157") >= 0 && hit(s.x - 0.5, s.x + 0.5));
    const visComet = arr.strokes.filter((s) => s.x >= R + 2 && s.x < R + 20 && s.w < 1.3 && s.w > 0.2).length;
    ok("S3 抵达帧(x0=判定线)23 笔全部墨量可见(落笔区间 x clip 求交 > 0) —— 硬核/右色散/彗尾/梳齿逐类在位",
      vis === 23 && visComb === 7 && visCore && visDispR && visComet === 5);
    const early = scanAt(mkU(STILL_UP, STILL_DL), 30);
    const earlyVis = early.strokes.filter((s) => hit(s.x - s.w / 2, s.x + s.w / 2)).length
      + early.fillRects.filter((r) => hit(r[0], r[0] + r[2])).length;
    const midVis = (() => {
      const c = scanAt(mkU(STILL_UP, STILL_DL), 90);
      return c.strokes.filter((s) => hit(s.x - s.w / 2, s.x + s.w / 2)).length
        + c.fillRects.filter((r) => hit(r[0], r[0] + r[2])).length;
    })();
    ok("S3 相位 A 滑入: 起步在留白外零墨(1.2 格行程 240px > 留白 40px, 计划相位 A 语义) -> 入画布帧当帧指令全可见(21/21) -> 抵达后 23/23",
      earlyVis === 0 && midVis === 21 && vis === 23);
  }
}
// —— S4. 回声: alpha <=0.20 + d=span 该帧零回声指令而束体仍在 + echoSpan 各档 ——
{
  const ctx = scanAt(mkU(STILL_UP, STILL_DL), 300);
  const echo = echoStrokes(ctx);
  ok("S4 回声恰 2 笔(1px 包络核 + 9px 淡晕), 位置 = 判定线 - span x q(匀速)",
    echo.length === 2
    && Math.abs(echoD(ctx) - 176 * (300 / 1000 - 0.18) / 0.27) <= 1e-9);
  ok("S4 回声 alpha: 核 = 渐变 stop 峰值 0.2xfallxa0(I9 修订: 1px 包络核仍 <=0.20 不变), "
    + "晕 = 0.34xfall(B4 模板保真二轮 —— 模板 demo:1246 同式, 旧 0.20 晕上限对 9px 晕退役; "
    + "晕随 fall 同步收, d=span 仍零笔)", (() => {
    const core = echo.find((s) => s.w === 1);
    const halo = echo.find((s) => s.w === 9);
    if (!core || !halo || !core.stops) return false;
    const peak = Math.max(...core.stops.map(([, c]) => {
      const m = /rgba\([^,]+,[^,]+,[^,]+,([0-9.]+)\)/.exec(c);
      return m ? parseFloat(m[1]) : 0;
    }));
    const fall = Math.pow(1 - echoD(ctx) / 176, 0.85);
    return peak <= 0.2001 && Math.abs(halo.alpha - 0.34 * fall) <= 1e-9;
  })());
  const hard = scanAt(mkU(STILL_UP, STILL_DL), 450);
  ok("S4 d=span(450ms): 该帧零回声指令(x<判定线-2)而束体仍在(21 笔 = 竖笔 14 + 梳齿 7 —— I9-R7 探针)",
    echoStrokes(hard).length === 0 && hard.strokes.length + hard.fillRects.length === 21);
  const d200 = mkU(STILL_UP, STILL_DL);
  global.window.AQB_FX_CFG = Object.assign({}, CFG, { echoSpan: "200" });
  scan(d200);
  const d100 = mkU(STILL_UP, STILL_DL);
  global.window.AQB_FX_CFG = Object.assign({}, CFG, { echoSpan: "100" });
  scan(d100);
  const dfull = mkU(STILL_UP, STILL_DL);
  global.window.AQB_FX_CFG = Object.assign({}, CFG, { echoSpan: "full" });
  scan(dfull);
  global.window.AQB_FX_CFG = CFG;
  ok("S4 echoSpan 200 -> d=88.9 / 100 -> d=44.4 / full 整幅 s=W(d=800xq —— A2 回退恢复整幅对照档)",
    Math.abs(echoD(d200.ctx) - 200 * (300 / 1000 - 0.18) / 0.27) <= 1e-9
    && Math.abs(echoD(d100.ctx) - 100 * (300 / 1000 - 0.18) / 0.27) <= 1e-9
    && Math.abs(echoD(dfull.ctx) - 800 * (300 / 1000 - 0.18) / 0.27) <= 1e-9);
}
// —— S5. 梳齿冻结(同拍重绘几何逐像素恒同)+ 横向细线条合计 ——
{
  const a = scanAt(mkU(STILL_UP, STILL_DL), 300).fillRects;
  const b = scanAt(mkU(STILL_UP, STILL_DL), 440).fillRects;
  const geom = (rs) => JSON.stringify(rs.map((r) => r.slice(0, 4)));
  ok("S5 梳齿 7 条 1px 级 fillRect(x>=判定线域, y 在绘图区 [T+2, B-3] 内 —— 评审 minor5 钳边), 同拍重绘几何逐像素冻结(只判定帧重算 —— R6; alpha 随束衰减不算几何)",
    a.length === 7 && b.length === 7 && geom(a) === geom(b)
    && a.every((r) => r[3] === 1) && a.every((r) => r[0] >= R)
    && a.every((r) => r[1] >= 12 && r[1] <= 307));
  ok("S5 横向细线条合计 = 切片 5 + 梳齿 7 = 12 <= 12(I9-R6)", SLICES.length + COMB.length === 12);
}
// —— S6. T2 光带(两轨各自 + 零长不落笔 + bandHalo 辉光预算; 光带计数用 scan=false 档隔离束体渐变笔) ——
{
  const ctx = drawFx(mkU(LIVE_UP_M, LIVE_DL_M), 300, CFG_NO_SCAN);
  const gradStrokes = ctx.strokes.filter((s) => s.stops);
  ok("S6 layers.band: 双轨各一道渐变 stroke 于末点 x(读数过渡两轨都必须画 —— L1 aside)",
    gradStrokes.length === 2 && gradStrokes.every((s) => Math.abs(s.x - R) <= 1e-9 && s.w === 4));
  const stopsUp = gradStrokes[0].stops;
  ok("S6 光带渐变底透明顶峰值(轨道语义色 #8B93F8)", stopsUp[0][1] === "rgba(139,147,248,0.000)"
    && stopsUp[1][1].indexOf("139,147,248") >= 0
    && parseFloat(/,([0-9.]+)\)/.exec(stopsUp[1][1])[1]) > 0.1);
  ok("S6 光带渐变构造坐标 = (0, yOf(prev), 0, yOf(shown)) 逐轨(评审 minor3: 爬升方向变异静默反转即红)",
    JSON.stringify(gradStrokes[0].gcoords) === JSON.stringify([0, yOfT(10), 0, yOfT(20)])
    && JSON.stringify(gradStrokes[1].gcoords) === JSON.stringify([0, yOfT(55), 0, yOfT(58)]));
  const full = drawFx(mkU(LIVE_UP_M, LIVE_DL_M), 300);
  ok("S6 同帧 blur 描边 <=5(I9 辉光预算修订: 环外圈 <=2 + bandHalo 1 + 曲线辉光 2 预留 S3 落地"
    + " —— S2 实测 3, 断言按新口径 <=5 写), 非零 blur 赋值点 <=2, 帧末清零",
    full.strokesWhileBlur <= 5 && full.blurSets.filter((v) => v > 0).length === 2
    && full.shadowBlur === 0);
  const halo = full.strokes.filter((s) => s.blur > 0 && s.w === 4);
  ok("S6 bandHalo 仅 lead 轨一道(白名单 bandHalo; 双轨都画即超 <=3 预算)",
    halo.length === 1 && halo[0].style === "#FF6BD6");
  const none = drawFx(mkU(STILL_UP, STILL_DL), 300, CFG_NO_SCAN);
  ok("S6 shown=prev(impact 窗)光带零长不落笔(零渐变笔)", none.strokes.filter((s) => s.stops).length === 0);
  const off = mkU(LIVE_UP_M, LIVE_DL_M);
  const offCtx = drawFx(off, 300, Object.assign({}, CFG, {
    layers: Object.assign({}, CFG.layers, { band: false, scan: false }) }));
  ok("S6 layers.band=false: 零光带落笔(层开关逐帧读 AQB_FX_CFG)",
    offCtx.strokes.filter((s) => s.stops && s.w === 4).length === 0);
}
// —— S6b. 束包络接线(评审 minor6): env 渐变峰位 p = (yOf(shown)-T)/H —— 错用 prev / 缺口轨不退让变异即红;
//    渐变构造坐标 = (0, T, 0, T+H)(评审 minor3) ——
{
  const envOf = (u) => {
    const c = scanAt(u, 300);
    return c.strokes[0];
  };
  // 双峰分立: LIVE shown 20/58 -> p = (yOfT(20)-10)/300 与 (yOfT(58)-10)/300, 差 > 0.08
  const live = envOf(mkU(LIVE_UP_M, LIVE_DL_M));
  const pUp = (yOfT(20) - 10) / 300;
  const pDl = (yOfT(58) - 10) / 300;
  ok("S6b env 双峰分立: 构造坐标 (0,T,0,T+H) + 升序 stop 峰位 = 两轨末点 shown 的归一化 y(非 prev —— 接线变异即红)",
    JSON.stringify(live.gcoords) === JSON.stringify([0, 10, 0, 310])
    && Math.abs(live.stops[1][0] - Math.min(pUp, pDl)) <= 1e-9
    && Math.abs(live.stops[2][0] - Math.max(pUp, pDl)) <= 1e-9
    && live.stops[1][1].indexOf("255,107,214") >= 0 && live.stops[0][0] === 0 && live.stops[3][0] === 1);
  // 贴近合并: shown 30/33 -> 两峰差 0.0476 < 0.08 -> 单峰 = 中点
  const CLOSE_UP = { prev: 28, target: 32, shown: 30, delta: 2, level: 3, live: true };
  const CLOSE_DL = { prev: 31, target: 35, shown: 33, delta: 0.09, level: 2, live: true };
  const close = envOf(mkU(CLOSE_UP, CLOSE_DL));
  const pMid = ((yOfT(30) - 10) / 300 + (yOfT(33) - 10) / 300) / 2;
  ok("S6b env 贴近合并: 两峰差 < 0.08 -> 单峰 p = 两轨末点 y 中点",
    close.stops.length === 3 && Math.abs(close.stops[1][0] - pMid) <= 1e-9
    && close.stops[1][1].indexOf("255,107,214") >= 0);
  // 缺口轨退让: dl 缺口 -> 两源同退 lead 末点 y -> 单峰 = lead shown 的 p(缺口轨 shown=null 直算得底边 p=1 即红)
  const gap = envOf(mkU(LIVE_UP_M, { prev: null, target: null, shown: null, delta: 0, level: 0, live: false }));
  ok("S6b env 缺口轨退 lead 末点 y: 单峰 p = (yOf(lead.shown)-T)/H(假底边峰 p=1 即红 —— I10/D4)",
    gap.stops.length === 3 && Math.abs(gap.stops[1][0] - (yOfT(20) - 10) / 300) <= 1e-9
    && Math.abs(gap.stops[1][0] - 1) > 0.1);
  // 回声同包络: 渐变构造坐标同 (0, T, 0, T+H)
  const echoEnv = (() => {
    const c = scanAt(mkU(LIVE_UP_M, LIVE_DL_M), 300);
    return c.strokes.find((s) => s.x < R - 2 && s.w === 1 && s.stops);
  })();
  ok("S6b 回声渐变构造坐标 = (0,T,0,T+H)(按曲线包络着色 —— 评审 minor3)",
    echoEnv && JSON.stringify(echoEnv.gcoords) === JSON.stringify([0, 10, 0, 310]));
}
// —— S7. R6 切片绘制域(C2 门 glitch || lv>=2 / 厚 1.5(Lv.3 2.0; fixed 3) / 独立窗 0.25×beat
//          / 右缘域)+ 束体+切片合计 <=28 + 微震让位。观测帧 t=210: 切片窗(<250ms)与束体回声
//          窗(180-450ms)双开 -> 切片 5 + 束体 23 = 28 恰满(冲击闪光 +1 stroke 仅 impact 窗
//          t<120, 不在本帧, 不入本合计 —— I9 装饰指令修订注记) ——
{
  const ctx = drawFx(mkU(LIVE_UP_M, LIVE_DL_M), 210, Object.assign({}, CFG, { palette: "glitch" }));
  const sl = ctx.fillRects.filter((r) => r[0] < R);
  ok("S7 C2 切片: t=210(0.25xbeat 窗内)5 条 2px 级(Lv.3 厚 2.0; fixed 档 3), x<判定线右缘域, len 10-80, 右端 <=判定线",
    sl.length === 5 && sl.every((r) => r[3] === 2)
    && sl.every((r) => r[0] + r[2] <= R + 1e-9 && r[2] >= 10 && r[2] <= 80));
  ok("S7 切片色池以故障色为主(45/35/20 -> 池序 Lv 色/品红/lead 语义色 #8B93F8)",
    sl.every((r) => ["#FF6BD6", "#FF4D9D", "#8B93F8"].indexOf(r[4]) >= 0)
    && sl.filter((r) => r[4] === "#FF6BD6").length >= 1);
  ok("S7 束体+切片合计 5+23=28 <=28(I9-R6; 切片窗 0.25xbeat 独立 q —— t>=250 切片先于束体退场)",
    sl.length + 23 <= 28);
  methods._drawerAnimRaf = 7;
  const paused = drawFx(mkU(LIVE_UP_M, LIVE_DL_M), 210, Object.assign({}, CFG, { palette: "glitch" }));
  methods._drawerAnimRaf = 0;
  const resumed = drawFx(mkU(LIVE_UP_M, LIVE_DL_M), 210, Object.assign({}, CFG, { palette: "glitch" }));
  ok("S7 抽屉入场 rAF 在途(_drawerAnimRaf 非零): 切片与微震暂停(零切片落笔), 归零恢复 —— §09 让位",
    paused.fillRects.filter((r) => r[0] < R).length === 0 && paused.fillRects.filter((r) => r[0] >= R).length === 7
    && resumed.fillRects.filter((r) => r[0] < R).length === 5);
  // 窗界外采样(#4): t=300 >= 0.25xbeat(250ms)切片窗已尽而束体仍在 —— 切片窗回退 0.55/0.7 即红。
  // 束体计数走 scan 单域(scanAt): t=300 回声+色散双开 = 16 笔 stroke + 7 梳齿 = 23(修复单「束体 19」
  // 系 510/540ms 档(色散+回声均止)的恰值, t=300 实为 23 —— 以现场恰值为准)。
  const late = drawFx(mkU(LIVE_UP_M, LIVE_DL_M), 300, Object.assign({}, CFG, { palette: "glitch" }));
  ok("S7 切片窗 0.25xbeat 窗界外(t=300>=250): 切片 0 条且束体全预算仍在(scan 单域恰 23)—— 窗回退即红",
    late.fillRects.filter((r) => r[0] < R).length === 0
    && (() => { const c = scanAt(mkU(LIVE_UP_M, LIVE_DL_M), 300); return c.strokes.length + c.fillRects.length; })() === 23);
}
// —— S8. T5 grade=false: 全域(描边/填充/渐变 stop/阴影色)无 Lv.3 色, 恒 Lv.1 ——
{
  const lv3 = "#FF6BD6";
  const ctx = drawFx(mkU(LIVE_UP_M, LIVE_DL_M), 300);
  ok("S8 grade 开: Lv.3 色在位(对照)", ctx.strokes.some((s) => s.style === lv3)
    && ctx.strokes.some((s) => s.blur > 0 && s.style === lv3));
  const off = mkU(LIVE_UP_M, LIVE_DL_M);
  const offCtx = drawFx(off, 300, Object.assign({}, CFG, {
    layers: Object.assign({}, CFG.layers, { grade: false }) }));
  const bad = []
    .concat(offCtx.strokes.filter((s) => s.style === lv3))
    .concat(offCtx.fillRects.filter((r) => r[4] === lv3))
    .concat(offCtx.fillTexts.filter((f) => f.style === lv3))
    .concat(offCtx.strokes.filter((s) => s.stops && s.stops.some(([, c]) => c.indexOf(lv3) >= 0)));
  ok("S8 grade 关: 描边/填充/渐变 stop 全域无 Lv.3 色(bandHalo/徽标/束包络/切片池恒 Lv.1 —— T5 收口)",
    bad.length === 0 && offCtx.fillTexts.some((f) => f.style === "#7AD9FF"));
}
// —— S10. 判定帧全高冲击闪光(C4 模板保真二轮): t < impactMs 判定线全高 lw2 stroke,
//          alpha 0.75x(1-t/impactMs)ximpact 线性回落; 不挂 neon 门、calm 档亦显、色走 Lv 表
//          (D7/I11 例外注记); I9 装饰指令白名单: +1 stroke 仅 impact 窗内(束 <=23/束+切片
//          <=28/横线 <=12 原样不抬) —— 闪光记录面 = lw2 + rgba Lv 色(短亮段直色 #FF6BD6 不
//          混入; 本 ctx fill 不清 ops, 闪光 x 记录面被小菱形顶点污染, 全高几何(x=判定线-0.5,
//          T->T+H)由视觉引擎电池 G13 ops[16..27] 逐点钉死 —— ops[16..17] 短亮段/[18..21] C10 小
//          菱形/[22..25] 判定线小菱形(P4)/[26..27] 闪光) ——
{
  const flashOf = (t, over) => {
    const c = drawFx(mkU(LIVE_UP_M, LIVE_DL_M), t,
      Object.assign({}, CFG, { layers: Object.assign({}, CFG.layers, { scan: false }) }, over || {}));
    return c.strokes.filter((s) => s.w === 2 && String(s.style).indexOf("255,107,214") >= 0);
  };
  const f60 = flashOf(60);
  const alphaOf = (s) => {
    const m = /,([0-9.]+)\)$/.exec(String(s.style));
    return m ? parseFloat(m[1]) : NaN;
  };
  ok("S10 impact 窗内(t=60<120): 冲击闪光恰 1 笔, alpha = 0.75x(1-0.5)x0.7 = 0.2625(线性回落)",
    f60.length === 1 && Math.abs(alphaOf(f60[0]) - 0.2625) <= 1e-3);
  ok("S10 impact 窗外(t=150>=120): 零闪光笔(窗有界 —— I9 装饰指令白名单仅窗内 +1)",
    flashOf(150).length === 0);
  ok("S10 不挂 neon 门(D7): neon=false 闪光仍在(恰 1 笔)",
    flashOf(60, { neon: false }).length === 1);
  ok("S10 calm 档亦显(D7): palette=calm 闪光仍在(色走 Lv 表 —— 不随配色降档熄灭)",
    flashOf(60, { palette: "calm" }).length === 1);
  ok("S10 impact=0: 零闪光笔(全零 alpha 不落笔, 同束体 a0 门口径)",
    flashOf(60, { impact: 0 }).length === 0);
}
console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
"""


def test_frontend_qb_fx_scan_band_battery():
    """T6 综合表现层 S2-b 电池 + 接缝静态钉(plan 26-11-12-1139 §03 T4/T6 行/R6 节/D17-D19, §02 R5/R6/R7)

    行为面(node 电池, 无 node 静默跳过, 同视觉引擎口径):
    1. R6 确定性伪随机: hash01 同(拍,槽)恒同且恒 [0,1)、分布 45/35/20 ±0.05(plan §04 原型带符号
       >> 版本实测 90% 落 [0,0.5) 色池配比失真 —— 生产改 Math.imul+>>> 雪崩, 分布断言守);
       strat 分层采样恒 [0,1) 且第 i 条只在第 i 层内; tearRnd 三档(fixed=0.5 恒同形对照/
       random 不可复现对照/linked=hash01 默认);
    2. R6 撕裂切片清单: 2/3/5 条按 lead 等级(<=5)、长 10-80 随 Δ、alpha 线性式 (0.10+0.08×lv)×q×impact
       (C2: 0.18/0.26/0.34 同值不同源; q/impact 由绘制侧逐帧乘, 冻结清单不含逐帧因子, 表常量退役)、
       y 在撕裂带 ±(0.08+0.30×min(1,Δ/0.5))×H 内且钳绘图区、右端缩进 0-18(fixed 恒 0 齐平)、
       同参数恒同 / fixed 跨拍同形 / linked 跨拍异形 + 逐条公式紧断言(y = yC + (strat(i,n,
       hash01(bi,slot))-0.5)×2×halfBand, 首末双端对称 —— 评审 minor4: 分层采样/槽位/半带使用
       变异即红; spawn 侧同式紧断言在调度器电池 F9, 半带系数 0.08/0.30 与 /0.5 归一变异即红);
    3. R6 梳齿清单: 3/5/7 条按等级、长 4-24 随 Δ、带内、fixed 等距恒长(strat(c,n,0.5)) +
       y 输出侧钳 [tTop+2, tBot-3](带越出绘图区的夹具断言钳边真实生效 —— 评审 minor5,
       越界齿计入预算却被裁零墨回潮即红);
    4. D19 回声数学: span=clamp(0.22×绘图宽,100,200) 不超绘图宽、full 恢复整幅 s=w(A2 回退,
       模板 demo:1152-1158 对照档口径)、100/150/200 直取; fall=pow(1−d/span,0.85) 且 d≥span 恒 0
       (几何硬停)单调不增; echoQ 0.18-0.45beat 匀速;
    5. 束包络 stops(R5): 双峰分立/贴近 <0.08 合并单峰/钳 [0.02,0.98]/NaN 退 0.5;
    6. T5 联动单点: lvColor grade 关恒 Lv.1、开随等级、非法等级退 Lv.3(束宽度感联动 beamWScale
       已退役 A2 —— 六层晕恒 hw[0], 行为面见绘制面电池 S9); fade 助手;
    7. 绘制面束体指令计数(_qbDrawFxScan 记账 ctx): 逐帧 ≤23、Lv.3 双开窗恰 23/回声窗止 21/
       色散窗止 19/束 fade 窗 0.7×beat(B2 模板保真二轮: 550-690ms 恰 19, 700ms 起零)/calm/
       scan=false/impact=0/on=false 各自 0 + 束体 clip 实参
       记账断言(自含一次 clip 且 = [绘图区左缘, 画布右缘] 宽矩形, 宽 >= 绘图区宽 > 0 ——
       评审 major: rect/clip 记实参, no-op 前提下的计数/落笔断言是盲区);
    8. 相位 A 行程: t=0 硬核在判定线右 1.2 格(cellPx×1.2)、easeOut 单调收敛、0.12beat 内抵达;
    9. 亮束止于判定线: 全部落笔 x ≥ 判定线−200、回声 x ≥ 判定线−span + **墨量可见防回潮**
       (评审 blocker: 束体 clip 放宽到画布右缘后, 抵达帧 23 笔落笔区间与 clip 求交全 > 0,
       硬核/右色散/彗尾/梳齿逐类在位; 相位 A 起步在留白外零墨 -> 入画布帧当帧全可见 ——
       按死指令计满却零渲染回潮即红);
    10. 回声: 恰 2 笔、位置 = 判定线 − span×q、1px 核 alpha ≤0.20 不变 + 9px 晕 0.34×fall(B4
        模板保真二轮, 旧 0.20 晕上限退役 —— I9 修订表)、d=span 帧零回声指令而束体仍在、
        echoSpan 各档(200/100 直取, full 整幅 s=W —— A2 回退);
    11. 梳齿冻结(同拍重绘几何逐像素恒同, y 在绘图区内)+ 横向细线条合计 12;
    12. T2 光带: 双轨各一道渐变 stroke 于末点 x、底透明顶峰值、shown=prev 零长不落笔、
        band=false 零落笔、bandHalo 仅 lead 一道(同帧 blur stroke = 环外圈 2 + 光带 1 = 3
        ≤ 5 —— I9 辉光预算修订 ≤5, 曲线辉光 2 预留 S3, S2 实测 3; 非零赋值点 ≤2、帧末清零)
        + 渐变构造坐标逐轨断言
        (0, yOf(prev), 0, yOf(shown) —— 评审 minor3: 坐标丢失会让爬升方向变异静默反转);
    13. 切片绘制域(C2 模板保真二轮 + 评审修复 calm 排除): 门 非 calm 且 (glitch || lv>=2)
        (模板 demo:1086 isCalm() 早退同口径)、t=210(0.25×beat 独立窗与回声窗双开)
        5 条 2px 级(Lv.3 厚 2.0; fixed 档 3)x<判定线、色池故障色为主、束体+切片 28、
        _drawerAnimRaf 在途切片暂停归零恢复(§09 微震让位)、窗界外采样(t=300 切片 0 条而束体
        恰 23 —— 窗回退 0.55/0.7 即红);
    14. T5 grade=false 全域(描边/填充/渐变 stop/阴影)无 Lv.3 色;
    15. 冲击闪光白名单(S10, C4/D7/I11 例外注记): t<impactMs 判定线全高 lw2 恰 1 笔 alpha
        0.75×(1−t/impactMs)×impact 线性回落/窗外零笔/neon=false 仍在/calm 档亦显/impact=0
        零笔 —— I9 装饰指令修订注记 +1 stroke 仅 impact 窗内(束 ≤23/束+切片 ≤28/横线 ≤12
        原样不抬), 几何面(x=判定线−0.5 全高)由视觉引擎电池 G13 ops 钉;
    16. 束包络接线(评审 minor6): env 渐变峰位 p = (yOf(shown)-T)/H —— 双峰分立/贴近合并单峰/
        缺口轨退 lead 末点 y(错用 prev/缺口不退让变异即红); env 与回声渐变构造坐标
        (0,T,0,T+H)(评审 minor3)。
    接缝面(静态钉):
    a. 层开关接线点: cfg.layers.band/scan/grade 字面量在各自绘制域 + _qbDrawFx 内调用
       _qbDrawFxScan 行在位且在 _qbDrawFx 自身 restore 之后(嵌套 clip 只收不放 —— 评审
       blocker 的 clip 放宽前提)+ 束体域自含 ctx.scale(px,px) 与 clip=画布右缘
       (u.ctx.canvas + Math.max(W, canvasW-L))字面量;
    b. 束体绘制域(_qbDrawFxScan)剥注释后 fillRect 恰 1 处且为梳齿 1px 级(零整块铺底 —— I9-R6),
       T2 光带块零 fillRect;
    c. I3 反向钉扩 scan 域(零 destroy/new uPlot/零 loading);
    d. 切片微震让位门(!this._drawerAnimRaf 在切片条件内);
    e. _qbFxLvColor(fx.lv, cfg.layers.grade === true) 恰 3 处(fx/锚/束);
    f. 束体常量行逐字(六层晕表/强度 0.78/条数表/回声八常量含 _QB_FX_ECHO_HALO_ALPHA = 0.34
       —— B4 模板保真二轮/T2 三常量; 束宽度感表与切片 alpha 表
       退役 —— A2/C2, 缺残留断言)。
    变异自证(S2-b 评审修复轮, 10 发全 KILLED): M1 宽clip->绘图区clip/M2 clip no-op(桩)/
    M3a band渐变坐标反转/M3b env渐变坐标漂移/M4a 半带系数0.30->0.20/M4b 0.08->0.05/
    M4c 归一分母0.5->1/M5 梳齿钳边移除(纯函数带越界夹具)/M6a env错用prev/
    M6b 缺口轨不退让 —— 逐发由对应新断言判红。
    既有电池口径保持: 束体+切片 ≤28 由 S7 分域计数合成, 横向 ≤12 由 S5 清单长度合成。"""
    shared = os.path.join(STATIC_ROOT, "shared")
    js = open(os.path.join(shared, "qb_traffic_chart.js"), encoding="utf-8").read()
    # —— a. 层开关接线点(逐帧读 AQB_FX_CFG 的三个新开关 + 扫描束调用行与宽 clip 域) ——
    fxb = re.search(r"_qbDrawFx\(u, tk\) \{\n(.*?)\n    \},", js, re.S)
    assert fxb, "缺 _qbDrawFx(drawAxes 装饰段)"
    scb = re.search(r"_qbDrawFxScan\(u, tk\) \{\n(.*?)\n    \},", js, re.S)
    assert scb, "缺 _qbDrawFxScan(T4 扫描束绘制单点)"
    assert "this._qbDrawFxScan(u, tk);" in fxb.group(1), \
        "_qbDrawFx 内必须调用 _qbDrawFxScan(束体挂 drawAxes 段 = 网格后系列前, I6 层序)"
    fxb_body = fxb.group(1)
    assert fxb_body.rfind("ctx.restore();") < fxb_body.find("this._qbDrawFxScan(u, tk);"), \
        "束体调用必须在 _qbDrawFx 自身 restore 之后(评审 blocker: 嵌套 clip 只收不放, 束体 clip 放宽到画布右缘必须在绘图区 clip 之外)"
    scb_code_raw = scb.group(1)
    assert "ctx.scale(px, px);" in scb_code_raw, \
        "束体绘制域必须自含 save+scale(CSS px 坐标系 —— 调用点已 restore, 不再共享调用方变换)"
    assert "u.ctx.canvas" in scb_code_raw and "Math.max(W, canvasW - L)" in scb_code_raw, \
        "束体 clip 必须放宽到画布右缘(canvas.width/px, 下限绘图区宽)—— 判定线右侧留白是相位 A 滑入与右向结构的可见域(评审 blocker)"
    assert "cfg.layers.band === true" in fxb_body, \
        "T2 光带缺 cfg.layers.band 逐帧门(层开关拍内改参下一帧生效 —— §05.3)"
    assert "cfg.layers.scan !== true" in scb_code_raw, \
        "T4 扫描束缺 cfg.layers.scan 逐帧门(层开关拍内改参下一帧生效 —— §05.3)"
    assert "cfg.layers.grade === true" in fxb_body and "cfg.layers.grade === true" in scb_code_raw, \
        "T5 分级联动: fx 与束体绘制域必须逐帧读 cfg.layers.grade(grade 关恒 Lv.1 色)"
    # —— b. 束体绘制域零整块铺底(fillRect 恰 1 处 = 梳齿 1px 级; T2 光带块零 fillRect) ——
    scb_code = re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", scb.group(1), flags=re.S))
    assert scb_code.count("fillRect") == 1 and re.search(r"fillRect\([^;]*, 1\);", scb_code), \
        "束体绘制域 fillRect 必须 = 梳齿 1px 级横条恰一处(整块铺底回潮即红 —— I9-R6/R4)"
    band_blk = re.search(r"if \(cfg\.layers\.band === true\) \{\n(.*?)\n      \}", js, re.S)
    assert band_blk, "缺 T2 光带块(cfg.layers.band 分支)"
    assert "fillRect" not in band_blk.group(1), "T2 光带块不得有 fillRect(渐变描边, 零铺底)"
    # —— c. I3 反向钉: scan 域零销毁重建/零 loading ——
    assert "new uPlot" not in scb.group(1) and "destroy(" not in scb.group(1) and "loading" not in scb.group(1), \
        "束体绘制域不得 destroy/new uPlot/触碰 loading(I3 不闪; 装饰帧只经调度器提交)"
    # —— d. 切片微震让位门(§09: 抽屉入场 rAF 追赶循环在途时切片与 ±3px 微震暂停) ——
    assert "!this._drawerAnimRaf" in fxb.group(1), \
        "切片绘制条件缺 !this._drawerAnimRaf 让位门(抽屉入场逐帧改 dock 高会经 RO->setSize 连锁重画)"
    # —— e. T5 联动色相单点恰 3 处(fx 装饰段/锚段/束体) ——
    assert js.count("_qbFxLvColor(fx.lv, cfg.layers.grade === true)") == 3, \
        "Lv 色解析单点 _qbFxLvColor(fx.lv, grade) 必须恰 3 处(fx/锚/束), 内联 Lv 色表取值回潮即双写漂移"
    assert "_QB_FX_LV_COLORS[fx.lv] ||" not in js, \
        "fx 绘制域不得再内联取 Lv 色(全部走 _qbFxLvColor 单点 —— grade 关恒 Lv.1 的收口面)"
    # —— f. 束体常量行逐字(单点漂移即红) ——
    assert "const _QB_FX_BEAM_HALO = [[34, 0.035], [24, 0.05], [16, 0.08], [10, 0.13], [5, 0.22], [2.5, 0.38]];" in js, \
        "缺/漂移 T4 六层晕宽度表(R5: 宽到窄递进, 低 alpha 叠层逼近高斯)"
    assert "const _QB_FX_BEAM_INTENSITY = 0.78;" in js, "缺/漂移 T6 束强度系数 0.78"
    assert "const _QB_FX_TEAR_COUNT = { 1: 2, 2: 3, 3: 5 };" in js, "缺/漂移 R6 切片条数表"
    assert "const _QB_FX_COMB_COUNT = { 1: 3, 2: 5, 3: 7 };" in js, "缺/漂移 R6 梳齿条数表"
    for line in (
        "const _QB_FX_ECHO_SPAN_RATIO = 0.22;",
        "const _QB_FX_ECHO_SPAN_MIN = 100;",
        "const _QB_FX_ECHO_SPAN_MAX = 200;",
        "const _QB_FX_ECHO_PHASE_LO = 0.18;",
        "const _QB_FX_ECHO_PHASE_HI = 0.45;",
        "const _QB_FX_ECHO_FADE_POW = 0.85;",
        "const _QB_FX_ECHO_ALPHA_CAP = 0.2;",
        "const _QB_FX_ECHO_HALO_ALPHA = 0.34;",
    ):
        assert line in js, f"缺/漂移 D19 回声常量 {line}"
    assert "const _QB_FX_BAND_ALPHA = 0.7;" in js and "const _QB_FX_BAND_WIDTH = 4;" in js \
        and "const _QB_FX_BAND_HALO_ALPHA = 0.5;" in js, "缺/漂移 T2 光带常量"
    # 束宽度感分级退役(A2 回退 —— 模板无宽度感系数, 六层晕恒 hw[0]; T5 色相联动保留):
    assert "_QB_FX_BEAM_WSCALE" not in js and "_qbFxBeamWScale" not in js, \
        "束宽度感表/联动函数残留(A2 回退: 六层晕恒 hw[0], 宽度感分级退役)"
    # 切片 alpha 表退役(C2 —— 改线性式 0.10+0.08×lv, q/impact 由绘制侧逐帧乘):
    assert "_QB_FX_TEAR_ALPHA" not in js, \
        "切片 alpha 表残留(C2: 改线性式 0.10+0.08xlv, 表常量退役)"
    # —— 行为面 node 电池(纯函数面 + 绘制面各一发) ——
    node = shutil.which("node")
    if not node:
        return
    for probe, tag in (
        (_NODE_QB_FXVIS_SCAN_PROBE, "T6 表现层纯函数"),
        (_NODE_QB_FXVIS_SCAN_DRAW_PROBE, "T6 表现层绘制面"),
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
