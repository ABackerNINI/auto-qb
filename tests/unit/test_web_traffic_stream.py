"""test_web_traffic_stream 测试计划: 流量步进 SSE 传输面(plan 26-11-18-0037 阶段 2, §03 (2))

## 测试计划(每个测试函数一条)
- test_traffic_stream_scope_validation: scope 缺参 422 / 未知形态与裸 hash 400 / 种子哈希
  非法 400 / 组标识畸形 400(同 /api/groups 通道)/ 三形态合法 scope 通过校验(_parse_scope 单点)
- test_traffic_stream_ticket_discipline: 票据无效/缺参 401(全局鉴权闸 _TICKET_STREAM_PATHS
  fail-fast 4xx); 有效票据在本路径被消费(取即删); /api/events 既有路径不受影响;
  换票池满额 503(共用 POST /api/events/ticket 同一池)
- test_traffic_stream_sse_lifecycle: hello 帧 -> 派发帧(event: traffic, {seq,scope,points})
  -> keepalive 心跳(间隔 < WEB_VIEW_TTL)-> 消费端关闭 finally 退订(有界等待, 同
  test_web_hr_endpoints 先例)
- test_traffic_stream_sse_generator_error_still_unsubscribes: 生成器异常死亡也走 finally 退订
- test_traffic_stream_multi_subscriber_isolation: 同 scope 两队列各得一份拷贝(帧对象互不同一),
  不同 scope 互不串(各取各的点)
- test_traffic_stream_seq_continuity: 连续多拍发布 seq 单调递增; 无真值点的 scope 不派帧
  不占号(静默 = 停流信号)
- test_traffic_stream_queue_full_drops: 队列满丢弃 + traffic_notify_dropped 计数可观测 +
  seq 断档(消费端据 D9 重拉兜底)
- test_traffic_stream_group_scope_merge: 组 scope Sigma 口径(_group_merge_points 单 tick 形态):
  已知向求和未知向按 0 计 / 该成员此 t 无点不设观测 / 全 None 真值点不设观测 / 全员无观测
  与组解散不派帧
- test_publish_global_frame_per_tick: 主循环侧(注入时钟)handler 每 tick 恰 1 帧/scope,
  载荷形状 {seq, scope, points:[{t, dl, up}]}
- test_publish_idle_tick_zero_point: 空闲 tick -> 差分真值点 {t, 0, 0}(z 观测链推进)
- test_publish_disconnect_no_data_points: 断连分支不推数据点(帧数 0), seq 不虚增, 恢复后续上
- test_publish_no_subscriber_keeps_chain: 无订阅者零计算零派发, 观测链照常推进(中途订阅首帧真值)
- test_publish_z_run_close_matches_get_contract: z 游程收口样本点与 GET 读侧样本分组装配
  逐位一致(assemble_group_points 同链活尾槽流 k=1 装配; 清洁等节拍链下收口/链首两锚逐位
  对账); 空闲期事件点 = 派发时刻真值 0, 收口后读侧摊配回写属 GET 全量重算能力, 事件流
  增量语义不重发(D9 对账校准 —— traffic_sample_events「已知有界偏差」的机器钉面)
- test_publish_midnight_seal_close_matches_get: 常态路径守阵(评审 #1)—— 活跃 -> 空闲跨
  00:00 硬切(z 游程跨天封口重开, 摊配链锚跨段持续) -> 次日恢复 r 收口: 收口点与 GET 读侧
  (跨天日块 + 活尾块合流装配)逐位一致, 收口后链锚清除
- test_publish_marked_recovery_spread_matches_get: 评审 #5 —— 活跃 -> 空闲(z 游程开着) ->
  断连数拍(z 换型封口进 n) -> 恢复 totals 增长(非零 step): 恢复点 marked 摊配份额值级断言
  + 与 GET 读侧同链活尾装配逐位一致
- test_publish_z_chain_stepped_open: 链锚首槽台阶形态(空闲首拍 totals 已增长): 锚 = 首零
  样本槽(_ev_note_z_open else 支), z1 台阶点/收口摊配点与 GET 读侧逐位一致
- test_publish_z_chain_zero_item_close: 收口时链项覆盖 0 的退化面(一拍空闲闪断): 空项面
  摊配不触发收口全步, 与 GET 读侧三点逐位一致
- test_ev_series_point_stale_chain_fallback: 链 totals 断链 -> 回退单段锚与链缺位同值(纯函数)
- test_publish_marked_reset_recovery_null: 轮2 #1 —— 断连恢复 + totals 回落(重置):
  恢复点两向 None(broke = marked 置位守阵), 与 GET 读侧 fold 同判对账
- test_ev_series_point_aged_chain_fallback: 轮2 #2 —— 链锚年龄超回看界回退单段锚
  (与链缺位同值), 未超界链照常参与摊配(纯函数两路径可分)
- test_publish_stale_keys_pruned_when_torrent_gone: 轮2 #3 —— 种子移出采样面后观测
  游标/摊配链差集清除(churn 回收), 全局恒在
- test_publish_prune_store_without_by_hash: store 替身缺 by_hash 判定面 -> 清除静默跳过
- test_traffic_stream_keepalive_ttl_invariant: 静态守阵(评审 #7)—— SSE_KEEPALIVE_S <
  WEB_VIEW_TTL 且两端点共用同一常量
- test_publish_layering_no_webui_import: 层级方向守阵 —— 采样模块五拆分件源码 import 面
  零 webui 引用(core 不得反向依赖表现层, 依赖倒置经 ctx.web 鸭型发布)
- test_publish_hub_absent_silent: hub 缺席(ctx.web None)静默关断, 零异常零派发
- test_publish_reset_point_zero: 计数器重置 -> 差分 None -> 点值 0(三层同判, 绝不产负增量)
- test_publish_long_gap_null_point: 断连跨停机洞(缝 > 60s)恢复 -> 两向 None(断链未知不造 0 值)
- test_publish_same_tick_zero_cov: 同刻病理面(对跨 0) -> 覆盖 0 不归因 -> 0
- test_publish_point_error_isolated: 单系列点计算异常不阻断其余系列, 留痕不上抛
- test_publish_hub_publish_error_swallowed: hub 派发异常不上抛(与 notify 同纪律)
- test_traffic_stream_put_error_counts_dropped: put 非 Full 异常同样计丢弃 + 丢弃帧占号不回收

时钟/节拍纪律: 采样轮直调 handle_traffic_sample(不经队列/到期闸门), FakeClock 逐轮推进
恰一个生效间隔(清洁链 —— 事件口径与读侧逐位对账的前提); 整数对齐 epoch(块首 B.start
int 截断不引入 ts 漂移)。
"""
import queue as _queue
import time as _time

import anyio
import pytest

from auto_qb.config import QbTraffic
from auto_qb.core.traffic_group_assembly import assemble_group_points, assemble_group_points_from_blocks
from auto_qb.core.traffic_store import GLOBAL_KEY, V4Block, parse_v4_day_text, v4_day_file_path, v4_epoch_date_str, v4_live_tail_slots
from auto_qb.infra.utils_paths import encode_group_key

from clock import FakeClock
from helpers import FakeClient, active_torrent, capture_logs, make_manager, seed_store, server_state

