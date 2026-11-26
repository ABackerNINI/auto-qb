"""test_traffic_acc_wiring 测试计划: acc 快照账本接线(P2b, plan 26-11-21-1546 S2 第二步 —— 启动快路/flush 随批/stop 终态行接进恢复与落盘流程)

在线语料脚手架(单日确定性): r 标称链 300 点(0..2h30m, 零漂移, 30s 档) + n 尾游程(3 槽,
清 open_credit —— 快路直采与 fallback 重建的 SeriesAgg 字段严格对齐, 对拍可逐字段 bitwise),
经真实 _append_record/_flush_all_series/stop 驱动(与生产同路)。

## 测试计划(每个测试函数一条)
- test_acc_wiring_fastpath_adopt_zero_reads: 快路直采 —— 账本行+指纹匹配+raw 尾<=游标 ->
  AccSeriesState 逐字段直采 SeriesAgg(与在线终态 AccSeriesState 逐字段深度相等); monkeypatch
  计数 read_day/read_day_open_segment/read_agg 调用 = 0(零 agg 读零 raw 读 —— 判定只走
  1 次 agg.dat stat + 尾块轻量读); 游标记忆就位; recovery_reads[source]=ledger/bound=ledger/
  slots=0 + recovery_stats[ledger_fastpath]=1/ledger_fallback=0
- test_acc_wiring_raw_tail_two_way: R3 两向判定 —— raw_tail_beyond_cursor 直测矩阵(无候选
  文件 False / 游标 None 有文件 True / 尾块游标==账本游标 False / 直接 append_records 超前块
  True / 尾块超窗翻倍重读(300KB 单块大文件) False / 损坏文件 True / 空文件 True / 头行-only
  True); 接线面: 超前块(指纹未变)重启 -> 该系列 fallback 回放
- test_acc_wiring_fingerprint_mismatch_and_isolation: 指纹失配(agg 直接补行)或账本行损坏/缺行
  -> 仅该系列 fallback, 他系列快路不放大(D9 单系列隔离); 指纹列序语义钉: 行内 fp =
  (size, mtime_ns) 且 == 封口后 agg.dat stat(探针可回配)
- test_acc_wiring_ledger_missing_bootstrap: 账本缺失 = 全体 fallback(升级首启)+ 首轮 flush
  自举账本(重建系列 dirty 标记 -> 变化行落账, cursor/指纹就位)
- test_acc_wiring_flush_batch_and_compaction: flush 随批 —— 累计器推进系列追加 / 封口-only
  变化(hour 完结后无记录 flush 也追加)/ 空闲 flush 零追加(账本字节不变)/ 压实触发(注桩
  小阈值单次重写折叠 last-wins, 内容等价)/ 行内指纹 = 封口后 stat
- test_acc_wiring_stop_terminal_rows_idempotent: stop 全系列终态行(多系列, 各带终态 cursor/
  指纹); 幂等(二次 stop 账本字节不变); dry_run stop 零写
- test_acc_wiring_hard_order_agg_append_failure: 硬序 —— agg 封口 append 失败 -> acc 行跳过
  (账本不领先于 agg 现状); 下轮无 agg 行时自愈补写
- test_acc_wiring_crash_raw_ahead_replay: crash 窗口两向之一(§04 S2 用例 1) —— crash 落在 raw
  追加与 acc 追加之间(指纹未变): raw 尾>游标 -> fallback 回放(尾段小时重建进 pending)
- test_acc_wiring_crash_raw_behind_adopt: crash 窗口两向之二(§04 S2 用例 2) —— raw 追加失败
  (观测保留在累计器)acc 行照写(cursor > raw 尾): 重启快路直采, 折叠态含 raw 已丢信用
  (agg 面比现状完整, raw 面真空 = 既有崩溃语义)
- test_acc_wiring_fastpath_vs_rebuild_equivalence: 快路 vs 重建对拍(D2) —— 同一语料先跑出
  账本(stop 终态行), 快路恢复 vs 删账本 fallback 重建: SeriesAgg 逐字段 bitwise(pending
  折叠态 8 字段/open_credit/day/month 累计器/earliest_hour/已关层存根)+ pending seal 行
  format_agg_row bitwise + 游标记忆一致; 快路读计数 0 vs 重建读计数 > 0
- test_acc_wiring_adopt_with_stubs_and_null_cursor: 已关层存根随快照直采(AccSeriesState ->
  SeriesAgg stub 重建分支)+ 游标 None 快照直采(游标记忆不置位); 尾块空块保守回放分支;
  _tail_block_cursor 未知记录型 fail-fast
- test_acc_wiring_acc_append_failure_paths: acc 落盘失败面 —— flush 追加 OSError(连续失败
  告警一次 + 保持 dirty)/ 游标 None 变化系列(行 cursor 空列)/ stop 硬序跳过(agg append
  失败系列)与全跳过(snaps 空 return)/ stop 终态行追加 OSError / 账本整读 OSError(恢复入口
  全体 fallback)/ 游标记忆捕获对零游标缓冲跳过
- test_acc_wiring_credit_day_file_unknown_record: _agg_credit_day_file 未知块记录型
  fail-fast(既有防御分支的定向钉面 —— 本批覆盖率闸回补, 详见交付报告)
- test_acc_wiring_z_run_collapsed_slots_direct: B2 塌缩区间分支定向钉面(spacing << ULP ->
  桶内无正长度区间 ki 回退负值不入账; 既有防御分支的覆盖率闸回补)
- test_acc_wiring_compact_oserror_swallowed: 压实调用 OSError 护栏(评审 major)—— flush 与
  stop 两处 compact_acc_ledger 调用告警不上抛(行已落账原文件完好下轮自愈, stop 不跳过
  state.save/锁释放)
- test_acc_wiring_dt1_boundary_replays: 容差边界(评审 minor)—— dt_ms=1 钳制边界下单条
  1ms 记录的超前(尾-游标 ≈ 1e-3)必判回放(ACC_RAW_TAIL_TOL_S=5e-4), 尾槽恰等游标仍直采
"""

import os
from types import SimpleNamespace

import pytest

from clock import FakeClock

