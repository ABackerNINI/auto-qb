"""测试公共组件: 模拟 qB 客户端 / 种子 / 配置 + 构造辅助 + 本地假 qB 服务

由 pytest.ini 的 pythonpath=src 处理 src 导入, 无需 sys.path 处理。
"""
import json
import os
import tempfile
import threading
import time
from collections.abc import Mapping
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

from auto_qb.config import (
    AddEpisodeTagsConfig,
    GroupingConfig,
    HRRule,
    LoggingConfig,
    NotifyConfig,
    QbittorrentConfig,
    WebConfig,
)  # noqa: E402
from auto_qb.config.models import HrCheckConfig  # noqa: E402  (包 __init__ 未导出 HR 在线核实配置类)
from auto_qb.core.qbmanager import QbManager  # noqa: E402
from auto_qb.rules import ActionResult, RuleContext  # noqa: E402
from auto_qb.torrents import REQUIRED_TORRENT_FIELDS, _VIEW_FIELDS, _VIEW_QUANTUM, view_field_value  # noqa: E402

try:
    from qbittorrentapi import TorrentState  # noqa: E402
except ImportError:  # 未安装 qbittorrentapi 时降级: state_enum 为 None
    TorrentState = None


# ---------- 模拟 qB 客户端 ----------
class _FakeTorrents(dict):
    """模拟 qbittorrentapi 的 torrents 命名空间: dict 风格访问 + .info(tag=...) 过滤"""
    def info(self, torrent_hashes=None, tag=None, **kw):
        """按 hash 和/或 tag 过滤种子(与 torrents_info 同语义)"""
        if torrent_hashes:
            if isinstance(torrent_hashes, (list, tuple)):
                hashes = set(torrent_hashes)
                items = [self[h] for h in hashes if h in self]
            else:
                items = [self[torrent_hashes]] if torrent_hashes in self else []
        else:
            items = list(self.values())
        if tag:
            items = [
                t for t in items
                if tag in ((t.get("tags", "") if isinstance(t, dict) else getattr(t, "tags", "")) or "").split(",")
            ]
        return items


def _torrent_fields(tor) -> dict:
    """把种子对象/映射归一为 qB sync 响应中 `torrents[hash]` 的**值**字段

    对齐真机: qB sync 响应的 hash 是 `torrents` 字典的**键**, 值内**不含** hash(与
    `torrents/info` 数组元素不同)。测试若在值里塞 hash, 会掩盖"校验样本需补 hash"这类
    真机 bug(2026-09-13 实际踩过)。缺失字段不入 dict —— 与 JSON 语义一致, 也让版本
    兼容校验能照常报缺失。
    """
    if isinstance(tor, dict):
        return {f: tor.get(f) for f in REQUIRED_TORRENT_FIELDS if f in tor and f != "hash"}
    return {f: getattr(tor, f) for f in REQUIRED_TORRENT_FIELDS if hasattr(tor, f) and f != "hash"}


