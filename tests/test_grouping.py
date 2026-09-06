"""test_grouping 测试计划: 种子分组

## 测试计划(每个测试函数一条)
- test_grouping_size_mismatch_pauses_group: 新增种子归组时文件大小不一致 -> 整组暂停
- test_grouping_missing_files_pauses_group: 上传转暂停且文件丢失 -> 整组暂停 + MISSING
- test_grouping_state_change_triggers_check: 仅上传转暂停触发缺文件检查
- test_grouping_deleted_torrent_triggers_check: 种子删除触发组内联动
- test_grouping_no_global_task: 无分组配置不创建全局任务
- test_grouping_replaces_per_torrent_missing_files: 归组替代逐种子缺文件检查
- test_grouping_incremental_on_add: 新增种子增量归组
- test_grouping_removed_from_groups: 种子移出分组
- test_grouping_save_path_change_triggers_check: save_path 变化触发检查
- test_grouping_save_path_change_new_group_alone: save_path 变化单独成组
- test_grouping_no_full_files_scan: 归组仅拉一次文件列表, 后续不重复扫描
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
- test_group_members_not_in_group: 未归组 -> 仅自身
- test_group_members_in_group: 已归组 -> 全部成员
- test_leave_group_removes: 移出成员返回剩余组 key
- test_leave_group_empty_deletes: 组空删除返回 None
- test_leave_group_not_in_group: 不在组内返回 None
- test_group_has_downloading: 组内存在下载中成员判定
- test_group_reference_candidates: 返回做种成员作为参考候选
- test_grouping_save_path_change_no_cache: 无缓存文件映射 -> 维持原行为不重归组
- test_assign_new_torrent_missing: 哈希不在 by_hash -> AttributeError 上抛(调用方保证存在)
- test_assign_new_torrent_files_error: 文件列表拉取异常 -> 异常上抛(由 run 主循环兜底)
- test_assign_to_group_empty_map: 空文件映射 -> 不归组
- test_check_missing_files_no_seeding_rep: 组内无已完成未校验种子 -> 不检查(暂停完成成员亦是代表)
- test_check_missing_files_size_mismatch: 文件存在但大小不符 -> 暂停 + MISSING
- test_check_missing_files_getsize_error: 文件读取 OSError -> 暂停 + MISSING
- test_check_missing_files_checking_up_not_rep: checkingUP(校验中)非有效代表(排除 is_checking) -> 不扫描
- test_check_missing_files_first_done_rep: 多已完成成员取第一个作代表, 非代表大小差异不影响
- test_check_missing_files_empty_sizes_map: 大小映射为空 -> 无文件可检查不误报
- test_check_missing_files_member_has_tag: 成员已带 MISSING 标签 -> 不重复 add_tags(仍暂停)
- test_check_missing_files_dry_run: 缺文件 dry-run -> 不暂停不加标签
"""
import os
import tempfile
from types import SimpleNamespace
from unittest import mock

import pytest

from auto_qb.config import GroupingConfig
from auto_qb.qbmanager import QbManager
from helpers import FakeClient, FakeConfig, FakeTorrent, seed_store


def _fake_file(name, size):
    return SimpleNamespace(name=name, size=size)


def _group_cfg(state_file, enabled=True):
    cfg = FakeConfig()
    cfg.state_file = state_file
    cfg.grouping = GroupingConfig(enabled=enabled, missing_tag="MISSING")
    return cfg


