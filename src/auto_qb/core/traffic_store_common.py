"""traffic_store 拆分件: 常量与低层编解码助手(R5 move-only, 计划 26-11-02-2342 §07)。

只放常量与纯助手(无 logger、无模块级可变状态), 供 paths/codec/agg/根模块共享。
"""
import math
import re
from typing import Optional

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
#: 消费端必须 fullmatch(issue 26-11-08-0045): Python 的 $ 允许串尾恰一个换行,
#: re.match 下 "ABC\n" 放行, fail-fast 形同虚设; fullmatch(全串必须被消费)才是本意。
_INFOHASH_RE = re.compile(r"^[A-Za-z0-9_-]+$")

#: v4 全局系列目录名(天文件 + agg.dat 的父目录)
V4_GLOBAL_DIR_NAME = "global"

#: v4 每系列聚合文件名(hour/day/month 9 列追加混存, §02.2)
V4_AGG_NAME = "agg.dat"

#: dt_ms 校验上界(毫秒, 一天; §02.1 全整数/毫秒口径)
DT_MS_MAX = 86_400_000

#: 写侧累积漂移容差(毫秒, 裁决 D2; 模块常量非配置键, §02.3)
DRIFT_TOL_MS = 250

#: agg 行字段数(kind + epoch + 6 数据列 + cov_s; §02.2 hour/day/month 同构)
AGG_FIELDS = 9

#: agg 8 列旧行型字段数(解析兜底 cov_s = 3600, 防御性 —— v4 全新目录正常不出现)
AGG_LEGACY_FIELDS = 8

#: agg 行型种类(§02.2)
AGG_KINDS = ("hour", "day", "month")

#: 本地日期串格式(天文件名与 day_epoch 口径, §06.2/§02.2)
V4_DATE_FORMAT = "%Y-%m-%d"

#: 逐级派生合法行型(§04.1: 严格逐级 —— day 只从 hour 行聚, month 只从 day 行聚)
V4_ROLLUP_KINDS = ("day", "month")

#: 天文件日期串形状(严格 4-2-2 位, 配合 strptime 拒绝 2 月 30 日等)
#: 消费端必须 fullmatch(issue 26-11-08-1923): Python 的 $ 允许串尾恰一个换行,
#: re.match 下 "2026-11-08\n" 放行; fullmatch(全串必须被消费)才是本意。
_V4_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


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


def _fmt_dt_ms(dt_ms: Optional[int]) -> str:
    """可选 dt_ms 列文本(None = 缺省标称); 非法 fail-fast(写侧纪律 —— 解析侧按坏行)"""
    if dt_ms is None:
        return ""
    if not isinstance(dt_ms, int) or isinstance(dt_ms, bool) or dt_ms < 1 or dt_ms > DT_MS_MAX:
        raise ValueError(f"非法 dt_ms(须正整数且 <= {DT_MS_MAX}): {dt_ms!r}")
    return str(dt_ms)


def _fmt_dt_tail(dt_ms: Optional[int]) -> str:
    """可选第 6 列的行尾段(空 = 不写该列)"""
    tail = _fmt_dt_ms(dt_ms)
    return f",{tail}" if tail else ""


def _fmt_interval_s(interval_s: float) -> str:
    """块头 interval_s 列文本(规范十进制): 整数值不带小数点(与历史整秒文件形态一致),
    非整值最短往返表示(1.5 -> "1.5")"""
    if interval_s == int(interval_s):
        return str(int(interval_s))
    return repr(float(interval_s))


def _parse_dt_ms(text: str) -> int:
    """dt_ms 列解析(§02.1/§02.3): 须正整数且 <= DT_MS_MAX; 违者 ValueError -> 整行坏行"""
    v = int(text)  # 非数值抛 ValueError
    if v < 1 or v > DT_MS_MAX:
        raise ValueError(f"dt_ms 越界: {text}")
    return v


def _parse_pos_int(text: str) -> int:
    """正整数列(run_len); < 1 抛 ValueError"""
    v = int(text)
    if v < 1:
        raise ValueError(f"须正整数: {text}")
    return v


def _parse_interval_s(text: str) -> float:
    """块头 interval_s 列解析: >= 1 的数值, 允许小数秒(1.5); 整数十进制归一 float。
    NaN/inf/非数值/越界抛 ValueError -> 整行坏行(与 run_len 的正整数口径分离)"""
    v = float(text)
    if not math.isfinite(v) or v < 1:
        raise ValueError(f"interval_s 须 >= 1: {text}")
    return v


def _parse_nn_int(text: str) -> int:
    """非空非负整数列(r/z 数据列 —— 无 null 形态, null 走 n 游程); 违者 ValueError"""
    v = _parse_int_field(text)
    if v is None:
        raise ValueError("空列")
    return v


#: 头行 v4(每文件一次; v4 读侧对 v1/v2/v3 旧头行整文件不匹配, 不设双读 —— R2 换代语义)
HEADER_LINE_V4 = "# auto-qb qb-traffic v4"

#: v4 存储根目录名(相对 data_dir, v4 计划 §01 换代语义; 旧 qb-traffic-v3/ 原样留存不读)
TRAFFIC_V4_DIR_NAME = "qb-traffic-v4"
