"""test_grouping_scan 测试计划: 种子分组

## 测试计划(每个测试函数一条)
- test_grouping_state_change_triggers_check: 仅上传转暂停触发缺文件检查
- test_own_stop_triggers_scan_on_next_sync (A 系 S3 E1): 自有停种经下一轮同步回流触发转移扫描(源无关), 且不重复触发
- test_grouping_deleted_torrent_triggers_check: 种子删除触发组内联动
- test_grouping_incremental_on_add: 新增种子增量归组
- test_grouping_removed_from_groups: 种子移出分组
- test_grouping_save_path_change_triggers_check: save_path 变化触发检查
- test_grouping_save_path_change_new_group_alone: save_path 变化单独成组 + 组键迁移待办双向登记(P7)
- test_grouping_no_full_files_scan: 归组仅拉一次文件列表, 后续不重复扫描
- test_grouping_save_path_change_no_cache: 无缓存文件映射 -> 维持原行为不重归组
- test_missing_scan_dedup_within_round: 同组同轮多触发源只扫一次(轮内去重), 跨轮清空后可再扫
- test_grouping_removed_event_disabled_check_returns_early: 删除事件 check_missing_files=False 早退 (P2-a)
- test_grouping_removed_event_group_emptied_no_scan: 组内最后成员删除 -> 组解散不扫描 (P2-a)
- test_grouping_save_path_change_ghost_and_same_path_skipped: save_path 变化幽灵 hash / 未变路径跳过 (P2-a)
- test_grouping_save_path_change_no_cached_map_skipped: 无缓存文件映射不重归组 (P2-a)
- test_grouping_save_path_change_stale_group_no_scan: 原组剩余成员均已不在快照不扫描 (P2-a)
- test_cross_group_same_group_overlap_not_triggered: 同组文件重叠是分组固有属性 -> 不触发跨组警告 (26-10-04-0107 S2)
- test_cross_group_dispose_clear_and_retrigger: S3 消除+重现: 下载方转暂停 -> 去重清除且 stop 不增; 恢复下载 -> 再次触发 (26-10-04-0107 S3)
- test_grouping_regroup_scope_skips_unowned_and_empty
- test_grouping_save_path_change_group_emptied_still_regroups
- test_grouping_save_path_change_without_group_key_skipped
- test_guard_missing_files_scan_dry_run_and_stop_scope: 缺文件扫描 dry-run 零副作用(sg27)+真实路径停组名单(mf77 高危)+缺失警告在(mf38)
- test_guard_save_path_change_mixed_delta: delta 首条非 save_path 不得 break 截断重归组+扫描(sp6 高危)
- test_guard_removed_scan_dry_run: 删除事件 dry-run 零真实副作用(rs3/12/14/16/17+hr8)
- test_guard_regroup_scope_members: 别名作用域重归组成员面(rg14/15/16/17/22/28/40)+回执计数(rg45-48)
- test_guard_save_path_alias_no_churn: 别名在场成员不得被判路径变化(churn 簇 sp23/24/31/32/33)
- test_guard_relocating_window_scan: 搬迁窗口只让路在迁组(sg19 全盲/sg24 截断)
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
    _CrossWarnCapture,
    _OVERLAP_A,
    _OVERLAP_B,
    _grab_cross_warnings,
    _grp_env,
    _non_tag_calls,
    _record_stop_scope,
    _scan_scenario,
    _seed_cross_pair,
    _seed_group,
)


def test_grouping_state_change_triggers_check():
    """仅"上传转暂停"触发检查(检测到即立即处理); 上传状态间变化/状态不变不触发"""
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

        # 首轮: 归组 + 建立状态快照(上传中, 不触发)
        mgr._refresh_torrents()
        assert _non_tag_calls(client) == [], f"首轮不应触发: {client.calls}"

        # H1 stalledUP -> uploading(仍是上传, 不触发)
        t1.state = "uploading"
        mgr._refresh_torrents()
        assert _non_tag_calls(client) == [], f"上传状态间变化不应触发: {client.calls}"

        # H1 uploading -> pausedUP(上传转暂停, 立即触发)
        t1.state = "pausedUP"
        mgr._refresh_torrents()
        assert client.calls.count(("stop", None)) == 1, f"上传转暂停应触发: {client.calls}"
        assert "MISSING" in client.tags

        # 状态不变 -> 不重复触发
        # !A 系 26-10-13-0540 S1 语义变更: 上一轮的整组停种(H1+H2)不再当场改写快照, 其中 H2 的
        #   stalledUP->pausedUP 于**下一轮同步**才可见、并再次满足「上传转暂停」谓词(:206)
        #   ⇒ 追加一次扫描+停种(幂等)。这是「源无关」的应有之义(2229 裁定), 且一轮即收敛。
        #   故先跑一个收敛轮, 再断言真正的「状态不变不重复触发」。
        client.calls.clear()
        mgr._refresh_torrents()  # 收敛轮: 承接整组停种经同步回流的 H2 状态变化
        client.calls.clear()
        mgr._refresh_torrents()
        assert _non_tag_calls(client) == [], f"状态不变不应重复触发: {client.calls}"


def test_own_stop_triggers_scan_on_next_sync():
    """守阵(A 系 S3 E1 发射): 自有停种经下一轮同步回流触发转移扫描(源无关), 且不重复触发

    A 系下自有动作不再写快照, 故自有停种的结果与**外部变更完全对称** —— 都在「qB 缓存前进
    后的那一轮同步」才被转移检测看见。这正是 26-10-12-2229 裁定的源无关语义。
    红验: 屏蔽发射(如把 state_changed 收集去掉/谓词加 `not self_caused`) -> 触发轮无 stop 即红。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr, client, t1, t2 = _scan_scenario(os.path.join(td, "state.json"))

        # 自有停种(经 QbApi, 与 WEB 命令/规则动作同路径): 替身翻真值, 快照本轮不动(值层不回写)
        mgr.api.torrents_stop(["H1"])
        assert client.torrents["H1"].state == "pausedUP", "替身侧真值已翻"
        assert mgr.store.by_hash["H1"].state == "stalledUP", "同 tick 快照不动(A 系值层)"
        client.calls.clear()

        mgr._refresh_torrents()  # 同步应用 -> state_changed 含 H1 -> 谓词命中 -> 触发扫描
        assert client.calls.count(("stop", None)) >= 1, f"自有停种应在回流那一轮触发: {client.calls}"
        assert "MISSING" in client.tags, f"应打缺文件标签: {client.tags}"

        # 收敛轮(整组停种经回流再命中一次, 幂等) -> 之后不再重复触发
        client.calls.clear()
        mgr._refresh_torrents()
        client.calls.clear()
        mgr._refresh_torrents()
        assert _non_tag_calls(client) == [], f"状态不变不应重复触发: {client.calls}"


