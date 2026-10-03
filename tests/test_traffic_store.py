"""test_traffic_store 测试计划: qB 口径流量 dat 存储层(plan 26-10-03-0946 方案C P2, §02)

## 测试计划(每个测试函数一条)
- test_series_path_layout_and_invalid_keys: 目录布局 <data_dir>/qb-traffic/{global.dat, torrents/<h>.dat}; 非法系列键 fail-fast
- test_format_v1_roundtrip_columns: 格式 v1 逐列往返(raw 六列 / hour 八列 / null 行四空列读写还原)
- test_parse_skips_bad_lines_and_counts: 坏行(垃圾/列数不符/负数/非数值)跳过并计数; 空行注释行忽略; hour 同桶取最后一行
- test_missing_header_treated_as_corrupt: 头行缺失/不符 -> 整文件判坏(损坏处置)
- test_append_flush_kill_window_at_most_one_row: 每行追加即达盘面(独立句柄可见); kill 模拟(截断尾部半行)丢 <=1 行且不触发隔离
- test_torn_tail_not_merged_on_next_append: 崩溃残留半行不与后续追加合并(补换行), 新行照常可读
- test_corrupt_ratio_over_threshold_moves_aside: 坏行占比 >5% -> 原文移 .corrupt + 按空文件对待; 下次追加重建
- test_corrupt_ratio_at_threshold_not_moved: 恰好 5% 不移交(严格大于)
- test_seal_hour_aggregates_bucket: 封口归并 avg/max + totals 取本小时末快照; null 行不参与
- test_seal_hour_null_only_bucket_no_row: 桶内全 null 行 -> 不产 hour 行(空桶 = null, §05.1)
- test_seal_hour_upsert_idempotent: 同桶重封替换旧 hour 行(无重复); 内容无变化跳过重写(零写放大)
- test_seal_cleans_torn_tail: 封口重写一并清除崩溃残留坏行(一次性自洁)
- test_prune_exact_n_rows_boundary: 窗口裁剪边界(恰好压线行保留): raw 段 ts >= now-raw_window, hour 段 epoch >= now-rollup_window
- test_rewrite_permission_error_backoff_retry: os.replace 竞态(PermissionError)退避重试后成功; 持续失败放弃且原文件完好无 tmp 残留
- test_index_written_only_at_change_points: index 仅条目变化时点写(建文件即写; 追加不写; 封口冲刷)
- test_reconcile_orphan_dat_self_heals: 孤儿 dat(index 无条目)从头行重建条目(frozen_at=None, created/updated 取 mtime)
- test_reconcile_drops_entry_without_file: index 条目无文件 -> 删条目
- test_reconcile_self_heals_from_disk_when_index_corrupt: index 坏/半写 -> 按空表自愈, 以磁盘头行为准
- test_reconcile_key_mismatch_warns_filename_wins: 头行 key 与文件名失配 -> 告警并按文件名登记(不改写文件)
- test_reconcile_never_touches_raw_hour_data: 对账前后 dat 数据字节级不变; 存储目录不存在零动作不建目录
- test_lazy_file_creation_zero_files_without_samples: 从未采样的种子零文件; global 首点(含 null 点)才建文件
- test_restart_continuity_appends_without_truncation: 重启(新 store/新模块实例)后 dat 接续追加不断史 + 首窗 null(基线不落盘, S1 语义)
- test_handler_triggers_hourly_seal_once_per_hour: 每小时首个采样触发封口扫描(上一小时桶); 同小时内不重复触发
- test_handler_dry_run_persists_nothing: dry_run 全程零文件(start 对账跳过 + handler 不落盘不封口)
- test_empty_data_dir_persists_nothing: data_dir 为空(防御, 真实配置恒非空) -> 零文件零目录(CWD 无泄漏)
- test_all_persist_writes_on_caller_thread: 全部落盘写在调用 run_due 的线程(主循环线程)内完成, 模块不建线程(黄金法则 5)
- test_seal_sweep_covers_global_and_torrents_and_counts: 封口扫描 catch-up 补封当前桶之前全部未封桶(含更早漏封桶), 覆盖 global + torrents/, 按文件数计数; 非 dat/.corrupt 不碰

线程/时钟纪律: 需要确定时刻的用例经 monkeypatch 固定 time.time / time.sleep(测试进程内单线程,
恢复由 monkeypatch 保证); 文件一律落在 tmp_path(test.* 已内置 TMPDIR, 不手工加前缀)。
"""
import json
import os
import threading

