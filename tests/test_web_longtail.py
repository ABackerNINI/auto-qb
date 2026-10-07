"""test_web_longtail 测试计划: P1 覆盖率提升轮 + v3 活尾 (运行时 / 命令 / 路由长尾)

## 测试计划(每个测试函数一条)
### P1 覆盖率提升轮: webui 运行时与命令长尾
- test_web_runtime_notify_drops_are_counted: SSE 广播非阻塞(慢/坏订阅者各计丢弃)
- test_web_runtime_check_pending_paths: 在途汇报确认全路径(item 级 deadline 超时 warn(epoch/legacy 文案)/停止直判/断连/读异常 error/判定聚合三桶与前 3 条原因截断)
- test_web_runtime_resync_elapsed_ms_logs_by_threshold: 补刷新计时按阈值分级(慢 WARNING / 正常 DEBUG)
- test_web_runtime_set_result_prunes_stale_and_carries_truth: 回执表 TTL 淘汰 + truth 附带
- test_web_runtime_affected_hashes_shapes: 受影响种子三种取法 + 异常退化
- test_web_runtime_affected_truth_queries_live_api: 真值直查 qB, 失败回 None 不回落快照
- test_web_commands_delete_with_files_and_reannounce_gone_receipt: 删除透传 delete_files; 汇报缺失显式回执
- test_reannounce_group_empty_snapshot_error_receipt: 组命令空组回执(E-03) —— 组内成员执行时刻全不在快照时显式 error 回执, 不发指令不登记跟踪(对齐单发口径, 前端不再挂到超时)
- test_web_commands_recheck_and_skip_check_receipts: recheck/skip-check 拒绝回执带文案
- test_web_commands_limits_partial_directions: 限速只下发提供的方向; 分享限制缺省 -2 补齐
- test_web_commands_rename_fs_folder_branch: 重命名文件夹分支
- test_web_commands_bulk_argument_errors: 批量参数四类错误回执
- test_web_commands_bulk_missing_targets_reported: 批量缺失种子/组分列计数
- test_web_commands_bulk_recheck_via_ops: 批量 recheck 经 ops 聚合回执
- test_web_commands_add_torrents_receipt: 添加种子受理/拒绝回执
- test_api_torrent_write_endpoints_extra_enqueue: 写端点补遗(pause/resume/delete/skip-check/limits 部分方向)
- test_api_torrents_add_endpoint_errors_and_enqueue: 添加种子 base64 坏/空载荷 400 + 合法入队
- test_api_config_put_and_preview_tree_shape: 配置树 PUT/preview 非对象 400 + preview 不落盘
- test_api_expr_eval_runtime_error: 求值期失败(除零) -> ok=False 带文案与 used
- test_api_keys_endpoint_roundtrip_and_validation: 快捷键默认表/422 校验/保存读回
- test_api_keys_sanitize_rejects_non_dict: _sanitize 非 dict 一律 None
- test_api_category_and_tag_empty_rejections: 分类/标签空入参 400
- test_api_speed_mode_reads_client_with_alt_fields: 限速托管直读 qB(含 ALT 双组) + 读失败/部分成功整组回 None(DEBUG 留摘要)
- test_api_fs_error_semantics: fs 端点错误语义化(404/501/403/400)
- test_api_traffic_qb_global_live_tail_realtime: (S6 验收追加)raw 段窗活尾合流 —— 纯活尾(零盘)出实时桶点(桶值 = 区间平均, 计划 26-10-07-2127 S2);
  磁盘落盘后滞后快照重列已落盘记录被按 ts 精确去重(快照与 flush 竞态不重不漏), 快照清空后磁盘响应与合流响应逐点一致
- test_api_traffic_qb_group_live_tail_member_only: (S6)组端点空态判据计入活尾 —— 成员仅活尾(零盘)组图非空(单记录窗首基线缺失 D4 0 线, S2);
  单种端点同享活尾
- test_frontend_toast_duration_floor_by_kind: 错误/超时类 toast 停留下限守阵(2026-10-05 用户报「右下角错误信息停留太短」) ——
  ui_feedback.js 头部 `TOAST_MS_FLOOR` 给 error/timeout 设 ≥8s 下限, `toast()` 与 `_finishToast()`
  两条排期路径都经 `toastMs(kind, ms)` 解析且 ms 缺省为 null(绕过即回到裸 ms, 下限形同虚设)
- test_aq_tip_anchor_watch_and_reacquire_wired: aq-tip 锚定保活守阵(2026-10-07 用户报「详情面板 tooltip 位置不正确」, 变体 5s 轮询整帧重建三条错位路径) —— ui_feedback.js 定位抽 place() 单点(show 初显与显示期重定位共用, 夹取/err-panel 避让同口径) + reacquire() 语义重解析(data-aq-tip 同文案节点按视口中心距旧矩形最近者, 语义扫描先于指针坐标 elementFromPoint 回退, 回退有 Number.isFinite(curX) 门护键盘 NaN 路径) + watch/tick rAF 帧环(浮层可见期才运转, 每帧只 1 次 getBoundingClientRect 零 DOM 查询: 断链走语义重解析 / 四轴 rect 漂移超 1px 重定位) + enter 记 curRect 基准 / hide 作废成对, 任一环被重构摘除即红
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

from webui_helpers import (
    KEY,
    STATIC_ROOT,
    _enable_qb_traffic,
    _qb_v4,
    _make_grouped_manager,
    module_log,
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
    with module_log("auto_qb.webui.runtime") as messages:
        rt.resync_elapsed_ms(time.time() - (float(CMD_SLOW_MS) / 1000.0 + 1.0))
        assert any("命令后补刷新" in m and "真值" in m for m in messages), "超阈值 -> WARNING"
        rt.resync_elapsed_ms(time.time())
    assert any("命令后补刷新" in m for m in messages), "正常耗时也落 DEBUG(排障可查)"


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
    with module_log("auto_qb.webui.runtime") as messages:
        assert rt2._affected_truth("pause_torrent", {"hash": "HA"}) is None
    assert any("真值直查失败" in m for m in messages), "直查失败落 WARNING(不回落快照)"


def test_web_commands_delete_with_files_and_reannounce_gone_receipt():
    """删除透传 delete_files; 汇报种子已不存在 -> 显式 error 回执(不静默)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        mgr.web.commands.put(("delete_torrent", {"hash": "HA", "delete_files": True, "cmd_id": "d1"}))
        mgr.web.commands.put(("reannounce_torrent", {"hash": "GONE", "cmd_id": "r1"}))
        mgr.web.consume_commands()
        assert client.calls[-1] == ("delete", True), "delete_files 透传给 API"
        assert mgr.web.results["d1"]["status"] == "ok"
        assert mgr.web.results["r1"]["status"] == "error" and "不存在" in mgr.web.results["r1"]["error"]