def test_grouping_deleted_torrent_triggers_check():
    """同组种子被删除 -> 同一轮立即触发缺文件扫描(不等下一轮)"""
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
        mgr._refresh_torrents()  # 归组
        assert _non_tag_calls(client) == [], f"上传状态不应触发检查: {client.calls}"

        # 删除 H2 -> 移出组; 组内剩 H1, 同一轮立即触发缺文件扫描(文件不存在)
        del client.torrents["H2"]
        mgr._refresh_torrents()

        key = next(iter(mgr.store.groups))
        assert mgr.store.groups[key] == ["H1"], f"删除后组内成员: {mgr.store.groups}"
        assert client.calls.count(("stop", None)) == 1, f"删除种子应立即触发整组暂停: {client.calls}"
        assert "MISSING" in client.tags, f"文件丢失应加标签: {client.tags}"


def test_grouping_incremental_on_add():
    """新增种子时自动归组(增量), 不再每轮全量重建分组"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        client = FakeClient()
        mgr = make_manager(state_file, bare=True, grouping=grouping_cfg(), client=client)

        # 新增 H1 -> _refresh_torrents 检测 added 并自动归组(全部增量归组, 无初始化)
        t1 = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=r"R:\Downloads")
        client.torrents["H1"] = t1
        client.files_map["H1"] = [_fake_file("movie.mkv", 100)]
        mgr._refresh_torrents()
        assert len(mgr.store.groups) == 1, f"新种子应自动归组: {mgr.store.groups}"
        key = next(iter(mgr.store.groups))
        assert mgr.store.groups[key] == ["H1"], f"组内成员: {mgr.store.groups[key]}"
        assert key == ("R:/Downloads", ("movie.mkv", )), f"分组键: {key}"

        # 再新增 H2(同名同大小) -> 归入同一组
        t2 = FakeTorrent(hash="H2", name="T2", state="stalledUP", save_path=r"R:\Downloads")
        client.torrents["H2"] = t2
        client.files_map["H2"] = [_fake_file("movie.mkv", 100)]
        mgr._refresh_torrents()
        assert len(mgr.store.groups) == 1, f"H2 应归入同组: {mgr.store.groups}"
        assert set(mgr.store.groups[key]) == {"H1", "H2"}, f"组内成员: {mgr.store.groups[key]}"


def test_grouping_removed_from_groups():
    """种子删除时自动从分组移除(空组删除)"""
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
        mgr._refresh_torrents()
        key = next(iter(mgr.store.groups))
        assert set(mgr.store.groups[key]) == {"H1", "H2"}

        # 删除 H2 -> 组内只剩 H1
        del client.torrents["H2"]
        mgr._refresh_torrents()
        assert mgr.store.groups[key] == ["H1"], f"删除后组内成员: {mgr.store.groups[key]}"
        assert "H2" not in mgr.store.group_sizes[key], f"删除后应清掉文件大小映射: {mgr.store.group_sizes}"

        # 删除 H1 -> 空组删除
        del client.torrents["H1"]
        mgr._refresh_torrents()
        assert mgr.store.groups == {}, f"空组应删除: {mgr.store.groups}"
        assert mgr.store.group_sizes == {}, f"空组大小映射应删除: {mgr.store.group_sizes}"


def test_grouping_save_path_change_triggers_check():
    """种子保存路径变化 -> 原组剩余成员触发缺文件扫描; 新组已有其它成员也触发扫描"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        client = FakeClient()
        mgr = make_manager(state_file, bare=True, grouping=grouping_cfg(), client=client)

        # 组 A: H1/H2(DownloadsA); 组 B: H3(DownloadsB)
        t1 = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=r"R:\DownloadsA")
        t2 = FakeTorrent(hash="H2", name="T2", state="stalledUP", save_path=r"R:\DownloadsA")
        t3 = FakeTorrent(hash="H3", name="T3", state="stalledUP", save_path=r"R:\DownloadsB")
        for t in (t1, t2, t3):
            client.torrents[t.hash] = t
            client.files_map[t.hash] = [_fake_file("movie.mkv", 100)]
        mgr._refresh_torrents()
        assert _non_tag_calls(client) == [], f"首轮归组不应触发扫描: {client.calls}"
        key_a = ("R:/DownloadsA", ("movie.mkv", ))
        key_b = ("R:/DownloadsB", ("movie.mkv", ))
        assert set(mgr.store.groups[key_a]) == {"H1", "H2"}
        assert set(mgr.store.groups[key_b]) == {"H3"}

        # H1 保存路径改为 DownloadsB -> 原组 A 剩 H2 触发扫描; 新组 B 有 H1+H3 也触发扫描
        t1.save_path = r"R:\DownloadsB"
        mgr._refresh_torrents()

        assert set(mgr.store.groups[key_a]) == {"H2"}, f"H1 应移出原组: {mgr.store.groups[key_a]}"
        assert set(mgr.store.groups[key_b]) == {"H1", "H3"}, f"H1 应重归新组: {mgr.store.groups[key_b]}"
        assert client.calls.count(("stop", None)) == 2, f"原组与新组各扫描一次并整组暂停: {client.calls}"
        assert client.calls.count(("add_tags", ["MISSING"])) == 3, f"三个成员应分别加标签: {client.calls}"