from auto_qb.config import QbTraffic
from auto_qb.core.module import AppContext
from auto_qb.core.modules.traffic_sample_agg import _tail_block_cursor, raw_tail_beyond_cursor
from auto_qb.core.modules.traffic_sample_mod import TrafficSampleModule
from auto_qb.core.modules.traffic_sample_common import BlockBuffer, SeriesAgg
from auto_qb.core import traffic_store_acc_ledger as acc_ledger_mod
from auto_qb.core.traffic_store import (
    HOUR_SECONDS,
    AggRow,
    TrafficV4Store,
    V4Block,
    V4NullRun,
    V4Sample,
    format_agg_row,
    v4_date_str_epoch,
    v4_agg_file_path,
)
from auto_qb.core.traffic_store_acc_ledger import (
    AccSeriesState,
    AccSnapshot,
    append_acc_snapshots,
    parse_acc_ledger_text,
    read_acc_ledger,
    stat_agg_fingerprint,
)
from auto_qb.core.traffic_store_paths import v4_acc_ledger_path, v4_series_dir

#: 语料日(固定本地日, 同 test_traffic_recovery_equivalence 先例)与在线相位
DAY0 = v4_date_str_epoch("2026-06-05")
INTERVAL = 30.0
NOW = DAY0 + 9900.0  # 当日 02:45:00: hour 0/1 完结已封, hour 2(7200..10800)开放 pending
WINDOW = 30 * 86400.0
KEY_A = "torrent:" + "ab" * 20
KEY_B = "torrent:" + "cd" * 20
CURSOR = DAY0 + 9060.0  # 末记录(n 尾游程末槽)槽位锚点 = 账本游标


def _make_mod(data_dir, clock):
    """直构模块(与 bench harness 同款最小装配; interval 预置 30s 供标称链零漂移)。"""
    conf = QbTraffic(enabled=True, sample_interval_multiplier=1, rollup_window=WINDOW)
    ctx = AppContext(SimpleNamespace(data_dir=str(data_dir), qb_traffic=conf, main_tick=2.0))
    mod = TrafficSampleModule(ctx, clock=clock)
    mod._effective_interval = INTERVAL
    return mod, ctx


def _feed_chain(mod, key):
    """在线喂 r 标称链 300 点(0..2h30m)+ n 尾游程 3 槽(清 open_credit) -> 末槽 = CURSOR。"""
    t = float(DAY0)
    for k in range(300):
        mod._append_record(key, V4Sample(100 + k % 7, 50 + k % 5, 1_000_000 + k * 111, 2_000_000 + k * 57), t, t)
        t += INTERVAL
    mod._append_record(key, V4NullRun(3), DAY0 + 9000.0, DAY0 + 9060.0)  # 非块首 n: 末槽恰 9060


def _build_online(tmp_path, keys=(KEY_A, )):
    """在线跑出 raw+agg+账本(stop 终态行); 返回 (参照 SeriesAgg 终态, ctx, clock)。"""
    clock = FakeClock(start=NOW)
    mod, ctx = _make_mod(tmp_path, clock)
    for key in keys:
        _feed_chain(mod, key)
    mod.stop()
    return mod._agg_states[keys[0]], ctx, clock


def acc_state_from_mod(mod, key):
    """模块累计器原样返回(SeriesAgg —— 对拍断言面: dataclass 值等逐字段比较, fold 带
    seal 供封口输出层 bitwise 断言)。"""
    return mod._agg_states[key]


def acc_state_from_agg_snap(snap):
    """AccSnapshot.state -> SeriesAgg(读侧直采镜像, 断言辅助: 与写侧构建同一转换单点)。"""
    from auto_qb.core.modules.traffic_sample_agg import agg_state_from_acc

    return agg_state_from_acc(snap.state)


def _ledger_text(data_dir):
    with open(v4_acc_ledger_path(str(data_dir)), "r", encoding="utf-8") as f:
        return f.read()


def _parse_ledger(data_dir):
    return parse_acc_ledger_text(_ledger_text(data_dir))


def _count_reads(monkeypatch):
    """读入口计数探针: read_day / read_day_open_segment / read_agg 调用数(快路应为全 0)。"""
    counts = {"day": 0, "segment": 0, "agg": 0}
    real = (TrafficV4Store.read_day, TrafficV4Store.read_day_open_segment, TrafficV4Store.read_agg)

    def _day(self, *a, **k):
        counts["day"] += 1
        return real[0](self, *a, **k)

    def _seg(self, *a, **k):
        counts["segment"] += 1
        return real[1](self, *a, **k)

    def _agg(self, *a, **k):
        counts["agg"] += 1
        return real[2](self, *a, **k)

    monkeypatch.setattr(TrafficV4Store, "read_day", _day)
    monkeypatch.setattr(TrafficV4Store, "read_day_open_segment", _seg)
    monkeypatch.setattr(TrafficV4Store, "read_agg", _agg)
    return counts


# ---------- 快路直采 ----------


def test_acc_wiring_fastpath_adopt_zero_reads(tmp_path, monkeypatch):
    """快路直采: 指纹匹配 + raw 尾 <= 游标 -> AccSeriesState 逐字段直采, 零 agg 读零 raw 读
    (读入口计数全 0 —— 判定只走 stat 探针与尾块轻量读), 游标记忆与埋点就位。"""
    ref, ctx, _ck = _build_online(tmp_path)
    mod2, _ctx2 = _make_mod(tmp_path, FakeClock(start=NOW))
    counts = _count_reads(monkeypatch)
    mod2.start(ctx, dry_run=False)
    assert counts == {"day": 0, "segment": 0, "agg": 0}  # 零 agg 读零 raw 读(快路 §03.3)
    assert acc_state_from_mod(mod2, KEY_A) == ref  # SeriesAgg 全部持久化字段逐字段直采
    assert mod2._acc_cursors[KEY_A] == CURSOR  # 游标记忆就位(封口-only 变化行的游标源)
    reads = mod2.recovery_reads[KEY_A]
    assert reads["source"] == "ledger" and reads["bound"] == "ledger"
    assert reads["day_dates"] == () and reads["slots"] == 0 and reads["new_hours"] == 0
    assert mod2.recovery_stats["ledger_fastpath"] == 1 and mod2.recovery_stats["ledger_fallback"] == 0


