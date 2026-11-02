"""test_speed_curve_curve 测试计划: 全局限速曲线(Traffic Monitor 接入 qB 全局速度限制)

## 测试计划(每个测试函数一条)
- test_curve_speed_plan_b: 全程分档覆盖(首档覆盖低端, 边界, 末档延续)
- test_curve_speed_last_tier_clamp_matrix: 末档 clamp 边界矩阵(各档内部不变/恰好压线/超末档取末档速度/末档 0 显式放开)
- test_speed_curve_beyond_last_tier_clamps_both_directions: 双向累计超末档 -> 写末档速度值而非解除限速(任务集成)
- test_merge_direction_after_clamp_takes_strictest: 多曲线各自超末档 -> clamp 到末档速度后合并, 取最严仍正确(SPD-01/D5)
- test_merge_direction_and_bytes_to_kib: 取最小非零(全0=0/空=None/1B/s 仍算非零) / KiB 半值进位
- test_curve_state_day_keys_pruned: 守阵(26-10-06-0028 A-03)——speed_limit_curve 日键保 N 天, 保留期外旧日键写入时顺带淘汰
"""

import copy

import io

import logging

import os

from datetime import date, timedelta

import pytest

import yaml

from auto_qb.core import curves

from auto_qb.config import CurvePoint, GlobalSpeedLimitCurve, PeriodCurve, load_config

from auto_qb.config import ConfigError

from auto_qb.core.modules.speed_curve_mod import (
    _CURVE_STATE_KEEP_DAYS, _MANUAL_REMIND_GAP, _cn_number, _fmt_bytes, _fmt_global_limit, _period_label
)

from auto_qb.core.taskqueue import Task

from auto_qb.core.traffic_source import paths as traffic_paths

from helpers import FakeClient, capture_logs, make_manager, write_dat

from speed_curve_support import (
    FULL_DOWNLOAD,
    FULL_UPLOAD,
    GIB,
    MIB,
    _FakeTransfer,
    _GslcBundle,
    _fake_client,
    _gslc,
    _make_mgr,
    _pc,
    _points,
    _run_curve,
)


def test_curve_speed_plan_b():
    """全程分档覆盖: 首档覆盖低端 / 边界落在"达到阈值"档 / 末档延续"""
    pts = _points(FULL_UPLOAD)

    def kib(gib):
        return curves.bytes_to_kib(curves.curve_speed(int(gib * GIB), pts))

    # X < 10GiB -> 首档 6MiB/s(低于指定值也限速); X == 10GiB -> 达到阈值, 用下一档区间速度 5
    assert kib(0) == 6 * 1024
    assert kib(5) == 6 * 1024
    assert kib(10) == 5 * 1024
    assert kib(15) == 5 * 1024
    assert kib(20) == 4 * 1024
    assert kib(25) == 4 * 1024
    assert kib(30) == 2 * 1024
    assert kib(49) == 2 * 1024
    assert kib(50) == 1 * 1024
    assert kib(60) == 1 * 1024  # 60GiB -> 1MiB/s(用户确认)
    assert kib(100) == 512  # 达到 100GiB -> 末档前区间 0.5MiB/s
    assert kib(150) == 512
    assert kib(2000) == 512  # 超末档 -> 末档延续
    # 单点档位 + 0 档: 低于阈值不限速, 达到阈值后仍为末档 0(显式放开)
    zero_pts = _points([(10, 0)])
    assert curves.curve_speed(5 * GIB, zero_pts) == 0
    assert curves.curve_speed(50 * GIB, zero_pts) == 0


def test_curve_speed_last_tier_clamp_matrix():
    """末档 clamp 边界矩阵(D5 定案): 各档内部不变 / 恰好压线 / 超末档 clamp 到末档速度 / 末档 0 仍为不限速

    累计流量超出末档边界不是"解除限速", 而是一直沿用末档速度; 末档速度为 0 是用户
    显式配置的放开档, 超出后同样延续该 0(语义为显式不限速, 非功能性行为)。
    """
    pts = _points(FULL_UPLOAD)  # 末档 (1000GiB, 0.5MiB/s)

    def kib(gib):
        return curves.bytes_to_kib(curves.curve_speed(int(gib * GIB), pts))

    # (阈值 GiB, 阈值前区间档速 KiB/s, 恰好压线后档速 KiB/s); 首档覆盖低端, 末档压线即末档自身
    tiers = [(10, 6144, 5120), (20, 5120, 4096), (30, 4096, 2048), (50, 2048, 1024), (100, 1024, 512), (1000, 512, 512)]
    for t, before, after in tiers:
        assert kib(t - 1) == before, f"X={t - 1}GiB 应为本档 {before}KiB/s"
        assert kib(t) == after, f"X={t}GiB 恰好压线应为 {after}KiB/s"
    # 超末档: 一律 clamp 到末档 0.5MiB/s(512KiB/s), 不解除限速
    for gib in (1001, 1002, 2048, 102400):
        assert kib(gib) == 512, f"X={gib}GiB 超末档应 clamp 到末档 512KiB/s"
    # 单点曲线(首档即末档): 低端覆盖 / 压线 / 超末档同值
    single = _points([(30, 2)])
    for gib in (0, 29, 30, 31, 10000):
        assert curves.curve_speed(int(gib * GIB), single) == 2 * MIB
    # 末档显式配 0(用户显式放开): 压线与超末档延续该 0 = 不限速
    zero_tail = _points([(10, 6), (50, 0)])
    assert curves.curve_speed(int(9 * GIB), zero_tail) == 6 * MIB
    assert curves.curve_speed(int(50 * GIB), zero_tail) == 0  # 恰好压线末档
    assert curves.curve_speed(int(51 * GIB), zero_tail) == 0
    assert curves.curve_speed(int(10240 * GIB), zero_tail) == 0


