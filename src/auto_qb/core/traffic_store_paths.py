"""traffic_store 拆分件: 日期窗口与按天目录/路径解析(R5 move-only, 计划 26-11-02-2342 §07)。"""
import os
from datetime import datetime, timedelta
from typing import Optional

from .traffic_store_common import (
    DAT_SUFFIX,
    GLOBAL_KEY,
    TORRENTS_DIR_NAME,
    TORRENT_KEY_PREFIX,
    TRAFFIC_V4_DIR_NAME,
    V4_AGG_NAME,
    V4_DATE_FORMAT,
    V4_GLOBAL_DIR_NAME,
    _INFOHASH_RE,
    _V4_DATE_RE,
)

# ---------- 按天目录与路径解析(§06.2) ----------


def v4_root_dir(data_dir: str) -> str:
    """存储根: <data_dir>/qb-traffic-v4/(v4 计划 §01 换代语义; 旧 qb-traffic-v3/ 原样留存
    不读不迁移 —— R2, 删留决定权在用户)"""
    return os.path.join(data_dir, TRAFFIC_V4_DIR_NAME)


def v4_series_dir(data_dir: str, key: str) -> str:
    """系列键 -> 系列目录(global/ 或 torrents/<infohash>/); 非法键 fail-fast(对齐 v2)"""
    if key == GLOBAL_KEY:
        return os.path.join(v4_root_dir(data_dir), V4_GLOBAL_DIR_NAME)
    if key.startswith(TORRENT_KEY_PREFIX):
        h = key[len(TORRENT_KEY_PREFIX):]
        if not h or not _INFOHASH_RE.fullmatch(h):
            raise ValueError(f"非法单种系列键(哈希须为文件名安全字符): {key!r}")
        return os.path.join(v4_root_dir(data_dir), TORRENTS_DIR_NAME, h)
    raise ValueError(f"未知系列键: {key!r}")


def v4_day_file_path(data_dir: str, key: str, date_str: str) -> str:
    """系列键 + 本地日期串 -> 天文件路径(<YYYY-MM-DD>.dat); 日期串非法 fail-fast"""
    _validate_date(date_str)
    return os.path.join(v4_series_dir(data_dir, key), date_str + DAT_SUFFIX)


def v4_agg_file_path(data_dir: str, key: str) -> str:
    """系列键 -> agg.dat 路径(§02.2: 每系列一个聚合文件)"""
    return os.path.join(v4_series_dir(data_dir, key), V4_AGG_NAME)


def v4_rel_dir_to_key(rel_dir: str) -> Optional[str]:
    """v4 根下相对目录 -> 系列键(global -> "global", torrents/<h> -> "torrent:<h>");
    不匹配返回 None(S3 扫目录时跳过非系列项)。两种路径分隔符都认(Windows 扫目录)"""
    norm = rel_dir.replace("\\", "/").strip("/")
    if norm == V4_GLOBAL_DIR_NAME:
        return GLOBAL_KEY
    if norm.startswith(TORRENTS_DIR_NAME + "/"):
        h = norm[len(TORRENTS_DIR_NAME) + 1:]
        if h and _INFOHASH_RE.fullmatch(h):
            return TORRENT_KEY_PREFIX + h
    return None


def v4_day_file_date(filename: str) -> Optional[str]:
    """天文件名 "<YYYY-MM-DD>.dat" -> 日期串; 其余(agg.dat/.corrupt/杂物/非真实日历
    日期形状)返回 None"""
    if not filename.endswith(DAT_SUFFIX):
        return None
    d = filename[:-len(DAT_SUFFIX)]
    if not _V4_DATE_RE.fullmatch(d):
        return None
    try:
        datetime.strptime(d, V4_DATE_FORMAT)  # 真实日期校验(2 月 30 日等)
    except ValueError:
        return None
    return d


def _validate_date(date_str: str) -> None:
    """日期串校验: 形状 YYYY-MM-DD 且为真实日历日期; 违者 ValueError"""
    if not _V4_DATE_RE.fullmatch(date_str or ""):
        raise ValueError(f"非法日期串(须 YYYY-MM-DD): {date_str!r}")
    datetime.strptime(date_str, V4_DATE_FORMAT)  # 真实日期校验(2 月 30 日等)


def v4_date_str_epoch(date_str: str) -> int:
    """本地日期串 -> 当日 00:00 epoch(本地时区, §02.2 day_epoch 口径)"""
    _validate_date(date_str)
    return int(datetime.strptime(date_str, V4_DATE_FORMAT).timestamp())


def v4_epoch_date_str(ts: float) -> str:
    """epoch 秒 -> 本地日期串(YYYY-MM-DD)"""
    return datetime.fromtimestamp(ts).strftime(V4_DATE_FORMAT)


def v4_day_epoch(ts: float) -> int:
    """epoch 秒 -> 本地当日 00:00 epoch(§02.2 day_epoch)"""
    d = datetime.fromtimestamp(ts)
    return int(datetime(d.year, d.month, d.day).timestamp())


def v4_month_epoch(ts: float) -> int:
    """epoch 秒 -> 本地自然月 1 日 00:00 epoch(§02.2 month_epoch)"""
    d = datetime.fromtimestamp(ts)
    return int(datetime(d.year, d.month, 1).timestamp())


def v4_next_month_epoch(ts: float) -> int:
    """epoch 秒 -> 下一自然月 1 日 00:00 epoch(S3b all 视图逐月铺格用): ts 所在月的
    次月 1 日 00:00(本地时区); 结果严格大于输入(逐月推进必终止)。"""
    d = datetime.fromtimestamp(int(ts))
    year, month = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    return int(datetime(year, month, 1).timestamp())


def v4_window_dates(start_epoch: float, end_epoch: float) -> frozenset:
    """查询窗口起止(epoch 秒) -> 涉及的本地日期串集合(含两端所在日; §05.2 按天加载
    的窗口 -> 日期集合解析)。end < start -> ValueError(调用方口径错误, fail-fast)。"""
    if end_epoch < start_epoch:
        raise ValueError(f"窗口起止倒置: {start_epoch} > {end_epoch}")
    d0 = datetime.fromtimestamp(start_epoch).date()
    d1 = datetime.fromtimestamp(end_epoch).date()
    out = set()
    d = d0
    while d <= d1:
        out.add(d.strftime(V4_DATE_FORMAT))
        d += timedelta(days=1)
    return frozenset(out)
