"""test_traffic_store_slots 测试计划: qB 口径流量 v4 存储层(plan 26-10-05-2200 §01-§05; v1/v2/v3 退役面已随各代删除)

## 测试计划(每个测试函数一条)
handler 接线(S2a, v4 写侧):

v4 纯函数区(B1 立并于批 2 接线, plan 26-10-05-2200 §01):

v4 写侧存储(S2a/S2b, TrafficV4Store):

v4 读侧解析缓存(S3a/S3b, V4DayCache):

体量实测(plan 26-10-04-1957 §09.1 口径沿用到 v4):

v4 活尾快照(S6 验收):
- test_v4_live_tail_slots_mirror_identity_family: 镜像保证族 —— 磁盘部分块槽 + 活尾槽 == 整块
  重算槽(逐槽恒等): 块全量未落盘(head_pending 整块重算, 含块首 r/块首游程)/块中途 flush 后
  倒推复原(显式 dt + z/n 游程混排)/全部落盘仅剩开放游程
- test_v4_live_tail_slots_open_run_forms: 开放游程封口形态 —— 无开放块块首形([int(run.start),
  last_seen] 端点含, n=1 单槽)/有开放块非块首形((链终点, last_seen] 均摊, 末槽 = last_seen)
- test_v4_live_tail_slots_invariants_fail_fast: block_open=False 带 records/head_pending -> ValueError;
  未知记录型 -> TypeError

v4 定约专测(B1 用例, 批 2 回归):

P1-T1.2 守卫与容错簇(计划 26-10-20-2101, 覆盖率缺口清偿):
- test_v4_block_slots_unknown_record_type_fail_fast: 未知块记录型 -> TypeError(raw/agg 两条
  槽位数学同源, 不静默跳过)

mut-core W4 S5 定向补测(变异审计确认真洞守阵, 2026-10-31; 红验 tmp-analysis/redverify-s5-w4.py):
- test_v4_block_slots_first_run_single_slot_nominal_spacing: slots_45 —— 块首单槽游程(run_len=1
  带 dt)槽距落标称 interval, 不除零崩
- test_v4_live_tail_slots_open_run_edge_spans: live_tail_104/136/137/150 —— 开放游程封口边缘
  跨度(span=1 非块首形均摊 / 块首形 n=2 端点含 / n=1 单槽 dt_s = 标称 interval)

mut-core W4 S6 定向补测(2026-11-02, issue 26-10-31-1539 两件清偿; 红验 tmp-analysis/redverify-s6-w4.py):
- test_v4_live_tail_slots_zero_and_negative_span_forms: live_101/103/128 —— 开放游程封口同秒
  病态(span==0)与时钟回拨(last_seen < 链锚点): 非块首落标称 interval 均摊, 块首收拢
  int(start) 且 dt_s 落标称 interval

活尾链端延伸 holding 槽(F4, 计划 26-11-14-1313 S1b)已随持有面退役(26-11-18-0037
D2/T1c-2: 尾组恒真值无克隆, v4_live_tail_slots 的 now/max_gap_s 形参面删除)—— 旧持有
族 6 例改写为「槽位复原无持有延伸」守阵:
- test_v4_live_tail_slots_pure_restoration_no_hold_extension: 复原即纯槽序 —— 活跃链/z
  游程/停滞过界/断连(n 游程收尾与开放 n 游程)各形态输出均与「末真实样本」槽序恒等,
  now 之外无任何合成槽(间隙大小不影响输出; 旧「now 超链端追加 holding 槽」不存在)
- test_v4_live_tail_slots_signature_no_hold_params: 持有延伸形参面退役的 poka-yoke ——
  签名无 now/max_gap_s(inspect 单点), 传参即 TypeError(变异加回形参面即红)
- test_block_slots_from_full_equivalence: (自桶缓存电池迁入, T1c-2)v4_block_slots_from 与
  v4_block_slots 双形态等价 —— 随机混排块全量展开逐槽相等/游标分段链式拼接 == 全量/游程
  中段截停续展 == 全量(唯一 dt 链实现的两入口不漂移)
- test_v4_z_ramp_element_matches_ramp_and_run_geometry: B2 闭合式单点守阵(plan
  26-11-21-1546 S1)—— v4_z_ramp_element 与 v4_z_totals_ramp 逐元素相等(随机入参全域:
  端点/退化末端/单槽/奇偶 n), v4_run_geometry 与 v4_block_slots 的 spacing/base 推导逐位
  一致(块首/非块首 x 显式/标称 dt)—— 闭合式入账与逐槽展开公式同源不漂移

线程/时钟纪律: 需要确定时刻的用例经 monkeypatch 固定 time.time(测试进程内单线程, 恢复由
monkeypatch 保证); 文件一律落在 tmp_path(test.* 已内置 TMPDIR, 不手工加前缀)。
"""