def test_grouping_size_mismatch_pauses_group():
    """新增种子归组时文件大小不一致 -> 警告 + 整组暂停(不加标签, 不再每轮检查)"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        cfg = _group_cfg(state_file)
        mgr = QbManager("", config=cfg, no_lock=True)  # 测试不持锁
        client = FakeClient()
        mgr.client = client

        t1 = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=r"R:\Downloads")
        client.torrents["H1"] = t1
        client.files_map["H1"] = [_fake_file("movie.mkv", 100)]
        mgr._refresh_torrents()  # 归组完全增量: 首轮刷新视为新增, 经 _assign_new_torrent 归组
        assert client.calls == [], f"单成员归组不应触发动作: {client.calls}"

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
        cfg = _group_cfg(state_file)
        mgr = QbManager("", config=cfg, no_lock=True)  # 测试不持锁
        client = FakeClient()
        mgr.client = client

        t1 = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=r"R:\Downloads")
        t2 = FakeTorrent(hash="H2", name="T2", state="stalledUP", save_path=r"R:\Downloads")
        client.torrents["H1"] = t1
        client.torrents["H2"] = t2
        client.files_map["H1"] = [_fake_file("movie.mkv", 100)]
        client.files_map["H2"] = [_fake_file("movie.mkv", 100)]

        # 首轮: 归组 + 建立状态快照(上传中, 无触发条件, 不扫描)
        mgr._refresh_torrents()
        assert client.calls == [], f"上传状态不应触发检查: {client.calls}"

        # H1 由上传(stalledUP)转为暂停(pausedUP) -> 同一轮立即触发缺文件扫描(文件不存在)
        t1.state = "pausedUP"
        mgr._refresh_torrents()

        assert client.calls.count(("stop", None)) == 1, f"整组应暂停一次: {client.calls}"
        assert "MISSING" in client.tags, f"丢失应添加标签: {client.tags}"
        assert mgr.store.state_snapshot.get("H1") == "pausedUP", f"状态快照应更新: {mgr.store.state_snapshot}"


def test_grouping_state_change_triggers_check():
    """仅"上传转暂停"触发检查(检测到即立即处理); 上传状态间变化/状态不变不触发"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        cfg = _group_cfg(state_file)
        mgr = QbManager("", config=cfg, no_lock=True)  # 测试不持锁
        client = FakeClient()
        mgr.client = client

        t1 = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=r"R:\Downloads")
        t2 = FakeTorrent(hash="H2", name="T2", state="stalledUP", save_path=r"R:\Downloads")
        client.torrents["H1"] = t1
        client.torrents["H2"] = t2
        client.files_map["H1"] = [_fake_file("movie.mkv", 100)]
        client.files_map["H2"] = [_fake_file("movie.mkv", 100)]

        # 首轮: 归组 + 建立状态快照(上传中, 不触发)
        mgr._refresh_torrents()
        assert client.calls == [], f"首轮不应触发: {client.calls}"

        # H1 stalledUP -> uploading(仍是上传, 不触发)
        t1.state = "uploading"
        mgr._refresh_torrents()
        assert client.calls == [], f"上传状态间变化不应触发: {client.calls}"

        # H1 uploading -> pausedUP(上传转暂停, 立即触发)
        t1.state = "pausedUP"
        mgr._refresh_torrents()
        assert client.calls.count(("stop", None)) == 1, f"上传转暂停应触发: {client.calls}"
        assert "MISSING" in client.tags

        # 状态不变 -> 不重复触发
        client.calls.clear()
        mgr._refresh_torrents()
        assert client.calls == [], f"状态不变不应重复触发: {client.calls}"


def test_grouping_deleted_torrent_triggers_check():
    """同组种子被删除 -> 同一轮立即触发缺文件扫描(不等下一轮)"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        cfg = _group_cfg(state_file)
        mgr = QbManager("", config=cfg, no_lock=True)  # 测试不持锁
        client = FakeClient()
        mgr.client = client

        t1 = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=r"R:\Downloads")
        t2 = FakeTorrent(hash="H2", name="T2", state="stalledUP", save_path=r"R:\Downloads")
        client.torrents["H1"] = t1
        client.torrents["H2"] = t2
        client.files_map["H1"] = [_fake_file("movie.mkv", 100)]
        client.files_map["H2"] = [_fake_file("movie.mkv", 100)]
        mgr._refresh_torrents()  # 归组
        assert client.calls == [], f"上传状态不应触发检查: {client.calls}"

        # 删除 H2 -> 移出组; 组内剩 H1, 同一轮立即触发缺文件扫描(文件不存在)
        del client.torrents["H2"]
        mgr._refresh_torrents()

        key = next(iter(mgr.store.groups))
        assert mgr.store.groups[key] == ["H1"], f"删除后组内成员: {mgr.store.groups}"
        assert client.calls.count(("stop", None)) == 1, f"删除种子应立即触发整组暂停: {client.calls}"
        assert "MISSING" in client.tags, f"文件丢失应加标签: {client.tags}"


def test_grouping_no_global_task():
    """分组为事件驱动, 不再创建周期轮询全局任务"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = QbManager("", config=_group_cfg(state_file), no_lock=True)  # 测试不持锁
        names = {t.name for t in mgr.task_queue._fast}
        assert "grouping" not in names, f"事件驱动不应创建分组周期任务: {names}"

        # 未启用也不创建
        mgr2 = QbManager("", config=_group_cfg(state_file, enabled=False), no_lock=True)  # 测试不持锁
        names2 = {t.name for t in mgr2.task_queue._fast}
        assert "grouping" not in names2, f"未启用也不应创建分组任务: {names2}"


