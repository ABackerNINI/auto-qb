"""test_web_commands_reannounce 测试计划: Web 命令执行 (_drain_web_commands) 与强制汇报确认

## 测试计划(每个测试函数一条)
- test_verdict_reannounce_epoch_matrix: epoch 判定矩阵(消解等待模型 plan 26-10-31-2354: updating/status3 恒 pending ②已废/③前跳 ==TOL 边界 pending/基线 status 0/1 行极值不触发/③″ 0/1/4/5/6->2 confirmed/④′ 4/5/6+msg rejected 且先于③″③判, 空 msg 不判败; 事故 26-10-31-1740)
- test_verdict_reannounce_legacy_matrix: legacy 判定矩阵(基线行无 epoch 字段 -> ③″/④′ 生效, ②在途直证已废 -> updating/status3 pending, 前跳判据不参与)
- test_verdict_reannounce_min_window_guard: updating 不构成成功证据(D2 废除②): min 未来/过期/缺失/0 下 updating 与 status3 一律 pending; min 只余③ reason 佐证与 item 级 deadline 用途
- test_trackers_baseline_shape_and_epoch_mode: baseline 形状回归 {url: {status, updating, next, min}} + epoch_mode 字段存在性探测(虚拟行排除)
- test_reannounce_receipt_truth_results_contract: 逐目标回执契约(计划 26-10-19-2007 D6/S5) —— truth.results 长度 == 目标 hash 数/status 取值域/ok 桶 reason 可空, 聚合文案逐字不变
- test_reannounce_receipt_prefix_contract: D4=warn 前缀文案契约(三前缀常量钉死, 改文案必红; 机器分流依据 = status 三值)
- test_reannounce_confirm_success_and_timeout: epoch 确认回执: 前跳命中 -> ok 回执跟踪清空; 超时 -> warn「未确认」不再判「失败」
- test_reannounce_confirm_group_aggregate: 组汇报三桶聚合(ok+error -> error 带计数与原因; 全推迟 -> warn「已受理」早回执 + 后台登记)
- test_reannounce_register_immediate_verdicts_and_deadline: 注册直判(停止种子: 投递面已拦故注册支退化为竞态兜底/推迟检出早回执+后台登记) + item 级 deadline 公式与 600 上限
- test_reannounce_skips_inactive_targets: 投递收敛(2026-10-10): 混选只投活跃子集(组内排队/暂停成员不发指令也不进确认层, 免白等窗口报假「未确认」)+ 全非活跃给显式 warn 回执 + 单种非活跃同口径; 判据读 qB 原始 state 串(queuedDL 命中 is_downloading, 谓词判不出排队)
- test_reannounce_stopped_midwindow_direct_verdict: 窗口内暂停直判(下一 tick warn「种子已停止」, 不等 deadline)
- test_reannounce_background_verify_and_cap: 推迟后台核实(达 min_e 出结论落 INFO/WARNING 日志并移除/逾时 DEBUG 静默移除/500 上限丢最旧 WARNING)
- test_reannounce_torrent_missing_and_blocked: 单种汇报 —— 未知 hash 有无 cmd_id; 非活跃 warn 且不发指令
"""

import tempfile

import time

from types import SimpleNamespace

from auto_qb.infra.clock import SYSTEM_CLOCK
from auto_qb.infra.utils import encode_group_key, mask_tracker_url

from auto_qb.webui.runtime import WebUIRuntime

from helpers import capture_logs

from webui_helpers import _make_grouped_manager


def _epoch_tracker(url="u", status=2, updating=False, next_announce=10_000, min_announce=5_000, msg=""):
    """构造 epoch 语义的 qB tracker 行替身(next_announce/min_announce 是 Unix epoch 绝对秒)"""
    return {
        "url": url,
        "status": status,
        "updating": updating,
        "next_announce": next_announce,
        "min_announce": min_announce,
        "msg": msg,
    }


