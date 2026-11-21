"""test_traffic_recovery_equivalence 测试计划: B1+B2 恢复对拍守阵(plan 26-11-21-1546 S1;
D2 等价判据「聚合输出层逐位等价」+ §07 R1 边界上下文忠实 + B2 游程级闭合式 FP 分级)。
harness 单点在 tests/traffic_recovery_support.py(语料合成 + 逐槽参照件 reference_slot_credit
+ 对拍断言)。参照件 = B2 改造前生产 _agg_credit_day_file 的逐字镜像(冻结在测试侧)。

## 测试计划(每个测试函数一条)
- test_b1_equivalence_random_corpus_three_phases: 随机合成语料(3 风格 x 6 种子)x 三水位
  相位(当日 fresh / 陈旧至昨日 / 无水位 fallback)—— 逐槽参照(全解析 + 全槽入账 + 尾部
  丢弃)vs 生产路径(B1 字节级开放段 + 记账入口过滤 + B2 游程级闭合式): hour 桶集 +
  折叠字段分级(wsum/max/totals 逐位, cov ULP 免责)/ 完结小时 seal 行 bitwise(AggRow +
  format_agg_row 文本)/ pending 桶集 + 字段分级 + seal 行 bitwise / 跨文件 tail 上下文
  逐位; 且处理槽 <= 参照全量槽(开放段只减不增)
- test_b1_equivalence_missing_file_chain_break: 读集中部天文件缺失 -> 两路 tail 同断链
  (None), 其后产出仍分级相等(缺文件断链形态)
- test_b1_equivalence_missing_last_file_breaks_tail_to_none: 缺失/空文件是读集最后一个
  文件(评审 P1b-1)-> 两路 tail 同归 None(参照实现 else 断链分支对齐钉住)
- test_b1_equivalence_empty_trailing_block_tail_preserved: 全封口空末块窄角(评审 P1b-3)
  —— wm 恰 23:00 + 末块 B 行后撕裂(blocks=())+ 次日 00:00 连续: 空末块回退前一有效
  块头重解, tail 接力恢复, hour 0 桶 = 结算 10s + 块内 30s
- test_b1_equivalence_empty_context_block_before_open_segment: 段首上下文块为空块窄角
  (评审 P1b-3 同族)—— 有效 B 行无记录夹在封口/保留块之间: 回退重解保跨块结算,
  hour 11 桶 cov = 35s
- test_b1_equivalence_torn_tail_variants: 撕裂尾两形态(末记录半行 / 末块 B 行半行)——
  两路坏行纪律同判, 产出分级相等(撕裂尾形态)
- test_b1_equivalence_end_to_end_recovery: 端到端 —— 真 _recover_series(mod.start)产出
  (pending 字段分级 / agg 补算 hour 行 / recovery_reads 计数)与参照全量路径一致
  (fresh + stale 两相位, 各自独立目录)
B2 游程级闭合式定向守阵(plan §03.1 B2 / §07 R1 忠实移植):
- test_b2_equivalence_random_corpus_exact_grid: 生产 1.5s 精确栅格族(exact_grid, 槽位链
  全程 FP 精确)x 3 风格 x 2 种子 x 三相位 —— cov 断言升级为逐位(闭合式端点差 == 逐槽
  累加和, ULP 免责路径零触发形态)
- test_b2_equivalence_random_corpus_offgrid_run_dt: 随机 dt 族(run_dt_jitter, 游程显式
  dt_ms 带超容差实测抖动 -> spacing 非精确可表示)x 3 风格 x 2 种子 x 三相位 —— cov ULP
  免责路径断言全语料 max cov 差 <= COV_ULP_TOL(精确栅格论证下实测恒 0, 容差仅契约面
  保留), 其余字段分级同上
- test_b2_directed_run_crossing_hour_boundary: 跨小时 z 游程(120 槽, 桶界切分)—— hour 11
  桶 = 信用 30s + 桶级合并 3560s, hour 12 桶 = 跨界残余 10s + 末端结算 30s; 桶末笔
  totals = ramp[ki](桶末正长度区间)与末端快照两形态钉死
- test_b2_directed_run_crossing_midnight: 跨 00:00 游程(跨文件 tail 接力)—— 末端摊配
  上下文过日界结算, hour 23 = 游程内 60s + 跨文件 30s
- test_b2_directed_single_slot_runs: 单槽游程(块首/非块首 x z/n)—— 零内部区间,
  尾部信用 n=1 退化取开启快照(非末端快照); 块首单槽游标零推进
- test_b2_directed_blockhead_n_only: 块首 n-only 前缀块(3 列 B)—— 全程零入账,
  tail obs = None, 其后块结算自然跳过
- test_b2_directed_degenerate_ramp: 退化 ramp 两形态 —— 旧文件无末端列(4 列 z 行)与
  末端 < 开启(游程内计数器重置): 恒开启快照, 无插值
- test_b2_directed_mixed_rz_bucket: r+z 混桶 —— wsum/max 来自 r 信用(逐位), totals
  末笔 = 游程末端快照, 桶级合并与逐槽的信用区间序列同位
- test_b2_directed_block_riding_watermark: 骑水位上下文块 —— 封口部分 skip_through_hour
  过滤, 保留部分照常入账(hour 11 = 20s + 跨块结算 30s), 两路产出分级相等
- test_b2_credit_cost_rows_not_slots: B2 成本微基准(§02.2 候选实测的单元级复验)——
  单条 86400 槽 z 游程 + z-heavy 1.5s 全天(约 3 千行/5.7 万槽): _agg_credit_hours
  调用数 B2 <= 2x行数+50 且 <= 参照/10(结构复杂度断言, 确定性), 耗时数字 print
  (量级证据, 不作时序断言)
"""

import os
import random
from time import perf_counter

import pytest

from clock import FakeClock

from auto_qb.config import QbTraffic

from auto_qb.core.modules import traffic_sample_agg as _agg_mod
from auto_qb.core.modules.traffic_sample_mod import GLOBAL_SERIES_KEY

from auto_qb.core.traffic_store import (
    DT_MS_MAX,
    HEADER_LINE_V4,
    HOUR_SECONDS,
    AggRow,
    TrafficV4Store,
    V4Block,
    V4NullRun,
    V4Sample,
    V4ZeroRun,
    format_v4_day_text,
    parse_v4_agg_text,
    parse_v4_day_text,
    v4_date_str_epoch,
    v4_z_totals_ramp,
)

from traffic_recovery_support import (
    COV_ULP_TOL,
    assert_b1_bitwise_equivalent,
    assert_folds_field_equivalent,
    b1_production_credit,
    read_set_dates,
    reference_full_credit,
    reference_slot_credit,
    split_rows_pending,
    synthesize_series_files,
)

from traffic_sample_support import _agg_text, _mgr_with_traffic

