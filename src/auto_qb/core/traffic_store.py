"""traffic_store: qB 口径流量 v3 存储层(plan 26-10-04-1957 §02 格式规格/§03 写侧/§04 聚合/§05 读侧)

【格式 v3 契约 —— 主题事实单点(计划 §09.2, memory-bank 无 qb-traffic 独立主题文档)】
v1/v2 逐行格式及其写侧/解析已随 S5 退役删除; v3 读侧遇旧头行按「整文件不匹配格式」
整文件记坏(R2 换代不设双读) —— 本 docstring 即现行唯一格式契约。

数据落点(§01.1 观测/日志数据: append-only、丢失无一致性后果; §06.2 R2 换代):
    <data_dir>/qb-traffic-v3/
      global/<YYYY-MM-DD>.dat + agg.dat                  # 全局系列
      torrents/<infohash>/<YYYY-MM-DD>.dat + agg.dat     # 每有数据种子一目录(组不落盘)
v3 全部写新目录; 旧 qb-traffic/ 原样留存不读不迁移(删留决定权在用户)。目录惰性创建;
enabled=false(含 qb_traffic None)全程零文件零目录(保守默认, 黄金法则 2)。

天文件行型(§02.1 逐列冻结; 全整数/毫秒口径; 坏行整行跳过计数、游标不推进):
    # auto-qb qb-traffic v3              文件头, 每文件一次(头行必须恰为 v3)
    key,<系列标识>                        global 固定 key,global; torrents/ = torrent:<infohash>
    B,<start_epoch>,<interval_s>         块头: start = 块首记录实测 epoch(整数秒); 块不跨天(00:00 硬切)
    r,<dl>,<up>,<dlt>,<upt>[,<dt_ms>]    数据行 5 列无时间戳; dt_ms 可选 = 距上一记录实测毫秒
    z,<run_len>,<dlt>,<upt>[,<dt_ms>]    零速游程: 占 run_len 个采样槽, 速率恒 (0,0)
    n,<run_len>[,<dt_ms>]                null 游程: 占 run_len 个采样槽(断连/缺字段)
- r 行无 null 形态(null 走 n 游程); z 游程 totals 快照恒定(空闲期 all-time 计数不增长)。
- dt_ms: 正整数且 <= DT_MS_MAX; 写侧累积漂移 <= DRIFT_TOL_MS(250ms, D2)时缺省(按标称
  interval / run_len x interval 推进); 时钟回拨钳制 dt_ms >= 1。dt 链定约(§02.3, 读写两侧
  同源)见「v3 纯函数区」头注释: 游标 = 上一已消费记录槽位锚点, 游程槽均摊, 链式自洽;
  全路径无纯等间隔推算(证伪用例钉住)。
- 撕裂尾半行(崩溃残留)豁免损坏占比; 坏行占比超阈值的隔离处置在解析纪律内计数呈现。

聚合文件 agg.dat(§02.2, 每系列一个, hour/day/month 9 列追加混存):
    <kind>,<epoch>,<dl_avg>,<dl_max>,<up_avg>,<up_max>,<dl_total>,<up_total>,<cov_s>
- epoch: hour = 桶起点 / day = 本地当日 00:00 / month = 自然月 1 日 00:00; cov_s = 有效
  覆盖秒(hour 必带 —— 8 列无法还原有效时长)。同 kind 同 epoch 重复行取最后一行(重封 =
  追加行, 读侧口径)。
- 8 列旧行兜底 cov_s = 3600(AGG_LEGACY_FIELDS, 防御性保留 —— v3 全新目录正常不出现,
  计划 §02.2 明文)。
- 严格逐级派生(§04.1): day 只从 hour 行聚, month 只从 day 行聚, day 不从 raw 直聚
  (cov_s 链只在逐级传递才完整)。

换代语义与保留窗(§04.5/§06.1):
- rollup_window 三义合一: hour 行保留窗 + 系列淘汰龄 + catch-up 补算窗口(= 天文件存活期);
  raw_window 语义不变(raw 段 = 按天整文件存删)。
- 淘汰: 系列最新天文件日期距 now 超 rollup_window -> 整目录删除(天文件 + agg.dat), 龄期
  由文件名日期直接算(v2 注册表机制退役); frozen 照删; 全局结构性豁免。
- catch-up(§04.3): 停机 < rollup_window 重启逐级补算(hour <- 窗口内天文件 raw / day <-
  hour 行 / month <- day 行), 硬序 catch-up 先于裁剪; 停机超窗天文件已删, 缺失跳过不标注
  (图上真空, 与块间 gap 语义一致)。

写路径(§03, 仅主循环线程 —— 黄金法则 5, 本层无锁): 每系列每 flush_interval 单次
open("a") 批量追加 + flush + fsync(崩溃窗口 <= flush_interval, 丢失形态与真空同形);
尾字节查补每 flush 一次; agg 行随 flush 时点水位封口合并追加(piggyback, 至多 +1 次
open); 唯一原子重写点 = hour 裁剪(tmp+fsync+os.replace); stop() 优雅退出全量落盘
(封游程 + flush + 聚合封口)。OSError 上抛(调用方按落盘失败口径处理)。

读路径(§05, Web 线程只读): 按窗口日期集合只读涉及天文件(24h 窗至多 2 个), V3DayCache
mtime_ns+size 键控解析缓存; 3d+ 窗只读成员 agg.dat 单文件; OSError 上抛由端点按竞态
降级处理(回退 last-good 标 stale, 不以空态冒充无数据)。
"""
import logging
import math
import os
import re
import shutil
import tempfile
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import NamedTuple, Optional

