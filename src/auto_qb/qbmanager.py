"""QbManager: qBittorrent 主管理类

任务队列统一协调: 种子刷新 / 规则 / 种子级内置功能 / 异步校验 全部是带内置 interval 的任务。
检测到新增种子时, 自动为该种子创建所有符合条件的 rule 任务(tracker 引用规则或全部启用规则)。

职责拆分(mixins 包, 各模块组合进本类):
- mixins.rule_engine  RuleEngineMixin  规则加载/状态持久化/种子级规则任务/process_torrent 兼容入口
- mixins.tags         TagsMixin        标签/分类/HR 辅助
- mixins.checking     CheckingMixin    文件检查/辅种跳检/异步校验轮询回调
- mixins.tracker      TrackerMixin     tracker 配置匹配
"""
import logging
import time
from typing import List, Optional

from qbittorrentapi import Client, TorrentDictionary

from .config import Config, load_config
from .mixins import CheckingMixin, RuleEngineMixin, TagsMixin, TrackerMixin
from .rules import Rule
from .taskqueue import Task, TaskQueue

# 主循环 tick 间隔(秒): 唯一的循环粒度, 每个任务有内置 interval 决定自身执行频率
MAIN_TICK = 2.0


class QbManager(RuleEngineMixin, TagsMixin, CheckingMixin, TrackerMixin):
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
        # 任务队列: 统一管理所有任务(种子刷新/规则/种子级内置功能/异步校验/全局标签清理)
        self.task_queue = TaskQueue()
        # 全局任务: 彻底删除标签 / 彻底删除无种子的标签(有配置才创建)
        self._create_global_tasks()
        # 种子增删检测: 上一轮已知 hash 集合, None 表示首轮(首次刷新为全部现有种子创建任务)
        self._known_hashes: Optional[set] = None
        # 最近一次种子快照: 新增种子创建任务/规则条件(上传量基线)使用
        self._snapshot: list = []

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
            self.task_queue.shutdown(wait=False)
            if not dry_run:
                self.save_state()

    def _tick(self, dry_run: bool):
        """单次 tick: 1) 轮询慢速队列(异步校验) 2) 弹出快速队列到期任务并执行"""
        now = time.time()

        self._refresh_torrents()

        # 1. 慢速队列: 轮询异步校验结果(仅当有待处理任务时才查询客户端)
        if self.task_queue.pending_slow():
            completed = self.task_queue.poll_slow(self._is_check_done)
            for task in completed:
                if task.send_error is not None:
                    self.logger.warning(f"异步校验任务异常({task.torrent_hash}): {task.send_error}")

        # 2. 快速队列: 弹出到期任务并执行
        due = self.task_queue.due(now)
        if due:
            self._execute_due(due, dry_run, now)

    def _execute_due(self, due: list, dry_run: bool, now: float):
        """执行到期任务: 逐个执行任务(规则/种子级内置)"""
        # 1. 任务逐个执行; handler 返回 False 表示任务消亡(如种子已删除), 不重新入队
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

    # ---------- 全局任务 ----------

    def _create_global_tasks(self):
        """创建全局任务(非种子级): 彻底删除标签 / 彻底删除无种子的标签, 加入队列统一管理

        对应配置为空时跳过; 任务使用主 interval 定期执行。
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
            self.logger.info(f"创建全局标签清理任务 {len(tasks)} 个: {[t.name for t in tasks]}")

    # ---------- 种子级任务 ----------

    def _get_torrent(self, torrent_hash: str) -> Optional[TorrentDictionary]:
        """拉取单个种子信息; 种子已删除返回 None"""
        try:
            infos = self.client.torrents_info(torrent_hashes=torrent_hash)
        except Exception:
            return None
        return infos[0] if infos else None

    def _refresh_torrents(self):
        """种子列表刷新: 拉全量 -> 增删检测 -> 新种子创建内置+规则任务, 删除种子移除任务, 更新快照"""
        torrents = self.client.torrents_info()
        current_hashes = {t.hash for t in torrents}
        self._snapshot = torrents

        if self._known_hashes is not None:
            added = current_hashes - self._known_hashes
            removed = self._known_hashes - current_hashes
        else:
            added = current_hashes  # 首轮: 为所有现有种子创建任务
            removed = set()
        if added:
            self.logger.info(f"检测到新增种子 {len(added)} 个, 创建内置+规则任务")
            for h in added:
                self._create_torrent_tasks(h)
        if removed:
            self.logger.info(f"检测到删除种子 {len(removed)} 个, 移除对应任务")
            for h in removed:
                self.task_queue.remove_torrent(h)

        self._known_hashes = current_hashes
        # 上传量快照(按自然日/周/月, 周期切换时重建基线) — 幂等
        self.begin_round(torrents)

    def _create_torrent_tasks(self, torrent_hash: str):
        """为新增种子创建任务: 内置功能(missing_files/maintenance) + 所有符合条件的规则任务

        每个任务有内置 interval(规则任务用规则自身 interval), 加入队列即立即到期(下一 tick 执行)。
        """
        tor = next((t for t in self._snapshot if t.hash == torrent_hash), None)
        tasks = []
        if self.config.check_missing_files:
            tasks.append(
                Task(
                    "internal",
                    "missing_files",
                    torrent_hash=torrent_hash,
                    interval=self.config.interval,
                    handler=self._handle_missing_files
                )
            )
        tasks.append(
            Task(
                "internal",
                "maintenance",
                torrent_hash=torrent_hash,
                interval=self.config.interval,
                handler=self._handle_maintenance
            )
        )
        if tor is not None:
            for rule in self._rules_for_torrent(tor):
                tasks.append(self._create_rule_task(rule, torrent_hash))
        self.task_queue.add_tasks(tasks)

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
        if tracker_conf.remove_similar_tags:  # 站点覆盖全局后的值
            handled |= self._remove_similar_tags(tor, tracker_conf.tags, dry_run)
        if tracker_conf.hr:  # 站点合并全局默认后的 HR 设置
            handled |= self._add_hr_tag_or_category(tor, tracker_conf, dry_run)
        if handled:
            self._log_torrent_details(tor, tracker_conf)
            self.logger.info(f"--------------------------------------------------------------------------")
        return True
