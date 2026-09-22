#!/usr/bin/env python
"""BTSchool HR 种子下载实验脚本 (独立实验程序, 不接入 auto-qb 主程序)。

用途: 验证「HR 统计页解析 + cookie 下载 .torrent + infohash 计算」整条链路, 为
docs/plans/26-09-22-2204-partial-hr-site-verify-plan.html (部分种子 HR 在线核实) 的 M1 探路。
页面样张: D:/Projects/站点页面/ (myhr.php 保存页, 已验证表格结构)。

页面事实 (2026-09-22 样张核对):
- myhr.php 表头: HR编号 | 种子名称 | 上传量 | 下载量 | 分享率 | 还需做种时间 | 完成时间 | 剩余达标时间 | 20000魔力值免罪
- HR编号 即种子 tid (站点内唯一); 页面无 download.php 链接, 按 NexusPHP 惯例拼 download.php?id={tid}
- HR 表外还有一层 <td class="embedded"> 包裹表 (嵌套), 解析器须容忍
- 状态过滤: myhr.php?hrtype=A(考察中,默认) / B(已达标) / C(未达标) / D(已免罪)
- 时间格式: 还需做种 "H:MM:SS"; 剩余达标 "X天HH:MM:SS"; 完成时间 "YYYY-MM-DD HH:MM:SS"

用法:
  # 离线解析样张 (无网络, 开发解析器用)
  uv run python scripts/hr_fetch_experiment.py --html <保存的 myhr.html>

  # 在线: 解析 HR 页 (需要 cookie, 不下载种子)
  uv run python scripts/hr_fetch_experiment.py --cookie-file <cookie.txt>

  # 在线: 解析并下载前 2 个种子的 .torrent (限速 20s±25%)
  uv run python scripts/hr_fetch_experiment.py --cookie-file <cookie.txt> --download 2 --min-interval 20

  # 自测 (bencode/infohash 钉死向量 + 数值解析)
  uv run python scripts/hr_fetch_experiment.py --selftest

cookie 获取: 浏览器登录 BTSchool 后, DevTools -> Network -> 任一请求 -> Cookie 请求头整串复制,
存入本地文件 (一行, "uid=...; pass=...; ..." 形态) 再用 --cookie-file 传入。脚本不打印 cookie 内容。
安全: cookie 文件不要放进仓库 (auto-qb-data/ 已 gitignore, 可放那里)。

自动抓取 cookie (Chrome/Edge 专用 profile + CDP, 推荐):
  # 首次/失效重登: 打开可见浏览器, 登录后脚本自动检测并收尾 (cookie 存专用 profile, 不落明文文件)
  uv run python scripts/hr_fetch_experiment.py --auto-cookie-login
  # 日常: 无头拉起专用 profile, 经 CDP 自动读 cookie 再抓 HR 页 (全自动, 无需人工)
  uv run python scripts/hr_fetch_experiment.py --auto-cookie
原理: Chrome 136+ 禁止在默认用户目录开调试端口 (已核实), 专用 --user-data-dir 是官方许可通道;
cookie 由浏览器进程自己解密经 CDP 交付 (App-Bound Encryption 下的合法路径), 本脚本不碰 cookie 库、不落明文。

已知边界: 未自动翻页 (有下一页时会提示, 可用 --page); 下载 URL 形态 (download.php?id= 是否还需
passkey 参数) 待在线验证; 站点改版时解析器需按新样张更新。
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import random
import re
import socket
import struct
import subprocess
import sys
import time
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

DEFAULT_BASE_URL = "https://pt.btschool.club"
DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

# ---------- bencode / infohash ----------


def bdecode(data: bytes, pos: int = 0):
    """最小 bencode 解码, 返回 (value, next_pos)。只服务于 .torrent 解析。"""
    c = data[pos : pos + 1]
    if c == b"i":
        e = data.index(b"e", pos)
        return int(data[pos + 1 : e]), e + 1
    if c == b"l":
        pos += 1
        out = []
        while data[pos : pos + 1] != b"e":
            v, pos = bdecode(data, pos)
            out.append(v)
        return out, pos + 1
    if c == b"d":
        pos += 1
        out = {}
        while data[pos : pos + 1] != b"e":
            k, pos = bdecode(data, pos)
            v, pos = bdecode(data, pos)
            out[k] = v
        return out, pos + 1
    if c.isdigit():
        colon = data.index(b":", pos)
        n = int(data[pos:colon])
        start = colon + 1
        return data[start : start + n], start + n
    raise ValueError(f"bencode 非法字节 @ {pos}: {data[pos : pos + 8]!r}")


def compute_infohashes(data: bytes) -> tuple[str, str, dict]:
    """v1 = sha1(info dict 原始字节切片), v2 = sha256 同切片。

    刻意不做 decode->re-encode: 键序/整数表示的重编码漂移会算错 infohash (计划文档 §5)。
    返回 (v1_hex, v2_hex, info_dict)。
    """
    if not data.startswith(b"d"):
        raise ValueError("不是 bencode 字节流 (应为 'd' 开头)")
    top, _ = bdecode(data, 0)
    if not isinstance(top, dict) or b"info" not in top:
        raise ValueError("缺少 info dict, 不是 .torrent")
    pos = 1  # 跳过顶层 'd'
    while data[pos : pos + 1] != b"e":
        key, p = bdecode(data, pos)
        val, p2 = bdecode(data, p)
        if key == b"info":
            span = data[p:p2]
            return hashlib.sha1(span).hexdigest(), hashlib.sha256(span).hexdigest(), val
        pos = p2
    raise ValueError("未遍历到 info")


# ---------- 自测钉死向量 ----------
# 由独立临时编码器 (.openclaw/tmp/genvec.py) 生成, 以 base64 装载 —— 不手抄二进制转义:
# 2026-09-22 实测, repr 里的 \t/\n/\r 经工具层会变成真实控制字符, 钉死向量当场抓到。

_SELFTEST_TORRENTS = [
    (
        "ZDg6YW5ub3VuY2UyNTpodHRwOi8vdC5leGFtcGxlL2Fubm91bmNlNDppbmZvZDY6bGVuZ3RoaTVlNDpuYW1lNTphLmJpbjEyOnBpZWNlIGxlbmd0aGkxNjM4NGU2OnBpZWNlczIwOgAAAAAAAAAAAAAAAAAAAAAAAAAAZWU=",
        "3cc95307628a6ee049939b7fe016c05785e95bf7",
        "d3fa2e18585e3be68da3c9bd54bd8abc47d48e18b54644b965b0c95a8d4fa033",
    ),
    (
        "ZDg6YW5ub3VuY2UyNTpodHRwOi8vdC5leGFtcGxlL2Fubm91bmNlNzpjb21tZW50MjI6aHItZXhwZXJpbWVudCBzZWxmdGVzdDQ6aW5mb2Q2Omxlbmd0aGkxMDQ4NTc2ZTQ6bmFtZTEwOua1i+ivlS5iaW4xMjpwaWVjZSBsZW5ndGhpMjYyMTQ0ZTY6cGllY2VzMjA6AAECAwQFBgcICQoLDA0ODxAREhNlNzpwcml2YXRlaTFlZQ==",
        "786b051887df6be782953b6d43ec9da57525bad5",
        "5a45147916aa9f8920c5737a65e54a4363a9cac397427d108a851bc78838ce93",
    ),
]


# ---------- 容错数值解析 ----------

_SIZE_UNITS = {
    "B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4,
    "KIB": 1024, "MIB": 1024**2, "GIB": 1024**3, "TIB": 1024**4,
}


def parse_size(text: str) -> int | None:
    m = re.search(r"([\d.,]+)\s*([A-Za-z]+)", text or "")
    if not m:
        return None
    try:
        value = float(m.group(1).replace(",", ""))
    except ValueError:
        return None
    return int(value * _SIZE_UNITS.get(m.group(2).upper(), 1))


def parse_duration(text: str) -> int | None:
    """"2:42:17" -> 9721; "9天06:05:11" -> 799511。返回秒。"""
    if not text:
        return None
    t = text.strip()
    days = 0
    dm = re.match(r"^(\d+)天", t)
    if dm:
        days = int(dm.group(1))
        t = t[dm.end():]
    parts = t.split(":")
    if not all(p.strip().isdigit() for p in parts) or len(parts) < 2:
        return None
    parts = [int(p) for p in parts]
    while len(parts) < 3:
        parts.insert(0, 0)
    h, m, s = parts[-3:]
    return days * 86400 + h * 3600 + m * 60 + s


def parse_ratio(text: str) -> float | None:
    m = re.search(r"[\d.]+", text or "")
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None


def parse_dt(text: str) -> str | None:
    t = (text or "").strip()
    try:
        return datetime.strptime(t, "%Y-%m-%d %H:%M:%S").isoformat(sep=" ")
    except ValueError:
        return None


# ---------- myhr.php 表格解析 (栈式树, 容忍包裹表嵌套) ----------


class _TableTree(HTMLParser):
    """收集 <tr>/<td> 树。row 节点: {"cells", "container"}; cell 节点: {"text", "hrefs", "rows"}。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root: list[dict] = []
        self._cells: list[dict] = []  # 打开的 cell 栈
        self._rows: list[dict] = []   # 打开的 row 栈

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            row: dict = {"cells": [], "container": None}
            if self._cells:
                kids = self._cells[-1].setdefault("rows", [])
                kids.append(row)
                row["container"] = kids
            else:
                self.root.append(row)
                row["container"] = self.root
            self._rows.append(row)
        elif tag in ("td", "th") and self._rows:
            cell: dict = {"text": [], "hrefs": [], "rows": []}
            self._rows[-1]["cells"].append(cell)
            self._cells.append(cell)
        elif tag == "a" and self._cells:
            href = dict(attrs).get("href")
            if href:
                self._cells[-1]["hrefs"].append(href)

    def handle_data(self, data):
        if self._cells:
            self._cells[-1]["text"].append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._cells:
            self._cells.pop()
        elif tag == "tr" and self._rows:
            self._rows.pop()

    def flat_rows(self) -> list[tuple[dict, list, int]]:
        """遍历全部 row, 返回 (row, container, index); 仅收「全部 cell 无嵌套行」的扁平行。"""

        def walk(container: list, out: list) -> None:
            for i, row in enumerate(container):
                if all(len(c["rows"]) == 0 for c in row["cells"]):
                    out.append((row, container, i))
                for c in row["cells"]:
                    walk(c["rows"], out)

        out: list[tuple[dict, list, int]] = []
        walk(self.root, out)
        return out


