"""test_webui_static_r4_static_batteries 测试计划: 存量评审 R4 static 主题清池 P09 —— commands/hr/scope_audit/ui_feedback 四域 node 电池

## 测试计划(每个测试函数一条)
- test_r4_cmdstats_receipt_ownership: R5#233(major) 修复回归 —— cmdStats 单槽归属校验 node 电池真跑:
  命令 A 在途时点击 B(_newCmdStats 整体重写槽), A 的回执到达不许把 totalMs/waitMs/execMs/cmdId
  合并进 B 的槽、A 的 cmd 事件不写 B 的 eventMs、A 的旧 t0 迟到入账不写 B 的 patch/post 两段;
  B 自己的回执照常合并(点击侧 patchMs 保留)、归属内的事件照常落 eventMs(修复前旧回执错挂必红)
- test_r4_set_row_icon_timer_lifecycle: R5#29 —— setRowIcon 假计时器电池真跑: 每 hash 覆盖先清旧
  定时器(先落 pending 再落 ok, pending 的 45s 兜底定时器必须被 clearTimeout, 否则误触发即清掉后到的
  图标)、ok 图标按 ALERT_ICON_MS.ok(10s) 存活不被 45s pending 兜底提前清掉(推时钟 10s 恰好退场)、
  显式 ms 覆盖档位寿命、非法 kind 摘图标不排定时器、rowIcon 对过期 until 的兜底判读
- test_r4_waitcmd_race_settle_three_timings: R5#25 —— waitCmd SSE/轮询竞态三时序 node 电池真跑:
  事件先到(收摊: 落败轮询路 stop.v 置位 + _cancelCmdWait 清 waiter)/轮询先到(事件路 waiter 同口径
  清掉, 回执 error 原样带出)/双超时(回退 {ok:false} 且超时文案逐字), 落败路径一律收摊
- test_r4_hr_pop_data_matrix_and_place: R5#191 —— HR 悬停弹窗 hrPopData 纯映射分支矩阵(excluded 两态/
  未接入 null/badge 与 gauge 互斥/考察中 need 端点与无端点两态/本地已超出与还需/终态 failed/站点轨 pct
  夹取/lag 判定/verdict 回落)+ _hrPopPlace 定位几何(上方优先/翻下方/贴底钳位/零矩形收弹窗/箭头钳位)
- test_r4_scope_audit_classify_ring_dedup: R5#27 —— _auditScope 分类 node 电池真跑: shape(载荷形状/
  非串元素)/dup/empty/ok 五类 rec.kind 逐类断言 + {groupKeys,memberHashes} 兼容形状 + 签名去重 warn
  只响一次 + 50 条有界环挤出最旧 + 关态零记账
- test_r4_err_history_ring_upsert_unread: R5#19 —— 通知环形缓冲行为契约 node 电池真跑: emit 即收
  (info/busy 不入史)/同 id 二次 _recordErrorToast 只覆盖不增行(「同一条错误只留一条」)/busy 经
  _finishToast 结算成终态首次入史/第 51 条挤掉最旧(unshift 新在上 + pop 最旧)/errPanelOpen=false 时
  _errUnread 递增而 true 不计

加载口径: 单文件域直接读盘 eval(顶层纯函数声明随非严格 eval 入作用域, 同 hrsCompareRows 电池范式);
定时器桩住只记节拍/手动放拍(waitCmd 双超时一支用 1.1s 真钟, 其余零真睡)。无 node 静默跳过(返回 None,
不引入 pytest skip; 有 node 时断言电池全绿)。
"""

import json
import os
import shutil
import subprocess

from webui_helpers import STATIC_ROOT


def _shared(name):
    return os.path.join(STATIC_ROOT, "shared", name)


