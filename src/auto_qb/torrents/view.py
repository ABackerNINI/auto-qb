"""Web 视图字段契约: 展示字段集合 + 量化步长 + 置脏判定(重建依据与展示值共用同一函数)"""
from collections.abc import Iterable
from typing import Any, Dict

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
        # 标签/分类在组级以"成员共同值"展示(前端求交集), 变更须让视图重建
        "tags",
        "category",
        # 添加时间: 组级默认排序键(几乎不变, 加入仅为了"新添加种子"时能即时反映)
        "added_on",
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


_VIEW_FIELD_SET = frozenset(_VIEW_FIELDS)


def view_dirty(changed: Iterable[str]) -> bool:
    """变化字段集是否触及 Web 分组视图的展示字段(_VIEW_FIELDS)

    apply_delta 返回的变化集已按 `view_field_value` 量化过滤(seeding_time 秒级递增不算变化),
    故这里只需集合交集判定。
    """
    return not _VIEW_FIELD_SET.isdisjoint(changed)
