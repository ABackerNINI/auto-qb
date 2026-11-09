#!/usr/bin/env python
"""快进合并(release skill · 通用件): 把工作分支的发版提交快进推到发布分支。

计划 26-09-22-2318 v2 §6.2 步骤 5。实现取「显式 ref 推送」路径:
    git push <remote> <from_tip>:refs/heads/<to_branch>
服务端天然拒绝非快进 —— 本地不 checkout、不产生 merge commit, 发布分支与工作分支上
是同一个 commit(hash 溯源不分叉)。前置校验用 ls-remote 现查远端真值 + merge-base
祖先判定, 分叉即停手要人(拍板 §09-10, 不做自动 merge/rewind)。

用法:
    python ff_merge.py --repo <root> --remote <remote> --to-branch <branch> [--from-ref HEAD]
退出码: 0 快进推送成功(或远端已同点, 重入) / 1 分叉/失败, 停手要人。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys


def run_git(args: list[str], repo: str) -> str:
    """git 调用单点(测试经 monkeypatch 注入, 不起真子进程)。"""
    proc = subprocess.run(
        ["git", "-C", repo, *args], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} 失败 rc={proc.returncode}: {proc.stderr.strip()[:400]}")
    return proc.stdout


def remote_tip_of(run_git, repo: str, remote: str, branch: str) -> str | None:
    """ls-remote 现查远端分支真值; 不存在返回 None(首次创建发布分支属合法快进)。"""
    out = run_git(["ls-remote", remote, f"refs/heads/{branch}"], repo)
    for line in out.splitlines():
        sha, _, ref = line.partition("\t")
        if ref.strip() == f"refs/heads/{branch}":
            return sha.strip() or None
    return None


def check_clean_tree(repo: str, run_git) -> None:
    out = run_git(["status", "--porcelain"], repo)
    if out.strip():
        raise RuntimeError("工作树不净, 拒跑快进合并")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="快进合并: 工作分支 -> 发布分支(release skill)")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--remote", required=True, help="发布分支所在远端(项目事实, 由 task 提供)")
    parser.add_argument("--to-branch", required=True)
    parser.add_argument("--from-ref", default="HEAD")
    ns = parser.parse_args(argv)

    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    try:
        check_clean_tree(ns.repo, run_git)
        from_tip = run_git(["rev-parse", f"{ns.from_ref}^{{commit}}"],
                           ns.repo).strip()  # 剥 annotation: annotated tag 直给会拿到 tag 对象 sha, push 被服务端拒收
        if not from_tip:
            raise RuntimeError(f"from-ref {ns.from_ref!r} 解析为空")
        remote_tip = remote_tip_of(run_git, ns.repo, ns.remote, ns.to_branch)
        if remote_tip is not None:
            # 先取对象再判祖先(merge-base 需要远端提交对象在本地)。
            run_git(["fetch", "--quiet", ns.remote, ns.to_branch], ns.repo)
            try:
                run_git(["merge-base", "--is-ancestor", remote_tip, from_tip], ns.repo)
            except RuntimeError:
                raise RuntimeError(
                    f"发布分支 {ns.to_branch}({remote_tip[:9]}) 不是 {from_tip[:9]} 的祖先 —— 非快进, 停手要人"
                ) from None
            if remote_tip == from_tip:
                print(json.dumps({"status": "reentrant", "tip": from_tip, "branch": ns.to_branch}))
                return 0
        run_git(["push", ns.remote, f"{from_tip}:refs/heads/{ns.to_branch}"], ns.repo)
        pushed = remote_tip_of(run_git, ns.repo, ns.remote, ns.to_branch)
        if pushed != from_tip:
            raise RuntimeError(f"推送后 ls-remote 仍为 {pushed}, 推送未生效(报告一次不重试)")
        print(json.dumps({"status": "fast-forwarded", "tip": from_tip, "branch": ns.to_branch, "remote": ns.remote}))
        return 0
    except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
        print(f"[ff_merge] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
