"""traffic_store 拆分件: acc 快照账本(单文件追加账本, plan 26-11-21-1546 S2 第一步)。

本批只交付账本核心读写组件与单测, 零接线(§04 S2): flush 随批追加变化行 / stop 全系列
终态行 / 启动快路 / fallback 是下一批 P2b 的接线面 —— P2b 经 TrafficV4Store 包装层调用
本模块函数(与 append_agg_rows / trim_agg_hours 同款挂法)。

【格式契约 —— 主题事实单点(§03.1 acc.dat 行)】
落点: <data_dir>/qb-traffic-v4/acc.dat(根级, 与 global//torrents/ 平级; 旧版本回滚不
认识该陌生文件 —— 系列键扫描只看两级目录, 原样留存不读不删, §03.5)。

文件形态(文本, \\n 行尾; 版本头行门闩与天文件头行同款机制, 不设双读):
    # auto-qb qb-traffic-acc v1        版本头行, 每文件一次; 不匹配 = 整本无效(返回空,
                                        调用方全体系列 fallback, §03.5 升级首启/换代留门)
    A,<key>,<cursor>,<fp_size>,<fp_mtime_ns>,<earliest>,<day_epoch>,<n_dh>[,<hour 行 8 列>x n_dh],
       <month_epoch>,<n_md>[,<day 行 8 列>x n_md],<cd_epoch>,<n_cd>[...],<cm_epoch>,<n_cm>[...],
       <n_pending>[,<h>,<fold 8 字段>x n_pending],<credit 5 列 | 空列>
    (每变化系列一行(D8): flush 随批追加变化系列行 / stop 全系列终态行 / 单系列行共用
     一个追加入口; 同 key 重复行读侧取最后一行(last-wins, 与 agg.dat「同 epoch 取末行」
     同款纪律, §03.4))

列定约:
- key: 系列键(global / torrent:<infohash>, 无逗号 —— v4 系列键字符集保证), 写侧经
  v4_series_dir 同源校验 fail-fast。
- cursor: 游标 = 累计器(折叠态)已入账到的最后槽位 epoch(浮点秒 repr, 无损往返; 空列 =
  尚无入账)。!R3 crash 竞态窗口两向语义(§03.4/§07 R3):
    * crash 后 raw 尾 <= 游标: 缓冲信用已在账本 —— raw 面真空 = 现有崩溃语义(丢失段
      真空无偏, avg/totals/max 无偏), agg 面比现状更完整(折叠态已落账本, 零重算);
    * raw 尾 > 游标: crash 恰落在 raw 追加与账本追加之间 —— 账本落后, 恢复时对该系列
      回放 (游标, raw 尾] 小尾段(P2b 接线实现, 本批只钉字段语义)。
- fp_size/fp_mtime_ns: 写入时刻该系列 agg.dat 的 os.stat 指纹(size, mtime_ns; 与
  V4DayCache 的 (mtime_ns, size) 序相反, 本组件口径 = 任务 D9 原文 size 在前);
  (0, 0) = 写入时 agg.dat 缺失哨兵。读侧探针(D9): 现 stat 指纹 == 行内指纹 -> 采信
  快照; 失配/缺失/损坏 -> 该系列 fallback(单系列隔离, INFO 留痕; 快照是加速器不承载
  正确性)。追加必变 size / hour 裁剪重写 size 严格变小 —— 两向都使指纹失配。
- earliest/day_epoch/month_epoch/cd_epoch/cm_epoch: int 或空列 = None(earliest_hour
  裁剪判据 / 开放日 / 开放月 / 已关日存根 epoch / 已关月存根 epoch —— SeriesAgg 全部
  持久化字段; 水位不在 SeriesAgg, 已排除不落盘)。
- n_dh/n_md/n_cd/n_cm: 各段 AggRow 行数(非负 int); 每行 8 列 int(epoch + 6 数据列 +
  cov_s, kind 由段位隐含: dh/cd 段 = hour 行, md/cm 段 = day 行; 写侧 kind 不符
  fail-fast); cov_s 下限 1 与 agg 解析同源(行存在即有覆盖); epoch 空列的段不得携带行
  (读侧免费校验, 写侧 format_acc_row 同判据 fail-fast 对称)。
- n_pending: 未封口 hour 桶数; 每桶 9 列 = hour epoch + HourFold 8 字段(dl_wsum/up_wsum/
  cov 浮点 3 列 repr 无损往返, dl_max/up_max/dl_total/up_total/credits int 5 列), 按
  hour epoch 升序写出, 重复 epoch 记坏。
- credit: open_credit 5 列(槽位 float repr + dl_rate/up_rate/dl_total/up_total int 4 列)
  或单个空列 = None。

失败语义(§03.3/S2, 按系列隔离不放大): 末行撕裂(文件不以 \\n 结尾)或任一行解析失败 ->
该行丢弃, 该系列取其上一有效行(last-wins); 无上一有效行 = 该系列无快照(调用方按系列
fallback); 头行门闩失守 = 整本无效; 空行/注释行(# 前缀)跳过不计坏。读侧留痕: 撕裂尾
DEBUG(崩溃残留常态), 非撕裂坏行 INFO, 门闩失守/整本缺失 INFO(调用方全体 fallback)。

写纪律(D8 单文件追加账本): 追加 = 单次 open("a") + flush + fsync(与 append_agg_rows
同款), 尾字节查补同 _ensure_file_prefix 先例; 唯一原子重写点 = 压实(超 16MB 单次重写:
整本 last-wins 折叠成每系列单行, tmp+fsync+os.replace 与 hour 裁剪同款; 重写自洁撕裂
尾/坏行); 门闩失守的文件不重写(陌生格式原样留存, 不代别的版本清场)。16MB 阈值与
账本文件名都是模块常量非配置键(照 ZRUN_FLUSH_S 先例, 本组件零新增配置键)。

数据镜像面(P2b 接缝): AccSeriesState/AccHourFoldState 为 modules 层 SeriesAgg/HourFold
(D12)的字段镜像 —— 本组件不反向依赖 modules 层(拆分件只依赖 common/paths/codec),
字段对齐(名字+顺序+默认值)由 tests/test_traffic_acc_ledger.py 静态守阵钉死, P2b 转换
= 逐字段拷贝。SeriesAgg 若增删字段, 守阵即红, 强制同步本镜像与行格式。
"""
import logging
import math
import os
import tempfile
import time
from dataclasses import dataclass, field
from typing import Iterable, Optional

