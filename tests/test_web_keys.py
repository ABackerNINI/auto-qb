"""test_web_keys 测试计划: 键盘快捷键 /api/keys (W6)

## 测试计划(每个测试函数一条)
- test_api_keys_get_default_when_missing: 快捷键配置文件不存在 -> GET 回默认表(计划 26-09-28-0354 W6 §4.4)
- test_api_keys_put_roundtrip: PUT 合法配置落盘(atomic_write)且 GET 原样回读; 空串=显式禁用语义保留
- test_api_keys_put_invalid_rejected: PUT 结构非法(schema_version/模板/overrides 形状/归一化串) -> 422 且不触碰磁盘
- test_api_keys_read_corrupt_fallback: 主文件坏 JSON -> WARN + 默认表; .bak 完好 -> 回备份(读时兜底链)
- test_api_keys_unknown_schema_version_fallback: schema_version 不识别 -> 回默认表 + WARN(升级链口径: 宁可回默认不带病生效)
- test_drain_web_commands_recheck_rejected_while_checking: R1 单发拒绝(plan 26-09-30-0109) —— 规则校验在途时 WEB recheck 回执 error「校验进行中」, qB 不重启校验
- test_drain_web_commands_bulk_recheck_skips_inflight: R1 bulk 第二入口 —— 在途 hash 逐个经 ops 过滤, 聚合回执带「N 个校验进行中已跳过」, 其余正常提交
- test_drain_web_commands_bulk_skip_check_aggregated: bulk 跳检经 ops 逐 hash 串行(计划 26-10-02-1955 W3) —— 混合结果聚合回执分段计数(成功 / 同日去重 skip / 部分下载禁+执行失败 fail); 成功批 ok 回执且记录同日去重(skip_check_day 跨来源共享)
- test_drain_web_commands_bulk_skip_check_gated: bulk 跳检 gate(D2=是·fail-closed) —— web.skip_check_menu 关时 drain 分派处拒单且零 qB 调用; 同 manager 实时改配置即放行(现读不按值持有)
- test_drain_web_commands_skip_check_torrent: 右键跳检命令(P2') —— 经 ops 层四阶段全流程, 回执 ok 且记录同日去重
"""
import os
import tempfile
from pathlib import Path

from webui_helpers import _make_grouped_manager, module_log

# ---------------- 键盘快捷键 /api/keys(W6, 计划 26-09-28-0354 §4.4; 前端接线守阵在 test_web_shortcuts.py) ----------------


def _keys_headers(mgr):
    return {"Authorization": f"Bearer {mgr.web.token}"}


def test_api_keys_get_default_when_missing(web_env):
    """快捷键配置文件不存在(用户从未自定义) -> GET 回默认表, 不报错不建文件"""
    mgr, client = web_env
    r = client.get("/api/keys", headers=_keys_headers(mgr))
    assert r.status_code == 200
    assert r.json() == {"schema_version": 1, "template": "aqb-default", "overrides": {}}


def test_api_keys_put_roundtrip(web_env):
    """PUT 合法配置落盘且 GET 原样回读; 空串(显式禁用)语义在存储层原样保留"""
    import json as _json

    from auto_qb.webui.server.routes.keys import keys_file_path

    mgr, client = web_env
    doc = {"schema_version": 1, "template": "aqb-default", "overrides": {"act-pause": "Ctrl+KeyP", "act-resume": ""}}
    r = client.put("/api/keys", headers=_keys_headers(mgr), json=doc)
    assert r.status_code == 200, r.text
    assert r.json() == doc
    # 落盘: 同目录文件存在且内容与响应一致(读回是合法 JSON)
    stored = _json.loads(Path(keys_file_path(mgr)).read_text(encoding="utf-8"))
    assert stored == doc
    # 回读
    r2 = client.get("/api/keys", headers=_keys_headers(mgr))
    assert r2.status_code == 200 and r2.json() == doc


