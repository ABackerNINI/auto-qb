"""traffic_sample_mod 拆分件: 常量、数据类与模块级纯助手(R5 move-only, 计划 26-11-02-2342 §07)。"""
from dataclasses import dataclass, field
from typing import Optional

from typing import Any

from ..traffic_store import HOUR_SECONDS, V4NullRun, V4Sample, V4ZeroRun

#: 全局系列键(对应流量存储 global/ 目录的系列标识)
GLOBAL_SERIES_KEY = "global"

#: 单种系列键前缀(对应流量存储 torrents/<infohash>/ 目录; infohash 即稳定身份键)
_TORRENT_KEY_PREFIX = "torrent:"

#: 全局系列采样字段(顺序 = dl_rate, up_rate, dl_total, up_total, dl_session, up_session)
_GLOBAL_FIELDS = ("dl_info_speed", "up_info_speed", "alltime_dl", "alltime_ul", "dl_info_data", "up_info_data")

#: 单种系列采样字段(顺序同上; record 属性)
_TORRENT_FIELDS = ("dlspeed", "upspeed", "downloaded", "uploaded", "downloaded_session", "uploaded_session")

#: 游程时间刷新封口阈值(秒, N4 天级保险闸): v4 起开放 z 游程正常封口走「非 z 事件」
#: (恢复传输 / null 游程 / 计数器重置 / 00:00 / stop —— §01「空闲封口」), 本阈值退役为
#: 防溢出保险闸(正常空闲段任何路径都不应触闸, 触闸即测试 bug); 模块常量非配置键
ZRUN_FLUSH_S = 86400

#: 游程样本数上限(N4 天级保险闸, 同上): = ceil(86400 / sample_interval) 在 sample_interval
#: >= 1s(配置校验下限 + _apply_interval max(1.0) 钳制)下的上界, 保证游程跨度不超天级
#: dt_ms 口径; 模块常量非配置键
ZRUN_CAP_SAMPLES = 86400

#: 单系列缓冲槽数上限(Q3 保险闸, plan 26-10-04-1957 §3.1): r 记录占 1 槽, 游程占 run_len
#: 槽; 达到即提前单独 flush(防大种子库最坏 ~60MB 滞留); 模块常量非配置键
V4_BUFFER_SLOT_CAP = 3600

#: 种子按龄淘汰扫描节流间隔(秒, §4.5: 触发点 = flush 时点, 扫目录 IO 节流至多每小时
#: 一次 —— 判据口径与触发频率解耦); 模块常量非配置键
EVICT_CHECK_INTERVAL_S = 3600


def _valid_counter(value: Any) -> bool:
    """qB 计数字段合法性: 数值即合法(0 合法); None/缺失/布尔/非数值 = 空值(按 null 处理, 不写 0)"""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


@dataclass(frozen=True)
class TrafficSamplePoint:
    """单系列单轮采样点(内存镜像形态): 全字段 None = null 点(断连/关键字段缺失)。

    v4 起本结构只是「最近一点」的排障镜像(latest), 落盘形态为 v4 块记录
    (V4Sample/V4ZeroRun/V4NullRun); dl_inc/up_inc 为相邻采样的 all-time 累计增量
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
    last_dl_total/last_up_total = 游程内最后一条零样本的读数(形态 D 封口末端锚点候选,
    plan 26-10-16-1509 §04: 封口时落进 z 行末端列); 只随「带 totals 的零样本推进」刷新
    —— 已开游程免重读字段的既有路径不刷新它, 封口时它仍是「封口时刻已知的最后观测」。
    """

    kind: str  # "z" | "n"(z = 零速游程, n = null 游程; 同系列同时至多一个, 换型先封口)
    start: float  # 首个零/null 样本实测时刻(触发 (3) 时长判据基准)
    last_seen: float  # 最后一个样本时刻(封口区间上界 = 游程实测终点)
    dl_total: int  # all-time 下载累计快照(开启时刻, 恒定不刷新; n 游程恒 0 不落盘)
    up_total: int  # all-time 上传累计快照(同上)
    samples: int  # 游程内样本计数(触发 (4) 判据 = 落盘 run_len)
    last_dl_total: int  # 游程内最后一条零样本的 all-time 下载读数(末端锚点候选; n 游程恒 0 不用)
    last_up_total: int  # 同上(上传)


