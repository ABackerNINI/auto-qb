"""test_traffic_raw_prune 测试计划: raw 保留窗清理(S3, plan 26-11-21-1546 —— 补齐 raw_window「按天整文件存删」删除半边 + 清理子线程 + 守阵)

## 测试计划(每个测试函数一条)
保留下界公式(v4_raw_keep_floor_date, 单点纯函数):
- test_raw_keep_floor_formula: 全档参数化(1h/24h/24h+1s/3d/7d/30d/90d)—— floor =
  date(now) - ceil(raw_window/86400) - 2, 默认 24H -> 保留 4 个天文件(今日 + 前 3 日)
- test_guard_view_side_floor_never_after_read_lo: 守阵正面(R7, 双面之一)—— 7 档 raw 段视图窗
  x 采样间隔(1.5/600 上界) x t1 相位(午间/午夜边角) x raw_window(1d/7d/90d)全组合:
  读侧装配消费下界 group_null_lo(t0, si) 涉及的最早天文件日期 >= 保留下界(清理只删读侧
  不再需要的文件)。窗宽表从单点 WINDOW_SPECS 现取 + 模块级断言钉最大 raw span == 86400
  (评审 minor: 新增更宽 raw 段窗 = 本模块收集期直接打红, R7 不变量不静默漏接)
- test_guard_view_side_corner_shapes: 读侧假设本身钉住 —— 24h 窗 si=600 午夜边角(tod < si)
  恰 4 个天文件(D-3..D)且最早读日期 == floor(24H)(等号边角: 删除判据严格 <, 边界日保留);
  午间常态恰 3 个(D-2..D)
- test_guard_recovery_read_set_disjoint_from_deletion: 守阵反面(双面之二)—— 恢复读集
  (series_day_dates 真实机制, 下界 = 水位日)与删除集(日期 < floor)年龄不相交: 水位日
  D-1/D 时读集 <= 2(常态), 余量盖到水位日 D-3(读集 4); floor <= 水位日恒成立
清理动作面(TrafficV4Store.prune_raw_window_days):
- test_prune_deletes_only_over_window_day_files: 只删日期 < floor 的天文件(两系列);
  边界日/窗内保留; agg.dat/根级 acc.dat/非日期名(杂物/非法日历日期/非法形状)一律不碰
- test_prune_oserror_skip_warn_throttle_and_recover: OSError/PermissionError 跳过该文件
  下轮重试(R4); 告警节流同系列恢复前只一次(_agg_warned 先例)—— 连续失败只一条, 恢复
  (成功删除)后再失败重新告警
- test_prune_filenotfound_counts_as_deleted: FileNotFoundError(并发双闸窄角/evict 已删)
  计入删除(目标态达成, 幂等)且零告警
- test_prune_skips_vanished_series_dir: 系列目录消失(evict 并发删净/listdir OSError)本系列
  跳过不复活不报错, 其它系列照常清理
- test_prune_coexists_with_evict_and_double_run: 与 evict 共存 —— evict 删整目录后 prune
  不复活不报错; 二跑幂等零删除; 全局系列照常清理
调度(D13: 启动一次 + flush 时点每日闸, daemon 自终止):
- test_start_spawns_once_after_recovery: start() 尾部在恢复完成后 spawn 一次(顺序钉住);
  同日二次 start 每日闸不重 spawn
- test_start_no_spawn_dry_run_or_disabled: dry_run / enabled=false / 键组缺省(None) /
  data_dir 空 / persistence 关闭五种情形零 spawn(黄金法则 2 保守默认)
- test_daily_gate_once_per_day: 每日闸 —— 同日只 spawn 一次, 跨日再 spawn; gate 的 now
  原样传给 daemon(保留下界与 spawn 判据同源, 跨午夜窄角不相交)
- test_spawn_failure_keeps_gate_open: 线程启动失败告警返回 False 且标记不置位(未启动 =
  未清理, 同日下轮可重试; relocate-probe 同款口径)
- test_flush_hook_gate_and_stop_never_spawns: flush 时点(_maybe_flush_all 末尾)过每日闸
  —— 首轮只记时零 spawn, 到期 flush spawn 一次, 同日不重 spawn; stop() 走
  _flush_all_series 不经每日闸(停机不 spawn)
- test_worker_end_to_end_via_fake_thread: 假线程同步执行钉线程名/daemon/实参 + 端到端
  删除面; worker 用 spawn 时刻的 now 计算下界(时钟已跨 2 日边界日仍保留 —— 不用线程内
  现取, 跨午夜窄角删除面不随调度相位前移); 删除计数 INFO 埋点
- test_worker_full_catch_and_disabled_zero_touch: daemon 线程体全 catch(异常告警不上抛,
  不带进程); 未启用时零触 store(黄金法则 2)

线程纪律: 调度面全部用假线程同步执行或实例级桩(零真线程, 无 join/轮询 flaky 面); 文件
一律落 tmp_path; 日期常量钉 2026-11-21(远离 DST 转换, 跨平台时区无歧义)。
"""