class FakeClient:
    def __init__(self):
        self.tags = set()
        self.category = ""
        self.calls = []
        self.torrents = _FakeTorrents()  # 模拟客户端中的种子: hash -> info dict
        self.exported = b"TORRENT-DATA"  # torrents_export 返回值
        self.add_error = None  # 模拟重加失败
        self.files = []  # torrents_files 返回值(空 = 全部通过)
        self.files_map = {}  # hash -> 文件列表(分组测试用: 按种子区分文件列表)
        self.trackers_map = {}  # hash -> trackers 列表(强制覆盖; 强制汇报确认测试用)
        self.files_calls = 0  # torrents_files 调用计数(验证分组检查不再全量拉文件列表)
        self.sync_calls = 0  # sync_maindata 调用计数(验证增量同步路径)
        self.server_state = None  # 非空时随 sync 响应回传(模拟 qB 每轮都带 server_state)
        self.peers_map = {}  # hash -> peers 响应(sync_torrent_peers 替身; 未命中回空整包)
        self.peers_calls = 0  # sync_torrent_peers 调用计数
        self.transfer_upload_limit_value = 0  # transfer/uploadLimit 读数(bytes/s)
        self.transfer_download_limit_value = 0
        self.recheck_hashes_calls = []  # torrents_recheck 作用范围(hash 列表; calls 保持旧约定只记 None)
        self._sync_rid = 0  # 已发送的响应 ID(模拟 qB m_maindataLastSentID)
        self._sync_snapshot = {}  # 上次响应对应的全量数据(模拟 qB m_maindataSnapshot)

    def torrents_trackers(self, h):
        if h in self.trackers_map:
            return self.trackers_map[h]
        return [{"url": "https://tracker.hhanclub.net/announce.php"}]

    def torrents_files(self, h):
        self.files_calls += 1
        # 优先按 hash 返回文件列表(分组测试用), 否则返回共享 files
        if h in self.files_map:
            return self.files_map[h]
        return self.files

    def torrents_info(self, torrent_hashes=None, **kw):
        return self.torrents.info(torrent_hashes=torrent_hashes, **kw)

    def sync_maindata(self, rid=0, **kw):
        """模拟 /api/v2/sync/maindata(与 qB synccontroller.cpp 同语义)

        rid 与上次响应一致 -> 只含**变化种子**的**变化字段**(未变化种子不出现);
        删除的种子单列 torrents_removed; 基线缺失的新种子回全量字段;
        rid 为 0 或不匹配 -> full_update=true 且含全部种子全量字段。
        不写入 calls(避免影响既有调用序列断言), 用 sync_calls 计数。
        """
        self.sync_calls += 1
        cur = {h: _torrent_fields(t) for h, t in self.torrents.items()}
        if rid != 0 and rid == self._sync_rid:
            torrents = {}
            for h, fields in cur.items():
                prev = self._sync_snapshot.get(h)
                if prev is None:
                    torrents[h] = fields  # 新种子: 基线缺失 -> 全量字段
                    continue
                diff = {k: v for k, v in fields.items() if prev.get(k) != v}
                if diff:
                    torrents[h] = diff
            removed = [h for h in self._sync_snapshot if h not in cur]
            resp = {"rid": self._sync_rid + 1, "full_update": False}
            if torrents:
                resp["torrents"] = torrents
            if removed:
                resp["torrents_removed"] = removed
        else:
            resp = {"rid": self._sync_rid + 1, "full_update": True, "torrents": cur}
        self._sync_rid += 1
        self._sync_snapshot = cur
        if self.server_state is not None:
            resp["server_state"] = self.server_state  # qB 每轮(全量/增量)都带 server_state
        return resp

    def sync_torrent_peers(self, torrent_hash=None, rid=0, **kw):
        """单种子 peer 列表替身(qB sync/torrentPeers 同形状: 整包含 peers 键; 未命中回空整包)"""
        self.peers_calls += 1
        if torrent_hash in self.peers_map:
            return self.peers_map[torrent_hash]
        return {"peers": [], "rid": 0}

    def torrents_edit_category(self, name=None, save_path=None, **kw):
        self.calls.append(("edit_category", name, save_path))

    def torrents_remove_categories(self, categories=None, **kw):
        self.calls.append(("remove_categories", list(categories or [])))

    def torrents_create_tags(self, tags=None, **kw):
        self.tags.update(tags or [])
        self.calls.append(("create_tags", list(tags or [])))

    def transfer_upload_limit(self, **kw):
        return self.transfer_upload_limit_value

    def transfer_download_limit(self, **kw):
        return self.transfer_download_limit_value

    def transfer_set_upload_limit(self, limit=None, **kw):
        self.transfer_upload_limit_value = int(limit or 0)
        self.calls.append(("transfer_set_upload_limit", self.transfer_upload_limit_value))

    def transfer_set_download_limit(self, limit=None, **kw):
        self.transfer_download_limit_value = int(limit or 0)
        self.calls.append(("transfer_set_download_limit", self.transfer_download_limit_value))

    def torrents_export(self, torrent_hashes=None, torrent_hash=None, **kw):
        self.calls.append(("export", torrent_hash if torrent_hash is not None else torrent_hashes))
        return self.exported

    def torrents_delete(self, torrent_hashes=None, delete_files=False):
        self.calls.append(("delete", delete_files))
        hashes = [torrent_hashes] if isinstance(torrent_hashes, str) else (torrent_hashes or [])
        for h in hashes:
            self.torrents.pop(h, None)

    def torrents_add(
        self,
        torrent_files=None,
        torrent_paths=None,
        save_path=None,
        category=None,
        tags=None,
        upload_limit=None,
        download_limit=None,
        is_skip_checking=False,
        paused=False,
        is_paused=False,
        is_stopped=None,
        contentLayout=None,
        ratio_limit=None,
        seeding_time_limit=None,
        inactive_seeding_time_limit=None,
        share_limit_action=None,
        **kw
    ):
        # is_paused / is_stopped 是同一个 qB 参数(`stopped`)的两个名字(qbittorrent-api 取
        # `is_paused or is_stopped`); `is_stopped_raw` 原样记下**有没有显式传**(None = 没传),
        # 供测试区分"显式下发 stopped=false"与"省略该参数"(后者会吃 qB 会话默认值, 见
        # memory-bank/pitfalls/backend/qb-api.md 的添加选项一节)。
        stopped = bool(paused or is_paused or is_stopped)
        self.calls.append(
            (
                "add",
                {
                    "is_skip_checking": is_skip_checking,
                    "paused": stopped,
                    "is_stopped_raw": is_stopped,
                    "upload_limit": upload_limit,
                    "download_limit": download_limit,
                    "contentLayout": contentLayout,
                    "ratio_limit": ratio_limit,
                    "seeding_time_limit": seeding_time_limit,
                    "save_path": save_path,
                    "category": category,
                    "tags": tags,
                    "use_auto_torrent_management": kw.get("use_auto_torrent_management"),
                    "is_sequential_download": kw.get("is_sequential_download"),
                    "is_first_last_piece_priority": kw.get("is_first_last_piece_priority"),
                },
            )
        )
        if self.add_error:
            raise self.add_error
        # 新种子进入客户端(hash 固定 HASH123, 与 FakeTorrent 默认一致); 存对象而非 dict,
        # 保证 store.refresh / trackers_info 等按 .hash/.state 属性访问不崩
        self.torrents["HASH123"] = FakeTorrent(
            hash="HASH123",
            state="pausedUP" if stopped else "stalledUP",
            save_path=save_path or r"R:\Downloads",
            category=category or "",
            tags=tags or "",
        )
        # ⚠ 只模拟 **Web API < 2.14.0** 的文本形态("Ok."/"Fails."); 真机 qB 5.2+(API 2.14.0 起)
        #   回的是 JSON 元数据 `{success_count, failure_count, pending_count, added_torrent_ids}`,
        #   本替身**回不出**该形态 —— 这正是"添加成功却报失败"能溜到线上的口子(2026-09-24)。
        #   新形态的守阵由 test_web.py::test_add_torrent_receipt_and_optional_flags 直接用
        #   库内 TorrentsAddedMetadata 顶替返回值来钉(见 memory-bank/pitfalls/testing/stubs-sim.md)。
        return "Ok."

    def torrents_add_tags(self, tags=None, torrent_hashes=None):
        self.tags.update(tags)
        self.calls.append(("add_tags", tags))

    def torrents_remove_tags(self, tags=None, torrent_hashes=None):
        self.tags.difference_update(tags)
        self.calls.append(("remove_tags", tags))

    def torrents_tags(self):
        return list(self.tags)

    def torrents_delete_tags(self, tags=None):
        # 模拟真实行为: 删除标签定义并同时从所有种子移除
        tags = set(tags or [])
        self.tags.difference_update(tags)
        for tor in self.torrents.values():
            cur = (tor.get("tags", "") if isinstance(tor, dict) else getattr(tor, "tags", "")) or ""
            if cur:
                remain = [t.strip() for t in cur.split(",") if t.strip() and t.strip() not in tags]
                new = ",".join(remain)
                if isinstance(tor, dict):
                    tor["tags"] = new
                else:
                    tor.tags = new
        self.calls.append(("delete_tags", tags))

    def torrents_categories(self):
        return {}

    def torrents_create_category(self, name=None, save_path=None, **kw):
        # 兼容旧断言: 未传 save_path 时保持二元素 calls 形状
        if save_path:
            self.calls.append(("create_category", name, save_path))
        else:
            self.calls.append(("create_category", name))

    def torrents_set_category(self, category=None, torrent_hashes=None):
        self.category = category
        self.calls.append(("set_category", category))

    def torrents_start(self, torrent_hashes=None):
        self.calls.append(("start", None))

    def torrents_stop(self, torrent_hashes=None):
        self.calls.append(("stop", None))

    def torrents_pause(self, torrent_hashes=None):
        # 与 start/stop 记 None 不同: 记 hash 列表(Web 命令测试需断言"整组/单种"作用范围)
        self.calls.append(("pause", torrent_hashes))

    def torrents_resume(self, torrent_hashes=None):
        self.calls.append(("resume", torrent_hashes))

    def torrents_recheck(self, torrent_hashes=None):
        self.calls.append(("recheck", None))
        # hash 级作用范围另记(Web 命令/批量测试断言用; calls 里的 ("recheck", None) 约定被大量既有断言依赖)
        self.recheck_hashes_calls.append(torrent_hashes)

    def torrents_reannounce(self, torrent_hashes=None):
        self.calls.append(("reannounce", None))

    def torrents_set_upload_limit(self, torrent_hashes=None, limit=None):
        self.calls.append(("set_upload_limit", limit))

    def torrents_set_download_limit(self, torrent_hashes=None, limit=None):
        self.calls.append(("set_download_limit", limit))

    def torrents_set_location(self, torrent_hashes=None, location=None):
        self.calls.append(("set_location", location))

    # ---- WEB UI 二轮写命令替身(snake 命名与 QbApi 调用一致; 记 calls 供断言) ----

    def torrents_set_super_seeding(self, enable=None, torrent_hashes=None):
        self.calls.append(("set_super_seeding", enable))

    def torrents_set_force_start(self, enable=None, torrent_hashes=None):
        self.calls.append(("set_force_start", enable))

    def torrents_set_share_limits(
        self, ratio_limit=None, seeding_time_limit=None, inactive_seeding_time_limit=None, torrent_hashes=None
    ):
        self.calls.append(("set_share_limits", (ratio_limit, seeding_time_limit, inactive_seeding_time_limit)))

    def torrents_rename(self, torrent_hash=None, new_torrent_name=None):
        self.calls.append(("rename", (torrent_hash, new_torrent_name)))

    def torrents_set_auto_management(self, enable=None, torrent_hashes=None):
        self.calls.append(("set_auto_tmm", enable))

    def torrents_top_priority(self, torrent_hashes=None):
        self.calls.append(("queue_top", torrent_hashes))

    def torrents_increase_priority(self, torrent_hashes=None):
        self.calls.append(("queue_up", torrent_hashes))

    def torrents_decrease_priority(self, torrent_hashes=None):
        self.calls.append(("queue_down", torrent_hashes))

    def torrents_bottom_priority(self, torrent_hashes=None):
        self.calls.append(("queue_bottom", torrent_hashes))

    def torrents_add_trackers(self, torrent_hash=None, urls=None):
        self.calls.append(("add_trackers", (torrent_hash, list(urls or []))))

    def torrents_edit_tracker(self, torrent_hash=None, original_url=None, new_url=None):
        self.calls.append(("edit_tracker", (torrent_hash, original_url, new_url)))

    def torrents_remove_trackers(self, torrent_hash=None, urls=None):
        self.calls.append(("remove_trackers", (torrent_hash, list(urls or []))))

    def torrents_file_priority(self, torrent_hash=None, file_ids=None, priority=None):
        self.calls.append(("file_priority", (torrent_hash, list(file_ids or []), priority)))

    def torrents_rename_file(self, torrent_hash=None, old_path=None, new_path=None):
        self.calls.append(("rename_file", (torrent_hash, old_path, new_path)))

    def torrents_rename_folder(self, torrent_hash=None, old_path=None, new_path=None):
        self.calls.append(("rename_folder", (torrent_hash, old_path, new_path)))


