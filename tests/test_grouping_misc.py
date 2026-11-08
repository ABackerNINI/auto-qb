"""test_grouping_misc 测试计划: 种子分组

## 测试计划(每个测试函数一条)
- test_group_reference_candidates: 返回做种成员作为参考候选
- test_grouping_errored_files_intact_no_action: errored 转换但磁盘文件齐全 -> 无动作(保守)
- test_grouping_errored_whole_group_representative: 全组同时 errored -> errored 成员作代表仍能扫描暂停 + MISSING
- test_grouping_errored_check_disabled: check_missing_files=False -> errored 转换不触发
- test_group_key_of_is_single_source_of_truth: 归组 key 纯函数 group_key_of 与真实 mixin 输出一致(语料计划 §04 守阵)
- test_grouping_size_consistency_dry_run_no_stop: 大小一致性 dry-run 只告警 (P2-a)
- test_cross_group_partial_overlap_warns: 场景1部分重叠 -> 警告含重叠文件物理路径; S3 起处置生效 (26-10-04-0107 S2/S3)
- test_cross_group_case_only_posix_no_false_positive: 场景2POSIX normcase 恒等 -> 大小写不同不误报 (26-10-04-0107 S2)
- test_cross_group_case_only_windows_detected: 场景2Windows normcase 折叠 -> 大小写交叉检出 (26-10-04-0107 S2)
- test_cross_group_junction_alias_detected: 场景3junction 别名目录 realpath_lexical 归同 -> 检出 (26-10-04-0107 S2)
- test_cross_group_missing_tag_exempt: D3 任一侧成员带 MISSING 标签豁免, 去标签后照常检出 (26-10-04-0107 S2)
- test_cross_group_zero_change_short_circuit: rounds_applied>0 且 dirty 空 -> 提前返回; dirty 非空恢复全量 (26-10-04-0107 S2)
- test_cross_group_switch_off_silent: 开关缺省 false -> 交叉在场仍零输出零动作, 打开后检出 (26-10-04-0107 S2)
- test_cross_group_dispose_stops_downloader: S3 触发处置: 交叉在场 -> 仅暂停涉事下载方(hash 精确, 不含完成侧), 组对入去重 (26-10-04-0107 S3)
- test_cross_group_dispose_dedup_no_repeat: S3 去重门: 冲突持续不重复警告/暂停(暂停幂等) (26-10-04-0107 S3)
- test_cross_group_dispose_seeder_side_untouched: S3/D2: stop 名单只含下载方, 无完成/做种成员混入 (26-10-04-0107 S3)
- test_cross_group_dispose_dry_run_only_warns: S3 dry-run: 警告在, 不暂停, 不记去重 (26-10-04-0107 S3)
- test_cross_group_reset_runtime_keeps_warned: S3 reset_runtime 有意不清跨组去重集合(决策钉死, 防后人顺手加 clear) (26-10-04-0107 S3)
- test_cross_group_single_side_dirty_still_detected: S3/风险2: 单侧脏(dirty 仅含组 A)仍全量检出并暂停 (26-10-04-0107 S3)
- test_guard_ck5_cross_physical_key_needs_dir_prefix: 物理键丢目录前缀 -> 不同组同名相对路径误判同物理路径(W9a ck5 高危)
- test_guard_size_consistency_stop_scope_and_warning: 大小一致性暂停名单=组内成员精确列表(cs17 高危 None=全库) + 警告文案在(cs12/15) + dry-run 缺省不可达(ag40)
- test_guard_dry_run_transitions_no_side_effect: transitions 相位 dry-run 会话零真实副作用(tr2/3/5/7/8)
- test_guard_dry_run_torrents_added_no_side_effect: torrents_added 相位 dry-run 零真实副作用(ta3/5/8/10/12/13+an8/11)
- test_guard_dry_run_post_no_side_effect: post 相位 dry-run 零真实副作用(po2/3/5/7/8/10/12+sp43/46/56)
- test_guard_content_root_flat: 单文件平铺种子内容根=save_path 本身(cr18 平铺早退丢失)
- test_guard_content_root_nested_first_segment: 嵌套内容根取首段(cr30 rsplit/cr35 恒 join)
- test_guard_within_scope_contract: 作用域判定契约(含等于/子路径/尾斜杠 scope/POSIX 绝对路径)(ws1/3/9/10/14)
- test_guard_syscall_path_mapping: 容器映射命中必须返回映射路径(sy2 映射丢失)
- test_guard_third_party_link_probe_and_discard: 第三方链接探测对象=代表文件(mk20)+判非链接必须消除标记(mk35)
- test_guard_sections_pin_grouping: sections 认领段名 pin(sec1/sec2 双杀)
- test_guard_cross_group_active_side_detected: 跨组交叉 ka 侧下载方必须检出(x76 激活半丢)
- test_guard_cross_group_missing_exempt: kb 位 MISSING 组豁免不得误停补救下载方(x72)
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
    _seed_cross_pair,
    _seed_group,
)


def test_group_reference_candidates():
    """_group_reference_candidates: 组内已完成且未在校验的成员(参考种子候选, 读 store 快照)"""
    mgr = make_manager("state.json", bare=True, grouping=grouping_cfg())
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


def test_grouping_errored_files_intact_no_action():
    """errored 转换但磁盘文件齐全(非缺文件的 error)-> 扫描确认后无任何动作(保守)"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        client = FakeClient()
        mgr = make_manager(state_file, bare=True, grouping=grouping_cfg(), client=client)

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
        client = FakeClient()
        mgr = make_manager(state_file, bare=True, grouping=grouping_cfg(), client=client)

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
        client = FakeClient()
        mgr = make_manager(state_file, bare=True, grouping=grouping_cfg(check_missing_files=False), client=client)

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