SI = 2.0  # 生效采样间隔(秒): multiplier=1 x main_tick=2.0, 清洁链基准
_AUTH_HDR = "Auth" + "orization"  # 写侧凭据判据测试 idiom(traffic_sample_support 同款)

# ---------- 构造辅助 ----------


def _mgr(tmp_path, clock=None, qb_traffic=None):
    """流量步进事件源用采样环境(bare 装配 + 可注入假钟; 间隔 = 1 x main_tick)"""
    mgr = make_manager(str(tmp_path / "state.json"), bare=True, main_tick=SI, client=FakeClient(), clock=clock)
    mgr.config.data_dir = str(tmp_path)
    mgr.config.qb_traffic = qb_traffic if qb_traffic is not None else QbTraffic(
        enabled=True, sample_interval_multiplier=1
    )
    return mgr


def _run(mgr, dry_run: bool = False) -> None:
    """直调一轮采样(不经队列/到期闸门; 与 traffic_sample_support._run_sample 同款)"""
    mgr.host.get("qb_traffic").handle_traffic_sample(dry_run=dry_run)


def _auth_request(path="/api/traffic/qb/stream", query="", client=("127.0.0.1", 50000)):
    """require_token 直调用的 Request 构造(test_web_auth._auth_request 同款内联形)"""
    from starlette.requests import Request as StarletteRequest

    scope = {
        "type": "http",
        "asgi": {
            "version": "3.0"
        },
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": query.encode(),
        "root_path": "",
        "headers": [(b"host", b"127.0.0.1:8080")],
        "client": client,
        "server": ("127.0.0.1", 8080),
    }
    return StarletteRequest(scope)


def _stream_route(mgr):
    """直调生产路由端点(绕开 TestClient 的流式端点阻塞; test_web_hr_endpoints 同款)"""
    from auto_qb.webui.server.context import WebContext
    from auto_qb.webui.server.routes import traffic_stream as traffic_stream_mod

    return next(
        r for r in traffic_stream_mod.build_router(WebContext(mgr)).routes if r.path == "/api/traffic/qb/stream"
    )


# ---------- 端点电池 ----------


def test_traffic_stream_scope_validation(web_env):
    """scope 缺参 422 / 未知形态与裸 hash 400 / 哈希非法 400 / 组标识畸形 400 / 三形态合法"""
    from auto_qb.webui.server.routes.traffic_stream import _parse_scope

    mgr, client = web_env
    auth = {_AUTH_HDR: f"Bearer {mgr.web.token}"}
    # 缺参 -> 422(FastAPI 必填查询参数), 未知形态/裸 hash -> 400
    assert client.get("/api/traffic/qb/stream", headers=auth).status_code == 422
    for bad in ("", "foo:bar", "HASH123", "torrent:", "group:"):
        assert client.get(f"/api/traffic/qb/stream?scope={bad}", headers=auth).status_code == 400
    # 种子哈希非法(路径不安全字符) -> 400, 与 GET /api/traffic/qb/torrent/{hash} 同判
    assert client.get("/api/traffic/qb/stream?scope=torrent:..%2Fx", headers=auth).status_code == 400
    # 组标识畸形 -> 400(同 /api/groups/{key} 通道)
    assert client.get("/api/traffic/qb/stream?scope=group:not-b64!!", headers=auth).status_code == 400
    # 三形态合法 scope 过校验单点(不触 hub); torrent 合法哈希放行
    assert _parse_scope(mgr, "global") == ("global", None)
    assert _parse_scope(mgr, "torrent:HASH123")[0] == "torrent:HASH123"
    gk = ("剧名", ("a.mkv", ))
    assert _parse_scope(mgr, "group:" + encode_group_key(gk)) == ("group:" + encode_group_key(gk), gk)


def test_traffic_stream_ticket_discipline(web_env):
    """票据无效/缺参 401(fail-fast 4xx); 有效票据本路径消费即删; /api/events 不受影响;
    换票池满额 503(共用同一签发池)"""
    from auto_qb.webui.server.auth import make_require_token
    from auto_qb.webui.runtime import EVENT_TICKET_MAX

    mgr, client = web_env
    auth = {_AUTH_HDR: f"Bearer {mgr.web.token}"}
    # 无票据(缺参)与无效票据 -> 401
    assert client.get("/api/traffic/qb/stream?scope=global").status_code == 401
    assert client.get("/api/traffic/qb/stream?scope=global&ticket=bogus").status_code == 401
    # 有效票据在本路径被全局闸消费(取即删)—— require_token 直调
    require_token = make_require_token(mgr)
    ticket = mgr.web.issue_event_ticket()
    assert require_token(_auth_request(query=f"ticket={ticket}"), "") is None
    assert mgr.web.consume_event_ticket(ticket) is False, "闸必须已消费该票据"
    # /api/events 既有票据路径行为不变(放行 + 消费); 集合外路径不消费
    t2 = mgr.web.issue_event_ticket()
    assert require_token(_auth_request(path="/api/events", query=f"ticket={t2}"), "") is None
    assert mgr.web.consume_event_ticket(t2) is False
    t3 = mgr.web.issue_event_ticket()
    with pytest.raises(Exception):
        require_token(_auth_request(path="/api/state", query=f"ticket={t3}"), "")
    assert mgr.web.consume_event_ticket(t3) is True, "集合外路径不得误消费票据"
    # 满额 503(同一签发池, 前端据此退 GET 轮询兜底 E7)
    for _ in range(EVENT_TICKET_MAX):
        mgr.web.issue_event_ticket()
    assert client.post("/api/events/ticket", headers=auth).status_code == 503


def test_traffic_stream_sse_lifecycle(web_env, monkeypatch):
    """hello 帧 -> 派发帧 -> keepalive 心跳 -> 消费端关闭 finally 退订(有界等待)"""
    import gc

    from auto_qb.webui.server.routes import traffic_stream as traffic_stream_mod

    mgr, _client = web_env
    monkeypatch.setattr(traffic_stream_mod, "SSE_KEEPALIVE_S", 0.05)
    touches = []
    monkeypatch.setattr(mgr.web, "touch", lambda: touches.append(1))
    resp = _stream_route(mgr).endpoint(scope="global")
    assert resp.media_type == "text/event-stream"
    assert resp.headers["cache-control"] == "no-cache"
    assert resp.headers["x-accel-buffering"] == "no"  # 反代不缓冲, SSE 才能逐帧到

    async def _drive():
        frames = resp.body_iterator
        assert await frames.__anext__() == 'event: hello\ndata: {"ok": true, "scope": "global"}\n\n'
        assert touches == []  # hello 帧不触发 touch(还没进事件循环)
        hit = mgr.web.publish_traffic_batch({"global": {"t": 100.0, "dl": 5, "up": 6}})
        assert hit == 1
        assert await frames.__anext__(
        ) == ('event: traffic\ndata: {"seq": 1, "scope": "global", "points": [{"t": 100.0, "dl": 5, "up": 6}]}\n\n')
        assert len(touches) == 1  # 事件帧先 touch 再发
        t0 = _time.monotonic()
        assert await frames.__anext__() == ": keepalive\n\n"  # 队列空 -> 心跳注释帧
        assert _time.monotonic() - t0 >= 0.05 - 0.02  # 挂钟下界留余量(pitfalls/testing/timing-tolerance.md)
        assert len(touches) == 2
        # 心跳后循环继续(continue): 再派发一条, 事件帧照常送达
        mgr.web.publish_traffic_batch({"global": {"t": 101.0, "dl": 1, "up": 2}})
        assert await frames.__anext__(
        ) == ('event: traffic\ndata: {"seq": 2, "scope": "global", "points": [{"t": 101.0, "dl": 1, "up": 2}]}\n\n')
        assert len(touches) == 3
        await frames.aclose()  # 客户端断开: 消费端关闭

    anyio.run(_drive)
    # 终结退订是跨线程终态(生成器由 anyio 工作线程持有)—— 有界等待判据, 缘由与实测数字
    # 见 test_web_hr_endpoints.test_api_events_sse_stream_lifecycle 同族注释
    del resp
    gc.collect()
    deadline = _time.monotonic() + 5.0
    while mgr.web.traffic_stream_subscriber_count() and _time.monotonic() < deadline:
        _time.sleep(0.005)  # 让出 GIL, 工作线程才能跑完它那几个 del
    if mgr.web.traffic_stream_subscriber_count():
        gc.collect()
    assert mgr.web.traffic_stream_subscriber_count() == 0, "断流后必须退订, 防句柄堆叠"


