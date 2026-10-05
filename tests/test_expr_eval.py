"""test_expr_eval 测试计划: rules/expr 取值面(env)与求值(eval)

## 测试计划(每个测试函数一条)
- test_seed_fields: tor.* 快照字段取值(大小/名称/标签集合/状态类别/标签数)与类型
- test_derived_values: 派生值(progress_pct / age / idle 哨兵 / hr 缺省)
- test_tracker_values: tracker.name 未匹配站点 = "Unknown"、groups = 空列表(有定义的缺省, 不报错)
- test_sys_time_and_counts: sys 时间类与全局计数
- test_torrent_count_no_full_copy: sys.torrent_count 无谓词直接 len(by_hash) O(1), 不做全库浅拷贝
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
- test_more_getters_and_funcs: 取值器/函数表补遗(idle 正值/计数谓词/tracker.names/file_count/
  len/abs·round·min·max·days·hours/disk_total·disk_used/exists/同 ctx 二次取值命中缓存)
- test_file_access_error_paths: 文件访问层错误映射(FileAccessError 显式报错/OSError 包装/
  exists UNDETERMINED -> ExprError/traffic 数据源不可读)
- test_runtime_error_paths_batch: 运行期错误路径参数化(未知名/未知函数/非布尔逻辑操作数/
  len 不可计长/数值函数吃非数值/in 非容器/比较类型错/未知运算符/未知节点)
- test_arith_and_compare_runtime: 算术 +-*//% 与字符串比较/== !=/一元负号/列表字面量求值
- test_cross_container_list_equality: ==/!= 对 LIST 两侧容器形态归一化(frozenset/list/tuple 转 set
  再比, issue 26-10-06-0027): tor.tags/tracker.groups 对列表字面量精确匹配不再恒错; 标量比较不受影响
- test_static_type_edges: 静态校验补遗(函数参数类型错含无位置字面量/列表与一元/ANY 放行/
  未知节点兜底 ANY/used_names 遍历 Unary·Call·ListLit)
- test_trace_walks_all_node_kinds: trace 遍历 Call/Unary/ListLit + _jsonable 容器/inf/异型兜底
- test_eval_cache_created_on_missing: ctx 无 expr_cache 时求值侧自建缓存
- test_name_table_skips_unmapped_annotation: 注解无类型映射的快照字段跳过登记(不炸), 全局表不受重建影响
"""
import os
import shutil
import tempfile
from datetime import date, datetime
from types import SimpleNamespace

import pytest

from auto_qb.config.models import GlobalSpeedLimitCurve
from auto_qb.config.validation.rules import _validate_expr_condition_spec, _validate_rules
from auto_qb.infra import file_access
from auto_qb.infra.file_access import UNDETERMINED, FileAccessError
from auto_qb.rules.base import Rule
from auto_qb.rules.expr import env as expr_env
from auto_qb.rules.expr import ANY, compile_expr, evaluate, validate
from auto_qb.rules.expr.errors import ExprError, ExprSyntaxError
from auto_qb.rules.expr.eval import trace
from auto_qb.rules.expr.parser import Binary, Lit
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
)
from helpers import FakeClient, FakeTorrent, make_ctx, make_manager

_GIB = 1024**3