def test_group_key_of_is_single_source_of_truth():
    """归组 key 纯函数与真实 mixin 输出一致(守阵: 内联公式与纯函数分叉即红)

    范围: 语料计划 26-09-21-0024 §04 第 5 步 —— 抽 group_key_of 是为了让 scripts/ 侧抓取器
    import 同一份公式; 若将来有人把 _assign_to_group 改回内联、或改了内联忘了改纯函数,
    这条会红(否则 CORPUS.group_exact 会拿"错误的期望"判"正确的实现")。
    """
    from auto_qb.core.modules.grouping_mod import group_key_of

    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        client = FakeClient()
        mgr = make_manager(state_file, bare=True, grouping=grouping_cfg(), client=client)

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


def test_grouping_size_consistency_dry_run_no_stop():
    """大小一致性: dry-run 只告警不暂停"""
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"))
        key = (r"R:/D", "k")
        _seed_group(mgr.store, key, ["H1", "H2"])
        mgr.store.group_sizes[key]["H2"] = {"movie.mkv": 999}  # 大小不一致
        grp._check_size_consistency(key, True)
        assert client.calls == [], "dry-run 不得整组暂停"


def test_cross_group_partial_overlap_warns():
    """场景1部分重叠: 两组同 save_path 文件列表 [ep01,ep02]/[ep02,ep03], B 下载中
    -> 警告含 ep02 物理路径; S3 起处置生效: 涉事下载方被暂停(hash 精确断言见 S3 用例)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"), cross_group_conflict_check=True)
        _seed_cross_pair(mgr.store, td, _OVERLAP_A, td, _OVERLAP_B)
        with _grab_cross_warnings() as cap:
            grp._check_cross_group_file_conflicts(dry_run=False)
        assert any("跨组文件交叉" in m for m in cap.messages), f"部分重叠应警告: {cap.messages}"
        assert any("ep02.mkv" in m for m in cap.messages), f"消息应含重叠文件 ep02 的物理路径: {cap.messages}"
        assert client.calls.count(("stop", None)) == 1, f"S3 处置应暂停涉事下载方: {client.calls}"


@pytest.mark.skipif(os.name == "nt", reason="normcase 在 Windows 折叠大小写, 该不误报断言仅在 POSIX 成立")  # owner: abacker
def test_cross_group_case_only_posix_no_false_positive():
    """场景2POSIX 不误报: 两组文件名仅大小写不同(normcase 恒等 = 两个物理文件) -> 无警告"""
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"), cross_group_conflict_check=True)
        _seed_cross_pair(mgr.store, td, {"ep01.mkv": 100}, td, {"EP01.mkv": 100})
        with _grab_cross_warnings() as cap:
            grp._check_cross_group_file_conflicts(dry_run=False)
        assert not any("跨组文件交叉" in m for m in cap.messages), f"POSIX 大小写敏感不应误报: {cap.messages}"


@pytest.mark.skipif(os.name != "nt", reason="大小写折叠仅在 Windows 生效")  # owner: abacker
def test_cross_group_case_only_windows_detected():
    """场景2Windows 真检出: 同样大小写数据, normcase 折叠为同一物理文件 -> 警告(与 POSIX 用例分开断言, 不按平台分支期望)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"), cross_group_conflict_check=True)
        _seed_cross_pair(mgr.store, td, {"ep01.mkv": 100}, td, {"EP01.mkv": 100})
        with _grab_cross_warnings() as cap:
            grp._check_cross_group_file_conflicts(dry_run=False)
        assert any("跨组文件交叉" in m for m in cap.messages), f"Windows 大小写折叠应检出交叉: {cap.messages}"
        assert client.calls.count(("stop", None)) == 1, f"S3 处置应暂停涉事下载方: {client.calls}"


