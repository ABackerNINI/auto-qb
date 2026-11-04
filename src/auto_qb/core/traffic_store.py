"""traffic_store: qB 口径流量 v4 存储层(行型定约 = plan 26-10-05-2200 §01; 聚合/读侧沿用 plan 26-10-04-1957 §04/§05)

【格式 v4 契约 —— 主题事实单点(plan 26-10-05-2200 §01, 取代 v3 计划 §02.1「逐列冻结」条款)】
v1/v2/v3 逐行格式及其写侧/解析均已随各代退役删除; v4 读侧遇旧头行按「整文件不匹配格式」
整文件记坏(R2 换代不设双读) —— 本 docstring 即现行唯一格式契约。

数据落点(§01.1 观测/日志数据: append-only、丢失无一致性后果):
    <data_dir>/qb-traffic-v4/
      global/<YYYY-MM-DD>.dat + agg.dat                  # 全局系列
      torrents/<infohash>/<YYYY-MM-DD>.dat + agg.dat     # 每有数据种子一目录(组不落盘)
v4 全部写新目录; 旧 qb-traffic-v3/ 与更早的 qb-traffic/ 原样留存不读不迁移(删留决定权在
用户)。目录惰性创建; enabled=false(含 qb_traffic None)全程零文件零目录(保守默认, 黄金法则 2)。

天文件行型(§01 spec; interval_s 小数秒 + dt_ms 毫秒口径沿用; 坏行整行跳过计数、游标不推进):
    # auto-qb qb-traffic v4                                    文件头, 每文件一次(头行门闩, 不设双读)
    key,<系列标识>                                      global 固定 key,global; torrents/ = torrent:<infohash>
    B,<start_epoch>,<interval_s>                        3 列 = 无基线块(仅 n 游程合法)
    B,<start_epoch>,<interval_s>,<dl_base>,<up_base>    5 列 = 基线 = 块内首个带 totals 观测的快照
    r,<dl_rate>,<up_rate>,<dl_delta>,<up_delta>[,<dt_ms>]  delta 相对块基线; 负值 = 坏行(免费校验)
    z,<run_len>,<dl_delta>,<up_delta>[,<dt_ms>]         零速游程: 占 run_len 个采样槽, 速率恒 (0,0); 块首 z 的 delta = 0
    n,<run_len>[,<dt_ms>]                               null 游程: 占 run_len 个采样槽(断连/缺字段), 行型不变
- 核心不变式: delta 只存在于线格式 —— 内存结构(V4Sample/V4ZeroRun/V4NullRun/V4Block/LiveTail/
  聚合累计器)全部维持绝对 totals; format 序列化时减块基线, parse 以块基线逐行复原
  (绝对值 = 基线 + 本行 delta; delta-vs-基线逐行独立 —— 坏行整行跳过不传播, 无块内链式状态)。
- 基线立点: 块首记录带 totals(r 或 z)时基线 = 该快照, 其 delta = 0; 块首为 n 游程时写侧
  把 n-only 前缀拆成 3 列 B 无基线块(块内仅 n 游程合法, 出现 r/z 即坏行 —— 解析守卫),
  恢复传输的记录开新块立基线。基线二态须成对(全 None / 全非 None)。
- 负 delta: 基线块内必是损坏 —— 绝对值形态做不到的解析免费校验(计数器回落由写侧「重置
  强制关块重立基线」排除)。!这是「cur < last 判重置」口径的解析层形态(采样器 _delta /
  视图层 _bucket_delta 记 null, 本层 delta 形态直接记坏行 —— 分层语义不同、判据同源,
  issue 26-10-11-0207 R07/R10 登记)。
- dt_ms: 正整数且 <= DT_MS_MAX; 写侧累积漂移 <= DRIFT_TOL_MS(250ms, D2)时缺省(按标称
  interval / run_len x interval 推进); 时钟回拨钳制 dt_ms >= 1。dt 链定约(读写两侧同源)
  见「纯函数区」头注释: 游标 = 上一已消费记录槽位锚点, 游程槽均摊, 链式自洽; 全路径无
  纯等间隔推算(证伪用例钉住)。
- 撕裂尾半行(崩溃残留)豁免损坏占比; 坏行整行跳过计数, 无隔离动作(v2 的 .corrupt 隔离
  已随换代退役)—— 真实损坏的观测信号 = 读侧坏行占比超阈(>=2 行且 >5%, 撕裂尾豁免)时
  WARNING 告警(节流, 仅日志; _warn_bad_lines, issue C-04 P-05)。

关块状态机(写侧单点在采样模块 BlockBuffer, §01「关块状态机」定约):
- 关块触发: 既有触发点(00:00 硬切 / 改间隔 / 落盘失败复位)+ 计数器重置(cur < last)强制
  关块(新块基线 = 重置后 totals, 首记录 delta = 0)+ flush 且块内有 r 行才关(纯空闲块跨
  flush 开放); 关块时开放 z/n 游程先封口。
- 空闲封口: 开放 z 游程按「非 z 事件」封口 —— 恢复传输 / null 游程 / 计数器重置 / 00:00 /
  stop。空闲段盘上恰 1 条长 z 行, 空闲期主文件零写入; ZRUN_CAP_SAMPLES / ZRUN_FLUSH_S
  退役为防溢出保险闸(阈值天级, 正常路径不触闸)。代价(已知接受): 崩溃窗口 <= 当天已过
  时长, 丢失形态 = 真空, avg/totals/max 无偏。

聚合文件 agg.dat(§02.2, 每系列一个, hour/day/month 9 列追加混存; 行型与逐级派生不变):
    <kind>,<epoch>,<dl_avg>,<dl_max>,<up_avg>,<up_max>,<dl_total>,<up_total>,<cov_s>
- epoch: hour = 桶起点 / day = 本地当日 00:00 / month = 自然月 1 日 00:00; cov_s = 有效
  覆盖秒(hour 必带 —— 8 列无法还原有效时长)。同 kind 同 epoch 重复行取最后一行(重封 =
  追加行, 读侧口径)。
- 8 列旧行兜底 cov_s = 3600(AGG_LEGACY_FIELDS, 防御性保留 —— v4 全新目录正常不出现)。
- 严格逐级派生(§04.1): day 只从 hour 行聚, month 只从 day 行聚, day 不从 raw 直聚
  (cov_s 链只在逐级传递才完整)。

覆盖结算(§01「覆盖结算」, 判定函数单点 v4_block_gap_continuous, 在线/离线两路复用):
gap = 新块 B.start - 上一块末槽; gap <= interval_s + DRIFT_TOL -> 连续, 按上一记录速率
把 [末槽, 本槽) 结算进覆盖信用; 否则真空(崩溃保护内核不动)。

换代语义与保留窗(§01 换代语义 + §04.5/§06.1):
- 目录 qb-traffic-v4/ 全新落点; 旧 qb-traffic-v3/ 原样留存不读不迁移(R2, 删留决定权在
  用户); 头行门闩 v4, 不设双读。
- rollup_window 两义合一: hour 行保留窗 + 系列淘汰龄(原「catch-up 补算窗口(= 天文件存活
  期)」一义已随 plan 26-10-12-2010 解耦 —— 启动恢复读集下界 = agg 水位所在日, 不由窗口
  决定); raw_window 语义不变(raw 段 = 按天整文件存删)。
- 淘汰: 系列最新天文件日期距 now 超 rollup_window -> 整目录删除(天文件 + agg.dat), 龄期
  由文件名日期直接算; frozen 照删; 全局结构性豁免。
- catch-up(§04.3): 重启逐级补算(hour <- 读集内天文件 raw, 下界 = agg 水位所在日(plan
  26-10-12-2010) / day <- hour 行 / month <- day 行), 硬序 catch-up 先于裁剪; 停机超窗
  天文件已删, 缺失跳过不标注(图上真空, 与块间 gap 语义一致)。

写路径(§03, 仅主循环线程 —— 黄金法则 5, 本层无锁): 每系列每 flush_interval 单次
open("a") 批量追加 + flush + fsync(正常期崩溃窗口 <= flush_interval); 尾字节查补每 flush
一次; agg 行随 flush 时点水位封口合并追加(piggyback, 至多 +1 次 open); 唯一原子重写点 =
hour 裁剪(tmp+fsync+os.replace); stop() 优雅退出全量落盘(封游程 + flush + 聚合封口)。
OSError 上抛(调用方按落盘失败口径处理)。

读路径(§05, Web 线程只读): 按窗口日期集合只读涉及天文件(24h 窗至多 2 个), V4DayCache
mtime_ns+size 键控解析缓存; 3d+ 窗只读成员 agg.dat 单文件; OSError 上抛由端点按竞态
降级处理(回退 last-good 标 stale, 不以空态冒充无数据)。raw 段窗另合流采样模块活尾快照
(S6 验收追加, 2026-10-05): 未落盘 buffer 记录 + 开放游程经 v4_live_tail_slots 复原绝对
槽位(head_pending 整块重算 / 否则从写侧游标倒推)—— 镜像保证下槽 ts 与落盘重算恒等,
读侧按 ts 精确去重, 图面尾部随采样节拍实时, 不等 flush_interval 落盘。agg 段窗(3d+)
另合流同一快照的 pending_agg 未封口部分行(S7 验收追加, 2026-10-14): 开放小时/当日/
当月只活在写侧累计器, 读侧按 epoch 与封口行合流(v4_merge_agg 口径), 图尾不再停在
最后一个封口桶。

R5 拆分(计划 26-11-02-2342 §07)后的本文件: 只留 v4 读写存储类、坏行告警域与
`_write_text_payload`; 常量与低层 fmt/parse 助手迁至 traffic_store_common.py,
日期/路径迁至 traffic_store_paths.py, 行型编解码迁至 traffic_store_codec.py,
聚合计算迁至 traffic_store_agg.py, 全部公开名在本文件重导出。
`_bad_line_warn_ts` / `_warn_bad_lines` / `_read_parse` 与 TrafficV4Store /
V4DayCache 必须与本域同模块 —— 测试按 `auto_qb.core.traffic_store.*` 打补丁。
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

from ..infra import clock

logger = logging.getLogger(__name__)

# ---------- 拆分件重导出(公开面保持: 旧 import 路径全部继续可用) ----------
from .traffic_store_common import (  # noqa: F401
    AGG_FIELDS,
    AGG_KINDS,
    AGG_LEGACY_FIELDS,
    DAT_SUFFIX,
    DRIFT_TOL_MS,
    DT_MS_MAX,
    GLOBAL_KEY,
    HEADER_LINE_V4,
    HOUR_SECONDS,
    REWRITE_BACKOFF_S,
    REWRITE_RETRIES,
    TORRENTS_DIR_NAME,
    TORRENT_KEY_PREFIX,
    TRAFFIC_V4_DIR_NAME,
    V4_AGG_NAME,
    V4_DATE_FORMAT,
    V4_GLOBAL_DIR_NAME,
    V4_ROLLUP_KINDS,
    _INFOHASH_RE,
    _V4_DATE_RE,
    _fmt_dt_ms,
    _fmt_dt_tail,
    _fmt_int,
    _fmt_interval_s,
    _parse_dt_ms,
    _parse_int_field,
    _parse_interval_s,
    _parse_nn_int,
    _parse_pos_int,
)
from .traffic_store_paths import (  # noqa: F401
    _validate_date,
    v4_agg_file_path,
    v4_date_str_epoch,
    v4_day_epoch,
    v4_day_file_date,
    v4_day_file_path,
    v4_epoch_date_str,
    v4_month_epoch,
    v4_next_month_epoch,
    v4_rel_dir_to_key,
    v4_root_dir,
    v4_series_dir,
    v4_window_dates,
)
from .traffic_store_codec import (  # noqa: F401
    AggRow,
    LiveTail,
    LiveTailRun,
    V4Block,
    V4HourSample,
    V4NullRun,
    V4ParsedAgg,
    V4ParsedDay,
    V4Sample,
    V4Slot,
    V4ZeroRun,
    _parse_v4_text,
    format_agg_row,
    format_v4_b_row,
    format_v4_day_text,
    format_v4_n_row,
    format_v4_r_row,
    format_v4_z_row,
    parse_v4_agg_text,
    parse_v4_day_text,
    v4_block_agg_totals,
    v4_block_slots,
    v4_bucket_width_s,
    v4_live_tail_slots,
    v4_z_totals_ramp,
)
from .traffic_store_agg import (  # noqa: F401
    _agg_width_s,
    v4_block_gap_continuous,
    v4_hour_agg,
    v4_merge_agg,
    v4_rollup_agg,
)

#: 坏行占比告警阈值(沿用 v2 口径, issue C-04 P-05 最小消费方): 坏行(撕裂尾豁免)>=2 行
#: 且占比 >5% 时 WARNING。固定常量而非配置键: 观测面告警阈值不是行为开关。
_BAD_LINE_WARN_MIN_LINES = 2
_BAD_LINE_WARN_RATIO = 0.05

#: 同一文件坏行告警的最小间隔(秒, 节流): 天文件随追加反复重解析, 不节流等于逐次读刷屏。
_BAD_LINE_WARN_GAP_S = 3600.0

# 告警节流表(键 = 文件标识): 读侧被 Web 线程并发调用, 无锁 —— 竞态最坏多告一条, 无害;
# 只增则在上界处整体重置(最坏重复告警一次), 不做精细 LRU(不值当)。
_bad_line_warn_ts: dict = {}


def _warn_bad_lines(source: str, bad_lines: int, data_lines: int, torn_tail: bool = False) -> None:
    """坏行占比超阈值的解析告警(仅日志零行为, issue C-04 P-05)

    v2 的「坏行超阈隔离 .corrupt」动作在 v3/v4 退役: 坏行整行跳过只计数, 真实损坏
    (磁盘坏块/外部编辑)此前被静默逐行跳过 —— 图面缺数据无任何信号。本函数补**最小
    观测消费方**: 超阈(>=2 行且占比 >5%, 撕裂尾豁免)时 WARNING 一条, 不改任何解析结果。
    节流: 同一文件 _BAD_LINE_WARN_GAP_S 内至多一条。
    """
    bad = bad_lines - (1 if torn_tail else 0)
    if bad < _BAD_LINE_WARN_MIN_LINES or data_lines <= 0 or bad / data_lines <= _BAD_LINE_WARN_RATIO:
        return
    now = clock.SYSTEM_CLOCK.monotonic()  # 叶子函数: 走取时单点(D8); 原 time.monotonic() 节流语义
    prev = _bad_line_warn_ts.get(source)
    if prev is not None and now - prev < _BAD_LINE_WARN_GAP_S:
        return
    _bad_line_warn_ts[source] = now
    if len(_bad_line_warn_ts) > 256:
        _bad_line_warn_ts.clear()
    logger.warning(
        f"流量存储 | {source} 坏行 {bad}/{data_lines} 行(占比 {bad / data_lines:.1%} 超阈), "
        "已逐行跳过(图面数据缺失, 疑似磁盘损坏/外部编辑)"
    )


def _read_parse(path: str, parser, empty):
    """「读文件 -> 解析 -> 坏行超阈告警」缺省纪律单点(issue 26-10-11-0207 R07)

    缺失/空文件返回 empty(调用方声明空态: agg = 空解析结果, day = None), 其余整读后
    交 parser(解析坏行/撕裂尾/同 epoch 取末行等纪律全在 parser 内); OSError 上抛,
    调用方按恢复失败口径处理。TrafficV4Store 与 V4DayCache 共用 —— 缓存层与 store 层
    同一读纪律, 防两份漂移。
    """
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return empty
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        parsed = parser(f.read())
    _warn_bad_lines_path(path, parsed)  # 坏行超阈告警(仅日志, issue C-04 P-05)
    return parsed


def _ensure_file_prefix(key: str, path: str) -> str:
    """追加写前缀单点(issue 26-10-11-0207 R07): append_records / append_agg_rows 共用

    文件不存在/空 = 头行(v4) + key 行; 已有文件且尾字节非换行 = 撕裂尾补一个换行
    (不与残行合并, 每 flush 查补一次 —— v2 逐行查补退役); 其余空串。
    """
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return f"{HEADER_LINE_V4}\nkey,{key}\n"
    with open(path, "rb") as f:
        f.seek(-1, os.SEEK_END)
        if f.read(1) != b"\n":
            return "\n"
    return ""


def _warn_bad_lines_path(path: str, parsed) -> None:
    """按文件路径取告警标识(系列目录名/文件名, 如 global/2026-10-06.dat)并转 _warn_bad_lines"""
    _warn_bad_lines(
        f"{os.path.basename(os.path.dirname(path))}/{os.path.basename(path)}",
        parsed.bad_lines,
        parsed.data_lines,
        getattr(parsed, "torn_tail", False),
    )


class TrafficV4Store:
    """v4 写侧存储(S2a 天文件 + S2b 聚合, plan 26-10-04-1957 §03.3/§04): 按天文件块化
    追加 + 批量落盘 + agg.dat 聚合行追加/裁剪 + 系列按龄淘汰

    写侧翻转后的落盘单点: 采样模块 BlockBuffer 每系列每 flush 单次 open("a") 写 N 行 +
    flush + fsync; 尾字节查补(崩溃残留半行补 \\n)每 flush 仅一次; 块头(B 行)由调用方在
    块首次 flush 时随批传入(块状态单点在采样模块 —— 跨 flush 的同块只传一次头), 行型为
    v4(B 行携带块基线, r/z 行相对基线 delta, 见文件尾 v4 纯函数区)。只写 qb-traffic-v4/,
    旧 qb-traffic-v3/ 原样留存不读不迁移(R2 换代); 目录惰性创建。

    S2b 聚合分层(§04, 累计器/水位在采样模块, 本层只管文件):
    - append_agg_rows: 聚合行(hour/day/month 9 列)追加, 与 append_records 同款追加纪律
      (open("a") + flush + fsync, 每 flush 至多一次 open —— piggyback 语义);
    - read_agg / series_day_dates / series_keys: 重启恢复(catch-up)的读取入口;
    - trim_agg_hours: hour 行按 rollup_window 裁剪 —— 本层唯一的 tmp+fsync+os.replace
      原子重写点(§04.5, 常规写路径全是追加); 无到龄行零写(same_content 语义);
    - evict_expired_series: 超龄系列整目录删除(天文件 + agg.dat), 龄期由天文件名日期
      直接算, frozen 照删, 全局豁免。淘汰/裁剪触发点都在采样模块的 flush 时点。

    rollup_window 语义(§06.1 扩一句): hour 行保留窗 + 系列淘汰龄 两义合一, 不再只是 v2 的
    hour 段保留窗(原「catch-up 补算窗口(= 天文件存活期)」一义已随 plan 26-10-12-2010 解耦
    —— 启动恢复读集下界 = agg 水位所在日, 不由本窗口决定); raw_window 语义不变。
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
        return v4_day_file_path(self._data_dir, key, date_str)

    def series_has_data(self, key: str) -> bool:
        """「系列目录存在且含 >=1 个 .dat」(§3.2: v2 index 条目门改目录判定, 惰性零目录零 IO)

        门语义(v2 §3.3 平移): 有数据(或已开游程)的系列零样本才开/延长游程, 从未传输种子
        零文件零游程。agg.dat 亦以 .dat 结尾, 计入(有聚合必有历史, 语义一致)。
        """
        series_dir = v4_series_dir(self._data_dir, key)
        if not os.path.isdir(series_dir):
            return False
        try:
            for name in os.listdir(series_dir):
                if name.endswith(DAT_SUFFIX):
                    return True
        except OSError:
            return False
        return False

    def append_records(self, key: str, date_str: str, header: Optional[tuple], records: tuple, block_base=None) -> None:
        """块化追加一批记录(§03.3 批量写; 批 2 本棒起 v4 行型 —— B 行携带块基线, r/z 行
        存相对基线 delta): 单次 open("a") + flush + fsync

        header = (start_epoch, interval_s) 时先写 B 行(该块首次 flush; 跨 flush 的同块
        由调用方只传一次); block_base = (dl_base, up_base) 本块基线快照对(每批必传 ——
        r/z 行 delta 序列化需减基线; 全 None = 无基线块, 3 列 B 且仅 n 游程合法);
        records 为 V4Sample / V4ZeroRun / V4NullRun 序列(按槽序, totals 恒绝对值)。
        文件不存在先建头行(v4) + key 行; 崩溃残留尾部半行先补一个换行(不与残行合并,
        每 flush 查补一次 —— v2 逐行查补退役)。records 与 header 全空 = 零操作。
        """
        if header is None and not records:
            return
        path = self.series_day_path(key, date_str)  # 非法键/日期在此 fail-fast
        os.makedirs(os.path.dirname(path), exist_ok=True)
        prefix = _ensure_file_prefix(key, path)  # 建头行/撕裂尾查补单点(与 append_agg_rows 同款)
        dl_base, up_base = block_base if block_base is not None else (None, None)
        lines = []
        if header is not None:
            lines.append(format_v4_b_row(int(header[0]), float(header[1]), dl_base, up_base))
        for rec in records:
            if isinstance(rec, V4Sample):
                lines.append(format_v4_r_row(rec, dl_base, up_base))
            elif isinstance(rec, V4ZeroRun):
                lines.append(format_v4_z_row(rec, dl_base, up_base))
            else:
                lines.append(format_v4_n_row(rec))
        with open(path, "a", encoding="utf-8", newline="\n") as f:
            f.write(prefix)
            f.write("\n".join(lines) + "\n")
            f.flush()
            os.fsync(f.fileno())

    # ---------- S2b: 聚合文件(agg.dat)与淘汰(§04) ----------

    def read_agg(self, key: str) -> V4ParsedAgg:
        """读系列 agg.dat(§04.3 恢复入口): 缺失/空文件 = 空解析结果(key=None, 全空元组);
        OSError 上抛(调用方按恢复失败口径处理)。解析坏行/同 epoch 取最后一行等纪律
        全在 parse_v4_agg_text(撕裂尾行跳过, 水位从文件尾推)。
        读侧快读口径(D3, §05.2): agg.dat 单次快读上界按 ~1MB 口径放宽(全年 hour 行
        ≈8760 x ~90B + day/month 行) —— 口径记录非强制截断, S3b 视图读取沿用本入口。"""
        path = v4_agg_file_path(self._data_dir, key)
        return _read_parse(
            path,
            parse_v4_agg_text,
            V4ParsedAgg(key=None, hours=(), days=(), months=(), bad_lines=0, data_lines=0),
        )

    def append_agg_rows(self, key: str, rows: tuple) -> None:
        """追加一批聚合行(§04.2): 与 append_records 同款追加纪律 —— 单次 open("a") +
        flush + fsync, 尾字节查补一次, 文件不存在先建头行(v4) + key 行。调用方每系列
        每 flush 至多一次调用(piggyback 语义: hour/day/month 行合并一批)。rows 空 = 零操作。"""
        rows = tuple(rows)
        if not rows:
            return
        path = v4_agg_file_path(self._data_dir, key)  # 非法键 fail-fast
        os.makedirs(os.path.dirname(path), exist_ok=True)
        prefix = _ensure_file_prefix(key, path)  # 建头行/撕裂尾查补单点(与 append_records 同款)
        with open(path, "a", encoding="utf-8", newline="\n") as f:
            f.write(prefix)
            f.write("\n".join(format_agg_row(r) for r in rows) + "\n")
            f.flush()
            os.fsync(f.fileno())

    def series_keys(self) -> list:
        """扫描 v4 根目录列出现存系列键(§04.3 恢复入口): global/ + torrents/<infohash>/
        (目录存在即列出, 数据有无由调用方读文件判断); 根目录缺失 = 空表。"""
        root = v4_root_dir(self._data_dir)
        keys: list = []
        if os.path.isdir(os.path.join(root, V4_GLOBAL_DIR_NAME)):
            keys.append(GLOBAL_KEY)
        torrents_dir = os.path.join(root, TORRENTS_DIR_NAME)
        if os.path.isdir(torrents_dir):
            for name in sorted(os.listdir(torrents_dir)):
                if _INFOHASH_RE.match(name) and os.path.isdir(os.path.join(torrents_dir, name)):
                    keys.append(TORRENT_KEY_PREFIX + name)
        return keys

    def series_day_dates(self, key: str, min_epoch: float) -> tuple:
        """系列目录内天文件日期串(升序), 仅保留 date 00:00 epoch >= min_epoch 的
        (min_epoch = 调用方传的读集下界; 恢复路径现传 agg 水位所在日 —— 按需口径
        plan 26-10-12-2010, 读集与历史数据量/保留窗口解耦; 行为零改动, 仍按文件名
        日期过滤); 目录缺失 = 空表; 非日期杂物(agg.dat/.corrupt 等)跳过。"""
        try:
            names = os.listdir(v4_series_dir(self._data_dir, key))
        except OSError:
            return ()
        out = []
        for name in names:
            d = v4_day_file_date(name)
            if d is not None and v4_date_str_epoch(d) >= min_epoch:
                out.append(d)
        return tuple(sorted(out))

    def read_day(self, key: str, date_str: str) -> Optional["V4ParsedDay"]:
        """读单天文件(§04.3 catch-up 的 raw 源; 批 2 本棒起 v4 行型解析): 缺失/空文件 =
        None; OSError 上抛。"""
        path = self.series_day_path(key, date_str)
        return _read_parse(path, parse_v4_day_text, None)

    def trim_agg_hours(self, key: str, now: float, rollup_window: float) -> Optional[int]:
        """hour 行按 rollup_window 裁剪(§04.5, 本层唯一 tmp+fsync+os.replace 原子重写点):
        保留 hour.epoch >= now - rollup_window(边界含)的 hour 行, day/month 行全保留
        (永久, D7); 无到龄行零写(same_content 语义, 返回现存最老 hour epoch);
        撕裂尾行/坏行随重写自洁。PermissionError(Windows 读侧竞态)退避重试后仍失败则
        放弃本轮(原文件完好), 返回原最老 epoch。返回重写后的最老 hour epoch(空 = None)。"""
        path = v4_agg_file_path(self._data_dir, key)
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            return None
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            parsed = parse_v4_agg_text(f.read())
        kept = tuple(h for h in parsed.hours if h.epoch >= now - rollup_window)
        oldest = parsed.hours[0].epoch if parsed.hours else None
        if len(kept) == len(parsed.hours):
            return oldest  # 无到龄行: 零写(黄金法则 1)
        lines = [HEADER_LINE_V4, f"key,{key}"]
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
        torrents_dir = os.path.join(v4_root_dir(self._data_dir), TORRENTS_DIR_NAME)
        evicted: list = []
        if not os.path.isdir(torrents_dir):
            return evicted
        for name in sorted(os.listdir(torrents_dir)):
            series_dir = os.path.join(torrents_dir, name)
            if not _INFOHASH_RE.match(name) or not os.path.isdir(series_dir):
                continue
            dates = [d for d in (v4_day_file_date(n) for n in os.listdir(series_dir)) if d is not None]
            if not dates:
                continue
            newest = max(dates)  # YYYY-MM-DD 字典序 = 时间序
            if now - v4_date_str_epoch(newest) <= rollup_window:
                continue  # 未超龄不动(边界含)
            try:
                shutil.rmtree(series_dir)
            except OSError as exc:
                logger.warning(f"流量存储 | 系列目录 {name} 淘汰删除失败(下轮重试): {exc}")
                continue
            evicted.append(TORRENT_KEY_PREFIX + name)
        return evicted


