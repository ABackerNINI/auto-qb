"""tracker 匹配 mixin

由 QbManager 组合(mixin), 依赖实例属性: client/config/store。
"""
import logging
from typing import Optional
from qbittorrentapi import TorrentDictionary

from ..config import TrackerConfig, Config
from ..torrents import TorrentRecord

logger = logging.getLogger(__name__)


class TrackerMixin:
    """tracker 配置匹配"""

    config: Config

    def _match_tracker(self, tor: TorrentDictionary) -> Optional[TrackerConfig]:
        """
        根据种子的 tracker URLs 匹配配置中的 tracker
        返回第一个匹配的 TrackerConfig，若无匹配则返回 None
        """
        try:
            tracker_urls = self.store.tracker_urls(tor.hash)  # 惰性缓存, 不重复拉取
        except Exception as e:
            logger.debug(f"获取 tracker 列表失败({tor.hash}): {e}")
            return None

        for conf in self.config.trackers.values():
            for domain in conf.domains:
                for url in tracker_urls:
                    if domain in url:  # 简单包含匹配
                        return conf
        return None
