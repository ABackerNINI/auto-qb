"""test_traffic_group_cache 测试计划: 样本分组点列缓存(plan 26-11-18-0037 阶段 1 T1c-1)
—— _V4BucketDayCursor 游标模式改造为分组游标的增量面: 主断言 = 「缓存命中与冷算逐位
等价」(旧桶缓存电池 test_cache_polling_bitwise_equivalent 的转世, 按样本分组契约重钉)。

## 测试计划(每个测试函数一条)
- test_cold_seed_bitwise_equivalent: 冷态首拉(全新缓存)与 assemble_group_points 全量
  现算逐位等价 —— points/totals/stride/over_budget 四元组逐位对账(活跃 r 流 + z 游程 +
  n 断连混排)
- test_polling_bitwise_equivalent: 主阵 —— 仿真采样流(稳态变流/台阶/长 z 游程/游程闭合
  摊配/计数器重置/停机真空 65s/n 游程断连/跨本地午夜多天/记录 ts 相位漂移)逐拍轮询,
  每拍(写文件 -> 建栅格 -> 读天文件 -> 缓存路径)与冷算全量现算逐位等价; 白盒不变量:
  样本计数 N == len(ts)+base、marks 严格升序(同秒去重)
- test_polling_short_window_and_multi_day: 主阵(短窗 + 跨本地午夜多天面)—— 1m 窗窗沿
  高频掉样本 + 多天文件游标面, 逐拍逐位等价
- test_tail_group_true_value_updates_each_tick: 尾组恒真值且每 tick 更新 —— 追加样本后
  末组点 t/值随样本推进(无克隆无持有), 逐拍与冷算逐位等价
- test_stride_raises_on_new_marks: 缺口标记新增 -> k 上调组界整体重排(前缀差分现推),
  与冷算逐位等价(k 上调不是降级路径, 是组界平移的常态形态)
- test_over_budget_propagation: 缺口标记数 >= 500(预算数学不可达)-> over_budget=True
  如实标注 + stride = 窗内样本数(k 上限)+ 空值点一个不弃, 与冷算逐位等价
- test_tail_snapshot_handoff: 活尾快照整体替换面 —— 未落盘槽走活尾 -> 下一拍落盘磁盘
  接管(记录值/槽位与活尾形态恒等, 不重不漏不双计), 逐拍与冷算逐位等价
- test_tail_frozen_race_dedup: 活尾快照冻结竞态 —— 快照携带已落盘槽(同 ts 恒等形态)
  被去重丢弃, 与冷算(同款去重)逐位等价
- test_si_change_invalidates: 配置面失效(c)—— 采样间隔变更 -> 条目冷重建, 结果与
  新 si 下冷算逐位等价(消费下界/预期样本数/k 整体改变不得串值); 白盒: si 指纹更新
- test_day_shrink_and_delete_invalidates: 失效面(b)—— 天文件裁剪重写(size 缩 -> 游标
  校验不过)与天文件删除 -> 整条目冷重建, 各自与冷算逐位等价(不得以陈旧前缀和应答)
- test_cursor_corrupt_rebuilds_whitebox: 游标结构非法校验(fail-fast 同款)—— 白盒篡改
  天游标起点前缀 -> 下轮校验不过冷重建, 结果与冷算逐位等价
- test_first_date_advance_rebuilds: 读集前沿变化(c2)—— 窗滑动使最早读取日期更替 ->
  整条目冷重建(白盒锚 first_date 更替), 结果与冷算逐位等价(差分链起点重锚不得串值)
- test_sanitize_run_anchor_rebuilds_whitebox: 游程锚点滑出回看界(sanitize 防御路径)
  -> 整条目冷重建, 结果与冷算逐位等价
- test_prefix_compaction_invariant: 前缀死区压缩(白盒压低 _COMPACT_MIN_DEAD)—— 长轮询
  下 base 前移(数组对齐点推进)后逐拍仍与冷算逐位等价(基线和嵌入的尾差分不变式)
- test_lru_eviction_and_multi_key: LRU 上限逐出(超限最久未用先逐出)后重查冷算仍等价;
  多系列键(组图 M 成员键面)同实例互不串扰; 同输入重查恒等(幂等)
- test_over_budget_rise_and_fall_whitebox: over_budget 真回落跨拍(评审 #9)—— r/n 交替
  流(>=500 枚窗内标记)首拍 over_budget=True(stride = 窗内样本数), 窗推进过半标记滑出
  窗沿后回落 False/stride 回落 k_init, 两拍均与冷算逐位等价(白盒: marks 存活面计数)
- test_tail_eps_band_boundaries: eps 带边界两面(评审 #10)—— 活尾槽 ts = 磁盘末槽 +
  _V4_VACUUM_EPS_S 恰丢弃 / + 2 x _V4_VACUUM_EPS_S 保留, 各与冷算对账; guard_batch
  容差带内回退槽(s.ts = last - eps/2)不 raise
- test_dips_eps_band_regression_whitebox: ts 非降破例旁路(评审 #5 防御面, 白盒直驱)
  —— eps 带内回退槽入列 -> dips 登记 -> 组末 t = 组内 ts 最晚者(旁路全组取 max, 与
  冷算逐位对账); k=2 布景(窗内预期样本 501 > 500)破例位落组内旁路实际触发 + compact
  裁窗沿前破例位(窗沿前永不进组, 窗内破例位存活)
- test_run_prefix_trim_and_window_fully_slid: 开放项裁剪两支(评审 #11, 白盒压压缩阈)
  —— (a)窗基前移越过开放游程起点: 长空闲 z 流 base 越过 r0 后唤醒闭合(摊配经 cov[0]
  前缀 + 虚拟首项 acc 对齐算术守恒), 逐拍与冷算逐位等价; (b)窗全滑出(t0 越过全部
  样本): compact 全切支(前缀数组保底基线和 + 开放项全量折入 cov[0])后恢复采样闭合
  摊配仍逐位等价
- test_tail_close_with_open_run_rollback: 尾折闭合带开放项游程的回滚面(#6 连带守阵)
  —— 磁盘空闲 z 流(开放游程带项)+ 活尾唤醒 r 记录(尾折闭合摊配), 响应后回滚, 次拍
  逐位等价(cov 按引用还原: 闭合对象替换不损毁快照面)
- test_fail_fast_guards_whitebox: fail-fast 面白盒 —— guard_batch 持有槽/时序倒挂 raise;
  series_result 非 raw 段窗 raise; compact 无死区调用为无操作; 同刻病理槽序(对跨 0 ->
  覆盖 0)差分不归因(0,0) 定影(T1a test_zero_coverage_pair 同款防御面的折叠态直驱形)
- test_entry_stats_faces: 驻留账两形态 —— 无条目 no-entry / 有条约目含样本驻留与
  开放游程项计数(内存打印面, 基准电池 skipif 覆盖率形态下的覆盖面兜底)
- test_empty_read_set_and_window_before_data: 空读集(无天文件)-> 空态(stride=1)与
  窗整体在数据之前(冷种子空槽组分支), 与冷算逐位等价
- test_sanitize_run_anchor_rebuilds_whitebox 的白盒前置: 锚点/链基/标记位一并滑出
  (sanitize 清置支 + 重建支同路径覆盖)
- test_sanitize_n_only_stream_continue: sanitize 非重建支(未立游程 continue)—— 纯 n
  断连系列逐拍推进, 逐位等价 + 纯空值点面

线程/时钟纪律: 纯函数层 + V4DayCache 真文件(tmp_path, test.* 已内置 TMPDIR 不手工加
前缀); 轮询时刻为仿真推进值(不触系统时钟, 栅格由 build_grid(window, now, si) 现建);
活尾为直接构造的 LiveTail 快照(不触采样模块宿主); 代码/断言零 emoji 零图形符号;
writer 一律 interval_s=si(块标称间隔须与栅格采样间隔同源: 缺省时块首游程按标称间隔
摊槽, 读侧 dt 链与写侧名义链漂移会触发槽组时序守卫)。
"""
import os
import random

