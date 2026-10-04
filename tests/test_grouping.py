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
- test_group_has_downloading_delegates_to_store: _group_has_downloading 委托 store 单点等价断言(plan 26-10-05-0314 T9: 同输入同输出 + 路由钉死)
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
- test_check_missing_files_qb_transitional_suffix_skips: 原名缺失但 .!qB 孪生存在 -> 过渡态本轮不判缺失(不暂停不打标, 计数+1)
- test_check_missing_files_transitional_skip_limit_reaches_missing: 过渡态连续 3 次未消除 -> 第 3 次按真实缺失暂停 + MISSING(残留兜底)
- test_check_missing_files_transitional_counter_resets_on_clean: 过渡态跳过后一次正常判定 -> 计数清零, 之后需重新连续 3 次
- test_check_missing_files_real_missing_no_twin: 原名缺失且无孪生 -> 照旧判缺失(回归保护)
- test_check_missing_files_dry_run_transitional: dry-run 下过渡态命中 -> 零外部副作用(不暂停不打标)
- test_grouping_errored_transition_pauses_group: 重校验发现缺失(进入 errored)-> 同轮整组暂停 + MISSING; 持续 errored 不重复触发
- test_grouping_errored_via_checking_transition: 经 checkingUP/checkingResumeData 中间态 -> 校验拍不触发, missingFiles 拍触发
- test_grouping_errored_files_intact_no_action: errored 转换但磁盘文件齐全 -> 无动作(保守)
- test_grouping_errored_whole_group_representative: 全组同时 errored -> errored 成员作代表仍能扫描暂停 + MISSING
- test_grouping_errored_check_disabled: check_missing_files=False -> errored 转换不触发
- test_download_conflict_missing_done_excluded: mixed 冲突排除带 MISSING 标签的完成成员(重下补救); 无标签照旧触发
- test_download_conflict_multi_dl_with_missing_tag: multi-dl 不受 MISSING 标签豁免仍拦截
- test_missing_scan_dedup_within_round: 同组同轮多触发源只扫一次(轮内去重), 跨轮清空后可再扫
- test_group_key_of_is_single_source_of_truth: 归组 key 纯函数 group_key_of 与真实 mixin 输出一致(语料计划 §04 守阵)
- test_grouping_removed_event_disabled_check_returns_early: 删除事件 check_missing_files=False 早退 (P2-a)
- test_grouping_removed_event_group_emptied_no_scan: 组内最后成员删除 -> 组解散不扫描 (P2-a)
- test_grouping_save_path_change_ghost_and_same_path_skipped: save_path 变化幽灵 hash / 未变路径跳过 (P2-a)
- test_grouping_save_path_change_no_cached_map_skipped: 无缓存文件映射不重归组 (P2-a)
- test_grouping_save_path_change_stale_group_no_scan: 原组剩余成员均已不在快照不扫描 (P2-a)
- test_grouping_state_transitions_first_round_and_empty_paths: 状态转移首轮无快照 / key 缺失 / 空组跳过 (P2-a)
- test_grouping_size_consistency_dry_run_no_stop: 大小一致性 dry-run 只告警 (P2-a)
- test_grouping_leave_group_member_index_missing_from_group_list: 索引有组表无的成员移出仍清理映射 (P2-a)
- test_grouping_missing_files_check_disabled_guard: 缺文件检查入口禁用守卫 (P2-a)
- test_grouping_conflict_scan_skips_ghost_members: 冲突扫描幽灵成员跳过; _group_has_downloading 幽灵不活跃 (P2-a)
- test_cross_group_partial_overlap_warns: 场景①部分重叠 -> 警告含重叠文件物理路径; S3 起处置生效 (26-10-04-0107 S2/S3)
- test_cross_group_case_only_posix_no_false_positive: 场景②POSIX normcase 恒等 -> 大小写不同不误报 (26-10-04-0107 S2)
- test_cross_group_case_only_windows_detected: 场景②Windows normcase 折叠 -> 大小写交叉检出 (26-10-04-0107 S2)
- test_cross_group_junction_alias_detected: 场景③junction 别名目录 realpath_lexical 归同 -> 检出 (26-10-04-0107 S2)
- test_cross_group_missing_tag_exempt: D3 任一侧成员带 MISSING 标签豁免, 去标签后照常检出 (26-10-04-0107 S2)
- test_cross_group_zero_change_short_circuit: rounds_applied>0 且 dirty 空 -> 提前返回; dirty 非空恢复全量 (26-10-04-0107 S2)
- test_cross_group_switch_off_silent: 开关缺省 false -> 交叉在场仍零输出零动作, 打开后检出 (26-10-04-0107 S2)
- test_cross_group_same_group_overlap_not_triggered: 同组文件重叠是分组固有属性 -> 不触发跨组警告 (26-10-04-0107 S2)
- test_cross_group_dispose_stops_downloader: S3 触发处置: 交叉在场 -> 仅暂停涉事下载方(hash 精确, 不含完成侧), 组对入去重 (26-10-04-0107 S3)
- test_cross_group_dispose_dedup_no_repeat: S3 去重门: 冲突持续不重复警告/暂停(暂停幂等) (26-10-04-0107 S3)
- test_cross_group_dispose_clear_and_retrigger: S3 消除+重现: 下载方转暂停 -> 去重清除且 stop 不增; 恢复下载 -> 再次触发 (26-10-04-0107 S3)
- test_cross_group_dispose_seeder_side_untouched: S3/D2: stop 名单只含下载方, 无完成/做种成员混入 (26-10-04-0107 S3)
- test_cross_group_dispose_dry_run_only_warns: S3 dry-run: 警告在, 不暂停, 不记去重 (26-10-04-0107 S3)
- test_cross_group_reset_runtime_keeps_warned: S3 reset_runtime 有意不清跨组去重集合(决策钉死, 防后人顺手加 clear) (26-10-04-0107 S3)
- test_cross_group_single_side_dirty_still_detected: S3/风险2: 单侧脏(dirty 仅含组 A)仍全量检出并暂停 (26-10-04-0107 S3)
"""
import logging
import os
import tempfile
from contextlib import contextmanager
from types import SimpleNamespace
from unittest import mock

import pytest

from auto_qb.config import GroupingConfig
from auto_qb.core.qbmanager import QbManager
from helpers import FakeClient, FakeConfig, FakeTorrent, seed_store


def _fake_file(name, size):
    return SimpleNamespace(name=name, size=size)


def _non_tag_calls(client):
    """排除 maintenance 的 add_tags 噪音(tracker 标签), 只看分组相关动作"""
    return [c for c in client.calls if c[0] != "add_tags"]


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
        assert _non_tag_calls(client) == [], f"上传状态不应触发检查: {client.calls}"

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
        client.calls.clear()
        mgr._refresh_torrents()
        assert _non_tag_calls(client) == [], f"状态不变不应重复触发: {client.calls}"


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
        assert _non_tag_calls(client) == [], f"上传状态不应触发检查: {client.calls}"

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

        mgr.host.get("rules")._create_torrent_tasks("H1")
        names = {t.name for t in mgr.task_queue._fast}
        assert "missing_files" not in names, f"不应创建逐种子检查: {names}"

        # 未启用分组同样不创建(逐种子检查已整体移除, 不再回退)
        cfg2 = _group_cfg(state_file, enabled=False)
        cfg2.check_missing_files = True
        mgr2 = QbManager("", config=cfg2, no_lock=True)  # 测试不持锁
        mgr2.client = FakeClient()
        seed_store(mgr2, [tor])
        mgr2.host.get("rules")._create_torrent_tasks("H1")
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
        assert _non_tag_calls(client) == [], f"首轮归组不应触发扫描: {client.calls}"

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
        assert _non_tag_calls(client) == [], f"状态不变不应触发检查: {client.calls}"


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
    assert mgr.host.get("grouping")._group_has_downloading(["H1"]) is False, "checkingDL 不应算下载中"
    assert mgr.host.get("grouping")._group_has_downloading(["H2"]) is False, "checkingUP 不应算下载中"
    assert mgr.host.get("grouping")._group_has_downloading(["H3"]) is False, "checkingResumeData 不应算下载中"
    assert mgr.host.get("grouping")._group_has_downloading(["H1", "H2", "H3"]) is False, "组内只有强制校验种子不应算活跃下载"


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
        assert _non_tag_calls(client) == [], f"强制校验种子不应触发下载冲突暂停: {client.calls}"
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

        mgr.host.get("grouping")._check_download_conflicts(dry_run=False)
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
            mgr.host.get("grouping")._check_download_conflicts(dry_run=False)
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
            mgr.host.get("grouping")._check_download_conflicts(dry_run=False)
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
            mgr.host.get("grouping")._check_download_conflicts(dry_run=False)
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

        mgr.host.get("grouping")._check_download_conflicts(dry_run=False)
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


def test_group_members_not_in_group():
    """_group_members: 未归组 -> [自身 hash] 单种子(无参考)"""
    mgr = QbManager("", config=_group_cfg("state.json"), no_lock=True)  # 测试不持锁
    assert mgr.host.get("grouping")._group_members("H1") == ["H1"]


def test_group_members_in_group():
    """_group_members: 已归组 -> 返回全部成员 hash"""
    mgr = QbManager("", config=_group_cfg("state.json"), no_lock=True)  # 测试不持锁
    mgr.store.member_to_key = {"H1": "g1", "H2": "g1"}
    mgr.store.groups = {"g1": ["H1", "H2"]}
    assert mgr.host.get("grouping")._group_members("H1") == ["H1", "H2"]


def test_leave_group_removes():
    """_leave_group: 移出成员, 组内仍有剩余 -> 返回组 key"""
    mgr = QbManager("", config=_group_cfg("state.json"), no_lock=True)  # 测试不持锁
    mgr.store.member_to_key = {"H1": "g1", "H2": "g1"}
    mgr.store.groups = {"g1": ["H1", "H2"]}
    mgr.store.group_sizes = {"g1": {"H1": {}, "H2": {}}}
    assert mgr.host.get("grouping")._leave_group("H1") == "g1"
    assert mgr.store.groups["g1"] == ["H2"]
    assert "H1" not in mgr.store.member_to_key
    assert "H1" not in mgr.store.group_sizes["g1"]


def test_leave_group_empty_deletes():
    """_leave_group: 组空 -> 删除整组返回 None"""
    mgr = QbManager("", config=_group_cfg("state.json"), no_lock=True)  # 测试不持锁
    mgr.store.member_to_key = {"H1": "g1"}
    mgr.store.groups = {"g1": ["H1"]}
    mgr.store.group_sizes = {"g1": {"H1": {}}}
    assert mgr.host.get("grouping")._leave_group("H1") is None
    assert mgr.store.groups == {}
    assert mgr.store.group_sizes == {}


def test_leave_group_not_in_group():
    """_leave_group: 种子不在任何组 -> None 且不抛异常"""
    mgr = QbManager("", config=_group_cfg("state.json"), no_lock=True)  # 测试不持锁
    assert mgr.host.get("grouping")._leave_group("NOPE") is None


def test_group_has_downloading():
    """_group_has_downloading: 组内存在活跃下载成员 -> True(成员状态读 store 快照)"""
    mgr = QbManager("", config=_group_cfg("state.json"), no_lock=True)  # 测试不持锁
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
    mgr = QbManager("", config=_group_cfg("state.json"), no_lock=True)  # 测试不持锁
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
    cands = mgr.host.get("grouping")._group_reference_candidates(["H1", "H2", "H3", "H4"])
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
        mgr.host.get("grouping")._handle_save_path_changes(dry_run=False)
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
            mgr.host.get("grouping")._assign_new_torrent("NOPE", dry_run=False)
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
            mgr.host.get("grouping")._assign_new_torrent("H1", dry_run=False)
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
        mgr.host.get("grouping")._assign_to_group(t1, {}, dry_run=False)
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
        mgr = QbManager("", config=_group_cfg(state_file), no_lock=True)  # 测试不持锁
        client = FakeClient()
        mgr.client = client
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
        mgr = QbManager("", config=_group_cfg(state_file), no_lock=True)  # 测试不持锁
        client = FakeClient()
        mgr.client = client
        real = os.path.join(td, "movie.mkv")
        with open(real, "wb") as f:
            f.write(b"x" * 10)
        rep = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=td, amount_left=0)
        sizes = {"H1": {"movie.mkv": 10}}
        with mock.patch("os.path.getsize", side_effect=OSError("denied")):
            mgr.host.get("grouping")._check_missing_files([rep], sizes, dry_run=False, key="K")
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
        mgr.host.get("grouping")._check_missing_files([checking_up], sizes, dry_run=False, key="K")
        assert client.calls == [], f"checkingUP 非有效代表不应触发扫描: {client.calls}"

        # 对照: stalledUP 作代表 -> 缺文件暂停 + MISSING
        stalled_up = FakeTorrent(hash="H2", name="T2", state="stalledUP", save_path=td, amount_left=0)
        sizes2 = {"H2": {"movie.mkv": 100}}
        mgr.host.get("grouping")._check_missing_files([stalled_up], sizes2, dry_run=False, key="K")
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
        mgr = QbManager("", config=_group_cfg(state_file), no_lock=True)  # 测试不持锁
        client = FakeClient()
        mgr.client = client
        rep = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=td, amount_left=0)
        mgr.host.get("grouping")._check_missing_files([rep], {}, dry_run=False, key="K")
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
        mgr.host.get("grouping")._check_missing_files([rep], sizes, dry_run=False, key="K")
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
        mgr = QbManager("", config=_group_cfg(state_file), no_lock=True)  # 测试不持锁
        client = FakeClient()
        mgr.client = client
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
        mgr = QbManager("", config=_group_cfg(state_file), no_lock=True)  # 测试不持锁
        client = FakeClient()
        mgr.client = client
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
        mgr = QbManager("", config=_group_cfg(state_file), no_lock=True)  # 测试不持锁
        client = FakeClient()
        mgr.client = client
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
        mgr = QbManager("", config=_group_cfg(state_file), no_lock=True)  # 测试不持锁
        client = FakeClient()
        mgr.client = client
        rep = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=td, amount_left=0)
        sizes = {"H1": {"movie.mkv": 100}}  # 文件不存在, 也无孪生
        mgr.host.get("grouping")._check_missing_files([rep], sizes, dry_run=False, key="K")
        assert client.calls.count(("stop", None)) == 1, f"真实缺失应照旧暂停: {client.calls}"
        assert "MISSING" in client.tags


def test_check_missing_files_dry_run_transitional():
    """dry-run 下过渡态命中 -> 零外部副作用(不暂停、不加标签; 计数为会话内报告态)"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = QbManager("", config=_group_cfg(state_file), no_lock=True)  # 测试不持锁
        client = FakeClient()
        mgr.client = client
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
        assert _non_tag_calls(client) == [], f"上传状态不应触发检查: {client.calls}"

        # H1 强制重校验发现文件缺失 -> missingFiles(errored) -> 同轮触发缺文件扫描(文件不存在)
        t1.state = "missingFiles"
        mgr._refresh_torrents()

        assert client.calls.count(("stop", None)) == 1, f"errored 转换应触发整组暂停: {client.calls}"
        assert "MISSING" in client.tags, f"丢失应添加标签: {client.tags}"

        # 持续 errored(状态不变) -> 不重复触发
        client.calls.clear()
        mgr._refresh_torrents()
        assert _non_tag_calls(client) == [], f"持续 errored 不应重复触发: {client.calls}"


