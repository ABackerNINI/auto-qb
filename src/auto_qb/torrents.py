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
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from qbittorrentapi import TorrentState, TorrentDictionary

from . import utils
from .config import TrackerConfig
from .errors import AutoQbError

logger = logging.getLogger(__name__)

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
    "dlspeed",
    "upspeed",
    "seeding_time",
    "ratio",
    "amount_left",
    "completed",
    "progress",
    "dl_limit",
    "up_limit",
)

# 跳检重加所需属性(qB torrent info 直接字段, 不经快照复制; 单一来源, CheckAction 引用)
RE_ADD_FIELDS = (
    "seq_dl",
    "f_l_piece_prio",
    "ratio_limit",
    "seeding_time_limit",
    "inactive_seeding_time_limit",
    "share_limit_action",
)

# 版本兼容校验所需全字段(快照字段 + 重加字段): 快照字段缺失会静默零值(规则基于假数据决策),
# 比崩溃更危险, 启动期一并校验
REQUIRED_TORRENT_FIELDS = _SNAPSHOT_FIELDS + RE_ADD_FIELDS


class QbCompatError(AutoQbError):
    """qBittorrent torrent info 字段与预期不符(版本不兼容), 首次拉到种子信息时 fail-fast"""


def missing_torrent_fields(tor) -> List[str]:
    """返回 tor 上缺失的必需字段列表(空列表 = 版本兼容); AttrDict 缺键时 hasattr 为 False"""
    return [f for f in REQUIRED_TORRENT_FIELDS if not hasattr(tor, f)]


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
    dlspeed: int = 0
    upspeed: int = 0
    seeding_time: int = 0
    ratio: float = 0.0
    amount_left: int = 0
    completed: int = 0
    progress: float = 0.0
    dl_limit: int = 0
    up_limit: int = 0

    # 惰性缓存(不参与 update_from 复制)
    _tags_set: Optional[frozenset] = None
    _state_enum: Any = None
    _trackers_info: Optional[List[dict]] = None
    _files: Optional[List[Any]] = None

    tor: Optional[TorrentDictionary] = None
    tracker_conf: Optional[TrackerConfig] = None

    @classmethod
    def from_torrent(cls, tor: Any) -> "TorrentRecord":
        """从原始种子对象(TorrentDictionary/FakeTorrent)构建新记录"""
        rec = cls(hash=getattr(tor, "hash", ""))
        rec.update_from(tor)
        return rec

    def update_from(self, tor: Any) -> None:
        """用最新种子对象更新快照字段(惰性缓存保留, 文本派生缓存失效)"""
        self.tor = tor
        for f in _SNAPSHOT_FIELDS:
            if f == "hash":
                continue  # hash 是主键, 不更新
            v = getattr(tor, f, None)
            if v is not None:
                setattr(self, f, v)
        self._tags_set = None
        self._state_enum = None

    @property
    def tracker_name(self) -> str:
        """返回 tracker 名称(从 tracker_conf 派生, 主要用于log)

        tracker_conf=None 时返回 "Unknown": 不回退 self.tor.client 取 URL —— 真实
        qbittorrentapi TorrentDictionary 无 client 属性(AttributeError), 且为日志
        字符串发起 tracker 请求不值得。与 FakeTorrent.tracker_name 行为对齐。
        """
        if self.tracker_conf is not None:
            if self.tracker_conf.tags is not None and len(self.tracker_conf.tags) > 0:
                return self.tracker_conf.tags[0]
            return self.tracker_conf.name
        return "Unknown"

    @property
    def log_repr(self) -> str:
        """日志输出简化表示"""
        return f"'{self.name}' [{self.tracker_name}] ({self.hash[:8]})"

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
    def state_enum(self) -> TorrentState:
        """由 state 字符串构造的 TorrentState(与 qB 版本无关的状态类别判定)"""
        if self._state_enum is None and TorrentState is not None:
            try:
                self._state_enum = TorrentState(self.state)
            except ValueError:
                self._state_enum = TorrentState.UNKNOWN
        return self._state_enum

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


