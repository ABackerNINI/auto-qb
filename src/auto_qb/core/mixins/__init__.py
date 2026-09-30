"""QbManager 职责拆分 mixins: 各功能模块组合进 QbManager(单一协调者)

- RuleEngineMixin    规则加载/种子级规则任务/事件分派(状态持久化已迁 core/state.py, plan P0)

已迁出为功能模块(plan kernel-module-refactor, 见 core/modules/):
- P1: logging/notify -> P2: webui/hr(门面转正) -> P3: tracker/speed_curve/tags ->
- P4: grouping(GroupingModule) / ops+checking(OpsModule, ctx.ops 服务) —— QbManager 旧名
  方法只剩单行委托(plan §7.2)。
- P5 待迁: rule_engine -> RulesModule(刷新管线收口后 mixins 包整体退役)。
"""
from .rule_engine import RuleEngineMixin

__all__ = ["RuleEngineMixin"]
