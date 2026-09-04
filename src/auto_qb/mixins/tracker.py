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

    def _match_tracker_conf(self, torrent: TorrentRecord) -> Optional[TrackerConfig]:
        """
        根据种子的 tracker URLs 按 hostname 精确匹配配置中的 tracker(含子域名),
        与规则绑定(utils.match_tracker_confs)同语义, 避免子串误匹配(如配置 hhanclub.net
        误匹配 fakehhanclub.net)。返回第一个匹配的 TrackerConfig，若无匹配则返回 None;
        匹配到多个 tracker 配置时打印 ERROR 日志(仍返回第一个)
        """
        confs = utils.match_tracker_confs(self.config.trackers, torrent.tracker_urls(self.client))
        if len(confs) > 1:
            desc = ", ".join(f"{c.name}({', '.join(c.domains)})" for c in confs)
            logger.error(f"种子匹配到多个 tracker 配置, 使用第一个: {desc} {torrent.log_repr}")
        return confs[0] if confs else None

    def _apply_speed_limit(self, torrent: TorrentRecord, tracker_conf: TrackerConfig, dry_run: bool):
        self._apply_single_speed_limit(torrent, "torrents_set_upload_limit", tracker_conf.upload_speed_limit, dry_run)
        self._apply_single_speed_limit(
            torrent, "torrents_set_download_limit", tracker_conf.download_speed_limit, dry_run
        )

    def _apply_single_speed_limit(self, torrent: TorrentRecord, api_method: str, value: int, dry_run: bool):
        """应用单个速度限制"""
        if "upload" in api_method:
            current_limit = torrent.up_limit
            direction = "上传"
        else:
            current_limit = torrent.dl_limit
            direction = "下载"

        if current_limit == value:
            return

        # 不覆盖单数值
        if (current_limit / 1024) % 2 == 1:
            return

        if not dry_run:
            getattr(self.api, api_method)(torrent_hashes=torrent.hash, limit=value)

        logger.info(f"设置{direction}限速: {utils.fmt_speed(value)}")