import pytest

from auto_qb.core import traffic_group_cache as gmod
from auto_qb.core.traffic_group_cache import V4SeriesGroupCache, _GroupFoldState
from auto_qb.core.traffic_grid import (
    _V4_SEAM_LOOKBACK_S,
    _V4_VACUUM_EPS_S,
    build_grid,
    v4_series_slots,
)
from auto_qb.core.traffic_group_assembly import assemble_group_points, group_null_lo
from auto_qb.core.traffic_store import (
    V4DayCache,
    V4Sample,
    v4_day_epoch,
    v4_day_file_path,
    v4_epoch_date_str,
)
from auto_qb.core.traffic_store_codec import LiveTail, V4Slot, v4_live_tail_slots

from test_traffic_grid_bucket_cache import _SeriesWriter

_SI = 2.0  # 仿真采样间隔(秒)
_BASE = 1_800_000_000 + 86_400  # 仿真锚点(固定 epoch, 仅作数据起点)

# ---------- 参照面与对账单点 ----------


def _cold_reference(days, grid, tail_slots, si):
    """冷算参照(traffic_qb T1b 冷算直连同式): 全部块平展 + 活尾槽按 ts 去重并入
    (同 ts 槽 = 已落盘恒等形态, 保留严格更晚后缀 —— 与端点面 _tail_slots_plain 同判)
    -> 分组装配"""
    blocks = tuple(b for _d, p in days if p for b in p.blocks)
    slots = v4_series_slots(blocks)
    if tail_slots and slots:
        end = slots[-1].ts
        tail_slots = tuple(s for s in tail_slots if s.ts > end + _V4_VACUUM_EPS_S)
    return assemble_group_points(slots + tuple(tail_slots), grid.t0, grid.t1, si)


def _assert_bitwise(got, want, tag):
    """四元组逐位对账(points/totals 逐元素, stride/over_budget 标量)"""
    assert got.points == want.points, (
        f"{tag}: points 逐位不等 len {len(got.points)}/{len(want.points)} "
        f"首个差异 {next(((i, x, y) for i, (x, y) in enumerate(zip(got.points, want.points)) if x != y), None)}"
    )
    assert got.totals == want.totals, (
        f"{tag}: totals 逐位不等 "
        f"首个差异 {next(((i, x, y) for i, (x, y) in enumerate(zip(got.totals, want.totals)) if x != y), None)}"
    )
    assert got.stride == want.stride, f"{tag}: stride {got.stride} != {want.stride}"
    assert got.over_budget == want.over_budget, f"{tag}: over_budget {got.over_budget} != {want.over_budget}"


def _polling(tmp_path, key, window, polls, *, seed=2026_11_18, compact_min_dead=None):
    """仿真轮询主阵: 每拍(采样 -> 写文件 -> 建栅格 -> 读天文件 -> 缓存 vs 冷算)逐位对账,
    收集白盒不变量。阶段化数据面 = 稳态变流/台阶/长 z 游程/游程闭合摊配/计数器重置/
    停机真空/n 断连/跨本地午夜(起点钉在本地午夜前 90s)。返回 (违例数, 末拍折叠态)。"""
    old = None
    if compact_min_dead is not None:
        old = gmod._COMPACT_MIN_DEAD
        gmod._COMPACT_MIN_DEAD = compact_min_dead
    try:
        writer = _SeriesWriter(str(tmp_path), key, interval_s=_SI)
        daycache = V4DayCache(str(tmp_path))
        cache = V4SeriesGroupCache()
        t = v4_day_epoch(_BASE) - 90.0  # 本地午夜前 90s: 仿真中段跨日(多天文件面)
        rng = random.Random(seed)
        bad = 0
        st = None
        for poll in range(polls):
            ts = t + 0.5  # 记录 ts 取半秒偏移(相位漂移常态)
            phase = poll % 30
            if phase == 28:
                # 停机真空: 跳过 65s 后关块重写(组界缝 > 60s = 停机洞 -> 空值标记 + 摊配)
                t += 65.0
                ts = t + 0.5
                writer.reopen()
                writer.r(ts, 60_000, 30_000)
            elif phase < 10:
                writer.r(ts, 40_000 + rng.randrange(0, 30_000), 10_000 + rng.randrange(0, 9_000))
            elif phase < 14:
                writer.r(ts, 90_000, 90_000)  # 台阶(恒值段后跳变 -> 游程闭合摊配面)
            elif phase < 20:
                writer.z(ts + 1.0, 1)  # 空闲 z 游程(开放游程跨 tick)
            elif phase == 20:
                writer.r(ts, 50_000, 50_000)  # 台阶出游程 -> 摊配回写游程项
            elif phase < 24:
                writer.r(ts, 50_000, 50_000)
            elif phase < 27:
                writer.n(ts, 1)  # 断连(n 游程 -> 显式空值点)
            elif phase == 27:
                writer.reopen()  # 计数器重置形态(新块新基线)
                writer.r(ts, 70_000, 20_000)
            else:
                writer.r(ts, 70_000, 20_000)
                if phase == 29:
                    writer.reopen()
            writer.write()
            t += (2.0 if poll % 5 else 3.0) + 0.25
            grid = build_grid(window, t, _SI)
            days = daycache.read_window(key, grid.t0 - _SI - _V4_SEAM_LOOKBACK_S, grid.t1)
            res, _blocks, tail_slots = cache.series_result(key, days, grid, (), _SI)
            try:
                _assert_bitwise(res, _cold_reference(days, grid, tail_slots, _SI), f"poll={poll} phase={phase}")
            except AssertionError as e:
                bad += 1
                print(f"[polling anomaly] {e}")
                if bad > 3:
                    break
            st = cache._entries.get((key, window)).st
            assert st.N == len(st.ts) + st.base  # 白盒: 样本计数与数组对齐恒等
            assert all(a < b for a, b in zip(st.marks, st.marks[1:]))  # marks 严格升序(同秒去重)
        return bad, st
    finally:
        if compact_min_dead is not None:
            gmod._COMPACT_MIN_DEAD = old


# ---------- 主阵: 逐位等价 ----------


def test_cold_seed_bitwise_equivalent(tmp_path):
    """冷态首拉(全新缓存)与冷算全量现算逐位等价(四元组对账)"""
    key = "global"
    writer = _SeriesWriter(str(tmp_path), key, interval_s=_SI)
    t = _BASE
    t_end = t
    for i in range(40):
        ts = t + 0.5 + i * _SI
        if i % 9 == 4:
            writer.z(ts + 1.0, 1)
        elif i % 9 == 7:
            writer.n(ts, 1)
        else:
            writer.r(ts, 40_000 + (i % 5) * 3000, 12_000 + (i % 3) * 1000)
        t_end = ts
    writer.write()
    now = t_end + 3 * _SI
    grid = build_grid("30m", now, _SI)
    days = V4DayCache(str(tmp_path)).read_window(key, grid.t0 - _SI - _V4_SEAM_LOOKBACK_S, grid.t1)
    cache = V4SeriesGroupCache()
    res, blocks, tail_slots = cache.series_result(key, days, grid, (), _SI)
    assert blocks  # 读集非空(数据面已写)
    assert tail_slots == ()
    _assert_bitwise(res, _cold_reference(days, grid, (), _SI), "cold-seed")


