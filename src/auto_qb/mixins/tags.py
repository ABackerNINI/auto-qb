"""标签/分类/HR 辅助 mixin

由 QbManager 组合(mixin), 依赖实例属性: client/logger/config/state/store。
"""
import logging
from typing import List, Optional
from qbittorrentapi import Client, TorrentDictionary

from ..config import HRRule, TrackerConfig, Config
from ..qbapi import QbApi
from .. import episodes, utils
from ..torrents import TorrentRecord

logger = logging.getLogger(__name__)


class TagsMixin:
    """标签/分类/HR 辅助"""

    client: Optional[Client]
    api: Optional[QbApi]
    config: Config

    def _add_tags(self, torrent: TorrentRecord, tags: List[str], dry_run: bool, log_level: int = logging.INFO):
        """为种子添加标签（若不存在）; log_level 控制日志级别(如分组流程整组宣告后传 DEBUG 避免逐成员重复)"""
        if not tags:
            return False

        current_tags = torrent.tags_set
        new_tags = [t for t in tags if t not in current_tags]
        if new_tags:
            if not dry_run:
                self.api.torrents_add_tags(tags=new_tags, torrent_hashes=torrent.hash)
            logger.log(log_level, f"维护 {torrent.log_repr} | 添加标签: {new_tags}")
            return True
        return False

    def _remove_tags(self, torrent: TorrentRecord, patterns: List[str], dry_run: bool):
        """
        为种子删除标签（若存在）.
        """
        if not patterns:
            return False

        current_tags = torrent.tags_set
        to_remove_tags = [tag for tag in current_tags if utils.match_tag_patterns(tag, patterns)]
        if to_remove_tags:
            if not dry_run:
                self.api.torrents_remove_tags(tags=to_remove_tags, torrent_hashes=torrent.hash)
            logger.info(f"维护 {torrent.log_repr} | 删除标签: {to_remove_tags}")
            return True
        return False

    def _add_episode_tags(self, torrent: TorrentRecord, dry_run: bool):
        """种子添加时自动添加集数标签(如 zE1-5)

        仅种子添加时触发(由 QbManager 在 added 循环调用), 非周期任务。
        名称已含集数标记(S01E01/EP01/第1集等) -> 跳过; 否则从文件列表解析集数(走 store 惰性缓存),
        如 01.mkv~05.mkv -> 添加自定义模板标签(单集用 add_tag_single, 多集用 add_tag_multi)。
        解析不到集数(电影/合集等)或集数非连续则不加标签, 避免错标。
        """
        cfg = self.config.add_episode_tags
        if not cfg.enabled:
            return
        episodes_list = episodes.extract_episodes_from_files(torrent.files(self.client))
        if not episodes_list:
            return  # 文件列表无集数(电影/合集), 不加标签
        tag = episodes.format_episode_tag(episodes_list, cfg.add_tag_single, cfg.add_tag_multi)
        if not tag:
            return  # 集数非连续(存在缺集/误提取), 放弃添加
        self._add_tags(torrent, [tag], dry_run)

    def _remove_similar_tags(self, torrent: TorrentRecord, tags: List[str], dry_run: bool):
        """删除类似(单词相同大小写不同)的tag"""
        if not tags:
            return False

        current_tags = torrent.tags_set

        # 删除单词相同但大小写不一致的标签
        to_remove_tags = [tag for tag in current_tags if tag.lower() in [t.lower() for t in tags] and tag not in tags]
        if to_remove_tags:
            if not dry_run:
                self.api.torrents_remove_tags(tags=to_remove_tags, torrent_hashes=torrent.hash)
            logger.info(f"维护 {torrent.log_repr} | 删除相似标签: {to_remove_tags}")
            return True

        return False

    def _set_category(self, torrent: TorrentRecord, category: str, overwrite: bool, dry_run: bool):
        """设置种子的分类"""
        old_category = torrent.category

        if old_category == category:  # 分类已存在
            return False

        auto_categories = self.state.setdefault("auto_categories", {})

        # 定义一个内部函数可以利用if短路
        def can_update_previous():
            previous_auto_category = auto_categories.get(torrent.hash)
            return old_category == previous_auto_category

        if not old_category or overwrite or can_update_previous():  # 分类为空、强制覆盖或更新此前自动分类
            self._create_category_if_not_exists(category, dry_run)

            # 设置分类
            if not dry_run:
                self.api.torrents_set_category(category=category, torrent_hashes=torrent.hash)
                auto_categories[torrent.hash] = category

            # 打印日志
            if old_category:
                logger.info(f"维护 {torrent.log_repr} | 修改分类: '{old_category}' -> '{category}'")
            else:
                logger.info(f"维护 {torrent.log_repr} | 设置分类: '{category}'")

            return True
        else:  # 存在分类但不覆盖
            logger.warning(f"维护 {torrent.log_repr} | 跳过设置分类: 已有分类 '{old_category}' 且不覆盖")
            return True

    def _create_category_if_not_exists(self, category: str, dry_run: bool):
        """如果分类不存在则创建分类(全部分类走 store 惰性缓存, 创建后失效) """
        current_categories = self.store.all_categories()
        if category not in current_categories:  # 分类不存在
            if not dry_run:
                self.api.torrents_create_category(name=category)
            logger.info(f"创建分类: '{category}'")

    # ---------- HR ----------

    @staticmethod
    def _fmt_hr(template: str, hr: HRRule) -> str:
        """HR 格式变量替换: ${required_seeding_time}"""
        return (str(template).replace("${required_seeding_time}", hr.required_seeding_time_raw))

    def _add_hr_tag_or_category(self, torrent: TorrentRecord, tracker_conf: TrackerConfig, dry_run: bool):
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
            dlratio = torrent.downloaded / torrent.total_size if torrent.total_size else 0
            condition_met = dlratio >= cond_value
        else:  # dlsize
            condition_met = torrent.downloaded >= cond_value
        if not condition_met:
            return False

        added = False

        # 做种时长满足 或 分享率达标, 添加 satisfied 标签/分类
        seeding_ok = torrent.seeding_time >= (hr.required_seeding_time + hr.extra_seeding_time)
        ratio_ok = hr.required_share_ratio > 0 and (torrent.ratio or 0) >= hr.required_share_ratio
        if seeding_ok or ratio_ok:
            if hr.add_tag_for_satisfied:
                added |= self._add_tags(torrent, [self._fmt_hr(hr.add_tag_for_satisfied, hr)], dry_run)
            if hr.add_category_for_satisfied:
                added |= self._set_category(
                    torrent,
                    self._fmt_hr(hr.add_category_for_satisfied, hr),
                    hr.overwrite_category_for_satisfied,
                    dry_run,
                )

            return added
        else:  # 做种时长不够 且 分享率未达标: 添加 HR 标签/分类
            if hr.add_tag:
                added |= self._add_tags(torrent, [self._fmt_hr(hr.add_tag, hr)], dry_run)
            if hr.add_category:
                added |= self._set_category(torrent, self._fmt_hr(hr.add_category, hr), hr.overwrite_category, dry_run)

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
            all_tags = self.store.all_tags()  # 惰性缓存
        except Exception as e:
            logger.error(f"获取标签列表失败: {e}")
            return True
        matched = [t for t in all_tags if utils.match_tag_patterns(t, patterns)]
        if not matched:
            return True
        if not dry_run:
            self.api.torrents_delete_tags(tags=matched)
        logger.info(f"彻底删除标签: {matched}")
        return True

    def _handle_delete_tags_if_has_no_torrents(self, task, dry_run: bool) -> bool:
        """全局任务: 彻底删除无种子的标签(支持正则, regex: 前缀)

        仅当标签定义存在且没有任何种子使用(所有种子 tags 的并集之外)时才删除。
        """
        patterns = self.config.delete_tags_if_has_no_torrents or []
        if not patterns:
            return True
        try:
            all_tags = self.store.all_tags()  # 惰性缓存
        except Exception as e:
            logger.error(f"获取标签列表失败: {e}")
            return True
        if not all_tags:
            return True

        # 从快照聚合标签使用情况(替代 torrents.info(tag=) 逐个查询), 使用数为 0 则删除
        used = self.store.tag_usage()
        matched = [tag for tag in all_tags if utils.match_tag_patterns(tag, patterns) and used.get(tag, 0) == 0]

        if not matched:
            return True
        if not dry_run:
            self.api.torrents_delete_tags(tags=matched)
        logger.info(f"彻底删除无种子的标签: {matched}")

        return True
