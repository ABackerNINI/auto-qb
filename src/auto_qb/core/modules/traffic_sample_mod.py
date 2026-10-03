"""TrafficSampleModule: qB 口径流量采样器(plan 26-10-03-0946 方案C P1 采样器核心)

两系列周期采样, 全部读内存快照(1.5s 增量同步已在 store), 零新增 qB 请求:
- 全局(恒采, qB 在线即有值): store.server_state 的 dl_info_speed/up_info_speed(瞬时)
  + dl_info_data/up_info_data(会话累计) + alltime_dl/alltime_ul(终身累计);
- 单种(活跃过滤): record.dlspeed/upspeed(瞬时) + downloaded/uploaded(all-time 累计)
  + downloaded_session/uploaded_session(会话累计), 仅 dlspeed>0 or upspeed>0 才采,
  非活跃期不产点 —— 全库空闲时零采样行。

P1 范围边界(本阶段纯内存): 采样点只进内存可测结构(latest, 每系列保留最近一点),
不写任何文件、不建任何目录。S2 的 dat 落盘将挂在 sample_series 产出缝上 —— 该方法是
"每系列每轮产出采样点"的单一出口, 产出后落盘(存储阶段)与内存镜像(本阶段)共用它。
内存常驻结构只有差分基线(baselines, 进程内推进不落盘, §03.3/§03.4): 程序重启后基线为空,
重启后首个采样只立基线不出增量(首窗 null), 与「停机 = 断线」的拍板语义一致。

差分与重置规则(§03.4):
- 速率字段直采不差分; 累计差分对 all-time 对(downloaded/uploaded / alltime_dl/alltime_ul)
  进行: delta = max(0, cur - last)(cur >= last 时 cur-last 天然非负);
- cur < last(qB 非优雅重启 alltime 回退 / 删种重加) => 判计数器重置: 该点累计增量记 null、
  基线更新为 cur —— 绝不产负增量;
- 会话累计(dl_info_data / *_session)按快照存入采样点不差分(qB 重启即归零, 由消费侧按
  快照口径取用; 采样器不对其进行重置判定)。

断连与空值防御(§03.5):
- qB 断连退避期(qbmanager APIConnectionError 路径置 store.client = None)采样任务照常出队:
  全局出 null 点(全字段 None), 单种不产点 —— 单种图空闲与停机同为无行, 停机洞由全局系列
  表达(§05.2); 不沿用旧值画假曲线, null 点不推进基线;
- server_state / 记录关键字段缺失或空值 => 该轮该系列按 null 点处理并 DEBUG 记录, 不写 0。

线程模型(黄金法则 5): handler 由 TaskQueue 在主循环线程执行, baselines/latest 全部只在
该线程读写, 无锁; 模块自身不创建任何线程。

配置: config.qb_traffic(QbTraffic, 缺省 None = 未启用)。enabled 为 false(含段缺省)时
start 不建任务、零开销(保守默认, 黄金法则 2); 热重载改 enabled=true 后经 queue_rebuilt
相位自然起任务(L2 重建换新队列, has_named 判空后按新配置入队)。任务已注册而运行期被
热重载关闭(L0 换对象不重建队列)时, handler 每轮自检 enabled 短路不采样。
"""
import logging
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Optional

from ..module import AppContext, BaseModule
from ..taskqueue import REQUEUE, Task

logger = logging.getLogger(__name__)

#: 全局任务名(与模块名区分: 任务是采样动作, 模块是功能域)
TASK_NAME = "qb_traffic_sample"

#: 全局系列键(对应存储阶段 global.dat 的系列标识)
GLOBAL_SERIES_KEY = "global"

#: 单种系列键前缀(对应存储阶段 torrents/<infohash>.dat; infohash 即稳定身份键, 无身份层)
_TORRENT_KEY_PREFIX = "torrent:"

#: 全局系列采样字段(顺序 = dl_rate, up_rate, dl_total, up_total, dl_session, up_session)
_GLOBAL_FIELDS = ("dl_info_speed", "up_info_speed", "alltime_dl", "alltime_ul", "dl_info_data", "up_info_data")

#: 单种系列采样字段(顺序同上; record 属性)
_TORRENT_FIELDS = ("dlspeed", "upspeed", "downloaded", "uploaded", "downloaded_session", "uploaded_session")


def _valid_counter(value) -> bool:
    """qB 计数字段合法性: 数值即合法(0 合法); None/缺失/布尔/非数值 = 空值(按 null 处理, 不写 0)"""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


