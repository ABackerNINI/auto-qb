"""种子分组测试(原 test_rules.py 迁移): 增量归组 / 大小一致性 / 缺文件联动 / 保存路径变化"""
import os
import tempfile
from types import SimpleNamespace

from auto_qb.config import GroupingConfig
from auto_qb.qbmanager import QbManager
from helpers import FakeClient, FakeConfig, FakeTorrent


def _fake_file(name, size):
    return SimpleNamespace(name=name, size=size)


def _group_cfg(state_file, enabled=True):
    cfg = FakeConfig()
    cfg.state_file = state_file
    cfg.grouping = GroupingConfig(enabled=enabled, interval=300, missing_tag="MISSING")
    return cfg


def test_grouping_size_mismatch_pauses_group():
    """新增种子归组时文件大小不一致 -> 警告 + 整组暂停(不加标签, 不再每轮检查)"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        cfg = _group_cfg(state_file)
        mgr = QbManager("", config=cfg)
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
        mgr = QbManager("", config=cfg)
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
        assert mgr._group_state_snapshot.get("H1") == "pausedUP", f"状态快照应更新: {mgr._group_state_snapshot}"


def test_grouping_state_change_triggers_check():
    """仅"上传转暂停"触发检查(检测到即立即处理); 上传状态间变化/状态不变不触发"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        cfg = _group_cfg(state_file)
        mgr = QbManager("", config=cfg)
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
        mgr = QbManager("", config=cfg)
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

        key = next(iter(mgr._groups))
        assert mgr._groups[key] == ["H1"], f"删除后组内成员: {mgr._groups}"
        assert client.calls.count(("stop", None)) == 1, f"删除种子应立即触发整组暂停: {client.calls}"
        assert "MISSING" in client.tags, f"文件丢失应加标签: {client.tags}"


def test_grouping_no_global_task():
    """分组为事件驱动, 不再创建周期轮询全局任务"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = QbManager("", config=_group_cfg(state_file))
        names = {t.name for t in mgr.task_queue._fast}
        assert "grouping" not in names, f"事件驱动不应创建分组周期任务: {names}"

        # 未启用也不创建
        mgr2 = QbManager("", config=_group_cfg(state_file, enabled=False))
        names2 = {t.name for t in mgr2.task_queue._fast}
        assert "grouping" not in names2, f"未启用也不应创建分组任务: {names2}"


def test_grouping_replaces_per_torrent_missing_files():
    """逐种子 missing_files 任务已移除, 缺文件检查统一由分组事件驱动承担"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        cfg = _group_cfg(state_file)
        cfg.check_missing_files = True
        mgr = QbManager("", config=cfg)
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(hash="H1", name="T1")
        mgr._snapshot = [tor]

        mgr._create_torrent_tasks("H1")
        names = {t.name for t in mgr.task_queue._fast}
        assert "missing_files" not in names, f"不应创建逐种子检查: {names}"

        # 未启用分组同样不创建(逐种子检查已整体移除, 不再回退)
        cfg2 = _group_cfg(state_file, enabled=False)
        cfg2.check_missing_files = True
        mgr2 = QbManager("", config=cfg2)
        mgr2.client = FakeClient()
        mgr2._snapshot = [tor]
        mgr2._create_torrent_tasks("H1")
        names2 = {t.name for t in mgr2.task_queue._fast}
        assert "missing_files" not in names2, f"未启用分组也不应创建逐种子检查: {names2}"


