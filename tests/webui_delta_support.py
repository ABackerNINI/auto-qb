"""`webui_delta_support` 支撑: 从 `test_webui_delta.py` 拆出的模块级辅助/常量(move-only 搬迁, 未改语义)."""

import inspect

import json

import time

from collections import deque

from types import SimpleNamespace

from auto_qb.core import tvshows

from auto_qb.core.qbapi import QbApi

from auto_qb.infra.utils import encode_group_key

from auto_qb.webui import WebUIRuntime

from auto_qb.infra.clock import SYSTEM_CLOCK
from auto_qb.webui.views import WebviewMixin

from helpers import FakeTorrent, FakeTracker

from webui_helpers import make_store


class _ViewHost(WebviewMixin):
    """views 构建器**真跑**的最小宿主: 纯读 store/web(构建器是纯读, 见 WebviewMixin 模块头),
    让 cross 键集的构建期回传(note_cross_keys)走真实 _build_group_view 接线"""
    def __init__(self, store):
        self.store = store
        self.web = None  # _delta_runtime 里回填
        self.client = None
        self._clock = SYSTEM_CLOCK  # refresh_tracker_health 的取时点(views 走宿主 _clock, D8)

    def wake(self):  # _build_shows_view 的 post_command 路径兜底(本文件用例不会触发)
        pass


def _delta_runtime(store) -> WebUIRuntime:
    host = _ViewHost(store)
    rt = WebUIRuntime(host)
    host.web = rt
    rt.touch()  # Web 活跃: 门控放行(is_active 依赖 last_seen 心跳)
    return rt


def _publish(rt) -> dict:
    """驱动一轮 flush 并落代(清 pending_ver 模拟客户端取走上一版), 回本代条目"""
    rt.pending_ver = None
    rt.flush_views()
    return rt._delta_timeline[-1]


def _beat(store, hash_, **fields):
    """真机节拍的一拍: 改 qB 侧种子字段 -> 增量 sync 一轮(范式同 test_webui_delta_mirror)"""
    tor = store.client.torrents[hash_]
    for k, v in fields.items():
        setattr(tor, k, v)
    return store.apply_sync(QbApi(store.client, store))


_S8_NAME = "Show.{}.S01E01.720p.x264-GRP"  # 与 webui_helpers.make_store 的装库命名同款


def _s8_baseline(*hashes) -> tuple:
    """装库 + 基线代发布(空键集 -> 全量路径): 映射随首个全量代回填, 回 (store, runtime, 键表)"""
    store = make_store(*hashes)
    rt = _delta_runtime(store)
    rt.mark_dirty()
    _publish(rt)
    keys = {h: tvshows.parse_release(_S8_NAME.format(h)).key for h in hashes}
    assert rt._show_member_keys == keys  # 前置: 基线代全量路径已回填映射
    return store, rt, keys
