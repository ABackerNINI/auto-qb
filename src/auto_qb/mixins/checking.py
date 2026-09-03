"""
检查类 mixin: 辅种跳检功能已由规则动作(actions.py CheckAction)完全替代;
"""
import logging
import os

from ..torrents import TorrentRecord
from .. import utils

logger = logging.getLogger(__name__)


class CheckingMixin:
    """文件检查; 辅种跳检(已迁移至规则动作, 占位保留)"""
    @staticmethod
    def check_filelist(api, torrent: TorrentRecord) -> str:
        """检查种子文件是否存在且大小一致(api 为 QbApi 门面或兼容客户端). 返回错误描述字符串, 全部通过返回 None"""
        logger.debug(f"检查种子文件完整性: {torrent.name} ({torrent.hash[:8]})")
        try:
            files = api.torrents_files(torrent.hash)
        except Exception as e:
            return f"获取文件列表失败: {e}"
        save_path = torrent.save_path
        for f in files:
            full_path = utils.add_long_path_prefix_for_win(os.path.normpath(os.path.join(save_path, f.name)))
            if not os.path.exists(full_path):
                return f"文件缺失: {f.name}"
            try:
                if os.path.getsize(full_path) != f.size:
                    return f"文件大小不一致: {f.name}"
            except OSError:
                return f"无法读取文件: {f.name}"
        return None