@dataclass(frozen=True)
class TrafficSamplePoint:
    """单系列单轮采样点(P1 内存形态; S2 起经产出缝追加落盘)

    全字段 None = null 点(断连/关键字段缺失), 前端渲染为断线; dl_inc/up_inc 为相邻采样
    的 all-time 累计增量(差分), None = 首样立基线 / 计数器重置 —— 与 null 点同作断线语义。
    """
    ts: float  # epoch 秒(采样时刻, 不对齐栅格 —— 抖动是事实, 存储层不假装均匀, §05.1)
    dl_rate: Optional[int]  # 瞬时下载速率 bytes/s(直采)
    up_rate: Optional[int]  # 瞬时上传速率 bytes/s(直采)
    dl_total: Optional[int]  # all-time 下载累计快照 bytes(Prometheus 口径: 存快照)
    up_total: Optional[int]  # all-time 上传累计快照 bytes
    dl_session: Optional[int]  # 会话下载累计快照 bytes(qB 重启归零)
    up_session: Optional[int]  # 会话上传累计快照 bytes
    dl_inc: Optional[int]  # 相邻采样下载累计增量 bytes(max(0, cur-last); None = 首样/重置)
    up_inc: Optional[int]  # 相邻采样上传累计增量 bytes(同上)


class TrafficSampleModule(BaseModule):
    """qb_traffic 模块: internal 采样任务自注册 + 两系列采样(P1 纯内存)"""

    name = "qb_traffic"

    def __init__(self, ctx: AppContext) -> None:
        self._ctx = ctx
        # 差分基线(§03.3): 系列键 -> {"dl_total": int, "up_total": int}, 仅进程内推进不落盘;
        # 重启为空 -> 首个采样只立基线不出增量(首窗 null)。null 点不推进基线。
        self._baselines: dict = {}
        # P1 采样落点(可测结构): 系列键 -> 最近一个采样点。S2 挂缝后每点直接追加落盘,
        # 本结构退化为"最近一点"的排障镜像, 内存有界(与系列数同阶)。
        self.latest: dict = {}

    def sections(self) -> tuple[str, ...]:
        return ("qb_traffic", )

    # ---------- 生命周期与相位 ----------

    def start(self, ctx: AppContext, dry_run: bool) -> None:
        # 采样任务自注册(plan §03.1 仿 speed_curve): dry_run 不影响注册(P1 采样纯内存,
        # dry_run 同口径; 未启用 = 不建任务零开销)
        self._register_task(ctx)

    def subscribe(self, phases) -> None:
        phases.on("queue_rebuilt", self._on_queue_rebuilt)

    def _on_queue_rebuilt(self, event) -> None:
        """L2 热重载整体重建队列后重新入队: 新队列按新配置起任务(含 enabled=true 后自然启用)"""
        self._register_task(self._ctx)

    def _register_task(self, ctx: AppContext) -> None:
        """采样任务自注册: 已在当前队列幂等跳过(黄金法则 1, 判据单点 TaskQueue.has_named);
        enabled=false(含段缺省 None)不建任务零开销(黄金法则 2); 队列引用现取 ctx.task_queue
        (L2 重建后 manager 委托落回 ctx, 不存在旧队列)"""
        queue = ctx.task_queue
        if queue is None or queue.has_named(TASK_NAME):
            return
        conf = ctx.config.qb_traffic
        if conf is None or not conf.enabled:  # 未启用: 不建任务不建目录零文件
            return
        task = Task(
            "internal",
            TASK_NAME,
            interval=conf.sample_interval,
            handler=self.handle_traffic_sample,
        )
        queue.add_task(task)
        logger.info(f"创建全局任务 1 个: ['{task.log_tag}']")

    # ---------- 全局任务执行体 ----------

    def handle_traffic_sample(self, task: Task, dry_run: bool) -> bool:
        """一轮采样: 全局恒采 + 单种活跃过滤, 采样点经产出缝进内存(P1 不落盘)"""
        conf = self._ctx.config.qb_traffic
        if conf is None or not conf.enabled:
            # 未启用/运行期被热重载关闭: 本轮不采样不动内存(任务保留, L2 重建时按新配置重注册)
            return REQUEUE
        store = self._ctx.store
        now = time.time()
        if store.client is None:
            # qB 断连(重连退避期, qbmanager 置 client=None): 快照 stale —— 全局出 null 点,
            # 单种不产点(单种空闲与停机同为无行, 停机洞由全局系列表达, §05.2)
            self.record_null_point(GLOBAL_SERIES_KEY, now)
            logger.debug("流量采样 | qB 断连, 本轮全局出 null 点")
            return REQUEUE
        self._sample_global(store.server_state, now)
        self._sample_torrents(store, now)
        return REQUEUE

    # ---------- 两系列采样 ----------

    def _sample_global(self, server_state, ts: float) -> None:
        """全局系列(恒采): server_state 直采; 缺失/空值走 null 点不写 0(§03.5)"""
        getter = server_state.get if isinstance(server_state, Mapping) else (lambda name: None)
        readings = self._read_fields(_GLOBAL_FIELDS, getter)
        if readings is None:
            logger.debug("流量采样 | server_state 关键字段缺失/空值, 本轮全局按 null 处理")
            self.record_null_point(GLOBAL_SERIES_KEY, ts)
            return
        self.sample_series(GLOBAL_SERIES_KEY, ts, *readings)

    def _sample_torrents(self, store, ts: float) -> None:
        """单种系列(活跃过滤): dlspeed>0 or upspeed>0 才采; 空闲零采样行(§03.2)

        只读遍历 by_hash: handler 在主循环线程执行, 单线程不变式下迭代期无并发写(黄金法则 5)。
        """
        for record in store.by_hash.values():
            if not (record.dlspeed > 0 or record.upspeed > 0):
                continue  # 活跃过滤: 非活跃期不产点
            key = _TORRENT_KEY_PREFIX + record.hash
            readings = self._read_fields(_TORRENT_FIELDS, lambda name, rec=record: getattr(rec, name, None))
            if readings is None:
                logger.debug(f"流量采样 | 种子 {record.hash} 关键字段缺失/空值, 本轮按 null 处理")
                self.record_null_point(key, ts)
                continue
            self.sample_series(key, ts, *readings)

    @staticmethod
    def _read_fields(fields, getter) -> Optional[tuple]:
        """按 fields 顺序经 getter 读六字段; 任一字段缺失/空值 => None(调用方走 null 点),
        绝不用 0 充数(§03.5)。getter 以字段名取值(dict.get / getattr 皆可)"""
        values = tuple(getter(name) for name in fields)
        if not all(_valid_counter(v) for v in values):
            return None
        return values

    # ---------- 产出缝(S2 dat 落盘挂点) ----------

    def sample_series(
        self, key: str, ts: float, dl_rate, up_rate, dl_total, up_total, dl_session, up_session
    ) -> TrafficSamplePoint:
        """单系列单轮采样点产出 —— plan §03.3「每系列每轮产出采样点」的单一出口

        差分基线推进 + 增量计算(§03.4): 基线为空(重启后首样)只立基线不出增量;
        cur < last 判计数器重置(该点增量记 null + INFO 记录, 基线更新为 cur), 绝不产负增量。
        S2 的 dat 追加写将挂在本方法出口(每轮每系列恰一点)。
        """
        base = self._baselines.get(key)
        if base is None:
            dl_inc = None  # 基线为空: 首个采样只立基线不出增量(首窗 null, §03.4)
            up_inc = None
        else:
            dl_inc = self._delta(key, "下载", dl_total, base["dl_total"])
            up_inc = self._delta(key, "上传", up_total, base["up_total"])
        self._baselines[key] = {"dl_total": dl_total, "up_total": up_total}
        point = TrafficSamplePoint(
            ts=ts,
            dl_rate=dl_rate,
            up_rate=up_rate,
            dl_total=dl_total,
            up_total=up_total,
            dl_session=dl_session,
            up_session=up_session,
            dl_inc=dl_inc,
            up_inc=up_inc,
        )
        self.latest[key] = point
        return point

    def record_null_point(self, key: str, ts: float) -> TrafficSamplePoint:
        """null 点(断连 / 关键字段缺失): 全字段 None, 不推进基线(无读数可言, §03.5)"""
        point = TrafficSamplePoint(
            ts=ts,
            dl_rate=None,
            up_rate=None,
            dl_total=None,
            up_total=None,
            dl_session=None,
            up_session=None,
            dl_inc=None,
            up_inc=None
        )
        self.latest[key] = point
        return point

    @staticmethod
    def _delta(key: str, direction: str, cur, last) -> Optional[int]:
        """累计差分: delta = max(0, cur - last)(cur >= last 时天然非负);
        cur < last 判计数器重置: 该点增量记 null + INFO 记录(P6 真机验证重置语义靠它观察)"""
        if cur < last:
            logger.info(f"流量采样 | {key} {direction}累计计数器回落({last} -> {cur}), 判重置, 本点增量记 null")
            return None
        return cur - last