def test_grouping_replaces_per_torrent_missing_files():
    """逐种子 missing_files 任务已移除, 缺文件检查统一由分组事件驱动承担"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        cfg = _group_cfg(state_file)
        cfg.check_missing_files = True
        mgr = QbManager("", config=cfg, no_lock=True)  # 测试不持锁
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(hash="H1", name="T1")
        tor.tracker_conf = cfg.trackers["HHan"]  # 显式 setUp: 模拟 _refresh_torrents 匹配
        seed_store(mgr, [tor])

        mgr._create_torrent_tasks("H1", cfg.trackers["HHan"])
        names = {t.name for t in mgr.task_queue._fast}
        assert "missing_files" not in names, f"不应创建逐种子检查: {names}"

        # 未启用分组同样不创建(逐种子检查已整体移除, 不再回退)
        cfg2 = _group_cfg(state_file, enabled=False)
        cfg2.check_missing_files = True
        mgr2 = QbManager("", config=cfg2, no_lock=True)  # 测试不持锁
        mgr2.client = FakeClient()
        seed_store(mgr2, [tor])
        mgr2._create_torrent_tasks("H1", cfg2.trackers["HHan"])
        names2 = {t.name for t in mgr2.task_queue._fast}
        assert "missing_files" not in names2, f"未启用分组也不应创建逐种子检查: {names2}"


def test_grouping_incremental_on_add():
    """新增种子时自动归组(增量), 不再每轮全量重建分组"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = QbManager("", config=_group_cfg(state_file), no_lock=True)  # 测试不持锁
        client = FakeClient()
        mgr.client = client

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
        mgr = QbManager("", config=_group_cfg(state_file), no_lock=True)  # 测试不持锁
        client = FakeClient()
        mgr.client = client

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
        mgr = QbManager("", config=_group_cfg(state_file), no_lock=True)  # 测试不持锁
        client = FakeClient()
        mgr.client = client

        # 组 A: H1/H2(DownloadsA); 组 B: H3(DownloadsB)
        t1 = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=r"R:\DownloadsA")
        t2 = FakeTorrent(hash="H2", name="T2", state="stalledUP", save_path=r"R:\DownloadsA")
        t3 = FakeTorrent(hash="H3", name="T3", state="stalledUP", save_path=r"R:\DownloadsB")
        for t in (t1, t2, t3):
            client.torrents[t.hash] = t
            client.files_map[t.hash] = [_fake_file("movie.mkv", 100)]
        mgr._refresh_torrents()
        assert client.calls == [], f"首轮归组不应触发扫描: {client.calls}"
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
        mgr = QbManager("", config=_group_cfg(state_file), no_lock=True)  # 测试不持锁
        client = FakeClient()
        mgr.client = client

        t1 = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=r"R:\DownloadsA")
        t2 = FakeTorrent(hash="H2", name="T2", state="stalledUP", save_path=r"R:\DownloadsA")
        client.torrents["H1"] = t1
        client.torrents["H2"] = t2
        client.files_map["H1"] = [_fake_file("movie.mkv", 100)]
        client.files_map["H2"] = [_fake_file("movie.mkv", 100)]
        mgr._refresh_torrents()
        assert client.calls == [], f"首轮归组不应触发扫描: {client.calls}"

        # H1 移到空目录 DownloadsB(新组仅本种子) -> 仅原组 A(H2)触发扫描
        t1.save_path = r"R:\DownloadsB"
        mgr._refresh_torrents()

        assert set(mgr.store.groups[("R:/DownloadsA", ("movie.mkv", ))]) == {"H2"}
        assert mgr.store.groups[("R:/DownloadsB", ("movie.mkv", ))] == ["H1"]
        assert client.calls.count(("stop", None)) == 1, f"仅原组扫描暂停一次: {client.calls}"
        assert client.calls.count(("add_tags", ["MISSING"])) == 1, f"仅 H2 加标签: {client.calls}"


def test_grouping_no_full_files_scan():
    """归组仅拉一次文件列表(增量归组); 后续刷新状态不变不触发扫描, 不重复拉取"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = QbManager("", config=_group_cfg(state_file), no_lock=True)  # 测试不持锁
        client = FakeClient()
        mgr.client = client

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
        assert client.calls == [], f"状态不变不应触发检查: {client.calls}"


def test_is_downloading_excludes_checking():
    """活跃下载判定: 强制校验(checkingDL/checkingUP/checkingResumeData)不算活跃下载(62dbc25 修复)

    修复前 checkingDL(is_downloading=True, is_checking=True)被误判为下载中,
    导致下载冲突检查误暂停整组。现活跃下载判定由 _group_has_downloading 承担:
    is_downloading and not is_stopped and not is_checking(读 store 快照)。
    """
    mgr = QbManager("", config=_group_cfg("state.json"), no_lock=True)  # 测试不持锁
    # checking* 状态 -> 不算组内活跃下载(不阻塞校验决策链)
    seed_store(
        mgr, [
            FakeTorrent(hash="H1", state="checkingDL", amount_left=100),
            FakeTorrent(hash="H2", state="checkingUP", amount_left=0),
            FakeTorrent(hash="H3", state="checkingResumeData", amount_left=100),
        ]
    )
    assert mgr._group_has_downloading(["H1"]) is False, "checkingDL 不应算下载中"
    assert mgr._group_has_downloading(["H2"]) is False, "checkingUP 不应算下载中"
    assert mgr._group_has_downloading(["H3"]) is False, "checkingResumeData 不应算下载中"
    assert mgr._group_has_downloading(["H1", "H2", "H3"]) is False, "组内只有强制校验种子不应算活跃下载"


def test_grouping_force_checking_not_conflict():
    """强制校验种子不再被当作下载中(62dbc25 回归): 与下载中/已完成成员同组不触发冲突暂停"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = QbManager("", config=_group_cfg(state_file), no_lock=True)  # 测试不持锁
        client = FakeClient()
        mgr.client = client

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
        assert client.calls == [], f"强制校验种子不应触发下载冲突暂停: {client.calls}"
        assert mgr.store.download_conflict_warned == set()


