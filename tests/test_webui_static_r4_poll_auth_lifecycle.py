"""test_webui_static_r4_poll_auth_lifecycle 测试计划: 存量评审 R4 static 主题清池 P08 —— 轮询/鉴权/生命周期/视图域 行为修复回归 + 纯逻辑 node 电池

## 测试计划(每个测试函数一条)
- test_r4_sse_edge_reconnect_state_machine: R5#14(major) + R5#15 —— SSE 断线沿判定与换票重连状态机 node 电池真跑(兑现 polling.js 文件头「探针真跑」注释契约, 兑现前 tests/ 零命中): _esDisconnectEdge 纯函数三分型(undefined 首断/true->false 跳变/重试期 false 非沿) + startEvents 换票接线(POST /api/events/ticket + ?ticket= 连流) + onopen 回置 + 首断沿恰一条 toast + 重试期重复 onerror 只发一条 toast 不叠重试定时器 + 重连必关旧连接换新票 + ver 驱动 60ms 去抖合并(R5#4 修复回归: 落拍 document.hidden 短路, 后台标签不吃 ver 驱动, 恢复可见照常拉) + stopEvents 归置 _esConnected/_esRetry/_verTimer + 换票 await 期间登出落票后不开流(issue 26-11-08-0229 #7: authOk 复查拦在 EventSource 之前, _esBusy 不残留)
- test_r4_poll_backoff_and_stop_onend: R5#17 + R5#5 —— 轮询失败退避曲线真跑分型(骨架探针把 currentPollMs 桩成常量的绕过面在此补上): pollFails=0..4 序列(1.5s 档 3000/6000/12000/15000 封顶)、大库 3s 档与总量未知 2s 档、refresh 成功清零/失败递增封顶 4/401 分支停轮询+拆推送不续排(R5#2 第二半); stopPoll 对 awaitPoll 收摊走 onEnd 且兑现 null(文件头契约「收敛/耗尽/到点都走」含外部叫停), startPoll 顶掉同 key 有界等待 onEnd 不双调, 收敛路径(finish)与叫停路径互斥不双调; onEnd 抛异常不吞 settle(issue 26-11-08-0229 #8: stopPoll 与 finish 两路同式 try/finally, settle 必达、异常照常上抛不吞不藏); fail 路(fn 抛异常 reject)不走 onEnd、句柄表归置(issue 26-11-08-1621 契约定案: 清理归调用方, 文件头注释已写明)
- test_r4_errlog_reseed_probe: R5#16 —— lifecycle.js _errlogReseed node 电池真跑(兑现「探针真跑」注释契约, 兑现前 tests/ 零命中): cursor 0(尚无游标)不判重启 / last<cursor 判重启(seq 进程内只增, 倒退唯一路径是重启归零) / last>=cursor 正常
- test_r4_logout_settles_modal_and_stops_events: R5#1 + R5#2 —— auth.js _logout 登出收口: 悬空模态先 resolve(false) 再复位(直接丢弃 _modalResolve 会让 confirmDialog/promptDialog 永久 pending, 删除流程在 await 处挂死)、await 侧恢复看到已复位框状态走取消分支、SSE 通道与轮询同口径一并拆(stopEvents 与 _qbTeardown 同收)、无框登出 no-op 不炸
- test_r4_search_quiet_retry_backoff: R5#236 —— view.js 静默刷新失败重试退避真跑: searchBuilding 残留 true 时失败续查逐次翻倍夹 15s(2s/4s/8s/15s/15s, 与轮询失败退避 currentPollMs 同曲线口径), 服务端宕机不再形成固定 1 req/s 无限循环; 成功一轮计数清零且续查保持 1s 节拍、resetSearch 新会话从零起算
- test_r4_lifecycle_unmounted_listener_sweep: R5#3 —— lifecycle.js mounted/unmounted 监听对称 node 电池真跑: mounted 挂的五支监听(click 收层/Esc 退栈/防抖 resize/visibilitychange/contextmenu)提为实例字段后 unmounted 逐一撤除(热重载句柄不再堆叠), stopPolling 与 stopEvents 同收, 既有撤除面(键盘引擎/守卫/storage/时钟 interval)零回归
- test_r4_webflags_boot_retry_and_ensure: issue 26-11-11-0633 —— loadWebFlags boot 韧性 node 电池真跑: boot 期(loadWebFlagsBoot)失败 1s/3s 退避各补一发共三发(穷尽止/中间态保持 fail-closed)、登出态(e.auth)不重试不排定时器、flagsLoaded 态(成功收口/"未取到"可分)、惰性补拉 ensureWebFlags(已取到返回 null 零副作用/未取到补一发)、并发单飞(同档同帧与退避窗口期并入复用同一 promise 不叠发)、档位分槽(boot 链在途时惰性补拉异档另起单发不骑退避链、惰性结算不挤占 boot 槽, 请求计数钉 3 发)
- test_r4_truth_snapshot_materialized_members: S2a ingestion 物化缝(计划 26-11-11-0630 §03)× 乐观真值快照 node 电池真跑 —— S2a 后 _snapshotTruth 的组员源从服务端成员字典换成客户端物化拷贝, 此前该缝 tests/ 零命中。前置两断言钉 spike 裁决不变式(组员 = **独立浅拷贝**非平铺行引用, 同 hash 多命中各为独立对象; applyOptimisticPatch 经 _forEachRow 平铺行与组员拷贝同拍命中); 三个绿色向: 全量轮(命令在途)物化源 = 载荷平铺行 = 服务端真值 → 快照逐键比对不误判收敛(hold 保留)且 op.prev 保鲜为真值(兜底回滚不打到补丁值) / 全量轮真值落地 kind 对齐 → 正常收敛(撤 hold 出口) / 增量轮组未脏 → 组不进 d.groups → 快照无该 hash → 宁可慢收不误判(3s 兜底)。*已知边界(电池内注释, 不落断言)*: 误判窗口 = 组脏(**他员变化**使组进 d.groups)+ 该组另有成员 pending —— 物化源落到本地已打补丁行, 快照可能读到补丁值提前撤 hold(op.prev 同窗被污染); 影响如实两分支: 成功路径真值落地即收敛, 失败/停滞路径补丁值停留至该成员下次变化或下一次全量轮(回滚与 3s 兜底同被跳过, 长期滞留而非一轮弹回, 已确认接受该残留) —— S2a 报告「混合组未脏」表述以此修正: **组完全未脏是安全向**(即第三个绿色断言); 三入口接线(delta 桶序/先物化后赋值/auth.js 同缝)留给 S4 e2e 覆盖
- test_r4_version_reload_self_heal: S3 version-reload 自愈(计划 26-11-11-0630 §03 version-reload 行 / §04 S3 行)node 电池真跑 —— 轮询数据处理入口(refresh, 定时轮询与 SSE ver 驱动同汇)每轮比对 status payload 既有 version 字段(_status_payload 恒回传): (1)一致轮零成本直通不 reload 不碰存储 (2)变更沿发起 location.reload(), 本轮载荷不应用但照常续排下一拍(跨版本载荷不喂旧 JS; 防抖封顶续排无循环, 导航取消时链保活)(3)sessionStorage 30s 防抖窗口内第二次变更不重复 reload(窗口内照常处理+续排 = 有界节流非冻结, 基线不动; 窗口外放行一次 = 1 次/窗口有界节流)(4)version 缺失/非字符串轮保守默认不触发不动基线(黄金法则 2; 缺后再见 version 首见记基线不当变更沿)(5)配置编辑器脏态守卫(cfgGuardActive 替身置位)活跃轮跳过自愈(不 reload/不记防抖时间戳/基线不动, 轮询照常), 守卫释放后下一轮变更沿自然再触发 —— 后台轮询不替脏态用户弹原生框; 另钉循环破除主证据: reload 后新页 incarnation 重记新基线, 稳定版本下恰好一次 reload 零循环(防重签发循环第 1 层); 可控时钟替身 global.Date 免真睡 30s; 静态钉 _versionSelfHeal 函数体内含 cfgGuardActive 调用(照 test_webui_static_dom_page_layout.py 守阵先例 —— 电池守卫沿替身驱动只测「活跃时怎么走」, 真机问没问守卫由静态钉补位); 电池替身 mk() 自备 _versionSeen: null(真机初值来自 state.js data() —— Vue3 生产构建跳过 methods 非函数条目, 声明已挪出 polling.js, 搜索续查电池 _searchRetryFails 同款先例), 基线判据随之收紧单臂 === null(undefined 臂会吸收声明错位回归, 已删)
- test_r4_version_reload_no_storage_fallback: S3 同上存储不可用分支(私隐模式访问即抛, columns_persist.js 先例), 独立探针隔离内存层模块级状态(共进程与主探针串账; cfgGuardActive 以替身置不活跃, 只为过守卫沿): sessionStorage 缺席时变更沿仍放行 reload(fail-open, 自愈不让位) + 内存层 _versionReloadMemAt 同页限流仍拦重复触发(防抖不随存储缺席而全失) + 窗口外放行(内存层窗口同口径); 跨 reload 记忆丢失的残留(唯「存储被禁 + 每请求翻转版本」组合才可能循环)已在 polling.js 注释声明, 电池不钉不可达面; 替身 mk() 同款自备 _versionSeen: null(真机初值来自 state.js data())

加载口径: 单文件域直接读盘 eval(顶层纯函数声明随非严格 eval 入作用域, 同 hrsCompareRows 电池范式);
多域电池(真值快照 × S2a 物化)经 _run_probe 的 list 路径两路 argv 同进程 eval(polling.js + commands.js
域聚合 bundle_file, webui_helpers 先例)。定时器全部桩住(只记节拍/手动放拍), 时钟可手动放拍 —— 免得
真睡 3s/15s。无 node 时 _run_probe 返回 None、_assert_battery 即红(不引入 pytest skip; 有 node 时断言电池全绿)。
"""

