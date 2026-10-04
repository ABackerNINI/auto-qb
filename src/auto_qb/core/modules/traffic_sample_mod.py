"""TrafficSampleModule: qB 口径流量采样器(v3 写侧, plan 26-10-04-1957 S2a)

两系列周期采样, 全部读内存快照(1.5s 增量同步已在 store), 零新增 qB 请求:
- 全局(恒采, qB 在线即有值): store.server_state 六字段(瞬时速率对 + all-time 累计对 +
  会话累计对); 速率非零 -> r 记录, (0,0) -> z 游程, 断连/缺字段 -> n 游程;
- 单种(活跃过滤): record 六字段, 仅 dlspeed>0 or upspeed>0 才产 r; 零速/断连进 z/n 游程。

S2a 写侧翻转(§03): 采样点不再逐行落盘, 进内存 BlockBuffer(每系列一个), 每 flush_interval
(默认 600s, handler 内计时)批量追加落盘到 <data_dir>/qb-traffic-v3/<系列>/<YYYY-MM-DD>.dat
(v3 块化稀疏 delta 格式; 序列化/解析纯函数单点在 core/traffic_store.py v3 纯函数区, 文件
写入单点在同文件 TrafficV3Store)。聚合分层(内存累计器/水位封口/文件尾恢复/catch-up/hour
裁剪/种子淘汰)属 S2b, 本阶段不接线 —— 写侧已留接缝: 块化追加(BlockBuffer.records 批量写)、
flush 时点(_maybe_flush_all 单点)、游程封口时机(_seal_run 封口即成为 buffer 记录)。
v2 写路径随翻转停用: 本模块不再触旧目录 qb-traffic/ 与 index.json(停写; 退役方法保留
待 S5 清理, 标注 pragma no cover)。

差分与重置规则(沿用 §03.4): 速率字段直采不差分; 累计差分对 all-time 对进行,
delta = max(0, cur - last); cur < last 判计数器重置(该点增量记 null + INFO, 基线更新为 cur),
绝不产负增量; 会话累计按快照存入采样点不差分不落盘。差分基线(baselines)进程内推进不落盘,
重启后首样只立基线不出增量(首窗 null)。

零值/null 游程(v3 §3.2, v2 四触发沿用、⑤小时封口触发退役):
- 每系列至多一个开放游程(OpenRun, 主循环线程独占); 封口 = 成为 buffer 记录(不单独落盘),
  跨 flush 的开放游程滞留内存, 随下次封口或 stop() 落盘; 崩溃丢开放游程 <= ZRUN_FLUSH_S
  纯零信息(与 v2 等价, 无信息损失)。
- 四触发: (1)非零样本到达(封任意型开放游程, 同轮先游程后 r, 文件序 = 时间序);
  (2)null 到达先封口再记 n(z 覆盖不得横跨断连期, R2); (3)行程时长 >= ZRUN_FLUSH_S(600s);
  (4)样本数 >= ZRUN_CAP_SAMPLES(120)。另加块机械必要触发: 00:00 跨天样本到达先封游程
  (块不跨天, §3.3 —— 封 [start, 天界前末样本], 跨天样本开新游程)。
- 游程 dt_ms(§09.2 S1 定约): dt 基准 = 链上锚点(上一记录槽位时刻 = 写侧游标; 块首游程
  = B.start) —— 相邻游程之间的一次采样间隔并入后一游程的 dt_ms, 该读法下
  「缺省 = run_len x interval」恰为同一跨度的标称值; OpenRun.start 保留首样本实测时刻
  (触发 (3) 时长判据基准), dt 基准在封口时按块头/非块头分别解析。

单种数据门(§3.2, v2 index 条目门退役): 「种子目录存在且含 >=1 个 .dat」(目录判定) +
  本进程已有缓冲/已确认有数据的系列缓存(零稳态 IO) —— 零样本仅在已有数据或已开游程时
  开启/延长游程, 从未传输种子零文件零游程。totals 快照固定在游程开启时刻(§3.4 沿用)。

累积漂移触发 dt_ms(§2.3 写侧, 最易踩坑处 —— 判据必须用「累积漂移」):
- 写侧游标 projected_ts 严格镜像读侧 dt 链(上一记录槽位锚点); 每记录判
  |actual - (游标 + 标称推进)| > DRIFT_TOL_MS(250ms, D2) -> 本行写实测 dt_ms 并自然复位
  (游标被推到实测点)。禁止用「本行偏差」作判据 —— 稳态小漂移(d̄=150ms < tol)逐行判永不
  触发、误差照旧累积; 写后复位使稳态漂移自动退化周期性写, 空载(等间隔)保持稀疏零 dt 行。
- 时钟回拨单调钳制: dt_ms = max(1, 实测)(回拨行退回 1ms, 桶归属 max(ts, prev_ts) 属读侧
  S3); 暂停恢复/挂起/过载顺延: dt 取实测大值如实入行(「抖动是事实, 存储层不假装均匀」)。
- 块首记录亚秒余量: B.start = 块首记录实测 epoch 截断到整数秒, 块首 dt 列无语义不写
  (§02.3), 余量成为初始累积漂移由后续显式 dt 自然吸收。

flush 驱动与跨天切块(§3.3):
- 驱动点在采样 handler 内计时(now - last_flush >= flush_interval -> 全系列批量 flush),
  不引新线程(黄金法则 5), 不用 state.maybe_flush 主循环驱动点; 暂停期间 handler 不跑、
  缓冲滞留, 恢复后首轮补 flush。进程首轮只记时点不提前 flush(批量优先, 崩溃窗口
  <= flush_interval 拍板语义不变)。
- 批量写: 每系列单次 open("a") 写 N 行 + flush + fsync; 尾字节查补每 flush 仅一次;
  块头在该块首次 flush 时随批写入(块跨多次 flush 头只写一次)。
- 跨天切块(00:00 硬切, 本地时区): 记录日期 != 块日期 -> 旧块落盘(旧日期文件)+ 新文件新块头
  (interval 不变); 开放游程由跨天封口保证不跨天。落盘失败(OSError)丢弃本块并复位块状态
  (dt 链卫生: 下次成功写起新块, 避免半块游标错位), 连续失败只告警一次。
- Q3 保险闸: 单系列缓冲槽数(r=1 / 游程=run_len) >= V3_BUFFER_SLOT_CAP(3600) 提前单独
  flush(防大种子库最坏 ~60MB 滞留)。
- dry_run: 缓冲与游程内存照常推进, flush 触发静默跳过写; enabled=false 不建任务零开销。

优雅退出 stop() 钩子(§3.4): 经 host.stop_all() 触发 —— 封全部开放游程 + 全量 flush;
dry_run 短路; 幂等; OSError 按落盘失败口径告警不上抛。qbmanager 的 finally 与
state.save 顺序不改。

C1 生效与热重载联动(§3.5): handler 每轮现读 sample_interval 与 main_tick, 失配向上取整
到下一倍数 + 告警一次(D5: logger.warning + 已告警记忆防重复, 配置变化时记忆复位), 不拒采;
检测 sample_interval 变化 -> 直接改 task.interval + 关闭全部现块(旧块落盘, 新块带新
interval —— 新旧数据分块各有 interval); main_tick 每轮现读无需联动。

生命周期判定(S3 的 v2 index 面)随换代退役: v3 冻结语义 = 删种即不再产新块(不在
by_hash 本就无采样), 文件留存到按龄删除(淘汰属 S2b); 旧 lifecycle_sweep/reconcile/
seal_sweep 触发已断开(方法保留待 S5)。

线程模型(黄金法则 5): handler 由 TaskQueue 在主循环线程执行, buffers/baselines/latest/
游程全部只在该线程读写, 无锁; 模块自身不创建任何线程; 全部落盘写在 handler 调用链内。

配置: config.qb_traffic(QbTraffic, 缺省 None = 未启用)。任务自注册仿 speed_curve;
热重载 enabled=true 经 queue_rebuilt 相位自然起任务; 运行期关闭 handler 短路。
"""
import logging
import math
import time
from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Optional

