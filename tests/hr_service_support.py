"""`hr_service_support` 支撑: 从 `test_hr_service.py` 拆出的模块级辅助/常量(move-only 搬迁, 未改语义)."""

import logging

import re

import tempfile

import time

from datetime import datetime

from typing import Dict

import pytest

import auto_qb.hr.service as hr_service

from auto_qb.hr import events

from auto_qb.hr.fetcher import (
    HrChannelStopped,
    HrChannelTimeout,
    HrExtensionNetwork,
    HrExtensionNoPermission,
    HrFetchError,
    NullFetcher,
)

from auto_qb.hr.model import (
    CHANNEL_NETWORK,
    CHANNEL_NO_PERMISSION,
    CHANNEL_OK,
    FETCH_LANES,
    LANE_EXEMPT,
    LANE_FAILED,
    LANE_IDLE,
    LANE_OK,
    LANE_SATISFIED,
    LANE_SCOPE,
    LANE_UNSATISFIED,
    SOURCE_EXEMPT,
    SOURCE_NOT_LISTED,
    SOURCE_SATISFIED,
    HrDlFail,
    HrDownloaded,
    HrEntry,
    HrLaneState,
    HrSiteData,
    HrVerified,
    HrWaveMeta,
)

from auto_qb.hr.resolve import HrAnchor, HrIdentity, judge_record

from auto_qb.hr.status import build_site_statuses, entry_details

from auto_qb.hr.store import HrSiteStore

from auto_qb.hr.service import (
    ACTION_ERROR,
    ACTION_LOCKED,
    ACTION_NO_CHANNEL,
    ACTION_PARTIAL,
    ACTION_REFRESHED,
    ACTION_REUSED,
    ACTION_WAITING,
    CHANNEL_SILENCE_WARN,
    COVERAGE_SLACK,
    DL_RETRY_COOLDOWN,
    FUZZY_NAME_K,
    HISTORY_NOTES_MAX,
    INDEX_RETENTION,
    LANE_FAIL_ALERT_STREAK,
    MISSING_GRACE_WAVES,
    HrRefreshService,
    MAX_DOWNLOAD_RETRIES,
    REASON_BUDGET,
    REASON_NONE,
    REASON_PARSE,
    _absence_proven_all,
    _Budget,
    _lane_covers_done,
    _position_covered,
    _prune_index,
    _release_record,
    _settle_lane,
    _WaveContext,
    _lanes_summary_from,
    _mark_fetch_failed_lane,
    fuzzy_name_match,
)

from helpers import capture_logs

from hr_helpers import (
    CHALLENGE_PAGE,
    EMPTY_TABLE_PAGE,
    LOGIN_PAGE,
    REVISED_PAGE,
    Clock,
    FakeFetcher,
    global_conf,
    make_service as hr_make_service,
    myhr_page,
    row,
    site_conf,
    torrent_blob,
)

SITE = "example"

URL = "https://pt.example.com/myhr.php"


def url_of(lane: str, page: int = 1) -> str:
    return f"{URL}?hrtype={lane}" + (f"&page={page}" if page > 1 else "")


def E(done: str) -> float:
    return datetime.strptime(done, "%Y-%m-%d %H:%M:%S").timestamp()


DONE_OLD = "2026-09-01 10:00:00"  # 深处(老)行

DONE_NEW = "2026-09-20 10:00:00"  # 浅处(新)行

T_DONE_NEW = E(DONE_NEW)


def anchor_for(
    blob_name: str,
    *,
    completion_on: float = -1,
    seeding_time: int = 0,
    added_on: int = 100,
    name: str = ""
) -> HrAnchor:
    return HrAnchor(
        added_on=added_on,
        downloaded=1 << 30,
        completion_on=int(completion_on),
        progress=1.0,
        seeding_time=seeding_time,
        name=name or blob_name,
    )


def _no_sleep(_seconds: float) -> None:
    """空转 sleeper(测试不打盹; 需要测「无 sleeper 放弃」的用例显式传 None)"""


def make_service(
    tmp_path,
    fetcher,
    *,
    site=None,
    gconf=None,
    clock=None,
    sleep_max=None,
    round_wait_max=None,
    allow_fetch=True,
    persist=True,
    sleeper=_no_sleep,
    confs=None,
    data_dir=None,
) -> HrRefreshService:
    """薄绑定到 hr_helpers.make_service 单点(issue 26-10-29-1404 收口, 调用点签名不变)。

    本文件的差异面: 假钟(clock 缺省时**每次新建** Clock 实例, 不共享 —— 可推进时钟
    跨用例共享就是状态泄漏)+ 空转 sleeper + owner="test"(owner 透传守阵
    test_store_lazy_branch_constructor_args 钉死该字样)。新场景(多站 confs / 换
    data_dir / sleeper=None)扩参数而不是内联 new。
    """
    return hr_make_service(
        tmp_path,
        fetcher,
        now_fn=clock or Clock(),
        site_confs=confs if confs is not None else {SITE: site or site_conf()},
        gconf=gconf,
        owner="test",
        persist=persist,
        allow_fetch=allow_fetch,
        sleeper=sleeper,
        data_dir=data_dir,
        sleep_max=sleep_max,
        round_wait_max=round_wait_max,
    )


def run_wave(service, anchors=None):
    # 三态直通(计划 26-10-05-0555 §2.5): None = 锚点未知(不构成稳态, 与本计划实施前的闸门节奏一致);
    # 显式 {} = 确认零锚点(可降频)。旧实现这里是 `anchors or {}`, 复刻的是 refresh_site 已删除的吞并。
    return service.refresh_site(SITE, anchors)


