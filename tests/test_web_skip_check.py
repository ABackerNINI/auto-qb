"""test_web_skip_check 测试计划: 跳检三分流预检 + force 透传

## 测试计划(每个测试函数一条)
- test_web_skip_check_completed_rejected_receipt: T10(26-10-05-0314 S2) —— 单发已完成种子: ops G3 闸门拒绝文案经 ActionResult 通道原样透传进 error 回执(不截断不改写), 零 qB 写调用
- test_web_bulk_skip_check_mixed_outcome: T11(26-10-05-0314 S2) —— 批量混合(1 已完成 + 1 暂停未完成): 聚合回执失败计数与文案自解释(G3), 成功标的走通四阶段并记同日去重(T12 门控不回归由既有 test_api_t_skip_check_gated_by_config(单发 403)/test_drain_web_commands_bulk_skip_check_gated(批量拒单)+ 本轮 T21 预检 403 断言覆盖, 无新用例)
- test_web_precheck_endpoint: T21(26-10-05-0314 S2) —— 预检端点 POST /api/torrents/skip-check/precheck: 路由级 403 门控同单发(fail-closed 零入队)/空 hashes 400 不入队/入队载荷 {hashes}; drain 级回执 truth={results, summary} 结构、混合 {ok, force, blocked} 计数、未知 hash → cls=blocked 文案「已不在客户端」
- test_web_force_passthrough: T22(26-10-05-0314 S2) —— 单发 body.force → ops.skip_check 收到 force=True(mock kwarg 断言)/缺省 force=False; 批量 body.force → _bulk_skip_check_via_ops 逐 hash 透传; 路由级提供才透传(缺省载荷形态不变); force=true 时 case 1 闸门(G3)照常硬拒进回执
- test_webui_no_rules_import: 边界守阵(P2') —— webui 操作链不得 import 规则模块; 其余 webui 模块不得触碰规则动作插件(rules.actions/registry)
"""
import os
import re
import tempfile
from unittest import mock

# ==================== 跳检三分流预检 + force 透传(plan 26-10-05-0314 S2) ====================


def test_web_skip_check_completed_rejected_receipt():
    """T10: 单发已完成种子 —— ops G3 闸门拒绝文案经 ActionResult 通道原样透传进 error 回执
    (handler 只映射不截断不改写), 拒绝零副作用(不得导出/删除/重加)"""
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        t = FakeTorrent(hash="HDONE", name="Done", state="pausedUP", progress=1.0)
        seed_store(mgr, [t])
        client.torrents["HDONE"] = t
        mgr.web.commands.put(("skip_check_torrent", {"hash": "HDONE", "cmd_id": "s-done"}))
        mgr.web.consume_commands()
        rec = mgr.web.results["s-done"]
        assert rec["status"] == "error", rec
        assert "已完成" in rec["error"], f"ops 拒绝文案必须原样进回执: {rec['error']!r}"
        assert client.calls == [], f"拒绝零副作用(不得导出/删除/重加): {client.calls}"


def test_web_bulk_skip_check_mixed_outcome():
    """T11: 批量混合(1 已完成 + 1 暂停未完成) —— 聚合回执失败计数与文案自解释(G3), 成功
    标的走通四阶段并记同日去重(FakeClient 重加固定回 HASH123, 成功标的只能用它 ——
    同 test_drain_web_commands_bulk_skip_check_aggregated 的口径)"""
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        tors = [
            FakeTorrent(hash="HDONE", name="Done", state="pausedUP", progress=1.0),
            FakeTorrent(hash="HASH123", name="Fresh", state="pausedDL", progress=0.0),
        ]
        for t in tors:
            client.torrents[t.hash] = t
        seed_store(mgr, tors)
        mgr.web.commands.put(
            ("bulk_torrents", {
                "hashes": ["HDONE", "HASH123"],
                "action": "skip_check",
                "cmd_id": "bm1"
            })
        )
        mgr.web.consume_commands()
        rec = mgr.web.results["bm1"]
        assert rec["status"] == "error", rec  # 部分成功也报错(既有聚合口径)
        assert "1 个失败: " in rec["error"] and "已完成" in rec["error"], f"失败计数与文案自解释: {rec['error']!r}"
        names = [c[0] for c in client.calls]
        assert "export" in names and "delete" in names and "add" in names, client.calls
        assert mgr.state["skip_check_day"].get("HASH123"), "成功的标的应记录同日去重"


