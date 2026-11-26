"""test_speed_curve_dispatch 测试计划: 全局限速曲线(Traffic Monitor 接入 qB 全局速度限制)

## 测试计划(每个测试函数一条)
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
- test_speed_curve_enabled_false_short_circuits: enabled=False -> 任务仍注册但短路, 不读 dat 不写 qB, 发布 disabled
- test_speed_curve_source_off_publishes_nothing: 数据来源总开关关(S1/D1; A4) -> 曲线任务不发布任何东西
  (来源态归 traffic_snapshot), 不读 dat 不写 qB
- test_speed_curve_dat_all_bad_lines_noop: dat 有文件但全坏行 -> 本轮不动
- test_speed_curve_dat_bad_lines_still_applies: dat 部分坏行 -> 跳过坏行仍写 qB
- test_speed_curve_success_logs_period_stats: 设置成功按各 period 输出累计上传/下载(今日/七日/本月/三十日)
- test_speed_curve_format_helpers: 日志格式化辅助(_fmt_bytes/_cn_number/_period_label/_fmt_global_limit)
- test_speed_curve_manual_log_throttled_same_state: 手动保护同状态逐轮不刷屏(仅首轮 INFO, 次轮降 DEBUG)
- test_speed_curve_manual_log_periodic_reminder_and_value_change: 超周期提醒一次 / 手动值变化立即重报
- test_speed_curve_manual_log_resets_after_release: 退出手动保护后清记忆, 再次进入重新报
- test_speed_curve_readback_failure_degrades_actual
- test_speed_curve_require_snapshot_missing_fails_fast
"""

import copy

import io

import logging

import os

from datetime import date, timedelta

import pytest

import yaml

from auto_qb.core import curves

from clock import FakeClock

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


# ---------- 集成: 任务注册 / handler ----------
def test_speed_curve_global_task_registered(tmp_path):
    """配置存在 -> _create_global_tasks 创建 speed_limit_curve 任务(interval 缺省回退主 interval)

    26-10-18-0813 起队列里**还**有一条 traffic_snapshot_refresh(来源侧节奏, 与曲线解绑);
    本用例只锁曲线那一条 —— 两条并存正是解耦的形态。
    """
    gslc = _gslc("whatever.dat", _pc("day", up=_points(FULL_UPLOAD)))
    mgr, _ = _make_mgr(tmp_path, gslc)
    mgr._create_global_tasks()
    assert [t.name for t in mgr.task_queue._fast if t.name.startswith("speed_")] == ["speed_limit_curve"]
    assert mgr.task_queue.named("speed_limit_curve").interval == mgr.config.interval  # FakeConfig.interval = 60
    assert mgr.task_queue.named("traffic_snapshot_refresh") is not None


def test_speed_curve_global_task_uses_own_interval(tmp_path):
    """曲线配置 interval -> 任务使用专属间隔, 不跟随主 interval"""
    gslc = _gslc("whatever.dat", _pc("day", up=_points(FULL_UPLOAD)), interval=600)
    mgr, _ = _make_mgr(tmp_path, gslc)
    mgr._create_global_tasks()
    assert mgr.task_queue.named("speed_limit_curve").interval == 600
    # 曲线节奏与来源节奏互不影响: 来源仍是自己的缺省 600s(models 默认), 不跟曲线走
    assert mgr.task_queue.named("traffic_snapshot_refresh") is not None


def test_speed_curve_global_task_not_registered(tmp_path):
    """未配置曲线 -> 不创建任务(即使有 delete_tags 之外的全局任务也不含曲线任务)"""
    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.client = FakeClient()
    mgr._create_global_tasks()
    assert all(t.name != "speed_limit_curve" for t in mgr.task_queue._fast)


def test_speed_curve_applies_staged_upload_limit(tmp_path):
    """今天行流量命中档位 -> transfer_set_upload_limit 写入对应 bytes/s(只管理配置了的方向) """
    today = date.today()
    dat = write_dat(tmp_path, [(today, 15 * GIB, 5 * GIB)])
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
    dat = write_dat(tmp_path, [(today, 15 * GIB, 0)])
    gslc = _gslc(dat, _pc("day", up=_points(FULL_UPLOAD)))
    mgr, client = _make_mgr(tmp_path, gslc)

    assert _run_curve(mgr)
    assert _run_curve(mgr)
    assert client.transfer.calls == [("set_upload_limit", 5120 * 1024)]