import json
import re
import shutil
import subprocess

from webui_helpers import STATIC_ROOT, bundle_file, read_shared


def _shared(name):
    import os
    return os.path.join(STATIC_ROOT, "shared", name)


def _run_probe(probe, path):
    """跑一个 node 电池: 无 node 返回 None(由 _assert_battery fail-fast 红); 输出末行必须是 {ok, total, failed} JSON。
    path 传单文件路径(str)或路径列表(依序作 argv[1..n], 多域电池同进程多路 eval, 见真值快照 × 物化电池)"""
    node = shutil.which("node")
    if not node:
        return None
    paths = path if isinstance(path, (list, tuple)) else [path]
    proc = subprocess.run(
        [node, "-e", probe, *paths],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    assert proc.returncode == 0, f"node 电池跑挂: {proc.stderr.strip()}"
    return json.loads(proc.stdout.strip().splitlines()[-1])


def _assert_battery(report, what):
    assert report is not None, "无 node: 本电池无法运行(不再静默跳过, 见 R4 终审修复)"
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
  // 1. 沿判定纯函数(R5#15 注释契约: 探针真跑)
  ok("沿判定: undefined(本会话尚未连上)是沿=发 toast", _esDisconnectEdge(undefined) === true);
  ok("沿判定: true->false 跳变是沿", _esDisconnectEdge(true) === true);
  ok("沿判定: 重试期重复 onerror(prev=false)不是沿", _esDisconnectEdge(false) === false);

  // 2. startEvents: 换票接线 + 连流
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

  // 3. onopen 恢复回置; onerror 首断(沿): 恰一条 toast + 关旧连接 + 排 3s 重试
  const es1 = instances[0];
  es1.onopen();
  ok("onopen 回置 _esConnected(不发恢复噪音)", ctx._esConnected === true && ctx.toasts.length === 0);
  es1.onerror();
  ok("首次断线(沿): 恰一条 error toast 且沿位落 false", ctx.toasts.length === 1 && ctx._esConnected === false);
  ok("旧连接必关(一次性票据重连必失效)", es1.closed === true && ctx._es === null);
  ok("重试定时器已排(3s, 与 EventSource 默认重连同拍)", timers.has(ctx._esRetry) && timers.get(ctx._esRetry).ms === 3000);

  // 4. 重试期重复 onerror: 不重复 toast、不叠重试定时器(R5#14 钉的行为)
  es1.onerror();
  es1.onerror();
  ok("重试期重复 onerror 只发一条 toast", ctx.toasts.length === 1);
  ok("重复 onerror 不叠重试定时器", [...timers.values()].filter((t) => t.ms === 3000).length === 1);

  // 5. 重连: 必关旧连接换新票(R5#14 钉的行为)
  fireTimer(ctx._esRetry);
  await drain();
  ok("重连第二次换票", ticketCalls.length === 2);
  ok("重连开新连接且 _es 换新", instances.length === 2 && ctx._es === instances[1]);
  ok("重连仍走 ?ticket= 换票通道", instances[1].url.indexOf("?ticket=TK2") >= 0);
  ok("重试定时器归置", ctx._esRetry === null);

  // 6. ver 驱动: 60ms 去抖合并; 落拍 document.hidden 短路(R5#4)
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

  // 7. stopEvents 归置(R5#14: 断线沿状态位随连接会话归置)
  ctx.stopEvents();
  ok("stopEvents 关连接清句柄", ctx._es === null && ctx._esRetry === null && ctx._verTimer === null);
  ok("stopEvents 归置 _esConnected(重登后首断仍算首次断线)", ctx._esConnected === undefined);
  ok("归置后连接实例已 close", instances[1].closed === true);

  // 8. #7(issue 26-11-08-0229): 换票 await 期间登出, 落票后复查 authOk 再开流 ——
  // skip_local_verify 下换票免密钥, 票据落下不等于会话仍活; 旧序落票即开流, 首个 ver
  // 事件才被 _logout 的 stopEvents 拆除(残留至多一轮空转)。复查点在 await 恢复之后。
  const baseN = instances.length;
  const ctx7 = Object.assign({}, P, {
    authOk: true, _es: null, _esBusy: false, _esRetry: null, _verTimer: null, _esConnected: undefined,
    toasts: [], toast(msg, kind) { this.toasts.push([kind, msg]); },
    api() {  // 换票在途: 票据在登出之后才落下(手动放行, 模拟 await 窗口)
      return new Promise((res) => { this._dropTicket = () => res({ ticket: "TK7" }); });
    },
  });
  const p7 = P.startEvents.call(ctx7);
  await drain();
  ctx7.authOk = false;       // await 窗口内 _logout 收口(token 清空 => authOk 翻 false)
  ctx7._dropTicket();        // 票据落下(免密钥也发票, 旧序此处会开流)
  await p7;
  await drain();
  ok("#7 换票期间登出: 落票后不开流(authOk 复查拦在 EventSource 之前)",
    instances.length === baseN && ctx7._es === null);
  ok("#7 落票不开流不残留 _esBusy(重登后 startEvents 可正常重入)", ctx7._esBusy === false);

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
  // 1. currentPollMs 真跑分型(R5#17: 骨架探针把 currentPollMs 桩成常量的绕过面, 这里真跑)
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

  // 2. refresh 真跑: 成功清零 / 失败递增封顶(曲线的进位端)
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

  // 3. 401 分支(R5#2 修法第二半): stopPolling + stopEvents, 不再续排
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

  // 4. stopPoll 对 awaitPoll 收摊(R5#5): 兑现 null + onEnd 恰一次
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

  // 5. startPoll 顶掉同 key 有界等待: onEnd 也走(loading 复位不再被跳过), 不双调
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

  // 6. 正常收敛路径(finish)onEnd 恰一次, 与叫停路径互斥
  let ended3 = 0;
  const st3 = Object.assign({}, P, { _polls: null });
  const v3 = await P.awaitPoll.call(st3, "n", { ms: () => 0, max: 9, fn: async () => "ok",
    until: (v) => !!v, onEnd: () => { ended3 += 1; } });
  ok("收敛路径 onEnd 恰一次且兑现该拍值", v3 === "ok" && ended3 === 1);
  P.stopPoll.call(st3, "n");
  ok("收敛后 stopPoll 不再调 onEnd(alive 守卫)", ended3 === 1);

  // 7. #8(issue 26-11-08-0229): onEnd 抛异常不吞 settle —— stopPoll 与 finish 两路同式
  // try/finally, settle 必达, 异常语义不变照常上抛(finish 路在上抛处成 unhandled
  // rejection, 由收集器钉住; 旧序该异常会吞掉 settle, 调用方 Promise 永久悬挂)。
  const unhandled = [];
  process.on("unhandledRejection", (e) => unhandled.push(e));
  const boomStop = new Error("onEnd boom (stopPoll)");
  let ended7 = 0;
  const st7 = Object.assign({}, P, { _polls: null });
  const p7 = P.awaitPoll.call(st7, "j", { ms: () => 5, fn: () => null, until: () => false,
    onEnd: () => { ended7 += 1; throw boomStop; } });
  await drain();
  let stopErr = null;
  try { P.stopPoll.call(st7, "j"); } catch (e) { stopErr = e; }
  ok("#8 stopPoll 路: onEnd 异常照常上抛(不吞不藏)", stopErr === boomStop);
  ok("#8 stopPoll 路: settle 先于异常必达(兑现 null)", (await p7) === null);
  ok("#8 stopPoll 路: onEnd 恰一次", ended7 === 1);
  const boomFin = new Error("onEnd boom (finish)");
  let ended8 = 0;
  const st8 = Object.assign({}, P, { _polls: null });
  const p8 = P.awaitPoll.call(st8, "f", { ms: () => 0, max: 9, fn: async () => "ok",
    until: (v) => !!v, onEnd: () => { ended8 += 1; throw boomFin; } });
  let v8 = null; let finErr = null;
  try { v8 = await p8; } catch (e) { finErr = e; }
  await drain();
  await new Promise((r) => setImmediate(r));  // unhandledRejection 在事件轮末派发, 让一轮宏任务跑完
  ok("#8 finish 路: settle 不被 onEnd 异常吞掉(兑现该拍值)", v8 === "ok" && finErr === null);
  ok("#8 finish 路: onEnd 恰一次且异常上抛成 unhandled rejection(语义不变)",
    ended8 === 1 && unhandled.includes(boomFin));

  // 8. #1621(issue 26-11-08-1621): fail 路(fn 抛异常 -> reject)不走 onEnd, 清理归调用方 ——
  // 契约注释单点在 polling.js 文件头; 现调用面要么 fn 全吞错(tmLoad 经 _panelLoad, fail 分支
  // 不可达), 要么刻意上抛 401 统一收口(commands.js _pollCmd), 都无 onEnd 侧清理面, 故 fail
  // 不调 onEnd 是定案口径而非缺陷。此处把契约钉住, 防行为静默漂移而注释失真。
  const boomFn = new Error("fn boom");
  let ended9 = 0;
  const st9 = Object.assign({}, P, { _polls: null });
  const p9 = P.awaitPoll.call(st9, "z", { ms: () => 0, fn: () => { throw boomFn; },
    until: () => false, onEnd: () => { ended9 += 1; } });
  let fnErr = null;
  try { await p9; } catch (e) { fnErr = e; }
  await drain();
  ok("#1621 fail 路: fn 异常原样 reject(不吞不换型)", fnErr === boomFn);
  ok("#1621 fail 路: 不走 onEnd(清理归调用方, 文件头契约注释已写明)", ended9 === 0);
  ok("#1621 fail 路: 句柄表归置", st9._polls.z === null);
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
  // 1. 悬空模态结算(R5#1): 先 resolve(false) 再复位框
  let resolved = 0, resolvedWith;
  const c1 = mk();
  c1._modalResolve = (v) => { resolved += 1; resolvedWith = v; };
  A._logout.call(c1, "密钥无效或已更换");
  ok("登出结算悬空模态: resolve(false)(取消语义)", resolved === 1 && resolvedWith === false);
  ok("登出复位框状态(不留 visible 残框)", c1.modal.visible === false);
  ok("_modalResolve 归置", c1._modalResolve === null);
  ok("登出收口: 遮罩+凭证+受保护数据清空", c1.authRequired === true && c1.token === ""
    && c1.groups.length === 0 && c1.toasts.length === 0);

  // 2. SSE 通道一并拆(R5#2): 与 stopPolling/_qbTeardown 同口径
  ok("_logout 调 stopEvents(与 stopPolling/_qbTeardown 同收)",
    c1.calls.includes("stopEvents") && c1.calls.includes("stopPolling") && c1.calls.includes("_qbTeardown"));

  // 3. 无悬空模态: no-op 不炸
  const c2 = mk();
  A._logout.call(c2);
  ok("无框登出 no-op 不炸", c2.modal.visible === false && c2.calls.includes("stopEvents"));

  // 4. await 侧恢复(microtask): 看到的是已复位框状态, 删除流程走取消分支不再挂死
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

  // issue 26-11-11-0633: 右键挂点 —— 任意右键(在 header/input 早退分支**之前**)触发 flags 惰性补拉
  const drainCtx = async () => { for (let i = 0; i < 10; i++) await null; };
  let flagApi = 0;
  ctx.api = async () => { flagApi += 1; return { skip_check_menu: false, qb_traffic_enabled: false, relocate_enabled: false, ctx_menu: null }; };
  const ctxHandler = reg.filter((l) => l[0] === "document" && l[1] === "contextmenu")[0][2];
  ctx.flagsLoaded = false;
  ctxHandler({ target: { closest: () => null }, preventDefault() {} });  // 普通目标: 走完整屏蔽分支
  await drainCtx();
  ok("右键挂点: 普通右键触发 flags 惰性补拉并成功收口", flagApi === 1 && ctx.flagsLoaded === true);
  ctx.flagsLoaded = false;  // 复位再探第二条路径
  ctxHandler({ target: { closest: (s) => (s.indexOf("input") === 0 ? {} : null) } });  // input 命中早退分支
  await drainCtx();
  ok("右键挂点: input 右键在早退分支之前照样补拉", flagApi === 2);

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

# issue 26-11-11-0633: loadWebFlags boot 韧性(有限重试 + flagsLoaded 态 + 惰性补拉 + 单飞) ----
_NODE_WEBFLAGS_PROBE = r"""
const fs = require("fs");
global.window = {};
global.document = { hidden: false, addEventListener() {}, removeEventListener() {} };
// 伪时钟: 只入队不真跑, 手动放拍(免真睡 1s/3s)
const timers = new Map(); let tid = 0;
global.setTimeout = (fn, ms) => { const id = ++tid; timers.set(id, { fn, ms: ms || 0 }); return id; };
global.clearTimeout = (id) => { timers.delete(id); };
const drain = async () => { for (let i = 0; i < 10; i++) await null; };
const fireMs = (ms) => { for (const [id, t] of [...timers.entries()]) { if (t.ms === ms) { timers.delete(id); t.fn(); return true; } } return false; };
eval(fs.readFileSync(process.argv[1], "utf8"));   // lifecycle.js
const LC = window.AQB_LIFECYCLE;
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);
const FAIL_CLOSED = (c) => c.flags.skip_check_menu === false && c.flags.qb_traffic_enabled === false
  && c.flags.relocate_enabled === false && c.flags.ctx_menu === null;

// 根组件替身: api 行为可编程; flags/flagsLoaded 按 state.js 初值显式建
const mkCtx = (apiImpl) => Object.assign({}, LC.methods, {
  flags: { skip_check_menu: false, qb_traffic_enabled: false, relocate_enabled: false, ctx_menu: null },
  flagsLoaded: false, _flagsLoadSlots: null, toasts: [],
  toast(msg, kind) { this.toasts.push([kind, msg]); },
  api: apiImpl,
});
const slotsEmpty = (c) => !c._flagsLoadSlots || Object.keys(c._flagsLoadSlots).length === 0;

(async () => {
  // 1. 成功路径: 四键写回 + flagsLoaded 收口 + 单飞句柄归置
  let n = 0;
  const okCtx = mkCtx(async () => { n += 1; return { skip_check_menu: true, qb_traffic_enabled: true, relocate_enabled: true, ctx_menu: { multi: ["a"] } }; });
  ok("成功: 返回 true", (await LC.methods.loadWebFlags.call(okCtx)) === true);
  ok("成功: 恰一发请求", n === 1);
  ok("成功: 四键写回(漏键 = 该功能恒取不到真值)", okCtx.flags.skip_check_menu === true
    && okCtx.flags.qb_traffic_enabled === true && okCtx.flags.relocate_enabled === true
    && okCtx.flags.ctx_menu && okCtx.flags.ctx_menu.multi.length === 1);
  ok("成功: flagsLoaded 收口(真未启用不再被惰性补拉重复探测)", okCtx.flagsLoaded === true);
  ok("已取到: ensureWebFlags 返回 null(零网络副作用)", LC.methods.ensureWebFlags.call(okCtx) === null && n === 1);
  ok("成功: 单飞槽归置", slotsEmpty(okCtx));

  // 2. 默认单发(无重试档): 失败落 fail-closed, flagsLoaded=false
  let fails = 0;
  const f1 = mkCtx(async () => { fails += 1; throw new Error("boom"); });
  ok("单发失败: 返回 false", (await LC.methods.loadWebFlags.call(f1)) === false);
  ok("单发失败: 恰一发(不带重试档不续试)", fails === 1);
  ok("单发失败: flags 保持 fail-closed", FAIL_CLOSED(f1));
  ok("单发失败: flagsLoaded=false(未取到)", f1.flagsLoaded === false);
  ok("单发失败: 单飞槽归置(失败路径同样 finally)", slotsEmpty(f1));

  // 3. 惰性补拉: 未取到时补一发; 在途复用同一 promise(单飞不叠发); 成功后收口
  f1.api = async () => ({ skip_check_menu: true, qb_traffic_enabled: false, relocate_enabled: false, ctx_menu: null });
  const ep = LC.methods.ensureWebFlags.call(f1);
  ok("未取到: ensure 发起补拉(返回 promise)", !!ep && typeof ep.then === "function");
  ok("在途: ensure 复用同一 promise", LC.methods.ensureWebFlags.call(f1) === ep);
  ok("补拉成功: flagsLoaded 翻 true + 旗标写回", (await ep) === true && f1.flagsLoaded === true && f1.flags.skip_check_menu === true);
  ok("ensure 补拉全程恰一发(并发并入方不叠发)", fails === 1);

  // 4. boot 有限重试: 两败后第三发成功; 退避节拍 1s/3s; 失败期间保持 fail-closed
  let boot = 0;
  const bootCtx = mkCtx(async () => { boot += 1; if (boot <= 2) throw new Error("e" + boot); return { skip_check_menu: false, qb_traffic_enabled: true, relocate_enabled: false, ctx_menu: null }; });
  const bp = LC.methods.loadWebFlagsBoot.call(bootCtx);
  await drain();
  ok("boot 重试: 首败后保持 fail-closed + 未取到", boot === 1 && bootCtx.flagsLoaded === false && FAIL_CLOSED(bootCtx));
  ok("boot 重试: 首败排 1s 退避", boot === 1 && [...timers.values()].some((t) => t.ms === 1000));
  fireMs(1000);
  await drain();
  ok("boot 重试: 次败后排 3s 退避", boot === 2 && [...timers.values()].some((t) => t.ms === 3000));
  fireMs(3000);
  ok("boot 重试: 第三发成功收口(2 败 1 成 = 共 3 发)", (await bp) === true && boot === 3
    && bootCtx.flagsLoaded === true && bootCtx.flags.qb_traffic_enabled === true);
  ok("boot 重试: 定时器归置", timers.size === 0);

  // 5. boot 重试穷尽: 三发全败 -> 返回 false, flagsLoaded=false, 不再续排
  let exhaust = 0;
  const exCtx = mkCtx(async () => { exhaust += 1; throw new Error("down"); });
  const exP = LC.methods.loadWebFlagsBoot.call(exCtx);
  await drain();
  fireMs(1000); await drain();
  fireMs(3000); await drain();
  ok("boot 重试穷尽: 共三发(1 首发 + 2 补试)后止", exhaust === 3 && timers.size === 0);
  ok("boot 重试穷尽: 返回 false 且整会话 fail-closed 口径保持", (await exP) === false
    && exCtx.flagsLoaded === false && FAIL_CLOSED(exCtx));

  // 6. 登出态(e.auth)不重试: 再发只会重复 401
  let authN = 0;
  const authCtx = mkCtx(async () => { authN += 1; const err = new Error("unauthorized"); err.auth = true; throw err; });
  ok("登出态: 只一发不重试", (await LC.methods.loadWebFlagsBoot.call(authCtx)) === false && authN === 1);
  ok("登出态: 不排退避定时器", timers.size === 0);

  // 7. 并发单飞(同档): boot 重试链在途时并入的同档 loadWebFlagsBoot 复用同一 promise 不叠发
  let conc = 0;
  const concCtx = mkCtx(async () => { conc += 1; if (conc === 1) throw new Error("first"); return {}; });
  const cp = LC.methods.loadWebFlagsBoot.call(concCtx);
  const cp2 = LC.methods.loadWebFlagsBoot.call(concCtx);  // 同帧并入(单飞位已占)
  await drain();
  const cp3 = LC.methods.loadWebFlagsBoot.call(concCtx);  // 退避窗口期并入(1s 未放拍, 槽仍被 boot 链持有)
  ok("并发单飞(同档): 同帧与退避窗口期并入都复用同一 promise", cp2 === cp && cp3 === cp);
  fireMs(1000);
  ok("并发单飞(同档): 共两发(首发败 + 1s 重试成功), 并入方不叠发", (await cp) === true && (await cp2) === true && conc === 2);

  // 8. 档位分槽: 单飞槽记重试档 —— boot 链在途时惰性补拉异档另起单发(不骑退避链,
  //    await 方不必等重试穷尽才落门控), boot 的 3 发保障也不被在途惰性单发降级
  let slot = 0;
  const slotCtx = mkCtx(async () => { slot += 1; if (slot === 1) throw new Error("b1"); return {}; });
  const bp2 = LC.methods.loadWebFlagsBoot.call(slotCtx);
  await drain();  // 首败, 排 1s, boot 档槽在途
  const bp3 = LC.methods.loadWebFlagsBoot.call(slotCtx);
  ok("档位分槽: boot 链在途时同档再调复用同一 promise", bp3 === bp2);
  const lp2 = LC.methods.ensureWebFlags.call(slotCtx);
  ok("档位分槽: 惰性补拉异档另起单发(不复用 boot 链)", lp2 !== bp2 && typeof lp2.then === "function");
  ok("档位分槽: 惰性单发独立落地成功", (await lp2) === true);
  const bp4 = LC.methods.loadWebFlagsBoot.call(slotCtx);
  ok("档位分槽: 惰性结算不挤占 boot 槽(仍在途 boot 链可复用, 不叠发)", bp4 === bp2);
  fireMs(1000);
  ok("档位分槽: boot 重试第二发成功收口", (await bp2) === true && (await bp3) === true);
  ok("档位分槽: 请求计数恰 3 发(boot 2 + 惰性 1, 无人叠发)", slot === 3);

  console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
    failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
})().catch((e) => { console.error(e && e.stack || e); process.exit(1); });
"""
# S2a ingestion 物化缝(计划 26-11-11-0630 §03)× 乐观真值快照: 绿色向三场景 ----------------------
# S2a 后组行 members 进客户端是 hash 串, 三条 state 入口(polling.js applyStateRows 全量/delta +
# auth.js bootstrap)在赋值前就地物化成成员行浅拷贝; _snapshotTruth(commands_optimistic.js)的组员
# 源随之从服务端成员字典换成这些拷贝 —— 快照「只认服务端真值」的语义换源后要重新钉住, 此前该缝
# tests/ 零命中(e2e 乐观用例只走 Happy 时序)。
# *已知边界(不落断言, S2a 报告表述修正)*: 误判窗口 = 组脏(**他员变化**使组进 d.groups)+ 该组另有
# 成员 pending —— delta 物化源落到本地已打补丁行, 快照可能读到补丁值而提前撤 hold(op.prev 同窗被
# 污染)。影响如实两分支: 成功路径真值落地即收敛(观感与换源前一致); 失败/停滞路径(该成员此后静默
# 不脏)补丁值停留至其下次变化或下一次全量轮, 期间失败回滚(resolveOptimistic: op 已删即跳过)与
# 3s 兜底(_expirePending 同依赖 pendingOps)一并被跳过 —— 是长期滞留而非「一轮弹回」, 已确认接受
# 该残留(S2 缝语义)。「组完全未脏」是安全向(场景 3 断言钉住); 组完全未脏时物化根本不发生
# (组不进 d.groups), 与误判窗口互斥。
# *接线覆盖声明*: 三场景直呼物化/快照助手, 不经 applyStateRows/refresh 驱动 —— 三入口接线
# (delta 桶序 torrents/singles 先于 groups、先物化后赋值、auth.js bootstrap 同缝)由 S4 e2e
# 全量回归覆盖(计划 26-11-11-0630 §04 S4), 本电池不重复钉。
_NODE_TRUTHSNAPSHOT_PROBE = r"""
const fs = require("fs");
global.window = {};
eval(fs.readFileSync(process.argv[1], "utf8"));   // polling.js(S2a 物化三助手 _memberIndexBuild/_materializeGroupRows/_rematDrain)
eval(fs.readFileSync(process.argv[2], "utf8"));   // commands.js 域聚合(commands + commands_optimistic + commands_send)
const P = window.AQB_POLL.methods;
const C = window.AQB_COMMANDS.methods;
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

// vm = 轮询域 + 命令域 methods 合并(生产里 mixin 进同一个 Vue 实例, 方法全走 this)
const mk = () => Object.assign({}, P, C, {
  torrents: [], singles: [], groups: [], pendingOps: {}, truthSnapshot: null,
});
// 基线: 组 k1 两成员 A(活跃, 会变的"他员") + B(将 pending); 组行 hash 形进站 → 物化
const boot = (vm) => {
  vm.torrents = [{ hash: "A", kind: "downloading", progress: 0.5 }, { hash: "B", kind: "seeding", progress: 1 }];
  vm.singles = [];
  vm.groups = [{ key: "k1", members: ["A", "B"] }];
  vm._materializeGroupRows(vm.groups, vm._memberIndexBuild(vm.torrents, vm.singles));
  vm.pendingOps = {};
  vm.truthSnapshot = null;
};

(async () => {
  // 0. 物化基元(spike 裁决不变式): 组员是**独立浅拷贝**非平铺行引用 —— 同 hash 多命中各为
  //    独立对象, 乐观链 prev 采集(后命中覆盖前命中)才不互相污染; 快照换源后的语义全建立在它上。
  const vm0 = mk();
  boot(vm0);
  ok("物化: hash 形 members 原地换成成员行对象(消费位不见 hash 串)", typeof vm0.groups[0].members[0] === "object");
  ok("物化: 组员拷贝独立于平铺行(非同一引用)", vm0.groups[0].members[1] !== vm0.torrents[1]);
  vm0.applyOptimisticPatch(["B"], "pause", { kind: "paused" });
  ok("补丁链: _forEachRow 三数组同拍命中(平铺行 + 组员拷贝都吃到 patch)",
    vm0.torrents[1].kind === "paused" && vm0.groups[0].members[1].kind === "paused");

  // 1. 全量轮(命令在途): refresh 走 full 分支, 物化源 = 载荷平铺行 = 服务端真值(B 仍 seeding,
  //    pause 未落地)→ 快照逐键比对读真值 → 不误判收敛(hold 保留), 且 op.prev 被真值保鲜
  //    (take() 的 op.prev 合并) —— 兜底回滚打的是真值, 不是补丁值。
  //    判别面: 快照 torrents 桶只放 [A](take 先扫平铺桶, m.has 短路)—— B 只能经组员拷贝命中,
  //    物化源(载荷真值 vs 本地已补丁行)才真正进断言; 若物化错源读补丁值(kind=paused),
  //    「不误判收敛」与「prev 保鲜」两条都会红。
  const vm1 = mk();
  boot(vm1);
  vm1.applyOptimisticPatch(["B"], "pause", { kind: "paused" });
  const fullT = [{ hash: "A", kind: "downloading", progress: 0.6 }, { hash: "B", kind: "seeding", progress: 1 }];
  const fullG = [{ key: "k1", members: ["A", "B"] }];
  vm1._materializeGroupRows(fullG, vm1._memberIndexBuild(fullT, []));
  vm1._snapshotTruth({ torrents: [fullT[0]], singles: [], groups: fullG });
  ok("全量轮在途: 快照确实经组员拷贝取到 B(守门: groups 迭代回退/物化失效时此条红)",
    vm1.truthSnapshot && vm1.truthSnapshot.has("B"));
  ok("全量轮在途: 快照读载荷真值(kind=seeding)→ 不误判收敛(hold 保留)",
    vm1._optimisticSettled("B", vm1.pendingOps.B) === false);
  ok("全量轮在途: op.prev 保鲜为服务端真值(兜底回滚不打到补丁值)", vm1.pendingOps.B.prev.kind === "seeding");

  // 2. 全量轮(真值已落地): 服务端 kind=paused 与补丁对齐 → 收敛(撤 hold 出口, 既有契约)。
  const vm2 = mk();
  boot(vm2);
  vm2.applyOptimisticPatch(["B"], "pause", { kind: "paused" });
  const landT = [{ hash: "A", kind: "downloading", progress: 0.6 }, { hash: "B", kind: "paused", progress: 1 }];
  const landG = [{ key: "k1", members: ["A", "B"] }];
  vm2._materializeGroupRows(landG, vm2._memberIndexBuild(landT, []));
  vm2._snapshotTruth({ torrents: landT, singles: [], groups: landG });
  ok("真值落地: 快照 kind=paused 与补丁对齐 → 收敛(撤 hold)", vm2._optimisticSettled("B", vm2.pendingOps.B) === true);

  // 3. 增量轮(组未脏, 安全向): B 的组 k1 未脏 → 不进 d.groups → 物化不发生、快照无 B →
  //    不收敛(hold 保留, 交 3s 兜底) —— 宁可慢收不可误判; 同轮另一组 k2 脏(X 推进)照常
  //    走 delta 物化与快照, 证明安全向不是"delta 轮整体跳过"的假绿。
  const vm3 = mk();
  boot(vm3);
  vm3.applyOptimisticPatch(["B"], "pause", { kind: "paused" });
  const dT = [{ hash: "X", kind: "downloading", progress: 0.9 }];
  const dG = [{ key: "k2", members: ["X"] }];
  vm3.torrents = [...vm3.torrents, dT[0]];   // 平铺桶先行合并(applyRows upsert 追加)
  vm3._materializeGroupRows(dG, vm3._memberIndexBuild(null, null));
  vm3._snapshotTruth({ torrents: dT, singles: [], groups: dG });
  ok("增量轮组未脏: 快照无该 hash → 不误判收敛(hold 保留, 3s 兜底)",
    vm3._optimisticSettled("B", vm3.pendingOps.B) === false);

  console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
    failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
})().catch((e) => { console.error(e && e.stack || e); process.exit(1); });
"""

# S3 version-reload 自愈(计划 26-11-11-0630 §03 version-reload 行 / §04 S3 行)--------------------
# 钉 §04 S3 验收的机械面: 前端轮询比对 status payload 既有 version 字段(_status_payload 恒回传),
# 变更即 location.reload() 自愈 + 防抖避免重签发循环。可控时钟替身 global.Date(电池免真睡 30s
# 防抖窗口); sessionStorage/location 桩沿既有电池先例(global 桩, config_editor 电池同款)。
# 单点语义见 polling.js _versionSelfHeal 注(循环场景怎么破的三层口径都注释在生产代码里)。
_NODE_VERSIONRELOAD_PROBE = r"""
const fs = require("fs");
global.window = {};
global.document = { hidden: false };
const store = {};               // sessionStorage 替身: 记录写入面(主探针存储可用)
let storeReads = 0;
global.sessionStorage = {
  getItem(k) { storeReads += 1; return Object.prototype.hasOwnProperty.call(store, k) ? store[k] : null; },
  setItem(k, v) { store[k] = String(v); },
};
const reloads = [];
global.location = { reload: () => reloads.push(1) };
let t = 1730000000000;          // 可控时钟
global.Date = { now: () => t };
eval(fs.readFileSync(process.argv[1], "utf8"));   // polling.js
const P = window.AQB_POLL.methods;
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

// refresh 全依赖桩(与退避曲线电池同一家): api 每轮注入 payload, 域外方法全替身
const mk = () => Object.assign({}, P, {
  status: null, lastRid: null, pollFails: 0, serviceDown: false, selectedCount: 0,
  searchQuery: "", viewMode: "", nextN: 0, cfgGuardDirty: false,
  _versionSeen: null,   // 真机初值来自 state.js data()(state.js 不在电池聚合面, 搜索续查电池
                        // _searchRetryFails 同款先例); 替身自备同值 = 与真机同臂(基线判据单臂 === null)
  api: async () => { throw new Error("payload 未注入"); },
  _expirePending() {}, reapplyPending() {}, _maybeSearchRefresh() {}, _snapshotTruth() {},
  scheduleNext() { this.nextN += 1; },
  cfgGuardActive() { return !!this.cfgGuardDirty; },  // 守卫判据替身(域外方法全替身): 置位驱动守卫活跃
});
const payload = (ver) => ({
  status: ver === undefined ? { torrents: 0 } : { torrents: 0, version: ver },
  updated: true, rid: 1,
});
const poll = async (ctx, ver) => { ctx.api = async () => payload(ver); await P.refresh.call(ctx); };

(async () => {
  // --- A. 基线与变更沿((1)(2)) ---
  const ctx = mk();
  await poll(ctx, "1.2.3");
  ok("首轮: 记基线不 reload(首见=基线, 不当变更沿)", reloads.length === 0 && ctx._versionSeen === "1.2.3");
  ok("首轮照常应用 status + 续排", ctx.status && ctx.status.version === "1.2.3" && ctx.nextN === 1);
  await poll(ctx, "1.2.3");
  ok("(1)version 一致轮不 reload(直通, 不碰存储)", reloads.length === 0 && ctx.nextN === 2 && storeReads === 0);
  await poll(ctx, "9.9.9");
  ok("(2)version 变更轮发起 reload", reloads.length === 1);
  ok("(2)reload 轮中止: status 不更新(跨版本载荷不喂旧 JS)", ctx.status.version === "1.2.3");
  ok("(2)reload 轮照常续排下一拍(防抖封顶续排无循环; 导航取消时链保活)", ctx.nextN === 3);
  ok("(2)基线不动(仍=本页 incarnation 版本)", ctx._versionSeen === "1.2.3");
  ok("(2)防抖时间戳已入 sessionStorage(恰好一键, 数字时间戳)",
    Object.keys(store).length === 1 && /^\d+$/.test(Object.values(store)[0]));

  // --- B. (3)防抖窗口内不重复 reload + 窗口外放行 ---
  t += 1000;
  await poll(ctx, "0.0.1");
  ok("(3)防抖窗口内第二次变更不重复 reload", reloads.length === 1);
  ok("(3)窗口内本轮照常处理+续排(有界节流非冻结)", ctx.nextN === 4 && ctx.status.version === "0.0.1");
  ok("(3)窗口内不动基线(窗口外才可能再次自愈)", ctx._versionSeen === "1.2.3");
  t += 31000;   // 拨出 30s 窗口(时间戳与内存层同批入账, 双层同老)
  await poll(ctx, "0.0.1");
  ok("窗口外再变更: 放行一次 reload(1 次/窗口的有界节流)", reloads.length === 2);

  // --- C. (4)version 缺失/非字符串轮保守默认 ---
  const ctx2 = mk();
  await poll(ctx2, undefined);
  ok("(4)version 缺失轮不触发、不动基线(老服务端响应)", reloads.length === 2 && ctx2._versionSeen == null);
  await poll(ctx2, null);
  ok("(4)version 非字符串(null)轮不触发、不动基线(异常响应)", reloads.length === 2 && ctx2._versionSeen == null);
  await poll(ctx2, "7.7.7");
  ok("(4)缺后再见 version: 首见记基线, 不当变更沿", reloads.length === 2 && ctx2._versionSeen === "7.7.7");

  // --- D. reload 后新页重记基线(循环破除主证据: 稳定版本恰好一次 reload 零循环) ---
  const ctx3 = mk();   // 模拟 reload 后的新页 incarnation: 实例态全新, sessionStorage 仍存(跨 reload 存活)
  await poll(ctx3, "9.9.9");
  ok("reload 后新页: 首轮记新基线, 不二次 reload", reloads.length === 2 && ctx3._versionSeen === "9.9.9");
  await poll(ctx3, "9.9.9");
  ok("reload 后新页: 稳定版本下恒不再触发(零循环)", reloads.length === 2 && ctx3.nextN === 2);

  // --- E. 配置编辑器脏态守卫共存((5)): cfgGuardActive 活跃轮跳过自愈, 释放后下一轮自然再触发 ---
  const ctx4 = mk();   // 全新 incarnation; store/时钟沿用(与真实多轮轮询同环境)
  await poll(ctx4, "2.0.0");
  ctx4.cfgGuardDirty = true;   // 用户正在编辑配置(守卫判据为真, 双脏源替身置位驱动)
  const stampBefore = Object.values(store)[0];
  await poll(ctx4, "3.0.0");
  ok("(5)守卫活跃轮不 reload(后台轮询不替脏态用户弹原生框)", reloads.length === 2);
  ok("(5)守卫活跃轮轮询照常: 载荷应用+续排不中断", ctx4.status.version === "3.0.0" && ctx4.nextN === 2);
  ok("(5)守卫活跃轮不记基线(变更沿留给释放后的轮次)", ctx4._versionSeen === "2.0.0");
  ok("(5)守卫活跃轮不记防抖时间戳(存储层值不动; 内存层与存储层同拍入账)", Object.values(store)[0] === stampBefore);
  t += 31000;   // 拨出 B 段遗留时间戳的窗口, 释放轮不再受防抖拦
  ctx4.cfgGuardDirty = false;   // 守卫释放(保存/放弃清脏)
  await poll(ctx4, "3.0.0");
  ok("(5)守卫释放后的下一轮: 变更沿自然再触发 reload", reloads.length === 3);

  console.log(JSON.stringify({ ok: checks.filter((c) => c[1]).length, total: checks.length,
    failed: checks.filter((c) => !c[1]).map((c) => c[0]) }));
})().catch((e) => { console.error(e && e.stack || e); process.exit(1); });
"""

# 存储不可用分支(私隐模式访问即抛, columns_persist.js 先例)独立探针: 内存层 _versionReloadMemAt
# 是模块级状态, 与主探针共用进程会串账(主探针的 reload 已写入内存层)—— 单进程隔离才能钉
# fail-open 与内存层窗口外放行。残留面(跨 reload 记忆丢失, 唯「存储被禁+每请求翻转版本」才可能
# 循环)已在 polling.js 注释 declared, 本电池不钉不可达面。
_NODE_VERSIONRELOAD_NOSTORE_PROBE = r"""
const fs = require("fs");
global.window = {};
global.document = { hidden: false };
const denied = () => { throw new Error("Storage denied"); };
global.sessionStorage = { getItem: denied, setItem: denied };   // 私隐模式: 访问即抛
const reloads = [];
global.location = { reload: () => reloads.push(1) };
let t = 1730000000000;
global.Date = { now: () => t };
eval(fs.readFileSync(process.argv[1], "utf8"));   // polling.js
const P = window.AQB_POLL.methods;
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);
const mk = () => Object.assign({}, P, {
  status: null, lastRid: null, pollFails: 0, serviceDown: false, selectedCount: 0,
  searchQuery: "", viewMode: "", nextN: 0, cfgGuardDirty: false,
  _versionSeen: null,   // 真机初值来自 state.js data()(state.js 不在电池聚合面); 替身自备同值, 与真机同臂
  api: async () => { throw new Error("payload 未注入"); },
  _expirePending() {}, reapplyPending() {}, _maybeSearchRefresh() {}, _snapshotTruth() {},
  scheduleNext() { this.nextN += 1; },
  cfgGuardActive() { return !!this.cfgGuardDirty; },  // 守卫判据替身: 本探针恒不活跃, 只为过新增守卫沿
});
const payload = (ver) => ({
  status: ver === undefined ? { torrents: 0 } : { torrents: 0, version: ver },
  updated: true, rid: 1,
});
const poll = async (ctx, ver) => { ctx.api = async () => payload(ver); await P.refresh.call(ctx); };

(async () => {
  const ctx = mk();
  await poll(ctx, "1.0.0");
  ok("存储不可用: 首轮记基线不 reload(内存零值不误拦首轮)", reloads.length === 0 && ctx._versionSeen === "1.0.0");
  await poll(ctx, "2.0.0");
  ok("存储不可用: 变更沿仍放行 reload(fail-open, 自愈不让位)", reloads.length === 1);
  t += 1000;
  await poll(ctx, "3.0.0");
  ok("存储不可用: 内存层同页限流仍拦重复触发(防抖不随存储缺席而全失)", reloads.length === 1);
  t += 31000;
  await poll(ctx, "3.0.0");
  ok("存储不可用: 窗口外放行(内存层窗口同口径)", reloads.length === 2);
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


def test_r4_webflags_boot_retry_and_ensure():
    """issue 26-11-11-0633: loadWebFlags boot 韧性 node 电池真跑 —— boot 期 1s/3s 有限重试
    (穷尽三发止/auth 态不重试) + flagsLoaded 态收口("未启用"与"未取到"可分) + 惰性补拉
    ensureWebFlags(已取到零副作用/在途复用单飞) + 并发单飞不叠发; 全程 fail-closed 语义保持。"""
    _assert_battery(_run_probe(_NODE_WEBFLAGS_PROBE, _shared("lifecycle.js")), "flags boot 韧性电池")
def test_r4_truth_snapshot_materialized_members():
    """S2a 物化缝 × 乐观真值快照: 快照读服务端真值不读本地补丁值(全量在途/真值落地/增量安全向三绿色向)。"""
    _assert_battery(
        _run_probe(_NODE_TRUTHSNAPSHOT_PROBE, [_shared("polling.js"), bundle_file("commands.js")]),
        "真值快照×物化电池",
    )


def test_r4_version_reload_self_heal():
    """S3 version-reload(计划 26-11-11-0630 §04): 轮询比对 version 自愈 —— 一致直通/变更沿 reload(载荷
    不应用但照常续排, 防抖封顶)/30s 防抖窗口内不重复 reload(窗口外放行)/缺失与非字符串轮保守默认/
    配置脏态守卫活跃轮跳过自愈(释放后再触发) + reload 后新页重记基线零循环。"""
    # 静态钉(照 test_webui_static_dom_page_layout.py cfgGuardActive 守阵先例): 电池的守卫沿由替身
    # 置位驱动, 只测「守卫活跃时怎么走」; 真机变更沿是否**真的问过守卫**电池测不到, 静态钉补位 ——
    # _versionSelfHeal 函数体内必须保留 cfgGuardActive 调用(删/绕开 = 后台轮询替脏态用户弹原生框)。
    heal = re.search(r"_versionSelfHeal\(status\) \{(.*?)\n    \},", read_shared("polling.js"), re.S)
    assert heal, "polling.js 缺 _versionSelfHeal(改名? 同步本守阵与 node 电池)"
    assert "this.cfgGuardActive()" in heal.group(1), \
        "变更沿必须先问配置编辑器脏态守卫(cfgGuardActive): 删/绕开 = 后台自愈 reload 替脏态用户弹原生 beforeunload 框"
    _assert_battery(_run_probe(_NODE_VERSIONRELOAD_PROBE, _shared("polling.js")), "version-reload 电池")


def test_r4_version_reload_no_storage_fallback():
    """S3 version-reload 存储不可用分支(独立探针): sessionStorage 访问即抛时 fail-open 放行自愈 reload,
    内存层同页限流仍拦重复触发、窗口外放行(跨 reload 记忆丢失残留见 polling.js 注释声明)。"""
    _assert_battery(_run_probe(_NODE_VERSIONRELOAD_NOSTORE_PROBE, _shared("polling.js")), "version-reload 无存储电池")
