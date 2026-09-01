"""test_conditions 测试计划: rules/conditions 条件插件匹配语义

## 测试计划(每个测试函数一条)
- test_state_map: TorrentState 映射辅助
- test_in_range_and_parse_hm: 时间范围与 hh:mm 解析
- test_path_condition: path 条件匹配
- test_size_condition: size 条件匹配
- test_tags_condition: tags 条件匹配
- test_category_condition: category 条件匹配
- test_trackers_condition: trackers 条件匹配
- test_state_condition: state 条件匹配
- test_hr_condition: HR 条件(做种时间/分享率/上传量)
- test_date_time_condition: 日期时间条件
- test_seedtime_condition: 做种时间条件
- test_upload_ratio_condition: 上传分享率条件
- test_upload_size_condition: 上传量条件
- test_upload_delta_conditions: 上传增量条件(本轮-上轮)
- test_freespace_no_path: FreespaceCondition 无 path 不触发; 空 amount 构造抛 ValueError
- test_freespace_triggered: 磁盘剩余空间低于阈值 -> 触发
- test_freespace_not_triggered: 空间充足 -> 不触发
- test_freespace_os_error: disk_usage 抛 OSError -> 不触发
- test_tags_condition_invalid_regex: 标签条件非法正则 -> 不匹配
- test_tags_condition_regex_no_match: 标签条件正则无匹配 -> 不匹配
- test_category_condition_invalid_regex: 分类条件非法正则 -> 跳过继续
- test_trackers_condition_invalid_regex: tracker 条件非法正则 -> 跳过继续
- test_date_time_day_of_week_mismatch: day_of_week 不匹配 -> 不触发
- test_date_time_cross_midnight: 跨午夜 time 区间匹配/不匹配
- test_date_time_out_of_range: 非跨午夜区间当前时刻不在 -> 不触发
- test_tags_condition_case_sensitive: 标签条件精确匹配区分大小写(:ignore_case 由 utils 层承担)
"""
import os
import shutil
import tempfile
from types import SimpleNamespace

import pytest

from auto_qb.rules.conditions import (
    _in_range,
    _parse_hm,
    _STATE_MAP,
    CategoryCondition,
    DateTimeCondition,
    FreespaceCondition,
    HrCondition,
    PathCondition,
    SeedtimeCondition,
    SizeCondition,
    StateCondition,
    TagsCondition,
    TrackersCondition,
    UploadRatioCondition,
    UploadSizeCondition,
    UploadSizeThisMonthCondition,
    UploadSizeThisWeekCondition,
    UploadSizeTodayCondition,
)
from helpers import FakeClient, FakeTorrent, _hr_rule, make_ctx, make_manager


def _ctx(mgr, tor, client=None):
    return make_ctx(mgr, tor, client or FakeClient())


def test_state_map():
    """语义状态映射表"""
    assert "checkingDL" in _STATE_MAP["checking"]
    assert "stalledUP" in _STATE_MAP["uploading"]
    assert "missingFiles" in _STATE_MAP["errored"]
    assert "stoppedDL" in _STATE_MAP["stopped"]
    assert "pausedUP" in _STATE_MAP["complete"]
    assert "downloading" in _STATE_MAP["downloading"]


def test_in_range_and_parse_hm():
    """_in_range / _parse_hm 纯函数"""
    assert _in_range(5, "3-8")
    assert not _in_range(2, "3-8")
    assert _in_range(5, "5")
    assert not _in_range(4, "5")
    assert _parse_hm("23:59") == (23, 59)
    assert _parse_hm("00:00") == (0, 0)