def test_speed_curve_manual_odd_kib_skips_direction(tmp_path):
    """当前限速为正奇数 KiB(如 2001)视为手动 -> 该方向不覆盖, 另一方向照常写"""
    today = date.today()
    dat = write_dat(tmp_path, [(today, 5 * GIB, 5 * GIB)])
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
    dat = write_dat(tmp_path, [(today, 15 * GIB, 0)])
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
    dat = write_dat(tmp_path, [(today - timedelta(days=1), 200 * GIB, 0)])
    gslc = _gslc(dat, _pc("day", up=_points([(10, 0)])))
    mgr, client = _make_mgr(tmp_path, gslc)
    client.transfer.limits["upload_limit"] = 5120 * 1024  # 上一轮旧限速

    assert _run_curve(mgr)
    assert client.transfer.calls == [("set_upload_limit", 0)]


def test_speed_curve_cross_day_rollback(tmp_path):
    """今天行缺失 -> 累计 0 -> 自动放开回落到首档(昨天触发的低速档被放宽)"""
    today = date.today()
    dat = write_dat(tmp_path, [(today - timedelta(days=1), 200 * GIB, 0)])
    gslc = _gslc(dat, _pc("day", up=_points(FULL_UPLOAD)))
    mgr, client = _make_mgr(tmp_path, gslc)
    client.transfer.limits["upload_limit"] = 512 * 1024  # 昨天触发到 0.5MiB/s(200GiB >= 100GiB)

    assert _run_curve(mgr)
    # 今天累计视为 0 -> 首档 6MiB/s = 6144KiB/s -> bytes/s
    assert client.transfer.calls == [("set_upload_limit", 6144 * 1024)]


def test_speed_curve_dry_run_no_read_no_write(tmp_path):
    """dry_run: 不读当前、不写 qB, 仅记录 state(dry_run=True)"""
    today = date.today()
    dat = write_dat(tmp_path, [(today, 15 * GIB, 0)])
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


def test_speed_curve_enabled_false_short_circuits(tmp_path):
    """enabled=False: 曲线任务仍注册但整体短路 -> 不读 dat 不写 qB, limit 段落 disabled(Web 视为未启用)"""
    gslc = _gslc(write_dat(tmp_path, [(date.today(), 15 * GIB, 0)]), _pc("day", up=_points(FULL_UPLOAD)))
    gslc.curve.enabled = False  # 数据可用, 证明短路先于读数据
    mgr, client = _make_mgr(tmp_path, gslc)
    client.transfer.limits["upload_limit"] = 999 * 1024  # 当前非目标值: 若未短路将被改写

    # 任务仍注册(enabled=False 只在 handler 内短路, 不影响任务创建)
    mgr._create_global_tasks()
    assert [t.name for t in mgr.task_queue._fast if t.name.startswith("speed_")] == ["speed_limit_curve"]

    assert _run_curve(mgr) is True
    assert client.transfer.calls == []  # 不动 qB 限速
    assert client.transfer.limits["upload_limit"] == 999 * 1024
    assert "speed_limit_curve" not in mgr.state  # 不记录曲线 state
    # 派生 state 仍是 disabled(来源段 ok + limit 段 disabled), Web 端据此渲染为未启用
    assert mgr.web.traffic_view["state"] == "disabled"
    assert mgr.web.traffic_view["limit"]["state"] == "disabled"


def test_speed_curve_source_off_publishes_nothing(tmp_path):
    """数据来源总开关关(S1/D1; A4 收窄): 曲线任务**不发布任何东西**, 直接让位

    曲线功能本身仍启用, 停的是 traffic_source.enabled。来源态(off)归 traffic_snapshot:
    它有自己的节奏, 关源时由它发 off 快照(配置一保存还会立刻触发一次), 曲线任务抢这个判定
    只会让"谁写 state"变成两个作者 —— 所以这里断言的是"快照一字未动"。
    """
    today = date.today()
    gslc = _gslc(write_dat(tmp_path, [(today, 15 * GIB, 0)]), _pc("day", up=_points(FULL_UPLOAD)))
    mgr, client = _make_mgr(tmp_path, gslc)
    mgr.config.traffic_source.enabled = False  # 数据可用, 证明短路先于读数据
    client.transfer.limits["upload_limit"] = 888 * 1024  # 偶数非目标值: 若未短路将被改写
    before = copy.deepcopy(mgr.web.traffic_view)

    assert _run_curve(mgr) is True
    assert client.transfer.calls == []  # 不动 qB 限速
    assert client.transfer.limits["upload_limit"] == 888 * 1024
    assert "speed_limit_curve" not in mgr.state  # 不记录曲线 state
    assert mgr.web.traffic_view == before, "关源时曲线任务不得发布任何东西(A4)"

    # 开回来自动恢复: 下一轮正常读数写限速(无需重配曲线)
    mgr.config.traffic_source.enabled = True
    assert _run_curve(mgr) is True
    assert client.transfer.calls == [("set_upload_limit", 5120 * 1024)]
    assert mgr.web.traffic_view["limit"]["state"] == "ok"
    assert mgr.web.traffic_view["state"] == "ok"


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
    dat = write_dat(tmp_path, [(today, 15 * GIB, 5 * GIB)])
    # day 双向; 7D 仅下载; month/30D 仅上传(覆盖单方向曲线分支与中文两位数标签)
    gslc = _gslc(
        dat,
        _pc("day", up=_points([(10, 6)]), down=_points([(20, 11)])),
        _pc("7D", down=_points([(20, 11)])),
        _pc("month", up=_points([(50, 4)])),
        _pc("30D", up=_points([(50, 4)])),
    )
    mgr, client = _make_mgr(tmp_path, gslc)
    lg = logging.getLogger("auto_qb.core.modules.speed_curve_mod")
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
    assert _fmt_bytes(1023) == "1023B"
    assert _fmt_bytes(1024) == "1KiB"
    assert _fmt_bytes(int(1.5 * GIB)) == "1.5GiB"
    assert _fmt_bytes(int(1.25 * GIB)) == "1.25GiB"  # 两位小数必须保留(非整值不是 .1f)
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
    assert _period_label("99D") == "九十九日"
    assert _period_label("100D") == "100日"  # >=100 直接落数字(与 99D 卡边界)
    assert _period_label("120D") == "120日"
    assert _fmt_global_limit(None) == "不限速"
    assert _fmt_global_limit(0) == "不限速"
    assert _fmt_global_limit(1) == "1KiB/s"
    assert _fmt_global_limit(5120) == "5120KiB/s"


