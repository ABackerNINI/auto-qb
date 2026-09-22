"""SSE 事件流路由: /api/events(P2 事件驱动).

端点体逐字平移(plan 26-09-22-1857 W2); 仅 @app.* → @router.* 与共享件别名(原闭包名不变)。
鉴权由 factory 的全局 dependencies 单点覆盖, 本模块不另挂依赖。
日志命名空间见包 __init__(K3)。"""

import json
import queue
from fastapi.responses import StreamingResponse

from ...web_runtime import SSE_KEEPALIVE_S

from fastapi import APIRouter
from ..context import WebContext


def build_router(ctx: WebContext) -> APIRouter:
    manager = ctx.manager
    router = APIRouter()

    @router.get("/api/events")
    def api_events():
        """SSE 事件流(P2 事件驱动): 命令回执 / 视图版本变更**主动推**, 前端据此撤下与刷新

        替代什么: ① 前端对 `/api/cmd/{id}` 的退避轮询(0→150→300→500ms 粒度);
                  ② 对 `/api/state` 的定时轮询触发(1.5/2/3s 分档)。
        ❗只推**信号与小真值**, 绝不推全量状态 —— 3000 种子一轮全量要 63ms(序列化+网络+
          JSON.parse), 频繁推会把主线程打满(本项目踩过同类坑: 搜索索引阻塞主循环)。

        ⚠ 两个前端侧注意: EventSource 发不出 Authorization 头(密钥走 ?token=, 见 require_token);
          经过反代时要关掉响应缓冲(已带 X-Accel-Buffering: no)。
        """
        q = manager.web.subscribe()

        def frame(etype, data):
            """SSE 帧: `event: <type>\\ndata: <json>\\n\\n`(空行结束)"""
            return "event: " + str(etype) + "\ndata: " + json.dumps(data, ensure_ascii=False) + "\n\n"

        def gen():
            try:
                yield frame("hello", {"ok": True})
                while True:
                    try:
                        ev = q.get(timeout=SSE_KEEPALIVE_S)
                    except queue.Empty:
                        # 心跳: 一是保活(防代理/浏览器掐连接), 二是把客户端标记为活跃
                        # (间隔必须 < WEB_VIEW_TTL, 否则主循环停止组装视图 ⇒ 自锁)
                        manager.touch_web_client()
                        yield ": keepalive\n\n"
                        continue
                    manager.touch_web_client()
                    yield frame(ev.get("type") or "msg", ev.get("payload") or {})
            except GeneratorExit:
                pass
            finally:
                manager.web.unsubscribe(q)

        return StreamingResponse(
            gen(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            },
        )

    return router
