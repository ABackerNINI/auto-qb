"""QbManager: qBittorrent 主管理类

任务队列统一协调: 种子刷新 / 规则 / 种子级内置功能 / 异步校验 全部是带内置 interval 的任务。
检测到新增种子时, 自动为该种子创建所有符合条件的 rule 任务(tracker 引用规则或全部启用规则)。

职责拆分(mixins 包, 各模块组合进本类):
- mixins.rule_engine  RuleEngineMixin  规则加载/状态持久化/种子级规则任务
- mixins.tags         TagsMixin        标签/分类/HR 辅助
- mixins.checking     CheckingMixin    文件存在性/大小一致性检查(checking 动作前置检查复用)
- mixins.grouping     GroupingMixin    种子分组管理(辅种管理): 分组 + 组内大小一致性 + 缺文件联动
- mixins.tracker      TrackerMixin     tracker 配置匹配/单种限速
- mixins.speed_curve  SpeedCurveMixin  全局限速曲线(Traffic Monitor 流量聚合 -> qB 全局限速)
"""
import logging
import os
import queue
import time
from typing import List, Optional

from qbittorrentapi import APIConnectionError, Client

from .config import Config, load_config
from .errors import AutoQbError
from .locking import SingleInstanceLock
from .mixins import CheckingMixin, GroupingMixin, RuleEngineMixin, SpeedCurveMixin, TagsMixin, TrackerMixin
from .notify import NotifyHandler, setup_notify
from .qbapi import QbApi
from .rules import Rule
from .taskqueue import FINISHED, REQUEUE, Task, TaskQueue
from .torrents import QbCompatError, TorrentRecord, TorrentStore, missing_torrent_fields
from . import utils
from .logging import setup_logging

logger = logging.getLogger(__name__)

WEB_VIEW_TTL = 10.0  # Web 客户端活跃窗口: 超时无请求则主循环跳过分组视图组装(惰性)
SEARCH_INDEX_BUILD_BUDGET = 500  # 搜索索引单次构建最多拉取的文件列表数(限流, 避免首轮 N 次 qB API 阻塞主循环)