def test_api_keys_put_invalid_rejected(web_env):
    """PUT 结构非法 -> 422, 且不触碰磁盘(合法旧值原样保留)"""
    import json as _json

    from auto_qb.webui.server.routes.keys import keys_file_path

    mgr, client = web_env
    good = {"schema_version": 1, "template": "aqb-default", "overrides": {"act-pause": "KeyP"}}
    assert client.put("/api/keys", headers=_keys_headers(mgr), json=good).status_code == 200
    bad_cases = [
        # schema_version 错 / 缺 template / overrides 非表 / 值非字符串 / 归一化串非法(修饰序乱/小写)
        {
            "schema_version": 2,
            "template": "aqb-default",
            "overrides": {}
        },
        {
            "schema_version": 1,
            "overrides": {}
        },
        {
            "schema_version": 1,
            "template": "aqb-default",
            "overrides": []
        },
        {
            "schema_version": 1,
            "template": "aqb-default",
            "overrides": {
                "act-pause": 1
            }
        },
        {
            "schema_version": 1,
            "template": "aqb-default",
            "overrides": {
                "act-pause": "Shift+Ctrl+KeyP"
            }
        },
        {
            "schema_version": 1,
            "template": "aqb-default",
            "overrides": {
                "act-pause": "ctrl+keyp"
            }
        },
    ]
    for bad in bad_cases:
        r = client.put("/api/keys", headers=_keys_headers(mgr), json=bad)
        assert r.status_code == 422, f"{bad} 应 422, 实得 {r.status_code}"
    # 磁盘未被触碰
    import json as _json2
    stored = _json2.loads(Path(keys_file_path(mgr)).read_text(encoding="utf-8"))
    assert stored == good


def test_api_keys_read_corrupt_fallback(web_env, caplog):
    """读时兜底链: 主文件坏 JSON -> WARN + 默认表; .bak 完好 -> 回备份(§4.4)"""
    import json as _json
    import logging as _logging

    from auto_qb.webui.server.routes.keys import keys_file_path

    mgr, client = web_env
    path = Path(keys_file_path(mgr))
    # 主文件坏 + 无备份 -> 默认表 + WARN
    path.write_text("{oops", encoding="utf-8")
    with caplog.at_level(_logging.WARNING, logger="auto_qb.web"):
        r = client.get("/api/keys", headers=_keys_headers(mgr))
    assert r.status_code == 200
    assert r.json() == {"schema_version": 1, "template": "aqb-default", "overrides": {}}
    assert any("快捷键配置" in rec.message for rec in caplog.records), "损坏必须 WARN(失效模式可测可查)"
    # .bak 完好 -> 回备份
    bak = {"schema_version": 1, "template": "aqb-default", "overrides": {"act-pause": "KeyP"}}
    (path.parent / (path.name + ".bak")).write_text(_json.dumps(bak), encoding="utf-8")
    r2 = client.get("/api/keys", headers=_keys_headers(mgr))
    assert r2.json() == bak


def test_api_keys_unknown_schema_version_fallback(web_env, caplog):
    """schema_version 不识别(未来版本) -> 回默认表 + WARN(宁可回默认, 不带病生效)"""
    import json as _json
    import logging as _logging

    from auto_qb.webui.server.routes.keys import keys_file_path

    mgr, client = web_env
    Path(keys_file_path(mgr)
        ).write_text(_json.dumps({
            "schema_version": 99,
            "template": "x",
            "overrides": {}
        }), encoding="utf-8")
    with caplog.at_level(_logging.WARNING, logger="auto_qb.web"):
        r = client.get("/api/keys", headers=_keys_headers(mgr))
    assert r.json() == {"schema_version": 1, "template": "aqb-default", "overrides": {}}
    assert any("结构不符" in rec.message for rec in caplog.records)


def test_drain_web_commands_recheck_rejected_while_checking():
    """R1 单发拒绝(plan 26-09-30-0109 §3.2): 规则校验在途时 WEB recheck -> 回执 error「校验进行中」, qB 不重启校验

    C1 的 WEB->规则半边: WEB recheck 直调 API 会重启规则正在轮询的校验, 进度回落可能触发
    CHECK_START_GIVEUP 误判失败并污染当日失败计数。提交点检查在 ops 层单点, handler 只映射回执。
    """
    from auto_qb.core.taskqueue import REQUEUE, Task

    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        inflight = Task("check", "check-checking-result", hash="HA", store=mgr.store, handler=lambda t, d: REQUEUE)
        assert mgr.task_queue.add_task(inflight)
        mgr.web.commands.put(("recheck_torrent", {"hash": "HA", "cmd_id": "r1"}))
        mgr.web.consume_commands()
        assert client.recheck_hashes_calls == [], f"拒绝时 qB 不得收到 recheck: {client.recheck_hashes_calls}"
        assert mgr.web.results["r1"]["status"] == "error", mgr.web.results
        assert "校验进行中" in mgr.web.results["r1"]["error"], mgr.web.results["r1"]


