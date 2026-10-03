"""qB 口径流量图三 GET 端点的读侧共享装配(plan 26-10-03-0946 方案C P4, §08)

三端点(global / torrent / group)的公共口径收在这里, 各域 router 在 build_router 时自建
一个实例(一域恰一端点, last-good 快照按 window 分键互不串扰):

- 响应形状三域一致: {"points": [...], "totals": [...], "meta": {...}}(§08); points/totals
  为「桶值 | null」定长数组(§05.1 栅格离散), meta = window/interval_s/source/stale。
- 未启用(qb_traffic 缺省 None / enabled=false / data_dir 为空防御)或无数据 -> 空态
  (points/totals 空数组 + meta), 与 /api/traffic/history 未启用空数组分支同构。
- window 查询参数仅认 WINDOW_NAMES(1m/5m/30m/3h/6h/12h/24h/3d/7d/30d), 其余 400(客户端错误不 500)。
- 读盘走 TrafficDatStore.read_series_checked(快读即关 + OSError 按空系列对待); 读取失败
  (Windows rewrite 竞态等瞬态, 概率极低)不以空态冒充「无数据」: 回退上一份成功响应并标
  meta.stale=true(§08「最坏返回上一秒快照 + stale」), 无历史快照才回本次现算结果。
  last-good 每端点每 window 仅存一份、每次成功现算后覆盖 —— 这是竞态兜底快照, 不是聚合
  缓存(组聚合仍每请求现算, §04.3)。
- 组端点(§04.1): key 收当前指纹 base64url(同 /api/groups/{key} 通道, 畸形 400), 成员集
  = 查询时刻 store.groups[指纹键](与分组视图/弹层同源同刻); 聚合口径在 core.traffic_grid
  纯函数层(API 层现算不做聚合缓存); 指纹解析不到成员 / 成员从未产过流量(全部成员文件
  缺失或零行)-> 空态。
"""
import time
from typing import Optional

from fastapi import HTTPException

from ...core import traffic_grid as tg
from ...core.traffic_store import GLOBAL_KEY, TORRENT_KEY_PREFIX, TrafficDatStore
from .common import group_key_param

#: window 查询参数合法值(§08; 1m-24h 与 qB 速度图窗口对齐 + 3d/7d 外延, 3d/7d/30d 消费
#: hour 段); 其余一律 400
WINDOW_NAMES = ("1m", "5m", "30m", "3h", "6h", "12h", "24h", "3d", "7d", "30d")


def parse_window(window: str) -> str:
    """window 查询参数校验: 仅 WINDOW_NAMES, 其余 400(非法值 4xx, §08 验收判据)"""
    if window not in WINDOW_NAMES:
        raise HTTPException(status_code=400, detail="window 须为 " + "|".join(WINDOW_NAMES))
    return window


