#!/usr/bin/env python3
"""Status drift guard: what the progress files claim as done vs what the linked documents say.

Purpose (2026-10-31): machine-check the drift between a status enum and the actual
completion state around it.
Same disease the 2026-09-27 implementation audit (reports/26-09-27-1547) evidenced: a status
layer asserted something the referenced layer contradicted (slices said "waiting for commit"
while the commit had already landed; slice and plan meta went stale together). Here the
claiming layer is the progress whitelist sections ("done" bullets that backlink documents),
and the referenced layer is the status field itself: tasks `**Status:**`, issues
`<meta name="issue-status">`, plans/reports `<meta name="doc-status">`. A "done" bullet that
backlinks an Open document is the doc-status-meta.md failure shape: the status layer is wrong
(or the claim is) and it must RING, not be silently collected.

Data sources / scope:
  progress   `memory-bank/progress/implemented-*.md` + `progress/known-bugs.md` (the latter
             only sections whose heading starts with the judgement word "已修复");
             `roadmap.md` / `suggestions.md` / `evolution.md` and every other progress file
             are excluded entirely.
  sections   headings of level >= 2 whose title starts with "已实现" or "已修复" (a trailing
             emoji/suffix is tolerated -- match by prefix, never by full string; real files
             decorate the heading). The H1 file title is NOT a section (it describes the
             file topic, not a completion claim). Links are collected only inside these
             sections.
  targets    markdown link targets resolved relative to the source file; only targets that
             land in `memory-bank/tasks/*.md`, `issues/*.html`, `plans/*.html`,
             `reports/*.html` count. External URLs, pure anchors, attachments and other
             families (pitfalls, testing, progress itself) are ignored.
  status     tasks: `**Status:**` (4-word vocab TASK_STATUSES); issues: `<meta
             name="issue-status">`; plans/reports: `<meta name="doc-status">` (5-word vocab
             DOC_STATUSES). Unreadable status (missing field / out-of-vocab value / missing
             file) is reported as an anomaly and counts as hard fail -- per the
             doc-status-meta.md pit, a broken status layer must ring, never drop silently.

Four output tiers:
  A (hard fail)  backlink target status == Open: the progress file claims a "done" the
                 target still calls Open. Hint printed once: flip the target to In Progress
                 via `commands run kb.status` when the claim is genuinely partial.
  B (hard fail)  issue cover badge text != meta issue-status. Boundary: a MISSING badge is
                 NOT a violation (some legacy issues carry no cover badge at all); only
                 badge-present-but-contradicting-meta fails. A parenthetical suffix on the
                 badge (e.g. "Open(常驻)") is treated as consistent with the meta status
                 (display annotation, not a different status).
  C (list only)  same backlinks, target status == In Progress: printed as a manual-review
                 list; never affects the exit code.
  D (list only)  `tasks/*.md` and `issues/*.html` bodies whose status is Open/In Progress
                 and whose text contains a done-style word (已完成|已修复|已落地|已实现|
                 已上线). Exemptions: negation prefixes (未/尚未/没有/没), date-prefixed
                 lines, fenced code blocks, inline code. Low-confidence list; never affects
                 the exit code.

Exit code: 1 iff tier A, tier B or the anomalies are non-empty; otherwise 0. Tiers C/D only
print.

Usage (from repo root; `<skill-dir>` = the dir the memory-bank skill was loaded from):
    python <skill-dir>/scripts/check_status_drift.py --check    status drift guard, rc 1 on drift
    python <skill-dir>/scripts/check_status_drift.py --safety   smoke probe (is bare run a real action)
A bare run behaves exactly like `--check`: this checker is pure read-only (no write mode
exists, so there is nothing a --check gate could distinguish), --check is kept only so
kb.check can wire it in the same shape as its sibling checkers.

## 测试计划 (T2 implements these in tests/test_memory_bank.py)
- test_status_drift_scripts_import_cleanly: module import stays clean (extend the existing
  test_kb_scripts_import_cleanly name list with "check_status_drift").
- test_status_drift_sections_are_whitelisted: only level>=2 headings starting with the
  judgement words (emoji/suffix tolerated) open a link-collecting section; H1 file titles
  and non-whitelisted sections are ignored; known-bugs.md only honours 已修复 sections.
- test_status_drift_link_targets_resolved: `../tasks/...` style relative targets resolve to
  the four families; external/anchor/attachment/other-family links are ignored; a markdown
  link title after the target does not break parsing; unresolved-in-family targets are
  reported as anomalies, not crashes.
- test_status_drift_gate_a_flags_open_backlinks: a whitelisted-section link to an Open
  target yields one `src:line -> target (status: Open)` row plus the kb.status hint; rc == 1.
- test_status_drift_gate_b_badge_vs_meta: badge text contradicting meta issue-status fails;
  a missing badge is tolerated (documented boundary); an "Open(常驻)" style parenthetical
  suffix matches meta "Open"; missing/out-of-vocab meta is an anomaly (rc 1).
- test_status_drift_gate_c_never_fails: In Progress backlinks are printed and rc stays 0
  when only tier C (and D) rows exist.
- test_status_drift_gate_d_exemptions: negation prefixes / date lines / fenced code / inline
  code are exempt; a naked done-word in an Open task body is listed; rc unaffected.
- test_status_drift_anomaly_on_unreadable_status: missing `**Status:**` / status meta or an
  out-of-vocab value yields an anomaly row and rc == 1 (doc-status-meta.md: ring, not drop).
"""

