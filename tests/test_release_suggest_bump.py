"""test_release_suggest_bump 测试计划: gitmoji bump 决策器回归网 (计划 26-09-22-2318 v2 §6.2)。

守什么: `.agents/skills/release/scripts/suggest_bump.py` 的决策表语义 ——
✨→minor / 🐛→patch / ⚡️→patch / 破坏性→minor+警示 / 其余不入册 / 永不自动产 major;
版本推算与 CHANGELOG 分段草稿。git 调用经 monkeypatch `run_git` 注入历史 ——
零真实网络、零子进程、零仓库外副作用 (进程内 importlib 挂载, deps-upgrade 先例)。

## 测试计划

- test_classify_subject_table: 决策表参数化 (✨/🐛/⚡️/⚡/♻️/📝/垃圾主题)
- test_classify_breaking_variants: 💥 前缀 / BREAKING 字样 / breaking+emoji 组合 -> minor+Breaking
- test_decide_bump_precedence: minor 压过 patch / 仅 patch -> patch / 全 none -> none
- test_decide_counts_and_sections: 计数与分段归集 (breaking 同时计入 minor)
- test_next_version_table: 0.2.0 -> 0.3.0 / 0.2.1 / none 原样
- test_next_version_rejects_major_kind: next_version 不提供 major 档, 决策器主体对破坏性也只产 minor
- test_next_version_rejects_non_semver: 当前版本混 local 段/垃圾串 -> RuntimeError
- test_load_version_regex: 版本文件正则单捕获组提取; 多命中/非 SemVer 报错
- test_changelog_draft_sections: 分段 markdown 草稿 (Breaking 加粗, 空段省略)
- test_major_only_via_explicit_flag: main 层 --major 才产 major, 无旗标时决策表永不给出
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".agents" / "skills" / "release" / "scripts" / "suggest_bump.py"


def _mod():
    """进程内装载 release skill 的决策器脚本 (注册 sys.modules 后 exec, 只装一次)。"""
    if "release_suggest_bump" not in sys.modules:
        spec = importlib.util.spec_from_file_location("release_suggest_bump", SCRIPT)
        assert spec and spec.loader, f"缺少 release skill 脚本: {SCRIPT}"
        mod = importlib.util.module_from_spec(spec)
        sys.modules["release_suggest_bump"] = mod
        spec.loader.exec_module(mod)
    return sys.modules["release_suggest_bump"]


# --------------------------------------------------------------- classify_subject


@pytest.mark.parametrize(
    ("subject", "kind", "section"),
    [
        ("✨ (webui) 新增导出面板", "minor", "Added"),
        ("🐛 修复转移删源失败误判整条失败", "patch", "Fixed"),
        ("⚡️ (gtm) 取数专用 3s 超时", "patch", "Changed"),
        ("⚡ (gtm) 无 VS16 变体同档", "patch", "Changed"),
        ("♻️ (core) 分支0遮蔽跳检 dedup 前插", "none", None),
        ("📝 (memory-bank) 重写 8K 口径文档", "none", None),
        ("🗑️ 弃置过期计划文档", "none", None),
        ("普通主题无 emoji", "none", None),
    ],
)
def test_classify_subject_table(subject, kind, section):
    assert _mod().classify_subject(subject) == (kind, section)


@pytest.mark.parametrize(
    "subject",
    [
        "💥 (config) 移除旧版限速键",
        "✨ (rules) 新增规则引擎 BREAKING: 旧字段弃用",
        "🐛 (web) 修复 breaking 兼容缺口",
    ],
)
def test_classify_breaking_variants(subject):
    assert _mod().classify_subject(subject) == ("minor", "Breaking")


# --------------------------------------------------------------- decide


def test_decide_bump_precedence():
    mod = _mod()
    assert mod.decide(["✨ 新功能", "🐛 修复"])["bump"] == "minor"
    assert mod.decide(["🐛 修复", "⚡️ 性能"])["bump"] == "patch"
    assert mod.decide(["📝 文档", "♻️ 重构", "✅ 测试"])["bump"] == "none"


def test_decide_counts_and_sections():
    verdict = _mod().decide(["✨ A", "✨ B", "🐛 C", "⚡️ D", "📝 E", "💥 F"])
    assert verdict["bump"] == "minor"
    assert verdict["counts"] == {"minor": 3, "patch": 2, "none": 1, "breaking": 1}
    assert verdict["sections"]["Added"] == ["✨ A", "✨ B"]
    assert verdict["sections"]["Fixed"] == ["🐛 C"]
    assert verdict["sections"]["Changed"] == ["⚡️ D"]
    assert verdict["sections"]["Breaking"] == ["💥 F"]


# --------------------------------------------------------------- next_version / load_version


@pytest.mark.parametrize(
    ("current", "bump", "expected"),
    [
        ("0.2.0", "minor", "0.3.0"),
        ("0.2.0", "patch", "0.2.1"),
        ("0.2.0", "none", "0.2.0"),
        ("0.9.9", "patch", "0.9.10"),
    ],
)
def test_next_version_table(current, bump, expected):
    assert _mod().next_version(current, bump) == expected


def test_next_version_rejects_major_kind():
    # 永不自动跨 major: next_version 不提供 major 档, 决策器主体也产不出它。
    mod = _mod()
    with pytest.raises(RuntimeError, match="未知 bump 档位"):
        mod.next_version("0.2.0", "major")
    assert mod.decide(["💥 破坏性"])["bump"] == "minor"


@pytest.mark.parametrize("current", ["0.2.0+dev", "v0.2.0", "0.2", "garbage"])
def test_next_version_rejects_non_semver(current):
    with pytest.raises(RuntimeError, match="纯 SemVer"):
        _mod().next_version(current, "patch")


def test_load_version_regex(tmp_path):
    mod = _mod()
    vf = tmp_path / "ver.py"
    vf.write_text('__version__ = "0.2.0"\n', encoding="utf-8")
    assert mod.load_version(vf, r'__version__ = "([^"]+)"') == "0.2.0"

    vf.write_text('__version__ = "0.2.0"\n__version__ = "0.3.0"\n', encoding="utf-8")
    with pytest.raises(RuntimeError, match="须恰好 1 处"):
        mod.load_version(vf, r'__version__ = "([^"]+)"')

    vf.write_text('__version__ = "0.2.0+dev"\n', encoding="utf-8")
    with pytest.raises(RuntimeError, match="纯 SemVer"):
        mod.load_version(vf, r'__version__ = "([^"]+)"')


# --------------------------------------------------------------- changelog_draft


def test_changelog_draft_sections():
    sections = {
        "Breaking": ["💥 移除旧键"],
        "Added": ["✨ 面板"],
        "Fixed": ["🐛 修复"],
    }
    draft = _mod().changelog_draft(sections)
    assert draft.index("⚠️ **Breaking**") < draft.index("### Added") < draft.index("### Fixed")
    assert "- **💥 移除旧键**" in draft
    assert "### Changed" not in draft  # 空段省略


# --------------------------------------------------------------- main 层 (--major 旗标与 git 注入)


def test_major_only_via_explicit_flag(tmp_path, monkeypatch, capsys):
    mod = _mod()
    vf = tmp_path / "ver.py"
    vf.write_text('__version__ = "0.2.0"\n', encoding="utf-8")
    monkeypatch.setattr(mod, "run_git", lambda args, repo: "v0.2.0" if args[0] == "describe" else "✨ A\n🐛 B")

    rc = mod.main(["--repo", str(tmp_path), "--version-file", str(vf), "--version-regex", r'__version__ = "([^"]+)"'])
    assert rc == 0
    out = capsys.readouterr().out
    assert "提案: minor" in out and "0.2.0 -> 0.3.0" in out

    rc = mod.main(
        ["--repo",
         str(tmp_path), "--version-file",
         str(vf), "--version-regex", r'__version__ = "([^"]+)"', "--json"]
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["bump"] == "minor" and payload["next"] == "0.3.0" and payload["range"] == "v0.2.0..HEAD"

    rc = mod.main(
        ["--repo",
         str(tmp_path), "--version-file",
         str(vf), "--version-regex", r'__version__ = "([^"]+)"', "--major"]
    )
    out = capsys.readouterr().out
    assert "提案: major" in out and "0.2.0 -> 1.0.0" in out