@pytest.mark.skipif(os.name != "nt", reason="junction 仅 Windows(目录 symlink 需开发者模式, 不测)")  # owner: abacker
def test_cross_group_junction_alias_detected():
    """场景3junction 别名: 两组 save_path 分别指向真身与 junction, realpath_lexical 归同 -> 警告"""
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


def test_cross_group_dispose_stops_downloader():
    """S3 触发处置: 两组交叉 + B 下载中 -> 暂停仅涉事下载方(hash 精确, 不含完成侧); 组对入去重集合"""
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"), cross_group_conflict_check=True)
        key_a, key_b = _seed_cross_pair(mgr.store, td, _OVERLAP_A, td, _OVERLAP_B)
        pair = tuple(sorted((key_a, key_b), key=str))  # 组对规范序(与去重集合元素同形)
        # mock 掉 api.torrents_stop: 用于断言调用参数/作用范围, 并隔离替身的客户端侧翻转
        # (S0-P3)。!A 系 26-10-13-0540 S1 起真实 stop **不再**回写 store 快照,
        # 原「同 tick 改写快照污染去重断言」的顾虑已随 _sync_paused_state 删除而消失
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
        # mock 掉 api.torrents_stop: 用于断言调用参数/作用范围, 并隔离替身的客户端侧翻转
        # (S0-P3)。!A 系 26-10-13-0540 S1 起真实 stop **不再**回写 store 快照,
        # 原「同 tick 改写快照污染去重断言」的顾虑已随 _sync_paused_state 删除而消失
        with mock.patch.object(mgr.api, "torrents_stop") as stop_mock:
            grp._check_cross_group_file_conflicts(dry_run=False)
            assert stop_mock.call_count == 1
            grp._check_cross_group_file_conflicts(dry_run=False)
            assert stop_mock.call_count == 1, f"冲突持续不应重复暂停: {stop_mock.call_count}"


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
        # mock 掉 api.torrents_stop: 用于断言调用参数/作用范围, 并隔离替身的客户端侧翻转
        # (S0-P3)。!A 系 26-10-13-0540 S1 起真实 stop **不再**回写 store 快照,
        # 原「同 tick 改写快照污染去重断言」的顾虑已随 _sync_paused_state 删除而消失
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
        # mock 掉 api.torrents_stop: 用于断言调用参数/作用范围, 并隔离替身的客户端侧翻转
        # (S0-P3)。!A 系 26-10-13-0540 S1 起真实 stop **不再**回写 store 快照,
        # 原「同 tick 改写快照污染去重断言」的顾虑已随 _sync_paused_state 删除而消失
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
        # mock 掉 api.torrents_stop: 用于断言调用参数/作用范围, 并隔离替身的客户端侧翻转
        # (S0-P3)。!A 系 26-10-13-0540 S1 起真实 stop **不再**回写 store 快照,
        # 原「同 tick 改写快照污染去重断言」的顾虑已随 _sync_paused_state 删除而消失
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
        # mock 掉 api.torrents_stop: 用于断言调用参数/作用范围, 并隔离替身的客户端侧翻转
        # (S0-P3)。!A 系 26-10-13-0540 S1 起真实 stop **不再**回写 store 快照,
        # 原「同 tick 改写快照污染去重断言」的顾虑已随 _sync_paused_state 删除而消失
        with mock.patch.object(mgr.api, "torrents_stop") as stop_mock:
            with _grab_cross_warnings() as cap:
                grp._check_cross_group_file_conflicts(dry_run=False)
            assert any("跨组文件交叉" in m for m in cap.messages), f"单侧脏仍应检出交叉: {cap.messages}"
            assert stop_mock.call_count == 1, f"检出即处置: {stop_mock.call_count}"
            assert stop_mock.call_args.kwargs["torrent_hashes"] == ["HB"], "只停下载方 HB"
            assert key_a in mgr.store.dirty_groups, "dirty_groups 只读不复位(消费单点仍是同组检查)"


