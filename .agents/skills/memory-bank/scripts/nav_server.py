"""nav 导航页服务层 (纯 stdlib http.server, 零新依赖; 服务模式零落盘)。

路由 (计划 26-10-04-0952 §03):
    GET /                    页面壳 (同目录 nav_page.html, S2 交付; 缺失返回 503 提示, 不抛 traceback)
    GET /api/data            每请求现算 nav_data.collect_nav(), JSON 直返 (前端 30s 轮询此端点)
    GET /memory-bank/<path>  静态映射四工位原文, 供「打开原文」; resolve 后必须仍落在 memory-bank/
                             内, 越界一律 403 (URL 先解码再判, ../ 与 %2e%2e / ..%2f / 反斜杠等
                             变体全部拦截, 测试钉死)
    POST /api/pull           仅快进同步本仓库 (前端顶栏「拉取」按钮): ls-remote 取远端真值 → fetch →
                             merge --ff-only; 不能快进 (分叉 / 本地改动重叠 / 离线) 一律失败并回一行
                             原因, 绝不 rebase / 绝不生成 merge commit。必须带 X-Nav-Action 头 ——
                             CSRF 护栏: 跨站 fetch 带自定义头会先发 OPTIONS 预检, 本服务不答 (501)
                             → 浏览器拦下; 同源页面不受影响。
                             网络容错 (2026-11-11): _git 层单次超时 + 有界重试 (默认 3 次, 判据同
                             .commands/my-commit-flow/_pipeline.py 三档) —— Gitee 间歇抖动时
                             「拉取」在同一个 POST 里自愈, 全部尝试失败才回失败行 (带「已重试 N 次」)。

用法 (从仓库根):
    python .agents/skills/memory-bank/scripts/nav_server.py                    起服务 (绑 127.0.0.1:8765,
                                                                               浏览器开 localhost:8765;
                                                                               启动后自动开浏览器, --no-open 关)
    python .agents/skills/memory-bank/scripts/nav_server.py --port 9000        换端口 (被占用时
                                                                               报错行内提示 --port)
    python .agents/skills/memory-bank/scripts/nav_server.py --gen-static [DIR] 不起服务: 壳+注入
                                                                               数据落盘单文件
                                                                               (默认 tmp-analysis/nav/,
                                                                               已 gitignored; 静态件内
                                                                               memory-bank 链接用相对
                                                                               前缀 ../../memory-bank/)

CLI 入口沿用同目录 gen_doc_map 的 _utf8_stdout() Windows 编码兜底。allow_reuse_address 必须关:
Windows 上 SO_REUSEADDR 会让同端口双绑静默成功, 「端口被占」检测就失效了。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import find_root, resolve_mb_dir  # noqa: E402
import nav_data  # noqa: E402

SHELL_NAME = "nav_page.html"
# 关系图组件 (2026-11-07 拆分): 独立文件, 服务模式按路由发货, --gen-static 时**内联**回壳里 ——
# 静态导出件必须仍是单文件 (file:// 打开时同目录没有 .js 可拉)。
GRAPH_NAME = "nav_graph.js"
GRAPH_TAG = '<script src="%s"></script>' % GRAPH_NAME
BIND_HOST = "127.0.0.1"  # 监听只绑回环 (sidefx 放行), 不对外暴露
OPEN_HOST = "localhost"  # 浏览器打开的地址一律用 localhost: 127.0.0.1 这个 origin 有历史遗留
# (旧缓存 / 残留服务), 换成 localhost 拿一个干净 origin
DEFAULT_STATIC_DIR = "tmp-analysis/nav"  # 相对仓库根; 目录已 gitignored, 静态导出件不入库
STATIC_LINK_PREFIX = "../../memory-bank/"  # 静态件指向 memory-bank 原文的相对链接前缀 (壳按 file: 协议取用)
# 壳里该前缀写成带引号的 JS 字符串字面量; gen_static 按**实际输出目录深度**换掉它 ——
# 写死时只有输出到仓库根下两级 (默认 tmp-analysis/nav/) 才对, --gen-static out/ 会让链接全部算到仓库外。
STATIC_LINK_JS = '"%s"' % STATIC_LINK_PREFIX
DATA_TOKEN = "__DATA__"  # 壳内数据注入位 (S2 的壳以同款 token 预留)

# ---- 仅快进拉取 (前端顶栏「拉取」按钮 → POST /api/pull) ----
PULL_PATH = "/api/pull"
PULL_HEADER = "X-Nav-Action"  # CSRF 护栏: 跨站 fetch 带自定义头会先发 OPTIONS 预检, 本服务不答
PULL_HEADER_VALUE = "pull"
# 主线远端候选与顺序: 与 .commands/my-commit-flow 的 main_candidates 同序 (Gitee 优先, 历史 clone 的
# origin 可能是 GitHub 镜像)。判据纪律同 sync.py —— 只认 ls-remote 现查的远端真值, 不读 refs/remotes
# (本环境该 ref 的写入会被静默丢弃, 见 pitfalls/git/refs.md)。
MAIN_REMOTE_CANDIDATES = ("gitee", "origin", "github")
# 单条 git 命令超时(秒) + 有界重试: 口径整体移植自 .commands/my-commit-flow/scripts/_pipeline.py
# (2026-11-11, 用户报「Gitee 经常抖动, 首次 pull 失败」)。单次超时收紧 60→20s 的理由同源:
# Gitee 间歇性卡住时 60s 只够等出一次失败, 20s + 重试才能在同一个 POST 里自愈 (最坏
# 3 次×20s + 退避 ≈ 63s 仍有界, 不至于挂死服务线程 —— 离线 / 凭据弹窗的初衷不变)。
GIT_TIMEOUT = 20
GIT_ATTEMPTS = 3  # 含首次; 重试与否由 _retryable 判, 全部失败才把最后一次结果交出去
GIT_RETRY_BACKOFF = 1.0  # 重试间隔(秒)
_PULL_LOCK = threading.Lock()  # 串行化并发拉取 (ThreadingHTTPServer 每请求一线程)

# 三档重试判据 (与 _pipeline.py 同一份理由, 单点复制不 import —— commands 包是 .commands 私产,
# memory-bank skill 只依赖 stdlib + 本目录):
#   1. 网络子命令(拉 / 取) —— 失败即重试: 失败签名五花八门(网关 502 / 代理重置 / TLS 抖动),
#      靠白名单必然漏; 除 pull 外都幂等(只读), 重试安全。集合与 _pipeline 保持同源(含 pull ——
#      它其实非幂等, 但本服务从不调用 git pull, 留在集合里只是同源的代价)。
#   2. 非幂等的本地写(merge / reset …) —— 只给超时, 不给重试: 超时被杀 ≠ 没执行完, 再跑一次
#      轻则把正常答案当失败, 重则把工作区搅乱。
#   3. 其余(只读查询) —— 只在可能自愈的失败上重试: 超时(rc=-1)或命中瞬时签名。
NETWORK_SUBCOMMANDS = frozenset({"push", "fetch", "pull", "ls-remote", "clone", "remote"})
NON_IDEMPOTENT_SUBCOMMANDS = frozenset(
    {
        "commit",
        "rebase",
        "merge",
        "reset",
        "checkout",
        "switch",
        "restore",
        "rm",
        "mv",
        "am",
        "apply",
        "cherry-pick",
        "revert",
        "stash",
        "tag",
        "update-ref",
        "branch",
        "worktree",
        "clean",
    }
)
TRANSIENT_MARKS = (
    "Recv failure",
    "Connection was reset",
    "Could not resolve host",
    "Failed to connect",
    "Connection timed out",
    "Operation timed out",
    "The remote end hung up",
    "remote end hung up",
    "early EOF",
    "RPC failed",
    "unable to access",
    "unexpected disconnect",
    "Temporary failure",
    "SSL",
    "TLS",
    "timed out",
    "502",
    "503",
    "504",
)

# 壳缺失时的占位模板 (仅 --gen-static 自验管线用): dark 主题, 注入数据并回显计数, 不冒充正式壳。
_PLACEHOLDER_SHELL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>kb nav - placeholder shell (S2 pending)</title>
<style>
  :root { color-scheme: dark; }
  body { background: #0e1114; color: #dde3e8; font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
         margin: 0; padding: 48px; line-height: 1.7; }
  code, .mono { font-family: Consolas, monospace; color: #86d7e0; }
  .dim { color: #9aa4ad; }
</style>
</head>
<body>
<h1>kb nav placeholder shell</h1>
<p>正式页面壳 nav_page.html 由 S2 阶段交付; 本文件只是 --gen-static 管线的自验产物, 勿当正式页使用。</p>
<p class="mono">stamp <span id="stamp"></span> | <span id="n"></span> items | <span id="t"></span> topics</p>
<p class="dim">memory-bank link prefix: <code>../../memory-bank/</code></p>
<script>
const DATA = __DATA__;
document.getElementById("stamp").textContent = DATA.stamp || "(empty)";
document.getElementById("n").textContent = DATA.items.length;
document.getElementById("t").textContent = DATA.topics.length;
</script>
</body>
</html>
"""

