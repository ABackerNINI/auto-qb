"""检查类 mixin: 文件丢失检查 / 辅种跳检 / 异步校验轮询回调

由 QbManager 组合(mixin), 依赖实例属性: client/logger/config/_add_tags。
"""
import logging
import os
from typing import Any

from qbittorrentapi import TorrentDictionary

from ..utils import add_long_path_prefix_for_win

logger = logging.getLogger("auto-qb")


class CheckingMixin:
    """文件检查/辅种跳检/异步校验轮询"""

    client: Any
    logger: Any
    config: Any

    def _is_check_done(self, torrent_hash: str) -> bool:
        """慢速队列轮询回调: 查询种子当前状态, 退出校验(checking*)状态即视为完成"""
        try:
            infos = self.client.torrents_info(torrent_hashes=torrent_hash)
        except Exception as e:
            self.logger.debug(f"查询校验状态失败({torrent_hash}): {e}")
            return False
        if not infos:
            return True  # 种子已被删除, 视为完成
        state = (infos[0].state or "").lower()
        return not state.startswith("checking")

    def _check_and_handle_missing_files(self, tor: TorrentDictionary, dry_run: bool) -> bool:
        """
        检查种子文件是否存在，如果已完成但文件缺失，则暂停并添加标签"MISSING"
        返回 True 表示已处理（已暂停），否则 False
        """
        # 只处理已完成且正在做种的种子
        if tor.amount_left > 0 or not tor.state_enum.is_uploading:
            return False

        # 获取文件列表
        files = self.client.torrents_files(tor.hash)
        save_path = tor.save_path
        missing = False
        for f in files:
            # 组合完整路径, 添加长路径前缀
            full_path = add_long_path_prefix_for_win(os.path.normpath(os.path.join(save_path, f.name)))

            if not os.path.exists(full_path):  # 查看文件是否存在
                self.logger.warning(f"File missing: '{full_path}'!")
                missing = True
                break

            if os.path.getsize(full_path) != f.size:  # 比较文件大小
                self.logger.warning(
                    f"File size mismatch: '{full_path}', expected {f.size}, got {os.path.getsize(full_path)}!"
                )
                missing = True
                break

        if missing:
            # 暂停种子
            if not dry_run:
                self.client.torrents_stop(tor.hash)
            self.logger.warning(f"Paused torrent due to missing files")

            # 设置标签
            self._add_tags(tor, ["MISSING"], dry_run)

        return missing

    def _skip_checking_for_cross_seeding(self, tor: TorrentDictionary, dry_run: bool):
        """
        辅种任务跳过检查并自动开始, 添加跳检标签.
        下载量/完成量/进度为0 且 状态为暂停stop 的种子视为辅种任务.
        """
        if tor.downloaded > 0:  # 下载量必须为0
            return False

        if tor.completed != 0:  # 完成量必须为0
            return False

        if tor.progress != 0:  # 进度必须为0
            return False

        if not tor.state_enum.is_stopped:  # 必须是停止状态
            return False

        # 对文件进行简单检查: 确保所有文件都存在且大小一致
        files = self.client.torrents_files(tor.hash)
        save_path = tor.save_path
        missing = False
        for f in files:
            # 组合完整路径, 添加长路径前缀
            full_path = add_long_path_prefix_for_win(os.path.normpath(os.path.join(save_path, f.name)))

            if not os.path.exists(full_path):  # 查看文件是否存在
                missing = True
                break

            if os.path.getsize(full_path) != f.size:  # 比较文件大小
                missing = True
                break

        if missing:
            return

        self.logger.info(f"Skip checking")

        # 获取种子的关键属性，以便重新添加时保留
        save_path = tor.save_path
        category = tor.category
        tags = tor.tags
        # 注意：此处未保留上传/下载限速等高级设置，如有需要可自行添加

        # 重要：从 qBittorrent 中导出 .torrent 文件
        # 这是为了保留 tracker 等信息
        if not dry_run:
            torrent_file_data = self.client.torrents_export(torrent_hash=tor.hash)
        self.logger.info(f"  Exporting torrent")

        # 删除原种子（注意：不要删除已下载的数据文件）
        if not dry_run:
            self.client.torrents_delete(torrent_hashes=tor.hash, delete_files=False)
        self.logger.info(f"  Deleting torrent")

        # 使用"跳过校验"选项重新添加
        # is_skip_checking=True 即为跳过哈希校验的关键参数
        if not dry_run:
            self.client.torrents_add(
                torrent_files=torrent_file_data,  # 使用导出的 .torrent 文件数据
                save_path=save_path,  # 恢复原保存路径
                category=category,  # 恢复原分类
                tags=tags,  # 恢复原标签
                is_skip_checking=True,  # 核心：跳过校验！
                is_paused=False,  # 添加后自动开始
            )
        self.logger.info(f"  Re-adding torrent")

        # 开始刚添加的种子
        if self.config.skip_checking_auto_start:
            if not dry_run:
                self.client.torrents_start(torrent_hashes=tor.hash)
            self.logger.info(f"  Starting torrent")

        # 添加跳检标签
        if self.config.add_skip_checking_tags:
            self._add_tags(tor, [self.config.skip_checking_tag_format], dry_run)

        return True