def test_grouping_download_conflict_multi_dl():
    """下载冲突: 同组两个及以上种子同时下载 -> 警告+整组暂停; 去重: 冲突持续不重复, 消除后清除可再次触发"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = QbManager("", config=_group_cfg(state_file), no_lock=True)  # 测试不持锁
        client = FakeClient()
        mgr.client = client
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
            mgr._check_download_conflicts(dry_run=False)
            assert stop_mock.call_count == 1, f"多下载应整组暂停: {stop_mock.call_count}"
            assert (key, "multi-dl") in mgr.store.download_conflict_warned

            # 冲突持续 -> 不重复暂停(去重)
            mgr._check_download_conflicts(dry_run=False)
            assert stop_mock.call_count == 1, f"冲突持续不应重复暂停: {stop_mock.call_count}"

            # 冲突消除(H1 转暂停) -> 去重记录清除
            t1.state = "pausedDL"
            mgr._check_download_conflicts(dry_run=False)
            assert mgr.store.download_conflict_warned == set()

            # 冲突重现 -> 再次警告+暂停
            t1.state = "downloading"
            mgr._check_download_conflicts(dry_run=False)
            assert stop_mock.call_count == 2, f"冲突重现应再次暂停: {stop_mock.call_count}"
            assert (key, "multi-dl") in mgr.store.download_conflict_warned


def test_grouping_download_conflict_mixed():
    """下载冲突: 同组已完成与下载中并存 -> 警告+整组暂停(真冲突不受修复影响)"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = QbManager("", config=_group_cfg(state_file), no_lock=True)  # 测试不持锁
        client = FakeClient()
        mgr.client = client
        t1 = FakeTorrent(hash="H1", name="T1", state="stalledDL", amount_left=100)
        t2 = FakeTorrent(hash="H2", name="T2", state="stalledUP", amount_left=0)
        key = ("R:/Downloads", ("movie.mkv", ))
        mgr.store.by_hash = {"H1": t1, "H2": t2}
        mgr.store.groups = {key: ["H1", "H2"]}
        mgr.store.group_sizes = {key: {}}
        mgr.store.member_to_key = {"H1": key, "H2": key}

        mgr._check_download_conflicts(dry_run=False)
        assert client.calls.count(("stop", None)) == 1, f"已完成与下载中并存应整组暂停: {client.calls}"
        assert (key, "mixed") in mgr.store.download_conflict_warned


def test_grouping_download_conflict_dry_run():
    """下载冲突 dry-run: 只报告不暂停, 也不记录去重(下次真实执行仍会暂停)"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = QbManager("", config=_group_cfg(state_file), no_lock=True)  # 测试不持锁
        client = FakeClient()
        mgr.client = client
        t1 = FakeTorrent(hash="H1", name="T1", state="downloading", amount_left=100)
        t2 = FakeTorrent(hash="H2", name="T2", state="stalledDL", amount_left=100)
        key = ("R:/Downloads", ("movie.mkv", ))
        mgr.store.by_hash = {"H1": t1, "H2": t2}
        mgr.store.groups = {key: ["H1", "H2"]}
        mgr.store.group_sizes = {key: {}}
        mgr.store.member_to_key = {"H1": key, "H2": key}

        mgr._check_download_conflicts(dry_run=True)
        assert client.calls == [], f"dry-run 不应暂停: {client.calls}"
        assert mgr.store.download_conflict_warned == set(), "dry-run 不记录去重"

        # 真实执行仍会警告+暂停
        mgr._check_download_conflicts(dry_run=False)
        assert client.calls.count(("stop", None)) == 1, f"真实执行应整组暂停: {client.calls}"


def test_download_conflict_meta_dl_mixed():
    """下载冲突: metaDL(元数据下载, amount_left>0)算活跃下载, 与已完成并存 -> mixed"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = QbManager("", config=_group_cfg(state_file), no_lock=True)  # 测试不持锁
        client = FakeClient()
        mgr.client = client
        t1 = FakeTorrent(hash="H1", name="T1", state="metaDL", amount_left=100)
        t2 = FakeTorrent(hash="H2", name="T2", state="stalledUP", amount_left=0)
        key = ("R:/Downloads", ("movie.mkv", ))
        mgr.store.by_hash = {"H1": t1, "H2": t2}
        mgr.store.groups = {key: ["H1", "H2"]}
        mgr.store.group_sizes = {key: {}}
        mgr.store.member_to_key = {"H1": key, "H2": key}

        with mock.patch.object(mgr.api, "torrents_stop") as stop_mock:
            mgr._check_download_conflicts(dry_run=False)
        assert stop_mock.call_count == 1, f"metaDL 与已完成并存应整组暂停: {stop_mock.call_count}"
        assert (key, "mixed") in mgr.store.download_conflict_warned


