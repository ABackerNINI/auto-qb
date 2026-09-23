"""test_expr_eval 测试计划: rules/expr 取值面(env)与求值(eval)

## 测试计划(每个测试函数一条)
- test_seed_fields: tor.* 快照字段取值(大小/名称/标签集合/状态类别/标签数)与类型
- test_derived_values: 派生值(progress_pct / age / idle 哨兵 / upload_today / hr 缺省)
- test_tracker_values: tracker.name 未匹配站点 = "Unknown"、groups = 空列表(有定义的缺省, 不报错)
- test_sys_time_and_counts: sys 时间类与全局计数
- test_server_state_unavailable: server_state 未同步 -> ExprError(绝不返回假 0)
- test_server_state_values: server_state 可用 -> 取值正确; 缺字段 -> 报错
- test_expensive_values_cached: freespace 同表达式内只查一次(ctx 缓存)
- test_short_circuit_skips_expensive: and/or 短路 -> 右侧昂贵取值不被调用
- test_runtime_type_errors: 除零 / 运行期类型不符 -> ExprError(raw() 静态类型为 ANY, 只能运行期发现)
- test_static_validation: 配置期语义校验(未知名/未知函数/参数个数/类型冲突/结果必须布尔)
- test_expr_condition_matches: ExprCondition 正常匹配(编译期校验 + 运行期求值)
- test_config_validation_rejects_bad_expr: config 校验把表达式错误聚合成可读报错
- test_process_stops_on_condition_error: 求值出错 -> process 返回 (False, True)(出错即停规则)
- test_legacy_condition_equivalence: 旧 16 个条件逐条对拍等价表达式(同一 FakeTorrent 结果一致)
- test_traffic_values: 全局流量值(需 traffic_source 数据源)取值正确
- test_traffic_unconfigured: 未配置数据源 -> ExprError(绝不返回 0)
- test_config_gate_for_traffic_names: 用到无数据源名字 -> 配置期禁用(配了才放行)
"""
import os
import shutil
import tempfile
from datetime import date, datetime

import pytest

from auto_qb.config.models import GlobalSpeedLimitCurve
from auto_qb.config.validation.rules import _validate_expr_condition_spec, _validate_rules
from auto_qb.rules.base import Rule
from auto_qb.rules.conditions import (
    CategoryCondition,
    DateTimeCondition,
    ExprCondition,
    FreespaceCondition,
    HrCondition,
    PathCondition,
    SeedtimeCondition,
    SizeCondition,
    StateCondition,
    TagsCondition,
    TrackerGroupCondition,
    TrackersCondition,
    UploadRatioCondition,
    UploadSizeCondition,
    UploadSizeThisMonthCondition,
    UploadSizeThisWeekCondition,
    UploadSizeTodayCondition,
)
from auto_qb.rules.expr import compile_expr, evaluate, validate
from auto_qb.rules.expr.errors import ExprError, ExprSyntaxError
from helpers import FakeClient, FakeTorrent, make_ctx, make_manager

_GIB = 1024**3


def _setup(tmp=None, **tor_kw):
    """造 manager + ctx; tor 默认 200GiB / 分享率 2.0 / 已做种 4 天

    ❗不传 `tmp` 时**不用 `tempfile.mkdtemp()`**(2026-09-23 实测): 那个没人回收, 每跑一次就在
    TMPDIR 根下留一个 `tmpXXXX` 目录 —— 实测已积到 1268 个。改挂 `TemporaryDirectory` 到 mgr 上:
    随 mgr 释放即删, 且不会像"局部变量不返回"那样被提前回收(那会让 mgr 后续写 state.json 失败)。
    """
    holder = None if tmp else tempfile.TemporaryDirectory(prefix="autoqb-expr-")
    td = tmp or holder.name
    mgr = make_manager(os.path.join(td, "state.json"))
    if holder is not None:
        mgr._test_tmpdir = holder  # 生命周期锚点: 见 docstring
    tor = FakeTorrent(size=200 * _GIB, uploaded=400 * _GIB, ratio=2.0, seeding_time=4 * 86400, **tor_kw)
    ctx = make_ctx(mgr, tor, FakeClient())
    return mgr, tor, ctx