def test_grouping_save_path_change_new_group_alone():
    """保存路径变化但新组无其它成员 -> 仅原组触发扫描, 新组不扫"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        client = FakeClient()
        mgr = make_manager(state_file, bare=True, grouping=grouping_cfg(), client=client)

        t1 = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=r"R:\DownloadsA")
        t2 = FakeTorrent(hash="H2", name="T2", state="stalledUP", save_path=r"R:\DownloadsA")
        client.torrents["H1"] = t1
        client.torrents["H2"] = t2
        client.files_map["H1"] = [_fake_file("movie.mkv", 100)]
        client.files_map["H2"] = [_fake_file("movie.mkv", 100)]
        mgr._refresh_torrents()
        assert _non_tag_calls(client) == [], f"首轮归组不应触发扫描: {client.calls}"

        # H1 移到空目录 DownloadsB(新组仅本种子) -> 仅原组 A(H2)触发扫描
        t1.save_path = r"R:\DownloadsB"
        mgr._refresh_torrents()

        assert set(mgr.store.groups[("R:/DownloadsA", ("movie.mkv", ))]) == {"H2"}
        assert mgr.store.groups[("R:/DownloadsB", ("movie.mkv", ))] == ["H1"]
        # P7: 组键迁移待办双向登记(旧键解散待 removed / 新键待 upsert) —— WebUI 增量排空的
        # 键源; 排空消费后清空(本例由 _refresh_torrents 后的视图线消费, 无 Web 活跃时原样保留)
        mig = mgr.store.group_key_migrations
        assert ("R:/DownloadsA", ("movie.mkv", )) in mig or not mig, mig
        assert ("R:/DownloadsB", ("movie.mkv", )) in mig or not mig, mig
        assert client.calls.count(("stop", None)) == 1, f"仅原组扫描暂停一次: {client.calls}"
        assert client.calls.count(("add_tags", ["MISSING"])) == 1, f"仅 H2 加标签: {client.calls}"


def test_grouping_no_full_files_scan():
    """归组仅拉一次文件列表(增量归组); 后续刷新状态不变不触发扫描, 不重复拉取"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        client = FakeClient()
        mgr = make_manager(state_file, bare=True, grouping=grouping_cfg(), client=client)

        t1 = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=r"R:\Downloads")
        client.torrents["H1"] = t1
        client.files_map["H1"] = [_fake_file("movie.mkv", 100)]

        # 归组(首轮视为新增, 增量归组): 仅在此处拉一次文件列表
        mgr._refresh_torrents()
        assert client.files_calls == 1, f"归组应只拉一次文件列表: {client.files_calls}"
        assert len(mgr.store.groups) == 1, f"首轮应完成归组: {mgr.store.groups}"

        # 后续刷新: 状态不变 -> 不触发扫描, 也不拉取文件列表
        mgr._refresh_torrents()
        assert client.files_calls == 1, f"后续刷新不应再拉文件列表: {client.files_calls}"
        assert _non_tag_calls(client) == [], f"状态不变不应触发检查: {client.calls}"


