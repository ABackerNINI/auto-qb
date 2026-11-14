"""提交流水线的**内部共享件** —— 闸门引擎 / 占位符展开 / 改动清单 / 配置体检。

v3 输出契约(计划 26-09-28-0157)「沉默即成功」: 本模块只提供机制, **不打印检查表** ——
常规路径成功即静默, 失败由调用方(sync / commit / push)给一行「原因 + 下一步」。
v3.1(2026-10-06)在本模块加了唯一的**输出机制**例外: 「步骤登记」段(`step` / `emit_steps`)——
结果行仍是上面那句话, 只是**真改写 HEAD 的步骤**由它登记成一行证据, 见该段注释。
2026-10-06 另加: **git 命令统一走 `run_git`** —— 单次 20s 超时 + 有界重试(默认 3 次, 全部失败才判失败),
动机(Gitee 间歇性卡住)与三档重试判据见「git 命令: 单次超时 + 有界重试」段。
2026-10-07 改: 上述"热刷新 / 重取"两条治标机制已**退役** —— 根治方案是**快照自举**(`_snapshot.py`):
入口把整包复制到**仓库之外**再从副本重入, **一次调用 = 一个版本**, 中途的自我改写对本进程不可见。
本模块只留 `pack_touched()` 回答"上游改没改本包"(供调用方提示重跑), 见「快照语义: 本包被上游改动」段。
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
from concurrent.futures import ThreadPoolExecutor
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
# ! Windows 上 `subprocess.run(capture_output=True)` 会**无限挂住**, 两种入口都实测到过
#   (2026-10-03 定位, 见 memory-bank/pitfalls/testing/parallel-run.md):
#   1. `_winapi.CreateProcess`(即 `Popen.__init__`)在大量 spawn / 高负载下不再返回
#      —— 本机 4 个 clone 同时跑测试时, 约第 800 次 spawn 起概率性永久阻塞;
#   2. `communicate()` 里 join 读线程: git 的**孙进程**继承了管道写端且不退出时, 读端永远
#      等不到 EOF —— 此时连 `subprocess.run(timeout=…)` 也救不了(timeout 只杀直接子进程,
#      `communicate()` 仍阻塞在 join)。
#   处置: 全程跑在**看门狗线程**里, 硬截止到点就 `taskkill /F /T` 整棵进程树 + 关掉我们这端
#   的管道(不 join), 然后返回一个可判定的失败 —— 让调用方**快速失败**而不是冻住整条 ship。
#   代价: 极少数卡死会泄漏一个幽灵线程(无法从外部杀), 相对于"提交无声中止"可接受。
# 单次 git 命令的超时(秒) —— 到点看门狗杀整棵进程树, 再由下面的重试层决定要不要再来一次。
# 2026-10-06 由 120s 收紧到 20s: Gitee **间歇性卡住**时 120s 只够等出一次失败(提交被拆成
# 「未推送 + 手工补推」两步), 20s + 重试才能在**同一条命令里**自愈。环境变量可覆盖。
GIT_TIMEOUT = float(os.environ.get("COMMAND_FLOW_GIT_TIMEOUT", "20"))

# ------------------------------------------------------------------ git 命令: 单次超时 + 有界重试
# 动机(2026-10-06 用户指出): Gitee 会间歇性卡住(不报错, 就是不返回) —— 旧行为要等满 120s 才被杀,
# 于是「提交成功(未推送)」+ 手工 `ship.push` 成了常态。修法两件: 1) 单次超时 20s;
# 2) 失败后**有界重试**, 全部尝试都失败才判失败(重试层对 push / pull / fetch 等所有 git 命令生效)。
#
# 为什么不是「任何非 0 都重试」: 有些调用的**非 0 是正常答案**(`cat-file -e` 判路径在不在 HEAD、
# `merge-tree` 判能否干净合流), 盲重试会把正常答案拖成 3 倍耗时; 而网络子命令的失败签名五花八门
# (网关 502 / 代理重置 / TLS 抖动), 靠签名白名单必然漏。所以分三档(判据单点: `_retryable`):
#   1. 网络子命令(推 / 拉 / 取) —— **失败即重试**: 签名靠不住, 而它们**幂等**(fetch / ls-remote 只读;
#      push 同 ref 重推是 no-op 或 "up-to-date") ⇒ 重试永远安全, 还能顺手救回「推成功但被判失败」。
#   2. 非幂等的本地写(commit / rebase / merge / reset …) —— **只给超时, 不给重试**:
#      超时被杀 ≠ 没执行完; 再跑一次轻则把 "nothing to commit" 当成失败, 重则 amend 又挪一次 hash
#      把步骤链写坏(v3.1 的 旧hash→新hash 就对不上了)。
#   3. 其余(只读查询 + 幂等写) —— 只在**可能自愈**的失败上重试: 超时(rc=-1)或命中瞬时签名。
GIT_ATTEMPTS = int(os.environ.get("COMMAND_FLOW_GIT_ATTEMPTS", "3"))
GIT_RETRY_BACKOFF = float(os.environ.get("COMMAND_FLOW_GIT_RETRY_BACKOFF", "1"))

NETWORK_SUBCOMMANDS = frozenset({"push", "fetch", "pull", "ls-remote", "clone", "remote"})
NON_IDEMPOTENT_SUBCOMMANDS = frozenset(
    {
        "commit", "rebase", "merge", "reset", "checkout", "switch", "restore", "rm", "mv", "am", "apply", "cherry-pick",
        "revert", "stash", "tag", "update-ref", "branch", "worktree", "clean"
    }
)
# 瞬时网络失败的已知签名 —— 只作第 3 档的补充判据(网络子命令不靠它, 见上)。
TRANSIENT_MARKS = (
    "Recv failure", "Connection was reset", "Could not resolve host", "Failed to connect", "Connection timed out",
    "Operation timed out", "The remote end hung up", "remote end hung up", "early EOF", "RPC failed",
    "unable to access", "unexpected disconnect", "Temporary failure", "SSL", "TLS", "timed out", "502", "503", "504"
)


def _kill_tree(pid: int) -> None:
    """Windows: 连孙子一起杀掉(`git push` 会派生 sh.exe → git-receive-pack → git)。"""
    try:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        pass


def run_capture(
    args,
    cwd=None,
    timeout: float = GIT_TIMEOUT,
    shell: bool = False,
    env: dict | None = None
) -> subprocess.CompletedProcess:
    """跑一条命令并抓输出, **保证不永久挂住**(见上面的根因注释)。

    返回 CompletedProcess; 超时/卡死时 rc 记 `-1`(与真实 git 码不冲突), 输出带一句原因。
    实现: 真正的 Popen + communicate 放在看门狗线程里, 主线程只等到 deadline;
    到点后杀掉**整棵进程树**并关掉我们的管道读端, 让读线程随之结束(不 join)。

    `shell=True` 供闸门(`run_gates`)这类**命令串**用 —— 与 git 的 argv 直调不同, 但同样
    走本看门狗(裸 subprocess.run 在 Windows 上同款挂死)。
    `env` 传 None = 继承当前进程环境; 传 dict = **整份替换**(调用方自己拼 `{**os.environ, …}`) ——
    供 `rebase --continue` 这类需要 `GIT_EDITOR=true` 的调用用。
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
                env=env,
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
                # ! 必须**真的收尸**: 只记下 pid 不杀, 子进程会继续活着占着 cwd 与管道
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