def test_grouping_errored_via_checking_transition():
    """errored 触发不依赖中间状态名: stalledUP -> checkingUP/checkingResumeData(校验中, 不触发)
    -> missingFiles(下一拍触发)"""
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


def test_grouping_errored_files_intact_no_action():
    """errored 转换但磁盘文件齐全(非缺文件的 error)-> 扫描确认后无任何动作(保守)"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        cfg = _group_cfg(state_file)
        mgr = QbManager("", config=cfg, no_lock=True)  # 测试不持锁
        client = FakeClient()
        mgr.client = client

        # 真实文件存在且大小一致
        real_file = os.path.join(td, "movie.mkv")
        with open(real_file, "wb") as f:
            f.write(b"x" * 100)

        t1 = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=td)
        t2 = FakeTorrent(hash="H2", name="T2", state="stalledUP", save_path=td)
        client.torrents["H1"] = t1
        client.torrents["H2"] = t2
        client.files_map["H1"] = [_fake_file("movie.mkv", 100)]
        client.files_map["H2"] = [_fake_file("movie.mkv", 100)]
        mgr._refresh_torrents()  # 首轮归组

        # H1 进入 errored(如 tracker 报错等非缺文件原因) -> 扫描文件齐全 -> 无动作
        t1.state = "missingFiles"
        mgr._refresh_torrents()
        assert _non_tag_calls(client) == [], f"文件齐全不应暂停/加标签: {client.calls}"
        assert "MISSING" not in client.tags


def test_grouping_errored_whole_group_representative():
    """全组同时进入 errored(如同轮重校验全部成员)-> errored 成员可作代表种, 仍能扫描暂停 + MISSING"""
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
        mgr._refresh_torrents()  # 首轮归组

        # 全组同轮 missingFiles -> 无健康成员, errored 成员作代表 -> 扫描缺文件 -> 暂停 + MISSING
        t1.state = "missingFiles"
        t2.state = "missingFiles"
        mgr._refresh_torrents()
        assert client.calls.count(("stop", None)) == 1, f"全组 errored 仍应扫描并暂停: {client.calls}"
        assert "MISSING" in client.tags, f"丢失应添加标签: {client.tags}"


def test_grouping_errored_check_disabled():
    """grouping.check_missing_files=False -> errored 转换不触发缺文件扫描"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        cfg = _group_cfg(state_file)
        cfg.grouping.check_missing_files = False
        mgr = QbManager("", config=cfg, no_lock=True)  # 测试不持锁
        client = FakeClient()
        mgr.client = client

        t1 = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=r"R:\Downloads")
        t2 = FakeTorrent(hash="H2", name="T2", state="stalledUP", save_path=r"R:\Downloads")
        client.torrents["H1"] = t1
        client.torrents["H2"] = t2
        client.files_map["H1"] = [_fake_file("movie.mkv", 100)]
        client.files_map["H2"] = [_fake_file("movie.mkv", 100)]
        mgr._refresh_torrents()  # 首轮归组

        t1.state = "missingFiles"
        mgr._refresh_torrents()
        assert _non_tag_calls(client) == [], f"缺文件检查禁用不应触发: {client.calls}"
        assert "MISSING" not in client.tags


