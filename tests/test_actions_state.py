"""test_actions_state 测试计划: rules/actions 动作插件执行语义

## 测试计划(每个测试函数一条)
- test_start_stop_idempotent: 开始/停止动作幂等(重复执行不报错)
- test_stop_preserves_completeness: 暂停/恢复**不再**合成回写 state(A 系 26-10-13-0540 S1)——动作后快照不变, 完成位不可能被写坏(该类 bug 结构性消失)
- test_pause_resume_no_same_tick_writeback: 契约变更(A 系 S1, 原 26-10-06-0028 A-04 守阵方向翻面)——QbApi pause/resume 不再写后同步 store 快照, 同 tick 读到旧值
- test_start_stop_idempotent_within_same_tick: 同 tick 二次 stop/start 被 own_writes 意图标记拦下(A2), 且不写任何假 state 值
- test_move_to: 移动保存路径动作
- test_reannounce: 重新 announce 动作
- test_speed_limit_actions: 限速动作(下载/上传/全局)
- test_has_reference_filelist_states: filelist 谓词两态 —— 有参考/无参考/带标候选排除/verified
  并集命中(含排除自身)
- test_has_reference_piecehashes_shortcircuit: piecehashes 首个匹配提前返回(后续候选不再拉取)/
  无匹配/带标候选不询问
- test_has_reference_piecehashes_cand_error: piecehashes 候选拉取异常 -> 忽略候选; 目标拉取失败 -> 无参考
- test_has_reference_custom_shortcircuit: custom 首个通过提前返回短路(后续候选不再请求)/全不通过
- test_run_custom_check_error: custom 程序执行异常 -> 视为非参考
- test_speed_limit_fmt_bytes: 小值限速格式化为 B/s
- test_start_stop_dry_run: start/stop dry-run (P2-a)
- test_move_to_dry_run: move_to dry-run (P2-a)
- test_speed_limit_dry_run_manual_and_same_value_skips: 限速 dry-run / 手动限速不覆盖 / 同值不重设 (P2-a)
- test_print_details_missing_torrent: print_torrent_details 种子不存在 -> fail (P2-a)
- test_checking_disabled_segment_skips: checking 未启用段 -> skip 有/无参考两指代 (P2-a)
- test_actions_torrent_hash_scope: 各动作下发 qB 的 torrent_hashes 恒为本种子 hash(置 None = 全库副作用)
- test_actions_expand_tracker_vars: ${required_seeding_time} 经 tracker_conf 展开(remove_tags/add_category)
- test_move_to_confirm_gate_skips: 整组迁移 confirm 形态只回 skip 且规则侧 confirm=False
- test_speed_limit_direction_uses_own_axis: 上传/下载限速各读自己的轴做手动限速闸门
- test_start_stop_gate_ignores_group_members_own_write: C31 守阵 —— 起停幂等门只判本 hash
  (group=False), 兄弟成员的自写不得误伤
- test_print_details_numeric_fields: C46 守阵 —— 进度/分享率/做种时长有值精确、None 显示 "-" 且仍 ok
- test_print_details_non_empty_fields_not_replaced_by_dash: C47 守阵 —— 非空字段不得被 `and "-"` 恒替换
- test_print_details_size_fields_formatted: C51 守阵 —— 大小/上传/下载走 fmt_size 真实值(不得传 None)
- test_print_details_line_contains_all_fields: C55 守阵 —— detail 整行不得被置 None
- test_print_details_emits_exactly_one_info_line: C56 守阵 —— logger.info 不得被置 None(有且仅一行)
- test_actions_registry_complete
"""

import os

import tempfile

from unittest.mock import patch

from auto_qb.rules.base import ActionResult, Rule, VERDICT_EXECUTED, VERDICT_RETRY

from auto_qb.rules.actions import (
    AddCategoryAction,
    AddTagsAction,
    CheckAction,
    DownloadSpeedLimitAction,
    MoveToAction,
    ReannounceAction,
    RemoveCategoryAction,
    RemoveTagsAction,
    StartAction,
    StopAction,
    UploadSpeedLimitAction,
)

from helpers import capture_logs, drive_skip, FakeClient, FakeTorrent, make_ctx, make_manager, seed_store

from actions_support import (
    _check_action,
    _run_action,
    _seg,
)


def test_actions_registry_complete():
    """全部内置动作已注册(锁定名称清单): 防新增模块漏 import 到 actions/__init__ 致 config 校验拒绝合法动作名"""
    from auto_qb.rules import registry
    assert set(registry.ACTIONS) == {
        "add_tags",
        "remove_tags",
        "add_category",
        "remove_category",
        "start",
        "stop",
        "checking",
        "move_to",
        "reannounce",
        "upload_speed_limit",
        "download_speed_limit",
        "print_torrent_details",
    }


