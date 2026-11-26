"""test_grouping_conflict 测试计划: 种子分组

## 测试计划(每个测试函数一条)
- test_is_downloading_excludes_checking: 强制校验(checking*)不算下载中(62dbc25 修复)
- test_grouping_force_checking_not_conflict: 强制校验种子与下载中/已完成同组不触发冲突暂停
- test_grouping_download_conflict_multi_dl: 多下载冲突 -> 暂停 + 去重语义
- test_grouping_download_conflict_mixed: 已完成与下载中并存 -> 暂停
- test_grouping_download_conflict_dry_run: 冲突 dry-run 只报告不暂停不记录去重
- test_download_conflict_meta_dl_mixed: metaDL(元数据下载, amount_left>0)属活跃下载, 与已完成并存 -> mixed
- test_download_conflict_checking_up_mixed: checkingUP(校验中 amount_left=0)+stalledDL -> mixed(qB 重启场景)
- test_download_conflict_forced_queued_dl: forcedDL+queuedDL 双下载 -> multi-dl
- test_download_conflict_paused_dl_pair: pausedDL+stoppedDL 停种不算活跃下载 -> 不冲突
- test_download_conflict_resolve_by_complete: 混合冲突随下载完成(转做种)消除 -> 去重清除可再触发
- test_download_conflict_two_groups_independent: 两组冲突独立处理, 去重 key 按组隔离
- test_check_missing_files_checking_up_not_rep: checkingUP(校验中)非有效代表(排除 is_checking) -> 不扫描
- test_grouping_errored_via_checking_transition: 经 checkingUP/checkingResumeData 中间态 -> 校验拍不触发, missingFiles 拍触发
- test_download_conflict_missing_done_excluded: mixed 冲突排除带 MISSING 标签的完成成员(重下补救); 无标签照旧触发
- test_download_conflict_multi_dl_with_missing_tag: multi-dl 不受 MISSING 标签豁免仍拦截
- test_grouping_conflict_scan_skips_ghost_members: 冲突扫描幽灵成员跳过; _group_has_downloading 幽灵不活跃 (P2-a)
- test_guard_download_conflict_stop_scope: 下载冲突停组名单=成员精确列表(dc79 高危, dc68 过滤反转)
- test_guard_download_conflict_incremental: 增量短路(dc2/dc7 高危): rounds>0+脏组在场必须真重算
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
    _seed_group,
)


def test_is_downloading_excludes_checking():
    """活跃下载判定: 强制校验(checkingDL/checkingUP/checkingResumeData)不算活跃下载(62dbc25 修复)

    修复前 checkingDL(is_downloading=True, is_checking=True)被误判为下载中,
    导致下载冲突检查误暂停整组。现活跃下载判定由 _group_has_downloading 承担:
    is_downloading and not is_stopped and not is_checking(读 store 快照)。
    """
    mgr = make_manager("state.json", bare=True, grouping=grouping_cfg())
    # checking* 状态 -> 不算组内活跃下载(不阻塞校验决策链)
    seed_store(
        mgr, [
            FakeTorrent(hash="H1", state="checkingDL", amount_left=100),
            FakeTorrent(hash="H2", state="checkingUP", amount_left=0),
            FakeTorrent(hash="H3", state="checkingResumeData", amount_left=100),
        ]
    )
    assert mgr.host.get("grouping")._group_has_downloading(["H1"]) is False, "checkingDL 不应算下载中"
    assert mgr.host.get("grouping")._group_has_downloading(["H2"]) is False, "checkingUP 不应算下载中"
    assert mgr.host.get("grouping")._group_has_downloading(["H3"]) is False, "checkingResumeData 不应算下载中"
    assert mgr.host.get("grouping")._group_has_downloading(["H1", "H2", "H3"]) is False, "组内只有强制校验种子不应算活跃下载"


def test_grouping_force_checking_not_conflict():
    """强制校验种子不再被当作下载中(62dbc25 回归): 与下载中/已完成成员同组不触发冲突暂停"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        client = FakeClient()
        mgr = make_manager(state_file, bare=True, grouping=grouping_cfg(), client=client)

        # 组 A: H1 强制校验(未完成) + H2 下载中 —— 修复前误判 multi-dl
        # 组 B: H3 强制校验(未完成) + H4 已完成做种 —— 修复前误判 mixed
        t1 = FakeTorrent(hash="H1", name="T1", state="checkingDL", save_path=r"R:\A", amount_left=100)
        t2 = FakeTorrent(hash="H2", name="T2", state="downloading", save_path=r"R:\A", amount_left=100)
        t3 = FakeTorrent(hash="H3", name="T3", state="checkingDL", save_path=r"R:\B", amount_left=100)
        t4 = FakeTorrent(hash="H4", name="T4", state="stalledUP", save_path=r"R:\B", amount_left=0)
        for t in (t1, t2, t3, t4):
            client.torrents[t.hash] = t
            client.files_map[t.hash] = [_fake_file("movie.mkv", 100)]
        mgr._refresh_torrents()

        assert len(mgr.store.groups) == 2, f"应归为两组: {mgr.store.groups}"
        assert _non_tag_calls(client) == [], f"强制校验种子不应触发下载冲突暂停: {client.calls}"
        assert mgr.store.download_conflict_warned == set()