# ---------- 本地假 qBittorrent Web API 服务 ----------
class FakeQbServer:
    """本地假 qBittorrent Web API 服务(标准库 http.server, 后台线程)

    用途: 让测试用**真实** qbittorrentapi Client + 真实 requests/urllib3 栈走完整 HTTP 往返,
    覆盖单元替身(FakeClient)无法暴露的行为 —— 例如 requests Session 的 trust_env 是否真的生效、
    库在首次请求时重建 Session 会不会丢掉我们的设置、sync/maindata 的 rid 增量语义能否被真机栈
    完整驱动。

    数据来源复用 `FakeClient`(单一口径): 服务端只做 HTTP 适配, 不重复实现业务语义。
    监听 127.0.0.1 的随机空闲端口, 用 with 语句保证线程与 socket 回收。

        with FakeQbServer() as srv:
            cfg.qbittorrent = QbittorrentConfig(host="127.0.0.1", port=srv.port)
            ...
            srv.hits("sync/maindata")   # 端点命中次数(可断言请求量/节流效果)

    已实现端点(未列出的 GET -> 404 JSON, 未列出的 POST -> "Ok."):
      POST auth/login;  HEAD 任意路径;  GET app/webapiVersion|app/version;
      GET sync/maindata(rid 增量);  GET torrents/info|tags|categories|files|trackers;
      GET transfer/uploadLimit|downloadLimit;  POST transfer/setUploadLimit|setDownloadLimit

    abort=True: 收到任何请求即断开(不写响应) —— 模拟 qB 中途断开, 用于确定地产生
      `APIConnectionError`(实测回环下约 0.7s; 比指向"死端口"快得多, 后者在部分环境
      是超时等待, 库内超时重试会拖垮测试)。
    """
    WEB_API_VERSION = "2.11.4"  # >= 库内全部 version_introduced 门槛, 避免假服务触发"端点未实现"
    QBIT_VERSION = "5.0.3"
    _PREFIX = "/api/v2/"

    def __init__(self, client=None, abort: bool = False):
        self.client = client or FakeClient()
        self.abort = abort  # 见类 docstring: 收到请求即断开(制造 APIConnectionError)
        self.requests = []  # 请求台账 [(method, path, ts)]
        self.upload_limit = 0  # transfer/uploadLimit 读数(bytes/s)
        self.download_limit = 0
        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), self._make_handler())
        self.host, self.port = self._httpd.server_address

    # ---------- 生命周期 ----------
    def start(self):
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()
        self._thread.join(timeout=5)

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc):
        self.stop()

    # ---------- 请求台账 ----------
    def hits(self, endpoint: str) -> int:
        """路径包含 endpoint 的命中次数(断言请求量/节流效果用)"""
        return sum(1 for _, path, _ in self.requests if endpoint in path)

    def torrents_info(self) -> list:
        """种子信息数组(与真机 torrents/info 一致: 每元素含 hash 字段)"""
        return [{"hash": h, **_torrent_fields(t)} for h, t in self.client.torrents.items()]

    def _make_handler(self):
        server = self

        class _Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args):  # 静默: 默认会往 stderr 打请求日志(测试输出噪声)
                pass

            def _send(self, body: str, content_type: str, status: int = 200) -> None:
                payload = body.encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def _json(self, obj, status: int = 200) -> None:
                self._send(json.dumps(obj), "application/json", status)

            def _route_and_query(self):
                """记台账并返回 (去除 /api/v2/ 前缀的端点, 查询参数)"""
                u = urlparse(self.path)
                route = u.path[len(server._PREFIX):].rstrip("/") if u.path.startswith(server._PREFIX) else u.path
                server.requests.append((self.command, self.path, time.time()))
                return route, parse_qs(u.query)

            def _body(self) -> dict:
                """读尽请求体(keep-alive 必须): 库以 form-encoded 发送, 兼容 JSON"""
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length).decode("utf-8") if length else ""
                if not raw:
                    return {}
                if raw.lstrip().startswith("{"):
                    return json.loads(raw)
                return {k: v[0] for k, v in parse_qs(raw).items()}

            def do_HEAD(self):
                # 库的 build_base_url() 先 HEAD 探测 http/https; 真机 qB 同样支持 HEAD
                self._route_and_query()
                self.send_response(200)
                self.send_header("Content-Length", "0")
                self.end_headers()

            def do_GET(self):
                self._dispatch("GET")

            def do_POST(self):
                self._dispatch("POST")

            def _dispatch(self, method: str):
                """按路由分派(**不按方法区分**读端点: 库对 info/files/trackers/maindata 用 POST,
                对 tags/categories/transfer 用 GET, 真机 qB 两者都接受)

                参数来源合并 body(form)与 query: POST 端点(如 maindata 的 rid、files 的 hash)
                把参数放在请求体, GET 端点放在 query。
                """
                if server.abort:
                    self._body()  # 读尽请求体后直接断开(不写响应) -> 客户端报连接错误
                    self.close_connection = True
                    return
                route, query = self._route_and_query()
                params = {**self._body(), **{k: v[0] for k, v in query.items()}}
                if route == "auth/login":
                    return self._send("Ok.", "text/plain")
                if route == "app/webapiVersion":
                    return self._send(server.WEB_API_VERSION, "text/plain")
                if route == "app/version":
                    return self._send(server.QBIT_VERSION, "text/plain")
                if route == "sync/maindata":
                    return self._json(server.client.sync_maindata(rid=int(params.get("rid") or 0)))
                if route == "torrents/info":
                    return self._json(server.torrents_info())
                if route == "torrents/tags":
                    return self._json(server.client.torrents_tags())
                if route == "torrents/categories":
                    return self._json(server.client.torrents_categories())
                if route == "torrents/files":
                    return self._json([_file_to_dict(f) for f in server.client.torrents_files(params.get("hash"))])
                if route == "torrents/trackers":
                    return self._json(server.client.torrents_trackers(params.get("hash")))
                if route == "transfer/uploadLimit":
                    return self._send(str(server.upload_limit), "text/plain")
                if route == "transfer/downloadLimit":
                    return self._send(str(server.download_limit), "text/plain")
                if route == "transfer/setUploadLimit":
                    server.upload_limit = int(params.get("limit") or 0)
                    return self._send("Ok.", "text/plain")
                if route == "transfer/setDownloadLimit":
                    server.download_limit = int(params.get("limit") or 0)
                    return self._send("Ok.", "text/plain")
                if method == "POST":
                    return self._send("Ok.", "text/plain")  # 其余写操作统一 "Ok."(与 qB 多数端点一致)
                return self._json({"error": f"unknown endpoint: {self.path}"}, status=404)

        return _Handler


