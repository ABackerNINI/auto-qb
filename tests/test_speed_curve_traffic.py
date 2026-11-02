"""test_speed_curve_traffic 测试计划: 全局限速曲线(Traffic Monitor 接入 qB 全局速度限制)

## 测试计划(每个测试函数一条)
- test_qbapi_global_speed_limit_normalization: qbapi KiB<->bytes/s 换算与读写
- test_traffic_view_dry_run_has_target_without_actual
- test_traffic_view_manual_reason_on_odd_kib
- test_traffic_view_ok_reports_limits
- test_traffic_view_stale_when_dat_missing_or_empty
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


def test_qbapi_global_speed_limit_normalization(tmp_path):
    """QbApi Facade: 全局限速走 qB 5.0 transfer 端点(bytes/s, 0=不限); 对外 KiB<->bytes/s 换算 """
    mgr, client = _make_mgr(tmp_path, _gslc("x.dat", _pc("day", up=_points(FULL_UPLOAD))))
    api = mgr.api
    assert api.get_global_speed_limits() == {"upload_limit": 0, "download_limit": 0}  # 0 归一 0

    api.set_global_speed_limits(upload_kib=512)  # 0.5MiB/s = 512KiB/s
    assert client.transfer.limits["upload_limit"] == 512 * 1024  # bytes/s
    api.set_global_speed_limits(upload_kib=0)  # 不限速 -> 0
    assert client.transfer.limits["upload_limit"] == 0
    assert api.get_global_speed_limits() == {"upload_limit": 0, "download_limit": 0}

    api.set_global_speed_limits(upload_kib=6144, download_kib=2048)
    assert client.transfer.limits["upload_limit"] == 6144 * 1024
    assert client.transfer.limits["download_limit"] == 2048 * 1024
    assert api.get_global_speed_limits() == {"upload_limit": 6144, "download_limit": 2048}


def test_traffic_view_ok_reports_limits(tmp_path):
    """正常路径: 曲线只写 limit 段 —— 命中/实际限速(KiB/s)一致, 来源段一字未变"""
    today = date.today()
    dat = write_dat(tmp_path, [(today, 15 * GIB, 5 * GIB)])
    gslc = _gslc(dat, _pc("day", up=_points(FULL_UPLOAD), down=_points(FULL_DOWNLOAD)))
    mgr, client = _make_mgr(tmp_path, gslc)
    # 来源侧先发一次(历史上这两段是同一次发布; 解耦后是两个模块各管一段)
    assert mgr.host.get("traffic_snapshot").refresh() is True
    source_before = {k: copy.deepcopy(mgr.web.traffic_view[k]) for k in ("source", "periods", "history")}

    assert _run_curve(mgr)
    tv = mgr.web.traffic_view
    assert tv["state"] == "ok"
    assert tv["date"] == today.isoformat()
    # periods 由来源模块固定发布(day + month, 单位字节); 曲线本轮不再碰它
    assert [(p["period"], p["up"], p["down"])
            for p in tv["periods"]] == [("day", 15 * GIB, 5 * GIB), ("month", 15 * GIB, 5 * GIB)]
    # 命中: 15GiB -> 5MiB/s = 5120KiB/s; 5GiB -> 11MiB/s = 11264KiB/s
    assert tv["limit"]["target"] == {"up": 5120, "down": 11264}
    # 写入成功后回读 -> 实际 == 目标(前端此时只显示一个值)
    assert tv["limit"]["actual"] == {"up": 5120, "down": 11264}
    assert tv["limit"]["reasons"] == []
    assert tv["limit"]["state"] == "ok"
    assert {k: tv[k] for k in ("source", "periods", "history")} == source_before, "曲线一轮不得改来源段(A4)"


def test_traffic_view_manual_reason_on_odd_kib(tmp_path):
    """手动保护(奇数 KiB)写入 reasons(含方向与中文原因) -> 前端标锁图标并显示"命中/实际"两值"""
    today = date.today()
    dat = write_dat(tmp_path, [(today, 5 * GIB, 5 * GIB)])
    gslc = _gslc(dat, _pc("day", up=_points(FULL_UPLOAD), down=_points(FULL_DOWNLOAD)))
    mgr, client = _make_mgr(tmp_path, gslc)
    client.transfer.limits["upload_limit"] = 2001 * 1024  # 用户手动 2001KiB/s(奇数)
    client.transfer.limits["download_limit"] = 10265 * 1024  # 用户手动 10265KiB/s(奇数, 用户实报值)

    assert _run_curve(mgr)
    tv = mgr.web.traffic_view
    assert tv["limit"]["target"] == {"up": 6144, "down": 11264}  # 5GiB -> 首档 6MiB/s / 11MiB/s
    # 未被覆盖, 仍是手动值 -> 前端显示"命中/实际"两者不一致
    assert tv["limit"]["actual"] == {"up": 2001, "down": 10265}
    # 完整键面 pin: 前端锁图标与文案直接消费 dir/code/text 三键, 丢键、错方向、改文案都让 UI 静默失真
    assert tv["limit"]["reasons"] == [
        {
            "dir": "up",
            "code": "manual",
            "text": "上传限速 2001KiB/s 为奇数(疑似手动设置), 本轮不覆盖"
        },
        {
            "dir": "down",
            "code": "manual",
            "text": "下载限速 10265KiB/s 为奇数(疑似手动设置), 本轮不覆盖"
        },
    ]


def test_traffic_view_dry_run_has_target_without_actual(tmp_path):
    """dry_run: 只有命中目标, 不读不写 qB -> actual 为 None"""
    today = date.today()
    dat = write_dat(tmp_path, [(today, 15 * GIB, 0)])
    gslc = _gslc(dat, _pc("day", up=_points(FULL_UPLOAD)))
    mgr, client = _make_mgr(tmp_path, gslc)

    assert _run_curve(mgr, dry_run=True)
    tv = mgr.web.traffic_view
    assert tv["state"] == "dry_run"
    assert tv["limit"]["target"] == {"up": 5120, "down": None}
    assert tv["limit"]["actual"] == {"up": None, "down": None}
    assert client.transfer.calls == []  # 确实未读未写


def test_traffic_view_stale_when_dat_missing_or_empty(tmp_path):
    """数据源缺失/无有效行 -> limit 段落 stale + 原因码(本轮不动限速, 目标归 None)"""
    gslc = _gslc(str(tmp_path / "not-exist.dat"), _pc("day", up=_points(FULL_UPLOAD)))
    mgr, client = _make_mgr(tmp_path, gslc)

    assert _run_curve(mgr) is True
    tv = mgr.web.traffic_view
    assert tv["state"] == "stale"  # 曲线侧先判定也可派生 stale(与今日同格)
    assert tv["limit"]["state"] == "stale"
    assert tv["limit"]["target"] == {"up": None, "down": None}
    r0 = tv["limit"]["reasons"][0]
    assert set(r0) == {"dir", "code", "text"}, f"reasons 键面必须是 dir/code/text 三键: {r0}"
    assert r0["dir"] == "" and r0["code"] == "dat_missing"
    assert r0["text"].startswith("流量数据读取失败: "), f"前端文案前缀必须点明读取失败: {r0['text']}"

    # 文件存在但无有效记录: 同样 stale, 原因码与文案均确定
    bad = tmp_path / "bad.dat"
    bad.write_text('lines: "2"\nnot-a-date\n', encoding="utf-8")
    _b = _gslc(str(bad), _pc("day", up=_points(FULL_UPLOAD)))
    mgr.config.global_speed_limit_curve = _b.curve
    mgr.config.traffic_source.traffic_monitor.dat_path = _b.dat_path
    assert _run_curve(mgr) is True
    assert mgr.web.traffic_view["state"] == "stale"
    assert mgr.web.traffic_view["limit"]["reasons"] == [{"dir": "", "code": "dat_empty", "text": "流量数据无有效记录"}]
