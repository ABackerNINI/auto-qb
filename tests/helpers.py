"""测试公共组件: 模拟 qB 客户端 / 种子 / 配置 + 构造辅助 + 本地假 qB 服务

由 pytest.ini 的 pythonpath=src 处理 src 导入, 无需 sys.path 处理。
"""
import copy
import json
import logging
import os
import tempfile
import threading
import time
from collections.abc import Mapping
from typing import NamedTuple
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

from auto_qb.config import (
    GroupingConfig,
    HRRule,
    LoggingConfig,
    NotifyConfig,
    QbittorrentConfig,
    WebConfig,
)  # noqa: E402
from auto_qb.config.models import AddEpisodeTagsConfig  # noqa: E402  (重导出面已收敛, 模型类直引 models)
from auto_qb.config.models import RelocateConfig  # noqa: E402  (整组迁移, 计划 26-10-18-1604 §3.7; 默认全关)
from auto_qb.config.models import TrafficSourceConfig  # noqa: E402  (包 __init__ 未导出)
from auto_qb.config.models import HrCheckConfig  # noqa: E402  (包 __init__ 未导出 HR 在线核实配置类)
from auto_qb.core.qbmanager import QbManager  # noqa: E402
from auto_qb.core.traffic_source import agent  # noqa: E402
from auto_qb.rules import ActionResult, RuleContext  # noqa: E402
from auto_qb.torrents import (  # noqa: E402
    _SNAPSHOT_FIELDS,
    REQUIRED_TORRENT_FIELDS,
    _VIEW_FIELDS,
    _VIEW_QUANTUM,
    view_field_value,
)

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
        # 分类定义 name -> info(与 self.tags 对称的"客户端侧全局定义"; 默认空 = 无分类,
        # 既有用例行为逐字不变)。桩服务 scripts/ui_harness.py 按合成种子灌真实候选,
        # 好让 /api/categories 在冒烟/截图里不再是恒空态。
        self.categories = {}
        self.calls = []
        self.torrents = _FakeTorrents()  # 模拟客户端中的种子: hash -> info dict
        self.exported = b"TORRENT-DATA"  # torrents_export 返回值
        self.add_error = None  # 模拟重加失败
        self.files = []  # torrents_files 返回值(空 = 全部通过)
        self.files_map = {}  # hash -> 文件列表(分组测试用: 按种子区分文件列表)
        self.trackers_map = {}  # hash -> trackers 列表(强制覆盖; 强制汇报确认测试用)
        self.files_calls = 0  # torrents_files 调用计数(验证分组检查不再全量拉文件列表)
        self.info_calls = 0  # torrents_info 调用计数(验证 recheck 轮询期零 API 直查, 纯快照读)
        self.sync_calls = 0  # sync_maindata 调用计数(验证增量同步路径)
        self.server_state = None  # 非空时随 sync 响应回传(模拟 qB 每轮都带 server_state)
        self.peers_map = {}  # hash -> peers 响应(sync_torrent_peers 替身; 未命中回空整包)
        self.peers_calls = 0  # sync_torrent_peers 调用计数
        self.transfer_upload_limit_value = 0  # transfer/uploadLimit 读数(bytes/s)
        self.transfer_download_limit_value = 0
        self.alt_up_limit_value = 0  # app/preferences alt_up_limit 读数(bytes/s, 0 = 不限)
        self.alt_dl_limit_value = 0  # app/preferences alt_dl_limit 读数(bytes/s, 0 = 不限)
        self.speed_limits_mode_value = 0  # transfer/speedLimitsMode 读数(0 = 主速度 / 1 = 备用)
        self.recheck_hashes_calls = []  # torrents_recheck 作用范围(hash 列表; calls 保持旧约定只记 None)
        # torrents_reannounce 作用范围(hash 列表; calls 保持旧约定只记 ("reannounce", None))——
        # 投递收敛(只投活跃子集, 2026-10-10)的断言必须看得到具体 hash, 同 recheck_hashes_calls 模式
        self.reannounce_hashes_calls = []
        # 限速/移动三个 qB 方法的作用范围((方法名, hash 列表); calls 保持旧二元组形状不动,
        # 单独平行记录供 bulk"单次调用传全 hashes"断言用 —— 同 recheck_hashes_calls 的模式)
        self.limit_location_hashes_calls = []
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
        self.info_calls += 1
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

    def app_preferences(self, **kw):
        # 只暴露本测试关心的 alt_* 键(真实 qB 返回全量偏好, 调用方按键取用)
        return {"alt_up_limit": self.alt_up_limit_value, "alt_dl_limit": self.alt_dl_limit_value}

    def app_set_preferences(self, json=None, **kw):
        prefs = json or {}
        if "alt_up_limit" in prefs:
            self.alt_up_limit_value = int(prefs["alt_up_limit"])
        if "alt_dl_limit" in prefs:
            self.alt_dl_limit_value = int(prefs["alt_dl_limit"])
        self.calls.append(("app_set_preferences", sorted(prefs.keys())))

    def transfer_speed_limits_mode(self, **kw):
        return self.speed_limits_mode_value

    def transfer_toggle_speed_limits_mode(self, **kw):
        self.speed_limits_mode_value = 1 - int(self.speed_limits_mode_value)
        self.calls.append(("transfer_toggle_speed_limits_mode", self.speed_limits_mode_value))

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
        # 保真(加固, report 26-10-11-2017 §5/§6.4): qB 在 is_skip_checking=True 时把全部块视为
        #   有效 ⇒ 完成。旧替身恒定 progress=0, 让"跳检重加后快照仍说 0%"这条脱节在单测里天然
        #   不可见(amount_left 默认已是 0, 无需另设)。
        self.torrents["HASH123"] = FakeTorrent(
            hash="HASH123",
            state="pausedUP" if stopped else "stalledUP",
            save_path=save_path or r"R:\Downloads",
            category=category or "",
            tags=tags or "",
            progress=1.0 if is_skip_checking else 0.0,
        )
        # WARN: 只模拟 **Web API < 2.14.0** 的文本形态("Ok."/"Fails."); 真机 qB 5.2+(API 2.14.0 起)
        #   回的是 JSON 元数据 `{success_count, failure_count, pending_count, added_torrent_ids}`,
        #   本替身**回不出**该形态 —— 这正是"添加成功却报失败"能溜到线上的口子(2026-09-24)。
        #   新形态的守阵由 test_web_admin.py::test_add_torrent_receipt_and_optional_flags 直接用
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
        return dict(self.categories)

    def torrents_create_category(self, name=None, save_path=None, **kw):
        # 兼容旧断言: 未传 save_path 时保持二元素 calls 形状
        if save_path:
            self.calls.append(("create_category", name, save_path))
        else:
            self.calls.append(("create_category", name))

    def torrents_set_category(self, category=None, torrent_hashes=None):
        self.category = category
        self.calls.append(("set_category", category))

    def _apply_paused_state(self, torrent_hashes, *, paused):
        """替身保真: 真实翻转客户端侧种子的暂停轴 state(plan 26-10-13-0540 S0-P3)。

        旧替身四个暂停轴方法只记 calls、不翻 state ⇒ 「快照 == 真值」类守阵没有真值可断言
        (A 系删掉合成回写后, 只能靠"下一轮同步读真值"验位)。本方法补齐该能力。

        口径对齐 qB 自身: 停/暂停 -> pausedUP/pausedDL, 起/恢复 -> stalledUP/stalledDL; 完成位由
        state 后缀 UP 或 progress>=1.0 判定(不看 amount_left, 与 TorrentRecord 默认
        amount_left=0 的口径保持一致)。!A 系 26-10-13-0540 S1 后生产已无合成回写
        (_sync_paused_state 已删), 本方法成为「客户端侧真值」的**唯一**来源 —— A 系守阵断言
        「停/起后快照不变、下一轮同步才翻位」正依赖它。torrent_hashes 为 None = 全体
        (qB "不传 hash 即全体" 语义, 与 _FakeTorrents.info 的过滤语义对齐)。
        """
        if torrent_hashes is None:
            hashes = list(self.torrents.keys())
        elif isinstance(torrent_hashes, (list, tuple, set)):
            hashes = list(torrent_hashes)
        else:
            hashes = [torrent_hashes]
        for h in hashes:
            tor = self.torrents.get(h)
            if tor is None:
                continue
            if isinstance(tor, dict):
                cur = tor.get("state")
                progress = tor.get("progress", 0.0) or 0.0
            else:
                cur = getattr(tor, "state", None)
                progress = getattr(tor, "progress", 0.0) or 0.0
            complete = (isinstance(cur, str) and cur.endswith("UP")) or progress >= 1.0
            want = ("pausedUP" if complete else "pausedDL") if paused else ("stalledUP" if complete else "stalledDL")
            if isinstance(tor, dict):
                tor["state"] = want
            else:
                tor.state = want
                tor._state_enum = None  # 与 store.update_torrent_fields 同款: state 变更失效缓存

    def torrents_start(self, torrent_hashes=None):
        self.calls.append(("start", None))
        self._apply_paused_state(torrent_hashes, paused=False)

    def torrents_stop(self, torrent_hashes=None):
        self.calls.append(("stop", None))
        self._apply_paused_state(torrent_hashes, paused=True)

    def torrents_pause(self, torrent_hashes=None):
        # 与 start/stop 记 None 不同: 记 hash 列表(Web 命令测试需断言"整组/单种"作用范围)
        self.calls.append(("pause", torrent_hashes))
        self._apply_paused_state(torrent_hashes, paused=True)

    def torrents_resume(self, torrent_hashes=None):
        self.calls.append(("resume", torrent_hashes))
        self._apply_paused_state(torrent_hashes, paused=False)

    def torrents_recheck(self, torrent_hashes=None):
        self.calls.append(("recheck", None))
        # hash 级作用范围另记(Web 命令/批量测试断言用; calls 里的 ("recheck", None) 约定被大量既有断言依赖)
        self.recheck_hashes_calls.append(torrent_hashes)

    def torrents_reannounce(self, torrent_hashes=None):
        self.calls.append(("reannounce", None))
        self.reannounce_hashes_calls.append(torrent_hashes)  # hash 级作用范围另记(见 __init__ 注释)

    def torrents_set_upload_limit(self, torrent_hashes=None, limit=None):
        self.calls.append(("set_upload_limit", limit))
        self.limit_location_hashes_calls.append(("set_upload_limit", torrent_hashes))

    def torrents_set_download_limit(self, torrent_hashes=None, limit=None):
        self.calls.append(("set_download_limit", limit))
        self.limit_location_hashes_calls.append(("set_download_limit", torrent_hashes))

    def torrents_set_location(self, torrent_hashes=None, location=None):
        self.calls.append(("set_location", location))
        self.limit_location_hashes_calls.append(("set_location", torrent_hashes))

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
        # tracker 健康(WebUI 站点 chip 底色, 计划 26-10-19-2206 D2): 同名的非快照字段
        self.tracker_health_msg = kw.get("tracker_health_msg", "")
        self.tracker_health_ts = kw.get("tracker_health_ts", 0.0)
        self.tracker_suspect_since = kw.get("tracker_suspect_since", 0.0)
        # HR 桥回引(与 TorrentRecord 同名的非快照字段): store._apply 增量路径会读写它
        # (hr_link 挂桥时给记录补回引) —— 桩走真 _apply(S6/S7 间回归修复)后必须存在
        self.hr_link = None
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

        !没有这个方法时桩服务的详情端点 `/api/torrents/{hash}` **恒 500**
        (`'FakeTorrent' object has no attribute 'to_dict'`, 2026-09-19 实测), 于是整条依赖详情的
        链路在冒烟里从未被覆盖: 详情抽屉、限速/分享率/移动/重命名对话框、以及"复制磁力"
        (magnet_uri 只在详情里 —— 轮询载荷按需取详情口径已不含它, issue E-04 P-06;
        见 drawer.js copyTorrentInfo)。
        与真实现同口径(快照/非快照分则, pitfalls/testing/stub-bypass-apply.md): 导出单点 =
        compat._SNAPSHOT_FIELDS(桩构造器恒全量赋值, 含扩展快照字段 magnet_uri 等);
        **非快照字段不进导出** —— 桩改走真 store._apply 后, _apply 会给记录补挂
        `hr_link`(HrRuntime 对象, 不可 JSON 化), 旧的 vars() 全导出口径让详情端点
        恒 500(S10 e2e 复测实爆, 2026-10-07)。tracker_error_msg/ts 同为非快照字段,
        真记录 to_dict 一并不含(详情层的 HR 展示字段由端点另行附加, 与桩无关)。
        """
        return {f: getattr(self, f) for f in _SNAPSHOT_FIELDS}

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

    def hr_excluded(self) -> bool:
        """与 TorrentRecord.hr_excluded 同语义(HR 排除表, 计划 26-09-28-1805); 真实判定以真记录为准"""
        hr = self.tracker_conf.hr
        if hr is None:
            return False
        from auto_qb.infra.utils import match_tag_patterns

        if hr.exclude_tags and any(match_tag_patterns(t, hr.exclude_tags) for t in self.tags_set):
            return True
        return bool(hr.exclude_categories) and match_tag_patterns(self.category, hr.exclude_categories)

    def hr_excluded_by(self) -> str:
        """与 TorrentRecord.hr_excluded_by 同语义(命中来源 token, 2026-10-02); 真实判定以真记录为准"""
        hr = self.tracker_conf.hr
        if hr is None:
            return ""
        from auto_qb.infra.utils import match_tag_patterns

        tag_hit = bool(hr.exclude_tags) and any(match_tag_patterns(t, hr.exclude_tags) for t in self.tags_set)
        cat_hit = bool(hr.exclude_categories) and match_tag_patterns(self.category, hr.exclude_categories)
        if not (tag_hit or cat_hit):
            return ""
        if tag_hit and cat_hit:
            return "tag+category"
        return "tag" if tag_hit else "category"

    def check_hr_condition(self) -> bool:
        if not self.tracker_conf.hr:
            return False
        if self.hr_excluded():
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
        """与 TorrentRecord.check_hr_satisfied 同语义(计划 26-09-30-0559): 无触发门,
        达标只看做种事实(时长/分享率); 真实判定以真记录为准"""
        if not self.tracker_conf.hr:
            return False
        if self.hr_excluded():
            return False
        hr = self.tracker_conf.hr
        seeding_ok = self.seeding_time >= (hr.required_seeding_time + hr.extra_seeding_time)
        ratio_ok = hr.required_share_ratio > 0 and (self.ratio or 0) >= hr.required_share_ratio
        return seeding_ok or ratio_ok

    def hr_managed(self) -> bool:
        """与 TorrentRecord.hr_managed 同语义(计划 26-09-30-0559): 替身恒未接入(judged None)
        -> 本地判据兜底, 未达标即需管束; 真实判定以真记录为准"""
        if not self.tracker_conf.hr:
            return False
        if self.hr_excluded():
            return False
        return not self.check_hr_satisfied()

    def hr_anchor(self):
        """与 TorrentRecord.hr_anchor 一致(由快照字段派生的下载锚点)"""
        from auto_qb.hr.resolve import HrAnchor

        return HrAnchor(
            added_on=self.added_on,
            downloaded=self.downloaded,
            completion_on=self.completion_on,
            progress=self.progress,
        )

    def hr_judgement(self):
        """替身恒 None(未接判定桥): 即"站点未接入 -> 走本地口径", 与真记录未挂桥时同语义"""
        return None

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
        # HR 在线核实(站点级): 与真实 TrackerConfig 对齐 —— 该字段在真模型上恒存在(默认 None),
        # 记录侧 `hr_judgement()` 直接读它(未接入 = None => 走既有本地判定)。替身缺这个属性会
        # 让"站点未接入"的路径在测试里直接 AttributeError(而不是走本地逻辑)。
        self.hr_check = None
        self.rules = rules or []
        self.remove_similar_tags = remove_similar_tags
        self.upload_speed_limit = upload_speed_limit  # 字节/秒; 0 = 不限速(等价 UNLIMITED_SPEED)
        self.download_speed_limit = download_speed_limit


# ---------- 模拟 Config ----------
class FakeConfig:
    def __init__(self):
        # !类属性里的 dataclass/dict/list 是**共享可变对象**: 任一测试原地改
        #   (mgr.config.grouping.enabled = True / mgr.config.web.port = ...) 都会泄漏到
        #   之后所有 make_manager 的实例 —— 是否爆雷只取决于 xdist 把哪些测试分到同一
        #   worker(2026-10-01 P5 期间实报: test_build_group_view 污染
        #   test_refresh_removed_grouping_disabled)。每实例深拷贝一份可变默认,
        #   测试间隔离(与真实 Config 每次构造独立实例同形); 标量默认仍走类属性。
        for name, default in vars(type(self)).items():
            if name.startswith("_") or isinstance(default, (str, int, float, bool, type(None))):
                continue
            setattr(self, name, copy.deepcopy(default))

    # qB 口令桩值的键名**拆写**: 工作区写入判据把「凭据键名 + 赋值形态」当凭据字面量拦整文件
    # (pitfalls/testing/credential-shape-write-guard.md), 拆写是 2026-10-15 用户拍板的收敛样板;
    # 行为等价(同一 dataclass 字段同一值), 仅为让本文件对 agent 可写
    qbittorrent = QbittorrentConfig(host="127.0.0.1", port=16585, username="u", **{"pass" + "word": "p"})
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
    maintenance_tag_mode = "interval"  # 维护 tags 节奏(计划 26-09-27-1438): interval = 现状; 测试按需改 on_change
    add_episode_tags = AddEpisodeTagsConfig()  # 默认 disabled; 测试按需赋值 AddEpisodeTagsConfig(enabled=True, ...)
    hr = HRRule()  # 全局 HR 默认输出设置
    skip_checking_tag = "zSkipChecked"  # 跳检成功标签默认名(与 Config 默认一致; 测试按需赋值, ""=禁用)
    delete_tags = []  # 全局: 彻底删除的标签格式(支持正则)
    delete_tags_if_has_no_torrents = []  # 全局: 彻底删除无种子的标签格式(支持正则)
    grouping = GroupingConfig(enabled=False, missing_tag="MISSING")  # 种子分组管理(默认关闭)
    global_speed_limit_curve = None  # 全局限速曲线(未启用; 与 Config 默认一致, 测试按需赋值)
    # 全局流量来源(计划 26-10-17-0339 S15): 限速曲线/expr 取数单点; 与真 Config 同默认
    # (provider=traffic_monitor, dat_path 空), 既有用例行为零变化
    traffic_source = TrafficSourceConfig()
    # 整组迁移(计划 26-10-18-1604 §3.7): P1 只立配置面, enabled=false(缺省)与真 Config 同默认;
    # RelocateModule.start/apply 会读它, 替身缺该属性会 AttributeError
    relocate = RelocateConfig()
    qb_traffic = None  # qB 口径流量采样(未启用; 与 Config 默认一致, 测试按需赋 QbTraffic(...))
    notify = NotifyConfig()  # 主动通知(默认 disabled)
    web = WebConfig(skip_check_menu=True)  # WEB UI(默认 disabled); skip_check_menu 测试侧默认开 ——
    # R2 gate 用例(计划 26-10-02-1955 W1)按需实例级置 False(fail-closed 403), 深拷贝不跨测试泄漏,
    # 既有 skip-check 端点用例(期望入队 200)无需逐个补开
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


# ---------- 日志捕获(QbManager 系测试统一范式; 别用 caplog) ----------
class _LogCapture(logging.Handler):
    """挂模块 logger 的极简捕获器: records/messages 持续累积(同一列表对象), text 按需派生"""
    def __init__(self):
        super().__init__()
        self.records = []
        self.messages = []  # getMessage() 字符串, 与 records 同序

    def emit(self, record):
        self.records.append(record)
        self.messages.append(record.getMessage())

    @property
    def text(self):
        return "\n".join(self.messages)


@contextmanager
def capture_logs(logger_name="auto_qb", level=logging.DEBUG):
    """临时挂捕获 handler 到指定 logger 并临时关闭其 propagate(不污染测试输出)

    为什么不用 caplog: QbManager 构造链(LoggingModule -> setup_logging)会
    `logging.getLogger().handlers.clear()` 清空 root handlers, pytest caplog 挂在
    root 上的捕获 handler 一并被清 —— 用例体内构造 QbManager 的测试 caplog.text
    恒空("有日志"断言稳定红, "无日志"断言可能静默假绿)。本 helper 直挂 auto_qb
    子树的 logger, 对 root handlers / level / 传播链全部免疫。限界: 只收 auto_qb.*
    树下的日志(第三方库 logger 收不到)。

    用法: `with capture_logs("auto_qb.core.modules.ops_mod") as cap:` 后断言
    cap.messages / cap.text / cap.records。挂 auto_qb 顶层(默认)收全树; 子 logger
    的有效等级由祖先决定 —— 构造过 QbManager 的场景 auto_qb 已被 setup_logging
    设为 DEBUG, 直接可用; 未构造的场景子日志可能被祖先等级(默认 WARNING)拦截,
    此时挂具体模块 logger 更直接(helper 会替它显式 setLevel)。
    """
    h = _LogCapture()
    lg = logging.getLogger(logger_name)
    old_level, old_propagate = lg.level, lg.propagate
    lg.setLevel(level)
    lg.propagate = False
    lg.addHandler(h)
    try:
        yield h
    finally:
        lg.removeHandler(h)
        lg.setLevel(old_level)
        lg.propagate = old_propagate


def _example_rules_config():
    """make_manager 默认装配的三条示例规则(站点标签 / HR 完成 / 低分享率停种)"""
    return {
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


def make_manager(
    state_file=None,
    tracker_rules=None,
    tracker_kw=None,
    cfg=None,
    client=None,
    no_lock=True,
    bare=False,
    load_rules=None,
    **cfg_overrides,
):
    """QbManager 构造单点 —— 测试侧唯一装配入口(用例里不要再内联 QbManager(...))。

    state_file: 写进 cfg.state_file; None = 沿用 cfg 自带的值
    tracker_rules / tracker_kw: 默认装配的 HHan 假 tracker 的 rules / 其余构造参数
    cfg: 现成配置对象(默认 FakeConfig()); 给了就**不装**默认 tracker + 三条示例规则
    bare: True = 空配置(等价内联 `FakeConfig()`, 只留 cfg_overrides 覆盖的段);
          与 cfg 同给时 cfg 优先
    client: 构造后挂上替身(等价 `mgr.client = client`)
    no_lock: 透传 QbManager(默认 True = 测试不持锁)
    load_rules: None = 自动(默认装配路径 True, cfg / bare 路径 False —— 配置自备则规则面也自备);
                显式 True 强制加载(自备 rules_config 的场景)
    **cfg_overrides: 对最终 cfg 的段覆盖(未知段名抛 TypeError, 防手滑写成幽灵属性)

    用法: `make_manager(state_file)` 全默认; `make_manager(state_file, bare=True,
    grouping=grouping_cfg(), client=client)` 只要分组段 + 替身客户端。
    """
    assemble = cfg is None and not bare  # 默认装配 = 假 tracker + 三条示例规则
    if cfg is None:
        cfg = FakeConfig()
    if assemble:
        kw = dict(hr=_hr_rule(), rules=tracker_rules)
        kw.update(tracker_kw or {})
        cfg.trackers = {"HHan": FakeTracker("HHan", **kw)}
        cfg.rules_config = _example_rules_config()
    if state_file is not None:
        cfg.state_file = state_file
    for key, value in cfg_overrides.items():
        if not hasattr(cfg, key):
            raise TypeError(f"make_manager: FakeConfig 无 {key!r} 段(段名写错了?)")
        setattr(cfg, key, value)
    mgr = QbManager("", config=cfg, no_lock=no_lock)
    if load_rules is None:
        load_rules = assemble
    if load_rules:
        mgr.host.get("rules").load_rules()  # run() 中才自动加载; 测试直接构造后需手动加载规则
    if client is not None:
        mgr.client = client
    return mgr


def grouping_cfg(enabled=True, **grouping_kw):
    """分组场景的 grouping 段(测试统一口径: missing_tag 固定 MISSING)"""
    return GroupingConfig(enabled=enabled, missing_tag="MISSING", **grouping_kw)


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
    因此本函数保证: 1.client 已绑定到 mgr(动作经 ctx.api 调 manager.api Facade) 2.store 中已有该
    tor 的记录, 且记录对象即 tor 本身(对象身份直写: 后续修改 tor 属性对 ctx.torrent 实时可见)
    3.tracker_conf 已匹配(等效 _refresh_torrents 对新增种子的处理; ${required_seeding_time} 等依赖它)。
    """
    # 1. client 绑定: 动作走 ctx.api -> manager.api(QbApi), 未绑 client 时自动绑定
    if getattr(mgr, "_client", None) is None:
        mgr.client = client
    # 3. tracker_conf 匹配(未显式设置时; 模拟新增种子进 refresh 后由 ctx.trackers.match 赋值)
    if tor.tracker_conf is None:
        try:
            tor.tracker_conf = mgr.ctx.trackers.match(tor)
        except Exception:
            tor.tracker_conf = None
    # 2. 对象身份注入: by_hash[h] is tor(已存在则原地替换/更新)
    existing = mgr.store.by_hash.get(tor.hash)
    if existing is not tor:
        if existing is not None and not isinstance(existing, FakeTorrent):
            existing.apply_delta(tor)  # 真 TorrentRecord: 应用字段变化
        mgr.store.by_hash[tor.hash] = tor  # 对象身份直写(供改 tor 属性后实时可见)
    return RuleContext(mgr, client, mgr.config, tor.hash, dry_run=dry_run)


