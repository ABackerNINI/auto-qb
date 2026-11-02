"""`hr_status_support` 支撑: 从 `test_hr_status.py` 拆出的模块级辅助/常量(move-only 搬迁, 未改语义)."""

import json

from types import SimpleNamespace

from auto_qb.config.models import SiteHrCheckConfig

from auto_qb.hr import report

from auto_qb.hr.model import (
    CHANNEL_NETWORK,
    CHANNEL_NO_PERMISSION,
    CHANNEL_OK,
    LANE_FAILED,
    LANE_IDLE,
    LANE_OK,
    SOURCE_EXEMPT,
    SOURCE_NOT_LISTED,
    SOURCE_SATISFIED,
    HrEntry,
    HrHistoryEvent,
    HrLaneState,
    HrSiteData,
    HrVerified,
    HrWaveMeta,
)

from auto_qb.hr.service import _lanes_summary_from

from auto_qb.hr.ratelimit import HrLimits, day_key

from auto_qb.hr.resolve import HrSiteView

from auto_qb.hr.status import (
    CHANNEL_TEXTS,
    LANE_STATUS_TEXTS,
    LANE_TEXTS,
    LaneStatus,
    QuotaStatus,
    SOURCE_TEXTS,
    SiteStatus,
    _history_lanes,
    _lane_statuses,
    _retention_text,
    ago_text,
    blocking_reason,
    build_site_statuses,
    duration_text,
    entry_details,
    history_rows,
    lane_counts,
    need_seed_text,
    site_conf_interval,
    site_status,
    stamp_text,
)

from webui_helpers import (  # 键面单点(与 test_web_hr 同引, issue 26-10-21-0502)
    ENTRY_ROW_KEYS,
    HISTORY_LANE_KEYS,
    HISTORY_ROW_KEYS,
    SITE_STATUS_KEYS,
)


def _site(entries) -> HrSiteData:
    """最小站点数据: 只填索引(verified join 与排序的被测面都在这)"""
    data = HrSiteData()
    for e in entries:
        data.index[e.tid] = e
    return data


def _entry(
    tid: int,
    *,
    lane: str = "A",
    down=None,
    up=None,
    ratio=None,
    need=None,
    active: bool = True,
    missing_streak: int = 0,
    ih1: str = "",
    ih2: str = "",
) -> HrEntry:
    return HrEntry(
        tid=tid,
        name=f"EXAMPLE {tid}",
        lane=lane,
        uploaded_bytes=up,
        downloaded_bytes=down,
        ratio=ratio,
        need_seed_seconds=need,
        infohash_v1=ih1,
        infohash_v2=ih2,
        active=active,
        missing_streak=missing_streak,
        first_seen=111.0,
        last_seen=222.0,
    )
