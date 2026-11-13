"""test_web_commands_bulk 测试计划: Web 命令执行 (_drain_web_commands) 与强制汇报确认

## 测试计划(每个测试函数一条)
- test_queue_torrent_qb_reject_receipt_and_log: qB 业务拒绝(409 未启用队列) -> error 回执带可读文案 + 行动建议, 日志走 WARNING 分支不带堆栈
- test_qb_reject_text_classification: qb_reject_text 分流(4xx 业务拒绝附建议; 401/5xx/非 qB 异常返回 None)
- test_bulk_optimistic_actions_have_truth_channel: 守阵(report 26-10-11-2017 §6.4): 乐观白名单 {pause,resume} 的批量动作必须不在延迟回执族、走完 drain 登记待推真值、回执由 drain 写; 非乐观批量动作保持延迟回执族
- test_group_commands_unknown_key_error_receipt: 组命令空兜底(issue 26-10-31-1740) —— key 形状合法但 store 查无此组/成员已空 -> 不发指令 + WARNING 日志 + 显式 error 回执(drain 不覆盖); 存活组照常 ok 回执
- test_add_outcome_fail_branch: _add_outcome 全拒档(Mapping 三值最右档 "fail")
- test_bulk_limits_each_direction_independently: limits 单方向时另一方向守卫整条跳过(P0-T0.2 早退矩阵)
- test_recheck_skip_check_receipt_matrix: recheck/skip_check 回执矩阵 —— 未知 hash 有无 cmd_id 两路 + ops 拒绝/受理两档
- test_skip_check_precheck_truth_receipt: 跳检预检只读聚合 truth(results/summary) + ok 回执
- test_relocate_receipt_direct_branches: 迁移回执单点 —— 无 cmd_id 早退 / 全 blocked 带首条原因 / 无原因回落通用文案 / 混合态 ok
- test_relocate_armed_false_when_module_absent: ctx 无 relocate 模块 -> False(走旧 setLocation 路)
- test_bulk_missing_group_receipt: bulk 组键缺失计组数 -> error 回执点名
- test_bulk_recheck_via_ops_aggregates_skip_and_fail: 批量 recheck 经 ops 逐个提交, 跳过/失败计数进聚合文案
- test_add_torrents_files_only_and_urls_only: _cmd_add_torrents files/urls 两分支各自一次调用
- test_add_torrents_registers_expect_landing: add 回执的 added_torrent_ids 登记为「待落地」(issue 26-10-30-0626 追平); 老版 qB 纯文本回执拿不到 id -> 静默跳过不报错
- test_bulk_partial_group_delete_files_hard_rejected: 部分组闸门(issue 26-11-11-0823 混合形态) —— delete×delete_files=true×部分组 fail-closed 硬拒: error 回执点名共存成员(组名/缺口/改选整组) + 零 qB 调用 + WARNING 日志; delete_files=false 部分组照常放行(辅种退役正常路径)
- test_bulk_partial_group_release_faces_matrix: 放行面矩阵(D2 口径, 与前端 _partialGroupsOf 守阵对账) —— keys 覆盖全组 / 成员全选平铺 / 单成员组 / 未归组 / 组缩到 1 在册成员(陈旧索引不算) 各自 delete_files=true 放行
- test_bulk_partial_group_dual_channel_same_batch_rejected: 双通道同批拒收面(keys=[组A 全组]+hashes=[组B 部分成员]×delete_files=true) —— 拒且只列组 B, keys 非空不得短路闸门(与前端 S3 电池跨组混合断言同款兜底)
- test_bulk_partial_group_delete_message_aggregates_groups: 多组聚合文案 —— 两组合计缺口; 四组触发「等 K 个组」截断(与前端 _partialGroupsSummary 同形)
- test_bulk_partial_group_location_confirm_gate: 迁移关 location 部分组闸 —— 无 confirm 拒单(零 qB 调用), confirm=true 放行直发 setLocation(D3 拍板挪一个单放合法); keys 覆盖全组照常直发
- test_bulk_partial_group_location_armed_not_gated: 迁移武装态部分组 location 不进闸门(锚点 :701 在闸前分流) —— relocate_execute 收选中集合与 confirm 原样透传, 零 setLocation 直发
- test_rename_fs_partial_group_hard_rejected: rename-fs 部分组闸门(issue 26-11-12-0807) —— 重命名辅种组共享文件/文件夹 fail-closed 硬拒(组名/缺口/不支持重命名) + 零 qB 调用; 未归组/单成员组/组缩到 1 在册成员照常放行(谓词复用 _partial_groups_of)
"""

import tempfile

import time

from types import SimpleNamespace

from auto_qb.infra.utils import encode_group_key, mask_tracker_url

from auto_qb.webui.runtime import WebUIRuntime

from helpers import capture_logs

from webui_helpers import _make_grouped_manager


