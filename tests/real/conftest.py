"""真机实测轨的 pytest 基座 —— 守卫 fixture + 伪 tracker + 临时目录。

本目录已随测试树三分并入 `tests/real`, 落在 `pytest.ini` 的 `testpaths` 下: 靠本文件无条件
打上的 `real_machine` 标记, 由 addopts 的 `-m "not real_machine"` 统一过滤, 主套件零扰动。
跑真机一律走 `real.run` / `real.suite`(task id, 内部 `-m real_machine` 反向选择), 不要裸 pytest
—— 裸跑会跳过守卫 fixture 之外的环境核验(例如实例没起时应该给一句人话, 而不是 30 条红)。
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import guard, instances  # noqa: E402
from lib.tracker import FakeTracker  # noqa: E402


def pytest_collection_modifyitems(items):
    """给本目录收集到的用例打 real_machine 标 —— 钩子无条件安装, 仅按路径限定作用域。

    pytest 对已加载的每个 conftest 都调用本钩子并传入**全部** items, 不按目录裁剪;
    故必须自己按路径过滤, 否则 tests/unit 也会被误标而被 ini 的 -m 一起 deselect。
    """
    real_root = Path(__file__).resolve().parent
    for item in items:
        path = getattr(item, "path", None) or Path(str(item.fspath))
        if path == real_root or real_root in path.parents:
            item.add_marker(pytest.mark.real_machine)


@pytest.fixture(scope="session")
def env():
    """三层守卫: 白名单 → 归零 → 看门狗。任一层不过直接跳过整片(环境问题不是用例失败)。"""
    reports, qbs, protected = {}, {}, {}
    for port in (instances.PRIMARY, instances.SECONDARY):
        try:
            reports[port] = guard.check_port(port)
            qb = instances.make(port)
            qb.version()  # 探活: 起不来就别往下走
            # disconnected ⇒ 本轮所有"零流量/零 announce"结论都是假的, 直接拦在门口
            reports[port]["connection"] = guard.check_online(qb)
            # 自造种子不在保护面也不由守卫暂停 —— 它们由用例自己管(issue 26-11-21-0639)
            protected[port] = set(guard.snapshot(qb, skip_tags=(guard.REAL_FAKE_TAG, )))
            qbs[port] = qb
        except Exception as exc:
            pytest.skip(f"实例 {port} 不可用或守卫不通过: {exc}")
    dogs = {p: guard.Watchdog(qbs[p], protected[p]) for p in qbs}
    for d in dogs.values():
        d.start()
    yield {"qbs": qbs, "protected": protected, "reports": reports, "dogs": dogs}
    for d in dogs.values():
        d.stop()
    violations = {p: d.violations for p, d in dogs.items() if d.violations}
    assert not violations, f"运行期真实种子被激活(看门狗已暂停): {violations}"


@pytest.fixture()
def primary(env):
    return env["qbs"][instances.PRIMARY]


@pytest.fixture()
def secondary(env):
    return env["qbs"][instances.SECONDARY]


@pytest.fixture()
def workdir(request):
    """本地工作目录 —— 不用 pytest 的 tmp_path: qB 要真读这些文件, 慢盘/沙箱重定向会让
    用例假红(同 pitfalls/testing/tmpdir.md 的教训)。TMPDIR 自 2026-11-02 起由
    tests/unit/_tmp_bootstrap.py 探测(R→H→系统temp, 计划 26-11-02-0657), 但 tests/real 需要
    的是仓库本地确定性目录, 与探测无关, 故仍用 .work/。"""
    d = Path(__file__).resolve().parent / ".work" / re.sub(r"\W+", "_", request.node.name)
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True, exist_ok=True)
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture()
def tracker():
    t = FakeTracker(interval=5).start()
    yield t
    t.stop()


LIMIT_KEYS = ("dl_limit", "up_limit", "alt_dl_limit", "alt_up_limit", "use_alt_speed_limits")
L2_RATE = 256 * 1024  # L2 互传用固定限速: 太快则「持续上传」观测不到, 太慢则用例拖成几分钟


@pytest.fixture()
def transfer_limits(env):
    """把两实例的限速临时钉成 L2_RATE, 结束时逐字恢复。

    测试实例原本带 dl_limit=1024(1 KiB/s) 的下载限速 —— 那是给真实种子留的, 但会让
    L2 互传 2MB 需要半小时。这里**不改环境语义, 只临时覆盖并在 finally 里还原**
    (还原值取自用例开始前的快照, 不是硬编码)。
    """
    saved = {port: {k: qb.prefs().get(k) for k in LIMIT_KEYS} for port, qb in env["qbs"].items()}
    for qb in env["qbs"].values():
        qb.set_prefs(
            dl_limit=L2_RATE, up_limit=L2_RATE, alt_dl_limit=L2_RATE, alt_up_limit=L2_RATE, use_alt_speed_limits=False
        )
    yield L2_RATE
    for port, qb in env["qbs"].items():
        qb.set_prefs(**saved[port])
