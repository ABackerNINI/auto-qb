"""tests/test_webui_drawer_fileprio_optimistic: 抽屉文件优先级乐观写补丁(W6a)守阵与 node 电池

计划 26-11-02-0351 §06 拍板: W6a(乐观优先级)= 实施; W6b(payload 裁剪)= Dropped。
`drawer.files` 不在 commands.js::_forEachRow 覆盖的 torrents/singles/groups 三数组内,
既有 applyOptimisticPatch/pendingOps 管不到它 —— 本补丁在 drawer.js 单点新增, 必须先写
后发 POST, 且失败与等待超时两条出口都要回滚并静默重拉(最终态 == 整表重拉)。

## 测试计划(每个测试函数一条)
- test_w6a_static_optimistic_write_precedes_post: 守阵: setFilePriority 只经 _drawerFilePriority
  投递; 乐观写(row.priority = priority)必须早于 api POST; waitCmd 必须带 10s 超时; 失败分支
  与 catch 分支都必须调 _drawerFileRollback 并 refresh(静默重拉); 仓库既有 rename 的
  applyOptimisticPatch 调用点不被本补丁改动
- test_w6a_drawer_fileprio_states_node: node 电池(无 node 静默跳过): 成功(写入先于 POST +
  回执后重拉收口)/ 回执失败回滚 / 等待超时回滚 / 重叠点击不回滚后一次的值 / 同值重复点击
  失败后仍回到最后真值(幂等)
"""

import json
import os
import re
import shutil
import subprocess

from webui_helpers import STATIC_ROOT


def _shared_path(name):
    return os.path.join(STATIC_ROOT, "shared", name)


def _run_node_probe(probe, *js_paths):
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
    assert proc.returncode == 0, f"node 电池跑挂(源码语法/探针环境问题): {proc.stderr.strip()}"
    report = json.loads(proc.stdout.strip().splitlines()[-1])
    assert report["failed"] == [], (
        f"{report.get('title', '')} 电池 {report['ok']}/{report['total']} 过, 失败: {report['failed']}"
    )
    return report


def test_w6a_static_optimistic_write_precedes_post():
    """守阵: 乐观写先于 POST + 两条回滚出口 + 收口重拉(plan 26-11-02-0351 §06 W6a)

    顺序倒了 = 先等回执再贴补丁, 「点击当帧可见」整条设计作废; 少任一回滚出口 =
    徽章停在假值(与整表重拉不一致)。另钉 rename 既有 applyOptimisticPatch 消费点不被本补丁
    扩成第二处(drawer.files 不属于它的覆盖面, 走独立通道是本计划的明确取舍)。
    """
    js = open(_shared_path("drawer.js"), encoding="utf-8").read()

    m = re.search(r"async _drawerFilePriority\(hash, indices, priority, okText\)\s*\{(.*?)\n    \},", js, re.S)
    assert m, "drawer.js 找不到 _drawerFilePriority(改名或挪走了? 同步本守阵)"
    body = m.group(1)

    i_write = body.find("row.priority = priority;")
    i_post = body.find("this.api(`/api/torrents/${hash}/files/priority`")
    assert i_write >= 0, "缺乐观写入 row.priority = priority(徽章不会当帧可见)"
    assert i_post >= 0, "缺 files/priority POST 投递"
    assert i_write < i_post, "乐观写必须先于 POST(顺序倒了 = 先等回执再贴补丁)"

    assert "this.waitCmd(resp.cmd_id, 10000)" in body, "优先级命令必须带 10s 超时(超时回滚出口的前提)"
    assert "/执行等待超时/.test(String(r.error || \"\"))" in body, "缺等待超时的显式判别"
    assert body.count("this._drawerFileRollback(hash, snap)") == 2, ("回滚出口必须两条(回执失败 + 发送失败), 各调一次 _drawerFileRollback")
    i_nonok = body.find("const timeout = /执行等待超时/")
    i_nonok_rollback = body.find("this._drawerFileRollback(hash, snap)", i_nonok)
    i_catch = body.find("} catch (e) {")
    i_catch_rollback = body.find("this._drawerFileRollback(hash, snap)", i_catch)
    assert i_nonok >= 0 and i_nonok_rollback > i_nonok, "失败/超时分支缺回滚"
    assert i_catch >= 0 and i_catch_rollback > i_catch, "发送失败 catch 分支缺回滚"
    assert "this._fetchDrawerFiles(true)" in body, "回滚/成功后必须静默重拉 files(最终态 == 整表重拉)"

    # setFilePriority 只经本通道投递(不再直连 _editPost, 否则乐观写不会发生)
    sp = re.search(r"async setFilePriority\(p, indices = null\)\s*\{(.*?)\n    \},", js, re.S)
    assert sp, "drawer.js 找不到 setFilePriority"
    assert "this._drawerFilePriority(hash, idx, p, okText)" in sp.group(1), (
        "setFilePriority 未走 _drawerFilePriority(乐观写链断了)"
    )
    assert "_editPost(hash, \"files/priority\"" not in sp.group(1), ("setFilePriority 不得绕过乐观通道直连 _editPost")

    # 既有 rename 乐观补丁消费点保持唯一(本补丁走独立通道, 不扩 applyOptimisticPatch)
    assert js.count("this.applyOptimisticPatch("
                   ) == 1, ("drawer.js 出现第二个 applyOptimisticPatch 调用点(抽屉 files 不属于它的覆盖面, 应走独立通道)")


