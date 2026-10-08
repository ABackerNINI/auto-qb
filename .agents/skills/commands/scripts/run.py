"""入口: run / list / show / add —— 项目命令的统一调用面。

引擎不认识任何具体动作, 一切命令都来自 `.commands/` 下的包。
执行者只需要回答"现在该调哪个", 命令怎么拼不归它管。

退出码: 0 成功 · 1 失败(配置写错 / 占位符展不开 / 前置不满足 / 命令本身非 0 —— 统一 0/1, 语义只在输出)

输出契约(2026-09-27 P1, 计划 26-09-26-2345; 2026-09-30 修订): 包脚本可用 RESULT: / WHY: / NEXT: /
EVIDENCE: 协议行收尾(语义单点在脚本), 失败时紧跟 [FAIL] 行转述; 文本输出**不出现裸 rc 数字** ——
退出码只走进程通道, 语义只在协议行, 免得调用方去查码表。
输出**一律全文透传, 引擎不做有损摘要**: 「略过 N 行 + show 拿命令直接跑」的提示会把调用方逼成
show → 裸跑两步返工, 会话后期每步都是带全量历史的整轮请求, 省几行换两轮 token 永远亏。
省 token 走**声明式静默**: 任务自己在包配置里标 silent_success —— 成功只出结论行, 失败照旧全文。
编码口径(2026-09-30): 引擎**自身**的 stdout/stderr 在 main() 入口锁 UTF-8 —— 管道下不再按
本地码页出中文(否则部分终端乱码, 详单在 pitfalls/ops/console-encoding.md)。
"""

from __future__ import annotations

import argparse
import io
import json
import locale
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # 允许 `python scripts/run.py` 直接跑

import _config as C  # noqa: E402
import _tree as T  # noqa: E402

STOP = 1
FAILED = 1  # 命令本身非 0 —— 与 STOP 同为失败; 语义全在输出里, 码表没有存在的必要(计划 26-09-28-0157)
SUMMARY_LINES = 3  # silent_success 任务无结论形态时的兜底末几行
# 协议行判据(输出契约): 失败时从正文剥出来紧跟 [FAIL] 转述 —— 全文透传后若不剥, 协议行会出现两遍。
_RESULT = re.compile(r"^\s*(?:RESULT|WHY|NEXT|EVIDENCE):")
# 结论行判据(silent_success, 计划 26-09-28-0157 §10): pytest 的 "N passed…" 与覆盖率的 "TOTAL …" 是
# 任务的存在意义本身, 但警告/覆盖率明细可能打在其前其后 —— 声明式静默只留这类行, 其余不上屏。
_CONCLUSION = re.compile(r"^\s*\d+ (?:passed|failed)\b|^\s*TOTAL\s|^\s*no tests ran\b")

# 子进程必须说 UTF-8。Windows 上 Python 子进程的 stdout 一旦被管道接住, 编码取的是
# **本地码页**(本机 cp936) —— 中文按 GBK 出去, 而本引擎按 UTF-8 解, 结果是一串 U+FFFD:
# 实测 2026-09-24 `已生成 16 个索引` 显示成 `������ 16 ������`(kb.index 这类包脚本)。
# 放在 pack env **之前** —— 包仍然可以覆盖。
_CHILD_ENV = {"PYTHONIOENCODING": "utf-8"}

# ------------------------------------------------------------------ 子命令


