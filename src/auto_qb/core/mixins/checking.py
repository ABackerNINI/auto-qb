"""
检查类 mixin: 辅种跳检功能已由规则动作(actions.py CheckAction)完全替代;
"""
import logging
import os

from ...torrents import TorrentRecord
from ...infra import file_access

logger = logging.getLogger(__name__)


class CheckingMixin:
    """文件存在+大小一致性检查(checking 动作决策链与缺文件扫描复用本方法)"""
    @staticmethod
    def check_filelist(api, torrent: TorrentRecord) -> str:
        """检查种子文件是否存在且大小一致(api 为 QbApi Facade或兼容客户端). 返回错误描述字符串, 全部通过返回 None"""
        logger.debug(f"{torrent.log_repr} | 检查文件完整性")
        try:
            files = api.torrents_files(torrent.hash)
        except Exception as e:
            return f"获取文件列表失败: {e}"
        save_path = torrent.save_path
        fa = file_access.get_file_access()
        for f in files:
            full_path = os.path.normpath(os.path.join(save_path, f.name))
            exists = fa.exists(full_path)
            if exists is file_access.UNDETERMINED:
                # 映射 miss: 存在性不可判定 —— 显式报「不可判定」而非「文件缺失」,
                # 让跳检前置保守停住但不误报缺失语义(报告 §05 红线)
                return f"路径不可判定: '{full_path}'(未命中 fs.path_map 映射)"
            if not exists:
                return f"文件缺失: {f.name}"
            try:
                if fa.getsize(full_path) != f.size:
                    return f"文件大小不一致: {f.name}"
            except OSError:
                return f"无法读取文件: {f.name}"
        return None