def _subcommand(args) -> str:
    """从 git argv 里取子命令 —— 跳过开头的可执行名与 `-c k=v` / 其余前缀旗标。

    ! 必须吃掉开头的 `git`: `run_git` 拿到的是**完整 argv**(首元素是可执行名), 不跳它就会永远
    把子命令读成 "git" ⇒ 三档判据全部失效 —— `push` 被当成本地只读命令, 非 0 不再重试,
    恰好把本功能**静默修没**(2026-10-06 实写时踩到, 由 GitRetryTest 的 push / commit 两条守住)。
    ! 可执行名先反斜杠归一成正斜杠再取 stem: Windows 全路径的可执行名在 POSIX 的 Path 语义里
    反斜杠不是分隔符, stem 恒为整串 ⇒ 判定随宿主 OS 摆动, Linux 宿主跳不掉可执行名、三档判据
    跟着全失效 —— 可执行名识别只认 argv 数据里的分隔符, 不绑宿主(包是跨项目资产, 两侧行为
    必须一致; 2026-11-14 issue 0912, 方案 B 生产归一化)。
    """
    tokens = list(args)
    if tokens and not tokens[0].startswith("-") and Path(tokens[0].replace("\\", "/")).stem.lower() == "git":
        tokens = tokens[1:]
    i = 0
    while i < len(tokens):
        a = tokens[i]
        if a == "-c":  # `-c key=value` 是**两个** argv 元素, 值不能被子命令判定吃到
            i += 2
            continue
        if a.startswith("-"):
            i += 1
            continue
        return a
    return ""


