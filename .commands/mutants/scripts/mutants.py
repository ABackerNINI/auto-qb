"""变异测试审计的编排 —— WSL 里跑 mutmut(主力) / Windows 里跑 pytest-gremlins(兜底)。

用法::

    python mutants.py setup     [--distro D] [--mirror P] [--branch B] [--no-sync] [--dry-run]
    python mutants.py run       --target G [--pool F ...] [--children N] [--no-refresh] [--dry-run]
    python mutants.py report    [--target G] [--status S,S] [--limit N] [--out DIR] [--dry-run]
    python mutants.py verify    (--from-report F | --ids-file F) [--workers N] [--no-refresh] [--dry-run]
    python mutants.py gremlins  --target F [--pool F ...] [--workers N] [--dry-run]
    python mutants.py status    [--distro D] [--mirror P]

**report → verify 是本包的主线后半段**(首轮 `run` 之后):

- `report` 把镜像里那一轮的存活/未覆盖变异导出成**带 diff 的清单**(`mutmut results` 只回 id,
  没有文件:行与变异内容, 没法三分类); 同时打按状态/按模块的汇总。
- `verify` 对清单里的候选逐条做 **S4 手工确认的机械化版本**: 在镜像里 `mutmut apply <id>` →
  跑**全套件** → 还原, 记 KILLED(假存活, 池没选到) / SURVIVED(真洞候选或等价)。
  **这一步是整轮的时间大头**(实测 ~15s/条), 所以清单要先按 `--status` / 手挑缩小。

**为什么要有这个脚本**(而不是把命令写进 config.toml 的 run 串): 一轮 mutmut 是
「刷新镜像 -> 装工具 -> 清缓存 -> 写 [tool.mutmut] -> 跑 -> 取结果」六步, 中间全是
「看着正常但不生效」的写法(见可行性报告 26-10-08-0231 §10)。把它们收在脚本里, 改配置比改记忆可靠。

**主仓库环境不动**: 镜像仓与工具都只在 WSL 侧(`--mirror`, 默认 `~/auto-qb-mut`); 本脚本
不碰主仓库的 pyproject.toml / .venv(报告 §01 的沙箱纪律)。

**输出策略**: mutmut/gremlins 的进度行(\r 刷新)会被折叠, 只留最后一行汇总 + 警告/报错原文;
存活清单(可能上千行, 超过 AI 工具壳 30KB 内联上限)写到 --out 目录并只回显头部。
"""

from __future__ import annotations

import argparse
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

DEFAULT_DISTRO = "Ubuntu-26.04"
DEFAULT_MIRROR = "~/auto-qb-mut"
DEFAULT_BRANCH = "develop"
MUTMUT_VERSION = "3.8.0"
GREMLINS_VERSION = "1.11.2"
DEFAULT_CHILDREN = 4  # WSL 只有 8 核(.wslconfig), 拉满会打挂
DEFAULT_WORKERS = 8
DEFAULT_OUT = "R:/Temp/auto-qb/mutants"  # 别落仓内(报告 §10 #7)
HEAD_LINES = 30
#: 结果导出脚本(仓库内, 由本脚本推进镜像 /tmp 后执行) —— 它 import mutmut 内部 API, 只能在镜像里跑
DUMP_SCRIPT_REL = ".commands/mutants/scripts/mutants_dump.py"

_PROGRESS = (re.compile(r"\d+/\d+\s"), re.compile(r"pytest-gremlins: Progress "))

_DRY = False


class Fail(RuntimeError):
    """脚本级失败 —— 调用方打印文案并停手(不静默降级)。"""


# ------------------------------------------------------------------ 小工具


def repo_root() -> Path:
    here = Path(__file__).resolve()
    for p in (here, *here.parents):
        if (p / ".git").exists():
            return p
    raise Fail("找不到仓库根(从脚本目录向上没有 .git)")


def _say(msg: str = "") -> None:
    print(msg)


