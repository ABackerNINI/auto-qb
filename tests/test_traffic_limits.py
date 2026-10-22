"""test_traffic_limits 测试计划: qB 全局限速历史(plan 26-10-12-0535 W1 后端)

## 测试计划(每个测试函数一条)
- test_parse_limits_day_text_and_torn_tail: 解析纯函数 —— 3 列 CSV 逐行复原 / 坏行(列数/非数值/负数)整行豁免 / 注释空行跳过 / 撕裂尾半行丢弃 / 空文本空元组
- test_limits_day_path_validates_date: 路径单点 —— 非法日期(形状/2月30)fail-fast, 合法路径落 qb-traffic-v4/limits/
- test_recorder_change_only_appends: 事件语义 D2 —— 值不变零写入, 变化才追加一行(含 0 = 不限速的合法事件), 字段未知不记不推进
- test_recorder_midnight_carry: 00:00 硬切 + 基线 carry D3 —— 新天首行无条件写上一生效值(值没变也写), 此后同值零追加
- test_recorder_restart_dedup: 重启去重 —— 新记录器首轮与当日文件末条相同则跳过, 不同写事件; 失败轮不推进基线(下一轮重试)
- test_recorder_oserror_degrade: 失败降级 —— 追加 OSError 只 WARNING(节流)不上抛, 基线不推进, 恢复后事件补上
- test_recorder_dry_run_silent: dry_run persistence_on=False 零文件零状态推进(恢复真实运行后由重启去重口径对齐)
- test_recorder_patological_flip_guard: 病态翻转护栏 —— 单天事件超常量阈值只告警照记(节流), 数据不删
- test_recorder_warn_first_fire_on_fresh_boot: 节流哨兵回归 —— monotonic() 起点=开机时刻, 开机时长 < 节流间隔(3600s)时两处首次告警仍必须发出(0.0 哨兵会吞掉首次告警)
- test_limits_cache_stat_keyed: 解析缓存 —— mtime+size 键控命中零重解析(解析函数替换探针), 追加后失效重解析, 缺失文件恒 () 零 open
- test_limits_cache_no_data_dir_and_open_oserror: 读侧降级 —— data_dir 空恒 () 零 IO; 读天文件 OSError(权限/竞态)按缺失处理不上抛(观测面缺一文件 = 事件缺口)
- test_limits_cache_evicts_oldest: 缓存上限治理 —— 条目超 _LIMITS_CACHE_MAX_ENTRIES 丢最旧(LRU), 重读被丢的天触发重解析(不常驻内存)
- test_events_for_window_empty_when_reversed: 装配入口闸 —— t1 <= t0(空窗/反窗) 恒 [] 零读盘
- test_events_for_window_breaks_at_window_end_and_pick_limit: 窗口右界 break + _pick_limit 取值口径
- test_events_for_window_synthetic_first_and_dedup: 读侧装配 D3″/D5 —— 合成首事件(<= t0 最近值, 窗首前一天的 carry 窥得到) / 同值连续事件去重 / 记录起点晚于窗口起点不合成 / 无记录空表 / 跨天文件拼接
- test_api_payload_limits_shape_and_same_source: payload 契约 D3″ —— 三端点响应恒带 limits 且同源同值(组/单种不另读文件), 空态未启用也恒在(= [])
- test_module_wiring_sample_global_observes: 采样模块接线守阵 —— _sample_global 调 SpeedLimitRecorder.observe(真实模块实例 + 替身 server_state 触发落盘), dry_run 轮零写入
- test_recorder_append_fail_arcs_bootstrap_and_throttle
"""
import logging
import os
import time

import pytest

from auto_qb.core.traffic_limits import (
    LIMITS_DIR_NAME,
    SpeedLimitRecorder,
    limits_day_path,
    limits_events_for_window,
    parse_limits_day_text,
)
from auto_qb.core.traffic_limits import LimitsCache
from auto_qb.core.traffic_store import v4_day_epoch, v4_epoch_date_str


def _state(up, down):
    return {"up_rate_limit": up, "dl_rate_limit": down}