def test_acc_wiring_raw_tail_two_way(tmp_path):
    """R3 两向判定直测矩阵 + 接线面(超前块 -> fallback 回放)。"""
    store = TrafficV4Store(str(tmp_path))
    # 无候选文件: raw 尾 <= 游标(游标日之后无天文件)
    assert raw_tail_beyond_cursor(store, KEY_A, DAY0 + 100.0) is False
    store.append_records(KEY_A, "2026-06-05", (DAY0 + 100, INTERVAL), (V4Sample(100, 50, 1000, 2000), ), (1000, 2000))
    # 游标 None 且存在天文件: 有 raw 即有未回放槽位(保守, 不读文件直判)
    assert raw_tail_beyond_cursor(store, KEY_A, None) is True
    # 尾块游标 == 账本游标: False; 游标落后于尾块: True(末槽 = 块首 r 槽 100, 单槽游标零推进)
    assert raw_tail_beyond_cursor(store, KEY_A, DAY0 + 100.0) is False
    assert raw_tail_beyond_cursor(store, KEY_A, DAY0 + 99.0) is True
    # 保守闸: 日界换算异常(Windows epoch 0 附近 OSError 坑) -> True(fallback), 判定不抛错
    assert raw_tail_beyond_cursor(store, KEY_A, 100.0) is True
    # 尾块超窗: 16000 行 r 块(~285KB > 256KB 窗口, interval 5s 保块不跨天写侧不变式)在
    # 窗口内无 B 行 -> 翻倍重读命中块头
    big_dir = tmp_path / "big"
    big_store = TrafficV4Store(str(big_dir))
    recs = tuple(V4Sample(100 + k % 7, 50, 1_000_000 + k * 37, 2_000_000) for k in range(16000))
    big_store.append_records(KEY_A, "2026-06-05", (DAY0, 5.0), recs, (1_000_000, 2_000_000))
    assert os.path.getsize(big_store.series_day_path(KEY_A, "2026-06-05")) > 256 * 1024
    tail = DAY0 + (len(recs) - 1) * 5.0  # 非块首标称链: 末槽 = 块首 + (n-1)*interval(仍在当日)
    assert raw_tail_beyond_cursor(big_store, KEY_A, tail) is False
    assert raw_tail_beyond_cursor(big_store, KEY_A, tail - 100.0) is True
    # 保守分支: 损坏文件 / 空文件 / 头行-only(无有效块头)
    bad_dir = tmp_path / "bad"
    bad_store = TrafficV4Store(str(bad_dir))
    path = bad_store.series_day_path(KEY_A, "2026-06-05")
    os.makedirs(v4_series_dir(str(bad_dir), KEY_A))
    for payload in (b"garbage bytes no header", b"", b"# auto-qb qb-traffic v4\nkey," + KEY_A.encode()):
        with open(path, "wb") as f:
            f.write(payload)
        assert raw_tail_beyond_cursor(bad_store, KEY_A, DAY0 + 100.0) is True
    # 接线面: 直接 append_records 超前块(指纹未变) -> 重启走 fallback 回放
    ref, ctx, _ck = _build_online(tmp_path / "wire")
    store2 = TrafficV4Store(str(tmp_path / "wire"))
    store2.append_records(
        KEY_A,
        "2026-06-05",
        (DAY0 + 3 * HOUR_SECONDS + 10, INTERVAL),
        (V4Sample(300, 90, 5_000_000, 6_000_000), V4Sample(310, 95, 5_000_100, 6_000_100)),
        (5_000_000, 6_000_000),
    )
    mod2, _c2 = _make_mod(tmp_path / "wire", FakeClock(start=NOW))
    mod2.start(ctx, dry_run=False)
    assert mod2.recovery_reads[KEY_A]["source"] == "rebuild"
    assert DAY0 + 3 * HOUR_SECONDS in mod2._agg_states[KEY_A].pending  # 尾段小时已回放进 pending
    assert mod2.recovery_stats["ledger_fastpath"] == 0 and mod2.recovery_stats["ledger_fallback"] == 1


def test_acc_wiring_fingerprint_mismatch_and_isolation(tmp_path, monkeypatch):
    """指纹失配(agg 直接补行)与账本单行损坏/缺行 -> 仅该系列 fallback(D9 单系列隔离),
    他系列快路不放大; 指纹列序语义钉: 行内 fp = (size, mtime_ns) 且 == 封口后 agg stat。"""
    # 指纹列序(写侧面): flush 后行内 fp 与 agg.dat stat 逐列相等(size 在前, D9 原文口径)
    ref, ctx, _ck = _build_online(tmp_path / "a")
    agg = v4_agg_file_path(str(tmp_path / "a"), KEY_A)
    row = _parse_ledger(tmp_path / "a").snapshots[KEY_A]
    assert row.agg_fingerprint == (os.path.getsize(agg), os.stat(agg).st_mtime_ns)
    assert row.agg_fingerprint[0] == os.path.getsize(agg)  # fp_size 在前(与 V4DayCache 列序相反)
    # 情形 1: 指纹失配(agg.dat 被直接补行, 账本未动) -> A fallback, B 快路
    root = tmp_path / "mismatch"
    ref, ctx, _ck = _build_online(root, keys=(KEY_A, KEY_B))
    TrafficV4Store(str(root)).append_agg_rows(KEY_A, (AggRow("hour", DAY0, 9, 9, 9, 9, 9, 9, 3600), ))
    mod2, _c2 = _make_mod(root, FakeClock(start=NOW))
    mod2.start(ctx, dry_run=False)
    assert mod2.recovery_reads[KEY_A]["source"] == "rebuild"
    assert mod2.recovery_reads[KEY_B]["source"] == "ledger"
    assert (mod2.recovery_stats["ledger_fastpath"], mod2.recovery_stats["ledger_fallback"]) == (1, 1)
    # 情形 2: 账本单行损坏(解析失败) -> A 无快照走 fallback, B 不受牵连
    root = tmp_path / "corrupt"
    ref, ctx, _ck = _build_online(root, keys=(KEY_A, KEY_B))
    lines = _ledger_text(root).splitlines()
    out = [lines[0]]
    for ln in lines[1:]:  # [0] = 版本头行(无数据列, 跳过)
        out.append(f"A,{ln.split(',')[1]},garbage" if ln.split(",")[1] == KEY_A else ln)
    with open(v4_acc_ledger_path(str(root)), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out) + "\n")
    mod3, _c3 = _make_mod(root, FakeClock(start=NOW))
    mod3.start(ctx, dry_run=False)
    assert mod3.recovery_reads[KEY_A]["source"] == "rebuild"
    assert mod3.recovery_reads[KEY_B]["source"] == "ledger"
    # 情形 3: 账本缺该系列行(last-wins 视图缺 A) -> 同隔离
    root = tmp_path / "missing"
    ref, ctx, _ck = _build_online(root, keys=(KEY_A, KEY_B))
    all_lines = _ledger_text(root).splitlines()
    kept = [ln for ln in all_lines[1:] if ln.split(",")[1] != KEY_A]
    with open(v4_acc_ledger_path(str(root)), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join([all_lines[0]] + kept) + "\n")
    mod4, _c4 = _make_mod(root, FakeClock(start=NOW))
    mod4.start(ctx, dry_run=False)
    assert mod4.recovery_reads[KEY_A]["source"] == "rebuild"
    assert mod4.recovery_reads[KEY_B]["source"] == "ledger"


