#!/usr/bin/env python
"""CI 全绿门(release skill · 通用件): tag 前核验发版提交的 GitHub CI 全绿。

计划 26-09-22-2318 v2 §6.2 步骤⑥(拍板 §09-12): master run 全绿才准打 tag;
红 → 停手报告, 不静默跳过。轮询走无鉴权 GitHub check-runs API(公开仓, 60 req/h 限额,
30s 间隔 20 分钟 ≈ 40 次在限额内); gh CLI 缺席不阻塞(本机已实证未装)。

判定:
    全部 check run concluded 且 conclusion ∈ {success, neutral, skipped} -> rc 0
    任一 failure/timed_out/cancelled/action_required          -> rc 1(列明细, 停手)
    超时仍未收敛(含全程零 run)                                -> rc 2(停手报告, 不静默)

用法:
    python ci_gate.py --gh-repo <owner/name> [--sha <sha>] [--branch <branch>]
                      [--timeout-min 20] [--interval-sec 30]
退出码: 0 全绿 / 1 CI 红 / 2 超时未收敛(argparse 用法错误同为 2, 停手看 stderr 首行区分) / 3 API 不可用。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request

API_OK_CONCLUSIONS = {"success", "neutral", "skipped"}
API_BAD_CONCLUSIONS = {"failure", "timed_out", "cancelled", "action_required", "startup_failure"}


def fetch_check_runs(sha: str, repo: str) -> list[dict] | None:
    """无鉴权 check-runs 轮询单点(测试经 monkeypatch 注入)。返回 None = API 不可用。"""
    url = f"https://api.github.com/repos/{repo}/commits/{sha}/check-runs?per_page=100"
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "release-skill"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        return payload.get("check_runs", [])
    except urllib.error.HTTPError as exc:
        print(f"[ci_gate] check-runs API HTTP {exc.code}(403=限额/私有仓), 停手报告", file=sys.stderr)
        return None
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError, AttributeError, ValueError) as exc:
        # 代理注入 HTML/5xx 异常体等解析失败按「API 不可用」契约走 None(rc3), 不误诊成 CI 红(R2-F2-4)。
        print(f"[ci_gate] check-runs 响应不可解析, 按 API 不可用停手: {exc}", file=sys.stderr)
        return None


def judge(runs: list[dict]) -> tuple[str, list[str]]:
    """run 列表 -> (pending|green|red, 红明细行)。纯函数, 守阵主战场。"""
    if not runs:
        return "pending", []
    bad = []
    pending = False
    for run in runs:
        name = run.get("name") or run.get("app", {}).get("slug") or "unknown"
        if run.get("status") != "completed":
            pending = True
            continue
        conclusion = (run.get("conclusion") or "").lower()
        if conclusion in API_BAD_CONCLUSIONS:
            bad.append(f"{name}: {conclusion} ({run.get('html_url', '')})")
        elif conclusion not in API_OK_CONCLUSIONS:
            pending = True  # 未知结论按未收敛处理, 不当绿放行
    if bad:
        return "red", bad
    if pending:
        return "pending", []
    return "green", []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CI 全绿门: GitHub check-runs 轮询(release skill)")
    parser.add_argument("--gh-repo", required=True, help="GitHub 仓库 owner/name(项目事实, 由 task 提供)")
    parser.add_argument("--sha", default=None, help="发版提交(默认 HEAD)")
    parser.add_argument("--branch", default=None, help="分支名(仅注释用途)")
    parser.add_argument("--timeout-min", type=int, default=20)
    parser.add_argument("--interval-sec", type=int, default=30)
    ns = parser.parse_args(argv)

    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    sha = ns.sha
    if not sha:
        try:
            proc = subprocess.run(
                ["git", "rev-parse", "HEAD"], capture_output=True, text=True, encoding="utf-8", timeout=30
            )
            sha = proc.stdout.strip() if proc.returncode == 0 else ""
        except (OSError, subprocess.SubprocessError):
            sha = ""
    if not sha:
        print("[ci_gate] 无法解析发版提交 sha(--sha 未给且 git 不可用)", file=sys.stderr)
        return 3

    deadline = time.monotonic() + ns.timeout_min * 60
    saw_any = False
    while True:
        runs = fetch_check_runs(sha, ns.gh_repo)
        if runs is None:
            return 3
        if runs:
            saw_any = True
        state, bad = judge(runs)
        if state == "green":
            print(json.dumps({"sha": sha[:9], "state": "green", "runs": len(runs)}, ensure_ascii=False))
            return 0
        if state == "red":
            print("[ci_gate] CI 红, 停手(修复后重走, 管线可重入):", file=sys.stderr)
            for line in bad:
                print(f"  - {line}", file=sys.stderr)
            return 1
        if time.monotonic() >= deadline:
            if not saw_any:
                print(
                    "[ci_gate] 超时且全程零 check run —— 推送是否真落 GitHub/触发面是否覆盖该分支, 停手报告",
                    file=sys.stderr,
                )
            else:
                print(f"[ci_gate] 超时({ns.timeout_min}min)未收敛, 停手报告", file=sys.stderr)
            return 2
        time.sleep(ns.interval_sec)


if __name__ == "__main__":
    sys.exit(main())
