"""`torrents_support` 支撑: 从 `test_torrents.py` 拆出的模块级辅助/常量(move-only 搬迁, 未改语义)."""

from dataclasses import MISSING, fields as dc_fields

import pytest

from auto_qb.torrents import REQUIRED_TORRENT_FIELDS, TorrentRecord, TorrentStore, view_dirty, view_field_value

from auto_qb.torrents.compat import _SNAPSHOT_FIELDS

from auto_qb.torrents.view import _VIEW_EXCLUDED_FIELDS

from helpers import FakeClient, FakeTorrent

# 真机 TorrentDictionary 字段样例(qB 5.x, 2026-09-15 字段表定稿依据; 见 docs/record-full-fields-plan.html)
# 全部字段必须能进入 TorrentRecord 快照(声明字段进 slot, 未声明的落 _raw —— 两者都不允许丢弃)
_EXAMPLE_TORRENT_INFO = {
    "added_on": 1786920863,
    "amount_left": 5196343118,
    "auto_tmm": False,
    "availability": 0,
    "category": "",
    "comment": "https://kufirc.com/torrents.php?id=240006",
    "completed": 0,
    "completion_on": -1,
    "connections_count": 0,
    "connections_limit": 30,
    "content_path": "G:\\临时\\[OnlyFans] Marly (mementomarly) Siterip",
    "created_by": "uTorrent/2210",
    "creation_date": 1665579740,
    "dl_limit": 0,
    "dlspeed": 0,
    "download_path": "",
    "downloaded": 0,
    "downloaded_session": 0,
    "eta": 8640000,
    "f_l_piece_prio": False,
    "force_start": False,
    "has_metadata": True,
    "hash": "047b3fad9834f0f2c00f9d4a9189068431e4a191",
    "inactive_seeding_time_limit": -2,
    "infohash_v1": "047b3fad9834f0f2c00f9d4a9189068431e4a191",
    "infohash_v2": "",
    "last_activity": 1786920863,
    "magnet_uri": "magnet:?xt=urn:btih:047b3fad9834f0f2c00f9d4a9189068431e4a191",
    "max_inactive_seeding_time": -1,
    "max_ratio": -1,
    "max_seeding_time": -1,
    "name": "[OnlyFans] Marly (mementomarly) Siterip",
    "num_complete": 0,
    "num_incomplete": 0,
    "num_leechs": 0,
    "num_seeds": 0,
    "piece_size": 4194304,
    "pieces_have": 0,
    "pieces_num": 1239,
    "popularity": 0,
    "priority": 3,
    "private": True,
    "progress": 0,
    "ratio": 0,
    "ratio_limit": -2,
    "root_path": "G:\\临时\\[OnlyFans] Marly (mementomarly) Siterip",
    "save_path": "G:\\临时",
    "seeding_time": 0,
    "seeding_time_limit": -2,
    "seen_complete": -1,
    "seq_dl": False,
    "share_limit_action": "Default",
    "size": 5196343118,
    "state": "stoppedDL",
    "super_seeding": False,
    "tags": "Kufirc",
    "time_active": 23098,
    "total_size": 5196343118,
    "total_wasted": 0,
    "tracker": "http://kufirc.com:7456/announce",
    "trackers_count": 1,
    "up_limit": 0,
    "uploaded": 0,
    "uploaded_session": 0,
    "upspeed": 0,
    "reannounce_in": 0,
}


def _client(files=None):
    client = FakeClient()
    if files is not None:
        client.files = files
    return client


class _StubLink:
    """最小判定桥(替身真实 HrRuntime): 记下入参, 返回给定判定(None = 本模块不适用)"""
    def __init__(self, judged=None):
        self.judged = judged
        self.calls = []

    def judge(
        self,
        site,
        infohashes,
        *,
        anchor=None,
        now=0.0,
    ):
        self.calls.append((site, tuple(infohashes), anchor))
        return self.judged


def _count_trackers(client):
    """包装 torrents_trackers 返回计数函数, FakeClient 不记录该调用"""
    state = {"n": 0}
    orig = client.torrents_trackers

    def counting(h):
        state["n"] += 1
        return orig(h)

    client.torrents_trackers = counting
    return state