def _read_day(data_dir, date_str):
    with open(limits_day_path(data_dir, date_str), encoding="utf-8") as f:
        return f.read()


def _write_day(data_dir, date_str, text):
    """测试侧直接写天文件(建父目录 + 覆盖写)"""
    p = limits_day_path(data_dir, date_str)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)


def _anchored_ts() -> int:
    """用例时间原点 = **本地当日正午**, 替代裸 `int(time.time())`

    坑史(issue 26-10-19-0013): 起点取真实此刻, 用例里 ts+30/60/120 的推进跨到本地零点时,
    按日文件随即分家 —— `_read_day(date)` 读的是起点那天, 新事件却落进了次日文件,
    23:59-00:00 之间跑全量必红 4 条(与本轮改动零交集)。
    锚到当日 12:00: 前后各 12h 余量, 本文件最大跨度(+90030s≈25h)仍吃得下,
    既有「跨日 carry / 同日零追加 / 按天护栏」语义一条不变。
    口径单点 `v4_day_epoch` = 本地自然日零点, 与 `v4_epoch_date_str` 同源。

    例外: 依赖**真实此刻**收边的窗口查询用例(test_api_payload_limits_shape_and_same_source)
    必须留在真钟上 —— 那里的 24h 窗口由服务端按真实 now 取尾。
    """
    return v4_day_epoch(time.time()) + 12 * 3600


def test_parse_limits_day_text_and_torn_tail():
    """解析纯函数: 逐行复原 / 坏行整行豁免 / 撕裂尾丢弃 / 注释空行跳过"""
    assert parse_limits_day_text("") == ()
    text = (
        "# 手写注释\n"
        "\n"
        "100,1048576,2097152\n"
        "200,0,2097152\n"
        "bad-line\n"
        "300,1,2,3\n"  # 列数错
        "400,-1,0\n"  # 负数
        "abc,0,0\n"  # 非数值
        "500,42,"  # 撕裂尾(无换行)
    )
    assert parse_limits_day_text(text) == (
        (100, 1048576, 2097152),
        (200, 0, 2097152),
    )


def test_limits_day_path_validates_date(tmp_path):
    """路径单点: 非法日期 fail-fast; 合法日期落 qb-traffic-v4/limits/<日期>.dat"""
    for bad in ("2026-02-30", "26-10-12", "", "2026/10/12", "2026-10-12 "):
        with pytest.raises(ValueError):
            limits_day_path(str(tmp_path), bad)
    p = limits_day_path(str(tmp_path), "2026-10-12")
    assert os.path.normpath(p) == os.path.normpath(
        os.path.join(str(tmp_path), "qb-traffic-v4", LIMITS_DIR_NAME, "2026-10-12.dat")
    )


def test_recorder_change_only_appends(tmp_path):
    """D2 事件语义: 值不变零写入; 变化才追加; 0 = 不限速合法事件; 字段未知不记不推进"""
    data_dir = str(tmp_path)
    rec = SpeedLimitRecorder(data_dir)
    ts = _anchored_ts()
    rec.observe(_state(1024, 2048), ts)  # 首轮: 立基线 + 首事件
    date = v4_epoch_date_str(ts)
    assert _read_day(data_dir, date).count("\n") == 1
    rec.observe(_state(1024, 2048), ts + 30)  # 不变: 零追加
    assert _read_day(data_dir, date).count("\n") == 1
    rec.observe(_state(0, 2048), ts + 60)  # 上行改不限速(0): 合法事件
    assert _read_day(data_dir, date).count("\n") == 2
    assert _read_day(data_dir, date).splitlines()[-1] == f"{ts + 60},0,2048"
    rec.observe(_state(None, 2048), ts + 90)  # 字段未知: 不记不推进
    assert _read_day(data_dir, date).count("\n") == 2
    rec.observe(_state(4096, 2048), ts + 120)  # 恢复已知: 正常事件
    assert _read_day(data_dir, date).count("\n") == 3