def test_grouping_download_conflict_multi_dl():
    """下载冲突: 同组两个及以上种子同时下载 -> 警告+整组暂停; 去重: 冲突持续不重复, 消除后清除可再次触发"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        client = FakeClient()
        mgr = make_manager(state_file, bare=True, grouping=grouping_cfg(), client=client)
        t1 = FakeTorrent(hash="H1", name="T1", state="downloading", amount_left=100)
        t2 = FakeTorrent(hash="H2", name="T2", state="stalledDL", amount_left=100)
        key = ("R:/Downloads", ("movie.mkv", ))
        mgr.store.by_hash = {"H1": t1, "H2": t2}
        mgr.store.groups = {key: ["H1", "H2"]}
        mgr.store.group_sizes = {key: {}}
        mgr.store.member_to_key = {"H1": key, "H2": key}

        # mock 掉 api.torrents_stop: QbApi 的 stop 会同步 store 把成员状态改为暂停,
        # 污染 by_hash 快照(真实场景下轮 refresh 才校准), 干扰去重语义验证
        with mock.patch.object(mgr.api, "torrents_stop") as stop_mock:
            mgr.host.get("grouping")._check_download_conflicts(dry_run=False)
            assert stop_mock.call_count == 1, f"多下载应整组暂停: {stop_mock.call_count}"
            assert (key, "multi-dl") in mgr.store.download_conflict_warned

            # 冲突持续 -> 不重复暂停(去重)
            mgr.host.get("grouping")._check_download_conflicts(dry_run=False)
            assert stop_mock.call_count == 1, f"冲突持续不应重复暂停: {stop_mock.call_count}"

            # 冲突消除(H1 转暂停) -> 去重记录清除
            t1.state = "pausedDL"
            mgr.host.get("grouping")._check_download_conflicts(dry_run=False)
            assert mgr.store.download_conflict_warned == set()

            # 冲突重现 -> 再次警告+暂停
            t1.state = "downloading"
            mgr.host.get("grouping")._check_download_conflicts(dry_run=False)
            assert stop_mock.call_count == 2, f"冲突重现应再次暂停: {stop_mock.call_count}"
            assert (key, "multi-dl") in mgr.store.download_conflict_warned


def test_grouping_download_conflict_mixed():
    """下载冲突: 同组已完成与下载中并存 -> 警告+整组暂停(真冲突不受修复影响)"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        client = FakeClient()
        mgr = make_manager(state_file, bare=True, grouping=grouping_cfg(), client=client)
        t1 = FakeTorrent(hash="H1", name="T1", state="stalledDL", amount_left=100)
        t2 = FakeTorrent(hash="H2", name="T2", state="stalledUP", amount_left=0)
        key = ("R:/Downloads", ("movie.mkv", ))
        mgr.store.by_hash = {"H1": t1, "H2": t2}
        mgr.store.groups = {key: ["H1", "H2"]}
        mgr.store.group_sizes = {key: {}}
        mgr.store.member_to_key = {"H1": key, "H2": key}

        mgr.host.get("grouping")._check_download_conflicts(dry_run=False)
        assert client.calls.count(("stop", None)) == 1, f"已完成与下载中并存应整组暂停: {client.calls}"
        assert (key, "mixed") in mgr.store.download_conflict_warned