def test_verdict_reannounce_epoch_matrix():
    """epoch 判定矩阵(消解等待模型, plan 26-10-31-2354): updating/status3 恒 pending(②已废),
    ③前跳=confirmed(==TOL 边界=pending, 基线 status 0/1 行不判), ③″ 变 working=confirmed,
    ④′ 4/5/6+msg=rejected(空 msg 不判败, 先于③″③判), 其余 pending"""
    from auto_qb.core.qbmanager import QbManager

    f = QbManager._verdict_reannounce
    base = {"u": {"status": 2, "updating": False, "next": 10_000, "min": 5_000}}
    kw = dict(t0=9_000, tol=3.0, now=20_000)
    # ② 已废(D2): updating/status==3 恒 pending, 不再是任何意义上的成功证据
    assert f([_epoch_tracker(updating=True)], base, **kw) == ("", "")
    assert f([_epoch_tracker(status=3)], base, **kw) == ("", "")
    # ③ 主判据: 前跳 > TOL -> confirmed; ==TOL 边界不触发
    assert f([_epoch_tracker(next_announce=10_004)], base, **kw)[0] == "confirmed"
    state, reason = f([_epoch_tracker(next_announce=10_504, min_announce=6_000)], base, **kw)
    assert state == "confirmed" and "epoch 前跳 +504s" in reason and "min 同前跳" in reason, "min 同向前跳作佐证"
    assert f([_epoch_tracker(next_announce=10_003)], base, **kw) == ("", ""), "==TOL 边界 -> pending"
    assert f([_epoch_tracker(next_announce=10_001)], base, **kw) == ("", ""), "跳幅 <= TOL -> pending"
    assert f([_epoch_tracker()], base, **kw) == ("", ""), "无变化继续等待"
    # ③ 判定域限基线 status>=2: 基线未联系行(status 0/1)带极值 next 不触发假前跳
    for b_status in (0, 1):
        b = {"u": {"status": b_status, "updating": False, "next": 10_000, "min": 5_000}}
        assert f([_epoch_tracker(status=1, next_announce=999_999)], b, **kw) == ("", ""), f"基线 status={b_status} 行不判前跳"
    # ③″(新, D6): 从未联系/曾失败行转 working -> confirmed(失败路径产不出 working, 强正证据)
    for b_status in (0, 1, 4, 5, 6):
        b = {"u": {"status": b_status, "updating": False, "next": 10_000, "min": 5_000}}
        assert f([_epoch_tracker(status=2)], b, **kw) == ("confirmed", "tracker 状态转为 working"), f"基线 {b_status} -> 2"
    # 基线已是 working: ③″ 不触发(成功证据走 ③ 前跳)
    assert f([_epoch_tracker()], base, **kw) == ("", "")
    # ④′ tracker 拒绝: 4/5/6+msg -> rejected(逐行先于③″③判, 防失败退避前跳被误判成功)
    for st in (4, 5, 6):
        assert f([_epoch_tracker(status=st, msg="tracker message", next_announce=99_999)], base,
                 **kw) == ("rejected", "失败: tracker 未接受汇报(not working): tracker message"), f"status{st}+msg"
    assert f([_epoch_tracker(status=4)], base, **kw) == ("", ""), "status4 空 msg 不武断判败"
    assert f([_epoch_tracker(status=6)], base, **kw) == ("", ""), "status6 空 msg 同口径"
    # 虚拟 tracker 行不参与判定
    assert f([_epoch_tracker(url="** [DHT]", next_announce=99_999)], base, **kw) == ("", "")


def test_verdict_reannounce_legacy_matrix():
    """legacy 判定矩阵(消解等待模型, plan 26-10-31-2354 D3): 基线行无 epoch 字段 -> ③″变 working/
    ④′拒绝生效; ②在途直证已废 -> updating/status3 恒 pending; 前跳判据不参与"""
    from auto_qb.core.qbmanager import QbManager

    f = QbManager._verdict_reannounce
    base = {"u": {"status": 1, "updating": None, "next": None, "min": None}}  # 行无 epoch 字段
    kw = dict(t0=9_000, tol=3.0, now=20_000)
    # ② 已废(D3): 在途不再判成功, 落 pending 等消解/超时(当前行用非 working 态, 免混入③″)
    assert f([_epoch_tracker(status=3)], base, **kw) == ("", "")
    assert f([_epoch_tracker(status=1, updating=True)], base, **kw) == ("", "")
    assert f([_epoch_tracker(status=2)], base, **kw) == ("confirmed", "tracker 状态转为 working")
    assert f([_epoch_tracker(status=4, msg="bad")], base, **kw) == ("rejected", "失败: tracker 未接受汇报(not working): bad")
    # 无前跳判据: 基线非 working + 当前仍非 working, next_announce 再大也不得判成功
    assert f([_epoch_tracker(status=1, next_announce=99_999)], base, **kw) == ("", "")
    assert f([_epoch_tracker(status=1)], base, **kw) == ("", ""), "基线 1 -> 1 无结论"
    b2 = {"u": {"status": 2, "updating": None, "next": None, "min": None}}
    assert f([_epoch_tracker(status=2)], b2, **kw) == ("", ""), "基线已是 working -> ③″ 不触发"
    assert f([_epoch_tracker(status=4)], base, **kw) == ("", ""), "status4 空 msg 不武断判败"


