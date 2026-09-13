"""WEB UI 后端: FastAPI 应用工厂(只读快照 + 命令投递, 不直接触碰主循环状态)

线程模型: uvicorn 在独立线程运行; 本模块的所有请求处理器只做两件事——
1) 读取 manager 暴露的只读快照(_group_view/status_snapshot, 主循环每 tick 原子替换);
2) 向 manager.web_commands 投递控制命令(由主循环线程消费执行, 写操作只在主循环线程)。

鉴权: 所有 /api/* 请求校验 Bearer 密钥; 密钥来自 config.web.token, 留空则随机生成并
持久化到 <data_dir>/web.token(0600), 启动日志打印一次。默认仅监听 127.0.0.1。
"""
import base64
import json
import logging
import os
import secrets
from types import SimpleNamespace

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.staticfiles import StaticFiles

from .utils import decode_group_key

logger = logging.getLogger(__name__)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "web_ui", "static")


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
        expected = f"Bearer {manager._web_token}"
        if authorization != expected:
            # 诊断日志(临时): 收到与期望不一致时打印前缀与长度, 定位密钥不匹配来源
            logger.warning(
                f"WEB 鉴权失败: 收到 {authorization[:16]!r}(len={len(authorization)}), "
                f"期望 'Bearer {manager._web_token[:8]}…'(len={len(expected)})"
            )
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
        }

    @app.get("/api/state")
    def api_state():
        """合并端点: status + groups 一次返回(前端单请求轮询, 请求数减半)"""
        manager.touch_web_client()
        snap = manager.status_snapshot()
        return {
            "status":
                {
                    "connected": snap["connected"],
                    "paused": snap["paused"],
                    "torrents": snap["torrents"],
                    "groups": len(manager._group_view),
                },
            "groups": manager.ensure_group_view(),
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

    @app.get("/api/config/raw")
    def api_config_raw():
        """当前 config.yml 原文(含注释), 供 UI 编辑"""
        with open(manager.config_path, "r", encoding="utf-8") as f:
            return {"content": f.read()}

    @app.put("/api/config/raw")
    def api_config_raw_put(body: dict):
        """保存设置: 新文本经完整校验(与启动同路径)后写回并投递热重载

        R 级字段(state_file/data_dir)变更不参与热重载(保留旧值), 其余立即生效。
        """
        import tempfile

        from .config import load_config
        from .config.impact import diff_config_impacts

        content = (body or {}).get("content")
        if not isinstance(content, str) or not content.strip():
            raise HTTPException(status_code=400, detail="content 不能为空")
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".yml", delete=False) as f:
                f.write(content)
                tmp_path = f.name
            new_config = load_config(tmp_path)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)

        old_config = manager.config
        changes = diff_config_impacts(old_config, new_config)
        restart_required = [c.path for c in changes if c.level == "R"]
        if restart_required:
            # R 级字段(state_file/data_dir)保留旧值, 其余字段照常应用
            for c in changes:
                if c.level != "R":
                    continue
            new_config = _reject_restart_fields(old_config, new_config, changes)

        # 备份当前配置后写回(ruamel round-trip 保留新文本自身格式)
        config_path = manager.config_path
        if os.path.exists(config_path):
            backup = config_path + ".bak"
            with open(config_path, "r", encoding="utf-8") as src, open(backup, "w", encoding="utf-8") as dst:
                dst.write(src.read())
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(content)

        # 投递热重载(主循环线程应用; R 级字段已被替换为旧值)
        _enqueue("reload_config", {"config": load_config(config_path)})
        return {
            "applied": True,
            "changes": len(changes),
            "restart_required": restart_required,
        }

    def _reject_restart_fields(old_config, new_config, changes):
        """R 级字段回退为旧值(进程身份不可热切换), 其余字段保留新值"""
        r_paths = {c.path for c in changes if c.level == "R"}
        for c in changes:
            if c.level != "R":
                continue
            parts = c.path.split(".")
            if len(parts) == 1:
                setattr(new_config, parts[0], getattr(old_config, parts[0]))
            elif len(parts) == 2:
                seg = getattr(new_config, parts[0])
                if seg is not None and hasattr(seg, parts[1]):
                    setattr(seg, parts[1], getattr(getattr(old_config, parts[0]), parts[1], None))
        logger.warning(f"以下字段需重启进程才能生效, 本次保存保留旧值: {sorted(r_paths)}")
        return new_config

    # 静态前端(阶段 B 挂载: web_ui/static; index.html 兜底)
    static_dir = os.path.join(os.path.dirname(__file__), "web_ui", "static")
    if os.path.isdir(static_dir):
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
    return app


def start_web_server(manager) -> SimpleNamespace:
    """启动 WEB 服务器(独立线程); 返回句柄(stop())供停止"""
    manager._web_token = ensure_web_token(manager)
    app = create_app(manager)
    config = uvicorn.Config(
        app,
        host=manager.config.web.host,
        port=manager.config.web.port,
        log_level="warning",
    )
    server = uvicorn.Server(config)

    import threading

    threading.Thread(target=server.run, name="auto-qb-web", daemon=True).start()
    logger.warning(
        f"WEB UI 已启动: http://{manager.config.web.host}:{manager.config.web.port}"
        f"(密钥见 {os.path.join(os.path.dirname(manager.state_file) or '.', 'web.token')})"
    )
    return SimpleNamespace(stop=lambda: setattr(server, "should_exit", True))