def cmd_run(args: argparse.Namespace) -> int:
    tree = C.load_tree()
    task = _pick(tree, args.task)
    extra = _extra(args)
    cmds = C.task_commands(task, tree.root, extra)

    # 详略随风险自适应: 带前置检查或标了高风险的, 先自证"将要跑什么"再跑。
    # 只打首条 + 条数 —— 全量展开串每轮提交都重复, 是常规路径上的纯 token 税; 要看全量: show <id>。
    if task.requires or task.risky:
        print(f"[自证] {task.id} 将要执行:")
        for cmd in cmds[:1]:
            print(f"  {cmd}")
        if len(cmds) > 1:
            print(f"  …(共 {len(cmds)} 条, 全量: show {task.id})")

    for check in task.requires:
        ok, out = _shell(C.expand(check, tree.root, C.args_text(extra)), task.timeout)
        if not ok:
            print(f"[STOP] 前置不满足: {check}")
            if out.strip():
                print(out.rstrip())
            print(f"  NEXT: 处理后重跑 commands run {task.id}; 定义: show {task.id}")
            return STOP
        print(f"[前置] ok: {check}")

    for cmd in cmds:
        started = time.time()
        if task.stream:
            # 前台长跑(常驻服务): stdio 直连终端, 输出实时可见, Ctrl-C 直达子进程组 ——
            # 捕获式 _shell 的"跑完才见输出"对它是反模式; timeout 同理不适用(服务没有"跑完")。
            # env 仍注入 _CHILD_ENV: 一旦输出被管道接住(AI 工具捕获), 子进程照旧说 UTF-8。
            try:
                proc = subprocess.run(
                    cmd,
                    shell=True,
                    cwd=str(C.find_root()),
                    env={
                        **os.environ,
                        **_CHILD_ENV,
                        **C.pack_env(task)
                    },
                )
            except KeyboardInterrupt:
                print(f"\n[stop] {task.id} (Ctrl-C)")
                return 0
            spent = time.time() - started
            if proc.returncode != 0:
                print(f"[FAIL] {task.id} (exit {proc.returncode}, {spent:.1f}s) —— 输出见上, 未捕获")
                return FAILED
            print(f"[ok] {task.id} ({spent:.1f}s)")
            continue
        try:
            ok, out = _shell(cmd, task.timeout, env=C.pack_env(task))
        except subprocess.TimeoutExpired:
            # 超时必须指名卡住的是哪条命令 —— 多命令 task 里"哪条卡死"本身就是排障结论
            print(f"[FAIL] {task.id} 超时({task.timeout}s) —— 卡住的命令: {cmd}")
            return FAILED
        spent = time.time() - started
        if not ok:
            print(f"[FAIL] {task.id} ({spent:.1f}s)")
            proto = _protocol_lines(out)
            body = _strip_protocol(out) if proto else out
            for ln in proto:  # 协议行紧跟 [FAIL] —— 语义单点在脚本, 引擎只负责让它可见
                print(f"  {ln}")
            _passthrough(body)
            return FAILED
        print(f"[ok] {task.id} ({spent:.1f}s)")
        _emit(out, silent_success=task.silent_success)
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    tree = C.load_tree()
    print(T.render(tree, args.path))
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
    """取 task; **也接受包路径限定的写法** `包/子包.<task>`(取最后一个 `/` 之后)。

    只认一种写法就会在"看起来对"的另一种上 STOP: `list` 里显示的是短 id(`ship.commit`),
    而文档与人习惯写全路径(`my-commit-flow/ship.commit`)—— 两种都认, 少一次排障往返。
    """
    task = tree.tasks.get(name)
    short = name.rsplit("/", 1)[-1]
    if task is None and short != name:
        task = tree.tasks.get(short)
    if task is None:
        near = [t for t in tree.tasks if name in t or short in t or t.startswith(name.split(".")[0])]
        hint = f"  相近: {', '.join(sorted(near)[:8])}" if near else "  用 list 平铺找(全树一次列出)"
        raise SystemExit(f"[STOP] 没有这个 task: {name}\n{hint}\n"
                         "  写法: `run <id>`; id 见 list(子包可写 `包/子包.<task>`)")
    return task


def _extra(args: argparse.Namespace) -> list[str]:
    """调用方给的额外参数, 以 **argv 列表**直达脚本(2026-09-27 P2) —— 不再 join 成字符串,
    免得后面 `split()` 把含空格的路径拆碎; 引号由调用方 shell 层负责。"""
    extra = list(getattr(args, "extra", None) or [])
    if extra and extra[0] == "--":
        extra = extra[1:]
    return extra


def _kill_tree(pid: int) -> None:
    """连孙子一起杀 —— `shell=True` 下直接子进程是 cmd.exe, 真正干活的工具是它的孙子。

    ❗`subprocess.run(timeout=)` 超时只 kill **直接子进程**(cmd.exe), 孙子(yapf / uv / git)
      会被留成**孤儿**: 继续 100% CPU 烧着、还占着管道读端, 父进程即便"超时返回"也可能卡在
      communicate 的 join 上(2026-10-08 实报: yapf 在沙箱里挂住, 闸门超时后 yapf 仍在跑且一直
      写磁盘)。与 my-commit-flow `_pipeline._kill_tree` 同款处置, 判据单点见
      memory-bank/pitfalls/testing/sandbox-tool-cache.md。
    """
    try:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        pass


def _shell(cmd: str, timeout: int, env: dict[str, str] | None = None) -> tuple[bool, str]:
    full = {**os.environ, **_CHILD_ENV, **(env or {})}
    # ❗不用 subprocess.run(timeout=): 它超时只杀直接子进程(见 _kill_tree)。用 Popen 拿 pid,
    #   到点杀整棵树并收尸; 然后**照旧上抛 TimeoutExpired** —— cmd_run 靠它打「超时指名卡住的命令」。
    proc = subprocess.Popen(
        cmd,
        shell=True,
        cwd=str(C.find_root()),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=full,
    )
    try:
        out_b, err_b = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        _kill_tree(proc.pid)
        try:
            out_b, err_b = proc.communicate(timeout=5)  # 收尸: 树杀掉了, 管道才会 EOF
        except subprocess.TimeoutExpired:
            out_b, err_b = b"", b""
        raise
    return proc.returncode == 0, _decode(out_b) + _decode(err_b)


def _local_codepage() -> str:
    """本地码页回退编码 —— 必须是原生子进程的真实输出编码, 不随 Python 的 UTF-8 模式变。

    ❗不能用 `locale.getpreferredencoding(False)`: PYTHONUTF8=1 / -X utf8 下它返回
    'utf-8' 而非码页, GBK 回退整条静默失效(2026-09-25 实测, 守阵
    test_decode_falls_back_to_local_codepage 假红)。原生子进程不吃 PYTHONUTF8,
    Windows 上恒按系统 ANSI 码页输出, 所以直接问系统要 (GetACP)。
    """
    if sys.platform == "win32":
        import ctypes

        return f"cp{ctypes.windll.kernel32.GetACP()}"
    return locale.getpreferredencoding(False)