def test_polling_bitwise_equivalent(tmp_path):
    """主阵: 混排采样流逐拍轮询(3h 窗), 每拍与冷算逐位等价 + 白盒不变量"""
    bad, st = _polling(tmp_path, "global", "3h", 90)
    assert bad == 0
    assert st is not None and st.N > 0


def test_polling_short_window_and_multi_day(tmp_path):
    """主阵(短窗 + 跨本地午夜多天面): 1m 窗窗沿高频掉样本 + 多天文件游标面"""
    bad, _st = _polling(tmp_path, "global", "1m", 70, seed=777)
    assert bad == 0


def test_tail_group_true_value_updates_each_tick(tmp_path):
    """尾组恒真值且每 tick 更新: 追加样本 -> 末组点 t/值推进(无克隆无持有), 逐拍与
    冷算逐位等价; 窗内无缺口时末点 t == 最新样本 ts"""
    key = "global"
    writer = _SeriesWriter(str(tmp_path), key, interval_s=_SI)
    cache = V4SeriesGroupCache()
    daycache = V4DayCache(str(tmp_path))
    t = _BASE
    for i in range(25):
        ts = t + i * _SI  # 整值对齐(块首 B.start = int(ts) = ts, 记录槽链恒落在标称位)
        writer.r(ts, 50_000, 25_000)
        writer.write()
        now = ts + _SI
        grid = build_grid("1m", now, _SI)
        days = daycache.read_window(key, grid.t0 - _SI - _V4_SEAM_LOOKBACK_S, grid.t1)
        res, _blocks, tail_slots = cache.series_result(key, days, grid, (), _SI)
        _assert_bitwise(res, _cold_reference(days, grid, tail_slots, _SI), f"tail tick={i}")
        assert tail_slots == ()
        pts = res.points
        assert pts and pts[-1]["t"] == ts  # 末点 = 最新真实样本(尾组恒真值, 无持有克隆)
    assert res.points[-1]["dl"] is not None  # 尾组有值(非空态非断链)


def test_stride_raises_on_new_marks(tmp_path):
    """缺口标记新增 -> k 上调组界整体重排(前缀差分现推), 与冷算逐位等价: r/n 交替流
    逐拍新增标记逼近预算(组点 + 空值点 > 500)-> k 从 k_init 连续上调, 未达 500 标记
    前 over_budget 恒 False(k 上调不是降级路径, 是组界平移的常态形态)"""
    key = "global"
    writer = _SeriesWriter(str(tmp_path), key, interval_s=_SI)
    cache = V4SeriesGroupCache()
    daycache = V4DayCache(str(tmp_path))
    t = _BASE
    stride_seq = []
    ob_seq = []
    for i in range(990):
        ts = t + 0.5 + i * _SI
        if i % 2:
            writer.n(ts, 1)  # 断连游程逐拍新增标记(每拍 1 枚 n 槽 = 1 标记)
        else:
            writer.r(ts, 45_000, 22_000)
        writer.write()
        now = ts + _SI
        grid = build_grid("3h", now, _SI)
        days = daycache.read_window(key, grid.t0 - _SI - _V4_SEAM_LOOKBACK_S, grid.t1)
        res, _blocks, tail_slots = cache.series_result(key, days, grid, (), _SI)
        _assert_bitwise(res, _cold_reference(days, grid, tail_slots, _SI), f"stride tick={i}")
        stride_seq.append(res.stride)
        ob_seq.append(res.over_budget)
    assert all(not ob for ob in ob_seq)  # 全程未达不可达角(over_budget 恒 False)
    assert stride_seq[40] == stride_seq[100]  # 标记未顶破预算段 k 恒定(k_init)
    assert stride_seq[-1] > stride_seq[100]  # 标记逼近预算 -> k 上调(组界整体重排)
    assert stride_seq == sorted(stride_seq)  # k 单调不减(预算条件随标记数收紧)


def test_over_budget_propagation(tmp_path):
    """缺口标记数 >= 500(预算数学不可达)-> over_budget=True + stride = 窗内样本数
    (k 上限)+ 空值点一个不弃, 与冷算逐位等价(诚实优先于预算)"""
    key = "global"
    writer = _SeriesWriter(str(tmp_path), key, interval_s=_SI)
    t = _BASE
    for i in range(1100):
        ts = t + 0.5 + i * _SI
        if i % 2:
            writer.n(ts, 1)  # 550 枚 n 槽 -> >= 500 标记
        else:
            writer.r(ts, 40_000, 20_000)
    writer.write()
    now = t + 0.5 + 1100 * _SI
    grid = build_grid("3h", now, _SI)
    days = V4DayCache(str(tmp_path)).read_window(key, grid.t0 - _SI - _V4_SEAM_LOOKBACK_S, grid.t1)
    cache = V4SeriesGroupCache()
    res, _blocks, tail_slots = cache.series_result(key, days, grid, (), _SI)
    _assert_bitwise(res, _cold_reference(days, grid, tail_slots, _SI), "over-budget")
    assert res.over_budget is True
    assert res.stride == 550  # k 上限 = 窗内样本数(550 r 槽)
    n_null = sum(1 for p in res.points if p["dl"] is None and p["up"] is None)
    assert n_null == 550  # 空值点一个不弃(缺口显式空值语义不弃)


# ---------- 活尾合流(整体替换面 / 回滚) ----------


def test_tail_snapshot_handoff(tmp_path):
    """活尾快照整体替换面: 未落盘槽走活尾 -> 下一拍落盘磁盘接管 —— 手法: 每拍磁盘
    写 1 条记录(r 记录), 活尾 = 下一条同构记录(值/槽位按 writer 同款增量预测, 下一拍
    writer 落盘的记录与活尾记录逐字段恒等 -> 不重不漏不双计), 逐拍与冷算逐位等价。"""
    key = "global"
    writer = _SeriesWriter(str(tmp_path), key, interval_s=_SI)
    cache = V4SeriesGroupCache()
    daycache = V4DayCache(str(tmp_path))
    t = _BASE
    for i in range(30):
        ts = t + 0.5 + i * _SI
        # 活尾记录 = 下一拍才落盘的记录: 值按 writer 增量口径预测(dt = 标称 si)
        dr, ur = 48_000 + (i % 4) * 2000, 24_000
        tail = LiveTail(
            block_open=True,
            head_pending=False,
            start_epoch=int(ts) - 120,
            interval_s=_SI,
            projected_ts=float(ts + _SI),
            records=(
                V4Sample(dr, ur, writer.dl + int(round(dr * _SI)), writer.up + int(round(ur * _SI)), int(_SI * 1000)),
            ),
            open_run=None,
        )
        writer.r(ts, dr, ur)  # 磁盘记录(与上一拍活尾记录恒等 —— 活尾->磁盘接管面)
        writer.write()
        now = ts + _SI
        grid = build_grid("5m", now, _SI)
        days = daycache.read_window(key, grid.t0 - _SI - _V4_SEAM_LOOKBACK_S, grid.t1)
        res, _blocks, tail_slots = cache.series_result(key, days, grid, v4_live_tail_slots(tail), _SI)
        assert len(tail_slots) == 1 and tail_slots[0].ts == ts + _SI  # 活尾槽在磁盘链尾之后
        _assert_bitwise(res, _cold_reference(days, grid, tail_slots, _SI), f"handoff tick={i}")
        st = cache._entries.get((key, "5m")).st
        assert st.N == len(st.ts) + st.base  # 白盒: 活尾折叠响应后回滚(不入持久态)
        assert st.prev_chain_end is None or st.prev_chain_end <= ts  # 链终值不含活尾槽


