"""test_traffic_store 测试计划: qB 口径流量 v3 存储层(plan 26-10-04-1957 §02/§03/§04/§05; v1/v2 退役面已随 S5 删除)

## 测试计划(每个测试函数一条)
handler 接线(S2a 重写, S5 清理):
- test_restart_continuity_appends_without_truncation: 重启(新模块实例)后同天文件开新块接续不断史 + 首窗 null(基线不落盘)
- test_handler_writes_v3_only_no_legacy_side_effects: handler 零触旧目录 qb-traffic/(R2 留存不读); 断连轮 n 游程; stop() 封 n 游程落 v3
- test_handler_dry_run_persists_nothing: dry_run 全程零文件零目录
- test_empty_data_dir_persists_nothing: data_dir 为空(防御, 真实配置恒非空) -> 零文件零目录(CWD 无泄漏)
- test_all_persist_writes_on_caller_thread: 全部 v3 批量落盘(TrafficV3Store.append_records)写在主循环线程, 模块不建线程(黄金法则 5)
- test_handler_deleted_torrent_no_new_records: v3 冻结语义 = 删种即零新记录, 缓冲随 flush 收尾
- test_handler_readded_torrent_keeps_history: 重加 -> 原块续写, 断采间隔如实写成显式 dt
- test_handler_dry_run_skips_store_construction: dry_run 不构造 v3 存储层, 零文件

v3 纯函数区(S1, S5 起为现行唯一实现):
- test_v3_day_roundtrip_with_drift_rows: roundtrip —— 序列化->解析->dt 链推算与实测序列逐一相等(显式 dt/z+n 游程/标称缺省)
- test_v3_amortized_run_chain_self_consistent: 均摊定位与链式自洽; 块首游程端点含
- test_v3_parse_bad_line_family_cursor_not_advanced: 坏行族逐项计坏(v1/v2 旧头行整文件不匹配 —— R2 识别-忽略保留 / r 列数 {5,6} 之外 /
  dt_ms 非法族 / 负速率 / run_len<1 / interval<1 / 块头前数据行), 好行不受牵连且游标不推进
- test_v3_no_equal_interval_drift_immunity: 纯等间隔路径不存在(证伪)
- test_v3_bucket_width_effective_dt: 桶宽 max(1, ceil(有效dt)) 各形态
- test_v3_paths_dates_and_window: 按天目录与路径解析(§06.2)
- test_v3_agg_roundtrip_and_legacy_8col: agg.dat roundtrip + 8 列旧行兜底 cov_s=3600(防御性保留, 计划 §02.2 明文)
- test_v3_hour_agg_dt_weighted_degenerate_to_v2: dt 加权 hour 聚合, 等间隔退化公式对照钉住
- test_v3_rollup_strict_level_by_level: 逐级派生 day/month
- test_v3_format_fail_fast_and_torn_tail: 序列化 fail-fast + 撕裂尾行豁免口径

v3 写侧存储(S2a/S2b, TrafficV3Store):
- test_v3_store_append_records_day_file_shape: 新文件头行+key+B 行+r/z/n roundtrip; 全空零操作
- test_v3_store_header_once_and_torn_tail_repair: 块头只写一次; 残半行补换行照常收(kill 不放大)
- test_v3_store_series_has_data_gate: v3 数据门(目录存在且含 >=1 个 .dat)
- test_v3_store_agg_append_read_and_torn_tail: agg 追加/读取/残行/空解析
- test_v3_store_series_keys_and_day_dates: 恢复入口(系列键扫描/日期补算窗过滤/read_day)
- test_v3_store_trim_agg_hours: hour 裁剪(v3 唯一原子重写点; day/month 永久; 无到龄零写)
- test_v3_store_trim_agg_hours_replace_locked: 裁剪重写被占用退避重试
- test_v3_store_evict_expired_series: 系列按龄淘汰(整目录; 龄期由文件名日期算)

v3 读侧解析缓存(S3a/S3b, V3DayCache):
- test_v3_day_cache_hit_and_invalidate: mtime+size 键控命中与两向失效; 缺失哨兵
- test_v3_day_cache_window_reads_only_involved_files: 24h 窗只开 2 个日期文件(open 计数断言, S5 复核)
- test_v3_day_cache_budget_lru: 字节预算 LRU
- test_v3_agg_cache_hit_and_invalidate: agg 缓存命中/失效/OSError 上抛不落缓存

S5 实测(plan §09.1):
- test_v3_row_width_vs_legacy_layout_bytes: 体量对比 —— 同一构造采样序列按 v2 行型布局与 v3 行型
  序列化的实测字节对照(r 行 40-52B -> 30-40B; 空闲段游程压缩)

v3 活尾快照(S6 验收追加, 2026-10-05):
- test_v3_live_tail_slots_mirror_identity_family: 镜像保证族 —— 磁盘部分块槽 + 活尾槽 == 整块
  重算槽(逐槽恒等): 块全量未落盘(head_pending 整块重算, 含块首 r/块首游程)/块中途 flush 后
  倒推复原(显式 dt + z/n 游程混排)/全部落盘仅剩开放游程
- test_v3_live_tail_slots_open_run_forms: 开放游程封口形态 —— 无开放块块首形([int(run.start),
  last_seen] 端点含, n=1 单槽)/有开放块非块首形((链终点, last_seen] 均摊, 末槽 = last_seen)
- test_v3_live_tail_slots_invariants_fail_fast: block_open=False 带 records/head_pending -> ValueError;
  未知记录型 -> TypeError

线程/时钟纪律: 需要确定时刻的用例经 monkeypatch 固定 time.time(测试进程内单线程, 恢复由
monkeypatch 保证); 文件一律落在 tmp_path(test.* 已内置 TMPDIR, 不手工加前缀)。
"""
import builtins
import os
import threading
import time
from datetime import datetime

import pytest

import auto_qb.core.traffic_store as traffic_store_module
from auto_qb.config import QbTraffic
from auto_qb.core.modules.traffic_sample_mod import GLOBAL_SERIES_KEY, TASK_NAME
from auto_qb.core.taskqueue import Task
from auto_qb.core.traffic_store import (
    DRIFT_TOL_MS,
    DT_MS_MAX,
    HEADER_LINE_V3,
    HOUR_SECONDS,
    REWRITE_RETRIES,
    TRAFFIC_V3_DIR_NAME,
    AggRow,
    LiveTail,
    LiveTailRun,
    TrafficV3Store,
    V3Block,
    V3DayCache,
    V3HourSample,
    V3NullRun,
    V3Sample,
    V3ZeroRun,
    format_agg_row,
    format_v3_b_row,
    format_v3_day_text,
    format_v3_n_row,
    format_v3_r_row,
    format_v3_z_row,
    parse_v3_agg_text,
    parse_v3_day_text,
    v3_agg_file_path,
    v3_block_slots,
    v3_bucket_width_s,
    v3_date_str_epoch,
    v3_day_epoch,
    v3_day_file_date,
    v3_day_file_path,
    v3_epoch_date_str,
    v3_hour_agg,
    v3_live_tail_slots,
    v3_month_epoch,
    v3_rel_dir_to_key,
    v3_rollup_agg,
    v3_root_dir,
    v3_series_dir,
    v3_window_dates,
)
from helpers import FakeClient, FakeTorrent, make_manager, seed_store

HOUR = HOUR_SECONDS
H0 = 10 * HOUR  # 被封口的小时桶起点
H1 = 11 * HOUR  # 当前小时桶起点(封口触发时刻所在桶)


def _ss(**overrides) -> dict:
    base = {
        "dl_info_speed": 1024,
        "up_info_speed": 2048,
        "alltime_dl": 10_000_000,
        "alltime_ul": 20_000_000,
        "dl_info_data": 1_000_000,
        "up_info_data": 2_000_000,
    }
    base.update(overrides)
    return base


def _active_torrent(hash="HASH123", **kw) -> FakeTorrent:
    kw.setdefault("dlspeed", 512)
    kw.setdefault("upspeed", 256)
    kw.setdefault("downloaded", 5_000_000)
    kw.setdefault("uploaded", 3_000_000)
    kw.setdefault("downloaded_session", 500_000)
    kw.setdefault("uploaded_session", 300_000)
    return FakeTorrent(hash=hash, **kw)


def _mgr(tmp_path, qb_traffic, data_dir=True) -> object:
    """带 qb_traffic 段的测试 manager(同 test_traffic_sample._mgr_with_traffic 口径)"""
    mgr = make_manager(str(tmp_path / "state.json"))
    if data_dir:
        mgr.config.data_dir = str(tmp_path)
    mgr.client = FakeClient()
    if qb_traffic is not None:
        mgr.config.qb_traffic = qb_traffic
    return mgr


def _run_sample(mgr, dry_run=False) -> bool:
    mod = mgr.host.get("qb_traffic")
    task = Task("internal", TASK_NAME, interval=30, handler=mod.handle_traffic_sample)
    return mod.handle_traffic_sample(task, dry_run=dry_run)


