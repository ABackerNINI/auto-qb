"""test_web_longtail_runtime 测试计划: P1 覆盖率提升轮 + v3 活尾 (运行时 / 命令 / 路由长尾)

## 测试计划(每个测试函数一条)
### P1 覆盖率提升轮: webui 运行时与命令长尾
- test_web_runtime_notify_drops_are_counted: SSE 广播非阻塞(慢/坏订阅者各计丢弃)
- test_web_runtime_check_pending_paths: 在途汇报确认全路径(item 级 deadline 超时 warn(epoch/legacy 文案)/停止直判/断连/读异常 error/判定聚合三桶与前 3 条原因截断)
- test_web_runtime_resync_elapsed_ms_logs_by_threshold: 补刷新计时按阈值分级(慢 WARNING / 正常 DEBUG)
- test_web_runtime_set_result_prunes_stale_and_carries_truth: 回执表 TTL 淘汰 + truth 附带
- test_web_runtime_affected_hashes_shapes: 受影响种子三种取法 + 异常退化
- test_web_runtime_affected_truth_queries_live_api: 真值直查 qB, 失败回 None 不回落快照
### T2a 覆盖率第三轮: runtime_commands / Stream 防御弧
- test_web_runtime_consume_unknown_cmd_writes_error_receipt: 未知命令 KeyError 分流 —— cmd_id 在场时写 error 回执(文案含「未知命令」), 本批不改状态
- test_web_runtime_check_pending_storeless_and_background_reads: check_pending 无 store 宿主(判空跳过快照直判走判定链聚合 ok) + 后台核实读失败 DEBUG 保留条目 + 非终态结论条目保留
- test_web_runtime_affected_truth_skips_foreign_rows: 真值直查逐行过滤 —— qB 返回窗口外的行不进 truth
- test_web_runtime_unsubscribe_unknown_queue_noop: 退订未订阅队列静默 no-op(订阅计数不变)
"""

import base64

import errno

import os

import re

import tempfile

import time

from pathlib import Path

from types import SimpleNamespace

from auto_qb.infra import file_access

from auto_qb.infra.utils import encode_group_key

from auto_qb.webui.runtime import (
    CMD_SLOW_MS,
    EVENT_QUEUE_MAX,
    REANNOUNCE_CONFIRM_TIMEOUT,
    WEB_RESULT_MAX,
    WEB_RESULT_TTL,
    WebUIRuntime,
)

from helpers import capture_logs

from webui_helpers import (
    KEY,
    STATIC_ROOT,
    _enable_qb_traffic,
    _qb_v4,
    _make_grouped_manager,
    _attach_live_tail_host,
)


def test_web_runtime_notify_drops_are_counted():
    """SSE 广播非阻塞: 慢消费者(队列满)与坏消费者(异常)各计一次丢弃, 不影响其它订阅者"""
    from auto_qb.webui.runtime import EVENT_QUEUE_MAX

    mgr = SimpleNamespace()  # notify 不读 host
    rt = WebUIRuntime(mgr)
    slow = rt.subscribe()  # 有界队列: 灌满即丢
    broken = rt.subscribe()
    broken.put_nowait = lambda ev: (_ for _ in ()).throw(RuntimeError("坏订阅者"))  # 每次都炸
    good = rt.subscribe()
    for _ in range(EVENT_QUEUE_MAX):
        slow.put_nowait({"type": "x", "payload": {}, "ts": 0.0})
    assert rt.subscriber_count() == 3
    hit = rt.notify("state", {"v": 1})
    assert hit == 1, "只有健康订阅者送达"
    assert rt.notify_dropped == 2, "队列满 + 异常各记一次丢弃"
    assert good.qsize() == 1