from ..module import AppContext, BaseModule
from ..taskqueue import REQUEUE, Task
from ..traffic_store import (
    DRIFT_TOL_MS,
    V3NullRun,
    V3Sample,
    V3ZeroRun,
    TrafficDatStore,
    TrafficV3Store,
    v3_epoch_date_str,
)

logger = logging.getLogger(__name__)

#: 全局任务名(与模块名区分: 任务是采样动作, 模块是功能域)
TASK_NAME = "qb_traffic_sample"

#: 全局系列键(对应 v3 存储阶段 global/ 目录的系列标识)
GLOBAL_SERIES_KEY = "global"

#: 单种系列键前缀(对应 v3 存储阶段 torrents/<infohash>/ 目录; infohash 即稳定身份键)
_TORRENT_KEY_PREFIX = "torrent:"

#: 全局系列采样字段(顺序 = dl_rate, up_rate, dl_total, up_total, dl_session, up_session)
_GLOBAL_FIELDS = ("dl_info_speed", "up_info_speed", "alltime_dl", "alltime_ul", "dl_info_data", "up_info_data")

#: 单种系列采样字段(顺序同上; record 属性)
_TORRENT_FIELDS = ("dlspeed", "upspeed", "downloaded", "uploaded", "downloaded_session", "uploaded_session")

#: 游程时间刷新封口阈值(秒, plan 26-10-04-0721 修正 R1, v3 四触发 (3) 沿用): 行程时长 >=
#: 此值即封口成 buffer 记录; 模块常量非配置键
ZRUN_FLUSH_S = 600

#: 游程样本数上限(v3 四触发 (4), 写侧保险): 达到即封口; 采样间隔 < 5s 时先于 (3) 触发
ZRUN_CAP_SAMPLES = 120

#: 单系列缓冲槽数上限(Q3 保险闸, plan 26-10-04-1957 §3.1): r 记录占 1 槽, 游程占 run_len
#: 槽; 达到即提前单独 flush(防大种子库最坏 ~60MB 滞留); 模块常量非配置键
V3_BUFFER_SLOT_CAP = 3600


def _valid_counter(value) -> bool:
    """qB 计数字段合法性: 数值即合法(0 合法); None/缺失/布尔/非数值 = 空值(按 null 处理, 不写 0)"""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