#: 解析缓存默认字节预算(按天文件文本字节数计, LRU; S3a 实施期定约, §05.2): 解析产物
#: (V4Block/V4Sample 对象图)对文本约有 6-8 倍内存膨胀, 4MB 文本预算把最坏驻留(2s 档
#: 天文件 ≈2MB 文本/天)压在约 2 个文件 ≈25-30MB 对象内存; 30s 档(≈115KB/天)可驻 ~34 个
#: 天文件。缓存粒度 = 整天解析结果(V4ParsedDay): 命中率最高的入口是 Web 图窗按
#: meta.interval_s 的重复轮询(查询窗口日期集不变即全命中); 不驻留 90d x 2s 档全量 raw
#: (§05.2 口径 —— 驻留受本预算上界约束, 105 万行/系列的驻留方案已否决)。
V4_DAY_CACHE_BUDGET_BYTES = 4_000_000

#: agg 解析缓存条目数上界(S3b; 解析产物为紧凑 AggRow 行元组, 按条目数 LRU 逐出即可,
#: 不占天文件的文本字节预算 —— 全年 hour 行解析产物 ≈8760 行/系列, 64 系列驻留可忽略)
V4_AGG_CACHE_MAX_ENTRIES = 64


class V4DayCache:
    """按天文件解析缓存(S3a §05.2, 读侧; Web 线程调用): mtime_ns+size 键控

    - 失效键 = os.stat 的 (st_mtime_ns, st_size): 天文件只在追加期变化(追加必变 size),
      裁剪/重写(tmp+replace)size 严格变小 —— 两向都使 stat 键变化而失效; 未变即命中,
      直接复用解析产物(不重读不重解析)。
    - 内存上界: 驻留条目的文件文本字节总量 <= budget(默认 V4_DAY_CACHE_BUDGET_BYTES),
      超出按 LRU 逐出(命中移队尾, 最久未用先逐出; 至少保留最新一条 —— 单文件超预算时
      不自我清空)。缺失/空文件也缓存(stat 键 = None 哨兵): 文件此后出现则 stat 变化
      自然失效。
    - 线程模型: 读侧被 Web 线程并发调用 —— 缓存表用锁保护; 解析(慢段)在锁外进行,
      并发对同一文件重复解析无害(后写胜, 黄金法则 5 的单写线程约束不涉及只读缓存)。

    S3b 接缝: 视图端点经 read_window(窗口 -> 日期集合 -> 只读涉及文件, 24h 窗至多
    2 个日期文件)取 V4ParsedDay, 块序列交给 traffic_grid.v4_series_points 归桶;
    agg.dat 消费(hour/day/month 段)经 read_agg 同款 mtime/size 键控缓存(S3b 加)。
    """
    def __init__(self, data_dir: str, budget: int = V4_DAY_CACHE_BUDGET_BYTES) -> None:
        self._data_dir = data_dir
        self._budget = max(1, int(budget))
        self._lock = threading.Lock()
        # (系列键, 日期串) -> (stat 键 | None, 文本字节数, V4ParsedDay | None)
        self._entries: OrderedDict = OrderedDict()
        # 系列键 -> (stat 键 | None, V4ParsedAgg)(agg.dat 缓存, S3b; 条目数上界独立于天文件字节预算)
        self._agg_entries: OrderedDict = OrderedDict()

    def read_day(self, key: str, date_str: str) -> Optional["V4ParsedDay"]:
        """读单天文件(带缓存; 批 2 本棒起 v4 行型解析): 缺失/空文件 = None; 非法键/日期
        fail-fast(路径纯计算)。"""
        path = v4_day_file_path(self._data_dir, key, date_str)
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
        parsed = _read_parse(path, parse_v4_day_text, None)  # 锁外解析(慢段; 并发重复解析无害; 读纪律单点)
        with self._lock:
            self._entries[(key, date_str)] = (stat_key, size, parsed)
            self._entries.move_to_end((key, date_str))
            while len(self._entries) > 1 and sum(e[1] for e in self._entries.values()) > self._budget:
                self._entries.popitem(last=False)
        return parsed

    def read_window(self, key: str, start_epoch: float, end_epoch: float) -> tuple:
        """查询窗口 -> 日期集合 -> 只读涉及的天文件(§05.2 按天加载): 按日期升序返回
        (date_str, V4ParsedDay | None) 元组。块不跨天(00:00 硬切), 单天文件可独立解析;
        24h 窗至多 2 个日期文件(窗口只开涉及文件, 不扫全目录)。"""
        return tuple((d, self.read_day(key, d)) for d in sorted(v4_window_dates(start_epoch, end_epoch)))

    def read_agg(self, key: str) -> V4ParsedAgg:
        """读系列 agg.dat(带缓存, S3b §05.2/§05.3 端点取数入口): mtime_ns+size 键控与
        天文件同款纪律 —— agg.dat 只在追加期变化(追加必变 size), 裁剪重写(size 严格变小)
        两向都使 stat 键变化而失效; 缺失/空文件 = 空解析结果(None 哨兵缓存, 文件此后出现
        自然失效); OSError(打开/读取失败)上抛 —— 端点按读取竞态 degraded 处理(§08)。
        解析产物为紧凑 AggRow 行元组, 缓存按条目数上界(V4_AGG_CACHE_MAX_ENTRIES)LRU
        逐出, 不占天文件的字节预算。"""
        path = v4_agg_file_path(self._data_dir, key)
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
        parsed = _read_parse(
            path,
            parse_v4_agg_text,
            V4ParsedAgg(key=None, hours=(), days=(), months=(), bad_lines=0, data_lines=0),
        )  # 锁外解析(慢段; OSError 上抛不落缓存; 读纪律单点 _read_parse)
        with self._lock:
            self._agg_entries[key] = (stat_key, parsed)
            self._agg_entries.move_to_end(key)
            while len(self._agg_entries) > V4_AGG_CACHE_MAX_ENTRIES:
                self._agg_entries.popitem(last=False)
        return parsed


def _write_text_payload(path: str, payload: str) -> bool:
    """整文件重写(trim_agg_hours 专用, §04.5): 同目录 tmp -> fsync -> os.replace
    (纪律对齐 utils.atomic_write 先例; 行尾固定 \\n)。
    PermissionError(Windows 读侧竞态)退避重试 x3, 仍失败放弃(删 tmp, 返回 False,
    原文件完好 —— 裁剪留待下轮, 数据无损)。常规写路径全是追加, 原子重写仅存于此。"""
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
