"""配置备份 bundle 导出路由(计划 26-11-14-0624 S1): GET /api/backup/export

一次导出 = 一个 JSON bundle 文件(§03 形态): 服务端三段 + 前端一段:
- ``config_yaml``: config.yml 原文 -> ruamel round-trip -> 整体掩码(新单点
  ``config.writer.mask_yaml_text``, 与 GET /api/config 的 mask_tree 同一套判定)。
  **掩码不出机**(D2 不变量): 导出端点是纯掩码面 —— bundle 永不含明文凭据,
  也不新增「秘密读取原语」; 导入侧(S2)遇哨兵回填本机现值。
- ``webui_keys``: 经现有 ``routes.keys.load_keys_doc``(与 GET /api/keys 同源同形状)。
- ``gtm``: 经 ``traffic_monitor._source_status``(与 GET /api/traffic/monitor/status 同源,
  只经 HTTP 契约通信); 工具离线/未就绪该段为 null(缺段 = 不含该面, 导入跳过)。
- ``ui_prefs``: 浏览器 localStorage 偏好(D3 拍板「只存浏览器」) —— **服务端零接触**,
  由前端把该段并进已下载的服务端 bundle 再落盘, 故本端点响应不含该键。

响应为可下载 JSON(文件名 auto-qb-backup-<YYYYMMDD-HHMMSS>.json), 沿用 .torrent 导出的
``Response`` + ``Content-Disposition`` 先例(全仓无 FileResponse)。

direct 端点(非 cmd 透传): 只读面, 不碰任务队列与 state_file, 不违反单一写线程假设;
也不取 _WRITE_LOCK(mask_yaml_text 纯内存, 不写盘)。鉴权由 factory 的全局 dependencies
单点覆盖, 本模块不另挂依赖。日志命名空间见包 __init__(K3)。
"""
import json
import logging
import os
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from ..common import content_disposition
from ..context import WebContext
from . import traffic_monitor as _tm
from .keys import load_keys_doc

logger = logging.getLogger("auto_qb.web")  # noqa: F401  (K3: server 包内 logger 名冻结; 本模块现无直接日志点)

BUNDLE_FORMAT = "auto-qb-config-bundle"
BUNDLE_VERSION = 1


def _config_yaml_section(manager) -> str:
    """config_yaml 段: 读原文 -> mask_yaml_text(掩码 + 注释保留); 文件不存在回空串"""
    if not os.path.exists(manager.config_path):
        return ""
    with open(manager.config_path, "r", encoding="utf-8") as f:
        text = f.read()
    from ....config.writer import mask_yaml_text

    try:
        return mask_yaml_text(text)
    except Exception as e:  # noqa: BLE001  (ruamel YAMLError/OSError 统一收口为明确 500)
        # detail 只留固定文案 + 异常类型名, 绝不拼 {e} —— ruamel DuplicateKeyError 的异常
        # 文本逐字回显重复键的明文值(实测: found duplicate key "password" with value "b"),
        # detail 进响应体 = 凭据泄敏, 违反 D2(掩码不出机)。也不为拼日志在此打点。
        raise HTTPException(status_code=500, detail=f"配置文件掩码化失败(bundle 导出中止): {type(e).__name__}") from e


def _gtm_section(manager) -> dict | None:
    """gtm 段: 工具在线 -> {config 合并树, tool_version, captured_at}; 离线 -> None(D9 不抛错)

    同源单点: 复用 traffic_monitor._source_status(与 GET /api/traffic/monitor/status 逐字
    同一状态面), 不另起探活链路。reachable 但 /status 回显缺失(非 200 竞态)同样按 None。
    """
    st = _tm._source_status(manager)
    if not st["reachable"]:
        return None
    status = st.get("status")
    if not isinstance(status, dict):
        return None
    return {
        "config": status.get("config"),  # 外部契约(工具 /status 回显), 保留 get 防御
        "tool_version": st["version"] or "",  # _source_status 自产字典, 直接访问
        "captured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }


def build_backup_bundle(manager) -> dict:
    """组装服务端侧 bundle(§03 形态; ui_prefs 由前端并入, 本函数不含)"""
    # 延迟导入: 本模块经 routes/__init__ 在 auto_qb/__init__ 的 import 链上被拉起,
    # 顶层 `from .... import __version__` 会撞 partially initialized(循环导入)
    from .... import __version__

    return {
        "format": BUNDLE_FORMAT,
        "bundle_version": BUNDLE_VERSION,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "app_version": __version__,
        "config_yaml": _config_yaml_section(manager),
        "webui_keys": load_keys_doc(manager),
        "gtm": _gtm_section(manager),
    }


def build_router(ctx: WebContext) -> APIRouter:
    manager = ctx.manager
    router = APIRouter()

    @router.get("/api/backup/export")
    def api_backup_export():
        """导出配置备份 bundle(可下载 JSON, 掩码不出机): 详见模块 docstring"""
        manager.web.touch()
        bundle = build_backup_bundle(manager)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        return Response(
            content=json.dumps(bundle, ensure_ascii=False, indent=2),
            media_type="application/json",
            # content_disposition 自拼扩展名(与 .torrent 导出同口径): 传不带后缀的基名
            headers={"Content-Disposition": content_disposition(f"auto-qb-backup-{stamp}", "auto-qb-backup", "json")},
        )

    return router