def test_download_conflict_checking_up_mixed():
    """下载冲突: checkingUP(校验中但已完成, amount_left=0) + stalledDL -> mixed(qB 重启场景)"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = QbManager("", config=_group_cfg(state_file), no_lock=True)  # 测试不持锁
        client = FakeClient()
        mgr.client = client
        t1 = FakeTorrent(hash="H1", name="T1", state="checkingUP", amount_left=0)
        t2 = FakeTorrent(hash="H2", name="T2", state="stalledDL", amount_left=100)
        key = ("R:/Downloads", ("movie.mkv", ))
        mgr.store.by_hash = {"H1": t1, "H2": t2}
        mgr.store.groups = {key: ["H1", "H2"]}
        mgr.store.group_sizes = {key: {}}
        mgr.store.member_to_key = {"H1": key, "H2": key}

        with mock.patch.object(mgr.api, "torrents_stop") as stop_mock:
            mgr._check_download_conflicts(dry_run=False)
        assert stop_mock.call_count == 1, f"校验中已完成成员与下载中并存应触发 mixed: {stop_mock.call_count}"
        assert (key, "mixed") in mgr.store.download_conflict_warned


def test_download_conflict_forced_queued_dl():
    """下载冲突: forcedDL + queuedDL 两个活跃下载 -> multi-dl"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = QbManager("", config=_group_cfg(state_file), no_lock=True)  # 测试不持锁
        client = FakeClient()
        mgr.client = client
        t1 = FakeTorrent(hash="H1", name="T1", state="forcedDL", amount_left=100)
        t2 = FakeTorrent(hash="H2", name="T2", state="queuedDL", amount_left=100)
        key = ("R:/Downloads", ("movie.mkv", ))
        mgr.store.by_hash = {"H1": t1, "H2": t2}
        mgr.store.groups = {key: ["H1", "H2"]}
        mgr.store.group_sizes = {key: {}}
        mgr.store.member_to_key = {"H1": key, "H2": key}

        with mock.patch.object(mgr.api, "torrents_stop") as stop_mock:
            mgr._check_download_conflicts(dry_run=False)
        assert stop_mock.call_count == 1, f"双下载应触发 multi-dl: {stop_mock.call_count}"
        assert (key, "multi-dl") in mgr.store.download_conflict_warned


def test_download_conflict_paused_dl_pair():
    """下载冲突: pausedDL + stoppedDL 停种(暂停)不算活跃下载 -> 不冲突不暂停"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = QbManager("", config=_group_cfg(state_file), no_lock=True)  # 测试不持锁
        client = FakeClient()
        mgr.client = client
        t1 = FakeTorrent(hash="H1", name="T1", state="pausedDL", amount_left=100)
        t2 = FakeTorrent(hash="H2", name="T2", state="stoppedDL", amount_left=100)
        key = ("R:/Downloads", ("movie.mkv", ))
        mgr.store.by_hash = {"H1": t1, "H2": t2}
        mgr.store.groups = {key: ["H1", "H2"]}
        mgr.store.group_sizes = {key: {}}
        mgr.store.member_to_key = {"H1": key, "H2": key}

        mgr._check_download_conflicts(dry_run=False)
        assert client.calls == [], f"暂停的下载不应触发冲突暂停: {client.calls}"
        assert mgr.store.download_conflict_warned == set()


def test_download_conflict_resolve_by_complete():
    """下载冲突: 混合冲突随下载完成(转做种)消除 -> 去重清除; 重现可再次触发"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = QbManager("", config=_group_cfg(state_file), no_lock=True)  # 测试不持锁
        client = FakeClient()
        mgr.client = client
        t1 = FakeTorrent(hash="H1", name="T1", state="downloading", amount_left=100)
        t2 = FakeTorrent(hash="H2", name="T2", state="stalledUP", amount_left=0)
        key = ("R:/Downloads", ("movie.mkv", ))
        mgr.store.by_hash = {"H1": t1, "H2": t2}
        mgr.store.groups = {key: ["H1", "H2"]}
        mgr.store.group_sizes = {key: {}}
        mgr.store.member_to_key = {"H1": key, "H2": key}

        with mock.patch.object(mgr.api, "torrents_stop") as stop_mock:
            mgr._check_download_conflicts(dry_run=False)
            assert stop_mock.call_count == 1
            assert (key, "mixed") in mgr.store.download_conflict_warned

            # 下载完成: 状态转做种 + amount_left=0 -> 冲突消除, 去重记录清除
            t1.state = "stalledUP"
            t1.amount_left = 0
            mgr._check_download_conflicts(dry_run=False)
            assert mgr.store.download_conflict_warned == set(), "下载完成应清除去重记录"
            assert stop_mock.call_count == 1

            # 新种子又开始下载 -> 冲突重现, 再次暂停
            t1.state = "downloading"
            t1.amount_left = 100
            mgr._check_download_conflicts(dry_run=False)
            assert stop_mock.call_count == 2, f"冲突重现应再次暂停: {stop_mock.call_count}"
            assert (key, "mixed") in mgr.store.download_conflict_warned


