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

包拆分结构(2026-09-15 大文件拆分批次三):
- compat.py  qB 字段契约与版本兼容(字段表/REQUIRED_TORRENT_FIELDS/QbCompatError)
- view.py    Web 视图字段契约(_VIEW_FIELDS/量化步长/置脏判定)
- record.py  TorrentRecord(种子数据唯一所有者)
- store.py   TorrentStore(增量同步 + 分组索引 + 写后同步)
- __init__.py 全量重导出(调用方 from auto_qb.torrents import X 不变)

说明:
- TorrentRecord 是种子数据的**唯一所有者**(无需中间投影视图): 快照字段走 slots(C 级属性
  访问的热路径; 2026-09-15 起全量缓存 qB 种子对象的全部数据字段, 见 compat._SNAPSHOT_FIELDS),
  未声明字段(qB 新版本)存 `_raw` 并由属性访问兜底; 字段名与
  qbittorrentapi TorrentDictionary 一致, 鸭子类型兼容(可直接传给需要种子对象的代码)。
- apply_delta() 只处理 patch 中的字段(增量轮成本 ∝ 变化字段数), 记录对象跨 tick 保留
  (惰性缓存存活), 种子删除时记录被回收, 缓存自然清理。
- 种子不在快照中但被查询时(如 process_torrent 外部传入对象)退化为直接拉取, 不做缓存。
"""
from .compat import (
    RE_ADD_FIELDS,
    REQUIRED_TORRENT_FIELDS,
    QbCompatError,
    _SNAPSHOT_FIELDS,
    missing_torrent_fields,
)
from .record import TorrentRecord
from .store import TorrentStore
from .view import _VIEW_FIELDS, _VIEW_QUANTUM, view_dirty, view_field_value

__all__ = [
    "TorrentRecord",
    "TorrentStore",
    "QbCompatError",
    "missing_torrent_fields",
    "REQUIRED_TORRENT_FIELDS",
    "RE_ADD_FIELDS",
    "view_dirty",
    "view_field_value",
]
