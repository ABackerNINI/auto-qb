"""同步本地分支到主线 —— fetch + 快进 / rebase。输出契约 v3(计划 26-09-28-0157): 成功一行, 失败一行(原因 + 下一步)。

行为(D1 已拍板 2026-09-28: 必要时用 rebase 保持提交历史线性):
  齐平            → 已同步 <hash>
  纯落后          → git merge --ff-only <远端tip>; 树脏交 git 裁决 —— 无重叠自然成功, 重叠被拒 → 同步成功 <hash>
  分叉(树净)      → git rebase <远端tip>: 只改写按定义未推送的本地独有提交, 历史保持线性;
                    中途冲突 → --abort 全量自动回滚 → 同步成功 <新hash>
  分叉(树脏)      → 失败(先提交或 stash; 脚本不代做清理)

判据纪律: 判落后只用 ls-remote 现查的远端真值对比本地 HEAD —— refs/remotes/* 的写入在本环境
会被静默丢弃, `status -sb` 的 ahead/behind 是快照, 都不可信(单点: memory-bank/pitfalls/git/refs.md)。
合并/变基失败一律自动回滚现场, sync 失败后仓库状态与跑之前一致 —— 写状态的命令必须比只读的更干净地失败。

用法: python <包>/scripts/sync.py   (无旗标; 引擎任务 my-commit-flow.sync)
退出码: 0 已同步 / 同步成功 · 1 失败(输出自带原因, 不存在需要查的码表)
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Windows GBK 控制台兑底(与包内其它脚本同根): 输出含非常用字符时编不出来会 UnicodeEncodeError。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _pipeline import changed_files, git, git_run, staged_overflow  # noqa: E402
from _ship_config import CONFIG_NAME, ConfigMissing, load_config, resolve_branch, resolve_main_remote  # noqa: E402


def remote_sha_with_retry(name: str, branch: str, attempts: int = 2) -> str:
    """取远端 ref 真值 —— 主线瞬时失败可重试一次(网络抖动常见)。取不到(空)≠ 不一致。"""
    for attempt in range(attempts):
        out = git("ls-remote", name, branch, check=False)
        for line in out.splitlines():
            parts = line.split()
            if len(parts) == 2 and parts[1] == f"refs/heads/{branch}":
                return parts[0]
        if attempt == 0:
            time.sleep(1)
    return ""


def _git_reason(proc) -> str:
    """git 失败 stderr 里最后一行人话(hint 行滤掉) —— 失败行的「原因」段。"""
    lines = [l.strip() for l in (proc.stderr or "").splitlines() if l.strip() and not l.startswith("hint:")]
    return lines[-1] if lines else "git 非 0"


def run_sync() -> tuple[bool, str]:
    """核心动作。返回 (ok, line): 成功时 line 是完整成功行(已同步/同步成功 <hash>);
    失败时 line 是「同步失败」的**后缀** —— 冲突场景以「需解决冲突 本地<x> 远端<y> …」开头,
    main 拼上「同步失败」后正好是约定模板「同步失败需解决冲突 本地<x> 远端<y> <步骤>」。
    缺配置等停止类问题 line 以「[STOP]」开头, main 原样打印。
    """
    try:
        cfg, _src = load_config()
    except ConfigMissing as exc:
        return False, str(exc)
    if not git("rev-parse", "--is-inside-work-tree", check=False):
        return False, "不在 git 工作树里 —— 核对 cwd"
    branch = resolve_branch(cfg)
    main, _url = resolve_main_remote(cfg)
    staged, unstaged = changed_files()
    overflow = staged_overflow(staged, cfg["staged_panic"])
    if overflow:
        return False, overflow
    if not main:
        return False, f"找不到主线远端 —— git remote -v 核对后改 {CONFIG_NAME} 的 main_candidates"

    git("fetch", main, branch, check=False)  # 只为把远端 tip 的对象拉进对象库; 判据不读 refs/remotes
    rsha = remote_sha_with_retry(main, branch)
    if not rsha:
        return False, f"拿不到远端 {main}/{branch} (离线?) —— 联网后重跑"
    head = git("rev-parse", "HEAD", check=False)
    if not head:
        return False, "本地没有任何提交 (空仓库)"
    if head == rsha:
        return True, f"已同步 {head[:8]}"

    raw = git("rev-list", "--left-right", "--count", f"{rsha}...HEAD", check=False)
    try:
        behind, ahead = (int(x) for x in raw.split())
    except ValueError:
        return False, "本地没有远端 tip 的对象 (fetch 未落稳?) —— 重跑"
    if behind == 0:
        # 本地领先(未推送) —— 推送即快进, 同步无事可做
        return True, f"已同步 {head[:8]}"

    if ahead == 0:  # 纯落后 → 快进; 树脏与否交 git 裁决(无重叠自然成功)
        proc = git_run("merge", "--ff-only", rsha)
        if proc.returncode != 0:
            reason = ("本地改动与远端新提交重叠" if "would be overwritten" in (proc.stderr or "") else _git_reason(proc))
            return False, f"{reason} 本地{head[:8]} 远端{rsha[:8]} —— 先提交或移出本地改动后重跑"
        return True, f"同步成功 {git('rev-parse', 'HEAD')[:8]}"

    # 分叉 → rebase 保持线性(D1); 树脏不做 —— rebase 会拒绝, 与其让 git 报生码不如自己说人话
    if staged or unstaged:
        return False, (f"已分叉且工作区脏 —— rebase 需干净工作区, 先提交或 stash 后重跑 "
                       f"(本地{head[:8]} 远端{rsha[:8]})")
    proc = git_run("rebase", rsha)
    if proc.returncode != 0:
        git("rebase", "--abort", check=False)  # 全量自动回滚: 失败后仓库与跑之前一致
        return False, (f"需解决冲突 本地{head[:8]} 远端{rsha[:8]} —— rebase 已自动回滚, "
                       "手动合流(解冲突)后重跑")
    return True, f"同步成功 {git('rev-parse', 'HEAD')[:8]}"


def main(argv: list[str] | None = None) -> int:
    import argparse

    # ❗argparse 必须在动作之前: 冒烟闸门会跑 `sync.py --help` —— 没有 argparse 就会把
    # --help 当无参调用, **真的执行一次同步**(push.py 同理, 那会真的推)。
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv or [])  # 显式空表: main() 裸调(测试)不吃 sys.argv 杂音
    ok, line = run_sync()
    if ok:
        print(line)
        return 0
    if line.startswith("[STOP]"):
        print(line)
    else:
        # 冲突场景 line 以「需解决冲突 本地<x> 远端<y> …」开头 —— 无缝拼接后正好是
        # 约定模板「同步失败需解决冲突 本地<x> 远端<y> <步骤>」; 其余失败用冒号分隔。
        sep = "" if line.startswith("需解决") else ": "
        print(f"同步失败{sep}{line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