# 扩展名 -> Content-Type (四工位制品以 .html / .md 为主, .md 给 text/plain 让浏览器直接显示原文)
_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".htm": "text/html; charset=utf-8",
    ".md": "text/plain; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".svg": "image/svg+xml",
}


def _utf8_stdout() -> None:
    """Windows 控制台可能是 GBK, 打中文/符号会崩 —— CLI 入口统一 UTF-8 兜底 (同 gen_doc_map)。

    line_buffering: stdout 被管道接住(AI 工具捕获)时默认是块缓冲, 启动行会滞留到进程退出才可见 ——
    常驻服务必须逐行可见, 强制行缓冲 (真终端 isatty 本来就是行缓冲, 不受影响)。
    """
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)


class NavServer(ThreadingHTTPServer):
    allow_reuse_address = False  # Windows 上 REUSEADDR 会让同端口双绑静默成功, 占用检测失效
    daemon_threads = True


# --------------------------------------------------------------------------- 仅快进拉取
def _subcommand(args: tuple[str, ...]) -> str:
    """从 git argv 里取子命令 —— 跳过 `-c k=v` 与其余前缀旗标 (判据按子命令分档, 吃不掉就会判错)。

    与 _pipeline 原版的差异: 本版 `_git` 收到的 args 首元素即子命令 (可执行名在 _git_once 才拼上),
    无需再吃开头的 `git`; 原版吃它是因为 `run_git` 拿的是完整 argv。
    """
    tokens = list(args)
    i = 0
    while i < len(tokens):
        a = tokens[i]
        if a == "-c":  # `-c key=value` 是两个 argv 元素, 值不能被吃到
            i += 2
            continue
        if a.startswith("-"):
            i += 1
            continue
        return a
    return ""