def test_grouping_incremental_on_add():
    """新增种子时自动归组(增量), 不再每轮全量重建分组"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = QbManager("", config=_group_cfg(state_file))
        client = FakeClient()
        mgr.client = client

        # 新增 H1 -> _refresh_torrents 检测 added 并自动归组(全部增量归组, 无初始化)
        t1 = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=r"R:\Downloads")
        client.torrents["H1"] = t1
        client.files_map["H1"] = [_fake_file("movie.mkv", 100)]
        mgr._refresh_torrents()
        assert len(mgr._groups) == 1, f"新种子应自动归组: {mgr._groups}"
        key = next(iter(mgr._groups))
        assert mgr._groups[key] == ["H1"], f"组内成员: {mgr._groups[key]}"
        assert key == ("R:/Downloads", ("movie.mkv", )), f"分组键: {key}"

        # 再新增 H2(同名同大小) -> 归入同一组
        t2 = FakeTorrent(hash="H2", name="T2", state="stalledUP", save_path=r"R:\Downloads")
        client.torrents["H2"] = t2
        client.files_map["H2"] = [_fake_file("movie.mkv", 100)]
        mgr._refresh_torrents()
        assert len(mgr._groups) == 1, f"H2 应归入同组: {mgr._groups}"
        assert set(mgr._groups[key]) == {"H1", "H2"}, f"组内成员: {mgr._groups[key]}"


def test_grouping_removed_from_groups():
    """种子删除时自动从分组移除(空组删除)"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = QbManager("", config=_group_cfg(state_file))
        client = FakeClient()
        mgr.client = client

        t1 = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=r"R:\Downloads")
        t2 = FakeTorrent(hash="H2", name="T2", state="stalledUP", save_path=r"R:\Downloads")
        client.torrents["H1"] = t1
        client.torrents["H2"] = t2
        client.files_map["H1"] = [_fake_file("movie.mkv", 100)]
        client.files_map["H2"] = [_fake_file("movie.mkv", 100)]
        mgr._refresh_torrents()
        key = next(iter(mgr._groups))
        assert set(mgr._groups[key]) == {"H1", "H2"}

        # 删除 H2 -> 组内只剩 H1
        del client.torrents["H2"]
        mgr._refresh_torrents()
        assert mgr._groups[key] == ["H1"], f"删除后组内成员: {mgr._groups[key]}"
        assert "H2" not in mgr._group_sizes[key], f"删除后应清掉文件大小映射: {mgr._group_sizes}"

        # 删除 H1 -> 空组删除
        del client.torrents["H1"]
        mgr._refresh_torrents()
        assert mgr._groups == {}, f"空组应删除: {mgr._groups}"
        assert mgr._group_sizes == {}, f"空组大小映射应删除: {mgr._group_sizes}"


def test_grouping_save_path_change_triggers_check():
    """种子保存路径变化 -> 原组剩余成员触发缺文件扫描; 新组已有其它成员也触发扫描"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = QbManager("", config=_group_cfg(state_file))
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
        assert set(mgr._groups[key_a]) == {"H1", "H2"}
        assert set(mgr._groups[key_b]) == {"H3"}

        # H1 保存路径改为 DownloadsB -> 原组 A 剩 H2 触发扫描; 新组 B 有 H1+H3 也触发扫描
        t1.save_path = r"R:\DownloadsB"
        mgr._refresh_torrents()

        assert set(mgr._groups[key_a]) == {"H2"}, f"H1 应移出原组: {mgr._groups[key_a]}"
        assert set(mgr._groups[key_b]) == {"H1", "H3"}, f"H1 应重归新组: {mgr._groups[key_b]}"
        assert client.calls.count(("stop", None)) == 2, f"原组与新组各扫描一次并整组暂停: {client.calls}"
        assert client.calls.count(("add_tags", ["MISSING"])) == 3, f"三个成员应分别加标签: {client.calls}"


def test_grouping_save_path_change_new_group_alone():
    """保存路径变化但新组无其它成员 -> 仅原组触发扫描, 新组不扫"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = QbManager("", config=_group_cfg(state_file))
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

        assert set(mgr._groups[("R:/DownloadsA", ("movie.mkv", ))]) == {"H2"}
        assert mgr._groups[("R:/DownloadsB", ("movie.mkv", ))] == ["H1"]
        assert client.calls.count(("stop", None)) == 1, f"仅原组扫描暂停一次: {client.calls}"
        assert client.calls.count(("add_tags", ["MISSING"])) == 1, f"仅 H2 加标签: {client.calls}"


def test_grouping_no_full_files_scan():
    """归组仅拉一次文件列表(增量归组); 后续刷新状态不变不触发扫描, 不重复拉取"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = QbManager("", config=_group_cfg(state_file))
        client = FakeClient()
        mgr.client = client

        t1 = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=r"R:\Downloads")
        client.torrents["H1"] = t1
        client.files_map["H1"] = [_fake_file("movie.mkv", 100)]

        # 归组(首轮视为新增, 增量归组): 仅在此处拉一次文件列表
        mgr._refresh_torrents()
        assert client.files_calls == 1, f"归组应只拉一次文件列表: {client.files_calls}"
        assert len(mgr._groups) == 1, f"首轮应完成归组: {mgr._groups}"

        # 后续刷新: 状态不变 -> 不触发扫描, 也不拉取文件列表
        mgr._refresh_torrents()
        assert client.files_calls == 1, f"后续刷新不应再拉文件列表: {client.files_calls}"
        assert client.calls == [], f"状态不变不应触发检查: {client.calls}"
