"""标签/分类/HR 辅助 mixin

由 QbManager 组合(mixin), 依赖实例属性: client/logger/config。
"""
import logging
from typing import Any, List, Optional

from qbittorrentapi import Client, TorrentDictionary

from ..config import HRRule, TrackerConfig, Config
from .. import utils

logger = logging.getLogger("auto-qb")


class TagsMixin:
    """标签/分类/HR 辅助"""

    client: Optional[Client]
    logger: Any
    config: Config

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

    def _remove_tags(self, tor: TorrentDictionary, patterns: List[str], dry_run: bool):
        """
        为种子删除标签.
        Args:
            tor: 种子信息.
            patterns: 要删除的标签格式.
            dry_run: 测试运行.
        """
        if not patterns:
            return False

        current_tags = (set(part.strip() for part in tor.tags.split(",")) if tor.tags else set())
        patterns = [tag for tag in current_tags if utils.match_tag_patterns(tag, patterns)]
        if patterns:
            if not dry_run:
                self.client.torrents_remove_tags(tags=patterns, torrent_hashes=tor.hash)
            self.logger.info(f"Removed tags '{patterns}'")
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
        old_category = tor.category

        if old_category == category:  # 分类已存在
            return False

        auto_categories = self.state.setdefault("auto_categories", {})

        # 定义一个内部函数可以利用if短路
        def can_update_previous():
            previous_auto_category = auto_categories.get(tor.hash)
            return not overwrite and old_category == previous_auto_category

        if not old_category or overwrite or can_update_previous():  # 分类为空、强制覆盖或更新此前自动分类
            self._create_category_if_not_exists(category, dry_run)

            # 设置分类
            if not dry_run:
                self.client.torrents_set_category(category=category, torrent_hashes=tor.hash)
                if not overwrite:
                    auto_categories[tor.hash] = category

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

    @staticmethod
    def _fmt_hr(template: str, hr: HRRule) -> str:
        """HR 格式变量替换: ${required_seeding_time}"""
        return (str(template).replace("${required_seeding_time}", hr.required_seeding_time_raw))

    def _add_hr_tag_or_category(self, tor: TorrentDictionary, tracker_conf: TrackerConfig, dry_run: bool):
        """添加HR标签或分类(基于站点合并后的 hr 设置)

        - 满足触发条件(下载比例/下载量): 添加 add_tag / add_category
        - HR 满足(做种时长 >= required_seeding_time + extra_seeding_time 或 分享率达标): 添加 add_tag_for_satisfied / add_category_for_satisfied
        """
        hr = tracker_conf.hr
        if hr is None:
            return False

        # 检查下载条件, 主要为了排除辅种
        cond_type, cond_value = hr.condition
        if cond_type == "dlratio":
            dlratio = tor.downloaded / tor.total_size if tor.total_size else 0
            condition_met = dlratio >= cond_value
        else:  # dlsize
            condition_met = tor.downloaded >= cond_value
        if not condition_met:
            return False

        added = False

        # 做种时长满足 或 分享率达标, 添加 satisfied 标签/分类
        seeding_ok = tor.seeding_time >= (hr.required_seeding_time + hr.extra_seeding_time)
        ratio_ok = hr.required_share_ratio > 0 and (tor.ratio or 0) >= hr.required_share_ratio
        if seeding_ok or ratio_ok:
            if hr.add_tag_for_satisfied:
                added |= self._add_tags(tor, [self._fmt_hr(hr.add_tag_for_satisfied, hr)], dry_run)
            if hr.add_category_for_satisfied:
                added |= self._set_category(
                    tor,
                    self._fmt_hr(hr.add_category_for_satisfied, hr),
                    hr.overwrite_category_for_satisfied,
                    dry_run,
                )

            return added
        else:  # 做种时长不够 且 分享率未达标: 添加 HR 标签/分类
            if hr.add_tag:
                added |= self._add_tags(tor, [self._fmt_hr(hr.add_tag, hr)], dry_run)
            if hr.add_category:
                added |= self._set_category(
                    tor,
                    self._fmt_hr(hr.add_category, hr),
                    hr.overwrite_category,
                    dry_run,
                )

        return added

    # ---------- 全局标签清理(全局任务) ----------

    def _handle_delete_tags(self, task, dry_run: bool) -> bool:
        """全局任务: 彻底删除匹配格式的标签(支持正则, regex: 前缀)

        匹配所有现有标签定义(含无种子的), 调用 torrents_delete_tags 从所有种子移除并删除定义。
        """
        patterns = self.config.delete_tags or []
        if not patterns:
            return True
        try:
            all_tags = self.client.torrents_tags() or []
        except Exception as e:
            self.logger.error(f"获取标签列表失败: {e}")
            return True
        matched = [t for t in all_tags if utils.match_tag_patterns(t, patterns)]
        if not matched:
            return True
        if not dry_run:
            self.client.torrents_delete_tags(tags=matched)
        self.logger.info(f"彻底删除标签: {matched}")
        return True

    def _handle_delete_tags_if_has_no_torrents(self, task, dry_run: bool) -> bool:
        """全局任务: 彻底删除无种子的标签(支持正则, regex: 前缀)

        仅当标签定义存在且没有任何种子使用(所有种子 tags 的并集之外)时才删除。
        """
        patterns = self.config.delete_tags_if_has_no_torrents or []
        if not patterns:
            return True
        try:
            all_tags = set(self.client.torrents_tags() or [])
        except Exception as e:
            self.logger.error(f"获取标签列表失败: {e}")
            return True
        if not all_tags:
            return True

        # # 收集所有种子正在使用的标签
        # used = set()
        # for tor in self.client.torrents_info():
        #     for t in (tor.tags or "").split(","):
        #         t = t.strip()
        #         if t:
        #             used.add(t)
        # orphan = all_tags - used
        # matched = [t for t in orphan if match_tag_pattern(t, patterns)]
        # if not matched:
        #     return True
        # if not dry_run:
        #     self.client.torrents_delete_tags(tags=matched)
        # self.logger.info(f"彻底删除无种子的标签: {matched}")

        # 对满足筛选条件的标签查询种子数, 如果为0则删除
        matched = []
        for tag in all_tags:
            if utils.match_tag_patterns(tag, patterns):
                if len(self.client.torrents.info(tag=tag)) == 0:
                    matched.append(tag)

        if not matched:
            return True
        if not dry_run:
            self.client.torrents_delete_tags(tags=matched)
        self.logger.info(f"彻底删除无种子的标签: {matched}")

        return True
