"""真机轨安全边界守卫(issue 26-11-02-1208 复验).

## 测试计划
2026-11-02 issue 26-11-02-1208 复验(L490 前置改显式入口, 移除隐藏卷依赖):
- test_tests_real_source_has_no_hidden_volume_access: 扫描 tests-real/ 源码, 禁止
  FindFirstVolumeW/FindNextVolumeW/卷 GUID 字面量/隐藏卷 junction 构造函数名;
  一旦有人再引入隐藏卷路径即红。
- test_small_target_guard_rejects_unsafe_paths: 入口守卫拒绝 UNC/无盘符/系统盘/
  reparse point/hidden 属性; 普通临时目录放行 (受控桩分支把 SystemDrive 指向非系统
  盘符且桩掉祖先属性, 不依赖 tmp_path 所在卷/目录属性)。
- test_small_target_missing_env_fails_with_instructions: 未设入口环境变量时显式失败,
  提示里含准备指引(不是 skip)。
- test_label_forbidden_keywords: Recovery/System/EFI 类卷标关键词判定。

2026-11-06 issue 26-11-06-0448 修复(real.down 强杀 → WebAPI app/shutdown 优雅退出):
- test_real_down_source_has_no_forced_kill: 扫 tests-real/runner.py 禁止进程强杀字面量,
  并要求 cmd_down 走 .shutdown(); 旧实现(Stop-Process -Force)必红。
- test_cmd_down_dry_run_never_touches_webapi: dry-run 零副作用, 不核验进程也不发 API。
- test_cmd_down_uses_webapi_shutdown_and_waits_for_port_release: 正常路径只发一次 shutdown,
  带 pid 回执并等端口释放。
- test_cmd_down_skips_when_port_not_listening: 实例没起 -> skip, 不误发 shutdown。
- test_cmd_down_refuses_non_test_instance: 镜像路径核验失败 -> rc=1 且不发 shutdown。
- test_cmd_down_fails_closed_on_api_error: API 失败 -> rc=1, 不回退强杀。
- test_cmd_down_reports_timeout_without_force_kill: 等退出超时 -> rc=1 如实报, 不强杀。
- test_qb_shutdown_is_post_with_empty_body: app/shutdown 是空体 POST(不是 GET)。
- test_qb_default_calls_stay_get: 默认读端点仍是 GET, 防 _open 改动带偏既有调用。
"""
from __future__ import annotations

import importlib.util
import os
import stat
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TESTS_REAL = ROOT / "tests-real"


