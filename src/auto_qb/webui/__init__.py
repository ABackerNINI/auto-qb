"""WEB UI 表现层包（门面）: runtime（表现层门面）+ server/（HTTP 层）+ static/（前端资产）

由 web/ 包 + web_ui/ + web_runtime.py 归拢而来（plan 26-09-22-2112 · 方案 C · W1）:
- 对外导入点统一为本包: ``from auto_qb.webui import create_app / start_web_server / WebUIRuntime ...``
- runtime.py 在 W1 前是根模块 web_runtime.py; views.py / commands.py 在 W3 由
  mixins/web_view.py 与 mixins/web_commands.py 迁入（WebviewMixin / WebCommandsMixin）,
  本包集齐 WEB 表现层全部 Python 代码（runtime + 构建器 + 命令处理器 + server + static）。
- server/ 整体平移自 web/ 包（plan 26-09-22-1857 拆分结构不变: factory=组装壳 / auth=鉴权单点 /
  context=路由共享件 / common=纯工具 / lifecycle=uvicorn 启停 / static_ui=静态挂载 / routes/=按域 APIRouter）。

❗日志命名空间冻结（K3）: server 包内**所有子模块**一律显式 ``logging.getLogger("auto_qb.web")``,
  不用 __name__ —— tests/test_web.py 多处按 ``r.name == "auto_qb.web"`` 断言 caplog 记录,
  包目录改名不改 logger 名, 子模块 logger 名漂移必红。
"""
from .commands import WebCommandsMixin
from .runtime import WebUIRuntime
from .server import (
    WEB_START_TIMEOUT,
    WEB_STOP_TIMEOUT,
    WebServerHandle,
    content_disposition,
    create_app,
    ensure_web_token,
    start_web_server,
    stop_web_server,
)
from .views import WebviewMixin

__all__ = [
    "WEB_START_TIMEOUT",
    "WEB_STOP_TIMEOUT",
    "WebCommandsMixin",
    "WebServerHandle",
    "WebUIRuntime",
    "WebviewMixin",
    "content_disposition",
    "create_app",
    "ensure_web_token",
    "start_web_server",
    "stop_web_server",
]