def test_download_conflict_missing_done_excluded():
    """mixed 冲突排除带 MISSING 标签的已完成成员: MISSING 组重新下载是合法补救, 不拦停;
    对照: 完成成员无 MISSING 标签(健康组)-> 照旧触发 mixed 暂停"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = QbManager("", config=_group_cfg(state_file), no_lock=True)  # 测试不持锁
        client = FakeClient()
        mgr.client = client
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
        mgr = QbManager("", config=_group_cfg(state_file), no_lock=True)  # 测试不持锁
        client = FakeClient()
        mgr.client = client
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


def test_missing_scan_dedup_within_round():
    """缺文件扫描轮内去重: 同组 key 同轮多触发源(如状态转移+路径变化)只扫一次; 轮重置后可再扫"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = QbManager("", config=_group_cfg(state_file), no_lock=True)  # 测试不持锁
        client = FakeClient()
        mgr.client = client
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


def test_group_key_of_is_single_source_of_truth():
    """归组 key 纯函数与真实 mixin 输出一致(守阵: 内联公式与纯函数分叉即红)

    范围: 语料计划 26-09-21-0024 §04 第 5 步 —— 抽 group_key_of 是为了让 scripts/ 侧抓取器
    import 同一份公式; 若将来有人把 _assign_to_group 改回内联、或改了内联忘了改纯函数,
    这条会红(否则 CORPUS.group_exact 会拿"错误的期望"判"正确的实现")。
    """
    from auto_qb.core.modules.grouping_mod import group_key_of

    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = QbManager("", config=_group_cfg(state_file), no_lock=True)
        client = FakeClient()
        mgr.client = client

        # 覆盖等价类边界: 反斜杠/正斜杠混用、重复斜杠、尾斜杠有无、大小写、多文件、中文
        cases = [
            ("H1", r"R:/Downloads/TV", [("a.mkv", 100)]),
            ("H2", "R:/Downloads//TV", [("a.mkv", 100)]),  # 规范化后与 H1 同 key(重复斜杠压缩)
            ("H3", r"R:/Downloads/TV/", [("a.mkv", 100)]),  # 尾斜杠保留 -> 与 H1 不同组
            ("H4", r"r:/downloads/tv", [("a.mkv", 100)]),  # 大小写不归一 -> 与 H1 不同组
            ("H5", r"R:/Downloads/TV", [("b.mkv", 1), ("a.mkv", 2)]),  # 路径集合不同
            ("H6", r"R:/Downloads/TV", [("中文 名.mkv", 3)]),
        ]
        for h, sp, files in cases:
            client.torrents[h] = FakeTorrent(hash=h, name=h, state="stalledUP", save_path=sp)
            client.files_map[h] = [_fake_file(n, s) for n, s in files]
        mgr._refresh_torrents()

        for h, sp, files in cases:
            fmap = {n: s for n, s in files}
            assert mgr.store.member_to_key[h] == group_key_of(
                sp, fmap
            ), (f"{h}: mixin 与纯函数分叉 -> mixin={mgr.store.member_to_key[h]} "
                f"pure={group_key_of(sp, fmap)}")

        # 纯函数本身: 规范化后同 key 的成员确实落在同一组
        assert mgr.store.member_to_key["H1"] == mgr.store.member_to_key["H2"], "重复斜杠应被压缩为同组"
        assert mgr.store.member_to_key["H1"] != mgr.store.member_to_key["H3"], "尾斜杠必须 1:1 保留(不同组)"
        assert mgr.store.member_to_key["H1"] != mgr.store.member_to_key["H4"], "大小写形态必须保留(不同组)"