def test_guard_ck5_cross_physical_key_needs_dir_prefix():
    """守阵(W9a ck5 高危): 物理键必须含目录前缀 —— 不同组共享常见相对路径(同名剧集文件)
    不得因键丢目录前缀被误判「同一物理路径」(误警告+误停无辜组下载方)"""
    from auto_qb.core.modules.grouping_mod import _cross_physical_key

    k_a = _cross_physical_key(r"R:\GroupA", "poster.jpg")
    k_b = _cross_physical_key(r"R:\GroupB", "poster.jpg")
    assert k_a != k_b, f"不同目录的同名相对路径必须是不同物理键: {k_a!r} vs {k_b!r}"
    assert k_a == _cross_physical_key(r"R:\GroupA", "poster.jpg"), "同输入物理键必须稳定"
    k_c = _cross_physical_key(r"R:\GroupA", "sub\\poster.jpg")
    assert k_c != k_a, "不同相对路径不得折叠成同键"


def test_guard_size_consistency_stop_scope_and_warning():
    """守阵(W9a cs17 高危 + cs12/cs15 + ag40): 大小一致性暂停名单必须是组内成员精确列表
    (torrents_stop(torrent_hashes=None) 在 qbittorrent-api 语义 = 暂停全库, 灾难面);
    警告必须含成员清单(审计日志丢真=低钉面); dry-run 缺省路径不暂停"""
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"), check_missing_files=False)
        stops = _record_stop_scope(client)
        key = ("R:/Downloads", ("movie.mkv", ))  # 重归组键首元经 path_normalize(正斜杠), 必须同形
        _seed_group(mgr.store, key, ["H1", "H2"])
        mgr.store.by_hash["H1"].name = "T1"
        mgr.store.by_hash["H2"].name = "T2"
        mgr.store.group_sizes[key]["H2"] = {"movie.mkv": 200}  # 与 H1 同名不同大小
        with capture_logs("auto_qb.core.modules.grouping_mod") as cap:
            grp._check_size_consistency(key, False)
        assert stops == [["H1", "H2"]], f"暂停名单必须是成员精确列表(不得 None=全库): {stops}"
        assert "文件大小不一致" in cap.text and "T1" in cap.text and "T2" in cap.text, \
            f"警告不得丢失且须含成员清单: {cap.messages}"
        # dry-run 缺省路径: 归组重入(同键) + dry_run=True -> 不得真实暂停
        stops.clear()
        grp._assign_to_group(mgr.store.by_hash["H2"], {"movie.mkv": 300}, True)
        assert stops == [], f"dry_run=True 不得真实暂停(缺省击穿即红): {stops}"