def test_queue_torrent_qb_reject_receipt_and_log():
    """qB 业务拒绝(HTTP 4xx): 队列命令遇 409 -> error 回执带可读文案 + 行动建议, 日志 WARNING 不带堆栈"""
    from qbittorrentapi import Conflict409Error

    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)

        def _boom(torrent_hashes=None):
            raise Conflict409Error("必须启用 torrent 队列")

        client.torrents_decrease_priority = _boom
        with capture_logs("auto_qb.webui.runtime") as cap:
            mgr.web.commands.put(("queue_torrent", {"hash": "HA", "action": "down", "cmd_id": "q409"}))
            mgr.web.consume_commands()
        r = mgr.web.results["q409"]
        assert r["status"] == "error", r
        assert "qB 拒绝执行" in r["error"] and "必须启用 torrent 队列" in r["error"], r
        assert "启用队列" in r["error"], "已知场景应附可行动建议"
        # 分流判据: 走「被 qB 拒绝」WARNING 分支, 而非「命令执行失败」ERROR 分支(文案区分, 级别绑定分支)
        assert any("命令被 qB 拒绝" in m for m in cap.messages), cap.messages
        assert not any("命令执行失败" in m for m in cap.messages), cap.messages


def test_qb_reject_text_classification():
    """qb_reject_text: 4xx 业务拒绝 -> 可读文案(已知场景附建议); 401/5xx/非 qB 异常 -> None(交回 ERROR 分支)"""
    from qbittorrentapi import Conflict409Error, HTTP500Error, NotFound404Error, Unauthorized401Error

    from auto_qb.webui.commands import qb_reject_text

    txt = qb_reject_text(Conflict409Error("必须启用 torrent 队列"))
    assert txt is not None and "qB 拒绝执行" in txt and "启用队列" in txt, txt
    # 未知 4xx: 只给通用前缀, 不硬塞建议
    assert qb_reject_text(NotFound404Error("Not Found")) == "qB 拒绝执行: Not Found"
    # 401(凭据/环境) / 5xx(服务端) / 非 qB 异常: 不属业务拒绝 -> None
    assert qb_reject_text(Unauthorized401Error("bad creds")) is None
    assert qb_reject_text(HTTP500Error("boom")) is None
    assert qb_reject_text(ValueError("x")) is None


def test_bulk_optimistic_actions_have_truth_channel():
    """守阵(report 26-10-11-2017 §6.4): 前端乐观白名单的动作必须都具备"真值出口"

    bulk_torrents 是 8-action 大杂烩 —— 若对"是否延迟回执"做**整体**归属, pause/resume 的真值
    出口会被一并切断(§4.3: 前端 resolveOptimistic 成功时设 hold=true 等真值事件, 而批量路径永远
    等不到 ⇒ 8 秒兜底回滚到"点击那一刻的旧值")。

    本用例按乐观白名单遍历断言: 每个动作都 1. 不在延迟回执族 2. 走完 drain 后登记待推真值
    3. 回执由 drain 写。**新增乐观动作(前端 _optimisticPatch 加分支)时必须同步进来** —— 这就是
    "白名单加了新动作、真值出口没跟上"这类回归的机械守卫。
    """
    from auto_qb.webui.commands import _OPTIMISTIC_BULK_ACTIONS, is_deferred_receipt
    assert _OPTIMISTIC_BULK_ACTIONS, "乐观白名单不应为空(空则本守阵失去意义)"
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        for i, action in enumerate(sorted(_OPTIMISTIC_BULK_ACTIONS)):
            assert not is_deferred_receipt("bulk_torrents", {"action": action}), \
                f"{action} 是乐观动作, 不得进延迟回执族(否则收不到真值事件)"
            cid = f"t{i}"
            mgr.web.commands.put(("bulk_torrents", {"hashes": ["HA"], "action": action, "cmd_id": cid}))
            mgr.web.consume_commands()
            assert mgr.web.results[cid]["status"] == "ok", (action, mgr.web.results[cid])
            assert cid in mgr.web.truth_pending, f"{action}: 乐观动作必须登记待推真值(真值出口)"
        # 反向: 非乐观的批量动作仍走延迟回执族(handler 自写回执, drain 不登记真值)
        for action in ("recheck", "skip_check", "delete", "add_tags", "limits"):
            assert is_deferred_receipt("bulk_torrents", {"action": action}), \
                f"{action} 非乐观动作应保持延迟回执族"
        # 单发 pause/resume 本就走 drain 的真值通路(handler 不自写回执); recheck 由 handler 自写
        assert not is_deferred_receipt("pause_torrent")
        assert not is_deferred_receipt("resume_torrent")
        assert is_deferred_receipt("recheck_torrent")


