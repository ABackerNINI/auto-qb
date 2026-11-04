"""test_traffic_store_store 测试计划: qB 口径流量 v4 存储层(plan 26-10-05-2200 §01-§05; v1/v2/v3 退役面已随各代删除)

## 测试计划(每个测试函数一条)
handler 接线(S2a, v4 写侧):
- test_restart_continuity_appends_without_truncation: 重启(新模块实例)后同天文件开新块接续不断史 + 首窗 null(基线不落盘)
- test_handler_writes_v4_only_no_legacy_side_effects: handler 零触旧目录 qb-traffic/ 与 qb-traffic-v4 之外的旧代目录(R2 留存不读);
  断连轮 n 游程; stop() 封 n 游程落 v4
- test_handler_dry_run_persists_nothing: dry_run 全程零文件零目录
- test_handler_deleted_torrent_no_new_records: 删种即零新记录(冻结语义), 缓冲随 flush 收尾
- test_handler_readded_torrent_keeps_history: 重加 -> 同文件续写, 断采间隔如实写成显式 dt
- test_handler_dry_run_skips_store_construction: dry_run 不构造 v4 存储层, 零文件

v4 纯函数区(B1 立并于批 2 接线, plan 26-10-05-2200 §01):

v4 写侧存储(S2a/S2b, TrafficV4Store):
- test_v4_store_append_records_day_file_shape: 新文件头行(v4)+key+B 行(带块基线)+r/z/n delta 行 roundtrip; 全空零操作
- test_v4_store_header_once_and_torn_tail_repair: 跨 flush 同块头只写一次; 残半行补换行照常收(kill 不放大)
- test_v4_store_agg_append_read_and_torn_tail: agg 追加/读取/残行/空解析
- test_v4_store_trim_agg_hours: hour 裁剪(唯一原子重写点; day/month 永久; 无到龄零写)
- test_v4_store_trim_agg_hours_replace_locked: 裁剪重写被占用退避重试

v4 读侧解析缓存(S3a/S3b, V4DayCache):

体量实测(plan 26-10-04-1957 §09.1 口径沿用到 v4):

v4 活尾快照(S6 验收):

v4 定约专测(B1 用例, 批 2 回归):
- test_v4_cumsum_restore_pointwise: delta 以块基线复原绝对值逐点相等(大基线量级 + 块内
  递增 delta r/z 混排 + 块首 z 立基线 delta=0 + 多块基线独立)

P1-T1.2 守卫与容错簇(计划 26-10-20-2101, 覆盖率缺口清偿):

mut-core W4 S5 定向补测(变异审计确认真洞守阵, 2026-10-31; 红验 tmp-analysis/redverify-s5-w4.py):
- test_v4_store_trim_day_month_only_no_hour_rows: trim_34 —— 只剩 day/month 行的 agg.dat 裁剪
  返 None 零写不崩(hour 全部到龄已裁的常态)
- test_v4_store_append_batches_leave_no_blank_lines: _ensure_15/17/18/22 —— 两批 append 后原始
  文本无空行(尾字节查补不恒插 
, 坏行占比分母不被稀释)
- test_v4_store_trim_replaces_invalid_utf8_bytes: trim_15/19/24/25 —— 裁剪独享读路径同纪律
- test_v4_store_write_side_lf_only_contract: app_rec_58/62 + app_agg_23/27 + wtp_23/27 —— 三写点
  open/fdopen 显式 newline="
" 且落盘原始字节无 
(实参断言在 Linux 面同样可杀)
- test_v4_store_append_records_block_base_none_writes_3col_b: app_rec_22 —— header 非 None 且
  block_base=None 显式写 3 列 B 无基线块(None 不得解包崩)

mut-core W4 S6 定向补测(2026-11-02, issue 26-10-31-1539 两件清偿; 红验 tmp-analysis/redverify-s6-w4.py):

线程/时钟纪律: 需要确定时刻的用例经构造期 clock=FakeClock 注入(采样模块经 qbmanager 装配链
透传, S3 后不再经 stdlib time 名寻址); 文件一律落在 tmp_path(test.* 已内置 TMPDIR, 不手工加前缀)。
"""

import builtins

import inspect

import logging

import os

import re

import tempfile

import threading

import time

from datetime import datetime

