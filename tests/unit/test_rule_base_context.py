"""test_rule_base_context 测试计划: rules/base ActionResult/RuleContext/Rule

## 测试计划(每个测试函数一条)
- test_rule_context_required_seeding_time: required_seeding_time 解析
- test_rule_context_tracker_urls_and_conf: tracker URL 与配置解析(记录级 tracker_urls + tracker_conf)
- test_rule_context_log_repr: 种子日志描述(describe 已移除由 log_repr 承担)
- test_rule_context_hr_checks: HR 达标判定(做种时间/分享率)
- test_rule_context_files_cached: tor.files(client) 惰性缓存只拉一次
- test_rule_context_tracker_urls_empty: 无 tracker -> tracker_conf None / required_seeding_time 空 / log_repr Unknown
- test_base_condition_init: 基类 __init__ 保存 spec(子类继承)
- test_rule_context_required_seeding_time_no_hr: 无 hr 配置 -> 空字符串
- test_rule_context_log_repr_tracker_error: tracker 拉取异常 -> make_ctx 容错 tracker_conf None / log_repr Unknown
- test_rule_context_hr_dlratio_not_met: 下载比例未达标 -> 触发/满足均 False
- test_rule_context_hr_satisfied_by_ratio: 分享率达标 -> satisfied True
- test_rule_context_hr_no_conf: tracker 无 hr 配置 -> 触发/满足均 False
- test_rule_context_hr_dlsize_not_met: dlsize 下载量未达标 -> 触发 False
- test_rule_context_api_fallback_to_client: manager 无 api 门面时退化 client (P2-a)
"""

import os

import tempfile

from auto_qb.config import TrackerConfig

from auto_qb.core.modules import rules_mod

from auto_qb.rules.base import (
    VERDICT_DEDUPED,
    VERDICT_ERROR,
    VERDICT_EXECUTED,
    VERDICT_NO_MATCH,
    VERDICT_NO_OP,
    VERDICT_PENDING,
    ActionResult,
    BaseAction,
    Rule,
    RuleContext,
)

from auto_qb.rules.conditions import SizeCondition

from auto_qb.rules.actions import AddTagsAction

from auto_qb.infra import utils

from helpers import FakeClient, FakeTorrent, _hr_rule, make_ctx, make_manager


def test_rule_context_required_seeding_time():
    """RuleContext.replace_vars 经 utils.replace_vars 委托: required_seeding_time 取匹配 tracker 的 hr 原始值"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        ctx = make_ctx(mgr, FakeTorrent(tags=""), FakeClient())
        # 旧 RuleContext.required_seeding_time property 已迁出, 直接用 utils.replace_vars 验证
        assert utils.replace_vars("seed-${required_seeding_time}", ctx.torrent.tracker_conf) == "seed-3D"
        assert utils.replace_vars("plain", ctx.torrent.tracker_conf) == "plain"


def test_rule_context_tracker_urls_and_conf():
    """RuleContext: 记录级 tracker_urls + tracker_conf(种子匹配到的 tracker 配置)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        tor = FakeTorrent(tags="")
        ctx = make_ctx(mgr, tor, client)
        assert ctx.torrent.tracker_urls(client) == ["https://tracker.hhanclub.net/announce.php"]
        conf = ctx.torrent.tracker_conf
        assert conf is not None and conf.name == "HHan"
        assert conf.tags == ["HHan"]


def test_rule_context_log_repr():
    """RuleContext: 种子日志描述 log_repr(名称/site/hash; describe 已移除由 log_repr 承担)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        ctx = make_ctx(mgr, FakeTorrent(tags=""), FakeClient())
        desc = ctx.torrent.log_repr
        assert "Test" in desc and "HASH123" in desc and "HHan" in desc


def test_rule_context_hr_checks():
    """RuleContext: check_hr_condition / check_hr_satisfied"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        tor = FakeTorrent(tags="", downloaded=70 * 1024**2, total_size=100 * 1024**2, seeding_time=0)
        ctx = make_ctx(mgr, tor, client)
        conf = ctx.torrent.tracker_conf  # make_ctx 已匹配 tracker 并赋值
        # dlratio: 0.7 >= 0.7 满足
        assert ctx.torrent.check_hr_condition()
        # satisfied: 需要做种 >= 3D+12H
        assert not ctx.torrent.check_hr_satisfied()
        tor.seeding_time = 3 * 86400 + 12 * 3600 + 5
        assert ctx.torrent.check_hr_satisfied()
        # dlsize 条件
        hr = _hr_rule(condition=("dlsize", 100 * 1024**2))
        conf2 = TrackerConfig(
            name="X",
            domains=["x.com"],
            tags=[],
            remove_tags=[],
            upload_speed_limit=None,
            download_speed_limit=None,
            hr=hr,
            rules=[],
            remove_similar_tags=False,
        )
        ctx2 = make_ctx(mgr, FakeTorrent(tags="", downloaded=100 * 1024**2, total_size=0), client)
        # 显式用 dlsize 条件(否则 total_size=0 走 dlratio 会被"总大小为0的辅种兜底"排除)
        ctx2.torrent.tracker_conf.hr = hr
        # dlsize 100MiB = 100*1024*1024 B, downloaded 100MiB 满足触发条件
        assert ctx2.torrent.check_hr_condition()
        # satisfied 还需 seeding_ok (seeding_time=0 不满足) 或 ratio_ok (default 0 不满足), 故 False
        assert not ctx2.torrent.check_hr_satisfied()