def test_start_stop_idempotent():
    """start/stop 幂等: 已开始/已停止 skip"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        # start: stalledUP 已开始 -> skip; pausedUP -> start
        tor = FakeTorrent(state="stalledUP")
        ctx = make_ctx(mgr, tor, client)
        assert StartAction("").execute(ctx).is_skipped
        tor.state = "pausedUP"
        assert StartAction("").execute(ctx).is_ok
        assert ("start", None) in client.calls
        # stop: pausedUP 已停止 -> skip; stalledUP -> stop
        # 注意: !A 系 26-10-13-0540 S1 起 start/stop **不再回写快照**(state 只由 qB 同步驱动),
        # 故此处显式复位不再是为了抵消写回副作用, 只是把种子置回待测的暂停态
        tor.state = "pausedUP"
        assert StopAction("").execute(ctx).is_skipped
        tor.state = "stalledUP"
        # !A 系 S3(A2): 上面的 start 已登记 own_writes, 本例手工把 state 改成"运行中"等价于
        #   **已回流**的形态, 故同步清掉登记再测 stop; 生产里「同 tick 内 start 后再 stop」由
        #   传统判据拦下(快照不动 ⇒ is_stopped 仍为真 ⇒ skip「已停止」), 轮不到幂等门。
        mgr.store.own_writes.clear()
        assert StopAction("").execute(ctx).is_ok
        assert ("stop", None) in client.calls


def test_stop_preserves_completeness():
    """暂停/恢复**不再**由客户端合成回写 state(A 系 26-10-13-0540 S1)

    历史: 修复前 `QbApi.torrents_stop` 硬编码 `state="pausedUP"`、`torrents_start` 硬编码
    `"stalledUP"` —— 停一个**正在下载**的种子会被记成"已完成 + 上传", `is_complete` 变真,
    可能误触下载冲突与缺文件分组分支。S1 起该合成回写整段删除(state 只由 qB 同步驱动)⇒
    **这一类「完成位被写坏」的 bug 结构性消失**。本守阵改钉新契约: 动作后快照**逐字不变**,
    不产生任何合成值; 「暂停位/完成位」的真值语义由替身真值与下一轮同步承担。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()

        # 未完成且下载中: 停不改写快照(此前会被合成写成 pausedDL)
        # !各标的取不同 hash: A 系 S3(A2)起动作会登记 own_writes, 同 hash 会互相触发幂等门
        tor = FakeTorrent(hash="HA", state="downloading", downloaded=10 * 1024**2, total_size=100 * 1024**2)
        ctx = make_ctx(mgr, tor, client)
        assert StopAction("").execute(ctx).is_ok
        assert tor.state == "downloading", f"动作不再合成 state(A 系): {tor.state}"
        assert tor.state_enum.is_complete is False, "完成位不可能被写坏(无回写)"

        # 未完成且已暂停: 起不改写快照(此前会被合成写成 stalledDL)
        tor2 = FakeTorrent(hash="HB", state="pausedDL", downloaded=10 * 1024**2, total_size=100 * 1024**2)
        ctx2 = make_ctx(mgr, tor2, client)
        assert StartAction("").execute(ctx2).is_ok
        assert tor2.state == "pausedDL", f"动作不再合成 state(A 系): {tor2.state}"
        assert tor2.state_enum.is_complete is False

        # 已完成做种: 同理, 动作不改写快照
        tor3 = FakeTorrent(hash="HC", state="uploading", downloaded=100 * 1024**2, total_size=100 * 1024**2)
        ctx3 = make_ctx(mgr, tor3, client)
        assert StopAction("").execute(ctx3).is_ok
        assert tor3.state == "uploading", tor3.state
        assert tor3.state_enum.is_complete is True


