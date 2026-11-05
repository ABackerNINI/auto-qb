#!/usr/bin/env python
"""建 Release 页(release skill · 通用件): gitee 主线 + github 镜像, 各尝试一次不重试。

计划 26-09-22-2318 v2 §6.2 步骤⑧(拍板 §09-14):
- gitee: API 需个人 token(环境变量, 默认 GITEE_TOKEN); 未配置 = 降级过渡
  (「tag + CHANGELOG 即发布口径」), 打 WARN 不失败, token 配好后补建;
- github: 镜像, 尝试一次, 失败只报告不重试不回滚主线;
- 幂等重入: Release 页已存在时跳过(gitee 40x 已存在按重入处理)。

用法:
    python release_page.py --tag v0.3.0 --notes-file <path> [--gitee-repo owner/name]
                           [--github-repo owner/name] [--gitee-token-env GITEE_TOKEN]
退出码: 0 成功/降级(gitee 无 token)/镜像失败 | 1 主线(gitee)建页失败(有 token 时)。
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

GITEE_API = "https://gitee.com/api/v5"


def http_json(url: str, payload: dict, method: str = "POST") -> tuple[int, str]:
    """HTTP JSON 调用单点(测试经 monkeypatch 注入)。"""
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method=method, headers={
            "Content-Type": "application/json",
            "User-Agent": "release-skill"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, (exc.read().decode("utf-8", "replace") or "")[:500]
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return 0, str(exc)


def gitee_release_exists(http, repo: str, token: str, tag: str) -> bool:
    status, body = http(f"{GITEE_API}/repos/{repo}/releases/tags/{tag}?access_token={token}", {}, method="GET")
    return status == 200


def gitee_create(http, repo: str, token: str, tag: str, notes: str) -> tuple[bool, str]:
    if gitee_release_exists(http, repo, token, tag):
        return True, "reentrant"
    status, body = http(
        f"{GITEE_API}/repos/{repo}/releases",
        {
            "access_token": token,
            "tag_name": tag,
            "name": tag,
            "body": notes,
            "prerelease": tag.startswith("v0.")
        },
    )
    if status in (200, 201):
        return True, "created"
    if status in (400, 409, 422) and "已存在" in body or "already" in body.lower():
        return True, "reentrant"
    return False, f"HTTP {status}: {body.strip()[:300]}"


def github_create(repo: str, tag: str, notes_file: Path) -> tuple[bool, str]:
    """gh CLI 尝试一次(镜像纪律: 失败只报告不重试); gh 缺席按镜像失败报告。"""
    gh = shutil.which("gh")
    if not gh:
        return False, "gh 不在 PATH, 镜像 Release 未建(报告一次, 不重试)"
    proc = subprocess.run(
        [gh, "release", "create", tag, "--repo", repo, "--title", tag, "--notes-file",
         str(notes_file)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    if proc.returncode != 0:
        out = (proc.stderr or proc.stdout or "").strip()[:300]
        if "already exists" in out.lower():
            return True, "reentrant"
        return False, f"gh rc={proc.returncode}: {out}"
    return True, "created"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="建 Release 页: gitee 主线 + github 镜像(release skill)")
    parser.add_argument("--tag", required=True)
    parser.add_argument("--notes-file", required=True, type=Path, help="发行说明(CHANGELOG 该版段)文件")
    parser.add_argument("--gitee-repo", default=None, help="gitee owner/name(项目事实, 由 task 提供)")
    parser.add_argument("--github-repo", default=None, help="github owner/name")
    parser.add_argument("--gitee-token-env", default="GITEE_TOKEN", help="gitee token 的环境变量名")
    ns = parser.parse_args(argv)

    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    if not ns.notes_file.exists():
        print(f"[release_page] 发行说明文件不存在: {ns.notes_file}", file=sys.stderr)
        return 1
    notes = ns.notes_file.read_text(encoding="utf-8")

    results: dict[str, str] = {}
    main_failed = False

    if ns.gitee_repo:
        token = os.environ.get(ns.gitee_token_env, "")
        if not token:
            results["gitee"] = "degraded: token 未配置, 以「tag + CHANGELOG 即发布口径」过渡, 配好后补建"
            print(f"[release_page] WARN {results['gitee']}", file=sys.stderr)
        else:
            ok, detail = gitee_create(http_json, ns.gitee_repo, token, ns.tag, notes)
            results["gitee"] = detail
            if not ok:
                main_failed = True
                print(f"[release_page] gitee 建页失败: {detail}", file=sys.stderr)
    else:
        results["gitee"] = "skipped: 未给 --gitee-repo"

    if ns.github_repo:
        ok, detail = github_create(ns.github_repo, ns.tag, ns.notes_file)
        results["github"] = detail + ("" if ok else "(镜像, 允许滞后)")
        if not ok:
            print(f"[release_page] github 镜像建页失败(报告一次不重试): {detail}", file=sys.stderr)
    else:
        results["github"] = "skipped: 未给 --github-repo"

    print(json.dumps({"tag": ns.tag, "results": results}, ensure_ascii=False))
    return 1 if main_failed else 0


if __name__ == "__main__":
    sys.exit(main())