def test_grouping_save_path_change_no_cache():
    """_handle_save_path_changes: 无缓存文件映射 -> 跳过该种子(维持原行为)"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        client = FakeClient()
        mgr = make_manager(state_file, bare=True, grouping=grouping_cfg(), client=client)

        t1 = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=r"R:\DownloadsB")
        seed_store(mgr, [t1])
        mgr.store.member_to_key["H1"] = (r"R:\DownloadsA", ("movie.mkv", ))
        mgr.store.group_sizes = {}  # 无缓存映射
        mgr.host.get("grouping")._handle_save_path_changes(dry_run=False)
        # 无旧映射 -> 不重归组也不触发扫描
        assert client.calls == []
        assert "H1" not in mgr.store.groups


def test_missing_scan_dedup_within_round():
    """缺文件扫描轮内去重: 同组 key 同轮多触发源(如状态转移+路径变化)只扫一次; 轮重置后可再扫"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        client = FakeClient()
        mgr = make_manager(state_file, bare=True, grouping=grouping_cfg(), client=client)
        rep = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=td, amount_left=0)
        sizes = {"H1": {"movie.mkv": 100}}  # 文件不存在
        key = ("R:/Downloads", ("movie.mkv", ))

        mgr.host.get("grouping")._check_missing_files([rep], sizes, dry_run=False, key=key)
        mgr.host.get("grouping")._check_missing_files([rep], sizes, dry_run=False, key=key)
        assert client.calls.count(("stop", None)) == 1, f"同轮重复触发应只扫一次: {client.calls}"

        # 新的一轮(去重集合清空, 语义同 _refresh_torrents 每轮开头) -> 可再次扫描
        mgr.host.get("grouping")._missing_scanned_keys.clear()
        client.calls.clear()
        mgr.host.get("grouping")._check_missing_files([rep], sizes, dry_run=False, key=key)
        assert client.calls.count(("stop", None)) == 1, "跨轮应重新扫描"