def _load_small_target():
    p = TESTS_REAL / "lib" / "small_target.py"
    spec = importlib.util.spec_from_file_location("real_small_target_guard", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.skipif(sys.platform != "win32", reason="Windows 盘符/卷标/属性语义")  # owner: abacker
def test_tests_real_source_has_no_hidden_volume_access():
    forbidden = (
        "FindFirstVolumeW",
        "FindNextVolumeW",
        "FindFirstVolume(",
        "FindNextVolume(",
        "small_volume_junction",
        "_volume_roots",
        "Volume{",
    )
    hits = []
    for f in sorted(TESTS_REAL.rglob("*.py")):
        text = f.read_text(encoding="utf-8", errors="ignore")
        for token in forbidden:
            if token in text:
                hits.append(f"{f.relative_to(ROOT)}: {token}")
    assert not hits, "真机轨源码出现隐藏卷枚举/挂接路径(已废弃并禁止):\n" + "\n".join(hits)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows 盘符/卷标/属性语义")  # owner: abacker
def test_small_target_guard_rejects_unsafe_paths(tmp_path, monkeypatch):
    mod = _load_small_target()
    with pytest.raises(AssertionError, match="UNC"):
        mod.assert_safe_target("\\\\?\\Volume{deadbeef}\\")
    with pytest.raises(AssertionError, match="绝对路径"):
        mod.assert_safe_target("C:relative-real-machine-no-drive")
    sysdrive = os.environ.get("SystemDrive") or "C:"
    with pytest.raises(AssertionError, match="系统卷"):
        mod.assert_safe_target(sysdrive + "\\")

    # reparse point / hidden 用受控桩验证判定分支, 不在真实盘上建 junction/改属性
    # (真机轨里的显式入口守卫本身会读真实属性; 这里只守控制流, 避免测试自己造副作用)
    # 本机临时目录可能落在系统卷 (TMP=C:), 守卫会在系统卷检查处提前拒绝; 受控桩分支
    # 先把 SystemDrive 指向不存在的盘符, 使控制流测试不依赖 tmp_path 所在卷。
    monkeypatch.setenv("SystemDrive", "Z:")
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    (real_dir / "link").mkdir()
    monkeypatch.setattr(mod, "_is_link", lambda p: Path(p).name == "link")
    # 祖先目录在真实盘上可能带 hidden/system 属性 (本机 tmp 落在 AppData 下), 受控桩一律返回 0,
    # 只让 "hid" 命中 hidden 分支 —— 否则会先撞祖先属性检查, 测不到目标分支。
    monkeypatch.setattr(mod, "_get_attrs", lambda p: 0)
    with pytest.raises(AssertionError, match="reparse"):
        mod.assert_safe_target(str(real_dir / "link"))

    (real_dir / "hid").mkdir()
    monkeypatch.setattr(
        mod,
        "_get_attrs",
        lambda p: (stat.FILE_ATTRIBUTE_HIDDEN | stat.FILE_ATTRIBUTE_DIRECTORY if Path(p).name == "hid" else 0),
    )
    with pytest.raises(AssertionError, match="hidden"):
        mod.assert_safe_target(str(real_dir / "hid"))


def test_small_target_missing_env_fails_with_instructions(monkeypatch):
    mod = _load_small_target()
    monkeypatch.delenv(mod.SMALL_TARGET_ENV, raising=False)
    with pytest.raises(AssertionError) as ei:
        mod.require_small_target(134217728)
    msg = str(ei.value)
    assert mod.SMALL_TARGET_ENV in msg
    assert "准备" in msg


def test_label_forbidden_keywords():
    mod = _load_small_target()
    for label in ("Recovery", "SYSTEM", "EFI", "系统恢复"):
        assert mod.label_forbidden(label), f"应判为禁用卷标: {label}"
    assert not mod.label_forbidden("Data")


# ---- real.down 进程安全守阵 (issue 26-11-06-0448) ----
# 关停测试实例只许走 qB 自己的 WebAPI app/shutdown: 外部强杀既触 AGENTS.md 进程红线,
# 又会跳过 fastresume/state 的优雅写回, 与 relocate 下线窗口机制相抵触。
FORCE_KILL_TOKENS = ("Stop-Process", "taskkill", "TerminateProcess", "os.kill", ".kill(", "-Force")


def _blocked_subprocess_run(*args, **kwargs):
    """守阵用例绝不允许真实起外部进程 —— 红验时旧实现会走到 PowerShell 强杀路径。

    只替换 runner 模块自己的 subprocess 引用(不改标准库模块对象), 避免污染同进程其它用例。
    """
    pytest.fail("守阵用例禁止真实起外部进程(会触进程安全红线)")


class _FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return b""


def _load_qb():
    p = TESTS_REAL / "lib" / "qb.py"
    spec = importlib.util.spec_from_file_location("_real_qb_under_test", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_runner(monkeypatch, ports=(36596, )):
    """隔离加载 tests-real/runner.py: 注入假 lib 包, 全程不触 netstat / qB / 系统进程。

    runner 模块级会 sys.path.insert, 先把 sys.path 换成可恢复的副本; `from lib import ...`
    由 sys.modules 里的假包承接, 不把真实 lib 命名空间带进主套件。
    """
    exe = {p: f"C:/qb-testing/{p}/qbittorrent.exe" for p in ports}
    fake_guard = types.SimpleNamespace(
        WHITELIST_PORTS=tuple(ports),
        EXE=exe,
        GuardError=type("GuardError", (RuntimeError, ), {}),
        check_port=lambda port: {
            "port": port,
            "pid": 4242,
            "image": exe[port]
        },
    )
    fake_lib = types.ModuleType("lib")
    fake_lib.guard = fake_guard
    fake_lib.env_registry = types.SimpleNamespace(ENVIRONMENTS={})
    fake_lib.instances = types.SimpleNamespace(make=lambda port: None)
    monkeypatch.setitem(sys.modules, "lib", fake_lib)
    monkeypatch.setattr(sys, "path", list(sys.path))
    spec = importlib.util.spec_from_file_location("_real_runner_under_test", TESTS_REAL / "runner.py")
    mod = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, mod)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "subprocess", types.SimpleNamespace(run=_blocked_subprocess_run))
    return mod, fake_guard


def _down_args(port="36596", dry_run=False):
    return types.SimpleNamespace(port=port, dry_run=dry_run)


def _fake_qb(calls):
    return types.SimpleNamespace(shutdown=lambda: calls.append("shutdown"))


def test_real_down_source_has_no_forced_kill():
    text = (TESTS_REAL / "runner.py").read_text(encoding="utf-8")
    hits = [token for token in FORCE_KILL_TOKENS if token in text]
    assert not hits, f"真机轨 runner.py 出现进程强杀形态 {hits}; 关停实例只走 WebAPI app/shutdown"
    assert ".shutdown()" in text, "cmd_down 必须调用 WebAPI app/shutdown 优雅退出"


