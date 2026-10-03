"""同步本地分支到主线 —— fetch + 快进 / rebase。输出契约 v3(计划 26-09-28-0157): 成功一行, 失败一行(原因 + 下一步)。

行为(D1 已拍板 2026-09-28: 必要时用 rebase 保持提交历史线性):
  齐平            → 已同步 <hash>
  纯落后          → git merge --ff-only <远端tip>; 树脏交 git 裁决 —— 无重叠自然成功, 重叠被拒 → 同步成功 <hash>
  分叉(树净)      → git rebase <远端tip>: 只改写按定义未推送的本地独有提交, 历史保持线性;
                    中途冲突 → --abort 全量自动回滚 → 同步成功 <新hash>
  树脏挡路(上两类的脏分支) → 失败, 失败行**自带解锁配方** UNLOCK_STEPS(脚本仍不代做清理)

生成物冲突自动化解(计划 26-10-03-1544, 默认开; 键 auto_resolve_generated / generated_*_cmd):
  快进被拒 / rebase 冲突时, 若重叠 / 冲突**全部**落在生成物白名单(`generated_list_cmd` 的 --list)上,
  则「任取一侧 + 重跑生成器 + --check 自证」自动化解, 成功行带「自动重跑生成物 N 处」标记。
  只要有一个手写文件参与, 或白名单 / 重跑 / 自证任一步取不到, 一律**退回上面的失败行**(不猜、不部分解决)。
  为什么敢默认开: 生成器是纯函数(内容只由工作树里的手写文件决定), 重跑后自证通过 = 文件确实等于
  生成结果 ⇒ 证明没有手写内容被丢弃。白名单是唯一权威来源(生成器自己的 --list), 不在这里再抄一份。

注: 树脏类失败行为什么必须自带配方(2026-10-03 定): 只说「先提交或移出后重跑」会撞**双向死锁** ——
  sync 要你先提交, 而 ship.commit 内部第一步就是这条 sync(树脏未解, 必再撞同一处), 两端互斥谁都进不去。
  解锁唯一走法: stash 移出 → 同步 → pop 弹回(两处改动上下文不重叠时自动合并, 实测零冲突)。

判据纪律: 判落后只用 ls-remote 现查的远端真值对比本地 HEAD —— refs/remotes/* 的写入在本环境
会被静默丢弃, `status -sb` 的 ahead/behind 是快照, 都不可信(单点: memory-bank/pitfalls/git/refs.md)。
合并/变基失败一律自动回滚现场, sync 失败后仓库状态与跑之前一致 —— 写状态的命令必须比只读的更干净地失败。

用法: python <包>/scripts/sync.py   (无旗标; 引擎任务 my-commit-flow.sync)
退出码: 0 已同步 / 同步成功 · 1 失败(输出自带原因, 不存在需要查的码表)
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

# Windows GBK 控制台兑底(与包内其它脚本同根): 输出含非常用字符时编不出来会 UnicodeEncodeError。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _pipeline import changed_files, expand_run, git, git_run, staged_overflow  # noqa: E402
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


# 树脏挡路的**解锁配方** —— 两类脏分支失败行都必须带上它(不带 = 双向死锁, 见模块 docstring)。
# `-u` 必带: 收尾产物常是未跟踪新文件(新档案 / 新切片 / 新 pitfall), 默认 stash 不收未跟踪,
# 快进仍会被它们挡住; pop 时远端不会新增同名文件, 实测无冲突。高风险同步前照例 `cp -a .git <仓库外备份>`。
UNLOCK_STEPS = (
    "git stash push -u → commands run my-commit-flow.sync → git stash pop → "
    "测试 → commands run ship.commit"
)

# 树脏类失败行的固定前缀 —— commit.py 靠它识别「本轮会死锁」, 好补一句护栏提示(不重复配方)。
DIRTY_BLOCK_MARK = "树脏挡路"


def is_dirty_block(line: str) -> bool:
    """失败行是不是「本地改动挡住同步」这一类 —— 是就必须按 UNLOCK_STEPS 解锁, 不能走「先提交」。"""
    return line.startswith(DIRTY_BLOCK_MARK)


def _git_reason(proc) -> str:
    """git 失败 stderr 里最后一行人话(hint 行滤掉) —— 失败行的「原因」段。"""
    lines = [l.strip() for l in (proc.stderr or "").splitlines() if l.strip() and not l.startswith("hint:")]
    return lines[-1] if lines else "git 非 0"


# ------------------------------------------------------------------ 生成物冲突自动化解
# 三步不变量(计划 26-10-03-1544): 白名单(生成器 --list) → 任取一侧 + 重跑 → --check 自证。
# 不做文本合并、不做行级并集; 任一步取不到即退回现状失败行(保守默认), 绝不在「部分解决」的状态上硬上。
GENERATED_MARK = "自动重跑生成物"


def _repo_root() -> str:
    """当前工作树根 —— 配置里的命令要在此 cwd 下跑(相对路径才对得上)。"""
    return git("rev-parse", "--show-toplevel", check=False) or "."


def _expand_and_run(cmd: str, root: str, timeout: int = 120) -> subprocess.CompletedProcess | None:
    """展开(<skill-dir:NAME> 与闸门同一套解析)并执行一条配置命令; 展开不了 / 起不来 → None。"""
    if not cmd.strip():
        return None
    try:
        cmds, skip = expand_run(cmd, {"root": Path(root), "changed": [], "each_limit": 1})
    except Exception:  # ExpandError 及其它展开异常 —— 一律按「取不到」处理
        return None
    if skip or not cmds:
        return None
    try:
        return subprocess.run(
            cmds[0],
            shell=True,
            cwd=root,
            timeout=timeout,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def _whitelist(cfg: dict) -> set[str] | None:
    """生成物白名单(仓库相对 posix); 命令缺失 / 非 0 退出 / 输出为空 → None(退回现状)。"""
    proc = _expand_and_run(str(cfg.get("generated_list_cmd") or ""), _repo_root())
    if proc is None or proc.returncode != 0:
        return None
    paths = {line.strip().replace("\\", "/") for line in proc.stdout.splitlines() if line.strip()}
    return paths or None


def _regen(cfg: dict, root: str) -> bool:
    """重跑生成器; 成功 rc=0。"""
    proc = _expand_and_run(str(cfg.get("generated_regen_cmd") or ""), root)
    return proc is not None and proc.returncode == 0


def _self_check(cfg: dict, root: str) -> bool:
    """自证: 同一重跑命令加 `--check`; rc=0 = 磁盘内容确实等于生成结果(⇒ 没丢手写内容)。"""
    cmd = str(cfg.get("generated_regen_cmd") or "").strip()
    if not cmd:
        return False
    proc = _expand_and_run(f"{cmd} --check", root)
    return proc is not None and proc.returncode == 0


def _modified_paths() -> set[str]:
    """本地**被修改**(不含新增 / 删除 / 改名 / 未跟踪)的路径 —— 生成物自动化解只碰这一类。"""
    out: set[str] = set()
    for extra in ((), ("--cached", )):
        out |= {
            line.strip()
            for line in git("diff", *extra, "--name-only", "--diff-filter=M", check=False).splitlines() if line.strip()
        }
    return out


def _remote_changed(rsha: str) -> set[str]:
    """远端 tip 相对本地 HEAD 改动过的路径。"""
    return {line.strip() for line in git("diff", "--name-only", "HEAD", rsha, check=False).splitlines() if line.strip()}


def _in_head(path: str) -> bool:
    """路径在 HEAD 里存在 —— 自动化解只处理「被修改」的已跟踪文件, 删除 / 改名 / 未跟踪一律不猜。"""
    return git_run("cat-file", "-e", f"HEAD:{path}").returncode == 0


def _snapshot_dirty() -> dict[str, bytes | None]:
    """记录全部已跟踪脏文件的字节(None = 已删除), 供失败回滚; 未跟踪文件不在内(不受影响)。"""
    snap: dict[str, bytes | None] = {}
    for line in git("-c", "core.quotepath=off", "status", "--porcelain", "-uall").splitlines():
        if not line.strip():
            continue
        xy = line[:2]
        path = line[3:].strip() if len(line) > 3 else ""
        if " -> " in path:
            path = path.split(" -> ")[-1].strip()
        if not path or xy[0] == "?" or xy[1] == "?":
            continue
        target = Path(path)
        snap[path] = target.read_bytes() if target.exists() else None
    return snap


def _restore(head: str, snap: dict[str, bytes | None]) -> None:
    """回滚到跑之前: HEAD 回到旧值, 已跟踪脏文件字节原样写回(未跟踪文件不受影响)。"""
    git("reset", "--hard", head, check=False)
    for path, data in snap.items():
        target = Path(path)
        try:
            if data is None:
                if target.exists():
                    target.unlink()
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
        except OSError:
            pass


def _resolve_behind_overlap(rsha: str, cfg: dict, head: str) -> int | None:
    """落后 + 本地脏与远端改动重叠: 重叠全在生成物白名单 → 丢弃本地那份 + 快进 + 重跑。

    成功返回重跑的处数; 任一前提不成立或中途失败 → 回滚并返回 None(调用方退回现状失败行)。
    """
    whitelist = _whitelist(cfg)
    if not whitelist:
        return None
    overlap = _remote_changed(rsha) & _modified_paths()
    if not overlap or not overlap <= whitelist:
        return None
    if any(not _in_head(p) for p in overlap):
        return None  # 本地删除 / 改名 / 未跟踪 —— 异常状态, 不猜意图
    root = _repo_root()
    if not _self_check(cfg, root):
        return None  # 预检: 生成器健康且当前生成物自洽 —— 不成立就不动任何东西
    snap = _snapshot_dirty()
    for path in sorted(overlap):
        if git_run("checkout", "HEAD", "--", path).returncode != 0:
            _restore(head, snap)
            return None
    if git_run("merge", "--ff-only", rsha).returncode != 0:
        _restore(head, snap)
        return None
    if not _regen(cfg, root) or not _self_check(cfg, root):
        _restore(head, snap)
        return None
    return len(overlap)


def _git_run_editor(*args: str) -> subprocess.CompletedProcess:
    """带 GIT_EDITOR=true 的 git 调用 —— `rebase --continue` 不带它会在编辑器上挂住。"""
    return subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={
            **os.environ, "GIT_EDITOR": "true"
        }
    )


def _resolve_rebase(rsha: str, cfg: dict, ahead: int, head: str) -> tuple[bool, int]:
    """分叉 rebase 的**有界冲突循环**。返回 (ok, 重跑处数); 失败时已 --abort / 回滚, 状态与跑之前一致。

    单次 rebase 一旦停下就取冲突集: 全在生成物白名单 → 取一侧 + 重跑 + 自证 + continue;
    出现任何手写冲突 / 白名单取不到 / 超限 → abort。循环上限 = 本地独有提交数 + 1(防死循环)。
    """
    root = _repo_root()
    limit = ahead + 1
    resolved = 0
    proc = git_run("rebase", rsha)
    if proc.returncode == 0:
        return True, 0  # 无冲突 —— 与现状逐字一致, 不做任何重跑
    whitelist = _whitelist(cfg)
    if not whitelist:
        git("rebase", "--abort", check=False)
        return False, 0
    steps = 0
    while proc.returncode != 0 and steps < limit:
        steps += 1
        conflicts = {
            line.strip()
            for line in git("diff", "--name-only", "--diff-filter=U", check=False).splitlines() if line.strip()
        }
        if not conflicts or not conflicts <= whitelist:
            git("rebase", "--abort", check=False)
            return False, 0
        for path in sorted(conflicts):
            git_run("checkout", "--ours", "--", path)  # rebase 里 --ours = 上游侧; 取哪侧无所谓, 马上被重写
        if not _regen(cfg, root) or not _self_check(cfg, root):
            git("rebase", "--abort", check=False)
            return False, 0
        resolved += len(conflicts)
        git_run("add", "--", *sorted(conflicts))
        proc = _git_run_editor("rebase", "--continue")
    if proc.returncode != 0:
        git("rebase", "--abort", check=False)
        return False, 0
    # 收尾再自证: 多提交重放时, 中间那次重跑基于「部分重放」的树 → tip 上可能仍是中间态。
    if not _regen(cfg, root):
        git("reset", "--hard", head, check=False)
        return False, 0
    dirty = _modified_paths() & whitelist
    if dirty:
        git_run("add", "--", *sorted(dirty))
        if git_run("commit", "--amend", "--no-edit").returncode != 0:
            git("reset", "--hard", head, check=False)
            return False, 0
        resolved += len(dirty)
    if not _self_check(cfg, root):
        git("reset", "--hard", head, check=False)
        return False, 0
    return True, resolved


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
        if proc.returncode == 0:
            return True, f"同步成功 {git('rev-parse', 'HEAD')[:8]}"
        if cfg.get("auto_resolve_generated", True):  # 重叠全在生成物上 → 自动化解
            count = _resolve_behind_overlap(rsha, cfg, head)
            if count is not None:
                return True, f"同步成功 {git('rev-parse', 'HEAD')[:8]} {GENERATED_MARK} {count} 处"
        reason = ("本地改动与远端新提交重叠" if "would be overwritten" in (proc.stderr or "") else _git_reason(proc))
        return False, (
            f"{DIRTY_BLOCK_MARK} 本地{head[:8]} 远端{rsha[:8]} —— {reason}; "
            f"「先提交」解不开(ship.commit 内部第一步就是这条同步, 必再撞同一处) —— 解锁: {UNLOCK_STEPS}"
        )

    # 分叉 → rebase 保持线性(D1); 树脏不做 —— rebase 会拒绝, 与其让 git 报生码不如自己说人话
    if staged or unstaged:
        return False, (
            f"{DIRTY_BLOCK_MARK} 本地{head[:8]} 远端{rsha[:8]} —— 已分叉且工作区脏, rebase 需干净工作区; "
            f"「先提交」解不开(提交入口第一步还是这条同步) —— 解锁: {UNLOCK_STEPS}"
        )
    conflict_line = (f"需解决冲突 本地{head[:8]} 远端{rsha[:8]} —— rebase 已自动回滚, "
                     "手动合流(解冲突)后重跑")
    if cfg.get("auto_resolve_generated", True):  # 冲突全在生成物上 → 有界循环自动化解
        ok, count = _resolve_rebase(rsha, cfg, ahead, head)
        if ok:
            tail = f" {GENERATED_MARK} {count} 处" if count else ""
            return True, f"同步成功 {git('rev-parse', 'HEAD')[:8]}{tail}"
        return False, conflict_line
    proc = git_run("rebase", rsha)
    if proc.returncode != 0:
        git("rebase", "--abort", check=False)  # 全量自动回滚: 失败后仓库与跑之前一致
        return False, conflict_line
    return True, f"同步成功 {git('rev-parse', 'HEAD')[:8]}"


def main(argv: list[str] | None = None) -> int:
    import argparse

    # ❗参数入口的判据(2026-10-03 定性, 修 `argv or []`):
    #   `argv is None`  = **CLI 直跑** —— 必须吃真实 sys.argv, 否则 `--help` / `--safety` /
    #                    任何陌生参数都被当"无参", 直接下沉到 run_sync() 真跑一次同步
    #                    (冒烟闸门就在跑 `sync.py --help`; push.py 同款更危险, 会真推)。
    #   显式空表([])     = 测试里裸调的动作入口 —— 语义不变(不吃 pytest 自己的 sys.argv)。
    # 两种调用方各有明确入口, 不再靠 `or []` 把二者混成一个。
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--safety", action="store_true", help="回答「无参跑我是否即真动作」(冒烟安全过滤用)")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if args.safety:  # 冒烟安全过滤的探针: 只答常量, 不碰 git
        print("sync.py: action-without-args")
        return 0
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
