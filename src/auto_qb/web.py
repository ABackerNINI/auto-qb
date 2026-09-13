"""WEB UI 后端: FastAPI 应用工厂(只读快照 + 命令投递, 不直接触碰主循环状态)

线程模型: uvicorn 在独立线程运行; 本模块的所有请求处理器只做两件事——
1) 读取 manager 暴露的只读快照(_group_view/status_snapshot, 主循环每 tick 原子替换);
2) 向 manager.web_commands 投递控制命令(由主循环线程消费执行, 写操作只在主循环线程)。

鉴权: 所有 /api/* 请求校验 Bearer 密钥; 密钥来自 config.web.token, 留空则随机生成并
持久化到 <data_dir>/web.token(0600), 启动日志打印一次。默认仅监听 127.0.0.1。
"""
import logging
import os
import secrets
import threading
import time
from typing import Optional

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.staticfiles import StaticFiles

from .utils import decode_group_key

logger = logging.getLogger(__name__)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "web_ui", "static")

# 热重载重启服务器的时间预算: uvicorn 的 should_exit 只是"请求退出"(主循环每 0.1s 才读一次,
# 之后才关闭监听套接字), 不等旧线程退出就启新服务会撞 Errno 10048 —— 见 stop_web_server。
WEB_STOP_TIMEOUT = 5.0
WEB_START_TIMEOUT = 5.0


def _app_version() -> str:
    """包版本号(供前端顶栏展示)。

    必须函数内延迟导入: `auto_qb/__init__.py` 先 `from .qbmanager import QbManager` 再赋值
    `__version__`, 模块顶层导入版本号会在包初始化未完成时抛 ImportError。
    """
    from . import __version__
    return __version__


def ensure_web_token(manager) -> str:
    """确定 WEB 访问密钥: 显式配置优先; 否则随机生成并持久化到 data_dir/web.token(0600)"""
    if manager.config.web.token:
        return manager.config.web.token
    token_file = os.path.join(os.path.dirname(manager.state_file) or ".", "web.token")
    if os.path.exists(token_file):
        with open(token_file, "r", encoding="ascii") as f:
            token = f.read().strip()
        if token:
            return token
    token = secrets.token_hex(32)
    fd = os.open(token_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="ascii") as f:
        f.write(token)
    logger.info(f"WEB 访问密钥已生成: {token_file}(下方启动日志亦打印一次)")
    logger.warning(f"WEB UI 访问密钥: {token}")
    return token