def _setup(tmp=None, **tor_kw):
    """造 manager + ctx; tor 默认 200GiB / 分享率 2.0 / 已做种 4 天

    !不传 `tmp` 时**不用 `tempfile.mkdtemp()`**(2026-09-23 实测): 那个没人回收, 每跑一次就在
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
    assert _val("tor.age", ctx) > 0
    # last_activity = -1(从未传输) -> idle 为无穷大(从未活动即无限久)
    tor.last_activity = -1
    assert _val("tor.idle", ctx) == float("inf")
    # 无 tracker_conf / 无 HR 配置 -> 有定义的缺省 false, 不报错
    tor.tracker_conf = None
    assert _val("tor.hr_condition_met", ctx) is False
    assert _val("tor.hr_local_triggered", ctx) is False
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


def test_torrent_count_no_full_copy():
    """sys.torrent_count 无谓词直接 len(by_hash) O(1), 不做全库浅拷贝(issue 26-10-06-0028)。

    守法: values() 一被调用即炸 —— 曾每求值 list(by_hash.values()) 只取 len,
    3000 种子库 interval:0 规则每轮数百万次元素拷贝纯浪费。
    """
    mgr, _, ctx = _setup()

    class _NoValues(dict):
        def values(self):
            raise AssertionError("sys.torrent_count 不应遍历全库(应 len(by_hash) O(1))")

    mgr.store.by_hash = _NoValues({"h1": object(), "h2": object(), "h3": object()})
    assert _val("sys.torrent_count", ctx) == 3


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
            (StateCondition("is_complete&is_uploading"), "tor.is_complete and tor.is_uploading"),
            (TagsCondition(["a,b", "c"]), '(("a" in tor.tags) and ("b" in tor.tags)) or ("c" in tor.tags)'),
            (CategoryCondition(["regex:^HR"]), 'tor.category ~ "regex:^HR"'),
            (TrackersCondition(["HHan"]), 'tracker.name ~ "HHan"'),
            (TrackerGroupCondition(["国内"]), '"国内" in tracker.groups'),
            # 2026-09-30 计划 hr-trigger-semantics: hr_condition_met 与 condition-met 同步换绑
            # hr_managed(需管束), 等价性不破; 纯本地触发另给 tor.hr_local_triggered(循环后直测)
            (HrCondition("condition-met"), "tor.hr_condition_met"),
            (HrCondition("satisfied"), "tor.hr_satisfied"),
            (HrCondition("condition-not-met"), "not tor.hr_condition_met"),
            (PathCondition("/data/x"), '(tor.save_path ~ "/data/x") or (tor.content_path ~ "/data/x")'),
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
        assert len(pairs) == 14
        for old, text in pairs:
            assert old.match(ctx) == _val(text, ctx), f"不等价: {old!r} vs {text}"
        # tor.hr_local_triggered(2026-09-30 新增) = 纯本地下载触发判据:
        # 本种 downloaded 达 total_size(小种子完整下载兜底) -> 触发; 管束判据 hr_condition_met
        # 在同一颗已达标种子上为 False —— 两名语义分叉正好由这组断言钉住
        assert _val("tor.hr_local_triggered", ctx) is True
        assert _val("tor.hr_condition_met", ctx) is False


# ---------- T0.2 扩展: 取值器/函数表错误路径与运行期边界 ----------


def test_more_getters_and_funcs(tmp_path, monkeypatch):
    """取值器与函数表补遗: idle 正值 / 全局计数谓词 / tracker.names / file_count / len /
    abs·round·min·max·days·hours / disk_total·disk_used / exists 真值 / 同 ctx 二次取值命中缓存"""
    calls = []

    def fake_usage(path):
        calls.append(path)
        return shutil._ntuple_diskusage(500 * _GIB, 100 * _GIB, 400 * _GIB)

    monkeypatch.setattr(shutil, "disk_usage", fake_usage)
    _, tor, ctx = _setup(tags="HR", state="uploading")
    # last_activity 为正值(> 0)时 idle = now - last_activity, 不再是 inf 哨兵
    tor.last_activity = datetime.now().timestamp() - 30
    assert 0 < _val("tor.idle", ctx) < 120
    # 全局计数谓词: 库里只有本种子 → 按状态类别各归其位
    assert _val("sys.seeding_count", ctx) == 1
    assert _val("sys.downloading_count", ctx) == 0
    # tracker.names = 该种子所有 tracker URL 命中的站点名集合(昂贵, 按 ctx 缓存)
    assert _val("tracker.names", ctx) == frozenset({"HHan"})
    assert _val('"HHan" in tracker.names', ctx) is True
    # file_count: 走 client 拉文件列表
    ctx.client.files_map[tor.hash] = [{"name": "a.bin"}, {"name": "b.bin"}]
    assert _val("file_count()", ctx) == 2
    # len / 数值函数
    assert _val("len(tor.tags) == 1", ctx) is True
    assert _val("abs(-5) == 5", ctx) is True
    assert _val("round(1.5) == 2", ctx) is True
    assert _val("min(tor.ratio, 1.5) == 1.5", ctx) is True
    assert _val("max(tor.ratio, 1.5) == 2.0", ctx) is True
    assert _val("days(2) == 48H", ctx) is True
    assert _val("hours(2) == 7200", ctx) is True
    # 同 ctx 第二次取同名值: 命中缓存不重查(disk_total/disk_used 已各查一次 = 2,
    # 两次 freespace 只新增 1 次真实查询; Local 层会把路径补成长路径前缀)
    assert _val('disk_total("C:/") == 500GiB', ctx) is True
    assert _val('disk_used("C:/") == 100GiB', ctx) is True
    # exists 真值/假值(经 Local 实现, 只读 stat): 真值用 tmp_path 这个**跨平台真实存在**的目录
    # —— 写死 "C:/" 只在 Windows 成立(Linux CI 上它不存在, 断言必红); 假值用必然不存在的盘符路径
    real_dir = str(tmp_path).replace("\\", "/")
    assert _val(f'exists("{real_dir}")', ctx) is True
    assert _val('exists("Z:/__auto_qb_no_such_path__")', ctx) is False
    n0 = len(calls)
    assert _val('freespace("C:/")', ctx) == 400 * _GIB
    assert _val('freespace("C:/")', ctx) == 400 * _GIB
    assert len(calls) == n0 + 1 and calls[-1] == calls[0] and "C:" in calls[0]


def test_file_access_error_paths(monkeypatch):
    """文件访问层错误映射: FileAccessError -> ExprError(显式不可判定) / OSError -> 「磁盘不可用」/
    exists UNDETERMINED -> ExprError / traffic 数据源配置了但文件不可读 -> ExprError(不给假 0)"""
    class _StubFA:
        def __init__(self, exc):
            self._exc = exc

        def disk_usage(self, path):
            raise self._exc

        def exists(self, path):
            return UNDETERMINED

    _, _, ctx = _setup()
    monkeypatch.setattr(file_access, "get_file_access", lambda: _StubFA(FileAccessError("映射未命中: 不可判定")))
    for fn in ("freespace", "disk_total", "disk_used"):
        with pytest.raises(ExprError, match="不可判定"):
            _val(f'{fn}("C:/") > 0', ctx)
    monkeypatch.setattr(file_access, "get_file_access", lambda: _StubFA(OSError("device boom")))
    for fn in ("freespace", "disk_total", "disk_used"):
        with pytest.raises(ExprError, match="磁盘不可用"):
            _val(f'{fn}("C:/") > 0', ctx)
    with pytest.raises(ExprError, match="路径不可判定"):
        _val('exists("C:/__missing__")', ctx)

    _, _, ctx2 = _setup()
    ctx2.manager.config.global_speed_limit_curve = GlobalSpeedLimitCurve(dat_path="Z:/__no_such__.dat", curves=[])
    with pytest.raises(ExprError, match="数据源不可读"):
        _val("sys.upload_today > 1GiB", ctx2)


def test_runtime_error_paths_batch():
    """运行期错误路径参数化(raw/名字等 ANY 面只拦在运行期): 每条断言钉住报错语义"""
    _, tor, ctx = _setup()
    tor.int_field = 5
    cases = [
        ("tor.nope > 1", "未知取值"),
        ("nope(1) > 1", "未知函数"),
        ("(tor.size > 1) and tor.name", "'and' 的操作数必须是布尔"),
        ("tor.name or (tor.size > 1)", "'or' 的操作数必须是布尔"),
        ('len(raw("int_field")) > 0', "'len' 的参数不可计长"),
        ("abs(tor.name) > 0", "参数必须是数值"),
        ("min(tor.name, 1) > 0", "参数必须是数值"),
        ("1 in tor.size", "不是可容纳取值的容器"),
        ("tor.name > 1", "同为数值或同为字符串"),
        ("tor.name == 1", "类型不一致"),
        ("(tor.size / 0) > 1", "除数为 0"),
        ("(tor.size % 0) > 1", "除数为 0"),
    ]
    for text, match in cases:
        with pytest.raises(ExprError, match=match):
            _val(text, ctx)
    with pytest.raises(ExprError, match="未知运算符"):
        evaluate(Binary("xor", Lit(True), Lit(False)), ctx)
    with pytest.raises(ExprError, match="无法求值"):
        evaluate(object(), ctx)


def test_arith_and_compare_runtime():
    """算术 + - * / % 与取模零、字符串比较、== !=、一元负号、列表字面量求值(运行期各支路)"""
    _, _, ctx = _setup()
    assert _val("(tor.size + tor.uploaded) > 0", ctx) is True
    assert _val("(tor.size - tor.uploaded) < 0", ctx) is True
    assert _val("(tor.ratio * 2) > 3", ctx) is True
    assert _val("(tor.uploaded / tor.size) > 1.5", ctx) is True
    assert _val("(tor.size % 1GiB) == 0", ctx) is True
    assert _val('tor.name > "A"', ctx) is True
    assert _val('tor.name == "Test"', ctx) is True
    assert _val('tor.name != "X"', ctx) is True
    assert _val("(-tor.size) < 0", ctx) is True
    assert _val('tor.state in ["stalledUP", "uploading"]', ctx) is True
    assert _val('tor.state in ["downloading"]', ctx) is False


def test_cross_container_list_equality():
    """==/!= 对 LIST 两侧做容器形态归一化(issue 26-10-06-0027): tor.tags 是 frozenset /
    tracker.groups 是 list / 列表字面量求值为 tuple, Python 跨形态比较恒 False —— 两侧转 set 再比。
    修复前: tor.tags == ["HR"] 恒 False(== 静默失效)、!= 恒 True(全员误匹配)。标量比较不受影响。"""
    _, _, ctx = _setup(tags="HR,1080p")
    # tor.tags(frozenset) 对列表字面量(tuple): 精确匹配(含乱序/重复元素) == True, != False
    assert _val('tor.tags == ["HR", "1080p"]', ctx) is True
    assert _val('tor.tags == ["1080p", "HR"]', ctx) is True  # 集合语义无序
    assert _val('tor.tags == ["HR", "HR", "1080p"]', ctx) is True  # 去重后相等
    assert _val('tor.tags != ["HR", "1080p"]', ctx) is False
    assert _val('tor.tags == ["HR"]', ctx) is False  # 真子集不算相等
    assert _val('tor.tags != ["HR"]', ctx) is True
    # tracker.groups(list) 对列表字面量(tuple): 同口径
    _, _, ctx2 = _setup()
    ctx2.torrent.tracker_conf.groups = ["A组", "B组"]
    assert _val('tracker.groups == ["A组", "B组"]', ctx2) is True
    assert _val('tracker.groups == ["B组", "A组"]', ctx2) is True
    assert _val('tracker.groups != ["A组", "B组"]', ctx2) is False
    assert _val('tracker.groups != []', ctx2) is True
    # 元素不可哈希(列表嵌列表) -> 归一化失败显式报错, 不静默
    with pytest.raises(ExprError, match="不可哈希"):
        _val('tracker.groups == [tracker.groups]', ctx2)
    # 归一化只作用于 LIST: 标量 ==/!= 行为不变(钉子)
    assert _val('tor.name == "Test"', ctx) is True
    assert _val('tor.name != "X"', ctx) is True
    assert _val("tor.size == 200GiB", ctx) is True
    assert _val("tor.is_uploading == tor.is_uploading", ctx) is True  # 布尔等值不受归一化影响


def test_static_type_edges():
    """静态校验补遗: 函数参数类型错(名字带位置 / 字面量无位置) / 列表与一元节点 /
    ANY 参与运算静态放行 / 未知节点兜底 ANY / used_names 遍历 Unary·Call·ListLit"""
    with pytest.raises(ExprSyntaxError, match="参数类型应为 数值"):
        validate(compile_expr("abs(tor.name) > 0").root)
    with pytest.raises(ExprSyntaxError, match="参数类型应为 数值"):
        validate(compile_expr('abs("abc") > 0').root)  # Lit 参数: 无位置信息也要报
    validate(compile_expr("len(raw('x')) > 0").root)  # ANY 参数放行
    validate(compile_expr("(raw('x') + 1) > 0").root)  # ANY 参与算术: 静态放行, 运行期才拦
    validate(compile_expr("(-raw('x')) == 0").root)  # ANY 一元: 静态放行
    validate(compile_expr('(tor.state in ["uploading"]) and (not tor.is_stopped)').root)
    assert expr_env.static_type(object()) == ANY
    ast = compile_expr(
        '(not (sys.upload_today > 1GiB)) and ((sys.download_today in [1, 2]) or (len(tor.tags) > 0))'
    ).root
    assert expr_env.gated_names_in(ast) == ["sys.download_today", "sys.upload_today"]


def test_trace_walks_all_node_kinds(monkeypatch):
    """trace 求值路径: Call/Unary/ListLit 节点遍历 + _jsonable 三类兜底(容器转列表 /
    inf 转字符串 / 其余对象转字符串) —— WEB 试算面板的显示保真"""
    monkeypatch.setattr(shutil, "disk_usage", lambda p: shutil._ntuple_diskusage(500 * _GIB, 100 * _GIB, 400 * _GIB))
    _, tor, ctx = _setup(tags="HR")
    tor.last_activity = -1  # 从未传输 → idle = inf
    tor.extra_dict = {"a": 1}
    # Call 节点 + 参数下钻
    items = trace(compile_expr('freespace("C:/") > 0').root, ctx)
    assert {"kind": "call", "name": "freespace", "value": 400 * _GIB} in items
    # Unary / ListLit 节点
    items = trace(compile_expr('(not tor.is_stopped) and (tor.state in ["stalledUP"])').root, ctx)
    assert [i["name"] for i in items if i["kind"] == "name"] == ["tor.is_stopped", "tor.state"]
    # 集合值转列表(frozenset → ["HR"])
    items = trace(compile_expr('"HR" in tor.tags').root, ctx)
    assert items[-1]["value"] == ["HR"]
    # inf 转字符串
    items = trace(compile_expr("(tor.idle > 1)").root, ctx)
    assert items[0]["value"] == "inf"
    # 其余对象(dict)转字符串
    items = trace(compile_expr('(raw("extra_dict") == raw("extra_dict"))').root, ctx)
    assert all(isinstance(i["value"], str) for i in items)


def test_eval_cache_created_on_missing():
    """ctx 无 expr_cache 属性时求值侧自建缓存(外部极简 ctx 的兜底路径)"""
    ctx = SimpleNamespace(torrent=None, manager=None, config=None, client=None)
    assert evaluate(compile_expr("sys.now > 0").root, ctx) is True
    assert ctx.expr_cache, "昂贵取值应把结果落进自建的 expr_cache"


def test_name_table_skips_unmapped_annotation(monkeypatch):
    """名字表构建对「注解不在类型映射里」的快照字段: 跳过登记而非炸表 —— 新增注解类型
    (如嵌套 dataclass)时引擎优雅降级, 其余字段照常可用; 重建不影响模块级全局表"""
    patched = dict(expr_env._PY_KIND)
    del patched["str"]  # str 型快照字段(如 tor.name)全部失去映射
    monkeypatch.setattr(expr_env, "_PY_KIND", patched)
    table = expr_env._build_name_table()
    assert "tor.name" not in table, "无类型映射的字段应被跳过(continue 支路)"
    assert "tor.size" in table and table["tor.size"].type == expr_env._PY_KIND["int"]
    assert "tor.tags" in table, "手工登记的派生名不受注解映射影响"
    assert "tor.name" in expr_env.NAME_TABLE, "重建只产局部表, 模块级全局表保持原样"