logger = logging.getLogger(__name__)

#: 单种 dat 子目录名
TORRENTS_DIR_NAME = "torrents"

#: dat 文件后缀
DAT_SUFFIX = ".dat"

#: 全局系列键(与采样器 GLOBAL_SERIES_KEY 同值; 本层不 import 采样模块, 字面量对齐)
GLOBAL_KEY = "global"

#: 单种系列键前缀(与采样器 _TORRENT_KEY_PREFIX 同值)
TORRENT_KEY_PREFIX = "torrent:"

#: rewrite 遇 PermissionError 的重试次数(不含首次; §02.4 x3)
REWRITE_RETRIES = 3

#: rewrite 重试退避间隔(秒)
REWRITE_BACKOFF_S = 0.05

#: 小时桶宽(秒)
HOUR_SECONDS = 3600

#: 单种哈希合法字符(infohash 实际为 hex, 但 FakeTorrent 式测试哈希与宽容口径取
#: 文件名安全集: 字母/数字/下划线/连字符 —— 排除路径分隔符与点, 非法键 fail-fast)
_INFOHASH_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _fmt_int(v: int) -> str:
    """数值列统一整数文本(qB 计数字段本身整型; 浮点输入截断存储, 口径全链一致)"""
    return str(int(v))


def _parse_int_field(text: str) -> Optional[int]:
    """数据列解析: 空 = None(null 列); 非负整数合法; 其余(负数/非数值)抛 ValueError -> 坏行"""
    if text == "":
        return None
    v = int(text)
    if v < 0:
        raise ValueError(f"负数列: {text}")
    return v


def _parse_int_field(text: str) -> Optional[int]:
    """数据列解析: 空 = None(null 列); 非负整数合法; 其余(负数/非数值)抛 ValueError -> 坏行"""
    if text == "":
        return None
    v = int(text)
    if v < 0:
        raise ValueError(f"负数列: {text}")
    return v


# ======================================================================
# v3 纯函数区(plan 26-10-04-1957 S1, §02/§04/§06.2)
#
# v1/v2 旧格式与其写侧/解析已随 S5 退役删除(换代语义 R2): v3 全部落 qb-traffic-v3/
# 新目录, 旧 qb-traffic/ 原样留存不读不迁移; 本区为现行唯一实现。
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