def test_recorder_midnight_carry(tmp_path):
    """D3 00:00 硬切 + 基线 carry: 新天首行无条件写上一生效值(值没变也写), 同值继续零追加"""
    data_dir = str(tmp_path)
    rec = SpeedLimitRecorder(data_dir)
    ts = _anchored_ts()
    d1 = v4_epoch_date_str(ts)
    rec.observe(_state(1024, 2048), ts)
    rec.observe(_state(1024, 2048), ts + 30)  # 同日不变: 零追加
    assert _read_day(data_dir, d1).count("\n") == 1
    # 次日(值没变): carry 行无条件写
    rec.observe(_state(1024, 2048), ts + 90000)
    d2 = v4_epoch_date_str(ts + 90000)
    assert d2 != d1
    assert _read_day(data_dir, d2) == f"{ts + 90000},1024,2048\n"
    # carry 后同值继续零追加
    rec.observe(_state(1024, 2048), ts + 90030)
    assert _read_day(data_dir, d2) == f"{ts + 90000},1024,2048\n"


def test_recorder_restart_dedup(tmp_path):
    """重启去重: 首轮与当日文件末条相同则跳过(不产生假事件); 不同写事件"""
    data_dir = str(tmp_path)
    ts = _anchored_ts()
    date = v4_epoch_date_str(ts)
    r1 = SpeedLimitRecorder(data_dir)
    r1.observe(_state(1024, 2048), ts)
    r1.observe(_state(0, 4096), ts + 30)
    tail = _read_day(data_dir, date).splitlines()[-1]  # = ts+30,0,4096
    # 重启: 首轮值与末条相同 -> 去重跳过
    r2 = SpeedLimitRecorder(data_dir)
    r2.observe(_state(0, 4096), ts + 60)
    assert tail == f"{ts + 30},0,4096" and _read_day(data_dir, date).splitlines()[-1] == tail
    # 重启: 首轮值不同 -> 正常事件
    r3 = SpeedLimitRecorder(data_dir)
    r3.observe(_state(8192, 4096), ts + 90)
    assert _read_day(data_dir, date).splitlines()[-1] == f"{ts + 90},8192,4096"


def test_recorder_oserror_degrade(tmp_path, caplog):
    """失败降级: 追加 OSError WARNING 节流不上抛; 基线不推进, 恢复后事件补上"""
    data_dir = str(tmp_path)
    rec = SpeedLimitRecorder(data_dir)
    ts = _anchored_ts()
    date = v4_epoch_date_str(ts)
    rec.observe(_state(1024, 2048), ts)
    # 破坏目录: 让追加失败(makedirs 复现用文件占位)
    path = limits_day_path(data_dir, date)
    with caplog.at_level(logging.WARNING, logger="auto_qb.core.traffic_limits"):
        import builtins

        real_open = builtins.open
        try:
            builtins.open = lambda *a, **k: (_ for _ in ()).throw(OSError("disk gone"))
            rec.observe(_state(0, 0), ts + 30)  # 失败轮: 不上抛, 基线不推进
        finally:
            builtins.open = real_open
        rec.observe(_state(0, 0), ts + 60)  # 恢复: 补上事件(值没丢)
    assert any("追加失败" in r.message for r in caplog.records)
    lines = _read_day(data_dir, date).splitlines()
    assert lines[-1] == f"{ts + 60},0,0"  # 失败轮 30s 的变化在 60s 恢复轮补上


def test_recorder_dry_run_silent(tmp_path):
    """dry_run: persistence_on=False 零文件零落盘(与采样器 dry_run 同门)"""
    data_dir = str(tmp_path)
    rec = SpeedLimitRecorder(data_dir)
    ts = _anchored_ts()
    rec.observe(_state(1024, 2048), ts, persistence_on=False)
    assert not os.path.exists(os.path.join(str(tmp_path), "qb-traffic-v4", LIMITS_DIR_NAME))