class QbManager(RuleEngineMixin, TagsMixin, CheckingMixin, GroupingMixin, TrackerMixin, SpeedCurveMixin):
    def __init__(self, config_path: str, config: Config = None, no_lock: bool = False):
        self.config_path = config_path
        self.config = config or load_config(config_path)
        self._setup_logging()
        # 种子信息数据层: 每 tick 全量快照 + 惰性缓存 + 分组索引 + 全局标签/分类缓存
        # 每 main_tick 刷新一次后, 本 tick 内所有读取操作都只通过 self.store 接口访问
        self.store = TorrentStore()
        self._client: Optional[Client] = None  # 由 client 属性管理, 与 store.client 同步
        # qB API Facade: 统一封装客户端调用 + 写操作后同步 store 快照(快照一致性)
        self.api = QbApi(self._client, self.store)
        # 状态持久化: 规则执行历史 / 上传量快照 / 跳检备份元数据
        self.state_file = self.config.state_file
        # 数据目录(state/锁/日志/跳检备份同处): 显式建目录, 不依赖日志文件配置(console-only 时无日志建目录)
        os.makedirs(os.path.dirname(self.state_file) or ".", exist_ok=True)
        self.state = self._load_state()  # 从文件加载(run() 时再次加载覆盖; 直接使用(测试/process_torrent 入口)也含历史)
        # 规则结构初始化(规则加载在 run() 中进行: --export-yaml 等只导出模式不需要)
        self.rules: List[Rule] = []
        self.enabled_rules: List[Rule] = []
        # 任务队列: 统一管理所有任务(种子刷新/规则/种子级内置功能/异步校验/全局标签清理/分组)
        self.task_queue = TaskQueue()
        # 版本兼容校验: 首次拉到非空种子信息时执行一次(qB 版本运行期不变)
        self._schema_validated = False
        # 连接状态(节流重复连接错误日志): None=未知/首次, True=已连接, False=已断开
        # 仅状态转换时记录, 断开期间静默(qB 宕机时不刷屏)
        self._last_conn_ok: Optional[bool] = None
        # 主动通知 handler(run() 启用时挂载; dry-run/export 模式不挂载)
        self._notify_handler: Optional[NotifyHandler] = None
        # WEB UI: 控制命令队列(Web 线程投递, 主循环消费执行——写操作只在主循环线程)
        self.web_commands: "queue.Queue" = queue.Queue()
        # WEB UI: 分组视图快照(主循环每 tick 重建并原子替换, Web 线程只读)
        self._group_view: List[dict] = []
        # WEB UI 惰性组装: _group_view_dirty 标记快照是否过期; _web_last_seen 记录最近一次 Web 请求时间。
        # 主循环仅当 Web 客户端活跃(_web_last_seen 距今 < WEB_VIEW_TTL)才重建快照, 否则跳过以降低 CPU。
        self._group_view_dirty: bool = True
        self._web_last_seen: float = 0.0
        # WEB UI 搜索索引(hash -> {name, files[文件名]}): 主循环按需构建并原子替换, Web 线程只读。
        # 种子名匹配直接读 store.by_hash(即时无 API); 文件列表匹配依赖此索引(文件 API 只在主循环线程)。
        # 索引仅在种子集变化(added/removed)时置脏, 避免每 tick 重复构建; 记录 _files 缓存跨 tick 复用。
        self._search_index: Optional[dict] = None
        self._search_index_dirty: bool = True
        # WEB UI: 访问密钥/服务器句柄(run() 启用时确定)
        self._web_token: str = ""
        self._web_handle = None
        # 热重载后首轮抑制事件分派(全量重建的 added 重放保护)
        self._suppress_events = False
        # 暂停事件(run() 注入; UI 线程切换, 主循环线程只读)
        self._pause_event = None
        # 缺文件扫描轮内去重: 移动种子等场景同一轮会命中多个触发源(状态转移+路径变化),
        # 同组 key 同轮只扫一次(_refresh_torrents 每轮开始清空)
        self._missing_scanned_keys: set = set()
        # 单实例锁: 仅正常 run 模式持锁(--export-yaml 等只读模式传 no_lock=True 跳过, 允许并发)
        self._lock = None
        if not no_lock:
            self._lock = SingleInstanceLock(self.state_file)
            self._lock.acquire()

    @property
    def client(self) -> Optional[Client]:
        """qBittorrent 客户端(与 store.client/api 同步绑定, 业务代码请走 self.api) """
        return self._client

    @client.setter
    def client(self, value: Optional[Client]):
        self._client = value
        self.store.client = value
        self.api.bind(value, self.store)

    def _setup_logging(self):
        logging_conf = self.config.logging
        setup_logging(logging_conf.file, logging_conf.level, logging_conf.max_bytes, logging_conf.format)

    def connect(self) -> bool:
        """连接 qBittorrent"""
        try:
            qb = self.config.qbittorrent
            self.client = Client(
                host=qb.base_url,
                username=qb.username,
                password=qb.password,
            )
            self.api.auth_log_in()
            # 连接恢复(此前断开)或首次连接: 记录一次"已连接"状态
            if self._last_conn_ok is False:
                logger.info("已重新连接 qBittorrent")
            self._last_conn_ok = True
            return True
        except APIConnectionError as e:
            # 仅状态转换时记录一次失败(首次失败或从连接态转入); 断开期间静默不刷屏
            if self._last_conn_ok is not False:
                logger.error(f"连接 qBittorrent 失败: {e}")
                self._last_conn_ok = False
            return False
        except Exception as e:
            logger.error(f"连接 qBittorrent 失败: {e}")
            self._last_conn_ok = False
            return False

    def run(self, dry_run: bool = False, stop_event=None, pause_event=None):
        """主循环(任务队列驱动): 固定 main_tick 秒执行一次
        - 弹出到期任务并执行(种子刷新/规则/种子级内置功能/校验结果轮询, 各任务有内置 interval)
        - stop_event: 置位后循环退出并落盘(UI/托盘托管模式必传; 默认 None 行为与历史一致)
        - pause_event: 置位期间完全旁观(不刷新/不执行任务, qB 自身行为不受影响),
          恢复后的首次 refresh 以增量 diff 补上暂停期间的状态变化
        - 托管模式(非 None)首连失败不退出, 按 main_tick 重试直至成功或收到停止 —— 托盘应用保持常驻;
          非托管模式首连失败直接返回(历史行为)
        """
        self._pause_event = pause_event
        logger.info(f"启动 qB 管理器: 主循环 {self.config.main_tick}s, 默认任务间隔 {self.config.interval}s")
        # 主动通知: 启用后全项目 WARNING/ERROR 日志推送平台原生通知(notify.py);
        # dry_run 判定在调用点(项目约定: dry-run 只打日志), 内部检查 enabled, 未启用返回 None
        # WEB UI: 启用后伴随启动(浏览器访问, 辅种管理/设置); 密钥随机生成并持久化
        if not dry_run and self.config.web.enabled:
            from .web import ensure_web_token, start_web_server

            self._web_token = ensure_web_token(self)
            self._web_handle = start_web_server(self)
        if not dry_run:
            self._notify_handler = setup_notify(self.config.notify)
        try:
            main_tick = self.config.main_tick
            while not self.connect():
                if stop_event is None or stop_event.wait(main_tick):
                    return
                logger.warning(f"连接 qBittorrent 失败, {main_tick:g}s 后重试(检查 qB 是否运行/端口是否正确)")
            self.state = self._load_state()
            # 规则加载 + 全局任务创建仅运行模式需要(--export-yaml 等只导出模式在构造后直接退出, 跳过)
            self._load_rules()
            self._create_global_tasks()

            try:
                while True:
                    if stop_event is not None and stop_event.is_set():
                        logger.info("收到停止信号, 退出主循环")
                        break
                    # WEB UI 控制命令(暂停/开始/删除/强制汇报/热重载): 主循环线程执行写操作
                    self._drain_web_commands()
                    if pause_event is not None and pause_event.is_set():
                        # 已暂停: 完全旁观; wait 保持对停止信号的即时响应
                        if stop_event is not None and stop_event.wait(main_tick):
                            logger.info("收到停止信号, 退出主循环")
                            break
                        continue
                    try:
                        self._tick(dry_run)
                        # 连接恢复检测: tick 成功即 API 可达(connect() 仅启动时调用一次,
                        # 断开后恢复只能在此翻转, 否则 UI 永远显示"qB 断开")
                        if self._last_conn_ok is False:
                            self._last_conn_ok = True
                            logger.info("已重新连接 qBittorrent")
                    except AutoQbError:
                        raise  # 致命错误(配置/qB 兼容)穿透到 CLI 干净退出, 不落入"主循环异常"继续跑
                    except APIConnectionError as e:
                        # 连接失败节流: 仅状态转换时记录一次, 断开期间静默(qB 宕机时不刷屏);
                        # 断开期间自动重建连接(qB 重启/网络恢复后下一 tick 自动接上)
                        if self._last_conn_ok is not False:
                            logger.error(f"连接 qBittorrent 失败: {e}")
                            self._last_conn_ok = False
                        self.client = None
                        self.connect()
                    except Exception as e:
                        logger.error(f"主循环异常: {e}", exc_info=True)
                    if stop_event is not None and stop_event.wait(main_tick):
                        logger.info("收到停止信号, 退出主循环")
                        break
            except KeyboardInterrupt:
                logger.info("停止")
        finally:
            if self._web_handle is not None:
                self._web_handle.stop()
            if not dry_run:
                self.save_state()
            if self._lock is not None:
                self._lock.release()

    def status_snapshot(self) -> dict:
        """运行状态只读快照(UI 线程轮询用): 全部为基本类型, 不暴露内部可变对象"""
        return {
            "torrents": len(self.store.by_hash),
            "connected": self._last_conn_ok,  # None=连接中/未知, True=已连接, False=已断开
            "paused": self._pause_event is not None and self._pause_event.is_set(),
        }

    def _drain_web_commands(self):
        """消费 WEB UI 控制命令(Web 线程投递, 主循环线程执行写操作——单一写者约束保持)"""
        try:
            while True:
                cmd, payload = self.web_commands.get_nowait()
                try:
                    {
                        "pause_group": self._cmd_pause_group,
                        "resume_group": self._cmd_resume_group,
                        "reannounce_group": self._cmd_reannounce_group,
                        "delete_group": self._cmd_delete_group,
                        "pause_torrent": self._cmd_pause_torrent,
                        "resume_torrent": self._cmd_resume_torrent,
                        "reannounce_torrent": self._cmd_reannounce_torrent,
                        "delete_torrent": self._cmd_delete_torrent,
                        "reload_config": self._cmd_reload_config,
                        "build_search_index": self._cmd_build_search_index,
                    }[cmd](**payload)
                except KeyError as e:
                    logger.warning(f"WEB UI 未知命令: {e}")
                except Exception as e:
                    logger.error(f"WEB UI 命令执行失败: {cmd}: {e}", exc_info=True)
        except queue.Empty:
            pass

    @staticmethod
    def _state_kind(rec: TorrentRecord) -> str:
        """状态语义分类(前端着色): 错误红/校验蓝/下载蓝/做种绿/暂停灰

        注意 is_stopped 须先于 is_downloading/is_uploading 判定: 暂停的种子
        (stoppedDL/stoppedUP)同时命中下载/做种类别, 暂停态优先展示。
        """
        e = rec.state_enum
        if e.is_errored:
            return "error"
        if e.is_checking:
            return "checking"
        if e.is_stopped:
            return "paused"
        if e.is_downloading:
            return "downloading"
        if e.is_uploading:
            return "seeding"
        return "other"

    def _build_group_view(self) -> List[dict]:
        """从 store 分组索引组装分组视图快照(主循环每 tick 重建, Web 线程只读引用)"""
        from . import utils as _utils

        view = []
        for key, members in self.store.groups.items():
            recs = [self.store.by_hash[h] for h in members if h in self.store.by_hash]
            if not recs:
                continue
            members_view = [
                {
                    "hash": r.hash,
                    "site": r.tracker_name,
                    "state": r.state,
                    "kind": self._state_kind(r),
                    "dlspeed": r.dlspeed,
                    "upspeed": r.upspeed,
                    "uploaded": r.uploaded,
                    "size": r.size,
                    "progress": round(r.progress, 4),
                    "seeding_time": r.seeding_time,
                    "ratio": round(r.ratio, 3),
                } for r in recs
            ]
            view.append(
                {
                    "key": _utils.encode_group_key(key),
                    "name": recs[0].name,
                    "count": len(recs),
                    "dlspeed": sum(m["dlspeed"] for m in members_view),
                    "upspeed": sum(m["upspeed"] for m in members_view),
                    "uploaded": sum(m["uploaded"] for m in members_view),
                    "size": sum(m["size"] for m in members_view),
                    "members": members_view,
                }
            )
        return view

    def ensure_group_view(self) -> List[dict]:
        """WEB 线程调用: 确保分组视图最新——过期则立即重建(Web 请求触发), 否则直接返回当前引用。
        与主循环惰性组装配合: 主循环只在 Web 活跃且脏时重建, 这里兜底保证每次请求都拿到最新。"""
        if self._group_view_dirty:
            self._group_view = self._build_group_view()
            self._group_view_dirty = False
        return self._group_view

    def _build_search_index(self) -> None:
        """主循环线程调用: 增量构建搜索索引(hash -> {name, files[文件名]}), 单次限流拉取。

        **原子交换契约**: 每轮在**新字典**上重组(消失的种子不进新字典即淘汰), 完成后整体替换
        `_search_index` 引用 —— 绝不就地增删旧字典, 否则 Web 线程正在迭代时会抛
        "dictionary changed size during iteration"。已建条目只刷新名称(值替换不改结构, 并发只读安全),
        新种子拉取文件列表(rec.files 惰性拉取 + 记录 _files 跨 tick 缓存, 只在主循环线程), 单条失败
        跳过(记空文件列表)不阻塞整体。
        限流: 单次最多拉取 SEARCH_INDEX_BUILD_BUDGET 条, 未拉完保持 _search_index_dirty=True,
        由后续调用(下一 tick 推进 / 前端据 building 重查投递)续建 —— 避免首轮 N 次 API 长时间阻塞主循环。
        """
        if self.client is None:
            # qB 断开中: 无文件 API 可用, 保持脏待连接恢复后重建(不能把空文件列表当成"已建完")
            self._search_index_dirty = True
            return
        prev = self._search_index if self._search_index is not None else {}
        idx: dict = {}
        budget = SEARCH_INDEX_BUILD_BUDGET
        for h, rec in self.store.by_hash.items():
            entry = prev.get(h)
            if entry is not None:
                entry["name"] = rec.name
            elif budget > 0:
                budget -= 1
                try:
                    files = [f.name for f in rec.files(self.client)]
                except Exception:
                    files = []
                entry = {"name": rec.name, "files": files}
            else:
                # 预算用尽: 剩余种子本轮不进新字典(下次调用续建), 保持脏
                self._search_index = idx
                self._search_index_dirty = True
                return
            idx[h] = entry
        self._search_index = idx
        self._search_index_dirty = False

    def _cmd_build_search_index(self):
        """WEB UI 命令: 构建搜索索引(Web 线程检测到索引脏后投递, 主循环线程执行)。

        限流构建可能需多轮: 仅在全部拉取完成(不再脏)时记录完成日志, 避免分批刷屏。
        """
        self._build_search_index()
        if not self._search_index_dirty:
            logger.info(f"WEB UI | 搜索索引已构建: {len(self._search_index)} 个种子")

    def search_torrents(self, q: str) -> dict:
        """WEB 线程调用: 按 q(种子名 + 文件列表)搜索种子。

        种子名匹配即时遍历 store.by_hash(无 qB API); 文件列表匹配依赖 _search_index 缓存。
        返回 {"results": [..], "building": bool}——building 为 True 表示文件索引已过期/缺失,
        已投递构建命令, 前端应稍后重查以获取完整文件匹配结果。
        结果项含完整明细字段(与分组成员视图对齐): hash/name/site/kind/dlspeed/upspeed/
        uploaded/size/progress/seeding_time/ratio/by, 供前端完整展示命中种子信息。
        """
        def _view(rec, by):
            return {
                "hash": rec.hash,
                "name": rec.name,
                "site": rec.tracker_name,
                "kind": self._state_kind(rec),
                "dlspeed": rec.dlspeed,
                "upspeed": rec.upspeed,
                "uploaded": rec.uploaded,
                "size": rec.size,
                "progress": round(rec.progress, 4),
                "seeding_time": rec.seeding_time,
                "ratio": round(rec.ratio, 3),
                "by": by,
            }

        q = (q or "").strip().lower()
        if not q:
            return {"results": [], "building": False}
        results = []
        seen = set()
        # 种子名匹配(即时)
        for h, rec in self.store.by_hash.items():
            if q in rec.name.lower():
                seen.add(h)
                results.append(_view(rec, "name"))
        # 文件列表匹配(依赖缓存索引)
        idx = self._search_index
        if idx is not None:
            for h, entry in idx.items():
                if h in seen:
                    continue
                if any(q in fn.lower() for fn in entry["files"]):
                    rec = self.store.by_hash.get(h)
                    if rec is None:
                        continue
                    results.append(_view(rec, "file"))
        building = self._search_index_dirty
        if building:
            self.web_commands.put(("build_search_index", {}))
        return {"results": results, "building": building}

    def touch_web_client(self) -> None:
        """WEB 请求心跳: 刷新 _web_last_seen, 让主循环在 Web 活跃窗口内持续重建分组视图。"""
        self._web_last_seen = time.time()

    def _group_hashes(self, key: tuple) -> List[str]:
        return [h for h in self.store.groups.get(key, []) if h in self.store.by_hash]

    def _cmd_pause_group(self, key: tuple):
        hashes = self._group_hashes(key)
        if hashes:
            self.api.torrents_pause(torrent_hashes=hashes)
            logger.info(f"WEB UI | 暂停整组({len(hashes)}个种子)")

    def _cmd_resume_group(self, key: tuple):
        hashes = self._group_hashes(key)
        if hashes:
            self.api.torrents_resume(torrent_hashes=hashes)
            logger.info(f"WEB UI | 开始整组({len(hashes)}个种子)")

    def _cmd_reannounce_group(self, key: tuple):
        hashes = self._group_hashes(key)
        if hashes:
            self.api.torrents_reannounce(torrent_hashes=hashes)
            logger.warning(f"WEB UI | 强制汇报整组({len(hashes)}个种子)")

    def _cmd_delete_group(self, key: tuple, delete_files: bool = False):
        hashes = self._group_hashes(key)
        if hashes:
            self.api.torrents_delete(torrent_hashes=hashes, delete_files=delete_files)
            logger.warning(f"WEB UI | 删除整组({len(hashes)}个种子, delete_files={delete_files})")

    # ---------- 单种子命令(WEB 明细行右键) ----------

    def _cmd_pause_torrent(self, hash: str):
        if self.store.get(hash) is not None:
            self.api.torrents_pause(torrent_hashes=[hash])
            logger.info(f"WEB UI | 暂停种子 {hash[:8]}")

    def _cmd_resume_torrent(self, hash: str):
        if self.store.get(hash) is not None:
            self.api.torrents_resume(torrent_hashes=[hash])
            logger.info(f"WEB UI | 开始种子 {hash[:8]}")

    def _cmd_reannounce_torrent(self, hash: str):
        if self.store.get(hash) is not None:
            self.api.torrents_reannounce(torrent_hashes=[hash])
            logger.warning(f"WEB UI | 强制汇报种子 {hash[:8]}")

    def _cmd_delete_torrent(self, hash: str, delete_files: bool = False):
        if self.store.get(hash) is not None:
            self.api.torrents_delete(torrent_hashes=[hash], delete_files=delete_files)
            logger.warning(f"WEB UI | 删除种子 {hash[:8]}(delete_files={delete_files})")

    def _cmd_reload_config(self, config: Config):
        self.apply_new_config(config)

    def apply_new_config(self, config: Config) -> dict:
        """应用新配置(热重载, 主循环线程经命令队列调用): 按变更影响分级执行

        - L0 即时生效(仅替换 Config 对象): main_tick/max_tasks_per_tick/remove_similar_tags/
          skip_checking_tag/grouping.*/add_episode_tags.*/trackers.X.tags|remove_tags|remove_similar_tags|
          limits|hr.*(运行时动态读取, 数据/任务/分组全保留)
        - L1 轻量应用: logging 重挂 / 通知 handler 重挂 / qbittorrent 重连 / web 服务器重启
        - L2 结构重建: 重建任务队列与规则 + 全部记录重匹配 tracker(保留 store 记录/分组/执行历史)
        - R(state_file/data_dir 变更): 拒绝热应用, 返回 restart_required 提示重启进程
        """
        from .config.impact import diff_config_impacts

        changes = diff_config_impacts(self.config, config)
        restart_required = [c.path for c in changes if c.level == "R"]
        if restart_required:
            logger.warning(f"以下配置需重启进程才能生效: {restart_required}")
        levels = sorted({c.level for c in changes if c.level != "R"})
        # L0: 替换配置对象(动态读取项即刻生效)
        self.config = config
        if "L1" in levels:
            self._setup_logging()
            if self._notify_handler is not None:
                logging.getLogger("auto_qb").removeHandler(self._notify_handler)
                self._notify_handler = None
            self._notify_handler = setup_notify(config.notify, force=True)
            self.client = None
            self._last_conn_ok = None
            self.connect()
            if self._web_handle is not None:
                self._web_handle.stop()
                from .web import start_web_server

                self._web_handle = start_web_server(self)
        if "L2" in levels:
            logger.warning("应用结构级配置变更: 重建任务队列/规则, 全部记录重匹配 tracker")
            self.task_queue = TaskQueue()
            self.store.reset_runtime()
            self.state = self._load_state()
            self._load_rules()
            self._create_global_tasks()
            self._suppress_events = True
            self.client = None
            self._last_conn_ok = None
            self.connect()
        logger.warning(
            f"配置热重载完成: 级别 {levels or ['L0']}, 变更 {len(changes)} 项" +
            (f", 需重启进程: {restart_required}" if restart_required else "")
        )
        return {"applied": True, "levels": levels, "changes": len(changes), "restart_required": restart_required}

    def _tick(self, dry_run: bool):
        """单次 tick: 1) 刷新快照 2) 执行到期任务(执行与收尾统一由 TaskQueue.run_due 管理)"""
        now = time.time()

        self._refresh_torrents(dry_run)

        self.task_queue.run_due(dry_run, now=now, max_tasks=self.config.max_tasks_per_tick)

        if self.config.grouping.enabled:
            # WEB UI: 分组视图快照——惰性组装。仅当 Web 客户端活跃(_web_last_seen 距今 < WEB_VIEW_TTL)
            # 且快照已过期(_group_view_dirty)时才重建, 否则主循环不空转; 关闭网页后 CPU 回落。
            if self._group_view_dirty and (time.time() - self._web_last_seen) < WEB_VIEW_TTL:
                self._group_view = self._build_group_view()
                self._group_view_dirty = False

        # WEB UI: 搜索索引限流构建——同样仅 Web 活跃时推进(每 tick 一批, 直至不再脏);
        # 关闭网页后停止推进, 避免无谓的文件 API 调用
        if self._search_index_dirty and (time.time() - self._web_last_seen) < WEB_VIEW_TTL:
            self._build_search_index()

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
        # 全局限速曲线(Traffic Monitor): 读 dat -> 聚合 -> 查档 -> 写 qB 全局速度限制
        gslc = self.config.global_speed_limit_curve
        if gslc is not None:
            tasks.append(
                Task(
                    "internal",
                    "speed_limit_curve",
                    interval=gslc.interval or self.config.interval,  # 缺省回退主 interval
                    handler=self._handle_speed_limit_curve,
                )
            )
        if tasks:
            self.task_queue.add_tasks(tasks)
            logger.info(f"创建全局任务 {len(tasks)} 个: {[t.log_tag for t in tasks]}")

    # ---------- 种子级任务 ----------

    def _validate_torrent_schema(self, tors) -> None:
        """版本兼容 fail-fast: 首次拉到非空种子信息时校验必需字段(qB 版本漂移早暴露)。

        样本取列表中首个非 dict 对象(真实 API 恒为 TorrentDictionary; 测试注入的 dict
        不作样本); 通过后置 _schema_validated 不再重复校验(qB 版本运行期不变);
        空 qB / 全 dict 时本轮跳过, 下次非空再验。缺失抛 QbCompatError -> CLI 干净退出。
        """
        if self._schema_validated:
            return
        sample = next((t for t in tors if not isinstance(t, dict)), None)
        if sample is None:
            return
        missing = missing_torrent_fields(sample)
        if missing:
            raise QbCompatError(f"qBittorrent torrent info 缺少字段: {missing}; 请检查 qBittorrent 版本兼容性")
        self._schema_validated = True

    def _refresh_torrents(self, dry_run: bool = False):
        """种子列表刷新: 拉全量 -> store.refresh 增删检测 -> 新种子创建内置+规则任务并归组,
        删除种子移除任务, 分组事件(新增归组+大小一致性/删除/上传转暂停)检测到即立即处理,
        更新状态快照。本 tick 刷新后所有读取操作都只通过 store 接口, 不再重复拉取 API。"""
        self._missing_scanned_keys.clear()  # 缺文件扫描去重按轮重置
        tors = self.api.torrents_info()
        self._validate_torrent_schema(tors)
        prev_records = dict(self.store.by_hash)  # 删除前快照副本(供 on_torrent_deleted 只读动作)
        added, removed = self.store.refresh(tors)
        # 种子增删/状态可能变化: 置分组视图过期, 供 _tick 惰性重建(仅 Web 活跃时)
        self._group_view_dirty = True
        # 种子集变化(新增/删除) -> 搜索索引需反映新/删种子, 标记脏(Web 搜索时重建)
        if added or removed:
            self._search_index_dirty = True
        # 删除种子的删除前快照: 种子已从 store 移除后, ctx.torrent 回退此副本供只读动作留档
        removed_snapshots = {h: prev_records[h] for h in removed if h in prev_records}

        if self.config.grouping.enabled:
            # 组内种子由上传(做种)转暂停 -> 立即触发缺文件扫描(用上一轮状态快照, 不等下一轮)。
            # 必须在本轮任何自有动作之前观测: 新增归组的大小一致性停种经快照同步会当场改写
            # by_hash 状态, 放在后面会把自家停种误判为外部"上传转暂停"
            self._handle_state_transitions(dry_run)

        # 事件分派(on_torrent_deleted / on_torrent_state_enum_changed): 在自有动作之前、
        # 状态快照更新之前同步即时执行(新增种子本轮不触发状态变化; added 事件在下方匹配后触发);
        # 热重载后首轮抑制(全量重建的 added 重放保护), 一轮后恢复
        if not self._suppress_events:
            self._dispatch_events([], removed, dry_run, removed_snapshots=removed_snapshots, tors=tors)

        if added:
            logger.info(f"检测到新增种子 {len(added)} 个, 创建内置+规则任务")
            # 先为所有新增种子匹配 tracker 配置(事件分派与后续自有动作都需要)
            matched_added = []
            for h in added:
                torrent = self.store.get(h)
                if torrent is None:
                    continue
                if torrent.tracker_conf is None:
                    torrent.tracker_conf = self._match_tracker_conf(torrent)
                if not torrent.tracker_conf:
                    try:
                        trackers_info = torrent.trackers_info(self.client)
                        all_domains = utils.extract_tracker_hostnames(trackers_info)
                    except Exception:
                        all_domains = []
                    logger.warning(f"种子[{h[:8]}] | 未匹配 tracker 配置, 域名: {', '.join(all_domains)}")
                    continue  # 未匹配tracker配置, 直接跳过
                matched_added.append(h)
            # 事件分派(on_torrent_added): 新增种子已匹配 tracker 配置, 同步触发事件规则
            if not self._suppress_events:
                self._dispatch_events(matched_added, [], dry_run, removed_snapshots=None, tors=None)
            # 自有动作: 内置任务/限速/创建任务/归组/集数标签
            for h in matched_added:
                torrent = self.store.get(h)
                tracker_conf = torrent.tracker_conf
                # 立即运行一次内置任务
                self._handle_maintenance(torrent, dry_run)
                # tracker单种限速
                self._apply_speed_limit(torrent, tracker_conf, dry_run)
                # 创建种子级任务: 内置 maintenance + 所有符合条件的规则任务
                self._create_torrent_tasks(h)
                # 增量归组: 新种子(含程序启动首轮的现有种子)按文件列表自动归组, 归组时检查大小一致性
                if self.config.grouping.enabled:
                    self._assign_new_torrent(h, dry_run)
                # 自动添加集数标签(仅种子添加时触发): 名称不含集数标记时从文件列表解析, 如 E1-5
                if self.config.add_episode_tags.enabled:
                    self._add_episode_tags(torrent, dry_run)

        if removed:
            # 已删种子的任务不显式清理: 由 run_due 到期执行时 handler 检测种子缺失自然消亡
            logger.info(f"检测到删除种子 {len(removed)} 个")
            # 组内种子被删除 -> 立即触发缺文件扫描(剩余种子可能文件丢失), 不等下一轮
            if self.config.grouping.enabled:
                self._handle_removed_torrents(removed, dry_run)

        if self.config.grouping.enabled:
            # 保存路径变化重归组(文件列表变化会走新增种子重新归组)
            self._handle_save_path_changes(dry_run)
            # 下载冲突检查(每轮): 同组多个同时下载/已完成与下载中并存 -> 警告+整组暂停
            self._check_download_conflicts(dry_run)

        # 更新状态快照(仅本轮可见种子; 存 state_enum 枚举对象, 与 qB 版本无关; 新增种子本轮不视为状态变化)
        # 事件分派(on_torrent_state_enum_changed)依赖此上一轮快照对比, 故不局限于 grouping 启用时
        self.store.update_state_snapshot(tors)

        # 上传量快照(按自然日/周/月, 周期切换时重建基线) — 幂等
        self.begin_round(list(self.store.by_hash.values()))
        self._suppress_events = False  # 事件抑制仅覆盖热重载后的首轮全量重建

    def _create_torrent_tasks(self, hash: str):
        """
        为新增种子创建任务: 内置 maintenance + 所有符合条件的规则任务

        缺文件检查统一由分组事件驱动承担(_refresh_torrents 检测到删除/状态变化/
        保存路径变化立即触发组内扫描), 不再创建逐种子 missing_files 任务。
        每个任务有内置 interval(规则任务用规则自身 interval), 规则任务加入队列即立即到期(下一 tick 执行)。
        内置种子任务加入队列后下一个interval到期。
        """

        torrent = self.store.get(hash)
        if not torrent:
            return

        # 创建内置种子任务
        self.task_queue.add_task(
            Task(
                "internal",
                "maintenance",
                hash=hash,
                store=self.store,
                interval=self.config.interval,
                handler=self._handle_maintenance_task_interface
            ),
            time.time() + self.config.interval
        )

        # 创建种子规则任务(仅 interval 规则建周期任务; on_* 事件规则不建, 由事件分派即时处理)
        tasks = []
        for rule in self._rules_for_torrent(torrent):
            task = self._create_rule_task(rule, hash)
            if task is not None:
                tasks.append(task)
        self.task_queue.add_tasks(tasks)

    def _handle_maintenance_task_interface(self, task: Task, dry_run: bool) -> bool:
        return self._handle_maintenance(task.torrent, dry_run)

    def _handle_maintenance(self, torrent: TorrentRecord, dry_run: bool) -> bool:
        """内置种子级任务: 添加/删除/相似标签 + HR 标签分类"""
        if torrent is None:
            return FINISHED

        tracker_conf = torrent.tracker_conf

        handled = False
        handled |= self._add_tags(torrent, tracker_conf.tags, dry_run)
        handled |= self._remove_tags(torrent, tracker_conf.remove_tags, dry_run)
        if tracker_conf.remove_similar_tags:  # 站点覆盖全局后的值
            handled |= self._remove_similar_tags(torrent, tracker_conf.tags, dry_run)
        if tracker_conf.hr:  # 站点合并全局默认后的 HR 设置
            handled |= self._add_hr_tag_or_category(torrent, dry_run)
        # if handled:
        #     self._log_torrent_details(torrent, tracker_conf)
        #     logger.info(f"--------------------------------------------------------------------------")
        return REQUEUE

    def export_torrents_info(self, path):
        """导出种子信息, 用于debug"""
        torrents = self.client.torrents_info()
        with open(path, "w") as f:
            for tor in torrents:
                f.write(f"{tor}\n\n")
