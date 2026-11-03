"""test_deps_upgrade_check_updates 测试计划: deps-upgrade 巡检脚本回归网 (issue 26-11-03-1209)。

守什么: `.agents/skills/deps-upgrade/scripts/check_updates.py` 此前零自动化测试 ——
版本段切分 (`version_segments`)、增量分类 (`delta_kind`)、单个上游源失败降级
(`Unreachable` 不中止整个巡检)全靠人眼。本文件进程内 import 该脚本 (本项目测试
禁止起子进程), 全部网络访问经 monkeypatch 打桩 —— 零真实网络、零仓库外副作用。

## 测试计划

- test_version_segments_parameterized: CalVer / rc 预发布 / v 前缀 / 位数不等 / 非数字段的切分形态
- test_delta_kind_parameterized: none / patch / minor / major-line / pre/tag diff / check (lower) 六类
- test_delta_kind_numeric_not_lexicographic: 1.2.9 -> 1.2.10 按 patch (数字比较而非字典序)
- test_watch_entry_tags_unreachable_degrades: tags 源整体失败 -> 行降级 [unreachable] 不抛异常
- test_watch_entry_single_date_unreachable_degrades: 单条 tag/branch 日期源失败 -> 对应单元格 [unreachable], 行照常
- test_watch_entry_new_version_emits_trigger: 最新 tag 不在支持矩阵 -> 返回联合分析触发行 + 日期取到
- test_pin_deps_single_source_failure_degrades: 单个 PyPI 源失败 -> 该行 [unreachable], 其余行照常计数不涨
- test_pin_deps_counts_updates_and_delta: 正常路径 delta 分类 / 更新计数 / direct-joint-support 列
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".agents" / "skills" / "deps-upgrade" / "scripts" / "check_updates.py"


def _mod():
    """进程内装载 deps-upgrade 的巡检脚本(注册 sys.modules 后再 exec, 只装一次)。"""
    if "deps_upgrade_check_updates" not in sys.modules:
        spec = importlib.util.spec_from_file_location("deps_upgrade_check_updates", SCRIPT)
        assert spec and spec.loader, f"缺少 deps-upgrade skill 脚本: {SCRIPT}"
        mod = importlib.util.module_from_spec(spec)
        sys.modules["deps_upgrade_check_updates"] = mod
        spec.loader.exec_module(mod)
    return sys.modules["deps_upgrade_check_updates"]


# --------------------------------------------------------------- version_segments


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1.2.3", [1, 2, 3]),
        ("2026.11.03", [2026, 11, 3]),  # CalVer: 前导零段按数字取
        ("2.0.0rc1", [2, 0, 0, "rc1"]),  # rc 预发布: 尾段是非数字 token
        ("1.2.3-rc.1", [1, 2, 3, "rc", 1]),
        ("v1.2.3", ["v1", 2, 3]),  # v 前缀带数字粘成一个非数字段
        ("1.2.x", [1, 2, "x"]),  # 非数字段
        ("1.2", [1, 2]),  # 位数不等
    ],
)
def test_version_segments_parameterized(raw, expected):
    assert _mod().version_segments(raw) == expected


@pytest.mark.parametrize(
    ("current", "latest", "expected"),
    [
        ("1.2.3", "1.2.3", "none"),
        ("1.2.2", "1.2.3", "patch"),
        ("1.2.3", "1.3.0", "minor"),
        ("2025.10.1", "2026.1.1", "major-line"),  # CalVer 首段变化 = major-line
        ("1.2.3", "1.3", "minor"),  # 位数不等, 缺段按 0 补
        ("2.0.0rc1", "2.0.0", "pre/tag diff"),  # 数字段全等, 非数字差异
        ("1.2", "1.2.0", "pre/tag diff"),
        ("1.3.0", "1.2.9", "check (lower)"),
    ],
)
def test_delta_kind_parameterized(current, latest, expected):
    assert _mod().delta_kind(current, latest) == expected


def test_delta_kind_numeric_not_lexicographic():
    # 字典序下 "10" < "9"; 必须按数字比较判 patch, 降级判 check (lower)
    mod = _mod()
    assert mod.delta_kind("1.2.9", "1.2.10") == "patch"
    assert mod.delta_kind("1.2.10", "1.2.9") == "check (lower)"


# ------------------------------------------------------------- 失败降级 (watch)


def test_watch_entry_tags_unreachable_degrades(monkeypatch):
    """tags 源整体失败: 该 watch 行降级 [unreachable], 表头与 no-tag 行照常, 不抛异常。"""
    mod = _mod()

    def boom(url, timeout):
        raise mod.Unreachable("URLError: down")

    monkeypatch.setattr(mod, "fetch_json", boom)
    entry = {
        "id": "qb",
        "repo": "qbittorrent/qBittorrent",
        "lines": [{
            "name": "stable",
            "tag_filter": "release-",
            "ref": "master"
        }],
    }
    lines, triggers = mod.check_watch_entry(entry, 1.0, {})
    text = "\n".join(lines)
    assert "[unreachable] tags for qbittorrent/qBittorrent" in text
    assert "| line | latest tag | version | tag date | branch ref | branch head |" in text
    assert "(no tag yet)" in text  # tags 为空 -> 每条 line 降级 no-tag 行
    assert triggers == []


def test_watch_entry_single_date_unreachable_degrades(monkeypatch):
    """单条日期源失败: 只有对应单元格降级 [unreachable], tag 行本身照常产出。"""
    mod = _mod()
    tags = [{"name": "release-5.0.0"}]

    def fake(url, timeout):
        if "/tags?" in url:
            return tags
        raise mod.Unreachable("HTTPError: 502")

    monkeypatch.setattr(mod, "fetch_json", fake)
    entry = {
        "id": "qb",
        "repo": "x/y",
        "lines": [{
            "name": "stable",
            "tag_filter": "release-",
            "ref": "master"
        }],
    }
    lines, triggers = mod.check_watch_entry(entry, 1.0, {})
    text = "\n".join(lines)
    assert "release-5.0.0" in text  # tag 行照常
    assert "[unreachable]" in text  # tag date / branch head 两格降级
    assert triggers == []


def test_watch_entry_new_version_emits_trigger(monkeypatch):
    """最新 tag 版本不在支持矩阵 -> 返回联合分析触发行; 日期取到并截到日期段。"""
    mod = _mod()
    tags = [{"name": "v4.9.9"}]

    def fake(url, timeout):
        if "/tags?" in url:
            return tags
        return {"commit": {"committer": {"date": "2026-01-02T03:04:05Z"}}}

    monkeypatch.setattr(mod, "fetch_json", fake)
    support = {"dep": {"analyzed": ["4.8.x"]}}  # 4.9.9 不匹配 4.8.x 前缀
    entry = {
        "id": "dep",
        "repo": "x/y",
        "version_extract": r"^v(.+)$",
        "lines": [{
            "name": "stable",
            "tag_filter": r"^v",
            "ref": ""
        }],
    }
    lines, triggers = mod.check_watch_entry(entry, 1.0, support)
    assert len(triggers) == 1 and "4.9.9" in triggers[0] and "NEW vs matrix" in triggers[0]
    assert "2026-01-02" in "\n".join(lines)  # fmt_date 截 ISO 日期


# ------------------------------------------------------------- 失败降级 (pin)


def _pin_env(tmp_path, monkeypatch, lock_versions, project_name="auto-qb"):
    """搭 pin 扫描环境: tmp 下写 uv.lock + pyproject.toml, REPO_ROOT 指向 tmp。"""
    mod = _mod()
    lock = tmp_path / "uv.lock"
    lock.write_text(
        "".join(f'[[package]]\nname = "{n}"\nversion = "{v}"\n\n' for n, v in lock_versions.items()),
        encoding="utf-8",
    )
    (tmp_path /
     "pyproject.toml").write_text(f'[project]\nname = "{project_name}"\ndependencies = ["aaaa"]\n', encoding="utf-8")
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
    cfg = {
        "pin": {
            "exempt": []
        },
        "joint": {
            "deps": ["aaaa"]
        },
        "support": [{
            "dep": "bbbb",
            "analyzed": ["1.9.x"]
        }],
        "paths": {
            "lockfile": "uv.lock",
            "pyproject": "pyproject.toml"
        },
    }
    return mod, cfg


def test_pin_deps_single_source_failure_degrades(tmp_path, monkeypatch):
    """单个 PyPI 源失败: 该行 [unreachable] 降级, 其余行照常, 更新计数不被失败行污染。"""
    mod, cfg = _pin_env(tmp_path, monkeypatch, {"aaaa": "1.0.0", "bbbb": "1.0.0"})

    def fake_pypi(name, timeout):
        if name == "aaaa":
            raise mod.Unreachable("HTTPError: 503")
        return "1.0.1", "2026-01-02T10:00:00Z"

    monkeypatch.setattr(mod, "pypi_latest", fake_pypi)
    lines, updates = mod.check_pin_deps(cfg, quick=False, timeout=1.0)
    text = "\n".join(lines)
    aaaa_row = next(ln for ln in lines if ln.startswith("| aaaa "))
    bbbb_row = next(ln for ln in lines if ln.startswith("| bbbb "))
    assert "[unreachable]" in aaaa_row and "Unreachable" in aaaa_row  # 失败行降级并带异常类名
    assert "| 1.0.1 | patch | 2026-01-02 |" in bbbb_row  # 其余行照常
    assert updates == 1  # 只有 bbbb 有更新


def test_pin_deps_counts_updates_and_delta(tmp_path, monkeypatch):
    """正常路径: delta 分类 / 更新计数 / direct 与 joint 标记 / support 列只在有更新时判。"""
    mod, cfg = _pin_env(tmp_path, monkeypatch, {"aaaa": "1.2.3", "bbbb": "2.0.0rc1"})

    def fake_pypi(name, timeout):
        return {"aaaa": ("1.2.3", ""), "bbbb": ("2.0.0", "2026-03-04T00:00:00Z")}[name]

    monkeypatch.setattr(mod, "pypi_latest", fake_pypi)
    lines, updates = mod.check_pin_deps(cfg, quick=False, timeout=1.0)
    aaaa_row = next(ln for ln in lines if ln.startswith("| aaaa "))
    bbbb_row = next(ln for ln in lines if ln.startswith("| bbbb "))
    assert updates == 1  # aaaa 无更新不计
    assert " none " in aaaa_row and aaaa_row.rstrip().endswith("| - |")  # 无更新时 support 恒 '-'
    assert " pre/tag diff " in bbbb_row
    assert bbbb_row.rstrip().endswith("| NEW vs matrix |")  # support 判定 (bbbb 非 direct/joint)
    assert " yes " in aaaa_row  # aaaa 是 direct + joint