#: 语料日序(固定本地日, 末日 = 「今日」; 生成面用 v4_date_str_epoch 换算日界)
CORPUS_DATES = ("2026-06-02", "2026-06-03", "2026-06-04", "2026-06-05")
_NOW = v4_date_str_epoch("2026-06-05") + 13 * HOUR_SECONDS + 30  # 今日 13:00:30
_WINDOW = 30 * 86400.0


def _build_corpus(tmp_path, seed, style):
    """随机合成语料(种子可复现): 返回 (store, info)"""
    rng = random.Random(f"b1-equivalence-{seed}-{style}")
    store = TrafficV4Store(str(tmp_path))
    info = synthesize_series_files(store, GLOBAL_SERIES_KEY, CORPUS_DATES, rng, style=style)
    return store, info


@pytest.mark.parametrize("style", ["z-heavy", "r-heavy", "mixed"])
@pytest.mark.parametrize("seed", range(6))
def test_b1_equivalence_random_corpus_three_phases(tmp_path, seed, style):
    """随机合成语料 x 三水位相位对拍(D2): 三相位逐相位断言 bitwise 等价 + 处理槽单调"""
    store, _info = _build_corpus(tmp_path, seed, style)
    phases = (
        ("fresh", v4_date_str_epoch("2026-06-05") + 11 * HOUR_SECONDS),  # 当日 11:00(新鲜)
        ("stale", v4_date_str_epoch("2026-06-04") + 10 * HOUR_SECONDS),  # 昨日 10:00(陈旧)
        ("fallback", None),  # 无水位(D4 全量兜底语义不变)
    )
    for phase, wm in phases:
        dates = read_set_dates(store, GLOBAL_SERIES_KEY, _NOW, wm, _WINDOW)
        ref_samples, ref_tail, ref_slots = reference_full_credit(store, GLOBAL_SERIES_KEY, dates, wm)
        b1_samples, b1_tail, b1_slots = b1_production_credit(store, GLOBAL_SERIES_KEY, dates, wm)
        rows, pending = assert_b1_bitwise_equivalent(
            ref_samples, ref_tail, b1_samples, b1_tail, _NOW, ctx=f"{style}/s{seed}/{phase}"
        )
        assert b1_slots <= ref_slots, f"{style}/s{seed}/{phase}: B1 处理槽 {b1_slots} > 全量 {ref_slots}"
        # 产出非空护栏(语料确有读集内小时, 对拍不是空对空)
        assert len(rows) + len(pending) >= 1, f"{style}/s{seed}/{phase}: 语料无产出"


def test_b1_equivalence_missing_file_chain_break(tmp_path, monkeypatch):
    """缺文件断链形态(D1 语料要素): 读集中部天文件读失败(竞态/手工清理 -> 两读入口
    None)-> 两路 tail 同断链(None), 其后文件的记账与产出仍 bitwise 相等(陈旧水位相位,
    断链文件跨 00:00 连续边界; 文件在名册但读取为空 = listdir 与 open 的竞态窗口形态)"""
    store, _info = _build_corpus(tmp_path, 7, "mixed")
    wm = v4_date_str_epoch("2026-06-04") + 10 * HOUR_SECONDS  # 陈旧至昨日
    dates = read_set_dates(store, GLOBAL_SERIES_KEY, _NOW, wm, _WINDOW)
    assert "2026-06-04" in dates
    real_read_day = TrafficV4Store.read_day
    real_read_segment = TrafficV4Store.read_day_open_segment

    def _drop_mid(self, key, date_str):
        if date_str == "2026-06-04":
            return None
        return real_read_day(self, key, date_str)

    def _drop_mid_segment(self, key, date_str, wm_hour):
        if date_str == "2026-06-04":
            return None
        return real_read_segment(self, key, date_str, wm_hour)

    monkeypatch.setattr(TrafficV4Store, "read_day", _drop_mid)
    monkeypatch.setattr(TrafficV4Store, "read_day_open_segment", _drop_mid_segment)
    ref_samples, ref_tail, _ref_slots = reference_full_credit(store, GLOBAL_SERIES_KEY, dates, wm)
    b1_samples, b1_tail, _b1_slots = b1_production_credit(store, GLOBAL_SERIES_KEY, dates, wm)
    assert_b1_bitwise_equivalent(ref_samples, ref_tail, b1_samples, b1_tail, _NOW, ctx="missing-file/stale")


def test_b1_equivalence_missing_last_file_breaks_tail_to_none(tmp_path, monkeypatch):
    """缺失/空文件是读集**最后一个**文件(评审 P1b-1): 两路 tail 同归 None(断链,
    不携带前一文件的陈旧 tail)—— 参照实现循环补 else 断链分支后与生产 _recover_series
    逐字对齐; 前段文件产出照常 bitwise 相等"""
    store, _info = _build_corpus(tmp_path, 7, "mixed")
    wm = v4_date_str_epoch("2026-06-04") + 10 * HOUR_SECONDS
    dates = read_set_dates(store, GLOBAL_SERIES_KEY, _NOW, wm, _WINDOW)
    last_date = dates[-1]
    real_read_day = TrafficV4Store.read_day
    real_read_segment = TrafficV4Store.read_day_open_segment

    def _drop_last(self, key, date_str):
        return None if date_str == last_date else real_read_day(self, key, date_str)

    def _drop_last_segment(self, key, date_str, wm_hour):
        return None if date_str == last_date else real_read_segment(self, key, date_str, wm_hour)

    monkeypatch.setattr(TrafficV4Store, "read_day", _drop_last)
    monkeypatch.setattr(TrafficV4Store, "read_day_open_segment", _drop_last_segment)
    ref_samples, ref_tail, _ref_slots = reference_full_credit(store, GLOBAL_SERIES_KEY, dates, wm)
    b1_samples, b1_tail, _b1_slots = b1_production_credit(store, GLOBAL_SERIES_KEY, dates, wm)
    assert ref_samples  # 前段文件确有产出(非空对空)
    assert ref_tail is None and b1_tail is None  # 末文件缺失: 两路 tail 同断链(钉住参照 else 分支)
    assert_b1_bitwise_equivalent(ref_samples, ref_tail, b1_samples, b1_tail, _NOW, ctx="missing-last")