# ---------- 辅助方法 ----------

    def check_hr_condition(self) -> bool:
        """是否满足 HR 触发条件(下载比例或下载量), 用于排除辅种

        前置: tracker_conf 已在 _refresh_torrents 阶段匹配(无 None 防御, 早暴露调用路径错误)。
        兜底边界: 未达触发量的种子, 把种子完整下载完(下载量 >= 种子大小)也视为触发——
        否则触发量大于种子体积的小种子永远不会触发(想法.md 已知问题)。
        downloaded=0 的纯辅种(添加时数据已完整, 对本站无下载消耗)与部分下载(如 1B)不触发。
        """
        if not self.tracker_conf.hr:
            return False
        hr = self.tracker_conf.hr
        cond_type, cond_value = hr.condition
        if cond_type == "dlratio":
            if self.total_size == 0:  # 无实际数据量(总大小为0), 辅种排除兜底, 不视为触发
                return False
            if (self.downloaded / self.total_size) >= cond_value:
                return True
        elif cond_type == "dlsize":
            if self.downloaded >= cond_value:
                return True
        return self.total_size > 0 and self.downloaded >= self.total_size

    def check_hr_satisfied(self) -> bool:
        """是否满足 HR 要求: 触发条件 + (做种时长 >= 要求时间 + 额外时间 或 分享率达标)"""
        if not self.tracker_conf.hr:
            return False
        hr = self.tracker_conf.hr
        if not self.check_hr_condition():
            return False
        seeding_ok = self.seeding_time >= (hr.required_seeding_time + hr.extra_seeding_time)
        ratio_ok = hr.required_share_ratio > 0 and self.ratio >= hr.required_share_ratio
        return seeding_ok or ratio_ok


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

    def refresh(self, tors: List[TorrentDictionary]) -> Tuple[List[str], List[str]]:
        """全量刷新快照: 返回 (added, removed) hash 列表

        首轮(_known_hashes is None)全部视为新增(与旧 _known_hashes 语义一致);
        已存在的记录对象原地更新, 惰性缓存跨 tick 存活。
        """
        new_by_hash: Dict[str, TorrentRecord] = {}
        for t in tors:
            h = t.hash
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

    def get(self, hash: str) -> Optional[TorrentRecord]:
        return self.by_hash.get(hash)

    def __contains__(self, hash: str) -> bool:
        return hash in self.by_hash

    def __len__(self) -> int:
        return len(self.by_hash)

    def all(self) -> List[TorrentRecord]:
        return list(self.by_hash.values())

    def hashes(self) -> List[str]:
        return list(self.by_hash)

    def update_state_snapshot(self, tors: List[TorrentDictionary]) -> None:
        """本轮结束前更新状态快照(存 state_enum 枚举对象, 与 qB 版本无关)"""
        self.state_snapshot = {t.hash: getattr(t, "state_enum", None) for t in tors}

    # ---------- 分组查询接口 ----------

    def group_members(self, hash: str) -> List[str]:
        """种子所属组全部成员 hash; 未归组 -> [自身] 单种子"""
        key = self.member_to_key.get(hash)
        if key is None:
            return [hash]
        return list(self.groups.get(key, [hash]))

    def group_key(self, hash: str) -> Optional[Any]:
        """种子所属组 key; 未归组 -> None"""
        return self.member_to_key.get(hash)

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

    # ---------- 写操作同步(供 QbApi Facade调用) ----------

    def reset_runtime(self) -> None:
        """热重载配置后的运行态重置: 清分组索引/缓存/状态快照/校验记录;
        种子记录保留(tracker_conf 置空, 由下一轮全量 refresh 重匹配)"""
        self.groups.clear()
        self.group_sizes.clear()
        self.member_to_key.clear()
        self.state_snapshot.clear()
        self.verified_references.clear()
        self.invalidate_tags()
        self.invalidate_categories()
        for rec in self.by_hash.values():
            rec.tracker_conf = None

    def update_torrent_fields(
        self,
        torrent_hashes: Union[str, List[str]],
        *,
        tags_add: Optional[List[str]] = None,
        tags_remove: Optional[List[str]] = None,
        category: Optional[str] = None,
        state: Optional[str] = None,
        up_limit: Optional[int] = None,
        dl_limit: Optional[int] = None,
        save_path: Optional[str] = None,
    ) -> None:
        """写操作后同步快照字段(单 hash 或 hash 列表)

        由 QbApi Facade调用: 调用客户端 API 后立即更新内存快照, 保证同 tick 内
        后续读取(如 tag_usage / 分类判断 / 限速幂等)读到最新值; 下轮 refresh 校准。
        tags_add/tags_remove 合并式更新并失效 _tags_set, state 变化失效 _state_enum。
        """
        hashes = [torrent_hashes] if isinstance(torrent_hashes, str) else list(torrent_hashes or [])
        tags_changed = tags_add is not None or tags_remove is not None
        state_changed = state is not None
        for h in hashes:
            torrent = self.by_hash.get(h)
            if torrent is None:
                continue
            if tags_add is not None:
                current = set(torrent.tags_set)
                current.update(tags_add)
                torrent.tags = ",".join(sorted(current))
            if tags_remove is not None:
                current = set(torrent.tags_set)
                current.difference_update(tags_remove)
                torrent.tags = ",".join(sorted(current))
            if category is not None:
                torrent.category = category
            if state is not None:
                torrent.state = state
            if up_limit is not None:
                torrent.up_limit = up_limit
            if dl_limit is not None:
                torrent.dl_limit = dl_limit
            if save_path is not None:
                torrent.save_path = save_path
            if tags_changed:
                torrent._tags_set = None
            if state_changed:
                torrent._state_enum = None

    def apply_tag_removal(self, tags: List[str]) -> None:
        """torrents_delete_tags 后从所有记录移除已删除标签(定义删除 = 所有种子移除)"""
        tags = set(tags or [])
        if not tags:
            return
        for torrent in self.by_hash.values():
            cur = torrent.tags_set
            removed = cur & tags
            if removed:
                torrent.tags = ",".join(sorted(cur - removed))
                torrent._tags_set = None

    def remove_torrent(self, hash: str) -> None:
        """种子删除后立即从快照移除(保留 _known_hashes, 下轮 refresh 产生 removed 事件驱动任务/分组清理)"""
        self.by_hash.pop(hash, None)

    def restore_torrent(self, record: TorrentRecord) -> None:
        """跳检重加后恢复删除前记录(tracker_conf/惰性缓存保留); 幂等

        remove_torrent 移除 by_hash 但保留 _known_hashes(为真实删除的 removed 事件),
        导致重加的同 hash 种子不进下轮 added 列表 -> 永久未匹配(生产 BUG 2026-09-06)。
        此方法把删除前记录放回快照: 下轮 refresh 走 update_from 更新快照字段,
        tracker_conf 与惰性缓存(trackers_info/files)均保留。
        """
        self.by_hash[record.hash] = record
        if self._known_hashes is not None:
            self._known_hashes.add(record.hash)
