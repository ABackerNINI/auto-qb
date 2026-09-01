"""tracker 匹配 mixin

由 QbManager 组合(mixin), 依赖实例属性: client/config/store。
"""
import logging
from typing import Optional
from qbittorrentapi import Client

from ..config import TrackerConfig, Config
from ..torrents import TorrentRecord
from .. import utils

logger = logging.getLogger(__name__)


class TrackerMixin:
    """tracker 配置匹配"""

    client: Optional[Client]
    config: Config

    # TODO: 优化, 考虑使用缓存
    def _match_tracker(self, hash) -> Optional[TrackerConfig]:
        """
        根据种子的 tracker URLs 匹配配置中的 tracker
        返回第一个匹配的 TrackerConfig，若无匹配则返回 None
        """
        try:
            tracker_urls = self.store.tracker_urls(hash)  # 惰性缓存, 不重复拉取
        except Exception as e:
            logger.debug(f"获取 tracker 列表失败({hash}): {e}")
            return None

        for conf in self.config.trackers.values():
            for domain in conf.domains:
                for url in tracker_urls:
                    if domain in url:  # 简单包含匹配
                        return conf
        return None

    def _apply_speed_limit(self, torrent_record: TorrentRecord, tracker_conf: TrackerConfig, dry_run: bool):
        self._apply_single_speed_limit(
            torrent_record, "torrents_set_upload_limit", tracker_conf.upload_speed_limit, dry_run
        )
        self._apply_single_speed_limit(
            torrent_record, "torrents_set_download_limit", tracker_conf.download_speed_limit, dry_run
        )

    def _apply_single_speed_limit(self, torrent_record: TorrentRecord, api_method: str, value: int, dry_run: bool):
        """应用单个速度限制"""
        if "upload" in api_method:
            current_limit = torrent_record.up_limit
            direction = "上传"
        else:
            current_limit = torrent_record.dl_limit
            direction = "下载"

        # 不覆盖单数值
        if (current_limit / 1024) % 2 == 1:
            return
        if current_limit == value:
            return

        if not dry_run:
            getattr(self.api, api_method)(torrent_hashes=torrent_record.hash, limit=value)

        logger.info(f"设置{direction}限速: {utils.fmt_speed(value)}")
