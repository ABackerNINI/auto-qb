"""推送 —— **顺序固定**: 先推 Gitee 主线(必须成功), 再尝试一次 GitHub 直连(失败只报一次)。

用法:
    python .agents/skills/my-commit-flow/scripts/push.py [--skip-mirror]

流程:
  1. 先 `git fetch` 再看是否落后 —— 落后就 STOP(不自动 rebase, 那是红线区)
  2. `git push <main> <branch>`; 失败原样输出并退出
  3. 核对远端 ref == 本地 HEAD(`git ls-remote`);`git status -sb` 不应再有 ahead
  4. 镜像: `git -c http.https://github.com.proxy= push <mirror> <branch>` —— **只尝试一次**,
     失败如实报告一次, 不重试 / 不换代理 / 不改走 SSH / 不回滚 Gitee 上已完成的推送

退出码: 0 主线推送成功(镜像失败不影响) · 1 落后主线 · 5 主线推送失败
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _ship_config import (  # noqa: E402
    BRANCH,
    MIRROR_PROXY_DISABLE_ARGS,
    MIRROR_URL,
    resolve_main_remote,
    REMOTE_MIRROR,
)


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")


MAIN = resolve_main_remote()  # 运行期定主线远端名(gitee / origin)


def remotes() -> dict[str, str]:
    out: dict[str, str] = {}
    proc = git("remote", "-v")
    for line in proc.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[2] == "(push)":
            out[parts[0]] = parts[1]
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-mirror", action="store_true", help="不尝试 GitHub 镜像")
    args = parser.parse_args(argv)

    print("=== 推送前再 fetch 一次(status -sb 的 ahead/behind 是上次 fetch 的快照) ===")
    git("fetch", MAIN, BRANCH)
    behind_ahead = git("rev-list", "--left-right", "--count", f"{MAIN}/{BRANCH}...HEAD").stdout.split()
    if len(behind_ahead) == 2 and int(behind_ahead[0]) > 0:
        sys.stderr.write(f"落后主线 {behind_ahead[0]} 个提交 —— 先 rebase(工作区必须干净), 不推。\n")
        return 1
    print(f"  与主线齐平(本地领先 {behind_ahead[1] if len(behind_ahead) == 2 else '?'} 个)")

    head = git("rev-parse", "HEAD").stdout.strip()
    print(f"\n=== 推主线 {MAIN}/{BRANCH} ===")
    proc = git("push", MAIN, BRANCH)
    print((proc.stdout + proc.stderr).strip())
    if proc.returncode != 0:
        sys.stderr.write("主线推送失败 —— 镜像不再尝试, 先解决主线。\n")
        return 5

    print("\n=== 核对远端 ===")
    remote = git("ls-remote", MAIN, BRANCH).stdout.split()
    remote_sha = remote[0] if remote else ""
    ok = remote_sha == head
    print(f"  远端 {remote_sha}\n  本地 {head}  →  {'一致' if ok else '**不一致**'}")
    print(f"  {git('status', '-sb').stdout.splitlines()[0]}")

    if args.skip_mirror:
        return 0 if ok else 5

    print(f"\n=== 尝试一次 GitHub 直连({REMOTE_MIRROR}) ===")
    rem = remotes()
    if REMOTE_MIRROR not in rem:
        print(f"  没有 {REMOTE_MIRROR} 远端; 需要时: git remote add {REMOTE_MIRROR} {MIRROR_URL}")
        return 0 if ok else 5
    proc = git(*MIRROR_PROXY_DISABLE_ARGS, "push", REMOTE_MIRROR, BRANCH)  # -c 覆盖为空 = 禁用全局代理
    out = (proc.stdout + proc.stderr).strip()
    if proc.returncode == 0:
        print(f"  镜像已推: {out.splitlines()[-1] if out else 'ok'}")
    else:
        # 只如实报告一次: 不重试 / 不换代理 / 不改 SSH / 不回滚 Gitee
        print(f"  镜像直连失败(不重试, GitHub 允许滞后): {out.splitlines()[-1] if out else '无输出'}")

    return 0 if ok else 5


if __name__ == "__main__":
    raise SystemExit(main())