def test_path_condition():
    """路径条件: save_path/content_path 前缀/regex/或"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        tor = FakeTorrent(save_path=r"R:\Downloads\Movie", content_path=r"R:\Downloads\Movie\file.mkv")
        ctx = _ctx(mgr, tor)

        assert PathCondition(r"R:\Downloads\Movie").match(ctx), "精确匹配 save_path"
        assert PathCondition(r"R:\Downloads\Movie\file.mkv").match(ctx), "精确匹配 content_path"
        assert PathCondition(r"regex:^R:/Downloads").match(ctx), "regex 匹配(斜杠统一)"
        assert not PathCondition(r"R:\Other").match(ctx)
        # 列表为或关系
        assert PathCondition([r"R:\Other", r"R:\Downloads\Movie"]).match(ctx)


def test_size_condition():
    """大小条件"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        ctx = _ctx(mgr, FakeTorrent(size=100 * 1024**2))
        assert SizeCondition(">=100MiB").match(ctx)
        assert SizeCondition(">100MiB").match(ctx) is False
        assert SizeCondition("<200MiB").match(ctx)


def test_tags_condition():
    """标签条件: 逗号与/组间或/regex/变量替换"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        ctx = _ctx(mgr, FakeTorrent(tags="HHan,seed-3D"))
        # 组内逗号 = 与
        assert TagsCondition("HHan,seed-3D").match(ctx)
        assert TagsCondition("HHan,OTHER").match(ctx) is False
        # 组间 = 或
        assert TagsCondition(["A,B", "HHan"]).match(ctx)
        # regex
        assert TagsCondition("regex:^seed-").match(ctx)
        # 变量替换: ${required_seeding_time} -> 3D(来自 tracker hr)
        assert TagsCondition("seed-${required_seeding_time}").match(ctx)
        assert TagsCondition("other-${required_seeding_time}").match(ctx) is False


def test_tags_condition_case_sensitive():
    """标签条件精确匹配区分大小写(:ignore_case 由 utils.match_tag_patterns 承担, 条件插件不支持)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        ctx = _ctx(mgr, FakeTorrent(tags="HHan"))
        assert TagsCondition("HHan").match(ctx)
        assert TagsCondition("hhan").match(ctx) is False, "精确匹配应区分大小写"
        assert TagsCondition("HHAN").match(ctx) is False


def test_category_condition():
    """分类条件: 精确/regex/列表或"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        ctx = _ctx(mgr, FakeTorrent(category="HR-DONE"))
        assert CategoryCondition("HR-DONE").match(ctx)
        assert CategoryCondition("regex:^HR-").match(ctx)
        assert CategoryCondition(["A", "HR-DONE"]).match(ctx)
        assert CategoryCondition("OTHER").match(ctx) is False


def test_trackers_condition():
    """tracker 条件: 匹配配置名/regex/列表或"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        ctx = _ctx(mgr, FakeTorrent(tags=""), client)
        assert TrackersCondition("HHan").match(ctx), "tracker URL 应匹配配置名"
        assert TrackersCondition("regex:^HH").match(ctx)
        assert TrackersCondition("Kufirc").match(ctx) is False
        assert TrackersCondition(["Kufirc", "HHan"]).match(ctx)


def test_state_condition():
    """状态条件: & 与/组间或/语义映射"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        ctx = _ctx(mgr, FakeTorrent(state="stalledUP"))
        assert StateCondition("complete&uploading").match(ctx)
        assert StateCondition("uploading").match(ctx)
        assert StateCondition("downloading").match(ctx) is False
        assert StateCondition(["downloading", "uploading"]).match(ctx), "组间为或"


def test_hr_condition():
    """HR 条件: condition-met / condition-not-met / satisfied / 无配置"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        # tracker 带 hr: 3D@70%
        mgr = make_manager(state_file)
        client = FakeClient()
        tor = FakeTorrent(tags="", downloaded=70 * 1024**2, total_size=100 * 1024**2, seeding_time=0)
        ctx = _ctx(mgr, tor, client)

        assert HrCondition("condition-met").match(ctx), "下载比例 0.7 >= 0.7 应触发"
        assert HrCondition("condition-not-met").match(ctx) is False
        assert HrCondition("satisfied").match(ctx) is False, "做种时长不足不算 satisfied"

        # satisfied: 做种满 3D+12H
        tor.seeding_time = 3 * 86400 + 12 * 3600 + 10
        assert HrCondition("satisfied").match(ctx)

        # condition-not-met: 下载比例不足
        tor2 = FakeTorrent(tags="", downloaded=10 * 1024**2, total_size=100 * 1024**2)
        ctx2 = _ctx(mgr, tor2, client)
        assert HrCondition("condition-not-met").match(ctx2)
        assert HrCondition("condition-met").match(ctx2) is False

        # 无 hr 配置的 tracker: 均不匹配
        mgr3 = make_manager(state_file, tracker_kw={"hr": None})
        ctx3 = _ctx(mgr3, tor, client)
        assert HrCondition("condition-met").match(ctx3) is False