import builtins

import inspect

import logging

import random

import os

import re

import tempfile

import threading

import time

from datetime import datetime

import pytest

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
    v4_block_slots_from,
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
    v4_run_geometry,
    v4_z_ramp_element,
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


def test_v4_block_slots_unknown_record_type_fail_fast():
    """v4_block_slots / v4_block_agg_totals 只认 V4Sample/V4ZeroRun/V4NullRun 三种记录型:
    未知记录型 TypeError(fail-fast —— 槽位数学静默跳过会让 raw/agg 两车道错位, 比抛错更难查)"""
    block = V4Block(1000, 30, 5, 8, (object(), ))
    with pytest.raises(TypeError, match="未知块记录型"):
        v4_block_slots(block)
    with pytest.raises(TypeError, match="未知块记录型"):
        v4_block_agg_totals(block)


def _s6_mixed_records(interval: int) -> tuple:
    """S6 镜像保证用例的混排记录序列: r(标称) / r(显式 dt) / z 游程 / r / n 游程 / r"""
    base = 1_800_000_000
    return (
        V4Sample(100, 50, 1000, 500),  # 块首 r(槽位 = B.start)
        V4Sample(200, 70, 2000, 800, dt_ms=(interval + 1) * 1000),  # 显式 dt(超容差)
        V4ZeroRun(3, 2000, 800),  # 零速游程(标称 3 槽)
        V4Sample(150, 60, 2600, 1100),  # 游程后 r(链锚点 = 游程终点)
        V4NullRun(2, dt_ms=(2 * interval - 1) * 1000),  # 断连游程(显式 dt)
        V4Sample(90, 40, 3000, 1300),  # 末记录
    )


def test_v4_live_tail_slots_mirror_identity_family():
    """镜像保证族: 磁盘部分块槽 + 活尾槽 == 整块重算槽(逐槽恒等, S6 去重的正确性根基)

    三分割点: k=0(块全量未落盘 -> head_pending 整块重算)/ 0<k<N(中途 flush 后从写侧
    游标倒推)/ k=N(全部落盘, 活尾只剩开放游程 —— 单独在 open_run 用例覆盖)。
    """
    interval = 30
    recs = _s6_mixed_records(interval)
    start = 1_800_000_000
    full_block = V4Block(start, interval, 1000, 500, recs)
    full_slots = v4_block_slots(full_block)
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
    assert v4_live_tail_slots(tail_head) == full_slots
    for k in (1, 3, 5):  # 中途 flush: 磁盘已收前 k 条, 缓冲滞留其余
        disk_slots = v4_block_slots(V4Block(start, interval, 1000, 500, recs[:k]))
        tail = LiveTail(
            block_open=True,
            head_pending=False,
            start_epoch=start,
            interval_s=interval,
            projected_ts=projected,
            records=recs[k:],
            open_run=None,
        )
        assert disk_slots + v4_live_tail_slots(tail) == full_slots, k
    # 倒推不依赖磁盘链可见(1m 窗场景): 仅活尾自身也逐槽落在整块槽序的后缀上
    k = 3  # 前 3 条记录 = 1+1+3(r,r,z 游程) = 5 槽
    prefix_slots = sum(rec.run_len if hasattr(rec, "run_len") else 1 for rec in recs[:k])
    tail_only = v4_live_tail_slots(LiveTail(True, False, start, interval, projected, recs[k:], None))
    assert tail_only == full_slots[prefix_slots:]


