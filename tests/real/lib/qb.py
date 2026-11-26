"""极简 qBittorrent WebUI API 客户端(只覆盖真机实测要用的端点)。

设计约束(每条都有现场证据, 见 plan 26-10-31-0705 §02):
  - **绕代理**: 本机 HTTP_PROXY 会把 127.0.0.1 的请求转成 502, 一律用 ProxyHandler({}) 的 opener;
  - **字段名**: qB 5.2 返回 upspeed / dlspeed;
  - **免鉴权直连**: 四测试实例均已开 WebUI「跳过本地验证」, 不带任何凭据; 收到 401/403
    按 fail-closed 抛错停手, 信息直指「去 qB WebUI 重新勾选跳过本地验证」—— 修环境,
    不做鉴权降级/注入等绕行(免token口径, 2026-11-04 起);
  - **不吞异常**: HTTP 错误一律带状态码与 body 片段抛出, 让用例红在原因上而不是 None 上。
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # 绕 HTTP_PROXY: 127.0.0.1 不该走代理


class QbError(RuntimeError):
    """qB API 调用失败(带状态码与 body 片段)。"""


def _multipart(fields: dict, file_field: str, filename: str, payload: bytes) -> tuple[bytes, str]:
    """手工拼 multipart/form-data —— /torrents/add 的种子是文件字段, urllib 不自带。"""
    boundary = "----realqbrm00boundary7f3a"
    out = []
    for k, v in fields.items():
        out.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode())
    out.append(
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"{file_field}\"; filename=\"{filename}\"\r\n"
        "Content-Type: application/x-bittorrent\r\n\r\n".encode() + payload + b"\r\n"
    )
    out.append(f"--{boundary}--\r\n".encode())
    return b"".join(out), f"multipart/form-data; boundary={boundary}"


class Qb:
    """一个实例的客户端。port 必须在调用方(guard)已核过的白名单内。"""
    def __init__(self, port: int, timeout: float = 15.0):
        self.port = port
        self.timeout = timeout

    # ---- 底层 ----
    def _open(self, path: str, body: bytes | None, headers: dict[str, str]):
        # body=None → GET; body=b"" → POST 空体(app/shutdown 这类无参写端点)。
        # 不能按 `if body` 判: 空体写端点会被静默降成 GET, 退出指令根本发不出去。
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/v2{path}",
            data=body,
            method="POST" if body is not None else "GET",
        )
        for k, v in headers.items():
            req.add_header(k, v)
        return _OPENER.open(req, timeout=self.timeout)

    def _call(self, path: str, body: bytes | None = None, content_type: str | None = None) -> bytes:
        headers: dict[str, str] = {}
        if content_type:
            headers["Content-Type"] = content_type
        try:
            with self._open(path, body, headers) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            snippet = e.read()[:120]
            if e.code in (401, 403):
                # fail-closed: 实例本该免鉴权直连, 要鉴权说明「跳过本地验证」被重置(qB 升级/重装等)。
                # 修环境而不是加绕行: 不恢复 token 注入、不要用户现场给凭据。
                raise QbError(
                    f"port {self.port} {path} -> {e.code} {snippet!r}: "
                    "测试实例本应本机免鉴权, 现在要鉴权 —— 去 qB WebUI 设置重新勾选「跳过本地验证」后重跑"
                ) from None
            raise QbError(f"port {self.port} {path} -> {e.code} {snippet!r}") from None

    # ---- 端点 ----
    def version(self) -> str:
        return self._call("/app/version").decode().strip()

    def prefs(self) -> dict:
        return json.loads(self._call("/app/preferences"))

    def set_prefs(self, **changes) -> None:
        """改偏好。注意 qB 要的是表单字段 `json=<urlencoded>`, 直接发 JSON body 会 400。"""
        body = urllib.parse.urlencode({"json": json.dumps(changes)}).encode()
        self._call("/app/setPreferences", body, "application/x-www-form-urlencoded")

    def shutdown(self) -> None:
        """让 qB 自己优雅退出: POST /api/v2/app/shutdown(空体), 由它写回 fastresume/state。

        关停测试实例只走这里 —— 任何从外部强制终止进程的形态都禁止(AGENTS.md 进程安全
        红线, 事故档案见 memory-bank/pitfalls/ops/taskkill-image-name-ban.md)。
        N9 实验轮在 qB 5.2.3 上实测该端点返回 HTTP 200。
        """
        self._call("/app/shutdown", b"")

    def connection_status(self) -> str:
        """connected / firewalled / disconnected —— disconnected 说明没有可用监听 socket,
        此时 libtorrent 不会做任何 announce(现场证据见 plan 26-10-31-0705 §02 D4)。"""
        return json.loads(self._call("/transfer/info"))["connection_status"]

    def torrents(self, hashes: str | None = None) -> list[dict]:
        q = f"?hashes={hashes}" if hashes else ""
        return json.loads(self._call(f"/torrents/info{q}"))

    def torrent(self, infohash: str) -> dict | None:
        ts = self.torrents(infohash)
        return ts[0] if ts else None

    def trackers(self, infohash: str) -> list[dict]:
        return json.loads(self._call(f"/torrents/trackers?hash={infohash}"))

    def add_torrent(
        self,
        raw: bytes,
        savepath: str,
        paused: bool = False,
        tags: str = "",
        category: str = "",
        infohash_hint: str | None = None
    ) -> None:
        # paused / stopped 两个键都发: qB 5.0 起把 paused 改名 stopped, 同时发对新旧版本都成立
        fields = {
            "savepath": savepath,
            "paused": "true" if paused else "false",
            "stopped": "true" if paused else "false"
        }
        if tags:
            fields["tags"] = tags
        if category:
            fields["category"] = category
        body, ctype = _multipart(fields, "torrents", "realqb.torrent", raw)
        resp = self._call("/torrents/add", body, ctype).decode(errors="replace").strip()
        # qB 5.2 起返回 JSON 收据({"success_count":1,...}), 4.x 返回 "Ok."; 两种都算成功, 只有失败才抛
        if resp.startswith("{"):
            import json as _json
            try:
                receipt = _json.loads(resp)
            except ValueError:
                raise QbError(f"add_torrent 收据不是合法 JSON: {resp[:120]!r}") from None
            if not receipt.get("success_count"):
                raise QbError(f"add_torrent 失败: {resp[:200]!r}")
        elif resp not in ("Ok.", ""):
            raise QbError(f"add_torrent 被拒: {resp!r}")
        if not paused and infohash_hint:
            # qB 5.2 实测: 传 paused=false/stopped=false 加进来的种子仍可能是 stoppedUP(不 announce),
            # 所以这里显式补一次 start —— 否则用例会停在「没报到」而不是「零流量」上。
            cur = self.torrent(infohash_hint)
            if cur and cur["state"].startswith("stopped"):
                self.resume(infohash_hint)

    def pause(self, hashes: str) -> None:
        self._call(
            "/torrents/stop",
            urllib.parse.urlencode({
                "hashes": hashes
            }).encode(), "application/x-www-form-urlencoded"
        )

    def resume(self, hashes: str) -> None:
        self._call(
            "/torrents/start",
            urllib.parse.urlencode({
                "hashes": hashes
            }).encode(), "application/x-www-form-urlencoded"
        )

    def delete(self, hashes: str, delete_files: bool = True) -> None:
        data = urllib.parse.urlencode({"hashes": hashes, "deleteFiles": "true" if delete_files else "false"}).encode()
        self._call("/torrents/delete", data, "application/x-www-form-urlencoded")

    def set_location(self, hashes: str, location: str) -> None:
        """qB 原生搬种子(RM04-08 绕产品闸门用: 验产品的 save_path 变化检测面)"""
        data = urllib.parse.urlencode({"hashes": hashes, "location": location}).encode()
        self._call("/torrents/setLocation", data, "application/x-www-form-urlencoded")

    def add_tags(self, hashes: str, tags: str) -> None:
        data = urllib.parse.urlencode({"hashes": hashes, "tags": tags}).encode()
        self._call("/torrents/addTags", data, "application/x-www-form-urlencoded")

    def remove_tags(self, hashes: str, tags: str) -> None:
        data = urllib.parse.urlencode({"hashes": hashes, "tags": tags}).encode()
        self._call("/torrents/removeTags", data, "application/x-www-form-urlencoded")
