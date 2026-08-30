"""测试公共组件: 模拟 qB 客户端 / 种子 / 配置 + 构造辅助

由 pytest.ini 的 pythonpath=src 处理 src 导入, 无需 sys.path 处理。
"""
import os
import tempfile
import time
from types import SimpleNamespace

from auto_qb.config import GroupingConfig, HRRule, QbittorrentConfig  # noqa: E402
from auto_qb.qbmanager import QbManager  # noqa: E402
from auto_qb.rules import ActionResult, RuleContext  # noqa: E402

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
        self.files_calls = 0  # torrents_files 调用计数(验证分组检查不再全量拉文件列表)

    def torrents_trackers(self, h):
        return [{"url": "https://tracker.hhanclub.net/announce.php"}]

    def torrents_files(self, h):
        self.files_calls += 1
        # 优先按 hash 返回文件列表(分组测试用), 否则返回共享 files
        if h in self.files_map:
            return self.files_map[h]
        return self.files

    def torrents_info(self, torrent_hashes=None, **kw):
        return self.torrents.info(torrent_hashes=torrent_hashes, **kw)

    def torrents_export(self, torrent_hashes=None, torrent_hash=None, **kw):
        self.calls.append(("export", torrent_hash if torrent_hash is not None else torrent_hashes))
        return self.exported

    def torrents_delete(self, torrent_hashes=None, delete_files=False):
        self.calls.append(("delete", delete_files))
        if not delete_files:
            self.torrents.pop(torrent_hashes, None)

    def torrents_add(
        self,
        torrent_files=None,
        torrent_paths=None,
        save_path=None,
        category=None,
        tags=None,
        is_skip_checking=False,
        paused=False,
        is_paused=False,
        **kw
    ):
        self.calls.append(("add", {"is_skip_checking": is_skip_checking, "paused": paused or is_paused}))
        if self.add_error:
            raise self.add_error
        self.torrents["HASH123"] = {"state": "pausedUP" if (paused or is_paused) else "stalledUP"}

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

    def torrents_create_category(self, name=None):
        self.calls.append(("create_category", name))

    def torrents_set_category(self, category=None, torrent_hashes=None):
        self.category = category
        self.calls.append(("set_category", category))

    def torrents_start(self, torrent_hashes=None):
        self.calls.append(("start", None))

    def torrents_stop(self, torrent_hashes=None):
        self.calls.append(("stop", None))

    def torrents_recheck(self, torrent_hashes=None):
        self.calls.append(("recheck", None))

    def torrents_reannounce(self, torrent_hashes=None):
        self.calls.append(("reannounce", None))

    def torrents_set_upload_limit(self, torrent_hashes=None, upload_limit=None):
        self.calls.append(("set_upload_limit", upload_limit))

    def torrents_set_download_limit(self, torrent_hashes=None, download_limit=None):
        self.calls.append(("set_download_limit", download_limit))

    def torrents_set_location(self, torrent_hashes=None, location=None):
        self.calls.append(("set_location", location))


# ---------- 模拟种子 ----------
class FakeTorrent:
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
        self.seeding_time = kw.get("seeding_time", 0)
        self.ratio = kw.get("ratio", 0.0)
        self.amount_left = kw.get("amount_left", 0)
        self.completed = kw.get("completed", 0)
        self.progress = kw.get("progress", 0.0)

    @property
    def state_enum(self):
        """模拟真实客户端: 由 state 字符串动态构造 TorrentState(与 qB 版本无关的状态类别判定)"""
        if TorrentState is None:
            return None
        try:
            return TorrentState(self.state)
        except ValueError:
            return TorrentState.UNKNOWN


# ---------- 模拟 TrackerConfig ----------
class FakeTracker:
    def __init__(self, name, hr=None, rules=None, remove_similar_tags=False):
        self.name = name
        self.domains = ["tracker.hhanclub.net"]
        self.tags = ["HHan"]
        self.remove_tags = []
        self.hr = hr  # HRRule 或 None
        self.rules = rules or []
        self.remove_similar_tags = remove_similar_tags


# ---------- 模拟 Config ----------
class FakeConfig:
    qbittorrent = QbittorrentConfig(host="127.0.0.1", port=16585, username="u", password="p")
    trackers = {"HHan": FakeTracker("HHan")}
    state_file = ""  # 由测试设置
    interval = 60  # QbManager 主刷新任务 interval(测试不触发 refresh)
    check_missing_files = False
    remove_similar_tags = False
    add_episode_tags = False  # 自动添加集数标签(默认关闭)
    hr = HRRule()  # 全局 HR 默认输出设置
    delete_tags = []  # 全局: 彻底删除的标签格式(支持正则)
    delete_tags_if_has_no_torrents = []  # 全局: 彻底删除无种子的标签格式(支持正则)
    grouping = GroupingConfig(enabled=False, interval=300, missing_tag="MISSING")  # 种子分组管理(默认关闭)


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
                            "state": "complete&uploading"
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
    return QbManager("", config=cfg)


def _fake_file(name, size):
    return SimpleNamespace(name=name, size=size)


def make_ctx(mgr, tor, client, dry_run=False):
    """构造 RuleContext(规则动作测试辅助)"""
    return RuleContext(mgr, client, mgr.config, tor, dry_run=dry_run)