def test_v4_live_tail_slots_open_run_forms():
    """开放游程封口形态: 无开放块 -> 块首形([int(run.start), last_seen] 端点含, n=1 单槽);
    有开放块 -> 非块首形((链终点, last_seen] 均摊, 末槽 = last_seen); n 游程 obs = None"""
    dlt, upt = 3000, 1300
    # 无开放块: 块首形, 120 槽端点含均摊 [100, 340]
    run_z = LiveTailRun(kind="z", start=100.4, last_seen=340.4, dl_total=dlt, up_total=upt, samples=120)
    slots = v4_live_tail_slots(LiveTail(False, False, None, 2, 0.0, (), run_z))
    assert len(slots) == 120
    assert slots[0].ts == 100.0 and slots[-1].ts == pytest.approx(340.4)
    assert all(s.obs == (0, 0, dlt, upt) and s.is_zero for s in slots)
    # n 游程同形: obs = None, is_zero = False
    run_n = LiveTailRun(kind="n", start=100.0, last_seen=160.0, dl_total=0, up_total=0, samples=4)
    slots_n = v4_live_tail_slots(LiveTail(False, False, None, 2, 0.0, (), run_n))
    assert [s.ts for s in slots_n] == [100.0, 120.0, 140.0, 160.0]
    assert all(s.obs is None and not s.is_zero for s in slots_n)
    # n=1 块首单槽: 槽位恰在 int(run.start)
    run_z1 = LiveTailRun(kind="z", start=100.4, last_seen=100.4, dl_total=dlt, up_total=upt, samples=1)
    slots_1 = v4_live_tail_slots(LiveTail(False, False, None, 2, 0.0, (), run_z1))
    assert len(slots_1) == 1 and slots_1[0].ts == 100.0
    # 有开放块(全落盘): 非块首形, 槽在 (projected_ts, last_seen] 均摊, 末槽 = last_seen
    run_open = LiveTailRun(kind="z", start=1000.0, last_seen=1010.0, dl_total=dlt, up_total=upt, samples=5)
    slots_open = v4_live_tail_slots(LiveTail(True, False, 900, 30, 1000.0, (), run_open))
    assert [s.ts for s in slots_open] == [1002.0, 1004.0, 1006.0, 1008.0, 1010.0]
    assert all(s.obs == (0, 0, dlt, upt) and s.is_zero for s in slots_open)
    # 有开放块且块全量未落盘: 游程链锚点 = 整块重算游标终值(链式接续)
    recs = _s6_mixed_records(30)
    full_slots = v4_block_slots(V4Block(1_800_000_000, 30, 1000, 500, recs))
    chain_end = full_slots[-1].ts
    run_at_chain = LiveTailRun(
        kind="z", start=chain_end, last_seen=chain_end + 10, dl_total=dlt, up_total=upt, samples=5
    )
    tail = LiveTail(True, True, 1_800_000_000, 30, chain_end, recs, run_at_chain)
    slots_both = v4_live_tail_slots(tail)
    assert slots_both[:len(full_slots)] == full_slots
    assert [s.ts for s in slots_both[len(full_slots):]] == [chain_end + 2.0 * k for k in range(1, 6)]


def test_v4_live_tail_slots_invariants_fail_fast():
    """invariant 拦截: block_open=False 携带 records / head_pending -> ValueError;
    未知记录型 -> TypeError(发布侧单点保证, 读侧 tripwire)"""
    with pytest.raises(ValueError):
        v4_live_tail_slots(LiveTail(False, False, None, 30, 0.0, (V4Sample(1, 1, 1, 1), ), None))
    with pytest.raises(ValueError):
        v4_live_tail_slots(LiveTail(False, True, None, 30, 0.0, (), None))
    with pytest.raises(TypeError):
        v4_live_tail_slots(LiveTail(True, False, 100, 30, 100.0, ("bad", ), None))


