"""TorrentRecord: 种子快照记录(种子数据的唯一所有者, slots + 惰性缓存 + HR 判定)"""
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Dict, FrozenSet, List, Optional, Set

from qbittorrentapi import TorrentState

from ..config import TrackerConfig
from .compat import REQUIRED_TORRENT_FIELDS, _SNAPSHOT_FIELDS, _SNAPSHOT_FIELD_SET
from .view import _VIEW_FIELD_SET, _VIEW_QUANTUM, view_field_value


@dataclass(slots=True)
class TorrentRecord:
    """种子快照记录: 字段名与 TorrentDictionary 一致, 鸭子类型兼容

    种子数据的**唯一所有者**(无需中间投影视图):
    - 快照字段 = slots(C 级属性访问, 热路径), hash 为主键; 字段表单一来源 = compat._SNAPSHOT_FIELDS
      (2026-09-15 全量扩容: 缓存 qB 种子对象的全部数据字段, 为 WebUI 后续功能供数);
    - 可选扩展字段缺失时保持 qB 哨兵默认值(-1 = 从未/未设, -2 = 使用全局默认, eta 8640000 = 无 ETA);
    - 未声明字段(qB 新版本前向兼容) = `_raw` dict, 属性访问经 __getattr__ 兜底;
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
    added_on: int = 0

    # ---- 限制策略(原 RE_ADD_FIELDS, 自 _raw 升格; -2 = 使用全局默认, -1 = 无限制) ----
    seq_dl: bool = False
    f_l_piece_prio: bool = False
    ratio_limit: float = -2.0
    seeding_time_limit: int = -2
    inactive_seeding_time_limit: int = -2
    share_limit_action: str = "Default"
    # ---- 传输/会话 ----
    downloaded_session: int = 0
    uploaded_session: int = 0
    eta: int = 8640000  # qB 哨兵: 8640000 = 无 ETA
    time_active: int = 0
    last_activity: int = -1  # -1 = 从未传输
    availability: float = 0.0
    # ---- tracker/peer 概要 ----
    num_seeds: int = 0
    num_leechs: int = 0
    num_complete: int = 0
    num_incomplete: int = 0
    tracker: str = ""
    trackers_count: int = 0
    connections_count: int = 0
    connections_limit: int = 0
    reannounce_in: int = 0  # 与 reannounce 并存: 不同 qB 版本二选一出现
    reannounce: int = 0
    # ---- 分享/做种限制(-1 = 未设) ----
    max_ratio: float = -1.0
    max_seeding_time: int = -1
    max_inactive_seeding_time: int = -1
    # ---- 元数据 ----
    magnet_uri: str = ""
    infohash_v1: str = ""
    infohash_v2: str = ""
    private: bool = False
    comment: str = ""
    created_by: str = ""
    creation_date: int = 0
    has_metadata: bool = False
    piece_size: int = 0
    pieces_have: int = 0
    pieces_num: int = 0
    # ---- 行为/路径 ----
    auto_tmm: bool = False
    download_path: str = ""
    root_path: str = ""
    force_start: bool = False
    super_seeding: bool = False
    priority: int = 0
    completion_on: int = -1  # -1 = 未完成
    seen_complete: int = -1  # -1 = 从未见到完整副本
    total_wasted: int = 0
    popularity: float = 0.0
    # ---- tracker 状态概要 ----
    has_tracker_error: bool = False
    has_tracker_warning: bool = False
    has_other_announce_error: bool = False

    # ---- 错误原因展示(WebUI 状态列的"具体错误"文本) ----
    # qB torrents/info **不含**任何错误文本(已核实 Web API), 原因只能从 torrents/trackers
    # 的 msg 取; 由 WebviewMixin.refresh_error_reasons 在主循环按 TTL 限额预取后写在此处,
    # 视图组装只读缓存(视图可能每 tick 重建, 不能在里面发 API)。
    # 非快照字段: 不进 _SNAPSHOT_FIELDS/_raw, 不参与 apply_delta 与视图脏判定(变化由预取方显式置脏)。
    tracker_error_msg: str = ""
    tracker_error_ts: float = 0.0

    # 惰性缓存(不参与 apply_delta 复制)
    _tags_set: Optional[frozenset] = None
    _state_enum: Any = None
    _trackers_info: Optional[List[dict]] = None
    _files: Optional[List[Any]] = None
    # 未声明字段(qB 新版本前向兼容): 仅存于此, 属性访问兜底
    _raw: Optional[Dict[str, Any]] = None

    tracker_conf: Optional[TrackerConfig] = None

    def __getattr__(self, name: str) -> Any:
        """未声明字段(qB 新版本新增)兜底读取 `_raw`(前向兼容, 数据不丢)

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

        快照字段写入 slot; 未声明字段(qB 新版本前向兼容)写入 `_raw`(不计入变化集)。
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
                # 未声明字段(qB 新版本前向兼容): 存 _raw 供属性访问兜底, 不参与视图脏判定
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

    def to_dict(self) -> Dict[str, Any]:
        """全字段导出: 快照 slots(顺序同 _SNAPSHOT_FIELDS) + _raw 前向兼容字段合并

        未来 WebUI 详情接口的取数入口; 惰性缓存槽(_tags_set/_state_enum/_trackers_info/_files)
        与 tracker_conf 不进导出。字段值原样透传(qB 哨兵 -1/-2/8640000 不解读, 展示层自行翻译)。
        """
        out = {f: getattr(self, f) for f in _SNAPSHOT_FIELDS}
        raw = self._raw
        if raw:
            out.update(raw)
        return out

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

    def invalidate_trackers(self) -> None:
        """tracker 写操作后失效本记录的 tracker 惰性缓存(下轮 trackers_info 重新拉取)

        由 QbApi 的 tracker 写操作(add/edit/remove_trackers)在主循环线程调用,
        保证同 tick 内后续读取(如强制汇报基线)拿到写后新值。
        """
        self._trackers_info = None

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