def test_tail_frozen_race_dedup(tmp_path):
    """活尾快照冻结竞态: 快照携带已落盘槽(同 ts 恒等形态)被去重丢弃 -> 不双计,
    与冷算(同款去重)逐位等价"""
    key = "global"
    writer = _SeriesWriter(str(tmp_path), key, interval_s=_SI)
    t = _BASE
    for i in range(10):
        writer.r(t + 0.5 + i * _SI, 46_000, 23_000)
    writer.write()
    # 末槽位 = 块首(B.start = int(首记录 ts))起标称推进 -> 第 i 条槽 = _BASE + 2*i
    last_slot_ts = _BASE + 9 * _SI
    now = last_slot_ts + _SI
    grid = build_grid("1m", now, _SI)
    days = V4DayCache(str(tmp_path)).read_window(key, grid.t0 - _SI - _V4_SEAM_LOOKBACK_S, grid.t1)
    # 快照携带末条已落盘记录(同 ts): 冷算参照与缓存走同一 raw_tail 输入面
    tail = LiveTail(
        block_open=True,
        head_pending=False,
        start_epoch=_BASE,
        interval_s=_SI,
        projected_ts=float(last_slot_ts),
        records=(V4Sample(46_000, 23_000, 460_000, 230_000, int(_SI * 1000)), ),
        open_run=None,
    )
    raw_tail = v4_live_tail_slots(tail) + (
        # eps 带边界两面(评审 #10): 恰在容差带上(= end + eps)-> 丢弃; 带外一步
        # (+ 2 x eps)-> 保留(各与冷算同款去重对账, 判别力不依赖参照面常数巧合)
        V4Slot(ts=last_slot_ts + _V4_VACUUM_EPS_S, dt_s=_SI, obs=(46_000, 23_000, 460_000, 230_000), is_zero=False),
        V4Slot(ts=last_slot_ts + 2 * _V4_VACUUM_EPS_S, dt_s=_SI, obs=(46_000, 23_000, 460_000, 230_000), is_zero=False),
    )
    cache = V4SeriesGroupCache()
    res, _blocks, tail_slots = cache.series_result(key, days, grid, raw_tail, _SI)
    assert tail_slots == (raw_tail[-1], )  # 同 ts 槽与 eps 带内槽丢弃, 带外一步槽保留
    _assert_bitwise(res, _cold_reference(days, grid, raw_tail, _SI), "frozen-race")


# ---------- 失效面 ----------


def test_si_change_invalidates(tmp_path):
    """配置面失效(c): 采样间隔变更 -> 条目冷重建, 与新 si 冷算逐位等价(不串值);
    白盒: 条目 si 指纹更新"""
    key = "global"
    writer = _SeriesWriter(str(tmp_path), key, interval_s=_SI)
    for i in range(20):
        writer.r(_BASE + 0.5 + i * _SI, 50_000, 25_000)
    writer.write()
    daycache = V4DayCache(str(tmp_path))
    cache = V4SeriesGroupCache()
    grid = build_grid("1m", _BASE + 60.0, _SI)
    days = daycache.read_window(key, grid.t0 - _SI - _V4_SEAM_LOOKBACK_S, grid.t1)
    cache.series_result(key, days, grid, (), _SI)
    ent = cache._entries.get((key, "1m"))
    assert ent is not None and ent.si == _SI
    si2 = 4.0
    grid2 = build_grid("1m", _BASE + 65.0, si2)
    days2 = daycache.read_window(key, grid2.t0 - si2 - _V4_SEAM_LOOKBACK_S, grid2.t1)
    res2, _blocks, tail2 = cache.series_result(key, days2, grid2, (), si2)
    ent2 = cache._entries.get((key, "1m"))
    assert ent2 is not None and ent2.si == si2  # 指纹更新(条目按新 si 重建)
    _assert_bitwise(res2, _cold_reference(days2, grid2, tail2, si2), "si-change")


def test_day_shrink_and_delete_invalidates(tmp_path):
    """失效面(b): 天文件裁剪重写(size 缩 -> 游标校验不过)与天文件删除 -> 整条目
    冷重建, 各自与冷算逐位等价(不得以陈旧前缀和应答)"""
    key = "global"
    writer = _SeriesWriter(str(tmp_path), key, interval_s=_SI)
    for i in range(30):
        writer.r(_BASE + 0.5 + i * _SI, 50_000 + i * 100, 25_000)
    writer.write()
    daycache = V4DayCache(str(tmp_path))
    cache = V4SeriesGroupCache()
    grid = build_grid("1m", _BASE + 80.0, _SI)
    days = daycache.read_window(key, grid.t0 - _SI - _V4_SEAM_LOOKBACK_S, grid.t1)
    cache.series_result(key, days, grid, (), _SI)

    # 裁剪重写: 只留前 10 条记录(结构变化 -> 游标校验不过 -> 冷重建)
    path = v4_day_file_path(str(tmp_path), key, v4_epoch_date_str(_BASE))
    lines = open(path, encoding="utf-8").read().splitlines()
    open(path, "w", encoding="utf-8", newline="\n").write("\n".join(lines[:11]) + "\n")
    grid2 = build_grid("1m", _BASE + 110.0, _SI)
    days2 = daycache.read_window(key, grid2.t0 - _SI - _V4_SEAM_LOOKBACK_S, grid2.t1)
    res2, _blocks, tail2 = cache.series_result(key, days2, grid2, (), _SI)
    _assert_bitwise(res2, _cold_reference(days2, grid2, tail2, _SI), "day-shrink")

    # 天文件删除(缓存面缺失哨兵生效) -> 冷重建
    os.remove(path)
    grid3 = build_grid("1m", _BASE + 115.0, _SI)
    days3 = daycache.read_window(key, grid3.t0 - _SI - _V4_SEAM_LOOKBACK_S, grid3.t1)
    res3, _blocks, tail3 = cache.series_result(key, days3, grid3, (), _SI)
    _assert_bitwise(res3, _cold_reference(days3, grid3, tail3, _SI), "day-delete")


def test_cursor_corrupt_rebuilds_whitebox(tmp_path):
    """游标结构非法校验(fail-fast 同款, 白盒): 篡改天游标起点前缀 -> 下轮校验不过
    冷重建, 结果与冷算逐位等价"""
    key = "global"
    writer = _SeriesWriter(str(tmp_path), key, interval_s=_SI)
    for i in range(15):
        writer.r(_BASE + 0.5 + i * _SI, 52_000, 26_000)
    writer.write()
    daycache = V4DayCache(str(tmp_path))
    cache = V4SeriesGroupCache()
    grid = build_grid("1m", _BASE + 40.0, _SI)
    days = daycache.read_window(key, grid.t0 - _SI - _V4_SEAM_LOOKBACK_S, grid.t1)
    cache.series_result(key, days, grid, (), _SI)
    ent = cache._entries.get((key, "1m"))
    date_str = next(iter(ent.day_cursors))
    cur = ent.day_cursors[date_str]
    cur.starts = cur.starts + (cur.cur_start if cur.cur_start is not None else 0, )  # 结构性篡改
    grid2 = build_grid("1m", _BASE + 45.0, _SI)
    days2 = daycache.read_window(key, grid2.t0 - _SI - _V4_SEAM_LOOKBACK_S, grid2.t1)
    res2, _blocks, tail2 = cache.series_result(key, days2, grid2, (), _SI)
    _assert_bitwise(res2, _cold_reference(days2, grid2, tail2, _SI), "cursor-corrupt")


