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
- test_state_condition_matches_enum_matrix: StateCondition(语义) 判定 == 枚举属性(全状态 × 全语义)
- test_state_condition_unknown_semantic: 未识别语义名 -> 恒不匹配
"""
import os
import tempfile

import pytest

from auto_qb.config import GroupingConfig
from auto_qb.mixins.grouping import GroupingMixin
from auto_qb.qbmanager import QbManager
from auto_qb.rules.conditions import StateCondition
from helpers import FakeClient, FakeConfig, FakeTorrent, make_ctx, seed_store

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


# 语义状态 -> TorrentState 枚举判定属性(StateCondition 接线依据)
_SEMANTIC_ATTRS = {
    "checking": "is_checking",
    "downloading": "is_downloading",
    "complete": "is_complete",
    "uploading": "is_uploading",
    "errored": "is_errored",
    "stopped": "is_stopped",
}


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


@pytest.mark.parametrize("semantic,attr", sorted(_SEMANTIC_ATTRS.items()))
@pytest.mark.parametrize("state", ALL_STATES, ids=lambda s: s.value)
def test_state_condition_matches_enum_matrix(state, semantic, attr):
    """StateCondition(语义) 判定 == TorrentState 枚举属性(全状态 × 全语义, 锁定无手写映射漂移)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = QbManager("", config=_group_cfg(os.path.join(td, "state.json")))
        ctx = make_ctx(mgr, FakeTorrent(state=state.value), FakeClient())
        assert StateCondition(semantic).match(ctx) is getattr(state, attr), f"{semantic} × {state.value}"


def test_state_condition_unknown_semantic():
    """StateCondition: 未识别语义名 -> 恒不匹配(防御配置笔误)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = QbManager("", config=_group_cfg(os.path.join(td, "state.json")))
        ctx = make_ctx(mgr, FakeTorrent(state="stalledUP"), FakeClient())
        assert StateCondition("bogus").match(ctx) is False
        assert StateCondition("complete&bogus").match(ctx) is False
