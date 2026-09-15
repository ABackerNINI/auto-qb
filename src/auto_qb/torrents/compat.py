"""qB 字段契约与版本兼容: 快照字段表 + 版本校验必需字段 + 兼容性异常

torrents 包拆分(2026-09-15 大文件拆分批次三): 字段契约(与 qB TorrentDictionary 对齐)是
record/store 之外的独立关注点 —— 版本漂移检查(REQUIRED_TORRENT_FIELDS)与字段表单一事实源在此。
"""
from collections.abc import Mapping
from typing import List

from ..errors import AutoQbError

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
    # 添加时间(unix 秒): Web 分组视图的默认排序依据(组级取组内最大值), 快照保留供规则条件使用
    "added_on",
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