# ---------------- P2-a 长尾清偿 (计划 26-10-01-2157 §3 P2, 2026-10-02) ----------------


def _grp_env(state_file, **grouping_kw):
    """直驱 grouping 模块方法的白盒环境: QbManager + FakeClient, 返回 (mgr, grp, client)"""
    cfg = FakeConfig()
    cfg.state_file = state_file
    cfg.grouping = GroupingConfig(enabled=True, missing_tag="MISSING", **grouping_kw)
    mgr = QbManager("", config=cfg, no_lock=True)
    client = FakeClient()
    mgr.client = client
    return mgr, mgr.host.get("grouping"), client


def _seed_group(store, key, hashes, file_map=None, in_by_hash=None):
    """直填分组结构(in_by_hash: 只把列出的 hash 灌入 by_hash, 缺省全部)"""
    store.groups[key] = list(hashes)
    for h in hashes:
        store.member_to_key[h] = key
    store.group_sizes.setdefault(key, {})
    for h in hashes:
        store.group_sizes[key][h] = file_map or {"movie.mkv": 100}
    for h in (in_by_hash if in_by_hash is not None else hashes):
        if h not in store.by_hash:
            store.by_hash[h] = FakeTorrent(hash=h, state="stalledUP", save_path=key[0])


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


def test_grouping_size_consistency_dry_run_no_stop():
    """大小一致性: dry-run 只告警不暂停"""
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"))
        key = (r"R:/D", "k")
        _seed_group(mgr.store, key, ["H1", "H2"])
        mgr.store.group_sizes[key]["H2"] = {"movie.mkv": 999}  # 大小不一致
        grp._check_size_consistency(key, True)
        assert client.calls == [], "dry-run 不得整组暂停"


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