def test_group_commands_unknown_key_error_receipt():
    """组命令空兜底(issue 26-10-31-1740): key 形状合法但 store 查无此组 / 成员已全部不在快照
    -> 不发指令 + WARNING 日志 + 显式 error 回执, drain 不得再用 ok 覆盖

    修复前: _group_action/_cmd_delete_group 空 hashes 静默返回, drain 侧 RESYNC 通路恒补
    ok —— 直调 API / 前端视图过期时回执 ok、零效果、零日志。两档文案区分根因(查无此组 vs
    成员已删光); reannounce 的空组分支收编进同一兜底单点。红验: 兜底拆掉(空组静默返回)
    则回执判红 + 日志判红。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        unknown = ("R:/no-such-group", ("y.mkv", ))
        with capture_logs("auto_qb.webui.commands") as cap:
            for cmd, payload in (
                ("pause_group", {
                    "key": unknown
                }),
                ("resume_group", {
                    "key": unknown
                }),
                ("delete_group", {
                    "key": unknown,
                    "delete_files": True
                }),
                ("reannounce_group", {
                    "key": unknown
                }),
            ):
                mgr.web.commands.put((cmd, {**payload, "cmd_id": f"c-{cmd}"}))
            mgr.web.consume_commands()
        assert client.calls == [], f"查无此组不得调用 qB API: {client.calls}"
        for cmd in ("pause_group", "resume_group", "delete_group", "reannounce_group"):
            r = mgr.web.results[f"c-{cmd}"]
            assert r["status"] == "error", f"{cmd}: 必须 error 回执(drain 恒 ok 已废): {r}"
            assert "组不存在或已被解散" in r["error"], f"{cmd}: 文案区分根因: {r['error']}"
        assert sum("整组跳过: 组不存在或已被解散" in m for m in cap.messages) == 4, cap.messages
    with tempfile.TemporaryDirectory() as td:
        # 成员执行时刻已全部不在快照(组还在 store.groups): 第二档文案
        mgr, client, key = _make_grouped_manager(td)
        mgr.store.remove_torrent("HA")
        mgr.store.remove_torrent("HB")
        assert mgr._group_hashes(key) == [], "前置: 组内成员已全部不在快照"
        for cmd in ("pause_group", "delete_group"):
            mgr.web.commands.put((cmd, {"key": key, "cmd_id": f"m-{cmd}"}))
        mgr.web.consume_commands()
        assert client.calls == [], f"成员空不得调用 qB API: {client.calls}"
        for cmd in ("pause_group", "delete_group"):
            r = mgr.web.results[f"m-{cmd}"]
            assert r["status"] == "error" and "组内种子不存在或已被删除" in r["error"], r
    with tempfile.TemporaryDirectory() as td:
        # 存活组不回归: 正常路径照旧由 drain 写 ok(handler 不写, defer_receipt 通路不变)
        mgr, client, key = _make_grouped_manager(td)
        mgr.web.commands.put(("pause_group", {"key": key, "cmd_id": "ok-alive"}))
        mgr.web.consume_commands()
        assert client.calls == [("pause", ["HA", "HB"])], client.calls
        assert mgr.web.results["ok-alive"]["status"] == "ok", "存活组回执通路不变"


def test_add_outcome_fail_branch():
    """_add_outcome 全拒档(Mapping 形态): success+pending 都为 0 => "fail"(聚合三值的最右档)"""
    from auto_qb.webui.commands import _add_outcome

    assert _add_outcome({"success_count": 0, "failure_count": 2, "pending_count": 0})[0] == "fail"
    assert _add_outcome({"success_count": 1, "failure_count": 1, "pending_count": 0})[0] == "partial"
    assert _add_outcome({"success_count": 1, "failure_count": 0, "pending_count": 0})[0] == "ok"


def test_bulk_limits_each_direction_independently():
    """limits 只调有值方向: 单方向时另一方向的守卫整条跳过(早退矩阵 296)<+=></+=>"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        hashes = ["HA", "HB"]
        mgr.web.commands.put(("bulk_torrents", {"hashes": hashes, "action": "limits", "up_limit": 512}))
        mgr.web.commands.put(("bulk_torrents", {"hashes": hashes, "action": "limits", "dl_limit": 256}))
        mgr.web.consume_commands()
        up_calls = [c for c in client.calls if c[0] == "set_upload_limit"]
        dl_calls = [c for c in client.calls if c[0] == "set_download_limit"]
        assert len(up_calls) == 1 and up_calls[0][1] == 512
        assert len(dl_calls) == 1 and dl_calls[0][1] == 256, "两次投递各只调各自方向"


def test_recheck_skip_check_receipt_matrix(monkeypatch):
    """recheck/skip_check 回执矩阵: 未知 hash 有无 cmd_id 两路 + ops 拒绝/受理两档"""
    from types import SimpleNamespace

    with tempfile.TemporaryDirectory() as td:
        mgr, client, _key = _make_grouped_manager(td)
        cmds = mgr.host.get("web_commands") if mgr.host.get("web_commands") else mgr
        drain = mgr.web.consume_commands

        # 未知 hash: 无 cmd_id 静默; 有 cmd_id error 回执(删除守卫的显式回执口径)
        mgr.web.commands.put(("recheck_torrent", {"hash": "ZZZ"}))
        mgr.web.commands.put(("recheck_torrent", {"hash": "ZZZ", "cmd_id": "c-unknown"}))
        drain()
        rec = mgr.web.results.get("c-unknown")
        assert rec is not None and rec["status"] == "error" and "不存在" in rec["error"]

        # ops 拒绝(校验进行中) -> error 回执带自解释文案
        monkeypatch.setattr(
            mgr.ctx.ops, "recheck", lambda *a, **k: SimpleNamespace(is_ok=False, is_pending=False, message="校验进行中")
        )
        mgr.web.commands.put(("recheck_torrent", {"hash": "HA", "cmd_id": "c-busy"}))
        drain()
        assert mgr.web.results["c-busy"]["status"] == "error" and "校验进行中" in mgr.web.results["c-busy"]["error"]

        # ops 受理 -> ok 回执
        monkeypatch.setattr(mgr.ctx.ops, "recheck", lambda *a, **k: SimpleNamespace(is_ok=True, message="ok"))
        mgr.web.commands.put(("recheck_torrent", {"hash": "HA", "cmd_id": "c-ok"}))
        drain()
        assert mgr.web.results["c-ok"]["status"] == "ok"

        # skip_check: 拒绝 -> error; 受理 -> ok
        monkeypatch.setattr(mgr.ctx.ops, "skip_check", lambda *a, **k: SimpleNamespace(is_ok=False, message="今天已跳过"))
        mgr.web.commands.put(("skip_check_torrent", {"hash": "HA", "cmd_id": "c-skip-no"}))
        drain()
        assert mgr.web.results["c-skip-no"]["status"] == "error"
        monkeypatch.setattr(mgr.ctx.ops, "skip_check", lambda *a, **k: SimpleNamespace(is_ok=True, message="ok"))
        mgr.web.commands.put(("skip_check_torrent", {"hash": "HA", "cmd_id": "c-skip-yes"}))
        drain()
        assert mgr.web.results["c-skip-yes"]["status"] == "ok"