def test_grouping_download_conflict_dry_run():
    """下载冲突 dry-run: 只报告不暂停, 也不记录去重(下次真实执行仍会暂停)"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        client = FakeClient()
        mgr = make_manager(state_file, bare=True, grouping=grouping_cfg(), client=client)
        t1 = FakeTorrent(hash="H1", name="T1", state="downloading", amount_left=100)
        t2 = FakeTorrent(hash="H2", name="T2", state="stalledDL", amount_left=100)
        key = ("R:/Downloads", ("movie.mkv", ))
        mgr.store.by_hash = {"H1": t1, "H2": t2}
        mgr.store.groups = {key: ["H1", "H2"]}
        mgr.store.group_sizes = {key: {}}
        mgr.store.member_to_key = {"H1": key, "H2": key}

        mgr.host.get("grouping")._check_download_conflicts(dry_run=True)
        assert client.calls == [], f"dry-run 不应暂停: {client.calls}"
        assert mgr.store.download_conflict_warned == set(), "dry-run 不记录去重"

        # 真实执行仍会警告+暂停
        mgr.host.get("grouping")._check_download_conflicts(dry_run=False)
        assert client.calls.count(("stop", None)) == 1, f"真实执行应整组暂停: {client.calls}"


def test_download_conflict_meta_dl_mixed():
    """下载冲突: metaDL(元数据下载, amount_left>0)算活跃下载, 与已完成并存 -> mixed"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        client = FakeClient()
        mgr = make_manager(state_file, bare=True, grouping=grouping_cfg(), client=client)
        t1 = FakeTorrent(hash="H1", name="T1", state="metaDL", amount_left=100)
        t2 = FakeTorrent(hash="H2", name="T2", state="stalledUP", amount_left=0)
        key = ("R:/Downloads", ("movie.mkv", ))
        mgr.store.by_hash = {"H1": t1, "H2": t2}
        mgr.store.groups = {key: ["H1", "H2"]}
        mgr.store.group_sizes = {key: {}}
        mgr.store.member_to_key = {"H1": key, "H2": key}

        with mock.patch.object(mgr.api, "torrents_stop") as stop_mock:
            mgr.host.get("grouping")._check_download_conflicts(dry_run=False)
        assert stop_mock.call_count == 1, f"metaDL 与已完成并存应整组暂停: {stop_mock.call_count}"
        assert (key, "mixed") in mgr.store.download_conflict_warned


def test_download_conflict_checking_up_mixed():
    """下载冲突: checkingUP(校验中但已完成, amount_left=0) + stalledDL -> mixed(qB 重启场景)"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        client = FakeClient()
        mgr = make_manager(state_file, bare=True, grouping=grouping_cfg(), client=client)
        t1 = FakeTorrent(hash="H1", name="T1", state="checkingUP", amount_left=0)
        t2 = FakeTorrent(hash="H2", name="T2", state="stalledDL", amount_left=100)
        key = ("R:/Downloads", ("movie.mkv", ))
        mgr.store.by_hash = {"H1": t1, "H2": t2}
        mgr.store.groups = {key: ["H1", "H2"]}
        mgr.store.group_sizes = {key: {}}
        mgr.store.member_to_key = {"H1": key, "H2": key}

        with mock.patch.object(mgr.api, "torrents_stop") as stop_mock:
            mgr.host.get("grouping")._check_download_conflicts(dry_run=False)
        assert stop_mock.call_count == 1, f"校验中已完成成员与下载中并存应触发 mixed: {stop_mock.call_count}"
        assert (key, "mixed") in mgr.store.download_conflict_warned


def test_download_conflict_forced_queued_dl():
    """下载冲突: forcedDL + queuedDL 两个活跃下载 -> multi-dl"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        client = FakeClient()
        mgr = make_manager(state_file, bare=True, grouping=grouping_cfg(), client=client)
        t1 = FakeTorrent(hash="H1", name="T1", state="forcedDL", amount_left=100)
        t2 = FakeTorrent(hash="H2", name="T2", state="queuedDL", amount_left=100)
        key = ("R:/Downloads", ("movie.mkv", ))
        mgr.store.by_hash = {"H1": t1, "H2": t2}
        mgr.store.groups = {key: ["H1", "H2"]}
        mgr.store.group_sizes = {key: {}}
        mgr.store.member_to_key = {"H1": key, "H2": key}

        with mock.patch.object(mgr.api, "torrents_stop") as stop_mock:
            mgr.host.get("grouping")._check_download_conflicts(dry_run=False)
        assert stop_mock.call_count == 1, f"双下载应触发 multi-dl: {stop_mock.call_count}"
        assert (key, "multi-dl") in mgr.store.download_conflict_warned


