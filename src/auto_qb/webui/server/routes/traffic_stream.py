"""流量步进 SSE 专用通道: GET /api/traffic/qb/stream(plan 26-11-18-0037 阶段 2, §03 (2))

传输面硬切(D7): 轮询 -> SSE 推送, 毫秒级管线。专用端点不扩全局 /api/events 枢纽(E1):
per-scope 订阅生命周期在订阅时定死, 只推本 scope 的差分小真值({seq, scope, points}),
绝不推全量状态。复用既有 SSE 纪律(events.py 形态): 票据 ?ticket= 一次性换流(EventSource
发不出 Authorization 头, 签发面共用 POST /api/events/ticket 同一池 —— 单次消费 + TTL +
满额 503 退轮询兜底, 见 auth._TICKET_STREAM_PATHS)、心跳保活(间隔必须 < WEB_VIEW_TTL,
自锁防线)、X-Accel-Buffering: no(反代不缓冲)、finally 退订(生成器异常死亡也退)。

scope 语法 = "global" | "torrent:<hash>" | "group:<key>"(与 /api/traffic/qb 三 GET 端点
同语法): torrent 哈希非法 400(同 payload_torrent 的 v4_series_dir 校验)、组标识畸形 400
(同 /api/groups/{key} 通道)、其它形态 400 —— 票据无效/缺参由全局鉴权闸 401(fail-fast
4xx)。scope 与订阅队列的绑定面在 StreamMixin.subscribe_traffic_stream。

断连/停流语义(如实设计): 采样断连分支无新样本 -> 不推数据点(帧只在有真值点时派发,
seq 不虚增)—— 前端按静默(>3 x si)起「滞后」徽标并 GET 重拉, 显式空值点由 GET 契约
承载(§01 验收 4)。日志命名空间见包 __init__(K3)。
"""

import json
import queue

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ...runtime import SSE_KEEPALIVE_S
from ..common import group_key_param
from ....core.traffic_store import v4_series_dir
from ..context import WebContext


def _parse_scope(manager, scope: str) -> tuple:
    """scope 查询参数校验(非法 4xx, 客户端错误不 500): 返回 (scope 原串, 组解码键|None)

    - "global" 恒合法(全局系列恒采);
    - "torrent:<hash>": 哈希合法性走读侧同判(v4_series_dir 的路径纯计算, ValueError
      -> 400「种子哈希非法」, 与 GET /api/traffic/qb/torrent/{hash} 同口径);
    - "group:<key>": 解码走 group_key_param(畸形 400, 与 /api/groups/{key} 通道同判),
      解码键(tuple)随订阅缓存, 成员集每帧现查 store.groups;
    - 其余形态(空串/未知前缀/裸 hash)一律 400。
    """
    text = (scope or "").strip()
    if text == "global":
        return text, None
    if text.startswith("torrent:"):
        try:
            v4_series_dir(manager.config.data_dir, text)
        except ValueError:
            raise HTTPException(status_code=400, detail="种子哈希非法") from None
        return text, None
    if text.startswith("group:"):
        return text, group_key_param(text[len("group:"):])
    raise HTTPException(status_code=400, detail="scope 须为 global|torrent:<hash>|group:<key>")


def build_router(ctx: WebContext) -> APIRouter:
    manager = ctx.manager
    router = APIRouter()

    @router.get("/api/traffic/qb/stream")
    def api_traffic_qb_stream(scope: str):
        """流量步进 SSE 事件流(§03 (2), D7/E1): per-scope 差分小真值推送

        载荷帧 = {seq, scope, points:[{t, dl, up}]}(event: traffic): points = 本 tick
        该 scope 的聚合显示点(全局/单种 = 系列差分点; 组 = 成员 Σ, _group_merge_points
        口径), per-tick 样本粒度真值(对计划 §03(2) k>1「尾组更新点+组闭合时新组点」措辞的
        有意偏离, 增量语义: 摊回份额/漂移由 GET 对账校准) —— 前端不按 stride 折组: 事件
        样本点直显为尾点, 组粒度归位 = 30s 对账 GET + seq 断档重拉; meta.stride 仅契约
        标注, 前端不消费。seq 每 scope 单调递增(队列满丢弃留断档, 消费端据此重拉 +
        低频 GET 对账, D9)。票据: ?ticket= 一次性短时票据(POST /api/events/ticket 换取,
        满额 503 ->
        前端退 GET 轮询兜底, E7), 无效/缺参 401(全局鉴权闸 _TICKET_STREAM_PATHS,
        fail-fast 4xx); scope 缺参/非法 422/400。WARN: 经反代时已带 X-Accel-Buffering:
        no(SSE 逐帧到, 不缓冲)。
        """
        scope_text, group_key = _parse_scope(manager, scope)
        q = manager.web.subscribe_traffic_stream(scope_text, group_key)

        def frame(etype, data):
            """SSE 帧: `event: <type>\\ndata: <json>\\n\\n`(空行结束; events.py 同款)"""
            return "event: " + str(etype) + "\ndata: " + json.dumps(data, ensure_ascii=False) + "\n\n"

        def gen():
            try:
                yield frame("hello", {"ok": True, "scope": scope_text})
                while True:
                    try:
                        ev = q.get(timeout=SSE_KEEPALIVE_S)
                    except queue.Empty:
                        # 心跳: 保活(防代理/浏览器掐连接)+ 把客户端标记为活跃
                        # (间隔必须 < WEB_VIEW_TTL, 否则主循环停止组装视图 -> 自锁)
                        manager.web.touch()
                        yield ": keepalive\n\n"
                        continue
                    manager.web.touch()
                    yield frame("traffic", ev)
            except GeneratorExit:
                pass
            finally:
                manager.web.unsubscribe_traffic_stream(scope_text, q)

        return StreamingResponse(
            gen(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    return router
