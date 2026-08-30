"""QbManager: qBittorrent 主管理类

任务队列统一协调: 种子刷新 / 规则 / 种子级内置功能 / 异步校验 全部是带内置 interval 的任务。
检测到新增种子时, 自动为该种子创建所有符合条件的 rule 任务(tracker 引用规则或全部启用规则)。

职责拆分(mixins 包, 各模块组合进本类):
- mixins.rule_engine  RuleEngineMixin  规则加载/状态持久化/种子级规则任务/process_torrent 兼容入口
- mixins.tags         TagsMixin        标签/分类/HR 辅助
- mixins.checking     CheckingMixin    文件检查/辅种跳检/异步校验轮询回调
- mixins.grouping     GroupingMixin    种子分组管理(辅种管理): 分组 + 组内大小一致性 + 缺文件联动
- mixins.tracker      TrackerMixin     tracker 配置匹配
"""
import logging
import time
from typing import List, Optional

from qbittorrentapi import Client, TorrentDictionary

from .config import Config, load_config
from .mixins import CheckingMixin, GroupingMixin, RuleEngineMixin, TagsMixin, TrackerMixin
from .rules import Rule
from .taskqueue import Task, TaskQueue
from . import utils

# 主循环 tick 间隔(秒): 唯一的循环粒度, 每个任务有内置 interval 决定自身执行频率
MAIN_TICK = 2.0

logger = logging.getLogger(__name__)