@dataclass
class BlockBuffer:
    """v4 单系列写侧缓冲(§3.1 + v4 计划 §01 关块状态机): 当前块的待写记录 + dt 链写侧
    状态 + 块基线状态(主循环线程独占)

    projected_ts 是写侧游标, 严格镜像读侧 dt 链(上一记录槽位锚点): 每记录判
    |actual - (projected_ts + 标称推进)| > DRIFT_TOL_MS -> 写实测 dt_ms 并把游标推到
    实测点(自然复位); 否则游标推进标称值。块跨多次 flush: records 在 flush 时清空,
    start_epoch/interval_s/projected_ts/基线等块状态延续到关块(00:00 硬切 / 改间隔 /
    计数器重置 / flush ∧ has_r_row / 落盘失败复位)。

    v4 基线状态(§01「基线立点」): dl_base/up_base = 块内首个带 totals 观测的快照
    (块首 r 或 z 立基线, 其 delta = 0; 全 None = 无基线块 —— 块首 n 游程前缀, 3 列 B,
    仅 n 游程合法, 恢复传输的记录拆块另立基线); has_r_row = 块内已出现 r 行(关块谓词
    flush ∧ has_r_row —— 纯空闲块跨 flush 开放不关); last_dl_total/last_up_total =
    块内最近一次 totals 观测(计数器重置判定 cur < last —— 强制关块重开, 新块基线 =
    重置后 totals, 绝不产负 delta)。内存 totals 恒绝对值(delta 只在序列化时减基线)。
    """

    start_epoch: Optional[int]  # 本块首记录槽位 epoch 秒(B 行 start); None = 尚无开放块
    interval_s: float  # 本块采样间隔(秒, 块头 B 列; 允许小数秒; 开块时取生效间隔)
    date_str: Optional[str]  # 本块本地日期(YYYY-MM-DD; 块不跨天, 00:00 硬切)
    records: list  # 待写记录(V4Sample/V4ZeroRun/V4NullRun, 按槽序; flush 时清空)
    slots: int  # 待写槽数(r=1 / 游程=run_len; Q3 保险闸判据)
    prev_actual_ts: float  # 上一记录实测时刻(§3.1 结构字段; 回拨参照/诊断)
    projected_ts: float  # 写侧游标 = 上一记录槽位锚点(读侧 dt 链镜像; 漂移判据基准)
    header_written: bool  # 块头是否已随某次 flush 落盘(块头只写一次)
    dl_base: Optional[int]  # v4 块基线: 下载 all-time 快照(None = 无基线块, 与 up_base 成对)
    up_base: Optional[int]  # v4 块基线: 上传 all-time 快照(同上成对)
    has_r_row: bool  # 块内已出现 r 行(v4 关块谓词 flush ∧ has_r_row 的判据)
    last_dl_total: Optional[int]  # 块内最近 totals 观测(重置判定 cur < last; 与基线同点立)
    last_up_total: Optional[int]  # 同上(上传)


@dataclass
class SeriesAgg:
    """单系列聚合分层内存态(S2b §04, 主循环线程独占): 累计器 + 翻日/翻月状态 +
    裁剪判据。水位不在此 —— 水位 = agg 文件尾, append 成功即推进(§4.4)。

    pending: 未封口 hour 桶样本(hour_epoch -> V4HourSample 列表, 按时序); 常态只含
    当前小时, 暂停恢复跨多小时时可含多日(封口时逐桶检查完结)。同 epoch 桶重开
    (flush 恰在小时界后区间信用补记)时入账续接, 重封行替换累计器/文件旧行。
    open_credit: 区间信用 (槽位, dl_rate, up_rate, dl_total, up_total) —— 上一非 null
    槽的前向覆盖待下一记录首槽结算; None = 无信用(null 期/无观测)。块首(v4 起)经
    v4_block_gap_continuous 条件结算: 连续边界把 [上一块末槽, 本块首槽) 按上一记录
    速率入账, 崩溃/停机间隙真空(判定单点, 与离线 _agg_credit_day_file 同源)。
    day_epoch/day_hours: 开放日累计器(当日已封口 hour 行); month_epoch/month_days:
    开放自然月累计器(当月已封口 day 行)。严格逐级(§4.1), day 不从 raw 直聚。
    earliest_hour: agg 文件内最老 hour 行 epoch(裁剪判据, §4.5 —— 零常规文件读)。
    """

    pending: dict = field(default_factory=dict)
    open_credit: Optional[tuple] = None
    day_epoch: Optional[int] = None
    day_hours: list = field(default_factory=list)
    month_epoch: Optional[int] = None
    month_days: list = field(default_factory=list)
    earliest_hour: Optional[int] = None


def _record_slots(rec: V4Sample | V4ZeroRun | V4NullRun, anchor: float, cursor: float, block_head: bool) -> tuple:
    """单记录的槽位序列(绝对时刻浮点秒; 与块内槽位推算同一口径, 在线记账与恢复离线
    记账共用): r = [cursor]; z/n 游程非块首 = anchor + spacing*k (k=1..len, 末槽恰在
    cursor = 游程实测终点), 块首 = anchor + spacing*k (k=0..len-1, 首槽恰在
    B.start)。spacing 由 cursor-anchor 派生(显式 dt 或标称), 不重复解读 dt_ms。"""
    if isinstance(rec, V4Sample):
        return (float(cursor), )
    n = rec.run_len
    if block_head:
        if n == 1:
            return (float(anchor), )  # 块首单槽游程: 读侧零推进
        spacing = (cursor - anchor) / (n - 1)  # 端点含均摊(§09.2 定约)
        return tuple(anchor + spacing * k for k in range(n))
    spacing = (cursor - anchor) / n  # 均摊 span/run_len(§02.3)
    return tuple(anchor + spacing * k for k in range(1, n + 1))


def _hour_spans(start: float, end: float) -> tuple:
    """[start, end) 按小时界切段(与 _agg_credit_hours 的桶切分规则同源; 模块级纯函数)。

    返回 Tuple[(段起, 段止), ...], 每段恰落一个 hour 桶; 空/退化区间 -> ()。段数 =
    区间跨的小时数 —— 活尾合成上界 ~24: 开放游程被 00:00 硬切, 不跨天。"""
    spans: list = []
    cur = start
    while cur < end:
        h = int(cur) // HOUR_SECONDS * HOUR_SECONDS
        nxt = min(end, float(h + HOUR_SECONDS))
        spans.append((cur, nxt))
        cur = nxt
    return tuple(spans)
