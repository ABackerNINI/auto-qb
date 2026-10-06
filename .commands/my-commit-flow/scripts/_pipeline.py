"""提交流水线的**内部共享件** —— 闸门引擎 / 占位符展开 / 改动清单 / 配置体检。

v3 输出契约(计划 26-09-28-0157)「沉默即成功」: 本模块只提供机制, **不打印检查表** ——
常规路径成功即静默, 失败由调用方(sync / commit / push)给一行「原因 + 下一步」。
v3.1(2026-10-06)在本模块加了唯一的**输出机制**例外: 「步骤登记」段(`step` / `emit_steps`)——
结果行仍是上面那句话, 只是**真改写 HEAD 的步骤**由它登记成一行证据, 见该段注释。
人工排障口: `_pipeline.py --show-config` 看生效配置, `--init` 生成新仓库的配置初稿。

前身是 preflight.py(检查表式预检, v2 计划 26-09-26-2345); v3 把"检查"下沉进 ship 编排,
把"报告"压缩成一行, 检查项本身一个不删(保全清单见计划 §04)。
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import re
import subprocess
import sys
import threading
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

# ------------------------------------------------------------------ 子进程防挂死
# ❗Windows 上 `subprocess.run(capture_output=True)` 会**无限挂住**, 两种入口都实测到过
#   (2026-10-03 定位, 见 memory-bank/pitfalls/testing/parallel-run.md):
#   ① `_winapi.CreateProcess`(即 `Popen.__init__`)在大量 spawn / 高负载下不再返回
#      —— 本机 4 个 clone 同时跑测试时, 约第 800 次 spawn 起概率性永久阻塞;
#   ② `communicate()` 里 join 读线程: git 的**孙进程**继承了管道写端且不退出时, 读端永远
#      等不到 EOF —— 此时连 `subprocess.run(timeout=…)` 也救不了(timeout 只杀直接子进程,
#      `communicate()` 仍阻塞在 join)。
#   处置: 全程跑在**看门狗线程**里, 硬截止到点就 `taskkill /F /T` 整棵进程树 + 关掉我们这端
#   的管道(不 join), 然后返回一个可判定的失败 —— 让调用方**快速失败**而不是冻住整条 ship。
#   代价: 极少数卡死会泄漏一个幽灵线程(无法从外部杀), 相对于"提交无声中止"可接受。
GIT_TIMEOUT = float(os.environ.get("COMMAND_FLOW_GIT_TIMEOUT", "120"))


def _kill_tree(pid: int) -> None:
    """Windows: 连孙子一起杀掉(`git push` 会派生 sh.exe → git-receive-pack → git)。"""
    try:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        pass


def run_capture(args, cwd=None, timeout: float = GIT_TIMEOUT, shell: bool = False) -> subprocess.CompletedProcess:
    """跑一条命令并抓输出, **保证不永久挂住**(见上面的根因注释)。

    返回 CompletedProcess; 超时/卡死时 rc 记 `-1`(与真实 git 码不冲突), 输出带一句原因。
    实现: 真正的 Popen + communicate 放在看门狗线程里, 主线程只等到 deadline;
    到点后杀掉**整棵进程树**并关掉我们的管道读端, 让读线程随之结束(不 join)。

    `shell=True` 供闸门(`run_gates`)这类**命令串**用 —— 与 git 的 argv 直调不同, 但同样
    走本看门狗(裸 subprocess.run 在 Windows 上同款挂死)。
    """
    box: dict = {}
    argv = args if shell else list(args)

    def _worker() -> None:
        proc = None
        try:
            proc = subprocess.Popen(
                argv,
                shell=shell,
                cwd=str(cwd) if cwd else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace"
            )
            box["pid"] = proc.pid
            out, err = proc.communicate(timeout=timeout)
            box["rc"], box["out"], box["err"] = proc.returncode, out, err
        except subprocess.TimeoutExpired:
            box["rc"] = -1
            box["err"] = f"超时 {timeout:.0f}s (进程树已杀)"
            if proc is not None:
                box["pid"] = proc.pid
                # ❗必须**真的收尸**: 只记下 pid 不杀, 子进程会继续活着占着 cwd 与管道
                # (调用方 tearDown 立刻 rmtree 临时目录 → WinError 32; 实测 2026-10-03)。
                # `subprocess.run` 在这里内部会 kill(), 裸 Popen 得自己做 —— 连孙子一起杀
                # 再 wait() 掉进程, Windows 上 cwd 锁才真正释放。
                _kill_tree(proc.pid)
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass
        except (OSError, subprocess.SubprocessError) as exc:
            box["rc"], box["err"] = -1, f"起不来: {exc!r}"

    worker = threading.Thread(target=_worker, daemon=True)
    worker.start()
    worker.join(timeout + 15)  # 给 communicate 自己一点余量(它内部已有 timeout)
    if worker.is_alive():
        # communicate / CreateProcess 卡在共享管道或系统调用上 —— 杀树 + 关管道, 不等它。
        pid = box.get("pid")
        if pid:
            _kill_tree(int(pid))
        label = argv if shell else list(args)
        return subprocess.CompletedProcess(label, -1, "", f"卡死 (>{timeout:.0f}s, 进程树已杀)")
    label = argv if shell else list(args)
    return subprocess.CompletedProcess(label, box.get("rc", -1), box.get("out", "") or "", box.get("err", "") or "")


def git(*args: str, check: bool = True) -> str:
    # **不能整段 strip()**: `git status --porcelain` 的首列空格表示"无暂存改动",
    # 整段 strip 会把首行的这个空格吃掉 → ' M a/b' 变成 'M  a/b', 首列被误判成已暂存,
    # 且 line[3:] 丢掉路径首字符, 红线匹配会**静默放行**。
    proc = run_capture(["git", *args])
    if check and proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} 失败: {proc.stderr.strip()}")
    return proc.stdout.rstrip("\n")


def git_rc(*args: str) -> int:
    """只关心**退出码**的 git 调用(如 `merge-tree --write-tree`: 0 = 可干净合流, 非 0 = 有冲突)。"""
    return run_capture(["git", *args]).returncode


def git_run(*args: str) -> subprocess.CompletedProcess:
    """要 rc + stderr 的 git 调用(merge --ff-only / rebase / push 的失败原因都在 stderr)。"""
    return run_capture(["git", *args])


def changed_files(with_safety: bool = False) -> tuple[list[str], list[str]]:
    """返回 (staged, unstaged) 文件清单(按 `git status --porcelain` 的两列判读)。

    `with_safety = True`: 每行末补一个状态字符(`S` = 「无参即真动作」的危险脚本, `.` = 其余),
    供 `<each:GLOB|--with-safety>` 的展开把危险脚本剔除 —— **闸门冒烟不做「只挑文件名」的静态
    规则**: 判据留在只有脚本自己知道的地方(见 `_is_parameterless_action` 所在的 gen 脚本)。

    ❗必须带 `-uall`: 默认模式下**未跟踪目录只报一条 `?? <dir>/`**, 于是 `<each:GLOB>` 之类
    按文件的展开**匹配不到新加的文件** —— 新增脚本拿不到冒烟, 且是静默的。

    ❗`--with-safety` 必须走 `-z`(2026-10-03): 危险脚本的状态字符挂在**整段末尾**, 非 -z 形态
    下 rename 记录的 `old -> new` 里 new 之后才是它 —— 用普通行解析会把状态字符切成名单的一部分。
    """
    staged, unstaged = [], []
    # ❗必须关 quotepath(2026-09-29 实测): 默认 ON 时非 ASCII 文件名被八进制转义加引号
    #   (`?? "\346..."`), 解析出的路径不存在 → exists()=False → 按"已暂存删除"被静默跳过
    #   → 什么都没暂存, commit 报 "nothing added"。off 后路径为原始 UTF-8, 解析才对得上。
    if with_safety:
        raw = git("-c", "core.quotepath=off", "status", "--porcelain", "-uall", "-z")
        for rec in [r for r in raw.split("\0") if len(r) > 3]:
            xy = rec[:2].ljust(2)
            path = rec[3:].strip()
            if " -> " in path:  # rename 被 NUL 切成两段后只剩新路径 —— 取它就是
                path = path.split(" -> ")[-1].strip()
            if xy[0] not in (" ", "?"):
                staged.append(path)
            if xy[1] != " ":
                unstaged.append(path)
        return staged, unstaged
    for line in git("-c", "core.quotepath=off", "status", "--porcelain", "-uall").splitlines():
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
EACH_RE = re.compile(r"<each:([^<>|]+?)(?:\|(--[^<>]+))?>")
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


def _safe_files(files: list[str], root) -> tuple[list[str], list[str]]:
    """把 `files` 里的路径分成 (安全, 被摘掉) —— 判据**只问脚本自己**(`<路径> --safety`)。

    `--with-safety` 的语义: 闸门冒烟给脚本加的参数只有 `--help` 一种, 而 `--help` 未必被脚本
    认; 脚本若把陌生参数当无参处理(CLI 无参数 = 执行真动作), 冒烟就会**真去跑一次动作** ——
    `sync.py --help` 真的同步、`push.py --help` 真的推送, 而后者本仓库明确禁止(推送顺序固定)。

    所以这里不问「文件名像不像危险脚本」(那种规则会在下一次改名时静默失效), 而是拿
    `--safety` 探针去问脚本本人: 慢 / 挂住 / 非 0 / 没明说 `action-without-args` 一律按不安全
    (退回不冒烟)。摘掉是**可见的** —— 展开里写明数量, 不是静默丢文件。
    """
    safe: list[str] = []
    skipped: list[str] = []
    for rel in files:
        path = Path(rel)
        full = path if path.is_absolute() else Path(root) / rel
        # 走 run_capture: 同样的 `CreateProcess` 挂死风险(见其上方根因注释)。
        # rc != 0(超时 / 起不来 / 脚本报错)一律按**不安全**摘掉 —— 原实现靠
        # `subprocess.run(timeout=…)` 抛 TimeoutExpired 走到 except 分支, 而 run_capture
        # 把超时收成 rc=-1(不抛), 所以判据必须显式带上 rc(2026-10-03, 改错会静默放行)。
        proc = run_capture([sys.executable, str(full), "--safety"], cwd=root, timeout=10)
        out = f"{proc.stdout or ''}\n{proc.stderr or ''}"
        # 摘掉(不安全)判据: ①脚本自认「无参即真动作」, 或 ②探针没跑通(rc != 0 —— 超时 /
        # 起不来 / 脚本报错)。只有「跑通且没自认危险」才留下冒烟。
        if proc.returncode != 0 or "action-without-args" in out:
            skipped.append(rel)
        else:
            safe.append(rel)
    return safe, skipped


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
        if m.group(2) == "--with-safety":
            files, skipped = _safe_files(files, ctx["root"])
            if skipped:  # 摘掉必须看得见: 不然"没冒烟"与"没改动"分不开
                print(f"[冒烟] 摘掉 {len(skipped)} 个「无参即真动作」脚本: {'、'.join(skipped)}")
            if not files:
                return [], f"<each:{m.group(1)}|--with-safety> 全部被安全过滤摘掉"
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
                "(只认 <root> / <skill-dir:NAME> / <changed:GLOB> / <each:GLOB> / <each:GLOB|--with-safety>)"
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
                # 走 run_capture(shell 模式): 闸门命令串同样会撞 Windows 的 CreateProcess / 管道挂死,
                # 且闸门带超时语义 —— 看门狗到点杀**整棵进程树**, 比裸 subprocess.run(timeout=…)
                # 只杀直接子进程更彻底(根因见模块顶「子进程防挂死」段)。
                proc = run_capture(real, cwd=str(ctx["root"]), timeout=timeout, shell=True)
                rc = proc.returncode
                out = (proc.stdout or "") + (proc.stderr or "")
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


# ------------------------------------------------------------------ 步骤登记(v3.1「改写留痕」)
# ❗为什么要有它: 一次命令内部 HEAD 会被改写多次(提交 → 内部 rebase → 闸门改后 amend → 推送再同步),
#   而 v3 只吐终值那一个 hash —— 执行者看到 hash 与印象不符就跑去查原因(2026-10-06 用户指出)。
#   v3.1 的补法不是推翻它: **只补"真发生了"的步骤**, 绝不回到 v2 的检查表(那版一次成功 76 行)。
#
# 登记纪律(三条, 违反即重新引入噪音或新的疑惑):
#   ① 改写 HEAD 的步骤**必须**登记, 且带 `旧hash→新hash` —— 相邻两步首尾同值 ⇒ 任何 hash 变化都可回溯;
#   ② 没发生的步骤**一律不登记**(齐平 / 闸门复跑无改动 = 静默), 输出"跑了但什么都没做"本身就是噪音;
#   ③ 登记(发生在动作内部, 按时间顺序)与打印(只在最终结果行之前, 由入口做)分离 ——
#      步骤行打在结果行**上面**, 结果行本身逐字不动(它才是要贴进回复 / 档案的那个值)。
#
# 传递方式: 显式列表 `steps`, 由入口持有(sync / commit / push 的 main), 逐层透传给内部动作。
#   不用模块级全局缓冲 —— 那样跨测试的残留会让断言互相污染。传 None = 调用方不要痕迹(现状行为)。


def step(steps: list[str] | None, text: str) -> None:
    """登记一行已发生的步骤; steps 为 None 时静默。"""
    if steps is not None:
        steps.append(text)


def emit_steps(steps: list[str]) -> None:
    """把登记的步骤行吐出并清空 —— 由入口在打结果行**之前**调用一次。"""
    while steps:
        print(steps.pop(0))


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
