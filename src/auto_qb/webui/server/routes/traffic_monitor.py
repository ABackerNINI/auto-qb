"""全局流量监视器工具联动路由(计划 26-10-16-0541 S6): 设置页经本模块代理工具控制面.

端点:
  GET  /api/traffic/monitor/status    工具 GET /status 代理(只读; 设置页状态区 + 工具参数回显)
  PUT  /api/traffic/monitor/config    工具 PUT /config 代理(全量覆盖 -> 前端「读后写」)
  POST /api/traffic/monitor/autostart 工具 POST /autostart 代理(幂等注册/卸载开机自启)

auto-qb 与工具是两个进程、两个 venv: 本模块是唯一桥 —— 用 stdlib urllib 带 Bearer token
调工具控制面(缺省 127.0.0.1:8099)。**不 import 工具包**, 只经 HTTP 契约通信(与架构图一致)。

错误口径(两段不同, 各有理由):
- `GET /status` 是**展示端点** —— 工具没在跑也要能显示「为什么」, 故恒 200 + 结构化空态
  (`reachable=false` + `error`), 不抛 5xx(否则设置页只能看到一片红)。
- `PUT /config` / `POST /autostart` 是**写端点** —— 失败必须真报错(前端据此提示), 工具 400
  原样透传(校验错误逐条可见), 上游 5xx / 不可达收口为 502, 平台不支持透传 501。

token 解析(单点 `_resolve_token_path`): `global_traffic_monitor.tool_token_path` 非空则用它,
否则取工具平台默认数据目录下的 `monitor.token`(镜像 gtm.storage.default_data_dir 的惯例)。
真值仍以工具 `/status` 回显的 `paths.token` 为准, 供排障对照。
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from fastapi import APIRouter, HTTPException

from ....infra.utils import is_mac, is_windows
from ..context import WebContext

# 工具控制面调用超时(秒): 本机回环调用, 正常亚毫秒级; 给足余量但不无限等(工具假死)
_TOOL_TIMEOUT_S = 5.0


class ToolUnreachable(RuntimeError):
    """工具控制面不可达 / 响应非法(网络错、连接拒绝、非 JSON)."""


def _tm_conf(manager):
    """global_traffic_monitor 配置读取单点(段恒在, 缺省 enabled=false)"""
    return manager.config.global_traffic_monitor


def _tool_default_data_dir() -> str:
    """工具数据目录默认值(镜像 gtm.storage.default_data_dir 的平台惯例; 环境变量优先)

    镜像而非 import: 工具是独立包/venv, auto-qb 不 import 它。仅用于 tool_token_path 留空时
    定位缺省 token; 用户在配置里显式给 tool_token_path 即覆盖本推断。平台判定走 utils 单点。
    """
    env = os.environ.get("GTM_DATA_DIR")
    if env:
        return env
    if is_windows():
        base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
        return os.path.join(base, "gtm")
    if is_mac():
        return os.path.join(os.path.expanduser("~"), "Library", "Application Support", "gtm")
    base = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
    return os.path.join(base, "gtm")


def _resolve_token_path(conf) -> str:
    """工具 monitor.token 路径: 显式 tool_token_path 优先, 否则工具平台默认数据目录下"""
    explicit = str(conf.tool_token_path or "").strip()
    if explicit:
        return os.path.abspath(os.path.expanduser(explicit))
    return os.path.join(_tool_default_data_dir(), "monitor.token")


def _read_token(path: str) -> str:
    """读工具密钥文件(去空白); 缺失/读失败 -> 空串(由调用方决定报错口径)"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def _call_tool(base_url: str, path: str, method: str, token: str, payload=None, timeout: float = _TOOL_TIMEOUT_S):
    """调工具控制面: 返回 (status_code, payload_dict); 不可达/非 JSON -> ToolUnreachable

    只经 HTTP 契约; 4xx/5xx 也正常返回(交给调用方按域映射), 网络层失败才抛。
    """
    url = base_url.rstrip("/") + path
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        url,
        method=method,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            code = resp.status
    except urllib.error.HTTPError as e:
        raw = e.read()
        code = e.code
    except (urllib.error.URLError, OSError) as e:
        raise ToolUnreachable(f"工具控制面不可达({url}): {e}") from e
    try:
        return code, (json.loads(raw.decode("utf-8")) if raw else {})
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise ToolUnreachable(f"工具响应非法 JSON: {e}") from e


