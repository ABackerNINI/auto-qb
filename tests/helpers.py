"""测试公共组件: 模拟 qB 客户端 / 种子 / 配置 + 构造辅助

由 pytest.ini 的 pythonpath=src 处理 src 导入, 无需 sys.path 处理。
"""
import os
import tempfile
import time
from types import SimpleNamespace

from auto_qb.config import AddEpisodeTagsConfig, GroupingConfig, HRRule, LoggingConfig, QbittorrentConfig  # noqa: E402
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
        contentLayout=None,
        ratio_limit=None,
        seeding_time_limit=None,
        inactive_seeding_time_limit=None,
        share_limit_action=None,
        **kw
    ):
        self.calls.append((
            "add",
            {
                "is_skip_checking": is_skip_checking,
                "paused": paused or is_paused,
                "upload_limit": upload_limit,
                "download_limit": download_limit,
                "contentLayout": contentLayout,
                "ratio_limit": ratio_limit,
                "seeding_time_limit": seeding_time_limit,
            },
        ))
        if self.add_error:
            raise self.add_error
        # 新种子进入客户端(hash 固定 HASH123, 与 FakeTorrent 默认一致); 存对象而非 dict,
        # 保证 store.refresh / trackers_info 等按 .hash/.state 属性访问不崩
        self.torrents["HASH123"] = FakeTorrent(
            hash="HASH123",
            state="pausedUP" if (paused or is_paused) else "stalledUP",
            save_path=save_path or r"R:\Downloads",
            category=category or "",
            tags=tags or "",
        )

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

    def torrents_set_upload_limit(self, torrent_hashes=None, limit=None):
        self.calls.append(("set_upload_limit", limit))

    def torrents_set_download_limit(self, torrent_hashes=None, limit=None):
        self.calls.append(("set_download_limit", limit))

    def torrents_set_location(self, torrent_hashes=None, location=None):
        self.calls.append(("set_location", location))


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
        self.seeding_time = kw.get("seeding_time", 0)
        self.ratio = kw.get("ratio", 0.0)
        self.amount_left = kw.get("amount_left", 0)
        self.completed = kw.get("completed", 0)
        self.progress = kw.get("progress", 0.0)
        self.dl_limit = kw.get("dl_limit", 0)
        self.up_limit = kw.get("up_limit", 0)
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
            total = self.total_size or 1
            if (self.downloaded / total) < cond_value:
                return False
        elif cond_type == "dlsize":
            if self.downloaded < cond_value:
                return False
        return True

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
    )

    def update_from(self, tor):
        """用最新种子对象更新快照字段(惰性缓存保留, 文本派生缓存失效); 与 TorrentRecord.update_from 同语义"""
        self.tor = tor
        for f in self._SNAPSHOT_FIELDS:
            v = getattr(tor, f, None)
            if v is not None:
                setattr(self, f, v)
        self._tags_set = None
        self._state_enum = None
        self._trackers_info = None
        self._files = None

    def trackers_info(self, client):
        if self._trackers_info is None:
            if client is None:
                raise RuntimeError("TorrentStore 未绑定 client")
            self._trackers_info = list(client.torrents_trackers(self.hash) or [])
        return self._trackers_info

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
        self, name, hr=None, rules=None, remove_similar_tags=False, upload_speed_limit=0, download_speed_limit=0
    ):
        self.name = name
        self.domains = ["tracker.hhanclub.net"]
        self.tags = ["HHan"]
        self.remove_tags = []
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
            existing.update_from(tor)  # 真 TorrentRecord: 原地更新快照
        mgr.store.by_hash[tor.hash] = tor  # 对象身份直写(供改 tor 属性后实时可见)
        if mgr.store._known_hashes is not None:
            mgr.store._known_hashes.add(tor.hash)
    return RuleContext(mgr, client, mgr.config, tor.hash, dry_run=dry_run)


def seed_store(mgr, torrents=None):
    """将种子灌入 mgr.store(对象身份直写: 记录即传入对象, 后续修改实时可见)

    语义与 store.refresh 一致(首轮全部视为新增, 后续 diff), 但保留对象身份而非复制字段;
    返回值 (added, removed)。
    """
    if torrents is None:
        torrents = list(mgr.client.torrents.values())
    store = mgr.store
    old_known = store._known_hashes
    new_by_hash: dict = {}
    for tor in torrents:
        if tor is None or isinstance(tor, dict):
            continue  # 无快照形状的对象(如测试手动注入的 dict)不参与
        h = getattr(tor, "hash", None)
        if not h:
            continue
        new_by_hash[h] = tor
    if old_known is None:
        added, removed = list(new_by_hash), []
    else:
        added = [h for h in new_by_hash if h not in old_known]
        removed = [h for h in old_known if h not in new_by_hash]
    store.by_hash = new_by_hash
    store._known_hashes = set(new_by_hash)
    return added, removed
