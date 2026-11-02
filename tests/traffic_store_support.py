"""`traffic_store_support` 支撑: 从 `test_traffic_store.py` 拆出的模块级辅助/常量(move-only 搬迁, 未改语义)."""

import builtins

import inspect

import logging

import os

import re

import tempfile

import threading

import time

from datetime import datetime

import pytest

import auto_qb.core.traffic_store as traffic_store_module

from auto_qb.config import QbTraffic

from auto_qb.core.modules.traffic_sample_mod import GLOBAL_SERIES_KEY

from auto_qb.core.traffic_store import (
    DRIFT_TOL_MS,
    DT_MS_MAX,
    HEADER_LINE_V4,
    HOUR_SECONDS,
    REWRITE_BACKOFF_S,
    REWRITE_RETRIES,
    TORRENTS_DIR_NAME,
    TRAFFIC_V4_DIR_NAME,
    V4_AGG_CACHE_MAX_ENTRIES,
    AggRow,
    LiveTail,
    LiveTailRun,
    TrafficV4Store,
    V4Block,
    V4DayCache,
    V4HourSample,
    V4NullRun,
    V4Sample,
    V4ZeroRun,
    format_agg_row,
    format_v4_b_row,
    format_v4_day_text,
    format_v4_n_row,
    format_v4_r_row,
    format_v4_z_row,
    parse_v4_agg_text,
    parse_v4_day_text,
    v4_agg_file_path,
    v4_block_agg_totals,
    v4_block_gap_continuous,
    v4_block_slots,
    v4_bucket_width_s,
    v4_date_str_epoch,
    v4_day_epoch,
    v4_day_file_date,
    v4_day_file_path,
    v4_epoch_date_str,
    v4_hour_agg,
    v4_live_tail_slots,
    v4_merge_agg,
    v4_month_epoch,
    v4_next_month_epoch,
    v4_rel_dir_to_key,
    v4_rollup_agg,
    v4_root_dir,
    v4_series_dir,
    v4_window_dates,
    v4_z_totals_ramp,
)

from helpers import (
    FakeClient,
    FakeTorrent,
    active_torrent,
    make_manager,
    seed_store,
    server_state,
    write_dat_lines,
)

HOUR = HOUR_SECONDS

H0 = 10 * HOUR  # 被封口的小时桶起点

H1 = 11 * HOUR  # 当前小时桶起点(封口触发时刻所在桶)


def _mgr(tmp_path, qb_traffic, data_dir=True) -> object:
    """带 qb_traffic 段的测试 manager(同 test_traffic_sample._mgr_with_traffic 口径)"""
    mgr = make_manager(str(tmp_path / "state.json"))
    if data_dir:
        mgr.config.data_dir = str(tmp_path)
    mgr.client = FakeClient()
    if qb_traffic is not None:
        mgr.config.qb_traffic = qb_traffic
    return mgr


def _run_sample(mgr, dry_run=False) -> None:
    """直调一轮采样(时钟线钩子的执行体; issue 26-10-16-0954 起采样不在队列里)"""
    mgr.host.get("qb_traffic").handle_traffic_sample(dry_run=dry_run)


def _read_text(path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _v4_day_text(lines) -> str:
    """手工构造 v3 天文件文本(行列表逐行写, \\n 行尾)"""
    return "\n".join(lines) + "\n"


_S2B_H0 = (1_760_000_000 // HOUR) * HOUR  # hour 对齐的现代 epoch(Windows 不支持负 epoch, 勿用 1970 附近)


def _agg_row(
    kind: str, epoch: int, dl_avg=10, dl_max=20, up_avg=5, up_max=8, dl_total=100, up_total=200, cov=3600
) -> AggRow:
    """聚合行构造辅助(默认值可覆盖)"""
    return AggRow(kind, epoch, dl_avg, dl_max, up_avg, up_max, dl_total, up_total, cov)


def _v4_day_text(lines) -> str:
    """手工构造 v4 天文件文本(行列表逐行写, \\n 行尾)"""
    return "\n".join(lines) + "\n"
