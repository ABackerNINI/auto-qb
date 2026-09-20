"""提交前预检 —— **只读**(外加一次安全的 fetch), 不改任何 git 状态。

用法(**不要写死 skill 的安装路径**, `<skill-dir>` = 加载本 skill 时它实际所在的目录):
    python <skill-dir>/scripts/preflight.py [--no-fetch]
    python <skill-dir>/scripts/preflight.py --init           # 生成外置配置初稿(需人工确认)
    python <skill-dir>/scripts/preflight.py --show-config     # 打印生效配置与来源

**先有配置才预检**: 项目特有项(红线 / 闸门 …)一律来自 `<仓库根>/.commit-flow.toml`;
没有配置文件 → 打印引导并停手, 不猜默认值。

输出一张检查表(PASS / WARN / STOP):
- 远端与上游是不是主线(按配置探测)、分支对不对
- 落不落后主线(**push 前也要再跑一次**: `status -sb` 的 ahead/behind 是上次 fetch 的快照)
- 工作区脏不脏(脏 + 需要 rebase = 红线区)
- 改动清单里有没有红线 / 高危文件
- 提交前该跑哪些闸门命令
- 是否需要换平台复现

有 STOP → 退出码 1; 只有 WARN → 0(需人工确认后继续)。
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _ship_config import (  # noqa: E402
    CONFIG_NAME,
    ConfigMissing,
    find_root,
    init_config,
    load_config,
    main_matches_mark,
    resolve_branch,
    resolve_main_remote,
    resolve_mirror_remote,
)

PASS, WARN, STOP = "PASS", "WARN", "STOP"


def git(*args: str, check: bool = True) -> str:
    proc = subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} 失败: {proc.stderr.strip()}")
    return proc.stdout.strip()


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
        xy, path = line[:2], line[3:].strip()
        if xy[0] not in (" ", "?"):
            staged.append(path)
        if xy[1] != " ":
            unstaged.append(path)
    return staged, unstaged


def hit(files: list[str], patterns) -> list[str]:
    return [f for f in files if any(f.startswith(p) or p in f for p in patterns)]


def gates_for(files: list[str], gates: list[dict]) -> list[tuple[str, list[str]]]:
    found = []
    for gate in gates:
        if hit(files, gate.get("match", [])):
            found.append((gate.get("note", "闸门"), list(gate.get("run", []))))
    return found


def show_config(cfg: dict, src: Path) -> int:
    print(f"生效配置来源: {src}\n")
    for key in sorted(cfg):
        print(f"  {key:16} {cfg[key]}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-fetch", action="store_true", help="跳过 fetch(离线时用)")
    parser.add_argument("--phase", choices=("commit", "push"), default="push",
                        help="commit 阶段: 落后主线只 WARN(本地提交可以, 推送前必须 rebase); push 阶段: STOP")
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

    rows: list[tuple[str, str, str]] = []  # (级别, 项, 说明)
    # 全新仓库(还没任何提交)时 `rev-parse HEAD` 会失败 —— 按空处理, 不当致命错误
    branch = git("rev-parse", "--abbrev-ref", "HEAD", check=False) or "(无提交)"
    staged, unstaged = changed_files()
    changed = staged + unstaged

    # 1 配置
    rows.append((PASS, "外置配置", str(src)))

    # 2 分支
    rows.append((PASS if branch == BRANCH else WARN, "分支", f"当前 {branch}(探测/配置为 {BRANCH})"))

    # 3 主线远端
    if not MAIN:
        rows.append((STOP, "主线远端", f"候选 {list(CANDIDATES)} 里没有可用远端; 先 `git remote -v` 确认主线挂在哪个名字上"))
    elif not main_matches_mark(cfg, MAIN_URL):
        rows.append((WARN, "主线远端",
                     f"{MAIN} = {MAIN_URL} 不含特征 {MAIN_MARK} —— 按候选顺序**回退**选了它; "
                     "若这就是主线可忽略, 否则改配置里的 main_host_mark / main_candidates"))
    else:
        rows.append((PASS, "主线远端", f"{MAIN} = {MAIN_URL}"))

    # 4 上游
    try:
        upstream = git("rev-parse", "--abbrev-ref", "@{u}")
    except RuntimeError:
        upstream = ""
    want_up = f"{MAIN}/{BRANCH}"
    rows.append((PASS if upstream == want_up else WARN, "上游",
                 f"{upstream or '(未设置)'}(期望 {want_up}; 判 ahead/behind 看的是当前上游)"))

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
            rows.append((WARN, "落后主线",
                         f"落后 {behind} 个提交 —— 本地提交可以, 但**推送前必须先 rebase**(工作区要干净)"))
        else:
            rows.append((STOP, "落后主线",
                         f"落后 {behind} 个提交 —— 先 rebase(**工作区必须干净**); 别等 push 被拒才发现"))
    elif behind == 0:
        rows.append((PASS, "落后主线", f"与主线齐平(本地领先 {ahead})"))
    else:
        rows.append((WARN, "落后主线", f"没能算出领先/落后, 手工 `git log --oneline HEAD..{MAIN}/{BRANCH}`"))

    # 6 工作区
    rows.append((WARN if unstaged else PASS, "工作区",
                 f"未暂存 {len(unstaged)} 个 / 已暂存 {len(staged)} 个" +
                 (" —— **脏工作区不做非快进合并 / rebase**(红线)" if unstaged else "")))

    # 7 staged 异常(分支 ref 被回退的信号)
    if len(staged) > STAGED_PANIC:
        rows.append((STOP, "staged 数量", f"{len(staged)} 个 staged —— 高度怀疑分支 ref 被别的会话回退;"
                     " **不要 `git add -A` 去解决**, 走 format-patch 留底 + update-ref"))

    # 8 红线 / 高危文件
    red = hit(changed, RED_LINES)
    if red:
        rows.append((STOP, "红线文件", "、".join(red) + " 不得进暂存清单"))
    warn = hit(changed, WARN_LINES)
    if warn:
        rows.append((WARN, "高危文件", "、".join(warn) + " —— 确认是不是用户自己的在途改动"))

    # 9 闸门
    gates = gates_for(changed, cfg["gates"])
    if gates:
        rows.append((WARN, "提交前闸门", "; ".join(note for note, _ in gates)))
    else:
        rows.append((PASS, "提交前闸门", "未命中配置里的闸门(仍按改动面自行判断)"))

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

    if gates:
        print("\n该跑的闸门命令:")
        for _, cmds in gates:
            for cmd in cmds:
                print(f"  - {cmd}")

    stops = [r for r in rows if r[0] == STOP]
    if stops:
        print(f"\n{len(stops)} 项 STOP —— 处理完再提交。")
        return 1
    warns = [r for r in rows if r[0] == WARN]
    print(f"\n无 STOP{'；%d 项 WARN 需人工确认' % len(warns) if warns else ''} —— 可以继续。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
