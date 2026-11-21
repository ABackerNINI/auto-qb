"""test_traffic_store_agg 测试计划: qB 口径流量 v4 存储层(plan 26-10-05-2200 §01-§05; v1/v2/v3 退役面已随各代删除)

## 测试计划(每个测试函数一条)
handler 接线(S2a, v4 写侧):

v4 纯函数区(B1 立并于批 2 接线, plan 26-10-05-2200 §01):
- test_v4_agg_roundtrip_and_legacy_8col: agg.dat roundtrip + 8 列旧行兜底 cov_s=3600(防御性保留)
- test_v4_agg_parse_cov_floor_one_bad_line: 解析侧 cov_s 下限 1(issue 26-10-30-0622, 与写侧
  v4_hour_agg 契约对齐)—— cov_s=0/-1 按坏行整行跳过, cov_s=1 边界合法, 8 列旧行兜底不受影响,
  解析产物 rollup 上卷恒可(恢复路径回归)
- test_v4_hour_agg_dt_weighted_degenerate_to_v2: dt 加权 hour 聚合, 等间隔退化公式对照钉住
- test_v4_hour_agg_subsecond_coverage_floors_cov_to_one: 亚秒覆盖桶 cov_s 下限 1(行存在即有覆盖)——
  迟到补记重封桶的亚秒残余覆盖不再折 0, hour->day->month 逐级链恒可上卷(2026-10-13 真机
  「逐级聚合无有效覆盖」回归); 零覆盖(无观测)仍 fail-fast; avg 仍按 float cov 加权
- test_v4_rollup_strict_level_by_level: 逐级派生 day/month
- test_v4_merge_agg_same_epoch_reseal_keeps_coverage: 同 epoch 重封合流 —— 迟到补记把已封桶
  重建再封时 cov 相加(非取残余), avg 按 cov 加权 / totals 取后封行 / 桶宽截断 / 异 kind-epoch
  fail-fast(2026-10-13 真机「重封替换丢覆盖」回归)
- test_v4_merge_agg_zero_cov_fail_closed: 合流 cov<=0 fail-closed(issue 26-10-30-0622,
  同 v4_rollup_agg 守卫)—— 双行零 cov 除零兜底, 单边零 cov 合法

v4 写侧存储(S2a/S2b, TrafficV4Store):

v4 读侧解析缓存(S3a/S3b, V4DayCache):

体量实测(plan 26-10-04-1957 §09.1 口径沿用到 v4):

v4 活尾快照(S6 验收):

v4 定约专测(B1 用例, 批 2 回归):

P1-T1.2 守卫与容错簇(计划 26-10-20-2101, 覆盖率缺口清偿):
- test_v4_next_month_epoch_steps_and_wraps: 逐月推进(12 月跨年 / 常规月)且严格大于输入
- test_v4_merge_agg_month_bucket_width: _agg_width_s 月行桶宽(32 天后的月界实算 + 28 天保底;
  2 月恰落保底线 / 31 天月按实宽), hour/day 桶宽不变

mut-core W4 S5 定向补测(变异审计确认真洞守阵, 2026-10-31; 红验 tmp-analysis/redverify-s5-w4.py):
- test_v4_merge_agg_day_cov_capped_at_86400: width_5/6 —— day 行合流 cov 上限 = 当日宽(86400)

mut-core W4 S6 定向补测(2026-11-02, issue 26-10-31-1539 两件清偿; 红验 tmp-analysis/redverify-s6-w4.py):

在线聚合封口防线单元(S4 缺口收口 26-11-17):
- test_acc_upsert_row_same_epoch_replace_else_append: 累计器行表同 epoch 原位替换 /
  无此 epoch 追加(不得产生同 epoch 重复行)
- test_agg_reseal_closed_day_stub_first_write_and_month_mismatch: 已关日迟到重封 ——
  存根无此小时追加首写(354)/ 有此小时合流替换(对照)/ 月层都不匹配日行落盘月层
  零动作(361->exit, 背日不级联翻月)

D12 折叠态对拍守阵(plan 26-11-21-1546 S1/D12; 等价判据 D2 + 浮点序不变量 R2):
- test_hour_fold_seal_bitwise_matches_v4_hour_agg_random_credits: 随机信用序列三路对拍
  (列表路径 v4_hour_agg / fold 全序列逐笔 merge / settled 拷贝 + 合成段按原序 merge 的
  活尾组合序)AggRow bitwise 相等 + format_agg_row 9 列文本逐位 —— R2 场景: dt_s 取
  dt_ms/1000 二进制不精确值(亚秒残余/恰满一小时/超一小时大段), 零速率/零 dt 退化笔,
  Σdt > 3600 截断
- test_hour_fold_reseal_matches_list_and_seal_is_readonly: 同 epoch 桶重开续接时序对拍
  (A 段 seal -> B 段续 merge -> 再 seal, 与列表版逐轮 bitwise 一致)+ seal 只读不变式
- test_hour_fold_degenerate_inputs_parity: 退化值钉面(负速率 max 首笔立基线与列表 max
  逐位一致 / totals 恒取末笔 / 全零速率桶)
- test_hour_fold_error_and_boundary_parity: 空桶/零覆盖 ValueError 逐条对齐列表路径 +
  cov 边界(亚秒下限 1 / Σdt > 3600 截断 / 恰 3600 / 整值不回归)

线程/时钟纪律: 需要确定时刻的用例经 monkeypatch 固定 time.time(测试进程内单线程, 恢复由
monkeypatch 保证); 文件一律落在 tmp_path(test.* 已内置 TMPDIR, 不手工加前缀)。
"""