def _retryable(args: tuple[str, ...], proc: subprocess.CompletedProcess) -> bool:
    """这次失败重试有没有意义 —— 三档判据 (理由见 NETWORK_SUBCOMMANDS 上方注释, 单点同 _pipeline)。"""
    if proc.returncode == 0:
        return False
    sub = _subcommand(args)
    if sub in NETWORK_SUBCOMMANDS:
        return True
    if sub in NON_IDEMPOTENT_SUBCOMMANDS:
        return False
    if proc.returncode == -1:  # 超时 / 起不来 —— 只读命令重试一次大概率能过
        return True
    err = proc.stderr or ""
    return any(mark in err for mark in TRANSIENT_MARKS)


def retry_note(proc: subprocess.CompletedProcess) -> str:
    """失败行里的重试备注 —— 只有真重试过才出现 (1 次尝试 = 没重试, 不啰嗦; 同 _pipeline)。"""
    used = getattr(proc, "attempts_used", 1)
    return "(已重试 %d 次)" % (used - 1) if used > 1 else ""


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    """在 root 下跑一条 git: 单次超时 + 有界重试, 全部尝试失败才交最后一次的结果。

    超时 / 起不来统一以 rc!=0 表达 (不抛) —— 调用方一律按 rc 判, 失败原因取 stderr 末行
    (要向人交代重试过, 用 retry_note(proc))。`errors="replace"` 兜住 Windows 下非 UTF-8 输出。
    重试与否由 _retryable 判 (三档); 实际尝试次数挂在返回值的 attempts_used 上。
    """
    proc = _git_once(root, *args)
    used = 1
    while used < GIT_ATTEMPTS and _retryable(args, proc):
        time.sleep(GIT_RETRY_BACKOFF)
        proc = _git_once(root, *args)
        used += 1
    proc.attempts_used = used  # CompletedProcess 是普通类, 挂属性安全 (同 _pipeline)
    return proc