def test_download_conflict_paused_dl_pair():
    """下载冲突: pausedDL + stoppedDL 停种(暂停)不算活跃下载 -> 不冲突不暂停"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        client = FakeClient()
        mgr = make_manager(state_file, bare=True, grouping=grouping_cfg(), client=client)
        t1 = FakeTorrent(hash="H1", name="T1", state="pausedDL", amount_left=100)
        t2 = FakeTorrent(hash="H2", name="T2", state="stoppedDL", amount_left=100)
        key = ("R:/Downloads", ("movie.mkv", ))
        mgr.store.by_hash = {"H1": t1, "H2": t2}
        mgr.store.groups = {key: ["H1", "H2"]}
        mgr.store.group_sizes = {key: {}}
        mgr.store.member_to_key = {"H1": key, "H2": key}

        mgr.host.get("grouping")._check_download_conflicts(dry_run=False)
        assert client.calls == [], f"暂停的下载不应触发冲突暂停: {client.calls}"
        assert mgr.store.download_conflict_warned == set()


def test_download_conflict_resolve_by_complete():
    """下载冲突: 混合冲突随下载完成(转做种)消除 -> 去重清除; 重现可再次触发"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        client = FakeClient()
        mgr = make_manager(state_file, bare=True, grouping=grouping_cfg(), client=client)
        t1 = FakeTorrent(hash="H1", name="T1", state="downloading", amount_left=100)
        t2 = FakeTorrent(hash="H2", name="T2", state="stalledUP", amount_left=0)
        key = ("R:/Downloads", ("movie.mkv", ))
        mgr.store.by_hash = {"H1": t1, "H2": t2}
        mgr.store.groups = {key: ["H1", "H2"]}
        mgr.store.group_sizes = {key: {}}
        mgr.store.member_to_key = {"H1": key, "H2": key}

        with mock.patch.object(mgr.api, "torrents_stop") as stop_mock:
            mgr.host.get("grouping")._check_download_conflicts(dry_run=False)
            assert stop_mock.call_count == 1
            assert (key, "mixed") in mgr.store.download_conflict_warned

            # 下载完成: 状态转做种 + amount_left=0 -> 冲突消除, 去重记录清除
            t1.state = "stalledUP"
            t1.amount_left = 0
            mgr.host.get("grouping")._check_download_conflicts(dry_run=False)
            assert mgr.store.download_conflict_warned == set(), "下载完成应清除去重记录"
            assert stop_mock.call_count == 1

            # 新种子又开始下载 -> 冲突重现, 再次暂停
            t1.state = "downloading"
            t1.amount_left = 100
            mgr.host.get("grouping")._check_download_conflicts(dry_run=False)
            assert stop_mock.call_count == 2, f"冲突重现应再次暂停: {stop_mock.call_count}"
            assert (key, "mixed") in mgr.store.download_conflict_warned