import pytest

import auto_qb.core.traffic_store as traffic_store_module

from clock import FakeClock

from auto_qb.config import QbTraffic

from auto_qb.core.modules.traffic_sample_mod import GLOBAL_SERIES_KEY

from auto_qb.core.traffic_store import (
    DRIFT_TOL_MS,
    DT_MS_MAX,
    HEADER_LINE_V4,
    HOUR_SECONDS,
    REWRITE_BACKOFF_S,
    REWRITE_RETRIES,
    TORRENTS_DIR_NAME,
    TRAFFIC_V4_DIR_NAME,
    V4_AGG_CACHE_MAX_ENTRIES,
    AggRow,
    LiveTail,
    LiveTailRun,
    TrafficV4Store,
    V4Block,
    V4DayCache,
    V4HourSample,
    V4NullRun,
    V4Sample,
    V4ZeroRun,
    format_agg_row,
    format_v4_b_row,
    format_v4_day_text,
    format_v4_n_row,
    format_v4_r_row,
    format_v4_z_row,
    parse_v4_agg_text,
    parse_v4_day_text,
    v4_agg_file_path,
    v4_block_agg_totals,
    v4_block_gap_continuous,
    v4_block_slots,
    v4_bucket_width_s,
    v4_date_str_epoch,
    v4_day_epoch,
    v4_day_file_date,
    v4_day_file_path,
    v4_epoch_date_str,
    v4_hour_agg,
    v4_live_tail_slots,
    v4_merge_agg,
    v4_month_epoch,
    v4_next_month_epoch,
    v4_rel_dir_to_key,
    v4_rollup_agg,
    v4_root_dir,
    v4_series_dir,
    v4_window_dates,
    v4_z_totals_ramp,
)

from helpers import (
    FakeClient,
    FakeTorrent,
    active_torrent,
    make_manager,
    seed_store,
    server_state,
    write_dat_lines,
)

from traffic_store_support import (
    H1,
    HOUR,
    _S2B_H0,
    _agg_row,
    _mgr,
    _read_text,
    _run_sample,
)


def test_restart_continuity_appends_without_truncation(tmp_path, monkeypatch):
    """重启接续: 新模块实例(baselines/缓冲空)在同一天文件上开新块接续追加不断史;
    重启后首窗 null(基线不落盘, S1 语义); 新块块首 = 重启后首个记录"""
    fixed = H1 + 100.0
    clock = FakeClock(start=fixed)  # 构造期注入(S3 monkeypatch 收敛)
    # 第一段运行: 一轮采样(r 记录随 flush 落盘)
    mgr = _mgr(tmp_path, QbTraffic(enabled=True, sample_interval=30), clock=clock)
    mgr.store.server_state = server_state()
    seed_store(mgr, [active_torrent()])
    mod = mgr.host.get("qb_traffic")
    mod.start(mgr.ctx, dry_run=False)
    _run_sample(mgr)
    mod._flush_all_series()
    gpath = v4_day_file_path(str(tmp_path), "global", v4_epoch_date_str(fixed))
    tpath = v4_day_file_path(str(tmp_path), "torrent:HASH123", v4_epoch_date_str(fixed))
    assert len(_read_text(gpath).splitlines()) == 4  # 头 + key + B + 1 行
    # 重启: 全新 manager(同 data_dir), 计数器推进
    mgr2 = _mgr(tmp_path, QbTraffic(enabled=True, sample_interval=30), clock=clock)
    mgr2.store.server_state = server_state(alltime_dl=10_001_000, alltime_ul=20_002_000)
    seed_store(mgr2, [active_torrent(downloaded=5_000_700, uploaded=3_000_400)])
    mod2 = mgr2.host.get("qb_traffic")
    mod2.start(mgr2.ctx, dry_run=False)
    _run_sample(mgr2)
    assert mod2.latest[GLOBAL_SERIES_KEY].dl_inc is None  # 基线不落盘 -> 首窗 null(S1 语义)
    mod2._flush_all_series()
    parsed = parse_v4_day_text(_read_text(gpath))
    assert len(parsed.blocks) == 2  # dat 接续开新块, 不断史
    assert parsed.blocks[0].start_epoch == int(fixed) and parsed.blocks[1].start_epoch == int(fixed)
    assert len(parse_v4_day_text(_read_text(tpath)).blocks) == 2