def test_guard_dry_run_transitions_no_side_effect():
    """守阵(W9a tr2/tr3/tr5/tr7/tr8): transitions 相位 dry-run 会话零真实副作用 ——
    payload 恒带 dry_run 键, 键名/键位/传参任一变异都会让缺文件处置真实落库"""
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"))
        stops = _record_stop_scope(client)
        key = (r"R:\Downloads", ("movie.mkv", ))
        _seed_group(mgr.store, key, ["H1", "H2"])
        mgr.store.state_snapshot = {"H1": FakeTorrent(state="stalledUP").state_enum}
        mgr.store.state_changed = [("H1", FakeTorrent(state="pausedUP").state_enum)]
        grp._on_transitions(SimpleNamespace(payload={"dry_run": True}))
        assert stops == [], f"dry-run transitions 相位不得真实暂停(击穿即红): {stops}"


def test_guard_dry_run_torrents_added_no_side_effect():
    """守阵(W9a ta3/ta5/ta8/ta10/ta12/ta13 + an8/an11): torrents_added 相位 dry-run 会话零真实副作用 ——
    新种子归组仍发生(分组视图), 但大小一致性暂停必须被 dry-run 闸挡住"""
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"))
        stops = _record_stop_scope(client)
        key = ("R:/Downloads", ("movie.mkv", ))  # 重归组键首元经 path_normalize(正斜杠), 必须同形
        _seed_group(mgr.store, key, ["H1"], file_map={"movie.mkv": 100})
        client.files_map["H2"] = [_fake_file("movie.mkv", 200)]  # 同名不同大小 -> 触发大小一致性
        mgr.store.by_hash["H2"] = FakeTorrent(hash="H2", state="stalledUP", save_path="R:/Downloads")
        grp._on_torrents_added(SimpleNamespace(payload={"hash": "H2", "dry_run": True}))
        assert stops == [], f"dry-run 归组不得真实暂停大小不一致组(击穿即红): {stops}"
        assert mgr.store.member_to_key.get("H2") == key, "dry-run 只挡外部动作, 归组本身必须发生"


def test_guard_dry_run_post_no_side_effect():
    """守阵(W9a po2/po3/po5/po7/po8/po10/po12 + sp43/sp46/sp56): post 相位 dry-run 会话零真实副作用 ——
    保存路径重归组(大小一致性)/缺文件扫描/下载冲突三面的外部动作全部只报告"""
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"))
        stops = _record_stop_scope(client)
        k1 = ("R:/Downloads", ("movie.mkv", ))  # 重归组键首元经 path_normalize(正斜杠), 必须同形
        _seed_group(mgr.store, k1, ["H1", "H2"])
        mgr.store.by_hash["H1"] = FakeTorrent(hash="H1", state="stalledDL", progress=0.0, downloaded=0)
        k2 = ("R:/Downloads2", ("movie.mkv", ))
        _seed_group(mgr.store, k2, ["H3"], file_map={"movie.mkv": 100})
        mgr.store.by_hash["H1"].save_path = "R:/Downloads2"
        mgr.store.group_sizes[k1]["H1"] = {"movie.mkv": 200}  # H1 缓存映射(与 H3 不同大小)
        mgr.store.delta_fields = {"H1": {"save_path"}}
        grp._on_post(SimpleNamespace(payload={"dry_run": True}))
        assert stops == [], f"dry-run post 相位不得真实暂停(三面任一击穿即红): {stops}"
        assert mgr.store.member_to_key["H1"] == k2, "dry-run 只挡外部动作, 重归组本身必须发生"