def _decode(raw: bytes | None) -> str:
    """把子进程输出解成文本 —— ❗不假定它是 UTF-8。

    顺序: ① UTF-8 (子进程已被 `_CHILD_ENV` 强制, 也是 git / uv 这类工具的原生编码)
    ② 本地码页 (非 Python 子进程仍可能按 cp936 输出中文) ③ 兜底 replace, 永不抛。
    按 UTF-8 硬解历史事故: 中文变 U+FFFD 且**静默** —— 退出码照旧 0, 只是人读不了。
    """
    data = raw or b""
    for enc in ("utf-8", _local_codepage()):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _utf8_self_stdio(*streams: io.TextIOBase | None) -> None:
    """把引擎**自己**的 stdout/stderr 锁成 UTF-8 —— "部分终端乱码"的根因(2026-09-30)。

    子进程侧已有 `_CHILD_ENV` + `_decode` 兜住, 但引擎自己 print 的中文(协议行 / 包摘要 /
    透传的子进程正文)走的是 Python 自己的 stdio: 真控制台上走 WriteConsoleW(Unicode, 与
    码页无关, 永不乱); stdout 一旦是**管道**(Git Bash 的 mintty、AI 工具捕获、`| tee`、
    CI 日志), 编码就回退本地码页 cp936 —— 实测 `show kb.active` 的 `何时用` 在管道下按
    GBK 出字节, 按 UTF-8 解的对端看到的就是乱码, 且退出码照旧 0; Windows Terminal /
    VS Code 这类真控制台终端正常 —— 这就是"部分终端"的分界线
    (详单: pitfalls/ops/console-encoding.md)。
    errors=replace 与 `_decode` 同款: 编不出的字符降级显示, 不让打印本身抛
    UnicodeEncodeError 把整条命令打死。
    """
    for stream in streams or (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def _protocol_lines(out: str) -> list[str]:
    """输出里的协议行(RESULT / WHY / NEXT / EVIDENCE), 原样保序 —— 失败转述用。"""
    return [ln for ln in out.splitlines() if _RESULT.match(ln)]


def _strip_protocol(out: str) -> str:
    """剥掉协议行后的正文 —— 失败路径已把协议行转述在 [FAIL] 后, 摘要里不再重复它们。"""
    return "\n".join(ln for ln in out.splitlines() if not _RESULT.match(ln))


def _passthrough(out: str) -> None:
    """全文透传 —— 引擎不做有损摘要(2026-09-30 定调, 见模块 docstring)。

    有损摘要 + 「略过 N 行; show 拿命令直接跑」的提示会把调用方逼成 show → 裸跑两步返工:
    会话后期每步都是带全量历史的整轮请求, 省 3 行换两轮 token 永远亏(实测教训, 详见
    pitfalls/kb/scripts.md)。空行不打印 —— 两格缩进会把空行打成尾随空白; 内容行一个不丢。
    """
    for ln in out.splitlines():
        if ln.strip():
            print(f"  {ln.rstrip()}")


def _conclusions(out: str, limit: int = SUMMARY_LINES) -> list[str]:
    """silent_success 任务的成功输出: 只留结论行(N passed / TOTAL / no tests ran)。

    与已退役的通用有损摘要不同, 这是任务在包配置里**声明**的静默 —— 不打「略过」提示,
    调用方要明细是主动 show 取命令加参数, 不是被提示逼出的两步返工。
    一条结论都没中(输出形态变了)就退回末 N 行, 不让输出彻底变盲。
    """
    lines = [ln.rstrip() for ln in out.splitlines() if ln.strip()]
    if len(lines) <= limit:
        return lines
    picked = [ln for ln in lines if _CONCLUSION.match(ln)]
    return picked if picked else lines[-limit:]


def _emit(out: str, silent_success: bool = False) -> None:
    """成功输出: 默认全文透传; silent_success 任务只出结论行 —— 两种形态都不打「略过」提示。"""
    if silent_success:
        for line in _conclusions(out):
            print(f"  {line}")
        return
    _passthrough(out)


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
    _utf8_self_stdio()  # 引擎自己的输出先锁 UTF-8 —— 管道对端一律按 UTF-8 解(见函数 docstring)
    parser = argparse.ArgumentParser(
        prog="run.py",
        description="项目命令的统一调用面 —— 只认 task id, 命令本体在包里单点定义。",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="校验前置后执行(常规路径只用它)")
    p_run.add_argument("task")
    p_run.add_argument("extra", nargs=argparse.REMAINDER, help="填进 <args> 占位符")

    p_list = sub.add_parser("list", help="平铺列出全部包与命令(一次看全, 无需下钻)")
    p_list.add_argument("path", nargs="?", default=None, help="只看某子树, 如 <父包>/<子包>")

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
    p_add.add_argument("--pin", action="store_true", help="标 ★(高频命令记号; 平铺视图下仅作视觉锚点)")
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