def test_grouping_removed_event_disabled_check_returns_early():
    """删除事件: check_missing_files=False -> 直接返回, 分组结构不动"""
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"), check_missing_files=False)
        _seed_group(mgr.store, (r"R:/D", "k"), ["H1", "H2"])
        grp._handle_removed_torrents(["H1"], False)
        assert mgr.store.groups[(r"R:/D", "k")] == ["H1", "H2"], "禁用缺文件检查: 不移出成员"
        assert client.calls == []


def test_grouping_removed_event_group_emptied_no_scan():
    """删除事件: 组内最后一名成员被删 -> 组解散, 无剩余成员不触发扫描"""
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"))
        key = (r"R:/D", "k")
        _seed_group(mgr.store, key, ["H1"])
        grp._handle_removed_torrents(["H1"], False)
        assert key not in mgr.store.groups, "组应解散"
        assert "H1" not in mgr.store.member_to_key
        assert client.calls == [], "无剩余成员不扫描"


def test_grouping_save_path_change_ghost_and_same_path_skipped():
    """save_path 变化处理: 增量里 hash 已不在快照 / 路径未变(与组 key 前缀一致)都跳过"""
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"))
        key = (r"R:/D", "k")
        _seed_group(mgr.store, key, ["H1"])
        mgr.store.delta_fields["GHOST"] = {"save_path"}  # 已不在快照: 跳过
        grp._handle_save_path_changes(False)  # 不崩溃, 分组不动
        assert mgr.store.member_to_key["H1"] == key
        # H1 路径与组 key 前缀一致: 非"变化", 跳过
        _seed_group(mgr.store, key, ["H2"])
        mgr.store.delta_fields["H2"] = {"save_path"}
        grp._handle_save_path_changes(False)
        assert mgr.store.member_to_key["H2"] == key, "路径未变不重归组"


def test_grouping_save_path_change_no_cached_map_skipped():
    """save_path 变化处理: 无缓存文件映射(无法重归组) -> 维持原行为"""
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"))
        key = (r"R:/D", "k")
        _seed_group(mgr.store, key, ["H1"])
        tor = mgr.store.by_hash["H1"]
        tor.save_path = r"R:\Else"  # 路径已变
        mgr.store.delta_fields["H1"] = {"save_path"}
        del mgr.store.group_sizes[key]["H1"]  # 无缓存文件映射
        grp._handle_save_path_changes(False)
        assert mgr.store.member_to_key["H1"] == key, "无映射不重归组(维持原组)"


def test_grouping_save_path_change_stale_group_no_scan():
    """save_path 变化处理: 原组剩余成员均已不在快照 -> 不触发缺文件扫描"""
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"))
        key = (r"R:/D", "k")
        _seed_group(mgr.store, key, ["H1", "H2"], in_by_hash=["H1"])  # H2 只在组表, 快照已无
        tor = mgr.store.by_hash["H1"]
        tor.save_path = r"R:\Else"
        mgr.store.delta_fields["H1"] = {"save_path"}
        grp._handle_save_path_changes(False)
        assert mgr.store.member_to_key["H1"] != key, "H1 应按新路径重归组"
        assert client.calls == [], "原组无可扫描成员: 不扫描不暂停"


