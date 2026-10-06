"""同步本地分支到主线 —— fetch + 快进 / rebase。输出契约 v3.1(承接 v3 计划 26-09-28-0157)。

v3「成功一行, 失败一行(原因 + 下一步)」保留, **结果行逐字不动**; v3.1 只补一件事 ——
**步骤**: 真发生了的、尤其改写了 HEAD 的步骤, 在结果行**上面**按发生顺序各吐一行, 改写必带
`旧hash→新hash`, 相邻两步首尾相接(详细说明与三条登记纪律见 `_pipeline.py`「步骤登记」段)。

  齐平 / 本地领先  → 无步骤, 已同步 <hash>(两者都没改写 HEAD)
  纯落后          → git merge --ff-only <远端tip>; 树脏交 git 裁决 —— 无重叠自然成功, 重叠被拒 → 同步成功 <hash>
  分叉(树净)      → git rebase <远端tip>: 只改写按定义未推送的本地独有提交, 历史保持线性;
                    中途冲突 → --abort 全量自动回滚 → 同步成功 <新hash>
  树脏挡路(上两类的脏分支) → 失败, 失败行自带**两条出路**: stash 解锁配方 UNLOCK_STEPS(脚本仍不代做
                    清理)或提交先行(ship.commit 已改先提交后同步, 2026-10-04)

为什么要补: 一次同步内部 HEAD 会被改写多次(rebase 重放、生成物重跑后 amend), 而结果行只给终值 ——
执行者看到 hash 与印象不符就会去查原因(2026-10-06 用户指出), 这一行忧虑比噪音贵。

生成物冲突自动化解(计划 26-10-03-1544, 默认开; 键 auto_resolve_generated / generated_*_cmd):
  快进被拒 / rebase 冲突时, 若重叠 / 冲突**全部**落在生成物白名单(`generated_list_cmd` 的 --list)上,
  则「任取一侧 + 重跑生成器 + --check 自证」自动化解, 成功行带「自动重跑生成物 N 处」标记。
  只要有一个手写文件参与, 或白名单 / 重跑 / 自证任一步取不到, 一律**退回上面的失败行**(不猜、不部分解决)。
  为什么敢默认开: 生成器是纯函数(内容只由工作树里的手写文件决定), 重跑后自证通过 = 文件确实等于
  生成结果 ⇒ 证明没有手写内容被丢弃。白名单是唯一权威来源(生成器自己的 --list), 不在这里再抄一份。
  ⚠ **配置自身也会被换掉**: 本包配置就在仓库里, 而这一步的头一件事就是把树推到上游 tip —— 上游那笔
  若改了 `.my-commit-flow.toml`(白名单来源 / 重跑命令 / 开关), 必须按**磁盘现版本**重取后再用
  (`_reload_cfg`), 否则就是"拿旧政策处置合并后的树": 旧白名单放宽 = **静默丢内容**, 旧重跑命令 =
  重跑的是旧生成器(自证也自证的是旧规则)。重取不成立(读不到 / 有 STOP 级问题 / 新配置把
  `auto_resolve_generated` 关掉了)→ **放弃自动化解**, 回滚后退回上面的现状失败行(自动化解是优化,
  不是必须; 不为它新增失败模板)。

注: 树脏类失败行为什么必须自带出路(2026-10-03 定, 2026-10-04 更新): 只说「先提交或移出后重跑」会让执行者
  原地打转 —— 单独重跑 sync 树还是脏的, 必再撞同一处。出路两条: ① stash 移出 → 同步 → pop 弹回(两处改动
  上下文不重叠时自动合并, 实测零冲突); ② 提交先行 —— ship.commit 已改为先提交后同步(2026-10-04), 树净
  rebase 恒可自动, 与远端的冲突改在 rebase 时暴露。「先提交是死锁」的旧论断随 ship.commit 顺序翻转作废。

判据纪律: 判落后只用 ls-remote 现查的远端真值对比本地 HEAD —— refs/remotes/* 的写入在本环境
会被静默丢弃, `status -sb` 的 ahead/behind 是快照, 都不可信(单点: memory-bank/pitfalls/git/refs.md)。
合并/变基失败一律自动回滚现场, sync 失败后仓库状态与跑之前一致 —— 写状态的命令必须比只读的更干净地失败。

网络容错(2026-10-06): 本脚本每条 git 命令都走 `_pipeline.run_git` —— **单次超时 20s + 有界重试**
(push / fetch / ls-remote 这类网络子命令**失败即重试**, 默认 3 次, 全部失败才判失败; 非幂等的本地写
只给超时、不给重试)。Gitee 间歇性卡住时旧行为要等满 120s 才失败一次 ⇒ 提交被拆成「未推送 + 手工补推」,
现在在同一条命令里自愈。三档判据单点在 `_pipeline._retryable`。

用法: python <包>/scripts/sync.py   (无旗标; 引擎任务 my-commit-flow.sync)
退出码: 0 已同步 / 同步成功 · 1 失败(输出自带原因, 不存在需要查的码表)
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# Windows GBK 控制台兑底(与包内其它脚本同根): 输出含非常用字符时编不出来会 UnicodeEncodeError。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _pipeline import (  # noqa: E402
    changed_files,
    emit_steps,
    expand_run,
    git,
    git_run,
    reload_config,
    retry_note,
    run_git,
    staged_overflow,
    step,
)
from _ship_config import CONFIG_NAME, ConfigMissing, load_config, resolve_branch, resolve_main_remote  # noqa: E402


def remote_sha(name: str, branch: str) -> str:
    """取远端 ref 真值(空串 = 取不到)。**取不到 ≠ 不一致** —— 调用方按「无法核实」如实说。

    「重试」已下沉到 git 层(`_pipeline.run_git`: 网络子命令失败即重试, 单次超时 20s) ——
    这里**不再套第二层**, 否则 ls-remote 会被重试 9 次, 离线时白等三个退避周期(2026-10-06)。
    """
    out = git("ls-remote", name, branch, check=False)
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1] == f"refs/heads/{branch}":
            return parts[0]
    return ""


# 树脏挡路的**解锁配方** —— 两类脏分支失败行都必须带上它(不带 = 双向死锁, 见模块 docstring)。
# `-u` 必带: 收尾产物常是未跟踪新文件(新档案 / 新切片 / 新 pitfall), 默认 stash 不收未跟踪,
# 快进仍会被它们挡住; pop 时远端不会新增同名文件, 实测无冲突。高风险同步前照例 `cp -a .git <仓库外备份>`。
UNLOCK_STEPS = (
    "git stash push -u → commands run my-commit-flow.sync → git stash pop → "
    "测试 → commands run ship.commit"
)

# 树脏类失败行的固定前缀 —— 供调用方 / 测试辨认「本地改动挡住同步」这一类(ship.commit 翻转后提交路径
# 树净不再撞它, 只剩独立 sync 的树脏场景; 2026-10-04)。
DIRTY_BLOCK_MARK = "树脏挡路"


def is_dirty_block(line: str) -> bool:
    """失败行是不是「本地改动挡住同步」这一类 —— 独立 sync 场景按 UNLOCK_STEPS 解锁, 或改走提交先行。"""
    return line.startswith(DIRTY_BLOCK_MARK)


def _git_reason(proc) -> str:
    """git 失败 stderr 里最后一行人话(hint 行滤掉) —— 失败行的「原因」段。

    真重试过(网络子命令)就在后面缀上次数: 否则读的人只看到一次失败原因, 不知道命令其实
    已经自己重试过 3 次 —— 那会让人以为是「没重试就报错」而去手工补跑。
    """
    lines = [l.strip() for l in (proc.stderr or "").splitlines() if l.strip() and not l.startswith("hint:")]
    return f"{lines[-1] if lines else 'git 非 0'}{retry_note(proc)}"


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


def _reload_cfg(cfg: dict) -> dict | None:
    """树被自我改写后按**磁盘现版本**重取配置, 并确认新配置仍允许自动化解; 任一不成立 → None。

    为什么必须重取: 自动化解的第一步就是把树推到上游 tip(`git rebase` / `merge --ff-only`), 而**本包
    配置就在仓库里**(`.my-commit-flow.toml` 随包走) —— 上游那笔若换了白名单来源 / 重跑命令 / 开关,
    继续用启动那份就是**拿旧政策处置合并后的树**: 白名单**放宽** = 静默丢内容(把新政策不再认作生成物
    的路径当生成物丢掉), **收窄** = 该保的没保; `generated_regen_cmd` 换了则重跑的是旧生成器(自证也
    自证的是旧规则)。与 `_pipeline.reload_config` 同一判据(磁盘现版本 + STOP 级复检)。

    三档判据(任一不成立即放弃自动化解, 退回现状失败行 —— 自动化解是**优化**, 不是必须, 所以这里的
    "停"是回滚 + 现状失败行, 不是新增失败模板):
      ① 读不到配置 / 新配置有 STOP 级问题(`reload_config` 的停止原因);
      ② 新配置把 `auto_resolve_generated` 关掉了 —— 合并后的政策就是"不要自动丢生成物"。
    """
    fresh, problem = reload_config(cfg)
    if problem or not fresh.get("auto_resolve_generated", True):
        return None
    return fresh


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
    # 树已换成上游版本 —— 配置(白名单来源 / 重跑命令 / 开关)可能也跟着换了: 拿启动那份继续跑, 就是
    # "用旧政策丢本地内容"。**丢了的那几处也要按新白名单复核**: 新政策若不再认它们是生成物, 就得回滚。
    fresh = _reload_cfg(cfg)
    fresh_whitelist = _whitelist(fresh) if fresh else None
    if not fresh_whitelist or not overlap <= fresh_whitelist:
        _restore(head, snap)
        return None
    if not _regen(fresh, root) or not _self_check(fresh, root):
        _restore(head, snap)
        return None
    return len(overlap)


def _git_run_editor(*args: str) -> subprocess.CompletedProcess:
    """带 GIT_EDITOR=true 的 git 调用 —— `rebase --continue` 不带它会在编辑器上挂住。

    同样走 `run_git`(单次超时 20s): 裸 `subprocess.run` 在 Windows 上会无限挂住(根因见
    `_pipeline.run_capture` 的注释)。`rebase` 属**非幂等**子命令 ⇒ 只给超时、不重试 ——
    超时被杀时 rebase 可能已经落地, 再来一次会把 "no rebase in progress" 当成失败。
    """
    return run_git(["git", *args], env={**os.environ, "GIT_EDITOR": "true"})


def _resolve_rebase(rsha: str, cfg: dict, ahead: int, head: str) -> tuple[bool, int, str, str]:
    """分叉 rebase 的**有界冲突循环**。返回 (ok, 重跑处数, rebase 刚落地的 hash, amend 后的 hash);
    末位空串 = 收尾没 amend; 失败时已 --abort / 回滚, 状态与跑之前一致。

    后两个返回值是给调用方写步骤行用的 —— 本函数**不登记步骤**: 两行痕迹必须按发生顺序
    (先「rebase 重放」再「重跑后 amend」)排在结果行上面, 而 rebase 那一行只有拿到本函数的返回值
    才拼得出来。谁登记谁就会把顺序写反(amend 先于 rebase 记录 ⇒ 打印出的链子是倒的), 所以
    干脆把「怎么排」交给唯一知道全局顺序的调用方。

    单次 rebase 一旦停下就取冲突集: 全在生成物白名单 → 取一侧 + 重跑 + 自证 + continue;
    出现任何手写冲突 / 白名单取不到 / 超限 → abort。循环上限 = 本地独有提交数 + 1(防死循环)。

    ❗**每轮开头按磁盘现版本重取配置**(见 `_reload_cfg`): 树被 rebase 往上游推的同时, 本包配置
    (白名单来源 / 重跑命令 / 开关)也可能被上游那笔换掉 —— 拿启动那份判「冲突 ⊆ 白名单」是**静默丢内容**
    (旧白名单放宽时把新政策不认的路径当生成物丢掉); 重取不成立即 abort 回滚。
    """
    root = _repo_root()
    limit = ahead + 1
    resolved = 0
    proc = git_run("rebase", rsha)
    if proc.returncode == 0:
        return True, 0, git("rev-parse", "HEAD", check=False), ""  # 无冲突 —— 与现状逐字一致, 不做任何重跑
    steps_done = 0
    while proc.returncode != 0 and steps_done < limit:
        steps_done += 1
        # 每轮开头重取配置: 上一轮(rebase 本身 / `--continue`)已把树往上游推, 而本包配置就在仓库里 ——
        # 上游那笔若换了白名单来源 / 重跑命令 / 开关, 继续用旧政策判「冲突 ⊆ 白名单」会**静默丢内容**。
        fresh = _reload_cfg(cfg)
        whitelist = _whitelist(fresh) if fresh else None
        if not whitelist:
            git("rebase", "--abort", check=False)
            return False, 0, "", ""
        cfg = fresh
        conflicts = {
            line.strip()
            for line in git("diff", "--name-only", "--diff-filter=U", check=False).splitlines() if line.strip()
        }
        if not conflicts or not conflicts <= whitelist:
            git("rebase", "--abort", check=False)
            return False, 0, "", ""
        for path in sorted(conflicts):
            git_run("checkout", "--ours", "--", path)  # rebase 里 --ours = 上游侧; 取哪侧无所谓, 马上被重写
        if not _regen(cfg, root) or not _self_check(cfg, root):
            git("rebase", "--abort", check=False)
            return False, 0, "", ""
        resolved += len(conflicts)
        git_run("add", "--", *sorted(conflicts))
        proc = _git_run_editor("rebase", "--continue")
    if proc.returncode != 0:
        git("rebase", "--abort", check=False)
        return False, 0, "", ""
    landed = git("rev-parse", "HEAD", check=False)  # rebase 刚落地的 tip; 之后还可能被 amend 挪走
    # 收尾再取一次: 最后一笔重放的是**本地**提交, 它也可能改了配置 —— 终值才算数(白名单同样复核)
    fresh = _reload_cfg(cfg)
    whitelist = _whitelist(fresh) if fresh else None
    if not whitelist:
        git("reset", "--hard", head, check=False)
        return False, 0, "", ""
    cfg = fresh
    amended = ""
    # 收尾再自证: 多提交重放时, 中间那次重跑基于「部分重放」的树 → tip 上可能仍是中间态。
    if not _regen(cfg, root):
        git("reset", "--hard", head, check=False)
        return False, 0, "", ""
    dirty = _modified_paths() & whitelist
    if dirty:
        git_run("add", "--", *sorted(dirty))
        if git_run("commit", "--amend", "--no-edit").returncode != 0:
            git("reset", "--hard", head, check=False)
            return False, 0, "", ""
        resolved += len(dirty)
        amended = git("rev-parse", "HEAD", check=False)
    if not _self_check(cfg, root):
        git("reset", "--hard", head, check=False)
        return False, 0, "", ""
    return True, resolved, landed, amended


def _step_rebase(steps: list[str] | None, behind: int, ahead: int, head: str, new: str) -> None:
    """分叉 rebase 的步骤行 —— 这一步是 hash 变化的头号疑惑源: 本地提交内容没变, 但重放到远端
    tip 上必然重写 hash, 不写明就会有人去查「我的提交哪去了」。"""
    step(steps, f"同步: 远端领先 {behind} 笔 · 本地领先 {ahead} 笔(分叉) → "
         f"rebase 重放本地 {ahead} 笔 {head[:8]}→{new[:8]}")


def run_sync(steps: list[str] | None = None) -> tuple[bool, str]:
    """核心动作。返回 (ok, line): 成功时 line 是完整结果行(已同步/同步成功 <hash>);
    失败时 line 是「同步失败」的**后缀** —— 冲突场景以「需解决冲突 本地<x> 远端<y> …」开头,
    main 拼上「同步失败」后正好是约定模板「同步失败需解决冲突 本地<x> 远端<y> <步骤>」。
    缺配置等停止类问题 line 以「[STOP]」开头, main 原样打印。

    `steps` 是 v3.1 的步骤登记簿(见 `_pipeline.step` 的三条纪律): 由入口持有并打印,
    传 None = 不要痕迹(现状行为)。改写 HEAD 的每一步都在这里登记 `旧hash→新hash`。
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
    rsha = remote_sha(main, branch)
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
        # 本地领先(未推送) —— 推送即快进, 同步无事可做。**不登记步骤**: 登记纪律②只认
        # 改写了 HEAD 的步骤, 这里一个都没改写; 「跑了但什么都没做」本身就是噪音。
        return True, f"已同步 {head[:8]}"

    if ahead == 0:  # 纯落后 → 快进; 树脏与否交 git 裁决(无重叠自然成功)
        proc = git_run("merge", "--ff-only", rsha)
        if proc.returncode == 0:
            step(
                steps, f"同步: 远端领先 {behind} 笔 → 快进 {head[:8]}→{git('rev-parse', 'HEAD')[:8]}" +
                (" · 本地未提交改动原样保留" if (staged or unstaged) else "")
            )
            return True, f"同步成功 {git('rev-parse', 'HEAD')[:8]}"
        if cfg.get("auto_resolve_generated", True):  # 重叠全在生成物上 → 自动化解
            count = _resolve_behind_overlap(rsha, cfg, head)
            if count is not None:
                new = git("rev-parse", "HEAD")[:8]
                step(steps, f"同步: 远端领先 {behind} 笔 · 重叠 {count} 处全在生成物 → "
                     f"丢弃本地那份后快进 {head[:8]}→{new}")
                return True, f"同步成功 {new} {GENERATED_MARK} {count} 处"
        reason = ("本地改动与远端新提交重叠" if "would be overwritten" in (proc.stderr or "") else _git_reason(proc))
        return False, (
            f"{DIRTY_BLOCK_MARK} 本地{head[:8]} 远端{rsha[:8]} —— {reason}; 出路二选一: "
            f"不提交先同步 {UNLOCK_STEPS}; 或工作已完成待入库 → commands run ship.commit"
            f"(提交先行, 与远端的冲突改在 rebase 时暴露)"
        )

    # 分叉 → rebase 保持线性(D1); 树脏不做 —— rebase 会拒绝, 与其让 git 报生码不如自己说人话
    if staged or unstaged:
        return False, (
            f"{DIRTY_BLOCK_MARK} 本地{head[:8]} 远端{rsha[:8]} —— 已分叉且工作区脏, rebase 需干净工作区; "
            f"出路二选一: 不提交先同步 {UNLOCK_STEPS}; 或工作已完成待入库 → commands run ship.commit"
            f"(提交先行, 树净 rebase 恒可自动)"
        )
    conflict_line = (f"需解决冲突 本地{head[:8]} 远端{rsha[:8]} —— rebase 已自动回滚, "
                     "手动合流(解冲突)后重跑")
    if cfg.get("auto_resolve_generated", True):  # 冲突全在生成物上 → 有界循环自动化解
        ok, count, landed, amended = _resolve_rebase(rsha, cfg, ahead, head)
        if ok:
            tail = f" {GENERATED_MARK} {count} 处" if count else ""
            # 两行痕迹按发生顺序登记: 先 rebase 重放, 再收尾重跑导致的 amend —— 顺序反了链子就倒了
            _step_rebase(steps, behind, ahead, head, landed)
            if amended:
                step(steps, f"同步: 生成物自动重跑后 amend {landed[:8]}→{amended[:8]}")
            return True, f"同步成功 {git('rev-parse', 'HEAD')[:8]}{tail}"
        return False, conflict_line
    proc = git_run("rebase", rsha)
    if proc.returncode != 0:
        git("rebase", "--abort", check=False)  # 全量自动回滚: 失败后仓库与跑之前一致
        return False, conflict_line
    _step_rebase(steps, behind, ahead, head, git("rev-parse", "HEAD"))
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
    steps: list[str] = []  # 步骤登记簿由入口持有(见 _pipeline 的「步骤登记」段纪律)
    ok, line = run_sync(steps)
    if ok:
        emit_steps(steps)
        print(line)
        return 0
    if line.startswith("[STOP]"):
        emit_steps(steps)
        print(line)
    else:
        # 冲突场景 line 以「需解决冲突 本地<x> 远端<y> …」开头 —— 无缝拼接后正好是
        # 约定模板「同步失败需解决冲突 本地<x> 远端<y> <步骤>」; 其余失败用冒号分隔。
        # 失败行前的步骤行照旧吐: 失败虽已自动回滚, 但结果行里的 hash 指的是回滚后的 HEAD,
        # 把「期间 tip 到过哪」摆出来, 才不会让人怀疑回滚漏了东西。
        sep = "" if line.startswith("需解决") else ": "
        emit_steps(steps)
        print(f"同步失败{sep}{line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
