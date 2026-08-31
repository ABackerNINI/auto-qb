"""种子信息数据层(TorrentStore)

设计目标(优先级: 速度 > 可读性 > 内存):
- 每 main_tick 通过 qbittorrentapi 全量拉取一次种子信息写入 TorrentStore, 之后本 tick 内
  所有读取操作(规则条件/动作/分组/标签/轮询回调)都只访问本数据层, 不再重复调用
  torrents_info / torrents_trackers / torrents_files / torrents_tags / torrents_categories。
- 惰性缓存: tracker/files 首次访问才拉取并在记录上持久缓存, 种子删除时随记录一起回收;
  全局标签/分类列表缓存, 写操作后失效。
- 分组索引: groups / group_sizes / member_to_key / state_snapshot / download_conflict_warned
  内聚于此, O(1) 定位。
- 写操作(新增/删除/暂停/开始/加删标签/设分类等)仍直接调 qbittorrentapi, 不经过本层;
  本 tick 内的写操作下一 tick 快照刷新后可见。

说明:
- TorrentRecord 字段名与 qbittorrentapi TorrentDictionary 一致, 鸭子类型兼容(可直接传给
  需要种子对象的代码)。
- refresh() 保留已存在记录对象(惰性缓存跨 tick 存活), 仅 in-place 更新快照字段;
  种子不在快照中但被查询时(如 process_torrent 外部传入对象)退化为直接拉取, 不做缓存。
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    from qbittorrentapi import TorrentState
except ImportError:  # 未安装 qbittorrentapi 时降级: state_enum 为 None
    TorrentState = None  # type: ignore[assignment]

# 与 qbittorrentapi TorrentDictionary 一致的快照字段(refresh 时逐字段 in-place 更新)
_SNAPSHOT_FIELDS = (
    "hash",
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
)


@dataclass(slots=True)
class TorrentRecord:
    """种子快照记录: 字段名与 TorrentDictionary 一致, 鸭子类型兼容

    惰性缓存槽(_tags_set/_state_enum/_trackers_info/_files)跨 tick 存活:
    update_from() 只更新快照字段, 缓存随记录对象保留; 种子删除时记录被回收, 缓存自然清理。
    """

    hash: str
    name: str = ""
    save_path: str = ""
    content_path: str = ""
    size: int = 0
    total_size: int = 0
    tags: str = ""
    category: str = ""
    state: str = ""
    downloaded: int = 0
    uploaded: int = 0
    seeding_time: int = 0
    ratio: float = 0.0
    amount_left: int = 0
    completed: int = 0
    progress: float = 0.0

    # 惰性缓存(不参与 update_from 复制)
    _tags_set: Optional[frozenset] = None
    _state_enum: Any = None
    _trackers_info: Optional[List[dict]] = None
    _files: Optional[List[Any]] = None

    @classmethod
    def from_torrent(cls, tor: Any) -> "TorrentRecord":
        """从原始种子对象(TorrentDictionary/FakeTorrent)构建新记录"""
        rec = cls(hash=getattr(tor, "hash", ""))
        rec.update_from(tor)
        return rec

    def update_from(self, tor: Any) -> None:
        """用最新种子对象更新快照字段(惰性缓存保留, 文本派生缓存失效)"""
        for f in _SNAPSHOT_FIELDS:
            if f == "hash":
                continue  # hash 是主键, 不更新
            v = getattr(tor, f, None)
            if v is not None:
                setattr(self, f, v)
        self._tags_set = None
        self._state_enum = None

    # ---------- 派生/预计算属性 ----------

    @property
    def tags_set(self) -> frozenset:
        """预计算标签集合(逗号分隔去空白), 用于全局标签使用统计"""
        s = self._tags_set
        if s is None:
            s = frozenset(p.strip() for p in (self.tags or "").split(",") if p.strip())
            self._tags_set = s
        return s

    @property
    def state_enum(self) -> Any:
        """由 state 字符串构造的 TorrentState(与 qB 版本无关的状态类别判定)"""
        if self._state_enum is None and TorrentState is not None:
            try:
                self._state_enum = TorrentState(self.state)
            except ValueError:
                self._state_enum = TorrentState.UNKNOWN
        return self._state_enum

    @property
    def is_paused(self) -> bool:
        enum = self.state_enum
        return bool(enum is not None and enum.is_paused)

    @property
    def is_uploading(self) -> bool:
        enum = self.state_enum
        return bool(enum is not None and enum.is_uploading)

    @property
    def is_downloading(self) -> bool:
        enum = self.state_enum
        return bool(enum is not None and enum.is_downloading and not enum.is_paused)

    # ---------- 惰性缓存(tracker/files) ----------

    def trackers_info(self, client: Any) -> List[dict]:
        """该种子 tracker 信息列表(惰性拉取+持久缓存; 异常向上传播, 由调用方决定处理)"""
        if self._trackers_info is None:
            if client is None:
                raise RuntimeError("TorrentStore 未绑定 client")
            self._trackers_info = list(client.torrents_trackers(self.hash) or [])
        return self._trackers_info

    def tracker_urls(self, client: Any) -> List[str]:
        """该种子 tracker URL 列表(基于 trackers_info 派生)"""
        return [t.get("url") for t in self.trackers_info(client) if t.get("url")]

    def files(self, client: Any) -> List[Any]:
        """该种子文件列表(惰性拉取+持久缓存; 异常向上传播, 由调用方决定处理)"""
        if self._files is None:
            if client is None:
                raise RuntimeError("TorrentStore 未绑定 client")
            self._files = list(client.torrents_files(self.hash) or [])
        return self._files


class TorrentStore:
    """种子信息数据层: 主索引 + 惰性缓存 + 分组索引 + 全局标签/分类缓存

    分组相关结构(供 GroupingMixin 直接读写, 保持增量语义):
      - groups:        key=(save_path, 排序文件路径元组) -> [hash...]
      - group_sizes:   key -> {hash: {规范化相对路径: 大小}}
      - member_to_key: hash -> 组 key(O(1) 定位)
      - state_snapshot: hash -> 上一轮 state_enum(上传转暂停检测)
      - download_conflict_warned: (组key, 冲突类型) 去重集合
    参考种子集合(仅内存): verified_references
    全局缓存: all_tags() / all_categories()(写操作后 invalidate)
    """
    def __init__(self, client: Any = None):
        self.client: Any = client
        # 主索引: hash -> TorrentRecord(每 tick 重建引用, 记录对象跨 tick 保留)
        self.by_hash: Dict[str, TorrentRecord] = {}
        self._known_hashes: Optional[Set[str]] = None
        # 分组结构
        self.groups: Dict[Any, List[str]] = {}
        self.group_sizes: Dict[Any, Dict[str, Dict[str, int]]] = {}
        self.member_to_key: Dict[str, Any] = {}
        self.state_snapshot: Dict[str, Any] = {}
        self.download_conflict_warned: Set[Tuple[Any, str]] = set()
        # 内存参考种子集合(仅内存, 重启后重新积累): full-checking 校验通过的种子, 可作为同组参考
        self.verified_references: Set[str] = set()
        # 全局标签/分类缓存
        self._all_tags_cache: Optional[set] = None
        self._all_categories_cache: Optional[dict] = None

    # ---------- 快照 ----------

    def refresh(self, torrents: Any) -> Tuple[List[str], List[str]]:
        """全量刷新快照: 返回 (added, removed) hash 列表

        首轮(_known_hashes is None)全部视为新增(与旧 _known_hashes 语义一致);
        已存在的记录对象原地更新, 惰性缓存跨 tick 存活。
        """
        new_by_hash: Dict[str, TorrentRecord] = {}
        for t in torrents:
            h = getattr(t, "hash", None)
            if not h:
                continue
            rec = self.by_hash.get(h)
            if rec is None:
                rec = TorrentRecord.from_torrent(t)
            else:
                rec.update_from(t)
            new_by_hash[h] = rec

        if self._known_hashes is None:
            added = list(new_by_hash)
            removed: List[str] = []
        else:
            added = [h for h in new_by_hash if h not in self._known_hashes]
            removed = [h for h in self._known_hashes if h not in new_by_hash]

        self.by_hash = new_by_hash
        self._known_hashes = set(new_by_hash)
        return added, removed

    def apply(self, torrents: Any) -> Tuple[List[str], List[str]]:
        """测试/外部注入入口: 与 refresh 等价(不依赖 client)"""
        return self.refresh(torrents)

    def get(self, torrent_hash: str) -> Optional[TorrentRecord]:
        return self.by_hash.get(torrent_hash)

    def __contains__(self, torrent_hash: str) -> bool:
        return torrent_hash in self.by_hash

    def __len__(self) -> int:
        return len(self.by_hash)

    def all(self) -> List[TorrentRecord]:
        return list(self.by_hash.values())

    def hashes(self) -> List[str]:
        return list(self.by_hash)

    # ---------- 惰性缓存(tracker/files, 记录级) ----------

    def trackers_info(self, torrent_hash: str) -> List[dict]:
        """种子 tracker 信息列表(快照种子走记录缓存; 外部种子直接拉取)"""
        rec = self.by_hash.get(torrent_hash)
        if rec is None:
            if self.client is None:
                raise RuntimeError("TorrentStore 未绑定 client")
            return list(self.client.torrents_trackers(torrent_hash) or [])
        return rec.trackers_info(self.client)

    def tracker_urls(self, torrent_hash: str) -> List[str]:
        """种子 tracker URL 列表"""
        rec = self.by_hash.get(torrent_hash)
        if rec is None:
            if self.client is None:
                raise RuntimeError("TorrentStore 未绑定 client")
            return [t.get("url") for t in (self.client.torrents_trackers(torrent_hash) or []) if t.get("url")]
        return rec.tracker_urls(self.client)

    def files(self, torrent_hash: str) -> List[Any]:
        """种子文件列表(快照种子走记录缓存; 外部种子直接拉取)"""
        rec = self.by_hash.get(torrent_hash)
        if rec is None:
            if self.client is None:
                raise RuntimeError("TorrentStore 未绑定 client")
            return list(self.client.torrents_files(torrent_hash) or [])
        return rec.files(self.client)

    def update_state_snapshot(self, torrents: Any) -> None:
        """本轮结束前更新状态快照(存 state_enum 枚举对象, 与 qB 版本无关)"""
        self.state_snapshot = {t.hash: getattr(t, "state_enum", None) for t in torrents}

    # ---------- 分组查询接口 ----------

    def group_members(self, torrent_hash: str) -> List[str]:
        """种子所属组全部成员 hash; 未归组 -> [自身] 单种子"""
        key = self.member_to_key.get(torrent_hash)
        if key is None:
            return [torrent_hash]
        return list(self.groups.get(key, [torrent_hash]))

    def group_key(self, torrent_hash: str) -> Optional[Any]:
        """种子所属组 key; 未归组 -> None"""
        return self.member_to_key.get(torrent_hash)

    # ---------- 全局标签/分类缓存 ----------

    def all_tags(self) -> set:
        """客户端全部标签定义(惰性缓存; 异常向上传播, 调用方处理)"""
        if self._all_tags_cache is None:
            if self.client is None:
                raise RuntimeError("TorrentStore 未绑定 client")
            self._all_tags_cache = set(self.client.torrents_tags() or [])
        return set(self._all_tags_cache)

    def all_categories(self) -> dict:
        """客户端全部分类定义(惰性缓存; 异常向上传播, 调用方处理)"""
        if self._all_categories_cache is None:
            if self.client is None:
                raise RuntimeError("TorrentStore 未绑定 client")
            self._all_categories_cache = dict(self.client.torrents_categories() or {})
        return self._all_categories_cache

    def invalidate_tags(self) -> None:
        """标签写操作后调用, 使全局标签缓存失效"""
        self._all_tags_cache = None

    def invalidate_categories(self) -> None:
        """分类写操作后调用, 使全局分类缓存失效"""
        self._all_categories_cache = None

    def tag_usage(self) -> Dict[str, int]:
        """从快照聚合标签使用情况 {tag: 使用该标签的种子数}

        替代 _handle_delete_tags_if_has_no_torrents 的 torrents.info(tag=) 逐个查询。
        """
        usage: Dict[str, int] = {}
        for rec in self.by_hash.values():
            for tag in rec.tags_set:
                usage[tag] = usage.get(tag, 0) + 1
        return usage
