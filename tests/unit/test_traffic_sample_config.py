"""test_traffic_sample_config 测试计划: qB 口径流量采样器(plan 26-10-03-0946 方案C P1 采样器核心 + §06 配置键
+ plan 26-10-04-1957 S2a 写侧/S2b 聚合与恢复 + plan 26-10-05-2200 v4 换代 B2 写侧状态机与结算)

## 测试计划(每个测试函数一条)
- test_qb_traffic_config_absent_means_disabled: 键组缺省 -> config.qb_traffic 为 None(未启用)
- test_qb_traffic_config_parses_sample: 完整样例解析(enabled/四个时间键换算成秒, 含 flush_interval)
- test_qb_traffic_config_partial_falls_back_to_defaults: 部分键缺省回退 QbTraffic 默认值
- test_qb_traffic_config_rejects_bad_section: 段非 dict / 未知键 / enabled 非布尔
- test_qb_traffic_config_bounds_matrix: 各时间/布尔键边界矩阵(1.5S 需 main_tick 配合 / 60S~1H / 1H~90D / 7D~无上限 恰好压线收, 压线外拒)
- test_qb_traffic_sample_interval_multiplier_below_one_rejected: 倍数下限(int >= 1) —— 0 拒,
  1 = 1 倍 main_tick 收(倍数语义下生效间隔恒 >= main_tick, 原「< main_tick」不可能)
- test_qb_traffic_legacy_sample_interval_key_rejected: 旧秒值键 sample_interval 已退役(计划
  26-11-10-0252 D1 硬切) —— 出现即按未知键拒, 不做静默换算
- test_qb_traffic_flush_interval_bounds: flush_interval —— dataclass 缺省 600 /
  60~3600s 整数秒压线收 / 越界与非整数秒与坏格式聚合报错

聚合分层与恢复(plan 26-10-04-1957 S2b §04):

启动恢复按需读集(plan 26-10-12-2010, 读集下界 now - rollup_window -> agg 水位所在日):

v4 定约用例(plan 26-10-05-2200 §04 表 3/5/6/7, B2 落地):

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

from traffic_sample_support import (
    _PW_KEY,
    _cfg_dict,
    _load,
)


def test_qb_traffic_config_absent_means_disabled(tmp_path):
    """键组缺省 -> qb_traffic 为 None(未启用); 全默认实例同样为 None"""
    p = tmp_path / "config.yml"
    p.write_text(
        yaml.dump(
            {
                "config":
                    {
                        "qbittorrent": {
                            "host": "127.0.0.1",
                            "port": 8080,
                            "username": "u",
                            _PW_KEY: "p"
                        },
                        "trackers": {}
                    }
            },
            allow_unicode=True
        ),
        encoding="utf-8"
    )
    assert load_config(str(p)).qb_traffic is None


def test_qb_traffic_config_parses_sample(tmp_path):
    """完整样例解析: enabled 布尔化 + 各时间键换算成秒(含 v3 新键 flush_interval)

    采样间隔键是整数倍数(计划 26-11-10-0252): 30 倍 x 缺省 main_tick 2s = 60s 生效。
    """
    cfg = _load(
        tmp_path, {
            "enabled": "true",
            "sample_interval_multiplier": 30,
            "flush_interval": "10M",
            "raw_window": "48H",
            "rollup_window": "60D",
        }
    ).qb_traffic
    assert cfg.enabled is True
    assert cfg.sample_interval_multiplier == 30
    assert cfg.flush_interval == 600.0
    assert cfg.raw_window == 48 * 3600.0
    assert cfg.rollup_window == 60 * 86400.0


def test_qb_traffic_config_partial_falls_back_to_defaults(tmp_path):
    """部分键缺省回退默认值(1 倍 main_tick / 10M / 24H / 30D, enabled 缺省 false)"""
    cfg = _load(tmp_path, {"enabled": "true"}).qb_traffic
    assert cfg.enabled is True
    d = QbTraffic()
    assert cfg.sample_interval_multiplier == d.sample_interval_multiplier == 1
    assert cfg.flush_interval == d.flush_interval == 600.0
    assert cfg.raw_window == d.raw_window == 86400.0
    assert cfg.rollup_window == d.rollup_window == 30 * 86400.0


def test_qb_traffic_config_rejects_bad_section():
    """段非 dict / 未知键 / enabled 非布尔 -> 聚合报错(fail-fast)"""
    errors = validate_config(_cfg_dict("nope"))
    assert any("config.qb_traffic" in e and "字典" in e for e in errors)
    errors = validate_config(_cfg_dict({"unknown_key": "1", "enabled": "maybe"}))
    assert any("未知键" in e and "qb_traffic" in e for e in errors)
    assert any("config.qb_traffic.enabled" in e for e in errors)


def test_qb_traffic_config_bounds_matrix():
    """边界矩阵: 恰好压线合法(含等价秒数), 压线外拒绝; 各键独立校验

    采样间隔是 main_tick 的整数倍数(计划 26-11-10-0252 D3/D6): 倍数下限 1, 有效秒数上限 600s
    (缺省 main_tick=2s 时 300 倍恰好 600s 压线收, 301 倍 602s 拒)。
    """
    # 合法: 上下边界恰好压线(1 倍 main_tick / 300 倍 x 2s = 600s / 1H~90D / 7D~无上限)
    ok = validate_config(
        _cfg_dict(
            {
                "enabled": "true",
                "sample_interval_multiplier": 1,
                "flush_interval": "10M",
                "raw_window": "1H",
                "rollup_window": "7D",
            },
            main_tick="1S",  # 1 倍 = 1s 生效(倍数语义下恒 >= main_tick, 无需再比下限)
        )
    )
    assert ok == [], ok
    ok = validate_config(
        _cfg_dict(
            {
                "enabled": "false",
                "sample_interval_multiplier": 300,  # 300 x 缺省 main_tick 2s = 600s 恰好压上边界
                "flush_interval": "1H",  # 3600s 恰好压上边界
                "raw_window": "90D",
                "rollup_window": "36500D",  # 保留窗无上限: 100 年也合法(等效永久保留)
            }
        )
    )
    assert ok == [], ok
    # 越界: 各键压线外即拒
    bad = validate_config(_cfg_dict({"sample_interval_multiplier": 301}))  # 301 x 2s = 602s > 600s
    assert any("sample_interval_multiplier" in e and "600" in e for e in bad), bad
    bad = validate_config(_cfg_dict({"raw_window": "30M"}))
    assert any("raw_window" in e for e in bad), bad
    bad = validate_config(_cfg_dict({"raw_window": "91D"}))
    assert any("raw_window" in e for e in bad), bad
    bad = validate_config(_cfg_dict({"rollup_window": "6D"}))
    assert any("rollup_window" in e for e in bad), bad


def test_qb_traffic_sample_interval_multiplier_below_one_rejected():
    """倍数下限(计划 26-11-10-0252 D3): int >= 1, 0 拒; 1 = 1 倍 main_tick 收

    倍数语义下生效间隔恒 >= main_tick, 原「采样间隔 < main_tick」在配置面数学上不可能 ——
    该下限用例随旧秒值键一并退役, 改守倍数自身的整数下限。
    """
    errors = validate_config(_cfg_dict({"sample_interval_multiplier": 0}, main_tick="2S"))
    assert any("sample_interval_multiplier" in e and ">= 1" in e for e in errors), errors
    # 压线即合法: 恰 1 倍收
    assert validate_config(_cfg_dict({"sample_interval_multiplier": 1}, main_tick="2S")) == []


def test_qb_traffic_legacy_sample_interval_key_rejected():
    """旧秒值键 sample_interval 已退役(D1 硬切): 出现即按未知键拒, 不做静默换算

    存量配置由迁移链 v6->v7 保行为换算; 终态校验层零旧键分支, 旧写法必须是硬错而非被
    曲解成倍数(30S 若被 int() 吃掉就变 30 倍, 静默放大 30 倍间隔)。
    """
    errors = validate_config(_cfg_dict({"sample_interval": "30S"}, main_tick="2S"))
    assert any("未知键" in e and "sample_interval" in e for e in errors), errors


def test_qb_traffic_flush_interval_bounds():
    """flush_interval(v3 新键): 60~3600s 整数秒压线收; 越界 / 非整数秒 / 坏格式聚合报错"""
    assert QbTraffic().flush_interval == 600.0  # dataclass 缺省 600
    for good in ("60S", "600S", "1H", "10M"):  # 压线 + 等价写法
        assert validate_config(_cfg_dict({"flush_interval": good})) == [], good
    bad = validate_config(_cfg_dict({"flush_interval": "30S"}))
    assert any("flush_interval" in e and ">= 60" in e for e in bad), bad
    bad = validate_config(_cfg_dict({"flush_interval": "7200S"}))
    assert any("flush_interval" in e and "<= 3600" in e for e in bad), bad
    bad = validate_config(_cfg_dict({"flush_interval": "90.5S"}))
    assert any("flush_interval" in e and "整数秒" in e for e in bad), bad
    bad = validate_config(_cfg_dict({"flush_interval": "abc"}))
    assert any("config.qb_traffic.flush_interval" in e for e in bad), bad