def _run(cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None,
         check: bool = True) -> subprocess.CompletedProcess:
    if _DRY:
        _say("+ " + " ".join(cmd))
        return subprocess.CompletedProcess(cmd, 0, "", "")
    proc = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and proc.returncode != 0:
        raise Fail(f"命令失败(rc={proc.returncode}): {' '.join(cmd)}\n{proc.stdout.strip()}\n{proc.stderr.strip()}")
    return proc


def _bq(path: str) -> str:
    """把路径变成 bash 里安全的字面量; `~/x` 展开成 `$HOME/x`(引号内的 `~` 不展开)。"""
    if path == "~":
        return '"$HOME"'
    if path.startswith("~/"):
        return '"$HOME/' + path[2:].replace('"', '') + '"'
    return '"' + path.replace('"', '') + '"'


def check_mirror(mirror: str) -> None:
    """镜像必须是 **WSL 侧**路径 —— 收到 Windows 路径说明它被调用方 shell 展开过。

    Git Bash 会把未加引号的 `~/auto-qb-mut` 展开成本机家目录(`C:/Users/...`), 再进 WSL 就是
    一个不存在(且语义错误)的路径。这种错**不会报错**, 只会让后续步骤在别处莫名其妙地失败 ——
    所以在这里停手, 而不是让它跑下去。走 `commands run mutants.*` 时 cmd.exe 不展开 `~`, 不受影响。
    """
    if re.match(r"^[A-Za-z]:[\\/]", mirror) or mirror.startswith("\\\\"):
        raise Fail(
            f"--mirror 收到 Windows 路径: {mirror}\n"
            "  镜像仓在 WSL 侧, 要写 WSL 路径(默认 ~/auto-qb-mut)。\n"
            "  在 Git Bash 里手工调用时, `~` 必须加引号: --mirror '~/auto-qb-mut'"
        )


def _wsl(distro: str, script: str, *, check: bool = True) -> subprocess.CompletedProcess:
    if shutil.which("wsl.exe") is None and not _DRY:
        raise Fail("找不到 wsl.exe —— 本机没装 WSL, 走 mutants.gremlins(Windows 兜底)")
    return _run(["wsl.exe", "-d", distro, "--", "bash", "-lc", script], check=check)