def test_b1_equivalence_empty_trailing_block_tail_preserved(tmp_path):
    """全封口空末块窄角(评审 P1b-3): wm 恰 23:00 + 末日末块 B 行后撕裂(块无合法记录,
    build 丢弃 -> 段解析 blocks=())+ 次日 00:00 连续 —— 空末块不产 tail, 段解析不得让
    tail 退化成上一文件尾/None: 自前一有效块头重解, 前一块末槽(23:59:50)照常接力,
    次日 00:00 结算信用落保留小时(hour 0 桶 = 结算 10s + 块内 30s = 40s)"""
    st = TrafficV4Store(str(tmp_path))
    key = GLOBAL_SERIES_KEY
    day_d0 = v4_date_str_epoch("2026-06-04")
    day_e0 = v4_date_str_epoch("2026-06-05")
    wm = day_d0 + 23 * HOUR_SECONDS  # 恰 23:00
    # 末日(06-04): 块 A(23:59:20, 2 r -> 末槽 23:59:50, 封口小时) + 末块 B 行(23:59:55)
    # 后撕裂(r 半行 -> 块无合法记录, 空块被丢弃)
    st.append_records(
        key,
        "2026-06-04",
        (day_d0 + 23 * HOUR_SECONDS + 59 * 60 + 20, 30),
        (V4Sample(100, 50, 1000, 2000), V4Sample(200, 60, 2000, 3000)),
        (1000, 2000),
    )
    with open(st.series_day_path(key, "2026-06-04"), "a", encoding="utf-8", newline="") as f:
        f.write(f"B,{day_d0 + 23 * HOUR_SECONDS + 59 * 60 + 55},30\nr,9,9")  # 撕裂: 无换行尾
    # 次日(06-05): 00:00:10 块(与 A 末槽 gap 20s < interval 30s -> 跨文件连续)
    st.append_records(
        key,
        "2026-06-05",
        (day_e0 + 10, 30),
        (V4Sample(10, 5, 100, 200), V4Sample(20, 6, 200, 300)),
        (100, 200),
    )
    now = day_e0 + 30 * 60 + 30
    dates = read_set_dates(st, key, now, wm, _WINDOW)
    assert dates == ("2026-06-04", "2026-06-05")
    ref_samples, ref_tail, _r = reference_full_credit(st, key, dates, wm)
    b1_samples, b1_tail, _b = b1_production_credit(st, key, dates, wm)
    assert_b1_bitwise_equivalent(ref_samples, ref_tail, b1_samples, b1_tail, now, ctx="empty-trailing-block")
    # 显式钉住: hour 0 桶 = 跨文件结算保留部分 10s([00:00:00, 00:00:10)) + 块内区间 30s
    h0 = day_e0
    assert ref_samples[h0].cov == 40.0 and ref_samples[h0].credits == 2
    assert b1_samples[h0].cov == 40.0 and b1_samples[h0].credits == 2


def test_b1_equivalence_empty_context_block_before_open_segment(tmp_path):
    """段首上下文块为空块窄角(评审 P1b-3 同族): wm = 10:00, 块 j-2(10:59:20, 2 r,
    末槽 10:59:50)后跟**有效 B 行无记录**(崩溃恰在 B 行落盘后, 空块被丢弃), j(11:00:05,
    保留小时首块)—— 旧路径 j 的结算上下文 = j-2 末槽(gap 15s 连续, 保留部分
    [11:00:00, 11:00:05) 5s); 段自 j-1 起但 j-1 空块被丢弃时须回退 j-2 重解,
    否则 hour 11 折叠态少 5s(cov 35 vs 30)"""
    st = TrafficV4Store(str(tmp_path))
    key = GLOBAL_SERIES_KEY
    day0 = v4_date_str_epoch("2026-06-05")
    wm = day0 + 10 * HOUR_SECONDS
    st.append_records(
        key,
        "2026-06-05",
        (day0 + 10 * HOUR_SECONDS + 59 * 60 + 20, 30),
        (V4Sample(100, 50, 1000, 2000), V4Sample(200, 60, 2000, 3000)),
        (1000, 2000),
    )  # j-2: 末槽 10:59:50(封口小时)
    with open(st.series_day_path(key, "2026-06-05"), "a", encoding="utf-8", newline="\n") as f:
        f.write(f"B,{day0 + 10 * HOUR_SECONDS + 59 * 60 + 51},30\n")  # j-1: 有效 B 行, 无记录
    st.append_records(
        key,
        "2026-06-05",
        (day0 + 11 * HOUR_SECONDS + 5, 30),
        (V4Sample(300, 90, 3000, 4000), V4Sample(400, 100, 4000, 5000)),
        (3000, 4000),
    )  # j: 11:00:05(保留小时首块)
    now = day0 + 13 * HOUR_SECONDS + 30
    dates = read_set_dates(st, key, now, wm, _WINDOW)
    assert dates == ("2026-06-05", )
    ref_samples, ref_tail, _r = reference_full_credit(st, key, dates, wm)
    b1_samples, b1_tail, _b = b1_production_credit(st, key, dates, wm)
    assert_b1_bitwise_equivalent(ref_samples, ref_tail, b1_samples, b1_tail, now, ctx="empty-context-block")
    # 显式钉住: hour 11 桶 = 跨块结算保留部分 5s + 块内区间 30s(无回退时 = 30s)
    h11 = day0 + 11 * HOUR_SECONDS
    assert ref_samples[h11].cov == 35.0 and ref_samples[h11].credits == 2
    assert b1_samples[h11].cov == 35.0 and b1_samples[h11].credits == 2


def test_b1_equivalence_torn_tail_variants(tmp_path):
    """撕裂尾形态(D1 语料要素): 末记录半行(崩溃截断, 去 \\n)与末块 B 行半行(开块
    中途崩溃, 追加 \\nB,123 残行)—— 两路坏行纪律同判(torn_tail/bad_lines), 产出
    bitwise 相等"""
    # 形态 1: 末记录半行
    store, _info = _build_corpus(tmp_path, 11, "z-heavy")
    path = store.series_day_path(GLOBAL_SERIES_KEY, "2026-06-05")
    text = open(path, encoding="utf-8").read()
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text[:-1])  # 去掉最后一个 \n -> 末行撕裂
    wm = v4_date_str_epoch("2026-06-04") + 10 * HOUR_SECONDS
    dates = read_set_dates(store, GLOBAL_SERIES_KEY, _NOW, wm, _WINDOW)
    ref_samples, ref_tail, _r = reference_full_credit(store, GLOBAL_SERIES_KEY, dates, wm)
    b1_samples, b1_tail, _b = b1_production_credit(store, GLOBAL_SERIES_KEY, dates, wm)
    assert_b1_bitwise_equivalent(ref_samples, ref_tail, b1_samples, b1_tail, _NOW, ctx="torn-record")
    # 形态 2: 末块 B 行半行(开块中途崩溃; 候选定位含它但非有效块头, 不作切分点)
    store2, _info2 = _build_corpus(tmp_path / "b", 11, "z-heavy")
    path2 = store2.series_day_path(GLOBAL_SERIES_KEY, "2026-06-05")
    with open(path2, "a", encoding="utf-8", newline="") as f:
        f.write("B,1234")  # 撕裂 B 半行(无换行)
    ref2_samples, ref2_tail, _r2 = reference_full_credit(store2, GLOBAL_SERIES_KEY, dates, wm)
    b12_samples, b12_tail, _b2 = b1_production_credit(store2, GLOBAL_SERIES_KEY, dates, wm)
    assert_b1_bitwise_equivalent(ref2_samples, ref2_tail, b12_samples, b12_tail, _NOW, ctx="torn-b-row")