def _retryable(args, proc: subprocess.CompletedProcess) -> bool:
    """这次失败**重试有没有意义** —— 判据单点(三档理由见模块顶「git 命令: 单次超时 + 有界重试」段)。

    非 0 一律重试是错的: `cat-file -e` / `merge-tree` 这类**非 0 就是正常答案**, 盲重试既慢又把
    语义搅浑; 而网络子命令反过来 —— 失败签名靠不住, 只能按「失败即重试」兜(它们幂等, 重试安全)。
    """
    if proc.returncode == 0:
        return False
    sub = _subcommand(args)
    if sub in NETWORK_SUBCOMMANDS:
        return True
    if sub in NON_IDEMPOTENT_SUBCOMMANDS:
        return False
    if proc.returncode == -1:  # 看门狗杀树(超时 / 卡死) —— 只读命令重试一次大概率能过
        return True
    err = proc.stderr or ""
    return any(mark in err for mark in TRANSIENT_MARKS)


def retry_note(proc: subprocess.CompletedProcess) -> str:
    """失败行里的重试备注 —— 只有真重试过才出现(1 次尝试 = 没重试, 不啰嗦)。"""
    used = getattr(proc, "attempts_used", 1)
    return f"(已重试 {used - 1} 次)" if used > 1 else ""


def run_git(
    args,
    cwd=None,
    timeout: float = GIT_TIMEOUT,
    attempts: int = GIT_ATTEMPTS,
    shell: bool = False,
    env: dict | None = None
) -> subprocess.CompletedProcess:
    """跑一条 git 命令: **单次超时 + 有界重试**, 全部尝试都失败才把最后一次的结果交出去。

    `attempts` 是本层唯一的重试旋钮: 1 = 不重试(GitHub 镜像用 —— 允许滞后, 成败都不提),
    默认 3(含首次)。重试与否由 `_retryable` 判; 实际尝试次数挂在返回值的 `attempts_used` 上,
    调用方用 `retry_note(proc)` 在**失败行**里写明「已重试 N 次」; 成功则照旧沉默(v3 契约)。
    """
    cmd = args if shell else list(args)
    proc = run_capture(cmd, cwd=cwd, timeout=timeout, shell=shell, env=env)
    used = 1
    while used < attempts and _retryable(cmd, proc):
        time.sleep(GIT_RETRY_BACKOFF)
        proc = run_capture(cmd, cwd=cwd, timeout=timeout, shell=shell, env=env)
        used += 1
    proc.attempts_used = used  # 给 retry_note 用; CompletedProcess 是普通类, 挂属性安全
    return proc