def test_recorder_patological_flip_guard(tmp_path, caplog):
    """病态翻转护栏: 单天事件超阈值只告警照记(节流 1h), 数据不删"""
    data_dir = str(tmp_path)
    rec = SpeedLimitRecorder(data_dir)
    # 固定同一天内: 循环 ts+i(i 到阈值+30) 跨本地零点即把 _day_events 清零(按天护栏语义,
    # 生产正确), 2000 阈值永不达 —— 2030s 跨度必须落在同一自然日(锚点见 _anchored_ts)。
    ts = _anchored_ts()
    date = v4_epoch_date_str(ts)
    from auto_qb.core import traffic_limits as tl

    with caplog.at_level(logging.WARNING, logger="auto_qb.core.traffic_limits"):
        for i in range(tl._LIMITS_DAILY_EVENT_WARN + 30):
            rec.observe(_state(1024 + (i % 2), 2048), ts + i)
    assert any("超常" in r.message for r in caplog.records)
    assert _read_day(data_dir, date).count("\n") == tl._LIMITS_DAILY_EVENT_WARN + 30  # 照记


def test_recorder_warn_first_fire_on_fresh_boot(tmp_path, caplog, monkeypatch):
    """节流哨兵回归: monotonic() 起点 = 机器开机时刻(Linux CLOCK_MONOTONIC), 刚开机的
    机器上 monotonic() 可小于节流间隔(3600s) —— 此时两处**首次**告警仍必须发出。

    用 0.0 当「从未告警」哨兵会让 `now - 0.0 >= 3600` 判假, 首次告警被静默吞掉(本机
    uptime > 1h 时看不出来, 只有 CI 全新 VM 会红)。哨兵须为「从未告警」语义(None)。
    """
    from auto_qb.core import traffic_limits as tl

    monkeypatch.setattr(tl.time, "monotonic", lambda: 120.0)  # 模拟开机 2 分钟: < 3600
    data_dir = str(tmp_path)
    # 固定同一天内(场景 B 病态翻转循环 ts+i 跨零点即把 _day_events 清零, 2000 阈值永不达)
    ts = _anchored_ts()  # 同一自然日内(_anchored_ts)
    with caplog.at_level(logging.WARNING, logger="auto_qb.core.traffic_limits"):
        # 场景 A: 追加失败告警
        rec = tl.SpeedLimitRecorder(data_dir)
        rec.observe(_state(1024, 2048), ts)
        import builtins

        real_open = builtins.open
        try:
            builtins.open = lambda *a, **k: (_ for _ in ()).throw(OSError("disk gone"))
            rec.observe(_state(0, 0), ts + 30)
        finally:
            builtins.open = real_open
        # 场景 B: 病态翻转护栏告警
        rec2 = tl.SpeedLimitRecorder(str(tmp_path / "guard"))
        for i in range(tl._LIMITS_DAILY_EVENT_WARN + 5):
            rec2.observe(_state(1024 + (i % 2), 2048), ts + i)
    msgs = [r.message for r in caplog.records]
    assert any("追加失败" in m for m in msgs)
    assert any("超常" in m for m in msgs)


def test_limits_cache_stat_keyed(tmp_path, monkeypatch):
    """解析缓存: mtime+size 键控命中零重解析; 追加(必变 size)失效重解析; 缺失恒 () 零 open"""
    data_dir = str(tmp_path)
    cache = LimitsCache(data_dir)
    ts = _anchored_ts()
    date = v4_epoch_date_str(ts)
    assert cache.read_day(date) == ()  # 缺失: 空
    _write_day(data_dir, date, f"{ts},1024,2048\n")
    path = limits_day_path(data_dir, date)
    calls = {"n": 0}
    real_parse = parse_limits_day_text

    def spy(text):
        calls["n"] += 1
        return real_parse(text)

    monkeypatch.setattr("auto_qb.core.traffic_limits.parse_limits_day_text", spy)
    assert cache.read_day(date) == ((ts, 1024, 2048), )
    assert calls["n"] == 1
    assert cache.read_day(date) == ((ts, 1024, 2048), )  # 命中: 零重解析
    assert calls["n"] == 1
    # 任何 stat 变化(mtime/size 任一)都失效 —— 键是指纹不是变更类型判别器(对齐 V4DayCache;
    # 不变式靠写侧保证: 追加必同时变两者), 此处只钉「没变命中 / 变了重解析」两头
    assert cache.read_day(date) == ((ts, 1024, 2048), )  # 未动: 命中零重解析
    assert calls["n"] == 1
    _write_day(data_dir, date, f"{ts},1024,2048\n{ts + 30},0,2048\n")  # 覆盖写: size 变 -> 失效重解析
    assert cache.read_day(date) == ((ts, 1024, 2048), (ts + 30, 0, 2048))
    assert calls["n"] == 2