# ---------- 模拟种子(TorrentDictionary 鸭子) ----------
class FakeTorrent:
    """模拟 qB TorrentDictionary 对象(变量命名: tor), 鸭子类型兼容 TorrentRecord/TorrentStore

    快照字段与 TorrentRecord 一致(含 dl_limit/up_limit), 补派生属性与记录级惰性接口:
      tags_set / log_repr / tracker_name + trackers_info(client)/tracker_urls(client)/files(client)。
    """
    def __init__(self, **kw):
        self.hash = kw.get("hash", "HASH123")
        self.name = kw.get("name", "Test")
        self.save_path = kw.get("save_path", r"R:\Downloads")
        self.content_path = kw.get("content_path", r"R:\Downloads\Test")
        self.size = kw.get("size", 100 * 1024**2)
        self.total_size = kw.get("total_size", 100 * 1024**2)
        self.tags = kw.get("tags", "")
        self.category = kw.get("category", "")
        self.state = kw.get("state", "stalledUP")
        self.downloaded = kw.get("downloaded", 100 * 1024**2)
        self.uploaded = kw.get("uploaded", 0)
        self.dlspeed = kw.get("dlspeed", 0)
        self.upspeed = kw.get("upspeed", 0)
        self.seeding_time = kw.get("seeding_time", 0)
        self.ratio = kw.get("ratio", 0.0)
        # 未显式给 amount_left 时按下载状态推导(与真实 qB 一致: 未下完剩余字节 > 0), 供 HR 完成判定
        self.amount_left = kw.get("amount_left", max(0, self.total_size - self.downloaded))
        self.completed = kw.get("completed", 0)
        self.progress = kw.get("progress", 0.0)
        self.dl_limit = kw.get("dl_limit", 0)
        self.up_limit = kw.get("up_limit", 0)
        # 添加时间(unix 秒): Web 分组视图默认排序依据; 默认取固定值保证测试确定性
        self.added_on = kw.get("added_on", 1700000000)
        # TorrentDictionary 扩展字段(skip-checking 重加时逐项回传; 默认 None/False 即不传)
        self.seq_dl = kw.get("seq_dl", False)
        self.f_l_piece_prio = kw.get("f_l_piece_prio", False)
        self.ratio_limit = kw.get("ratio_limit", None)
        self.seeding_time_limit = kw.get("seeding_time_limit", None)
        self.inactive_seeding_time_limit = kw.get("inactive_seeding_time_limit", None)
        self.share_limit_action = kw.get("share_limit_action", None)
        self.tracker_conf = kw.get("tracker_conf", None)
        self.tor = self  # 原始 TorrentDictionary(自身), 提供 client 兼容访问
        self._tags_set = None
        self._state_enum = None
        self._trackers_info = None
        self._files = None
        # 错误原因(WebUI 状态列): 与 TorrentRecord 同名的非快照字段, 由主循环预取写入
        self.tracker_error_msg = kw.get("tracker_error_msg", "")
        self.tracker_error_ts = kw.get("tracker_error_ts", 0.0)
        # 扩展快照字段(与 TorrentRecord 扩展 slots 同默认值): 种子平铺视图/详情读取用;
        # kw 可覆盖, 未提及取 qB 哨兵默认(与 TorrentRecord 一致)
        _ext_defaults = {
            "downloaded_session": 0,
            "uploaded_session": 0,
            "eta": 8640000,
            "time_active": 0,
            "last_activity": -1,
            "availability": 0.0,
            "num_seeds": 0,
            "num_leechs": 0,
            "num_complete": 0,
            "num_incomplete": 0,
            "tracker": "",
            "trackers_count": 0,
            "connections_count": 0,
            "connections_limit": 0,
            "reannounce_in": 0,
            "reannounce": 0,
            "max_ratio": -1.0,
            "max_seeding_time": -1,
            "max_inactive_seeding_time": -1,
            "magnet_uri": "",
            "infohash_v1": "",
            "infohash_v2": "",
            "private": False,
            "comment": "",
            "created_by": "",
            "creation_date": 0,
            "has_metadata": False,
            "piece_size": 0,
            "pieces_have": 0,
            "pieces_num": 0,
            "auto_tmm": False,
            "download_path": "",
            "root_path": "",
            "force_start": False,
            "super_seeding": False,
            "priority": 0,
            "completion_on": -1,
            "seen_complete": -1,
            "total_wasted": 0,
            "popularity": 0.0,
            "has_tracker_error": False,
            "has_tracker_warning": False,
            "has_other_announce_error": False,
        }
        for _f, _v in _ext_defaults.items():
            setattr(self, _f, kw[_f] if _f in kw else _v)

    def to_dict(self) -> dict:
        """全字段导出(真记录是 `TorrentRecord.to_dict`: 快照字段 + `_raw` 前向兼容字段)

        ❗没有这个方法时桩服务的详情端点 `/api/torrents/{hash}` **恒 500**
        (`'FakeTorrent' object has no attribute 'to_dict'`, 2026-09-19 实测), 于是整条依赖详情的
        链路在冒烟里从未被覆盖: 详情抽屉、限速/分享率/移动/重命名对话框、以及"复制磁力"
        (magnet_uri 只在平铺 SEED_ITEM 与详情里, 成员索引没有该字段 —— 见 app.js copyTorrentInfo)。
        与真实现一致: 惰性缓存槽(下划线开头)与 tracker_conf 不进导出(后者是配置对象, 不可 JSON 化)。
        """
        skip = {"tor", "tracker_conf"}
        return {k: v for k, v in vars(self).items() if not k.startswith("_") and k not in skip and not callable(v)}

    @property
    def state_enum(self):
        """模拟真实客户端: 由 state 字符串动态构造 TorrentState(与 qB 版本无关的状态类别判定)

        不缓存: 测试常直接改 .state 属性后重执行动作, 缓存会导致 state_enum 不同步。
        """
        if TorrentState is None:
            return None
        try:
            return TorrentState(self.state)
        except ValueError:
            return TorrentState.UNKNOWN

    @property
    def tags_set(self) -> frozenset:
        # 不缓存: 测试常直接改 .tags 属性后重执行动作
        return frozenset(p.strip() for p in (self.tags or "").split(",") if p.strip())

    @property
    def tracker_name(self) -> str:
        """返回 tracker 名称(从 tracker_conf 或 tracker_url 派生), 主要用于log"""
        if self.tracker_conf is not None:
            if self.tracker_conf.tags is not None and len(self.tracker_conf.tags) > 0:
                return self.tracker_conf.tags[0]
            return self.tracker_conf.name
        return "Unknown"

    @property
    def log_repr(self) -> str:
        return f"'{self.name}' [{self.tracker_name}] ({self.hash[:8]})"

    # ---------- HR 条件(2026-09 迁到 TorrentRecord, FakeTorrent 鸭子兼容补) ----------

    def check_hr_condition(self) -> bool:
        if not self.tracker_conf.hr:
            return False
        hr = self.tracker_conf.hr
        cond_type, cond_value = hr.condition
        if cond_type == "dlratio":
            if self.total_size == 0:  # 无实际数据量, 辅种排除兜底, 不视为触发
                return False
            if (self.downloaded / self.total_size) >= cond_value:
                return True
        elif cond_type == "dlsize":
            if self.downloaded >= cond_value:
                return True
        # 未达触发量但已完整下载完(下载量 >= 种子大小)的种子同样视为触发(小种子边界)
        return self.total_size > 0 and self.downloaded >= self.total_size

    def check_hr_satisfied(self) -> bool:
        if not self.tracker_conf.hr:
            return False
        hr = self.tracker_conf.hr
        if not self.check_hr_condition():
            return False
        seeding_ok = self.seeding_time >= (hr.required_seeding_time + hr.extra_seeding_time)
        ratio_ok = hr.required_share_ratio > 0 and (self.ratio or 0) >= hr.required_share_ratio
        return seeding_ok or ratio_ok

    # ---------- 记录级惰性接口(与 TorrentRecord 一致; client None -> RuntimeError) ----------

    # 快照字段(与 TorrentRecord._SNAPSHOT_FIELDS 一致; update_from 时逐字段复制)
    _SNAPSHOT_FIELDS = (
        "name",
        "save_path",
        "content_path",
        "size",
        "total_size",
        "tags",
        "category",
        "state",
        "downloaded",
        "uploaded",
        "seeding_time",
        "ratio",
        "amount_left",
        "completed",
        "progress",
        "dl_limit",
        "up_limit",
        "added_on",
    )

    def apply_delta(self, patch):
        """用 patch 更新快照字段, 返回变化字段名集合; 与 TorrentRecord.apply_delta 同语义

        Mapping 源(qB sync 响应/测试 dict)只遍历其键; 普通对象源按 REQUIRED_TORRENT_FIELDS
        收集属性。FakeTorrent 无 `_raw`(非快照字段本就是真实属性), 故仅处理快照字段。
        """
        changed = set()
        if isinstance(patch, Mapping):
            items = patch.items()
        else:
            items = ((f, getattr(patch, f, None)) for f in REQUIRED_TORRENT_FIELDS)
        for f, v in items:
            if v is None or f not in self._SNAPSHOT_FIELDS:
                continue
            cur = getattr(self, f, None)
            if cur == v:
                continue
            setattr(self, f, v)
            if f not in _VIEW_FIELDS:
                changed.add(f)
            elif f not in _VIEW_QUANTUM or view_field_value(f, cur) != view_field_value(f, v):
                changed.add(f)
        self._tags_set = None
        self._state_enum = None
        self._trackers_info = None
        self._files = None
        return frozenset(changed)

    def trackers_info(self, client):
        if self._trackers_info is None:
            if client is None:
                raise RuntimeError("TorrentStore 未绑定 client")
            self._trackers_info = list(client.torrents_trackers(self.hash) or [])
        return self._trackers_info

    def invalidate_trackers(self):
        """tracker 写操作后失效惰性缓存(与 TorrentRecord.invalidate_trackers 鸭子兼容)"""
        self._trackers_info = None

    def tracker_urls(self, client):
        return [t.get("url") for t in self.trackers_info(client) if t.get("url")]

    def files(self, client):
        if self._files is None:
            if client is None:
                raise RuntimeError("TorrentStore 未绑定 client")
            self._files = list(client.torrents_files(self.hash) or [])
        return self._files


