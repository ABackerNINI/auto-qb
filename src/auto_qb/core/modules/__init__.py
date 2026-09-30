"""功能模块包(plan kernel-module-refactor §3): 实现 Module 契约的自治单元

模块之间不互相 import, 需要别人能力时经 ctx 取服务或经事件相位协作(plan §3.1);
装配清单在 core/qbmanager.py 构造期 —— 那是全项目唯一「知道模块名字」的地方(plan §3.3),
顺序 = 相位内消费序 = 生命周期序。

挂入进度(P1 起逐段补齐): P1 logging/notify(基建样板, 在本包) -> P2 webui/hr(门面转正,
模块类随门面住各自包: webui/module.py + hr/module.py) -> P3 tracker/speed_curve/maintenance
-> P4 grouping/ops(+checking 并入) -> P5 rules + 刷新管线收口。
"""
from .logging_mod import LoggingModule
from .notify_mod import NotifyModule
from .tracker_mod import TrackerModule
from .speed_curve_mod import SpeedCurveModule
from .maintenance_mod import MaintenanceModule
from .grouping_mod import GroupingModule
from .ops_mod import OpsModule
from .rules_mod import RulesModule

__all__ = [
    "LoggingModule",
    "NotifyModule",
    "TrackerModule",
    "SpeedCurveModule",
    "MaintenanceModule",
    "GroupingModule",
    "OpsModule",
    "RulesModule",
]