from .traffic_store_common import (
    ACC_LEDGER_HEADER_V1,
    REWRITE_BACKOFF_S,
    REWRITE_RETRIES,
    _fmt_int,
    _parse_nn_int,
)
from .traffic_store_codec import AggRow
from .traffic_store_paths import v4_acc_ledger_path, v4_agg_file_path, v4_series_dir

logger = logging.getLogger(__name__)

#: 压实阈值(字节, D8): 账本超过即单次重写折叠。模块常量非配置键(黄金法则 4;
#: 本组件零新增配置键), 口径 = 计划 §03.1「16MB 阈值压实」。
ACC_LEDGER_COMPACT_BYTES = 16 * 1024 * 1024

#: 数据行行型前缀(A = acc snapshot 行; 其余非注释行记坏)
_ROW_TYPE = "A"

#: 每段 AggRow 的列数(kind 由段位隐含, 不落盘): epoch + 6 数据列 + cov_s
_AGG_COLUMNS = 8

#: pending 每桶列数: hour epoch + HourFold 8 字段
_FOLD_COLUMNS = 9

#: open_credit 列数: 槽位 + 4 int
_CREDIT_COLUMNS = 5

# ---------- 数据镜像(dataclasses; 字段与 SeriesAgg/HourFold 对齐由静态守阵钉死) ----------


@dataclass(frozen=True)
class AccHourFoldState:
    """未封口 hour 桶折叠累计态的账本镜像(D12 HourFold 8 字段同名同序同默认值)。

    浮点 3 字段(dl_wsum/up_wsum/cov)以 repr 无损往返; 整数 5 字段照 agg 数据列口径
    (非负 int)。与 HourFold 的字段对齐由 tests/test_traffic_acc_ledger.py 静态守阵钉死。
    """

    dl_wsum: float = 0.0
    up_wsum: float = 0.0
    cov: float = 0.0
    dl_max: int = 0
    up_max: int = 0
    dl_total: int = 0
    up_total: int = 0
    credits: int = 0


