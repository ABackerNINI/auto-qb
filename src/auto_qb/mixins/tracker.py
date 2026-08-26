"""tracker 匹配 mixin

由 QbManager 组合(mixin), 依赖实例属性: client/config。
"""
from typing import Any, Optional

from qbittorrentapi import TorrentDictionary

from ..config import TrackerConfig


class TrackerMixin:
    """tracker 配置匹配"""

    client: Any
    config: Any

    def _match_tracker(self, tor: TorrentDictionary) -> Optional[TrackerConfig]:
        """
        根据种子的 tracker URLs 匹配配置中的 tracker
        返回第一个匹配的 TrackerConfig，若无匹配则返回 None
        """
        trackers_info = self.client.torrents_trackers(tor.hash)
        tracker_urls = [t["url"] for t in trackers_info if t.get("url")]

        for conf in self.config.trackers.values():
            for domain in conf.domains:
                for url in tracker_urls:
                    if domain in url:  # 简单包含匹配
                        return conf
        return None
