"""test_web_longtail_traffic 测试计划: P1 覆盖率提升轮 + v3 活尾 (运行时 / 命令 / 路由长尾)

## 测试计划(每个测试函数一条)
### P1 覆盖率提升轮: webui 运行时与命令长尾
- test_api_traffic_qb_global_live_tail_realtime: (S6 验收追加)raw 段窗活尾合流 —— 纯活尾(零盘)出实时桶点(桶值 = 区间平均, 计划 26-10-07-2127 S2);
  磁盘落盘后滞后快照重列已落盘记录被按 ts 精确去重(快照与 flush 竞态不重不漏), 快照清空后磁盘响应与合流响应逐点一致
- test_api_traffic_qb_group_live_tail_member_only: (S6)组端点空态判据计入活尾 —— 成员仅活尾(零盘)组图非空(单记录窗首基线缺失 D4 0 线, S2);
  单种端点同享活尾
- test_api_traffic_qb_global_3d_live_open_hour_fills_tail_vacuum: (S7, 2026-10-14 用户报「3 天及以上的流量图视图有真空: 目前仅显示到 14 日 0 点, 实际上现在已经 14 日 1 点了」)
  3d 窗(hour 段)活尾合流 —— 磁盘封口行之外, 活尾 pending_agg 开放小时部分行按 epoch 合流, 图尾桶(栅格最后一桶)从 null 真空变为实时值(修复前形态对照);
  totals 相邻桶快照差分跨封口/活尾接缝延续
- test_api_traffic_qb_global_6mo_live_open_day_fills_tail: (S7)6mo 窗(day 段)活尾合流 —— 当日日界桶从 null 真空变为活尾日部分行; totals 跨接缝差分
- test_api_traffic_qb_global_all_live_current_month_in_grid: (S7)all 窗(month 段)活尾合流 —— 数据面铺格计入活尾当月行(修复前当月桶整个不在栅格里), 当月桶出值 + totals 差分
- test_api_traffic_qb_group_30d_live_member_partial_and_empty_state: (S7)组端点 agg 段活尾合流 —— 成员仅活尾(零盘)组图非空(空态判据计入活尾部分行);
  组尾桶 = Σ 成员观测(无行成员按 0 计), 磁盘行与活尾部分行按成员各自合流;
  all 窗(month 段)活尾当月行并入组月行铺格面 + 组 totals 逐成员差分(基线缺失不出洞; 同成员磁盘上月行 -> 活尾当月行跨接缝差分链不断)
"""

import base64

import errno

import os

import re

import tempfile

import time

from pathlib import Path

from types import SimpleNamespace

from auto_qb.infra import file_access

from auto_qb.infra.utils import encode_group_key

from auto_qb.webui.runtime import (
    CMD_SLOW_MS,
    EVENT_QUEUE_MAX,
    REANNOUNCE_CONFIRM_TIMEOUT,
    WEB_RESULT_MAX,
    WEB_RESULT_TTL,
    WebUIRuntime,
)

from helpers import capture_logs

from webui_helpers import (
    KEY,
    STATIC_ROOT,
    _enable_qb_traffic,
    _qb_v4,
    _make_grouped_manager,
    _attach_live_tail_host,
)


