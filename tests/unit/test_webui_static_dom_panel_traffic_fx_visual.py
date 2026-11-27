"""test_webui_static_dom_panel_traffic_fx_visual 测试计划: webui 前端静态守阵: 详情面板 / 弹窗 / 浮层

原 test_webui_static_dom_panel_traffic.py 按域拆分(move-only, 2026-11-27); 测试 ID/名称/断言零变化。

## 测试计划(每个测试函数一条)
- test_frontend_qb_fx_visual_engine_battery: 视觉引擎 V + N 霓虹元素层 S2-a 电池 + 接缝静态钉(S2-a, plan 26-11-12-1139 §03 V 表/N 节/D1-D4, §06 S2 行) —— node 电池真跑(同节拍内核范式): I6 图层顺序常量逐字(geometry/neon 恒在 curve 前、anchor 在后)+ I11 N 层白名单六元素(S2-b 增 bandHalo 数值光带辉光)/黑名单八元素逐字且零交集 + V1 Lv 色表逐字(#7AD9FF/#FEFFA9/#FF6BD6; 四皮肤无 --qb-lv* 令牌已核查, 计划色值常量落 shared 层)+ 三档配色 blur 上限(neon 10/glitch 14/calm 0)+ V2 环边数映射(3/6/8)+ I9 预算常量(粒子 ≤32/每轨半套 ≤16/N 0.33×beat/粒子窗 0.55×beat/y 间距 26px/切片 ≤5/微震 3px/光点 ≤2/全宽巡回(旧末段 6 桶常量退役)) + D3 lead 仲裁(argmax 优先非缺口非静默轨/双轨静默 null/恰等取 up) + partCap(D5 模板基数 6+7×lv=13/20/27 x 密度, clamp 32 保留, 密度 ≤0 零粒子; P9 兼容 Lv.1 仍发射) + D3 三策略分配(both 对半各 ≤16 合计守恒全域扫/lead 全套从属零/merge 中点一次/未知回落 both) + D4 y 间距缩小(线性 /26 下限 0.4 不合并不取消) + N 回落 0.33×beat + 冲击环(C3 模板式: pf=t/(0.6×beat) 线性扩张 r=(4+24pf)×rScale×gapScale, alpha=0.85×(1−pf)×impact×rScale×gapScale, rScale 半套系数 both 0.5/lead 1/merge 1, pf≥1 null —— B3 环窗 0.6) + V3 粒子三阶段(爆发 ×4.5 闭式/拖尾 easeOut 减速位移步单调收缩/末态恰 dist/C8 模板式 alpha=0.78×(1−t/T)×impact 与 rot=t/260+idx 匀速单向 —— rot0/vr 退役/carryPx 随 L0 末点滑动) + 喷射清单(三/四/五边非圆点/同种子恒同/360° 全向 + 行程上限静态钳(P1, 旧左向 270° 弧 D2 退役)/尺寸 1.6-4.2 C8/行程界) + R6 撕裂切片(≤5/|offX| ≤3 x 向微震 dy0/ph 退役 —— C2/D3/长 10-80/同参数恒同) + 锚旋转周期常量 2639(C1/D6) + I9 逐元素窗常量(模板保真二轮 S2: 顶门最大窗 0.7/切片独立窗 0.25/束 fade 窗 0.7 —— 旧 0.55 单一顶门退役, 粒子 0.55/环 0.6 各自独立保留) + 伪随机确定性; 调度器 fx 面(真 mixin 方法 + 桩 uPlot 含 valToPos/bbox 全量): 判定帧 fx 生成门(cfg.on=false fx null 但 L0/L1 照常/reduce 无 anim/缺口轨 lead 单轨/双轨真 0 零装饰 —— F1 后值>0 恒 >=Lv.1)+ both/lead/merge 三策略落 fx 清单 + D4 y 间距实测缩小 + 装饰帧保障(无 shift 长窗 impact 窗零提交帧强制重绘 + y 钉 31.5 成对)+ 次区相位(收敛帧衔接/光点 ≤4 alpha 0.3×(1−qt) ≤0.3 位置在绘图区内/全宽巡回 x 跨多段非末段/1px 量化去重零空转/窗尽收尾 anim null/拍内关 tail 下一帧收尾)+ merge+缺口轨落位退 lead 末点 y(F7: specs.merge[0].y0 === yOf(lead.shown), 与底边的假中点即红 —— 评审修复2; S2-b 起切片锚带改 R6 撕裂带 ±(0.08+0.30×min(1,Δ/0.5))×H, 断言带内且清单无条件生成)+ spawn 满额清单与密度解耦(F8: 密度 0.4 仍 14/13 —— D5 基数 27, cap=partCap(lv,1), 评审修复3) + R6 撕裂带 spawn 公式逐条紧断言(F9: halfBand=(0.08+0.30×min(1,Δ/0.5))×H + strat×hash01(尾桶,slot) + 带内钳边与梳齿绘图区钳 —— 评审 minor4: 半带系数与归一分母变异即红); 绘制面 ctx 桩电池(G0-G16, 记账式 2d context 真 _qbDrawFx/_qbDrawFxAnchor; 模板保真二轮 S2: stroke 记 strokeMeta 笔画元数据/fillText 记 {s,font,alpha}): blur 预算(非零赋值恰 1 施加点/带 blur stroke = spots 数 ≤2/逐帧扫帧末 shadowBlur 恒 0/palette=calm 恒不赋非零 —— 评审修复7, 变异自证删 blur 清零行必红; 旧场景 shown=prev 光带零长 bandHalo 不参与, 完整辉光预算在 scan_band 电池)+ neon=false 白名单断言面收窄(I11 例外注记 —— D7: lvBadge 常显 fillText 恰 1 + 判定帧全高冲击闪光 rgba Lv 色lw2 恰 1 笔不挂 neon 门; 环外圈辉光/短亮段/粒子外圈仍零 Lv 直色落笔, 锚段同验)+ 密度拍内即时(0.4→15/1→31/0.1→7 —— D5 基数 27 + 每活性轨 +2 fill: C10 小菱形 + P4 判定线小菱形)+ 切片门 C2+calm 排除(非 calm 且 (glitch || lv≥2 —— neon 档 Lv.3 即画 5 条 2px 级/Lv.1 neon 零切片/拍内切 glitch 下一帧即画 2 条 1.5px 级/calm 档 Lv.3 亦零切片 —— 模板 demo:1086 isCalm() 早退同口径), 独立窗 0.25×beat; 计数按 x<绘图右缘滤除束体梳齿)+ 环旋转与外圈新式(G13: t=100 顶点逐点吻合 rot=t/300/外圈 rot+0.4 半径 9+31pf alpha 0.55(1-pf)impact, 主环 lw2/短亮段 lw3 alpha 0.55×q×impact(P2); 环心观测 G8/G11 改 t=0 对径两点 + neon=false 摘 N 层噪声, 粒子镜像 G12 改 t=130 避闪光窗; 判定线小菱形 P4: poly(xJudge,y,2.6,4,t/420) rgba(trackCol,0.35) 钉 x=L+W, 与 C10 并存)+ draw 侧 merge+缺口轨环心 = yOf(lead.shown)(x=tipX 顶点四点均值观测, 假中点即红)+ lead 加亮跨缺口重新 moveTo 不桥接([20,null,25] vs [20,22,25] 对照 —— 评审修复6) + S3 轮追加(G15 曲线辉光 A1: 拍内 t<beat 独立窗/t=800 顶门外仍画/两轨 trackCol blur 2 道计入 I9 <=5/calm blurCap=0 退化普通描边; G16 N 锚辉光 C7: 6 边/两轨各 6 顶点/alpha=0.5xqximpact/rot=t/320/tipX —— 机检归属本电池, CSS 逐字钉在锚电池) + 缺陷修补轮追加 G17 ctx transform 配平(drawGlow 返回后 save==restore 计数相等 —— _qbCanvasScale 的 save+scale 必须由函数自还; uPlot 1.6.x 渲染循环无顶层 save 兕底, pxRatio>1 泄漏 scale 逐帧叠加 = 真机全图放大错位乱跳); 静态钉: I6/I11/V1/I9 常量行逐字 + 钩子注册序 = 层序(vendor 1.6.32 源实证: 主渲染序 clearRect→drawClear→Pl.forEach[axes→series]→draw, Ci("drawAxes") 在 Dl.axes 末尾 = 网格后系列前 —— drawClear 斜纹恒最底/drawAxes fx(挂 drawClear 会被网格盖住违 I6)/draw 限速→锚)+ 背景零铺色(fx 域剥注释后 fillRect 恰 1 处且为切片 1px 级、锚/次区域零 fillRect)+ I11 黑名单(fx 域零触碰 legend/cursor/series)+ I3 反向钉(fx 域零 destroy/new uPlot/loading)+ 生效条件门(spawn 与 fx 装饰段逐帧复核 cfg.on、tail 域复核 cfg.tail)+ 收敛帧次区衔接(phase tail/fxTail/cfg.tail 门)+ 装饰帧保障行 + 次区相位分支在 _qbBeatFrame(装饰帧挂调度器循环, 无独立循环) + S4-a 轮 F1e/G9(§10 双轨探针「上传零粒子零环、下载有反馈」两面; F1 后静默面收窄为真 0/缺口轨): F1e 上轨真 0(target==0 -> level 0)时 lead=dl 真零轨不参与仲裁/act.up=false/act.dl=true/次区资格只 dl —— 与 F1d 缺口轨(live=false)互补的「live=true 但真 0」面; B3 追加 F1e2(F1 下限 spawn 消费面: 值>0 delta=0 恒 Lv.1 -> act/次区资格全开 + 装饰清单在场)与 G0(fx 主 clip 实参记账: 右缘放宽到画布右缘宽 840 + 上下缘放宽到画布上下缘(P6, [60,0,840,320]), 束体/锚段只右缘放宽 —— F5+P6)/G11(环心去钳制: P6 删旧 F5/P3 近底/近顶 clamp, 越下界 305/越上界 24.3 原样通过, 旧钳到 282/38 回潮即红)/G12(粒子底缘去镜像: 90° 单粒子 ps.y 越底 -> fill 顶点均值 = 真位, 旧折回值回潮即红); G9 绘制面计数(spawn 侧 alloc 照发 both 半套, spots 组装被 fx.act 门滤除 —— 真 0 注入态 13 vs 双活性对照 27(D5 基数), act 门删掉即翻倍) + 裁决轮追加 F1f/G10 并经评审 major 修正(calm 档零粒子: plan §04 原型 partCap 的 isCalm 口径, §10「克制档零粒子」原文补齐; 生产只采纳 calm 分量 —— 原型另有 leadLevel()<=1->0 门, Lv.1 发粒子系用户拍板维持现状/P9 未采纳; 唯一闸 = 绘制面 eff 逐帧门, spawn 恒满额清单与配色档解耦(F1f 钉, F8 同款 —— spawn 冻 palette 会让拍内切出 calm 余下冲击窗零粒子到下一拍才恢复且切片带 yCenter 漂移) + 拍内切 calm 下一帧零粒/切出恢复(G10 记账 ctx, neon 同参数 27 对照); isCalm 的 reduce 分量由 spawn 顶门 cfg.on !== true 承接) + 粒子三形态因子对齐模板(plan 26-11-26-0227 §3.2/S2): y 位移纵向压 0.7 椭圆喷雾(同帧同 ang, y 行程 = 0.7×x 行程同相 —— P9)/life = 1−t/T 线性衰减与 alpha 同源(alpha = 0.78×life×impact —— P10)+ 绘制侧 _qbFxPolyPath 半径 = size×life(旧恒定半径调用形态退役静态钉 —— P10 绘制接线)/边数 = 3+(i%3) 按清单序号轮换(伪随机分配退役, 序列漂移即红 —— P11)。无 node 静默跳过(同 _NODE_QB_TRAFFIC_PROBE 口径)
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

# 视觉引擎 V + N 层 node 电池(S2-a, plan 26-11-12-1139 §03 V 表/N 节/D1-D4): 常量/仲裁/预算/
# 粒子运动/清单确定性真跑。new Function 取出口径(同 _NODE_QB_BEAT_PROBE); 无 node 静默跳过。
_NODE_QB_FXVIS_PROBE = r"""
const fs = require("fs");
global.window = {};
const src = fs.readFileSync(process.argv[1], "utf8");
const {
  _QB_FX_LAYER_ORDER, _QB_FX_N_WHITELIST, _QB_FX_N_BLACKLIST, _QB_FX_LV_COLORS,
  _QB_FX_BLUR_CAPS, _QB_FX_RING_SIDES, _QB_FX_PART_MAX, _QB_FX_SHARD_MAX,
  _QB_FX_NEON_RATIO, _QB_FX_PART_RATIO, _QB_FX_RING_RATIO, _QB_FX_Y_GAP_PX, _QB_FX_SLICES_MAX,
  _QB_FX_SLICE_SHAKE_PX, _QB_FX_TAIL_PTS_MAX,
  _QB_FX_ANCHOR_SPIN_MS,
  _qbFxLead, _qbFxPartCap, _qbFxAlloc, _qbFxGapScale, _qbFxNeonQ, _qbFxRingAt,
  _qbFxParticleAt, _qbFxSpawnSpecs, _qbFxTearSlices, _qbFxRand,
} = new Function(src + "\nreturn { _QB_FX_LAYER_ORDER, _QB_FX_N_WHITELIST, _QB_FX_N_BLACKLIST,"
  + " _QB_FX_LV_COLORS, _QB_FX_BLUR_CAPS, _QB_FX_RING_SIDES, _QB_FX_PART_MAX, _QB_FX_SHARD_MAX,"
  + " _QB_FX_NEON_RATIO, _QB_FX_PART_RATIO, _QB_FX_RING_RATIO, _QB_FX_Y_GAP_PX, _QB_FX_SLICES_MAX,"
  + " _QB_FX_SLICE_SHAKE_PX, _QB_FX_TAIL_PTS_MAX, _QB_FX_ANCHOR_SPIN_MS,"
  + " _qbFxLead, _qbFxPartCap, _qbFxAlloc, _qbFxGapScale, _qbFxNeonQ, _qbFxRingAt,"
  + " _qbFxParticleAt, _qbFxSpawnSpecs, _qbFxTearSlices, _qbFxRand };")();
/* I9 逐元素窗常量(S2 模板保真二轮: 顶门最大窗 0.7 / 切片独立窗 0.25 / 束 fade 窗 0.7 —— 旧
 * 「0.55 单一顶门」退役; 常量未落时 EXTRA 取空由 ok() 判红, 不炸整探针) */
