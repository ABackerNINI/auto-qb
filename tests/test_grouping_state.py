"""test_grouping_state 测试计划: 种子分组

## 测试计划(每个测试函数一条)
- test_grouping_size_mismatch_pauses_group: 新增种子归组时文件大小不一致 -> 整组暂停
- test_grouping_missing_files_pauses_group: 上传转暂停且文件丢失 -> 整组暂停 + MISSING
- test_pause_via_qb_webui_and_autoqb_webui_agree (A 系 S3 E2): qB 自身 WebUI 暂停 与 auto-qb WebUI 暂停 行为一致
- test_grouping_no_global_task: 无分组配置不创建全局任务
- test_grouping_replaces_per_torrent_missing_files: 归组替代逐种子缺文件检查
- test_group_members_not_in_group: 未归组 -> 仅自身
- test_group_members_in_group: 已归组 -> 全部成员
- test_leave_group_removes: 移出成员返回剩余组 key
- test_leave_group_empty_deletes: 组空删除返回 None
- test_leave_group_not_in_group: 不在组内返回 None
- test_group_has_downloading: 组内存在下载中成员判定
- test_group_has_downloading_delegates_to_store: _group_has_downloading 委托 store 单点等价断言(plan 26-10-05-0314 T9: 同输入同输出 + 路由钉死)
- test_assign_new_torrent_missing: 哈希不在 by_hash -> AttributeError 上抛(调用方保证存在)
- test_assign_new_torrent_files_error: 文件列表拉取异常 -> 异常上抛(由 run 主循环兜底)
- test_assign_to_group_empty_map: 空文件映射 -> 不归组
- test_check_missing_files_no_seeding_rep: 组内无已完成未校验种子 -> 不检查(暂停完成成员亦是代表)
- test_check_missing_files_size_mismatch: 文件存在但大小不符 -> 暂停 + MISSING
- test_check_missing_files_getsize_error: 文件读取 OSError -> 暂停 + MISSING
- test_check_missing_files_first_done_rep: 多已完成成员取第一个作代表, 非代表大小差异不影响
- test_check_missing_files_empty_sizes_map: 大小映射为空 -> 无文件可检查不误报
- test_check_missing_files_member_has_tag: 成员已带 MISSING 标签 -> 不重复 add_tags(仍暂停)
- test_check_missing_files_dry_run: 缺文件 dry-run -> 不暂停不加标签
- test_check_missing_files_qb_transitional_suffix_skips: 原名缺失但 .!qB 孪生存在 -> 过渡态本轮不判缺失(不暂停不打标, 计数+1)
- test_check_missing_files_transitional_skip_limit_reaches_missing: 过渡态连续 3 次未消除 -> 第 3 次按真实缺失暂停 + MISSING(残留兜底)
- test_check_missing_files_transitional_counter_resets_on_clean: 过渡态跳过后一次正常判定 -> 计数清零, 之后需重新连续 3 次
- test_check_missing_files_real_missing_no_twin: 原名缺失且无孪生 -> 照旧判缺失(回归保护)
- test_check_missing_files_dry_run_transitional: dry-run 下过渡态命中 -> 零外部副作用(不暂停不打标)
- test_grouping_errored_transition_pauses_group: 重校验发现缺失(进入 errored)-> 同轮整组暂停 + MISSING; 持续 errored 不重复触发
- test_grouping_state_transitions_first_round_and_empty_paths: 状态转移首轮无快照 / key 缺失 / 空组跳过 (P2-a)
- test_grouping_leave_group_member_index_missing_from_group_list: 索引有组表无的成员移出仍清理映射 (P2-a)
- test_grouping_missing_files_check_disabled_guard: 缺文件检查入口禁用守卫 (P2-a)
- test_grouping_physical_dir_three_layers
- test_grouping_state_transitions_first_round_no_snapshot_skipped
- test_grouping_third_party_link_alias_error_keeps_mark
- test_guard_state_transitions_mixed_delta: state_changed 首条非触发不得 break 截断扫描(st16 高危) + dry-run 闸(st22)
- test_guard_physical_dir_layer2_alias_resolved: 第2层目录级别名必须真解析(pd23/25/26/27/29/30/33 失效簇)
- test_guard_assign_move_cleans_old_and_dirty: 归组迁移幂等: 旧组摘除+新旧组双置脏(ag19/ag31/lv7)
"""

import logging

import os

import tempfile

from contextlib import contextmanager

from types import SimpleNamespace

from unittest import mock

import pytest

from helpers import FakeClient, FakeTorrent, _fake_file, capture_logs, grouping_cfg, make_manager, seed_store

from grouping_support import (
    _grp_env,
    _non_tag_calls,
    _record_stop_scope,
    _scan_scenario,
    _seed_group,
)