import builtins

import inspect

import logging

import os

import random

import re

import tempfile

import threading

import time

from datetime import datetime

import pytest

import auto_qb.core.traffic_store as traffic_store_module

from auto_qb.config import QbTraffic

from auto_qb.core.modules.traffic_sample_mod import GLOBAL_SERIES_KEY, HourFold

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
    _agg_row,
    _v4_day_text,
)


def test_v4_agg_roundtrip_and_legacy_8col():
    """agg.dat roundtrip(§02.2): hour/day/month 9 列混存解析按 kind 分列升序 / 同 epoch
    重复取最后一行 / 8 列旧行兜底 cov_s=3600 / format_agg_row 逐列往返 / 非法 kind fail-fast"""
    text = _v4_day_text(
        [
            HEADER_LINE_V4,
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
    parsed = parse_v4_agg_text(text)
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
    reparsed = parse_v4_agg_text(_v4_day_text([HEADER_LINE_V4, format_agg_row(row)]))
    assert reparsed.days == (row, ) and reparsed.bad_lines == 0
    # 非法 kind fail-fast; 9 字段(kind + 8)整行恰合, 10 字段计坏
    with pytest.raises(ValueError):
        format_agg_row(AggRow("week", 1, 1, 1, 1, 1, 1, 1, 1))
    bad = parse_v4_agg_text(_v4_day_text([HEADER_LINE_V4, "hour,1,1,1,1,1,1,1,1,1"]))
    assert bad.bad_lines == 1 and bad.hours == ()


def test_v4_agg_parse_cov_floor_one_bad_line():
    """解析侧 cov_s 下限 1(issue 26-10-30-0622, 与写侧 v4_hour_agg 契约对齐): cov_s=0
    语义非法行按坏行整行跳过(负值本就计坏), 好行不受牵连; 8 列旧行兜底不受影响;
    解析产物全部 cov_s >= 1 -> rollup(v4_rollup_agg)的 Σcov > 0 前置在恢复路径上恒成立"""
    text = _v4_day_text(
        [
            HEADER_LINE_V4,
            "key,torrent:ABC",
            "hour,1000,10,20,5,8,100,200,0",  # cov_s = 0: 写侧不产出的语义非法行 -> 坏行
            "hour,2000,11,21,6,9,110,210,-1",  # 负值: _parse_nn_int 拒 -> 坏行
            "hour,3000,12,22,7,10,120,220,1",  # 下限边界: cov_s = 1 合法
            "day,86400,1,1,1,1,1,1,0",  # day 行同口径
        ]
    )
    parsed = parse_v4_agg_text(text)
    assert parsed.bad_lines == 3 and parsed.data_lines == 5  # 三条非法行(hour x2 + day)全计坏
    assert parsed.hours == (AggRow("hour", 3000, 12, 22, 7, 10, 120, 220, 1), )
    assert parsed.days == ()  # cov_s=0 的 day 行同样按坏行拦下
    # 8 列旧行兜底 cov_s = 3600 不受下限影响
    legacy = parse_v4_agg_text(_v4_day_text([HEADER_LINE_V4, "hour,1000,9,19,4,7,90,190"]))
    assert legacy.hours[0].cov_s == 3600 and legacy.bad_lines == 0
    # 恢复路径回归: 全零 cov 子行不再能到达 v4_rollup_agg(坏行已拦), 逐级聚合正常上卷
    day = v4_rollup_agg("day", 86400, parsed.hours)
    assert day.cov_s == 1


def test_v4_hour_agg_dt_weighted_degenerate_to_v2():
    """dt 加权 hour 聚合(§04.1): avg = round(Σ(rate x dt)/cov) / cov 上界 3600 /
    totals 级末快照 / dt_i 恒等 interval_s 时严格退化为等间隔均值公式 round(Σrate/n)
    (对照断言钉住) / 空样本与零覆盖 fail-fast"""
    h0 = 36_000
    # 退化形态: dt_i 恒 = 30s, 120 样本恰满 1h -> 与等间隔均值公式(v2 纯活跃桶口径)逐列一致
    rates = [100 + i for i in range(120)]
    up_rates = [50 + i for i in range(120)]
    samples = tuple(
        V4HourSample(dl_rate=dl, up_rate=up, dl_total=1000 + i, up_total=2000 + i, dt_s=30.0)
        for i, (dl, up) in enumerate(zip(rates, up_rates))
    )
    agg = v4_hour_agg(h0, samples)
    assert agg.dl_avg == int(round(sum(rates) / 120))  # 退化: = round(Σ(rate x dt) / (n x dt)) = 等间隔均值
    assert agg.cov_s == 3600 and agg.dl_max == rates[-1] and agg.up_max == up_rates[-1]
    assert (agg.dl_total, agg.up_total) == (1000 + 119, 2000 + 119)  # totals = 级末快照
    # dt 加权(非均匀): 2 样本各 1800s
    half = v4_hour_agg(h0, (V4HourSample(100, 50, 1, 2, 1800.0), V4HourSample(300, 150, 3, 4, 1800.0)))
    assert (half.dl_avg, half.up_avg) == (200, 100) and half.cov_s == 3600
    # cov 上界: Σdt > 3600 裁到 3600
    clamped = v4_hour_agg(h0, (V4HourSample(100, 50, 1, 2, 2000.0), V4HourSample(300, 150, 3, 4, 2000.0)))
    assert clamped.cov_s == 3600 and clamped.dl_avg == int(round((100 * 2000 + 300 * 2000) / 3600))
    # fail-fast: 空样本 / 零覆盖
    with pytest.raises(ValueError):
        v4_hour_agg(h0, ())
    with pytest.raises(ValueError):
        v4_hour_agg(h0, (V4HourSample(1, 1, 1, 1, 0.0), ))


def test_v4_hour_agg_subsecond_coverage_floors_cov_to_one():
    """亚秒覆盖桶 cov_s 下限 1(§04.1 不变量「行存在即有覆盖」, 2026-10-13 真机
    「逐级聚合无有效覆盖」回归): 迟到补记重封的桶只带跨小时界亚秒残余覆盖, round 把它
    折 0 会让 day/month 封口的 v4_rollup_agg 失掉 Σcov_s > 0 前置条件 -> 逐级链恒可
    上卷; cov == 0(无观测)仍 fail-fast; cov_s 是落盘/上卷的度量, avg 仍按 float cov 加权"""
    h0 = 36_000
    tiny = v4_hour_agg(h0, (V4HourSample(100, 50, 1000, 500, 0.263), ))  # 0.263s = 真机实测残余
    assert tiny.cov_s == 1  # round(0.263) = 0 -> 下限 1 兜住
    assert (tiny.dl_avg, tiny.up_avg, tiny.dl_total, tiny.up_total) == (100, 50, 1000, 500)
    # (0, 0.5] 全带内: 0.5 恰在 round 的银行家舍入边界, 同样须为 1
    assert [v4_hour_agg(h0, (V4HourSample(1, 1, 1, 1, dt), )).cov_s for dt in (0.001, 0.263, 0.5)] == [1, 1, 1]
    # 既有整值形态不受下限影响(不回归已落盘数字)
    assert v4_hour_agg(h0, (V4HourSample(1, 1, 1, 1, 3597.0), )).cov_s == 3597
    assert v4_hour_agg(h0, (V4HourSample(1, 1, 1, 1, 3600.0), )).cov_s == 3600
    # 逐级链回归(报错路径): Σcov_s 不再为 0 -> day 可上卷, day 行再上卷 month
    day = v4_rollup_agg("day", 0, (tiny, ))
    assert (day.cov_s, day.dl_avg, day.dl_total) == (1, 100, 1000)
    month = v4_rollup_agg("month", 0, (day, ))
    assert (month.cov_s, month.dl_avg) == (1, 100)
    # 下限只兜「有覆盖」: 零覆盖(无观测)仍 fail-fast
    with pytest.raises(ValueError):
        v4_hour_agg(h0, (V4HourSample(1, 1, 1, 1, 0.0), ))


def test_v4_merge_agg_same_epoch_reseal_keeps_coverage():
    """同 epoch 重封合流(§04.2, 2026-10-13 真机「重封替换丢覆盖」回归): 迟到补记把已封桶
    重建又再封一次时, 合流后 cov = 两段之和(不是「取残余」), avg 按各自 cov 加权 / max 取大
    / totals 取后封行(时刻更晚的快照) / cov 截到行型桶宽; kind/epoch 不一致 fail-fast"""
    prev = AggRow("hour", 100, 100, 200, 50, 80, 1000, 2000, 1838)  # 先到的那部分覆盖
    late = AggRow("hour", 100, 300, 400, 90, 160, 1100, 2100, 1762)  # 24h 后才封口的空闲段补记
    m = v4_merge_agg(prev, late)
    assert m.cov_s == 1838 + 1762  # 真机形态: 两段相加恰满一小时(替换语义只留 1762)
    assert m.dl_avg == int(round((100 * 1838 + 300 * 1762) / 3600))  # cov 加权, 非任一侧
    assert m.dl_max == 400 and m.up_max == 160
    assert (m.dl_total, m.up_total) == (1100, 2100)  # 后封行 = 时刻更晚的累计快照
    assert v4_merge_agg(m, AggRow("hour", 100, 1, 1, 1, 1, 1200, 2200, 900)).cov_s == 3600  # 桶宽截断
    d1 = AggRow("day", 86400, 100, 100, 100, 100, 1, 1, 40000)
    d2 = AggRow("day", 86400, 200, 200, 200, 200, 2, 2, 46400)
    assert v4_merge_agg(d1, d2).cov_s == 86400  # day 行同构(cov = 40000 + 46400 截到当日)
    with pytest.raises(ValueError):
        v4_merge_agg(prev, AggRow("day", 100, 1, 1, 1, 1, 1, 1, 1))
    with pytest.raises(ValueError):
        v4_merge_agg(prev, AggRow("hour", 200, 1, 1, 1, 1, 1, 1, 1))


def test_v4_merge_agg_zero_cov_fail_closed():
    """合流 cov <= 0 fail-closed(issue 26-10-30-0622, 同 v4_rollup_agg 断言式守卫):
    双行 cov 全零时加权除法是除零 —— 解析侧 cov_s 下限 1 后正常输入到不了这里,
    守卫只对绕过解析的语义非法输入兜底; 单边零 cov 合法(等效另一侧原样加权)"""
    zero = AggRow("hour", 100, 100, 200, 50, 80, 1000, 2000, 0)
    with pytest.raises(ValueError):
        v4_merge_agg(zero, AggRow("hour", 100, 300, 400, 90, 160, 1100, 2100, 0))
    # 单边零 cov: cov = 0 + 1762 > 0, 合法(另一侧加权口径)
    live = AggRow("hour", 100, 300, 400, 90, 160, 1100, 2100, 1762)
    m = v4_merge_agg(zero, live)
    assert m.cov_s == 1762 and m.dl_avg == 300 and m.dl_total == 1100


def test_v4_rollup_strict_level_by_level():
    """逐级派生(§04.1): day 从 hour 行 / month 从 day 行 —— avg 按 cov 加权 /
    max 取下级最大 / totals 级末快照(epoch 最大下级行) / cov = Σ下级.cov;
    kind 限 day/month(严格逐级, day 不从 raw 直聚)与空下级/零覆盖 fail-fast"""
    h1 = AggRow("hour", 100, 100, 150, 50, 80, 1000, 2000, 3600)
    h2 = AggRow("hour", 4600, 200, 250, 100, 160, 1100, 2100, 1800)
    day = v4_rollup_agg("day", 0, (h1, h2))
    # avg = (100x3600 + 200x1800)/5400 = 133.33 -> 133; up = (50x3600 + 100x1800)/5400 = 66.67 -> 67
    assert day == AggRow("day", 0, 133, 250, 67, 160, 1100, 2100, 5400)
    d2 = AggRow("day", 86_400, 0, 0, 0, 0, 1200, 2200, 7200)
    month = v4_rollup_agg("month", 100, (day, d2))
    # avg = (133x5400 + 0x7200)/12600 = 57; up = (67x5400)/12600 = 28.7 -> 29; totals = 级末(d2)
    assert month == AggRow("month", 100, 57, 250, 29, 160, 1200, 2200, 12_600)
    # fail-fast: hour 不可逐级派生 / 空下级 / 零覆盖
    with pytest.raises(ValueError):
        v4_rollup_agg("hour", 1, (day, ))
    with pytest.raises(ValueError):
        v4_rollup_agg("day", 1, ())
    with pytest.raises(ValueError):
        v4_rollup_agg("day", 1, (AggRow("hour", 1, 1, 1, 1, 1, 1, 1, 0), ))


def test_v4_next_month_epoch_steps_and_wraps():
    """v4_next_month_epoch(S3b 逐月铺格): 常规月 -> 次月 1 日 00:00; 12 月跨年 -> 次年 1 月;
    结果严格大于输入(逐月推进必终止)"""
    mid = int(datetime(2026, 10, 20, 13, 45).timestamp())
    assert v4_epoch_date_str(v4_next_month_epoch(mid)) == "2026-11-01"
    assert v4_next_month_epoch(mid) > mid
    dec = int(datetime(2026, 12, 31, 23, 59).timestamp())
    assert v4_epoch_date_str(v4_next_month_epoch(dec)) == "2027-01-01"
    assert v4_next_month_epoch(dec) > dec


def test_v4_merge_agg_month_bucket_width():
    """_agg_width_s 月行桶宽(同 epoch 合流的 cov 上限): 「32 天后的月界」实算并保底 28 天 ——
    2 月(28 天)恰落保底线, 31 天月按实宽截断; hour/day 桶宽恒定(不受 epoch 影响)"""
    feb = v4_month_epoch(v4_date_str_epoch("2026-02-10"))
    merged = v4_merge_agg(_agg_row("month", feb, cov=20 * 86400), _agg_row("month", feb, cov=20 * 86400))
    assert merged.cov_s == 28 * 86400  # 40 天 > 2 月实宽 28 天 -> 截到保底线
    jul = v4_month_epoch(v4_date_str_epoch("2026-07-10"))
    merged = v4_merge_agg(_agg_row("month", jul, cov=20 * 86400), _agg_row("month", jul, cov=20 * 86400))
    assert merged.cov_s == 31 * 86400  # 31 天月按实宽
    day = v4_day_epoch(v4_date_str_epoch("2026-02-10"))
    assert v4_merge_agg(_agg_row("day", day, cov=HOUR), _agg_row("day", day, cov=HOUR)).cov_s == 2 * HOUR
    hour = _agg_row("hour", 1000, cov=1800)
    assert v4_merge_agg(hour, _agg_row("hour", 1000, cov=1800)).cov_s == HOUR  # 3600 上限


def test_v4_merge_agg_day_cov_capped_at_86400():
    """day 行同 epoch 迟到补记合流的桶宽上限(§04.1 合流只补缺口): 双行 cov 超出当日宽截到
    86400 —— 变异面: day 行误落 month 支(宽 >= 28 天), 合流 cov 虚增重复计覆盖(真机已证
    hour 级同形态合流现实发生)"""
    day0 = v4_day_epoch(_S2B_H0)
    prev = _agg_row("day", day0, dl_avg=10, cov=60_000)
    late = _agg_row("day", day0, dl_avg=30, cov=40_000)
    m = v4_merge_agg(prev, late)
    assert m.kind == "day" and m.cov_s == 86_400  # 上限 = 当日宽(非 28 天起的月宽)
    assert m.dl_avg == int(round((10 * 60_000 + 30 * 40_000) / 100_000))  # 加权均值不受截断影响


# ======================================================================
# 在线聚合封口防线单元(S4 缺口收口, 26-11-17)
# ======================================================================


def test_acc_upsert_row_same_epoch_replace_else_append():
    """(缺口收口)累计器/存根行表的同 epoch 替换单点(_acc_upsert_row): 已有行同
    epoch = 原位替换(重封行覆盖旧行, 不追加重复行), 无此 epoch = 追加(首写)——
    迟到重封与首写两形态都不得产生同 epoch 重复行(读侧按「同 epoch 取最后一行」
    解析, 重复行 = 行表无序化)。"""
    from auto_qb.core.modules.traffic_sample_agg import _SampleAggMixin
    from auto_qb.core.traffic_store_paths import v4_day_epoch

    d0 = v4_day_epoch(1_800_000_000)
    row0 = AggRow("hour", d0, 1, 1, 1, 1, 1, 1, 3600)
    rows = [row0]
    _SampleAggMixin._acc_upsert_row(rows, AggRow("hour", d0 + HOUR_SECONDS, 9, 9, 9, 9, 9, 9, 3600))
    assert len(rows) == 2 and rows[-1].epoch == d0 + HOUR_SECONDS  # 无此 epoch -> 追加
    repl = AggRow("hour", d0, 5, 5, 5, 5, 5, 5, 3600)
    _SampleAggMixin._acc_upsert_row(rows, repl)
    assert len(rows) == 2 and rows[0] is repl  # 同 epoch -> 原位替换(对象同一, 非尾部追加)


def test_agg_reseal_closed_day_stub_first_write_and_month_mismatch():
    """(缺口收口)已关日 hour 迟到重封的存根合流面(_agg_reseal_closed_day, issue
    26-11-07-0527 R1#63): 存根无此小时(此前整点无行)= 追加首写(354)而非合流 ——
    修复前残余行未经合流直接落盘被读侧「同 epoch 取最后一行」静默腐蚀; 存根有此小时
    = v4_merge_agg 合流替换(对照面); 存根行表重建完整日行(v4_rollup_agg 替换语义)
    随批落盘, 开放月吃重建日行(month_days upsert); **月层都不匹配**(背日超过一个月,
    信用回溯到不了的防御面)时日行照常落盘、月层零动作 —— 背日行不得级联翻月。"""
    from auto_qb.core.modules.traffic_sample_agg import _SampleAggMixin
    from auto_qb.core.modules.traffic_sample_common import SeriesAgg
    from auto_qb.core.traffic_store_paths import v4_day_epoch, v4_month_epoch

    d0 = v4_day_epoch(1_800_000_000)

    def mk(epoch, dl):
        return AggRow("hour", epoch, dl, dl, dl // 2, dl // 2, 1000 + dl, 500 + dl // 2, 3600)

    stub9, stub11 = mk(d0 + 9 * HOUR_SECONDS, 100), mk(d0 + 11 * HOUR_SECONDS, 200)
    # 存根无此小时(10 点缺) -> 追加首写 + 日行重建(3 小时等权 cov 10800) + 开放月吃日行
    agg = SeriesAgg(closed_day=(d0, [stub9, stub11]), month_epoch=v4_month_epoch(d0), month_days=[])
    rows_out = []
    _SampleAggMixin._agg_reseal_closed_day(agg, mk(d0 + 10 * HOUR_SECONDS, 150), rows_out)
    assert [(r.kind, (r.epoch - d0) // HOUR_SECONDS) for r in rows_out] == [("hour", 10), ("day", 0)]
    assert [(h.epoch - d0) // HOUR_SECONDS for h in agg.closed_day[1]] == [9, 11, 10]  # 存根追加首写
    assert rows_out[1].cov_s == 3 * HOUR_SECONDS and rows_out[1].dl_avg == 150  # 重建日行(等权)
    assert len(agg.month_days) == 1 and agg.month_days[0] is rows_out[1]  # 开放月 upsert 重建日行
    # 存根有此小时 -> 合流替换(对照面: v4_merge_agg 保覆盖语义)
    agg_b = SeriesAgg(closed_day=(d0, [stub9]), month_epoch=v4_month_epoch(d0), month_days=[])
    rows_b = []
    _SampleAggMixin._agg_reseal_closed_day(agg_b, mk(d0 + 9 * HOUR_SECONDS, 300), rows_b)
    assert agg_b.closed_day[1][0].dl_avg == 200  # 合流行(100/300 覆盖加权)
    assert [(r.epoch - d0) // HOUR_SECONDS for r in rows_b] == [9, 0]
    # 月层都不匹配(背日超月) -> 日行落盘, 月层零动作
    agg_c = SeriesAgg(closed_day=(d0, [stub9]), month_epoch=v4_month_epoch(d0) + 1, closed_month=None, month_days=[])
    rows_c = []
    _SampleAggMixin._agg_reseal_closed_day(agg_c, mk(d0 + 9 * HOUR_SECONDS, 300), rows_c)
    assert [r.kind for r in rows_c] == ["hour", "day"]  # 无 month 行
    assert agg_c.month_days == []  # 开放月累计器未动(背日行不级联翻月)


# ======================================================================
# D12 折叠态对拍守阵(plan 26-11-21-1546 S1/D12; 等价判据 D2 + 浮点序不变量 R2):
# HourFold(逐笔 merge -> seal)与旧列表路径(逐条 append V4HourSample -> v4_hour_agg)
# 的聚合输出 bitwise 等价。v4_hour_agg 本体保留作参照实现与对拍基准(生产封口已改走
# fold.seal, 数学逐条对齐)。
# ======================================================================


def _list_seal(credits, hour_epoch):
    """列表路径(参照): 信用逐条 append 成 V4HourSample 元组 -> v4_hour_agg"""
    samples = tuple(V4HourSample(dl, up, dlt, upt, dt) for dl, up, dlt, upt, dt in credits)
    return v4_hour_agg(hour_epoch, samples)


def _fold_seal(credits, hour_epoch):
    """fold 路径: 信用按到达顺序逐笔 merge -> seal(R2: 与列表路径同序才 bitwise 一致)"""
    fold = HourFold()
    for dl, up, dlt, upt, dt in credits:
        fold.merge(dl, up, dlt, upt, dt)
    return fold.seal(hour_epoch)


def _random_credits(rng, n):
    """随机信用序列(R2 场景生成器): dt_s = dt_ms/1000 的二进制不精确值(亚秒残余/整秒/
    恰满一小时/超一小时大段混采), 速率 0 与大值混合, 退化零 dt 笔可现(首笔保底正覆盖
    —— 全零覆盖两路同抛由 error_and_boundary 专测钉), totals 随机大整数。"""
    credits = []
    for i in range(n):
        dt_ms = rng.choice([rng.randrange(1, 1000), rng.randrange(1, 3_600_001), 263, 1500, 3_599_999, 3_600_000, 0])
        if i == 0 and dt_ms == 0:
            dt_ms = 263
        credits.append(
            (
                rng.choice([0, rng.randrange(0, 50_000_000)]),
                rng.choice([0, rng.randrange(0, 50_000_000)]),
                rng.randrange(0, 10**12),
                rng.randrange(0, 10**12),
                dt_ms / 1000.0,
            )
        )
    return credits


def test_hour_fold_seal_bitwise_matches_v4_hour_agg_random_credits():
    """D12 随机对拍(D2 等价判据 / R2 浮点序): 同一随机信用序列走三条路 —— 列表路径
    (V4HourSample 逐条 append -> v4_hour_agg)/ fold 路径(全序列逐笔 merge -> seal)/
    活尾组合序(settled fold 拷贝成副本后合成段按原序 merge 再 seal, 即 _pending_agg_rows
    的组合)—— 断言 AggRow bitwise 相等(NamedTuple 相等 = 逐字段相等, 另以 format_agg_row
    文本钉 9 列逐位)。固定种子可复现。"""
    rng = random.Random(1546)
    for _ in range(300):
        hour_epoch = rng.randrange(0, 2**31 - 2 * HOUR_SECONDS) // HOUR_SECONDS * HOUR_SECONDS
        credits = _random_credits(rng, rng.randint(1, 40))
        settled_n = rng.randint(1, len(credits))
        row_list = _list_seal(credits, hour_epoch)
        row_fold = _fold_seal(credits, hour_epoch)
        settled = HourFold()
        for credit in credits[:settled_n]:
            settled.merge(*credit)
        composed = settled.copy()  # 活尾副本(D12): copy 后按原序并入合成段
        for credit in credits[settled_n:]:
            composed.merge(*credit)
        assert row_list == row_fold == composed.seal(hour_epoch)
        assert format_agg_row(row_list) == format_agg_row(row_fold)  # 9 列文本逐位


def test_hour_fold_reseal_matches_list_and_seal_is_readonly():
    """D12 时序对拍(D2): 同 epoch 桶重开续接 —— 先并 A 段信用 seal, 再并 B 段信用再
    seal; fold 两轮输出与列表版(A 段聚合 -> 扩展 B 段再聚合)逐轮 bitwise 一致, 且 seal
    只读(两轮之间折叠态逐字段不变 —— 封口后迟到信用续接的形态)。"""
    rng = random.Random(1121)
    for _ in range(100):
        hour_epoch = rng.randrange(0, 2**31 - 2 * HOUR_SECONDS) // HOUR_SECONDS * HOUR_SECONDS
        a = _random_credits(rng, rng.randint(1, 15))
        b = _random_credits(rng, rng.randint(0, 15))
        fold = HourFold()
        for dl, up, dlt, upt, dt in a:
            fold.merge(dl, up, dlt, upt, dt)
        snapshot = fold.copy()  # 第一轮 seal 前快照(seal 只读不变式的对照面)
        row_first = fold.seal(hour_epoch)
        assert row_first == _list_seal(a, hour_epoch)
        assert fold == snapshot  # seal 未改折叠态
        for dl, up, dlt, upt, dt in b:
            fold.merge(dl, up, dlt, upt, dt)
        assert fold.credits == len(a) + len(b)
        assert fold.seal(hour_epoch) == _list_seal(a + b, hour_epoch)


def test_hour_fold_degenerate_inputs_parity():
    """D12 退化值钉面(D2): max 语义(首笔立基线逐笔取大 —— 负速率下与列表 max 逐位
    一致, 不含隐含 0 下界)/ totals 恒取末笔(中间笔快照被覆盖)/ 全零速率桶聚合输出
    一致。生产不产负速率, 表示面等价性仍须逐位。"""
    h = HOUR_SECONDS
    neg = [(-5, -3, 100, 200, 10.0), (-7, -1, 150, 250, 5.0), (-6, -9, 160, 260, 15.0)]
    row = _fold_seal(neg, h)
    assert row == _list_seal(neg, h)
    assert row.dl_max == -5 and row.up_max == -1  # 隐含 0 下界会腐蚀负速率 max
    tot = [(100, 50, 1000, 2000, 10.0), (200, 60, 3000, 4000, 10.0), (0, 0, 5000, 6000, 10.0)]
    row = _fold_seal(tot, h)
    assert row == _list_seal(tot, h) and (row.dl_total, row.up_total) == (5000, 6000)
    zero = [(0, 0, 1, 2, 1800.0), (0, 0, 1, 2, 1800.0)]
    row = _fold_seal(zero, h)
    assert row == _list_seal(zero, h) and row.dl_avg == 0 and row.cov_s == 3600


def test_hour_fold_error_and_boundary_parity():
    """D12 语义边界钉面(D2): 空(无信用)与零覆盖 ValueError 逐条对齐列表路径(空桶 =
    不出行语义由调用方 try/except 承接); cov 边界 —— 亚秒残余 cov_s 下限 1(2026-10-13
    真机「逐级聚合无有效覆盖」不变量)/ Σdt > 3600 截 3600 / 恰 3600 / 整值形态不回归
    —— 与 v4_hour_agg 逐位一致。"""
    h = HOUR_SECONDS
    with pytest.raises(ValueError, match="无样本"):
        v4_hour_agg(h, ())
    with pytest.raises(ValueError, match="无样本"):
        HourFold().seal(h)
    with pytest.raises(ValueError, match="无有效覆盖"):
        v4_hour_agg(h, (V4HourSample(1, 1, 1, 1, 0.0), ))
    with pytest.raises(ValueError, match="无有效覆盖"):
        _fold_seal([(1, 1, 1, 1, 0.0)], h)
    # 亚秒残余: cov_s 下限 1(真机 0.263s 残余形态), avg 仍按 float cov 加权, round 边界 0.5 同折 1
    for dt in (0.001, 0.263, 0.5):
        credits = [(100, 50, 1000, 500, dt)]
        row = _fold_seal(credits, h)
        assert row == _list_seal(credits, h) and row.cov_s == 1
    # Σdt > 3600 截断: cov_s = 3600, avg 按截断后的 cov 加权
    over = [(100, 50, 1, 2, 2000.0), (300, 150, 3, 4, 2000.0)]
    row = _fold_seal(over, h)
    assert row == _list_seal(over, h) and row.cov_s == 3600
    assert row.dl_avg == int(round((100 * 2000 + 300 * 2000) / 3600))
    # 整值形态不回归(已落盘数字不变)
    assert _fold_seal([(1, 1, 1, 1, 3597.0)], h).cov_s == 3597
    assert _fold_seal([(1, 1, 1, 1, 3600.0)], h).cov_s == 3600
