"""WebUIRuntime: WEB UI 表现层运行时(**门面**)

把 WEB UI 的全部状态与节拍判据从 QbManager 里收出来, 使主循环不再持有、也不再判断任何
表现层细节 —— 主循环只见本对象暴露的少数语义方法(见下方「主循环接口」)。

为什么是门面而不是别的
----------------------
耦合的性质是「状态与门控」耦合: Web 侧从不通写路径, 只投递命令 + 只读快照, 边界对象早
就存在(命令队列 + 视图快照), 只是边界两侧的字段被平铺在同一个 self 上。故正解是把状态
与判据一起收走, 而不是引入事件总线(同步回调等价于直接调用, 只增加间接层)或 MVP 全套
(视图是 JSON 快照而非控件树, Presenter 的"更新控件"语义落空)。

依赖方向
--------
- **核心域 → 表现层**: 单向。主循环调本对象的门面方法; 核心域状态变化经 `mark_dirty()`
  / `mark_search_index_dirty()` 单向通知, 而不是直接写表现层的字段。
- **表现层 → 核心域**: 只有一条 —— 本对象通过 `self._host` 回调 QbManager 的写能力与
  视图**构建器**(`_cmd_*` 命令处理器 / `_build_*_view` / `store` / `api`)。构建器是纯读
  (读 store + config 产出 dict), 快照的装配、版本号与锁全部留在本对象。

线程契约(与拆分前**逐字一致**, 不得在后续改动中放松)
--------------------------------------------------
- 命令队列: Web 线程投递, 主循环线程消费 —— 写操作只在主循环线程(单一写者)。
- 视图快照: 主循环线程**发布**(持 `view_lock` 一次性替换四份视图 + 版本号),
  Web 线程**只读**;`ensure_*` 的「判脏 → 重建 → 取值」全程持锁, 保证四份视图同轮。
- `wake()` / 唤醒事件**不在这里**: 它是主循环的等待原语(托盘 UI 停止时也要用), 归核心域。

!「四视图同轮发布」是硬约束: 四份视图共用 `group_view_ver` 一个版本号回传, 任何一份漏建
或跨轮混拼, 前端都会把陈旧数组当成新数据换上去(2026-09-18 实测事故)。新增视图只挂
`_publish_locked`, 不要在调用点各建一部分。
"""
import logging
import queue
import secrets
import threading
import time
from collections import deque
from typing import Dict, List, Optional, Tuple

from .commands import (
    CMD_SLOW_MS,
    DEFERRED_RECEIPT_COMMANDS,
    RC_UNCONFIRMED_PREFIX,
    REANNOUNCE_CONFIRM_TIMEOUT,
    REANNOUNCE_JUMP_TOL,
    TRUTH_PUSH_CAP_MS,
    RESYNC_COMMANDS,
    SELF_POSTED_COMMANDS,
    _timing,
)

logger = logging.getLogger(__name__)

# Web 客户端活跃窗口: 超时无请求则主循环跳过视图组装(惰性), 关闭网页后 CPU 回落
WEB_VIEW_TTL = 10.0
# 回执保留窗口与容量上限: 前端轮询完即弃, 兜底防无界增长
WEB_RESULT_TTL = 120.0
WEB_RESULT_MAX = 64

# 真值直查(torrents/info)的分批大小: hashes 是拼在 URL 里的,
# 448 个 40 位 hash ≈ 18KB, 超多数服务端/代理的 URL 长度限制(被截断或 414) ⇒ 分批查。
TRUTH_QUERY_CHUNK = 50

# 单个 SSE 订阅者的事件队列上限: 超过就丢(慢消费者靠轮询补), 防无界增长
EVENT_QUEUE_MAX = 200
# SSE 空闲心跳间隔(秒): 必须 **< WEB_VIEW_TTL**, 否则连着的客户端会被判成不活跃
# ⇒ 主循环停止组装视图 ⇒ 推送自己也没内容可发(自锁)。
SSE_KEEPALIVE_S = 5.0
# SSE 一次性票据(查询串 ?ticket= 换票): 短 TTL + 单次消费 —— 查询串会进反代/中间层
# 访问日志, 只放短命票据, 不再放长期访问密钥(issue 26-09-21-1408 B-01)
EVENT_TICKET_TTL_S = 30.0
# 未消费票据上限: 防签发端无界堆积(签发需要凭证, 上限只是内存卫生)
EVENT_TICKET_MAX = 64

# ---- 错误历史环(WEBUI 错误历史 S2): 挂 auto_qb logger 的 WARNING+ 内存环 ----
# 容量写常量(零新配置键): 环满挤最旧, 200 条足够前端重连后补拉一段历史
WEB_ERR_RING_MAX = 200
# 单条消息截断上限: traceback 等长文案收集时压掉, 展示层不再处理
WEB_ERR_MSG_MAX = 500

# ---- 增量时间线(plan 26-10-07-0414 S2): qB 启发的自创窗口 —— deque 只存脏行键不存值(R1),
# 值回放时从当前已发布视图现取, 内存 O(代数 x 脏行键) 与库大小无关 ----
# 容量写常量(零新配置键): 40 代 ~= 60s @1.5s tick, 环满挤最旧(窗外客户端退化全量, R10)
_DELTA_TIMELINE_MAX = 40
# S3 启用矩阵(plan 26-10-07-0414): group/torrent 视图 S3 起启用; show 视图 S9b 解锁 ——
# 剧行键 = S8 剧键映射(_show_member_keys)派生, 局部重聚合按脏剧键整行重建(R8); 缺省
# (四数组)与未知 view 值仍一律 full(无视图上下文可裁剪, 保守默认)
_DELTA_VIEWS = frozenset({"group", "torrent", "show"})


def _new_delta_buckets() -> dict:
    """增量键集桶结构(plan S2): 分视图 upsert/removed 键集; show 桶 S9b 起随剧键推导填充"""
    return {
        "upsert": {
            "torrent": set(),
            "group": set(),
            "show": set()
        },
        "removed": {
            "torrent": set(),
            "group": set(),
            "show": set()
        },
    }


class WebErrLogHandler(logging.Handler):
    """auto_qb logger -> WEB 错误历史内存环(WARNING+; tray/app.py UiLogHandler 同款范式)

    emit 仅格式化 + 入环(持 runtime 的锁), 全程 try/except 静默 —— 收集器永不干扰
    业务日志; 环操作零 IO, 纯内存不进 state_file。环本体与 seq 计数器是 WebUIRuntime
    字段, handler 持引用写: 日志线程经 lock 写, Web 线程端点只读(单一写者纪律不破)。
    """
    def __init__(self, runtime: "WebUIRuntime"):
        super().__init__()
        self._runtime = runtime

    def emit(self, record: logging.LogRecord):
        try:
            if record.levelno >= logging.WARNING:
                # 多行合一(换行等空白折叠成空格)+ 截断: 收集时一次处理, 展示层不管
                msg = " ".join(str(record.getMessage()).split())
                if len(msg) > WEB_ERR_MSG_MAX:
                    msg = msg[:WEB_ERR_MSG_MAX]
                self._runtime.append_err(msg, record.levelname)
        except Exception:
            pass


