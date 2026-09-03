"""检查类 mixin: 辅种跳检功能已由规则动作(actions.py CheckAction)完全替代;
此 mixin 保留为空类以维持 QbManager 组合结构(_is_check_done 由 QbManager 定义)。

由 QbManager 组合(mixin), 依赖实例属性: client/logger/config。
"""
import logging
from typing import Optional
from qbittorrentapi import Client

from ..config import Config


class CheckingMixin:
    """文件检查/辅种跳检(已迁移至规则动作, 占位保留)"""

    client: Optional[Client]
    config: Config
