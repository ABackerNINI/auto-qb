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
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import RedirectResponse
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


def _config_backup_path(manager) -> str:
    """配置保存前的备份路径: `<data_dir>/<配置文件名>.bak`

    备份集中到运行时数据目录(与 state/log/web.token 同处), 不在项目根目录产生 config.yml.bak。
    data_dir 为相对路径时以 cwd 为基准 —— 与 state_file 的派生口径一致(见 config/loaders._under)。
    """
    return os.path.join(manager.config.data_dir, os.path.basename(manager.config_path) + ".bak")


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


def _is_loopback_host(host) -> bool:
    """是否为本机 loopback 地址: 仅 127.0.0.1 / ::1 及其 IPv4-mapped 形式"""
    if not host:
        return False
    return host in ("127.0.0.1", "::1", "::ffff:127.0.0.1")


def create_app(manager) -> FastAPI:
    """构建 WEB 应用: 只读快照 + 命令投递 + 设置读写, 全部 /api/* 经 Bearer 密钥鉴权"""
    def require_token(request: Request, authorization: str = Header(default="")):
        # 公开只读端点: 前端登录前读取本机免鉴权等标志(不含任何机密), 免 token 放行
        if request.url.path == "/api/config/public":
            return
        # 跳过本地验证: 本机(loopback)连接免 token 鉴权, 直接放行进入(web.skip_local_verify)
        if manager.config.web.skip_local_verify and _is_loopback_host(request.client.host if request.client else None):
            if not authorization.startswith("Bearer "):
                logger.warning("WEB 跳过本地验证: 本机连接免密钥放行(web.skip_local_verify=true)")
            return
        # 鉴权范围 = /api/*: 静态页面与 UI 重定向路由无密钥也可访问(页面本身不含数据,
        # 密钥由前端加载后带 Authorization 头访问 API; 旧实现仅靠"StaticFiles 挂载不经
        # 依赖系统"这个副作用放行静态, UI 目录化后根路径/重定向是真实路由, 必须显式放行)。
        # 缺省/畸形凭证(无头、scheme 错误、空 token)静默 401: 属客户端常态(登录框空提交、
        # 轮询竞态、端口探测), 记 WARNING 会经 notify 推送扰民(历史上前端空 token 请求被
        # HTTP 头 OWS 裁剪成裸 "Bearer", 曾持续误报); 仅"携带了但错误"的密钥记一条不含密钥
        # 内容的 WARNING, 保留真实错密钥/探测信号。比较走 compare_digest 防时序侧信道。
        if not request.url.path.startswith("/api"):
            return
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

    @app.get("/api/config/public")
    def api_config_public():
        """前端登录前读取的公开只读标志(不含密钥等机密): 本机免鉴权开关"""
        return {"web": {"skip_local_verify": manager.config.web.skip_local_verify}}

    def _enqueue(cmd: str, payload: dict) -> dict:
        """投递控制命令并生成回执 ID: 前端据 cmd_id 轮询 /api/cmd/{id} 获取执行结果"""
        cmd_id = secrets.token_hex(8)
        body = dict(payload or {})
        body["cmd_id"] = cmd_id
        manager.web_commands.put((cmd, body))
        return {"queued": True, "cmd_id": cmd_id}

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
        return _enqueue("pause_group", {"key": decode_group_key(key)})

    @app.post("/api/groups/{key}/resume")
    def api_resume(key: str):
        return _enqueue("resume_group", {"key": decode_group_key(key)})

    @app.post("/api/groups/{key}/reannounce")
    def api_reannounce(key: str):
        return _enqueue("reannounce_group", {"key": decode_group_key(key)})

    @app.post("/api/groups/{key}/delete")
    def api_delete(key: str, body: dict = None):
        delete_files = bool((body or {}).get("delete_files", False))
        result = _enqueue("delete_group", {"key": decode_group_key(key), "delete_files": delete_files})
        result["delete_files"] = delete_files
        return result

    @app.post("/api/torrents/{hash}/pause")
    def api_t_pause(hash: str):
        return _enqueue("pause_torrent", {"hash": hash})

    @app.post("/api/torrents/{hash}/resume")
    def api_t_resume(hash: str):
        return _enqueue("resume_torrent", {"hash": hash})

    @app.post("/api/torrents/{hash}/reannounce")
    def api_t_reannounce(hash: str):
        return _enqueue("reannounce_torrent", {"hash": hash})

    @app.post("/api/torrents/{hash}/delete")
    def api_t_delete(hash: str, body: dict = None):
        delete_files = bool((body or {}).get("delete_files", False))
        result = _enqueue("delete_torrent", {"hash": hash, "delete_files": delete_files})
        result["delete_files"] = delete_files
        return result

    # ---- 种子控制写端点(WEB UI 替代 qB 界面二轮: 全部 POST + _enqueue, 主循环线程执行) ----
    # 除 bulk 外, hash 不在快照时主循环侧静默跳过(照 pause_torrent 样板); 参数错误由
    # _cmd_* 抛 ValueError -> 命令分发层写 error 回执。qB 写后的快照同步策略见 QbApi。

    @app.post("/api/torrents/{hash}/recheck")
    def api_t_recheck(hash: str):
        return _enqueue("recheck_torrent", {"hash": hash})

    @app.post("/api/torrents/{hash}/super-seeding")
    def api_t_super_seeding(hash: str, body: dict = None):
        enable = bool((body or {}).get("enable", False))
        return _enqueue("super_seeding", {"hash": hash, "enable": enable})

    @app.post("/api/torrents/{hash}/force-start")
    def api_t_force_start(hash: str, body: dict = None):
        enable = bool((body or {}).get("enable", False))
        return _enqueue("force_start", {"hash": hash, "enable": enable})

    @app.post("/api/torrents/{hash}/limits")
    def api_t_limits(hash: str, body: dict = None):
        """种子传输限速(bytes/s, 0=不限); 两方向均可缺省(缺省的方向不下发)"""
        b = body or {}
        payload = {"hash": hash}
        if b.get("up_limit") is not None:
            payload["up_limit"] = int(b["up_limit"])
        if b.get("dl_limit") is not None:
            payload["dl_limit"] = int(b["dl_limit"])
        return _enqueue("set_torrent_limits", payload)

    @app.post("/api/torrents/{hash}/share-limits")
    def api_t_share_limits(hash: str, body: dict = None):
        """分享限制: -1=不限制, -2=用全局; 前端应从详情回填三值后整组提交"""
        b = body or {}
        payload = {"hash": hash}
        if b.get("ratio_limit") is not None:
            payload["ratio_limit"] = float(b["ratio_limit"])
        if b.get("seeding_time_limit") is not None:
            payload["seeding_time_limit"] = int(b["seeding_time_limit"])
        if b.get("inactive_seeding_time_limit") is not None:
            payload["inactive_seeding_time_limit"] = int(b["inactive_seeding_time_limit"])
        return _enqueue("set_share_limits", payload)

    @app.post("/api/torrents/{hash}/location")
    def api_t_location(hash: str, body: dict = None):
        location = str((body or {}).get("location") or "")
        return _enqueue("set_torrent_location", {"hash": hash, "location": location})

    @app.post("/api/torrents/{hash}/rename")
    def api_t_rename(hash: str, body: dict = None):
        name = str((body or {}).get("name") or "")
        return _enqueue("rename_torrent", {"hash": hash, "name": name})

    @app.post("/api/torrents/{hash}/queue")
    def api_t_queue(hash: str, body: dict = None):
        action = str((body or {}).get("action") or "")
        return _enqueue("queue_torrent", {"hash": hash, "action": action})

    @app.post("/api/torrents/{hash}/auto-tmm")
    def api_t_auto_tmm(hash: str, body: dict = None):
        enable = bool((body or {}).get("enable", False))
        return _enqueue("set_auto_tmm", {"hash": hash, "enable": enable})

    @app.post("/api/torrents/{hash}/trackers/add")
    def api_t_trackers_add(hash: str, body: dict = None):
        urls = [str(u) for u in ((body or {}).get("urls") or []) if u]
        return _enqueue("add_trackers", {"hash": hash, "urls": urls})

    @app.post("/api/torrents/{hash}/trackers/edit")
    def api_t_trackers_edit(hash: str, body: dict = None):
        b = body or {}
        payload = {"hash": hash, "orig_url": str(b.get("orig_url") or ""), "new_url": str(b.get("new_url") or "")}
        return _enqueue("edit_tracker", payload)

    @app.post("/api/torrents/{hash}/trackers/remove")
    def api_t_trackers_remove(hash: str, body: dict = None):
        url = str((body or {}).get("url") or "")
        return _enqueue("remove_tracker", {"hash": hash, "url": url})

    @app.post("/api/torrents/{hash}/files/priority")
    def api_t_file_priority(hash: str, body: dict = None):
        b = body or {}
        payload = {
            "hash": hash,
            "indices": [int(i) for i in (b.get("indices") or [])],
            "priority": int(b.get("priority") or 0),
        }
        return _enqueue("set_file_priority", payload)

    @app.post("/api/torrents/{hash}/rename-fs")
    def api_t_rename_fs(hash: str, body: dict = None):
        b = body or {}
        payload = {
            "hash": hash,
            "old_path": str(b.get("old_path") or ""),
            "new_path": str(b.get("new_path") or ""),
            "is_folder": bool(b.get("is_folder", False)),
        }
        return _enqueue("rename_fs", payload)

    @app.post("/api/torrents/bulk")
    def api_t_bulk(body: dict = None):
        """批量操作(平铺视图多选): 单命令批量, 主循环侧一次 API 调用传全部 hashes"""
        b = body or {}
        payload = {
            "hashes": [str(h) for h in (b.get("hashes") or []) if h],
            "action": str(b.get("action") or ""),
            "delete_files": bool(b.get("delete_files", False)),
        }
        return _enqueue("bulk_torrents", payload)

    # ---- 种子中心视图读端点(WEB UI 替代 qB 界面: 详情抽屉/全局统计) ----
    # 全部只读: 快照读 store, tracker/文件/peer 按需直读 client(不写 store 惰性缓存 ——
    # 缓存写入只在主循环线程, 保持 Web 线程无副作用); qB 断连时 503, 未知 hash 404。

    def _require_torrent(hash: str):
        rec = manager.store.get(hash)
        if rec is None:
            raise HTTPException(status_code=404, detail="种子不存在")
        return rec

    def _require_client():
        if manager.client is None:
            raise HTTPException(status_code=503, detail="qB 未连接")
        return manager.client

    @app.get("/api/torrents/{hash}")
    def api_torrent_detail(hash: str):
        """单种子全量详情: TorrentRecord.to_dict 全字段(含 _raw 前向兼容字段)
        + site(站点名) + HR 展示字段(与分组成员视图同源) —— 详情抽屉 General tab 数据源"""
        manager.touch_web_client()
        rec = _require_torrent(hash)
        return {"torrent": {**rec.to_dict(), "site": rec.tracker_name, **manager._hr_view_fields(rec)}}

    @app.get("/api/torrents/{hash}/trackers")
    def api_torrent_trackers(hash: str):
        """单种子 tracker 列表(qB 透传; 含 **/[DHT]/[PeX]/[LSD] 虚拟条目, 前端自行弱化)"""
        manager.touch_web_client()
        _require_torrent(hash)
        return list(_require_client().torrents_trackers(hash) or [])

    @app.get("/api/torrents/{hash}/files")
    def api_torrent_files(hash: str):
        """单种子文件列表(qB 透传; 详情抽屉 Content tab 数据源)"""
        manager.touch_web_client()
        _require_torrent(hash)
        return list(_require_client().torrents_files(hash) or [])

    @app.get("/api/torrents/{hash}/peers")
    def api_torrent_peers(hash: str):
        """单种子 peer 列表(qB 透传; 详情抽屉打开期间前端按需轮询, 关闭即停, 不进主循环 tick)"""
        manager.touch_web_client()
        _require_torrent(hash)
        return dict(_require_client().torrents_peers(hash) or {})

    @app.get("/api/stats")
    def api_stats():
        """qB 全局状态(sync/maindata 的 server_state: 会话/累计流量/DHT 节点/连接状态等)

        数据源是主循环增量同步时原子替换的只读引用; 降级全量(无 sync 端点)或
        尚未同步到响应时为 null, 前端按空态渲染。
        """
        manager.touch_web_client()
        return {"server": manager.store.server_state}

    @app.get("/api/cmd/{cmd_id}")
    def api_cmd_result(cmd_id: str):
        """命令执行结果查询(前端投递后轮询): pending = 主循环尚未执行完或仍在确认中

        reannounce 的回执由主循环的 tracker 确认跟踪器在确认成功/失败/超时后写入,
        其余命令执行完立即写入。结果只由主循环线程写, 此处只读。
        """
        manager.touch_web_client()
        result = manager._web_results.get(cmd_id)
        return dict(result) if result else {"status": "pending"}

    @app.get("/api/traffic/history")
    def api_traffic_history():
        """历史流量按日行(dat 原始数据, 升序): 供前端历史流量柱状图按天/月/年聚合

        数据源是限速曲线任务每轮发布的只读快照(_traffic_view["history"]), Web 线程只读;
        未启用限速曲线或数据源不可用时 history 为空数组, state 供前端判断展示分支。
        """
        manager.touch_web_client()
        view = manager._traffic_view
        return {"state": view.get("state"), "history": view.get("history") or []}

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
            result = write_tree(manager.config_path, tree, manager.config, _config_backup_path(manager))
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

    # 静态前端(UI 目录化: atlas=星图(旧) / prism=棱镜(新) / shared=公共逻辑层; 目录即 URL,
    # 新增 UI = static/<名字>/ 一个目录, 无需后端改动)
    static_dir = os.path.join(os.path.dirname(__file__), "web_ui", "static")
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