def _val(text, ctx):
    return evaluate(compile_expr(text).root, ctx)


def test_seed_fields():
    _, _, ctx = _setup(tags="HR,1080p", state="uploading")
    assert _val("tor.size", ctx) == 200 * _GIB
    assert _val("tor.name", ctx) == "Test"
    assert _val('"HR" in tor.tags', ctx) is True
    assert _val('"nope" in tor.tags', ctx) is False
    assert _val("tor.is_uploading", ctx) is True
    assert _val("tor.is_downloading", ctx) is False
    assert _val("tor.tags_count", ctx) == 2
    assert _val("tor.tags_raw", ctx) == "HR,1080p"


def test_derived_values():
    _, tor, ctx = _setup()
    assert _val("tor.progress_pct", ctx) == tor.progress * 100
    assert _val("tor.upload_today", ctx) == tor.uploaded  # 无基线时增量 = 累计上传
    assert _val("tor.age", ctx) > 0
    # last_activity = -1(从未传输) -> idle 为无穷大(从未活动即无限久)
    tor.last_activity = -1
    assert _val("tor.idle", ctx) == float("inf")
    # 无 tracker_conf / 无 HR 配置 -> 有定义的缺省 false, 不报错
    tor.tracker_conf = None
    assert _val("tor.hr_condition_met", ctx) is False
    assert _val("tor.hr_satisfied", ctx) is False


def test_tracker_values():
    mgr, tor, ctx = _setup()
    assert _val("tracker.name", ctx) == "HHan"
    tor.tracker_conf = None
    assert _val("tracker.name", ctx) == "Unknown"
    assert _val('"国内" in tracker.groups', ctx) is False


def test_sys_time_and_counts():
    mgr, _, ctx = _setup()
    now = datetime.now()
    assert _val("sys.dow", ctx) == now.isoweekday()
    assert _val("sys.dom", ctx) == now.day
    assert _val("sys.time_of_day", ctx) == now.hour * 60 + now.minute
    assert _val("sys.torrent_count", ctx) >= 1
    assert _val("sys.torrent_count", ctx) == len(mgr.store.by_hash)


def test_server_state_unavailable():
    _, _, ctx = _setup()
    with pytest.raises(ExprError, match="数据源不可用"):
        _val("sys.dl_speed", ctx)
    with pytest.raises(ExprError, match="数据源不可用"):
        _val("sys.alt_speed_on", ctx)


def test_server_state_values():
    mgr, _, ctx = _setup()
    mgr.store.server_state = {"dl_info_speed": 1024, "up_info_speed": 2048, "use_alt_speed_limits": True}
    assert _val("sys.dl_speed", ctx) == 1024
    assert _val("sys.up_speed", ctx) == 2048
    assert _val("sys.alt_speed_on", ctx) is True
    # 缺字段 -> 报错(不静默给 0)
    with pytest.raises(ExprError, match="缺失字段"):
        _val("sys.dl_limit", ctx)


def test_expensive_values_cached(monkeypatch):
    _, _, ctx = _setup()
    calls = []

    def fake_usage(path):
        calls.append(path)
        return shutil._ntuple_diskusage(500 * _GIB, 100 * _GIB, 400 * _GIB)

    monkeypatch.setattr(shutil, "disk_usage", fake_usage)
    # 同表达式内两次调用同一路径 -> 只查一次(ctx 缓存)
    assert _val('(freespace("R:/") < 100GiB) and (freespace("R:/") < 50GiB)', ctx) is False
    assert len(calls) == 1


def test_short_circuit_skips_expensive(monkeypatch):
    _, _, ctx = _setup()
    calls = []
    monkeypatch.setattr(
        shutil, "disk_usage", lambda path: calls.append(path) or shutil._ntuple_diskusage(500 * _GIB, 0, 0)
    )
    # 左侧已为真 -> or 短路, 右侧 freespace 不执行
    assert _val('(tor.size > 1GiB) or (freespace("R:/") < 1GiB)', ctx) is True
    assert calls == []


