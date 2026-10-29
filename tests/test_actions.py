"""test_actions 测试计划: rules/actions 动作插件执行语义

## 测试计划(每个测试函数一条)
- test_add_tags: 添加标签动作: 直接调用 client.add_tags
- test_remove_tags: 移除标签动作: 调用 client.remove_tags
- test_add_category_overwrite_semantics: 加分类动作的 overwrite 覆盖语义
- test_remove_category: 移除分类动作
- test_start_stop_idempotent: 开始/停止动作幂等(重复执行不报错)
- test_stop_preserves_completeness: 暂停/恢复**不再**合成回写 state(A 系 26-10-13-0540 S1)——动作后快照不变, 完成位不可能被写坏(该类 bug 结构性消失)
- test_pause_resume_no_same_tick_writeback: 契约变更(A 系 S1, 原 26-10-06-0028 A-04 守阵方向翻面)——QbApi pause/resume 不再写后同步 store 快照, 同 tick 读到旧值
- test_start_stop_idempotent_within_same_tick: 同 tick 二次 stop/start 被 own_writes 意图标记拦下(A2), 且不写任何假 state 值
- test_move_to: 移动保存路径动作
- test_reannounce: 重新 announce 动作
- test_speed_limit_actions: 限速动作(下载/上传/全局)
- test_add_category_create_error: 创建分类失败被吞掉, set_category 仍执行
- test_find_reference_piecehashes_cand_error: piecehashes 候选拉取异常 -> 忽略候选
- test_find_reference_dedup: 候选与 verified_references 重合 -> 去重
- test_run_custom_check_error: custom 程序执行异常 -> 视为非参考
- test_skip_checking_export_error: 导出 .torrent 失败 -> fail
- test_skip_checking_export_empty: 导出为空 -> fail
- test_skip_checking_delete_error: 删除种子失败 -> fail(无损失)
- test_skip_checking_delete_not_confirmed: 删除后确认种子消失失败 -> 放弃跳检不重加
- test_skip_checking_readd_preserves_values: 重加属性直传(0/负值有语义, 不得被 or None 吞掉)
- test_skip_checking_readd_restores_store_record: 重加成功后恢复删除前快照记录(tracker_conf 保留, 修复 log_repr 崩溃)
- test_skip_checking_content_layout_inferred: contentLayout 由 content_path/save_path/文件列表推断
- test_skip_checking_auto_start_error: 自动开始失败 -> fail
- test_speed_limit_fmt_bytes: 小值限速格式化为 B/s
- test_remove_tags_dry_run: remove_tags dry-run 命中不打 API (P2-a)
- test_add_category_existing_no_recreate_and_dry_run: add_category 已存在不重建 / dry-run 跳过整段 (P2-a)
- test_remove_category_dry_run: remove_category dry-run (P2-a)
- test_start_stop_dry_run: start/stop dry-run (P2-a)
- test_move_to_dry_run: move_to dry-run (P2-a)
- test_speed_limit_dry_run_manual_and_same_value_skips: 限速 dry-run / 手动限速不覆盖 / 同值不重设 (P2-a)
- test_print_details_missing_torrent: print_torrent_details 种子不存在 -> fail (P2-a)
- test_checking_disabled_segment_skips: checking 未启用段 -> skip 有/无参考两指代 (P2-a)
- test_checking_verified_reference_union_filters: verified_references 并集过滤(自身/快照外)且去重 (P2-a)
- test_actions_ignore_error_passthrough: 六个动作类 __init__ 原样透传 ignore_error(丢实参/置 None 即失效)
- test_actions_torrent_hash_scope: 各动作下发 qB 的 torrent_hashes 恒为本种子 hash(置 None = 全库副作用)
- test_add_category_overwrite_switch: add_category 的 overwrite 开关读取(显式 true/false 与缺省)
- test_add_remove_tags_string_spec_not_split: 字符串 spec 不得被 list() 拆成单字符
- test_add_category_format_default: add_category 缺 format 键时兜底空串(不得产出 "None"/"XXXX")
- test_actions_expand_tracker_vars: ${required_seeding_time} 经 tracker_conf 展开(remove_tags/add_category)
- test_add_category_creates_named_category: 建分类时 create_category 收到真实分类名
- test_move_to_confirm_gate_skips: 整组迁移 confirm 形态只回 skip 且规则侧 confirm=False
- test_speed_limit_direction_uses_own_axis: 上传/下载限速各读自己的轴做手动限速闸门
- test_actions_registry_complete
"""
import os
import tempfile
from unittest.mock import patch

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
from helpers import drive_skip, FakeClient, FakeTorrent, make_ctx, make_manager, seed_store