def test_skip_check_precheck_truth_receipt(monkeypatch):
    """跳检预检只读: 聚合 truth(results/summary) + ok 回执; ops 侧零副作用透传"""
    with tempfile.TemporaryDirectory() as td:
        mgr, _client, _key = _make_grouped_manager(td)
        rows = [
            {
                "hash": "HA",
                "name": "a",
                "cls": "ok",
                "reasons": []
            },
            {
                "hash": "HB",
                "name": "b",
                "cls": "blocked",
                "reasons": [{
                    "text": "部分下载"
                }]
            },
        ]
        monkeypatch.setattr(mgr.ctx.ops, "skip_check_precheck", lambda req: rows)
        mgr.web.commands.put(("skip_check_precheck", {"hashes": ["HA", "HB"], "cmd_id": "c-pre"}))
        mgr.web.consume_commands()
        rec = mgr.web.results["c-pre"]
        assert rec["status"] == "ok"
        assert rec["truth"]["results"] == rows
        assert rec["truth"]["summary"] == {"ok": 1, "force": 0, "blocked": 1}


def test_relocate_receipt_direct_branches():
    """迁移回执单点直驱: 无 cmd_id 早退 / 全 blocked 带首条原因 / 无原因回落通用文案"""
    with tempfile.TemporaryDirectory() as td:
        mgr, _client, _key = _make_grouped_manager(td)
        cmds = mgr
        items_all_blocked = [{"cls": "blocked", "reasons": [{"text": "目标目录已被占用"}]}, {"cls": "blocked", "reasons": []}]
        # 无 cmd_id: 不发回执也不炸(813 早退)
        cmds._relocate_receipt("", items_all_blocked, "移动位置(整组迁移) HA")
        assert mgr.web.results.get("", None) is None
        # 全 blocked + 有原因: error 回执带首条自解释文案(815-823)
        cmds._relocate_receipt("c-b1", items_all_blocked, "移动位置(整组迁移) HA")
        rec = mgr.web.results["c-b1"]
        assert rec["status"] == "error" and rec["error"] == "目标目录已被占用"
        assert rec["truth"]["summary"]["blocked"] == 2
        # 全 blocked 无任何原因: 回落通用文案
        cmds._relocate_receipt("c-b2", [{"cls": "blocked", "reasons": []}], "批量移动位置(整组迁移)")
        assert mgr.web.results["c-b2"]["error"] == "整组迁移被闸门拒绝"
        # 混合态(有 started): ok 回执
        cmds._relocate_receipt(
            "c-mix", [{
                "cls": "started",
                "reasons": []
            }, {
                "cls": "blocked",
                "reasons": [{
                    "text": "x"
                }]
            }], "移动位置(整组迁移) HA"
        )
        assert mgr.web.results["c-mix"]["status"] == "ok"


def test_relocate_armed_false_when_module_absent(monkeypatch):
    """三入口接线判据: ctx 无 relocate 模块 -> False(整组迁移未武装时走旧 setLocation 路)"""
    from types import SimpleNamespace

    with tempfile.TemporaryDirectory() as td:
        mgr, _client, _key = _make_grouped_manager(td)
        real_ctx = mgr.ctx
        mgr.ctx = SimpleNamespace(relocate=None, config=mgr.config, api=mgr.api)
        try:
            assert mgr._relocate_armed() is False
        finally:
            mgr.ctx = real_ctx


def test_bulk_missing_group_receipt():
    """bulk 组键缺失: 缺失组计组数 -> error 回执点名组数(纯 hash 列表不变)"""
    from helpers import FakeTorrent

    with tempfile.TemporaryDirectory() as td:
        mgr, _client, key = _make_grouped_manager(td)
        from auto_qb.infra.utils import encode_group_key

        bad_key = encode_group_key(("R:/no-such", ("x.mkv", )))
        mgr.web.commands.put(
            ("bulk_torrents", {
                "hashes": ["HA"],
                "keys": [bad_key],
                "action": "pause",
                "cmd_id": "c-mg"
            })
        )
        mgr.web.consume_commands()
        rec = mgr.web.results["c-mg"]
        assert rec["status"] == "error" and "组不存在" in rec["error"]


