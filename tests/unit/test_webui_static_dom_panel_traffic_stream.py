"""test_webui_static_dom_panel_traffic_stream 测试计划: webui 前端静态守阵: 详情面板 / 弹窗 / 浮层

原 test_webui_static_dom_panel_traffic.py 按域拆分(move-only, 2026-11-27); 测试 ID/名称/断言零变化。

## 测试计划(每个测试函数一条)
- test_frontend_qb_stream_merge_degrade_and_badge_battery: SSE 主路径 node 电池 + 生命周期静态钉(T4a, plan 26-11-18-0037 阶段 3 子波 2; D7/D9/E1/E4/E7) —— 判定帧节拍源换轴后的前端事件驱动面, 行为级真跑(真骨架 polling.js + 真图方法 + EventSource/票据桩): 合并语义纯函数 _qbStreamAppend(t > 列末追加「最新测量」尾点=步进 / t == 列末尾点替代 / 同值重发 false / t < 列末丢弃(GET 竞态不得回退) / 显式空值点透传 / 超预算 500+64 从头截断) + wiring(换票 POST /api/events/ticket -> EventSource ?scope=&ticket= 建流 / 对账 30s + watchdog 两张骨架定时器 / hello+onopen 双源 live) + 数据帧(首帧基线=后端「断档检测在基线之后」契约 / seq 连续推进 / 断档立即 GET 重拉 + 3s 节流防断档风暴 / GET 快照晚于事件按 ts 归并: t > GET 列末保留其余折叠) + 徽标 D3(两文案两态: 滞后 Ns = 末样本 ts vs 墙钟超 3 x si / 已断连 = retry/degraded/pullFail 叠加静默 / connecting 不惊扰; 恢复自动消显; 位置 = 判定线 x/绘图区顶沿, 变值才写; ensure 幂等) + 降级 E7(票据 503 计失败轮, 连续 3 轮 3s/轮失败 -> GET 轮询 qb:<scope> 接管 + 对账停摆 + 60s 保守重试; 恢复 = 流回来撤销降级 + 轮询退役 + 立即对账) + 清理面(_qbStreamStop 收 ES/重试定时器/三张定时器/状态缓冲, 幂等; 重开先停后起不泄漏; 目标未就绪不开流; 落票后复查= polling.js #7 同款竞态窗口); 静态钉: E4 常量五件(对账 30000/静默 3/重连 3000/失败上限 3/降级恢复 60000)+ 尾点预算(500+64)+ _QB_SCOPES stream 构建器三形态(与后端 _parse_scope 同语法)+ 生命周期挂钩(openDrawerTraffic _qbStreamStart / drawer_store 页签 _qbStreamStart("torrent") / _stopDrawerPoll 与 _qbTeardown 收流 / _qbReloadOnEnter _qbStreamResume / 换窗不动流)+ 徽标接线(build ensure + _qbFxAnchorSync 顶部搭车(anc 早退之前, 不受 FX 门控)+ destroy 清记录)+ CSS 单点(transform 右收/pointer-events:none/z-index 2 照 tooltip 惯例, --warn 断连色)+ 会话代际三件(_qbStreamStop 翻代 gen / _qbStreamConnect 两处 await 后核验 / onopen/hello/帧/onerror 四监听器来连核验 st.es === es)+ 失败计数单点(onopen 不清 —— 握手成功 ≠ 可用 / _qbStreamFrame 来帧清); 行为面含 watchdog 静默沿(>3 x si)三检查点: 静默沿立即 GET 重拉一次(D6)+ silentPull 记账防同段静默重复重拉(D6b)+ 新帧到复位(下一次静默重新判, D6c) + A7 名义窗头部修剪真跑(2026-11-21, 修「左移时左边曲线不出窗口而是整列 x 向压缩」): _qbStreamFrame 数据入口面按保留窗剪: 修剪线 = 视口锚 − (span_s + margin=2×组距)(锚缺/无效回落尾点) 剪除头部陈旧点(schema=2 + span_s 门) —— store 列与显示列恒对齐(悬停取值/缺口区段索引零错位面) + 建图触发; 无 span_s 门关不剪(旧后端/agg 回落)。无 node 静默跳过(同 _NODE_QB_TRAFFIC_PROBE 口径)
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

# ==================== SSE 主路径 node 电池 + 生命周期静态钉(T4a, plan 26-11-18-0037 阶段 3
# 子波 2; D7/D9/E1/E4/E7) ====================
# 真骨架(polling.js)+ 真图方法 + EventSource/票据桩: 开连 / seq 断档重拉 / 30s 对账 / GET 竞态
# 归并 / 降级与恢复 / 清理面 / 徽标两文案两态; 纯函数面 _qbStreamAppend(尾点替代/追加/竞态不回退/
# 预算截断)。生命周期挂钩(打开/页签/收口/登出/换窗)为 python 静态钉。无 node 静默跳过(同
# _NODE_QB_TRAFFIC 口径)。
_NODE_QB_STREAM_PROBE = r"""
const fs = require("fs");
global.window = {};
global.document = { hidden: false };
eval(fs.readFileSync(process.argv[1], "utf8"));   // polling.js(骨架)
eval(fs.readFileSync(process.argv[2], "utf8"));   // qb_traffic_chart.js
const P = window.AQB_POLL.methods;
const M = window.AQB_QB_TRAFFIC.methods;
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);
// —— 桩: 定时器捕获(不真跑) / 可控墙钟 / EventSource 桩 / DOM 元素桩 ——
let timers = [];
let tseq = 0;
global.setTimeout = (fn, ms) => { const id = ++tseq; timers.push({ id, fn, ms, cleared: false, fired: false }); return id; };
global.clearTimeout = (id) => { const t = timers.find((x) => x.id === id); if (t) t.cleared = true; };
const fireOne = (ms) => {
  const t = timers.find((x) => !x.cleared && !x.fired && x.ms === ms);
  if (!t) return false;
  t.fired = true;
  t.fn();
  return true;
};
const timerArmed = (ms) => timers.some((x) => !x.cleared && !x.fired && x.ms === ms);
const realNow = Date.now; let off = 0;
Date.now = () => realNow() + off;
const nowS = () => Math.floor((realNow() + off) / 1000);
let esList = [];
global.EventSource = class {
  constructor(url) {
    this.url = url; this.closed = false; this._h = {}; this.onopen = null; this.onerror = null;
    esList.push(this);
  }
  addEventListener(t, fn) { (this._h[t] = this._h[t] || []).push(fn); }
  close() { this.closed = true; }
  emit(t, data) { (this._h[t] || []).forEach((fn) => fn({ data: JSON.stringify(data) })); }
  open() { if (this.onopen) this.onopen(); }
  fail() { if (this.onerror) this.onerror(); }
};
const flush = () => new Promise((r) => setImmediate(r));
const META = { interval_s: 30, sample_interval_s: 1.5, schema: 2, stride: 1 };
function mkVm(over) {
  const v = Object.assign({
    qbTrafficOn: true, drawerIsTraffic: true, drawer: { open: true, scope: "global" },
    page: "groups", qbHistWindow: "24h", qbHistData: null, qbHistLoading: false, qbHistError: "",
    authOk: true, apiCalls: [], apiFail: false, apiData: null,
    _qbCharts: null,
  }, over || {});
  Object.assign(v, M, { _qbChartBuild: () => {} });   // 真方法全域 + 建图桩(帧合并只验数据面)
  v.$nextTick = (fn) => { if (fn) fn(); };   // 渲染等价桩: 同步 flush(落袋/合并后当帧见数)
  v.startPoll = P.startPoll;
  v.stopPoll = P.stopPoll;
  v.api = async (path, opts) => {
    v.apiCalls.push({ path, opts: opts || {} });
    if (v.apiFail) throw new Error(v.apiFailMsg || "HTTP 503");
    if (path === "/api/events/ticket") return { ticket: "T-" + (v.ticketSeq = (v.ticketSeq || 0) + 1), ttl: 30 };
    return JSON.parse(JSON.stringify(v.apiData
      || { points: [], totals: [], limits: [], meta: META }));
  };
  return v;
}
const COL = (tEnd, n) => {
  // 造一列 n 个点(t 步进 30, 末点 t = tEnd, 升序)
  const pts = [];
  for (let i = 0; i < n; i++) pts.push({ t: tEnd - (n - 1 - i) * 30, dl: 1 + i, up: 2 + i });
  return { points: pts, totals: [], limits: [], meta: META };
};

