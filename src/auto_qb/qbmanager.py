"""QbManager: qBittorrent 主管理类

任务队列统一协调: 种子刷新 / 规则 / 种子级内置功能 / 异步校验 全部是带内置 interval 的任务。
检测到新增种子时, 自动为该种子创建所有符合条件的 rule 任务(仅 tracker 显式引用的规则; 站点未配置
rules 引用时该站点种子不绑定任何规则 —— 不会回退为"执行全部启用规则")。

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
import threading
import time
from typing import List, Optional
from urllib.parse import urlparse

from qbittorrentapi import APIConnectionError, Client

from .config import Config, QbittorrentConfig, WebConfig, load_config
from .errors import AutoQbError
from .locking import SingleInstanceLock
from .mixins import CheckingMixin, GroupingMixin, RuleEngineMixin, SpeedCurveMixin, TagsMixin, TrackerMixin
from .notify import NotifyHandler, setup_notify
from .qbapi import QbApi
from .rules import Rule
from .taskqueue import FINISHED, REQUEUE, Task, TaskQueue
from .torrents import (
    QbCompatError,
    TorrentRecord,
    TorrentStore,
    missing_torrent_fields,
    view_field_value,
)
from . import utils
from .logging import setup_logging

logger = logging.getLogger(__name__)

WEB_VIEW_TTL = 10.0  # Web 客户端活跃窗口: 超时无请求则主循环跳过分组视图组装(惰性)
SEARCH_INDEX_BUILD_BUDGET = 500  # 搜索索引单次构建最多拉取的文件列表数(限流, 避免首轮 N 次 qB API 阻塞主循环)

# 强制汇报的 tracker 确认窗口: reannounce 后 qB 立即重发 announce, 私站响应通常 1~10s;
# 留足慢站点余量取 30s(主循环 main_tick=2s -> 约 15 轮确认机会), 超时仍未确认即判失败。
REANNOUNCE_CONFIRM_TIMEOUT = 30.0
# 本地 qB 地址(关闭 requests trust_env: 环境代理与 ~/.netrc 解析对本机连接无意义)
_LOCAL_HOSTS = frozenset(("127.0.0.1", "localhost", "::1"))


def _throttle(stop_event: Optional[threading.Event], main_tick: float) -> bool:
    """主循环节流: 阻塞 main_tick 秒, 返回 True 表示收到停止信号

    托管模式(tray/UI 传入 stop_event)走 Event.wait, 保持对停止信号的即时响应;
    非托管模式(CLI 默认无 stop_event)走 time.sleep —— **必须真实睡眠**。

    ❗回归背景(2026-09-14): 主循环曾写成 `if stop_event is not None and stop_event.wait(main_tick)`,
    非托管模式下被 `and` 短路 -> 完全不阻塞 -> 空转。由 begin_round + update_state_snapshot 的
    每 tick 固定成本反推约 2800 tick/s, 是 main_tick=2s 设计值的约 5500 倍: CPU 打满, 且把
    sync/maindata 请求量同步放大 5500 倍(连带 requests 每次请求的 netrc/代理/注册表解析一并放大)。
    任何"简化 stop_event 判断"的改动都必须保持本函数语义(非托管 -> time.sleep)。
    """
    if stop_event is None:
        time.sleep(main_tick)
        return False
    return stop_event.wait(main_tick)


def _is_local_qb(qb: QbittorrentConfig) -> bool:
    """qB 地址是否指向本机(取 base_url 解析后的 hostname, 兼容带端口/带协议写法)"""
    return urlparse(qb.base_url).hostname in _LOCAL_HOSTS


class LocalQbClient(Client):
    """本地 qB 客户端: 每个(重)建的 requests Session 都强制关闭 trust_env

    背景: 打开 trust_env 时 requests 每次请求都要解析环境代理(get_environ_proxies ->
    proxy_bypass_registry 读注册表)与 ~/.netrc(get_netrc_auth 走 expanduser + os.path.exists),
    对 127.0.0.1/localhost 连接毫无意义(实测单请求 0.276ms -> 0.043ms)。

    ❗为什么不"连上后给 client._session.trust_env 赋 False": 库的 `Request._session` 是**只读
    property**(qbittorrentapi/request.py), 且库在 `build_base_url()`(首次请求)与
    `_initialize_context()`(登录过期/qB 重启)中都会调用 `_trigger_session_initialization()`
    **丢弃当前 Session 并在下次访问时重建** —— 旧实现赋的值在第一次真实请求时即被清除
    (静默失效, 从未生效过; 实测: 赋值后触发重建 -> trust_env 回到 True 且对象已换)。
    此处改为覆盖 property, 在返回前强制关闭, 因此对任何时刻新建的 Session 都生效。

    仅本地地址使用本子类, 远程/域名连接保留 requests 默认行为(企业代理/~/.netrc 可能真实需要)。
    """
    @property
    def _session(self):
        session = super()._session
        session.trust_env = False
        return session


def _new_client(qb: QbittorrentConfig) -> Client:
    """按配置构造 qB 客户端(本地地址用关闭 trust_env 的 LocalQbClient)"""
    cls = LocalQbClient if _is_local_qb(qb) else Client
    return cls(host=qb.base_url, username=qb.username, password=qb.password)


class QbManager(RuleEngineMixin, TagsMixin, CheckingMixin, GroupingMixin, TrackerMixin, SpeedCurveMixin):
    def __init__(self, config_path: str, config: Config = None, no_lock: bool = False):
        self.config_path = config_path
        self.config = config or load_config(config_path)
        self._setup_logging()
        # 种子信息数据层: 增量同步 + 惰性缓存 + 分组索引 + 全局标签/分类缓存
        # 每 main_tick 只拉变化部分(sync/maindata)后, 本 tick 内所有读取操作都只通过 self.store 接口访问
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
        # WEB UI: 命令执行结果回执(cmd_id -> {status, error, ts})。主循环线程唯一写者,
        # Web 线程经 /api/cmd/{id} 只读。多数命令执行完立即写; reannounce 的回执由
        # tracker 确认跟踪器(_reannounce_pending)在后续 tick 写入。
        self._web_results: dict = {}
        # WEB UI: 强制汇报确认跟踪(cmd_id -> {deadline, items: {hash: {done, ok, err, baseline}}})。
        # 每 tick 检查一次: 读 torrents/trackers 判定 "status 变 working / next_announce 被重置"。
        self._reannounce_pending: dict = {}
        # WEB UI: 分组视图快照(主循环每 tick 重建并原子替换, Web 线程只读)
        self._group_view: List[dict] = []
        # WEB UI: 分组视图版本号(等价 qB 的 rid): 每次重建自增, Web 端按版本跳过整表替换。
        # 以进程启动时间播种: 进程重启后版本号不会回落到旧客户端已持有的值(否则前端会误判
        # "无更新"而一直展示重启前的旧列表)。
        self._group_view_ver: int = int(time.time())
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
        # WEB UI: 限速/流量只读快照(限速曲线任务每次执行后**整体替换**, Web 线程只读)。
        # 含今日/多周期累计流量与"命中(曲线目标)/实际(qB 当前)"限速对照, 供顶栏 pill 显示。
        # 未启用曲线功能时保持 state="disabled"(前端据此不渲染流量/限速 pill)。
        self._traffic_view: dict = {"state": "disabled", "periods": [], "limit": {}}
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
        # 重连/换客户端 -> 旧 rid 失效: 重置同步基线, 下轮强制全量重建
        self.store.reset_sync()

    def _setup_logging(self):
        logging_conf = self.config.logging
        setup_logging(logging_conf.file, logging_conf.level, logging_conf.max_bytes, logging_conf.format)

    def connect(self) -> bool:
        """连接 qBittorrent(本地地址经 _new_client 使用关闭 trust_env 的 LocalQbClient)"""
        try:
            self.client = _new_client(self.config.qbittorrent)
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

    def run(
        self,
        dry_run: bool = False,
        stop_event: Optional[threading.Event] = None,
        pause_event: Optional[threading.Event] = None,
    ):
        """主循环(任务队列驱动): 每轮执行后经 _throttle 阻塞 main_tick 秒
        - 弹出到期任务并执行(种子刷新/规则/种子级内置功能/校验结果轮询, 各任务有内置 interval)
        - stop_event: 置位后循环退出并落盘(UI/托盘托管模式必传; 传 None 时非托管,
          节流退化为 time.sleep —— 见 _throttle 的回归说明)
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
            from .web import start_web_server

            # 密钥由 start_web_server 内部确定(显式配置或随机生成持久化到 data_dir/web.token)
            self._web_handle = start_web_server(self)
        if not dry_run:
            self._notify_handler = setup_notify(self.config.notify)
        try:
            main_tick = self.config.main_tick
            # 首连失败: 托管模式按 main_tick 重试直至成功/停止; 非托管模式直接返回(历史行为,
            # 与主循环节流的 _throttle 语义不同 —— 此处不可替换为 _throttle)
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
                    self._check_reannounce_pending()
                    if pause_event is not None and pause_event.is_set():
                        # 已暂停: 完全旁观; 节流保持对停止信号的即时响应
                        if _throttle(stop_event, main_tick):
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
                    if _throttle(stop_event, main_tick):
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
        """消费 WEB UI 控制命令(Web 线程投递, 主循环线程执行写操作——单一写者约束保持)

        命令带 cmd_id: 执行完立即写回执(_web_results), 供前端 /api/cmd/{id} 轮询执行结果。
        reannounce 例外: handler 只发指令并登记确认跟踪(_reannounce_pending), 回执由
        _check_reannounce_pending 在 tracker 确认后写入 —— "已发送"不等于"汇报成功"。
        """
        handlers = {
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
        }
        try:
            while True:
                cmd, payload = self.web_commands.get_nowait()
                cmd_id = str(payload.get("cmd_id") or "")
                args = {k: v for k, v in payload.items() if k != "cmd_id"}
                try:
                    if cmd_id and cmd in ("reannounce_group", "reannounce_torrent"):
                        # handler 只发指令并登记确认跟踪; 回执由 _check_reannounce_pending 在
                        # tracker 确认后写入 —— "已发送"不等于"汇报成功", 故此处不写 ok
                        handlers[cmd](cmd_id=cmd_id, **args)
                    else:
                        handlers[cmd](**args)
                        if cmd_id:
                            self._set_web_result(cmd_id, "ok")
                except KeyError as e:
                    logger.warning(f"WEB UI 未知命令: {e}")
                    if cmd_id:
                        self._set_web_result(cmd_id, "error", f"未知命令: {e}")
                except Exception as e:
                    logger.error(f"WEB UI 命令执行失败: {cmd}: {e}", exc_info=True)
                    if cmd_id:
                        self._set_web_result(cmd_id, "error", str(e))
        except queue.Empty:
            pass

    def _set_web_result(self, cmd_id: str, status: str, error: str = "") -> None:
        """写入命令执行结果回执(主循环线程唯一写者); 顺手清理 2 分钟前的旧回执防无限增长"""
        now = time.time()
        if len(self._web_results) > 64:
            self._web_results = {k: v for k, v in self._web_results.items() if now - v.get("ts", 0) < 120}
        self._web_results[cmd_id] = {"status": status, "error": error, "ts": now}

    def _trackers_baseline(self, hashes: List[str]) -> dict:
        """读取汇报前各种子的 tracker 状态基线: {hash: {url: (status, next_announce)}}

        排除 DHT/PeX/LSD 虚拟 tracker(url 以 **/[DHT]/[PeX]/[LSD] 开头, 它们不走 announce)。
        qB 断连等读取失败时异常上抛, 由命令分发层写 error 回执。
        """
        baseline = {}
        for h in hashes:
            trackers = self.client.torrents_trackers(h) or []
            real = {}
            for t in trackers:
                url = str(t.get("url") or "")
                if url.startswith(("**", "[DHT]", "[PeX]", "[LSD]")):
                    continue
                real[url] = (t.get("status"), t.get("next_announce"))
            baseline[h] = real
        return baseline

    @staticmethod
    def _confirm_reannounce_result(trackers: list, baseline: dict) -> Optional[bool]:
        """判定单个种子汇报确认结果: True=已确认成功 / False=已确认失败 / None=仍在进行

        逐 tracker 检查, 任一命中即结论:
        - status == 3 (updating)                    -> qB 正在汇报, 视为成功
        - next_announce 比基线提前(>60 单位, 秒/毫秒通用) -> next_announce 被重置, 视为成功
        - status 从非 working 变为 2 (working)      -> 视为成功
        - status == 4 (not working) 且带错误消息    -> tracker 拒绝, 视为失败
        """
        for t in trackers:
            url = str(t.get("url") or "")
            if url.startswith(("**", "[DHT]", "[PeX]", "[LSD]")):
                continue
            b_status, b_na = baseline.get(url, (None, None))
            status = t.get("status")
            na = t.get("next_announce")
            if status == 3:
                return True
            if na is not None and b_na is not None and na < b_na - 60:
                return True
            if status == 2 and b_status is not None and b_status != 2:
                return True
            if status == 4 and (t.get("msg") or ""):
                return False
        return None

    def _check_reannounce_pending(self):
        """每 tick 检查在途的强制汇报确认; 某 cmd_id 全部种子出结论后聚合写回执"""
        if not self._reannounce_pending:
            return
        now = time.time()
        finished = []
        for cmd_id, entry in self._reannounce_pending.items():
            for h, it in entry["items"].items():
                if it["done"]:
                    continue
                if now >= entry["deadline"]:
                    it["done"], it["ok"] = True, False
                    it["err"] = f"汇报确认超时({REANNOUNCE_CONFIRM_TIMEOUT:.0f}s 内未确认到 tracker 响应)"
                    continue
                if self.client is None:
                    continue  # qB 断连: 等恢复继续确认, 或按超时判失败
                try:
                    trackers = self.client.torrents_trackers(h) or []
                    r = self._confirm_reannounce_result(trackers, it["baseline"])
                except Exception as e:
                    it["done"], it["ok"], it["err"] = True, False, f"读取 tracker 状态失败: {e}"
                    continue
                if r is True:
                    it["done"], it["ok"] = True, True
                elif r is False:
                    it["done"], it["ok"], it["err"] = True, False, "tracker 未接受汇报(not working)"
            if all(it["done"] for it in entry["items"].values()):
                finished.append(cmd_id)
        for cmd_id in finished:
            entry = self._reannounce_pending.pop(cmd_id)
            items = list(entry["items"].values())
            fails = [it for it in items if not it["ok"]]
            if not fails:
                self._set_web_result(cmd_id, "ok")
                logger.info(f"WEB UI | 强制汇报确认成功({len(items)}个种子)")
            else:
                msg = f"{len(fails)}/{len(items)} 个种子汇报确认失败: " + "; ".join(it["err"] for it in fails[:3])
                self._set_web_result(cmd_id, "error", msg)
                logger.warning(f"WEB UI | {msg}")

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

    @staticmethod
    def _hr_view_fields(rec: TorrentRecord) -> dict:
        """该成员的 HR 展示字段(标签文本 + 要求/达成布尔), 供前端渲染 H&R 栏与对照列

        - hr_tag / hr_tag_done: 已触发未达标 / 已达标时应有的标签(供前端按文本着色)
        - hr_triggered / hr_satisfied: 是否触发 HR / 是否已达成要求
        - hr_req_time: 要求做种时长(秒) = required_seeding_time + extra_seeding_time
        - hr_req_ratio: 要求分享率(0 = 不要求)

        判定委托 TorrentRecord.check_hr_condition/check_hr_satisfied, 标签文本经
        utils.replace_vars 解析 ${required_seeding_time}, 与维护流程(打 HR 标签)完全同源 ——
        前端只做展示比较, 不得在 JS 里重算模板或阈值(否则自定义标签格式/阈值会立即失效)。
        未配置 HR 站点返回全空值(前端据此整列显示"—"), 不做 None 防御(早暴露配置匹配错误)。
        """
        from . import utils as _utils

        conf = rec.tracker_conf
        hr = conf.hr if conf is not None else None
        if hr is None:
            return {
                "hr_tag": "",
                "hr_tag_done": "",
                "hr_triggered": False,
                "hr_satisfied": False,
                "hr_req_time": 0,
                "hr_req_ratio": 0.0,
            }
        triggered = rec.check_hr_condition()
        satisfied = triggered and rec.check_hr_satisfied()
        fields = {
            "hr_tag": "",
            "hr_tag_done": "",
            "hr_triggered": triggered,
            "hr_satisfied": satisfied,
            "hr_req_time": hr.required_seeding_time + hr.extra_seeding_time,
            "hr_req_ratio": hr.required_share_ratio,
        }
        if triggered:
            if satisfied:
                fields["hr_tag_done"] = _utils.replace_vars(hr.add_tag_for_satisfied, conf)
            else:
                fields["hr_tag"] = _utils.replace_vars(hr.add_tag, conf)
        return fields

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
                    "name": r.name,
                    "site": r.tracker_name,
                    "state": r.state,
                    "kind": self._state_kind(r),
                    "dlspeed": r.dlspeed,
                    "upspeed": r.upspeed,
                    "uploaded": r.uploaded,
                    "size": r.size,
                    # 组级"共同标签/分类"与保存路径筛选器的数据来源(交集/共同值由前端计算,
                    # 后端只透出原始值, 避免每次重建做 O(成员数) 以上的集合运算)
                    "save_path": r.save_path,
                    "tags": sorted(r.tags_set),
                    "category": r.category,
                    "progress": round(r.progress, 4),
                    # 取整到分钟(与 torrents.view_field_value 的重建判定同一步长): 该字段每秒递增,
                    # 不取整会让做种中的种子每轮置脏, 惰性重建失效; 前端展示精度本就是分钟
                    "seeding_time": view_field_value("seeding_time", r.seeding_time),
                    "ratio": round(r.ratio, 3),
                    # 添加时间(unix 秒): 组级默认排序取组内最大值(见下方组级 added_on)
                    "added_on": r.added_on,
                    # HR 展示字段(标签语义色 + 要求/达成布尔): 判定与打标签流程同源, 见 _hr_view_fields
                    **self._hr_view_fields(r),
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
                    # size = **单种子**大小(同组文件列表相同, 取代表成员); total_size = 全组求和。
                    # 两者不等即说明组内大小不一致(前端据此提示风险), 而非显示重复信息
                    "size": members_view[0]["size"],
                    "total_size": sum(m["size"] for m in members_view),
                    # 组级默认排序键 = 组内**最近添加**时间(前端 sortKey=added_on 降序);
                    # 用 max 而非 min: "刚补进来的那个辅种"才是用户最关心的新条目
                    "added_on": max(m["added_on"] for m in members_view),
                    # HR 栏: 分子 = 已触发但未达标(需关注), 分母 = 已触发 HR 的成员数;
                    # 在**后端**算好计数, 前端只负责显示(与 memory-bank/pitfalls.md 的"派生值后端算"约定一致)
                    "hr_triggered": sum(1 for m in members_view if m["hr_triggered"]),
                    "hr_pending": sum(1 for m in members_view if m["hr_triggered"] and not m["hr_satisfied"]),
                    "members": members_view,
                }
            )
        return view

    def ensure_group_view(self) -> List[dict]:
        """WEB 线程调用: 确保分组视图最新——过期则立即重建(Web 请求触发), 否则直接返回当前引用。
        与主循环惰性组装配合: 主循环只在 Web 活跃且视图有变化时重建, 这里兜底保证每次请求都拿到最新。"""
        if self._group_view_dirty:
            self._group_view = self._build_group_view()
            self._group_view_ver += 1
            self._group_view_dirty = False
        return self._group_view

    def ensure_group_state(self, rid: Optional[int]) -> dict:
        """WEB 线程调用: 带版本号的合并状态(前端按 rid 跳过整表替换与重渲染)

        rid 与服务端视图版本一致时**不回传 groups**(响应体趋近于零); 不一致时回传
        全量分组数据并带上新版本号。status 体积极小(4 个标量), 无关版本恒回传,
        以保证连接状态/暂停状态/种子数变化能即时反映。
        """
        self.ensure_group_view()
        ver = self._group_view_ver
        updated = rid != ver
        state: dict = {"rid": ver, "updated": updated}
        if updated:
            state["groups"] = self._group_view
        return state

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
        uploaded/size/progress/seeding_time/ratio/save_path/tags/category/by, 供前端完整展示命中种子信息。
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
                "save_path": rec.save_path,
                "tags": sorted(rec.tags_set),
                "category": rec.category,
                "progress": round(rec.progress, 4),
                "seeding_time": rec.seeding_time,
                "ratio": round(rec.ratio, 3),
                "added_on": rec.added_on,
                # 未归组命中种子以单种子虚拟行展示, 同样需要 HR 列所需字段
                **self._hr_view_fields(rec),
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

    def _cmd_reannounce_group(self, key: tuple, cmd_id: str = ""):
        hashes = self._group_hashes(key)
        if hashes:
            self.api.torrents_reannounce(torrent_hashes=hashes)
            # 发送仅是"已下发指令"; 成功回执由 tracker 确认跟踪器在后续 tick 写入
            baseline = self._trackers_baseline(hashes)
            self._register_reannounce_pending(cmd_id, hashes, baseline)
            logger.warning(f"WEB UI | 强制汇报整组({len(hashes)}个种子), 等待 tracker 确认")

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

    def _cmd_reannounce_torrent(self, hash: str, cmd_id: str = ""):
        if self.store.get(hash) is None:
            # 种子已不存在: 无法汇报, 直接给失败回执(删除流程据此不删除)
            if cmd_id:
                self._set_web_result(cmd_id, "error", "种子不存在或已被删除")
            return
        self.api.torrents_reannounce(torrent_hashes=[hash])
        baseline = self._trackers_baseline([hash])
        self._register_reannounce_pending(cmd_id, [hash], baseline)
        logger.warning(f"WEB UI | 强制汇报种子 {hash[:8]}, 等待 tracker 确认")

    def _register_reannounce_pending(self, cmd_id: str, hashes: List[str], baseline: dict) -> None:
        """登记汇报确认跟踪: 全部种子出结论(成功/失败/超时)后聚合写该 cmd_id 的回执"""
        if not cmd_id:
            return  # 无回执需求的调用(直接构造 manager 的场景): 只发指令不跟踪
        self._reannounce_pending[cmd_id] = {
            "deadline": time.time() + REANNOUNCE_CONFIRM_TIMEOUT,
            "items": {
                h: {
                    "done": False,
                    "ok": False,
                    "err": "",
                    "baseline": baseline[h]
                }
                for h in hashes
            },
        }

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
        - L1 轻量应用: logging 重挂 / 通知 handler 重挂 / qbittorrent 重连 / web 服务器
          **仅在"监听身份"(enabled/host/port)变化时重启**(次序: 停旧并等其线程退出 -> 启新, 见 _apply_web_config)
        - L2 结构重建: 重建任务队列与规则 + 全部记录重匹配 tracker(保留 store 记录/分组/执行历史)
        - R(state_file/data_dir 变更): 拒绝热应用, 返回 restart_required 提示重启进程
        """
        from .config.impact import diff_config_impacts

        changes = diff_config_impacts(self.config, config)
        restart_required = [c.path for c in changes if c.level == "R"]
        if restart_required:
            logger.warning(f"以下配置需重启进程才能生效: {restart_required}")
        levels = sorted({c.level for c in changes if c.level != "R"})
        # L1 分支需对比新旧 web 段(替换后旧对象不可达)
        old_web = self.config.web
        # L0: 替换配置对象(动态读取项即刻生效)
        self.config = config
        # 分组视图含由配置派生的展示值(HR 标签模板如 ${required_seeding_time}, 见 _hr_view_fields),
        # 配置变了视图内容就可能变 —— 与 store 视图字段变化无关, 需显式置脏
        self._group_view_dirty = True
        if "L1" in levels:
            self._setup_logging()
            if self._notify_handler is not None:
                logging.getLogger("auto_qb").removeHandler(self._notify_handler)
                self._notify_handler = None
            self._notify_handler = setup_notify(config.notify, force=True)
            self.client = None
            self._last_conn_ok = None
            self.connect()
            self._apply_web_config(old_web)
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

    def _apply_web_config(self, old_web: WebConfig) -> None:
        """WEB 服务器热应用: 仅"监听身份"(enabled/host/port)变化才重启

        - 监听身份未变: 只同步密钥(鉴权每请求实时读 self._web_token, 无需重启 —— 否则改个
          日志级别也会把 web 服务器拆了重建, 白白放大竞态窗口)
        - 变化时: 按目标态启停; 重启必须"先停旧服务并等其线程退出"再启新服务
          (uvicorn 的 should_exit 是异步生效的, 直接重启会与新服务竞抢端口 -> WinError 10048)
        """
        from .web import ensure_web_token, start_web_server, stop_web_server

        enabled = bool(self.config.web.enabled)
        want = (enabled, self.config.web.host, self.config.web.port)
        have = (bool(old_web.enabled), old_web.host, old_web.port)
        if want == have:
            if self._web_handle is not None:
                self._web_token = ensure_web_token(self)
            return
        if self._web_handle is not None:
            stop_web_server(self._web_handle)
            self._web_handle = None
        if enabled:
            self._web_handle = start_web_server(self)
        else:
            logger.warning("WEB UI 已停止(web.enabled=false)")

    def _tick(self, dry_run: bool):
        """单次 tick: 1) 刷新快照 2) 执行到期任务(执行与收尾统一由 TaskQueue.run_due 管理)"""
        now = time.time()

        self._refresh_torrents(dry_run)

        self.task_queue.run_due(dry_run, now=now, max_tasks=self.config.max_tasks_per_tick)

        # 视图相关内容变化(store 视图字段/组成员)读取并复位, 供下方分组视图惰性重建判定
        view_changed = self.store.consume_view_changed()
        if self.config.grouping.enabled:
            # WEB UI: 分组视图快照——惰性组装。仅当 Web 客户端活跃(_web_last_seen 距今 < WEB_VIEW_TTL)
            # 且视图内容确有变化(视图字段/成员变化, 或显式置脏)时才重建, 否则主循环不空转;
            # 关闭网页后 CPU 回落。
            if view_changed:
                self._group_view_dirty = True
            if self._group_view_dirty and (time.time() - self._web_last_seen) < WEB_VIEW_TTL:
                self._group_view = self._build_group_view()
                self._group_view_ver += 1
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

    def _validate_torrent_schema(self, sample) -> None:
        """版本兼容 fail-fast: 首次拿到全量种子信息时校验必需字段(qB 版本漂移早暴露)。

        样本由 TorrentStore 在全量轮提供(`need_validate` 为真): sync 路径为 qB 原始字段
        映射(全量响应含全部必需字段), 降级路径为首个非 dict 真实种子对象(测试注入的
        plain dict 不作样本)。仅在真正有样本时校验; 增量轮的响应只含变化字段,
        校验会误报 —— 由调用方按 need_validate 闸门。
        通过后置 _schema_validated 不再重复校验(qB 版本运行期不变);
        空 qB 时样本为 None, 本轮跳过, 下次有种子再验。
        缺失抛 QbCompatError -> CLI 干净退出。
        """
        if self._schema_validated or sample is None:
            return
        missing = missing_torrent_fields(sample)
        if missing:
            raise QbCompatError(f"qBittorrent torrent info 缺少字段: {missing}; 请检查 qBittorrent 版本兼容性")
        self._schema_validated = True

    def _refresh_torrents(self, dry_run: bool = False):
        """种子列表刷新: 增量同步 -> 增删检测 -> 新种子创建内置+规则任务并归组,
        删除种子移除任务, 分组事件(新增归组+大小一致性/删除/上传转暂停)检测到即立即处理,
        更新状态快照。本 tick 刷新后所有读取操作都只通过 store 接口, 不再重复拉取 API。

        增量同步(/sync/maindata)只取自上轮 rid 起的变化(未变化种子不出现在响应中),
        故 store 只更新变化的记录; 本轮变化集(state_changed/path_changed)供分组与
        事件分派把 O(N) 全量扫描降为 O(变化数)。
        """
        self._missing_scanned_keys.clear()  # 缺文件扫描去重按轮重置
        prev_records = dict(self.store.by_hash)  # 删除前快照副本(供 on_torrent_deleted 只读动作)
        added, removed = self.store.apply_sync(self.api)
        if self.store.need_validate:
            self._validate_torrent_schema(self.store.validate_sample)
        # 分组视图过期由 store.view_changed 精确驱动(仅视图字段/成员变化时置脏), 不再每轮无条件置脏
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
            self._dispatch_events([], removed, dry_run, removed_snapshots=removed_snapshots, state_changed=True)

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
                self._dispatch_events(matched_added, [], dry_run, removed_snapshots=None)
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

        # 更新状态快照(本轮 by_hash 的状态; 新增种子本轮不视为状态变化)
        # 事件分派(on_torrent_state_enum_changed)依赖此上一轮快照对比, 故不局限于 grouping 启用时
        self.store.update_state_snapshot()

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