def test_first_date_advance_rebuilds(tmp_path):
    """读集前沿变化(c2): 窗滑动使最早读取日期更替 -> 整条目冷重建(白盒锚 first_date
    更替), 结果与冷算逐位等价(差分链起点重锚不得串值)。数据面: 长 z 游程铺满两天 +
    末端活跃 r 段(游程锚点保持新鲜 —— 与 sanitize 面隔离, 冷重建纯由 c2 触发)。"""
    key = "global"
    writer = _SeriesWriter(str(tmp_path), key, interval_s=_SI)
    day0 = v4_day_epoch(_BASE)
    writer.z(day0 + 100.0, 49)  # 首段 z(锚 day0+1..day0+98, 标称 2s 摊槽)
    writer.r(day0 + 101.0, 46_000, 23_000)
    writer.z(day0 + 86_101.0, 43_000)  # 空闲游程铺满前半(dt 86000s <= 写侧 86400s 上限)
    writer.z(day0 + 171_700.0, 42_800)  # 空闲游程铺满后半(dt 85599s)
    t_tail = day0 + 171_701.0
    for i in range(100):
        writer.r(t_tail + i * _SI, 52_000 + (i % 6) * 1500, 26_000)  # 末端活跃段(游程锚新鲜)
    writer.write()
    daycache = V4DayCache(str(tmp_path))
    cache = V4SeriesGroupCache()
    now = t_tail + 100 * _SI
    grid = build_grid("1m", now, _SI)
    days = daycache.read_window(key, grid.t0 - _SI - _V4_SEAM_LOOKBACK_S, grid.t1)
    cache.series_result(key, days, grid, (), _SI)
    ent = cache._entries.get((key, "1m"))
    first_before = ent.first_date
    assert first_before == v4_epoch_date_str(day0)  # 前沿 = 数据首日
    # 窗推进跨日: read_lo 滑过数据首日 -> 最早读取日期更替 -> c2 冷重建
    now2 = now + 1000.0
    grid2 = build_grid("1m", now2, _SI)
    days2 = daycache.read_window(key, grid2.t0 - _SI - _V4_SEAM_LOOKBACK_S, grid2.t1)
    assert days2[0][0] != first_before  # 前沿确实更替(c2 前提)
    res2, _blocks, tail2 = cache.series_result(key, days2, grid2, (), _SI)
    _assert_bitwise(res2, _cold_reference(days2, grid2, tail2, _SI), "first-date")


def test_sanitize_run_anchor_rebuilds_whitebox(tmp_path):
    """游程锚点滑出回看界(sanitize 防御路径, 白盒): 开放游程锚点置为远窗前 -> 下轮
    sanitize True 冷重建, 结果与冷算逐位等价"""
    key = "global"
    writer = _SeriesWriter(str(tmp_path), key, interval_s=_SI)
    for i in range(15):
        writer.r(_BASE + 0.5 + i * _SI, 54_000, 27_000)
    writer.write()
    daycache = V4DayCache(str(tmp_path))
    cache = V4SeriesGroupCache()
    grid = build_grid("1m", _BASE + 40.0, _SI)
    days = daycache.read_window(key, grid.t0 - _SI - _V4_SEAM_LOOKBACK_S, grid.t1)
    cache.series_result(key, days, grid, (), _SI)
    ent = cache._entries.get((key, "1m"))
    # 白盒: 锚点 + 链基 + 标记位一并滑出回看界(sanitize 的清置支与重建支同路径)
    ent.st.dl.anchor_ts = _BASE - 200_000.0
    ent.st.prev_slot = (_BASE - 200_000.0, 1, 1)
    ent.st.marked_ts = _BASE - 200_000.0
    grid2 = build_grid("1m", _BASE + 45.0, _SI)
    days2 = daycache.read_window(key, grid2.t0 - _SI - _V4_SEAM_LOOKBACK_S, grid2.t1)
    res2, _blocks, tail2 = cache.series_result(key, days2, grid2, (), _SI)
    _assert_bitwise(res2, _cold_reference(days2, grid2, tail2, _SI), "sanitize-anchor")


def test_prefix_compaction_invariant(tmp_path):
    """前缀死区压缩(白盒压低 _COMPACT_MIN_DEAD): 长轮询下 base 前移后逐拍仍与冷算
    逐位等价(基线和嵌入的尾差分不变式)"""
    bad, st = _polling(tmp_path, "global", "5m", 220, seed=42, compact_min_dead=16)
    assert bad == 0
    assert st.base > 0  # 压缩确实发生(对齐点前移)


# ---------- LRU 与多键隔离 ----------


def test_lru_eviction_and_multi_key(tmp_path):
    """LRU 上限逐出(超限最久未用先逐出)后重查冷算仍等价; 多系列键(组图 M 成员键面)
    同实例互不串扰; 同输入重查恒等(幂等)"""
    daycache = V4DayCache(str(tmp_path))
    cache = V4SeriesGroupCache(max_entries=3)
    keys = ("global", "torrent:aa", "torrent:bb")
    for k in keys:
        writer = _SeriesWriter(str(tmp_path), k, interval_s=_SI)
        for i in range(10):
            writer.r(_BASE + 0.5 + i * _SI, 50_000 + len(k) * 100, 25_000)
        writer.write()
    grid = build_grid("1m", _BASE + 40.0, _SI)
    for k in keys:
        days = daycache.read_window(k, grid.t0 - _SI - _V4_SEAM_LOOKBACK_S, grid.t1)
        cache.series_result(k, days, grid, (), _SI)
    assert len(cache._entries) == 3
    # 第四键入列 -> 最久未用(global)逐出
    writer = _SeriesWriter(str(tmp_path), "torrent:cc", interval_s=_SI)
    for i in range(10):
        writer.r(_BASE + 0.5 + i * _SI, 55_000, 27_000)
    writer.write()
    days = daycache.read_window("torrent:cc", grid.t0 - _SI - _V4_SEAM_LOOKBACK_S, grid.t1)
    cache.series_result("torrent:cc", days, grid, (), _SI)
    assert ("global", "1m") not in cache._entries  # LRU 逐出
    assert len(cache._entries) == 3
    # 逐出后重查 = 冷重建, 与冷算逐位等价; 同输入重查恒等(幂等)
    days = daycache.read_window("global", grid.t0 - _SI - _V4_SEAM_LOOKBACK_S, grid.t1)
    res_again, _blocks, _tail = cache.series_result("global", days, grid, (), _SI)
    _assert_bitwise(res_again, _cold_reference(days, grid, (), _SI), "rebuild-after-evict")
    res_idem, _b2, _t2 = cache.series_result("global", days, grid, (), _SI)
    assert res_idem == res_again
    # 多键互不串扰: 各键结果与其冷算逐位相等(逐键对账)
    for k in keys:
        days = daycache.read_window(k, grid.t0 - _SI - _V4_SEAM_LOOKBACK_S, grid.t1)
        res_k, _bk, _tk = cache.series_result(k, days, grid, (), _SI)
        _assert_bitwise(res_k, _cold_reference(days, grid, (), _SI), f"multi-key {k}")


# ---------- fail-fast / 防御面(白盒直驱) ----------