from __future__ import annotations

import argparse
import html as html_mod
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import (  # noqa: E402
    DOC_STATUSES,
    TASK_STATUSES,
    find_root,
    html_meta,
    md_field,
    rel_posix,
    resolve_mb_dir,
)

# --------------------------------------------------------------------------- judgement words
# These Chinese literals ARE the criteria (not comments): section whitelist, done-style
# assertion words and their negation prefixes. Everything else in this file is ASCII.

SECTION_PREFIXES = ("已实现", "已修复")
KNOWN_BUGS_ONLY_PREFIX = "已修复"  # known-bugs.md only honours this section prefix
DONE_WORDS = ("已完成", "已修复", "已落地", "已实现", "已上线")
DONE_WORD_RE = re.compile("|".join(DONE_WORDS))
NEGATION_PREFIXES = ("尚未", "没有", "未", "没")
OPEN_STATUS = "Open"
IN_PROGRESS_STATUS = "In Progress"
ACTIVE_STATUSES = (OPEN_STATUS, IN_PROGRESS_STATUS)

# --------------------------------------------------------------------------- parsing rules
# All regexes below were fixed against real samples (2026-10-31):
#   section heading : "## " + judgement prefix + "(emoji, notes)"  (suffix is common)
#   backlink        : "(2026-10-30; plan [..](../plans/..html), archive [..](../tasks/..md))"
#   issue badge     : '<div class="item"><div class="k">状态</div><div class="v">'
#                     '<span class="badge">Done</span></div></div>'  (badge class may carry a
#                     colour variant such as "badge go" / "badge ok"; "badge type" holds the
#                     issue type, but it never appears inside the 状态 item, so anchoring on
#                     the 状态 item keeps it out)
#   task status     : "**Status:** Done"  (line 3 of the archive head)
#   html status     : '<meta name="issue-status" content="Done">' / doc-status for plans/reports

HEADING_RE = re.compile(r"^(#{2,6})\s+(.*?)\s*$")  # sections start at level >= 2 (H1 = file title)
MD_LINK_RE = re.compile(r"\[[^\]]*\]\(\s*([^)\s]+)")  # capture the target, drop an optional title
SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")  # http(s):, mailto:, ... -> external
BADGE_RE = re.compile(r'<div class="k">\s*状态\s*</div>\s*<div class="v">\s*<span class="badge[^"]*">([^<]*)</span>')
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
TAG_RE = re.compile(r"<[^>]+>")
CODE_TAG_RE = re.compile(r"<code\b[^>]*>.*?</code>", re.DOTALL)
# date-prefixed lines are immutable history log entries (same wording-guard exemption)
LINE_PREFIX_RE = re.compile(r"^\s*(?:[-*+>|]\s*|\#{1,6}\s*)*\*{0,2}\s*")
DATE_HEAD_RE = re.compile(r"^(?:\d{4}-\d{2}-\d{2}|\d{2}-\d{2}-\d{2})")

