"""test_torrents_view 测试计划: 种子信息数据层(TorrentRecord/TorrentStore)自测(不连接真实 qB)

## 测试计划(每个测试函数一条)
- test_view_field_value_quantizes_seeding_time: 视图量化: seeding_time 按分钟取整, 其余原样
- test_view_fields_derived_from_snapshot: 守阵(issue 26-10-11-0352) _VIEW_FIELDS 派derive 快照表-不展示缺口, 缺口 ⊆ 快照且缺口字段不置脏
- test_view_dirty_intersection: view_dirty 集合交集判定(触及视图字段 True / 无关字段 False)
- test_hr_entry_guard_single_point: 守阵(issue torrents-hr-entry-guard-dup) HR 判定入口前置守卫单点在 _hr_guard —— record.py 里 not self.tracker_conf.hr 只许出现一次
"""

from dataclasses import MISSING, fields as dc_fields

import pytest

from auto_qb.torrents import REQUIRED_TORRENT_FIELDS, TorrentRecord, TorrentStore, view_dirty, view_field_value

from auto_qb.torrents.compat import _SNAPSHOT_FIELDS

from auto_qb.torrents.view import _VIEW_EXCLUDED_FIELDS

from helpers import FakeClient, FakeTorrent


def test_view_field_value_quantizes_seeding_time():
    """视图字段量化: seeding_time 按分钟取整(向下); 未配置步长的字段原样返回

    前端本就只展示到分钟, 故秒级精度对 UI 无信息量 —— 量化后做种中的种子库不再每轮重建视图。
    """
    assert view_field_value("seeding_time", 0) == 0
    assert view_field_value("seeding_time", 59) == 0
    assert view_field_value("seeding_time", 60) == 60
    assert view_field_value("seeding_time", 119) == 60
    assert view_field_value("seeding_time", 3600) == 3600
    # 未配置步长: 精确返回(速度/上传量等实时字段必须逐字节/逐 Bps 变化)
    assert view_field_value("upspeed", 123) == 123
    assert view_field_value("uploaded", 4096) == 4096
    assert view_field_value("name", "x") == "x"


def test_view_fields_derived_from_snapshot():
    """守阵(issue 26-10-11-0352): 视图展示表 = compat 快照全表 - 不展示缺口(派derive 单点, 手抄两份退役)

    静态: view.py 里 `_SNAPSHOT_FIELD_SET - _VIEW_EXCLUDED_FIELDS` 只允许出现一次(派derive 接线);
    含: 缺口 ⊆ 快照(拼不错/陈旧即红)。行为: 缺口字段不置脏, 快照其余全进脏判定。
    红验: 1. 自抄 61 项 literal 回(行为不变)即静态红; 2. 缺口拼不错即含红; 3. 手抄漏一字段即行为红。
    """
    from pathlib import Path

    snapshot = set(_SNAPSHOT_FIELDS)
    assert _VIEW_EXCLUDED_FIELDS <= snapshot, "缺口里有字段不在快照表(拼不错或陈旧)"
    for f in _VIEW_EXCLUDED_FIELDS:
        assert view_dirty({f}) is False, f"{f} 在缺口 yet view_dirty 真"
    assert all(view_dirty({f}) for f in snapshot - _VIEW_EXCLUDED_FIELDS), "快照字段不在脏判定(手抄漏回归)"
    view_src = (Path(__file__).resolve().parents[1] / "src" / "auto_qb" / "torrents" /
                "view.py").read_text(encoding="utf-8")
    assert view_src.count("_SNAPSHOT_FIELD_SET - _VIEW_EXCLUDED_FIELDS") == 1, "展示表须派derive 快照表-缺口(自抄回即接线消失)"


def test_view_dirty_intersection():
    """view_dirty: 变化字段集触及视图展示字段 -> True; 全是无关字段 -> False"""
    assert view_dirty({"name"}) is True
    assert view_dirty({"state", "ratio_limit"}) is True
    assert view_dirty({"ratio_limit"}) is False
    assert view_dirty(set()) is False


def test_hr_entry_guard_single_point():
    """守阵(issue torrents-hr-entry-guard-dup): HR 判定入口前置守卫单点在 TorrentRecord._hr_guard

    check_hr_condition / hr_managed / check_hr_satisfied 三处顶部逐字同的
    「未配 hr + 排除表」两行守卫收成一处。静态: record.py 里 `not self.tracker_conf.hr`
    只允许出现一次(在 _hr_guard 内)。红验: 任一入口改回自抄两行守卫即红。
    """
    from pathlib import Path

    record = (Path(__file__).resolve().parents[1] / "src" / "auto_qb" / "torrents" /
              "record.py").read_text(encoding="utf-8")
    assert record.count("not self.tracker_conf.hr") == 1, ("HR 判定入口守卫必须在 _hr_guard 单点(出现 >1 次 = 又有人自抄)")
