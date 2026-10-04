"""traffic_store: qB 口径流量 dat 存储层(plan 26-10-03-0946 方案C P2 落盘 + P3 生命周期, §02)

数据落点(§01.1 归类为观测/日志数据, 不入 state_file —— append-only、丢失无一致性后果、
体量日志型): `<data_dir>/qb-traffic/` 子目录(kebab-case 硬编码常量, 不做配置键; 子目录名
对齐既有兄弟目录 skip-check-backup/hr 先例), 布局(§02.1):

    <data_dir>/qb-traffic/
      index.json               # 单种注册表(format 1): infohash -> {frozen_at/created_at/updated_at}
      global.dat               # 全局系列(单文件, 永不冻结, 不进 index)
      torrents/<infohash>.dat  # 每活跃种子一文件(惰性建; 组不落盘 —— 三轮拍板, §02.2)

目录惰性创建: enabled 且首次采样(首个产出点)时 os.makedirs(exist_ok=True);
enabled=false(含 qb_traffic None)全程零文件零目录(保守默认, 黄金法则 2)。

文件格式(§02, 逐列冻结, 不得扩列改版; v2 = v1 + z 行型, 双读门闩 —— plan 26-10-04-0721 §02):
    # auto-qb qb-traffic v1 | v2                 <- 头行: 格式标识 + 版本(双读门闩)
    key,<系列标识>                                <- 不变; global.dat 固定 key,global; torrents/ = torrent:<infohash>
    raw,<epoch_s>,<dl_rate>,<up_rate>,<dl_total>,<up_total>                      # 不变; v2 语义收窄为「非零速率采样行」
    raw,<epoch_s>,,,,,                           <- 不变; null 行(断连/缺字段), v1 v2 同形
    hour,<hour_epoch>,<dl_avg>,<dl_max>,<up_avg>,<up_max>,<dl_total>,<up_total>  # 列不变
    z,<start_s>,<end_s>,<dl_total>,<up_total>    <- v2 新增: 零值行程行(Z_FIELDS = 5)

- 头行双读门闩(§02.2): 头行恰为 v2(HEADER_LINE_V2)才接受 z 行; 头行仍为 v1(HEADER_LINE,
  常量保留用于识别)时 z 行按坏行计数 —— v1 语义逐字节不变; 其它头行整文件记坏(现行口径)。
  头行升级到 v2 属写路径(P1b): 新文件默认 v2, 存量 v1 首次 z 追加/内容重写时升级(R3)。
- raw 四数据列 = 瞬时速率对(bytes/s) + all-time 累计快照对(bytes, Prometheus 口径:
  存快照、消费侧差分; 取 all-time 对 —— 跨 qB 重启连续性最好, §10.1 两行风险均按
  消费侧回落判重置兜底); 会话快照对本层不落盘(§02.3, S1 采样点的 session 字段在此截除)。
- null 点(断连/关键字段缺失)写 `raw,<epoch_s>,,,,`(四数据列全空), 读侧还原 None。
- z 行(v2 §02.1): [start, end] 闭区间按采样节奏观测、速率恒 (0,0); totals 快照行程内
  恒定(无传输则 all-time 计数不增长)。恒非负整数, 时间列整数秒, 口径对齐 raw/hour。
  校验宽松(§02.2): 列数 = 5, 四数值列非空非负, end >= start 且 end - start <=
  ZRUN_MAX_SPAN_S —— 违者一律按坏行跳过计数, 走既有损坏阈值隔离。
- 累计快照列恒非负整数; 时间列(epoch_s/hour_epoch/start_s/end_s)恒整数秒。

写路径(§02.4 左, 仅主循环线程 —— 黄金法则 5, 调用方义务; 本层无锁):
- 平时每次采样 open("a") 追加一行 raw + flush(进程崩溃丢 <=1 行), 不做常驻句柄;
- 零值行程追加(append_z_run, v2 plan 26-10-04-0721 §02.3): 与 raw 追加同款纪律
  (open("a") + flush 崩溃丢 <=1 行; 尾部半行先补 \\n); 文件不存在则建头行 + key 行,
  头行直接写 v2; 存量 v1 头行文件追加前先做一次内容保持重写(仅头行升 v2, 数据行
  逐字节不变, 绕过 same_content 短路)—— R3 硬不变式: 绝不向 v1 头行文件追加 z 行
  (v1 解析器把 z 行判坏行, 反复追加会累积坏行触发整文件隔离), 升级被读侧竞态占满
  重试后放弃则本轮不追加(OSError 上抛, 调用方按落盘失败口径处理); z 追加与 raw
  追加同样推进 index 条目 updated_at(空闲期不因「无 raw 行」被误判超龄淘汰);
- 小时封口(每小时首个采样触发一次, 逐系列): 读全文件 -> 归并未封桶的 raw 行与 z 覆盖
  出 hour 行(avg/max; totals 取本小时末观测快照 —— z 覆盖桶末时取行程快照; 混合桶
  avg 按 interval_s 加权, 见 _aggregate_bucket) -> 按窗裁剪(raw 与 z 行属 raw 段留
  raw_window(z 行按 end 判)、hour 段留 rollup_window, 窗口值由调用方从
  config.qb_traffic 现取) -> 写 *.tmp -> os.replace 原子替换(tmp+replace 纪律对齐
  utils.atomic_write; 行尾固定 \\n, dat 是行式文本, 对齐 TM history_traffic.dat 先例;
  重写输出序 = 头行(v2) + key + hour + z + raw)。封口对同一小时桶幂等(upsert: 重封
  替换同桶 hour 行, 内容无变化则跳过重写 —— 黄金法则 1)。
- 封口扫描(seal_sweep)是 catch-up 语义: 归并 < 当前桶的全部「有 raw 行或被 z 行覆盖
  且尚无 hour 行」的桶 —— 每小时首个采样触发只保证触发频率, 桶本身不依赖触发不缺席: 重启跨度(停机跨越
  整小时, 恢复后首个触发补封停机前残桶)与断连跳桶都不会把已产出的 raw 行永远留在 30d
  视图之外; 已封桶不重算(空闲系列每小时扫描零写放大)。
- rewrite 遇 PermissionError(Windows 读侧竞态: os.replace 目标被打开)退避重试 x3、
  每次 50ms; 仍失败则放弃本轮(原文件完好, 数据无损, 下一小时封口自然补上)。

读路径(§02.4 右, 面向 Web 线程只读; S4 API 经 traffic_grid 纯函数消费):
- 不匹配格式/字段非法的行跳过并计数(纪律对齐 curves.parse_history_dat 坏行先例;
  TM 是外部只读文件, 我们自有写路径 —— 半行容错是自己的义务); 仅尾部半行是正常崩溃残留:
  无换行结尾的末段若是完整合法行则照常收数据(只是缺行尾换行, 追加侧会先补 \\n), 解析失败
  则按尾部半行跳过 —— 它豁免损坏占比(否则小文件的 1 行崩溃残留必然触发整文件隔离,
  与「kill 丢 <=1 行」验收冲突), 但计入 bad_lines 供观察;
- 坏行占比 > 5% 且坏行 >= 2 判文件损坏 -> 原文移 <name>.corrupt 后按空文件对待(不静默吞,
  也不让坏文件常驻报错); 绝对下限兜住「上一次崩溃的尾半行经追加补 \\n 后成为小文件中段
  坏行」的场景 —— 单行残留跳过即可, 随下一次封口重写自洁, 不据以整文件隔离(kill 丢行
  恒 <=1); 下一次追加按新建重建(头行 + key 行);
- 文件 <=205KB(raw 24h@30s + hour 30d 设计上界)一次性快读即关;
- read_series_checked(S4): read_series 的可判别变体, 附读取健康位 —— OSError 瞬态
  (Windows rewrite 竞态)时 read_ok=False, API 层据此回退上一份响应并标 stale(§08),
  不以空态冒充无数据。

index.json 与启动对账(§02.5):
- 条目 {frozen_at, created_at, updated_at}; frozen_at = None 常态, 非 None = 种子已删
  冻结不再追加(整数秒);
- 写入走 utils.atomic_write, 仅条目变化时点写(建文件/封口/冻结/解冻/淘汰/对账),
  非每采样; updated_at 随追加在内存推进(= 最后数据活动时刻), 到上述时点才落盘
  (崩溃后滞后 <=1 小时, 对按龄淘汰判据 7d 粒度无影响); 内存值恒为真值 ——
  淘汰判定读内存, 不受落盘滞后影响;
- 生命周期(§02.2, S3): 删种 -> 冻结(lifecycle_sweep: 条目未冻结 + 文件存在 + infohash
  不在当前种子集合 => frozen_at = now); 同 hash 重加 -> 解冻(frozen_at = None, 历史保留
  续写, 计数器回落由采样器判重置兜底); 判定时机跟随采样轮(调用方 = 采样 handler,
  主循环线程) —— 断连轮快照 stale, 由调用方跳过判定;
- 按龄淘汰(§02.5, S3): evict_expired_frozen 在每小时封口时点顺带(复用封口触发, 无独立
  任务), frozen 条目且 now - updated_at > rollup_window => 删 dat 文件 + index 条目;
  文件删除失败(Windows 读侧竞态)保留条目下轮重试; global 不在 index, 结构性豁免
  (永不冻结永不淘汰);
- reconcile: 扫目录与 index 求差 —— 孤儿 dat(index 无条目)从头行 key, 重建条目;
  index 条目无文件则删条目; index 本身坏/半写按空表自愈(以磁盘为准)。对账只读目录与
  头行, 永不改写 raw/hour 数据。文件身份 = 文件名(infohash, §02.2「infohash 本身就是
  永久稳定身份」); 头行 key 与文件名失配属于被损坏的 key 行 —— 告警并按文件名登记
  (不改写文件: 头行重写要动全文件, 超出对账权限)。

线程模型: 本层不做任何加锁/线程假设的强制 —— 全部写方法只在主循环线程调用(采样
handler 内), 读方法(read_series)线程无关(只读 + 原子替换保证读到完整一份)。
"""
import json
import logging
import math
import os
import re
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import NamedTuple, Optional

from ..infra.utils import atomic_write

logger = logging.getLogger(__name__)

#: data_dir 下的存储子目录名(kebab-case 硬编码常量, 不做配置键, §02.1)
TRAFFIC_DIR_NAME = "qb-traffic"

#: 单种 dat 子目录名
TORRENTS_DIR_NAME = "torrents"

#: index.json 文件名
INDEX_NAME = "index.json"

#: 全局系列 dat 文件名
GLOBAL_DAT_NAME = "global.dat"

#: dat 文件后缀
DAT_SUFFIX = ".dat"

#: 损坏文件隔离后缀(§02.4: 原文移 <name>.corrupt)
CORRUPT_SUFFIX = ".corrupt"

#: 头行 v1(格式标识 + 版本, §02.3 逐列冻结; 双读门闩保留用于识别 —— v1 文件 z 行按坏行计数)
HEADER_LINE = "# auto-qb qb-traffic v1"

#: 头行 v2(新增 z 行型; 双读门闩 —— 头行恰为 v2 才接受 z 行, plan 26-10-04-0721 §02.2)
HEADER_LINE_V2 = "# auto-qb qb-traffic v2"