def test_web_runtime_check_pending_paths():
    """在途汇报确认全路径(item 级 deadline): 完成跳过/超时 warn(epoch+legacy 文案)/停止直判/断连等待/
    读 tracker 异常 error/判定 confirmed 与 rejected/聚合三桶与前 3 条原因截断"""
    from auto_qb.core.qbmanager import QbManager
    from auto_qb.webui.commands import RC_FAIL_PREFIX

    verdicts = {"H_OK": ("confirmed", ""), "H_FAIL": ("rejected", RC_FAIL_PREFIX + "ann"), "H_WAIT": ("", "")}
    client = SimpleNamespace(
        torrents_trackers=lambda h: (_ for _ in ()).throw(RuntimeError("读取失败")) if h == "H_ERR" else [h]
    )
    store = SimpleNamespace(
        get=lambda h: SimpleNamespace(state_enum=SimpleNamespace(is_stopped=True)) if h == "H_STOP" else None
    )
    host = SimpleNamespace(
        client=client,
        store=store,
        _verdict_reannounce=lambda trackers, baseline, **kw: verdicts.get(trackers[0], ("", "")),
    )
    rt = WebUIRuntime(host)
    now = time.time()

    def _item(**over):
        it = {
            "done": False,
            "status": "",
            "reason": "",
            "baseline": {},
            "epoch_mode": True,
            "t0": now,
            "deadline": now + REANNOUNCE_CONFIRM_TIMEOUT,
        }
        it.update(over)
        return it

    rt.reannounce_pending["c1"] = {
        "items":
            {
                "H_DONE": _item(done=True, status="warn", reason="未确认: 种子已停止"),
                "H_OK": _item(),
                "H_FAIL": _item(),
                "H_WAIT": _item(),
                "H_ERR": _item(),
                "H_STOP": _item(),
            },
    }
    rt.reannounce_pending["c_timeout"] = {"items": {"H_T": _item(deadline=now - 1.0)}}
    rt.reannounce_pending["c_timeout_legacy"] = {"items": {"H_TL": _item(deadline=now - 1.0, epoch_mode=False)}}
    rt.reannounce_pending["c_disconnected"] = {"items": {"H_D": _item()}}
    rt.check_pending()
    # 超时 -> warn「未确认」(epoch/legacy 两文案), 不再判「失败」
    assert rt.results["c_timeout"]["status"] == "warn" and "未确认: 30s" in rt.results["c_timeout"]["error"]
    assert rt.results["c_timeout_legacy"]["status"] == "warn"
    assert "旧版 qB 无 epoch 字段" in rt.results["c_timeout_legacy"]["error"]
    # 仍在进行(无证据)的条目: 不出结论, 条目留在途; 其余已定论的先记进条目
    assert "c1" in rt.reannounce_pending, "确认未决不出结论"
    items = rt.reannounce_pending["c1"]["items"]
    assert items["H_OK"]["status"] == "ok" and items["H_FAIL"]["status"] == "error"
    assert items["H_FAIL"]["reason"] == RC_FAIL_PREFIX + "ann"
    assert items["H_STOP"]["status"] == "warn" and "种子已停止" in items["H_STOP"]["reason"], "store 快照 stopped 直判"
    assert items["H_ERR"]["done"] is True and "读取失败" in items["H_ERR"]["reason"]
    # 断连: client None -> 本轮跳过(等恢复), 保持在途
    host.client = None
    rt.check_pending()
    assert "c_disconnected" in rt.reannounce_pending, "断连不判失败, 等恢复继续确认"
    # 最后一个未决出结论 -> 聚合三桶(任一 error -> error; 原因截断为前 3 条)
    host.client = client
    verdicts["H_WAIT"] = ("confirmed", "")
    verdicts["H_D"] = ("rejected", RC_FAIL_PREFIX + "ann")  # 同 tick 断连条目恢复, 出拒绝结论
    rt.check_pending()
    assert "c1" not in rt.reannounce_pending, "全部种子出结论后聚合并移除"
    r = rt.results["c1"]
    assert r["status"] == "error", "任一 error -> 聚合 error"
    assert "成功 2, 失败 2, 未确认 2" in r["error"], "三桶计数按 item status 分流"
    assert r["error"].count(";") == 2, "原因截断为前 3 条"
    assert rt.results["c_disconnected"]["status"] == "error", "断连恢复后出结论的失败项照常聚合"
    assert rt.results["c_disconnected"]["error"] == "成功 0, 失败 1, 未确认 0: " + RC_FAIL_PREFIX + "ann"
    # 单条确认成功 -> ok 回执, 跟踪清空
    rt2 = WebUIRuntime(
        SimpleNamespace(
            client=SimpleNamespace(torrents_trackers=lambda h: ["H_D"]),
            store=SimpleNamespace(get=lambda h: None),
            _verdict_reannounce=lambda trackers, baseline, **kw: ("confirmed", ""),
        )
    )
    rt2.reannounce_pending["c_ok"] = {"items": {"H_D": _item()}}
    rt2.check_pending()
    assert rt2.results["c_ok"]["status"] == "ok" and rt2.reannounce_pending == {}