def test_acc_wiring_ledger_missing_bootstrap(tmp_path):
    """账本缺失 = 全体 fallback(升级首启常态)+ 首轮 flush 自举账本(重建系列 dirty 标记
    -> 变化行落账, 游标/指纹取重建后现状)。"""
    ref, ctx, _ck = _build_online(tmp_path)
    os.remove(v4_acc_ledger_path(str(tmp_path)))  # 升级首启形态: 账本不存在
    mod2, _c2 = _make_mod(tmp_path, FakeClock(start=NOW))
    mod2.start(ctx, dry_run=False)
    assert mod2.recovery_reads[KEY_A]["source"] == "rebuild"
    assert (mod2.recovery_stats["ledger_fastpath"], mod2.recovery_stats["ledger_fallback"]) == (0, 1)
    assert acc_state_from_mod(mod2, KEY_A) == ref  # 重建态与账本直采态同源(同一语料)
    mod2._flush_all_series()  # 首轮 flush: 重建系列 dirty -> 自举账本行
    res = read_acc_ledger(str(tmp_path))
    assert res.header_ok and KEY_A in res.snapshots
    snap = res.snapshots[KEY_A]
    assert snap.cursor == CURSOR  # 重建游标 = 读集尾槽(与在线游标同语义)
    assert snap.agg_fingerprint == stat_agg_fingerprint(str(tmp_path), KEY_A)
    assert acc_state_from_mod(mod2, KEY_A) == acc_state_from_agg_snap(snap)


# ---------- flush 随批 / stop 终态行 / 硬序 ----------


def test_acc_wiring_flush_batch_and_compaction(tmp_path, monkeypatch):
    """flush 随批(D8): 累计器推进 -> 追加; 封口-only 变化(hour 完结后无记录的 flush) ->
    追加; 空闲 flush 零追加(账本字节不变); 注桩小阈值压实单次重写折叠 last-wins(内容等价)。"""
    ref, ctx, clock = _build_online(tmp_path)
    path = v4_acc_ledger_path(str(tmp_path))
    baseline = os.path.getsize(path)
    # 空闲 flush(无记录无封口): 零追加零 stat(黄金法则 1)
    mod, _c = _make_mod(tmp_path, clock)
    mod.start(ctx, dry_run=False)
    mod._flush_all_series()
    assert os.path.getsize(path) == baseline
    # 封口-only 变化: hour 2 完结(now 越过 3h), 无任何新记录 -> agg append -> acc 行追加
    clock.freeze(DAY0 + 3 * HOUR_SECONDS + 300)
    mod._flush_all_series()
    res = _parse_ledger(tmp_path)
    snap = res.snapshots[KEY_A]
    assert snap.cursor == CURSOR and snap.state.day_epoch == DAY0 and snap.state.pending == {}
    assert snap.state.day_hours == ref.day_hours + [  # hour 2 已封入开放日累计器
        _sealed_hour2(ref)
    ]
    assert snap.agg_fingerprint == stat_agg_fingerprint(str(tmp_path), KEY_A)  # 指纹 = 封口后 stat
    assert os.path.getsize(path) > baseline
    # 空闲再次 flush(封口已被上轮消化): 零追加
    baseline = os.path.getsize(path)
    mod._flush_all_series()
    assert os.path.getsize(path) == baseline
    # 压实触发: 注桩小阈值 + 新变化 -> append 后单次重写折叠(last-wins, 内容等价)
    monkeypatch.setattr(acc_ledger_mod, "ACC_LEDGER_COMPACT_BYTES", 10)
    mod._append_record(KEY_A, V4Sample(120, 60, 3_000_000, 4_000_000), DAY0 + 11100.0, DAY0 + 11100.0)
    mod._flush_all_series()
    res2 = _parse_ledger(tmp_path)
    assert res2.snapshots[KEY_A].cursor == DAY0 + 11100.0  # last-wins: 最新行胜
    lines = _ledger_text(tmp_path).splitlines()
    assert len(lines) == 2  # 头行 + 每系列单行(重写折叠)
    assert not res2.torn_tail and res2.bad_lines == 0


def _sealed_hour2(ref):
    """参照 pending hour 2 折叠态的 seal 行(封口-only 变化断言的期望行)。"""
    (hour2, ) = [h for h in ref.pending if h == DAY0 + 2 * HOUR_SECONDS]
    return ref.pending[hour2].seal(hour2)