def git(*args: str, check: bool = True, attempts: int = GIT_ATTEMPTS) -> str:
    # **不能整段 strip()**: `git status --porcelain` 的首列空格表示"无暂存改动",
    # 整段 strip 会把首行的这个空格吃掉 → ' M a/b' 变成 'M  a/b', 首列被误判成已暂存,
    # 且 line[3:] 丢掉路径首字符, 红线匹配会**静默放行**。
    proc = run_git(["git", *args], attempts=attempts)
    if check and proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} 失败{retry_note(proc)}: {proc.stderr.strip()}")
    return proc.stdout.rstrip("\n")


def git_rc(*args: str, attempts: int = GIT_ATTEMPTS) -> int:
    """只关心**退出码**的 git 调用(如 `merge-tree --write-tree`: 0 = 可干净合流, 非 0 = 有冲突)。"""
    return run_git(["git", *args], attempts=attempts).returncode


def git_run(*args: str, attempts: int = GIT_ATTEMPTS) -> subprocess.CompletedProcess:
    """要 rc + stderr 的 git 调用(merge --ff-only / rebase / push 的失败原因都在 stderr)。"""
    return run_git(["git", *args], attempts=attempts)


# ------------------------------------------------------------------ 快照语义: 本包被上游改动
# 快照自举(见 `_snapshot.py`)让**本进程**对"自己脚下的仓库被改写"免疫 —— 一次调用只认启动时那份副本,
# 中途 rebase 写进工作区的新版本对本进程不可见。但"上游改动了本包"这件事对用户是有价值的信号:
# 新版本要**重跑**才生效, 静默会让人以为已经用上了。这里只回答"改没改"(纯查询), 提示文案由调用方登记。
ORIG_PACK_ENV = "COMMAND_FLOW_ORIGINAL_PACK"  # 快照自举注入的原包路径(见 `_snapshot.py`)
PACK_REL_FALLBACK = ".commands/my-commit-flow"  # 本包不在仓库内(测试 / 手工跑)时的引擎约定位置


def pack_rel_path() -> str:
    """本包相对仓库根的路径(posix) —— 供 `git diff -- <path>` 判「上游是否改动了本包」。

    快照里 `COMMAND_FLOW_ORIGINAL_PACK` 指向**原包**(副本在仓库外); 不在快照里时退回脚本目录的上一级。
    两者都可能不在仓库内, 那时退回引擎约定位置(`.commands/<包>`)。
    """
    orig = os.environ.get(ORIG_PACK_ENV, "").strip()
    pack = Path(orig).resolve() if orig else Path(__file__).resolve().parent.parent
    try:
        return pack.relative_to(find_root()).as_posix()
    except ValueError:
        return PACK_REL_FALLBACK


def pack_touched(old_sha: str, new_sha: str) -> bool:
    """`old_sha` → `new_sha`(内部同步的 rebase)之间, 本包目录是否被改动过。

    只回答"改没改": 快照语义下本进程仍按启动版本运行, 改动**从下一次调用生效** —— 调用方据此登记
    一行提示, 而不是去追赶新版本(那正是撕裂的来源)。
    """
    if not old_sha or not new_sha or old_sha == new_sha:
        return False
    out = git("diff", "--name-only", old_sha, new_sha, "--", pack_rel_path(), check=False)
    return bool(out.strip())


def changed_files(with_safety: bool = False) -> tuple[list[str], list[str]]:
    """返回 (staged, unstaged) 文件清单(按 `git status --porcelain` 的两列判读)。

    `with_safety = True`: 每行末补一个状态字符(`S` = 「无参即真动作」的危险脚本, `.` = 其余),
    供 `<each:GLOB|--with-safety>` 的展开把危险脚本剔除 —— **闸门冒烟不做「只挑文件名」的静态
    规则**: 判据留在只有脚本自己知道的地方(见 `_is_parameterless_action` 所在的 gen 脚本)。

    ! 必须带 `-uall`: 默认模式下**未跟踪目录只报一条 `?? <dir>/`**, 于是 `<each:GLOB>` 之类
    按文件的展开**匹配不到新加的文件** —— 新增脚本拿不到冒烟, 且是静默的。

    ! `--with-safety` 必须走 `-z`(2026-10-03): 危险脚本的状态字符挂在**整段末尾**, 非 -z 形态
    下 rename 记录的 `old -> new` 里 new 之后才是它 —— 用普通行解析会把状态字符切成名单的一部分。
    """
    staged, unstaged = [], []
    # ! 必须关 quotepath(2026-09-29 实测): 默认 ON 时非 ASCII 文件名被八进制转义加引号
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
    """命中的闸门 —— 返回完整 dict(auto / timeout 在里头, 后面要靠它们决定"跑不跑")。

    ! `match` 里含空串 = **每次提交都命中**, 哪怕本次改动清单为空。`hit()` 靠 startswith 匹配,
    空清单上恒为 False —— 于是"每次提交跑"的闸门在**纯删除提交**上静默不跑(commit.py 传给它的
    `present` 只收工作区仍存在的路径): 删 500 行可零评审入库(2026-11-06 评审实测)。
    """
    return [g for g in gates if "" in g.get("match", []) or hit(files, g.get("match", []))]


