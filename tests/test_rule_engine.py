"""test_rule_engine 测试计划: mixins/rule_engine 规则加载/状态/引用/种子级任务

架构说明(任务队列驱动): process_torrent/_tracker_rule_refs 兼容入口已删除,
规则绑定由 _rules_for_torrent(tor) 承担(匹配 tracker 的 rules 引用解析), 执行
经种子级规则任务(_create_rule_task + _handle_rule + 队列移除)驱动。

## 测试计划(每个测试函数一条)
- test_load_rules_from_config: 从配置加载规则
- test_load_state_missing_or_broken: 状态文件缺失或损坏 -> 空状态
- test_load_state_valid: 有效状态加载
- test_save_state_error_swallowed: 保存状态错误被吞掉
- test_record_and_get_exec_record: 执行记录写入与读取
- test_begin_round_and_upload_delta: 本轮开始与上传增量
- test_resolve_refs_exact_and_prefix: 引用精确与前缀解析
- test_tracker_rule_refs: tracker rules 引用 -> _rules_for_torrent 精确绑定单规则
- test_rule_task_executes_only_refs: 规则任务只执行被引用的规则(不再全量执行)
- test_handle_rule_missing_torrent: 种子不存在 -> 返回 False 任务消亡(清理由 run_due 自然承担)
- test_handle_rule_process_ok: _handle_rule 正常执行动作
- test_handle_rule_process_error: 规则处理异常被捕获 -> True
- test_load_rules_skips_non_dict_group: 非 dict 规则组 -> 跳过
- test_rules_for_torrent_uninitialized_conf_raises: 上游未走 refresh (tracker_conf=None) 早暴露 AttributeError (不静默兜底)
- test_rule_task_no_enabled_rules: 无启用规则 -> 无绑定
- test_rules_for_torrent_all_refs: 引用整个规则集 -> 绑定全部启用规则
- test_rules_for_torrent_unresolved_refs: 引用规则不存在 -> 无绑定
- test_rules_for_torrent_ignores_non_ref: tracker rules 非 @ 项(旧 ignore 标志)被忽略
"""
import json
import os
import tempfile
from unittest import mock

import pytest

from auto_qb.rules.base import Rule
from auto_qb.taskqueue import FINISHED, REQUEUE, Task
from helpers import FakeClient, FakeTorrent, make_manager, seed_store


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
    """tracker rules 引用 -> 种子绑定规则: 精确 '@set.rule' -> 只绑定该规则"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"), tracker_rules=["@example_rules.add_site_tag"])
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(tags="")
        tor.tracker_conf = mgr.config.trackers["HHan"]  # 显式 setUp: 模拟 _refresh_torrents 匹配结果
        bound = mgr._rules_for_torrent(tor)
        assert [r.name for r in bound] == ["example_rules.add_site_tag"]


def test_rule_task_executes_only_refs():
    """种子级规则任务只执行 tracker 引用的规则(不再全量执行; 含 set_category 不会被触发)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"), tracker_rules=["@example_rules.add_site_tag"])
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(tags="")
        seed_store(mgr, [tor])
        tor.tracker_conf = mgr._match_tracker_conf(tor)  # 等效 _refresh_torrents 对新增种子的处理
        rules = mgr._rules_for_torrent(tor)
        assert [r.name for r in rules] == ["example_rules.add_site_tag"], "只应绑定被引用的规则"
        for rule in rules:
            task = mgr._create_rule_task(rule, tor.hash, mgr.config.trackers["HHan"])
            assert mgr._handle_rule(rule, task, dry_run=False) is True
        # 只应执行 add_site_tag(加标签); 未引用的 hr_done(设分类)/stop_low_ratio 不执行
        assert ("add_tags", ["HHan", "seed-3D"]) in client.calls
        assert all(c[0] != "set_category" for c in client.calls), f"未引用规则不应执行: {client.calls}"