def test_rule_context_files_cached():
    """tor.files(client): 惰性缓存, 多次调用只拉取一次"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(tags=""), client)
        assert ctx.torrent.files(client) == []
        assert ctx.torrent.files(client) == []
        assert client.files_calls == 1, "files 应只拉取一次(缓存)"


def test_base_condition_init():
    """BaseCondition.__init__: 子类不定义 __init__ 时继承保存 spec"""
    from auto_qb.rules.base import BaseCondition

    class C(BaseCondition):
        name = "c"

        def match(self, ctx):
            return True

    c = C({"k": "v"})
    assert c.spec == {"k": "v"}


def test_rule_context_required_seeding_time_no_hr():
    """required_seeding_time: 匹配 tracker 无 hr 配置 -> utils.replace_vars 留原文 (无 HR 不替换占位)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"), tracker_kw={"hr": None})
        ctx = make_ctx(mgr, FakeTorrent(tags=""), FakeClient())
        assert utils.replace_vars(
            "seed-${required_seeding_time}", ctx.torrent.tracker_conf
        ) == "seed-${required_seeding_time}"
        assert utils.replace_vars("plain", ctx.torrent.tracker_conf) == "plain"


def test_rule_context_log_repr_tracker_error():
    """tracker 拉取异常: make_ctx 容错(tracker_conf None), log_repr 站点显示 Unknown"""
    def boom(hash_):
        raise RuntimeError("tracker api failed")

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        client.torrents_trackers = boom
        ctx = make_ctx(mgr, FakeTorrent(tags=""), client)
        assert ctx.torrent.tracker_conf is None, "tracker 拉取异常应容错为未匹配"
        assert "Unknown" in ctx.torrent.log_repr


def test_rule_context_hr_dlratio_not_met():
    """check_hr_condition 只答本地触发(0.5 < 0.7 -> False); satisfied 不设触发门,
    做种 999D 远超 3D+12H -> True(计划 26-09-30-0559: 旧断言「未触发则未达标」作废)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        tor = FakeTorrent(tags="", downloaded=50 * 1024**2, total_size=100 * 1024**2, seeding_time=999 * 86400)
        ctx = make_ctx(mgr, tor, client)
        assert ctx.torrent.check_hr_condition() is False, "0.5 < 0.7: 本地不触发(展示辅助判据)"
        assert ctx.torrent.check_hr_satisfied() is True, "做种事实达标即 satisfied, 与触发无关"
        assert ctx.torrent.hr_managed() is False, "达标即不需管束"


def test_rule_context_hr_satisfied_by_ratio():
    """check_hr_satisfied: 分享率达标即可满足, 即使做种时长不足"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"), tracker_kw={"hr": _hr_rule(required_share_ratio=1.0)})
        client = FakeClient()
        tor = FakeTorrent(tags="", downloaded=100 * 1024**2, total_size=100 * 1024**2, seeding_time=0, ratio=2.0)
        ctx = make_ctx(mgr, tor, client)
        conf = ctx.torrent.tracker_conf
        assert ctx.torrent.check_hr_satisfied(), "分享率 2.0 >= 1.0 应算 satisfied"


def test_rule_context_tracker_urls_empty():
    """无 tracker: tracker_conf None、required_seeding_time 空、log_repr 站点 Unknown"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        client.torrents_trackers = lambda h: []  # 无 tracker
        ctx = make_ctx(mgr, FakeTorrent(tags=""), client)
        assert ctx.torrent.tracker_urls(client) == []
        assert ctx.torrent.tracker_conf is None, "无匹配 tracker -> tracker_conf 应为 None"
        assert utils.replace_vars(
            "seed-${required_seeding_time}", ctx.torrent.tracker_conf
        ) == "seed-${required_seeding_time}"
        assert "Unknown" in ctx.torrent.log_repr


def test_rule_context_hr_no_conf():
    """check_hr_condition/check_hr_satisfied: tracker 无 hr 配置 -> 均 False"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"), tracker_kw={"hr": None})
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(tags=""), client)
        conf = ctx.torrent.tracker_conf
        assert conf.hr is None
        assert ctx.torrent.check_hr_condition() is False, "无 hr 配置不应满足触发"
        assert ctx.torrent.check_hr_satisfied() is False, "无 hr 配置不应满足要求"


def test_rule_context_hr_dlsize_not_met():
    """check_hr_condition: dlsize 条件下载量未达标 -> False"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(
            os.path.join(td, "state.json"),
            tracker_kw={"hr": _hr_rule(condition=("dlsize", 100 * 1024**2))},
        )
        client = FakeClient()
        ctx = make_ctx(mgr, FakeTorrent(tags="", downloaded=50 * 1024**2, total_size=0), client)
        conf = ctx.torrent.tracker_conf
        assert ctx.torrent.check_hr_condition() is False, "下载量 50MiB < 100MiB 不应满足"
        assert ctx.torrent.check_hr_satisfied() is False


def test_rule_context_api_fallback_to_client():
    """RuleContext.api: manager 无 api 门面时退化到 client(外部传入种子/测试场景)"""
    from types import SimpleNamespace

    manager = SimpleNamespace(store=SimpleNamespace(get=lambda h: None))  # 无 api 属性
    client = FakeClient()
    ctx = RuleContext(manager, client, None, "H1", dry_run=False)
    assert ctx.api is client