class WebUIRuntime:
    """WEB UI 表现层状态 + 节拍判据 + 命令编排(主循环经门面方法调用, Web 线程经只读方法调用)"""
    def __init__(self, host):
        # host = QbManager。逆向引用只用于回调写能力与视图构建器, 不读它的表现层字段
        self._host = host
        # 控制命令队列: Web 线程投递, 主循环线程消费(写操作只在主循环线程)
        self.commands: "queue.Queue" = queue.Queue()
        # 写命令序号: 任何一条非自投递命令执行成功即自增 —— Web 线程的只读端点短缓存据此失效,
        # 避免改完立刻重取还拿到缓存里的旧值
        self.write_seq: int = 0
        # 命令执行结果回执(cmd_id -> {status, error, ts, wait_ms, exec_ms, truth})。
        # 主循环线程唯一写者, Web 线程经 /api/cmd/{id} 只读
        self.results: dict = {}
        # 强制汇报确认跟踪(cmd_id -> {items: {hash: item}}); item 形状见
        # commands._register_reannounce_pending(done/status/reason/baseline/epoch_mode/t0/deadline)
        self.reannounce_pending: dict = {}
        # 推迟汇报的后台核实(D1 早回执后半段, hash -> {min_e, baseline, epoch_mode, t0}):
        # 已受理·推迟的 item 移出回执跟踪后登记于此, 达 min_e 后每 tick 核实一次,
        # confirmed/rejected 只落日志后移除; 上限 REANNOUNCE_BACKGROUND_MAX 条(超限丢最旧),
        # 逾时(min_e + TIMEOUT)未出结论静默移除。与 reannounce_pending 同为主循环线程单写者
        # (check_pending 内推进), 不引入并发(黄金法则 5)。
        self.reannounce_background: dict = {}
        # 待推真值(cmd_id -> {cmd, args, ts}); 回执已即时发出, 这里只等真值落地再推事件
        self.truth_pending: dict = {}
        # ---- 视图快照(Web 线程只读, 发布时整体替换) ----
        self.group_view: List[dict] = []
        self.singles_view: List[dict] = []  # 未归组单种子视图
        self.flat_view: List[dict] = []  # 种子平铺视图(种子页数据源)
        self.shows_view: dict = {"list": [], "unrecognized": []}  # 追剧视图(剧→季→集)
        # 追剧视图文件兑底待解析标记: 名称无标记的种子需等搜索索引提供文件列表
        self.shows_pending: bool = False
        # 视图版本号(等价 qB 的 rid): 每次发布自增, Web 端按版本跳过整表替换。
        # 以进程启动时间播种 —— 进程重启后版本号不会回落到旧客户端已持有的值
        self.group_view_ver: int = int(time.time())
        # 快照是否过期(全部 Web 视图共享: 主循环据此惰性重建)
        self.group_view_dirty: bool = True
        # HR 判定新鲜度基线: 最近一次视图重建完成时的 hr.revision。HR 判定结果不是 store
        # 快照字段, store.view_changed 覆盖不到它, 取数线程发布新判定后靠 flush_views
        # 比对基线显式置脏(与「错误原因」预取同一判别法)。None = 尚未重建过或重建时无
        # HR 运行时; 比对端对 None 一律跳过(经 manager 现取, 判空防御)。
        self._hr_rev_at_build: Optional[int] = None
        # flush_views 上一次排空时的 store.rounds_applied: 判定「本拍是否有新应用轮」用 ——
        # S1 快照(last_added/last_removed/delta_fields)是「最近一轮」语义不排空, 无新应用轮
        # 时是残值, 不得作为纯命令源判定(本代 full)的键源(S5 镜子 fuzz 捕获)
        self._drained_sync_rounds: int = 0
        # 最近一次 Web 请求时间(活跃门控的心跳)
        self.last_seen: float = 0.0
        # 已发布但**还没被任何 /api/state 请求取走**的版本号(None = 没有"欠着"的版本)。
        # 用于把"服务端重建节拍"对齐到"客户端实际取数据的节拍": 上一版没人看就不生产下一版
        self.pending_ver: Optional[int] = None
        # 发布锁: 四份视图 + 版本号必须**同一临界区内**发布
        self.view_lock = threading.Lock()
        # 搜索索引(hash -> {name, files[文件名]}): 主循环按需构建并原子替换, Web 线程只读
        self.search_index: Optional[dict] = None
        self.search_index_dirty: bool = True
        # ---- 增量时间线(plan 26-10-07-0414 S2; qB 启发的自创窗口, R1/R2/R12) ----
        # 已发布各代的脏行键时间线: 每次发布恰追加一条目(maxlen 截断), 条目形状 =
        # {"ver": int, "full": bool, "upsert": 分视图键集, "removed": 分视图键集}。
        # 只存键不存值, 值回放时从当前已发布视图现取(R1)。写入只在 view_lock 临界区
        # (flush_views 排空 / _publish_locked 落代, 主循环线程; Web 线程的 ensure_state
        # 触发重建时也在同一把锁内), S3 的 ensure_state 归约读同一把锁 —— 不引入新锁(R12)。
        self._delta_timeline: deque = deque(maxlen=_DELTA_TIMELINE_MAX)
        # 跨拍累积器: flush_views 每拍(无论门控是否放行)排空 store 增量并入此, 落代时一次性
        # 折叠进时间线并清空 —— 门控跳拍的键集累积进下一代不丢(R4)
        self._delta_pending: dict = _new_delta_buckets()
        # full 降级理由集合(R11): 降级源在触发点登记("config_reload"/"hr_revision"/
        # "shows_pending"/"cross_group"/"row_key_unresolvable"), 落代时任一非空 -> 本代 full
        # 且累积键集清空(full 响应覆盖到当前 ver, 累积键已无意义)。mark_dirty/mark_shows_pending
        # 的登记点可能落在 Web 线程(_build_shows_view 经 ensure_state 触发路径)且不持锁:
        # 集合 add/clear 在 GIL 下原子, 竞争最坏结果是多退化一次 full, 无正确性风险
        # (与 group_view_dirty 的既有跨线程语义同一口径)。
        self._pending_full_reasons: set = set()
        # 跨组交叉键集的构建期发现(plan S2): _build_group_view 经 note_cross_keys 回传本代
        # 键集, 落代时与上一已发布代比较, 增删即本代 full(R11, 不归约旧组键)
        self._cross_keys_seen: frozenset = frozenset()
        self._cross_keys_prev: Optional[frozenset] = None  # None = 尚未发布过(首代只立基线)
        # 错误原因预取的行级脏暂存(plan S2 补, 源标签 "tracker_error_refresh"):
        # refresh_error_reasons 改写 tracker_error_msg 的受影响 hash 在改写点可得 -> 按
        # 行级归约(不走 full 降级), _publish_locked 落代前在 view_lock 内并入 _delta_pending。
        # 主循环线程写(任务线预取先于 flush_views), 竞争最坏是键集晚一代并入 —— 与
        # _pending_full_reasons 同一「无正确性风险」口径。
        self._pending_error_hashes: set = set()
        # ---- 剧键等价映射(plan 26-10-07-0414 S8): hash -> 剧键, 「上一版键」记忆 ----
        # 正确性边界 1(成员迁移: name 变化移动剧键)的实现前提, S9 按脏剧键局部重算的数据源。
        # 剧键口径 = tvshows.parse_release(rec.name).key(views._build_shows_view 现算点同款;
        # refine_with_files 的 replace 只动 kind/season/ep 不改 key, 文件兑底不影响剧键)。
        # 剧键是 parse_release 派生的表现层概念, store 只懂 hash/组 -> 收本对象而非 store;
        # 读写模式与时间线同构: 写只在 view_lock 临界区(排空段更新/清理 + 全量路径回填,
        # 主循环线程; Web 线程 ensure_state 触发的发布也在同一把锁内), R12 单一写线程不变。
        # 解析不出剧键(name 全噪音)的 hash 不登记; 映射随种子删除清理; 重启后为空, 首个
        # 全量代全库回填(_backfill_show_member_keys_locked) —— 重启后客户端本就窗外 full
        # (R10: ver 时间播种 + 时间线归零), 回填无正确性风险。
        self._show_member_keys: Dict[str, str] = {}
        # 迁移候选暂存(S8, S9b 消费): 成员迁移时「旧剧行 removed + 新剧行 upsert」的剧键集,
        # 桶结构与时间线条目的分视图桶对齐 —— S9b 在 _publish_locked 键集定型段并入 show 桶
        # (与 _pending_error_hashes 同款生命周期: 并入后清空)。两侧候选都并入 **upsert**(重建
        # 候选): 旧剧键行可能仍有其余成员(应重建为减员后的内容, 直剔会漏行), 只有重算后成员
        # 为空(_build_show_row 回 None)才转 removed。集语义幂等: 排空段残值重跑/同键反复迁移
        # 不产生重复候选; 现算命中同键零成本(parse_release 按 name lru 缓存, name 未变不产生
        # 候选)。
        self._pending_show_migrations: dict = {"upsert": set(), "removed": set()}
        # 访问密钥 / 服务器句柄(启用时确定)
        self.token: str = ""
        self.handle = None
        # 限速/流量只读快照(限速曲线任务整体替换, Web 线程只读); 未启用曲线时 state="disabled"
        self.traffic_view: dict = {"state": "disabled", "periods": [], "limit": {}}
        # 全量种子上传/下载速度合计(状态栏常显统计): 与四视图**同一临界区**发布, 随 /api/state
        # 的 status 恒回传 —— 不参与 VIEW_ARRAYS 视图分片、不受 rid 门控(状态栏是跨视图的常驻
        # 显示, 不能依赖任何一个"可能被裁掉"的数组, 见 issue 26-09-20-1646)
        self.speed_totals: dict = {"dlspeed": 0, "upspeed": 0}
        # ---- 事件推送(SSE /api/events) ----
        # 每个订阅者一个**有界**队列: 主循环侧只 put_nowait, 队列满就丢(推送是加速手段,
        # 丢了只是退化成轮询, 不是错误)。!主循环**绝不直接写 socket** —— 本项目头号教训:
        # 搜索索引单次 500 条文件 API 曾占满主循环, 导致命令排队数秒。
        self._subscribers: list = []
        self._sub_lock = threading.Lock()
        self.notify_dropped: int = 0
        # SSE 一次性票据(ticket -> 签发时刻): Web 线程签发/消费, 锁保护(端点跑在线程池)
        self._event_tickets: dict = {}
        self._event_tickets_lock = threading.Lock()
        # ---- 错误历史环(/api/errlog 数据源; 挂 auto_qb logger 的 WARNING+ 条目) ----
        # 纯内存(零磁盘触点, 不进 state_file —— 跨轮状态零新增): 日志线程经 lock 写,
        # Web 线程端点只读。seq 进程内单调递增, 重启回零 —— 客户端以 last < 已持游标
        # 判定后端重启并清空重拉, 服务端只如实返回。
        self.err_log_lock = threading.Lock()
        self.err_log_seq: int = 0
        self.err_log_ring: deque = deque(maxlen=WEB_ERR_RING_MAX)
        # 已挂 handler 引用(幂等闸: 已挂不重挂, 照 module.py start() 同款范式)
        self._err_log_handler: Optional[WebErrLogHandler] = None

    # ------------------------------------------------------------------ 事件推送

    def subscribe(self):
        """登记一个 SSE 订阅者, 返回它的事件队列(Web 线程调用)"""
        q = queue.Queue(maxsize=EVENT_QUEUE_MAX)
        with self._sub_lock:
            self._subscribers.append(q)
        # 订阅/退订都记一条 INFO: 排查"SSE 没连上 / 句柄堆叠"的第一手依据(重连时会成对出现)
        # DEBUG: 连接级事件, 重连时会成对刷屏。排查"没连上 / 句柄堆叠"时把日志级别调到 DEBUG 即可。
        logger.debug(f"WEB SSE 订阅 +1(当前 {len(self._subscribers)})")
        return q

    def unsubscribe(self, q) -> None:
        with self._sub_lock:
            if q in self._subscribers:
                self._subscribers.remove(q)
                logger.debug(f"WEB SSE 退订 -1(当前 {len(self._subscribers)})")

    def subscriber_count(self) -> int:
        with self._sub_lock:
            return len(self._subscribers)

    # ------------------------------------------------------------------ SSE 换票

    def issue_event_ticket(self) -> str:
        """签发一条 SSE 一次性票据(短 TTL); 未消费满额时回 ""(端点转 503, 前端轮询兜底)

        EventSource 发不出 Authorization 头, 前端以带鉴权的 POST /api/events/ticket 换票,
        再把票据放查询串开流 —— 查询串会进反代访问日志, 所以只放**单次消费的短命票据**,
        不再放长期访问密钥(26-10-02 加固, 取代旧 ?token= 兜底)。
        """
        now = time.time()
        with self._event_tickets_lock:
            if len(self._event_tickets) >= EVENT_TICKET_MAX:
                # 先清过期再判满额; 仍满则拒签(都是没被消费的活票, 退避比挤掉别人合理)
                expired = [t for t, ts in self._event_tickets.items() if now - ts > EVENT_TICKET_TTL_S]
                for t in expired:
                    del self._event_tickets[t]
                if len(self._event_tickets) >= EVENT_TICKET_MAX:
                    return ""
            ticket = secrets.token_urlsafe(24)
            self._event_tickets[ticket] = now
            return ticket

    def consume_event_ticket(self, ticket: str) -> bool:
        """消费票据: **取即删**(单次有效), TTL 外按无效; 重放/过期/未知一律 False"""
        with self._event_tickets_lock:
            issued_at = self._event_tickets.pop(ticket, None)
        return issued_at is not None and (time.time() - issued_at) <= EVENT_TICKET_TTL_S

    # ------------------------------------------------------------------ 错误历史(/api/errlog)

    def append_err(self, msg: str, level: str) -> None:
        """入环一条 WARNING+ 记录(日志线程经 WebErrLogHandler 调用): seq 自增, 环满挤最旧"""
        with self.err_log_lock:
            self.err_log_seq += 1
            self.err_log_ring.append({"seq": self.err_log_seq, "ts": time.time(), "level": level, "msg": msg})

    def err_log_since(self, after: int) -> Tuple[List[dict], int]:
        """只读增量(Web 线程): 回 (seq > after 的条目, 环当前最大 seq)

        after >= 当前 last 时回空列表 —— 含后端重启后客户端持旧游标的场景(seq 回零),
        重启判定在客户端(last < 游标即重启), 服务端只如实返回。
        """
        with self.err_log_lock:
            items = [e for e in self.err_log_ring if e["seq"] > after]
            return items, self.err_log_seq

    def attach_err_log_handler(self) -> None:
        """把 WebErrLogHandler 挂到 auto_qb logger(幂等: 已挂不重挂, 黄金法则 1)

        在 start_server() 里调用; 热重载重启服务器会再进 start_server, 而环与 handler
        都是进程级(不随服务器重启), 故以 _err_log_handler 引用闸防重复挂载。
        """
        if self._err_log_handler is not None:
            return
        self._err_log_handler = WebErrLogHandler(self)
        logging.getLogger("auto_qb").addHandler(self._err_log_handler)

    def notify(self, etype: str, payload: dict) -> int:
        """广播一条事件; 返回送达的订阅者数

        !必须**非阻塞**: 调用点可能在主循环线程(且 `_publish_locked` 还持有 view_lock)。
        这里只做 put_nowait, 慢消费者丢事件(它下一轮轮询会补上)。
        """
        ev = {"type": etype, "payload": payload, "ts": time.time()}
        hit = 0
        with self._sub_lock:
            subs = list(self._subscribers)
        for q in subs:
            try:
                q.put_nowait(ev)
                hit += 1
            except queue.Full:
                self.notify_dropped += 1
            except Exception:
                self.notify_dropped += 1
        return hit

    # ------------------------------------------------------------------ 活跃门控

    def is_active(self) -> bool:
        """Web 客户端是否活跃(最近一次请求距今 < WEB_VIEW_TTL)

        「Web 未启用 / 网页已关闭」在本方法里自然恒为 False —— 主循环因此不需要任何
        `if web_enabled` 分支(空对象语义): 这与拆分前 `_web_last_seen = 0` 的判据逐字等价。
        """
        return (time.time() - self.last_seen) < WEB_VIEW_TTL

    def touch(self) -> None:
        """WEB 请求心跳: 刷新 last_seen, 让主循环在活跃窗口内持续组装视图"""
        self.last_seen = time.time()

    def mark_dirty(self, full: bool = False, reason: str = "") -> None:
        """核心域 → 表现层: 视图内容已变, 下次组装前必须重建

        覆盖四份视图(groups/singles/shows/flat): 它们共享同一个版本号, 置脏必须一致 ——
        曾因只在"分组启用"分支内置脏, 导致分组关闭时另三份视图被饿死(2026-09-18 事故)。

        full=True(plan S2 R11 降级源): 本次置脏**无法归约为行级脏**(如配置热重载改写的
        配置派生展示值) —— reason 登记进 _pending_full_reasons, 落代时该代标 full 且
        累积键集清空。缺省 False: store 增量等可归约源照常推导行键。
        """
        self.group_view_dirty = True
        if full:
            self._pending_full_reasons.add(reason or "unspecified")

    def mark_search_index_dirty(self) -> None:
        """核心域 → 表现层: 种子集变化, 搜索索引需重建"""
        self.search_index_dirty = True

    def note_cross_keys(self, keys) -> None:
        """视图构建期回传跨组交叉键集(plan S2; _build_group_view 在 view_lock 临界区内调用)

        落代时与上一已发布代的键集比较, 增删即本代 full(R11): cross_group_conflict 标记
        派生自去重集合, 旧组键不归约。
        """
        self._cross_keys_seen = frozenset(keys)

    def note_error_reason_hashes(self, hashes) -> None:
        """错误原因预取的行级脏登记(plan S2 补, 源标签 "tracker_error_refresh")

        refresh_error_reasons 改写 tracker_error_msg 的受影响行键在改写点可得 -> 按**行级
        归约**(R11 不降级): _publish_locked 落代前并入 torrent/group 桶 upsert, delta 客户端
        本代即拿到这些行的新内容。主循环线程调用(任务线预取先于视图发布)。
        """
        self._pending_error_hashes.update(hashes)

    def set_traffic_view(self, view: dict) -> None:
        """限速/流量只读快照发布口(plan kernel-module-refactor P3)

        speed_curve 模块经 ctx.web 的这个服务方法推送快照, 不再跨层直写 self.traffic_view
        字段(外围绕过边界直写内核/门面私有面清零, 同 plan P1 托盘改 ctx.notify 的口径)。
        主循环线程**整体替换**引用, Web 线程只读该引用 —— 无锁即可保证读到自洽的一份。
        """
        self.traffic_view = view

    # ------------------------------------------------------------------ 主循环接口

    def consume_commands(self) -> bool:
        """消费 WEB UI 控制命令; 返回本批是否含"改了 qB 种子状态"的命令(主循环据此补刷新)

        命令带 cmd_id: 执行完立即写回执(见 results), 供前端 /api/cmd/{id} 轮询。
        例外: reannounce 只发指令并登记确认跟踪(reannounce_pending), 回执由 check_pending()
        在 tracker 确认后写入 —— "已发送"不等于"汇报成功"; bulk/add 的回执由 handler 聚合写。

        !写序号必须在写回执**之前**自增: 前端拿到回执会立刻重取只读端点(如改完分类重取
        /api/categories), 顺序反过来会让那一瞬的读命中旧写序号对应的缓存键。
        """
        host = self._host
        handlers = host._web_command_handlers()
        changed = False
        try:
            while True:
                cmd, payload = self.commands.get_nowait()
                cmd_id = str(payload.get("cmd_id") or "")
                # 下划线前缀的键是埋点/元数据, 不传给 handler(否则被当命令参数报 TypeError)
                args = {k: v for k, v in payload.items() if k != "cmd_id" and not k.startswith("_")}
                queued_ts = payload.get("_queued_ts")
                start_ts = time.time()  # 出队即开始, 用于拆 wait_ms / exec_ms
                try:
                    deferred = cmd in DEFERRED_RECEIPT_COMMANDS
                    if cmd_id and deferred:
                        handlers[cmd](cmd_id=cmd_id, **args)
                    else:
                        handlers[cmd](**args)
                    # 自投递命令不计数: 它只是内部索引推进, 且频次高, 计进去会让缓存在
                    # 建索引期间完全失效
                    if cmd not in SELF_POSTED_COMMANDS:
                        self.write_seq += 1
                    timing = _timing(queued_ts, start_ts)
                    if cmd_id and not deferred:
                        if cmd in RESYNC_COMMANDS:
                            # 改种子状态的命令: 回执**推迟到补刷新之后**再写(见 flush_truths)。
                            # 原写法在这里就写 ok, 而补刷新还在后面才跑 ⇒ 前端"拿到回执就立刻
                            # refresh"取到的必然是补刷新之前的旧快照(rid 未变), 第一次拉取 100%
                            # 扑空。推迟后第一次拉取即可命中。
                            self.defer_receipt(cmd_id, cmd, args, timing)
                        else:
                            self.set_result(cmd_id, "ok", timing=timing)
                    if cmd_id:
                        self._log_cmd_timing(cmd, timing)
                    if cmd in RESYNC_COMMANDS:
                        changed = True
                except KeyError as e:
                    logger.warning(f"WEB UI 未知命令: {e}")
                    if cmd_id:
                        self.set_result(cmd_id, "error", f"未知命令: {e}", _timing(queued_ts, start_ts))
                except Exception as e:
                    logger.error(f"WEB UI 命令执行失败: {cmd}: {e}", exc_info=True)
                    if cmd_id:
                        self.set_result(cmd_id, "error", str(e), _timing(queued_ts, start_ts))
        except queue.Empty:
            pass
        return changed

    def check_pending(self) -> None:
        """每 tick 检查在途的强制汇报确认与推迟后台核实; 某 cmd_id 全部种子出结论后聚合写回执

        逐 item 推进(判定链, 见 commands._verdict_reannounce 的五分支):
          item 级 deadline 超时 -> warn「未确认」(不再判「失败」) / store 快照 stopped 直判 ->
          qB 断连等待 / 调 _verdict_reannounce 出 confirmed(ok)/rejected(error)。
        全部 item 出结论后聚合三桶(D4=warn): 任一 error -> error; 否则任一 warn -> warn;
        全 ok -> ok, 文案「成功 X, 失败 Y, 未确认 Z: <前 3 条原因>」。
        推迟登记的后台核实(reannounce_background)同 tick 推进, 结论只落日志。
        """
        host = self._host
        if not self.reannounce_pending and not self.reannounce_background:
            return
        now = time.time()
        self._advance_reannounce_background(now)
        if not self.reannounce_pending:
            return
        store = getattr(host, "store", None)
        finished = []
        for cmd_id, entry in self.reannounce_pending.items():
            for h, it in entry["items"].items():
                if it["done"]:
                    continue
                if now >= it["deadline"]:
                    # 超时落「未确认」(warn), 不与「失败」混淆; legacy 无 epoch 字段, 只承诺
                    # 「未观测到拒绝」的诚实标签
                    tail = (
                        "旧版 qB 无 epoch 字段, 仅未观测到拒绝"
                        if not it.get("epoch_mode") else f"{REANNOUNCE_CONFIRM_TIMEOUT:.0f}s 内未观测到 epoch 前跳/在途/拒绝证据"
                    )
                    it["done"], it["status"], it["reason"] = True, "warn", RC_UNCONFIRMED_PREFIX + tail
                    continue
                if store is not None:
                    rec = store.get(h)
                    if rec is not None and rec.state_enum.is_stopped:
                        # 用户在确认窗口内暂停了种子: qB 静默忽略强制汇报, 直判免白等
                        it["done"], it["status"] = True, "warn"
                        it["reason"] = RC_UNCONFIRMED_PREFIX + "种子已停止, qB 静默忽略强制汇报"
                        continue
                if host.client is None:
                    continue  # qB 断连: 等恢复继续确认, item 级 deadline 到点落「未确认」
                try:
                    trackers = host.client.torrents_trackers(h) or []
                    state, reason = host._verdict_reannounce(
                        trackers, it["baseline"], t0=it["t0"], tol=REANNOUNCE_JUMP_TOL, now=now
                    )
                except Exception as e:
                    it["done"], it["status"], it["reason"] = True, "error", f"读取 tracker 状态失败: {e}"
                    continue
                if state == "confirmed":
                    it["done"], it["status"] = True, "ok"
                elif state == "rejected":
                    it["done"], it["status"], it["reason"] = True, "error", reason
            if all(it["done"] for it in entry["items"].values()):
                finished.append(cmd_id)
        for cmd_id in finished:
            entry = self.reannounce_pending.pop(cmd_id)
            items = list(entry["items"].values())
            ok_n = sum(1 for it in items if it["status"] == "ok")
            err_n = sum(1 for it in items if it["status"] == "error")
            warn_n = len(items) - ok_n - err_n
            msg = f"成功 {ok_n}, 失败 {err_n}, 未确认 {warn_n}"
            reasons = [it["reason"] for it in items if it["status"] != "ok" and it["reason"]]
            if reasons:
                msg += ": " + "; ".join(reasons[:3])
            if err_n:
                self.set_result(cmd_id, "error", msg)
                logger.warning(f"WEB UI | 强制汇报回执: {msg}")
            elif warn_n:
                self.set_result(cmd_id, "warn", msg)
                logger.info(f"WEB UI | 强制汇报回执: {msg}")
            else:
                self.set_result(cmd_id, "ok")
                logger.info(f"WEB UI | 强制汇报确认成功({ok_n}个种子)")

    def _advance_reannounce_background(self, now: float) -> None:
        """推进推迟登记的后台核实(D1): 达 min_e 后每 tick 读一次 trackers, 出结论只落日志

        登记面在 commands._register_reannounce_pending(已受理·推迟的 item); 本方法只消费:
        confirmed -> INFO 后移除 / rejected -> WARNING 后移除 / 逾时(min_e + TIMEOUT)未出结论
        静默移除(DEBUG)。断连 tick 跳过照旧, 逾时移除兜底(防种子被删等泄漏面, R5)。
        """
        if not self.reannounce_background:
            return
        host = self._host
        for h in list(self.reannounce_background):
            bg = self.reannounce_background[h]
            if now < bg["min_e"]:
                continue
            if now >= bg["min_e"] + REANNOUNCE_CONFIRM_TIMEOUT:
                del self.reannounce_background[h]
                logger.debug(f"WEB UI | 推迟汇报后台核实逾时移除 {h[:8]}")
                continue
            if host.client is None:
                continue
            try:
                trackers = host.client.torrents_trackers(h) or []
                state, reason = host._verdict_reannounce(
                    trackers, bg["baseline"], t0=bg["t0"], tol=REANNOUNCE_JUMP_TOL, now=now
                )
            except Exception as e:
                logger.debug(f"WEB UI | 推迟汇报后台核实读取失败 {h[:8]}: {e}")
                continue
            if state == "confirmed":
                del self.reannounce_background[h]
                logger.info(f"WEB UI | 推迟汇报后台核实已确认 {h[:8]}: {reason or 'epoch 前跳'}")
            elif state == "rejected":
                del self.reannounce_background[h]
                logger.warning(f"WEB UI | 推迟汇报后台核实失败 {h[:8]}: {reason}")

    def _drain_delta_locked(self, store) -> None:
        """把 store 本轮增量推导成脏行键并入 _delta_pending(**持 view_lock**, 主循环线程)

        映射口径(plan S2/S9b): flat/singles 行键 = hash 直用 -> torrent 桶; 组行键 =
        store.member_to_key -> group 桶(成员字段变化会改组行聚合值); 剧行键 =
        _show_member_keys(S8 剧键映射)-> show 桶。数据源 = S1 属性快照
        (last_added/last_removed) + delta_fields(变化字段集, added 不在其中)。

        组行 removed 键推导: 先查 member_to_key 后消费 removed 清单 —— 查得到: 组仍在 ->
        组行内容变了(upsert), 组已解散 -> 组行消失(removed); 查不到(组键已随
        _leave_group/解散清除, 且与「从未归组」不可区分) -> 该组行键不可归约 -> 本代
        full(R11 保守正确优先)。

        show 桶推导(plan S9b): 成员离开/成员字段变化都会改剧行聚合值(频次/季级 gaps/
        状态归并全是剧内聚合) -> 该剧键整行重建。removed 成员的**旧**剧键须在映射清理
        **前**捕获(S8 清理在后); added/delta_fields 涉及 hash 的**新**剧键在 S8 映射更新
        **后**现算 —— 两个方向都进 upsert(重建候选), 全删剧转 removed 由局部重聚合
        _build_show_row 回 None 定行止(S8 口径「候选允许过宽, 重聚合按当前库态定行止」)。
        名称解析不出剧键的 hash 不在映射 -> 无剧行, 不推导。

        同一临界区顺带更新剧键等价映射(plan S8): S1 added/delta_fields 涉及的 hash 现算
        新剧键, 键变化记迁移候选 —— 详见 _update_show_member_keys_locked。
        """
        added = store.last_added
        removed = store.last_removed
        delta_fields = store.delta_fields
        if not added and not removed and not delta_fields:
            return
        upsert = self._delta_pending["upsert"]
        rem = self._delta_pending["removed"]
        t_up, g_up = upsert["torrent"], upsert["group"]
        t_rm, g_rm = rem["torrent"], rem["group"]
        s_up = upsert["show"]
        member_to_key = store.member_to_key
        groups = store.groups
        show_keys = self._show_member_keys
        unresolvable = False
        for h in added:
            t_up.add(h)
            key = member_to_key.get(h)
            if key is not None:
                g_up.add(key)
        for h in delta_fields:
            t_up.add(h)
            key = member_to_key.get(h)
            if key is not None:
                g_up.add(key)
        for h in removed:
            t_rm.add(h)
            key = member_to_key.get(h)
            if key is not None:
                # 组仍在 -> 行内容变了(upsert); 组已解散 -> 行已消失(removed)
                (g_up if key in groups else g_rm).add(key)
            else:
                unresolvable = True
            # 旧剧键在映射清理前捕获: 成员离开 -> 该剧行内容必然变化(重建候选)
            sk = show_keys.get(h)
            if sk is not None:
                s_up.add(sk)
        if unresolvable:
            self._pending_full_reasons.add("row_key_unresolvable")
        self._update_show_member_keys_locked(store, added, delta_fields, removed)
        # 新剧键现算(S8 映射更新后): added/delta_fields 涉及 hash 的落点剧键
        for h in added:
            sk = show_keys.get(h)
            if sk is not None:
                s_up.add(sk)
        for h in delta_fields:
            sk = show_keys.get(h)
            if sk is not None:
                s_up.add(sk)

    def _update_show_member_keys_locked(self, store, added, delta_fields, removed) -> None:
        """剧键等价映射更新(plan S8, **持 view_lock**): S1 added/delta_fields 涉及的 hash
        现算新剧键并登记; 旧键存在且不同 -> 记「旧剧行 removed + 新剧行 upsert」迁移候选
        (S9 消费的暂存, 本步不进时间线 show 桶); removed 清理映射条目 —— 映射与 store
        状态同步。

        剧键口径 = tvshows.parse_release(rec.name).key, 出处 views._build_shows_view 现算
        点(views.py, 「parsed = tvshows.parse_release(rec.name)」行)—— 口径以现码为准;
        refine_with_files 不改 key(tvshows.py replace 字段集仅 kind/season/ep), 故文件
        兑底不影响剧键, 无需复刻索引兑底。局部导入同 views 同款(核心域入口按需取)。

        解析不出剧键的 hash 不登记; 已登记 hash 改名进未识别区 -> 清条目, 候选只记旧键
        一侧(新剧行不存在)。暂存只供 S9 推导脏剧键: 候选允许「过宽」—— 名称可解析但暂居
        未识别区(如季包待文件兑底)的 hash 也按 parse 键登记, 其迁移候选的旧键行可能实际
        未含该成员, S9 重聚合按当前库态定行止; 决不允许「过窄」—— 凡剧键变化的成员迁移必
        产出旧+新两侧候选。同拍增删同 hash 以删除为准(登记在先、清理在后, 与 store.by_hash
        终态一致)。
        """
        from ..core import tvshows  # 局部导入同 views._build_shows_view 同款

        mapping = self._show_member_keys
        staged = self._pending_show_migrations
        by_hash = store.by_hash

        def _register(h: str) -> None:
            rec = by_hash.get(h)  # 已删 hash(同拍增删/删除残值)现算不出键: 走清除分支
            new_key = tvshows.parse_release(rec.name).key if rec is not None else ""
            old_key = mapping.get(h)
            if old_key is not None and new_key != old_key:
                # 成员迁移(正确性边界 1): 旧剧行失去该成员 -> 旧键 removed 候选; 新名解析
                # 出剧键 -> 新剧行获得该成员 -> 新键 upsert 候选
                staged["removed"].add(old_key)
                if new_key:
                    staged["upsert"].add(new_key)
            if new_key:
                mapping[h] = new_key
            else:
                mapping.pop(h, None)

        for h in added:
            _register(h)
        for h in delta_fields:
            _register(h)
        for h in removed:
            mapping.pop(h, None)

    def _backfill_show_member_keys_locked(self, store) -> None:
        """剧键映射重启回填(plan S8, **持 view_lock**): 映射为空时全库现算登记, 全量路径
        调用(「首拍全量时回填」)。

        重启后映射空且客户端本就窗外 full(R10) —— 回填无旧键可比, 纯登记不产生迁移候选。
        非空即跳过: 运行期映射由排空段增量维护, 全库扫描只在重启后首代发生一次(全量路径
        可能因降级源反复走, 幂等)。by_hash 快照迭代同 _build_shows_view 读侧口径(发布可能
        经 Web 线程 ensure_state 触发, 主循环侧 apply 并发改库的窗口内不裸迭代)。
        """
        if self._show_member_keys:
            return
        from ..core import tvshows

        parse = tvshows.parse_release
        for h, rec in tuple(store.by_hash.items()):
            key = parse(rec.name).key
            if key:
                self._show_member_keys[h] = key

    def _merge_pending_error_hashes_locked(self) -> None:
        """错误原因预取的行级脏并入累积器(**持 view_lock**, plan S2 补)

        refresh_error_reasons 改写 tracker_error_msg 的受影响 hash 进 torrent 桶; 组行
        members 的 error_reason 随成员变化 -> 组键经 member_to_key 一并进 group 桶(与
        store 增量推导同口径)。S6 起调用点在 _publish_locked 的分叉判定前(键集须在
        构建**前**定型) —— 分叉判定需要完整键集, fold 落代段不再重跑。
        """
        error_hashes = self._pending_error_hashes
        if not error_hashes:
            return
        member_to_key = self._host.store.member_to_key
        error_upsert = self._delta_pending["upsert"]
        for h in error_hashes:
            error_upsert["torrent"].add(h)
            key = member_to_key.get(h)
            if key is not None:
                error_upsert["group"].add(key)
        error_hashes.clear()

    def _merge_pending_show_migrations_locked(self) -> None:
        """剧键迁移候选并入累积器(plan S8/S9b, **持 view_lock**)

        S8 暂存的迁移候选在键集定型段并入 show 桶(与 _merge_pending_error_hashes_locked
        同款生命周期: 并入后清空, 调用点在 _publish_locked 的分叉判定前 —— 分叉判定需要
        完整键集)。并入目标两侧统一为 **upsert**(重建候选): 暂存口径「候选允许过宽,
        重聚合按当前库态定行止」—— 旧剧键行可能仍有其余成员(须重建为减员后的内容),
        全删剧由局部重聚合 _build_show_row 回 None 转 removed; 由此「决不允许过窄」
        (凡剧键变化的成员迁移必被重算)由两侧候选都参与重建保证。
        """
        staged = self._pending_show_migrations
        if not staged["upsert"] and not staged["removed"]:
            return
        show_up = self._delta_pending["upsert"]["show"]
        show_up |= staged["upsert"]
        show_up |= staged["removed"]
        staged["upsert"].clear()
        staged["removed"].clear()

    def _fold_delta_pending_locked(self) -> None:
        """把跨拍累积的脏行键折叠成本代时间线条目并清空累积器(**持 view_lock**)

        - 每次发布恰追加一条目(maxlen 截断兜底窗口滑出; 时间线全局一份, R2)。
        - 交叉抵消(R5): 落代前分视图 upsert -= removed; removed -= upsert —— 同拍增删
          同一行净变化为零, 不给客户端又删又发同一行。
        - full 代判定(R11): 本代任一降级源活跃 -> full=true 且键集清空, 累积器与理由
          一并清空(full 响应覆盖到当前 ver, 累积键已无意义)。
        - 错误原因预取暂存已前移到 _publish_locked 的 S6 分叉判定段(构建前定型本代键集);
          交叉键集基线检查在此保留(与分叉判定段同条件幂等, 兜构建期键集竞态)。
        """
        ver = self.group_view_ver
        reasons = self._pending_full_reasons
        # 跨组交叉标记增删: 本代构建期发现的键集与上一已发布代不同 -> 本代 full
        # (首代只立基线: 时间线此前为空, 任何客户端本就窗外)
        if self._cross_keys_prev is not None and self._cross_keys_seen != self._cross_keys_prev:
            reasons.add("cross_group")
        self._cross_keys_prev = self._cross_keys_seen
        if reasons:
            entry = {"ver": ver, "full": True, **_new_delta_buckets()}
            reasons.clear()
            self._delta_pending = _new_delta_buckets()
        else:
            upsert = self._delta_pending["upsert"]
            removed = self._delta_pending["removed"]
            for view in ("torrent", "group", "show"):
                both = upsert[view] & removed[view]
                upsert[view] -= both
                removed[view] -= both
            entry = {"ver": ver, "full": False, "upsert": upsert, "removed": removed}
            self._delta_pending = _new_delta_buckets()
        self._delta_timeline.append(entry)

    def flush_views(self, force: bool = False) -> None:
        """消费视图脏标记并在 Web 活跃时惰性重建(同步线 / 任务线各自调用一次)

        `force=True` 表示"本轮有命令改了种子状态", 必须**绕过**下面的"已取走"门控 ——
        用户操作后真值要在几十毫秒内进快照, 不能因为上一版还没被取走就跳过。
        """
        host = self._host
        # 增量排空(plan S2): 每拍(无论门控是否放行)先把 store 本轮增量推导成脏行键并入
        # _delta_pending —— 门控跳拍的键集累积进下一代不丢(R4)。排空段持 view_lock: 落代
        # 折叠在 _publish_locked(可能经 Web 线程 ensure_state 触发)的同一临界区, 同锁才无
        # 并发折叠/累积竞态(R12, 不引入新锁)。last_added/last_removed 只读不排空(下轮
        # _apply 覆盖, S1「最近一轮」语义), 同拍两次 flush 重复并入同键集 —— 集合语义幂等。
        rounds_now = host.store.rounds_applied
        with self.view_lock:
            self._drain_delta_locked(host.store)
        # 本拍 store 是否提供行级键: last_added/last_removed/delta_fields 是「最近一轮」快照
        # (不排空、下轮 _apply 覆盖), 无新应用轮时是残值, 不得当作本拍键源 —— 故须同时要求
        # 本拍确有新的 _apply 轮(rounds_applied 前进)。命令自写(update_torrent_fields)/
        # reset_runtime/标签定义删除这类纯命令源不跑 _apply, 只置 view_changed
        keyed = rounds_now != self._drained_sync_rounds and bool(
            host.store.last_added or host.store.last_removed or host.store.delta_fields
        )
        self._drained_sync_rounds = rounds_now
        # store 的视图变化标记是 consume 语义(读后复位), 两条线各取一次即可完整覆盖
        if host.store.consume_view_changed():
            if keyed:
                self.mark_dirty()
            else:
                # R11: 视图须重建但行键不可推导的纯命令源 -> 本代标 full(保守正确优先)。
                # 否则落代为「空键集且 full=False」, 增量归约回空 delta, delta 客户端漏变更
                # (S3 观察缺口; S5 镜子 test_unkeyed_command_source_yields_full 钉住)。
                # store 驱动的常规轮不受影响: _apply 置 view_changed 必伴随三者之一的键。
                self.mark_dirty(full=True, reason="unkeyed_command_source")
        # HR 判定新鲜度: revision 与重建基线不等即置脏(基线在 _publish_locked 随重建前移,
        # 故只在 revision 真变的那一拍置一次, 无循环置脏)。发布侧按内容指纹去重, 不会周期空转。
        # HR 派生字段无法归约为行级脏 -> 兼登记 full 降级理由(R11)。
        hr = getattr(host, "hr", None)
        if hr is not None and self._hr_rev_at_build != hr.revision:
            self.mark_dirty(full=True, reason="hr_revision")
        web_active = self.is_active()
        # 「上一版有没有人取走」门控: 服务端节拍与客户端节拍各自独立定档, 大库下服务端
        # 生产的中间版本可能无人消费。让"生产"等一等"消费"。
        unconsumed = self.pending_ver is not None
        if self.group_view_dirty and web_active and (force or not unconsumed):
            self.rebuild_views()

    def advance_error_reasons(self) -> None:
        """任务线: 错误状态种子的具体原因预取(仅 Web 活跃时发 tracker 请求)"""
        if self.is_active():
            self._host.refresh_error_reasons()

    def advance_search_index(self) -> None:
        """任务线末尾: 搜索索引限流推进(仅 Web 活跃时), 关闭网页后不发多余的文件 API"""
        if self.search_index_dirty and self.is_active():
            self._host.build_search_index()

    def flush_truths(self) -> None:
        """直查真值, 落地了就推 `truth` 事件; 未落地继续等(上限 TRUTH_PUSH_CAP_MS)

        !**必须无条件调用**(哪怕本轮没跑补刷新): 漏调会让前端一直挂着乐观值。
        !超时**不推**: 推一个未落地的真值 = 让前端采纳命令前的旧值 ⇒ 弹回。
          那种情况交给前端超时回滚, 且必须有明确 toast(不能静默)。
        """
        if not self.truth_pending:
            return
        pending, self.truth_pending = self.truth_pending, {}
        now = time.time()
        n_push = 0
        n_wait = 0
        for cmd_id, item in pending.items():
            truth = self._affected_truth(item["cmd"], item["args"])
            landed = self._truth_landed(item["cmd"], item["args"], truth)
            if not landed and (now - item.get("ts", now)) * 1000.0 < TRUTH_PUSH_CAP_MS:
                self.truth_pending[cmd_id] = item
                n_wait += 1
                continue
            if not landed:
                logger.warning(f"[cmd] 真值超时(>{TRUTH_PUSH_CAP_MS:.0f}ms)未落地, 放弃推送: {cmd_id}")
                continue
            self.notify("truth", {"cmd_id": cmd_id, "hashes": sorted(truth or {}), "truth": truth})
            n_push += 1
        if n_push:
            # DEBUG: 一次命令一条, 常态下不必占 INFO —— 真值是否到达可从前端
            # [perf] 的 `via=push` 看出, 排查埋点归前端一处, 后端不重复刷。
            logger.debug(f"[cmd] 真值已推 {n_push} 条")
        elif n_wait:
            # 等待轮次只打 DEBUG: 真机实测一次命令要等 7~8 轮(每轮 ~200ms), 全打 INFO 会把日志
            # 刷满 —— 而这段等待现在**完全不影响观感**(压暗早已结束), 不值得占 INFO。
            logger.debug(f"[cmd] 真值未落地, 继续等 {n_wait} 条(上限 {TRUTH_PUSH_CAP_MS:.0f}ms)")

    def resync_elapsed_ms(self, t0: float) -> None:
        """命令后补刷新耗时落日志(计时口径见 qbmanager.run 的"命令驱动那一轮")

        与 set_result 里的 wait_ms / exec_ms 合起来是"点下去到真值进快照"的三段归因。
        """
        ms = round((time.time() - t0) * 1000, 1)
        # !正常耗时只打 DEBUG: 每条命令都会跑一次补刷新, 全打 INFO 会把日志刷满 ——
        #   而现在真值走直查、撤下也不再等它, 它已经不在用户可见的延迟链路上。
        #   只有**异常慢**才升到 WARNING(那时它确实会拖慢下一次视图数据的新鲜度)。
        if ms > CMD_SLOW_MS:
            logger.warning(f"[cmd] 命令后补刷新 {ms}ms —— 真值要这一轮跑完才进快照,"
                           " 前端的乐观撤下再快也得等它(大库 /sync/maindata 往返 + 四视图重建)")
        else:
            logger.debug(f"[cmd] 命令后补刷新 {ms}ms")

    # ------------------------------------------------------------------ 回执

    def set_result(
        self,
        cmd_id: str,
        status: str,
        error: str = "",
        timing: Optional[dict] = None,
        truth: Optional[dict] = None,
    ) -> None:
        """写入命令执行结果回执(主循环线程唯一写者); 顺手清理过期回执防无限增长

        timing: 埋点(wait_ms 排队等主循环 / exec_ms 执行耗时), 由 /api/cmd/{id} 一并返回。
        truth: 受影响种子的当前真值, 前端拿到即可撤下乐观态, 省掉一次全量 refresh。
        """
        now = time.time()
        if len(self.results) > WEB_RESULT_MAX:
            self.results = {k: v for k, v in self.results.items() if now - v.get("ts", 0) < WEB_RESULT_TTL}
        rec = {"status": status, "error": error, "ts": now}
        if timing:
            rec.update(timing)
        if truth:
            rec["truth"] = truth
        self.results[cmd_id] = rec
        # 事件驱动(P2): 回执**主动推**给前端, 前端不必再轮询 /api/cmd/{id}。
        # 轮询退避 0→150→300→500ms 的粒度是撤下延迟的一部分, 推送把它压到 ~1ms。
        # !必须带上 cmd_id —— 前端按它匹配自己那条命令(多个命令可能同时在途)。
        self.notify("cmd", {**rec, "cmd_id": cmd_id})

    def defer_receipt(self, cmd_id: str, cmd: str, args: dict, timing: dict) -> None:
        """回执**立即**写 + 真值登记为"稍后推"(2026-09-20 D2 定案)

        !为什么不再"扣住回执等真值": 真机实测 qB 把状态翻过来要 **1258ms**, 而命令执行
          只要 2.7ms —— 扣着回执等, 撤下就被 qB 钉死在 1.25s+(实测撤下 2947ms)。
          拆成两步:
            1. 回执立刻发(只表示"命令已执行"), 前端据此**结束压暗** ⇒ 撤下降到 10~20ms;
            2. 真值继续直查, 落地了再推 `truth` 事件, 前端据此结束"值覆盖"。
        !回执**不带 truth**: 带上未落地的真值 = 让前端采纳命令**前**的旧值 ⇒ 弹回
          (4df80dc 那条红线)。真值只走 `truth` 事件, 且只有落地了才推。
        """
        self.set_result(cmd_id, "ok", timing=timing)
        self.truth_pending[cmd_id] = {
            "cmd": cmd,
            "args": dict(args or {}),
            "ts": time.time(),
        }

    @staticmethod
    def _truth_landed(cmd: str, args: dict, truth: Optional[dict]) -> bool:
        """真值是否已**落地**(命令的效果是否已经在种子状态上体现)

        !与"命令执行成功"是两回事: `torrents/resume` 返回 200 时 qB 可能还没翻状态,
        补刷新读到的还是命令**前**的 paused。此时若把回执发出去, 回执里的真值就是旧值 ——
        前端一旦采纳就会把行改回「已暂停」, 用户看到"乐观做种 → 弹回暂停 → 2 秒后变做种"
        (2026-09-20 真机回归)。故这里在服务端**等真值落地**再发回执, 前端拿到的必然是自洽的。
        """
        if not truth:
            return True  # 取不到真值就不等(退回前端拉一次的老路径)
        act = args.get("action") if cmd == "bulk_torrents" else cmd.split("_", 1)[0]
        for v in truth.values():
            kind = (v or {}).get("kind")
            if act == "pause" and kind != "paused":
                return False
            if act == "resume" and kind == "paused":
                return False
        return True

    def _affected_hashes(self, cmd: str, args: dict) -> List[str]:
        """命令影响了哪些种子(用于回执带真值); 取不到就返回空 —— 只影响能否省一次 refresh"""
        host = self._host
        try:
            if cmd.endswith("_torrent"):
                h = (args or {}).get("hash")
                return [h] if h else []
            if cmd.endswith("_group"):
                return list(host.store.groups.get((args or {}).get("key") or (), []) or [])
            if cmd == "bulk_torrents":
                out = list((args or {}).get("hashes") or [])
                for k in (args or {}).get("keys") or []:
                    out.extend(host.store.groups.get(k, []) or [])
                return list(dict.fromkeys(out))
        except Exception:  # 桩/异常配置下取不到就退化为"不写真值", 前端照旧拉一次
            return []
        return []

    def _affected_truth(self, cmd: str, args: dict) -> Optional[dict]:
        """受影响种子的**当前真值**({hash: {"kind": ...}}) —— **直查 qB, 不读同步快照**

        !为什么必须直查(2026-09-20 定案):
          `store.by_hash` 来自 `/sync/maindata` **同步快照**, 按 qB 的节奏刷新 —— 真机实测命令后
          要等 6 轮 / **1362ms** 才在上面看到新状态(而命令本身只要 8.4ms), 这个数与
          `sync_interval = 1.5 # 与 qB 自带 WebUI(1500ms)同量级` 几乎重合 ⇒ 滞后来自快照刷新节奏。
          拿快照当"命令后的真值"就会读到命令**前**的旧值 —— 这正是"撤下要等 3s"的根源。
          改走 `torrents/info` 直查, 拿到的是 qB 的**实时**状态。

        !取不到就返回 **None（不回落快照）**: 回落会把"读不到"伪装成"读到了旧值",
          而旧值正是要消灭的东西。没有真值时前端保持乐观/等待, 语义更干净。
        """
        hashes = self._affected_hashes(cmd, args)
        if not hashes:
            return None
        want = set(hashes)
        truth: dict = {}
        try:
            # 分批: hashes 拼在 URL 里, 448 个 hash ≈ 18KB 会超长度限制(被截断/414)
            for i in range(0, len(hashes), TRUTH_QUERY_CHUNK):
                chunk = hashes[i:i + TRUTH_QUERY_CHUNK]
                for t in self._host.api.torrents_info(torrent_hashes=chunk) or []:
                    # 真机是 TorrentDictionary(有 .get/.hash); 测试桩 FakeTorrent 只有属性
                    h = getattr(t, "hash", None) or (t.get("hash") if hasattr(t, "get") else None)
                    if h in want:
                        truth[h] = {"kind": self._host.state_kind(t)}
        except Exception as e:
            logger.warning(f"[cmd] 真值直查失败(不回落同步快照): {e}")
            return None
        return truth or None

    def _log_cmd_timing(self, cmd: str, timing: Optional[dict]) -> None:
        """命令耗时落日志 —— 排查"点了要等几秒"的**主出口**(不依赖浏览器控制台)

        三段的读法(配合 resync_elapsed_ms 的补刷新那段):
          排队 wait_ms 大 = 主循环正被长任务占住(搜索索引 500 条文件 API / 任务批 / tracker 预取);
          执行 exec_ms 大 = qB API 本身慢(库大 / qB 忙 / 网络);
          补刷新大       = 命令后的强制同步慢(大库 /sync/maindata 往返)。
        """
        if not timing:
            return
        w = timing.get("wait_ms")
        e = timing.get("exec_ms")
        msg = f"[cmd] {cmd}: 排队 {w}ms / 执行 {e}ms"
        if cmd in SELF_POSTED_COMMANDS:
            logger.debug(msg + "(自投递, 不唤醒主循环)")  # 自投递频次高, 不进常规日志
            return
        if (w or 0) > CMD_SLOW_MS or (e or 0) > CMD_SLOW_MS:
            logger.warning(
                msg + f" —— 超过 {CMD_SLOW_MS:.0f}ms:"
                " 排队大=主循环被长任务占住(搜索索引/任务批/tracker 预取),"
                " 执行大=qB API 慢; 前端再快也盖不住这一段(乐观 UI 只遮住回执之前的一半)"
            )
        else:
            # !正常耗时只打 DEBUG: 每条命令都打, 全进 INFO 会把日志刷满 ——
            #   常态下的耗时看前端 `[perf]` 那一行即可(五段更全), 异常慢才由上面升 WARNING。
            logger.debug(msg)

    # ------------------------------------------------------------------ 服务器生命周期(plan P2 门面转正)

    def ensure_token(self) -> str:
        """确定访问密钥(显式配置优先, 否则随机生成并持久化到 data_dir/web.token)并落 self.token

        自 P2 起令牌生命周期内聚本门面: start_web_server 不再直写令牌字段(plan
        §05「外围绕过边界直写内核私有面」清零)。!密钥内容不进日志(server/common 契约)。
        """
        from .server.common import ensure_web_token

        self.token = ensure_web_token(self._host)
        return self.token

    def start_server(self) -> None:
        """启动 WEB 服务器(独立线程): 先确定密钥再拉起 —— 启用时的启动与热重载重启共用

        WebUIModule 是宿主侧唯一调用方(run() 的 web 启动块已退役, plan P2)。
        错误历史 handler 挂接在启动前完成(幂等, 重启不重挂)。
        """
        from . import start_web_server

        self.ensure_token()
        self.attach_err_log_handler()
        self.handle = start_web_server(self._host)

    def stop_server(self) -> None:
        """请求服务器退出(进程关停路径): 只置退出位**不等**线程

        uvicorn 每 0.1s 才读一次 should_exit, 服务线程是 daemon 随进程终灭 —— 与原 run()
        finally 的 `handle.stop()` 口径逐字一致; 只有热重载重启才需要 stop_web_server
        的"停旧并等线程退出"(见 server/lifecycle 的 10048 回归说明)。
        """
        if self.handle is not None:
            self.handle.stop()

    # ------------------------------------------------------------------ 命令投递(Web 线程)

    def post_command(self, cmd: str, payload: Optional[dict] = None) -> dict:
        """投递控制命令并生成回执 ID: 前端据 cmd_id 轮询 /api/cmd/{id} 获取执行结果

        自投递命令(SELF_POSTED_COMMANDS)**不唤醒主循环**且不带 cmd_id —— 否则会形成
        「唤醒 → drain → 索引仍脏 → 再投递」的自激循环, 打满 CPU 并冲垮 qB。
        """
        body = dict(payload or {})
        if cmd in SELF_POSTED_COMMANDS:
            # 自投递: 不入回执(没有 cmd_id), 也不带埋点 —— 它根本没有回执消费者
            self.commands.put((cmd, body))
            return {"queued": True, "cmd_id": ""}
        body["_queued_ts"] = time.time()  # 埋点: 投递时刻, 回执据此拆出排队耗时
        cmd_id = secrets.token_hex(8)
        body["cmd_id"] = cmd_id
        self.commands.put((cmd, body))
        self._host.wake()  # 唤醒主循环立即消费(命令延迟从 0~main_tick 降到近乎 0)
        return {"queued": True, "cmd_id": cmd_id}

    # ------------------------------------------------------------------ 视图发布 / 读取

    def rebuild_views(self) -> None:
        """重建全部视图快照并自增版本号 —— **唯一**的重建入口(主循环侧)"""
        with self.view_lock:
            self._publish_locked()

    def _publish_locked(self) -> None:
        """重建四视图并发布 —— **调用方必须持有 view_lock**

        与 rebuild_views 分离, 使"判脏 → 重建 → 读取"能在**同一个临界区**内一次完成
        (见 ensure_view); 若拆成"加锁重建 / 释放 / 再加锁读", 中间仍可能被另一线程插入
        一次重建, 读到的四份视图依旧不属于同一轮。

        S6/S9b 分叉(plan 26-10-07-0414): 本代无 full 降级理由且有净键可归约 -> 局部重聚合
        (_publish_partial_locked, 未脏行对象引用原样保留; S9b 起 show 视图按脏剧键整行
        重建); full 理由/HR 波次/无键 -> 走原全量路径(四视图整体重建, 行为与 S6 之前逐字段
        一致)。应急回退(不 revert): 分叉判定恒为假(把下面的 if 条件整个换成 False)即回
        纯全量 —— 单行改动。
        """
        host = self._host
        # ---- 本代键集定型(原属 _fold_delta_pending_locked 的前置段前移到构建前, S6) ----
        # 错误原因暂存并入: 分叉判定需要完整键集, 该源比 store 增量键集(排空在 flush_views
        # 开头)更及时, 并入点仍在 view_lock 临界区内(R12 不变)。
        self._merge_pending_error_hashes_locked()
        # 剧键迁移候选并入(plan S9b): S8 暂存的旧/新剧键统一作重建候选, 生命周期同上
        self._merge_pending_show_migrations_locked()
        # 交叉键集基线检查前移: 直接从 store 现算(与构建期 note_cross_keys 同源同值),
        # 增删即本代 full(R11) —— 局部重聚合无法修正未脏组行的 cross 标记, 必须先判定。
        cross_keys = host._cross_keys_snapshot()
        if self._cross_keys_prev is not None and cross_keys != self._cross_keys_prev:
            self._pending_full_reasons.add("cross_group")
        self.note_cross_keys(cross_keys)  # 局部路径不经 _build_group_view, 基线在此统一前移
        # R5 交叉抵消前移: 分叉判据是抵消后的净键集(fold 落代段重跑一遍, 幂等)
        upsert = self._delta_pending["upsert"]
        removed = self._delta_pending["removed"]
        for bucket in ("torrent", "group", "show"):
            both = upsert[bucket] & removed[bucket]
            upsert[bucket] -= both
            removed[bucket] -= both
        # 未识别折叠面变化检测(plan S9b, R11): 增量协议没有未识别桶(S4 前端 delta 轮对
        # unrecognized「不动」, 只在 full 轮整表替换) -> 折叠成员增删不可归约为行级脏,
        # 本代标 full(保守正确优先)。判定用全量分类同款口径(_parse_show_member 解析+
        # 兑底): 「现分类未识别」≠「原居折叠区」即折叠面变化 —— 精确不放大, 静止未识别
        # 种子(如下载中的电影)速度抖动不触发。parse_release 按 name lru 缓存, 排空段已
        # 现算过同一批名字 -> 此处缓存命中, 增量成本可忽略(远廉于 S9b 前每拍全量重扫)。
        if upsert["torrent"] or removed["torrent"]:
            from ..core import tvshows as _tvshows

            _store = host.store
            index = self.search_index or {}
            old_unrec = set(self.shows_view["unrecognized"])
            unrec_changed = False
            for h in upsert["torrent"]:
                rec = _store.by_hash.get(h)
                if rec is None:
                    continue  # 已删 hash: 折叠面归 removed 分支判定
                _, parsed, _ = host._parse_show_member(rec, (index.get(h) or {}).get("files"))
                if (parsed.kind == _tvshows.KIND_UNKNOWN or not parsed.key) != (h in old_unrec):
                    unrec_changed = True  # 新进/离开折叠区(含改名与兑底归位两侧)
                    break
            if not unrec_changed:
                unrec_changed = any(h in old_unrec for h in removed["torrent"])
            if unrec_changed:
                self._pending_full_reasons.add("show_unrecognized")
        # HR 波次判定(flush_views 同款): ensure_state 触发的发布不经 flush 的判定点,
        # 局部重聚合只刷新脏行的 HR 派生字段, 波次未捕获会让未脏行的 HR 字段永久陈旧
        hr = getattr(host, "hr", None)
        hr_wave = hr is not None and hr.revision != self._hr_rev_at_build
        has_keys = bool(
            upsert["torrent"] or upsert["group"] or upsert["show"] or removed["torrent"] or removed["group"] or
            removed["show"]
        )
        partial = not self._pending_full_reasons and not hr_wave and has_keys
        if partial:
            self._publish_partial_locked(upsert, removed, cross_keys)
        else:
            old_show_keys = {r["key"] for r in self.shows_view["list"]}
            self.group_view = host._build_group_view()
            self.singles_view = host._build_singles_view()
            self.shows_view = host._build_shows_view()
            self.flat_view = host._build_flat_view()
            # 速度合计与四视图同一快照、同一临界区发布(状态栏据此与行数据同源同轮)
            self.speed_totals = host._build_speed_totals()
            # 剧键映射回填(plan S8): 重启后首个全量代全库登记(映射非空即跳过, 幂等)
            self._backfill_show_member_keys_locked(host.store)
            # show 桶时间线按现视图行止校准(plan S9b): 重建候选中已无剧行的键(迁移旧键
            # 成员迁空等)—— 原居旧视图的转 removed(客户端按它删行), 从未有过行的纯未识别
            # 键只撤候选不产生 removed 噪音; 免得后续归约对缺失行防御性 full
            gone = upsert["show"] - {r["key"] for r in self.shows_view["list"]}
            if gone:
                upsert["show"] -= gone
                removed["show"] |= gone & old_show_keys
        self.group_view_ver += 1
        self.group_view_dirty = False
        # 记下"这一版还没被任何 /api/state 请求取走" —— 主循环据此不再生产下一版(节拍对齐)
        self.pending_ver = self.group_view_ver
        # 增量时间线落代(plan S2): 跨拍累积的 _delta_pending 与本代 full 理由折叠成条目
        # 追加进时间线 —— 每次发布恰一条(R4 累积/R5 抵消/R11 降级/R12 临界区)
        self._fold_delta_pending_locked()
        # 事件驱动(P2): 新版本**主动推**信号(只推版本号, 绝不推数据 —— 3000 种子一轮
        # 全量要 63ms 序列化+网络+解析, 频繁推会把主线程打满)。前端据此触发一次 refresh。
        self.notify("ver", {"ver": self.group_view_ver})
        # 重建完成记 HR 判定新鲜度基线: 经 manager 现取 + 判空 —— 无 HR 运行时(测试桩/
        # 未装配)记 None, 比对端同样跳过, 不得在重建路径抛 AttributeError。
        # 全量路径基线恒前移(revision 已随全量重建落地, 不前移会让 flush 的波次判定
        # 每拍置脏 -> 无限 full 循环); 局部重聚合路径基线**只在 revision 仍等于旧基线时**
        # 前移(值不变即无操作): 若构建期间波次又动了(跨线程登记竞态), 保留旧基线让下一拍
        # flush 的波次判定补一次 full —— 否则基线前移会吞掉波次, 未脏行的 HR 字段永久陈旧。
        if hr is None:
            self._hr_rev_at_build = None
        elif not partial or hr.revision == self._hr_rev_at_build:
            self._hr_rev_at_build = hr.revision

    def _publish_partial_locked(self, upsert: dict, removed: dict, cross_keys: set) -> None:
        """局部重聚合(plan S6/S9b): 仅对本代 upsert/removed 行键重跑构建 —— **调用方必须持有 view_lock**

        不变量(plan S6/S9b 核心):
        - 未脏行**对象引用原样保留**(同一 dict), 脏行必然新对象 —— 引用稳定只对未脏行承诺,
          前端 S7 按行对象身份的 WeakMap 记忆化依赖这一点;
        - 「四视图同轮发布」硬约束(模块 docstring)不破: 数组仍整体一次性替换, 行对象按
          未脏/脏区别复用/新建, 不在调用点分批建;
        - 组行内嵌 members 数组随组行整行走(P-02 一期口径); singles/flat 脏行按 hash 逐行
          重建(便宜); removed 键直接从视图剔除(与全量构建不产已删行/空组行对齐);
        - show 行(S9b): 脏剧键经 _show_member_keys 反查成员集 -> 逐成员 _parse_show_member
          重解析 -> _build_show_row 重调出**整行** upsert(R8; 剧名频次/季级 gaps/集行状态
          归并全随整行重算, 正确性边界 2-4 落位); 重算成员为空(全删/迁移旧键清空)-> 行
          消失转 removed(对齐 _build_group_row 空组口径);
        - 脏行重算必须与全量重跑该行逐字段一致(S6/S9b 单测钉住; S5 镜子兜整体等价)。
        """
        host = self._host
        store = host.store
        from ..infra import utils as _utils

        # ---- groups: 脏组键整行重建(members 随行), 未脏组行复用, removed 组键剔除 ----
        enc_rm = {_utils.encode_group_key(k) for k in removed["group"]}
        rebuilt: dict = {}
        for k in upsert["group"]:
            members = store.groups.get(k) or ()
            recs = [store.by_hash[h] for h in members if h in store.by_hash]
            row = host._build_group_row(k, recs, cross_keys)
            if row is not None:  # 组已空/已解散 -> 行消失(全量构建跳过空组, 产物对齐)
                rebuilt[_utils.encode_group_key(k)] = row
        group_view = []
        for old in self.group_view:
            k = old["key"]
            if k in enc_rm:
                continue
            # 脏行换新对象(rebuilt.pop 顺带把替换过的键清出, 残余即新增组行)
            group_view.append(rebuilt.pop(k) if k in rebuilt else old)
        group_view.extend(rebuilt.values())  # 新组行追加在尾部(前端排序不依赖数组顺序)

        # ---- singles: torrent 桶脏行中未归组的按 hash 逐行重建(_member_view 口径) ----
        # 归组判定与 _build_singles_view 同款(groups 值并集, 不用 member_to_key —— 与
        # 全量构建的分类口径严格一致)
        grouped = set()
        for members in tuple(store.groups.values()):
            grouped.update(members)
        new_singles: dict = {}
        for h in upsert["torrent"]:
            if h not in grouped:
                rec = store.by_hash.get(h)
                if rec is not None:
                    new_singles[h] = host._member_view(rec)
        singles_view = []
        for old in self.singles_view:
            h = old["hash"]
            if h in removed["torrent"]:
                continue
            singles_view.append(new_singles.pop(h) if h in new_singles else old)
        singles_view.extend(new_singles.values())  # 新落地 singles(如成员脱离组)追加在尾部

        # ---- flat: torrent 桶脏行按 hash 逐行重建(_seed_view 口径) ----
        new_flat: dict = {}
        for h in upsert["torrent"]:
            rec = store.by_hash.get(h)
            if rec is not None:
                new_flat[h] = host._seed_view(rec)
        flat_view = []
        for old in self.flat_view:
            h = old["hash"]
            if h in removed["torrent"]:
                continue
            flat_view.append(new_flat.pop(h) if h in new_flat else old)
        flat_view.extend(new_flat.values())  # 新增种子行追加在尾部(全量构建同按入库序在尾)

        # ---- shows: 脏剧键整行重建(plan S9b), 未脏剧行复用, 全删剧转 removed 剔除 ----
        show_up = upsert["show"]
        show_rm = removed["show"]
        new_shows: dict = {}
        old_show_keys = {r["key"] for r in self.shows_view["list"]}
        if show_up:
            from ..core import tvshows

            index = self.search_index or {}
            by_hash = store.by_hash
            # 成员集反查(plan S9: 脏剧键经 _show_member_keys 取该剧成员 hash 集): 单次扫描
            # 只收脏剧键的成员 —— 映射规模 = 名称可解析的种子数, dict 扫描远廉于全库
            # parse_release(S9 的收益点)。映射口径比全量分类「宽一档」(S8: 名称可解析但
            # 暂居未识别区/待兑底的 hash 也登记) -> 成员逐个过 _parse_show_member 重分类,
            # 现分类未识别的(KIND_UNKNOWN, 如电影)剔除出剧行 —— 与全量分类产物对齐。
            want = set(show_up)
            members_by_key: dict = {}
            for h, k in self._show_member_keys.items():
                if k in want and h in by_hash:
                    members_by_key.setdefault(k, []).append(h)
            parse_member = host._parse_show_member
            build_row = host._build_show_row
            pending: List[str] = []
            for k in list(show_up):  # 快照迭代: 行止转换要写回原集合(fold 读同一对象)
                members = []
                for h in members_by_key.get(k) or ():
                    rec = by_hash.get(h)
                    if rec is None:  # 映射残值防御(理论不可达: 映射随删除清理)
                        continue
                    rec, parsed, is_pending = parse_member(rec, (index.get(h) or {}).get("files"))
                    if is_pending:
                        pending.append(h)  # 可兑底而索引未覆盖(全量同款: 未识别形态也计)
                    if parsed.kind == tvshows.KIND_UNKNOWN or not parsed.key:
                        continue  # 未识别折叠区不进剧行(全量分类同口径, 折叠面由检测器兜)
                    members.append((rec, parsed))
                row = build_row(k, members)
                if row is not None:
                    new_shows[k] = row
                elif k in old_show_keys:
                    # 剧已无(可分类)成员(全删/迁移旧键清空): 行消失 -> 转 removed
                    # (对齐 _build_group_row 空组口径; 改动进本代时间线条目)
                    show_up.discard(k)
                    show_rm.add(k)
                else:
                    # 从未有过剧行(纯未识别键等): 仅撤重建候选, 不产生 removed 噪音
                    show_up.discard(k)
            # 文件兑底接线(与 _build_shows_view 同款): 脏成员中可被兑底而索引未覆盖 -> 登记
            # pending 并按需投递构建命令。False 归位转换刻意不在局部路径判定: 非脏成员的
            # pending 状态此处不可见, 误归位会丢「索引建成 -> 整季重解析」的重建触发
            # (归位拍由索引推进的 _trigger_shows_rebuild_if_pending 或下一个全量代兜住)
            pending = [h for h in pending if h not in index]
            if pending:
                self.mark_shows_pending(True)
                if self.search_index_dirty or self.search_index is None:
                    self.post_command("build_search_index")
        shows_list = []
        for old in self.shows_view["list"]:
            k = old["key"]
            if k in show_rm:
                continue
            shows_list.append(new_shows.pop(k) if k in new_shows else old)
        shows_list.extend(new_shows.values())  # 新剧行追加在尾部(前端排序不依赖数组顺序)
        # 未识别折叠面原样保留: 折叠面变化已被 _publish_locked 的 show_unrecognized 检测
        # 拦为 full 代(R11, 协议无未识别桶), 走到这里的局部代折叠成员必与上一代一致
        shows_view = {"list": shows_list, "unrecognized": self.shows_view["unrecognized"]}

        # ---- 发布: 数组整体一次性替换(硬约束); speed_totals 无行键可归约, 仍现算 ----
        self.group_view = group_view
        self.singles_view = singles_view
        self.flat_view = flat_view
        self.shows_view = shows_view
        self.speed_totals = host._build_speed_totals()

    def ensure_view(self) -> List[dict]:
        """WEB 线程调用: 确保分组视图最新——过期则立即重建(Web 请求触发), 否则返回当前引用

        与主循环惰性组装配合; 全程持锁保证"判脏 → 重建 → 读取"不被另一线程的重建插入。
        """
        with self.view_lock:
            if self.group_view_dirty:
                self._publish_locked()
            return self.group_view

    def ensure_state(self, rid: Optional[int], view: Optional[str] = None, delta: bool = False) -> dict:
        """WEB 线程调用: 带版本号的合并状态(前端按 rid 跳过整表替换与重渲染)

        rid 与服务端视图版本一致时**不回传任何数组**(响应体趋近于零)。status 体积极小,
        无关版本恒回传, 以保证连接状态 / 暂停状态 / 种子数变化能即时反映。

        **按视图回传**: view 指定当前视图时只回传该视图需要的数组(见 VIEW_ARRAYS), 响应体
        降到约 1/4。四视图仍共享同一版本号 —— 切视图时前端把 lastRid 置空强制取一次全量。

        **增量归约**(plan 26-10-07-0414 S3/S9b): 双重门控后才走归约分支 ——
        ①协商: 请求带 delta=1(路由层解析)才允许归约, 未带协商参数的请求**不进归约**,
        响应与历史版本逐字节等价(无 full 键)—— S3 与 S4 各自独立提交/回滚的兼容闸
        (P-01 定案: 未升级前端把增量载荷当全量吃会四数组 undefined 白屏);
        ②启用矩阵: view ∈ _DELTA_VIEWS(group/torrent/show); 缺省与未知值一律 full(无视图
        上下文可裁剪)。归约判定详见 _reduce_delta; 窗外/窗内含 full 代/防御检查不过时
        (R10)回落全量并标 full: true。
        """
        from .views import VIEW_ARRAYS

        with self.view_lock:
            if self.group_view_dirty:
                self._publish_locked()
            ver = self.group_view_ver
            # 本请求观察到了 ver ⇒ 这一版已被消费, 允许主循环生产下一版(节拍对齐的另一半)
            self.pending_ver = None
            updated = rid != ver
            state: dict = {"rid": ver, "updated": updated}
            if not updated:
                # 「零回传」: 版本一致只回 rid, 增量协商也不改变本分支(plan S3 保留 :828 语义)
                return state
            if delta and view in _DELTA_VIEWS:
                reduced = self._reduce_delta(rid, view)
                if not reduced.get("full"):
                    # 归约命中: rid(== ver)/full=False/delta/removed 四键并入(键名对齐 qB 命名法)
                    state.update(reduced)
                    return state
            # 全量分支(原路径): 协商客户端按协议标 full=true(不含 delta/removed 键, R10);
            # 未协商客户端**不加** full 键 —— 与 S3 之前的历史响应逐字节等价(独立提交安全)
            if delta:
                state["full"] = True
            arrays = {
                "groups": self.group_view,
                "singles": self.singles_view,
                "shows": self.shows_view,
                "torrents": self.flat_view,
            }
            keys = VIEW_ARRAYS.get(view) if view else None
            for k in keys or arrays:
                state[k] = arrays[k]
        return state

    def _reduce_delta(self, rid: int, view: str) -> dict:
        """把 (rid, ver] 窗口内的时间线归约为该视图的增量载荷(**调用方必须持有 view_lock**)

        判定顺序(plan 26-10-07-0414 S3, R3/R10; 协商与启用矩阵已在 ensure_state 门控):
          1. rid 缺省/0 / rid > ver(时钟倒挂) / rid < 时间线最旧代次(窗口滑出或尚未落代)
             -> 全量(R3: 数值区间比较, 不做 qB 式等值 ack/回绕);
          2. 窗口内任一代 full -> 全量(R11: full 代键集已清空, 键集链断裂);
          3. rid == ver(「零回传」)不进本函数(ensure_state 先行短路);
          4. 否则归约: upsert = 窗口内各代该视图 upsert 并集; removed = removed 并集 -
             最终 upsert(R5 跨代版: 后又改回的行让位, 回 upsert 不回 removed); 行内容现取
             自当前已发布视图(R1 时间线只存键不存值)。upsert 行必须存在于当前视图 ——
             不存在(跨代先增后删被 R5 抵消后的残留 upsert 等)即防御性转全量。

        返回 {"full": True} 或 {"rid": ver, "full": False, "delta": {...}, "removed": {...}}。
        delta/removed 的内层桶按该视图实际数组构成裁剪(与全量分支同款 VIEW_ARRAYS 裁剪),
        恒在、可为空。应急语义回退(不 revert): 本方法首行加 `return {"full": True}` 即回
        今天的行为(full 语义常驻)。
        """
        ver = self.group_view_ver
        # R3: rid 数值区间比较。缺省/0 与 >ver 都不可归约(后者含进程重启后旧客户端持未来 rid)
        if not rid or rid > ver:
            return {"full": True}
        timeline = self._delta_timeline
        # 时间线为空(尚未落代/重启归零)或最旧代次已越过 rid(环满滑出) -> 窗外全量(R10)
        if not timeline or rid < timeline[0]["ver"]:
            return {"full": True}
        window = [e for e in timeline if e["ver"] > rid]
        if any(e["full"] for e in window):
            return {"full": True}  # 窗内任一代 full: 键集链断裂, 只能全量(R10/R11)
        up_t: set = set()
        up_g: set = set()
        up_s: set = set()
        rm_t: set = set()
        rm_g: set = set()
        rm_s: set = set()
        for e in window:
            up_t |= e["upsert"]["torrent"]
            up_g |= e["upsert"]["group"]
            up_s |= e["upsert"]["show"]
            rm_t |= e["removed"]["torrent"]
            rm_g |= e["removed"]["group"]
            rm_s |= e["removed"]["show"]
        # R5 跨代版: removed 让位于后续 upsert(同键先删后改 = 行还在, 回 upsert)
        rm_t -= up_t
        rm_g -= up_g
        rm_s -= up_s
        from ..infra import utils as _utils
        from .views import VIEW_ARRAYS

        # 行内容现取自当前已发布视图(R1); upsert 行必须存在, 缺行即防御性转全量(见 docstring)。
        # 平铺视图含 store 全量 -> torrent 桶 upsert 的每一行都必须在 flat_view 里(三个视图通用)
        flat_rows = [r for r in self.flat_view if r["hash"] in up_t]
        if len(flat_rows) != len(up_t):
            return {"full": True}
        group_rows: list = []
        if up_g:
            enc_up = {_utils.encode_group_key(k) for k in up_g}
            group_rows = [r for r in self.group_view if r["key"] in enc_up]
            if len(group_rows) != len(up_g):
                return {"full": True}  # 组行已不在当前视图(跨代先改后解散的残留 upsert)
        show_rows: list = []
        if up_s:
            show_rows = [r for r in self.shows_view["list"] if r["key"] in up_s]
            if len(show_rows) != len(up_s):
                return {"full": True}  # 剧行已不在当前视图(全删转 removed 的跨代残留 upsert)
        # delta/removed 内层桶按该视图实际数组构成裁剪(与全量分支同款 VIEW_ARRAYS;
        # S9b 起 view=show 启用, delta.shows 回剧行/removed.shows 回剧键)
        keys = VIEW_ARRAYS.get(view) or ()
        delta: dict = {}
        removed: dict = {}
        if "torrents" in keys:
            delta["torrents"] = flat_rows
            removed["torrents"] = sorted(rm_t)
        if "groups" in keys:
            delta["groups"] = group_rows
            # 组行键回 encode 后的字符串(与视图行 r["key"] 同标识, 前端按它删行)
            removed["groups"] = sorted(_utils.encode_group_key(k) for k in rm_g)
        if "singles" in keys:
            # singles 行 = torrent 桶 upsert 中未归组的行(归组行的变更只落在 groups 桶);
            # 未归组行必须存在于当前 singles 视图, 缺行即防御性转全量
            member_to_key = self._host.store.member_to_key
            ungrouped = {h for h in up_t if h not in member_to_key}
            if ungrouped:
                singles_hashes = {r["hash"] for r in self.singles_view}
                if not ungrouped <= singles_hashes:
                    return {"full": True}
            delta["singles"] = [r for r in self.singles_view if r["hash"] in up_t]
            # removed.singles 回全部已删 hash(保守多删: 客户端删不存在的行是幂等 no-op,
            # 漏删才会留幽灵行 —— 已删行归没归过组在删除点之后已不可靠)
            removed["singles"] = sorted(rm_t)
        if "shows" in keys:
            delta["shows"] = show_rows
            # 剧行键 = parse_release 派生的剧键字符串(与视图行 r["key"] 同标识, 前端按它删行)
            removed["shows"] = sorted(rm_s)
        return {"rid": ver, "full": False, "delta": delta, "removed": removed}

    def mark_shows_pending(self, pending: bool) -> None:
        """追剧视图文件兑底标记: 索引推进后由构建器据此置脏重建

        True->False 归位拍登记 full 降级理由(plan S2 R11): 集行此前按名称解析展示,
        文件兑底后剧/季/集结构可能整体重组, 无法归约为行级脏 -> 本代 full。
        """
        was = self.shows_pending
        self.shows_pending = pending
        if was and not pending:
            self._pending_full_reasons.add("shows_pending")
