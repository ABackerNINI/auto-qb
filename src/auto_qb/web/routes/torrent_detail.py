"""种子详情读路由: /api/torrents/{hash} 及 trackers/files/peers/export + 分类/标签 CRUD + 限速覆盖.

端点体逐字平移(plan 26-09-22-1857 W4); 仅 @app.* → @router.* 与共享件别名(原闭包名不变)。
鉴权由 factory 的全局 dependencies 单点覆盖, 本模块不另挂依赖。
日志命名空间见包 __init__(K3)。"""

from fastapi import HTTPException
from fastapi.responses import JSONResponse, Response

from ..common import content_disposition

from fastapi import APIRouter
from ..context import WebContext


def build_router(ctx: WebContext) -> APIRouter:
    manager = ctx.manager
    _cached_read = ctx.cached_read
    _enqueue = ctx.enqueue
    _require_torrent = ctx.require_torrent
    _require_client = ctx.require_client
    router = APIRouter()

    @router.get("/api/torrents/{hash}")
    def api_torrent_detail(hash: str):
        """单种子全量详情: TorrentRecord.to_dict 全字段(含 _raw 前向兼容字段)
        + site(站点名) + HR 展示字段(与分组成员视图同源) —— 详情抽屉 General tab 数据源"""
        manager.touch_web_client()
        rec = _require_torrent(hash)
        return JSONResponse(
            content={"torrent": {
                **rec.to_dict(), "site": rec.tracker_name,
                **manager._hr_view_fields(rec)
            }}
        )

    @router.get("/api/torrents/{hash}/trackers")
    def api_torrent_trackers(hash: str):
        """单种子 tracker 列表(qB 透传; 含 **/[DHT]/[PeX]/[LSD] 虚拟条目, 前端自行弱化)"""
        manager.touch_web_client()
        _require_torrent(hash)
        client = _require_client()  # 断开即 503: 绝不能拿缓存里的旧值冒充"还连着"
        return JSONResponse(
            content=_cached_read(f"trackers:{hash}", lambda: list(client.torrents_trackers(hash) or []))
        )

    @router.get("/api/torrents/{hash}/files")
    def api_torrent_files(hash: str):
        """单种子文件列表(qB 透传; 详情抽屉 Content tab 数据源)"""
        manager.touch_web_client()
        _require_torrent(hash)
        client = _require_client()  # 同上: 断连优先于缓存
        return JSONResponse(content=_cached_read(f"files:{hash}", lambda: list(client.torrents_files(hash) or [])))

    @router.get("/api/torrents/{hash}/peers")
    def api_torrent_peers(hash: str):
        """单种子 peer 列表(qB 透传; 详情抽屉打开期间前端按需轮询, 关闭即停, 不进主循环 tick)

        走 sync/torrentPeers(qbittorrent-api 2026.8.1 无 torrents_peers 方法, 旧调用线上
        AttributeError): 响应整包含 rid/full_update/peers/peers_removed, 前端对 peers 键
        做 dict/数组双形态归一。
        """
        manager.touch_web_client()
        _require_torrent(hash)
        client = _require_client()  # 同上: 断连优先于缓存
        # peers 是"活"数据: 窗口更短(1s), 抽屉 5s 轮询本就在窗口外
        return JSONResponse(
            content=_cached_read(
                f"peers:{hash}", lambda: dict(client.sync_torrent_peers(torrent_hash=hash) or {}), ttl=1.0
            )
        )

    # ---- 管理端点(R2B: 分类/标签/限速覆盖/添加种子/导出/日志) ----

    @router.get("/api/categories")
    def api_categories_list():
        """全部分类(name -> {save_path,...}, 读 store 缓存; 首次访问可能触发一次 qB 拉取)"""
        manager.touch_web_client()
        return {"categories": _cached_read("categories", lambda: manager.api.torrents_categories())}

    @router.get("/api/tags")
    def api_tags_list():
        """全部标签(读 store 缓存)"""
        manager.touch_web_client()
        return {"tags": _cached_read("tags", lambda: manager.api.torrents_tags())}

    @router.post("/api/categories")
    def api_category_create(body: dict = None):
        b = body or {}
        name = str(b.get("name") or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="分类名不能为空")
        return _enqueue("create_category", {"name": name, "save_path": str(b.get("save_path") or "").strip()})

    @router.post("/api/categories/edit")
    def api_category_edit(body: dict = None):
        b = body or {}
        name = str(b.get("name") or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="分类名不能为空")
        return _enqueue("edit_category", {"name": name, "save_path": str(b.get("save_path") or "").strip()})

    @router.post("/api/categories/remove")
    def api_category_remove(body: dict = None):
        names = [str(n).strip() for n in ((body or {}).get("names") or []) if str(n).strip()]
        if not names:
            raise HTTPException(status_code=400, detail="未提供要删除的分类")
        return _enqueue("remove_categories", {"names": names})

    @router.post("/api/tags")
    def api_tags_create(body: dict = None):
        tags = [str(t).strip() for t in ((body or {}).get("tags") or []) if str(t).strip()]
        if not tags:
            raise HTTPException(status_code=400, detail="未提供要新建的标签")
        return _enqueue("create_tags", {"tags": tags})

    @router.post("/api/tags/remove")
    def api_tags_remove(body: dict = None):
        tags = [str(t).strip() for t in ((body or {}).get("tags") or []) if str(t).strip()]
        if not tags:
            raise HTTPException(status_code=400, detail="未提供要删除的标签")
        return _enqueue("delete_tags", {"tags": tags})

    @router.get("/api/speed/mode")
    def api_speed_mode():
        """限速托管状态(D2): 曲线目标来自限速曲线任务快照(_traffic_view);
        qB 当前全局限速直读(只读, 无状态副作用 —— 与 peers 透传同一先例)"""
        manager.touch_web_client()
        view = manager._traffic_view
        curve_enabled = view.get("state") not in (None, "", "disabled")
        # 曲线存在但 enabled=False: 功能整体停用, 视为未启用(快照滞后/未发布时也兜底正确)
        gslc = manager.config.global_speed_limit_curve
        if gslc is not None and not gslc.enabled:
            curve_enabled = False
        target = None
        if curve_enabled:
            t = (view.get("limit") or {}).get("target") or {}
            target = {"upload_kib": t.get("up"), "download_kib": t.get("down")}
        current = None
        if manager.client is not None:
            try:
                current = manager.api.get_global_speed_limits()
            except Exception:
                current = None
        return {"curve_enabled": curve_enabled, "curve_target": target, "current": current}

    @router.post("/api/speed/override")
    def api_speed_override(body: dict = None):
        """全局限速手动覆盖(D2 语义): 曲线启用时为临时覆盖(下一档位切换恢复), 停用即常态设置"""
        b = body or {}
        return _enqueue(
            "speed_override", {
                "upload_kib": int(b.get("upload_kib") or 0),
                "download_kib": int(b.get("download_kib") or 0),
            }
        )

    @router.get("/api/torrents/{hash}/export")
    def api_torrent_export(hash: str):
        """导出 .torrent(QbApi 透传原始字节): Content-Disposition 附种子名(浏览器下载)"""
        manager.touch_web_client()
        rec = _require_torrent(hash)
        client = _require_client()
        data = client.torrents_export(torrent_hash=hash)
        return Response(
            content=data,
            media_type="application/x-bittorrent",
            headers={"Content-Disposition": content_disposition(rec.name or "", hash, "torrent")},
        )

    return router
