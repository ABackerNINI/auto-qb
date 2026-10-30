"""tests/test_webui_optimistic_rename_alt: 乐观UI扩面(重命名乐观补丁+主备速度切预翻转)守阵与单测

计划 26-10-30-0610(§04 S5 / 决策 D9): S1 重命名乐观补丁(commit 5ac63a7e)与 S2 主备速度切
预翻转(commit e6ef9344)的静态守阵两条 + node 电池单测两组四态。e2e 两条(Playwright)不在本文件。

## 测试计划(每个测试函数一条)
- test_rename_optimistic_patch_precedes_post: 守阵一(plan §04 S5 / §07 行1): drawer.js::editRename 的 applyOptimisticPatch 调用点必须先于 POST(_editPost)、resolveOptimistic 必须在 POST 之后收口 —— 顺序倒了就是「先等回执再贴补丁」, 「点击当帧可见」整条设计作废; 另钉 patch 恰为 {name} 单键(§01 不变量: 值覆盖只盖「值来自我们」的字段)与 drawer.js 全文件 applyOptimisticPatch 调用点唯一
- test_on_truth_event_kind_injection_action_guard: 守阵二(plan §04 S1.3 / §07 行1): commands.js::onTruthEvent 的 kind 注入必须带 action 守卫 —— 只对 pause/resume 的 op 注入 kind(patch/prev/hold/ts 四写全在守卫块内), rename 等 action 的 op 保持原 patch(掺入 kind 会让 _optimisticSettled 逐键比对永远差一键, 对账判据被污染, op 挂到 8s 兜底才回滚且行名被错误弹回)
- test_rename_optimistic_four_states_node: rename 四态 node 电池(plan §04 S5, 仿 pause/resume 乐观既有用例; 无 node 静默跳过): 真跑 commands.js + drawer.js 的 editRename 全链 —— 态1 贴上(POST 发出时行上已是新名, op grey=true/hold=false)/态2 回执 ok 转 hold(值覆盖保持, 陈旧快照回到来不弹回)/态3 失败回滚(原名恢复, op 清除)/态4 快照对齐清除(op 清除且显示保持新名不弹回); 附加: 3s 无回执兜底回滚 + §07 指定回归「rename 收到 truth 事件后 patch 仍只有 name」(对照: pause op 照旧注入 kind 转 hold)
- test_alt_override_four_states_node: altOverride 四态 node 电池(plan §04 S2, 无 node 静默跳过): 真跑 dialogs.js 的 toggleAltSpeed/_altOverride* 与 sbAltOn 显示单点 —— 态1 预翻转(点击当帧 sbAltOn 已翻转且 3s 兜底武装)/态2 三路回滚(回执 error/发送失败/3s 无回执 -> 覆盖清除回落 server 值)/态3 确认清除(轮询带回一致值 -> 清除且零观感跳变; 带回旧值 -> 覆盖保留不弹回)/态4 8s 兜底清除(回执 ok 转 hold 后 8s 未确认 -> 清除; 旧 3s 兜底误触发被 needHold 守卫拦下); 另钉接线静态锚: sbAltOn override 优先 server 兜底 + polling.js statsServer 赋值后必调 _altOverrideReconcile + state.js data 声明 altOverride
- test_alt_limits_empty_gate_node: altLimits 非空闸 node 电池(issue 26-10-30-0622, 无 node 静默跳过): 真跑 dialogs.js 的 submitAltLimits —— A /api/speed/mode 读失败窗口(altCurrent=null 两框回空)整组跳过零 POST / B 任一框为空同判(与 speedOvReady 同形) / C 未改动不下发 / D 改动照常 POST 载荷正确 / E 显式 0=不限速不拦
"""

import json
import os
import re
import shutil
import subprocess

from webui_helpers import STATIC_ROOT

# node 电池报告失败行的前缀(与 test_webui_static_dom_panel 同口径: failed 数组逐条列名)
_NODE_REPORT_HINT = "node 电池跑挂(源码语法/探针环境问题): {stderr}"
_NODE_FAIL_HINT = "{title} 电池 {ok}/{total} 过, 失败: {failed}"