@dataclass(frozen=True)
class TrafficSamplePoint:
    """单系列单轮采样点(内存镜像形态): 全字段 None = null 点(断连/关键字段缺失)。

    v3 起本结构只是「最近一点」的排障镜像(latest), 落盘形态为 v3 块记录
    (V3Sample/V3ZeroRun/V3NullRun); dl_inc/up_inc 为相邻采样的 all-time 累计增量
    (差分), None = 首样立基线 / 计数器重置。
    """
    ts: float  # epoch 秒(采样时刻, 不对齐栅格 —— 抖动是事实, 存储层不假装均匀)
    dl_rate: Optional[int]  # 瞬时下载速率 bytes/s(直采)
    up_rate: Optional[int]  # 瞬时上传速率 bytes/s(直采)
    dl_total: Optional[int]  # all-time 下载累计快照 bytes(Prometheus 口径: 存快照)
    up_total: Optional[int]  # all-time 上传累计快照 bytes
    dl_session: Optional[int]  # 会话下载累计快照 bytes(qB 重启归零; 不落盘)
    up_session: Optional[int]  # 会话上传累计快照 bytes(不落盘)
    dl_inc: Optional[int]  # 相邻采样下载累计增量 bytes(max(0, cur-last); None = 首样/重置)
    up_inc: Optional[int]  # 相邻采样上传累计增量 bytes(同上)


@dataclass
class OpenRun:
    """开放游程(v3 §3.2, 内存态每系列至多一个): 连续零速或 null 观测段, 封口 = 成为
    buffer 记录(_seal_run)。主循环线程独占(黄金法则 5), 随进程消失(崩溃丢 <= ZRUN_FLUSH_S
    纯零信息); totals 快照固定在开启时刻(首个零样本的 all-time 对), 后续零样本不刷新。
    """

    kind: str  # "z" | "n"(z = 零速游程, n = null 游程; 同系列同时至多一个, 换型先封口)
    start: float  # 首个零/null 样本实测时刻(触发 (3) 时长判据基准)
    last_seen: float  # 最后一个样本时刻(封口区间上界 = 游程实测终点)
    dl_total: int  # all-time 下载累计快照(开启时刻, 恒定不刷新; n 游程恒 0 不落盘)
    up_total: int  # all-time 上传累计快照(同上)
    samples: int  # 游程内样本计数(触发 (4) 判据 = 落盘 run_len)


@dataclass
class BlockBuffer:
    """v3 单系列写侧缓冲(§3.1): 当前块的待写记录 + dt 链写侧状态(主循环线程独占)

    projected_ts 是写侧游标, 严格镜像读侧 dt 链(上一记录槽位锚点): 每记录判
    |actual - (projected_ts + 标称推进)| > DRIFT_TOL_MS -> 写实测 dt_ms 并把游标推到
    实测点(自然复位); 否则游标推进标称值。块跨多次 flush: records 在 flush 时清空,
    start_epoch/interval_s/projected_ts 等块状态延续到 00:00 硬切或采样率变化关块。
    """

    start_epoch: Optional[int]  # 本块首记录槽位 epoch 秒(B 行 start); None = 尚无开放块
    interval_s: int  # 本块采样间隔(整数秒, 块头 B 列; 开块时取生效间隔)
    date_str: Optional[str]  # 本块本地日期(YYYY-MM-DD; 块不跨天, 00:00 硬切)
    records: list  # 待写记录(V3Sample/V3ZeroRun/V3NullRun, 按槽序; flush 时清空)
    slots: int  # 待写槽数(r=1 / 游程=run_len; Q3 保险闸判据)
    prev_actual_ts: float  # 上一记录实测时刻(§3.1 结构字段; 回拨参照/诊断)
    projected_ts: float  # 写侧游标 = 上一记录槽位锚点(读侧 dt 链镜像; 漂移判据基准)
    header_written: bool  # 块头是否已随某次 flush 落盘(块头只写一次)


