"""test_speed_curve 测试计划: 全局限速曲线(Traffic Monitor 接入 qB 全局速度限制)

## 测试计划(每个测试函数一条)
- test_speed_curve_config_disabled_by_default: 未配置 global_speed_limit_curve -> None(不启用)
- test_speed_curve_config_parses_sample: 完整样例解析(period 归一化/阈值字节/速度字节)
- test_speed_curve_config_rejects_bad_section: 顶层非 dict / 未知键
- test_speed_curve_config_interval_optional_and_validated: interval 缺省回退主 interval / 非法值报错
- test_speed_curve_config_rejects_bad_traffic_source: 数据源缺失/空/多元素/未知来源/元素非 dict/缺 traffic_monitor/内部未知键/缺 dat_path
- test_speed_curve_config_rejects_bad_curves: curves 缺失/空/非单项映射/键名非 curve/curve 非 dict/未知键/缺 period/非法或重复 period/双向全缺
- test_speed_curve_config_rejects_bad_points: 档位表空/阈值<=0或非递增/缺方向键/未知键/速度非法/多阈值键
- test_normalize_period_aliases: period 别名归一化(day/1D/month/ND) / 非法值 ValueError
- test_parse_history_dat_rows: 头行忽略 / KB×1024 / 乱序按日期升序返回
- test_parse_history_dat_bad_lines: 脏行计数 / 非法日期 / 重复日期取最后
- test_aggregate_periods: day 当天行(缺失=0) / month 当月求和 / ND 自然日窗口求和(窗口外排除)
- test_curve_speed_plan_b: 全程分档覆盖(首档覆盖低端, 边界, 末档延续)
- test_merge_direction_and_bytes_to_kib: 取最小非零(全0=0/空=None) / KiB 半值进位
- test_speed_curve_global_task_registered: 配置存在 -> 创建 speed_limit_curve 全局任务
- test_speed_curve_global_task_uses_own_interval: 曲线配置专属 interval
- test_speed_curve_global_task_not_registered: 未配置 -> 不创建
- test_speed_curve_applies_staged_upload_limit: 命中档位 -> transfer_set_upload_limit(bytes/s)
- test_speed_curve_idempotent_second_run_no_write: 同档位重复执行不重复写
- test_speed_curve_manual_odd_kib_skips_direction: 当前正奇数 KiB(手动)不覆盖该方向
- test_speed_curve_multi_period_takes_strictest: 同方向多条 period 曲线取最严(最小非零)
- test_speed_curve_unlimited_target_writes_zero: 目标 0(该档不限速) -> transfer 写 0(不限)
- test_speed_curve_cross_day_rollback: 今天行缺失 -> 累计 0 -> 回落首档(自动放开)
- test_speed_curve_dry_run_no_read_no_write: dry_run 不读当前不写 qB, 记录 state
- test_speed_curve_dat_missing_noop: dat 文件缺失 -> 本轮不动
- test_speed_curve_no_config_noop: 未配置曲线(conf None) -> handler 直接返回
- test_speed_curve_dat_all_bad_lines_noop: dat 有文件但全坏行 -> 本轮不动
- test_speed_curve_dat_bad_lines_still_applies: dat 部分坏行 -> 跳过坏行仍写 qB
- test_speed_curve_success_logs_period_stats: 设置成功按各 period 输出累计上传/下载(今日/七日/本月/三十日)
- test_speed_curve_format_helpers: 日志格式化辅助(_fmt_bytes/_cn_number/_period_label/_fmt_global_limit)
- test_qbapi_global_speed_limit_normalization: qbapi KiB<->bytes/s 换算与读写
"""
import copy
import logging
import os
from datetime import date, timedelta

import pytest
import yaml

from auto_qb import curves
from auto_qb.config import CurvePoint, GlobalSpeedLimitCurve, PeriodCurve, load_config
from auto_qb.config import ConfigError
from auto_qb.mixins.speed_curve import _cn_number, _fmt_bytes, _fmt_global_limit, _period_label
from auto_qb.taskqueue import Task
from helpers import FakeClient, make_manager

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


def _gslc(dat_path, *period_curves, interval=None) -> GlobalSpeedLimitCurve:
    return GlobalSpeedLimitCurve(dat_path=dat_path, curves=list(period_curves), interval=interval)