const EXTRA = (() => {
  try {
    return new Function(src + "\nreturn { _QB_FX_TOP_RATIO, _QB_FX_SLICE_RATIO, _QB_FX_BEAM_RATIO };")();
  } catch (e) { return {}; }
})();
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
ok("I11 白名单六元素逐字(判定线短亮段/环外圈/粒子外圈/锚辉光/Lv 徽标/数值光带辉光 bandHalo —— S2-b)",
  JSON.stringify(_QB_FX_N_WHITELIST)
  === JSON.stringify(["judgeFlash", "ringOuter", "partOuter", "anchorHalo", "lvBadge", "bandHalo"]));
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
ok("锚旋转周期常量 2639ms(C1/D6: 2πx420 取整 —— 模板 rot=t/420 一圈时长; CSS 接线/注释改写在后续阶段)",
  _QB_FX_ANCHOR_SPIN_MS === 2639);
// —— D. I9 预算常量(全部两轨合计) ——
ok("I9 预算常量: 粒子 32 / 半套 16 / N 0.33 / 粒子窗 0.55 / 环窗 0.6 / y 间距 26 / 切片 5 / 微震 3px / 光点 2(每轨, 全宽巡回 —— 旧末段 6 桶常量退役)",
  _QB_FX_PART_MAX === 32 && _QB_FX_SHARD_MAX === 16 && _QB_FX_NEON_RATIO === 0.33
  && _QB_FX_PART_RATIO === 0.55 && _QB_FX_RING_RATIO === 0.6 && _QB_FX_Y_GAP_PX === 26 && _QB_FX_SLICES_MAX === 5
  && _QB_FX_SLICE_SHAKE_PX === 3 && _QB_FX_TAIL_PTS_MAX === 2);
ok("I9 逐元素窗常量(模板保真二轮改判): 顶门最大窗 0.7 / 切片独立窗 0.25 / 束 fade 窗 0.7"
  + "(粒子 0.55 / 环 0.6 各自独立窗保留 —— 顶门只做最大窗粗滤, 逐元素窗在各自块内)",
  EXTRA._QB_FX_TOP_RATIO === 0.7 && EXTRA._QB_FX_SLICE_RATIO === 0.25 && EXTRA._QB_FX_BEAM_RATIO === 0.7);
// —— E. D3 lead 仲裁(argmax, 优先非缺口非静默轨) ——
const mkTr = (delta, level, live) => ({ prev: 100, target: 100, shown: 100, delta, level, live: live !== false });
ok("lead = argmax: up 0.5 > dl 0.3 -> up", _qbFxLead(mkTr(0.5, 3), mkTr(0.3, 2)) === "up");
ok("lead: dl 更大 -> dl", _qbFxLead(mkTr(0.1, 1), mkTr(0.4, 3)) === "dl");
ok("双轨皆静默(level 0) -> null(零装饰, L0/L1 照常 —— I10/D2)", _qbFxLead(mkTr(0.001, 0), mkTr(0.002, 0)) === null);
ok("缺口轨(live=false)不参与仲裁, 另一轨全量照常(D4)", _qbFxLead(mkTr(0.9, 3, false), mkTr(0.1, 1)) === "dl");
ok("delta 大但 level 0(静默)不参与(优先非静默轨)", _qbFxLead({ delta: 0.9, level: 0, live: true }, mkTr(0.1, 1)) === "dl");
ok("恰等 delta 取 up(稳定序)", _qbFxLead(mkTr(0.3, 2), mkTr(0.3, 2)) === "up");
// —— F. partCap(lead 等级 + 密度参数, 两轨合计上限; D5 基数 6+7×lv = 13/20/27, 模板 demo:911 同式) ——
ok("partCap 密度 0.7: Lv1 13x0.7=9 / Lv2 20x0.7=14 / Lv3 27x0.7=19(D5 基数 6+7lv)",
  _qbFxPartCap(1, 0.7) === 9 && _qbFxPartCap(2, 0.7) === 14 && _qbFxPartCap(3, 0.7) === 19);
ok("partCap 密度 1: Lv1 13 / Lv2 20 / Lv3 27(D5 模板基数; P9 兼容 Lv.1 仍发射)",
  _qbFxPartCap(3, 1) === 27 && _qbFxPartCap(1, 1) === 13 && _qbFxPartCap(2, 1) === 20);
ok("partCap 密度 0/负/NaN = 0 粒子(密度关到底即无粒子)",
  _qbFxPartCap(3, 0) === 0 && _qbFxPartCap(3, -0.5) === 0 && _qbFxPartCap(3, NaN) === 0);
ok("partCap 密度 >1 钳 1 / level 0 = 0 / 等级超 3 基数钳 Lv.3(D5: clamp 32 保留, 基数 27 触顶)",
  _qbFxPartCap(3, 1.7) === 27 && _qbFxPartCap(0, 1) === 0 && _qbFxPartCap(9, 1) === 27);
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
// —— J. 冲击扩张环(C3 模板式重写: pf=t/(0.6beat) 线性不 easeOut, r=(4+24pf)×rScale×gapScale,
//          alpha=0.85×(1−pf)×impact×rScale×gapScale, rScale 半套系数 both 0.5/lead 1/merge 1) ——
ok("ring t=0: r=4xrsxgs alpha=0.85ximpactxrsxgs(模板起步半径 4 —— C3)", (() => {
  const r = _qbFxRingAt(0, 1000, 1, 1, 1);
  return r && Math.abs(r.r - 4) <= 1e-12 && Math.abs(r.alpha - 0.85) <= 1e-12;
})());
ok("ring 线性扩张 pf=0.5: r=(4+12)xrsxgs / alpha=0.425ximpactxrsxgs(不 easeOut —— C3)", (() => {
  const r = _qbFxRingAt(300, 1000, 1, 1, 0.7);
  return r && Math.abs(r.r - 16) <= 1e-12 && Math.abs(r.alpha - 0.85 * 0.5 * 0.7) <= 1e-12;
})());
ok("ring 半套系数 both 0.5: r/alpha 各半(lead/merge 1 —— 模板 demo:1388-1390)", (() => {
  const b = _qbFxRingAt(300, 1000, 0.5, 1, 1);
  const g = _qbFxRingAt(300, 1000, 0.5, 0.5, 1);
  return b && g && Math.abs(b.r - 8) <= 1e-12 && Math.abs(b.alpha - 0.2125) <= 1e-12
    && Math.abs(g.r - 4) <= 1e-12 && Math.abs(g.alpha - 0.10625) <= 1e-12;
})());
ok("ring >=0.6×beat -> null(B3 环窗放宽 0.55->0.6)+ 负 t -> null",
  _qbFxRingAt(600, 1000, 1, 1, 1) === null && _qbFxRingAt(601, 1000, 1, 1, 1) === null
  && _qbFxRingAt(-1, 1000, 1, 1, 1) === null);
// —— K. V3 粒子三阶段(爆发 x4.5 / 拖尾减速透明 / 0.55×beat 后零绘制; alpha=0.78×(1−t/T)×impact
//          与 rot=t/260+idx 匀速单向系 C8 模板式 —— rot0/vr 字段退役) ——
const spec = { x0: 100, y0: 50, ang: Math.PI, dist: 100, size: 2, sides: 4 };
const IMP = 0.7;
const V = 100 / (4.5 * 120 + 430);   // beat 1000 / burst 120 / T 550: v = dist/(4.5×burst + trail)
ok("粒子 t=0: 原点起喷 alpha=0.78ximpact(首帧最亮与判定线闪光同帧 —— I9), rot=idx(t/260+idx —— C8)", (() => {
  const p = _qbFxParticleAt(0, 1000, 120, spec, 0, 3, IMP);
  return p && p.x === 100 && p.y === 50 && Math.abs(p.alpha - 0.78 * IMP) <= 1e-12
    && Math.abs(p.rot - 3) <= 1e-12;
})());
ok("爆发期速度 ×4.5: d(60) = 4.5v×60", (() => {
  const p = _qbFxParticleAt(60, 1000, 120, spec, 0, 0, IMP);
  const dExp = 4.5 * V * 60;
  return p && Math.abs(p.d - dExp) <= 1e-9 && Math.abs(p.x - (100 + Math.cos(Math.PI) * dExp)) <= 1e-9;
})());
ok("爆发/拖尾交接连续: d(burst) 恒 4.5v×burst", (() => {
  const p = _qbFxParticleAt(120, 1000, 120, spec, 0, 0, IMP);
  return p && Math.abs(p.d - 4.5 * V * 120) <= 1e-9;
})());
ok("拖尾期减速: 等距采样位移步单调收缩(easeOut 减速)", (() => {
  let prevStep = Infinity;
  let prevD = null;
  for (let t = 120; t < 550; t += 30) {
    const p = _qbFxParticleAt(t, 1000, 120, spec, 0, 0, IMP);
    if (prevD != null) {
      const step = p.d - prevD;
      if (step > prevStep + 1e-12) return false;
      prevStep = step;
    }
    prevD = p.d;
  }
  return true;
})());
ok("末态: d(T-1) 收敛到 dist / alpha(T/2)=0.78x0.5ximpact(C8) / t>=T -> null(0.55×beat 后零绘制)", (() => {
  const near = _qbFxParticleAt(549, 1000, 120, spec, 0, 0, IMP);
  const mid = _qbFxParticleAt(275, 1000, 120, spec, 0, 0, IMP);
  return near && Math.abs(near.d - 100) <= 1e-6 && mid && Math.abs(mid.alpha - 0.78 * 0.5 * IMP) <= 1e-12
    && _qbFxParticleAt(550, 1000, 120, spec, 0, 0, IMP) === null
    && _qbFxParticleAt(551, 1000, 120, spec, 0, 0, IMP) === null;
})());
ok("rot 匀速单向: rot(520,idx=0)=2 且 rot(520,idx=5)=7(t/260 —— C8 模板自旋; 不随种子漂移)", (() => {
  const a = _qbFxParticleAt(520, 1000, 120, spec, 0, 0, IMP);
  const b = _qbFxParticleAt(520, 1000, 120, spec, 0, 5, IMP);
  return a && b && Math.abs(a.rot - 2) <= 1e-12 && Math.abs(b.rot - 7) <= 1e-12;
})());
ok("impact 0/负/NaN -> alpha 0(不反放大; 窗内几何仍有效)", (() => {
  const p0 = _qbFxParticleAt(100, 1000, 120, spec, 0, 0, 0);
  const pn = _qbFxParticleAt(100, 1000, 120, spec, 0, 0, -0.5);
  const pN = _qbFxParticleAt(100, 1000, 120, spec, 0, 0, NaN);
  return p0 && pn && pN && p0.alpha === 0 && pn.alpha === 0 && pN.alpha === 0;
})());
ok("carryPx: 粒子随 L0 末点滑动(x 平移, 与曲线不脱钩)", (() => {
  const p = _qbFxParticleAt(60, 1000, 120, spec, -7, 0, IMP);
  const q = _qbFxParticleAt(60, 1000, 120, spec, 0, 0, IMP);
  return p && q && Math.abs((q.x - p.x) - 7) <= 1e-9;
})());
ok("粒子纵向压 0.7(P9, 模板 demo:1072 椭圆喷雾): 同帧同 ang, y 行程 = 0.7 x x 行程(sin/cos 同相; 旧正圆回潮即红)", (() => {
  const s45 = { x0: 100, y0: 50, ang: Math.PI / 4, dist: 100, size: 2, sides: 4 };
  const p = _qbFxParticleAt(60, 1000, 120, s45, 0, 0, IMP);
  const dx = p.x - 100, dy = p.y - 50;   // carryPx = 0
  return p && dx > 0 && dy > 0 && Math.abs(dy - 0.7 * dx) <= 1e-9;
})());
ok("life = 1 - t/T 线性衰减(P10, 模板 demo:1064): 起点 1 / 中点 0.5 / 单调递减, 且与 alpha 同源(alpha = 0.78 x life x impact)", (() => {
  const a = _qbFxParticleAt(0, 1000, 120, spec, 0, 0, IMP);
  const m = _qbFxParticleAt(275, 1000, 120, spec, 0, 0, IMP);
  const n = _qbFxParticleAt(549, 1000, 120, spec, 0, 0, IMP);
  let prev = Infinity;
  for (let t = 0; t < 550; t += 25) {
    const p = _qbFxParticleAt(t, 1000, 120, spec, 0, 0, IMP);
    if (!p || !(p.life < prev) || Math.abs(p.life - (1 - t / 550)) > 1e-12) return false;
    prev = p.life;
  }
  return a && a.life === 1 && m && Math.abs(m.life - 0.5) <= 1e-12
    && n && n.life > 0 && Math.abs(m.alpha - 0.78 * m.life * IMP) <= 1e-12;
})());
// —— L. 喷射清单(V3 多边形碎片) ——
ok("清单长度 = cap; 同种子恒同清单(同拍重绘不闪变)", (() => {
  const a = _qbFxSpawnSpecs(11, 0, 0, 29, 12345);
  const b = _qbFxSpawnSpecs(11, 0, 0, 29, 12345);
  return a.length === 11 && JSON.stringify(a) === JSON.stringify(b);
})());
ok("碎片三/四/五边(非圆点), 尺寸 1.6-4.2px(C8 模板式 1.6+rnd x 2.6; 上确界超旧式 3.5 —— 旧式回潮即红)", (() => {
  const specs = _qbFxSpawnSpecs(16, 0, 0, 29, 7);
  return specs.every((s) => s.sides >= 3 && s.sides <= 5 && s.size >= 1.6 && s.size <= 4.2)
    && Math.max(...specs.map((s) => s.size)) > 3.5;
})());
ok("rot0/vr 字段退役(C8: 自旋 = t/260+idx 绘制侧现算, 清单不含自旋字段)",
  _qbFxSpawnSpecs(8, 0, 0, 29, 5).every((s) => s.rot0 === undefined && s.vr === undefined));
ok("边数按清单序号 3/4/5 轮换(P11, 模板 demo:944 sides = 3+(i%3); 伪随机分配退役 —— 序列漂移即红)", (() => {
  const specs = _qbFxSpawnSpecs(7, 0, 0, 29, 7);
  return specs.every((s, i) => s.sides === 3 + (i % 3));
})());
ok("绘制尺寸 = size x life(P10 绘制接线): _qbFxPolyPath 半径随寿命缩小, 旧恒定半径调用形态退役(静态钉; P6 起 y 实参 = 粒子真位 ps.y)",
  src.includes("_qbFxPolyPath(ctx, ps.x, ps.y, sp.specs[i].size * ps.life,")
  && !src.includes("_qbFxPolyPath(ctx, ps.x, py, sp.specs[i].size,"));
