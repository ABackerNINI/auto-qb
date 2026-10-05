"""QbManager: qBittorrent 主管理类(核心域)

任务队列统一协调: 种子刷新 / 规则 / 种子级内置功能 / 异步校验 全部是带内置 interval 的任务。
检测到新增种子时, 自动为该种子创建所有符合条件的 rule 任务(仅 tracker 显式引用的规则; 站点未配置
rules 引用时该站点种子不绑定任何规则 —— 不会回退为"执行全部启用规则")。

**本类只管核心域**: 连接 / 主循环节拍 / 状态同步 / 任务执行 / 种子刷新。WEB UI 的表现层状态
与节拍判据在 `web_runtime.WebUIRuntime`(门面), 主循环经宿主 loop hooks 与它交互
(命令线/同步线收尾/任务线收尾, plan kernel-module-refactor P2), 不持有也不判断任何表现层
字段(2026-09-20 拆出, 见 memory-bank/plans/26-09-20-0234-webui-decoupling-plan.html)。

职责拆分(表现层 mixin, 各模块组合进本类):
- webui.views         WebviewMixin     WEB 视图**构建器**(纯读 store/config, 产出 dict)
- webui.commands      WebCommandsMixin WEB 控制命令**处理器**与命令表(主循环线程执行写操作)
- web_runtime         WebUIRuntime     WEB 表现层门面(状态 + 节拍判据 + 命令编排; P2 起经
                                       WebUIModule 接入宿主, 见 webui/module.py)
- qbclient            (独立模块)       qB 客户端构造(本地地址关闭 trust_env)

已模块化(plan kernel-module-refactor, 见 core/modules/ 与 webui/hr 各自 module.py):
- P1 logging/notify(基建样板) → P2 webui/hr(门面转正) → P3 tracker(tracker 匹配升
  ctx.trackers 服务 + full_round 相位重匹配)/speed_curve(曲线任务自注册 + 流量快照经
  ctx.web.set_traffic_view 推送)/maintenance(标签/分类/HR 标签/集数标签/维护任务 + 全局
  标签清理任务自注册) → P4 grouping(四刷新相位 transitions/torrents_added/removed_scan/
  post 认领)/ops(+checking 并入, 决策点 D2; 危险操作层升 ctx.ops 服务) → P5 rules(规则
  引擎整体迁 RulesModule, 事件分派/建任务改相位认领, L2 结构重建收进 rules.apply ——
  刷新管线收口为「同步 + 相位广播」, 内核不再点名任何业务步骤, 也不再 import rules)。
  旧名兼容层(_WEB_STATE_ALIAS + 五节单行委托)已随别名层处置 W3 整体退役(2026-10-01,
  plan web-state-alias-disposal; 反复活守阵 tests/test_qbmanager_alias_freeze.py)。

内核地基(plan kernel-module-refactor): 构造期立 AppContext(ctx)并把能力服务挂上
(store/api/state/task_queue/web/trackers/maintenance/ops), 本类同名属性自此刻起全部是
**委托**(ctx 为单一真相, 守阵断言同对象); ModuleHost / EventBus 编排机制 + 装配清单在
构造期建立 —— 最终收敛为「宿主只知何时, 不知何事」。属性对按处置计划 D1 拍板**永久
保留**(manager 即外观的公共面), 旧名方法与别名字段不再存在。
"""
import logging
import os
import threading
import time
from typing import List, Optional

from qbittorrentapi import APIConnectionError, Client

from ..config import Config, load_config
from ..config.writer import materialize_schema_migration
from ..infra import file_access
from ..infra.errors import AutoQbError
from ..infra.locking import SingleInstanceLock
from .module import AppContext, EventBus, ModuleHost
from .modules import (
    GroupingModule,
    LoggingModule,
    MaintenanceModule,
    NotifyModule,
    OpsModule,
    RulesModule,
    SpeedCurveModule,
    TrackerModule,
    TrafficSampleModule,
)
from .state import StateService
from ..webui.commands import WebCommandsMixin
from ..webui.views import WebviewMixin
from .qbapi import QbApi
from .qbclient import new_client
from .taskqueue import TaskQueue
from ..webui import WebUIRuntime
from ..webui.module import WebUIModule
# HR 在线核实运行时门面(端点 + 取数线程 + 只读视图): 与 WebUIRuntime 同级, 见 __init__ 说明
from ..hr.runtime import HrRuntime
from ..hr.module import HrModule
from ..torrents import (
    QbCompatError,
    TorrentStore,
    missing_torrent_fields,
)
from ..infra import utils

logger = logging.getLogger(__name__)


class QbConnectError(AutoQbError):
    """无法连接 qBittorrent(非托管模式首连失败)

    走 CLI 的 AutoQbError 统一出口: stderr 干净消息、无堆栈、退出码 1
    (docs/deployment.md 排障表承诺的契约, 与 ConfigError/SingleInstanceLockError 同路径)。
    托管模式(--tray/托管 UI)不抛 —— 首连失败按 main_tick 重试保持常驻, 见 run()。
    """


# 等真值落地时的重新同步间隔(秒): resume 后 qB 要过一会儿才翻状态, 不能干等一个 sync_interval
# (真机大库 2s)。只在有真值等待时生效, 由 TRUTH_PUSH_CAP_MS 兜底不会无限空转。
TRUTH_RETRY_S = 0.2
RECONNECT_MAX_INTERVAL = 30.0  # 重连退避上限(秒): qB 长时间宕机时最多每 30s 试一次
STOP_POLL_INTERVAL = 0.5  # 停止信号轮询粒度(秒): 见 _wait_next —— 多事件等待的分段间隔