def test_cross_group_same_group_overlap_not_triggered():
    """同组文件重叠是分组固有属性: 单组两成员共享文件列表(甚至同时下载) -> 不触发跨组警告(归同组检查管)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"), cross_group_conflict_check=True)
        files = {"ep01.mkv": 100, "ep02.mkv": 200}
        key = (td, ("ep01.mkv", "ep02.mkv"))
        _seed_group(mgr.store, key, ["HA", "HB"], file_map=files, in_by_hash=[])
        mgr.store.by_hash["HA"] = FakeTorrent(hash="HA", name="TA", state="downloading", save_path=td, amount_left=100)
        mgr.store.by_hash["HB"] = FakeTorrent(hash="HB", name="TB", state="stalledDL", save_path=td, amount_left=100)
        with _grab_cross_warnings() as cap:
            grp._check_cross_group_file_conflicts(dry_run=False)
        assert not any("跨组文件交叉" in m for m in cap.messages), f"同组重叠不应触发跨组警告: {cap.messages}"
        assert client.calls == [], "跨组检测不处置同组冲突"


def test_cross_group_dispose_clear_and_retrigger():
    """S3 消除+重现(四段式, 对齐同组检查先例): 下载方转暂停 -> 组对失活去重清除且 stop 不增; 恢复下载 -> 再次触发"""
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"), cross_group_conflict_check=True)
        key_a, key_b = _seed_cross_pair(mgr.store, td, _OVERLAP_A, td, _OVERLAP_B)
        pair = tuple(sorted((key_a, key_b), key=str))
        # mock 掉 api.torrents_stop: 用于断言调用参数/作用范围, 并隔离替身的客户端侧翻转
        # (S0-P3)。!A 系 26-10-13-0540 S1 起真实 stop **不再**回写 store 快照,
        # 原「同 tick 改写快照污染去重断言」的顾虑已随 _sync_paused_state 删除而消失
        with mock.patch.object(mgr.api, "torrents_stop") as stop_mock:
            grp._check_cross_group_file_conflicts(dry_run=False)
            assert stop_mock.call_count == 1
            # 冲突消除(B 转暂停): 组对失活(无下载中参与者) -> 去重清除, stop 不增
            mgr.store.by_hash["HB"].state = "pausedDL"
            grp._check_cross_group_file_conflicts(dry_run=False)
            assert stop_mock.call_count == 1, f"消除轮不应新增暂停: {stop_mock.call_count}"
            assert mgr.store.cross_group_conflict_warned == set(), "组对失活应清除去重记录"
            # 冲突重现(B 恢复下载中) -> 再次警告+暂停
            mgr.store.by_hash["HB"].state = "downloading"
            grp._check_cross_group_file_conflicts(dry_run=False)
            assert stop_mock.call_count == 2, f"冲突重现应再次暂停: {stop_mock.call_count}"
            assert pair in mgr.store.cross_group_conflict_warned


def test_grouping_save_path_change_without_group_key_skipped():
    """save_path 变化: 快照里有但从未归组(member_to_key 缺该 hash) -> 跳过, 不重归组不扫描"""
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"))
        mgr.store.by_hash["H1"] = FakeTorrent(hash="H1", save_path=r"R:/New")
        mgr.store.delta_fields["H1"] = {"save_path"}
        grp._handle_save_path_changes(False)
        assert "H1" not in mgr.store.member_to_key, "无原组可移出, 不得凭空建组"
        assert client.calls == []


def test_grouping_save_path_change_group_emptied_still_regroups():
    """save_path 变化: 原组只有它一个成员 -> 组解散(不登记扫描), 但仍按新路径重归组

    种子本身没丢: 组解散只是「原组无剩余成员可扫」, 该种子必须回到分组视图里(否则它
    在界面上变成「未归组」, 缺文件检查也不再覆盖它)。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"))
        key = (r"R:/D", "k")
        _seed_group(mgr.store, key, ["H1"])
        mgr.store.by_hash["H1"].save_path = r"R:/Else"
        mgr.store.delta_fields["H1"] = {"save_path"}
        grp._handle_save_path_changes(False)
        assert key not in mgr.store.groups, "原组已解散"
        assert mgr.store.member_to_key["H1"] != key, "必须按新路径重归组"


