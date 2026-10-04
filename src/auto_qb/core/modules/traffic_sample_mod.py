"""TrafficSampleModule: qB 口径流量采样器(plan 26-10-03-0946 方案C P1 采样器核心)

两系列周期采样, 全部读内存快照(1.5s 增量同步已在 store), 零新增 qB 请求:
- 全局(恒采, qB 在线即有值): store.server_state 的 dl_info_speed/up_info_speed(瞬时)
  + dl_info_data/up_info_data(会话累计) + alltime_dl/alltime_ul(终身累计);
- 单种(活跃过滤): record.dlspeed/upspeed(瞬时) + downloaded/uploaded(all-time 累计)
  + downloaded_session/uploaded_session(会话累计), 仅 dlspeed>0 or upspeed>0 才出 raw 行,
  非活跃期零样本按开放行程纪律压缩(见下), 不出逐行零行。

P1 范围边界已被 S2 接续(plan §02 dat 落盘): 采样点除进内存镜像(latest, 每系列保留最近一点)
外, 经产出缝追加落盘到 <data_dir>/qb-traffic/ 下(global.dat + torrents/<infohash>.dat,
存储层单点在 core/traffic_store.py)。内存常驻结构只有差分基线(baselines, 进程内推进不落盘,
§03.3/§03.4): 程序重启后基线为空, 重启后首个采样只立基线不出增量(首窗 null), 与「停机 =
断线」的拍板语义一致; dat 文件不受重启影响 —— 重启后接续追加不断史(§01.3)。

差分与重置规则(§03.4):
- 速率字段直采不差分; 累计差分对 all-time 对(downloaded/uploaded / alltime_dl/alltime_ul)
  进行: delta = max(0, cur - last)(cur >= last 时 cur-last 天然非负);
- cur < last(qB 非优雅重启 alltime 回退 / 删种重加) => 判计数器重置: 该点累计增量记 null、
  基线更新为 cur —— 绝不产负增量;
- 会话累计(dl_info_data / *_session)按快照存入采样点不差分(qB 重启即归零, 由消费侧按
  快照口径取用; 采样器不对其进行重置判定)。

零值行程(open run, plan 26-10-04-0721 §03, v2 纪律):
- 速率 (0,0) 的采样不出 raw 行, 只推进内存开放行程(每系列至多一个, self._open_runs:
  系列键 -> OpenRun{start, last_seen, dl_total, up_total, samples}, 主循环线程独占);
  封口即经 append_z_run 落盘 z 行并移除行程。五触发(§3.1):
  (1)非零样本到达 -> 封 [start, last_seen], 先 append z 行再 append raw 行(同轮两行,
      文件序 = 时间序); (2)null 点到达(R2) -> 先封口再写 null 行, z 覆盖不横跨断连期;
  (3)行程时长 now - start >= ZRUN_FLUSH_S(600s, R1 时间刷新, 每零采样检查) -> 封
      [start, 当前样本 ts]; (4)行程样本数 >= ZRUN_CAP_SAMPLES(120, 写侧保险, 采样间隔
      < 5s 时先于 (3)) -> 同 (3); (5)小时封口扫描 -> 全部开放行程先 flush-all(end =
      last_seen)再调 store.seal_sweep, 断连轮照常触发。常量为模块常量非配置键。
- 两系列零样本纪律(§3.2): 全局恒开行程(全局文件必然存在或即将由首次封口创建); 单种
  条件开行程 —— store.has_entry(infohash)(index 条目 = 已有数据文件)或已开行程才
  推进/开启, 从未传输的种子整体跳过(连字段都不读, 零文件零行程零 index 条目);
  null 行仅活跃且缺字段时出(先封口该系列行程)。
- 零样本读数口径: 开行程需要 totals 快照(行程开启时首个零样本的 all-time 对) —— 该
  样本 totals 字段缺失/非法(_read_fields 现行判据)则不开新行程; 已开行程的零样本只
  推进 last_seen, 无需重读 totals。
- totals 快照固定在开启时刻、后续零样本不刷新(§3.4): qB 空闲期重启(计数器回落)统一
  在下一活跃样本处现形(一处 null), 0 平线本身不断裂; 零样本不动 baselines 与 latest
  (差分基线只在 raw 采样点推进, latest 镜像冻结在最后活跃点)。
- 崩溃/重启语义: 内存行程随进程消失 —— 丢一段 <= 600s 的纯零信息(与丢一行零行等价,
  无信息损失); 已落盘 z/raw/null 行不受影响, 重启后零样本按纪律重新开行程。
- dry_run / enabled=false: 现行短路全部沿用 —— dry_run 行程内存照常推进/封口移除,
  flush 触发静默跳过 append; 未启用不建任务零开销。

断连与空值防御(§03.5):
- qB 断连退避期(qbmanager APIConnectionError 路径置 store.client = None)采样任务照常出队:
  全局出 null 点(全字段 None), 单种不产点 —— 单种图空闲与停机同为无行, 停机洞由全局系列
  表达(§05.2); 不沿用旧值画假曲线, null 点不推进基线;
- server_state / 记录关键字段缺失或空值 => 该轮该系列按 null 点处理并 DEBUG 记录, 不写 0。

生命周期判定(§02.2/§02.5, S3, 全部跟随采样轮在 handler 内, 不开新任务新线程):
- 删种冻结: 连接轮对照 store.by_hash(当前种子集合内存快照)与 index 条目 —— 条目未冻结 +
  文件存在 + infohash 不在集合 => frozen_at = now, 该文件不再追加(不在集合本就无采样点);
- 重加解冻: 已冻结条目重新出现在集合 => frozen_at = null 解冻续写, 历史保留; 重加后
  all-time 计数器回落由既有判重置兜底(§03.4), 不新增机制;
- 按龄淘汰: 每小时封口时点顺带(复用封口触发, 无独立任务)检查 frozen 文件,
  now - updated_at > rollup_window => 删 dat 文件 + index 条目; global 永不冻结永不淘汰;
- 断连轮跳过冻结/解冻判定: by_hash 是断连前快照, 以它判定会误冻结在线种子/漏判重加。

线程模型(黄金法则 5): handler 由 TaskQueue 在主循环线程执行, baselines/latest 全部只在
该线程读写, 无锁; 模块自身不创建任何线程。dat 追加/封口重写/index 写入/冻结淘汰等全部
落盘写操作都在 handler 调用链内(主循环线程), 存储层无锁(单写线程不变式由测试钉住)。

配置: config.qb_traffic(QbTraffic, 缺省 None = 未启用)。enabled 为 false(含段缺省)时
start 不建任务、不建目录、零文件零开销(保守默认, 黄金法则 2); 热重载改 enabled=true 后经
queue_rebuilt 相位自然起任务(L2 重建换新队列, has_named 判空后按新配置入队)。任务已注册而
运行期被热重载关闭(L0 换对象不重建队列)时, handler 每轮自检 enabled 短路不采样不落盘。
dry_run 同口径不落盘(观测写盘属真实副作用): start 跳过对账、handler 跳过落盘与封口。
落盘失败(OSError)不阻断采样 —— 观测数据丢失无一致性后果(§01.1), 连续失败只告警一次。
"""
import logging
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Optional