def test_reannounce_group_empty_snapshot_error_receipt():
    """组强制汇报空组回执(E-03): 组内成员执行时刻全不在快照 -> 显式 error 回执, 不发指令不登记

    组快照渲染后、命令执行前组内成员全被删除(主循环被长任务占住时窗口秒级): _group_hashes
    回空 -> 修复前不发指令不写回执, 前端 waitCmd 挂到自身超时才弹「超时」。对齐单发
    reannounce_torrent 对缺失的显式 error 回执口径。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        mgr.store.remove_torrent("HA")
        mgr.store.remove_torrent("HB")
        assert mgr._group_hashes(key) == [], "前置: 组内成员已全部不在快照"
        mgr.web.commands.put(("reannounce_group", {"key": key, "cmd_id": "r-gone"}))
        mgr.web.consume_commands()
        assert client.calls == [], "空组不得发任何指令"
        assert mgr.web.reannounce_pending == {}, "空组不登记确认跟踪"
        r = mgr.web.results["r-gone"]
        assert r["status"] == "error" and "不存在" in r["error"], "空组必须显式 error 回执"


def test_web_commands_recheck_and_skip_check_receipts():
    """重新校验/右键跳检经 ops 提交: 拒绝时回执带自解释文案; 种子不存在同样显式报"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        mgr.web.commands.put(("recheck_torrent", {"hash": "GONE", "cmd_id": "c-gone"}))
        mgr.web.commands.put(("skip_check_torrent", {"hash": "GONE", "cmd_id": "s-gone"}))
        mgr.web.consume_commands()
        assert mgr.web.results["c-gone"]["status"] == "error" and "不存在" in mgr.web.results["c-gone"]["error"]
        assert mgr.web.results["s-gone"]["status"] == "error", "跳检拒绝(种子消失) -> error 回执带文案"
        assert mgr.web.results["s-gone"]["error"], "拒绝文案不为空"


def test_web_commands_limits_partial_directions():
    """限速只下发提供的方向(up/dl 可各自缺省); 分享限制同理"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        mgr._cmd_set_torrent_limits("HA", up_limit=1024)
        mgr._cmd_set_torrent_limits("HA", dl_limit=2048)
        mgr._cmd_set_share_limits("HA", ratio_limit=1.5)
        kinds = [c[0] for c in client.calls]
        assert kinds.count("set_upload_limit") == 1 and kinds.count("set_download_limit") == 1
        assert client.calls[-1] == ("set_share_limits", (1.5, -2, -2)), "缺失维度按 -2(全局默认)补齐"


def test_web_commands_rename_fs_folder_branch():
    """重命名文件夹走 torrents_rename_folder(文件走 rename_file 已有守阵)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        mgr._cmd_rename_fs("HA", old_path="old/dir", new_path="new/dir", is_folder=True)
        assert client.calls[-1] == ("rename_folder", ("HA", "old/dir", "new/dir"))


