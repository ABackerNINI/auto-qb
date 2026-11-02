"""`speed_curve_support` 支撑: 从 `test_speed_curve.py` 拆出的模块级辅助/常量(move-only 搬迁, 未改语义)."""

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

GIB = 1024**3

MIB = 1024**2

# 用户样例档位表(阈值 GiB, 限速 MiB/s)
FULL_UPLOAD = [(10, 6), (20, 5), (30, 4), (50, 2), (100, 1), (1000, 0.5)]

FULL_DOWNLOAD = [(30, 11), (50, 10), (100, 5), (200, 2), (1000, 1)]


# ---------- 模拟 qB 5.0 transfer 端点(全局速度限制; 单位 bytes/s, 0 = 不限速) ----------
class _FakeTransfer:
    """模拟 qbittorrent-api 的 transfer 命名空间(全局限速)

    与真实 qB 5.0 Web API 一致: transfer_upload_limit()/transfer_download_limit()
    返回当前限速(bytes/s, 0 = 不限速); transfer_set_upload_limit(limit) 等写入
    bytes/s(旧版 app/preferences 的 upload_limit/-1 语义在 5.0 已失效)。
    """
    def __init__(self):
        self.limits = {"upload_limit": 0, "download_limit": 0}  # bytes/s
        self.calls = []

    def transfer_upload_limit(self):
        return self.limits["upload_limit"]

    def transfer_download_limit(self):
        return self.limits["download_limit"]

    def transfer_set_upload_limit(self, limit=None):
        self.calls.append(("set_upload_limit", int(limit)))
        self.limits["upload_limit"] = int(limit)

    def transfer_set_download_limit(self, limit=None):
        self.calls.append(("set_download_limit", int(limit)))
        self.limits["download_limit"] = int(limit)


def _fake_client():
    client = FakeClient()
    transfer = _FakeTransfer()
    client.transfer = transfer  # 动态附加(helpers.py 只读); 与真实 client.transfer 同语义
    client.transfer_upload_limit = transfer.transfer_upload_limit
    client.transfer_download_limit = transfer.transfer_download_limit
    client.transfer_set_upload_limit = transfer.transfer_set_upload_limit
    client.transfer_set_download_limit = transfer.transfer_set_download_limit
    return client


# ---------- 构造辅助 ----------
def _points(pairs):
    """[(阈值GiB, 限速MiB/s)] -> CurvePoint 列表(与 parse_fsize/parse_speed 换算一致)"""
    return [CurvePoint(threshold_bytes=int(g * GIB), speed_bytes_per_s=int(v * MIB)) for g, v in pairs]


def _pc(period: str, up=None, down=None) -> PeriodCurve:
    return PeriodCurve(period=period, upload_points=up, download_points=down)


class _GslcBundle:
    """测试组合: 曲线段配置 + 顶层数据源 dat 路径(S15 后数据源独立于曲线段, 直接注入 FakeConfig 用)"""
    def __init__(self, dat_path: str, curve: GlobalSpeedLimitCurve):
        self.dat_path = dat_path
        self.curve = curve


def _gslc(dat_path, *period_curves, interval=None) -> _GslcBundle:
    return _GslcBundle(dat_path, GlobalSpeedLimitCurve(curves=list(period_curves), interval=interval))


def _run_curve(mgr, dry_run: bool = False) -> bool:
    """直接执行全局限速曲线 handler(等价到期任务执行)"""
    task = Task(
        "internal", "speed_limit_curve", interval=60, handler=mgr.host.get("speed_curve").handle_speed_limit_curve
    )
    return mgr.host.get("speed_curve").handle_speed_limit_curve(task, dry_run=dry_run)


def _make_mgr(tmp_path, gslc: _GslcBundle, with_app: bool = True):
    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.config.global_speed_limit_curve = gslc.curve
    # 取数路径来自顶层 traffic_source(S15): 直接注入 FakeConfig, 等价于 load_config 后的形态
    mgr.config.traffic_source.traffic_monitor.dat_path = gslc.dat_path
    client = _fake_client() if with_app else FakeClient()
    mgr.client = client
    return mgr, client
