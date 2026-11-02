"""test_speed_curve_config 测试计划: 全局限速曲线(Traffic Monitor 接入 qB 全局速度限制)

## 测试计划(每个测试函数一条)
- test_speed_curve_config_disabled_by_default: 未配置 global_speed_limit_curve -> None(不启用)
- test_speed_curve_config_parses_sample: 完整样例解析(period 归一化/阈值字节/速度字节)
- test_speed_curve_config_enabled_key: enabled 总开关解析(缺省 True/显式 true|false/非法值报错)
- test_speed_curve_config_rejects_bad_section: 顶层非 dict / 未知键
- test_speed_curve_config_interval_optional_and_validated: interval 缺省回退主 interval / 非法值报错
- test_speed_curve_config_rejects_bad_traffic_source: 顶层 traffic_source 结构错误(非字典/未知键/provider 非枚举/缺或空 dat_path/traffic_monitor 非字典)
- test_speed_curve_config_rejects_bad_curves: curves 缺失/空/非单项映射/键名非 curve/curve 非 dict/未知键/缺 period/非法或重复 period/双向全缺
- test_speed_curve_config_rejects_bad_points: 档位表空/阈值<=0或非递增/缺方向键/未知键/速度非法/多阈值键
- test_speed_unit_prefixless_ib_aggregates_config_error: 守阵(issue 26-10-29-1252)——速度键写无前缀 iB/s 时 load_config 聚合成 ConfigError(消息含键名), 不许 KeyError 裸穿「统一 ConfigError」契约
- test_normalize_period_aliases: period 别名归一化(day/1D/D/month/ND) / 非法值 ValueError
- test_parse_history_dat_rows: 头行忽略 / KB×1024 / 乱序按日期升序返回
- test_parse_history_dat_bad_lines: 脏行计数(同分支多条累加) / 非法日期 / 重复日期取最后
- test_aggregate_periods: day 当天行(缺失=0) / month 当月求和 / ND 自然日窗口求和(窗口外排除)
- test_aggregate_nd_window_multi_digit: ND 窗口两位数 N(30D)精确求和 —— 前导数字截断(30D->3D)不得缩水 (W3-S5)
- test_speed_unit_conversion_boundaries: kib_to_bytes / bytes_to_kib_floor 边界(0/1/负/半值; kib_1 负值契约锁, 上游不可达的防御分支) (W3-S5)
- test_speed_curve_no_config_noop: 未配置曲线(conf None) -> handler 直接返回
- test_traffic_view_disabled_without_config
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
    GIB,
    MIB,
    _FakeTransfer,
    _fake_client,
    _run_curve,
)

# ---------- 配置解析 / fail-fast ----------
#: 合法样例数据源(S15 后在顶层 traffic_source 段, 不再内联进曲线段)
_VALID_DAT = r"D:\Programs\TrafficMonitor\history_traffic.dat"


def _cfg_dict(gslc_spec, traffic_source=None) -> dict:
    if traffic_source is None:  # 缺省 = 合法 Traffic Monitor 数据源
        traffic_source = {"traffic_monitor": {"dat_path": _VALID_DAT}}
    return {
        "config":
            {
                "qbittorrent": {
                    "host": "127.0.0.1",
                    "port": 8080,
                    "username": "u",
                    "password": "p"
                },
                "trackers": {},
                "traffic_source": traffic_source,
                "global_speed_limit_curve": gslc_spec,
            }
    }


def _load(tmp_path, gslc_spec, traffic_source=None):
    p = tmp_path / "config.yml"
    p.write_text(yaml.dump(_cfg_dict(gslc_spec, traffic_source), allow_unicode=True), encoding="utf-8")
    return load_config(str(p))


def _valid_spec() -> dict:
    """合法完整样例(与 想法.md 样式一致, 上/下载曲线各带 period); 数据源见顶层 traffic_source"""
    return {
        "interval":
            "10M",
        "curves":
            [
                {
                    "curve":
                        {
                            "period": "1D",
                            "upload_curve":
                                [
                                    {
                                        "10GiB": {
                                            "upload_speed_limit": "6MiB/s"
                                        }
                                    },
                                    {
                                        "20GiB": {
                                            "upload_speed_limit": "5MiB/s"
                                        }
                                    },
                                    {
                                        "1000GiB": {
                                            "upload_speed_limit": "0.5MiB/s"
                                        }
                                    },
                                ],
                            "download_curve": [{
                                "30GiB": {
                                    "download_speed_limit": "11MiB/s"
                                }
                            }],
                        },
                },
                {
                    "curve": {
                        "period": "7D",
                        "download_curve": [{
                            "50GiB": {
                                "download_speed_limit": "10MiB/s"
                            }
                        }]
                    },
                },
            ],
    }


def test_speed_curve_config_disabled_by_default(tmp_path):
    """未配置 global_speed_limit_curve 段 -> Config.global_speed_limit_curve is None"""
    p = tmp_path / "config.yml"
    d = _cfg_dict(None)
    d["config"].pop("global_speed_limit_curve")
    p.write_text(yaml.dump(d, allow_unicode=True), encoding="utf-8")
    cfg = load_config(str(p))
    assert cfg.global_speed_limit_curve is None


def test_speed_curve_config_parses_sample(tmp_path):
    """完整样例解析: period 归一化 / 阈值与速度为字节 / 多曲线 / 单方向省略"""
    cfg = _load(tmp_path, _valid_spec())
    g = cfg.global_speed_limit_curve
    assert g is not None
    # 数据源在顶层 traffic_source 段(S15), 曲线段不再持有 dat_path
    assert cfg.traffic_source.traffic_monitor.dat_path == _VALID_DAT
    assert traffic_paths.dat_path(cfg) == _VALID_DAT
    assert not hasattr(g, "dat_path")
    assert g.interval == 600.0  # interval: 10M -> 600 秒
    assert len(g.curves) == 2
    day, week = g.curves
    assert day.period == "day"  # 1D -> day
    assert week.period == "7D"
    # upload: 10GiB -> 6MiB/s
    assert day.upload_points[0].threshold_bytes == 10 * GIB
    assert day.upload_points[0].speed_bytes_per_s == 6 * MIB
    assert day.upload_points[2].speed_bytes_per_s == int(0.5 * MIB)  # 0.5MiB/s 支持
    assert day.download_points[0].threshold_bytes == 30 * GIB
    # 第二曲线只配 download_curve -> upload_points None(不管理上传)
    assert week.upload_points is None
    assert week.download_points[0].speed_bytes_per_s == 10 * MIB


def test_speed_curve_config_enabled_key(tmp_path):
    """enabled 总开关: 缺省 True(现行行为) / 显式 true|false 解析为 bool / 非法值报错"""
    g = _load(tmp_path, copy.deepcopy(_valid_spec())).global_speed_limit_curve
    assert g.enabled is True  # 缺省 = True

    spec = copy.deepcopy(_valid_spec())
    spec["enabled"] = "false"
    assert _load(tmp_path, spec).global_speed_limit_curve.enabled is False

    spec = copy.deepcopy(_valid_spec())
    spec["enabled"] = "true"
    assert _load(tmp_path, spec).global_speed_limit_curve.enabled is True

    spec = copy.deepcopy(_valid_spec())
    spec["enabled"] = "abc"
    with pytest.raises(ConfigError):
        _load(tmp_path, spec)


def test_speed_curve_config_rejects_bad_section(tmp_path):
    """顶层非字典 / 未知键 -> ValueError"""
    for bad in ("str", [], 123):
        with pytest.raises(ConfigError):
            _load(tmp_path, bad)
    spec = _valid_spec()
    spec["extra"] = 1
    with pytest.raises(ConfigError):
        _load(tmp_path, spec)


def test_speed_curve_config_interval_optional_and_validated(tmp_path):
    """interval 缺省 -> None(回退主 interval); 非法/非正 -> ValueError"""
    spec = copy.deepcopy(_valid_spec())
    spec.pop("interval")
    assert _load(tmp_path, spec).global_speed_limit_curve.interval is None

    for bad in ("abc", "0S", "-5M", 0):
        spec = copy.deepcopy(_valid_spec())
        spec["interval"] = bad
        with pytest.raises(ConfigError):
            _load(tmp_path, spec)


def test_speed_curve_config_rejects_bad_traffic_source(tmp_path):
    """顶层 traffic_source 结构错误 -> ValueError(段缺省合法, 由 test_config_traffic_monitor 覆盖)

    S15 后数据源从曲线段内联迁到顶层 traffic_source 段; 这里只覆盖形状错误被拒。
    """
    bad_sources = [
        [],  # 非字典
        "not-a-dict",  # 非字典
        {
            "other_app": {
                "path": "a"
            }
        },  # 未知顶层键
        {
            "provider": "other_app"
        },  # provider 非枚举
        {
            "provider": "traffic_monitor",
            "traffic_monitor": {}
        },  # 缺 dat_path
        {
            "provider": "traffic_monitor",
            "traffic_monitor": {
                "dat_path": ""
            }
        },  # 空 dat_path
        {
            "traffic_monitor": "not-a-dict"
        },  # traffic_monitor 非字典
        {
            "traffic_monitor": {
                "dat_path": "a",
                "extra": 1
            }
        },  # traffic_monitor 内部未知键
    ]
    for src in bad_sources:
        with pytest.raises(ConfigError):
            _load(tmp_path, copy.deepcopy(_valid_spec()), traffic_source=src)
    # 合法数据源(两来源参数可并存, provider 决定生效来源)
    tm_cfg = _load(
        tmp_path,
        copy.deepcopy(_valid_spec()),
        traffic_source={"traffic_monitor": {
            "dat_path": "a"
        }},
    )
    assert traffic_paths.dat_path(tm_cfg) == "a"
    # 工具来源: 配置里只剩 tool_dir/tool_exe/notify_cooldown_s —— 取数路径由工具发现指针提供,
    # 解析细节见 test_traffic_source_paths.py(这里只验配置面能通过校验)
    tool_cfg = _load(
        tmp_path,
        copy.deepcopy(_valid_spec()),
        traffic_source={
            "provider": "global_traffic_monitor",
            "global_traffic_monitor": {
                "tool_dir": "/d"
            }
        },
    )
    assert tool_cfg.traffic_source.provider == "global_traffic_monitor"


def test_speed_curve_config_rejects_bad_curves(tmp_path):
    """curves 结构错误: 缺失/空/非单项映射/键名非 curve/curve 非字典/未知键/缺 period/非法或重复 period/双向全缺 -> ValueError"""
    base = copy.deepcopy(_valid_spec())

    def item(inner):
        """构造单个曲线条目: curves 列表元素必须是单项映射 {curve: {...}}"""
        return {"curve": inner}

    cases = []
    c = copy.deepcopy(base)
    c.pop("curves")
    cases.append(("curves 缺失", c))
    c = copy.deepcopy(base)
    c["curves"] = []
    cases.append(("curves 空", c))
    c = copy.deepcopy(base)
    c["curves"] = ["not-a-dict"]
    cases.append(("条目非字典", c))
    c = copy.deepcopy(base)
    c["curves"] = [{"curve": {"period": "1D"}, "extra": 1}]
    cases.append(("条目非单项映射", c))
    c = copy.deepcopy(base)
    c["curves"] = [{"other": {"period": "1D"}}]
    cases.append(("键名非 curve", c))
    c = copy.deepcopy(base)
    c["curves"] = [{"curve": "not-a-dict"}]
    cases.append(("curve 非字典", c))
    c = copy.deepcopy(base)
    c["curves"] = [item({"period": "1D", "extra": 1, "upload_curve": [{"10GiB": {"upload_speed_limit": "6MiB/s"}}]})]
    cases.append(("曲线内未知键", c))
    c = copy.deepcopy(base)
    c["curves"] = [item({"upload_curve": [{"10GiB": {"upload_speed_limit": "6MiB/s"}}]})]
    cases.append(("缺 period", c))
    c = copy.deepcopy(base)
    c["curves"] = [item({"period": "weekly", "upload_curve": [{"10GiB": {"upload_speed_limit": "6MiB/s"}}]})]
    cases.append(("非法 period", c))
    c = copy.deepcopy(base)
    c["curves"] = [item({"period": "0D", "upload_curve": [{"10GiB": {"upload_speed_limit": "6MiB/s"}}]})]
    cases.append(("非法 period 0D", c))
    c = copy.deepcopy(base)
    c["curves"] = [  # 1D 与 day 归一化后重复
        item({"period": "1D", "upload_curve": [{"10GiB": {"upload_speed_limit": "6MiB/s"}}]}),
        item({"period": "day", "upload_curve": [{"10GiB": {"upload_speed_limit": "6MiB/s"}}]}),
    ]
    cases.append(("重复 period", c))
    c = copy.deepcopy(base)
    c["curves"] = [item({"period": "1D"})]
    cases.append(("双向全缺", c))
    for name, spec in cases:
        with pytest.raises(ConfigError):
            _load(tmp_path, spec), name


def test_speed_curve_config_rejects_bad_points(tmp_path):
    """档位表错误: 空表/阈值<=0或非递增/缺方向键/未知键/速度非法/非单项 -> ValueError"""
    up = [{"10GiB": {"upload_speed_limit": "6MiB/s"}}]

    def curve(points=up, **kw):
        inner = {"period": "1D", "upload_curve": points}
        inner.update(kw)
        return {"curves": [{"curve": inner}]}

    cases = [
        curve(points=[]),  # 空档位表
        curve(points=[{
            "0GiB": {
                "upload_speed_limit": "6MiB/s"
            }
        }]),  # 阈值 0
        curve(points=[{
            "20GiB": {
                "upload_speed_limit": "6MiB/s"
            }
        }, {
            "10GiB": {
                "upload_speed_limit": "5MiB/s"
            }
        }]),  # 非递增
        curve(points=[{
            "10GiB": {
                "download_speed_limit": "6MiB/s"
            }
        }]),  # 方向键不符
        curve(points=[{
            "10GiB": {
                "upload_speed_limit": "6MiB/s",
                "extra": 1
            }
        }]),  # 未知键
        curve(points=[{
            "10GiB": {
                "upload_speed_limit": "6MiB/s",
                "download_speed_limit": "5MiB/s"
            }
        }]),  # 多方向键
        curve(points=[{
            "10GiB": "6MiB/s"
        }]),  # 速度非字典
        curve(points=[{
            "10GiB": {
                "upload_speed_limit": "6MiB/h"
            }
        }]),  # 非法速度格式
        curve(points=[{
            "10GiB": {
                "upload_speed_limit": "-1MiB/s"
            }
        }]),  # 负速度
        curve(points=[{
            "10GiB": {
                "upload_speed_limit": "6MiB/s"
            },
            "20GiB": {
                "upload_speed_limit": "5MiB/s"
            }
        }]),  # 多阈值键
        curve(points=[{
            "10GiB": {}
        }]),  # 档位内缺方向键
    ]
    for spec in cases:
        with pytest.raises(ConfigError):
            _load(tmp_path, spec)


def test_speed_unit_prefixless_ib_aggregates_config_error(tmp_path):
    """守阵(issue 26-10-29-1252): 速度键写无前缀 iB/s -> 聚合 ConfigError(消息含键名)

    旧实现 parse_speed 正则允许 iB/s 但单位表无此键, KeyError 逃出校验层 _try(只接
    ValueError)与 load_config「任何配置问题统一抛 ConfigError」契约, 用户只见裸 traceback。
    """
    d = _cfg_dict(None)
    d["config"]["trackers"] = {"T1": {"domains": ["example.com"], "upload_speed_limit": "1iB/s"}}
    p = tmp_path / "config.yml"
    p.write_text(yaml.dump(d, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ConfigError) as ei:
        load_config(str(p))
    msg = str(ei.value)
    assert "配置校验失败" in msg and "upload_speed_limit" in msg, msg


# ---------- curves 纯函数 ----------
def test_normalize_period_aliases():
    """period 别名归一化: day/1D/D -> day; month -> month; ND -> ND; 非法 -> ValueError"""
    assert curves.normalize_period("day") == "day"
    assert curves.normalize_period("1D") == "day"
    assert curves.normalize_period("D") == "day"  # 文档别名 "D"(loaders 配置期直达)
    assert curves.normalize_period("DAY") == "day"
    assert curves.normalize_period("month") == "month"
    assert curves.normalize_period("7D") == "7D"
    assert curves.normalize_period("30D") == "30D"
    for bad in ("weekly", "0D", "3", "-1D", ""):
        with pytest.raises(ValueError):  # utils 层原始 ValueError, 非配置校验错误
            curves.normalize_period(bad)


def test_parse_history_dat_rows():
    """头行忽略 / KB×1024 / 乱序 -> 按日期升序返回"""
    text = (
        'lines: "30"\n'
        "2026/09/04 64033621/104743685\n"
        "2026/09/02 23243979/53483350\n"
        "2026/09/03 23295975/37857445\n"
    )
    rows, bad = curves.parse_history_dat(text)
    assert bad == 0
    assert [r[0].isoformat() for r in rows] == ["2026-09-02", "2026-09-03", "2026-09-04"]
    # 64033621 KB * 1024
    assert rows[-1][1] == 64033621 * 1024
    assert rows[-1][2] == 104743685 * 1024
    assert rows[0][1] == 23243979 * 1024


def test_parse_history_dat_bad_lines():
    """脏行计数 / 非法日期跳过 / 重复日期取最后 / 空行忽略

    两条格式坏行 + 两条非法日期行: 每个分支都出现两次, 计数必须是累加而非覆盖
    (parse_dat_19: 格式坏行分支 `bad += 1` -> `bad = 1` 会漏计)。
    """
    text = (
        'lines: "30"\n'
        "2026/09/04 100/200\n"
        "garbage line\n"
        "another garbage line\n"  # 同分支第二条格式坏行
        "2026/13/40 1/2\n"  # 非法日期
        "2026/02/30 1/2\n"  # 非法日期(2 月无 30 日), 同分支第二条
        "2026/09/04 300/400\n"  # 重复日期 -> 取最后
        "   \n"
    )
    rows, bad = curves.parse_history_dat(text)
    assert bad == 4
    assert len(rows) == 1
    assert rows[0] == (date(2026, 9, 4), 300 * 1024, 400 * 1024)


def test_aggregate_periods():
    """day 当天行(缺失=0) / month 当月求和 / ND 自然日窗口求和(窗口外排除)"""
    today = date(2026, 9, 4)
    rows = [
        (date(2026, 9, 4), 10 * GIB, 1 * GIB),  # 今天
        (date(2026, 9, 3), 2 * GIB, 0),
        (date(2026, 9, 2), 3 * GIB, 0),
        (date(2026, 8, 30), 100 * GIB, 0),  # 上月底(7D 窗口外, month 窗口外)
    ]
    # day: 只取今天行
    assert curves.aggregate(rows, "day", today) == (10 * GIB, 1 * GIB)
    # day + 今天行缺失(如程序在跨天后首轮): 累计视为 0
    assert curves.aggregate(rows, "day", date(2026, 9, 5)) == (0, 0)
    # month: 当月(9月)所有行求和
    assert curves.aggregate(rows, "month", today) == (15 * GIB, 1 * GIB)
    # 3D: 最近 3 个自然日 [09-02, 09-04], 8-30 在窗口外
    assert curves.aggregate(rows, "3D", today) == (15 * GIB, 1 * GIB)
    # 2D: 最近 2 个自然日 [09-03, 09-04]
    assert curves.aggregate(rows, "2D", today) == (12 * GIB, 1 * GIB)
    # 空窗口 -> (0, 0)
    assert curves.aggregate(rows, "1D", date(2026, 9, 10)) == (0, 0)


def test_aggregate_nd_window_multi_digit():
    """ND 窗口两位数 N: 30D 按 N=30 取 [today-29d, today] 整窗求和

    W3-S5(aggregate_20: period[:-1] -> period[:1]): 30D 被截成 3D -> 窗口缩水,
    全局限速按错窗口决策。单位数窗口(3D/2D)对截断变异免疫, 必须用两位数 N 才能杀;
    反向对照: 单位数 3D 截断前后同值。
    """
    today = date(2026, 9, 30)
    rows = [
        (date(2026, 9, 30), 1 * GIB, 1 * GIB),  # 窗口内(30D 与 3D 都含)
        (date(2026, 9, 10), 2 * GIB, 2 * GIB),  # 仅 30D 含
        (date(2026, 9, 1), 4 * GIB, 4 * GIB),  # 仅 30D 含(窗口起点 today-29d = 09-01, 含端点)
        (date(2026, 8, 15), 8 * GIB, 8 * GIB),  # 窗口外
    ]
    assert curves.aggregate(rows, "30D", today) == (7 * GIB, 7 * GIB)
    assert curves.aggregate(rows, "3D", today) == (1 * GIB, 1 * GIB)


def test_speed_unit_conversion_boundaries():
    """kib_to_bytes / bytes_to_kib_floor 边界(0/1/负/半值)—— 此前全套件零覆盖

    kib_1 契约锁: 负 KiB 上游不可达(qbapi 旧版 -1 标记已停用, 曲线目标 speed 来自
    config 非负域), 属防御分支 —— 断言行为锁契约, 不判真洞(W3-S5)。
    """
    # kib_to_bytes: 0 = 不限速; 1 KiB/s 是合法正值不得抹 0(kib_5); 负值归 0(kib_1 契约锁)
    assert curves.kib_to_bytes(0) == 0
    assert curves.kib_to_bytes(1) == 1024
    assert curves.kib_to_bytes(-1) == 0
    # bytes_to_kib_floor: 整除向下, 0/负数归 0; 1 B 不足 1 KiB 归 0(floor_6: 负值不得漏成负 KiB)
    assert curves.bytes_to_kib_floor(0) == 0
    assert curves.bytes_to_kib_floor(1) == 0
    assert curves.bytes_to_kib_floor(1024) == 1
    assert curves.bytes_to_kib_floor(1536) == 1
    assert curves.bytes_to_kib_floor(-1) == 0
    assert curves.bytes_to_kib_floor(-1024) == 0
    assert curves.bytes_to_kib_floor(None) == 0


def test_speed_curve_no_config_noop(tmp_path):
    """未配置曲线(conf None) -> handler 直接返回, 不读文件不写 qB"""
    mgr = make_manager(str(tmp_path / "state.json"))
    client = _fake_client()
    mgr.client = client

    assert _run_curve(mgr) is True
    assert client.transfer.calls == []


# ---------- 限速/流量只读快照的 limit 段(来源段见 test_traffic_snapshot) ----------
#
# 26-10-18-0813 A4 起本文件只锁 **limit 段**: 曲线的结论(命中/实际限速/原因码/限速态);
# 来源段(source/periods/history)的所有权与段隔离在 test_traffic_snapshot, 这里只顺带断言
# "曲线跑完来源段不动", 不重复那套契约。
def test_traffic_view_disabled_without_config(tmp_path):
    """未启用曲线 -> state=disabled(前端据此不渲染流量/限速 pill)"""
    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.config.global_speed_limit_curve = None
    assert mgr.web.traffic_view["state"] == "disabled"

    assert _run_curve(mgr) is True
    assert mgr.web.traffic_view["state"] == "disabled"