def test_acc_wiring_stop_terminal_rows_idempotent(tmp_path):
    """stop 全系列终态行(多系列各带终态游标/指纹, 每系列恰一行); 同实例重复 stop 幂等
    (终态行单次闸 -> 账本字节不变); dry_run stop 零写(账本不触)。"""
    root = tmp_path / "a"
    _ref, ctx, clock = _build_online(root, keys=(KEY_A, KEY_B))
    res = read_acc_ledger(str(root))
    assert set(res.snapshots) == {KEY_A, KEY_B}
    for key in (KEY_A, KEY_B):
        snap = res.snapshots[key]
        assert snap.cursor == CURSOR and snap.agg_fingerprint == stat_agg_fingerprint(str(root), key)
        assert snap.state.pending and snap.state.day_epoch == DAY0
    assert _parse_ledger(root).data_lines == 2  # 每系列恰一行
    # 同实例重复 stop: 单次闸 -> 第二次零追加(黄金法则 1)
    mod, _c = _make_mod(root, clock)
    mod.start(ctx, dry_run=False)
    mod.stop()  # 本实例首次 stop: 终态行 append(内容与首发批一致)
    after_first = os.path.getsize(v4_acc_ledger_path(str(root)))
    mod.stop()
    assert os.path.getsize(v4_acc_ledger_path(str(root))) == after_first
    # dry_run: stop 短路(账本零写)
    root2 = tmp_path / "b"
    _ref2, ctx2, _ck2 = _build_online(root2)
    before2 = os.path.getsize(v4_acc_ledger_path(str(root2)))
    mod2, ctx3 = _make_mod(root2, FakeClock(start=NOW))
    mod2.start(ctx3, dry_run=True)
    _feed_chain(mod2, KEY_A)
    mod2.stop()
    assert os.path.getsize(v4_acc_ledger_path(str(root2))) == before2


def test_acc_wiring_hard_order_agg_append_failure(tmp_path, monkeypatch):
    """硬序(D7): agg 封口 append 失败 -> acc 行跳过(账本不领先于 agg 现状, 行内指纹/游标
    语义对齐 agg); 下轮无 agg 行时旗标复位 -> acc 行自愈补写。"""
    ref, ctx, clock = _build_online(tmp_path)
    mod, _c = _make_mod(tmp_path, clock)
    mod.start(ctx, dry_run=False)
    mod._append_record(KEY_A, V4Sample(200, 80, 2_500_000, 3_500_000), DAY0 + 9900.0, DAY0 + 9900.0)
    baseline = os.path.getsize(v4_acc_ledger_path(str(tmp_path)))
    real_append = TrafficV4Store.append_agg_rows

    def _boom(self, key, rows):
        raise OSError("disk full")

    monkeypatch.setattr(TrafficV4Store, "append_agg_rows", _boom)
    clock.freeze(DAY0 + 3 * HOUR_SECONDS + 300)  # hour 2 完结: 本轮封口确有 agg 行可 append
    mod._flush_all_series()  # agg append 失败 -> acc 行跳过(硬序)
    assert os.path.getsize(v4_acc_ledger_path(str(tmp_path))) == baseline  # 账本零追加
    monkeypatch.setattr(TrafficV4Store, "append_agg_rows", real_append)
    mod._flush_all_series()  # 下轮无 agg 行(封口已消化) -> 旗标复位 -> 自愈补写
    res = _parse_ledger(tmp_path)
    assert res.snapshots[KEY_A].cursor == DAY0 + 9900.0  # 自愈行游标 = 末记录槽位
    assert os.path.getsize(v4_acc_ledger_path(str(tmp_path))) > baseline


# ---------- crash 窗口语义两向(§04 S2) ----------


def test_acc_wiring_crash_raw_ahead_replay(tmp_path):
    """crash 用例 1: crash 落在 raw 追加与 acc 追加之间 —— 账本行/agg 均为上一 flush 现状
    (指纹未变), raw 尾 > 游标 -> 两向判定拦截 -> fallback 回放尾段(尾段小时重建进 pending)。"""
    ref, ctx, _ck = _build_online(tmp_path)
    store = TrafficV4Store(str(tmp_path))
    store.append_records(
        KEY_A,
        "2026-06-05",
        (DAY0 + 3 * HOUR_SECONDS + 10, INTERVAL),
        (V4Sample(300, 90, 5_000_000, 6_000_000), V4Sample(310, 95, 5_000_100, 6_000_100)),
        (5_000_000, 6_000_000),
    )  # 模拟: 上一 flush 的 raw 追加成功、agg/acc 未写(崩溃窗口)
    mod2, _c2 = _make_mod(tmp_path, FakeClock(start=NOW))
    mod2.start(ctx, dry_run=False)
    assert mod2.recovery_reads[KEY_A]["source"] == "rebuild"  # 两向判定拦截(raw 尾 10840 > 游标 9060)
    pending = mod2._agg_states[KEY_A].pending
    assert DAY0 + 3 * HOUR_SECONDS in pending and pending[DAY0 + 3 * HOUR_SECONDS].cov == 30.0
    assert acc_state_from_mod(mod2, KEY_A) != ref  # 回放态 = 参照态 + 尾段


def test_acc_wiring_crash_raw_behind_adopt(tmp_path, monkeypatch):
    """crash 用例 2: raw 追加失败(观测保留在累计器, R3「raw 尾 <= 游标」向)—— acc 行照写
    (cursor 超前于 raw 尾): 重启快路直采, 折叠态含 raw 已丢信用(agg 面比现状完整)。"""
    _ref, ctx, clock = _build_online(tmp_path)
    mod, _c = _make_mod(tmp_path, clock)
    mod.start(ctx, dry_run=False)

    def _boom(self, *a, **k):
        raise OSError("raw disk full")

    monkeypatch.setattr(TrafficV4Store, "append_records", _boom)
    mod._append_record(KEY_A, V4Sample(200, 80, 2_500_000, 3_500_000), DAY0 + 9900.0, DAY0 + 9900.0)
    mod.stop()  # raw 追加失败(观测保留累计器) -> agg 封口/acc 终态行照常(硬序不触)
    monkeypatch.setattr(TrafficV4Store, "append_records", TrafficV4Store.append_records)
    store = TrafficV4Store(str(tmp_path))
    assert raw_tail_beyond_cursor(store, KEY_A, DAY0 + 9900.0) is False  # raw 尾(9060) <= 游标(9900)
    snap = read_acc_ledger(str(tmp_path)).snapshots[KEY_A]
    assert snap.cursor == DAY0 + 9900.0  # 游标超前于 raw 尾(raw 无任何文件)
    assert DAY0 + 2 * HOUR_SECONDS in snap.state.pending  # 折叠态含全部已入账信用
    mod2, _c2 = _make_mod(tmp_path, FakeClock(start=NOW))
    counts = _count_reads(monkeypatch)
    mod2.start(ctx, dry_run=False)
    assert counts == {"day": 0, "segment": 0, "agg": 0}  # raw 尾(无) <= 游标 -> 快路直采
    assert mod2.recovery_reads[KEY_A]["source"] == "ledger"
    assert acc_state_from_mod(mod2, KEY_A) == acc_state_from_agg_snap(snap)  # agg 面比现状(raw)完整


