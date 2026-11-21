"""test_traffic_recovery_equivalence 测试计划: B1 恢复对拍守阵(plan 26-11-21-1546 S1;
D2 等价判据「聚合输出层逐位等价」+ §07 R1 边界上下文忠实)。harness 单点在
tests/traffic_recovery_support.py(语料合成 + 旧全量路径参照 + 对拍断言, P1c/B2 复用)。

## 测试计划(每个测试函数一条)
- test_b1_equivalence_random_corpus_three_phases: 随机合成语料(3 风格 x 6 种子)x 三水位
  相位(当日 fresh / 陈旧至昨日 / 无水位 fallback)—— 旧全量路径(参照: 全解析 + 全槽
  入账 + 尾部丢弃)vs B1 生产路径(字节级开放段 + 记账入口过滤): hour 折叠态逐字段
  bitwise / 完结小时 seal 行 bitwise(AggRow + format_agg_row 文本)/ 开放 pending 折叠态
  bitwise / 跨文件 tail 上下文逐位; 且 B1 处理槽 <= 参照全量槽(开放段只减不增)
- test_b1_equivalence_missing_file_chain_break: 读集中部天文件缺失 -> 两路 tail 同断链
  (None), 其后产出仍 bitwise 相等(缺文件断链形态)
- test_b1_equivalence_missing_last_file_breaks_tail_to_none: 缺失/空文件是读集最后一个
  文件(评审 P1b-1)-> 两路 tail 同归 None(参照实现 else 断链分支对齐钉住)
- test_b1_equivalence_empty_trailing_block_tail_preserved: 全封口空末块窄角(评审 P1b-3)
  —— wm 恰 23:00 + 末块 B 行后撕裂(blocks=())+ 次日 00:00 连续: 空末块回退前一有效
  块头重解, tail 接力恢复, hour 0 桶 = 结算 10s + 块内 30s
- test_b1_equivalence_empty_context_block_before_open_segment: 段首上下文块为空块窄角
  (评审 P1b-3 同族)—— 有效 B 行无记录夹在封口/保留块之间: 回退重解保跨块结算,
  hour 11 桶 cov = 35s
- test_b1_equivalence_torn_tail_variants: 撕裂尾两形态(末记录半行 / 末块 B 行半行)——
  两路坏行纪律同判, 产出 bitwise 相等(撕裂尾形态)
- test_b1_equivalence_end_to_end_recovery: 端到端 —— 真 _recover_series(mod.start)产出
  (pending 折叠态 / agg 补算 hour 行 / recovery_reads 计数)与参照全量路径一致
  (fresh + stale 两相位, 各自独立目录)
"""

import random

import pytest

from clock import FakeClock

from auto_qb.config import QbTraffic

from auto_qb.core.modules.traffic_sample_mod import GLOBAL_SERIES_KEY

from auto_qb.core.traffic_store import (
    HOUR_SECONDS,
    AggRow,
    TrafficV4Store,
    V4Sample,
    parse_v4_agg_text,
    v4_date_str_epoch,
)

from traffic_recovery_support import (
    assert_b1_bitwise_equivalent,
    b1_production_credit,
    read_set_dates,
    reference_full_credit,
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
        # pending 折叠态 bitwise(重建累计器)
        assert mod._agg_state(GLOBAL_SERIES_KEY).pending == ref_pending, f"[{phase}] pending 不等"
        # agg 补算 hour 行 == 参照 seal 行(水位行原样保留 + 补算行按 epoch 升序)
        parsed = parse_v4_agg_text(_agg_text(root, GLOBAL_SERIES_KEY))
        wm_row = AggRow("hour", wm, 7, 9, 3, 4, 500, 600, 3600)
        assert parsed.hours == (wm_row, ) + tuple(ref_rows), f"[{phase}] agg hour 行不等"
        # 埋点计数与 B1 镜像循环一致(production loop 接线面)
        reads = mod.recovery_reads[GLOBAL_SERIES_KEY]
        assert reads["day_dates"] == dates and reads["bound"] == "watermark"
        assert reads["slots"] == b1_slots, f"[{phase}] slots 计数不等: {reads['slots']} vs {b1_slots}"
        assert reads["new_hours"] == len(ref_rows)
