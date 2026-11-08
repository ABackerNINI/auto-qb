"""test_traffic_store_paths 测试计划: qB 口径流量 v4 存储层(plan 26-10-05-2200 §01-§05; v1/v2/v3 退役面已随各代删除)

## 测试计划(每个测试函数一条)
handler 接线(S2a, v4 写侧):
- test_empty_data_dir_persists_nothing: data_dir 为空(防御, 真实配置恒非空) -> 零文件零目录(CWD 无泄漏)

v4 纯函数区(B1 立并于批 2 接线, plan 26-10-05-2200 §01):
- test_v4_paths_dates_and_window: 按天目录与路径解析(§06.2; 尾换行键/日期串拒收, issue 26-11-08-0045/1923)

v4 写侧存储(S2a/S2b, TrafficV4Store):
- test_v4_store_series_has_data_gate: 数据门(目录存在且含 >=1 个 .dat)
- test_v4_store_series_keys_and_day_dates: 恢复入口(系列键扫描/日期补算窗过滤/read_day)
- test_v4_store_evict_expired_series: 系列按龄淘汰(整目录; 龄期由文件名日期算)

v4 读侧解析缓存(S3a/S3b, V4DayCache):
- test_v4_day_cache_hit_and_invalidate: mtime+size 键控命中与两向失效; 缺失哨兵
- test_v4_day_cache_window_reads_only_involved_files: 24h 窗只开 2 个日期文件(open 计数断言)
- test_v4_day_cache_budget_lru: 字节预算 LRU
- test_v4_agg_cache_hit_and_invalidate: agg 缓存命中/失效/OSError 上抛不落缓存

体量实测(plan 26-10-04-1957 §09.1 口径沿用到 v4):

v4 活尾快照(S6 验收):

v4 定约专测(B1 用例, 批 2 回归):

P1-T1.2 守卫与容错簇(计划 26-10-20-2101, 覆盖率缺口清偿):
- test_v4_store_data_dir_property_and_has_data_edges: data_dir 只读出口; series_has_data 三档
  边界(只有非 .dat 文件遍历到底 / listdir OSError 保守 False / 无目录)
- test_v4_store_evict_skips_missing_root_and_foreign_entries: 无 torrents/ 根目录零操作;
  目录内非 infohash 名与普通文件跳过(不删不报)
- test_v4_agg_cache_entry_lru_bounded: agg 缓存条目数上界 LRU —— 第 N+1 个系列进来逐出最久
  未用条目, 被逐出者再读重解析(不冒充命中)
- test_v4_write_text_payload_cleanup_paths: 整文件重写失败路径的 tmp 清理 —— PermissionError
  退避耗尽放弃(tmp 已不在 / 删 tmp 自身抛 OSError 被吞), 非 PermissionError 异常清理后原样
  上抛(原文件完好)

mut-core W4 S5 定向补测(变异审计确认真洞守阵, 2026-10-31; 红验 tmp-analysis/redverify-s5-w4.py):
- test_v4_write_text_payload_tmp_same_directory: wtp_1/9/12 —— 原子重写 tmp 落目标目录
  (mkstemp dir 实参恒 == 目标目录, 防跨文件系统 EXDEV)
- test_v4_write_text_payload_permission_backoff_real_sleep: wtp_49(+wtp_42/43)—— PermissionError
  退避真 sleep(REWRITE_BACKOFF_S)x3 后放弃返 False; 永不退出形态经红验 harness 超时判红
- test_v4_store_evict_hash_named_file_and_aged_after_junk: evict_17/22 —— torrents/ 下 hash 名
  普通文件跳过不炸; 排序在前的杂物项不阻断本轮, 其后到龄系列照常淘汰

mut-core W4 S6 定向补测(2026-11-02, issue 26-10-31-1539 两件清偿; 红验 tmp-analysis/redverify-s6-w4.py):
- test_v4_one_byte_read_and_append_semantics: _read_parse_6/_ensure_6 —— 1 字节文件(仅外部损坏
  可造)读侧照常解析记坏(不冒充空文件 None), 写侧只补换行不重出头行/key 行
- test_v4_read_agg_empty_default_exact_fields: sra_14/15/23 + cache_agg_29/36/37 —— 缺失
  agg.dat 空哨兵全字段精确(key=None/空元组/bad_lines/data_lines=0), store 与缓存两层同钉
- test_v4_store_series_keys_skips_hash_named_plain_file: skeys_24 —— torrents/ 下 hash 名普通
  文件不得当系列目录列出
- test_v4_day_cache_budget_exact_fit_and_evict_to_one: cache_day_36/33 —— 驻留总量恰等 budget
  不逐出(严格大于才逐), 超预算逐到只剩最新一条
- test_v4_store_evict_rmtree_failure_continues_remaining: evict_37 —— 淘汰删除失败 continue
  不 break, 排序在后的到龄系列照常淘汰
(width_7/cache_agg_28 经红验已被既有守阵覆盖, 不另补测 —— 见 issue 26-10-31-1539 状态日志)
- test_v4_evict_and_rewrite_failure_warning_message_content: evict_36 + wtp_46 —— 淘汰删除失败
  与裁剪重写放弃的 WARNING 带语义文案与对象标识
(_wblp_20 判等价变异: 两解析结果型恒带 torn_tail 字段, getattr 默认值不可达 —— 见 issue 状态日志)

线程/时钟纪律: 本文件不再经 stdlib time 名 patch(S3 monkeypatch 收敛)—— 裁剪重写的
PermissionError 退避(REWRITE_BACKOFF_S=0.05s x 3)让真实发生, 耗时毫秒级可接受; 文件一律
落在 tmp_path(test.* 已内置 TMPDIR, 不手工加前缀)。
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

from platform_tolerance import SLEEP_LOWER_MARGIN_S

import auto_qb.core.traffic_store as traffic_store_module

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
    _validate_date,
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
    _agg_row,
    _mgr,
    _read_text,
    _run_sample,
)


def test_empty_data_dir_persists_nothing(tmp_path, monkeypatch):
    """data_dir 为空(防御: 真实配置恒非空, loaders 默认 auto-qb-data) -> 零文件零目录零泄漏"""
    monkeypatch.chdir(tmp_path)  # CWD 钉到 tmp: 断言无相对路径泄漏
    mgr = _mgr(tmp_path, QbTraffic(enabled=True, sample_interval=30), data_dir=False)
    mgr.store.server_state = server_state()
    seed_store(mgr, [active_torrent()])
    mod = mgr.host.get("qb_traffic")
    mod.start(mgr.ctx, dry_run=False)
    _run_sample(mgr)
    assert mod.latest != {}
    assert sorted(str(p) for p in tmp_path.rglob("*")) == []


def test_v4_paths_dates_and_window(tmp_path):
    """按天目录与路径解析(§06.2): 系列 key <-> 目录双向 / 日期 <-> 文件名 / agg.dat
    路径 / 窗口 -> 涉及日期集合(跨月/跨年) / day_epoch/month_epoch 本地 00:00 /
    非法键与倒置窗口 fail-fast"""
    data_dir = str(tmp_path)
    root = os.path.join(data_dir, TRAFFIC_V4_DIR_NAME)
    assert v4_root_dir(data_dir) == root
    assert v4_series_dir(data_dir, "global") == os.path.join(root, "global")
    assert v4_series_dir(data_dir, "torrent:ABC123") == os.path.join(root, "torrents", "ABC123")
    assert v4_day_file_path(data_dir, "global", "2026-10-04") == os.path.join(root, "global", "2026-10-04.dat")
    assert v4_agg_file_path(data_dir, "torrent:ABC123") == os.path.join(root, "torrents", "ABC123", "agg.dat")
    # 反向: 相对目录 -> 系列键(两种分隔符都认); 非系列目录 None
    assert v4_rel_dir_to_key("global") == "global"
    assert v4_rel_dir_to_key("torrents/ABC123") == "torrent:ABC123"
    assert v4_rel_dir_to_key("torrents\\ABC123") == "torrent:ABC123"
    assert v4_rel_dir_to_key("torrents") is None and v4_rel_dir_to_key("other") is None
    assert v4_rel_dir_to_key("torrents/../evil") is None
    # 文件名 <-> 日期: 形状与非真实日期都拒收
    assert v4_day_file_date("2026-10-04.dat") == "2026-10-04"
    assert v4_day_file_date("agg.dat") is None
    assert v4_day_file_date("2026-10-4.dat") is None and v4_day_file_date("2026-13-01.dat") is None
    assert v4_day_file_date("x.corrupt") is None
    # 本地 00:00 口径(day_epoch/month_epoch)
    day0 = int(datetime(2026, 10, 4).timestamp())
    assert v4_date_str_epoch("2026-10-04") == day0
    assert v4_epoch_date_str(day0) == "2026-10-04"
    assert v4_day_epoch(day0 + 3600) == day0
    assert v4_month_epoch(day0) == int(datetime(2026, 10, 1).timestamp())
    # 窗口 -> 日期集合: 跨日/跨年含两端所在日; 单日窗口
    assert v4_window_dates(day0 - 3600, day0 + 3600) == frozenset({"2026-10-03", "2026-10-04"})
    ny = int(datetime(2027, 1, 1).timestamp())
    assert v4_window_dates(ny - 3600, ny + 3600) == frozenset({"2026-12-31", "2027-01-01"})
    assert v4_window_dates(day0, day0) == frozenset({"2026-10-04"})
    # 跨月窗口(月末日 23:00 -> 次月 1 日 01:00)
    month_end = int(datetime(2026, 9, 30).timestamp())
    assert v4_window_dates(month_end - 3600,
                           month_end + 25 * 3600) == frozenset({"2026-09-29", "2026-09-30", "2026-10-01"})
    # fail-fast: 非法键 / 非法日期串 / 倒置窗口
    with pytest.raises(ValueError):
        v4_series_dir(data_dir, "torrent:../evil")
    with pytest.raises(ValueError):
        v4_series_dir(data_dir, "weird")
    # issue 26-11-08-0045: Python 的 $ 允许串尾恰一个换行, re.match 下 "ABC\n" 放行;
    # 消费端改 fullmatch 后尾随换行与空哈希一律拒收(合法哈希仍放行)
    with pytest.raises(ValueError):
        v4_series_dir(data_dir, "torrent:ABC\n")
    with pytest.raises(ValueError):
        v4_series_dir(data_dir, "torrent:")
    assert v4_rel_dir_to_key("torrents/ABC\n") is None
    # issue 26-11-08-1923: _V4_DATE_RE 同族缺口 —— 尾换行日期串拒收(消费端 fullmatch),
    # 合法日期串仍放行; _validate_date 的 ValueError 须出自形状闸门(非法日期串文案),
    # 不是放行后才由 strptime 兜底的另一种 ValueError
    assert v4_day_file_date("2026-10-04\n.dat") is None
    with pytest.raises(ValueError, match="非法日期串"):
        _validate_date("2026-10-04\n")
    with pytest.raises(ValueError):
        v4_day_file_path(data_dir, "global", "2026-13-01")
    with pytest.raises(ValueError):
        v4_date_str_epoch("2026-10-4")
    with pytest.raises(ValueError):
        v4_window_dates(day0, day0 - 1)


def test_v4_store_series_has_data_gate(tmp_path):
    """series_has_data(数据门, §3.2): 目录缺失/空目录 -> False; 有天文件或 agg.dat
    (同为 .dat 后缀) -> True; 非法系列键 fail-fast"""
    st = TrafficV4Store(str(tmp_path))
    assert st.series_has_data("torrent:ABC") is False  # 目录缺失
    os.makedirs(v4_series_dir(str(tmp_path), "torrent:ABC"))
    assert st.series_has_data("torrent:ABC") is False  # 目录空
    write_dat_lines(
        v4_day_file_path(str(tmp_path), "torrent:ABC", v4_epoch_date_str(H1)), [HEADER_LINE_V4, "key,torrent:ABC"]
    )
    assert st.series_has_data("torrent:ABC") is True  # 有天文件
    os.makedirs(v4_series_dir(str(tmp_path), "torrent:DEF"))
    (tmp_path / TRAFFIC_V4_DIR_NAME / "torrents" / "DEF" / "agg.dat").write_text("", encoding="utf-8")
    assert st.series_has_data("torrent:DEF") is True  # 仅 agg.dat 亦计入(.dat 后缀)
    with pytest.raises(ValueError):
        st.series_has_data("torrent:bad/key")  # 路径分隔符不进文件名


def test_v4_store_series_keys_and_day_dates(tmp_path):
    """series_keys/series_day_dates/read_day(§04.3 恢复入口): global + torrents/<h> 全列出
    (非 infohash 目录跳过); 天文件日期按补算窗口过滤(min_epoch 边界含, 升序), agg.dat 等
    非日期杂物跳过; 目录缺失 = 空表; 非法日期串 fail-fast(路径层校验)"""
    st = TrafficV4Store(str(tmp_path))
    assert st.series_keys() == []  # 根目录缺失
    d_old, d_new = "2026-01-01", "2026-03-15"
    for key in ("global", "torrent:ABC"):
        for d in (d_old, d_new):
            write_dat_lines(st.series_day_path(key, d), [HEADER_LINE_V4, f"key,{key}"])
        write_dat_lines(v4_agg_file_path(str(tmp_path), key), [HEADER_LINE_V4, f"key,{key}"])
    os.makedirs(os.path.join(v4_root_dir(str(tmp_path)), "torrents", "NOT!HASH"))  # 非 infohash 目录: 跳过
    assert st.series_keys() == ["global", "torrent:ABC"]
    min_epoch = v4_date_str_epoch("2026-03-01")
    assert st.series_day_dates("torrent:ABC", min_epoch) == (d_new, )  # 窗外天文件不进补算
    assert st.series_day_dates("torrent:ABC", v4_date_str_epoch(d_old)) == (d_old, d_new)  # 边界含(升序)
    assert st.series_day_dates("torrent:NOPE", 0) == ()  # 目录缺失
    assert st.read_day("torrent:ABC", d_new) is not None and st.read_day("torrent:ABC", "2026-03-16") is None
    with pytest.raises(ValueError):
        st.read_day("torrent:ABC", "2026-99-01")  # 非法日期串: 路径层 fail-fast


def test_v4_write_text_payload_cleanup_paths(tmp_path, monkeypatch):
    """整文件重写(§04.5 唯一原子重写点)失败路径的 tmp 清理: PermissionError 退避耗尽放弃
    (tmp 已被上一轮删掉时不再删 / 删 tmp 自身抛 OSError 被吞不掩盖主因); 非 PermissionError
    异常清理 tmp 后原样上抛 —— 三条路径下原文件都完好(数据无损)"""
    target = tmp_path / "agg.dat"
    target.write_text("old\n", encoding="utf-8")
    real_remove = os.remove  # 打桩前捕获(桩内不能再走被替换的 os.remove)

    # !不桩 sleep(S3 收敛): 退避真实发生(3 x 0.05s x 2 次失败调用), 顺带覆盖真退避面

    def _always_locked(src, dst):
        raise PermissionError(13, "locked")

    def _remove_locked(p):
        raise OSError(13, "locked")

    # ① PermissionError + 删 tmp 自身抛 OSError(被吞): 退避重试耗尽 -> 放弃, 原文件完好
    monkeypatch.setattr("auto_qb.core.traffic_store.os.replace", _always_locked)
    monkeypatch.setattr("auto_qb.core.traffic_store.os.remove", _remove_locked)
    assert traffic_store_module._write_text_payload(str(target), "new\n") is False
    assert target.read_text(encoding="utf-8") == "old\n"
    # ② PermissionError + tmp 已不在(上一轮删过): 跳过删除照常退避, 结果同上
    real_exists = os.path.exists
    monkeypatch.setattr(
        "auto_qb.core.traffic_store.os.path.exists",
        lambda p: False if str(p).endswith(".tmp") else real_exists(p),
    )
    assert traffic_store_module._write_text_payload(str(target), "new\n") is False
    assert target.read_text(encoding="utf-8") == "old\n"
    monkeypatch.undo()
    for leaked in tmp_path.glob("*.tmp"):  # ①② 故意留下的 tmp 残骸(删除被拦/被跳过的路径)
        leaked.unlink()

    # ③ 非 PermissionError 异常: 清理 tmp 后原样上抛(不静默吞掉真故障)
    def _boom(src, dst):
        raise RuntimeError("disk on fire")

    monkeypatch.setattr("auto_qb.core.traffic_store.os.replace", _boom)
    with pytest.raises(RuntimeError, match="disk on fire"):
        traffic_store_module._write_text_payload(str(target), "new\n")
    assert target.read_text(encoding="utf-8") == "old\n"
    assert [p.name for p in tmp_path.iterdir()] == ["agg.dat"]  # tmp 已清理(不留残骸)
    # ④ 异常路径下删 tmp 自身失败: OSError 被吞不掩盖主因, 主因照常上抛
    monkeypatch.setattr("auto_qb.core.traffic_store.os.remove", _remove_locked)
    with pytest.raises(RuntimeError, match="disk on fire"):
        traffic_store_module._write_text_payload(str(target), "new\n")
    assert target.read_text(encoding="utf-8") == "old\n"
    monkeypatch.setattr("auto_qb.core.traffic_store.os.remove", real_remove)
    for leaked in tmp_path.glob("*.tmp"):
        leaked.unlink()
    # ⑤ 异常路径下 tmp 已不在(前一轮删过): 跳过删除直接上抛
    monkeypatch.setattr(
        "auto_qb.core.traffic_store.os.path.exists",
        lambda p: False if str(p).endswith(".tmp") else real_exists(p),
    )
    with pytest.raises(RuntimeError, match="disk on fire"):
        traffic_store_module._write_text_payload(str(target), "new\n")
    assert target.read_text(encoding="utf-8") == "old\n"


def test_v4_store_evict_expired_series(tmp_path, monkeypatch):
    """evict_expired_series(§04.5 新口径): 系列最新天文件日期距 now 超过 rollup_window
    -> 整目录删除(天文件 + agg.dat, 龄期由文件名日期直接算); 边界(恰 window)不动;
    无天文件的目录保守跳过; 全局系列结构性豁免; 删除失败(读侧竞态)保留下轮重试且
    不进返回表"""
    st = TrafficV4Store(str(tmp_path))
    window = 30 * 86400.0
    edge_midnight = v4_date_str_epoch("2026-03-15")
    now = edge_midnight + window  # now 恰在窗口边界上: 2026-03-15 的 00:00 距 now 恰 = window(边界含, 保留)
    old_d = v4_epoch_date_str(now - 40 * 86400)
    new_d = "2026-03-16"
    # OLD: 超龄(天文件 + agg.dat 同删); EDGE: 恰压线保留; NEW: 新鲜; AGGONLY: 无天文件保守跳过
    for key, d in (("torrent:OLD", old_d), ("torrent:EDGE", "2026-03-15"), ("torrent:NEW", new_d)):
        write_dat_lines(st.series_day_path(key, d), [HEADER_LINE_V4, f"key,{key}"])
    write_dat_lines(v4_agg_file_path(str(tmp_path), "torrent:OLD"), [HEADER_LINE_V4, "key,torrent:OLD"])
    os.makedirs(v4_series_dir(str(tmp_path), "torrent:AGGONLY"))
    write_dat_lines(v4_agg_file_path(str(tmp_path), "torrent:AGGONLY"), [HEADER_LINE_V4, "key,torrent:AGGONLY"])
    write_dat_lines(st.series_day_path("global", old_d), [HEADER_LINE_V4, "key,global"])  # 全局豁免(结构性)
    evicted = st.evict_expired_series(now, window)
    assert evicted == ["torrent:OLD"]
    assert not os.path.exists(v4_series_dir(str(tmp_path), "torrent:OLD"))  # 整目录(天文件 + agg.dat)
    for key in ("torrent:EDGE", "torrent:NEW", "torrent:AGGONLY"):
        assert os.path.exists(v4_series_dir(str(tmp_path), key))
    assert os.path.exists(v4_series_dir(str(tmp_path), "global"))
    # 删除失败重试: 重建 OLD(首轮已被删) -> rmtree 抛错 -> 目录保留且不进返回表 -> 下轮重试成功
    write_dat_lines(st.series_day_path("torrent:OLD", old_d), [HEADER_LINE_V4, "key,torrent:OLD"])
    write_dat_lines(v4_agg_file_path(str(tmp_path), "torrent:OLD"), [HEADER_LINE_V4, "key,torrent:OLD"])

    def _boom(path):
        raise OSError(16, "locked")

    monkeypatch.setattr("auto_qb.core.traffic_store.shutil.rmtree", _boom)
    assert st.evict_expired_series(now, window) == []  # 删除失败: 不进返回表
    assert os.path.exists(v4_series_dir(str(tmp_path), "torrent:OLD"))  # 目录保留下轮重试
    monkeypatch.undo()
    assert st.evict_expired_series(now, window) == ["torrent:OLD"]  # 下轮重试成功


def test_v4_store_data_dir_property_and_has_data_edges(tmp_path, monkeypatch):
    """TrafficV4Store.data_dir 只读出口(采样模块算路径用); series_has_data 三档边界:
    目录存在但只有非 .dat 文件(遍历到底 -> False, 不因有文件就认有数据) / listdir 抛
    OSError(读侧竞态 -> 保守 False, 不冒泡打断采样轮) / 目录不存在 -> False(惰性零 IO)"""
    st = TrafficV4Store(str(tmp_path))
    assert st.data_dir == str(tmp_path)
    key = "torrent:ABC"
    assert st.series_has_data(key) is False  # 无目录
    series_dir = v4_series_dir(str(tmp_path), key)
    os.makedirs(series_dir)
    with open(os.path.join(series_dir, "notes.txt"), "w", encoding="utf-8") as f:
        f.write("x")
    assert st.series_has_data(key) is False  # 只有非 .dat 文件

    def _boom_listdir(path):
        raise OSError(5, "io error")

    monkeypatch.setattr("auto_qb.core.traffic_store.os.listdir", _boom_listdir)
    assert st.series_has_data(key) is False  # 读侧竞态保守 False
    monkeypatch.undo()
    write_dat_lines(os.path.join(series_dir, "2026-10-20.dat"), [HEADER_LINE_V4])
    assert st.series_has_data(key) is True


def test_v4_store_evict_skips_missing_root_and_foreign_entries(tmp_path):
    """evict_expired_series 结构边界: 无 torrents/ 根目录直接零操作(惰性); 目录内非 infohash
    名与同名普通文件跳过(既不删也不报, 防误删非本层产物)"""
    st = TrafficV4Store(str(tmp_path))
    assert st.evict_expired_series(1_800_000_000.0, 30 * 86400.0) == []
    torrents_dir = os.path.join(v4_root_dir(str(tmp_path)), TORRENTS_DIR_NAME)
    os.makedirs(torrents_dir)
    os.makedirs(os.path.join(torrents_dir, "not-a-hash"))
    write_dat_lines(os.path.join(torrents_dir, "notes.txt"), ["x"])
    assert st.evict_expired_series(1_800_000_000.0, 30 * 86400.0) == []
    assert os.path.isdir(os.path.join(torrents_dir, "not-a-hash"))
    assert os.path.exists(os.path.join(torrents_dir, "notes.txt"))


def _write_v4_day(data_dir, key, date, text):
    """测试助手: 直接落一个天文件(不经写侧批量纪律)"""
    path = v4_day_file_path(data_dir, key, date)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return path


def test_v4_day_cache_hit_and_invalidate(tmp_path, monkeypatch):
    """解析缓存命中与失效两向(验收): 未变命中(不重读不重解析, 同一解析对象) /
    追加变 size 失效 / 裁剪重写变小失效(mtime+size 键控, 两向都变); 缺失文件缓存 None
    (文件此后出现则 stat 键变化自然失效)"""
    data_dir = str(tmp_path)
    d = "2026-10-04"
    text = format_v4_day_text("global", (V4Block(1000, 30, 10, 20, (V4Sample(1, 1, 10, 20), )), ))
    _write_v4_day(data_dir, "global", d, text)
    calls = []
    real_parse = traffic_store_module.parse_v4_day_text

    def counting_parse(t):
        calls.append(1)
        return real_parse(t)

    monkeypatch.setattr(traffic_store_module, "parse_v4_day_text", counting_parse)
    cache = V4DayCache(data_dir)
    p1 = cache.read_day("global", d)
    assert p1 is not None and p1.key == "global" and calls == [1]
    assert cache.read_day("global", d) is p1  # 未变命中: 同一解析对象, 零重解析
    assert calls == [1]
    # 追加(size 变大) -> 失效重解析
    bigger = format_v4_day_text(
        "global", (V4Block(1000, 30, 10, 20, (V4Sample(1, 1, 10, 20), V4Sample(2, 2, 20, 40))), )
    )
    _write_v4_day(data_dir, "global", d, bigger)
    p2 = cache.read_day("global", d)
    assert calls == [1, 1] and len(p2.blocks[0].records) == 2
    # 裁剪重写(size 严格变小) -> 失效重解析
    _write_v4_day(data_dir, "global", d, text)
    p3 = cache.read_day("global", d)
    assert calls == [1, 1, 1] and len(p3.blocks[0].records) == 1
    assert cache.read_day("global", d) is p3  # 未变再命中
    assert calls == [1, 1, 1]
    # 缺失文件: None 且缓存(不再触发解析); 文件出现后 stat 键变化自然失效
    assert cache.read_day("global", "2026-10-03") is None
    assert cache.read_day("global", "2026-10-03") is None
    assert calls == [1, 1, 1]
    _write_v4_day(data_dir, "global", "2026-10-03", text)
    assert cache.read_day("global", "2026-10-03") is not None and calls == [1, 1, 1, 1]


def test_v4_day_cache_window_reads_only_involved_files(tmp_path, monkeypatch):
    """按天加载(验收: 24h 窗只开 2 个日期文件): read_window 按 v4_window_dates 只读涉及
    日期的天文件, 目录内其余天文件零 open; 返回按日期升序"""
    data_dir = str(tmp_path)
    block = V4Block(1000, 30, 10, 20, (V4Sample(1, 1, 10, 20), ))
    for date in ("2026-10-03", "2026-10-04", "2026-10-05"):
        _write_v4_day(data_dir, "global", date, format_v4_day_text("global", (block, )))
    opened = []
    real_open = builtins.open

    def counting_open(file, *a, **k):
        opened.append(os.fspath(file))
        return real_open(file, *a, **k)

    monkeypatch.setattr(builtins, "open", counting_open)
    cache = V4DayCache(data_dir)
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


def test_v4_day_cache_budget_lru(tmp_path, monkeypatch):
    """字节预算 LRU: 驻留条目文本总量 <= budget, 超出最久未用先逐出(至少保留最新一条);
    命中把条目移到队尾(刷新新近度)"""
    data_dir = str(tmp_path)
    block = V4Block(1000, 30, 10, 20, (V4Sample(1, 1, 10, 20), ))
    for date in ("2026-10-01", "2026-10-02", "2026-10-03"):
        _write_v4_day(data_dir, "global", date, format_v4_day_text("global", (block, )))
    calls = []
    real_parse = traffic_store_module.parse_v4_day_text

    def counting_parse(t):
        calls.append(1)
        return real_parse(t)

    monkeypatch.setattr(traffic_store_module, "parse_v4_day_text", counting_parse)
    cache = V4DayCache(data_dir, budget=1)  # 预算 1B: 每条都超, 恒只保最新读入的一条
    cache.read_day("global", "2026-10-01")
    cache.read_day("global", "2026-10-02")  # 10-01 被挤出
    cache.read_day("global", "2026-10-03")  # 10-02 被挤出
    assert calls == [1, 1, 1]
    cache.read_day("global", "2026-10-01")  # 10-01 已被逐出: 重解析(10-03 被挤出)
    assert calls == [1, 1, 1, 1]
    cache.read_day("global", "2026-10-01")  # 最新读入的条目保留: 命中
    assert calls == [1, 1, 1, 1]


def test_v4_agg_cache_hit_and_invalidate(tmp_path, monkeypatch):
    """agg.dat 解析缓存(S3b §05.2/§05.3, V4DayCache.read_agg): mtime_ns+size 键控与天文件
    同款纪律 —— 未变命中(同一解析对象) / 追加变 size 失效 / 裁剪重写变小失效; 缺失文件
    缓存空解析哨兵(文件此后出现自然失效); OSError(打开/读取失败)上抛不落缓存"""
    data_dir = str(tmp_path)
    rows = (AggRow("hour", 1000, 11, 21, 6, 9, 110, 210, 3500), AggRow("day", 0, 1, 2, 3, 4, 5, 6, 86400))
    cache = V4DayCache(data_dir)
    # 缺失文件: 空解析结果且缓存(哨兵); 文件出现后 stat 键变化自然失效
    empty = cache.read_agg("global")
    assert empty.key is None and empty.hours == () and empty.days == ()
    assert cache.read_agg("global") is empty
    store = TrafficV4Store(data_dir)
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
    agg_path = v4_agg_file_path(data_dir, "global")
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


def test_v4_agg_cache_entry_lru_bounded(tmp_path, monkeypatch):
    """agg 缓存条目数上界(S3b, V4_AGG_CACHE_MAX_ENTRIES): 第 N+1 个系列进来时逐出最久未用
    条目; 被逐出者再读重解析(不冒充命中), 命中刷新新近度 —— 缓存不随系列数无界增长"""
    data_dir = str(tmp_path)
    store = TrafficV4Store(data_dir)
    cache = V4DayCache(data_dir)
    keys = [f"torrent:{i:040x}" for i in range(V4_AGG_CACHE_MAX_ENTRIES + 1)]
    for k in keys:
        store.append_agg_rows(k, (_agg_row("hour", 1000), ))
    calls = []
    real_parse = traffic_store_module.parse_v4_agg_text

    def counting_parse(t):
        calls.append(1)
        return real_parse(t)

    monkeypatch.setattr(traffic_store_module, "parse_v4_agg_text", counting_parse)
    for k in keys:
        cache.read_agg(k)
    assert calls == [1] * len(keys)  # 逐个首次读: 全解析
    first = keys[0]  # 最早那条: 被第 N+1 个系列挤出
    cache.read_agg(first)
    assert len(calls) == len(keys) + 1  # 重解析(逐出后不冒充命中)
    cache.read_agg(first)
    assert len(calls) == len(keys) + 1  # 最新读入 -> 命中


def test_v4_write_text_payload_tmp_same_directory(tmp_path, monkeypatch):
    """裁剪原子重写的 tmp 同目录纪律(§04.5 —— 原子重写前提, 跨文件系统 os.replace EXDEV):
    mkstemp 的 dir 实参恒 == 目标文件所在目录(变异面: dir 缺省 None -> 落系统 TMP)"""
    target = tmp_path / "sub" / "agg.dat"
    target.parent.mkdir(parents=True)
    target.write_text("old\n", encoding="utf-8")
    seen = {}
    real_mkstemp = tempfile.mkstemp

    def spy_mkstemp(*args, **kwargs):
        seen["dir"] = kwargs.get("dir")
        return real_mkstemp(*args, **kwargs)

    monkeypatch.setattr("tempfile.mkstemp", spy_mkstemp)
    assert traffic_store_module._write_text_payload(str(target), "new\n") is True
    assert seen["dir"] == str(target.parent)
    assert target.read_text(encoding="utf-8") == "new\n"
    assert [p.name for p in target.parent.iterdir()] == ["agg.dat"]  # tmp 已原子替换走


def test_v4_write_text_payload_permission_backoff_real_sleep(tmp_path, monkeypatch):
    """PermissionError 退避重试(Windows 读侧竞态): 全文件唯一**不桩 sleep** 的退避用例 ——
    退避真调用 time.sleep(REWRITE_BACKOFF_S) 且重试 REWRITE_RETRIES 次后放弃返 False(原文件完好)。
    变异面: 退避被改成 sleep(None) 时 TypeError 上抛(调用方按 OSError 口径接不住);
    重试计数器被改成永不退出时本用例挂起 —— 由红验 harness 超时判红(与 mutmut timeout 同口径)。
    S3 收敛裁决(2026-11-05): 旧形态经「局部别名 real_sleep = time.sleep」计数, 是裸睡守阵的
    口径盲区; 现改用**真实经过时间下界**验证退避真发生(Windows 睡眠按 15.6ms 刻度可提前
    约 3 刻度, 3 次合计下界留 20ms 余量), 不再引入任何 time 名寻址, 守阵盲区随之消失
    (无需白名单条目)。
    """
    target = tmp_path / "agg.dat"
    target.write_text("old\n", encoding="utf-8")

    def always_locked(src, dst):
        raise PermissionError(13, "locked")

    monkeypatch.setattr("auto_qb.core.traffic_store.os.replace", always_locked)
    start = time.monotonic()
    assert traffic_store_module._write_text_payload(str(target), "new\n") is False
    elapsed = time.monotonic() - start
    # 首试失败后真退避 3 次: 总耗时 >= 3 x REWRITE_BACKOFF_S(下界余量 = 平台刻度容差单点; 空转退避当场红)
    assert elapsed >= REWRITE_RETRIES * REWRITE_BACKOFF_S - SLEEP_LOWER_MARGIN_S, elapsed
    assert target.read_text(encoding="utf-8") == "old\n"


def test_v4_store_evict_hash_named_file_and_aged_after_junk(tmp_path):
    """淘汰轮结构边界(hash 名形态): torrents/ 下 infohash 形状的普通文件跳过不炸(不当系列
    目录 listdir); 排序在前的杂物项不阻断本轮 —— 其后的到龄系列照常淘汰(continue 不退化成 break)"""
    st = TrafficV4Store(str(tmp_path))
    window = 30 * 86400.0
    now = 1_800_000_000.0
    old_d = v4_epoch_date_str(now - 40 * 86400)
    torrents_dir = os.path.join(v4_root_dir(str(tmp_path)), TORRENTS_DIR_NAME)
    os.makedirs(torrents_dir)
    hash_file = os.path.join(torrents_dir, "aaaa")  # infohash 形状的普通文件(排序在杂物与到龄系列之前)
    with open(hash_file, "w", encoding="utf-8") as f:
        f.write("x")
    os.makedirs(os.path.join(torrents_dir, "bad!name"))  # 非 infohash 杂物目录
    write_dat_lines(st.series_day_path("torrent:zzzz", old_d), [HEADER_LINE_V4, "key,torrent:zzzz"])
    assert st.evict_expired_series(now, window) == ["torrent:zzzz"]  # 杂物不阻断, 到龄系列照常淘汰
    assert not os.path.exists(st.series_day_path("torrent:zzzz", old_d))
    assert os.path.exists(hash_file)  # hash 名普通文件不删不炸
    assert os.path.isdir(os.path.join(torrents_dir, "bad!name"))


def test_v4_one_byte_read_and_append_semantics(tmp_path):
    """1 字节文件(仅外部损坏可造, W4 _read_parse_6/_ensure_6): 读侧不得当空文件 ——
    read_day/read_agg 照常解析(头行门闩整文件记坏, 不返 None/空哨兵); 写侧
    _ensure_file_prefix 不得当新文件 —— 撕裂尾只补一个换行, 不重出头行/key 行"""
    st = TrafficV4Store(str(tmp_path))
    day_path = st.series_day_path("global", "2026-10-31")
    os.makedirs(os.path.dirname(day_path), exist_ok=True)
    for p in (day_path, v4_agg_file_path(str(tmp_path), "global")):
        with open(p, "wb") as f:
            f.write(b"x")
    parsed_day = st.read_day("global", "2026-10-31")
    assert parsed_day is not None and parsed_day.bad_lines == 1 and parsed_day.data_lines == 1
    parsed_agg = st.read_agg("global")
    assert parsed_agg.bad_lines == 1 and parsed_agg.data_lines == 1
    # 写侧: 1 字节天文件上追加 -> 只补换行(头行/key 行不得重出)
    st.append_records("global", "2026-10-31", (1000, 30), (V4Sample(1, 1, 6, 9), ), block_base=(5, 8))
    raw = _read_text(day_path)
    assert raw.startswith("x\nB,1000,30,5,8\n") and HEADER_LINE_V4 not in raw


def test_v4_read_agg_empty_default_exact_fields(tmp_path):
    """read_agg 空哨兵全字段钉住(W4 sra_14/15/23 + cache_agg_29/36/37): 缺失 agg.dat 时
    store 层与缓存层空解析结果全字段精确 —— key=None, hours/days/months 空元组,
    bad_lines/data_lines = 0(坏行计数空默认不漂)"""
    st = TrafficV4Store(str(tmp_path))
    for empty in (st.read_agg("global"), V4DayCache(str(tmp_path)).read_agg("global")):
        assert empty.key is None
        assert empty.hours == () and empty.days == () and empty.months == ()
        assert empty.bad_lines == 0 and empty.data_lines == 0
        assert empty.torn_tail is False


def test_v4_store_series_keys_skips_hash_named_plain_file(tmp_path):
    """series_keys(W4 skeys_24): torrents/ 下 hash 名的普通文件(非目录)不得被当系列目录
    列出; hash 名目录照常列出"""
    st = TrafficV4Store(str(tmp_path))
    tdir = os.path.join(v4_root_dir(str(tmp_path)), TORRENTS_DIR_NAME)
    os.makedirs(tdir)
    with open(os.path.join(tdir, "HASHFILE1"), "w", encoding="utf-8") as f:
        f.write("junk")
    os.makedirs(os.path.join(tdir, "HASHDIR1"))
    assert st.series_keys() == ["torrent:HASHDIR1"]


def test_v4_day_cache_budget_exact_fit_and_evict_to_one(tmp_path, monkeypatch):
    """天文件字节预算两向边界(W4 cache_day_36/cache_day_33): 驻留总量恰等 budget 不逐出
    (严格大于才逐); 超预算逐出到只剩最新一条(len > 1 才逐, 最新读入者恒保留)"""
    data_dir = str(tmp_path)
    block = V4Block(1000, 30, 10, 20, (V4Sample(1, 1, 10, 20), ))
    paths = {}
    for date in ("2026-10-01", "2026-10-02"):
        paths[date] = _write_v4_day(data_dir, "global", date, format_v4_day_text("global", (block, )))
    size1 = os.path.getsize(paths["2026-10-01"])
    size2 = os.path.getsize(paths["2026-10-02"])
    calls = []
    real_parse = traffic_store_module.parse_v4_day_text

    def counting_parse(t):
        calls.append(1)
        return real_parse(t)

    monkeypatch.setattr(traffic_store_module, "parse_v4_day_text", counting_parse)
    # 恰等 budget: 两条都驻留, 重读命中不重解析
    cache = V4DayCache(data_dir, budget=size1 + size2)
    cache.read_day("global", "2026-10-01")
    cache.read_day("global", "2026-10-02")
    cache.read_day("global", "2026-10-01")
    assert calls == [1, 1], "驻留总量恰等 budget 不逐出(严格大于才逐)"
    # 差 1B 超预算: 逐出最久未用到只剩最新一条, 重读 10-01 重解析
    calls.clear()
    cache2 = V4DayCache(data_dir, budget=size1 + size2 - 1)
    cache2.read_day("global", "2026-10-01")
    cache2.read_day("global", "2026-10-02")  # 超预算: 10-01 被逐出
    cache2.read_day("global", "2026-10-01")  # 已被逐出: 重解析(10-02 被逐出)
    assert calls == [1, 1, 1], "超预算逐到只剩最新一条"


def test_v4_store_evict_rmtree_failure_continues_remaining(tmp_path, monkeypatch):
    """淘汰删除失败不阻断当轮后续(W4 evict_37): rmtree 抛 OSError 的系列保留下轮重试
    (不进返回表), 排序在后的到龄系列照常淘汰(continue 非 break)"""
    st = TrafficV4Store(str(tmp_path))
    window = 30 * 86400.0
    now = v4_date_str_epoch("2026-03-15") + window
    old_d = v4_epoch_date_str(now - 40 * 86400)
    for h in ("AAA", "BBB"):
        write_dat_lines(st.series_day_path(f"torrent:{h}", old_d), [HEADER_LINE_V4, f"key,torrent:{h}"])
    real_rmtree = traffic_store_module.shutil.rmtree

    def _flaky(path):
        if os.path.basename(path) == "AAA":
            raise OSError(16, "locked")
        return real_rmtree(path)

    monkeypatch.setattr("auto_qb.core.traffic_store.shutil.rmtree", _flaky)
    assert st.evict_expired_series(now, window) == ["torrent:BBB"]
    assert os.path.exists(v4_series_dir(str(tmp_path), "torrent:AAA"))  # 失败保留下轮重试
    assert not os.path.exists(v4_series_dir(str(tmp_path), "torrent:BBB"))  # 不阻断后续淘汰


def test_v4_evict_and_rewrite_failure_warning_message_content(tmp_path, caplog, monkeypatch):
    """失败告警消息内容(W4 evict_36 + wtp_46): 淘汰删除失败与裁剪重写放弃的 WARNING 须带
    语义文案与对象标识(非 None/空消息)"""
    st = TrafficV4Store(str(tmp_path))
    window = 30 * 86400.0
    now = v4_date_str_epoch("2026-03-15") + window
    old_d = v4_epoch_date_str(now - 40 * 86400)
    write_dat_lines(st.series_day_path("torrent:AAA", old_d), [HEADER_LINE_V4, "key,torrent:AAA"])

    def _boom_rmtree(path):
        raise OSError(16, "locked")

    monkeypatch.setattr("auto_qb.core.traffic_store.shutil.rmtree", _boom_rmtree)
    with caplog.at_level(logging.WARNING, logger="auto_qb.core.traffic_store"):
        assert st.evict_expired_series(now, window) == []
    evict_warns = [r.getMessage() for r in caplog.records if "淘汰删除失败" in r.getMessage()]
    assert len(evict_warns) == 1 and "AAA" in evict_warns[0]
    # 裁剪重写被占用退避耗尽: 放弃本轮告警含文案与文件名, 原文件完好
    caplog.clear()

    def _boom_replace(src, dst):  # 退避真实发生(S3 收敛后不桩 sleep, 3 x 0.05s)
        raise PermissionError(13, "locked")

    monkeypatch.setattr("auto_qb.core.traffic_store.os.replace", _boom_replace)
    target = tmp_path / "agg.dat"
    target.write_text("old\n", encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger="auto_qb.core.traffic_store"):
        assert traffic_store_module._write_text_payload(str(target), "new\n") is False
    wtp_warns = [r.getMessage() for r in caplog.records if "放弃本轮" in r.getMessage()]
    assert len(wtp_warns) == 1 and "agg.dat" in wtp_warns[0]
    assert target.read_text(encoding="utf-8") == "old\n"
