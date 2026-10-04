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
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import find_root, resolve_mb_dir  # noqa: E402
import nav_data  # noqa: E402

SHELL_NAME = "nav_page.html"
BIND_HOST = "127.0.0.1"  # 监听只绑回环 (sidefx 放行), 不对外暴露
OPEN_HOST = "localhost"  # 浏览器打开的地址一律用 localhost: 127.0.0.1 这个 origin 有历史遗留
# (旧缓存 / 残留服务), 换成 localhost 拿一个干净 origin
DEFAULT_STATIC_DIR = "tmp-analysis/nav"  # 相对仓库根; 目录已 gitignored, 静态导出件不入库
STATIC_LINK_PREFIX = "../../memory-bank/"  # 静态件指向 memory-bank 原文的相对链接前缀 (壳按 file: 协议取用)
DATA_TOKEN = "__DATA__"  # 壳内数据注入位 (S2 的壳以同款 token 预留)

# ---- 仅快进拉取 (前端顶栏「拉取」按钮 → POST /api/pull) ----
PULL_PATH = "/api/pull"
PULL_HEADER = "X-Nav-Action"  # CSRF 护栏: 跨站 fetch 带自定义头会先发 OPTIONS 预检, 本服务不答
PULL_HEADER_VALUE = "pull"
# 主线远端候选与顺序: 与 .commands/my-commit-flow 的 main_candidates 同序 (Gitee 优先, 历史 clone 的
# origin 可能是 GitHub 镜像)。判据纪律同 sync.py —— 只认 ls-remote 现查的远端真值, 不读 refs/remotes
# (本环境该 ref 的写入会被静默丢弃, 见 pitfalls/git/refs.md)。
MAIN_REMOTE_CANDIDATES = ("gitee", "origin", "github")
GIT_TIMEOUT = 60  # 单条 git 命令超时(秒): 离线 / 凭据弹窗时不至于挂死服务线程
_PULL_LOCK = threading.Lock()  # 串行化并发拉取 (ThreadingHTTPServer 每请求一线程)

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
def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    """在 root 下跑一条 git。超时 / 起不来统一以 rc!=0 表达 (不抛) —— 调用方一律按 rc 判,
    失败原因取 stderr 末行。`errors="replace"` 兜住 Windows 下非 UTF-8 输出。"""
    try:
        return subprocess.run(
            ["git", *args],
            cwd=str(root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=GIT_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(args, 1, "", "git 起不来 / 超时: %s" % exc)


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
    rsha = ""
    for line in _out(_git(root, "ls-remote", remote, branch)).splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1] == "refs/heads/" + branch:
            rsha = parts[0]
            break
    if not rsha:
        return False, "拿不到远端 %s/%s (离线?) —— 联网后重试" % (remote, branch)
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
        return False, ("快进被拒 —— %s; 本地改动可能与远端新提交重叠, 先提交或移出后重试" % _last_line(proc.stderr))
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
        if status < 400 and (path == "/api/data" or path in ("/", "/index.html")):
            return
        sys.stderr.write("[nav] %s %s\n" % (status, self.requestline))

    def do_GET(self) -> None:  # noqa: N802
        path = urlsplit(self.path).path
        if path in ("/", "/index.html"):
            self._send_shell()
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
    """壳 + 注入数据落盘单文件 (不开服务); 链接前缀由壳自行按 file: 协议取 STATIC_LINK_PREFIX。"""
    html, is_real = _read_shell(shell_path)
    payload = json.dumps(nav_data.collect_nav(mb), ensure_ascii=False)
    if DATA_TOKEN not in html:
        sys.stderr.write("[nav] shell has no %s token, data not injected\n" % DATA_TOKEN)
        return 1
    html = html.replace(DATA_TOKEN, payload)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "nav_page.html"
    out.write_text(html, encoding="utf-8")
    kind = "shell" if is_real else "placeholder shell (nav_page.html pending, S2)"
    print("[nav] static export: %s (%d bytes, %s)" % (out, out.stat().st_size, kind))
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