def test_fail_fast_guards_whitebox():
    """fail-fast 面白盒 —— guard_batch 时序倒挂 raise(持有槽拒收支已随持有面退役删除:
    V4Slot.is_hold 字段同批退役, v4_live_tail_slots 复原即纯槽序); series_result 非 raw
    段窗 raise; compact 无死区调用为无操作; 同刻病理槽序(对跨 0 -> 覆盖 0)差分不归因
    (0,0) 定影(T1a test_zero_coverage_pair 同款防御面的折叠态直驱形)"""
    st = gmod._GroupFoldState()
    # 时序倒挂(跨批衔接锚) = fail-fast
    st.guard_batch((V4Slot(ts=10.0, dt_s=2.0, obs=(10, 10, 100, 100), is_zero=False), ))
    with pytest.raises(ValueError, match="时序倒挂"):
        st.guard_batch((V4Slot(ts=5.0, dt_s=2.0, obs=(10, 10, 100, 100), is_zero=False), ), last=10.0)
    # eps 容差带内回退(s.ts = last - eps/2)不 raise(带内判据: 非降容差同款)
    st.guard_batch(
        (V4Slot(ts=10.0 - _V4_VACUUM_EPS_S / 2, dt_s=2.0, obs=(10, 10, 100, 100), is_zero=False), ), last=10.0
    )
    # 同刻病理槽序: 对跨 0 -> 覆盖 0, 差分不归因(0,0) 定影, 组值 0 线不炸; totals 照常
    st.feed(
        (
            V4Slot(ts=100.0, dt_s=2.0, obs=(10, 10, 100, 100), is_zero=False),
            V4Slot(ts=100.0, dt_s=5.0, obs=(20, 20, 200, 200), is_zero=False),
        ),
        0.0,
        200.0,
        0.0,
    )
    res = st.respond(0.0, 200.0, 2.0)
    # 两样本各成一组(k=1): 覆盖 0 不归因不造分母 -> 双 0 线(无缝链首 D4); totals
    # 快照差分照常入账(首样本基线缺失逐向 None, 次样本差分 100)
    assert res.points == ({"t": 100.0, "dl": 0, "up": 0}, {"t": 100.0, "dl": 0, "up": 0})
    assert res.totals == ({"t": 100.0, "dl": None, "up": None}, {"t": 100.0, "dl": 100, "up": 100})
    # compact 无死区调用(s <= 0)= 无操作
    st.compact(st.base)
    assert st.base == 0
    # 非 raw 段窗 = fail-fast
    cache = V4SeriesGroupCache()
    hour_grid = build_grid("3d", _BASE + 60.0, _SI)
    with pytest.raises(ValueError, match="raw"):
        cache.series_result("global", (), hour_grid, (), _SI)


def test_entry_stats_faces(tmp_path):
    """驻留账两形态 —— 无条目 no-entry / 有条约目含样本驻留与开放游程项计数(内存打印
    面, 基准电池 skipif 覆盖率形态下的覆盖面兜底)"""
    cache = V4SeriesGroupCache()
    assert cache.entry_stats("global", "1m") == "no-entry"
    key = "global"
    writer = _SeriesWriter(str(tmp_path), key, interval_s=_SI)
    for i in range(10):
        writer.r(_BASE + 0.5 + i * _SI, 50_000, 25_000)
    writer.write()
    grid = build_grid("1m", _BASE + 40.0, _SI)
    days = V4DayCache(str(tmp_path)).read_window(key, grid.t0 - _SI - _V4_SEAM_LOOKBACK_S, grid.t1)
    cache.series_result(key, days, grid, (), _SI)
    stats = cache.entry_stats(key, "1m")
    assert "样本驻留=" in stats and "开放游程项=" in stats and "base=" in stats


def test_empty_read_set_and_window_before_data(tmp_path):
    """空读集(无天文件)-> 空态(stride=1)与窗整体在数据之前(冷种子空槽组分支), 各自
    与冷算逐位等价"""
    key = "global"
    cache = V4SeriesGroupCache()
    # 空读集: 无任何天文件 -> 空点列空 totals, stride = 1(无装配面 k 兜底)
    grid = build_grid("1m", _BASE + 40.0, _SI)
    days = V4DayCache(str(tmp_path)).read_window(key, grid.t0 - _SI - _V4_SEAM_LOOKBACK_S, grid.t1)
    res, blocks, tail_slots = cache.series_result(key, days, grid, (), _SI)
    assert blocks == () and tail_slots == ()
    assert res.points == () and res.totals == ()
    assert res.stride == 1 and res.over_budget is False
    _assert_bitwise(res, _cold_reference(days, grid, (), _SI), "empty-read-set")
    # 窗整体在数据之前(块全在窗尾外 -> 冷种子空槽组分支: 游标停驻, 槽不喂不消费)
    writer = _SeriesWriter(str(tmp_path), key, interval_s=_SI)
    for i in range(10):
        writer.r(_BASE + 0.5 + i * _SI, 50_000, 25_000)
    writer.write()
    daycache = V4DayCache(str(tmp_path))
    grid2 = build_grid("1m", _BASE - 3600.0, _SI)
    days2 = daycache.read_window(key, grid2.t0 - _SI - _V4_SEAM_LOOKBACK_S, grid2.t1)
    res2, blocks2, tail2 = cache.series_result(key, days2, grid2, (), _SI)
    assert res2.points == () and res2.totals == ()
    _assert_bitwise(res2, _cold_reference(days2, grid2, tail2, _SI), "window-before-data")
    # 窗推入数据面(游标从停驻块续展) -> 与冷算逐位等价(空槽组分支后的续展面)
    grid3 = build_grid("1m", _BASE + 40.0, _SI)
    days3 = daycache.read_window(key, grid3.t0 - _SI - _V4_SEAM_LOOKBACK_S, grid3.t1)
    res3, _blocks, tail3 = cache.series_result(key, days3, grid3, (), _SI)
    _assert_bitwise(res3, _cold_reference(days3, grid3, tail3, _SI), "window-enters-data")


def test_sanitize_n_only_stream_continue(tmp_path):
    """sanitize 非重建支(未立游程 continue, n-only 流)—— 全断连系列(纯 n 槽, 游程
    恒未立)逐拍推进: sanitize 的游程检查按 continue 跳过(锚点 0.0 是初值哨兵),
    逐拍与冷算逐位等价, 响应 = 纯显式空值点面(无样本无组点)"""
    key = "torrent:nn"
    writer = _SeriesWriter(str(tmp_path), key, interval_s=_SI)
    daycache = V4DayCache(str(tmp_path))
    cache = V4SeriesGroupCache()
    d0 = v4_day_epoch(_BASE)
    writer.n(d0 + 10.0, 2)
    writer.write()
    grid = build_grid("1m", d0 + 30.0, _SI)
    days = daycache.read_window(key, grid.t0 - _SI - _V4_SEAM_LOOKBACK_S, grid.t1)
    res, _blocks, tail_slots = cache.series_result(key, days, grid, (), _SI)
    _assert_bitwise(res, _cold_reference(days, grid, tail_slots, _SI), "n-only-1")
    assert res.stride == 1 and res.points  # 0 样本 -> k 兜底 1, 空值点在列
    st = cache._entries.get((key, "1m")).st
    assert st.dl.value is None and st.up.value is None and st.N == 0  # 游程未立(纯 n 面)
    writer.n(d0 + 20.0, 2)
    writer.write()
    grid2 = build_grid("1m", d0 + 40.0, _SI)
    days2 = daycache.read_window(key, grid2.t0 - _SI - _V4_SEAM_LOOKBACK_S, grid2.t1)
    res2, _blocks, tail2 = cache.series_result(key, days2, grid2, (), _SI)
    _assert_bitwise(res2, _cold_reference(days2, grid2, tail2, _SI), "n-only-2")
    assert all(p["dl"] is None and p["up"] is None for p in res2.points)  # 纯空值点面