def test_handler_writes_v4_only_no_legacy_side_effects(tmp_path, monkeypatch):
    """写侧 v4 单点(§6.2 换代矩阵沿用到 v4): handler 全程零触旧目录 qb-traffic/ 与
    qb-traffic-v3/(各代退役删除或 R2 留存不读); 断连轮全局 n 游程照常推进; stop() 后
    n 游程封口落 v4 天文件"""
    clock = FakeClock(start=H1 + 100.0)  # 构造期注入(S3 monkeypatch 收敛)
    mgr = _mgr(tmp_path, QbTraffic(enabled=True, sample_interval=30), clock=clock)
    mgr.store.server_state = server_state()
    seed_store(mgr, [active_torrent()])
    mod = mgr.host.get("qb_traffic")
    mod.start(mgr.ctx, dry_run=False)
    assert _run_sample(mgr) is None
    mgr.client = None  # 断连轮: 照常记 n 槽(生命周期判定已退役, 无 stale 快照误判面)
    clock.freeze(H1 + 130.0)
    _run_sample(mgr)
    assert mod._open_runs[GLOBAL_SERIES_KEY].kind == "n"
    assert not (tmp_path / "qb-traffic").exists()  # 旧目录零文件零目录
    mod.stop()  # 优雅收尾: 封 n 游程 + 落 v4
    assert not (tmp_path / "qb-traffic").exists()
    text = _read_text(v4_day_file_path(str(tmp_path), "global", v4_epoch_date_str(H1 + 100)))
    recs = parse_v4_day_text(text).blocks[0].records
    assert [type(r) for r in recs] == [V4Sample, V4NullRun]  # r + 断连 n 槽