def drive_skip(mgr, timeout=5.0):
    """把在途跳检 job 驱动到终态(测试替身: 主循环的第三条时间线)

    生产由主循环每轮调 `ops.advance_due()`, 等待超时由 `next_run_at()` 并入; 测试里没有主循环,
    这里按同一预算反复推进直到没有在途 job。返回是否清空(超时 -> False)。
    """
    ops = mgr.ctx.ops
    deadline = time.time() + timeout
    while True:
        nxt = ops.next_run_at()
        if nxt is None:
            return True
        if time.time() >= deadline:
            return False
        wait = nxt - time.time()
        if wait > 0:
            time.sleep(min(wait, 0.01))
        ops.advance_due(budget_ms=200.0, budget_calls=100)


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


# ---------- 跨文件小助手单点(issue 26-10-21-0502: 8 族同名小助手逐字拷贝收口) ----------
# 口径: dat 文本与 legacy 配置样本刻意**测试侧手写**, 不引生产解析/写入实现(防同义反复);
# 格式正确性由读侧往返守阵钉(生产 parse 回读 / 生产 read_tree 回读), 不靠与生产共用代码自证。

DAT_HEADER_LINE = 'lines: "30"'

# schema v1 存量形态(BTSchool 旧键未迁移, 无版本章): 程序升级前打开的页签 GET 到的就是这棵树
LEGACY_V1 = (
    "config:\n"
    "  qbittorrent:\n"
    "    host: h\n"
    "    port: 1\n"
    "    username: u\n"
    "    password: p\n"
    "  trackers:\n"
    "    BTSchool:\n"
    "      domains: [pt.btschool.club]\n"
    "      hr:\n"
    "        required_seeding_time: 3D\n"
    "      hr_check:\n"
    "        mode: partial\n"
    "        adapter: nexusphp\n"
    "        hr_page_url: https://pt.btschool.club/myhr.php\n"
    "        refresh_interval: 6H\n"
)


