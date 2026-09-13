"""种子信息数据层(TorrentStore)

设计目标(优先级: 速度 > 可读性 > 内存):
- 每 main_tick 经 qB `/api/v2/sync/maindata` **增量同步**一次(只含变化种子的变化字段,
  未变化种子完全不出现在响应中), 之后本 tick 内所有读取操作(规则条件/动作/分组/标签/
  轮询回调)都只访问本数据层, 不再重复调用
  torrents_info / torrents_trackers / torrents_files / torrents_tags / torrents_categories。
- 惰性缓存: tracker/files 首次访问才拉取并在记录上持久缓存, 种子删除时随记录一起回收;
  全局标签/分类列表缓存, 写操作后失效。
- 分组索引: groups / group_sizes / member_to_key / state_snapshot / download_conflict_warned
  内聚于此, O(1) 定位。
- 写操作(新增/删除/暂停/开始/加删标签/设分类等)仍直接调 qbittorrentapi, 不经过本层;
  本 tick 内的写操作下一 tick 快照刷新后可见。

说明:
- TorrentRecord 是种子数据的**唯一所有者**(无需中间投影视图): 快照字段走 slots(C 级属性
  访问的热路径), 非快照必需字段(RE_ADD_FIELDS)存 `_raw` 并由属性访问兜底; 字段名与
  qbittorrentapi TorrentDictionary 一致, 鸭子类型兼容(可直接传给需要种子对象的代码)。
- apply_delta() 只处理 patch 中的字段(增量轮成本 ∝ 变化字段数), 记录对象跨 tick 保留
  (惰性缓存存活), 种子删除时记录被回收, 缓存自然清理。
- 种子不在快照中但被查询时(如 process_torrent 外部传入对象)退化为直接拉取, 不做缓存。
"""
import logging
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, FrozenSet, List, Optional, Set, Tuple, Union
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

# 热路径成员判定集合(apply_delta 每字段至少一次查询, frozenset 为 C 级哈希查找)
_SNAPSHOT_FIELD_SET = frozenset(_SNAPSHOT_FIELDS)
_VIEW_FIELD_SET = frozenset(_VIEW_FIELDS)

# qB 不支持 sync/maindata(旧版本 / 测试替身缺方法)时的降级信号; 其它异常(网络等)照常上抛
_SYNC_UNAVAILABLE = (AttributeError, NotFound404Error)


def view_dirty(changed: Iterable[str]) -> bool:
    """变化字段集是否触及 Web 分组视图的展示字段(_VIEW_FIELDS)

    apply_delta 返回的变化集已按 `view_field_value` 量化过滤(seeding_time 秒级递增不算变化),
    故这里只需集合交集判定。
    """
    return not _VIEW_FIELD_SET.isdisjoint(changed)


class QbCompatError(AutoQbError):
    """qBittorrent torrent info 字段与预期不符(版本不兼容), 首次拉到种子信息时 fail-fast"""


def missing_torrent_fields(tor) -> List[str]:
    """返回 tor 上缺失的必需字段列表(空列表 = 版本兼容)

    支持两类来源: **字段映射**(qB sync 原始 JSON / 测试注入的 dict -> 按键判定)
    与**属性对象**(TorrentDictionary / FakeTorrent / TorrentRecord -> 按 hasattr 判定)。
    AttrDict 缺键时 hasattr 为 False(不回退 __getattr__), 故两类语义一致。
    """
    if isinstance(tor, Mapping):
        return [f for f in REQUIRED_TORRENT_FIELDS if f not in tor]
    return [f for f in REQUIRED_TORRENT_FIELDS if not hasattr(tor, f)]