def _cell_text(cell: dict) -> str:
    return "".join(cell["text"]).strip()


def parse_myhr(html: str) -> list[dict]:
    """解析 myhr.php 的 HR 表。以表头行 (首列 'HR编号') 锚定, 同容器内后续 tid 数字行即数据。"""
    parser = _TableTree()
    parser.feed(html)

    columns: list[str] = []
    container: list | None = None
    header_i: int | None = None
    for row, cont, i in parser.flat_rows():
        cells = row["cells"]
        if cells and _cell_text(cells[0]) == "HR编号":
            container = cont
            header_i = i
            columns = [_cell_text(c) for c in cells]
            break
    if container is None or header_i is None:
        return []

    def col(name: str) -> int:
        return columns.index(name)

    i_name, i_up = col("种子名称"), col("上传量")
    i_dl, i_ratio = col("下载量"), col("分享率")
    i_need, i_done, i_remain = col("还需做种时间"), col("完成时间"), col("剩余达标时间")

    out: list[dict] = []
    for row in container[header_i + 1 :]:
        cells = row["cells"]
        if not cells or not _cell_text(cells[0]).isdigit():
            break  # 数据区结束 (页脚/分页等)
        name_cell = cells[i_name] if i_name < len(cells) else {"text": [""], "hrefs": []}
        details = next((h for h in name_cell["hrefs"] if "details.php" in h), None)
        uploaded_raw = _cell_text(cells[i_up]) if i_up < len(cells) else ""
        downloaded_raw = _cell_text(cells[i_dl]) if i_dl < len(cells) else ""
        ratio_raw = _cell_text(cells[i_ratio]) if i_ratio < len(cells) else ""
        need_raw = _cell_text(cells[i_need]) if i_need < len(cells) else ""
        done_raw = _cell_text(cells[i_done]) if i_done < len(cells) else ""
        remain_raw = _cell_text(cells[i_remain]) if i_remain < len(cells) else ""
        bonus = None
        for c in cells:
            for h in c["hrefs"]:
                if "USEBOUNS" in h:
                    bonus = h
        out.append(
            {
                "tid": int(_cell_text(cells[0])),
                "name": _cell_text(name_cell),
                "details_url": details,
                "uploaded_raw": uploaded_raw,
                "uploaded_bytes": parse_size(uploaded_raw),
                "downloaded_raw": downloaded_raw,
                "downloaded_bytes": parse_size(downloaded_raw),
                "ratio_raw": ratio_raw,
                "ratio": parse_ratio(ratio_raw),
                "need_seed_raw": need_raw,
                "need_seed_seconds": parse_duration(need_raw),
                "done_raw": done_raw,
                "done_iso": parse_dt(done_raw),
                "remain_raw": remain_raw,
                "remain_seconds": parse_duration(remain_raw),
                "bonus_url": bonus,
            }
        )
    return out