def _throttle(stop_event: Optional[threading.Event], main_tick: float) -> bool:
    """主循环节流: 阻塞 main_tick 秒, 返回 True 表示收到停止信号

    托管模式(tray/UI 传入 stop_event)走 Event.wait, 保持对停止信号的即时响应;
    非托管模式(CLI 默认无 stop_event)走 time.sleep —— **必须真实睡眠**。

    !回归背景(2026-09-14): 主循环曾写成 `if stop_event is not None and stop_event.wait(main_tick)`,
    非托管模式下被 `and` 短路 -> 完全不阻塞 -> 空转。由每 tick 固定成本(update_state_snapshot 等)
    反推约 2800 tick/s, 是 main_tick=2s 设计值的约 5500 倍: CPU 打满, 且把
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

    !stop_event 与 wake_event 是两个独立事件, Python 无多事件等待原语。这里**以唤醒为主**:
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
    WebviewMixin,
    WebCommandsMixin,
):
    def __init__(self, config_path: str, config: Config = None, no_lock: bool = False):
        self.config_path = config_path
        # 内核地基(plan kernel-module-refactor P0): ctx 先立 —— config/store/api/state 挂上
        # ctx, 本类同名属性自此刻起全部委托 ctx(单一真相; 见下方服务委托属性区)。
        self.ctx = AppContext(config or load_config(config_path))
        # 事件总线与模块宿主(plan §3/§4): 宿主持注册表并编排生命周期, 总线供相位广播
        self.events = EventBus()
        self.host = ModuleHost(self.ctx, self.events)
        # 装配清单(plan §3.3): 顺序 = 相位内消费序 = 生命周期序, 内核唯一「知道模块名字」的
        # 地方。P1 基建两模块(logging/notify), P2 门面转正(webui/hr), P3 小模块三件
        # (tracker/speed_curve/maintenance), P4 中坚两件(grouping/ops), P5 收官 rules
        # (rules 最后: 它消费前面所有人的服务)。
        self.host.register(LoggingModule())
        self.ctx.notify = NotifyModule(self.ctx)  # 托盘经 ctx.notify 调公开方法(plan §3.2)
        self.host.register(self.ctx.notify)
        # 文件访问层单点(plan 26-09-27-1407): 下载数据目录的全部本地访问经此包装;
        # fs 段 R 级热重载 —— 单例在此按配置构建一次, 运行期不切换
        file_access.init_file_access(self.config)
        self._fs_path_map_checked = False  # 映射自检一次性闸门(首轮全量同步后跑, 见 _refresh_torrents)
        # 日志初始化经 logging 模块(plan P1): 实现单点在 LoggingModule; dry_run 与日志无关
        # (dry-run/导出模式同样要日志), 故这里恒传 False, run() 的 start_all 靠 start 幂等合流
        self.host.get("logging").start(self.ctx, dry_run=False)
        # 种子信息数据层: 增量同步 + 惰性缓存 + 分组索引 + 全局标签/分类缓存
        # 每 main_tick 只拉变化部分(sync/maindata)后, 本 tick 内所有读取操作都只通过 self.store 接口访问
        self.store = TorrentStore()
        self._client: Optional[Client] = None  # 由 client 属性管理, 与 store.client 同步
        # qB API Facade: 统一封装客户端调用 + 写操作后同步 store 快照(快照一致性)
        self.api = QbApi(self._client, self.store)
        # 状态持久化服务(plan P0 自 RuleEngineMixin 迁出): state.json 读写/迁移/周期落盘单点
        self.ctx.state = StateService(self.config.state_file)
        # 数据目录(state/锁/日志/跳检备份同处): 显式建目录, 不依赖日志文件配置(console-only 时无日志建目录)
        os.makedirs(os.path.dirname(self.state_file) or ".", exist_ok=True)
        self.state = self.ctx.state.load()  # 从文件加载(run() 时再次加载覆盖; 直接使用(测试/process_torrent 入口)也含历史)
        self.ctx.state.bind_field_snapshots(self.store)  # 字段变化基线挂到 state 顶层键(计划 26-09-27-1438)
        # 周期落盘计时器(见 StateService.maybe_flush): run() 加载状态后重置为首个到期点
        self.ctx.state.next_flush_at = 0.0
        # 规则结构初始化移入 RulesModule(P5; 规则加载在 run() 中进行: --export-yaml 等
        # 只导出模式不需要); rules/enabled_rules 旧名委托属性已随别名层处置 W3 删除
        # 任务队列: 统一管理所有任务(种子刷新/规则/种子级内置功能/异步校验/全局标签清理/分组)
        # (P3 起挂 ctx: speed_curve/maintenance 模块的任务自注册经 ctx.task_queue 现取当前队列;
        #  本属性只是委托, L2 整体重建也经 setter 落回 ctx)
        self.task_queue = TaskQueue()
        # 版本兼容校验: 首次拉到非空种子信息时执行一次(qB 版本运行期不变)
        self._schema_validated = False
        # 连接状态(节流重复连接错误日志): None=未知/首次, True=已连接, False=已断开
        # 仅状态转换时记录, 断开期间静默(qB 宕机时不刷屏)
        self._last_conn_ok: Optional[bool] = None
        # WEB UI: 表现层门面 —— 视图快照 / 版本号 / 脏标记 / 活跃心跳 / 回执 / 命令队列 /
        # 搜索索引 / 密钥与句柄 全部收在 WebUIRuntime 里, 主循环只见它暴露的少数语义方法。
        # (2026-09-20 从本类拆出: 原先 19 个表现层字段平铺在 __init__, 主循环因此要替表现层
        #  做"要不要重建 / 要不要补刷新"的判断。详见 web_runtime.py 的模块 docstring。)
        # P2 门面转正: 服务器启停/热重载语义/loop hooks 内聚 WebUIModule(webui/module.py)。
        # (P3 起 web 挂 ctx: speed_curve 模块经 ctx.web.set_traffic_view 推送流量快照,
        #  本属性只是委托, 测试整对象替换也经 setter 落回 ctx)
        self.web = WebUIRuntime(self)
        # HR 在线核实运行时: 本地取数端点 + 取数线程 + 只读视图(计划 §8)。
        # 同 WebUIRuntime 的思路 —— 附属线程与文件句柄的生命周期不进核心域, 主循环只见门面:
        # 取数线程按 poll_interval 自唤醒, 主循环与判定路径只读视图(hr.view_set(), 零等待、
        # 读取时现算三态); hr.wake() 是留给主循环的**可选**叫醒口(非阻塞, 当前无调用点)。
        # 未启用(总开关关 / 无站点 enabled)时它什么都建, 也不会起任何线程。
        # P2 门面转正: 启停/热重载语义内聚 HrModule(hr/module.py)。
        self.hr = HrRuntime(self)
        # 装配清单 P2(plan §3.2 门面转正): webui/hr 实现 Module 契约, 启停与热重载语义
        # 内聚模块 —— 服务器启动/HR 端点与取数线程的启停都改经 host.start_all/stop_all,
        # 热重载广播经各自 apply(web 服务器重启/hr 重挂自 apply_new_config 的手工分派迁出)。
        self.host.register(WebUIModule(self))
        # 判定桥: 记录持有门面的**稳定引用**(热重载不换对象), 读取时现算三态 ——
        # 故锚点漂移/站点视图更新都不需要"记录置脏"或全库重建记录(计划 §9)。
        # 注入属装配的一部分(plan P2): 桥接在装配点一次成形, 记录侧只认这个稳定引用。
        self.store.hr_link = self.hr
        self.host.register(HrModule(self))
        # 装配清单 P3(plan §3.3 小模块先行): tracker 匹配升 ctx 服务(决策点 D3), 曲线与
        # 全局标签清理任务由模块 start() 自注册 —— 内核 _create_global_tasks 的任务点名退役
        self.ctx.trackers = TrackerModule(self.ctx)
        self.host.register(self.ctx.trackers)
        self.host.register(SpeedCurveModule(self.ctx))
        # maintenance 句柄挂 ctx(P4): grouping 打标经 ctx.maintenance.add_tags, 不 import 兄弟模块
        self.ctx.maintenance = MaintenanceModule(self.ctx)
        self.host.register(self.ctx.maintenance)
        # 装配清单 P4(plan §3.3 中坚模块): grouping 认领四个刷新相位(transitions /
        # torrents_added / removed_scan / post, _refresh_torrents 的分组调用点改相位广播,
        # enabled 开关模块自判); ops(+checking 并入, 决策点 D2)升 ctx.ops 服务 —— 规则
        # 动作与 WEB 命令的危险操作执行体单点, web 命令改走 ctx.ops(plan P4)
        self.host.register(GroupingModule(self.ctx))
        self.ctx.ops = OpsModule(self.ctx)
        self.host.register(self.ctx.ops)
        # 装配清单 P5 收官(plan §3.3): rules 最后 —— 事件分派/建任务改相位认领, L2 结构
        # 重建收进 rules.apply(W3), 级别分派层与三张手写表退役(W4)
        self.host.register(RulesModule(self))
        # 装配清单追加(plan 26-10-03-0946 方案C P1): qB 口径流量采样器 —— internal 采样任务
        # 自注册(start/queue_rebuilt), enabled=false(缺省)零任务零文件(黄金法则 2); 与其余
        # 模块零耦合(只读 store 快照), 挂清单末尾
        self.host.register(TrafficSampleModule(self.ctx))
        # 命令唤醒事件(**核心域原语**, 不是表现层的): 投递命令后 set, 主循环不等下个节拍
        # 立即消费一次命令(只走命令线, 不触发 tick —— 见 run() 的双时间线与 wake() 说明)。
        # 托盘 UI 停止时也要用它打断等待, 故留在核心域。
        self._wake_event = threading.Event()
        # 重连退避(见 _reconnect_due): 断开后按 main_tick → 2× → 4× … 递增重试, 上限
        # RECONNECT_MAX_INTERVAL; 每 tick 无脑 connect() 会在 qB 长时间宕机时每 2s 重建一次
        # Client(含 netrc / 代理解析), 纯属空转。连接成功即在 _reset_reconnect_backoff 归零。
        self._reconnect_at: float = 0.0
        self._reconnect_interval: float = 0.0
        # 暂停事件(run() 注入; UI 线程切换, 主循环线程只读)
        self._pause_event = None
        # 单实例锁: 仅正常 run 模式持锁(--export-yaml 等只读模式传 no_lock=True 跳过, 允许并发)
        self._lock = None
        if not no_lock:
            self._lock = SingleInstanceLock(self.state_file)
            self._lock.acquire()
            # 持锁后才清: 锁住了说明没有别的实例在写, 状态目录里的 <state_file>.*.tmp 全是上次崩溃的遗留
            self.ctx.state.cleanup_orphan_tmp()

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

    # ---------- 服务委托(外观属性面, D1 拍板永久保留) ----------
    # config/store/api/state/state_file 的实现单点在 ctx(AppContext/StateService); 这组
    # 属性对使 76 处构造点 / 279 处 make_manager 测试 / mixin 与门面的直读全部零改动,
    # 热重载的整体替换(self.config = config)与测试整对象替换(mgr.api = ...)也经 setter
    # 落回 ctx。别名层处置 D1 拍板(2026-10-01): 属性面永久保留 —— 340/309/134 处直读是
    # 「manager 即外观」的合理公共面, 不是别名; 纯内部属性对 _next_state_flush_at 已随
    # W3 删除(读写改经 ctx.state.next_flush_at)。

    @property
    def config(self) -> Config:
        """当前生效配置(热重载时整体替换; ctx 为单一真相)"""
        return self.ctx.config

    @config.setter
    def config(self, value: Config) -> None:
        self.ctx.config = value

    @property
    def store(self) -> TorrentStore:
        """种子信息数据层(与 ctx.store 同一对象)"""
        return self.ctx.store

    @store.setter
    def store(self, value: TorrentStore) -> None:
        self.ctx.store = value

    @property
    def api(self) -> QbApi:
        """qB API Facade(与 ctx.api 同一对象)"""
        return self.ctx.api

    @api.setter
    def api(self, value: QbApi) -> None:
        self.ctx.api = value

    @property
    def state(self) -> dict:
        """运行期状态 dict(执行历史/去重/备份元数据...): ctx.state 服务的落盘载荷, 同一对象"""
        return self.ctx.state.data

    @state.setter
    def state(self, value: dict) -> None:
        self.ctx.state.data = value

    @property
    def state_file(self) -> str:
        """state.json 路径(构造期确定, 运行期不变; R 级热重载拒绝项)"""
        return self.ctx.state.state_file

    @property
    def task_queue(self) -> TaskQueue:
        """任务队列(与 ctx.task_queue 同一对象; speed_curve/maintenance 模块自注册经 ctx 现取)"""
        return self.ctx.task_queue

    @task_queue.setter
    def task_queue(self, value: TaskQueue) -> None:
        self.ctx.task_queue = value

    @property
    def web(self) -> WebUIRuntime:
        """WEB 表现层门面(与 ctx.web 同一对象; speed_curve 模块经 ctx.web 推送流量快照)"""
        return self.ctx.web

    @web.setter
    def web(self, value: WebUIRuntime) -> None:
        self.ctx.web = value

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
        """连接 qBittorrent(本地地址经 new_client 使用关闭 trust_env 的 LocalQbClient)"""
        try:
            self.client = new_client(self.config.qbittorrent)
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
            # 非 API 类连接异常(典型: 凭据错 LoginError)与连接类同用转换节流(issue A-07):
            # 托管模式首连重试循环每 main_tick 走一次这里, 无条件 ERROR 等于逐拍刷屏;
            # 同一根因只说明白一次(pitfalls/ops/alert-levels.md 2.), 失败态下再失败静默。
            if self._last_conn_ok is not False:
                logger.error(f"连接 qBittorrent 失败: {e}")
                self._last_conn_ok = False
            return False

    def reconnect(self) -> None:
        """重建 qB 客户端连接(热重载共用口, plan P5): client 换新 + rid 失效(下轮全量)

        连接管理属内核(plan §3.1): 热重载 L1 的 qbittorrent 段变由 apply_new_config 调用,
        L2 结构重建由 RulesModule.rebuild_runtime 调用 —— 模块不直写 client/_last_conn_ok
        私有面。原 apply_new_config 两个分支的 `client=None + _last_conn_ok=None + connect()`
        三行序列收敛于此。
        """
        self.client = None
        self._last_conn_ok = None
        self.connect()

    def wake(self) -> None:
        """唤醒主循环立即消费一次 WEB 控制命令(命令线; **不触发 tick**)

        Web 线程投递命令后调用: 命令延迟从 0~main_tick(最坏 2s)降到近乎 0。

        !只走命令线是硬约束, 不能退化成"投递即跑下一轮 tick":
        1) max_tasks_per_tick 承载的是**速率语义**(20 个/2s = 10 任务/秒), tick 频率一旦由命令
           决定, 这个上限即失效;
        2) 存在**自投递命令**(Web 侧索引脏时自己 put build_search_index), "投递即唤醒跑 tick"
           会形成自激循环: 唤醒 -> drain(单轮 500 条文件 API) -> 索引仍脏 -> 再投递 -> 立刻再唤醒,
           中间没有 tick 兜底 —— 不是变慢, 是打满 CPU 并冲垮 qB。
        故: 自投递命令不唤醒(见 webui/commands.py 的 SELF_POSTED_COMMANDS),
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
          非托管模式首连失败抛 QbConnectError -> CLI 干净退出码 1(fail-fast, docker/compose 重启策略
          据此判失败; 容器里配合 restart 策略由 Docker 自带退避接管, qB 恢复后下一轮自动接上)
        """
        self._pause_event = pause_event
        # 启动物化(计划 26-09-27-2252): 磁盘版本落后则「版本号备份 -> 迁移 -> 校验 -> 原子写回」。
        # 放 run() 不进 __init__: 锁已持有 + 日志已就绪 + dry_run 已知三个前提在此齐备, 且先于
        # WebUI 对外服务 —— 与保存请求无并发窗口。dry-run 只探测提示不落盘(与 state 迁移同口径)。
        desc, backup = materialize_schema_migration(self.config_path, self.config.data_dir, write=not dry_run)
        if desc and dry_run:
            logger.info(f"磁盘配置 schema 落后({desc}), dry-run 仅内存生效不落盘")
        elif desc:
            logger.info(f"配置 schema 已迁移 {desc} 并落盘(迁移前备份: {backup})")
        logger.info(f"启动 qB 管理器: 主循环 {self.config.main_tick}s, 默认任务间隔 {self.config.interval}s")
        # 模块启用(plan P1/P2): web 服务器(启用时)/HR 端点与取数线程/通知挂载全部在各自模块
        # 的 start(dry-run/未启用 = 无操作, 模块自判), 内核只按装配序调 —— web 启动失败(端口
        # 被占)记 ERROR 由句柄呈现; HR 端口被占抛 HrChannelBindError 穿透到 CLI 干净退出
        # (fail-fast 契约原样)。logging 已在构造期初始化(start 幂等跳过)。
        # P3 起 speed_curve/maintenance 的全局任务自注册也发生在 start_all(原 _create_global_tasks
        # 在连接成功后手工调用, 入队时点前移到启动 —— 队列在首个任务线才被 drain, 行为等价)。
        self.host.start_all(dry_run)
        try:
            main_tick = self.config.main_tick
            # 首连失败: 托管模式按 main_tick 重试直至成功/停止; 非托管模式 fail-fast 抛
            # QbConnectError(退出码 1, docs/deployment.md 契约)。条件本身是有意语义(见
            # behavior-core.md: 不要把 or 改成 and), 只允许改 None 分支的处置。
            # 重试 WARNING 只在进入重试时说明白一次(issue A-07: 凭据错等非连接类异常此前
            # connect() ERROR + 本行 WARNING 每 main_tick 逐拍刷屏; connect() 侧转换节流后,
            # 这里同口径不再逐拍重复 —— 同因静默, 连接成功后有 INFO 收尾)。
            retry_warned = False
            while not self.connect():
                if stop_event is None or stop_event.wait(main_tick):
                    if stop_event is None:
                        qb = self.config.qbittorrent
                        raise QbConnectError(
                            f"无法连接 qBittorrent {qb.host}:{qb.port}: 请检查 qB 是否在运行、"
                            "Web UI 地址/端口/凭据是否正确"
                            "(容器里连宿主机 qB 应填 host.docker.internal; 详细失败原因见上方日志)"
                        )
                    return
                if not retry_warned:
                    logger.warning(f"连接 qBittorrent 失败, {main_tick:g}s 后重试(检查 qB 是否运行/端口是否正确)")
                    retry_warned = True
            self.state = self.ctx.state.load()
            self.ctx.state.bind_field_snapshots(self.store)  # state 被整体替换, 字段变化基线重新挂接
            # schema 迁移物化(计划 26-09-26-0506): 磁盘版本 < CURRENT 时立即落盘一次新版本。
            # 此处已持锁(与 __init__ 的 cleanup_orphan_tmp 同判据); __init__ 的早期加载只做内存迁移。
            self.ctx.state.materialize_migration(dry_run)
            # 周期落盘起点: 刚从磁盘加载过, 到期点从现在起算一个完整间隔(避免启动即无意义重写)
            self.ctx.state.next_flush_at = time.time() + max(self.config.state_save_interval, 0.0)
            self.host.get("rules").load_rules()

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
                    # 命令线: WEB 控制命令(暂停/开始/删除/强制汇报/热重载)由主循环线程执行写操作。
                    # 先清唤醒位再 drain —— drain 期间新到的命令会再次置位, 下一轮立即消费。
                    # 命令表分发/回执/写序号/自投递判据归 webui 模块的 on_command_line hook
                    # (plan P2), 这里只取"本批是否改了 qB 种子状态"这一个语义结果(P0-5 判据)。
                    self._wake_event.clear()
                    state_changed = self.host.run_command_line()
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
                    # !必须在 try **之外**初始化: 兜底 flush 在 except 之后读它, 若异常发生在这行
                    # 之前, 名字未绑定会抛 NameError —— 它在 try 外面, 会直接把主循环打挂。
                    _flushed = False  # 本轮正常路径是否已落过回执(兜底据此跳过, 免得日志打两遍)
                    try:
                        # 命令驱动(state_changed)的那一轮 force=True: 绕过"上一版是否被取走"门控,
                        # 否则用户操作后的真值可能要等客户端下一次轮询才进快照(与 P0-5 相悖)。
                        # 有真值在**等落地**(见 WebUIRuntime.flush_truths): resume 后 qB
                        # 要过一会儿才翻状态, 紧跟着的那次补刷新读到的还是命令前的值。此时不能干等
                        # 下一个同步周期(真机大库 2s) —— 那正是用户看到的"点了要 2 秒才恢复正常"。
                        _wait_truth = bool(getattr(self.web, "truth_pending", None))
                        cmd_forced = (bool(state_changed) or _wait_truth) and not dry_run
                        # 命令驱动的那一轮顺带计时: 「补刷新」是用户感知延迟的第三段
                        # (前两段 排队/执行 由门面的 _log_cmd_timing 落日志)。
                        # 真值在这一段结束才进快照 —— 前端乐观 UI 撤下要等的就是它。
                        _t_line = time.time() if (state_changed and not dry_run) else 0.0
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
                        # !无条件落"推迟的回执"(哪怕本轮没跑补刷新 / dry_run):
                        # 漏调会让前端 waitCmd 干等 40s。放在补刷新**之后**是刻意的 ——
                        # 回执带上此刻的真值, 前端就不必再拉一次全量 /api/state。
                        self.web.flush_truths()
                        _flushed = True
                        if _t_line:  # pragma: no cover - web 命令线补刷新计时弧, 单测 web 未启用不可达(26-10-02-0441)
                            self.web.resync_elapsed_ms(_t_line)
                        # 周期落盘(非优雅终止的状态丢失窗口, issue 26-09-21-1347): 到期则写盘一次。
                        # save_state 原本仅优雅退出可达 —— taskkill/断电/崩溃不走 finally, 运行期
                        # 状态全丢; 间隔 state_save_interval(0=关闭), dry-run 不落盘(与退出路径
                        # `if not dry_run` 口径一致), 暂停分支已在上面 continue(暂停期无变更)。
                        if not dry_run:
                            self.ctx.state.maybe_flush(time.time(), self.config.state_save_interval)
                        # 还在等真值落地 ⇒ 下一轮**立刻**再同步一次(不再等 sync_interval)。
                        # 有 TRUTH_PUSH_CAP_MS 兜底, 不会无限空转。
                        # web 真值弧单测不可达(truth_pending 仅 web 启用时非空; 26-10-02-0441)
                        if _wait_truth and getattr(self.web, "truth_pending", None):  # pragma: no cover
                            next_sync_at = time.time() + TRUTH_RETRY_S
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
                    except StopIteration as e:
                        # !必须列在 except Exception **之前**(StopIteration 是 Exception 子类): 落进
                        # 下面会被当普通异常吞掉 —— 本轮 next_sync_at/next_tick_at 未推进, wait_for
                        # 算出 0, while True 立即进下一拍再吞一次, 形成「无 sleep、无工作」的静默空转
                        # 死循环(issue 26-10-02-0442)。PEP 479 精神: StopIteration 逃出 _tick 调用链
                        # = 生成器误用 bug(裸 next()/迭代器耗尽), 属编程错误而非运行态故障 —— 静默
                        # 空转比崩溃更危险。ERROR 落日志后原样重抛: 与 AutoQbError 同为显式失败路径,
                        # 经 finally 清理(停模块/落盘/放锁)后穿透 run(), 绝不继续下一拍。
                        logger.error(f"主循环内部错误: StopIteration 逃出 _tick 调用链(疑似生成器误用): {e}", exc_info=True)
                        raise
                    except Exception as e:
                        logger.error(f"主循环异常: {e}", exc_info=True)
                        # 退避(issue 26-10-02-0728): 异常路径不推进 next_*_at —— 首轮两者是 0.0,
                        # 非首轮保持"已到期"的过去值, wait_for 恒算出 0, while True 立即进下一拍
                        # 重跑同一条线再炸一次, 形成无退避的快速重试循环(ERROR 刷屏 + CPU 空转;
                        # StopIteration 已重抛、APIConnectionError 走 _reconnect_due, 均不在此列)。
                        # 两条时间线一起推到 max(原值, now + main_tick): 失败的线最早下个节拍重试
                        # (退避起步与 _reconnect_due 口径一致); max 不把尚未到期的时间线往回拨。
                        _backoff = time.time() + main_tick
                        next_sync_at = max(next_sync_at, _backoff)
                        next_tick_at = max(next_tick_at, _backoff)
                    # 兜底: 上面任何一条线抛异常时也要把推迟的回执落掉 —— 漏写会让前端 waitCmd
                    # 干等 40s, 界面一直半透明。!**只在正常路径没跑到时才补**: 否则等真值的那些
                    # 回执会在同一轮里被 flush 两次, 日志出现两行一模一样的"另 N 条等真值落地"。
                    if not _flushed:
                        self.web.flush_truths()
                    # 等待到最近一条时间线到期, 或被命令唤醒(命令线近乎零延迟)
                    wait_for = max(0.0, min(next_sync_at, next_tick_at) - time.time())
                    if _wait_next(stop_event, self._wake_event, wait_for):
                        logger.info("收到停止信号, 退出主循环")
                        break
            except KeyboardInterrupt:
                logger.info("停止")
        finally:
            # 模块停用(plan P2): 装配逆序 stop(hr → webui → notify → logging)—— 状态落盘与
            # 锁释放是内核生命周期, 留在 stop_all 之后
            self.host.stop_all()
            if not dry_run:
                self.ctx.state.save()
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
        """应用新配置(热重载, 主循环线程经命令队列调用): 换配置对象 + 无条件广播 apply + 汇报动作

        统一挂载口(hot-reload-simplify 方向一, plan §4.3; 级别分派层与三张手写表 W4 退役):
        - R 闸留在内核: state_file/data_dir/fs 变更拒绝热应用, 返回 restart_required 提示重启;
        - L0 即换 Config 对象(运行时现读键即刻生效, ctx.config 为单一真相);
        - 其余语义全部由各模块 apply 自判: 每模块**无条件**被调, 相关段整段相等即短路
          (web 重启/HR 重挂/日志通知重挂/L2 队列与规则重建各自单点在模块);
        - qbittorrent 段变由内核自判重连(连接管理属内核, plan §3.1)。
        回执按 W4 从 levels 换 actions(各模块 ApplyResult 汇总)。
        """
        from ..config.impact import KERNEL_SECTIONS, RESTART_SECTIONS, diff_config_impacts, restart_required_paths

        changes = diff_config_impacts(self.config, config)
        restart_required = restart_required_paths(changes)
        if restart_required:
            logger.info(f"以下配置需重启进程才能生效: {restart_required}")
        # 段认领兜底(plan P6; hot-reload-simplify §3.3 规则 3): 变更段若没有任何认领面
        # (模块 sections / 内核段)覆盖, 说明新增配置键没有消费方登记 —— 保守起见 WARN +
        # 全量重建(拍板决策 3: 保守性可解释), 经 rebuild_runtime 相位由 rules 模块执行,
        # 语义与 L2 一致(全量重匹配按新配置兑现合并默认值)。认领完备时不可达
        # (守阵锁定), 这里只防认领面漂移(如模块 sections 漏登 / 装配裁剪)。
        claimed = self.host.claimed_sections() | KERNEL_SECTIONS | RESTART_SECTIONS
        unclaimed = sorted({c.path for c in changes} - claimed)
        if unclaimed:
            logger.warning(f"以下配置段变更未被任何模块认领(缺 sections 声明?), 按全量重建兜底: {unclaimed}")
        # 旧配置先留底(替换后旧对象不可达): 模块 apply 的整段对比与监听身份判定都要用
        old = self.config
        # L0: 替换配置对象(动态读取项即刻生效)
        self.config = config
        # 每模块无条件 apply, 自判短路/重启/重建 —— 「统一挂载口」的落地形态(plan §4.3)
        actions = self.host.apply_all(old, config)
        # 未认领段兜底的重建放在模块 apply 之后: 重建按**新配置**重载规则与重匹配
        if unclaimed:
            self.events.emit("rebuild_runtime", {"sections": unclaimed})
        # qb 重连(原 L1 分支的最后一项): 段变由内核自判, 不经级别表
        if old.qbittorrent != config.qbittorrent:
            self.reconnect()
        # 生命周期消息按 INFO 记(pitfalls/ops/alert-levels.md: 按配置做的动作不许用 WARNING,
        # 否则 notify 开启时每次保存配置都弹一条通知); "需重启进程"仍保留在消息文本里
        logger.info(
            f"配置热重载完成: 变更 {len(changes)} 项, 动作 {[f'{a.module}:{a.action}' for a in actions if a.action != 'none']}" +
            (f", 需重启进程: {restart_required}" if restart_required else "")
        )
        action_list = [{"module": a.module, "action": a.action, "detail": a.detail} for a in actions]
        if unclaimed:
            action_list.append(
                {
                    "module": "kernel",
                    "action": "rebuild_fallback",
                    "detail": f"未认领段: {', '.join(unclaimed)}",
                }
            )
        return {
            "applied": True,
            "actions": action_list,
            "changes": len(changes),
            "restart_required": restart_required,
        }

    def _sync_line(self, dry_run: bool, flush: bool = True, force: bool = False) -> None:
        """同步线(sync_interval 节拍): 拉 qB 增量 -> 推进快照/事件/分组 -> 视图惰性重建

        只做状态同步、**不跑任务** —— 状态新鲜度不再被任务节拍(main_tick)拖累。
        sync_interval 取 1.5s 与 qB 自带 WebUI(1500ms)同量级: 比 qB 自身数据粒度更快没有意义。

        视图那一步整体转交 webui 模块的 on_sync_line hook(plan P2): 「要不要重建」的判据
        (客户端活跃窗口 / 上一版有没有被取走)属于表现层, 不再出现在核心域。
        """
        self._refresh_torrents(dry_run)
        if flush:
            self.host.run_sync_line(force)

    def _task_line(self, dry_run: bool, force: bool = False) -> None:
        """任务线(main_tick 节拍): 执行到期任务 + 表现层收尾(错误原因预取/视图发布/搜索索引)

        tracker 预取与文件 API 批量调用**仍跟 main_tick, 不跟随快档**: 它们不是状态新鲜度的
        瓶颈, 提频只会线性放大 qB 请求量(见计划附录 A3 的五动作归档)。

        「错误原因预取」「视图发布」「搜索索引推进」都是表现层的慢路径(Tracker/文件 API),
        只在 Web 客户端活跃时才有意义 —— 门控在 webui 模块与门面里, 内核只负责在节拍上
        调 on_task_line hook(plan P2), 收尾次序(预取 -> 发布 -> 索引)是模块内聚知识。
        """
        now = time.time()

        self.task_queue.run_due(dry_run, now=now, max_tasks=self.config.max_tasks_per_tick)

        self.host.run_task_line(force)

    def _tick(self, dry_run: bool, force: bool = False):
        """完整一轮 = 同步线 + 任务线(执行与收尾统一由 TaskQueue.run_due 管理)

        主循环按节拍**分别**调度两条线(见 run); 本方法保留"同步+任务"的完整语义,
        供测试与一次性调用使用。两条线同时到期时走这里, 保证视图只重建一次。
        """
        self._sync_line(dry_run, flush=False)
        self._task_line(dry_run, force=force)

    # ---------- 全局任务 ----------

    def _create_global_tasks(self):
        """全局任务注册的内核触发口(plan P3 §7.2 兼容转发): 具体任务归各模块, 这里只广播相位

        delete_tags / speed_limit_curve 等任务的知识已迁 SpeedCurveModule / MaintenanceModule
        (start 自注册, plan §3.2), 内核不再点名。本方法只剩一个语义: 队列(可能刚被 L2 重建)
        请求各模块按当前配置注册全局任务 —— 经 EventBus 的 queue_rebuilt 相位, 已注册的模块
        幂等跳过(TaskQueue.has_named), 新队列则重新入队。run() 启动路径由 start_all 的
        模块 start() 承担, 不再经过这里; L2 分支与测试入口仍走本方法(test_web 守阵点名)。
        """
        self.events.emit("queue_rebuilt")

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

    # _hr_anchors 已迁 HrRuntime._anchors(plan §05: 门面经 ctx/store 取锚点数据,
    # 不再 getattr 窥内核私有方法); 旧名测试兼容委托已随别名层处置 W3 删除(退役名单见分诊清单)。

    def _refresh_torrents(self, dry_run: bool = False):
        """种子列表刷新(P5 收口): 增量同步 -> 按 §4.2 相位表广播 -> 数据面收尾

        内核只报「何时」: 同步完成后按相位表(plan §4.2, 现 _refresh_torrents 历史调用顺序的
        忠实编码)依次广播, 业务步骤全部由认领模块执行 —— full_round(tracker 重匹配)/
        transitions(分组状态转移)/events_removed + events_added(规则事件分派)/
        torrents_added(逐种子管线: 维护→限速→建任务→归组→集数, 由
        maintenance/tracker/rules/grouping 按装配序认领)/removed_scan(缺文件扫描)/
        post(重归组 + 冲突检查)。内核保留: schema 校验 / fs 自检(fail-fast, 兼容性职责)、
        事件重放保护窗口(总线 suppress, 仅覆盖两个事件分派相位)、
        store.update_state_snapshot / field_snapshots(数据面收尾)。

        增量同步(/sync/maindata)只取自上轮 rid 起的变化(未变化种子不出现在响应中),
        故 store 只更新变化的记录; 本轮变化集(state_changed/field_changed)供分组与
        事件分派把 O(N) 全量扫描降为 O(变化数)。
        """
        prev_records = dict(self.store.by_hash)  # 删除前快照副本(供 on_torrent_deleted 只读动作)
        added, removed = self.store.apply_sync(self.api)
        if self.store.need_validate:
            self._validate_torrent_schema(self.store.validate_sample)
            # fs.path_map 映射自检(非 fail-fast, 只记日志): 首轮全量同步后跑一次 ——
            # 挂载点存在性/可写探测 + save_path 命中率要等 store 有种子才有意义
            if not self._fs_path_map_checked:
                self._fs_path_map_checked = True
                file_access.path_map_selfcheck([rec.save_path for rec in self.store.by_hash.values()])
            # 全量轮兑现 reset_runtime 的契约: 热重载 L2 置空的 tracker_conf 在此重匹配
            # (存量记录不走 added 分支, 事件分派/维护任务都依赖 conf 已就位) —— 相位广播
            # (plan §4.2): 重匹配知识在 tracker 模块(ctx.trackers), 内核只报「全量轮」时机
            self.events.emit("full_round")
        # 分组视图过期由 store.view_changed 精确驱动(仅视图字段/成员变化时置脏), 不再每轮无条件置脏
        # 种子集变化(新增/删除) -> 搜索索引需反映新/删种子, 标记脏(Web 搜索时重建)
        if added or removed:
            self.web.mark_search_index_dirty()
        # 删除种子的删除前快照: 种子已从 store 移除后, ctx.torrent 回退此副本供只读动作留档
        removed_snapshots = {h: prev_records[h] for h in removed if h in prev_records}

        # 组内种子由上传(做种)转暂停 -> 立即触发缺文件扫描(用上一轮状态快照, 不等下一轮)。
        # 必须在本轮任何自有动作之前观测: 新增归组的大小一致性停种经快照同步会当场改写
        # by_hash 状态, 放在后面会把自家停种误判为外部"上传转暂停"。
        # 相位广播(plan §4.2): 每轮无条件 emit —— enabled 开关与缺文件扫描去重集合的
        # 按轮清零都归 grouping 模块自判
        self.events.emit("transitions", {"dry_run": dry_run})

        # 事件分派相位(plan §4.2 events_removed): on_torrent_deleted / on_torrent_state_enum_changed /
        # on_torrent_field_changed 在自有动作之前、状态快照更新之前同步即时执行(新增种子本轮
        # 不触发状态变化; added 事件在下方匹配后触发); 热重载首轮重放保护窗口在此开启。
        # 请求位(rules L2 重建挂, plan §4.3)也在此消费 —— take 即 arm, 相邻无窗(审计 M1):
        # apply_sync/full_round/transitions 抛异常的失败轮走不到这里, 请求位留待下一个成功轮,
        # 抑制跨失败轮存活(原 _suppress_events 语义); 若在轮首消费, 失败轮读走请求而旗标未挂,
        # 下一轮全量同步(rid 已失效)把存量种子全判 added, 事件规则对全库重放
        if self.events.take_suppressed():
            self.events.set_suppressed(True)
        try:
            self.events.emit(
                "events_removed",
                {
                    "removed": list(removed),
                    "snapshots": removed_snapshots,
                    "dry_run": dry_run
                },
            )

            matched_added: List[str] = []
            if added:
                logger.info(f"检测到新增种子 {len(added)} 个, 创建内置+规则任务")
                # 先为所有新增种子匹配 tracker 配置(事件分派与后续自有动作都需要; D3 服务)
                for h in added:
                    torrent = self.store.get(h)
                    if torrent is None:
                        continue
                    if torrent.tracker_conf is None:
                        torrent.tracker_conf = self.ctx.trackers.match(torrent)
                    if not torrent.tracker_conf:
                        try:
                            trackers_info = torrent.trackers_info(self.client)
                            all_domains = utils.extract_tracker_hostnames(trackers_info)
                        except Exception:
                            all_domains = []
                        logger.warning(f"种子[{h[:8]}] | 未匹配 tracker 配置, 域名: {', '.join(all_domains)}")
                        continue  # 未匹配tracker配置, 直接跳过
                    matched_added.append(h)
                # 事件分派相位(plan §4.2 events_added): on_torrent_added —— 新增种子已匹配
                # tracker 配置, 同步触发事件规则
                self.events.emit("events_added", {"added": list(matched_added), "dry_run": dry_run})
        finally:
            # 重放保护窗口关闭: 抑制仅覆盖热重载后的首轮事件分派(两个事件相位)。
            # try/finally 兜底: 窗内异常(tracker 匹配/订阅者)上抛时 live 旗标不残留,
            # 下一成功刷新轮 full_round/transitions/events_* 不被吞(坑 suppress-request-vs-live-flag,
            # live 旗标异常路径侧; emit 无逐订阅者隔离, 异常原样上抛)
            self.events.set_suppressed(False)

        # 逐新增种子管线(plan §4.2 torrents_added 相位): 维护/限速/建任务/归组/集数由
        # maintenance/tracker/rules/grouping 按装配序认领, 内核不再点名
        for h in matched_added:
            self.events.emit("torrents_added", {"hash": h, "dry_run": dry_run})

        if removed:
            # 已删种子的任务不显式清理: 由 run_due 到期执行时 handler 检测种子缺失自然消亡
            logger.info(f"检测到删除种子 {len(removed)} 个")
            # 组内种子被删除 -> 立即触发缺文件扫描(剩余种子可能文件丢失), 不等下一轮
            # (相位广播 plan §4.2 removed_scan 相位, enabled 由 grouping 模块自判)
            self.events.emit("removed_scan", {"hashes": list(removed), "dry_run": dry_run})

        # 保存路径变化重归组(文件列表变化会走新增种子重新归组) + 下载冲突检查(每轮):
        # post 相位(plan §4.2 收尾), enabled 由 grouping 模块自判
        self.events.emit("post", {"dry_run": dry_run})

        # 更新状态快照(本轮 by_hash 的状态; 新增种子本轮不视为状态变化)
        # 事件分派(on_torrent_state_enum_changed)依赖此上一轮快照对比, 故不局限于 grouping 启用时
        self.store.update_state_snapshot()
        # 字段变化基线同步刷新(事件分派 on_torrent_field_changed 的跨轮对比口径, 计划 26-09-27-1438)
        self.store.update_field_snapshots()

    def export_torrents_info(self, path):
        """导出种子信息, 用于debug"""
        torrents = self.client.torrents_info()
        # encoding 显式 utf-8: Windows 默认 cp936, 种子名含 GBK 外字符会中途崩
        # (同款见 exporter.py; issue 26-10-06-0028 chore-export-torrents-info-encoding)
        with open(path, "w", encoding="utf-8") as f:
            for tor in torrents:
                f.write(f"{tor}\n\n")