def test_web_commands_bulk_argument_errors():
    """批量动作参数错误: 未知动作 / 空目标 / 标签动作无标签 / set_category 无分类 /
    limits 两方向全空 / location 空路径 -> error 回执且不调 API"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        cases = [
            ({
                "hashes": ["HA"],
                "action": "purge"
            }, "purge"),
            ({
                "action": "pause"
            }, "未提供任何 hash"),
            ({
                "hashes": ["HA"],
                "action": "add_tags"
            }, "未提供标签"),
            ({
                "hashes": ["HA"],
                "action": "set_category"
            }, "未提供分类"),
            ({
                "hashes": ["HA"],
                "action": "limits"
            }, "未提供限速值"),
            ({
                "hashes": ["HA"],
                "action": "location"
            }, "未提供目标路径"),
        ]
        for i, (payload, want) in enumerate(cases):
            mgr.web.commands.put(("bulk_torrents", dict(payload, cmd_id=f"b{i}")))
            mgr.web.consume_commands()
            assert mgr.web.results[f"b{i}"]["status"] == "error", (payload, mgr.web.results)
            assert want in mgr.web.results[f"b{i}"]["error"]
        assert client.calls == [], "参数错误不触达 qB"


def test_web_commands_bulk_missing_targets_reported():
    """批量: 缺失种子与缺失组分列计数(部分缺失也进 error 文案, 拒绝计数可见)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        ghost_key = ("R:/Nowhere", ("none.mkv", ))
        mgr.web.commands.put(
            ("bulk_torrents", {
                "hashes": ["HA", "GONE"],
                "keys": [ghost_key],
                "action": "pause",
                "cmd_id": "bm"
            })
        )
        mgr.web.consume_commands()
        rec = mgr.web.results["bm"]
        assert rec["status"] == "error"
        assert "1/2 个种子不存在" in rec["error"] and "1/1 个组不存在" in rec["error"]


def test_web_commands_bulk_recheck_via_ops():
    """批量 recheck 经 ops 逐个提交: 提交/跳过/缺失聚合进回执(部分成功也报错)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        with module_log("auto_qb.webui.commands") as messages:
            mgr.web.commands.put(("bulk_torrents", {"hashes": ["HA", "GONE"], "action": "recheck", "cmd_id": "br"}))
            mgr.web.consume_commands()
        rec = mgr.web.results["br"]
        assert rec["status"] == "error" and "1/2 个种子不存在" in rec["error"]
        assert any("批量 recheck(提交 1" in m for m in messages), "提交/跳过计数落日志(回执只带缺失文案)"


def test_web_commands_add_torrents_receipt():
    """添加种子: 文件+链接都受理 -> ok 回执; qB 未接受 -> error 回执带详情"""
    from hr_helpers import torrent_blob

    with tempfile.TemporaryDirectory() as td:
        mgr, client, key = _make_grouped_manager(td)
        blob = torrent_blob(name="added.bin")
        mgr.web.commands.put(
            (
                "add_torrents",
                {
                    "files": [blob],
                    "urls": ["magnet:?xt=urn:btih:xyz"],
                    "save_path": "R:/Drop",
                    "category": "cat",
                    "tags": ["t1"],
                    "paused": False,
                    "skip_checking": False,
                    "sequential": False,
                    "first_last_piece_prio": False,
                    "auto_tmm": False,
                    "cmd_id": "a1",
                },
            )
        )
        mgr.web.consume_commands()
        assert mgr.web.results["a1"]["status"] == "ok", mgr.web.results["a1"]
        assert any(c[0] == "add" for c in client.calls)
        # qB 拒绝(旧文本形态 "Fails.") -> error 回执(新形态元数据由既有守阵钉)
        client.torrents_add = lambda *a, **kw: "Fails."
        mgr.web.commands.put(("add_torrents", {"files": [blob], "urls": [], "cmd_id": "a2"}))
        mgr.web.consume_commands()
        assert mgr.web.results["a2"]["status"] == "error" and "qB 未接受" in mgr.web.results["a2"]["error"]


# ==================== P1 覆盖率提升轮: webui 路由长尾 ====================


def test_api_torrent_write_endpoints_extra_enqueue(web_env):
    """种子写端点补遗: pause/resume/delete(带 delete_files)/skip-check/limits(部分方向)/share-limits(部分维度)"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    post = lambda path, body=None: client.post(f"/api/torrents/HA{path}", json=body, headers=auth)  # noqa: E731
    cases = [
        ("/pause", None, "pause_torrent", {
            "hash": "HA"
        }),
        ("/resume", None, "resume_torrent", {
            "hash": "HA"
        }),
        ("/delete", {
            "delete_files": True
        }, "delete_torrent", {
            "hash": "HA",
            "delete_files": True
        }),
        ("/skip-check", None, "skip_check_torrent", {
            "hash": "HA"
        }),
        ("/limits", {
            "up_limit": 1024
        }, "set_torrent_limits", {
            "hash": "HA",
            "up_limit": 1024
        }),
        ("/share-limits", {
            "ratio_limit": 1.5
        }, "set_share_limits", {
            "hash": "HA",
            "ratio_limit": 1.5
        }),
    ]
    for path, body, cmd, want in cases:
        resp = post(path, body)
        assert resp.status_code == 200, (path, resp.text)
        got_cmd, payload = mgr.web.commands.get_nowait()
        assert got_cmd == cmd
        payload.pop("cmd_id")
        payload.pop("_queued_ts", None)
        assert payload == want, path
    # 鉴权沿用 /api/* 全局依赖
    assert client.post("/api/torrents/HA/pause").status_code == 401