def _wsl_write(distro: str, remote_path: str, content: str) -> None:
    """把文本写进 WSL 的文件 —— **走 stdin**, 不走命令行参数。

    多行内容塞进 `bash -lc '<script>'` 会被 WSL 的登录壳按行拆开(实测: 后续行不报错地
    落到别处), 所以统一用 `cat > <path>` + stdin 传内容。目标路径必须是 WSL 侧绝对路径。
    """
    if _DRY:
        _say(f"+ (stdin -> {remote_path}) {len(content)} bytes")
        return
    proc = subprocess.run(
        ["wsl.exe", "-d", distro, "--", "bash", "-lc", f"cat > {_bq(remote_path)}"],
        input=content, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if proc.returncode != 0:
        raise Fail(f"写入 WSL 文件失败({remote_path}, rc={proc.returncode}): {proc.stderr.strip()}")


def _strip_spinner(line: str) -> str:
    """去掉行首的 spinner / 缩进, 只留内容 —— 用来判「这是不是同一条被反复刷新的输出」。"""
    return re.sub(r"^[^0-9A-Za-z\u4e00-\u9fff]+", "", line).strip()


def _collapse(text: str) -> tuple[list[str], str]:
    """折叠 \\r 刷新出来的进度: 返回(其余正文, 最后一条进度汇总)。

    两级: 1) **连续近重复**只留最后一条(工具用 spinner 原地刷新, 拆开看就是同一句话重复几十遍);
    2) 含 `N/M` 或 `gremlins Progress` 的行是纯进度, 只留最后一条作汇总。
    其余行(警告 / 报错 / 速度)原样保留 —— 折叠的是刷新, 不是内容。
    """
    raw = [ln for ln in re.split(r"[\r\n]+", text) if ln.strip()]
    dedup: list[str] = []
    for line in raw:
        if dedup and _strip_spinner(dedup[-1]) == _strip_spinner(line):
            dedup[-1] = line
        else:
            dedup.append(line)
    body: list[str] = []
    last = ""
    for line in dedup:
        if any(p.search(line) for p in _PROGRESS):
            last = line.strip()
        else:
            body.append(line.rstrip())
    if last:
        m = re.search(r"\d+/\d+.*", last)
        last = m.group(0) if m else last
    return body, last


def _git_url() -> str:
    proc = _run(["git", "-C", str(repo_root()), "remote", "get-url", "origin"])
    return proc.stdout.strip()


def _slug(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-") or "target"


# ------------------------------------------------------------------ 子命令


def _ensure_mirror(distro: str, mirror: str, branch: str, *, refresh: bool, no_sync: bool) -> None:
    mq = _bq(mirror)
    have = _wsl(distro, f"test -d {mq}/.git", check=False).returncode == 0
    if not have:
        _say(f"[1/3] 建镜像仓 {mirror} (git clone)")
        _wsl(distro, f"git clone -q --branch {branch} {_git_url()} {mq}")
    elif refresh:
        _say(f"[1/3] 刷新镜像仓 {mirror} (fetch + 硬切到 origin/{branch})")
        _wsl(distro, f"git -C {mq} fetch -q origin {branch} && git -C {mq} checkout -q -f -B {branch} FETCH_HEAD")
    else:
        _say(f"[1/3] 跳过刷新(--no-refresh): {mirror}")
    if not no_sync:
        _say("[2/3] uv sync")
        _wsl(distro, f"cd {mq} && uv sync -q")
    else:
        _say("[2/3] 跳过 uv sync(--no-sync)")


def _ensure_tool(distro: str, mirror: str) -> None:
    mq = _bq(mirror)
    _say(f"[3/3] 确保 mutmut=={MUTMUT_VERSION} 在镜像 venv 里(缺了才装)")
    _wsl(distro, f"cd {mq} && test -x .venv/bin/mutmut || uv pip install -q mutmut=={MUTMUT_VERSION}")
    # WSL 里通常只有 python3; 包脚本的 wrapper 端到端用例要裸 `python`(报告 §10 #13)
    _wsl(
        distro,
        'command -v python >/dev/null 2>&1 || { mkdir -p "$HOME/.local/bin" '
        '&& ln -sf "$(command -v python3)" "$HOME/.local/bin/python"; }',
        check=False
    )


def cmd_setup(args: argparse.Namespace) -> int:
    _ensure_mirror(args.distro, args.mirror, args.branch, refresh=not args.no_refresh, no_sync=args.no_sync)
    _ensure_tool(args.distro, args.mirror)
    _say(f"[OK] 镜像就绪: {args.mirror} (distro={args.distro}, branch={args.branch})")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    _ensure_mirror(args.distro, args.mirror, args.branch, refresh=not args.no_refresh, no_sync=args.no_sync)
    _ensure_tool(args.distro, args.mirror)
    mq = _bq(args.mirror)

    if not args.pool:
        _say("[WARN] 没给 --pool: 会用全 tests 当池 —— 实测会把 WSL 打挂(报告 §07 对照四), 强烈建议给定向池")
    # 清缓存: 目标/池一变, 旧 mutants/ 会让 mutmut 保留旧结果并「0 files mutated」提前收工(实测)
    _say("[4/6] 清 mutants/ 与 mutmut-cache.db")
    _wsl(args.distro, f"cd {mq} && rm -rf mutants mutmut-cache.db")
    _say("[5/6] 写 [tool.mutmut] (目标 / 池 / forkserver / deselect)")
    pool = " ".join(_bq(p) for p in args.pool)
    _wsl(
        args.distro, f"cd {mq} && .venv/bin/python .commands/mutants/scripts/set_conf.py "
        f"--target {_bq(args.target)}" + (f" --pool {pool}" if args.pool else "")
    )
    _say(f"[6/6] mutmut run --max-children {args.children}")
    proc = _wsl(args.distro, f"cd {mq} && .venv/bin/mutmut run --max-children {args.children}", check=False)
    body, summary = _collapse(proc.stdout + "\n" + proc.stderr)
    for line in body:
        _say(line)
    if summary:
        _say(f"SUMMARY: {summary}")
    if proc.returncode != 0:
        _say(f"[FAIL] mutmut 退出码 {proc.returncode} —— 常见原因: 基线不绿(工具要求先全绿) / 池里没有测试 / 配置写错")
        return 1

    _write_results(args)
    return 0


def _write_results(args: argparse.Namespace) -> None:
    proc = _wsl(args.distro, f"cd {_bq(args.mirror)} && .venv/bin/mutmut results", check=False)
    text = proc.stdout.strip()
    n = len([x for x in text.splitlines() if x.strip()])
    if _DRY:
        _say(f"[结果] (dry-run 未取) 预计未杀死 {n} 条")
        return
    stamp = datetime.now().strftime("%y-%m-%d-%H%M")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{stamp}-{_slug(args.target)}-results.txt"
    path.write_text(text + "\n", encoding="utf-8")
    _say(f"[结果] 未杀死(存活+超时) {n} 条 -> {path}")
    for line in text.splitlines()[:HEAD_LINES]:
        _say(line)
    if n > HEAD_LINES:
        _say(f"... 另有 {n - HEAD_LINES} 条, 读全文见上面的文件(别整读, 按需 grep)")


def cmd_report(args: argparse.Namespace) -> int:
    """把镜像里**上一轮**的存活/未覆盖变异导出成带 diff 的清单 + 分类汇总(只读, 不刷新镜像)。"""
    _ensure_mirror(args.distro, args.mirror, args.branch, refresh=False, no_sync=True)
    _ensure_tool(args.distro, args.mirror)
    dump_src = (repo_root() / DUMP_SCRIPT_REL).read_text(encoding="utf-8")
    _wsl_write(args.distro, "/tmp/mutants_dump.py", dump_src)
    mq = _bq(args.mirror)
    cmd = f"cd {mq} && .venv/bin/python /tmp/mutants_dump.py --status {shlex.quote(args.status)}"
    if args.limit:
        cmd += f" --limit {args.limit}"
    if args.target:
        cmd += f" --target-glob {shlex.quote(args.target)}"
    proc = _wsl(args.distro, cmd, check=False)
    if proc.returncode != 0:
        for line in (proc.stdout + "\n" + proc.stderr).splitlines()[-20:]:
            _say(line)
        _say(f"[FAIL] 导出失败(rc={proc.returncode}) —— 先在镜像里跑一轮 mutants.run")
        return 1

    text = proc.stdout
    stamp = datetime.now().strftime("%y-%m-%d-%H%M")
    slug = _slug(args.target) if args.target else "mutants"
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{stamp}-{slug}-mutants-dump.txt"
    path.write_text(text, encoding="utf-8")
    n = sum(1 for line in text.splitlines() if line.startswith("@@@ "))
    _say(f"[结果] 导出 {n} 条(带 diff) -> {path}")
    for line in proc.stderr.strip().splitlines():
        _say(line)
    _say(f"[下一步] 挑候选后: commands run mutants.verify -- --from-report \"{path}\"")
    return 0


def _candidate_ids(args: argparse.Namespace) -> list[str]:
    """候选 id 来源: --ids-file 直给, 或 --from-report 从 mutants.report 的产物里按状态挑。"""
    if args.ids_file:
        return [x.strip() for x in Path(args.ids_file).read_text(encoding="utf-8").splitlines() if x.strip()]
    want = {s.strip() for s in (args.only_status or "survived").split(",") if s.strip()}
    ids: list[str] = []
    for line in Path(args.from_report).read_text(encoding="utf-8").splitlines():
        if not line.startswith("@@@ "):
            continue
        mid, _, status = line[4:].partition(" :: ")
        if status.strip() in want:
            ids.append(mid.strip())
    return ids


def cmd_verify(args: argparse.Namespace) -> int:
    """S4 的机械化: 对候选逐条 `mutmut apply` → 跑**全套件** → 还原, 记 KILLED / SURVIVED。

    KILLED = 全套件能杀 ⇒ 池没选到(假存活); SURVIVED = 全套件仍杀不掉 ⇒ 真洞候选或等价变异。
    这是整轮的时间大头(实测 ~15s/条), 所以先 `mutants.report` 再挑候选。**幂等可续跑**:
    已写进结果文件的 id 会跳过。
    """
    if not (args.from_report or args.ids_file):
        raise Fail("verify 需要 --from-report(用 mutants.report 的产物)或 --ids-file")
    ids = _candidate_ids(args)
    if not ids:
        raise Fail("候选为空 —— 核 --only-status / --ids-file / 报告文件")
    _ensure_mirror(args.distro, args.mirror, args.branch, refresh=not args.no_refresh, no_sync=args.no_sync)
    _ensure_tool(args.distro, args.mirror)
    mq = _bq(args.mirror)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{datetime.now().strftime('%y-%m-%d-%H%M')}-s4-verify.txt"
    done = set()
    if path.exists():
        done = {x.split(" :: ")[0] for x in path.read_text(encoding="utf-8").splitlines() if " :: " in x}
    todo = [i for i in ids if i not in done]
    _say(f"[verify] 候选 {len(ids)} 条(已验 {len(done)} · 本次 {len(todo)}) · 全套件 -n {args.workers}")
    _say(f"[verify] 结果 -> {path}(逐条 ~15s, 中断后重跑自动续)")

    killed = survived = failed = 0
    with path.open("a", encoding="utf-8") as fh:
        for i, mid in enumerate(todo, 1):
            t0 = time.time()
            script = (
                f"cd {mq} && git checkout -- src/ 2>/dev/null; "
                f".venv/bin/mutmut apply {mid} >/dev/null 2>&1 || {{ echo APPLYFAIL; exit 9; }}; "
                f".venv/bin/python -m pytest tests/ -q -n {args.workers} --no-cov -x -p no:cacheprovider 2>&1 | tail -4; "
                f"git checkout -- src/ 2>/dev/null"
            )
            proc = _wsl(args.distro, script, check=False)
            summary = next(
                (l.strip() for l in reversed(proc.stdout.strip().splitlines())
                 if ("passed" in l or "failed" in l or "error" in l)), ""
            )
            if "APPLYFAIL" in proc.stdout:
                verdict, failed = "APPLY_FAIL", failed + 1
            elif "failed" in summary or "error" in summary:
                verdict, killed = "KILLED", killed + 1
            else:
                verdict, survived = "SURVIVED", survived + 1
            fh.write(f"{mid} :: {verdict} :: {summary}\n")
            fh.flush()
            _say(f"  [{i}/{len(todo)}] {time.time() - t0:.0f}s {verdict}  {mid}")
    _wsl(args.distro, f"cd {mq} && git checkout -- src/ 2>/dev/null", check=False)
    _say(f"[verify] KILLED(假存活) {killed} · SURVIVED(真洞候选) {survived} · 失败 {failed} -> {path}")
    return 0


def cmd_gremlins(args: argparse.Namespace) -> int:
    root = repo_root()
    env = dict(os.environ)
    env["TMPDIR"] = "R:/Temp/auto-qb/tests"  # 不设会在收尾崩(假红, 报告 §10 #6)
    env["COVERAGE_FILE"] = "R:/Temp/auto-qb/gremlins.cov"
    if not args.pool:
        _say("[WARN] 没给 --pool: 会扫全 tests 收集覆盖 —— 慢且可能撞 WinError 206(报告 §10 #2)")
    cmd = [
        "uv", "run", "--with", f"pytest-gremlins=={GREMLINS_VERSION}", "pytest", *args.pool, "--gremlins",
        f"--gremlin-targets={args.target}", "-n", "0", "--no-cov", f"--gremlin-workers={args.workers}"
    ]
    proc = _run(cmd, cwd=root, env=env, check=False)
    body, summary = _collapse(proc.stdout + "\n" + proc.stderr)
    for line in body:
        _say(line)
    if summary:
        _say(f"SUMMARY: {summary}")
    return proc.returncode


def cmd_status(args: argparse.Namespace) -> int:
    mq = _bq(args.mirror)
    script = (
        f"echo mirror={mq}; cd {mq} 2>/dev/null || {{ echo '[FAIL] 镜像不存在, 先跑 setup'; exit 3; }}; "
        "echo head=$(git rev-parse --short HEAD 2>/dev/null || echo none); "
        "echo mutmut=$(test -x .venv/bin/mutmut && echo yes || echo no); "
        "echo mutants=$(du -sh mutants 2>/dev/null | cut -f1 || echo none); "
        ".venv/bin/mutmut results 2>/dev/null | wc -l | sed 's/^/not_killed=/'; "
        "test -f pyproject.toml && grep -m1 only_mutate pyproject.toml"
    )
    proc = _wsl(args.distro, script, check=False)
    _say(proc.stdout.strip() or proc.stderr.strip())
    out = Path(args.out)
    if out.is_dir():
        files = sorted(out.glob("*-results.txt"))
        if files:
            _say(f"[上次结果] {files[-1]} ({files[-1].stat().st_size} B)")
    return 0 if proc.returncode == 0 else 1


# ------------------------------------------------------------------ 入口


def main(argv: list[str] | None = None) -> int:
    global _DRY
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("cmd", choices=("setup", "run", "report", "verify", "gremlins", "status"))
    p.add_argument("--target", help="run: 只变异的目标 glob(相对仓库根, 例 '**/config/*.py'); gremlins: 目标文件")
    p.add_argument("--pool", nargs="*", default=[], help="测试选择池(定向的几个文件; 别用全 tests)")
    p.add_argument("--children", type=int, default=DEFAULT_CHILDREN, help=f"mutmut --max-children(默认 {DEFAULT_CHILDREN})")
    p.add_argument("--workers", type=int, default=DEFAULT_WORKERS,
                   help=f"gremlins --gremlin-workers / verify 的全套件并行度(默认 {DEFAULT_WORKERS})")
    p.add_argument("--status", default="survived,no tests,timeout,suspicious,segfault",
                   help="report: 导出哪些状态(逗号分隔; 默认全部非 killed)")
    p.add_argument("--limit", type=int, default=0, help="report: 最多导出多少条(0 = 不限)")
    p.add_argument("--from-report", help="verify: 用 mutants.report 的产物文件挑候选")
    p.add_argument("--ids-file", help="verify: 直接给一份候选 id 清单(每行一条)")
    p.add_argument("--only-status", default="survived", help="verify: 从 --from-report 里挑哪些状态(默认 survived)")
    p.add_argument("--distro", default=DEFAULT_DISTRO, help=f"WSL 发行版(默认 {DEFAULT_DISTRO})")
    p.add_argument("--mirror", default=DEFAULT_MIRROR, help=f"WSL 镜像仓路径(默认 {DEFAULT_MIRROR})")
    p.add_argument("--branch", default=DEFAULT_BRANCH, help=f"镜像跟的分支(默认 {DEFAULT_BRANCH})")
    p.add_argument("--out", default=DEFAULT_OUT, help=f"结果落盘目录(默认 {DEFAULT_OUT}, 别落仓内)")
    p.add_argument("--no-refresh", action="store_true", help="不 fetch/硬切镜像(用现成的工作树)")
    p.add_argument("--no-sync", action="store_true", help="不跑 uv sync")
    p.add_argument("--dry-run", action="store_true", help="只打印将执行的命令")
    args = p.parse_args(argv)
    _DRY = args.dry_run

    if args.cmd in ("run", "gremlins") and not args.target:
        sys.stderr.write("[FAIL] 这条子命令必须给 --target\n")
        return 2
    try:
        if args.cmd != "gremlins":
            check_mirror(args.mirror)
        return {"setup": cmd_setup, "run": cmd_run, "report": cmd_report, "verify": cmd_verify,
                "gremlins": cmd_gremlins, "status": cmd_status}[args.cmd](args)
    except Fail as exc:
        sys.stderr.write(f"[FAIL] {exc}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
