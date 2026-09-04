"""test_tracker 测试计划: mixins/tracker tracker 配置匹配

## 测试计划(每个测试函数一条)
- test_match_tracker_domain: 域名匹配
- test_match_tracker_no_match: 无匹配返回 None
- test_match_tracker_multi_domain: 多域名配置匹配
- test_apply_speed_limit_sets_both_directions: 未设限速时写入上传+下载
- test_apply_speed_limit_skips_when_equal: 当前值==目标值不重复写
- test_apply_speed_limit_odd_manual_skip: 当前为奇数 KiB 手动限速不覆盖(仅另一方向写)
- test_apply_speed_limit_dry_run_no_api: dry_run 只记日志不调 API
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


# ---------- tracker 单种限速 _apply_speed_limit ----------


def test_apply_speed_limit_sets_both_directions():
    """未设限速的种子: 上传+下载按 tracker 配置写入(字节/秒)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(hash="H1")
        conf = _conf("HHan", ["hhanclub.net"])
        conf.upload_speed_limit = 5 * 1024 * 1024
        conf.download_speed_limit = 2 * 1024 * 1024
        mgr._apply_speed_limit(tor, conf, dry_run=False)
        assert client.calls == [
            ("set_upload_limit", 5 * 1024 * 1024),
            ("set_download_limit", 2 * 1024 * 1024),
        ]


def test_apply_speed_limit_skips_when_equal():
    """当前限速已等于目标值: 幂等跳过不重复写"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(hash="H1", up_limit=5 * 1024 * 1024, dl_limit=5 * 1024 * 1024)
        conf = _conf("HHan", ["hhanclub.net"])
        conf.upload_speed_limit = 5 * 1024 * 1024
        conf.download_speed_limit = 5 * 1024 * 1024
        mgr._apply_speed_limit(tor, conf, dry_run=False)
        assert client.calls == []


def test_apply_speed_limit_odd_manual_skip():
    """当前为手动限速(奇数 KiB): 不覆盖该方向; 另一方向仍正常写入"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        # up_limit=2001*1024B = 2001KiB(奇数 -> 视为手动设置), dl_limit=0
        tor = FakeTorrent(hash="H1", up_limit=2001 * 1024, dl_limit=0)
        conf = _conf("HHan", ["hhanclub.net"])
        conf.upload_speed_limit = 5 * 1024 * 1024
        conf.download_speed_limit = 5 * 1024 * 1024
        mgr._apply_speed_limit(tor, conf, dry_run=False)
        assert client.calls == [("set_download_limit", 5 * 1024 * 1024)]


def test_apply_speed_limit_dry_run_no_api():
    """dry_run: 只打日志不调用任何 API"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(hash="H1")
        conf = _conf("HHan", ["hhanclub.net"])
        conf.upload_speed_limit = 5 * 1024 * 1024
        conf.download_speed_limit = 2 * 1024 * 1024
        mgr._apply_speed_limit(tor, conf, dry_run=True)
        assert client.calls == []
