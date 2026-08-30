"""mixins/checking 模块测试: 校验完成判定 / 辅种跳检"""
import os
import tempfile
from types import SimpleNamespace

from helpers import FakeClient, FakeTorrent, make_manager


def _setup():
    td = tempfile.TemporaryDirectory()
    mgr = make_manager(os.path.join(td.name, "state.json"))
    client = FakeClient()
    mgr.client = client
    return td, mgr, client


def test_is_check_done_exit_checking():
    """种子退出 checking 状态视为校验完成"""
    td, mgr, client = _setup()
    try:
        client.torrents["H1"] = FakeTorrent(hash="H1", state="checkingDL")
        assert mgr._is_check_done("H1") is False
        client.torrents["H1"] = FakeTorrent(hash="H1", state="stalledUP")
        assert mgr._is_check_done("H1") is True
    finally:
        td.cleanup()


def test_is_check_done_deleted():
    """种子已删除视为完成"""
    td, mgr, client = _setup()
    try:
        assert mgr._is_check_done("NOPE") is True
    finally:
        td.cleanup()


def test_is_check_done_error():
    """查询异常时返回 False(保守等待)"""
    td, mgr, client = _setup()
    try:
        client.torrents_info = lambda **kw: (_ for _ in ()).throw(RuntimeError("boom"))
        assert mgr._is_check_done("H1") is False
    finally:
        td.cleanup()


def test_skip_checking_reject_non_zero():
    """下载量/完成量/进度任一非 0 即拒绝跳检"""
    td, mgr, client = _setup()
    try:
        tor = FakeTorrent(state="pausedUP", downloaded=0, completed=0, progress=0.0)
        tor.downloaded = 1
        assert mgr._skip_checking_for_cross_seeding(tor, dry_run=False) is False
        tor.downloaded = 0
        tor.completed = 1
        assert mgr._skip_checking_for_cross_seeding(tor, dry_run=False) is False
        tor.completed = 0
        tor.progress = 0.5
        assert mgr._skip_checking_for_cross_seeding(tor, dry_run=False) is False
    finally:
        td.cleanup()


def test_skip_checking_reject_not_stopped():
    """非停止状态拒绝跳检"""
    td, mgr, client = _setup()
    try:
        tor = FakeTorrent(state="stalledUP", downloaded=0, completed=0, progress=0.0)
        assert mgr._skip_checking_for_cross_seeding(tor, dry_run=False) is False
    finally:
        td.cleanup()


def test_skip_checking_missing_files():
    """文件缺失时中止(返回 None), 不重加"""
    td, mgr, client = _setup()
    try:
        client.files = [SimpleNamespace(name=os.path.join("SubDir", "missing.mkv"), size=100)]
        tor = FakeTorrent(state="pausedUP", downloaded=0, completed=0, progress=0.0)
        assert mgr._skip_checking_for_cross_seeding(tor, dry_run=False) is None
        assert client.calls == []
    finally:
        td.cleanup()


def test_skip_checking_success():
    """跳检成功: 导出->删除->重加(is_skip_checking=True)->可选 start/标签"""
    td, mgr, client = _setup()
    try:
        mgr.config.skip_checking_auto_start = True
        mgr.config.add_skip_checking_tags = True
        mgr.config.skip_checking_tag_format = "skip-checking"
        tor = FakeTorrent(state="pausedUP", downloaded=0, completed=0, progress=0.0)
        assert mgr._skip_checking_for_cross_seeding(tor, dry_run=False) is True
        assert ("export", tor.hash) in client.calls
        assert ("delete", False) in client.calls
        add_call = [c for c in client.calls if c[0] == "add"][-1]
        assert add_call[1]["is_skip_checking"] is True
        assert add_call[1]["paused"] is False
        assert ("start", None) in client.calls
        assert ("add_tags", ["skip-checking"]) in client.calls
    finally:
        td.cleanup()


def test_skip_checking_dry_run_no_calls():
    """dry-run: 判定通过但不调用任何客户端方法"""
    td, mgr, client = _setup()
    try:
        mgr.config.skip_checking_auto_start = True
        mgr.config.add_skip_checking_tags = True
        mgr.config.skip_checking_tag_format = "skip-checking"
        tor = FakeTorrent(state="pausedUP", downloaded=0, completed=0, progress=0.0)
        assert mgr._skip_checking_for_cross_seeding(tor, dry_run=True) is True
        assert client.calls == []
    finally:
        td.cleanup()