def test_pause_resume_no_same_tick_writeback():
    """契约变更(A 系 26-10-13-0540 S1): QbApi pause/resume **不再**写后同步 store 快照

    原守阵为 26-10-06-0028 (A-04) `test_pause_resume_sync_store_snapshot`: 断言「写后同 tick
    读 is_paused 为新值」。S1 起该写后同步整段删除 —— 断言方向**正好翻面**: 同 tick 读到的是
    **旧值**(不新鲜), 真值须等下一轮同步。这不是回归而是刻意的源无关契约: 自家停/起与外部
    变更一视同仁, 快照严格等于最近一次同步的应用结果(真值落地的守阵在 test_sync)。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()

        # 未完成下载中: pause/resume 均不改写快照
        tor = FakeTorrent(state="downloading", downloaded=10 * 1024**2, total_size=100 * 1024**2)
        make_ctx(mgr, tor, client)  # tor 即 store 记录(对象身份直写)
        mgr.api.torrents_pause(tor.hash)
        assert tor.state == "downloading", f"同 tick 不应出现合成值(A 系): {tor.state}"
        assert tor.state_enum.is_paused is False, "同 tick 读到旧值(不新鲜)"
        mgr.api.torrents_resume(tor.hash)
        assert tor.state == "downloading", f"同 tick 不应出现合成值(A 系): {tor.state}"
        assert tor.state_enum.is_paused is False

        # 已完成做种: 同样不改写快照
        tor2 = FakeTorrent(state="uploading", downloaded=100 * 1024**2, total_size=100 * 1024**2)
        make_ctx(mgr, tor2, client)
        mgr.api.torrents_pause(tor2.hash)
        assert tor2.state == "uploading" and tor2.state_enum.is_complete is True
        mgr.api.torrents_resume(tor2.hash)
        assert tor2.state == "uploading" and tor2.state_enum.is_complete is True

        # 透传语义不变: 客户端侧仍收到 pause/resume 调用(替身真值亦已翻转, 见 S0-P3)
        assert ("pause", tor.hash) in client.calls and ("resume", tor.hash) in client.calls


def test_start_stop_idempotent_within_same_tick():
    """守阵(A 系 S3 I1): 同 tick 二次 stop/start 被 own_writes 意图标记拦下, 且不写任何假 state 值

    A 系删回写后同 tick 的 is_stopped 仍是旧值 ⇒ 第二次同类动作会重发一次请求(qB 侧幂等、无功能
    错误, 只是重复 HTTP 与日志噪声)。可选件 A2 用**意图标记**补回幂等: 只登记「刚发过停/起」,
    不写任何假 state 值(那正是 R1–R6 的来源)。
    红验: 用假值实现幂等(如回写 pausedUP) -> 「快照逐字不变」红; 去掉幂等门 -> 第二次不再 skip 红。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        # 快照记录与客户端真值**分离**: 替身翻真值而快照不动, 才是 A 系同 tick 的真实形态
        rec = FakeTorrent(hash="HA", state="stalledUP", progress=1.0)
        client.torrents["HA"] = FakeTorrent(hash="HA", state="stalledUP", progress=1.0)
        ctx = make_ctx(mgr, rec, client)

        assert StopAction("").execute(ctx).is_ok, "首次 stop 应执行"
        assert client.calls.count(("stop", None)) == 1
        assert rec.state == "stalledUP", "动作后快照逐字不变(不写假 state 值)"

        r2 = StopAction("").execute(ctx)
        assert r2.is_skipped, f"同 tick 二次 stop 应被意图标记拦下: {r2}"
        assert client.calls.count(("stop", None)) == 1, "不应重复下发"
        assert rec.state == "stalledUP", "让位路径同样不写假值"

        # 登记清除(模拟回流)后恢复执行: 证明是 deferral 而非永久拒绝
        mgr.store.own_writes.clear()
        rec.state = "pausedUP"  # 回流后快照落真值
        assert StartAction("").execute(ctx).is_ok, "回流后 start 应执行"
        assert client.calls.count(("start", None)) == 1
        r3 = StartAction("").execute(ctx)
        assert r3.is_skipped, f"同 tick 二次 start 应被拦下: {r3}"
        assert client.calls.count(("start", None)) == 1, "不应重复下发"


def test_move_to():
    """移动种子: path 空 fail/正常移动"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(), client)
        assert MoveToAction({"path": ""}).execute(ctx).is_failed
        assert MoveToAction({"path": r"R:\New"}).execute(ctx).is_ok
        assert ("set_location", r"R:\New") in client.calls


def test_reannounce():
    """强制汇报 tracker: 最小间隔限频 + 暂停种子跳过 + dry-run 不调用不记录时间戳"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        tor = FakeTorrent()
        ctx = make_ctx(mgr, tor, client)
        assert ReannounceAction("").execute(ctx).is_ok
        assert ("reannounce", None) in client.calls
        # 最小间隔内重复: 跳过(运行时限频, 独立于 execute_once)
        assert ReannounceAction("").execute(ctx).is_skipped
        assert client.calls.count(("reannounce", None)) == 1
        # 超过最小间隔: 再次执行
        mgr.state["reannounce_ts"][tor.hash] -= ReannounceAction.MIN_INTERVAL + 1
        assert ReannounceAction("").execute(ctx).is_ok
        assert client.calls.count(("reannounce", None)) == 2
        # 暂停种子: 跳过(无需汇报)
        paused = FakeTorrent(hash="H2", state="pausedUP")
        ctx2 = make_ctx(mgr, paused, client)
        assert ReannounceAction("").execute(ctx2).is_skipped
        assert client.calls.count(("reannounce", None)) == 2
        # dry-run: 不调用、不记录时间戳
        ctx3 = make_ctx(mgr, FakeTorrent(hash="H3"), client, dry_run=True)
        assert ReannounceAction("").execute(ctx3).is_ok
        assert client.calls.count(("reannounce", None)) == 2
        assert "H3" not in mgr.state.get("reannounce_ts", {})