def create_app(manager) -> FastAPI:
    """构建 WEB 应用: 只读快照 + 命令投递 + 设置读写, 全部 /api/* 经 Bearer 密钥鉴权"""
    def require_token(authorization: str = Header(default="")) -> None:
        # 缺省/畸形凭证(无头、scheme 错误、空 token)静默 401: 属客户端常态(登录框空提交、
        # 轮询竞态、端口探测), 记 WARNING 会经 notify 推送扰民(历史上前端空 token 请求被
        # HTTP 头 OWS 裁剪成裸 "Bearer", 曾持续误报); 仅"携带了但错误"的密钥记一条不含密钥
        # 内容的 WARNING, 保留真实错密钥/探测信号。比较走 compare_digest 防时序侧信道。
        scheme = "Bearer "
        if not authorization.startswith(scheme):
            raise HTTPException(status_code=401, detail="invalid token")
        token = authorization[len(scheme):].strip()
        if not token:
            raise HTTPException(status_code=401, detail="invalid token")
        if not secrets.compare_digest(token, manager._web_token):
            logger.warning("WEB 鉴权失败: 密钥不匹配")
            raise HTTPException(status_code=401, detail="invalid token")

    app = FastAPI(
        title="auto-qb",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        dependencies=[Depends(require_token)],
    )

    def _enqueue(cmd: str, payload: dict) -> None:
        manager.web_commands.put((cmd, payload))

    @app.get("/api/status")
    def api_status():
        manager.touch_web_client()
        snap = manager.status_snapshot()
        return {
            "connected": snap["connected"],
            "paused": snap["paused"],
            "torrents": snap["torrents"],
            "groups": len(manager._group_view),
            "version": _app_version(),
            "traffic": manager._traffic_view,
        }

    @app.get("/api/state")
    def api_state(rid: int = -1):
        """合并端点: status + groups 一次返回(前端单请求轮询, 请求数减半)

        rid 为前端已持有的分组视图版本: 版本一致时只回 status(体积极小), groups 不回传,
        前端据此跳过整表替换与重渲染; rid 缺省/不匹配时回传全量分组数据。
        """
        manager.touch_web_client()
        snap = manager.status_snapshot()
        return {
            "status":
                {
                    "connected": snap["connected"],
                    "paused": snap["paused"],
                    "torrents": snap["torrents"],
                    "groups": len(manager._group_view),
                    "version": _app_version(),
                    # 限速/流量快照: 恒回传(不受 rid 门控) —— 数据源是限速曲线任务而非分组视图,
                    # 若参与版本门控会与 groups 的脏语义耦合, 反而可能长时间不刷新
                    "traffic": manager._traffic_view,
                },
            **manager.ensure_group_state(rid),
        }

    @app.get("/api/groups")
    def api_groups():
        manager.touch_web_client()
        return {"groups": manager.ensure_group_view()}

    @app.get("/api/search")
    def api_search(q: str = ""):
        """按种子名/文件列表搜索种子(主循环构建的缓存索引, Web 线程只读; 索引脏时投递构建命令)"""
        manager.touch_web_client()
        return manager.search_torrents(q)

    @app.post("/api/groups/{key}/pause")
    def api_pause(key: str):
        _enqueue("pause_group", {"key": decode_group_key(key)})
        return {"queued": True}

    @app.post("/api/groups/{key}/resume")
    def api_resume(key: str):
        _enqueue("resume_group", {"key": decode_group_key(key)})
        return {"queued": True}

    @app.post("/api/groups/{key}/reannounce")
    def api_reannounce(key: str):
        _enqueue("reannounce_group", {"key": decode_group_key(key)})
        return {"queued": True}

    @app.post("/api/groups/{key}/delete")
    def api_delete(key: str, body: dict = None):
        delete_files = bool((body or {}).get("delete_files", False))
        _enqueue("delete_group", {"key": decode_group_key(key), "delete_files": delete_files})
        return {"queued": True, "delete_files": delete_files}

    @app.post("/api/torrents/{hash}/pause")
    def api_t_pause(hash: str):
        _enqueue("pause_torrent", {"hash": hash})
        return {"queued": True}

    @app.post("/api/torrents/{hash}/resume")
    def api_t_resume(hash: str):
        _enqueue("resume_torrent", {"hash": hash})
        return {"queued": True}

    @app.post("/api/torrents/{hash}/reannounce")
    def api_t_reannounce(hash: str):
        _enqueue("reannounce_torrent", {"hash": hash})
        return {"queued": True}

    @app.post("/api/torrents/{hash}/delete")
    def api_t_delete(hash: str, body: dict = None):
        delete_files = bool((body or {}).get("delete_files", False))
        _enqueue("delete_torrent", {"hash": hash, "delete_files": delete_files})
        return {"queued": True, "delete_files": delete_files}

    @app.get("/api/config/schema")
    def api_config_schema():
        """配置表单元数据(分组/字段/控件/帮助) + 热重载级别(唯一来源: config.impact)"""
        from .config import schema as config_schema
        from .config.impact import SECTION_LEVELS, TRACKER_FIELD_LEVELS

        payload = config_schema.schema_payload()
        # 级别表由 impact 单一维护(与热重载实际分级同源), API 层只做合并
        payload["levels"] = {"sections": SECTION_LEVELS, "tracker_fields": TRACKER_FIELD_LEVELS}
        return payload

    @app.get("/api/config")
    def api_config_get():
        """当前配置树(YAML 同构, 标量为字符串) + 写盘路径"""
        from .config.writer import read_tree

        return {"tree": read_tree(manager.config_path), "path": manager.config_path}

    @app.put("/api/config")
    def api_config_put(body: dict):
        """保存图形化配置: 结构校验(与启动同路径) -> R 级字段回退 -> round-trip 写盘 -> 投递热重载

        校验失败不触碰磁盘; R 级字段(state_file/data_dir)保留旧值, 其余立即生效。
        """
        from .config.errors import ConfigError
        from .config.loaders import load_config
        from .config.writer import write_tree

        tree = (body or {}).get("tree")
        if not isinstance(tree, dict):
            raise HTTPException(status_code=400, detail="tree 必须是对象")
        try:
            result = write_tree(manager.config_path, tree, manager.config)
        except (ConfigError, ValueError) as e:
            raise HTTPException(status_code=400, detail=str(e))

        # 投递热重载(主循环线程应用; R 级字段已在树中回退为旧值)
        _enqueue("reload_config", {"config": load_config(manager.config_path)})
        return {
            "applied": True,
            "changes": [{
                "path": c.path,
                "level": c.level
            } for c in result.changes],
            "restart_required": result.restart_required,
        }

    @app.post("/api/config/preview")
    def api_config_preview(body: dict):
        """只读预览: 返回"即将写入"的 YAML 文本(不落盘、不投递热重载), 校验口径与保存一致"""
        from .config.errors import ConfigError
        from .config.writer import preview_tree

        tree = (body or {}).get("tree")
        if not isinstance(tree, dict):
            raise HTTPException(status_code=400, detail="tree 必须是对象")
        try:
            text = preview_tree(manager.config_path, tree, manager.config)
        except (ConfigError, ValueError) as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"yaml": text}

    # 静态前端(阶段 B 挂载: web_ui/static; index.html 兜底)
    static_dir = os.path.join(os.path.dirname(__file__), "web_ui", "static")
    if os.path.isdir(static_dir):
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

    return app


