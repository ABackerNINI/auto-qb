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
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple, Union
from qbittorrentapi import NotFound404Error, TorrentState, TorrentDictionary

from . import utils
from .config import TrackerConfig
from .errors import AutoQbError

if TYPE_CHECKING:  # 仅用于类型标注, 避免与 qbapi 形成运行期循环导入
    from .qbapi import QbApi

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

# Web 分组视图展示的字段: 仅这些字段变化才需重建视图(_build_group_view 的取值集合),
# 避免种子库无变化时主循环空转重建; save_path 决定分组键, 故一并计入
_VIEW_FIELDS = frozenset(
    (
        "name",
        "save_path",
        "state",
        "dlspeed",
        "upspeed",
        "uploaded",
        "size",
        "progress",
        "seeding_time",
        "ratio",
    )
)

# 视图字段量化步长: 该字段在 Web 视图中按此步长取整, 重建判定与展示值共用同一步长
# (保证"视图内容"与"脏标记依据"一致, 否则前端展示会与实际重建时机脱钩)。
# seeding_time 每秒递增 —— 不量化时做种中的种子会每轮置脏, 使惰性重建对绝大多数种子失效;
# 前端本就只展示到分钟, 故取整到 60s 无任何可见损失。
_VIEW_QUANTUM: Dict[str, int] = {"seeding_time": 60}


def view_field_value(field: str, value: Any) -> Any:
    """视图字段的量化值(重建判定与 `_build_group_view` 展示值共用的唯一取整入口)

    未配置步长的字段原样返回(精确比较)。seeding_time 等单调递增但展示精度有限的字段
    按 `_VIEW_QUANTUM` 取整, 避免活跃但数据无实质变化的种子库每 tick 重建视图。
    """
    q = _VIEW_QUANTUM.get(field)
    if q:
        return value // q * q
    return value


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

    def update_from(self, tor: Any) -> bool:
        """用最新种子对象更新快照字段(惰性缓存保留, 文本派生缓存失效)

        返回: 是否有**视图相关字段**变化(_VIEW_FIELDS, 按 _VIEW_QUANTUM 量化后比较)
        —— Web 分组视图惰性重建用。判定与 Web 展示字段保持一致, 不引入额外遍历
        (复用本方法已有的逐字段循环)。

        性能: 真机 qbittorrentapi TorrentDictionary 是 Mapping, 其字段以映射条目存储,
        用 .get() 走 C 级 item 访问, 比 getattr 触发 AttrDict.__getattr__→_build 的属性派发
        快 ~13×(py-spy 实测 __getattr__ 占 17% CPU)。快照字段全为标量, _build 对其是 no-op,
        故 .get() 与 getattr 返回值一致。测试替身 FakeTorrent 等普通对象非 Mapping, 回退属性访问。
        """
        self.tor = tor
        changed = False
        if isinstance(tor, Mapping):
            get = tor.get
            for f in _SNAPSHOT_FIELDS:
                if f == "hash":
                    continue  # hash 是主键, 不更新
                v = get(f)
                if v is not None:
                    if f in _VIEW_FIELDS and view_field_value(f, getattr(self, f)) != view_field_value(f, v):
                        changed = True
                    setattr(self, f, v)
        else:  # TODO: 移除下方的测试专用通道
            for f in _SNAPSHOT_FIELDS:
                if f == "hash":
                    continue  # hash 是主键, 不更新
                v = getattr(tor, f, None)
                if v is not None:
                    if f in _VIEW_FIELDS and view_field_value(f, getattr(self, f)) != view_field_value(f, v):
                        changed = True
                    setattr(self, f, v)
        self._tags_set = None
        self._state_enum = None
        return changed

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
        # Web 分组视图需重建标记: 视图相关字段(_VIEW_FIELDS)或组成员变化时置真,
        # 主循环每 tick 消费(consume_view_changed), 无变化则不重建(惰性真正生效)
        self.view_changed: bool = True

    # ---------- 快照 ----------

    def refresh(self, tors: List[TorrentDictionary]) -> Tuple[List[str], List[str]]:
        """全量刷新快照: 返回 (added, removed) hash 列表

        首轮(_known_hashes is None)全部视为新增(与旧 _known_hashes 语义一致);
        已存在的记录对象原地更新, 惰性缓存跨 tick 存活。
        同时累计 view_changed(视图字段/成员变化), 供 Web 分组视图惰性重建。
        """
        new_by_hash: Dict[str, TorrentRecord] = {}
        view_changed = False
        for t in tors:
            h = t.hash
            rec = self.by_hash.get(h)
            if rec is None:
                rec = TorrentRecord.from_torrent(t)
            elif bool(rec.update_from(t)):
                view_changed = True
            new_by_hash[h] = rec

        if self._known_hashes is None:
            added = list(new_by_hash)
            removed: List[str] = []
        else:
            added = [h for h in new_by_hash if h not in self._known_hashes]
            removed = [h for h in self._known_hashes if h not in new_by_hash]

        self.by_hash = new_by_hash
        self._known_hashes = set(new_by_hash)
        if view_changed or added or removed:
            self.view_changed = True
        return added, removed

    def consume_view_changed(self) -> bool:
        """读取并复位"分组视图需重建"标记(主循环每 tick 消费一次)"""
        changed = self.view_changed
        self.view_changed = False
        return changed

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
        self.view_changed = True  # 分组索引已清空, 视图必须重建
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
        # state/save_path 属视图展示字段: 写操作后视图需重建(tags/category/限速不影响展示)
        if state_changed or save_path is not None:
            self.view_changed = True
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