from ..module import AppContext, BaseModule
from ..taskqueue import REQUEUE, Task
from ..traffic_store import HOUR_SECONDS, TrafficDatStore

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

#: 行程时间刷新封口阈值(秒, plan 26-10-04-0721 修正 R1): 行程时长 >= 此值即封口重开,
#: 0 平线落盘延迟 <= 10min; 模块常量非配置键(§03.1, 对齐 TRAFFIC_DIR_NAME 先例)
ZRUN_FLUSH_S = 600

#: 行程样本数上限(plan §03.1 触发 (4), 写侧保险): 达到即封口; 采样间隔 < 5s 时先于
#: ZRUN_FLUSH_S 触发
ZRUN_CAP_SAMPLES = 120


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


@dataclass
class OpenRun:
    """开放行程(plan 26-10-04-0721 §03.1, 内存态每系列至多一个): [start, last_seen] 闭区间
    的连续零速观测段, 封口即经 append_z_run 落盘 z 行并移除。

    主循环线程独占(黄金法则 5), 随进程消失(崩溃丢 <= ZRUN_FLUSH_S 纯零信息, 重启后
    零样本按纪律重新开行程); totals 快照固定在开启时刻(首个零样本的 all-time 对),
    后续零样本不刷新(§3.4)。
    """

    start: float  # 行程起点 epoch 秒(首个零样本时刻)
    last_seen: float  # 最后一个零样本时刻(封口区间上界)
    dl_total: int  # all-time 下载累计快照(开启时刻, 恒定不刷新)
    up_total: int  # all-time 上传累计快照(同上)
    samples: int  # 行程内零样本计数(触发 (4) 的判据)