def test_download_conflict_two_groups_independent():
    """下载冲突: 两组同时冲突分别处理, 去重 key 按组独立; 一组消除不影响另一组"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        client = FakeClient()
        mgr = make_manager(state_file, bare=True, grouping=grouping_cfg(), client=client)
        t1 = FakeTorrent(hash="H1", name="T1", state="downloading", amount_left=100)
        t2 = FakeTorrent(hash="H2", name="T2", state="stalledDL", amount_left=100)
        t3 = FakeTorrent(hash="H3", name="T3", state="stalledDL", amount_left=100)
        t4 = FakeTorrent(hash="H4", name="T4", state="stalledUP", amount_left=0)
        key_a = ("R:/Downloads/A", ("movie.mkv", ))
        key_b = ("R:/Downloads/B", ("movie.mkv", ))
        mgr.store.by_hash = {"H1": t1, "H2": t2, "H3": t3, "H4": t4}
        mgr.store.groups = {key_a: ["H1", "H2"], key_b: ["H3", "H4"]}
        mgr.store.group_sizes = {key_a: {}, key_b: {}}
        mgr.store.member_to_key = {"H1": key_a, "H2": key_a, "H3": key_b, "H4": key_b}

        with mock.patch.object(mgr.api, "torrents_stop") as stop_mock:
            mgr.host.get("grouping")._check_download_conflicts(dry_run=False)
            assert stop_mock.call_count == 2, f"两组各暂停一次: {stop_mock.call_count}"
            assert (key_a, "multi-dl") in mgr.store.download_conflict_warned
            assert (key_b, "mixed") in mgr.store.download_conflict_warned

            # 组A 冲突消除(H1 暂停) -> 仅组A 去重清除, 组B 保留且不重复暂停
            t1.state = "pausedDL"
            mgr.host.get("grouping")._check_download_conflicts(dry_run=False)
            assert (key_a, "multi-dl") not in mgr.store.download_conflict_warned
            assert (key_b, "mixed") in mgr.store.download_conflict_warned
            assert stop_mock.call_count == 2


def test_check_missing_files_checking_up_not_rep():
    """_check_missing_files: checkingUP(校验中, is_checking)不算有效代表 -> 不扫描;
    对照 stalledUP(校验完成做种)作代表 -> 缺文件触发暂停 + MISSING"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        client = FakeClient()
        mgr = make_manager(state_file, bare=True, grouping=grouping_cfg(), client=client)

        # checkingUP: is_complete 但 is_checking -> 排除出有效代表, 不扫描
        checking_up = FakeTorrent(hash="H1", name="T1", state="checkingUP", save_path=td, amount_left=0)
        sizes = {"H1": {"movie.mkv": 100}}  # 文件不存在
        mgr.host.get("grouping")._check_missing_files([checking_up], sizes, dry_run=False, key="K")
        assert client.calls == [], f"checkingUP 非有效代表不应触发扫描: {client.calls}"

        # 对照: stalledUP 作代表 -> 缺文件暂停 + MISSING
        stalled_up = FakeTorrent(hash="H2", name="T2", state="stalledUP", save_path=td, amount_left=0)
        sizes2 = {"H2": {"movie.mkv": 100}}
        mgr.host.get("grouping")._check_missing_files([stalled_up], sizes2, dry_run=False, key="K")
        assert client.calls.count(("stop", None)) == 1, f"stalledUP 作代表缺文件应暂停: {client.calls}"
        assert "MISSING" in client.tags


def test_grouping_errored_via_checking_transition():
    """errored 触发不依赖中间状态名: stalledUP -> checkingUP/checkingResumeData(校验中, 不触发)
    -> missingFiles(下一拍触发)"""
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
        mgr._refresh_torrents()  # 首轮归组
        assert _non_tag_calls(client) == [], f"首轮不应触发: {client.calls}"

        # 两个成员分别经 checkingUP / checkingResumeData(恢复时自动重校验)进入校验 -> 不触发
        t1.state = "checkingUP"
        t2.state = "checkingResumeData"
        mgr._refresh_torrents()
        assert _non_tag_calls(client) == [], f"校验中状态不应触发: {client.calls}"

        # 校验完成发现文件缺失 -> missingFiles -> 触发(同组去重, 扫描一次)
        t1.state = "missingFiles"
        t2.state = "missingFiles"
        mgr._refresh_torrents()
        assert client.calls.count(("stop", None)) == 1, f"校验发现缺失应触发整组暂停: {client.calls}"
        assert "MISSING" in client.tags, f"丢失应添加标签: {client.tags}"