def test_verdict_reannounce_min_window_guard():
    """updating 不构成成功证据(plan 26-10-31-2354 D2 废除②): min 未来/过期/缺失/0 下 updating
    与 status3 一律 pending; min_announce 的剩余用途只有 ③ reason 佐证与 item 级 deadline。
    min 缺失/为 0 支即事故 26-10-31-1740(+1ms 假 ok)的回归锚"""
    from auto_qb.core.qbmanager import QbManager

    f = QbManager._verdict_reannounce
    base = {"u": {"status": 2, "updating": False, "next": 100_000, "min": 200_000}}
    kw = dict(t0=190_000, tol=3.0)
    # 旧断言「min 过期后 updating 直证」已随②废除翻转(D2, 语义变更重写非弱化): 在途从来不是
    # 成功证据 —— tracker 中途死掉的场景(min 过期+updating)旧断言正是假 ok 源
    assert f([_epoch_tracker(updating=True)], base, now=150_000, **kw) == ("", ""), "min 未过期: 假瞬态"
    assert f([_epoch_tracker(status=3)], base, now=199_999, **kw) == ("", "")
    assert f([_epoch_tracker(updating=True)], base, now=200_000, **kw) == ("", ""), "min 已过期: 仍 pending(消解等待)"
    # min 缺失/为 0(从未成功响应的行): 同样不给 updating 任何确认效力
    b_none = {"u": {"status": 2, "updating": False, "next": 100_000, "min": None}}
    assert f([_epoch_tracker(updating=True)], b_none, now=150_000, **kw) == ("", "")
    b_zero = {"u": {"status": 2, "updating": False, "next": 100_000, "min": 0}}
    assert f([_epoch_tracker(updating=True)], b_zero, now=150_000, **kw) == ("", "")


def test_trackers_baseline_shape_and_epoch_mode():
    """baseline 形状回归: {url: {status, updating, next, min}} + epoch_mode(任一 real 行含 next_announce 键)"""
    from auto_qb.core.qbmanager import QbManager

    from helpers import FakeClient

    client = FakeClient()
    client.trackers_map = {
        "HA":
            [
                _epoch_tracker(url="https://t.example/ann", status=2, next_announce=1000, min_announce=900),
                {
                    "url": "** [DHT]",
                    "status": 2,
                    "next_announce": 5,
                    "min_announce": 5
                },
            ],
        "HB": [{
            "url": "https://t2.example/ann",
            "status": 1,
            "msg": "x"
        }],  # 无 epoch 字段行
    }
    baseline, epoch_mode = QbManager._trackers_baseline(SimpleNamespace(client=client), ["HA", "HB"])
    assert epoch_mode is True, "任一 real 行含 next_announce 键 = epoch 模式"
    assert baseline["HA"] == {
        "https://t.example/ann": {
            "status": 2,
            "updating": False,
            "next": 1000,
            "min": 900
        }
    }, "real 行按新 dict 形状记录, 虚拟行排除"
    assert baseline["HB"] == {"https://t2.example/ann": {"status": 1, "updating": None, "next": None, "min": None}}
    # 全部行都无 next_announce 键 -> legacy 模式
    client.trackers_map = {"HA": [{"url": "https://t.example/ann", "status": 1}]}
    baseline, epoch_mode = QbManager._trackers_baseline(SimpleNamespace(client=client), ["HA"])
    assert epoch_mode is False and baseline["HA"]["https://t.example/ann"]["next"] is None


