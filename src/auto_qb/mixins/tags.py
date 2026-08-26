"""标签/分类/HR 辅助 mixin

由 QbManager 组合(mixin), 依赖实例属性: client/logger/config。
"""
import logging
import re
from typing import Any, List

from qbittorrentapi import TorrentDictionary

from ..config import TrackerConfig
from ..utils import parse_hr_rule

logger = logging.getLogger("auto-qb")


class TagsMixin:
    """标签/分类/HR 辅助"""

    client: Any
    logger: Any
    config: Any

    def _log_torrent_details(self, tor: TorrentDictionary, tracker_conf: TrackerConfig | None) -> str:
        site = tracker_conf.name if tracker_conf else "未知"
        self.logger.info(f"种子: {tor.name}")
        self.logger.info(f"站点: {site}")
        self.logger.info(f"状态: {tor.state}")
        self.logger.info(f"哈希: {tor.hash}")

    @staticmethod
    def _torrent_desc(tor: TorrentDictionary) -> str:
        """单行种子摘要: 名称 + hash, 用于内置步骤日志"""
        return f"{tor.name} [{tor.hash}]"

    def _add_tags(self, tor: TorrentDictionary, tags: List[str], dry_run: bool):
        """为种子添加标签（若不存在）"""
        if not tags:
            return False

        current_tags = (set(part.strip() for part in tor.tags.split(",")) if tor.tags else set())
        new_tags = [t for t in tags if t not in current_tags]
        if new_tags:
            if not dry_run:
                self.client.torrents_add_tags(tags=new_tags, torrent_hashes=tor.hash)
            self.logger.info(f"Added tags '{new_tags}'")
            return True
        return False

    def _remove_tags(self, tor: TorrentDictionary, tags_to_remove: List[str], dry_run: bool):
        """为种子删除标签"""
        if not tags_to_remove:
            return False

        current_tags = (set(part.strip() for part in tor.tags.split(",")) if tor.tags else set())
        tags_to_remove = set(tags_to_remove) & current_tags
        if tags_to_remove:
            if not dry_run:
                self.client.torrents_remove_tags(tags=tags_to_remove, torrent_hashes=tor.hash)
            self.logger.info(f"Removed tags '{tags_to_remove}'")
            return True
        return False

    def _remove_similar_tags(self, tor: TorrentDictionary, tags: List[str], dry_run: bool):
        """删除类似(单词相同大小写不同)的tag"""
        if not tags:
            return False

        current_tags = (set(part.strip() for part in tor.tags.split(",")) if tor.tags else set())

        removed = False

        # 删除单词相同但大小写不一致的标签
        for tag in current_tags:
            if tag.lower() in [t.lower() for t in tags] and tag not in tags:
                if not dry_run:
                    self.client.torrents_remove_tags(tags=tag, torrent_hashes=tor.hash)
                self.logger.info(f"Removed similar tag '{tag}'")
                removed = True

        return removed

    def _set_category(self, tor: TorrentDictionary, category: str, overwrite: bool, dry_run: bool):
        """设置种子的分类"""
        old_category = tor.category.strip()

        if old_category == category:  # 分类已存在
            return False

        if not old_category or overwrite:  # 分类为空或者强制覆盖
            self._create_category_if_not_exists(category, dry_run)

            # 设置分类
            if not dry_run:
                self.client.torrents_set_category(category=category, torrent_hashes=tor.hash)

            # 打印日志
            if old_category:
                self.logger.info(f"Set category from '{old_category}' to '{category}'")
            else:
                self.logger.info(f"Set category to '{category}'")

            return True
        else:  # 存在分类但不覆盖
            self.logger.warning(f"Skipping as it already has category '{old_category}'")
            return True

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
            return False

        # 满足基础 HR 条件，添加 HR tag
        # 从规则中提取时间部分，如 "3D" -> "HR3D"
        time_part = re.match(r"^([\d.]+[SMHD])", rule_str)
        if not time_part:
            raise ValueError(f"Invalid rule format: '{rule_str}'")

        added = False

        # 添加 HR tag
        if self.config.add_hr_tags:
            hr_tag = self.config.hr_tag_format.replace("${time}", time_part.group(1))
            added |= self._add_tags(tor, [hr_tag], dry_run)

        # 添加 HR 分类
        if self.config.add_hr_categories:
            hr_category = self.config.hr_category_format.replace("${time}", time_part.group(1))
            added |= self._set_category(tor, hr_category, self.config.overwrite_category_for_hr, dry_run)

        return added

    def _mark_hr_done(self, tor: TorrentDictionary, dry_run: bool):
        """标记种子为 HR-DONE 分类并强制汇报"""
        if tor.category != "HR-DONE":
            if not dry_run:
                self.client.torrents_set_category(tor.hash, category="HR-DONE")
            self.logger.info(f"Marked torrent as HR-DONE")
        # 强制汇报
        if not dry_run:
            self.client.torrents_reannounce(tor.hash)
        self.logger.info(f"Reannounced torrent")
