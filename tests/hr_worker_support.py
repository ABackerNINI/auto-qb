"""`hr_worker_support` 支撑: 从 `test_hr_worker.py` 拆出的模块级辅助/常量(move-only 搬迁, 未改语义)."""

import logging

import threading

import time

from auto_qb.hr.fetcher import NullFetcher

from auto_qb.hr.model import CHANNEL_OK, CHANNEL_SILENT

from auto_qb.hr.resolve import HrIdentity, HrSiteView, HrViewSet, judge_record

from auto_qb.hr.service import ACTION_ERROR, ACTION_NO_CHANNEL, ACTION_PARTIAL, ACTION_REFRESHED, ACTION_REUSED, \
    ACTION_WAITING, REASON_BUDGET, HrRefreshResult

import auto_qb.hr.worker as worker_module

from auto_qb.hr import events

from auto_qb.hr.fetcher import HrFetchError, NullFetcher

from auto_qb.hr.worker import HrViewPublisher, HrWorker, pacing_class, stable_key, view_signature

from auto_qb.infra.logging import DOMAIN_ATTR

from helpers import capture_logs

from clock import wait_until

from hr_helpers import EMPTY_TABLE_PAGE, REVISED_PAGE, FakeFetcher, global_conf, make_service, myhr_page, row, \
    site_conf, torrent_blob
from clock import FakeClock

TID_A = 313852


def _blobs(*tids: int):
    return {tid: torrent_blob(f"t{tid}.bin") for tid in tids}


def _pages(*tids: int):
    """三个档位都给同一批行(完整刷新: 覆盖证明成立)"""
    page = myhr_page([row(tid) for tid in tids])
    return {"A": page, "B": page, "C": page}


def _service(tmp_path, fetcher, *, global_overrides=None, persist=True, allow_fetch=True, clock=None, confs=None):
    """薄绑定到 hr_helpers.make_service 单点(issue 26-10-29-1404 收口)。

    本文件的差异面 = 真钟缺省(worker 的节流/视图行为按真实时间断言) —— 单点不给时钟
    默认值, 真/假钟的表态在这里; clock= 时照旧走假钟。owner 用单点默认 "tester"
    (收口前缺省空串 -> store 随机实例标识, 无用例断言该字样)。
    """
    return make_service(
        tmp_path,
        fetcher,
        now_fn=clock.now if clock is not None else time.time,
        site_confs=confs or {"pt.example.com": site_conf()},
        gconf=global_conf(**(global_overrides or {})),
        persist=persist,
        allow_fetch=allow_fetch,
    )


def _silence_worker(tmp_path, clock, endpoint, *, web_active):
    service = _service(tmp_path, FakeFetcher(pages=_pages(TID_A), blobs=_blobs(TID_A)), clock=clock)
    return HrWorker(
        service=service,
        publisher=HrViewPublisher(),
        endpoint=endpoint,
        poll_interval=60.0,
        now_fn=clock.now,
        web_active_fn=lambda: web_active,
    )