def test_grouping_size_mismatch_pauses_group():
    """新增种子归组时文件大小不一致 -> 警告 + 整组暂停(不加标签, 不再每轮检查)"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        client = FakeClient()
        mgr = make_manager(state_file, bare=True, grouping=grouping_cfg(), client=client)

        t1 = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=r"R:\Downloads")
        client.torrents["H1"] = t1
        client.files_map["H1"] = [_fake_file("movie.mkv", 100)]
        mgr._refresh_torrents()  # 归组完全增量: 首轮刷新视为新增, 经 _assign_new_torrent 归组
        assert _non_tag_calls(client) == [], f"单成员归组不应触发动作: {client.calls}"

        # H2 同名文件但大小不同 -> 加入同一组, 归组时立即检查大小一致性 -> 暂停整组
        t2 = FakeTorrent(hash="H2", name="T2", state="stalledUP", save_path=r"R:\Downloads")
        client.torrents["H2"] = t2
        client.files_map["H2"] = [_fake_file("movie.mkv", 200)]  # 同名不同大小
        mgr._refresh_torrents()

        assert client.calls.count(("stop", None)) == 1, f"归组时大小不一致应整组暂停: {client.calls}"
        assert "MISSING" not in client.tags, f"大小不一致不应加标签: {client.tags}"


def test_grouping_missing_files_pauses_group():
    """种子由上传转暂停 -> 同轮立即触发缺文件检查, 文件丢失 -> 整组暂停 + MISSING"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        client = FakeClient()
        mgr = make_manager(state_file, bare=True, grouping=grouping_cfg(), client=client)

        t1 = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=r"R:\Downloads")
        t2 = FakeTorrent(hash="H2", name="T2", state="stalledUP", save_path=r"R:\Downloads")
        client.torrents["H1"] = t1
        client.torrents["H2"] = t2
        client.files_map["H1"] = [_fake_file("movie.mkv", 100)]
        client.files_map["H2"] = [_fake_file("movie.mkv", 100)]

        # 首轮: 归组 + 建立状态快照(上传中, 无触发条件, 不扫描)
        mgr._refresh_torrents()
        assert _non_tag_calls(client) == [], f"上传状态不应触发检查: {client.calls}"

        # H1 由上传(stalledUP)转为暂停(pausedUP) -> 同一轮立即触发缺文件扫描(文件不存在)
        t1.state = "pausedUP"
        mgr._refresh_torrents()

        assert client.calls.count(("stop", None)) == 1, f"整组应暂停一次: {client.calls}"
        assert "MISSING" in client.tags, f"丢失应添加标签: {client.tags}"
        assert mgr.store.state_snapshot.get("H1") == "pausedUP", f"状态快照应更新: {mgr.store.state_snapshot}"


def test_pause_via_qb_webui_and_autoqb_webui_agree():
    """守阵(A 系 S3 E2 一致性): qB 自身 WebUI 暂停 与 auto-qb WebUI 暂停 行为一致(都触发扫描)

    合成回写时代两条路径不对称(自家写快照 → 自家停种被转移检测吞掉; 外部暂停则被看见)。
    A 系下 state 只由同步驱动 ⇒ 二者必须完全一致。
    红验: 任一条路径不触发 / 触发结果不同 -> 断言红。
    """
    def trigger_result(state_file, own: bool):
        mgr, client, t1, t2 = _scan_scenario(state_file)
        if own:
            mgr.api.torrents_pause(["H1"])  # auto-qb WebUI/命令路径(经 QbApi)
        else:
            t1.state = "pausedUP"  # qB 自身 WebUI 暂停(外部变更)
        client.calls.clear()
        mgr._refresh_torrents()
        return client.calls.count(("stop", None)), sorted(client.tags)

    with tempfile.TemporaryDirectory() as td:
        external = trigger_result(os.path.join(td, "ext.json"), own=False)
    with tempfile.TemporaryDirectory() as td:
        own = trigger_result(os.path.join(td, "own.json"), own=True)

    assert external[0] >= 1 and own[0] >= 1, f"两条路径都应触发扫描: 外部={external} 自有={own}"
    assert external == own, f"两条路径行为应完全一致: 外部暂停={external} vs auto-qb 暂停={own}"


def test_grouping_no_global_task():
    """分组为事件驱动, 不再创建周期轮询全局任务"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = make_manager(state_file, bare=True, grouping=grouping_cfg())
        names = {t.name for t in mgr.task_queue._fast}
        assert "grouping" not in names, f"事件驱动不应创建分组周期任务: {names}"

        # 未启用也不创建
        mgr2 = make_manager(state_file, bare=True, grouping=grouping_cfg(enabled=False))
        names2 = {t.name for t in mgr2.task_queue._fast}
        assert "grouping" not in names2, f"未启用也不应创建分组任务: {names2}"


def test_grouping_replaces_per_torrent_missing_files():
    """逐种子 missing_files 任务已移除, 缺文件检查统一由分组事件驱动承担"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        client = FakeClient()
        mgr = make_manager(state_file, bare=True, grouping=grouping_cfg(), check_missing_files=True, client=client)
        tor = FakeTorrent(hash="H1", name="T1")
        tor.tracker_conf = mgr.config.trackers["HHan"]  # 显式 setUp: 模拟 _refresh_torrents 匹配
        seed_store(mgr, [tor])

        mgr.host.get("rules")._create_torrent_tasks("H1")
        names = {t.name for t in mgr.task_queue._fast}
        assert "missing_files" not in names, f"不应创建逐种子检查: {names}"

        # 未启用分组同样不创建(逐种子检查已整体移除, 不再回退)
        mgr2 = make_manager(
            state_file, bare=True, grouping=grouping_cfg(enabled=False), check_missing_files=True, client=FakeClient()
        )
        seed_store(mgr2, [tor])
        mgr2.host.get("rules")._create_torrent_tasks("H1")
        names2 = {t.name for t in mgr2.task_queue._fast}
        assert "missing_files" not in names2, f"未启用分组也不应创建逐种子检查: {names2}"


