"""test_traffic_grid_bucket_cache 测试计划(26-11-18-0037 T1c-2 退役转世文件): 26-11-15-1104
桶值单调缓存(V4SeriesBucketCache, F4-2/3)已随样本分组契约退役删除 —— 本文件现为共用基建
的家, 桶缓存断言面由 V4SeriesGroupCache 电池(test_traffic_group_cache, 主阵逐位对账/
失效面/白盒不变量)与样本分组装配电池(test_traffic_group_assembly)承接:
- _SeriesWriter: 仿真采样器的天文件只追加写 —— test_traffic_group_cache 与
  test_traffic_qb_bucket_cache_perf(A4 基准)复用, 保留原样;
- test_block_slots_from_full_equivalence: v4_block_slots_from 与 v4_block_slots 的双形态
  等价守阵已迁至 test_traffic_store_slots(槽位数学守阵归位 slots 电池, 单点不双钉)。
"""
import os

from auto_qb.core.traffic_store import (
    HEADER_LINE_V4,
    V4NullRun,
    V4Sample,
    V4ZeroRun,
    format_v4_b_row,
    format_v4_n_row,
    format_v4_r_row,
    format_v4_z_row,
    v4_day_file_path,
    v4_epoch_date_str,
)

_SI = 2.0  # 仿真采样间隔缺省值(_SeriesWriter interval_s 缺省; A4 基准显式传 1.5)

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