@dataclass
class AccSeriesState:
    """单系列折叠态的账本镜像(SeriesAgg 全部持久化字段, 名字+顺序对齐; 水位不在
    SeriesAgg, 已排除)。

    pending 桶值为 AccHourFoldState(P2b 转 HourFold 逐字段拷贝); day_hours/month_days
    与两个已关层存根的行表持真实 AggRow(本层同族类型, kind 由段位约束: day_hours 与
    closed_day[1] = hour 行, month_days 与 closed_month[1] = day 行)。
    """

    pending: dict = field(default_factory=dict)  # hour_epoch -> AccHourFoldState
    open_credit: Optional[tuple] = None  # (槽位 float, dl_rate, up_rate, dl_total, up_total)
    day_epoch: Optional[int] = None
    day_hours: list = field(default_factory=list)  # AggRow(kind=hour)
    month_epoch: Optional[int] = None
    month_days: list = field(default_factory=list)  # AggRow(kind=day)
    closed_day: Optional[tuple] = None  # (epoch, [AggRow hour], 已关日存根 issue R1#63)
    closed_month: Optional[tuple] = None  # (epoch, [AggRow day], 已关月存根)
    earliest_hour: Optional[int] = None


@dataclass(frozen=True)
class AccSnapshot:
    """账本单行(每变化系列一行, §03.1): key + 游标 + agg 指纹 + 折叠态字段。"""

    key: str
    cursor: Optional[float]  # 累计器已入账到的最后槽位 epoch(浮点秒; None = 尚无入账)
    agg_fingerprint: tuple  # (size, mtime_ns); (0, 0) = 写入时 agg.dat 缺失哨兵
    state: AccSeriesState


@dataclass(frozen=True)
class AccLedgerRead:
    """acc 账本整读结果(read_acc_ledger / parse_acc_ledger_text 返回)。

    snapshots = key -> AccSnapshot(整本 last-wins 后的每系列最终行); 空 dict 且
    header_ok=False = 文件缺失/空/头行门闩失守(调用方全体系列 fallback, §03.3);
    header_ok=True 时缺某系列 = 该系列无快照(按系列 fallback, 单行损坏/撕裂尾隔离)。
    """

    snapshots: dict
    header_ok: bool
    bad_lines: int = 0
    data_lines: int = 0
    torn_tail: bool = False


# ---------- 低层列编解码助手(浮点 repr 无损往返 / 空列 = None) ----------


def _fmt_float(v: float) -> str:
    """浮点列文本(repr = 最短往返表示; 有限性由调用方数据面保证)"""
    return repr(float(v))


def _parse_fin_float(text: str) -> float:
    """有限浮点列解析(空列/非数值/inf/nan 记坏 —— 折叠态/游标不存在非有限值)"""
    v = float(text)
    if not math.isfinite(v):
        raise ValueError(f"非有限浮点列: {text}")
    return v


def _parse_opt_float(text: str) -> Optional[float]:
    """可选浮点列解析(空列 = None)"""
    if text == "":
        return None
    return _parse_fin_float(text)


def _fmt_opt_int(v: Optional[int]) -> str:
    """可选整数列文本(空列 = None)"""
    return "" if v is None else _fmt_int(v)


def _parse_opt_int(text: str) -> Optional[int]:
    """可选整数列解析(空列 = None; 非空走非负 int 口径 —— epoch 类列负值记坏)"""
    if text == "":
        return None
    return _parse_nn_int(text)


def _parse_agg_columns(parts: list, idx: int, kind: str) -> tuple:
    """段内单行 AggRow 8 列解析(epoch + 6 数据列 + cov_s; kind 由段位给入; 纪律镜像
    parse_v4_agg_text: 数据列非负 int, cov_s 下限 1 行存在即有覆盖, epoch 纯 int)。"""
    row = AggRow(
        kind=kind,
        epoch=int(parts[idx]),
        dl_avg=_parse_nn_int(parts[idx + 1]),
        dl_max=_parse_nn_int(parts[idx + 2]),
        up_avg=_parse_nn_int(parts[idx + 3]),
        up_max=_parse_nn_int(parts[idx + 4]),
        dl_total=_parse_nn_int(parts[idx + 5]),
        up_total=_parse_nn_int(parts[idx + 6]),
        cov_s=_parse_nn_int(parts[idx + 7]),
    )
    if row.cov_s < 1:
        raise ValueError(f"cov_s 下限 1(行存在即有覆盖): {parts[idx + 7]}")
    return row


