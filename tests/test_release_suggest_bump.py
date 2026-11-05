"""test_release_suggest_bump 测试计划: gitmoji bump 决策器回归网 (计划 26-09-22-2318 v2 §6.2)。

守什么: `.agents/skills/release/scripts/suggest_bump.py` 的决策表语义 ——
✨→minor / 🐛→patch / ⚡️→patch / 破坏性→minor+警示 / 其余不入册 / 永不自动产 major;
版本推算与 CHANGELOG 分段草稿。git 调用经 monkeypatch `run_git` 注入历史 ——
零真实网络、零子进程、零仓库外副作用 (进程内 importlib 挂载, deps-upgrade 先例)。

## 测试计划

- test_classify_subject_table: 决策表参数化 (✨/🐛/⚡️/⚡/♻️/📝/垃圾主题/前导空格)
- test_classify_breaking_variants: 💥 前缀 / 严格大写 BREAKING -> minor+Breaking; 小写 breaking 与 non-breaking 不误报 (评审 R1-F1)
- test_decide_bump_precedence: minor 压过 patch / 仅 patch -> patch / 全 none -> none
- test_decide_counts_and_sections: 计数与分段归集 (breaking 同时计入 minor)
- test_decide_empty_range: 空 subjects(空区间重入场景) -> bump=none 零分段 (评审 R1-13)
- test_next_version_table: 0.2.0 -> 0.3.0 / 0.2.1 / none 原样
- test_next_version_rejects_major_kind: next_version 不提供 major 档, 决策器主体对破坏性也只产 minor
- test_next_version_rejects_non_semver: 当前版本混 local 段/垃圾串 -> RuntimeError
- test_load_version_regex: 版本文件正则单捕获组提取; 多命中/非 SemVer 报错
- test_load_version_regex_group_count: 捕获组 0 个或 2+ 个显式报错 (评审 R1-F6)
- test_changelog_draft_sections: 分段 markdown 草稿 (Breaking 加粗纯文本, 空段省略)
- test_main_error_path_single_line: run_git 失败/非法正则 -> rc=1 且 stderr 单行 [suggest_bump] 前缀 (评审 R1-9/F5)
- test_default_from_ref_guidance: 无 v-tag 时 describe rc=128 转带 --from-ref 指引的停手消息 (评审 R1-F2)
- test_main_empty_range_and_changelog_flag: 空区间提案 none / --emit-changelog 透出草稿段 / 空区间无草稿 (评审 R1-F11/F13)
- test_json_includes_changelog_draft: --json 与 --emit-changelog 同给时草稿并入 JSON 不静默丢 (评审 R1-F3)
- test_major_only_via_explicit_flag: main 层 --major 才产 major, 无旗标时决策表永不给出
- test_default_version_file: [tool.hatch.version].path 读取(有键返回/无键报错) (R2-F3-1)
- test_main_uses_smart_defaults: 不传 --version-file/--version-regex 时走默认链出提案 (R2-F3-1)
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
        (" ✨ 前导空格照常命中", "minor", "Added"),
    ],
)
def test_classify_subject_table(subject, kind, section):
    assert _mod().classify_subject(subject) == (kind, section)


@pytest.mark.parametrize(
    ("subject", "kind", "section"),
    [
        ("💥 (config) 移除旧版限速键", "minor", "Breaking"),
        ("✨ (rules) 新增规则引擎 BREAKING: 旧字段弃用", "minor", "Breaking"),
        # 小写 breaking 是常规表述: 不误报抬 minor(评审 R1-F1)。
        ("🐛 (web) 修复 breaking 兼容缺口", "patch", "Fixed"),
        ("🐛 修复 non-breaking 空格处理", "patch", "Fixed"),
    ],
)
def test_classify_breaking_variants(subject, kind, section):
    assert _mod().classify_subject(subject) == (kind, section)


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


@pytest.mark.parametrize("regex", [r"0\.2\.0", r'(__version__) = "([^"]+)"'])
def test_load_version_regex_group_count(tmp_path, regex):
    # 捕获组 0 个或 2+ 个显式报错, 不静默取组(评审 R1-F6)。
    vf = tmp_path / "ver.py"
    vf.write_text('__version__ = "0.2.0"\n', encoding="utf-8")
    with pytest.raises(RuntimeError, match="恰好一个捕获组"):
        _mod().load_version(vf, regex)


# --------------------------------------------------------------- changelog_draft


def test_changelog_draft_sections():
    sections = {
        "Breaking": ["💥 移除旧键"],
        "Added": ["✨ 面板"],
        "Fixed": ["🐛 修复"],
    }
    draft = _mod().changelog_draft(sections)
    # Breaking 段标题纯文本(code-style 非 ASCII 纪律, 评审 R1-F8); 段序 Breaking < Added < Fixed。
    assert draft.index("### **Breaking**") < draft.index("### Added") < draft.index("### Fixed")
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


def test_decide_empty_range():
    # 空区间(tag 后零提交的重入场景): bump=none 且零分段(评审 R1-F13)。
    verdict = _mod().decide([])
    assert verdict["bump"] == "none"
    assert verdict["counts"] == {"minor": 0, "patch": 0, "none": 0, "breaking": 0}
    assert verdict["sections"] == {}


def test_main_error_path_single_line(tmp_path, monkeypatch, capsys):
    # 错误契约: 任意失败路径 rc=1 且 stderr 单行 [suggest_bump] 前缀(评审 R1-9/F5)。
    mod = _mod()
    vf = tmp_path / "ver.py"
    vf.write_text('__version__ = "0.2.0"\n', encoding="utf-8")

    def boom(args, repo):
        raise RuntimeError("git 炸了(注入)")

    monkeypatch.setattr(mod, "run_git", boom)
    rc = mod.main(["--repo", str(tmp_path), "--version-file", str(vf), "--version-regex", r'__version__ = "([^"]+)"'])
    err = capsys.readouterr().err.strip()
    assert rc == 1
    assert err.startswith("[suggest_bump]") and "\n" not in err

    # 非法正则(re.error)与缺失文件(OSError)同走单行出口, 不裸 traceback。
    rc = mod.main(["--repo", str(tmp_path), "--version-file", str(vf), "--version-regex", "["])
    err = capsys.readouterr().err.strip()
    assert rc == 1 and err.startswith("[suggest_bump]") and "\n" not in err

    rc = mod.main(["--repo", str(tmp_path), "--version-file", str(tmp_path / "nope.py"), "--version-regex", "x"])
    err = capsys.readouterr().err.strip()
    assert rc == 1 and err.startswith("[suggest_bump]") and "\n" not in err


def test_default_from_ref_guidance(tmp_path, monkeypatch):
    # 无 v-tag: describe 的 rc=128 转为带 --from-ref 指引的停手消息(评审 R1-F2)。
    mod = _mod()

    def no_tag(args, repo):
        raise RuntimeError("git describe 失败 rc=128: fatal: No names found")

    monkeypatch.setattr(mod, "run_git", no_tag)
    with pytest.raises(RuntimeError, match="--from-ref"):
        mod.default_from_ref(str(tmp_path))


def test_main_empty_range_and_changelog_flag(tmp_path, monkeypatch, capsys):
    # 空区间提案 none / --emit-changelog 有草稿时透出 / 空区间无草稿段(评审 R1-F11/F13)。
    mod = _mod()
    vf = tmp_path / "ver.py"
    vf.write_text('__version__ = "0.2.0"\n', encoding="utf-8")
    # 先打桩再调 main —— tmp 目录不是 git 仓, 不打桩会真起子进程(POPEN 越界)。
    monkeypatch.setattr(mod, "run_git", lambda args, repo: "v0.2.0" if args[0] == "describe" else "")

    rc = mod.main(
        [
            "--repo",
            str(tmp_path), "--version-file",
            str(vf), "--version-regex", r'__version__ = "([^"]+)"', "--emit-changelog"
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "提案: none" in out and "0.2.0 -> 0.2.0" in out
    assert "### Added" not in out  # 空区间无草稿

    monkeypatch.setattr(mod, "run_git", lambda args, repo: "v0.2.0" if args[0] == "describe" else "✨ A\n🐛 B")
    rc = mod.main(
        [
            "--repo",
            str(tmp_path), "--version-file",
            str(vf), "--version-regex", r'__version__ = "([^"]+)"', "--emit-changelog"
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0 and "### Added" in out and "- ✨ A" in out and "### Fixed" in out


def test_json_includes_changelog_draft(tmp_path, monkeypatch, capsys):
    # --json 与 --emit-changelog 同给: 草稿并入 JSON 字段, 不静默丢(评审 R1-F3)。
    mod = _mod()
    vf = tmp_path / "ver.py"
    vf.write_text('__version__ = "0.2.0"\n', encoding="utf-8")
    monkeypatch.setattr(mod, "run_git", lambda args, repo: "v0.2.0" if args[0] == "describe" else "✨ A\n🐛 B")
    rc = mod.main(
        [
            "--repo",
            str(tmp_path),
            "--version-file",
            str(vf),
            "--version-regex",
            r'__version__ = "([^"]+)"',
            "--json",
            "--emit-changelog",
        ]
    )
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["changelog_draft"].startswith("### Added")
    assert payload["bump"] == "minor" and payload["next"] == "0.3.0"


# --------------------------------------------------------------- 智能默认链 (R2-F3-1)


def test_default_version_file(tmp_path):
    mod = _mod()
    (tmp_path / "ver.py").write_text('__version__ = "0.2.0"\n', encoding="utf-8")
    (tmp_path /
     "pyproject.toml").write_text('[tool.hatch.version]\nsource = "regex"\npath = "ver.py"\n', encoding="utf-8")
    assert mod.default_version_file(str(tmp_path)) == tmp_path / "ver.py"

    (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n', encoding="utf-8")
    with pytest.raises(RuntimeError, match="--version-file"):
        mod.default_version_file(str(tmp_path))


def test_main_uses_smart_defaults(tmp_path, monkeypatch, capsys):
    # 不传 --version-file/--version-regex: 默认链 = [tool.hatch.version].path + dunder 正则。
    mod = _mod()
    (tmp_path / "ver.py").write_text('__version__ = "0.2.0"\n', encoding="utf-8")
    (tmp_path /
     "pyproject.toml").write_text('[tool.hatch.version]\nsource = "regex"\npath = "ver.py"\n', encoding="utf-8")
    monkeypatch.setattr(mod, "run_git", lambda args, repo: "v0.2.0" if args[0] == "describe" else "✨ A\n🐛 B")
    rc = mod.main(["--repo", str(tmp_path)])
    cap = capsys.readouterr()
    assert rc == 0
    assert "提案: minor" in cap.out and "0.2.0 -> 0.3.0" in cap.out