class WebServerHandle:
    """WEB 服务器句柄(uvicorn 独立线程)

    stop() 仅请求退出(异步: uvicorn 主循环每 0.1s 才读一次 should_exit, 随后才关闭监听套接字);
    wait() 等待服务线程真正退出。**重启同端口必须 stop 后 wait**, 否则新服务 bind 报
    Errno 10048(每个套接字地址只允许使用一次)。
    """

    __slots__ = ("server", "thread")

    def __init__(self, server: uvicorn.Server, thread: threading.Thread) -> None:
        self.server = server
        self.thread = thread

    def stop(self) -> None:
        """请求停止(返回时服务仍在退出中, 需 wait() 确认已释放端口)"""
        self.server.should_exit = True

    def wait(self, timeout: Optional[float] = None) -> bool:
        """等待服务线程退出; 返回是否已退出(False = 超时仍在运行)"""
        self.thread.join(timeout)
        return not self.thread.is_alive()

    @property
    def started(self) -> bool:
        """监听是否已就绪(uvicorn 在 create_server 成功后置位)"""
        return bool(self.server.started)


def _run_server(server: uvicorn.Server) -> None:
    """服务线程入口: 把 uvicorn 的失败退出记进日志

    bind 失败时 uvicorn 走 sys.exit(STARTUP_FAILURE), 而 SystemExit 在非主线程被 threading
    静默吞掉(只剩 uvicorn 自己那行无时间戳的 ERROR), 日志上看不出"WEB UI 已经死了"。
    这里就地记录(含异常链: OSError -> SystemExit)后不再上抛 —— 上抛同样被吞, 只会多一份噪音。
    """
    try:
        server.run()
    except BaseException:
        logger.error("WEB UI 服务异常退出(端口被占用/监听失败?)", exc_info=True)


def _wait_until_started(handle: WebServerHandle, timeout: float) -> bool:
    """等待监听就绪: server.started 置位即成功; 线程提前退出(启动失败)/超时返回 False"""
    deadline = time.monotonic() + timeout
    while not handle.started:
        if not handle.thread.is_alive():
            return False
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.01)
    return True


def start_web_server(manager) -> WebServerHandle:
    """启动 WEB 服务器(独立线程); 返回句柄(stop()/wait())

    就绪(或确认失败)后才打日志: 起线程后立即打印会掩盖 bind 失败(端口被占用时依然显示"已启动")。
    """
    manager._web_token = ensure_web_token(manager)
    app = create_app(manager)
    config = uvicorn.Config(
        app,
        host=manager.config.web.host,
        port=manager.config.web.port,
        log_level="warning",
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=_run_server, args=(server, ), name="auto-qb-web", daemon=True)
    thread.start()
    handle = WebServerHandle(server, thread)
    if _wait_until_started(handle, WEB_START_TIMEOUT):
        logger.warning(
            f"WEB UI 已启动: http://{manager.config.web.host}:{manager.config.web.port} "
            f"(密钥见 {os.path.join(os.path.dirname(manager.state_file) or '.', 'web.token')})"
        )
    else:
        logger.error(
            f"WEB UI 启动失败: {manager.config.web.host}:{manager.config.web.port} 无法监听"
            "(端口被占用? 详见上方 uvicorn 错误)"
        )
    return handle


def stop_web_server(handle: WebServerHandle, timeout: float = WEB_STOP_TIMEOUT) -> bool:
    """请求停止并等待服务线程退出; 返回是否已退出(False = 超时仍在运行, 调用方自行决定)

    热重载重启(host/port 变更)必须先走本函数: 只 handle.stop() 就立刻启新服务,
    旧服务的监听套接字尚未释放 -> Errno 10048。
    """
    handle.stop()
    if handle.wait(timeout):
        return True
    logger.warning(f"WEB UI 旧服务在 {timeout:g}s 内未退出, 仍尝试重启(监听套接字通常已释放)")
    return False
