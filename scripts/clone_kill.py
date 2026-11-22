"""按 clone 域定点清理本 clone 残留进程 — dev-only

第一用户故事(2026-11-22): `commands run dev.run -- config.yml --dry-run` 是守护循环
(src/auto_qb/cli.py:305 `manager.run(args.dry_run)` -- dry 只压动作, 循环永续), 后台
任务被停/会话收尾只杀 bash/uv 包装链, python 子进程孤儿化继续持 state 锁、周期落盘。
这是 port_kill docstring 记录的「杀包装不死子」形态(pitfalls/testing/harness-save-flow.md)
在 dev.run 守护循环上的再现(取证与判别见 pitfalls/ops/dev-run-dry-run-daemon-orphan.md)。
此类残留多数不监听端口(干跑探针的 webui/HR 口被占时静默不绑), port_kill 的端口定位
管不到, 只剩 cmdline 归属一条路 -- 本工具按归属定点, 与 port_kill(按端口定点)互补。

身份判据(2026-11-22 拍板): import 复用 port_kill 的 in_clone_domain + REPO_ROOT
(不复制 -- 两个工具共用同一归属语义, 判据不各自演化): cmdline 归一化后带分隔符
边界的仓库根前缀匹配, 查不到 cmdline / 不含本 clone 仓库根 = 一律不杀(fail-closed)。
已知盲区接受: uv 包装进程的 cmdline 常是相对形态(`uv run python scripts/dev_run.py`,
不含仓库根)杀不到 -- 杀掉 python 子进程后包装自退。

交互面(2026-11-22 拍板): 默认只列(候选行带 pid/进程名/cmdline); 杀必须 --match +
--yes 双闸缺一不可, --match 是 cmdline 的小写子串过滤(非正则)。依据: bash 瞬态的
命令文本也含 clone 根(实测), 且 clone 域分不出「本会话残留」与「并发会话活体」--
「杀全部 clone 域」这个表达从工具里物理删掉; --yes 而 --match 缺失直接 rc=2 拒跑。

自杀面(2026-11-22 拍板): 工具自身经 commands 引擎跑在本 clone .venv 下, 自身 +
祖先链(bash/uv/python)全在 clone 域内, 且自身 cmdline 还含 --match 关键词 -- 硬编码
排除自身 pid + 祖先链(PPID 上溯到根), 非配置项。

杀树(2026-11-22 拍板): 每个过闸目标枚举后代闭包(PPID 递归), 后代逐个过同一闸
(归属 + 排除)后一并杀, 后代先杀(深度降序) -- 连坐但要过闸, 不是无条件树杀; 后代里
clone 域外的进程(如产品拉起的 explorer)被 fail-closed 闸保住, REFUSED 行如实记账。

平台双支: 与 port_kill 同构 -- nt 走 Win32_Process 全量枚举, POSIX 走 /proc 扫描;
实杀一律经 port_kill._kill_pid 单点(import 私名: 实杀路径复制一分就有了第二个
taskkill 调用点, 两个工具共用同一单点)。守阵把 os.name 钉成 posix + 假 /proc 树,
任一平台跑(tests/test_clone_kill_script.py)。

红线豁免(AGENTS.md 进程安全节, 2026-11-22 拍板追加第三处): 本脚本的一切杀都过
归属闸; AI 代理在 shell 直接执行 taskkill 仍一律禁止。

用法:
    commands run dev.clone-kill --                       # 列出 clone 域候选(只读)
    commands run dev.clone-kill -- --match dev_run       # 列出 match 命中子集(只读)
    commands run dev.clone-kill -- --match dev_run --yes # 杀命中目标 + 过闸后代
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

# port_kill 判据/仓库根/实杀单点, import 复用不复制(e2e_selfcheck 同款先例, 计划
# 26-11-13-0234); sys.path 先插 scripts/ 目录再 import, spec 加载(守阵)同样成立。
sys.path.insert(0, str(Path(__file__).resolve().parent))
from port_kill import REPO_ROOT, _kill_pid, in_clone_domain  # noqa: E402

# POSIX 支的 /proc 根单点(守阵用假 /proc 树钉双支, 与 port_kill.PROC_ROOT 同款)
PROC_ROOT = "/proc"

#: 归属行展示截断口径(port_kill 同款)
_SHOW_MAX = 160


def _show(cmdline: str) -> str:
    """归属行展示单点: 超长截断, 与 port_kill 同口径。"""
    return cmdline if len(cmdline) <= _SHOW_MAX else cmdline[:_SHOW_MAX - 3] + "..."


def _scan_processes_nt() -> dict:
    """nt 支全量枚举: Win32_Process 一把查全(ProcessId/Name/CommandLine/ParentProcessId)。

    与 port_kill.process_info 同语义: 查询整体失败(非零 rc / JSON 解析不动)返回空表
    -- main 视空表为 verify-failed 形态, fail-safe 拒绝一切杀; 单个进程行缺
    ProcessId/Name 则跳过该行; CommandLine 为 null(部分系统进程)记空串, 归属闸对
    空串恒 False(fail-closed), 自然出局。
    """
    ps = (
        "$r = Get-CimInstance Win32_Process | "
        "Select-Object ProcessId,Name,CommandLine,ParentProcessId; "
        "ConvertTo-Json -InputObject @($r) -Compress"
    )
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    out = (r.stdout or "").strip()
    if r.returncode != 0 or not out:
        return {}
    try:
        data = json.loads(out)
    except ValueError:
        return {}
    if isinstance(data, dict):  # some PS hosts unwrap a single-element array
        data = [data]
    procs = {}
    for row in data or []:
        pid = row.get("ProcessId")
        name = row.get("Name")
        if pid is None or not name:
            continue
        procs[int(pid)] = (str(name), str(row.get("CommandLine") or ""), int(row.get("ParentProcessId") or 0))
    return procs


def _scan_processes_posix() -> dict:
    """POSIX 支全量枚举: /proc/<pid>/{comm,cmdline,stat} 直读。

    stat 的 ppid 取 rpartition(")") 后第 2 个字段 -- comm 可含空格/括号, 裸 split
    会错位。读不了的 pid 缺席(raced exit / 别用户 /proc 权限), 与 port_kill 的
    verify 语义一致: 缺席 = 查不到, 不误报也不盲杀。
    """
    procs = {}
    for entry in os.listdir(PROC_ROOT):
        if not entry.isdigit():
            continue
        try:
            with open(PROC_ROOT + "/" + entry + "/comm", "r", encoding="utf-8", errors="replace") as fh:
                name = fh.read().strip()
            with open(PROC_ROOT + "/" + entry + "/cmdline", "rb") as fh:
                cmdline = fh.read().decode("utf-8", "replace").replace("\0", " ").strip()
            with open(PROC_ROOT + "/" + entry + "/stat", "r", encoding="utf-8", errors="replace") as fh:
                stat_tail = fh.read().rpartition(")")[2].split()
        except OSError:
            continue
        if not name:
            continue
        ppid = 0
        if len(stat_tail) >= 2:
            try:
                ppid = int(stat_tail[1])  # stat_tail[0]=state, [1]=ppid
            except ValueError:
                ppid = 0
        procs[int(entry)] = (name, cmdline, ppid)
    return procs


def scan_processes() -> dict:
    """全量进程表: pid -> (name, cmdline, ppid)。按 os.name 分派, 两支判据一致。"""
    if os.name != "nt":
        return _scan_processes_posix()
    return _scan_processes_nt()


def self_and_ancestors(procs: dict, self_pid: int | None = None) -> set:
    """自身 + 祖先链排除集(硬编码非配置): 从自身 PPID 一路上溯到仓库外。

    祖先不管是否 clone 域一律排除 -- 这是「本工具自己的调用链」(bash/uv/python),
    不是候选; 自身 cmdline 还含 --match 关键词, 不排除必自杀。祖先不在进程表
    (raced exit / 权限)即停; PPID 成环用 visited 兜底, 不死循环。
    self_pid 参数只给守阵注入假自身(生产恒 os.getpid())。
    """
    pid = os.getpid() if self_pid is None else self_pid
    excluded = {pid}
    seen = set()
    cur = procs.get(pid)
    while cur is not None:
        ppid = cur[2]
        if not ppid or ppid in seen:
            break
        seen.add(ppid)
        excluded.add(ppid)
        cur = procs.get(ppid)
    return excluded


def select_candidates(procs: dict, match: str | None = None, excluded: set | None = None) -> list:
    """候选筛选纯函数: 全量进程表 -> clone 域候选, pid 升序。

    候选 = 不在排除集(自身 + 祖先链) 且 in_clone_domain(cmdline, REPO_ROOT);
    match 给定时再要求 match 的小写形态是 cmdline 的小写子串(非正则)。
    返回 [(pid, name, cmdline)]。
    """
    if excluded is None:
        excluded = self_and_ancestors(procs)
    out = []
    for pid in sorted(procs):
        if pid in excluded:
            continue
        name, cmdline, _ppid = procs[pid]
        if not in_clone_domain(cmdline, REPO_ROOT):
            continue
        if match is not None and match.lower() not in cmdline.lower():
            continue
        out.append((pid, name, cmdline))
    return out


def build_kill_plan(targets: list, procs: dict, excluded: set) -> list:
    """杀面编排纯函数: 目标 + 各自后代闭包(PPID 递归), 每个成员逐个过同一道闸。

    闸 = in_clone_domain(cmdline, REPO_ROOT) + 排除集; 不过闸的成员 allowed=False
    带原因(outside-repo / self-or-ancestor), main 给 REFUSED 行并记 rc=1 -- 连坐
    但要过闸, 不是无条件树杀。返回 [(pid, name, cmdline, depth, allowed, reason)],
    按 depth 降序(后代先杀)再按 pid 升序; depth 0 = 目标本身, 1+ = 第 N 代后代。
    """
    children = {}
    for pid, (_name, _cmdline, ppid) in procs.items():
        children.setdefault(ppid, []).append(pid)
    seen = set(targets)
    queue = [(pid, 0) for pid in targets]
    walked = []  # (depth, pid, name, cmdline), 发现序(父先于子)
    while queue:
        pid, depth = queue.pop(0)
        name, cmdline, _ppid = procs.get(pid, ("", "", 0))
        walked.append((depth, pid, name, cmdline))
        for child in children.get(pid, []):
            if child in seen or child in excluded:
                continue
            seen.add(child)
            queue.append((child, depth + 1))
    plan = []
    for depth, pid, name, cmdline in walked:
        if pid in excluded:  # 防御面: 目标/后代落在排除集(语义上不可能), 拒杀
            plan.append((pid, name, cmdline, depth, False, "self-or-ancestor"))
        elif not in_clone_domain(cmdline, REPO_ROOT):
            plan.append((pid, name, cmdline, depth, False, "outside-repo"))
        else:
            plan.append((pid, name, cmdline, depth, True, "gated"))
    plan.sort(key=lambda row: (-row[3], row[0]))  # (pid, name, cmdline, depth, ...): 深度降序(后代先杀), 再 pid 升序
    return plan


def main(argv: list) -> int:
    """入口: 无参/仅 --match = 只列; --match + --yes = 杀(双闸缺一即拒, D4)。

    rc: 0 = 只列完成 / 无候选 / 全部杀成; 1 = 有 REFUSED(后代归属不过闸)/扫描空表
    fail-safe 或 kill-failed; 2 = 用法错误(--yes 无 --match / --match 缺值/空值)。
    """
    confirmed = "--yes" in argv
    match = None
    if "--match" in argv:
        i = argv.index("--match")
        if i + 1 >= len(argv) or argv[i + 1] == "--yes":
            print("usage: commands run dev.clone-kill -- [--match <cmdline 子串>] [--yes]")
            print("[clone-kill] --match 需要一个子串参数(杀闸: 杀必须 --match + --yes 双闸)")
            return 2
        match = argv[i + 1]
        if not str(match).strip():
            print("usage: commands run dev.clone-kill -- [--match <cmdline 子串>] [--yes]")
            print("[clone-kill] --match 不能为空/全空白(空子串恒真 = 变相「杀全部 clone 域」, 双闸拒收)")
            return 2
    if confirmed and match is None:
        print("usage: commands run dev.clone-kill -- [--match <cmdline 子串>] [--yes]")
        print(
            "[clone-kill] 拒绝无 --match 的杀调用(双闸): clone 域候选混有 bash 瞬态与并发会话活体,"
            " 「杀全部 clone 域」不是合法表达 -- 先 --match 收窄再 --yes"
        )
        return 2
    procs = scan_processes()
    if not procs:
        print("[clone-kill] process scan returned nothing (query failed or raced?) -- refusing to act")
        return 1
    excluded = self_and_ancestors(procs)
    candidates = select_candidates(procs, match=match, excluded=excluded)
    if not candidates:
        print(
            f"[clone-kill] no candidates in clone domain (repo root: {REPO_ROOT})" +
            (f", match: {match!r}" if match else "")
        )
        return 0
    for pid, name, cmdline in candidates:
        print(f"[clone-kill] pid {pid} = {name} : {_show(cmdline)}")
    if not confirmed:
        if match is not None:
            print("[clone-kill] listing only -- 杀须 --match + --yes 双闸齐备(再补 --yes)")
        return 0
    rc = 0
    for pid, name, cmdline, depth, allowed, reason in build_kill_plan(
        [pid for pid, _n, _c in candidates], procs, excluded
    ):
        tag = "target" if depth == 0 else f"descendant-d{depth}"
        if not allowed:
            if reason == "outside-repo":
                # 归属闸拒绝: 显眼 WARNING(port_kill 2026-11-17 加固同款口径)
                print(
                    f"[clone-kill] WARNING: pid {pid} is an OUTSIDE-REPO process"
                    f" (cmdline does not name this clone; repo root: {REPO_ROOT}) -- kill refused"
                )
            print(f"[clone-kill] pid {pid} ({tag}) -> REFUSED({reason})")
            print(f"[clone-kill]   pid {pid} = {name} : {_show(cmdline)}")
            rc = 1
            continue
        if depth > 0:
            # 后代不经候选行(只有 match 命中的目标在列选时打过归属), 实杀前补归属行供人工审计
            print(f"[clone-kill]   pid {pid} = {name} : {_show(cmdline)}")
        ok, detail = _kill_pid(pid)
        print(f"[clone-kill] pid {pid} ({tag}) -> {detail}")
        if not ok:
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