#: index.json 格式版本
INDEX_FORMAT = 1

#: 全局系列键(与采样器 GLOBAL_SERIES_KEY 同值; 本层不 import 采样模块, 字面量对齐)
GLOBAL_KEY = "global"

#: 单种系列键前缀(与采样器 _TORRENT_KEY_PREFIX 同值)
TORRENT_KEY_PREFIX = "torrent:"

#: raw 行字段数(raw + 时间 + 4 数据列)
RAW_FIELDS = 6

#: hour 行字段数(hour + 时间 + 6 数据列)
HOUR_FIELDS = 8

#: z 行字段数(z + start/end 两个时间列 + 2 个 totals 列, v2 §02.1)
Z_FIELDS = 5

#: z 行最大时间跨度(秒, 宽松上界: 合法行程 <= ~1h + 间隔抖动, 超界即损坏, §02.2)
ZRUN_MAX_SPAN_S = 86400

#: 坏行占比损坏阈值(§02.4: > 5% 判文件损坏)
CORRUPT_RATIO = 0.05

#: rewrite 遇 PermissionError 的重试次数(不含首次; §02.4 x3)
REWRITE_RETRIES = 3

#: rewrite 重试退避间隔(秒)
REWRITE_BACKOFF_S = 0.05

#: 小时桶宽(秒)
HOUR_SECONDS = 3600

#: 混合桶加权均值的缺省采样间隔(秒; 与 config QbTraffic.sample_interval 缺省 30 同值):
#: seal_sweep/seal_hour 的 interval_s 缺省 None 时取此值 —— 默认路径行为确定且向后兼容
#: (纯活跃/纯空闲桶的 hour 行与该值无关); P2 起调用方传 config.qb_traffic.sample_interval 真实值
DEFAULT_SAMPLE_INTERVAL_S = 30.0

#: 单种哈希合法字符(infohash 实际为 hex, 但 FakeTorrent 式测试哈希与宽容口径取
#: 文件名安全集: 字母/数字/下划线/连字符 —— 排除路径分隔符与点, 非法键 fail-fast)
_INFOHASH_RE = re.compile(r"^[A-Za-z0-9_-]+$")


@dataclass(frozen=True)
class RawRow:
    """dat 采样行(读侧还原形态): 全数据列 None = null 点(断连/缺字段)"""

    ts: int  # epoch 秒(采样时刻, 不对齐栅格, §05.1)
    dl_rate: Optional[int]
    up_rate: Optional[int]
    dl_total: Optional[int]
    up_total: Optional[int]

    @property
    def is_null(self) -> bool:
        return self.dl_rate is None


@dataclass(frozen=True)
class HourRow:
    """dat 小时封口行: 桶内速率均值/峰值 + 本小时末累计快照(§02.3)"""

    hour_epoch: int  # 桶起点 epoch 秒(即 30d 视图的桶键)
    dl_avg: int
    dl_max: int
    up_avg: int
    up_max: int
    dl_total: int
    up_total: int


@dataclass(frozen=True)
class ZRow:
    """dat 零值行程行(v2 §02.1): [start, end] 闭区间按采样节奏观测, 速率恒 (0,0)"""

    start: int  # 行程起点 epoch 秒(含)
    end: int  # 行程终点 epoch 秒(含; >= start 且跨度 <= ZRUN_MAX_SPAN_S)
    dl_total: int  # all-time 累计快照对(行程开启时首个零样本, 行程内恒定不刷新)
    up_total: int


@dataclass(frozen=True)
class ParsedSeries:
    """单文件解析结果(read_series 返回; S4 API 的取数入口)"""

    key: Optional[str]  # 头行 key 行的系列标识(无头行/坏头行时 None)
    raw: tuple  # Tuple[RawRow, ...](文件序; 封口裁剪时另行排序)
    hours: tuple  # Tuple[HourRow, ...](按 hour_epoch 升序, 同桶重复取最后一行)
    bad_lines: int  # 跳过的坏行数(含尾部半行)
    data_lines: int  # 受检行总数(头行后全部行, 含空行/注释/坏行; 损坏占比分母)
    torn_tail: bool = False  # 末尾存在未写完的半行(正常崩溃残留; 豁免损坏占比)
    zruns: tuple = ()  # Tuple[ZRow, ...](文件序; v1 文件恒空 —— 默认空元组, 构造点向后兼容)


def _fmt_int(v: int) -> str:
    """数值列统一整数文本(qB 计数字段本身整型; 浮点输入截断存储, 口径全链一致)"""
    return str(int(v))


def format_raw_row(ts: int, dl_rate, up_rate, dl_total, up_total) -> str:
    """采样行文本(§02.3 逐列); 任一数据列 None = null 点(四列全空)"""
    if dl_rate is None:
        return f"raw,{_fmt_int(ts)},,,,"
    return f"raw,{_fmt_int(ts)},{_fmt_int(dl_rate)},{_fmt_int(up_rate)},{_fmt_int(dl_total)},{_fmt_int(up_total)}"


def format_hour_row(row: HourRow) -> str:
    """小时封口行文本(§02.3 逐列)"""
    return (
        f"hour,{_fmt_int(row.hour_epoch)},{_fmt_int(row.dl_avg)},{_fmt_int(row.dl_max)},"
        f"{_fmt_int(row.up_avg)},{_fmt_int(row.up_max)},{_fmt_int(row.dl_total)},{_fmt_int(row.up_total)}"
    )


def format_z_row(start: int, end: int, dl_total: int, up_total: int) -> str:
    """零值行程行文本(v2 §02.1 逐列: z + 两个时间列 + totals 快照对)"""
    return f"z,{_fmt_int(start)},{_fmt_int(end)},{_fmt_int(dl_total)},{_fmt_int(up_total)}"


def _parse_int_field(text: str) -> Optional[int]:
    """数据列解析: 空 = None(null 列); 非负整数合法; 其余(负数/非数值)抛 ValueError -> 坏行"""
    if text == "":
        return None
    v = int(text)
    if v < 0:
        raise ValueError(f"负数列: {text}")
    return v


def parse_dat_text(text: str) -> ParsedSeries:
    """dat 文本 -> ParsedSeries(纯函数, 无文件访问)

    头行必须恰为 HEADER_LINE 或 HEADER_LINE_V2(缺失/不符 = 整文件不匹配格式, 全部行记坏);
    双读门闩(§02.2): 头行恰为 v2 才接受 z 行, 头行仍为 v1 时 z 行按坏行计数(v1 语义
    逐字节不变)。其后每行都计入 data_lines(损坏占比分母), key 行取首个(重复 key 行记坏),
    raw/hour/z 行按列解析, 空行/注释行跳过不计坏, 其余不匹配格式的一律跳过计数。无换行
    结尾的末段是崩溃残留位: 解析成功则照常收数据(缺的只是行尾换行, 追加侧会先补), 失败
    则记 torn_tail(豁免损坏占比)。hour 行同桶重复取最后一行(重封 upsert 的读侧口径,
    对齐 curves 重复日期先例)。z 行校验宽松(§02.2): 列数 = 5, 四数值列经 _parse_int_field
    (空/负/非数值 -> 坏行), end >= start 且 end - start <= ZRUN_MAX_SPAN_S —— 违者一律坏行。
    """
    lines = text.splitlines()
    torn = bool(text) and not text.endswith("\n")
    header = lines[0].strip() if lines else None
    if header not in (HEADER_LINE, HEADER_LINE_V2):
        # 头行缺失/不符: 文件级不匹配格式 —— 每一行都算坏行(损坏判定必然命中阈值)
        return ParsedSeries(key=None, raw=(), hours=(), bad_lines=len(lines), data_lines=len(lines), torn_tail=torn)
    accept_z = header == HEADER_LINE_V2
    key: Optional[str] = None
    raw_rows: list = []
    hours_by_epoch: dict = {}
    zruns: list = []
    bad = 0
    data = 0
    torn_tail = False
    last_idx = len(lines) - 1
    for i, line in enumerate(lines[1:]):
        data += 1
        s = line.strip()
        if not s or s.startswith("#"):
            continue  # 空行/注释行跳过不计坏(对齐 curves 空行先例)
        parts = s.split(",")
        try:
            if parts[0] == "key" and len(parts) == 2 and parts[1] and key is None:
                key = parts[1]
                continue
            if parts[0] == "raw" and len(parts) == RAW_FIELDS:
                raw_rows.append(
                    RawRow(
                        ts=int(parts[1]),
                        dl_rate=_parse_int_field(parts[2]),
                        up_rate=_parse_int_field(parts[3]),
                        dl_total=_parse_int_field(parts[4]),
                        up_total=_parse_int_field(parts[5]),
                    )
                )
                continue
            if parts[0] == "hour" and len(parts) == HOUR_FIELDS:
                row = HourRow(
                    hour_epoch=int(parts[1]),
                    dl_avg=_parse_int_field(parts[2]),  # type: ignore[arg-type]
                    dl_max=_parse_int_field(parts[3]),  # type: ignore[arg-type]
                    up_avg=_parse_int_field(parts[4]),  # type: ignore[arg-type]
                    up_max=_parse_int_field(parts[5]),  # type: ignore[arg-type]
                    dl_total=_parse_int_field(parts[6]),  # type: ignore[arg-type]
                    up_total=_parse_int_field(parts[7]),  # type: ignore[arg-type]
                )
                hours_by_epoch[row.hour_epoch] = row  # 同桶重复取最后一行
                continue
            if accept_z and parts[0] == "z" and len(parts) == Z_FIELDS:
                start = _parse_int_field(parts[1])
                end = _parse_int_field(parts[2])
                dl_total = _parse_int_field(parts[3])
                up_total = _parse_int_field(parts[4])
                if None in (start, end, dl_total, up_total):
                    raise ValueError("z 行存在空列")  # ZRow 恒非负整数, 无 null 形态
                if end < start or end - start > ZRUN_MAX_SPAN_S:
                    raise ValueError("z 行时间区间非法")
                zruns.append(ZRow(start=start, end=end, dl_total=dl_total, up_total=up_total))
                continue
        except (ValueError, IndexError):
            pass
        bad += 1  # 键名/列数不匹配或字段非法(v1 头行下的 z 行在此落网 —— 按坏行计数)
        if torn and i == last_idx - 1:
            torn_tail = True  # 尾部半行 = 正常崩溃残留(阈值豁免, 见 _read_path)
    hours = tuple(hours_by_epoch[e] for e in sorted(hours_by_epoch))
    return ParsedSeries(
        key=key,
        raw=tuple(raw_rows),
        hours=hours,
        bad_lines=bad,
        data_lines=data,
        torn_tail=torn_tail,
        zruns=tuple(zruns)
    )