def _error_text(payload: dict, code: int) -> str:
    """从工具响应里抽人读错误: errors 列表优先(校验聚合), 否则 error 字段"""
    errors = payload.get("errors")
    if isinstance(errors, list) and errors:
        return "; ".join(str(x) for x in errors)
    return str(payload.get("error") or f"工具返回 {code}")


def build_router(ctx: WebContext) -> APIRouter:
    manager = ctx.manager
    router = APIRouter()

    @router.get("/api/traffic/monitor/status")
    def api_tm_status():
        """工具 /status 代理(只读, 展示端点): 恒 200 + 结构化结果

        - enabled=false 也照查(设置页要能在启用前先验证工具是否在跑);
        - 工具不可达 / 密钥缺失 -> reachable=false + error 文案, 不抛 5xx。
        """
        manager.web.touch()
        conf = _tm_conf(manager)
        token_path = _resolve_token_path(conf)
        base = {
            "enabled": bool(conf.enabled),
            "tool_url": conf.tool_url,
            "token_path": token_path,
            "reachable": False,
            "error": "",
            "status": None,
        }
        token = _read_token(token_path)
        if not token:
            base["error"] = f"工具密钥文件不存在或为空: {token_path}(工具未启动过? 或 tool_token_path 配置有误)"
            return base
        try:
            code, payload = _call_tool(conf.tool_url, "/status", "GET", token)
        except ToolUnreachable as e:
            base["error"] = str(e)
            return base
        if code != 200:
            base["error"] = f"工具 /status 返回 {code}: {_error_text(payload, code)}"
            return base
        base["reachable"] = True
        base["status"] = payload
        return base

    @router.put("/api/traffic/monitor/config")
    def api_tm_put_config(body: dict = None):
        """工具 /config 代理(写端点): 载荷 = {"config": {...全量...}}

        `PUT /config` 是**全量覆盖**(last-writer-wins): 前端必须「读后写」(先取 /status 的
        配置回显, 改字段后整体提交), 只发要改的键会把其余键打回默认值。
        """
        manager.web.touch()
        conf = _tm_conf(manager)
        payload = (body or {}).get("config")
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="config 必须是对象(工具配置全量载荷)")
        token = _read_token(_resolve_token_path(conf))
        if not token:
            raise HTTPException(status_code=502, detail="工具密钥文件不存在或为空(工具未启动过? 或 tool_token_path 配置有误)")
        try:
            code, resp = _call_tool(conf.tool_url, "/config", "PUT", token, payload)
        except ToolUnreachable as e:
            raise HTTPException(status_code=502, detail=str(e))
        if code == 200:
            return resp
        if code == 400:  # 工具侧校验失败: 逐条错误原样透传(前端展示)
            raise HTTPException(status_code=400, detail=_error_text(resp, code))
        raise HTTPException(status_code=502, detail=f"工具返回 {code}: {_error_text(resp, code)}")

    @router.post("/api/traffic/monitor/autostart")
    def api_tm_autostart(body: dict = None):
        """工具 /autostart 代理(写端点): 载荷 = {"action": "install"|"uninstall"}

        幂等注册/卸载开机自启; 退出码语义由工具侧承载(200 达成期望态含 no-op /
        501 平台不支持 / 5xx 命令失败), 本层原样映射。⚠ 工具与 WebUI 必须同机。
        """
        manager.web.touch()
        conf = _tm_conf(manager)
        action = str((body or {}).get("action") or "").strip()
        if action not in ("install", "uninstall"):
            raise HTTPException(status_code=400, detail="action 必须是 install 或 uninstall")
        token = _read_token(_resolve_token_path(conf))
        if not token:
            raise HTTPException(status_code=502, detail="工具密钥文件不存在或为空(工具未启动过? 或 tool_token_path 配置有误)")
        try:
            code, resp = _call_tool(conf.tool_url, "/autostart", "POST", token, {"action": action})
        except ToolUnreachable as e:
            raise HTTPException(status_code=502, detail=str(e))
        if code == 200:
            return resp
        if code == 400:
            raise HTTPException(status_code=400, detail=_error_text(resp, code))
        if code == 501:
            raise HTTPException(status_code=501, detail=_error_text(resp, code))
        raise HTTPException(status_code=502, detail=f"工具返回 {code}: {_error_text(resp, code)}")

    return router
