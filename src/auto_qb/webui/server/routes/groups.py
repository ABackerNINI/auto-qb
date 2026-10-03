"""辅种组命令路由: /api/groups/{key}/pause|resume|reannounce|delete + /api/traffic/qb/group/{key}.

端点体逐字平移(plan 26-09-22-1857 W3); 仅 @app.* → @router.* 与共享件别名(原闭包名不变)。
鉴权由 factory 的全局 dependencies 单点覆盖, 本模块不另挂依赖。
日志命名空间见包 __init__(K3)。"""

from fastapi.responses import JSONResponse

from ..common import group_key_param as _group_key_param
from ..traffic_qb import QbTrafficChartApi as _QbTrafficChartApi

from fastapi import APIRouter
from ..context import WebContext


def build_router(ctx: WebContext) -> APIRouter:
    manager = ctx.manager
    _enqueue = ctx.enqueue
    _qb_traffic = _QbTrafficChartApi(manager)
    router = APIRouter()

    @router.get("/api/traffic/qb/group/{key}")
    def api_traffic_qb_group(key: str, window: str = "24h"):
        """分组 qB 口径流量时序(plan 26-10-03-0946 §08 + §04.1, P4): 组不落盘, 读侧现算

        key 收当前指纹 base64url(同 /api/groups/{key} 通道, 畸形 400); 成员集 = 查询时刻
        store.groups[指纹键](与分组视图/弹层同源同刻, §04.1-①), 聚合 Σ 成员单种 dat 现算
        (装配单点在 server/traffic_qb.py; 纯函数口径在 core/traffic_grid.py)。
        """
        manager.web.touch()
        return JSONResponse(content=_qb_traffic.payload_group(key, window))

    @router.post("/api/groups/{key}/pause")
    def api_pause(key: str):
        return _enqueue("pause_group", {"key": _group_key_param(key)})

    @router.post("/api/groups/{key}/resume")
    def api_resume(key: str):
        return _enqueue("resume_group", {"key": _group_key_param(key)})

    @router.post("/api/groups/{key}/reannounce")
    def api_reannounce(key: str):
        return _enqueue("reannounce_group", {"key": _group_key_param(key)})

    @router.post("/api/groups/{key}/delete")
    def api_delete(key: str, body: dict = None):
        delete_files = bool((body or {}).get("delete_files", False))
        result = _enqueue("delete_group", {"key": _group_key_param(key), "delete_files": delete_files})
        result["delete_files"] = delete_files
        return result

    return router
