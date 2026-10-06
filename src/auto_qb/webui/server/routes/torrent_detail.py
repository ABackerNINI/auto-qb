"""种子详情读路由: /api/torrents/{hash} 及 trackers/files/peers/export + 分类/标签 CRUD + 限速覆盖.

端点体逐字平移(plan 26-09-22-1857 W4); 仅 @app.* → @router.* 与共享件别名(原闭包名不变)。
鉴权由 factory 的全局 dependencies 单点覆盖, 本模块不另挂依赖。
日志命名空间见包 __init__(K3)。"""

import logging

from fastapi import HTTPException
from fastapi.responses import JSONResponse, Response

from ....infra.utils import auto_managed_tag_rules, is_auto_managed_tag, mask_tracker_entry
from ..common import content_disposition
from ..traffic_qb import QbTrafficChartApi as _QbTrafficChartApi

from fastapi import APIRouter
from ..context import WebContext

logger = logging.getLogger("auto_qb.web")  # noqa: F401  (speed/mode 读失败 DEBUG 记录)


def build_router(ctx: WebContext) -> APIRouter:
    manager = ctx.manager
    _cached_read = ctx.cached_read
    _enqueue = ctx.enqueue
    _require_torrent = ctx.require_torrent
    _require_client = ctx.require_client
    _qb_traffic = _QbTrafficChartApi(manager)
    router = APIRouter()

    @router.get("/api/torrents/{hash}")
    def api_torrent_detail(hash: str):
        """单种子全量详情: TorrentRecord.to_dict 全字段(含 _raw 前向兼容字段)
        + site(站点名) + HR 展示字段(与分组成员视图同源) —— 详情抽屉 General tab 数据源"""
        manager.web.touch()
        rec = _require_torrent(hash)
        return JSONResponse(
            content={"torrent": {
                **rec.to_dict(), "site": rec.tracker_name,
                **manager.hr_view_fields(rec)
            }}
        )

    @router.get("/api/torrents/{hash}/trackers")
    def api_torrent_trackers(hash: str):
        """单种子 tracker 列表(qB 透传; 含 **/[DHT]/[PeX]/[LSD] 虚拟条目, 前端自行弱化);
        url 已 mask(虚拟条目原样透传), 原文不再外发"""
        manager.web.touch()
        _require_torrent(hash)
        client = _require_client()  # 断开即 503: 绝不能拿缓存里的旧值冒充"还连着"
        # mask 先于缓存写入: 缓存里永远只有 mask 条目(plan 26-10-07-0055 S3)
        return JSONResponse(
            content=_cached_read(
                f"trackers:{hash}", lambda: [mask_tracker_entry(t) for t in (client.torrents_trackers(hash) or [])]
            )
        )

    @router.get("/api/torrents/{hash}/files")
    def api_torrent_files(hash: str):
        """单种子文件列表(qB 透传; 详情抽屉 Content tab 数据源)"""
        manager.web.touch()
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
        manager.web.touch()
        _require_torrent(hash)
        client = _require_client()  # 同上: 断连优先于缓存
        # peers 是"活"数据: 窗口更短(1s), 抽屉 5s 轮询本就在窗口外
        return JSONResponse(
            content=_cached_read(
                f"peers:{hash}", lambda: dict(client.sync_torrent_peers(torrent_hash=hash) or {}), ttl=1.0
            )
        )

    @router.get("/api/traffic/qb/torrent/{hash}")
    def api_traffic_qb_torrent(hash: str, window: str = "24h"):
        """单种子 qB 口径流量时序(plan 26-10-03-0946 §08, P4; v3 翻转 S3b): torrents/<hash>/
        天文件 + agg.dat 读侧栅格离散

        数据挂 infohash 身份(§02.2), 删种冻结后历史仍可查(与详情端点的 _require_torrent
        404 口径刻意不同 —— 哈希不合法 400 / 无数据空态, 不以快照存在性裁决历史数据);
        响应形状与全局/分组端点一致(装配单点在 server/traffic_qb.py)。
        """
        manager.web.touch()
        return JSONResponse(content=_qb_traffic.payload_torrent(hash, window))

    # ---- 管理端点(R2B: 分类/标签/限速覆盖/添加种子/导出/日志) ----

    @router.get("/api/categories")
    def api_categories_list():
        """全部分类(name -> {save_path,...}, 读 store 缓存; 首次访问可能触发一次 qB 拉取)"""
        manager.web.touch()
        return {"categories": _cached_read("categories", lambda: manager.api.torrents_categories())}

    @router.get("/api/tags")
    def api_tags_list(exclude_auto: bool = False):
        """全部标签(读 store 缓存); exclude_auto=1 剔除程序自动维护的标签(判定口径
        utils.auto_managed_tag_rules: 站点/HR 精确集 + 集数模板形状) —— 添加种子窗口与
        「标签/分类…」弹窗的候选源用本参, 避免站点名等程序标签刷屏; 标签管理对话框不带
        本参保持全量。选中种子已携带的标签由前端并回候选(胶囊是唯一摘除入口, 不能藏)。"""
        manager.web.touch()
        tags = _cached_read("tags", lambda: manager.api.torrents_tags())
        if exclude_auto:
            exact, patterns = auto_managed_tag_rules(manager.config)
            tags = [t for t in tags if not is_auto_managed_tag(t, exact, patterns)]
        return {"tags": tags}

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
        """限速托管状态(D2): 曲线目标来自限速曲线任务快照(traffic_view);
        qB 当前全局限速直读(只读, 无状态副作用 —— 与 peers 透传同一先例)"""
        manager.web.touch()
        view = manager.web.traffic_view
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
        alt_on = None
        alt_current = None
        if manager.client is not None:
            try:
                current = manager.api.get_global_speed_limits()
                # ALT-01: 备用速度模式与备用限速值同窗取(限速浮层主/备双组的数据源)
                alt_on = bool(manager.api.get_speed_limits_mode())
                alt_current = manager.api.get_alt_speed_limits()
            except Exception as e:
                # 三读成败口径对齐: 任一失败整组回 None(前端浮层不出现「一半真一半未知」),
                # 不拿旧缓存冒充; 异常降 DEBUG 留一行摘要(排障「为什么显示未知」有日志可查,
                # qB 瞬时故障属常态不打 WARNING; issue 26-10-06-0028 chore-speed-mode-silent-except)
                current = alt_on = alt_current = None
                logger.debug("speed/mode 直读 qB 失败, 整组回 None: %s: %s", type(e).__name__, e)
        return {
            "curve_enabled": curve_enabled,
            "curve_target": target,
            "current": current,
            "alt_on": alt_on,
            "alt_current": alt_current,
        }

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

    @router.post("/api/speed/alt")
    def api_speed_alt(body: dict = None):
        """备用速度限制设置(ALT-01): app/setPreferences(alt_dl_limit/alt_up_limit), 两方向都必填, 0 = 不限"""
        b = body or {}
        return _enqueue(
            "speed_alt_set", {
                "upload_kib": int(b.get("upload_kib") or 0),
                "download_kib": int(b.get("download_kib") or 0),
            }
        )

    @router.post("/api/speed/alt/toggle")
    def api_speed_alt_toggle():
        """主/备速度模式切换(ALT-01): qB toggle 端点原生语义; 新状态以主轮询 server_state 回读为准"""
        return _enqueue("speed_alt_toggle", {})

    @router.get("/api/torrents/{hash}/export")
    def api_torrent_export(hash: str):
        """导出 .torrent(QbApi 透传原始字节): Content-Disposition 附种子名(浏览器下载)"""
        manager.web.touch()
        rec = _require_torrent(hash)
        client = _require_client()
        data = client.torrents_export(torrent_hash=hash)
        return Response(
            content=data,
            media_type="application/x-bittorrent",
            headers={"Content-Disposition": content_disposition(rec.name or "", hash, "torrent")},
        )

    return router