def has_next_page(html: str) -> bool:
    """分页区存在真实 <a> 的「下一页」(样张里灰色的下一页是无链接的 <font><b>)。"""
    return re.search(r'<a[^>]+href="[^"]*myhr\.php[^"]*"[^>]*>\s*(?:<b>)?下一页', html) is not None


# ---------- HTTP ----------


def build_client(cookie: str | None, user_agent: str, base_url: str):
    try:
        import httpx
    except ImportError as e:  # pragma: no cover
        raise SystemExit("缺少 httpx, 请用项目环境运行: uv run python scripts/hr_fetch_experiment.py") from e
    cookies = {}
    if cookie:
        for pair in cookie.split(";"):
            pair = pair.strip()
            if "=" in pair:
                k, v = pair.split("=", 1)
                cookies[k.strip()] = v.strip()
    return httpx.Client(
        headers={"User-Agent": user_agent, "Accept-Language": "zh-CN,zh;q=0.9"},
        cookies=cookies,
        follow_redirects=True,
        timeout=20.0,
        base_url=base_url,
    )


def fetch_page_text(client, url: str) -> str:
    resp = client.get(url)
    resp.raise_for_status()
    # NexusPHP 头部 charset 可靠性一般, 直接 utf-8 宽松解码 (样张即 utf-8)
    return resp.content.decode("utf-8", "replace")