# ------------------------------------------------------------------ 占位符展开

PLACEHOLDER_RE = re.compile(r"<[^<>]+>")
EACH_RE = re.compile(r"<each:([^<>|]+?)(?:\|(--[^<>]+))?>")
CHANGED_RE = re.compile(r"<changed:([^<>]+)>")
SKILL_RE = re.compile(r"<skill-dir:([^<>]+)>")


class ExpandError(RuntimeError):
    """占位符展开失败 —— 调用方必须转成失败, **不降级**成"打印给人"。"""


# ------------------------------------------------------------------ 命令行长度守卫
# `<changed:>` 展开后拼进**一条完整命令行**: run_gates 走 shell=True(cmd.exe), 单条上限 8191 字符。
# 仓库相对路径平均约 69 字符 ⇒ 100 个改动文件约 6856 字符, 大批量 KB 提交会被 cmd.exe **静默截断**
# 成半截命令(末尾路径丢掉, 且 rc 看着正常), 计划 26-11-09-0559 §02 洞 2。
# 处置: 超限**先分片**(仍走命令行, 把一条 run 拆成多条文件子集, 内容不丢不改), 分片仍不够才谈
# 清单文件 / 响应文件 —— 本轮不做响应文件(沙箱白名单有 YAPF 坑前例, 见该计划 §07 R3)。
CMD_LINE_LIMIT = 8191  # cmd.exe 单条上限(含命令本体)
CMD_LINE_BUDGET = 7000  # 分片预算: 给 `cmd /c` 前缀 + 路径前缀留约 1.2k 余量
PLACEHOLDER_RESERVE = 400  # 模板里还剩 `<root>` / `<skill-dir:...>` 时再留的余量(单个远小于它)


def _quote(path: str) -> str:
    return path if not re.search(r"\s", path) else f'"{path}"'


def _short(cmd: str, root) -> str:
    """命令里的仓库根绝对路径换成 `.` —— 失败明细里那段前缀是常量, 每次重复纯属占地方。

    两种分隔符都试: 展开出来的命令可能用 `/`(占位符来自配置)也可能用 `\\`(来自 git)。
    形态集合正反两向显式备齐 —— 单靠 `str(root)` 只有宿主原生那一种分隔符形态(Windows
    反斜杠 / POSIX 正斜杠), 换个宿主就漏换另一种; 备齐后两侧宿主都产两种形态、行为一致
    (包是跨项目资产, 语义不该绑宿主 OS; 2026-11-14 issue 0912, 方案 B 生产归一化)。
    """
    forms = {str(root), str(root).replace("\\", "/"), str(root).replace("/", "\\")}
    for form in sorted(forms, key=len, reverse=True):
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