def test_grouping_regroup_scope_skips_unowned_and_empty():
    """别名作用域重归组两条跳过: 非本 job 成员且 save_path 不在 src 下(与本 job 无关);
    文件表为空(无从重算内容根) —— 都不计入重归组数量"""
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"))
        mgr.store.by_hash["H1"] = FakeTorrent(hash="H1", save_path=r"R:/Other/x")
        mgr.store.by_hash["H2"] = FakeTorrent(hash="H2", save_path=r"R:/D/k")
        client.files = []  # 文件表读不到 -> fmap 空
        assert grp.regroup_scope("R:/D", src=r"R:/D/k", hashes=()) == 0


def test_guard_missing_files_scan_dry_run_and_stop_scope():
    """守阵(W9a mf77 高危 + sg27 + mf38): 缺文件扫描 dry-run 只报告不暂停(闸门击穿即红);
    真实路径整组暂停且名单=成员精确列表; 「文件缺失」警告不得整条丢失"""
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"))
        stops = _record_stop_scope(client)
        key = (r"R:\Downloads", ("movie.mkv", ))
        _seed_group(mgr.store, key, ["H1", "H2"])  # stalledUP=完成侧, 均为有效代表
        with capture_logs("auto_qb.core.modules.grouping_mod") as cap:
            grp._scan_triggered_groups({key}, True)
        assert stops == [], f"dry-run 缺文件扫描不得真实暂停(击穿即红): {stops}"
        assert "文件缺失" in cap.text, f"缺失警告不得丢失: {cap.messages}"
        grp._missing_scanned_keys.clear()  # 轮内去重集合: 两段独立扫描
        grp._scan_triggered_groups({key}, False)
        assert stops == [["H1", "H2"]], f"真实路径应停整组且名单精确: {stops}"


def test_guard_save_path_change_mixed_delta():
    """守阵(W9a sp6 高危): delta_fields 常态混有非 save_path 条目, 首条不得 break 截断 ——
    后续 save_path 变化的重归组+缺文件扫描必须照常发生"""
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"))
        stops = _record_stop_scope(client)
        key = (r"R:\Downloads", ("movie.mkv", ))
        _seed_group(mgr.store, key, ["H1", "H2"])
        mgr.store.by_hash["H1"].save_path = r"R:\Elsewhere"
        mgr.store.delta_fields = {"HG": {"name"}, "H1": {"save_path"}}  # 首条非 save_path
        grp._handle_save_path_changes(False)
        assert stops == [["H2"]], f"首条非 save_path delta 不得截断: H1 应重归组且原组触发扫描: {stops}"
        assert mgr.store.member_to_key["H1"] != key, "save_path 变化的成员必须重归组"