# ---------------- 跨组文件交叉检测 S2 (计划 26-10-04-0107 §05, 纯检测不处置, 2026-10-04) ----------------


class _CrossWarnCapture(logging.Handler):
    """直挂 grouping 模块 logger 的 WARNING 采集器

    QbManager 构造链 setup_logging 清空 root handlers, caplog.text 恒空
    (pitfalls/testing/log-capture); 对齐本文件过渡态用例的 _Capture 直挂先例。
    """
    def __init__(self):
        super().__init__(level=logging.WARNING)
        self.messages = []

    def emit(self, record):
        self.messages.append(record.getMessage())


@contextmanager
def _grab_cross_warnings():
    cap = _CrossWarnCapture()
    log = logging.getLogger("auto_qb.core.modules.grouping_mod")
    log.addHandler(cap)
    try:
        yield cap
    finally:
        log.removeHandler(cap)


def _seed_cross_pair(store, sp_a, files_a, sp_b, files_b, state_a="stalledUP", state_b="downloading", tags_a=""):
    """跨组检测夹具: 两组各 1 成员(save_path/文件清单可异同), 默认 A 完成侧 + B 下载中, 返回组对 key

    直注 store.groups / group_sizes / member_to_key / by_hash(姿势对齐 _seed_group);
    文件字典必须是 {"ep01.mkv": 100} 形状的真实清单 —— 跨组检测的展开源就是它, 空字典 = 无文件 = 检不出。
    """
    key_a = (sp_a, tuple(sorted(files_a)))
    key_b = (sp_b, tuple(sorted(files_b)))
    _seed_group(store, key_a, ["HA"], file_map=files_a, in_by_hash=[])
    _seed_group(store, key_b, ["HB"], file_map=files_b, in_by_hash=[])
    store.by_hash["HA"] = FakeTorrent(hash="HA", name="TA", state=state_a, save_path=sp_a, amount_left=100, tags=tags_a)
    store.by_hash["HB"] = FakeTorrent(hash="HB", name="TB", state=state_b, save_path=sp_b, amount_left=100)
    return key_a, key_b