def test_drain_web_commands_bulk_recheck_skips_inflight():
    """R1 bulk 第二入口(plan 26-09-30-0109 §3.2): 在途 hash 逐个经 ops 过滤, 聚合回执带跳过计数

    bulk recheck 直调 API 是 C1 的第二入口(批量路径旁路); 现逐个走 ops_recheck(source="web"):
    在途/校验中的 hash 被拒绝并计数, 其余正常提交并登记在途(决策链 1.5 可见)。
    """
    from auto_qb.core.taskqueue import REQUEUE, Task

    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        inflight = Task("check", "check-checking-result", hash="HB", store=mgr.store, handler=lambda t, d: REQUEUE)
        assert mgr.task_queue.add_task(inflight)
        mgr.web.commands.put(("bulk_torrents", {"hashes": ["HA", "HB"], "action": "recheck", "cmd_id": "b9"}))
        mgr.web.consume_commands()
        assert client.recheck_hashes_calls == ["HA"], f"仅非在途的 HA 提交: {client.recheck_hashes_calls}"
        assert "HA" in mgr.task_queue.active_check_hashes(), "提交的 hash 应登记在途"
        assert mgr.web.results["b9"]["status"] == "error", mgr.web.results
        assert "1 个校验进行中已跳过" in mgr.web.results["b9"]["error"], mgr.web.results["b9"]


def test_drain_web_commands_bulk_skip_check_aggregated():
    """bulk 跳检经 ops 逐 hash 串行(计划 26-10-02-1955 W3): 混合结果聚合回执分段计数

    ok(四阶段走通+记同日去重) / 同日去重(skip) / 部分下载禁(fail) / 执行失败(fail) 四类
    混在一批, 回执文案逐段断言; 成功批回执 ok。gate 关闭拒单见 test_drain_web_commands_bulk_skip_check_gated。
    """
    from datetime import date

    from helpers import FakeClient, FakeTorrent, make_manager, seed_store

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        tors = [
            FakeTorrent(hash="HASH123", name="Show", state="pausedUP", progress=0.0),
            FakeTorrent(hash="HDUP", name="Dup", state="pausedUP", progress=0.0),
            FakeTorrent(hash="HPART", name="Part", state="pausedUP", progress=0.5),
            FakeTorrent(hash="HEXP", name="Exp", state="pausedUP", progress=0.0),
            FakeTorrent(hash="HASH456", name="Solo", state="pausedUP", progress=0.0),
        ]
        for t in tors:
            client.torrents[t.hash] = t
        seed_store(mgr, tors)
        # 同日去重预置(HDUP 当日已跳检过 —— skip_check_day 跨来源共享, 这里直接预写该表)
        mgr.state["skip_check_day"] = {"HDUP": date.today().isoformat()}
        # HEXP 导出失败(四阶段第一步即炸, fail 有文案)
        orig_export = client.torrents_export

        def export(torrent_hash=None, **kw):
            if torrent_hash == "HEXP":
                raise RuntimeError("boom")
            return orig_export(torrent_hash=torrent_hash, **kw)

        client.torrents_export = export
        with module_log("auto_qb.webui.commands") as messages:
            mgr.web.commands.put(
                (
                    "bulk_torrents", {
                        "hashes": ["HASH123", "HDUP", "HPART", "HEXP"],
                        "action": "skip_check",
                        "cmd_id": "bs1"
                    }
                )
            )
            mgr.web.consume_commands()
        rec = mgr.web.results["bs1"]
        assert rec["status"] == "error", rec
        # 文案逐段: ok 之外的三类各占一段(跳过按原因分桶, 失败聚合计数)
        assert "1 个跳过: 今日已跳检过该种子" in rec["error"], rec["error"]
        assert "2 个失败: " in rec["error"] and "部分下载的种子禁止跳检" in rec["error"], rec["error"]
        assert "导出 .torrent 失败" in rec["error"], rec["error"]
        assert any("批量跳检(成功 1, 跳过 1, 失败 2)" in m for m in messages), messages
        # ok 的那枚走通四阶段并记录同日去重(跨来源共享不回归)
        names = [c[0] for c in client.calls]
        assert "export" in names and "delete" in names and "add" in names, client.calls
        assert mgr.state["skip_check_day"].get("HASH123"), "web 批量跳检应记录同日去重"
        # 纯成功批 -> ok 回执(FakeClient 重加固定回 HASH123, 成功标的只能用它; 独立新 manager)
        with tempfile.TemporaryDirectory() as td2:
            mgr2 = make_manager(os.path.join(td2, "state.json"))
            client2 = FakeClient()
            mgr2.client = client2
            t2 = FakeTorrent(hash="HASH123", name="Solo", state="pausedUP", progress=0.0)
            client2.torrents["HASH123"] = t2
            seed_store(mgr2, [t2])
            with module_log("auto_qb.webui.commands") as messages2:
                mgr2.web.commands.put(
                    ("bulk_torrents", {
                        "hashes": ["HASH123"],
                        "action": "skip_check",
                        "cmd_id": "bs2"
                    })
                )
                mgr2.web.consume_commands()
            assert mgr2.web.results["bs2"]["status"] == "ok", mgr2.web.results["bs2"]
            assert any("批量跳检(成功 1 个种子)" in m for m in messages2), messages2