def _shared_path(name):
    return os.path.join(STATIC_ROOT, "shared", name)


def _run_node_probe(probe, *js_paths):
    """跑 node 电池并解析报告(无 node 静默跳过返回 None —— 与 static_dom_panel 同口径)。"""
    node = shutil.which("node")
    if not node:
        return None
    proc = subprocess.run(
        [node, "-e", probe, *js_paths],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0, _NODE_REPORT_HINT.format(stderr=proc.stderr.strip())
    report = json.loads(proc.stdout.strip().splitlines()[-1])
    assert report["failed"] == [], _NODE_FAIL_HINT.format(
        title=report.get("title", ""), ok=report["ok"], total=report["total"], failed=report["failed"]
    )
    return report


def test_rename_optimistic_patch_precedes_post():
    """守阵一(plan 26-10-30-0610 §04 S5): applyOptimisticPatch 调用点必须先于 POST

    「点击 -> 行上新名当帧可见」的设计前提是补丁在 POST 之前贴上(drawer.js::editRename);
    若有人把补丁挪到 _editPost 之后(或改成等回执再贴), 观感退回修复前(可见 ~1.7s),
    本守阵用源码序钉死: 贴补丁 < POST < resolveOptimistic 收口。
    同时钉 patch 形状 = {name} 单键(§01 不变量「值覆盖只盖值来自我们的字段」)与
    drawer.js 全文件调用点唯一(第二处消费者出现时应显式扩本守阵, 不许静默长出来)。
    """
    js = open(_shared_path("drawer.js"), encoding="utf-8").read()
    m = re.search(r"async editRename\(h = \"\"\)\s*\{(.*?)\n    \},", js, re.S)
    assert m, "drawer.js 找不到 editRename(改名或挪走了? 同步本守阵)"
    body = m.group(1)
    i_apply = body.find('this.applyOptimisticPatch([hash], "rename", { name: res.name })')
    i_post = body.find('this._editPost(hash, "rename"')
    i_resolve = body.find("this.resolveOptimistic([hash], ok)")
    assert i_apply >= 0, ("editRename 缺乐观补丁调用(退回「只 toast 等下轮 sync」? "
                          "行上新名可见会从回执级劣化到 ~1.7s, 同步本守阵或回滚设计变更)")
    assert i_post >= 0, "editRename 缺 _editPost(rename) 投递调用(编辑链断了? 同步本守阵)"
    assert i_resolve >= 0, "editRename 缺 resolveOptimistic 收口(ok 转 hold / 失败回滚断链)"
    assert i_apply < i_post, (
        "applyOptimisticPatch 必须先于 POST(顺序倒了 = 先等回执再贴补丁, "
        "「点击当帧可见」作废) —— 见 plan 26-10-30-0610 §04 S1.2"
    )
    assert i_post < i_resolve, "resolveOptimistic 必须在 _editPost 之后(回执结果驱动 hold/回滚)"
    # patch 形状: 恰为 {name} 单键 —— 多盖字段违反 §01 不变量(值覆盖只盖「值来自我们」的字段)
    assert body.count('applyOptimisticPatch([hash], "rename", { name: res.name })'
                     ) == 1, ("rename 乐观补丁必须是 {name} 单键(多盖的字段在失败回滚/对账时会盖到不属于本次命令的显示)")
    # 调用点唯一: drawer.js 里 applyOptimisticPatch 只允许 editRename 这一处
    assert js.count("this.applyOptimisticPatch("
                   ) == 1, ("drawer.js 出现第二个 applyOptimisticPatch 调用点(新消费者应显式扩本守阵并核对"
                            "「值来自我们」不变量, 不许静默长出来)")


def test_on_truth_event_kind_injection_action_guard():
    """守阵二(plan 26-10-30-0610 §04 S1.3 / §07 行1): onTruthEvent 的 kind 注入必须带 action 守卫

    kind 注入只允许对 pause/resume 的 op —— 它们的真值是 kind, 注入后走 _optimisticSettled
    的专用谓词; rename 的真值是 **name**, 掺入 kind 会让通用分支的逐键比对永远差一键
    (对账判据被污染: op 挂到 8s 兜底才回滚, 行名被错误弹回旧名)。
    本守阵钉: 守卫字面量在、注入四写(patch/prev/hold/ts)全在守卫块内、注入语句全文件仅此一处。
    行为面回归在 test_rename_optimistic_four_states_node 的「守卫」段。
    """
    js = open(_shared_path("commands.js"), encoding="utf-8").read()
    m = re.search(r"onTruthEvent\(rec\)\s*\{(.*?)\n    \},", js, re.S)
    assert m, "commands.js 找不到 onTruthEvent(改名或挪走了? 同步本守阵)"
    body = m.group(1)
    guard = 'if (op && (op.action === "pause" || op.action === "resume")) {'
    assert guard in body, (
        "onTruthEvent 的 kind 注入缺 action 守卫(rename 等 action 的 op 会被掺入 kind, "
        "污染 _optimisticSettled 的逐键比对) —— 见 plan 26-10-30-0610 §04 S1.3"
    )
    gm = re.search(re.escape(guard) + r"\n(.*?)\n        \}", body, re.S)
    assert gm, "onTruthEvent 守卫块形状变了(提取失败? 同步本守阵)"
    inner = gm.group(1)
    for stmt in (
        "op.patch = { ...op.patch, kind: t.kind };",
        "op.prev = { ...op.prev, kind: t.kind };",
        "op.hold = true;",
        "op.ts = now;",
    ):
        assert stmt in inner, f"kind 注入四写缺「{stmt.strip()}」(必须全在 pause/resume 守卫块内)"
    # 注入语句在 onTruthEvent 里只出现一次(守卫块外不得再有第二处无条件注入)
    assert body.count("op.patch = { ...op.patch, kind: t.kind };"
                     ) == 1, ("onTruthEvent 出现第二处 kind 注入(守卫被绕开? 所有注入必须收敛进 pause/resume 守卫块)")


_RENAME_NODE_PROBE = r"""
const fs = require("fs");
global.window = {};
eval(fs.readFileSync(process.argv[1], "utf8"));   // commands.js(乐观四件套)
eval(fs.readFileSync(process.argv[2], "utf8"));   // drawer.js(editRename 全链)
const CM = window.AQB_COMMANDS.methods;
const DM = window.AQB_DRAWER.methods;
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);
const flush = () => new Promise((r) => setImmediate(r));

/* 桩组件: 真方法(commands 全量 + drawer 的 editRename/_editPost) + 桩 api/waitCmd/编辑原语。
 * api 桩记录「POST 发出那一刻」行上的名字 —— 它是「补丁先于 POST」的行为级判据。 */
const mkCtx = (rows, waitImpl) => {
  const ctx = {
    torrents: rows.map((r) => ({ ...r })),
    singles: [],
    groups: [],
    pendingOps: {},
    truthSnapshot: null,
    drawer: { open: true, hash: "H1", detail: { name: "旧名" } },
    postSeenName: null,
  };
  Object.assign(ctx, CM);
  ctx.editRename = DM.editRename;
  ctx._editPost = DM._editPost;
  ctx.toast = () => {};
  ctx.api = async () => { ctx.postSeenName = ctx.torrents[0].name; return { cmd_id: "c1" }; };
  ctx.waitCmd = waitImpl;
  ctx._fetchDrawerDetail = async () => {};
  ctx._editTargetHash = (h) => h || "H1";
  ctx._editDetail = async () => ({ name: "旧名" });
  ctx._openModal = async () => ({ name: "新名" });
  return ctx;
};

(async () => {
  /* ---- 态1: 贴上(点击后行名立变, 补丁先于 POST) ---------------------------------- */
  let holdResolve;
  const c1 = mkCtx([{ hash: "H1", name: "旧名", kind: "downloading" }],
    () => new Promise((res) => { holdResolve = res; }));
  const p1 = c1.editRename();
  await flush(); await flush();   // _editDetail + _openModal 的微任务之后、回执之前
  ok("态1: 对话框确认后 POST 发出前行上已是新名(补丁先于 POST, 行为级)", c1.postSeenName === "新名");
  ok("态1: 行名当帧更新", c1.torrents[0].name === "新名");
  ok("态1: 抽屉 detail 同步新名(D3 覆盖面)", c1.drawer.detail.name === "新名");
  const op1 = c1.pendingOps["H1"];
  ok("态1: op 注册 grey=true hold=false action=rename patch={name}",
    !!op1 && op1.grey === true && op1.hold === false && op1.action === "rename"
    && JSON.stringify(Object.keys(op1.patch)) === '["name"]' && op1.prev.name === "旧名");
  holdResolve({ ok: true });
  await p1;

  /* ---- 态2: 回执 ok 转 hold(值覆盖保持, 防弹回) ---------------------------------- */
  const op2 = c1.pendingOps["H1"];
  ok("态2: 回执 ok 后 grey=false hold=true(压暗结束, 值覆盖转入保持)",
    !!op2 && op2.grey === false && op2.hold === true);
  ok("态2: 行名保持新名", c1.torrents[0].name === "新名");
  c1.torrents[0].name = "旧名";   // 模拟陈旧快照: 整表替换带回命令前旧值
  c1.reapplyPending();
  ok("态2: 陈旧轮询带回旧名被补丁盖回(hold 防弹回)",
    c1.torrents[0].name === "新名" && !!c1.pendingOps["H1"]);

  /* ---- 态3: 失败回滚(原名恢复, 不留假状态) --------------------------------------- */
  const c3 = mkCtx([{ hash: "H1", name: "旧名", kind: "downloading" }],
    async () => ({ ok: false, error: "qB 拒绝" }));
  await c3.editRename();
  ok("态3: 失败回滚原名", c3.torrents[0].name === "旧名");
  ok("态3: op 已清除(无残留 pending)", !c3.pendingOps["H1"]);

  /* ---- 态4: 快照对齐清除(清除后显示保持, 不弹回) --------------------------------- */
  const c4 = mkCtx([{ hash: "H1", name: "旧名", kind: "downloading" }], async () => ({ ok: true }));
  await c4.editRename();
  c4._snapshotTruth({ torrents: [{ hash: "H1", name: "新名" }], singles: [], groups: [] });
  c4.reapplyPending();
  ok("态4: 快照 name 对齐后 op 清除", !c4.pendingOps["H1"]);
  ok("态4: 清除后行名保持新名(不弹回)", c4.torrents[0].name === "新名");
  /* 反向: 快照带回的还是旧名(服务端尚未反映) -> 不算对齐, op 继续保持 */
  const c4b = mkCtx([{ hash: "H1", name: "旧名", kind: "downloading" }], async () => ({ ok: true }));
  await c4b.editRename();
  c4b._snapshotTruth({ torrents: [{ hash: "H1", name: "旧名" }], singles: [], groups: [] });
  c4b.reapplyPending();
  ok("态4 反向: 快照未对齐 -> op 保持且补丁继续盖住", !!c4b.pendingOps["H1"] && c4b.torrents[0].name === "新名");

  /* ---- 附加: 3s 无回执兜底回滚(验收口径「3s 无回执回原名」) ---------------------- */
  const c5 = mkCtx([{ hash: "H1", name: "旧名", kind: "downloading" }], () => new Promise(() => {}));
  c5.editRename();   // 回执永不到
  await flush(); await flush();
  ok("兜底前置: 补丁已贴上且在飞", c5.torrents[0].name === "新名" && !!c5.pendingOps["H1"]);
  c5.pendingOps["H1"].ts = Date.now() - 3500;   // 快进 3s(改 op.ts, 不用假时钟)
  c5._expirePending();
  ok("3s 无回执: 兜底回滚原名且清 op", c5.torrents[0].name === "旧名" && !c5.pendingOps["H1"]);

  /* ---- 守卫回归(plan §07 行1): rename 收到 truth 事件后 patch 仍只有 name -------- */
  const c6 = mkCtx([{ hash: "H1", name: "旧名", kind: "downloading" }], async () => ({ ok: true }));
  await c6.editRename();
  const ts6 = c6.pendingOps["H1"].ts;
  c6.onTruthEvent({ truth: { H1: { kind: "paused" } } });
  const op6 = c6.pendingOps["H1"];
  ok("守卫: rename op 收到 truth 后 patch 键集仍恰为 name",
    !!op6 && JSON.stringify(Object.keys(op6.patch)) === '["name"]' && op6.patch.name === "新名");
  ok("守卫: rename op 未被注入 kind(prev 无 kind)/期限未重算(hold 保持回执链的 true)",
    !!op6 && op6.ts === ts6 && !("kind" in op6.patch) && !("kind" in op6.prev) && op6.hold === true);
  ok("守卫: 行上真值 kind 照落(对 rename 无害)", c6.torrents[0].kind === "paused");
  /* 对照: pause 的 op 必须照旧注入 kind 并转 hold(守卫只放行 pause/resume, 不许误伤既有) */
  const c7 = mkCtx([{ hash: "H2", name: "x", kind: "downloading", progress: 0.5 }], async () => ({ ok: true }));
  c7.applyOptimistic(["H2"], "pause");
  c7.onTruthEvent({ truth: { H2: { kind: "paused" } } });
  const op7 = c7.pendingOps["H2"];
  ok("对照: pause op 注入 kind 且转 hold", !!op7 && op7.patch.kind === "paused" && op7.hold === true);

  process.stdout.write(JSON.stringify({
    title: "rename四态",
    ok: checks.filter((c) => c[1]).length,
    total: checks.length,
    failed: checks.filter((c) => !c[1]).map((c) => c[0]),
  }) + "\n");
})().catch((e) => { console.error(e && e.stack || e); process.exit(1); });
"""

_ALT_NODE_PROBE = r"""
const fs = require("fs");
/* 假时钟: dialogs.js 的 _altOverrideArm 走全局 setTimeout/clearTimeout —— 先截获再换桩,
 * 定时器进表不真等, fire(ms) 手动触发; 探针自身的等待用 setImmediate/setTimeout 早先捕获的原件。 */
const realST = globalThis.setTimeout;
const timers = [];
let seq = 1;
globalThis.setTimeout = (fn, ms) => { const id = seq++; timers.push({ id, fn, ms: ms || 0 }); return id; };
globalThis.clearTimeout = (id) => {
  const i = timers.findIndex((t) => t.id === id);
  if (i >= 0) timers.splice(i, 1);
};
const armed = (ms) => timers.some((t) => t.ms === ms);
const fire = (ms) => {
  const due = timers.filter((t) => t.ms === ms);
  for (const t of due) { timers.splice(timers.indexOf(t), 1); t.fn(); }
  return due.length;
};
const flush = () => new Promise((r) => setImmediate(r));

globalThis.window = {};
eval(fs.readFileSync(process.argv[1], "utf8"));   // dialogs.js(toggleAltSpeed/_altOverride*/sbAltOn/_postWaitCmd)
const DG = window.AQB_DIALOGS;
const D = DG.methods;
const sbAltOn = DG.computed.sbAltOn;   // 显示单点(computed, call(ctx) 取值)
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

const mkCtx = (serverOn, apiImpl, waitImpl) => {
  const ctx = {
    altToggling: false,
    altOverride: null,
    _altOverrideTimer: null,
    statsServer: { use_alt_speed_limits: serverOn },
  };
  Object.assign(ctx, D);
  ctx.api = apiImpl;
  ctx.waitCmd = waitImpl;
  ctx.toast = () => {};
  ctx._finishToast = () => {};
  return ctx;
};

(async () => {
  /* ---- 态1: 预翻转(点击当帧高亮翻转, 0ms 级) ------------------------------------ */
  const c1 = mkCtx(false, () => new Promise(() => {}), async () => ({ ok: true }));  // 回执永不到
  D.toggleAltSpeed.call(c1);   // 不 await: 只取点击当帧
  ok("态1: 点击当帧 altOverride 预翻转(value=true prev=false hold=false)",
    !!c1.altOverride && c1.altOverride.value === true && c1.altOverride.prev === false && c1.altOverride.hold === false);
  ok("态1: 点击当帧 sbAltOn 已翻转(读 override, 显示单点)", sbAltOn.call(c1) === true);
  ok("态1: 3s 无回执兜底已武装", armed(3000) === true);
  const ovRef = c1.altOverride;
  D.toggleAltSpeed.call(c1);   // 防重入: altToggling 在飞时第二次点击必须零副作用
  ok("态1: 防重入(在飞中再点不换覆盖)", c1.altOverride === ovRef && timers.length === 1);

  /* ---- 态2: 三路回滚(回落 server 值, 绝不留假状态) ------------------------------ */
  timers.length = 0;
  const c2 = mkCtx(false, async () => ({ cmd_id: "c1" }), async () => ({ ok: false, error: "qB 拒绝" }));
  await D.toggleAltSpeed.call(c2);
  ok("态2a: 回执 error -> 覆盖清除回落 server 值(false)",
    c2.altOverride === null && sbAltOn.call(c2) === false && timers.length === 0);
  const c3 = mkCtx(false, async () => { throw new Error("net down"); }, async () => ({ ok: true }));
  await D.toggleAltSpeed.call(c3);
  ok("态2b: 发送失败 -> 覆盖清除回落 server 值(false)",
    c3.altOverride === null && sbAltOn.call(c3) === false);
  const c4 = mkCtx(true, () => new Promise(() => {}), async () => ({ ok: true }));
  D.toggleAltSpeed.call(c4);   // 回执永不到: 3s 兜底负责
  ok("态2c 前置: 自 server=true 起预翻转(value=false)", c4.altOverride && c4.altOverride.value === false);
  const fired3 = fire(3000);
  ok("态2c: 3s 无回执 -> 兜底清除回落 server 值(true)",
    fired3 === 1 && c4.altOverride === null && sbAltOn.call(c4) === true);

  /* ---- 态3: 确认清除(轮询对账, 清除不弹回) -------------------------------------- */
  timers.length = 0;
  let resolveApi5;
  const c5 = mkCtx(false, () => new Promise((res) => { resolveApi5 = res; }), async () => ({ ok: true }));
  const p5 = D.toggleAltSpeed.call(c5);
  await flush();
  resolveApi5({ cmd_id: "c1" });
  await p5;
  ok("态3 前置: 回执 ok 转 hold, 8s 兜底武装且 3s 已撤",
    !!c5.altOverride && c5.altOverride.hold === true && armed(8000) && !armed(3000));
  c5.statsServer = { use_alt_speed_limits: false };   // 轮询带回命令前旧值
  D._altOverrideReconcile.call(c5);                   // polling.js statsServer 赋值处的对账单点
  ok("态3: 轮询带回旧值 -> 覆盖保留, 显示仍为新值(不弹回)",
    !!c5.altOverride && sbAltOn.call(c5) === true);
  c5.statsServer = { use_alt_speed_limits: true };    // 轮询带回一致值
  D._altOverrideReconcile.call(c5);
  ok("态3: 轮询带回一致值 -> 覆盖清除且显示保持(零观感跳变)",
    c5.altOverride === null && sbAltOn.call(c5) === true && timers.length === 0);

  /* ---- 态4: 8s 兜底清除(hold 中未确认 -> 回落 server 值) ------------------------ */
  timers.length = 0;
  let resolveApi6;
  const c6 = mkCtx(true, () => new Promise((res) => { resolveApi6 = res; }), async () => ({ ok: true }));
  const p6 = D.toggleAltSpeed.call(c6);
  await flush();
  resolveApi6({ cmd_id: "c1" });
  await p6;
  ok("态4 前置: hold 中且 8s 兜底在", !!c6.altOverride && c6.altOverride.hold === true && armed(8000));
  const fired8 = fire(8000);
  ok("态4: 8s 未确认 -> 兜底清除回落 server 值(true)",
    fired8 === 1 && c6.altOverride === null && sbAltOn.call(c6) === true);
  /* needHold 守卫: 状态已推进(hold)后旧 3s 兜底误触发不得摘覆盖 */
  timers.length = 0;
  let resolveApi7;
  const c7 = mkCtx(false, () => new Promise((res) => { resolveApi7 = res; }), async () => ({ ok: true }));
  const p7 = D.toggleAltSpeed.call(c7);
  await flush();
  const stale3 = timers.find((t) => t.ms === 3000);
  resolveApi7({ cmd_id: "c1" });
  await p7;
  ok("needHold 前置: 回执后 3s 旧兜底已被重排撤下", !armed(3000) && !!c7.altOverride && c7.altOverride.hold === true);
  if (stale3) stale3.fn();
  ok("needHold: 旧 3s 兜底误触发被拦下(覆盖仍在 hold)", !!c7.altOverride && c7.altOverride.hold === true);

  process.stdout.write(JSON.stringify({
    title: "altOverride四态",
    ok: checks.filter((c) => c[1]).length,
    total: checks.length,
    failed: checks.filter((c) => !c[1]).map((c) => c[0]),
  }) + "\n");
})().catch((e) => { console.error(e && e.stack || e); process.exit(1); });
"""


def test_rename_optimistic_four_states_node():
    """rename 四态 node 电池: 真跑 commands.js + drawer.js 的 editRename 全链(plan §04 S5)

    四态 = 贴上 / 回执 hold / 失败回滚 / 快照对齐清除, 另带 3s 兜底与 §07 的 kind 守卫回归。
    桩面最小化: api/waitCmd/_editDetail/_openModal/toast 六个原语, 其余全是被测真方法
    (applyOptimisticPatch/resolveOptimistic/reapplyPending/_snapshotTruth/_optimisticSettled/
    _expirePending/onTruthEvent/_forEachRow 与 drawer.js 的 editRename/_editPost 原体)。
    无 node 静默跳过(与 test_webui_static_dom_panel 同口径)。
    """
    _run_node_probe(_RENAME_NODE_PROBE, _shared_path("commands.js"), _shared_path("drawer.js"))


def test_alt_override_four_states_node():
    """altOverride 四态 node 电池: 真跑 dialogs.js 的 toggleAltSpeed/_altOverride*(plan §04 S2)

    四态 = 预翻转 / 回滚(回执 error + 发送失败 + 3s 无回执三路) / 确认清除 / 8s 兜底清除。
    定时器走假时钟(截获全局 setTimeout 进表手动触发), POST/waitCmd 走最小桩, 其余真方法。
    静态锚一并钉: sbAltOn「override 优先, server 兜底」、polling.js statsServer 赋值后必调
    _altOverrideReconcile(对账点单点)、state.js data 声明 altOverride。无 node 静默跳过。
    """
    # 静态锚: 显示单点 override 优先(摘覆盖后自动回落 server 值, 两态间零观感跳变的前提)
    dialogs = open(_shared_path("dialogs.js"), encoding="utf-8").read()
    m = re.search(r"sbAltOn\(\)\s*\{\n(.*?)\n    \},", dialogs, re.S)
    assert m, "dialogs.js 找不到 sbAltOn(显示单点, 移动了就同步本守阵)"
    assert "if (this.altOverride) return !!this.altOverride.value;" in m.group(1), (
        "sbAltOn 缺 override 优先分支(预翻转当帧可见与确认清除不弹回都靠它)"
    )
    # 静态锚: 对账点单点 —— statsServer 赋值后必须立即调 _altOverrideReconcile(polling.js)
    polling = open(_shared_path("polling.js"), encoding="utf-8").read()
    i_assign = polling.find("this.statsServer = state.status.server || null;")
    i_recon = polling.find("this._altOverrideReconcile();")
    assert i_assign >= 0 and i_recon > i_assign, (
        "polling.js 缺 statsServer 赋值后的 _altOverrideReconcile 对账点"
        "(server_state 是 use_alt_speed_limits 唯一确认通道, 挪走/漏调即预翻转永不确认)"
    )
    assert polling.count("this._altOverrideReconcile()"
                        ) == 1, ("polling.js 出现第二个 _altOverrideReconcile 调用点(对账点必须单点在 statsServer 赋值处)")
    # 静态锚: data 声明 altOverride(形 { value, prev, ts, hold } | null)
    state = open(_shared_path("state.js"), encoding="utf-8").read()
    assert re.search(r"altOverride:\s*null,", state), "state.js data 缺 altOverride 声明(覆盖态没有落点)"

    _run_node_probe(_ALT_NODE_PROBE, _shared_path("dialogs.js"))


_ALT_LIMITS_PROBE = r"""
const fs = require("fs");
globalThis.window = {};
eval(fs.readFileSync(process.argv[1], "utf8"));   // dialogs.js(submitAltLimits/_postWaitCmd)
const D = window.AQB_DIALOGS.methods;
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);

const mkCtx = (altCurrent, up, down) => {
  const posts = [];
  const ctx = {
    speedAlt: { up, down, busy: false },
    speedMode: { altCurrent },
  };
  Object.assign(ctx, D);
  ctx.api = async (url, opts) => { posts.push({ url, body: JSON.parse(opts.body) }); return { cmd_id: "c1" }; };
  ctx.waitCmd = async () => ({ ok: true });
  ctx.toast = () => {};
  ctx._finishToast = () => {};
  ctx.fmtLimit = () => "";   // okMsg 模板串构造时即取值, 桩成空不影响载荷断言
  return { ctx, posts };
};

(async () => {
  /* A(issue 26-10-30-0622 修复目标): /api/speed/mode 读失败窗口 altCurrent=null, _fillSpeedFields
   * 两框回空, 用户只填主速点「应用」—— 整组必须跳过(返回 true 不挡主速), 零 POST。 */
  const { ctx: cA, posts: pA } = mkCtx(null, "", "");
  ok("A: 读失败窗口两框全空 -> 整组跳过(返回 true)", await D.submitAltLimits.call(cA) === true);
  ok("A: 零 POST 且 busy 已复位", pA.length === 0 && cA.speedAlt.busy === false);

  /* B: 任一框为空同判(与 speedOvReady 同形的非空闸) */
  const { ctx: cB, posts: pB } = mkCtx({ upload_limit: 50, download_limit: 60 }, "", "60");
  ok("B: 任一框为空 -> 整组跳过", await D.submitAltLimits.call(cB) === true && pB.length === 0);

  /* C: 未改动不下发(既有承诺, 闸不得破坏它) */
  const { ctx: cC, posts: pC } = mkCtx({ upload_limit: 50, download_limit: 60 }, "50", "60");
  ok("C: 未改动 -> 不下发", await D.submitAltLimits.call(cC) === true && pC.length === 0);

  /* D: 改动照常下发, 载荷数值正确 */
  const { ctx: cD, posts: pD } = mkCtx({ upload_limit: 50, download_limit: 60 }, "50", "70");
  ok("D: 改动 -> POST /api/speed/alt 载荷正确", await D.submitAltLimits.call(cD) === true &&
    pD.length === 1 && pD[0].url === "/api/speed/alt" &&
    pD[0].body.upload_kib === 50 && pD[0].body.download_kib === 70);

  /* E: 显式 0 = 不限速照常下发(非空闸只拦空串, 不拦 0) */
  const { ctx: cE, posts: pE } = mkCtx({ upload_limit: 50, download_limit: 60 }, "0", "60");
  ok("E: 显式 0(不限速)照常下发", await D.submitAltLimits.call(cE) === true &&
    pE.length === 1 && pE[0].body.upload_kib === 0 && pE[0].body.download_kib === 60);

  process.stdout.write(JSON.stringify({
    title: "altLimits空闸",
    ok: checks.filter((c) => c[1]).length,
    total: checks.length,
    failed: checks.filter((c) => !c[1]).map((c) => c[0]),
  }) + "\n");
})().catch((e) => { console.error(e && e.stack || e); process.exit(1); });
"""


def test_alt_limits_empty_gate_node():
    """altLimits 非空闸 node 电池(issue 26-10-30-0622): 真跑 dialogs.js 的 submitAltLimits

    五案: A /api/speed/mode 读失败窗口(altCurrent=null 两框回空)整组跳过零 POST —— 修复目标,
    闸前 Number("")||0=0 会把备用限速静默写成 0/0(不限速); B 任一框为空同判(与 speedOvReady
    同形); C 未改动不下发(既有承诺不破); D 改动照常 POST 载荷正确; E 显式 0=不限速不拦。
    api/waitCmd/toast 走最小桩, 其余真方法。无 node 静默跳过(与本文件既有电池同口径)。
    """
    _run_node_probe(_ALT_LIMITS_PROBE, _shared_path("dialogs.js"))
