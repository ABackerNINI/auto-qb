"""test_mixins_checking 测试计划: mixins/checking 校验完成判定

## 测试计划(每个测试函数一条)
- test_is_check_done_exit_checking: checking 状态 -> 完成
- test_is_check_done_deleted: 种子被删除 -> 完成
- test_is_check_done_missing: 快照外种子(未刷新) -> 视为完成

(旧辅种跳检 _skip_checking_for_cross_seeding 为无调用者的死代码, 已删除;
其职责由 rules/actions.py CheckAction 承担, 对应测试见 test_checking.py / test_actions.py)
"""
import os
import tempfile

from helpers import FakeClient, FakeTorrent, make_manager, seed_store


def _setup():
    td = tempfile.TemporaryDirectory()
    mgr = make_manager(os.path.join(td.name, "state.json"))
    client = FakeClient()
    mgr.client = client
    return td, mgr, client


def test_is_check_done_exit_checking():
    """种子退出 checking 状态视为校验完成(判定走 store 快照, 不调 API)"""
    td, mgr, client = _setup()
    try:
        seed_store(mgr, [FakeTorrent(hash="H1", state="checkingDL")])
        assert mgr._is_check_done("H1") is False
        seed_store(mgr, [FakeTorrent(hash="H1", state="stalledUP")])
        assert mgr._is_check_done("H1") is True
    finally:
        td.cleanup()


def test_is_check_done_deleted():
    """种子已删除(快照移除)视为完成"""
    td, mgr, client = _setup()
    try:
        assert mgr._is_check_done("NOPE") is True
    finally:
        td.cleanup()


def test_is_check_done_missing():
    """快照外种子(本 tick 未刷新到)视为完成(保守放行, 避免阻塞队列)"""
    td, mgr, client = _setup()
    try:
        assert mgr._is_check_done("H1") is True
    finally:
        td.cleanup()