class TrafficSampleModule(BaseModule):
    """qb_traffic 模块: internal 采样任务自注册 + 两系列采样 + v3 块化批量落盘(S2a)"""

    name = "qb_traffic"

    def __init__(self, ctx: AppContext) -> None:
        self._ctx = ctx
        # 差分基线(§03.3): 系列键 -> {"dl_total", "up_total"}, 仅进程内推进不落盘;
        # 重启为空 -> 首个采样只立基线不出增量(首窗 null)。null 点不推进基线。
        self._baselines: dict = {}
        # 采样落点镜像: 系列键 -> 最近一个采样点(null 点含)。内存有界(与系列数同阶)。
        self.latest: dict = {}
        # v2 存储层(惰性构造): S2a 起写侧不再触旧目录, 仅退役方法引用(待 S5 清理)
        self._store: Optional[TrafficDatStore] = None
        # 已触发过封口扫描的小时桶起点(退役字段, 随 _maybe_hourly_seal 待 S5 清理)
        self._sealed_hour: Optional[int] = None
        # 开放游程(v3 §3.2): 系列键 -> OpenRun, 每系列至多一个; 主循环线程独占
        self._open_runs: dict = {}
        # dry_run 语境旗标(start/handler 每轮设置): dry_run 缓冲游程照常推进, 落盘静默跳过
        self._persistence_on: bool = True
        # 落盘连续失败只告警一次(防断盘场景刷屏), 成功即复位
        self._persist_warned: bool = False
        # ---- v3 写侧状态(S2a) ----
        # 单系列写侧缓冲(§3.1): 系列键 -> BlockBuffer; 只对「有记录或开放块」系列存在
        self._buffers: dict = {}
        # v3 写侧存储(惰性构造: 首次 flush 才触盘)
        self._v3store: Optional[TrafficV3Store] = None
        # flush 驱动时点(None = 进程首轮只记时不 flush)
        self._last_flush: Optional[float] = None
        # 当前生效采样间隔(整数秒, C1 失配取整后; 块头 interval 列口径)
        self._effective_interval: Optional[int] = None
        # 失配告警记忆键(sample_interval, main_tick): 配置对变化时复位(同配对只告警一次, D5)
        self._interval_signature: Optional[tuple] = None
        self._ratio_warned: bool = False
        # 单种数据门缓存(§3.2): 已确认有 v3 数据 / 确认无数据的系列键(零稳态目录 IO)
        self._has_data: set = set()
        self._no_data: set = set()
        # 本轮已采样系列键(shell 缓冲清理参照, handler 每轮清空)
        self._round_keys: set = set()

    def sections(self) -> tuple[str, ...]:
        return ("qb_traffic", )

    # ---------- 生命周期与相位 ----------

    def start(self, ctx: AppContext, dry_run: bool) -> None:
        self._persistence_on = not dry_run  # dry_run 全程零落盘(含 stop 钩子短路)
        self._register_task(ctx)
        # v2 启动对账(reconcile/index)随换代退役: v3 写侧不触 index.json(R2), S5 删方法

    def _reconcile_on_start(self, ctx: AppContext, dry_run: bool) -> None:  # pragma: no cover
        """[v2 退役面, S2a 断开调用, S5 删] 启动对账: 扫 v2 目录与 index 求差自愈。"""
        if dry_run:
            return
        conf = ctx.config.qb_traffic
        if conf is None or not conf.enabled or not ctx.config.data_dir:
            return
        try:
            counts = self._get_store(ctx).reconcile()
        except OSError as e:
            logger.warning(f"流量采样 | 启动对账失败(不影响采样, 文件侧按现状运行): {e}")
            return
        if counts["dropped_entries"] or counts["recovered_entries"]:
            logger.info(
                f"流量采样 | 启动对账: 重建孤儿条目 {counts['recovered_entries']} 个, "
                f"删除失配条目 {counts['dropped_entries']} 个"
            )

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
        """一轮采样: C1 间隔联动 + 两系列采样(游程纪律) + flush 驱动, 全在调用线程内"""
        conf = self._ctx.config.qb_traffic
        if conf is None or not conf.enabled:
            # 未启用/运行期被热重载关闭: 本轮不采样不动内存不落盘(任务保留, L2 重建时按新配置重注册)
            return REQUEUE
        self._persistence_on = not dry_run  # dry_run 同口径不落盘(观测写盘属真实副作用)
        now = time.time()
        self._round_keys.clear()
        self._apply_interval(conf, task)  # C1(§3.5): 失配取整告警 + 采样率变化关块改 task.interval
        store = self._ctx.store
        if store.client is None:
            # qB 断连(重连退避期, qbmanager 置 client=None): 快照 stale —— 全局出 n 游程槽
            # (v3 §3.2: 现行断连 null 点改写为 n 游程占槽), 单种本轮不采样(停机洞由全局系列
            # 表达, §05.2); 缓冲滞留, flush 驱动照常
            self._touch_null_run(GLOBAL_SERIES_KEY, now)
            logger.debug("流量采样 | qB 断连, 本轮全局记 n 游程槽")
            self._maybe_flush_all(conf, now)
            return REQUEUE
        self._sample_global(store.server_state, now)
        self._sample_torrents(store, now)
        self._maybe_flush_all(conf, now)
        return REQUEUE

    # ---------- C1 生效与热重载联动(§3.5) ----------

    def _apply_interval(self, conf, task: Optional[Task]) -> None:
        """采样间隔现读与联动(C1, §3.5): 失配向上取整到下一倍数 + 告警一次(D5), 不拒采;
        sample_interval 变化 -> 直接改 task.interval + 关闭全部现块(旧块落盘, 新块带新
        interval —— 新旧数据分块各有 interval, A3 根因闭合); main_tick 每轮现读。"""
        main_tick = float(getattr(self._ctx.config, "main_tick", 0.0) or 0.0)
        sample_interval = float(conf.sample_interval)
        if main_tick > 0:
            multiple = math.ceil(sample_interval / main_tick - 1e-9)
            effective = multiple * main_tick  # 整数倍时恰等于配置值; 失配向上取整
        else:
            effective = sample_interval
        interval_s = max(1, int(math.ceil(effective - 1e-9)))  # 块头 interval_s 整数秒口径
        signature = (sample_interval, main_tick)
        if signature != self._interval_signature:
            self._interval_signature = signature  # 配置对变化: 告警记忆复位(新失配新告警)
            self._ratio_warned = False
        if main_tick > 0 and abs(effective - sample_interval) > 1e-9 and not self._ratio_warned:
            logger.warning(
                f"流量采样 | sample_interval {sample_interval:g}s 非 main_tick {main_tick:g}s 整数倍, "
                f"实际节拍取整为 {interval_s}s(颗粒变粗不断线, 本失配只告警一次)"
            )
            self._ratio_warned = True
        if self._effective_interval is None:
            self._effective_interval = interval_s  # 进程首轮: 只立基线不开关块
        elif interval_s != self._effective_interval:
            logger.info(f"流量采样 | 采样率变化 -> {interval_s}s: 关闭全部现块, 新数据分块带新 interval")
            self._effective_interval = interval_s
            self._close_blocks_for_interval_change()
        if task is not None:
            task.interval = interval_s  # 直接改运行中任务的间隔(A3: 注册时定死不跟 的修复点)

    def _close_blocks_for_interval_change(self) -> None:
        """采样率变化关块(§3.5): 开放块内游程先封口(记录入旧块), 旧块全量落盘并复位 ——
        之后的记录以新 interval 开新块。无开放块的开放游程不封(将成为新块首记录)。"""
        for key in list(self._open_runs):
            buf = self._buffers.get(key)
            if buf is not None and buf.start_epoch is not None:
                self._seal_run(key)
        for key in list(self._buffers):
            if self._buffers[key].start_epoch is not None:
                self._flush_series(key, close_block=True)

    # ---------- 两系列采样 ----------

    def _sample_global(self, server_state, ts: float) -> None:
        """全局系列(恒采): server_state 直采; 缺失/空值走 n 游程不写 0(§03.5);
        零样本(速率 0,0)推进/开启 z 游程(v3 §3.2: 全局恒开, 无数据门)。"""
        getter = server_state.get if isinstance(server_state, Mapping) else (lambda name: None)
        readings = self._read_fields(_GLOBAL_FIELDS, getter)
        if readings is None:
            logger.debug("流量采样 | server_state 关键字段缺失/空值, 本轮全局按 n 游程槽处理")
            self._touch_null_run(GLOBAL_SERIES_KEY, ts)
            return
        dl_rate, up_rate, dl_total, up_total, _dl_session, _up_session = readings
        if dl_rate == 0 and up_rate == 0:
            self._advance_run(GLOBAL_SERIES_KEY, ts, "z", dl_total, up_total)
            return
        self.sample_series(GLOBAL_SERIES_KEY, ts, *readings)

    def _sample_torrents(self, store, ts: float) -> None:
        """单种系列(活跃过滤): dlspeed>0 or upspeed>0 才产 r; 零速/缺字段进 z/n 游程(§3.2)

        零样本: 已开游程直接推进(无需重读 totals); 无游程经数据门(目录判定 + 进程内缓存,
        v2 has_entry 门退役)才读字段开游程(totals 缺失不开新游程), 无数据(从未传输)整体
        跳过。null 仅活跃且缺字段时记 n 游程槽(先封开放游程, R2)。只读遍历 by_hash:
        handler 在主循环线程执行, 单线程不变式下迭代期无并发写(黄金法则 5)。
        """
        for record in store.by_hash.values():
            key = _TORRENT_KEY_PREFIX + record.hash
            if record.dlspeed > 0 or record.upspeed > 0:
                readings = self._read_fields(_TORRENT_FIELDS, lambda name, rec=record: getattr(rec, name, None))
                if readings is None:
                    logger.debug(f"流量采样 | 种子 {record.hash} 关键字段缺失/空值, 本轮按 n 游程槽处理")
                    self._touch_null_run(key, ts)
                    continue
                self.sample_series(key, ts, *readings)
                continue
            # 零样本: 已开游程直接推进; 否则数据门为门(目录判定)
            if key in self._open_runs:
                self._advance_run(key, ts, "z")
                continue
            if not self._torrent_has_data(record.hash):
                continue  # 从未传输的种子: 空态, 整体跳过(§3.2)
            readings = self._read_fields(_TORRENT_FIELDS, lambda name, rec=record: getattr(rec, name, None))
            if readings is None:
                continue  # 开新游程需要 totals 快照; 缺失不开(空闲不出 null 槽)
            dl_rate, up_rate, dl_total, up_total, _dl_session, _up_session = readings
            if dl_rate == 0 and up_rate == 0:
                self._advance_run(key, ts, "z", dl_total, up_total)
            else:  # 防御: 活跃过滤与字段读数口径漂移时按非零样本处理, 绝不把活跃读数吞进游程
                self.sample_series(key, ts, *readings)

    def _torrent_has_data(self, infohash: str) -> bool:
        """单种数据门(§3.2): 「种子目录存在且含 >=1 个 .dat」+ 进程内缓存

        缓存: 本进程确认有数据(含已有缓冲 —— 有记录即动过)后恒 True(目录只增), 确认无数据
        后恒 False(数据只由本进程写出), 稳态零目录 IO; dry_run 不做目录判定(零落盘口径)。
        """
        key = _TORRENT_KEY_PREFIX + infohash
        if key in self._has_data or key in self._buffers:
            self._has_data.add(key)
            return True
        if key in self._no_data or not self._persistence_on or not self._ctx.config.data_dir:
            self._no_data.add(key)
            return False
        has = self._get_v3_store().series_has_data(key)
        if has:
            self._has_data.add(key)
        else:
            self._no_data.add(key)
        return has

    def _torrent_has_entry(self, infohash: str) -> bool:  # pragma: no cover
        """[v2 退役面, S2a 断开调用, S5 删] v2 index 条目门(被 _torrent_has_data 取代)。"""
        if not self._ctx.config.data_dir:
            return False
        return self._get_store(self._ctx).has_entry(infohash)

    @staticmethod
    def _read_fields(fields, getter) -> Optional[tuple]:
        """按 fields 顺序经 getter 读六字段; 任一字段缺失/空值 => None(调用方走 null 点),
        绝不用 0 充数(§03.5)。getter 以字段名取值(dict.get / getattr 皆可)"""
        values = tuple(getter(name) for name in fields)
        if not all(_valid_counter(v) for v in values):
            return None
        return values

    # ---------- 产出缝(v3: buffer 记录) ----------

    def sample_series(
        self, key: str, ts: float, dl_rate, up_rate, dl_total, up_total, dl_session, up_session
    ) -> TrafficSamplePoint:
        """单系列单轮非零采样点产出(plan §03.3「每系列每轮产出采样点」的单一出口)

        触发 (1): 非零样本到达先封开放游程(任意型)再出 r 记录 —— 同轮两记录, 文件序 =
        时间序。差分基线推进 + 增量计算(§03.4): 基线为空(重启后首样)只立基线不出增量;
        cur < last 判计数器重置(该点增量记 null + INFO 记录), 绝不产负增量。
        r 记录进 BlockBuffer(v3 §3.1), 随批量 flush 落盘; latest 镜像照常推进。
        """
        self._round_keys.add(key)
        self._seal_run(key)
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
        self._append_record(
            key,
            V3Sample(dl_rate=int(dl_rate), up_rate=int(up_rate), dl_total=int(dl_total), up_total=int(up_total)),
            ts,
            ts,
        )
        return point

    def _touch_null_run(self, key: str, ts: float) -> None:
        """null 点(断连 / 关键字段缺失)v3 处理(§3.2): 先封开放游程(z 覆盖不得横跨断连期,
        R2)再推进/开启 n 游程; latest 镜像置全 None 点(§05.2 全局 null 语义), 基线不动。"""
        point = TrafficSamplePoint(
            ts=ts,
            dl_rate=None,
            up_rate=None,
            dl_total=None,
            up_total=None,
            dl_session=None,
            up_session=None,
            dl_inc=None,
            up_inc=None,
        )
        self.latest[key] = point
        self._round_keys.add(key)
        self._advance_run(key, ts, "n")

    # ---------- 开放游程(v3 §3.2) ----------

    def _advance_run(self, key: str, ts: float, kind: str, dl_total=None, up_total=None) -> None:
        """零/null 样本推进/开启开放游程(§3.2): 零样本只动内存(不出记录/不动 baselines/
        latest), 封口判据 (3)(4) 在此逐样本检查; 换型(z<->n)与跨天先封旧游程(触发 (2) 与
        00:00 硬切)。已开游程只推进 last_seen 与 samples(无需重读 totals); 开 z 游程需要
        totals 快照(缺失不开, 空闲不出 null 槽), n 游程无此要求。
        """
        run = self._open_runs.get(key)
        if run is not None:
            if run.kind != kind or v3_epoch_date_str(ts) != v3_epoch_date_str(run.last_seen):
                self._seal_run(key)  # 换型(触发 (2) R2)或 00:00 硬切: 游程不跨型不跨天
                run = None
        if run is None:
            if kind == "z" and (dl_total is None or up_total is None):
                return  # 开 z 游程需要 totals 快照; 缺失/非法不开新游程
            self._open_runs[key] = OpenRun(
                kind=kind,
                start=ts,
                last_seen=ts,
                dl_total=int(dl_total) if dl_total is not None else 0,
                up_total=int(up_total) if up_total is not None else 0,
                samples=1,
            )
            return
        run.last_seen = ts
        run.samples += 1
        if run.samples >= ZRUN_CAP_SAMPLES or ts - run.start >= ZRUN_FLUSH_S:
            self._seal_run(key)

    def _seal_run(self, key: str) -> None:
        """封口开放游程(v3 §3.2, 各触发共同出口): 封口 = 成为 buffer 记录(不单独落盘;
        跨 flush 滞留内存, 随下次封口或 stop() 落盘)。dt 基准在 _append_record 按块头/
        非块头解析(链上锚点定约, §09.2)。无开放游程零操作。"""
        run = self._open_runs.pop(key, None)
        if run is None:
            return
        if run.kind == "n":
            rec = V3NullRun(run_len=run.samples)
        else:
            rec = V3ZeroRun(run_len=run.samples, dl_total=run.dl_total, up_total=run.up_total)
        self._append_record(key, rec, run.start, run.last_seen)

    def _seal_all_runs(self) -> None:
        """封全部开放游程(stop() 钩子 / S2b 聚合封口接缝): 逐系列封口成 buffer 记录。"""
        for key in list(self._open_runs):
            self._seal_run(key)

    # ---------- v3 批量落盘(§3.3) ----------

    def _get_v3_store(self) -> TrafficV3Store:
        """v3 写侧存储惰性构造(路径纯计算不触盘; data_dir 就绪由调用方保证)"""
        if self._v3store is None:
            self._v3store = TrafficV3Store(self._ctx.config.data_dir)
        return self._v3store

    def _get_store(self, ctx: AppContext) -> TrafficDatStore:  # pragma: no cover
        """[v2 退役面, S2a 断开调用, S5 删] v2 存储层惰性构造(退役方法引用)。"""
        if self._store is None:
            self._store = TrafficDatStore(ctx.config.data_dir)
        return self._store

    def _append_record(self, key: str, rec, start_ts: float, end_ts: float) -> None:
        """单条 v3 记录进缓冲(§3.1/§2.3 写侧核心): 块开启 / 00:00 跨天切块 / 累积漂移触发
        dt_ms / Q3 保险闸, 全部在此单点。

        - 块首记录: B.start = start_ts 截断整数秒, 写侧游标镜像读侧 = B.start(块首亚秒
          余量成为初始累积漂移, 由后续显式 dt 自然吸收); 块首 r 与单槽游程不写 dt(无语义)。
        - 非块首: 判据 = 累积漂移 |end_ts - (游标 + 标称推进)| > DRIFT_TOL_MS(250ms) ->
          本行写实测 dt_ms = max(1, round((end_ts - 游标) x 1000)) 并把游标推到实测点
          (自然复位; 时钟回拨钳制 dt_ms >= 1); 否则游标推进标称值。
        - 跨天(记录日期 != 块日期): 旧块落盘(旧日期文件)后本记录递归走新块首路径(游程
          不跨天由 _advance_run 的跨天封口保证, 此分支常态只服务 r/n 记录)。
        """
        buf = self._buffers.get(key)
        if buf is None:
            buf = self._buffers[key] = BlockBuffer(
                start_epoch=None,
                interval_s=0,
                date_str=None,
                records=[],
                slots=0,
                prev_actual_ts=0.0,
                projected_ts=0.0,
                header_written=False,
            )
        interval = self._effective_interval or 1
        tol_s = DRIFT_TOL_MS / 1000.0
        if buf.start_epoch is None:
            # 新块首记录(§3.1): B.start = 块首记录实测 epoch(整数秒)
            buf.start_epoch = int(start_ts)
            buf.interval_s = interval
            buf.date_str = v3_epoch_date_str(start_ts)
            buf.header_written = False
            anchor = float(buf.start_epoch)
            if isinstance(rec, V3Sample):
                buf.records.append(rec)  # 块首 r 的 dt 列无语义, 不写(§02.3)
                buf.slots += 1
                buf.projected_ts = anchor
            elif rec.run_len == 1:
                buf.records.append(rec)  # 块首单槽游程: 读侧零推进, dt 无消费者 —— 不写
                buf.slots += 1
            else:
                span = end_ts - anchor
                nominal = (rec.run_len - 1) * interval  # 块首游程无引导间隔(读侧标称口径)
                if abs(span - nominal) > tol_s:
                    dt_ms = max(1, int(round(span * 1000)))
                    rec = replace(rec, dt_ms=dt_ms)
                    buf.projected_ts = anchor + dt_ms / 1000.0
                else:
                    buf.projected_ts = anchor + nominal
                buf.records.append(rec)
                buf.slots += rec.run_len
            buf.prev_actual_ts = end_ts
        else:
            if buf.date_str != v3_epoch_date_str(end_ts):
                # 00:00 硬切(§3.3): 旧块先落盘(旧日期文件), 本记录成为新块首
                self._flush_series(key, close_block=True)
                self._append_record(key, rec, start_ts, end_ts)
                return
            anchor = buf.projected_ts
            nominal = interval if isinstance(rec, V3Sample) else rec.run_len * interval
            drift = end_ts - (anchor + nominal)
            if abs(drift) > tol_s:
                # 累积漂移超容差(§2.3): 写实测 dt 并自然复位(游标推到实测点); 回拨钳制 >= 1
                dt_ms = max(1, int(round((end_ts - anchor) * 1000)))
                rec = replace(rec, dt_ms=dt_ms)
                buf.projected_ts = anchor + dt_ms / 1000.0
            else:
                buf.projected_ts = anchor + nominal
            buf.records.append(rec)
            buf.slots += 1 if isinstance(rec, V3Sample) else rec.run_len
            buf.prev_actual_ts = end_ts
        if buf.slots >= V3_BUFFER_SLOT_CAP:
            self._flush_series(key)  # Q3 保险闸(§3.1): 超限提前单独 flush(不关块)

    def _flush_series(self, key: str, close_block: bool = False) -> None:
        """单系列批量落盘(§3.3): 单次 open("a") 写待写记录(块头在该块首次 flush 随批写入,
        跨 flush 的同块只写一次头)。dry_run / data_dir 为空(防御)静默跳过写, 内存状态照常
        推进。OSError 不上抛(观测数据丢失无一致性后果, §01.1), 连续失败只告警一次; 失败
        丢弃本块并复位块状态(dt 链卫生: 避免半块游标错位, 下次成功写起新块)。
        close_block(00:00 硬切 / 采样率变化): 写后块复位为无块, 之后的记录开新块。"""
        buf = self._buffers.get(key)
        if buf is None:
            return
        if buf.records:
            if self._persistence_on and self._ctx.config.data_dir:
                header = None
                if buf.start_epoch is not None and not buf.header_written:
                    header = (buf.start_epoch, buf.interval_s)
                try:
                    self._get_v3_store().append_records(key, buf.date_str, header, tuple(buf.records))
                    if header is not None:
                        buf.header_written = True
                    if key.startswith(_TORRENT_KEY_PREFIX):
                        self._has_data.add(key)  # 天文件已落盘: 数据门缓存翻真
                        self._no_data.discard(key)
                    self._persist_warned = False
                except OSError as e:
                    if self._persist_warned:
                        logger.debug(f"流量采样 | {key} 批量落盘失败(持续): {e}")
                    else:
                        logger.warning(f"流量采样 | {key} 批量落盘失败(本批数据丢失, 后续失败不再重复告警): {e}")
                        self._persist_warned = True
                    buf.start_epoch = None
                    buf.date_str = None
                    buf.header_written = False
            buf.records = []
            buf.slots = 0
        if close_block:
            buf.start_epoch = None
            buf.date_str = None
            buf.header_written = False

    def _maybe_flush_all(self, conf, now: float) -> None:
        """flush 驱动(§3.3): handler 内计时, now - last_flush >= flush_interval -> 全系列
        批量 flush。进程首轮只记时不提前 flush(批量优先; 崩溃窗口 <= flush_interval 不变)。
        暂停期间 handler 不跑、缓冲滞留, 恢复后首轮补 flush —— 语义正确。"""
        if self._last_flush is None:
            self._last_flush = now  # 进程首轮: 只记时点不提前 flush(批量优先)
            return
        if now - self._last_flush < conf.flush_interval:
            return
        self._last_flush = now
        self._flush_all_series()

    def _flush_all_series(self) -> None:
        """全系列批量 flush(§3.3 驱动点; stop() 复用): 逐系列落盘待写记录; 顺带做内存
        卫生 —— 无开放块、无待写记录、无开放游程且本轮未采样的 shell 缓冲清除。"""
        for key in list(self._buffers):
            self._flush_series(key)
        for key in list(self._buffers):
            buf = self._buffers[key]
            if buf.start_epoch is None and not buf.records and key not in self._open_runs and key not in self._round_keys:
                del self._buffers[key]

    # ---------- 优雅退出 stop() 钩子(§3.4) ----------

    def stop(self) -> None:
        """stop 钩子(§3.4): 经 host.stop_all() 触发 —— 封全部开放游程 + 全量 flush, 优雅
        退出零丢失(现行 v2 丢开放行程 <=600s 的语义在此闭合)。dry_run 短路(不落盘);
        幂等(重复调用缓冲游程已空, 零副作用); OSError 按落盘失败口径告警不上抛。
        聚合封口(hour/day/month)是 S2b 接缝: 在此追加即可。"""
        if not self._persistence_on:
            return  # dry_run: 不落盘(观测写盘属真实副作用)
        conf = self._ctx.config.qb_traffic
        if conf is None or not conf.enabled or not self._ctx.config.data_dir:
            return
        self._seal_all_runs()
        self._flush_all_series()

    def _persist_point(self, key: str, point: TrafficSamplePoint) -> None:  # pragma: no cover
        """[v2 退役面, S2a 断开调用, S5 删] v2 逐行追加落盘(被 BlockBuffer 批量 flush 取代)。"""
        conf = self._ctx.config.qb_traffic
        if conf is None or not conf.enabled or not self._persistence_on:
            return
        if not self._ctx.config.data_dir:
            return
        try:
            self._get_store(self._ctx
                           ).append_point(key, point.ts, point.dl_rate, point.up_rate, point.dl_total, point.up_total)
            self._persist_warned = False
        except OSError as e:
            if self._persist_warned:
                logger.debug(f"流量采样 | {key} 采样行落盘失败(持续): {e}")
                return
            logger.warning(f"流量采样 | {key} 采样行落盘失败(本轮数据丢失, 后续失败不再重复告警): {e}")
            self._persist_warned = True

    def _maybe_hourly_seal(self, now: float) -> None:  # pragma: no cover
        """[v2 退役面, S2a 断开触发, S5 删] v2 小时封口(每小时首采样触发 seal_sweep)随 v3
        写侧翻转退役: v3 空载压缩走 z/n 游程、聚合分层(hour/day/month + catch-up)属 S2b。"""

    def _sample_lifecycle(self, store, now: float) -> None:  # pragma: no cover
        """[v2 退役面, S2a 断开调用, S5 删] v2 冻结/解冻判定(index 面)。v3 冻结语义 =
        删种即不再产新块(不在 by_hash 本就无采样), 文件留存到按龄删除(淘汰属 S2b)。"""

    @staticmethod
    def _delta(key: str, direction: str, cur, last) -> Optional[int]:
        """累计差分: delta = max(0, cur - last)(cur >= last 时天然非负);
        cur < last 判计数器重置: 该点增量记 null + INFO 记录(P6 真机验证重置语义靠它观察)"""
        if cur < last:
            logger.info(f"流量采样 | {key} {direction}累计计数器回落({last} -> {cur}), 判重置, 本点增量记 null")
            return None
        return cur - last