def _seg(mode, auto_start=True, enabled=True):
    """构造 with_reference/without_reference 段配置(新架构: 段需显式 enabled=True 才启用)"""
    return {"enabled": enabled, "mode": mode, "auto_start": auto_start}


def _setup(state_file=None):
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(state_file or os.path.join(td, "state.json"))
        client = FakeClient()
        tor = FakeTorrent(tags="")
        yield mgr, client, tor


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


def test_add_tags():
    """添加标签: 新标签/已存在 skip/变量替换/dry-run"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        tor = FakeTorrent(tags="HHan")
        ctx = make_ctx(mgr, tor, client)
        r = AddTagsAction(["HHan", "seed-${required_seeding_time}"]).execute(ctx)
        assert r.is_ok, f"应添加标签: {r}"
        assert ("add_tags", ["seed-3D"]) in client.calls
        # 已存在 -> skip
        r2 = AddTagsAction(["HHan"]).execute(ctx)
        assert r2.is_skipped
        # dry-run 无调用
        client.calls.clear()
        ctx2 = make_ctx(mgr, tor, client, dry_run=True)
        assert AddTagsAction(["NEW"]).execute(ctx2).is_ok
        assert client.calls == []


def test_remove_tags():
    """删除标签: 正则/无匹配 skip/dry-run"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        client.tags = {"HHan", "seed-3D"}
        tor = FakeTorrent(tags="HHan,seed-3D")
        ctx = make_ctx(mgr, tor, client)
        r = RemoveTagsAction(["regex:^seed-"]).execute(ctx)
        assert r.is_ok
        assert ("remove_tags", ["seed-3D"]) in client.calls
        # 无匹配 -> skip
        assert RemoveTagsAction(["NOPE"]).execute(ctx).is_skipped


def test_add_category_overwrite_semantics():
    """分类动作: 手动分类不覆盖/自动分类可更新/同分类 skip"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        tor = FakeTorrent(category="")
        ctx = make_ctx(mgr, tor, client)
        assert AddCategoryAction({"format": "AUTO-A"}).execute(ctx).is_ok
        assert mgr.state["auto_categories"] == {"HASH123": "AUTO-A"}
        # 当前分类 == 上次自动设置 -> 可更新
        tor.category = "AUTO-A"
        assert AddCategoryAction({"format": "AUTO-B"}).execute(ctx).is_ok
        assert mgr.state["auto_categories"]["HASH123"] == "AUTO-B"
        # 手动分类 -> 不覆盖
        tor.category = "MANUAL"
        assert AddCategoryAction({"format": "AUTO-C"}).execute(ctx).is_skipped
        # 同分类 -> skip
        assert AddCategoryAction({"format": "MANUAL"}).execute(ctx).is_skipped


def test_remove_category():
    """清空分类: 空分类 skip/正常清空"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        tor = FakeTorrent(category="")
        ctx = make_ctx(mgr, tor, client)
        assert RemoveCategoryAction("").execute(ctx).is_skipped
        tor.category = "HR-DONE"
        assert RemoveCategoryAction("").execute(ctx).is_ok
        assert ("set_category", "") in client.calls


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