def test_v4_block_slots_first_run_single_slot_nominal_spacing():
    """块首单槽游程(run_len=1, 带 dt 列): 槽位 = B.start、槽距落标称 interval(单槽无均摊
    语义)—— 变异面: 均摊式打到 run_len-1 = 0 除零崩读路径。写侧现网不产该形态(块首单槽
    游程不写 dt), 本守阵钉解析产物可算性契约(解析侧放行 7 列 z 行)"""
    block = V4Block(1000, 30, None, None, (V4ZeroRun(1, 500, 300, dt_ms=5000), ))
    slots = v4_block_slots(block)
    assert [s.ts for s in slots] == [1000.0]
    assert slots[0].dt_s == 30 and slots[0].is_zero and slots[0].obs == (0, 0, 500, 300)


def test_v4_live_tail_slots_open_run_edge_spans():
    """开放游程封口形态的边缘跨度: 非块首形 0 < span <= 1 按实测 span 均摊(不落标称
    interval —— 1s 档现实可达); 块首形 n=2 端点含均摊(两槽落 int(start) 与 last_seen,
    dt_s = span 非标称); 块首形 n=1 单槽 dt_s = 标称 interval(非 1.0)"""
    dlt, upt = 3000, 1300
    # 非块首形 span = 1s(interval = 30): spacing = 0.5, 末槽 = last_seen
    run_span1 = LiveTailRun(kind="z", start=1000.0, last_seen=1001.0, dl_total=dlt, up_total=upt, samples=2)
    slots = v4_live_tail_slots(LiveTail(True, False, 900, 30, 1000.0, (), run_span1))
    assert [s.ts for s in slots] == [1000.5, 1001.0]
    assert all(s.dt_s == 0.5 and s.obs == (0, 0, dlt, upt) and s.is_zero for s in slots)
    # 块首形 n=2: spacing = span/(n-1) = 60(链锚点 = int(run.start)), dt_s = spacing(非标称)
    run_n2 = LiveTailRun(kind="z", start=100.0, last_seen=160.0, dl_total=dlt, up_total=upt, samples=2)
    slots2 = v4_live_tail_slots(LiveTail(False, False, None, 2, 0.0, (), run_n2))
    assert [s.ts for s in slots2] == [100.0, 160.0]
    assert all(s.dt_s == 60.0 for s in slots2)
    # 块首形 n=1: 单槽 dt_s = 标称 interval(spacing 0.0 短路到 interval)
    run_n1 = LiveTailRun(kind="z", start=100.4, last_seen=100.4, dl_total=dlt, up_total=upt, samples=1)
    slots1 = v4_live_tail_slots(LiveTail(False, False, None, 2, 0.0, (), run_n1))
    assert len(slots1) == 1 and slots1[0].ts == 100.0 and slots1[0].dt_s == 2