# ---------- 模拟 TrackerConfig ----------
class FakeTracker:
    def __init__(
        self,
        name,
        hr=None,
        rules=None,
        remove_similar_tags=False,
        upload_speed_limit=0,
        download_speed_limit=0,
        groups=None,
    ):
        self.name = name
        self.domains = ["tracker.hhanclub.net"]
        self.tags = ["HHan"]
        self.remove_tags = []
        self.groups = groups or []  # 站点分组(配置层声明, tracker_group 条件匹配来源)
        self.hr = hr  # HRRule 或 None
        self.rules = rules or []
        self.remove_similar_tags = remove_similar_tags
        self.upload_speed_limit = upload_speed_limit  # 字节/秒; 0 = 不限速(等价 UNLIMITED_SPEED)
        self.download_speed_limit = download_speed_limit


# ---------- 模拟 Config ----------
class FakeConfig:
    qbittorrent = QbittorrentConfig(host="127.0.0.1", port=16585, username="u", password="p")
    trackers = {"HHan": FakeTracker("HHan")}
    state_file = ""  # 由测试设置
    interval = 60  # QbManager 主刷新任务 interval(测试不触发 refresh)
    main_tick = 1.0
    sync_interval = 1.5  # 同步线节拍(状态刷新); 与 Config 默认一致
    state_save_interval = 120.0  # 状态周期落盘间隔(秒); 与 Config 默认一致(0=关闭周期落盘)
    max_tasks_per_tick = 20
    logging = LoggingConfig(
        level="WARNING", file="", max_bytes="10MiB", format="%(asctime)s [%(levelname)s] %(message)s"
    )
    rules_config = {}  # 规则集原始配置(由 make_manager 设置)
    check_missing_files = False
    remove_similar_tags = False
    add_episode_tags = AddEpisodeTagsConfig()  # 默认 disabled; 测试按需赋值 AddEpisodeTagsConfig(enabled=True, ...)
    hr = HRRule()  # 全局 HR 默认输出设置
    skip_checking_tag = "zSkipChecked"  # 跳检成功标签默认名(与 Config 默认一致; 测试按需赋值, ""=禁用)
    delete_tags = []  # 全局: 彻底删除的标签格式(支持正则)
    delete_tags_if_has_no_torrents = []  # 全局: 彻底删除无种子的标签格式(支持正则)
    grouping = GroupingConfig(enabled=False, missing_tag="MISSING")  # 种子分组管理(默认关闭)
    global_speed_limit_curve = None  # 全局限速曲线(未启用; 与 Config 默认一致, 测试按需赋值)
    notify = NotifyConfig()  # 主动通知(默认 disabled)
    web = WebConfig()  # WEB UI(默认 disabled)
    # HR 在线核实(M2 起 QbManager 会读它): 默认关 = 不建端点、不建取数线程, 与真实默认一致
    hr_check = HrCheckConfig()
    data_dir = ""  # 由测试按需设置(HR 站点文件目录从它派生)