def test_group_members_not_in_group():
    """_group_members: 未归组 -> [自身 hash] 单种子(无参考)"""
    mgr = make_manager("state.json", bare=True, grouping=grouping_cfg())
    assert mgr.host.get("grouping")._group_members("H1") == ["H1"]


def test_group_members_in_group():
    """_group_members: 已归组 -> 返回全部成员 hash"""
    mgr = make_manager("state.json", bare=True, grouping=grouping_cfg())
    mgr.store.member_to_key = {"H1": "g1", "H2": "g1"}
    mgr.store.groups = {"g1": ["H1", "H2"]}
    assert mgr.host.get("grouping")._group_members("H1") == ["H1", "H2"]


def test_leave_group_removes():
    """_leave_group: 移出成员, 组内仍有剩余 -> 返回组 key"""
    mgr = make_manager("state.json", bare=True, grouping=grouping_cfg())
    mgr.store.member_to_key = {"H1": "g1", "H2": "g1"}
    mgr.store.groups = {"g1": ["H1", "H2"]}
    mgr.store.group_sizes = {"g1": {"H1": {}, "H2": {}}}
    assert mgr.host.get("grouping")._leave_group("H1") == "g1"
    assert mgr.store.groups["g1"] == ["H2"]
    assert "H1" not in mgr.store.member_to_key
    assert "H1" not in mgr.store.group_sizes["g1"]


def test_leave_group_empty_deletes():
    """_leave_group: 组空 -> 删除整组返回 None"""
    mgr = make_manager("state.json", bare=True, grouping=grouping_cfg())
    mgr.store.member_to_key = {"H1": "g1"}
    mgr.store.groups = {"g1": ["H1"]}
    mgr.store.group_sizes = {"g1": {"H1": {}}}
    assert mgr.host.get("grouping")._leave_group("H1") is None
    assert mgr.store.groups == {}
    assert mgr.store.group_sizes == {}


def test_leave_group_not_in_group():
    """_leave_group: 种子不在任何组 -> None 且不抛异常"""
    mgr = make_manager("state.json", bare=True, grouping=grouping_cfg())
    assert mgr.host.get("grouping")._leave_group("NOPE") is None


def test_group_has_downloading():
    """_group_has_downloading: 组内存在活跃下载成员 -> True(成员状态读 store 快照)"""
    mgr = make_manager("state.json", bare=True, grouping=grouping_cfg())
    seed_store(mgr, [
        FakeTorrent(hash="H1", state="stalledDL"),
        FakeTorrent(hash="H2", state="stalledUP"),
    ])
    assert mgr.host.get("grouping")._group_has_downloading(["H1", "H2"]) is True
    assert mgr.host.get("grouping")._group_has_downloading(["H2"]) is False


def test_group_has_downloading_delegates_to_store():
    """_group_has_downloading 委托等价断言(plan 26-10-05-0314 T9): 谓词上移 store 单点后对同输入同输出

    生产输入形态(members == store.group_members(hash) 全量列表)与未归组/幽灵/空列表输入下,
    委托后输出 == 上移前逐字语义(内联参照实现) == store 直查; 末段以实例级替身钉死委托路由。
    """
    mgr = make_manager("state.json", bare=True, grouping=grouping_cfg())
    seed_store(
        mgr,
        [
            FakeTorrent(hash="H1", state="stalledDL"),  # 下载中
            FakeTorrent(hash="H2", state="stalledUP"),
            FakeTorrent(hash="H3", state="checkingDL"),  # 强制校验: is_downloading 且 is_checking -> 不算
            FakeTorrent(hash="H4", state="pausedDL"),
            FakeTorrent(hash="H5", state="stalledUP"),  # 未归组
            FakeTorrent(hash="H6", state="stalledDL"),  # 未归组且下载中
        ]
    )
    grp = mgr.host.get("grouping")
    store = mgr.store
    key_a, key_b = ("R:\\A", ("a.mkv", )), ("R:\\B", ("b.mkv", ))
    store.groups = {key_a: ["H1", "H2"], key_b: ["H3", "H4"]}
    store.member_to_key = {"H1": key_a, "H2": key_a, "H3": key_b, "H4": key_b}

    def reference(members):
        """上移前逐字语义(参照实现, 防上移走样的对照)"""
        by_hash = store.by_hash
        for h in members:
            if h not in by_hash:
                continue
            e = by_hash[h].state_enum
            if e.is_downloading and not e.is_stopped and not e.is_checking:
                return True
        return False

    # 同输入同输出: 委托后 == 参照实现 == store 直查(全量列表/未归组/不在库/幽灵/空列表)
    cases = [
        store.group_members("H1"),  # [H1, H2] 组内有下载中成员 -> True
        store.group_members("H3"),  # [H3, H4] checkingDL+pausedDL -> False
        store.group_members("H5"),  # [H5] 未归组做种 -> False
        store.group_members("H6"),  # [H6] 未归组下载中 -> True
        store.group_members("NOPE"),  # [NOPE] 不在库 -> False
        ["GHOST", "H5"],  # 幽灵成员 + 未归组做种 -> False
        [],  # 空列表 -> False
    ]
    for members in cases:
        expected = reference(members)
        assert grp._group_has_downloading(members) is expected, f"委托等价失败: {members}"
        if members and members[0] in store.by_hash:
            assert store.group_has_downloading(members[0]) is expected, f"store 直查不一致: {members}"
    assert grp._group_has_downloading(store.group_members("H1")) is True, "组内有下载中成员"
    assert grp._group_has_downloading(store.group_members("H3")) is False, "checkingDL 不算活跃下载"
    # 委托路由钉死: store 方法被替身接管 -> grouping 侧跟着变(证明本地不再持有谓词)
    store.group_has_downloading = lambda h: True
    assert grp._group_has_downloading(store.group_members("H3")) is True