def test_b1_equivalence_end_to_end_recovery(tmp_path, monkeypatch):
    """端到端对拍: 真 _recover_series(mod.start)与参照全量路径一致 —— pending 折叠态
    bitwise / agg 补算 hour 行 == 参照 seal 行序列 / recovery_reads 计数与 B1 镜像循环
    一致(fresh + stale 两相位, 各自独立目录; D2 输出层口径)"""
    phases = (
        ("fresh", v4_date_str_epoch("2026-06-05") + 11 * HOUR_SECONDS),
        ("stale", v4_date_str_epoch("2026-06-04") + 10 * HOUR_SECONDS),
    )
    for phase, wm in phases:
        root = tmp_path / phase
        root.mkdir()
        store, _info = _build_corpus(root, 5, "mixed")
        store.append_agg_rows(GLOBAL_SERIES_KEY, (AggRow("hour", wm, 7, 9, 3, 4, 500, 600, 3600), ))
        clock = FakeClock(start=_NOW)
        mgr = _mgr_with_traffic(
            root, QbTraffic(enabled=True, sample_interval_multiplier=30, rollup_window=_WINDOW), clock=clock
        )
        mod = mgr.host.get("qb_traffic")
        mod.start(mgr.ctx, dry_run=False)  # 恢复 + catch-up(先于一切采样)
        dates = read_set_dates(store, GLOBAL_SERIES_KEY, _NOW, wm, _WINDOW)
        ref_samples, _ref_tail, _r = reference_full_credit(store, GLOBAL_SERIES_KEY, dates, wm)
        b1_samples, _b1_tail, b1_slots = b1_production_credit(store, GLOBAL_SERIES_KEY, dates, wm)
        ref_rows, ref_pending = split_rows_pending(ref_samples, _NOW)
        # pending 重建累计器: 桶集 + 字段分级相等(B2 FP 纪律, 见
        # assert_folds_field_equivalent —— wsum/max/totals 逐位, cov ULP 免责(本语料
        # 精确栅格实测逐位), credits 结构豁免: 桶级合并后 merge 笔数变少, 仅 ==0 判空
        # 消费不进聚合输出)
        prod_pending = mod._agg_state(GLOBAL_SERIES_KEY).pending
        assert set(prod_pending) == set(ref_pending), f"[{phase}] pending 桶集不等"
        for h in sorted(ref_pending):
            assert_folds_field_equivalent(ref_pending[h], prod_pending[h], ctx=f"{phase} pending h={h}")
        # agg 补算 hour 行 == 参照 seal 行(水位行原样保留 + 补算行按 epoch 升序)
        parsed = parse_v4_agg_text(_agg_text(root, GLOBAL_SERIES_KEY))
        wm_row = AggRow("hour", wm, 7, 9, 3, 4, 500, 600, 3600)
        assert parsed.hours == (wm_row, ) + tuple(ref_rows), f"[{phase}] agg hour 行不等"
        # 埋点计数与 B1 镜像循环一致(production loop 接线面)
        reads = mod.recovery_reads[GLOBAL_SERIES_KEY]
        assert reads["day_dates"] == dates and reads["bound"] == "watermark"
        assert reads["slots"] == b1_slots, f"[{phase}] slots 计数不等: {reads['slots']} vs {b1_slots}"
        assert reads["new_hours"] == len(ref_rows)


# ==================== B2 游程级闭合式定向守阵(plan 26-11-21-1546 S1) ====================


def _build_corpus_ex(tmp_path, seed, style, **kw):
    """随机合成语料(扩展参数面): 返回 (store, info)"""
    rng = random.Random(f"b2-equivalence-{seed}-{style}")
    store = TrafficV4Store(str(tmp_path))
    info = synthesize_series_files(store, GLOBAL_SERIES_KEY, CORPUS_DATES, rng, style=style, **kw)
    return store, info


def _phases():
    """三水位相位(与随机矩阵同形)"""
    return (
        ("fresh", v4_date_str_epoch("2026-06-05") + 11 * HOUR_SECONDS),
        ("stale", v4_date_str_epoch("2026-06-04") + 10 * HOUR_SECONDS),
        ("fallback", None),
    )


def _credit_both_parsed(parsed_day, skip_through_hour=None):
    """参照(逐槽)与生产(闭合式)对同一解析结果各记一笔: 返回 (ref_samples, ref_tail,
    b2_samples, b2_tail)。"""
    ref_samples: dict = {}
    ref_tail = reference_slot_credit(ref_samples, parsed_day, None, None, skip_through_hour)
    b2_samples: dict = {}
    b2_tail = _agg_mod._SampleAggMixin._agg_credit_day_file(b2_samples, parsed_day, None, None, skip_through_hour)
    return ref_samples, ref_tail, b2_samples, b2_tail


@pytest.mark.parametrize("style", ["z-heavy", "r-heavy", "mixed"])
@pytest.mark.parametrize("seed", range(2))
def test_b2_equivalence_random_corpus_exact_grid(tmp_path, seed, style):
    """生产 1.5s 精确栅格族(D2/B2 第 4 点(2)): r 行恒标称、游程 dt = 标称跨度整毫秒 ——
    槽位链全程 FP 精确(整数 + 1.5k 在 [2^30, 2^31) binade 均可精确表示, 分段差与
    累加和全部精确), 闭合式端点差 == 逐槽累加和 => cov 断言升级为逐位(ULP 免责路径
    零触发形态), 其余字段分级 + seal/pending/tail 断言同随机矩阵"""
    store, _info = _build_corpus_ex(tmp_path, seed, style, interval=1.5, exact_grid=True)
    for phase, wm in _phases():
        dates = read_set_dates(store, GLOBAL_SERIES_KEY, _NOW, wm, _WINDOW)
        ref_samples, ref_tail, _rs = reference_full_credit(store, GLOBAL_SERIES_KEY, dates, wm)
        b2_samples, b2_tail, _bs = b1_production_credit(store, GLOBAL_SERIES_KEY, dates, wm)
        rows, pending = assert_b1_bitwise_equivalent(
            ref_samples,
            ref_tail,
            b2_samples,
            b2_tail,
            _NOW,
            ctx=f"exact-grid/{style}/s{seed}/{phase}",
            cov_bitwise=True
        )
        assert len(rows) + len(pending) >= 1, f"exact-grid/{style}/s{seed}/{phase}: 语料无产出"