_LOGIN_MARKS = ("takelogin.php", 'name="password"')


def looks_like_login(html: str) -> bool:
    return any(mark in html for mark in _LOGIN_MARKS) and "HR编号" not in html


# ---------- 下载 ----------


def download_torrent(client, base_url: str, tid: int, out_dir: Path) -> dict:
    """下载单个 .torrent 并计算 infohash。返回结果 dict (不抛网络异常, 由调用方记失败)。"""
    out_path = out_dir / f"{tid}.torrent"
    if out_path.exists():
        data = out_path.read_bytes()
        v1, v2, _ = compute_infohashes(data)
        return {"tid": tid, "status": "cached", "path": str(out_path), "v1": v1, "v2": v2, "bytes": len(data)}
    url = f"{base_url}/download.php?id={tid}"
    resp = client.get(url)
    if resp.status_code != 200:
        return {"tid": tid, "status": f"http {resp.status_code}"}
    data = resp.content
    ctype = resp.headers.get("content-type", "")
    if "text/html" in ctype or data[:1] == b"<":
        return {"tid": tid, "status": "返回 HTML (登录失效/权限/挑战?), 非 .torrent"}
    v1, v2, info = compute_infohashes(data)
    out_path.write_bytes(data)
    name = info.get(b"name", b"?").decode("utf-8", "replace")
    return {
        "tid": tid, "status": "downloaded", "path": str(out_path), "v1": v1, "v2": v2,
        "bytes": len(data), "torrent_name": name, "content_type": ctype,
    }


# ---------- 自动 cookie: 专用 profile + CDP (Chrome/Edge) ----------

_BROWSER_PATHS = {
    "chrome": ["Google/Chrome/Application/chrome.exe"],
    "edge": ["Microsoft/Edge/Application/msedge.exe"],
}


def find_browser(kind: str) -> str | None:
    if "/" in kind or "\\" in kind:  # 完整路径
        return kind if Path(kind).exists() else None
    roots = []
    for var in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
        v = os.environ.get(var)
        if v:
            roots.append(Path(v))
    for rel in _BROWSER_PATHS.get(kind, []):
        for root in roots:
            p = root / rel
            if p.exists():
                return str(p)
    return None


def resolve_browser(browser: str) -> str:
    if browser == "auto":
        exe = find_browser("chrome") or find_browser("edge")
    else:
        exe = find_browser(browser)
    if not exe:
        raise SystemExit("未找到浏览器可执行文件 (试过 chrome 与 edge; 可用 --browser 指定完整路径)。")
    return exe


class MiniWSError(RuntimeError):
    pass