# ---------- 增量同步层(qB /api/v2/sync/maindata, rid 语义) ----------

# qB 不支持该端点(旧版本/测试替身缺方法)时的降级信号; 其它异常(网络等)照常上抛
_SYNC_UNAVAILABLE = (AttributeError, NotFound404Error)


class SyncTorrent(Mapping):
    """qB 增量同步合并后的种子字段视图(鸭子类型兼容 TorrentDictionary)

    与 TorrentRecord 的分工: TorrentRecord 是业务快照(含 tracker_conf/惰性缓存),
    本类只是"qB 原始字段"的轻量视图, 供 store.refresh 读取。

    - Mapping 协议: 支持 .get()/in/迭代, 使 TorrentRecord.update_from 走 dict 级
      item 访问快路径(实机约快 13×), 不需要额外的 dict 拷贝
    - 属性访问: __getattr__ 直接取字段, 缺失抛 AttributeError —— 对齐 AttrDict/
      TorrentDictionary 语义, 故 store/规则/跳检等按属性读取的既有代码零改动
    - state_enum: 由 state 字符串构造(TorrentState 为 str 枚举, 成员单例)
    - 非 dict 子类: 版本兼容校验的样本选择(跳过测试注入的 plain dict)不受影响

    _fields 为 TorrentSync 持有的**可变 baseline dict**, 增量轮就地更新。
    """
    __slots__ = ("_fields", )

    def __init__(self, fields: Dict[str, Any]) -> None:
        self._fields = fields

    # ---------- Mapping 协议 ----------

    def __getitem__(self, key: str) -> Any:
        return self._fields[key]

    def __iter__(self):
        return iter(self._fields)

    def __len__(self) -> int:
        return len(self._fields)

    # ---------- 属性访问(对齐 TorrentDictionary/AttrDict) ----------

    def __getattr__(self, name: str) -> Any:
        try:
            fields = object.__getattribute__(self, "_fields")
        except AttributeError:
            raise AttributeError(name) from None
        try:
            return fields[name]
        except KeyError:
            raise AttributeError(name) from None

    @property
    def state_enum(self) -> Optional[TorrentState]:
        """由 state 字符串构造的状态枚举(与 TorrentRecord.state_enum 同语义)"""
        if TorrentState is None:
            return None
        try:
            return TorrentState(self._fields.get("state", ""))
        except ValueError:
            return TorrentState.UNKNOWN

    def merge(self, patch: Any, *, hash: str) -> None:
        """把增量字段合并进本视图(baseline 合并后始终为全量字段)

        patch 为 Mapping(qB 正式响应/测试 dict)时逐键合并; 为普通对象(测试替身
        FakeTorrent 等)时按必需字段收集属性 —— 与 TorrentRecord.update_from 的
        Mapping/对象双通道一致。hash 缺失时用响应键补上(主键不可缺)。
        """
        if isinstance(patch, Mapping):
            self._fields.update(patch)
        else:
            for f in REQUIRED_TORRENT_FIELDS:
                v = getattr(patch, f, None)
                if v is not None:
                    self._fields[f] = v
        self._fields.setdefault("hash", hash)