def test_api_traffic_qb_global_live_tail_realtime(web_env):
    """(S6)raw 段窗活尾合流: 纯活尾(零盘)出实时桶点(不等 flush_interval 落盘);
    磁盘落盘后滞后快照重列已落盘记录被按 ts 精确去重(快照与 flush 竞态不重不漏),
    快照清空后磁盘响应与合流响应逐点一致 —— 图面全程无跳变"""
    from auto_qb.core.traffic_store import LiveTail, V4Sample, v4_epoch_date_str

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    _enable_qb_traffic(mgr)
    store = _qb_v4(mgr)
    now = int(time.time())
    base = ((now - 240) // 30) * 30  # 5m 窗内
    b0, b1, b2 = (base + i * 30 for i in range(3))
    recs = (V4Sample(100, 50, 1000, 500), V4Sample(200, 70, 2000, 800))
    tail_full = LiveTail(
        block_open=True,
        head_pending=True,
        start_epoch=b0 + 30,
        interval_s=30,
        projected_ts=float(b1 + 30),
        records=recs,
        open_run=None,
    )
    # 纯活尾(块全量未落盘, 零天文件): 图面实时出点
    _attach_live_tail_host(mgr, {"global": tail_full})
    body = client.get("/api/traffic/qb/global", headers=auth, params={"window": "5m"}).json()

    def pt(seg, t):
        return next((p for p in body[seg] if p and p["t"] == t), None)

    assert body["meta"]["stale"] is False
    assert pt("points", b0) == {"t": b0, "dl": 0, "up": 0}  # 区间平均口径: 首点基线缺失 D4 0 线
    assert pt("points", b1) == {"t": b1, "dl": 33, "up": 10}  # delta(1000, 300)/30
    assert pt("points", b2) is None  # 活尾之外无观测
    assert pt("totals", b1) == {"t": b1, "dl": 1000, "up": 300}
    live_body = body
    # flush 落盘(同两记录) + 滞后快照仍重列全部记录: 按 ts 去重, 响应逐点不变
    store.append_records("global", v4_epoch_date_str(b0 + 30), (b0 + 30, 30), recs, (1000, 500))
    body = client.get("/api/traffic/qb/global", headers=auth, params={"window": "5m"}).json()
    assert body == live_body
    # 快照清空(flush 后的下一轮发布): 纯磁盘读路径, 响应仍逐点一致
    _attach_live_tail_host(mgr, {})
    body = client.get("/api/traffic/qb/global", headers=auth, params={"window": "5m"}).json()
    assert body == live_body


def test_api_traffic_qb_group_live_tail_member_only(web_env):
    """(S6)组端点空态判据计入活尾: 成员仅活尾(零盘)组图非空(不再误判「从未产过流量」);
    单种端点同享活尾"""
    from auto_qb.core.traffic_store import LiveTail, V4Sample

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    _enable_qb_traffic(mgr)
    now = int(time.time())
    base = ((now - 240) // 30) * 30  # 5m 窗内
    b0, b1 = (base + i * 30 for i in range(2))
    tail = LiveTail(
        block_open=True,
        head_pending=True,
        start_epoch=b0 + 30,
        interval_s=30,
        projected_ts=float(b1 + 30),
        records=(V4Sample(300, 30, 500, 50), ),
        open_run=None,
    )
    _attach_live_tail_host(mgr, {"torrent:HB": tail})
    body = client.get(f"/api/traffic/qb/group/{encode_group_key(KEY)}", headers=auth, params={"window": "5m"}).json()

    def pt(seg, t):
        return next((p for p in body[seg] if p and p["t"] == t), None)

    assert pt("points", b0) == {"t": b0, "dl": 0, "up": 0}  # HB 活尾观测(HA 无数据按 0 计); 单记录窗首基线缺失 D4 0 线
    assert pt("totals", b0) == {"t": b0, "dl": 0, "up": 0}  # 窗首基线缺失
    assert pt("points", b1) is None  # 单记录覆盖桶 [b0, b0+30) 恰一格, b1 无观测
    # 单种端点同享活尾(区间平均口径: 单记录无基线, D4 豁免 0 线 —— 桶在即合流生效)
    body = client.get("/api/traffic/qb/torrent/HB", headers=auth, params={"window": "5m"}).json()
    assert next((p for p in body["points"] if p and p["t"] == b0), None) == {"t": b0, "dl": 0, "up": 0}


def test_api_traffic_qb_global_3d_live_open_hour_fills_tail_vacuum(web_env):
    """(S7, 2026-10-14 用户报「3 天及以上的流量图视图有真空: 目前仅显示到 14 日 0 点,
    实际上现在已经 14 日 1 点了」)3d 窗(hour 段)活尾合流: agg.dat 只有封口行, 当前
    开放小时只活在采样模块累计器 —— 活尾 pending_agg 把它发布出来, 读侧按 epoch 与
    磁盘封口行合流: 图尾桶(栅格最后一桶)从 null 真空变为实时值(修复前形态对照断言),
    totals 相邻桶快照差分跨封口/活尾接缝自然延续"""
    from auto_qb.core import traffic_grid as tg
    from auto_qb.core.traffic_store import AggRow, LiveTail

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    _enable_qb_traffic(mgr)
    store = _qb_v4(mgr)
    now = int(time.time())
    h_open = tg.build_grid("3d", now).last  # 图尾桶(开放小时; now 恰整点时 = 刚完结小时, 断言不变式)
    rows = []
    t_dl, t_up = 1000, 400
    for i in range(5, 0, -1):  # 尾桶前 5 小时的封口行(totals 单调递增, 差分链不断)
        t_dl += 500
        t_up += 300
        rows.append(AggRow("hour", h_open - i * 3600, 100, 200, 30, 60, t_dl, t_up, 3600))
    store.append_agg_rows("global", tuple(rows))
    live = LiveTail(
        block_open=False,
        head_pending=False,
        start_epoch=None,
        interval_s=30,
        projected_ts=0.0,
        records=(),
        open_run=None,
        pending_agg=(AggRow("hour", h_open, 300, 300, 100, 100, 5000, 2500, 1800), ),
    )
    # 修复前形态(无活尾): 尾桶 = null 真空(只显示到最后一个封口桶)
    _attach_live_tail_host(mgr, {})
    body0 = client.get("/api/traffic/qb/global", headers=auth, params={"window": "3d"}).json()
    assert body0["meta"]["interval_s"] == 3600 and body0["points"][-1] is None
    # 修复后: 活尾开放小时部分行合流 —— 尾桶出值, totals 跨接缝差分
    _attach_live_tail_host(mgr, {"global": live})
    body = client.get("/api/traffic/qb/global", headers=auth, params={"window": "3d"}).json()
    assert body["points"][-1] == {"t": h_open, "dl": 300, "up": 100}
    assert body["points"][-2] == {"t": h_open - 3600, "dl": 100, "up": 30}  # 前一封口桶原样
    assert body["totals"][-1] == {"t": h_open, "dl": 1500, "up": 600}  # 5000-3500 / 2500-1900


def test_api_traffic_qb_global_6mo_live_open_day_fills_tail(web_env):
    """(S7)6mo 窗(day 段)活尾合流: 当日(本地日界桶)只活在写侧累计器 —— 活尾日部分行
    按 epoch 合流后, 图尾桶从 null 真空变为实时值; totals 跨封口/活尾接缝差分"""
    from auto_qb.core import traffic_grid as tg
    from auto_qb.core.traffic_store import AggRow, LiveTail

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    _enable_qb_traffic(mgr)
    store = _qb_v4(mgr)
    now = int(time.time())
    d_open = tg.build_grid("6mo", now).last  # 当日日界桶(now 恰零点时 = 前一日, 断言不变式)
    store.append_agg_rows(
        "global", (
            AggRow("day", d_open - 2 * 86400, 60, 90, 40, 50, 1000, 500, 86400),
            AggRow("day", d_open - 86400, 100, 200, 50, 60, 3500, 1900, 86400),
        )
    )
    live = LiveTail(
        block_open=False,
        head_pending=False,
        start_epoch=None,
        interval_s=30,
        projected_ts=0.0,
        records=(),
        open_run=None,
        pending_agg=(AggRow("day", d_open, 300, 300, 100, 100, 9000, 4500, 43200), ),
    )
    _attach_live_tail_host(mgr, {"global": live})
    body = client.get("/api/traffic/qb/global", headers=auth, params={"window": "6mo"}).json()
    assert body["meta"]["interval_s"] == 86400
    assert body["points"][-1] == {"t": d_open, "dl": 300, "up": 100}
    assert body["totals"][-1] == {"t": d_open, "dl": 5500, "up": 2600}  # 9000-3500 / 4500-1900


def test_api_traffic_qb_global_all_live_current_month_in_grid(web_env):
    """(S7)all 窗(month 段)活尾合流: 数据面铺格(build_month_grid)计入活尾当月行 ——
    修复前当月桶整个不在栅格里(连 null 都没有); 修复后当月桶出值 + totals 差分"""
    from auto_qb.core.traffic_store import AggRow, LiveTail, v4_month_epoch

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    _enable_qb_traffic(mgr)
    store = _qb_v4(mgr)
    now = int(time.time())
    m_cur = v4_month_epoch(now)
    m_prev = v4_month_epoch(m_cur - 86400)  # 上一自然月
    store.append_agg_rows("global", (AggRow("month", m_prev, 100, 200, 50, 60, 1000, 500, 3 * 86400), ))
    live = LiveTail(
        block_open=False,
        head_pending=False,
        start_epoch=None,
        interval_s=30,
        projected_ts=0.0,
        records=(),
        open_run=None,
        pending_agg=(AggRow("month", m_cur, 300, 300, 100, 100, 5000, 2500, 20 * 86400), ),
    )
    # 修复前: 数据面只有上一月 -> 栅格不含当月
    _attach_live_tail_host(mgr, {})
    body0 = client.get("/api/traffic/qb/global", headers=auth, params={"window": "all"}).json()
    assert len(body0["points"]) == 1 and body0["points"][0]["t"] == m_prev
    # 修复后: 活尾当月行并入铺格面并合流
    _attach_live_tail_host(mgr, {"global": live})
    body = client.get("/api/traffic/qb/global", headers=auth, params={"window": "all"}).json()
    assert body["meta"]["interval_s"] == 30 * 86400
    assert len(body["points"]) == 2
    assert body["points"][-1] == {"t": m_cur, "dl": 300, "up": 100}
    assert body["totals"][-1] == {"t": m_cur, "dl": 4000, "up": 2000}  # 5000-1000 / 2500-500


def test_api_traffic_qb_group_30d_live_member_partial_and_empty_state(web_env):
    """(S7)组端点 agg 段活尾合流: 成员仅活尾(零盘)组图非空 —— 空态判据「组从未产过流量」
    计入活尾部分行(修复前误判空态); 组尾桶 = Σ 成员观测(无行成员按 0 计); 磁盘封口行与
    活尾部分行按成员各自合流, 组口径不变; all 窗(month 段)活尾当月行并入组月行铺格面"""
    from auto_qb.core import traffic_grid as tg
    from auto_qb.core.traffic_store import AggRow, LiveTail, v4_month_epoch

    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    _enable_qb_traffic(mgr)
    now = int(time.time())
    h_open = tg.build_grid("30d", now).last  # 组图尾桶
    live = LiveTail(
        block_open=False,
        head_pending=False,
        start_epoch=None,
        interval_s=30,
        projected_ts=0.0,
        records=(),
        open_run=None,
        pending_agg=(AggRow("hour", h_open, 300, 300, 100, 100, 5000, 2500, 1800), ),
    )
    _attach_live_tail_host(mgr, {"torrent:HB": live})  # HB 仅活尾(零盘), HA 全无
    body = client.get(f"/api/traffic/qb/group/{encode_group_key(KEY)}", headers=auth, params={"window": "30d"}).json()
    assert body["points"] != []  # 非空态(修复前 = 空态 points: [])
    assert body["points"][-1] == {"t": h_open, "dl": 300, "up": 100}  # HB 活尾观测, HA 无行按 0 计
    assert body["totals"][-1] == {"t": h_open, "dl": 0, "up": 0}  # 双成员基线缺失 -> 0(不出洞)
    # HA 有磁盘封口行: 组尾桶仍 = HB 活尾 + HA 无观测(0); HA 历史桶照常出值
    store = _qb_v4(mgr)
    store.append_agg_rows("torrent:HA", (AggRow("hour", h_open - 3600, 100, 200, 50, 60, 1000, 500, 3600), ))
    body2 = client.get(f"/api/traffic/qb/group/{encode_group_key(KEY)}", headers=auth, params={"window": "30d"}).json()
    assert body2["points"][-1] == {"t": h_open, "dl": 300, "up": 100}
    assert next(p for p in body2["points"] if p and p["t"] == h_open - 3600) == {
        "t": h_open - 3600,
        "dl": 100,
        "up": 50
    }
    assert next(p for p in body2["totals"] if p and p["t"] == h_open - 3600) == {"t": h_open - 3600, "dl": 0, "up": 0}
    # all 窗(month 段): HB 活尾当月行并入组月行铺格面(HA 持上一月磁盘行)
    m_cur = v4_month_epoch(now)
    m_prev = v4_month_epoch(m_cur - 86400)
    store.append_agg_rows("torrent:HA", (AggRow("month", m_prev, 100, 200, 50, 60, 1000, 500, 3 * 86400), ))
    live_month = LiveTail(
        block_open=False,
        head_pending=False,
        start_epoch=None,
        interval_s=30,
        projected_ts=0.0,
        records=(),
        open_run=None,
        pending_agg=(AggRow("month", m_cur, 300, 300, 100, 100, 5000, 2500, 20 * 86400), ),
    )
    _attach_live_tail_host(mgr, {"torrent:HB": live_month})
    body3 = client.get(f"/api/traffic/qb/group/{encode_group_key(KEY)}", headers=auth, params={"window": "all"}).json()
    assert body3["meta"]["interval_s"] == 30 * 86400
    assert [p["t"] for p in body3["points"]] == [m_prev, m_cur]  # 铺格面含活尾当月行
    assert body3["points"][-1] == {"t": m_cur, "dl": 300, "up": 100}
    assert body3["totals"][-1] == {"t": m_cur, "dl": 0, "up": 0}  # 组口径逐成员差分: HA 无当月行, HB 无上月基线 -> 0(不出洞)
    # 同一成员跨接缝(HA 磁盘上月行 -> 活尾当月行): 组 totals 差分链不断
    _attach_live_tail_host(mgr, {"torrent:HA": live_month})
    body4 = client.get(f"/api/traffic/qb/group/{encode_group_key(KEY)}", headers=auth, params={"window": "all"}).json()
    assert body4["points"][-1] == {"t": m_cur, "dl": 300, "up": 100}  # HA 活尾观测, HB 无行按 0 计
    assert body4["totals"][-1] == {"t": m_cur, "dl": 4000, "up": 2000}  # HA 5000-1000 / 2500-500, HB 无观测
    assert next(p for p in body4["totals"] if p and p["t"] == m_prev) == {"t": m_prev, "dl": 0, "up": 0}  # 窗首基线缺失