def _parse_row_segment(parts: list, idx: int, kind: str) -> tuple:
    """带行段解析「<epoch 列>,<n 列>[,<行 8 列>x n]」-> (epoch | None, rows, new_idx);
    epoch 空列的段不得携带行(免费校验)。"""
    epoch = _parse_opt_int(parts[idx])
    n = _parse_nn_int(parts[idx + 1])
    idx += 2
    if epoch is None and n:
        raise ValueError("epoch 空列的段不得携带行")
    rows = []
    for _ in range(n):
        rows.append(_parse_agg_columns(parts, idx, kind))
        idx += _AGG_COLUMNS
    return epoch, rows, idx


def _fmt_agg_columns(row: AggRow, expected_kind: str) -> tuple:
    """段内 AggRow 8 列文本(kind 由段位约束, 不符 fail-fast —— 防错段序列化静默改行型)"""
    if row.kind != expected_kind:
        raise ValueError(f"段位 kind 不符(须 {expected_kind}): {row.kind!r}")
    return (
        _fmt_int(row.epoch),
        _fmt_int(row.dl_avg),
        _fmt_int(row.dl_max),
        _fmt_int(row.up_avg),
        _fmt_int(row.up_max),
        _fmt_int(row.dl_total),
        _fmt_int(row.up_total),
        _fmt_int(row.cov_s),
    )


def _validate_ledger_key(key: str) -> None:
    """系列键校验(与写侧/读侧同源单点: 复用 v4_series_dir 的 fail-fast 校验, 只用其
    校验副作用弃其返回值 —— 非法键 ValueError, 键字符集保证无逗号)"""
    v4_series_dir("", key)


# ---------- 行格式(纯函数; 单测钉无损 roundtrip) ----------


def format_acc_row(snapshot: AccSnapshot) -> str:
    """AccSnapshot -> 账本数据行文本(格式契约见模块 docstring; 列序 = 定约单点):
    A,<key>,<cursor>,<fp_size>,<fp_mtime_ns>,<earliest>,<day_epoch>,<n_dh>[...],
    <month_epoch>,<n_md>[...],<cd_epoch>,<n_cd>[...],<cm_epoch>,<n_cm>[...],
    <n_pending>[...],<credit 5 列 | 空列>。pending 按 hour epoch 升序写出(确定性);
    非法键/段位 kind 不符/epoch 空列段带行(day 与 month 开放段)fail-fast。"""
    _validate_ledger_key(snapshot.key)
    state = snapshot.state
    parts = [
        _ROW_TYPE,
        snapshot.key,
        "" if snapshot.cursor is None else _fmt_float(snapshot.cursor),
        _fmt_int(snapshot.agg_fingerprint[0]),
        _fmt_int(snapshot.agg_fingerprint[1]),
        _fmt_opt_int(state.earliest_hour),
    ]
    # 开放日段(hour 行) / 开放月段(day 行)—— epoch 空列的段不得携带行(与读侧
    # _parse_row_segment 免费校验同判据对称, 防转换层拷贝 bug 静默写出坏行型)
    if state.day_epoch is None and state.day_hours:
        raise ValueError("day_epoch 空列的开放日段不得携带 hour 行")
    if state.month_epoch is None and state.month_days:
        raise ValueError("month_epoch 空列的开放月段不得携带 day 行")
    parts.append(_fmt_opt_int(state.day_epoch))
    parts.append(str(len(state.day_hours)))
    for row in state.day_hours:
        parts.extend(_fmt_agg_columns(row, "hour"))
    parts.append(_fmt_opt_int(state.month_epoch))
    parts.append(str(len(state.month_days)))
    for row in state.month_days:
        parts.extend(_fmt_agg_columns(row, "day"))
    # 已关日/已关月存根段(行表随存根持久化 —— 快路恢复后迟到重封仍走存根合流, R1#63 语义不丢)
    if state.closed_day is None:
        parts.extend(("", "0"))
    else:
        parts.append(_fmt_opt_int(state.closed_day[0]))
        parts.append(str(len(state.closed_day[1])))
        for row in state.closed_day[1]:
            parts.extend(_fmt_agg_columns(row, "hour"))
    if state.closed_month is None:
        parts.extend(("", "0"))
    else:
        parts.append(_fmt_opt_int(state.closed_month[0]))
        parts.append(str(len(state.closed_month[1])))
        for row in state.closed_month[1]:
            parts.extend(_fmt_agg_columns(row, "day"))
    # pending 段(hour epoch 升序)
    parts.append(str(len(state.pending)))
    for h in sorted(state.pending):
        fold = state.pending[h]
        parts.append(_fmt_int(h))
        parts.extend(
            (
                _fmt_float(fold.dl_wsum),
                _fmt_float(fold.up_wsum),
                _fmt_float(fold.cov),
                _fmt_int(fold.dl_max),
                _fmt_int(fold.up_max),
                _fmt_int(fold.dl_total),
                _fmt_int(fold.up_total),
                _fmt_int(fold.credits),
            )
        )
    # open_credit 尾段(空列 = None)
    if state.open_credit is None:
        parts.append("")
    else:
        slot, dl_rate, up_rate, dl_total, up_total = state.open_credit
        parts.extend(
            (
                _fmt_float(slot),
                _fmt_int(dl_rate),
                _fmt_int(up_rate),
                _fmt_int(dl_total),
                _fmt_int(up_total),
            )
        )
    return ",".join(parts)


