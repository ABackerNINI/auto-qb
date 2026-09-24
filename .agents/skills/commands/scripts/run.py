"""入口: run / list / show / add —— 项目命令的统一调用面。

引擎不认识任何具体动作, 一切命令都来自 `.commands/` 下的包。
执行者只需要回答"现在该调哪个", 命令怎么拼不归它管。

退出码: 0 成功 · 1 STOP(配置写错 / 占位符展不开 / 前置不满足) · 3 命令本身非 0
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # 允许 `python scripts/run.py` 直接跑

import _config as C  # noqa: E402
import _tree as T  # noqa: E402

STOP = 1
FAILED = 3
SUMMARY_LINES = 3  # 成功时只回最后几行 —— 常规路径不该把整段输出搬进上下文

# ------------------------------------------------------------------ 子命令


def cmd_run(args: argparse.Namespace) -> int:
    tree = C.load_tree()
    task = _pick(tree, args.task)
    extra = _extra(args)
    cmds = C.task_commands(task, tree.root, extra)

    # 详略随风险自适应: 带前置检查或标了高风险的, 先自证"将要跑什么"再跑
    if task.requires or task.risky:
        print(f"[自证] {task.id} 将要执行:")
        for cmd in cmds:
            print(f"  {cmd}")

    for check in task.requires:
        ok, out = _shell(C.expand(check, tree.root, extra), task.timeout)
        if not ok:
            print(f"[STOP] 前置不满足: {check}")
            if out.strip():
                print(out.rstrip())
            return STOP
        print(f"[前置] ok: {check}")

    for cmd in cmds:
        started = time.time()
        ok, out = _shell(cmd, task.timeout, env=C.pack_env(task))
        spent = time.time() - started
        if not ok:
            print(f"[FAIL] {task.id} rc!=0 ({spent:.1f}s)")
            print(out.rstrip())
            return FAILED
        print(f"[ok] {task.id} ({spent:.1f}s)")
        for line in _tail(out):
            print(f"  {line}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    tree = C.load_tree()
    print(T.render(tree, args.path, show_all=args.all))
    if tree.warnings:
        print("")
        for warn in tree.warnings:
            print(f"[WARN] {warn}")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    tree = C.load_tree()
    task = _pick(tree, args.task)
    extra = _extra(args)
    print(f"{task.id}  ({task.pack_path})")
    if task.when:
        print(f"  何时用: {task.when}")
    if task.note:
        print(f"  注意:   {task.note}")
    if task.doc:
        # "想看细节该读哪份"必须接到决策点上 —— 否则唯一的出路是回头整读包内 README
        print(f"  深读:   {task.doc_path or task.doc}")
    print(f"  超时:   {task.timeout}s")
    # strict: 展不开就 STOP —— show 若把未展开的原文打印出来, 等于"看起来拿到了命令"
    for cmd in C.task_commands(task, tree.root, extra):
        print(f"  $ {cmd}")
    return 0


def cmd_add(args: argparse.Namespace) -> int:
    tree = C.load_tree()
    if not (args.run or args.script):
        print("[STOP] --run 与 --script 至少给一个")
        return STOP
    if args.run and args.script:
        print("[STOP] --run 与 --script 只能二选一")
        return STOP
    if not args.when.strip():
        # "何时用"是下次能被发现的唯一线索 —— 说不出场景就说明这条还不该被收
        print("[STOP] --when 不能为空: 缺了它, 这条命令在 list 里只剩一个 id, 等于没收录")
        return STOP
    pack = T.resolve(tree, args.pack)
    if pack is None:
        print(f"[STOP] 没有这个包: {args.pack}(命令只能落进已有的包; 用 list 看有哪些包)")
        return STOP
    if args.id in tree.tasks:
        print(f"[STOP] task id 已存在: {args.id}(改既有命令请直接编辑 {pack.dir / 'config.toml'})")
        return STOP

    block = _toml_block(args)
    target = pack.dir / "config.toml"
    print(f"落点: {target}")
    print("─" * 78)
    print(block)
    if not args.write:
        print("(dry-run: 未写入 —— 核对无误后加 --write)")
        return 0
    with target.open("a", encoding="utf-8") as fh:
        fh.write("\n" + block)
    print(f"已写入。自证: show {args.id}")
    return cmd_show(argparse.Namespace(task=args.id, extra=[]))


# ------------------------------------------------------------------ 工具


def _pick(tree: C.Tree, name: str) -> C.Task:
    task = tree.tasks.get(name)
    if task is None:
        near = [t for t in tree.tasks if name in t or t.startswith(name.split(".")[0])]
        hint = f"  相近: {', '.join(sorted(near)[:8])}" if near else "  用 list 逐级找"
        raise SystemExit(f"[STOP] 没有这个 task: {name}\n{hint}")
    return task


def _extra(args: argparse.Namespace) -> str:
    extra = list(getattr(args, "extra", None) or [])
    if extra and extra[0] == "--":
        extra = extra[1:]
    return " ".join(extra)


def _shell(cmd: str, timeout: int, env: dict[str, str] | None = None) -> tuple[bool, str]:
    full = {**os.environ, **(env or {})}
    proc = subprocess.run(
        cmd,
        shell=True,
        cwd=str(C.find_root()),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        env=full,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode == 0, out


def _tail(out: str) -> list[str]:
    lines = [ln.rstrip() for ln in out.splitlines() if ln.strip()]
    return lines[-SUMMARY_LINES:]


def _toml_block(args: argparse.Namespace) -> str:
    def val(text: str) -> str:
        return json.dumps(text, ensure_ascii=False)

    out = [f'[tasks."{args.id}"]']
    if args.run:
        out.append(f"run     = [{val(args.run)}]")
    else:
        out.append(f"script  = {val(args.script)}")
        if args.args:
            out.append("args    = [" + ", ".join(val(a) for a in args.args) + "]")
    out.append(f"when    = {val(args.when)}")
    if args.note:
        out.append(f"note    = {val(args.note)}")
    if args.doc:
        out.append(f"doc     = {val(args.doc)}")
    if args.timeout:
        out.append(f"timeout = {args.timeout}")
    if args.pin:
        out.append("pin     = true")
    if args.risky:
        out.append("risky   = true")
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------ 入口


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="run.py",
        description="项目命令的统一调用面 —— 只认 task id, 命令本体在包里单点定义。",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="校验前置后执行(常规路径只用它)")
    p_run.add_argument("task")
    p_run.add_argument("extra", nargs=argparse.REMAINDER, help="填进 <args> 占位符")

    p_list = sub.add_parser("list", help="逐级列出当前层级")
    p_list.add_argument("path", nargs="?", default=None, help="子包路径, 如 <父包>/<子包>")
    p_list.add_argument("--all", action="store_true", help="全量(排障兜底, 不是入口)")

    p_show = sub.add_parser("show", help="打印展开后的真实命令, 不执行")
    p_show.add_argument("task")
    p_show.add_argument("extra", nargs=argparse.REMAINDER)

    p_add = sub.add_parser("add", help="收录一条命令进包(默认 dry-run)")
    p_add.add_argument("--id", required=True)
    p_add.add_argument("--pack", required=True)
    p_add.add_argument("--when", required=True, help="必填: 什么时候该调它")
    p_add.add_argument("--run", default=None, help="命令行(可用 <args> 占位符)")
    p_add.add_argument("--script", default=None, help="包内脚本名")
    p_add.add_argument("--args", nargs="*", default=[], help="传给脚本的固定参数")
    p_add.add_argument("--note", default="", help="环境陷阱判据: 为什么必须这么写")
    p_add.add_argument("--doc", default="", help="包内深读文档的相对路径(排障才读, 不进常规路径)")
    p_add.add_argument("--timeout", type=int, default=0)
    p_add.add_argument("--pin", action="store_true", help="常显: 浮到父级列表")
    p_add.add_argument("--risky", action="store_true", help="高风险: run 时先打印命令")
    p_add.add_argument("--write", action="store_true", help="真的落盘(默认只打印)")

    args = parser.parse_args(argv)
    try:
        return {
            "run": cmd_run,
            "list": cmd_list,
            "show": cmd_show,
            "add": cmd_add,
        }[args.cmd](args)
    except C.ConfigError as exc:
        print(str(exc))
        return STOP
    except subprocess.TimeoutExpired:
        print(f"[FAIL] 超时(按失败计, 不让卡死的命令挂住调用方)")
        return FAILED


if __name__ == "__main__":
    sys.exit(main())
