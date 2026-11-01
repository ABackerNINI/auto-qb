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
import sys
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


# 覆盖率闸: 平台定档 (与根仓 tests/conftest.py::pytest_configure 同口径)。
# 实测 (2026-11-01, issue 26-10-20-2345 实施轮; Linux 侧为本机 WSL Ubuntu-26.04 + uv,
# UV_PROJECT_ENVIRONMENT=~/.venvs/gtm-linux): Windows 侧 99.03% / Linux 侧 98.54%;
# 差额 = gtm/nic.py 的 win32 专属读取函数 (_iph 体 + read_table_rows try 体, 15 语句) 在
# Linux 跑不到。分档: 两侧各留 ~0.5 点余量 (98.5 / 98.0)。
COVERAGE_FLOOR_WIN = 98.5
COVERAGE_FLOOR_OTHER = 98.0


def pytest_configure(config):
    """覆盖率闸按平台定档 —— nic.py 的 win32 专属行在 Linux 跑不到, 单一阈值必有一侧恒红。

    实现照搬根仓同名单点: pytest-cov 在早期解析阶段就建好插件, 只改插件实例的 options
    才生效; 命令行显式传非零 --cov-fail-under 时让路, =0 与 --no-cov 照旧。
    """
    plugin = config.pluginmanager.getplugin("_cov")
    if plugin is None:
        return  # 没开覆盖率 (--no-cov / 无 --cov): 无闸可设
    if getattr(plugin.options, "cov_fail_under", 0):
        return  # 命令行已显式给了非零阈值 —— 让路
    plugin.options.cov_fail_under = COVERAGE_FLOOR_WIN if sys.platform == "win32" else COVERAGE_FLOOR_OTHER


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
