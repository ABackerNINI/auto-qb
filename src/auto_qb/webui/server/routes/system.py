"""系统诊断路由: /api/log · /api/cmd/{cmd_id}.

端点体逐字平移(plan 26-09-22-1857 W2); 仅 @app.* → @router.* 与共享件别名(原闭包名不变)。
鉴权由 factory 的全局 dependencies 单点覆盖, 本模块不另挂依赖。
日志命名空间见包 __init__(K3)。"""

import os
from typing import List

from fastapi import APIRouter
from ..context import WebContext


def build_router(ctx: WebContext) -> APIRouter:
    manager = ctx.manager
    router = APIRouter()

    @router.get("/api/log")
    def api_log(lines: int = 200, level: str = ""):
        """auto-qb 自身日志 tail(只读; qB 日志不在范围)。level 按 [LEVEL] 标记过滤;
        日志文件未配置/不存在时返回空列表(前端空态)。"""
        manager.touch_web_client()
        path = getattr(manager.config.logging, "file", "") or ""
        out: List[str] = []
        if path and os.path.isfile(path):
            n = max(10, min(int(lines or 200), 2000))
            with open(path, "rb") as f:
                raw = f.read()[-256 * 1024:]
            all_lines = [ln for ln in raw.decode("utf-8", errors="replace").splitlines() if ln.strip()]
            lv = (level or "").strip().upper()
            if lv:
                all_lines = [ln for ln in all_lines if f"[{lv}" in ln]
            out = all_lines[-n:]
        return {"lines": out, "file": path}

    @router.get("/api/cmd/{cmd_id}")
    def api_cmd_result(cmd_id: str):
        """命令执行结果查询(前端投递后轮询): pending = 主循环尚未执行完或仍在确认中

        reannounce 的回执由主循环的 tracker 确认跟踪器在确认成功/失败/超时后写入,
        其余命令执行完立即写入。结果只由主循环线程写, 此处只读。
        """
        manager.touch_web_client()
        result = manager._web_results.get(cmd_id)
        return dict(result) if result else {"status": "pending"}

    return router