# family dirs (first path component under memory-bank) -> (kind, required suffix)
FAMILY_BY_DIR = {
    "tasks": ("task", ".md"),
    "issues": ("issue", ".html"),
    "plans": ("plan", ".html"),
    "reports": ("report", ".html"),
}
PROGRESS_DIR = "progress"
KNOWN_BUGS_NAME = "known-bugs.md"
IMPLEMENTED_GLOB = "implemented-*.md"

GATE_A_HINT = "确属部分完成 -> commands run kb.status 翻 In Progress 后重跑"


@dataclass(frozen=True)
class Backlink:
    """One markdown link from a whitelisted progress section into a status-bearing family."""

    src_rel: str  # repo-relative posix path of the progress file
    lineno: int  # 1-based line of the link occurrence
    target: Path  # absolute resolved target path
    kind: str  # FAMILY_BY_DIR kind: task | issue | plan | report


def _read(path: Path) -> str:
    return path.read_bytes().decode("utf-8", errors="replace")


def iter_whitelisted_lines(lines: list[str], known_bugs_only: bool) -> list[tuple[int, str]]:
    """Lines inside whitelisted sections as [(lineno, line)].

    A section opens at a level>=2 heading whose title starts with an allowed prefix and
    closes at the next heading of level <= its own (deeper subsections stay inside).
    `known_bugs_only` restricts the allowed prefix to "已修复" (known-bugs.md scope).
    """
    allowed = (KNOWN_BUGS_ONLY_PREFIX, ) if known_bugs_only else SECTION_PREFIXES
    out: list[tuple[int, str]] = []
    level = 0  # 0 = outside any whitelisted section
    for lineno, line in enumerate(lines, 1):
        m = HEADING_RE.match(line)
        if m:
            this_level = len(m.group(1))
            title = m.group(2).strip()
            if level and this_level <= level:
                level = 0  # close the current section before considering a new one
            if not level and title.startswith(allowed):
                level = this_level
        elif level:
            out.append((lineno, line))
    return out


def resolve_family_target(raw: str, src: Path, mb: Path) -> tuple[Path, str] | None:
    """Link target text -> (absolute path, kind) when it lands in a status-bearing family.

    Pure anchors, external URLs and targets outside the four families return None.
    """
    target = raw.split("#", 1)[0].strip()
    if not target or SCHEME_RE.match(target):
        return None
    path = (src.parent / target).resolve()
    try:
        rel = path.relative_to(mb.resolve())
    except ValueError:
        return None
    parts = rel.parts
    if len(parts) < 2 or parts[0] not in FAMILY_BY_DIR:
        return None
    kind, suffix = FAMILY_BY_DIR[parts[0]]
    if path.suffix != suffix:
        return None
    return path, kind


def collect_backlinks(mb: Path) -> tuple[list[Backlink], list[str]]:
    """Scan progress whitelist sections -> (backlinks, in-family targets that do not exist)."""
    directory = mb / PROGRESS_DIR
    backlinks: list[Backlink] = []
    missing: set[str] = set()
    if not directory.is_dir():
        return backlinks, missing
    sources = sorted(directory.glob(IMPLEMENTED_GLOB))
    known_bugs = directory / KNOWN_BUGS_NAME
    if known_bugs.is_file():
        sources.append(known_bugs)
    for src in sources:
        rel = rel_posix(src, mb.parent)
        known_bugs_only = src.name == KNOWN_BUGS_NAME
        lines = _read(src).split("\n")
        seen: set[tuple[str, int, str]] = set()
        for lineno, line in iter_whitelisted_lines(lines, known_bugs_only):
            for m in MD_LINK_RE.finditer(line):
                hit = resolve_family_target(m.group(1), src, mb)
                if hit is None:
                    continue
                target, kind = hit
                key = (rel, lineno, str(target))
                if key in seen:
                    continue
                seen.add(key)
                if not target.is_file():
                    missing.add(f"{rel}:{lineno}: [status-unreadable] target missing: {rel_posix(target, mb.parent)}")
                    continue
                backlinks.append(Backlink(src_rel=rel, lineno=lineno, target=target, kind=kind))
    return backlinks, sorted(missing)