def _dat_text(rows) -> str:
    """rows: [(date, 上传字节, 下载字节)] -> dat 文件文本(单位 KB)"""
    lines = ['lines: "30"']
    for d, up_b, down_b in rows:
        lines.append(f"{d:%Y/%m/%d} {up_b // 1024}/{down_b // 1024}")
    return "\n".join(lines)


def _write_dat(tmp_path, rows, name="history_traffic.dat") -> str:
    p = tmp_path / name
    p.write_text(_dat_text(rows), encoding="utf-8")
    return str(p)


def _run_curve(mgr, dry_run: bool = False) -> bool:
    """直接执行全局限速曲线 handler(等价到期任务执行)"""
    task = Task("internal", "speed_limit_curve", interval=60, handler=mgr._handle_speed_limit_curve)
    return mgr._handle_speed_limit_curve(task, dry_run=dry_run)


def _make_mgr(tmp_path, gslc, with_app: bool = True):
    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.config.global_speed_limit_curve = gslc
    client = _fake_client() if with_app else FakeClient()
    mgr.client = client
    return mgr, client


# ---------- 配置解析 / fail-fast ----------
def _cfg_dict(gslc_spec) -> dict:
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
                "global_speed_limit_curve": gslc_spec,
            }
    }


def _load(tmp_path, gslc_spec):
    p = tmp_path / "config.yml"
    p.write_text(yaml.dump(_cfg_dict(gslc_spec), allow_unicode=True), encoding="utf-8")
    return load_config(str(p))


