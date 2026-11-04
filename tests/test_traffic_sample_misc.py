"""test_traffic_sample_misc 测试计划: qB 口径流量采样器(plan 26-10-03-0946 方案C P1 采样器核心 + §06 配置键
+ plan 26-10-04-1957 S2a 写侧/S2b 聚合与恢复 + plan 26-10-05-2200 v4 换代 B2 写侧状态机与结算)

## 测试计划(每个测试函数一条)
- test_disabled_at_runtime_handler_noop: 运行期关闭 -> 采样体短路不采样不动内存(队列无关)

聚合分层与恢复(plan 26-10-04-1957 S2b §04):

启动恢复按需读集(plan 26-10-12-2010, 读集下界 now - rollup_window -> agg 水位所在日):

v4 定约用例(plan 26-10-05-2200 §04 表 ③⑤⑥⑦, B2 落地):

时钟/落盘纪律: 需要确定时刻的用例经 monkeypatch 把模块 SYSTEM_CLOCK 换成统一假钟(tests/clock.py FakeClock)逐轮推进; flush 时点
除专项驱动用例外用 mod._flush_all_series() 直调(绕开驱动计时, 驱动时序由专项用例钉住)。

形态 D 封口末端锚点(plan 26-10-16-1509 §04, z 行扩列; 五条封口路径):

P1-T1.2 守卫与容错簇(计划 26-10-20-2101, 覆盖率缺口清偿):

W5(R29) S5 补测守阵(mutcore 审计 core/modules/traffic_sample_mod.py; 三分类/红验对应单点
tmp-analysis/mut-core-w5-classify.md, 中危真洞全盖 + 低危按簇代表, bug 面不入此列):
"""

import logging

import os

import threading

import time

from datetime import datetime, time as _time

import pytest

import yaml

from auto_qb.config import QbTraffic, load_config

from auto_qb.config.validation import validate_config

from auto_qb.core.modules import traffic_sample_mod as ts_mod

from auto_qb.core.modules.traffic_sample_mod import (
    EVICT_CHECK_INTERVAL_S,
    GLOBAL_SERIES_KEY,
    V4_BUFFER_SLOT_CAP,
    ZRUN_CAP_SAMPLES,
    ZRUN_FLUSH_S,
    TrafficSampleModule,
)

from auto_qb.core.taskqueue import Task

from auto_qb.core.traffic_store import (
    AggRow,
    HEADER_LINE_V4,
    HOUR_SECONDS,
    TrafficV4Store,
    V4Block,
    V4HourSample,
    V4NullRun,
    V4Sample,
    V4ZeroRun,
    format_agg_row,
    format_v4_day_text,
    parse_v4_agg_text,
    parse_v4_day_text,
    v4_agg_file_path,
    v4_block_slots,
    v4_day_epoch,
    v4_day_file_path,
    v4_date_str_epoch,
    v4_epoch_date_str,
    v4_hour_agg,
    v4_live_tail_slots,
    v4_month_epoch,
    v4_rollup_agg,
    v4_series_dir,
    v4_window_dates,
    v4_z_totals_ramp,
)

from helpers import FakeClient, FakeTorrent, active_torrent, capture_logs, make_manager, seed_store, server_state

from webui_helpers import _enable_qb_traffic, _qb_v4

from traffic_sample_support import (
    _mgr_with_traffic,
    _run_sample,
)


def test_disabled_at_runtime_handler_noop(tmp_path):
    """运行期关闭(L0 换对象): 采样体入口现读判据 -> 短路不采样不动内存(与队列无关)"""
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = server_state()
    mod = mgr.host.get("qb_traffic")
    mod.start(mgr.ctx, dry_run=False)
    mgr.config.qb_traffic = QbTraffic(enabled=False)
    _run_sample(mgr)
    assert mod.latest == {} and mod._baselines == {}  # 零采样零内存变更