def test_speed_limit_actions():
    """限速动作: 上传/下载限速解析与调用"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(), client)
        r = UploadSpeedLimitAction("1000KiB/s").execute(ctx)
        assert r.is_ok
        assert ("set_upload_limit", 1000 * 1024) in client.calls
        r2 = DownloadSpeedLimitAction("2MiB/s").execute(ctx)
        assert r2.is_ok
        assert ("set_download_limit", 2 * 1024**2) in client.calls


def _grouped_mgr(state_file, hashes):
    """构造已归组 manager: store 分组结构 + 快照齐全(store.apply 已删, 用 seed_store 灌快照)"""
    mgr = make_manager(state_file)
    mgr.store.groups[("KEY", )] = list(hashes)
    for h in hashes:
        mgr.store.member_to_key[h] = ("KEY", )
    seed_store(mgr, list(hashes.values()))
    return mgr


def test_has_reference_filelist_states():
    """checking: filelist 谓词两态 —— 有参考 True; 带标候选排除; verified 并集命中组内未带标成员"""
    with tempfile.TemporaryDirectory() as td:
        me = FakeTorrent(hash="H1", name="T", state="pausedDL", progress=0.5, tags="")
        normal = FakeTorrent(hash="H2", name="N", state="stalledUP", tags="")
        tagged = FakeTorrent(hash="H3", name="K", state="stalledUP", tags="zSkipChecked")
        verified = FakeTorrent(hash="H4", name="V", state="pausedDL", progress=0.5, tags="")
        outside = FakeTorrent(hash="H9", name="O", state="stalledUP", tags="")
        mgr = _grouped_mgr(os.path.join(td, "state.json"), {"H1": me, "H2": normal, "H3": tagged, "H4": verified})
        mgr.store.by_hash["H9"] = outside  # 在快照里但不在组内
        # H3=带标候选 / H4=组内 verified(非候选态) / H9=组外 verified / GHOST=不在快照
        mgr.store.verified_references = {"H3", "H4", "H9", "GHOST"}
        action = _check_action(basic_check="filelist")
        ctx = make_ctx(mgr, me, FakeClient())
        # 有参考: 组内存在已完成且未带标候选
        assert action.has_reference(ctx, ["H1", "H2", "H3"]) is True
        # 带标候选被排除, verified 侧(带标 H3/组外 H9/快照外 GHOST)也命中不了 -> 无参考
        assert action.has_reference(ctx, ["H1", "H3"]) is False, "带标候选与带标/组外/快照外 verified 均被排除"
        # verified 并集命中: 组内未带标成员(非候选态)经 verified 命中 -> 有参考
        assert action.has_reference(ctx, ["H1", "H3", "H4"]) is True, "verified 组内成员命中"
        # 排除自身: verified 只含自身 -> 无参考
        mgr.store.verified_references = {"H1"}
        assert action.has_reference(ctx, ["H1", "H3"]) is False, "自身不得作为自己的参考"


class _PHClient(FakeClient):
    """piecehashes 谓词测试替身: 按 hash 返回 piece hashes, bad 集合内的 hash 抛异常"""
    def __init__(self, hashes=None, bad=()):
        super().__init__()
        self.ph_calls = []
        self._hashes = hashes or {}
        self._bad = set(bad)

    def torrents_piece_hashes(self, torrent_hashes=None):
        self.ph_calls.append(torrent_hashes)
        if torrent_hashes in self._bad:
            raise RuntimeError("api error")
        return self._hashes.get(torrent_hashes, [b"a", b"b"])


def test_has_reference_piecehashes_shortcircuit():
    """checking: piecehashes 谓词 —— 首个匹配参考提前返回(后续候选不再拉取); 无匹配/带标候选不询问"""
    with tempfile.TemporaryDirectory() as td:
        me = FakeTorrent(hash="H1", name="T", state="pausedDL", progress=0.5, tags="")
        c1 = FakeTorrent(hash="H2", name="C1", state="stalledUP", tags="")
        c2 = FakeTorrent(hash="H3", name="C2", state="stalledUP", tags="")
        tagged = FakeTorrent(hash="H4", name="K", state="stalledUP", tags="zSkipChecked")
        mgr = _grouped_mgr(os.path.join(td, "state.json"), {"H1": me, "H2": c1, "H3": c2, "H4": tagged})
        action = _check_action(basic_check="piecehashes")
        # 首个匹配即提前返回: 第二个候选不再拉取
        client = _PHClient()
        mgr.client = client
        ctx = make_ctx(mgr, me, client)
        assert action.has_reference(ctx, ["H1", "H2", "H3"]) is True
        assert client.ph_calls == ["H1", "H2"], "首个匹配即提前返回, 第二个候选不再拉取"
        # 无匹配: 候选 piece hash 与目标全不同
        client2 = _PHClient(hashes={"H1": [b"a"], "H2": [b"x"], "H3": [b"y"]})
        mgr.client = client2
        ctx2 = make_ctx(mgr, me, client2)
        assert action.has_reference(ctx2, ["H1", "H2", "H3"]) is False
        assert client2.ph_calls == ["H1", "H2", "H3"]
        # 带标候选被排除: 不对其发 piece hashes 请求, 后面的有效候选仍命中
        client3 = _PHClient(hashes={"H2": [b"x"], "H3": [b"a", b"b"]})
        mgr.client = client3
        ctx3 = make_ctx(mgr, me, client3)
        assert action.has_reference(ctx3, ["H1", "H2", "H3", "H4"]) is True
        assert "H4" not in client3.ph_calls and "H3" in client3.ph_calls, "带标候选不询问, 未带标候选仍命中"


def test_has_reference_piecehashes_cand_error():
    """checking: piecehashes 候选拉取异常 -> 忽略该候选, 不崩溃; 目标拉取失败 -> 视为无参考"""
    with tempfile.TemporaryDirectory() as td:
        t1 = FakeTorrent(hash="H1", name="T1", state="stalledUP", tags="")
        t2 = FakeTorrent(hash="H2", name="T2", state="stalledUP", tags="")
        mgr = _grouped_mgr(os.path.join(td, "state.json"), {"H1": t1, "H2": t2})
        action = _check_action(basic_check="piecehashes")

        class BoomClient(_PHClient):
            def torrents_piece_hashes(self, torrent_hashes=None):
                self.ph_calls.append(torrent_hashes)
                if torrent_hashes in self._bad:
                    raise RuntimeError("cand api error")
                return [b"a", b"b"]

        # 候选拉取失败: 该候选忽略, 不崩溃
        client = BoomClient(bad={"H2"})
        mgr.client = client
        ctx = make_ctx(mgr, t1, client)
        assert action.has_reference(ctx, ["H1", "H2"]) is False, "候选拉取失败不应作为参考"
        assert client.ph_calls == ["H1", "H2"]
        # 目标拉取失败: 视为无参考, 候选不再询问
        client2 = BoomClient(bad={"H1"})
        mgr.client = client2
        ctx2 = make_ctx(mgr, t1, client2)
        assert action.has_reference(ctx2, ["H1", "H2"]) is False
        assert client2.ph_calls == ["H1"]


def test_has_reference_custom_shortcircuit():
    """checking: custom 谓词 —— 首个候选通过即 True 且短路(不再对后续候选发请求); 全不通过 -> False"""
    with tempfile.TemporaryDirectory() as td:
        me = FakeTorrent(hash="H1", name="T", state="pausedDL", progress=0.5, tags="")
        c1 = FakeTorrent(hash="H2", name="C1", state="stalledUP", tags="")
        c2 = FakeTorrent(hash="H3", name="C2", state="stalledUP", tags="")
        mgr = _grouped_mgr(os.path.join(td, "state.json"), {"H1": me, "H2": c1, "H3": c2})
        action = _check_action(basic_check="custom", custom_program="fake_prog")
        ctx = make_ctx(mgr, me, FakeClient())
        # 首个候选通过 -> True, 且不再询问第二个候选(短路)
        with patch("subprocess.run") as run:
            run.return_value.returncode = 0
            assert action.has_reference(ctx, ["H1", "H2", "H3"]) is True
            assert run.call_count == 1, "首个候选通过即短路, 不再对后续候选发请求"
            assert run.call_args[0][0][1] == "H2"
        # 全部候选不通过 -> False
        with patch("subprocess.run") as run:
            run.return_value.returncode = 1
            run.return_value.stderr = ""
            assert action.has_reference(ctx, ["H1", "H2", "H3"]) is False
            assert run.call_count == 2


def test_run_custom_check_error():
    """checking: custom 程序执行异常 -> 视为非参考, 不崩溃"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        tor = FakeTorrent(tags="")
        ctx = make_ctx(mgr, tor, client)
        action = _check_action(basic_check="custom", custom_program="fake_prog")
        with patch("subprocess.run", side_effect=OSError("no prog")):
            assert action._run_custom_check(ctx, tor) is False