def test_over_budget_rise_and_fall_whitebox(tmp_path):
    """over_budget 真回落跨拍(评审 #9, 白盒)—— r/n 交替流(600 枚窗内标记 >= 500)首拍
    over_budget=True(stride = 窗内样本数 k 上限), 窗推进过半标记滑出窗沿后回落
    False/stride 回落 k_init, 两拍均与冷算逐位等价(回落是滑出窗沿的真语义, 非断言
    恒真前提)"""
    key = "global"
    writer = _SeriesWriter(str(tmp_path), key, interval_s=_SI)
    daycache = V4DayCache(str(tmp_path))
    cache = V4SeriesGroupCache()
    t = _BASE
    for i in range(1200):
        ts = t + 0.5 + i * _SI
        if i % 2:
            writer.n(ts, 1)  # 600 枚 n 槽(标记)
        else:
            writer.r(ts, 40_000, 20_000)
    writer.write()
    data_end = t + 0.5 + 1199 * _SI
    # 拍 1: 3h 窗全罩数据面 -> 窗内标记 600 >= 500 -> over_budget=True
    now1 = data_end + 2.0
    grid1 = build_grid("3h", now1, _SI)
    days1 = daycache.read_window(key, grid1.t0 - _SI - _V4_SEAM_LOOKBACK_S, grid1.t1)
    res1, _b1, tail1 = cache.series_result(key, days1, grid1, (), _SI)
    _assert_bitwise(res1, _cold_reference(days1, grid1, tail1, _SI), "ob-rise")
    assert res1.over_budget is True
    assert res1.stride == 600  # k 上限 = 窗内样本数
    st = cache._entries.get((key, "3h")).st
    assert len(st.marks) >= 500  # 白盒: 窗内标记存活面
    # 拍 2: 窗推进至数据中段 -> 过半标记滑出窗沿 -> 回落 False/stride 回落
    now2 = t + 12_000.0  # t0_2 = t + 1200: 标记存活面 ~300 < 500
    grid2 = build_grid("3h", now2, _SI)
    days2 = daycache.read_window(key, grid2.t0 - _SI - _V4_SEAM_LOOKBACK_S, grid2.t1)
    res2, _b2, tail2 = cache.series_result(key, days2, grid2, (), _SI)
    _assert_bitwise(res2, _cold_reference(days2, grid2, tail2, _SI), "ob-fall")
    assert res2.over_budget is False
    assert res2.stride < res1.stride  # k 上限(600)回落 k_init(11)
    st2 = cache._entries.get((key, "3h")).st
    assert len(st2.marks) < 500  # 白盒: 过半标记已滑出(裁到存活面)


def test_tail_eps_band_boundaries(tmp_path):
    """eps 带边界两面(评审 #10)—— 活尾槽 ts = 磁盘末槽 + _V4_VACUUM_EPS_S 恰丢弃
    (去重判据严格更晚)/ + 2 x _V4_VACUUM_EPS_S 保留并入装配, 各与冷算对账; guard_batch
    容差带内回退槽不 raise(fail-fast 判据的带内半边)。见 test_tail_frozen_race_dedup
    (边界槽并入其 raw_tail)与 test_fail_fast_guards_whitebox(带内回退)"""
    key = "global"
    writer = _SeriesWriter(str(tmp_path), key, interval_s=_SI)
    t = _BASE
    for i in range(10):
        writer.r(t + 0.5 + i * _SI, 46_000, 23_000)
    writer.write()
    last_slot_ts = _BASE + 9 * _SI  # 末槽位(块首链标称推进)
    now = last_slot_ts + _SI
    grid = build_grid("1m", now, _SI)
    days = V4DayCache(str(tmp_path)).read_window(key, grid.t0 - _SI - _V4_SEAM_LOOKBACK_S, grid.t1)
    cache = V4SeriesGroupCache()
    # 带上恰丢弃: 仅一枚 + eps 槽
    only_eps = (
        V4Slot(ts=last_slot_ts + _V4_VACUUM_EPS_S, dt_s=_SI, obs=(46_000, 23_000, 460_000, 230_000), is_zero=False),
    )
    res1, _b1, tail1 = cache.series_result(key, days, grid, only_eps, _SI)
    assert tail1 == ()  # 恰在容差带上 -> 丢弃
    _assert_bitwise(res1, _cold_reference(days, grid, only_eps, _SI), "eps-boundary-drop")
    # 带外一步保留: 仅一枚 + 2 x eps 槽
    two_eps = (
        V4Slot(ts=last_slot_ts + 2 * _V4_VACUUM_EPS_S, dt_s=_SI, obs=(46_000, 23_000, 460_000, 230_000), is_zero=False),
    )
    res2, _b2, tail2 = cache.series_result(key, days, grid, two_eps, _SI)
    assert tail2 == two_eps  # 带外一步 -> 保留
    _assert_bitwise(res2, _cold_reference(days, grid, two_eps, _SI), "eps-boundary-keep")


def test_run_prefix_trim_and_window_fully_slid(tmp_path):
    """开放项裁剪两支(评审 #11, 白盒压压缩阈)—— (a)窗基前移越过开放游程起点: 长空闲
    z 流 base 越过 r0(游程自首样本立起)后唤醒闭合, 摊配经 cov[0] 前缀 + 虚拟首项
    acc 对齐算术守恒, 逐拍与冷算逐位等价; (b)窗全滑出(t0 越过全部样本): compact
    全切支(前缀数组保底基线和 + 开放项全量折入 cov[0])后恢复采样闭合摊配仍逐位等价"""
    old = gmod._COMPACT_MIN_DEAD
    gmod._COMPACT_MIN_DEAD = 16
    try:
        key = "global"
        writer = _SeriesWriter(str(tmp_path), key, interval_s=_SI)
        daycache = V4DayCache(str(tmp_path))
        cache = V4SeriesGroupCache()
        t = v4_day_epoch(_BASE)
        anomalies = 0
        # 铺 200s 空闲 z 流(游程自首样本立起, r0 = 首样本位) + 逐拍轮询(1m 窗, 窗沿
        # 高频掉样本 -> 压缩触发 -> base 前移越过 r0, 开放项折入 cov[0] 前缀)
        for i in range(80):
            ts = t + 0.5 + i * _SI
            writer.z(ts + 1.0, 1)
            writer.write()
            now = ts + _SI
            grid = build_grid("1m", now, _SI)
            days = daycache.read_window(key, grid.t0 - _SI - _V4_SEAM_LOOKBACK_S, grid.t1)
            res, _blocks, tail_slots = cache.series_result(key, days, grid, (), _SI)
            try:
                _assert_bitwise(res, _cold_reference(days, grid, tail_slots, _SI), f"prefix-trim tick={i}")
            except AssertionError as e:
                anomalies += 1
                print(f"[prefix-trim anomaly] {e}")
        assert anomalies == 0
        st = cache._entries.get((key, "1m")).st
        # (a)支达成: 窗基越过游程起点的开放项已裁折入前缀(compact 同步 r0 前移到
        # base —— 裁剪即该形态的处理面, r0 >= base 恒成立, cov[0] > 0 证被裁项非空)
        assert st.base >= st.dl.r0
        assert st.dl.cov[0] > 0  # 被裁项覆盖已折入前缀(cov[0] = run_prefix 载体)
        assert st.dl.value == 0 and st.dl.r0 <= st.N  # 游程仍开放
        # (b)窗全滑出(游程仍开放时): 窗推过全部样本(数据日内, 不触 c2)-> compact
        # 全切支: 余下开放项全量折入 cov[0](前缀累计), 前缀数组保底基线和
        ts_last = t + 0.5 + 79 * _SI
        now_slide = ts_last + 120.0  # t0 = now - 60 越过全部样本
        grid_slide = build_grid("1m", now_slide, _SI)
        days_slide = daycache.read_window(key, grid_slide.t0 - _SI - _V4_SEAM_LOOKBACK_S, grid_slide.t1)
        res_slide, _blocks, tail_slide = cache.series_result(key, days_slide, grid_slide, (), _SI)
        _assert_bitwise(res_slide, _cold_reference(days_slide, grid_slide, tail_slide, _SI), "fully-slid")
        st_slide = cache._entries.get((key, "1m")).st
        assert st_slide.base == st_slide.N  # 全切: 数组对齐点 = 样本终点(窗内 0 样本)
        assert len(st_slide.ts) == 0 and st_slide.dl.cov[0] > 0  # 全切后开放覆盖全在前缀
        assert st_slide.dl.r0 == st_slide.N  # 开放项全部折入(游程仍开放, value 保持)
        # 唤醒闭合: 台阶 r 记录 -> 摊配跨全量被裁段(cov[0] 前缀 + 虚拟首项 acc 对齐,
        # 冷算被裁段全为 g=None 项: 份额弃入/acc 推进逐位同)—— 采样/窗沿单调推进
        # (t0 回退会回到已裁样本区, 违反裁剪地平线单调前提)
        ts_wake = now_slide + 2.0
        writer.r(ts_wake, 80_000, 40_000)
        writer.write()
        now_wake = ts_wake + _SI
        grid_wake = build_grid("1m", now_wake, _SI)
        days_wake = daycache.read_window(key, grid_wake.t0 - _SI - _V4_SEAM_LOOKBACK_S, grid_wake.t1)
        res_wake, _blocks, tail_wake = cache.series_result(key, days_wake, grid_wake, (), _SI)
        _assert_bitwise(res_wake, _cold_reference(days_wake, grid_wake, tail_wake, _SI), "prefix-trim-wake")
        st_wake = cache._entries.get((key, "1m")).st
        assert st_wake.dl.value == writer.dl  # 游程已闭合重立(value = 快照 totals 面)
        # 恢复采样: 闭合摊配经前缀(虚拟首项)仍逐位等价
        ts_resume = now_wake + 2.0
        writer.r(ts_resume, 85_000, 42_000)
        writer.write()
        grid_resume = build_grid("1m", ts_resume + _SI, _SI)
        days_resume = daycache.read_window(key, grid_resume.t0 - _SI - _V4_SEAM_LOOKBACK_S, grid_resume.t1)
        res_resume, _blocks, tail_resume = cache.series_result(key, days_resume, grid_resume, (), _SI)
        _assert_bitwise(res_resume, _cold_reference(days_resume, grid_resume, tail_resume, _SI), "resume-after-slide")
    finally:
        gmod._COMPACT_MIN_DEAD = old