def _kill_tree(pid: int) -> None:
    """Windows: 连孙子一起杀掉 (git fetch/ls-remote 会派生 git-remote-https 等, 继承管道句柄)。

    仅定点杀本服务自己拉起的 git 进程树 (脚本内部定点杀, 同 _pipeline._kill_tree)。
    """
    try:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        pass


def _git_once(root: Path, *args: str) -> subprocess.CompletedProcess:
    """单次尝试: Popen + 看门狗线程, 超时杀整棵进程树, 统一以 rc=-1 表达 (同 _pipeline.run_capture)。

    ! 不能用裸 subprocess.run(timeout=...): Windows 上它只 kill git.exe 直属进程, 派生的
    git-remote-https 等孙进程继承管道句柄继续活着, 随后 run 内部无超时的 communicate() 会
    阻塞到管道写端全部关闭 —— 卡在 Gitee 的 TCP 读上(正是本功能的动机场景)就是永久挂住,
    且请求线程还持着 _PULL_LOCK, 之后所有拉取全部阻塞 (_pipeline 2026-10-03 实测同款挂死)。
    """
    box: dict = {}

    def _worker() -> None:
        proc = None
        try:
            proc = subprocess.Popen(
                ["git", *args],
                cwd=str(root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,  # 凭据提示场景读 stdin 得 EOF 立即失败, 不白等超时
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            box["pid"] = proc.pid
            out, err = proc.communicate(timeout=GIT_TIMEOUT)
            box["rc"], box["out"], box["err"] = proc.returncode, out, err
        except subprocess.TimeoutExpired:
            box["rc"], box["err"] = -1, "git 超时 %ds (进程树已杀)" % GIT_TIMEOUT
            if proc is not None:
                box["pid"] = proc.pid
                # ! 必须真的收尸: 只记 pid 不杀, 孙进程会继续活着占着管道 (同 _pipeline 注释)
                _kill_tree(proc.pid)
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass
        except OSError as exc:
            box["rc"], box["err"] = -1, "git 起不来: %s" % exc

    worker = threading.Thread(target=_worker, daemon=True)
    worker.start()
    worker.join(GIT_TIMEOUT + 15)  # 给 communicate 一点余量; 再卡死就弃线程 (幽灵线程可接受, 同 _pipeline)
    if worker.is_alive():
        pid = box.get("pid")
        if pid:
            _kill_tree(int(pid))
        return subprocess.CompletedProcess(args, -1, "", "git 卡死 (>%ds, 进程树已杀)" % GIT_TIMEOUT)
    return subprocess.CompletedProcess(args, box.get("rc", -1), box.get("out", "") or "", box.get("err", "") or "")


def _out(proc: subprocess.CompletedProcess) -> str:
    """git 成功输出的 strip 版 (调用方只在 rc==0 时消费)。"""
    return (proc.stdout or "").strip()


def _last_line(text: str) -> str:
    """失败原因: stderr 末条非空行 (git 的 hint 行也在, 取末行通常是最具体的那句)。"""
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    return lines[-1] if lines else "git 非 0"


def classify_pull(head: str, rsha: str, behind: int, ahead: int) -> str:
    """仅快进同步的分类 (纯逻辑, 无 git 副作用) —— 返回 up-to-date / ahead-only / fast-forward / diverged。

    behind / ahead = `git rev-list --left-right --count <rsha>...HEAD` 的左右计数
    (远端落后本地数 / 本地领先远端数)。仅快进口径: 只有 ahead==0 且 behind>0 才允许 merge --ff-only;
    两端都有(diverged)一律失败 —— 不 rebase / 不生成 merge commit, 交人处理。
    """
    if head == rsha:
        return "up-to-date"
    if behind == 0:
        return "ahead-only"
    if ahead == 0:
        return "fast-forward"
    return "diverged"


def pick_remote(root: Path) -> str:
    """主线远端名: 按 MAIN_REMOTE_CANDIDATES 顺序取第一个存在的 (都没有则退第一个, 无远端则空串)。"""
    names = [line.strip() for line in _out(_git(root, "remote")).splitlines() if line.strip()]
    for cand in MAIN_REMOTE_CANDIDATES:
        if cand in names:
            return cand
    return names[0] if names else ""


def pull_ff_only(root: Path) -> tuple[bool, str]:
    """仅快进把当前 clone 同步到主线远端; 返回 (ok, 一行结果)。

    步骤与 sync.py 同源: fetch(把对象拉进对象库) → ls-remote 取远端真值 → rev-list 算领先/落后 →
    可快进才 merge --ff-only。任何不能快进的情形都返回 ok=False + 一行原因, 不改动工作区 / 历史。
    """
    if _out(_git(root, "rev-parse", "--is-inside-work-tree")) != "true":
        return False, "不在 git 工作树里 —— 本目录不是仓库"
    remote = pick_remote(root)
    if not remote:
        return False, "找不到远端 —— git remote -v 核对"
    branch = _out(_git(root, "rev-parse", "--abbrev-ref", "HEAD"))
    if not branch or branch == "HEAD":
        return False, "当前处于游离 HEAD —— 无法确定要同步的分支"
    _git(root, "fetch", remote, branch)  # 只为把远端 tip 的对象拉进对象库; 成败不判(离线时 ls-remote 也为空)
    ls_proc = _git(root, "ls-remote", remote, branch)
    rsha = ""
    for line in _out(ls_proc).splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1] == "refs/heads/" + branch:
            rsha = parts[0]
            break
    if not rsha:
        return False, ("拿不到远端 %s/%s (离线?)%s —— 联网后重试" % (remote, branch, retry_note(ls_proc)))
    head = _out(_git(root, "rev-parse", "HEAD"))
    if not head:
        return False, "本地没有任何提交 (空仓库)"
    raw = _out(_git(root, "rev-list", "--left-right", "--count", "%s...HEAD" % rsha))
    try:
        behind, ahead = (int(x) for x in raw.split())
    except ValueError:
        return False, "算不出领先 / 落后 (fetch 未落稳?) —— 重试"
    kind = classify_pull(head, rsha, behind, ahead)
    if kind == "up-to-date":
        return True, "已是最新 %s" % head[:8]
    if kind == "ahead-only":
        return True, "本地领先远端 %d 个提交, 无需拉取" % ahead
    if kind == "diverged":
        return False, ("本地已分叉 (领先 %d / 落后 %d) —— 仅快进不自动 rebase / merge; "
                       "需人工合流后重试" % (ahead, behind))
    proc = _git(root, "merge", "--ff-only", rsha)
    if proc.returncode != 0:
        return False, ("快进被拒 —— %s%s; 本地改动可能与远端新提交重叠, 先提交或移出后重试" % (_last_line(proc.stderr), retry_note(proc)))
    return True, "已快进到 %s" % _out(_git(root, "rev-parse", "HEAD"))[:8]


class NavHandler(BaseHTTPRequestHandler):
    """路由处理器; mb / shell_path / root 由 _build_handler 在子类上注入。"""

    mb: Path
    shell_path: Path
    root: Path

    def log_message(self, fmt: str, *args) -> None:  # noqa: A002
        sys.stderr.write("[nav] %s - %s\n" % (self.address_string(), fmt % args))

    def log_request(self, code: object = "-", size: object = "-") -> None:  # noqa: N802
        # 精简 log: /api/data 是页面 30s 轮询、/ 是壳加载 —— 成功时不上屏; 只留错误与其余请求。
        path = self.requestline.split(" ")[1] if self.requestline else ""
        status = code if isinstance(code, int) else 200
        if status < 400 and (path == "/api/data" or path in ("/", "/index.html", "/" + GRAPH_NAME)):
            return
        sys.stderr.write("[nav] %s %s\n" % (status, self.requestline))

    def do_GET(self) -> None:  # noqa: N802
        path = urlsplit(self.path).path
        if path in ("/", "/index.html"):
            self._send_shell()
        elif path == "/" + GRAPH_NAME:
            self._send_graph()
        elif path == "/api/data":
            self._send_api()
        elif path == "/memory-bank" or path.startswith("/memory-bank/"):
            self._send_mb_file(path)
        else:
            self._send_text(404, "not found: %s" % path)

    def do_POST(self) -> None:  # noqa: N802
        path = urlsplit(self.path).path
        if path == PULL_PATH:
            self._handle_pull()
        else:
            self._send_text(404, "not found: %s" % path)

    def _handle_pull(self) -> None:
        """仅快进同步本仓库。CSRF 护栏 (两道): 必须带 X-Nav-Action 头 (跨站 fetch 带自定义头会先发
        OPTIONS 预检, 本服务不实现 do_OPTIONS → 501 → 浏览器拦下); Origin 若存在则必须同源回环。
        动作失败 (分叉 / 重叠 / 离线) 仍回 200 + {ok:false, message} —— 那是业务结果不是 HTTP 错误。"""
        if self.headers.get(PULL_HEADER) != PULL_HEADER_VALUE:
            self._send_text(403, "forbidden: missing %s header" % PULL_HEADER)
            return
        origin = self.headers.get("Origin")
        if origin:
            try:
                host = urlsplit(origin).hostname
            except ValueError:
                host = None
            if host not in ("localhost", "127.0.0.1"):
                self._send_text(403, "forbidden: cross-origin")
                return
        length = int(self.headers.get("Content-Length") or 0)
        if length:  # 消费请求体, 免得连接上残留字节
            self.rfile.read(length)
        with _PULL_LOCK:
            ok, message = pull_ff_only(self.root)
        self._send_json(200, {"ok": ok, "message": message})

    def _send_bytes(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, code: int, text: str) -> None:
        self._send_bytes(code, text.encode("utf-8"), "text/plain; charset=utf-8")

    def _send_json(self, code: int, obj: dict) -> None:
        self._send_bytes(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def _send_shell(self) -> None:
        try:
            body = self.shell_path.read_text(encoding="utf-8")
        except OSError:
            self._send_text(
                503, "nav_page.html not found (S2 pending): no shell to serve; "
                "use --gen-static for a placeholder snapshot or wait for S2."
            )
            return
        self._send_bytes(200, body.encode("utf-8"), "text/html; charset=utf-8")

    def _send_graph(self) -> None:
        """关系图组件 (壳里以 `<script src="nav_graph.js">` 引用; 静态导出时这个引用被内联替换)。"""
        try:
            body = (self.shell_path.parent / GRAPH_NAME).read_bytes()
        except OSError:
            self._send_text(404, "not found: %s" % GRAPH_NAME)
            return
        self._send_bytes(200, body, _CONTENT_TYPES[".js"])

    def _send_api(self) -> None:
        try:
            data = nav_data.collect_nav(self.mb)
        except OSError as exc:
            self._send_text(500, "collect_nav failed: %s" % exc)
            return
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self._send_bytes(200, body, "application/json; charset=utf-8")

    def _send_mb_file(self, raw: str) -> None:
        """静态映射四工位原文。防穿越: URL 解码后再 resolve, 落点必须严格在 memory-bank/ 内。"""
        rel = unquote(raw[len("/memory-bank/"):]) if raw.startswith("/memory-bank/") else ""
        if not rel:
            self._send_text(404, "not found: /memory-bank itself maps no file")
            return
        if "\x00" in rel:
            self._send_text(403, "forbidden")
            return
        try:
            cand = (self.mb / rel).resolve()
            mb_real = self.mb.resolve()
        except (OSError, ValueError):
            self._send_text(403, "forbidden: unresolvable path")
            return
        if cand != mb_real and mb_real not in cand.parents:
            self._send_text(403, "forbidden: path escapes memory-bank/")
            return
        if not cand.is_file():
            self._send_text(404, "not found: %s" % rel)
            return
        ctype = _CONTENT_TYPES.get(cand.suffix.lower(), "application/octet-stream")
        self._send_bytes(200, cand.read_bytes(), ctype)


def _build_handler(mb: Path, shell_path: Path, root: Path) -> type[NavHandler]:
    return type("BoundNavHandler", (NavHandler, ), {"mb": mb, "shell_path": shell_path, "root": root})


def _read_shell(shell_path: Path) -> tuple[str, bool]:
    """读页面壳; 缺失时退占位模板 (仅静态导出用, 服务模式走 503)。返回 (壳文本, 是否正式壳)。"""
    try:
        return shell_path.read_text(encoding="utf-8"), True
    except OSError:
        return _PLACEHOLDER_SHELL, False


def gen_static(mb: Path, shell_path: Path, out_dir: Path) -> int:
    """壳 + 注入数据落盘单文件 (不开服务)。

    两处按实际落点改写, 写死任何一处都会让静态件在非默认目录下全体失效:
    1. 数据 token -> 现算 JSON;
    2. `../../memory-bank/` -> 按 out_dir 与 mb 的相对关系现算的前缀 (默认目录恰好两级深才对);
    3. `<script src="nav_graph.js">` -> 该文件的**内联内容** (静态件必须单文件, file:// 拉不到同级 js)。
    """
    html, is_real = _read_shell(shell_path)
    payload = json.dumps(nav_data.collect_nav(mb), ensure_ascii=False)
    if DATA_TOKEN not in html:
        sys.stderr.write("[nav] shell has no %s token, data not injected\n" % DATA_TOKEN)
        return 1
    html = html.replace(DATA_TOKEN, payload)

    graph_path = shell_path.parent / GRAPH_NAME
    try:
        graph = graph_path.read_text(encoding="utf-8")
    except OSError:
        graph = ""
    if GRAPH_TAG in html and graph:
        html = html.replace(GRAPH_TAG, "<script>\n%s\n</script>" % graph)
    elif GRAPH_TAG in html:
        sys.stderr.write("[nav] %s missing next to shell, graph component not inlined\n" % GRAPH_NAME)

    try:
        prefix = os.path.relpath(mb, out_dir).replace(os.sep, "/").rstrip("/") + "/"
    except ValueError:
        # Windows 跨盘 (D: 盘导出到 C: 盘仓库): 相对路径算不出来 —— 退绝对 file:// 前缀, 链接仍然能开
        prefix = mb.resolve().as_uri().rstrip("/") + "/"
    if STATIC_LINK_JS in html:
        html = html.replace(STATIC_LINK_JS, json.dumps(prefix))

    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "nav_page.html"
    out.write_text(html, encoding="utf-8")
    kind = "shell" if is_real else "placeholder shell (nav_page.html pending, S2)"
    print("[nav] static export: %s (%d bytes, %s, link prefix %s)" % (out, out.stat().st_size, kind, prefix))
    return 0


def serve(mb: Path, shell_path: Path, root: Path, port: int, open_browser: bool = True) -> int:
    try:
        server = NavServer((BIND_HOST, port), _build_handler(mb, shell_path, root))
    except OSError as exc:
        sys.stderr.write(
            "[nav] bind %s:%d failed (%s): port likely in use, retry with --port <other>\n" % (BIND_HOST, port, exc)
        )
        return 1
    url = "http://%s:%d" % (OPEN_HOST, port)
    print("[nav] serving %s  (memory-bank: %s)" % (url, mb))
    if open_browser:
        webbrowser.open(url)
    print("[nav] Ctrl-C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    print("[nav] stopped")
    return 0


def main() -> int:
    _utf8_stdout()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=8765, help="服务端口 (默认 8765; 被占用换此参数)")
    parser.add_argument("--no-open", action="store_true", help="不起浏览器 (默认启动后自动打开页面)")
    parser.add_argument(
        "--gen-static",
        nargs="?",
        const=DEFAULT_STATIC_DIR,
        default=None,
        metavar="DIR",
        help="不起服务: 壳+注入数据落盘 DIR 单文件 (默认 %s, 已 gitignored)" % DEFAULT_STATIC_DIR
    )
    parser.add_argument("--root", help="仓库根 (默认向上找 .git)")
    parser.add_argument("--mb-dir", help="memory-bank 目录 (默认 <root>/memory-bank)")
    args = parser.parse_args()

    root = Path(args.root).resolve() if args.root else find_root()
    mb = resolve_mb_dir(root, args.mb_dir)
    if not mb.is_dir():
        sys.stderr.write("[nav] memory-bank dir not found: %s\n" % mb)
        return 1
    shell_path = Path(__file__).resolve().parent / SHELL_NAME

    if args.gen_static is not None:
        out_dir = Path(args.gen_static)
        return gen_static(mb, shell_path, out_dir if out_dir.is_absolute() else root / out_dir)
    return serve(mb, shell_path, root, args.port, open_browser=not args.no_open)


if __name__ == "__main__":
    raise SystemExit(main())
