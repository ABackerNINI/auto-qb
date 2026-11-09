"""test_traffic_store_codec 测试计划: qB 口径流量 v4 存储层(plan 26-10-05-2200 §01-§05; v1/v2/v3 退役面已随各代删除)

## 测试计划(每个测试函数一条)
handler 接线(S2a, v4 写侧):
- test_all_persist_writes_on_caller_thread: 全部 v4 批量落盘(TrafficV4Store.append_records)写在主循环线程, 模块不建线程(黄金法则 5)

v4 纯函数区(B1 立并于批 2 接线, plan 26-10-05-2200 §01):
- test_v4_day_roundtrip_with_drift_rows: roundtrip —— 序列化->解析与原始内存块逐点相等(显式 dt 漂移行/z+n 游程/标称缺省行);
  delta 列 = 绝对值 - 块基线字面文本; dt 链槽位实测序列逐点相等 + obs/dt_s 形态逐项核对
- test_v4_amortized_run_chain_self_consistent: 均摊定位与链式自洽; 块首游程端点含
- test_v4_parse_bad_line_family_cursor_not_advanced: 坏行族逐项计坏(v1/v2/v3 旧头行整文件不匹配 —— R2 不设双读 /
  r 列数 {5,6} 之外 / dt_ms 非法族 / 负速率 / run_len<1 / interval<1 / 块头前数据行), 好行不受牵连且游标不推进
- test_v4_bad_line_ratio_warning_once_throttled: 守阵(26-10-06-0028 C-04, P-05)——坏行占比超阈(>=2 行且 >5%, 撕裂尾豁免)
  读侧 WARNING 一次(按文件节流); 正常文件零告警
- test_v4_no_equal_interval_drift_immunity: 纯等间隔路径不存在(证伪)
- test_v4_decimal_interval_roundtrip_and_bad_parse: 块头 interval_s 小数秒 —— B 行 1.5 roundtrip +
  标称槽位推进 1.5s + 解析侧非法族整行计坏; 整值形态不变
- test_v4_format_fail_fast_and_torn_tail: 序列化 fail-fast + 撕裂尾行豁免口径
- test_v4_parse_discipline_dual_parser_same_verdict: 同纪律夹具双 parser 同判(issue 26-10-29-1304 R07-T06
  解析纪律收敛 _parse_v4_text 单点的行为守阵)—— 空文本/头行缺失与旧头行(整文件坏含头行本身)/
  坏行族+空行注释跳/撕裂尾(末行坏才豁免)/完整末行无换行 五组夹具, day 与 agg 纪律面逐项同判
- test_v4_parse_skeleton_single_point: 静态守阵 —— 骨架行/行循环/驱动器接线在 traffic_store_codec.py
  各恰一处(_parse_v4_text 单点, 两解析器无行循环副本)

v4 写侧存储(S2a/S2b, TrafficV4Store):

v4 读侧解析缓存(S3a/S3b, V4DayCache):

体量实测(plan 26-10-04-1957 §09.1 口径沿用到 v4):
- test_v4_row_width_vs_legacy_layout_bytes: 体量对比 —— 同一构造采样序列按 v2 行型布局与 v4 行型
  序列化的实测字节对照(r 行 delta 列存块内增量; 空闲段游程压缩 >10x)

v4 活尾快照(S6 验收):

v4 定约专测(B1 用例, 批 2 回归):
- test_v4_b_row_dual_form_3col_5col: B 行 3/5 列二态(无基线块/基线块)格式与解析两侧 +
  基线缺一 fail-fast + interval_s 小数秒口径沿用 + n 行行型不变 + 二态同文件任意顺序并存
- test_v4_negative_delta_bad_row_non_propagating: 负 delta 判坏行(整行跳过、游标不推进)+
  坏行不传播(中段坏行后后续行 totals 复原仍精确, delta-vs-基线逐行独立)+ 序列化侧负
  delta fail-fast + 撕裂尾半行豁免口径沿用
- test_v4_z_end_pair_shapes_legacy_compat: 形态 D z 行末端对(plan 26-10-16-1509 §04)——
  新 6/7 列(末端对在 dt 之前)与旧 4/5 列同文件并存; 旧行末端 = None(向后兼容); raw 槽
  obs 仍为冻结列(末端对仅 agg 车道); 新列显式退化(末端 = 冻结)roundtrip
- test_v4_z_totals_ramp_endpoints_monotone_and_conservation: 摊配纯函数(形态 D)—— 端点精确
  (v_0 = S0, v_{n-1} = S1)/逐分量单调不减/区间累加严格守恒(取整余量归末端槽)/逐向独立/
  n = 1 与无末端与末端低于开启降档恒快照
- test_v4_no_baseline_block_n_only_guard: n-only 无基线块(3 列 B + 纯 n 合法, roundtrip);
  无基线块内 r/z 判坏行(解析守卫, 后续 n 照常收); 序列化侧同源守卫 fail-fast; n-only
  前缀块 -> 恢复传输基线块两块接续
- test_v4_header_latch_whole_file_mismatch: 头行 v4 门闩 —— v3/v1/v2 旧头行/缺失整文件
  不匹配(R2 不设双读); v4 常量字面值钉住

P1-T1.2 守卫与容错簇(计划 26-10-20-2101, 覆盖率缺口清偿):
- test_v4_parse_null_column_and_nn_int_guard: 数据列空文本 = None(null 列)与 r/z 列「空列」
  判坏的同一入口(_parse_int_field -> _parse_nn_int), 天文件/agg 两路各钉一行
- test_v4_block_gap_continuous_boundary: 跨块覆盖结算判定 —— 恰等 interval / 恰压 250ms 容差
  判连续, 超容差判真空, 病态重叠判连续(结算区间为空)
- test_v4_parse_tolerance_blank_comment_and_orphan_rows: 空行/注释行跳过不计坏、块头前数据行
  判坏(游标无锚点)、agg 头行不符整文件记坏、agg 坏行(非数值/空列)整行跳过不污染好行、
  agg 撕裂尾行豁免口径与天文件一致
- test_v4_z_row_requires_baseline_block: z 行须基线块(无基线块仅 n 游程合法)序列化 fail-fast

mut-core W4 S5 定向补测(变异审计确认真洞守阵, 2026-10-31; 红验 tmp-analysis/redverify-s5-w4.py):
- test_v4_parse_orphan_n_row_counts_bad_no_ghost_block: day_2 —— 块头前 n 行计坏且 blocks 空
  (无幽灵块; r/z 形态有既有守卫拦着, 唯 n 行可穿透)
- test_v4_read_replaces_invalid_utf8_bytes_as_bad_lines: _read_parse_10/14/19/20 —— 非 UTF-8
  字节在 read_agg/read_day 两入口记坏行不炸(errors="replace" 缺省纪律)
- test_v4_z_row_negative_delta_each_direction_fail_fast: z_row_33/34/36 —— z 行负 delta 逐向
  独立 fail-fast(dl/up 冻结列与末端对四列任一单列为负即拒)

mut-core W4 S6 定向补测(2026-11-02, issue 26-10-31-1539 两件清偿; 红验 tmp-analysis/redverify-s6-w4.py):
- test_v4_bad_line_warn_torn_exemption_and_gate_boundaries: _wbl_4/6/9/13/14 + _wblp_4/8/12/18/19
  —— 撕裂尾恰豁免 1 行(不多不少)/单行坏行不告(行数闸)/占比 <=5%(含恰等)不告
- test_v4_bad_line_warn_throttle_table_clear_boundary: _wbl_21/23/24 —— 节流表含本条恰 256 条
  不清空, 第 257 条触发整体清空(两向边界)
- test_v4_bad_line_warn_message_fields_and_source_identity: _wbl_26/27 + _wblp_1 —— 告警消息
  字段(文件标识/有效坏行数/占比)与按来源分槽各自告警不互吞

线程/时钟纪律: 需要确定时刻的用例经 monkeypatch 固定 time.time(测试进程内单线程, 恢复由
monkeypatch 保证); 文件一律落在 tmp_path(test.* 已内置 TMPDIR, 不手工加前缀)。
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

import auto_qb.core.traffic_store_codec as traffic_store_codec_module

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
    HOUR,
    _S2B_H0,
    _mgr,
    _v4_day_text,
)


def test_all_persist_writes_on_caller_thread(tmp_path, monkeypatch):
    """单写线程不变式: 全部 v4 批量落盘(TrafficV4Store.append_records)发生在调时钟线钩子
    的线程(= 主循环线程)内, 模块不建线程(黄金法则 5)"""
    mgr = _mgr(tmp_path, QbTraffic(enabled=True, sample_interval_multiplier=30))
    mgr.store.server_state = server_state()
    seed_store(mgr, [active_torrent()])
    mod = mgr.host.get("qb_traffic")
    mod.start(mgr.ctx, dry_run=False)
    mod._last_flush = time.time() - 601  # 预置过期: 本轮采样内 flush 驱动即触发
    seen = []
    real = TrafficV4Store.append_records

    def spy(self, key, date_str, header, records, block_base):
        seen.append((key, threading.get_ident()))
        return real(self, key, date_str, header, records, block_base)

    monkeypatch.setattr(TrafficV4Store, "append_records", spy)
    # 不量全局 active_count 快照: 同 xdist worker 上无关用例的线程启停会污染计数
    # (issue 26-11-04-0600: 全量并行 3==4 偶红, 方向是无关线程退出)。改 spy
    # Thread.start, 只看本同步窗口内是否真的启动了线程 —— 对无关线程启停免疫,
    # 且比快照强: 窗口内建线程又 join 掉的形态也逃不掉。
    started = []
    real_start = threading.Thread.start

    def spy_start(self, *args, **kwargs):
        started.append(self.name)
        return real_start(self, *args, **kwargs)

    monkeypatch.setattr(threading.Thread, "start", spy_start)
    mod.on_task_line(force=False)  # 宿主经任务线钩子调采样(首拍即采)
    assert {k for k, _ in seen} == {"global", "torrent:HASH123"}
    assert all(ident == threading.get_ident() for _, ident in seen)
    assert started == [], f"模块新建了线程: {started}"


def test_v4_amortized_run_chain_self_consistent():
    """均摊定位(§02.3): 非块首游程槽均摊 [锚点, 锚点+dt] 且末槽恰在游程实测终点;
    其后首 r 的 dt 以游程终点为基准(链式自洽); 块首游程端点含(首槽 = B.start);
    缺省游程按标称栅格"""
    # 非块首显式 z 游程: 锚点 1000, advance 90s -> 槽 1030/1060/1090(末槽 = 锚点+dt)
    b = V4Block(
        start_epoch=1000,
        interval_s=30,
        dl_base=1,
        up_base=1,
        records=(V4Sample(1, 1, 1, 1), V4ZeroRun(3, 5, 6, dt_ms=90000), V4Sample(2, 2, 2, 2, dt_ms=30000)),
    )
    slots = v4_block_slots(b)
    assert [s.ts for s in slots] == pytest.approx([1000.0, 1030.0, 1060.0, 1090.0, 1120.0], abs=1e-9)
    assert slots[1].ts == pytest.approx(1000.0 + 90.0 / 3, abs=1e-9)  # 首槽在锚点 + dt/len(非锚点)
    assert slots[3].ts == pytest.approx(1000.0 + 90.0, abs=1e-9)  # 末槽恰在游程实测终点
    # 其后首 r 的 dt 以游程终点(1090, 实测)为基准: dt_ms=30000 -> 1120, 链式自洽
    assert slots[4].ts == pytest.approx(1090.0 + 30.0, abs=1e-9)
    # 缺省 z 游程(非块首, 前置 r 行): 标称栅格(槽 = 锚点 + k x interval, k=1..len), 其后 r 标称接续
    b2 = V4Block(
        start_epoch=1000,
        interval_s=30,
        dl_base=1,
        up_base=1,
        records=(V4Sample(1, 1, 1, 1), V4ZeroRun(2, 5, 6), V4Sample(1, 1, 1, 1)),
    )
    assert [s.ts for s in v4_block_slots(b2)] == pytest.approx([1000.0, 1030.0, 1060.0, 1090.0], abs=1e-9)
    # 块首游程: 首槽 = B.start(端点含), 槽距 = dt/(len-1), 游标终点 = 末槽
    b3 = V4Block(
        start_epoch=5000,
        interval_s=30,
        dl_base=5,
        up_base=6,
        records=(V4ZeroRun(3, 5, 6, dt_ms=60000), V4Sample(1, 1, 1, 1, dt_ms=30000)),
    )
    slots3 = v4_block_slots(b3)
    assert [s.ts for s in slots3] == pytest.approx([5000.0, 5030.0, 5060.0, 5090.0], abs=1e-9)
    # 相邻游程(z -> n, R2 纪律): n 的 dt 含引导间隔(链上锚点 = 前游程终点), 槽均摊精确
    b4 = V4Block(
        start_epoch=1000,
        interval_s=30,
        dl_base=1,
        up_base=1,
        records=(V4Sample(1, 1, 1, 1), V4ZeroRun(2, 5, 6, dt_ms=60000), V4NullRun(2, dt_ms=61000)),
    )
    assert [s.ts for s in v4_block_slots(b4)] == pytest.approx([1000.0, 1030.0, 1060.0, 1090.5, 1121.0], abs=1e-9)


def test_v4_parse_bad_line_family_cursor_not_advanced():
    """v4 坏行族逐项计坏(§02.3 沿用): v1/v2/v3 旧头行整文件不匹配 / r 列数 {5,6} 之外 /
    dt_ms 非法族(0/负/超上界/非数值) / 负速率 / run_len<1 / interval<1 / 块头前数据行;
    好行不受牵连且游标不推进(坏行前后好行推算时刻与干净文件一致)"""
    good_head = [HEADER_LINE_V4, "key,global", "B,1000,30,5,8"]
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
        "z,2,1,1,-5,6",  # z 末端 delta 负(形态 D 免费校验)
        "z,2,1,1,5,6,0",  # z 7 列 dt_ms = 0
        "z,2,1,1,5,6,7,8",  # z 8 列(超形状)
        "n,0",  # n run_len < 1
        "n,2,1,1",  # n 4 列
        f"n,2,{DT_MS_MAX + 1}",  # n dt_ms 超上界
        "garbage",  # 未知行型
        "key,other",  # 重复 key 行
        "B,1000,0",  # interval_s < 1 -> 整行坏(不开新块)
    ]
    good_tail = ["r,2,2,2,2", "B,2000,60,3,4", "r,3,3,3,3,45000"]
    text = _v4_day_text(good_head + ["r,1,1,1,1"] + bad_lines + good_tail)
    parsed = parse_v4_day_text(text)
    assert parsed.key == "global" and parsed.bad_lines == len(bad_lines) and parsed.data_lines == 25
    # 坏行不落 records 且游标不推进: 块 1 = B(1000,30) + r@1000 + r@1030(坏 B 未开新块)
    assert len(parsed.blocks) == 2
    assert [len(b.records) for b in parsed.blocks] == [2, 1]
    assert [s.ts for s in v4_block_slots(parsed.blocks[0])] == pytest.approx([1000.0, 1030.0], abs=1e-9)
    assert [s.ts for s in v4_block_slots(parsed.blocks[1])] == pytest.approx([2000.0], abs=1e-9)
    # 干净文件对照: 同一批好行的推算时刻完全一致(坏行不影响游标链)
    clean = parse_v4_day_text(_v4_day_text(good_head + ["r,1,1,1,1"] + good_tail))
    assert [s.ts for b in clean.blocks
            for s in v4_block_slots(b)] == [s.ts for b in parsed.blocks for s in v4_block_slots(b)]
    # dt_ms 恰好上界合法
    ok = parse_v4_day_text(_v4_day_text(good_head + [f"r,1,1,1,1,{DT_MS_MAX}"]))
    assert ok.bad_lines == 0 and ok.blocks[0].records[0].dt_ms == DT_MS_MAX
    # 旧版头行(含 v1/v2/v3)整文件不匹配格式 —— R2 换代, v4 读侧不设双读
    for head in ("# auto-qb qb-traffic v1", "# auto-qb qb-traffic v2", "key,global"):
        old = parse_v4_day_text(_v4_day_text([head, "key,global", "B,1000,30", "r,1,1,1,1"]))
        assert old.key is None and old.blocks == () and old.bad_lines == 4 and old.data_lines == 4


def test_v4_bad_line_ratio_warning_once_throttled(tmp_path, caplog, monkeypatch):
    """守阵(26-10-06-0028 C-04, P-05 最小消费方): 坏行占比超阈(>=2 行且 >5%, 撕裂尾豁免)
    读侧 WARNING 一次(按文件节流); 正常文件零告警; 超阈单行/撕裂尾不告"""
    monkeypatch.setattr(traffic_store_module, "_bad_line_warn_ts", {})
    store = TrafficV4Store(str(tmp_path))
    # 头行 + key + B + 34 好行 = 37 行, + 2 坏行 = 38 受检行(头行不计, 2/38 ≈ 5.3% > 5%)
    good = [HEADER_LINE_V4, "key,global", "B,1000,30,5,8"] + ["r,1,1,1,1"] * 34

    def _write(date_str: str, text: str) -> str:
        path = v4_day_file_path(str(tmp_path), "global", date_str)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    _write("2026-10-06", _v4_day_text(good + ["garbage1", "garbage2"]))
    with caplog.at_level(logging.WARNING, logger="auto_qb.core.traffic_store"):
        parsed = store.read_day("global", "2026-10-06")
    assert parsed.bad_lines == 2 and parsed.data_lines == 38
    assert len([r for r in caplog.records if "坏行" in r.getMessage()]) == 1, "超阈告警恰好一次"
    # 节流: 同文件再读(缓存命中路径)不重复告警
    caplog.clear()
    with caplog.at_level(logging.WARNING, logger="auto_qb.core.traffic_store"):
        store.read_day("global", "2026-10-06")
    assert not [r for r in caplog.records if "坏行" in r.getMessage()]
    # 节流表上界保险: 塞满 256+ 条后告警路径整体重置不崩(clear 分支)
    full = {f"f{i}": 0.0 for i in range(300)}
    monkeypatch.setattr(traffic_store_module, "_bad_line_warn_ts", full)
    caplog.clear()
    with caplog.at_level(logging.WARNING, logger="auto_qb.core.traffic_store"):
        store.read_day("global", "2026-10-06")
    assert len([r for r in caplog.records if "坏行" in r.getMessage()]) == 1
    assert len(traffic_store_module._bad_line_warn_ts) <= 256, "上界保险: 节流表整体重置"
    # 正常文件零告警
    caplog.clear()
    _write("2026-10-05", _v4_day_text(good))
    with caplog.at_level(logging.WARNING, logger="auto_qb.core.traffic_store"):
        store.read_day("global", "2026-10-05")
    assert not [r for r in caplog.records if "坏行" in r.getMessage()]
    # 撕裂尾豁免: 尾部半行(1 坏行)豁免占比口径 → 有效坏行 0 < 2, 不告警
    caplog.clear()
    _write("2026-10-04", _v4_day_text(good + ["garbage"])[:-1])
    with caplog.at_level(logging.WARNING, logger="auto_qb.core.traffic_store"):
        torn = store.read_day("global", "2026-10-04")
    assert torn.bad_lines == 1 and torn.torn_tail is True
    assert not [r for r in caplog.records if "坏行" in r.getMessage()], "撕裂尾豁免后不超阈"


def test_v4_decimal_interval_roundtrip_and_bad_parse():
    """块头 interval_s 小数秒(2026-10-05 放宽, 修复 1.5/1.5 被整数秒口径静默抬到 2s):
    B 行 1.5 roundtrip(interval_s 还原 + 标称槽位推进 1.5s); 解析侧非法族(0.5/非数值/
    非有限)整行计坏不开新块; 整秒历史文件形态不受影响(整值序列化不带小数点)"""
    recs = (V4Sample(1, 2, 3, 4), V4Sample(5, 6, 7, 8))
    parsed = parse_v4_day_text(format_v4_day_text("global", (V4Block(1000, 1.5, 3, 4, recs), )))
    assert parsed.bad_lines == 0
    (block, ) = parsed.blocks
    assert block.start_epoch == 1000 and block.interval_s == 1.5
    # 标称槽位推进 1.5s(缺省 dt 链): 槽 1000, 1001.5
    assert [s.ts for s in v4_block_slots(block)] == pytest.approx([1000.0, 1001.5], abs=1e-9)
    # 解析侧非法族: 整行坏、不开新块、游标不推进
    good_head = [HEADER_LINE_V4, "key,global", "B,1000,30,5,8"]
    bad_b = ["B,1000,0.5", "B,1000,abc", "B,1000,nan", "B,1000,inf", "B,1000,1.5.5"]
    out = parse_v4_day_text(_v4_day_text(good_head + ["r,1,1,1,1"] + bad_b + ["r,2,2,2,2"]))
    assert out.bad_lines == len(bad_b)
    assert len(out.blocks) == 1 and len(out.blocks[0].records) == 2


def test_v4_no_equal_interval_drift_immunity():
    """纯等间隔路径不存在(§02.3): 构造 d̄>0 全显式 dt 序列 —— dt 链逐点等于实测,
    等间隔推算(start + i x interval)漂移远超 tol(证无累积误差)"""
    interval, n = 30, 20
    actual = [2000.0 + i * 30.4 for i in range(n)]
    recs = tuple(V4Sample(i, i, i, i, dt_ms=None if i == 0 else 30400) for i in range(n))
    parsed = parse_v4_day_text(format_v4_day_text("global", (V4Block(2000, interval, 0, 0, recs), )))
    slots = v4_block_slots(parsed.blocks[0])
    assert [s.ts for s in slots] == pytest.approx(actual, abs=1e-6)  # dt 链逐点相等
    equal_interval = [2000.0 + i * interval for i in range(n)]
    max_drift = max(abs(a - e) for a, e in zip(actual, equal_interval))
    assert max_drift > 1.0  # 等间隔推算在块尾漂移 > 1s(远超 tol=250ms) —— 该路径不存在于实现
    assert DRIFT_TOL_MS == 250  # D2: 模块常量非配置键


def test_v4_format_fail_fast_and_torn_tail():
    """写侧序列化纪律: dt_ms 非法(0/负/超上界/bool)与 interval_s 非法 fail-fast;
    解析侧撕裂尾半行豁免口径(完整末行无换行不算 torn, 残缺末行记 torn_tail 且坏行计数)"""
    assert format_v4_r_row(V4Sample(1, 2, 3, 4, dt_ms=DT_MS_MAX), 0, 0) == f"r,1,2,3,4,{DT_MS_MAX}"  # 上界合法
    assert format_v4_n_row(V4NullRun(2)) == "n,2" and format_v4_n_row(V4NullRun(2, dt_ms=5000)) == "n,2,5000"
    assert format_v4_z_row(V4ZeroRun(2, 3, 4), 0, 0) == "z,2,3,4,3,4"  # delta = 绝对值 - 基线; 末端缺省写冻结列同值(显式退化)
    assert format_v4_z_row(V4ZeroRun(2, 3, 4, dl_total_end=9, up_total_end=10), 0, 0) == "z,2,3,4,9,10"  # 形态 D 末端对
    assert format_v4_z_row(V4ZeroRun(2, 3, 4, dt_ms=9000), 0, 0) == "z,2,3,4,3,4,9000"  # 末端对位次在 dt 之前(定约)
    for bad_dt in (0, -1, DT_MS_MAX + 1, True, 1.5, "3"):
        with pytest.raises(ValueError):
            format_v4_r_row(V4Sample(1, 1, 1, 1, dt_ms=bad_dt), 0, 0)
        with pytest.raises(ValueError):
            format_v4_z_row(V4ZeroRun(2, 1, 1, dt_ms=bad_dt), 0, 0)
    with pytest.raises(ValueError):
        format_v4_z_row(V4ZeroRun(2, 20, 4, dl_total_end=5), 10, 0)  # 末端相对基线负 delta(免费校验)
    # interval_s >= 1 数值(允许小数秒); 非数值/越界/非有限 fail-fast
    assert format_v4_b_row(1000, 30) == "B,1000,30"  # 整值不带小数点(与历史文件形态一致)
    assert format_v4_b_row(1000, 30.0) == "B,1000,30"
    assert format_v4_b_row(1000, 1.5) == "B,1000,1.5"  # 小数秒最短往返表示
    for bad_iv in (0, -30, True, float("nan"), float("inf"), "30"):
        with pytest.raises(ValueError):
            format_v4_b_row(1000, bad_iv)
    head = [HEADER_LINE_V4, "key,global", "B,1000,30,5,8", "r,1,1,1,1"]
    # 完整末行无换行: 正常收数据, 不算 torn_tail(缺的只是行尾换行, 追加侧先补)
    ok = parse_v4_day_text("\n".join(head))
    assert ok.bad_lines == 0 and not ok.torn_tail and len(ok.blocks[0].records) == 1
    # 残缺末行: 记 torn_tail(豁免损坏占比)且计坏行; 前面好行照常收
    torn = parse_v4_day_text(_v4_day_text(head + ["r,1,1"])[:-1])  # 去掉末行换行 -> 残缺尾段
    assert torn.torn_tail is True and torn.bad_lines == 1 and len(torn.blocks[0].records) == 1


def test_v4_parse_discipline_dual_parser_same_verdict():
    """同纪律夹具双 parser 同判(行为守阵): 解析纪律骨架收敛 _parse_v4_text 单点后, 同一
    夹具喂 parse_v4_day_text / parse_v4_agg_text, 纪律面 (key / bad_lines / data_lines /
    torn_tail) 逐项同判 —— 夹具只用行型中立行(空行/注释/key 行/两侧皆坏的行), 行型语义
    差异(day 块状态机 vs agg 9+8 列)不进本守阵; 覆盖空文本 / 头行缺失与旧头行(整文件坏
    含头行本身) / 坏行族+空行注释跳 / 撕裂尾(末行坏才豁免) / 完整末行无换行(不标 torn)"""
    def _both(text):
        return parse_v4_day_text(text), parse_v4_agg_text(text)

    # 空文本: 零行零坏不撕裂, key 空
    day, agg = _both("")
    assert (day.key, day.bad_lines, day.data_lines, day.torn_tail) == (None, 0, 0, False)
    assert (agg.key, agg.bad_lines, agg.data_lines, agg.torn_tail) == (None, 0, 0, False)
    # 头行缺失 / 旧头行(v1/v3): 整文件记坏且 bad 含头行本身(bad == data == 全行数, 非 len-1)
    for head in ("key,early", "# auto-qb qb-traffic v1", "# auto-qb qb-traffic v3"):
        day, agg = _both(_v4_day_text([head, "garbage", "key,g1"]))
        for parsed in (day, agg):
            assert (parsed.key, parsed.bad_lines, parsed.data_lines, parsed.torn_tail) == (None, 3, 3, False)
    # 坏行族 + 空行注释跳: data 分母 = 头行之后全部行(含空行/注释/坏行), bad 只计真坏行,
    # key 首个消费(重复 key 行按行型记坏); 行型载荷两侧皆空
    neutral_bad = ["garbage", "x,y,z", "key,a,b", "key,", "r,1,1,1,1"]  # 两侧皆坏的行型中立行
    lines = [HEADER_LINE_V4, "key,g1", "", "# note"] + neutral_bad + ["key,g2"]
    day, agg = _both(_v4_day_text(lines))
    for parsed in (day, agg):
        assert parsed.key == "g1"
        assert parsed.bad_lines == len(neutral_bad) + 1  # + 重复 key 行
        assert parsed.data_lines == len(lines) - 1
        assert parsed.torn_tail is False
    assert day.blocks == () and (agg.hours, agg.days, agg.months) == ((), (), ())
    # 撕裂尾: 无尾换行且坏行恰为末行 -> torn_tail 两侧同判
    day, agg = _both(_v4_day_text([HEADER_LINE_V4, "key,g1", "garbage"])[:-1])
    for parsed in (day, agg):
        assert (parsed.key, parsed.bad_lines, parsed.data_lines, parsed.torn_tail) == ("g1", 1, 2, True)
    # 撕裂文件但末行是好行(被消费) -> 不标 torn_tail(豁免只标末行坏)
    day, agg = _both(_v4_day_text([HEADER_LINE_V4, "garbage", "key,g1"])[:-1])
    for parsed in (day, agg):
        assert (parsed.key, parsed.bad_lines, parsed.data_lines, parsed.torn_tail) == ("g1", 1, 2, False)


def test_v4_parse_skeleton_single_point():
    """静态守阵: 解析纪律骨架单点(issue 26-10-29-1304 R07-T06) —— 骨架行 / 行循环 /
    驱动器接线在 traffic_store_codec.py 各恰一处(两解析器都走 _parse_v4_text, 无行循环副本)。
    口径说明: 同形的空行注释跳行在 traffic_limits.parse_limits_day_text 还有一处, 但那是
    另一族解析器(无头行门闩 / 撕裂尾直接丢弃), 不在本 issue 收敛范围 —— 守阵只扫本文件"""
    src = inspect.getsource(traffic_store_codec_module)  # R5 拆分: 编解码骨架迁至 traffic_store_codec.py
    assert src.count('if not s or s.startswith("#")') == 1, "空行注释跳骨架行应只在公共驱动器"
    assert src.count("for i, line in enumerate(lines[1:]):") == 1, "行循环应只在公共驱动器"
    assert src.count("def _parse_v4_text(") == 1
    wiring = re.findall(r"^    key, bad, data, torn_tail = _parse_v4_text\(text, on_\w+_line\)$", src, re.M)
    assert sorted(wiring) == [
        "    key, bad, data, torn_tail = _parse_v4_text(text, on_agg_line)",
        "    key, bad, data, torn_tail = _parse_v4_text(text, on_day_line)",
    ], "两个解析器必须各自单点接线公共驱动器"


def test_v4_parse_null_column_and_nn_int_guard():
    """数据列空文本 = None(null 列), 非负整数合法 —— _parse_int_field 的单点语义;
    r/z 数据列无 null 形态(null 走 n 游程), 空列经 _parse_nn_int 抛「空列」-> 整行坏;
    agg 行的 cov/avg 列同一入口(9 列末列为空同样判坏)"""
    head = [HEADER_LINE_V4, "key,global", "B,1000,30,5,8"]
    # r 行 dl_rate 空列: _parse_int_field("") -> None -> _parse_nn_int 抛「空列」
    parsed = parse_v4_day_text(_v4_day_text(head + ["r,,1,0,0"]))
    assert parsed.bad_lines == 1 and parsed.blocks == ()  # 整块无好行: 空块不落(块尾才收)
    # 同族: z 行冻结列空(空列不因行型而豁免)
    parsed = parse_v4_day_text(_v4_day_text(head + ["z,2,,0,0,0"]))
    assert parsed.bad_lines == 1 and parsed.blocks == ()
    # 空列好行对照: 该块仍收得到合法行, 坏行不传染
    parsed = parse_v4_day_text(_v4_day_text(head + ["r,,1,0,0", "r,1,1,0,0"]))
    assert parsed.bad_lines == 1 and len(parsed.blocks[0].records) == 1
    # agg 路: 9 列末列(cov_s)为空 -> 「空列」坏行; 前 8 列照常可解析(行型合法)
    agg = parse_v4_agg_text(_v4_day_text([HEADER_LINE_V4, "hour,1000,10,20,5,8,100,200,"]))
    assert agg.bad_lines == 1 and agg.hours == ()


def test_v4_block_gap_continuous_boundary():
    """跨块覆盖结算判定单点(§01 定约): gap <= interval_s + 250ms(DRIFT_TOL) 判连续(边界含);
    超容差 = 真空(崩溃窗口/停机间隙不虚记覆盖); 病态重叠(gap <= 0)判连续 —— 结算区间为空,
    调用方自然无操作"""
    assert v4_block_gap_continuous(1000.0, 1030.0, 30) is True  # 恰等于 interval
    assert v4_block_gap_continuous(1000.0, 1030.25, 30) is True  # 恰压 250ms 容差(边界含)
    assert v4_block_gap_continuous(1000.0, 1030.26, 30) is False  # 超容差 = 真空
    assert v4_block_gap_continuous(1000.0, 900.0, 30) is True  # 病态重叠
    assert v4_block_gap_continuous(1000.0, 1001.5, 1.5) is True  # 小数秒 interval 同口径


def test_v4_parse_tolerance_blank_comment_and_orphan_rows():
    """解析容错面(天文件与 agg 同族纪律): 空行/注释行跳过不计坏; 块头前数据行判坏(游标无
    锚点, 记坏不消费); agg 头行不符整文件记坏; agg 坏行(字段非数值/空列)整行跳过不污染好行;
    agg 撕裂尾行豁免口径与天文件一致"""
    day = parse_v4_day_text(
        _v4_day_text([HEADER_LINE_V4, "key,global", "", "# 注释行", "r,1,1,0,0", "B,1000,30,5,8", "r,1,1,0,0"])
    )
    assert day.bad_lines == 1  # 仅块头前那条 r 计坏
    assert day.key == "global" and len(day.blocks) == 1 and len(day.blocks[0].records) == 1
    assert [s.ts for s in v4_block_slots(day.blocks[0])] == pytest.approx([1000.0], abs=1e-9)
    # 空文本 / 头行不符: 整文件记坏(key = None, 零块)
    assert parse_v4_agg_text("").key is None
    mismatch = parse_v4_agg_text("garbage\nhour,1000,10,20,5,8,100,200,3600")
    assert mismatch.key is None and mismatch.hours == () and mismatch.bad_lines == 2
    # agg 好行 + 空行/注释 + 两条坏行(非数值 epoch / cov 空列)
    agg = parse_v4_agg_text(
        _v4_day_text(
            [
                HEADER_LINE_V4,
                "key,global",
                "",
                "# 注释行",
                "hour,1000,10,20,5,8,100,200,3600",
                "hour,notanum,10,20,5,8,100,200,3600",
                "hour,4600,10,20,5,8,100,200,",
                "day,0,1,2,3,4,5,6,86400",
            ]
        )
    )
    assert agg.bad_lines == 2 and [h.epoch for h in agg.hours] == [1000] and len(agg.days) == 1
    # 撕裂尾: 末行残缺(无换行)且坏 -> torn_tail 豁免损坏占比, 前面好行照收
    torn = parse_v4_agg_text(f"{HEADER_LINE_V4}\nkey,global\nhour,1000,10,20,5,8,100,200,3600\nhour,1,2,3")
    assert torn.torn_tail is True and torn.bad_lines == 1 and len(torn.hours) == 1


def test_v4_z_row_requires_baseline_block():
    """r/z 行须基线块(无基线块仅 n 游程合法): 序列化侧同源守卫 fail-fast, 与解析侧
    「无基线块内出现 r/z 判坏行」互为镜像(写侧不允许落出读侧必判坏的行)"""
    with pytest.raises(ValueError, match="z 行须基线块"):
        format_v4_z_row(V4ZeroRun(2, 3, 4), None, None)
    with pytest.raises(ValueError, match="z 行须基线块"):
        format_v4_z_row(V4ZeroRun(2, 3, 4), 0, None)  # 基线只缺一侧同样拒
    with pytest.raises(ValueError, match="r 行须基线块"):
        format_v4_r_row(V4Sample(1, 1, 1, 1), None, 0)
    assert format_v4_n_row(V4NullRun(2)) == "n,2"  # n 行不受基线约束(无基线块唯一合法行型)


def test_v4_row_width_vs_legacy_layout_bytes():
    """体量对比: 同一构造采样序列分别按 v2 行型布局与 v4 行型序列化, 实测字节数对照 ——
    活跃 r 行 40-52B(v2: raw 前缀 + 时间戳列) -> 30-40B(v4: r 前缀无时间戳列 + delta 列存
    块内增量, 时刻由 dt 链推算); 空闲段 v2 零值行(1 行/采样) vs v4 z 游程(1 行/封口节奏
    600s)压缩 >10x。v2 行型布局此处仅作字节数对照基线(测量用途, 其解析/写侧已随 S5 退役)。"""
    dl, up, dlt, upt = 98_765, 45_678, 9_876_543_210, 1_234_567_890  # 真实量级: 速率 ~10^5, all-time totals ~10^10
    delta = 100_000_000  # 块内已传量 ~10^8(flush 窗 x 速率的真实量级, v4 delta 列的典型宽度)
    # 活跃段: 2880 行 30s 采样(一天); v2 行含 10 位 epoch 时间戳, v4 r 行无时间列且 delta 短
    v2_active = [f"raw,{1_800_000_000 + i * 30},{dl},{up},{dlt},{upt}" for i in range(2880)]
    v4_active = [f"r,{dl},{up},{delta},{delta}" for _ in range(2880)]
    v2_w = len(v2_active[0].encode()) + 1
    v4_w = len(v4_active[0].encode()) + 1
    assert 40 <= v2_w <= 52  # 计划 §09.1 规格带: v2 行宽 40-52B
    assert 30 <= v4_w <= 40  # v4 行宽 30-40B(delta 列存块内增量)
    assert v4_w < v2_w
    v2_bytes = sum(len(r.encode()) + 1 for r in v2_active)
    v4_bytes = sum(len(r.encode()) + 1 for r in v4_active)
    assert v2_bytes - v4_bytes >= 2880 * 10  # 每行至少省 10B(时间戳列 10-12B)
    # 空闲段: 一天全空闲(600s 游程节奏); v4 再加 B 行块头与头行(单文件一次性成本)
    v2_idle = [f"raw,{1_800_000_000 + i * 30},0,0,0,0" for i in range(2880)]
    v4_idle = [f"z,300,0,0" for _ in range(144)]  # 2880 槽 / 游程 300 槽; 空闲 delta 持平 0
    v2_idle_bytes = sum(len(r.encode()) + 1 for r in v2_idle)
    v4_idle_bytes = sum(len(r.encode()) + 1 for r in v4_idle)
    assert v2_idle_bytes / v4_idle_bytes > 10  # 空闲压缩 >10x
    # v4 行全部合法: 经解析 roundtrip 零坏行(对照基线不破坏格式契约)
    block = V4Block(
        1_800_000_000,
        30,
        dlt,
        upt,
        tuple(V4Sample(dl, up, dlt, upt) for _ in range(2880)) + tuple(V4ZeroRun(300, dlt, upt) for _ in range(144)),
    )
    parsed = parse_v4_day_text(format_v4_day_text("global", (block, )))
    assert parsed.bad_lines == 0 and len(parsed.blocks) == 1
    assert len(parsed.blocks[0].records) == 2880 + 144


def test_v4_day_roundtrip_with_drift_rows():
    """B1 roundtrip: v4 序列化 -> 解析与原始内存块逐点相等(绝对 totals + 显式 dt 漂移行 +
    z+n 游程 + 标称缺省行); delta 列 = 绝对值 - 块基线的字面文本核对; dt 链信息经 v3 同构
    转换后槽位实测序列逐点相等"""
    interval = 30
    recs = [
        V4Sample(10, 20, 1000, 2000),  # 块首 r: 基线 = 该快照, delta = 0
        V4Sample(11, 21, 1100, 2100, dt_ms=30400),  # r1 @1030.4, delta 100/100
        V4Sample(12, 22, 1200, 2200, dt_ms=30400),  # r2 @1060.8
        # z 游程 3 槽 @1091.6/1122.4/1153.2(空闲 totals 恒定): delta = 200/200 相对块基线;
        # 形态 D 末端对带真实值(delta 215/212)一并 roundtrip
        V4ZeroRun(3, 1200, 2200, dt_ms=92400, dl_total_end=1215, up_total_end=2212),
        V4NullRun(2, dt_ms=61600),
        V4Sample(13, 23, 1300, 2300, dt_ms=30800),  # r3 @1245.6, delta 300/300
        V4Sample(14, 24, 1400, 2400, dt_ms=30800),  # r4
        V4Sample(15, 25, 1500, 2500),  # r5 标称缺省行
        V4Sample(16, 26, 1600, 2600, dt_ms=30400),  # r6
    ]
    expected_ts = [1000.0, 1030.4, 1060.8, 1091.6, 1122.4, 1153.2, 1184.0, 1214.8, 1245.6, 1276.4, 1306.4, 1336.8]
    block = V4Block(start_epoch=1000, interval_s=interval, dl_base=1000, up_base=2000, records=tuple(recs))
    text = format_v4_day_text("global", (block, ))
    lines = text.splitlines()
    assert lines[0] == HEADER_LINE_V4 and lines[1] == "key,global"
    assert lines[2] == "B,1000,30,1000,2000"  # 5 列基线块
    assert lines[3] == "r,10,20,0,0" and lines[4] == "r,11,21,100,100,30400"  # delta = 绝对值 - 基线
    assert lines[5] == "r,12,22,200,200,30400" and lines[6] == "z,3,200,200,215,212,92400"  # 空闲 z: delta 持平非 0; 末端对在后
    parsed = parse_v4_day_text(text)
    assert parsed.key == "global" and parsed.bad_lines == 0 and parsed.data_lines == 11 and not parsed.torn_tail
    assert len(parsed.blocks) == 1 and parsed.blocks[0] == block  # 解析还原 == 原始内存形态(逐点)
    # 形态 D: agg 摊配序列由末端对派生(端点精确 + 单调; raw obs 不变见下)
    assert v4_block_agg_totals(parsed.blocks[0])[3:6] == ((1200, 2200), (1208, 2206), (1215, 2212))
    # dt 链槽位推算与实测序列逐一相等(delta 复原后槽位数学与基线无关)
    slots = v4_block_slots(parsed.blocks[0])
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
    # 多块: 各块基线独立(delta 各自相对本块基线)
    b2 = V4Block(
        start_epoch=5000,
        interval_s=60,
        dl_base=100,
        up_base=200,
        records=(V4Sample(1, 1, 101, 202), V4Sample(1, 1, 161, 262, dt_ms=61000)),
    )
    assert format_v4_day_text("k", (b2, )).splitlines()[4] == "r,1,1,61,62,61000"
    parsed2 = parse_v4_day_text(format_v4_day_text("torrent:ABC", (block, b2)))
    assert parsed2.key == "torrent:ABC" and len(parsed2.blocks) == 2 and parsed2.blocks[1] == b2
    assert [s.ts for s in v4_block_slots(parsed2.blocks[1])] == pytest.approx([5000.0, 5061.0], abs=1e-6)  # 第二块独立游标


def test_v4_b_row_dual_form_3col_5col():
    """B 行 3/5 列二态(v4 §01): 无基线 = 3 列(仅 n 游程合法)/ 基线 = 5 列(基线 = 块内
    首个带 totals 观测的快照); 格式与解析两侧二态识别; 基线缺一 fail-fast; interval_s
    小数秒口径沿用; n 行行型与 v3 不变; 二态同文件任意顺序并存"""
    assert format_v4_b_row(1000, 30) == "B,1000,30"  # 3 列无基线
    assert format_v4_b_row(1000, 30, 5_000_000_000, 8_000_000_000) == "B,1000,30,5000000000,8000000000"  # 5 列
    assert format_v4_b_row(1000, 1.5, 5, 8) == "B,1000,1.5,5,8"  # 小数秒口径沿用
    assert format_v4_b_row(1000, 30.0, 5, 8) == "B,1000,30,5,8"  # 整值不带小数点
    # 基线二态须成对(缺一 fail-fast); interval_s 校验口径同 v3
    for bad_pair in ((5, None), (None, 8)):
        with pytest.raises(ValueError):
            format_v4_b_row(1000, 30, *bad_pair)
    for bad_iv in (0, -30, True, float("nan"), float("inf"), "30"):
        with pytest.raises(ValueError):
            format_v4_b_row(1000, bad_iv)
    # n 行不变(与 v3 同形)
    assert format_v4_n_row(V4NullRun(2)) == "n,2" and format_v4_n_row(V4NullRun(2, dt_ms=5000)) == "n,2,5000"
    # 解析二态: 3 列 B -> 基线 None/None; 5 列 B -> 基线还原; 同文件并存(无基线块在前)
    parsed = parse_v4_day_text(
        _v4_day_text(
            [
                HEADER_LINE_V4,
                "key,global",
                "B,1000,30",
                "n,3",
                "n,2,9000",  # 无基线块(纯 n)
                "B,2000,60,100,200",
                "r,1,1,0,0",
                "r,2,2,50,60,61000",  # 基线块
            ]
        )
    )
    assert parsed.bad_lines == 0 and len(parsed.blocks) == 2
    assert (parsed.blocks[0].dl_base, parsed.blocks[0].up_base) == (None, None)
    assert parsed.blocks[0].records == (V4NullRun(3), V4NullRun(2, 9000))
    assert (parsed.blocks[1].dl_base, parsed.blocks[1].up_base) == (100, 200)
    assert parsed.blocks[1].records == (V4Sample(1, 1, 100, 200), V4Sample(2, 2, 150, 260, 61000))
    # 反序并存: 基线块 -> 无基线块(如 00:00 硬切后空闲开场)同样二态各自成立
    rev = parse_v4_day_text(
        _v4_day_text([HEADER_LINE_V4, "key,global", "B,1000,30,5,8", "r,1,1,0,0", "B,2000,60", "n,2"])
    )
    assert rev.bad_lines == 0 and len(rev.blocks) == 2
    assert (rev.blocks[0].dl_base, rev.blocks[0].up_base) == (5, 8)
    assert (rev.blocks[1].dl_base, rev.blocks[1].up_base) == (None, None) and len(rev.blocks[1].records) == 1
    # 二态之外(4/6 列)与基线列负值: 整行计坏、不开新块、既有块不受影响
    head = [HEADER_LINE_V4, "key,global", "B,1000,30,5,8", "r,1,1,0,0"]
    bad_bs = ["B,1000,30,5", "B,1000,30,5,8,9", "B,1000,30,-5,8", "B,1000,30,5,-8"]
    out = parse_v4_day_text(_v4_day_text(head + bad_bs + ["r,2,2,10,10"]))
    assert out.bad_lines == len(bad_bs)
    assert len(out.blocks) == 1 and [r.dl_total for r in out.blocks[0].records] == [5, 15]


def test_v4_negative_delta_bad_row_non_propagating():
    """负 delta 判坏行(§01 免费校验: 计数器回落在绝对值形态合法, delta 形态必是损坏):
    整行跳过计数、游标不推进; delta-vs-基线逐行独立 —— 块中段坏行后, 后续行 totals 复原
    仍精确(坏行不传播); r/z 两行型都判; 序列化侧负 delta fail-fast(写侧纪律); 撕裂尾
    半行豁免口径沿用"""
    base_dl, base_up = 10_000, 20_000
    head = [HEADER_LINE_V4, "key,global", f"B,1000,30,{base_dl},{base_up}", "r,10,20,0,0", "r,11,21,100,100"]
    bads = ["r,12,22,-1,50", "z,2,0,-3"]  # r 与 z 的负 delta 各一
    tail = ["r,13,23,300,300", "z,2,300,300,45000", "n,2", "r,14,24,400,400,30000"]
    parsed = parse_v4_day_text(_v4_day_text(head + bads + tail))
    assert parsed.bad_lines == 2 and parsed.data_lines == 10
    (block, ) = parsed.blocks
    # 复原绝对值 = 基线 + 本行 delta(逐行独立): 坏行两侧的好行都精确
    # (若实现误作块内增量链, 坏行后一行会复位成 10400 —— 本断言同时甄别两种语义)
    assert [type(r) for r in block.records] == [V4Sample, V4Sample, V4Sample, V4ZeroRun, V4NullRun, V4Sample]
    assert [(r.dl_total, r.up_total) for r in block.records[:3]] == [(10000, 20000), (10100, 20100), (10300, 20300)]
    assert (block.records[3].dl_total, block.records[3].up_total) == (10300, 20300)
    assert (block.records[5].dl_total, block.records[5].up_total) == (10400, 20400)
    # 游标不推进: 坏行剔除后的 dt 链推算时刻与干净文件(无坏行)完全一致
    clean = parse_v4_day_text(_v4_day_text(head + tail))
    assert [s.ts for s in v4_block_slots(block)] == [s.ts for s in v4_block_slots(clean.blocks[0])]
    assert block.records[5].dt_ms == 30000  # 尾行显式 dt 以好行链上锚点起算(坏行不占链)
    # 序列化侧: 负 delta fail-fast(计数器回落须先关块重立基线); r/z 行须基线块
    with pytest.raises(ValueError):
        format_v4_r_row(V4Sample(1, 1, 9_999, 20_000), base_dl, base_up)
    with pytest.raises(ValueError):
        format_v4_z_row(V4ZeroRun(2, 10_000, 19_999), base_dl, base_up)
    with pytest.raises(ValueError):
        format_v4_r_row(V4Sample(1, 1, 5, 5), None, None)
    # 撕裂尾半行豁免口径沿用: 残缺末行记 torn_tail 且计坏, 前面好行照常收
    torn = parse_v4_day_text(_v4_day_text(head + tail + ["r,15,25,5"])[:-1])
    assert torn.torn_tail is True and torn.bad_lines == 1 and len(torn.blocks[0].records) == 6


def test_v4_z_end_pair_shapes_legacy_compat():
    """形态 D z 行末端对(plan 26-10-16-1509 §04): 新 6/7 列(末端对在 dt 之前)与旧 4/5 列
    同文件并存; 旧行解析末端 = None(agg 摊配按开启快照退化, 向后兼容); 末端对 delta 以块
    基线复原绝对值; 末端对仅 agg 车道 —— raw 槽 obs 仍为冻结列(逐字不变)"""
    head = [HEADER_LINE_V4, "key,global", "B,1000,30,100,200", "r,1,1,0,0"]
    rows = [
        "z,2,10,20",  # 旧 4 列: 无末端列
        "z,2,30,40,50,60",  # 新 6 列: 末端对(块基线 + 列 delta), 无 dt
        "z,2,70,80,90,100,9000",  # 新 7 列: 末端对 + dt
        "z,2,110,120,110,120",  # 新列显式退化(末端 = 冻结列)
    ]
    parsed = parse_v4_day_text(_v4_day_text(head + rows))
    assert parsed.bad_lines == 0 and len(parsed.blocks) == 1
    z0, z1, z2, z3 = parsed.blocks[0].records[1:5]
    assert z0.dl_total_end is None and z0.up_total_end is None  # 旧行: 无末端列
    assert (z1.dl_total, z1.up_total, z1.dl_total_end, z1.up_total_end) == (130, 240, 150, 260)
    assert z1.dt_ms is None
    assert (z2.dl_total_end, z2.up_total_end, z2.dt_ms) == (190, 300, 9000)
    assert (z3.dl_total_end, z3.up_total_end) == (z3.dl_total, z3.up_total)  # 显式退化
    # raw 车道不变: z 槽 obs 仍为冻结列(末端对不参与)
    slots = v4_block_slots(parsed.blocks[0])
    assert slots[1].obs == (0, 0, 110, 220) and slots[3].obs == (0, 0, 130, 240)
    assert slots[5].obs == (0, 0, 170, 280) and slots[7].obs == (0, 0, 210, 320)
    # agg 车道: 逐槽摊配序列(旧行/退化行 → 恒快照; 有末端行 → 端点内插)
    assert v4_block_agg_totals(parsed.blocks[0]) == (
        None,
        (110, 220),
        (110, 220),
        (130, 240),
        (150, 260),
        (170, 280),
        (190, 300),
        (210, 320),
        (210, 320),
    )
    # 平行序列长度口径与 v4_block_slots 一致(改任一处需同步)
    assert len(v4_block_agg_totals(parsed.blocks[0])) == len(slots) == 9


def test_v4_z_totals_ramp_endpoints_monotone_and_conservation():
    """形态 D 摊配纯函数(plan 26-10-16-1509 §04/§05 判据 1/2/4): 端点精确(v_0 = S0,
    v_{n-1} = S1)/ 逐分量单调不减 / 区间累加严格守恒(Σ 相邻差 = S1 - S0, 取整余量归
    末端槽; 每步与精确均值偏差 <= 1 字节)/ 逐向独立; n = 1 与无末端与末端低于开启降档"""
    s0, s1 = (1_000_000, 2_000_000), (15_999_000, 18_000_000)
    ramp = v4_z_totals_ramp(s0[0], s0[1], s1[0], s1[1], 121)
    assert ramp[0] == s0 and ramp[-1] == s1  # 端点精确
    assert all(ramp[k][0] <= ramp[k + 1][0] and ramp[k][1] <= ramp[k + 1][1] for k in range(len(ramp) - 1))
    inc = [ramp[k + 1][0] - ramp[k][0] for k in range(len(ramp) - 1)]
    assert sum(inc) == s1[0] - s0[0]  # 守恒
    exact = (s1[0] - s0[0]) / (len(ramp) - 1)
    assert max(abs(i - exact) for i in inc) <= 1.0  # 逐步取整偏差 <= 1 字节
    # 半上取整钉住(.5 边界逐槽进; 余量随步进自然归末端槽)
    assert v4_z_totals_ramp(0, 0, 10, 0, 5) == ((0, 0), (3, 0), (5, 0), (8, 0), (10, 0))
    # 逐向独立(仅 dl / 仅 up 增长各摊各的)
    dl_only = v4_z_totals_ramp(10, 20, 1000, 20, 5)
    assert [p[1] for p in dl_only] == [20] * 5 and dl_only[-1] == (1000, 20)
    up_only = v4_z_totals_ramp(10, 20, 10, 900, 5)
    assert [p[0] for p in up_only] == [10] * 5 and up_only[-1] == (10, 900)
    # n = 1(跨度退化)/ 无末端列 / 末端低于开启(游程内重置): 恒快照(逐向独立)
    assert v4_z_totals_ramp(5, 6, 99, 99, 1) == ((5, 6), )
    assert set(v4_z_totals_ramp(5, 6, None, None, 4)) == {(5, 6)}
    assert set(v4_z_totals_ramp(5, 6, 4, 3, 4)) == {(5, 6)}  # 两向都低于开启 -> 全降档
    mixed = v4_z_totals_ramp(5, 6, 4, 906, 4)  # 仅 dl 低于开启: 该向降档, up 照常摊配
    assert [p[0] for p in mixed] == [5] * 4 and mixed[-1] == (5, 906)


def test_v4_no_baseline_block_n_only_guard():
    """n-only 无基线块(v4 §01 基线立点: 块首 n 游程 -> 写侧拆 3 列 B 无基线块): 3 列 B +
    纯 n 合法(roundtrip); 无基线块内 r/z 判坏行(解析守卫, 整行跳过、后续 n 照常收);
    序列化侧同源守卫 fail-fast; n-only 前缀块 -> 恢复传输记录开新块立基线(两块接续)"""
    # 合法: 3 列 B + 纯 n, roundtrip 还原
    block = V4Block(1000, 30, None, None, (V4NullRun(3), V4NullRun(2, 9000)))
    text = format_v4_day_text("global", (block, ))
    assert text.splitlines()[2] == "B,1000,30"
    parsed = parse_v4_day_text(text)
    assert parsed.bad_lines == 0 and parsed.blocks[0] == block
    # 解析守卫: 无基线块内 r/z 整行判坏, 后续 n 照常收(游标不推进)
    guarded = parse_v4_day_text(
        _v4_day_text([HEADER_LINE_V4, "key,global", "B,1000,30", "r,1,1,0,0", "z,2,0,0", "n,3,45000", "n,2"])
    )
    assert guarded.bad_lines == 2 and guarded.data_lines == 6 and len(guarded.blocks) == 1
    assert guarded.blocks[0].records == (V4NullRun(3, 45000), V4NullRun(2))
    # n-only 前缀块 -> 恢复传输开新块立基线: 前块无基线, 后块 5 列, 两块接续不断史
    seq = parse_v4_day_text(
        _v4_day_text([HEADER_LINE_V4, "key,global", "B,1000,30", "n,3", "B,1090,30,1000,2000", "r,1,1,0,0"])
    )
    assert seq.bad_lines == 0 and len(seq.blocks) == 2
    assert (seq.blocks[0].dl_base, seq.blocks[0].up_base) == (None, None) and seq.blocks[0].records == (V4NullRun(3), )
    assert (seq.blocks[1].dl_base, seq.blocks[1].up_base) == (1000, 2000)
    assert seq.blocks[1].records == (V4Sample(1, 1, 1000, 2000), )
    # 序列化侧同源守卫: r 行须基线块; day_text 组装无基线块内 r 同样 fail-fast
    with pytest.raises(ValueError):
        format_v4_r_row(V4Sample(1, 1, 2, 2), None, None)
    with pytest.raises(ValueError):
        format_v4_day_text("global", (V4Block(1000, 30, None, None, (V4Sample(1, 1, 2, 2), )), ))


def test_v4_header_latch_whole_file_mismatch():
    """头行 v4 门闩(v4 §01, R2 不设双读): 头行必须恰为 v4 —— v3/v1/v2 旧头行/缺失/非头行
    整文件不匹配格式, 全部行记坏、key None; v4 常量字面值钉住(批 2 翻转的接线依据)"""
    assert HEADER_LINE_V4 == "# auto-qb qb-traffic v4"
    assert TRAFFIC_V4_DIR_NAME == "qb-traffic-v4"
    body = ["key,global", "B,1000,30,5,8", "r,1,1,0,0"]
    for head in ("# auto-qb qb-traffic v3", "# auto-qb qb-traffic v1", "# auto-qb qb-traffic v2", "key,global"):
        old = parse_v4_day_text(_v4_day_text([head] + body))
        assert old.key is None and old.blocks == () and old.bad_lines == 4 and old.data_lines == 4
    # 空文本: 头行缺失 -> 全空解析(与 v3 口径一致)
    empty = parse_v4_day_text("")
    assert empty.key is None and empty.blocks == () and empty.bad_lines == 0 and empty.data_lines == 0


def test_v4_parse_orphan_n_row_counts_bad_no_ghost_block():
    """块头前数据行纪律(n 游程形态): 头行后直接跟 n 行(无 B 行)整行计坏且不产幽灵块
    (blocks 空)—— 变异面: 块头游标哨兵死值让 n 行混进幽灵块(start_epoch=""/interval=None),
    下游 v4_block_slots float(None) TypeError 崩读路径且坏行计数归零(r/z 形态有「无基线块
    内 r/z」守卫拦着, 唯 n 行可穿透)"""
    parsed = parse_v4_day_text(_v4_day_text([HEADER_LINE_V4, "key,global", "n,3"]))
    assert parsed.key == "global"
    assert parsed.bad_lines == 1 and parsed.data_lines == 2  # 分母含 key 行
    assert parsed.blocks == ()


def test_v4_read_replaces_invalid_utf8_bytes_as_bad_lines(tmp_path):
    """读侧缺省纪律(errors="replace", issue 26-10-11-0207 R07): 非 UTF-8 字节(磁盘坏/外部
    编辑)记坏行不炸读路径 —— read_agg 与 read_day 两入口(经 _read_parse 单点), 好行不受牵连"""
    st = TrafficV4Store(str(tmp_path))
    key = "torrent:BAD"
    os.makedirs(v4_series_dir(str(tmp_path), key))
    with open(v4_agg_file_path(str(tmp_path), key), "wb") as f:
        f.write((HEADER_LINE_V4 + "\n" + f"key,{key}\n").encode("utf-8"))
        f.write(b"\xff\xfe broken\n")
        f.write(f"hour,{int(_S2B_H0)},10,20,5,8,100,200,3600\n".encode("utf-8"))
    parsed = st.read_agg(key)
    assert parsed.key == key and parsed.bad_lines == 1 and parsed.data_lines == 3
    assert [h.epoch for h in parsed.hours] == [int(_S2B_H0)]  # 好行不受牵连
    with open(st.series_day_path(key, "2026-10-31"), "wb") as f:
        f.write((HEADER_LINE_V4 + "\n" + f"key,{key}\n" + "B,1000,30,5,8\n").encode("utf-8"))
        f.write(b"\xff garbage\n")
        f.write(b"r,1,1,0,0\n")
    day = st.read_day(key, "2026-10-31")
    assert day.bad_lines == 1 and day.data_lines == 4 and len(day.blocks) == 1


def test_v4_z_row_negative_delta_each_direction_fail_fast():
    """z 行负 delta 写侧 fail-fast 逐向独立(dl/up 冻结列与末端对四列, 任一单列为负即拒 ——
    变异面: min 漏检任一列则该向负 delta 落盘, 读侧整行静默丢且无写侧信号)"""
    dl_base, up_base = 10_000, 20_000
    negatives = (
        V4ZeroRun(2, dl_base - 1, up_base + 10, dl_total_end=dl_base + 5, up_total_end=up_base + 10),  # dl 冻结列
        V4ZeroRun(2, dl_base + 10, up_base - 1, dl_total_end=dl_base + 10, up_total_end=up_base + 5),  # up 冻结列
        V4ZeroRun(2, dl_base + 10, up_base + 10, dl_total_end=dl_base - 1, up_total_end=up_base + 10),  # dl 末端
        V4ZeroRun(2, dl_base + 10, up_base + 10, dl_total_end=dl_base + 5, up_total_end=up_base - 1),  # up 末端
    )
    for rec in negatives:
        with pytest.raises(ValueError, match="负 delta"):
            format_v4_z_row(rec, dl_base, up_base)
    # 正向对照: 全列非负照常序列化(delta 文本 = 绝对值 - 基线)
    ok = format_v4_z_row(
        V4ZeroRun(2, dl_base + 5, up_base + 8, dl_total_end=dl_base + 9, up_total_end=up_base + 12), dl_base, up_base
    )
    assert ok == "z,2,5,8,9,12"


def test_v4_bad_line_warn_torn_exemption_and_gate_boundaries(tmp_path, caplog, monkeypatch):
    """坏行告警豁免与闸门(W4 _wbl_4/6/9/13/14 + _wblp_4/8/12/18/19): 撕裂尾恰豁免 1 行
    (失效则临界误告, 加倍则临界被吞); 单行坏行(占比再高)不告; 占比 <= 5%(含恰等)不告"""
    monkeypatch.setattr(traffic_store_module, "_bad_line_warn_ts", {})
    store = TrafficV4Store(str(tmp_path))
    head = [HEADER_LINE_V4, "key,global", "B,1000,30,5,8"]

    def _write(date_str: str, lines, trailing_newline: bool = True) -> None:
        path = v4_day_file_path(str(tmp_path), "global", date_str)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        text = _v4_day_text(lines)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text if trailing_newline else text[:-1])

    def _warns() -> list:
        return [r for r in caplog.records if "坏行" in r.getMessage()]

    # 1. 撕裂尾恰豁免 1 行: 中段 1 坏行 + 尾部半行(豁免) -> 有效坏行 1 < 2, 不告
    _write("2026-10-01", head + ["r,1,1,1,1"] * 34 + ["garbage", "torn_half"], trailing_newline=False)
    with caplog.at_level(logging.WARNING, logger="auto_qb.core.traffic_store"):
        parsed = store.read_day("global", "2026-10-01")
    assert parsed.bad_lines == 2 and parsed.torn_tail is True
    assert not _warns(), "撕裂尾豁免后有效坏行 1 < 2(豁免不得失效)"
    # 2. 豁免不加倍: 中段 2 坏行 + 尾部半行 -> 有效坏行 2 且 2/39 > 5% -> 告警恰一次
    caplog.clear()
    _write("2026-10-02", head + ["r,1,1,1,1"] * 34 + ["garbage1", "garbage2", "torn_half"], trailing_newline=False)
    with caplog.at_level(logging.WARNING, logger="auto_qb.core.traffic_store"):
        parsed2 = store.read_day("global", "2026-10-02")
    assert parsed2.bad_lines == 3 and parsed2.torn_tail is True
    assert len(_warns()) == 1, "豁免后有效坏行 2 超阈告警(豁免不得加倍)"
    # 3. 单行坏行(1/10 = 10% > 5%): 行数闸拦下不告
    caplog.clear()
    _write("2026-10-03", head + ["r,1,1,1,1"] * 7 + ["garbage"])
    with caplog.at_level(logging.WARNING, logger="auto_qb.core.traffic_store"):
        parsed3 = store.read_day("global", "2026-10-03")
    assert parsed3.bad_lines == 1 and parsed3.data_lines == 10
    assert not _warns(), "单行坏行不告(行数闸)"
    # 4. 占比闸: 2/100 = 2% <= 5% 不告
    caplog.clear()
    _write("2026-10-04", head + ["r,1,1,1,1"] * 96 + ["garbage1", "garbage2"])
    with caplog.at_level(logging.WARNING, logger="auto_qb.core.traffic_store"):
        store.read_day("global", "2026-10-04")
    assert not _warns(), "占比 2% <= 5% 不告"
    # 5. 占比恰等边界: 2/40 = 5.0% 恰压线不告(超阈为严格大于)
    caplog.clear()
    _write("2026-10-05", head + ["r,1,1,1,1"] * 36 + ["garbage1", "garbage2"])
    with caplog.at_level(logging.WARNING, logger="auto_qb.core.traffic_store"):
        store.read_day("global", "2026-10-05")
    assert not _warns(), "占比恰等 5% 不告(严格大于才告)"


def test_v4_bad_line_warn_throttle_table_clear_boundary(tmp_path, caplog, monkeypatch):
    """节流表清空边界(W4 _wbl_21/23/24): 含本条恰 256 条不清空; 第 257 条触发整体清空"""
    monkeypatch.setattr(traffic_store_module, "_bad_line_warn_ts", {})
    store = TrafficV4Store(str(tmp_path))
    good = [HEADER_LINE_V4, "key,global", "B,1000,30,5,8"] + ["r,1,1,1,1"] * 34
    path = v4_day_file_path(str(tmp_path), "global", "2026-10-06")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(_v4_day_text(good + ["garbage1", "garbage2"]))
    # 预填 255 条 + 本次告警 = 256: 未越上界不清空
    monkeypatch.setattr(traffic_store_module, "_bad_line_warn_ts", {f"f{i}": 0.0 for i in range(255)})
    with caplog.at_level(logging.WARNING, logger="auto_qb.core.traffic_store"):
        store.read_day("global", "2026-10-06")
    assert len([r for r in caplog.records if "坏行" in r.getMessage()]) == 1
    assert len(traffic_store_module._bad_line_warn_ts) == 256, "含本条恰 256 条不清空"
    # 预填 256 条 + 本次告警 = 257: 越上界整体清空
    caplog.clear()
    monkeypatch.setattr(traffic_store_module, "_bad_line_warn_ts", {f"f{i}": 0.0 for i in range(256)})
    with caplog.at_level(logging.WARNING, logger="auto_qb.core.traffic_store"):
        store.read_day("global", "2026-10-06")
    assert len([r for r in caplog.records if "坏行" in r.getMessage()]) == 1
    assert len(traffic_store_module._bad_line_warn_ts) == 0, "第 257 条触发整体清空"


def test_v4_bad_line_warn_message_fields_and_source_identity(tmp_path, caplog, monkeypatch):
    """告警消息字段与来源标识(W4 _wbl_26/27 + _wblp_1): 消息含文件标识(系列目录名/文件名)、
    有效坏行数/受检行数与占比字段; 不同文件按来源分槽各自告警不互吞"""
    monkeypatch.setattr(traffic_store_module, "_bad_line_warn_ts", {})
    store = TrafficV4Store(str(tmp_path))
    good = [HEADER_LINE_V4, "key,global", "B,1000,30,5,8"] + ["r,1,1,1,1"] * 34
    for date in ("2026-10-06", "2026-10-05"):
        path = v4_day_file_path(str(tmp_path), "global", date)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(_v4_day_text(good + ["garbage1", "garbage2"]))
    with caplog.at_level(logging.WARNING, logger="auto_qb.core.traffic_store"):
        store.read_day("global", "2026-10-06")
        store.read_day("global", "2026-10-05")
    warns = [r.getMessage() for r in caplog.records if "坏行" in r.getMessage()]
    assert len(warns) == 2, "不同文件按来源分槽各自告警(不互吞)"
    assert any("global/2026-10-06.dat" in m and "坏行 2/38 行" in m and "占比 5.3%" in m for m in warns)
    assert any("global/2026-10-05.dat" in m for m in warns)
    # 撕裂尾场景消息中的有效坏行数 = 豁免后计数(3 非 4)
    caplog.clear()
    torn = good + ["garbage1", "garbage2", "garbage3", "torn_half"]
    path = v4_day_file_path(str(tmp_path), "global", "2026-10-04")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(_v4_day_text(torn)[:-1])
    with caplog.at_level(logging.WARNING, logger="auto_qb.core.traffic_store"):
        store.read_day("global", "2026-10-04")
    warns2 = [r.getMessage() for r in caplog.records if "坏行" in r.getMessage()]
    assert len(warns2) == 1 and "坏行 3/40 行" in warns2[0]
