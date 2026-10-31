"""RM06 片内基座: 只做「环境还活着 + 真实种子没被点着」的只读核验(与 RM03/RM04/RM05 同口径)。

不挂 `tests-real/conftest.py` 的 `env` fixture: 那套会**暂停**两实例的全部种子并起看门狗 ——
RM06 的八条只依赖「36596 在线且空库」(产品进程只连 36596; HR 取数通道数据面全部发生在
127.0.0.1 回环, 打标/站点文件全落在自造假种子与用例临时 data_dir 里; 真实种子所在的
36595 只在守卫里出现), 归零对它是多余的副作用。这里只读: 端口白名单 + 实例在线 +
36595 的真实种子必须仍在非活跃态。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib import guard, instances  # noqa: E402

ACTIVE = {
    "uploading", "downloading", "stalledUP", "stalledDL", "queuedUP", "queuedDL", "forcedUP", "forcedDL", "checkingUP",
    "checkingDL", "moving", "metadl"
}

_SERIAL_LOCK = Path(__file__).resolve().parents[1] / ".work" / "rm06" / "serial.lock"


@pytest.fixture(autouse=True)
def serial():
    """跨进程串行: 本片每条都要起真实产品进程(还占 39000-39999 段 web 端口与发现端口)。

    `pytest.ini` 的 addopts 是 `-n 8`, 默认 `--dist load` 下 `xdist_group` 标记**不生效**
    (RM01 实测), 直跑 pytest 会互相抢端口; 官方跑法 `real.suite` 传 `-n 0` 本就没问题,
    但一把文件锁比"记得加 -n 0"可靠 —— 照抄 rm05_tracker_tags/conftest.py。
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