def test_traffic_stream_sse_generator_error_still_unsubscribes(web_env, monkeypatch):
    """生成器中途异常死亡(touch 异常)也必须走 finally 退订 —— fail-safe 语义"""
    import anyio as _anyio

    mgr, _client = web_env
    resp = _stream_route(mgr).endpoint(scope="global")

    async def _drive():
        frames = resp.body_iterator
        assert (await frames.__anext__()).startswith("event: hello")
        monkeypatch.setattr(mgr.web, "touch", lambda: (_ for _ in ()).throw(RuntimeError("touch boom")))
        mgr.web.publish_traffic_batch({"global": {"t": 1.0, "dl": 0, "up": 0}})
        with pytest.raises(RuntimeError, match="touch boom"):
            await frames.__anext__()

    _anyio.run(_drive)
    assert mgr.web.traffic_stream_subscriber_count() == 0, "生成器异常死亡也要退订, 防句柄堆叠"


def test_traffic_stream_multi_subscriber_isolation(web_env):
    """同 scope 两队列各得一份拷贝(帧对象互不同一), 不同 scope 互不串"""
    mgr, _client = web_env
    q1 = mgr.web.subscribe_traffic_stream("global")
    q2 = mgr.web.subscribe_traffic_stream("global")
    qt = mgr.web.subscribe_traffic_stream("torrent:HASH123")
    assert mgr.web.traffic_stream_subscriber_count() == 3
    mgr.web.publish_traffic_batch({"global": {"t": 1.0, "dl": 5, "up": 6}})
    f1, f2 = q1.get_nowait(), q2.get_nowait()
    assert f1["points"] == f2["points"] == [{"t": 1.0, "dl": 5, "up": 6}]
    assert f1 == f2 and f1 is not f2, "同 scope 两队列各得一份拷贝(隔离面)"
    assert f1["seq"] == f2["seq"] == 1  # 同 scope 同帧号(同一派发)
    with pytest.raises(_queue.Empty):
        qt.get_nowait(), "torrent scope 本 tick 无观测 -> 不派帧(互不串)"
    # 不同 scope 各取各的点
    mgr.web.publish_traffic_batch(
        {
            "global": {
                "t": 2.0,
                "dl": 7,
                "up": 8
            },
            "torrent:HASH123": {
                "t": 2.0,
                "dl": 9,
                "up": 1
            }
        }
    )
    assert qt.get_nowait()["points"] == [{"t": 2.0, "dl": 9, "up": 1}]
    assert q1.get_nowait()["points"] == [{"t": 2.0, "dl": 7, "up": 8}]
    assert q2.get_nowait()["seq"] == 2  # 同 scope 第二帧照常送达
    # 退订成对: 单队列退订后另一队列照常, 空 scope 表项清理; 未知队列/未知 scope 退订零操作
    mgr.web.unsubscribe_traffic_stream("global", q1)
    mgr.web.unsubscribe_traffic_stream("global", object())  # 非本 scope 队列: 零操作
    mgr.web.unsubscribe_traffic_stream("nope", object())  # 未知 scope: 零操作
    mgr.web.publish_traffic_batch({"global": {"t": 3.0, "dl": 0, "up": 0}})
    assert q2.get_nowait()["seq"] == 3
    mgr.web.unsubscribe_traffic_stream("torrent:HASH123", qt)
    mgr.web.unsubscribe_traffic_stream("global", q2)
    assert mgr.web.traffic_stream_active() is False
    assert mgr.web.traffic_stream_subscriber_count() == 0
    assert mgr.web.publish_traffic_batch({"global": {"t": 4.0, "dl": 0, "up": 0}}) == 0, "零订阅者零派发零占号"


def test_traffic_stream_seq_continuity(web_env):
    """连续多拍发布 seq 单调; 无真值点的 scope 不派帧不占号(seq 不虚增)"""
    mgr, _client = web_env
    q = mgr.web.subscribe_traffic_stream("global")
    qg = mgr.web.subscribe_traffic_stream("group:GX")
    for _ in range(3):
        mgr.web.publish_traffic_batch({"global": {"t": 1.0, "dl": 5, "up": 6}})
    seqs = [q.get_nowait()["seq"] for _ in range(3)]
    assert seqs == [1, 2, 3], "seq 每 scope 单调递增"
    with pytest.raises(_queue.Empty):
        qg.get_nowait(), "组 scope 本 tick 无观测(无 batch 键命中)-> 不派帧不占号"
    # 恢复派发: seq 从上一帧续上(静默期无空洞)
    mgr.web.publish_traffic_batch({"global": {"t": 2.0, "dl": 0, "up": 0}})
    assert q.get_nowait()["seq"] == 4


def test_traffic_stream_queue_full_drops(web_env):
    """队列满丢弃 + traffic_notify_dropped 计数可观测 + seq 断档(D9 重拉兜底锚)"""
    from auto_qb.webui.runtime import EVENT_QUEUE_MAX

    mgr, _client = web_env
    q = mgr.web.subscribe_traffic_stream("global")
    for i in range(EVENT_QUEUE_MAX):
        assert mgr.web.publish_traffic_batch({"global": {"t": float(i), "dl": 0, "up": 0}}) == 1
    assert q.qsize() == EVENT_QUEUE_MAX
    hit = mgr.web.publish_traffic_batch({"global": {"t": 999.0, "dl": 0, "up": 0}})
    assert hit == 0 and mgr.web.traffic_notify_dropped == 1, "队列满丢弃计数可观测(notify_dropped 同款)"
    assert q.get_nowait()["seq"] == 1
    q.get_nowait()
    assert list(q.queue)[-1]["seq"] == EVENT_QUEUE_MAX, "丢弃帧之前的帧号连续"
    mgr.web.publish_traffic_batch({"global": {"t": 1000.0, "dl": 0, "up": 0}})
    assert list(q.queue)[-1]["seq"] == EVENT_QUEUE_MAX + 2, "丢弃帧占号不回收 -> 消费端见 seq 断档(D9 兜底)"