def dat_text(rows) -> str:
    """rows: [(日期, 上传字节, 下载字节)] -> history dat 文本(单位 KB)"""
    lines = [DAT_HEADER_LINE]
    for d, up_b, down_b in rows:
        lines.append(f"{d:%Y/%m/%d} {up_b // 1024}/{down_b // 1024}")
    return "\n".join(lines)


def write_dat(tmp_path, rows, name="history_traffic.dat") -> str:
    """写一份 history dat(工具侧总账文件的 qB 形态), 返回路径字符串"""
    p = tmp_path / name
    p.write_text(dat_text(rows), encoding="utf-8")
    return str(p)


def write_dat_lines(path, lines) -> None:
    """按行列表落盘 dat(建父目录 + 覆盖写, LF 行尾 + 尾换行)"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


def server_state(**overrides) -> dict:
    """合法 server_state 样例(六字段齐全, 与 qB sync 响应同键名)"""
    base = {
        "dl_info_speed": 1024,
        "up_info_speed": 2048,
        "alltime_dl": 10_000_000,
        "alltime_ul": 20_000_000,
        "dl_info_data": 1_000_000,
        "up_info_data": 2_000_000,
    }
    base.update(overrides)
    return base


def active_torrent(hash="HASH123", **kw) -> FakeTorrent:
    """活跃种子样例(默认 dlspeed>0); 字段可覆盖"""
    kw.setdefault("dlspeed", 512)
    kw.setdefault("upspeed", 256)
    kw.setdefault("downloaded", 5_000_000)
    kw.setdefault("uploaded", 3_000_000)
    kw.setdefault("downloaded_session", 500_000)
    kw.setdefault("uploaded_session", 300_000)
    return FakeTorrent(hash=hash, **kw)


def write_credential_file(tmp_path, text="tool-credential-abc") -> str:
    """写一个假的工具密钥文件(值仅用于断言透传, 与真工具凭据无关)"""
    path = tmp_path / "gtm" / "monitor.token"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return str(path)


def pin_disk_usage(monkeypatch, free=1 << 40) -> None:
    """把 disk_usage 钉成固定值: 同卷证明/空间闸门不再受并行写盘抖动影响(测试确定性)"""
    from auto_qb.infra import file_access as fa_mod

    monkeypatch.setattr(
        fa_mod.LocalFileAccess,
        "disk_usage",
        lambda self, path: fa_mod.DiskUsage(total=free * 10, used=0, free=free),
    )


def pin_atomic_write_crash(monkeypatch) -> None:
    """把 atomic_write 换成「写一半抛错」: 回调落半截内容后抛 RuntimeError

    目标路径保持旧内容 + 临时文件被清理 —— 两件事都由真 atomic_write 负责; 若实现退回
    O_TRUNC 直写, 半截内容会直接落进目标文件, 断言当场红。
    """
    from auto_qb.infra import utils as infra_utils

    real_atomic_write = infra_utils.atomic_write

    def _crash_mid(path, write_fn, **kw):
        def _half(_f):
            _f.write("deadbeef")  # 半截内容, 模拟写盘途中被杀
            raise RuntimeError("simulated kill mid-write")

        return real_atomic_write(path, _half, **kw)

    monkeypatch.setattr(infra_utils, "atomic_write", _crash_mid)


def wait_until(pred, *, timeout=3.0, poll=0.02) -> bool:
    """轮询等待条件成立(线程用例): 命中即返回 True

    超时分支再判一次 pred()(monitor_client 版语义): 只为减少线程用例的 flake ——
    最后一个 poll 窗口内条件刚好翻转时多判一次, 方向只会更宽松, 不放宽任何断言语义
    (现有断言没有一处依赖「必须更严」)。
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if pred():
            return True
        time.sleep(poll)
    return pred()


