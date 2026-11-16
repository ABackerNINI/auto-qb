"""test_traffic_grid_bucket_cache 测试计划: 桶值单调缓存(F4-2/3, 计划 26-11-15-1104 S2-2)
—— 封口桶不可变(T2/T3 定影定义)为正确性根基, 折叠态机(_V4SeriesFold)与游标式槽展开
(v4_block_slots_from)为增量面, 本文件钉「缓存命中与全量现算逐位等价」与失效面。

## 测试计划(每个测试函数一条)
- test_block_slots_from_full_equivalence: v4_block_slots_from 与 v4_block_slots 的双形态
  等价 —— 随机混排块(r/z/n/显式漂移 dt/块首游程)全量展开逐槽相等; 游标分段的链式续展
  (t1 逐次右移)拼接 == 全量展开; 部分游标(游程中段截停)续展 == 全量。唯一 dt 链实现的
  两个入口不得漂移。
- test_cache_polling_bitwise_equivalent: 主阵 —— 仿真采样流(稳态变流/台阶/长 z 游程
  (开放游程跨多桶)/游程闭合摊配/计数器重置/停机真空/n 游程断连/有界空桶回填/跨本地
  午夜多天/活尾 holding 槽/记录 ts 落窗尾界外重展)逐拍轮询, 每拍缓存路径(obs + points
  段 + totals 段)与 v4_series_points 全量现算逐位等价; 白盒不变量: 封口边界单调不减、
  封口值跨拍恒等(定影后不改写)、cell_keys 插入序 == 升序。
- test_sealed_floor_open_run_not_sealed: 封口判定与定影定义单点对齐守阵 —— 开放等值
  游程覆盖的桶不入封口值表(游程闭合摊配前其值可改写); 台阶到达(游程闭合)后游程桶
  连同此前全部桶入封口值表且后续追加不再变化; 进行中桶/台阶接收桶恒在界上。
- test_cache_config_change_invalidates: 配置面失效 —— 桶宽 interval / 采样间隔变更 ->
  条目丢弃冷重建, 结果与全量现算等价(桶键格整体改变不得串值)。
- test_cache_day_shrink_and_delete_invalidates: 天文件裁剪重写(size 缩)与天文件删除 ->
  游标校验不过整条目冷重建, 结果与全量现算等价(不得以陈旧封口值应答)。
- test_cache_lru_eviction_and_multi_key: LRU 上限逐出(超限最久未用先逐出)后重查冷算
  仍等价; 多系列键(组图 M 成员键面)同实例互不串扰; 同输入重算恒等(幂等)。

线程/时钟纪律: 纯函数层 + V4DayCache 真文件(tmp_path, test.* 已内置 TMPDIR 不手工加
前缀); 轮询时刻为仿真推进值(不触系统时钟); 计时用 time.perf_counter(实测数字非断言
精确值, 阈值断言放宽防环境噪声); 代码/断言零 emoji 零图形符号。
"""
import os
import random

import pytest

from auto_qb.core.traffic_grid import (
    V4SeriesBucketCache,
    build_grid,
    rate_points,
    series_totals_points,
    v4_grid_obs,
    v4_series_points,
)
from auto_qb.core.traffic_store import (
    HEADER_LINE_V4,
    V4Block,
    V4NullRun,
    V4Sample,
    V4Slot,
    V4ZeroRun,
    format_v4_b_row,
    format_v4_n_row,
    format_v4_r_row,
    format_v4_z_row,
    v4_block_slots,
    v4_block_slots_from,
    v4_day_file_path,
    v4_epoch_date_str,
    v4_day_epoch,
)
from auto_qb.core.traffic_store import V4DayCache

#: 仿真基点(2027-01-15, 与 traffic_grid_support.NOW 同源; 本地午夜对齐用 v4_day_epoch 派生)
_BASE = 1_800_000_000
_SI = 2.0  # 仿真采样间隔(秒)

# ---------- 仿真采样器(只追加天文件写侧) ----------