class MiniWS:
    """极小 WebSocket 客户端, 只满足 CDP 一问一答 (文本帧 + ping/pong + 分片累积)。"""

    def __init__(self, url: str, timeout: float = 10.0):
        u = urlparse(url)
        host = u.hostname or "127.0.0.1"
        port = u.port or (443 if u.scheme == "wss" else 80)
        self._sock = socket.create_connection((host, port), timeout=timeout)
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        req = (
            f"GET {u.path or '/'} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            "Upgrade: websocket\r\nConnection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
        )
        self._sock.sendall(req.encode("ascii"))
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = self._sock.recv(4096)
            if not chunk:
                raise MiniWSError("WS 握手无响应")
            buf += chunk
        head, _, self._buf = buf.partition(b"\r\n\r\n")
        status = head.split(b"\r\n", 1)[0]
        if b"101" not in status:
            raise MiniWSError(f"WS 握手失败: {status!r}")

    def _frame(self, opcode: int, payload: bytes) -> bytes:
        mask = os.urandom(4)
        head = bytearray([0x80 | opcode])
        n = len(payload)
        if n < 126:
            head.append(0x80 | n)
        elif n < 65536:
            head.append(0x80 | 126)
            head += struct.pack(">H", n)
        else:
            head.append(0x80 | 127)
            head += struct.pack(">Q", n)
        head += mask
        return bytes(head) + bytes(b ^ mask[i % 4] for i, b in enumerate(payload))

    def send_text(self, text: str) -> None:
        self._sock.sendall(self._frame(0x1, text.encode("utf-8")))

    def _read_exact(self, n: int) -> bytes:
        while len(self._buf) < n:
            chunk = self._sock.recv(65536)
            if not chunk:
                raise MiniWSError("WS 连接关闭")
            self._buf += chunk
        out, self._buf = self._buf[:n], self._buf[n:]
        return out

    def recv_text(self) -> str:
        chunks = bytearray()
        while True:
            b1, b2 = self._read_exact(2)
            opcode, fin = b1 & 0x0F, b1 & 0x80
            ln = b2 & 0x7F
            if ln == 126:
                ln = struct.unpack(">H", self._read_exact(2))[0]
            elif ln == 127:
                ln = struct.unpack(">Q", self._read_exact(8))[0]
            payload = self._read_exact(ln) if ln else b""
            if opcode == 0x8:
                raise MiniWSError("WS 对端关闭")
            if opcode == 0x9:  # ping -> pong
                self._sock.sendall(self._frame(0xA, payload))
                continue
            if opcode in (0x1, 0x2, 0x0):
                chunks += payload
                if fin:
                    return chunks.decode("utf-8", "replace")


def _free_debug_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _kill_profile_browsers(profile_dir: Path) -> None:
    """按命令行匹配结束占用专用 profile 的浏览器进程树。

    实测 (2026-09-22): Chrome/Edge 启动器进程会秒退 (exit 0/21) 而真实浏览器继续存活,
    proc.terminate() 只杀得掉启动器 —— 只能按命令行里的 profile 路径击杀, 不会碰到用户自己的浏览器。
    """
    marker = str(profile_dir).replace("'", "''")
    ps = (
        "Get-CimInstance Win32_Process -Filter \"Name='chrome.exe' or Name='msedge.exe'\" | "
        f"Where-Object {{ $_.CommandLine -like '*{marker}*' }} | "
        "Select-Object -ExpandProperty ProcessId"
    )
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True, timeout=20
        )
        for line in r.stdout.splitlines():
            pid = line.strip()
            if pid.isdigit():
                subprocess.run(["taskkill", "/T", "/F", "/PID", pid], capture_output=True, timeout=20)
    except Exception:
        pass


def _launch_cdp_browser(browser: str, profile_dir: Path, headless: bool, url: str):
    exe = resolve_browser(browser)
    profile_abs = str(profile_dir.resolve())
    port = _free_debug_port()
    cmd = [
        exe, f"--user-data-dir={profile_abs}", f"--remote-debugging-port={port}",
        "--no-first-run", "--no-default-browser-check", "--disable-gpu", "--disable-crashpad",
        "--window-size=1150,860",
    ]
    if headless:
        cmd.append("--headless=new")
    if url:
        cmd.append(url)
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    import httpx

    # 就绪判定只看调试端口: 启动器进程可能秒退而真实浏览器继续存活 (2026-09-22 实测),
    # 不能用 proc.poll() 判活
    deadline = time.time() + 30
    ver = None
    while time.time() < deadline:
        try:
            r = httpx.get(f"http://127.0.0.1:{port}/json/version", timeout=1.0)
            if r.status_code == 200:
                ver = r.json()
                break
        except Exception:
            time.sleep(0.3)
    if ver is None:
        _kill_profile_browsers(profile_dir)
        raise SystemExit(
            "浏览器调试端口 30s 未就绪; 若反复失败: 关闭残留进程后删除专用 profile 目录"
            f"({profile_abs}) 并重跑 --auto-cookie-login。"
        )
    return proc, ver