def _parse_acc_row(parts: list) -> AccSnapshot:
    """账本数据行列序解析(格式契约见模块 docstring; 任何越界/非法列 -> ValueError/
    IndexError -> 整行记坏, 游标走严格列数收尾校验)。"""
    if len(parts) < 7:
        raise ValueError("列数不足")
    key = parts[1]
    _validate_ledger_key(key)
    cursor = _parse_opt_float(parts[2])
    fingerprint = (_parse_nn_int(parts[3]), _parse_nn_int(parts[4]))
    earliest = _parse_opt_int(parts[5])
    idx = 6
    day_epoch, day_hours, idx = _parse_row_segment(parts, idx, "hour")
    month_epoch, month_days, idx = _parse_row_segment(parts, idx, "day")
    cd_epoch, cd_rows, idx = _parse_row_segment(parts, idx, "hour")
    cm_epoch, cm_rows, idx = _parse_row_segment(parts, idx, "day")
    n_pending = _parse_nn_int(parts[idx])
    idx += 1
    pending: dict = {}
    for _ in range(n_pending):
        h = _parse_nn_int(parts[idx])
        if h in pending:
            raise ValueError("pending hour epoch 重复")
        pending[h] = AccHourFoldState(
            dl_wsum=_parse_fin_float(parts[idx + 1]),
            up_wsum=_parse_fin_float(parts[idx + 2]),
            cov=_parse_fin_float(parts[idx + 3]),
            dl_max=_parse_nn_int(parts[idx + 4]),
            up_max=_parse_nn_int(parts[idx + 5]),
            dl_total=_parse_nn_int(parts[idx + 6]),
            up_total=_parse_nn_int(parts[idx + 7]),
            credits=_parse_nn_int(parts[idx + 8]),
        )
        idx += _FOLD_COLUMNS
    if parts[idx] == "":
        credit = None
        idx += 1
    else:
        credit = (
            _parse_fin_float(parts[idx]),
            _parse_nn_int(parts[idx + 1]),
            _parse_nn_int(parts[idx + 2]),
            _parse_nn_int(parts[idx + 3]),
            _parse_nn_int(parts[idx + 4]),
        )
        idx += _CREDIT_COLUMNS
    if idx != len(parts):
        raise ValueError("尾部多余列")
    state = AccSeriesState(
        pending=pending,
        open_credit=credit,
        day_epoch=day_epoch,
        day_hours=day_hours,
        month_epoch=month_epoch,
        month_days=month_days,
        closed_day=None if cd_epoch is None else (cd_epoch, cd_rows),
        closed_month=None if cm_epoch is None else (cm_epoch, cm_rows),
        earliest_hour=earliest,
    )
    return AccSnapshot(key=key, cursor=cursor, agg_fingerprint=fingerprint, state=state)