def test_events_for_window_synthetic_first_and_dedup(tmp_path):
    """D3″/D5 读侧装配: 合成首事件 / 窗首前一天 carry 窥得到 / 同值去重 / 起点晚于窗口不合成 / 跨天拼接"""
    data_dir = str(tmp_path)
    cache = LimitsCache(data_dir)
    now = _anchored_ts()
    today = v4_epoch_date_str(now)
    yest = v4_epoch_date_str(now - 86400)
    # 场景 1: 无任何记录 -> 空表
    assert limits_events_for_window(cache, now - 3600, now) == []
    # 场景 2: 记录起点在窗口内(首事件 30 分钟前) -> 不合成, 从首事件开始
    _write_day(data_dir, today, f"{now - 1800},1024,2048\n{now - 900},0,2048\n")
    ev = limits_events_for_window(cache, now - 3600, now)
    assert ev == [[now - 1800, 1024, 2048], [now - 900, 0, 2048]]
    # 场景 3: 记录起点早于窗口起点 -> 合成首事件(<= t0 最近值, ts = t0) + 窗内事件
    t0 = now - 600
    _write_day(data_dir, today, f"{now - 7200},1024,2048\n{now - 7200},1024,2048\n{now - 300},0,4096\n")
    cache2 = LimitsCache(data_dir)  # 新缓存避开同进程 stat 缓存噪声
    ev = limits_events_for_window(cache2, t0, now)
    assert ev == [[t0, 1024, 2048], [now - 300, 0, 4096]]
    # 场景 4: <= t0 的最近事件在前一天文件末行(跨天 carry) -> 窥前文件合成
    # (today 文件重置为只有窗内事件, 昨日末行 = t0 前最近值)
    _write_day(data_dir, today, f"{now - 300},0,4096\n")
    _write_day(data_dir, yest, f"{now - 86400},512,512\n{now - 7300},333,444\n")
    ev = limits_events_for_window(cache2, t0, now)
    assert ev == [[t0, 333, 444], [now - 300, 0, 4096]]
    # 场景 5: 同值连续事件(窗内事件与合成值相同)去重 —— 段边界只在真实变化处
    _write_day(data_dir, yest, f"{now - 86400},512,512\n")
    _write_day(data_dir, today, f"{now - 400},512,512\n{now - 300},0,4096\n")
    ev = limits_events_for_window(cache2, t0, now)
    assert ev == [[t0, 512, 512], [now - 300, 0, 4096]]  # now-400 的同值事件不重复出段
    # 场景 6: 跨天拼接升序(昨文件在 t0 前仍有事件, 合成取其末)
    _write_day(data_dir, yest, f"{now - 86400},512,512\n{now - 60000},256,256\n")
    _write_day(data_dir, today, f"{now - 300},0,4096\n")
    ev = limits_events_for_window(cache2, t0, now)
    assert ev == [[t0, 256, 256], [now - 300, 0, 4096]]