_OVERLAP_A = {"ep01.mkv": 100, "ep02.mkv": 200}
_OVERLAP_B = {"ep02.mkv": 200, "ep03.mkv": 300}


def test_cross_group_partial_overlap_warns():
    """场景①部分重叠: 两组同 save_path 文件列表 [ep01,ep02]/[ep02,ep03], B 下载中
    -> 警告含 ep02 物理路径; S3 起处置生效: 涉事下载方被暂停(hash 精确断言见 S3 用例)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"), cross_group_conflict_check=True)
        _seed_cross_pair(mgr.store, td, _OVERLAP_A, td, _OVERLAP_B)
        with _grab_cross_warnings() as cap:
            grp._check_cross_group_file_conflicts(dry_run=False)
        assert any("跨组文件交叉" in m for m in cap.messages), f"部分重叠应警告: {cap.messages}"
        assert any("ep02.mkv" in m for m in cap.messages), f"消息应含重叠文件 ep02 的物理路径: {cap.messages}"
        assert client.calls.count(("stop", None)) == 1, f"S3 处置应暂停涉事下载方: {client.calls}"


@pytest.mark.skipif(os.name == "nt", reason="normcase 在 Windows 折叠大小写, 该不误报断言仅在 POSIX 成立")
def test_cross_group_case_only_posix_no_false_positive():
    """场景②POSIX 不误报: 两组文件名仅大小写不同(normcase 恒等 = 两个物理文件) -> 无警告"""
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"), cross_group_conflict_check=True)
        _seed_cross_pair(mgr.store, td, {"ep01.mkv": 100}, td, {"EP01.mkv": 100})
        with _grab_cross_warnings() as cap:
            grp._check_cross_group_file_conflicts(dry_run=False)
        assert not any("跨组文件交叉" in m for m in cap.messages), f"POSIX 大小写敏感不应误报: {cap.messages}"


@pytest.mark.skipif(os.name != "nt", reason="大小写折叠仅在 Windows 生效")
def test_cross_group_case_only_windows_detected():
    """场景②Windows 真检出: 同样大小写数据, normcase 折叠为同一物理文件 -> 警告(与 POSIX 用例分开断言, 不按平台分支期望)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"), cross_group_conflict_check=True)
        _seed_cross_pair(mgr.store, td, {"ep01.mkv": 100}, td, {"EP01.mkv": 100})
        with _grab_cross_warnings() as cap:
            grp._check_cross_group_file_conflicts(dry_run=False)
        assert any("跨组文件交叉" in m for m in cap.messages), f"Windows 大小写折叠应检出交叉: {cap.messages}"
        assert client.calls.count(("stop", None)) == 1, f"S3 处置应暂停涉事下载方: {client.calls}"


@pytest.mark.skipif(os.name != "nt", reason="junction 仅 Windows(目录 symlink 需开发者模式, 不测)")
def test_cross_group_junction_alias_detected():
    """场景③junction 别名: 两组 save_path 分别指向真身与 junction, realpath_lexical 归同 -> 警告"""
    import _winapi  # CPython 标准库内部 API(测试套同款), 无需管理员权限; 平台用例体内导入, POSIX 收集不触

    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"), cross_group_conflict_check=True)
        link = os.path.join(td, "link")
        _winapi.CreateJunction(td, link)  # 造 junction: link -> td 真身
        try:
            _seed_cross_pair(mgr.store, td, {"movie.mkv": 100}, link, {"movie.mkv": 100})
            with _grab_cross_warnings() as cap:
                grp._check_cross_group_file_conflicts(dry_run=False)
            assert any("跨组文件交叉" in m for m in cap.messages), f"junction 别名归同后应检出: {cap.messages}"
            assert client.calls.count(("stop", None)) == 1, f"S3 处置应暂停涉事下载方: {client.calls}"
        finally:
            os.rmdir(link)  # 先摘 junction 再交还 TemporaryDirectory 清理(防 rmtree 循环进入真身)


