"""_tmp_bootstrap 自举的回归阵(计划 26-11-02-0657)。

防两件事:
1. 候选根字面量散落 —— TMP_ROOT_CANDIDATES 必须全局唯一, 别处不得复制盘符/标记;
2. 探测/拒收/幂等的核心行为漂移(本进程内只能验幂等口与标记判定;
   rc=4 拒收与锁的端到端已在本计划实施记录里实测, 这里留进程级用例)。

## 测试计划
- test_candidates_single_source: 候选根字面量全仓库唯一, 不得复制到第二处
- test_candidates_order_is_r_h_system: 固定顺序 R→H→系统 temp 回落(None)
- test_bootstrap_mark_recognition: 路径含标记即自举值, 系统 temp / H:\Temp 不算
- test_external_tmpdir_rejected_rc4: 外部 TMPDIR ⇒ SystemExit(4) + 拒收文案
- test_idempotent_bootstrap_value_accepted: 继承的自举值幂等复用, 不重探测
- test_lock_zombie_dual_condition: 僵尸判定 —— pid 死 / pid 活但 CreateTime 不符
- test_retarget_cov_data_file: coverage 改 _filename 保后缀, combining 改 data_file, 未自举时 no-op
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

import _tmp_bootstrap as tb

REPO = Path(__file__).resolve().parent.parent


def test_candidates_single_source():
    """TMP_ROOT_CANDIDATES 字面量(盘符+标记组合)全仓库唯一, 不得复制到第二处。"""
    offenders: list[str] = []
    pat = re.compile(r'TMP_ROOT_CANDIDATES\s*=\s*\(')
    for p in REPO.rglob("*.py"):
        if ".venv" in p.parts or ".git" in p.parts:
            continue
        if p.samefile(REPO / "tests" / "_tmp_bootstrap.py") or p.samefile(Path(__file__)):
            continue
        try:
            if pat.search(p.read_text(encoding="utf-8", errors="ignore")):
                offenders.append(str(p))
        except OSError:
            continue
    assert not offenders, f"候选根定义散落: {offenders}"


def test_candidates_order_is_r_h_system():
    """固定顺序 R→H→系统回落(None), 与用户拍板口径一致。"""
    cands = list(tb.TMP_ROOT_CANDIDATES)
    assert cands[0][0] == "R:\\" and cands[1][0] == "H:\\"
    assert cands[-1][0] is None, "最后一级必须是系统 temp 回落(None)"


def test_bootstrap_mark_recognition():
    assert tb._is_bootstrap_path(os.environ["TMPDIR"])  # 本进程已被自举接管
    assert not tb._is_bootstrap_path("C:\\Windows\\Temp")
    assert not tb._is_bootstrap_path("H:\\Temp")


def test_external_tmpdir_rejected_rc4(monkeypatch, capsys):
    """外部 TMPDIR(不含标记)→ SystemExit(4) + 拒收文案; 进程级端到端实测见计划实施记录。"""
    monkeypatch.setattr(tb, "_INSTANCE_ROOT", None)
    monkeypatch.setenv("TMPDIR", "H:\\Temp-not-marked")
    with pytest.raises(SystemExit) as ei:
        tb._acquire_instance_root()
    assert ei.value.code == 4
    assert "外部 TMPDIR 拒收" in capsys.readouterr().err


def test_idempotent_bootstrap_value_accepted(monkeypatch):
    """含标记的 TMPDIR(继承自举值, xdist worker/嵌套 pytest 场景)→ 幂等复用不重探测。"""
    monkeypatch.setattr(tb, "_INSTANCE_ROOT", None)
    marked = os.environ["TMPDIR"]  # 本进程已被自举接管, 即合法样本
    monkeypatch.setenv("TMPDIR", marked)
    assert tb._acquire_instance_root() == Path(marked)


def test_lock_zombie_dual_condition(tmp_path):
    """僵尸判定: pid 死 → 僵尸; pid 活 + CreateTime 不符 → 僵尸(PID 复用)。"""
    d = tmp_path / "lock-probe"
    d.mkdir()
    assert tb._lock_zombie(d, {"pid": "99999999", "create_time": "0"})
    me = os.getpid()
    assert not tb._lock_zombie(d, {"pid": str(me), "create_time": str(tb._proc_create_time(me) or 0)})
    assert tb._lock_zombie(d, {"pid": str(me), "create_time": "1"})  # 同人不同皮


def test_retarget_cov_data_file(tmp_path, monkeypatch):
    """coverage 重定向: 主 cov 改写已缓存的 _filename(保留原后缀), combining 改 config.data_file。

    为什么必须改 _filename 而不是 config.data_file: pytest-cov 在 conftest 导入前已
    start(), CoverageData 已缓存完整文件名 —— 实测探针见 _tmp_bootstrap.retarget_cov_data_file。
    """
    root = tmp_path / "inst"
    root.mkdir()
    monkeypatch.setattr(tb, "_INSTANCE_ROOT", root)

    class _Data:
        _basename = r"C:\repo\.coverage"
        _filename = r"C:\repo\.coverage.NINI.pid1.XXXX"

    class _Cfg:
        data_file = r"C:\repo\.coverage"

    class _Cov:
        def __init__(self):
            self._data = _Data()
            self.config = _Cfg()

    class _Ctl:
        def __init__(self):
            self.cov = _Cov()
            self.combining_cov = _Cov()

    ctl = _Ctl()

    class _PM:
        def get_plugin(self, name):
            class _P:
                cov_controller = ctl

            return _P()

    class _Config:
        pluginmanager = _PM()

    tb.retarget_cov_data_file(_Config())
    target = str(root / "cov")
    assert ctl.cov._data._filename == target + ".NINI.pid1.XXXX"
    assert ctl.combining_cov.config.data_file == target

    # 无覆盖率插件 / 未自举: 静默 no-op(不炸)
    monkeypatch.setattr(tb, "_INSTANCE_ROOT", None)
    tb.retarget_cov_data_file(_Config())