class _SeriesWriter:
    """模拟采样器的天文件只追加写(逐记录推进; 块在跨天/重开时重立基线):
    记录型 r/z/n + 显式 dt_ms 链, 与真实写侧同构度以覆盖读侧路径为准(块基线/z 游程
    摊配签名/真空组界), 不追求写侧内部状态机复刻。"""
    def __init__(self, data_dir: str, key: str, interval_s: float = _SI) -> None:
        self._data_dir = data_dir
        self.key = key
        self.interval_s = interval_s
        self.day = None
        self.lines = None
        self.blk = None  # (start, dl_base, up_base)
        self.cursor = None  # 上一记录链上终点
        self.dl = 0
        self.up = 0
        self.last_obs = None  # (dr, ur, dl, up) 末观测(r/z); None = 断连

    def _ensure_day(self, ts: float) -> None:
        d = v4_epoch_date_str(ts)
        if d != self.day:
            self.write()
            self.day = d
            self.lines = [HEADER_LINE_V4, f"key,{self.key}"]
            self.blk = None

    def _open_block(self, ts: float) -> None:
        self.blk = (int(ts), self.dl, self.up)
        self.lines.append(format_v4_b_row(int(ts), self.interval_s, self.dl, self.up))

    def r(self, ts: float, dr: int, ur: int) -> None:
        self._ensure_day(ts)
        if self.blk is None:
            self._open_block(ts)
        dt = None if self.cursor is None else int(round((ts - self.cursor) * 1000))
        span = 0 if self.cursor is None else max(0, ts - self.cursor)
        self.dl += int(round(dr * span))
        self.up += int(round(ur * span))
        rec = V4Sample(dr, ur, self.dl, self.up, dt)
        self.lines.append(format_v4_r_row(rec, self.blk[1], self.blk[2]))
        self.cursor = ts
        self.last_obs = (dr, ur, self.dl, self.up)

    def z(self, ts_end: float, n: int) -> None:
        self._ensure_day(ts_end)
        if self.blk is None:
            self._open_block(ts_end - n * self.interval_s)
        dt = None if self.cursor is None else int(round((ts_end - self.cursor) * 1000))
        rec = V4ZeroRun(n, self.dl, self.up, dt)
        self.lines.append(format_v4_z_row(rec, self.blk[1], self.blk[2]))
        self.cursor = ts_end
        self.last_obs = (0, 0, self.dl, self.up)

    def n(self, ts_end: float, n: int) -> None:
        self._ensure_day(ts_end)
        if self.blk is None:
            self._open_block(ts_end - n * self.interval_s)
        dt = None if self.cursor is None else int(round((ts_end - self.cursor) * 1000))
        self.lines.append(format_v4_n_row(V4NullRun(n, dt)))
        self.cursor = ts_end
        self.last_obs = None

    def reopen(self) -> None:
        """关块(计数器重置/重启形态): 下一记录按块首立基线开新块"""
        self.blk = None

    def write(self) -> None:
        if self.day is None:
            return
        path = v4_day_file_path(self._data_dir, self.key, self.day)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(self.lines) + "\n")


# ---------- 仿真轮询主阵 ----------


