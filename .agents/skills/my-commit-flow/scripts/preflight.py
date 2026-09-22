"""提交前预检 —— 不改任何 git 状态, 但**会执行 `auto = true` 的闸门**(可能改工作区)。

用法(**不要写死 skill 的安装路径**, `<skill-dir>` = 加载本 skill 时它实际所在的目录):
    python <skill-dir>/scripts/preflight.py [--no-fetch] [--no-auto]
    python <skill-dir>/scripts/preflight.py --init           # 生成外置配置初稿(需人工确认)
    python <skill-dir>/scripts/preflight.py --show-config     # 打印生效配置与来源

⚠ **不再是"只读"**: `auto = true` 的闸门会被真的执行(测试 / 格式化 / 索引 --check / skill 同步),
可能改写工作区文件。只想看检查表时用 `--no-auto`。

闸门命令里的占位符由本脚本展开(展开不了即 STOP, 不降级成"打印给人"):
    <root>              仓库根绝对路径
    <skill-dir:NAME>    skill 目录(项目级 → 用户级, 找不到即 STOP)
    <changed:GLOB>      本次改动里匹配的文件 → 拼成一条命令
    <each:GLOB>         按匹配文件把这条 run 复制成多条命令(条数上限 each_limit)

**先有配置才预检**: 项目特有项(红线 / 闸门 …)一律来自 `<仓库根>/.commit-flow.toml`;
没有配置文件 → 打印引导并停手, 不猜默认值。

输出一张检查表(PASS / WARN / STOP):
- 远端与上游是不是主线(按配置探测)、分支对不对
- 落不落后主线(**push 前也要再跑一次**: `status -sb` 的 ahead/behind 是上次 fetch 的快照)
- 工作区脏不脏(脏 + 需要 rebase = 红线区)
- 改动清单里有没有红线 / 高危文件
- 闸门: `auto = true` 的直接跑(红了即 STOP), 其余列出来给人跑
- 是否需要换平台复现

有 STOP → 退出码 1; 只有 WARN → 0(需人工确认后继续)。
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
import sys
import time
from pathlib import Path

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


def remotes() -> dict[str, str]:
    out: dict[str, str] = {}
    for line in git("remote", "-v").splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[2] == "(push)":
            out[parts[0]] = parts[1]
    return out


def changed_files() -> tuple[list[str], list[str]]:
    """返回 (staged, unstaged) 文件清单(按 `git status --porcelain` 的两列判读)。"""
    staged, unstaged = [], []
    for line in git("status", "--porcelain").splitlines():
        if not line.strip():
            continue
        xy = line[:2].ljust(2)  # 短行兜底, 避免索引错位后再切错路径
        path = line[3:].strip() if len(line) > 3 else ""
        if not path:
            continue
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


def run_auto_gates(hits: list[dict],
                   ctx: dict,
                   execute: bool = True) -> tuple[list[tuple[str, str, str]], list[str], list[tuple[str, str]]]:
    """处理命中的闸门, 返回 (检查表行, 待人工命令, 失败命令的末 20 行输出)。

    - `auto = true` 且 `execute` → shell 执行, 红了进 STOP; 超时同样按失败计(不让卡死的命令挂住预检)
    - `auto = false` 或 `--no-auto` → 只把**展开后**的命令列给人(列占位符没法照着跑)
    - 展开失败 → STOP, 不降级
    - 匹配不到文件 → 记一行 WARN(可见但不挡提交)
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
                rows.append((WARN, "闸门", f"跳过(gate「{note}」): {skip}"))
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
            summary = " · ".join(f"{cmd} {secs:.1f}s" for cmd, _, secs, _ in results)
            rows.append((PASS, "自动闸门", f"{len(results)} 条全过 ({summary})"))
        else:
            for cmd, rc, secs, out in failed:
                rows.append((STOP, "自动闸门", f"{cmd} → rc={rc} ({secs:.1f}s)"))
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
    parser.add_argument(
        "--phase",
        choices=("commit", "push"),
        default="push",
        help="commit 阶段: 落后主线只 WARN(本地提交可以, 推送前必须 rebase); push 阶段: STOP"
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

    # 5 落后 / 领先
    if not args.no_fetch and MAIN_URL:
        git("fetch", MAIN, BRANCH, check=False)
    try:
        counts = git("rev-list", "--left-right", "--count", f"{MAIN}/{BRANCH}...HEAD")
        behind, ahead = (int(x) for x in counts.split())
    except (RuntimeError, ValueError):
        behind, ahead = -1, -1
    if behind > 0:
        if args.phase == "commit":
            rows.append((WARN, "落后主线", f"落后 {behind} 个提交 —— 本地提交可以, 但**推送前必须先 rebase**(工作区要干净)"))
        else:
            rows.append((STOP, "落后主线", f"落后 {behind} 个提交 —— 先 rebase(**工作区必须干净**); 别等 push 被拒才发现"))
    elif behind == 0:
        rows.append((PASS, "落后主线", f"与主线齐平(本地领先 {ahead})"))
    else:
        rows.append((WARN, "落后主线", f"没能算出领先/落后, 手工 `git log --oneline HEAD..{MAIN}/{BRANCH}`"))

    # 6 工作区
    rows.append(
        (
            WARN if unstaged else PASS, "工作区",
            f"未暂存 {len(unstaged)} 个 / 已暂存 {len(staged)} 个" + (" —— **脏工作区不做非快进合并 / rebase**(红线)" if unstaged else "")
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

    # 9 闸门 —— auto = true 的直接跑(先展开、再执行), 其余列出来给人跑
    hits = gates_for(changed, cfg["gates"])
    gate_rows, manual, tails = run_auto_gates(hits, ctx, execute=not args.no_auto)
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
