"""RM01 片内基座: 只做「环境还活着 + 真实种子没被点着」的只读核验。

不挂 `tests-real/conftest.py` 的 `env` fixture: 那套会**暂停**两实例的全部种子并起看门狗 ——
对 RM01 是多余的副作用(本片一个种子都不碰)。这里只读: 端口白名单 + 实例在线 + 36595 的
真实种子必须仍在非活跃态。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib import guard, instances  # noqa: E402

ACTIVE = {"uploading", "downloading", "stalledUP", "stalledDL", "queuedUP", "queuedDL",
          "forcedUP", "forcedDL", "checkingUP", "checkingDL", "moving", "metadl"}

_SERIAL_LOCK = Path(__file__).resolve().parents[1] / ".work" / "rm01" / "serial.lock"


@pytest.fixture(autouse=True)
def serial():
    """跨进程串行: 本片每条都要抢端口 + 起真实进程 + 写同一个注册表值。

    `pytest.ini` 的 addopts 是 `-n 8`, 默认 `--dist load` 下 `xdist_group` 标记**不生效**,
    9 条会摊到 8 个 worker 并行 ⇒ 互相抢 39000-39999 段(实测: 前一条刚停的进程还没放端口,
    后一条就 bind 到同一个, 10048)。官方跑法 `real.suite` 传 `-n 0` 本就没这问题, 但直接
    `pytest tests-real/...` 的人也该拿到稳定结果 —— 一把文件锁比"记得加 -n 0"可靠。
    """
    import filelock

    _SERIAL_LOCK.parent.mkdir(parents=True, exist_ok=True)
    with filelock.FileLock(str(_SERIAL_LOCK), timeout=900):
        yield


@pytest.fixture(scope="module", autouse=True)
def environment():
    """开工前核一次: 实例在、连接在线、真实种子没在跑。任一不过 ⇒ 整片 skip(环境问题不是用例失败)。"""
    for port in (instances.PRIMARY, instances.SECONDARY):
        try:
            guard.check_port(port)
            qb = instances.make(port)
            qb.version()
            guard.check_online(qb)
        except Exception as exc:  # noqa: BLE001 —— 环境问题一律 skip, 给一句人话
            pytest.skip(f"实例 {port} 不可用: {exc}")

    primary = instances.make(instances.PRIMARY)
    active = [t["name"] for t in primary.torrents() if t["state"] in ACTIVE]
    assert not active, f"36595 的真实种子有活跃的, 本片不该在此时跑: {active[:5]}"
