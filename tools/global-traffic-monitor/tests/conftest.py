"""工具侧测试 hermetic 守阵: 任何用例不得改动真实用户级指针目录.

背景 (26-10-20-1316 计划实施期发现): 身份层 (gtm.identity) 与存储层 (gtm.storage)
各自 import 了 pointer_dir, 两个命名空间各持一份引用 —— 用例只 patch 其中一个时,
另一个仍指向真实 %LOCALAPPDATA%/global-traffic-monitor, primary.json/deferred.json
就会落进真实目录 (指向早已删除的 pytest 临时目录, 每轮全量再生).

本 conftest 以 autouse 夹具对每个用例做前后快照比对 (文件名 + 内容哈希):
真实指针目录多文件/少文件/内容变化即红. snapshot 取值口径与 gtm.storage.pointer_dir
一致但不经过被测命名空间 (防patch自批).
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest


def _real_pointer_dir() -> Path:
    """真实用户级指针目录 (平台口径同 gtm.storage.pointer_dir, 但不走被测代码)."""
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
    return Path(base) / "global-traffic-monitor"


def _snapshot(root: Path) -> dict[str, str]:
    if not root.is_dir():
        return {}
    snap: dict[str, str] = {}
    for entry in sorted(root.iterdir()):
        if entry.is_file():
            try:
                raw = entry.read_bytes()
            except OSError:
                # 真实实例运行中: instance.lock 被独占持有 (share none), 跨进程读必 EPERM;
                # 记不可读标记 (整轮运行期间持有态稳定, 前后一致即不误报).
                snap[entry.name] = "<unreadable>"
            else:
                snap[entry.name] = hashlib.sha256(raw).hexdigest()
        else:
            snap[entry.name] = "<dir>"
    return snap


@pytest.fixture(autouse=True)
def _real_pointer_dir_unchanged():
    """每个用例前后真实指针目录快照一致; 用例尾 teardown 先于本夹具 (逆序),
    monkeypatch 还原后采样, patch 自批无效."""
    before = _snapshot(_real_pointer_dir())
    yield
    after = _snapshot(_real_pointer_dir())
    assert after == before, (
        f"真实用户级指针目录被测试改动 (hermetic 违约): before={before} after={after}; "
        "gtm.identity.pointer_dir 与 gtm.storage.pointer_dir 是两个命名空间, 必须同址重定向"
    )