def v3_next_month_epoch(ts: float) -> int:
    """epoch 秒 -> 下一自然月 1 日 00:00 epoch(S3b all 视图逐月铺格用): ts 所在月的
    次月 1 日 00:00(本地时区); 结果严格大于输入(逐月推进必终止)。"""
    d = datetime.fromtimestamp(int(ts))
    year, month = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    return int(datetime(year, month, 1).timestamp())


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
    hours: tuple  # Tuple[AggRow, ...](epoch 升序, 同 epoch 取最后一行 —— 重封追加行读侧口径)
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
    epoch 重复行取最后一行(重封 = 追加行的读侧口径); 坏行纪律与天文件一致。
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
                rows_by_kind[row.kind][row.epoch] = row  # 同 epoch 重复取最后一行(重封读侧口径)
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
    (avg = round(Σrate/n)) —— 测试对照钉住。"""
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
    """v3 写侧存储(S2a 天文件 + S2b 聚合, plan 26-10-04-1957 §03.3/§04): 按天文件块化
    追加 + 批量落盘 + agg.dat 聚合行追加/裁剪 + 系列按龄淘汰

    写侧翻转后的落盘单点: 采样模块 BlockBuffer 每系列每 flush 单次 open("a") 写 N 行 +
    flush + fsync; 尾字节查补(崩溃残留半行补 \\n)每 flush 仅一次; 块头(B 行)由调用方在
    块首次 flush 时随批传入(块状态单点在采样模块 —— 跨 flush 的同块只传一次头)。
    只写 qb-traffic-v3/, 不触旧 qb-traffic/(R2 换代); 目录惰性创建。

    S2b 聚合分层(§04, 累计器/水位在采样模块, 本层只管文件):
    - append_agg_rows: 聚合行(hour/day/month 9 列)追加, 与 append_records 同款追加纪律
      (open("a") + flush + fsync, 每 flush 至多一次 open —— piggyback 语义);
    - read_agg / series_day_dates / series_keys: 重启恢复(catch-up)的读取入口;
    - trim_agg_hours: hour 行按 rollup_window 裁剪 —— v3 唯一的 tmp+fsync+os.replace
      原子重写点(§04.5, 常规写路径全是追加); 无到龄行零写(same_content 语义);
    - evict_expired_series: 超龄系列整目录删除(天文件 + agg.dat), 龄期由天文件名日期
      直接算, frozen 照删, 全局豁免。淘汰/裁剪触发点都在采样模块的 flush 时点。

    rollup_window v3 语义(§06.1 扩一句): hour 行保留窗 + 系列淘汰龄 + catch-up 补算
    窗口(= 天文件存活期)三义合一, 不再只是 v2 的 hour 段保留窗; raw_window 语义不变。
    day/month 行永久(D7 不设上限键); 注意 §04.5 淘汰口径是删整目录(天文件 + agg.dat),
    被淘汰系列的月行随目录一并消失 —— 「月行永久」指不按龄裁剪, 非目录删除后仍可读。

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

    # ---------- S2b: 聚合文件(agg.dat)与淘汰(§04) ----------

    def read_agg(self, key: str) -> V3ParsedAgg:
        """读系列 agg.dat(§04.3 恢复入口): 缺失/空文件 = 空解析结果(key=None, 全空元组);
        OSError 上抛(调用方按恢复失败口径处理)。解析坏行/同 epoch 取最后一行等纪律
        全在 parse_v3_agg_text(撕裂尾行跳过, 水位从文件尾推)。
        读侧快读口径(D3, §05.2): agg.dat 单次快读上界按 ~1MB 口径放宽(全年 hour 行
        ≈8760 x ~90B + day/month 行) —— 口径记录非强制截断, S3b 视图读取沿用本入口。"""
        path = v3_agg_file_path(self._data_dir, key)
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            return V3ParsedAgg(key=None, hours=(), days=(), months=(), bad_lines=0, data_lines=0)
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return parse_v3_agg_text(f.read())

    def append_agg_rows(self, key: str, rows: tuple) -> None:
        """追加一批聚合行(§04.2): 与 append_records 同款追加纪律 —— 单次 open("a") +
        flush + fsync, 尾字节查补一次, 文件不存在先建头行(v3) + key 行。调用方每系列
        每 flush 至多一次调用(piggyback 语义: hour/day/month 行合并一批)。rows 空 = 零操作。"""
        rows = tuple(rows)
        if not rows:
            return
        path = v3_agg_file_path(self._data_dir, key)  # 非法键 fail-fast
        os.makedirs(os.path.dirname(path), exist_ok=True)
        prefix = ""
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            prefix = f"{HEADER_LINE_V3}\nkey,{key}\n"
        else:
            with open(path, "rb") as f:
                f.seek(-1, os.SEEK_END)
                if f.read(1) != b"\n":
                    prefix = "\n"
        with open(path, "a", encoding="utf-8", newline="\n") as f:
            f.write(prefix)
            f.write("\n".join(format_agg_row(r) for r in rows) + "\n")
            f.flush()
            os.fsync(f.fileno())

    def series_keys(self) -> list:
        """扫描 v3 根目录列出现存系列键(§04.3 恢复入口): global/ + torrents/<infohash>/
        (目录存在即列出, 数据有无由调用方读文件判断); 根目录缺失 = 空表。"""
        root = v3_root_dir(self._data_dir)
        keys: list = []
        if os.path.isdir(os.path.join(root, V3_GLOBAL_DIR_NAME)):
            keys.append(GLOBAL_KEY)
        torrents_dir = os.path.join(root, TORRENTS_DIR_NAME)
        if os.path.isdir(torrents_dir):
            for name in sorted(os.listdir(torrents_dir)):
                if _INFOHASH_RE.match(name) and os.path.isdir(os.path.join(torrents_dir, name)):
                    keys.append(TORRENT_KEY_PREFIX + name)
        return keys

    def series_day_dates(self, key: str, min_epoch: float) -> tuple:
        """系列目录内天文件日期串(升序), 仅保留 date 00:00 epoch >= min_epoch 的
        (补算窗口过滤, §04.3 —— rollup_window 外的天文件已删/不读); 目录缺失 = 空表;
        非日期杂物(agg.dat/.corrupt 等)跳过。"""
        try:
            names = os.listdir(v3_series_dir(self._data_dir, key))
        except OSError:
            return ()
        out = []
        for name in names:
            d = v3_day_file_date(name)
            if d is not None and v3_date_str_epoch(d) >= min_epoch:
                out.append(d)
        return tuple(sorted(out))

    def read_day(self, key: str, date_str: str) -> Optional[V3ParsedDay]:
        """读单天文件(§04.3 catch-up 的 raw 源): 缺失/空文件 = None; OSError 上抛。"""
        path = self.series_day_path(key, date_str)
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            return None
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return parse_v3_day_text(f.read())

    def trim_agg_hours(self, key: str, now: float, rollup_window: float) -> Optional[int]:
        """hour 行按 rollup_window 裁剪(§04.5, v3 唯一 tmp+fsync+os.replace 原子重写点):
        保留 hour.epoch >= now - rollup_window(边界含)的 hour 行, day/month 行全保留
        (永久, D7); 无到龄行零写(same_content 语义, 返回现存最老 hour epoch);
        撕裂尾行/坏行随重写自洁。PermissionError(Windows 读侧竞态)退避重试后仍失败则
        放弃本轮(原文件完好), 返回原最老 epoch。返回重写后的最老 hour epoch(空 = None)。"""
        path = v3_agg_file_path(self._data_dir, key)
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            return None
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            parsed = parse_v3_agg_text(f.read())
        kept = tuple(h for h in parsed.hours if h.epoch >= now - rollup_window)
        oldest = parsed.hours[0].epoch if parsed.hours else None
        if len(kept) == len(parsed.hours):
            return oldest  # 无到龄行: 零写(黄金法则 1)
        lines = [HEADER_LINE_V3, f"key,{key}"]
        lines.extend(format_agg_row(r) for r in kept)
        lines.extend(format_agg_row(r) for r in parsed.days)
        lines.extend(format_agg_row(r) for r in parsed.months)
        if _write_text_payload(path, "\n".join(lines) + "\n"):
            return kept[0].epoch if kept else None
        return oldest

    def evict_expired_series(self, now: float, rollup_window: float) -> list:
        """单种系列按龄淘汰(§04.5 新口径): 系列目录内最新天文件日期的 00:00 epoch 距
        now 超过 rollup_window -> 整目录删除(天文件 + agg.dat); 龄期由文件名日期直接算
        (注册表机制退役, S5); frozen 与否不豁免(删种即不再产新块与聚合, 文件
        留存到按龄删除); 全局系列不在 torrents/ 下, 结构性豁免。无天文件的目录(纯
        agg.dat, 无法判龄)保守跳过。返回淘汰的系列键列表(调用方据此清内存缓存);
        删除失败(Windows 读侧竞态)保留目录下轮重试。"""
        torrents_dir = os.path.join(v3_root_dir(self._data_dir), TORRENTS_DIR_NAME)
        evicted: list = []
        if not os.path.isdir(torrents_dir):
            return evicted
        for name in sorted(os.listdir(torrents_dir)):
            series_dir = os.path.join(torrents_dir, name)
            if not _INFOHASH_RE.match(name) or not os.path.isdir(series_dir):
                continue
            dates = [d for d in (v3_day_file_date(n) for n in os.listdir(series_dir)) if d is not None]
            if not dates:
                continue
            newest = max(dates)  # YYYY-MM-DD 字典序 = 时间序
            if now - v3_date_str_epoch(newest) <= rollup_window:
                continue  # 未超龄不动(边界含)
            try:
                shutil.rmtree(series_dir)
            except OSError as exc:
                logger.warning(f"流量存储 | 系列目录 {name} 淘汰删除失败(下轮重试): {exc}")
                continue
            evicted.append(TORRENT_KEY_PREFIX + name)
        return evicted