def test_bulk_recheck_via_ops_aggregates_skip_and_fail(monkeypatch):
    """批量 recheck 经 ops 逐个提交: 跳过/失败计数分别进聚合回执文案"""
    from types import SimpleNamespace

    def _outcome(**kw):
        base = dict(is_ok=False, is_pending=False, is_skipped=False, is_failed=False, message="")
        base.update(kw)
        return SimpleNamespace(**base)

    with tempfile.TemporaryDirectory() as td:
        mgr, _client, _key = _make_grouped_manager(td)
        plan = {
            "HA": _outcome(is_ok=True, message="ok"),
            "HB": _outcome(is_failed=True, message="qB 拒绝"),
        }
        monkeypatch.setattr(mgr.ctx.ops, "recheck", lambda h, source=None: plan[h])
        mgr.web.commands.put(("bulk_torrents", {"hashes": ["HA", "HB"], "action": "recheck", "cmd_id": "c-fail"}))
        mgr.web.consume_commands()
        assert "个发送失败" in mgr.web.results["c-fail"]["error"]

        plan["HB"] = _outcome(is_skipped=True, message="校验进行中")
        mgr.web.commands.put(("bulk_torrents", {"hashes": ["HA", "HB"], "action": "recheck", "cmd_id": "c-skip"}))
        mgr.web.consume_commands()
        assert "个校验进行中已跳过" in mgr.web.results["c-skip"]["error"]


def test_add_torrents_files_only_and_urls_only(monkeypatch):
    """_cmd_add_torrents 两分支矩阵: 只走 files / 只走 urls(各自一次 api 调用)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, _key = _make_grouped_manager(td)
        f = td + "/x.torrent"
        with open(f, "wb") as fh:
            fh.write(b"d8:announce3:fooe")
        seen = []
        real_add = client.torrents_add

        def _spy(**kw):
            seen.append(kw)
            return real_add(**kw)

        client.torrents_add = _spy
        mgr.web.commands.put(("add_torrents", {"files": [f], "cmd_id": "c-f"}))
        mgr.web.consume_commands()
        assert mgr.web.results["c-f"]["status"] == "ok"
        assert seen and seen[0].get("torrent_files") == [f], seen

        seen.clear()
        mgr.web.commands.put(("add_torrents", {"urls": ["magnet:?xt=urn:btih:abc"], "cmd_id": "c-u"}))
        mgr.web.consume_commands()
        assert mgr.web.results["c-u"]["status"] == "ok"
        assert seen and seen[0].get("urls") == ["magnet:?xt=urn:btih:abc"], seen


def test_add_torrents_registers_expect_landing(monkeypatch):
    """add 回执的 added_torrent_ids 登记为「待落地」; 老版 qB 纯文本回执静默跳过

    issue 26-10-30-0626: qB 的 200 只代表受理, torrent 还要过 6~40ms 异步管线才进 session;
    命令后那次补刷新距 add 返回仅 0.5~0.8ms, 只拿到一部分 -> 主循环按 store 的到期时刻
    有界追平。这里钉住「登记」这一步: 回执里的 id 必须进 store, 且老版回执不得炸。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr, client, _key = _make_grouped_manager(td)
        f = td + "/x.torrent"
        with open(f, "wb") as fh:
            fh.write(b"d8:announce3:fooe")

        hashes = ["A" * 40, "B" * 40]
        client.torrents_add = lambda **kw: {
            "success_count": 2,
            "failure_count": 0,
            "pending_count": 0,
            "added_torrent_ids": hashes,
        }
        mgr.web.commands.put(("add_torrents", {"files": [f], "cmd_id": "c-x"}))
        mgr.web.consume_commands()
        assert mgr.web.results["c-x"]["status"] == "ok"
        assert mgr.store._expect_pending == set(hashes), "回执里的 added_torrent_ids 必须登记"
        assert mgr.store.expect_due_at() > 0, "登记后主循环应能提前同步"

        # 老版 qB(Web API < 2.14): 纯文本回执拿不到 id -> 不登记、不报错
        mgr.store.clear_expect()
        client.torrents_add = lambda **kw: "Ok."
        mgr.web.commands.put(("add_torrents", {"files": [f], "cmd_id": "c-y"}))
        mgr.web.consume_commands()
        assert mgr.web.results["c-y"]["status"] == "ok"
        assert mgr.store._expect_pending == set(), "拿不到 id 时不得凭空登记"


# ---------- 部分组闸门(issue 26-11-11-0823, 用户拍板混合形态) ----------


def _seed_group(mgr, client, hashes, name, file_name):
    """再灌一组(同文件表归组); 返回组 key(裸 tuple, 队列直投 = Web 层已解码态)

    seed_store 不传列表(取 client.torrents 全量) —— 传子列表会整体替换 by_hash, 把
    既有种子挤出快照(_make_grouped_manager 是全量同灌, 本助手是增量追加, 口径不同)。
    """
    from helpers import FakeTorrent, _fake_file, seed_store

    tors = [FakeTorrent(hash=h, name=name, save_path=r"R:\Downloads") for h in hashes]
    for t in tors:
        client.torrents[t.hash] = t
        client.files_map[t.hash] = [_fake_file(file_name, 100)]
    seed_store(mgr)
    grouping = mgr.host.get("grouping")
    for h in hashes:
        grouping._assign_new_torrent(h)
    return mgr.store.member_to_key[hashes[0]]


def _seed_ungrouped(mgr, client, hash_, name):
    """灌一个不归组种子(未归组 = 前端虚拟行的后端对应物); seed_store 全量口径同 _seed_group"""
    from helpers import FakeTorrent, _fake_file, seed_store

    tor = FakeTorrent(hash=hash_, name=name, save_path=r"R:\Downloads")
    client.torrents[hash_] = tor
    client.files_map[hash_] = [_fake_file(f"{name}.mkv", 100)]
    seed_store(mgr)


