"""功能模块包(plan kernel-module-refactor §3): 实现 Module 契约的自治单元

模块之间不互相 import, 需要别人能力时经 ctx 取服务或经事件相位协作(plan §3.1);
装配清单在 core/qbmanager.py 构造期 —— 那是全项目唯一「知道模块名字」的地方(plan §3.3),
顺序 = 相位内消费序 = 生命周期序。

挂入进度(P1 起逐段补齐): P1 logging/notify(基建样板) -> P2 webui/hr(门面转正) ->
P3 tracker/speed_curve/maintenance -> P4 grouping/ops -> P5 rules + 刷新管线收口。
"""
from .logging_mod import LoggingModule
from .notify_mod import NotifyModule

__all__ = ["LoggingModule", "NotifyModule"]
