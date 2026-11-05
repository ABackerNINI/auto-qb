"""test_hatch_build 测试计划: wheel BUILD_ID 侧车钩子守阵 (计划 26-09-22-2318 v2 §4.2 双路径)。

守什么: `hatch_build.py` 的两件事 —— build_id_from_git 三态(g<hash> 净树 / g<hash>.dirty 脏树 /
None git 不可得)与 BuildHook.initialize 的 extra_metadata 映射方向({源文件: dist-info 相对目标},
写反则 wheel 静默丢 BUILD_ID, 与 release.build note 记档的静默陷阱同型)。subprocess.run 经
monkeypatch 注入 —— 零真实 git 调用、零子进程; 钩子本体用 stub self(root=...) 调未绑定方法。

## 测试计划

- test_build_id_from_git_clean: 净树 -> g<short> 无后缀
- test_build_id_from_git_dirty: status 非空 -> .dirty 后缀
- test_build_id_from_git_git_missing: rev-parse 失败/超时异常 -> None(构建不失败)
- test_build_id_from_git_empty_sha: rev-parse rc=0 但输出空 -> None
- test_initialize_mapping_direction: initialize 把 {tmp/BUILD_ID: BUILD_ID} 塞进 build_data, 临时文件内容带换行
- test_initialize_git_missing_noop: git 不可得时 build_data 不动(保守默认)
- test_hook_requires_hatchling_base: 防漂移——BuildHook 必须继承 hatchling 的 BuildHookInterface
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "hatch_build.py"


def _mod():
    if "hatch_build_hook" not in sys.modules:
        # hatchling 是构建期隔离依赖(运行态 venv 没有): 先给个最小桩模块, 让钩子文件可挂载。
        try:
            import hatchling.builders.hooks.plugin.interface  # noqa: F401
        except ModuleNotFoundError:
            fake = types.ModuleType("hatchling")
            builders = types.ModuleType("hatchling.builders")
            hooks = types.ModuleType("hatchling.builders.hooks")
            plugin = types.ModuleType("hatchling.builders.hooks.plugin")
            interface = types.ModuleType("hatchling.builders.hooks.plugin.interface")

            class BuildHookInterface:  # 最小桩基类(本测试不实例化它, 只需 import 成立)
                pass

            interface.BuildHookInterface = BuildHookInterface
            fake.builders = builders
            builders.hooks = hooks
            hooks.plugin = plugin
            plugin.interface = interface
            for name, m in (
                ("hatchling", fake),
                ("hatchling.builders", builders),
                ("hatchling.builders.hooks", hooks),
                ("hatchling.builders.hooks.plugin", plugin),
                ("hatchling.builders.hooks.plugin.interface", interface),
            ):
                sys.modules.setdefault(name, m)
        spec = importlib.util.spec_from_file_location("hatch_build_hook", SCRIPT)
        assert spec and spec.loader, f"缺少 hatch_build.py: {SCRIPT}"
        mod = importlib.util.module_from_spec(spec)
        sys.modules["hatch_build_hook"] = mod
        spec.loader.exec_module(mod)
    return sys.modules["hatch_build_hook"]


class _Proc:
    """subprocess.CompletedProcess 替身。"""
    def __init__(self, returncode: int, stdout: str):
        self.returncode = returncode
        self.stdout = stdout


def _patch_git(monkeypatch, mod, rev_parse: _Proc | Exception, status: _Proc):
    calls = []

    def fake_run(args, **kwargs):
        calls.append(tuple(args))
        if "rev-parse" in args:
            if isinstance(rev_parse, Exception):
                raise rev_parse
            return rev_parse
        if "status" in args:
            return status
        raise AssertionError(f"unexpected subprocess call: {args}")

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    return calls


# --------------------------------------------------------------- build_id_from_git


def test_build_id_from_git_clean(monkeypatch):
    mod = _mod()
    _patch_git(monkeypatch, mod, _Proc(0, "abc1234\n"), _Proc(0, ""))
    assert mod.build_id_from_git("somewhere") == "gabc1234"


def test_build_id_from_git_dirty(monkeypatch):
    mod = _mod()
    _patch_git(monkeypatch, mod, _Proc(0, "abc1234\n"), _Proc(0, " M hatch_build.py\n"))
    assert mod.build_id_from_git("somewhere") == "gabc1234.dirty"


def test_build_id_from_git_git_missing(monkeypatch):
    mod = _mod()
    _patch_git(monkeypatch, mod, _Proc(128, ""), _Proc(0, ""))
    assert mod.build_id_from_git("somewhere") is None
    _patch_git(monkeypatch, mod, FileNotFoundError("no git"), _Proc(0, ""))
    assert mod.build_id_from_git("somewhere") is None  # 构建不失败(保守默认)


def test_build_id_from_git_empty_sha(monkeypatch):
    mod = _mod()
    _patch_git(monkeypatch, mod, _Proc(0, "\n"), _Proc(0, ""))
    assert mod.build_id_from_git("somewhere") is None


# --------------------------------------------------------------- BuildHook.initialize


class _StubHook:
    """最小 self 替身: 只带 root, 调未绑定的 initialize/finalize(不 import hatchling)。"""
    def __init__(self, root: Path):
        self.root = str(root)


def _make_hook(monkeypatch, mod, tmp_path, rev: _Proc, status: _Proc) -> types.SimpleNamespace:
    hook = _StubHook(tmp_path)
    monkeypatch.setattr(mod.subprocess, "run", lambda args, **kw: rev if "rev-parse" in args else status)
    return types.SimpleNamespace(
        initialize=lambda build_data: mod.BuildHook.initialize(hook, "standard", build_data),
        finalize=lambda build_data: mod.BuildHook.finalize(hook, "standard", build_data, []),
        hook=hook,
    )


def test_initialize_mapping_direction(tmp_path, monkeypatch):
    # 映射方向 = {源文件路径: dist-info 相对目标}; 写反则 wheel 静默丢 BUILD_ID(R2-F3-2)。
    mod = _mod()
    api = _make_hook(monkeypatch, mod, tmp_path, _Proc(0, "abc1234\n"), _Proc(0, ""))
    build_data: dict = {}
    api.initialize(build_data)
    em = build_data["extra_metadata"]
    assert list(em.values()) == ["BUILD_ID"], f"目标键必须是 BUILD_ID(相对 dist-info), 实际 {em}"
    (source_path, ) = em.keys()
    assert Path(source_path).read_text(encoding="utf-8") == "gabc1234\n"
    # finalize 清临时目录(幂等, atexit 兜底仍在)
    api.finalize(build_data)
    assert not Path(source_path).parent.exists()


def test_initialize_git_missing_noop(tmp_path, monkeypatch):
    mod = _mod()
    api = _make_hook(monkeypatch, mod, tmp_path, _Proc(128, ""), _Proc(0, ""))
    build_data: dict = {}
    api.initialize(build_data)
    assert build_data == {}, "git 不可得时不得改动 build_data(保守默认)"


def test_hook_requires_hatchling_base():
    # 防漂移: BuildHook 必须继承 hatchling 的 BuildHookInterface(钩子能被 hatchling 加载的前提)。
    src = SCRIPT.read_text(encoding="utf-8")
    assert "BuildHookInterface" in src and "from hatchling.builders.hooks.plugin.interface import" in src