def test_speed_limit_fmt_bytes():
    """限速动作: 小值(<1KiB) 格式化为 B/s(与 utils.fmt_speed 一致)"""
    from auto_qb.infra import utils
    assert utils.fmt_speed(512) == "512 B/s"
    assert utils.fmt_speed(2048) == "2.00 KiB/s"
    assert utils.fmt_speed(0) == "0 B/s"


def test_start_stop_dry_run():
    """start/stop dry-run: 状态语义判定通过但不打 API"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        paused = FakeTorrent(hash="HP", state="pausedUP")
        ctx = make_ctx(mgr, paused, client, dry_run=True)
        assert StartAction(True).execute(ctx).is_ok
        assert not any(c[0] == "start" for c in client.calls)
        running = FakeTorrent(hash="HR", state="stalledUP")
        ctx2 = make_ctx(mgr, running, client, dry_run=True)
        assert StopAction(True).execute(ctx2).is_ok
        assert not any(c[0] == "stop" for c in client.calls)


def test_move_to_dry_run():
    """move_to dry-run: 不打 set_location"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        tor = FakeTorrent(tags="")
        ctx = make_ctx(mgr, tor, client, dry_run=True)
        result = MoveToAction({"path": r"R:\New"}).execute(ctx)
        assert result.is_ok and r"R:\New" in result.message
        assert not any(c[0] == "set_location" for c in client.calls)


