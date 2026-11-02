"""`traffic_grid_support` 支撑: 从 `test_traffic_grid.py` 拆出的模块级辅助/常量(move-only 搬迁, 未改语义)."""

import math

import time

import pytest

from auto_qb.core.traffic_grid import (
    BucketObs,
    MAX_RAW_BUCKETS,
    MONTH_NOMINAL_S,
    V4PointEntry,
    WINDOW_SPECS,
    WindowGrid,
    build_grid,
    build_month_grid,
    grid_for_now,
    group_null_mask,
    group_rate_points,
    group_totals_points,
    rate_points,
    series_totals_points,
    v4_agg_obs,
    v4_agg_obs_live,
    v4_earliest_row_ts,
    v4_grid_obs,
    v4_rate_from_totals,
    v4_series_points,
    v4_series_slots,
    v4_totals_points,
    _V4_SEAM_LOOKBACK_S,
    _V4_SEAM_NULL_S,
    _V4_SEAM_SPREAD_MIN_S,
    _bucket_delta,
    _floor_buckets,
)

from auto_qb.core.traffic_store import (
    AggRow,
    LiveTail,
    LiveTailRun,
    V4Block,
    V4NullRun,
    V4ParsedAgg,
    V4Sample,
    V4Slot,
    V4ZeroRun,
    format_v4_day_text,
    parse_v4_day_text,
    v4_block_slots,
    v4_live_tail_slots,
    v4_date_str_epoch,
    v4_day_epoch,
    v4_month_epoch,
    v4_next_month_epoch,
    v4_window_dates,
)

#: 固定"现在"(2027-01-15, 纯测试时刻; 恰为 30 与 3600 的公倍数, 对齐断言干净)
NOW = 1_800_000_000


def _p(entry):
    """V4PointEntry -> 可比元组"""
    return (entry.t, entry.dl_rate, entry.up_rate, entry.dl_total, entry.up_total)
