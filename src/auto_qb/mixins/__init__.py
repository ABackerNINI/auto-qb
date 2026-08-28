"""QbManager 职责拆分 mixins: 各功能模块组合进 QbManager(单一协调者)

- RuleEngineMixin  规则加载/状态持久化/规则种子级任务/process_torrent 兼容入口
- TagsMixin        标签/分类/HR 辅助
- CheckingMixin    文件检查/辅种跳检/异步校验轮询回调
- GroupingMixin    种子分组管理(辅种管理): 分组 + 组内大小一致性 + 缺文件联动
- TrackerMixin     tracker 配置匹配
"""
from .checking import CheckingMixin
from .grouping import GroupingMixin
from .rule_engine import RuleEngineMixin
from .tags import TagsMixin
from .tracker import TrackerMixin

__all__ = ["RuleEngineMixin", "TagsMixin", "CheckingMixin", "GroupingMixin", "TrackerMixin"]