# ---------- 手动保护的日志节流(持续状态不逐轮刷屏) ----------
def test_speed_curve_manual_log_throttled_same_state(tmp_path):
    """手动保护同状态逐轮不刷屏: 首轮每方向一条 INFO, 次轮降 DEBUG(但快照 reasons 照旧)"""
    today = date.today()
    dat = write_dat(tmp_path, [(today, 5 * GIB, 5 * GIB)])
    gslc = _gslc(dat, _pc("day", up=_points(FULL_UPLOAD), down=_points(FULL_DOWNLOAD)))
    mgr, client = _make_mgr(tmp_path, gslc)
    client.transfer.limits["upload_limit"] = 2001 * 1024  # 奇数: 手动
    client.transfer.limits["download_limit"] = 10265 * 1024  # 奇数: 手动(用户实报的值)

    with capture_logs("auto_qb.core.modules.speed_curve_mod") as cap:
        assert _run_curve(mgr)
        assert cap.text.count("本轮不覆盖") == 2  # 上传 + 下载 各一条
        assert _run_curve(mgr)
        assert cap.text.count("本轮不覆盖") == 2  # 同状态第二轮不再记 INFO
        assert "同状态不重复记" in cap.text  # 降 DEBUG: 排障仍看得见每轮在等什么

    assert client.transfer.calls == []  # 两方向都被保护, 一次都不写
    # 去重不丢信号: Web UI 快照的 reasons 照旧逐轮带 code=manual(前端锁图标的数据源)
    assert [r["code"] for r in mgr.web.traffic_view["limit"]["reasons"]] == ["manual", "manual"]


def test_speed_curve_manual_log_periodic_reminder_and_value_change(tmp_path):
    """超 _MANUAL_REMIND_GAP 再提醒一次; 手动值变化(仍是奇数)立即重报, 不等周期"""
    today = date.today()
    dat = write_dat(tmp_path, [(today, 5 * GIB, 0)])
    gslc = _gslc(dat, _pc("day", up=_points(FULL_UPLOAD)))
    # 构造期注入(S3 收敛: 不再经模块 time 名 patch stdlib; speed_curve 经装配链收 _clock)
    clock = FakeClock(start=1_000_000.0)
    mgr, client = _make_mgr(tmp_path, gslc, clock=clock)
    client.transfer.limits["upload_limit"] = 2001 * 1024

    with capture_logs("auto_qb.core.modules.speed_curve_mod") as cap:
        assert _run_curve(mgr)
        assert cap.text.count("本轮不覆盖") == 1  # 首次进入该状态 -> 说明白一次
        clock.advance(61.0)  # 远小于提醒周期
        assert _run_curve(mgr)
        assert cap.text.count("本轮不覆盖") == 1  # 同状态不重复
        # 恰好整周期(不是"越过"): >= 边界必须再提醒一次(改成 > 就会吞掉这一轮)
        clock.freeze(1_000_000.0 + _MANUAL_REMIND_GAP)
        assert _run_curve(mgr)
        assert cap.text.count("本轮不覆盖") == 2
        # 手动值变化(2001 -> 2003, 仍是奇数): 状态指纹变了 -> 立即重报
        client.transfer.limits["upload_limit"] = 2003 * 1024
        assert _run_curve(mgr)
        assert cap.text.count("本轮不覆盖") == 3
        assert "2003KiB/s" in cap.text