def test_tail_close_with_open_run_rollback(tmp_path):
    """尾折闭合带开放项游程的回滚面(#6 连带守阵)—— 磁盘空闲 z 流(开放游程带项)+
    活尾唤醒 r 记录(尾折闭合摊配: fin 追加 + cov 对象替换), 响应后回滚, 次拍(活尾
    整体替换/磁盘照常推进)逐位等价 —— cov 按引用还原面的守阵: 闭合对象替换不得损毁
    快照按长度还原的开放项覆盖"""
    key = "global"
    writer = _SeriesWriter(str(tmp_path), key, interval_s=_SI)
    daycache = V4DayCache(str(tmp_path))
    cache = V4SeriesGroupCache()
    t = _BASE
    for i in range(12):  # 磁盘空闲 z 流(开放游程带项)
        writer.z(t + 0.5 + i * _SI + 1.0, 1)
    writer.write()
    bad = 0
    for i in range(6):
        ts = t + 0.5 + (12 + i) * _SI
        tail = LiveTail(
            block_open=True,
            head_pending=False,
            start_epoch=int(ts) - 120,
            interval_s=_SI,
            projected_ts=float(ts + 2.5),  # 磁盘末槽(ts+1)之后、窗尾(now=t+4)之前
            records=(V4Sample(80_000, 40_000, 120_000, 60_000, int(_SI * 1000)), ),
            open_run=None,
        )
        writer.z(ts + 1.0, 1)  # 磁盘侧照常空闲推进
        writer.write()
        now = ts + 4.0
        grid = build_grid("5m", now, _SI)
        days = daycache.read_window(key, grid.t0 - _SI - _V4_SEAM_LOOKBACK_S, grid.t1)
        res, _blocks, tail_slots = cache.series_result(key, days, grid, v4_live_tail_slots(tail), _SI)
        try:
            _assert_bitwise(res, _cold_reference(days, grid, tail_slots, _SI), f"tail-close tick={i}")
        except AssertionError as e:
            bad += 1
            print(f"[tail-close anomaly] {e}")
        st = cache._entries.get((key, "5m")).st
        assert st.N == len(st.ts) + st.base  # 回滚后样本驻留不含尾折槽
        assert len(tail_slots) == 1 and tail_slots[0].ts == ts + 2.5  # 活尾槽在磁盘链尾之后
        if bad > 2:
            break
    assert bad == 0


def test_dips_eps_band_regression_whitebox():
    """ts 非降破例旁路(评审 #5 防御面, 白盒直驱)—— eps 带内回退槽入列 -> dips 登记 ->
    respond 组末 t = 组内 ts 最晚者(旁路全组取 max, 冷算 e[5] 判据逐位同); compact
    裁剪窗沿前破例位(响应组恒在窗沿之后, 破例位永不进组)"""
    st = _GroupFoldState()
    slots = (
        V4Slot(ts=100.0, dt_s=2.0, obs=(10, 10, 100, 100), is_zero=False),
        V4Slot(ts=100.0 - _V4_VACUUM_EPS_S / 2, dt_s=2.0, obs=(20, 20, 200, 200), is_zero=False),
        V4Slot(ts=102.0, dt_s=2.0, obs=(30, 30, 300, 300), is_zero=False),
    )
    st.guard_batch(slots)  # eps 带内回退不 raise
    st.feed(slots, 0.0, 200.0, 0.0)
    assert st.dips == [1]  # 破例位登记(样本 1 回退)
    res = st.respond(0.0, 200.0, 2.0)
    # 组 0 末 t = 组内 ts 最晚者 100.0(非末位样本 99.9999995); 组点 t 非单调 ->
    # 响应按 t 排序(冷算 items.sort 同判)—— 与冷算逐位等价
    _assert_bitwise(res, assemble_group_points(slots, 0.0, 200.0, 2.0), "dips-bypass")
    assert {p["t"] for p in res.points} == {100.0, 99.9999995, 102.0}
    # k=2 组(窗内预期样本 (1902-900)/2 = 501 > 500 -> k_init = 2): 破例位落组内 ->
    # 旁路全组取 max 实际触发 —— 窗内末组 = 样本对 [1000.0, 1000.0 - eps/2](绝对序号
    # 53, 54, 破例位 54 = 组末位), 旁路缺席时 ts[ib-1] 即回退值, 组末 t 应为组内 ts
    # 最晚者 1000.0(非回退样本; 冷算 e[5] 判据同, 对账见 _assert_bitwise)
    slots2 = tuple(
        V4Slot(
            ts=1000.0 - _V4_VACUUM_EPS_S / 2 if j == 51 else 900.0 + 2.0 * j,
            dt_s=2.0,
            obs=(10 * (j + 1), 10 * (j + 1), 100 * (j + 1), 100 * (j + 1)),
            is_zero=False,
        ) for j in range(52)
    )
    st.guard_batch(slots2)  # eps 带内回退不 raise(链锚 = 前批末槽 102.0)
    st.feed(slots2, 900.0, 1902.0, group_null_lo(900.0, 2.0))
    res2 = st.respond(900.0, 1902.0, 2.0)
    _assert_bitwise(res2, assemble_group_points(slots + slots2, 900.0, 1902.0, 2.0), "dips-bypass-k2")
    assert res2.stride == 2  # k=2 实际触发(窗内预期 501 > 500)
    assert [p["t"] for p in res2.points].count(1000.0) == 1  # 破例组组末 t = 组内 ts max
    assert all(p["t"] != 1000.0 - _V4_VACUUM_EPS_S / 2 for p in res2.points)  # 非回退样本值
    # compact 裁窗沿前破例位(生产 compact(i_lo) 同形, i_lo = 窗首样本序号 3): pos 1 已裁,
    # 窗内破例位(pos 54)存活(后继响应旁路仍需)
    st.compact(3)
    assert st.dips == [54]
