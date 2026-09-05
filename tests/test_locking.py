"""test_locking 测试计划: 单实例锁 (基于 filelock + 伴生 meta)

## 测试计划 (每个测试函数一条)
- test_lock_acquire_release_basic: 锁文件创建/释放, 伴生 meta 产生/消失
- test_lock_contention_raises_with_holder_info: 第二次获取抛 SingleInstanceLockError, 消息含 PID/时间/路径
- test_lock_skipped_when_no_lock_flag: QbManager no_lock=True 不创建锁文件 (导出模式)
- test_lock_file_path_derives_from_state_file: state_file 去掉扩展名, 锁文件为 `<base>.lock`
"""
import os
import re
import time

import pytest

from auto_qb.config import ConfigError
from auto_qb.locking import SingleInstanceLock, SingleInstanceLockError
from auto_qb.qbmanager import QbManager
from helpers import FakeConfig


def test_lock_acquire_release_basic(tmp_path):
    """锁文件创建/释放, 伴生 meta 产生/消失"""
    state_file = str(tmp_path / "state.json")
    lock = SingleInstanceLock(state_file)
    lock.acquire()
    assert os.path.exists(lock.lock_path), "acquire 后锁文件应存在"
    assert os.path.exists(lock.meta_path), "acquire 后伴生 meta 应存在"
    lock.release()
    assert not os.path.exists(lock.lock_path), "release 后锁文件应消失"
    assert not os.path.exists(lock.meta_path), "release 后伴生 meta 应消失"


def test_lock_contention_raises_with_holder_info(tmp_path):
    """第二次获取抛 SingleInstanceLockError, 消息含持有者 PID/时间/路径"""
    state_file = str(tmp_path / "state.json")
    lock1 = SingleInstanceLock(state_file)
    lock1.acquire()
    # 等一下确保 meta 起始时间可读
    time.sleep(0.05)
    try:
        lock2 = SingleInstanceLock(state_file)
        with pytest.raises(SingleInstanceLockError) as excinfo:
            lock2.acquire()
        msg = str(excinfo.value)
        # 错误为 ConfigError 子类, 走 CLI 单点捕获 (退出码 1)
        assert isinstance(excinfo.value, ConfigError)
        assert "另一实例已持有锁" in msg
        # 含持有者信息
        assert "PID" in msg
        assert str(os.getpid()) in msg
        assert state_file.replace(".json", ".lock") in msg
    finally:
        lock1.release()


def test_lock_skipped_when_no_lock_flag(tmp_path):
    """QbManager no_lock=True 不创建锁文件 (导出模式)"""
    cfg = FakeConfig()
    cfg.state_file = str(tmp_path / "state.json")
    lock_path = str(tmp_path / "state.lock")
    assert not os.path.exists(lock_path)
    mgr = QbManager("", config=cfg, no_lock=True)
    try:
        assert not os.path.exists(lock_path), "no_lock=True 不应创建锁文件"
        assert mgr._lock is None
    finally:
        if mgr._lock is not None:
            mgr._lock.release()


def test_lock_file_path_derives_from_state_file(tmp_path):
    """state_file 去掉扩展名, 锁文件为 `<base>.lock` (避免与 state 文件同名冲突)"""
    # .json -> .lock
    lock1 = SingleInstanceLock(str(tmp_path / "auto-qb-state.json"))
    assert lock1.lock_path.endswith("auto-qb-state.lock")
    assert lock1.lock_path != str(tmp_path / "auto-qb-state.json.lock")
    # 无扩展名也加 .lock
    lock2 = SingleInstanceLock(str(tmp_path / "state"))
    assert lock2.lock_path.endswith("state.lock")
    # 多点: foo.bar.json -> foo.bar.lock
    lock3 = SingleInstanceLock(str(tmp_path / "foo.bar.json"))
    assert lock3.lock_path.endswith("foo.bar.lock")
