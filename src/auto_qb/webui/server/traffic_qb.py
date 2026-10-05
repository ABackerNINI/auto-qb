"""qB 口径流量图三 GET 端点的读侧共享装配(plan 26-10-03-0946 方案C P4, §08; v3 翻转
plan 26-10-04-1957 S3b, §05.2-§05.4)

三端点(global / torrent / group)的公共口径收在这里, 各域 router 在 build_router 时自建
一个实例(一域恰一端点, last-good 快照按 window 分键互不串扰):

- 响应形状三域一致: {"points": [...], "totals": [...], "meta": {...}}(§08); points/totals
  为窗口栅格上「桶值 | null」定长数组, meta = window/interval_s/source/stale。
  interval_s = 桶宽: raw 段窗 = 采样间隔, 3d/7d/30d = 3600, 6mo/1y = 86400(本地日界),
  all = 标称月长(真实月长按行间隔, 点位真值在 points[].t, 前端按真值落点)。
- 未启用(qb_traffic 缺省 None / enabled=false / data_dir 为空防御)或无数据 -> 空态
  (points/totals 空数组 + meta), 与 /api/traffic/history 未启用空数组分支同构。
- window 查询参数仅认 WINDOW_NAMES(13 档, D4), 其余 400(客户端错误不 500)。
- 读盘 v4(plan 26-10-04-1957 R2 换代立, 只读 qb-traffic-v4/ 新目录): raw 段窗(1m-24h)经
  V4DayCache.read_window 按窗口日期集合只读涉及天文件(24h 窗至多 2 个), 块序列 ->
  traffic_grid.v4_series_points 桶点 -> v4_grid_obs 栅格展开; agg 段窗(3d/7d/30d/6mo/1y/
  all)经 V4DayCache.read_agg 单文件读取(mtime/size 键控缓存), 行按 kind 直映栅格桶
  (3d+ 组图由 M×31 -> M×1 次文件读取)。
- 活尾合流(S6 验收追加, 2026-10-05): raw 段窗在磁盘块之外合流采样模块活尾快照
  (未落盘 buffer 记录 + 开放游程, handler 每轮整体替换引用)—— 图面尾部随采样节拍实时,
  不等 flush_interval 落盘; 槽 ts 镜像保证下按 ts 精确去重, 快照与 flush 竞态不重不漏。
  agg 段窗(3d+)仍纯磁盘(未完结小时/日/月桶缺口的合流留待后续切片)。
- 读取失败(Windows 竞态等瞬态 OSError)不以空态冒充「无数据」: 回退上一份成功响应并标
  meta.stale=true(§08「最坏返回上一秒快照 + stale」), 无历史快照才回本次现算结果。
  last-good 每端点每 window 仅存一份、每次成功现算后覆盖 —— 这是竞态兜底快照, 不是聚合
  缓存(组聚合仍每请求现算, §04.3)。
- 组端点(§04.1 -> §05.4 v3): key 收当前指纹 base64url(同 /api/groups/{key} 通道, 畸形
  400), 成员集 = 查询时刻 store.groups[指纹键]; 聚合口径在 core.traffic_grid 纯函数层
  (API 层现算不做聚合缓存); 「借 global 判 null」退役 —— 桶 null 由成员自身观测面裁决
  (任一成员 r/z 观测即程序存活真值); 指纹解析不到成员 / 组从未产过流量(全部成员无块无
  agg 行, v4_earliest_row_ts 全 None)-> 空态。
"""
import time

from fastapi import HTTPException

from ...core import traffic_grid as tg
from ...core.traffic_store import (
    GLOBAL_KEY,
    TORRENT_KEY_PREFIX,
    V4DayCache,
    v4_live_tail_slots,
    v4_series_dir,
)
from .common import group_key_param

#: window 查询参数合法值(§08 + plan 26-10-04-1957 §05.3/D4: 1m-24h 与 qB 速度图窗口对齐
#: + 3d/7d/30d 消费 agg hour 行 + 6mo/1y 消费 day 行 + all 消费 month 行, 共 13 档;
#: 90d 拍板延后不上); 其余一律 400
WINDOW_NAMES = ("1m", "5m", "30m", "3h", "6h", "12h", "24h", "3d", "7d", "30d", "6mo", "1y", "all")


def parse_window(window: str) -> str:
    """window 查询参数校验: 仅 WINDOW_NAMES, 其余 400(非法值 4xx, §08 验收判据)"""
    if window not in WINDOW_NAMES:
        raise HTTPException(status_code=400, detail="window 须为 " + "|".join(WINDOW_NAMES))
    return window