def _cdp_get_cookies(ws: MiniWS, request_id: int) -> list[dict]:
    ws.send_text(json.dumps({"id": request_id, "method": "Storage.getCookies", "params": {}}))
    deadline = time.time() + 15
    while time.time() < deadline:
        msg = json.loads(ws.recv_text())
        if msg.get("id") == request_id:
            if "error" in msg:
                raise SystemExit(f"CDP Storage.getCookies 失败: {msg['error']}")
            return msg.get("result", {}).get("cookies", [])
    raise SystemExit("CDP 响应超时。")


def _bs_cookies(cookies: list[dict], domain_suffix: str) -> list[dict]:
    out = []
    for c in cookies:
        dom = (c.get("domain") or "").lstrip(".").lower()
        if dom == domain_suffix or dom.endswith("." + domain_suffix):
            out.append(c)
    return out


def _cookie_header(cookies: list[dict]) -> str:
    return "; ".join(f"{c['name']}={c['value']}" for c in cookies)


_LOGIN_COOKIE_NAMES = {"uid", "pass", "c_secure_uid", "c_secure_ssl", "c_secure_login", "c_secure_tracker_ssl"}


def _logged_in(bs: list[dict]) -> bool:
    return any(c.get("name") in _LOGIN_COOKIE_NAMES and c.get("value") for c in bs)


def _close_browser_gracefully(ws: MiniWS | None, proc, profile_dir: Path | None = None) -> None:
    if ws is not None:
        try:  # Browser.close 走优雅退出, 保证 cookie 落盘
            ws.send_text(json.dumps({"id": 99990, "method": "Browser.close", "params": {}}))
            time.sleep(1.5)
        except Exception:
            pass
    try:
        proc.terminate()  # 只能杀启动器; 真实浏览器靠下一步按 profile 击杀
    except Exception:
        pass
    if profile_dir is not None:
        time.sleep(0.5)
        _kill_profile_browsers(profile_dir)


def auto_cookie_login(args) -> int:
    """可见浏览器完成一次登录; cookie 由浏览器存进专用 profile, 脚本只探测不落盘。"""
    suffix = (urlparse(args.base_url).hostname or "").lower()
    profile = Path(args.profile_dir)
    profile.mkdir(parents=True, exist_ok=True)
    url = f"{args.base_url}/myhr.php"
    print(f"启动浏览器 (专用 profile: {profile}) 打开 {url}")
    print("请在浏览器里登录 BTSchool; 脚本每 2s 自动检测登录 cookie, 成功即自动收尾 (最长等 10 分钟)。")
    proc, ver = _launch_cdp_browser(args.browser, profile, headless=False, url=url)
    ws: MiniWS | None = None
    try:
        ws = MiniWS(ver["webSocketDebuggerUrl"], timeout=10.0)
        deadline = time.time() + 600
        request_id = 1
        while time.time() < deadline:
            time.sleep(2)
            try:
                cookies = _cdp_get_cookies(ws, request_id)
            except (MiniWSError, OSError, json.JSONDecodeError):
                print("WS 断开, 重连…")
                ws = MiniWS(ver["webSocketDebuggerUrl"], timeout=10.0)
                continue
            request_id += 1
            bs = _bs_cookies(cookies, suffix)
            if _logged_in(bs):
                names = sorted({c.get("name", "") for c in bs})
                print(f"检测到登录 cookie ({len(bs)} 条, 名称: {', '.join(names)})。会话已存专用 profile。")
                print("之后用 --auto-cookie 即可全自动抓取。")
                return 0
        print("超时 (10 分钟) 未检测到登录 cookie; 未完成的话请重跑本命令。", file=sys.stderr)
        return 1
    finally:
        _close_browser_gracefully(ws, proc, profile)


