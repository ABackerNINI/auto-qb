"""提交前预检 —— 不改任何 git 状态, 但**会执行 `auto = true` 的闸门**(可能改工作区)。

用法(**不要写死包的安装路径**, `<包>` = 本包目录(`<仓库根>/.commands/my-commit-flow`)):
    python <包>/scripts/preflight.py [--no-fetch] [--no-auto] [--check-started]
    python <包>/scripts/preflight.py --init           # 生成外置配置初稿(需人工确认)
    python <包>/scripts/preflight.py --show-config     # 打印生效配置与来源

⚠ **不再是"只读"**: `auto = true` 的闸门会被真的执行(测试 / 格式化 / 索引 --check / skill 同步),
可能改写工作区文件。只想看检查表时用 `--no-auto`。

闸门命令里的占位符由本脚本展开(展开不了即 STOP, 不降级成"打印给人"):
    <root>              仓库根绝对路径
    <skill-dir:NAME>    skill 目录(项目级 → 用户级, 找不到即 STOP)
    <changed:GLOB>      本次改动里匹配的文件 → 拼成一条命令
    <each:GLOB>         按匹配文件把这条 run 复制成多条命令(条数上限 each_limit)

**先有配置才预检**: 项目特有项(红线 / 闸门 …)一律来自 `<包>/.my-commit-flow.toml`;
没有配置文件 → 打印引导并停手, 不猜默认值。

输出一张检查表(PASS / WARN / STOP):
- 远端与上游是不是主线(按配置探测)、分支对不对
- 落不落后主线(**push 前也要再跑一次**; 判据 = fetch 后与远端真值对比本地 HEAD, `status -sb` 的 ahead/behind 是快照不可信)
- **合流预判(只读)**: 落后 / 分叉时跑 `git merge-tree --write-tree HEAD <远端 tip>` 报「撞 / 不撞」——
  把冲突从「push 被拒才发现」提前到「提交前就知道」。它只在对象库里算合并树, **不写工作区 / ref / index**;
  拿不到远端 tip 的对象(如 `--no-fetch`)时如实说"无法预判", 不假装。**push 阶段预判到冲突 = STOP**
  (本环境「非快进合并 + 脏工作区 = 必炸」, 得先留备份并把工作区弄干净)
- 开工自检(`--check-started`): **只读** —— ls-remote 对比本地 HEAD + 工作区状态, 不 fetch、不写任何 git 状态, 与其余检查互斥; 结果贴进会话回复。
  落后且**本地已有远端 tip 对象**时, 额外附一行合流预判(仍是只读); 没有对象就省略, 不为凑一行去 fetch
- 工作区脏不脏(脏 + 需要历史整合 = 红线区)
- 改动清单里有没有红线 / 高危文件
- 闸门: `auto = true` 的直接跑(红了即 STOP), 其余列出来给人跑
- 是否需要换平台复现

有 STOP → 退出码 1; 只有 WARN → 0(需人工确认后继续)。开工自检(`--check-started`)的退出码: 0 = 同步齐平可开工; 1 = 需先处理(落后 / 分叉 / 无法验证)。
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import re
import subprocess
import sys
import time
from pathlib import Path

# Windows GBK 控制台兑底(与 commit.py 同根): 闸门/ git 输出含 emoji 时, GBK 编不出来会让
# print 直接 UnicodeEncodeError, 已跑完的检查表/闸门结果被打印中断, 退出码失真。
# 强制 stdout/stderr 走 UTF-8, 编不出时降级 replace 显示。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _ship_config import (  # noqa: E402
    CONFIG_NAME,
    ConfigMissing,
    config_problems,
    find_root,
    find_skill_dir,
    init_config,
    load_config,
    main_matches_mark,
    resolve_branch,
    resolve_main_remote,
    resolve_mirror_remote,
)

PASS, WARN, STOP = "PASS", "WARN", "STOP"


def git(*args: str, check: bool = True) -> str:
    # **不能整段 strip()**: `git status --porcelain` 的首列空格表示"无暂存改动",
    # 整段 strip 会把首行的这个空格吃掉 → ' M a/b' 变成 'M  a/b', 首列被误判成已暂存,
    # 且 line[3:] 丢掉路径首字符(`.agents/...` → `agents/...`), 红线匹配会**静默放行**。
    proc = subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} 失败: {proc.stderr.strip()}")
    return proc.stdout.rstrip("\n")


def git_rc(*args: str) -> int:
    """只关心**退出码**的 git 调用(如 `merge-tree --write-tree`: 0 = 可干净合流, 非 0 = 有冲突)。

    与 `git()` 分开是必要的: 那个函数 `check=False` 时只回 stdout, 而退出码正是这里的信号;
    `cat-file -e` 同理(成功时 stdout 为空, 用它判断"对象在不在"会永远为假)。
    """
    return subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace").returncode


def classify_merge_probe(rc: int | None, phase: str) -> tuple[str, str, str]:
    """合流预判结果 → (级别, 项, 说明) —— 纯函数(便于自测), 不碰 git。

    `rc` 来自 `git merge-tree --write-tree HEAD <远端 tip>`: 0 = 可干净合流, 非 0 = 有冲突。
    `rc is None` = 没预判(拿不到远端 tip 的对象, 如 `--no-fetch`) → 如实说无法预判。
    返回**三元组**(级别 / 项 / 说明)直接进检查表 —— 曾因返回二元组在打印 rows 解包时
    ValueError: not enough values to unpack (expected 3, got 2)。
    """
    if rc is None:
        return (
            WARN,
            "合流预判",
            "无法预判合流冲突(本地没有远端 tip 的对象 —— 先 fetch 主线分支, 或别用 `--no-fetch`)",
        )
    if rc == 0:
        return PASS, "合流预判", "预判**不撞**: 同步后可直接合流(`merge-tree --write-tree` 退出码 0)"
    return (
        STOP if phase == "push" else WARN,
        "合流预判",
        "预判**会撞**: 合流需人工解冲突 —— 本环境「非快进合并 + 脏工作区 = 必炸」, "
        "推送前务必先把工作区弄干净并留好改动备份(树脏就先停下报告)",
    )


def classify_sync(remote_sha: str, head_sha: str, counts: tuple[int, int] | None) -> tuple[str, str]:
    """把开工同步状态分类成 (级别, 说明) —— 纯函数(便于自测), 不碰 git。

    - `remote_sha` 为空 = 远端真值拿不到(离线 / 远端不存在) → WARN, 如实说"无法验证"
    - `head_sha` 为空 = 空仓库 → 跳过对比
    - `counts` 为 None = 本地没有远端 tip 的对象(从未 fetch) → WARN"先 fetch 再重跑"
    """
    if not remote_sha:
        return WARN, "拿不到远端真值(离线或远端不存在) —— 无法验证同步状态, 开工前请人工确认"
    if not head_sha:
        return WARN, "本地没有任何提交(空仓库) —— 跳过对比"
    if remote_sha == head_sha:
        return PASS, f"与主线齐平({remote_sha[:8]}) —— 可开工"
    if counts is None:
        return WARN, f"远端在 {remote_sha[:8]}, 本地没有它的对象(从未 fetch?) —— 先 fetch 主线分支再重跑本自检"
    behind, ahead = counts
    if behind == 0:
        return PASS, f"本地领先 {ahead} 个提交(未推送), 远端无新提交 —— 可开工, 推送即快进"
    if ahead == 0:
        return WARN, (
            f"落后 {behind} 个提交 —— 开工前先同步: `git fetch <主线> <分支>` + "
            "`git merge --ff-only FETCH_HEAD`(树脏先停下报告)"
        )
    return WARN, (f"已分叉(本地独有 {ahead} / 远端新 {behind}) —— 可直接开工, "
                  "提交时先同步远端再合流(树脏先停下报告)")


def sync_recipe(behind: int, ahead: int, dirty: int, overlap: list[str], fetch_cmd: str) -> tuple[str, str, str] | None:
    """落后 / 分叉 + 树脏时给出**可执行的下一步** —— 纯函数(便于自测), 不碰 git。

    开工自检只说"先同步, 树脏先停下报告"是不够的: 这句话本身不含动作, 执行者只能自己
    把仓库翻一遍(实测要 6 次只读 git 调用才拼出下一步)。这里把 AGENTS.md 的规范路径
    (先同步后提交, 历史保持线性)落成配方。

    ❗有**文件重叠**时不给配方: 施回会撞, 那已经不是机械步骤了 —— 如实报"先停下报告"
    (与全库「不静默降级」同源)。分叉同理, 只给指针不给配方。
    """
    if behind <= 0:
        return None
    if ahead > 0:
        return (
            WARN,
            "同步路径",
            f"已分叉(本地独有 {ahead} / 远端新 {behind}) —— 按 `references/pipeline.md` 的替代路径同步合流, "
            "**别硬合**(非快进合并前先把工作区弄干净)",
        )
    ff = f"`{fetch_cmd}` + `git merge --ff-only FETCH_HEAD`"
    if not dirty:
        return PASS, "同步路径", f"工作区干净, 直接快进: {ff}"
    if overlap:
        shown = "、".join(overlap[:3]) + ("…" if len(overlap) > 3 else "")
        return (
            WARN,
            "同步路径",
            f"落后 {behind} + 树脏 {dirty}, 且**与远端新提交重叠 {len(overlap)} 个文件**({shown}) —— "
            "施回会撞, **先停下报告**, 不要自己解冲突",
        )
    return (
        WARN,
        "同步路径",
        f"落后 {behind} + 树脏 {dirty}, 与远端新提交**无文件重叠** ⇒ 可走规范路径(先同步后提交): "
        f"①`git diff --output=<仓外>/wip.patch`(改动文件另存一份到仓外) ②`git restore --source=HEAD -- <改动文件>` "
        f"③{ff} ④`git apply --3way --ignore-whitespace <patch>` ⑤`git reset -q` 变回未暂存; "
        "施回后按 `git diff --stat` 与快进前的数字逐项对账",
    )


def behind_rows(
    behind: int, ahead: int, phase: str, dirty: int, overlap: list[str], fetch_cmd: str
) -> list[tuple[str, str, str]]:
    """落后 >0 时「落后主线」相关的检查表行(纯函数, 便于自测); 合流预判要跑 git, 不在这里。

    commit / push 两阶段**都是 STOP**(2026-09-26 起 commit 阶段废除旧 WARN 放行): 旧口径
    「先提交再合流」会让收尾回写落在陈旧基线上 —— baseline.md / activeContext 切片 / 各 _index
    是全体 clone 收尾 DoD 都要写的最热写点, 陈旧基线上写, 合并时必撞(「baseline 总是撞」的根因)。
    """
    if phase == "commit":
        rows: list[tuple[str, str, str]] = [
            (
                STOP,
                "落后主线",
                f"落后 {behind} 个提交 —— **先合并远端, 再收尾回写、后提交**(回写件是全体 clone 的最热写点, "
                "在陈旧基线上写, 合并时 baseline/切片必撞)",
            )
        ]
    else:
        rows = [(STOP, "落后主线", f"落后 {behind} 个提交 —— 先同步合流(**工作区必须干净**); 别等 push 被拒才发现")]
    recipe = sync_recipe(behind, ahead, dirty, overlap, fetch_cmd)
    if recipe:
        rows.append(recipe)
    return rows


def remotes() -> dict[str, str]:
    out: dict[str, str] = {}
    for line in git("remote", "-v").splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[2] == "(push)":
            out[parts[0]] = parts[1]
    return out


def changed_files() -> tuple[list[str], list[str]]:
    """返回 (staged, unstaged) 文件清单(按 `git status --porcelain` 的两列判读)。

    ❗必须带 `-uall`: 默认模式下**未跟踪目录只报一条 `?? <dir>/`**, 于是 `<each:GLOB>` 之类
    按文件的展开**匹配不到新加的文件** —— 新增 skill 脚本拿不到 `--help` 冒烟, 且是静默的。
    """
    staged, unstaged = [], []
    for line in git("status", "--porcelain", "-uall").splitlines():
        if not line.strip():
            continue
        xy = line[:2].ljust(2)  # 短行兜底, 避免索引错位后再切错路径
        path = line[3:].strip() if len(line) > 3 else ""
        if not path:
            continue
        # 重命名在 porcelain 里是 `R  old -> new` —— 取**新**路径, 否则改动清单里
        # 会出现 "old -> new" 这种不存在的路径, `<changed:>` / `<each:>` 静默匹配不到。
        if " -> " in path:
            path = path.split(" -> ")[-1].strip()
        if xy[0] not in (" ", "?"):
            staged.append(path)
        if xy[1] != " ":
            unstaged.append(path)
    return staged, unstaged


def hit(files: list[str], patterns) -> list[str]:
    return [f for f in files if any(f.startswith(p) or p in f for p in patterns)]


def gates_for(files: list[str], gates: list[dict]) -> list[dict]:
    """命中的闸门 —— 返回完整 dict(`auto` / `timeout` 在里头, 后面要靠它们决定"跑不跑")。"""
    return [g for g in gates if hit(files, g.get("match", []))]


# ------------------------------------------------------------------ 占位符展开

PLACEHOLDER_RE = re.compile(r"<[^<>]+>")
EACH_RE = re.compile(r"<each:([^<>]+)>")
CHANGED_RE = re.compile(r"<changed:([^<>]+)>")
SKILL_RE = re.compile(r"<skill-dir:([^<>]+)>")


class ExpandError(RuntimeError):
    """占位符展开失败 —— 调用方必须转成 STOP, **不降级**成"打印给人"。"""


def _quote(path: str) -> str:
    return path if not re.search(r"\s", path) else f'"{path}"'


def _short(cmd: str, root) -> str:
    """命令里的仓库根绝对路径换成 `.` —— 明细行里那段前缀是常量, 每次重复纯属占地方。

    两种分隔符都试: 展开出来的命令可能用 `/`(占位符来自配置)也可能用 `\\`(来自 git)。
    """
    for form in sorted({str(root), str(root).replace("\\", "/")}, key=len, reverse=True):
        cmd = cmd.replace(form + "/", "").replace(form + "\\", "").replace(form, ".")
    return cmd


def _glob_match(path: str, pattern: str) -> bool:
    """改动清单里的路径是否匹配 GLOB: 支持 `**/`(跨目录)与 fnmatch 语义的 `*`。"""
    norm, pat = path.replace("\\", "/"), pattern.replace("\\", "/")
    if "**/" in pat:
        head, tail = pat.split("**/", 1)
        if head and not norm.startswith(head):
            return False
        rest = norm[len(head):] if head else norm
        # fnmatch 从头匹配, 而 `**/` 的意思是"任意层级" —— 所以尾巴也要允许前面带若干层
        return fnmatch.fnmatch(rest, tail) or fnmatch.fnmatch(rest, "*/" + tail)
    return fnmatch.fnmatch(norm, pat)


def match_changed(changed: list[str], pattern: str) -> list[str]:
    return sorted(p for p in changed if _glob_match(p, pattern))


def expand_run(cmd: str, ctx: dict) -> tuple[list[str], str | None]:
    """展开一条 `run`, 返回 (命令列表, 跳过原因); 展开不了抛 `ExpandError`。

    顺序固定: `<each:>` → `<changed:>` → `<skill-dir:>` / `<root>` → **残留检查**。
    最后一步是关键: 还剩下尖括号说明占位符名拼错或没被认出来 —— 那时必须停手,
    而不是把带尖括号的命令交给 shell(那会静默变成一条没人看得懂的失败命令)。
    """
    cmds = [cmd]

    for m in EACH_RE.finditer(cmd):
        files = match_changed(ctx["changed"], m.group(1))
        if not files:
            return [], f"无匹配文件: <each:{m.group(1)}>"
        limit = int(ctx.get("each_limit", 99))
        if len(files) > limit:
            raise ExpandError(
                f"<each:{m.group(1)}> 展开 {len(files)} 条, 超过 each_limit={limit} "
                f"—— 拆分提交范围, 或调高 each_limit"
            )
        cmds = [c.replace(m.group(0), _quote(f)) for f in files for c in cmds]

    for m in CHANGED_RE.finditer(cmd):
        files = match_changed(ctx["changed"], m.group(1))
        if not files:
            return [], f"无匹配文件: <changed:{m.group(1)}>"
        joined = " ".join(_quote(f) for f in files)
        cmds = [c.replace(m.group(0), joined) for c in cmds]

    resolved: list[str] = []
    for c in cmds:
        for m in SKILL_RE.finditer(c):
            name = m.group(1)
            found = find_skill_dir(name, ctx["root"])
            if found is None:
                raise ExpandError(f"找不到 skill 目录: {name}"
                                  "(已试 .agents/skills/ · .codebuddy/skills/ · 用户级)")
            c = c.replace(m.group(0), str(found))
        resolved.append(c.replace("<root>", str(ctx["root"])))

    for c in resolved:
        leftover = PLACEHOLDER_RE.search(c)
        if leftover:
            raise ExpandError(
                f"无法展开的占位符: {leftover.group(0)}"
                "(只认 <root> / <skill-dir:NAME> / <changed:GLOB> / <each:GLOB>)"
            )
    return resolved, None


# ------------------------------------------------------------------ 自动闸门执行


def summarize_gates(results: list[tuple[str, int, float, str]]) -> str:
    """全过时的一行摘要 —— **只给条数与总耗时**, 不把每条命令全文拼进来。

    原写法把 9 条展开后的命令(含绝对路径)拼成一行 ≈1.5 KB: 它每次提交都出现, 却是"过"的
    噪音 —— 要看是哪几条用 `--verbose`(明细按需, 不占常规路径的预算)。
    """
    total = sum(secs for _, _, secs, _ in results)
    return f"{len(results)} 条全过 (共 {total:.1f}s)"


def run_auto_gates(hits: list[dict],
                   ctx: dict,
                   execute: bool = True,
                   verbose: bool = False) -> tuple[list[tuple[str, str, str]], list[str], list[tuple[str, str]]]:
    """处理命中的闸门, 返回 (检查表行, 待人工命令, 失败命令的末 20 行输出)。

    - `auto = true` 且 `execute` → shell 执行, 红了进 STOP; 超时同样按失败计(不让卡死的命令挂住预检)
    - `auto = false` 或 `--no-auto` → 只把**展开后**的命令列给人(列占位符没法照着跑)
    - 展开失败 → STOP, 不降级
    - 匹配不到文件 → 记一行 WARN(可见但不挡提交)
    - `verbose` → 全过时也逐条列出命令与耗时(默认只回条数 + 总耗时)
    """
    rows: list[tuple[str, str, str]] = []
    manual: list[str] = []
    tails: list[tuple[str, str]] = []
    results: list[tuple[str, int, float, str]] = []

    for gate in hits:
        note = gate.get("note", "(无 note)")
        auto = bool(gate.get("auto", False))
        timeout = int(gate.get("timeout", 600))
        for cmd in gate.get("run", []):
            try:
                cmds, skip = expand_run(cmd, ctx)
            except ExpandError as exc:
                if auto:
                    rows.append((STOP, "自动闸门", f"展开失败(gate「{note}」): {exc}"))
                else:
                    manual.append(cmd)
                    rows.append((WARN, "人工闸门", f"展开失败, 需手工: {cmd} —— {exc}"))
                continue
            if skip:
                # 说清"跳过"是**按设计**(`<each:>` / `<changed:>` 只盯本次改动), 不是闸门失效 ——
                # 否则这条 WARN 会被读成"闸门没跑起来", 反而引着人去改一个没坏的闸门
                rows.append((WARN, "闸门", f"跳过(gate「{note}」): {skip}"
                             " —— 本次改动里没有匹配文件, 按设计跳过(**不是闸门失效**)"))
                continue
            if not auto or not execute:
                manual.extend(cmds)
                continue
            for real in cmds:
                t0 = time.monotonic()
                try:
                    proc = subprocess.run(
                        real,
                        shell=True,
                        cwd=str(ctx["root"]),
                        timeout=timeout,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace"
                    )
                    rc, out = proc.returncode, (proc.stdout or "") + (proc.stderr or "")
                except subprocess.TimeoutExpired:
                    rc, out = -1, f"超时 {timeout}s"
                results.append((real, rc, time.monotonic() - t0, out))

    failed = [r for r in results if r[1] != 0]
    if results:
        if not failed:
            rows.append((PASS, "自动闸门", summarize_gates(results)))
            if verbose:
                for cmd, _, secs, _ in results:
                    rows.append((PASS, "闸门明细", f"{secs:5.1f}s  {_short(cmd, ctx['root'])}"))
        else:
            for cmd, rc, secs, out in failed:
                rows.append((STOP, "自动闸门", f"{_short(cmd, ctx['root'])} → rc={rc} ({secs:.1f}s)"))
                lines = [l for l in out.splitlines() if l.strip()]
                tails.append((cmd, "\n".join(lines[-20:])))
            rows.append((WARN, "自动闸门", f"{len(results) - len(failed)} 条过 / {len(failed)} 条红"))
    return rows, manual, tails


def show_config(cfg: dict, src: Path) -> int:
    print(f"生效配置来源: {src}\n")
    for key in sorted(cfg):
        print(f"  {key:16} {cfg[key]}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-fetch", action="store_true", help="跳过 fetch(离线时用)")
    parser.add_argument("--no-auto", action="store_true", help="只列闸门命令、不执行(推送前的复跑用它 —— 闸门刚在提交前跑过)")
    parser.add_argument("--verbose", action="store_true", help="闸门明细逐条列出(默认只回条数 + 总耗时)")
    parser.add_argument(
        "--check-started",
        action="store_true",
        help="会话开工自检(只读): ls-remote 对比本地 HEAD + 工作区状态; 不 fetch、不写任何 git 状态, 与其余检查互斥"
    )
    parser.add_argument(
        "--phase",
        choices=("commit", "push"),
        default="push",
        help="commit 阶段: 落后主线也 STOP(先合并远端再提交, 收尾回写必须落在合并后的基线上); push 阶段: STOP"
    )
    parser.add_argument("--config", default=None, help=f"指定配置文件(默认 <仓库根>/{CONFIG_NAME})")
    parser.add_argument("--init", action="store_true", help="生成外置配置初稿(按仓库特征猜, 需人工确认)")
    parser.add_argument("--show-config", action="store_true", help="打印生效配置与来源")
    args = parser.parse_args(argv)

    if not git("rev-parse", "--is-inside-work-tree", check=False):
        print("[STOP] 当前目录不在 git 工作树里 —— 检查 cwd 与仓库根探测(find_root)")
        return 1

    if args.init:
        try:
            path = init_config(find_root())
        except FileExistsError as exc:
            print(f"[STOP] {exc}")
            return 1
        print(f"已生成初稿: {path}\n请打开逐项确认/修改, 特别是 red_lines 与 [[gates]]。\n"
              f"确认后再跑: preflight.py --show-config")
        return 0

    try:
        cfg, src = load_config(explicit=args.config)
    except ConfigMissing as exc:
        print(exc)
        return 1

    if args.show_config:
        return show_config(cfg, src)

    BRANCH = resolve_branch(cfg)
    MAIN, MAIN_URL = resolve_main_remote(cfg)
    MIRROR, _ = resolve_mirror_remote(cfg)
    RED_LINES, WARN_LINES = cfg["red_lines"], cfg["warn_lines"]
    STAGED_PANIC, HINTS = cfg["staged_panic"], cfg["platform_hints"]
    CANDIDATES, MAIN_MARK = cfg["main_candidates"], cfg["main_host_mark"]
    ROOT = find_root()

    rows: list[tuple[str, str, str]] = []  # (级别, 项, 说明)
    # 全新仓库(还没任何提交)时 `rev-parse HEAD` 会失败 —— 按空处理, 不当致命错误
    branch = git("rev-parse", "--abbrev-ref", "HEAD", check=False) or "(无提交)"
    staged, unstaged = changed_files()
    changed = staged + unstaged

    # ---- 开工自检(--check-started): **只读** —— 连 fetch 都不做, 不写任何 ref/对象 ----
    # 目的: 把「开工先同步」从注意力约束变成可执行机检 —— 结果贴进会话回复, 跳过会留可见空洞。
    # 判据: ls-remote 现查远端真值, 不读 refs/remotes(部分工具 shell 里它的写入会被静默丢弃)。
    if args.check_started:
        head_sha = git("rev-parse", "HEAD", check=False)
        remote_sha = ""
        if MAIN_URL:
            ls_out = git("ls-remote", MAIN, BRANCH, check=False)
            for line in ls_out.splitlines():
                parts = line.split()
                if len(parts) == 2 and parts[1] == f"refs/heads/{BRANCH}":
                    remote_sha = parts[0]
                    break
        counts = None
        if remote_sha and head_sha and remote_sha != head_sha:
            try:
                raw = git("rev-list", "--left-right", "--count", f"{remote_sha}...HEAD")
                nums = raw.split()
                counts = (int(nums[0]), int(nums[1]))
            except (RuntimeError, ValueError, IndexError):
                counts = None
        level, msg = classify_sync(remote_sha, head_sha, counts)
        mine = staged + unstaged
        dirty = len(mine)
        # 合流预判 / 重叠判定都只在**落后**且**本地已有远端 tip 对象**时做 —— 它们都是只读的;
        # 没有对象就省略, 不为了凑几行去 fetch(开工自检承诺"不 fetch、不写任何 git 状态")。
        has_obj = bool(counts and counts[0] > 0 and git_rc("cat-file", "-e", f"{remote_sha}^{{commit}}") == 0)
        probe = (
            [classify_merge_probe(git_rc("merge-tree", "--write-tree", "HEAD", remote_sha), "commit")]
            if has_obj else []
        )
        overlap: list[str] = []
        if has_obj and dirty:
            remote_files = set(git("diff", "--name-only", "HEAD", remote_sha, check=False).splitlines())
            overlap = sorted(set(mine) & remote_files)
        recipe = sync_recipe(*counts, dirty, overlap, f"git fetch {MAIN} {BRANCH}") if counts else None
        dirty_note = ""
        if dirty:
            # 指针只在真有「同步路径」那行时给 —— 齐平时指向一行不存在的行, 比不说更坏
            dirty_note = " —— 树脏: 见上面的「同步路径」" if recipe else " —— 树脏(与主线齐平, 不影响开工)"
        rows_cs = [
            (level, "同步状态", msg),
            *probe,
            *([recipe] if recipe else []),
            (WARN if dirty else PASS, "工作区", f"未暂存 {len(unstaged)} / 已暂存 {len(staged)}{dirty_note}"),
        ]
        width = max(len(r[1]) for r in rows_cs)
        print("\n开工自检(--check-started, 全程只读):\n")
        for lv, item, detail in rows_cs:
            print(f"  [{lv:4}] {item.ljust(width)}  {detail}")
        print(f"\n远端基准: {MAIN or '(无主线远端)'}/{BRANCH} @ {remote_sha[:8] or '(拿不到)'}; 退出码 0=可开工, 1=需先处理")
        return 0 if level == PASS else 1

    # 占位符只喂**磁盘上还在**的文件: D(已删除)状态的文件被 git 记着但已不在盘上,
    # 交给 yapf 之类的命令会直接失败。
    present = [p for p in changed if (ROOT / p).exists()]
    ctx = {"root": ROOT, "changed": present, "each_limit": cfg.get("each_limit", 99)}

    # 1 配置(含分级体检: 未知键 / timeout 非法 → STOP; 初稿未确认等 → WARN)
    rows.append((PASS, "外置配置", str(src)))
    for level, issue in config_problems(cfg, src):
        rows.append((level, "配置体检", issue))

    # 2 分支
    rows.append((PASS if branch == BRANCH else WARN, "分支", f"当前 {branch}(探测/配置为 {BRANCH})"))

    # 3 主线远端
    if not MAIN:
        rows.append((STOP, "主线远端", f"候选 {list(CANDIDATES)} 里没有可用远端; 先 `git remote -v` 确认主线挂在哪个名字上"))
    elif not main_matches_mark(cfg, MAIN_URL):
        rows.append(
            (
                WARN, "主线远端", f"{MAIN} = {MAIN_URL} 不含特征 {MAIN_MARK} —— 按候选顺序**回退**选了它; "
                "若这就是主线可忽略, 否则改配置里的 main_host_mark / main_candidates"
            )
        )
    else:
        rows.append((PASS, "主线远端", f"{MAIN} = {MAIN_URL}"))

    # 4 上游
    try:
        upstream = git("rev-parse", "--abbrev-ref", "@{u}")
    except RuntimeError:
        upstream = ""
    want_up = f"{MAIN}/{BRANCH}"
    rows.append(
        (PASS if upstream == want_up else WARN, "上游", f"{upstream or '(未设置)'}(期望 {want_up}; 判 ahead/behind 看的是当前上游)")
    )

    # 5 落后 / 领先 —— 判据 = 远端真值(ls-remote)对比本地 HEAD; **绝不读 refs/remotes**
    # (部分工具 shell 里 refs/remotes/* 的写入会被静默丢弃, 跟踪 ref 是陈年快照, 给过假"落后 5";
    # `status -sb` 的 ahead/behind 同理)。拿不到远端真值就如实说"无法验证", 不拿快照凑数。
    remote_sha = ""
    if MAIN_URL and not args.no_fetch:
        ls_out = git("ls-remote", MAIN, BRANCH, check=False)
        for line in ls_out.splitlines():
            parts = line.split()
            if len(parts) == 2 and parts[1] == f"refs/heads/{BRANCH}":
                remote_sha = parts[0]
                break
        if remote_sha:
            git("fetch", MAIN, BRANCH, check=False)
    behind, ahead = -1, -1
    if remote_sha:
        try:
            behind, ahead = (int(x) for x in git("rev-list", "--left-right", "--count", f"{remote_sha}...HEAD").split())
        except (RuntimeError, ValueError):
            pass  # 本地没有远端 tip 的对象(fetch 失败?) —— 保持 -1, 下面如实报"没能算出"
    if behind > 0:
        # 同步路径配方与 --check-started 同一份: 树干净直接快进 / 树脏走「移出→快进→施回」/
        # 与远端改动重叠或已分叉则停下报告 —— commit 阶段也要给: 新流程要求先合并远端再收尾回写。
        overlap: list[str] = []
        if changed:
            remote_files = set(git("diff", "--name-only", "HEAD", remote_sha, check=False).splitlines())
            overlap = sorted(set(changed) & remote_files)
        rows.extend(behind_rows(behind, ahead, args.phase, len(changed), overlap, f"git fetch {MAIN} {BRANCH}"))
        # 合流预判(只读): 把「撞不撞」提前到提交前 —— 本环境非快进合并 + 脏工作区 = 必炸,
        # 提前知道才好决定"先留备份 / 先弄干净工作区"。merge-tree 只在对象库里算合并树, 不写工作区/ref/index。
        # 对象不在库里(如 fetch 失败)时按"无法预判"处理 —— merge-tree 非 0 还有"对象缺失"这种失败模式,
        # 不加对象守卫会把"拉不到对象"误报成"会撞"的 STOP。
        has_remote_obj = remote_sha and git_rc("cat-file", "-e", f"{remote_sha}^{{commit}}") == 0
        rows.append(
            classify_merge_probe(
                git_rc("merge-tree", "--write-tree", "HEAD", remote_sha) if has_remote_obj else None, args.phase
            )
        )
    elif behind == 0:
        rows.append((PASS, "落后主线", f"与主线齐平(本地领先 {ahead})"))
    else:
        rows.append(
            (
                WARN,
                "落后主线",
                f"拿不到远端真值(离线 / --no-fetch / ls-remote 失败), 无法算领先/落后 —— 联网后重跑, "
                f"或手工对比 `git ls-remote {MAIN} {BRANCH}` 与本地 HEAD(别看 refs/remotes 快照)",
            )
        )

    # 6 工作区
    rows.append(
        (
            WARN if unstaged else PASS, "工作区",
            f"未暂存 {len(unstaged)} 个 / 已暂存 {len(staged)} 个" + (" —— **脏工作区不做非快进合并**(先弄干净工作区)" if unstaged else "")
        )
    )

    # 7 staged 异常(分支 ref 被回退的信号)
    if len(staged) > STAGED_PANIC:
        rows.append(
            (
                STOP, "staged 数量", f"{len(staged)} 个 staged —— 高度怀疑分支 ref 被别的会话回退;"
                " **不要 `git add -A` 去解决**, 走 format-patch 留底 + update-ref"
            )
        )

    # 8 红线 / 高危文件
    red = hit(changed, RED_LINES)
    if red:
        rows.append((STOP, "红线文件", "、".join(red) + " 不得进暂存清单"))
    warn = hit(changed, WARN_LINES)
    if warn:
        rows.append((WARN, "高危文件", "、".join(warn) + " —— 确认是不是用户自己的在途改动"))

    # 9 闸门 —— auto = true 的直接跑(先展开、再执行), 其余列出来给人跑;
    # 落后未合流时**不跑**: 合并远端后反正要重跑提交预检, 现在跑全量测试纯属白跑。
    hits = gates_for(changed, cfg["gates"])
    gate_rows: list[tuple[str, str, str]] = []
    manual: list[str] = []
    tails: list[tuple[str, str]] = []
    if behind > 0:
        rows.append((WARN, "提交前闸门", f"命中 {len(hits)} 条闸门但落后未合流, 先不跑 —— 按「同步路径」合并远端后重跑"))
    else:
        gate_rows, manual, tails = run_auto_gates(hits, ctx, execute=not args.no_auto, verbose=args.verbose)
        rows.extend(gate_rows)
        if not hits:
            rows.append((PASS, "提交前闸门", "未命中配置里的闸门(仍按改动面自行判断)"))
        elif args.no_auto:
            rows.append((WARN, "提交前闸门", f"命中 {len(hits)} 条闸门, --no-auto 只列不跑"))

    # 10 平台差异
    if any(h in " ".join(changed) for h in HINTS):
        rows.append((WARN, "平台差异", "改动命中平台相关关键词 —— 单平台跑绿不算数, 建议换平台复现"))

    # 11 镜像远端
    if not MIRROR:
        rows.append((WARN, "镜像远端", "没找到镜像远端; 镜像允许滞后, 可不管"))

    width = max(len(r[1]) for r in rows)
    print("\n预检结果(PASS / WARN / STOP):\n")
    for level, item, detail in rows:
        print(f"  [{level:4}] {item.ljust(width)}  {detail}")

    if cfg.get("pitfalls_index"):
        print(f"\n决策点指针(改代码 / 跑 git 前先读): {cfg['pitfalls_index']}")

    if manual:
        print("\n该跑的闸门命令(已展开占位符):")
        for cmd in manual:
            print(f"  - {cmd}")

    if tails:
        print("\n失败输出(末 20 行):")
        for cmd, out in tails:
            print(f"\n  $ {cmd}")
            for line in out.splitlines():
                print(f"    {line}")

    stops = [r for r in rows if r[0] == STOP]
    if stops:
        print(f"\n{len(stops)} 项 STOP —— 处理完再提交。")
        return 1
    warns = [r for r in rows if r[0] == WARN]
    print(f"\n无 STOP{'；%d 项 WARN 需人工确认' % len(warns) if warns else ''} —— 可以继续。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
