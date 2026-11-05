#!/usr/bin/env python
"""打发布 tag(release skill · 通用件): 锚定发版提交 + 显式 ref 推送 + ls-remote 核验。

计划 26-09-22-2318 v2 §6.2 步骤⑦。拍板口径:
- tag 名恒 v<major>.<minor>.<patch>, 不带 hash(hash 溯源走显示层/BUILD_ID 侧车);
- 推送一律显式 ref, 推完 ls-remote --tags 核验(本 shell ref 写入有静默丢弃先例);
- 幂等重入: tag 已存在时校验指向而非重建。

用法:
    python tag_release.py --repo <root> --tag v0.3.0 --remotes gitee,github [--message ..]
退出码: 0 全部远端落定(含重入) / 1 校验或推送失败。
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys

TAG_PATTERN = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")


def run_git(args: list[str], repo: str) -> tuple[int, str]:
    proc = subprocess.run(
        ["git", "-C", repo, *args], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def must_git(args: list[str], repo: str, what: str) -> str:
    rc, out = run_git(args, repo)
    if rc != 0:
        raise RuntimeError(f"{what} 失败 rc={rc}: {out.strip()[:400]}")
    return out


def local_tag_sha(run_git, repo: str, tag: str) -> str | None:
    """本地 tag 指向的提交(剥 annotation); 不存在返回 None。"""
    rc, out = run_git(["rev-parse", "--verify", "--quiet", f"refs/tags/{tag}^{{commit}}"], repo)
    return out.strip() or None if rc == 0 else None


def remote_tag_sha(run_git, repo: str, remote: str, tag: str) -> str | None:
    """远端 tag 剥 annotation 后的提交; 不存在返回 None。"""
    out = must_git(["ls-remote", remote, f"refs/tags/{tag}"], repo, "ls-remote")
    for line in out.splitlines():
        sha, _, ref = line.partition("\t")
        if ref.strip() == f"refs/tags/{tag}^{{}}":  # peeled: annotated tag 的真身
            return sha.strip()
        if ref.strip() == f"refs/tags/{tag}":
            peeled = sha.strip()  # light-weight tag 回退值(无 ^{} 行时用它)
    return locals().get("peeled")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="打发布 tag + 显式推送 + ls-remote 核验(release skill)")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--tag", required=True, help="发布 tag, 形如 v0.3.0(不带 hash)")
    parser.add_argument("--remotes", required=True, help="逗号分隔, 首位=主线远端")
    parser.add_argument("--message", default=None, help="tag 附注(默认 auto-qb <tag>)")
    ns = parser.parse_args(argv)

    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    remotes = [r.strip() for r in ns.remotes.split(",") if r.strip()]
    if not remotes:
        print("[tag_release] --remotes 为空", file=sys.stderr)
        return 1

    try:
        if not TAG_PATTERN.match(ns.tag):
            raise RuntimeError(f"tag {ns.tag!r} 不符合 v<major>.<minor>.<patch> 形态(不带 hash)")
        head = must_git(["rev-parse", "HEAD"], ns.repo, "rev-parse HEAD").strip()
        message = ns.message or f"auto-qb {ns.tag}"

        # 幂等重入: 本地已有 → 校验指向而非重建。
        local_sha = local_tag_sha(run_git, ns.repo, ns.tag)
        if local_sha is None:
            must_git(["tag", "-a", ns.tag, "-m", message, head], ns.repo, "git tag")
            local_sha = local_tag_sha(run_git, ns.repo, ns.tag)
            if local_sha != head:
                raise RuntimeError("tag 建后 show-ref 指向异常(ref 静默丢弃先例, 停手核验)")
        elif local_sha != head:
            raise RuntimeError(f"本地 {ns.tag} 已存在但指向 {local_sha[:9]} != HEAD {head[:9]}, 停手要人")

        results = {}
        for remote in remotes:
            rsha = remote_tag_sha(run_git, ns.repo, remote, ns.tag)
            if rsha == local_sha:
                results[remote] = "reentrant"
                continue
            if rsha is not None:
                raise RuntimeError(f"远端 {remote} 的 {ns.tag} 已存在但指向 {rsha[:9]} != 本地 {local_sha[:9]}, 停手要人")
            must_git(["push", remote, ns.tag], ns.repo, f"push {remote}")
            rsha = remote_tag_sha(run_git, ns.repo, remote, ns.tag)
            if rsha != local_sha:
                raise RuntimeError(f"远端 {remote} 推送后 ls-remote 不一致({rsha}), 推送未生效")
            results[remote] = "pushed"
        print(json.dumps({"tag": ns.tag, "sha": local_sha, "remotes": results}, ensure_ascii=False))
        return 0
    except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
        print(f"[tag_release] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