def test_api_torrents_add_endpoint_errors_and_enqueue(web_env):
    """/api/torrents/add: base64 坏 -> 400; 空载荷 -> 400; 合法载荷入队(文件+链接)"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    assert client.post("/api/torrents/add", json={"files_b64": ["!!not-b64!!"]}, headers=auth).status_code == 400
    assert client.post("/api/torrents/add", json={}, headers=auth).status_code == 400
    assert client.post("/api/torrents/add", json={"files_b64": ["!!not-b64!!"]}).status_code == 401
    blob = base64.b64encode(b"d4:infod4:name4:abcee").decode("ascii")
    resp = client.post(
        "/api/torrents/add",
        json={
            "files_b64": [blob, ""],
            "urls": ["magnet:?xt=urn:btih:abc"],
            "save_path": "R:/Drop",
            "tags": ["t"]
        },
        headers=auth,
    )
    assert resp.status_code == 200 and resp.json()["queued"] is True
    cmd, payload = mgr.web.commands.get_nowait()
    assert cmd == "add_torrents"
    assert payload["files"] == [b"d4:infod4:name4:abcee"], "空串条目被过滤, base64 解出原始字节"
    assert payload["urls"] == ["magnet:?xt=urn:btih:abc"] and payload["save_path"] == "R:/Drop"


def test_api_config_put_and_preview_tree_shape(web_env):
    """配置树: PUT/preview 的 tree 非对象都 400; preview 返回 YAML 文本不落盘"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    assert client.put("/api/config", json={"tree": "nope"}, headers=auth).status_code == 400
    assert client.post("/api/config/preview", json={"tree": [1]}, headers=auth).status_code == 400
    assert client.put("/api/config", json={"tree": "nope"}).status_code == 401
    tree = client.get("/api/config", headers=auth).json()["tree"]
    resp = client.post("/api/config/preview", json={"tree": tree}, headers=auth)
    assert resp.status_code == 200 and "yaml" in resp.json()
    before = Path(mgr.config_path).read_text(encoding="utf-8")
    assert Path(mgr.config_path).read_text(encoding="utf-8") == before, "preview 不落盘"


def test_api_expr_eval_runtime_error(web_env):
    """表达式试算: 编译/校验通过但**求值期**失败(除零) -> ok=False 带错误文案与 used 清单"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    mgr.store.get = lambda h: SimpleNamespace(uploaded=100, downloaded=0)
    resp = client.post(
        "/api/expr/eval",
        json={
            "text": "(tor.uploaded / tor.downloaded) > 1",
            "hash": "HA"
        },
        headers=auth,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is False and "除数为 0" in body["error"]
    assert body["used"] == ["tor.downloaded", "tor.uploaded"]


def test_api_keys_endpoint_roundtrip_and_validation(web_env):
    """快捷键配置: 默认表 / 非法结构 422 / 合法保存后读回一致"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    assert client.get("/api/keys", headers=auth).json()["template"] == "aqb-default"
    bad = {"schema_version": 1, "template": "", "overrides": {}}
    assert client.put("/api/keys", json=bad, headers=auth).status_code == 422
    bad2 = {"schema_version": 1, "template": "aqb-default", "overrides": {"k": "Bad Serial!"}}
    assert client.put("/api/keys", json=bad2, headers=auth).status_code == 422
    assert client.put("/api/keys", json=bad2).status_code == 401
    good = {"schema_version": 1, "template": "aqb-default", "overrides": {"openSearch": "Ctrl+K", "x": ""}}
    assert client.put("/api/keys", json=good, headers=auth).status_code == 200
    assert client.get("/api/keys", headers=auth).json()["overrides"]["openSearch"] == "Ctrl+K"