def test_add_category_create_error():
    """分类动作: 创建分类失败被吞掉, set_category 仍执行"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        tor = FakeTorrent(category="")
        ctx = make_ctx(mgr, tor, client)

        def boom():
            raise RuntimeError("create failed")

        client.torrents_create_category = boom
        r = AddCategoryAction({"format": "NEW"}).execute(ctx)
        assert r.is_ok
        assert ("set_category", "NEW") in client.calls


def _check_action(basic_check="filelist", with_seg=None, without_seg=None, custom_program=None):
    spec = {
        "basic_check": basic_check,
        "with_reference": with_seg or _seg("full-checking"),
        "without_reference": without_seg or _seg("full-checking"),
    }
    if custom_program:
        spec["custom_basic_check_program_path"] = custom_program
    return CheckAction(spec)


def _grouped_mgr(state_file, hashes):
    """构造已归组 manager: store 分组结构 + 快照齐全(store.apply 已删, 用 seed_store 灌快照)"""
    mgr = make_manager(state_file)
    mgr.store.groups[("KEY", )] = list(hashes)
    for h in hashes:
        mgr.store.member_to_key[h] = ("KEY", )
    seed_store(mgr, list(hashes.values()))
    return mgr


def test_find_reference_piecehashes_cand_error():
    """checking: piecehashes 模式候选拉取异常 -> 忽略该候选, 不崩溃"""
    with tempfile.TemporaryDirectory() as td:
        t1 = FakeTorrent(hash="H1", name="T1", state="stalledUP", tags="")
        t2 = FakeTorrent(hash="H2", name="T2", state="stalledUP", tags="")
        mgr = _grouped_mgr(os.path.join(td, "state.json"), {"H1": t1, "H2": t2})

        class BoomClient(FakeClient):
            def torrents_piece_hashes(self, torrent_hashes=None):
                self.calls.append(("piece_hashes", torrent_hashes))
                if torrent_hashes == "H2":
                    raise RuntimeError("cand api error")
                return [b"a", b"b"]

        client = BoomClient()
        ctx = make_ctx(mgr, t1, client)
        action = _check_action(basic_check="piecehashes")
        refs = action._find_reference(ctx, ["H1", "H2"])
        assert refs == [], "候选拉取失败不应作为参考"


def test_find_reference_dedup():
    """checking: 候选与 verified_references 重合 -> 去重"""
    with tempfile.TemporaryDirectory() as td:
        t1 = FakeTorrent(hash="H1", name="T1", state="stalledUP", tags="")
        t2 = FakeTorrent(hash="H2", name="T2", state="stalledUP", tags="")
        mgr = _grouped_mgr(os.path.join(td, "state.json"), {"H1": t1, "H2": t2})
        mgr.store.verified_references = {"H2"}
        client = FakeClient()
        ctx = make_ctx(mgr, t1, client)
        action = _check_action(basic_check="filelist")
        refs = action._find_reference(ctx, ["H1", "H2"])
        assert [t.hash for t in refs] == ["H2"], "verified 重合应去重"


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


def _run_action(action, ctx):
    """执行动作; 跳检自 S4 起是异步入口(pending), 这里驱动微步线到终态并返回终态结果

    生产由主循环微步线推进; 测试无主循环, 用 drive_skip 替身。非 pending 动作原样返回。
    """
    r = action.execute(ctx)
    if r.is_pending:
        drive_skip(ctx.manager)
        return ctx.manager.ctx.ops.skip_result(ctx.hash) or r
    return r


def _skip_ctx(state_file, **client_patches):
    """构造 skip-checking 执行环境: 未归组 + 单种子快照 + 自定义 client"""
    mgr = make_manager(state_file)
    tor = FakeTorrent(hash="HASH123", name="T1", state="pausedDL", tags="")  # 暂停未完成, 满足决策链 0
    seed_store(mgr, [tor])
    client = FakeClient()
    client.torrents["HASH123"] = {"state": "pausedUP"}  # 重加后出现
    for attr, fn in client_patches.items():
        setattr(client, attr, fn)
    ctx = make_ctx(mgr, tor, client)

    # 跳检动作语义: 删除种子(保留文件)后按旧种子字段重加。真实 qB 中种子删除后立即以同 hash
    # 重新出现; 测试包装 torrents_delete: 先真实调用(QbApi 同步移除快照的语义保留, 供
    # test_skip_checking_delete_error 等校验), 成功后恢复快照记录, 模拟重加后种子重新出现,
    # 使动作能读到重加参数(save_path/category/tags/limits, actions._execute_skip_checking 的
    # delete 后 ctx.torrent 读取)。不改 src, 仅测试侧镜像"重加后同 tick 内快照可用"。
    orig_delete = mgr.api.torrents_delete

    def wrapped_delete(torrent_hashes=None, delete_files=False, **kw):
        orig_delete(torrent_hashes=torrent_hashes, delete_files=delete_files, **kw)
        mgr.store.restore_torrent(tor)  # 重加后同 tick 快照恢复(并撤销待报删除)

    mgr.api.torrents_delete = wrapped_delete
    return ctx, client


def test_skip_checking_export_error():
    """checking skip-checking: 导出 .torrent 失败 -> fail"""
    with tempfile.TemporaryDirectory() as td:

        def boom(h=None, **kw):
            raise RuntimeError("export failed")

        ctx, _ = _skip_ctx(os.path.join(td, "state.json"), torrents_export=boom)
        action = _check_action(without_seg=_seg("skip-checking"))
        r = _run_action(action, ctx)
        assert r.is_failed and "导出" in r.message, f"应失败: {r}"


def test_skip_checking_export_empty():
    """checking skip-checking: 导出为空 -> fail"""
    with tempfile.TemporaryDirectory() as td:
        ctx, client = _skip_ctx(os.path.join(td, "state.json"))
        client.exported = b""
        action = _check_action(without_seg=_seg("skip-checking"))
        r = _run_action(action, ctx)
        assert r.is_failed and "为空" in r.message, f"应失败: {r}"


def test_skip_checking_delete_error():
    """checking skip-checking: 删除种子失败 -> fail(种子未删除, 无损失)"""
    with tempfile.TemporaryDirectory() as td:

        def boom(h=None, **kw):
            raise RuntimeError("delete failed")

        ctx, _ = _skip_ctx(os.path.join(td, "state.json"), torrents_delete=boom)
        action = _check_action(without_seg=_seg("skip-checking"))
        r = _run_action(action, ctx)
        assert r.is_failed and "删除种子失败" in r.message, f"应失败: {r}"


def test_skip_checking_readd_preserves_values():
    """checking skip-checking: 重加属性直传 —— 0 等有语义值(不限速/分享率限制)不得被 or None 吞成 qB 新种缺省"""
    with tempfile.TemporaryDirectory() as td:
        ctx, client = _skip_ctx(os.path.join(td, "state.json"))
        tor = ctx.torrent
        tor.up_limit = 0  # 0 = 不限速
        tor.dl_limit = 2001 * 1024  # 非零控制组
        tor.ratio_limit = 0  # qB 分享率限制(有语义)
        tor.seeding_time_limit = 0
        action = _check_action(without_seg=_seg("skip-checking"))
        with patch("auto_qb.core.modules.ops_mod.time.sleep"):
            r = _run_action(action, ctx)
        assert r.is_ok, f"{r}"
        add = next(c for c in client.calls if c[0] == "add")
        assert add[1]["upload_limit"] == 0, f"不限速 0 应直传: {add}"
        assert add[1]["download_limit"] == 2001 * 1024, f"{add}"
        assert add[1]["ratio_limit"] == 0 and add[1]["seeding_time_limit"] == 0, f"{add}"


def test_skip_checking_readd_restores_store_record():
    """重加成功后恢复删除前快照记录: 否则下轮 refresh 重建记录 tracker_conf=None 且不进
    added 列表(remove_torrent 保留 _known_hashes), 该种子永久未匹配 —— 真实 BUG:
    log_repr -> tracker_name -> self.tor.client AttributeError(生产日志 2026-09-06)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(tags="", state="pausedDL")  # 暂停未完成: 过闸门 0
        tor.tracker_conf = mgr.config.trackers["HHan"]  # 删除前已匹配(生产: _refresh_torrents 阶段)
        client.torrents["HASH123"] = tor
        seed_store(mgr, [tor])
        action = _check_action(without_seg=_seg("skip-checking"))
        ctx = make_ctx(mgr, tor, client)
        with patch("auto_qb.core.modules.ops_mod.time.sleep"):
            r = _run_action(action, ctx)
        assert r.is_ok, f"{r}"
        # 快照记录已恢复(对象身份 = 删除前捕获的 tor), tracker_conf 保留
        assert mgr.store.get("HASH123") is tor
        assert tor.tracker_conf is mgr.config.trackers["HHan"]
        # log_repr 不再崩(tracker_name 走 conf, 不回退 self.tor.client)
        assert "[HHan]" in tor.log_repr

        # 真实 qB 场景: tor 是 TorrentDictionary(无 client 属性)也不崩 —— 模拟无 client 属性的 tor
        class _TorDictLike:
            pass  # 无 client/_client

        rec = tor  # 直接验证 tracker_name 在 conf 存在时不触碰 tor.client
        assert rec.tracker_name == "HHan"