def test_reannounce_receipt_prefix_contract():
    """D4=warn 双契约(§3.4): 三前缀常量文案钉死(改文案必红); 机器分流依据是回执 status 三值"""
    from auto_qb.webui.commands import RC_DEFERRED_PREFIX, RC_FAIL_PREFIX, RC_UNCONFIRMED_PREFIX

    assert RC_FAIL_PREFIX == "失败: tracker 未接受汇报(not working): "
    assert RC_DEFERRED_PREFIX == "已受理: 最小间隔未过期, 推迟至 "
    assert RC_UNCONFIRMED_PREFIX == "未确认: "


def test_reannounce_confirm_success_and_timeout():
    """强制汇报确认(epoch 语义): 前跳命中 -> ok 回执且跟踪清空; 超时 -> warn「未确认」不再判「失败」"""
    import time as _time

    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        u = "https://tracker.hhanclub.net/announce.php"
        client.trackers_map = {"HA": [_epoch_tracker(url=u, status=2, next_announce=100_000, min_announce=90_000)]}
        # 确认前不写回执(登记 pending), tracker 无变化时继续等待
        mgr.web.commands.put(("reannounce_torrent", {"hash": "HA", "cmd_id": "cmd1"}))
        mgr.web.consume_commands()
        assert "cmd1" in mgr.web.reannounce_pending and "cmd1" not in mgr.web.results
        mgr.web.check_pending()
        assert "cmd1" not in mgr.web.results, "无前跳证据应继续等待"
        client.trackers_map["HA"][0]["next_announce"] = 105_000  # epoch 前跳 +5000s
        mgr.web.check_pending()
        assert mgr.web.results["cmd1"]["status"] == "ok"
        assert mgr.web.reannounce_pending == {}, "全部确认后跟踪应移除"
        # 超时: item 级 deadline 已过仍无证据 -> warn「未确认」(不与 error「失败」混淆)
        mgr.web.commands.put(("reannounce_torrent", {"hash": "HA", "cmd_id": "cmd2"}))
        mgr.web.consume_commands()
        mgr.web.reannounce_pending["cmd2"]["items"]["HA"]["deadline"] = _time.time() - 1
        mgr.web.check_pending()
        r = mgr.web.results["cmd2"]
        assert r["status"] == "warn"
        assert "未确认: " in r["error"] and "前跳" in r["error"]
        assert "汇报确认失败" not in r["error"], "超时不再用旧「失败」标签"


def test_reannounce_confirm_group_aggregate():
    """组强制汇报三桶聚合: ok+error -> error 带计数与原因; 全推迟 -> warn「已受理」早回执 + 后台登记"""
    import time as _time

    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        u = "https://tracker.hhanclub.net/announce.php"
        client.trackers_map = {
            "HA": [_epoch_tracker(url=u, status=2, next_announce=100_000, min_announce=90_000)],
            "HB": [_epoch_tracker(url=u, status=4, msg="rejected by tracker", next_announce=100_000)],
        }
        mgr.web.commands.put(("reannounce_group", {"key": key, "cmd_id": "cmd3"}))
        mgr.web.consume_commands()
        assert "cmd3" not in mgr.web.results
        # HA 前跳命中(ok); HB status4+msg(rejected) -> 聚合 error
        client.trackers_map["HA"][0]["next_announce"] = 105_000
        mgr.web.check_pending()
        r = mgr.web.results["cmd3"]
        assert r["status"] == "error"
        assert "成功 1, 失败 1, 未确认 0" in r["error"]
        assert "失败: tracker 未接受汇报(not working): rejected by tracker" in r["error"]
        assert mgr.web.reannounce_pending == {}
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        u = "https://tracker.hhanclub.net/announce.php"
        fut = _time.time() + 1000  # min_e - t0 = 1000s > 25s -> 双双推迟
        client.trackers_map = {
            "HA": [_epoch_tracker(url=u, status=2, next_announce=fut, min_announce=fut)],
            "HB": [_epoch_tracker(url=u, status=2, next_announce=fut + 5, min_announce=fut)],
        }
        mgr.web.commands.put(("reannounce_group", {"key": key, "cmd_id": "cmd4"}))
        mgr.web.consume_commands()
        items = mgr.web.reannounce_pending["cmd4"]["items"]
        assert all(it["done"] and it["status"] == "warn" for it in items.values()), "推迟 item 注册即出结论"
        assert set(mgr.web.reannounce_background) == {"HA", "HB"}, "推迟 item 登记后台核实"
        mgr.web.check_pending()  # 全部 item 注册时已出结论 -> 下一 tick 即聚合
        r = mgr.web.results["cmd4"]
        assert r["status"] == "warn" and "成功 0, 失败 0, 未确认 2" in r["error"]
        assert r["error"].count("已受理: 最小间隔未过期, 推迟至 ") == 2
        assert mgr.web.reannounce_pending == {}