def write_endpoint_pointer(
    tmp_path,
    monkeypatch,
    *,
    token_path="",
    host="127.0.0.1",
    port=8099,
    schema=agent.ENDPOINT_SCHEMA,
    autostart_error=None,
    payload=None,
) -> str:
    """写发现指针 endpoint.json 并把 agent 的指针路径重定向到它(三份 traffic 测试共用的单点)

    payload 非空则整字典原样写(喂最小合法指针 / schema 不匹配等任意形态, 测读者容错),
    否则按 11 键默认载荷写 —— 字段集镜像工具侧 gtm 的写出契约(含 autostart_error,
    缺键时读侧 .get() 容错, 但镜像保持完整)。统一落 tmp/pointer/endpoint.json,
    monkeypatch 后返回路径字符串。
    """
    path = tmp_path / "pointer" / agent.ENDPOINT_FILE_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    if payload is None:
        payload = {
            "schema": schema,
            "version": "0.1.0",
            "pid": 4321,
            "started_at": "2026-10-17T00:00:00+08:00",
            "host": host,
            "port": port,
            "data_dir": str(tmp_path / "gtm"),
            "token_path": token_path,
            "exe_path": "",
            "autostart_registered": True,
            "autostart_error": autostart_error,
        }
    path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(agent, "endpoint_path", lambda: str(path))
    return str(path)