def test_web_precheck_endpoint(web_env):
    """T21: 预检端点 POST /api/torrents/skip-check/precheck —— 路由级: 403 门控同单发
    (fail-closed, detail 注明键名, 关时零入队)/ 空 hashes 400 不入队 / 入队 cmd 与载荷;
    drain 级(make_manager): 回执 truth={results, summary} 结构、混合 {ok, force, blocked}
    计数、未知 hash → cls=blocked 文案「已不在客户端」"""
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    # 路由级: 门控同单发(D2=是 · fail-closed)
    mgr.config.web.skip_check_menu = False
    resp = client.post("/api/torrents/skip-check/precheck", headers=auth, json={"hashes": ["HA"]})
    assert resp.status_code == 403, resp.text
    assert "web.skip_check_menu" in resp.json()["detail"], "403 detail 必须注明配置键名"
    assert mgr.web.commands.empty(), "配置关时不得投递命令"
    # 门开: 200 入队, cmd 与载荷形状
    mgr.config.web.skip_check_menu = True
    resp = client.post("/api/torrents/skip-check/precheck", headers=auth, json={"hashes": ["HA", "HB"]})
    assert resp.status_code == 200 and resp.json()["queued"] is True, resp.text
    cmd, payload = mgr.web.commands.get_nowait()
    assert cmd == "skip_check_precheck", (cmd, payload)
    payload.pop("cmd_id")
    payload.pop("_queued_ts", None)
    assert payload == {"hashes": ["HA", "HB"]}, payload
    # 空 hashes: 400 拒收不入队(路由层参数校验, 同 bulk/limits/location 先例)
    resp = client.post("/api/torrents/skip-check/precheck", headers=auth, json={"hashes": []})
    assert resp.status_code == 400, resp.text
    assert mgr.web.commands.empty(), "空 hashes 400 不得入队"
    # drain 级: 回执结构 + 混合三态 + gone verdict
    from auto_qb.core.taskqueue import REQUEUE, Task

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        qc = FakeClient()
        mgr.client = qc
        t_ok = FakeTorrent(hash="HASH123", name="Fresh", state="pausedDL", progress=0.0)
        t_done = FakeTorrent(hash="HDONE", name="Done", state="pausedUP", progress=1.0)
        t_force = FakeTorrent(hash="HFORCE", name="Busy", state="pausedDL", progress=0.0)
        for t in (t_ok, t_done, t_force):
            qc.torrents[t.hash] = t
        seed_store(mgr, [t_ok, t_done, t_force])
        # force 样本: G5 同 hash 校验在途(kind=check 任务入队即登记 _active_checks)
        assert mgr.task_queue.add_task(
            Task("check", "check-checking-result", hash="HFORCE", store=mgr.store, handler=lambda t, d: REQUEUE)
        )
        mgr.web.commands.put(
            ("skip_check_precheck", {
                "hashes": ["HASH123", "HDONE", "HFORCE", "HMISSING"],
                "cmd_id": "pc1"
            })
        )
        mgr.web.consume_commands()
        rec = mgr.web.results["pc1"]
        assert rec["status"] == "ok", rec
        data = rec["truth"]
        assert set(data) == {"results", "summary"}, data
        results, summary = data["results"], data["summary"]
        assert [x["hash"] for x in results] == ["HASH123", "HDONE", "HFORCE", "HMISSING"], results
        assert results[0]["cls"] == "ok" and results[0]["reasons"] == [] and results[0]["name"] == "Fresh"
        assert results[1]["cls"] == "blocked", results[1]
        assert results[1]["reasons"][0]["gate"] == "G3" and "已完成" in results[1]["reasons"][0]["text"]
        assert results[2]["cls"] == "force", results[2]
        assert results[2]["reasons"][0]["gate"] == "G5"
        assert results[3]["cls"] == "blocked", results[3]
        assert results[3]["reasons"][0]["gate"] == "gone"
        assert "已不在客户端" in results[3]["reasons"][0]["text"], "gone 文案自解释"
        assert summary == {"ok": 1, "force": 1, "blocked": 2}, summary