def test_cross_group_missing_tag_exempt():
    """D3 MISSING 豁免: 任一侧成员带 missing_tag -> 豁免该事件无警告; 去标签后照常检出(对照)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"), cross_group_conflict_check=True)
        _seed_cross_pair(mgr.store, td, _OVERLAP_A, td, _OVERLAP_B, tags_a="MISSING")
        with _grab_cross_warnings() as cap:
            grp._check_cross_group_file_conflicts(dry_run=False)
        assert not any("跨组文件交叉" in m for m in cap.messages), f"MISSING 侧重下补救合法, 应豁免: {cap.messages}"
        mgr.store.by_hash["HA"].tags = ""
        with _grab_cross_warnings() as cap:
            grp._check_cross_group_file_conflicts(dry_run=False)
        assert any("跨组文件交叉" in m for m in cap.messages), "豁免解除后应照常检出"


def test_cross_group_zero_change_short_circuit():
    """零变化短路: rounds_applied>0 且 dirty_groups 空 -> 提前返回无警告; dirty 非空恢复全量(对照)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"), cross_group_conflict_check=True)
        key_a, _key_b = _seed_cross_pair(mgr.store, td, _OVERLAP_A, td, _OVERLAP_B)
        mgr.store.rounds_applied = 1  # 增量基线已建立
        with _grab_cross_warnings() as cap:
            grp._check_cross_group_file_conflicts(dry_run=False)
        assert not any("跨组文件交叉" in m for m in cap.messages), "增量轮零变化应提前返回"
        mgr.store.dirty_groups.add(key_a)  # 变化登记 -> 恢复全量扫描
        with _grab_cross_warnings() as cap:
            grp._check_cross_group_file_conflicts(dry_run=False)
        assert any("跨组文件交叉" in m for m in cap.messages), "dirty 非空应恢复全量并检出"
        assert key_a in mgr.store.dirty_groups, "dirty_groups 只读不复位(消费单点仍是同组检查)"


def test_cross_group_switch_off_silent():
    """开关缺省 false(保守默认): 交叉数据在场仍零输出零动作; 打开后照常检出(对照, 证明确实是开关拦的)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"))  # cross_group_conflict_check 缺省 false
        _seed_cross_pair(mgr.store, td, _OVERLAP_A, td, _OVERLAP_B)
        with _grab_cross_warnings() as cap:
            grp._check_cross_group_file_conflicts(dry_run=False)
        assert not any("跨组文件交叉" in m for m in cap.messages), "开关关闭应零输出"
        assert client.calls == [], "开关关闭应零动作"
        mgr.config.grouping.cross_group_conflict_check = True
        with _grab_cross_warnings() as cap:
            grp._check_cross_group_file_conflicts(dry_run=False)
        assert any("跨组文件交叉" in m for m in cap.messages), "开关打开后同数据应检出"


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


# ---------------- 跨组文件交叉检测 S3 (计划 26-10-04-0107 §05, 处置: 暂停 + 去重 + 消除, 2026-10-04) ----------------
# 暂停断言一律 mock api.torrents_stop: 真实 stop 经 _sync_paused_state 同 tick 改写 store 快照,
# 把「下载中」谓词打掉、污染去重断言(对齐 :472 同组四段式先例的注释口径)


def test_cross_group_dispose_stops_downloader():
    """S3 触发处置: 两组交叉 + B 下载中 -> 暂停仅涉事下载方(hash 精确, 不含完成侧); 组对入去重集合"""
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"), cross_group_conflict_check=True)
        key_a, key_b = _seed_cross_pair(mgr.store, td, _OVERLAP_A, td, _OVERLAP_B)
        pair = tuple(sorted((key_a, key_b), key=str))  # 组对规范序(与去重集合元素同形)
        # mock 掉 api.torrents_stop: QbApi 的 stop 会经 _sync_paused_state 同 tick 改写 store 快照,
        # 污染去重断言(真实场景下轮 refresh 才校准)
        with mock.patch.object(mgr.api, "torrents_stop") as stop_mock:
            grp._check_cross_group_file_conflicts(dry_run=False)
            assert stop_mock.call_count == 1, f"交叉在场应暂停涉事下载方: {stop_mock.call_count}"
            assert stop_mock.call_args.kwargs["torrent_hashes"] == ["HB"], "只停下载方 HB, 不含完成侧"
            assert pair in mgr.store.cross_group_conflict_warned, f"组对应登记去重: {mgr.store.cross_group_conflict_warned}"


def test_cross_group_dispose_dedup_no_repeat():
    """S3 去重门: 冲突持续不重复警告/暂停(暂停幂等), 再跑一轮 stop 仍只 1 次"""
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"), cross_group_conflict_check=True)
        _seed_cross_pair(mgr.store, td, _OVERLAP_A, td, _OVERLAP_B)
        # mock 掉 api.torrents_stop: QbApi 的 stop 会经 _sync_paused_state 同 tick 改写 store 快照,
        # 污染去重断言(真实场景下轮 refresh 才校准)
        with mock.patch.object(mgr.api, "torrents_stop") as stop_mock:
            grp._check_cross_group_file_conflicts(dry_run=False)
            assert stop_mock.call_count == 1
            grp._check_cross_group_file_conflicts(dry_run=False)
            assert stop_mock.call_count == 1, f"冲突持续不应重复暂停: {stop_mock.call_count}"


def test_cross_group_dispose_clear_and_retrigger():
    """S3 消除+重现(四段式, 对齐同组检查先例): 下载方转暂停 -> 组对失活去重清除且 stop 不增; 恢复下载 -> 再次触发"""
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"), cross_group_conflict_check=True)
        key_a, key_b = _seed_cross_pair(mgr.store, td, _OVERLAP_A, td, _OVERLAP_B)
        pair = tuple(sorted((key_a, key_b), key=str))
        # mock 掉 api.torrents_stop: QbApi 的 stop 会经 _sync_paused_state 同 tick 改写 store 快照,
        # 污染去重断言(真实场景下轮 refresh 才校准)
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


def test_cross_group_dispose_seeder_side_untouched():
    """S3/D2 红线: stop 名单只含下载中成员, 完成侧/做种成员绝不混入(组 A 含两个做种成员仍只停 HB)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"), cross_group_conflict_check=True)
        key_a, key_b = _seed_cross_pair(mgr.store, td, _OVERLAP_A, td, _OVERLAP_B)
        # 组 A 补第二个做种成员: 证明 stop 名单不随组员扩散(只按下载中谓词取)
        mgr.store.by_hash["HA2"] = FakeTorrent(hash="HA2", name="TA2", state="stalledUP", save_path=td, amount_left=0)
        mgr.store.groups[key_a].append("HA2")
        mgr.store.member_to_key["HA2"] = key_a
        mgr.store.group_sizes[key_a]["HA2"] = dict(_OVERLAP_A)
        # mock 掉 api.torrents_stop: QbApi 的 stop 会经 _sync_paused_state 同 tick 改写 store 快照,
        # 污染去重断言(真实场景下轮 refresh 才校准)
        with mock.patch.object(mgr.api, "torrents_stop") as stop_mock:
            grp._check_cross_group_file_conflicts(dry_run=False)
            assert stop_mock.call_count == 1, f"应只调一次 stop: {stop_mock.call_count}"
            hashes = stop_mock.call_args.kwargs["torrent_hashes"]
            assert set(hashes) == {"HB"}, f"stop 名单应只含下载方: {hashes}"
            assert "HA" not in hashes and "HA2" not in hashes, f"完成/做种侧不得混入: {hashes}"


