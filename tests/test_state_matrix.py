"""test_state_matrix 测试计划: 状态判定矩阵(qB 全部状态 × 分组判定)

qB 状态具有"双重身份"(checkingDL 既是校验又是下载, checkingUP 既是校验又是
做种), 62dbc25 修复暴露状态判定未系统测试的问题。本文件对 qbittorrentapi 的
TorrentState 全部状态做参数化矩阵测试, 锁定每个判定函数的精确语义, 防止
"新增状态/修改枚举属性" 导致静默回归。

## 测试计划(每个测试函数一条)
- test_state_enum_has_exactly_22_members: TorrentState 枚举成员数量锁定(qB 当前 22 个, 含 allocating)
- test_is_downloading_matrix: 全部状态 × _is_downloading(锁定 62dbc25: 排除校验/暂停)
- test_is_uploading_matrix: 全部状态 × _is_uploading(checkingUP 校验中也算做种)
- test_is_paused_matrix: 全部状态 × _is_paused(stoppedUP/stoppedDL 新版暂停)
- test_group_has_downloading_state_matrix: 全部状态 × _group_has_downloading 组内判定
- test_state_map_consistent_with_enum: _STATE_MAP 状态分组与枚举属性一致性
"""
import os
import tempfile

import pytest

from auto_qb.config import GroupingConfig
from auto_qb.mixins.grouping import GroupingMixin
from auto_qb.qbmanager import QbManager
from auto_qb.rules.conditions import _STATE_MAP
from helpers import FakeClient, FakeConfig, FakeTorrent, seed_store

try:
    from qbittorrentapi import TorrentState

    ALL_STATES = list(TorrentState)
except ImportError:  # pragma: no cover
    TorrentState = None
    ALL_STATES = []

pytestmark = pytest.mark.skipif(TorrentState is None, reason="qbittorrentapi 未安装")


def _group_cfg(state_file):
    cfg = FakeConfig()
    cfg.state_file = state_file
    cfg.grouping = GroupingConfig(enabled=True, missing_tag="MISSING")
    return cfg


def _dl_expected(state):
    """_is_downloading 语义: is_downloading 且 非校验 且 非暂停(62dbc25)"""
    return state.is_downloading and not state.is_checking and not state.is_paused


def test_state_enum_has_exactly_22_members():
    """TorrentState 枚举成员数量锁定为 22(含 allocating 磁盘分配状态; 新增状态需审视判定语义)"""
    assert len(ALL_STATES) == 22


@pytest.mark.parametrize("state", ALL_STATES, ids=lambda s: s.value)
def test_is_downloading_matrix(state):
    """_is_downloading: 全部状态判定 == is_downloading 且非 checking 且非 paused"""
    tor = FakeTorrent(state=state.value)
    assert GroupingMixin._is_downloading(tor) is _dl_expected(state), f"state={state.value}"


@pytest.mark.parametrize("state", ALL_STATES, ids=lambda s: s.value)
def test_is_uploading_matrix(state):
    """_is_uploading: 全部状态判定 == is_uploading(checkingUP 校验中仍算做种)"""
    tor = FakeTorrent(state=state.value)
    assert GroupingMixin._is_uploading(tor) is state.is_uploading, f"state={state.value}"


@pytest.mark.parametrize("state", ALL_STATES, ids=lambda s: s.value)
def test_is_paused_matrix(state):
    """_is_paused: 全部状态判定 == is_paused(pausedDL/stoppedDL 下载暂停也算暂停)"""
    tor = FakeTorrent(state=state.value)
    assert GroupingMixin._is_paused(tor) is state.is_paused, f"state={state.value}"


@pytest.mark.parametrize("state", ALL_STATES, ids=lambda s: s.value)
def test_group_has_downloading_state_matrix(state):
    """_group_has_downloading: 单成员组是否含活跃下载 == _is_downloading(state)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = QbManager("", config=_group_cfg(os.path.join(td, "state.json")))
        mgr.client = FakeClient()
        seed_store(mgr, [FakeTorrent(hash="H1", state=state.value)])
        assert mgr._group_has_downloading(["H1"]) is _dl_expected(state), f"state={state.value}"


def test_state_map_consistent_with_enum():
    """_STATE_MAP 状态分组与 TorrentState 枚举属性一致(锁定语义不漂移)"""
    def enum_set(pred):
        return {s for s in ALL_STATES if pred(s)}

    def spec_set(names):
        return {TorrentState(n) for n in names}

    checking = spec_set(_STATE_MAP["checking"])
    paused = spec_set(_STATE_MAP["stopped"])
    downloading = spec_set(_STATE_MAP["downloading"])
    complete = spec_set(_STATE_MAP["complete"])
    uploading = spec_set(_STATE_MAP["uploading"])

    # 语义恒等式: checking 分组 == is_checking; stopped 分组 == is_paused
    assert checking == enum_set(lambda s: s.is_checking)
    assert paused == enum_set(lambda s: s.is_paused)
    # downloading 是 is_downloading 子集, 且与校验/暂停无交集(62dbc25 语义)
    assert downloading <= enum_set(lambda s: s.is_downloading)
    assert downloading & checking == set()
    assert downloading & paused == set()
    # complete/uploading 是 is_complete/is_uploading 子集
    assert complete <= enum_set(lambda s: s.is_complete)
    assert uploading <= enum_set(lambda s: s.is_uploading)
    # errored 分组全部是合法状态
    for name in _STATE_MAP["errored"]:
        assert TorrentState(name) is not None
