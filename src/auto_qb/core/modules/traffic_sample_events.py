"""traffic_sample_events 拆分件: 流量步进 SSE 事件源(plan 26-11-18-0037 阶段 2, §03 传输面表(2))

事件源 = 采样 handler 每轮(主循环线程)随活尾快照发布点派发 per-scope 增量: 本 tick 新样本
差分点, 载荷 = 小真值 {seq, scope, points:[{t, dl, up}]}(points 形态与新 GET 契约一致, §03 契约表(1));
全局 scope 每 tick 恰 1 帧(qB 在线且有字段时), 几十字节。seq 每 scope 单调递增(hub 侧)。

层级方向(依赖倒置): 本模块不 import webui —— 发布经 ctx.web 上注入的 hub 对象鸭型方法
(publish_traffic_batch / traffic_stream_active, 与活尾快照 set_traffic_view 同款发布形态:
core 调用注入对象的服务方法, 不反向依赖表现层)。hub 缺席(web 未启用/替身缺方法)= 事件源
静默关断, 零副作用(黄金法则 2: 保守默认)。

每 tick 派发语义(§03 传输面表(2) + 任务契约):
- 每系列每 tick 恰一个新观测(r / z / n 三型; 捕获点见 _ev_capture_obs 的调用面), r/z 产
  一个差分真值点, n(null/断连)不产数据点 —— 显式空值点由 GET 读侧 _slot_null_marks 承载,
  事件流如实静默(断连分支无新样本 -> 不推数据点), 恢复后 seq 续上(帧只在有真值点时派发)。
- 载荷 points 是 per-tick 样本粒度真值(§03 传输面表(2) 原文), 组闭合/尾组更新语义属前端按其
  stride 现算 —— 本模块不做 stride/k 分组(与读侧 V4SeriesGroupCache 的窗内分组正交)。
- 聚合(scope Σ)不在本模块: batch = {系列键: 点} 交 hub, global/torrent scope 直取,
  group scope 由 hub 按 _group_merge_points 口径现查 store.groups 合并(成员集 = 派发
  时刻成员, 与 GET 读侧同口径; R3: 载荷 = scope 聚合显示点, 绝不 per-torrent 逐成员推)。

差分点口径(与 GET 读侧一致性论证, 判据/摊配复用同一原语不造第二套):
- 差分链 = 相邻**观测**槽(r 与 z 都是观测; n 槽不推进链 —— 与读侧 fold 的 prev_slot
  语义逐字同构), 台阶判据复用 traffic_grid._bucket_delta(三层同判单点: 计数器回落 ->
  None, 绝不产负增量; 与采样器 _delta 同判据的读侧同名原语)。
- 覆盖分母 = min(距上一观测实测间隔, 生效采样间隔) —— 读侧 fold 的 cov = min(dur, 声称
  覆盖)同形(声称覆盖 ≈ si, 漂移由写侧 dt 链吸收; 断连后的首观测对跨含 null 段, 分母
  取声称间隔与 fold 同判)。
- 值 = round(delta * 1000 / 覆盖毫秒)(读侧组值公式同式); delta None(重置)-> broke(有观测
  缝或断连标记)则两向 None、无缝链则 0(fold 立点 c=0 的 broke 判据同形: unobs > 0 或
  marked -> 断链未知不造 0 值孤点); 观测缝超停机洞阈值(_V4_SEAM_NULL_S)-> 两向 None。
- 摊配判定/份额复用 traffic_grid._seam_spread_delta 原样提取件(调用形态与读侧折叠
  feed 逐字同构): z 游程被 r 收口时空闲期字节按覆盖份额摊回 z 槽 —— 事件流取收口样本的
  **自身份额**(与 GET 该样本现值一致), 摊回 z 槽的份额是对已派发点的追溯改写, 事件流
  不重发(增量语义), 由 GET 对账(D9: 30s 低频 + seq 断档重拉)校准。
  摊配项面经 **事件摊配链锚**(_ev_z_chain, 见 _ev_note_z_open)重建: 锚 = 折叠 run 的
  run.anchor_ts 等价物(等值接续 = 前观测槽 ts / 首槽台阶形态 = 首零样本 ts), 链跨封口段
  (00:00 硬切 / 保险闸 / 换型进 n 后回 z)持续 —— 收口摊配的 span/cov 因此覆盖**整段空闲
  链**(与读侧 fold 跨封口边界连续的 run 同分母), 游程项以单一合成项(覆盖 = 链末 - 锚)
  入参: _seam_spread_delta 的收口返回值只依赖项覆盖**合计**(acc = step_w x 合计 // cov_ms),
  逐项分布不影响返回值 —— 等节拍清洁链下与读侧逐位等价(电池钉住), 漂移链差异 ≤ si,
  对账面吸收。链锚年龄受读侧回看界约束(锚早于 ts - _V4_SEAM_LOOKBACK_S 即回退单段锚:
  >24h 空闲链读侧装配在消费下界 group_null_lo 内重立锚, 单段锚 = 同一重立形态的一致
  口径, 见「已知有界偏差」)。

已知有界偏差(全部落在 D9 对账机制的设计容差内, 不另造状态机):
- 摊回 z 槽的份额(含 z 首槽台阶形态的归账)是对已派发点的追溯改写, 事件流不重发;
- 空闲链 > 24h(_V4_SEAM_LOOKBACK_S): 事件收口走单段锚回退(摊配只覆盖末段), 读侧
  装配同样在消费下界内重立锚 —— 两源同一「窗内重立」形态, 收口值仍同口径;
- 空闲期主循环停顿(样本缝 > 停机洞阈值且无 n 观测)时事件出 None 而读侧活尾槽把游程
  跨缝均摊(分母被缝拉大不出洞)—— 两源值型分歧, GET 对账校准;
- 事件点 t = 实测样本 ts(§03 契约表(1)「真实样本 ts」), 读侧槽位 ts = dt 链游标: 漂移
  容差内相差 ≤ 250ms; 跨天封口的次段槽位均摊把游标锚留在前日链终(段内槽位与实测 ts
  偏差可达段跨度)—— 前端合并两源以 GET 对账校准。

线程模型(黄金法则 5): 捕获点(_ev_capture_obs)与派发点(_publish_traffic_events)全部在
采样调用链 = 主循环线程; _ev_tick_obs / _ev_prev_obs 仅该线程读写, 无锁; hub 的订阅表
由 hub 自身锁保护(Web 线程 subscribe/unsubscribe), 派发侧只经其方法调用。
"""
import logging
from typing import Optional