class TrafficDatStore:
    """qb-traffic dat 存储层: writer(仅主循环线程) + reader(只读) + index/对账

    构造只算路径, 不触文件系统 —— 目录与文件全部惰性创建(首个产出点/首次对账时)。
    """
    def __init__(self, data_dir: str) -> None:
        self._root = os.path.join(data_dir, TRAFFIC_DIR_NAME)
        self._torrents_dir = os.path.join(self._root, TORRENTS_DIR_NAME)
        self._index_path = os.path.join(self._root, INDEX_NAME)
        self._index: dict = {}  # infohash -> {"frozen_at", "created_at", "updated_at"}
        self._index_dirty = False  # 内存条目变化未落盘(封口/对账时点统一冲刷)

    # ---------- 路径(§02.1) ----------

    @property
    def root_dir(self) -> str:
        return self._root

    @property
    def torrents_dir(self) -> str:
        return self._torrents_dir

    def series_path(self, key: str) -> str:
        """系列键 -> dat 路径; 非法键 fail-fast(绝不让畸形键派生出意外路径)"""
        if key == GLOBAL_KEY:
            return os.path.join(self._root, GLOBAL_DAT_NAME)
        if key.startswith(TORRENT_KEY_PREFIX):
            h = key[len(TORRENT_KEY_PREFIX):]
            if not h or not _INFOHASH_RE.match(h):
                raise ValueError(f"非法单种系列键(哈希须为文件名安全字符): {key!r}")
            return os.path.join(self._torrents_dir, h + DAT_SUFFIX)
        raise ValueError(f"未知系列键: {key!r}")

    # ---------- 写路径(仅主循环线程, §02.4 左) ----------

    def append_point(self, key: str, ts: float, dl_rate, up_rate, dl_total, up_total) -> None:
        """追加一行 raw(含 null 点行); 系列文件不存在则先建(头行 + key 行, 惰性建文件)。

        崩溃残留的尾部半行(无换行符)先补一个换行 —— 否则本行会与残行合并成一条坏行,
        崩溃丢失就从 <=1 行变成 2 行(§01.2「半行容错是自己的义务」的写侧兑现)。
        """
        path = self.series_path(key)  # 非法键在此 fail-fast
        self._ensure_layout()
        prefix = ""
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            prefix = f"{HEADER_LINE}\nkey,{key}\n"
        else:
            with open(path, "rb") as f:
                f.seek(-1, os.SEEK_END)
                if f.read(1) != b"\n":
                    prefix = "\n"
        if key.startswith(TORRENT_KEY_PREFIX):
            self._touch_entry(key[len(TORRENT_KEY_PREFIX):], ts)
        line = format_raw_row(ts, dl_rate, up_rate, dl_total, up_total)
        with open(path, "a", encoding="utf-8", newline="\n") as f:
            if prefix:
                f.write(prefix)
            f.write(line + "\n")
            f.flush()  # 每行即冲: 进程崩溃丢 <=1 行(§02.4)

    def append_z_run(self, key: str, start: int, end: int, dl_total: int, up_total: int) -> None:
        """追加一行零值行程(v2 §02.3): 与 append_point 同款追加纪律 —— open("a") + flush
        (崩溃丢 <=1 行); 崩溃残留的尾部半行先补一个换行(不与残行合并); 文件不存在则建
        头行 + key 行, 头行直接写 v2。

        R3 硬不变式: 绝不向 v1 头行文件追加 z 行 —— 追加前检查头行版本, v1 先做一次
        内容保持重写(仅头行升 v2)再追加; 升级失败(读侧竞态占满重试)本轮不追加,
        OSError 上抛(调用方按落盘失败口径处理, 原文件完好)。end 为行程终点 = 最后
        数据活动时刻, 单种条目 updated_at 据此推进(与 raw 追加同口径)。
        """
        path = self.series_path(key)  # 非法键在此 fail-fast
        self._ensure_layout()
        prefix = ""
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            prefix = f"{HEADER_LINE_V2}\nkey,{key}\n"  # 新文件头行直接 v2(§02.3)
        else:
            with open(path, "rb") as f:
                f.seek(-1, os.SEEK_END)
                if f.read(1) != b"\n":
                    prefix = "\n"
            if not self._upgrade_header_v1_to_v2(path):
                raise OSError(f"{os.path.basename(path)} v1 头行升级失败(读侧竞态), 本轮 z 行未追加")
        if key.startswith(TORRENT_KEY_PREFIX):
            self._touch_entry(key[len(TORRENT_KEY_PREFIX):], float(end))
        line = format_z_row(start, end, dl_total, up_total)
        with open(path, "a", encoding="utf-8", newline="\n") as f:
            if prefix:
                f.write(prefix)
            f.write(line + "\n")
            f.flush()  # 每行即冲: 进程崩溃丢 <=1 行(§02.4)

    def _upgrade_header_v1_to_v2(self, path: str) -> bool:
        """R3 头行升级: v1 头行文件做一次内容保持重写(仅首行换 v2, 其余行逐字节不变,
        绕过 same_content 短路 —— 升级本身就是本次的写目的); 重写失败(读侧竞态)返回
        False, 调用方必须放弃本轮 z 追加(硬不变式: 未升级绝不追加)。头行非 v1(已是
        v2 / 畸形头行)不动返回 True —— 畸形头行走既有损坏阈值口径, 不在此扩权。"""
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError as e:
            logger.warning(f"流量存储 | {os.path.basename(path)} 头行读取失败(z 行不追加): {e}")
            return False
        head, sep, rest = text.partition("\n")
        if head.strip() != HEADER_LINE:
            return True  # 已是 v2 或畸形头行: 畸形文件由损坏阈值处置, 追加口径同 append_point
        payload = HEADER_LINE_V2 + ("\n" + rest if sep else "\n")
        if not self._write_payload(path, payload):
            return False
        logger.debug(f"流量存储 | {os.path.basename(path)} 头行 v1 -> v2(首 z 追加, R3)")
        return True

    def seal_hour(
        self,
        key: str,
        hour_epoch: int,
        now: float,
        raw_window: float,
        rollup_window: float,
        interval_s: Optional[float] = None
    ) -> bool:
        """单桶封口 + 按窗裁剪(§02.4): 指定桶 upsert 重封(测试与迟到行兜底入口)

        interval_s: 混合桶加权均值的采样间隔(秒, plan 26-10-04-0721 §04.2); None 取
        DEFAULT_SAMPLE_INTERVAL_S(纯活跃/纯空闲桶不受影响, 默认路径向后兼容)。
        """
        return self._seal_file(key, now, raw_window, rollup_window, force_buckets=(hour_epoch, ), interval_s=interval_s)

    def seal_sweep(
        self,
        current_bucket: int,
        now: float,
        raw_window: float,
        rollup_window: float,
        interval_s: Optional[float] = None
    ) -> int:
        """小时封口扫描(catch-up 语义): global + torrents/ 全系列各补封全部未封桶(§02.4「逐系列」)

        归并 < current_bucket 的「有 raw 行或被 z 行覆盖且尚无 hour 行」的桶 —— 触发
        频率由采样器保证(每小时首个采样), 桶本身不依赖触发不缺席: 重启跨度 / 断连跳桶
        不会把已产出的 raw/z 行永远留在 hour 段之外; 已封桶不重算。行程跨小时边界时
        按交集拆权重进相邻两桶(§04.2)。顺带完成按窗裁剪(裁剪只在重写时发生, 空闲系列的
        窗外残行留待下次活动重写时自洁 —— 读侧按窗取数不受影响)。
        interval_s 语义同 seal_hour(None 取缺省 30s 口径, P2 起调用方传真实配置值)。
        返回发生 rewrite 的文件数(日志/测试用)。
        """
        keys = [GLOBAL_KEY]
        if os.path.isdir(self._torrents_dir):
            for name in sorted(os.listdir(self._torrents_dir)):
                if name.endswith(DAT_SUFFIX):
                    keys.append(TORRENT_KEY_PREFIX + name[:-len(DAT_SUFFIX)])
        rewritten = 0
        for key in keys:
            if self._seal_file(key, now, raw_window, rollup_window, due_before=current_bucket, interval_s=interval_s):
                rewritten += 1
        return rewritten

    def _seal_file(
        self,
        key: str,
        now: float,
        raw_window: float,
        rollup_window: float,
        force_buckets: tuple = (),
        due_before: Optional[int] = None,
        interval_s: Optional[float] = None,
    ) -> bool:
        """单文件封口: 归并待封桶出 hour 行 + 按窗裁剪, 有变化才重写; 返回是否 rewrite

        待封桶 = force_buckets(直接指定, upsert 重封 —— 已有同桶 hour 行也被替换)∪
        (due_before 之下「有 raw 行或被 z 行覆盖且尚无 hour 行」的桶 —— catch-up 补封,
        z 行覆盖的桶按行程与桶的交集逐桶纳入)。桶内全 null 行不产 hour 行(空桶 = null,
        §05.1); 被行程覆盖的桶可产(全空闲桶 avg=0/max=0, 混合桶加权 —— §04.2)。
        裁剪: raw 段留 ts >= now - raw_window, z 行同属 raw 段按 end >= now - raw_window
        留置(其派生 hour 行在 hour 段按 rollup_window 独立留置), hour 段留
        hour_epoch >= now - rollup_window(边界含)。内容无变化(无新行、无裁剪、无坏行、
        重封行与旧行相同, z 行纳入比较)则跳过重写 —— 空闲系列每小时扫描零写放大(黄金
        法则 1); 坏行(尾部半行等)不算内容一致 —— 随重写一并清除(自洁)。
        """
        path = self.series_path(key)
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            return False
        parsed = self._read_path(path)  # 损坏文件在此被移 .corrupt -> 视同空文件
        if parsed.key is None:
            return False
        due = set(force_buckets)
        if due_before is not None:
            raw_buckets = {(r.ts // HOUR_SECONDS) * HOUR_SECONDS for r in parsed.raw if r.ts < due_before}
            z_buckets = set()
            for z in parsed.zruns:  # 行程覆盖的桶逐桶纳入(span <= 86400, 至多 25 桶)
                b = (z.start // HOUR_SECONDS) * HOUR_SECONDS
                top = (z.end // HOUR_SECONDS) * HOUR_SECONDS
                while b <= top:
                    if b < due_before:
                        z_buckets.add(b)
                    b += HOUR_SECONDS
            due |= (raw_buckets | z_buckets) - {h.hour_epoch for h in parsed.hours}
        new_hours = []
        for b in sorted(due):
            row = self._aggregate_bucket(parsed.raw, parsed.zruns, b, interval_s)
            if row is not None:
                new_hours.append(row)
        replaced = {h.hour_epoch for h in new_hours}
        kept_raw = sorted((r for r in parsed.raw if r.ts >= now - raw_window), key=lambda r: r.ts)
        kept_z = tuple(sorted((z for z in parsed.zruns if z.end >= now - raw_window), key=lambda z: z.start))
        kept_hours = sorted(
            (h for h in parsed.hours if h.hour_epoch >= now - rollup_window and h.hour_epoch not in replaced),
            key=lambda h: h.hour_epoch,
        ) + new_hours
        same_content = (
            kept_hours == list(parsed.hours) and kept_raw == sorted(parsed.raw, key=lambda r: r.ts) and
            kept_z == tuple(sorted(parsed.zruns, key=lambda z: z.start)) and parsed.bad_lines == 0
        )
        if same_content:
            self._flush_index()  # 追加期内存推进的 updated_at 在封口时点落盘(§02.5)
            return False
        if not self._rewrite_file(path, key, tuple(kept_hours), tuple(kept_raw), kept_z):
            return False  # rewrite 被读侧竞态占满重试后放弃: 原文件完好, 下轮封口自然补上
        self._flush_index()
        return True

    def _rewrite_file(self, path: str, key: str, hours: tuple, raws: tuple, zruns: tuple = ()) -> bool:
        """整文件重写: 输出序 = 头行(v2, R3: 内容重写即升级) + key 行 + hour 行 + z 行 +
        raw 行(§02.3); 同目录 tmp -> fsync -> os.replace(纪律对齐 utils.atomic_write;
        行尾固定 \\n —— dat 是行式文本, 对齐 TM history.dat 先例, 与追加行一致)。
        PermissionError(Windows 读侧竞态)退避重试 x3, 仍失败放弃本轮(原文件完好)。"""
        lines = [HEADER_LINE_V2, f"key,{key}"]
        lines.extend(format_hour_row(h) for h in hours)
        lines.extend(format_z_row(z.start, z.end, z.dl_total, z.up_total) for z in zruns)
        lines.extend(format_raw_row(r.ts, r.dl_rate, r.up_rate, r.dl_total, r.up_total) for r in raws)
        return self._write_payload(path, "\n".join(lines) + "\n")

    def _write_payload(self, path: str, payload: str) -> bool:
        """payload 整文件写入: 同目录 tmp -> fsync -> os.replace; PermissionError
        (Windows 读侧竞态)退避重试 x3, 仍失败放弃(删 tmp, 返回 False, 原文件完好)。"""
        directory = os.path.dirname(path) or "."
        attempt = 0
        while True:
            fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=os.path.basename(path) + ".", suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
                    f.write(payload)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_path, path)
                return True
            except PermissionError:
                self._remove_quiet(tmp_path)
                attempt += 1
                if attempt > REWRITE_RETRIES:
                    logger.warning(f"流量存储 | {os.path.basename(path)} 重写被占用(读侧竞态), 放弃本轮(数据无损)")
                    return False
                time.sleep(REWRITE_BACKOFF_S)
            except BaseException:
                self._remove_quiet(tmp_path)
                raise

    @staticmethod
    def _remove_quiet(tmp_path: str) -> None:
        """清理残留 tmp(os.replace 已成功时不该走到这里); 清理失败不影响主流程"""
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    @staticmethod
    def _aggregate_bucket(raw_rows: tuple, zruns: tuple, hour_epoch: int,
                          interval_s: Optional[float]) -> Optional[HourRow]:
        """桶内归并出 hour 行(§02.3 + plan 26-10-04-0721 §04.2)

        - 纯活跃桶(只有非 null raw 行): avg 取整(round)/max 只计 raw 行, totals 取桶末
          (最新非 null 行)累计快照 —— v1 口径不变。
        - 纯空闲桶(只被 z 行覆盖, 无非 null raw 行): 产 avg=0/max=0 的 hour 行, totals
          取行程快照(空闲期计数不增长)。
        - 混合桶(既有活跃 raw 行又有 z 覆盖): avg 口径从 v1 的「活跃期均值」变为
          「加权小时均量」—— avg = (Σ raw 速率 + 0*w) / (n + w), 权重 w = 行程与本桶
          交集秒数 ÷ interval_s(interval_s None/非正取 DEFAULT_SAMPLE_INTERVAL_S, 与
          config 缺省同值; P2 起调用方传 config.qb_traffic.sample_interval); 行程跨
          小时边界按交集拆权重进相邻两桶; max 不受 0 权重影响; totals 取桶末观测快照
          (z 覆盖桶末时 = 行程快照, 空闲期与最后活跃样本同值无歧义; 纯活跃桶沿用
          「最新非 null 行」现行规则)。
        - 桶内全 null 行且无 z 覆盖 -> 不产 hour 行(空桶 = null, §05.1, 现行规则不变)。
        """
        bucket_end = hour_epoch + HOUR_SECONDS  # 桶 = 半开区间 [b, b+HOUR); 行程 = 闭区间 [start, end]
        rows = [r for r in raw_rows if hour_epoch <= r.ts < bucket_end and not r.is_null]
        overlap_s = 0
        z_end_cov = None  # 行程在本桶内的最晚观测秒(闭区间上界)
        z_snap = None  # 取到该上界的行程(桶末覆盖者)
        for z in zruns:
            lo = max(z.start, hour_epoch)
            hi = min(z.end, bucket_end - 1)
            if lo > hi:
                continue
            overlap_s += hi - lo + 1
            if z_end_cov is None or hi > z_end_cov:
                z_end_cov = hi
                z_snap = z
        if not rows and overlap_s == 0:
            return None
        n = len(rows)
        if not interval_s or interval_s <= 0:
            interval_s = DEFAULT_SAMPLE_INTERVAL_S
        w = overlap_s / interval_s  # 行程折算样本数(仅用于均值权重, §06.3)
        if rows:
            dl_avg = int(round(sum(r.dl_rate for r in rows) / (n + w)))
            up_avg = int(round(sum(r.up_rate for r in rows) / (n + w)))
            dl_max = max(r.dl_rate for r in rows)
            up_max = max(r.up_rate for r in rows)
        else:  # 纯空闲桶: 全程 0 观测
            dl_avg = dl_max = up_avg = up_max = 0
        last_raw = max(rows, key=lambda r: r.ts) if rows else None
        if z_snap is not None and (last_raw is None or z_end_cov >= last_raw.ts):
            last = z_snap  # 桶末观测由行程覆盖: totals 取行程快照
        else:
            last = last_raw
        return HourRow(
            hour_epoch=hour_epoch,
            dl_avg=dl_avg,
            dl_max=dl_max,
            up_avg=up_avg,
            up_max=up_max,
            dl_total=int(last.dl_total),
            up_total=int(last.up_total),
        )

    # ---------- 读路径(§02.4 右, 只读) ----------

    def read_series(self, key: str) -> ParsedSeries:
        """读单系列(一次性快读即关; S4 API 的取数入口)。文件缺失 = 空系列"""
        parsed, _read_ok = self.read_series_checked(key)
        if parsed.key is None:
            return ParsedSeries(key=key, raw=(), hours=(), bad_lines=parsed.bad_lines, data_lines=parsed.data_lines)
        return parsed

    def read_series_checked(self, key: str) -> tuple:
        """读单系列 + 读取健康位(S4 API 的判别取数入口; read_series 的可判别变体)

        返回 (ParsedSeries, read_ok): read_ok=False 仅当文件打开/读取抛 OSError
        (Windows rewrite 竞态等瞬态 —— §02.4 读侧竞态口径: 按空系列对待, 原文件无损);
        其余语义与 read_series 一致(文件缺失 = 空系列 + 健康; 损坏阈值处置后 = 空系列;
        头行 key 缺失不掩蔽数据行 —— API 以请求路径定位系列, 数据行照常消费)。
        健康位供 API 层区分「真没数据」与「这轮没读到」: 后者回退上一份响应并标
        meta.stale(§08), 不以空态冒充无数据。
        """
        path = self.series_path(key)
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            return ParsedSeries(key=key, raw=(), hours=(), bad_lines=0, data_lines=0), True
        text, ok = self._read_text(path)
        if text is None:
            return ParsedSeries(key=key, raw=(), hours=(), bad_lines=0, data_lines=0), False
        return self._parse_and_guard(path, text), True

    @staticmethod
    def _read_text(path: str) -> tuple:
        """整文件快读即关(<=205KB 设计上界); OSError -> (None, False) 按空系列对待(§02.4)"""
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return f.read(), True
        except OSError as e:
            logger.warning(f"流量存储 | {os.path.basename(path)} 读取失败(按空系列对待): {e}")
            return None, False

    def _parse_and_guard(self, path: str, text: str) -> ParsedSeries:
        """坏行计数 + 损坏阈值处置(>5% 且坏行 >= 2 移 .corrupt 后按空文件对待, §02.4)

        - 尾部半行(正常崩溃残留, torn_tail)从占比分子分母双侧扣除;
        - 坏行 >= 2 的绝对下限: 上一次崩溃的尾半行经「追加先补 \\n」后会成为中段坏行,
          小文件 1 行即超 5% —— 若据此整文件隔离, kill 的丢失就从 <=1 行放大成全文件,
          与 P2 验收冲突; 单行残留跳过即可, 随下一次封口重写自洁(坏行不算内容一致);
          真实损坏(盘损/格式错乱)坏行远不止 1 行, 阈值判据不受影响。
        """
        parsed = parse_dat_text(text)
        eff_bad = parsed.bad_lines - (1 if parsed.torn_tail else 0)
        eff_data = parsed.data_lines - (1 if parsed.torn_tail else 0)
        if eff_bad >= 2 and eff_data > 0 and eff_bad / eff_data > CORRUPT_RATIO:
            logger.warning(
                f"流量存储 | {os.path.basename(path)} 坏行占比超阈值"
                f"({eff_bad}/{eff_data} > {CORRUPT_RATIO:.0%}), 移 .corrupt 后按空文件重建"
            )
            if self._quarantine(path):
                return ParsedSeries(key=None, raw=(), hours=(), bad_lines=0, data_lines=0)
        return parsed

    def _read_path(self, path: str) -> ParsedSeries:
        """读 + 坏行计数 + 损坏阈值处置(写侧封口的读回入口; = _read_text + _parse_and_guard)"""
        text, _ok = self._read_text(path)
        if text is None:
            return ParsedSeries(key=None, raw=(), hours=(), bad_lines=0, data_lines=0)
        return self._parse_and_guard(path, text)

    def _quarantine(self, path: str) -> bool:
        """坏文件原文移 <name>.corrupt(已存在则覆盖 —— 只留最近一份现场); 失败不阻断读"""
        target = path + CORRUPT_SUFFIX
        try:
            os.replace(path, target)
            return True
        except OSError as e:
            logger.warning(f"流量存储 | {os.path.basename(target)} 移交失败(按解析结果继续): {e}")
            return False

    # ---------- index.json 与启动对账(§02.5) ----------

    def entry(self, infohash: str) -> Optional[dict]:
        """单种条目(只读视图; None = 无条目)"""
        e = self._index.get(infohash)
        return dict(e) if e is not None else None

    def has_entry(self, infohash: str) -> bool:
        """单种数据文件存在判定(plan 26-10-04-0721 §03.3): index 条目存在即有数据文件

        判据 = dict 查(零样本轮询每轮 <= 种子数次, 无 IO)。语义: 建文件与建条目同步
        (_touch_entry 惰性建文件时同步建条目, §02.5; 启动 reconcile 保证条目 <-> 文件
        一致) —— index 有条目即有数据文件。单种零样本开行程的门: 动过的种子停下 = 0 线
        (有条目 -> 开/推进行程); 从未传输的种子 = 无数据(无条目 -> 整体跳过, 空态)。
        """
        return infohash in self._index

    def _touch_entry(self, infohash: str, ts: float) -> None:
        """追加时点推进条目: 无条目则建(惰性建文件同步建条目, frozen_at 本阶段恒 None,
        §02.5)并立即落盘(建文件时点); 有条目仅内存推进 updated_at(封口时点统一落盘,
        非每采样写 index)。时间戳整数秒(§02.5 示例口径)。"""
        e = self._index.get(infohash)
        if e is None:
            self._index[infohash] = {"frozen_at": None, "created_at": int(ts), "updated_at": int(ts)}
            self._index_dirty = True
            self._flush_index()
            return
        e["updated_at"] = int(ts)
        self._index_dirty = True

    def _flush_index(self) -> None:
        """条目变化落盘(仅脏时写; atomic_write tmp+replace, §02.5)"""
        if not self._index_dirty:
            return
        payload = {"format": INDEX_FORMAT, "torrents": {k: self._index[k] for k in sorted(self._index)}}
        atomic_write(self._index_path, lambda f: json.dump(payload, f, indent=2))
        self._index_dirty = False

    def _load_index(self) -> None:
        """读 index.json(容错: 缺失 = 空表; 坏/半写/版本不符 = 空表自愈, 以磁盘文件为准)"""
        self._index = {}
        self._index_dirty = False
        if not os.path.exists(self._index_path):
            return
        try:
            with open(self._index_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError) as e:
            logger.warning(f"流量存储 | index.json 读取/解析失败(按空表自愈, 磁盘头行为准): {e}")
            return
        if not isinstance(data, dict) or data.get("format") != INDEX_FORMAT:
            logger.warning("流量存储 | index.json 版本/形状不符(按空表自愈, 磁盘头行为准)")
            return
        torrents = data.get("torrents")
        if not isinstance(torrents, dict):
            logger.warning("流量存储 | index.json torrents 段形状不符(按空表自愈)")
            return
        for h, e in torrents.items():
            if not isinstance(e, dict):
                logger.warning(f"流量存储 | index.json 条目 {h} 形状不符, 丢弃")
                continue
            self._index[h] = {
                "frozen_at": e.get("frozen_at"),
                "created_at": e.get("created_at"),
                "updated_at": e.get("updated_at"),
            }

    def reconcile(self) -> dict:
        """启动对账(§02.5): 扫目录与 index 求差并自愈; 只读目录与头行, 永不改写 raw/hour 数据

        - index 条目无文件 -> 删条目(手工删文件/盘损);
        - 孤儿 dat(index 无条目) -> 从头行 key, 重建条目(created/updated 取文件 mtime);
        - 头行 key 与文件名失配 = key 行损坏 -> 告警并按文件名登记(不改写文件)。
        返回计数(日志/测试用); 存储目录不存在时零动作(惰性创建纪律 —— 首个采样才建)。
        """
        counts = {"dropped_entries": 0, "recovered_entries": 0}
        self._load_index()
        # 1) 条目无文件 -> 删
        for h in list(self._index):
            if not os.path.exists(os.path.join(self._torrents_dir, h + DAT_SUFFIX)):
                del self._index[h]
                counts["dropped_entries"] += 1
        # 2) 文件无条目 -> 从头行重建
        if os.path.isdir(self._torrents_dir):
            for name in sorted(os.listdir(self._torrents_dir)):
                if not name.endswith(DAT_SUFFIX):
                    continue  # *.corrupt 等非系列文件不碰
                h = name[:-len(DAT_SUFFIX)]
                path = os.path.join(self._torrents_dir, name)
                header_key = self._read_header_key(path)
                if header_key is None:
                    logger.warning(f"流量存储 | {name} 无合法头行, 对账跳过(不登记不改动)")
                    continue
                if header_key != TORRENT_KEY_PREFIX + h:
                    logger.warning(f"流量存储 | {name} 头行 key 与文件名失配({header_key}), 按文件名登记(key 行损坏)")
                if h not in self._index:
                    mtime = int(os.path.getmtime(path))
                    self._index[h] = {"frozen_at": None, "created_at": mtime, "updated_at": mtime}
                    counts["recovered_entries"] += 1
        if counts["dropped_entries"] or counts["recovered_entries"]:
            self._index_dirty = True
            self._flush_index()
        return counts

    @staticmethod
    def _read_header_key(path: str) -> Optional[str]:
        """只读头行区取系列标识(纯 parse, 无阈值处置 —— 对账不改文件)"""
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read(4096)
        except OSError:
            return None
        return parse_dat_text(text).key

    # ---------- 生命周期: 冻结/解冻/按龄淘汰(§02.2/§02.5, S3) ----------

    def lifecycle_sweep(self, present_infohashes, now: float) -> dict:
        """冻结/解冻判定(§02.2 生命周期): 对照当前种子集合与 index 条目, 变化即落盘

        - 删种冻结: 条目未冻结 + 文件存在 + infohash 不在 present_infohashes =>
          frozen_at = now(整数秒), 停止追加(追加侧本就不产点 —— 不在集合内无采样;
          此处是注册表语义收口); 文件不存在的失配条目留给启动 reconcile, 不据以冻结;
        - 重加解冻: 已冻结条目的 infohash 重新出现在集合 => frozen_at = None, 历史保留
          续写(重加后 all-time 计数器回落由采样器判重置兜底, 本层不感知);
        - 两次判定都只动条目不动 dat 数据; 重复调用幂等(已冻结/未冻结各自稳定, 黄金
          法则 1), 无变化时零落盘(仅条目变化时点写 index, §02.5)。

        调用方 = 采样 handler(主循环线程, 黄金法则 5), 判定时机跟随采样轮; 断连轮的
        by_hash 是断连前快照(stale), 由调用方跳过本轮判定。present_infohashes 为空集
        是合法输入(qB 全库清空 => 全部未冻结条目冻结)。
        返回计数 {"frozen": n, "unfrozen": m}(日志/测试用)。
        """
        present = present_infohashes if isinstance(present_infohashes, (set, frozenset)) else set(present_infohashes)
        counts = {"frozen": 0, "unfrozen": 0}
        for h, e in self._index.items():
            if h in present:
                if e.get("frozen_at") is not None:
                    e["frozen_at"] = None
                    self._index_dirty = True
                    counts["unfrozen"] += 1
            elif e.get("frozen_at") is None and os.path.exists(os.path.join(self._torrents_dir, h + DAT_SUFFIX)):
                e["frozen_at"] = int(now)
                self._index_dirty = True
                counts["frozen"] += 1
        self._flush_index()  # 仅脏时写
        return counts

    def evict_expired_frozen(self, now: float, rollup_window: float) -> int:
        """冻结文件按龄淘汰(§02.5): frozen 且 now - updated_at > rollup_window =>
        删 dat 文件 + index 条目; 返回淘汰数(日志/测试用)

        调用时机 = 每小时封口时点顺带(复用封口触发, 无独立任务; 调用方义务)。global
        不在 index, 结构性豁免(永不冻结永不淘汰, §02.5)。updated_at = 最后数据活动
        时刻(内存真值): 冻结后不再追加即停摆, 超龄即该文件最新数据已滑出 hour 保留窗。
        文件已不存在(FileNotFoundError)也删条目(死条目自洁); 其余删除失败(Windows
        读侧竞态占文件)保留条目下轮重试 —— 条目与文件状态恒一致, 不产孤儿。条目
        updated_at 畸形(手工编辑 index)不据以删除, 留给人工处置。
        """
        evicted = 0
        for h in list(self._index):
            e = self._index[h]
            if e.get("frozen_at") is None:
                continue  # 未冻结不淘汰(追加与对账各自维护活跃/失配条目)
            updated = e.get("updated_at")
            if not isinstance(updated, (int, float)) or isinstance(updated, bool):
                continue
            if now - updated <= rollup_window:
                continue  # 未超龄不删
            path = os.path.join(self._torrents_dir, h + DAT_SUFFIX)
            try:
                os.remove(path)
            except FileNotFoundError:
                pass  # 文件早已不在: 死条目照常清
            except OSError as exc:
                logger.warning(f"流量存储 | {h + DAT_SUFFIX} 淘汰删除失败(下轮封口重试): {exc}")
                continue
            del self._index[h]
            self._index_dirty = True
            evicted += 1
        if evicted:
            self._flush_index()
        return evicted

    # ---------- 内部 ----------

    def _ensure_layout(self) -> None:
        """目录惰性创建(首个产出点时; exist_ok 幂等, §02.1)"""
        os.makedirs(self._torrents_dir, exist_ok=True)


# ======================================================================
# v3 纯函数区(plan 26-10-04-1957 S1, §02/§04/§06.2)
#
# 本区全部为 v3 行型与纯函数, **不接线**: 写侧仍 v2, 既有行为零改动; S2(写侧
# 翻转)/S3(读侧翻转) 时消费。换代语义(R2): v3 全部落 qb-traffic-v3/ 新目录, 旧
# qb-traffic/ 原样留存不读不迁移。
#
# 天文件行型(§02.1):
#     # auto-qb qb-traffic v3              文件头, 每文件一次(非 v3 头行整文件不匹配, 不设双读)
#     key,<系列标识>
#     B,<start_epoch>,<interval_s>         块头: start = 块首记录实测 epoch; 块结束 = 下一块头或文件尾
#     r,<dl>,<up>,<dlt>,<upt>[,<dt_ms>]    数据行 5 列无时间戳; dt_ms 可选 = 距上一记录实测毫秒数
#     z,<run_len>,<dlt>,<upt>[,<dt_ms>]    零速游程: 占 run_len 个采样槽, 速率恒 0
#     n,<run_len>[,<dt_ms>]                null 游程: 占 run_len 个采样槽(断连/缺字段)
# 全整数/毫秒口径: start_epoch/interval_s 整数秒(interval_s >= 1); dt_ms 正整数且
# <= DT_MS_MAX; 非法整行按坏行计数跳过、游标不推进(沿用 v2 坏行口径 + 损坏阈值隔离)。
#
# dt 链定约(§02.3 读侧规则 + §09.2 授权的实施期细化, S2 写侧必须同约定产出):
# - 游标 t = 上一已消费记录的槽位锚点; t0 = B.start = 块首记录实测 epoch(块首记录
#   槽位恰在 t0, 块首记录自身的 dt 列无语义, 写侧不写)。
# - r 记录: 槽位 = t + advance; advance = 显式 dt_ms 或标称 interval_s。显式 dt_ms =
#   距上一记录链上终点的实测毫秒数 —— 链上终点在上一记录显式时即其实测锚点, 故即
#   「距上一记录实际毫秒数」(§02.1)。
# - z/n 游程: advance = 显式 dt_ms 或标称 run_len x interval_s(§02.1 缺省口径);
#   run_len 个槽在 [t, t+advance] 内均摊(槽 k = t + k x advance/run_len, k=1..len,
#   末槽恰在 t+advance = 游程实测终点 last_seen); 显式 dt_ms = 游程开启时链上锚点
#   到末槽的实测毫秒数(OpenRun.start := 链上锚点 —— §09.2「z/n 相邻游程编码细节」
#   实施期定约: 相邻游程间的一次采样间隔并入后一游程的 dt_ms, 链式无系统误差);
#   其后记录的 dt 以游程终点(实测)为基准(§02.3) —— 链式自洽。
# - 块首记录为游程时特殊: B.start 即其首槽(块首无上一记录, 无引导间隔), 槽 k =
#   t0 + k x dt_ms/(run_len-1)(k=0..len-1, 端点含), 缺省按标称 interval。
# - 有效 dt(桶宽, §02.3): r = 显式 dt 或标称 interval; 游程槽 = 均摊 span/run_len。
# ======================================================================

#: 头行 v3(每文件一次; v3 读侧遇 v1/v2 旧头行直接忽略, 不设双读 —— R2 换代语义)
HEADER_LINE_V3 = "# auto-qb qb-traffic v3"

#: v3 存储根目录名(相对 data_dir, §06.2; 旧 qb-traffic/ 原样留存不读)
TRAFFIC_V3_DIR_NAME = "qb-traffic-v3"

#: v3 全局系列目录名(天文件 + agg.dat 的父目录)
V3_GLOBAL_DIR_NAME = "global"

#: v3 每系列聚合文件名(hour/day/month 9 列追加混存, §02.2)
V3_AGG_NAME = "agg.dat"

#: dt_ms 校验上界(毫秒, 一天; §02.1 全整数/毫秒口径)
DT_MS_MAX = 86_400_000

#: 写侧累积漂移容差(毫秒, 裁决 D2; 模块常量非配置键, §02.3)
DRIFT_TOL_MS = 250

#: agg 行字段数(kind + epoch + 6 数据列 + cov_s; §02.2 hour/day/month 同构)
AGG_FIELDS = 9

#: agg 8 列旧行型字段数(解析兜底 cov_s = 3600, 防御性 —— v3 全新目录正常不出现)
AGG_LEGACY_FIELDS = 8

#: agg 行型种类(§02.2)
AGG_KINDS = ("hour", "day", "month")

#: 本地日期串格式(天文件名与 day_epoch 口径, §06.2/§02.2)
V3_DATE_FORMAT = "%Y-%m-%d"

#: 逐级派生合法行型(§04.1: 严格逐级 —— day 只从 hour 行聚, month 只从 day 行聚)
V3_ROLLUP_KINDS = ("day", "month")

#: 天文件日期串形状(严格 4-2-2 位, 配合 strptime 拒绝 2 月 30 日等)
_V3_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True)
class V3Sample:
    """v3 数据记录(r 行): 速率对 + all-time totals 快照对; dt_ms = 距上一记录链上
    终点的实测毫秒数(写侧累积漂移 > DRIFT_TOL_MS 才写, §02.3), None = 标称 interval"""

    dl_rate: int
    up_rate: int
    dl_total: int
    up_total: int
    dt_ms: Optional[int] = None


@dataclass(frozen=True)
class V3ZeroRun:
    """v3 零速游程(z 行): 占 run_len 个采样槽, 速率恒 (0,0); dt_ms = 游程开启时链上
    锚点到末槽的实测毫秒数(§02.1 行程实际跨度, 缺省 = run_len x interval)"""

    run_len: int
    dl_total: int
    up_total: int
    dt_ms: Optional[int] = None


@dataclass(frozen=True)
class V3NullRun:
    """v3 null 游程(n 行): 占 run_len 个采样槽(断连/缺字段), 无观测; dt_ms 语义同 z"""

    run_len: int
    dt_ms: Optional[int] = None


@dataclass(frozen=True)
class V3Block:
    """v3 块: 块头 B + 记录序列(按槽序); 块不跨天(00:00 硬切, §03.3)"""

    start_epoch: int  # 块首记录实测 epoch 秒
    interval_s: int  # 本块采样间隔(整数秒, >= 1)
    records: tuple  # Tuple[V3Sample | V3ZeroRun | V3NullRun, ...]


@dataclass(frozen=True)
class V3ParsedDay:
    """单天文件解析结果(parse_v3_day_text 返回; S3 按天加载的入口形态, 纯数据)"""

    key: Optional[str]  # 头行 key 行的系列标识(无头行/坏头行/头行非 v3 时 None)
    blocks: tuple  # Tuple[V3Block, ...](文件序; 空块不保留)
    bad_lines: int  # 跳过的坏行数(含尾部半行)
    data_lines: int  # 受检行总数(头行后全部行; 损坏占比分母)
    torn_tail: bool = False  # 末尾未写完的半行(正常崩溃残留; 豁免损坏占比)


@dataclass(frozen=True)
class V3Slot:
    """v3 块内单槽展开(v3_block_slots 返回): 游标 dt 链推算出的观测点

    obs 形态: r 槽 = (dl_rate, up_rate, dl_total, up_total); z 槽 = (0, 0, dlt, upt)
    (空闲观测, totals 恒定); n 槽 = None(null)。ts 为浮点秒 —— 显式 dt_ms 带亚秒精度;
    dt_s = 距上一槽有效间隔(秒, §02.3 桶宽的有效 dt; 块首槽取标称 interval_s)。
    """

    ts: float
    dt_s: float
    obs: Optional[tuple]
    is_zero: bool  # True = z 游程槽(速率恒 0); n 槽为 False 且 obs = None


def _fmt_v3_dt_ms(dt_ms: Optional[int]) -> str:
    """可选 dt_ms 列文本(None = 缺省标称); 非法 fail-fast(写侧纪律 —— 解析侧按坏行)"""
    if dt_ms is None:
        return ""
    if not isinstance(dt_ms, int) or isinstance(dt_ms, bool) or dt_ms < 1 or dt_ms > DT_MS_MAX:
        raise ValueError(f"非法 dt_ms(须正整数且 <= {DT_MS_MAX}): {dt_ms!r}")
    return str(dt_ms)


def _fmt_v3_dt_tail(dt_ms: Optional[int]) -> str:
    """可选第 6 列的行尾段(空 = 不写该列)"""
    tail = _fmt_v3_dt_ms(dt_ms)
    return f",{tail}" if tail else ""


def format_v3_b_row(start_epoch: int, interval_s: int) -> str:
    """块头行文本(§02.1): B,<start_epoch>,<interval_s>; interval_s 须 >= 1 整数秒"""
    if not isinstance(interval_s, int) or isinstance(interval_s, bool) or interval_s < 1:
        raise ValueError(f"非法 interval_s(须 >= 1 整数秒): {interval_s!r}")
    return f"B,{_fmt_int(start_epoch)},{_fmt_int(interval_s)}"


def format_v3_r_row(rec: V3Sample) -> str:
    """数据行文本(§02.1): r,<dl>,<up>,<dlt>,<upt>[,<dt_ms>](5/6 列; 无 null 形态)"""
    return (
        f"r,{_fmt_int(rec.dl_rate)},{_fmt_int(rec.up_rate)},{_fmt_int(rec.dl_total)},{_fmt_int(rec.up_total)}"
        f"{_fmt_v3_dt_tail(rec.dt_ms)}"
    )


def format_v3_z_row(rec: V3ZeroRun) -> str:
    """零速游程行文本(§02.1): z,<run_len>,<dlt>,<upt>[,<dt_ms>]"""
    return f"z,{_fmt_int(rec.run_len)},{_fmt_int(rec.dl_total)},{_fmt_int(rec.up_total)}{_fmt_v3_dt_tail(rec.dt_ms)}"


def format_v3_n_row(rec: V3NullRun) -> str:
    """null 游程行文本(§02.1): n,<run_len>[,<dt_ms>]"""
    return f"n,{_fmt_int(rec.run_len)}{_fmt_v3_dt_tail(rec.dt_ms)}"


def format_v3_day_text(key: str, blocks: tuple) -> str:
    """v3 天文件整文件文本(头行 v3 + key 行 + 逐块 B 行与记录行; \\n 行尾, 对齐 v2
    输出纪律)。S2 flush 的批量写入口形态; 本函数只做序列化, 不触文件系统。"""
    lines = [HEADER_LINE_V3, f"key,{key}"]
    for b in blocks:
        lines.append(format_v3_b_row(b.start_epoch, b.interval_s))
        for rec in b.records:
            if isinstance(rec, V3Sample):
                lines.append(format_v3_r_row(rec))
            elif isinstance(rec, V3ZeroRun):
                lines.append(format_v3_z_row(rec))
            else:
                lines.append(format_v3_n_row(rec))
    return "\n".join(lines) + "\n"


def _parse_v3_dt_ms(text: str) -> int:
    """dt_ms 列解析(§02.1/§02.3): 须正整数且 <= DT_MS_MAX; 违者 ValueError -> 整行坏行"""
    v = int(text)  # 非数值抛 ValueError
    if v < 1 or v > DT_MS_MAX:
        raise ValueError(f"dt_ms 越界: {text}")
    return v


def _parse_v3_pos_int(text: str) -> int:
    """正整数列(run_len/interval_s); < 1 抛 ValueError"""
    v = int(text)
    if v < 1:
        raise ValueError(f"须正整数: {text}")
    return v


def _parse_v3_nn_int(text: str) -> int:
    """非空非负整数列(r/z 数据列 —— 无 null 形态, null 走 n 游程); 违者 ValueError"""
    v = _parse_int_field(text)
    if v is None:
        raise ValueError("空列")
    return v


def parse_v3_day_text(text: str) -> V3ParsedDay:
    """v3 天文件文本 -> V3ParsedDay(纯函数, 无文件访问; §02.1 逐字规格)

    头行必须恰为 HEADER_LINE_V3: 缺失/不符(含 v1/v2 旧头行 —— R2 换代, v3 读侧对旧
    格式不设双读)整文件不匹配格式, 全部行记坏。其后每行都计入 data_lines(损坏占比
    分母), key 行取首个(重复记坏), 空行/注释行跳过不计坏; B 行开新块(前块在下一块头
    或文件尾结束, 无记录的空块不保留), r/z/n 行按列解析, 其余一律跳过计数。坏行纪律
    (§02.3): r 行列数 ∈ {5,6}, z ∈ {4,5}, n ∈ {2,3}; dt_ms 须正整数且 <= DT_MS_MAX ——
    违者整行按坏行跳过、游标不推进(坏行不落 records, 后续行推算链不受影响)。无换行
    结尾的末段: 解析成功照常收数据, 失败记 torn_tail(豁免损坏占比, 对齐 v2 口径)。
    """
    lines = text.splitlines()
    torn = bool(text) and not text.endswith("\n")
    header = lines[0].strip() if lines else None
    if header != HEADER_LINE_V3:
        # 头行缺失/不符(含旧版头行): 文件级不匹配格式 —— 每一行都算坏行(损坏判定必然命中)
        return V3ParsedDay(key=None, blocks=(), bad_lines=len(lines), data_lines=len(lines), torn_tail=torn)
    key: Optional[str] = None
    blocks: list = []
    cur_start: Optional[int] = None
    cur_interval: Optional[int] = None
    cur_records: list = []

    def _close() -> None:
        nonlocal cur_start, cur_interval, cur_records
        if cur_start is not None and cur_records:
            blocks.append(V3Block(start_epoch=cur_start, interval_s=cur_interval, records=tuple(cur_records)))
        cur_start = None
        cur_interval = None
        cur_records = []

    bad = 0
    data = 0
    torn_tail = False
    last_idx = len(lines) - 1
    for i, line in enumerate(lines[1:]):
        data += 1
        s = line.strip()
        if not s or s.startswith("#"):
            continue  # 空行/注释行跳过不计坏(对齐 v2 先例)
        parts = s.split(",")
        try:
            if parts[0] == "key" and len(parts) == 2 and parts[1] and key is None:
                key = parts[1]
                continue
            if parts[0] == "B" and len(parts) == 3:
                # 先解析校验再切换块状态: 非法 B 行整行计坏, 既有块不受影响
                b_start = int(parts[1])
                b_interval = _parse_v3_pos_int(parts[2])
                _close()
                cur_start = b_start
                cur_interval = b_interval
                continue
            if cur_start is None:
                raise ValueError("块头前出现数据行")  # 游标无锚点, 记坏不消费
            if parts[0] == "r" and len(parts) in (5, 6):
                cur_records.append(
                    V3Sample(
                        dl_rate=_parse_v3_nn_int(parts[1]),
                        up_rate=_parse_v3_nn_int(parts[2]),
                        dl_total=_parse_v3_nn_int(parts[3]),
                        up_total=_parse_v3_nn_int(parts[4]),
                        dt_ms=_parse_v3_dt_ms(parts[5]) if len(parts) == 6 else None,
                    )
                )
                continue
            if parts[0] == "z" and len(parts) in (4, 5):
                cur_records.append(
                    V3ZeroRun(
                        run_len=_parse_v3_pos_int(parts[1]),
                        dl_total=_parse_v3_nn_int(parts[2]),
                        up_total=_parse_v3_nn_int(parts[3]),
                        dt_ms=_parse_v3_dt_ms(parts[4]) if len(parts) == 5 else None,
                    )
                )
                continue
            if parts[0] == "n" and len(parts) in (2, 3):
                cur_records.append(
                    V3NullRun(
                        run_len=_parse_v3_pos_int(parts[1]),
                        dt_ms=_parse_v3_dt_ms(parts[2]) if len(parts) == 3 else None,
                    )
                )
                continue
        except (ValueError, IndexError):
            pass
        bad += 1  # 键名/列数不匹配或字段非法(整行跳过, 游标不推进)
        if torn and i == last_idx - 1:
            torn_tail = True  # 尾部半行 = 正常崩溃残留(阈值豁免, 对齐 v2)
    _close()
    return V3ParsedDay(key=key, blocks=tuple(blocks), bad_lines=bad, data_lines=data, torn_tail=torn_tail)


def v3_block_slots(block: V3Block) -> tuple:
    """块内逐槽时间推算(游标 dt 链 + 均摊定位; §02.3 读侧规则, 纯函数)

    规则见模块 v3 纯函数区头注释「dt 链定约」: t0 = B.start; 每消费一记录游标推进
    (显式 dt_ms 或 槽位数 x interval_s x 1000)/1000 秒, r 槽落在新游标处, z/n 游程的
    run_len 个槽在 [t, t+advance] 内均摊(末槽恰在 t+advance = 游程实测终点), 其后
    记录的 dt 以游程终点为基准 —— 链式自洽。缺省按标称 interval; 显式 dt 行严格按
    实测推进。本函数只走 dt 链 —— 全路径不存在「时刻 = start + i x interval」的纯
    等间隔推算(测试钉住 d̄>0 序列无累积误差)。

    块首记录槽位恰在 B.start(其自身 dt 列无语义, 不消费); 块首记录为游程时首槽 =
    B.start、槽距 = dt_ms/(run_len-1)(端点含)或缺省标称 interval。
    返回 Tuple[V3Slot, ...](槽序 = 槽位升序 = 记录槽序展开)。
    """
    slots: list = []
    interval = float(block.interval_s)
    t = float(block.start_epoch)  # 游标 = 上一已消费记录的槽位锚点; 块首记录锚点 = B.start
    for idx, rec in enumerate(block.records):
        first = idx == 0
        if isinstance(rec, V3Sample):
            if first:
                advance = 0.0  # 块首记录槽位恰在 B.start(其 dt 列无语义, 不消费)
                dt_s = interval
            else:
                advance = (rec.dt_ms / 1000.0) if rec.dt_ms is not None else interval
                dt_s = advance
            slots.append(
                V3Slot(
                    ts=t + advance,
                    dt_s=dt_s,
                    obs=(rec.dl_rate, rec.up_rate, rec.dl_total, rec.up_total),
                    is_zero=False,
                )
            )
            t += advance
            continue
        if isinstance(rec, (V3ZeroRun, V3NullRun)):
            run_len = rec.run_len
            if first:
                # 块首游程: 首槽 = B.start, 端点含均摊(§09.2 实施期定约, 见区头注释);
                # 游标终点 = 末槽 = B.start + spacing x (run_len-1)
                spacing = (rec.dt_ms / 1000.0) / (run_len - 1) if (rec.dt_ms is not None and run_len > 1) else interval
                base = 0.0
            else:
                # 非块首游程: advance = 显式 dt(链上锚点 -> 末槽)或标称 run_len x interval;
                # 槽 k = t + k x advance/run_len(k=1..len), 均摊 span/run_len(§02.3);
                # 引导一次采样间隔(链上锚点 -> 首槽)并入 dt_ms, 游标终点 = 末槽
                advance = (rec.dt_ms / 1000.0) if rec.dt_ms is not None else run_len * interval
                spacing = advance / run_len
                base = spacing
            for k in range(run_len):
                if isinstance(rec, V3ZeroRun):
                    obs = (0, 0, rec.dl_total, rec.up_total)
                    is_zero = True
                else:
                    obs = None
                    is_zero = False
                slots.append(V3Slot(ts=t + base + spacing * k, dt_s=spacing, obs=obs, is_zero=is_zero))
            t += base + spacing * (run_len - 1)  # 游标 = 末槽 = 游程实测终点(链式自洽)
            continue
        raise TypeError(f"未知 v3 记录型: {type(rec).__name__}")
    return tuple(slots)


def v3_bucket_width_s(dt_s: float) -> int:
    """逐记录桶宽(秒): max(1, ceil(有效dt))(§02.3/§05.1 —— S3 归桶的纯函数层)"""
    return max(1, math.ceil(dt_s))


# ---------- v3 按天目录与路径解析(§06.2) ----------


def v3_root_dir(data_dir: str) -> str:
    """v3 存储根: <data_dir>/qb-traffic-v3/(§06.2; 旧 qb-traffic/ 原样留存不读)"""
    return os.path.join(data_dir, TRAFFIC_V3_DIR_NAME)


def v3_series_dir(data_dir: str, key: str) -> str:
    """系列键 -> 系列目录(global/ 或 torrents/<infohash>/); 非法键 fail-fast(对齐 v2)"""
    if key == GLOBAL_KEY:
        return os.path.join(v3_root_dir(data_dir), V3_GLOBAL_DIR_NAME)
    if key.startswith(TORRENT_KEY_PREFIX):
        h = key[len(TORRENT_KEY_PREFIX):]
        if not h or not _INFOHASH_RE.match(h):
            raise ValueError(f"非法单种系列键(哈希须为文件名安全字符): {key!r}")
        return os.path.join(v3_root_dir(data_dir), TORRENTS_DIR_NAME, h)
    raise ValueError(f"未知系列键: {key!r}")


def v3_day_file_path(data_dir: str, key: str, date_str: str) -> str:
    """系列键 + 本地日期串 -> 天文件路径(<YYYY-MM-DD>.dat); 日期串非法 fail-fast"""
    _validate_v3_date(date_str)
    return os.path.join(v3_series_dir(data_dir, key), date_str + DAT_SUFFIX)


def v3_agg_file_path(data_dir: str, key: str) -> str:
    """系列键 -> agg.dat 路径(§02.2: 每系列一个聚合文件)"""
    return os.path.join(v3_series_dir(data_dir, key), V3_AGG_NAME)


def v3_rel_dir_to_key(rel_dir: str) -> Optional[str]:
    """v3 根下相对目录 -> 系列键(global -> "global", torrents/<h> -> "torrent:<h>");
    不匹配返回 None(S3 扫目录时跳过非系列项)。两种路径分隔符都认(Windows 扫目录)"""
    norm = rel_dir.replace("\\", "/").strip("/")
    if norm == V3_GLOBAL_DIR_NAME:
        return GLOBAL_KEY
    if norm.startswith(TORRENTS_DIR_NAME + "/"):
        h = norm[len(TORRENTS_DIR_NAME) + 1:]
        if h and _INFOHASH_RE.match(h):
            return TORRENT_KEY_PREFIX + h
    return None


def v3_day_file_date(filename: str) -> Optional[str]:
    """天文件名 "<YYYY-MM-DD>.dat" -> 日期串; 其余(agg.dat/.corrupt/杂物/非真实日历
    日期形状)返回 None"""
    if not filename.endswith(DAT_SUFFIX):
        return None
    d = filename[:-len(DAT_SUFFIX)]
    if not _V3_DATE_RE.match(d):
        return None
    try:
        datetime.strptime(d, V3_DATE_FORMAT)  # 真实日期校验(2 月 30 日等)
    except ValueError:
        return None
    return d


def _validate_v3_date(date_str: str) -> None:
    """日期串校验: 形状 YYYY-MM-DD 且为真实日历日期; 违者 ValueError"""
    if not _V3_DATE_RE.match(date_str or ""):
        raise ValueError(f"非法日期串(须 YYYY-MM-DD): {date_str!r}")
    datetime.strptime(date_str, V3_DATE_FORMAT)  # 真实日期校验(2 月 30 日等)


def v3_date_str_epoch(date_str: str) -> int:
    """本地日期串 -> 当日 00:00 epoch(本地时区, §02.2 day_epoch 口径)"""
    _validate_v3_date(date_str)
    return int(datetime.strptime(date_str, V3_DATE_FORMAT).timestamp())


def v3_epoch_date_str(ts: float) -> str:
    """epoch 秒 -> 本地日期串(YYYY-MM-DD)"""
    return datetime.fromtimestamp(ts).strftime(V3_DATE_FORMAT)


def v3_day_epoch(ts: float) -> int:
    """epoch 秒 -> 本地当日 00:00 epoch(§02.2 day_epoch)"""
    d = datetime.fromtimestamp(ts)
    return int(datetime(d.year, d.month, d.day).timestamp())


def v3_month_epoch(ts: float) -> int:
    """epoch 秒 -> 本地自然月 1 日 00:00 epoch(§02.2 month_epoch)"""
    d = datetime.fromtimestamp(ts)
    return int(datetime(d.year, d.month, 1).timestamp())


def v3_window_dates(start_epoch: float, end_epoch: float) -> frozenset:
    """查询窗口起止(epoch 秒) -> 涉及的本地日期串集合(含两端所在日; §05.2 按天加载
    的窗口 -> 日期集合解析)。end < start -> ValueError(调用方口径错误, fail-fast)。"""
    if end_epoch < start_epoch:
        raise ValueError(f"窗口起止倒置: {start_epoch} > {end_epoch}")
    d0 = datetime.fromtimestamp(start_epoch).date()
    d1 = datetime.fromtimestamp(end_epoch).date()
    out = set()
    d = d0
    while d <= d1:
        out.add(d.strftime(V3_DATE_FORMAT))
        d += timedelta(days=1)
    return frozenset(out)


# ---------- v3 聚合行型(agg.dat, §02.2 + §04.1) ----------


@dataclass(frozen=True)
class AggRow:
    """v3 聚合行(§02.2): hour/day/month 同构 9 列, agg.dat 追加混存

    epoch 语义: hour = 桶起点; day = 本地当日 00:00; month = 本地自然月 1 日 00:00。
    cov_s = 有效时长秒(hour 必带 —— 8 列无法还原有效时长, 部分覆盖小时等权平均有偏)。
    """

    kind: str  # "hour" | "day" | "month"
    epoch: int
    dl_avg: int
    dl_max: int
    up_avg: int
    up_max: int
    dl_total: int
    up_total: int
    cov_s: int


class V3HourSample(NamedTuple):
    """hour 累计器的逐记录输入(§04.1): dt_s 由调用方裁剪到桶内(min(dt_i, hour_end-t_i));
    z 游程槽 rate=0/span 均摊(v3_block_slots 的 z 槽即此形态), n 槽不贡献(调用方剔除)"""

    dl_rate: int
    up_rate: int
    dl_total: int
    up_total: int
    dt_s: float


@dataclass(frozen=True)
class V3ParsedAgg:
    """agg.dat 解析结果(parse_v3_agg_text 返回)"""

    key: Optional[str]
    hours: tuple  # Tuple[AggRow, ...](epoch 升序, 同 epoch 取最后一行 —— :273 口径)
    days: tuple
    months: tuple
    bad_lines: int
    data_lines: int
    torn_tail: bool = False


def format_agg_row(row: AggRow) -> str:
    """agg 行文本(§02.2): <kind>,<epoch>,<dl_avg>,<dl_max>,<up_avg>,<up_max>,
    <dl_total>,<up_total>,<cov_s>(9 列); kind 须在 AGG_KINDS"""
    if row.kind not in AGG_KINDS:
        raise ValueError(f"非法聚合行型: {row.kind!r}")
    return (
        f"{row.kind},{_fmt_int(row.epoch)},{_fmt_int(row.dl_avg)},{_fmt_int(row.dl_max)},"
        f"{_fmt_int(row.up_avg)},{_fmt_int(row.up_max)},{_fmt_int(row.dl_total)},{_fmt_int(row.up_total)},"
        f"{_fmt_int(row.cov_s)}"
    )


def parse_v3_agg_text(text: str) -> V3ParsedAgg:
    """agg.dat 文本 -> V3ParsedAgg(纯函数; §02.2 + §04.4)

    头行必须恰为 HEADER_LINE_V3(缺失/不符整文件记坏, 同天文件口径); hour/day/month
    行 9 列, 8 列旧行兜底 cov_s = 3600(防御性, v3 全新目录正常不出现); 同 kind 同
    epoch 重复行取最后一行(traffic_store.py:273 口径沿用); 坏行纪律与天文件一致。
    返回按 kind 分列、epoch 升序。
    """
    lines = text.splitlines()
    torn = bool(text) and not text.endswith("\n")
    header = lines[0].strip() if lines else None
    if header != HEADER_LINE_V3:
        return V3ParsedAgg(
            key=None, hours=(), days=(), months=(), bad_lines=len(lines), data_lines=len(lines), torn_tail=torn
        )
    key: Optional[str] = None
    rows_by_kind: dict = {k: {} for k in AGG_KINDS}
    bad = 0
    data = 0
    torn_tail = False
    last_idx = len(lines) - 1
    for i, line in enumerate(lines[1:]):
        data += 1
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split(",")
        try:
            if parts[0] == "key" and len(parts) == 2 and parts[1] and key is None:
                key = parts[1]
                continue
            if parts[0] in AGG_KINDS and len(parts) in (AGG_LEGACY_FIELDS, AGG_FIELDS):
                # 8 列旧行兜底 cov_s = 3600(§02.2 防御性)
                cov = _parse_v3_nn_int(parts[8]) if len(parts) == AGG_FIELDS else HOUR_SECONDS
                row = AggRow(
                    kind=parts[0],
                    epoch=int(parts[1]),
                    dl_avg=_parse_v3_nn_int(parts[2]),
                    dl_max=_parse_v3_nn_int(parts[3]),
                    up_avg=_parse_v3_nn_int(parts[4]),
                    up_max=_parse_v3_nn_int(parts[5]),
                    dl_total=_parse_v3_nn_int(parts[6]),
                    up_total=_parse_v3_nn_int(parts[7]),
                    cov_s=cov,
                )
                rows_by_kind[row.kind][row.epoch] = row  # 同 epoch 重复取最后一行(:273 口径)
                continue
        except (ValueError, IndexError):
            pass
        bad += 1
        if torn and i == last_idx - 1:
            torn_tail = True
    by_kind = {k: tuple(rows_by_kind[k][e] for e in sorted(rows_by_kind[k])) for k in AGG_KINDS}
    return V3ParsedAgg(
        key=key,
        hours=by_kind["hour"],
        days=by_kind["day"],
        months=by_kind["month"],
        bad_lines=bad,
        data_lines=data,
        torn_tail=torn_tail,
    )


def v3_hour_agg(hour_epoch: int, samples: tuple) -> AggRow:
    """hour 聚合行(dt 加权, §04.1): avg = round(Σ(rate_i x dt_i) / cov_s),
    cov_s = min(Σdt_i, HOUR_SECONDS); max 取逐记录最大; totals 取级末快照(末记录);
    cov_s = 0(无有效覆盖)或空 samples -> ValueError(hour 行只在有覆盖时产出, 调用方
    义务)。dt_i 恒等于 interval_s 时严格退化为现行 _aggregate_bucket 纯活跃桶公式
    (avg = round(Σrate/n), traffic_store.py:653-657 口径) —— 测试对照钉住。"""
    if not samples:
        raise ValueError("hour 聚合无样本")
    cov = min(sum(s.dt_s for s in samples), float(HOUR_SECONDS))
    if cov <= 0:
        raise ValueError("hour 聚合无有效覆盖")
    last = samples[-1]
    return AggRow(
        kind="hour",
        epoch=hour_epoch,
        dl_avg=int(round(sum(s.dl_rate * s.dt_s for s in samples) / cov)),
        dl_max=max(s.dl_rate for s in samples),
        up_avg=int(round(sum(s.up_rate * s.dt_s for s in samples) / cov)),
        up_max=max(s.up_rate for s in samples),
        dl_total=int(last.dl_total),
        up_total=int(last.up_total),
        cov_s=int(round(cov)),
    )


class TrafficV3Store:
    """v3 写侧存储(S2a, plan 26-10-04-1957 §03.3): 按天文件块化追加 + 批量落盘

    写侧翻转后的落盘单点: 采样模块 BlockBuffer 每系列每 flush 单次 open("a") 写 N 行 +
    flush + fsync; 尾字节查补(崩溃残留半行补 \\n)每 flush 仅一次; 块头(B 行)由调用方在
    块首次 flush 时随批传入(块状态单点在采样模块 —— 跨 flush 的同块只传一次头)。
    只写 qb-traffic-v3/, 不触旧 qb-traffic/ 与 index.json(R2 换代); 目录惰性创建。
    S2b 接缝: 聚合封口(hour/day/month 行)将 append 到 v3_agg_file_path(同款追加纪律)。
    OSError 上抛(调用方按落盘失败口径处理 —— 观测数据丢失无一致性后果, §01.1)。
    """
    def __init__(self, data_dir: str) -> None:
        self._data_dir = data_dir

    @property
    def data_dir(self) -> str:
        return self._data_dir

    def series_day_path(self, key: str, date_str: str) -> str:
        """系列键 + 本地日期串 -> 天文件路径(路径计算复用 S1 纯函数, 非法键/日期 fail-fast)"""
        return v3_day_file_path(self._data_dir, key, date_str)

    def series_has_data(self, key: str) -> bool:
        """「系列目录存在且含 >=1 个 .dat」(§3.2: v2 index 条目门改目录判定, 惰性零目录零 IO)

        门语义(v2 §3.3 平移): 有数据(或已开游程)的系列零样本才开/延长游程, 从未传输种子
        零文件零游程。agg.dat 亦以 .dat 结尾, 计入(有聚合必有历史, 语义一致)。
        """
        series_dir = v3_series_dir(self._data_dir, key)
        if not os.path.isdir(series_dir):
            return False
        try:
            for name in os.listdir(series_dir):
                if name.endswith(DAT_SUFFIX):
                    return True
        except OSError:
            return False
        return False

    def append_records(self, key: str, date_str: str, header: Optional[tuple], records: tuple) -> None:
        """块化追加一批记录(§03.3 批量写): 单次 open("a") + flush + fsync

        header = (start_epoch, interval_s) 时先写 B 行(该块首次 flush; 跨 flush 的同块
        由调用方只传一次); records 为 V3Sample / V3ZeroRun / V3NullRun 序列(按槽序)。
        文件不存在先建头行(v3) + key 行; 崩溃残留尾部半行先补一个换行(不与残行合并,
        每 flush 查补一次 —— v2 逐行查补退役)。records 与 header 全空 = 零操作。
        """
        if header is None and not records:
            return
        path = self.series_day_path(key, date_str)  # 非法键/日期在此 fail-fast
        os.makedirs(os.path.dirname(path), exist_ok=True)
        prefix = ""
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            prefix = f"{HEADER_LINE_V3}\nkey,{key}\n"
        else:
            with open(path, "rb") as f:
                f.seek(-1, os.SEEK_END)
                if f.read(1) != b"\n":
                    prefix = "\n"
        lines = []
        if header is not None:
            lines.append(format_v3_b_row(int(header[0]), int(header[1])))
        for rec in records:
            if isinstance(rec, V3Sample):
                lines.append(format_v3_r_row(rec))
            elif isinstance(rec, V3ZeroRun):
                lines.append(format_v3_z_row(rec))
            else:
                lines.append(format_v3_n_row(rec))
        with open(path, "a", encoding="utf-8", newline="\n") as f:
            f.write(prefix)
            f.write("\n".join(lines) + "\n")
            f.flush()
            os.fsync(f.fileno())


def v3_rollup_agg(kind: str, epoch: int, children: tuple) -> AggRow:
    """逐级派生聚合行(§04.1, 严格逐级 —— day 只从 hour 行聚, month 只从 day 行聚,
    day 不从 raw 直聚: raw_window 裁剪边缘的 cov_s 链只在逐级传递才完整):
    avg = round(Σ(下级.avg x 下级.cov) / Σcov), max = max(下级.max), totals = 级末快照
    (epoch 最大的下级行), cov = Σ下级.cov。kind 限 {"day","month"}(hour 由 v3_hour_agg
    从记录直聚); children 空或 Σcov <= 0 -> ValueError。"""
    if kind not in V3_ROLLUP_KINDS:
        raise ValueError(f"非法逐级聚合行型(须 day/month): {kind!r}")
    if not children:
        raise ValueError("逐级聚合无下级行")
    cov = sum(c.cov_s for c in children)
    if cov <= 0:
        raise ValueError("逐级聚合无有效覆盖")
    last = max(children, key=lambda c: c.epoch)
    return AggRow(
        kind=kind,
        epoch=epoch,
        dl_avg=int(round(sum(c.dl_avg * c.cov_s for c in children) / cov)),
        dl_max=max(c.dl_max for c in children),
        up_avg=int(round(sum(c.up_avg * c.cov_s for c in children) / cov)),
        up_max=max(c.up_max for c in children),
        dl_total=int(last.dl_total),
        up_total=int(last.up_total),
        cov_s=int(cov),
    )