def test_drain_web_commands_bulk_skip_check_gated():
    """bulk 跳检 gate(计划 26-10-02-1955 W3, D2=是·fail-closed): web.skip_check_menu 关 -> drain 分派处拒单

    读实时配置(ctx.config 现取); 拒单不发任何 qB 调用(export/delete/add 零出现)。
    单发端点 403 双态既有用例不回归(test_api_t_skip_check_gated_by_config)。
    hash 用 FakeClient 重加固定回的 HASH123, 使重开开关后的放行段走通重加确认。
    """
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        t = FakeTorrent(hash="HASH123", name="Show", state="pausedUP", progress=0.0)
        client.torrents["HASH123"] = t
        seed_store(mgr, [t])
        mgr.config.web.skip_check_menu = False
        mgr.web.commands.put(("bulk_torrents", {"hashes": ["HASH123"], "action": "skip_check", "cmd_id": "bg1"}))
        mgr.web.consume_commands()
        rec = mgr.web.results["bg1"]
        assert rec["status"] == "error" and "web.skip_check_menu" in rec["error"], rec
        assert client.calls == [], "gate 拒单不得触达 qB(四阶段零调用)"
        # 开关重开(实时配置现读, 同一 manager 热改即生效)-> 放行执行
        mgr.config.web.skip_check_menu = True
        mgr.web.commands.put(("bulk_torrents", {"hashes": ["HASH123"], "action": "skip_check", "cmd_id": "bg2"}))
        mgr.web.consume_commands()
        assert mgr.web.results["bg2"]["status"] == "ok", mgr.web.results["bg2"]
        assert any(c[0] == "export" for c in client.calls), client.calls


def test_drain_web_commands_skip_check_torrent():
    """右键跳检命令(P2', plan 26-09-30-0109 §3.6): 经 ops 层四阶段全流程, 回执 ok 且记录同日去重

    WEB 触发的跳检与规则跳检同一闸门/同一去重/同一执行体(天然串行于主循环线程);
    hash 用 FakeClient 重加固定回的 HASH123, 使重加确认走通全流程。
    """
    from helpers import FakeClient, FakeTorrent, make_manager, seed_store

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        t = FakeTorrent(hash="HASH123", name="Show", state="pausedDL", progress=0.0)
        client.torrents["HASH123"] = t
        seed_store(mgr, [t])
        mgr.web.commands.put(("skip_check_torrent", {"hash": "HASH123", "cmd_id": "s1"}))
        mgr.web.consume_commands()
        names = [c[0] for c in client.calls]
        assert "export" in names and "delete" in names and "add" in names, f"应走跳检四阶段: {client.calls}"
        assert mgr.web.results["s1"]["status"] == "ok", mgr.web.results
        assert mgr.state["skip_check_day"]["HASH123"], "web 跳检应记录跨来源同日去重"