def parse_acc_ledger_text(text: str) -> AccLedgerRead:
    """acc 账本文本 -> AccLedgerRead(纯函数, 无文件访问; 读纪律单点)。

    版本头行门闩: 首行 strip 后须恰为 ACC_LEDGER_HEADER_V1, 缺失/不符整本无效
    (header_ok=False, snapshots 空, 全部行计坏含头行 —— 与 _parse_v4_text 同款口径);
    数据行行型 A, 解析失败整行记坏(last-wins 只取有效行 —— 撕裂尾/单行损坏自然隔离到
    该系列的上一有效行); 空行/注释行(# 前缀)跳过不计坏; 撕裂尾 = 文件不以 \\n 结尾且
    恰末行解析失败(豁免口径与 _parse_v4_text 同源)。"""
    lines = text.splitlines()
    torn = bool(text) and not text.endswith("\n")
    header = lines[0].strip() if lines else None
    if header != ACC_LEDGER_HEADER_V1:
        return AccLedgerRead(snapshots={}, header_ok=False, bad_lines=len(lines), data_lines=len(lines), torn_tail=torn)
    snapshots: dict = {}
    bad = 0
    data = 0
    torn_tail = False
    last_idx = len(lines) - 1
    for i in range(1, len(lines)):
        data += 1
        s = lines[i].strip()
        if not s or s.startswith("#"):
            continue
        try:
            parts = s.split(",")
            if parts[0] != _ROW_TYPE:
                raise ValueError(f"未知行型: {parts[0]!r}")
            snap = _parse_acc_row(parts)
        except (ValueError, IndexError):
            bad += 1
            if torn and i == last_idx:
                torn_tail = True  # 末行撕裂(崩溃残留半行, 豁免口径与 agg 解析同源)
            continue
        snapshots[snap.key] = snap  # last-wins: 同 key 重复行取最后一行(§03.4)
    return AccLedgerRead(snapshots=snapshots, header_ok=True, bad_lines=bad, data_lines=data, torn_tail=torn_tail)


# ---------- 文件面(追加 / 整读 / 压实; 只主循环线程 —— 黄金法则 5, 本层无锁) ----------


def _ensure_ledger_prefix(path: str) -> str:
    """追加写前缀单点(镜像 traffic_store._ensure_file_prefix 先例): 文件不存在/空 =
    版本头行; 已有文件且尾字节非换行 = 撕裂尾补一个换行(不与残行合并); 其余空串。"""
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return ACC_LEDGER_HEADER_V1 + "\n"
    with open(path, "rb") as f:
        f.seek(-1, os.SEEK_END)
        if f.read(1) != b"\n":
            return "\n"
    return ""


