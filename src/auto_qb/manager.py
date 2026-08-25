"""PTManager: qBittorrent 主管理类(内置处理步骤 + 规则框架集成 + 主循环)"""
import logging
import os
import re
import time
from typing import List, Optional

from qbittorrentapi import Client, TorrentDictionary

from .config import Config, TrackerConfig, load_config
from .rules import RuleManager
from .utils import add_long_path_prefix_for_win, parse_hr_rule


class PTManager:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config: Config = load_config(config_path)
        self.client: Optional[Client] = None
        self._setup_logging()
        # 规则框架: 统一管理规则插件(条件+动作), 配置来自 config 下 *_rules 段
        self.rules = RuleManager(self.config, self.config.state_file)

    def _setup_logging(self):
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
        self.logger = logging.getLogger("PTManager")

    def connect(self) -> bool:
        """连接 qBittorrent"""
        try:
            self.client = Client(
                host=self.config.qbittorrent.base_url,
                username=self.config.qbittorrent.username,
                password=self.config.qbittorrent.password,
            )
            self.client.auth_log_in()
            self.rules.client = self.client
            self.logger.info("Connected to qBittorrent successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to qBittorrent: {e}")
            return False

    def run(self, dry_run: bool):
        """主循环"""
        if not self.connect():
            return

        self.logger.info(f"Starting PT manager with interval {self.config.interval}s")
        while True:
            try:
                self._process_all_torrents(dry_run)
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
            time.sleep(self.config.interval)

    def _process_all_torrents(self, dry_run: bool):
        """获取所有种子并处理"""
        torrents = self.client.torrents_info()
        self.logger.info(f"Processing {len(torrents)} torrents")

        # 规则框架: 每轮开始维护上传量快照(按自然日/周/月)
        self.rules.begin_round(torrents)

        for tor in torrents:
            try:
                self._process_single_torrent(tor, dry_run)
            except Exception as e:
                self.logger.error(f"Error processing torrent {tor.hash}: {e}")

    def _process_single_torrent(self, tor: TorrentDictionary, dry_run: bool):
        """处理单个种子"""
        # 1. 检查文件丢失（先做，若丢失则暂停并分类，跳过其他）
        #    缺文件检查优先级最高: MISSING 的种子任何规则都不生效, 直到文件恢复
        if self.config.check_missing_files:
            if self._check_and_handle_missing_files(tor, dry_run):
                return  # 已处理，跳过后续

        # 2. 规则框架: 内置步骤只在种子未匹配任何启用的规则时兜底执行
        #    规则动作执行后内置步骤跳过, 避免冲突(如规则 start 了种子, 内置缺文件检查又 stop 它)
        if self.rules.enabled_rules:
            if self.rules.process_torrent(tor, dry_run):
                return

        # 3. 辅种跳检
        if self.config.skip_checking_for_cross_seeding:
            self._skip_checking_for_cross_seeding(tor, dry_run)

        # 4. 匹配 tracker 配置
        tracker_conf = self._match_tracker(tor)
        if not tracker_conf:
            return  # 未匹配，不处理

        # 5. 添加标签
        self._add_tags(tor, tracker_conf.tags, dry_run)

        # 6. 删除标签
        self._remove_tags(tor, tracker_conf.remove_tags, dry_run)

        # 7. 删除相似标签
        if self.config.remove_similar_tags:
            self._remove_similar_tags(tor, tracker_conf.tags, dry_run)

        # 8. 处理 HR 规则
        if tracker_conf.hr_rule and (self.config.add_hr_tags or self.config.add_hr_categories):
            self._add_hr_tag_or_category(tor, tracker_conf.hr_rule, dry_run)

    # ---------- 标签/分类辅助 ----------

    def _add_tags(self, tor: TorrentDictionary, tags: List[str], dry_run: bool):
        """为种子添加标签（若不存在）"""
        if not tags:
            return

        current_tags = (set(part.strip() for part in tor.tags.split(",")) if tor.tags else set())
        new_tags = [t for t in tags if t not in current_tags]
        if new_tags:
            if not dry_run:
                self.client.torrents_add_tags(tags=new_tags, torrent_hashes=tor.hash)
            self.logger.info(f"Added tags '{new_tags}' to '{tor.name}'")

    def _remove_tags(self, tor: TorrentDictionary, tags_to_remove: List[str], dry_run: bool):
        """为种子删除标签"""
        if not tags_to_remove:
            return

        current_tags = (set(part.strip() for part in tor.tags.split(",")) if tor.tags else set())
        tags_to_remove = set(tags_to_remove) & current_tags
        if tags_to_remove:
            if not dry_run:
                self.client.torrents_remove_tags(tags=tags_to_remove, torrent_hashes=tor.hash)
            self.logger.info(f"Removed tags '{tags_to_remove}' from '{tor.name}'")

    def _remove_similar_tags(self, tor: TorrentDictionary, tags: List[str], dry_run: bool):
        """删除类似(单词相同大小写不同)的tag"""
        if not tags:
            return

        current_tags = (set(part.strip() for part in tor.tags.split(",")) if tor.tags else set())

        # 删除单词相同但大小写不一致的标签
        for tag in current_tags:
            if tag.lower() in [t.lower() for t in tags] and tag not in tags:
                if not dry_run:
                    self.client.torrents_remove_tags(tags=tag, torrent_hashes=tor.hash)
                self.logger.info(f"Removed similar tag '{tag}' from '{tor.name}'")

    def _set_category(self, tor: TorrentDictionary, category: str, overwrite: bool, dry_run: bool):
        """设置种子的分类"""
        old_category = tor.category.strip()

        if old_category == category:  # 分类已存在
            return

        if not old_category or overwrite:  # 分类为空或者强制覆盖
            self._create_category_if_not_exists(category, dry_run)

            # 设置分类
            if not dry_run:
                self.client.torrents_set_category(category=category, torrent_hashes=tor.hash)

            # 打印日志
            if old_category:
                self.logger.info(f"Set category from '{old_category}' to '{category}' for '{tor.name}'")
            else:
                self.logger.info(f"Set category to '{category}' for '{tor.name}'")
        else:  # 存在分类但不覆盖
            self.logger.warning(f"Skipping '{tor.name}' as it already has category '{old_category}'")

    def _create_category_if_not_exists(self, category: str, dry_run: bool):
        """如果分类不存在则创建分类"""
        current_categories = self.client.torrents_categories()
        if category not in current_categories:  # 分类不存在
            if not dry_run:
                self.client.torrents_create_category(name=category)
            self.logger.info(f"Created category '{category}'")

    # ---------- HR ----------

    def _add_hr_tag_or_category(self, tor: TorrentDictionary, rule_str: str, dry_run: bool):
        """添加HR标签或分类"""
        required_time, condition, extra_time = parse_hr_rule(rule_str)

        # 检查下载条件, 主要为了排除辅种
        condition_met = False

        cond_type, cond_value = condition
        if cond_type == "dlratio":
            dlratio = tor.downloaded / tor.total_size
            condition_met = dlratio >= cond_value
        elif cond_type == "dlsize":
            condition_met = tor.downloaded >= cond_value

        if not condition_met:
            return

        # 满足基础 HR 条件，添加 HR tag
        # 从规则中提取时间部分，如 "3D" -> "HR3D"
        time_part = re.match(r"^([\d.]+[SMHD])", rule_str)
        if not time_part:
            raise ValueError(f"Invalid rule format: '{rule_str}'")

        # 添加 HR tag
        if self.config.add_hr_tags:
            hr_tag = self.config.hr_tag_format.replace("${time}", time_part.group(1))
            self._add_tags(tor, [hr_tag], dry_run)

        # 添加 HR 分类
        if self.config.add_hr_categories:
            hr_category = self.config.hr_category_format.replace("${time}", time_part.group(1))
            self._set_category(tor, hr_category, self.config.overwrite_category_for_hr, dry_run)

    def _mark_hr_done(self, tor: TorrentDictionary, dry_run: bool):
        """标记种子为 HR-DONE 分类并强制汇报"""
        if tor.category != "HR-DONE":
            if not dry_run:
                self.client.torrents_set_category(tor.hash, category="HR-DONE")
            self.logger.info(f"Marked {tor.hash} as HR-DONE")
        # 强制汇报
        if not dry_run:
            self.client.torrents_reannounce(tor.hash)
        self.logger.info(f"Reannounced {tor.hash}")

    # ---------- 检查类 ----------

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
                self.logger.warning(f"File missing: '{full_path}' of torrent '{tor.name}'!")
                missing = True
                break

            if os.path.getsize(full_path) != f.size:  # 比较文件大小
                self.logger.warning(
                    f"File size mismatch: '{full_path}' of torrent '{tor.name}', "
                    f"expected {f.size}, got {os.path.getsize(full_path)}!"
                )
                missing = True
                break

        if missing:
            # 暂停种子
            if not dry_run:
                self.client.torrents_stop(tor.hash)
            self.logger.warning(f"Paused {tor.hash} due to missing files")

            # 设置标签
            self._add_tags(tor, ["MISSING"], dry_run)
            return True
        return False

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

        self.logger.info(f"Skip checking for torrent '{tor.name}'")

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

    # ---------- tracker 匹配 ----------

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