class QbTrafficChartApi:
    """单域流量图端点的读侧装配(每域 router 一实例; 无锁 —— 只读 + 原子替换读语义)"""
    def __init__(self, manager) -> None:
        self._manager = manager
        # 构造期预建(路径纯计算): 惰性建无锁在 Web 线程池并发首访同一端点时会双构造、其一
        # 被引用覆盖丢弃(仅损失一份解析缓存, 但契约依赖实现时序; issue 26-10-06-0028
        # chore-lazy-init-double-construct)。data_dir 为 R 级重启闸字段(热重载拒绝项), 改动
        # 即整体重启重建 router —— 预建无快照失效面。
        # data_dir 缺字段(测试替身 config)时落空串 = 未启用防御语义, 用法仍由 _feature_on 兜底
        self._v4cache = V4DayCache(getattr(manager.config, "data_dir", ""))
        self._last_good: dict = {}  # window 名 -> 最近一次成功现算的响应(竞态兜底, 非聚合缓存)

    # ---------- 基础件 ----------

    @property
    def v4cache(self) -> V4DayCache:
        """v4 读侧缓存(天文件按天解析缓存 + agg.dat 解析缓存; 构造期预建, 只读引用)"""
        return self._v4cache

    def _conf(self):
        return self._manager.config.qb_traffic

    def _feature_on(self) -> bool:
        """功能启用判定: qb_traffic 缺省(None)/enabled=false/data_dir 为空(防御, 对齐采样器)都算未启用"""
        conf = self._conf()
        return conf is not None and bool(conf.enabled) and bool(self._manager.config.data_dir)

    def _grid(self, window: str) -> tg.WindowGrid:
        """当前时刻的时间栅格; raw 段窗(1m-24h)桶宽 = 采样间隔(未启用/缺省兜底 30s),
        hour 段窗(3d/7d/30d)恒 3600s, day 段窗(6mo/1y)= 本地日界 86400s;
        month 段窗(all)栅格由数据面定, 此处只出空 buckets 兜底形(空态 meta 用)"""
        conf = self._conf()
        sample = conf.sample_interval if conf is not None else tg.DEFAULT_SAMPLE_INTERVAL_S
        if tg.WINDOW_SPECS[window][1] == "month":
            return tg.build_month_grid((), time.time())
        return tg.build_grid(window, time.time(), sample)

    def _meta(self, grid: tg.WindowGrid, stale: bool) -> dict:
        return {"window": grid.name, "interval_s": grid.interval, "source": "qb", "stale": stale}

    def _live_tail(self, key: str):
        """采样模块活尾快照(S6 验收追加): 未落盘 buffer 记录 + 开放游程的当轮冻结副本,
        raw 段窗合流使图面尾部随采样节拍实时(不等 flush_interval)。模块宿主缺位(manager
        替身 / 功能未启用 / 模块未注册)返回 None —— 活尾纯增益, 缺席即退回纯磁盘读路径。"""
        host = getattr(self._manager, "host", None)
        get = getattr(host, "get", None) if host is not None else None
        mod = get("qb_traffic") if callable(get) else None
        if mod is None:
            return None
        return getattr(mod, "live_tail", {}).get(key)

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

    # ---------- 三端点(§08; v4 读侧 §05.2-§05.4) ----------

    def payload_global(self, window: str) -> dict:
        """GET /api/traffic/qb/global: 全局系列(qb-traffic-v4/global/ 天文件 + agg.dat)"""
        parse_window(window)
        if not self._feature_on():
            return self._empty(window)
        return self._payload_series(GLOBAL_KEY, window)

    def payload_torrent(self, hash_text: str, window: str) -> dict:
        """GET /api/traffic/qb/torrent/{hash}: 单种系列(torrents/<hash>/; 非活跃期无行 = 断线)"""
        parse_window(window)
        try:
            v4_series_dir(self._manager.config.data_dir, TORRENT_KEY_PREFIX + hash_text)
        except ValueError:
            raise HTTPException(status_code=400, detail="种子哈希非法") from None
        if not self._feature_on():
            return self._empty(window)
        return self._payload_series(TORRENT_KEY_PREFIX + hash_text, window)

    def payload_group(self, key_text: str, window: str) -> dict:
        """GET /api/traffic/qb/group/{key}: 组系列读侧现算(§04.1; 组不落盘, Σ 成员观测面)

        key 与成员集解析同 /api/groups/{key} 通道(decode -> store.groups 查表); 聚合口径
        (成员求和 / 逐成员差分 / 桶 null 由成员观测面裁决)全部在 core.traffic_grid 纯函数层;
        不再读全局系列(「借 global 判 null」退役, §05.1/§05.4)。
        """
        parse_window(window)
        key = group_key_param(key_text)  # 畸形 key -> 400(同 /api/groups/{key} 通道, 不 500)
        if not self._feature_on():
            return self._empty(window)
        members = self._manager.store.groups.get(key)
        if not members:
            return self._empty(window)  # 指纹解析不到成员(组不存在/已无成员)-> 空态(§08)
        seg = tg.WINDOW_SPECS[window][1]
        degraded = False
        if seg == "raw":
            grid = self._grid(window)
            member_obs = []
            member_blocks = []
            member_has_tail = []
            for h in members:
                tail_slots = ()
                try:
                    days = self.v4cache.read_window(TORRENT_KEY_PREFIX + h, grid.t0, grid.t1)
                    blocks = tuple(blk for _, parsed in days if parsed for blk in parsed.blocks)
                    tail = self._live_tail(TORRENT_KEY_PREFIX + h)
                    tail_slots = v4_live_tail_slots(tail) if tail is not None else ()
                    member_obs.append(
                        tg.v4_grid_obs(tg.v4_series_points(blocks, grid.t0, grid.t1, tail_slots=tail_slots), grid)
                    )
                except OSError:
                    degraded = True  # 读取竞态: 该成员按空观测面计, degraded 走 last-good 兜底
                    blocks = ()
                    tail_slots = ()
                    member_obs.append({})
                member_blocks.append(blocks)
                member_has_tail.append(bool(tail_slots))
            if all(
                tg.v4_earliest_row_ts(blocks, None) is None and not has_tail
                for blocks, has_tail in zip(member_blocks, member_has_tail)
            ):
                # 组从未产过流量(窗内无任何成员块且无成员活尾)-> 空态(§08); 降级时如实标 stale
                return {"points": [], "totals": [], "meta": self._meta(grid, stale=degraded)}
        else:
            aggs = []
            for h in members:
                try:
                    aggs.append(self.v4cache.read_agg(TORRENT_KEY_PREFIX + h))
                except OSError:
                    degraded = True
                    aggs.append(None)

            def _rows(a):
                if a is None:
                    return ()
                return a.hours if seg == "hour" else a.days if seg == "day" else a.months

            if all(a is None or not (a.hours or a.days or a.months) for a in aggs):
                # 组从未产过流量(成员无任何 agg 行)-> 空态(§08; v2 not p.zruns 判据的 v3 平移)
                return {"points": [], "totals": [], "meta": self._meta(self._grid(window), stale=degraded)}
            if seg == "month":
                # all 视图栅格由成员月行数据面的并集定(首末自然月逐月铺格, 缺失月 = null)
                epochs = [r.epoch for a in aggs if a is not None for r in a.months]
                grid = tg.build_month_grid(epochs, time.time()) if epochs else self._grid(window)
            else:
                grid = self._grid(window)
            member_obs = [tg.v4_agg_obs(_rows(a), grid) for a in aggs]
        mask = tg.group_null_mask(member_obs, grid)
        points = tg.group_rate_points(member_obs, grid, mask)
        totals = tg.group_totals_points(member_obs, grid, mask)
        return self._respond(grid, points, totals, degraded=degraded)

    # ---------- 单系列装配(raw / agg 两段合流, §05.3) ----------

    def _payload_series(self, key: str, window: str) -> dict:
        """global/torrent 共用单系列装配: raw 段窗 = 天文件桶点 -> 栅格展开; agg 段窗 =
        agg 行直映栅格(all 的栅格由月行数据面定)。OSError(读取竞态)-> degraded,
        回退 last-good / 空态标 stale(§08), 不以空态冒充无数据。"""
        seg = tg.WINDOW_SPECS[window][1]
        if seg == "raw":
            grid = self._grid(window)
            try:
                days = self.v4cache.read_window(key, grid.t0, grid.t1)
                blocks = tuple(blk for _, parsed in days if parsed for blk in parsed.blocks)
                tail = self._live_tail(key)
                tail_slots = v4_live_tail_slots(tail) if tail is not None else ()
                obs = tg.v4_grid_obs(tg.v4_series_points(blocks, grid.t0, grid.t1, tail_slots=tail_slots), grid)
                degraded = False
            except OSError:
                obs, degraded = {}, True
            return self._respond(grid, tg.rate_points(obs, grid), tg.series_totals_points(obs, grid), degraded=degraded)
        grid = None if seg == "month" else self._grid(window)
        try:
            agg = self.v4cache.read_agg(key)
            rows = agg.hours if seg == "hour" else agg.days if seg == "day" else agg.months
            if seg == "month":
                grid = tg.build_month_grid((r.epoch for r in rows), time.time()) if rows else self._grid(window)
            obs = tg.v4_agg_obs(rows, grid)
            degraded = False
        except OSError:
            obs, degraded = {}, True
            if grid is None:
                grid = self._grid(window)
        return self._respond(grid, tg.rate_points(obs, grid), tg.series_totals_points(obs, grid), degraded=degraded)