def test_assign_new_torrent_missing():
    """_assign_new_torrent: 哈希不在 store 快照 -> AttributeError 上抛(调用方保证传入存在的 hash)"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        client = FakeClient()
        mgr = make_manager(state_file, bare=True, grouping=grouping_cfg(), client=client)
        with pytest.raises(AttributeError):
            mgr.host.get("grouping")._assign_new_torrent("NOPE", dry_run=False)
        assert client.files_calls == 0, "tor 不存在不应拉文件列表"


def test_assign_new_torrent_files_error():
    """_assign_new_torrent: 文件列表拉取异常 -> 异常上抛(不缓存, 由 run 主循环兜底), 不归组"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        client = FakeClient()
        mgr = make_manager(state_file, bare=True, grouping=grouping_cfg(), client=client)

        def boom(h):
            raise RuntimeError("api down")

        client.torrents_files = boom
        t1 = FakeTorrent(hash="H1", name="T1", state="stalledUP")
        seed_store(mgr, [t1])
        with pytest.raises(RuntimeError, match="api down"):
            mgr.host.get("grouping")._assign_new_torrent("H1", dry_run=False)
        assert client.calls == []
        assert "H1" not in mgr.store.member_to_key


def test_assign_to_group_empty_map():
    """_assign_to_group: 空文件映射 -> 不归组"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        client = FakeClient()
        mgr = make_manager(state_file, bare=True, grouping=grouping_cfg(), client=client)
        t1 = FakeTorrent(hash="H1", name="T1", state="stalledUP")
        mgr.host.get("grouping")._assign_to_group(t1, {}, dry_run=False)
        assert mgr.store.groups == {}
        assert client.calls == []


def test_check_missing_files_no_seeding_rep():
    """_check_missing_files: 组内无已完成未校验种子 -> 不检查; 暂停完成成员亦是有效代表"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        client = FakeClient()
        mgr = make_manager(state_file, bare=True, grouping=grouping_cfg(), client=client)
        members = [FakeTorrent(hash="H1", name="T1", state="pausedUP", amount_left=100)]
        mgr.host.get("grouping")._check_missing_files(members, {}, dry_run=False, key="K")
        assert client.calls == [], "未完成成员不应作为代表扫描"
        # 暂停已完成(amount_left=0): is_complete 判定下路径同样可扫, 缺文件触发暂停 + MISSING
        # (独立 key: 同 key 第二次调用会被轮内去重跳过, 此处单测的是参数变体而非多触发源)
        paused_done = FakeTorrent(hash="H2", name="T2", state="pausedUP", save_path=td, amount_left=0)
        mgr.host.get("grouping")._check_missing_files(
            [paused_done], {"H2": {
                "movie.mkv": 100
            }}, dry_run=False, key="K2"
        )
        assert client.calls.count(("stop", None)) == 1, f"暂停完成代表缺文件应暂停: {client.calls}"
        assert "MISSING" in client.tags


def test_check_missing_files_size_mismatch():
    """_check_missing_files: 文件存在但大小不符 -> 警告 + 整组暂停 + MISSING"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        client = FakeClient()
        mgr = make_manager(state_file, bare=True, grouping=grouping_cfg(), client=client)
        real = os.path.join(td, "movie.mkv")
        with open(real, "wb") as f:
            f.write(b"x" * 10)
        rep = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=td, amount_left=0)
        sizes = {"H1": {"movie.mkv": 999}}  # 期望 999, 实际 10
        mgr.host.get("grouping")._check_missing_files([rep], sizes, dry_run=False, key="K")
        assert client.calls.count(("stop", None)) == 1, f"大小不符应整组暂停: {client.calls}"
        assert "MISSING" in client.tags


def test_check_missing_files_getsize_error():
    """_check_missing_files: 文件读取 OSError -> 警告 + 整组暂停 + MISSING"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        client = FakeClient()
        mgr = make_manager(state_file, bare=True, grouping=grouping_cfg(), client=client)
        real = os.path.join(td, "movie.mkv")
        with open(real, "wb") as f:
            f.write(b"x" * 10)
        rep = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=td, amount_left=0)
        sizes = {"H1": {"movie.mkv": 10}}
        with mock.patch("os.path.getsize", side_effect=OSError("denied")):
            mgr.host.get("grouping")._check_missing_files([rep], sizes, dry_run=False, key="K")
        assert client.calls.count(("stop", None)) == 1, f"读取失败应整组暂停: {client.calls}"
        assert "MISSING" in client.tags