def test_handle_rule_missing_torrent():
    """store 无该种子: _handle_rule 返回 False 任务消亡(清理由 run_due 自然承担, 不崩溃)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        task = Task("rule", "t", hash="H1", interval=0)
        real = Rule("t", {"conditions": [{"state": "is_complete&is_uploading"}], "actions": []}, mgr)
        assert mgr._handle_rule(real, task, dry_run=False) is False
        assert client.calls == [], "种子不存在不应执行动作"
        # 任务清理: 种子删除后任务由 run_due 到期执行时自然消亡(handler 返回 False), 不再显式移除
        tq = mgr.task_queue
        r1 = Task("rule", "r1", hash="H1", interval=60, handler=lambda t, d: FINISHED)
        r2 = Task("rule", "r2", hash="H1", interval=60, handler=lambda t, d: FINISHED)
        r3 = Task("rule", "r3", hash="H2", interval=60, handler=lambda t, d: REQUEUE)
        tq.add_task(r1, now=1000.0)
        tq.add_task(r2, now=1000.0)
        tq.add_task(r3, now=1000.0)
        assert tq.run_due(False, now=1000.0) == 3, "删除种子的任务到期执行一轮"
        assert [t.hash for t in tq._fast] == ["H2"], "H1 任务应自然消亡, H2 保留"


def test_handle_rule_process_ok():
    """_handle_rule: 正常执行规则 -> True 任务保留"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        # 显式给 FakeTorrent 配 conf: 模拟 _refresh_torrents 阶段的 tracker_conf 匹配结果
        # (不依赖隐式 make_ctx, 让 setUp 显式)
        tor = FakeTorrent(tags="")
        tor.tracker_conf = mgr.config.trackers["HHan"]
        client.torrents["HASH123"] = tor
        seed_store(mgr)
        rule = Rule("t", {"actions": [{"add_tags": ["X"]}]}, mgr)
        task = Task("rule", "t", hash="HASH123", interval=0)
        assert mgr._handle_rule(rule, task, dry_run=False) is True
        assert ("add_tags", ["X"]) in client.calls


def test_handle_rule_process_error():
    """_handle_rule: 规则执行抛异常 -> 捕获并返回 True"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.torrents["HASH123"] = FakeTorrent(tags="")
        seed_store(mgr)
        rule = mock.MagicMock()
        rule.process.side_effect = RuntimeError("boom")
        task = Task("rule", "t", hash="HASH123", interval=0)
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


def test_rules_for_torrent_uninitialized_conf_raises():
    """_rules_for_torrent: 上游未走 refresh (tracker_conf=None) 早暴露 AttributeError, 不静默兜底

    哲学: 防御性 fallback 隐藏调用路径错误, 这里反之让 NoneType.rules 早崩溃
    暴露"种子入 store 后未走 _match_tracker_conf"的设计错误。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        with pytest.raises(AttributeError):
            mgr._rules_for_torrent(FakeTorrent(tags=""))


def test_rule_task_no_enabled_rules():
    """无启用规则: 引用解析空 -> 种子不绑定规则任务"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"), tracker_rules=["@example_rules"])
        client = FakeClient()
        mgr.client = client
        mgr.enabled_rules = []
        tor = FakeTorrent(tags="")
        tor.tracker_conf = mgr.config.trackers["HHan"]
        assert mgr._rules_for_torrent(tor) == []


def test_rules_for_torrent_all_refs():
    """tracker rules 引用整个规则集(@example_rules) -> 绑定全部启用规则; 无引用 -> 不绑定"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"), tracker_rules=["@example_rules"])
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(tags="")
        tor.tracker_conf = mgr.config.trackers["HHan"]
        bound = mgr._rules_for_torrent(tor)
        names = {r.name for r in bound}
        assert names == {"example_rules.add_site_tag", "example_rules.hr_done", "example_rules.stop_low_ratio"}
        # 无 tracker 引用: 种子不绑定任何规则(不再回退执行全部启用规则)
        mgr2 = make_manager(os.path.join(td, "state.json"))  # tracker_rules=None -> conf.rules=[]
        client2 = FakeClient()
        mgr2.client = client2
        tor2 = FakeTorrent(tags="")
        tor2.tracker_conf = mgr2.config.trackers["HHan"]
        assert mgr2._rules_for_torrent(tor2) == []


def test_rules_for_torrent_unresolved_refs():
    """tracker 引用存在但规则解析为空 -> 种子不绑定规则不执行任何动作"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"), tracker_rules=["@nonexistent.rule"])
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(tags="")
        tor.tracker_conf = mgr.config.trackers["HHan"]
        assert mgr._rules_for_torrent(tor) == []


def test_rules_for_torrent_ignores_non_ref():
    """tracker rules 中非 @ 前缀项(旧 ignore_next_rule_error 标志)不被收集为规则引用"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(
            os.path.join(td, "state.json"),
            tracker_rules=["@example_rules.add_site_tag", "ignore_next_rule_error: true"],
        )
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(tags="")
        tor.tracker_conf = mgr.config.trackers["HHan"]
        bound = mgr._rules_for_torrent(tor)
        assert [r.name for r in bound] == ["example_rules.add_site_tag"]