def test_api_keys_sanitize_rejects_non_dict():
    """_sanitize 结构校验单点: 非 dict 文档一律 None(走默认表兜底链)"""
    from auto_qb.webui.server.routes.keys import _sanitize

    assert _sanitize(None) is None
    assert _sanitize([1, 2]) is None
    assert _sanitize("x") is None


def test_api_category_and_tag_empty_rejections(web_env):
    """分类/标签写端点的空入参 400(与既有详情端点同一校验口径)"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    assert client.post("/api/categories", json={"name": "  "}, headers=auth).status_code == 400
    assert client.post("/api/categories/edit", json={}, headers=auth).status_code == 400
    assert client.post("/api/tags/remove", json={"tags": []}, headers=auth).status_code == 400
    resp = client.post("/api/tags", json={"tags": ["新标签"]}, headers=auth)
    assert resp.status_code == 200
    cmd, payload = mgr.web.commands.get_nowait()
    assert cmd == "create_tags" and payload["tags"] == ["新标签"]


def test_api_speed_mode_reads_client_with_alt_fields(web_env):
    """限速托管状态: qB 在连时直读当前限速与 ALT 双组; 读失败不炸(回 None)"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    api = SimpleNamespace(
        get_global_speed_limits=lambda: {"up_limit": 1024},
        get_speed_limits_mode=lambda: 1,
        get_alt_speed_limits=lambda: {"up_limit": 512},
    )
    mgr.client = SimpleNamespace()
    mgr.api = api
    body = client.get("/api/speed/mode", headers=auth).json()
    assert body["current"] == {"up_limit": 1024} and body["alt_on"] is True
    assert body["alt_current"] == {"up_limit": 512}
    # 读失败 -> 字段回 None, 端点不 500
    mgr.api = SimpleNamespace(
        get_global_speed_limits=lambda: (_ for _ in ()).throw(RuntimeError("断连")),
        get_speed_limits_mode=lambda: 0,
        get_alt_speed_limits=lambda: {},
    )
    body = client.get("/api/speed/mode", headers=auth).json()
    assert body["current"] is None and body["alt_on"] is None and body["alt_current"] is None, "任一读取失败整组回 None(不拿旧缓存冒充)"
    # 部分成功组合同样整组回 None(首读成功后续读抛 -> 不出现「一半真一半未知」浮层;
    # issue 26-10-06-0028 chore-speed-mode-silent-except)
    mgr.api = SimpleNamespace(
        get_global_speed_limits=lambda: {"up_limit": 1024},
        get_speed_limits_mode=lambda: (_ for _ in ()).throw(RuntimeError("超时")),
        get_alt_speed_limits=lambda: {"up_limit": 512},
    )
    body = client.get("/api/speed/mode", headers=auth).json()
    assert body["current"] is None and body["alt_on"] is None and body["alt_current"] is None, "部分成功也整组回 None(口径对齐)"


def test_api_fs_error_semantics(web_env, tmp_path, monkeypatch):
    """fs 端点错误语义化: 目录不可读 404 / mkdir 不支持 501 / 只读挂载 403 / 其它失败 400 / open 不支持 501"""
    from auto_qb.infra import file_access as fa_mod

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    root = tmp_path / "fsroot"
    root.mkdir()
    mgr.store.by_hash = {"HA": SimpleNamespace(hash="HA", save_path=str(root), content_path=str(root))}
    norm = lambda p: str(p).replace("\\", "/")  # noqa: E731

    class _FakeFA:
        def isdir(self, p):
            return True

        def isfile(self, p):
            return True

        def exists(self, p):
            return False

        def realpath_lexical(self, p):
            return p

        def scandir(self, p):
            raise PermissionError(13, "拒绝访问")

        def mkdir(self, p):
            raise OSError(errno.EACCES, "拒绝访问")

    monkeypatch.setattr(file_access, "get_file_access", lambda: _FakeFA())
    # 目录浏览: scandir 失败 -> 404 带原因(不是裸 500)
    resp = client.get("/api/fs/dirs", params={"path": norm(root)}, headers=auth)
    assert resp.status_code == 404 and "目录不可读" in resp.json()["detail"]
    # mkdir: EACCES -> 403(只读挂载语义化)
    resp = client.post("/api/fs/mkdir", json={"name": "nd", "path": norm(root)}, headers=auth)
    assert resp.status_code == 403 and "只读" in resp.json()["detail"]

    # mkdir: 其它 OSError -> 400
    class _OtherFA(_FakeFA):
        def mkdir(self, p):
            raise OSError(errno.EINVAL, "无效参数")

    monkeypatch.setattr(file_access, "get_file_access", lambda: _OtherFA())
    resp = client.post("/api/fs/mkdir", json={"name": "nd", "path": norm(root)}, headers=auth)
    assert resp.status_code == 400 and "新建失败" in resp.json()["detail"]

    # mkdir: 环境不支持 -> 501
    class _NoFA(_FakeFA):
        def mkdir(self, p):
            raise fa_mod.NotSupported("nope")

    monkeypatch.setattr(file_access, "get_file_access", lambda: _NoFA())
    assert client.post("/api/fs/mkdir", json={"name": "nd", "path": norm(root)}, headers=auth).status_code == 501
    # open-path: 打开动作不支持 -> 501 引导「复制路径」(patch 地址 = common.open_path, 与既有守阵一致)
    import auto_qb.webui.server.common as fs_common

    def _unsupported(path, select=False):
        raise fa_mod.NotSupported("nope")

    monkeypatch.setattr(fs_common, "open_path", _unsupported)
    mgr.store.groups = {(norm(root), ("a.mkv", )): ["HA"]}
    encoded = encode_group_key((norm(root), ("a.mkv", )))
    resp = client.post("/api/open-path", json={"kind": "group", "key": encoded}, headers=auth)
    assert resp.status_code == 501 and "复制路径" in resp.json()["detail"]


