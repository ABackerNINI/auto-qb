"""test_webui_static_r4_poll_auth_lifecycle 测试计划: 存量评审 R4 static 主题清池 P08 —— 轮询/鉴权/生命周期/视图域 行为修复回归 + 纯逻辑 node 电池

## 测试计划(每个测试函数一条)
- test_r4_sse_edge_reconnect_state_machine: R5#14(major) + R5#15 —— SSE 断线沿判定与换票重连状态机 node 电池真跑(兑现 polling.js 文件头「探针真跑」注释契约, 兑现前 tests/ 零命中): _esDisconnectEdge 纯函数三分型(undefined 首断/true->false 跳变/重试期 false 非沿) + startEvents 换票接线(POST /api/events/ticket + ?ticket= 连流) + onopen 回置 + 首断沿恰一条 toast + 重试期重复 onerror 只发一条 toast 不叠重试定时器 + 重连必关旧连接换新票 + ver 驱动 60ms 去抖合并(R5#4 修复回归: 落拍 document.hidden 短路, 后台标签不吃 ver 驱动, 恢复可见照常拉) + stopEvents 归置 _esConnected/_esRetry/_verTimer
- test_r4_poll_backoff_and_stop_onend: R5#17 + R5#5 —— 轮询失败退避曲线真跑分型(骨架探针把 currentPollMs 桩成常量的绕过面在此补上): pollFails=0..4 序列(1.5s 档 3000/6000/12000/15000 封顶)、大库 3s 档与总量未知 2s 档、refresh 成功清零/失败递增封顶 4/401 分支停轮询+拆推送不续排(R5#2 第二半); stopPoll 对 awaitPoll 收摊走 onEnd 且兑现 null(文件头契约「收敛/耗尽/到点都走」含外部叫停), startPoll 顶掉同 key 有界等待 onEnd 不双调, 收敛路径(finish)与叫停路径互斥不双调
- test_r4_errlog_reseed_probe: R5#16 —— lifecycle.js _errlogReseed node 电池真跑(兑现「探针真跑」注释契约, 兑现前 tests/ 零命中): cursor 0(尚无游标)不判重启 / last<cursor 判重启(seq 进程内只增, 倒退唯一路径是重启归零) / last>=cursor 正常
- test_r4_logout_settles_modal_and_stops_events: R5#1 + R5#2 —— auth.js _logout 登出收口: 悬空模态先 resolve(false) 再复位(直接丢弃 _modalResolve 会让 confirmDialog/promptDialog 永久 pending, 删除流程在 await 处挂死)、await 侧恢复看到已复位框状态走取消分支、SSE 通道与轮询同口径一并拆(stopEvents 与 _qbTeardown 同收)、无框登出 no-op 不炸
- test_r4_search_quiet_retry_backoff: R5#236 —— view.js 静默刷新失败重试退避真跑: searchBuilding 残留 true 时失败续查逐次翻倍夹 15s(2s/4s/8s/15s/15s, 与轮询失败退避 currentPollMs 同曲线口径), 服务端宕机不再形成固定 1 req/s 无限循环; 成功一轮计数清零且续查保持 1s 节拍、resetSearch 新会话从零起算
- test_r4_lifecycle_unmounted_listener_sweep: R5#3 —— lifecycle.js mounted/unmounted 监听对称 node 电池真跑: mounted 挂的五支监听(click 收层/Esc 退栈/防抖 resize/visibilitychange/contextmenu)提为实例字段后 unmounted 逐一撤除(热重载句柄不再堆叠), stopPolling 与 stopEvents 同收, 既有撤除面(键盘引擎/守卫/storage/时钟 interval)零回归

加载口径: 单文件域直接读盘 eval(顶层纯函数声明随非严格 eval 入作用域, 同 hrsCompareRows 电池范式);
定时器全部桩住(只记节拍/手动放拍), 时钟可手动放拍 —— 免得真睡 3s/15s。无 node 静默跳过(返回 None,
不引入 pytest skip; 有 node 时断言电池全绿)。
"""