import logging
import os
from types import SimpleNamespace

import pytest

from helpers import capture_logs

from auto_qb.config import QbTraffic
from auto_qb.core import traffic_grid as tg
from auto_qb.core.module import AppContext
from auto_qb.core.modules.traffic_sample_mod import TrafficSampleModule
from auto_qb.core.traffic_group_assembly import group_null_lo
from auto_qb.core.traffic_store import (
    AggRow,
    GLOBAL_KEY,
    HEADER_LINE_V4,
    TrafficV4Store,
    v4_date_str_epoch,
    v4_day_file_path,
    v4_epoch_date_str,
    v4_raw_keep_floor_date,
    v4_series_dir,
    v4_window_dates,
)

#: 语料日(固定本地日, 同 test_traffic_acc_wiring 先例; 11 月下旬无 DST 转换)与正午时刻
D = "2026-11-21"
NOON = v4_date_str_epoch(D) + 12 * 3600
#: floor(24H) = 2026-11-18(今日 - 3): 保留 4 个天文件的边界日
FLOOR_24H = "2026-11-18"
#: 午夜边角 t1(当日已过 0.5s < 采样间隔 600s -> 读侧跨 3 个日界的 4 文件边角相位)
MIDNIGHT_EDGE = v4_date_str_epoch(D) + 0.5
KEY_T = "torrent:" + "ab" * 20

#: raw 段视图窗 -> 窗宽秒: 从单点 WINDOW_SPECS 现取(评审 minor: 守阵不自持手工副本 ——
#: 未来加宽 raw 段窗时由下面的机器断言直接打红, R7 不变量不静默漏接)
_RAW_VIEW_S = {name: float(span) for name, (span, seg) in tg.WINDOW_SPECS.items() if seg == "raw"}
assert max(_RAW_VIEW_S.values()) == 86400.0, (
    "出现 >24h 的 raw 段视图窗: R7 守阵的保留下界论证(读侧最早读时刻 = now - 172800 - si, "
    "si 校验上界 600s)按 24h 窗推导 —— 更宽 raw 窗须同步复核 v4_raw_keep_floor_date 的 "
    "+3 日界余量与本守阵的参数面(t1 相位/si 档), 不是改一行断言的事"
)


def _make_mod(data_dir, conf="default", clock=None):
    """直构模块(与 test_traffic_acc_wiring._make_mod 同款最小装配)。conf="default" ->
    enabled 缺省档; None -> 键组缺省(未启用)。"""
    if conf == "default":
        conf = QbTraffic(enabled=True, sample_interval_multiplier=1)
    ctx = AppContext(SimpleNamespace(data_dir=str(data_dir), qb_traffic=conf, main_tick=2.0))
    return TrafficSampleModule(ctx, clock=clock), ctx


def _recorder(mod):
    """spawn 桩: 记录 (now) 调用并返回 True(模拟启动成功)"""
    calls = []
    mod._spawn_raw_prune = lambda now: calls.append(now) or True
    return calls


def _mk_day(data_dir, key, date_str):
    """写一个形状合法的天文件(头行 + key 行; prune 按文件名日期判删, 内容不参与)"""
    p = v4_day_file_path(str(data_dir), key, date_str)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"{HEADER_LINE_V4}\nkey,{key}\n")