def test_download_conflict_missing_done_excluded():
    """mixed 冲突排除带 MISSING 标签的已完成成员: MISSING 组重新下载是合法补救, 不拦停;
    对照: 完成成员无 MISSING 标签(健康组)-> 照旧触发 mixed 暂停"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        client = FakeClient()
        mgr = make_manager(state_file, bare=True, grouping=grouping_cfg(), client=client)
        t1 = FakeTorrent(hash="H1", name="T1", state="stalledDL", amount_left=100)
        t2 = FakeTorrent(hash="H2", name="T2", state="stalledUP", amount_left=0, tags="MISSING")
        key = ("R:/Downloads", ("movie.mkv", ))
        mgr.store.by_hash = {"H1": t1, "H2": t2}
        mgr.store.groups = {key: ["H1", "H2"]}
        mgr.store.group_sizes = {key: {}}
        mgr.store.member_to_key = {"H1": key, "H2": key}

        mgr.host.get("grouping")._check_download_conflicts(dry_run=False)
        assert client.calls == [], f"MISSING 组的重新下载不应被 mixed 冲突拦截: {client.calls}"
        assert (key, "mixed") not in mgr.store.download_conflict_warned

        # 对照: 完成成员无 MISSING 标签(健康组)-> 照旧触发
        t2.tags = ""
        mgr.host.get("grouping")._check_download_conflicts(dry_run=False)
        assert client.calls.count(("stop", None)) == 1, f"健康完成成员与下载中并存应照旧暂停: {client.calls}"
        assert (key, "mixed") in mgr.store.download_conflict_warned


def test_download_conflict_multi_dl_with_missing_tag():
    """multi-dl 不受 MISSING 标签豁免: 同组两个活跃下载写同一物理文件, 与缺文件无关, 仍拦截"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        client = FakeClient()
        mgr = make_manager(state_file, bare=True, grouping=grouping_cfg(), client=client)
        t1 = FakeTorrent(hash="H1", name="T1", state="stalledDL", amount_left=100)
        t2 = FakeTorrent(hash="H2", name="T2", state="forcedDL", amount_left=100, tags="MISSING")
        key = ("R:/Downloads", ("movie.mkv", ))
        mgr.store.by_hash = {"H1": t1, "H2": t2}
        mgr.store.groups = {key: ["H1", "H2"]}
        mgr.store.group_sizes = {key: {}}
        mgr.store.member_to_key = {"H1": key, "H2": key}

        mgr.host.get("grouping")._check_download_conflicts(dry_run=False)
        assert client.calls.count(("stop", None)) == 1, f"MISSING 组内 multi-dl 仍应拦截: {client.calls}"
        assert (key, "multi-dl") in mgr.store.download_conflict_warned


def test_grouping_conflict_scan_skips_ghost_members():
    """下载冲突扫描: 组表成员不在快照(幽灵成员)跳过不崩溃; 幽灵成员直查返回不活跃"""
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"))
        key = (r"R:/D", "k")
        mgr.store.groups[key] = ["H1", "GHOST"]
        mgr.store.by_hash["H1"] = FakeTorrent(hash="H1", state="stalledUP")
        mgr.store.dirty_groups.add(key)  # 增量基线未建立(rounds_applied=0)退回全量; 脏组登记无害
        grp._check_download_conflicts(False)
        assert client.calls == []
        assert grp._group_has_downloading(["GHOST", "H1"]) is False, "stalledUP 非活跃下载"


def test_guard_download_conflict_stop_scope():
    """守阵(W9a dc79 高危 + dc68): 下载冲突整组暂停名单=按 by_hash 过滤后的成员精确列表
    (过滤反转 -> 暂停落空, 保护动作失效)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"))
        stops = _record_stop_scope(client)
        key = (r"R:\Downloads", ("movie.mkv", ))
        _seed_group(mgr.store, key, ["H1", "H2"])
        mgr.store.by_hash["H1"] = FakeTorrent(hash="H1", state="stalledDL", progress=0.0, downloaded=0)
        grp._check_download_conflicts(False)
        assert stops == [["H1", "H2"]], f"mixed 冲突应停整组且名单精确(不得 None=全库/空表): {stops}"


def test_guard_download_conflict_incremental():
    """守阵(W9a dc2/dc7 高危): 增量模式(rounds_applied>0)脏组在场必须真重算 ——
    dirty 读断(None)/早退条件反转都会让冲突检测整体死"""
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"))
        stops = _record_stop_scope(client)
        key = (r"R:\Downloads", ("movie.mkv", ))
        _seed_group(mgr.store, key, ["H1", "H2"])
        mgr.store.by_hash["H1"] = FakeTorrent(hash="H1", state="stalledDL", progress=0.0, downloaded=0)
        mgr.store.rounds_applied = 1
        mgr.store.dirty_groups = {key}
        grp._check_download_conflicts(False)
        assert stops == [["H1", "H2"]], f"增量轮脏组冲突必须被检出并处置: {stops}"
