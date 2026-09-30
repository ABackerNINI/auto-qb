"""QbManager 职责拆分 mixins: 各功能模块组合进 QbManager(单一协调者)

- RuleEngineMixin    规则加载/种子级规则任务/事件分派（状态持久化已迁 core/state.py, plan P0）
- CheckingMixin      文件检查/辅种跳检/异步校验轮询回调
- GroupingMixin      种子分组管理(辅种管理): 分组 + 组内大小一致性 + 缺文件联动
- OpsMixin           危险操作独立操作层(rules → ops ← web): recheck/跳检的执行体 +
                     提交点检查 + 按 source 保护策略(plan 26-09-30-0109)

已迁出为功能模块(plan kernel-module-refactor, 见 core/modules/):
- P3: tags -> MaintenanceModule / tracker -> TrackerModule(ctx.trackers 服务) /
  speed_curve -> SpeedCurveModule; QbManager 旧名方法只剩单行委托(plan §7.2)。
- P4 待迁: grouping / ops(+checking) -> P5: rule_engine。
"""
from .checking import CheckingMixin
from .grouping import GroupingMixin
from .ops import OpsMixin
from .rule_engine import RuleEngineMixin

__all__ = [
    "RuleEngineMixin",
    "CheckingMixin",
    "GroupingMixin",
    "OpsMixin",
]