# ---------- relocate 环境构建器单点(issue 26-10-29-1405: 4 份 35 行同构骨架收口) ----------


class RelocateEnv(NamedTuple):
    """relocate_env 返回值(具名六元; 防 5/6 元解包错位)"""

    mgr: QbManager
    client: FakeClient
    src: str
    dst: str
    content: str
    files: list


def relocate_env(
    td,
    *,
    file_count=2,
    subdir="Show",
    state="pausedUP",
    size=64,
    progress=1.0,
    assign=True,
    data_dir=True,
    free=1 << 40,
    paths=None,
) -> RelocateEnv:
    """真临时目录 + HA/HB 双成员组 + 目标卷的 relocate 测试环境(四份局部构建器的单点)

    组内两个成员共享同一份物理文件(HA/HB 同 files_map), 初始态默认 pausedUP, 目标卷
    真实存在(exists/scandir 才可判定)。参数化的是四个原局部版本的**真实差异**:
    - state: exec 用例从 uploading 起步(relocate 第一步就是暂停做种中的种子)
    - assign: False 时成员不登记进分组表(测「链接在场是否裂组」用例故意让成员先落各自组)
    - data_dir: False 时不设 mgr.config.data_dir(journal 落盘位置; 预检用例不依赖)
    - paths: 传入相对路径元组可指定成员文件名(默认按 file_count 生成 e00/e01/...)
    - size: 声明文件大小(字节), 磁盘实际写入同尺寸(声明与磁盘一致; 原web版100/64不一致已统一)
    pin_disk_usage(monkeypatch) 是能力钉不是环境, 仍由用例自己调。
    """
    mgr = make_manager(os.path.join(str(td), "state.json"))
    client = FakeClient()
    mgr.client = client
    src = os.path.join(str(td), "src")
    dst = os.path.join(str(td), "dst")
    content = os.path.join(src, subdir)
    os.makedirs(content)
    os.makedirs(dst)
    rels = paths if paths is not None else [f"{subdir}/e{i:02d}.mkv" for i in range(file_count)]
    files = []
    for rel in rels:
        p = os.path.join(src, *rel.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(b"x" * size)
        files.append(_fake_file(rel, size))
    client.files_map["HA"] = list(files)
    client.files_map["HB"] = list(files)
    tors = [
        FakeTorrent(hash="HA", name="Show", save_path=src, progress=progress, state=state),
        FakeTorrent(hash="HB", name="Show", save_path=src, progress=progress, state=state),
    ]
    for t in tors:
        client.torrents[t.hash] = t
    seed_store(mgr, tors)
    if assign:
        grouping = mgr.host.get("grouping")
        grouping._assign_new_torrent("HA")
        grouping._assign_new_torrent("HB")
    mgr.store.server_state = {"free_space_on_disk": free}
    if data_dir:
        mgr.config.data_dir = os.path.join(str(td), "data")
    mgr.config.relocate.enabled = True
    return RelocateEnv(mgr, client, src, dst, content, files)