def _exists(data_dir, key, date_str):
    return os.path.exists(v4_day_file_path(str(data_dir), key, date_str))


# ---------- 保留下界公式(单点纯函数) ----------


@pytest.mark.parametrize(
    "raw_window,expected",
    [
        (3600.0, FLOOR_24H),  # 1h: ceil=1 -> 今日-3(保留 4 个天文件的下界锚)
        (86400.0, FLOOR_24H),  # 24H 缺省档: 保留 4 个天文件(计划 §03.2)
        (86401.0, "2026-11-17"),  # 24H+1s: ceil 跨档 -> 今日-4
        (3 * 86400.0, "2026-11-16"),
        (7 * 86400.0, "2026-11-12"),
        (30 * 86400.0, "2026-10-20"),
        (90 * 86400.0, "2026-08-21"),
    ],
)
def test_raw_keep_floor_formula(raw_window, expected):
    """全档参数化: floor = date(now) - ceil(raw_window/86400) - 2(= raw_window 天数 + 3 日界
    余量的最早保留日, 含); 删除判据为严格早于该日(边界日保留, 动作面用例钉)"""
    assert v4_raw_keep_floor_date(NOON, raw_window) == expected


@pytest.mark.parametrize("raw_window", (86400.0, 7 * 86400.0, 90 * 86400.0))
@pytest.mark.parametrize("t1", (NOON, MIDNIGHT_EDGE))
@pytest.mark.parametrize("si", (1.5, 600.0))
@pytest.mark.parametrize("window", tuple(_RAW_VIEW_S))
def test_guard_view_side_floor_never_after_read_lo(tmp_path, raw_window, t1, si, window):
    """守阵正面(R7 双面之一, 全组合 84 例): 读侧 raw 段窗按天加载的最早读日期(装配消费
    下界 group_null_lo(t0, si) 的窗口日期集)恒 >= 保留下界 —— 清理只删读侧不再需要的
    文件; si = 生效采样间隔(1.5 常态 / 600 校验上界, 计划 26-11-10-0252 D6)"""
    w_s = _RAW_VIEW_S[window]
    read_dates = v4_window_dates(group_null_lo(t1 - w_s, si), t1)
    floor = v4_raw_keep_floor_date(t1, raw_window)
    assert min(read_dates) >= floor, (window, si, t1, raw_window)


def test_guard_view_side_corner_shapes():
    """读侧假设本身钉住(§03.2 口径): 24h 窗 si=600 午夜边角(tod < si)恰 4 个天文件
    (D-3..D), 最早读日期 == floor(24H) —— 等号边角(删除判据严格 <, 边界日恰被保留);
    午间常态恰 3 个(D-2..D)。本条钉死「边角至多 4 个」的前提, 公式余量 +3 恰好盖住"""
    read_dates = v4_window_dates(group_null_lo(MIDNIGHT_EDGE - 86400.0, 600.0), MIDNIGHT_EDGE)
    assert len(read_dates) == 4
    assert min(read_dates) == FLOOR_24H == v4_raw_keep_floor_date(MIDNIGHT_EDGE, 86400.0)
    read_dates = v4_window_dates(group_null_lo(NOON - 86400.0, 600.0), NOON)
    assert len(read_dates) == 3 and min(read_dates) == "2026-11-19"