def test_skip_checking_content_layout_inferred():
    """checking skip-checking: contentLayout 由 content_path/save_path/文件列表推断, 防止布局错位"""
    from types import SimpleNamespace

    with tempfile.TemporaryDirectory() as td:
        action = _check_action(without_seg=_seg("skip-checking"))
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()

        def case(save, content, files):
            tor = FakeTorrent(save_path=save, content_path=content, name="T1", state="pausedDL")
            client.files_map = {"HASH123": files}
            seed_store(mgr, [tor])
            ctx = make_ctx(mgr, tor, client)
            return mgr.ctx.ops._infer_content_layout(tor, client)  # 方法已迁 ops 模块(plan P4, 经 ctx.ops)

        def f(n):
            return SimpleNamespace(name=n, size=1)

        root_files = [f("T1/a.mkv"), f("T1/b.mkv")]
        # 多文件带根目录: content==save/种子名 -> Original(保留根); content==save -> NoSubfolder(原布局剥根)
        assert case(r"R:\Downloads", r"R:\Downloads\T1", root_files) == "Original"
        assert case(r"R:\Downloads", r"R:\Downloads", root_files) == "NoSubfolder"
        # 无根目录: content==save -> Original; 单文件 content==save/种子名 -> Original
        assert case(r"R:\Downloads", r"R:\Downloads", [f("a.mkv"), f("b.mkv")]) == "Original"
        assert case(r"R:\Downloads", r"R:\Downloads\T1", [f("T1.mkv")]) == "Original"
        # 路径异常(无法推断): None(用 qB 默认)
        assert case(r"R:\Downloads", r"R:\Elsewhere", root_files) is None