def test_bulk_partial_group_delete_files_hard_rejected():
    """部分组闸门(issue 26-11-11-0823 混合形态): delete×delete_files=true×部分组 fail-closed 硬拒

    证据(issue §01): bulk 直发可绕过前端三落点预警 —— 部分组带文件删除把共享物理文件删掉,
    同组其余在册成员必然缺文件(不可逆)。硬拒 = error 回执点名共存成员(组名/缺口计数/改选
    整组指引) + 零 qB 调用 + WARNING 日志。对照面: delete_files=false 的部分组删除不受闸门
    影响(不带文件删除正是辅种退役的正常路径, 计划 26-11-11-0820 不打扰原则)。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr, client, _key = _make_grouped_manager(td)
        with capture_logs("auto_qb.webui.commands") as cap:
            mgr.web.commands.put(
                ("bulk_torrents", {
                    "hashes": ["HA"],
                    "action": "delete",
                    "delete_files": True,
                    "cmd_id": "pg-del"
                })
            )
            mgr.web.consume_commands()
        r = mgr.web.results["pg-del"]
        assert r["status"] == "error", r
        assert "辅种组「Show」还有 1 个成员未包含" in r["error"], r["error"]
        assert "删除文件会破坏" in r["error"] and "请改选整组后重试" in r["error"], r["error"]
        assert client.calls == [], f"硬拒不得触碰 qB: {client.calls}"
        assert any("部分组拦截" in m for m in cap.messages), cap.messages

        # 免疫半面: confirm=true 对 delete 不释放(混合形态拍板: 硬拒不可被确认绕过) ——
        # 若闸内 confirmed 误改成对称的 bool(confirm), 本对照面红(handler 是纵深最后一层,
        # 路由层本就只对 location 透传 confirm)
        mgr.web.commands.put(
            (
                "bulk_torrents", {
                    "hashes": ["HA"],
                    "action": "delete",
                    "delete_files": True,
                    "confirm": True,
                    "cmd_id": "pg-del-c"
                }
            )
        )
        mgr.web.consume_commands()
        rc = mgr.web.results["pg-del-c"]
        assert rc["status"] == "error", rc
        assert client.calls == [], client.calls
    with tempfile.TemporaryDirectory() as td:
        mgr, client, _key = _make_grouped_manager(td)
        mgr.web.commands.put(
            ("bulk_torrents", {
                "hashes": ["HA"],
                "action": "delete",
                "delete_files": False,
                "cmd_id": "pg-soft"
            })
        )
        mgr.web.consume_commands()
        assert mgr.web.results["pg-soft"]["status"] == "ok", mgr.web.results["pg-soft"]
        assert client.calls == [("delete", False)], client.calls


def test_bulk_partial_group_release_faces_matrix():
    """放行面矩阵(D2 口径, 与前端 _partialGroupsOf 守阵对账): 闸门只拦「部分」, 其余全部放行

    - keys 覆盖全组: 组键级联展开即整组, delete_files=true 照常;
    - 成员全选平铺(恰好全组): sel==total 非部分组(API 直发全成员同样放行);
    - 单成员组: 无部分面; 未归组 hash(虚拟行对应物): 不参与判定;
    - 组缩到只剩 1 个在册成员(store.groups 陈旧索引项不算成员): 不制造假部分组。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        mgr.web.commands.put(
            ("bulk_torrents", {
                "keys": [key],
                "action": "delete",
                "delete_files": True,
                "cmd_id": "pg-k"
            })
        )
        mgr.web.consume_commands()
        assert mgr.web.results["pg-k"]["status"] == "ok", mgr.web.results["pg-k"]
        assert client.calls == [("delete", True)], client.calls
    with tempfile.TemporaryDirectory() as td:
        mgr, client, _key = _make_grouped_manager(td)
        mgr.web.commands.put(
            ("bulk_torrents", {
                "hashes": ["HA", "HB"],
                "action": "delete",
                "delete_files": True,
                "cmd_id": "pg-all"
            })
        )
        mgr.web.consume_commands()
        assert mgr.web.results["pg-all"]["status"] == "ok", mgr.web.results["pg-all"]
        assert client.calls == [("delete", True)], client.calls
    with tempfile.TemporaryDirectory() as td:
        mgr, client, _key = _make_grouped_manager(td)
        _seed_group(mgr, client, ["HS"], "Solo", "solo.mkv")
        _seed_ungrouped(mgr, client, "HU", "Lone")
        mgr.web.commands.put(
            ("bulk_torrents", {
                "hashes": ["HS", "HU"],
                "action": "delete",
                "delete_files": True,
                "cmd_id": "pg-mix"
            })
        )
        mgr.web.consume_commands()
        assert mgr.web.results["pg-mix"]["status"] == "ok", mgr.web.results["pg-mix"]
        assert client.calls == [("delete", True)], client.calls
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        mgr.store.remove_torrent("HB")
        assert [h for h in mgr.store.groups.get(key, []) if h in mgr.store.by_hash] == ["HA"], "前置: 在册成员已缩到 1"
        mgr.web.commands.put(
            ("bulk_torrents", {
                "hashes": ["HA"],
                "action": "delete",
                "delete_files": True,
                "cmd_id": "pg-shrunk"
            })
        )
        mgr.web.consume_commands()
        assert mgr.web.results["pg-shrunk"]["status"] == "ok", mgr.web.results["pg-shrunk"]
        assert client.calls == [("delete", True)], client.calls