def test_web_runtime_resync_elapsed_ms_logs_by_threshold():
    """命令后补刷新计时: 异常慢升 WARNING, 正常只 DEBUG(不刷满日志)"""
    rt = WebUIRuntime(SimpleNamespace())
    with capture_logs("auto_qb.webui.runtime") as cap:
        rt.resync_elapsed_ms(time.time() - (float(CMD_SLOW_MS) / 1000.0 + 1.0))
        assert any("命令后补刷新" in m and "真值" in m for m in cap.messages), "超阈值 -> WARNING"
        rt.resync_elapsed_ms(time.time())
    assert any("命令后补刷新" in m for m in cap.messages), "正常耗时也落 DEBUG(排障可查)"


def test_web_runtime_set_result_prunes_stale_and_carries_truth():
    """回执表: 超量时按 TTL 淘汰旧回执; truth 附带进回执供前端撤乐观态"""
    rt = WebUIRuntime(SimpleNamespace())
    now = time.time()
    for i in range(WEB_RESULT_MAX + 8):
        rt.results[f"stale{i}"] = {"status": "ok", "error": "", "ts": now - WEB_RESULT_TTL - 10.0}
    rt.results["fresh"] = {"status": "ok", "error": "", "ts": now}
    rt.set_result("new1", "ok", truth={"HA": {"kind": "seeding"}})
    assert "new1" in rt.results
    assert rt.results["new1"]["truth"] == {"HA": {"kind": "seeding"}}
    assert all(k.startswith("stale") is False or k == "fresh" for k in rt.results), "过期回执被清理"
    assert len(rt.results) <= WEB_RESULT_MAX


def test_web_runtime_affected_hashes_shapes():
    """受影响种子的三种取法(单种子 / 组 / 批量含组键) + 异常退化空表"""
    host = SimpleNamespace(store=SimpleNamespace(groups={("R:/X", ("a.mkv", )): ["HA", "HB"]}))
    rt = WebUIRuntime(host)
    assert rt._affected_hashes("pause_torrent", {"hash": "HA"}) == ["HA"]
    assert rt._affected_hashes("pause_torrent", {}) == [], "无 hash 不猜"
    assert rt._affected_hashes("pause_group", {"key": ("R:/X", ("a.mkv", ))}) == ["HA", "HB"]
    assert rt._affected_hashes("bulk_torrents", {
        "hashes": ["HC"],
        "keys": [("R:/X", ("a.mkv", ))]
    }) == ["HC", "HA", "HB"]
    broken = SimpleNamespace(store=None)
    assert WebUIRuntime(broken)._affected_hashes("pause_group", {"key": "k"}) == [], "桩/异常配置退化空表"


def test_web_runtime_affected_truth_queries_live_api():
    """真值直查 qB(不读同步快照); 查不到回 None(不回落旧值伪装)"""
    torrent = SimpleNamespace(hash="HA")
    host = SimpleNamespace(
        api=SimpleNamespace(torrents_info=lambda torrent_hashes=None: [torrent]),
        state_kind=lambda t: "seeding",
    )
    rt = WebUIRuntime(host)
    truth = rt._affected_truth("pause_torrent", {"hash": "HA"})
    assert truth == {"HA": {"kind": "seeding"}}
    assert rt._affected_truth("pause_torrent", {}) is None, "无受影响种子 -> None"

    def boom(torrent_hashes=None):
        raise RuntimeError("qB 断了")

    rt2 = WebUIRuntime(SimpleNamespace(api=SimpleNamespace(torrents_info=boom), state_kind=lambda t: "x"))
    with capture_logs("auto_qb.webui.runtime") as cap:
        assert rt2._affected_truth("pause_torrent", {"hash": "HA"}) is None
    assert any("真值直查失败" in m for m in cap.messages), "直查失败落 WARNING(不回落快照)"