@pytest.mark.parametrize("style", ["z-heavy", "r-heavy", "mixed"])
@pytest.mark.parametrize("seed", range(2))
def test_b2_equivalence_random_corpus_offgrid_run_dt(tmp_path, seed, style):
    """随机 dt 族(D2/B2 第 4 点(2)): 游程显式 dt_ms 带超容差实测抖动(真实写侧形态) ->
    spacing 非精确可表示, 槽位 ts 落在 ULP(ts) 栅格 —— cov ULP 免责路径的理论触发形态。
    实测与论证(S1 实施期发现): 生产 epoch(ts ~ 1.78e9, binade [2^30, 2^31))下全部
    ts 共享 2^-22 栅格, 桶内 cov < 2^12(3600s + 余量)的 ULP(2^-41)是 2^-22 的整分
    格 => 逐槽累加每步精确(Sterbenz 型归纳: fold.cov 恒为 2^-41 的倍数, z 分段差全
    是 2^-22 的倍数, 相加不舍入)且闭合式端点差一次精确 —— cov 恒逐位相等(4000 例
    随机混排块实测 0 差, 论证见 assert_folds_field_equivalent 注)。本族断言 cov
    <= COV_ULP_TOL(契约面保留 ULP 免责: 论证依赖 epoch binade 与桶宽的关系, 非全域),
    其余字段分级 + seal/pending/tail 断言同随机矩阵"""
    store, _info = _build_corpus_ex(tmp_path, seed, style, run_dt_jitter=True)
    max_cov_diff = 0.0
    for phase, wm in _phases():
        dates = read_set_dates(store, GLOBAL_SERIES_KEY, _NOW, wm, _WINDOW)
        ref_samples, ref_tail, _rs = reference_full_credit(store, GLOBAL_SERIES_KEY, dates, wm)
        b2_samples, b2_tail, _bs = b1_production_credit(store, GLOBAL_SERIES_KEY, dates, wm)
        rows, pending = assert_b1_bitwise_equivalent(
            ref_samples, ref_tail, b2_samples, b2_tail, _NOW, ctx=f"offgrid/{style}/s{seed}/{phase}"
        )
        assert len(rows) + len(pending) >= 1, f"offgrid/{style}/s{seed}/{phase}: 语料无产出"
        for h in ref_samples:
            max_cov_diff = max(max_cov_diff, abs(ref_samples[h].cov - b2_samples[h].cov))
    assert max_cov_diff <= COV_ULP_TOL


def test_b2_directed_run_crossing_hour_boundary(tmp_path):
    """跨小时 z 游程(120 槽标称, 桶界切分): hour 11 桶 = 块首 r 信用 30s([11:00:10,
    11:00:40)) + 桶级合并 3560s([11:00:40, 12:00:00)), hour 12 桶 = 跨界残余 10s + 末端
    结算 30s; 桶末笔 totals = ramp[ki](桶末正长度区间)与末端快照; 两路字段分级 +
    seal 行 bitwise + tail 逐位"""
    st = TrafficV4Store(str(tmp_path))
    key = GLOBAL_SERIES_KEY
    day0 = v4_date_str_epoch("2026-06-05")
    wm = day0 + 11 * HOUR_SECONDS
    s0 = (1_000_000, 2_000_000)
    s1 = (1_070_000, 2_035_000)
    st.append_records(
        key,
        "2026-06-05",
        (day0 + 11 * HOUR_SECONDS + 10, 30),
        (
            V4Sample(100, 50, s0[0], s0[1]),  # 块首 r: 11:00:10, 信用 [11:00:10, 11:00:40)
            V4ZeroRun(120, s0[0], s0[1], None, s1[0], s1[1]),  # 槽 0 = 11:00:40 .. 槽 119 = 12:00:10
            V4Sample(300, 90, s1[0] + 500, s1[1] + 300),  # 12:00:40: 结算末端信用
        ),
        s0,
    )
    now = day0 + 13 * HOUR_SECONDS + 30
    dates = read_set_dates(st, key, now, wm, _WINDOW)
    parsed = st.read_day(key, dates[0])
    ref_samples, ref_tail, b2_samples, b2_tail = _credit_both_parsed(parsed)
    assert_b1_bitwise_equivalent(ref_samples, ref_tail, b2_samples, b2_tail, now, ctx="run-cross-hour")
    ramp = v4_z_totals_ramp(s0[0], s0[1], s1[0], s1[1], 120)
    h11, h12 = day0 + 11 * HOUR_SECONDS, day0 + 12 * HOUR_SECONDS
    # hour 11: r 信用 30s + 桶级合并 3560s(逐槽 119 笔分段: 118 整段 + I_118 前切),
    # 末笔 totals = ramp[118](桶末正长度区间 I_118 = [11:59:40, 12:00:10) 的起点槽)
    for fold in (ref_samples[h11], b2_samples[h11]):
        assert fold.cov == 3590.0 and (fold.dl_total, fold.up_total) == ramp[118]
        assert fold.dl_max == 100 and fold.dl_wsum == 100 * 30.0  # r 信用面(逐位)
    assert b2_samples[h11].credits == 2  # 闭合式: r 结算 1 笔 + 桶级合并 1 笔
    # hour 12: 跨界残余 10s(ramp[118]) + 末端结算 30s(ramp[119] = 末端快照)
    for fold in (ref_samples[h12], b2_samples[h12]):
        assert fold.cov == 40.0 and (fold.dl_total, fold.up_total) == s1
    assert b2_samples[h12].credits == 2  # 闭合式: 桶级 1 笔 + 末端结算 1 笔
    assert b2_tail == ref_tail == (day0 + 12 * HOUR_SECONDS + 40, (300, 90, s1[0] + 500, s1[1] + 300))


def test_b2_directed_run_crossing_midnight(tmp_path):
    """跨 00:00 游程(跨文件 tail 接力, R1 边界忠实): 末日块首 z 游程(3 槽, 末端摊配
    上下文)过日界连续结算 —— hour 23 = 游程内 60s + 跨文件结算 30s, totals = 末端快照;
    两路字段分级 + seal 行 bitwise + tail 逐位"""
    st = TrafficV4Store(str(tmp_path))
    key = GLOBAL_SERIES_KEY
    day_d0 = v4_date_str_epoch("2026-06-04")
    day_e0 = v4_date_str_epoch("2026-06-05")
    wm = day_d0 + 10 * HOUR_SECONDS
    s0 = (5_000_000, 6_000_000)
    s1 = (5_000_400, 6_000_300)
    st.append_records(key, "2026-06-04", (day_d0 + 22 * HOUR_SECONDS, 30), (V4Sample(100, 50, s0[0], s0[1]), ), s0)
    st.append_records(
        key, "2026-06-04", (day_d0 + 23 * HOUR_SECONDS + 58 * 60 + 30, 30),
        (V4ZeroRun(3, s0[0], s0[1], None, s1[0], s1[1]), ), s0
    )  # 23:58:30..23:59:30(3 槽, 块首 z 立基线 = 开启快照)
    st.append_records(
        key, "2026-06-05", (day_e0, 30), (V4Sample(200, 80, s1[0] + 100, s1[1] + 100), ), (s1[0] + 100, s1[1] + 100)
    )  # 次日 00:00:00: gap 30 <= interval + 容差 -> 跨文件连续
    now = day_e0 + 2 * HOUR_SECONDS + 30
    dates = read_set_dates(st, key, now, wm, _WINDOW)
    assert dates == ("2026-06-04", "2026-06-05")
    ref_samples, ref_tail, b2_samples, b2_tail = {}, None, {}, None
    for d in dates:
        pd = st.read_day(key, d)
        ref_tail = reference_slot_credit(ref_samples, pd, ref_tail)
        b2_tail = _agg_mod._SampleAggMixin._agg_credit_day_file(b2_samples, pd, b2_tail)
    assert_b1_bitwise_equivalent(ref_samples, ref_tail, b2_samples, b2_tail, now, ctx="run-cross-midnight")
    h23 = day_d0 + 23 * HOUR_SECONDS
    for fold in (ref_samples[h23], b2_samples[h23]):
        assert fold.cov == 90.0 and (fold.dl_total, fold.up_total) == s1  # 游程内 60s + 跨文件 30s
        assert fold.dl_max == 0 and fold.dl_wsum == 0.0  # 全 z 信用
    assert b2_samples[h23].credits == 2  # 桶级 1 笔(60s) + 跨文件结算 1 笔(30s)