def test_handler_dry_run_persists_nothing(tmp_path):
    """dry_run 全程零文件: start 跳过对账, handler 不落盘不封口(观测写盘属真实副作用)"""
    mgr = _mgr(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = server_state()
    seed_store(mgr, [active_torrent()])
    mod = mgr.host.get("qb_traffic")
    mod.start(mgr.ctx, dry_run=True)
    _run_sample(mgr, dry_run=True)
    assert mod.latest != {}  # 采样照常进内存
    assert not (tmp_path / "qb-traffic").exists() and not (tmp_path / TRAFFIC_V4_DIR_NAME).exists()


def test_handler_deleted_torrent_no_new_records(tmp_path, monkeypatch):
    """删种冻结语义(§04.5 沿用): 删种即不再产新块/新记录(不在 by_hash 本就无采样) ——
    已有缓冲随 flush 落盘收尾, 后续轮零新增记录, 无 index 注册表动作"""
    clock = FakeClock(start=H1 + 100.0)  # 构造期注入(S3 monkeypatch 收敛)
    mgr = _mgr(tmp_path, QbTraffic(enabled=True, sample_interval=30), clock=clock)
    mgr.store.server_state = server_state()
    seed_store(mgr, [active_torrent()])
    mod = mgr.host.get("qb_traffic")
    mod.start(mgr.ctx, dry_run=False)
    _run_sample(mgr)  # r 进缓冲
    mgr.store.by_hash.pop("HASH123")  # 删种
    clock.freeze(H1 + 160.0)
    _run_sample(mgr)  # 删种轮: 该系列无采样
    clock.freeze(H1 + 700.0)
    _run_sample(mgr)  # flush 驱动触发: 缓冲收尾落盘
    parsed = parse_v4_day_text(
        _read_text(v4_day_file_path(str(tmp_path), "torrent:HASH123", v4_epoch_date_str(H1 + 100)))
    )
    assert [type(r) for r in parsed.blocks[0].records] == [V4Sample]  # 恰删种前 1 条, 后续零新增
    # v4 关块谓词下带 r 行的块随 flush 关闭, 空壳缓冲被内存卫生整个清除(比 v3 的空 records 更强)
    assert "torrent:HASH123" not in mod._buffers


def test_handler_readded_torrent_keeps_history(tmp_path, monkeypatch):
    """重加续写: 同 hash 重加(活跃, 计数器推进) -> 新记录接在原块续写(同文件, 历史
    保留); 断采间隔由累积漂移判据如实写成显式 dt; 重加后计数器回落由既有判重置兜底"""
    clock = FakeClock(start=H1 + 100.0)  # 构造期注入(S3 monkeypatch 收敛)
    mgr = _mgr(tmp_path, QbTraffic(enabled=True, sample_interval=30), clock=clock)
    mgr.store.server_state = server_state()
    seed_store(mgr, [active_torrent()])
    mod = mgr.host.get("qb_traffic")
    mod.start(mgr.ctx, dry_run=False)
    _run_sample(mgr)
    tpath = v4_day_file_path(str(tmp_path), "torrent:HASH123", v4_epoch_date_str(H1 + 100))
    mgr.store.by_hash.pop("HASH123")
    clock.freeze(H1 + 160.0)
    _run_sample(mgr)  # 删种期: 无记录
    # 同 hash 重加(活跃, 计数器推进) -> 续写
    seed_store(mgr, [active_torrent(downloaded=6_000_000, uploaded=4_000_000)])
    clock.freeze(H1 + 220.0)
    _run_sample(mgr)
    mod._flush_all_series()
    recs = parse_v4_day_text(_read_text(tpath)).blocks[0].records
    assert len(recs) == 2 and all(isinstance(r, V4Sample) for r in recs)  # 历史保留 + 续写
    assert recs[1].dt_ms == 120_000  # 断采 120s 如实入行(从链上锚点 H1+100 起算)
    assert recs[1].dl_total == 6_000_000  # 重加后的 totals 快照


def test_handler_dry_run_skips_store_construction(tmp_path, monkeypatch):
    """dry_run 不构造任何存储层(零触盘, 观测写盘属真实副作用); 删种轮同样零存储动作"""
    clock = FakeClock(start=H1 + 100.0)  # 构造期注入(S3 monkeypatch 收敛)
    mgr = _mgr(tmp_path, QbTraffic(enabled=True, sample_interval=30), clock=clock)
    mgr.store.server_state = server_state()
    seed_store(mgr, [active_torrent()])
    mod = mgr.host.get("qb_traffic")
    mod.start(mgr.ctx, dry_run=True)
    mgr.store.by_hash.pop("HASH123")
    _run_sample(mgr, dry_run=True)
    assert mod._v4store is None  # v4 存储层未构造
    assert not (tmp_path / TRAFFIC_V4_DIR_NAME).exists()  # v4 侧零文件
    assert not (tmp_path / "qb-traffic").exists()  # 旧目录零动作(R2 留存不读)


def test_v4_store_append_records_day_file_shape(tmp_path):
    """TrafficV4Store.append_records: 新文件建头行(v4) + key 行, header 随批写 B 行(携带块基线),
    r/z/n 记录逐行落盘(r/z 存相对基线 delta)且 parse_v4_day_text roundtrip 还原绝对值;
    records+header 全空零操作不建文件"""
    st = TrafficV4Store(str(tmp_path))
    date = v4_epoch_date_str(H1)
    st.append_records("global", date, (H1, 30), (V4Sample(1, 2, 3, 4), V4ZeroRun(2, 5, 6), V4NullRun(3)), (3, 4))
    text = _read_text(st.series_day_path("global", date))
    lines = text.splitlines()
    assert lines[0] == HEADER_LINE_V4 and lines[1] == "key,global" and lines[2] == f"B,{H1},30,3,4"
    assert lines[3:] == ["r,1,2,0,0", "z,2,2,2,2,2", "n,3"]  # r/z 存相对块基线(3,4)的 delta; z 末端列缺省 = 显式退化同值
    parsed = parse_v4_day_text(text)
    assert parsed.key == "global" and len(parsed.blocks) == 1 and len(parsed.blocks[0].records) == 3
    # 全空调用: 零操作(不建文件不建目录, 惰性创建纪律)
    st.append_records("torrent:X", date, None, (), None)
    assert not (tmp_path / TRAFFIC_V4_DIR_NAME / "torrents").exists()


def test_v4_store_header_once_and_torn_tail_repair(tmp_path):
    """跨 flush 同块 header 只传一次(不重复 B 行); 崩溃残留半行(完整合法行缺换行)先补
    换行照常收数据 —— kill 丢失不放大(每 flush 查补一次)"""
    st = TrafficV4Store(str(tmp_path))
    date = v4_epoch_date_str(H1)
    path = st.series_day_path("global", date)
    st.append_records("global", date, (H1, 30), (V4Sample(1, 1, 1, 1), ), (1, 1))
    st.append_records("global", date, None, (V4Sample(2, 2, 2, 2), ), (1, 1))  # 同块续写: header=None
    parsed = parse_v4_day_text(_read_text(path))
    assert len(parsed.blocks) == 1 and len(parsed.blocks[0].records) == 2  # 单 B 行单块
    with open(path, "a", encoding="utf-8", newline="") as f:
        f.write("r,9,9,9,9")  # 崩溃残留: 完整行但无换行
    st.append_records("global", date, None, (V4Sample(3, 3, 3, 3), ), (1, 1))
    parsed = parse_v4_day_text(_read_text(path))
    # 残行补 \n 后成为完整合法行照常收(2 + 残行 + 1 = 4), 零坏行零 torn
    assert len(parsed.blocks) == 1 and len(parsed.blocks[0].records) == 4
    assert parsed.bad_lines == 0 and not parsed.torn_tail


def test_v4_store_agg_append_read_and_torn_tail(tmp_path):
    """append_agg_rows/read_agg(§04.2/§04.3): 新文件建头行(v4)+key 行, hour/day/month
    9 列混存追加 + roundtrip; 空行批零操作(不建文件); 崩溃残留无换行尾先补换行照常收;
    缺失/空文件 = 空解析结果(key=None)"""
    st = TrafficV4Store(str(tmp_path))
    key = "torrent:ABC"
    rows = (
        _agg_row("hour", _S2B_H0), _agg_row("day", v4_day_epoch(_S2B_H0)), _agg_row("month", v4_month_epoch(_S2B_H0))
    )
    st.append_agg_rows(key, rows)  # 新文件: 惰性建目录 + 头行 + key 行
    lines = _read_text(v4_agg_file_path(str(tmp_path), key)).splitlines()
    assert lines[0] == HEADER_LINE_V4 and lines[1] == f"key,{key}"
    assert lines[2:] == [format_agg_row(r) for r in rows]
    parsed = st.read_agg(key)
    assert parsed.key == key
    assert parsed.hours == (rows[0], ) and parsed.days == (rows[1], ) and parsed.months == (rows[2], )
    # 空行批: 零操作不建文件(惰性纪律)
    st.append_agg_rows("torrent:EMPTY", ())
    assert not os.path.exists(v4_agg_file_path(str(tmp_path), "torrent:EMPTY"))
    # 崩溃残留: 末行无换行 -> 下批追加先补换行, 两批数据都完整可读
    with open(v4_agg_file_path(str(tmp_path), key), "a", encoding="utf-8", newline="") as f:
        f.write(format_agg_row(_agg_row("hour", _S2B_H0 + HOUR, dl_avg=99)))
    st.append_agg_rows(key, (_agg_row("hour", _S2B_H0 + 2 * HOUR, dl_avg=77), ))
    parsed = st.read_agg(key)
    assert [h.dl_avg for h in parsed.hours] == [10, 99, 77]  # 残行补换行后照常收
    assert parsed.bad_lines == 0 and not parsed.torn_tail
    # 缺失/空文件 = 空解析结果(key=None, 全空)
    empty = st.read_agg("torrent:NOPE")
    assert empty.key is None and empty.hours == () and empty.data_lines == 0
    os.makedirs(v4_series_dir(str(tmp_path), "torrent:BLANK"))
    (tmp_path / TRAFFIC_V4_DIR_NAME / "torrents" / "BLANK" / "agg.dat").write_text("", encoding="utf-8")
    assert st.read_agg("torrent:BLANK").key is None


def test_v4_store_trim_agg_hours(tmp_path):
    """trim_agg_hours(§04.5, 唯一 tmp+fsync+os.replace 原子重写点): epoch >=
    now-rollup_window 的 hour 行保留(边界含); day/month 行全保留(永久, D7 不裁);
    无到龄行零写(same_content, 文件字节不变); 返回重写后最老 hour epoch(空 = None)"""
    st = TrafficV4Store(str(tmp_path))
    key = "global"
    window = 30 * 86400.0
    now = 3000 * 86400.0
    aged, boundary, fresh = now - window - 2 * HOUR, now - window, now - HOUR
    st.append_agg_rows(
        key, (
            _agg_row("hour", aged, dl_avg=1),
            _agg_row("hour", boundary, dl_avg=2),
            _agg_row("hour", fresh, dl_avg=3),
            _agg_row("day", v4_day_epoch(aged)),
            _agg_row("month", v4_month_epoch(aged)),
        )
    )
    path = v4_agg_file_path(str(tmp_path), key)
    assert st.trim_agg_hours(key, now, window) == boundary  # 到龄行裁掉, 返回新最老
    parsed = st.read_agg(key)
    assert [h.epoch for h in parsed.hours] == [boundary, fresh]
    # day/month 行永久: 不按龄裁剪
    assert parsed.days[0].epoch == v4_day_epoch(aged) and parsed.months[0].epoch == v4_month_epoch(aged)
    # same_content: 无到龄行零写(文件字节不变, 黄金法则 1)
    snap = _read_text(path)
    assert st.trim_agg_hours(key, now, window) == boundary
    assert _read_text(path) == snap
    # 全部到龄: hours 清空, day/month 照常保留
    assert st.trim_agg_hours(key, now + 40 * 86400, window) is None
    parsed = st.read_agg(key)
    assert parsed.hours == () and len(parsed.days) == 1 and len(parsed.months) == 1
    # 缺失 = None
    assert st.trim_agg_hours("torrent:NOPE", now, window) is None


def test_v4_store_trim_agg_hours_replace_locked(tmp_path, monkeypatch):
    """裁剪重写被占用(Windows 读侧竞态, PermissionError): 退避重试 xREWRITE_RETRIES 后
    放弃本轮 —— 原文件完好返回原最老 epoch(下轮重试); 重试窗口内恢复则正常重写"""
    st = TrafficV4Store(str(tmp_path))
    key = "global"
    window = 30 * 86400.0
    now = 3000 * 86400.0
    aged = now - window - HOUR
    st.append_agg_rows(key, (_agg_row("hour", aged), ))
    calls = {"n": 0}
    real_replace = os.replace  # 打桩前捕获真函数(桩内不能再走被替换的 os.replace)

    def _always_locked(src, dst):
        calls["n"] += 1
        raise PermissionError(13, "locked")

    monkeypatch.setattr("auto_qb.core.traffic_store.os.replace", _always_locked)
    assert st.trim_agg_hours(key, now, window) == aged  # 放弃本轮: 返回原最老 epoch
    assert calls["n"] == REWRITE_RETRIES + 1  # 首试 + 退避重试 3 次(第 4 次仍锁 -> 放弃)
    assert len(st.read_agg(key).hours) == 1  # 原文件完好(原子重写失败不损数据)
    # 重试窗口内恢复: 第 2 次起放行 -> 重写成功
    calls["n"] = 0

    def _locked_once(src, dst):
        calls["n"] += 1
        if calls["n"] == 1:
            raise PermissionError(13, "locked")
        real_replace(src, dst)

    monkeypatch.setattr("auto_qb.core.traffic_store.os.replace", _locked_once)
    assert st.trim_agg_hours(key, now, window) is None  # 唯一 hour 行到龄被裁 -> 空
    assert st.read_agg(key).hours == ()


def test_v4_cumsum_restore_pointwise():
    """delta 以块基线复原绝对值逐点相等(B1「cumsum 复原」): 大基线量级(all-time ~10^13,
    报告 §06 字节对照同量级)+ 块内递增 delta(delta = 块内已传量)r/z 混排逐行复原 == 原始
    绝对 totals; 块首 z 立基线(delta = 0)与块首 r 同为合法基线立点; 多块基线独立互不串扰"""
    base_dl, base_up = 54_975_581_388_800, 5_497_558_138_880  # ~50 TiB / 5 TiB
    d_deltas = [0, 200_000_000, 500_000_000, 500_000_000, 900_000_000]  # 块内已传量递增(z 持平)
    u_deltas = [0, 20_000_000, 50_000_000, 50_000_000, 90_000_000]
    recs = (
        V4Sample(100_000_000, 10_000_000, base_dl + d_deltas[0], base_up + u_deltas[0]),  # 块首 r 立基线
        V4Sample(100_000_000, 10_000_000, base_dl + d_deltas[1], base_up + u_deltas[1], dt_ms=2001),
        V4Sample(100_000_000, 10_000_000, base_dl + d_deltas[2], base_up + u_deltas[2]),
        V4ZeroRun(
            10,
            base_dl + d_deltas[3],
            base_up + u_deltas[3],
            dt_ms=20005,
            dl_total_end=base_dl + d_deltas[3],
            up_total_end=base_up + u_deltas[3],
        ),  # 空闲: delta 持平; 末端列显式退化(= 冻结列)roundtrip
        V4Sample(100_000_000, 10_000_000, base_dl + d_deltas[4], base_up + u_deltas[4]),
    )
    block = V4Block(1000, 2, base_dl, base_up, recs)
    text = format_v4_day_text("global", (block, ))
    lines = text.splitlines()
    assert lines[2] == f"B,1000,2,{base_dl},{base_up}"
    assert lines[3] == "r,100000000,10000000,0,0" and lines[4] == "r,100000000,10000000,200000000,20000000,2001"
    assert lines[6] == "z,10,500000000,50000000,500000000,50000000,20005"
    parsed = parse_v4_day_text(text)
    assert parsed.bad_lines == 0 and parsed.blocks[0] == block
    # 逐行复原 == 原始绝对值(基线 + 本行 delta, 逐点)
    restored = [(r.dl_total - base_dl, r.up_total - base_up) for r in parsed.blocks[0].records]
    assert restored == list(zip(d_deltas, u_deltas))
    # 块首 z 立基线(delta = 0)+ 多块基线独立
    b2 = V4Block(
        9000,
        2,
        7_000_000,
        8_000_000,
        (
            V4ZeroRun(5, 7_000_000, 8_000_000, dl_total_end=7_000_000, up_total_end=8_000_000),
            V4Sample(1, 1, 7_000_100, 8_000_100),
        ),
    )
    parsed2 = parse_v4_day_text(format_v4_day_text("global", (block, b2)))
    assert parsed2.blocks[1] == b2
    assert parsed2.blocks[1].records[0].dl_total == 7_000_000  # 块首 z: 基线 = 该快照, 复原持平


def test_v4_store_trim_day_month_only_no_hour_rows(tmp_path):
    """trim_agg_hours 的 hour 全部到龄已裁常态(agg.dat 只剩 day/month 行): 返 None 零写不崩
    (变异面: oldest 取 parsed.hours[0] 的条件被破坏 -> IndexError 崩 flush 裁剪点)"""
    st = TrafficV4Store(str(tmp_path))
    key = "global"
    window = 30 * 86400.0
    now = 3000 * 86400.0
    st.append_agg_rows(key, (_agg_row("day", v4_day_epoch(now - HOUR)), _agg_row("month", v4_month_epoch(now - HOUR))))
    path = v4_agg_file_path(str(tmp_path), key)
    snap = _read_text(path)
    assert st.trim_agg_hours(key, now, window) is None
    assert _read_text(path) == snap  # 零写(黄金法则 1)


def test_v4_store_append_batches_leave_no_blank_lines(tmp_path):
    """追加写尾字节查补(§03, 每 flush 一次): 已有文件尾字节恰为 \\n 时不补空行 —— 两批
    append 后原始文本无空行(变异面: 末字节定位/比较被破坏 -> 每批前恒插空行, 坏行占比
    分母 data_lines 系统性虚增, 唯一损坏告警信号被稀释 + 文件膨胀)"""
    st = TrafficV4Store(str(tmp_path))
    key = "global"
    r1, r2 = _agg_row("hour", _S2B_H0), _agg_row("hour", _S2B_H0 + HOUR, dl_avg=11)
    st.append_agg_rows(key, (r1, ))
    st.append_agg_rows(key, (r2, ))
    expected = "\n".join([HEADER_LINE_V4, f"key,{key}", format_agg_row(r1), format_agg_row(r2)]) + "\n"
    assert _read_text(v4_agg_file_path(str(tmp_path), key)) == expected  # 无空行, 精确形状
    parsed = st.read_agg(key)
    assert [h.epoch for h in parsed.hours] == [_S2B_H0, _S2B_H0 + HOUR]
    assert parsed.bad_lines == 0 and parsed.data_lines == 3  # 分母 = key + 两行(不含插空行)


def test_v4_store_trim_replaces_invalid_utf8_bytes(tmp_path):
    """trim_agg_hours 的读路径(裁剪独享 open, 不经 _read_parse)同 errors="replace" 纪律:
    非 UTF-8 字节记坏行不炸, 无到龄行零写返回最老 hour epoch"""
    st = TrafficV4Store(str(tmp_path))
    key = "torrent:BAD"
    os.makedirs(v4_series_dir(str(tmp_path), key))
    window = 30 * 86400.0
    now = 3000 * 86400.0
    fresh = int(now - HOUR)
    path = v4_agg_file_path(str(tmp_path), key)
    with open(path, "wb") as f:
        f.write((HEADER_LINE_V4 + "\n" + f"key,{key}\n").encode("utf-8"))
        f.write(b"\xff\xfe broken\n")
        f.write(f"hour,{fresh},10,20,5,8,100,200,3600\n".encode("utf-8"))
    snap = open(path, "rb").read()  # 含非法字节, 快照比对走 bytes(守阵自身不越 errors 纪律)
    assert st.trim_agg_hours(key, now, window) == fresh  # kept == hours -> 零写
    assert open(path, "rb").read() == snap


def test_v4_store_write_side_lf_only_contract(tmp_path, monkeypatch):
    """行尾固定 \\n 契约(§03/§04.5): append_records / append_agg_rows / trim 原子重写三个写点
    的 open/fdopen 都显式传 newline="\\n"(Windows os.linesep 不得落盘), 落盘原始字节无 \\r。
    newline 实参断言在 Linux 面同样可杀(文本模式缺省 newline 在 Linux 不加 \\r, 字节断言
    对该变异形态不敏感)"""
    recorded = []
    real_open, real_fdopen = builtins.open, os.fdopen

    def spying_open(file, mode="r", *args, **kwargs):
        recorded.append(("open", mode, kwargs.get("newline")))
        return real_open(file, mode, *args, **kwargs)

    def spying_fdopen(fd, mode="r", *args, **kwargs):
        recorded.append(("fdopen", mode, kwargs.get("newline")))
        return real_fdopen(fd, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", spying_open)
    monkeypatch.setattr(os, "fdopen", spying_fdopen)
    st = TrafficV4Store(str(tmp_path))
    key = "global"
    st.append_records(key, "2026-10-31", (1000, 30), (V4NullRun(2), ), block_base=None)
    st.append_agg_rows(key, (_agg_row("hour", _S2B_H0), _agg_row("hour", _S2B_H0 + HOUR, dl_avg=11)))
    window = 30 * 86400.0
    now = _S2B_H0 + window + 2 * HOUR  # 两条 hour 都到龄 -> 触发原子重写
    assert st.trim_agg_hours(key, now, window) is None
    writes = [r for r in recorded if (r[0] == "open" and r[1] == "a") or (r[0] == "fdopen" and r[1] == "w")]
    assert writes == [("open", "a", "\n"), ("open", "a", "\n"), ("fdopen", "w", "\n")]
    for p in (st.series_day_path(key, "2026-10-31"), v4_agg_file_path(str(tmp_path), key)):
        with open(p, "rb") as f:
            assert b"\r" not in f.read()


def test_v4_store_append_records_block_base_none_writes_3col_b(tmp_path):
    """append_records 契约钉住: header 非 None 且 block_base=None = 无基线块(3 列 B, 仅 n
    游程合法)—— 显式 None 不得解包崩(变异面: 恒真条件让 None 进解包 TypeError)"""
    st = TrafficV4Store(str(tmp_path))
    key = "global"
    st.append_records(key, "2026-10-31", (1000, 30), (V4NullRun(2), V4NullRun(1, dt_ms=61000)), block_base=None)
    raw = _read_text(st.series_day_path(key, "2026-10-31"))
    assert raw == "\n".join([HEADER_LINE_V4, f"key,{key}", "B,1000,30", "n,2", "n,1,61000"]) + "\n"
    parsed = parse_v4_day_text(raw)
    assert len(parsed.blocks) == 1 and parsed.blocks[0].dl_base is None and parsed.blocks[0].up_base is None