def test_bulk_partial_group_dual_channel_same_batch_rejected():
    """双通道同批拒收面: keys=[组A 全组] + hashes=[组B 部分成员]×delete_files=true -> 拒且只列组 B

    钉住「keys 非空即短路」类回归(前端 S3 电池跨组混合断言的同款兜底面, 后端此前无等价物):
    keys 展开的组 A 照常放行不进文案, 组 B 部分成员照常拦 —— 若闸门给 keys 加非空早退,
    部分组带文件删除洞静默重开而现有电池全绿, 本用例兜住。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        _seed_group(mgr, client, ["HC", "HD"], "Show2", "other.mkv")
        mgr.web.commands.put(
            (
                "bulk_torrents", {
                    "keys": [key],
                    "hashes": ["HC"],
                    "action": "delete",
                    "delete_files": True,
                    "cmd_id": "pg-dual"
                }
            )
        )
        mgr.web.consume_commands()
        r = mgr.web.results["pg-dual"]
        assert r["status"] == "error", r
        assert "「Show2」还有 1 个成员未包含" in r["error"], r["error"]
        assert "「Show」" not in r["error"], f"keys 展开的组 A 是整组, 不得进文案: {r['error']}"
        assert client.calls == [], f"双通道同批拒收不得触碰 qB: {client.calls}"


def test_bulk_partial_group_delete_message_aggregates_groups():
    """多组聚合文案: 两组合计缺口; 四组触发「等 K 个组」截断(与前端 _partialGroupsSummary 同形)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, _key = _make_grouped_manager(td)
        _seed_group(mgr, client, ["HC", "HD"], "Show2", "other.mkv")
        mgr.web.commands.put(
            ("bulk_torrents", {
                "hashes": ["HA", "HC"],
                "action": "delete",
                "delete_files": True,
                "cmd_id": "pg-agg2"
            })
        )
        mgr.web.consume_commands()
        r = mgr.web.results["pg-agg2"]
        assert r["status"] == "error", r
        assert r["error"] == ("辅种组「Show」「Show2」还有 2 个成员未包含: 删除文件会破坏它们共享的文件(不可逆), 请改选整组后重试"), r["error"]
        assert client.calls == [], client.calls
    with tempfile.TemporaryDirectory() as td:
        mgr, client, _key = _make_grouped_manager(td)
        _seed_group(mgr, client, ["HC", "HD"], "Show2", "o1.mkv")
        _seed_group(mgr, client, ["HE", "HF"], "Show3", "o2.mkv")
        _seed_group(mgr, client, ["HG", "HH"], "Show4", "o3.mkv")
        mgr.web.commands.put(
            (
                "bulk_torrents", {
                    "hashes": ["HA", "HC", "HE", "HG"],
                    "action": "delete",
                    "delete_files": True,
                    "cmd_id": "pg-agg4"
                }
            )
        )
        mgr.web.consume_commands()
        r = mgr.web.results["pg-agg4"]
        assert "「Show」「Show2」「Show3」等 4 个组还有 4 个成员未包含" in r["error"], r["error"]
        assert client.calls == [], client.calls