def changed_for_expand(ctx: dict) -> list[str]:
    """`<changed:>` 的展开面 = 本批改动 + ctx["changed_extra"](复跑阶段远端合入的补集)。

    为什么要有这个键(计划 26-11-09-0559 §02 洞 1): 远端 rebase 合入的文件**不产生本地 diff**
    (HEAD 已经跟着往前走了), 纯增量闸门(`--files <changed:...>`)对这批文件形同虚设 ——
    「合流后第二轮闸门」扫不到它们, 而它恰恰是唯一能扫到的那一轮。

    扩面**只**喂 `<changed:>`: 不进 `<each:>`(冒烟只对本地改过的脚本有意义)、不进
    `gates_for` 的命中判定(命中仍按 present 算)、不进暂存清单 —— 三者读的都是 `ctx["changed"]`
    本身(计划 §07 R2: 扩面误伤命中 / 暂存语义)。去重保序: 已在基础清单里的路径不重复加。
    """
    extra = ctx.get("changed_extra") or []
    if not extra:
        return ctx["changed"]
    merged = list(ctx["changed"])
    seen = set(merged)
    for path in extra:
        if path not in seen:
            seen.add(path)
            merged.append(path)
    return merged


def _chunk_args(files: list[str], budget: int) -> list[str]:
    """把文件清单切成若干「空格分隔」段, 每段让整条命令落在字符预算内(顺序与内容逐字不变)。

    只给 `<changed:>` 用 —— 它是唯一随改动面**线性增长**的占位符(`<each:>` 是复制命令, 单条
    长度与文件数无关)。budget <= 0 时退化成"一个文件一段": 单条仍可能超上限, 由 expand_run
    末尾的硬守卫判 STOP(不截断、不降级)。

    只在闸门**允许分片**时调用(见 expand_run 的 `allow_shard` 判据): 聚合语义闸门
    (声明 `shard = false`)收到的是单条全量命令, 走不到这里。
    """
    chunks: list[str] = []
    cur: list[str] = []
    size = 0
    for path in files:
        piece = _quote(path)
        cost = len(piece) + (1 if cur else 0)
        if cur and size + cost > budget:
            chunks.append(" ".join(cur))
            cur, size = [], 0
            cost = len(piece)
        cur.append(piece)
        size += cost
    if cur:
        chunks.append(" ".join(cur))
    return chunks


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
        # 摘掉(不安全)判据: 1) 脚本自认「无参即真动作」, 或 2) 探针没跑通(rc != 0 —— 超时 /
        # 起不来 / 脚本报错)。只有「跑通且没自认危险」才留下冒烟。
        if proc.returncode != 0 or "action-without-args" in out:
            skipped.append(rel)
        else:
            safe.append(rel)
    return safe, skipped