def test_v4_live_tail_slots_zero_and_negative_span_forms():
    """开放游程封口的病态跨度(W4 live_101/103/128): 同秒病态(span == 0)与时钟回拨
    (last_seen < 链锚点)—— 非块首封口回落标称 interval 均摊(dt_s = interval, 槽位按
    interval 展开); 块首封口槽位收拢 int(start), dt_s 仍落标称 interval(max 钳到 0)"""
    dlt, upt = 3000, 1300
    # 非块首形 span == 0(last_seen == 写侧游标): spacing 落标称 interval(不落 0)
    run0 = LiveTailRun(kind="z", start=900.0, last_seen=1000.0, dl_total=dlt, up_total=upt, samples=2)
    slots = v4_live_tail_slots(LiveTail(True, False, 900, 30, 1000.0, (), run0))
    assert [s.ts for s in slots] == [1030.0, 1060.0]
    assert all(s.dt_s == 30 and s.is_zero for s in slots)
    # 非块首形时钟回拨(last_seen < 写侧游标): 同回落标称 interval
    run_back = LiveTailRun(kind="z", start=900.0, last_seen=970.0, dl_total=dlt, up_total=upt, samples=2)
    slots_b = v4_live_tail_slots(LiveTail(True, False, 900, 30, 1000.0, (), run_back))
    assert [s.ts for s in slots_b] == [1030.0, 1060.0]
    assert all(s.dt_s == 30 for s in slots_b)
    # 块首形 span == 0(start == last_seen)且 n = 2: 槽位收拢 int(start), dt_s 落标称 interval
    run_flat = LiveTailRun(kind="z", start=100.0, last_seen=100.0, dl_total=dlt, up_total=upt, samples=2)
    slots_f = v4_live_tail_slots(LiveTail(False, False, None, 30, 0.0, (), run_flat))
    assert [s.ts for s in slots_f] == [100.0, 100.0]
    assert all(s.dt_s == 30 for s in slots_f)
    # 块首形时钟回拨(last_seen < start): max 钳到 0 -> 同 span == 0 形态
    run_flat_b = LiveTailRun(kind="z", start=100.0, last_seen=70.0, dl_total=dlt, up_total=upt, samples=2)
    slots_fb = v4_live_tail_slots(LiveTail(False, False, None, 30, 0.0, (), run_flat_b))
    assert [s.ts for s in slots_fb] == [100.0, 100.0]
    assert all(s.dt_s == 30 for s in slots_fb)


def test_v4_live_tail_slots_pure_restoration_no_hold_extension():
    """(改写自旧持有族 6 例; 26-11-18-0037 T1c-2)槽位复原无持有延伸: 活跃链/z 游程/
    停滞过界/断连各形态的复原输出 = 纯真实样本槽序(末槽 = 末真实样本), 与「请求 now
    距链端多远」完全无关 —— 旧面「now 超链端且间隙有界时追加 holding 槽」不存在,
    新契约尾组 = 最新样本恒真值无克隆(§03), 停滞/断连不造点(诚实)"""
    interval = 30
    start = 1_800_000_000
    # 形态一: 活跃链(r 记录收尾)
    recs = (V4Sample(100, 50, 1000, 500), V4Sample(200, 70, 2000, 800), V4Sample(150, 60, 2600, 1100))
    projected = v4_block_slots(V4Block(start, interval, 1000, 500, recs))[-1].ts
    tail = LiveTail(True, False, start, interval, projected, recs, None)
    base = v4_live_tail_slots(tail)
    assert len(base) == 3 and base[-1].ts == projected and not base[-1].is_zero
    assert base[-1].obs == (150, 60, 2600, 1100)
    # 形态二: z 游程收尾(末槽 0 速率真实观测, 非持有克隆)
    recs_z = (V4Sample(100, 50, 1000, 500), V4ZeroRun(3, 1000, 500))
    projected_z = v4_block_slots(V4Block(start, interval, 1000, 500, recs_z))[-1].ts
    tail_z = LiveTail(True, False, start, interval, projected_z, recs_z, None)
    base_z = v4_live_tail_slots(tail_z)
    assert base_z[-1].is_zero and base_z[-1].obs == (0, 0, 1000, 500) and base_z[-1].ts == projected_z
    # 形态三: 断连 —— 记录链以 n 游程收尾(末槽 obs = None, 诚实断线不造点)
    recs_n = (V4Sample(100, 50, 1000, 500), V4NullRun(2))
    projected_n = v4_block_slots(V4Block(start, interval, 1000, 500, recs_n))[-1].ts
    tail_n = LiveTail(True, False, start, interval, projected_n, recs_n, None)
    base_n = v4_live_tail_slots(tail_n)
    assert base_n[-1].obs is None and base_n[-1].ts == projected_n
    # 形态四: 开放 n 游程(qB 断连未恢复, 活尾只剩断连游程)
    run_n = LiveTailRun(kind="n", start=start + 60.0, last_seen=start + 120.0, dl_total=0, up_total=0, samples=4)
    tail_open_n = LiveTail(True, False, start, interval, start + 60.0, (), run_n)
    base_open = v4_live_tail_slots(tail_open_n)
    assert base_open and base_open[-1].obs is None
    # 停滞/断连形态复原恒等: 输出只依赖快照面(无 now 判据可依赖 —— 镜像保证不漂);
    # is_hold 字段已退役(hasattr 恒假 —— 变异加回字段即红)
    assert all(not hasattr(s, "is_hold") for s in base + base_z + base_n + base_open)