def test_check_missing_files_first_done_rep():
    """_check_missing_files: 多已完成成员取第一个作代表, 非代表大小映射差异不影响扫描结果"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        client = FakeClient()
        mgr = make_manager(state_file, bare=True, grouping=grouping_cfg(), client=client)
        real = os.path.join(td, "movie.mkv")
        with open(real, "wb") as f:
            f.write(b"x" * 10)
        t1 = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=td, amount_left=0)
        t2 = FakeTorrent(hash="H2", name="T2", state="stalledUP", save_path=td, amount_left=0)
        # 代表 H1 大小正确; 非代表 H2 期望大小错误(仅扫代表, 不应触发)
        sizes = {"H1": {"movie.mkv": 10}, "H2": {"movie.mkv": 999}}
        mgr.host.get("grouping")._check_missing_files([t1, t2], sizes, dry_run=False, key="K")
        assert client.calls == [], f"非代表成员大小差异不应触发: {client.calls}"
        # 代表 H1 大小错误 -> 触发(独立 key: 避开同轮去重, 单测参数变体)
        sizes2 = {"H1": {"movie.mkv": 999}, "H2": {"movie.mkv": 10}}
        mgr.host.get("grouping")._check_missing_files([t1, t2], sizes2, dry_run=False, key="K2")
        assert client.calls.count(("stop", None)) == 1, f"代表大小不符应整组暂停: {client.calls}"
        assert "MISSING" in client.tags


def test_check_missing_files_empty_sizes_map():
    """_check_missing_files: 大小映射为空 -> 无文件可检查, 不误报"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        client = FakeClient()
        mgr = make_manager(state_file, bare=True, grouping=grouping_cfg(), client=client)
        rep = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=td, amount_left=0)
        mgr.host.get("grouping")._check_missing_files([rep], {}, dry_run=False, key="K")
        assert client.calls == [], f"空大小映射不应触发扫描: {client.calls}"


def test_check_missing_files_member_has_tag():
    """_check_missing_files: 成员已带 MISSING 标签 -> 不重复 add_tags(仍暂停)"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        client = FakeClient()
        mgr = make_manager(state_file, bare=True, grouping=grouping_cfg(), client=client)
        rep = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=td, amount_left=0, tags="MISSING")
        sizes = {"H1": {"movie.mkv": 100}}  # 文件不存在
        mgr.host.get("grouping")._check_missing_files([rep], sizes, dry_run=False, key="K")
        assert client.calls.count(("stop", None)) == 1, f"缺文件仍应暂停: {client.calls}"
        assert ("add_tags", ["MISSING"]) not in client.calls, "已有标签不应重复添加"


def test_check_missing_files_dry_run():
    """_check_missing_files dry-run: 不暂停也不加标签"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        client = FakeClient()
        mgr = make_manager(state_file, bare=True, grouping=grouping_cfg(), client=client)
        rep = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=td, amount_left=0)
        sizes = {"H1": {"movie.mkv": 100}}  # 文件不存在
        mgr.host.get("grouping")._check_missing_files([rep], sizes, dry_run=True, key="K")
        assert client.calls == [], f"dry-run 不应暂停/加标签: {client.calls}"
        assert "MISSING" not in client.tags


def test_check_missing_files_qb_transitional_suffix_skips():
    """过渡态容忍(issue 26-09-21-0219): 原名缺失但 <原名>.!qB 孪生存在 -> 本轮不判缺失

    qB 移动种子时偶发把磁盘文件临时改名为 原名.!qB(qB 搬运未完成后缀), 改名窗口内
    原路径不存在属过渡态 —— 本轮整轮放弃判定: 不暂停、不打 MISSING 标签; 会话级
    连续计数 +1(残留兜底见 test_check_missing_files_transitional_skip_limit_reaches_missing)。
    """
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        client = FakeClient()
        mgr = make_manager(state_file, bare=True, grouping=grouping_cfg(), client=client)
        # 磁盘上只有 qB 搬运期的孪生文件(原名不存在) —— 模拟改名窗口
        with open(os.path.join(td, "movie.mkv.!qB"), "wb") as f:
            f.write(b"x" * 100)
        rep = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=td, amount_left=0)
        sizes = {"H1": {"movie.mkv": 100}}
        mgr.host.get("grouping")._check_missing_files([rep], sizes, dry_run=False, key="K")
        assert client.calls == [], f"过渡态不应暂停: {client.calls}"
        assert "MISSING" not in client.tags, "过渡态不应打标"
        assert mgr.store.transitional_missing_skips.get("K") == 1, "过渡态命中应计数 +1"


def test_check_missing_files_transitional_skip_limit_reaches_missing():
    """过渡态连续 3 次未消除 -> 第 3 次按真实缺失处理(暂停 + MISSING), 兜底 qB 残留后缀

    每次调用前清轮内去重集合模拟跨轮独立触发事件(事件驱动扫描, 同组同轮只扫一次)。
    日志断言用临时 handler 直挂模块 logger: QbManager 构造链会执行 setup_logging 清空
    root handlers, pytest 的 caplog 挂在 root 上会一并被清(实测 caplog.text 恒空)。
    """
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        client = FakeClient()
        mgr = make_manager(state_file, bare=True, grouping=grouping_cfg(), client=client)
        grouping = mgr.host.get("grouping")
        with open(os.path.join(td, "movie.mkv.!qB"), "wb") as f:
            f.write(b"x" * 100)
        rep = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=td, amount_left=0)
        sizes = {"H1": {"movie.mkv": 100}}

        records = []

        class _Capture(logging.Handler):
            def emit(self, record):
                records.append(record.getMessage())

        glog = logging.getLogger("auto_qb.core.modules.grouping_mod")
        cap = _Capture(level=logging.WARNING)
        glog.addHandler(cap)
        try:
            for _ in range(3):
                grouping._missing_scanned_keys.clear()  # 模拟跨轮: 下一个触发事件再判
                grouping._check_missing_files([rep], sizes, dry_run=False, key="K")
        finally:
            glog.removeHandler(cap)

        assert client.calls.count(("stop", None)) == 1, f"第 3 次应按真实缺失暂停: {client.calls}"
        assert "MISSING" in client.tags, "上限触发应添加 MISSING 标签"
        assert any("未消除" in m for m in records), f"上限分支应有可 grep 的「未消除」日志: {records}"
        assert any("疑似 qB 搬运过渡态" in m for m in records), "前两次容忍应有过渡态日志(取证锚)"