def test_cross_group_dispose_dry_run_only_warns():
    """S3 dry-run(风险4): 警告照发, 但不暂停、不记去重 —— 下次真实执行仍会触发处置"""
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"), cross_group_conflict_check=True)
        _seed_cross_pair(mgr.store, td, _OVERLAP_A, td, _OVERLAP_B)
        # mock 掉 api.torrents_stop: QbApi 的 stop 会经 _sync_paused_state 同 tick 改写 store 快照,
        # 污染去重断言(真实场景下轮 refresh 才校准)
        with mock.patch.object(mgr.api, "torrents_stop") as stop_mock:
            with _grab_cross_warnings() as cap:
                grp._check_cross_group_file_conflicts(dry_run=True)
            assert any("跨组文件交叉" in m for m in cap.messages), f"dry-run 警告应照发: {cap.messages}"
            assert stop_mock.call_count == 0, f"dry-run 不得暂停: {stop_mock.call_count}"
            assert mgr.store.cross_group_conflict_warned == set(), "dry-run 不得记去重"


def test_cross_group_reset_runtime_keeps_warned():
    """S3 reset_runtime 续用(决策钉死): 热重载不清跨组去重集合 —— 组 key 纯函数派生, 旧条目语义仍成立"""
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"), cross_group_conflict_check=True)
        _seed_cross_pair(mgr.store, td, _OVERLAP_A, td, _OVERLAP_B)
        # mock 掉 api.torrents_stop: QbApi 的 stop 会经 _sync_paused_state 同 tick 改写 store 快照,
        # 污染去重断言(真实场景下轮 refresh 才校准)
        with mock.patch.object(mgr.api, "torrents_stop"):
            grp._check_cross_group_file_conflicts(dry_run=False)
        assert len(mgr.store.cross_group_conflict_warned) == 1, "前置: 处置已登记去重"
        mgr.store.reset_runtime()
        assert len(mgr.store.cross_group_conflict_warned
                  ) == 1, (f"reset_runtime 有意不清该集合(见 reset_runtime 注释): {mgr.store.cross_group_conflict_warned}")


def test_cross_group_single_side_dirty_still_detected():
    """S3/风险2: 单侧脏(dirty 仅含组 A, 交叉对象组 B 静止干净)仍全量检出并暂停 —— 跨组检测不做按组增量"""
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"), cross_group_conflict_check=True)
        key_a, _key_b = _seed_cross_pair(mgr.store, td, _OVERLAP_A, td, _OVERLAP_B)
        mgr.store.rounds_applied = 1  # 增量基线已建立: 若误按 dirty 增量, 组 B 侧交叉将漏检
        mgr.store.dirty_groups.add(key_a)
        # mock 掉 api.torrents_stop: QbApi 的 stop 会经 _sync_paused_state 同 tick 改写 store 快照,
        # 污染去重断言(真实场景下轮 refresh 才校准)
        with mock.patch.object(mgr.api, "torrents_stop") as stop_mock:
            with _grab_cross_warnings() as cap:
                grp._check_cross_group_file_conflicts(dry_run=False)
            assert any("跨组文件交叉" in m for m in cap.messages), f"单侧脏仍应检出交叉: {cap.messages}"
            assert stop_mock.call_count == 1, f"检出即处置: {stop_mock.call_count}"
            assert stop_mock.call_args.kwargs["torrent_hashes"] == ["HB"], "只停下载方 HB"
            assert key_a in mgr.store.dirty_groups, "dirty_groups 只读不复位(消费单点仍是同组检查)"