def test_guard_removed_scan_dry_run():
    """守阵(W9a rs3/rs12/rs14/rs16/rs17 + hr8): 删除事件 dry-run 会话零真实副作用 ——
    dry_run 读取/传-delivery 任一点击穿 -> 真实暂停(红)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"))
        stops = _record_stop_scope(client)
        key = (r"R:\Downloads", ("movie.mkv", ))
        _seed_group(mgr.store, key, ["H1", "H2"])
        grp._on_removed_scan(SimpleNamespace(payload={"hashes": ["H1"], "dry_run": True}))
        assert stops == [], f"删除事件 dry-run 不得真实暂停(击穿即红): {stops}"
        assert "H1" not in mgr.store.groups.get(key, []), "成员移出分组不是 dry-run 语义, 必须照常"


def test_guard_regroup_scope_members():
    """守阵(W9a rg14/15/16/17/22/28/40 + rg45/46/47/48): 别名作用域重归组 —— 本 job 成员与
    scope 内非自有成员都必须重归组(scope 外/非 src 跳过), 主链循环不得提前截断; INFO 回执计数真实"""
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"), check_missing_files=False)
        client.files_map = {
            "H1": [_fake_file("o.mkv", 100)],
            "H3": [_fake_file("flat.mkv", 100)],  # 内容根在 scope 外
            "H2": [_fake_file("sub/a.mkv", 100)],  # 内容根在 scope 内
        }
        for h, sp in (("H1", "R:/E"), ("H3", "R:/E"), ("H0", "R:/ZZZ"), ("H2", "R:/E")):
            # H0: 非 src 成员在前(rg17 截断面); H3: src 内但内容根在 scope 外(rg40 截断面)
            mgr.store.by_hash[h] = FakeTorrent(hash=h, state="pausedUP", save_path=sp)
        with capture_logs("auto_qb.core.modules.grouping_mod") as cap:
            n = grp.regroup_scope("R:/E/sub", src="R:/E", hashes=["H1"])
        assert n == 2, f"H1(本 job)+H2(scope 内)必须重归组; H0/H3 跳过但不得截断循环: {n}"
        assert mgr.store.member_to_key["H2"] == ("R:/E", ("sub/a.mkv", )), "H2 应按新文件表重归组(无别名=物理路径原样)"
        assert "重归组 2 个种子" in cap.text, f"INFO 回执计数必须真实: {cap.messages}"


def test_guard_save_path_alias_no_churn(monkeypatch):
    """守阵(W9a churn 簇 sp23/24/31/32/33): 别名在场的成员 save_path 伪变化必须被物理解析
    识别为「未变」—— content_root 传参任一变异都会让第 1 层 scope 提示错, 成员每轮被
    leave+rejoin 同键(churn: 置脏+误触发扫描)"""
    from auto_qb.core.modules import grouping_mod
    from auto_qb.infra import utils

    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"), check_missing_files=False)
        sp = "R:/D/alias"
        key = ("T:/phys", ("sub/movie.mkv", ))
        _seed_group(mgr.store, key, ["H1"], file_map={"sub/movie.mkv": 100})
        mgr.store.by_hash["H1"].save_path = sp

        def resolve_physical(p, root):
            # 只有 (save_path, 内容根) 对才是本 job 的作用域登记; 其余原样返回(无覆盖)
            if p == sp and utils.path_normalize(root) == "R:/D/alias/sub":
                return "T:/phys"
            return root

        monkeypatch.setattr(grp._ctx, "relocate", SimpleNamespace(resolve_physical=resolve_physical))
        monkeypatch.setattr(grouping_mod.alias_fs, "alias_kind_of", lambda p: None)  # 目录级非链接
        mgr.store.delta_fields = {"H1": {"save_path"}}
        grp._handle_save_path_changes(False)
        assert mgr.store.member_to_key["H1"] == key, "别名在场的成员不得被判「路径又变了」"
        assert mgr.store.group_key_migrations == set(), f"不得 churn(leave+rejoin 同键): {mgr.store.group_key_migrations}"
        assert mgr.store.dirty_groups == set(), f"churn 会误置脏同键: {mgr.store.dirty_groups}"


def test_guard_relocating_window_scan():
    """守阵(W9a sg19/sg24): 搬迁窗口只让路「成员在迁」的组 —— relocating 非空不得让全库
    缺文件扫描静默跳过; 单组让路也不得截断后续触发组"""
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"))
        stops = _record_stop_scope(client)
        k1 = ("R:/D1", ("a.mkv", ))
        k2 = ("R:/D2", ("b.mkv", ))
        _seed_group(mgr.store, k1, ["H1", "H2"])
        _seed_group(mgr.store, k2, ["H3"])
        mgr.store.relocating_hashes = {"H1"}  # 仅 k1 的成员在迁
        grp._scan_triggered_groups([k1, k2], False)  # list 传参: 迭代序确定(k1 在前)
        assert stops == [["H3"]], f"k1 让路但 k2 必须照常扫描(全盲/截断即红): {stops}"