# ---------- 快路 vs 重建对拍(D2) ----------


def test_acc_wiring_fastpath_vs_rebuild_equivalence(tmp_path, monkeypatch):
    """对拍(D2 口径): 同一语料(在线跑出账本, n 尾清 open_credit 使两路字段严格对齐)——
    快路直采 vs 删账本 fallback 重建: SeriesAgg 逐字段 bitwise + pending seal 行
    format_agg_row bitwise + 游标记忆一致; 快路读计数 0 vs 重建读计数 > 0。"""
    ref, ctx, _ck = _build_online(tmp_path)
    # 快路直采(零读)
    mod_fast, _c1 = _make_mod(tmp_path, FakeClock(start=NOW))
    counts_fast = _count_reads(monkeypatch)
    mod_fast.start(ctx, dry_run=False)
    assert counts_fast == {"day": 0, "segment": 0, "agg": 0}
    # fallback 重建(账本删除; 语料同源 —— 快路零写, agg/raw 未被触碰)
    os.remove(v4_acc_ledger_path(str(tmp_path)))
    mod_rebuild, _c2 = _make_mod(tmp_path, FakeClock(start=NOW))
    counts_rebuild = _count_reads(monkeypatch)
    mod_rebuild.start(ctx, dry_run=False)
    assert counts_rebuild["day"] + counts_rebuild["segment"] + counts_rebuild["agg"] > 0
    fast_state = acc_state_from_mod(mod_fast, KEY_A)
    rebuild_state = acc_state_from_mod(mod_rebuild, KEY_A)
    # SeriesAgg 逐字段 bitwise(全空 dict/list 用 == 深比较; fold/AggRow 均为值等 dataclass)
    assert rebuild_state == fast_state == ref  # 两路互等且 = 在线终态
    assert fast_state.pending and set(fast_state.pending) == {DAY0 + 2 * HOUR_SECONDS}
    assert fast_state.open_credit is None and fast_state.closed_day is None and fast_state.closed_month is None
    assert fast_state.day_epoch == DAY0 and len(fast_state.day_hours) == 2
    assert fast_state.month_epoch is None and fast_state.earliest_hour == DAY0
    # pending seal 行 bitwise(封口输出层)
    h2 = DAY0 + 2 * HOUR_SECONDS
    assert format_agg_row(fast_state.pending[h2].seal(h2)) == format_agg_row(rebuild_state.pending[h2].seal(h2))
    # 游标记忆一致(账本游标 / 重建读集尾槽)
    assert mod_fast._acc_cursors[KEY_A] == mod_rebuild._acc_cursors[KEY_A] == CURSOR


# ---------- 直采边界面 / 落盘失败面(覆盖率闸回补) ----------


def test_acc_wiring_adopt_with_stubs_and_null_cursor(tmp_path):
    """已关层存根随快照直采(AccSeriesState -> SeriesAgg stub 重建分支)+ 游标 None 快照
    直采(无 raw 候选文件 -> 两向判定 False, 游标记忆不置位); 尾块空块(有效 B 行后无
    记录)-> raw 判定保守回放; _tail_block_cursor 未知记录型 fail-fast。"""
    root = tmp_path / "stubs"
    root.mkdir()
    store = TrafficV4Store(str(root))
    store.append_agg_rows(KEY_A, (AggRow("hour", DAY0, 1, 2, 3, 4, 5, 6, 3600), ))  # agg 在场(指纹可配)
    state = AccSeriesState(
        closed_day=(DAY0 - 86400, [AggRow("hour", DAY0 - 86400, 1, 2, 3, 4, 5, 6, 3600)]),
        closed_month=(DAY0 - 30 * 86400, [AggRow("day", DAY0 - 30 * 86400, 1, 2, 3, 4, 5, 6, 86400)]),
        earliest_hour=DAY0 - 86400,
    )
    append_acc_snapshots(
        str(root),
        [AccSnapshot(key=KEY_A, cursor=None, agg_fingerprint=stat_agg_fingerprint(str(root), KEY_A), state=state)],
    )
    mod2, ctx2 = _make_mod(root, FakeClock(start=NOW))
    mod2.start(ctx2, dry_run=False)
    assert mod2.recovery_reads[KEY_A]["source"] == "ledger"  # 无 raw 候选文件: 游标 None 亦直采
    got = mod2._agg_states[KEY_A]
    assert got.closed_day == (DAY0 - 86400, [AggRow("hour", DAY0 - 86400, 1, 2, 3, 4, 5, 6, 3600)])
    assert got.closed_month == (DAY0 - 30 * 86400, [AggRow("day", DAY0 - 30 * 86400, 1, 2, 3, 4, 5, 6, 86400)])
    assert got.earliest_hour == DAY0 - 86400
    assert KEY_A not in mod2._acc_cursors  # 游标 None: 记忆不置位
    # 尾块空块: 有效 B 行后无记录(崩溃恰在 B 行落盘后)-> 尾槽不可判, 保守回放
    store2 = TrafficV4Store(str(tmp_path / "emptytail"))
    os.makedirs(v4_series_dir(str(tmp_path / "emptytail"), KEY_A))
    with open(store2.series_day_path(KEY_A, "2026-06-05"), "w", encoding="utf-8", newline="\n") as f:
        f.write("# auto-qb qb-traffic v4\nkey," + KEY_A + f"\nB,{DAY0 + 100},30\n")
    assert raw_tail_beyond_cursor(store2, KEY_A, DAY0 + 200.0) is True
    # 未知记录型 fail-fast(防御分支)
    with pytest.raises(TypeError):
        _tail_block_cursor(V4Block(DAY0, 30.0, 1, 2, (object(), )))