def test_bulk_partial_group_location_confirm_gate():
    """迁移关 location 部分组闸(issue 26-11-11-0823): 无 confirm 拒单、confirm=true 放行

    D3 拍板「挪一个种子单放」是合法意图 —— 闸门只拦未确认直发: 无 confirm 时 error 回执点名
    共存成员并给改选整组指引(第三方脚本可显式带 confirm=true 重发), 零 qB 调用; confirm=true
    放行直发 setLocation(前端 S3 确认框确认后即带此键, drawer.js submitMoveDialog 闸放行位)。
    对照面: keys 覆盖全组的迁移关移动照常直发(整组搬走无共存成员被破坏)。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr, client, _key = _make_grouped_manager(td)
        mgr.web.commands.put(
            ("bulk_torrents", {
                "hashes": ["HA"],
                "action": "location",
                "location": "R:/dst",
                "cmd_id": "pg-loc"
            })
        )
        mgr.web.consume_commands()
        r = mgr.web.results["pg-loc"]
        assert r["status"] == "error", r
        assert "辅种组「Show」还有 1 个成员未包含" in r["error"] and "移动会破坏" in r["error"], r["error"]
        assert client.calls == [], client.calls

        mgr.web.commands.put(
            (
                "bulk_torrents", {
                    "hashes": ["HA"],
                    "action": "location",
                    "location": "R:/dst",
                    "confirm": True,
                    "cmd_id": "pg-loc-ok"
                }
            )
        )
        mgr.web.consume_commands()
        assert mgr.web.results["pg-loc-ok"]["status"] == "ok", mgr.web.results["pg-loc-ok"]
        assert client.calls == [("set_location", "R:/dst")], client.calls
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        mgr.web.commands.put(
            ("bulk_torrents", {
                "keys": [key],
                "action": "location",
                "location": "R:/dst",
                "cmd_id": "pg-loc-key"
            })
        )
        mgr.web.consume_commands()
        assert mgr.web.results["pg-loc-key"]["status"] == "ok", mgr.web.results["pg-loc-key"]
        assert client.calls == [("set_location", "R:/dst")], client.calls


def test_bulk_partial_group_location_armed_not_gated():
    """迁移武装态部分组 location 不进闸门: 整组迁移分支级联全组(relocate_execute), 无此洞

    武装态在闸门之前分流(issue 锚点 commands_torrents.py:701); 本用例钉住分流序 ——
    relocate_execute 收到的是选中集合与 confirm 原样透传(全组级联是 relocate 侧 _buckets
    的职责), 闸门零触发、零 setLocation 直发。
    """
    from types import SimpleNamespace as NS

    with tempfile.TemporaryDirectory() as td:
        mgr, client, _key = _make_grouped_manager(td)
        mgr.config.relocate.enabled = True
        seen = []

        def _exec(hashes, location, confirm=False, origin="unknown"):
            seen.append((list(hashes), location, confirm, origin))
            return [{"hash": "HA", "cls": "skip", "reasons": [], "notes": ["幂等"]}]

        mgr.ctx.relocate = NS(relocate_execute=_exec)
        mgr.web.commands.put(
            ("bulk_torrents", {
                "hashes": ["HA"],
                "action": "location",
                "location": "R:/dst",
                "cmd_id": "pg-armed"
            })
        )
        mgr.web.consume_commands()
        assert seen == [(["HA"], "R:/dst", False, "web")], seen
        r = mgr.web.results["pg-armed"]
        assert r["status"] == "ok", r
        assert client.calls == [], f"武装态不得直发 setLocation: {client.calls}"


# ---------- rename-fs 部分组闸门(issue 26-11-12-0807) ----------


def test_rename_fs_partial_group_hard_rejected():
    """rename-fs 部分组闸门(issue 26-11-12-0807): 重命名辅种组共享文件 fail-closed 硬拒

    rename-fs 重命名的是共享物理文件/文件夹(同组 = 同 save_path + 同文件表, 磁盘只占一份),
    qB 只重写本成员的文件表映射, 同组其余在册成员仍指旧名 -> 缺文件(不可逆)。对共存成员纯
    破坏无合法意图(区别于迁移关 location 的 confirm 位) —— 硬拒 = error 回执点名组名与缺口
    + 零 qB 调用; 文件/文件夹两形态同闸。放行面: 未归组/单成员组照常(谓词复用 0823 的
    _partial_groups_of)。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr, client, _key = _make_grouped_manager(td)
        # 文件形态: 部分组(组内 2 在册成员, 直发其一)硬拒
        mgr.web.commands.put(
            ("rename_fs", {
                "hash": "HA",
                "old_path": "movie.mkv",
                "new_path": "renamed.mkv",
                "cmd_id": "rfs-g"
            })
        )
        mgr.web.consume_commands()
        r = mgr.web.results["rfs-g"]
        assert r["status"] == "error", r
        assert "辅种组「Show」还有 1 个成员共享该文件" in r["error"], r["error"]
        assert "不支持重命名" in r["error"], r["error"]
        assert client.calls == [], f"硬拒不得触碰 qB: {client.calls}"
        # 文件夹形态同闸
        mgr.web.commands.put(
            (
                "rename_fs", {
                    "hash": "HA",
                    "old_path": "season1",
                    "new_path": "season01",
                    "is_folder": True,
                    "cmd_id": "rfs-gf"
                }
            )
        )
        mgr.web.consume_commands()
        rf = mgr.web.results["rfs-gf"]
        assert rf["status"] == "error", rf
        assert "辅种组「Show」还有 1 个成员共享该文件" in rf["error"], rf["error"]
        assert client.calls == [], client.calls
    with tempfile.TemporaryDirectory() as td:
        # 放行面: 未归组 hash 照常重命名(谓词不参与)
        mgr, client, _key = _make_grouped_manager(td)
        _seed_ungrouped(mgr, client, "HU", "Lone")
        mgr.web.commands.put(
            ("rename_fs", {
                "hash": "HU",
                "old_path": "Lone.mkv",
                "new_path": "renamed.mkv",
                "cmd_id": "rfs-u"
            })
        )
        mgr.web.consume_commands()
        assert mgr.web.results["rfs-u"]["status"] == "ok", mgr.web.results["rfs-u"]
        assert client.calls == [("rename_file", ("HU", "Lone.mkv", "renamed.mkv"))], client.calls
    with tempfile.TemporaryDirectory() as td:
        # 放行面: 单成员组无部分面照常; 组缩到 1 个在册成员(陈旧索引不算)不制造假拦截
        mgr, client, key = _make_grouped_manager(td)
        _seed_group(mgr, client, ["HS"], "Solo", "solo.mkv")
        mgr.web.commands.put(
            ("rename_fs", {
                "hash": "HS",
                "old_path": "solo.mkv",
                "new_path": "renamed.mkv",
                "cmd_id": "rfs-s"
            })
        )
        mgr.web.consume_commands()
        assert mgr.web.results["rfs-s"]["status"] == "ok", mgr.web.results["rfs-s"]
        assert client.calls[-1] == ("rename_file", ("HS", "solo.mkv", "renamed.mkv")), client.calls
        mgr.store.remove_torrent("HB")
        mgr.web.commands.put(
            ("rename_fs", {
                "hash": "HA",
                "old_path": "movie.mkv",
                "new_path": "renamed.mkv",
                "cmd_id": "rfs-s1"
            })
        )
        mgr.web.consume_commands()
        assert mgr.web.results["rfs-s1"]["status"] == "ok", mgr.web.results["rfs-s1"]
        assert client.calls[-1] == ("rename_file", ("HA", "movie.mkv", "renamed.mkv")), client.calls
