"""WEB UI 后端(包): FastAPI 应用工厂(只读快照 + 命令投递, 不直接触碰主循环状态)

线程模型: uvicorn 在独立线程运行; 本包的所有请求处理器只做两件事——
1) 读取 manager 暴露的只读快照(_group_view/status_snapshot, 主循环每 tick 原子替换);
2) 向 manager.web_commands 投递控制命令(由主循环线程消费执行, 写操作只在主循环线程)。

鉴权: 所有 /api/* 请求校验 Bearer 密钥; 密钥来自 config.web.token, 留空则随机生成并
持久化到 <data_dir>/web.token(0600), 启动日志打印一次。默认仅监听 127.0.0.1。

由 web.py 拆分而来（plan 26-09-22-1857）： factory=create_app 组装壳 / auth=鉴权单点 /
context=路由共享件 / common=纯工具 / lifecycle=uvicorn 启停 / static_ui=静态挂载 /
routes/=按域 APIRouter。2026-09-22 方案 C W1 整体平移为 webui/server/（plan 26-09-22-2112），
对外导入点统一走 auto_qb.webui 门面；包内上游引用随包深 +1 层（..→... / ...→....）。

❗日志命名空间(K3): 本包**所有子模块**一律显式 ``logging.getLogger("auto_qb.web")``,
  不用 __name__ —— tests/test_web.py 多处按 ``r.name == "auto_qb.web"`` 断言 caplog
  记录, 子模块 logger 名漂移(auto_qb.web.auth 等)必红。
"""
from .common import content_disposition, ensure_web_token
from .factory import create_app
from .lifecycle import (
    WEB_START_TIMEOUT,
    WEB_STOP_TIMEOUT,
    WebServerHandle,
    start_web_server,
    stop_web_server,
)

__all__ = [
    "WEB_START_TIMEOUT",
    "WEB_STOP_TIMEOUT",
    "WebServerHandle",
    "content_disposition",
    "create_app",
    "ensure_web_token",
    "start_web_server",
    "stop_web_server",
]
