#!/usr/bin/env python3
"""Dependency update checker for the deps-upgrade skill.

Reads project/deps.toml and prints a markdown report to stdout.

- watch deps: external target programs tracked on GitHub (tags reported
  separately per branch line, stable vs dev). No bump action; an update
  feeds compatibility analysis only.
- pin deps: everything in uv.lock, checked against PyPI for a newer
  version (current -> latest, with release date and delta kind).

Design constraints (do not violate):
- Python stdlib only; this script must never add a dependency;
- read-only and stateless: never writes files, keeps no cache; the
  skill directory stays pure config (detection is separated from
  decision; see ../SKILL.md);
- zero network failure tolerance: a single unreachable source is
  reported as [unreachable] and the rest of the run continues;
- output is pure ASCII (no emoji, no graphic symbols).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[4]
CONFIG_PATH = Path(__file__).resolve().parents[1] / "project" / "deps.toml"
USER_AGENT = "auto-qb-deps-upgrade/1.0 (skill script; read-only)"

GITHUB_TAGS_URL = "https://api.github.com/repos/{repo}/tags?per_page=100"
GITHUB_COMMIT_URL = "https://api.github.com/repos/{repo}/commits/{ref}"
PYPI_JSON_URL = "https://pypi.org/pypi/{name}/json"

# ----------------------------------------------------------------- helpers


class Unreachable(Exception):
    """A single upstream source failed; the run must continue."""


def fetch_json(url: str, timeout: float) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - any failure => source skipped
        raise Unreachable(f"{exc.__class__.__name__}: {exc}") from exc


def version_segments(v: str) -> list[int | str]:
    segs: list[int | str] = []
    for tok in re.findall(r"\d+|[A-Za-z][A-Za-z0-9]*", v):
        segs.append(int(tok) if tok.isdigit() else tok)
    return segs


def delta_kind(current: str, latest: str) -> str:
    """Classify current -> latest for the pin table.

    Positional comparison of numeric segments only. Date-based (CalVer)
    projects fall out naturally: a first-segment change shows as
    'major-line'. Non-numeric differences (rc suffixes etc.) are
    reported as 'pre/tag diff'.
    """
    if current == latest:
        return "none"
    c = [s for s in version_segments(current) if isinstance(s, int)]
    l = [s for s in version_segments(latest) if isinstance(s, int)]
    for i in range(max(len(c), len(l))):
        a = c[i] if i < len(c) else 0
        b = l[i] if i < len(l) else 0
        if a != b:
            if a > b:
                return "check (lower)"
            return ("major-line", "minor", "patch")[min(i, 2)]
    return "pre/tag diff"


def support_status(dep: str, version: str, support_map: dict[str, dict[str, Any]]) -> str:
    """Check a version against the support matrix anchors in deps.toml.

    Matching: exact string, or 'N.x' prefix wildcard. alpha/beta are
    tracked but never enter the matrix (they stay 'NEW vs matrix').
    """
    entry = support_map.get(dep)
    if entry is None:
        return "-"
    for a in entry.get("analyzed", []):
        if a.endswith(".x"):
            if version.startswith(a[:-1]):
                return f"analyzed ({a})"
        elif version == a:
            return f"analyzed ({a})"
    return "NEW vs matrix"


def fmt_date(iso: str | None) -> str:
    if not iso:
        return "-"
    return iso[:10]


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


# ------------------------------------------------------------------ config


def load_config() -> dict[str, Any]:
    with open(CONFIG_PATH, "rb") as fh:
        return tomllib.load(fh)


def load_lock_versions(lockfile: Path) -> dict[str, str]:
    """Parse uv.lock into {normalized name: pinned version}."""
    with open(lockfile, "rb") as fh:
        data = tomllib.load(fh)
    out: dict[str, str] = {}
    for pkg in data.get("package", []):
        name = str(pkg.get("name", "")).lower().replace("_", "-")
        if name and name not in out:
            out[name] = str(pkg.get("version", "?"))
    return out


def load_pyproject(pyproject: Path) -> dict[str, Any]:
    with open(pyproject, "rb") as fh:
        return tomllib.load(fh)


def direct_dep_names(pydata: dict[str, Any]) -> set[str]:
    """Names of direct deps (project dependencies + dependency-groups)."""
    reqs: list[str] = list(pydata.get("project", {}).get("dependencies", []))
    for group in pydata.get("dependency-groups", {}).values():
        reqs.extend(group)
    names = set()
    for req in reqs:
        m = re.match(r"\s*([A-Za-z0-9_.\-]+)", req)
        if m:
            names.add(m.group(1).lower().replace("_", "-"))
    return names


# ------------------------------------------------------------------- watch


def github_tag_date(repo: str, ref: str, timeout: float) -> str:
    data = fetch_json(GITHUB_COMMIT_URL.format(repo=repo, ref=ref), timeout)
    return data.get("commit", {}).get("committer", {}).get("date", "")


def check_watch_entry(
    entry: dict[str, Any],
    timeout: float,
    support_map: dict[str, dict[str, Any]],
) -> tuple[list[str], list[str]]:
    """Return (markdown lines, joint-analysis triggers) for one watch dep.

    Single-source failures degrade that line/field to [unreachable];
    they never abort the run. A line whose latest tag version is not in
    the support matrix emits a joint-analysis trigger.
    """
    repo = entry["repo"]
    dep_id = entry["id"]
    version_re = re.compile(entry.get("version_extract", "^(.+)$"))
    triggers: list[str] = []
    lines = [
        f"### {dep_id}  (github: {repo})",
        "",
    ]
    note = entry.get("note")
    if note:
        lines.append(f"> {note}")
        lines.append("")

    tags: list[dict[str, Any]] = []
    try:
        # GitHub returns tags newest-first; we take the first match per line.
        tags = fetch_json(GITHUB_TAGS_URL.format(repo=repo), timeout)
    except Unreachable as exc:
        lines.append(f"[unreachable] tags for {repo} ({exc})")
        lines.append("")

    rows: list[list[str]] = []
    for line_entry in entry.get("lines", []):
        name = line_entry.get("name", "?")
        pattern = re.compile(line_entry.get("tag_filter", ""))
        ref = line_entry.get("ref", "")
        latest = next((t for t in tags if pattern.match(t.get("name", ""))), None)
        if latest is None:
            rows.append([name, "(no tag yet)", "-", "-", ref or "-", "-"])
            continue
        tag_name = latest["name"]
        m = version_re.match(tag_name)
        version = m.group(1) if m else tag_name
        status = support_status(dep_id, version, support_map)
        if status.startswith("NEW"):
            triggers.append(f"- [!] {dep_id}: line {name} has {version} ({status})")
        try:
            tag_date = fmt_date(github_tag_date(repo, tag_name, timeout))
        except Unreachable as exc:
            tag_date = f"[unreachable] {exc}"
        try:
            head_date = fmt_date(github_tag_date(repo, ref, timeout)) if ref else "-"
        except Unreachable as exc:
            head_date = f"[unreachable] {exc}"
        rows.append([name, tag_name, version, tag_date, ref or "-", head_date])

    lines.append("| line | latest tag | version | tag date | branch ref | branch head |")
    lines.append("|---|---|---|---|---|---|")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")
    return lines, triggers


# --------------------------------------------------------------------- pin


def pypi_latest(name: str, timeout: float) -> tuple[str, str]:
    """Return (latest version, latest release upload date)."""
    data = fetch_json(PYPI_JSON_URL.format(name=name), timeout)
    latest = data.get("info", {}).get("version", "?")
    date = ""
    files = data.get("releases", {}).get(latest) or []
    for f in files:
        date = f.get("upload_time_iso_8601") or ""
        if date:
            break
    return latest, date


def check_pin_deps(
    cfg: dict[str, Any],
    quick: bool,
    timeout: float,
) -> tuple[list[str], int]:
    """Return (markdown lines, count of deps with an update available)."""
    pin_cfg = cfg.get("pin", {})
    joint = set(cfg.get("joint", {}).get("deps", []))
    exempt = set(pin_cfg.get("exempt", []))
    support_map = {s["dep"]: s for s in cfg.get("support", [])}

    lock = load_lock_versions(REPO_ROOT / cfg["paths"]["lockfile"])
    pydata = load_pyproject(REPO_ROOT / cfg["paths"]["pyproject"])
    direct = direct_dep_names(pydata)
    project_name = str(pydata.get("project", {}).get("name", "")).lower()

    names = sorted(n for n in lock if n != project_name and n not in exempt)
    if quick:
        names = [n for n in names if n in joint]

    lines = ["| package | lock | pypi latest | delta | latest release | direct | joint | support |"]
    lines.append("|---|---|---|---|---|---|---|---|")
    updates = 0
    for name in names:
        current = lock[name]
        try:
            latest, date = pypi_latest(name, timeout)
        except Unreachable as exc:
            lines.append(
                f"| {name} | {current} | [unreachable] | - | "
                f"{exc.__class__.__name__} | "
                f"{'yes' if name in direct else '-'} | "
                f"{'yes' if name in joint else '-'} | - |"
            )
            continue
        kind = delta_kind(current, latest)
        changed = latest != current
        if changed:
            updates += 1
        lines.append(
            f"| {name} | {current} | {latest} | {kind} | {fmt_date(date)} | "
            f"{'yes' if name in direct else '-'} | "
            f"{'yes' if name in joint else '-'} | "
            f"{support_status(name, latest, support_map) if changed else '-'} |"
        )
    lines.append("")
    return lines, updates


# ------------------------------------------------------------------- report


def build_report(cfg: dict[str, Any], quick: bool, timeout: float) -> str:
    joint = list(cfg.get("joint", {}).get("deps", []))
    support_map = {s["dep"]: s for s in cfg.get("support", [])}
    mode = "quick (joint deps only)" if quick else "full"

    out: list[str] = [
        "# Dependency Update Check",
        "",
        f"- generated: {now_utc()}",
        f"- mode: {mode}",
        f"- config: {CONFIG_PATH.relative_to(REPO_ROOT)}",
        "- this script is read-only and stateless; it never bumps anything",
        "",
        "## Watch deps (external programs; no bump action, analysis only)",
        "",
    ]

    watch_entries = cfg.get("watch", [])
    if quick:
        watch_entries = [w for w in watch_entries if w.get("id") in joint]
    joint_hits: list[str] = []

    for entry in watch_entries:
        lines, triggers = check_watch_entry(entry, timeout, support_map)
        out.extend(lines)
        joint_hits.extend(triggers)

    out.append("## Pin deps (uv.lock; bumpable)")
    out.append("")
    pin_lines, pin_updates = check_pin_deps(cfg, quick, timeout)
    out.extend(pin_lines)

    # joint triggers from the pin side
    for line in pin_lines:
        if line.startswith("|") and "NEW vs matrix" in line:
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) >= 8:
                joint_hits.append(f"- [!] {cells[0]}: lock {cells[1]} -> pypi {cells[2]} ({cells[7]})")

    out.append("## Joint analysis triggers")
    out.append("")
    if joint_hits:
        out.append("Any update below requires JOINT analysis of all three special deps")
        out.append("(qbittorrent / libtorrent / qbittorrent-api): one upgrade changes the")
        out.append("adaptation surface of the others. Runbook: project/impact-map.md, section 3.")
        out.append("")
        out.extend(joint_hits)
    else:
        out.append("(none) - no unanalyzed release detected on the joint deps.")
    out.append("")

    out.append("## How to act")
    out.append("")
    out.append("Decision tiers (green bump / yellow issue / blue note / watch analysis):")
    out.append("see .agents/skills/deps-upgrade/SKILL.md. Bumping never includes commit/push;")
    out.append("commit and push wait for an explicit user instruction.")
    out.append("")
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check upstream dependency updates (watch + pin) and print a markdown report."
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="only check the joint/special deps instead of the full pin scan",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=20.0,
        help="per-request network timeout in seconds (default: 20)",
    )
    args = parser.parse_args()
    cfg = load_config()
    sys.stdout.write(build_report(cfg, args.quick, args.timeout))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
