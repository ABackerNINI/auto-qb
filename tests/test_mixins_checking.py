"""test_mixins_checking 测试计划: mixins/checking 校验完成判定

## 测试计划(每个测试函数一条)
- test_is_check_done_exit_checking: checking 状态 -> 完成
- test_is_check_done_deleted: 种子被删除 -> 完成
- test_is_check_done_error: error 状态 -> 未完成

(旧辅种跳检 _skip_checking_for_cross_seeding 为无调用者的死代码, 已删除;
其职责由 rules/actions.py CheckAction 承担, 对应测试见 test_checking.py / test_actions.py)
"""
import os
import tempfile

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
