"""test_state_matrix 测试计划: 状态判定矩阵(qB 全部状态 × 分组判定)

qB 状态具有"双重身份"(checkingDL 既是校验又是下载, checkingUP 既是校验又是
做种), 62dbc25 修复暴露状态判定未系统测试的问题。本文件对 qbittorrentapi 的
TorrentState 全部状态做参数化矩阵测试, 锁定每个判定函数的精确语义, 防止
"新增状态/修改枚举属性" 导致静默回归。

2024-12 用户重构: GroupingMixin._is_downloading/_is_uploading/_is_paused 等
手写语义判定已删除(不再有 tor 对象级静态判定), 状态判定全部直接使用
TorrentState 枚举属性(state_enum.is_*); StateCondition spec 直接写枚举属性名
(is_downloading / is_complete&is_uploading 等), 不再有 checking/downloading 等
语义名 -> is_* 属性的映射层(用户注释已删 _ATTRS 映射)。

## 测试计划(每个测试函数一条)
- test_state_enum_has_exactly_22_members: TorrentState 枚举成员数量锁定(qB 当前 22 个, 含 allocating)
- test_state_condition_matches_enum_matrix: StateCondition(is_* 属性名 spec) 判定 == 枚举属性(全状态 × 全语义)
- test_group_has_downloading_matrix: 全部状态 × _group_has_downloading 组内判定(活跃下载 = is_downloading 且非停止且非校验)
- test_state_condition_unknown_semantic: 非法 spec(非枚举属性名) -> AttributeError(快速失败, 防配置笔误静默不匹配)
"""
import os
import tempfile

import pytest

from auto_qb.config import GroupingConfig
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
    """_group_has_downloading 语义: is_downloading 且 非停止(stoppedUP/stoppedDL/pausedUP/pausedDL)
    且 非校验(checkingDL)(活跃下载, 排暂停/校验)"""
    return state.is_downloading and not state.is_stopped and not state.is_checking


# StateCondition spec 直接使用的 TorrentState 枚举判定属性(无手写语义映射层)
_ATTR_NAMES = (
    "is_checking",
    "is_downloading",
    "is_complete",
    "is_uploading",
    "is_errored",
    "is_stopped",
)


def test_state_enum_has_exactly_22_members():
    """TorrentState 枚举成员数量锁定为 22(含 allocating 磁盘分配状态; 新增状态需审视判定语义)"""
    assert len(ALL_STATES) == 22


@pytest.mark.parametrize("state", ALL_STATES, ids=lambda s: s.value)
def test_group_has_downloading_matrix(state):
    """_group_has_downloading: 单成员组是否含活跃下载 == is_downloading 且非停止且非校验"""
    with tempfile.TemporaryDirectory() as td:
        mgr = QbManager("", config=_group_cfg(os.path.join(td, "state.json")), no_lock=True)  # 测试不持锁
        mgr.client = FakeClient()
        seed_store(mgr, [FakeTorrent(hash="H1", state=state.value)])
        assert mgr._group_has_downloading(["H1"]) is _dl_expected(state), f"state={state.value}"


@pytest.mark.parametrize("attr", _ATTR_NAMES)
@pytest.mark.parametrize("state", ALL_STATES, ids=lambda s: s.value)
def test_state_condition_matches_enum_matrix(state, attr):
    """StateCondition(is_* 属性名 spec) 判定 == TorrentState 枚举属性(全状态 × 全属性, 锁定无手写映射漂移)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = QbManager("", config=_group_cfg(os.path.join(td, "state.json")), no_lock=True)  # 测试不持锁
        ctx = make_ctx(mgr, FakeTorrent(state=state.value), FakeClient())
        assert StateCondition(attr).match(ctx) is getattr(state, attr), f"{attr} × {state.value}"


def test_state_condition_unknown_semantic():
    """StateCondition: 非枚举属性名 spec -> AttributeError(配置错误快速失败, 而非静默不匹配)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = QbManager("", config=_group_cfg(os.path.join(td, "state.json")), no_lock=True)  # 测试不持锁
        ctx = make_ctx(mgr, FakeTorrent(state="stalledUP"), FakeClient())
        with pytest.raises(AttributeError):
            StateCondition("bogus").match(ctx)
        with pytest.raises(AttributeError):
            StateCondition("is_complete&bogus").match(ctx)