from ...core.traffic_grid import (
    _V4_SEAM_LOOKBACK_S,
    _V4_SEAM_NULL_S,
    _bucket_delta,
    _seam_spread_delta,
)
from .traffic_sample_common import GLOBAL_SERIES_KEY, _TORRENT_KEY_PREFIX

logger = logging.getLogger("auto_qb.core.modules.traffic_sample_mod")


def _ev_noop_share(_key, _d, _share) -> None:
    """_seam_spread_delta 的份额入桶回调: 摊回游程项的份额是对已派发点的追溯改写, 事件流
    不重发(增量语义, GET 对账校准)—— 只取返回值(收口样本自身份额), 份额落地为空操作。"""


def _ev_series_point(
    pre: Optional[tuple],
    kind: str,
    ts: float,
    dl_total: int,
    up_total: int,
    closed: Optional[tuple],
    si: float,
    z_chain: Optional[tuple],
) -> dict:
    """单系列单 tick 差分真值点(口径见模块 docstring「差分点口径」; 纯函数)

    pre = 该系列上一观测 (ts, dl_total, up_total)(None = 进程链首); kind = "r"|"z";
    closed = 本观测封口的游程快照 (kind, start, last_seen, samples) 或 None; si = 生效
    采样间隔(秒, >0); z_chain = 事件摊配链锚 (anchor_ts, dl_total, up_total) 或 None
    (r 观测消费后清除, 见 _ev_note_z_open)。返回 {t, dl, up}(值形态与 GET 契约一致:
    int | None)。
    """
    if pre is None:
        # 进程链首(重启后首个观测): 读侧 fold 首样本无差分对 -> c=0 非 broke -> 0 线
        return {"t": ts, "dl": 0, "up": 0}
    elapsed = ts - pre[0]
    cov_close_s = min(elapsed, si) if elapsed > 0 else 0.0
    cov_close_ms = int(round(cov_close_s * 1000))
    if elapsed - cov_close_s > _V4_SEAM_NULL_S:
        # 观测缝 > 停机洞阈值(断连跨缝): fold 立点 + broke -> 断链未知, 不造 0 值孤点
        return {"t": ts, "dl": None, "up": None}
    broke = marked = False
    span_ms = int(round(elapsed * 1000))
    cov_ms = cov_close_ms
    items: list = []
    if closed is not None and closed[0] == "z":
        # 等值游程(z)被本观测收口: 摊配项面经事件摊配链锚重建 —— 链锚 = 折叠 run 的
        # run.anchor_ts 等价物, 链跨封口段(00:00 硬切/保险闸/换型回 z)持续, span/cov
        # 因此覆盖整段空闲链(与读侧 fold 跨封口边界连续的 run 同分母); 链缺位、totals
        # 不匹配(重置/跳变断链)或锚龄超读侧回看界(_V4_SEAM_LOOKBACK_S, 与装配消费下界
        # group_null_lo 同源 —— 超界空闲链读侧在窗内重立锚)回退单段锚(首零样本前一个
        # 引导间隔 —— 写侧 dt 链定约「相邻游程之间的一次采样间隔并入后一游程 dt」)。
        # 游程项以单一合成项入参: 收口返回值只依赖项覆盖合计
        # (acc = step_w x 合计 // cov_ms), 逐项分布不影响。
        anchor = closed[1] - si
        # 链 totals 匹配基准 = 前观测(pre = 末 z 槽, 空闲链 totals 恒定)—— 收口 r 自身的
        # totals 恒大于链 totals(空闲期字节随收口样本入账), 不得作匹配基准
        if (
            z_chain is not None and z_chain[1] == pre[1] and z_chain[2] == pre[2] and
            closed[1] >= z_chain[0] >= ts - _V4_SEAM_LOOKBACK_S
        ):
            anchor = z_chain[0]
        span_ms = int(round((ts - anchor) * 1000))
        z_cov_ms = int(round((closed[2] - anchor) * 1000))
        items = [(0, z_cov_ms, True, 0.0)] if z_cov_ms > 0 else []
        cov_ms = z_cov_ms + cov_close_ms
    elif closed is not None and closed[0] == "n":
        # null 游程被本观测收口(短缝恢复): marked 断连标记面 —— 摊配基准按覆盖缩放
        # (span 含 null 段, 分母只取声称覆盖; fold marked + 全 z 游程项同判); 缝超阈值
        # 已在上方洞分支出 None。链在(z 游程未断链进 null, 折叠 run 跨 n 槽持续)时摊配
        # 项面含前置 z 槽(覆盖到末 z 槽), 与读侧 run 项面同构; 锚龄超回看界同 z 收口
        # 回退(与读侧窗内重立锚一致口径)。
        marked = True
        if (
            z_chain is not None and z_chain[1] == pre[1] and z_chain[2] == pre[2] and
            pre[0] >= z_chain[0] >= ts - _V4_SEAM_LOOKBACK_S
        ):
            anchor = z_chain[0]
            span_ms = int(round((ts - anchor) * 1000))
            z_cov_ms = int(round((pre[0] - anchor) * 1000))
            items = [(0, z_cov_ms, True, 0.0)] if z_cov_ms > 0 else []
            cov_ms = z_cov_ms + cov_close_ms
    # broke = fold 立点 c=0 形态的 broke 判据(unobs > 0 或 marked): 有未覆盖观测秒
    #(elapsed > 声称覆盖)或断连标记 —— 重置(delta None)时与读侧同判出 None
    broke = marked or elapsed > cov_close_s
    dl_v = _ev_direction_value(
        cur_total=dl_total,
        pre_total=pre[1],
        si=si,
        span_ms=span_ms,
        cov_ms=cov_ms,
        cov_close_ms=cov_close_ms,
        items=items,
        marked=marked,
        broke=broke,
    )
    up_v = _ev_direction_value(
        cur_total=up_total,
        pre_total=pre[2],
        si=si,
        span_ms=span_ms,
        cov_ms=cov_ms,
        cov_close_ms=cov_close_ms,
        items=items,
        marked=marked,
        broke=broke,
    )
    return {"t": ts, "dl": dl_v, "up": up_v}