def test_reannounce_receipt_truth_results_contract():
    """逐目标回执契约(计划 26-10-19-2007 D6/S5): truth.results 长度 == 目标 hash 数,
    status ∈ {ok,error,warn}, ok 桶 reason 可为空; 聚合文案(msg)逐字不变 —— 旧调用方零影响

    反例: 只带 msg 时"哪几个失败"在两层各丢一次(后端聚合只留前 3 条原因, 前端又把 job 拍平)。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        u = "https://tracker.hhanclub.net/announce.php"
        client.trackers_map = {
            "HA": [_epoch_tracker(url=u, status=2, next_announce=100_000, min_announce=90_000)],
            "HB": [_epoch_tracker(url=u, status=4, msg="rejected by tracker", next_announce=100_000)],
        }
        mgr.web.commands.put(("reannounce_group", {"key": key, "cmd_id": "cmdx"}))
        mgr.web.consume_commands()
        client.trackers_map["HA"][0]["next_announce"] = 105_000  # HA 确认成功, HB 被拒
        mgr.web.check_pending()

        r = mgr.web.results["cmdx"]
        assert r["status"] == "error"
        assert r["error"].startswith("成功 1, 失败 1, 未确认 0"), "聚合文案逐字不变"
        results = r["truth"]["results"]
        assert len(results) == 2, "逐目标结果长度 == 目标 hash 数"
        by_hash = {it["hash"]: it for it in results}
        assert set(by_hash) == {"HA", "HB"}
        assert {it["status"] for it in results} <= {"ok", "error", "warn"}
        assert by_hash["HA"]["status"] == "ok" and by_hash["HA"]["reason"] == "", "ok 桶 reason 可为空"
        assert by_hash["HB"]["status"] == "error" and "rejected by tracker" in by_hash["HB"]["reason"]


def test_reannounce_skips_inactive_targets():
    """投递收敛: 只投活跃子集(混选不再对非活跃发指令, 也不再给它们假「未确认」)

    qB 的 gate 只在 GUI(commit aa189a7), HTTP 端点侧没有门 —— 引擎侧的真拦截在 libtorrent
    (暂停种子 force_tracker_request 直接空转, 排队种子内部也是 paused 故同样发不出去)。
    于是"按 qB 口径放行(任一活跃即可用)"之后照集合全量投递是**有害**的: qB 的 GUI 没有
    per-target 回执所以无所谓, 我们有 tracker 确认层 —— 那些空转目标会白等到 item deadline
    再落「未确认」, 把一次干净的成功报成部分失败。故前后端各收敛一道(前端 reannouncePlan
    决定发什么, 后端这里按快照 raw state 再过滤一次, 防竞态与直连端点的调用方)。

    !判据必须读 qB 原始 state 串: 实测 queuedDL/queuedUP 命中 state_enum 的 is_downloading/
    is_uploading(只有 paused*/stopped* 是 is_stopped), 用谓词会把排队种子当活跃放过去。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        for h, st in (("HA", "uploading"), ("HB", "queuedDL")):
            rec = mgr.store.get(h)
            rec.state = st
            rec._state_enum = None  # 复位惰性缓存(state_enum 按新 state 重算)
        mgr.web.commands.put(("reannounce_group", {"key": key, "cmd_id": "g-mix"}))
        mgr.web.consume_commands()
        assert client.reannounce_hashes_calls == [["HA"]], (f"组汇报未收敛为活跃子集: {client.reannounce_hashes_calls}(排队成员也被投递了)")
        assert set(mgr.web.reannounce_pending["g-mix"]["items"]) == {"HA"}, \
            "非活跃成员进了确认跟踪(会白等窗口后落假「未确认」)"
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        for h, st in (("HA", "pausedUP"), ("HB", "checkingUP")):
            rec = mgr.store.get(h)
            rec.state = st
            rec._state_enum = None
        mgr.web.commands.put(("reannounce_group", {"key": key, "cmd_id": "g-dead"}))
        mgr.web.consume_commands()
        assert client.calls == [], "全非活跃不得发任何指令(qB 引擎收到也只是空转)"
        assert mgr.web.reannounce_pending == {}, "全非活跃不登记确认跟踪"
        r = mgr.web.results["g-dead"]
        assert r["status"] == "warn" and "均非活跃" in r["error"], \
            "全非活跃组必须给显式回执(不发指令又不写回执 = 前端 waitCmd 挂到自身超时)"
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        rec = mgr.store.get("HA")
        rec.state = "error"
        rec._state_enum = None
        mgr.web.commands.put(("reannounce_torrent", {"hash": "HA", "cmd_id": "t-dead"}))
        mgr.web.consume_commands()
        assert client.calls == [], "单种非活跃不得发指令"
        assert mgr.web.results["t-dead"]["status"] == "warn"
        assert "非活跃" in mgr.web.results["t-dead"]["error"]