ok("喷射角 360° 全向(P1, 模板 demo:941 TAU*(i+0.5)/n + (rnd-0.5)*0.6 弧度抖动 —— 旧左向 270° 弧回潮即红)", (() => {
  const n = 32;
  const specs = _qbFxSpawnSpecs(n, 0, 0, 29, 99);
  let min = Infinity, max = -Infinity;
  return specs.every((s, i) => {
    let d = s.ang - (Math.PI * 2 * (i + 0.5)) / n;
    d = ((d % (Math.PI * 2)) + Math.PI * 2) % (Math.PI * 2);
    if (d > Math.PI) d -= Math.PI * 2;
    if (Math.abs(d) > 0.3 + 1e-9) return false;   // 抖动 |d| <= 0.3rad
    min = Math.min(min, s.ang);
    max = Math.max(max, s.ang);
    return true;
  }) && max - min >= Math.PI * 2 - (Math.PI * 2 / n) - 0.6 - 1e-9;   // 覆盖全圆(容抖动收缩)
})());
ok("行程 = 1.1-1.6 x 环最大半径(无 maxDist 直调面 —— 桩/电池缺省不钳)",
  _qbFxSpawnSpecs(16, 0, 0, 40, 3).every((s) => s.dist >= 40 * 1.1 - 1e-9 && s.dist <= 40 * 1.6 + 1e-9));
ok("行程上限静态钳(P1/R6): maxDist 提供时 dist 钳到可用余量, 方向性/尺寸/确定性字段不变(生成时一次算定)", (() => {
  const clamped = _qbFxSpawnSpecs(16, 0, 0, 40, 3, 25);
  const natural = _qbFxSpawnSpecs(16, 0, 0, 40, 3);
  const loose = _qbFxSpawnSpecs(16, 0, 0, 40, 3, 1000);
  return clamped.every((s) => s.dist >= 0 && s.dist <= 25 + 1e-9)
    && clamped.some((s) => Math.abs(s.dist - 25) <= 1e-9)
    && clamped.every((s, i) => s.ang === natural[i].ang && s.size === natural[i].size
      && s.sides === natural[i].sides && Math.abs(s.dist - Math.min(natural[i].dist, 25)) <= 1e-9)
    && loose.every((s, i) => s.dist === natural[i].dist);
})());
ok("不同种子清单不同(跨拍随尾桶时刻自然变化)",
  JSON.stringify(_qbFxSpawnSpecs(8, 0, 0, 29, 1)) !== JSON.stringify(_qbFxSpawnSpecs(8, 0, 0, 29, 2)));