def test_b2_directed_single_slot_runs(tmp_path):
    """单槽游程(块首/非块首 x z/n): 零内部区间, 尾部信用 n=1 退化取开启快照(非末端
    快照 —— v4_z_totals_ramp n<=1 分支); 块首单槽游标零推进; 两路字段分级 + tail 逐位"""
    st = TrafficV4Store(str(tmp_path))
    key = GLOBAL_SERIES_KEY
    day0 = v4_date_str_epoch("2026-06-05")
    wm = day0 + 9 * HOUR_SECONDS
    s0 = (2_000_000, 3_000_000)
    s1 = (2_000_050, 3_000_040)
    st.append_records(
        key,
        "2026-06-05",
        (day0 + 10 * HOUR_SECONDS + 5, 30),
        (
            V4ZeroRun(1, s0[0], s0[1], None, s1[0], s1[1]),  # 块首单槽 z: 首槽 = B.start, 游标零推进
            V4Sample(100, 50, s0[0] + 100, s0[1] + 100),  # 10:00:35: 结算 z 尾信用(开启快照)
            V4Sample(120, 60, s0[0] + 200, s0[1] + 200),  # 10:01:05: 结算 r1 信用
        ),
        s0,
    )
    st.append_records(key, "2026-06-05", (day0 + 11 * HOUR_SECONDS + 5, 30), (V4NullRun(1), ), None)  # 3 列 B
    st.append_records(
        key,
        "2026-06-05",
        (day0 + 11 * HOUR_SECONDS + 35, 30),
        (V4ZeroRun(1, s0[0] + 300, s0[1] + 300, None, s0[0] + 400, s0[1] + 400), ),
        (s0[0] + 300, s0[1] + 300),
    )  # 块首单槽 z: 尾信用 = 开启快照(悬置)
    st.append_records(
        key,
        "2026-06-05",
        (day0 + 11 * HOUR_SECONDS + 65, 30),
        (V4Sample(200, 80, s0[0] + 500, s0[1] + 500), ),
        (s0[0] + 500, s0[1] + 500),
    )  # 11:01:05: 结算单槽 z 尾信用(gap 30 连续)
    now = day0 + 13 * HOUR_SECONDS + 30
    dates = read_set_dates(st, key, now, wm, _WINDOW)
    parsed = st.read_day(key, dates[0])
    ref_samples, ref_tail, b2_samples, b2_tail = _credit_both_parsed(parsed)
    assert_b1_bitwise_equivalent(ref_samples, ref_tail, b2_samples, b2_tail, now, ctx="single-slot")
    h10, h11 = day0 + 10 * HOUR_SECONDS, day0 + 11 * HOUR_SECONDS
    # hour 10: 单槽 z 无内部区间; 首笔 = z 尾信用 [10:00:05, 10:00:35) 30s totals = 开启
    # 快照 (s0, 非末端快照 s1 —— n=1 跨度退化); 次笔 = r1 信用 30s -> 末笔 totals = r1 冻结值
    for fold in (ref_samples[h10], b2_samples[h10]):
        assert fold.cov == 60.0 and (fold.dl_total, fold.up_total) == (s0[0] + 100, s0[1] + 100)
        assert fold.dl_max == 100 and fold.up_max == 50 and fold.dl_wsum == 100 * 30.0
    # hour 11: 块首 n 单槽零贡献(尾槽信用 obs None, 与 11:00:35 块结算自然跳过);
    # 单槽 z 尾信用 [11:00:35, 11:01:05) 30s totals = 开启快照 (s0+300) —— 非末端 (s0+400)
    for fold in (ref_samples[h11], b2_samples[h11]):
        assert fold.cov == 30.0 and (fold.dl_total, fold.up_total) == (s0[0] + 300, s0[1] + 300)
        assert fold.dl_max == 0 and fold.dl_wsum == 0.0
    assert b2_samples[h11].credits == 1
    assert b2_tail == ref_tail == (day0 + 11 * HOUR_SECONDS + 65, (200, 80, s0[0] + 500, s0[1] + 500))


def test_b2_directed_blockhead_n_only(tmp_path):
    """块首 n-only 前缀块(3 列 B): 全程零入账(断连不可归因), tail obs = None, 其后块
    结算自然跳过(否则 cov 会多出跨块 30s); 块槽位链照常推进(尾槽 = B.start + 120)"""
    st = TrafficV4Store(str(tmp_path))
    key = GLOBAL_SERIES_KEY
    day0 = v4_date_str_epoch("2026-06-05")
    wm = day0 + 9 * HOUR_SECONDS
    n_start = day0 + 10 * HOUR_SECONDS + 5
    st.append_records(key, "2026-06-05", (n_start, 30), (V4NullRun(3), V4NullRun(2)), None)  # 3 列 B
    st.append_records(
        key, "2026-06-05", (n_start + 150, 30), (V4Sample(100, 50, 900, 800), V4Sample(120, 60, 1100, 1000)),
        (900, 800)
    )  # n 尾槽 = n_start+120, 本块 B.start = n_start+150(gap 30 连续, 但 tail obs None -> 不结算)
    now = day0 + 13 * HOUR_SECONDS + 30
    dates = read_set_dates(st, key, now, wm, _WINDOW)
    parsed = st.read_day(key, dates[0])
    ref_samples, ref_tail, b2_samples, b2_tail = _credit_both_parsed(parsed)
    assert_b1_bitwise_equivalent(ref_samples, ref_tail, b2_samples, b2_tail, now, ctx="n-only")
    h10 = day0 + 10 * HOUR_SECONDS
    for fold in (ref_samples[h10], b2_samples[h10]):
        # 仅 r1 信用 30s([n_start+150, n_start+180); r2 信用悬置)—— n 尾槽到本块首槽
        # 的 30s 间隙(tail obs None)未入账
        assert fold.cov == 30.0 and fold.credits == 1
        assert (fold.dl_total, fold.up_total) == (900, 800) and fold.dl_max == 100
    assert b2_tail == ref_tail == (n_start + 180, (120, 60, 1100, 1000))


