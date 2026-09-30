"""QbManager 职责拆分 mixins(收尾中的过渡包)

已全部迁出为功能模块/表现层(plan kernel-module-refactor, 见 core/modules/ 与 webui/hr
各自 module.py):
- P0: rule_engine 的状态持久化族 -> core/state.py(StateService);
- P1: logging/notify -> P2: webui/hr(门面转正) -> P3: tracker/speed_curve/tags ->
- P4: grouping(GroupingModule) / ops+checking(OpsModule, ctx.ops 服务);
- P5: rule_engine 其余部分(规则加载/种子级任务/事件分派/L2 重建) -> RulesModule
  (core/modules/rules_mod.py) —— mixins 包自此只剩 webui 表现层两 mixin 的组合入口,
  QbManager 旧名方法只剩单行委托(plan §7.2)。
"""
from ..webui.commands import WebCommandsMixin
from ..webui.views import WebviewMixin

__all__ = ["WebCommandsMixin", "WebviewMixin"]