import pytest

from auto_qb.config import QbTraffic
from auto_qb.core.modules.traffic_sample_mod import GLOBAL_SERIES_KEY, TASK_NAME, TrafficSampleModule
from auto_qb.core.taskqueue import Task
from auto_qb.core.traffic_store import (
    CORRUPT_SUFFIX,
    HEADER_LINE,
    HOUR_SECONDS,
    HourRow,
    REWRITE_RETRIES,
    RawRow,
    TRAFFIC_DIR_NAME,
    TrafficDatStore,
    format_hour_row,
    format_raw_row,
    parse_dat_text,
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


def _store(tmp_path) -> TrafficDatStore:
    return TrafficDatStore(str(tmp_path))


def _write_dat(path, lines) -> None:
    """手工构造 dat 文件(行列表逐行写, \\n 行尾)"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


def _read_text(path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ---------- 路径与格式 ----------


def test_series_path_layout_and_invalid_keys(tmp_path):
    """目录布局: global 在根, 单种在 torrents/ 下; 非法键 fail-fast 不派生意外路径"""
    store = _store(tmp_path)
    assert store.series_path("global") == os.path.join(str(tmp_path), TRAFFIC_DIR_NAME, "global.dat")
    assert store.series_path("torrent:ABC123") == os.path.join(
        str(tmp_path), TRAFFIC_DIR_NAME, "torrents", "ABC123.dat"
    )
    for bad in ("", "foo", "torrent:", "torrent:../evil", "torrent:AB C", "group:x"):
        with pytest.raises(ValueError):
            store.series_path(bad)


def test_format_v1_roundtrip_columns(tmp_path):
    """格式 v1 逐列: raw 六列 / hour 八列 / null 行四空列; 读侧还原 None"""
    store = _store(tmp_path)
    store.append_point("global", 100, 1024, 2048, 1_000_000, 2_000_000)
    store.append_point("global", 130, None, None, None, None)  # null 点
    text = _read_text(store.series_path("global"))
    lines = text.splitlines()
    assert lines[0] == HEADER_LINE and lines[1] == "key,global"
    assert lines[2] == "raw,100,1024,2048,1000000,2000000"
    assert lines[3] == "raw,130,,,,"  # 四空字段
    parsed = store.read_series("global")
    assert parsed.key == "global" and parsed.bad_lines == 0
    assert parsed.raw[0] == RawRow(ts=100, dl_rate=1024, up_rate=2048, dl_total=1_000_000, up_total=2_000_000)
    assert parsed.raw[1] == RawRow(ts=130, dl_rate=None, up_rate=None, dl_total=None, up_total=None)
    assert parsed.raw[1].is_null
    # hour 行逐列往返
    row = HourRow(hour_epoch=H0, dl_avg=100, dl_max=300, up_avg=50, up_max=150, dl_total=2000, up_total=1000)
    assert format_hour_row(row) == f"hour,{H0},100,300,50,150,2000,1000"
    assert format_raw_row(7, None, None, None, None) == "raw,7,,,,"


def test_parse_skips_bad_lines_and_counts():
    """坏行跳过并计数: 垃圾/列数不符/负数/非数值; 空行与注释忽略; hour 同桶重复取最后一行"""
    text = "\n".join(
        [
            HEADER_LINE,
            "key,global",
            "raw,100,1,2,3,4",
            "garbage",  # 键名不匹配
            "raw,101,x,2,3,4",  # 非数值
            "raw,102,-1,2,3,4",  # 负数
            "raw,103,1,2",  # 列数不足
            "key,other",  # 重复 key 行记坏
            "",
            "# comment",
            f"hour,{H0},1,1,1,1,10,10",
            f"hour,{H0},2,2,2,2,20,20",  # 同桶重复: 取最后一行
            "raw,104,,,,",  # null 行
        ]
    )
    p = parse_dat_text(text)
    assert p.key == "global"
    assert [r.ts for r in p.raw] == [100, 104]
    assert p.raw[1].is_null
    assert p.hours == (HourRow(hour_epoch=H0, dl_avg=2, dl_max=2, up_avg=2, up_max=2, dl_total=20, up_total=20), )
    assert p.bad_lines == 5 and p.data_lines == 12  # 分母含 key 行(结构行)


def test_missing_header_treated_as_corrupt(tmp_path):
    """头行缺失/不符 = 文件级不匹配格式: 全部行记坏 -> 损坏处置移 .corrupt;
    read_series 按空文件对待(与文件缺失同口径: key=请求系列, 数据为空)"""
    store = _store(tmp_path)
    path = store.series_path("global")
    _write_dat(path, ["something else entirely", "raw,1,1,1,1,1"])
    parsed = store.read_series("global")
    assert parsed.key == "global" and parsed.raw == ()  # 按空文件对待(同缺文件口径)
    assert os.path.exists(path + CORRUPT_SUFFIX)
    assert not os.path.exists(path)  # 原位让位, 按空文件对待
    # 下次追加按新建重建(头行 + key 行齐全)
    store.append_point("global", 5, 1, 1, 1, 1)
    lines = _read_text(path).splitlines()
    assert lines[0] == HEADER_LINE and lines[1] == "key,global" and lines[-1] == "raw,5,1,1,1,1"


# ---------- 追加 / 崩溃窗口 ----------


def test_append_flush_kill_window_at_most_one_row(tmp_path):
    """kill 模拟: 每行追加返回即达盘面(独立句柄逐行可见 -> 进程崩溃丢 <=1 行);
    最后一行写到一半死亡(截断)只损失该行, 前续行完好, 且小文件的 1 行残留不触发隔离"""
    store = _store(tmp_path)
    path = store.series_path("global")
    for i in range(3):
        store.append_point("global", 100 + i, 10, 20, 100, 200)
        with open(path, "r", encoding="utf-8") as f:  # 独立句柄: flush 已落盘面
            assert f.read().count("raw,") == i + 1
    # 模拟 kill: 末行截断到行中(半行 "raw,102,", 无换行)
    content = _read_text(path)
    last_start = content.rfind("\n", 0, len(content) - 1) + 1  # 末行起点(末行以 \n 结尾)
    with open(path, "r+b") as f:
        f.truncate(last_start + 8)  # "raw,102," 8 字节
    parsed = store.read_series("global")
    assert [r.ts for r in parsed.raw] == [100, 101]  # 完整行无损
    assert parsed.bad_lines == 1 and parsed.torn_tail  # 仅尾部半行 = 正常崩溃残留


def test_torn_tail_not_merged_on_next_append(tmp_path):
    """崩溃残留半行(无换行)后续追加不与之合并: 补换行后新行独立可读(丢行恒 <=1)"""
    store = _store(tmp_path)
    path = store.series_path("global")
    store.append_point("global", 100, 1, 1, 1, 1)
    store.append_point("global", 101, 2, 2, 2, 2)
    with open(path, "r+b") as f:
        f.truncate(os.path.getsize(path) - 4)  # 截断末行尾部
    store.append_point("global", 102, 3, 3, 3, 3)  # 重启后接续追加
    parsed = store.read_series("global")
    assert [r.ts for r in parsed.raw] == [100, 102] and parsed.bad_lines == 1  # 半行被隔离, 新行完好


# ---------- 损坏阈值 ----------


def _file_with_bad_lines(tmp_path, good_rows, bad_rows) -> TrafficDatStore:
    store = _store(tmp_path)
    lines = [HEADER_LINE, "key,global"] + [f"raw,{100 + i},1,1,1,1" for i in range(good_rows)]
    lines += ["garbage-line"] * bad_rows
    _write_dat(store.series_path("global"), lines)
    return store


def test_corrupt_ratio_over_threshold_moves_aside(tmp_path):
    """>5% 坏行 -> 原文移 .corrupt(只留最近一份现场) + 按空文件对待 + 下次追加重建"""
    store = _file_with_bad_lines(tmp_path, good_rows=19, bad_rows=2)  # 2/22 > 5%
    path = store.series_path("global")
    original = _read_text(path)
    parsed = store.read_series("global")
    assert parsed.raw == () and parsed.key == "global"  # 按空文件对待(同缺文件口径)
    assert os.path.exists(path + CORRUPT_SUFFIX)
    assert _read_text(path + CORRUPT_SUFFIX) == original  # 原文保全(不静默吞)
    store.append_point("global", 999, 1, 1, 1, 1)
    assert [r.ts for r in store.read_series("global").raw] == [999]  # 重建后接续


def test_corrupt_ratio_at_threshold_not_moved(tmp_path):
    """恰好 5%(1/20)不算损坏(严格大于): 行照常读出, 文件原位不动"""
    store = _file_with_bad_lines(tmp_path, good_rows=18, bad_rows=1)  # 1/(18+1+key) = 1/20
    path = store.series_path("global")
    parsed = store.read_series("global")
    assert len(parsed.raw) == 18 and parsed.bad_lines == 1
    assert os.path.exists(path) and not os.path.exists(path + CORRUPT_SUFFIX)


# ---------- 小时封口 ----------


def test_seal_hour_aggregates_bucket(tmp_path):
    """封口归并: avg(取整)/max 只计非 null 行; totals 取本小时末累计快照; raw 行保留"""
    store = _store(tmp_path)
    k = "global"
    store.append_point(k, H0 + 10, 100, 50, 1000, 500)
    store.append_point(k, H0 + 20, 300, 150, 2000, 1000)
    store.append_point(k, H0 + 30, None, None, None, None)  # null 行不参与
    assert store.seal_hour(k, H0, now=H1 + 1, raw_window=24 * HOUR, rollup_window=30 * 24 * HOUR) is True
    parsed = store.read_series(k)
    assert parsed.hours == (
        HourRow(hour_epoch=H0, dl_avg=200, dl_max=300, up_avg=100, up_max=150, dl_total=2000, up_total=1000),
    )
    assert [r.ts for r in parsed.raw] == [H0 + 10, H0 + 20, H0 + 30]  # raw 段按窗保留(未到裁剪龄)


def test_seal_hour_null_only_bucket_no_row(tmp_path):
    """桶内全 null 行 -> 不产 hour 行(30d 视图由缺行呈现断线, §05.1 空桶 = null)"""
    store = _store(tmp_path)
    store.append_point("global", H0 + 10, None, None, None, None)
    store.append_point("global", H0 + 40, None, None, None, None)
    assert store.seal_hour("global", H0, now=H1 + 1, raw_window=24 * HOUR, rollup_window=30 * 24 * HOUR) is False
    assert store.read_series("global").hours == ()


def test_seal_hour_upsert_idempotent(tmp_path):
    """同桶重封: 替换旧 hour 行(无重复); 内容无变化跳过重写(幂等, 黄金法则 1)"""
    store = _store(tmp_path)
    k = "global"
    store.append_point(k, H0 + 10, 100, 50, 1000, 500)
    assert store.seal_hour(k, H0, now=H1 + 1, raw_window=24 * HOUR, rollup_window=30 * 24 * HOUR) is True
    first = _read_text(store.series_path(k))
    assert store.seal_hour(k, H0, now=H1 + 2, raw_window=24 * HOUR, rollup_window=30 * 24 * HOUR) is False
    assert _read_text(store.series_path(k)) == first  # 零重写
    # 迟到行入桶(异常时序兜底) -> 重封归并出新值, hour 行仍恰一条
    store.append_point(k, H0 + 50, 300, 150, 1500, 750)
    assert store.seal_hour(k, H0, now=H1 + 3, raw_window=24 * HOUR, rollup_window=30 * 24 * HOUR) is True
    parsed = store.read_series(k)
    assert len(parsed.hours) == 1
    assert parsed.hours[0].dl_avg == 200 and parsed.hours[0].dl_max == 300  # (100+300)/2, max
    assert parsed.hours[0].dl_total == 1500  # 本小时末快照


def test_seal_cleans_torn_tail(tmp_path):
    """崩溃残留坏行随下一次有变化的封口重写一并清除(一次性自洁)"""
    store = _store(tmp_path)
    path = store.series_path("global")
    store.append_point("global", H0 + 10, 100, 50, 1000, 500)
    with open(path, "r+b") as f:
        f.truncate(os.path.getsize(path) - 5)  # 末行截成 5 列半行("raw,36010,100,50,1000", 无换行)
    assert store.read_series("global").bad_lines == 1
    assert store.seal_hour("global", H0, now=H1 + 1, raw_window=24 * HOUR, rollup_window=30 * 24 * HOUR) is True
    assert store.read_series("global").bad_lines == 0  # 残行已清


def test_prune_exact_n_rows_boundary(tmp_path):
    """窗口裁剪边界(恰好压线行保留): raw 段 ts >= now-raw_window; hour 段 epoch >= now-rollup_window"""
    store = _store(tmp_path)
    path = store.series_path("global")
    _write_dat(
        path,
        [
            HEADER_LINE,
            "key,global",
            "hour,0,1,1,1,1,1,1",  # 老桶
            "hour,6400,1,1,1,1,1,1",  # 恰在 rollup_window 压线(10000-3600) -> 保留
            "hour,6401,1,1,1,1,1,1",
            "raw,9890,1,1,1,1",  # 压线外(9900-1) -> 裁
            "raw,9900,1,1,1,1",  # 恰在 raw_window 压线 -> 留
            "raw,9910,1,1,1,1",
        ],
    )
    assert store.seal_hour("global", H0, now=10000, raw_window=100, rollup_window=3600) is True
    parsed = store.read_series("global")
    assert [h.hour_epoch for h in parsed.hours] == [6400, 6401]  # 老桶裁掉, 压线桶保留
    assert [r.ts for r in parsed.raw] == [9900, 9910]  # 正好 2 行


def test_rewrite_permission_error_backoff_retry(tmp_path, monkeypatch):
    """Windows 读侧竞态: os.replace PermissionError 退避重试后成功; 持续失败放弃本轮且原文件完好"""
    store = _store(tmp_path)
    k = "global"
    store.append_point(k, H0 + 10, 100, 50, 1000, 500)
    path = store.series_path(k)
    real_replace = os.replace
    calls = {"n": 0}

    def flaky_replace(src, dst, *a, **kw):
        calls["n"] += 1
        if calls["n"] <= 2:
            raise PermissionError(f"[Errno 13] 模拟读侧占用: {dst}")
        return real_replace(src, dst, *a, **kw)

    monkeypatch.setattr(os, "replace", flaky_replace)
    monkeypatch.setattr("auto_qb.core.traffic_store.time.sleep", lambda s: None)  # 退避不等真实时长
    assert store.seal_hour(k, H0, now=H1 + 1, raw_window=24 * HOUR, rollup_window=30 * 24 * HOUR) is True
    assert calls["n"] == 3  # 2 次占用 + 1 次成功
    assert len(store.read_series(k).hours) == 1
    # 持续失败: 桶内新行使本轮封口必然要求 rewrite, 放弃后返回 False, 原文件完好, 无 tmp 残留
    calls["n"] = 0
    store.append_point(k, H0 + 20, 300, 150, 1500, 750)

    def always_busy(src, dst, *a, **kw):
        calls["n"] += 1
        raise PermissionError(dst)

    monkeypatch.setattr(os, "replace", always_busy)
    before = _read_text(path)
    assert store.seal_hour(k, H0, now=H1 + 2, raw_window=24 * HOUR, rollup_window=30 * 24 * HOUR) is False
    assert calls["n"] == REWRITE_RETRIES + 1  # 首次 + 退避重试 x3
    assert _read_text(path) == before  # 新 raw 行仍在, hour 行未更新(下轮封口自然补上)
    assert sorted(p for p in os.listdir(os.path.dirname(path)) if p.endswith(".tmp")) == []


# ---------- index.json ----------


def test_index_written_only_at_change_points(tmp_path):
    """index 仅条目变化时点写: 建文件即写; 追加只推进内存(updated_at), 封口时点统一冲刷"""
    store = _store(tmp_path)
    k = "torrent:ABC123"
    store.append_point(k, 100, 1, 1, 1, 1)
    index_path = tmp_path / TRAFFIC_DIR_NAME / "index.json"
    assert index_path.is_file()
    first = json.loads(index_path.read_text(encoding="utf-8"))
    assert first["format"] == 1 and first["torrents"]["ABC123"]["frozen_at"] is None  # 本阶段恒 None(S3)
    assert first["torrents"]["ABC123"]["created_at"] == 100
    # 追加不写盘(非每采样): updated_at 内存推进, 文件内容不变
    for i in range(3):
        store.append_point(k, 200 + i, 1, 1, 1, 1)
    assert json.loads(index_path.read_text(encoding="utf-8")) == first
    # 封口时点冲刷: updated_at 落盘
    store.seal_hour(k, H0, now=H1 + 1, raw_window=24 * HOUR, rollup_window=30 * 24 * HOUR)
    flushed = json.loads(index_path.read_text(encoding="utf-8"))
    assert flushed["torrents"]["ABC123"]["updated_at"] == 202


# ---------- 启动对账 ----------


def test_reconcile_orphan_dat_self_heals(tmp_path):
    """孤儿 dat(index 无条目)从头行 key, 重建条目: frozen_at=None, created/updated 取 mtime"""
    store = _store(tmp_path)
    path = store.series_path("torrent:ABC123")
    _write_dat(path, [HEADER_LINE, "key,torrent:ABC123", "raw,100,1,1,1,1"])
    counts = store.reconcile()
    assert counts == {"dropped_entries": 0, "recovered_entries": 1}
    e = store.entry("ABC123")
    assert e["frozen_at"] is None  # 本阶段(P2)一律 null
    assert e["created_at"] == pytest.approx(os.path.getmtime(path))
    assert e["updated_at"] == pytest.approx(os.path.getmtime(path))
    assert store.reconcile() == {"dropped_entries": 0, "recovered_entries": 0}  # 幂等


def test_reconcile_drops_entry_without_file(tmp_path):
    """index 条目无文件 -> 删条目(手工删文件/盘损自愈)"""
    store = _store(tmp_path)
    store._touch_entry("GHOST", 100)  # 直接造条目(无文件)
    assert store.entry("GHOST") is not None
    counts = store.reconcile()
    assert counts["dropped_entries"] == 1
    assert store.entry("GHOST") is None


def test_reconcile_self_heals_from_disk_when_index_corrupt(tmp_path):
    """index 坏/半写 -> 按空表自愈, 以磁盘头行为准重建; index 版本不符同样不猜"""
    store = _store(tmp_path)
    _write_dat(store.series_path("torrent:ABC123"), [HEADER_LINE, "key,torrent:ABC123", "raw,1,1,1,1,1"])
    index_path = tmp_path / TRAFFIC_DIR_NAME / "index.json"
    for bad in ('{"format": 1, "torrents": {"ABC123": ', "not json at all", '{"format": 99, "torrents": {}}'):
        _write_dat(str(index_path), [bad.rstrip("\n")])
        counts = store.reconcile()
        assert counts["recovered_entries"] == 1, bad
        assert store.entry("ABC123") is not None
        store._load_index()  # 自愈结果已落盘可回读
        assert store.entry("ABC123") is not None


def test_reconcile_key_mismatch_warns_filename_wins(tmp_path):
    """头行 key 与文件名失配 = key 行损坏: 告警并按文件名登记(不改写文件 —— 对账不动数据)"""
    store = _store(tmp_path)
    path = store.series_path("torrent:ABC123")
    _write_dat(path, [HEADER_LINE, "key,torrent:OTHER", "raw,100,1,1,1,1"])
    counts = store.reconcile()
    assert counts["recovered_entries"] == 1
    assert store.entry("ABC123") is not None  # 文件名(infohash)是存储身份(§02.2)
    assert "raw,100,1,1,1,1" in _read_text(path)  # 数据未被改动


def test_reconcile_never_touches_raw_hour_data(tmp_path):
    """对账只读目录与头行: dat 数据字节级不变; 存储目录不存在零动作且不建目录"""
    store = _store(tmp_path)
    _write_dat(store.series_path("torrent:ABC123"), [HEADER_LINE, "key,torrent:ABC123", "raw,1,1,1,1,1"])
    path = store.series_path("torrent:ABC123")
    before = _read_text(path)
    store.reconcile()
    assert _read_text(path) == before
    # 无目录: 零动作, 不创建任何目录(惰性创建纪律 —— 首个采样才建)
    empty = tmp_path / "elsewhere"
    empty.mkdir()
    store2 = TrafficDatStore(str(empty))
    assert store2.reconcile() == {"dropped_entries": 0, "recovered_entries": 0}
    assert not (empty / TRAFFIC_DIR_NAME).exists()


# ---------- 惰性建文件 / 重启接续 ----------


def test_lazy_file_creation_zero_files_without_samples(tmp_path):
    """惰性建文件: 从未采样(空闲种子)零文件零目录; global 首点(含 null 点)才建文件"""
    store = _store(tmp_path)
    store.seal_hour("global", H0, now=H1, raw_window=100, rollup_window=100)  # 无文件封口 = no-op
    store.read_series("global")  # 读不存在文件 = 空系列, 不触盘
    store.reconcile()  # 对账目录不存在 = 零动作
    assert not (tmp_path / TRAFFIC_DIR_NAME).exists()
    store.append_point("global", H1 + 5, None, None, None, None)  # 首点是 null 点也建
    assert (tmp_path / TRAFFIC_DIR_NAME / "global.dat").is_file()


def test_restart_continuity_appends_without_truncation(tmp_path):
    """重启接续: 新 store/新模块实例(baselines 空)在同一数据目录上接续追加不断史;
    重启后首窗 null(基线不落盘, S1 语义)"""
    # 第一段运行: 两轮采样(global.dat 2 行 + 单种 2 行)
    mgr = _mgr(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    seed_store(mgr, [_active_torrent()])
    mod = mgr.host.get("qb_traffic")
    mod.start(mgr.ctx, dry_run=False)
    _run_sample(mgr)
    _run_sample(mgr)
    gpath = tmp_path / TRAFFIC_DIR_NAME / "global.dat"
    tpath = tmp_path / TRAFFIC_DIR_NAME / "torrents" / "HASH123.dat"
    assert len(_read_text(gpath).splitlines()) == 4  # 头 + key + 2 行
    # 重启: 全新 manager(同 data_dir), 计数器推进
    mgr2 = _mgr(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr2.store.server_state = _ss(alltime_dl=10_001_000, alltime_ul=20_002_000)
    seed_store(mgr2, [_active_torrent(downloaded=5_000_700, uploaded=3_000_400)])
    mod2 = mgr2.host.get("qb_traffic")
    mod2.start(mgr2.ctx, dry_run=False)
    _run_sample(mgr2)
    assert mod2.latest[GLOBAL_SERIES_KEY].dl_inc is None  # 基线不落盘 -> 首窗 null(S1 语义)
    assert len(_read_text(gpath).splitlines()) == 5  # dat 接续追加, 不断史
    assert len(_read_text(tpath).splitlines()) == 5


# ---------- handler 接线 ----------


def test_handler_triggers_hourly_seal_once_per_hour(tmp_path, monkeypatch):
    """每小时首个采样触发封口扫描(上一小时桶); 同小时内不重复触发; 断连轮照常封口"""
    fixed = H1 + 100
    monkeypatch.setattr("auto_qb.core.modules.traffic_sample_mod.time.time", lambda: fixed)
    mgr = _mgr(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    # 预置上一小时桶的历史行(直接经存储层)
    TrafficDatStore(str(tmp_path)).append_point("global", H0 + 30, 500, 250, 100, 50)
    mod = mgr.host.get("qb_traffic")
    mod.start(mgr.ctx, dry_run=False)
    mgr.store.server_state = _ss()
    assert _run_sample(mgr) is True
    parsed = TrafficDatStore(str(tmp_path)).read_series("global")
    assert [h.hour_epoch for h in parsed.hours] == [H0]  # 上一小时桶已封口
    assert [r.ts for r in parsed.raw] == [H0 + 30, fixed]  # 本轮新行照常追加
    # 同小时第二轮: 不重复扫描
    swept = {"n": 0}
    real_sweep = mod._store.seal_sweep

    def counting_sweep(*a, **kw):
        swept["n"] += 1
        return real_sweep(*a, **kw)

    monkeypatch.setattr(mod._store, "seal_sweep", counting_sweep)
    assert _run_sample(mgr) is True
    assert swept["n"] == 0
    # 断连轮: 照常出 null 点且小时翻转时照常封口
    mgr.client = None
    monkeypatch.setattr("auto_qb.core.modules.traffic_sample_mod.time.time", lambda: H1 + 2 * HOUR)
    assert _run_sample(mgr) is True
    assert swept["n"] == 1
    assert mod.latest[GLOBAL_SERIES_KEY].dl_rate is None  # 断连 null 点
    assert [h.hour_epoch for h in TrafficDatStore(str(tmp_path)).read_series("global").hours] == [H0, H1]


def test_handler_dry_run_persists_nothing(tmp_path):
    """dry_run 全程零文件: start 跳过对账, handler 不落盘不封口(观测写盘属真实副作用)"""
    mgr = _mgr(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    seed_store(mgr, [_active_torrent()])
    mod = mgr.host.get("qb_traffic")
    mod.start(mgr.ctx, dry_run=True)
    assert _run_sample(mgr, dry_run=True) is True
    assert mod.latest != {}  # 采样照常进内存
    assert sorted(str(p) for p in tmp_path.rglob("*")) == [
        str(tmp_path / "state.json")
    ] or not list((tmp_path / TRAFFIC_DIR_NAME).rglob("*") if (tmp_path / TRAFFIC_DIR_NAME).exists() else [])


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
    """单写线程不变式: 全部 append_point 落盘发生在调用 run_due 的线程(= 主循环线程), 模块不建线程"""
    mgr = _mgr(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    seed_store(mgr, [_active_torrent()])
    mod = mgr.host.get("qb_traffic")
    mod.start(mgr.ctx, dry_run=False)
    seen = []
    orig = TrafficDatStore.append_point

    def spy(self, key, ts, *cols):
        seen.append((key, threading.get_ident()))
        return orig(self, key, ts, *cols)

    monkeypatch.setattr(TrafficDatStore, "append_point", spy)
    threads_before = threading.active_count()
    assert mgr.task_queue.run_due(max_tasks=10) == 1
    assert seen and {k for k, _ in seen} == {"global", "torrent:HASH123"}
    assert all(ident == threading.get_ident() for _, ident in seen)
    assert threading.active_count() == threads_before


def test_seal_sweep_covers_global_and_torrents_and_counts(tmp_path):
    """封口扫描 catch-up: 覆盖 global + torrents/ 全部 dat, 补封当前桶之前所有未封桶
    (含更早的漏封桶), 按文件数计数; 非 dat/.corrupt 不碰"""
    store = _store(tmp_path)
    store.append_point("global", H0 + 10, 100, 50, 100, 50)  # H0 桶未封 -> 重写
    store.append_point("torrent:A", H0 + 10, 100, 50, 100, 50)  # H0 桶未封 -> 重写
    store.append_point("torrent:B", H0 - 2 * HOUR, 100, 50, 100, 50)  # 更早漏封桶 -> catch-up 重写
    _write_dat(store.series_path("torrent:C") + CORRUPT_SUFFIX, [HEADER_LINE, "key,torrent:C"])  # 现场文件不碰
    _write_dat(store.series_path("torrent:D").replace(".dat", ".txt"), ["junk"])  # 非 dat 不碰
    rewritten = store.seal_sweep(H1, now=H1 + 1, raw_window=24 * HOUR, rollup_window=30 * 24 * HOUR)
    assert rewritten == 3
    assert [h.hour_epoch for h in store.read_series("global").hours] == [H0]
    assert [h.hour_epoch for h in store.read_series("torrent:A").hours] == [H0]
    assert [h.hour_epoch for h in store.read_series("torrent:B").hours] == [H0 - 2 * HOUR]
    assert os.path.exists(store.series_path("torrent:C") + CORRUPT_SUFFIX)  # 原位未动