// —— M. R6 撕裂切片(S2-b 重写; 完整面在 scan_band 电池; C2/D3: 微震回 x 向 offX, dy0/ph 退役) ——
ok("切片 Lv.3 5 条, |offX| <= 3px(x 向微震幅值 <=5px 上限 —— C2/D3), dy0/ph 字段退役, len 10-80(R6), 同参数恒同清单", (() => {
  const a = _qbFxTearSlices(3, 100, 40, 0.5, 42, "linked", 10, 310);
  const b = _qbFxTearSlices(3, 100, 40, 0.5, 42, "linked", 10, 310);
  return a.length === 5 && JSON.stringify(a) === JSON.stringify(b)
    && a.every((s) => Math.abs(s.offX) <= 3 && s.dy0 === undefined && s.ph === undefined
      && s.len >= 10 && s.len <= 80);
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
const { methods, _qbFxHash01, _qbFxStrat } =
  new Function(src + "\nreturn { methods: window.AQB_QB_TRAFFIC.methods, _qbFxHash01, _qbFxStrat };")();
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
function mkBeat(anchor, step, span, upShown, dlShown) {
  return {
    raf: 0, anim: null, anchor, step, span,
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
  u._qbBeat = mkBeat(1120, 30, 120, 10, 55);
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  const fx = u._qbBeat.anim && u._qbBeat.anim.fx;
  ok("F1a 判定帧起 fx(phase=impact) + lead=up Lv.3", u._qbBeat.anim && u._qbBeat.anim.phase === "impact"
    && fx && fx.lead === "up" && fx.lv === 3);
  ok("F1a both 分配: cap 27(D5 基数 6+7lv) -> 14/13, 清单各 14/13(两轨合计不翻倍 —— I9)",
    fx && fx.cap === 27 && fx.alloc.up === 14 && fx.alloc.dl === 13
    && fx.specs.up.length === 14 && fx.specs.dl.length === 13);
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
  u._qbBeat = mkBeat(1120, 30, 120, 10, 55);
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
  u._qbBeat = mkBeat(1120, 30, 120, 10, 55);
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  ok("F1c reduce 短路: 零 rAF 零 anim(退回快路)", rafMap.size === 0 && u._qbBeat.anim === null);
  global.window.AQB_FX_CFG = CFG;
}
// —— F1d: 缺口轨(dl null): lead 单轨, 另一轨零反馈(D4/I10) ——
{
  const u = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, null]);
  u._qbBeat = mkBeat(1120, 30, 120, 10, 55);
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
// —— F1e: 上轨真 0(target==0 -> level 0) + 下载 Lv.3(§10 双轨探针「上传零粒子零环、下载有反馈」
//          的 spawn 面; 与 F1d 缺口轨互补 —— 那是 live=false, 这是 live=true 但真 0, both 半套
//          分不到静默轨全靠 act 门)。F1(plan 26-11-14-1313)后「live 且 delta=0」不再静默(值>0
//          恒 >=Lv.1), 静默面收窄为真 0/缺口轨 —— 原形态(上轨尾值 30>0 delta=0)改由 F1e2 钉。 ——
{
  const u = mkU(XS1, [0, 0, 0, 0, 0], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1120, 30, 120, 0, 10);  // up 尾值 0(真 0 -> Lv.0 静默), dl 10->60(delta 0.5 -> Lv.3)
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  const fx = u._qbBeat.anim && u._qbBeat.anim.fx;
  ok("F1e 上真 0 下 Lv.3: lead=dl(真 0 轨不参与仲裁) + act.up=false(零粒子零环) + act.dl=true"
    + " + 次区资格只 dl(I10/D2)",
    !!fx && fx.lead === "dl" && fx.lv === 3 && fx.act.up === false && fx.act.dl === true
    && fx.tail.length === 1 && fx.tail[0] === "dl");
  drain();
  ok("F1e 收敛落地", u.data[1][4] === 0 && u.data[2][4] === 60 && u._qbBeat.anim === null);
}
// —— F1e2: F1 下限的 spawn 消费面(值>0 恒 >=Lv.1): 上轨尾值 30 与显示值相同(旧口径会静默),
//          现恒 Lv.1 -> act/次区资格全开 + 装饰清单在场(A1 稳态流每拍反馈的 spawn 等价面) ——
{
  const u = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1120, 30, 120, 30, 10);  // up 尾值 30 与显示值 30 相同(delta=0 -> Lv.1 下限), dl 10->60 Lv.3
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  const fx = u._qbBeat.anim && u._qbBeat.anim.fx;
  ok("F1e2 值>0 恒 >=Lv.1: act.up=true(零变化活跃轨也出环/粒子) + act.dl=true + 次区资格双轨"
    + " + lead=dl( Lv.3 大 Δ 仍主导仲裁 —— 下限不改变上限语义)",
    !!fx && fx.lead === "dl" && fx.lv === 3 && fx.act.up === true && fx.act.dl === true
    && fx.tail.length === 2 && fx.specs.up.length === 14);
  drain();
  ok("F1e2 收敛落地", u.data[1][4] === 30 && u.data[2][4] === 60 && u._qbBeat.anim === null);
}
// —— F1f: calm 档 spawn 满额解耦(评审 major 修正: calm 门只在绘制侧 eff —— spawn 恒满额清单,
//          与 F8 密度解耦/切片无条件生成同款先例。spawn 侧冻 palette 的两个破绽: calm 判定帧
//          specs 全不建后拍内切出 calm, 余下冲击窗零粒子到下一拍才恢复(违 §05.3「立即; 粒子池
//          重建」); alloc.merge=0 把切片带 yCenter 退 lead 末点 y。零粒子落笔的唯一闸 = 绘制面
//          eff 逐帧门, 由 G10 记账 ctx 钉) ——
{
  global.window.AQB_FX_CFG = Object.assign({}, CFG, { palette: "calm" });
  const u = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1120, 30, 120, 10, 55);
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  const fx = u._qbBeat.anim && u._qbBeat.anim.fx;
  ok("F1f calm 判定帧: spawn 满额清单与配色档解耦(cap=partCap(lv,1)=27 —— D5 基数, specs.up/dl 各 14/13,"
    + " slices/comb 照建), lead/lv 仲裁照旧",
    !!fx && fx.cap === 27 && !!fx.specs.up && fx.specs.up.length === 14
    && !!fx.specs.dl && fx.specs.dl.length === 13 && fx.slices.length === 5
    && fx.comb.length === 7 && fx.lead === "up" && fx.lv === 3);
  drain();
  ok("F1f calm 收敛落地(L0/L1 不受配色档影响)", u.data[1][4] === 30 && u.data[2][4] === 60
    && u._qbBeat.anim === null);
  global.window.AQB_FX_CFG = CFG;
}
// —— F2: D3 三策略落 fx 清单 ——
{
  global.window.AQB_FX_CFG = Object.assign({}, CFG, { dual: "lead" });
  const u = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1120, 30, 120, 10, 55);
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  let fx = u._qbBeat.anim.fx;
  ok("F2 lead 策略: 主导轨全套 27(D5 基数), 从属零清单", fx && fx.alloc.up === 27 && fx.alloc.dl === 0
    && fx.specs.up.length === 27 && fx.specs.dl === undefined);
  drain();
  global.window.AQB_FX_CFG = Object.assign({}, CFG, { dual: "merge" });
  const u2 = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u2._qbBeat = mkBeat(1120, 30, 120, 10, 55);
  self._qbCharts = { global: u2 };
  self._qbBeatStart("global", u2);
  fx = u2._qbBeat.anim.fx;
  ok("F2 merge 策略: 中点一次 merge=27(D5 基数; 原点 y = 两轨 y 中点), 双轨零清单",
    fx && fx.alloc.merge === 27 && fx.alloc.up === 0 && fx.specs.merge.length === 27
    && fx.specs.up === undefined
    && Math.abs(fx.specs.merge[0].y0 - (10 + 300 * (1 - ((10 + 55) / 2) / 63))) <= 1e-9);
  drain();
  global.window.AQB_FX_CFG = CFG;
}
// —— F3: D4 末点 y 间距缩小(实测) ——
{
  const u = mkU(XS1, [0, 0, 0, 0, 32.73], [0, 0, 0, 0, 35]);
  u._qbBeat = mkBeat(1120, 30, 120, 30, 32.73);
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
// —— F4: converge 起步 t=0(impact 窗 L1 已移动) + 零 Δ 拍装饰帧保障(无 shift 长窗零提交帧强制重绘) ——
{
  const xs = Array.from({ length: 2880 }, (_, i) => 1000 + i * 30);
  const up = new Array(2880).fill(0);
  up[2879] = 30;
  const dl = new Array(2880).fill(0);
  const u = mkU(xs, up, dl);
  u._qbBeat = mkBeat(87340, 30, 86400, 10, 0);
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  ok("F4-a 前置: 无 shift 长窗 gate 拒绝 -> 瞬时落地目标锚视口恰一次 x+y([970,87370] —— 旧"
    + " auto 落地面随显式视口退役, 长窗恒定压缩变体随补点退役消失) + fx 在",
    u.setScaleLog.length === 2 && u.setScaleLog[0][0] === "x"
    && u.setScaleLog[0][1] === 970 && u.setScaleLog[0][2] === 87370
    && u._qbBeat.anim && !!u._qbBeat.anim.fx);
  for (let i = 0; i < 2; i++) { nowMs += 50; pump(); }   // clock 0/50: 50 < impact 120
  ok("F4-a converge t=0 起步: impact 窗内 L1 已开始移动(shown 10 -> >10, 不再钉 prev), L0 gate"
    + " 拒绝零新增 x 提交", u.data[1][2879] > 10 && u.data[1][2879] < 30
    && u.setScaleLog.filter((r) => r[0] === "x").length === 1);
  drain();
  ok("F4-a 收敛落地(cfg.tail=false 无次区)", u.data[1][2879] === 30 && u._qbBeat.anim === null);
  // 零变化拍: 两轨 prev==target -> needsTail=false, L0 gate 拒绝 -> L0/L1 全零提交,
  // 装饰帧保障分支必须仍在(否则粒子/环/切片冻结在 t=0 帧)。
  const u2 = mkU(xs, up, dl);
  u2._qbBeat = mkBeat(87340, 30, 86400, 30, 0);
  self._qbCharts = { global: u2 };
  self._qbBeatStart("global", u2);
  ok("F4-b 前置: 零变化拍 fx 仍在(F1 下限 Lv.1)且 needsShift/needsTail 双 false",
    !!u2._qbBeat.anim && !!u2._qbBeat.anim.fx && u2._qbBeat.anim.fx.lv === 1
    && !u2._qbBeat.anim.needsShift && !u2._qbBeat.anim.needsTail);
  for (let i = 0; i < 2; i++) { nowMs += 50; pump(); }   // clock 0/50: 零提交帧
  ok("F4-b 装饰帧保障仍在: 零 Δ 拍 L0/L1 零提交帧强制重绘(粒子不冻结在 t=0) + y 钉成对 31.5",
    u2.redrawCount === 2 && u2.setScaleLog.length === 4
    && u2.setScaleLog.slice(2).every((r) => r[0] === "y" && r[2] === 31.5));
  drain();
  ok("F4-b 零变化拍收敛落地(尾点零改写)", u2.data[1][2879] === 30 && u2._qbBeat.anim === null);
}
// —— F5: 次区相位全生命周期(衔接/全宽巡回光点/1px 量化去重/收尾) ——
{
  global.window.AQB_FX_CFG = Object.assign({}, CFG, { tail: true });
  const xs = Array.from({ length: 2880 }, (_, i) => 1000 + i * 30);
  const up = new Array(2880).fill(0);
  up[2879] = 30;
  const dl = new Array(2880).fill(0);
  dl[2879] = 20;
  const u = mkU(xs, up, dl);
  u._qbBeat = mkBeat(87340, 30, 86400, 10, 5);
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  for (let i = 0; i < 13; i++) { nowMs += 50; pump(); }   // clock 600: 收敛帧
  ok("F5 收敛帧转次区相位(tail=true + 双轨活性) + 真值已落袋", u._qbBeat.anim
    && u._qbBeat.anim.phase === "tail" && u.data[1][2879] === 30 && u.data[2][2879] === 20);
  // 1px 量化去重零空转: 同一相位时钟连调两次, 第二次 sig 不变不提交(sig 比较行删除即红)
  {
    const a = u._qbBeat.anim;
    const r0 = u.redrawCount;
    self._qbTailFrame.call(self, u, a);
    const r1 = u.redrawCount;
    self._qbTailFrame.call(self, u, a);
    const r2 = u.redrawCount;
    ok("F5 1px 量化去重零空转: 同 clock 再调用不提交(sig 行删即红)",
      r1 > r0 && r2 === r1 && !!a.fxTail.sig && a.fxTail.pts.length > 0);
  }
  const seen = { pts: 0, minX: Infinity, maxX: -Infinity, bad: false };
  let guard = 0;
  while (rafMap.size && guard++ < 200) {
    nowMs += 50;
    pump();
    const a = u._qbBeat.anim;
    if (a && a.phase === "tail" && a.fxTail.pts && a.fxTail.pts.length) {
      if (a.fxTail.pts.length > seen.pts) seen.pts = a.fxTail.pts.length;
      for (const pt of a.fxTail.pts) {
        if (!(pt.alpha > 0 && pt.alpha <= 0.3)) seen.bad = true;
        if (!(pt.x >= 60 && pt.x <= 860 && pt.y >= 10 && pt.y <= 310)) seen.bad = true;
        if (pt.x < seen.minX) seen.minX = pt.x;
        if (pt.x > seen.maxX) seen.maxX = pt.x;
      }
    }
  }
  ok("F5 次区光点: <=2/轨 合计 <=4, alpha 0.3×(1−qt) <=0.3, 位置在绘图区内(极轻 —— I9/G2)",
    seen.pts > 0 && seen.pts <= 4 && !seen.bad);
  ok("F5 全宽巡回(C5): 光点 x 跨越多段而非仅末段 6 桶(旧末段扫过只近右缘即红)",
    seen.maxX - seen.minX > 120 && seen.minX < 620);
  ok("F5 次区收尾: 窗尽 anim null(下一拍前静默, tail=min(period-beat,2000) 非常驻)",
    u._qbBeat.anim === null && rafMap.size === 0);
  global.window.AQB_FX_CFG = CFG;
}
// —— F6: 拍内关 tail: 下一帧收尾 ——
{
  global.window.AQB_FX_CFG = Object.assign({}, CFG, { tail: true });
  const u = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1120, 30, 120, 10, 55);
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
  u._qbBeat = mkBeat(1120, 30, 120, 10, 55);
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  const fx = u._qbBeat.anim && u._qbBeat.anim.fx;
  const yMax = 31.5;   // dl 缺口 -> 全窗真值峰 30 x1.05
  const yMerge = 10 + 300 * (1 - 10 / yMax);   // yOf(up.shown=10)
  ok("F7 merge+缺口轨: specs.merge[0].y0 === yOf(lead.shown)(假中点 = (yMerge+310)/2 即红)",
    fx && fx.specs.merge && fx.specs.merge.length === 27
    && Math.abs(fx.specs.merge[0].y0 - yMerge) <= 1e-9
    && Math.abs(fx.specs.merge[0].y0 - (yMerge + 310) / 2) > 1);
  const halfBand7 = (0.08 + 0.30 * Math.min(1, 2 / 0.5)) * 300;   // R6 撕裂带: Δ=2 -> pow=1 -> ±114
  ok("F7 切片锚带中心同退 lead 末点 y(R6 撕裂带 ±(0.08+0.30×min(1,Δ/0.5))×H 内, 钳绘图区)"
    + " + 清单无条件生成(palette=neon 也有 —— 修复4)",
    fx && fx.slices && fx.slices.length === 5
    && fx.slices.every((s) => s.y >= Math.max(12, yMerge - halfBand7 - 1e-9)
      && s.y <= Math.min(307, yMerge + halfBand7 + 1e-9)));
  drain();
  global.window.AQB_FX_CFG = CFG;
}
// —— F8: 密度解耦(评审修复3): spawn 满额清单(= partCap(lv,1)), 与拍内 cfg.particles 无关 ——
//    密度/dual 拍内改参由绘制侧逐帧重算 + 钳制生效, cap 冻结会让改密度整拍失效(违 §05.3/D21) ——
{
  global.window.AQB_FX_CFG = Object.assign({}, CFG, { particles: 0.4 });
  const u = mkU(XS1, [0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeat(1120, 30, 120, 10, 55);
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  const fx = u._qbBeat.anim && u._qbBeat.anim.fx;
  ok("F8 密度 0.4 仍满额清单 14/13(cap 27 = partCap(lv,1) —— D5 基数, 清单长度与密度解耦)",
    fx && fx.cap === 27 && fx.specs.up.length === 14 && fx.specs.dl.length === 13);
  drain();
  global.window.AQB_FX_CFG = CFG;
}
// —— F9: R6 撕裂带 spawn 侧对称紧断言(评审 minor4: 半带系数 0.08/0.30 与 /0.5 归一变异即红) ——
//    夹具: up prev=31.5 -> target=60(delta=0.90476 -> Lv.3 -> n=5, pow=1), dl 静默; dmax=60 ->
//    yMax=63, 撕裂带中心 yOf(31.5)=160, 半带=(0.08+0.30x1)x300=114 -> 带 [46,274] 全在绘图区内
//    (无钳边干扰), 逐条 y 可按 spawn 同式复算(strat x hash01(seed=1150, slot))。
{
  global.window.AQB_FX_CFG = CFG;
  const u = mkU(XS1, [0, 0, 0, 0, 60], [0, 0, 0, 0, 40]);
  u._qbBeat = mkBeat(1120, 30, 120, 31.5, 40);
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  const fx = u._qbBeat.anim && u._qbBeat.anim.fx;
  const yC9 = 10 + 300 * (1 - 31.5 / 63);          // = 160
  const half9 = (0.08 + 0.30 * Math.min(1, (60 - 31.5) / 31.5 / 0.5)) * 300;   // = 114
  const n9 = 5;
  const exp9 = [];
  for (let i = 0; i < n9; i++) {
    const raw = yC9 + (_qbFxStrat(i, n9, _qbFxHash01(1150, i * 13 + 3)) - 0.5) * 2 * half9;
    exp9.push(Math.max(12, Math.min(307, raw)));
  }
  ok("F9 撕裂带 spawn 公式逐条紧断言(halfBand=(0.08+0.30xmin(1,delta/0.5))xH + strat x hash01(尾桶,slot) + 带内钳边 —— 半带系数/归一分母/槽位变异即红)",
    fx && fx.slices && fx.slices.length === 5
    && fx.slices.every((s, i) => Math.abs(s.y - exp9[i]) <= 1e-9)
    && fx.comb && fx.comb.length === 7
    && fx.comb.every((c) => c.y >= 12 && c.y <= 307));
  drain();
  global.window.AQB_FX_CFG = CFG;
}
// —— F10: C11 梳齿 fixed 档条数(fixed 恒 7 —— 模板 demo:1212 对照档; linked 仍 3/5/7 按等级) ——
//    夹具: up 30->31(delta=1/30≈0.033 -> Lv.1 lead), dl 55->56(delta≈0.018 Lv.1)—— linked Lv.1
//    梳齿 3, fixed 档恒 7, 两臂差 4 条即 C11 的判别面(旧口径 fixed 只冻随机源条数仍随等级)。 ——
{
  const FIXED_UP = [0, 0, 0, 0, 31];
  const FIXED_DL = [0, 0, 0, 0, 56];
  global.window.AQB_FX_CFG = Object.assign({}, CFG, { tear: "fixed" });
  const u = mkU(XS1, FIXED_UP, FIXED_DL);
  u._qbBeat = mkBeat(1120, 30, 120, 30, 55);
  self._qbCharts = { global: u };
  self._qbBeatStart("global", u);
  const fx = u._qbBeat.anim && u._qbBeat.anim.fx;
  ok("F10 梳齿 fixed 档恒 7(C11 模板对照档; lead=Lv.1 —— 条数不再随等级)",
    fx && fx.lead === "up" && fx.lv === 1 && fx.comb && fx.comb.length === 7);
  drain();
  global.window.AQB_FX_CFG = Object.assign({}, CFG, { tear: "linked" });
  const u2 = mkU(XS1, FIXED_UP, FIXED_DL);
  u2._qbBeat = mkBeat(1121, 30, 120, 30, 55);
  self._qbCharts = { global: u2 };
  self._qbBeatStart("global", u2);
  const fx2 = u2._qbBeat.anim && u2._qbBeat.anim.fx;
  ok("F10 对照: linked 档 Lv.1 仍 3(条数表不动 —— C11 只改 fixed 档)",
    fx2 && fx2.comb && fx2.comb.length === 3);
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
const { methods, _qbFxSpawnSpecs, _qbFxTearSlices, _qbFxComb, _qbFxRingAt, _qbFxParticleAt } =
  new Function(src + "\nreturn { methods: window.AQB_QB_TRAFFIC.methods,"
  + " _qbFxSpawnSpecs, _qbFxTearSlices, _qbFxComb, _qbFxRingAt, _qbFxParticleAt };")();
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);
/* 记账式 2d ctx: 只记不画。shadowBlur 用 getter/setter 截获每次赋值(含清零), stroke 时若
 * _blur > 0 记一次「带 blur 的 stroke」(I9 同帧 <=3 次预算的观测面), ops 记路径点(M/L);
 * createLinearGradient 记账(S2-b: T2 光带/束包络/回声走渐变描边 —— strokeVals 收对象引用,
 * 「渐变笔」观测面 = strokeVals 里的对象; S2-b 评审修复: 构造坐标也记录 —— 丢坐标会让
 * 渐变方向变异静默存活); rect/clip 记实参(评审 major: 无裁剪前提下的计数/落笔断言是盲区);
 * canvas 桩宽 900(绘图区右缘 860 -> 判定线右侧留白 40px —— 束体宽 clip 的可见域)。 */
function mkCtx() {
  const ctx = {
    blurSets: [], strokeVals: [], strokeMeta: [], fillRects: [], fillTexts: [], fillAlphas: [], ops: [],
    rects: [], clips: [], grads: [],
    strokesWhileBlur: 0, fillCnt: 0, saveCnt: 0, restoreCnt: 0,
    _blur: 0, shadowColor: "", globalAlpha: 1,
    strokeStyle: "", fillStyle: "", lineWidth: 1, font: "", textAlign: "", textBaseline: "",
    canvas: { width: 900, height: 320 },   // P6: 画布上下缘入桩(绘图区 [10,310], 画布 [0,320])
    beginPath() {}, closePath() {}, arc() {},
    rect(x, y, w, h) { this.rects.push([x, y, w, h]); },
    clip() { this.clips.push(this.rects[this.rects.length - 1] || null); },
    scale() {}, save() { this.saveCnt++; }, restore() { this.restoreCnt++; }, setLineDash() {},
    moveTo(x, y) { this.ops.push([x, y, "M"]); },
    lineTo(x, y) { this.ops.push([x, y, "L"]); },
    stroke() {
      if (this._blur > 0) this.strokesWhileBlur++;
      this.strokeVals.push(this.strokeStyle);
      this.strokeMeta.push({ style: this.strokeStyle, alpha: this.globalAlpha, w: this.lineWidth });
    },
    fill() { this.fillCnt++; this.fillAlphas.push(this.globalAlpha); },
    fillRect(x, y, w, h) { this.fillRects.push([x, y, w, h]); },
    fillText(s, x, y) { this.fillTexts.push({ s: String(s), font: this.font, alpha: this.globalAlpha, x, y }); },
    createLinearGradient(x0, y0, x1, y1) {
      const g = { coords: [x0, y0, x1, y1], stops: [],
        addColorStop(p, c) { g.stops.push([p, c]); } };
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
    slices: _qbFxTearSlices(3, yOfT(10), 40, 0.5, 7, "linked", 10, 310),
    comb: _qbFxComb(7, 100, 260, 0.5, 7, "linked", 10, 310),
    tail: ["up", "dl"],
    act: { up: true, dl: true },
    pxPerT: 0.5, dx0: 0, beatMs: 1000, burstMs: 120,
  }, over || {});
}
const TK = { up: "#UP", down: "#DN", grid: "#GRID", gap: "#GAP", axis: "#AXIS" };
const CFG0 = { enabled: true, on: true, shiftRatio: 0.6, neon: true, particles: 1, tail: false,
  dual: "both", palette: "neon", impact: 0.7, echoSpan: "auto", tear: "linked",
  layers: { band: true, particles: true, scan: true, grade: true } };
global.window.AQB_FX_CFG = CFG0;
const draw = (u) => methods._qbDrawFx.call(methods, u, TK);
const drawAnchor = (u) => methods._qbDrawFxAnchor.call(methods, u, TK);
const drawGlow = (u) => methods._qbDrawFxCurveGlow.call(methods, u, TK);
const at = (u, t) => { u._qbBeat.anim.clock = t; draw(u); };
// —— G0: 裁剪面实参记账(F5 + P6, plan 26-11-26-0227 §03.3): fx 段主 clip 右缘放宽到画布右缘
//    (canvas 桩宽 900 -> 宽 840)且上下缘放宽到画布上下缘(桩高 320 -> y=0/高 320 —— P6 仿 F5
//    先例, 贴边环/粒子不被裁; 张力处置: 允许画到画布留白不压轴标签, 静态钉钉「上下缘=画布
//    缘且不铺底」), 束体自含 clip 只放宽右缘(上下缘不动, [10,300]); 锚段 clip 右缘放宽不动
//    (P6 只动 _qbDrawFx 装饰主 clip) ——
{
  const u = mkDrawU([0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeatSt(LIVE_UP, LIVE_DL);
  u._qbBeat.anim = mkAnim(mkFx());
  draw(u);
  ok("G0 fx 段 clip 实参: 恰 2 笔(fx 主 clip + 束体自含 clip); 主 clip = [60, 0, 840, 320](F5 右缘 + P6 上下缘=画布上下缘), 束体 = [60, 10, 840, 300](只右缘放宽)",
    u.ctx.clips.length === 2 && JSON.stringify(u.ctx.clips[0]) === JSON.stringify([60, 0, 840, 320])
    && JSON.stringify(u.ctx.clips[1]) === JSON.stringify([60, 10, 840, 300]));
  const u2 = mkDrawU([0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u2._qbBeat = mkBeatSt(LIVE_UP, LIVE_DL);
  u2._qbBeat.anim = mkAnim(mkFx());
  drawAnchor(u2);
  ok("G0 锚段 clip 实参: 恰 1 笔且右缘放宽到画布右缘(F5 —— 末点贴判定线的菱形锚右半不再被切; P6 不动锚段)",
    u2.ctx.clips.length === 1 && JSON.stringify(u2.ctx.clips[0]) === JSON.stringify([60, 10, 840, 300]));
}
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
// —— G4: cfg.neon=false 白名单断言面收窄(S2 模板保真二轮 D7/I11 例外注记: lvBadge 常显与判定
//          帧全高冲击闪光不挂 neon 门、色走 Lv 表; 余晖线仍在门内待 S4 移出) —— 环外圈辉光/
//          短亮段/粒子外圈/小菱形仍零落笔 ——
{
  global.window.AQB_FX_CFG = Object.assign({}, CFG0, { neon: false });
  const lv = "#FF6BD6";   // Lv.3
  const u = mkDrawU([0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeatSt(LIVE_UP, LIVE_DL);
  u._qbBeat.anim = mkAnim(mkFx());
  draw(u);
  ok("G4 neon=false 收窄面: lvBadge 常显(fillText 恰 1 = 'Lv.3 · lead 上传', 11px, alpha 0.85 无 q 衰减,"
    + " 位置右对齐 x=L+W-4=856 / y=T+4=14 —— C9)"
    + " + 冲击闪光在(rgba Lv 色 lw2 恰 1 笔 —— 不挂 neon 门 D7)"
    + " + 环外圈辉光/短亮段/粒子外圈零 Lv 直色落笔(blur 恒 0)",
    u.ctx.fillTexts.length === 1 && u.ctx.fillTexts[0].s === "Lv.3 · lead 上传"
    && u.ctx.fillTexts[0].font.indexOf("11px") >= 0 && u.ctx.fillTexts[0].alpha === 0.85
    && u.ctx.fillTexts[0].x === 856 && u.ctx.fillTexts[0].y === 14
    && u.ctx.blurSets.every((v) => v === 0)
    && u.ctx.strokeMeta.filter((s) => s.style === lv).length === 0
    && u.ctx.strokeMeta.filter((s) => s.w === 2 && String(s.style).indexOf("255,107,214") >= 0).length === 1);
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
  const hi = [yOfT(20), yOfT(25)];   // 加亮段落这两桶(末 3 桶窗)
  const seg = u.ctx.ops.filter((o) => hi.some((y) => Math.abs(o[1] - y) < 1e-6));
  ok("G5 加亮缺口 [20,null,25]: moveTo+moveTo 零 lineTo 桥接(gap 后重新起笔 —— spanGaps:false 同款)",
    seg.length === 2 && seg.every((o) => o[2] === "M"));
  const ug = mkDrawU([0, 0, 0, 0, 30], [null, null, 20, null, 25]);
  ug._qbBeat = mkBeatSt(LIVE_UP, LIVE_DL);
  ug._qbBeat.anim = mkAnim(fxLead);
  drawGlow(ug);   // 曲线辉光缺口断段同验(缺陷一+二重构后辉光在独立常驻函数, 不在锚段)
  const gseg = ug.ctx.ops.filter((o) => hi.some((y) => Math.abs(o[1] - y) < 1e-6));
  ok("G5 曲线辉光缺口 [20,null,25]: 同款 moveTo+moveTo 断段零桥接(常驻段独立记账)",
    gseg.length === 2 && gseg.every((o) => o[2] === "M"));
  const u2 = mkDrawU([0, 0, 0, 0, 30], [null, null, 20, 22, 25]);
  u2._qbBeat = mkBeatSt(LIVE_UP, LIVE_DL);
  u2._qbBeat.anim = mkAnim(fxLead);
  drawAnchor(u2);
  const hi2 = [yOfT(20), yOfT(22), yOfT(25)];
  const seg2 = u2.ctx.ops.filter((o) => hi2.some((y) => Math.abs(o[1] - y) < 1e-6));
  ok("G5 对照连续 [20,22,25]: 加亮段 moveTo + lineTo x2(逐段描边原样)",
    seg2.length === 3 && seg2[0][2] === "M" && seg2[1][2] === "L" && seg2[2][2] === "L");
  const ug2 = mkDrawU([0, 0, 0, 0, 30], [null, null, 20, 22, 25]);
  ug2._qbBeat = mkBeatSt(LIVE_UP, LIVE_DL);
  ug2._qbBeat.anim = mkAnim(fxLead);
  drawGlow(ug2);
  const gseg2 = ug2.ctx.ops.filter((o) => hi2.some((y) => Math.abs(o[1] - y) < 1e-6));
  ok("G5 曲线辉光对照连续 [20,22,25]: moveTo + lineTo x2(逐段描边原样)",
    gseg2.length === 3 && gseg2[0][2] === "M" && gseg2[1][2] === "L" && gseg2[2][2] === "L");
  global.window.AQB_FX_CFG = CFG0;
}
// —— G6: 密度拍内即时(修复3): 逐帧 partCap 现算, 拍内改 cfg.particles 下一帧粒子数即变 ——
{
  const u = mkDrawU([0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeatSt(LIVE_UP, LIVE_DL);
  u._qbBeat.anim = mkAnim(mkFx());   // 满额清单 16/16(spawn 夹具; 绘制侧 eff 按密度现算)
  global.window.AQB_FX_CFG = Object.assign({}, CFG0, { particles: 0.4 });
  at(u, 100);
  const low = u.ctx.fillCnt;   // round(27x0.4)=11 -> both 6+5
  u.ctx = mkCtx();
  global.window.AQB_FX_CFG = Object.assign({}, CFG0, { particles: 1 });
  at(u, 100);
  const full = u.ctx.fillCnt;   // 27 = partCap(3,1)(D5 基数) -> both 14+13
  u.ctx = mkCtx();
  global.window.AQB_FX_CFG = Object.assign({}, CFG0, { particles: 0.1 });
  at(u, 100);
  const lower = u.ctx.fillCnt;   // round(2.7)=3 -> both 2+1
  global.window.AQB_FX_CFG = CFG0;
  ok("G6 密度即时: 同拍内 0.4 -> 15(11 粒+2 菱形 C10+2 判定线小菱形 P4) / 1 -> 31(27 粒 D5+2+2) /"
    + " 0.1 -> 7(3 粒+2+2)(下一帧生效; +4 = neon 块每活性轨 C10 小菱形 1 枚 + P4 判定线小菱形 1 枚,"
    + " 粒子差值面不变)",
    low === 15 && full === 31 && lower === 7);
}
// —— G7: 切片门 C2(glitch || lv>=2)+ 厚 1.5(Lv.3 2.0; fixed 3)+ 独立窗 0.25×beat(S2 模板保真
//          二轮; x 向 ±3q 与 alpha 联 impact 已在 S1)—— 束体梳齿也是 1px 级 fillRect 且在
//          x >= 判定线(860)域 —— 切片计数按 x < 860 滤除 ——
{
  // Arm A: neon 档 Lv.3 -> 门开(lv>=2 —— 不再 glitch 唯一门), 5 条 2px 级(Lv.3 厚 2.0)
  const u = mkDrawU([0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeatSt(LIVE_UP, LIVE_DL);
  u._qbBeat.anim = mkAnim(mkFx());
  at(u, 100);
  const slA = u.ctx.fillRects.filter((r) => r[0] < 860);
  ok("G7 C2 门: neon 档 Lv.3 即画 5 条 2px 级切片(lv>=2 即画 —— 「默认霓虹档永不出现」回潮即红)",
    slA.length === 5 && slA.every((r) => r[3] === 2));
  // Arm B: Lv.1 -> neon 门关零切片; 拍内切 glitch 下一帧即画(palette 逐帧门保留), 厚 1.5
  const u2 = mkDrawU([0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u2._qbBeat = mkBeatSt(LIVE_UP, LIVE_DL);
  u2._qbBeat.anim = mkAnim(mkFx({ lv: 1, slices: _qbFxTearSlices(1, yOfT(10), 40, 0.5, 7, "linked", 10, 310) }));
  at(u2, 100);
  ok("G7 Lv.1 neon: 零切片(lv<2 且非 glitch —— 门另一侧判别面)",
    u2.ctx.fillRects.filter((r) => r[0] < 860).length === 0);
  global.window.AQB_FX_CFG = Object.assign({}, CFG0, { palette: "glitch" });
  at(u2, 100);
  const sl = u2.ctx.fillRects.filter((r) => r[0] < 860);
  global.window.AQB_FX_CFG = CFG0;
  ok("G7 拍内切 glitch: 下一帧即画 2 条 1.5px 级(Lv.1; 切入口整拍无切片回潮即红; 梳齿在 x>=860 域不混入)",
    sl.length === 2 && sl.every((r) => r[3] === 1.5));
  // Arm C: calm 档零切片(评审修复 #1: 门补 calm 排除 —— 模板 demo:1086 isCalm() 早退在前,
  // 「C 类按模板修」拍板; 计划 §02 C2「不限配色」系只抄 demo:1088 门表达式漏看 :1086 前置
  // 早退的引用疏漏, 以模板为准)
  const u3 = mkDrawU([0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u3._qbBeat = mkBeatSt(LIVE_UP, LIVE_DL);
  u3._qbBeat.anim = mkAnim(mkFx());
  global.window.AQB_FX_CFG = Object.assign({}, CFG0, { palette: "calm" });
  at(u3, 100);
  global.window.AQB_FX_CFG = CFG0;
  ok("G7 calm 档: Lv.3 亦零切片(门补 calm 排除 —— 模板 demo:1086 isCalm() 早退同口径; 克制档细纹回潮即红)",
    u3.ctx.fillRects.filter((r) => r[0] < 860).length === 0);
}
// —— G8: draw 侧 merge + 缺口轨(修复2): 环心 = yOf(lead.shown), 非与底边的假中点 ——
//    观测面(S2 环旋转后改): t=0 时主环 rot=0 -> 8 边环恰两个对径顶点(90°/270°)落 x=tipX,
//    y = 环心 ± r, 两点均值即环心; neon=false 摘外圈与 N 层噪声(短亮段/小菱形/闪光 x=859.5
//    或 y 向远离, 不混入 x=tipX 滤器) ——
{
  global.window.AQB_FX_CFG = Object.assign({}, CFG0, { dual: "merge", neon: false });
  const u = mkDrawU([0, 0, 0, 0, 30], [0, 0, 0, 0, null]);
  u._qbBeat = mkBeatSt(LIVE_UP, GAP_DL);
  u._qbBeat.anim = mkAnim(mkFx({ alloc: { up: 0, dl: 0, merge: 32 },
    specs: { merge: _qbFxSpawnSpecs(32, 860, yOfT(10), 29, 15) }, act: { up: true, dl: false } }));
  at(u, 0);
  const ys = u.ctx.ops.filter((o) => Math.abs(o[0] - 860) < 1e-6).map((o) => o[1]);
  const avg = ys.reduce((a, b) => a + b, 0) / ys.length;
  ok("G8 draw merge+缺口: 环心 = yOf(lead.shown)(t=0 对径两点均值; 假中点 = (yOf+310)/2 即红 —— I10/D4)",
    ys.length === 2 && Math.abs(avg - yOfT(10)) <= 1e-6 && Math.abs(avg - (yOfT(10) + 310) / 2) > 1);
  const u2 = mkDrawU([0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u2._qbBeat = mkBeatSt(LIVE_UP, LIVE_DL);
  u2._qbBeat.anim = mkAnim(mkFx({ alloc: { up: 0, dl: 0, merge: 32 },
    specs: { merge: _qbFxSpawnSpecs(32, 860, (yOfT(10) + yOfT(55)) / 2, 29, 15) } }));
  u2.ctx = mkCtx();
  at(u2, 0);
  const ys2 = u2.ctx.ops.filter((o) => Math.abs(o[0] - 860) < 1e-6).map((o) => o[1]);
  const avg2 = ys2.reduce((a, b) => a + b, 0) / ys2.length;
  ok("G8 对照双轨 live: 环心 = (yUp+yDl)/2 中点(D3-c)", ys2.length === 2
    && Math.abs(avg2 - (yOfT(10) + yOfT(55)) / 2) <= 1e-6);
  global.window.AQB_FX_CFG = CFG0;
}
// —— G9: 真 0 轨零粒子(注入态 level=0 手工构造; F1 后生产侧 level 0 只来自真 0/缺口轨)——
//          §10 双轨探针「上传零粒子零环、下载有反馈」的绘制面计数;
//          spawn 侧 alloc 照发 both 半套, spots 组装被 fx.act 门滤除 —— 绘制侧是最终闸门;
//          对照臂证明 16 不是「恰好只有半套在画」的巧合, act 门删掉即 32/32 翻倍) ——
{
  const ZERO_UP = { prev: 10, target: 10, shown: 10, delta: 0, level: 0, live: true };   // 注入态
  const u = mkDrawU([0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeatSt(ZERO_UP, LIVE_DL);
  u._qbBeat.anim = mkAnim(mkFx({ lead: "dl", lv: 3, act: { up: false, dl: true } }));
  at(u, 100);   // t=100 < 0.55xbeat: 活粒子窗内, dl 半套 13 全活(D5 基数 27)
  const silent = u.ctx.fillCnt;
  const u2 = mkDrawU([0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u2._qbBeat = mkBeatSt(ZERO_UP, LIVE_DL);
  u2._qbBeat.anim = mkAnim(mkFx({ lead: "dl", lv: 3, act: { up: true, dl: true } }));
  at(u2, 100);
  ok("G9 上真 0 下 Lv.3(dual=both): 上轨零粒子(fillCnt = dl 半套 13 + dl 小菱形 C10 1 + 判定线小菱形 P4 1 = 15"
    + " —— D5 基数 27) vs 双活性对照 31(27 + 4 菱形 —— C10/P4 每活性轨各 1 枚)(I10/D2)",
    silent === 15 && u2.ctx.fillCnt === 31);
}
// —— G10: calm 档零粒子(绘制面 —— 与切片 glitch 门同款逐帧语义: palette 拍内切入下一帧生效;
//          同一 anim 不重建清单, eff=0 经 m=min(specs.length, n) 落零粒; neon 同参数为对照,
//          绘制侧 eff 门是唯一闸 —— 删门即 specs 满额照画) ——
{
  const u = mkDrawU([0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeatSt(LIVE_UP, LIVE_DL);
  u._qbBeat.anim = mkAnim(mkFx());   // 满额清单 16/16(neon, 密度 1)
  at(u, 100);
  const neonCnt = u.ctx.fillCnt;     // 与 G6 密度 1 同源: 27(D5 基数)
  global.window.AQB_FX_CFG = Object.assign({}, CFG0, { palette: "calm" });
  u.ctx = mkCtx();
  at(u, 100);                        // 同一 anim 拍内切 calm: specs 仍在, eff=0 -> 零粒
  const calmCnt = u.ctx.fillCnt;
  const calmAlphas = u.ctx.fillAlphas;
  global.window.AQB_FX_CFG = CFG0;
  ok("G10 calm 零粒子: neon 同参数 31 落笔对照(27 粒 D5 基数 + 2 小菱形 C10 + 2 判定线小菱形 P4), 拍内切 calm"
    + " 下一帧只剩 2+2 枚(粒子 0 —— 生产 neon 门不挂 palette 系既有适配, demo neonOn():882 含 isCalm"
    + " 此处有意不跟)(plan §04 原型 partCap isCalm 口径; C10 两笔 alpha = 0.7xqximpact —— #5,"
    + " P4 两笔 alpha 恒 0.35)",
    neonCnt === 31 && calmCnt === 4 && calmAlphas.length === 4
    && calmAlphas.slice(0, 2).every((a) => Math.abs(a - 0.7 * (1 - 100 / 330) * 0.7) <= 1e-9)
    && calmAlphas.slice(2).every((a) => a === 0.35));
}
// —— G11: 环心去钳制(P6, 26-11-26-0227 §03.3 —— 旧 F5/P3 近底/近顶 clamp 退役): 环心恒走
//          真位 sp.y, 越界原样通过(贴边环完整可见域由 clip 上下缘放宽承接)。观测面同旧
//          (环/辉光多边形在 x=tipX 处的顶点两点均值 —— G8 同款); dual=lead 单 spot + specs
//          置空消粒子噪声, shown 经 yOf 换算出目标环心(1.05 -> 305 越下界 / 60 -> 24.3 越上
//          界)。旧「钳到 282/38」回潮即红。 ——
{
  const clampCase = (shown) => {
    const u = mkDrawU([0, 0, 0, 0, 30], [0, 0, 0, 0, null]);
    u._qbBeat = mkBeatSt({ prev: shown, target: shown, shown, delta: 0.5, level: 3, live: true }, GAP_DL);
    u._qbBeat.anim = mkAnim(mkFx({ lead: "up", alloc: { up: 32, dl: 0, merge: 0 },
      specs: { up: [] }, act: { up: true, dl: false } }));
    global.window.AQB_FX_CFG = Object.assign({}, CFG0, { dual: "lead", neon: false });
    at(u, 0);   // S2 环旋转后观测面改 t=0(rot=0 对径两点落 x=tipX; neon=false 摘外圈/N 层噪声)
    global.window.AQB_FX_CFG = CFG0;
    const ys = u.ctx.ops.filter((o) => Math.abs(o[0] - 860) < 1e-6).map((o) => o[1]);
    return ys.reduce((a, b) => a + b, 0) / ys.length;
  };
  const below = clampCase(1.05);   // yOf -> 305 > T+H-28(282) —— 旧钳制面
  const above = clampCase(60);     // yOf -> 24.286 < T+28(38) —— 旧钳制面
  const inMid = clampCase(20);     // yOf -> 214.76(区间中部)
  const inNear = clampCase(55);    // yOf -> 48.095(距下界仅 10.1px 的区间内侧)
  ok("G11 环心越下界(近底): y=305 原样通过(钳制删除 —— 旧钳到 282 回潮即红)",
    Math.abs(below - 305) <= 1e-6);
  ok("G11 环心越上界(近顶): y=24.29 原样通过(旧钳到 38 回潮即红)",
    Math.abs(above - 24.2857142857) <= 1e-6);
  ok("G11 环心区间内恒等(不咬合): 中部 214.76 与近界 48.10 原样通过 —— 环心恒真位(G8 恒等面)",
    Math.abs(inMid - yOfT(20)) <= 1e-6 && Math.abs(inNear - yOfT(55)) <= 1e-6);
}
// —— G12: 粒子底缘去镜像(P6, 26-11-26-0227 §03.3 —— 旧 F5/P3 折回退役): y 恒走
//          _qbFxParticleAt 真位, 越底不折回(贴底粒子可见域由 clip 上下缘放宽承接)。构造 90°(正
//          下)单粒子 spec: t=130 时 ps.y>310(T+H)。观测 = ops 里 y>278 的顶点(环心 147/r<=13.2
//          的环、judgeFlash/小菱形顶点都在其下; scan 域 y=310 的竖笔由 layers.scan=false 摘除;
//          t=130 >= impactMs=120 闪光窗已过)—— 三顶点均值 == 真位 ps.y, 旧镜像回潮即红。 ——
{
  const spec = { x0: 860, y0: 300, ang: Math.PI / 2, sides: 3, size: 2, dist: 40 };
  const u = mkDrawU([0, 0, 0, 0, 30], [0, 0, 0, 0, null]);
  u._qbBeat = mkBeatSt({ prev: 30, target: 30, shown: 30, delta: 0.5, level: 3, live: true }, GAP_DL);
  u._qbBeat.anim = mkAnim(mkFx({ lead: "up", alloc: { up: 32, dl: 0, merge: 0 },
    specs: { up: [spec] }, act: { up: true, dl: false } }));
  global.window.AQB_FX_CFG = Object.assign({}, CFG0, { dual: "lead",
    layers: Object.assign({}, CFG0.layers, { scan: false }) });
  at(u, 130);
  global.window.AQB_FX_CFG = CFG0;
  const ps = _qbFxParticleAt(130, 1000, 120, spec, 0, 0, 1);
  const folded = 2 * (10 + 300) - ps.y;
  const vy = u.ctx.ops.filter((o) => o[1] > 278).map((o) => o[1]);
  const avg = vy.reduce((a, b) => a + b, 0) / vy.length;
  ok("G12 粒子底缘去镜像: ps.y=" + ps.y.toFixed(1) + " 越底缘 -> fill 顶点均值 = 真位 "
    + ps.y.toFixed(1) + "(恰 3 顶点; 旧折回值 " + folded.toFixed(1) + " 回潮即红)",
    vy.length === 3 && Math.abs(avg - ps.y) <= 1e-6 && Math.abs(avg - folded) > 5);
}
// —— G13: 环旋转 + 外圈新式(S2 模板保真二轮 C3): 主环 rot=t/300 / 外圈 rot+0.4, 外圈半径
//          (9+31×pf)×rScale×gapScale 独立扩张(替换恒 +3px), 外圈 alpha 0.55×(1−pf)×impact×
//          rScale×gapScale(替换 q×ringT.alpha —— q 衰减退役), 主环 lw2(模板 demo:1294-1300;
//          gapScale 为生产 D4 适配)。观测: dual=lead 单 spot + specs 空 + scan=false, t=100
//          -> ops[0..27] = 主环 8 顶点(rot=1/3) + 外圈 8 顶点(rot+0.4), 其后恰 12 笔(短亮段 2 +
//             C10 小菱形 4 + 判定线小菱形 4 + 冲击闪光 2); 顶点坐标/笔画宽/alpha 三面全钉(闪光全高几何含在内), 旋转
//          删除或外圈旧式回潮即红 ——
{
  const u = mkDrawU([0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeatSt(LIVE_UP, LIVE_DL);
  u._qbBeat.anim = mkAnim(mkFx({ lead: "up", alloc: { up: 32, dl: 0, merge: 0 },
    specs: { up: [] }, act: { up: true, dl: false } }));
  global.window.AQB_FX_CFG = Object.assign({}, CFG0, { dual: "lead",
    layers: Object.assign({}, CFG0.layers, { scan: false }) });
  at(u, 100);
  global.window.AQB_FX_CFG = CFG0;
  const cy = yOfT(10);
  const pf = 100 / 600;
  const rot = 100 / 300;
  const vert = (r, rt) => {
    const out = [];
    for (let i = 0; i < 8; i++) {
      const a = rt + (Math.PI * 2 * i) / 8;
      out.push([860 + Math.cos(a) * r, cy + Math.sin(a) * r]);
    }
    return out;
  };
  const exp = vert(4 + 24 * pf, rot).concat(vert(9 + 31 * pf, rot + 0.4));
  const qD = 1 - 100 / 330;                       // _qbFxNeonQ(100, 1000) 同式
  const rd = 2.2 * qD + 1;                        // C10 小菱形半径 2.2q+1
  const tail = [[859.5, cy - 10], [859.5, cy + 10]];   // 短亮段两点(判定线-0.5, 单活性轨)
  for (let i = 0; i < 4; i++) {
    const a = rot + (Math.PI * 2 * i) / 4;
    tail.push([860 + Math.cos(a) * rd, cy + Math.sin(a) * rd]);   // 小菱形 4 顶点(C10)
  }
  const rotJ = 100 / 420;                         // P4 判定线小菱形 rot=t/420(模板 demo:1421)
  for (let i = 0; i < 4; i++) {
    const a = rotJ + (Math.PI * 2 * i) / 4;
    tail.push([860 + Math.cos(a) * 2.6, cy + Math.sin(a) * 2.6]);   // 判定线小菱形 4 顶点(P4, r2.6)
  }
  tail.push([859.5, 10], [859.5, 310]);           // 冲击闪光两点(判定线-0.5, T -> T+H 全高 —— C4)
  const all = exp.concat(tail);
  let vOk = u.ctx.ops.length === 28;
  for (let i = 0; i < 28 && vOk; i++) {
    vOk = Math.abs(u.ctx.ops[i][0] - all[i][0]) <= 1e-9 && Math.abs(u.ctx.ops[i][1] - all[i][1]) <= 1e-9;
  }
  ok("G13 环旋转+外圈新式: ops[0..27] 逐点吻合 = 主环(rot=t/300)+外圈(rot+0.4) 16 顶点 + 短亮段 2"
    + "(x=判定线-0.5, y=cy±10)+ C10 小菱形 4 顶点 + 判定线小菱形 4 顶点(P4, r2.6 rot=t/420 钉判定线"
    + " x=L+W) + 冲击闪光 2(x=判定线-0.5, y=T/T+H 全高 —— C4 几何钉死)"
    + "(rot=0 旧式/恒 +3px 外圈/闪光几何漂移/判定线小菱形回退即红)", vOk);
  ok("G13 环笔画: 主环 lw2 alpha=0.85x(1-pf)ximpact(1 处) / 外圈 lw1 alpha=0.55x(1-pf)ximpact Lv 色"
    + "(独立扩张新式 —— 旧 q 衰减与恒 +3px 回潮即红)"
    + " / 短亮段 lw3 alpha=0.55xqximpact Lv 色(P2 模板 demo:1050 —— 旧 lw2/裸 q 回潮即红)",
    u.ctx.strokeMeta.length >= 2
    && u.ctx.strokeMeta[0].w === 2 && Math.abs(u.ctx.strokeMeta[0].alpha - 0.85 * (1 - pf) * 0.7) <= 1e-9
    && u.ctx.strokeMeta[1].w === 1 && Math.abs(u.ctx.strokeMeta[1].alpha - 0.55 * (1 - pf) * 0.7) <= 1e-9
    && u.ctx.strokeMeta[1].style === "#FF6BD6"
    && u.ctx.strokeMeta[2].w === 3 && Math.abs(u.ctx.strokeMeta[2].alpha - 0.55 * qD * 0.7) <= 1e-9
    && u.ctx.strokeMeta[2].style === "#FF6BD6");
  ok("G13 小菱形 alpha: fill 记录面恰 2 笔(单活性轨夹具) —— C10 = 0.7xqximpact = 0.7x(1-100/330)x0.7"
    + " / 判定线小菱形(P4) = 0.35(fill rgba(trackCol,0.35) 恒 alpha 面) —— 两枚不同元素并存(C10 删/判定线小菱形缺一即红)",
    u.ctx.fillAlphas.length === 2 && Math.abs(u.ctx.fillAlphas[0] - 0.7 * qD * 0.7) <= 1e-9
    && u.ctx.fillAlphas[1] === 0.35);
}
// —— G14: 顶门 0.7×beat 行为采样(S2 模板保真二轮): t=570 ∈ (0.55, 0.7)×beat —— 环仍在画
//          (strokeMeta lw2 alpha>0)+ lvBadge 常显 fillText 恰 1 —— 顶门接线回退 0.55 即红
//          (I9 逐元素窗改判的行为面锚点; 0.55-0.7 段此前只被 S1 扫描计数面覆盖) ——
{
  const u = mkDrawU([0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeatSt(LIVE_UP, LIVE_DL);
  u._qbBeat.anim = mkAnim(mkFx({ lead: "up", alloc: { up: 32, dl: 0, merge: 0 },
    specs: { up: [] }, act: { up: true, dl: false } }));
  global.window.AQB_FX_CFG = Object.assign({}, CFG0, { dual: "lead",
    layers: Object.assign({}, CFG0.layers, { scan: false }) });
  at(u, 570);
  global.window.AQB_FX_CFG = CFG0;
  ok("G14 顶门 0.7 行为采样: t=570(0.55-0.7xbeat 之间)环仍落笔(strokeMeta lw2 alpha>0)+ lvBadge 常显"
    + " fillText 恰 1(顶门回退 0.55 即红 —— I9 逐元素窗)",
    u.ctx.fillTexts.length === 1 && u.ctx.fillTexts[0].s === "Lv.3 · lead 上传"
    && u.ctx.strokeMeta.some((s) => s.w === 2 && s.alpha > 0));
}
// —— G15/G16(A1/D4 + C7 机检归属: 本视觉引擎电池; CSS 逐字钉在锚电池) ——
// G15 曲线辉光: 常驻(无 t<beat 窗 / 无 tail 门 —— 缺陷一重构, plan 26-11-26-0227 §3.1) /
//   两轨 trackCol blur 描边 / calm 退化(blurCap=0) ——
{
  const u = mkDrawU([0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeatSt(LIVE_UP, LIVE_DL);
  u._qbBeat.anim = mkAnim(mkFx());
  drawGlow(u);   // t=100, dual=both: 曲线辉光 2 道, 带 blur
  ok("G15 曲线辉光: 两轨 level>0 -> 2 道 trackCol blur 描边(帧末清零, 计入 I9 <=5)",
    u.ctx.blurSets.filter((v) => v > 0).length === 1 && u.ctx.strokesWhileBlur === 2
    && u.ctx.strokeVals.indexOf("#UP") >= 0 && u.ctx.strokeVals.indexOf("#DN") >= 0
    && u.ctx.shadowBlur === 0);
  const u2 = mkDrawU([0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u2._qbBeat = mkBeatSt(LIVE_UP, LIVE_DL);
  u2._qbBeat.anim = mkAnim(mkFx(), { clock: 800 });   // 0.8xbeat: 顶门外、拍内
  drawGlow(u2);
  ok("G15 常驻 t=800(0.8xbeat): 辉光仍在(无时间窗 —— 旧拍内窗回潮即红)",
    u2.ctx.strokesWhileBlur === 2 && u2.ctx.strokeVals.length === 2);
  const u2b = mkDrawU([0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u2b._qbBeat = mkBeatSt(LIVE_UP, LIVE_DL);
  u2b._qbBeat.anim = null;   // 拍间静默期(anim 缺席): level 仍在 -> 辉光仍画(缺陷一主判据)
  drawGlow(u2b);
  ok("G15 拍间(anim=null): 辉光仍 2 道(level 判据不依赖 anim —— 旧拍内窗该帧为零)",
    u2b.ctx.strokesWhileBlur === 2 && u2b.ctx.strokeVals.length === 2);
  const u2c = mkDrawU([0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u2c._qbBeat = mkBeatSt(LIVE_UP, LIVE_DL);
  u2c._qbBeat.anim = mkAnim(mkFx(), { phase: "tail", clock: 1400 });   // tail 清理帧亦画
  drawGlow(u2c);
  ok("G15 tail 相位: 辉光仍 2 道(无 phase 门 —— 拍周期全程常驻)",
    u2c.ctx.strokesWhileBlur === 2 && u2c.ctx.strokeVals.length === 2);
  global.window.AQB_FX_CFG = Object.assign({}, CFG0, { palette: "calm" });
  const u3 = mkDrawU([0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u3._qbBeat = mkBeatSt(LIVE_UP, LIVE_DL);
  u3._qbBeat.anim = mkAnim(mkFx(), { clock: 100 });
  drawGlow(u3);
  global.window.AQB_FX_CFG = CFG0;
  ok("G15 calm 退化: blurSets 恒 0(零 blur 描边)但两轨仍 trackCol 普通描边",
    u3.ctx.blurSets.every((v) => v === 0) && u3.ctx.strokesWhileBlur === 0
    && u3.ctx.strokeVals.indexOf("#UP") >= 0 && u3.ctx.strokeVals.indexOf("#DN") >= 0);
  // —— G17 ctx transform 配平: drawGlow 返回后 save/restore 计数必须相等 —— _qbCanvasScale
  //    的 save+scale(pxRatio) 由函数自己还(同 _qbDrawLimits/_qbDrawGaps 惯例: 函数内另加 clip
  //    save 也必须配平)。uPlot 1.6.x 渲染循环(clearRect→drawClear→axes/series→draw)**无顶层
  //    save/restore 兜底**: 泄漏的 ctx.scale(px) 跨帧累积 —— pxRatio=1(桩/100% 缩放)时无害,
  //    pxRatio>1(真机 Windows 125%/150% 显示缩放)时首帧泄漏后逐帧叠加, 全图按 px^n 放大重画
  //    = 曲线/网格/图例全错位(clearRect 实参为设备像素, 泄漏 scale 下映射为更大的设备矩形 =
  //    过清整幅无残影 —— 症状只有「越画越大」; 真机「彻底不正常乱跳」根因) ——
  ok("G17 transform 配平: drawGlow 返回后 ctx save==restore 计数相等(clip save 与 _qbCanvasScale save 双配平; pxRatio>1 泄漏 scale 逐帧叠加即真机全图放大错位)",
    u.ctx.saveCnt === u.ctx.restoreCnt);
}
// G16 N 锚辉光新式(C7): 6 边环 / r=(7+4q) / rot=t/320 / alpha=0.5xqximpact / tipX ——
//    轨 level 置 0 与辉光面解耦对照(曲线辉光已抽独立 _qbDrawFxCurveGlow, drawAnchor 只画锚面装饰)。
{
  const noGlowUp = Object.assign({}, LIVE_UP, { level: 0 });
  const noGlowDl = Object.assign({}, LIVE_DL, { level: 0 });
  const u = mkDrawU([0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeatSt(noGlowUp, noGlowDl);
  u._qbBeat.anim = mkAnim(mkFx(), { clock: 0 });   // rot=0, q=1, imp=0.7 -> alpha 0.35
  drawAnchor(u);
  ok("G16 C7 六边环: 两轨各 6 顶点(共 12 ops) + alpha=0.5x1x0.7=0.35 + Lv 语义色 lw1",
    u.ctx.ops.length === 12 && u.ctx.strokeMeta.length === 2
    && u.ctx.strokeMeta.every((s) => s.w === 1 && Math.abs(s.alpha - 0.35) <= 1e-9 && s.style === "#FF6BD6"));
  const u2 = mkDrawU([0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u2._qbBeat = mkBeatSt(noGlowUp, noGlowDl);
  u2._qbBeat.anim = mkAnim(mkFx(), { clock: 320 });
  drawAnchor(u2);
  const r0 = 7 + 4 * 1;
  const r320 = 7 + 4 * (1 - 320 / 330);
  ok("G16 rot=t/320 + tipX: t=0 首顶点 x=tipX+11=871, t=320 首顶点 x=tipX+r320xcos(1)(逐帧滑动)",
    Math.abs(u.ctx.ops[0][0] - (860 + r0)) <= 1e-6
    && Math.abs(u2.ctx.ops[0][0] - (860 + r320 * Math.cos(1))) <= 1e-6
    && Math.abs(u2.ctx.ops[0][0] - u.ctx.ops[0][0]) > 0.1);
}
// —— S4: tail 相位余晖线(C6/D7) + 全宽巡回菱形光点(C5) ——
{
  const u = mkDrawU([0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u._qbBeat = mkBeatSt(LIVE_UP, LIVE_DL);
  u._qbBeat.anim = { phase: "tail", clock: 1400, tl: { beat: 1000, tailMs: 1000 },
    fx: mkFx(), fxTail: { sig: "x", pts: [
      { k: "up", x: 300, y: 100, alpha: 0.3 }, { k: "dl", x: 500, y: 200, alpha: 0.15 },
    ] } };
  // D7: 不挂 neon 门 + calm 档 grade=false 仍画; 色走 Lv 表(Lv.1 蓝, 非 Lv.3 品红)
  global.window.AQB_FX_CFG = Object.assign({}, CFG0, { neon: false, palette: "calm",
    layers: Object.assign({}, CFG0.layers, { grade: false }) });
  draw(u);
  const rot = 1400 / 500;
  ok("S4 余晖线 C6: lw1 + rgba(Lv色,0.14x(1-qt)) + 判定线全高 + neon=false/calm 亦显(D7)",
    u.ctx.strokeMeta.length === 1 && u.ctx.strokeMeta[0].w === 1
    && u.ctx.strokeMeta[0].style === "rgba(122,217,255,0.084)"
    && Math.abs(u.ctx.strokeMeta[0].alpha - 1) <= 1e-9
    && Math.abs(u.ctx.ops[0][0] - 859.5) <= 1e-6 && Math.abs(u.ctx.ops[0][1] - 10) <= 1e-6
    && Math.abs(u.ctx.ops[1][0] - 859.5) <= 1e-6 && Math.abs(u.ctx.ops[1][1] - 310) <= 1e-6);
  ok("S4 光点菱形化 C5: 2 点各 4 顶点(共 8 ops) + 2 fill + rot=t/500",
    u.ctx.ops.length === 10 && u.ctx.fillCnt === 2
    && Math.abs(u.ctx.ops[2][0] - (300 + 2.2 * Math.cos(rot))) <= 1e-6
    && Math.abs(u.ctx.ops[2][1] - (100 + 2.2 * Math.sin(rot))) <= 1e-6);
  // Lv 表联动单点: grade=true 时余晖线色随 lead 等级升到 Lv.3 品红
  const u2 = mkDrawU([0, 0, 0, 0, 30], [0, 0, 0, 0, 60]);
  u2._qbBeat = mkBeatSt(LIVE_UP, LIVE_DL);
  u2._qbBeat.anim = Object.assign({}, u._qbBeat.anim, { fxTail: { sig: "", pts: [] } });
  global.window.AQB_FX_CFG = CFG0;
  draw(u2);
  ok("S4 余晖线色走 Lv 表联动: grade=true 时 Lv.3 品红 rgba(255,107,214,0.084)",
    u2.ctx.strokeMeta.length === 1 && u2.ctx.strokeMeta[0].style === "rgba(255,107,214,0.084)");
}
console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
"""


def test_frontend_qb_fx_visual_engine_battery():
    """视觉引擎 V + N 层 S2-a 电池 + 接缝静态钉(plan 26-11-12-1139 §03 V 表/N 节/D1-D4, §06 S2 行)

    行为面(node 电池, 无 node 静默跳过, 同节拍内核口径):
    1. I6 图层顺序常量逐字 + 序断言(geometry/neon 恒在 curve 之前, anchor 之后);
    2. I11 N 层白名单六元素(S2-b 增 bandHalo 数值光带辉光)/黑名单八元素逐字且零交集;
    3. V1 Lv 色表逐字(#7AD9FF/#FEFFA9/#FF6BD6) + 三档配色 blur 上限(10/14/0) + V2 环边数(3/6/8);
    4. I9 预算常量(32/16/0.33/0.55/环窗 0.6/26/5/3px/2(每轨, 全宽巡回 —— 旧末段 6 桶常量退役), 全部两轨合计口径)
       + 锚旋转周期常量 2639ms(C1/D6, 本阶段只立常量)
       + I9 逐元素窗常量(模板保真二轮 S2: 顶门最大窗 _QB_FX_TOP_RATIO 0.7 / 切片独立窗
       _QB_FX_SLICE_RATIO 0.25 / 束 fade 窗 _QB_FX_BEAM_RATIO 0.7 —— 旧 0.55 单一顶门退役,
       粒子 0.55 / 环 0.6 各自独立窗保留; 顶门只做最大窗粗滤, 逐元素窗在各自块内);
    5. D3 lead 仲裁(argmax 优先非缺口非静默/双轨静默 null/恰等取 up);
    6. partCap(D5 模板基数 6+7×lv = 13/20/27 x 密度, clamp 32 保留, 密度 <=0 零粒子;
       P9 兼容 Lv.1 仍发射; 等级超 3 基数钳 Lv.3);
    7. D3 三策略分配(both 对半各 <=16 合计守恒全域扫/lead 全套从属零/merge 中点一次/未知回落 both);
    8. D4 y 间距缩小(线性 /26 下限 0.4, 不合并不取消);
    9. N 回落 0.33×beat + 冲击环(C3 模板式: pf=t/(0.6×beat) 线性不 easeOut, r=(4+24pf)×rScale×gapScale
       起步半径 4, alpha=0.85×(1−pf)×impact×rScale×gapScale, rScale 半套系数 both 0.5/lead 1/merge 1,
       pf>=1 null —— B3 环窗 0.55->0.6);
    10. V3 粒子三阶段(爆发 x4.5 闭式/拖尾 easeOut 减速/末态恰 dist/carryPx 随 L0 末点滑动)
        + C8 模板式 alpha=0.78×(1−t/T)×impact(impact 0/负/NaN -> alpha 0)与 rot=t/260+idx 匀速单向
        (rot0/vr 字段退役) + 喷射清单(三/四/五边/同种子恒同/360° 全向 + 行程钳(P1, 旧 270° 左弧 D2 退役)/尺寸 1.6-4.2 C8)
        + 粒子三形态因子对齐模板(plan 26-11-26-0227 §3.2): y 位移纵向压 0.7 椭圆喷雾(y 行程
        = 0.7×x 行程同相 —— P9)/life = 1−t/T 线性衰减与 alpha 同源(alpha = 0.78×life×impact
        —— P10)+ 绘制侧 _qbFxPolyPath 半径 = size×life(旧恒定半径调用形态退役静态钉 ——
        P10 绘制接线)/边数 = 3+(i%3) 按清单序号轮换(伪随机分配退役 —— P11);
    11. glitch 撕裂切片(S2-b R6 重写; C2/D3: <=5/|offX|<=3 x 向微震 dy0/ph 退役/长 10-80/同参数恒同)
        + 伪随机确定性;
    12. 调度器 fx 面: fx 生成门(on=false fx null 但 L0/L1 照常/reduce 无 anim/缺口轨 lead 单轨/
        D4 实测缩小)/三策略落 fx 清单/装饰帧保障(impact 窗强制重绘 + y 钉成对)/次区相位全生命周期
        (衔接/光点 <=4 alpha=0.3x(1-qt)<=0.3 位置在绘图区/全宽巡回 x 跨多段/1px 量化去重零空转/窗尽收尾/拍内关 tail 下一帧收尾)
        + S4 次区面(C5/C6/D7, plan §3.4): 光点 4 边菱形 r2.2 rot=t/500 复用 _qbFxPolyPath(圆点 arc 退役),
        ph=(t/1000×0.12+i/2+轨偏移 up0.31/dl0) mod 1 映射整条 u.data[0] 全列, alpha 0.3×(1−qt) 线性衰减;
        余晖线判定线全高 lw1 rgba(Lv 色,0.14×(1−qt)) 不挂 neon 门(D7, calm 档亦显色走 Lv 表)、
        +1 stroke 记 I9 修订注记; 静态钉禁旧常量/圆点回潮
        + merge+缺口轨落位退 lead 末点 y(F7, specs.merge[0].y0 === yOf(lead.shown), 假中点即红
        —— 评审修复2; 切片锚带中心同退且清单无条件生成)/spawn 满额清单与密度解耦(F8, 密度 0.4
        仍 14/13 —— D5 基数 27, 评审修复3)/梳齿 fixed 档恒 7(F10, C11 模板对照档; linked 仍 3/5/7);
    13. 绘制面 ctx 桩电池(G0-G16 + S4 tail 用例, 记账式 2d context 真 _qbDrawFx/_qbDrawFxAnchor; S2 起 stroke
        另记 strokeMeta 笔画元数据, fillText 记 {s,font,alpha,x,y}): clip 实参记账
        (G0: fx 主 clip 右缘放宽到画布右缘宽 840 + 上下缘放宽到画布上下缘(P6, 桩高 320 -> [60,0,840,320]),
        束体/锚段只右缘放宽 —— F5)+ blur 预算
        (非零赋值恰 1 施加点/带 blur stroke = spots 数 <=2/逐帧扫帧末 shadowBlur 恒 0/palette=calm
        恒不赋非零 —— 评审修复7; 旧场景 tracks shown=prev 光带零长不落笔, bandHalo 不参与,
        完整辉光预算在 scan_band 电池)/neon=false 白名单断言面收窄(G4, I11 例外注记 —— D7:
        lvBadge 常显 fillText 恰 1 = 「Lv.3 · lead 上传」11px alpha 0.85 + 判定帧全高冲击闪光
        rgba Lv 色 lw2 恰 1 笔不挂 neon 门; 环外圈辉光/短亮段/粒子外圈仍零 Lv 直色落笔, 锚段
        同验)/密度拍内即时(0.4->15/1->31/0.1->7 = D5 基数 27 + 每活性轨 +2 fill: C10 小菱形 + P4 判定线小菱形)/
        切片门 C2+calm 排除(G7: 非 calm 且 (glitch || lv>=2) —— neon 档 Lv.3 即画 5 条 2px 级/
        Lv.1 neon 零切片/拍内切 glitch 下一帧即画 2 条 1.5px 级/calm 档 Lv.3 亦零切片 —— 模板
        demo:1086 isCalm() 早退同口径, 独立窗 0.25×beat; 计数按 x<绘图右缘的切片域滤除束体
        梳齿 —— S2-b)/draw 侧 merge+缺口轨环心 = yOf(lead.shown)(G8/G11 观测面 S2 改 t=0 对径
        两点 + neon=false 摘 N 层噪声 —— 环旋转后 rot≠0 无 x=tipX 顶点; 假中点即红)/lead 加亮
        跨缺口重新 moveTo 不桥接([20,null,25] vs [20,22,25] 对照)/环心去钳制(G11: P6 删旧
        F5/P3 近底/近顶 clamp —— 越下界 305/越上界 24.3 原样通过, 旧钳到 282/38 回潮即红;
        评审 major 的钳制机检面反转为去钳制机检面)/粒子底缘去镜像(G12: 90° 单粒子越底 ->
        fill 顶点均值 = 真位 ps.y, 旧折回值回潮即红; 观测帧 t=130 >= impactMs 避开 S2 冲击闪光
        全高 stroke 的 y=310 落笔)/环旋转与外圈新式
        (G13, C3 模板 demo:1294-1300: t=100 ops[0..27] = 主环 8 顶点(rot=t/300)+外圈 8 顶点
        (rot+0.4, 半径 (9+31×pf)×rScale×gapScale)逐点吻合 + 其后恰 12 笔(短亮段 2/C10 小菱形 4/
        判定线小菱形 4(P4, r2.6 rot=t/420 钉判定线 x=L+W, fill rgba(trackCol,0.35) 与 C10 并存)/
        冲击闪光 2 —— 闪光全高几何含在内), 主环 lw2 alpha=0.85×(1−pf)×impact / 外圈 lw1
        alpha=0.55×(1−pf)×impact Lv 色 / 短亮段 lw3 alpha=0.55×q×impact(P2) —— 旧 q 衰减与恒 +3px 外圈回潮即红)
        + 顶门 0.7 行为采样(G14: t=570 ∈ (0.55,0.7)×beat 环仍落笔 lw2 alpha>0 + lvBadge fillText
        恰 1 —— 顶门接线回退 0.55 即红) + 小菱形 alpha(fill 记录面: G13 恰 2 笔(C10 0.7×q×impact + P4 恒 0.35)/G10 calm 恰 4 笔
        (C10 = 0.7×q×impact + P4 = 0.35))+ lvBadge 位置右对齐(G4: x=L+W-4/y=T+4)
        + S3 轮 G15/G16 机检归属本电池(G15 曲线辉光常驻: 两轨 level>0 -> 2 道 trackCol blur 描边
        帧末清零, t=800 拍内 / anim=null 拍间 / tail 相位均仍画(无时间窗无 tail 门 —— 缺陷一),
        calm 档 blurCap=0 退化为普通描边; G16 N 锚辉光 C7:
        两轨各 6 顶点共 12 ops, alpha=0.5xqximpact=0.35, rot=t/320 首顶点随 t 滑动, tipX 末点换算);
    14. S4-a 盘点轮补双面(plan §10 双轨探针「上传零粒子零环、下载有反馈」; F1 后静默面 =
        真 0/缺口轨, 注入态构造): F1e(上轨真 0 = target==0 -> level 0: lead=dl 真零轨不参与仲裁/
        act.up=false/act.dl=true/次区资格只 dl —— 与 F1d 缺口轨(live=false)互补的
        「live=true 但真 0」面) + G9(绘制面计数: spawn 侧 alloc 照发 both 半套, spots 组装被
        fx.act 门滤除 —— 静默 13 vs 双活性对照 27(D5 基数), act 门删掉即翻倍);
    15. 裁决轮补 calm 档零粒子并经评审 major 修正(plan §04 原型 partCap 的 isCalm 口径, §10
        「克制档零粒子」原文; 生产只采纳 calm 分量 —— 原型另有 leadLevel()<=1->0 门, Lv.1 发
        粒子系用户拍板维持现状/P9 未采纳): F1f(spawn 满额清单与配色档解耦 —— cap=partCap(lv,1)=27
        D5 基数, specs.up/dl 各 14/13 且 slices/comb 照建, lead/lv 仲裁照旧, L0/L1 收敛照常;
        与 F8 密度解耦同款, 否则 calm 判定帧 specs 全不建后拍内切出 calm 余下冲击窗零粒子到
        下一拍才恢复, 且 alloc.merge=0 把切片带 yCenter 退 lead 末点 y) + G10(唯一闸在绘制面 eff:
        同一 anim 拍内切 calm 下一帧零粒、eff=0 经 m=min(specs.length, n) 落零粒, neon 同参数 27 对照;
        isCalm 的 reduce 分量由 spawn 顶门 cfg.on !== true 承接 —— F1c 已钉)。
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
    assert '_QB_FX_N_WHITELIST = ["judgeFlash", "ringOuter", "partOuter", "anchorHalo", "lvBadge", "bandHalo"]' in js, \
        "缺/漂移 I11 N 层白名单(S2-b: bandHalo = T2 数值光带辉光)"
    assert '_QB_FX_N_BLACKLIST = ["curveUp", "curveDl", "plotBg", "edgeBg", "grid", "tooltip", "legend", "limitDash"]' in js, \
        "缺/漂移 I11 N 层黑名单"
    assert '_QB_FX_LV_COLORS = { 1: "#7AD9FF", 2: "#FEFFA9", 3: "#FF6BD6" }' in js, \
        "缺/漂移 V1 Lv 色表(plan §03 V1 行逐字)"
    assert "_QB_FX_BLUR_CAPS = { neon: 10, glitch: 14, calm: 0 }" in js, \
        "缺/漂移 V1 三档配色 blur 上限"
    assert "_QB_FX_RING_SIDES = { 1: 3, 2: 6, 3: 8 }" in js, "缺/漂移 V2 环边数映射"
    for line in (
        "_QB_FX_PART_MAX = 32;", "_QB_FX_SHARD_MAX = 16;", "_QB_FX_NEON_RATIO = 0.33;", "_QB_FX_PART_RATIO = 0.55;",
        "_QB_FX_RING_RATIO = 0.6;", "_QB_FX_TOP_RATIO = 0.7;", "_QB_FX_SLICE_RATIO = 0.25;", "_QB_FX_BEAM_RATIO = 0.7;",
        "_QB_FX_Y_GAP_PX = 26;", "_QB_FX_ANCHOR_SPIN_MS = 2639;"
    ):
        assert line in js, f"缺/漂移 I9 预算常量 {line}"
    seg = re.search(r"N 判定线短亮段.*?ctx\.lineWidth = 3;", js, re.S)
    assert seg and "globalAlpha = 0.55 * q * imp" in seg.group(0), \
        "短亮段 lw/alpha 漂移(P2 模板 demo:1050: lw3 / alpha=0.55×q×impact —— 旧 lw2/裸 q 退役)"
    assert "specs.up = _qbFxSpawnSpecs(alloc.up, tipX0, yUp, rMax, seed, maxDist);" in js, \
        "spawn 判定帧必须把画布右余量 maxDist 传入喷射清单(P1/R6 行程静态钳 —— 缺参即旧无界行程回潮)"
    # —— P6(26-11-26-0227 §03.3)装饰 clip 上下缘放宽 + 去钳制/镜像静态钉(张力处置: 允许画到
    #    画布留白但不压轴标签, S4 真机核对; 「不铺底」由 c 项 fillRect 恰 1 处且 1px 级钉承接) ——
    fxb_m = re.search(r"_qbDrawFx\(u, tk\) \{\n(.*?)\n    \},", js, re.S)
    assert fxb_m, "缺 _qbDrawFx(装饰面)"
    fxb_code = re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", fxb_m.group(1), flags=re.S))
    for frag in (
        "const canvasH = hasCanvasH ? ctx.canvas.height / px : H;",
        "ctx.rect(L, hasCanvasH ? 0 : T, Math.max(W, canvasW - L), canvasH);",
    ):
        assert frag in fxb_code, f"P6 装饰 clip 上下缘必须放宽到画布边缘(仿 F5 右缘先例): {frag}"
    assert "ringY" not in fxb_code and "yFloor" not in fxb_code, \
        "P6: 环心钳制(ringY)与粒子底缘镜像(yFloor 折回)必须退役(几何回归模板式, 回潮即红)"
    # —— b. 钩子注册序 = I6 层序(vendor 1.6.32 源实证: 主渲染序 clearRect -> Ci("drawClear") ->
    #      Pl.forEach(axes -> series) -> Ci("draw"), 且 Ci("drawAxes") 在 Dl.axes 函数末尾 = 网格
    #      之后、系列之前 —— fx 挂 drawClear 会被网格盖住, 必须挂 drawAxes) ——
    assert "drawClear: [(u) => this._qbDrawGaps(u, tk)]" in js, \
        "drawClear 只挂缺口斜纹(恒最底, 与网格相互独立)"
    assert "drawAxes: [(u) => this._qbDrawFx(u, tk)]" in js, \
        "fx 装饰段必须挂 drawAxes(uPlot 网格之后、系列原生之前 —— 挂 drawClear 被网格盖住违 I6)"
    assert "draw: [(u) => this._qbDrawLimits(u, tk), (u) => this._qbDrawFxCurveGlow(u, tk), (u) => this._qbDrawFxAnchor(u, tk)]" in js, \
        "draw 层序: 限速虚线 -> 曲线辉光(常驻, 系列原生之后/锚段之前) -> 锚段(曲线描边(系列原生)之后)"
    # —— c. 背景零铺色(I11/G7) ——
    fxb = re.search(r"_qbDrawFx\(u, tk\) \{\n(.*?)\n    \},", js, re.S)
    assert fxb, "缺 _qbDrawFx(drawClear 装饰段)"
    fxb_code = re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", fxb.group(1), flags=re.S))
    fxb_tokens = re.sub(r"\s+", " ", fxb_code)  # 切片门跨行写法的 token 级比较(换行/空白不影响判据)
    assert fxb_code.count("fillRect") == 1 and re.search(r"fillRect\([^;]*, th\);", fxb_code), \
        "fx 装饰段 fillRect 必须 = 切片细条恰一处且高度走 th 变量(C2 模板保真二轮: 1.5/Lv.3 2/fixed 3" \
        " —— 整块铺底回潮即红 —— I11/G7)"
    assert 'cfg.palette !== "calm" && (cfg.palette === "glitch" || fx.lv >= 2)' in fxb_tokens, \
        "切片门漂移(C2 + 评审修复 calm 排除: 非 calm 且 (glitch || lv>=2) —— 模板 demo:1086" \
        " isCalm() 早退同口径)"
    assert 'cfg.tear === "fixed" ? 3 : (fx.lv >= 3 ? 2 : 1.5)' in fxb_code, \
        "切片厚度式漂移(C2 模板 demo:1096: fixed 3 / Lv.3 2.0 / 其余 1.5)"
    anb = re.search(r"_qbDrawFxAnchor\(u, tk\) \{\n(.*?)\n    \},", js, re.S)
    assert anb, "缺 _qbDrawFxAnchor(draw 锚段)"
    tlb = re.search(r"_qbTailFrame\(u, a\) \{\n(.*?)\n    \},", js, re.S)
    assert tlb, "缺 _qbTailFrame(次区相位帧)"
    assert "fillRect" not in anb.group(1), "锚段不得有 fillRect(1px 级以外零铺底)"
    assert "fillRect" not in tlb.group(1), "次区光点域不得有 fillRect"
    # —— S4 次区面新口径静态钉(C5/C6/D7, plan §3.4): 旧常量/圆点断言不得回潮 ——
    assert "_QB_FX_TAIL_SPAN_BUCKETS" not in js, "旧末段 6 桶常量未退役(C5)"
    assert "t / 1000 * 0.12 + i / 2 + off" in tlb.group(1), \
        "全宽巡回 ph 公式漂移(模板 demo:1124: ph=(t/1000×0.12 + i/2 + 轨偏移) mod 1)"
    assert 'k === "up" ? 0.31 : 0' in tlb.group(1), "双轨错峰偏移漂移(模板 demo:1124: up=0.31/dl=0)"
    assert "0.3 * (1 - qt)" in tlb.group(1), "alpha 0.3×(1−qt) 线性衰减漂移(峰值 ≤0.3)"
    assert "a.fx.tail" in tlb.group(1) and "v0 == null || v1 == null" in tlb.group(1), \
        "次区资格门(live && level>0)/缺口跳过丢失"
    assert "Math.round(pt.x)" in tlb.group(1), "1px 量化 sig 去重丢失"
    tail_draw = re.search(r'if \(a\.phase === "tail"\) \{\n(.*?)\n      \}\n      const fx = a\.fx;', js, re.S)
    assert tail_draw, "缺 _qbDrawFx tail 相位绘制分支"
    assert "_qbFxPolyPath(ctx, pt.x, pt.y, 2.2, 4, rot)" in tail_draw.group(1), \
        "光点菱形化漂移(C5: 4 边 r2.2 rot=t/500, 复用 _qbFxPolyPath 单点)"
    assert "ctx.arc(" not in tail_draw.group(1), "tail 光点圆点 arc 回潮(静态钉不得留圆点断言)"
    assert "0.14 * (1 - qt)" in tail_draw.group(1) and "ctx.lineWidth = 1" in tail_draw.group(1), \
        "余晖线 lw1/alpha 0.14×(1−qt) 漂移(C6)"
    assert "_qbFxLvColor(fx.lv" in tail_draw.group(1) and "cfg.neon" not in tail_draw.group(1), \
        "余晖线色未走 Lv 表联动或误挂 neon 门(D7)"
    # —— d. I11 黑名单: fx 三域零触碰图例/十字线/系列 ——
    for blk in (fxb.group(1), anb.group(1), tlb.group(1)):
        assert "legend" not in blk and "cursor" not in blk and "u.series" not in blk, \
            "fx 绘制域不得触碰图例/十字线/系列(黑名单元素恒静态基线 —— I11)"
    # —— e. I3 反向钉: fx 四域零销毁重建/零 loading ——
    spb = re.search(r"_qbFxSpawn\(u, tl, dxTip, needsShift, yMax\) \{\n(.*?)\n    \},", js, re.S)
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