import json
import shutil
import subprocess

import pytest

from webui_helpers import STATIC_ROOT


def _shared(name):
    import os
    return os.path.join(STATIC_ROOT, "shared", name)


def _run_probe(probe, path):
    """跑一个 node 电池: 无 node 返回 None(静默跳过); 输出末行必须是 {ok, total, failed} JSON"""
    node = shutil.which("node")
    if not node:
        return None
    proc = subprocess.run(
        [node, "-e", probe, path],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    assert proc.returncode == 0, f"node 电池跑挂: {proc.stderr.strip()}"
    return json.loads(proc.stdout.strip().splitlines()[-1])


def _assert_battery(report, what):
    if report is None:
        pytest.skip("无 node: 本电池静默跳过(与既有 node 电池同口径)")
    assert report["failed"] == [], f"{what} {report['ok']}/{report['total']} 过, 失败: {report['failed']}"


# R5#14 + R5#15: SSE 断线沿判定 + 换票重连状态机(含 R5#4 ver 落拍 hidden 短路) ----------------
_NODE_SSE_PROBE = r"""
const fs = require("fs");
global.window = {};
let hidden = false;
global.document = {
  get hidden() { return hidden; },
  addEventListener() {}, removeEventListener() {},
};
// 伪时钟: 只入队不真跑, 手动放拍(与 _NODE_POLL_SKELETON_PROBE 同口径, 免真睡 3s)
const timers = new Map(); let tid = 0;
global.setTimeout = (fn, ms) => { const id = ++tid; timers.set(id, { fn, ms: ms || 0 }); return id; };
global.clearTimeout = (id) => { timers.delete(id); };
const fireTimer = (id) => { const t = timers.get(id); if (!t) return false; timers.delete(id); t.fn(); return true; };
const drain = async () => { for (let i = 0; i < 10; i++) await null; };
// EventSource 替身: 记录实例/URL/close, 事件手动派发
const instances = [];
class FakeES {
  constructor(url) { this.url = url; this.handlers = {}; this.onopen = null; this.onerror = null; this.closed = false; instances.push(this); }
  addEventListener(type, fn) { (this.handlers[type] = this.handlers[type] || []).push(fn); }
  close() { this.closed = true; }
  emit(type, ev) { for (const fn of this.handlers[type] || []) fn(ev || { data: "{}" }); }
}
global.EventSource = FakeES;
eval(fs.readFileSync(process.argv[1], "utf8"));   // polling.js(顶层函数 _esDisconnectEdge 随 eval 入作用域)
const P = window.AQB_POLL.methods;
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

(async () => {
  // ① 沿判定纯函数(R5#15 注释契约: 探针真跑)
  ok("沿判定: undefined(本会话尚未连上)是沿=发 toast", _esDisconnectEdge(undefined) === true);
  ok("沿判定: true->false 跳变是沿", _esDisconnectEdge(true) === true);
  ok("沿判定: 重试期重复 onerror(prev=false)不是沿", _esDisconnectEdge(false) === false);

  // ② startEvents: 换票接线 + 连流
  const ticketCalls = [];
  const ctx = Object.assign({}, P, {
    authOk: true, _es: null, _esBusy: false, _esRetry: null, _verTimer: null, _esConnected: undefined,
    toasts: [],
    toast(msg, kind) { this.toasts.push([kind, msg]); },
    refreshes: 0,
    refresh() { this.refreshes += 1; },
    async api(path) { ticketCalls.push(path); return { ticket: "TK" + ticketCalls.length }; },
  });
  await P.startEvents.call(ctx);
  await drain();
  ok("换票: POST /api/events/ticket", ticketCalls.length === 1 && ticketCalls[0] === "/api/events/ticket");
  ok("?ticket= 连流(长期密钥不进查询串)", instances.length === 1 && instances[0].url.indexOf("?ticket=TK1") >= 0);
  ok("_es 持当前连接", ctx._es === instances[0]);
  ok("连接期零 toast(断线提示只在断线沿)", ctx.toasts.length === 0);

  // ③ onopen 恢复回置; onerror 首断(沿): 恰一条 toast + 关旧连接 + 排 3s 重试
  const es1 = instances[0];
  es1.onopen();
  ok("onopen 回置 _esConnected(不发恢复噪音)", ctx._esConnected === true && ctx.toasts.length === 0);
  es1.onerror();
  ok("首次断线(沿): 恰一条 error toast 且沿位落 false", ctx.toasts.length === 1 && ctx._esConnected === false);
  ok("旧连接必关(一次性票据重连必失效)", es1.closed === true && ctx._es === null);
  ok("重试定时器已排(3s, 与 EventSource 默认重连同拍)", timers.has(ctx._esRetry) && timers.get(ctx._esRetry).ms === 3000);

  // ④ 重试期重复 onerror: 不重复 toast、不叠重试定时器(R5#14 钉的行为)
  es1.onerror();
  es1.onerror();
  ok("重试期重复 onerror 只发一条 toast", ctx.toasts.length === 1);
  ok("重复 onerror 不叠重试定时器", [...timers.values()].filter((t) => t.ms === 3000).length === 1);

  // ⑤ 重连: 必关旧连接换新票(R5#14 钉的行为)
  fireTimer(ctx._esRetry);
  await drain();
  ok("重连第二次换票", ticketCalls.length === 2);
  ok("重连开新连接且 _es 换新", instances.length === 2 && ctx._es === instances[1]);
  ok("重连仍走 ?ticket= 换票通道", instances[1].url.indexOf("?ticket=TK2") >= 0);
  ok("重试定时器归置", ctx._esRetry === null);

  // ⑥ ver 驱动: 60ms 去抖合并; 落拍 document.hidden 短路(R5#4)
  const es2 = instances[1];
  es2.emit("ver");
  ok("ver 排 60ms 去抖", timers.has(ctx._verTimer) && timers.get(ctx._verTimer).ms === 60);
  es2.emit("ver");
  es2.emit("ver");
  fireTimer(ctx._verTimer);
  await drain();
  ok("密集 ver 去抖合并: 只拉一次 /api/state", ctx.refreshes === 1);
  hidden = true;
  es2.emit("ver");
  fireTimer(ctx._verTimer);
  await drain();
  ok("后台标签 ver 不拉数(document.hidden 短路, R5#4)", ctx.refreshes === 1);
  hidden = false;
  es2.emit("ver");
  fireTimer(ctx._verTimer);
  await drain();
  ok("恢复可见 ver 照常拉(补拉由 visibilitychange 负责, 电池只钉 ver 路径)", ctx.refreshes === 2);

  // ⑦ stopEvents 归置(R5#14: 断线沿状态位随连接会话归置)
  ctx.stopEvents();
  ok("stopEvents 关连接清句柄", ctx._es === null && ctx._esRetry === null && ctx._verTimer === null);
  ok("stopEvents 归置 _esConnected(重登后首断仍算首次断线)", ctx._esConnected === undefined);
  ok("归置后连接实例已 close", instances[1].closed === true);

  console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
    failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
})().catch((e) => { console.error(e && e.stack || e); process.exit(1); });
"""

# R5#17 + R5#5: 失败退避曲线真跑 + stopPoll 收摊 onEnd ----------------------------------------
_NODE_POLLCURVE_PROBE = r"""
const fs = require("fs");
global.window = {};
global.document = { hidden: false, addEventListener() {}, removeEventListener() {} };
const timers = new Map(); let tid = 0;
global.setTimeout = (fn, ms) => { const id = ++tid; timers.set(id, { fn, ms: ms || 0 }); return id; };
global.clearTimeout = (id) => { timers.delete(id); };
const drain = async () => { for (let i = 0; i < 10; i++) await null; };
eval(fs.readFileSync(process.argv[1], "utf8"));   // polling.js
const P = window.AQB_POLL.methods;
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

(async () => {
  // ① currentPollMs 真跑分型(R5#17: 骨架探针把 currentPollMs 桩成常量的绕过面, 这里真跑)
  const mk = (torrents, fails) => Object.assign({}, P, {
    status: typeof torrents === "number" ? { torrents } : {},
    pollFails: fails,
  });
  ok("pollFails=0: 恒定档 1.5s(500 种子, 与服务端 sync_interval 对齐)", P.currentPollMs.call(mk(500, 0)) === 1500);
  ok("退避 1: 1500*2=3000", P.currentPollMs.call(mk(500, 1)) === 3000);
  ok("退避 2: 6000", P.currentPollMs.call(mk(500, 2)) === 6000);
  ok("退避 3: 12000", P.currentPollMs.call(mk(500, 3)) === 12000);
  ok("退避 4: 封顶 15000", P.currentPollMs.call(mk(500, 4)) === 15000);
  ok("大库 base 3000: 退避 2 = 12000", P.currentPollMs.call(mk(4000, 2)) === 12000);
  ok("大库 base 3000: 退避 3 已封顶 15000", P.currentPollMs.call(mk(4000, 3)) === 15000);
  ok("总量未知 base 2000(不冒进): 退避 1 = 4000", P.currentPollMs.call(mk(undefined, 1)) === 4000);

  // ② refresh 真跑: 成功清零 / 失败递增封顶(曲线的进位端)
  const okCtx = Object.assign({}, P, {
    status: {}, serviceDown: true, pollFails: 3,
    api: async () => ({ updated: false, status: { torrents: 100 } }),
    _expirePending() {}, reapplyPending() {}, _maybeSearchRefresh() {},
    scheduleNext() { this.scheduleNextN = (this.scheduleNextN || 0) + 1; },
  });
  await P.refresh.call(okCtx);
  ok("成功轮 pollFails 清零 + serviceDown 复位", okCtx.pollFails === 0 && okCtx.serviceDown === false);
  ok("成功后排下一拍", okCtx.scheduleNextN === 1);

  const failCtx = Object.assign({}, P, {
    status: {}, serviceDown: false, pollFails: 4,
    api: async () => { throw new Error("boom"); },
    _expirePending() {}, reapplyPending() {}, _maybeSearchRefresh() {},
    scheduleNext() { this.scheduleNextN = (this.scheduleNextN || 0) + 1; },
  });
  await P.refresh.call(failCtx);
  ok("失败轮 pollFails 递增且封顶 4", failCtx.pollFails === 4 && failCtx.serviceDown === true);
  ok("失败后仍续排(错误风暴由轮询退避吸收)", failCtx.scheduleNextN === 1);

  // ③ 401 分支(R5#2 修法第二半): stopPolling + stopEvents, 不再续排
  const err = new Error("unauthorized"); err.auth = true;
  const authCtx = Object.assign({}, P, {
    status: {}, serviceDown: false, pollFails: 0,
    api: async () => { throw err; },
    _expirePending() {}, reapplyPending() {}, _maybeSearchRefresh() {},
    calls: [],
    stopPolling() { this.calls.push("stopPolling"); },
    stopEvents() { this.calls.push("stopEvents"); },
    scheduleNext() { this.calls.push("scheduleNext"); },
  });
  await P.refresh.call(authCtx);
  ok("401: 停轮询 + 拆推送(与 _logout 同口径)", authCtx.calls.join(",") === "stopPolling,stopEvents");
  ok("401: 不再续排下一拍且不置 serviceDown", !authCtx.calls.includes("scheduleNext") && authCtx.serviceDown === false);

  // ④ stopPoll 对 awaitPoll 收摊(R5#5): 兑现 null + onEnd 恰一次
  let ended = 0;
  const st1 = Object.assign({}, P, { _polls: null });
  const p1 = P.awaitPoll.call(st1, "k", { ms: () => 5, fn: () => null, until: () => false,
    onEnd: () => { ended += 1; } });
  await drain();
  P.stopPoll.call(st1, "k");
  ok("stopPoll 收摊兑现 null", (await p1) === null);
  ok("stopPoll 收摊走 onEnd(契约: 收敛/耗尽/到点/叫停都走)", ended === 1);
  ok("句柄表归置", st1._polls.k === null);
  P.stopPoll.call(st1, "k");
  ok("重复 stopPoll 不双调 onEnd", ended === 1);

  // ⑤ startPoll 顶掉同 key 有界等待: onEnd 也走(loading 复位不再被跳过), 不双调
  let ended2 = 0;
  const st2 = Object.assign({}, P, { _polls: null });
  const p2 = P.awaitPoll.call(st2, "m", { ms: () => 5, fn: () => null, until: () => false,
    onEnd: () => { ended2 += 1; } });
  await drain();
  P.startPoll.call(st2, "m", { ms: () => 50, fn: () => {} });  // 内部先 stopPoll("m")
  ok("被顶掉的有界等待兑现 null 且走 onEnd", (await p2) === null && ended2 === 1);
  P.stopPoll.call(st2, "m");  // 收掉顶上来的长驻心跳
  P.stopPoll.call(st2, "m");
  ok("顶掉场景 onEnd 不双调", ended2 === 1);

  // ⑥ 正常收敛路径(finish)onEnd 恰一次, 与叫停路径互斥
  let ended3 = 0;
  const st3 = Object.assign({}, P, { _polls: null });
  const v3 = await P.awaitPoll.call(st3, "n", { ms: () => 0, max: 9, fn: async () => "ok",
    until: (v) => !!v, onEnd: () => { ended3 += 1; } });
  ok("收敛路径 onEnd 恰一次且兑现该拍值", v3 === "ok" && ended3 === 1);
  P.stopPoll.call(st3, "n");
  ok("收敛后 stopPoll 不再调 onEnd(alive 守卫)", ended3 === 1);

  console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
    failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
})().catch((e) => { console.error(e && e.stack || e); process.exit(1); });
"""

# R5#16: lifecycle _errlogReseed 注释契约兑现(探针真跑) ---------------------------------------
_NODE_RESEED_PROBE = r"""
const fs = require("fs");
global.window = {};
eval(fs.readFileSync(process.argv[1], "utf8"));   // lifecycle.js(顶层纯函数 _errlogReseed 入作用域)
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);
// cursor 0 = 尚无游标(boot 全量/首轮), 不判重启 —— 否则开页即误清旧条目重拉
ok("cursor 0 且 last 0: 不判重启", _errlogReseed(0, 0) === false);
ok("cursor 0 且 last>0: 不判重启", _errlogReseed(5, 0) === false);
// seq 进程内只增, 回包 last 低于已持游标 = 后端重启归零(唯一可能倒退的路径)
ok("last<cursor: 判重启", _errlogReseed(0, 3) === true);
ok("last<cursor(非零): 判重启", _errlogReseed(2, 5) === true);
ok("last>=cursor: 正常增量", _errlogReseed(5, 3) === false);
ok("last==cursor: 正常(无新条目)", _errlogReseed(3, 3) === false);
console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
  failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
"""

# R5#1 + R5#2: _logout 登出收口(悬空模态结算 + SSE 通道同拆) ----------------------------------
_NODE_LOGOUT_PROBE = r"""
const fs = require("fs");
global.window = {};
global.localStorage = { getItem: () => null, setItem() {}, removeItem() {} };
eval(fs.readFileSync(process.argv[1], "utf8"));   // auth.js
const A = window.AQB_AUTH.methods;
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);
const drain = async () => { for (let i = 0; i < 10; i++) await null; };

const mk = () => Object.assign({}, A, {
  ui: "atlas", token: "t0", pendingToken: "t0", authPending: true, bootstrapping: true,
  authRequired: false, authError: "", authErrorKind: "",
  searchTimer: 0, pollFails: 3, serviceDown: true,
  modal: { visible: true, mid: 1 }, _modalResolve: null,
  expandMemo: { groups: "g1", shows: null },
  drawer: { open: true },
  calls: [],
  stopPolling() { this.calls.push("stopPolling"); },
  stopEvents() { this.calls.push("stopEvents"); },
  _qbTeardown() { this.calls.push("_qbTeardown"); },
  clearSelection() {}, cfgReset() {}, resetSearch() {},
  _modalInit() { return { visible: false }; },
});

(async () => {
  // ① 悬空模态结算(R5#1): 先 resolve(false) 再复位框
  let resolved = 0, resolvedWith;
  const c1 = mk();
  c1._modalResolve = (v) => { resolved += 1; resolvedWith = v; };
  A._logout.call(c1, "密钥无效或已更换");
  ok("登出结算悬空模态: resolve(false)(取消语义)", resolved === 1 && resolvedWith === false);
  ok("登出复位框状态(不留 visible 残框)", c1.modal.visible === false);
  ok("_modalResolve 归置", c1._modalResolve === null);
  ok("登出收口: 遮罩+凭证+受保护数据清空", c1.authRequired === true && c1.token === ""
    && c1.groups.length === 0 && c1.toasts.length === 0);

  // ② SSE 通道一并拆(R5#2): 与 stopPolling/_qbTeardown 同口径
  ok("_logout 调 stopEvents(与 stopPolling/_qbTeardown 同收)",
    c1.calls.includes("stopEvents") && c1.calls.includes("stopPolling") && c1.calls.includes("_qbTeardown"));

  // ③ 无悬空模态: no-op 不炸
  const c2 = mk();
  A._logout.call(c2);
  ok("无框登出 no-op 不炸", c2.modal.visible === false && c2.calls.includes("stopEvents"));

  // ④ await 侧恢复(microtask): 看到的是已复位框状态, 删除流程走取消分支不再挂死
  let saw = null;
  const c3 = mk();
  c3._modalResolve = (v) => { Promise.resolve().then(() => { saw = [v, c3.modal.visible]; }); };
  A._logout.call(c3, "");
  await drain();
  ok("await 侧恢复: 取消(false)且框已复位", !!saw && saw[0] === false && saw[1] === false);

  console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
    failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
})().catch((e) => { console.error(e && e.stack || e); process.exit(1); });
"""

# R5#236: 静默刷新失败重试退避 ----------------------------------------------------------------
_NODE_SEARCHBACKOFF_PROBE = r"""
const fs = require("fs");
global.window = {};
const timers = new Map(); let tid = 0; const armed = [];
global.setTimeout = (fn, ms) => { const id = ++tid; timers.set(id, { fn, ms: ms || 0 }); armed.push(ms || 0); return id; };
global.clearTimeout = (id) => { timers.delete(id); };
const lastArmed = () => armed[armed.length - 1];
eval(fs.readFileSync(process.argv[1], "utf8"));   // view.js
const V = window.AQB_VIEW.methods;
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

(async () => {
  const mk = () => Object.assign({}, V, {
    searchQuery: "abc", searchPending: false, searchHits: new Set(), searchUncovered: [],
    searchBuilding: true, searchNegativeOnly: false, searchError: "", searchRevApplied: -1,
    _searchRefreshBusy: false, _searchRefreshTimer: null, _searchRetryFails: 0,
    groups: [], searchTimer: null,
  });
  const failApi = () => Promise.reject(new Error("boom"));
  const c = mk();
  c.api = failApi;
  // 失败重试退避曲线: 1s 基准逐次翻倍夹 15s(R5#236; 与轮询失败退避 currentPollMs 同曲线口径)
  await V.doSearch.call(c, true);
  ok("失败 1 次续查 2s(不再固定 1 req/s)", lastArmed() === 2000);
  await V.doSearch.call(c, true);
  ok("失败 2 次 4s", lastArmed() === 4000);
  await V.doSearch.call(c, true);
  ok("失败 3 次 8s", lastArmed() === 8000);
  await V.doSearch.call(c, true);
  ok("失败 4 次 15s(封顶)", lastArmed() === 15000);
  await V.doSearch.call(c, true);
  ok("失败 5 次 15s(不再增长)", lastArmed() === 15000);
  ok("失败路径保留旧结果不塌列表且不弹错误", c.searchError === "" && c.searchHits.size === 0
    && c.searchPending === false && c.searchBuilding === true);

  // 成功一轮: 计数清零 + 续查回 1s 正常节拍(既有契约: 续查用独立定时器)
  c.api = async () => ({ results: [], building: true, rev: 9, negative_only: false });
  await V.doSearch.call(c, true);
  ok("成功轮退避计数清零", c._searchRetryFails === 0);
  ok("成功续查保持 1s 节拍", lastArmed() === 1000);
  c.api = failApi;
  await V.doSearch.call(c, true);
  ok("清零后失败重新从 2s 起翻倍", lastArmed() === 2000);

  // resetSearch: 新搜索会话退避从零起算(不带上一轮残值)
  c._searchRetryFails = 4;
  V.resetSearch.call(c);
  ok("resetSearch 清退避计数与续查定时器", c._searchRetryFails === 0 && c._searchRefreshTimer === null
    && c.searchBuilding === false);

  console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
    failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
})().catch((e) => { console.error(e && e.stack || e); process.exit(1); });
"""

# R5#3: lifecycle mounted/unmounted 监听对称(五支匿名监听提为实例字段后撤净) ------------------
_NODE_LIFECYCLE_PROBE = r"""
const fs = require("fs");
// 监听登记处: add/remove 全记 [scope, type, fn]
const reg = [];
const mkTarget = (scope) => ({
  addEventListener(type, fn) { reg.push([scope, type, fn]); },
  removeEventListener(type, fn) {
    const i = reg.findIndex((l) => l[0] === scope && l[1] === type && l[2] === fn);
    if (i >= 0) reg.splice(i, 1);
  },
});
global.window = Object.assign(mkTarget("window"), { innerHeight: 800 });
global.document = Object.assign(mkTarget("document"), { hidden: false });
global.localStorage = { getItem: () => null, setItem() {}, removeItem() {} };
global.aqbFetch = () => new Promise(() => {});   // 永悬挂: 本电池只验注册/撤除面, 不走启动链
global.readColStateRaw = () => "has-prefs";      // 非空 -> 跳过 origin 提示分支
const timers = new Map(); let tid = 0;
global.setTimeout = (fn, ms) => { const id = ++tid; timers.set(id, { fn, ms: ms || 0 }); return id; };
global.clearTimeout = (id) => { timers.delete(id); };
global.setInterval = (fn, ms) => { const id = ++tid; timers.set(id, { fn, ms, iv: true }); return id; };
global.clearInterval = (id) => { timers.delete(id); };
eval(fs.readFileSync(process.argv[1], "utf8"));   // lifecycle.js
const LC = window.AQB_LIFECYCLE;
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

(async () => {
  const calls = [];
  const ctx = Object.assign({}, LC.methods, {
    // 跨域方法以记录器替身: 本电池只验注册/撤除的对称面(R5#3)
    stopPolling() { calls.push("stopPolling"); },
    stopEvents() { calls.push("stopEvents"); },
    cfgGuardRelease() { calls.push("cfgGuardRelease"); },
    $nextTick() {},          // 首帧量高不在本电池面
    _showColsOriginHint() {},
  });
  LC.created.call(ctx);
  await LC.mounted.call(ctx);

  // mounted: 全部监听在册(scroll/resize 具名 + click/Esc/防抖 resize/可见性/右键/storage x2/keydown x3)
  const cnt = (scope, type) => reg.filter((l) => l[0] === scope && l[1] === type).length;
  ok("mounted: click 收层监听在册", cnt("window", "click") === 1);
  ok("mounted: keydown 恰三条(Esc 退栈 + 快捷键引擎 + 刷新守卫)", cnt("document", "keydown") === 3);
  ok("mounted: resize 恰两条(具名 + 防抖)", cnt("window", "resize") === 2);
  ok("mounted: visibilitychange 在册", cnt("document", "visibilitychange") === 1);
  ok("mounted: contextmenu 在册", cnt("document", "contextmenu") === 1);
  ok("mounted: storage 恰两条(列偏好 + 时间口径)", cnt("window", "storage") === 2);

  LC.unmounted.call(ctx);

  // unmounted: 五支监听撤净(R5#3 修复面) + 既有撤除面零回归
  ok("unmounted: click 撤除", cnt("window", "click") === 0);
  ok("unmounted: keydown 撤净(Esc 退栈 + 引擎 + 守卫)", cnt("document", "keydown") === 0);
  ok("unmounted: resize 撤净(具名 + 防抖)", cnt("window", "resize") === 0);
  ok("unmounted: visibilitychange 撤除", cnt("document", "visibilitychange") === 0);
  ok("unmounted: contextmenu 撤除", cnt("document", "contextmenu") === 0);
  ok("unmounted: storage 撤净", cnt("window", "storage") === 0);
  ok("unmounted: window 监听全撤净", reg.filter((l) => l[0] === "window").length === 0);
  ok("unmounted: document 监听全撤净", reg.filter((l) => l[0] === "document").length === 0);
  ok("unmounted: 时钟 interval 撤净", timers.size === 0);
  ok("unmounted: stopPolling 调用(主轮骨架一并收)", calls.includes("stopPolling"));
  ok("unmounted: stopEvents 调用(SSE 同收, 既有口径)", calls.includes("stopEvents"));
  ok("unmounted: cfgGuardRelease 调用(既有口径)", calls.includes("cfgGuardRelease"));

  console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
    failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
})().catch((e) => { console.error(e && e.stack || e); process.exit(1); });
"""


def test_r4_sse_edge_reconnect_state_machine():
    """R5#14(major)+R5#15: SSE 断线沿判定/换票重连状态机 node 电池真跑(含 R5#4 ver 落拍 hidden 短路)。"""
    _assert_battery(_run_probe(_NODE_SSE_PROBE, _shared("polling.js")), "SSE 状态机电池")


def test_r4_poll_backoff_and_stop_onend():
    """R5#17+R5#5: 失败退避曲线真跑分型 + stopPoll 收摊走 onEnd(顶掉/叫停/收敛三路不双调)。"""
    _assert_battery(_run_probe(_NODE_POLLCURVE_PROBE, _shared("polling.js")), "退避曲线与收摊电池")


def test_r4_errlog_reseed_probe():
    """R5#16: lifecycle.js _errlogReseed 探针真跑(兑现「探针真跑」注释契约)。"""
    _assert_battery(_run_probe(_NODE_RESEED_PROBE, _shared("lifecycle.js")), "_errlogReseed 电池")


def test_r4_logout_settles_modal_and_stops_events():
    """R5#1+R5#2: _logout 悬空模态 resolve(false) + stopEvents 与轮询同口径收口。"""
    _assert_battery(_run_probe(_NODE_LOGOUT_PROBE, _shared("auth.js")), "_logout 收口电池")


def test_r4_search_quiet_retry_backoff():
    """R5#236: 静默刷新失败续查退避(翻倍夹 15s/成功清零/resetSearch 从零起算)。"""
    _assert_battery(_run_probe(_NODE_SEARCHBACKOFF_PROBE, _shared("view.js")), "搜索续查退避电池")


def test_r4_lifecycle_unmounted_listener_sweep():
    """R5#3: lifecycle 五支匿名监听提为实例字段后 unmounted 撤净 + stopPolling 同收。"""
    _assert_battery(_run_probe(_NODE_LIFECYCLE_PROBE, _shared("lifecycle.js")), "监听对称电池")
