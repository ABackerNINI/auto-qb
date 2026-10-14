"""Web 视图字段契约: 展示字段集合 + 量化步长 + 置脏判定(重建依据与展示值共用同一函数)"""
from collections.abc import Iterable
from typing import Any, Dict

from .compat import _SNAPSHOT_FIELD_SET

# Web 视图展示字段: 仅这些字段变化才需重建视图(分组/平铺等所有 Web 视图的取值集合 ——
# 分组展示字段 ∪ 种子平铺视图(SEED_ITEM, WEB UI 替代 qB 界面的种子页)原始数据字段,
# 平铺列表/详情抽屉要展示它们, 变化同样须触发重建), 避免种子库无变化时主循环空转重建;
# save_path 决定分组键, 故一并计入。
# 派derive 而非手抄(issue 26-10-11-0352 修复): 展示表 = 快照全表(compat 单点) - 不展示缺口
# —— 新增快照字段默认进脏判定(多余重建无害); 手抄漏则该字段变化不置脏, 视图静默不重建。
_VIEW_EXCLUDED_FIELDS = frozenset(
    (
        "hash",  # 主键: 变化即种子换, 增/删路径已置脏, 字段级脏判定不需
        "completed",  # 展示用 progress/size 代替
        "ratio_limit",  # 重加 4 件: 规则/跳检重加参数, 视图不展示
        "seeding_time_limit",
        "inactive_seeding_time_limit",
        "share_limit_action",
        "max_ratio",  # 做种限制 3 件: 视图展示实际值(ratio/seeding_time), 不展示上限
        "max_seeding_time",
        "max_inactive_seeding_time",
    )
)
_VIEW_FIELDS = _SNAPSHOT_FIELD_SET - _VIEW_EXCLUDED_FIELDS

# 视图字段量化步长: 该字段在 Web 视图中按此步长取整, 重建判定与展示值共用同一步长
# (保证"视图内容"与"脏标记依据"一致, 否则前端展示会与实际重建时机脱钩)。
# seeding_time 每秒递增 —— 不量化时做种中的种子会每轮置脏, 使惰性重建对绝大多数种子失效;
# 前端本就只展示到分钟, 故取整到 60s 无任何可见损失。
# eta/time_active/last_activity 同理(秒级跳动, 展示精度为分钟)。
_VIEW_QUANTUM: Dict[str, int] = {
    "seeding_time": 60,
    "eta": 60,
    "time_active": 60,
    "last_activity": 60,
}


def view_field_value(field: str, value: Any) -> Any:
    """视图字段的量化值(重建判定与 Web 视图展示值共用的唯一取整入口)

    未配置步长的字段原样返回(精确比较)。seeding_time 等单调递增但展示精度有限的字段
    按 `_VIEW_QUANTUM` 取整, 避免活跃但数据无实质变化的种子库每 tick 重建视图。
    负数不量化: qB 哨兵 -1 = 从未/未设(last_activity/seen_complete/completion_on),
    地板除会把它变成 -60, 破坏"从未"的展示语义。
    """
    q = _VIEW_QUANTUM.get(field)
    if q and value >= 0:
        return value // q * q
    return value


_VIEW_FIELD_SET = frozenset(_VIEW_FIELDS)


def view_dirty(changed: Iterable[str]) -> bool:
    """变化字段集是否触及 Web 分组视图的展示字段(_VIEW_FIELDS)

    apply_delta 返回的变化集已按 `view_field_value` 量化过滤(seeding_time 秒级递增不算变化),
    故这里只需集合交集判定。
    """
    return not _VIEW_FIELD_SET.isdisjoint(changed)