def _run_polling_simulation(tmp_path, window: str, polls: int, *, with_tail_every: int = 7):
    """仿真采样流 + 逐拍轮询: 每拍(写文件 -> 建栅格 -> 读天文件 -> 缓存路径 vs 全量现算)
    逐位对账, 并收集白盒不变量。返回 (违例列表, 封口快照序列)。"""
    data_dir = str(tmp_path)
    key = "global"
    writer = _SeriesWriter(data_dir, key)
    cache = V4DayCache(data_dir)
    bucket_cache = V4SeriesBucketCache()
    gb_cache = lambda grid: max(grid.interval, _SI) * 2.0  # noqa: E731 - 判据界单点公式

    # 起点钉在本地午夜前 90s: 仿真中段跨日(多天文件面)
    t = v4_day_epoch(_BASE) + 86_400 - 90.0
    v4 = cache
    anomalies = []
    sealed_snapshots = []
    floors = []
    prev_ent = None
    rng = random.Random(2026_11_15)

    for poll in range(polls):
        # ---- 采样面: 按阶段写记录(记录 ts 取半秒偏移, 恒落 t1 界上/外 -> 重展面常态) ----
        ts = t + 0.5
        phase = poll % 30
        if phase == 28:
            # 停机真空: 跳过 65s 后关块重写(组界缝 > 60s = 停机洞 -> null 标记 + 摊配回收)
            t += 65.0
            ts = t + 0.5
            writer.reopen()
            writer.r(ts, 60_000, 30_000)
        elif phase < 10:
            writer.r(ts, 40_000 + rng.randrange(0, 30_000), 10_000 + rng.randrange(0, 9_000))
        elif phase < 14:
            writer.r(ts, 90_000, 90_000)  # 台阶(恒值段后跳变)
        elif phase < 20:
            # 空闲: 2s 一枚 z 记录(开放游程跨多桶; 游程闭合摊配在 phase==20 触发)
            writer.z(ts, 1)
        elif phase == 20:
            writer.r(ts, 50_000, 50_000)  # 台阶出游程 -> 摊配回写游程桶(其后定影)
        elif phase < 24:
            writer.r(ts, 50_000, 50_000)
        elif phase < 27:
            writer.n(ts, 1)  # 断连(n 游程)
        elif phase == 27:
            writer.reopen()  # 计数器重置形态(新块新基线)
            writer.r(ts, 70_000, 20_000)
        else:
            writer.r(ts, 70_000, 20_000)
            if phase == 29:
                writer.reopen()  # 块边界高频切换(游标续块面)
        writer.write()
        t += (2.0 if poll % 5 else 3.0) + 0.25  # 轮询节拍含半秒相位

        # ---- 读面: 缓存路径 vs 全量现算 ----
        grid = build_grid(window, t, _SI)
        gb = gb_cache(grid)
        days = v4.read_window(key, grid.t0 - grid.interval, grid.t1)
        tail_slots = ()
        if poll % with_tail_every == 3 and writer.last_obs is not None:
            dr, ur, dl, up = writer.last_obs
            tail_slots = (V4Slot(ts=t + 0.4, dt_s=_SI, obs=(dr, ur, dl, up), is_zero=False, is_hold=True), )
        points = bucket_cache.series_points(key, days, grid, tail_slots, gb, _SI)
        blocks = tuple(blk for _, parsed in days if parsed for blk in parsed.blocks)
        ref_points = v4_series_points(blocks, grid, tail_slots=tail_slots, gap_bound_s=gb)

        got_obs = v4_grid_obs(points, grid)
        want_obs = v4_grid_obs(ref_points, grid)
        if got_obs != want_obs:
            anomalies.append(
                (
                    poll, "obs", [
                        (k, got_obs.get(k), want_obs.get(k)) for k in sorted(set(got_obs) | set(want_obs), key=str)
                    ][:8]
                )
            )
        if rate_points(got_obs, grid) != rate_points(want_obs, grid):
            anomalies.append((poll, "rate_points", None))
        if series_totals_points(got_obs, grid) != series_totals_points(want_obs, grid):
            anomalies.append((poll, "totals_points", None))
        # 点列本体不逐位比(缓存点列 = 封口段 + 开放段, 标记点保留是发射契约;
        # 栅格观测/两段数组已逐位对账, 点列只核对窗内非标记点集合)
        gp = [
            p for p in points
            if not (p.dl_rate is None and p.up_rate is None and p.dl_total is None and p.up_total is None)
        ]
        rp = [
            p for p in ref_points if grid.first <= p.t <= grid.last and
            not (p.dl_rate is None and p.up_rate is None and p.dl_total is None and p.up_total is None)
        ]
        if gp != rp:
            anomalies.append((poll, "points_in_window", [(p.t) for p in gp[:6]]))

        # ---- 白盒不变量 ----
        ent = bucket_cache._entries.get((key, window))
        if ent is not None:
            if ent is not prev_ent:
                # 条目重建(读集前沿 c2 / 配置 c / 游标 b 失效): 封口值与封口边界随链重锚
                # 合法更替 —— 不变量只在单条目生命周期内钉(跨重建的比较基线重置)
                floors = []
                sealed_snapshots = []
            prev_ent = ent
            floors.append(ent.floor)
            if ent.floor is not None and floors[-2:-1] and floors[-2] is not None and ent.floor < floors[-2]:
                anomalies.append((poll, "floor_regressed", (floors[-2], ent.floor)))
            if ent.floor is not None:
                if any(k >= ent.floor for k in ent.sealed_keys):
                    anomalies.append((poll, "sealed_at_or_above_floor", None))
                if any(k < ent.floor for k in ent.fold.cell_keys):
                    anomalies.append((poll, "open_cell_below_floor", None))
            snap = dict(ent.sealed)
            for prev in sealed_snapshots[-3:]:
                for k, v in prev.items():
                    if k in snap and snap[k] != v:
                        anomalies.append((poll, "sealed_value_changed", (k, )))
            sealed_snapshots.append(snap)
            if ent.fold.cell_keys != sorted(ent.fold.cell_keys):
                anomalies.append((poll, "cell_keys_unsorted", None))
    writer.write()
    return anomalies, sealed_snapshots