def test_v4_live_tail_slots_signature_no_hold_params():
    """(持有延伸形参面退役的 poka-yoke)v4_live_tail_slots 签名无 now/max_gap_s
    (inspect 单点 —— 变异加回形参面即红); 传参即 TypeError(旧 fail-fast 校验面随形参
    退役, 无参复原无垃圾入参面)"""
    import inspect

    sig = inspect.signature(v4_live_tail_slots)
    assert list(sig.parameters) == ["tail"], sig
    start = 1_800_000_000
    tail = LiveTail(True, False, start, 30, start + 60.0, (V4Sample(1, 1, 1, 1), ), None)
    with pytest.raises(TypeError):
        v4_live_tail_slots(tail, now=start + 61.0)  # type: ignore[misc]
    with pytest.raises(TypeError):
        v4_live_tail_slots(tail, now=start + 61.0, max_gap_s=5.0)  # type: ignore[misc]


# ======================================================================
# 槽位数学双形态等价(自 test_traffic_grid_bucket_cache 迁入, 26-11-18-0037 T1c-2:
# 桶值缓存退役后该电池只留 _SeriesWriter 仿真器与本守阵, 槽位数学守阵归位 slots 电池)
# ======================================================================


def test_block_slots_from_full_equivalence():
    """v4_block_slots_from 与 v4_block_slots 双形态等价: 全量/游标分段链式/游程中段截停。"""
    rng = random.Random(42)
    t0 = 1_000_000
    for trial in range(60):
        recs = []
        cur = t0
        dl = up = 500
        for _ in range(rng.randrange(1, 14)):
            kind = rng.random()
            if kind < 0.45:
                dt = rng.choice([None, 2000, 1379, 3100])
                dr, ur = rng.randrange(0, 5000), rng.randrange(0, 5000)
                recs.append(("r", dr, ur, dt))
                cur += (dt / 1000.0) if dt else 2.0
            elif kind < 0.8:
                n = rng.randrange(1, 9)
                dt = rng.choice([None, n * 2000, 12345])
                recs.append(("z", n, dl, dt))
                cur += (dt / 1000.0) if dt else n * 2.0
            else:
                n = rng.randrange(1, 5)
                dt = rng.choice([None, n * 2000])
                recs.append(("n", n, None, dt))
                cur += (dt / 1000.0) if dt else n * 2.0
        # 落成 V4Block(绝对 totals; 序列化不做 —— 槽位数学与基线无关)
        blk_recs = []
        base = (dl, up) = (rng.randrange(0, 10**6), rng.randrange(0, 10**6))
        for rec in recs:
            if rec[0] == "r":
                dl += rng.randrange(0, 100)
                up += rng.randrange(0, 100)
                blk_recs.append(V4Sample(rng.randrange(0, 9000), rng.randrange(0, 9000), dl, up, rec[3]))
            elif rec[0] == "z":
                blk_recs.append(V4ZeroRun(rec[1], dl, up, rec[3]))
            else:
                blk_recs.append(V4NullRun(rec[1], rec[3]))
        blk = V4Block(t0, 2.0, base[0], base[1], tuple(blk_recs))
        full = v4_block_slots(blk)
        got, cur2, exhausted = v4_block_slots_from(blk, (0, 0, None, None, None), None)
        assert got == full and exhausted
        # 游标分段链式: t1 逐次右移(落在槽位之间), 拼接 == 全量
        cuts = sorted(rng.sample([s.ts + 0.3 for s in full], k=min(4, len(full))))
        chunks = []
        cursor = (0, 0, None, None, None)
        for c in cuts:
            part, cursor, exhausted = v4_block_slots_from(blk, cursor, c)
            chunks.extend(part)
        part, cursor, exhausted = v4_block_slots_from(blk, cursor, None)
        chunks.extend(part)
        assert tuple(chunks) == full, trial
        assert exhausted


