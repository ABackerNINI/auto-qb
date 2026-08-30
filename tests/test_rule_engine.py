"""mixins/rule_engine 模块测试: 规则加载 / 状态持久化 / 上传量快照 / 规则引用解析"""
import json
import os
import tempfile
from unittest import mock

from helpers import FakeTorrent, make_manager


def test_load_rules_from_config():
    """从 config rules_config 加载规则, 规则名带规则集前缀, enabled 过滤"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        names = {r.name for r in mgr.rules}
        assert names == {
            "example_rules.add_site_tag",
            "example_rules.hr_done",
            "example_rules.stop_low_ratio",
        }
        assert len(mgr.enabled_rules) == 3


def test_load_state_missing_or_broken():
    """状态文件缺失/损坏 JSON 均返回空 dict"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "missing.json")
        mgr = make_manager(state_file)
        assert mgr._load_state() == {}
        # 损坏 JSON
        with open(state_file, "w", encoding="utf-8") as f:
            f.write("{not json")
        assert mgr._load_state() == {}
        # 非 dict JSON 也返回 {}
        with open(state_file, "w", encoding="utf-8") as f:
            f.write("[1,2,3]")
        assert mgr._load_state() == {}


def test_load_state_valid():
    """合法状态文件返回 dict"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump({"exec_history": {"k": 1}}, f)
        mgr = make_manager(state_file)
        assert mgr._load_state() == {"exec_history": {"k": 1}}


def test_save_state_error_swallowed():
    """保存失败仅告警不抛异常"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.state = {"a": 1}
        with mock.patch("builtins.open", side_effect=OSError("disk full")):
            mgr.save_state()  # 不应抛异常


def test_record_and_get_exec_record():
    """记录/查询执行历史: key = '规则名:hash'"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.record_execution("example_rules.add_site_tag", "HASH123")
        rec = mgr.get_exec_record("example_rules.add_site_tag", "HASH123")
        assert rec is not None and "ts" in rec and "date" in rec and "hour" in rec
        assert mgr.get_exec_record("other.rule", "HASH123") is None


def test_begin_round_and_upload_delta():
    """周期快照: 首次建立基线, 同日幂等, 增量计算下限 0"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        tor = FakeTorrent(hash="H1", uploaded=100)
        mgr.begin_round([tor])
        snaps = mgr.state["upload_snapshots"]
        assert snaps["daily"]["baseline"]["H1"] == 100
        assert snaps["weekly"]["baseline"]["H1"] == 100
        assert snaps["monthly"]["baseline"]["H1"] == 100
        # 同日再次 begin_round: 基线不变
        tor.uploaded = 200
        mgr.begin_round([tor])
        assert snaps["daily"]["baseline"]["H1"] == 100
        # 增量
        assert mgr.upload_delta(tor, "daily") == 100
        # 客户端重启归零: 下限 0
        tor.uploaded = 10
        assert mgr.upload_delta(tor, "daily") == 0
        # 未在基线中的种子: 增量 = 当前上传量(基线按 0 计)
        assert mgr.upload_delta(FakeTorrent(hash="NEW", uploaded=999), "daily") == 999


def test_resolve_refs_exact_and_prefix():
    """规则引用解析: 精确 '集合.规则' / 前缀 '集合' / 去重"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        exact = mgr._resolve_refs(["example_rules.add_site_tag"])
        assert [r.name for r in exact] == ["example_rules.add_site_tag"]
        prefix = mgr._resolve_refs(["example_rules"])
        assert len(prefix) == 3
        # 前缀+精确去重
        both = mgr._resolve_refs(["example_rules", "example_rules.add_site_tag"])
        assert len(both) == 3
        # 未知引用 -> 空
        assert mgr._resolve_refs(["nope"]) == []


def test_tracker_rule_refs():
    """从匹配 tracker 收集 @ 引用与 ignore_next_rule_error 标志"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"), tracker_rules=["@example_rules.add_site_tag"])
        from auto_qb.rules.base import RuleContext
        from helpers import FakeClient
        ctx = RuleContext(mgr, FakeClient(), mgr.config, FakeTorrent(tags=""), False)
        refs, force_continue = mgr._tracker_rule_refs(ctx)
        assert refs == ["example_rules.add_site_tag"]
        assert force_continue is False


def test_process_torrent_with_refs():
    """process_torrent: 匹配 tracker 引用时只执行引用规则"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"), tracker_rules=["@example_rules.add_site_tag"])
        from helpers import FakeClient
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(tags="")
        handled = mgr.process_torrent(tor, dry_run=False)
        assert handled is True
        # 只执行了 add_site_tag(加标签), 未执行 hr_done(设分类)
        assert ("add_tags", ["HHan", "seed-3D"]) in client.calls
        assert all(c[0] != "set_category" for c in client.calls)