def expand_run(cmd: str, ctx: dict, allow_shard: bool = True) -> tuple[list[str], str | None]:
    """展开一条 `run`, 返回 (命令列表, 跳过原因); 展开不了抛 `ExpandError`。

    顺序固定: `<each:>` → `<changed:>` → `<skill-dir:>` / `<root>` → **残留检查** / 长度守卫。
    残留检查是关键: 还剩下尖括号说明占位符名拼错或没被认出来 —— 那时必须停手,
    而不是把带尖括号的命令交给 shell(那会静默变成一条没人看得懂的失败命令)。

    `<changed:>` 展开后是一条命令, 所以文件多到超 `CMD_LINE_BUDGET` 时**分片**成多条
    (每条仍是同一条模板 + 文件子集, 顺序与内容不变); 分片后仍超 `CMD_LINE_LIMIT` → `ExpandError`
    (STOP, 不截断不降级)。`<each:>` 是复制命令, 单条长度与文件数无关, 不分片。

    **哪些闸门分片**(显式声明, 不按文件名猜 —— 改名即静默失效的规则不能用):
    - 默认 `allow_shard = True` = **逐文件检查类**闸门(`<changed:>` 只是把一组文件喂给同一次检查,
      拆开跑与合跑语义等价, 如 timekit / check_html / check_command_drift --files)。
    - 配置里标 `shard = false` = **聚合语义**闸门: 一次调用要看到**完整**文件集合才能判
      (如 `test.pkg.scoped -- <changed:.commands/**>` 要按全局包集合决定「≥2 包整跑」,
      拆片会逐片重算、语义失效且多片 pytest -n 8 同池并发)。这类闸门展开后超限**直接
      ExpandError STOP**, 不分片、不截断、不降级。
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
        files = match_changed(changed_for_expand(ctx), m.group(1))
        if not files:
            return [], f"无匹配文件: <changed:{m.group(1)}>"
        expanded: list[str] = []
        for c in cmds:
            # 预算按**这条模板**算: 模板去掉占位符后的长度 + 未展开占位符的余量, 剩下的全给清单。
            # 无匹配 / 单段放得下时 _chunk_args 只返回一段, 展开结果与旧实现逐字相同。
            fixed = c.replace(m.group(0), "")
            reserve = PLACEHOLDER_RESERVE if PLACEHOLDER_RE.search(fixed) else 0
            budget = max(CMD_LINE_BUDGET - len(fixed) - reserve, 0)
            chunks = _chunk_args(files, budget) if allow_shard else [" ".join(_quote(f) for f in files)]
            expanded.extend(c.replace(m.group(0), chunk) for chunk in chunks)
        cmds = expanded

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
    for c in resolved:
        # 分片后仍超上限 = 单条命令本身就装不下(cmd.exe 会静默截断尾部路径): 宁可 STOP。
        if len(c) > CMD_LINE_LIMIT:
            if allow_shard:
                raise ExpandError(f"展开后命令行 {len(c)} 字符, 超过单条上限 {CMD_LINE_LIMIT}"
                                  " —— 分片后仍超限: 缩小提交范围, 或把该 run 拆成多条闸门")
            raise ExpandError(
                f"展开后命令行 {len(c)} 字符, 超过单条上限 {CMD_LINE_LIMIT}"
                " —— 该闸门声明 shard = false(聚合语义, 要看到完整文件集合, 不可分片): "
                "缩小提交范围, 或用一条不依赖完整集合的逐文件检查替代"
            )
    return resolved, None


# ------------------------------------------------------------------ 闸门执行(沉默即成功)

# 并发池上限(2026-11-01 拍板 D2, 计划 26-11-01-0434): 展开后的闸门命令在此池内并发执行。
# 4 = 十连检 10 条竞争适度, 低配机 spawn 压力可控; pytest 类重型闸门本身单条, 若实测它与
# 并行小命令互相拖慢(计划 §07 R3), 处置 = 改这里降并发或给 pytest 类命令独占池。
GATE_WORKERS = 4


def run_gates(hits: list[dict], ctx: dict) -> tuple[list[tuple[str, str, int, float, str]], list[str], int]:
    """执行命中的 `auto = true` 闸门 —— **全过即静默**(v3 契约), 失败才说话。

    返回 (failures, manual, ran):
    - failures: [(gate note, 命令, rc, 耗时s, 失败输出末 20 行)] —— 调用方转成失败行;
      展开失败 rc 记 -2(不是 git 的码, 避免与真实 rc 混淆), 超时记 -1。
    - manual: 非自动闸门的展开命令(不执行; 调用方决定要不要提示 —— 本仓库配置里没有这类)。
    - ran: 真正执行过的命令条数。
    - `<each:>` / `<changed:>` 无匹配文件 → **按设计静默跳过**(它们只盯本次改动)。
    - `<changed:>` 长命令被分片时, 每条子命令是**独立 job**(同上限、同 timeout, 顺序为文件序):
      失败定位与取 failures[0] 的语义不变, 只是 ran 计的是分片条数。
      声明 `shard = false` 的聚合语义闸门**不分片**: 单条超限直接走展开失败(rc=-2 STOP),
      不会降级成"跑若干半截聚合检查"(语义在拆片时已经失真)。

    执行模型(2026-11-01, 计划 26-11-01-0434 方案 B): 两阶段 —— 先**串行展开**全部命中闸门
    (顺序 = 配置序; 冒烟摘除的 print 只发生在这里), 再把展开出的命令按提交序丢进线程池并发跑
    (`GATE_WORKERS`)。失败全量收集后**按提交序**排列(展开失败在前, 两者都确定), 调用方
    「取 failures[0]」的语义不变; run_capture 的看门狗/杀树/超时语义逐条原样沿用 —— 线程只
    等 subprocess, Windows 下安全。2026-11-01 前是双层串行 for(十连检 6.2s 全走墙钟)。
    """
    failures: list[tuple[str, str, int, float, str]] = []
    manual: list[str] = []
    jobs: list[tuple[str, str, int]] = []  # (note, 命令, timeout) —— 提交序 = 配置序
    for gate in hits:
        note = gate.get("note", "(无 note)")
        timeout = int(gate.get("timeout", 600))
        # shard 是**显式**分片开关(默认 True = 逐文件检查类); false = 聚合语义闸门,
        # `<changed:>` 保持单条, 超限即展开失败 STOP。判据写在 expand_run 的 docstring。
        allow_shard = bool(gate.get("shard", True))
        for cmd in gate.get("run", []):
            try:
                cmds, skip = expand_run(cmd, ctx, allow_shard=allow_shard)
            except ExpandError as exc:
                failures.append((note, cmd, -2, 0.0, str(exc)))
                continue
            if skip:
                continue
            if not gate.get("auto", False):
                manual.extend(cmds)
                continue
            for real in cmds:
                jobs.append((note, real, timeout))

    def _run(job: tuple[str, str, int]) -> tuple[int, float, str] | None:
        # 返回 None = 通过; (rc, secs, tail) = 失败。线程池内不许让异常逃走 —— 例外按
        # rc=-1 收成失败(与超时同码), 不中断其余命令的收集。
        _note, real, timeout = job
        t0 = time.monotonic()
        try:
            # 走 run_capture(shell 模式): 闸门命令串同样会撞 Windows 的 CreateProcess / 管道挂死,
            # 且闸门带超时语义 —— 看门狗到点杀**整棵进程树**, 比裸 subprocess.run(timeout=…)
            # 只杀直接子进程更彻底(根因见模块顶「子进程防挂死」段)。
            proc = run_capture(real, cwd=str(ctx["root"]), timeout=timeout, shell=True)
            rc = proc.returncode
            out = (proc.stdout or "") + (proc.stderr or "")
        except Exception as exc:  # noqa: BLE001 —— 兜底成失败, 闸门红比静默崩好
            rc, out = -1, f"执行异常: {exc}"
        secs = time.monotonic() - t0
        if rc == 0:
            return None
        lines = [l for l in out.splitlines() if l.strip()]
        return rc, secs, "\n".join(lines[-20:])

    ran = len(jobs)
    if jobs:
        with ThreadPoolExecutor(max_workers=min(GATE_WORKERS, len(jobs))) as pool:
            results = list(pool.map(_run, jobs))
    else:
        results = []
    for (note, real, _timeout), res in zip(jobs, results):
        if res is not None:
            rc, secs, tail = res
            failures.append((note, real, rc, secs, tail))
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
# ! 为什么要有它: 一次命令内部 HEAD 会被改写多次(提交 → 内部 rebase → 闸门改后 amend → 推送再同步),
#   而 v3 只吐终值那一个 hash —— 执行者看到 hash 与印象不符就跑去查原因(2026-10-06 用户指出)。
#   v3.1 的补法不是推翻它: **只补"真发生了"的步骤**, 绝不回到 v2 的检查表(那版一次成功 76 行)。
#
# 登记纪律(三条, 违反即重新引入噪音或新的疑惑):
#   1. 改写 HEAD 的步骤**必须**登记, 且带 `旧hash→新hash` —— 相邻两步首尾同值 ⇒ 任何 hash 变化都可回溯;
#   2. 没发生的步骤**一律不登记**(齐平 / 闸门复跑无改动 = 静默), 输出"跑了但什么都没做"本身就是噪音;
#   3. 登记(发生在动作内部, 按时间顺序)与打印(只在最终结果行之前, 由入口做)分离 ——
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