def test_web_runtime_consume_unknown_cmd_writes_error_receipt():
    """未知命令 KeyError 分流: cmd_id 在场 -> 写 error 回执(文案含「未知命令」), 不改种子状态"""
    rt = WebUIRuntime(SimpleNamespace(_web_command_handlers=lambda: {}))
    rt.commands.put(("no_such_cmd", {"cmd_id": "cx", "x": 1}))
    assert rt.consume_commands() is False, "未知命令不属 RESYNC_COMMANDS, 不算改状态"
    rec = rt.results["cx"]
    assert rec["status"] == "error" and "未知命令" in rec["error"], rec


def test_web_runtime_check_pending_storeless_and_background_reads():
    """check_pending 无 store 宿主与后台核实读路径: store 判空跳过快照直判(走判定链聚合 ok);
    后台核实读 tracker 失败 -> DEBUG 后条目保留; 判定非终态(断连无结论)条目同样保留"""
    now = time.time()

    def _item(**over):
        it = {
            "done": False,
            "status": "",
            "reason": "",
            "baseline": {},
            "epoch_mode": True,
            "t0": now,
            "deadline": now + REANNOUNCE_CONFIRM_TIMEOUT,
        }
        it.update(over)
        return it

    # a) 宿主没有 store 属性(getattr 判空) -> 快照直判段跳过, 直接走判定链 -> 聚合 ok
    host = SimpleNamespace(
        client=SimpleNamespace(torrents_trackers=lambda h: ["T"]),
        _verdict_reannounce=lambda trackers, baseline, **kw: ("confirmed", ""),
    )
    rt = WebUIRuntime(host)
    rt.reannounce_pending["c1"] = {"items": {"HA": _item()}}
    rt.check_pending()
    assert rt.results["c1"]["status"] == "ok" and rt.reannounce_pending == {}

    # b) 后台核实: 判定读 tracker 抛异常 -> DEBUG 落日志, 条目保留(不误删等恢复)
    def boom(h):
        raise RuntimeError("读取失败")

    rt2 = WebUIRuntime(
        SimpleNamespace(client=SimpleNamespace(torrents_trackers=boom), _verdict_reannounce=lambda *a, **kw: ("", ""))
    )
    rt2.reannounce_background["HB"] = {"min_e": now - 1.0, "baseline": {}, "t0": now}
    with capture_logs("auto_qb.webui.runtime") as cap:
        rt2.check_pending()
    assert "HB" in rt2.reannounce_background, "读失败不出结论, 条目保留"
    assert any("推迟汇报后台核实读取失败" in m for m in cap.messages), "读失败只落 DEBUG"

    # c) 后台核实: 判定非终态(client 断连回空结论) -> 两个终态分支都不进, 条目保留
    rt3 = WebUIRuntime(SimpleNamespace(client=None, _verdict_reannounce=lambda *a, **kw: ("", "")))
    rt3.reannounce_background["HC"] = {"min_e": now - 1.0, "baseline": {}, "t0": now}
    rt3.check_pending()
    assert "HC" in rt3.reannounce_background, "无结论条目留在途, 等下一拍"


def test_web_runtime_affected_truth_skips_foreign_rows():
    """真值直查逐行过滤: qB 返回里窗口外的 hash 行不进 truth(390 判据)"""
    mine = SimpleNamespace(hash="HA")
    foreign = SimpleNamespace(hash="HZ")
    host = SimpleNamespace(
        api=SimpleNamespace(torrents_info=lambda torrent_hashes=None: [foreign, mine]),
        state_kind=lambda t: "seeding",
    )
    rt = WebUIRuntime(host)
    assert rt._affected_truth("pause_torrent", {"hash": "HA"}) == {"HA": {"kind": "seeding"}}


def test_web_runtime_unsubscribe_unknown_queue_noop():
    """退订未订阅的队列: 静默 no-op, 订阅计数不变(36 假分支)"""
    import queue as _queue

    rt = WebUIRuntime(SimpleNamespace())
    kept = rt.subscribe()
    stranger = _queue.Queue()
    rt.unsubscribe(stranger)
    assert rt.subscriber_count() == 1 and rt._subscribers == [kept]