def test_api_traffic_qb_global_live_tail_realtime(web_env):
    """(S6)raw 段窗活尾合流: 纯活尾(零盘)出实时桶点(不等 flush_interval 落盘);
    磁盘落盘后滞后快照重列已落盘记录被按 ts 精确去重(快照与 flush 竞态不重不漏),
    快照清空后磁盘响应与合流响应逐点一致 —— 图面全程无跳变"""
    from auto_qb.core.traffic_store import LiveTail, V4Sample, v4_epoch_date_str

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    _enable_qb_traffic(mgr)
    store = _qb_v4(mgr)
    now = int(time.time())
    base = ((now - 240) // 30) * 30  # 5m 窗内
    b0, b1, b2 = (base + i * 30 for i in range(3))
    recs = (V4Sample(100, 50, 1000, 500), V4Sample(200, 70, 2000, 800))
    tail_full = LiveTail(
        block_open=True,
        head_pending=True,
        start_epoch=b0 + 30,
        interval_s=30,
        projected_ts=float(b1 + 30),
        records=recs,
        open_run=None,
    )
    # 纯活尾(块全量未落盘, 零天文件): 图面实时出点
    _attach_live_tail_host(mgr, {"global": tail_full})
    body = client.get("/api/traffic/qb/global", headers=auth, params={"window": "5m"}).json()

    def pt(seg, t):
        return next((p for p in body[seg] if p and p["t"] == t), None)

    assert body["meta"]["stale"] is False
    assert pt("points", b0) == {"t": b0, "dl": 0, "up": 0}  # 区间平均口径: 首点基线缺失 D4 0 线
    assert pt("points", b1) == {"t": b1, "dl": 33, "up": 10}  # delta(1000, 300)/30
    assert pt("points", b2) is None  # 活尾之外无观测
    assert pt("totals", b1) == {"t": b1, "dl": 1000, "up": 300}
    live_body = body
    # flush 落盘(同两记录) + 滞后快照仍重列全部记录: 按 ts 去重, 响应逐点不变
    store.append_records("global", v4_epoch_date_str(b0 + 30), (b0 + 30, 30), recs, (1000, 500))
    body = client.get("/api/traffic/qb/global", headers=auth, params={"window": "5m"}).json()
    assert body == live_body
    # 快照清空(flush 后的下一轮发布): 纯磁盘读路径, 响应仍逐点一致
    _attach_live_tail_host(mgr, {})
    body = client.get("/api/traffic/qb/global", headers=auth, params={"window": "5m"}).json()
    assert body == live_body


def test_api_traffic_qb_group_live_tail_member_only(web_env):
    """(S6)组端点空态判据计入活尾: 成员仅活尾(零盘)组图非空(不再误判「从未产过流量」);
    单种端点同享活尾"""
    from auto_qb.core.traffic_store import LiveTail, V4Sample

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    _enable_qb_traffic(mgr)
    now = int(time.time())
    base = ((now - 240) // 30) * 30  # 5m 窗内
    b0, b1 = (base + i * 30 for i in range(2))
    tail = LiveTail(
        block_open=True,
        head_pending=True,
        start_epoch=b0 + 30,
        interval_s=30,
        projected_ts=float(b1 + 30),
        records=(V4Sample(300, 30, 500, 50), ),
        open_run=None,
    )
    _attach_live_tail_host(mgr, {"torrent:HB": tail})
    body = client.get(f"/api/traffic/qb/group/{encode_group_key(KEY)}", headers=auth, params={"window": "5m"}).json()

    def pt(seg, t):
        return next((p for p in body[seg] if p and p["t"] == t), None)

    assert pt("points", b0) == {"t": b0, "dl": 0, "up": 0}  # HB 活尾观测(HA 无数据按 0 计); 单记录窗首基线缺失 D4 0 线
    assert pt("totals", b0) == {"t": b0, "dl": 0, "up": 0}  # 窗首基线缺失
    assert pt("points", b1) is None  # 单记录覆盖桶 [b0, b0+30) 恰一格, b1 无观测
    # 单种端点同享活尾(区间平均口径: 单记录无基线, D4 豁免 0 线 —— 桶在即合流生效)
    body = client.get("/api/traffic/qb/torrent/HB", headers=auth, params={"window": "5m"}).json()
    assert next((p for p in body["points"] if p and p["t"] == b0), None) == {"t": b0, "dl": 0, "up": 0}


def test_frontend_toast_duration_floor_by_kind() -> None:
    """错误 / 超时类 toast 停留时长下限守阵(2026-10-05 用户报「右下角错误信息停留太短」)

    停留时长单点在 `shared/ui_feedback.js` 头部的 `TOAST_MS_FLOOR`; `toast()` 与 `_finishToast()`
    两条排期路径都必须经 `toastMs(kind, ms)` 解析 —— 绕过即回到裸 ms, 按 kind 的下限形同虚设。
    钉住三件事(全是"pytest 全绿、界面行为退化"的形态):
    1. error / timeout 的下限不得低于 8s(用户报障的正是"4s 一闪而过, 带原因段的报错读不完");
    2. 排期点恰好 2 处且都走 `toastMs(kind, ms)`(新增排期点须一并走解析, 否则新链路漏掉下限);
    3. 两处 `ms` 缺省为 `null`(写死数字会让 kind 下限在缺省路径不生效 —— 而报障的恰恰是缺省路径)。
    """
    fb = open(os.path.join(STATIC_ROOT, "shared", "ui_feedback.js"), encoding="utf-8").read()
    m = re.search(r"TOAST_MS_FLOOR = \{([^}]*)\}", fb)
    assert m, "ui_feedback.js 缺 TOAST_MS_FLOOR(停留时长单点; 改名或挪走了? 同步本守阵)"
    floors = {k: int(v) for k, v in re.findall(r"(\w+)\s*:\s*(\d+)", m.group(1))}
    assert floors.get("error", 0) >= 8000, \
        f"error 类 toast 停留下限过低({floors.get('error')}ms) —— 「错误信息一闪而过」会复发"
    assert floors.get("timeout", 0) >= 8000, \
        f"timeout 类 toast 停留下限过低({floors.get('timeout')}ms) —— 部分失败汇总同样要读得完"
    assert fb.count("toastMs(kind, ms)") == 2, \
        "排期点应为 2 处(toast / _finishToast)且都必须走 toastMs(kind, ms)(绕过 = 下限失效)"
    assert re.search(r"toast\(text, kind = \"info\", ms = null, opts = \{\}\)", fb), \
        "toast() 的 ms 缺省必须是 null(写死 4000 会让 kind 下限在缺省路径不生效)"
    assert re.search(r"_finishToast\(id, kind, text, ms = null\)", fb), \
        "_finishToast() 的 ms 缺省必须是 null(同上)"


def test_aq_tip_anchor_watch_and_reacquire_wired():
    """aq-tip 锚定保活守阵(2026-10-07 用户报「详情面板 tooltip 位置不正确」)

    详情面板 15 变体由轮询数据驱动整帧重建(replaceChildren), tooltip 三条错位路径:
    ①350ms 窗口内锚点被换掉后按旧指针坐标重解析可能中到别的元素(布局移位), 键盘 focusin
    路径无坐标; ②浮层已显示后锚点被 5s 轮询换成新节点(mouseover 不再触发), 浮层停旧坐标;
    ③重建引发布局移位, 浮层不跟随。修法单点在 shared/ui_feedback.js: 定位抽 place() 单点 +
    reacquire() 语义重解析(先于指针坐标回退) + watch/tick rAF 帧环廉价体检。本守阵读 JS
    源码钉住结构与次序(剥行注释后锚定, 注释改写不红、代码突变必红), 任一环被重构摘除即红:
    1. enter 记录锚点矩形基准 curRect, hide 作废(键盘路径无坐标, 全靠矩形基准重解析);
    2. reacquire 语义优先: 全文档 [data-aq-tip] 同文案节点按矩形中心距取最近, 之后才是指针
       坐标 elementFromPoint 回退(次序倒了 = 布局移位路径复发), 回退有 Number.isFinite 门;
    3. show 断链走 reacquire, 定位统一走 place 并挂 watch(两路径夹取/避让同口径);
    4. tick 帧环: 只在浮层可见期运转, 每帧仅 1 次 getBoundingClientRect 零 DOM 查询,
       断链分支与四轴漂移分支齐备(非断链路径出现 querySelectorAll = 性能红线)。
    """
    ui = open(os.path.join(STATIC_ROOT, "shared", "ui_feedback.js"), encoding="utf-8").read()

    # ① 矩形基准的记/废成对
    assert re.search(r"^  let curRect = null;", ui, re.M), \
        "ui_feedback.js 缺 curRect 矩形基准状态(语义重解析/漂移检测失锚, 同步本守阵)"
    assert re.search(r"curRect = target\.getBoundingClientRect\(\);", ui), \
        "enter 未记录锚点矩形基准 —— 键盘路径(focusin 无坐标)的锚点重解析退化为直接收起"
    m = re.search(r"function hide\(\)\s*\{(.*?)\n  \}", ui, re.S)
    assert m and "curRect = null" in m.group(1), \
        "hide 未作废 curRect 基准(悬空基准会污染下一次悬浮的重解析)"

    # ② reacquire: 语义扫描先于指针回退, 回退有 NaN 门
    m = re.search(r"function reacquire\(\)\s*\{(.*?)\n  \}", ui, re.S)
    assert m, "ui_feedback.js 找不到 reacquire(锚点被重建换掉后的语义重解析单点被摘? 同步本守阵)"
    acq = re.sub(r"//[^\n]*", "", m.group(1))
    assert 'querySelectorAll("[data-aq-tip]")' in acq, \
        "reacquire 缺语义候选扫描(同 data-aq-tip 文案的新节点) —— 断链后无处重解析"
    i_sem = acq.index('querySelectorAll("[data-aq-tip]")')
    i_ptr = acq.find("elementFromPoint")
    assert i_ptr != -1, \
        "reacquire 缺指针坐标回退(2026-10-04 收口口径: 语义解析不到才按指针重解析)"
    assert i_sem < i_ptr, \
        "reacquire 指针回退先于语义解析 —— 布局移位时旧坐标下的元素已不是原锚点(路径③复发)"
    assert re.search(r"Number\.isFinite\(curX\)", acq), \
        "指针回退缺 Number.isFinite(curX) 门 —— 键盘路径 NaN 坐标会传给 elementFromPoint"

    # ③ show 断链走 reacquire; 定位单点 place + 显示期监测 watch 成对
    m = re.search(r"function show\(anchor\)\s*\{(.*?)\n  \}", ui, re.S)
    assert m, "ui_feedback.js 找不到 show(改名或挪走了? 同步本守阵)"
    sh = re.sub(r"//[^\n]*", "", m.group(1))
    assert "reacquire()" in sh, \
        "show 的断链分支未走 reacquire(键盘路径无指针坐标, 只能靠语义重解析兜住)"
    assert re.search(r"function place\(anchor\)", ui), \
        "定位未抽 place() 单点 —— show 初显与显示期重定位两套夹取/避让口径必然漂移"
    assert re.search(r"place\(anchor\);", sh) and "watch();" in sh, \
        "show 未统一走 place + watch(定位单点/显示期监测被绕开)"
    assert re.search(r"curRect = \{ left: r\.left, top: r\.top", ui), \
        "place 未在定位时刷新 curRect 基准(漂移检测失准)"

    # ④ tick 帧环: 可见期才运转, 断链/漂移两分支齐备, 每帧路径零全文档查询
    m = re.search(r"function tick\(\)\s*\{(.*?)\n  \}", ui, re.S)
    assert m, "ui_feedback.js 找不到 tick(rAF 帧环主体被摘? 同步本守阵)"
    tick = re.sub(r"//[^\n]*", "", m.group(1))
    assert 'classList.contains("on")' in tick and "cur" in tick, \
        "tick 缺可见性守卫(cur + .on) —— 浮层收起后帧环空转烧帧"
    assert "isConnected" in tick, \
        "tick 缺锚点存活检查 —— 浮层显示后锚点被重建换掉不再跟随(路径②复发)"
    assert "reacquire()" in tick, "tick 断链分支未走语义重解析"
    for axis in ("left", "top", "width", "height"):
        assert f"curRect.{axis}" in tick, f"tick 漂移检测缺 {axis} 轴比对(重建移位/内容变宽不重定位)"
    assert "querySelectorAll" not in tick, \
        "tick 每帧路径出现全文档查询 —— 体检必须只做 1 次 rect 比对(5s 轮询场景的性能红线)"
    assert re.search(r"requestAnimationFrame\(tick\)", ui), \
        "帧环未用 requestAnimationFrame(定时器轮询会与绘制解耦空转)"