def append_acc_snapshots(data_dir: str, snapshots: Iterable[AccSnapshot]) -> None:
    """追加一批账本行(D8; 单系列行 / flush 随批变化行 / stop 全系列终态行共用本入口):
    单次 open("a") + flush + fsync(与 append_agg_rows 同款追加纪律), 尾字节查补一次,
    文件不存在先建版本头行。snapshots 空 = 零操作(幂等)。同批同 key 重复行不拦截
    (append-only 账本, 读侧 last-wins 兜底)。OSError 上抛(调用方按落盘失败口径处理
    —— 观测数据丢失无一致性后果)。"""
    snapshots = tuple(snapshots)
    if not snapshots:
        return
    path = v4_acc_ledger_path(data_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    prefix = _ensure_ledger_prefix(path)
    lines = [format_acc_row(s) for s in snapshots]
    with open(path, "a", encoding="utf-8", newline="\n") as f:
        f.write(prefix)
        f.write("\n".join(lines) + "\n")
        f.flush()
        os.fsync(f.fileno())


def read_acc_ledger(data_dir: str) -> AccLedgerRead:
    """整读 acc 账本(§03.3 恢复入口): 缺失/空文件 = 整本无效(header_ok=False, INFO
    留痕 —— 升级后首次启动的常态自举点); 其余整读后交 parse_acc_ledger_text(门闩/
    last-wins/撕裂尾/坏行纪律全在解析), 并按结果留痕(撕裂尾 DEBUG / 非撕裂坏行 INFO /
    门闩失守 INFO)。OSError 上抛(调用方按恢复失败口径处理 —— 与 store 读路径同款)。"""
    path = v4_acc_ledger_path(data_dir)
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        logger.info("流量存储 | acc 账本缺失(升级后首次启动或未自举), 全体系列走 fallback 重建")
        return AccLedgerRead(snapshots={}, header_ok=False)
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        result = parse_acc_ledger_text(f.read())
    if not result.header_ok:
        logger.info(f"流量存储 | acc 账本头行门闩失守(格式版本不符), 整本无效({result.bad_lines} 行), "
                    "全体系列走 fallback 重建")
        return result
    noisy = result.bad_lines - (1 if result.torn_tail else 0)
    if noisy > 0:
        logger.info(f"流量存储 | acc 账本损坏行 {noisy}/{result.data_lines} 行已跳过"
                    "(无快照系列按系列 fallback, 单系列隔离)")
    if result.torn_tail:
        logger.debug("流量存储 | acc 账本撕裂尾(崩溃残留半行), 末行已跳过")
    return result


def compact_acc_ledger(data_dir: str) -> bool:
    """acc 账本压实(D8 唯一原子重写点): 账本 > ACC_LEDGER_COMPACT_BYTES 时整本
    last-wins 折叠成每系列单行重写(key 升序), tmp+fsync+os.replace 与 hour 裁剪
    (_write_text_payload)同款纪律; 重写自洁撕裂尾/坏行。未到阈值零写(黄金法则 1,
    same_content); 文件缺失/空零写; 头行门闩失守不重写(陌生格式原样留存, 不代别的
    版本清场 —— 未来版本自己的门闩自己管)。返回是否实际重写; 读侧 OSError 上抛,
    重写竞态(Windows 读侧占用)退避重试后放弃本轮返回 False(原文件完好, 数据无损)。"""
    path = v4_acc_ledger_path(data_dir)
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return False
    if os.path.getsize(path) <= ACC_LEDGER_COMPACT_BYTES:
        return False  # 未到阈值: 零写(黄金法则 1)
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        parsed = parse_acc_ledger_text(f.read())
    if not parsed.header_ok:
        logger.warning("流量存储 | acc 账本头行门闩失守, 压实跳过(陌生格式文件原样留存)")
        return False
    if parsed.bad_lines:
        logger.info(f"流量存储 | acc 账本压实折叠损坏/撕裂行 {parsed.bad_lines} 行(重写自洁)")
    lines = [ACC_LEDGER_HEADER_V1]
    lines.extend(format_acc_row(parsed.snapshots[k]) for k in sorted(parsed.snapshots))
    return _rewrite_ledger_payload(path, "\n".join(lines) + "\n")


def _rewrite_ledger_payload(path: str, payload: str) -> bool:
    """整文件原子重写(acc 压实专用): 同目录 tmp -> fsync -> os.replace(纪律对齐
    traffic_store._write_text_payload 先例 —— hour 裁剪同款, 常量单点复用 REWRITE_*)。
    PermissionError(Windows 读侧竞态)退避重试 x3, 仍失败放弃(删 tmp, 返回 False,
    原文件完好 —— 压实留待下轮)。tmp 落 qb-traffic-v4/ 根级, 系列键扫描只见两级目录,
    残留 tmp 不被误读。"""
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
                logger.warning("流量存储 | acc 账本压实重写被占用(读侧竞态), 放弃本轮(数据无损)")
                return False
            time.sleep(REWRITE_BACKOFF_S)
        except BaseException:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except OSError:
                pass
            raise


# ---------- agg 指纹探针(D9: 纯函数 + 探针函数两级; 快照是加速器不承载正确性) ----------


def stat_agg_fingerprint(data_dir: str, key: str) -> tuple:
    """写侧指纹采样(P2b 构建 AccSnapshot 时随批调用): stat 系列 agg.dat 取
    (st_size, st_mtime_ns); OSError(缺失等)按 (0, 0) 缺失哨兵 —— 与读侧探针成对:
    写入时缺失记 (0, 0), 恢复探针时仍缺失 -> 探针 OSError -> 失配 -> 该系列 fallback
    (§03.3 保守口径, 不做「缺失对缺失 = 匹配」的乐观捷径)。"""
    try:
        st = os.stat(v4_agg_file_path(data_dir, key))
    except OSError:
        return (0, 0)
    return (st.st_size, st.st_mtime_ns)


def agg_fingerprint_matches(stored: tuple, size: int, mtime_ns: int) -> bool:
    """指纹比对纯函数(D9 两级之一): (size, mtime_ns) 两列全等才匹配 —— agg.dat 只在
    追加期变化(追加必变 size)或裁剪重写(size 严格变小), 两向都使指纹失配(与
    V4DayCache 的 stat 键同判据, 列序不同: 本组件按 D9 原文 size 在前)。"""
    return (int(stored[0]), int(stored[1])) == (int(size), int(mtime_ns))


def probe_agg_fingerprint(data_dir: str, key: str, stored: tuple) -> bool:
    """读侧指纹探针(D9 两级之二, 恢复路径消费): stat 系列 agg.dat 与账本行内指纹比对;
    OSError(agg.dat 缺失/不可读)按缺失 = 失配语义返回 False(该系列 fallback, 单系列
    隔离, §03.3)。"""
    try:
        st = os.stat(v4_agg_file_path(data_dir, key))
    except OSError:
        return False
    return agg_fingerprint_matches(stored, st.st_size, st.st_mtime_ns)