def test_api_payload_limits_shape_and_same_source(web_env, monkeypatch):
    """D3″ payload 契约: 三端点响应恒带 limits 且三作用域同值(同源); 未启用空态恒 []"""
    from webui_helpers import _enable_qb_traffic

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    _enable_qb_traffic(mgr)
    now = int(time.time())  # 刻意留在真钟: 端点 window=24h 由服务端按真实此刻收边(见 _anchored_ts 例外条)
    _write_day(mgr.config.data_dir, v4_epoch_date_str(now), f"{now - 3600},1024,2048\n{now - 60},0,4096\n")
    bodies = []
    for p in (
        "/api/traffic/qb/global?window=24h",
        "/api/traffic/qb/torrent/HA?window=24h",  # 种子无数据 -> 空态, limits 仍同源附加
    ):
        r = client.get(p, headers=auth)
        assert r.status_code == 200, p
        body = r.json()
        assert "limits" in body, p
        bodies.append(body)
    want = [[now - 3600, 1024, 2048], [now - 60, 0, 4096]]
    for body in bodies:
        assert body["limits"] == want
    # 未启用: 恒 [] 且字段仍在(契约形状一致)
    _enable_qb_traffic(mgr, enabled=False)
    body = client.get("/api/traffic/qb/global", headers=auth).json()
    assert body["limits"] == []


def test_module_wiring_sample_global_observes(web_env, monkeypatch):
    """接线守阵: 真实模块 + 替身 server_state -> _sample_global 触发记录落盘; dry_run 零写"""
    from types import SimpleNamespace

    from auto_qb.core.modules.traffic_sample_mod import TrafficSampleModule

    mgr, _client = web_env
    mgr.config.qb_traffic = SimpleNamespace(enabled=True, sample_interval=30)
    data_dir = str(mgr.config.data_dir)
    ctx = SimpleNamespace(config=mgr.config, store=SimpleNamespace(by_hash={}), web=None, host=None)
    mod = TrafficSampleModule(ctx)
    assert mod._limits_rec._data_dir == data_dir
    server_state = {
        "dl_info_speed": 0,
        "up_info_speed": 0,
        "alltime_dl": 0,
        "alltime_ul": 0,
        "dl_info_data": 0,
        "up_info_data": 0,
        "dl_rate_limit": 1024,
        "up_rate_limit": 2048,
    }
    ts = _anchored_ts()
    mod._sample_global(server_state, ts)
    date = v4_epoch_date_str(ts)
    assert _read_day(data_dir, date) == f"{ts},2048,1024\n"  # 行序 = ts,up,down
    # dry_run 轮(persistence_on=False): 不落盘且基线不推进(恢复后按重启去重对齐)
    ts2 = ts + 30
    mod._persistence_on = False
    mod._sample_global(server_state, ts2)
    assert _read_day(data_dir, date) == f"{ts},2048,1024\n"


def test_limits_cache_no_data_dir_and_open_oserror(tmp_path, monkeypatch):
    """读侧降级: data_dir 空恒 () 零 IO; 读天文件 OSError 按缺失处理不上抛"""
    empty = LimitsCache("")
    assert empty.read_day("2026-10-20") == ()
    assert empty.read_day("2026-10-20") == ()  # 恒空, 不建缓存条目也不碰盘

    data_dir = str(tmp_path)
    ts = _anchored_ts()
    date = v4_epoch_date_str(ts)
    _write_day(data_dir, date, f"{ts},1024,2048\n")
    cache = LimitsCache(data_dir)

    def _boom(*a, **k):
        raise OSError("permission denied")

    monkeypatch.setattr("builtins.open", _boom)
    # stat 成功但 open 失败: 按缺失处理(事件缺口), 不把异常抛给端点
    assert cache.read_day(date) == ()


def test_limits_cache_evicts_oldest(tmp_path, monkeypatch):
    """缓存上限治理: 条目超上限丢最旧(LRU), 被丢的天重读触发重解析(不常驻)"""
    monkeypatch.setattr("auto_qb.core.traffic_limits._LIMITS_CACHE_MAX_ENTRIES", 2)
    data_dir = str(tmp_path)
    cache = LimitsCache(data_dir)
    ts = _anchored_ts()
    dates = [v4_epoch_date_str(ts + i * 86400) for i in range(3)]
    for d in dates:
        _write_day(data_dir, d, f"{ts},1,2\n")
    calls = {"n": 0}
    real_parse = parse_limits_day_text

    def spy(text):
        calls["n"] += 1
        return real_parse(text)

    monkeypatch.setattr("auto_qb.core.traffic_limits.parse_limits_day_text", spy)
    assert cache.read_day(dates[0]) == ((ts, 1, 2), )
    assert cache.read_day(dates[1]) == ((ts, 1, 2), )
    assert cache.read_day(dates[2]) == ((ts, 1, 2), )  # 第三条写入即挤出最旧
    assert calls["n"] == 3
    assert len(cache._entries) == 2, "缓存条目不得超上限"
    # 最旧的天已不在缓存: 重读触发重解析(探针计数长 1)
    assert cache.read_day(dates[0]) == ((ts, 1, 2), )
    assert calls["n"] == 4