def test_reannounce_register_immediate_verdicts_and_deadline():
    """注册直判: 非活跃种子不进确认层 + 竞态兜底仍出结论; 推迟检出早回执 + 后台登记; deadline 公式与 600 上限

    2026-10-10 投递收敛后 (a) 支改口径: 非活跃目标在**投递面**就被拦下(前端 reannouncePlan +
    后端 _reannounce_active), 根本走不到注册 —— 故 (a) 支从常规路径退化为**竞态兜底**
    ("过滤判活跃 -> 注册前转停止"的瞬态), 契约面改为在本测试里直接调注册面来钉住。
    """
    import time as _time

    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        # (a) 停止种子: 第二道闸直接跳过 —— 不发指令、不进确认层(不再白等窗口后报「未确认」)
        rec = mgr.store.get("HA")
        rec.state = "stoppedUP"
        rec._state_enum = None  # 复位惰性缓存(state_enum 按新 state 重算)
        mgr.web.commands.put(("reannounce_torrent", {"hash": "HA", "cmd_id": "cmd5"}))
        mgr.web.consume_commands()
        r5 = mgr.web.results["cmd5"]
        assert r5["status"] == "warn"
        assert r5["error"] == "未确认: 种子非活跃(暂停/停止/排队/校验中/错误), qB 静默忽略强制汇报"
        assert client.reannounce_hashes_calls == [], "非活跃目标不该发指令(qB 引擎收到也只是空转)"
        assert mgr.web.reannounce_pending == {}, "非活跃目标不该进确认跟踪(否则白等到 deadline 报未确认)"
        assert mgr.web.reannounce_background == {}, "非活跃目标不走推迟后台"
        # (a′) 竞态兜底: 直接调注册面, 钉住"注册时已在停止态"的即时结论文案与不等待
        mgr._register_reannounce_pending("cmd5b", ["HA"], {}, False)
        it = mgr.web.reannounce_pending["cmd5b"]["items"]["HA"]
        assert it["done"] and it["status"] == "warn"
        assert it["reason"] == "未确认: 种子已停止, qB 静默忽略强制汇报"
        assert mgr.web.reannounce_background == {}, "停止种子不走推迟后台"
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        u = "https://tracker.hhanclub.net/announce.php"
        fut = _time.time() + 1000
        client.trackers_map = {"HA": [_epoch_tracker(url=u, status=2, next_announce=fut, min_announce=fut)]}
        # (b) 推迟检出: min_e - t0 > 25s -> 立即 warn「已受理」+ 后台登记
        mgr.web.commands.put(("reannounce_torrent", {"hash": "HA", "cmd_id": "cmd6"}))
        mgr.web.consume_commands()
        it = mgr.web.reannounce_pending["cmd6"]["items"]["HA"]
        assert it["done"] and it["status"] == "warn"
        assert it["reason"].startswith("已受理: 最小间隔未过期, 推迟至 ")
        assert it["reason"].endswith("(后台继续核实, 结果见日志)")
        assert it["deadline"] - it["t0"] == 600.0, "窗口公式 capped 600(异常大 min 值不撑爆窗口)"
        bg = mgr.web.reannounce_background["HA"]
        assert bg["min_e"] == fut and bg["baseline"] == it["baseline"] and bg["epoch_mode"] is True
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        u = "https://tracker.hhanclub.net/announce.php"
        # 立即路径: min_e - t0 = 20s(<= 25 不推迟) -> deadline = t0 + max(30, 20+15) = t0+35
        now = _time.time()
        client.trackers_map = {"HA": [_epoch_tracker(url=u, status=2, next_announce=now + 20, min_announce=now + 20)]}
        mgr.web.commands.put(("reannounce_torrent", {"hash": "HA", "cmd_id": "cmd7"}))
        mgr.web.consume_commands()
        it = mgr.web.reannounce_pending["cmd7"]["items"]["HA"]
        assert not it["done"], "min_e - t0 <= 25s 走立即路径轮询"
        assert 34.9 <= it["deadline"] - it["t0"] <= 35.0
        assert "HA" not in mgr.web.reannounce_background
        # 无 min 信息: min_e 按 0 -> max(30, 负) = 30 基础窗口; legacy 行 epoch_mode=False
        client.trackers_map = {"HB": [{"url": u, "status": 1}]}
        mgr.web.commands.put(("reannounce_torrent", {"hash": "HB", "cmd_id": "cmd8"}))
        mgr.web.consume_commands()
        it8 = mgr.web.reannounce_pending["cmd8"]["items"]["HB"]
        assert not it8["done"] and it8["epoch_mode"] is False
        assert 29.9 <= it8["deadline"] - it8["t0"] <= 30.1