def read_status(path: Path, kind: str, cache: dict[str, tuple[str | None, str]]) -> tuple[str | None, str]:
    """(valid status or None, raw value) for a family target; raw "" = field missing.

    Vocab per kind: task -> TASK_STATUSES via `**Status:**`; issue -> issue-status meta;
    plan/report -> doc-status meta; both metas use DOC_STATUSES. Out-of-vocab raw values are
    returned as (None, raw) so the caller can report an anomaly instead of guessing.
    """
    key = str(path)
    if key not in cache:
        text = _read(path)
        if kind == "task":
            raw = md_field(text, "Status")
            cache[key] = (raw if raw in TASK_STATUSES else None, raw or "")
        else:
            meta_name = "issue-status" if kind == "issue" else "doc-status"
            raw = html_meta(text, meta_name)
            cache[key] = (raw if raw in DOC_STATUSES else None, raw or "")
    return cache[key]


def badge_matches_meta(badge: str, meta: str) -> bool:
    """True when the cover badge agrees with the meta status.

    Exact equality, or a parenthetical/plain suffix after the meta status ("Open(常驻)"
    agrees with "Open"); a letter right after the meta status means a different word
    ("Opened" does not agree with "Open").
    """
    badge = " ".join(html_mod.unescape(badge).split())
    if badge == meta:
        return True
    if badge.startswith(meta):
        rest = badge[len(meta):]
        return not rest or not rest[0].isascii() or not rest[0].isalpha()
    return False


def collect_badge_drift(mb: Path, anomalies: list[str]) -> list[str]:
    """Tier B: issue cover badge text vs `<meta name="issue-status">`.

    Missing badge -> not a violation (documented boundary: legacy issues without a cover
    badge stay green here). Missing/out-of-vocab meta -> anomaly (hard fail).
    """
    drift: list[str] = []
    directory = mb / "issues"
    if not directory.is_dir():
        return drift
    for path in sorted(directory.glob("*.html")):
        rel = rel_posix(path, mb.parent)
        text = _read(path)
        raw = html_meta(text, "issue-status")
        if raw not in DOC_STATUSES:
            detail = "missing" if not raw else f"out-of-vocab: {raw!r}"
            anomalies.append(f"{rel}: [status-unreadable] issue-status meta {detail}")
            continue
        m = BADGE_RE.search(text)
        if m is None:
            continue  # legacy file without a cover badge: boundary, see module docstring
        badge = m.group(1).strip()
        if not badge_matches_meta(badge, raw):
            drift.append(f"{rel}: [badge-vs-meta] badge={badge!r} meta={raw!r}")
    return drift


def _negated(probe: str, start: int) -> bool:
    return any(probe[:start].endswith(neg) for neg in NEGATION_PREFIXES)


def _find_done_words(probe: str, lineno: int) -> list[tuple[int, str]]:
    return [(lineno, m.group()) for m in DONE_WORD_RE.finditer(probe) if not _negated(probe, m.start())]


def scan_md_done_words(text: str) -> list[tuple[int, str]]:
    """Tier D scan for markdown bodies (tasks archives): [(lineno, word)].

    Exemptions: fenced code blocks, inline code (quoting must stay possible), date-prefixed
    lines (immutable history entries) and negation prefixes.
    """
    hits: list[tuple[int, str]] = []
    in_fence = False
    for lineno, line in enumerate(text.split("\n"), 1):
        if line.strip().startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if DATE_HEAD_RE.match(LINE_PREFIX_RE.sub("", line)):
            continue
        probe = INLINE_CODE_RE.sub("", line)
        hits.extend(_find_done_words(probe, lineno))
    return hits


def scan_html_done_words(text: str) -> list[tuple[int, str]]:
    """Tier D scan for issue HTML bodies: [(lineno, word)].

    Exemptions mirror the markdown scan: <pre> blocks / inline <code> (quoting), tags are
    stripped before matching, date-prefixed text and negation prefixes.
    """
    hits: list[tuple[int, str]] = []
    in_pre = False
    for lineno, line in enumerate(text.split("\n"), 1):
        opens_pre = bool(re.search(r"<pre\b", line))
        closes_pre = "</pre>" in line
        if opens_pre and closes_pre:
            continue
        if opens_pre:
            in_pre = True
            continue
        if closes_pre:
            in_pre = False
            continue
        if in_pre:
            continue
        probe = TAG_RE.sub("", CODE_TAG_RE.sub("", line))
        if DATE_HEAD_RE.match(LINE_PREFIX_RE.sub("", probe)):
            continue
        hits.extend(_find_done_words(probe, lineno))
    return hits