#: 解析缓存默认字节预算(按天文件文本字节数计, LRU; S3a 实施期定约, §05.2): 解析产物
#: (V3Block/V3Sample 对象图)对文本约有 6-8 倍内存膨胀, 4MB 文本预算把最坏驻留(2s 档
#: 天文件 ≈2MB 文本/天)压在约 2 个文件 ≈25-30MB 对象内存; 30s 档(≈115KB/天)可驻 ~34 个
#: 天文件。缓存粒度 = 整天解析结果(V3ParsedDay): 命中率最高的入口是 Web 图窗按
#: meta.interval_s 的重复轮询(查询窗口日期集不变即全命中); 不驻留 90d x 2s 档全量 raw
#: (§05.2 口径 —— 驻留受本预算上界约束, 105 万行/系列的驻留方案已否决)。
V3_DAY_CACHE_BUDGET_BYTES = 4_000_000

#: agg 解析缓存条目数上界(S3b; 解析产物为紧凑 AggRow 行元组, 按条目数 LRU 逐出即可,
#: 不占天文件的文本字节预算 —— 全年 hour 行解析产物 ≈8760 行/系列, 64 系列驻留可忽略)
V3_AGG_CACHE_MAX_ENTRIES = 64


class V3DayCache:
    """按天文件解析缓存(S3a §05.2, 读侧; Web 线程调用): mtime_ns+size 键控

    - 失效键 = os.stat 的 (st_mtime_ns, st_size): 天文件只在追加期变化(追加必变 size),
      裁剪/重写(tmp+replace)size 严格变小 —— 两向都使 stat 键变化而失效; 未变即命中,
      直接复用解析产物(不重读不重解析)。
    - 内存上界: 驻留条目的文件文本字节总量 <= budget(默认 V3_DAY_CACHE_BUDGET_BYTES),
      超出按 LRU 逐出(命中移队尾, 最久未用先逐出; 至少保留最新一条 —— 单文件超预算时
      不自我清空)。缺失/空文件也缓存(stat 键 = None 哨兵): 文件此后出现则 stat 变化
      自然失效。
    - 线程模型: 读侧被 Web 线程并发调用 —— 缓存表用锁保护; 解析(慢段)在锁外进行,
      并发对同一文件重复解析无害(后写胜, 黄金法则 5 的单写线程约束不涉及只读缓存)。

    S3b 接缝: 视图端点经 read_window(窗口 -> 日期集合 -> 只读涉及文件, 24h 窗至多
    2 个日期文件)取 V3ParsedDay, 块序列交给 traffic_grid.v3_series_points 归桶;
    agg.dat 消费(hour/day/month 段)经 read_agg 同款 mtime/size 键控缓存(S3b 加)。
    """
    def __init__(self, data_dir: str, budget: int = V3_DAY_CACHE_BUDGET_BYTES) -> None:
        self._data_dir = data_dir
        self._budget = max(1, int(budget))
        self._lock = threading.Lock()
        # (系列键, 日期串) -> (stat 键 | None, 文本字节数, V3ParsedDay | None)
        self._entries: OrderedDict = OrderedDict()
        # 系列键 -> (stat 键 | None, V3ParsedAgg)(agg.dat 缓存, S3b; 条目数上界独立于天文件字节预算)
        self._agg_entries: OrderedDict = OrderedDict()

    def read_day(self, key: str, date_str: str) -> Optional[V3ParsedDay]:
        """读单天文件(带缓存): 缺失/空文件 = None; 非法键/日期 fail-fast(路径纯计算)。"""
        path = v3_day_file_path(self._data_dir, key, date_str)
        try:
            st = os.stat(path)
            stat_key = (st.st_mtime_ns, st.st_size)
            size = st.st_size
        except OSError:
            stat_key = None  # 缺失哨兵: 文件此后出现则 stat 键变化, 缓存自然失效
            size = 0
        with self._lock:
            ent = self._entries.get((key, date_str))
            if ent is not None and ent[0] == stat_key:
                self._entries.move_to_end((key, date_str))
                return ent[2]
        parsed = self._read_parse(path)  # 锁外解析(慢段; 并发重复解析无害)
        with self._lock:
            self._entries[(key, date_str)] = (stat_key, size, parsed)
            self._entries.move_to_end((key, date_str))
            while len(self._entries) > 1 and sum(e[1] for e in self._entries.values()) > self._budget:
                self._entries.popitem(last=False)
        return parsed

    def read_window(self, key: str, start_epoch: float, end_epoch: float) -> tuple:
        """查询窗口 -> 日期集合 -> 只读涉及的天文件(§05.2 按天加载): 按日期升序返回
        (date_str, V3ParsedDay | None) 元组。块不跨天(00:00 硬切), 单天文件可独立解析;
        24h 窗至多 2 个日期文件(窗口只开涉及文件, 不扫全目录)。"""
        return tuple((d, self.read_day(key, d)) for d in sorted(v3_window_dates(start_epoch, end_epoch)))

    def read_agg(self, key: str) -> V3ParsedAgg:
        """读系列 agg.dat(带缓存, S3b §05.2/§05.3 端点取数入口): mtime_ns+size 键控与
        天文件同款纪律 —— agg.dat 只在追加期变化(追加必变 size), 裁剪重写(size 严格变小)
        两向都使 stat 键变化而失效; 缺失/空文件 = 空解析结果(None 哨兵缓存, 文件此后出现
        自然失效); OSError(打开/读取失败)上抛 —— 端点按读取竞态 degraded 处理(§08)。
        解析产物为紧凑 AggRow 行元组, 缓存按条目数上界(V3_AGG_CACHE_MAX_ENTRIES)LRU
        逐出, 不占天文件的字节预算。"""
        path = v3_agg_file_path(self._data_dir, key)
        try:
            st = os.stat(path)
            stat_key = (st.st_mtime_ns, st.st_size)
        except OSError:
            stat_key = None  # 缺失哨兵: 文件此后出现则 stat 键变化, 缓存自然失效
        with self._lock:
            ent = self._agg_entries.get(key)
            if ent is not None and ent[0] == stat_key:
                self._agg_entries.move_to_end(key)
                return ent[1]
        parsed = self._read_parse_agg(path)  # 锁外解析(慢段; OSError 上抛不落缓存)
        with self._lock:
            self._agg_entries[key] = (stat_key, parsed)
            self._agg_entries.move_to_end(key)
            while len(self._agg_entries) > V3_AGG_CACHE_MAX_ENTRIES:
                self._agg_entries.popitem(last=False)
        return parsed

    @staticmethod
    def _read_parse_agg(path: str) -> V3ParsedAgg:
        """agg.dat 缺省解析纪律(对齐 TrafficV3Store.read_agg): 缺失/空文件 = 空解析结果。"""
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            return V3ParsedAgg(key=None, hours=(), days=(), months=(), bad_lines=0, data_lines=0)
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return parse_v3_agg_text(f.read())

    @staticmethod
    def _read_parse(path: str) -> Optional[V3ParsedDay]:
        """缺省解析纪律(对齐 TrafficV3Store.read_day): 缺失/空文件 None, 其余整读解析。"""
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            return None
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return parse_v3_day_text(f.read())


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


def _write_text_payload(path: str, payload: str) -> bool:
    """v3 整文件重写(trim_agg_hours 专用, §04.5): 同目录 tmp -> fsync -> os.replace
    (纪律对齐 utils.atomic_write 先例; 行尾固定 \\n)。
    PermissionError(Windows 读侧竞态)退避重试 x3, 仍失败放弃(删 tmp, 返回 False,
    原文件完好 —— 裁剪留待下轮, 数据无损)。v3 常规写路径全是追加, 原子重写仅存于此。"""
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
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except OSError:
                pass
            attempt += 1
            if attempt > REWRITE_RETRIES:
                logger.warning(f"流量存储 | {os.path.basename(path)} 裁剪重写被占用(读侧竞态), 放弃本轮(数据无损)")
                return False
            time.sleep(REWRITE_BACKOFF_S)
        except BaseException:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except OSError:
                pass
            raise
