"""规则动作插件(包): 按职责拆分, 子模块 import 即注册(@register_action); 公共名称经此
重导出 —— 调用方 `from auto_qb.rules.actions import X` 不变。

模块职责:
- basic.py: 基础种子操作(标签/分类/启停)
- transfer.py: 传输相关(move_to/reannounce/单种限速)
- checking.py: checking 校验动作主体(决策链+参考筛选)
- full_checking.py: full-checking 执行与组内校验串行化(FullCheckingMixin)
- skip_checking.py: 跳检四阶段(SkipCheckingMixin)

新增动作模块后必须在此 import, 否则插件不会注册(config 校验会拒绝合法动作名);
test_actions.py::test_actions_registry_complete 锁定全部动作名清单。
"""
from .basic import (
    AddCategoryAction,
    AddTagsAction,
    PrintTorrentDetailsAction,
    RemoveCategoryAction,
    RemoveTagsAction,
    StartAction,
    StopAction,
)
from .checking import CheckAction
from .full_checking import CHECK_RESULT_INTERVAL, GROUP_CHECK_WAIT_LIMIT, RECHECK_FAIL_LIMIT
from .transfer import DownloadSpeedLimitAction, MoveToAction, ReannounceAction, UploadSpeedLimitAction

__all__ = [
    "AddCategoryAction",
    "AddTagsAction",
    "CheckAction",
    "CHECK_RESULT_INTERVAL",
    "DownloadSpeedLimitAction",
    "GROUP_CHECK_WAIT_LIMIT",
    "MoveToAction",
    "PrintTorrentDetailsAction",
    "RECHECK_FAIL_LIMIT",
    "ReannounceAction",
    "RemoveCategoryAction",
    "RemoveTagsAction",
    "StartAction",
    "StopAction",
    "UploadSpeedLimitAction",
]