def _hr_rule(**kw) -> HRRule:
    """构造 HRRule, 默认匹配旧 '3D@70%+12H' 语义"""
    base = dict(
        required_seeding_time=3 * 86400,
        required_seeding_time_raw="3D",
        required_share_ratio=0.0,
        extra_seeding_time=12 * 3600,
        condition=("dlratio", 0.7),
        add_tag="",
        add_category="!!HR${required_seeding_time}!!",
        overwrite_category=False,
        add_tag_for_satisfied="",
        add_category_for_satisfied="--HR${required_seeding_time}--",
        overwrite_category_for_satisfied=False,
    )
    base.update(kw)
    return HRRule(**base)


def make_manager(state_file, tracker_rules=None, tracker_kw=None):
    cfg = FakeConfig()
    cfg.state_file = state_file
    kw = dict(hr=_hr_rule(), rules=tracker_rules)
    kw.update(tracker_kw or {})
    cfg.trackers = {"HHan": FakeTracker("HHan", **kw)}
    config_dict = {
        "example_rules":
            {
                "add_site_tag":
                    {
                        "enabled": True,
                        "execute_once": "never",
                        "conditions": [{
                            "trackers": "HHan"
                        }],
                        "actions": [{
                            "add_tags": ["HHan", "seed-${required_seeding_time}"]
                        }],
                        "stop_following_rules_if": "never",
                    },
                "hr_done":
                    {
                        "enabled": True,
                        "execute_once": "daily",
                        "conditions": [{
                            "state": "is_complete&is_uploading"
                        }, {
                            "hr": "satisfied"
                        }],
                        "actions": [{
                            "add_category": {
                                "format": "HR-DONE",
                                "overwrite": False
                            }
                        }],
                        "stop_following_rules_if": "conditions-met",
                    },
                "stop_low_ratio":
                    {
                        "enabled": True,
                        "execute_once": "once",
                        "conditions": [{
                            "upload_ratio": "<0.5"
                        }],
                        "actions": [{
                            "stop": True
                        }, {
                            "add_tags": ["low-ratio"]
                        }],
                        "stop_following_rules_if": "action-failed",
                    },
            }
    }
    cfg.rules_config = config_dict
    mgr = QbManager("", config=cfg, no_lock=True)  # 测试不持锁
    mgr._load_rules()  # run() 中才自动加载; 测试直接构造后需手动加载规则
    return mgr


