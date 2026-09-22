"""qB 字段契约与版本兼容: 快照字段表 + 版本校验必需字段 + 兼容性异常

torrents 包拆分(2026-09-15 大文件拆分批次三): 字段契约(与 qB TorrentDictionary 对齐)是
record/store 之外的独立关注点 —— 版本漂移检查(REQUIRED_TORRENT_FIELDS)与字段表单一事实源在此。

字段表分层(2026-09-15 全量扩容, 参照真机 TorrentDictionary 字段样例定稿):
- _REQUIRED_SNAPSHOT_FIELDS  版本校验必需(缺失会静默零值 -> 规则基于假数据决策, 启动期 fail-fast);
- RE_ADD_FIELDS              跳检重加必需(CheckAction 引用; 2026-09-15 起同时升格为快照 slots);
- _EXTENSION_FIELDS          全量快照扩展字段, 全部可选 —— 缺失保持 TorrentRecord 默认值
                             (默认值取 qB 自身哨兵: -1 = 从未/未设, -2 = 使用全局默认, eta 8640000 = 无 ETA),
                             老版本 qB / 端点差异不炸; qB 新版本的未声明字段自动落 _raw(数据不丢)。
"""
from collections.abc import Mapping
from typing import List

from ..infra.errors import AutoQbError

# 版本校验必需的快照字段(缺失即静默零值 -> 规则基于假数据决策, 比崩溃更危险, 启动期一并校验)
_REQUIRED_SNAPSHOT_FIELDS = (
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
    # 添加时间(unix 秒): Web 分组视图的默认排序依据(组级取组内最大值), 快照保留供规则条件使用
    "added_on",
)

# 跳检重加所需属性(qB torrent info 直接字段; 单一来源, CheckAction 引用)
RE_ADD_FIELDS = (
    "seq_dl",
    "f_l_piece_prio",
    "ratio_limit",
    "seeding_time_limit",
    "inactive_seeding_time_limit",
    "share_limit_action",
)

# 全量快照扩展字段(参照真机 TorrentDictionary 字段样例定稿, 见 docs/record-full-fields-plan.html):
# 全部可选, 缺失保持记录默认值; 分组注释仅为可读性, 运行期无语义
_EXTENSION_FIELDS = (
    # 传输/会话
    "downloaded_session",
    "uploaded_session",
    "eta",  # qB 哨兵 8640000 = 无 ETA
    "time_active",
    "last_activity",  # -1 = 从未传输
    "availability",
    # tracker/peer 概要
    "num_seeds",
    "num_leechs",
    "num_complete",
    "num_incomplete",
    "tracker",
    "trackers_count",
    "connections_count",
    "connections_limit",
    "reannounce_in",  # 与 reannounce 并存: 不同 qB 版本二选一出现
    "reannounce",
    # 分享/做种限制(-1 = 未设)
    "max_ratio",
    "max_seeding_time",
    "max_inactive_seeding_time",
    # 元数据
    "magnet_uri",
    "infohash_v1",
    "infohash_v2",
    "private",
    "comment",
    "created_by",
    "creation_date",
    "has_metadata",
    "piece_size",
    "pieces_have",
    "pieces_num",
    # 行为/路径
    "auto_tmm",
    "download_path",
    "root_path",
    "force_start",
    "super_seeding",
    "priority",
    "completion_on",  # -1 = 未完成
    "seen_complete",  # -1 = 从未见到完整副本
    "total_wasted",
    "popularity",
    # tracker 状态概要
    "has_tracker_error",
    "has_tracker_warning",
    "has_other_announce_error",
)

# 与 qbittorrentapi TorrentDictionary 一致的快照字段全表(refresh 时逐字段 in-place 更新):
# 必需 21 + 重加升格 6 + 可选扩展 43 = 70
_SNAPSHOT_FIELDS = _REQUIRED_SNAPSHOT_FIELDS + RE_ADD_FIELDS + _EXTENSION_FIELDS

# 版本兼容校验所需全字段(必需快照 + 重加字段): 扩展字段不做必需校验(老版本 qB 可能没有)
REQUIRED_TORRENT_FIELDS = _REQUIRED_SNAPSHOT_FIELDS + RE_ADD_FIELDS

# 热路径成员判定集合(apply_delta 每字段至少一次查询, frozenset 为 C 级哈希查找)
_SNAPSHOT_FIELD_SET = frozenset(_SNAPSHOT_FIELDS)


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