@pytest.mark.parametrize("wm_offset", (0, 1, 2, 3))
def test_guard_recovery_read_set_disjoint_from_deletion(tmp_path, wm_offset):
    """守阵反面(R7 双面之二): 恢复读集(series_day_dates 真实机制, 下界 = 水位日)与删除集
    (日期 < floor)年龄不相交; 水位日 D-1/D 常态读集 <= 2 个天文件, +3 余量盖住水位陈旧至
    D-3(读集 4); floor <= 水位日恒成立"""
    st = TrafficV4Store(str(tmp_path))
    all_dates = [v4_epoch_date_str(NOON - i * 86400) for i in range(6)]  # D-5 .. D
    for d in all_dates:
        _mk_day(tmp_path, KEY_T, d)
    floor = v4_raw_keep_floor_date(NOON, 86400.0)
    wm = v4_epoch_date_str(NOON - wm_offset * 86400)
    read_set = set(st.series_day_dates(KEY_T, v4_date_str_epoch(wm)))  # prune 前取恢复读集
    assert read_set <= set(all_dates[:wm_offset + 1])  # 读集 = [水位日, 今日](all_dates 今日在前降序)
    assert len(read_set) <= (2 if wm_offset <= 1 else 4)  # 常态 <=2 / 余量盖到 D-3
    assert floor <= wm  # 保留下界 <= 水位日(ISO 串字典序 = 时间序)
    deleted, skipped = st.prune_raw_window_days(NOON, 86400.0)
    assert (deleted, skipped) == (2, 0)  # 判据宁可少删: 只删 D-5/D-4
    deleted_dates = {d for d in all_dates if d < floor}
    assert deleted_dates == {v4_epoch_date_str(NOON - i * 86400) for i in (4, 5)}
    assert not (read_set & deleted_dates)  # 年龄不相交(结构性, R5/R7)


# ---------- 清理动作面(TrafficV4Store.prune_raw_window_days) ----------


def test_prune_deletes_only_over_window_day_files(tmp_path):
    """只删日期 < floor 的天文件(逐系列); 边界日/窗内保留; agg.dat/根级 acc.dat/非日期名
    (杂物/非法日历日期 2 月 30 日/非法形状)一律不碰"""
    st = TrafficV4Store(str(tmp_path))
    for key in (GLOBAL_KEY, KEY_T):
        for d in ("2026-11-14", "2026-11-16", "2026-11-17", FLOOR_24H, "2026-11-20", D):
            _mk_day(tmp_path, key, d)
    st.append_agg_rows(GLOBAL_KEY, (AggRow("hour", NOON - 3600, 1, 1, 1, 1, 1, 1, 3600), ))
    series_dir = v4_series_dir(str(tmp_path), KEY_T)
    junk = ["notes.dat", "2026-02-30.dat", "2026-13-01.dat", "2026-11-2.dat"]
    for name in junk:
        with open(os.path.join(series_dir, name), "w", encoding="utf-8") as f:
            f.write("junk\n")
    os.makedirs(os.path.join(str(tmp_path), "qb-traffic-v4"), exist_ok=True)
    with open(os.path.join(str(tmp_path), "qb-traffic-v4", "acc.dat"), "w", encoding="utf-8") as f:
        f.write("# acc\n")
    deleted, skipped = st.prune_raw_window_days(NOON, 86400.0)
    assert (deleted, skipped) == (6, 0)  # 两系列 x 3(D-7/D-5/D-4)
    for key in (GLOBAL_KEY, KEY_T):
        for d in (FLOOR_24H, "2026-11-20", D):
            assert _exists(tmp_path, key, d), (key, d)  # 边界日 + 窗内保留
        assert not _exists(tmp_path, key, "2026-11-16") and not _exists(tmp_path, key, "2026-11-17")
    assert os.path.exists(v4_series_dir(str(tmp_path), GLOBAL_KEY) + "/agg.dat")
    for name in junk:  # 非日期名一律不碰
        assert os.path.exists(os.path.join(series_dir, name)), name
    assert os.path.exists(os.path.join(str(tmp_path), "qb-traffic-v4", "acc.dat"))  # 根级不碰