def test_speed_limit_dry_run_manual_and_same_value_skips():
    """限速动作: dry-run 整段跳过; 手动限速(奇数 KiB/s)不覆盖; 同值不重设"""
    from auto_qb.infra import utils

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        value = utils.parse_speed("1MiB/s")
        # dry-run: 不读当前限速不打 API
        tor = FakeTorrent(tags="")
        ctx = make_ctx(mgr, tor, client, dry_run=True)
        result = DownloadSpeedLimitAction("1MiB/s").execute(ctx)
        assert result.is_ok and "MiB/s" in result.message
        assert not any(c[0] == "set_download_limit" for c in client.calls)
        # 手动限速: 奇数 KiB/s 视为用户设置, 不覆盖
        tor2 = FakeTorrent(hash="H2", tags="", dl_limit=1025)
        ctx2 = make_ctx(mgr, tor2, client)
        result2 = DownloadSpeedLimitAction("1MiB/s").execute(ctx2)
        assert result2.is_skipped and result2.message == "用户已设置"
        # 同值: 不重设
        tor3 = FakeTorrent(hash="H3", tags="", dl_limit=value)
        ctx3 = make_ctx(mgr, tor3, client)
        result3 = DownloadSpeedLimitAction("1MiB/s").execute(ctx3)
        assert result3.is_skipped and result3.message == "已设置"
        assert not any(c[0] == "set_download_limit" for c in client.calls)


def test_print_details_missing_torrent():
    """print_torrent_details: 种子不存在(实时快照与删除前副本皆无) -> fail"""
    from auto_qb.rules.actions import PrintTorrentDetailsAction

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        tor = FakeTorrent(tags="")
        ctx = make_ctx(mgr, tor, client)
        mgr.store.by_hash.pop(tor.hash)  # 移除实时快照; ctx.snapshot 亦无 -> ctx.torrent 为 None
        result = PrintTorrentDetailsAction(True).execute(ctx)
        assert result.is_failed and "种子不存在" in result.message


def test_checking_disabled_segment_skips():
    """checking: 未启用的校验段 -> skip(有参考/无参考两种指代)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        # 无参考段未启用: 单个未完成种子, 无参考 -> 走 without_reference 段
        tor = FakeTorrent(hash="H1", tags="", state="pausedDL", progress=0.5)
        ctx = make_ctx(mgr, tor, client)
        action = _check_action(without_seg=_seg("full-checking", enabled=False))
        result = _run_action(action, ctx)
        assert result.is_skipped and "无参考" in result.message
        # 有参考段未启用: 同组 H2 已完成作参考 -> 走 with_reference 段
        t2 = FakeTorrent(hash="H2", tags="", state="stalledUP", progress=1.0)
        mgr2 = make_manager(os.path.join(td, "state2.json"))
        mgr2.store.groups[("KEY", )] = ["H1", "H2"]
        mgr2.store.member_to_key["H1"] = ("KEY", )
        mgr2.store.member_to_key["H2"] = ("KEY", )
        seed_store(mgr2, [tor, t2])
        ctx2 = make_ctx(mgr2, tor, client)
        action2 = _check_action(with_seg=_seg("full-checking", enabled=False))
        result2 = action2.execute(ctx2)
        assert result2.is_skipped and "有参考" in result2.message


def test_actions_torrent_hash_scope():
    """动作下发 qB 的 torrent_hashes 必须是本种子 hash

    置 None / 省略 = qB 按「全库」处理, 一次规则命中会误伤所有种子。
    FakeClient 的 calls 不记 hash, 故对 remove_tags / set_category / set_location 挂记录器;
    限速与强制汇报用 FakeClient 已有的 hash 级台账。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        seen = []
        for meth in ("torrents_remove_tags", "torrents_set_category", "torrents_set_location"):
            orig = getattr(client, meth)

            def spy(*a, _orig=orig, _meth=meth, **kw):
                seen.append((_meth, kw.get("torrent_hashes")))
                return _orig(*a, **kw)

            setattr(client, meth, spy)

        tor = FakeTorrent(tags="seed-3D", category="")
        ctx = make_ctx(mgr, tor, client)
        assert RemoveTagsAction(["regex:^seed-"]).execute(ctx).is_ok
        assert AddCategoryAction({"format": "AUTO"}).execute(ctx).is_ok
        assert RemoveCategoryAction("").execute(ctx).is_ok
        assert MoveToAction({"path": r"R:\New"}).execute(ctx).is_ok
        assert ReannounceAction("").execute(ctx).is_ok
        assert UploadSpeedLimitAction("1000KiB/s").execute(ctx).is_ok
        assert DownloadSpeedLimitAction("2MiB/s").execute(ctx).is_ok

        assert len(seen) >= 4, f"作用域记录缺失: {seen}"
        assert [h for _, h in seen] == [ctx.hash] * len(seen), f"下发作用域必须只含本 hash: {seen}"
        assert client.reannounce_hashes_calls == [ctx.hash], "reannounce 作用域必须只含本 hash"
        assert ("set_upload_limit", ctx.hash) in client.limit_location_hashes_calls
        assert ("set_download_limit", ctx.hash) in client.limit_location_hashes_calls


