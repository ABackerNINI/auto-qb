#!/usr/bin/env python
"""执行 bump(release skill · 通用件): bump-my-version 改版本文件 + 刷新打包元数据。

前置: 决策器 suggest_bump.py 已出提案、agent 已完成改判(留痕在 CHANGELOG/commit body)。
本脚本只做机械三件事(计划 26-09-22-2318 v2 §6.2 步骤 3):
    1. 净树校验(脏树拒跑 —— bump 只发生在闸门前、测试后的干净基线上);
    2. bump-my-version bump <kind>(版本文件编辑单点, commit/tag 一律由其配置禁用);
    3. uv sync 刷新 editable 元数据(bump 与 sync 之间 dist-info 烤旧号, 评审 R1-F4)。

用法:
    python apply_bump.py --repo <root> --kind patch|minor|major [--skip-sync]
退出码: 0 成功 / 1 前置或执行失败(单行 stderr)。
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

SEMVER_KINDS = ("patch", "minor", "major")


def run_cmd(args: list[str], repo: str) -> tuple[int, str]:
    """命令调用单点(测试经 monkeypatch 注入, 不起真子进程)。"""
    proc = subprocess.run(
        args, cwd=repo, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def check_clean_tree(repo: str, run) -> None:
    rc, out = run(["git", "status", "--porcelain"], repo)
    if rc != 0:
        raise RuntimeError(f"git status 失败: {out.strip()}")
    if out.strip():
        raise RuntimeError("工作树不净, 拒跑 bump(先提交或清理; bump 只在净树上执行)")


def read_current_version(repo: str) -> str:
    pyproject = Path(repo) / "pyproject.toml"
    with pyproject.open("rb") as fh:
        data = tomllib.load(fh)
    version = data.get("tool", {}).get("bumpversion", {}).get("current_version")
    if not version or not re.match(r"^\d+\.\d+\.\d+$", version):
        raise RuntimeError(f"pyproject [tool.bumpversion] current_version 缺失或非 SemVer: {version!r}")
    return version


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="执行 bump (release skill)")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--kind", required=True, choices=SEMVER_KINDS)
    parser.add_argument("--skip-sync", action="store_true", help="跳过 uv sync(仅测试用)")
    ns = parser.parse_args(argv)

    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    try:
        check_clean_tree(ns.repo, run_cmd)
        before = read_current_version(ns.repo)
        bm = shutil.which("bump-my-version")
        if not bm:
            raise RuntimeError("bump-my-version 不在 PATH(应为 uv 环境调用; dev 依赖未装?)")
        rc, out = run_cmd([bm, "bump", ns.kind], ns.repo)
        if rc != 0:
            raise RuntimeError(f"bump-my-version bump {ns.kind} 失败 rc={rc}: {out.strip()[:500]}")
        after = read_current_version(ns.repo)
        if not ns.skip_sync:
            rc, out = run_cmd(["uv", "sync"], ns.repo)
            if rc != 0:
                raise RuntimeError(
                    f"uv sync 刷新元数据失败 rc={rc}: {out.strip()[:300]}" +
                    " —— 版本文件已 bump 且树脏, 恢复: 手动跑 uv sync 续跑, 或回退 bump 文件后重跑"
                )
        print(
            json.dumps(
                {
                    "before": before,
                    "kind": ns.kind,
                    "after": after,
                    "synced": not ns.skip_sync
                }, ensure_ascii=False
            )
        )
        return 0
    except (RuntimeError, OSError, subprocess.SubprocessError, tomllib.TOMLDecodeError) as exc:
        print(f"[apply_bump] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