@dataclass(slots=True)
class TorrentRecord:
    """种子快照记录: 字段名与 TorrentDictionary 一致, 鸭子类型兼容

    种子数据的**唯一所有者**(无需中间投影视图):
    - 快照字段 = slots(C 级属性访问, 热路径), hash 为主键;
    - 非快照必需字段(RE_ADD_FIELDS, 跳检重加用) = `_raw` dict, 属性访问经 __getattr__ 兜底;
    - 惰性缓存槽(_tags_set/_state_enum/_trackers_info/_files)跨 tick 存活:
      apply_delta() 只更新变化的字段, 缓存随记录对象保留; 种子删除时记录被回收, 缓存自然清理。
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

    # 惰性缓存(不参与 apply_delta 复制)
    _tags_set: Optional[frozenset] = None
    _state_enum: Any = None
    _trackers_info: Optional[List[dict]] = None
    _files: Optional[List[Any]] = None
    # 非快照必需字段(RE_ADD_FIELDS, 跳检重加用): 仅存于此, 属性访问兜底
    _raw: Optional[Dict[str, Any]] = None

    tracker_conf: Optional[TrackerConfig] = None

    def __getattr__(self, name: str) -> Any:
        """非快照字段(如跳检所需的 seq_dl/ratio_limit)兜底读取 `_raw`

        仅在常规属性查找失败时调用(slots 未声明的名字); 缺失仍抛 AttributeError ——
        与 qbittorrentapi AttrDict/TorrentDictionary 语义一致, 故 hasattr 版本校验照常工作。
        用 object.__getattribute__ 读槽, 避免 `_raw` 未初始化时无限递归。
        """
        try:
            raw = object.__getattribute__(self, "_raw")
        except AttributeError:
            raw = None
        if raw is not None:
            try:
                return raw[name]
            except KeyError:
                pass
        raise AttributeError(name)

    @classmethod
    def from_torrent(cls, tor: Any, hash: Optional[str] = None) -> "TorrentRecord":
        """从原始种子对象/字段映射构建新记录(hash 可显式给出: 增量响应以字典键为主键)"""
        rec = cls(hash=hash if hash is not None else getattr(tor, "hash", ""))
        rec.apply_delta(tor)
        return rec

    def apply_delta(self, patch: Any) -> FrozenSet[str]:
        """用 patch 中的字段更新快照, 返回本轮**变化字段名集合**(空 = 无变化)

        增量成本 ∝ patch 字段数: patch 为 Mapping(qB sync 响应/测试 dict/真机
        TorrentDictionary)时只遍历其键 —— 故未变化的种子/字段零开销; 为普通对象
        (测试替身 FakeTorrent 等)时按 REQUIRED_TORRENT_FIELDS 收集属性。

        快照字段写入 slot; 非快照字段(RE_ADD_FIELDS)写入 `_raw`(不计入变化集)。
        视图字段中配了 `_VIEW_QUANTUM` 步长的按量化值比较(seeding_time 秒级递增不算变化),
        故返回值可直接用 `view_dirty()` 判定是否需要重建 Web 分组视图。

        性能: 真机 TorrentDictionary 是 Mapping, 字段以映射条目存储, 故走 .items()
        (C 级迭代) 而不逐个 getattr(AttrDict.__getattr__→_build 属性派发慢 ~13×)。
        """
        changed: Set[str] = set()
        if isinstance(patch, Mapping):
            items = patch.items()
        else:  # TODO: 移除下方的测试专用通道
            items = ((f, getattr(patch, f, None)) for f in REQUIRED_TORRENT_FIELDS)
        raw = self._raw
        for f, v in items:
            if v is None or f == "hash":
                continue  # hash 是主键; None 视为"未提供"(与历史 update_from 一致)
            if f not in _SNAPSHOT_FIELD_SET:
                # 非快照字段(RE_ADD_FIELDS 等): 存 _raw 供属性访问兜底, 不参与视图脏判定
                if raw is None:
                    raw = self._raw = {}
                raw[f] = v
                continue
            cur = getattr(self, f)
            if cur == v:
                continue
            setattr(self, f, v)
            if f == "state":
                self._state_enum = None
            elif f == "tags":
                self._tags_set = None
            if f not in _VIEW_FIELD_SET:
                changed.add(f)  # 非视图字段: 值已不同即计入
            elif f not in _VIEW_QUANTUM or view_field_value(f, cur) != view_field_value(f, v):
                changed.add(f)  # 视图字段: 量化后确实变化才算
        return frozenset(changed)

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
    """种子信息数据层: 主索引 + 增量同步 + 惰性缓存 + 分组索引 + 全局标签/分类缓存

    增量同步态(qB /api/v2/sync/maindata rid 语义, 见 apply_sync):
      - rid: 上次响应 ID(0 = 下轮需全量); need_validate: 本轮是否全量(校验闸门);
      - using_fallback: 已降级全量(旧版 qB, 告警去重); validate_sample: 全量轮校验样本。
    分组相关结构(供 GroupingMixin 直接读写, 保持增量语义):
      - groups:        key=(save_path, 排序文件路径元组) -> [hash...]
      - group_sizes:   key -> {hash: {规范化相对路径: 大小}}
      - member_to_key: hash -> 组 key(O(1) 定位)
      - state_snapshot: hash -> 上一轮 state_enum(上传转暂停检测)
      - download_conflict_warned: (组key, 冲突类型) 去重集合
    本轮变化集(供主循环把 O(N) 扫描降为 O(变化数)):
      - delta_fields:  {hash: 变化字段名集合} 本轮发生变化的种子
      - state_changed: [(hash, fetch 时 state_enum)] state 字段变化的种子
      - dirty_groups:  需重算下载冲突的组 key(字段变化/成员增删/归组变化时登记)
    参考种子集合(仅内存): verified_references
    全局缓存: all_tags() / all_categories()(写操作后 invalidate)
    """
    def __init__(self, client: Any = None):
        self.client: Any = client
        # 主索引: hash -> TorrentRecord(每轮原子替换引用, 记录对象跨 tick 保留)
        self.by_hash: Dict[str, TorrentRecord] = {}
        # 本程序自身发起删除、待下轮上报的 hash(remove_torrent 登记 / restore_torrent 撤销)
        self._pending_removed: Set[str] = set()
        # 增量同步态
        self.rid: int = 0
        self.need_validate: bool = True
        self.using_fallback: bool = False
        self.validate_sample: Optional[Any] = None
        # 本轮变化集
        self.delta_fields: Dict[str, FrozenSet[str]] = {}
        self.state_changed: List[Tuple[str, Any]] = []
        # 需重算下载冲突的组 key: 变化字段/成员增删/归组/自有停种打标时登记,
        # 由 GroupingMixin._check_download_conflicts 取出并复位(跨轮累积, 不随 _apply 清空)
        self.dirty_groups: Set[Any] = set()
        # 轮次基线: >0 表示快照由主循环轮次驱动(变化集可用), 冲突检查走增量;
        # 直接驱动(_apply 未跑过, 如白盒测试)时为 0, 冲突检查退回全量扫描以保证正确
        self.rounds_applied: int = 0
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

    # ---------- 快照(增量同步) ----------

    def apply_sync(self, api: "QbApi") -> Tuple[List[str], List[str]]:
        """主循环入口: 从 qB 增量同步一轮并应用, 返回 (added, removed)

        /api/v2/sync/maindata 语义(见 src/webui/api/synccontroller.cpp):
          - full_update=true(首轮 / rid 失效) -> 响应含**全部种子全量字段**;
          - rid 一致 -> 只含**变化种子**的**变化字段**(未变化种子不出现),
            删除的种子列在 torrents_removed。
        端点不可用(旧版 qB / 测试替身缺方法)时降级为全量 torrents_info(一次性告警);
        其它异常 rid 归零后原样上抛(由调用方兜底, 不掩盖断连/鉴权问题)。
        """
        try:
            md = api.sync_maindata(rid=self.rid)
        except _SYNC_UNAVAILABLE as e:
            if not self.using_fallback:
                logger.warning(f"qB 不支持 sync/maindata, 降级为全量 torrents_info: {e}")
                self.using_fallback = True
            self.rid = 0
            self.need_validate = True
            tors = api.torrents_info()
            # 样本保持旧时序语义: 首个非 dict 的真实种子对象(测试注入的 plain dict 不作样本)
            self.validate_sample = next((t for t in tors if not isinstance(t, dict)), None)
            return self.refresh(tors)
        except Exception:
            self.rid = 0  # 未知异常: 下轮强制全量
            raise
        self.using_fallback = False
        self.rid = int(md.get("rid", 0) or 0)
        full = bool(md.get("full_update"))
        self.need_validate = full
        patches = md.get("torrents") or {}
        # 校验样本: 仅全量轮提供。注意 qB sync 响应的 **hash 是 torrents 字典的键**, 值内不含
        # hash(与 torrents/info 的数组元素不同) -> 校验前需补齐, 否则必报缺 'hash' 字段
        if full and patches:
            h0, p0 = next(iter(patches.items()))
            self.validate_sample = {**p0, "hash": h0} if isinstance(p0, Mapping) else p0
        else:
            self.validate_sample = None
        return self._apply(patches, list(md.get("torrents_removed") or []), full=full)

    def refresh(self, tors: List[TorrentDictionary]) -> Tuple[List[str], List[str]]:
        """全量刷新入口(测试/降级路径): 以给定种子列表为全集, 返回 (added, removed)

        已存在记录对象原地更新(惰性缓存跨 tick 存活), 首轮全部视为新增。
        """
        patches: Dict[str, Any] = {}
        for t in tors:
            h = t.get("hash") if isinstance(t, Mapping) else getattr(t, "hash", None)
            if h:
                patches[h] = t
        return self._apply(patches, [], full=True)

    def reset_sync(self) -> None:
        """重置增量同步态(重连 / 热重载后旧 rid 失效, 下轮强制全量重建)"""
        self.rid = 0
        self.need_validate = True
        self.using_fallback = False
        self.validate_sample = None
        self.delta_fields = {}
        self.state_changed = []
        self.dirty_groups = set()

    # 影响下载冲突判定的字段(分组 n_dl/n_done 的判定依据)
    _CONFLICT_FIELDS = frozenset(("state", "amount_left", "tags"))

    def _apply(self, patches: Dict[str, Any], removed: List[str], *, full: bool) -> Tuple[List[str], List[str]]:
        """核心: 把 patches 应用到快照(原子替换 by_hash, Web 线程只读安全), 返回 (added, removed)

        full=True: patches 为全集, 未出现者视为删除;
        full=False(增量): patches 只含变化种子, 其余记录原样保留, 删除以 removed(torrents_removed)为准。
        本轮无任何变化且无待报删除时提前返回 —— 静止种子库的每 tick 成本趋近于 0。
        """
        pending = self._pending_removed
        self.rounds_applied += 1
        # 增量轮无变化且无待报删除 -> 零成本早退; 全量轮即使 patches 为空也必须走完(需检测删除)
        if not full and not patches and not removed and not pending:
            self.delta_fields = {}
            self.state_changed = []
            return [], []
        prev = self.by_hash
        by_hash = {} if full else dict(prev)  # 全量重建 / 增量: C 级浅拷贝, 未变化记录原样保留
        added: List[str] = []
        changes = list(removed)
        view_changed = False
        delta_fields: Dict[str, FrozenSet[str]] = {}
        state_changed: List[Tuple[str, Any]] = []
        member_to_key = self.member_to_key
        for h, src in patches.items():
            rec = prev.get(h)
            if rec is None:
                rec = TorrentRecord.from_torrent(src, hash=h)
                added.append(h)
            else:
                changed = rec.apply_delta(src)
                if changed:
                    delta_fields[h] = changed
                    if not _VIEW_FIELD_SET.isdisjoint(changed):
                        view_changed = True
                    if "state" in changed:
                        state_changed.append((h, rec.state_enum))
                    if not self._CONFLICT_FIELDS.isdisjoint(changed):
                        key = member_to_key.get(h)
                        if key is not None:
                            self.dirty_groups.add(key)
            by_hash[h] = rec
        if full:
            # 全量: by_hash 由本轮响应重建, 旧快照中未出现者即已删除
            changes.extend(h for h in prev if h not in patches)
        else:
            for h in changes:
                by_hash.pop(h, None)
        # 本程序自身发起的删除(remove_torrent): qB 增量响应不一定会再列出, 由待报集合补齐
        changes.extend(h for h in pending if h not in by_hash)
        pending.clear()
        if changes:
            changes = list(dict.fromkeys(changes))
        # 被删除成员的原组需重算冲突(member_to_key 在下游取消归组前仍可定位)
        for h in changes:
            key = member_to_key.get(h)
            if key is not None:
                self.dirty_groups.add(key)
        self.by_hash = by_hash
        self.delta_fields = delta_fields
        self.state_changed = state_changed
        if view_changed or added or changes:
            self.view_changed = True
        return added, changes

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

    def update_state_snapshot(self) -> None:
        """本轮结束前更新状态快照(hash -> state_enum)

        直接取本轮 by_hash 的状态(record.state_enum 有缓存, 与 qB 版本无关): 自有动作
        经 QbApi 同步过的状态同样计入, 故下轮不会被误判为外部状态变化。
        """
        self.state_snapshot = {h: r.state_enum for h, r in self.by_hash.items()}

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
            if state_changed or tags_changed:
                # 自有停种/打标会改变组内冲突判定, 登记组级脏标记(下轮 qB 增量不会重报同样值)
                key = self.member_to_key.get(h)
                if key is not None:
                    self.dirty_groups.add(key)
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
                key = self.member_to_key.get(torrent.hash)
                if key is not None:
                    self.dirty_groups.add(key)

    def remove_torrent(self, hash: str) -> None:
        """种子删除后立即从快照移除, 并登记待报 removed(供下轮 added/removed 语义)"""
        if self.by_hash.pop(hash, None) is not None:
            self._pending_removed.add(hash)

    def restore_torrent(self, record: TorrentRecord) -> None:
        """跳检重加后恢复删除前记录(tracker_conf/惰性缓存保留); 幂等

        remove_torrent 会登记待报 removed; 此处撤销登记 —— 否则重加的同 hash 种子下轮
        被误判为"已删除"(多余的组内缺文件扫描与 on_torrent_deleted 事件)。
        """
        self.by_hash[record.hash] = record
        self._pending_removed.discard(record.hash)
