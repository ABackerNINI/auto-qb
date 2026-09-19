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
- mixins.web_view     WebviewMixin     WEB 视图组装(分组/单种子视图/搜索索引/状态回传)
- mixins.web_commands WebCommandsMixin WEB 控制命令消费/回执/汇报确认跟踪
- qbclient            (独立模块)       qB 客户端构造(本地地址关闭 trust_env)
"""
import logging
import os
import queue
import threading
import time
from typing import List, Optional

from qbittorrentapi import APIConnectionError, Client

from .config import Config, WebConfig, load_config
from .errors import AutoQbError
from .locking import SingleInstanceLock
from .mixins import (
    CheckingMixin,
    GroupingMixin,
    RuleEngineMixin,
    SpeedCurveMixin,
    TagsMixin,
    TrackerMixin,
    WebCommandsMixin,
    WebviewMixin,
)
from .notify import NotifyHandler, setup_notify
from .qbapi import QbApi
from .qbclient import _new_client
from .rules import Rule
from .taskqueue import FINISHED, REQUEUE, Task, TaskQueue
from .torrents import (
    QbCompatError,
    TorrentRecord,
    TorrentStore,
    missing_torrent_fields,
)
from . import utils
from .logging import setup_logging

logger = logging.getLogger(__name__)

WEB_VIEW_TTL = 10.0  # Web 客户端活跃窗口: 超时无请求则主循环跳过分组视图组装(惰性)
RECONNECT_MAX_INTERVAL = 30.0  # 重连退避上限(秒): qB 长时间宕机时最多每 30s 试一次
STOP_POLL_INTERVAL = 0.5  # 停止信号轮询粒度(秒): 见 _wait_next —— 多事件等待的分段间隔


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


def _wait_next(stop_event: Optional[threading.Event], wake_event: threading.Event, timeout: float) -> bool:
    """主循环等待: 睡到 timeout / 被命令唤醒 / 收到停止信号; 返回 True 表示收到停止信号

    与 _throttle 的区别: 本函数额外响应「命令唤醒」, 让 WEB 操作不必等到下个节拍才被消费;
    且 timeout 是「距下一条时间线的剩余时间」而非固定的 main_tick。

    ❗stop_event 与 wake_event 是两个独立事件, Python 无多事件等待原语。这里**以唤醒为主**:
    阻塞在 wake_event 上(命令到达即返回, 延迟 ≈ 0), 按 STOP_POLL_INTERVAL 分段,
    段间用**非阻塞**的 stop_event.is_set() 检查停止 —— 停止延迟 ≤ 0.5s(UI 退出路径另在
    stop_event.set() 后直接调 manager.wake(), 立即响应)。
    顺序不能反过来(先阻塞等 stop_event): 那样唤醒要等满一个分段才被看见, 命令延迟
    会从 ≈0 退化到 ≤0.5s —— 正是本函数要消除的延迟。
    """
    if stop_event is None:
        wake_event.wait(timeout)
        return False
    deadline = time.time() + timeout
    while True:
        remaining = deadline - time.time()
        if remaining <= 0:
            return False
        if wake_event.wait(min(remaining, STOP_POLL_INTERVAL)):
            return False
        if stop_event.is_set():
            return True


class QbManager(
    RuleEngineMixin,
    TagsMixin,
    CheckingMixin,
    GroupingMixin,
    TrackerMixin,
    SpeedCurveMixin,
    WebviewMixin,
    WebCommandsMixin,
):
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
        # WEB UI: 命令唤醒事件。Web 线程投递命令后 set, 主循环不等下个节拍立即消费一次命令
        # (只走命令线, 不触发 tick —— 见 run() 的双时间线与 wake() 说明)
        self._wake_event = threading.Event()
        # WEB UI: 写命令序号。任何一条非自投递命令执行成功即自增 —— Web 线程据此让
        # "直连 qB 的只读端点"短缓存失效(P1-4), 避免改完立刻重取还拿到缓存里的旧值。
        self._web_write_seq = 0
        # WEB UI: 命令执行结果回执(cmd_id -> {status, error, ts})。主循环线程唯一写者,
        # Web 线程经 /api/cmd/{id} 只读。多数命令执行完立即写; reannounce 的回执由
        # tracker 确认跟踪器(_reannounce_pending)在后续 tick 写入。
        self._web_results: dict = {}
        # WEB UI: 强制汇报确认跟踪(cmd_id -> {deadline, items: {hash: {done, ok, err, baseline}}})。
        # 每 tick 检查一次: 读 torrents/trackers 判定 "status 变 working / next_announce 被重置"。
        self._reannounce_pending: dict = {}
        # WEB UI: 分组视图快照(主循环每 tick 重建并原子替换, Web 线程只读)
        self._group_view: List[dict] = []
        # 单种子视图数据(未归组种子, 与分组视图同一脏窗口同快照重建, 见 ensure_group_view)
        self._singles_view: List[dict] = []
        # 种子平铺视图数据(全部种子的种子中心视图, WEB UI 替代 qB 界面的种子页数据源;
        # 与分组视图同一脏窗口同快照重建, 见 ensure_group_view)
        self._flat_view: List[dict] = []
        # 追剧视图数据(全量种子按 剧→季→集 聚合, 与分组视图同一脏窗口同快照重建):
        # {"list": [剧…], "unrecognized": [hash…]}, members 只放 hash(明细由前端从成员索引取)
        self._shows_view: dict = {"list": [], "unrecognized": []}
        # 追剧视图文件兑底待解析标记: 名称无标记的种子需等搜索索引提供文件列表,
        # 索引推进后置 _group_view_dirty 触发重建归位(见 _build_search_index / _build_shows_view)
        self._shows_pending: bool = False
        # WEB UI: 分组视图版本号(等价 qB 的 rid): 每次重建自增, Web 端按版本跳过整表替换。
        # 以进程启动时间播种: 进程重启后版本号不会回落到旧客户端已持有的值(否则前端会误判
        # "无更新"而一直展示重启前的旧列表)。
        self._group_view_ver: int = int(time.time())
        # WEB UI 惰性组装: _group_view_dirty 标记快照是否过期; _web_last_seen 记录最近一次 Web 请求时间。
        # 主循环仅当 Web 客户端活跃(_web_last_seen 距今 < WEB_VIEW_TTL)才重建快照, 否则跳过以降低 CPU。
        self._group_view_dirty: bool = True
        self._web_last_seen: float = 0.0
        # 已发布但**还没被任何 /api/state 请求取走**的版本号(None = 没有"欠着"的版本)。
        # 用于把"服务端重建节拍"对齐到"客户端实际取数据的节拍": 上一版没人看就不生产下一版
        # (否则 >3000 种子时前端 3s 取一次、服务端 1.5s 重建 ⇒ 约一半重建无人消费)。
        # 详见 _flush_views 的判据注释与 issues/26-09-19-1900-webui-poll-cadence-mismatch。
        self._web_pending_ver: Optional[int] = None
        # 重连退避(见 _reconnect_due): 断开后按 main_tick → 2× → 4× … 递增重试, 上限
        # RECONNECT_MAX_INTERVAL; 每 tick 无脑 connect() 会在 qB 长时间宕机时每 2s 重建一次
        # Client(含 netrc / 代理解析), 纯属空转。连接成功即在 _reset_reconnect_backoff 归零。
        self._reconnect_at: float = 0.0
        self._reconnect_interval: float = 0.0
        # 视图发布锁: 四份视图 + 版本号必须**同一临界区内**发布, 否则 Web 线程会读到
        # "半新半旧"的组合(groups 来自本轮重建、torrents 来自上一轮), 而版本号只有一个
        # ⇒ 前端按 rid 判定"已更新"却拿到互相错位的数据。详见 WebviewMixin.rebuild_views。
        self._view_lock = threading.Lock()
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

    def _reset_reconnect_backoff(self) -> None:
        """连接成功后清零退避(下次断开从最短间隔重新开始)"""
        self._reconnect_at = 0.0
        self._reconnect_interval = 0.0

    def _reconnect_due(self, main_tick: float) -> bool:
        """断开期间是否到了该重试的时刻(指数退避, 上限 RECONNECT_MAX_INTERVAL)

        每 tick 无脑重连在 qB 宕机时是纯空转: 一次 connect() 要重建 Client(含 netrc /
        代理解析), 2s 一次既刷不到有用日志也不加快恢复。恢复后由 _reset_reconnect_backoff 归零。
        """
        now = time.monotonic()
        if now < self._reconnect_at:
            return False
        base = self._reconnect_interval or main_tick
        self._reconnect_interval = min(max(base * 2, main_tick), RECONNECT_MAX_INTERVAL)
        self._reconnect_at = now + base
        return True

    def connect(self) -> bool:
        """连接 qBittorrent(本地地址经 _new_client 使用关闭 trust_env 的 LocalQbClient)"""
        try:
            self.client = _new_client(self.config.qbittorrent)
            self.api.auth_log_in()
            # 连接恢复(此前断开)或首次连接: 记录一次"已连接"状态
            if self._last_conn_ok is False:
                logger.info("已重新连接 qBittorrent")
            self._last_conn_ok = True
            self._reset_reconnect_backoff()
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

    def wake(self) -> None:
        """唤醒主循环立即消费一次 WEB 控制命令(命令线; **不触发 tick**)

        Web 线程投递命令后调用: 命令延迟从 0~main_tick(最坏 2s)降到近乎 0。

        ❗只走命令线是硬约束, 不能退化成"投递即跑下一轮 tick":
        1) max_tasks_per_tick 承载的是**速率语义**(20 个/2s = 10 任务/秒), tick 频率一旦由命令
           决定, 这个上限即失效;
        2) 存在**自投递命令**(Web 侧索引脏时自己 put build_search_index), "投递即唤醒跑 tick"
           会形成自激循环: 唤醒 -> drain(单轮 500 条文件 API) -> 索引仍脏 -> 再投递 -> 立刻再唤醒,
           中间没有 tick 兜底 —— 不是变慢, 是打满 CPU 并冲垮 qB。
        故: 自投递命令不唤醒(见 mixins/web_commands.py 的 SELF_POSTED_COMMANDS),
        且唤醒后只 drain 命令, tick 仍由 sync_interval / main_tick 严格决定。
        """
        self._wake_event.set()

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
                # 两条独立时间线(分层节拍):
                #   同步线 sync_interval(默认 1.5s) —— 只刷新快照, 不跑任务;
                #   任务线 main_tick(默认 2s)     —— 跑任务 + tracker 预取 + 搜索索引。
                # 拆开后状态新鲜度不再被任务节拍拖累, 而任务速率语义(max_tasks_per_tick)
                # 与每 tick 的 qB 请求预算仍由 main_tick 唯一决定。
                next_sync_at = 0.0
                next_tick_at = 0.0
                while True:
                    if stop_event is not None and stop_event.is_set():
                        logger.info("收到停止信号, 退出主循环")
                        break
                    # L0 热重载: 每轮重读节拍(配置对象可能被 apply_new_config 整体替换)
                    main_tick = self.config.main_tick
                    # 同步线只刷快照, 而任务线(_task_line)不拉快照 ⇒ sync_interval 一旦大于
                    # main_tick, 快照新鲜度就掉到主循环心跳之下, 任务会基于陈旧快照做判定。
                    # schema 已把契约写成「大于主循环间隔时按主循环间隔生效」, 这里落实为钳制
                    # (默认 1.5s < 2s, 对默认配置零影响; 见 BUG-6)。
                    sync_interval = min(self.config.sync_interval, main_tick)
                    # WEB UI 控制命令(暂停/开始/删除/强制汇报/热重载): 主循环线程执行写操作。
                    # 先清唤醒位再 drain —— drain 期间新到的命令会再次置位, 下一轮立即消费。
                    self._wake_event.clear()
                    state_changed = self._drain_web_commands()
                    self._check_reannounce_pending()
                    if pause_event is not None and pause_event.is_set():
                        # 已暂停: 完全旁观; 等待保持对停止信号与命令的响应
                        if _wait_next(stop_event, self._wake_event, main_tick):
                            logger.info("收到停止信号, 退出主循环")
                            break
                        continue
                    now = time.time()
                    # P0-5: 本批命令改了 qB 种子状态 -> 立即同步一次, 让真实状态在几十毫秒内
                    # 进快照(不必等下个节拍)。整批只补一次: sync_due 为真时本轮至多跑一次刷新。
                    # dry_run 不补(只观察); 暂停时上面已 continue(暂停 = 完全旁观)。
                    sync_due = (now >= next_sync_at) or (state_changed and not dry_run)
                    tick_due = now >= next_tick_at
                    try:
                        # 命令驱动(state_changed)的那一轮 force=True: 绕过"上一版是否被取走"门控,
                        # 否则用户操作后的真值可能要等客户端下一次轮询才进快照(与 P0-5 相悖)。
                        cmd_forced = bool(state_changed) and not dry_run
                        if sync_due and tick_due:
                            self._tick(dry_run, force=cmd_forced)
                            next_sync_at = time.time() + sync_interval
                            next_tick_at = time.time() + main_tick
                        elif sync_due:
                            self._sync_line(dry_run, force=cmd_forced)
                            next_sync_at = time.time() + sync_interval
                        elif tick_due:
                            self._task_line(dry_run, force=cmd_forced)
                            next_tick_at = time.time() + main_tick
                        # 连接恢复检测: 上面任一条线跑通即 API 可达(connect() 仅启动时调用一次,
                        # 断开后恢复只能在此翻转, 否则 UI 永远显示"qB 断开")
                        if (sync_due or tick_due) and self._last_conn_ok is False:
                            self._last_conn_ok = True
                            self._reset_reconnect_backoff()
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
                        # 退避: 不在每 tick 重建 Client(见 _reconnect_due)。qB 重启/网络恢复后
                        # 仍会自动接上, 只是重试间隔逐步拉长到 30s, 而不是 2s 一次空转。
                        if self._reconnect_due(main_tick):
                            self.connect()
                    except Exception as e:
                        logger.error(f"主循环异常: {e}", exc_info=True)
                    # 等待到最近一条时间线到期, 或被命令唤醒(命令线近乎零延迟)
                    wait_for = max(0.0, min(next_sync_at, next_tick_at) - time.time())
                    if _wait_next(stop_event, self._wake_event, wait_for):
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

    # ---------- 单种子命令(WEB 明细行右键) ----------

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

    def _flush_views(self, force: bool = False) -> None:
        """消费视图脏标记并在 Web 活跃时惰性重建(同步线/任务线各自调用一次)

        consume_view_changed 是 consume 语义(读后复位), 两条线各调一次即可完整覆盖
        自上次消费以来由「刷新」或「任务执行」产生的视图变化。

        `force=True` 表示"本轮有命令改了种子状态", 必须**绕过**下面的"已取走"门控 ——
        P0-5 要求用户操作后真值在几十毫秒内进快照, 不能因为上一版还没被取走就跳过。
        """
        # 视图相关内容变化(store 视图字段/组成员)读取并复位, 供下方视图惰性重建判定
        view_changed = self.store.consume_view_changed()
        # 置脏必须在 grouping 门控**之外**: 脏标记是**全部** Web 视图的共享状态 —— 种子页的
        # 平铺视图(flat)/ 未归组单种子(singles)/ 追剧视图(shows)与"辅种分组是否启用"无关。
        # 曾把置脏写在 `if grouping.enabled` 块内, 而 consume 在块外 ⇒ 分组关闭时标记被吞,
        # 版本号不再变化 ⇒ 前端 updated=false 并退避轮询, 四份视图全部冻住。
        if view_changed:
            self._group_view_dirty = True
        # WEB UI: 视图快照——惰性组装。仅当 Web 客户端活跃(_web_last_seen 距今 < WEB_VIEW_TTL)
        # 且视图内容确有变化(视图字段/成员变化, 或显式置脏)时才重建, 否则主循环不空转;
        # 关闭网页后 CPU 回落。重建统一走 `rebuild_views`(四份视图 + 版本号的唯一入口,
        # 不得在这里只建其中一份 —— 见该方法 docstring 的 2026-09-18 缺陷)。
        web_active = (time.time() - self._web_last_seen) < WEB_VIEW_TTL
        # 「上一版有没有人取走」门控: 服务端节拍(固定 1.5s)与客户端节拍(按种子量 1.5/2/3s)
        # 各自独立定档 ⇒ 大库下服务端每 3s 产 2 版而客户端只取最后一版, 中间那版的重建 CPU
        # 没有任何请求消费过。这里让"生产"等一等"消费": 上一版没被取走就不生产下一版。
        # 判据: _web_pending_ver 为 None(没有欠着的版本)才重建; force(命令改了状态)必须绕过。
        # 效果: >3000 种子由 2 版/次取降为 1 版/次取(≈省一半), ≤1000 种子(同为 1.5s)不受影响。
        # 数据新鲜度不受影响 —— 客户端本来就只在自己那拍才看得到数据。
        unconsumed = self._web_pending_ver is not None
        if self._group_view_dirty and web_active and (force or not unconsumed):
            self.rebuild_views()

    def _sync_line(self, dry_run: bool, flush: bool = True, force: bool = False) -> None:
        """同步线(sync_interval 节拍): 拉 qB 增量 -> 推进快照/事件/分组 -> 视图惰性重建

        只做状态同步、**不跑任务** —— 状态新鲜度不再被任务节拍(main_tick)拖累。
        sync_interval 取 1.5s 与 qB 自带 WebUI(1500ms)同量级: 比 qB 自身数据粒度更快没有意义。
        """
        self._refresh_torrents(dry_run)
        if flush:
            self._flush_views(force=force)

    def _task_line(self, dry_run: bool, force: bool = False) -> None:
        """任务线(main_tick 节拍): 错误原因预取 + 执行到期任务 + 视图/搜索索引推进

        tracker 预取与文件 API 批量调用**仍跟 main_tick, 不跟随快档**: 它们不是状态新鲜度的
        瓶颈, 提频只会线性放大 qB 请求量(见计划附录 A3 的五动作归档)。
        """
        now = time.time()

        # WEB UI: 错误状态种子的具体原因(状态列的"文件丢失"/tracker 报错原文)按 TTL 限额预取。
        # 与视图重建/搜索索引同一门控: 仅 Web 客户端活跃时推进, 关闭网页后不发多余的 tracker 请求。
        if (time.time() - self._web_last_seen) < WEB_VIEW_TTL:
            self.refresh_error_reasons()

        self.task_queue.run_due(dry_run, now=now, max_tasks=self.config.max_tasks_per_tick)

        self._flush_views(force=force)

        # WEB UI: 搜索索引限流构建——同样仅 Web 活跃时推进(每 tick 一批, 直至不再脏);
        # 关闭网页后停止推进, 避免无谓的文件 API 调用
        if self._search_index_dirty and (time.time() - self._web_last_seen) < WEB_VIEW_TTL:
            self._build_search_index()

    def _tick(self, dry_run: bool, force: bool = False):
        """完整一轮 = 同步线 + 任务线(执行与收尾统一由 TaskQueue.run_due 管理)

        主循环按节拍**分别**调度两条线(见 run); 本方法保留"同步+任务"的完整语义,
        供测试与一次性调用使用。两条线同时到期时走这里, 保证视图只重建一次。
        """
        self._sync_line(dry_run, flush=False)
        self._task_line(dry_run, force=force)

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