def test_guard_content_root_flat():
    """守阵(W9a cr18): 单文件平铺种子(常态)内容根 = save_path 本身 —— or→and 吞掉「全平铺早退」
    会让内容根塌成 save_path/文件名, 组键物理解析失真(组裂)"""
    from auto_qb.core.modules.grouping_mod import _content_root_of

    assert _content_root_of("R:/D", ["movie.mkv"]) == "R:/D", "平铺单文件必须早退返回 save_path"
    assert _content_root_of("R:/D", ["/movie.mkv"]) == "R:/D", "首斜杠包裹的平铺文件名归一后仍须早退"
    assert _content_root_of("R:/D", []) == "R:/D", "空文件表同样早退"
    assert _content_root_of("", ["a.mkv"]) == "", "空 save_path 同样早退"


def test_guard_content_root_nested_first_segment():
    """守阵(W9a cr30/cr35): 嵌套内容根 = save_path/唯一顶层段; 多顶层段回退 save_path ——
    rsplit 取末段/恒走 join 都会让目录别名作用域断裂"""
    from auto_qb.core.modules.grouping_mod import _content_root_of

    assert _content_root_of("R:/D", ["sub/deep/a.mkv", "sub/deep/b.mkv"]) == os.path.join("R:/D", "sub"), \
        "唯一顶层段必须是首段(不是末段, 二层嵌套区分 split/rsplit)"
    assert _content_root_of("R:/D", ["sub\\deep\\a.mkv", "sub\\deep\\b.mkv"]) == os.path.join("R:/D", "sub"), \
        "反斜杠文件名必须归一为正斜杠后再判顶层段"
    assert _content_root_of("R:/D", ["/sub/deep/a.mkv", "sub/deep/b.mkv"]) == os.path.join("R:/D", "sub"), \
        "首尾斜杠剥离后同顶层段必须合并(不剥离会裂成空首段)"
    assert _content_root_of("R:/D", ["/sub/a.mkv", ""]) == os.path.join("R:/D", "sub"), \
        "空文件名段必须在归一阶段被过滤(否则顶层段集合被空串污染而回退)"
    assert _content_root_of("R:/D", ["a/x.mkv", "b/y.mkv"]) == "R:/D", "多顶层段必须回退 save_path"


def test_guard_within_scope_contract():
    """守阵(W9a ws1/ws3/ws9/ws10/ws14): 作用域判定契约 —— 含等于/子路径/尾斜杠 scope 归一/
    POSIX 绝对路径; 塌成恒 False 或仅全等都会让重归组组裂"""
    from auto_qb.core.modules.grouping_mod import _within_scope

    assert _within_scope("R:/D", "R:/D") is True, "scope 等于自身必须在域内"
    assert _within_scope("R:/D", "R:/D/sub/f.mkv") is True, "子路径必须在域内"
    assert _within_scope("R:/D", "R:/Other/f.mkv") is False, "域外必须为 False"
    assert _within_scope("R:/D/", "R:/D/x") is True, "尾斜杠 scope 归一后必须在域内"
    assert _within_scope("/data", "/data/sub") is True, "POSIX 绝对路径 scope 必须真"
    assert _within_scope("/data", "/database") is False, "前缀串撞车不得误判在域内"
    assert _within_scope("", "/data") is False, "空 scope 不得因空判据而误判在域内"
    assert _within_scope("", "") is False, "空 scope 与空路径同样不得判在域内"