def test_speed_curve_manual_log_resets_after_release(tmp_path):
    """退出手动保护(改成偶数被正常覆盖)后清记忆 -> 再次进入手动状态重新报一条"""
    today = date.today()
    dat = write_dat(tmp_path, [(today, 5 * GIB, 0)])
    gslc = _gslc(dat, _pc("day", up=_points(FULL_UPLOAD)))
    mgr, client = _make_mgr(tmp_path, gslc)
    client.transfer.limits["upload_limit"] = 2001 * 1024

    with capture_logs("auto_qb.core.modules.speed_curve_mod") as cap:
        assert _run_curve(mgr)
        assert cap.text.count("本轮不覆盖") == 1
        curve_mod = mgr.host.get("speed_curve")
        assert "up" in curve_mod._curve_manual_log  # 节流记忆已建立(状态在模块实例, plan P3)
        assert _run_curve(mgr)
        assert cap.text.count("本轮不覆盖") == 1  # 同状态不重复

        # 用户取消手动(改成偶数) -> 曲线接管并清记忆
        client.transfer.limits["upload_limit"] = 2000 * 1024
        assert _run_curve(mgr)
        assert client.transfer.limits["upload_limit"] == 6144 * 1024  # 5GiB -> 首档 6MiB/s
        assert "up" not in curve_mod._curve_manual_log
        assert cap.text.count("本轮不覆盖") == 1  # 释放本身不额外刷日志(可见性由"设置全局限速"那条承载)

        # 再次手动设置(奇数) -> 重新说明白
        client.transfer.limits["upload_limit"] = 2001 * 1024
        assert _run_curve(mgr)
        assert cap.text.count("本轮不覆盖") == 2


def test_speed_curve_require_snapshot_missing_fails_fast(tmp_path):
    """装配清单缺项(traffic_snapshot 未挂) -> `_require_snapshot` fail-fast RuntimeError

    段级写只许经快照模块句柄(黄金法则 4: 装配错必须当场炸, 不许静默降级成"限速生效但界面
    永远不更新")。报错文案要指路到装配序(TrafficSnapshotModule 必须注册在 SpeedCurveModule 之前)。
    """
    today = date.today()
    dat = write_dat(tmp_path, [(today, 15 * GIB, 0)])
    gslc = _gslc(dat, _pc("day", up=_points([(10, 6)])))
    mgr, client = _make_mgr(tmp_path, gslc)
    mod = mgr.host.get("speed_curve")
    original = mod._ctx.traffic_snapshot
    mod._ctx.traffic_snapshot = None
    try:
        with pytest.raises(RuntimeError, match="traffic_snapshot"):
            mod._require_snapshot()
    finally:
        mod._ctx.traffic_snapshot = original


def test_speed_curve_readback_failure_degrades_actual(tmp_path, monkeypatch):
    """写后回读失败: 写入照样算成功, actual 退化为写前读数并附 read_failed 原因

    回读只是展示用的"实际生效值"; qB 回读失败(重启中/API 抖动)绝不能把已写入的限速回滚,
    也不能让本轮整体判失败 —— 前端靠 reasons 里的 read_failed 说明"实际值未知"。
    """
    today = date.today()
    dat = write_dat(tmp_path, [(today, 15 * GIB, 0)])
    gslc = _gslc(dat, _pc("day", up=_points([(10, 6)])))
    mgr, client = _make_mgr(tmp_path, gslc)

    api = mgr.host.get("speed_curve")._ctx.api
    real_read = api.get_global_speed_limits
    reads = {"n": 0}

    def _flaky_read():
        reads["n"] += 1
        if reads["n"] == 1:
            return real_read()  # 写前读数照常(本轮决策要用)
        raise OSError("qB 回读失败")

    monkeypatch.setattr(api, "get_global_speed_limits", _flaky_read)
    assert _run_curve(mgr)
    assert client.transfer.calls == [("set_upload_limit", 6 * 1024 * 1024)], "回读失败不影响已写入的限速"
    tv = mgr.web.traffic_view
    # 完整键面 + 文案 pin: 前端靠 reasons 说明"实际值未知", dir 为空表示非单一方向
    assert tv["limit"]["reasons"] == [
        {
            "dir": "",
            "code": "read_failed",
            "text": "回读实际限速失败: qB 回读失败"
        },
    ]
    assert tv["limit"]["actual"]["up"] == 0, "actual 退化为写前读数"