def mk_blob(name: str):
    """(blob, 真实 infohash) —— 锚点键必须用真实算出的 hash(与 blob 一致, 匹配才成立)"""
    from auto_qb.hr.bencode import compute_infohashes

    blob = torrent_blob(name=name)
    v1, _v2, _info = compute_infohashes(blob)
    return blob, v1


def standard_pages(rows_a=None, rows_b=None, rows_c=None, *, has_next: bool = False):
    """标准三页(每档一页, 无翻页)"""
    return {
        url_of("A"): myhr_page(rows_a or [], has_next=has_next),
        url_of("B"): myhr_page(rows_b or [], has_next=has_next),
        url_of("C"): myhr_page(rows_c or [], has_next=has_next),
    }


def five_expired_rows(base_tid: int) -> list:
    """5 行 remain==0(已到期段) —— 停翻2. 的最小触发面"""
    return [
        row(base_tid + i, f"OTHER-TORRENT {base_tid + i}", done=DONE_OLD, remain="0天00:00:00", need="0:00:00")
        for i in range(5)
    ]


def counter_adapter(monkeypatch, claims: Dict[str, int]):
    """把 build_adapter 换成「按 claims 表上交计数」的测试 adapter(§5: 覆写 parse_counters 上交合成值)。

    claims 波间可变: 测试直接改字典, 下一波 build_adapter 重建的 adapter 读到新表;
    键缺 = 该档不上交(降级 None)。返回 claims 本体方便波间改写。
    """
    from auto_qb.hr.adapters.nexusphp import NexusPhpMyhrAdapter

    class _CounterNexus(NexusPhpMyhrAdapter):
        def parse_counters(self, html):
            return {lane: v for lane, v in claims.items()}

    monkeypatch.setattr(
        hr_service,
        "build_adapter",
        lambda site, conf: _CounterNexus(
            site,
            hr_page_url=conf.hr_page_url,
            download_path=conf.download_path,
            scopes=FETCH_LANES,
            page_param=conf.page_param,
        ),
    )
    return claims


def _page_with_blank_required_row(tid: int) -> str:
    """表头完好但必填字段(名称/还需做种/剩余)全空的一行 -> S2 零容忍"""
    blank_cells = "".join("<td></td>" for _ in range(8))
    body = f'<tr><td class="rowfollow nowrap" align="center">{tid}</td>{blank_cells}</tr>'
    return myhr_page([]).replace("</tr></tbody></table>", "</tr>" + body + "</tbody></table>", 1)


def _gconf_channel_off():
    from auto_qb.config.models import HrChannelConfig

    return global_conf(channel=HrChannelConfig(enabled=False))


def _history_from_disk(service, site: str = SITE):
    """从磁盘读站点文件取拉取历史(能读到他 == 事件已随站点文件落盘)"""
    data, err = service.store(site).read_unlocked()
    assert err is None
    return data.history


class _TimeoutFetcher:
    """取页 / 取种即抛「等扩展回传超时」: 通道层故障, 不是页面问题(计划 §03.1 的洞口)"""
    def get_text(self, url):
        raise HrChannelTimeout(f"等待浏览器扩展取数超时(180s): {url}")

    def get_bytes(self, url):
        raise HrChannelTimeout(f"等待浏览器扩展取数超时(180s): {url}")


class _Parsed:
    """_stop_condition 消费的最小 parsed 替身(只有 .entries 被读)"""
    def __init__(self, entries):
        self.entries = entries


class _StubAdapter:
    """只提供 download_url 的桩(下载路径不碰站点解析)"""
    @staticmethod
    def download_url(tid):
        return f"https://pt.example.com/download.php?id={tid}"


def _expired(tid: int) -> HrEntry:
    """remain_seconds == 0 的到期行(停翻2. 尾部连击计数用)"""
    return HrEntry(tid=tid, name=f"EXPIRED {tid}", remain_seconds=0)


def _live(tid: int, done_iso: str = "") -> HrEntry:
    """remain 非零的行(不参与停翻2. 的尾部连击)"""
    return HrEntry(tid=tid, name=f"LIVE {tid}", remain_seconds=3600, done_iso=done_iso or None)


def _dl_budget(service, data, *, per_day: int = 100):
    from auto_qb.hr.ratelimit import HrLimits

    return _Budget(data, HrLimits(min_interval=0.0, max_requests_per_day=per_day), service._now, None)


class _StoppedFetcher(FakeFetcher):
    """首页即被叫停(HrChannelStopped): 模拟停止/热重挂期间开波"""
    def get_text(self, url):
        raise HrChannelStopped("正在停止或重挂端点")


class _RecordingCounterAdapter:
    """记录 parse_counters 实参的 adapter 壳(钉「引擎把页面 html 交给 adapter」的接线)"""
    def __init__(self, inner):
        self._inner = inner
        self.counter_htmls = []

    def parse_counters(self, html):
        self.counter_htmls.append(html)
        return {"A": 1}

    def __getattr__(self, name):
        return getattr(self._inner, name)


def _marks_page(rows, *, currentpage: int, maxpage: int, has_next: bool = False) -> str:
    """带 NexusPHP 翻页脚本标记的 HR 页(var currentpage/maxpage)"""
    return myhr_page(
        rows, has_next=has_next
    ) + f"<script>var maxpage={maxpage}; var currentpage={currentpage};</script>"


def _real_adapter(conf=None):
    from auto_qb.hr.adapters import build_adapter

    return build_adapter(SITE, conf or site_conf())


def _site_file_json(service):
    import json

    path = service.store(SITE).path
    return json.loads(path.read_text(encoding="utf-8"))