class QbManager(RuleEngineMixin, TagsMixin, CheckingMixin, GroupingMixin, TrackerMixin):
    def __init__(self, config_path: str, config: Config = None):
        self.config_path = config_path
        self.config = config or load_config(config_path)
        self.client: Optional[Client] = None
        self._setup_logging()
        # 状态持久化: 规则执行历史 / 上传量快照 / 跳检备份元数据
        self.state_file = self.config.state_file
        self.state = self._load_state()
        # 规则加载(条件+动作插件, manager 即本对象: 提供执行历史/状态/任务队列)
        self.rules: List[Rule] = []
        self.enabled_rules: List[Rule] = []
        self._load_rules()
        # 任务队列: 统一管理所有任务(种子刷新/规则/种子级内置功能/异步校验/全局标签清理/分组)
        self.task_queue = TaskQueue()
        # 全局任务: 彻底删除标签 / 彻底删除无种子的标签 / 种子分组(有配置才创建)
        self._create_global_tasks()
        # 种子增删检测: 上一轮已知 hash 集合, None 表示首轮(首次刷新为全部现有种子创建任务)
        self._known_hashes: Optional[set] = None
        # 最近一次种子快照: 新增种子创建任务/规则条件(上传量基线)使用
        self._snapshot: list = []
        # 分组状态快照: 组内种子状态变化检测(上传转暂停触发缺文件扫描, 由 GroupingMixin 使用)
        self._group_state_snapshot: dict = {}
        # 增量分组: key=(save_path, 排序文件路径元组) -> [hash...]; 新增种子时归组, 事件驱动, 无周期轮询
        self._groups: dict = {}
        # 组内缓存的文件大小映射: key -> {hash: {规范化相对路径: 大小}}(增量归组时拉取)
        self._group_sizes: dict = {}
        # 分组成员索引: hash -> 组 key, 删除/状态变化/save_path 同步时 O(1) 定位所属组, 避免遍历分组
        self._group_member_to_key: dict = {}
        # 内存参考种子集合(仅内存, 重启后重新积累): full-checking 校验通过的种子, 可作为同组参考
        self.verified_references: set = set()

    def _setup_logging(self):
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    def connect(self) -> bool:
        """连接 qBittorrent"""
        try:
            self.client = Client(
                host=self.config.qbittorrent.base_url,
                username=self.config.qbittorrent.username,
                password=self.config.qbittorrent.password,
            )
            self.client.auth_log_in()
            logger.info("Connected to qBittorrent successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to qBittorrent: {e}")
            return False

    def run(self, dry_run: bool):
        """主循环(任务队列驱动): 固定 MAIN_TICK 秒执行一次
        - 轮询慢速队列(异步校验完成情况)
        - 弹出快速队列到期任务并执行(种子刷新/规则/种子级内置功能, 各任务有内置 interval)
        """
        if not self.connect():
            return

        logger.info(f"Starting qB manager: main tick {MAIN_TICK}s, default task interval {self.config.interval}s")
        logger.info(f"==========================================================================")
        try:
            while True:
                try:
                    self._tick(dry_run)
                except Exception as e:
                    logger.error(f"Error in main loop: {e}", exc_info=True)
                time.sleep(MAIN_TICK)
        except KeyboardInterrupt:
            logger.info("Stopping...")
        finally:
            self.task_queue.shutdown(wait=False)
            if not dry_run:
                self.save_state()

    def _tick(self, dry_run: bool):
        """单次 tick: 1) 轮询慢速队列(异步校验) 2) 弹出快速队列到期任务并执行"""
        now = time.time()

        self._refresh_torrents(dry_run)

        # 1. 慢速队列: 轮询异步校验结果(仅当有待处理任务时才查询客户端)
        if self.task_queue.pending_slow():
            completed = self.task_queue.poll_slow(self._is_check_done)
            for task in completed:
                if task.send_error is not None:
                    logger.warning(f"异步校验任务异常({task.torrent_hash}): {task.send_error}")

        # 2. 快速队列: 弹出到期任务并执行
        due = self.task_queue.due(now, max=20)
        if due:
            self._execute_due(due, dry_run, now)

    def _execute_due(self, due: list, dry_run: bool, now: float):
        """执行到期任务: 逐个执行任务(规则/种子级内置)"""
        # 1. 任务逐个执行; handler 返回 False 表示任务消亡(如种子已删除), 不重新入队
        logger.debug(f"执行到期任务: {len(due)}个")
        for task in due:
            keep = self._safe(task, dry_run)
            if keep is False:
                continue
            self.task_queue.reschedule(task, now)

    def _safe(self, task: Task, dry_run: bool) -> bool:
        """执行任务 handler, 捕获异常; 返回 handler 结果(默认 True 重新入队)"""
        try:
            if task.handler:
                return bool(task.handler(task, dry_run))
        except Exception as e:
            logger.error(f"任务执行异常({task.kind}:{task.name} {task.torrent_hash}): {e}")
        return True

    def _is_check_done(self, torrent_hash: str) -> bool:
        """慢速队列轮询回调: 查询种子当前状态, 退出校验(checking*)状态即视为完成"""
        try:
            infos = self.client.torrents_info(torrent_hashes=torrent_hash)
        except Exception as e:
            logger.debug(f"查询校验状态失败({torrent_hash}): {e}")
            return False
        if not infos:
            return True  # 种子已被删除, 视为完成
        state = (infos[0].state or "").lower()
        return not state.startswith("checking")

    # ---------- 全局任务 ----------

    def _create_global_tasks(self):
        """创建全局任务(非种子级): 彻底删除标签 / 彻底删除无种子的标签, 加入队列统一管理

        对应配置为空时跳过; 标签清理任务使用主 interval。种子分组为事件驱动
        (_refresh_torrents 检测到增删/状态变化立即处理), 不再创建周期轮询任务。
        """
        tasks = []
        if self.config.delete_tags:
            tasks.append(
                Task(
                    "internal",
                    "delete_tags",
                    interval=self.config.interval,
                    handler=self._handle_delete_tags,
                )
            )
        if self.config.delete_tags_if_has_no_torrents:
            tasks.append(
                Task(
                    "internal",
                    "delete_tags_if_has_no_torrents",
                    interval=self.config.interval,
                    handler=self._handle_delete_tags_if_has_no_torrents,
                )
            )
        if tasks:
            self.task_queue.add_tasks(tasks)
            logger.info(f"创建全局任务 {len(tasks)} 个: {[t.name for t in tasks]}")

    # ---------- 种子级任务 ----------

    def _get_torrent(self, torrent_hash: str) -> Optional[TorrentDictionary]:
        """拉取单个种子信息; 种子已删除返回 None"""
        try:
            infos = self.client.torrents_info(torrent_hashes=torrent_hash)
        except Exception:
            return None
        return infos[0] if infos else None

    def _refresh_torrents(self, dry_run: bool = False):
        """种子列表刷新: 拉全量 -> 增删检测 -> 新种子创建内置+规则任务并归组, 删除种子移除任务,
        分组事件(新增归组+大小一致性/删除/上传转暂停)检测到即立即处理, 更新状态快照"""
        torrents = self.client.torrents_info()
        current_hashes = {t.hash for t in torrents}
        by_hash = {t.hash: t for t in torrents}
        self._snapshot = torrents

        if self._known_hashes is not None:
            added = current_hashes - self._known_hashes
            removed = self._known_hashes - current_hashes
        else:
            added = current_hashes  # 首轮: 为所有现有种子创建任务
            removed = set()
        if added:
            logger.info(f"检测到新增种子 {len(added)} 个, 创建内置+规则任务")
            for h in added:
                self._create_torrent_tasks(h)
                # 增量归组: 新种子(含程序启动首轮的现有种子)按文件列表自动归组, 归组时检查大小一致性
                if self.config.grouping.enabled:
                    self._assign_new_torrent(h, by_hash, dry_run)
                # 自动添加集数标签(仅种子添加时触发): 名称不含集数标记时从文件列表解析, 如 E1-5
                if self.config.add_episode_tags:
                    self._add_episode_tags(h, by_hash, dry_run)
        if removed:
            logger.info(f"检测到删除种子 {len(removed)} 个, 移除对应任务")
            for h in removed:
                self.task_queue.remove_torrent(h)
            # 组内种子被删除 -> 立即触发缺文件扫描(剩余种子可能文件丢失), 不等下一轮
            if self.config.grouping.enabled:
                self._handle_removed_torrents(removed, by_hash, dry_run)
        if self.config.grouping.enabled:
            # 保存路径变化重归组(文件列表变化会走新增种子重新归组)
            self._handle_save_path_changes(by_hash, dry_run)
            # 组内种子由上传(做种)转暂停 -> 立即触发缺文件扫描(用上一轮状态快照, 不等下一轮)
            self._handle_state_transitions(by_hash, dry_run)
            # 下载冲突检查(每轮): 同组多个同时下载/已完成与下载中并存 -> 警告+整组暂停
            self._check_download_conflicts(by_hash, dry_run)
            # 更新状态快照(仅本轮可见种子; 存 state_enum 枚举对象, 与 qB 版本无关;
            # 新增种子本轮不视为状态变化)
            self._group_state_snapshot = {t.hash: t.state_enum for t in torrents}

        self._known_hashes = current_hashes
        # 上传量快照(按自然日/周/月, 周期切换时重建基线) — 幂等
        self.begin_round(torrents)

    def _create_torrent_tasks(self, torrent_hash: str):
        """为新增种子创建任务: 内置 maintenance + 所有符合条件的规则任务

        缺文件检查统一由分组事件驱动承担(_refresh_torrents 检测到删除/状态变化/
        保存路径变化立即触发组内扫描), 不再创建逐种子 missing_files 任务。
        每个任务有内置 interval(规则任务用规则自身 interval), 加入队列即立即到期(下一 tick 执行)。
        """

        tor = next((t for t in self._snapshot if t.hash == torrent_hash), None)
        if not tor:
            return

        # 查找种子的tracker配置
        tracker_conf = self._match_tracker(tor)
        if not tracker_conf:
            trackers_info = self.client.torrents_trackers(tor.hash)
            all_domains = utils.extract_tracker_hostnames(trackers_info)
            logger.warning(f"种子未匹配tracker配置: tracker: {", ".join(all_domains)}, 哈希: {tor.hash}")
            return False  # 未匹配tracker配置, 直接跳过

        tasks = []

        # 创建内置种子任务
        tasks.append(
            Task(
                "internal",
                "maintenance",
                torrent_hash=torrent_hash,
                tracker_conf=tracker_conf,
                interval=self.config.interval,
                handler=self._handle_maintenance
            )
        )

        # 创建种子规则任务
        for rule in self._rules_for_torrent(tor):
            tasks.append(self._create_rule_task(rule, torrent_hash, tracker_conf))

        self.task_queue.add_tasks(tasks)

    def _handle_maintenance(self, task: Task, dry_run: bool) -> bool:
        """内置种子级任务: 添加/删除/相似标签 + HR 标签分类"""
        tor = self._get_torrent(task.torrent_hash)
        if tor is None:
            return False

        tracker_conf = task.tracker_conf
        assert tracker_conf is not None

        handled = False
        handled |= self._add_tags(tor, tracker_conf.tags, dry_run)
        handled |= self._remove_tags(tor, tracker_conf.remove_tags, dry_run)
        if tracker_conf.remove_similar_tags:  # 站点覆盖全局后的值
            handled |= self._remove_similar_tags(tor, tracker_conf.tags, dry_run)
        if tracker_conf.hr:  # 站点合并全局默认后的 HR 设置
            handled |= self._add_hr_tag_or_category(tor, tracker_conf, dry_run)
        if handled:
            self._log_torrent_details(tor, tracker_conf)
            logger.info(f"--------------------------------------------------------------------------")
        return True