def test_check_missing_files_transitional_counter_resets_on_clean():
    """过渡态计数只在相邻过渡态间累积: 一次正常判定(文件恢复原名)后清零, 需重新连续 3 次"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        client = FakeClient()
        mgr = make_manager(state_file, bare=True, grouping=grouping_cfg(), client=client)
        grouping = mgr.host.get("grouping")
        rep = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=td, amount_left=0)
        sizes = {"H1": {"movie.mkv": 100}}
        original = os.path.join(td, "movie.mkv")
        twin = os.path.join(td, "movie.mkv.!qB")

        # 第 1 轮: 过渡态 -> 跳过, 计数 = 1
        with open(twin, "wb") as f:
            f.write(b"x" * 100)
        grouping._check_missing_files([rep], sizes, dry_run=False, key="K")
        assert client.calls == [] and mgr.store.transitional_missing_skips.get("K") == 1

        # 第 2 轮: qB 改回原名且大小一致 -> 正常判定, 计数清零
        os.rename(twin, original)
        grouping._missing_scanned_keys.clear()
        grouping._check_missing_files([rep], sizes, dry_run=False, key="K")
        assert client.calls == [], "文件齐全不应触发动作"
        assert "K" not in mgr.store.transitional_missing_skips, "正常判定应清零过渡态计数"

        # 第 3/4 轮: 再次过渡态 -> 计数从 1 重计, 两轮仍不判缺失(证明需重新连续 3 次)
        os.remove(original)
        with open(twin, "wb") as f:
            f.write(b"x" * 100)
        for _ in range(2):
            grouping._missing_scanned_keys.clear()
            grouping._check_missing_files([rep], sizes, dry_run=False, key="K")
            assert client.calls == [], f"清零后连续 2 次仍不应判缺失: {client.calls}"

        # 第 5 轮: 第 3 次连续过渡态 -> 兜底判缺失
        grouping._missing_scanned_keys.clear()
        grouping._check_missing_files([rep], sizes, dry_run=False, key="K")
        assert client.calls.count(("stop", None)) == 1, f"重新连续 3 次应兜底判缺失: {client.calls}"
        assert "MISSING" in client.tags


def test_check_missing_files_real_missing_no_twin():
    """回归保护: 原名缺失且无 .!qB 孪生 -> 照旧判缺失(暂停 + MISSING), 不受容忍逻辑影响"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        client = FakeClient()
        mgr = make_manager(state_file, bare=True, grouping=grouping_cfg(), client=client)
        rep = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=td, amount_left=0)
        sizes = {"H1": {"movie.mkv": 100}}  # 文件不存在, 也无孪生
        mgr.host.get("grouping")._check_missing_files([rep], sizes, dry_run=False, key="K")
        assert client.calls.count(("stop", None)) == 1, f"真实缺失应照旧暂停: {client.calls}"
        assert "MISSING" in client.tags


def test_check_missing_files_dry_run_transitional():
    """dry-run 下过渡态命中 -> 零外部副作用(不暂停、不加标签; 计数为会话内报告态)"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        client = FakeClient()
        mgr = make_manager(state_file, bare=True, grouping=grouping_cfg(), client=client)
        with open(os.path.join(td, "movie.mkv.!qB"), "wb") as f:
            f.write(b"x" * 100)
        rep = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=td, amount_left=0)
        sizes = {"H1": {"movie.mkv": 100}}
        mgr.host.get("grouping")._check_missing_files([rep], sizes, dry_run=True, key="K")
        assert client.calls == [], f"dry-run 过渡态不应暂停/加标签: {client.calls}"
        assert "MISSING" not in client.tags


def test_grouping_errored_transition_pauses_group():
    """重校验发现文件缺失(stalledUP -> missingFiles)-> 同轮触发缺文件扫描, 整组暂停 + MISSING;
    持续 errored 不重复触发"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        client = FakeClient()
        mgr = make_manager(state_file, bare=True, grouping=grouping_cfg(), client=client)

        t1 = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=r"R:\Downloads")
        t2 = FakeTorrent(hash="H2", name="T2", state="stalledUP", save_path=r"R:\Downloads")
        client.torrents["H1"] = t1
        client.torrents["H2"] = t2
        client.files_map["H1"] = [_fake_file("movie.mkv", 100)]
        client.files_map["H2"] = [_fake_file("movie.mkv", 100)]

        # 首轮: 归组 + 建立状态快照(上传中, 无触发条件, 不扫描)
        mgr._refresh_torrents()
        assert _non_tag_calls(client) == [], f"上传状态不应触发检查: {client.calls}"

        # H1 强制重校验发现文件缺失 -> missingFiles(errored) -> 同轮触发缺文件扫描(文件不存在)
        t1.state = "missingFiles"
        mgr._refresh_torrents()

        assert client.calls.count(("stop", None)) == 1, f"errored 转换应触发整组暂停: {client.calls}"
        assert "MISSING" in client.tags, f"丢失应添加标签: {client.tags}"

        # 持续 errored(状态不变) -> 不重复触发
        # !A 系 26-10-13-0540 S1: 整组停种结果下一轮经同步回流, H2 的 stalledUP->pausedUP 会
        #   再触发一次扫描(见 test_grouping_state_change_triggers_check 同款说明), 一轮即收敛
        client.calls.clear()
        mgr._refresh_torrents()  # 收敛轮: 承接整组停种经同步回流的 H2 状态变化
        client.calls.clear()
        mgr._refresh_torrents()
        assert _non_tag_calls(client) == [], f"持续 errored 不应重复触发: {client.calls}"