class TorrentSync:
    """主循环 ↔ qB 增量同步层: 用 rid 只取变化部分, 替代每 tick 全量 torrents_info

    qB 的 /sync/maindata 语义(见 src/webui/api/synccontroller.cpp):
      - rid 与上次不一致 -> full_update=true, 响应含全部种子全量字段;
      - rid 一致 -> 只含**变化种子**的**变化字段**, 未变化种子完全不出现在响应中;
      - 删除的种子列在 torrents_removed(哈希列表)。
    故本地 baseline 视图集合即"当前全量种子集", 与旧的全量拉取语义等价。

    full_update 是自愈信号: rid 失效(漏 tick/服务端重启/rid 循环错位)时 qB 自动回全量,
    本地视图整体重建。端点不可用(旧版 qB / 测试替身)时降级为全量 torrents_info。
    """
    def __init__(self) -> None:
        self.rid: int = 0
        self.need_validate: bool = True  # 本轮为全量(需做版本兼容字段校验)
        self.using_fallback: bool = False  # 已降级全量(告警去重)
        self.validate_sample: Optional[Any] = None  # 全量轮的校验样本(空 qB -> None)
        self._views: Dict[str, SyncTorrent] = {}

    def reset(self) -> None:
        """重置 rid 与本地视图(重连/热重载后旧 rid 失效, 下轮强制全量重建)"""
        self.rid = 0
        self.need_validate = True
        self.using_fallback = False
        self.validate_sample = None
        self._views = {}

    def fetch(self, api: "QbApi") -> List[SyncTorrent]:
        """拉取一轮种子视图: 增量合并(首次/失效时全量重建), 返回全部种子视图列表"""
        try:
            md = api.sync_maindata(rid=self.rid)
        except _SYNC_UNAVAILABLE as e:
            if not self.using_fallback:
                logger.warning(f"qB 不支持 sync/maindata, 降级为全量 torrents_info: {e}")
                self.using_fallback = True
            return self._rebuild(api.torrents_info())
        except Exception:
            self.rid = 0  # 未知异常: 下轮强制全量, 异常照常上抛(由调用方兜底处理)
            raise
        self.using_fallback = False
        self.rid = int(md.get("rid", 0) or 0)
        self.need_validate = bool(md.get("full_update"))
        if self.need_validate:
            self._views = {}  # 全量轮: 丢弃旧基线, 由本轮响应重建
        for h, patch in (md.get("torrents") or {}).items():
            view = self._views.get(h)
            if view is None:
                view = SyncTorrent({})
                self._views[h] = view
            view.merge(patch, hash=h)
        for h in md.get("torrents_removed") or []:
            self._views.pop(h, None)
        # 校验样本: 仅全量轮提供(sync 路径样本恒为合并视图 —— 全量响应含全部必需字段;
        # 增量轮只含变化字段, 不能作样本, 置 None)
        self.validate_sample = next(iter(self._views.values()), None) if self.need_validate else None
        return list(self._views.values())

    def _rebuild(self, tors: List[Any]) -> List[SyncTorrent]:
        """用全量种子列表重建视图(降级路径: 旧版 qB / 测试替身无 sync 端点)

        校验样本仍按旧语义取首个非 dict 对象(真实 API 恒为 TorrentDictionary;
        测试注入的 plain dict 不作样本), 避免测试夹具触发误报。
        """
        views: Dict[str, SyncTorrent] = {}
        for t in tors:
            h = t.get("hash") if isinstance(t, Mapping) else getattr(t, "hash", None)
            if not h:
                continue
            view = SyncTorrent({})
            view.merge(t, hash=h)
            views[h] = view
        self.rid = 0
        self.need_validate = True
        self.validate_sample = next((t for t in tors if not isinstance(t, dict)), None)
        self._views = views
        return list(views.values())