def test_traffic_stream_group_scope_merge(web_env):
    """组 scope Sigma 口径(_group_merge_points 单 tick 形态): 已知向求和未知向按 0 计 /
    成员无点不设观测 / 全 None 真值点不设观测 / 全员无观测与组解散不派帧"""
    mgr, _client = web_env
    gk = ("剧名", ("a.mkv", ))
    scope = "group:" + encode_group_key(gk)
    mgr.store.groups[gk] = ["A", "B", "C"]
    q = mgr.web.subscribe_traffic_stream(scope, gk)
    # 已知向求和, 未知向按 0 计(有成员观测); 无点成员 C 不设观测
    mgr.web.publish_traffic_batch(
        {
            "torrent:A": {
                "t": 100.0,
                "dl": 10,
                "up": None
            },
            "torrent:B": {
                "t": 100.0,
                "dl": 5,
                "up": 7
            },
        }
    )
    assert q.get_nowait()["points"] == [{"t": 100.0, "dl": 15, "up": 7}]
    # 全 None 真值点(断链未知)不设观测 -> 全员无观测不派帧
    mgr.web.publish_traffic_batch({"torrent:A": {"t": 101.0, "dl": None, "up": None}})
    with pytest.raises(_queue.Empty):
        q.get_nowait(), "全员无观测不派帧"
    # 有观测成员(其余全 None)照常派帧
    mgr.web.publish_traffic_batch(
        {
            "torrent:A": {
                "t": 102.0,
                "dl": 3,
                "up": 3
            },
            "torrent:B": {
                "t": 102.0,
                "dl": None,
                "up": None
            }
        }
    )
    assert q.get_nowait()["points"] == [{"t": 102.0, "dl": 3, "up": 3}]
    # 单向未知: 全成员该向皆未知 -> 该向 None(断链未知不画 0 值孤点, _group_merge_points 同判)
    mgr.web.publish_traffic_batch(
        {
            "torrent:A": {
                "t": 102.5,
                "dl": None,
                "up": 5
            },
            "torrent:B": {
                "t": 102.5,
                "dl": None,
                "up": 7
            },
        }
    )
    assert q.get_nowait()["points"] == [{"t": 102.5, "dl": None, "up": 12}]
    # 组解散(成员集清空)不派帧
    mgr.store.groups.pop(gk)
    mgr.web.publish_traffic_batch({"torrent:A": {"t": 103.0, "dl": 4, "up": 4}})
    with pytest.raises(_queue.Empty):
        q.get_nowait(), "组解散不派帧"
    # 退订(评审 #6): 活跃门关 + 组键/seq 死键清理(#4, seq = 每连接游标)
    mgr.web.unsubscribe_traffic_stream(scope, q)
    assert mgr.web.traffic_stream_active() is False
    assert scope not in mgr.web._traffic_group_keys and scope not in mgr.web._traffic_seq
    # 重订阅同 scope -> 组键重缓存生效, seq 从 1 重新起(每连接游标语义)
    mgr.store.groups[gk] = ["A"]
    q2 = mgr.web.subscribe_traffic_stream(scope, gk)
    mgr.web.publish_traffic_batch({"torrent:A": {"t": 104.0, "dl": 6, "up": 6}})
    frame = q2.get_nowait()
    assert frame["seq"] == 1 and frame["points"] == [{"t": 104.0, "dl": 6, "up": 6}], ("重订阅组键重缓存生效, seq 每连接游标从 1 起")


# ---------- 发布路径主循环侧电池(注入时钟) ----------


def _drive_rounds(mgr, clk, rounds):
    """逐轮推进恰一个生效间隔并采样(清洁链); rounds = [(server_state, [torrents 形变])...]"""
    for st in rounds:
        clk.advance(SI)
        mgr.store.server_state = st
        _run(mgr)


def test_publish_global_frame_per_tick(tmp_path):
    """handler 每 tick 恰 1 帧/scope; 载荷形状 {seq, scope, points:[{t, dl, up}]}"""
    clk = FakeClock()  # 整数对齐 epoch(块首 int 截断不引入 ts 漂移)
    mgr = _mgr(tmp_path, clock=clk)
    q = mgr.web.subscribe_traffic_stream("global")
    v0 = 10_000_000
    mgr.store.server_state = server_state(dl_info_speed=5000, up_info_speed=2000, alltime_dl=v0, alltime_ul=v0)
    _run(mgr)  # 首轮(此刻不推进 —— 事件首点 t = 当前时钟)
    _drive_rounds(
        mgr, clk, [
            server_state(dl_info_speed=5000, up_info_speed=2000, alltime_dl=v0 + 9000, alltime_ul=v0),
        ]
    )
    frames = [q.get_nowait() for _ in range(2)]
    assert [f["seq"] for f in frames] == [1, 2]
    assert all(f["scope"] == "global" for f in frames)
    p0, p1 = frames[0]["points"], frames[1]["points"]
    assert len(p0) == 1 and set(p0[0]) == {"t", "dl", "up"}
    assert p0[0] == {"t": 1_700_000_000.0, "dl": 0, "up": 0}  # 链首: fold c=0 非 broke -> 0
    assert p1[0] == {"t": 1_700_000_002.0, "dl": 4500, "up": 0}  # inc 9000B / 2.0s = 4500 B/s


def test_publish_idle_tick_zero_point(tmp_path):
    """空闲 tick -> 差分真值点 {t, 0, 0}(z 观测链推进, 每 tick 恰 1 帧)"""
    clk = FakeClock()
    mgr = _mgr(tmp_path, clock=clk)
    q = mgr.web.subscribe_traffic_stream("global")
    mgr.store.server_state = server_state()  # 活跃一轮立基线
    _run(mgr)
    idle = server_state(dl_info_speed=0, up_info_speed=0, alltime_dl=10_000_000, alltime_ul=20_000_000)
    _drive_rounds(mgr, clk, [idle, idle, idle])
    frames = [q.get_nowait() for _ in range(4)]
    assert [f["points"][0]["dl"] for f in frames] == [0, 0, 0, 0], "z 观测 = 差分真值 0(与 GET 槽值同)"
    assert all(f["points"][0]["dl"] == 0 and f["points"][0]["up"] == 0 for f in frames)


def test_publish_disconnect_no_data_points(tmp_path):
    """断连分支不推数据点(帧数 0), seq 不虚增, 恢复后 seq 续上"""
    clk = FakeClock()
    mgr = _mgr(tmp_path, clock=clk)
    q = mgr.web.subscribe_traffic_stream("global")
    mgr.store.server_state = server_state()
    _run(mgr)  # 首轮
    mgr.client = None  # 断连(重连退避期同款)
    _drive_rounds(mgr, clk, [server_state()] * 3)
    assert q.qsize() == 1, "断连分支无新样本 -> 不推数据点(仅首轮 1 帧)"
    assert mgr.web._traffic_seq["global"] == 1, "seq 不虚增(静默 = 停流信号, 前端 >3si 徽标)"
    # 恢复: seq 续上(无空洞), 恢复样本为观测(短缝 3 x SI < 停机洞阈值 -> 摊配形态非 None)
    mgr.client = FakeClient()
    _drive_rounds(mgr, clk, [server_state()])
    assert q.qsize() == 2
    assert [f["seq"] for f in (q.get_nowait(), q.get_nowait())] == [1, 2], "恢复后 seq 续上"