def _ev_direction_value(
    cur_total: int,
    pre_total: int,
    si: float,
    span_ms: int,
    cov_ms: int,
    cov_close_ms: int,
    items: list,
    marked: bool,
    broke: bool,
) -> Optional[int]:
    """单方向差分值(纯函数): 台阶差分(_bucket_delta 三层同判)+ 摊配判定复用
    (_seam_spread_delta 与读侧折叠 feed 同调用形态: 普通观测/无项游程 = 不触发摊配
    原样全步, 等值游程收口/断连标记面按覆盖份额定影)。broke = fold 立点 c=0 形态的
    broke 判据(有观测缝 unobs > 0 或断连标记)—— 增量 None(重置)时对齐读侧值型。"""
    step = _bucket_delta(cur_total, pre_total)
    if step is None:
        # 计数器重置: fold 立点 c=0 -> broke 则断链未知(不造 0 值孤点), 无缝链 0 线
        return None if broke else 0
    delta = _seam_spread_delta(0, step, span_ms, cov_ms, cov_close_ms, si, marked, items, 0, _ev_noop_share)
    if cov_close_ms <= 0:
        return 0  # 覆盖 0(同刻病理面)= 不归因, fold c=0 非 broke -> 0 同判
    return int(round(delta * 1000 / cov_close_ms))


