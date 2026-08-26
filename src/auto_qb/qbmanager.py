"""QbManager: qBittorrent 主管理类(任务队列驱动 + 规则框架集成 + 主循环)"""
import logging
import os
import re
import time
from typing import List, Optional

from qbittorrentapi import Client, TorrentDictionary

from .config import Config, TrackerConfig, load_config
from .rules import RuleManager
from .taskqueue import Task
from .utils import add_long_path_prefix_for_win, parse_hr_rule

# 主循环 tick 间隔(秒): 唯一的循环粒度, 每个任务有内置 interval 决定自身执行频率
MAIN_TICK = 2.0


class QbManager:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config: Config = load_config(config_path)
        self.client: Optional[Client] = None
        self._setup_logging()
        # 规则框架: 统一管理规则插件(条件+动作), 配置来自 config 下 *_rules 段
        self.rules = RuleManager(self.config, self.config.state_file)
        # 种子增删检测: 上一轮已知 hash 集合, None 表示首轮(首次刷新为全部现有种子创建任务)
        self._known_hashes: Optional[set] = None
        # 最近一次种子快照: 规则任务执行时使用的种子列表
        self._snapshot: list = []
        # 注册种子列表刷新任务(interval = config.interval, 首次立即执行)
        self.rules.task_queue.add_task(
            Task("refresh", "refresh", interval=self.config.interval, handler=self._refresh_torrents)
        )

    def _setup_logging(self):
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
        self.logger = logging.getLogger("QbManager")

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
        """主循环(任务队列驱动): 固定 MAIN_TICK 秒执行一次
        - 轮询慢速队列(异步校验完成情况)
        - 弹出快速队列到期任务并执行(种子刷新/规则/种子级内置功能, 各任务有内置 interval)
        """
        if not self.connect():
            return

        self.logger.info(f"Starting qB manager: main tick {MAIN_TICK}s, default task interval {self.config.interval}s")
        self.logger.info(f"==========================================================================")
        try:
            while True:
                try:
                    self._tick(dry_run)
                except Exception as e:
                    self.logger.error(f"Error in main loop: {e}")
                time.sleep(MAIN_TICK)
        except KeyboardInterrupt:
            self.logger.info("Stopping...")
        finally:
            self.rules.shutdown(wait=False)

    def _tick(self, dry_run: bool):
        """单次 tick: 1) 轮询慢速队列(异步校验) 2) 弹出快速队列到期任务并执行"""
        now = time.time()

        # 1. 慢速队列: 轮询异步校验结果(仅当有待处理任务时才查询客户端)
        if self.rules.task_queue.pending_slow():
            completed = self.rules.task_queue.poll_slow(self._is_check_done)
            for task in completed:
                if task.send_error is not None:
                    self.logger.warning(f"异步校验任务异常({task.torrent_hash}): {task.send_error}")

        # 2. 快速队列: 弹出到期任务并执行
        due = self.rules.task_queue.due(now)
        if due:
            self._execute_due(due, dry_run, now)

    def _execute_due(self, due: list, dry_run: bool, now: float):
        """执行到期任务: 先种子刷新(更新快照) -> 规则任务聚合执行(一次快照遍历) -> 其他任务"""
        # 1. 种子刷新任务先执行, 保证规则/内置任务使用最新快照
        for task in due:
            if task.kind == "refresh":
                self._safe(task, dry_run)
        # 2. 规则任务聚合: 所有到期规则一起跑(一次遍历种子快照, 维护上传量基线)
        rule_names = {t.name for t in due if t.kind == "rule"}
        if rule_names and self._snapshot:
            self.rules.run_rules(rule_names, self._snapshot, dry_run)
        # 3. 种子级内置功能任务(handler 返回 False 则任务消亡, 不重新入队)
        for task in due:
            if task.kind not in ("refresh", "rule"):
                keep = self._safe(task, dry_run)
                if keep is False:
                    continue
                self.rules.task_queue.reschedule(task, now)
        # 4. 刷新/规则任务按内置 interval 重新入队
        for task in due:
            if task.kind in ("refresh", "rule"):
                self.rules.task_queue.reschedule(task, now)

    def _safe(self, task: Task, dry_run: bool) -> bool:
        """执行任务 handler, 捕获异常; 返回 handler 结果(默认 True 重新入队)"""
        try:
            if task.handler:
                return bool(task.handler(task, dry_run))
        except Exception as e:
            self.logger.error(f"任务执行异常({task.kind}:{task.name} {task.torrent_hash}): {e}")
        return True

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

    # ---------- 种子级任务 ----------

    def _get_torrent(self, torrent_hash: str) -> Optional[TorrentDictionary]:
        """拉取单个种子信息; 种子已删除返回 None"""
        try:
            infos = self.client.torrents_info(torrent_hashes=torrent_hash)
        except Exception:
            return None
        return infos[0] if infos else None

    def _refresh_torrents(self, task: Task, dry_run: bool) -> bool:
        """种子列表刷新任务: 拉全量 -> 增删检测 -> 新种子创建内置任务, 删除种子移除任务, 更新快照"""
        torrents = self.client.torrents_info()
        current_hashes = {t.hash for t in torrents}

        if self._known_hashes is not None:
            added = current_hashes - self._known_hashes
            removed = self._known_hashes - current_hashes
        else:
            added = current_hashes  # 首轮: 为所有现有种子创建任务
            removed = set()
        if added:
            self.logger.info(f"检测到新增种子 {len(added)} 个, 创建内置任务")
            for h in added:
                self._create_torrent_tasks(h)
        if removed:
            self.logger.info(f"检测到删除种子 {len(removed)} 个, 移除对应任务")
            for h in removed:
                self.rules.task_queue.remove_torrent(h)

        self._known_hashes = current_hashes
        self._snapshot = torrents
        return True

    def _create_torrent_tasks(self, torrent_hash: str):
        """为新增种子创建内置功能任务(每个任务有内置 interval = config.interval, 加入即立即到期)"""
        tasks = []
        if self.config.check_missing_files:
            tasks.append(
                Task(
                    "torrent",
                    "missing_files",
                    torrent_hash=torrent_hash,
                    interval=self.config.interval,
                    handler=self._handle_missing_files
                )
            )
        tasks.append(
            Task(
                "torrent",
                "maintenance",
                torrent_hash=torrent_hash,
                interval=self.config.interval,
                handler=self._handle_maintenance
            )
        )
        self.rules.task_queue.add_tasks(tasks)

    def _handle_missing_files(self, task: Task, dry_run: bool) -> bool:
        """种子级任务: 检查文件丢失(缺失则暂停并加 MISSING 标签); 种子已删返回 False 任务消亡"""
        tor = self._get_torrent(task.torrent_hash)
        if tor is None:
            return False
        if self.config.check_missing_files:
            self._check_and_handle_missing_files(tor, dry_run)
        return True

    def _handle_maintenance(self, task: Task, dry_run: bool) -> bool:
        """种子级任务: tracker 匹配 + 添加/删除/相似标签 + HR 标签分类(原 _process_single_torrent 步骤 3-7)"""
        tor = self._get_torrent(task.torrent_hash)
        if tor is None:
            return False

        tracker_conf = self._match_tracker(tor)
        if not tracker_conf:
            self.logger.debug(f"未匹配 tracker 配置, 跳过内置维护: {tor.hash}")
            return True

        handled = False
        handled |= self._add_tags(tor, tracker_conf.tags, dry_run)
        handled |= self._remove_tags(tor, tracker_conf.remove_tags, dry_run)
        if self.config.remove_similar_tags:
            handled |= self._remove_similar_tags(tor, tracker_conf.tags, dry_run)
        if tracker_conf.hr_rule and (self.config.add_hr_tags or self.config.add_hr_categories):
            handled |= self._add_hr_tag_or_category(tor, tracker_conf.hr_rule, dry_run)
        if handled:
            self._log_torrent_details(tor, tracker_conf)
            self.logger.info(f"--------------------------------------------------------------------------")
        return True

    def _log_torrent_details(self, tor: TorrentDictionary, tracker_conf: TrackerConfig | None) -> str:
        site = tracker_conf.name if tracker_conf else "未知"
        self.logger.info(f"种子: {tor.name}")
        self.logger.info(f"站点: {site}")
        self.logger.info(f"状态: {tor.state}")
        self.logger.info(f"哈希: {tor.hash}")

    # ---------- 标签/分类辅助 ----------

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