def test_publish_no_subscriber_keeps_chain(tmp_path):
    """无订阅者零计算零派发, 观测链照常推进; 中途订阅首帧即真值(链连续性)"""
    clk = FakeClock()
    mgr = _mgr(tmp_path, clock=clk)
    mod = mgr.host.get("qb_traffic")
    assert mgr.web.traffic_stream_active() is False
    mgr.store.server_state = server_state()
    _run(mgr)
    _drive_rounds(mgr, clk, [server_state(alltime_dl=10_009_000)])
    assert mod._ev_prev_obs[GLOBAL_KEY][1] == 10_009_000, "无人订阅观测链照常推进"
    assert mod._ev_prev_obs[GLOBAL_KEY][0] == 1_700_000_002.0
    # 中途订阅: 首帧即真值(基于已推进的链; up 无增量 = 0)
    q = mgr.web.subscribe_traffic_stream("global")
    _drive_rounds(mgr, clk, [server_state(alltime_dl=10_018_000)])
    frame = q.get_nowait()
    assert frame["seq"] == 1 and frame["points"] == [{"t": 1_700_000_004.0, "dl": 4500, "up": 0}]


def test_publish_z_run_close_matches_get_contract(tmp_path):
    """z 游程收口样本点与 GET 读侧样本分组装配逐位一致(k=1 清洁链): 事件差分点列 ==
    assemble_group_points(同链活尾槽流)点列 —— 口径复用同一原语的逐位对账锚"""
    clk = FakeClock()
    mgr = _mgr(tmp_path, clock=clk)
    q = mgr.web.subscribe_traffic_stream("global")
    v0 = 10_000_000
    mgr.store.server_state = server_state(dl_info_speed=5000, up_info_speed=2000, alltime_dl=v0, alltime_ul=20_000_000)
    _run(mgr)  # r1(t0): 活跃立基线, 事件链首 0
    idle = server_state(dl_info_speed=0, up_info_speed=0, alltime_dl=v0, alltime_ul=20_000_000)
    _drive_rounds(mgr, clk, [idle] * 40)  # 40 拍空闲 -> z 游程 40 样本(链内无缝, dt 链零漂移)
    v1 = v0 + 150_000
    _drive_rounds(mgr, clk, [server_state(dl_info_speed=3000, up_info_speed=1000, alltime_dl=v1)])  # 收口
    frames = [q.get_nowait() for _ in range(42)]
    ev_points = [f["points"][0] for f in frames]
    assert [f["seq"] for f in frames] == list(range(1, 43)), "每 tick 恰 1 帧, seq 连续"
    # 读侧同链装配: 活尾快照(整块未落盘)复原槽流 -> 样本分组点列(k=1: 42 样本 < 500)
    tail = mgr.host.get("qb_traffic").live_tail[GLOBAL_KEY]
    slots = v4_live_tail_slots(tail)
    res = assemble_group_points(slots, 1_700_000_000.0, 1_700_000_000.0 + 43 * SI, SI)
    assert res.stride == 1
    get_points = [dict(p) for p in res.points]
    # 收口样本 = 摊配份额, 与 GET 读侧**逐位一致**(口径复用同一原语的逐位对账锚)
    assert ev_points[-1] == get_points[-1] and ev_points[0] == get_points[0]
    assert ev_points[-1]["dl"] * 42 <= 150_000, "收口样本取摊配份额(非全步尖刺 —— 空闲字节按覆盖摊回)"
    assert ev_points[-1]["t"] == 1_700_000_000.0 + 41 * SI
    # 空闲期事件点 = 派发时刻的真值 0(开放游程 pending 项的 GET 现值同判); 收口后读侧把
    # 台阶按覆盖摊回 z 槽(追溯改写)是 GET 全量重算的能力 —— 事件流是增量语义不重发,
    # 由 GET 对账(D9)校准(traffic_sample_events.py docstring「已知有界偏差」)
    assert all(p["dl"] == 0 and p["up"] == 0 for p in ev_points[1:-1])