def test_prune_oserror_skip_warn_throttle_and_recover(tmp_path, monkeypatch, caplog):
    """OSError/PermissionError 跳过该文件下轮重试(R4); 告警节流同系列恢复前只一次
    (_agg_warned 先例): 连续失败只一条, 恢复(成功删除)后再失败重新告警一次"""
    caplog.set_level(logging.WARNING)
    _mk_day(tmp_path, KEY_T, "2026-11-16")  # 超窗
    _mk_day(tmp_path, KEY_T, FLOOR_24H)  # 边界日(不参与删除)
    real_remove = os.remove  # 打桩前捕获真函数(桩内放行走真 remove)
    state = {"locked": True}

    def _stub(path):
        if state["locked"]:
            raise PermissionError(13, "locked")
        real_remove(path)

    monkeypatch.setattr("auto_qb.core.traffic_store.os.remove", _stub)
    st = TrafficV4Store(str(tmp_path))
    assert st.prune_raw_window_days(NOON, 86400.0) == (0, 1)  # 跳过下轮重试
    assert _exists(tmp_path, KEY_T, "2026-11-16")
    warns = [r for r in caplog.records if "删除失败" in r.getMessage()]
    assert len(warns) == 1
    assert st.prune_raw_window_days(NOON, 86400.0) == (0, 1)  # 二轮仍失败
    assert len([r for r in caplog.records if "删除失败" in r.getMessage()]) == 1  # 节流: 不再告警
    state["locked"] = False
    assert st.prune_raw_window_days(NOON, 86400.0) == (1, 0)  # 恢复: 删除成功
    assert not _exists(tmp_path, KEY_T, "2026-11-16") and _exists(tmp_path, KEY_T, FLOOR_24H)
    _mk_day(tmp_path, KEY_T, "2026-11-16")
    state["locked"] = True
    assert st.prune_raw_window_days(NOON, 86400.0) == (0, 1)  # 恢复后再失败
    assert len([r for r in caplog.records if "删除失败" in r.getMessage()]) == 2  # 重新告警一次


def test_prune_filenotfound_counts_as_deleted(tmp_path, monkeypatch, caplog):
    """FileNotFoundError(并发双闸窄角重复删/evict 已删)计入删除(目标态达成, 幂等)且零告警"""
    caplog.set_level(logging.WARNING)
    _mk_day(tmp_path, KEY_T, "2026-11-16")
    monkeypatch.setattr(
        "auto_qb.core.traffic_store.os.remove", lambda path: (_ for _ in ()).throw(FileNotFoundError(2, "gone"))
    )
    st = TrafficV4Store(str(tmp_path))
    assert st.prune_raw_window_days(NOON, 86400.0) == (1, 0)
    assert not [r for r in caplog.records if "删除失败" in r.getMessage()]


def test_prune_skips_vanished_series_dir(tmp_path, monkeypatch):
    """系列目录消失(evict 并发删净/listdir OSError): 本系列跳过不复活不报错, 其它系列照常"""
    _mk_day(tmp_path, KEY_T, "2026-11-16")
    _mk_day(tmp_path, GLOBAL_KEY, "2026-11-16")
    real_listdir = os.listdir

    def _stub(path):
        if str(path).endswith("ab" * 20):
            raise OSError(2, "gone")  # 该系列目录已消失
        return real_listdir(path)

    monkeypatch.setattr("auto_qb.core.traffic_store.os.listdir", _stub)
    st = TrafficV4Store(str(tmp_path))
    assert st.prune_raw_window_days(NOON, 86400.0) == (1, 0)  # global 照常, torrent 跳过
    assert not _exists(tmp_path, GLOBAL_KEY, "2026-11-16")


def test_prune_coexists_with_evict_and_double_run(tmp_path):
    """与 evict 共存: evict 删超龄整目录后 prune 不复活不报错; 二跑幂等零删除(黄金法则 1);
    全局系列照常清理"""
    st = TrafficV4Store(str(tmp_path))
    old_d = v4_epoch_date_str(NOON - 40 * 86400)
    _mk_day(tmp_path, "torrent:OLD", old_d)
    _mk_day(tmp_path, KEY_T, "2026-11-16")
    _mk_day(tmp_path, KEY_T, D)
    _mk_day(tmp_path, GLOBAL_KEY, "2026-11-16")
    _mk_day(tmp_path, GLOBAL_KEY, D)
    assert st.evict_expired_series(NOON, 30 * 86400.0) == ["torrent:OLD"]
    assert st.prune_raw_window_days(NOON, 86400.0) == (2, 0)  # CUR + global 各删超窗 1 个
    assert not os.path.exists(v4_series_dir(str(tmp_path), "torrent:OLD"))  # 不复活
    assert st.prune_raw_window_days(NOON, 86400.0) == (0, 0)  # 幂等: 二跑零删除


# ---------- 调度(D13: 启动一次 + flush 时点每日闸, daemon 自终止) ----------