def _fake_file(name, size):
    return SimpleNamespace(name=name, size=size)


def _file_to_dict(f) -> dict:
    """文件条目 -> JSON 可序列化 dict

    真机 /torrents/files 返回对象数组(JSON), 而本地替身 _fake_file 是 SimpleNamespace:
    json.dumps 遇到它会抛 TypeError -> HTTP 连接被无响应关闭(客户端报 RemoteDisconnected)。
    FakeQbServer 对外必须是真机语义, 故出口统一转 dict。
    """
    if isinstance(f, Mapping):
        return dict(f)
    return dict(vars(f))


def make_ctx(mgr, tor, client, dry_run=False):
    """构造 RuleContext(规则动作测试辅助)

    新架构: RuleContext 第 4 参为 hash 字符串; ctx.torrent = mgr.store.get(hash)(无 None 兜底)。
    因此本函数保证: ①client 已绑定到 mgr(动作经 ctx.api 调 manager.api Facade) ②store 中已有该
    tor 的记录, 且记录对象即 tor 本身(对象身份直写: 后续修改 tor 属性对 ctx.torrent 实时可见)
    ③tracker_conf 已匹配(等效 _refresh_torrents 对新增种子的处理; ${required_seeding_time} 等依赖它)。
    """
    # ① client 绑定: 动作走 ctx.api -> manager.api(QbApi), 未绑 client 时自动绑定
    if getattr(mgr, "_client", None) is None:
        mgr.client = client
    # ③ tracker_conf 匹配(未显式设置时; 模拟新增种子进 refresh 后由 _match_tracker_conf 赋值)
    if tor.tracker_conf is None:
        try:
            tor.tracker_conf = mgr._match_tracker_conf(tor)
        except Exception:
            tor.tracker_conf = None
    # ② 对象身份注入: by_hash[h] is tor(已存在则原地替换/更新)
    existing = mgr.store.by_hash.get(tor.hash)
    if existing is not tor:
        if existing is not None and not isinstance(existing, FakeTorrent):
            existing.apply_delta(tor)  # 真 TorrentRecord: 应用字段变化
        mgr.store.by_hash[tor.hash] = tor  # 对象身份直写(供改 tor 属性后实时可见)
    return RuleContext(mgr, client, mgr.config, tor.hash, dry_run=dry_run)


def seed_store(mgr, torrents=None):
    """将种子灌入 mgr.store(对象身份直写: 记录即传入对象, 后续修改实时可见)

    与 store.refresh 语义一致(首轮全部视为新增, 后续 diff), 但保留对象身份而非复制字段;
    返回 (added, removed)。
    """
    if torrents is None:
        torrents = list(mgr.client.torrents.values())
    store = mgr.store
    old_hashes = set(store.by_hash)
    new_by_hash: dict = {}
    for tor in torrents:
        if tor is None or isinstance(tor, dict):
            continue  # 无快照形状的对象(如测试手动注入的 dict)不参与
        h = getattr(tor, "hash", None)
        if not h:
            continue
        new_by_hash[h] = tor
    added = [h for h in new_by_hash if h not in old_hashes]
    removed = [h for h in old_hashes if h not in new_by_hash]
    store.by_hash = new_by_hash
    return added, removed
