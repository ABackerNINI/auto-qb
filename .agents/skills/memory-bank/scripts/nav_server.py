"""nav 导航页服务层 (纯 stdlib http.server, 零新依赖; 服务模式零落盘)。

路由 (计划 26-10-04-0952 §03):
    GET /                    页面壳 (同目录 nav_page.html, S2 交付; 缺失返回 503 提示, 不抛 traceback)
    GET /api/data            每请求现算 nav_data.collect_nav(), JSON 直返 (前端 30s 轮询此端点)
    GET /memory-bank/<path>  静态映射四工位原文, 供「打开原文」; resolve 后必须仍落在 memory-bank/
                             内, 越界一律 403 (URL 先解码再判, ../ 与 %2e%2e / ..%2f / 反斜杠等
                             变体全部拦截, 测试钉死)

用法 (从仓库根):
    python .agents/skills/memory-bank/scripts/nav_server.py                    起服务 (127.0.0.1:8765;
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
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import find_root, resolve_mb_dir  # noqa: E402
import nav_data  # noqa: E402

SHELL_NAME = "nav_page.html"
DEFAULT_STATIC_DIR = "tmp-analysis/nav"  # 相对仓库根; 目录已 gitignored, 静态导出件不入库
STATIC_LINK_PREFIX = "../../memory-bank/"  # 静态件指向 memory-bank 原文的相对链接前缀 (壳按 file: 协议取用)
DATA_TOKEN = "__DATA__"  # 壳内数据注入位 (S2 的壳以同款 token 预留)

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


class NavHandler(BaseHTTPRequestHandler):
    """路由处理器; mb / shell_path 由 _build_handler 在子类上注入。"""

    mb: Path
    shell_path: Path

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

    def _send_bytes(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, code: int, text: str) -> None:
        self._send_bytes(code, text.encode("utf-8"), "text/plain; charset=utf-8")

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


def _build_handler(mb: Path, shell_path: Path) -> type[NavHandler]:
    return type("BoundNavHandler", (NavHandler, ), {"mb": mb, "shell_path": shell_path})


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


def serve(mb: Path, shell_path: Path, port: int, open_browser: bool = True) -> int:
    try:
        server = NavServer(("127.0.0.1", port), _build_handler(mb, shell_path))
    except OSError as exc:
        sys.stderr.write(
            "[nav] bind 127.0.0.1:%d failed (%s): port likely in use, retry with --port <other>\n" % (port, exc)
        )
        return 1
    url = "http://127.0.0.1:%d" % port
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
    return serve(mb, shell_path, args.port, open_browser=not args.no_open)


if __name__ == "__main__":
    raise SystemExit(main())
