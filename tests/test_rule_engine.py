"""test_rule_engine 测试计划: mixins/rule_engine 规则加载/状态/引用

## 测试计划(每个测试函数一条)
- test_load_rules_from_config: 从配置加载规则
- test_load_state_missing_or_broken: 状态文件缺失或损坏 -> 空状态
- test_load_state_valid: 有效状态加载
- test_save_state_error_swallowed: 保存状态错误被吞掉
- test_record_and_get_exec_record: 执行记录写入与读取
- test_begin_round_and_upload_delta: 本轮开始与上传增量
- test_resolve_refs_exact_and_prefix: 引用精确与前缀解析
- test_tracker_rule_refs: tracker 规则引用
- test_process_torrent_with_refs: 带引用处理种子
- test_handle_rule_missing_torrent: 种子不存在 -> 不执行规则
- test_handle_rule_process_ok: _handle_rule 正常执行动作
- test_handle_rule_process_error: 规则处理异常被捕获 -> True
- test_load_rules_skips_non_dict_group: 非 dict 规则组 -> 跳过
- test_rules_for_torrent_tracker_error: tracker 拉取异常 -> 无规则绑定
- test_process_torrent_no_enabled_rules: 无启用规则 -> False
- test_process_torrent_no_refs: 无 tracker 引用 -> 执行全部启用规则
- test_process_torrent_unresolved_refs: 引用规则不存在 -> False
- test_tracker_rule_refs_force_continue: ignore_next_rule_error 标志 -> force_continue
"""
import json
import os
import tempfile
from unittest import mock

from auto_qb.rules.base import Rule
from auto_qb.taskqueue import Task
from helpers import FakeClient, FakeTorrent, make_manager


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


def test_handle_rule_missing_torrent():
    """_handle_rule: 种子已删除(_get_torrent 返回 None) -> False 任务消亡"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr._get_torrent = lambda h: None
        rule = mock.MagicMock()
        task = Task("rule", "t", torrent_hash="H1", interval=0)
        assert mgr._handle_rule(rule, task, dry_run=False) is False


def test_handle_rule_process_ok():
    """_handle_rule: 正常执行规则 -> True 任务保留"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.torrents["HASH123"] = FakeTorrent(tags="")
        rule = Rule("t", {"actions": [{"add_tags": ["X"]}]}, mgr)
        task = Task("rule", "t", torrent_hash="HASH123", interval=0)
        assert mgr._handle_rule(rule, task, dry_run=False) is True
        assert ("add_tags", ["X"]) in client.calls


def test_handle_rule_process_error():
    """_handle_rule: 规则执行抛异常 -> 捕获并返回 True"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.torrents["HASH123"] = FakeTorrent(tags="")
        rule = mock.MagicMock()
        rule.process.side_effect = RuntimeError("boom")
        task = Task("rule", "t", torrent_hash="HASH123", interval=0)
        assert mgr._handle_rule(rule, task, dry_run=False) is True


def test_load_rules_skips_non_dict_group():
    """_load_rules: 非 dict 规则组 -> 跳过该组不崩溃"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.rules = []
        mgr.config.rules_config = {
            "bad_group": ["not", "a", "dict"],
            "example_rules": {
                "only_rule": {
                    "actions": []
                }
            },
        }
        mgr._load_rules()
        assert [r.name for r in mgr.rules] == ["example_rules.only_rule"]
        assert [r.name for r in mgr.enabled_rules] == ["example_rules.only_rule"]


def test_rules_for_torrent_tracker_error():
    """_rules_for_torrent: tracker 拉取异常 -> urls 为空 -> 无规则绑定"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client

        def boom(h):
            raise RuntimeError("api down")

        client.torrents_trackers = boom
        assert mgr._rules_for_torrent(FakeTorrent(tags="")) == []


def test_process_torrent_no_enabled_rules():
    """process_torrent: 无启用规则 -> 直接返回 False"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.client = FakeClient()
        mgr.enabled_rules = []
        assert mgr.process_torrent(FakeTorrent(tags=""), dry_run=False) is False


def test_process_torrent_no_refs():
    """process_torrent: 无 tracker 引用 -> 执行全部启用规则"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        handled = mgr.process_torrent(FakeTorrent(tags=""), dry_run=False)
        assert handled is True
        assert ("add_tags", ["HHan", "seed-3D"]) in client.calls, "add_site_tag 应执行"


def test_process_torrent_unresolved_refs():
    """process_torrent: tracker 引用存在但规则解析为空 -> False"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"), tracker_rules=["@nonexistent.rule"])
        client = FakeClient()
        mgr.client = client
        assert mgr.process_torrent(FakeTorrent(tags=""), dry_run=False) is False, \
            "引用解析为空应返回 False"
        assert client.calls == [], "不应执行任何动作"


def test_tracker_rule_refs_force_continue():
    """_tracker_rule_refs: ignore_next_rule_error 标志识别"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(
            os.path.join(td, "state.json"),
            tracker_rules=["@example_rules.add_site_tag", "ignore_next_rule_error: true"],
        )
        from auto_qb.rules.base import RuleContext
        ctx = RuleContext(mgr, FakeClient(), mgr.config, FakeTorrent(tags=""), False)
        refs, force_continue = mgr._tracker_rule_refs(ctx)
        assert refs == ["example_rules.add_site_tag"]
        assert force_continue is True
