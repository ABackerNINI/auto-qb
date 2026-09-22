"""辅种组命令路由: /api/groups/{key}/pause|resume|reannounce|delete.

端点体逐字平移(plan 26-09-22-1857 W3); 仅 @app.* → @router.* 与共享件别名(原闭包名不变)。
鉴权由 factory 的全局 dependencies 单点覆盖, 本模块不另挂依赖。
日志命名空间见包 __init__(K3)。"""

from ..common import group_key_param as _group_key_param

from fastapi import APIRouter
from ..context import WebContext


def build_router(ctx: WebContext) -> APIRouter:
    _enqueue = ctx.enqueue
    router = APIRouter()

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