def test_actions_expand_tracker_vars():
    """${required_seeding_time} 必须经 tracker_conf 展开(传 None 则占位符永不解析)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(tags="seed-3D"), client)  # 默认 HHan 站点 hr.required_seeding_time_raw = "3D"
        assert RemoveTagsAction(["seed-${required_seeding_time}"]).execute(ctx).is_ok
        assert ("remove_tags", ["seed-3D"]) in client.calls, f"pattern 未展开: {client.calls}"
        assert AddCategoryAction({"format": "CAT-${required_seeding_time}"}).execute(ctx).is_ok
        assert ("set_category", "CAT-3D") in client.calls, f"format 未展开: {client.calls}"


def test_move_to_confirm_gate_skips():
    """整组迁移的 confirm 形态: 规则侧无交互, 只回 skip 且不得请求确认

    confirm=True 会让「目录别名」这类需用户点头的形态在无人值守下直接执行整组迁移。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(), client)
        ctx.config.relocate.enabled = True
        calls = []

        class _Relocate:
            """迁移闸门替身: 别名形态需要显式确认"""
            def relocate_execute(self, hashes, path, confirm=False, origin="rule"):
                calls.append((list(hashes), path, confirm, origin))
                return [{"cls": "confirm", "form": "alias"}]

        mgr.ctx.relocate = _Relocate()
        r = MoveToAction({"path": r"R:\New"}).execute(ctx)
        assert r.is_skipped, f"需确认的形态只能 skip: {r}"
        assert calls == [([ctx.hash], r"R:\New", False, "rule")], f"规则侧不得请求确认且必须标记 rule 来源: {calls}"
        assert all(c[0] != "set_location" for c in client.calls), "闸门形态不得再直下 set_location"


def test_speed_limit_direction_uses_own_axis():
    """上传/下载限速各读自己的轴(up_limit / dl_limit)做手动限速闸门

    方向判定被改坏时上传动作会去读 dl_limit: 手动限速保护失效(覆盖用户设置),
    或本轴空闲却被另一轴的手动值挡住。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        manual = 2001 * 1024  # 奇数 KiB/s = 用户手动设置(utils.is_manual_speed_limit)
        tor = FakeTorrent(up_limit=manual, dl_limit=0)
        ctx = make_ctx(mgr, tor, client)
        assert UploadSpeedLimitAction("1000KiB/s").execute(ctx).is_skipped, "上传轴已手动设置 -> 不覆盖"
        tor.up_limit, tor.dl_limit = 0, manual
        assert DownloadSpeedLimitAction("1000KiB/s").execute(ctx).is_skipped, "下载轴已手动设置 -> 不覆盖"
        # 对照: 另一轴的手动值不得影响本轴下发
        tor.up_limit, tor.dl_limit = 0, manual
        assert UploadSpeedLimitAction("1000KiB/s").execute(ctx).is_ok, "上传轴空闲 -> 应下发"
        assert ("set_upload_limit", 1000 * 1024) in client.calls
        tor.up_limit, tor.dl_limit = manual, 0
        assert DownloadSpeedLimitAction("1000KiB/s").execute(ctx).is_ok, "下载轴空闲 -> 应下发"
        assert ("set_download_limit", 1000 * 1024) in client.calls


def test_start_stop_gate_ignores_group_members_own_write():
    """C31 守阵: 起停幂等门只判本 hash(`group=False`) —— 同组成员刚被自写时不得误伤

    变异: group=False 被省略/置 True -> 兄弟成员的自写登记把本种子的起停整段拦下
    (组内各成员各自起停互相误伤)。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        tor = FakeTorrent(hash="HA", state="pausedDL")
        sib = FakeTorrent(hash="HB", state="stalledUP")
        ctx = make_ctx(mgr, tor, client)
        mgr.store.by_hash["HB"] = sib
        mgr.store.groups[("KEY", )] = ["HA", "HB"]
        mgr.store.member_to_key.update({"HA": ("KEY", ), "HB": ("KEY", )})
        mgr.store.note_own_write("HB")  # 同组成员刚被自有停/起
        assert mgr.store.own_write_pending("HA") is True, "对照组: 组维度判据应为真"
        assert mgr.store.own_write_pending("HA", group=False) is False

        assert StartAction("").execute(ctx).is_ok, "兄弟成员的自写不得拦下本种子的 start"
        assert ("start", None) in client.calls

        mgr.store.own_writes.clear()
        mgr.store.note_own_write("HB")
        tor.state = "stalledUP"
        assert StopAction("").execute(ctx).is_ok, "兄弟成员的自写不得拦下本种子的 stop"
        assert ("stop", None) in client.calls