def test_runtime_type_errors():
    _, tor, ctx = _setup()
    with pytest.raises(ExprError, match="除数为 0"):
        _val("(tor.size / 0) > 1", ctx)
    # raw() 静态类型是 ANY -> 类型问题只能运行期发现
    tor.extra_field = "abc"
    with pytest.raises(ExprError, match="必须是数值"):
        _val('(raw("extra_field") + 1) > 0', ctx)
    with pytest.raises(ExprError, match="种子上没有字段"):
        _val('(raw("missing") + 1) > 0', ctx)


def test_static_validation():
    # 语义校验在配置期进行, 不需要 ctx
    for bad, match in (
        ("tor.nope > 1", "未知取值"),
        ("nope(1) > 1", "未知函数"),
        ("freespace() > 1", "参数个数"),
        ('tor.size > "abc"', "同为数值或同为字符串"),
        ('tor.name > 1', "同为数值或同为字符串"),
        ('(tor.size + "abc") > 1', "两侧都必须是数值"),
        ("(tor.size > 1) and (tor.name)", "两侧都必须是布尔"),
        ("tor.size", "结果必须是布尔"),
    ):
        with pytest.raises(ExprSyntaxError, match=match):
            validate(compile_expr(bad).root)
    validate(compile_expr("(tor.size >= 10GiB) and (tor.ratio > 1.5)").root)  # 正例不抛


def test_expr_condition_matches():
    _, _, ctx = _setup(tags="HR", state="uploading")
    cond = ExprCondition('(tor.size >= 100GiB) and ("HR" in tor.tags)')
    assert cond.match(ctx) is True
    assert ExprCondition('(tor.ratio > 3.0)').match(ctx) is False
    # 编译期就拒: 名字拼错 / 结果不是布尔
    for bad in ("tor.nope > 1", "tor.size"):
        with pytest.raises(ExprSyntaxError):
            ExprCondition(bad)


def test_config_validation_rejects_bad_expr():
    errors = []
    _validate_expr_condition_spec("", "config.r.conditions[0].expr", errors)
    assert "非空字符串" in errors[0]
    _validate_expr_condition_spec("tor.nope > 1", "config.r.conditions[1].expr", errors)
    assert "未知取值" in errors[1]
    errors.clear()
    _validate_expr_condition_spec("(tor.size >= 10GiB)", "config.r.conditions[2].expr", errors)
    assert errors == []


def test_process_stops_on_condition_error():
    with tempfile.TemporaryDirectory() as td:
        mgr, _, ctx = _setup(td)
        # server_state 未同步 -> 求值报错 -> 出错即停规则
        rule = Rule("g.t", {"conditions": [{"expr": "sys.dl_speed > 1"}], "actions": []}, mgr)
        assert rule.process(ctx) == (False, True)


