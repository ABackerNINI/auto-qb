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

from qbittorrentapi import Client

from .config import Config, load_config
from .mixins import CheckingMixin, GroupingMixin, RuleEngineMixin, TagsMixin, TrackerMixin
from .qbapi import QbApi
from .rules import Rule
from .taskqueue import DEFERRED, Task, TaskQueue
from .torrents import TorrentRecord, TorrentStore
from . import utils
from .logging import setup_logging

logger = logging.getLogger(__name__)


class QbManager(RuleEngineMixin, TagsMixin, CheckingMixin, GroupingMixin, TrackerMixin):
    def __init__(self, config_path: str, config: Config = None):
        self.config_path = config_path
        self.config = config or load_config(config_path)
        self._setup_logging()
        # 种子信息数据层: 每 tick 全量快照 + 惰性缓存 + 分组索引 + 全局标签/分类缓存
        # 每 main_tick 刷新一次后, 本 tick 内所有读取操作都只通过 self.store 接口访问
        self.store = TorrentStore()
        self._client: Optional[Client] = None  # 由 client 属性管理, 与 store.client 同步
        # qB API 门面: 统一封装客户端调用 + 写操作后同步 store 快照(快照一致性)
        self.api = QbApi(self._client, self.store)
        # 状态持久化: 规则执行历史 / 上传量快照 / 跳检备份元数据
        self.state_file = self.config.state_file
        self.state = self._load_state()  # 从文件加载(run() 时再次加载覆盖; 直接使用(测试/process_torrent 入口)也含历史)
        # 规则结构初始化(规则加载在 run() 中进行: --export-yaml 等只导出模式不需要)
        self.rules: List[Rule] = []
        self.enabled_rules: List[Rule] = []
        # 任务队列: 统一管理所有任务(种子刷新/规则/种子级内置功能/异步校验/全局标签清理/分组)
        self.task_queue = TaskQueue()

    @property
    def client(self) -> Optional[Client]:
        """qBittorrent 客户端(与 store.client/api 同步绑定, 业务代码请走 self.api) """
        return self._client

    @client.setter
    def client(self, value: Optional[Client]):
        self._client = value
        if getattr(self, "store", None) is not None:
            self.store.client = value
        if getattr(self, "api", None) is not None:
            self.api.bind(value, self.store)

    def _setup_logging(self):
        logging_conf = self.config.logging
        setup_logging(logging_conf.file, logging_conf.level, logging_conf.max_bytes, logging_conf.format)

    def connect(self) -> bool:
        """连接 qBittorrent"""
        try:
            self.client = Client(
                host=self.config.qbittorrent.base_url,
                username=self.config.qbittorrent.username,
                password=self.config.qbittorrent.password,
            )
            self.api.auth_log_in()
            logger.info("Connected to qBittorrent successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to qBittorrent: {e}")
            return False

    def run(self, dry_run: bool):
        """主循环(任务队列驱动): 固定 MAIN_TICK 秒执行一次
        - 弹出到期任务并执行(种子刷新/规则/种子级内置功能/校验结果轮询, 各任务有内置 interval)
        """
        if not self.connect():
            return

        self.state = self._load_state()
        # 规则加载 + 全局任务创建仅运行模式需要(--export-yaml 等只导出模式在构造后直接退出, 跳过)
        self._load_rules()
        self._create_global_tasks()

        main_tick = self.config.main_tick

        logger.info(f"Starting qB manager: main tick {main_tick}s, default task interval {self.config.interval}s")
        logger.info(f"==========================================================================")
        try:
            while True:
                try:
                    self._tick(dry_run)
                except Exception as e:
                    logger.error(f"Error in main loop: {e}", exc_info=True)
                time.sleep(main_tick)
        except KeyboardInterrupt:
            logger.info("Stopping...")
        finally:
            if not dry_run:
                self.save_state()

    def _tick(self, dry_run: bool):
        """单次 tick: 1) 刷新快照 2) 弹出到期任务并执行"""
        now = time.time()

        self._refresh_torrents(dry_run)

        # 到期任务: 弹出并执行(校验结果轮询等有状态任务在 handler 内续延)
        due = self.task_queue.due(now, max=self.config.max_tasks_per_tick)
        if due:
            self._execute_due(due, dry_run, now)

    def _execute_due(self, due: list, dry_run: bool, now: float):
        """执行到期任务: 逐个执行任务(规则/种子级内置); handler 返回 False 表示任务消亡, 不重新入队"""
        # 1. 任务逐个执行; handler 返回 False 表示任务消亡(如种子已删除), 不重新入队
        logger.debug(f"执行到期任务: {len(due)}个")
        for task in due:
            keep = self._safe(task, dry_run)
            if task.state == DEFERRED:
                continue  # 任务已让位(如 full-checking 校验期间), 由校验任务完成后恢复, 不重新入队
            if keep is False:
                self.task_queue.task_died(task)  # 释放校验在途标记(如有)
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
        """校验结果轮询判定: 从快照查询种子当前状态, 退出校验(checking*)状态即视为完成

        不再拉取 API(校验完成最迟下一 tick 快照刷新后可见); 种子已删除/未知 -> 视为完成。
        """
        rec = self.store.get(torrent_hash)
        if rec is None:
            return True  # 种子已被删除, 视为完成
        state = (rec.state or "").lower()
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

    def _get_torrent(self, torrent_hash: str) -> Optional[TorrentRecord]:
        """从快照查询单个种子(惰性缓存/分组字段随记录保留); 种子已删除返回 None"""
        return self.store.get(torrent_hash)

    def _refresh_torrents(self, dry_run: bool = False):
        """种子列表刷新: 拉全量 -> store.refresh 增删检测 -> 新种子创建内置+规则任务并归组,
        删除种子移除任务, 分组事件(新增归组+大小一致性/删除/上传转暂停)检测到即立即处理,
        更新状态快照。本 tick 刷新后所有读取操作都只通过 store 接口, 不再重复拉取 API。"""
        torrents = self.api.torrents_info()
        added, removed = self.store.refresh(torrents)

        if added:
            logger.info(f"检测到新增种子 {len(added)} 个, 创建内置+规则任务")
            for h in added:
                self._create_torrent_tasks(h)
                # 增量归组: 新种子(含程序启动首轮的现有种子)按文件列表自动归组, 归组时检查大小一致性
                if self.config.grouping.enabled:
                    self._assign_new_torrent(h, dry_run)
                # 自动添加集数标签(仅种子添加时触发): 名称不含集数标记时从文件列表解析, 如 E1-5
                if self.config.add_episode_tags:
                    self._add_episode_tags(h, dry_run)

                # TODO: 优化
                # tracker单种限速
                tracker_conf = self._match_tracker(h)
                if tracker_conf:
                    self._apply_speed_limit(self.store.get(h), tracker_conf, dry_run)
        if removed:
            logger.info(f"检测到删除种子 {len(removed)} 个, 移除对应任务")
            for h in removed:
                self.task_queue.remove_torrent(h)
            # 组内种子被删除 -> 立即触发缺文件扫描(剩余种子可能文件丢失), 不等下一轮
            if self.config.grouping.enabled:
                self._handle_removed_torrents(removed, dry_run)
        if self.config.grouping.enabled:
            # 保存路径变化重归组(文件列表变化会走新增种子重新归组)
            self._handle_save_path_changes(dry_run)
            # 组内种子由上传(做种)转暂停 -> 立即触发缺文件扫描(用上一轮状态快照, 不等下一轮)
            self._handle_state_transitions(dry_run)
            # 下载冲突检查(每轮): 同组多个同时下载/已完成与下载中并存 -> 警告+整组暂停
            self._check_download_conflicts(dry_run)
            # 更新状态快照(仅本轮可见种子; 存 state_enum 枚举对象, 与 qB 版本无关;
            # 新增种子本轮不视为状态变化)
            self.store.update_state_snapshot(torrents)

        # 上传量快照(按自然日/周/月, 周期切换时重建基线) — 幂等
        self.begin_round(list(self.store.by_hash.values()))

    def _create_torrent_tasks(self, torrent_hash: str):
        """为新增种子创建任务: 内置 maintenance + 所有符合条件的规则任务

        缺文件检查统一由分组事件驱动承担(_refresh_torrents 检测到删除/状态变化/
        保存路径变化立即触发组内扫描), 不再创建逐种子 missing_files 任务。
        每个任务有内置 interval(规则任务用规则自身 interval), 加入队列即立即到期(下一 tick 执行)。
        """

        tor = self.store.get(torrent_hash)
        if not tor:
            return

        # TODO: 优化
        # 查找种子的tracker配置
        tracker_conf = self._match_tracker(tor.hash)
        if not tracker_conf:
            trackers_info = self.store.trackers_info(tor.hash)
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

    def export_torrents_info(self, path):
        """导出种子信息, 用于debug"""
        torrents = self.client.torrents_info()
        with open(path, "w") as f:
            for tor in torrents:
                f.write(f"{tor}\n\n")
