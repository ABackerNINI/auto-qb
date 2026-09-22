"""create_app: FastAPI 应用工厂 —— 纯组装壳(plan 26-09-22-1857 拆分完成).

装配顺序: 鉴权依赖(auth.make_require_token, 全局 dependencies 单点) → FastAPI 实例 →
按域 Router(routes.ROUTE_BUILDERS 固定顺序) → 静态挂载(static_ui.mount_static_ui,
必须在全部 /api 路由之后 —— mount "/" 是兑底路由)。
端点定义一律在 routes/ 各模块; 本文件禁止内联路由(守阵 test_create_app_is_thin_assembly)。
"""
from fastapi import Depends, FastAPI
from .auth import make_require_token
from .context import WebContext
from .routes import ROUTE_BUILDERS
from .static_ui import mount_static_ui


def create_app(manager) -> FastAPI:
    """构建 WEB 应用: 只读快照 + 命令投递 + 设置读写, 全部 /api/* 经 Bearer 密钥鉴权"""

    require_token = make_require_token(manager)

    app = FastAPI(
        title="auto-qb",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        dependencies=[Depends(require_token)],
    )
    ctx = WebContext(manager)

    for _build in ROUTE_BUILDERS:
        app.include_router(_build(ctx))

    mount_static_ui(app)
    return app