def test_skip_checking_delete_not_confirmed():
    """checking skip-checking: 删除后轮询确认失败(torrents_info 异常) -> 放弃跳检, 不重加"""
    with tempfile.TemporaryDirectory() as td:

        ctx, client = _skip_ctx(os.path.join(td, "state.json"))
        # !R2 实时复核发生在删除前: info 故障必须从"删除生效后"才开始 —— 种子还在客户端时
        #   正常应答, 删除(pop 出 client.torrents)后再查即抛, 精确模拟"确认消失轮询失败"
        orig_info = client.torrents_info

        def info_after_delete(torrent_hashes=None, **kw):
            if torrent_hashes not in client.torrents:
                raise RuntimeError("info failed")
            return orig_info(torrent_hashes=torrent_hashes, **kw)

        client.torrents_info = info_after_delete
        action = _check_action(without_seg=_seg("skip-checking"))
        with patch("auto_qb.core.modules.ops_mod.time.sleep"):
            r = _run_action(action, ctx)
        assert r.is_failed and "确认删除失败" in r.message, f"应失败(看不见就当没确认, fail-closed): {r}"
        assert not any(c[0] == "add" for c in client.calls), "未确认消失前不得重加"


def test_skip_checking_auto_start_error():
    """checking skip-checking: 自动开始失败 -> fail"""
    with tempfile.TemporaryDirectory() as td:

        def boom(h=None, **kw):
            raise RuntimeError("start failed")

        ctx, _ = _skip_ctx(os.path.join(td, "state.json"), torrents_start=boom)
        action = _check_action(without_seg=_seg("skip-checking", auto_start=True))
        r = _run_action(action, ctx)
        assert r.is_failed and "自动开始失败" in r.message, f"应失败: {r}"


def test_speed_limit_fmt_bytes():
    """限速动作: 小值(<1KiB) 格式化为 B/s(与 utils.fmt_speed 一致)"""
    from auto_qb.infra import utils
    assert utils.fmt_speed(512) == "512 B/s"
    assert utils.fmt_speed(2048) == "2.00 KiB/s"
    assert utils.fmt_speed(0) == "0 B/s"


# ---------------- P2-a 长尾清偿 (计划 26-10-01-2157 §3 P2, 2026-10-02) ----------------


def test_remove_tags_dry_run():
    """remove_tags dry-run: 命中匹配标签但不打 API"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        tor = FakeTorrent(tags="a, b")
        ctx = make_ctx(mgr, tor, client, dry_run=True)
        result = RemoveTagsAction(["a"]).execute(ctx)
        assert result.is_ok and "a" in result.message
        assert not any(c[0] == "remove_tags" for c in client.calls)


def test_add_category_existing_no_recreate_and_dry_run():
    """add_category: 分类已存在(store 惰性缓存)不重复创建; dry-run 跳过创建与设置整段"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        client.torrents_categories = lambda: {"HR-DONE": {"savePath": ""}}  # 分类定义已存在
        tor = FakeTorrent(tags="")
        ctx = make_ctx(mgr, tor, client)
        result = AddCategoryAction({"format": "HR-DONE", "overwrite": False}).execute(ctx)
        assert result.is_ok
        assert not any(c[0] == "create_category" for c in client.calls), "已存在分类不应重复创建"
        assert any(c[0] == "set_category" for c in client.calls)

        before = list(client.calls)
        tor2 = FakeTorrent(hash="H2", tags="")
        ctx2 = make_ctx(mgr, tor2, client, dry_run=True)
        result2 = AddCategoryAction({"format": "NEWCAT", "overwrite": False}).execute(ctx2)
        assert result2.is_ok
        assert client.calls == before, "dry-run 不创建也不设置分类"