class TrafficSampleModule(BaseModule):
    """qb_traffic 模块: internal 采样任务自注册 + 两系列采样(P1 纯内存)"""

    name = "qb_traffic"

    def __init__(self, ctx: AppContext) -> None:
        self._ctx = ctx
        # 差分基线(§03.3): 系列键 -> {"dl_total": int, "up_total": int}, 仅进程内推进不落盘;
        # 重启为空 -> 首个采样只立基线不出增量(首窗 null)。null 点不推进基线。
        self._baselines: dict = {}
        # 采样落点(可测结构): 系列键 -> 最近一个采样点。S2 起每点同时追加落盘,
        # 本结构是"最近一点"的排障镜像, 内存有界(与系列数同阶)。
        self.latest: dict = {}
        # S2 存储层(惰性构造: 首次落盘/对账时才按 data_dir 建, enabled=false 全程不触盘)
        self._store: Optional[TrafficDatStore] = None
        # 已触发过封口扫描的小时桶起点(epoch 秒, 进程内): 每小时首个采样触发一次;
        # 重启为空 -> 首轮也触发(封口扫描 catch-up 补封全部未封桶, 幂等 upsert 兜底)
        self._sealed_hour: Optional[int] = None
        # 开放行程(plan 26-10-04-0721 §03.1, v2): 系列键 -> OpenRun, 每系列至多一个;
        # 主循环线程独占(与 baselines/latest 同线程模型), 随进程消失(重启丢 <=600s 纯零信息)
        self._open_runs: dict = {}
        # dry_run 语境旗标(handler 每轮设置): dry_run 不落盘不封口不建目录
        self._persistence_on: bool = True
        # 落盘连续失败只告警一次(防断盘场景 30s 一条刷屏), 成功即复位
        self._persist_warned: bool = False

    def sections(self) -> tuple[str, ...]:
        return ("qb_traffic", )

    # ---------- 生命周期与相位 ----------

    def start(self, ctx: AppContext, dry_run: bool) -> None:
        # 采样任务自注册(plan §03.1 仿 speed_curve): dry_run 不影响注册(任务纯内存);
        # 未启用 = 不建任务零开销
        self._register_task(ctx)
        self._reconcile_on_start(ctx, dry_run)

    def _reconcile_on_start(self, ctx: AppContext, dry_run: bool) -> None:
        """启动对账(§02.5): enabled 且非 dry_run 才触盘 —— 扫目录与 index 求差自愈,
        只读目录与头行, 永不改写 raw/hour 数据。存储目录不存在时零动作(惰性创建纪律):
        enabled=false / 未启用不产生任何文件或目录。"""
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
        """一轮采样: 生命周期判定(S3) + 全局恒采 + 单种活跃过滤, 产出点经产出缝落盘(S2)+内存镜像(P1)"""
        conf = self._ctx.config.qb_traffic
        if conf is None or not conf.enabled:
            # 未启用/运行期被热重载关闭: 本轮不采样不动内存不落盘(任务保留, L2 重建时按新配置重注册)
            return REQUEUE
        self._persistence_on = not dry_run  # dry_run 同口径不落盘(观测写盘属真实副作用)
        store = self._ctx.store
        now = time.time()
        if store.client is None:
            # qB 断连(重连退避期, qbmanager 置 client=None): 快照 stale —— 全局出 null 点,
            # 单种不产点(单种空闲与停机同为无行, 停机洞由全局系列表达, §05.2)
            self.record_null_point(GLOBAL_SERIES_KEY, now)
            self._maybe_hourly_seal(now)  # 断连轮照常封口: 断连期历史行同样要按小时归并
            logger.debug("流量采样 | qB 断连, 本轮全局出 null 点")
            return REQUEUE
        self._sample_lifecycle(store, now)  # 冻结/解冻判定先行: 重加种子本轮解冻后才可能被追加(S3)
        self._sample_global(store.server_state, now)
        self._sample_torrents(store, now)
        self._maybe_hourly_seal(now)
        return REQUEUE

    # ---------- 生命周期判定(S3, §02.2/§02.5) ----------

    def _sample_lifecycle(self, store, now: float) -> None:
        """冻结/解冻判定(采样轮时点): 对照 by_hash 当前种子集合与 index 条目(§02.2)

        仅连接轮调用(调用方保证): 断连轮 by_hash 是断连前快照, 误判会冻结在线种子/
        漏判重加。判定在采样之前 —— 同轮重加的种子先解冻再采样, 条目语义不倒挂。
        dry_run / 运行期关闭 / data_dir 为空(防御)均短路; OSError 不上抛(注册表写失败
        无一致性后果, 冻结/解冻在内存已生效, 下一个条目变化时点随封口/淘汰重试落盘)。
        """
        if not self._persistence_on or not self._ctx.config.data_dir:
            return
        try:
            counts = self._get_store(self._ctx).lifecycle_sweep(set(store.by_hash.keys()), now)
        except OSError as e:
            logger.warning(f"流量采样 | 冻结/解冻判定落盘失败(内存已生效, 下个变化时点重试): {e}")
            return
        if counts["frozen"] or counts["unfrozen"]:
            logger.info(f"流量采样 | 种子生命周期: 冻结 {counts['frozen']} 个(已删种), 解冻 {counts['unfrozen']} 个(重加)")

    # ---------- 两系列采样 ----------

    def _sample_global(self, server_state, ts: float) -> None:
        """全局系列(恒采): server_state 直采; 缺失/空值走 null 点不写 0(§03.5)

        零样本(速率 0,0)不出 raw 行, 只推进/开启开放行程(v2 §3.2: 全局恒开, 无
        index 门); totals 快照取本样本 all-time 对。
        """
        getter = server_state.get if isinstance(server_state, Mapping) else (lambda name: None)
        readings = self._read_fields(_GLOBAL_FIELDS, getter)
        if readings is None:
            logger.debug("流量采样 | server_state 关键字段缺失/空值, 本轮全局按 null 处理")
            self.record_null_point(GLOBAL_SERIES_KEY, ts)
            return
        dl_rate, up_rate, dl_total, up_total, _dl_session, _up_session = readings
        if dl_rate == 0 and up_rate == 0:
            self._touch_zero_run(GLOBAL_SERIES_KEY, ts, dl_total, up_total)
            return
        self.sample_series(GLOBAL_SERIES_KEY, ts, *readings)

    def _sample_torrents(self, store, ts: float) -> None:
        """单种系列(活跃过滤): dlspeed>0 or upspeed>0 才出 raw 行; 零样本条件开行程(§3.2/§3.3)

        零样本(v2 纪律): 已开行程 -> 只推进 last_seen(无需重读 totals); 无行程 ->
        store.has_entry(infohash)(index 条目 = 已有数据文件)为门, 有条目才读字段开行程
        (totals 缺失不开新行程), 无条目(从未传输)整体跳过 —— 连字段都不读, 零文件零行程
        零 index 条目。null 行仅活跃且缺字段时出(record_null_point 内先封口, R2)。
        只读遍历 by_hash: handler 在主循环线程执行, 单线程不变式下迭代期无并发写(黄金法则 5)。
        """
        for record in store.by_hash.values():
            key = _TORRENT_KEY_PREFIX + record.hash
            if record.dlspeed > 0 or record.upspeed > 0:
                readings = self._read_fields(_TORRENT_FIELDS, lambda name, rec=record: getattr(rec, name, None))
                if readings is None:
                    logger.debug(f"流量采样 | 种子 {record.hash} 关键字段缺失/空值, 本轮按 null 处理")
                    self.record_null_point(key, ts)
                    continue
                self.sample_series(key, ts, *readings)
                continue
            # 零样本: 条件开行程 —— 已开行程直接推进; 否则 has_entry 为门
            if key in self._open_runs:
                self._touch_zero_run(key, ts)
                continue
            if not self._torrent_has_entry(record.hash):
                continue  # 从未传输的种子: 空态, 整体跳过(§3.3)
            readings = self._read_fields(_TORRENT_FIELDS, lambda name, rec=record: getattr(rec, name, None))
            if readings is None:
                continue  # 开行程需要 totals 快照; 缺失不开新行程(空闲不出 null 行)
            dl_rate, up_rate, dl_total, up_total, _dl_session, _up_session = readings
            if dl_rate == 0 and up_rate == 0:
                self._touch_zero_run(key, ts, dl_total, up_total)
            else:  # 防御: 活跃过滤与字段读数口径漂移时按非零样本处理, 绝不把活跃读数吞进行程
                self.sample_series(key, ts, *readings)

    def _torrent_has_entry(self, infohash: str) -> bool:
        """单种数据文件判定(§3.3): store.has_entry(index 条目 dict 查, 无 IO);
        data_dir 为空(防御) -> False; store 惰性构造(纯路径计算不触盘)。"""
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

    # ---------- 产出缝(S2 dat 落盘挂点) ----------

    def sample_series(
        self, key: str, ts: float, dl_rate, up_rate, dl_total, up_total, dl_session, up_session
    ) -> TrafficSamplePoint:
        """单系列单轮采样点产出 —— plan §03.3「每系列每轮产出采样点」的单一出口

        触发 (1)(v2 §3.1): 非零样本到达先封开放行程(z 行)再出 raw 行 —— 同轮两行,
        文件序 = 时间序; 无开放行程时零操作。
        差分基线推进 + 增量计算(§03.4): 基线为空(重启后首样)只立基线不出增量;
        cur < last 判计数器重置(该点增量记 null + INFO 记录, 基线更新为 cur), 绝不产负增量。
        产出点经 _persist_point 追加落盘(§02.4: 只落 all-time 累计对 + 瞬时速率对,
        会话快照不落盘)。
        """
        self._flush_zero_run(key)
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
        self._persist_point(key, point)
        return point

    def record_null_point(self, key: str, ts: float) -> TrafficSamplePoint:
        """null 点(断连 / 关键字段缺失): 全字段 None, 不推进基线(无读数可言, §03.5);
        同样落盘为空值行(raw,<ts>,,,,), 读侧还原 null —— 断连段如实呈现为洞(§02.3)。

        触发 (2)(v2 §3.1, 修正 R2): null 点到达先封开放行程(z 行)再写 null 行 ——
        z 覆盖不得横跨断连期, 否则把「未知」虚标成「观测到 0」。
        """
        self._flush_zero_run(key)
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
        self._persist_point(key, point)
        return point

    # ---------- 开放行程(v2, plan 26-10-04-0721 §03) ----------

    def _touch_zero_run(self, key: str, ts: float, dl_total=None, up_total=None) -> None:
        """零样本推进/开启开放行程(§3.2): 零样本只动内存(不落盘/不建采样点/不动
        baselines/latest), 封口判据 (3)(4) 在此逐零采样检查。

        已开行程: 只推进 last_seen 与 samples(无需重读 totals), 时长 >= ZRUN_FLUSH_S 或
        样本数 >= ZRUN_CAP_SAMPLES 即封口(封 [start, 当前样本 ts] —— last_seen 已推进到
        本样本)并移除, 下个零样本开新行程。无行程: dl_total/up_total 齐备才开(快照 =
        本首零样本的 all-time 对); 缺失则不开新行程(§3.2 读数口径)。
        """
        run = self._open_runs.get(key)
        if run is None:
            if dl_total is None or up_total is None:
                return  # 开行程需要 totals 快照; 缺失/非法不开新行程
            self._open_runs[key] = OpenRun(
                start=ts, last_seen=ts, dl_total=int(dl_total), up_total=int(up_total), samples=1
            )
            return
        run.last_seen = ts
        run.samples += 1
        if run.samples >= ZRUN_CAP_SAMPLES or ts - run.start >= ZRUN_FLUSH_S:
            self._flush_zero_run(key)

    def _flush_zero_run(self, key: str) -> None:
        """封口开放行程并落盘 z 行(五触发的共同出口, §3.1): 封 [start, last_seen]

        行程先从内存移除(移除即封口 —— dry_run 亦然, 只静默跳过 append); append 走
        append_z_run(v2 z 行, 文件不存在则建头行直接 v2)。OSError 口径同 _persist_point:
        观测数据丢失无一致性后果(§01.1), 连续失败只告警一次, 成功复位。无开放行程零操作。
        """
        run = self._open_runs.pop(key, None)
        if run is None or not self._persistence_on:
            return
        conf = self._ctx.config.qb_traffic
        if conf is None or not conf.enabled or not self._ctx.config.data_dir:
            return
        try:
            self._get_store(
                self._ctx
            ).append_z_run(key, int(run.start), int(run.last_seen), int(run.dl_total), int(run.up_total))
            self._persist_warned = False
        except OSError as e:
            if self._persist_warned:
                logger.debug(f"流量采样 | {key} 行程行落盘失败(持续): {e}")
                return
            logger.warning(f"流量采样 | {key} 行程行落盘失败(本段零值信息丢失, 后续失败不再重复告警): {e}")
            self._persist_warned = True

    def _flush_all_zero_runs(self) -> None:
        """触发 (5) 小时封口 flush-all(§3.1): 全部开放行程先逐系列落盘 z 行(end =
        last_seen)再调 store.seal_sweep —— hour 归并能看见全部行程; 断连轮照常触发。"""
        for key in list(self._open_runs):
            self._flush_zero_run(key)

    # ---------- S2 落盘接线(§02.4) ----------

    def _get_store(self, ctx: AppContext) -> TrafficDatStore:
        """存储层惰性构造(路径纯计算不触盘; data_dir 就绪由调用方保证)"""
        if self._store is None:
            self._store = TrafficDatStore(ctx.config.data_dir)
        return self._store

    def _persist_point(self, key: str, point: TrafficSamplePoint) -> None:
        """产出点追加落盘(含 null 点行): 每活跃轮恰一行 raw(v2 §3.2 口径收窄 —— 零样本
        不出 raw 行, 压缩为开放行程行; null 点行照旧)

        仅主循环线程调用(产出缝在 handler 调用链内, 单写线程不变式由测试钉住);
        dry_run / 运行期关闭 / data_dir 为空(防御: 真实配置恒非空, loaders 默认
        auto-qb-data)均短路。OSError 不上抛 —— 观测数据丢失无一致性后果(§01.1),
        连续失败只告警一次, 成功复位。
        """
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

    def _maybe_hourly_seal(self, now: float) -> None:
        """小时封口触发(§02.4): 每小时首个采样触发一次, 逐系列补封全部未封桶

        进程重启后 _sealed_hour 为空 -> 首轮也触发; 封口扫描是 catch-up 语义(存储层
        seal_sweep): 归并当前桶之前所有「有 raw 行且尚无 hour 行」的桶 —— 重启跨度/
        断连跳桶不会把已产出的 raw 行永远留在 hour 段之外; 已封桶不重算, 同桶重封是
        upsert, 幂等(黄金法则 1)。断连轮同样触发(断连期历史行照常归并)。触发时机在
        handler(主循环线程), 与写入共用单线程。封口失败(OSError)不阻断采样, 原文件
        完好, 数据无损。
        触发 (5)(v2 §3.1): seal_sweep 之前先 flush-all 全部开放行程(end = last_seen)
        —— hour 归并能看见全部行程。seal_sweep 收 interval_s=config.qb_traffic.
        sample_interval 真实值(混合桶加权均值口径, store DEFAULT_SAMPLE_INTERVAL_S 仅为
        缺省兜底)。
        S3 顺带(§02.5, 复用同一触发无独立任务): 冻结文件按龄淘汰先行于封口扫描 ——
        本轮要淘汰的文件不必再重写封口; global 不在 index 结构性豁免。
        """
        conf = self._ctx.config.qb_traffic
        if conf is None or not conf.enabled or not self._persistence_on:
            return
        bucket = int(now // HOUR_SECONDS) * HOUR_SECONDS
        if self._sealed_hour == bucket:
            return
        self._sealed_hour = bucket
        if not self._ctx.config.data_dir:
            return
        try:
            evicted = self._get_store(self._ctx).evict_expired_frozen(now=now, rollup_window=conf.rollup_window)
            if evicted:
                logger.info(f"流量采样 | 冻结淘汰: 删除 {evicted} 个超龄冻结文件(超 rollup_window)")
            self._flush_all_zero_runs()  # 触发 (5): 先 flush-all(hour 归并见全部行程), 再归并扫描
            rewritten = self._get_store(self._ctx).seal_sweep(
                bucket,
                now=now,
                raw_window=conf.raw_window,
                rollup_window=conf.rollup_window,
                interval_s=conf.sample_interval,
            )
        except OSError as e:
            logger.warning(f"流量采样 | 小时封口失败(原文件完好, 后续封口自然补上): {e}")
            return
        if rewritten:
            logger.debug(f"流量采样 | 小时封口: 重写 {rewritten} 个系列文件(补封桶 {bucket} 之前未封桶)")

    @staticmethod
    def _delta(key: str, direction: str, cur, last) -> Optional[int]:
        """累计差分: delta = max(0, cur - last)(cur >= last 时天然非负);
        cur < last 判计数器重置: 该点增量记 null + INFO 记录(P6 真机验证重置语义靠它观察)"""
        if cur < last:
            logger.info(f"流量采样 | {key} {direction}累计计数器回落({last} -> {cur}), 判重置, 本点增量记 null")
            return None
        return cur - last