def auto_cookie_grab(args) -> str | None:
    """无头拉起专用 profile, 经 CDP 读 cookie, 返回可直接用的 Cookie 头串 (不落盘)。"""
    suffix = (urlparse(args.base_url).hostname or "").lower()
    profile = Path(args.profile_dir)
    if not profile.exists():
        print("专用 profile 不存在: 先跑一次 --auto-cookie-login。", file=sys.stderr)
        return None
    proc, ver = _launch_cdp_browser(args.browser, profile, headless=True, url="about:blank")
    ws: MiniWS | None = None
    try:
        ws = MiniWS(ver["webSocketDebuggerUrl"], timeout=10.0)
        cookies = _cdp_get_cookies(ws, 1)
        bs = _bs_cookies(cookies, suffix)
        if not _logged_in(bs):
            names = sorted({c.get("name", "") for c in bs}) or "(无)"
            print(f"专用 profile 无有效登录 cookie (现有: {names})。先跑一次 --auto-cookie-login。", file=sys.stderr)
            return None
        return _cookie_header(bs)
    finally:
        _close_browser_gracefully(ws, proc, profile)


# ---------- CLI ----------


def print_rows(rows: list[dict]) -> None:
    if not rows:
        print("(无数据行)")
        return
    widths = (10, 44, 12, 12, 8, 12, 20, 16)
    head = ("HR编号", "种子名称", "上传量", "下载量", "分享率", "还需做种", "完成时间", "剩余达标")
    print(" | ".join(h.ljust(w) for h, w in zip(head, widths)))
    print("-" * (sum(widths) + 3 * (len(widths) - 1)))
    for r in rows:
        name = r["name"][: widths[1] - 1] + "…" if len(r["name"]) > widths[1] else r["name"]
        cells = (
            str(r["tid"]), name, r["uploaded_raw"], r["downloaded_raw"], r["ratio_raw"],
            r["need_seed_raw"], r["done_raw"], r["remain_raw"],
        )
        print(" | ".join(c.ljust(w) for c, w in zip(cells, widths)))