def _run_probe(probe, *args):
    """跑一个 node 电池: 无 node 静默跳过(返回 None); 输出末行必须是 {ok, total, failed} JSON"""
    node = shutil.which("node")
    if not node:
        return None
    proc = subprocess.run(
        [node, "-e", probe, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0, f"node 电池跑挂: {proc.stderr.strip()}"
    return json.loads(proc.stdout.strip().splitlines()[-1])


def _assert_battery(report, what):
    assert report is not None, "无 node: 本电池静默跳过(与既有电池同口径)"
    assert report["failed"] == [], f"{what} {report['ok']}/{report['total']} 过, 失败: {report['failed']}"


# R5#233: cmdStats 单槽归属校验 -------------------------------------------------
_NODE_CMDSTATS_OWNERSHIP_PROBE = r"""
const fs = require("fs");
global.window = {};
// [perf] 打点进桩(既不污染 stdout 末行 JSON, 也供断言"错挂时会有 warn")
const logs = [];
global.console = { log: (...a) => logs.push(["log", a.join(" ")]), warn: (...a) => logs.push(["warn", a.join(" ")]) };
const src = fs.readFileSync(process.argv[1], "utf8");
eval(src + "\n;globalThis.__W2__ = window.AQB_COMMANDS;");
const M = globalThis.__W2__.methods;

// 回执两路都桩成手工放拍的手工 deferred: waitCmd 的竞态骨架照常真跑, 时序由电池控制
const mkD = () => { let res; const p = new Promise((r) => { res = r; }); return { p, res }; };
const mkCtx = () => {
  const evD = {}, pollD = {};
  const c = Object.assign({}, M, {
    cmdStats: null,
    pendingOps: {},
    _cmdWaiters: null,
    _awaitCmd: (id) => { const d = mkD(); evD[id] = d; return d.p; },
    _pollCmd: (id) => { const d = mkD(); pollD[id] = d; return d.p; },
    __evD: evD, __pollD: pollD,
  });
  return c;
};
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);
// node -e 含 top-level await 时按 ESM 解析(与 require 冲突): 场景体包 async IIFE
(async () => {

// 场景: 命令 A 在途(已开始等回执) -> 点击 B(_newCmdStats 整体重写槽) -> A 的回执迟到
let c = mkCtx();
const t0A = c._newCmdStats("pause");
c._markCmdPatch(t0A);
const pA = c.waitCmd("A1", 40000);
ok("场景有效: A 在途时槽已补记归属 cmdId=A1", c.cmdStats && c.cmdStats.cmdId === "A1");
const t0B = c._newCmdStats("resume");
c._markCmdPatch(t0B);
const pB = c.waitCmd("B1", 40000);
ok("B 建槽后归属换人 cmdId=B1", c.cmdStats && c.cmdStats.cmdId === "B1");
ok("B 的槽保住点击侧 patchMs(合并而非替换的既有契约)", typeof c.cmdStats.patchMs === "number");

// A 的回执迟到(轮询路径先回): 只许拿结果, 不许动 B 的槽
c.__pollD["A1"].res({ cmd_id: "A1", status: "ok", wait_ms: 5, exec_ms: 3 });
const rA = await pA;
ok("A 的回执结果转换不受影响(ok)", rA && rA.ok === true && rA.status === "ok");
ok("A 的回执不合并进 B 的槽(totalMs/waitMs/execMs 全不落)",
   c.cmdStats.totalMs == null && c.cmdStats.waitMs == null && c.cmdStats.execMs == null);
ok("A 的回执不改写归属(cmdId 仍是 B1)", c.cmdStats.cmdId === "B1");

// A 的 cmd 事件迟到同理: eventMs 是点击侧埋点, 不许挂到 B 头上
c.onCmdEvent({ cmd_id: "A1" });
ok("A 的事件不写 B 的 eventMs", c.cmdStats.eventMs == null);
// A 的旧 t0 迟到入账同理(patch/post 两段按 t0 归属比对)
c._markCmdPost(t0A);
ok("A 的旧 t0 迟到入账不写 B 的 postMs", c.cmdStats.postMs == null);

// B 自己的链路一切照常
c._markCmdPost(t0B);
ok("B 自己的 POST 入账正常", typeof c.cmdStats.postMs === "number");
c.__pollD["B1"].res({ cmd_id: "B1", status: "ok", wait_ms: 12, exec_ms: 7 });
const rB = await pB;
ok("B 自己的回执正常合并(waitMs/execMs/cmdId 落槽, 点击侧 patchMs 保留)",
   rB && rB.ok === true && c.cmdStats.waitMs === 12 && c.cmdStats.execMs === 7
   && c.cmdStats.cmdId === "B1" && typeof c.cmdStats.patchMs === "number");

// 归属内的事件照常落 eventMs(防"一刀切全丢"的过修)
c = mkCtx();
c._newCmdStats("pause");
const pC = c.waitCmd("C1", 40000);
c.onCmdEvent({ cmd_id: "C1" });
ok("归属内的事件正常写 eventMs", typeof c.cmdStats.eventMs === "number");
c.__evD["C1"].res({ cmd_id: "C1", status: "ok", wait_ms: 1, exec_ms: 1 });
const rC = await pC;
ok("归属内的回执正常合并", rC && rC.ok === true && c.cmdStats.waitMs === 1);
process.stdout.write(JSON.stringify({
  ok: checks.filter((x) => x[1]).length, total: checks.length,
  failed: checks.filter((x) => !x[1]).map((x) => x[0]),
}) + "\n");
})().catch((e) => { process.stderr.write(String((e && e.stack) || e) + "\n"); process.exit(1); });
"""

# R5#29: setRowIcon 假计时器电池 -------------------------------------------------
_NODE_SET_ROW_ICON_PROBE = r"""
const fs = require("fs");
global.window = {};
// 假计时器: 记 {fn, ms, cleared}; flush 推时钟 —— 只触发"到点且未被清"的定时器(被清的不许再响)
const timers = [];
global.setTimeout = (fn, ms) => { timers.push({ fn, ms, cleared: false, at: 0 }); return timers.length; };
global.clearTimeout = (id) => { if (timers[id - 1]) timers[id - 1].cleared = true; };
const flush = (uptoMs) => {
  for (const t of timers) {
    if (!t.cleared && !t.at && t.ms <= uptoMs) { t.at = uptoMs; t.fn(); }
  }
};
const src = fs.readFileSync(process.argv[1], "utf8");
eval(src + "\n;globalThis.__W2__ = window.AQB_COMMANDS;");
const M = globalThis.__W2__.methods;
const mkCtx = () => Object.assign({}, M, { alertIcons: {}, _rowIconTimers: {} });
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

// 1) pending 落图标: 45s 兜底寿命 + 定时器排上
let c = mkCtx();
c.setRowIcon("h1", "pending", "汇报中");
ok("pending 图标落槽(kind/msg 正确)", c.alertIcons.h1 && c.alertIcons.h1.kind === "pending" && c.alertIcons.h1.msg === "汇报中");
ok("pending 寿命 = ALERT_ICON_MS.pending(45s 兜底)",
   c.alertIcons.h1.until - Date.now() > 44000 && c.alertIcons.h1.until - Date.now() <= 45000);
ok("pending 定时器已排(45s)", timers.length === 1 && timers[0].ms === 45000 && !timers[0].cleared);

// 2) 先落 pending 再落 ok: 旧定时器必须被清(否则 45s 兜底会动后到的图标), ok 按 10s 存活
c.setRowIcon("h1", "ok", "完成");
ok("覆盖后旧 pending 定时器被 clearTimeout", timers[0].cleared === true);
ok("ok 定时器按 ALERT_ICON_MS.ok(10s)重排", timers.length === 2 && timers[1].ms === 10000 && !timers[1].cleared);
ok("ok 图标 until 按 10s 计(不是 45s)",
   c.alertIcons.h1.kind === "ok" && c.alertIcons.h1.until - Date.now() > 9000 && c.alertIcons.h1.until - Date.now() <= 10000);
// 旧定时器已清 = 事件循环不会再唤它(45s 兜底对后到图标彻底失声); 推时钟验证存活曲线
flush(9999);
ok("ok 图标存活到 10s 内(不被提前清)", c.alertIcons.h1 && c.alertIcons.h1.kind === "ok");
flush(10000);
ok("10s 到点 ok 图标退场且定时器槽位清掉", !c.alertIcons.h1 && !c._rowIconTimers.h1);

// 3) 显式 ms 覆盖档位寿命
c = mkCtx();
c.setRowIcon("h2", "warn", "已受理", 5000);
ok("显式 ms 覆盖档位寿命(5s 不是 warn 的 180s)",
   timers[timers.length - 1].ms === 5000 && c.alertIcons.h2.until - Date.now() > 4000 && c.alertIcons.h2.until - Date.now() <= 5000);

// 4) 非法 kind = 摘图标 + 不排定时器
c = mkCtx();
c.setRowIcon("h3", "pending", "x");
const nTimers = timers.length;
c.setRowIcon("h3", "bogus", "y");
c.setRowIcon("h3", "", "y");
ok("非法/空 kind 摘图标", !c.alertIcons.h3);
ok("非法 kind 不排新定时器", timers.length === nTimers);
ok("无 hash 直接返回(不炸)", c.setRowIcon("", "ok", "z") === undefined);

// 5) rowIcon 读口的过期兜底(定时器被页面挂起时不留孤儿图标)
c = mkCtx();
c.alertIcons.h4 = { kind: "ok", msg: "", until: Date.now() - 1 };
ok("until 已过 -> rowIcon 返回 null", c.rowIcon("h4") === null);
c.alertIcons.h5 = { kind: "ok", msg: "", until: 0 };
ok("until=0(无自动过期)-> rowIcon 照常返回", c.rowIcon("h5") && c.rowIcon("h5").kind === "ok");
ok("无记录 -> null", c.rowIcon("nope") === null);
console.log(JSON.stringify({
  ok: checks.filter((x) => x[1]).length, total: checks.length,
  failed: checks.filter((x) => !x[1]).map((x) => x[0]),
}));
"""

# R5#25: waitCmd 竞态三时序 -------------------------------------------------------
_NODE_WAITCMD_RACE_PROBE = r"""
const fs = require("fs");
global.window = {};
global.console = { log: () => {}, warn: () => {} };
const src = fs.readFileSync(process.argv[1], "utf8");
eval(src + "\n;globalThis.__W2__ = window.AQB_COMMANDS;");
const M = globalThis.__W2__.methods;
const mkD = () => { let res; const p = new Promise((r) => { res = r; }); return { p, res }; };
// _awaitCmd 用真实现(真挂 waiter 表, 供 _cancelCmdWait 清 waiter 断言); 轮询路桩成手工放拍
const mkCtx = () => {
  const pollD = {}, stops = {};
  const c = Object.assign({}, M, {
    cmdStats: null,
    pendingOps: {},
    _cmdWaiters: null,
    _pollCmd: (id, timeoutMs, firstMs, capMs, start, stop) => { const d = mkD(); pollD[id] = d; stops[id] = stop; return d.p; },
  });
  c.__pollD = pollD;
  c.__stops = stops;
  return c;
};
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);
// node -e 含 top-level await 时按 ESM 解析(与 require 冲突): 场景体包 async IIFE
(async () => {

// 时序 1: 事件先到 —— 轮询路收摊(stop.v 置位) + waiter 被 _cancelCmdWait 清掉
let c = mkCtx();
let p = c.waitCmd("E1", 5000);
c.onCmdEvent({ cmd_id: "E1", status: "ok", wait_ms: 4, exec_ms: 2 });
let r = await p;
ok("事件先到: 结果 ok 且事件回执原样带出", r && r.ok === true && r.status === "ok");
ok("事件先到: 落败轮询路收到收摊信号(stop.v=true)", c.__stops["E1"] && c.__stops["E1"].v === true);
ok("事件先到: _cancelCmdWait 清 waiter", c._cmdWaiters instanceof Map && !c._cmdWaiters.has("E1"));

// 时序 2: 轮询先到 —— 事件路 waiter 同口径清掉, 回执 error 原样带出
c = mkCtx();
p = c.waitCmd("E2", 5000);
c.__pollD["E2"].res({ cmd_id: "E2", status: "error", error: "炸了" });
r = await p;
ok("轮询先到: error 回执原样带出", r && r.ok === false && r.error === "炸了" && r.status === "error");
ok("轮询先到: 落败轮询路 stop.v=true", c.__stops["E2"] && c.__stops["E2"].v === true);
ok("轮询先到: 事件路 waiter 已清", c._cmdWaiters instanceof Map && !c._cmdWaiters.has("E2"));

// 时序 3: 双超时(事件路 1.1s 真超时 + 轮询永不回)—— 回退 {ok:false} 且超时文案逐字
c = mkCtx();
p = c.waitCmd("E3", 1100);
r = await p;
ok("双超时: 回退 ok=false", r && r.ok === false);
ok("双超时: 超时回退文案逐字", r.error === "执行等待超时(1s), 结果以程序日志为准");
ok("双超时: waiter 表已清(超时路径自删)", c._cmdWaiters instanceof Map && !c._cmdWaiters.has("E3"));
ok("双超时: stop.v 照常置位", c.__stops["E3"] && c.__stops["E3"].v === true);
process.stdout.write(JSON.stringify({
  ok: checks.filter((x) => x[1]).length, total: checks.length,
  failed: checks.filter((x) => !x[1]).map((x) => x[0]),
}) + "\n");
})().catch((e) => { process.stderr.write(String((e && e.stack) || e) + "\n"); process.exit(1); });
"""

# R5#191: HR 悬停弹窗 hrPopData 分支矩阵 + _hrPopPlace 定位几何 --------------------
_NODE_HR_POP_PROBE = r"""
const fs = require("fs");
global.window = { innerWidth: 1000, innerHeight: 800 };
eval(fs.readFileSync(process.argv[1], "utf8"));   // overlay_fit.js: 几何单点(AQB_OVERLAY_FIT)
eval(fs.readFileSync(process.argv[2], "utf8"));   // format.js: fmtDuration/fmtSize
eval(fs.readFileSync(process.argv[3], "utf8"));   // hr.js: AQB_HR
const HM = window.AQB_HR.methods, FM = window.AQB_FORMAT.methods;
const FIT = window.AQB_OVERLAY_FIT;
const mkCtx = () => Object.assign({}, HM, FM, { hrPop: { open: false, above: false, data: null } });
const J = (v) => JSON.stringify(v);
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

// ---- hrPopData 分支矩阵 ----
let c = mkCtx();
// excluded 两态(唯一不进档位也必弹的行)
let d = c.hrPopData({ hr_excluded: true, hr_excluded_by: "tag" });
ok("excluded: lane/verdict/gauge/badge/kv 全按排除口径",
   d.lane === "excluded" && d.verdict === "已排除出 HR 管理" && d.gauge === null && d.badge === "" && J(d.kv) === "[]" && d.ended === false && d.lag === false);
ok("excluded: 依据按 hr_excluded_by 映射", d.reason === "命中 HR 排除表的标签规则");
d = c.hrPopData({ hr_excluded: true, hr_excluded_by: "zzz" });
ok("excluded: 未知来源回落通用短语", d.reason === "命中 HR 排除表");
// 未接入 / none = 不弹
ok("未接入(hr_safety 空)-> null", c.hrPopData({ hr_safety: "" }) === null);
ok("hr_safety=none -> null", c.hrPopData({ hr_safety: "none" }) === null);
// 站点已达标 + 站点数值条(在线核实, 终态)
c = mkCtx();
d = c.hrPopData({ hr_safety: "safe", hr_safety_src: "site_satisfied", hr_safety_text: "已达标",
  seeding_time: 7200, hr_req_time: 3600, hr_site_ratio: "3.5", hr_site_dl: 1073741824, hr_site_need: "", hr_site_remain: "" });
ok("site_satisfied: lane/verdict/ended", d.lane === "safe" && d.verdict === "已达标" && d.ended === true);
ok("site_satisfied: 站点轨满格自明(无角标)", d.badge === "" && d.gauge.tag === null
   && d.gauge.site && d.gauge.site.tone === "safe" && d.gauge.site.pct === 100);
ok("site_satisfied: 本地轨已达标(7200/3600)", d.gauge.seeded === "2时00分" && d.gauge.req === "1时00分" && d.gauge.pct === 100);
ok("数值条两行按站点侧值拼装(缺省字段不挤行)", J(d.kv) === J([["站点分享率", "3.50"], ["站点下载", "1.00 GiB"]]));
ok("lag: 有站点侧数据为 true", d.lag === true);
// 考察中 + need 端点(角标 = 还需 X, 站点轨画剩余占比)
c = mkCtx();
d = c.hrPopData({ hr_safety: "danger", hr_safety_src: "site_scope", hr_safety_text: "考察中",
  seeding_time: 600, hr_req_time: 3600, hr_site_need: 1800, hr_site_remain: 1800, hr_site_ratio: "", hr_site_dl: "" });
ok("考察中: ended=false + 角标「还需 30分钟」", d.ended === false && d.gauge.tag.tone === "danger" && d.gauge.tag.text === "还需 30分钟");
ok("考察中: 站点轨剩余占比 50%", d.gauge.site && d.gauge.site.tone === "danger" && d.gauge.site.pct === 50);
ok("考察中: 本地轨 600/3600 = 16.7%(未夹取)", d.gauge.pct > 16 && d.gauge.pct < 17);
ok("考察中: 无站点数值条则 kv 空, lag 靠站点轨", J(d.kv) === "[]" && d.lag === true);
// pct 夹取: need 超要求 -> 100; need 负值 -> 0
d = c.hrPopData({ hr_safety: "danger", hr_safety_src: "site_scope", seeding_time: 0, hr_req_time: 3600, hr_site_need: 7200, hr_site_remain: 0 });
ok("站点轨 pct 上夹 100(need > req)", d.gauge.site.pct === 100);
d = c.hrPopData({ hr_safety: "danger", hr_safety_src: "site_scope", seeding_time: 0, hr_req_time: 3600, hr_site_need: -5, hr_site_remain: 5 });
ok("站点轨 pct 下夹 0(need 负值)", d.gauge.site.pct === 0);
// 本地轨 pct 夹取
d = c.hrPopData({ hr_safety: "safe", hr_safety_src: "local", seeding_time: 720000, hr_req_time: 3600, hr_site_ratio: "", hr_site_dl: "" });
ok("本地轨 pct 上夹 100(seeded 远超 req)", d.gauge.pct === 100);
// 考察中无 need 端点: remain=0 -> 站点轨满格; remain!=0 -> 角标回落本地差值
d = c.hrPopData({ hr_safety: "danger", hr_safety_src: "site_scope", seeding_time: 0, hr_req_time: 3600, hr_site_need: "", hr_site_remain: 0 });
ok("考察中无 need 端点: remain=0 -> 站点轨满格(danger)", d.gauge.site && d.gauge.site.tone === "danger" && d.gauge.site.pct === 100 && d.gauge.tag === null);
d = c.hrPopData({ hr_safety: "danger", hr_safety_src: "site_scope", seeding_time: 0, hr_req_time: 3600, hr_site_need: "", hr_site_remain: 600, hr_site_ratio: "", hr_site_dl: "" });
ok("考察中无 need 端点: remain!=0 -> 角标回落本地差值(还需 1时00分)且无站点轨",
   d.gauge.tag && d.gauge.tag.text === "还需 1时00分" && d.gauge.site === null && d.lag === false);
// 本地兜底: 已超出 / 还需
d = c.hrPopData({ hr_safety: "warning", hr_safety_src: "local", seeding_time: 100, hr_req_time: 3600, hr_site_ratio: "", hr_site_dl: "" });
ok("本地兜底: 还需 58分钟(warning 有要求不收轨)", d.gauge.tag.tone === "danger" && d.gauge.tag.text === "还需 58分钟" && d.gauge.site === null && d.lag === false);
d = c.hrPopData({ hr_safety: "warning", hr_safety_src: "local", seeding_time: 4000, hr_req_time: 3600, hr_site_ratio: "", hr_site_dl: "" });
ok("本地兜底: 已超出 6分钟(safe 角标)", d.gauge.tag.tone === "safe" && d.gauge.tag.text === "已超出 6分钟");
// 终态 failed: 考核期已过角标 + 无站点轨
d = c.hrPopData({ hr_safety: "failed", hr_safety_src: "site_unsatisfied", hr_safety_text: "未达标", seeding_time: 100, hr_req_time: 3600 });
ok("failed 终态: 角标「考核期已过」+ ended=true", d.gauge.tag.tone === "failed" && d.gauge.tag.text === "考核期已过" && d.ended === true && d.gauge.site === null);
// badge 与 gauge 互斥(轨道收起换徽记的三态)
c = mkCtx();
d = c.hrPopData({ hr_safety: "safe", hr_safety_src: "site_released", seeding_time: 100, hr_req_time: 3600, hr_site_ratio: "", hr_site_dl: "" });
ok("site_released: gauge 收起换 check 徽记", d.gauge === null && d.badge === "check" && d.ended === true);
d = c.hrPopData({ hr_safety: "safe", hr_safety_src: "site_exempt", seeding_time: 100, hr_req_time: 3600 });
ok("site_exempt: 同款 check 徽记", d.gauge === null && d.badge === "check" && d.ended === true);
d = c.hrPopData({ hr_safety: "safe", hr_safety_src: "local", seeding_time: 100, hr_req_time: 0 });
ok("无时长要求(req=0): check 徽记", d.gauge === null && d.badge === "check");
// verdict 回落 + 依据原文
d = c.hrPopData({ hr_safety: "danger", hr_safety_src: "local", seeding_time: 0, hr_req_time: 3600, hr_reason: "命中 H&R 规则" });
ok("verdict 回落到 hr_safety 原值 + 依据透传", d.verdict === "danger" && d.reason === "命中 H&R 规则");

// ---- _hrPopPlace 定位几何 ----
const mkEl = () => ({ offsetWidth: 200, offsetHeight: 100, style: {}, querySelector: () => ({ style: {} }) });
const mkRect = (left, top, width, height) => ({ left, top, width, height, right: left + width, bottom: top + height });
const place = (rect) => {
  const el = mkEl();
  const ctx = mkCtx();
  ctx.hrPop.open = true;
  ctx._hrPopPlace(el, { getBoundingClientRect: () => rect });
  return { el, ctx };
};
// 上方放得下: 贴上方居中, above=true
let r = place(mkRect(400, 400, 100, 30));
ok("上方优先: top = trg.top - gap - ph, 水平居中", r.el.style.top === "290px" && r.el.style.left === "350px" && r.ctx.hrPop.above === true);
// 上方放不下翻下方
r = place(mkRect(400, 50, 100, 30));
ok("上方不足翻下方: top = trg.bottom + gap", r.el.style.top === "90px" && r.ctx.hrPop.above === false);
// 下方也放不下: 贴底钳位(innerHeight - ph - edge)
r = place(mkRect(100, 60, 100, 760));
ok("下方也放不下贴底钳位(792 - 100 = 692)", r.el.style.top === "692px");
// 横向夹取: 锚点贴左缘
r = place(mkRect(0, 400, 20, 10));
ok("横向夹取到视口边距(左缘 8px)", r.el.style.left === "8px");
// 零矩形 = 触发目标已消失: 直接收弹窗, 不写定位
{
  const el = mkEl();
  const ctx = mkCtx();
  ctx.hrPop.open = true;
  ctx._hrPopPlace(el, { getBoundingClientRect: () => mkRect(0, 0, 0, 0) });
  ok("零矩形收弹窗(open=false, 不写 style)", ctx.hrPop.open === false && !el.style.left && !el.style.top);
}
// 几何单点: hrPopPlace 用的是 AQB_OVERLAY_FIT(EDGE=8 口径)
ok("几何单点在位(EDGE=8)", FIT && FIT.EDGE === 8 && typeof FIT.clampAxis === "function");
console.log(JSON.stringify({
  ok: checks.filter((x) => x[1]).length, total: checks.length,
  failed: checks.filter((x) => !x[1]).map((x) => x[0]),
}));
"""

# R5#27: _auditScope 分类/去重/有界环 ---------------------------------------------
_NODE_SCOPE_AUDIT_PROBE = r"""
const fs = require("fs");
const warns = [];
global.console = { log: () => {}, warn: (...a) => warns.push(a.join(" ")) };
global.window = { __AQB_AUDIT_SCOPE__: true };
eval(fs.readFileSync(process.argv[1], "utf8"));
const audit = (targets, event) => window.AQB_SCOPE_AUDIT.methods._auditScope(event || "actCore:pause", targets);
const ring = () => window.__AQB_SCOPE_RING__;
const last = () => ring()[ring().length - 1];
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

// ok 载荷(无偏差不 warn)
audit({ keys: ["a"], hashes: ["h1", "h2"] });
ok("ok 载荷: kind=ok, keys/hashes 串化入环", last().kind === "ok" && last().keys.join() === "a" && last().hashes.join() === "h1,h2");
ok("ok 载荷: 不 warn", warns.length === 0);
// {groupKeys, memberHashes} 兼容形状(metaTargets 等)
audit({ groupKeys: ["g1"], memberHashes: ["h1"] }, "meta:add_tags");
ok("兼容形状: groupKeys/memberHashes 认作 keys/hashes", last().kind === "ok" && last().keys.join() === "g1" && last().event === "meta:add_tags");
// shape: 载荷不是 {keys[],hashes[]}
audit(null);
ok("null 载荷 -> shape", last().kind === "shape" && last().msg.indexOf("形状") >= 0 && last().warned === true);
audit({ keys: "a", hashes: [] });
ok("keys 非数组 -> shape", last().kind === "shape");
// shape: 非串元素(目标没走 _scopeResolve 单点)
audit({ keys: [1, ""], hashes: ["h"] });
ok("非串/空串元素 -> shape(专项 msg)", last().kind === "shape" && last().msg.indexOf("非串或空串") >= 0);
// dup: 内部重复
audit({ keys: ["a", "a"], hashes: [] });
ok("keys 内部重复 -> dup", last().kind === "dup" && last().msg.indexOf("重复") >= 0);
audit({ keys: [], hashes: ["h", "h"] });
ok("hashes 内部重复 -> dup", last().kind === "dup");
// empty: 空载荷
audit({ keys: [], hashes: [] });
ok("空载荷 -> empty", last().kind === "empty" && last().msg.indexOf("空载荷") >= 0);
// 签名去重 warn: 同一签名偏差只 warn 一次
const warnsBefore = warns.length;
audit({ keys: ["dup", "dup"], hashes: [] });
audit({ keys: ["dup", "dup"], hashes: [] });
ok("同签名偏差只 warn 一次(第二条静默入环)",
   warns.length === warnsBefore + 1 && ring().filter((r) => r.kind === "dup" && r.keys.join() === "dup,dup").length === 2
   && last().warned === undefined);
// 不同签名的同类偏差再 warn
audit({ keys: ["other", "other"], hashes: [] });
ok("不同签名再 warn", warns.length === warnsBefore + 2 && last().warned === true);
// 50 条有界环: 挤出最旧
const before = ring().length;
for (let i = 0; i < 60; i++) audit({ keys: ["k" + i], hashes: [] });
ok("有界环: 长度钉在 50", ring().length === 50);
// 挤出 = 总拍数 - 50; 环前 before 条全部被挤出后, 循环里首个存活拍 = 60 - 50
ok("有界环: 最旧被挤出(首条是循环第 11 拍)", ring()[0].keys.join() === "k" + (60 - 50));
ok("挤出的 60 拍全是 ok 不 warn", warns.length === warnsBefore + 2);
// 关态: 零记账(环不动, 不 warn)
window.__AQB_AUDIT_SCOPE__ = false;
const frozen = ring().slice();
audit({ keys: ["x"], hashes: [] });
ok("关态: O(1) 直返不碰环", JSON.stringify(ring()) === JSON.stringify(frozen) && warns.length === warnsBefore + 2);
process.stdout.write(JSON.stringify({
  ok: checks.filter((x) => x[1]).length, total: checks.length,
  failed: checks.filter((x) => !x[1]).map((x) => x[0]),
}) + "\n");
"""

# R5#19: 通知环形缓冲行为契约 ------------------------------------------------------
_NODE_ERR_HISTORY_PROBE = r"""
const fs = require("fs");
global.window = {};
// ui_feedback.js 尾部两段 IIFE 碰 DOM: 桩到"第二段 CSS.supports 直接 return、第一段挂不上真监听"的程度
global.document = {
  addEventListener: () => {}, removeEventListener: () => {},
  querySelector: () => null, querySelectorAll: () => [],
  body: { appendChild: () => {} },
  createElement: () => ({ style: {}, setAttribute: () => {}, removeAttribute: () => {}, classList: { add() {}, remove() {}, contains() { return false; } } }),
  nodeType: 1, hasAttribute: () => false, getAttribute: () => null,
};
global.MutationObserver = class { observe() {} };
global.window = { addEventListener: () => {} };
global.CSS = { supports: () => true };   // 滚轮穿透 IIFE 的门控(bare CSS 全局)
// toast 的退场定时器只记不响(退场与本电池无关)
global.setTimeout = () => 0;
eval(fs.readFileSync(process.argv[1], "utf8"));   // overlay_fit.js: ui_feedback 尾部 IIFE 顶层取 FIT.EDGE
eval(fs.readFileSync(process.argv[2], "utf8"));
const F = window.AQB_FEEDBACK.methods;
const mkCtx = () => Object.assign({}, F, {
  toasts: [], _toastSeq: 0, _errHistory: [], _errSeq: 0, _errUnread: 0,
  errPanelOpen: false, ui: "prism",
});
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

// emit 即收: error/timeout 进史, info/busy 不进
let c = mkCtx();
c.toast("炸了", "error");
ok("emit 即收: error toast 当拍进史(source=toast)", c._errHistory.length === 1 && c._errHistory[0].kind === "error" && c._errHistory[0].text === "炸了" && c._errHistory[0].source === "toast");
c.toast("普通", "info");
c.toast("普通", "warn");
ok("info/warn 不入史", c._errHistory.length === 1);
const busyId = c.toast("强制重新汇报中…", "busy", 0, { sticky: true });
ok("busy 不入史(等待中不是终态)", c._errHistory.length === 1);
ok("面板关着: 首条已计未读", c._errUnread === 1);

// settle upsert 同 id 去重: busy 结算成终态首次入史; 同 id 二次 _recordErrorToast 只覆盖不增行
c._finishToast(busyId, "error", "强制重新汇报失败: 命令未能送达");
ok("busy 结算成 error 首次入史", c._errHistory.length === 2 && c._errHistory[0].id === busyId && c._errHistory[0].text === "强制重新汇报失败: 命令未能送达");
const nBefore = c._errHistory.length;
const entry = c._errHistory.find((e) => e.id === busyId);
c._recordErrorToast(busyId, "timeout", "结算改口");
ok("同 id 二次 _recordErrorToast 只覆盖不增行(「同一条错误只留一条」)",
   c._errHistory.length === nBefore && c._errHistory.find((e) => e.id === busyId).kind === "timeout"
   && c._errHistory.find((e) => e.id === busyId).text === "结算改口" && c._errHistory.find((e) => e.id === busyId) === entry);
ok("seq 保持单调(覆盖不重排)", c._errHistory.every((e, i, a) => i === 0 || a[i - 1].seq > e.seq));

// 第 51 条挤掉最旧: unshift 新在上 + pop 最旧(已有 2 条, 补 48 条恰满 cap)
for (let i = 0; i < 48; i++) c._recordErrorToast(100 + i, "error", "e" + i);
ok("补到 50 条恰满 cap(未挤出)", c._errHistory.length === 50 && c._errHistory.some((e) => e.id === busyId));
c._recordErrorToast(999, "error", "第 51 条");
ok("第 51 条入环后长度钉在 50", c._errHistory.length === 50);
ok("最旧被挤出(首条 id=1 不在环内)", !c._errHistory.some((e) => e.id === 1));
ok("最新在上(unshift)", c._errHistory[0].id === 999);
ok("cap 边界次序(第 2 条仍存活)", c._errHistory.some((e) => e.id === busyId));

// errPanelOpen 的未读口径: 关着递增, 开着不计
c.errPanelOpen = true;
c._errUnread = 0;
c._recordErrorToast(900, "error", "面板开着");
ok("面板开着不计未读", c._errUnread === 0);
c.errPanelOpen = false;
c._recordErrorToast(901, "error", "面板关了");
ok("面板关着未读递增", c._errUnread === 1);
// 清空归零(清空钮链路的单点)
c._clearErrorHistory();
ok("清空: 历史与未读全归零", c._errHistory.length === 0 && c._errUnread === 0);
console.log(JSON.stringify({
  ok: checks.filter((x) => x[1]).length, total: checks.length,
  failed: checks.filter((x) => !x[1]).map((x) => x[0]),
}));
"""


def test_r4_cmdstats_receipt_ownership():
    """R5#233 修复回归: cmdStats 单槽归属校验 —— 旧命令迟到回执/事件/t0 不污染新命令的槽"""
    report = _run_probe(_NODE_CMDSTATS_OWNERSHIP_PROBE, _shared("commands.js"))
    _assert_battery(report, "cmdStats 归属电池")


def test_r4_set_row_icon_timer_lifecycle():
    """R5#29: setRowIcon 每 hash 定时器生命周期 —— 覆盖先清旧、ok 按 10s 存活不被 45s 兜底提前清"""
    report = _run_probe(_NODE_SET_ROW_ICON_PROBE, _shared("commands.js"))
    _assert_battery(report, "setRowIcon 定时器电池")


def test_r4_waitcmd_race_settle_three_timings():
    """R5#25: waitCmd SSE/轮询竞态三时序 —— 事件先到/轮询先到/双超时, 落败路径收摊与超时回退"""
    report = _run_probe(_NODE_WAITCMD_RACE_PROBE, _shared("commands.js"))
    _assert_battery(report, "waitCmd 竞态电池")


def test_r4_hr_pop_data_matrix_and_place():
    """R5#191: hrPopData 分支矩阵(excluded/badge-gauge 互斥/pct 夹取/lag)+ _hrPopPlace 定位几何"""
    report = _run_probe(
        _NODE_HR_POP_PROBE,
        _shared("overlay_fit.js"),
        _shared("format.js"),
        _shared("hr.js"),
    )
    _assert_battery(report, "HR 悬停弹窗电池")


def test_r4_scope_audit_classify_ring_dedup():
    """R5#27: _auditScope 五类分类 + 签名去重 warn + 50 条有界环 + 关态零记账"""
    report = _run_probe(_NODE_SCOPE_AUDIT_PROBE, _shared("scope_audit.js"))
    _assert_battery(report, "scope 审计电池")


def test_r4_err_history_ring_upsert_unread():
    """R5#19: 通知环形缓冲契约 —— emit 即收/同 id upsert 去重/第 51 条挤最旧/未读按面板开合计"""
    report = _run_probe(_NODE_ERR_HISTORY_PROBE, _shared("overlay_fit.js"), _shared("ui_feedback.js"))
    _assert_battery(report, "通知环形缓冲电池")
