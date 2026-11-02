"""`grouping_support` 支撑: 从 `test_grouping.py` 拆出的模块级辅助/常量(move-only 搬迁, 未改语义)."""

import logging

import os

import tempfile

from contextlib import contextmanager

from types import SimpleNamespace

from unittest import mock

import pytest

from helpers import FakeClient, FakeTorrent, _fake_file, capture_logs, grouping_cfg, make_manager, seed_store


def _non_tag_calls(client):
    """排除 maintenance 的 add_tags 噪音(tracker 标签), 只看分组相关动作"""
    return [c for c in client.calls if c[0] != "add_tags"]


def _scan_scenario(state_file):
    """同组两成员(H1/H2)均 stalledUP 的场景: 首轮归组 + 建立状态快照, 调用记录已清空"""
    client = FakeClient()
    mgr = make_manager(
        state_file, bare=True, grouping=grouping_cfg(), client=client
    )  # property setter 会把 api 重绑到该 client(生产路径同构)

    t1 = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=r"R:\Downloads")
    t2 = FakeTorrent(hash="H2", name="T2", state="stalledUP", save_path=r"R:\Downloads")
    client.torrents["H1"] = t1
    client.torrents["H2"] = t2
    client.files_map["H1"] = [_fake_file("movie.mkv", 100)]
    client.files_map["H2"] = [_fake_file("movie.mkv", 100)]

    mgr._refresh_torrents()  # 首轮: 归组 + 建立状态快照(上传中, 不触发)
    assert _non_tag_calls(client) == [], f"首轮不应触发: {client.calls}"
    client.calls.clear()
    return mgr, client, t1, t2


def _grp_env(state_file, **grouping_kw):
    """直驱 grouping 模块方法的白盒环境: QbManager + FakeClient, 返回 (mgr, grp, client)"""
    client = FakeClient()
    mgr = make_manager(state_file, bare=True, grouping=grouping_cfg(**grouping_kw), client=client)
    return mgr, mgr.host.get("grouping"), client


def _seed_group(store, key, hashes, file_map=None, in_by_hash=None):
    """直填分组结构(in_by_hash: 只把列出的 hash 灌入 by_hash, 缺省全部)"""
    store.groups[key] = list(hashes)
    for h in hashes:
        store.member_to_key[h] = key
    store.group_sizes.setdefault(key, {})
    for h in hashes:
        store.group_sizes[key][h] = file_map or {"movie.mkv": 100}
    for h in (in_by_hash if in_by_hash is not None else hashes):
        if h not in store.by_hash:
            store.by_hash[h] = FakeTorrent(hash=h, state="stalledUP", save_path=key[0])


class _CrossWarnCapture(logging.Handler):
    """直挂 grouping 模块 logger 的 WARNING 采集器

    QbManager 构造链 setup_logging 清空 root handlers, caplog.text 恒空
    (pitfalls/testing/log-capture); 对齐本文件过渡态用例的 _Capture 直挂先例。
    """
    def __init__(self):
        super().__init__(level=logging.WARNING)
        self.messages = []

    def emit(self, record):
        self.messages.append(record.getMessage())


@contextmanager
def _grab_cross_warnings():
    cap = _CrossWarnCapture()
    log = logging.getLogger("auto_qb.core.modules.grouping_mod")
    log.addHandler(cap)
    try:
        yield cap
    finally:
        log.removeHandler(cap)


def _seed_cross_pair(store, sp_a, files_a, sp_b, files_b, state_a="stalledUP", state_b="downloading", tags_a=""):
    """跨组检测夹具: 两组各 1 成员(save_path/文件清单可异同), 默认 A 完成侧 + B 下载中, 返回组对 key

    直注 store.groups / group_sizes / member_to_key / by_hash(姿势对齐 _seed_group);
    文件字典必须是 {"ep01.mkv": 100} 形状的真实清单 —— 跨组检测的展开源就是它, 空字典 = 无文件 = 检不出。
    """
    key_a = (sp_a, tuple(sorted(files_a)))
    key_b = (sp_b, tuple(sorted(files_b)))
    _seed_group(store, key_a, ["HA"], file_map=files_a, in_by_hash=[])
    _seed_group(store, key_b, ["HB"], file_map=files_b, in_by_hash=[])
    store.by_hash["HA"] = FakeTorrent(hash="HA", name="TA", state=state_a, save_path=sp_a, amount_left=100, tags=tags_a)
    store.by_hash["HB"] = FakeTorrent(hash="HB", name="TB", state=state_b, save_path=sp_b, amount_left=100)
    return key_a, key_b


_OVERLAP_A = {"ep01.mkv": 100, "ep02.mkv": 200}

_OVERLAP_B = {"ep02.mkv": 200, "ep03.mkv": 300}


def _record_stop_scope(client):
    """包装 client.torrents_stop 记录每次调用的 torrent_hashes 实参(高位真洞 None="all" 全库面的判定源)"""
    scope = []
    orig = client.torrents_stop

    def rec(torrent_hashes=None, **kw):
        scope.append(torrent_hashes)
        return orig(torrent_hashes=torrent_hashes, **kw)

    client.torrents_stop = rec
    return scope
