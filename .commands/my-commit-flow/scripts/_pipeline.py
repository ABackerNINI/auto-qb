"""提交流水线的**内部共享件** —— 闸门引擎 / 占位符展开 / 改动清单 / 配置体检。

v3 输出契约(计划 26-09-28-0157)「沉默即成功」: 本模块只提供机制, **不打印检查表** ——
常规路径成功即静默, 失败由调用方(sync / commit / push)给一行「原因 + 下一步」。
人工排障口: `_pipeline.py --show-config` 看生效配置, `--init` 生成新仓库的配置初稿。

前身是 preflight.py(检查表式预检, v2 计划 26-09-26-2345); v3 把"检查"下沉进 ship 编排,
把"报告"压缩成一行, 检查项本身一个不删(保全清单见计划 §04)。
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
import sys
import time
from pathlib import Path

# Windows GBK 控制台兑底: git 输出含 emoji(gitmoji 首行)时 GBK 编不出来会让 print 直接
# UnicodeEncodeError —— 明明已成功, 却崩在打印、退出码非 0, 执行者会被骗去重跑
# (实测 2026-09-22)。强制 stdout/stderr 走 UTF-8, 编不出时降级 replace 显示。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _ship_config import CONFIG_NAME, ConfigMissing, config_problems, find_root, find_skill_dir, init_config, load_config  # noqa: E402


def git(*args: str, check: bool = True) -> str:
    # **不能整段 strip()**: `git status --porcelain` 的首列空格表示"无暂存改动",
    # 整段 strip 会把首行的这个空格吃掉 → ' M a/b' 变成 'M  a/b', 首列被误判成已暂存,
    # 且 line[3:] 丢掉路径首字符, 红线匹配会**静默放行**。
    proc = subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} 失败: {proc.stderr.strip()}")
    return proc.stdout.rstrip("\n")


def git_rc(*args: str) -> int:
    """只关心**退出码**的 git 调用(如 `merge-tree --write-tree`: 0 = 可干净合流, 非 0 = 有冲突)。"""
    return subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace").returncode


def git_run(*args: str) -> subprocess.CompletedProcess:
    """要 rc + stderr 的 git 调用(merge --ff-only / rebase / push 的失败原因都在 stderr)。"""
    return subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")


def changed_files() -> tuple[list[str], list[str]]:
    """返回 (staged, unstaged) 文件清单(按 `git status --porcelain` 的两列判读)。

    ❗必须带 `-uall`: 默认模式下**未跟踪目录只报一条 `?? <dir>/`**, 于是 `<each:GLOB>` 之类
    按文件的展开**匹配不到新加的文件** —— 新增脚本拿不到 `--help` 冒烟, 且是静默的。
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
    """命中的闸门 —— 返回完整 dict(auto / timeout 在里头, 后面要靠它们决定"跑不跑")。"""
    return [g for g in gates if hit(files, g.get("match", []))]


# ------------------------------------------------------------------ 占位符展开

PLACEHOLDER_RE = re.compile(r"<[^<>]+>")
EACH_RE = re.compile(r"<each:([^<>]+)>")
CHANGED_RE = re.compile(r"<changed:([^<>]+)>")
SKILL_RE = re.compile(r"<skill-dir:([^<>]+)>")


class ExpandError(RuntimeError):
    """占位符展开失败 —— 调用方必须转成失败, **不降级**成"打印给人"。"""


def _quote(path: str) -> str:
    return path if not re.search(r"\s", path) else f'"{path}"'


def _short(cmd: str, root) -> str:
    """命令里的仓库根绝对路径换成 `.` —— 失败明细里那段前缀是常量, 每次重复纯属占地方。

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


# ------------------------------------------------------------------ 闸门执行(沉默即成功)


def run_gates(hits: list[dict], ctx: dict) -> tuple[list[tuple[str, str, int, float, str]], list[str], int]:
    """执行命中的 `auto = true` 闸门 —— **全过即静默**(v3 契约), 失败才说话。

    返回 (failures, manual, ran):
    - failures: [(gate note, 命令, rc, 耗时s, 失败输出末 20 行)] —— 调用方转成失败行;
      展开失败 rc 记 -2(不是 git 的码, 避免与真实 rc 混淆), 超时记 -1。
    - manual: 非自动闸门的展开命令(不执行; 调用方决定要不要提示 —— 本仓库配置里没有这类)。
    - ran: 真正执行过的命令条数。
    - `<each:>` / `<changed:>` 无匹配文件 → **按设计静默跳过**(它们只盯本次改动)。
    """
    failures: list[tuple[str, str, int, float, str]] = []
    manual: list[str] = []
    ran = 0
    for gate in hits:
        note = gate.get("note", "(无 note)")
        timeout = int(gate.get("timeout", 600))
        for cmd in gate.get("run", []):
            try:
                cmds, skip = expand_run(cmd, ctx)
            except ExpandError as exc:
                failures.append((note, cmd, -2, 0.0, str(exc)))
                continue
            if skip:
                continue
            if not gate.get("auto", False):
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
                secs = time.monotonic() - t0
                ran += 1
                if rc != 0:
                    lines = [l for l in out.splitlines() if l.strip()]
                    failures.append((note, real, rc, secs, "\n".join(lines[-20:])))
    return failures, manual, ran


def staged_overflow(staged: list[str], limit: int) -> str | None:
    """staged 数量暴增 = 分支 ref 被别的会话回退的信号 —— 给一行人话, 拒绝继续。"""
    if len(staged) > limit:
        return (
            f"staged {len(staged)} 个(阈值 {limit}) —— 分支 ref 可能被别的会话回退; "
            "**不要用 add -A 去「解决」**, 处置步骤: commands run my-commit-flow.verify-ref"
        )
    return None


def config_stops(cfg: dict, src: Path) -> list[str]:
    """配置体检只取 STOP 级(未知键 / timeout 非法) —— 有它闸门可能静默失效, 必须停。

    WARN 级(初稿未确认等)不进常规路径: v3 沉默契约下, 它们只在排障(--show-config)时看。
    """
    return [msg for lvl, msg in config_problems(cfg, src) if lvl == "STOP"]


# ------------------------------------------------------------------ 人工排障口


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=None, help=f"指定配置文件(默认 <包>/{CONFIG_NAME})")
    parser.add_argument("--init", action="store_true", help="生成外置配置初稿(按仓库特征猜, 需人工确认)")
    parser.add_argument("--show-config", action="store_true", help="打印生效配置与来源")
    args = parser.parse_args(argv)

    if args.init:
        try:
            path = init_config(find_root())
        except FileExistsError as exc:
            print(f"[STOP] {exc}")
            return 1
        print(f"已生成初稿: {path}\n请打开逐项确认/修改, 特别是 red_lines 与 [[gates]]。\n"
              f"确认后再跑: _pipeline.py --show-config")
        return 0

    try:
        cfg, src = load_config(explicit=args.config)
    except ConfigMissing as exc:
        print(exc)
        return 1
    if args.show_config:
        print(f"生效配置来源: {src}\n")
        for key in sorted(cfg):
            print(f"  {key:16} {cfg[key]}")
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