class QbTrafficChartApi:
    """单域流量图端点的读侧装配(每域 router 一实例; 无锁 —— 只读 + 原子替换读语义)"""
    def __init__(self, manager) -> None:
        self._manager = manager
        self._store: Optional[TrafficDatStore] = None  # 惰性构造(路径纯计算; data_dir 为 R 级热重载字段, 进程内不变)
        self._last_good: dict = {}  # window 名 -> 最近一次成功现算的响应(竞态兜底, 非聚合缓存)

    # ---------- 基础件 ----------

    @property
    def store(self) -> TrafficDatStore:
        if self._store is None:
            self._store = TrafficDatStore(self._manager.config.data_dir)
        return self._store

    def _conf(self):
        return self._manager.config.qb_traffic

    def _feature_on(self) -> bool:
        """功能启用判定: qb_traffic 缺省(None)/enabled=false/data_dir 为空(防御, 对齐采样器)都算未启用"""
        conf = self._conf()
        return conf is not None and bool(conf.enabled) and bool(self._manager.config.data_dir)

    def _grid(self, window: str) -> tg.WindowGrid:
        """当前时刻的时间栅格; raw 段窗口(1m-24h)桶宽 = 采样间隔(未启用/缺省兜底 30s),
        hour 段窗口(3d/7d/30d)恒 3600s"""
        conf = self._conf()
        sample = conf.sample_interval if conf is not None else tg.DEFAULT_SAMPLE_INTERVAL_S
        return tg.build_grid(window, time.time(), sample)

    def _meta(self, grid: tg.WindowGrid, stale: bool) -> dict:
        return {"window": grid.name, "interval_s": grid.interval, "source": "qb", "stale": stale}

    def _empty(self, window: str) -> dict:
        """空态(§08): 未启用/无数据 —— points/totals 空数组 + meta(未启用空态先例:
        /api/traffic/history 的 state=disabled + history=[])"""
        return {"points": [], "totals": [], "meta": self._meta(self._grid(window), stale=False)}

    def _respond(self, grid: tg.WindowGrid, points: list, totals: list, degraded: bool) -> dict:
        """装配响应 + last-good 兜底(§08): 读取竞态降级时回上一份成功快照标 stale=true

        - degraded 且有 last-good -> 回 last-good(数据最多旧一个请求周期, 前端按 stale
          提示), 不覆盖缓存;
        - degraded 且无 last-good -> 回本次现算(可能残缺/空), stale=true;
        - 全桶 null = 窗口内无任何观测 -> 空态(无数据, §08);
        - 仅成功响应入 last-good(降级响应绝不覆盖上一份好快照)。
        """
        if degraded:
            good = self._last_good.get(grid.name)
            if good is not None:
                return {
                    "points": good["points"],
                    "totals": good["totals"],
                    "meta": {
                        **good["meta"], "stale": True
                    },
                }
        if not any(p is not None for p in points):
            payload = {"points": [], "totals": [], "meta": self._meta(grid, stale=degraded)}
        else:
            payload = {"points": points, "totals": totals, "meta": self._meta(grid, stale=degraded)}
        if not degraded:
            self._last_good[grid.name] = payload
        return payload

    # ---------- 三端点(§08) ----------

    def payload_global(self, window: str) -> dict:
        """GET /api/traffic/qb/global: 全局系列(global.dat, 恒采含 null 点行 —— 停机/断连洞的真值源)"""
        parse_window(window)
        if not self._feature_on():
            return self._empty(window)
        grid = self._grid(window)
        parsed, read_ok = self.store.read_series_checked(GLOBAL_KEY)
        obs = tg.series_bucket_obs(parsed, grid)
        return self._respond(grid, tg.rate_points(obs, grid), tg.series_totals_points(obs, grid), degraded=not read_ok)

    def payload_torrent(self, hash_text: str, window: str) -> dict:
        """GET /api/traffic/qb/torrent/{hash}: 单种系列(torrents/<hash>.dat; 非活跃期无行 = 断线)"""
        parse_window(window)
        key = TORRENT_KEY_PREFIX + hash_text
        try:
            self.store.series_path(key)  # 非法哈希(路径不安全字符)在存储层 fail-fast -> 400
        except ValueError:
            raise HTTPException(status_code=400, detail="种子哈希非法") from None
        if not self._feature_on():
            return self._empty(window)
        grid = self._grid(window)
        parsed, read_ok = self.store.read_series_checked(key)
        obs = tg.series_bucket_obs(parsed, grid)
        return self._respond(grid, tg.rate_points(obs, grid), tg.series_totals_points(obs, grid), degraded=not read_ok)

    def payload_group(self, key_text: str, window: str) -> dict:
        """GET /api/traffic/qb/group/{key}: 组系列读侧现算(§04.1; 组不落盘, Σ 成员单种 dat)

        key 与成员集解析同 /api/groups/{key} 通道(decode -> store.groups 查表); 聚合口径
        (成员求和 / 逐成员差分 / 借全局系列判 null)全部在 core.traffic_grid 纯函数层。
        """
        parse_window(window)
        key = group_key_param(key_text)  # 畸形 key -> 400(同 /api/groups/{key} 通道, 不 500)
        if not self._feature_on():
            return self._empty(window)
        members = self._manager.store.groups.get(key)
        if not members:
            return self._empty(window)  # 指纹解析不到成员(组不存在/已无成员)-> 空态(§08)
        grid = self._grid(window)
        global_parsed, global_ok = self.store.read_series_checked(GLOBAL_KEY)
        member_series = [self.store.read_series_checked(TORRENT_KEY_PREFIX + h) for h in members]
        degraded = not global_ok or any(not ok for _, ok in member_series)
        member_parsed = [p for p, _ in member_series]
        if all(not p.raw and not p.hours for p in member_parsed):
            # 组从未有成员产过流量(成员文件全缺/零行)-> 空态(§08); 降级时如实标 stale
            return {"points": [], "totals": [], "meta": self._meta(grid, stale=degraded)}
        earliest = min(ts for ts in (tg.earliest_row_ts(p) for p in member_parsed) if ts is not None)
        member_obs = [tg.series_bucket_obs(p, grid) for p in member_parsed]
        mask = tg.group_null_mask(tg.series_bucket_obs(global_parsed, grid), grid, earliest)
        points = tg.group_rate_points(member_obs, grid, mask)
        totals = tg.group_totals_points(member_obs, grid, mask)
        return self._respond(grid, points, totals, degraded=degraded)
