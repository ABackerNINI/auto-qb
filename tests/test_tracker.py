"""test_tracker 测试计划: mixins/tracker tracker 配置匹配

## 测试计划(每个测试函数一条)
- test_match_tracker_domain: 域名匹配
- test_match_tracker_no_match: 无匹配返回 None
- test_match_tracker_multi_domain: 多域名配置匹配
"""
import os
import tempfile

from auto_qb.config import TrackerConfig
from helpers import FakeClient, FakeTorrent, make_manager


def _conf(name, domains):
    return TrackerConfig(
        name=name,
        domains=domains,
        tags=[],
        remove_tags=[],
        upload_speed_limit=None,
        download_speed_limit=None,
        hr=None,
        rules=[],
        remove_similar_tags=False,
    )


def test_match_tracker_domain():
    """域名包含匹配(URL 中含域名即匹配)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        mgr.config.trackers = {"HHan": _conf("HHan", ["tracker.hhanclub.net"])}
        tor = FakeTorrent(hash="H1")
        conf = mgr._match_tracker(tor)
        assert conf is not None and conf.name == "HHan"


def test_match_tracker_no_match():
    """无匹配域名返回 None"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        mgr.config.trackers = {"Kufirc": _conf("Kufirc", ["kufirc.com"])}
        tor = FakeTorrent(hash="H1")
        assert mgr._match_tracker(tor) is None


def test_match_tracker_multi_domain():
    """多域名配置: 任一命中即可"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        mgr.config.trackers = {"Kufirc": _conf("Kufirc", ["kufirc.com", "tracker.hhanclub.net"])}
        tor = FakeTorrent(hash="H1")
        assert mgr._match_tracker(tor).name == "Kufirc"