def test_download_conflict_two_groups_independent():
    """下载冲突: 两组同时冲突分别处理, 去重 key 按组独立; 一组消除不影响另一组"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = QbManager("", config=_group_cfg(state_file), no_lock=True)  # 测试不持锁
        client = FakeClient()
        mgr.client = client
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
            mgr._check_download_conflicts(dry_run=False)
            assert stop_mock.call_count == 2, f"两组各暂停一次: {stop_mock.call_count}"
            assert (key_a, "multi-dl") in mgr.store.download_conflict_warned
            assert (key_b, "mixed") in mgr.store.download_conflict_warned

            # 组A 冲突消除(H1 暂停) -> 仅组A 去重清除, 组B 保留且不重复暂停
            t1.state = "pausedDL"
            mgr._check_download_conflicts(dry_run=False)
            assert (key_a, "multi-dl") not in mgr.store.download_conflict_warned
            assert (key_b, "mixed") in mgr.store.download_conflict_warned
            assert stop_mock.call_count == 2


def test_group_members_not_in_group():
    """_group_members: 未归组 -> [自身 hash] 单种子(无参考)"""
    mgr = QbManager("", config=_group_cfg("state.json"), no_lock=True)  # 测试不持锁
    assert mgr._group_members("H1") == ["H1"]


def test_group_members_in_group():
    """_group_members: 已归组 -> 返回全部成员 hash"""
    mgr = QbManager("", config=_group_cfg("state.json"), no_lock=True)  # 测试不持锁
    mgr.store.member_to_key = {"H1": "g1", "H2": "g1"}
    mgr.store.groups = {"g1": ["H1", "H2"]}
    assert mgr._group_members("H1") == ["H1", "H2"]


def test_leave_group_removes():
    """_leave_group: 移出成员, 组内仍有剩余 -> 返回组 key"""
    mgr = QbManager("", config=_group_cfg("state.json"), no_lock=True)  # 测试不持锁
    mgr.store.member_to_key = {"H1": "g1", "H2": "g1"}
    mgr.store.groups = {"g1": ["H1", "H2"]}
    mgr.store.group_sizes = {"g1": {"H1": {}, "H2": {}}}
    assert mgr._leave_group("H1") == "g1"
    assert mgr.store.groups["g1"] == ["H2"]
    assert "H1" not in mgr.store.member_to_key
    assert "H1" not in mgr.store.group_sizes["g1"]


def test_leave_group_empty_deletes():
    """_leave_group: 组空 -> 删除整组返回 None"""
    mgr = QbManager("", config=_group_cfg("state.json"), no_lock=True)  # 测试不持锁
    mgr.store.member_to_key = {"H1": "g1"}
    mgr.store.groups = {"g1": ["H1"]}
    mgr.store.group_sizes = {"g1": {"H1": {}}}
    assert mgr._leave_group("H1") is None
    assert mgr.store.groups == {}
    assert mgr.store.group_sizes == {}


def test_leave_group_not_in_group():
    """_leave_group: 种子不在任何组 -> None 且不抛异常"""
    mgr = QbManager("", config=_group_cfg("state.json"), no_lock=True)  # 测试不持锁
    assert mgr._leave_group("NOPE") is None


def test_group_has_downloading():
    """_group_has_downloading: 组内存在活跃下载成员 -> True(成员状态读 store 快照)"""
    mgr = QbManager("", config=_group_cfg("state.json"), no_lock=True)  # 测试不持锁
    seed_store(mgr, [
        FakeTorrent(hash="H1", state="stalledDL"),
        FakeTorrent(hash="H2", state="stalledUP"),
    ])
    assert mgr._group_has_downloading(["H1", "H2"]) is True
    assert mgr._group_has_downloading(["H2"]) is False


def test_group_reference_candidates():
    """_group_reference_candidates: 组内已完成且未在校验的成员(参考种子候选, 读 store 快照)"""
    mgr = QbManager("", config=_group_cfg("state.json"), no_lock=True)  # 测试不持锁
    seed_store(
        mgr,
        [
            FakeTorrent(hash="H1", state="stalledUP"),
            FakeTorrent(hash="H2", state="pausedUP"),  # 已完成但停止做种: 亦是有效参考
            FakeTorrent(hash="H3", state="checkingUP"),  # 校验中: 完整性存疑, 排除
            FakeTorrent(hash="H4", state="downloading"),  # 未完成: 排除
        ]
    )
    cands = mgr._group_reference_candidates(["H1", "H2", "H3", "H4"])
    assert [t.hash for t in cands] == ["H1", "H2"]


def test_grouping_save_path_change_no_cache():
    """_handle_save_path_changes: 无缓存文件映射 -> 跳过该种子(维持原行为)"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = QbManager("", config=_group_cfg(state_file), no_lock=True)  # 测试不持锁
        client = FakeClient()
        mgr.client = client

        t1 = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=r"R:\DownloadsB")
        seed_store(mgr, [t1])
        mgr.store.member_to_key["H1"] = (r"R:\DownloadsA", ("movie.mkv", ))
        mgr.store.group_sizes = {}  # 无缓存映射
        mgr._handle_save_path_changes(dry_run=False)
        # 无旧映射 -> 不重归组也不触发扫描
        assert client.calls == []
        assert "H1" not in mgr.store.groups