def test_reannounce_stopped_midwindow_direct_verdict():
    """窗口内暂停直判: 确认窗口内用户暂停种子 -> 下一 tick 立即 warn「种子已停止」, 不等 deadline"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        u = "https://tracker.hhanclub.net/announce.php"
        client.trackers_map = {"HA": [_epoch_tracker(url=u, status=2, next_announce=100_000, min_announce=90_000)]}
        mgr.web.commands.put(("reannounce_torrent", {"hash": "HA", "cmd_id": "cmd9"}))
        mgr.web.consume_commands()
        mgr.web.check_pending()
        assert "cmd9" not in mgr.web.results, "运行中无证据继续等待"
        rec = mgr.store.get("HA")
        rec.state = "stoppedUP"
        rec._state_enum = None
        mgr.web.check_pending()
        r = mgr.web.results["cmd9"]
        assert r["status"] == "warn" and "未确认: 种子已停止" in r["error"]
        assert mgr.web.reannounce_pending == {}


def test_reannounce_background_verify_and_cap():
    """推迟后台核实(D1): 达 min_e 出结论落日志并移除; 逾时静默移除; 500 上限丢最旧并 WARNING"""
    from auto_qb.core.qbmanager import QbManager
    from auto_qb.webui.commands import REANNOUNCE_BACKGROUND_MAX

    base = {"u": {"status": 2, "updating": False, "next": 100_000, "min": 90_000}}

    def _runtime(rows):
        client = SimpleNamespace(torrents_trackers=lambda h: rows)
        # _clock: 取时单点(D8 构造期注入) —— SimpleNamespace 宿主补齐 QbManager 的同名属性
        return WebUIRuntime(
            SimpleNamespace(client=client, _verdict_reannounce=QbManager._verdict_reannounce, _clock=SYSTEM_CLOCK)
        )

    # confirmed: 达 min_e 后前跳 -> INFO 日志后移除
    rt = _runtime([_epoch_tracker(next_announce=105_000)])
    rt.reannounce_background["H_OK"] = {
        "min_e": time.time() - 10,
        "baseline": base,
        "epoch_mode": True,
        "t0": time.time() - 40
    }
    with capture_logs("auto_qb.webui.runtime") as cap:
        rt.check_pending()
    assert "H_OK" not in rt.reannounce_background
    assert any("后台核实已确认" in m for m in cap.messages)
    # rejected: status4+msg -> WARNING 日志后移除
    rt = _runtime([_epoch_tracker(status=4, msg="nope")])
    rt.reannounce_background["H_BAD"] = {
        "min_e": time.time() - 10,
        "baseline": base,
        "epoch_mode": True,
        "t0": time.time() - 40
    }
    with capture_logs("auto_qb.webui.runtime") as cap2:
        rt.check_pending()
    assert "H_BAD" not in rt.reannounce_background
    assert any("后台核实失败" in m for m in cap2.messages)
    # 未达 min_e: 不读不判, 条目保留; 逾时(min_e + TIMEOUT)未出结论 -> DEBUG 静默移除
    rt = _runtime([_epoch_tracker()])
    rt.reannounce_background["H_FUT"] = {
        "min_e": time.time() + 500,
        "baseline": base,
        "epoch_mode": True,
        "t0": time.time()
    }
    rt.reannounce_background["H_OLD"] = {
        "min_e": time.time() - 100,
        "baseline": base,
        "epoch_mode": True,
        "t0": time.time() - 200
    }
    with capture_logs("auto_qb.webui.runtime") as cap3:
        rt.check_pending()
    assert "H_FUT" in rt.reannounce_background, "未达 min_e 不核实"
    assert "H_OLD" not in rt.reannounce_background, "逾时未出结论静默移除"
    assert any("逾时移除" in m for m in cap3.messages)
    # 上限 500: 超限丢最旧并 WARNING 一次
    rt = _runtime([_epoch_tracker()])
    for i in range(REANNOUNCE_BACKGROUND_MAX):
        rt.reannounce_background[f"H{i:03d}"] = {
            "min_e": time.time() + 500,
            "baseline": base,
            "epoch_mode": True,
            "t0": time.time()
        }
    host = SimpleNamespace(
        client=SimpleNamespace(torrents_trackers=lambda h: []),
        store=SimpleNamespace(get=lambda h: None),
        _verdict_reannounce=QbManager._verdict_reannounce,
        _clock=SYSTEM_CLOCK,  # 取时单点(D8): _register_reannounce_pending 经宿主 _clock 现取
    )
    host.web = rt
    fut = time.time() + 1000  # min_e - t0 > 25s: HNEW 以推迟身份登记, 触发超限逐出
    bg_base = {"u": {"status": 2, "updating": False, "next": fut, "min": fut}}
    with capture_logs("auto_qb.webui.commands") as cap4:
        QbManager._register_reannounce_pending(host, "cmd_bg", ["HNEW"], {"HNEW": bg_base}, True)
    assert len(rt.reannounce_background) == REANNOUNCE_BACKGROUND_MAX
    assert "H000" not in rt.reannounce_background and "HNEW" in rt.reannounce_background, "超限丢最旧"
    assert any("丢弃最旧" in m for m in cap4.messages)


def test_reannounce_torrent_missing_and_blocked():
    """单种汇报: 未知 hash 有无 cmd_id; 非活跃状态 warn 且不发指令"""
    from helpers import FakeTorrent

    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        cmds = mgr
        cmds._cmd_reannounce_torrent("ZZZ")  # 无 cmd_id: 静默
        assert "c-none" not in mgr.web.results
        cmds._cmd_reannounce_torrent("ZZZ", cmd_id="c-gone")
        assert mgr.web.results["c-gone"]["status"] == "error" and "不存在" in mgr.web.results["c-gone"]["error"]

        mgr.store.get("HA").state = "queuedUP"  # 排队 = qB 静默忽略
        client.calls.clear()
        cmds._cmd_reannounce_torrent("HA", cmd_id="c-blocked")
        assert mgr.web.results["c-blocked"]["status"] == "warn" and "非活跃" in mgr.web.results["c-blocked"]["error"]
        assert not any(c[0] == "reannounce" for c in client.calls), "非活跃不得发指令"