def test_web_force_passthrough(web_env):
    """T22: force 透传 —— 单发 body.force=true → ops.skip_check 收到 force=True(mock kwarg
    断言)/ 缺省不传 → force=False; 批量 body.force=true → _bulk_skip_check_via_ops 逐 hash
    透传; 路由级提供才透传(缺省队列载荷形态不变); force=true 时 case 1 闸门(G3 已完成)
    照常硬拒, 拒绝文案进回执 —— force 只是许可不是指令"""
    from auto_qb.rules.base import ActionResult
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store

    # 路由级: force 提供才透传, 缺省载荷不带键
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    resp = client.post("/api/torrents/HA/skip-check", headers=auth, json={"force": True})
    assert resp.status_code == 200, resp.text
    cmd, payload = mgr.web.commands.get_nowait()
    assert cmd == "skip_check_torrent" and payload.get("force") is True, payload
    client.post("/api/torrents/HA/skip-check", headers=auth)  # 缺省: 不带 force
    _, payload = mgr.web.commands.get_nowait()
    assert "force" not in payload, "缺省载荷形态必须与今天一致"
    resp = client.post(
        "/api/torrents/bulk", headers=auth, json={
            "hashes": ["HA", "HB"],
            "action": "skip_check",
            "force": True
        }
    )
    assert resp.status_code == 200, resp.text
    cmd, payload = mgr.web.commands.get_nowait()
    assert cmd == "bulk_torrents" and payload.get("force") is True, payload
    client.post("/api/torrents/bulk", headers=auth, json={"hashes": ["HA"], "action": "skip_check"})
    _, payload = mgr.web.commands.get_nowait()
    assert "force" not in payload, "批量缺省载荷形态必须与今天一致"
    # drain 级(单发): kwarg 断言 —— force=True / 缺省 False
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        qc = FakeClient()
        mgr.client = qc
        t = FakeTorrent(hash="HASH123", name="Fresh", state="pausedDL", progress=0.0)
        seed_store(mgr, [t])
        qc.torrents["HASH123"] = t
        with mock.patch.object(mgr.ctx.ops, "skip_check", return_value=ActionResult.ok("mocked")) as m:
            mgr.web.commands.put(("skip_check_torrent", {"hash": "HASH123", "cmd_id": "f1", "force": True}))
            mgr.web.commands.put(("skip_check_torrent", {"hash": "HASH123", "cmd_id": "f2"}))
            mgr.web.consume_commands()
        assert [c.kwargs.get("force") for c in m.call_args_list] == [True, False], m.call_args_list
        assert mgr.web.results["f1"]["status"] == "ok" and mgr.web.results["f2"]["status"] == "ok", mgr.web.results
    # drain 级(批量): 逐 hash 透传
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        qc = FakeClient()
        mgr.client = qc
        tors = [
            FakeTorrent(hash="HA", name="A", state="pausedDL", progress=0.0),
            FakeTorrent(hash="HB", name="B", state="pausedDL", progress=0.0),
        ]
        seed_store(mgr, tors)
        with mock.patch.object(mgr.ctx.ops, "skip_check", return_value=ActionResult.ok("mocked")) as m:
            mgr.web.commands.put(
                ("bulk_torrents", {
                    "hashes": ["HA", "HB"],
                    "action": "skip_check",
                    "cmd_id": "bf1",
                    "force": True
                })
            )
            mgr.web.consume_commands()
        assert [c.kwargs.get("force") for c in m.call_args_list] == [True, True], "逐 hash 透传"
        assert mgr.web.results["bf1"]["status"] == "ok", mgr.web.results
    # force=true 时 case 1 闸门(G3)照常硬拒: 文案进回执, 零副作用
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        qc = FakeClient()
        mgr.client = qc
        t = FakeTorrent(hash="HDONE", name="Done", state="pausedUP", progress=1.0)
        seed_store(mgr, [t])
        qc.torrents["HDONE"] = t
        mgr.web.commands.put(("skip_check_torrent", {"hash": "HDONE", "cmd_id": "f3", "force": True}))
        mgr.web.consume_commands()
        rec = mgr.web.results["f3"]
        assert rec["status"] == "error" and "已完成" in rec["error"], "force 不豁越 case 1(blocked)硬闸"
        assert qc.calls == [], f"force 被拒同样零副作用: {qc.calls}"


def test_webui_no_rules_import():
    """边界守阵(P2', plan 26-09-30-0109 §3.4/FIG.2): webui 不触碰规则动作插件 —— 操作语义单点在 ops 层

    依赖方向 rules -> ops <- web: WEB 的操作执行链不得 import 规则模块(v2 收编方案做不到
    这一点 —— 它要求 WEB 调进规则模块内部)。两层口径:
    - 操作链模块(webui/{__init__,commands,runtime,views}.py): 不得 import auto_qb.rules 任何部分;
    - 其余 webui 模块: 不得 import 规则**根包**(会传递拉起动作插件注册)与 rules.actions /
      rules.registry; rules.expr / rules.base 仅限 config 编辑器表达式试算
      (server/routes/config.py 既有合法用途, 不属操作语义)。
    """
    import re

    import auto_qb.webui as _webui_pkg

    webui_root = os.path.dirname(os.path.abspath(_webui_pkg.__file__))
    op_chain = {"__init__.py", "commands.py", "runtime.py", "views.py"}
    plugin_prefixes = ("rules", "rules.actions", "rules.registry")
    rx = re.compile(r"^\s*(?:from|import)\s+(auto_qb\.rules[\w.]*|(?:\.{2,4})rules[\w.]*)")
    violations = []
    for dirpath, _dirs, files in os.walk(webui_root):
        for fn in files:
            if not fn.endswith(".py"):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, webui_root).replace("\\", "/")
            is_op_chain = "/" not in rel and fn in op_chain
            with open(full, encoding="utf-8") as f:
                for i, line in enumerate(f, 1):
                    m = rx.match(line)
                    if not m:
                        continue
                    mod = m.group(1).lstrip(".") or "rules"
                    if is_op_chain or mod in plugin_prefixes:
                        violations.append(f"{rel}:{i}: import {m.group(1).strip()}")
    assert not violations, ("webui 出现规则模块引用(依赖方向做反, 操作语义必须单点在 core/modules/ops_mod.py): "
                            f"{violations}")