def test_start_spawns_once_after_recovery(tmp_path):
    """start() 尾部在恢复完成后 spawn 一次(顺序钉住: 恢复读集与删除目标年龄不相交, R5);
    同日二次 start 每日闸不重 spawn"""
    from clock import FakeClock

    mod, ctx = _make_mod(tmp_path, clock=FakeClock(start=NOON))
    order = []
    real_recover = mod._recover_aggregates

    def _recover():
        order.append("recover")
        real_recover()

    mod._recover_aggregates = _recover
    calls = []

    def _spawn(now):
        order.append("spawn")  # spawn 桩(记录顺序)
        return calls.append(now) or True

    mod._spawn_raw_prune = _spawn
    mod.start(ctx, dry_run=False)
    assert order == ["recover", "spawn"] and len(calls) == 1 and calls[0] == NOON
    mod.start(ctx, dry_run=False)  # 同日二次 start: 每日闸不重 spawn
    assert len(calls) == 1


def test_start_no_spawn_dry_run_or_disabled(tmp_path):
    """dry_run / enabled=false / 键组缺省(None) / data_dir 空 / persistence 关闭: 零 spawn
    (黄金法则 2 保守默认 —— 清理属删除类动作)"""
    mod, ctx = _make_mod(tmp_path)
    calls = _recorder(mod)
    mod.start(ctx, dry_run=True)
    assert calls == []
    mod, ctx = _make_mod(tmp_path, conf=QbTraffic(enabled=False))
    calls = _recorder(mod)
    mod.start(ctx, dry_run=False)
    assert calls == []
    mod, ctx = _make_mod(tmp_path, conf=None)
    calls = _recorder(mod)
    mod.start(ctx, dry_run=False)
    assert calls == []
    mod, ctx = _make_mod(tmp_path)
    ctx.config.data_dir = ""  # 防御分支: data_dir 空
    assert mod._maybe_spawn_raw_prune(NOON) is False
    mod, ctx = _make_mod(tmp_path)
    mod._persistence_on = False  # dry_run 运行态旗标
    assert mod._maybe_spawn_raw_prune(NOON) is False


def test_daily_gate_once_per_day(tmp_path):
    """每日闸(D13): 同日只 spawn 一次, 跨日再 spawn; gate 的 now 原样传给 daemon
    (保留下界与 spawn 判据同源 —— 跨午夜窄角删除面不随线程调度相位前移)"""
    mod, ctx = _make_mod(tmp_path)
    calls = _recorder(mod)
    t0 = v4_date_str_epoch(D) + 10 * 3600
    assert mod._maybe_spawn_raw_prune(t0) is True and len(calls) == 1
    assert mod._maybe_spawn_raw_prune(t0 + 3600) is False and len(calls) == 1  # 同日
    assert mod._maybe_spawn_raw_prune(t0 + 86400 + 3600) is True and len(calls) == 2  # 跨日
    assert mod._maybe_spawn_raw_prune(t0 + 86400 + 7200) is False and len(calls) == 2  # 次日同日
    assert calls[1] == t0 + 86400 + 3600  # gate 的 now 原样下传


def test_spawn_failure_keeps_gate_open(tmp_path, monkeypatch, caplog):
    """线程启动失败: 告警返回 False 且标记不置位(未启动 = 未清理, 同日下轮可重试;
    relocate-probe 同款口径: 不收 BaseException 由调用线程面兜底)"""
    caplog.set_level(logging.WARNING)

    class _BoomThread:
        def __init__(self, **kw):
            pass

        def start(self):
            raise RuntimeError("no threads")

    monkeypatch.setattr("auto_qb.core.modules.traffic_sample_mod.threading.Thread", _BoomThread)
    mod, ctx = _make_mod(tmp_path)
    with capture_logs("auto_qb.core.modules.traffic_sample_mod") as logs:
        assert mod._maybe_spawn_raw_prune(NOON) is False
    assert "清理线程启动失败" in logs.text and "RuntimeError" in logs.text
    calls = _recorder(mod)
    assert mod._maybe_spawn_raw_prune(NOON) is True and len(calls) == 1  # 同日可重试(标记未置位)