def test_speed_curve_beyond_last_tier_clamps_both_directions(tmp_path):
    """超末档(D5): 上/下载累计流量超出末档边界 -> 写入末档速度值(clamp), 而非解除限速(写 0)"""
    today = date.today()
    dat = write_dat(tmp_path, [(today, 1200 * GIB, 1200 * GIB)])  # 双向均超各自末档(1000GiB)
    gslc = _gslc(dat, _pc("day", up=_points(FULL_UPLOAD), down=_points(FULL_DOWNLOAD)))
    mgr, client = _make_mgr(tmp_path, gslc)

    assert _run_curve(mgr)
    # 上传超末档(1000GiB, 0.5MiB/s) -> 512KiB/s; 下载超末档(1000GiB, 1MiB/s) -> 1024KiB/s
    assert client.transfer.calls == [("set_upload_limit", 512 * 1024), ("set_download_limit", 1024 * 1024)]
    assert client.transfer.limits["upload_limit"] == 512 * 1024
    assert client.transfer.limits["download_limit"] == 1024 * 1024
    assert mgr.state["speed_limit_curve"][today.isoformat()] == {
        "upload_kib": 512,
        "download_kib": 1024,
        "dry_run": False,
    }


def test_merge_direction_after_clamp_takes_strictest():
    """多曲线各自超末档 -> 各自 clamp 到末档速度后, merge_direction 按现逻辑取最严(最小非零)仍正确(SPD-01/D5)"""
    clamp_a = [CurvePoint(threshold_bytes=1000 * GIB, speed_bytes_per_s=3000)]
    clamp_b = [CurvePoint(threshold_bytes=1000 * GIB, speed_bytes_per_s=5000)]
    speeds = [curves.curve_speed(4000 * GIB, clamp_a), curves.curve_speed(4000 * GIB, clamp_b)]
    assert speeds == [3000, 5000]  # 双双超末档 -> 各自 clamp 到各自末档速度
    assert curves.merge_direction(speeds) == 3000  # 取最严(最小非零), 末档 clamp 值不干扰合并


def test_merge_direction_and_bytes_to_kib():
    """合并: 取最小非零(最严); 全 0 -> 0; 空 -> None; KiB 半值进位"""
    assert curves.merge_direction([6 * MIB, 2 * MIB, 4 * MIB]) == 2 * MIB
    assert curves.merge_direction([0, 0]) == 0
    assert curves.merge_direction([0, 1]) == 1  # 1 B/s 是合法非零最严, 不得被当 0(merge_4)
    assert curves.merge_direction([]) is None
    assert curves.merge_direction([0, 5 * MIB]) == 5 * MIB  # 0(不限速档)不拉低最严
    assert curves.bytes_to_kib(0) == 0
    assert curves.bytes_to_kib(6 * MIB) == 6144
    assert curves.bytes_to_kib(int(0.5 * MIB)) == 512
    assert curves.bytes_to_kib(int(0.25 * MIB)) == 256  # 半值进位


def test_curve_state_day_keys_pruned(tmp_path):
    """守阵(26-10-06-0028 A-03): speed_limit_curve 日键保 _CURVE_STATE_KEEP_DAYS 天

    修复前每天新增一日键且从不清 -> state 缓慢无界增长; 修复后写入时顺带淘汰保留期外
    的旧日键(该键仅供调试, 无正确性消费方), 保留期内与当日键不受影响。
    """
    mgr, _ = _make_mgr(tmp_path, _gslc("x.dat"), with_app=False)
    today = date.today()
    expired = (today - timedelta(days=_CURVE_STATE_KEEP_DAYS + 1)).isoformat()
    recent = (today - timedelta(days=1)).isoformat()
    mgr.state["speed_limit_curve"] = {expired: {"upload_kib": None}, recent: {"upload_kib": None}}
    mgr.host.get("speed_curve")._record_curve_state(today, None, None, False)
    keys = set(mgr.state["speed_limit_curve"])
    assert expired not in keys, "保留期外旧日键被淘汰(键面有界)"
    assert recent in keys and today.isoformat() in keys, "保留期内与当日键不受影响"
