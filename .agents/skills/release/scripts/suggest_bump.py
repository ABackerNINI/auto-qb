#!/usr/bin/env python
"""gitmoji -> SemVer bump 决策器 (release skill · 通用件, 零项目事实)。

决策表 = semantic-release 决策语义移植到 gitmoji 历史 (计划 26-09-22-2318 v2 §6.2):
    ✨ -> minor (Added)      🐛 -> patch (Fixed)      ⚡️ -> patch (Changed)
    破坏性标记 (💥 前缀 / 严格大写 BREAKING 字样) -> minor + 警示 (0.x 语义; **永不自动跨 major**)
    其余 gitmoji -> 无 bump 不入册

所有项目事实走参数 (通用性契约: 移植到另一项目本脚本零改动):
    仓库根 / 当前版本文件与正则 / 起算 ref (默认 = 最近的 v<数字> 形态 tag)。

用法:
    python suggest_bump.py --repo <root> --version-file <path> --version-regex <re>
                           [--from-ref REF] [--major] [--json] [--emit-changelog]

输出 (人读): 提案 / 计数 / next / 分段预览。
    --json          完整结构 (机器消费, release.bump task 用)
    --emit-changelog  可直接粘进 CHANGELOG.md [Unreleased] 的 markdown 段
退出码: 0 正常 (含 bump=none) / 1 参数或环境错误。
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

# 决策表: gitmoji 前缀 -> (bump 档位, CHANGELOG 段)。⚡️ 实为 ⚡ + VS16, startswith 两种都命中。
DECISION_TABLE: dict[str, tuple[str, str]] = {
    "✨": ("minor", "Added"),
    "🐛": ("patch", "Fixed"),
    "⚡": ("patch", "Changed"),
}
BREAKING_EMOJI = "💥"
# 严格大写形态才判破坏性: 小写 breaking 在 "non-breaking"/"breaking 兼容缺口" 等否定或常规
# 表述里常见, 误报会把 patch 抬成 minor + 虚假警示(评审 R1-F1)。💥 前缀仍是主判定。
BREAKING_PATTERN = re.compile(r"\bBREAKING\b")
SEMVER_PATTERN = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
# 未显式给 --version-regex 时的默认: __version__ dunder 行(单/双引号都吃)。
# 走默认而非 task 传参 —— 引擎 shell 拼接下"含空格又含双引号"的参数无法安全过境。
DEFAULT_VERSION_REGEX = r'__version__\s*=\s*["\']([^"\']+)["\']'

# bump 档位优先级: minor > patch > none (永不含 major —— major 只走显式 --major 旗标)。
_KIND_ORDER = {"none": 0, "patch": 1, "minor": 2}


def run_git(args: list[str], repo: str) -> str:
    """git 只读调用单点 (测试经 monkeypatch 本函数注入历史, 不起真子进程)。"""
    proc = subprocess.run(
        ["git", "-C", repo, *args], capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} 失败 rc={proc.returncode}: {proc.stderr.strip()}")
    return proc.stdout


def load_version(path: Path, version_regex: str) -> str:
    """从版本文件按正则取当前版本 (正则须含恰好一个捕获组)。"""
    pattern = re.compile(version_regex)
    if pattern.groups != 1:
        raise RuntimeError(f"--version-regex 须恰好一个捕获组, 当前 {pattern.groups} 个: {version_regex}")
    text = path.read_text(encoding="utf-8")
    matches = pattern.findall(text)
    if len(matches) != 1:
        raise RuntimeError(f"版本文件 {path} 按正则匹配到 {len(matches)} 处 (须恰好 1 处): {version_regex}")
    version = matches[0] if not isinstance(matches[0], tuple) else matches[0][0]
    if not SEMVER_PATTERN.match(version):
        raise RuntimeError(f"当前版本 {version!r} 不是纯 SemVer 三段数字")
    return version


def default_from_ref(repo: str) -> str:
    """默认起算点 = 最近 v<数字> 形态 tag (无 tag 即报错, 让调用方显式给 --from-ref)。"""
    try:
        out = run_git(["describe", "--tags", "--match", "v[0-9]*", "--abbrev=0"], repo).strip()
    except RuntimeError as exc:
        # describe 无匹配 tag 时 rc=128, 原始 git fatal 对调用方无指引价值(评审 R1-F2), 换设计好的停手指引。
        raise RuntimeError("仓库无 v<数字> 形态 tag, 请用 --from-ref 显式给起算点") from exc
    if not out:
        raise RuntimeError("仓库无 v<数字> 形态 tag, 请用 --from-ref 显式给起算点")
    return out


def classify_subject(subject: str) -> tuple[str, str | None]:
    """单条提交主题 -> (bump 档位, CHANGELOG 段)。纯函数, 守阵主战场。"""
    stripped = subject.strip()
    is_breaking = stripped.startswith(BREAKING_EMOJI) or bool(BREAKING_PATTERN.search(stripped))
    for emoji, (kind, section) in DECISION_TABLE.items():
        if stripped.startswith(emoji):
            return ("minor" if is_breaking else kind, "Breaking" if is_breaking else section)
    if is_breaking:
        return ("minor", "Breaking")
    return ("none", None)


def decide(subjects: list[str]) -> dict:
    """决策表主体: 主题列表 -> 档位/计数/分段。纯函数。"""
    counts = {"minor": 0, "patch": 0, "none": 0, "breaking": 0}
    sections: dict[str, list[str]] = {}
    for subject in subjects:
        kind, section = classify_subject(subject)
        counts[kind] += 1
        if section == "Breaking":
            counts["breaking"] += 1  # breaking 同时计入 minor (它走 minor + 警示)
        if section is not None:
            sections.setdefault(section, []).append(subject.strip())
    bump = "none"
    for candidate in ("minor", "patch"):
        if counts[candidate] > 0:
            bump = candidate
            break
    return {"bump": bump, "counts": counts, "sections": sections}


def next_version(current: str, bump: str) -> str:
    """按档位推下一版本。major 只在调用方显式传 --major 时由 main() 换算, 本函数不产 major。"""
    match = SEMVER_PATTERN.match(current)
    if not match:
        raise RuntimeError(f"当前版本 {current!r} 不是纯 SemVer 三段数字")
    major, minor, patch = (int(part) for part in match.groups())
    if bump == "minor":
        return f"{major}.{minor + 1}.0"
    if bump == "patch":
        return f"{major}.{minor}.{patch + 1}"
    if bump == "none":
        return current
    raise RuntimeError(f"未知 bump 档位: {bump!r}")


def changelog_draft(sections: dict[str, list[str]]) -> str:
    """分段 -> Keep a Changelog markdown 段 (Breaking 段加粗警示)。"""
    order = ["Breaking", "Added", "Fixed", "Changed"]
    headings = {"Breaking": "### **Breaking**", "Added": "### Added", "Fixed": "### Fixed", "Changed": "### Changed"}
    blocks = []
    for key in order:
        items = sections.get(key)
        if not items:
            continue
        lines = [headings[key]]
        if key == "Breaking":
            lines += [f"- **{item}**" for item in items]
        else:
            lines += [f"- {item}" for item in items]
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def preview(sections: dict[str, list[str]], per_section: int = 5) -> list[str]:
    """人读分段预览 (每段截前 per_section 条)。"""
    lines = []
    for key in ("Added", "Fixed", "Changed", "Breaking"):
        items = sections.get(key)
        if not items:
            continue
        shown = ", ".join(items[:per_section])
        more = f" …+{len(items) - per_section}" if len(items) > per_section else ""
        lines.append(f"{key}[{len(items)}]: {shown}{more}")
    return lines


def default_version_file(repo: str) -> Path:
    """默认版本文件 = pyproject [tool.hatch.version].path(hatchling 单源约定)。"""
    pyproject = Path(repo) / "pyproject.toml"
    with pyproject.open("rb") as fh:
        data = tomllib.load(fh)
    path = data.get("tool", {}).get("hatch", {}).get("version", {}).get("path")
    if not path:
        raise RuntimeError("pyproject 无 [tool.hatch.version].path, 请显式给 --version-file")
    return pyproject.parent / path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="gitmoji -> SemVer bump 决策器 (release skill)")
    parser.add_argument("--repo", required=True, help="仓库根 (git -C 的目标)")
    parser.add_argument("--version-file", type=Path, default=None, help="当前版本所在文件(默认 = [tool.hatch.version].path)")
    parser.add_argument("--version-regex", default=None, help="版本提取正则, 须恰好一个捕获组(默认 = __version__ dunder 行)")
    parser.add_argument("--from-ref", default=None, help="起算 ref (默认 = 最近 v<数字> tag)")
    parser.add_argument("--major", action="store_true", help="显式 major 放行 (人工拍板专用, 永不自动)")
    parser.add_argument("--json", action="store_true", dest="as_json", help="输出完整 JSON 结构")
    parser.add_argument("--emit-changelog", action="store_true", help="输出 CHANGELOG [Unreleased] markdown 段")
    ns = parser.parse_args(argv)

    # stdout/stderr 锁 UTF-8: 分段预览与草稿含 gitmoji, cp936 管道直跑会 UnicodeEncodeError
    # (评审 R1-F7; 经 commands 引擎调用时 _CHILD_ENV 已注入, reconfigure 幂等无害)。
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    try:
        current = load_version(
            ns.version_file or default_version_file(ns.repo), ns.version_regex or DEFAULT_VERSION_REGEX
        )
        from_ref = ns.from_ref or default_from_ref(ns.repo)
        subjects = [
            line for line in run_git(["log", f"{from_ref}..HEAD", "--pretty=%s"], ns.repo).splitlines() if line.strip()
        ]
        verdict = decide(subjects)
    except (RuntimeError, re.error, OSError, tomllib.TOMLDecodeError) as exc:
        # 单行错误契约: re.error(非法 --version-regex) / OSError(版本文件缺失、git 缺失)一并收口(评审 R1-F5)。
        print(f"[suggest_bump] {exc}", file=sys.stderr)
        return 1

    if ns.major:
        # major 档只存在于显式旗标路径 (人工拍板专用): major+1.0.0, 决策表永不产出。
        bump = "major"
        match = SEMVER_PATTERN.match(current)
        nxt = f"{int(match.group(1)) + 1}.0.0"
    else:
        bump = verdict["bump"]
        nxt = next_version(current, bump)
    result = {
        "current": current,
        "bump": bump,
        "next": nxt,
        "breaking": verdict["counts"]["breaking"] > 0,
        "counts": verdict["counts"],
        "sections": verdict["sections"],
        "range": f"{from_ref}..HEAD",
    }

    if ns.emit_changelog:
        result["changelog_draft"] = changelog_draft(verdict["sections"])

    if ns.as_json:
        # --emit-changelog 同给时草稿并入 JSON 字段, 不静默丢(评审 R1-F3)。
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    print(f"提案: {result['bump']}" + (" (显式 --major)" if ns.major else ""))
    print(
        f"计数: minor={verdict['counts']['minor']} patch={verdict['counts']['patch']} "
        f"none={verdict['counts']['none']} breaking={verdict['counts']['breaking']}"
    )
    print(f"next: {current} -> {nxt}")
    for line in preview(verdict["sections"]):
        print(line)
    if ns.emit_changelog:
        draft = changelog_draft(verdict["sections"])
        if draft:
            print()
            print(draft)
    return 0


if __name__ == "__main__":
    sys.exit(main())