def test_acc_wiring_acc_append_failure_paths(tmp_path, monkeypatch, caplog):
    """acc 落盘失败面: flush 追加 OSError(首失败 WARNING + 保持 dirty, 持续失败 DEBUG)/
    游标 None 变化系列(行 cursor 空列)/ stop 硬序跳过与全跳过(snaps 空 return)/ stop
    终态行追加 OSError / 账本整读 OSError(恢复入口全体 fallback)/ 游标记忆捕获对零游标
    缓冲跳过。"""
    import logging

    from auto_qb.core.modules import traffic_sample_agg as _agg_mod
    from auto_qb.core.modules import traffic_sample_mod as _mod_pkg

    real_acc_append = _agg_mod.append_acc_snapshots
    calls = {"n": 0}

    def _boom(data_dir, snaps):
        calls["n"] += 1
        raise OSError(f"acc disk full #{calls['n']}")

    ref, ctx, clock = _build_online(tmp_path)
    mod, _c = _make_mod(tmp_path, clock)
    mod.start(ctx, dry_run=False)
    monkeypatch.setattr(_agg_mod, "append_acc_snapshots", _boom)
    mod._acc_dirty.add(KEY_A)
    mod._flush_all_series()  # 首次失败: WARNING + dirty 保持
    assert calls["n"] == 1 and KEY_A in mod._acc_dirty
    mod._flush_all_series()  # 持续失败: DEBUG 节流(不再刷屏)
    assert calls["n"] == 2 and KEY_A in mod._acc_dirty
    monkeypatch.setattr(_agg_mod, "append_acc_snapshots", real_acc_append)
    # 游标 None 变化系列(缓冲不在/记忆不在/信用 None -> 行 cursor 空列, 不炸)
    empty_key = "torrent:" + "ef" * 20
    mod._agg_states[empty_key] = SeriesAgg()
    mod._acc_dirty.add(empty_key)
    mod._flush_all_series()
    snap = _parse_ledger(tmp_path).snapshots[empty_key]
    assert snap.cursor is None  # cursor 空列(读侧对 None 保守 fallback)
    # stop 硬序跳过(agg append 失败系列)与游标 None 终态行 / 全跳过(snaps 空 -> return)
    clock2 = FakeClock(start=DAY0 + 3 * HOUR_SECONDS + 300)  # hour 2 完结: 封口确有 agg 行
    mod2, _c2 = _make_mod(tmp_path, clock2)
    mod2.start(ctx, dry_run=False)
    real_agg_append = TrafficV4Store.append_agg_rows

    def _agg_boom(self, key, rows):
        raise OSError("agg down")

    monkeypatch.setattr(TrafficV4Store, "append_agg_rows", _agg_boom)
    mod2._acc_dirty.add(KEY_A)
    mod2._flush_all_series()  # agg append 失败 -> 旗标置位
    monkeypatch.setattr(TrafficV4Store, "append_agg_rows", real_agg_append)
    empty_key = "torrent:" + "07" * 20
    mod2._agg_states[empty_key] = SeriesAgg()  # 游标 None 系列(不在失败旗标)随 stop 出终态行
    n_before = _parse_ledger(tmp_path).data_lines
    mod2._acc_stop_rows()  # KEY_A 跳过(硬序), empty_key 出 cursor 空列终态行
    res_stop = _parse_ledger(tmp_path)
    assert res_stop.snapshots[empty_key].cursor is None  # 游标 None 终态行
    assert res_stop.snapshots[KEY_A].cursor == CURSOR  # 硬序: 失败旗标系列无终态行(账本仍是上一 flush 行)
    assert KEY_A in mod2._acc_dirty  # dirty 未清(行没写成)
    # 全跳过: 剩余系列也进失败旗标 -> snaps 空 -> return(零追加)
    mod2._acc_stop_done = False
    mod2._acc_append_failed.add(empty_key)
    n_lines = _parse_ledger(tmp_path).data_lines
    mod2._acc_stop_rows()
    assert _parse_ledger(tmp_path).data_lines == n_lines
    # stop 终态行追加 OSError(旗标清后重试): 告警不上抛
    mod2._acc_append_failed.clear()
    mod2._acc_stop_done = False
    monkeypatch.setattr(_agg_mod, "append_acc_snapshots", _boom)
    with caplog.at_level(logging.WARNING, logger="auto_qb.core.modules.traffic_sample_mod"):
        mod2._acc_stop_rows()
    assert calls["n"] == 3
    assert any("stop 终态行追加失败" in r.message for r in caplog.records)
    monkeypatch.undo()
    # 账本整读 OSError(恢复入口): 全体 fallback, 不上抛
    root3 = tmp_path / "oserr"
    root3.mkdir()
    TrafficV4Store(str(root3)).append_agg_rows(KEY_A, (AggRow("hour", DAY0, 1, 1, 1, 1, 1, 1, 3600), ))
    mod3, ctx3 = _make_mod(root3, FakeClock(start=NOW))

    def _ledger_boom(data_dir):
        raise OSError("ledger locked")

    monkeypatch.setattr(_mod_pkg, "read_acc_ledger", _ledger_boom)
    mod3.start(ctx3, dry_run=False)
    assert mod3.recovery_reads[KEY_A]["source"] == "rebuild"
    assert mod3.recovery_stats["ledger_fastpath"] == 0
    monkeypatch.undo()
    # 游标记忆捕获: 零游标缓冲(防御形态)跳过不置位
    mod4, _c4 = _make_mod(tmp_path, FakeClock(start=NOW))
    zkey = "torrent:" + "99" * 20
    mod4._buffers[zkey] = BlockBuffer(
        start_epoch=None,
        interval_s=0,
        date_str=None,
        records=[],
        slots=0,
        prev_actual_ts=0.0,
        projected_ts=0.0,
        header_written=False,
        dl_base=None,
        up_base=None,
        has_r_row=False,
        last_dl_total=None,
        last_up_total=None,
    )
    mod4._flush_all_series()
    assert zkey not in mod4._acc_cursors