@pytest.mark.parametrize("window", ["1m", "30m"])
def test_cache_polling_bitwise_equivalent(tmp_path, window):
    """主阵: 仿真采样流逐拍轮询, 缓存路径与全量现算逐位等价(obs/rate/totals/窗内点列)
    + 白盒不变量(封口边界单调/封口值恒定/累加器键序)。"""
    anomalies, _ = _run_polling_simulation(tmp_path, window, polls=120)
    assert not anomalies, anomalies[:5]


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


def test_sealed_floor_open_run_not_sealed(tmp_path, monkeypatch):
    """封口判定与定影定义单点对齐: 开放等值游程覆盖的桶不入封口值表(摊配回写面前);
    台阶到达(游程闭合)后游程桶及此前全部桶定影; 进行中桶/台阶接收桶恒在界上。"""
    data_dir = str(tmp_path)
    key = "global"
    writer = _SeriesWriter(data_dir, key)
    v4 = V4DayCache(data_dir)
    bucket_cache = V4SeriesBucketCache()
    t = v4_day_epoch(_BASE) + 3600.0

    # 活动段 -> 长空闲(z 游程开放, 覆盖多桶)
    for i in range(10):
        writer.r(t + 0.5 + i * _SI, 30_000, 30_000)
    t += 10 * _SI
    z_end = t + 60.0
    writer.z(z_end, 30)
    writer.write()

    def _poll(now):
        grid = build_grid("1m", now, _SI)
        days = v4.read_window(key, grid.t0 - grid.interval, grid.t1)
        gb = max(grid.interval, _SI) * 2.0
        return bucket_cache, grid, bucket_cache.series_points(key, days, grid, (), gb, _SI), days, gb

    bucket_cache, grid, points, days, gb = _poll(z_end + 1.0)
    ent = bucket_cache._entries[(key, "1m")]
    floor1 = ent.floor  # 快照(条目对象跨拍原位演进, 引用读到的恒是最新值)
    assert floor1 is not None
    # 台阶未到达: 开放游程覆盖桶(空闲段桶)不入封口值表(定影判定 = 不在开放游程覆盖内)
    run_bucket_keys = [k for k in ent.sealed_keys]
    grid_keys = set(grid.buckets)
    idle_keys = {b for b in grid.buckets if b >= t}
    assert idle_keys, "空闲段应覆盖栅格桶"
    assert not (idle_keys & set(ent.sealed_keys)), "开放游程覆盖的桶不得定影"

    # 台阶到达: 游程闭合, 摊配完成 -> 游程桶连同此前全部桶定影(后续追加不再变化)
    # (轮询时刻须晚过台阶槽 ts —— 窗尾界外的槽不消费, 下一拍重展重判, F3 窗尾语义)
    t2 = z_end + 3.0
    writer.r(t2 + 0.5, 80_000, 80_000)
    writer.write()
    bucket_cache2, grid2, points2, days2, gb2 = _poll(t2 + 2.5)
    ent2 = bucket_cache2._entries[(key, "1m")]
    assert ent2.floor is not None and ent2.floor > floor1
    idle_keys2 = {b for b in grid2.buckets if t <= b < t2 - _SI}
    assert idle_keys2 <= set(ent2.sealed_keys), "游程闭合后游程桶须定影"
    sealed_before = dict(ent2.sealed)
    # 闭合后继续追加样本: 封口值不再变化(定影桶值只依赖已落定样本)
    t3 = t2 + 6.0
    for i in range(3):
        writer.r(t3 + 0.5 + i * _SI, 80_000, 80_000)
    writer.write()
    bucket_cache3, grid3, points3, days3, gb3 = _poll(t3 + 2.5)
    ent3 = bucket_cache3._entries[(key, "1m")]
    for k, v in sealed_before.items():
        if k in ent3.sealed:
            assert ent3.sealed[k] == v, (k, "封口值被改写")
    # 等价性兜底: 三拍缓存路径与全量现算逐位等价
    for cache_i, grid_i, points_i, days_i, gb_i in (
        (bucket_cache, grid, points, days, gb),
        (bucket_cache2, grid2, points2, days2, gb2),
        (bucket_cache3, grid3, points3, days3, gb3),
    ):
        blocks = tuple(blk for _, parsed in days_i if parsed for blk in parsed.blocks)
        ref = v4_grid_obs(v4_series_points(blocks, grid_i, gap_bound_s=gb_i), grid_i)
        assert v4_grid_obs(points_i, grid_i) == ref