def test_traffic_values():
    """全局流量: 数据源(Traffic Monitor dat)配置后取值正确(单位 KB -> 字节)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, _, ctx = _setup(td)
        dat = os.path.join(td, "history_traffic.dat")
        with open(dat, "w", encoding="utf-8") as f:
            f.write("lines: 2\n")
            f.write(f"{date.today():%Y/%m/%d} 1000/500\n")
            f.write("2020/01/01 7/3\n")  # 非本日非本月 -> 不贡献
        mgr.config.global_speed_limit_curve = GlobalSpeedLimitCurve(dat_path=dat, curves=[])
        assert _val("sys.upload_today", ctx) == 1000 * 1024
        assert _val("sys.download_today", ctx) == 500 * 1024
        assert _val("sys.upload_month", ctx) == 1000 * 1024


def test_traffic_unconfigured():
    """未配置数据源 -> 报错(该名字禁用), 绝不静默返回 0"""
    _, _, ctx = _setup()
    for text in ("sys.upload_today", "sys.download_today", "sys.upload_month"):
        with pytest.raises(ExprError, match="数据源未配置"):
            _val(f"({text} > 1GiB)", ctx)


def test_config_gate_for_traffic_names():
    """配置期门控: 数据源没配 -> 用到该名字即报错; 配了 -> 放行(见 _expr_gate)"""
    spec = {"g": {"r": {"conditions": [{"expr": "(sys.upload_today > 1GiB)"}], "actions": []}}}
    with_source = {"global_speed_limit_curve": {"traffic_source": [{"traffic_monitor": {"dat_path": "/x"}}]}}

    errors: list = []
    _validate_rules(spec, errors, with_source)
    assert errors == []

    errors.clear()
    _validate_rules(spec, errors, {})  # 没配 traffic_source
    assert len(errors) == 1 and "无数据源" in errors[0]
    # 不涉及被门控名字的表达式不受影响
    errors.clear()
    _validate_rules({"g": {"r": {"conditions": [{"expr": "(tor.size > 1GiB)"}], "actions": []}}}, errors, {})
    assert errors == []


def test_legacy_condition_equivalence(monkeypatch):
    """旧 16 个条件 vs 等价表达式: 同一 FakeTorrent 上结果必须一致(见计划第 08 节)

    守阵价值: 表达式能力覆盖旧条件语义 —— 旧条件退役与否是另一回事, 但口径不能漂移。
    """
    monkeypatch.setattr(shutil, "disk_usage", lambda path: shutil._ntuple_diskusage(500 * _GIB, 100 * _GIB, 400 * _GIB))
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"), tracker_kw={"groups": ["国内"]})
        tor = FakeTorrent(
            size=200 * _GIB,
            uploaded=20 * _GIB,
            ratio=2.0,
            seeding_time=4 * 86400,
            tags="a,b",
            category="HR-X",
            state="uploading",
            save_path="/data/x",
            content_path="/data/x/name",
        )
        tor.tracker_conf = mgr.config.trackers["HHan"]
        ctx = make_ctx(mgr, tor, FakeClient())

        pairs = [
            (SizeCondition(">=100MiB"), "tor.size >= 100MiB"),
            (SeedtimeCondition("<24H"), "tor.seeding_time < 24H"),
            (UploadRatioCondition(">1.5"), "tor.ratio > 1.5"),
            (UploadSizeCondition(">10GiB"), "tor.uploaded > 10GiB"),
            (StateCondition("is_complete&is_uploading"), "tor.is_complete and tor.is_uploading"),
            (TagsCondition(["a,b", "c"]), '(("a" in tor.tags) and ("b" in tor.tags)) or ("c" in tor.tags)'),
            (CategoryCondition(["regex:^HR"]), 'tor.category ~ "regex:^HR"'),
            (TrackersCondition(["HHan"]), 'tracker.name ~ "HHan"'),
            (TrackerGroupCondition(["国内"]), '"国内" in tracker.groups'),
            (HrCondition("condition-met"), "tor.hr_condition_met"),
            (HrCondition("satisfied"), "tor.hr_satisfied"),
            (HrCondition("condition-not-met"), "not tor.hr_condition_met"),
            (PathCondition("/data/x"), '(tor.save_path ~ "/data/x") or (tor.content_path ~ "/data/x")'),
            (UploadSizeTodayCondition(">1GiB"), "tor.upload_today > 1GiB"),
            (UploadSizeThisWeekCondition(">1GiB"), "tor.upload_week > 1GiB"),
            (UploadSizeThisMonthCondition(">1GiB"), "tor.upload_month > 1GiB"),
            (
                DateTimeCondition({
                    "day_of_week": "1-7",
                    "time": "00:00-23:59"
                }),
                "((sys.dow >= 1) and (sys.dow <= 7)) and ((sys.time_of_day >= 00:00) and (sys.time_of_day <= 23:59))"
            ),
            (FreespaceCondition({
                "path": "R:/",
                "amount": "<100GiB"
            }), 'freespace("R:/") < 100GiB'),
        ]
        assert len(pairs) == 18
        for old, text in pairs:
            assert old.match(ctx) == _val(text, ctx), f"不等价: {old!r} vs {text}"