class _SampleEventsMixin:
    """流量步进事件源 mixin(挂 TrafficSampleModule; 主循环线程独占, 无锁)"""

    # ---------- 观测捕获(采样调用链内的单点) ----------

    def _ev_capture_obs(self, key: str, kind: str, ts: float, dl_total, up_total, closed: Optional[tuple]) -> None:
        """捕获本 tick 该系列的新观测(每系列每 tick 恰一个; 派发点整体消费清空)。
        n 型捕获只为占位(n 不产数据点不推进观测链), 恒被派发点跳过。"""
        self._ev_tick_obs[key] = (kind, ts, dl_total, up_total, closed)

    def _ev_capture_zn(self, key: str, kind: str, ts: float, dl_total, up_total) -> None:
        """_advance_run 出口的 z/n 观测捕获(薄封装: n 型无观测无 totals, 显式置 None)。"""
        if kind == "z":
            self._ev_capture_obs(key, "z", ts, dl_total, up_total, None)
        else:
            self._ev_capture_obs(key, "n", ts, None, None, None)

    def _ev_note_z_open(self, key: str, ts: float, dl_total, up_total) -> None:
        """z 游程开启登记事件摊配链锚(_ev_z_chain[key] = (anchor_ts, dl_total, up_total)):
        anchor = 读侧折叠 run.anchor_ts 的等价物 —— 等值接续(totals == 前观测)时锚 =
        前观测槽 ts, 首槽台阶形态(z1 已在派发面出过台阶)锚 = 本槽 ts。链跨封口段持续
        (00:00 硬切 / 保险闸 / 换型进 n 后回 z 的续开段不换锚 —— 折叠 run 跨封口边界
        连续, 评审 #1: 收口摊配 span/cov 须覆盖整段空闲链); 链只在 r 收口消费时清除,
        totals 断链(重置/跳变)由收口侧匹配校验兜底回退单段锚。"""
        if key in self._ev_z_chain:
            return
        pre = self._ev_prev_obs.get(key)
        if pre is not None and pre[1] == dl_total and pre[2] == up_total:
            self._ev_z_chain[key] = (pre[0], dl_total, up_total)
        else:
            self._ev_z_chain[key] = (ts, dl_total, up_total)

    # ---------- 派发(采样 handler 收尾, 与 _publish_live_tail 同点) ----------

    def _publish_traffic_events(self) -> None:
        """per-scope 增量派发(主循环线程): 本 tick 捕获的观测 -> 系列差分点 batch ->
        hub.publish_traffic_batch(hub 侧按订阅 scope 扇出: global/torrent 直取, group Σ)。

        - 无捕获(该 tick 无任何观测 —— 防御面, 全局恒采常态不发生)直接返回;
        - hub 缺席(ctx.web None / 替身无方法)或无订阅者: 只推进观测链不计算不派发
          (订阅面零开销 + 链连续性: 订阅者中途加入时 prev_obs 已在位, 首帧即真值);
        - n 型观测跳过(无数据点, 断连语义); r/z 型推进 prev_obs 并(活跃时)计算点。
        派发异常不上抛(事件是加速手段, 丢失退化 GET 轮询, 与 notify 同纪律)。"""
        obs, self._ev_tick_obs = self._ev_tick_obs, {}
        if not obs:
            return
        hub = getattr(self._ctx, "web", None)
        active = (
            hub is not None and callable(getattr(hub, "publish_traffic_batch", None)) and
            callable(getattr(hub, "traffic_stream_active", None)) and hub.traffic_stream_active()
        )
        si = self._effective_interval or 1.0
        batch: dict = {}
        prev = self._ev_prev_obs
        for key, (kind, ts, dl_total, up_total, closed) in obs.items():
            if kind == "n":
                continue  # null/断连观测: 无数据点(显式空值点由 GET 读侧承载, 事件流如实静默)
            pre = prev.get(key)
            prev[key] = (ts, dl_total, up_total)  # 观测链推进(r/z 同; 链首/重置形态由点函数判)
            # 摊配链锚: r 收口消费即清除(无论封口型 —— 折叠 run 被本观测收口); z/n 保留
            z_chain = self._ev_z_chain.pop(key, None) if kind == "r" else None
            if active:
                try:
                    batch[key] = _ev_series_point(pre, kind, ts, dl_total, up_total, closed, si, z_chain)
                except Exception:  # 单系列点计算异常不阻断其余系列(事件面非数据面)
                    logger.exception(f"流量事件 | {key} 步进点计算失败, 本 tick 该系列缺帧")
        self._ev_prune_stale_keys()
        if not batch:
            return
        try:
            hub.publish_traffic_batch(batch)
        except Exception:
            logger.exception("流量事件 | 步进事件派发失败(丢失退化 GET 轮询)")

    def _ev_prune_stale_keys(self) -> None:
        """内存卫生(评审 #2-3): 当前采样面之外的系列键差集清除 _ev_prev_obs/_ev_z_chain
        —— 种子删除/qB 移除后其观测游标与摊配链随种子 churn 单点回收(否则随种子删除
        单调无界增长)。判定面 = 当前 by_hash 种子集(全局恒在): 断连期 by_hash 不变,
        链照常保留(恢复后收口摊配续上); 种子淘汰/删种即清。主循环线程单点, 无锁。"""
        by_hash = getattr(self._ctx.store, "by_hash", None)
        if by_hash is None:
            return
        alive = {GLOBAL_SERIES_KEY}
        alive.update(_TORRENT_KEY_PREFIX + rec.hash for rec in by_hash.values())
        for table in (self._ev_prev_obs, self._ev_z_chain):
            for key in [k for k in table if k not in alive]:
                del table[key]