def collect_done_assertions(mb: Path, cache: dict) -> list[str]:
    """Tier D: done-style words inside Open/In Progress tasks archives and issue bodies."""
    hits: list[str] = []
    scanners = (("tasks", "*.md", "task", scan_md_done_words), ("issues", "*.html", "issue", scan_html_done_words))
    for sub, pattern, kind, scan in scanners:
        directory = mb / sub
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob(pattern)):
            if path.name.startswith("_"):
                continue  # generated indexes mirror their sources; the sources are scanned
            status, _raw = read_status(path, kind, cache)
            if status not in ACTIVE_STATUSES:
                continue
            rel = rel_posix(path, mb.parent)
            for lineno, word in scan(_read(path)):
                hits.append(f"{rel}:{lineno}: [done-assert] word={word!r} (status: {status})")
    return hits


# --------------------------------------------------------------------------- CLI


def _utf8_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def _print_tier(title: str, rows: list[str], tail: list[str] | None = None) -> None:
    if not rows:
        return
    print(f"== {title}: {len(rows)} ==")
    for row in rows:
        print(row)
    for line in tail or ():
        print(line)


def main(argv: list[str] | None = None) -> int:
    _utf8_stdout()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="run the status drift guard (the only action)")
    parser.add_argument("--safety", action="store_true", help="smoke probe: is a bare run a real action")
    parser.add_argument("--quiet", action="store_true", help="only print findings (suppress the all-clear line)")
    parser.add_argument("--root", help="repo root (default: walk up to .git)")
    parser.add_argument("--mb-dir", help="memory-bank dir (default <root>/memory-bank)")
    args = parser.parse_args(argv)

    if args.safety:
        print("read-only-default")
        return 0

    root = Path(args.root).resolve() if args.root else find_root()
    mb = resolve_mb_dir(root, args.mb_dir)
    if not mb.is_dir():
        sys.stderr.write(f"memory-bank dir not found: {mb}\n")
        return 2

    cache: dict[str, tuple[str | None, str]] = {}

    # backlinks -> tiers A / C; unreadable statuses and dangling in-family links -> anomalies
    backlinks, anomalies = collect_backlinks(mb)
    gate_a: list[str] = []
    gate_c: list[str] = []
    for row in backlinks:
        target_rel = rel_posix(row.target, mb.parent)
        status, raw = read_status(row.target, row.kind, cache)
        if status is None:
            detail = "missing" if not raw else f"out-of-vocab: {raw!r}"
            anomalies.append(f"{row.src_rel}:{row.lineno}: [status-unreadable] -> {target_rel} ({detail})")
        elif status == OPEN_STATUS:
            gate_a.append(f"{row.src_rel}:{row.lineno}: [backlink-x-Open] -> {target_rel} (status: {status})")
        elif status == IN_PROGRESS_STATUS:
            gate_c.append(f"{row.src_rel}:{row.lineno}: [backlink-x-InProgress] -> {target_rel} (status: {status})")

    gate_b = collect_badge_drift(mb, anomalies)
    gate_d = collect_done_assertions(mb, cache)

    _print_tier("A hard: backlink x Open", gate_a, tail=[f"hint: {GATE_A_HINT}"] if gate_a else None)
    _print_tier("B hard: issue cover badge vs issue-status meta", gate_b)
    _print_tier("anomalies: status unreadable (missing / out-of-vocab)", anomalies)
    _print_tier("C list: backlink x In Progress (manual review)", gate_c)
    _print_tier("D list: done-style words in Open/In Progress bodies (low confidence)", gate_d)

    hard = len(gate_a) + len(gate_b) + len(anomalies)
    if hard:
        sys.stderr.write(
            f"\nstatus drift guard: {hard} hard finding(s). "
            "Tier A: a progress whitelist section backlinks a document whose status is Open -- flip it to "
            "In Progress via `commands run kb.status` if the claim is genuinely partial. "
            "Tier B: issue cover badge contradicts issue-status meta. "
            "Anomalies: a status field is missing or out-of-vocab (doc-status-meta.md: ring, do not drop). "
            "Tiers C/D are lists only and never fail the exit code.\n"
        )
        return 1
    if not args.quiet:
        print("status drift guard: no hard drift (tiers A/B/anomalies empty).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