def selftest() -> int:
    failed = 0
    for b64, want_v1, want_v2 in _SELFTEST_TORRENTS:
        data = base64.b64decode(b64)
        v1, v2, info = compute_infohashes(data)
        ok = v1 == want_v1 and v2 == want_v2
        print(f"[{'OK' if ok else 'FAIL'}] infohash v1={v1[:12]}… v2={v2[:12]}… name={info.get(b'name', b'?')!r}")
        failed += 0 if ok else 1
    checks = [
        (parse_size("27.34 GB"), int(27.34 * 1024**3)),
        (parse_size("0.00 KB"), 0),
        (parse_size("451.88 GB"), int(451.88 * 1024**3)),
        (parse_duration("2:42:17"), 2 * 3600 + 42 * 60 + 17),
        (parse_duration("9天06:05:11"), 9 * 86400 + 6 * 3600 + 5 * 60 + 11),
        (parse_duration("06:05:11"), 6 * 3600 + 5 * 60 + 11),
        (parse_ratio("0.000"), 0.0),
        (parse_ratio("6.212"), 6.212),
        (parse_dt("2026-09-22 04:34:25"), "2026-09-22 04:34:25"),
    ]
    for got, want in checks:
        ok = got == want
        print(f"[{'OK' if ok else 'FAIL'}] {got!r} == {want!r}")
        failed += 0 if ok else 1
    print("selftest:", "全部通过" if failed == 0 else f"{failed} 项失败")
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="BTSchool HR 种子下载实验 (解析 + cookie 下载 + infohash)")
    ap.add_argument("--html", help="离线解析本地保存的 myhr.php 页面 (无网络)")
    ap.add_argument("--url", default=f"{DEFAULT_BASE_URL}/myhr.php", help="HR 统计页地址")
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL, help="站点根 (拼 download.php 用)")
    ap.add_argument("--hrtype", choices=["A", "B", "C", "D"], help="状态过滤: A考察中(默认页) B已达标 C未达标 D已免罪")
    ap.add_argument("--page", type=int, help="翻页参数 (?page=N, 形态待在线验证)")
    ap.add_argument("--cookie", help="cookie 串 (推荐改用 --cookie-file 或 --auto-cookie; 进程参数可能被本机其他进程看到)")
    ap.add_argument("--cookie-file", help="cookie 串所在文件 (一行, 浏览器复制的 Cookie 请求头)")
    ap.add_argument("--auto-cookie", action="store_true", help="无头拉起专用 profile 经 CDP 自动读 cookie (首次先 --auto-cookie-login)")
    ap.add_argument("--auto-cookie-login", action="store_true", help="打开可见浏览器完成登录; 会话存专用 profile 不落明文")
    ap.add_argument("--browser", default="auto", help="auto | chrome | edge | 浏览器可执行文件完整路径")
    ap.add_argument("--profile-dir", default="auto-qb-data/hr-experiment/chrome-profile", help="专用浏览器 profile 目录")
    ap.add_argument("--user-agent", default=DEFAULT_UA)
    ap.add_argument("--download", type=int, default=0, help="下载前 N 个种子的 .torrent (默认 0 = 只解析)")
    ap.add_argument("--all", action="store_true", help="下载全部 (受 --download 优先级低)")
    ap.add_argument("--min-interval", type=float, default=15.0, help="两次下载最小间隔秒 (±25%% 抖动)")
    ap.add_argument("--out-dir", default="auto-qb-data/hr-experiment", help=".torrent 保存目录")
    ap.add_argument("--json", help="把解析结果写 JSON 到该路径")
    ap.add_argument("--selftest", action="store_true", help="运行 bencode/infohash 与解析器自测")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()
    if args.auto_cookie_login:
        return auto_cookie_login(args)

    # ---- 取页面 (离线 or 在线) ----
    if args.html:
        html = Path(args.html).read_text(encoding="utf-8", errors="replace")
        source = f"offline: {args.html}"
        client = None
    else:
        if args.auto_cookie:
            cookie = auto_cookie_grab(args)
            if not cookie:
                return 1
        else:
            cookie = args.cookie
            if args.cookie_file:
                cookie = Path(args.cookie_file).read_text(encoding="utf-8").strip()
            if not cookie:
                print("错误: 在线模式需要 cookie (--auto-cookie 自动抓取, 或 --cookie-file <文件>)。", file=sys.stderr)
                print("首次使用: 先跑 --auto-cookie-login 完成一次登录, 之后 --auto-cookie 全自动。", file=sys.stderr)
                return 1
            if args.cookie:
                print("提示: 用 --cookie-file 或 --auto-cookie 代替 --cookie 更安全 (进程参数对本机其他进程可见)。")
        url = args.url
        if args.hrtype:
            url += ("&" if urlparse(url).query else "?") + f"hrtype={args.hrtype}"
        if args.page is not None:
            url += ("&" if urlparse(url).query else "?") + f"page={args.page}"
        client = build_client(cookie, args.user_agent, args.base_url)
        print(f"GET {url}")
        html = fetch_page_text(client, url)
        source = url

    rows = parse_myhr(html)
    print(f"来源: {source}")
    if not rows:
        if looks_like_login(html):
            print("页面像登录页 (未见 HR 表格): cookie 失效或未登录。", file=sys.stderr)
            return 2
        print("未找到 HR 表格: 当前过滤下无记录, 或页面改版 (解析器需更新)。", file=sys.stderr)
        return 2
    if has_next_page(html):
        print("注意: 存在下一页 (实验脚本未自动翻页, 可用 --page 继续)。")
    print(f"解析到 {len(rows)} 行:\n")
    print_rows(rows)

    if args.json:
        Path(args.json).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nJSON 已写入 {args.json}")

    # ---- 下载 ----
    targets = rows if args.all else rows[: max(0, args.download)]
    if client is None and targets:
        print("\n离线模式不下载; 在线下载请去掉 --html 并提供 cookie。")
        return 0
    if not targets:
        return 0

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n开始下载 {len(targets)} 个 .torrent -> {out_dir} (间隔 >= {args.min_interval}s ±25% 抖动)")
    failures = 0
    for i, row in enumerate(targets):
        if i:
            pause = args.min_interval * random.uniform(0.75, 1.25)
            print(f"  … 限速等待 {pause:.1f}s")
            time.sleep(pause)
        try:
            result = download_torrent(client, args.base_url, row["tid"], out_dir)
        except Exception as e:  # 实验脚本: 单个失败不中断
            result = {"tid": row["tid"], "status": f"异常: {e}"}
        status = result.get("status")
        if status in ("downloaded", "cached"):
            print(
                f"  [{status}] tid={result['tid']} {result.get('torrent_name', row['name'])[:40]} "
                f"{result['bytes']}B\n      v1={result['v1']}\n      v2={result['v2']}\n      {result['path']}"
            )
        else:
            failures += 1
            print(f"  [FAIL] tid={result['tid']} {status}")
    if failures:
        print(f"\n{failures} 个下载失败 (常见原因: cookie 失效 / 需 passkey 参数 / 触发站点限流)。")
        return 3
    print("\n全部完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