def test_v4_z_ramp_element_matches_ramp_and_run_geometry():
    """B2 闭合式单点守阵(plan 26-11-21-1546 S1): v4_z_ramp_element 与 v4_z_totals_ramp
    逐元素相等(随机入参全域: 端点/退化末端/单槽/奇偶 n), v4_run_geometry 与
    v4_block_slots 的 spacing/base 推导逐位一致(块首/非块首 x 显式/标称 dt)——
    闭合式入账与逐槽展开的公式同源不漂移"""
    rng = random.Random("b2-element-geometry")
    for _ in range(300):
        dl_open, up_open = rng.randrange(0, 10**12), rng.randrange(0, 10**12)
        n = rng.choice([1, 2, 3, 4, 5, 7, 8, 120, 240, 86400])
        dl_end = rng.choice([None, dl_open, dl_open + rng.randrange(0, 10**9), dl_open - 1])
        up_end = rng.choice([None, up_open, up_open + rng.randrange(0, 10**9), up_open - 1])
        ramp = v4_z_totals_ramp(dl_open, up_open, dl_end, up_end, n)
        assert len(ramp) == max(n, 0)
        for k in range(len(ramp)):
            assert v4_z_ramp_element(dl_open, up_open, dl_end, up_end, n, k) == ramp[k], (n, k)
        # 端点精确(v4_z_totals_ramp 契约): v_0 = S0, v_{n-1} = 逐向解析的 S1(退化取 S0)
        if n >= 2:
            dl1 = dl_open if (dl_end is None or dl_end < dl_open) else dl_end
            up1 = up_open if (up_end is None or up_end < up_open) else up_end
            assert ramp[0] == (dl_open, up_open) and ramp[-1] == (dl1, up1)
    for _ in range(200):
        interval = rng.choice([1.0, 1.5, 2.0, 30.0])
        n = rng.choice([1, 2, 3, 5, 40, 240])
        dt = rng.choice([None, rng.randrange(1000, 86400000)])
        rec = V4ZeroRun(n, 1000, 2000, dt) if rng.random() < 0.5 else V4NullRun(n, dt)
        for head in (True, False):
            spacing, base = v4_run_geometry(rec, interval, head)
            if head:
                # 单记录块 = 块首规则: 首槽恰在 B.start, base = 0
                blk = V4Block(
                    1_780_000_000, interval, None if isinstance(rec, V4NullRun) else 1000,
                    None if isinstance(rec, V4NullRun) else 2000, (rec, )
                )
                slots = v4_block_slots(blk)
                assert base == 0.0 and slots[0].ts == 1_780_000_000
                for k, slot in enumerate(slots):
                    assert slot.ts == 1_780_000_000 + base + spacing * k, (n, dt, head, k)
                    assert slot.dt_s == spacing, (n, dt, head)
            else:
                # 非块首规则: 前置一条块首 r(零推进锚点 = B.start), 游程槽 = fl(B.start + spacing*k)
                r = V4Sample(100, 50, 1000, 2000)
                blk = V4Block(1_780_000_000, interval, 1000, 2000, (r, rec))
                slots = v4_block_slots(blk)
                assert base == spacing
                run_slots = slots[1:]
                assert slots[0].ts == 1_780_000_000  # 块首 r 槽位恰在 B.start(零推进)
                for k, slot in enumerate(run_slots):
                    assert slot.ts == 1_780_000_000 + base + spacing * k, (n, dt, head, k)
                    assert slot.dt_s == spacing, (n, dt, head)