def test_assign_new_torrent_missing():
    """_assign_new_torrent: 哈希不在 store 快照 -> AttributeError 上抛(调用方保证传入存在的 hash)"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = QbManager("", config=_group_cfg(state_file), no_lock=True)  # 测试不持锁
        client = FakeClient()
        mgr.client = client
        with pytest.raises(AttributeError):
            mgr._assign_new_torrent("NOPE", dry_run=False)
        assert client.files_calls == 0, "tor 不存在不应拉文件列表"


def test_assign_new_torrent_files_error():
    """_assign_new_torrent: 文件列表拉取异常 -> 异常上抛(不缓存, 由 run 主循环兜底), 不归组"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = QbManager("", config=_group_cfg(state_file), no_lock=True)  # 测试不持锁
        client = FakeClient()
        mgr.client = client

        def boom(h):
            raise RuntimeError("api down")

        client.torrents_files = boom
        t1 = FakeTorrent(hash="H1", name="T1", state="stalledUP")
        seed_store(mgr, [t1])
        with pytest.raises(RuntimeError, match="api down"):
            mgr._assign_new_torrent("H1", dry_run=False)
        assert client.calls == []
        assert "H1" not in mgr.store.member_to_key


def test_assign_to_group_empty_map():
    """_assign_to_group: 空文件映射 -> 不归组"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = QbManager("", config=_group_cfg(state_file), no_lock=True)  # 测试不持锁
        client = FakeClient()
        mgr.client = client
        t1 = FakeTorrent(hash="H1", name="T1", state="stalledUP")
        mgr._assign_to_group(t1, {}, dry_run=False)
        assert mgr.store.groups == {}
        assert client.calls == []


def test_check_missing_files_no_seeding_rep():
    """_check_missing_files: 组内无已完成未校验种子 -> 不检查; 暂停完成成员亦是有效代表"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = QbManager("", config=_group_cfg(state_file), no_lock=True)  # 测试不持锁
        client = FakeClient()
        mgr.client = client
        members = [FakeTorrent(hash="H1", name="T1", state="pausedUP", amount_left=100)]
        mgr._check_missing_files(members, {}, dry_run=False)
        assert client.calls == [], "未完成成员不应作为代表扫描"
        # 暂停已完成(amount_left=0): is_complete 判定下路径同样可扫, 缺文件触发暂停 + MISSING
        paused_done = FakeTorrent(hash="H2", name="T2", state="pausedUP", save_path=td, amount_left=0)
        mgr._check_missing_files([paused_done], {"H2": {"movie.mkv": 100}}, dry_run=False)
        assert client.calls.count(("stop", None)) == 1, f"暂停完成代表缺文件应暂停: {client.calls}"
        assert "MISSING" in client.tags


def test_check_missing_files_size_mismatch():
    """_check_missing_files: 文件存在但大小不符 -> 警告 + 整组暂停 + MISSING"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = QbManager("", config=_group_cfg(state_file), no_lock=True)  # 测试不持锁
        client = FakeClient()
        mgr.client = client
        real = os.path.join(td, "movie.mkv")
        with open(real, "wb") as f:
            f.write(b"x" * 10)
        rep = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=td, amount_left=0)
        sizes = {"H1": {"movie.mkv": 999}}  # 期望 999, 实际 10
        mgr._check_missing_files([rep], sizes, dry_run=False)
        assert client.calls.count(("stop", None)) == 1, f"大小不符应整组暂停: {client.calls}"
        assert "MISSING" in client.tags


def test_check_missing_files_getsize_error():
    """_check_missing_files: 文件读取 OSError -> 警告 + 整组暂停 + MISSING"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = QbManager("", config=_group_cfg(state_file), no_lock=True)  # 测试不持锁
        client = FakeClient()
        mgr.client = client
        real = os.path.join(td, "movie.mkv")
        with open(real, "wb") as f:
            f.write(b"x" * 10)
        rep = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=td, amount_left=0)
        sizes = {"H1": {"movie.mkv": 10}}
        with mock.patch("os.path.getsize", side_effect=OSError("denied")):
            mgr._check_missing_files([rep], sizes, dry_run=False)
        assert client.calls.count(("stop", None)) == 1, f"读取失败应整组暂停: {client.calls}"
        assert "MISSING" in client.tags