def test_events_for_window_empty_when_reversed(tmp_path):
    """装配入口闸: t1 <= t0(空窗/反窗) 恒 [] 且零读盘"""
    cache = LimitsCache(str(tmp_path))
    ts = _anchored_ts()
    assert limits_events_for_window(cache, ts, ts) == []
    assert limits_events_for_window(cache, ts + 100, ts) == []
    assert cache._entries == {}, "空窗不得读任何天文件"


def test_events_for_window_breaks_at_window_end_and_pick_limit(tmp_path):
    """窗口右界: >= t1 的事件不进装配(break); _pick_limit 取值口径(None/空串/非数值)"""
    cache = LimitsCache(str(tmp_path))
    ts = _anchored_ts()
    date = v4_epoch_date_str(ts)
    # 窗内两行 + 窗外一行(epoch 更大): 窗外那行必须被 break 挡掉
    _write_day(data_dir := str(tmp_path), date, f"{ts},1,1\n{ts + 30},2,2\n{ts + 10**6},3,3\n")
    out = limits_events_for_window(cache, ts, ts + 60)
    assert out == [[ts, 1, 1], [ts + 30, 2, 2]], out

    from auto_qb.core.traffic_limits import _pick_limit

    assert _pick_limit(None) is None
    assert _pick_limit("") is None
    assert _pick_limit(1024) == 1024
    assert _pick_limit("2048") == 2048
    assert _pick_limit(0) == 0  # 0 = 不限速合法值
    assert _pick_limit("abc") is None
    assert _pick_limit(object()) is None


def test_recorder_append_fail_arcs_bootstrap_and_throttle(tmp_path):
    """追加失败的三条边缘: ① 启动首轮 `_bootstrap` 追加就失败 -> 不推进基线(下轮仍按首轮处理);
    ② 首轮失败后 `_last` 仍为 None, 跨日判定走「无 carry」假弧(首个可得值按普通事件写);
    ③ 同一告警窗口(3600s)内第二次失败**不再刷 WARNING**(节流, 否则磁盘故障会每秒刷屏)。

    用自建 handler 挂模块 logger 收 record(不用 caplog: QbManager 构造会清 root handlers)。
    """
    data_dir = str(tmp_path)
    ts = _anchored_ts()
    rec = SpeedLimitRecorder(data_dir)
    records = []

    class _Rec(logging.Handler):
        def emit(self, record):
            records.append(record.getMessage())

    lg = logging.getLogger("auto_qb.core.traffic_limits")
    handler = _Rec()
    handler.setLevel(logging.DEBUG)
    old_level = lg.level
    lg.setLevel(logging.DEBUG)
    lg.addHandler(handler)
    import builtins

    real_open = builtins.open
    try:
        builtins.open = lambda *a, **k: (_ for _ in ()).throw(OSError("disk gone"))
        try:
            rec.observe(_state(1024, 2048), ts)  # ① 首轮追加失败
            rec.observe(_state(0, 0), ts + 1)  # ②③ 同日再失败: 无 carry 分支 + 告警节流
        finally:
            builtins.open = real_open
    finally:
        lg.removeHandler(handler)
        lg.setLevel(old_level)

    warns = [m for m in records if "追加失败" in m]
    assert len(warns) == 1, f"告警必须节流成一条: {warns}"
    assert rec._last is None, "首轮失败不得推进基线"
    assert rec._last_date is None, "失败轮不得推进日期"