(async () => {
  // —— A: 纯函数 _qbStreamAppend(合并语义三分支 + 预算截断 + 缓冲记账) ——
  {
    const pts = [{ t: 100, dl: 1, up: 2 }];
    const tail = [];
    ok("A1 t > 列末 -> 追加「最新测量」尾点(步进) + tail 缓冲同步登记",
      _qbStreamAppend(pts, tail, { t: 130, dl: 3, up: 4 }, 564) === true && pts.length === 2
      && pts[1].t === 130 && tail.length === 1 && tail[0].t === 130);
    ok("A2 t == 列末 -> 尾点替代(同 tick 重发/尾组刷新)",
      _qbStreamAppend(pts, tail, { t: 130, dl: 9, up: 4 }, 564) === true && pts.length === 2
      && pts[1].dl === 9 && tail.length === 1 && tail[0].dl === 9);
    ok("A3 同值重发 -> false(零变化不触发重画)",
      _qbStreamAppend(pts, tail, { t: 130, dl: 9, up: 4 }, 564) === false && pts.length === 2);
    ok("A4 t < 列末 -> 丢弃(GET 竞态纪律: 不得回退)",
      _qbStreamAppend(pts, tail, { t: 90, dl: 0, up: 0 }, 564) === false && pts[0].t === 100);
    const q = [{ t: 200, dl: null, up: null }];
    const tq = [];
    _qbStreamAppend(q, tq, { t: 230, dl: null, up: null }, 564);
    ok("A5 显式空值点透传(缺口真值, dl/up = null 原样)", q[1].dl === null && q[1].up === null);
    const big = []; const tbig = [];
    let adv = false;
    for (let i = 0; i < 600; i++) adv = _qbStreamAppend(big, tbig, { t: i * 10, dl: i, up: i }, 564) || adv;
    ok("A6 超预算(MAN_RAW 500 + 余量 64)从头截断(防御双通道同故障的无界增长)",
      big.length === 564 && big[0].t === 360 && tbig.length === 564);
    // —— A7: 保留窗头部修剪(计划 26-11-22-0858 换代, _qbStreamFrame 数据入口面): 修剪线 =
    //          视口锚 − (span_s + margin)(margin = 2×组距), 锚缺/无效回落尾点 ——
    //          视口左缘滑动期余量列, store 列与显示列恒对齐(单列恒等)——
    {
      const col = COL(1030, 11);   // t = 730..1030 步进 30(跨度 300)
      col.points = [{ t: 640, dl: 1, up: 2 }].concat(col.points);  // 头部补陈旧点(t=640, 余量线外)
      col.meta = { interval_s: 30, sample_interval_s: 1.5, schema: 2, stride: 1, span_s: 300 };
      const v = mkVm({ qbHistData: col, _qbStreams: { global: { want: true, tail: [], seq: null, lastT: 0 } } });
      let buildCalls = 0;
      v._qbChartBuild = () => { buildCalls += 1; };
      v._qbStreamFrame("global", { seq: 5, points: [{ t: 1060, dl: 9, up: 9 }] });
      // 尾点 1060 -> 保留线 1060 - (300 + 2x30) = 700: 头部 640 剪除(点列 13 -> 12), 700..730
      // 在余量区内保留(视口左缘滑动期的真实历史裁剪数据), store 列即修剪列
      ok("A7 修剪在数据入口面落地: store 列头部陈旧点剪除(首点 640 -> 730, 余量线 700 内的"
        + " 700/730 保留)+ 尾点推进(1060) + store/显示列同源(悬停索引零错位) + 建图触发",
        v.qbHistData.points.length === 12 && v.qbHistData.points[0].t === 730
        && v.qbHistData.points[11].t === 1060 && buildCalls === 1);
      const col2 = COL(1030, 11);
      col2.points = [{ t: 640, dl: 1, up: 2 }].concat(col2.points);   // META 无 span_s: 门关
      const v2 = mkVm({ qbHistData: col2, _qbStreams: { global: { want: true, tail: [], seq: null, lastT: 0 } } });
      v2._qbChartBuild = () => {};
      v2._qbStreamFrame("global", { seq: 6, points: [{ t: 1060, dl: 9, up: 9 }] });
      ok("A7 对照(无 span_s 门关, 旧后端/agg 回落): 列原样不剪(首点 640 保留, 尾点照常追加)",
        v2.qbHistData.points.length === 13 && v2.qbHistData.points[0].t === 640
        && v2.qbHistData.points[12].t === 1060);
      // —— A7b GET 落地历史保留合并行为(尾锚显式视口不变量(2)调用面, 评审轮2 minor):
      //    keepLine = 视口锚 − (span + margin) 锚优先 —— 旧列余量区真值点并入列头 ——
      {
        const col3 = COL(1030, 11);   // t = 730..1030
        col3.meta = { interval_s: 30, sample_interval_s: 1.5, schema: 2, stride: 1, span_s: 300 };
        const v3 = mkVm({ qbHistData: col3, _qbStreams: { global: { want: true, tail: [], seq: null, lastT: 0 } } });
        v3._qbChartBuild = () => {};
        // 锚领先尾(旧窗响应落袋形态): 图记录锚 = 1060(尾 1030 前方 30s)
        v3._qbCharts = { global: { root: { isConnected: true }, data: col3.points.slice(),
          _qbBeat: { raf: 0, anim: null, anchor: 1060, step: 30, span: 300, tracks: {} } } };
        const oldPts3 = [{ t: 610, dl: 1, up: 2 }, { t: 640, dl: 1, up: 2 }, { t: 670, dl: 1, up: 2 }];
        const fresh3 = { points: buildCol(1000, 4), totals: [], limits: [], meta: col3.meta };
        function buildCol(t0, n) { const a = []; for (let i = 0; i < n; i++) a.push({ t: t0 + i * 30, dl: 1, up: 2 }); return a; }
        v3.qbHistData = fresh3;   // 真实流程: _qbLoad 先整列替换再调 _qbStreamOnLoad
        v3._qbStreamOnLoad("global", fresh3, oldPts3);
        // keepLine = max(锚 1060, 尾 1090) − 300 − 60 = 730 -> 旧列 610/640/670 全线外不并入,
        // 新列 [1000..1090] 全保留 —— 锚领先尾时不产生越线并入(负样本)
        const kept3 = v3.qbHistData.points;
        ok("A7b 保留合并(锚领先尾): keepLine 按视口锚, 线外旧点不并入(负样本), 列尾推进",
          kept3.length === fresh3.points.length && kept3[0].t === 1000
          && kept3[kept3.length - 1].t === 1090);
        // 正样本: 旧列含余量区真值点(锚 1060, 线 = 1060 − 360 = 700, 旧列 700..730 并入)
        const v4 = mkVm({ qbHistData: col3, _qbStreams: { global: { want: true, tail: [], seq: null, lastT: 0 } } });
        v4._qbChartBuild = () => {};
        v4._qbCharts = { global: { root: { isConnected: true }, data: col3.points.slice(),
          _qbBeat: { raf: 0, anim: null, anchor: 1060, step: 30, span: 300, tracks: {} } } };
        const oldPts4 = [{ t: 700, dl: 1, up: 2 }, { t: 715, dl: 1, up: 2 }, { t: 670, dl: 1, up: 2 }];
        const fresh4 = { points: [{ t: 1060, dl: 1, up: 2 }], totals: [], limits: [], meta: col3.meta };
        v4.qbHistData = fresh4;   // 同上: 整列替换先行
        v4._qbStreamOnLoad("global", fresh4, oldPts4);
        const kept4 = v4.qbHistData.points;
        ok("A7b 正样本: 旧列余量区点(700/715 >= 线 700)并入列头, 线外(670)弃, 升序不破",
          kept4.length === 3 && kept4[0].t === 700 && kept4[2].t === 1060
          && kept4.every((p, i) => i === 0 || p.t > kept4[i - 1].t));
      }
    }
  }
  // —— B: 开流 wiring(票据 -> EventSource -> live) ——
  const v = mkVm();
  v.qbHistData = COL(1030, 2);
  v._qbStreamStart("global");
  await flush(); await flush(); await flush();
  ok("B1 换票一次(POST /api/events/ticket) + EventSource 以 scope&ticket 建流",
    v.apiCalls.length === 1 && v.apiCalls[0].path === "/api/events/ticket"
    && v.apiCalls[0].opts.method === "POST"
    && esList.length === 1
    && esList[0].url === "/api/traffic/qb/stream?scope=global&ticket=T-1");
  ok("B2 对账 30s + watchdog 两张骨架定时器在表(qb-acc/qb-wd)",
    !!v._polls["qb-acc:global"] && !!v._polls["qb-wd:global"] && !v._polls["qb:global"]);
  const es = esList[0];
  ok("B3 流状态 connecting(票据/握手在途)", v._qbStreams.global.state === "connecting");
  es.emit("hello", { ok: true, scope: "global" });
  ok("B3b live(hello 开流标记 —— 双源汇一)", v._qbStreams.global.state === "live"
    && v._qbStreams.global.failRun === 0);   // 握手成功不清失败计数(R2: 清零认帧不认握手)
  es.open();
  ok("B3c onopen 同源幂等(已 live 再开零变化)", v._qbStreams.global.state === "live");
  const callsR = v.apiCalls.length;
  const esR = esList.length;
  v._qbStreamResume("global");
  ok("B3d 进场核对零操作(_qbStreamResume: 流在场 want=true 直返 —— 核对丢失即拆流重建)",
    esList.length === esR && v.apiCalls.length === callsR
    && v._qbStreams.global.state === "live" && v._qbStreams.global.want === true);
  // —— C: 数据帧(首帧基线 / 尾点替代推进 / seq 断档重拉) ——
  es.emit("traffic", { seq: 1, scope: "global", points: [{ t: 1030, dl: 30, up: 40 }] });
  ok("C1 首帧基线(断档检测在基线之后) + 同 t 尾点替代(GET 组尾点被事件样本真值替代 —— 步进)",
    v._qbStreams.global.seq === 1 && v.qbHistData.points.length === 2
    && v.qbHistData.points[1].t === 1030 && v.qbHistData.points[1].dl === 30);
  es.emit("traffic", { seq: 2, scope: "global", points: [{ t: 1060, dl: 5, up: 6 }] });
  ok("C2 seq 连续 + 新样本尾点追加(每 tick 替代推进) + tail 缓冲登记",
    v._qbStreams.global.seq === 2 && v.qbHistData.points.length === 3
    && v.qbHistData.points[2].t === 1060
    && v._qbStreams.global.tail.length === 2 && v._qbStreams.global.tail[1].t === 1060);
  const callsC3 = v.apiCalls.length;
  es.emit("traffic", { seq: 9, scope: "global", points: [{ t: 1090, dl: 7, up: 8 }] });
  ok("C3 seq 断档(队列满丢弃留痕) -> seq 重基线 + 立即 GET 重拉(D9)",
    v._qbStreams.global.seq === 9 && v.apiCalls.length === callsC3 + 1
    && v.apiCalls[v.apiCalls.length - 1].path.indexOf("/api/traffic/qb/global") === 0);
  await flush(); await flush();
  ok("C3b 重拉落袋: GET 空列(无样本)时事件尾点缓冲全量归并回显示列",
    v.qbHistData.points.length === 3 && v.qbHistData.points[2].t === 1090);
  // C4 重拉节流: 3s 内重复断档不再打 GET(防断档风暴)
  const callsC4 = v.apiCalls.length;
  es.emit("traffic", { seq: 20, scope: "global", points: [{ t: 1120, dl: 1, up: 1 }] });
  ok("C4 重拉 3s 节流(断档风暴防御): 节流窗内断档只重基线不发 GET",
    v._qbStreams.global.seq === 20 && v.apiCalls.length === callsC4);
  // —— C6(评审 T4a-R3/R2): ES onerror 路径 + 失败计数语义(清零认帧不认握手) ——
  {
    const vo = mkVm();
    vo.qbHistData = COL(1030, 2);
    vo._qbStreamStart("global");
    await flush(); await flush(); await flush();
    const eo = esList[esList.length - 1];
    eo.open();
    eo.emit("traffic", { seq: 1, scope: "global", points: [{ t: 1030, dl: 1, up: 1 }] });
    ok("C6pre live 且来帧计数归零(基线)", vo._qbStreams.global.state === "live"
      && vo._qbStreams.global.failRun === 0 && vo._qbStreams.global.es === eo);
    eo.fail();
    ok("C6a ES onerror(live->retry): 关连(st.es=null) + 计失败轮 1 + 3s 换票重开定时器"
      + "(漏置 null = 双连叠加/漏汇 retry = 永不降级, 任一回归即红)",
      eo.closed === true && vo._qbStreams.global.es === null
      && vo._qbStreams.global.state === "retry" && vo._qbStreams.global.failRun === 1
      && timerArmed(3000));
    fireOne(3000); await flush(); await flush(); await flush();
    const eo2 = esList[esList.length - 1];
    eo2.open();   // 握手成功但零帧(空闪连形态)
    ok("C6b 握手成功不清失败计数(onopen 不清 —— 空闪连 0/1 振荡形态被打破, R2)",
      vo._qbStreams.global.state === "live" && vo._qbStreams.global.failRun === 1);
    eo2.fail();
    ok("C6c 空闪连第 2 轮: 计轮 2(可积累到上限降级, E7 可达性)",
      vo._qbStreams.global.failRun === 2 && vo._qbStreams.global.state === "retry");
    fireOne(3000); await flush(); await flush(); await flush();
    const eo3 = esList[esList.length - 1];
    eo3.open();
    eo3.emit("traffic", { seq: 2, scope: "global", points: [{ t: 1060, dl: 2, up: 2 }] });
    ok("C6d 来帧清零(正常瞬断形态: 流过数据后断, 重连来帧即归零不积累)",
      vo._qbStreams.global.failRun === 0 && vo._qbStreams.global.state === "live");
    eo3.fail();
    ok("C6e 瞬断后再断: 计轮从 1 起算(前轮已被帧清零)",
      vo._qbStreams.global.failRun === 1 && timerArmed(3000));
    vo._qbStreamStop("global");
  }
  // —— C6f(评审 T4a-R3): 混合计轮(票据失败 1 轮 + ES 失败 2 轮交叉)达 3 -> 降级 ——
  {
    const vp = mkVm();
    vp.apiFail = true; vp.apiFailMsg = "HTTP 503";
    vp._qbStreamStart("global");
    await flush(); await flush(); await flush();   // 票据失败轮 1
    vp.apiFail = false;
    fireOne(3000); await flush(); await flush(); await flush();   // 重开: 建流成功
    const ep = esList[esList.length - 1];
    ep.open();                                     // 握手成功(零帧, 不清轮 —— R2)
    ep.fail();                                     // ES 失败轮 2
    fireOne(3000); await flush(); await flush(); await flush();   // 重开
    const ep2 = esList[esList.length - 1];
    ep2.open();
    ep2.fail();                                    // ES 失败轮 3 -> 降级
    ok("C6f 混合计轮(票据 1 + ES 2 交叉)达 3 -> 降级 GET 轮询接管(E7)",
      vp._qbStreams.global.failRun === 3 && vp._qbStreams.global.degraded === true
      && !!vp._polls["qb:global"]);
    vp._qbStreamStop("global");
  }
  // —— C5: GET 快照晚于事件(竞态归并): t > GET 列末 t 的尾点保留, t <= 的视为已折叠 ——
  {
    const v2 = mkVm();
    v2.qbHistData = COL(1030, 2);
    v2.apiData = COL(1030, 2);   // GET 列末 t = 1030
    v2._qbStreamStart("global");
    await flush(); await flush(); await flush();
    const e2 = esList[esList.length - 1];
    e2.open();
    e2.emit("traffic", { seq: 1, scope: "global", points: [{ t: 1030, dl: 30, up: 40 }] });
    e2.emit("traffic", { seq: 2, scope: "global", points: [{ t: 1060, dl: 5, up: 6 }] });
    v2.qbHistData = JSON.parse(JSON.stringify(v2.apiData));   // 模拟 _qbLoad 落袋次序(先换数据)
    v2._qbStreamOnLoad("global", v2.apiData);                 // 再做对账归并(生产同序)
    ok("C5 GET 竞态归并: t > GET列末 的事件尾点保留(1060), t <= 的被组粒度列折叠(1030 回 GET 真值)",
      v2.qbHistData.points.length === 3 && v2.qbHistData.points[1].t === 1030
      && v2.qbHistData.points[1].dl === 2 && v2.qbHistData.points[2].t === 1060
      && v2._qbStreams.global.tail.length === 1 && v2._qbStreams.global.tail[0].t === 1060);
    ok("C5b GET 落袋 = 对账基准: pullFail 复位 + lastT 归位(取最新已知样本 ts)",
      v2._qbStreams.global.pullFail === false && v2._qbStreams.global.lastT === 1060);
  }
  // —— D: 徽标(两文案两态 / 恢复消显 / 位置同步) ——
  {
    function mkEl() {
      return {
        className: "", style: {}, textContent: "", isConnected: true, parentElement: null, children: [],
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
    global.document.createElement = () => mkEl();
    const wrap = mkEl();
    const u = {
      root: { isConnected: true, querySelector: (s) => (s === ".u-wrap" ? wrap : null) },
      _wrap: wrap, bbox: { left: 60, top: 10, width: 800, height: 300 }, data: [],
      _qbScope: "global",
    };
    v._qbCharts = { global: u };
    v._qbStallBadgeEnsure(u);
    ok("D1 徽标建面: .qb-stall-badge 挂 .u-wrap(.u-wrap 末位) + 初始隐藏",
      !!u._qbStallBadge && u._qbStallBadge.className === "qb-stall-badge"
      && wrap.children[wrap.children.length - 1] === u._qbStallBadge
      && u._qbStallBadge.style.display === "none");
    v._qbStallBadgeEnsure(u);
    ok("D1b ensure 幂等(再调零操作 —— 与 _qbFxAnchorEnsure 同款纪律)",
      wrap.children.length === 1 && u._qbStallBadge === wrap.children[0]);
    const st = v._qbStreams.global;
    st.state = "live"; st.degraded = false; st.pullFail = false;
    st.lastT = nowS() - 100;   // 末样本落后墙钟 100s
    v.qbHistData.meta = Object.assign({}, META);   // si = 1.5 -> 阈值 4.5s
    v._qbStallBadgeSync(u);
    ok("D2 冻结态: 「滞后 Ns」(N = 末样本 ts vs 墙钟取整) + qb-stall-down 类不在",
      /^滞后 \d+s$/.test(u._qbStallBadge.textContent)
      && !u._qbStallBadge.classList.contains("qb-stall-down")
      && u._qbStallBadge.style.display === "");
    ok("D2b 位置 = 判定线 x(bbox 右缘 860)/绘图区顶沿(10+3) —— 尾点旁不遮菱形",
      u._qbStallBadge.style.left === "860px" && u._qbStallBadge.style.top === "13px");
    u._qbStallBadge.style.left = "keep";
    v._qbStallBadgeSync(u);
    ok("D2c 同位置重同步零改写(变值才写)", u._qbStallBadge.style.left === "keep");
    st.pullFail = true;
    v._qbStallBadgeSync(u);
    ok("D3 静默叠加对账失败 -> 升格「已断连」(两条取数路径都断) + qb-stall-down 类挂",
      u._qbStallBadge.textContent === "已断连"
      && u._qbStallBadge.classList.contains("qb-stall-down"));
    st.pullFail = false;
    st.lastT = nowS();   // 新帧到: 沉默解除
    v._qbStallBadgeSync(u);
    ok("D4 恢复(新帧到/seq 续上)徽标自动消显", u._qbStallBadge.style.display === "none");
    st.state = "retry";
    v._qbStallBadgeSync(u);
    ok("D5a 重连中(retry)-> 「已断连」(流断开且重连中)", u._qbStallBadge.textContent === "已断连");
    st.state = "live"; st.degraded = true;
    v._qbStallBadgeSync(u);
    ok("D5b 降级态 -> 「已断连」照显(E7)", u._qbStallBadge.textContent === "已断连");
    st.degraded = false; st.state = "connecting"; st.lastT = nowS() - 100;
    v._qbStallBadgeSync(u);
    ok("D5c connecting(票据/握手在途)不惊扰: 隐藏", u._qbStallBadge.style.display === "none");
    st.state = "stopped";
    v._qbStallBadgeSync(u);
    ok("D5d 流已停: 隐藏(want=false 同)", u._qbStallBadge.style.display === "none");
    // D6 静默沿立即 GET 重拉(watchdog 行为面): live + 静默超 3 x si -> 一次 GET
    // (墙钟前跳 10s: 越过 C3 重拉的 3s 节流窗 —— 本拍重拉是对账节流之外的独立通道)
    off += 10000;
    st.state = "live"; st.lastT = nowS() - 100; st.silentPull = false;
    const callsD6 = v.apiCalls.length;
    v._qbStallTick("global");
    ok("D6 静默沿(>3 x si)watchdog 立即 GET 重拉一次(D9) + silentPull 记账防重复",
      v.apiCalls.length === callsD6 + 1 && st.silentPull === true);
    v._qbStallTick("global");
    ok("D6b 同一段静默内不重复重拉(30s 对账兜周期)", v.apiCalls.length === callsD6 + 1);
    es.emit("traffic", { seq: 30, scope: "global", points: [{ t: nowS(), dl: 1, up: 1 }] });
    ok("D6c 新帧到: silentPull 复位(下一次静默重新判)", st.silentPull === false);
    // —— D7(评审 T4a-R4): pullFail 生产分支 —— 流活时对账 GET 失败(feeding 门内):
    //     pullFail 记账 + 数据不清 + 错误态不亮(回旧语义 = 对账失败闪空态一帧, 回归即红) ——
    {
      await flush(); await flush();   // D6 静默重拉的 GET 落定(loading 复位, 计时起点不叠)
      off += 10000;                   // 越过 D6 重拉的 3s 节流窗
      st.lastT = nowS();              // 静默解除基线(徽标先隐)
      v._qbStallBadgeSync(u);
      ok("D7 pre 徽标隐藏(数据面新鲜)", u._qbStallBadge.style.display === "none");
      v.apiFail = true; v.apiFailMsg = "HTTP 500";
      const dataBefore = v.qbHistData;
      const errBefore = v.qbHistError;
      v._qbReconcile("global");
      await flush(); await flush();
      ok("D7a 对账 GET 失败(feeding 门): pullFail 记账 + 显示列不清 + 错误态不亮",
        st.pullFail === true && v.qbHistData === dataBefore
        && v.qbHistError === errBefore && v.qbHistData !== null);
      st.lastT = nowS() - 100;        // 静默叠加 -> 徽标升格
      v._qbStallBadgeSync(u);
      ok("D7b 静默叠加对账失败: 徽标升格「已断连」(两条取数路径都断)",
        u._qbStallBadge.textContent === "已断连");
      v.apiFail = false;
      v.apiData = COL(2000, 3);
      v._qbStreamPullNow("global", true);   // 对账恢复(force: 生产 _qbLoad 全链)
      await flush(); await flush();
      ok("D7c 对账恢复: pullFail 复位 + 徽标退回(「已断连」升格撤销)",
        st.pullFail === false && u._qbStallBadge.textContent.indexOf("已断连") < 0);
      v.apiData = null;
    }
  }
  // —— E: 降级路径(E7: 票据 503 / 连续 3 轮失败 -> GET 轮询兜底; 60s 保守重试恢复) ——
  {
    const v3 = mkVm();
    v3.apiFail = true; v3.apiFailMsg = "HTTP 503";
    const esE = esList.length;
    v3._qbStreamStart("global");
    await flush(); await flush(); await flush();
    ok("E1 票据 503: 计失败轮 1 + 3s 换票重开定时器(照 polling.js 重试纪律)",
      v3._qbStreams.global.state === "retry" && v3._qbStreams.global.failRun === 1
      && timerArmed(3000) && esList.length === esE);   // 建流失败: 无新 ES 实例
    fireOne(3000); await flush(); await flush(); await flush();
    ok("E2 第 2 轮失败: 仍 retry(未达上限)", v3._qbStreams.global.failRun === 2
      && v3._qbStreams.global.degraded === false);
    fireOne(3000); await flush(); await flush(); await flush();
    ok("E3 连续 3 轮失败 -> 降级: GET 轮询接管(qb:global 在表) + 对账停摆 + 60s 恢复定时器",
      v3._qbStreams.global.degraded === true && v3._qbStreams.global.state === "degraded"
      && !!v3._polls["qb:global"] && timerArmed(60000));
    const callsE3 = v3.apiCalls.length;
    v3._qbReconcile("global");
    ok("E3b 降级态对账停摆(_qbStreamPullNow 的 degraded 门)", v3.apiCalls.length === callsE3);
    // 60s 重试(仍失败) -> 再走 retry -> 3 轮 -> 降级(已降级不重复拉轮询)
    fireOne(60000); await flush(); await flush(); await flush();
    fireOne(3000); await flush(); await flush(); await flush();
    fireOne(3000); await flush(); await flush(); await flush();
    fireOne(3000); await flush(); await flush(); await flush();
    ok("E4 降级恢复失败循环: 仍降级 + 轮询不重复重启(幂等)",
      v3._qbStreams.global.degraded === true && !!v3._polls["qb:global"] && timerArmed(60000));
    // 恢复: 票据/建流成功 -> live -> 降级撤销 + GET 轮询退役 + 立即对账
    v3.apiFail = false;
    v3.apiData = COL(2000, 3);
    fireOne(60000); await flush(); await flush(); await flush();
    const e3 = esList[esList.length - 1];
    e3.open();
    await flush(); await flush();
    ok("E5 流恢复: 降级撤销 + GET 轮询退役(qb:global 摘除) + 回 live",
      v3._qbStreams.global.degraded === false && v3._qbStreams.global.state === "live"
      && v3._polls["qb:global"] == null);
    ok("E5b 恢复后立即对账一次(轮询期可能积了滞后)",
      v3.apiCalls.some((c) => c.path.indexOf("/api/traffic/qb/global") === 0)
      && v3.qbHistData.points.length === 3);
    v3._qbStreamStop("global");
  }
  // —— F: 清理面(照 stopEvents 四件; 幂等) ——
  {
    // F0(评审 T4a-R6): 关流清「在挂的重试定时器」—— 先制造一轮票据失败(3s 定时器在挂)再关流
    const v7 = mkVm();
    v7.apiFail = true; v7.apiFailMsg = "HTTP 503";
    v7._qbStreamStart("global");
    await flush(); await flush(); await flush();   // 轮 1 失败 -> 3s 重试定时器在挂
    ok("F0 pre: 重试定时器确在挂(非空转前提)", timerArmed(3000)
      && v7._qbStreams.global.state === "retry");
    v7._qbStreamStop("global");
    ok("F0 关流清在挂重试定时器(fireOne 无拍可点 -> 不会再触发 connect)+ 单柄置 null + state 归位",
      !timerArmed(3000) && v7._qbStreams.global.retry === null
      && v7._qbStreams.global.state === "stopped");
    const v4 = mkVm();
    v4.qbHistData = COL(1030, 2);
    v4._qbStreamStart("global");
    await flush(); await flush(); await flush();
    const es4 = esList[esList.length - 1];
    es4.open();
    es4.emit("traffic", { seq: 1, scope: "global", points: [{ t: 1030, dl: 9, up: 9 }] });
    v4._qbStreamStop("global");
    ok("F1 关流: ES close + retry 清 + 三张定时器(qb-acc/qb-wd/qb)全收 + 状态归位",
      es4.closed === true && !timerArmed(3000) && !timerArmed(60000)
      && v4._polls["qb-acc:global"] == null && v4._polls["qb-wd:global"] == null
      && v4._polls["qb:global"] == null
      && v4._qbStreams.global.state === "stopped" && v4._qbStreams.global.want === false);
    ok("F1b 缓冲/seq/沉默基线随停流归置(重开零残留)",
      v4._qbStreams.global.tail.length === 0 && v4._qbStreams.global.seq === null
      && v4._qbStreams.global.lastT === 0 && v4._qbStreams.global.pullFail === false);
    v4._qbStreamStop("global");
    ok("F2 关流幂等(未开也安全, 重复调用零异常零变化)",
      v4._qbStreams.global.state === "stopped" && v4._qbStreams.global.want === false);
    const esBefore = esList.length;
    v4._qbStreamStart("global");
    await flush(); await flush(); await flush();
    ok("F3 重开: 先停后起(重复开连不泄漏 —— 恰一条新 ES)",
      esList.length === esBefore + 1 && v4._qbStreams.global.want === true);
    v4._qbStreamStop("global");
    // F4 目标未就绪(torrent 无 hash)不开流(防御: 空目标 URL 必 400)
    const v5 = mkVm({ drawer: { open: true, scope: "global" }, drawerIsTraffic: true });
    const esBefore5 = esList.length;
    v5._qbStreamStart("torrent");   // drawer.hash 缺失 -> stream() 给 "torrent:" -> 拒开
    ok("F4 目标未就绪(torrent 无 hash)不开流不发请求", esList.length === esBefore5
      && v5.apiCalls.length === 0);
    // F5 落票后复查(await 期间已停流): 票据到手但代际已翻(want 亦清) -> 不建流
    const esBefore6 = esList.length;
    const v6 = mkVm();
    v6._qbStreamStart("global");
    v6._qbStreamStop("global");   // await 换票期间关流(代际翻新)
    await flush(); await flush(); await flush();
    ok("F5 落票后复查(polling.js #7 同款竞态窗口 + 代际判据): 停流后落票不建流",
      esList.length === esBefore6 && v6._qbStreams.global.state === "stopped");
  }
  // —— G: 会话代际(评审 T4a-R1): stop/restart 翻代 —— 在途换票 continuation 落票即弃 ——
  {
    // a. 重开竞态(页签/抽屉在换票 RTT 内关-开): 旧 continuation 带票丢弃, 恰一条新 ES
    //    (无双建: 双建时 st.es 后写覆盖前写 = 先建 ES 永不 close 的订阅泄漏)
    const vg = mkVm();
    const esG = esList.length;
    vg._qbStreamStart("global");        // connect A 在途(换票 await)
    vg._qbStreamStop("global");         // 代际翻新 + 复位 busy 门
    vg._qbStreamStart("global");        // 新会话 connect B 在途
    await flush(); await flush(); await flush();
    ok("G1 重开竞态: 旧 continuation 带票丢弃不建流(恰一条新 ES —— 双建即泄漏)",
      esList.length === esG + 1 && vg.apiCalls.length === 2   // 两次换票都发出(旧票弃置)
      && vg._qbStreams.global.want === true && vg._qbStreams.global.gen >= 2);
    esList[esList.length - 1].open();
    ok("G1b 新会话状态完好(live 可达)", vg._qbStreams.global.state === "live");
    vg._qbStreamStop("global");
    // b. 在途重试定时器触发的 connect 被 stop 打断(同代际面)
    const vh = mkVm();
    vh.apiFail = true; vh.apiFailMsg = "HTTP 503";
    const esH = esList.length;
    vh._qbStreamStart("global");
    await flush(); await flush(); await flush();   // 轮 1 失败 -> 3s 重试定时器
    vh.apiFail = false;
    fireOne(3000);                      // 重试触发的 connect C 在途(换票 await)
    vh._qbStreamStop("global");         // 代际翻新: connect C 作废
    vh._qbStreamStart("global");        // 新会话 connect D
    await flush(); await flush(); await flush();
    ok("G2 在途重试触发的 connect 被 stop 打断: 旧 continuation 同样带票弃置(恰一条新 ES)",
      esList.length === esH + 1 && vh._qbStreams.global.want === true);
    esList[esList.length - 1].open();
    ok("G2b 新会话 live(重试路径同受代际保护)", vh._qbStreams.global.state === "live");
    vh._qbStreamStop("global");
    // c. 旧连监听器不误伤新会话(来连核验 st.es === es 三面: onerror/onopen/帧)
    const vk = mkVm();
    vk.qbHistData = COL(1030, 2);
    vk._qbStreamStart("global");
    await flush(); await flush(); await flush();
    const ek = esList[esList.length - 1];
    ek.open();
    const ghost = new global.EventSource("/api/traffic/qb/stream?scope=global&ticket=ghost");
    vk._qbStreams.global.es = ghost;    // 手工接管: 模拟新会话已建流、旧连未及 close 的窗口
    const callsK = vk.apiCalls.length;
    ek.fail();
    ok("G3 旧连 onerror: 不动新会话(st.es 保持 ghost / state 不翻 retry / 零重试定时器 / 零新请求)",
      vk._qbStreams.global.es === ghost && vk._qbStreams.global.state === "live"
      && !timerArmed(3000) && vk.apiCalls.length === callsK);
    ek.emit("traffic", { seq: 9, scope: "global", points: [{ t: 1090, dl: 7, up: 8 }] });
    ok("G3b 旧连帧: 不改写新会话显示列(合并零发生)",
      vk.qbHistData.points.length === 2 && vk.qbHistData.points[1].t === 1030);
    vk._qbStreams.global.state = "connecting";   // 模拟 ghost 会话仍在握手
    ek.open();
    ok("G3c 旧连 onopen 不改写新会话状态(仍 connecting —— 防旧连监听器改写 st)",
      vk._qbStreams.global.state === "connecting");
    vk._qbStreamStop("global");
  }
  // —— H: 隐藏渲染节流(评审 T4a-R5): 帧照常合并、建图跳过; 回场恢复 ——
  {
    const vz = mkVm();
    let builds = 0;
    vz._qbChartBuild = () => { builds += 1; };
    vz.qbHistData = COL(1030, 2);
    vz._qbStreamStart("global");
    await flush(); await flush(); await flush();
    const ez = esList[esList.length - 1];
    ez.open();
    ez.emit("traffic", { seq: 1, scope: "global", points: [{ t: 1030, dl: 9, up: 9 }] });
    ok("H1 可见态帧: 合并 + 建图照走(基线)", vz.qbHistData.points[1].dl === 9 && builds === 1);
    global.document.hidden = true;
    ez.emit("traffic", { seq: 2, scope: "global", points: [{ t: 1060, dl: 5, up: 6 }] });
    ok("H2 隐藏期帧: 合并照常(列推进)但建图跳过(渲染节流 —— 极性反转即红)",
      vz.qbHistData.points.length === 3 && vz.qbHistData.points[2].t === 1060 && builds === 1);
    global.document.hidden = false;
    ez.emit("traffic", { seq: 3, scope: "global", points: [{ t: 1090, dl: 7, up: 8 }] });
    ok("H3 回场: 建图恢复(下一帧补上渲染)", builds === 2 && vz.qbHistData.points[3].t === 1090);
    vz._qbStreamStop("global");
  }
  console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
    failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
})().catch((e) => { console.error("PROBE CRASH: " + (e && e.stack || e)); process.exit(1); });
"""


def test_frontend_qb_stream_merge_degrade_and_badge_battery():
    """SSE 主路径 node 电池 + 生命周期静态钉(T4a, plan 26-11-18-0037 阶段 3 子波 2)

    判定帧节拍源换轴(D7)后的前端事件驱动面, 行为级真跑(真骨架 + 真图方法 + 桩):
    - 合并语义(模块级 _qbStreamAppend 纯函数): t > 列末追加「最新测量」尾点(步进) / t == 列末
      尾点替代 / 同值重发 false / t < 列末丢弃(GET 竞态不得回退) / 显式空值点透传 / 超预算
      (500+64)从头截断;
    - wiring: 换票(POST /api/events/ticket)-> EventSource(?scope=&ticket=) 建流; 对账 30s +
      watchdog 两张骨架定时器; live 状态经 onopen/hello 双源; 进场核对零操作
      (_qbStreamResume: 流在场 want=true 直返, 不重连不发票 —— B3d);
    - 数据帧: 首帧基线(断档检测在基线之后, 后端契约)/ seq 连续推进 / 断档立即 GET 重拉 +
      3s 节流防断档风暴 / GET 快照晚于事件按 ts 归并(t > GET 列末保留, 其余折叠);
    - watchdog 静默沿(D9/R7): 流 live 且末样本 ts 落后墙钟超 3 x si -> 立即 GET 重拉一次
      (D6)+ silentPull 记账防同一段静默重复重拉(D6b)+ 新帧到复位(下一次静默重新判, D6c);
    - ES onerror 路径(评审 T4a-R3): live->retry 迁移全链(关连 st.es=null + 计失败轮 + 3s
      换票重开定时器, C6a)/ 空闪连计轮形态(握手成功不清计数 -> 可积累到上限, C6b/C6c)/
      正常瞬断形态(来帧清零不积累, C6d/C6e)/ 混合计轮(票据 1 + ES 2 交叉达 3 降级, C6f);
    - pullFail 生产分支(评审 T4a-R4): 流活时对账 GET 失败(feeding 门内)pullFail 记账 +
      显示列不清 + 错误态不亮(D7a)+ 静默叠加徽标升格「已断连」(D7b)+ 对账恢复复位(D7c);
    - 隐藏渲染节流(评审 T4a-R5): document.hidden 期帧照常合并但建图跳过、回场恢复(H1-H3);
    - 徽标(D3): 两文案两态(滞后 Ns = 末样本 ts vs 墙钟超 3 x si; 已断连 = retry/degraded/
      pullFail 叠加静默; connecting 不惊扰)+ 恢复自动消显 + 位置 = 判定线 x / 顶沿(变值才写);
    - 降级(E7): 票据 503 计失败轮, 连续 3 轮(3s/轮)失败 -> GET 轮询接管(qb:<scope> 骨架句柄)
      + 对账停摆 + 60s 保守重试; 恢复 = 流回来即撤销降级 + 轮询退役 + 立即对账;
    - 清理面: _qbStreamStop 收 ES/重试定时器/三张定时器/状态缓冲, 幂等; 在挂重试定时器真实
      清验(先票据失败一轮再关流, F0 —— 活流直关的空转断言不算数); 重开先停后起不泄漏;
      目标未就绪不开流; 落票后复查(await 期间已停流不建流, polling.js #7 同款 + 代际判据);
    - 会话代际(评审 T4a-R1): stop/restart 翻代 -> 在途换票 continuation 落票即弃(重开竞态
      G1 / 在途重试触发的 connect 被 stop 打断 G2 两形态, 恰一条新 ES = 双建泄漏即红)/
      旧连监听器三面核验(st.es === es: onerror 不误伤新会话 G3、旧帧不改写显示列 G3b、
      旧 onopen 不改写状态 G3c)。
    静态钉: E4 常量五件(对账 30s/静默 3 x si/重连 3s/失败上限 3/降级恢复 60s)+ _QB_SCOPES
    stream 构建器三形态 + 生命周期挂钩(打开 _qbStreamStart / 页签 _qbStreamStart("torrent") /
    _stopDrawerPoll 与 _qbTeardown 收流 / 进场 _qbStreamResume / 换窗不动流)+ 徽标接线
    (build ensure + _qbFxAnchorSync 顶部搭车 + destroy 清记录)+ CSS 单点(pointer-events:none /
    z-index 2 照 tooltip 惯例, --warn 断连色)+ 会话代际三件(stop 翻代 / connect 两处 await 后
    核验 / 四监听器来连核验)+ 失败计数单点(onopen 不清 / _qbStreamFrame 清)。无 node 静默跳过
    (同 _NODE_QB_TRAFFIC 口径)。
    """
    shared = os.path.join(STATIC_ROOT, "shared")
    poll_path = os.path.join(shared, "polling.js")
    js_path = os.path.join(shared, "qb_traffic_chart.js")
    poll_js = open(poll_path, encoding="utf-8").read()
    js = open(js_path, encoding="utf-8").read()
    store_js = open(os.path.join(shared, "drawer_store.js"), encoding="utf-8").read()
    drawer_js = read_shared("drawer.js")
    auth_js = open(os.path.join(shared, "auth.js"), encoding="utf-8").read()

    # —— E4 常量(模块常量不进配置, D5): 值漂移必须同步计划与本守阵 ——
    assert "const _QB_STREAM_RECONCILE_MS = 30000;" in js, \
        "缺对账周期常量 30s(E4: 流活着也低频 GET 全量校准, 缓冲归位组粒度)"
    assert "const _QB_STREAM_SILENCE_X = 3;" in js, \
        "缺静默阈值常量 3(E4: 静默 > 3 x si 起显「滞后 Ns」, R7 诚实等待)"
    assert "const _QB_STREAM_RETRY_MS = 3000;" in js, \
        "缺重连节奏常量 3s(照 polling.js 一次性票据换新票重开同拍)"
    assert "const _QB_STREAM_FAIL_MAX = 3;" in js, \
        "缺连续失败上限常量 3(达到即降级 GET 轮询, E7)"
    assert "const _QB_STREAM_RETRY_DEGRADE_MS = 60000;" in js, \
        "缺降级恢复重试周期常量 60s(保守侧: 降级期 GET 轮询在供数, 每分钟静默重试一次流)"
    assert "const _QB_RAW_POINTS_MAX = 500;" in js and "const _QB_STREAM_TAIL_HEADROOM = 64;" in js, \
        "缺事件尾点预算常量(MAX_RAW_POINTS 500 = §03 契约 + 64 余量; 超界从头截断防无界增长)"
    # —— _QB_SCOPES stream 构建器(与后端 _parse_scope 三形态同语法, 前端不自行编码) ——
    assert 'stream: () => "global",' in js \
        and 'stream: (t) => "torrent:" + (t.drawer.hash || ""),' in js \
        and 'stream: (t) => "group:" + (t.qbGroupKey || ""),' in js, \
        "_QB_SCOPES 缺 SSE 订阅 scope 构建器(global/torrent:<hash>/group:<key>)"
    # —— 生命周期挂钩(打开 / 页签 / 收口 / 进场 / 换窗 / 登出) ——
    od = re.search(r"async openDrawerTraffic\(scope, key\) \{\n(.*?)\n    \},", js, re.S)
    assert od and "this._qbLoad(scope);" in od.group(1) \
        and "this._qbStreamStart(scope);" in od.group(1) \
        and "this._qbPollStart(scope)" not in od.group(1), \
        "openDrawerTraffic 必须首拉 + 起 SSE 流(_qbStreamStart); GET 轮询骨架只在降级态拉起"
    assert 'this._qbLoad("torrent");' in store_js and 'this._qbStreamStart("torrent");' in store_js, \
        "drawer_store.js 流量页签分支缺首拉 + 起 SSE 流"
    assert 'this._qbPollStop("torrent");' in store_js and 'this._qbStreamStop("torrent");' in store_js, \
        "drawer_store.js _stopDrawerPoll 必须同收流量轮询与 SSE 流(页签切走/换目标/关面板即断流)"
    td = re.search(r"_qbTeardown\(\) \{\n(.*?)\n    \},", js, re.S)
    assert td and "this._qbPollStop(s);" in td.group(1) \
        and "this._qbStreamStop(s);" in td.group(1) \
        and "this._qbChartDestroy(s);" in td.group(1), \
        "_qbTeardown 必须单点收三挂点轮询 + SSE 流 + 图(closeDrawer/形态切换/登出全走这里)"
    assert "this._qbTeardown();" in drawer_js and "this._qbTeardown();" in auth_js, \
        "closeDrawer 与 _logout 必须走 _qbTeardown 单点(流随收 —— 登出不留后台流)"
    re_b = re.search(r"_qbReloadOnEnter\(scope\) \{\n(.*?)\n    \},", js, re.S)
    assert re_b and "this._qbStreamResume(scope);" in re_b.group(1) \
        and "this._qbLoad(scope);" in re_b.group(1), \
        "_qbReloadOnEnter 必须进场核对流在场(_qbStreamResume; 流活着零操作不重连)"
    sw = re.search(r"async _qbSetWindow\(scope, w\) \{\n(.*?)\n    \},", js, re.S)
    assert sw and "_qbStreamStart" not in sw.group(1) and "_qbStreamStop" not in sw.group(1), \
        "换窗不得动流(窗口是 GET 参数, 流 scope 不变 —— 换窗只首拉 + 流续)"
    # —— 徽标接线(建面/同步搭车/销毁清记录)——
    assert "this._qbStallBadgeEnsure(u);" in js and "u._qbScope = scope;" in js, \
        "建图缺徽标幂等建面(_qbStallBadgeEnsure)或图记录缺 scope 反查标记(_qbSync 点无 scope 参数)"
    fx_sync = re.search(r"_qbFxAnchorSync\(u\) \{\n(.*?)\n      const anc = u && u\._qbFxAnchors;", js, re.S)
    assert fx_sync and "this._qbStallBadgeSync(u);" in fx_sync.group(1), \
        "徽标同步必须搭车 _qbFxAnchorSync 顶部(四处几何同步点覆盖面一致; 不受 FX 门控 —— anc 早退之前)"
    assert "u._qbStallBadge = null;" in js, "_qbChartDestroy 必须清徽标图记录引用(换肤/重建零残留)"
    # —— CSS 单点(_qbChartInjectCss: pointer-events/z-index 照 tooltip 惯例 views.css .hist-tip) ——
    assert ".qb-stall-badge { position: absolute; transform: translateX(-100%); padding-right: 6px;" \
        " pointer-events: none;" in js, \
        "徽标 CSS 缺 transform 右收/pointer-events:none(悬停/FX 不受干扰)"
    assert ".qb-stall-badge.qb-stall-down { color: var(--warn); }" in js, \
        "徽标断连态缺 --warn 色分义(两文案两态的视觉面)"
    # —— 会话代际与来连核验(评审 T4a-R1)/ 失败计数单点(评审 T4a-R2)——
    assert "st.gen = (st.gen || 0) + 1;" in js, \
        "_qbStreamStop 必须翻会话代际(在途换票 continuation 落票即弃 —— 重开竞态双建即订阅泄漏)"
    assert "const myGen = st.gen || 0;" in js and js.count("if (st.gen !== myGen) return;") == 2, \
        "_qbStreamConnect 必须在换票前捕获代际且两处 await 后核验(catch 分支 + 落票后), 旧 continuation 不得建流"
    assert "es.onopen = () => { if (st.es === es)" in js \
        and 'es.addEventListener("hello", () => { if (st.es === es)' in js \
        and js.count("if (st.es !== es) return;") >= 2, \
        "onopen/hello/帧/onerror 四监听器必须核验来连 === st.es(旧连不误伤新会话也不自救)"
    fb = re.search(r"_qbStreamOnOpen\(scope\) \{\n(.*?)\n    \},", js, re.S)
    assert fb and "st.failRun = 0" not in fb.group(1), \
        "失败计数不得在 onopen 清(握手成功 ≠ 可用 —— 空闪连 0/1 振荡使 E7 降级不可达, 评审 T4a-R2)"
    frm = re.search(r"_qbStreamFrame\(scope, fr\) \{\n(.*?)\n      if \(st\.seq == null\) \{", js, re.S)
    assert frm and "st.failRun = 0;" in frm.group(1), \
        "失败计数清零单点必须在 _qbStreamFrame(本连产出过数据帧)处 —— onopen 清即 R2 回归"

    node = shutil.which("node")
    if node:
        proc = subprocess.run(
            [node, "-e", _NODE_STDIN_WRAPPER, poll_path, js_path],
            input=_NODE_QB_STREAM_PROBE,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert proc.returncode == 0, f"SSE 主路径 node 电池跑挂: {proc.stderr.strip()}"
        report = json.loads(proc.stdout.strip().splitlines()[-1])
        assert report["failed"] == [], \
            f"SSE 主路径电池 {report['ok']}/{report['total']} 过, 失败: {report['failed']}"