def test_date_time_condition():
    """日期时间条件: day_of_month/day_of_week/time(含跨午夜)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        ctx = _ctx(mgr, FakeTorrent())
        # 今天日期的 day_of_month 匹配
        import datetime
        today = datetime.date.today()
        assert DateTimeCondition({"day_of_month": str(today.day)}).match(ctx)
        assert DateTimeCondition({"day_of_month": "99"}).match(ctx) is False
        # day_of_week: 今天 isoweekday
        assert DateTimeCondition({"day_of_week": str(today.isoweekday())}).match(ctx)
        # time 范围: 取当前小时前后各 1 小时宽范围
        now = datetime.datetime.now()
        start = (now.hour - 1) % 24
        end = (now.hour + 1) % 24
        assert DateTimeCondition({"time": f"{start:02d}:00-{end:02d}:00"}).match(ctx)


def test_seedtime_condition():
    """做种时长条件"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        ctx = _ctx(mgr, FakeTorrent(seeding_time=3600))
        assert SeedtimeCondition(">=1H").match(ctx)
        assert SeedtimeCondition(">2H").match(ctx) is False


def test_upload_ratio_condition():
    """上传比率条件"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        ctx = _ctx(mgr, FakeTorrent(ratio=2.0))
        assert UploadRatioCondition(">1.5").match(ctx)
        assert UploadRatioCondition("<1.5").match(ctx) is False


def test_upload_size_condition():
    """总上传大小条件"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        ctx = _ctx(mgr, FakeTorrent(uploaded=11 * 1024**3))
        assert UploadSizeCondition(">10GiB").match(ctx)
        assert UploadSizeCondition(">12GiB").match(ctx) is False


def test_upload_delta_conditions():
    """周期上传增量条件: 基于 manager.upload_delta"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        tor = FakeTorrent(uploaded=0)
        client = FakeClient()
        # 直接 mock upload_delta 返回值
        mgr.upload_delta = lambda t, kind: 5 * 1024**2
        ctx = make_ctx(mgr, tor, client)
        assert UploadSizeTodayCondition(">1MiB").match(ctx)
        assert UploadSizeThisWeekCondition(">1MiB").match(ctx)
        assert UploadSizeThisMonthCondition(">1MiB").match(ctx)
        assert UploadSizeTodayCondition(">10MiB").match(ctx) is False


def test_freespace_no_path():
    """磁盘空间条件: 未配置 path -> 不匹配; 空 amount -> 构造时抛 ValueError"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        ctx = _ctx(mgr, FakeTorrent())
        assert FreespaceCondition({"path": "", "amount": "<100GiB"}).match(ctx) is False
        assert FreespaceCondition({"amount": "<100GiB"}).match(ctx) is False
        with pytest.raises(ValueError):
            FreespaceCondition({})  # amount 为空 -> parse_compare 报错


def test_freespace_triggered(monkeypatch):
    """磁盘空间条件: 可用空间小于阈值 -> 触发"""
    monkeypatch.setattr(shutil, "disk_usage", lambda p: SimpleNamespace(free=50 * 1024**3))
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        ctx = _ctx(mgr, FakeTorrent())
        assert FreespaceCondition({"path": r"R:\\", "amount": "<100GiB"}).match(ctx)


def test_freespace_not_triggered(monkeypatch):
    """磁盘空间条件: 可用空间充足 -> 不触发"""
    monkeypatch.setattr(shutil, "disk_usage", lambda p: SimpleNamespace(free=200 * 1024**3))
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        ctx = _ctx(mgr, FakeTorrent())
        assert FreespaceCondition({"path": r"R:\\", "amount": "<100GiB"}).match(ctx) is False