def test_guard_syscall_path_mapping(monkeypatch):
    """守阵(W9a sy2 + pd26/pd27): 容器映射命中必须返回映射后的 syscall 路径 ——
    `or path→and path` 会把映射丢掉, 第 2 层别名识别全灭"""
    from auto_qb.core.modules import grouping_mod

    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"))
        sp = "R:/D/movie"
        monkeypatch.setattr(grp._ctx, "relocate", None)
        monkeypatch.setattr(
            grouping_mod.file_access,
            "get_file_access",
            lambda: SimpleNamespace(
                map_to_container=lambda p: "C:/mapped" if p == sp else p,
                realpath_lexical=lambda p: "T:/lib/movie" if p == sp else (_ for _ in ()).throw(OSError()),
            ),
        )
        monkeypatch.setattr(
            grouping_mod.alias_fs,
            "alias_kind_of",
            lambda p: grouping_mod.alias_fs.KIND_JUNCTION if p == "C:/mapped" else None,
        )
        assert grp._syscall_path(sp) == "C:/mapped", "映射命中必须返回映射路径"
        assert grp._physical_dir(sp, sp) == "T:/lib/movie", "映射后的路径必须参与别名判定"


def test_guard_third_party_link_probe_and_discard(monkeypatch):
    """守阵(W9a mk20/mk35): 第三方链接探测对象必须是 save_path+代表文件(不得漂成目录);
    判非链接时必须消除旧标记(标记只增不减 = 误拒迁状态泄漏)"""
    from auto_qb.core.modules import grouping_mod

    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"), check_missing_files=False)
        key = ("T:/x", ("movie.mkv", ))
        monkeypatch.setattr(
            grouping_mod.file_access,
            "get_file_access",
            lambda: SimpleNamespace(map_to_container=lambda p: p),
        )
        monkeypatch.setattr(
            grouping_mod.alias_fs,
            "alias_kind_of",
            lambda p: grouping_mod.alias_fs.KIND_SYMLINK if p.endswith("movie.mkv") else None,
        )
        grp._mark_third_party_link(key, "R:/D", {"movie.mkv": 100})
        assert key in mgr.store.third_party_link_groups, "文件级链接代表种必须打标"
        monkeypatch.setattr(grouping_mod.alias_fs, "alias_kind_of", lambda p: None)
        grp._mark_third_party_link(key, "R:/D", {"movie.mkv": 100})
        assert key not in mgr.store.third_party_link_groups, "判非链接必须消除旧标记"


def test_guard_sections_pin_grouping():
    """守阵(W9a grouping sec1/sec2, no tests 记账): 配置段认领名 pin —— 认领错位会让
    grouping 段成孤儿段(热重载/配置认领面)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"))
        assert grp.sections() == ("grouping", )


def test_guard_cross_group_active_side_detected():
    """守阵(W9a x76): 跨组交叉激活判定两半必须都在 —— ka(规范序前位)下载中而 kb 静态时
    不得漏检(下载方继续覆盖他组数据)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"), cross_group_conflict_check=True)
        stops = _record_stop_scope(client)
        _seed_cross_pair(mgr.store, td, _OVERLAP_A, td, _OVERLAP_B, state_a="downloading", state_b="stalledUP")
        grp._check_cross_group_file_conflicts(dry_run=False)
        assert stops == [["HA"]], f"ka 侧下载方必须被检出并暂停(激活半丢即红): {stops}"


def test_guard_cross_group_missing_exempt():
    """守阵(W9a x72): D3 豁免两半都必须生效 —— MISSING 组在 kb 位时, ka 侧重新下载属合法补救,
    不得被误判激活而误停"""
    with tempfile.TemporaryDirectory() as td:
        mgr, grp, client = _grp_env(os.path.join(td, "state.json"), cross_group_conflict_check=True)
        stops = _record_stop_scope(client)
        _seed_cross_pair(mgr.store, td, _OVERLAP_A, td, _OVERLAP_B, state_a="downloading", state_b="stalledUP")
        mgr.store.by_hash["HB"].tags = "MISSING"  # kb 位带 MISSING 标签(豁免侧)
        grp._check_cross_group_file_conflicts(dry_run=False)
        assert stops == [], f"kb 位 MISSING 组应豁免该事件(不得误停 ka 侧补救下载方): {stops}"
