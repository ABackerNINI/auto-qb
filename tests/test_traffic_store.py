"""test_traffic_store 测试计划: qB 口径流量 dat 存储层(plan 26-10-03-0946 方案C P2 落盘 + P3 生命周期, §02)

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
- test_lifecycle_freeze_absent_from_torrent_set: 删种冻结(S3): 不在当前种子集合 -> frozen_at=整数秒 + 变化时点落盘; 重复判定幂等; dat 数据不动
- test_lifecycle_freeze_requires_existing_file: 条目无文件不冻结(留给启动 reconcile)
- test_lifecycle_unfreeze_when_back_in_set: 重加解冻(S3): 重新出现 -> frozen_at=None, 历史保留; 幂等
- test_lifecycle_no_change_no_index_write: 无变化零落盘(不写 index)
- test_evict_expired_frozen_removes_file_and_entry: 冻结超 rollup_window -> 删文件+条目; 未超龄(边界含)/未冻结不删; index 同步落盘
- test_evict_missing_file_drops_entry_and_removal_failure_retries: 文件已不在删死条目; 删除失败(读侧竞态)保条目下轮重试
- test_evict_never_touches_global: global 不在 index 结构性豁免: 永不冻结永不淘汰
- test_evict_skips_malformed_updated_at: 条目 updated_at 畸形不据以删除(淘汰判定不崩溃)
- test_handler_lifecycle_persist_failure_not_fatal: 冻结/解冻判定落盘失败(OSError)不阻断采样
- test_handler_freezes_deleted_torrent_stops_appends: 删种 -> 采样轮判定冻结 + 后续轮零追加
- test_handler_unfreezes_readded_torrent_keeps_history: 重加 -> 采样轮解冻续写, 历史保留
- test_handler_disconnect_round_skips_lifecycle: 断连轮跳过冻结/解冻判定(快照 stale), 恢复连接后才冻结
- test_handler_dry_run_skips_lifecycle: dry_run 不做生命周期判定(不构造存储层)
- test_handler_evicts_expired_frozen_at_seal_timing: 淘汰复用封口时机: 翻小时轮删除超龄冻结文件; 同小时轮不淘汰
- test_volume_regression_200_torrents_full_window: 体量回归(P3 验收): 200 活跃种子 + global 满窗数据 <= 201x205KB(≈41MB, §02.3 推导式); 满窗稳态封口零重写
- test_zrow_roundtrip_and_v2_mixed_rows: format_z_row 产出可被 v2 解析还原为相同 ZRow; v2 头行 + 混合行(raw/null/z/hour)解析正确, zruns 携带在 ParsedSeries(v1 文件恒空)
- test_v1_header_z_line_counted_bad: v1 头行文件 + z 行 -> 按坏行计数(zruns 恒空, v1 语义逐字节不变)
- test_z_bad_line_family_counts_bad: z 坏行族逐项计坏行(列数≠5/负数/非数值/空列/end<start), 合法 z 行不受牵连
- test_z_span_boundary_exact_day: span = ZRUN_MAX_SPAN_S(86400) 恰好合法, 86401 坏行
- test_z_corrupt_threshold_quarantine: 坏 z 行计入损坏占比分子分母, 达阈值整文件隔离移 .corrupt; 未达阈值照常跳过计数
- test_append_z_run_new_file_writes_v2_header: append_z_run 全新文件头行直接 v2 + key 行 + z 行; 单种键同步建 index 条目(updated_at=行程终点)
- test_append_z_run_upgrades_v1_header_content_preserving: v1 文件首 z 追加触发头行升级(内容保持重写, 仅头行变 v2 数据行逐字节不变), z 行落盘后解析零坏行
- test_append_z_run_upgrade_failure_appends_nothing: 头行升级重写失败(读侧竞态) -> OSError 且文件原样(z 行绝不追加, R3 硬不变式)
- test_append_z_run_torn_tail_repaired_no_merge: 崩溃残留半行后 z 追加先补换行不与残行合并(kill 丢 <=1 行口径与 append_point 同)
- test_seal_rewrite_upgrades_v1_header: v1 文件封口重写(裁剪触发)头行升 v2(R3: 内容重写即升级)
- test_rewrite_keeps_z_rows_order_and_prunes_by_window: 重写输出序 = 头行(v2)+key+hour+z+raw; z 行按 end >= now-raw_window 裁剪, 其派生 hour 行不受影响
- test_same_content_compares_z_rows: z 行纳入 same_content: 窗内 z 行零重写(空闲零写放大); 仅 z 行差异(窗外待裁)触发真重写
- test_idle_z_bucket_produces_zero_hour_row: 全空闲桶(仅 z 覆盖无 raw 行)产 avg=0/max=0 hour 行, totals 取行程快照
- test_mixed_bucket_weighted_avg_and_end_snapshot: 混合桶加权均值 avg=(Σ raw 速率)/(n+w), w=交集秒数/interval_s; interval_s 缺省 None 与 30 同值; 桶末 totals 取行程快照
- test_cross_hour_run_splits_weight: 跨小时边界行程按交集拆权重进相邻两桶(各桶独立出 hour 行)
- test_seal_sweep_due_includes_z_only_bucket: 待封桶集合含仅 z 覆盖(无 raw 行)的桶(seal_sweep catch-up 产 hour 行); 当前桶不提前封
- test_idle_24h_line_count_z_vs_zero_rows: 行数影响: 全空闲 24h@30s, v1 零行方案 2880 行 vs z 行方案 144 行(600s 封口节奏), 体积比 >10x
- test_read_series_z_grid_expansion_end_to_end: 端到端打通(P3, plan 26-10-04-0721 §04.1) —— append_point + append_z_run 落盘 -> read_series -> grid 覆盖展开: 空闲段 0 平线 + totals 空闲 delta=0 链不断

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
from auto_qb.core.traffic_grid import BucketObs, build_grid, rate_points, series_bucket_obs, series_totals_points
from auto_qb.core.traffic_store import (
    CORRUPT_SUFFIX,
    HEADER_LINE,
    HEADER_LINE_V2,
    HOUR_SECONDS,
    HourRow,
    REWRITE_RETRIES,
    RawRow,
    TRAFFIC_DIR_NAME,
    ZRUN_MAX_SPAN_S,
    ZRow,
    TrafficDatStore,
    format_hour_row,
    format_raw_row,
    format_z_row,
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
    assert first["format"
                ] == 1 and first["torrents"]["ABC123"]["frozen_at"] is None  # 建条目恒 None(冻结由 S3 lifecycle_sweep 判定)
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
    assert e["frozen_at"] is None  # 对账重建恒 null(冻结由 S3 lifecycle_sweep 判定)
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


# ---------- S3 生命周期: 冻结/解冻/按龄淘汰(§02.2/§02.5) ----------


def test_lifecycle_freeze_absent_from_torrent_set(tmp_path):
    """删种冻结: 条目未冻结 + 文件存在 + 不在当前种子集合 -> frozen_at=整数秒且变化时点落盘;
    重复判定幂等(已冻结不重复计数); 冻结只动注册表不动 dat 数据"""
    store = _store(tmp_path)
    store.append_point("torrent:ABC123", 100, 1, 1, 1, 1)  # 建文件 + 建条目
    path = store.series_path("torrent:ABC123")
    before = _read_text(path)
    assert store.lifecycle_sweep({"OTHER"}, now=200.6) == {"frozen": 1, "unfrozen": 0}
    assert store.entry("ABC123")["frozen_at"] == 200  # 整数秒(§02.5 示例口径)
    on_disk = json.loads((tmp_path / TRAFFIC_DIR_NAME / "index.json").read_text(encoding="utf-8"))
    assert on_disk["torrents"]["ABC123"]["frozen_at"] == 200  # 条目变化时点落盘
    assert _read_text(path) == before  # 数据不动
    assert store.lifecycle_sweep({"OTHER"}, now=300) == {"frozen": 0, "unfrozen": 0}  # 幂等


def test_lifecycle_freeze_requires_existing_file(tmp_path):
    """文件不存在的失配条目不冻结(死条目留给启动 reconcile 删除)"""
    store = _store(tmp_path)
    store._touch_entry("GHOST", 100)  # 直接造条目(无文件)
    assert store.lifecycle_sweep(set(), now=200) == {"frozen": 0, "unfrozen": 0}
    assert store.entry("GHOST")["frozen_at"] is None


def test_lifecycle_unfreeze_when_back_in_set(tmp_path):
    """重加解冻: 已冻结条目重新出现在种子集合 -> frozen_at=None, 历史保留(数据不动);
    重复判定幂等(未冻结不重复计数)"""
    store = _store(tmp_path)
    store.append_point("torrent:ABC123", 100, 1, 1, 1, 1)
    store.lifecycle_sweep(set(), now=200)
    before = _read_text(store.series_path("torrent:ABC123"))
    assert store.lifecycle_sweep({"ABC123"}, now=300) == {"frozen": 0, "unfrozen": 1}
    assert store.entry("ABC123")["frozen_at"] is None
    assert _read_text(store.series_path("torrent:ABC123")) == before  # 历史保留
    assert store.lifecycle_sweep({"ABC123"}, now=400) == {"frozen": 0, "unfrozen": 0}  # 幂等


def test_lifecycle_no_change_no_index_write(tmp_path, monkeypatch):
    """无变化零落盘: 无冻结/解冻发生时不写 index(仅条目变化时点写, §02.5)"""
    from auto_qb.core import traffic_store as traffic_store_mod

    store = _store(tmp_path)
    store.append_point("torrent:ABC123", 100, 1, 1, 1, 1)  # 建条目(此前的写不受计数影响)
    writes = []
    real_atomic = traffic_store_mod.atomic_write

    def counting_write(path, write_fn, **kw):
        writes.append(path)
        return real_atomic(path, write_fn, **kw)

    monkeypatch.setattr(traffic_store_mod, "atomic_write", counting_write)
    store.lifecycle_sweep({"ABC123"}, now=200)  # 在集合内且未冻结: 无变化
    store.lifecycle_sweep({"ABC123"}, now=300)
    assert writes == []
    store.lifecycle_sweep(set(), now=400)  # 变化时点(冻结): 恰一次写
    assert len(writes) == 1


def test_evict_expired_frozen_removes_file_and_entry(tmp_path):
    """按龄淘汰: frozen 且 now - updated_at > rollup_window -> 删 dat 文件 + index 条目;
    未超龄(边界含 now-updated == rollup_window)/未冻结不删; index 同步落盘"""
    store = _store(tmp_path)
    for h in ("OLD", "FRESH", "ALIVE"):
        store.append_point(f"torrent:{h}", 100, 1, 1, 1, 1)
    store.lifecycle_sweep(set(), now=200)  # 三个全部冻结
    window = 7200
    for h in ("OLD", "ALIVE"):
        store._index[h]["updated_at"] = 1000
    store._index["FRESH"]["updated_at"] = 1000 + window  # 年龄 1s(检查时刻之前刚活动)
    store._index["ALIVE"]["frozen_at"] = None  # 未冻结对照组
    assert store.evict_expired_frozen(now=1000 + window, rollup_window=window) == 0  # 边界: 严格大于才删
    assert store.evict_expired_frozen(now=1000 + window + 1, rollup_window=window) == 1
    assert store.entry("OLD") is None  # 超龄冻结: 文件 + 条目均删
    assert not os.path.exists(store.series_path("torrent:OLD"))
    assert store.entry("FRESH") is not None  # 未超龄不删
    assert os.path.exists(store.series_path("torrent:FRESH"))
    assert store.entry("ALIVE") is not None  # 未冻结不淘汰(哪怕超龄)
    on_disk = json.loads((tmp_path / TRAFFIC_DIR_NAME / "index.json").read_text(encoding="utf-8"))
    assert "OLD" not in on_disk["torrents"] and "FRESH" in on_disk["torrents"]


def test_evict_missing_file_drops_entry_and_removal_failure_retries(tmp_path, monkeypatch):
    """淘汰删除: 文件已不在(FileNotFoundError)删死条目; 删除失败(Windows 读侧竞态
    PermissionError)保留条目下轮重试 —— 条目与文件状态恒一致, 不产孤儿"""
    store = _store(tmp_path)
    store.append_point("torrent:GONE", 100, 1, 1, 1, 1)
    store.append_point("torrent:LOCKED", 100, 1, 1, 1, 1)
    store.lifecycle_sweep(set(), now=200)
    for h in ("GONE", "LOCKED"):
        store._index[h]["updated_at"] = 0  # 远超任何窗口
    os.remove(store.series_path("torrent:GONE"))  # 文件先消失
    real_remove = os.remove

    def failing_remove(path, *a, **kw):
        if str(path).endswith("LOCKED.dat"):
            raise PermissionError(13, "locked by reader")
        return real_remove(path, *a, **kw)

    monkeypatch.setattr("auto_qb.core.traffic_store.os.remove", failing_remove)
    assert store.evict_expired_frozen(now=10**9, rollup_window=7200) == 1  # GONE 删条目, LOCKED 失败保留
    assert store.entry("GONE") is None
    assert store.entry("LOCKED") is not None
    assert os.path.exists(store.series_path("torrent:LOCKED"))
    monkeypatch.setattr("auto_qb.core.traffic_store.os.remove", real_remove)  # 下轮竞态解除
    assert store.evict_expired_frozen(now=10**9, rollup_window=7200) == 1  # 重试成功
    assert store.entry("LOCKED") is None
    assert not os.path.exists(store.series_path("torrent:LOCKED"))


def test_evict_never_touches_global(tmp_path):
    """global 永不冻结永不淘汰(§02.5): 不在 index, 结构性豁免 —— 全库清空 + 极小淘汰窗都不碰"""
    store = _store(tmp_path)
    store.append_point("global", 100, 1, 1, 1, 1)
    path = store.series_path("global")
    assert store.lifecycle_sweep(set(), now=200) == {"frozen": 0, "unfrozen": 0}  # 无条目可冻
    assert store.evict_expired_frozen(now=10**9, rollup_window=1) == 0
    assert os.path.exists(path)
    assert _read_text(path).splitlines() == [HEADER_LINE, "key,global", "raw,100,1,1,1,1"]
    assert store._index == {}


def test_evict_skips_malformed_updated_at(tmp_path):
    """条目 updated_at 畸形(手工编辑 index)不据以删除, 留给人工处置(淘汰判定不崩溃)"""
    store = _store(tmp_path)
    store.append_point("torrent:WEIRD", 100, 1, 1, 1, 1)
    store.lifecycle_sweep(set(), now=200)
    store._index["WEIRD"]["updated_at"] = None
    assert store.evict_expired_frozen(now=10**9, rollup_window=1) == 0
    assert store.entry("WEIRD") is not None
    assert os.path.exists(store.series_path("torrent:WEIRD"))


def test_handler_lifecycle_persist_failure_not_fatal(tmp_path, monkeypatch):
    """冻结/解冻判定落盘失败(OSError)不阻断采样: 本轮照常出点"""
    mgr = _mgr(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    seed_store(mgr, [_active_torrent()])
    mod = mgr.host.get("qb_traffic")
    mod.start(mgr.ctx, dry_run=False)

    def failing_sweep(self, present, now):
        raise OSError("disk full")

    monkeypatch.setattr(TrafficDatStore, "lifecycle_sweep", failing_sweep)
    assert _run_sample(mgr) is True  # 不上抛
    assert GLOBAL_SERIES_KEY in mod.latest and "torrent:HASH123" in mod.latest  # 采样照常


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


# ---------- S3 handler 接线: 冻结/解冻/淘汰随采样轮(§02.2/§02.5) ----------


def test_handler_freezes_deleted_torrent_stops_appends(tmp_path, monkeypatch):
    """删种 -> 采样轮判定冻结: frozen_at 置值且后续轮零追加(停止追加, §02.2)"""
    t = {"now": H1 + 100.0}
    monkeypatch.setattr("auto_qb.core.modules.traffic_sample_mod.time.time", lambda: t["now"])
    mgr = _mgr(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    seed_store(mgr, [_active_torrent()])
    mod = mgr.host.get("qb_traffic")
    mod.start(mgr.ctx, dry_run=False)
    assert _run_sample(mgr) is True
    tpath = tmp_path / TRAFFIC_DIR_NAME / "torrents" / "HASH123.dat"
    lines_at_freeze = len(_read_text(tpath).splitlines())
    # 删种: 内存快照移除 -> 下一轮(同小时, 不触发封口)冻结
    mgr.store.by_hash.pop("HASH123")
    t["now"] = H1 + 160.0
    assert _run_sample(mgr) is True
    assert mod._store.entry("HASH123")["frozen_at"] == int(H1 + 160.0)
    # 继续推进多轮: 冻结文件零追加
    t["now"] = H1 + 220.0
    _run_sample(mgr)
    assert len(_read_text(tpath).splitlines()) == lines_at_freeze


def test_handler_unfreezes_readded_torrent_keeps_history(tmp_path, monkeypatch):
    """重加 -> 采样轮解冻续写: frozen_at 清零, 历史行保留, 新行照常追加
    (重加后 all-time 计数器回落由既有判重置兜底, 见 test_counter_rollback_records_reset_no_negative)"""
    t = {"now": H1 + 100.0}
    monkeypatch.setattr("auto_qb.core.modules.traffic_sample_mod.time.time", lambda: t["now"])
    mgr = _mgr(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    seed_store(mgr, [_active_torrent()])
    mod = mgr.host.get("qb_traffic")
    mod.start(mgr.ctx, dry_run=False)
    _run_sample(mgr)
    mgr.store.by_hash.pop("HASH123")
    t["now"] = H1 + 160.0
    _run_sample(mgr)
    assert mod._store.entry("HASH123")["frozen_at"] is not None
    tpath = tmp_path / TRAFFIC_DIR_NAME / "torrents" / "HASH123.dat"
    frozen_text = _read_text(tpath)
    # 同 hash 重加(活跃, 计数器推进) -> 同轮先解冻再采样追加
    seed_store(mgr, [_active_torrent(downloaded=6_000_000, uploaded=4_000_000)])
    t["now"] = H1 + 220.0
    assert _run_sample(mgr) is True
    assert mod._store.entry("HASH123")["frozen_at"] is None
    unfrozen_text = _read_text(tpath)
    assert unfrozen_text.startswith(frozen_text)  # 历史保留(同小时纯追加, 前缀不变)
    assert len(unfrozen_text.splitlines()) == len(frozen_text.splitlines()) + 1  # 解冻后续写


def test_handler_disconnect_round_skips_lifecycle(tmp_path, monkeypatch):
    """断连轮跳过冻结/解冻判定(by_hash 是断连前快照, 误判会冻结在线种子/漏判重加);
    恢复连接后才按当前种子集合判定"""
    t = {"now": H1 + 100.0}
    monkeypatch.setattr("auto_qb.core.modules.traffic_sample_mod.time.time", lambda: t["now"])
    mgr = _mgr(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    seed_store(mgr, [_active_torrent()])
    mod = mgr.host.get("qb_traffic")
    mod.start(mgr.ctx, dry_run=False)
    _run_sample(mgr)
    mgr.store.by_hash.pop("HASH123")  # 删种恰好落在断连期(快照不可知)
    mgr.client = None
    t["now"] = H1 + 160.0
    _run_sample(mgr)
    assert mod._store.entry("HASH123")["frozen_at"] is None  # 断连轮不判
    mgr.client = FakeClient()
    t["now"] = H1 + 220.0
    _run_sample(mgr)
    assert mod._store.entry("HASH123")["frozen_at"] == int(H1 + 220.0)  # 恢复连接后才冻结


def test_handler_dry_run_skips_lifecycle(tmp_path, monkeypatch):
    """dry_run 不做生命周期判定(观测写盘属真实副作用, 零落盘纪律): 存储层连构造都不发生"""
    t = {"now": H1 + 100.0}
    monkeypatch.setattr("auto_qb.core.modules.traffic_sample_mod.time.time", lambda: t["now"])
    mgr = _mgr(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    seed_store(mgr, [_active_torrent()])
    mod = mgr.host.get("qb_traffic")
    mod.start(mgr.ctx, dry_run=True)
    TrafficDatStore(str(tmp_path)).append_point("torrent:HASH123", H1 - 60, 1, 1, 1, 1)  # 预置历史条目+文件
    mgr.store.by_hash.pop("HASH123")
    assert _run_sample(mgr, dry_run=True) is True
    assert mod._store is None  # 未构造存储层(dry_run 不触盘)
    on_disk = json.loads((tmp_path / TRAFFIC_DIR_NAME / "index.json").read_text(encoding="utf-8"))
    assert on_disk["torrents"]["HASH123"]["frozen_at"] is None  # 磁盘条目未被冻结


def test_handler_evicts_expired_frozen_at_seal_timing(tmp_path, monkeypatch):
    """淘汰复用封口时机(§02.5, 无独立任务): 超龄冻结文件在翻小时的首个采样轮删除;
    同小时内的采样轮不淘汰"""
    t = {"now": H1 + 100.0}
    monkeypatch.setattr("auto_qb.core.modules.traffic_sample_mod.time.time", lambda: t["now"])
    conf = QbTraffic(enabled=True, sample_interval=30, raw_window=3600, rollup_window=7200)
    mgr = _mgr(tmp_path, conf)
    mgr.store.server_state = _ss()
    seed_store(mgr, [_active_torrent()])
    mod = mgr.host.get("qb_traffic")
    mod.start(mgr.ctx, dry_run=False)
    _run_sample(mgr)  # 建文件 + 建条目(本轮触发首次封口扫描)
    mgr.store.by_hash.pop("HASH123")
    t["now"] = H1 + 160.0
    _run_sample(mgr)  # 冻结(同小时)
    mod._store._index["HASH123"]["updated_at"] = int(H1 + 160.0) - 7201  # 最后活动已超 rollup_window
    tpath = tmp_path / TRAFFIC_DIR_NAME / "torrents" / "HASH123.dat"
    t["now"] = H1 + 220.0
    _run_sample(mgr)  # 同小时: 未到封口时机 -> 不淘汰
    assert os.path.exists(tpath)
    t["now"] = H1 + HOUR + 100.0
    _run_sample(mgr)  # 翻小时: 封口轮顺带淘汰
    assert not os.path.exists(tpath)
    assert mod._store.entry("HASH123") is None


# ---------- S3 体量回归(P3 验收, §02.3) ----------


def test_volume_regression_200_torrents_full_window(tmp_path):
    """体量回归: 200 活跃种子 + global 满窗连续活跃数据 -> 总盘占用 <= 201 x 205KB(≈41MB 上界)

    推导式(§02.3, 列宽取保守上界: 速率 <= 9,999,999 B/s≈9.5MB/s、累计 <= 9,999,999,999 B≈9.3GB、
    epoch 10 位): 单文件 = 头行 24B + key 行 46B(infohash 40 hex) + raw 2880 行(24h@30s)
    x 51B + hour 720 行(30d) x 66B = 194,470B <= 205KB; 201 文件 => 209,920 x 201
    = 42,193,920B ≈ 41MB(全部满窗连续活跃的保守假设; 空闲种子零行, 实际远小)。
    满窗数据按格式 v1 直接造文件(走存储层 API 需 201x2880 次 open 追加, 回归测试不可承受);
    随后一次封口扫描验证满窗稳态零重写(体量不增长)。
    """
    now = 1_800_000_000  # 整点 epoch(10 位, 2027-01-15), raw/hour 桶对齐
    raw_lines = [format_raw_row(now - 24 * HOUR + i * 30, 999999, 999999, 9999999999, 9999999999) for i in range(2880)]
    hour0 = now - 719 * HOUR  # 720 个整点桶铺满 30d 窗, 顶桶 = now(覆盖 raw 全部桶)
    hour_lines = [
        format_hour_row(HourRow(hour0 + j * HOUR, 999999, 999999, 999999, 999999, 9999999999, 9999999999))
        for j in range(720)
    ]
    root = tmp_path / TRAFFIC_DIR_NAME
    tdir = root / "torrents"
    tdir.mkdir(parents=True)
    for i in range(200):
        h = f"{i:040x}"  # 40 位 hex, 对齐真实 infohash 宽度
        _write_dat(tdir / f"{h}.dat", [HEADER_LINE, f"key,torrent:{h}"] + raw_lines + hour_lines)
    _write_dat(root / "global.dat", [HEADER_LINE, "key,global"] + raw_lines + hour_lines)
    dat_files = sorted(tdir.glob("*.dat")) + [root / "global.dat"]
    assert len(dat_files) == 201
    per_file_bound = 205 * 1024  # §02.3 单文件上界(205KB)
    sizes = [p.stat().st_size for p in dat_files]
    assert max(sizes) <= per_file_bound
    total = sum(sizes)
    assert total <= 201 * per_file_bound  # ≈41MB 总量上界
    # 满窗稳态: 封口扫描零重写(已封桶不重算 + 裁剪无窗外行), 体量不增长
    store = _store(tmp_path)
    assert store.seal_sweep((now // HOUR) * HOUR, now=now, raw_window=24 * HOUR, rollup_window=30 * 24 * HOUR) == 0
    assert sum(p.stat().st_size for p in dat_files) == total


# ---------- v2 z 行(plan 26-10-04-0721 P1a: 只做读路径与格式定义) ----------


def test_zrow_roundtrip_and_v2_mixed_rows():
    """v2 头行 + 混合行(raw/null/z/hour)解析正确, zruns 携带在 ParsedSeries;
    format_z_row 产出可被 v2 解析还原为相同 ZRow; v1 文件 zruns 恒空(默认字段零改动)"""
    text = "\n".join(
        [
            HEADER_LINE_V2,
            "key,global",
            "raw,100,1,2,3,4",
            "raw,130,,,,",  # null 行: v1 v2 同形
            format_z_row(200, 260, 3, 4),
            f"hour,{H0},1,1,1,1,10,10",
        ]
    )
    p = parse_dat_text(text)
    assert p.key == "global"
    assert [r.ts for r in p.raw] == [100, 130] and p.raw[1].is_null
    assert p.hours == (HourRow(hour_epoch=H0, dl_avg=1, dl_max=1, up_avg=1, up_max=1, dl_total=10, up_total=10), )
    assert p.zruns == (ZRow(start=200, end=260, dl_total=3, up_total=4), )
    assert p.bad_lines == 0 and p.data_lines == 5
    # roundtrip: format 逐列还原(含 10 位大数)
    assert format_z_row(200, 260, 3, 4) == "z,200,260,3,4"
    p2 = parse_dat_text("\n".join([HEADER_LINE_V2, "key,global", format_z_row(0, 3600, 9_999_999_999, 8_888_888_888)]))
    assert p2.zruns == (ZRow(start=0, end=3600, dl_total=9_999_999_999, up_total=8_888_888_888), )
    # v1 既有解析结果 zruns 恒空(默认空元组, 全部既有构造点零改动)
    p1 = parse_dat_text("\n".join([HEADER_LINE, "key,global", "raw,100,1,2,3,4"]))
    assert p1.zruns == ()


def test_v1_header_z_line_counted_bad():
    """v1 头行 + z 行 -> 按坏行计数(zruns 恒空): v1 语义逐字节不变(双读门闩, §02.2)"""
    text = "\n".join([
        HEADER_LINE,
        "key,global",
        "raw,100,1,2,3,4",
        "z,200,260,3,4",  # v1 头行不认 z 行
        "garbage",
    ])
    p = parse_dat_text(text)
    assert p.key == "global"
    assert [r.ts for r in p.raw] == [100] and p.hours == () and p.zruns == ()
    assert p.bad_lines == 2 and p.data_lines == 4  # 分母含 key 行(结构行), 不含头行


def test_z_bad_line_family_counts_bad():
    """z 坏行族逐项计坏行: 列数!=5 / 负数 / 非数值 / 空列 / end<start; 合法 z 行不受牵连"""
    good = "z,100,160,3,4"
    bad_lines = [
        "z,100,160,3",  # 列数不足
        "z,100,160,3,4,9",  # 列数超出
        "z,-100,160,3,4",  # 负时间列
        "z,100,160,-3,4",  # 负 totals 列
        "z,100,160,x,4",  # 非数值
        "z,100,,3,4",  # 空列(ZRow 恒非负整数, 无 null 形态)
        "z,200,100,3,4",  # end < start
    ]
    text = "\n".join([HEADER_LINE_V2, "key,global"] + bad_lines + [good])
    p = parse_dat_text(text)
    assert p.zruns == (ZRow(start=100, end=160, dl_total=3, up_total=4), )
    assert p.bad_lines == len(bad_lines) and p.data_lines == len(bad_lines) + 2  # 分母含 key 行


def test_z_span_boundary_exact_day():
    """span 边界: end - start = ZRUN_MAX_SPAN_S(86400) 恰好合法, 86401 坏行"""
    text = "\n".join([HEADER_LINE_V2, "key,global", "z,0,86400,1,1", "z,0,86401,1,1"])
    p = parse_dat_text(text)
    assert p.zruns == (ZRow(start=0, end=ZRUN_MAX_SPAN_S, dl_total=1, up_total=1), )
    assert p.bad_lines == 1


def test_z_corrupt_threshold_quarantine(tmp_path):
    """坏 z 行计入损坏占比(分子分母双侧, 与既有 raw 坏行同口径): 达阈值(>5% 且 >=2 行)
    整文件隔离移 .corrupt 后按空文件对待; 未达阈值时坏 z 行跳过计数, 合法行照常读出"""
    store = _store(tmp_path)
    path = store.series_path("global")
    lines = [HEADER_LINE_V2, "key,global"] + [f"raw,{100 + i},1,1,1,1" for i in range(19)]
    lines += ["z,0,-1,3,4", "z,x,1,1,1"]  # 2 坏 z 行 / 22 受检行 = 9.1% > 5%
    _write_dat(path, lines)
    original = _read_text(path)
    parsed = store.read_series("global")
    assert parsed.key == "global" and parsed.raw == () and parsed.zruns == ()  # 按空文件对待(同缺文件口径)
    assert os.path.exists(path + CORRUPT_SUFFIX)
    assert _read_text(path + CORRUPT_SUFFIX) == original  # 原文保全
    # 未达阈值: 坏 z 行(1 行, 不足绝对下限 2)跳过计数, 合法行照常
    store2 = _store(tmp_path / "sub")
    lines2 = [HEADER_LINE_V2, "key,global"] + [f"raw,{100 + i},1,1,1,1" for i in range(38)]
    lines2.append("z,0,-1,3,4")  # 1/40 且坏行 < 2 -> 不隔离
    _write_dat(store2.series_path("global"), lines2)
    p2 = store2.read_series("global")
    assert len(p2.raw) == 38 and p2.bad_lines == 1 and p2.zruns == ()
    assert os.path.exists(store2.series_path("global"))
    assert not os.path.exists(store2.series_path("global") + CORRUPT_SUFFIX)


# ---------- v2 写路径(plan 26-10-04-0721 P1b: append_z_run + R3 升级 + z 感知聚合) ----------


def test_append_z_run_new_file_writes_v2_header(tmp_path):
    """append_z_run 全新文件: 头行直接 v2 + key 行 + z 行; 单种键同步建 index 条目
    (updated_at = 行程终点 —— 空闲期 z 追加与 raw 追加同样推进, 不因无 raw 行被误判超龄)"""
    store = _store(tmp_path)
    store.append_z_run("global", 1000, 1599, 7, 8)
    lines = _read_text(store.series_path("global")).splitlines()
    assert lines == [HEADER_LINE_V2, "key,global", "z,1000,1599,7,8"]
    parsed = store.read_series("global")
    assert parsed.zruns == (ZRow(start=1000, end=1599, dl_total=7, up_total=8), ) and parsed.bad_lines == 0
    # 单种键: 建文件 + 建 index 条目, updated_at 推进到行程终点
    store.append_z_run("torrent:ABC123", 2000, 2599, 9, 10)
    e = store.entry("ABC123")
    assert e is not None and e["frozen_at"] is None and e["created_at"] == 2599 and e["updated_at"] == 2599
    tlines = _read_text(store.series_path("torrent:ABC123")).splitlines()
    assert tlines[0] == HEADER_LINE_V2 and tlines[-1] == "z,2000,2599,9,10"


def test_append_z_run_upgrades_v1_header_content_preserving(tmp_path):
    """v1 文件首 z 追加触发头行升级(R3): 内容保持重写 —— 仅头行 v1->v2, 数据行逐字节
    不变; 升级后 z 行落盘, 同一文件解析零坏行(绝不向未升级的 v1 头行文件追加 z 行)"""
    store = _store(tmp_path)
    path = store.series_path("global")
    _write_dat(path, [HEADER_LINE, "key,global", "raw,100,1,2,3,4", "raw,130,,,,"])
    before_body = _read_text(path).splitlines()[1:]  # 头行之外全部行
    store.append_z_run("global", 200, 260, 5, 6)
    lines = _read_text(path).splitlines()
    assert lines[0] == HEADER_LINE_V2  # 头行已升级
    assert lines[1:-1] == before_body  # 数据行逐字节不变(内容保持重写)
    assert lines[-1] == "z,200,260,5,6"  # z 行落盘
    parsed = store.read_series("global")
    assert parsed.bad_lines == 0 and parsed.zruns == (ZRow(start=200, end=260, dl_total=5, up_total=6), )
    assert [r.ts for r in parsed.raw] == [100, 130]  # 既有 raw 行原样


def test_append_z_run_upgrade_failure_appends_nothing(tmp_path, monkeypatch):
    """头行升级重写失败(读侧竞态占满重试) -> OSError 且文件逐字节原样:
    未升级绝不追加 z 行(R3 硬不变式 —— v1 解析器把 z 行判坏行, 追加即累积坏行)"""
    store = _store(tmp_path)
    path = store.series_path("global")
    _write_dat(path, [HEADER_LINE, "key,global", "raw,100,1,2,3,4"])
    before = _read_text(path)
    monkeypatch.setattr(store, "_write_payload", lambda p, payload: False)
    with pytest.raises(OSError):
        store.append_z_run("global", 200, 260, 5, 6)
    assert _read_text(path) == before  # 文件原样: 头行未升级, z 行未出现
    assert "z," not in before


def test_append_z_run_torn_tail_repaired_no_merge(tmp_path):
    """崩溃残留半行后 z 追加先补换行不与残行合并: 半行隔离计坏, z 行独立可读
    (kill 丢 <=1 行口径与 append_point 同)"""
    store = _store(tmp_path)
    path = store.series_path("global")
    store.append_point("global", 100, 1, 1, 1, 1)
    store.append_point("global", 130, 2, 2, 2, 2)
    with open(path, "r+b") as f:
        f.truncate(os.path.getsize(path) - 4)  # 末行截半(无换行)
    store.append_z_run("global", 200, 260, 3, 4)
    parsed = store.read_series("global")
    assert [r.ts for r in parsed.raw] == [100]  # 残半行未吞前行
    assert parsed.zruns == (ZRow(start=200, end=260, dl_total=3, up_total=4), )  # z 行独立成行
    assert parsed.bad_lines == 1 and not parsed.torn_tail  # 半行成中段坏行(下轮封口自洁), 文件已换行收尾


def test_seal_rewrite_upgrades_v1_header(tmp_path):
    """v1 文件封口重写(裁剪触发)头行升 v2(R3: 首次内容重写即升级)"""
    store = _store(tmp_path)
    path = store.series_path("global")
    _write_dat(path, [HEADER_LINE, "key,global", "raw,9890,1,1,1,1", "raw,9900,1,1,1,1"])
    assert store.seal_hour("global", 7200, now=10000, raw_window=100, rollup_window=3600) is True  # 9890 被裁 -> 重写
    lines = _read_text(path).splitlines()
    assert lines[0] == HEADER_LINE_V2
    assert store.read_series("global").zruns == ()  # 纯 raw 文件升级不添 z 行


def test_rewrite_keeps_z_rows_order_and_prunes_by_window(tmp_path):
    """重写输出序 = 头行(v2) + key + hour + z + raw; z 行按 end >= now-raw_window 裁剪
    (z 行属 raw 段数据), 其派生 hour 行在 hour 段按 rollup_window 独立留置不受影响"""
    store = _store(tmp_path)
    path = store.series_path("global")
    _write_dat(
        path,
        [
            HEADER_LINE_V2,
            "key,global",
            "z,100,200,1,1",  # end=200 << now-raw_window -> 裁
            "z,9900,9950,3,4",  # end=9950 恰压线 -> 留
            "raw,9950,100,50,7,8",
        ],
    )
    assert store.seal_hour("global", 7200, now=10000, raw_window=100, rollup_window=3600, interval_s=30) is True
    text = _read_text(path)
    lines = text.splitlines()
    assert lines[0] == HEADER_LINE_V2 and lines[1] == "key,global"
    # 输出序: hour 段 -> z 段 -> raw 段
    assert lines.index("z,9900,9950,3,4") > lines.index("hour,7200,37,100,19,50,3,4")
    assert lines.index("raw,9950,100,50,7,8") > lines.index("z,9900,9950,3,4")
    parsed = store.read_series("global")
    assert [z.end for z in parsed.zruns] == [9950]  # 窗外 z 行已裁
    assert [r.ts for r in parsed.raw] == [9950] and len(parsed.hours) == 1  # hour 行(raw_window 判定)不受 z 裁剪牵连
    assert "z,100,200" not in text


def test_same_content_compares_z_rows(tmp_path):
    """same_content 纳入 z 行: 全部封口且 z 行在窗内 -> 零重写(空闲系列零写放大);
    仅 z 行差异(窗外待裁, hour/raw 全同) = 内容不一致 -> 触发真重写"""
    store = _store(tmp_path)
    path = store.series_path("global")
    _write_dat(
        path,
        [
            HEADER_LINE_V2,
            "key,global",
            "hour,3600,0,0,0,0,3,4",  # z 覆盖桶已封(与聚合结果一致)
            "hour,7200,100,50,100,50,7,8",
            "z,9900,9950,3,4",  # 在窗内(now-raw_window=9900 压线保留)
            "raw,9950,100,50,7,8",
        ],
    )
    before = _read_text(path)
    assert store.seal_sweep(10800, now=10000, raw_window=100, rollup_window=7200) == 0
    assert _read_text(path) == before  # 零重写
    # 仅 z 行差异: z 行滑出窗外 -> hour/raw 全同也必须重写(坏行不算一致口径的 z 版)
    _write_dat(
        path,
        [
            HEADER_LINE_V2,
            "key,global",
            "hour,3600,0,0,0,0,3,4",
            "hour,7200,100,50,100,50,7,8",
            "z,3800,3900,3,4",  # end=3900 < 9900 -> 待裁; 其桶(3600)已封, 不产新 hour 行
            "raw,9950,100,50,7,8",
        ],
    )
    before2 = _read_text(path)
    assert store.seal_sweep(10800, now=10000, raw_window=100, rollup_window=7200) == 1
    after = _read_text(path)
    expected_after = "\n".join(l for l in before2.splitlines() if l != "z,3800,3900,3,4") + "\n"
    assert after == expected_after  # 仅 z 行被移除, hour/raw 逐字节不变(只 z 行差异触发真重写)


def test_idle_z_bucket_produces_zero_hour_row(tmp_path):
    """全空闲桶(仅 z 覆盖, 无 raw 行)产 avg=0/max=0 的 hour 行, totals 取行程快照
    (30d 单种图由 z 派生 hour 行带 0 线, §04.2)"""
    store = _store(tmp_path)
    store.append_z_run("global", H0, H0 + 3599, 5000, 6000)
    assert store.seal_hour("global", H0, now=H1 + 1, raw_window=24 * HOUR, rollup_window=30 * 24 * HOUR) is True
    parsed = store.read_series("global")
    assert parsed.hours == (
        HourRow(hour_epoch=H0, dl_avg=0, dl_max=0, up_avg=0, up_max=0, dl_total=5000, up_total=6000),
    )
    assert len(parsed.zruns) == 1 and parsed.raw == ()  # z 行本身仍在 raw 段留置


def test_mixed_bucket_weighted_avg_and_end_snapshot(tmp_path):
    """混合桶加权均值(§04.2): 桶内 2 行活跃 raw + 行程覆盖后段 2700s(interval 30 -> w=90):
    dl_avg = round((100+300)/(2+90)) = 4, up_avg = round((50+150)/92) = 2, max 不受 0 影响;
    桶末被行程覆盖 -> totals 取行程快照; interval_s 缺省 None 与显式 30 同值(默认路径确定)"""
    store = _store(tmp_path)
    k = "global"
    store.append_point(k, H0 + 10, 100, 50, 1000, 500)
    store.append_point(k, H0 + 20, 300, 150, 2000, 1000)
    store.append_z_run(k, H0 + 900, H0 + 3599, 5000, 6000)
    assert store.seal_hour(
        "global", H0, now=H1 + 1, raw_window=24 * HOUR, rollup_window=30 * 24 * HOUR, interval_s=30
    ) is True
    row = store.read_series(k).hours[0]
    assert (row.dl_avg, row.dl_max, row.up_avg, row.up_max) == (4, 300, 2, 150)
    assert (row.dl_total, row.up_total) == (5000, 6000)  # 行程快照(z 覆盖桶末)
    # 默认路径(interval_s=None -> DEFAULT_SAMPLE_INTERVAL_S=30): 数值逐列相同
    store2 = _store(tmp_path / "sub")
    for args in ((H0 + 10, 100, 50, 1000, 500), (H0 + 20, 300, 150, 2000, 1000)):
        store2.append_point(k, *args)
    store2.append_z_run(k, H0 + 900, H0 + 3599, 5000, 6000)
    store2.seal_hour("global", H0, now=H1 + 1, raw_window=24 * HOUR, rollup_window=30 * 24 * HOUR)
    assert store2.read_series(k).hours[0] == row


def test_cross_hour_run_splits_weight(tmp_path):
    """跨小时边界行程按交集拆权重进相邻两桶(§04.2): H0 段 100s(纯 z -> avg=0),
    H1 段 501s + 行程结束后 1 行活跃 raw(w=16.7 -> dl_avg=round(300/17.7)=17);
    各桶独立出 hour 行; 桶末在行程外 -> totals 取最新活跃行快照"""
    store = _store(tmp_path)
    k = "global"
    store.append_z_run(k, H0 + 3500, H1 + 500, 900, 800)  # 行程横跨 H0/H1 边界
    store.append_point(k, H1 + 600, 300, 200, 1200, 1100)
    assert store.seal_hour(
        "global", H0, now=H1 + HOUR, raw_window=24 * HOUR, rollup_window=30 * 24 * HOUR, interval_s=30
    ) is True
    assert store.seal_hour(
        "global", H1, now=H1 + HOUR, raw_window=24 * HOUR, rollup_window=30 * 24 * HOUR, interval_s=30
    ) is True
    hours = {h.hour_epoch: h for h in store.read_series(k).hours}
    assert (hours[H0].dl_avg, hours[H0].dl_max, hours[H0].up_avg, hours[H0].up_max) == (0, 0, 0, 0)
    assert (hours[H0].dl_total, hours[H0].up_total) == (900, 800)  # 行程快照
    assert (hours[H1].dl_avg, hours[H1].dl_max) == (17, 300)  # 加权: 300/(1+501/30)
    assert (hours[H1].up_avg, hours[H1].up_max) == (11, 200)
    assert (hours[H1].dl_total, hours[H1].up_total) == (1200, 1100)  # 桶末在行程外 -> 最新非 null 行快照


def test_seal_sweep_due_includes_z_only_bucket(tmp_path):
    """待封桶集合 = 有 raw 行的桶 ∪ 被 z 行覆盖的桶: 仅 z 覆盖(无 raw 行)的桶也到期
    产 hour 行(catch-up); 当前桶内的行程不提前封"""
    store = _store(tmp_path)
    store.append_z_run("global", H0, H0 + 3599, 5, 6)  # 上一小时桶: 仅 z 覆盖
    store.append_z_run("global", H1, H1 + 100, 7, 8)  # 当前桶: 不封
    assert store.seal_sweep(H1, now=H1 + 1, raw_window=24 * HOUR, rollup_window=30 * 24 * HOUR) == 1
    parsed = store.read_series("global")
    assert [h.hour_epoch for h in parsed.hours] == [H0]
    assert (parsed.hours[0].dl_avg, parsed.hours[0].dl_max, parsed.hours[0].dl_total) == (0, 0, 5)
    assert [z.end for z in parsed.zruns] == [H0 + 3599, H1 + 100]  # 行程行不受影响


def test_idle_24h_line_count_z_vs_zero_rows(tmp_path):
    """行数影响(plan §1.1 问题二): 全空闲 24h@30s —— v1 零行方案 2880 行零值 raw vs
    v2 行程行方案 144 行(600s 封口节奏, R1), 体积比 >10x(≈144 行量级断言)"""
    now = 1_800_000_000
    v1_lines = [HEADER_LINE, "key,global"] + [format_raw_row(now - 24 * HOUR + i * 30, 0, 0, 0, 0) for i in range(2880)]
    v1_text = "\n".join(v1_lines) + "\n"
    store = _store(tmp_path)
    zpath = store.series_path("global")
    start = now - 24 * HOUR
    for i in range(144):  # 86400s / 600s 封口节奏 = 144 条行程行
        store.append_z_run("global", start + i * 600, start + i * 600 + 599, 0, 0)
    z_text = _read_text(zpath)
    z_data_lines = len(z_text.splitlines()) - 2  # 除头行 + key 行
    assert z_data_lines == 144  # ≈144 行量级
    assert len(v1_lines) - 2 == 2880  # v1 同窗零行方案
    v1_size, z_size = len(v1_text.encode("utf-8")), len(z_text.encode("utf-8"))
    assert v1_size / z_size > 10  # raw 段空闲部分压缩显著(§6.2: 全文件口径另按真实工况实测)
    # z 方案经解析还原零坏行(144 条行程行全部合法)
    assert store.read_series("global").bad_lines == 0 and len(store.read_series("global").zruns) == 144
    assert max(z.end for z in store.read_series("global").zruns) <= now  # 跨度合法(ZRUN_MAX_SPAN_S 内)


def test_read_series_z_grid_expansion_end_to_end(tmp_path):
    """端到端打通(P3, plan 26-10-04-0721 §04.1): append_point 活跃段 + append_z_run 空闲段
    真实落盘 -> read_series -> grid 覆盖展开 —— 空闲段 0 平线 + totals 空闲 delta=0 链不断"""
    store = _store(tmp_path)
    base = 1_800_000_000 - 1200  # 对齐 30s 栅格的桶起点(1_800_000_000 恰为 30 的公倍数)
    store.append_point("global", base + 5, 100, 50, 1000, 500)  # 活跃桶 base
    store.append_z_run("global", base + 30, base + 300, 1000, 500)  # 空闲 270s -> 桶 base+30..base+300
    parsed = store.read_series("global")
    assert parsed.bad_lines == 0 and len(parsed.zruns) == 1  # 落盘 -> 解析 roundtrip 无损
    g = build_grid("30m", base + 600, 30.0)  # 30m 窗, t1 = base+600, 桶宽 30s
    obs = series_bucket_obs(parsed, g)
    assert obs[base] == BucketObs(100, 50, 1000, 500)  # 活跃桶(raw)
    for k in range(1, 11):  # z 覆盖桶 (0,0) + 行程快照
        assert obs[base + 30 * k] == BucketObs(0, 0, 1000, 500), k
    pts = rate_points(obs, g)
    assert pts[g.buckets.index(base + 150)] == {"t": base + 150, "dl": 0, "up": 0}  # 空闲 0 平线
    totals = series_totals_points(obs, g)
    assert totals[g.buckets.index(base)] == {"t": base, "dl": None, "up": None}  # 窗首基线缺失
    for k in range(1, 11):  # 空闲段 delta=0, 链不断
        assert totals[g.buckets.index(base + 30 * k)] == {"t": base + 30 * k, "dl": 0, "up": 0}, k