def test_b2_directed_degenerate_ramp(tmp_path):
    """退化 ramp 两形态(形态 D 兼容): (i) 旧文件无末端列(4 列 z 行, 解析 ends = None)
    —— 恒开启快照无插值; (ii) 末端 < 开启(游程内计数器重置的落盘形态, 块基线低于开启
    时可序列化)—— 恒开启快照。两路字段分级 + seal 行 bitwise + 显式 totals 钉死"""
    st = TrafficV4Store(str(tmp_path))
    key = GLOBAL_SERIES_KEY
    day0 = v4_date_str_epoch("2026-06-05")
    wm = day0 + 9 * HOUR_SECONDS
    # (i) 4 列 z 行(无末端列): 手写文本(append_records 恒写末端对)
    r0 = day0 + 10 * HOUR_SECONDS + 10
    text = (
        f"{HEADER_LINE_V4}\nkey,{key}\n"
        f"B,{r0},30,1000,2000\n"
        f"r,100,50,0,0\n"
        f"z,3,0,0\n"  # 开启快照 = 基线 (1000, 2000), 无末端列 -> ends None
        f"r,120,60,500,400,30000\n"  # 10:02:10
    )
    os.makedirs(os.path.dirname(st.series_day_path(key, "2026-06-05")), exist_ok=True)
    with open(st.series_day_path(key, "2026-06-05"), "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    # (ii) 末端 < 开启: 块基线 (3000, 2000) 低于开启 (5000, 3000) 与末端 (4000, 2500)
    st.append_records(
        key,
        "2026-06-05",
        (day0 + 11 * HOUR_SECONDS + 10, 30),
        (V4ZeroRun(4, 5000, 3000, None, 4000, 2500), V4Sample(90, 40, 5100, 3100)),
        (3000, 2000),
    )
    now = day0 + 13 * HOUR_SECONDS + 30
    dates = read_set_dates(st, key, now, wm, _WINDOW)
    parsed = st.read_day(key, dates[0])
    assert len(parsed.blocks) == 2
    ref_samples, ref_tail, b2_samples, b2_tail = _credit_both_parsed(parsed)
    assert_b1_bitwise_equivalent(ref_samples, ref_tail, b2_samples, b2_tail, now, ctx="degenerate-ramp")
    h10, h11 = day0 + 10 * HOUR_SECONDS, day0 + 11 * HOUR_SECONDS
    # (i) hour 10: r 信用 30s + 游程内 60s + 末端结算 30s, totals 恒 (1000, 2000) = 开启
    # 快照(逐槽 ramp 各元与闭合式桶末元同为开启快照 —— 退化无插值)
    for fold in (ref_samples[h10], b2_samples[h10]):
        assert fold.cov == 120.0 and (fold.dl_total, fold.up_total) == (1000, 2000)
        assert fold.dl_max == 100 and fold.dl_wsum == 100 * 30.0
    # (ii) hour 11: 游程内 90s(4 槽 3 区间) + 末端结算 30s, totals 恒 (5000, 3000) = 开启快照
    for fold in (ref_samples[h11], b2_samples[h11]):
        assert fold.cov == 120.0 and (fold.dl_total, fold.up_total) == (5000, 3000)
        assert fold.dl_max == 0 and fold.up_max == 0 and fold.up_wsum == 0.0
    assert b2_samples[h11].credits == 2  # 桶级 1 笔(90s) + 末端结算 1 笔(30s)
    assert b2_tail == ref_tail == (day0 + 11 * HOUR_SECONDS + 2 * 60 + 10, (90, 40, 5100, 3100))


def test_b2_directed_mixed_rz_bucket(tmp_path):
    """r+z 混桶: wsum/max 来自 r 信用(逐位), totals 末笔 = 游程末端快照(末笔 merge),
    桶级合并与逐槽的信用区间序列同位; 两路字段分级 + seal 行 bitwise"""
    st = TrafficV4Store(str(tmp_path))
    key = GLOBAL_SERIES_KEY
    day0 = v4_date_str_epoch("2026-06-05")
    wm = day0 + 9 * HOUR_SECONDS
    s0 = (7_000_000, 8_000_000)
    s1 = (7_000_900, 8_000_600)
    st.append_records(
        key,
        "2026-06-05",
        (day0 + 10 * HOUR_SECONDS + 5, 30),
        (
            V4Sample(100, 50, s0[0], s0[1]),  # 10:00:05
            V4ZeroRun(6, s0[0], s0[1], None, s1[0], s1[1]),  # 槽 10:00:35..10:03:05(6 槽)
            V4Sample(300, 90, s1[0], s1[1]),  # 10:03:35: 结算末端信用(rate 面)
            V4ZeroRun(4, s1[0], s1[1], None, s1[0] + 500, s1[1] + 400),  # 槽 10:04:05..10:05:35(4 槽)
            V4Sample(400, 100, s1[0] + 600, s1[1] + 500),  # 10:06:05: 结算末端信用
        ),
        s0,
    )
    now = day0 + 13 * HOUR_SECONDS + 30
    dates = read_set_dates(st, key, now, wm, _WINDOW)
    parsed = st.read_day(key, dates[0])
    ref_samples, ref_tail, b2_samples, b2_tail = _credit_both_parsed(parsed)
    assert_b1_bitwise_equivalent(ref_samples, ref_tail, b2_samples, b2_tail, now, ctx="mixed-rz")
    h10 = day0 + 10 * HOUR_SECONDS
    for fold in (ref_samples[h10], b2_samples[h10]):
        # wsum: r 信用 (100,50)x30 + (300,90)x30(z 信用 +0.0 精确; 末笔 r 信用悬置)
        assert fold.dl_wsum == (100 + 300) * 30.0 and fold.up_wsum == (50 + 90) * 30.0
        assert (fold.dl_max, fold.up_max) == (300, 90)
        # cov: r 信用 2 笔 30s + z1 引导间隔并入 r 结算 30s + z1 桶级 150s + z1 末端结算
        # 30s + z2 桶级 90s + z2 末端结算 30s
        assert fold.cov == 30 * 4 + 150 + 90
        assert (fold.dl_total, fold.up_total) == (s1[0] + 500, s1[1] + 400)  # 末笔 = 末段游程末端快照
    assert b2_samples[h10].credits == 6  # r2 笔 + z 桶级 2 笔 + z 末端结算 2 笔
    assert b2_tail == ref_tail == (day0 + 10 * HOUR_SECONDS + 6 * 60 + 5, (400, 100, s1[0] + 600, s1[1] + 500))


def test_b2_directed_block_riding_watermark(tmp_path):
    """骑水位上下文块(B1/R1 边界): 块 A 骑 wm 界(11:00, wm = 10:00 桶)—— 封口部分
    [10:59:50, 11:00:00) 被 skip_through_hour 过滤, 保留部分 [11:00:00, 11:00:20) 照常
    入账, 其后跨块结算 [11:00:20, 11:00:50) 30s; 两路(参照无过滤尾部丢弃 vs 生产入口
    过滤)字段分级相等, hour 11 cov = 50s 逐位钉死"""
    st = TrafficV4Store(str(tmp_path))
    key = GLOBAL_SERIES_KEY
    day0 = v4_date_str_epoch("2026-06-05")
    wm = day0 + 10 * HOUR_SECONDS
    st.append_records(
        key,
        "2026-06-05",
        (day0 + 10 * HOUR_SECONDS + 59 * 60 + 50, 30),
        (V4Sample(100, 50, 1000, 2000), V4Sample(200, 60, 2000, 3000)),  # 10:59:50 + 11:00:20
        (1000, 2000),
    )
    st.append_records(
        key, "2026-06-05", (day0 + 11 * HOUR_SECONDS + 50, 30), (V4Sample(300, 90, 3000, 4000), ), (3000, 4000)
    )  # 11:00:50: 与 A 末槽 gap 30 连续
    now = day0 + 13 * HOUR_SECONDS + 30
    dates = read_set_dates(st, key, now, wm, _WINDOW)
    assert dates == ("2026-06-05", )
    ref_samples, ref_tail, _rs = reference_full_credit(st, key, dates, wm)
    b2_samples, b2_tail, _bs = b1_production_credit(st, key, dates, wm)
    assert_b1_bitwise_equivalent(ref_samples, ref_tail, b2_samples, b2_tail, now, ctx="riding-wm")
    h11 = day0 + 11 * HOUR_SECONDS
    for fold in (ref_samples[h11], b2_samples[h11]):
        assert fold.cov == 50.0 and fold.credits == 2  # 保留 20s + 跨块结算 30s
        assert fold.dl_max == 200 and (fold.dl_total, fold.up_total) == (2000, 3000)
    assert set(ref_samples) == {h11}  # 封口部分 hour 10 两路同滤(参照尾部丢弃 / 生产入口过滤)


def test_b2_credit_cost_rows_not_slots(tmp_path, monkeypatch):
    """B2 成本微基准(计划 §02.2 候选实测的单元级复验, §04 S1): 成本 ∝ 记录行数而非
    槽位数。语料 = 单条 86400 槽 z 游程块 + z-heavy 1.5s 栅格全天。确定性结构断言:
    _agg_credit_hours 调用数 B2 <= 2x行数+50(每记录至多 1 笔 pending 结算 + 每桶 1 笔)
    且 <= 逐槽参照 / 10(参照每正长度槽区间 1 笔, ∝ 槽数); 耗时数字 print(量级证据,
    不作时序断言 —— 时序 flaky)"""
    # 语料 1: 单条 86400 槽 z 游程(1 行, dt_ms = DT_MS_MAX = 1 天毫秒, spacing 1.0s)
    day0 = v4_date_str_epoch("2026-06-05")
    blk = V4Block(day0, 1.0, 1000, 2000, (V4ZeroRun(86400, 1000, 2000, DT_MS_MAX, 2000, 3000), ))
    big_day = parse_v4_day_text(format_v4_day_text(GLOBAL_SERIES_KEY, (blk, )))
    # 语料 2: z-heavy 1.5s 栅格全天(行长槽多 —— 空闲系列真实形态)
    store, info = _build_corpus_ex(tmp_path, 3, "z-heavy", interval=1.5, exact_grid=True)
    (n_blocks, n_slots) = info[CORPUS_DATES[0]]
    heavy_day = store.read_day(GLOBAL_SERIES_KEY, CORPUS_DATES[0])
    heavy_rows = sum(len(b.records) for b in heavy_day.blocks)

    def run_once(parsed, impl):
        t0 = perf_counter()
        samples: dict = {}
        impl(samples, parsed, None, None, None)
        return perf_counter() - t0, samples

    # 耗时(未打点, 干净测量): 逐槽参照 vs B2 闭合式
    t_big_ref, _ = run_once(big_day, reference_slot_credit)
    t_big_b2, _ = run_once(big_day, _agg_mod._SampleAggMixin._agg_credit_day_file)
    t_heavy_ref, ref_samples = run_once(heavy_day, reference_slot_credit)
    t_heavy_b2, b2_samples = run_once(heavy_day, _agg_mod._SampleAggMixin._agg_credit_day_file)
    print(f"\n[b2-bench] 86400 槽单游程(1 行): 逐槽参照 {t_big_ref * 1000:.1f}ms vs "
          f"B2 闭合式 {t_big_b2 * 1000:.2f}ms")
    print(
        f"[b2-bench] z-heavy 1.5s 全天({heavy_rows} 行 / {n_slots} 槽 / {n_blocks} 块): "
        f"逐槽参照 {t_heavy_ref * 1000:.1f}ms vs B2 闭合式 {t_heavy_b2 * 1000:.2f}ms"
    )
    assert set(b2_samples) <= set(ref_samples)
    # 调用数(结构复杂度, 确定性): 打点 _agg_credit_hours(参照与生产共用入账原语)
    calls = {"n": 0}
    orig_credit = _agg_mod._SampleAggMixin._agg_credit_hours

    def _counting(pending, start, end, *a, **kw):
        calls["n"] += 1
        return orig_credit(pending, start, end, *a, **kw)

    monkeypatch.setattr(_agg_mod._SampleAggMixin, "_agg_credit_hours", staticmethod(_counting))

    def count_calls(parsed, impl):
        calls["n"] = 0
        samples: dict = {}
        impl(samples, parsed, None, None, None)
        return calls["n"]

    c_big_ref = count_calls(big_day, reference_slot_credit)
    c_big_b2 = count_calls(big_day, _agg_mod._SampleAggMixin._agg_credit_day_file)
    c_heavy_ref = count_calls(heavy_day, reference_slot_credit)
    c_heavy_b2 = count_calls(heavy_day, _agg_mod._SampleAggMixin._agg_credit_day_file)
    print(
        f"[b2-bench] merge 调用数: 单游程 参照 {c_big_ref} vs B2 {c_big_b2}; "
        f"z-heavy 参照 {c_heavy_ref} vs B2 {c_heavy_b2}(行数 {heavy_rows})"
    )
    assert c_big_ref >= 86400 - 1  # 逐槽: 每正长度槽区间 1 笔(86400 槽 86399 区间)
    assert c_big_b2 <= 52  # 闭合式: 24 个小时桶 + 尾部信用单区间 <= 25 笔(1 行)
    assert c_heavy_ref >= n_slots // 2  # z-heavy: 过半槽为 z 区间(逐槽 1 笔)
    assert c_heavy_b2 <= 2 * heavy_rows + 50  # 闭合式: 每记录至多 1 笔结算 + 每桶 1 笔
    assert c_big_b2 * 10 <= c_big_ref and c_heavy_b2 * 10 <= c_heavy_ref