def _write_dat(path, lines) -> None:
    """手工构造 dat 文件(行列表逐行写, 换行行尾)"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


def _read_text(path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ---------- handler 接线 ----------


def test_restart_continuity_appends_without_truncation(tmp_path, monkeypatch):
    """重启接续(v3): 新模块实例(baselines/缓冲空)在同一天文件上开新块接续追加不断史;
    重启后首窗 null(基线不落盘, S1 语义); 新块块首 = 重启后首个记录"""
    fixed = H1 + 100.0
    monkeypatch.setattr("auto_qb.core.modules.traffic_sample_mod.time.time", lambda: fixed)
    # 第一段运行: 一轮采样(r 记录随 flush 落盘)
    mgr = _mgr(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    seed_store(mgr, [_active_torrent()])
    mod = mgr.host.get("qb_traffic")
    mod.start(mgr.ctx, dry_run=False)
    _run_sample(mgr)
    mod._flush_all_series()
    gpath = v3_day_file_path(str(tmp_path), "global", v3_epoch_date_str(fixed))
    tpath = v3_day_file_path(str(tmp_path), "torrent:HASH123", v3_epoch_date_str(fixed))
    assert len(_read_text(gpath).splitlines()) == 4  # 头 + key + B + 1 行
    # 重启: 全新 manager(同 data_dir), 计数器推进
    mgr2 = _mgr(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr2.store.server_state = _ss(alltime_dl=10_001_000, alltime_ul=20_002_000)
    seed_store(mgr2, [_active_torrent(downloaded=5_000_700, uploaded=3_000_400)])
    mod2 = mgr2.host.get("qb_traffic")
    mod2.start(mgr2.ctx, dry_run=False)
    _run_sample(mgr2)
    assert mod2.latest[GLOBAL_SERIES_KEY].dl_inc is None  # 基线不落盘 -> 首窗 null(S1 语义)
    mod2._flush_all_series()
    parsed = parse_v3_day_text(_read_text(gpath))
    assert len(parsed.blocks) == 2  # dat 接续开新块, 不断史
    assert parsed.blocks[0].start_epoch == int(fixed) and parsed.blocks[1].start_epoch == int(fixed)
    assert len(parse_v3_day_text(_read_text(tpath)).blocks) == 2


# ---------- handler 接线 ----------


def test_handler_writes_v3_only_no_legacy_side_effects(tmp_path, monkeypatch):
    """写侧翻 v3(§6.2 换代矩阵): handler 全程零触旧目录 qb-traffic/(v2 写侧与触发面已随
    S5 退役删除, R2 旧目录留存不读); 断连轮全局 n 游程照常推进; stop() 后 n 游程封口落
    v3 天文件"""
    t = {"now": H1 + 100.0}
    monkeypatch.setattr("auto_qb.core.modules.traffic_sample_mod.time.time", lambda: t["now"])
    mgr = _mgr(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    seed_store(mgr, [_active_torrent()])
    mod = mgr.host.get("qb_traffic")
    mod.start(mgr.ctx, dry_run=False)
    assert _run_sample(mgr) is True
    mgr.client = None  # 断连轮: 照常记 n 槽(生命周期判定已退役, 无 stale 快照误判面)
    t["now"] = H1 + 130.0
    assert _run_sample(mgr) is True
    assert mod._open_runs[GLOBAL_SERIES_KEY].kind == "n"
    assert not (tmp_path / "qb-traffic").exists()  # 旧目录零文件零目录
    mod.stop()  # 优雅收尾: 封 n 游程 + 落 v3
    assert not (tmp_path / "qb-traffic").exists()
    text = _read_text(v3_day_file_path(str(tmp_path), "global", v3_epoch_date_str(H1 + 100)))
    recs = parse_v3_day_text(text).blocks[0].records
    assert [type(r) for r in recs] == [V3Sample, V3NullRun]  # r + 断连 n 槽


def test_handler_dry_run_persists_nothing(tmp_path):
    """dry_run 全程零文件: start 跳过对账, handler 不落盘不封口(观测写盘属真实副作用)"""
    mgr = _mgr(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    seed_store(mgr, [_active_torrent()])
    mod = mgr.host.get("qb_traffic")
    mod.start(mgr.ctx, dry_run=True)
    assert _run_sample(mgr, dry_run=True) is True
    assert mod.latest != {}  # 采样照常进内存
    assert not (tmp_path / "qb-traffic").exists() and not (tmp_path / TRAFFIC_V3_DIR_NAME).exists()


def test_empty_data_dir_persists_nothing(tmp_path, monkeypatch):
    """data_dir 为空(防御: 真实配置恒非空, loaders 默认 auto-qb-data) -> 零文件零目录零泄漏"""
    monkeypatch.chdir(tmp_path)  # CWD 钉到 tmp: 断言无相对路径泄漏
    mgr = _mgr(tmp_path, QbTraffic(enabled=True, sample_interval=30), data_dir=False)
    mgr.store.server_state = _ss()
    seed_store(mgr, [_active_torrent()])
    mod = mgr.host.get("qb_traffic")
    mod.start(mgr.ctx, dry_run=False)
    assert _run_sample(mgr) is True
    assert mod.latest != {}
    assert sorted(str(p) for p in tmp_path.rglob("*")) == []


def test_all_persist_writes_on_caller_thread(tmp_path, monkeypatch):
    """单写线程不变式: 全部 v3 批量落盘(TrafficV3Store.append_records)发生在调用 run_due
    的线程(= 主循环线程)内, 模块不建线程(黄金法则 5)"""
    mgr = _mgr(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    seed_store(mgr, [_active_torrent()])
    mod = mgr.host.get("qb_traffic")
    mod.start(mgr.ctx, dry_run=False)
    mod._last_flush = time.time() - 601  # 预置过期: 本轮 handler 内 flush 驱动即触发
    seen = []
    real = TrafficV3Store.append_records

    def spy(self, key, date_str, header, records):
        seen.append((key, threading.get_ident()))
        return real(self, key, date_str, header, records)

    monkeypatch.setattr(TrafficV3Store, "append_records", spy)
    threads_before = threading.active_count()
    assert mgr.task_queue.run_due(max_tasks=10) == 1
    assert {k for k, _ in seen} == {"global", "torrent:HASH123"}
    assert all(ident == threading.get_ident() for _, ident in seen)
    assert threading.active_count() == threads_before


def test_handler_deleted_torrent_no_new_records(tmp_path, monkeypatch):
    """v3 冻结语义(§04.5 平移): 删种即不再产新块/新记录(不在 by_hash 本就无采样) ——
    已有缓冲随 flush 落盘收尾, 后续轮零新增记录, 无 index 注册表动作"""
    t = {"now": H1 + 100.0}
    monkeypatch.setattr("auto_qb.core.modules.traffic_sample_mod.time.time", lambda: t["now"])
    mgr = _mgr(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    seed_store(mgr, [_active_torrent()])
    mod = mgr.host.get("qb_traffic")
    mod.start(mgr.ctx, dry_run=False)
    _run_sample(mgr)  # r 进缓冲
    mgr.store.by_hash.pop("HASH123")  # 删种
    t["now"] = H1 + 160.0
    _run_sample(mgr)  # 删种轮: 该系列无采样
    t["now"] = H1 + 700.0
    _run_sample(mgr)  # flush 驱动触发: 缓冲收尾落盘
    parsed = parse_v3_day_text(
        _read_text(v3_day_file_path(str(tmp_path), "torrent:HASH123", v3_epoch_date_str(H1 + 100)))
    )
    assert [type(r) for r in parsed.blocks[0].records] == [V3Sample]  # 恰删种前 1 条, 后续零新增
    assert mod._buffers["torrent:HASH123"].records == []


def test_handler_readded_torrent_keeps_history(tmp_path, monkeypatch):
    """重加续写(v3): 同 hash 重加(活跃, 计数器推进) -> 新记录接在原块续写(同文件, 历史
    保留); 断采间隔由累积漂移判据如实写成显式 dt; 重加后计数器回落由既有判重置兜底"""
    t = {"now": H1 + 100.0}
    monkeypatch.setattr("auto_qb.core.modules.traffic_sample_mod.time.time", lambda: t["now"])
    mgr = _mgr(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    seed_store(mgr, [_active_torrent()])
    mod = mgr.host.get("qb_traffic")
    mod.start(mgr.ctx, dry_run=False)
    _run_sample(mgr)
    tpath = v3_day_file_path(str(tmp_path), "torrent:HASH123", v3_epoch_date_str(H1 + 100))
    mgr.store.by_hash.pop("HASH123")
    t["now"] = H1 + 160.0
    _run_sample(mgr)  # 删种期: 无记录
    # 同 hash 重加(活跃, 计数器推进) -> 续写
    seed_store(mgr, [_active_torrent(downloaded=6_000_000, uploaded=4_000_000)])
    t["now"] = H1 + 220.0
    assert _run_sample(mgr) is True
    mod._flush_all_series()
    recs = parse_v3_day_text(_read_text(tpath)).blocks[0].records
    assert len(recs) == 2 and all(isinstance(r, V3Sample) for r in recs)  # 历史保留 + 续写
    assert recs[1].dt_ms == 120_000  # 断采 120s 如实入行(从链上锚点 H1+100 起算)
    assert recs[1].dl_total == 6_000_000  # 重加后的 totals 快照


def test_handler_dry_run_skips_store_construction(tmp_path, monkeypatch):
    """dry_run 不构造任何存储层(零触盘, 观测写盘属真实副作用); 删种轮同样零存储动作"""
    t = {"now": H1 + 100.0}
    monkeypatch.setattr("auto_qb.core.modules.traffic_sample_mod.time.time", lambda: t["now"])
    mgr = _mgr(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    seed_store(mgr, [_active_torrent()])
    mod = mgr.host.get("qb_traffic")
    mod.start(mgr.ctx, dry_run=True)
    mgr.store.by_hash.pop("HASH123")
    assert _run_sample(mgr, dry_run=True) is True
    assert mod._v3store is None  # v3 存储层未构造
    assert not (tmp_path / TRAFFIC_V3_DIR_NAME).exists()  # v3 侧零文件
    assert not (tmp_path / "qb-traffic").exists()  # 旧目录零动作(R2 留存不读)


# ---------- v3 纯函数区(plan 26-10-04-1957 S1, S5 起为现行唯一实现) ----------


def _v3_day_text(lines) -> str:
    """手工构造 v3 天文件文本(行列表逐行写, \\n 行尾)"""
    return "\n".join(lines) + "\n"


def test_v3_day_roundtrip_with_drift_rows():
    """S1 验收 roundtrip: 序列化 -> 解析 -> 游标 dt 链推算与原始采样实测序列逐一相等
    (含显式 dt_ms 漂移行 / z+n 相邻游程 / 标称缺省行); 多块与 obs 形态逐项核对"""
    interval = 30
    # 原始实测序列(稳态漂移 d=0.4s > tol=250ms -> 漂移行写显式 dt_ms; 游程内均匀间距
    # 与引导间隔一致 —— 均摊定位在该前提下逐点精确)
    recs = [
        V3Sample(10, 20, 1000, 2000),  # r0 块首 @1000.0(无 dt)
        V3Sample(11, 21, 1100, 2100, dt_ms=30400),  # r1 @1030.4
        V3Sample(12, 22, 1200, 2200, dt_ms=30400),  # r2 @1060.8
        # z 游程 3 槽 @1091.6/1122.4/1153.2: dt = 末槽 - 链上锚点(r2) = 92.4s
        V3ZeroRun(3, 1200, 2200, dt_ms=92400),
        # 相邻 n 游程 2 槽 @1184.0/1214.8: dt 含引导间隔 = 1214.8 - 1153.2 = 61.6s
        V3NullRun(2, dt_ms=61600),
        V3Sample(13, 23, 1300, 2300, dt_ms=30800),  # r3 @1245.6
        V3Sample(14, 24, 1400, 2400, dt_ms=30800),  # r4 @1276.4
        V3Sample(15, 25, 1500, 2500),  # r5 标称缺省行 @1306.4
        V3Sample(16, 26, 1600, 2600, dt_ms=30400),  # r6 @1336.8
    ]
    expected_ts = [1000.0, 1030.4, 1060.8, 1091.6, 1122.4, 1153.2, 1184.0, 1214.8, 1245.6, 1276.4, 1306.4, 1336.8]
    block = V3Block(start_epoch=1000, interval_s=interval, records=tuple(recs))
    text = format_v3_day_text("global", (block, ))
    lines = text.splitlines()
    assert lines[0] == HEADER_LINE_V3 and lines[1] == "key,global"
    assert lines[2] == "B,1000,30" and lines[3] == "r,10,20,1000,2000" and lines[6] == "z,3,1200,2200,92400"
    parsed = parse_v3_day_text(text)
    assert parsed.key == "global" and parsed.bad_lines == 0 and parsed.data_lines == 11 and not parsed.torn_tail
    assert len(parsed.blocks) == 1 and parsed.blocks[0] == block  # 解析还原 == 原始行型
    slots = v3_block_slots(parsed.blocks[0])
    assert len(slots) == 12  # 7 r 槽 + 3 z 槽 + 2 n 槽
    assert [s.ts for s in slots] == pytest.approx(expected_ts, abs=1e-6)
    # obs 形态: r 槽带观测 / z 槽速率恒 0 且 totals 快照恒定 / n 槽 null
    assert slots[0].obs == (10, 20, 1000, 2000) and not slots[0].is_zero
    assert all(s.obs == (0, 0, 1200, 2200) and s.is_zero for s in slots[3:6])
    assert all(s.obs is None and not s.is_zero for s in slots[6:8])
    # 有效 dt: r1 = 显式 30.4s / 游程槽 = 均摊 30.8s / r5 缺省 = 30.0s
    assert slots[1].dt_s == pytest.approx(30.4, abs=1e-9)
    assert slots[3].dt_s == pytest.approx(30.8, abs=1e-9)
    assert slots[10].dt_s == 30.0
    # 多块: 第二块独立游标(各自 B.start 起算)
    b2 = V3Block(
        start_epoch=5000,
        interval_s=60,
        records=(V3Sample(1, 1, 1, 1), V3Sample(1, 1, 1, 1, dt_ms=61000)),
    )
    parsed2 = parse_v3_day_text(format_v3_day_text("torrent:ABC", (block, b2)))
    assert parsed2.key == "torrent:ABC" and len(parsed2.blocks) == 2
    assert [s.ts for s in v3_block_slots(parsed2.blocks[1])] == pytest.approx([5000.0, 5061.0], abs=1e-6)


def test_v3_amortized_run_chain_self_consistent():
    """均摊定位(§02.3): 非块首游程槽均摊 [锚点, 锚点+dt] 且末槽恰在游程实测终点;
    其后首 r 的 dt 以游程终点为基准(链式自洽); 块首游程端点含(首槽 = B.start);
    缺省游程按标称栅格"""
    # 非块首显式 z 游程: 锚点 1000, advance 90s -> 槽 1030/1060/1090(末槽 = 锚点+dt)
    b = V3Block(
        start_epoch=1000,
        interval_s=30,
        records=(V3Sample(1, 1, 1, 1), V3ZeroRun(3, 5, 6, dt_ms=90000), V3Sample(2, 2, 2, 2, dt_ms=30000)),
    )
    slots = v3_block_slots(b)
    assert [s.ts for s in slots] == pytest.approx([1000.0, 1030.0, 1060.0, 1090.0, 1120.0], abs=1e-9)
    assert slots[1].ts == pytest.approx(1000.0 + 90.0 / 3, abs=1e-9)  # 首槽在锚点 + dt/len(非锚点)
    assert slots[3].ts == pytest.approx(1000.0 + 90.0, abs=1e-9)  # 末槽恰在游程实测终点
    # 其后首 r 的 dt 以游程终点(1090, 实测)为基准: dt_ms=30000 -> 1120, 链式自洽
    assert slots[4].ts == pytest.approx(1090.0 + 30.0, abs=1e-9)
    # 缺省 z 游程(非块首, 前置 r 行): 标称栅格(槽 = 锚点 + k x interval, k=1..len), 其后 r 标称接续
    b2 = V3Block(
        start_epoch=1000,
        interval_s=30,
        records=(V3Sample(1, 1, 1, 1), V3ZeroRun(2, 5, 6), V3Sample(1, 1, 1, 1)),
    )
    assert [s.ts for s in v3_block_slots(b2)] == pytest.approx([1000.0, 1030.0, 1060.0, 1090.0], abs=1e-9)
    # 块首游程: 首槽 = B.start(端点含), 槽距 = dt/(len-1), 游标终点 = 末槽
    b3 = V3Block(
        start_epoch=5000,
        interval_s=30,
        records=(V3ZeroRun(3, 5, 6, dt_ms=60000), V3Sample(1, 1, 1, 1, dt_ms=30000)),
    )
    slots3 = v3_block_slots(b3)
    assert [s.ts for s in slots3] == pytest.approx([5000.0, 5030.0, 5060.0, 5090.0], abs=1e-9)
    # 相邻游程(z -> n, R2 纪律): n 的 dt 含引导间隔(链上锚点 = 前游程终点), 槽均摊精确
    b4 = V3Block(
        start_epoch=1000,
        interval_s=30,
        records=(V3Sample(1, 1, 1, 1), V3ZeroRun(2, 5, 6, dt_ms=60000), V3NullRun(2, dt_ms=61000)),
    )
    assert [s.ts for s in v3_block_slots(b4)] == pytest.approx([1000.0, 1030.0, 1060.0, 1090.5, 1121.0], abs=1e-9)


def test_v3_parse_bad_line_family_cursor_not_advanced():
    """v3 坏行族逐项计坏(§02.3): v1/v2 头行整文件不匹配 / r 列数 {5,6} 之外 /
    dt_ms 非法族(0/负/超上界/非数值) / 负速率 / run_len<1 / interval<1 / 块头前数据行;
    好行不受牵连且游标不推进(坏行前后好行推算时刻与干净文件一致)"""
    good_head = [HEADER_LINE_V3, "key,global", "B,1000,30"]
    bad_lines = [
        "r,1,1,1",  # r 4 列(列数 {5,6} 之外)
        "r,1,1,1,1,1,1",  # r 7 列
        "r,1,1,1,1,0",  # dt_ms = 0(须正整数)
        "r,1,1,1,1,-5",  # dt_ms 负
        f"r,1,1,1,1,{DT_MS_MAX + 1}",  # dt_ms 超上界
        "r,1,1,1,1,abc",  # dt_ms 非数值
        "r,-1,1,1,1",  # 负速率
        "z,0,1,1",  # run_len < 1
        "z,2,1",  # z 3 列
        "z,2,1,1,0",  # z dt_ms = 0
        "n,0",  # n run_len < 1
        "n,2,1,1",  # n 4 列
        f"n,2,{DT_MS_MAX + 1}",  # n dt_ms 超上界
        "garbage",  # 未知行型
        "key,other",  # 重复 key 行
        "B,1000,0",  # interval_s < 1 -> 整行坏(不开新块)
    ]
    good_tail = ["r,2,2,2,2", "B,2000,60", "r,3,3,3,3,45000"]
    text = _v3_day_text(good_head + ["r,1,1,1,1"] + bad_lines + good_tail)
    parsed = parse_v3_day_text(text)
    assert parsed.key == "global" and parsed.bad_lines == len(bad_lines) and parsed.data_lines == 22
    # 坏行不落 records 且游标不推进: 块 1 = B(1000,30) + r@1000 + r@1030(坏 B 未开新块)
    assert len(parsed.blocks) == 2
    assert [len(b.records) for b in parsed.blocks] == [2, 1]
    assert [s.ts for s in v3_block_slots(parsed.blocks[0])] == pytest.approx([1000.0, 1030.0], abs=1e-9)
    assert [s.ts for s in v3_block_slots(parsed.blocks[1])] == pytest.approx([2000.0], abs=1e-9)
    # 干净文件对照: 同一批好行的推算时刻完全一致(坏行不影响游标链)
    clean = parse_v3_day_text(_v3_day_text(good_head + ["r,1,1,1,1"] + good_tail))
    assert [s.ts for b in clean.blocks
            for s in v3_block_slots(b)] == [s.ts for b in parsed.blocks for s in v3_block_slots(b)]
    # dt_ms 恰好上界合法
    ok = parse_v3_day_text(_v3_day_text(good_head + [f"r,1,1,1,1,{DT_MS_MAX}"]))
    assert ok.bad_lines == 0 and ok.blocks[0].records[0].dt_ms == DT_MS_MAX
    # 旧版头行(含 v1/v2)整文件不匹配格式 —— R2 换代, v3 读侧不设双读(识别-忽略, S5 保留)
    for head in ("# auto-qb qb-traffic v1", "# auto-qb qb-traffic v2", "key,global"):
        old = parse_v3_day_text(_v3_day_text([head, "key,global", "B,1000,30", "r,1,1,1,1"]))
        assert old.key is None and old.blocks == () and old.bad_lines == 4 and old.data_lines == 4


def test_v3_no_equal_interval_drift_immunity():
    """纯等间隔路径不存在(§02.3): 构造 d̄>0 全显式 dt 序列 —— dt 链逐点等于实测,
    等间隔推算(start + i x interval)漂移远超 tol(证无累积误差)"""
    interval, n = 30, 20
    actual = [2000.0 + i * 30.4 for i in range(n)]
    recs = tuple(V3Sample(i, i, i, i, dt_ms=None if i == 0 else 30400) for i in range(n))
    parsed = parse_v3_day_text(format_v3_day_text("global", (V3Block(2000, interval, recs), )))
    slots = v3_block_slots(parsed.blocks[0])
    assert [s.ts for s in slots] == pytest.approx(actual, abs=1e-6)  # dt 链逐点相等
    equal_interval = [2000.0 + i * interval for i in range(n)]
    max_drift = max(abs(a - e) for a, e in zip(actual, equal_interval))
    assert max_drift > 1.0  # 等间隔推算在块尾漂移 > 1s(远超 tol=250ms) —— 该路径不存在于实现
    assert DRIFT_TOL_MS == 250  # D2: 模块常量非配置键


def test_v3_bucket_width_effective_dt():
    """桶宽纯函数(§02.3): 逐记录 max(1, ceil(有效dt)); 有效dt = 显式 dt / 缺省 interval /
    游程均摊 span/run_len"""
    assert v3_bucket_width_s(0.25) == 1  # 亚秒 -> 下限 1
    assert v3_bucket_width_s(30.0) == 30
    assert v3_bucket_width_s(30.5) == 31  # 显式 dt 30500ms -> ceil
    assert v3_bucket_width_s(86.4) == 87
    b = V3Block(
        start_epoch=1000,
        interval_s=30,
        records=(
            V3Sample(1, 1, 1, 1), V3Sample(2, 2, 2, 2, dt_ms=30500), V3ZeroRun(3, 5, 6, dt_ms=90000), V3NullRun(2)
        ),
    )
    slots = v3_block_slots(b)
    # r0 缺省 30 / r1 显式 31 / z 均摊 90/3=30 x3 / n 缺省 30 x2(块首 r 槽宽 = 标称 interval)
    assert [v3_bucket_width_s(s.dt_s) for s in slots] == [30, 31, 30, 30, 30, 30, 30]


def test_v3_paths_dates_and_window(tmp_path):
    """按天目录与路径解析(§06.2): 系列 key <-> 目录双向 / 日期 <-> 文件名 / agg.dat
    路径 / 窗口 -> 涉及日期集合(跨月/跨年) / day_epoch/month_epoch 本地 00:00 /
    非法键与倒置窗口 fail-fast"""
    data_dir = str(tmp_path)
    root = os.path.join(data_dir, TRAFFIC_V3_DIR_NAME)
    assert v3_root_dir(data_dir) == root
    assert v3_series_dir(data_dir, "global") == os.path.join(root, "global")
    assert v3_series_dir(data_dir, "torrent:ABC123") == os.path.join(root, "torrents", "ABC123")
    assert v3_day_file_path(data_dir, "global", "2026-10-04") == os.path.join(root, "global", "2026-10-04.dat")
    assert v3_agg_file_path(data_dir, "torrent:ABC123") == os.path.join(root, "torrents", "ABC123", "agg.dat")
    # 反向: 相对目录 -> 系列键(两种分隔符都认); 非系列目录 None
    assert v3_rel_dir_to_key("global") == "global"
    assert v3_rel_dir_to_key("torrents/ABC123") == "torrent:ABC123"
    assert v3_rel_dir_to_key("torrents\\ABC123") == "torrent:ABC123"
    assert v3_rel_dir_to_key("torrents") is None and v3_rel_dir_to_key("other") is None
    assert v3_rel_dir_to_key("torrents/../evil") is None
    # 文件名 <-> 日期: 形状与非真实日期都拒收
    assert v3_day_file_date("2026-10-04.dat") == "2026-10-04"
    assert v3_day_file_date("agg.dat") is None
    assert v3_day_file_date("2026-10-4.dat") is None and v3_day_file_date("2026-13-01.dat") is None
    assert v3_day_file_date("x.corrupt") is None
    # 本地 00:00 口径(day_epoch/month_epoch)
    day0 = int(datetime(2026, 10, 4).timestamp())
    assert v3_date_str_epoch("2026-10-04") == day0
    assert v3_epoch_date_str(day0) == "2026-10-04"
    assert v3_day_epoch(day0 + 3600) == day0
    assert v3_month_epoch(day0) == int(datetime(2026, 10, 1).timestamp())
    # 窗口 -> 日期集合: 跨日/跨年含两端所在日; 单日窗口
    assert v3_window_dates(day0 - 3600, day0 + 3600) == frozenset({"2026-10-03", "2026-10-04"})
    ny = int(datetime(2027, 1, 1).timestamp())
    assert v3_window_dates(ny - 3600, ny + 3600) == frozenset({"2026-12-31", "2027-01-01"})
    assert v3_window_dates(day0, day0) == frozenset({"2026-10-04"})
    # 跨月窗口(月末日 23:00 -> 次月 1 日 01:00)
    month_end = int(datetime(2026, 9, 30).timestamp())
    assert v3_window_dates(month_end - 3600,
                           month_end + 25 * 3600) == frozenset({"2026-09-29", "2026-09-30", "2026-10-01"})
    # fail-fast: 非法键 / 非法日期串 / 倒置窗口
    with pytest.raises(ValueError):
        v3_series_dir(data_dir, "torrent:../evil")
    with pytest.raises(ValueError):
        v3_series_dir(data_dir, "weird")
    with pytest.raises(ValueError):
        v3_day_file_path(data_dir, "global", "2026-13-01")
    with pytest.raises(ValueError):
        v3_date_str_epoch("2026-10-4")
    with pytest.raises(ValueError):
        v3_window_dates(day0, day0 - 1)


def test_v3_agg_roundtrip_and_legacy_8col():
    """agg.dat roundtrip(§02.2): hour/day/month 9 列混存解析按 kind 分列升序 / 同 epoch
    重复取最后一行 / 8 列旧行兜底 cov_s=3600 / format_agg_row 逐列往返 / 非法 kind fail-fast"""
    text = _v3_day_text(
        [
            HEADER_LINE_V3,
            "key,torrent:ABC",
            "hour,1000,10,20,5,8,100,200,3600",
            "hour,1000,11,21,6,9,110,210,3500",  # 同 epoch 重复 -> 取最后一行(:273 口径)
            "hour,4600,12,22,7,10,120,220,1800",
            "day,5000,10,20,5,8,130,230,5400",
            "month,100,1,2,3,4,140,240,86400",
            "hour,5000,9,19,4,7,90,190",  # 8 字段旧行 -> cov_s 兜底 3600(防御性)
            "garbage,line",  # 坏行计数
        ]
    )
    parsed = parse_v3_agg_text(text)
    assert parsed.key == "torrent:ABC" and parsed.bad_lines == 1 and parsed.data_lines == 8
    assert parsed.hours == (
        AggRow("hour", 1000, 11, 21, 6, 9, 110, 210, 3500),  # 同 epoch 取最后一行
        AggRow("hour", 4600, 12, 22, 7, 10, 120, 220, 1800),
        AggRow("hour", 5000, 9, 19, 4, 7, 90, 190, 3600),  # 8 字段旧行兜底
    )
    assert parsed.days == (AggRow("day", 5000, 10, 20, 5, 8, 130, 230, 5400), )
    assert parsed.months == (AggRow("month", 100, 1, 2, 3, 4, 140, 240, 86400), )
    # 逐列往返: format -> parse 还原同值
    row = parsed.days[0]
    assert format_agg_row(row) == "day,5000,10,20,5,8,130,230,5400"
    reparsed = parse_v3_agg_text(_v3_day_text([HEADER_LINE_V3, format_agg_row(row)]))
    assert reparsed.days == (row, ) and reparsed.bad_lines == 0
    # 非法 kind fail-fast; 9 字段(kind + 8)整行恰合, 10 字段计坏
    with pytest.raises(ValueError):
        format_agg_row(AggRow("week", 1, 1, 1, 1, 1, 1, 1, 1))
    bad = parse_v3_agg_text(_v3_day_text([HEADER_LINE_V3, "hour,1,1,1,1,1,1,1,1,1"]))
    assert bad.bad_lines == 1 and bad.hours == ()


def test_v3_hour_agg_dt_weighted_degenerate_to_v2():
    """dt 加权 hour 聚合(§04.1): avg = round(Σ(rate x dt)/cov) / cov 上界 3600 /
    totals 级末快照 / dt_i 恒等 interval_s 时严格退化为等间隔均值公式 round(Σrate/n)
    (对照断言钉住) / 空样本与零覆盖 fail-fast"""
    h0 = 36_000
    # 退化形态: dt_i 恒 = 30s, 120 样本恰满 1h -> 与等间隔均值公式(v2 纯活跃桶口径)逐列一致
    rates = [100 + i for i in range(120)]
    up_rates = [50 + i for i in range(120)]
    samples = tuple(
        V3HourSample(dl_rate=dl, up_rate=up, dl_total=1000 + i, up_total=2000 + i, dt_s=30.0)
        for i, (dl, up) in enumerate(zip(rates, up_rates))
    )
    agg = v3_hour_agg(h0, samples)
    assert agg.dl_avg == int(round(sum(rates) / 120))  # 退化: = round(Σ(rate x dt) / (n x dt)) = 等间隔均值
    assert agg.cov_s == 3600 and agg.dl_max == rates[-1] and agg.up_max == up_rates[-1]
    assert (agg.dl_total, agg.up_total) == (1000 + 119, 2000 + 119)  # totals = 级末快照
    # dt 加权(非均匀): 2 样本各 1800s
    half = v3_hour_agg(h0, (V3HourSample(100, 50, 1, 2, 1800.0), V3HourSample(300, 150, 3, 4, 1800.0)))
    assert (half.dl_avg, half.up_avg) == (200, 100) and half.cov_s == 3600
    # cov 上界: Σdt > 3600 裁到 3600
    clamped = v3_hour_agg(h0, (V3HourSample(100, 50, 1, 2, 2000.0), V3HourSample(300, 150, 3, 4, 2000.0)))
    assert clamped.cov_s == 3600 and clamped.dl_avg == int(round((100 * 2000 + 300 * 2000) / 3600))
    # fail-fast: 空样本 / 零覆盖
    with pytest.raises(ValueError):
        v3_hour_agg(h0, ())
    with pytest.raises(ValueError):
        v3_hour_agg(h0, (V3HourSample(1, 1, 1, 1, 0.0), ))


def test_v3_rollup_strict_level_by_level():
    """逐级派生(§04.1): day 从 hour 行 / month 从 day 行 —— avg 按 cov 加权 /
    max 取下级最大 / totals 级末快照(epoch 最大下级行) / cov = Σ下级.cov;
    kind 限 day/month(严格逐级, day 不从 raw 直聚)与空下级/零覆盖 fail-fast"""
    h1 = AggRow("hour", 100, 100, 150, 50, 80, 1000, 2000, 3600)
    h2 = AggRow("hour", 4600, 200, 250, 100, 160, 1100, 2100, 1800)
    day = v3_rollup_agg("day", 0, (h1, h2))
    # avg = (100x3600 + 200x1800)/5400 = 133.33 -> 133; up = (50x3600 + 100x1800)/5400 = 66.67 -> 67
    assert day == AggRow("day", 0, 133, 250, 67, 160, 1100, 2100, 5400)
    d2 = AggRow("day", 86_400, 0, 0, 0, 0, 1200, 2200, 7200)
    month = v3_rollup_agg("month", 100, (day, d2))
    # avg = (133x5400 + 0x7200)/12600 = 57; up = (67x5400)/12600 = 28.7 -> 29; totals = 级末(d2)
    assert month == AggRow("month", 100, 57, 250, 29, 160, 1200, 2200, 12_600)
    # fail-fast: hour 不可逐级派生 / 空下级 / 零覆盖
    with pytest.raises(ValueError):
        v3_rollup_agg("hour", 1, (day, ))
    with pytest.raises(ValueError):
        v3_rollup_agg("day", 1, ())
    with pytest.raises(ValueError):
        v3_rollup_agg("day", 1, (AggRow("hour", 1, 1, 1, 1, 1, 1, 1, 0), ))


def test_v3_format_fail_fast_and_torn_tail():
    """写侧序列化纪律: dt_ms 非法(0/负/超上界/bool)与 interval_s 非法 fail-fast;
    解析侧撕裂尾半行豁免口径(完整末行无换行不算 torn, 残缺末行记 torn_tail 且坏行计数)"""
    assert format_v3_r_row(V3Sample(1, 2, 3, 4, dt_ms=DT_MS_MAX)) == f"r,1,2,3,4,{DT_MS_MAX}"  # 上界合法
    assert format_v3_n_row(V3NullRun(2)) == "n,2" and format_v3_n_row(V3NullRun(2, dt_ms=5000)) == "n,2,5000"
    assert format_v3_z_row(V3ZeroRun(2, 3, 4)) == "z,2,3,4"
    for bad_dt in (0, -1, DT_MS_MAX + 1, True, 1.5, "3"):
        with pytest.raises(ValueError):
            format_v3_r_row(V3Sample(1, 1, 1, 1, dt_ms=bad_dt))
        with pytest.raises(ValueError):
            format_v3_z_row(V3ZeroRun(2, 1, 1, dt_ms=bad_dt))
    for bad_iv in (0, -30, 30.5, True):
        with pytest.raises(ValueError):
            format_v3_b_row(1000, bad_iv)
    head = [HEADER_LINE_V3, "key,global", "B,1000,30", "r,1,1,1,1"]
    # 完整末行无换行: 正常收数据, 不算 torn_tail(缺的只是行尾换行, 追加侧先补)
    ok = parse_v3_day_text("\n".join(head))
    assert ok.bad_lines == 0 and not ok.torn_tail and len(ok.blocks[0].records) == 1
    # 残缺末行: 记 torn_tail(豁免损坏占比)且计坏行; 前面好行照常收
    torn = parse_v3_day_text(_v3_day_text(head + ["r,1,1"])[:-1])  # 去掉末行换行 -> 残缺尾段
    assert torn.torn_tail is True and torn.bad_lines == 1 and len(torn.blocks[0].records) == 1


# ---------- v3 写侧存储(S2a, TrafficV3Store) ----------


def test_v3_store_append_records_day_file_shape(tmp_path):
    """TrafficV3Store.append_records: 新文件建头行(v3) + key 行, header 随批写 B 行,
    r/z/n 记录逐行落盘且 parse_v3_day_text roundtrip 还原; records+header 全空零操作不建文件"""
    st = TrafficV3Store(str(tmp_path))
    date = v3_epoch_date_str(H1)
    st.append_records("global", date, (H1, 30), (V3Sample(1, 2, 3, 4), V3ZeroRun(2, 5, 6), V3NullRun(3)))
    text = _read_text(st.series_day_path("global", date))
    lines = text.splitlines()
    assert lines[0] == HEADER_LINE_V3 and lines[1] == "key,global" and lines[2] == f"B,{H1},30"
    assert lines[3:] == ["r,1,2,3,4", "z,2,5,6", "n,3"]
    parsed = parse_v3_day_text(text)
    assert parsed.key == "global" and len(parsed.blocks) == 1 and len(parsed.blocks[0].records) == 3
    # 全空调用: 零操作(不建文件不建目录, 惰性创建纪律)
    st.append_records("torrent:X", date, None, ())
    assert not (tmp_path / TRAFFIC_V3_DIR_NAME / "torrents").exists()


def test_v3_store_header_once_and_torn_tail_repair(tmp_path):
    """跨 flush 同块 header 只传一次(不重复 B 行); 崩溃残留半行(完整合法行缺换行)先补
    换行照常收数据 —— kill 丢失不放大(每 flush 查补一次)"""
    st = TrafficV3Store(str(tmp_path))
    date = v3_epoch_date_str(H1)
    path = st.series_day_path("global", date)
    st.append_records("global", date, (H1, 30), (V3Sample(1, 1, 1, 1), ))
    st.append_records("global", date, None, (V3Sample(2, 2, 2, 2), ))  # 同块续写: header=None
    parsed = parse_v3_day_text(_read_text(path))
    assert len(parsed.blocks) == 1 and len(parsed.blocks[0].records) == 2  # 单 B 行单块
    with open(path, "a", encoding="utf-8", newline="") as f:
        f.write("r,9,9,9,9")  # 崩溃残留: 完整行但无换行
    st.append_records("global", date, None, (V3Sample(3, 3, 3, 3), ))
    parsed = parse_v3_day_text(_read_text(path))
    # 残行补 \n 后成为完整合法行照常收(2 + 残行 + 1 = 4), 零坏行零 torn
    assert len(parsed.blocks) == 1 and len(parsed.blocks[0].records) == 4
    assert parsed.bad_lines == 0 and not parsed.torn_tail


def test_v3_store_series_has_data_gate(tmp_path):
    """series_has_data(v3 数据门, §3.2): 目录缺失/空目录 -> False; 有天文件或 agg.dat
    (同为 .dat 后缀) -> True; 非法系列键 fail-fast"""
    st = TrafficV3Store(str(tmp_path))
    assert st.series_has_data("torrent:ABC") is False  # 目录缺失
    os.makedirs(v3_series_dir(str(tmp_path), "torrent:ABC"))
    assert st.series_has_data("torrent:ABC") is False  # 目录空
    _write_dat(
        v3_day_file_path(str(tmp_path), "torrent:ABC", v3_epoch_date_str(H1)), [HEADER_LINE_V3, "key,torrent:ABC"]
    )
    assert st.series_has_data("torrent:ABC") is True  # 有天文件
    os.makedirs(v3_series_dir(str(tmp_path), "torrent:DEF"))
    (tmp_path / TRAFFIC_V3_DIR_NAME / "torrents" / "DEF" / "agg.dat").write_text("", encoding="utf-8")
    assert st.series_has_data("torrent:DEF") is True  # 仅 agg.dat 亦计入(.dat 后缀)
    with pytest.raises(ValueError):
        st.series_has_data("torrent:bad/key")  # 路径分隔符不进文件名


# ---------- v3 S2b 存储层: agg 追加/读取/裁剪/淘汰(plan 26-10-04-1957 §04) ----------

_S2B_H0 = (1_760_000_000 // HOUR) * HOUR  # hour 对齐的现代 epoch(Windows 不支持负 epoch, 勿用 1970 附近)


def _agg_row(
    kind: str, epoch: int, dl_avg=10, dl_max=20, up_avg=5, up_max=8, dl_total=100, up_total=200, cov=3600
) -> AggRow:
    """聚合行构造辅助(默认值可覆盖)"""
    return AggRow(kind, epoch, dl_avg, dl_max, up_avg, up_max, dl_total, up_total, cov)


def test_v3_store_agg_append_read_and_torn_tail(tmp_path):
    """append_agg_rows/read_agg(§04.2/§04.3): 新文件建头行(v3)+key 行, hour/day/month
    9 列混存追加 + roundtrip; 空行批零操作(不建文件); 崩溃残留无换行尾先补换行照常收;
    缺失/空文件 = 空解析结果(key=None)"""
    st = TrafficV3Store(str(tmp_path))
    key = "torrent:ABC"
    rows = (
        _agg_row("hour", _S2B_H0), _agg_row("day", v3_day_epoch(_S2B_H0)), _agg_row("month", v3_month_epoch(_S2B_H0))
    )
    st.append_agg_rows(key, rows)  # 新文件: 惰性建目录 + 头行 + key 行
    lines = _read_text(v3_agg_file_path(str(tmp_path), key)).splitlines()
    assert lines[0] == HEADER_LINE_V3 and lines[1] == f"key,{key}"
    assert lines[2:] == [format_agg_row(r) for r in rows]
    parsed = st.read_agg(key)
    assert parsed.key == key
    assert parsed.hours == (rows[0], ) and parsed.days == (rows[1], ) and parsed.months == (rows[2], )
    # 空行批: 零操作不建文件(惰性纪律)
    st.append_agg_rows("torrent:EMPTY", ())
    assert not os.path.exists(v3_agg_file_path(str(tmp_path), "torrent:EMPTY"))
    # 崩溃残留: 末行无换行 -> 下批追加先补换行, 两批数据都完整可读
    with open(v3_agg_file_path(str(tmp_path), key), "a", encoding="utf-8", newline="") as f:
        f.write(format_agg_row(_agg_row("hour", _S2B_H0 + HOUR, dl_avg=99)))
    st.append_agg_rows(key, (_agg_row("hour", _S2B_H0 + 2 * HOUR, dl_avg=77), ))
    parsed = st.read_agg(key)
    assert [h.dl_avg for h in parsed.hours] == [10, 99, 77]  # 残行补换行后照常收
    assert parsed.bad_lines == 0 and not parsed.torn_tail
    # 缺失/空文件 = 空解析结果(key=None, 全空)
    empty = st.read_agg("torrent:NOPE")
    assert empty.key is None and empty.hours == () and empty.data_lines == 0
    os.makedirs(v3_series_dir(str(tmp_path), "torrent:BLANK"))
    (tmp_path / TRAFFIC_V3_DIR_NAME / "torrents" / "BLANK" / "agg.dat").write_text("", encoding="utf-8")
    assert st.read_agg("torrent:BLANK").key is None


def test_v3_store_series_keys_and_day_dates(tmp_path):
    """series_keys/series_day_dates/read_day(§04.3 恢复入口): global + torrents/<h> 全列出
    (非 infohash 目录跳过); 天文件日期按补算窗口过滤(min_epoch 边界含, 升序), agg.dat 等
    非日期杂物跳过; 目录缺失 = 空表; 非法日期串 fail-fast(路径层校验)"""
    st = TrafficV3Store(str(tmp_path))
    assert st.series_keys() == []  # 根目录缺失
    d_old, d_new = "2026-01-01", "2026-03-15"
    for key in ("global", "torrent:ABC"):
        for d in (d_old, d_new):
            _write_dat(st.series_day_path(key, d), [HEADER_LINE_V3, f"key,{key}"])
        _write_dat(v3_agg_file_path(str(tmp_path), key), [HEADER_LINE_V3, f"key,{key}"])
    os.makedirs(os.path.join(v3_root_dir(str(tmp_path)), "torrents", "NOT!HASH"))  # 非 infohash 目录: 跳过
    assert st.series_keys() == ["global", "torrent:ABC"]
    min_epoch = v3_date_str_epoch("2026-03-01")
    assert st.series_day_dates("torrent:ABC", min_epoch) == (d_new, )  # 窗外天文件不进补算
    assert st.series_day_dates("torrent:ABC", v3_date_str_epoch(d_old)) == (d_old, d_new)  # 边界含(升序)
    assert st.series_day_dates("torrent:NOPE", 0) == ()  # 目录缺失
    assert st.read_day("torrent:ABC", d_new) is not None and st.read_day("torrent:ABC", "2026-03-16") is None
    with pytest.raises(ValueError):
        st.read_day("torrent:ABC", "2026-99-01")  # 非法日期串: 路径层 fail-fast


def test_v3_store_trim_agg_hours(tmp_path):
    """trim_agg_hours(§04.5, v3 唯一 tmp+fsync+os.replace 原子重写点): epoch >=
    now-rollup_window 的 hour 行保留(边界含); day/month 行全保留(永久, D7 不裁);
    无到龄行零写(same_content, 文件字节不变); 返回重写后最老 hour epoch(空 = None)"""
    st = TrafficV3Store(str(tmp_path))
    key = "global"
    window = 30 * 86400.0
    now = 3000 * 86400.0
    aged, boundary, fresh = now - window - 2 * HOUR, now - window, now - HOUR
    st.append_agg_rows(
        key, (
            _agg_row("hour", aged, dl_avg=1),
            _agg_row("hour", boundary, dl_avg=2),
            _agg_row("hour", fresh, dl_avg=3),
            _agg_row("day", v3_day_epoch(aged)),
            _agg_row("month", v3_month_epoch(aged)),
        )
    )
    path = v3_agg_file_path(str(tmp_path), key)
    assert st.trim_agg_hours(key, now, window) == boundary  # 到龄行裁掉, 返回新最老
    parsed = st.read_agg(key)
    assert [h.epoch for h in parsed.hours] == [boundary, fresh]
    # day/month 行永久: 不按龄裁剪
    assert parsed.days[0].epoch == v3_day_epoch(aged) and parsed.months[0].epoch == v3_month_epoch(aged)
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


def test_v3_store_trim_agg_hours_replace_locked(tmp_path, monkeypatch):
    """裁剪重写被占用(Windows 读侧竞态, PermissionError): 退避重试 xREWRITE_RETRIES 后
    放弃本轮 —— 原文件完好返回原最老 epoch(下轮重试); 重试窗口内恢复则正常重写"""
    st = TrafficV3Store(str(tmp_path))
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

    monkeypatch.setattr("auto_qb.core.traffic_store.time.sleep", lambda s: None)
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


def test_v3_store_evict_expired_series(tmp_path, monkeypatch):
    """evict_expired_series(§04.5 新口径): 系列最新天文件日期距 now 超过 rollup_window
    -> 整目录删除(天文件 + agg.dat, 龄期由文件名日期直接算); 边界(恰 window)不动;
    无天文件的目录保守跳过; 全局系列结构性豁免; 删除失败(读侧竞态)保留下轮重试且
    不进返回表"""
    st = TrafficV3Store(str(tmp_path))
    window = 30 * 86400.0
    edge_midnight = v3_date_str_epoch("2026-03-15")
    now = edge_midnight + window  # now 恰在窗口边界上: 2026-03-15 的 00:00 距 now 恰 = window(边界含, 保留)
    old_d = v3_epoch_date_str(now - 40 * 86400)
    new_d = "2026-03-16"
    # OLD: 超龄(天文件 + agg.dat 同删); EDGE: 恰压线保留; NEW: 新鲜; AGGONLY: 无天文件保守跳过
    for key, d in (("torrent:OLD", old_d), ("torrent:EDGE", "2026-03-15"), ("torrent:NEW", new_d)):
        _write_dat(st.series_day_path(key, d), [HEADER_LINE_V3, f"key,{key}"])
    _write_dat(v3_agg_file_path(str(tmp_path), "torrent:OLD"), [HEADER_LINE_V3, "key,torrent:OLD"])
    os.makedirs(v3_series_dir(str(tmp_path), "torrent:AGGONLY"))
    _write_dat(v3_agg_file_path(str(tmp_path), "torrent:AGGONLY"), [HEADER_LINE_V3, "key,torrent:AGGONLY"])
    _write_dat(st.series_day_path("global", old_d), [HEADER_LINE_V3, "key,global"])  # 全局豁免(结构性)
    evicted = st.evict_expired_series(now, window)
    assert evicted == ["torrent:OLD"]
    assert not os.path.exists(v3_series_dir(str(tmp_path), "torrent:OLD"))  # 整目录(天文件 + agg.dat)
    for key in ("torrent:EDGE", "torrent:NEW", "torrent:AGGONLY"):
        assert os.path.exists(v3_series_dir(str(tmp_path), key))
    assert os.path.exists(v3_series_dir(str(tmp_path), "global"))
    # 删除失败重试: 重建 OLD(首轮已被删) -> rmtree 抛错 -> 目录保留且不进返回表 -> 下轮重试成功
    _write_dat(st.series_day_path("torrent:OLD", old_d), [HEADER_LINE_V3, "key,torrent:OLD"])
    _write_dat(v3_agg_file_path(str(tmp_path), "torrent:OLD"), [HEADER_LINE_V3, "key,torrent:OLD"])

    def _boom(path):
        raise OSError(16, "locked")

    monkeypatch.setattr("auto_qb.core.traffic_store.shutil.rmtree", _boom)
    assert st.evict_expired_series(now, window) == []  # 删除失败: 不进返回表
    assert os.path.exists(v3_series_dir(str(tmp_path), "torrent:OLD"))  # 目录保留下轮重试
    monkeypatch.undo()
    assert st.evict_expired_series(now, window) == ["torrent:OLD"]  # 下轮重试成功


# ---------- v3 S3a 读侧: 按天解析缓存(plan 26-10-04-1957 §05.2, V3DayCache) ----------


def _write_v3_day(data_dir, key, date, text):
    """测试助手: 直接落一个天文件(不经写侧批量纪律)"""
    path = v3_day_file_path(data_dir, key, date)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return path


def test_v3_day_cache_hit_and_invalidate(tmp_path, monkeypatch):
    """解析缓存命中与失效两向(验收): 未变命中(不重读不重解析, 同一解析对象) /
    追加变 size 失效 / 裁剪重写变小失效(mtime+size 键控, 两向都变); 缺失文件缓存 None
    (文件此后出现则 stat 键变化自然失效)"""
    data_dir = str(tmp_path)
    d = "2026-10-04"
    text = format_v3_day_text("global", (V3Block(1000, 30, (V3Sample(1, 1, 10, 20), )), ))
    _write_v3_day(data_dir, "global", d, text)
    calls = []
    real_parse = traffic_store_module.parse_v3_day_text

    def counting_parse(t):
        calls.append(1)
        return real_parse(t)

    monkeypatch.setattr(traffic_store_module, "parse_v3_day_text", counting_parse)
    cache = V3DayCache(data_dir)
    p1 = cache.read_day("global", d)
    assert p1 is not None and p1.key == "global" and calls == [1]
    assert cache.read_day("global", d) is p1  # 未变命中: 同一解析对象, 零重解析
    assert calls == [1]
    # 追加(size 变大) -> 失效重解析
    bigger = format_v3_day_text("global", (V3Block(1000, 30, (V3Sample(1, 1, 10, 20), V3Sample(2, 2, 20, 40))), ))
    _write_v3_day(data_dir, "global", d, bigger)
    p2 = cache.read_day("global", d)
    assert calls == [1, 1] and len(p2.blocks[0].records) == 2
    # 裁剪重写(size 严格变小) -> 失效重解析
    _write_v3_day(data_dir, "global", d, text)
    p3 = cache.read_day("global", d)
    assert calls == [1, 1, 1] and len(p3.blocks[0].records) == 1
    assert cache.read_day("global", d) is p3  # 未变再命中
    assert calls == [1, 1, 1]
    # 缺失文件: None 且缓存(不再触发解析); 文件出现后 stat 键变化自然失效
    assert cache.read_day("global", "2026-10-03") is None
    assert cache.read_day("global", "2026-10-03") is None
    assert calls == [1, 1, 1]
    _write_v3_day(data_dir, "global", "2026-10-03", text)
    assert cache.read_day("global", "2026-10-03") is not None and calls == [1, 1, 1, 1]


def test_v3_day_cache_window_reads_only_involved_files(tmp_path, monkeypatch):
    """按天加载(验收: 24h 窗只开 2 个日期文件): read_window 按 v3_window_dates 只读涉及
    日期的天文件, 目录内其余天文件零 open; 返回按日期升序"""
    data_dir = str(tmp_path)
    block = V3Block(1000, 30, (V3Sample(1, 1, 10, 20), ))
    for date in ("2026-10-03", "2026-10-04", "2026-10-05"):
        _write_v3_day(data_dir, "global", date, format_v3_day_text("global", (block, )))
    opened = []
    real_open = builtins.open

    def counting_open(file, *a, **k):
        opened.append(os.fspath(file))
        return real_open(file, *a, **k)

    monkeypatch.setattr(builtins, "open", counting_open)
    cache = V3DayCache(data_dir)
    t0 = datetime(2026, 10, 4, 12, 0, 0).timestamp()
    t1 = datetime(2026, 10, 5, 12, 0, 0).timestamp()  # 24h 窗: 涉及 10-04 与 10-05 两个日期
    result = cache.read_window("global", t0, t1)
    dat_opens = [p for p in opened if p.endswith(".dat")]
    assert len(dat_opens) == 2  # 只开 2 个涉及文件(10-03 未动)
    assert [d for d, _ in result] == ["2026-10-04", "2026-10-05"]
    assert all(parsed is not None and parsed.key == "global" for _, parsed in result)
    # 窗口再查(缓存命中): 零新 open
    opened.clear()
    cache.read_window("global", t0, t1)
    assert [p for p in opened if p.endswith(".dat")] == []


def test_v3_day_cache_budget_lru(tmp_path, monkeypatch):
    """字节预算 LRU: 驻留条目文本总量 <= budget, 超出最久未用先逐出(至少保留最新一条);
    命中把条目移到队尾(刷新新近度)"""
    data_dir = str(tmp_path)
    block = V3Block(1000, 30, (V3Sample(1, 1, 10, 20), ))
    for date in ("2026-10-01", "2026-10-02", "2026-10-03"):
        _write_v3_day(data_dir, "global", date, format_v3_day_text("global", (block, )))
    calls = []
    real_parse = traffic_store_module.parse_v3_day_text

    def counting_parse(t):
        calls.append(1)
        return real_parse(t)

    monkeypatch.setattr(traffic_store_module, "parse_v3_day_text", counting_parse)
    cache = V3DayCache(data_dir, budget=1)  # 预算 1B: 每条都超, 恒只保最新读入的一条
    cache.read_day("global", "2026-10-01")
    cache.read_day("global", "2026-10-02")  # 10-01 被挤出
    cache.read_day("global", "2026-10-03")  # 10-02 被挤出
    assert calls == [1, 1, 1]
    cache.read_day("global", "2026-10-01")  # 10-01 已被逐出: 重解析(10-03 被挤出)
    assert calls == [1, 1, 1, 1]
    cache.read_day("global", "2026-10-01")  # 最新读入的条目保留: 命中
    assert calls == [1, 1, 1, 1]


def test_v3_agg_cache_hit_and_invalidate(tmp_path, monkeypatch):
    """agg.dat 解析缓存(S3b §05.2/§05.3, V3DayCache.read_agg): mtime_ns+size 键控与天文件
    同款纪律 —— 未变命中(同一解析对象) / 追加变 size 失效 / 裁剪重写变小失效; 缺失文件
    缓存空解析哨兵(文件此后出现自然失效); OSError(打开/读取失败)上抛不落缓存"""
    data_dir = str(tmp_path)
    rows = (AggRow("hour", 1000, 11, 21, 6, 9, 110, 210, 3500), AggRow("day", 0, 1, 2, 3, 4, 5, 6, 86400))
    cache = V3DayCache(data_dir)
    # 缺失文件: 空解析结果且缓存(哨兵); 文件出现后 stat 键变化自然失效
    empty = cache.read_agg("global")
    assert empty.key is None and empty.hours == () and empty.days == ()
    assert cache.read_agg("global") is empty
    store = TrafficV3Store(data_dir)
    store.append_agg_rows("global", rows)
    parsed = cache.read_agg("global")
    assert parsed.key == "global" and len(parsed.hours) == 1 and len(parsed.days) == 1
    assert cache.read_agg("global") is parsed  # 未变命中(同一解析对象)
    # 追加(hour 行新增): size 变 -> 失效重读
    store.append_agg_rows("global", (AggRow("hour", 4600, 12, 22, 7, 10, 120, 220, 1800), ))
    parsed2 = cache.read_agg("global")
    assert parsed2 is not parsed and len(parsed2.hours) == 2
    # 裁剪重写(hour 行全部到龄): size 严格变小 -> 失效重读(hour 清空, day 行永久保留)
    store.trim_agg_hours("global", now=100000, rollup_window=3600)
    parsed3 = cache.read_agg("global")
    assert parsed3 is not parsed2 and parsed3.hours == () and len(parsed3.days) == 1
    # OSError 上抛不落缓存: 先追加使 stat 键变化(失效), 再令打开失败 —— 上抛且不落缓存,
    # 恢复后重读生效(不以半态冒充好数据)
    store.append_agg_rows("global", (AggRow("hour", 8200, 13, 23, 8, 11, 130, 230, 900), ))
    agg_path = v3_agg_file_path(data_dir, "global")
    real_open = builtins.open

    def boom(file, *a, **k):
        if os.fspath(file) == agg_path:
            raise OSError("simulated read race")
        return real_open(file, *a, **k)

    monkeypatch.setattr(builtins, "open", boom)
    with pytest.raises(OSError):
        cache.read_agg("global")
    monkeypatch.undo()
    parsed4 = cache.read_agg("global")
    assert parsed4.key == "global" and len(parsed4.hours) == 1  # 恢复后重读生效(失败未落缓存)


# ---------- S5 实测: 体量对比(plan 26-10-04-1957 §09.1) ----------


def test_v3_row_width_vs_legacy_layout_bytes():
    """体量对比: 同一构造采样序列分别按 v2 行型布局与 v3 行型序列化, 实测字节数对照 ——
    活跃 r 行 40-52B(v2: raw 前缀 + 时间戳列) -> 30-40B(v3: r 前缀无时间戳列, 时刻由
    dt 链推算); 空闲段 v2 零值行(1 行/采样) vs v3 z 游程(1 行/封口节奏 600s)压缩 >10x。
    v2 行型布局此处仅作字节数对照基线(测量用途, 其解析/写侧已随 S5 退役)。"""
    dl, up, dlt, upt = 98_765, 45_678, 9_876_543_210, 1_234_567_890  # 真实量级: 速率 ~10^5, totals ~10^10
    # 活跃段: 2880 行 30s 采样(一天); v2 行含 10 位 epoch 时间戳, v3 r 行无时间列
    v2_active = [f"raw,{1_800_000_000 + i * 30},{dl},{up},{dlt},{upt}" for i in range(2880)]
    v3_active = [f"r,{dl},{up},{dlt},{upt}" for _ in range(2880)]
    v2_w = len(v2_active[0].encode()) + 1
    v3_w = len(v3_active[0].encode()) + 1
    assert 40 <= v2_w <= 52  # 计划 §09.1 规格带: v2 行宽 40-52B
    assert 30 <= v3_w <= 40  # v3 行宽 30-40B
    assert v3_w < v2_w
    v2_bytes = sum(len(r.encode()) + 1 for r in v2_active)
    v3_bytes = sum(len(r.encode()) + 1 for r in v3_active)
    assert v2_bytes - v3_bytes >= 2880 * 10  # 每行至少省 10B(时间戳列 10-12B)
    # 空闲段: 一天全空闲(600s 游程节奏); v3 再加 B 行块头与头行(单文件一次性成本)
    v2_idle = [f"raw,{1_800_000_000 + i * 30},0,0,0,0" for i in range(2880)]
    v3_idle = [f"z,300,{dlt},{upt}" for _ in range(144)]  # 2880 槽 / 游程 300 槽
    v2_idle_bytes = sum(len(r.encode()) + 1 for r in v2_idle)
    v3_idle_bytes = sum(len(r.encode()) + 1 for r in v3_idle)
    assert v2_idle_bytes / v3_idle_bytes > 10  # 空闲压缩 >10x
    # v3 行全部合法: 经解析 roundtrip 零坏行(对照基线不破坏格式契约)
    block = V3Block(
        1_800_000_000,
        30,
        tuple(V3Sample(dl, up, dlt, upt) for _ in range(2880)) + tuple(V3ZeroRun(300, dlt, upt) for _ in range(144)),
    )
    parsed = parse_v3_day_text(format_v3_day_text("global", (block, )))
    assert parsed.bad_lines == 0 and len(parsed.blocks) == 1
    assert len(parsed.blocks[0].records) == 2880 + 144


# ---------- v3 活尾快照(S6 验收追加, 2026-10-05) ----------


def _s6_mixed_records(interval: int) -> tuple:
    """S6 镜像保证用例的混排记录序列: r(标称) / r(显式 dt) / z 游程 / r / n 游程 / r"""
    base = 1_800_000_000
    return (
        V3Sample(100, 50, 1000, 500),  # 块首 r(槽位 = B.start)
        V3Sample(200, 70, 2000, 800, dt_ms=(interval + 1) * 1000),  # 显式 dt(超容差)
        V3ZeroRun(3, 2000, 800),  # 零速游程(标称 3 槽)
        V3Sample(150, 60, 2600, 1100),  # 游程后 r(链锚点 = 游程终点)
        V3NullRun(2, dt_ms=(2 * interval - 1) * 1000),  # 断连游程(显式 dt)
        V3Sample(90, 40, 3000, 1300),  # 末记录
    )


def test_v3_live_tail_slots_mirror_identity_family():
    """镜像保证族: 磁盘部分块槽 + 活尾槽 == 整块重算槽(逐槽恒等, S6 去重的正确性根基)

    三分割点: k=0(块全量未落盘 -> head_pending 整块重算)/ 0<k<N(中途 flush 后从写侧
    游标倒推)/ k=N(全部落盘, 活尾只剩开放游程 —— 单独在 open_run 用例覆盖)。
    """
    interval = 30
    recs = _s6_mixed_records(interval)
    start = 1_800_000_000
    full_block = V3Block(start, interval, recs)
    full_slots = v3_block_slots(full_block)
    # 写侧游标 = 最后一条记录的槽位锚点(游程末槽 = 游标终点, S1 定约) -> 镜像值取整块末槽
    projected = full_slots[-1].ts
    # k=0: 块全量未落盘(head_pending) -> 活尾槽 == 整块重算槽
    tail_head = LiveTail(
        block_open=True,
        head_pending=True,
        start_epoch=start,
        interval_s=interval,
        projected_ts=projected,
        records=recs,
        open_run=None,
    )
    assert v3_live_tail_slots(tail_head) == full_slots
    for k in (1, 3, 5):  # 中途 flush: 磁盘已收前 k 条, 缓冲滞留其余
        disk_slots = v3_block_slots(V3Block(start, interval, recs[:k]))
        tail = LiveTail(
            block_open=True,
            head_pending=False,
            start_epoch=start,
            interval_s=interval,
            projected_ts=projected,
            records=recs[k:],
            open_run=None,
        )
        assert disk_slots + v3_live_tail_slots(tail) == full_slots, k
    # 倒推不依赖磁盘链可见(1m 窗场景): 仅活尾自身也逐槽落在整块槽序的后缀上
    k = 3  # 前 3 条记录 = 1+1+3(r,r,z 游程) = 5 槽
    prefix_slots = sum(rec.run_len if hasattr(rec, "run_len") else 1 for rec in recs[:k])
    tail_only = v3_live_tail_slots(LiveTail(True, False, start, interval, projected, recs[k:], None))
    assert tail_only == full_slots[prefix_slots:]


def test_v3_live_tail_slots_open_run_forms():
    """开放游程封口形态: 无开放块 -> 块首形([int(run.start), last_seen] 端点含, n=1 单槽);
    有开放块 -> 非块首形((链终点, last_seen] 均摊, 末槽 = last_seen); n 游程 obs = None"""
    dlt, upt = 3000, 1300
    # 无开放块: 块首形, 120 槽端点含均摊 [100, 340]
    run_z = LiveTailRun(kind="z", start=100.4, last_seen=340.4, dl_total=dlt, up_total=upt, samples=120)
    slots = v3_live_tail_slots(LiveTail(False, False, None, 2, 0.0, (), run_z))
    assert len(slots) == 120
    assert slots[0].ts == 100.0 and slots[-1].ts == pytest.approx(340.4)
    assert all(s.obs == (0, 0, dlt, upt) and s.is_zero for s in slots)
    # n 游程同形: obs = None, is_zero = False
    run_n = LiveTailRun(kind="n", start=100.0, last_seen=160.0, dl_total=0, up_total=0, samples=4)
    slots_n = v3_live_tail_slots(LiveTail(False, False, None, 2, 0.0, (), run_n))
    assert [s.ts for s in slots_n] == [100.0, 120.0, 140.0, 160.0]
    assert all(s.obs is None and not s.is_zero for s in slots_n)
    # n=1 块首单槽: 槽位恰在 int(run.start)
    run_z1 = LiveTailRun(kind="z", start=100.4, last_seen=100.4, dl_total=dlt, up_total=upt, samples=1)
    slots_1 = v3_live_tail_slots(LiveTail(False, False, None, 2, 0.0, (), run_z1))
    assert len(slots_1) == 1 and slots_1[0].ts == 100.0
    # 有开放块(全落盘): 非块首形, 槽在 (projected_ts, last_seen] 均摊, 末槽 = last_seen
    run_open = LiveTailRun(kind="z", start=1000.0, last_seen=1010.0, dl_total=dlt, up_total=upt, samples=5)
    slots_open = v3_live_tail_slots(LiveTail(True, False, 900, 30, 1000.0, (), run_open))
    assert [s.ts for s in slots_open] == [1002.0, 1004.0, 1006.0, 1008.0, 1010.0]
    assert all(s.obs == (0, 0, dlt, upt) and s.is_zero for s in slots_open)
    # 有开放块且块全量未落盘: 游程链锚点 = 整块重算游标终值(链式接续)
    recs = _s6_mixed_records(30)
    full_slots = v3_block_slots(V3Block(1_800_000_000, 30, recs))
    chain_end = full_slots[-1].ts
    run_at_chain = LiveTailRun(
        kind="z", start=chain_end, last_seen=chain_end + 10, dl_total=dlt, up_total=upt, samples=5
    )
    tail = LiveTail(True, True, 1_800_000_000, 30, chain_end, recs, run_at_chain)
    slots_both = v3_live_tail_slots(tail)
    assert slots_both[:len(full_slots)] == full_slots
    assert [s.ts for s in slots_both[len(full_slots):]] == [chain_end + 2.0 * k for k in range(1, 6)]


def test_v3_live_tail_slots_invariants_fail_fast():
    """invariant 拦截: block_open=False 携带 records / head_pending -> ValueError;
    未知记录型 -> TypeError(发布侧单点保证, 读侧 tripwire)"""
    with pytest.raises(ValueError):
        v3_live_tail_slots(LiveTail(False, False, None, 30, 0.0, (V3Sample(1, 1, 1, 1), ), None))
    with pytest.raises(ValueError):
        v3_live_tail_slots(LiveTail(False, True, None, 30, 0.0, (), None))
    with pytest.raises(TypeError):
        v3_live_tail_slots(LiveTail(True, False, 100, 30, 100.0, ("bad", ), None))