def test_cache_config_change_invalidates(tmp_path):
    """配置面失效: 桶宽/采样间隔变更 -> 条目冷重建, 与全量现算等价(桶键格整体改变)。"""
    data_dir = str(tmp_path)
    key = "global"
    writer = _SeriesWriter(data_dir, key)
    v4 = V4DayCache(data_dir)
    bucket_cache = V4SeriesBucketCache()
    t = v4_day_epoch(_BASE) + 3600.0
    for i in range(12):
        writer.r(t + 0.5 + i * _SI, 25_000 + i * 100, 11_000)
        t += _SI
    writer.write()

    def _read(grid, si):
        days = v4.read_window(key, grid.t0 - grid.interval, grid.t1)
        gb = max(grid.interval, si) * 2.0
        blocks = tuple(blk for _, parsed in days if parsed for blk in parsed.blocks)
        return days, v4_grid_obs(bucket_cache.series_points(key, days, grid, (), gb, si),
                                 grid), v4_grid_obs(v4_series_points(blocks, grid, gap_bound_s=gb), grid)

    g1 = build_grid("1m", t, _SI)
    _, got1, want1 = _read(g1, _SI)
    assert got1 == want1
    ent = bucket_cache._entries[(key, "1m")]
    assert ent.sealed  # 温态后封口表非空
    # 配置变更: 采样间隔 2 -> 4(桶宽格整体改变) -> 条目冷重建仍等价
    g2 = build_grid("1m", t, 4.0)
    _, got2, want2 = _read(g2, 4.0)
    assert got2 == want2
    ent2 = bucket_cache._entries[(key, "1m")]
    assert ent2.interval == g2.interval and ent2.sample_interval == 4.0
    # 回到原配置: 再冷重建仍等价(旧格条目已随指纹失效)
    g3 = build_grid("1m", t + 2.0, _SI)
    _, got3, want3 = _read(g3, _SI)
    assert got3 == want3