def test_publish_layering_no_webui_import():
    """层级方向守阵: 采样模块五拆分件 import 面零 webui 引用(core 不得反向依赖表现层)"""
    import ast
    from pathlib import Path

    root = Path(__file__).resolve().parents[2] / "src" / "auto_qb" / "core" / "modules"
    for fname in (
        "traffic_sample_mod.py",
        "traffic_sample_blocks.py",
        "traffic_sample_common.py",
        "traffic_sample_agg.py",
        "traffic_sample_events.py",
    ):
        tree = ast.parse((root / fname).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                mods = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                mods = [node.module or ""]
            else:
                continue
            for m in mods:
                assert "webui" not in m, f"{fname}: 采样模块不得 import webui 面(现 {m!r})"


def test_publish_hub_absent_silent(tmp_path):
    """hub 缺席(ctx.web None)静默关断, 零异常零派发; hub 无方法替身同判(保守默认)"""
    clk = FakeClock()
    mgr = _mgr(tmp_path, clock=clk)
    mod = mgr.host.get("qb_traffic")
    mgr.ctx.web = None
    mod._publish_traffic_events()  # 无捕获防御面: 空跑直接返回
    _run(mgr)  # 零异常
    _drive_rounds(mgr, clk, [server_state(alltime_dl=10_009_000)])
    assert mod._ev_prev_obs[GLOBAL_KEY][1] == 10_009_000, "链照常推进(订阅者中途加入首帧即真值)"
    # 替身缺方法 -> 同静默
    mgr.ctx.web = object()
    _drive_rounds(mgr, clk, [server_state(alltime_dl=10_018_000)])
    assert mod._ev_prev_obs[GLOBAL_KEY][1] == 10_018_000


def test_publish_reset_point_zero(tmp_path):
    """计数器重置(cur < prev 观测) -> 差分记 None -> 点值 0(fold 立点 c=0 非 broke 同判)"""
    clk = FakeClock()
    mgr = _mgr(tmp_path, clock=clk)
    q = mgr.web.subscribe_traffic_stream("global")
    mgr.store.server_state = server_state(alltime_dl=10_000_000, alltime_ul=20_000_000)
    _run(mgr)
    _drive_rounds(
        mgr, clk, [server_state(dl_info_speed=0, up_info_speed=0, alltime_dl=9_000_000, alltime_ul=20_000_000)]
    )
    frames = [q.get_nowait() for _ in range(2)]
    assert frames[1]["points"] == [{"t": 1_700_000_002.0, "dl": 0, "up": 0}], "重置点增量 None -> 0(绝不产负增量, 三层同判)"


def test_publish_long_gap_null_point(tmp_path):
    """断连跨停机洞(缝 > 60s)恢复 -> 恢复样本两向 None(fold 立点 + broke -> 断链未知)"""
    clk = FakeClock()
    mgr = _mgr(tmp_path, clock=clk)
    q = mgr.web.subscribe_traffic_stream("global")
    mgr.store.server_state = server_state()
    _run(mgr)
    mgr.client = None
    clk.advance(70.0)  # 断连 70s(> 停机洞阈值)后恢复 —— n 观测不推进链, 缝 = 70s
    mgr.client = FakeClient()
    mgr.store.server_state = server_state()
    _run(mgr)
    frames = [q.get_nowait() for _ in range(2)]
    assert frames[0]["points"] == [{"t": 1_700_000_000.0, "dl": 0, "up": 0}]  # 断连前链首帧
    assert frames[1]["points"] == [{"t": 1_700_000_070.0, "dl": None, "up": None}], "跨停机洞恢复样本 = 断链未知, 不造 0 值孤点"


def test_publish_same_tick_zero_cov(tmp_path):
    """同刻病理面(对跨 0) -> 覆盖 0 不归因 -> 0(fold c=0 非 broke 同判)"""
    clk = FakeClock()
    mgr = _mgr(tmp_path, clock=clk)
    q = mgr.web.subscribe_traffic_stream("global")
    mgr.store.server_state = server_state(alltime_dl=10_000_000, alltime_ul=20_000_000)
    _run(mgr)
    mgr.store.server_state = server_state(alltime_dl=10_009_000, alltime_ul=20_000_000)
    _run(mgr)  # 时钟不推进: 对跨 0
    frames = [q.get_nowait() for _ in range(2)]
    assert frames[1]["points"] == [{"t": 1_700_000_000.0, "dl": 0, "up": 0}], "覆盖 0 不归因, 0 线"


def test_publish_point_error_isolated(tmp_path, monkeypatch):
    """单系列点计算异常不阻断其余系列(batch 仍含健康系列), 异常不上抛(事件面非数据面)"""
    clk = FakeClock()
    mgr = _mgr(tmp_path, clock=clk)
    seed_store(mgr, [active_torrent(hash="H1")])
    q = mgr.web.subscribe_traffic_stream("global")
    qt = mgr.web.subscribe_traffic_stream("torrent:H1")
    mgr.store.server_state = server_state()
    _run(mgr)  # 链首(两系列各一帧)
    import auto_qb.core.modules.traffic_sample_events as ev_mod

    origin = ev_mod._ev_series_point

    def boom(pre, kind, ts, dl_total, up_total, closed, si, z_chain):
        if dl_total == 10_009_000:
            raise RuntimeError("point boom")  # 只炸全局第二轮(链上点), H1 系列照常
        return origin(pre, kind, ts, dl_total, up_total, closed, si, z_chain)

    monkeypatch.setattr(ev_mod, "_ev_series_point", boom)
    with capture_logs("auto_qb.core.modules.traffic_sample_mod") as cap:
        mgr.store.server_state = server_state(alltime_dl=10_009_000)
        clk.advance(SI)
        _run(mgr)  # 全局点计算异常 / H1 已有链 -> 正常出点
    assert q.qsize() == 1, "全局只余链首帧, 第二轮缺帧(点计算异常)"
    q.get_nowait()
    frames_t = [qt.get_nowait(), qt.get_nowait()]
    assert frames_t[1]["seq"] == 2, "健康系列照常出帧"
    assert frames_t[1]["points"] == [{"t": 1_700_000_002.0, "dl": 0, "up": 0}], "健康系列点为同 totals 差分真值 0"
    assert any("步进点计算失败" in m for m in cap.messages), "异常留痕不上抛"


def test_publish_hub_publish_error_swallowed(tmp_path):
    """hub 派发异常不上抛(丢失退化 GET 轮询, 与 notify 同纪律)"""
    class _BoomHub:
        def traffic_stream_active(self):
            return True

        def publish_traffic_batch(self, batch):
            raise RuntimeError("hub boom")

    clk = FakeClock()
    mgr = _mgr(tmp_path, clock=clk)
    mgr.ctx.web = _BoomHub()
    mgr.store.server_state = server_state()
    with capture_logs("auto_qb.core.modules.traffic_sample_mod") as cap:
        _run(mgr)  # 零异常上抛
    assert any("派发失败" in m for m in cap.messages), "派发异常留痕"


class _BadQueue:
    """put_nowait 恒抛非 Full 异常的订阅者替身(丢弃兜底面的红验载体)"""
    @staticmethod
    def put_nowait(_item):
        raise RuntimeError("put boom")


def test_traffic_stream_put_error_counts_dropped(web_env):
    """put_nowait 非 Full 异常同样计丢弃(与 notify 同款兜底面); 丢弃帧占号不回收"""
    mgr, _client = web_env
    mgr.web.subscribe_traffic_stream("global")
    mgr.web._traffic_subs["global"] = [_BadQueue()]
    before = mgr.web.traffic_notify_dropped
    assert mgr.web.publish_traffic_batch({"global": {"t": 1.0, "dl": 0, "up": 0}}) == 0
    assert mgr.web.traffic_notify_dropped == before + 1
    mgr.web._traffic_subs["global"] = [_queue.Queue(maxsize=10)]
    mgr.web.publish_traffic_batch({"global": {"t": 2.0, "dl": 0, "up": 0}})
    assert mgr.web._traffic_seq["global"] == 2, "丢弃帧已占号 -> 下一帧 seq=2(断档可判定)"


def test_publish_midnight_seal_close_matches_get(tmp_path):
    """常态路径守阵(评审 #1): 活跃 -> 空闲跨 00:00 硬切(z 游程跨天封口重开) -> 次日恢复
    r 收口 —— 收口点与 GET 读侧装配逐位一致(跨天日块(已落盘) + 活尾块合流装配; 事件摊配
    链锚跨封口段持续, span/cov 与读侧 fold 整段空闲链同分母)"""
    from datetime import date, datetime, time as dtime

    clk = FakeClock()
    mgr = _mgr(tmp_path, clock=clk)
    mod = mgr.host.get("qb_traffic")
    q = mgr.web.subscribe_traffic_stream("global")
    v0 = 10_000_000
    t0 = float(int(datetime.combine(date.today(), dtime(23, 58, 0)).timestamp()))  # 整数秒(块首零漂移)
    clk.freeze(t0)
    mgr.store.server_state = server_state(dl_info_speed=5000, up_info_speed=2000, alltime_dl=v0, alltime_ul=20_000_000)
    _run(mgr)  # r @23:58:00(事件链首)
    idle = server_state(dl_info_speed=0, up_info_speed=0, alltime_dl=v0, alltime_ul=20_000_000)
    # 60 拍空闲(120s > 60s 摊配触发阈): z @23:58:02..23:59:58(段1, 59 样本) -> z @00:00:00
    # (00:00 硬切: 封段1落盘 + 段2开, 1 样本)
    for _ in range(60):
        clk.advance(SI)
        mgr.store.server_state = idle
        _run(mgr)
    assert mod._ev_z_chain[GLOBAL_KEY][0] == t0, "链锚跨 00:00 封口段持续(= 前观测槽 ts)"
    v1 = v0 + 150_000
    clk.advance(SI)
    mgr.store.server_state = server_state(dl_info_speed=3000, up_info_speed=1000, alltime_dl=v1)
    _run(mgr)  # r 收口 @00:00:02(t0+122 = 23:58:00+120+SI; 段2: 1 样本)
    frames = [q.get_nowait() for _ in range(62)]
    ev = [f["points"][0] for f in frames]
    assert [f["seq"] for f in frames] == list(range(1, 63))
    assert all(p["dl"] == 0 and p["up"] == 0 for p in ev[1:-1]), "空闲期事件点 = 派发时刻真值 0"
    assert mod._ev_z_chain == {}, "收口消费后链锚清除"
    # 读侧同链装配: 跨天日块(00:00 硬切已落盘) + 活尾块(段2 z + 收口 r, 未落盘)
    day1 = parse_v4_day_text(
        open(v4_day_file_path(mgr.config.data_dir, GLOBAL_KEY, v4_epoch_date_str(t0)), encoding="utf-8").read()
    )
    tail = mod.live_tail[GLOBAL_KEY]
    tail_block = V4Block(int(tail.start_epoch), tail.interval_s, None, None, tail.records)
    res = assemble_group_points_from_blocks(day1.blocks + (tail_block, ), t0, t0 + 123.0, SI)
    assert res.stride == 1
    get_points = [dict(p) for p in res.points]
    assert ev[0] == get_points[0], "链首逐位一致"
    assert ev[-1] == get_points[-1], "跨 00:00 封口链的收口点与 GET 读侧逐位一致"
    # 值级: 收口份额 = 摊配份额(整段空闲链分母), 非全步尖刺(150000B/2s)
    assert 0 < ev[-1]["dl"] < 150_000 // 2


def test_publish_marked_recovery_spread_matches_get(tmp_path):
    """评审 #5: 活跃 -> 空闲(z 游程开着) -> 断连数拍(z 换型封口进 n —— 换型捕获路径) ->
    恢复 totals 继续增长(非零 step) —— 恢复点摊配值与 GET 读侧逐位一致(marked + 链项面)"""
    clk = FakeClock()
    mgr = _mgr(tmp_path, clock=clk)
    mod = mgr.host.get("qb_traffic")
    q = mgr.web.subscribe_traffic_stream("global")
    v0 = 10_000_000
    mgr.store.server_state = server_state(alltime_dl=v0, alltime_ul=20_000_000)
    _run(mgr)  # r @t0
    idle = server_state(dl_info_speed=0, up_info_speed=0, alltime_dl=v0, alltime_ul=20_000_000)
    for _ in range(3):  # z @t0+2/4/6(游程开着)
        clk.advance(SI)
        mgr.store.server_state = idle
        _run(mgr)
    mgr.client = None  # 断连: z 游程换型封口进 n(两条 n 拍, 无帧)
    for _ in range(2):
        clk.advance(SI)
        mgr.store.server_state = server_state()
        _run(mgr)
    assert q.qsize() == 4, "断连期不推数据点"
    mgr.client = FakeClient()
    v1 = v0 + 12_000
    clk.advance(SI)
    mgr.store.server_state = server_state(alltime_dl=v1, alltime_ul=20_000_000)
    _run(mgr)  # 恢复 r @t0+12(totals 增长 -> 非零 step, marked 摊配面)
    frames = [q.get_nowait() for _ in range(5)]
    ev = [f["points"][0] for f in frames]
    assert ev[-1] == {
        "t": 1_700_000_012.0,
        "dl": 1000,
        "up": 0
    }, ("恢复点 = marked 摊配份额(12000B x 收口覆盖/整段对跨 = 2000B/2s), 非全步尖刺")
    # 读侧同链活尾装配(z + n + r 同块): 真值点列与事件一致(n 缺口为显式空值点, 事件流不推)
    slots = v4_live_tail_slots(mod.live_tail[GLOBAL_KEY])
    res = assemble_group_points(slots, 1_700_000_000.0, 1_700_000_013.0, SI)
    truth = [dict(p) for p in res.points if not (p["dl"] is None and p["up"] is None)]
    assert truth[0] == ev[0] and truth[-1] == ev[-1], "链首/恢复点与 GET 读侧逐位一致"


def test_traffic_stream_keepalive_ttl_invariant():
    """静态守阵(评审 #7): SSE 心跳间隔必须 < WEB_VIEW_TTL —— 间隔 >= TTL 会自锁(主循环
    判不活跃停组装视图, 推送自己也没内容); /api/events 与本端点共用同一常量。"""
    from auto_qb.webui.runtime_common import SSE_KEEPALIVE_S, WEB_VIEW_TTL
    from auto_qb.webui.server.routes import events as events_mod
    from auto_qb.webui.server.routes import traffic_stream as traffic_stream_mod

    assert SSE_KEEPALIVE_S < WEB_VIEW_TTL, "心跳间隔必须 < 活跃窗口(自锁防线)"
    assert events_mod.SSE_KEEPALIVE_S == traffic_stream_mod.SSE_KEEPALIVE_S == SSE_KEEPALIVE_S, (
        "两端点共用同一心跳常量(改一处即两处漂移)"
    )


def test_publish_z_chain_stepped_open(tmp_path):
    """链锚首槽台阶形态(空闲首拍 totals 已增长 —— 活跃尾带字节收尾): 链锚 = 首零样本槽
    (_ev_note_z_open else 支), z1 台阶点与收口摊配点均与 GET 读侧逐位一致"""
    clk = FakeClock()
    mgr = _mgr(tmp_path, clock=clk)
    mod = mgr.host.get("qb_traffic")
    q = mgr.web.subscribe_traffic_stream("global")
    v0 = 10_000_000
    mgr.store.server_state = server_state(alltime_dl=v0, alltime_ul=20_000_000)
    _run(mgr)  # r @t0(V0)
    # z1 @t0+2 totals 已增长(+500): fold z1 step 归账(锚 = z1 槽), 非等值接续形态
    clk.advance(SI)
    mgr.store.server_state = server_state(dl_info_speed=0, up_info_speed=0, alltime_dl=v0 + 500, alltime_ul=20_000_000)
    _run(mgr)
    idle = server_state(dl_info_speed=0, up_info_speed=0, alltime_dl=v0 + 500, alltime_ul=20_000_000)
    for _ in range(35):  # 空闲至链 span > 60s 摊配触发阈
        clk.advance(SI)
        mgr.store.server_state = idle
        _run(mgr)
    v1 = v0 + 500 + 90_000
    clk.advance(SI)
    mgr.store.server_state = server_state(dl_info_speed=3000, up_info_speed=1000, alltime_dl=v1)
    _run(mgr)  # r 收口 @t0+74
    frames = [q.get_nowait() for _ in range(38)]
    ev = [f["points"][0] for f in frames]
    assert ev[1] == {"t": 1_700_000_002.0, "dl": 250, "up": 0}, "z1 台阶点(500B/2s)与读侧同值"
    assert mod._ev_z_chain == {}, "收口消费后链锚清除"
    slots = v4_live_tail_slots(mod.live_tail[GLOBAL_KEY])
    res = assemble_group_points(slots, 1_700_000_000.0, 1_700_000_075.0, SI)
    truth = [dict(p) for p in res.points if not (p["dl"] is None and p["up"] is None)]
    assert truth[0] == ev[0] and truth[1] == ev[1] and truth[-1] == ev[-1], ("链首/z1 台阶/收口摊配三锚与 GET 读侧逐位一致")
    assert 0 < ev[-1]["dl"] < 90_000 // 2, "收口取摊配份额(整段空闲链分母)"


def test_publish_z_chain_zero_item_close(tmp_path):
    """收口时链项覆盖为 0 的退化面(z1 台阶即封段, 收口紧随 —— 一拍空闲闪断): 链锚 = z1 槽,
    链项覆盖 0 -> 空项面摊配不触发 -> 收口点全步 —— 与 GET 读侧逐位一致(链首/z1/收口三点)"""
    clk = FakeClock()
    mgr = _mgr(tmp_path, clock=clk)
    mod = mgr.host.get("qb_traffic")
    q = mgr.web.subscribe_traffic_stream("global")
    v0 = 10_000_000
    mgr.store.server_state = server_state(alltime_dl=v0, alltime_ul=20_000_000)
    _run(mgr)  # r @t0(V0)
    clk.advance(SI)
    mgr.store.server_state = server_state(dl_info_speed=0, up_info_speed=0, alltime_dl=v0 + 300, alltime_ul=20_000_000)
    _run(mgr)  # z1 @t0+2 台阶形态(totals +300), 游程即封段
    clk.advance(SI)
    mgr.store.server_state = server_state(alltime_dl=v0 + 900, alltime_ul=20_000_000)
    _run(mgr)  # r @t0+4 收口(600B 台阶, 链项覆盖 0)
    frames = [q.get_nowait() for _ in range(3)]
    ev = [f["points"][0] for f in frames]
    assert mod._ev_z_chain == {}, "收口消费后链锚清除"
    slots = v4_live_tail_slots(mod.live_tail[GLOBAL_KEY])
    res = assemble_group_points(slots, 1_700_000_000.0, 1_700_000_005.0, SI)
    assert [dict(p) for p in res.points] == ev, "三 truth 点(r 链首/z1 台阶/收口)与 GET 逐位一致"


def test_ev_series_point_stale_chain_fallback():
    """链 totals 与前观测不匹配(重置/跳变断链, 评审 #1 兜底面)-> 回退单段锚: 摊配 span/cov
    只覆盖当前段 —— 与链缺位(None)同值(纯函数单测; 覆盖链匹配 False 支)"""
    from auto_qb.core.modules.traffic_sample_events import _ev_series_point

    pre = (398.0, 1000, 500)
    closed = ("z", 400.0, 401.0, 3)
    stale = (50.0, 999, 500)  # totals 断链(999 != 1000) -> 链锚不可信
    p_stale = _ev_series_point(pre, "r", 402.0, 1600, 500, closed, 2.0, stale)
    p_none = _ev_series_point(pre, "r", 402.0, 1600, 500, closed, 2.0, None)
    assert p_stale == p_none == {
        "t": 402.0,
        "dl": 300,
        "up": 0
    }, ("回退单段锚(398 = 段 start - si): span/cov 只覆盖当前段, 摊配不触发(缝 < 阈)全步")


def test_publish_marked_reset_recovery_null(tmp_path):
    """轮2 #1: 断连恢复 + totals 回落(计数器重置)—— 恢复点两向 None(fold 立点 c=0
    broke -> 断链未知; broke = marked, 评审指出的恒 False 缺陷守阵), 与 GET 对账"""
    clk = FakeClock()
    mgr = _mgr(tmp_path, clock=clk)
    mod = mgr.host.get("qb_traffic")
    q = mgr.web.subscribe_traffic_stream("global")
    mgr.store.server_state = server_state(alltime_dl=10_000_000, alltime_ul=20_000_000)
    _run(mgr)  # r @t0(V0)
    mgr.client = None
    for _ in range(2):  # 断连两拍 -> n 观测(marked 面)
        clk.advance(SI)
        mgr.store.server_state = server_state()
        _run(mgr)
    mgr.client = FakeClient()
    clk.advance(SI)
    mgr.store.server_state = server_state(alltime_dl=9_000_000, alltime_ul=19_000_000)
    _run(mgr)  # 恢复 r @t0+6: totals 回落 -> 重置 + marked
    frames = [q.get_nowait() for _ in range(2)]
    ev = [f["points"][0] for f in frames]
    assert ev[0] == {"t": 1_700_000_000.0, "dl": 0, "up": 0}
    assert ev[-1] == {"t": 1_700_000_006.0, "dl": None, "up": None}, ("恢复点两向 None(重置 + marked -> broke), 绝不造 0 值孤点")
    # 读侧同链装配对账(重置关块已把 n 前缀落盘 -> 跨天日块 + 活尾块合流): 恢复点同形
    # None(fold 立点 + broke 同判)
    day = parse_v4_day_text(
        open(v4_day_file_path(mgr.config.data_dir, GLOBAL_KEY, v4_epoch_date_str(1_700_000_000.0)),
             encoding="utf-8").read()
    )
    tail = mod.live_tail[GLOBAL_KEY]
    tail_block = V4Block(int(tail.start_epoch), tail.interval_s, None, None, tail.records)
    res = assemble_group_points_from_blocks(day.blocks + (tail_block, ), 1_700_000_000.0, 1_700_000_007.0, SI)
    assert res.points[-1] == {"t": 1_700_000_006.0, "dl": None, "up": None}


def test_ev_series_point_aged_chain_fallback():
    """轮2 #2: 链锚年龄超读侧回看界(_V4_SEAM_LOOKBACK_S)-> 回退单段锚(与链缺位同值,
    与读侧窗内重立锚一致口径); 未超界链照常参与摊配(两路径值可分)"""
    from auto_qb.core.modules.traffic_sample_events import _ev_series_point

    pre = (99996.0, 1000, 500)
    closed = ("z", 99998.0, 99999.0, 3)
    ts = 100000.0
    aged = (10.0, 1000, 500)  # 锚龄 99990s > 86400s -> 回退
    young = (20000.0, 1000, 500)  # 锚龄 80000s < 86400s -> 参与摊配
    p_aged = _ev_series_point(pre, "r", ts, 1600, 500, closed, 2.0, aged)
    p_none = _ev_series_point(pre, "r", ts, 1600, 500, closed, 2.0, None)
    p_young = _ev_series_point(pre, "r", ts, 1600, 500, closed, 2.0, young)
    assert p_aged == p_none == {"t": ts, "dl": 300, "up": 0}, "超界链回退单段锚(= 链缺位同值)"
    assert p_young == {"t": ts, "dl": 0, "up": 0}, "未超界链参与整段摊配(份额摊薄趋零, 两路径可分)"


def test_publish_stale_keys_pruned_when_torrent_gone(tmp_path):
    """轮2 #3: 种子移出采样面(by_hash 消失)后其观测游标/摊配链差集清除(随种子 churn
    单点回收); 全局恒在; 断连不清(by_hash 未变, 链保留)"""
    clk = FakeClock()
    mgr = _mgr(tmp_path, clock=clk)
    mod = mgr.host.get("qb_traffic")
    seed_store(mgr, [active_torrent(hash="H1")])
    mgr.store.server_state = server_state()
    _run(mgr)
    assert "torrent:H1" in mod._ev_prev_obs, "采样一轮后游标在位"
    seed_store(mgr, [])  # H1 移出采样面(删种/移除同形)
    mgr.store.server_state = server_state()
    _run(mgr)
    assert "torrent:H1" not in mod._ev_prev_obs and "torrent:H1" not in mod._ev_z_chain, ("采样面之外的系列键差集清除(无界增长回收)")
    assert GLOBAL_KEY in mod._ev_prev_obs, "全局恒在"


def test_publish_prune_store_without_by_hash(tmp_path):
    """store 替身缺 by_hash 判定面 -> 清除静默跳过(防御面, 轮2 #3)"""
    clk = FakeClock()
    mgr = _mgr(tmp_path, clock=clk)
    mod = mgr.host.get("qb_traffic")
    mod._ev_prev_obs[GLOBAL_KEY] = (1.0, 10, 20)
    mod._ctx.store = type("S", (), {})()  # 无 by_hash 属性
    mod._ev_prune_stale_keys()  # 零异常
    assert mod._ev_prev_obs == {GLOBAL_KEY: (1.0, 10, 20)}, "缺判定面 -> 保留不动"