def _valid_spec() -> dict:
    """合法完整样例(与 想法.md 样式一致, 上/下载曲线各带 period)"""
    return {
        "interval":
            "10M",
        "traffic_source": [{
            "traffic_monitor": {
                "dat_path": r"D:\Programs\TrafficMonitor\history_traffic.dat"
            }
        }],
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
    assert g.dat_path == r"D:\Programs\TrafficMonitor\history_traffic.dat"
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
    """数据源缺失/空/多元素/未知来源/缺 dat_path -> ValueError"""
    bad_sources = [
        None,  # 缺失
        [],  # 空
        [{
            "traffic_monitor": {
                "dat_path": "a"
            }
        }, {
            "traffic_monitor": {
                "dat_path": "b"
            }
        }],  # 多数据源
        [{
            "other_app": {
                "path": "a"
            }
        }],  # 未知来源
        [{
            "traffic_monitor": {
                "dat_path": "a"
            },
            "extra": 1
        }],  # 来源额外键
        [{
            "traffic_monitor": "not-a-dict"
        }],  # traffic_monitor 非字典
        [{
            "traffic_monitor": {}
        }],  # 缺 dat_path
        [{
            "traffic_monitor": {
                "dat_path": ""
            }
        }],  # 空 dat_path
        ["not-a-dict"],  # 数据源元素非字典
        [{}],  # 缺少 traffic_monitor 键
        [{
            "traffic_monitor": {
                "dat_path": "a",
                "extra": 1
            }
        }],  # traffic_monitor 内部未知键
    ]
    for src in bad_sources:
        spec = copy.deepcopy(_valid_spec())
        spec["traffic_source"] = src
        with pytest.raises(ConfigError):
            _load(tmp_path, spec)


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
        return {"traffic_source": _valid_spec()["traffic_source"], "curves": [{"curve": inner}]}

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


# ---------- curves 纯函数 ----------
def test_normalize_period_aliases():
    """period 别名归一化: day/1D/D -> day; month -> month; ND -> ND; 非法 -> ValueError"""
    assert curves.normalize_period("day") == "day"
    assert curves.normalize_period("1D") == "day"
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
    """脏行计数 / 非法日期跳过 / 重复日期取最后 / 空行忽略"""
    text = (
        'lines: "30"\n'
        "2026/09/04 100/200\n"
        "garbage line\n"
        "2026/13/40 1/2\n"  # 非法日期
        "2026/09/04 300/400\n"  # 重复日期 -> 取最后
        "   \n"
    )
    rows, bad = curves.parse_history_dat(text)
    assert bad == 2
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


def test_merge_direction_and_bytes_to_kib():
    """合并: 取最小非零(最严); 全 0 -> 0; 空 -> None; KiB 半值进位"""
    assert curves.merge_direction([6 * MIB, 2 * MIB, 4 * MIB]) == 2 * MIB
    assert curves.merge_direction([0, 0]) == 0
    assert curves.merge_direction([]) is None
    assert curves.merge_direction([0, 5 * MIB]) == 5 * MIB  # 0(不限速档)不拉低最严
    assert curves.bytes_to_kib(0) == 0
    assert curves.bytes_to_kib(6 * MIB) == 6144
    assert curves.bytes_to_kib(int(0.5 * MIB)) == 512
    assert curves.bytes_to_kib(int(0.25 * MIB)) == 256  # 半值进位


# ---------- 集成: 任务注册 / handler ----------
def test_speed_curve_global_task_registered(tmp_path):
    """配置存在 -> _create_global_tasks 创建 speed_limit_curve 任务(interval 缺省回退主 interval) """
    gslc = _gslc("whatever.dat", _pc("day", up=_points(FULL_UPLOAD)))
    mgr, _ = _make_mgr(tmp_path, gslc)
    mgr._create_global_tasks()
    due = mgr.task_queue.due(max=100)
    assert [t.name for t in due] == ["speed_limit_curve"]
    assert due[0].interval == mgr.config.interval  # FakeConfig.interval = 60


def test_speed_curve_global_task_uses_own_interval(tmp_path):
    """曲线配置 interval -> 任务使用专属间隔, 不跟随主 interval"""
    gslc = _gslc("whatever.dat", _pc("day", up=_points(FULL_UPLOAD)), interval=600)
    mgr, _ = _make_mgr(tmp_path, gslc)
    mgr._create_global_tasks()
    due = mgr.task_queue.due(max=100)
    assert [t.name for t in due] == ["speed_limit_curve"]
    assert due[0].interval == 600


def test_speed_curve_global_task_not_registered(tmp_path):
    """未配置曲线 -> 不创建任务(即使有 delete_tags 之外的全局任务也不含曲线任务)"""
    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.client = FakeClient()
    mgr._create_global_tasks()
    assert mgr.task_queue.due(max=100) == []


def test_speed_curve_applies_staged_upload_limit(tmp_path):
    """今天行流量命中档位 -> transfer_set_upload_limit 写入对应 bytes/s(只管理配置了的方向) """
    today = date.today()
    dat = _write_dat(tmp_path, [(today, 15 * GIB, 5 * GIB)])
    gslc = _gslc(dat, _pc("day", up=_points(FULL_UPLOAD)))  # 只管理上传
    mgr, client = _make_mgr(tmp_path, gslc)

    assert _run_curve(mgr)
    # 15GiB -> 5MiB/s = 5120 KiB/s -> transfer 写 bytes/s; 下载方向无曲线 -> 不写
    assert client.transfer.calls == [("set_upload_limit", 5120 * 1024)]
    assert client.transfer.limits["upload_limit"] == 5120 * 1024
    assert client.transfer.limits["download_limit"] == 0  # 未管理下载(默认不限速)
    assert mgr.state["speed_limit_curve"][today.isoformat()] == {
        "upload_kib": 5120,
        "download_kib": None,
        "dry_run": False
    }


def test_speed_curve_idempotent_second_run_no_write(tmp_path):
    """目标 == 当前 -> 幂等, 重复执行不再调 transfer_set_upload_limit"""
    today = date.today()
    dat = _write_dat(tmp_path, [(today, 15 * GIB, 0)])
    gslc = _gslc(dat, _pc("day", up=_points(FULL_UPLOAD)))
    mgr, client = _make_mgr(tmp_path, gslc)

    assert _run_curve(mgr)
    assert _run_curve(mgr)
    assert client.transfer.calls == [("set_upload_limit", 5120 * 1024)]


def test_speed_curve_manual_odd_kib_skips_direction(tmp_path):
    """当前限速为正奇数 KiB(如 2001)视为手动 -> 该方向不覆盖, 另一方向照常写"""
    today = date.today()
    dat = _write_dat(tmp_path, [(today, 5 * GIB, 5 * GIB)])
    gslc = _gslc(dat, _pc("day", up=_points(FULL_UPLOAD), down=_points(FULL_DOWNLOAD)))
    mgr, client = _make_mgr(tmp_path, gslc)
    client.transfer.limits["upload_limit"] = 2001 * 1024  # 用户手动 2001KiB/s(奇数)

    assert _run_curve(mgr)
    # 上传方向(目标 6MiB=6144KiB)被跳过; 下载 X=5GiB -> 首档 11MiB=11264KiB 正常写
    assert client.transfer.calls == [("set_download_limit", 11264 * 1024)]
    assert client.transfer.limits["upload_limit"] == 2001 * 1024  # 未被覆盖
    # 偶数手动值(如 2000)不触发保护: 上传正常覆盖
    client.transfer.limits["upload_limit"] = 2000 * 1024
    assert _run_curve(mgr)
    assert client.transfer.limits["upload_limit"] == 6144 * 1024


def test_speed_curve_multi_period_takes_strictest(tmp_path):
    """同方向多条 period 曲线 -> 取最严(最小非零限速)"""
    today = date.today()
    dat = _write_dat(tmp_path, [(today, 15 * GIB, 0)])
    # 1D: X=15GiB >= 10GiB(单点末档) -> 6MiB/s; 7D: X=15GiB < 30GiB -> 2MiB/s(首档覆盖)
    gslc = _gslc(dat, _pc("day", up=_points([(10, 6)])), _pc("7D", up=_points([(30, 2)])))
    mgr, client = _make_mgr(tmp_path, gslc)

    assert _run_curve(mgr)
    # min(6, 2) -> 2MiB/s = 2048KiB/s -> bytes/s
    assert client.transfer.calls == [("set_upload_limit", 2048 * 1024)]


def test_speed_curve_unlimited_target_writes_zero(tmp_path):
    """档位限速为 0(该档不限速)且当前有限速 -> transfer 写 0(bytes/s = 不限速) """
    today = date.today()
    # 今天行缺失(跨天), 但存在历史行使 dat 有效: 今天累计 0 < 10GiB -> 首档 0(不限速)
    dat = _write_dat(tmp_path, [(today - timedelta(days=1), 200 * GIB, 0)])
    gslc = _gslc(dat, _pc("day", up=_points([(10, 0)])))
    mgr, client = _make_mgr(tmp_path, gslc)
    client.transfer.limits["upload_limit"] = 5120 * 1024  # 上一轮旧限速

    assert _run_curve(mgr)
    assert client.transfer.calls == [("set_upload_limit", 0)]


def test_speed_curve_cross_day_rollback(tmp_path):
    """今天行缺失 -> 累计 0 -> 自动放开回落到首档(昨天触发的低速档被放宽)"""
    today = date.today()
    dat = _write_dat(tmp_path, [(today - timedelta(days=1), 200 * GIB, 0)])
    gslc = _gslc(dat, _pc("day", up=_points(FULL_UPLOAD)))
    mgr, client = _make_mgr(tmp_path, gslc)
    client.transfer.limits["upload_limit"] = 512 * 1024  # 昨天触发到 0.5MiB/s(200GiB >= 100GiB)

    assert _run_curve(mgr)
    # 今天累计视为 0 -> 首档 6MiB/s = 6144KiB/s -> bytes/s
    assert client.transfer.calls == [("set_upload_limit", 6144 * 1024)]


def test_speed_curve_dry_run_no_read_no_write(tmp_path):
    """dry_run: 不读当前、不写 qB, 仅记录 state(dry_run=True)"""
    today = date.today()
    dat = _write_dat(tmp_path, [(today, 15 * GIB, 0)])
    gslc = _gslc(dat, _pc("day", up=_points(FULL_UPLOAD)))
    mgr, client = _make_mgr(tmp_path, gslc)

    assert _run_curve(mgr, dry_run=True)
    assert client.transfer.calls == []  # 未读未写
    assert client.transfer.limits["upload_limit"] == 0
    rec = mgr.state["speed_limit_curve"][today.isoformat()]
    assert rec == {"upload_kib": 5120, "download_kib": None, "dry_run": True}


def test_speed_curve_dat_missing_noop(tmp_path):
    """dat 文件缺失 -> warning 本轮不动(任务存活), 不写 qB"""
    gslc = _gslc(str(tmp_path / "not-exist.dat"), _pc("day", up=_points(FULL_UPLOAD)))
    mgr, client = _make_mgr(tmp_path, gslc)
    client.transfer.limits["upload_limit"] = 5120 * 1024

    assert _run_curve(mgr) is True  # 任务保留
    assert client.transfer.calls == []


def test_speed_curve_no_config_noop(tmp_path):
    """未配置曲线(conf None) -> handler 直接返回, 不读文件不写 qB"""
    mgr = make_manager(str(tmp_path / "state.json"))
    client = _fake_client()
    mgr.client = client

    assert _run_curve(mgr) is True
    assert client.transfer.calls == []


def test_speed_curve_dat_all_bad_lines_noop(tmp_path):
    """dat 有文件但无有效记录 -> warning 本轮不动, 既有全局限速保留"""
    p = tmp_path / "garbage.dat"
    p.write_text('garbage line\n2026/13/99 1/2\n', encoding="utf-8")
    gslc = _gslc(str(p), _pc("day", up=_points(FULL_UPLOAD)))
    mgr, client = _make_mgr(tmp_path, gslc)
    client.transfer.limits["upload_limit"] = 5120 * 1024  # 上一轮旧限速

    assert _run_curve(mgr) is True
    assert client.transfer.calls == []
    assert client.transfer.limits["upload_limit"] == 5120 * 1024


def test_speed_curve_dat_bad_lines_still_applies(tmp_path):
    """dat 部分坏行 -> warning 跳过, 有效行仍参与计算并写 qB"""
    today = date.today()
    p = tmp_path / "mixed.dat"
    p.write_text(f'lines: "30"\n{today:%Y/%m/%d} {15 * GIB // 1024}/0\nbroken\n', encoding="utf-8")
    gslc = _gslc(str(p), _pc("day", up=_points(FULL_UPLOAD)))
    mgr, client = _make_mgr(tmp_path, gslc)

    assert _run_curve(mgr)
    # 15GiB -> 5MiB/s; 坏行被跳过不影响有效行
    assert client.transfer.calls == [("set_upload_limit", 5120 * 1024)]


def test_speed_curve_success_logs_period_stats(tmp_path):
    """设置成功时按配置各 period 输出累计上传/下载统计(今日/七日/本月/三十日)

    注: QbManager 构造时 setup_logging 清空 root handlers(caplog 捕获失效),
    故直接给模块 logger 挂 StringIO 捕获 handler。
    """
    import io

    today = date.today()
    dat = _write_dat(tmp_path, [(today, 15 * GIB, 5 * GIB)])
    # day 双向; 7D 仅下载; month/30D 仅上传(覆盖单方向曲线分支与中文两位数标签)
    gslc = _gslc(
        dat,
        _pc("day", up=_points([(10, 6)]), down=_points([(20, 11)])),
        _pc("7D", down=_points([(20, 11)])),
        _pc("month", up=_points([(50, 4)])),
        _pc("30D", up=_points([(50, 4)])),
    )
    mgr, client = _make_mgr(tmp_path, gslc)
    lg = logging.getLogger("auto_qb.mixins.speed_curve")
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setLevel(logging.INFO)
    old_level = lg.level
    lg.setLevel(logging.INFO)  # 模块 logger 无 handlers 时 effective level 取自 root(WARNING), 需显式提升
    lg.addHandler(handler)
    try:
        assert _run_curve(mgr)
    finally:
        lg.removeHandler(handler)
        lg.setLevel(old_level)
    text = buf.getvalue()
    # 上传最严: min(day 6MiB, month 4MiB, 30D 4MiB) = 4MiB/s; 下载: 11MiB/s
    assert client.transfer.calls == [("set_upload_limit", 4 * MIB), ("set_download_limit", 11 * MIB)]
    assert "累计上传/下载" in text
    for label in ("今日", "七日", "本月", "三十日"):
        assert label in text, f"统计日志缺少 {label}: {text}"
    assert "上传限速: 4096KiB/s" in text
    assert "下载限速: 11264KiB/s" in text


def test_speed_curve_format_helpers():
    """日志格式化辅助: 字节可读串 / 中文数字(含两位数) / period 中文标签 / 限速显示"""
    assert _fmt_bytes(0) == "0B"
    assert _fmt_bytes(1024) == "1KiB"
    assert _fmt_bytes(int(1.5 * GIB)) == "1.5GiB"
    assert _fmt_bytes(60 * GIB) == "60GiB"
    assert _fmt_bytes(3 * 1024**4) == "3TiB"
    assert _cn_number(0) == "零"
    assert _cn_number(7) == "七"
    assert _cn_number(9) == "九"
    assert _cn_number(10) == "一十"  # 源码不省略十位一
    assert _cn_number(12) == "一十二"
    assert _cn_number(30) == "三十"
    assert _cn_number(99) == "九十九"
    assert _period_label("day") == "今日"
    assert _period_label("month") == "本月"
    assert _period_label("7D") == "七日"
    assert _period_label("30D") == "三十日"
    assert _period_label("120D") == "120日"
    assert _fmt_global_limit(None) == "不限速"
    assert _fmt_global_limit(0) == "不限速"
    assert _fmt_global_limit(5120) == "5120KiB/s"


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