def test_cache_day_shrink_and_delete_invalidates(tmp_path):
    """天文件结构性变化失效面: 裁剪重写(size 缩)与文件删除 -> 游标校验不过整条目冷
    重建, 结果与全量现算等价(不得以陈旧封口值应答)。"""
    data_dir = str(tmp_path)
    key = "global"
    writer = _SeriesWriter(data_dir, key)
    v4 = V4DayCache(data_dir)
    bucket_cache = V4SeriesBucketCache()
    t = v4_day_epoch(_BASE) + 3600.0
    for i in range(10):
        writer.r(t + 0.5 + i * _SI, 30_000, 30_000)
        t += _SI
    writer.write()
    grid = build_grid("1m", t, _SI)
    days = v4.read_window(key, grid.t0 - grid.interval, grid.t1)
    gb = max(grid.interval, _SI) * 2.0
    blocks = tuple(blk for _, parsed in days if parsed for blk in parsed.blocks)
    got = v4_grid_obs(bucket_cache.series_points(key, days, grid, (), gb, _SI), grid)
    want = v4_grid_obs(v4_series_points(blocks, grid, gap_bound_s=gb), grid)
    assert got == want

    # 裁剪重写: 砍掉后半记录行(size 缩, 结构变化) -> 冷重建仍等价
    path = v4_day_file_path(data_dir, key, v4_epoch_date_str(t))
    with open(path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
    trimmed = lines[:6]
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(trimmed) + "\n")
    days2 = v4.read_window(key, grid.t0 - grid.interval, grid.t1)
    blocks2 = tuple(blk for _, parsed in days2 if parsed for blk in parsed.blocks)
    got2 = v4_grid_obs(bucket_cache.series_points(key, days2, grid, (), gb, _SI), grid)
    want2 = v4_grid_obs(v4_series_points(blocks2, grid, gap_bound_s=gb), grid)
    assert got2 == want2

    # 文件删除: 同款冷重建等价(读取面按缺失 = 无数据)
    os.remove(path)
    days3 = v4.read_window(key, grid.t0 - grid.interval, grid.t1)
    blocks3 = tuple(blk for _, parsed in days3 if parsed for blk in parsed.blocks)
    got3 = v4_grid_obs(bucket_cache.series_points(key, days3, grid, (), gb, _SI), grid)
    want3 = v4_grid_obs(v4_series_points(blocks3, grid, gap_bound_s=gb), grid)
    assert got3 == want3


def test_cache_lru_eviction_and_multi_key(tmp_path):
    """LRU 上限逐出 + 多系列键互不串扰 + 同输入幂等。"""
    data_dir = str(tmp_path)
    v4 = V4DayCache(data_dir)
    bucket_cache = V4SeriesBucketCache(max_entries=2)
    t = v4_day_epoch(_BASE) + 3600.0
    writers = {}
    for key in ("global", "torrent:aa", "torrent:bb"):
        w = _SeriesWriter(data_dir, key)
        tt = t
        for i in range(8):
            w.r(tt + 0.5 + i * _SI, 20_000 + abs(hash(key)) % 9000, 5_000)
            tt += _SI
        w.write()
        writers[key] = w

    def _read(key, now):
        grid = build_grid("1m", now, _SI)
        days = v4.read_window(key, grid.t0 - grid.interval, grid.t1)
        gb = max(grid.interval, _SI) * 2.0
        blocks = tuple(blk for _, parsed in days if parsed for blk in parsed.blocks)
        return (
            v4_grid_obs(bucket_cache.series_points(key, days, grid, (), gb, _SI), grid),
            v4_grid_obs(v4_series_points(blocks, grid, gap_bound_s=gb), grid),
            grid,
            days,
            gb,
        )

    got1, want1, g1, d1, gb1 = _read("global", t + 20)
    assert got1 == want1
    got2, want2, g2, d2, gb2 = _read("torrent:aa", t + 22)
    assert got2 == want2
    got3, want3, g3, d3, gb3 = _read("torrent:bb", t + 24)
    assert got3 == want3
    assert len(bucket_cache._entries) == 2  # 上限逐出生效(global 被逐出)
    # 被逐出条目重查: 冷算仍等价(逐出只损性能不损正确性)
    got4, want4, g4, d4, gb4 = _read("global", t + 26)
    assert got4 == want4
    # 同输入幂等: 同栅格同解析产物重算恒等
    again = v4_grid_obs(bucket_cache.series_points("global", d4, g4, (), gb4, _SI), g4)
    assert again == got4
