"""traffic_store: qB 口径流量 dat 存储层(plan 26-10-03-0946 方案C P2, §02)

数据落点(§01.1 归类为观测/日志数据, 不入 state_file —— append-only、丢失无一致性后果、
体量日志型): `<data_dir>/qb-traffic/` 子目录(kebab-case 硬编码常量, 不做配置键; 子目录名
对齐既有兄弟目录 skip-check-backup/hr 先例), 布局(§02.1):

    <data_dir>/qb-traffic/
      index.json               # 单种注册表(format 1): infohash -> {frozen_at/created_at/updated_at}
      global.dat               # 全局系列(单文件, 永不冻结, 不进 index)
      torrents/<infohash>.dat  # 每活跃种子一文件(惰性建; 组不落盘 —— 三轮拍板, §02.2)

目录惰性创建: enabled 且首次采样(首个产出点)时 os.makedirs(exist_ok=True);
enabled=false(含 qb_traffic None)全程零文件零目录(保守默认, 黄金法则 2)。

文件格式 v1(§02.3, 逐列冻结, 不得扩列改版):
    # auto-qb qb-traffic v1                      <- 头行: 格式标识 + 版本
    key,<系列标识>                                <- global.dat 固定 key,global; torrents/ = torrent:<infohash>
    raw,<epoch_s>,<dl_rate>,<up_rate>,<dl_total>,<up_total>                      # 采样行
    hour,<hour_epoch>,<dl_avg>,<dl_max>,<up_avg>,<up_max>,<dl_total>,<up_total>  # 小时封口行

- raw 四数据列 = 瞬时速率对(bytes/s) + all-time 累计快照对(bytes, Prometheus 口径:
  存快照、消费侧差分; 取 all-time 对 —— 跨 qB 重启连续性最好, §10.1 两行风险均按
  消费侧回落判重置兜底); 会话快照对本层不落盘(§02.3, S1 采样点的 session 字段在此截除)。
- null 点(断连/关键字段缺失)写 `raw,<epoch_s>,,,,`(四数据列全空), 读侧还原 None。
- 累计快照列恒非负整数; 时间列(epoch_s/hour_epoch)恒整数秒。

写路径(§02.4 左, 仅主循环线程 —— 黄金法则 5, 调用方义务; 本层无锁):
- 平时每次采样 open("a") 追加一行 raw + flush(进程崩溃丢 <=1 行), 不做常驻句柄;
- 小时封口(每小时首个采样触发一次, 逐系列): 读全文件 -> 归并未封桶的 raw 行出 hour 行
  (avg/max; totals 取本小时末累计快照) -> 按窗裁剪(raw 段留 raw_window、hour 段留
  rollup_window, 窗口值由调用方从 config.qb_traffic 现取) -> 写 *.tmp -> os.replace
  原子替换(tmp+replace 纪律对齐 utils.atomic_write; 行尾固定 \\n, dat 是行式文本,
  对齐 TM history_traffic.dat 先例)。封口对同一小时桶幂等(upsert: 重封替换同桶 hour 行,
  内容无变化则跳过重写 —— 黄金法则 1)。
- 封口扫描(seal_sweep)是 catch-up 语义: 归并 < 当前桶的全部「有 raw 行且尚无 hour 行」
  的桶 —— 每小时首个采样触发只保证触发频率, 桶本身不依赖触发不缺席: 重启跨度(停机跨越
  整小时, 恢复后首个触发补封停机前残桶)与断连跳桶都不会把已产出的 raw 行永远留在 30d
  视图之外; 已封桶不重算(空闲系列每小时扫描零写放大)。
- rewrite 遇 PermissionError(Windows 读侧竞态: os.replace 目标被打开)退避重试 x3、
  每次 50ms; 仍失败则放弃本轮(原文件完好, 数据无损, 下一小时封口自然补上)。

读路径(§02.4 右, 面向 Web 线程只读; 本阶段供测试与 S4 API 使用):
- 不匹配格式/字段非法的行跳过并计数(纪律对齐 curves.parse_history_dat 坏行先例;
  TM 是外部只读文件, 我们自有写路径 —— 半行容错是自己的义务); 仅尾部半行是正常崩溃残留:
  无换行结尾的末段若是完整合法行则照常收数据(只是缺行尾换行, 追加侧会先补 \\n), 解析失败
  则按尾部半行跳过 —— 它豁免损坏占比(否则小文件的 1 行崩溃残留必然触发整文件隔离,
  与「kill 丢 <=1 行」验收冲突), 但计入 bad_lines 供观察;
- 坏行占比 > 5% 且坏行 >= 2 判文件损坏 -> 原文移 <name>.corrupt 后按空文件对待(不静默吞,
  也不让坏文件常驻报错); 绝对下限兜住「上一次崩溃的尾半行经追加补 \\n 后成为小文件中段
  坏行」的场景 —— 单行残留跳过即可, 随下一次封口重写自洁, 不据以整文件隔离(kill 丢行
  恒 <=1); 下一次追加按新建重建(头行 + key 行);
- 文件 <=205KB(raw 24h@30s + hour 30d 设计上界)一次性快读即关。

index.json 与启动对账(§02.5):
- 条目 {frozen_at, created_at, updated_at}; frozen_at 本阶段(P2)建条目一律 None ——
  删种冻结/重加解冻/按龄淘汰是 S3, 本层只留字段位;
- 写入走 utils.atomic_write, 仅条目变化时点写(建文件/封口/对账), 非每采样;
  updated_at 随追加在内存推进, 到上述时点才落盘(崩溃后滞后 <=1 小时, 对 S3 的按龄
  淘汰判据 7d 粒度无影响);
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
import os
import re
import tempfile
import time
from dataclasses import dataclass
from typing import Optional

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

#: 头行(格式标识 + 版本, §02.3 逐列冻结)
HEADER_LINE = "# auto-qb qb-traffic v1"

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

#: 坏行占比损坏阈值(§02.4: > 5% 判文件损坏)
CORRUPT_RATIO = 0.05

#: rewrite 遇 PermissionError 的重试次数(不含首次; §02.4 x3)
REWRITE_RETRIES = 3

#: rewrite 重试退避间隔(秒)
REWRITE_BACKOFF_S = 0.05

#: 小时桶宽(秒)
HOUR_SECONDS = 3600

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
class ParsedSeries:
    """单文件解析结果(read_series 返回; S4 API 的取数入口)"""

    key: Optional[str]  # 头行 key 行的系列标识(无头行/坏头行时 None)
    raw: tuple  # Tuple[RawRow, ...](文件序; 封口裁剪时另行排序)
    hours: tuple  # Tuple[HourRow, ...](按 hour_epoch 升序, 同桶重复取最后一行)
    bad_lines: int  # 跳过的坏行数(含尾部半行)
    data_lines: int  # 受检行总数(头行后全部行, 含空行/注释/坏行; 损坏占比分母)
    torn_tail: bool = False  # 末尾存在未写完的半行(正常崩溃残留; 豁免损坏占比)


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

    头行必须恰为 HEADER_LINE(缺失/不符 = 整文件不匹配格式, 全部行记坏); 其后每行都计入
    data_lines(损坏占比分母), key 行取首个(重复 key 行记坏), raw/hour 行按列解析, 空行/
    注释行跳过不计坏, 其余不匹配格式的一律跳过计数。无换行结尾的末段是崩溃残留位: 解析
    成功则照常收数据(缺的只是行尾换行, 追加侧会先补), 失败则记 torn_tail(豁免损坏占比)。
    hour 行同桶重复取最后一行(重封 upsert 的读侧口径, 对齐 curves 重复日期先例)。
    """
    lines = text.splitlines()
    torn = bool(text) and not text.endswith("\n")
    if not lines or lines[0].strip() != HEADER_LINE:
        # 头行缺失/不符: 文件级不匹配格式 —— 每一行都算坏行(损坏判定必然命中阈值)
        return ParsedSeries(key=None, raw=(), hours=(), bad_lines=len(lines), data_lines=len(lines), torn_tail=torn)
    key: Optional[str] = None
    raw_rows: list = []
    hours_by_epoch: dict = {}
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
        except (ValueError, IndexError):
            pass
        bad += 1  # 键名/列数不匹配或字段非法
        if torn and i == last_idx - 1:
            torn_tail = True  # 尾部半行 = 正常崩溃残留(阈值豁免, 见 _read_path)
    hours = tuple(hours_by_epoch[e] for e in sorted(hours_by_epoch))
    return ParsedSeries(key=key, raw=tuple(raw_rows), hours=hours, bad_lines=bad, data_lines=data, torn_tail=torn_tail)


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

    def seal_hour(self, key: str, hour_epoch: int, now: float, raw_window: float, rollup_window: float) -> bool:
        """单桶封口 + 按窗裁剪(§02.4): 指定桶 upsert 重封(测试与迟到行兜底入口)"""
        return self._seal_file(key, now, raw_window, rollup_window, force_buckets=(hour_epoch, ))

    def seal_sweep(self, current_bucket: int, now: float, raw_window: float, rollup_window: float) -> int:
        """小时封口扫描(catch-up 语义): global + torrents/ 全系列各补封全部未封桶(§02.4「逐系列」)

        归并 < current_bucket 的「有 raw 行且尚无 hour 行」的桶 —— 触发频率由采样器保证
        (每小时首个采样), 桶本身不依赖触发不缺席: 重启跨度 / 断连跳桶不会把已产出的 raw 行
        永远留在 hour 段之外; 已封桶不重算。顺带完成按窗裁剪(裁剪只在重写时发生, 空闲系列的
        窗外残行留待下次活动重写时自洁 —— 读侧按窗取数不受影响)。
        返回发生 rewrite 的文件数(日志/测试用)。
        """
        keys = [GLOBAL_KEY]
        if os.path.isdir(self._torrents_dir):
            for name in sorted(os.listdir(self._torrents_dir)):
                if name.endswith(DAT_SUFFIX):
                    keys.append(TORRENT_KEY_PREFIX + name[:-len(DAT_SUFFIX)])
        rewritten = 0
        for key in keys:
            if self._seal_file(key, now, raw_window, rollup_window, due_before=current_bucket):
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
    ) -> bool:
        """单文件封口: 归并待封桶出 hour 行 + 按窗裁剪, 有变化才重写; 返回是否 rewrite

        待封桶 = force_buckets(直接指定, upsert 重封 —— 已有同桶 hour 行也被替换)∪
        (due_before 之下「有 raw 行且尚无 hour 行」的桶 —— catch-up 补封)。桶内全 null 行
        不产 hour 行(空桶 = null, §05.1 —— 30d 视图由缺行呈现断线)。裁剪: raw 段留
        ts >= now - raw_window, hour 段留 hour_epoch >= now - rollup_window(边界含)。
        内容无变化(无新行、无裁剪、无坏行、重封行与旧行相同)则跳过重写 —— 空闲系列每小时
        扫描零写放大(黄金法则 1); 坏行(尾部半行等)不算内容一致 —— 随重写一并清除(自洁)。
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
            due |= raw_buckets - {h.hour_epoch for h in parsed.hours}
        new_hours = []
        for b in sorted(due):
            row = self._aggregate_bucket(parsed.raw, b)
            if row is not None:
                new_hours.append(row)
        replaced = {h.hour_epoch for h in new_hours}
        kept_raw = sorted((r for r in parsed.raw if r.ts >= now - raw_window), key=lambda r: r.ts)
        kept_hours = sorted(
            (h for h in parsed.hours if h.hour_epoch >= now - rollup_window and h.hour_epoch not in replaced),
            key=lambda h: h.hour_epoch,
        ) + new_hours
        same_content = (
            kept_hours == list(parsed.hours) and kept_raw == sorted(parsed.raw, key=lambda r: r.ts) and
            parsed.bad_lines == 0
        )
        if same_content:
            self._flush_index()  # 追加期内存推进的 updated_at 在封口时点落盘(§02.5)
            return False
        if not self._rewrite_file(path, key, tuple(kept_hours), tuple(kept_raw)):
            return False  # rewrite 被读侧竞态占满重试后放弃: 原文件完好, 下轮封口自然补上
        self._flush_index()
        return True

    def _rewrite_file(self, path: str, key: str, hours: tuple, raws: tuple) -> bool:
        """整文件重写: 同目录 tmp -> fsync -> os.replace(纪律对齐 utils.atomic_write;
        行尾固定 \\n —— dat 是行式文本, 对齐 TM history.dat 先例, 与追加行一致)。
        PermissionError(Windows 读侧竞态)退避重试 x3, 仍失败放弃本轮(原文件完好)。"""
        lines = [HEADER_LINE, f"key,{key}"]
        lines.extend(format_hour_row(h) for h in hours)
        lines.extend(format_raw_row(r.ts, r.dl_rate, r.up_rate, r.dl_total, r.up_total) for r in raws)
        payload = "\n".join(lines) + "\n"
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
    def _aggregate_bucket(raw_rows: tuple, hour_epoch: int) -> Optional[HourRow]:
        """桶内非 null raw 行归并(§02.3): avg 取整(round); totals 取本小时末累计快照"""
        rows = [r for r in raw_rows if hour_epoch <= r.ts < hour_epoch + HOUR_SECONDS and not r.is_null]
        if not rows:
            return None
        n = len(rows)
        last = max(rows, key=lambda r: r.ts)
        return HourRow(
            hour_epoch=hour_epoch,
            dl_avg=int(round(sum(r.dl_rate for r in rows) / n)),
            dl_max=max(r.dl_rate for r in rows),
            up_avg=int(round(sum(r.up_rate for r in rows) / n)),
            up_max=max(r.up_rate for r in rows),
            dl_total=int(last.dl_total),
            up_total=int(last.up_total),
        )

    # ---------- 读路径(§02.4 右, 只读) ----------

    def read_series(self, key: str) -> ParsedSeries:
        """读单系列(一次性快读即关; S4 API 的取数入口)。文件缺失 = 空系列"""
        path = self.series_path(key)
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            return ParsedSeries(key=key, raw=(), hours=(), bad_lines=0, data_lines=0)
        parsed = self._read_path(path)
        if parsed.key is None:
            return ParsedSeries(key=key, raw=(), hours=(), bad_lines=parsed.bad_lines, data_lines=parsed.data_lines)
        return parsed

    def _read_path(self, path: str) -> ParsedSeries:
        """读 + 坏行计数 + 损坏阈值处置(>5% 且坏行 >= 2 移 .corrupt 后按空文件对待, §02.4)

        - 尾部半行(正常崩溃残留, torn_tail)从占比分子分母双侧扣除;
        - 坏行 >= 2 的绝对下限: 上一次崩溃的尾半行经「追加先补 \\n」后会成为中段坏行,
          小文件 1 行即超 5% —— 若据此整文件隔离, kill 的丢失就从 <=1 行放大成全文件,
          与 P2 验收冲突; 单行残留跳过即可, 随下一次封口重写自洁(坏行不算内容一致);
          真实损坏(盘损/格式错乱)坏行远不止 1 行, 阈值判据不受影响。
        """
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError as e:
            logger.warning(f"流量存储 | {os.path.basename(path)} 读取失败(按空系列对待): {e}")
            return ParsedSeries(key=None, raw=(), hours=(), bad_lines=0, data_lines=0)
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

    # ---------- 内部 ----------

    def _ensure_layout(self) -> None:
        """目录惰性创建(首个产出点时; exist_ok 幂等, §02.1)"""
        os.makedirs(self._torrents_dir, exist_ok=True)
