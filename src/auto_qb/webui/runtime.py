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

import queue
import threading
from collections import deque
from typing import TYPE_CHECKING, Dict, List, Optional

from ..infra.clock import SYSTEM_CLOCK, Clock
# re-export 供测试经本门面取(commands 拆分后本文件不再直接使用): test_web_longtail_* 五个
# 文件从这里连同 EVENT_QUEUE_MAX/WEB_RESULT_*/WebUIRuntime 一把导入, 改指向 .commands 动面更大
from .commands import CMD_SLOW_MS, REANNOUNCE_CONFIRM_TIMEOUT
from .runtime_commands import CommandsMixin
from .runtime_common import (
    EVENT_QUEUE_MAX,
    EVENT_TICKET_MAX,
    EVENT_TICKET_TTL_S,
    SSE_KEEPALIVE_S,
    TRUTH_QUERY_CHUNK,
    WEB_ERR_MSG_MAX,
    WEB_ERR_RING_MAX,
    WEB_RESULT_MAX,
    WEB_RESULT_TTL,
    WEB_VIEW_TTL,
    WebErrLogHandler,
    _DELTA_TIMELINE_MAX,
    _DELTA_VIEWS,
    _cancel_delta_buckets,
    _new_delta_buckets,
    logger,
    public_traffic_view,
)
from .runtime_stream import StreamMixin
from .runtime_views import ViewsMixin

if TYPE_CHECKING:
    from .server.lifecycle import WebServerHandle


class WebUIRuntime(ViewsMixin, CommandsMixin, StreamMixin):
    """WEB UI 表现层状态 + 节拍判据 + 命令编排(主循环经门面方法调用, Web 线程经只读方法调用)"""
    def __init__(self, host, clock: Optional[Clock] = None):
        # host = QbManager。逆向引用只用于回调写能力与视图构建器, 不读它的表现层字段
        self._host = host
        # 取时注入(D8): 视图版本播种 / 回执与票据时间戳 / TTL 门控用挂钟; 缺省单点经模块
        # 属性现取(测试可 monkeypatch 本模块 SYSTEM_CLOCK 或构造期传假钟)
        self._clock = SYSTEM_CLOCK if clock is None else clock
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
        self.group_view_ver: int = int(self._clock.now())
        # 搜索数据版本号(plan 26-11-03-0120 S1): 搜索相关数据(增删 / name/category/
        # save_path/tags 变化 / full_round)一变化就在主循环自增一次; 随 /api/state 恒回传,
        # 前端发现手上的结果版本落后就静默重查。以启动毫秒播种 —— 服务重启后旧页面版本
        # 几乎必然不等, 天然触发一次自愈刷新; 只自增, 不清理、不落盘(搜索词本就不持久化)。
        self.search_rev: int = int(self._clock.now() * 1000)
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
        #
        # 门控去留裁决(plan 26-10-07-0414 P-03, S10 定案): **保留不动**。增量落地后其保护
        # 对象从「全量重建成本」缩水为「一次键集追加」—— 门控跳拍的脏键由 _delta_pending
        # 累积进下一代不丢(R4), 跳拍轮在时间线上不留空洞; 保留无害且保守(黄金法则 2),
        # 移除只剩简化收益、没有正确性收益, 且会同时改变现有节拍行为。若实测确认纯冗余,
        # 另立独立小步移除, 届时单独拍板。
        # 消费动态(issue 26-09-19-2122 方案 B 口径): SSE 主路径上客户端每版必拉, 本字段
        # 恒即刻被清, 门控等效失效; 只在轮询兜底路径(SSE 断线/不支持)上起作用 —— 重建
        # 总次数由消费率决定, 与门控无关。清账入口有二: ensure_state / ensure_view(同款
        # 「消费即清」), /api/groups 的消费方此前不清账, 已对齐(issue 顺带小修)。
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
        # 行级展示派生字段的行级脏暂存(plan S2 补, 源标签 "tracker_error_refresh"):
        # refresh_tracker_health 改写 tracker_error_msg / tracker_health_msg 的受影响 hash
        # 在改写点可得 -> 按
        # 行级归约(不走 full 降级), _publish_locked 落代前在 view_lock 内并入 _delta_pending。
        # 主循环线程写(任务线预取先于 flush_views), 竞争最坏是键集晚一代并入 —— 与
        # _pending_full_reasons 同一「无正确性风险」口径。
        self._pending_error_hashes: set = set()
        # ---- 剧键等价映射(plan 26-10-07-0414 S8): hash -> 剧键, 「上一版键」记忆 ----
        # 正确性边界 1(成员迁移: name 变化移动剧键)的实现前提, S9 按脏剧键局部重算的数据源。
        # 剧键口径 = tvshows.parse_release(rec.name).key(views._build_shows_view 现算点同款;
        # refine_with_files 的 replace 只动 kind/season/ep(+ season_inferred 留痕位)不改 key,
        # 文件兑底不影响剧键)。
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
        # 显式 Optional 注解: StreamMixin.start_server 侧赋值 start_web_server() -> WebServerHandle,
        # 本处初值 None —— 不标注会被 mypy 按赋值推断成 WebServerHandle 而报 assignment
        self.handle: "WebServerHandle | None" = None
        # 限速/流量只读快照(traffic_snapshot 模块整体替换, Web 线程只读); 未启用曲线时 state="disabled"
        # 三段契约(计划 26-10-18-0813 A2/D8/D10): source(来源态) / periods+history(来源数据) /
        # limit(曲线态); 顶层 state 是 derive_state 的派生值。!种子值刻意用 source=ok: "off" 是
        # 「总开关关闭」的断言, 未读之前不成立(首轮发布无论谁先跑都会覆盖它); 用 ok 让种子的
        # state 与派生规则自洽(ok + limit=disabled -> "disabled", 与今日初始态一致)。
        self.traffic_view: dict = {
            "state": "disabled",
            "ts": 0.0,
            "date": "",
            "source": {
                "state": "ok",
                "reasons": [],
            },
            "periods": [],
            "history": [],
            "limit":
                {
                    "target": {
                        "up": None,
                        "down": None
                    },
                    "actual": {
                        "up": None,
                        "down": None
                    },
                    "reasons": [],
                    "state": "disabled",
                },
        }
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