_W6A_NODE_PROBE = r"""
const fs = require("fs");
global.window = {
  AQB_DRAWER_TPL_REG: {
    helpers: { prioText: (p, s) => ({ 0: "跳过", 1: "普通", 6: "高", 7: "最高" }[p] || s) },
  },
};
eval(fs.readFileSync(process.argv[1], "utf8"));   // drawer.js
const DM = window.AQB_DRAWER.methods;
const checks = [];
const ok = (name, cond) => checks.push([name, !!cond]);
const flush = async (n = 2) => { for (let i = 0; i < n; i++) await Promise.resolve(); };

/* 桩: 真方法(setFilePriority/_drawerFilePriority/_drawerFileRollback) + 桩 api/waitCmd/toast/
 * _fetchDrawerFiles(模拟 GET 真值)/_fetchDrawerDetail。api 桩记录「POST 发出那一刻」的 files,
 * 它是「乐观写先于 POST」的行为级判据。 */
const mkCtx = (prios, waitImpl, applyOnPost = false) => {
  const ctx = {
    drawer: { open: true, hash: "H1", files: prios.map((p) => ({ priority: p })) },
    filePrio: { visible: true, index: 0 },
    serverPrios: prios.slice(),
    posts: [],
    postsSeen: [],
    refreshes: [],
    toasts: [],
    apiCalls: 0,
  };
  Object.assign(ctx, DM);
  ctx.toast = (msg, kind) => ctx.toasts.push({ msg, kind });
  ctx.api = async (url, opts) => {
    const body = JSON.parse(opts.body);
    ctx.apiCalls += 1;
    ctx.posts.push(body);
    ctx.postsSeen.push(ctx.drawer.files.map((r) => r.priority));
    if (applyOnPost) for (const i of body.indices) ctx.serverPrios[i] = body.priority;
    return { cmd_id: "c" + ctx.apiCalls };
  };
  ctx.waitCmd = waitImpl;
  ctx._fetchDrawerFiles = (silent) => {
    ctx.refreshes.push(silent);
    ctx.drawer.files = ctx.serverPrios.map((p) => ({ priority: p }));
  };
  ctx._fetchDrawerDetail = () => {};
  return ctx;
};

(async () => {
  /* ---- 态1: 成功(乐观写先于 POST, 回执后重拉收口) ------------------------------- */
  let resolve1;
  const c1 = mkCtx([1, 1], () => new Promise((r) => { resolve1 = r; }), true);
  const p1 = c1.setFilePriority(7, [0, 1]);
  await flush();
  ok("态1: POST 发出时 files 已是新值(乐观写先于 POST)", JSON.stringify(c1.postsSeen[0]) === "[7,7]");
  ok("态1: 加载中徽章值即新值", JSON.stringify(c1.drawer.files.map((r) => r.priority)) === "[7,7]");
  ok("态1: 一次 POST 载荷 = indices/priority", c1.posts.length === 1 && JSON.stringify(c1.posts[0]) === '{"indices":[0,1],"priority":7}');
  resolve1({ ok: true });
  await p1;
  ok("态1: 回执 ok 后静默重拉一次(true)", c1.refreshes.length === 1 && c1.refreshes[0] === true);
  ok("态1: 最终态 = 服务端真值(7)", JSON.stringify(c1.drawer.files.map((r) => r.priority)) === "[7,7]");
  ok("态1: 成功 toast", c1.toasts.some((t) => t.kind === "ok" && /已执行/.test(t.msg)));

  /* ---- 态2: 回执失败回滚(回 prev + 重拉对齐) ------------------------------------ */
  const c2 = mkCtx([1, 1], async () => ({ ok: false, error: "qB 拒绝" }), false);
  await c2.setFilePriority(7, [0]);
  ok("态2: 失败回滚到 prev(1)", JSON.stringify(c2.drawer.files.map((r) => r.priority)) === "[1,1]");
  ok("态2: 失败后静默重拉对齐真值", c2.refreshes.length === 1 && c2.refreshes[0] === true);
  ok("态2: 失败 toast error 含失败文案", c2.toasts.some((t) => t.kind === "error" && /失败/.test(t.msg)));

  /* ---- 态3: 等待超时回滚(与失败分开的显式出口) ---------------------------------- */
  const c3 = mkCtx([1, 1],
    async () => ({ ok: false, error: "执行等待超时(10s), 结果以程序日志为准" }), false);
  await c3.setFilePriority(7, [1]);
  ok("态3: 超时回滚到 prev(1)", JSON.stringify(c3.drawer.files.map((r) => r.priority)) === "[1,1]");
  ok("态3: 超时分支走独立文案(含「超时」)", c3.toasts.some((t) => t.kind === "error" && /超时/.test(t.msg)));
  ok("态3: 超时后静默重拉对齐", c3.refreshes.length === 1 && c3.refreshes[0] === true);

  /* ---- 态4: 重叠点击: 旧操作失败不得回滚后一次已覆盖的值 ------------------------- */
  const waits4 = [];
  const c4 = mkCtx([1], () => new Promise((r) => { waits4.push(r); }), true);
  const p4a = c4.setFilePriority(7, [0]);
  await flush();
  const p4b = c4.setFilePriority(6, [0]);
  await flush();
  ok("态4 前置: 第二次点击已覆盖为 6", c4.drawer.files[0].priority === 6);
  waits4[0]({ ok: false, error: "qB 拒绝" });
  await p4a;
  ok("态4: 旧操作失败不回滚已被覆盖的 6", c4.drawer.files[0].priority === 6);
  ok("态4: 旧操作不做重拉(由最新一次收口)", c4.refreshes.length === 0);
  waits4[1]({ ok: true });
  await p4b;
  ok("态4: 最新操作成功后重拉真值(6)", c4.refreshes.length === 1
    && c4.serverPrios[0] === 6 && c4.drawer.files[0].priority === 6);

  /* ---- 态5: 幂等: 同值重复点击, 第二次失败时回 prev(7) 而不是回到点击前的 1 ------- */
  const c5 = mkCtx([1], async () => ({ ok: true }), true);
  await c5.setFilePriority(7, [0]);
  ok("态5 前置: 第一次成功后真值 7", c5.serverPrios[0] === 7 && c5.drawer.files[0].priority === 7);
  const c5b = mkCtx([7], async () => ({ ok: false, error: "qB 拒绝" }), false);
  await c5b.setFilePriority(7, [0]);
  ok("态5: 同值重复点击失败后仍为 7(幂等, 无误回滚)", c5b.drawer.files[0].priority === 7);

  process.stdout.write(JSON.stringify({
    title: "drawerFilePrioW6a",
    ok: checks.filter((c) => c[1]).length,
    total: checks.length,
    failed: checks.filter((c) => !c[1]).map((c) => c[0]),
  }) + "\n");
})().catch((e) => { console.error(e && e.stack || e); process.exit(1); });
"""


def test_w6a_drawer_fileprio_states_node():
    """W6a node 电池: 真跑 drawer.js 的 setFilePriority/_drawerFilePriority/_drawerFileRollback

    五态: 成功(乐观写先于 POST + 重拉收口) / 回执失败回滚 / 等待超时回滚 / 重叠点击旧操作
    不回滚新值 / 同值重复点击失败仍回最后真值。api/waitCmd/toast 与两个取数原语走最小桩,
    其余真方法。无 node 静默跳过(与本仓库既有 node 电池同口径)。
    """
    _run_node_probe(_W6A_NODE_PROBE, _shared_path("drawer.js"))