def test_grouping_state_transitions_first_round_and_empty_paths():
    """状态转移: 首轮无上轮快照跳过; key 缺失不触发; 触发组无可扫成员不扫描"""
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"))
        prev_up = FakeTorrent(state="stalledUP").state_enum  # 上传中
        cur_paused = FakeTorrent(state="pausedUP").state_enum  # 完成转暂停: 命中转移判据
        key = (r"R:/D", "k")
        # H1: 转移命中但未归组(key None); H2: 归组但快照已无(组内无可扫成员)
        mgr.store.state_changed = [("H1", cur_paused), ("H2", cur_paused)]
        mgr.store.state_snapshot["H1"] = prev_up
        mgr.store.state_snapshot["H2"] = prev_up
        mgr.store.member_to_key["H2"] = key
        mgr.store.groups[key] = ["H2"]
        grp._handle_state_transitions(False)
        assert client.calls == [], "三种空转路径都不得触发扫描/暂停"


def test_grouping_leave_group_member_index_missing_from_group_list():
    """移出分组: 成员索引有记录但组表已无该成员(索引/组表短暂不一致) -> 仍清理映射返回组 key"""
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"))
        key = (r"R:/D", "k")
        mgr.store.groups[key] = ["H2"]
        mgr.store.member_to_key["H1"] = key  # 索引有 H1, 组表没有
        mgr.store.group_sizes[key] = {"H1": {"movie.mkv": 100}, "H2": {"movie.mkv": 100}}
        remain = grp._leave_group("H1")
        assert remain == key, "组内仍有 H2: 返回组 key"
        assert "H1" not in mgr.store.group_sizes[key], "大小映射应清理"
        assert mgr.store.groups[key] == ["H2"]


def test_grouping_missing_files_check_disabled_guard():
    """缺文件检查入口: 配置禁用 -> 直接返回零动作(事件路径之外的守卫)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"), check_missing_files=False)
        grp._check_missing_files([FakeTorrent(hash="H1", state="stalledUP")], {}, False, (r"R:/D", "k"))
        assert client.calls == []


def test_grouping_physical_dir_three_layers(monkeypatch):
    """物理解析三层各自的保守出口(组键首元 = 物理内容根, 解析错了就是误并/裂组)

    ① 迁移模块缺席(装配未挂) -> 直接进别名层;
    ② 迁移模块抛错 -> 退回词法路径(异常不影响归组, 少并一组的代价 < 误并一组);
    ③ 别名层: 判为 junction 但解析结果与词法路径相同 -> 返回原路径(没搬家);
    ④ 别名层抛错 -> 保守返回词法路径。
    """
    from auto_qb.core.modules import grouping_mod

    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"))
        sp = r"R:/D/movie"

        class _BoomRelocate:
            def resolve_physical(self, *a):
                raise RuntimeError("迁移模块炸了")

        class _Moved:
            def resolve_physical(self, p, root):
                return r"T:/lib/movie"

        # ① relocate 缺席
        monkeypatch.setattr(grp._ctx, "relocate", None)
        assert grp._physical_dir(sp, sp) == sp
        # ② relocate 抛错 -> 词法路径
        monkeypatch.setattr(grp._ctx, "relocate", _BoomRelocate())
        assert grp._physical_dir(sp, sp) == sp
        # 迁移模块解析出不同物理路径 -> 直接采用(别名在场时组键首元应是 T)
        monkeypatch.setattr(grp._ctx, "relocate", _Moved())
        assert grp._physical_dir(sp, sp) == r"T:/lib/movie"

        # ③ 别名层判为 junction 但 realpath 与词法路径一致 -> 返回原路径
        monkeypatch.setattr(grp._ctx, "relocate", None)
        monkeypatch.setattr(grouping_mod.alias_fs, "alias_kind_of", lambda p: grouping_mod.alias_fs.KIND_JUNCTION)
        monkeypatch.setattr(
            grouping_mod.file_access, "get_file_access", lambda: SimpleNamespace(realpath_lexical=lambda p: p)
        )
        assert grp._physical_dir(sp, sp) == sp

        # ④ 别名层抛错 -> 词法路径
        def _alias_boom(p):
            raise OSError("stat 失败")

        monkeypatch.setattr(grouping_mod.alias_fs, "alias_kind_of", _alias_boom)
        assert grp._physical_dir(sp, sp) == sp


def test_grouping_third_party_link_alias_error_keeps_mark(monkeypatch):
    """第三方链接打标: 形态判定抛错 -> 静默跳过且**不清掉已有标记**

    打标是给迁移用的拒迁依据: 判不出来就维持现状, 绝不能把上一轮已确认的标记抹掉
    (抹掉等于放行迁移, 比漏标更危险)。
    """
    from auto_qb.core.modules import grouping_mod

    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"))
        key = (r"R:/D", "k")
        mgr.store.third_party_link_groups.add(key)

        def _alias_boom(p):
            raise OSError("stat 失败")

        monkeypatch.setattr(grouping_mod.alias_fs, "alias_kind_of", _alias_boom)
        grp._mark_third_party_link(key, r"R:/D", {"movie.mkv": 100})
        assert key in mgr.store.third_party_link_groups, "判不出来必须维持原标记"


def test_grouping_state_transitions_first_round_no_snapshot_skipped():
    """状态转移: 首轮无上一轮快照(state_snapshot 缺该 hash) -> 不视为变化, 零动作

    首轮把「完成转暂停」全量当状态变化会在启动瞬间对整库触发缺文件扫描 —— 这是
    与上传转暂停路径一致的口径(prev 缺失即跳过)。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"))
        key = (r"R:/D", "k")
        _seed_group(mgr.store, key, ["H1"])
        mgr.store.state_changed = [("H1", FakeTorrent(state="pausedUP").state_enum)]
        grp._handle_state_transitions(False)
        assert client.calls == [], "首轮无快照不得触发扫描/暂停"


