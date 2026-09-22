"""静态前端挂载: UI 重定向 + StaticFiles 根挂载 + no-cache 中间件(整段平移).

必须在 create_app 全部 /api 路由注册之后调用(mount \"/\" 是兜底路由)。
"""
import os

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles


def mount_static_ui(app: FastAPI) -> None:
    # 静态前端(UI 目录化: atlas=星图(旧) / prism=棱镜(新) / shared=公共逻辑层; 目录即 URL,
    # 新增 UI = static/<名字>/ 一个目录, 无需后端改动)
    static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web_ui", "static")
    if os.path.isdir(static_dir):

        @app.get("/", include_in_schema=False)
        async def _ui_root() -> RedirectResponse:
            """根路径进默认 UI(星图): StaticFiles 根下已无 index.html, 由重定向兜底。"""
            return RedirectResponse("/atlas/", status_code=307)

        @app.get("/newui", include_in_schema=False)
        @app.get("/newui/{rest:path}", include_in_schema=False)
        async def _newui_legacy(rest: str = "") -> RedirectResponse:
            """旧 /newui/* 书签兼容: 307 到 /prism/*(观察一轮后可撤)。"""
            return RedirectResponse(f"/prism/{rest}", status_code=307)

        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

        @app.middleware("http")
        async def _static_no_cache(request, call_next):
            """静态资源禁用启发式缓存(不加 Cache-Control 时浏览器会自行缓存数小时)

            症状: 升级程序后仍加载旧 app.js/style.css, 界面“改了但没变”。
            用 no-cache(仍允许存储, 但每次必须带 ETag 重新校验): 未变更走 304, 变更为新内容。
            仅作用于非 /api 响应, 不影响接口语义。
            """
            response = await call_next(request)
            if not request.url.path.startswith("/api"):
                response.headers["Cache-Control"] = "no-cache"
            return response