def test_freespace_os_error(monkeypatch):
    """磁盘空间条件: disk_usage 抛 OSError -> 不匹配(不中断)"""
    def boom(path):
        raise OSError("no such drive")

    monkeypatch.setattr(shutil, "disk_usage", boom)
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        ctx = _ctx(mgr, FakeTorrent())
        assert FreespaceCondition({"path": r"R:\\", "amount": "<100GiB"}).match(ctx) is False


def test_tags_condition_invalid_regex():
    """标签条件: 非法正则 -> 整组不匹配(不抛异常)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        ctx = _ctx(mgr, FakeTorrent(tags="HHan"))
        assert TagsCondition("regex:[invalid").match(ctx) is False


def test_tags_condition_regex_no_match():
    """标签条件: 正则无匹配 -> 不触发"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        ctx = _ctx(mgr, FakeTorrent(tags="HHan,seed-3D"))
        assert TagsCondition("regex:^NO-").match(ctx) is False


def test_category_condition_invalid_regex():
    """分类条件: 非法正则 -> 跳过该模式继续"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        ctx = _ctx(mgr, FakeTorrent(category="HR-DONE"))
        assert CategoryCondition("regex:[invalid").match(ctx) is False
        assert CategoryCondition(["regex:[invalid", "HR-DONE"]).match(ctx), "非法正则跳过, 其余模式仍可匹配"


def test_trackers_condition_invalid_regex():
    """tracker 条件: 非法正则 -> 跳过该模式继续"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        ctx = _ctx(mgr, FakeTorrent(tags=""), FakeClient())
        assert TrackersCondition("regex:[invalid").match(ctx) is False
        assert TrackersCondition(["regex:[invalid", "HHan"]).match(ctx), "非法正则跳过, 其余模式仍可匹配"


def test_date_time_day_of_week_mismatch():
    """日期时间条件: day_of_week 不等于今天 -> 不触发"""
    import datetime
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        ctx = _ctx(mgr, FakeTorrent())
        today = datetime.date.today()
        other = (today.isoweekday() % 7) + 1  # 1-7 中与今天不同的值
        assert DateTimeCondition({"day_of_week": str(other)}).match(ctx) is False


def test_date_time_cross_midnight(monkeypatch):
    """日期时间条件: 跨午夜 time 区间(23:00-01:00)匹配与不匹配"""
    import datetime as _dt
    from auto_qb.rules import conditions as cond_mod

    class FakeDatetime(_dt.datetime):
        @classmethod
        def now(cls):
            return cls(2026, 1, 1, 23, 30)

    monkeypatch.setattr(cond_mod, "datetime", FakeDatetime)
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        ctx = _ctx(mgr, FakeTorrent())
        assert DateTimeCondition({"time": "23:00-01:00"}).match(ctx), "23:30 在跨午夜区间内"

    class FakeDatetime2(_dt.datetime):
        @classmethod
        def now(cls):
            return cls(2026, 1, 1, 5, 0)

    monkeypatch.setattr(cond_mod, "datetime", FakeDatetime2)
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        ctx = _ctx(mgr, FakeTorrent())
        assert DateTimeCondition({"time": "23:00-01:00"}).match(ctx) is False, "05:00 不在跨午夜区间内"


def test_date_time_out_of_range(monkeypatch):
    """日期时间条件: 非跨午夜 time 区间, 当前时刻不在区间内 -> 不触发"""
    import datetime as _dt
    from auto_qb.rules import conditions as cond_mod

    class FakeDatetime(_dt.datetime):
        @classmethod
        def now(cls):
            return cls(2026, 1, 1, 14, 0)

    monkeypatch.setattr(cond_mod, "datetime", FakeDatetime)
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        ctx = _ctx(mgr, FakeTorrent())
        assert DateTimeCondition({"time": "10:00-12:00"}).match(ctx) is False, \
            "14:00 不在 10:00-12:00 内"
