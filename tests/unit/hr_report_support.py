"""`hr_report_support` 支撑: 从 `test_hr_report.py` 拆出的模块级辅助/常量(move-only 搬迁, 未改语义)."""

import io

import pathlib

import re

import time

import unicodedata

import pytest

from auto_qb.config.models import Config, HrCheckConfig, HrChannelConfig, SiteHrCheckConfig, TrackerConfig

from auto_qb.hr.channel import token_path

from auto_qb.hr.fetcher import HrChannelUnavailable, NullFetcher

from auto_qb.hr.model import FETCH_LANES, HrEntry, HrSiteData

from auto_qb.hr.adapters.nexusphp import NexusPhpMyhrAdapter

from auto_qb.hr.ratelimit import day_key

from auto_qb.hr.report import LocalPageFetcher, build_fetcher, run_hr_confirm_empty, run_hr_once, run_hr_status

import auto_qb.hr.service as hr_service

from auto_qb.hr.store import HrSiteStore

from hr_helpers import EMPTY_TABLE_PAGE, FakeFetcher, global_conf, make_service, myhr_page, row, site_conf, torrent_blob

SITE = "example"


def _config(tmp_path, html_dir=None, *, enabled=True, site_enabled=True, data_dir=None) -> Config:
    cfg = Config()
    cfg.data_dir = str(data_dir or tmp_path / "data")
    # 间隔设 0: 走查会真的按 min_interval 等待, 测试不必真等 90s
    cfg.hr_check = HrCheckConfig(enabled=enabled, min_interval=0.0)
    cfg.trackers[SITE] = TrackerConfig(
        name=SITE,
        domains=["pt.example.com"],
        hr_check=SiteHrCheckConfig(
            enabled=site_enabled,
            tracker=SITE,
            hr_page_url="https://pt.example.com/myhr.php",
            download_path="/download.php?id={id}",
            page_param="page",
            listing="list",
            required_seeding_time=86400.0,
        ),
    )
    return cfg


def _seed(tmp_path, fetcher, *, site=None, gconf=None) -> None:
    """用真服务把一份数据落到 <tmp_path>/hr/<site>.json —— 现状报告读的就是它

    刻意不打钟(用真时钟): 报告里的「x 前 / 复用窗至」才有意义。
    """
    make_service(tmp_path, fetcher, now_fn=time.time, site_confs={
        SITE: site or site_conf()
    }, gconf=gconf).refresh_site(SITE)


def _rows_seed(tmp_path, entries, blobs=None):
    """落一份含指定条目的站点数据(明细表读它)"""
    _seed(
        tmp_path,
        FakeFetcher(
            pages={
                "A": myhr_page(entries),
                "B": EMPTY_TABLE_PAGE,
                "C": EMPTY_TABLE_PAGE
            },
            blobs=blobs or {},
        ),
    )


def _add_site(cfg, name: str) -> None:
    """给配置加第二个启用站点(多站点输出面用)"""
    cfg.trackers[name] = TrackerConfig(
        name=name,
        domains=[f"pt-{name}.example.com"],
        hr_check=SiteHrCheckConfig(
            enabled=True,
            tracker=name,
            hr_page_url=f"https://pt-{name}.example.com/myhr.php",
            download_path="/download.php?id={id}",
            page_param="page",
            listing="list",
            required_seeding_time=86400.0,
        ),
    )