def test_remove_category_dry_run():
    """remove_category dry-run: 有分类但不打 API"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        tor = FakeTorrent(category="c")
        ctx = make_ctx(mgr, tor, client, dry_run=True)
        result = RemoveCategoryAction(True).execute(ctx)
        assert result.is_ok and result.message == "清空分类"
        assert not any(c[0] == "set_category" for c in client.calls)


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


def test_checking_verified_reference_union_filters():
    """checking: verified_references 并集过滤(排除自身/非组内/已删除)且与候选去重"""
    with tempfile.TemporaryDirectory() as td:
        t1 = FakeTorrent(hash="H1", name="T1", state="pausedDL", progress=0.5, tags="")
        t2 = FakeTorrent(hash="H2", name="T2", state="stalledUP", tags="")
        mgr = _grouped_mgr(os.path.join(td, "state.json"), {"H1": t1, "H2": t2})
        mgr.store.verified_references = {"H1", "H2", "GHOST"}  # H1=自身 / GHOST=不在快照
        client = FakeClient()
        ctx = make_ctx(mgr, t1, client)
        action = _check_action(basic_check="filelist")
        refs = action._find_reference(ctx, ["H1", "H2"])
        assert [t.hash for t in refs] == ["H2"], "自身排除 / 快照外排除 / 与候选去重"


def test_actions_ignore_error_passthrough():
    """六个动作类 __init__ 必须把 ignore_error 原样交给基类

    ignore_next_action_error 的运行时效果全靠这个属性: 任一子类把 super().__init__ 的第二
    实参丢成 None / 省略, 规则链里「可忽略的失败」就升级成中断(后续动作不再执行)。
    """
    cases = [
        (AddTagsAction, "TAG"),
        (RemoveTagsAction, "TAG"),
        (AddCategoryAction, {
            "format": "AUTO"
        }),
        (CheckAction, {
            "basic_check": "filelist"
        }),
        (MoveToAction, {
            "path": r"R:\New"
        }),
        (UploadSpeedLimitAction, "1000KiB/s"),
        (DownloadSpeedLimitAction, "1000KiB/s"),
    ]
    for cls, spec in cases:
        assert cls(spec, True).ignore_error is True, f"{cls.__name__} 丢了 ignore_error"
        assert cls(spec).ignore_error is False, f"{cls.__name__} 默认应为 False"


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


def test_add_category_overwrite_switch():
    """add_category 的 overwrite 开关: 显式 true 必须为 True, 缺省/显式 false 为 False

    键名错位或置 None 会让 overwrite 恒 False —— 用户配了覆盖却永远不覆盖。
    """
    assert AddCategoryAction({"format": "X", "overwrite": True}).overwrite is True
    assert AddCategoryAction({"format": "X", "overwrite": "true"}).overwrite is True
    assert AddCategoryAction({"format": "X", "overwrite": False}).overwrite is False
    assert AddCategoryAction({"format": "X"}).overwrite is False


def test_add_remove_tags_string_spec_not_split():
    """字符串 spec 必须当成单个标签/模式, 不得被 list() 拆成单字符"""
    assert AddTagsAction("TAG").tags == ["TAG"]
    assert RemoveTagsAction("NOPE").patterns == ["NOPE"]
    assert AddTagsAction(["A", "B"]).tags == ["A", "B"]


def test_add_category_format_default():
    """add_category 缺 format 键时兜底空串(不得产出 "None"/"XXXX" 脏分类名)"""
    assert AddCategoryAction({}).format == ""
    assert AddCategoryAction({"format": "AUTO-${required_seeding_time}"}).format == "AUTO-${required_seeding_time}"


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


def test_add_category_creates_named_category():
    """建分类时 create_category 必须收到真实分类名(None 会在 qB 侧留下名为 None 的脏分类)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(category=""), client)
        assert AddCategoryAction({"format": "AUTO-A"}).execute(ctx).is_ok
        assert ("create_category", "AUTO-A") in client.calls, f"分类名丢失: {client.calls}"


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
            def relocate_execute(self, hashes, path, confirm=False):
                calls.append((list(hashes), path, confirm))
                return [{"cls": "confirm", "form": "alias"}]

        mgr.ctx.relocate = _Relocate()
        r = MoveToAction({"path": r"R:\New"}).execute(ctx)
        assert r.is_skipped, f"需确认的形态只能 skip: {r}"
        assert calls == [([ctx.hash], r"R:\New", False)], f"规则侧不得请求确认: {calls}"
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
