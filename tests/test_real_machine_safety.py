"""真机轨安全边界守卫(issue 26-11-02-1208 复验).

## 测试计划
2026-11-02 issue 26-11-02-1208 复验(L490 前置改显式入口, 移除隐藏卷依赖):
- test_tests_real_source_has_no_hidden_volume_access: 扫描 tests-real/ 源码, 禁止
  FindFirstVolumeW/FindNextVolumeW/卷 GUID 字面量/隐藏卷 junction 构造函数名;
  一旦有人再引入隐藏卷路径即红。
- test_small_target_guard_rejects_unsafe_paths: 入口守卫拒绝 UNC/无盘符/系统盘/
  reparse point/hidden 属性; 普通临时目录放行。
- test_small_target_missing_env_fails_with_instructions: 未设入口环境变量时显式失败,
  提示里含准备指引(不是 skip)。
- test_label_forbidden_keywords: Recovery/System/EFI 类卷标关键词判定。
"""
from __future__ import annotations

import importlib.util
import os
import stat
import sys
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


@pytest.mark.skipif(sys.platform != "win32", reason="Windows 盘符/卷标/属性语义")
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


@pytest.mark.skipif(sys.platform != "win32", reason="Windows 盘符/卷标/属性语义")
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
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    (real_dir / "link").mkdir()
    monkeypatch.setattr(mod, "_is_link", lambda p: Path(p).name == "link")
    with pytest.raises(AssertionError, match="reparse"):
        mod.assert_safe_target(str(real_dir / "link"))

    (real_dir / "hid").mkdir()
    orig_attrs = mod._get_attrs
    monkeypatch.setattr(
        mod,
        "_get_attrs",
        lambda p:
        (stat.FILE_ATTRIBUTE_HIDDEN | stat.FILE_ATTRIBUTE_DIRECTORY if Path(p).name == "hid" else orig_attrs(p)),
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