def test_flush_hook_gate_and_stop_never_spawns(tmp_path):
    """flush 时点(_maybe_flush_all 末尾)过每日闸: 首轮只记时零 spawn; 到期 flush spawn 一次
    (P2b flush 硬序不动 —— acc 随批行照常); 同日不重 spawn; stop() 走 _flush_all_series
    不经每日闸(停机不 spawn)"""
    mod, ctx = _make_mod(tmp_path)
    conf = ctx.config.qb_traffic  # flush_interval 缺省 600
    calls = _recorder(mod)
    mod._persistence_on = True
    mod._maybe_flush_all(conf, NOON)  # 进程首轮: 只记时不 flush 不 spawn
    assert calls == [] and mod._last_flush == NOON
    mod._maybe_flush_all(conf, NOON + 600)  # flush 时点: evict 后每日闸 -> spawn
    assert calls == [NOON + 600]
    mod._maybe_flush_all(conf, NOON + 1200)  # 同日再 flush: 不重 spawn
    assert calls == [NOON + 600]
    mod.stop()  # stop 不经每日闸
    assert calls == [NOON + 600]


def test_worker_end_to_end_via_fake_thread(tmp_path, monkeypatch, caplog):
    """假线程同步执行钉线程名/daemon/实参 + 端到端删除面; worker 用 spawn 时刻的 now 计算
    下界(时钟已跨 2 日, 边界日仍保留); 删除计数 INFO 埋点"""
    caplog.set_level(logging.INFO)
    for d in ("2026-11-15", FLOOR_24H, D):
        _mk_day(tmp_path, KEY_T, d)
    _mk_day(tmp_path, GLOBAL_KEY, "2026-11-15")
    _mk_day(tmp_path, GLOBAL_KEY, D)
    from clock import FakeClock

    mod, ctx = _make_mod(tmp_path, clock=FakeClock(start=NOON + 2 * 86400))  # 时钟已跨 2 日
    started = []

    class _FakeThread:
        def __init__(self, target=None, args=(), name=None, daemon=False):
            self.target, self.args, self.name, self.daemon = target, args, name, daemon

        def start(self):
            started.append((self.name, self.daemon, self.args))
            self.target(*self.args)  # 同步执行(零真线程, 无 flaky 面)

    monkeypatch.setattr("auto_qb.core.modules.traffic_sample_mod.threading.Thread", _FakeThread)
    assert mod._maybe_spawn_raw_prune(NOON) is True
    assert started == [("traffic-raw-prune", True, (NOON, ))]
    assert not _exists(tmp_path, KEY_T, "2026-11-15") and not _exists(tmp_path, GLOBAL_KEY, "2026-11-15")
    assert _exists(tmp_path, KEY_T, FLOOR_24H) and _exists(tmp_path, KEY_T, D)  # 边界日/今日保留
    assert _exists(tmp_path, GLOBAL_KEY, D)
    assert any("raw 保留窗清理: 删除超窗天文件 2 个" in r.getMessage() for r in caplog.records)
    n_info = len([r for r in caplog.records if "raw 保留窗清理" in r.getMessage()])
    mod._raw_prune_worker(NOON)  # 空闲二跑(零删零跳): 静默无 INFO(黄金法则 1 幂等)
    assert len([r for r in caplog.records if "raw 保留窗清理" in r.getMessage()]) == n_info


def test_worker_full_catch_and_disabled_zero_touch(tmp_path, monkeypatch, caplog):
    """daemon 线程体全 catch(异常告警不上抛 —— 异常不带进程); 未启用时零触 store"""
    caplog.set_level(logging.WARNING)
    mod, ctx = _make_mod(tmp_path)
    monkeypatch.setattr(
        TrafficV4Store, "prune_raw_window_days", lambda self, now, w: (_ for _ in ()).throw(RuntimeError("x"))
    )
    mod._raw_prune_worker(NOON)  # 不上抛
    assert any("清理线程异常" in r.getMessage() and "RuntimeError" in r.getMessage() for r in caplog.records)
    mod2, ctx2 = _make_mod(tmp_path, conf=QbTraffic(enabled=False))

    def _no_store():
        raise AssertionError("未启用时不得触 store")

    mod2._get_v4_store = _no_store
    mod2._raw_prune_worker(NOON)  # 静默返回(黄金法则 2)