def test_guard_state_transitions_mixed_delta():
    """守阵(W9a st16 高危 + st22): state_changed 常态混有非触发转移, 首条不得 break 截断 ——
    后续触发转移(上传转暂停)的缺文件扫描必须照常发生; dry-run 传递不得击穿"""
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"))
        stops = _record_stop_scope(client)
        key = (r"R:\Downloads", ("movie.mkv", ))
        _seed_group(mgr.store, key, ["H1", "H2"])
        mgr.store.state_snapshot = {
            "H0": FakeTorrent(state="stalledUP").state_enum,
            "H1": FakeTorrent(state="stalledUP").state_enum,
        }
        mgr.store.state_changed = [
            ("H0", FakeTorrent(state="stalledDL").state_enum),  # 非触发转移在前
            ("H1", FakeTorrent(state="pausedUP").state_enum),  # 上传转暂停触发在后
        ]
        grp._handle_state_transitions(False)
        assert stops == [["H1", "H2"]], f"首条非触发转移不得截断扫描(H1 转移应触发缺文件处置): {stops}"
        stops.clear()
        grp._missing_scanned_keys.clear()  # 轮内去重: 两段独立扫描
        grp._handle_state_transitions(True)
        assert stops == [], f"dry-run 转移扫描不得真实暂停(st22 击穿即红): {stops}"


def test_guard_physical_dir_layer2_alias_resolved(monkeypatch):
    """守阵(W9a pd23/25/26/27/29/30/33): 第 2 层目录级别名解析必须真生效 —— save_path 本身是
    junction 时解析结果才是组键首元; 判定/解析/比较任一点失效都会让静态别名两组不并组"""
    from auto_qb.core.modules import grouping_mod

    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"))
        sp = "R:/D/movie"
        # 第 1 层: 迁移模块在场但无 job 覆盖(原样返回) —— 不得提前 return 短路第 2 层(pd23)
        monkeypatch.setattr(grp._ctx, "relocate", SimpleNamespace(resolve_physical=lambda p, root: p))
        monkeypatch.setattr(
            grouping_mod.alias_fs,
            "alias_kind_of",
            lambda p: grouping_mod.alias_fs.KIND_JUNCTION if p == sp else None,
        )

        def fake_realpath(p):
            if p != sp:
                raise OSError("unexpected probe target")
            return "T:/lib/movie"

        monkeypatch.setattr(
            grouping_mod.file_access,
            "get_file_access",
            lambda: SimpleNamespace(realpath_lexical=fake_realpath),
        )
        assert grp._physical_dir(sp, sp) == "T:/lib/movie", "junction 别名必须解析出物理目录"


def test_guard_assign_move_cleans_old_and_dirty():
    """守阵(W9a ag19/ag31/lv7): 归组幂等迁移 —— 旧组必须摘除成员(幽灵双成员=成员数虚高/摘错组),
    新旧组都必须登记置脏(漏登记=增量冲突重算跳组)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"), check_missing_files=False)
        key1 = ("R:/D1", ("a.mkv", ))
        _seed_group(mgr.store, key1, ["H1"], file_map={"a.mkv": 100})
        t = mgr.store.by_hash["H1"]
        t.save_path = "R:/D2"
        grp._assign_to_group(t, {"b.mkv": 100})
        assert t.hash not in mgr.store.groups.get(key1, []), "旧组必须摘除成员(不得留幽灵)"
        key2 = mgr.store.member_to_key["H1"]
        assert key2 == ("R:/D2", ("b.mkv", )), "必须按新路径+新文件表归组"
        assert key1 in mgr.store.dirty_groups, "旧组必须置脏(冲突重算覆盖)"
        assert key2 in mgr.store.dirty_groups, "新组必须置脏(冲突重算覆盖)"