def test_cmd_down_dry_run_never_touches_webapi(monkeypatch, capsys):
    calls = []
    mod, fake_guard = _load_runner(monkeypatch)
    monkeypatch.setattr(fake_guard, "check_port", lambda port: pytest.fail("dry-run 不该核验进程"))
    monkeypatch.setattr(mod, "_qb", lambda port: _fake_qb(calls))
    assert mod.cmd_down(_down_args(dry_run=True)) == 0
    assert calls == []
    assert "app/shutdown" in capsys.readouterr().out


def test_cmd_down_uses_webapi_shutdown_and_waits_for_port_release(monkeypatch, capsys):
    calls = []
    mod, _ = _load_runner(monkeypatch)
    monkeypatch.setattr(mod, "_qb", lambda port: _fake_qb(calls))
    monkeypatch.setattr(mod, "_wait_port", lambda port, timeout=40.0: True)
    monkeypatch.setattr(mod, "_wait_port_gone", lambda port, timeout=60.0: True)
    assert mod.cmd_down(_down_args()) == 0
    assert calls == ["shutdown"]
    out = capsys.readouterr().out
    assert "优雅退出" in out and "pid=4242" in out


def test_cmd_down_skips_when_port_not_listening(monkeypatch, capsys):
    calls = []
    mod, fake_guard = _load_runner(monkeypatch)
    monkeypatch.setattr(mod, "_qb", lambda port: _fake_qb(calls))
    monkeypatch.setattr(mod, "_wait_port", lambda port, timeout=40.0: False)
    monkeypatch.setattr(fake_guard, "check_port", lambda port: pytest.fail("端口没起不该核验进程"))
    assert mod.cmd_down(_down_args()) == 0
    assert calls == []
    assert "未在跑" in capsys.readouterr().out


def test_cmd_down_refuses_non_test_instance(monkeypatch, capsys):
    calls = []
    mod, fake_guard = _load_runner(monkeypatch)

    def reject(port):
        raise fake_guard.GuardError(f"端口 {port} 被 {exe} 占用 —— 拒跑(可能是生产 qB)")

    exe = "C:/Program Files/qBittorrent/qbittorrent.exe"
    monkeypatch.setattr(fake_guard, "check_port", reject)
    monkeypatch.setattr(mod, "_qb", lambda port: _fake_qb(calls))
    monkeypatch.setattr(mod, "_wait_port", lambda port, timeout=40.0: True)
    assert mod.cmd_down(_down_args()) == 1
    assert calls == []
    assert "[FAIL]" in capsys.readouterr().out


def test_cmd_down_fails_closed_on_api_error(monkeypatch, capsys):
    def boom():
        raise RuntimeError("port 36596 /app/shutdown -> 401")

    mod, _ = _load_runner(monkeypatch)
    monkeypatch.setattr(mod, "_qb", lambda port: types.SimpleNamespace(shutdown=boom))
    monkeypatch.setattr(mod, "_wait_port", lambda port, timeout=40.0: True)
    assert mod.cmd_down(_down_args()) == 1
    assert "app/shutdown" in capsys.readouterr().out


def test_cmd_down_reports_timeout_without_force_kill(monkeypatch, capsys):
    calls = []
    mod, _ = _load_runner(monkeypatch)
    monkeypatch.setattr(mod, "_qb", lambda port: _fake_qb(calls))
    monkeypatch.setattr(mod, "_wait_port", lambda port, timeout=40.0: True)
    monkeypatch.setattr(mod, "_wait_port_gone", lambda port, timeout=60.0: False)
    assert mod.cmd_down(_down_args()) == 1
    out = capsys.readouterr().out
    assert "超时" in out and "未强杀" in out


def test_qb_shutdown_is_post_with_empty_body(monkeypatch):
    mod = _load_qb()
    seen = {}

    def fake_open(req, timeout=None):
        seen.update(method=req.get_method(), url=req.full_url, data=req.data)
        return _FakeResponse()

    monkeypatch.setattr(mod._OPENER, "open", fake_open)
    mod.Qb(36596).shutdown()
    assert seen["method"] == "POST"
    assert seen["url"].endswith("/api/v2/app/shutdown")
    assert seen["data"] == b""


def test_qb_default_calls_stay_get(monkeypatch):
    mod = _load_qb()
    seen = {}

    def fake_open(req, timeout=None):
        seen.update(method=req.get_method(), url=req.full_url, data=req.data)
        return _FakeResponse()

    monkeypatch.setattr(mod._OPENER, "open", fake_open)
    mod.Qb(36596).version()
    assert seen["method"] == "GET"
    assert seen["url"].endswith("/api/v2/app/version")
    assert seen["data"] is None