def test_check_missing_files_checking_up_not_rep():
    """_check_missing_files: checkingUP(校验中, is_checking)不算有效代表 -> 不扫描;
    对照 stalledUP(校验完成做种)作代表 -> 缺文件触发暂停 + MISSING"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = QbManager("", config=_group_cfg(state_file), no_lock=True)  # 测试不持锁
        client = FakeClient()
        mgr.client = client

        # checkingUP: is_complete 但 is_checking -> 排除出有效代表, 不扫描
        checking_up = FakeTorrent(hash="H1", name="T1", state="checkingUP", save_path=td, amount_left=0)
        sizes = {"H1": {"movie.mkv": 100}}  # 文件不存在
        mgr._check_missing_files([checking_up], sizes, dry_run=False)
        assert client.calls == [], f"checkingUP 非有效代表不应触发扫描: {client.calls}"

        # 对照: stalledUP 作代表 -> 缺文件暂停 + MISSING
        stalled_up = FakeTorrent(hash="H2", name="T2", state="stalledUP", save_path=td, amount_left=0)
        sizes2 = {"H2": {"movie.mkv": 100}}
        mgr._check_missing_files([stalled_up], sizes2, dry_run=False)
        assert client.calls.count(("stop", None)) == 1, f"stalledUP 作代表缺文件应暂停: {client.calls}"
        assert "MISSING" in client.tags


def test_check_missing_files_first_done_rep():
    """_check_missing_files: 多已完成成员取第一个作代表, 非代表大小映射差异不影响扫描结果"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = QbManager("", config=_group_cfg(state_file), no_lock=True)  # 测试不持锁
        client = FakeClient()
        mgr.client = client
        real = os.path.join(td, "movie.mkv")
        with open(real, "wb") as f:
            f.write(b"x" * 10)
        t1 = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=td, amount_left=0)
        t2 = FakeTorrent(hash="H2", name="T2", state="stalledUP", save_path=td, amount_left=0)
        # 代表 H1 大小正确; 非代表 H2 期望大小错误(仅扫代表, 不应触发)
        sizes = {"H1": {"movie.mkv": 10}, "H2": {"movie.mkv": 999}}
        mgr._check_missing_files([t1, t2], sizes, dry_run=False)
        assert client.calls == [], f"非代表成员大小差异不应触发: {client.calls}"
        # 代表 H1 大小错误 -> 触发
        sizes2 = {"H1": {"movie.mkv": 999}, "H2": {"movie.mkv": 10}}
        mgr._check_missing_files([t1, t2], sizes2, dry_run=False)
        assert client.calls.count(("stop", None)) == 1, f"代表大小不符应整组暂停: {client.calls}"
        assert "MISSING" in client.tags


def test_check_missing_files_empty_sizes_map():
    """_check_missing_files: 大小映射为空 -> 无文件可检查, 不误报"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = QbManager("", config=_group_cfg(state_file), no_lock=True)  # 测试不持锁
        client = FakeClient()
        mgr.client = client
        rep = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=td, amount_left=0)
        mgr._check_missing_files([rep], {}, dry_run=False)
        assert client.calls == [], f"空大小映射不应触发扫描: {client.calls}"


def test_check_missing_files_member_has_tag():
    """_check_missing_files: 成员已带 MISSING 标签 -> 不重复 add_tags(仍暂停)"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = QbManager("", config=_group_cfg(state_file), no_lock=True)  # 测试不持锁
        client = FakeClient()
        mgr.client = client
        rep = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=td, amount_left=0, tags="MISSING")
        sizes = {"H1": {"movie.mkv": 100}}  # 文件不存在
        mgr._check_missing_files([rep], sizes, dry_run=False)
        assert client.calls.count(("stop", None)) == 1, f"缺文件仍应暂停: {client.calls}"
        assert ("add_tags", ["MISSING"]) not in client.calls, "已有标签不应重复添加"


def test_check_missing_files_dry_run():
    """_check_missing_files dry-run: 不暂停也不加标签"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = QbManager("", config=_group_cfg(state_file), no_lock=True)  # 测试不持锁
        client = FakeClient()
        mgr.client = client
        rep = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=td, amount_left=0)
        sizes = {"H1": {"movie.mkv": 100}}  # 文件不存在
        mgr._check_missing_files([rep], sizes, dry_run=True)
        assert client.calls == [], f"dry-run 不应暂停/加标签: {client.calls}"
        assert "MISSING" not in client.tags