def _run_print_details(tor):
    """执行 print_torrent_details, 返回 (result, 动作模块产出的日志行列表)

    用 helpers.capture_logs 而非 caplog: make_manager 构造链会清空 root handlers, caplog 恒空。
    """
    from auto_qb.rules.actions import PrintTorrentDetailsAction

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        ctx = make_ctx(mgr, tor, FakeClient())
        with capture_logs("auto_qb.rules.actions.basic") as cap:
            result = PrintTorrentDetailsAction(True).execute(ctx)
    return result, cap.messages


def test_print_details_numeric_fields():
    """C46 守阵: 进度/分享率/做种时长有值时精确显示, None 时显示 "-" 且动作仍 ok
    (条件被 and False/or True 改写、算式 *100 漂移、判据 is None 反转都会显示错值或崩)"""
    tor = FakeTorrent(tags="", progress=0.5, ratio=2.0, seeding_time=3600)
    result, lines = _run_print_details(tor)
    assert result.is_ok
    text = "\n".join(lines)
    assert "进度=50.0%" in text
    assert "分享率=2.00" in text
    assert "做种时长=3600s" in text
    tor2 = FakeTorrent(hash="H2", tags="", progress=None, ratio=None, seeding_time=None)
    result2, lines2 = _run_print_details(tor2)
    assert result2.is_ok
    text2 = "\n".join(lines2)
    assert "进度=-" in text2 and "分享率=-" in text2 and "做种时长=-" in text2


def test_print_details_non_empty_fields_not_replaced_by_dash():
    """C47 守阵: 非空字段不得被 `x or "-"` → `x and "-"` 的改写恒替换成 "-" """
    tor = FakeTorrent(
        tags="HR,1080p",
        name="测试种子",
        state="uploading",
        save_path="R:/A",
        content_path="R:/A/B",
        category="Anime",
    )
    result, lines = _run_print_details(tor)
    assert result.is_ok
    text = "\n".join(lines)
    for frag in (
        "名称=测试种子",
        "状态=uploading",
        "保存路径=R:/A",
        "内容路径=R:/A/B",
        "标签=HR,1080p",
        "分类=Anime",
    ):
        assert frag in text, f"详情行丢了真实值: {frag}"


def test_print_details_size_fields_formatted():
    """C51 守阵: 大小/上传量/下载量必须把真实字节数交给 fmt_size(传 None 恒显示 "-")"""
    tor = FakeTorrent(tags="", size=200 * 1024**3, uploaded=400 * 1024**3, downloaded=100 * 1024**2)
    result, lines = _run_print_details(tor)
    assert result.is_ok
    text = "\n".join(lines)
    assert "大小=200.00 GiB" in text
    assert "上传=400.00 GiB" in text
    assert "下载=100.00 MiB" in text


def test_print_details_line_contains_all_fields():
    """C55 守阵: detail 整行不得被置 None —— 动作唯一产出必须是完整详情行"""
    tor = FakeTorrent(tags="HR", name="X")
    result, lines = _run_print_details(tor)
    assert result.is_ok
    text = "\n".join(lines)
    assert "打印种子详情:" in text
    assert "名称=" in text and "tracker=" in text


def test_print_details_emits_exactly_one_info_line():
    """C56 守阵: logger.info 不得被置 None —— 只读动作必须真的输出一行详情"""
    tor = FakeTorrent(tags="HR", name="X")
    result, lines = _run_print_details(tor)
    assert result.is_ok
    assert len(lines) == 1, f"应只有一行详情日志, 实得 {len(lines)} 行: {lines}"
    assert "打印种子详情:" in lines[0] and "名称=X" in lines[0]