def test_acc_wiring_credit_day_file_unknown_record():
    """_agg_credit_day_file 未知块记录型 fail-fast(既有防御分支的定向钉面 —— 本批覆盖率
    闸回补: 本批新增代码吃掉闸门余量后需回补覆盖, 选择既有防御分支补测而非改闸)。"""
    from auto_qb.core.modules.traffic_sample_agg import _SampleAggMixin

    block = V4Block(DAY0, 30.0, 1, 2, (object(), ))
    with pytest.raises(TypeError, match="未知块记录型"):
        _SampleAggMixin._agg_credit_day_file({}, SimpleNamespace(blocks=(block, )), None, None)


def test_acc_wiring_z_run_collapsed_slots_direct():
    """B2 塌缩区间分支定向钉面(spacing << ULP(first_ts): 相邻槽舍入同点 -> 桶内无正长度
    区间 -> ki 回退到负 -> 桶不入账, 与逐槽路径一致; 既有防御分支的覆盖率闸回补)。
    逐槽参照语义: 全部槽位塌缩成同一点 => 零长度区间不产 merge => hour_samples 空。"""
    from auto_qb.core.modules.traffic_sample_agg import _agg_credit_z_run
    from auto_qb.core.traffic_store import V4ZeroRun

    samples: dict = {}
    rec = V4ZeroRun(100, 1000, 2000, None, 1000, 2000)  # 块首形态退化(direct 调用自定 spacing)
    _agg_credit_z_run(samples, 1780588800.0, 1e-9, rec, None)  # span ~1e-7 << ULP(~2.4e-7)
    assert samples == {}  # 全塌缩: 零正长度区间, 零入账
    # 半塌缩边界(spacing 跨 ULP 栅格): 塌缩链回退后仍可能命中正长度区间 —— 两形态都不崩
    samples2: dict = {}
    _agg_credit_z_run(samples2, 1780588800.0, 5e-8, V4ZeroRun(100, 1000, 2000, None, 1000, 2000), None)
    assert isinstance(samples2, dict)


def test_acc_wiring_compact_oserror_swallowed(tmp_path, monkeypatch, caplog):
    """压实调用 OSError 护栏(评审 major): compact_acc_ledger 读侧/重写侧可上抛 OSError ——
    flush 与 stop 两处调用都告警不上抛(flush 不穿透采样轮; stop 不跳过 host.stop_all()
    的 state.save/锁释放), 行已追加成功、tmp+os.replace 纪律下原文件完好下轮自愈。"""
    import logging

    from auto_qb.core.modules import traffic_sample_agg as _agg_mod

    def _compact_boom(data_dir):
        raise OSError("compact locked")

    _ref, ctx, clock = _build_online(tmp_path)
    mod, _c = _make_mod(tmp_path, clock)
    mod.start(ctx, dry_run=False)
    monkeypatch.setattr(_agg_mod, "compact_acc_ledger", _compact_boom)
    with caplog.at_level(logging.WARNING, logger="auto_qb.core.modules.traffic_sample_mod"):
        mod._append_record(KEY_A, V4Sample(200, 80, 2_500_000, 3_500_000), DAY0 + 9900.0, DAY0 + 9900.0)
        mod._flush_all_series()  # append 成功 + 压实 OSError -> 吞掉, 采样轮不受影响
    assert _parse_ledger(tmp_path).snapshots[KEY_A].cursor == DAY0 + 9900.0  # 行已落账(不牵连)
    assert any("压实检查失败" in r.message for r in caplog.records)
    # stop 路径同样不上抛(终态行落账 + 压实失败吞掉, stop 流程照常走完)
    mod2, _c2 = _make_mod(tmp_path, FakeClock(start=NOW))
    mod2.start(ctx, dry_run=False)
    with caplog.at_level(logging.WARNING, logger="auto_qb.core.modules.traffic_sample_mod"):
        mod2.stop()
    # mod2 直采账本末行(cursor 9900)-> 终态行同值 last-wins; 关键 = stop 走完未上抛
    assert read_acc_ledger(str(tmp_path)).snapshots[KEY_A].cursor == DAY0 + 9900.0
    assert any("stop 压实检查失败" in r.message for r in caplog.records)


def test_acc_wiring_dt1_boundary_replays(tmp_path):
    """容差边界(评审 minor): dt_ms=1 钳制边界(时钟回拨/亚毫秒到达写 dt_ms=1 合法行)下,
    crash 恰落在 raw 追加与 acc 追加之间且尾槽恰为该 1ms 记录时, 尾游标-游标 ≈ 1e-3 必须
    大于 ACC_RAW_TAIL_TOL_S(5e-4)判回放 —— 容差若为 1e-3 会误判直采丢该记录 obs(「误判
    只向多回放单向倾斜」反向); 表达式噪声侧(尾槽恰等游标)仍直采。"""
    store = TrafficV4Store(str(tmp_path))
    # 块首 r 槽 9060(=账本游标)+ 非块首 dt_ms=1 记录 -> 尾槽 9060.001(超前恰 1ms)
    store.append_records(
        KEY_A,
        "2026-06-05",
        (DAY0 + 9060, INTERVAL),
        (V4Sample(100, 50, 100, 200), V4Sample(200, 60, 300, 400, 1)),
        (100, 200),
    )
    assert raw_tail_beyond_cursor(store, KEY_A, CURSOR) is True  # 1e-3 > 5e-4: 必判回放
    # 噪声侧: 尾槽恰等账本游标 -> False(直采); 表达式差几个 ULP(~1e-6)远低于容差
    store2 = TrafficV4Store(str(tmp_path / "noise"))
    store2.append_records(KEY_A, "2026-06-05", (DAY0 + 9060, INTERVAL), (V4Sample(100, 50, 100, 200), ), (100, 200))
    assert raw_tail_beyond_cursor(store2, KEY_A, CURSOR) is False
