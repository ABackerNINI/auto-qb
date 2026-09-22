"""种子写命令路由: /api/torrents/{hash}/*(POST 18 条)+ /api/torrents/bulk + /api/torrents/add.

端点体逐字平移(plan 26-09-22-1857 W3); 仅 @app.* → @router.* 与共享件别名(原闭包名不变)。
鉴权由 factory 的全局 dependencies 单点覆盖, 本模块不另挂依赖。
日志命名空间见包 __init__(K3)。"""

from fastapi import HTTPException

from ..common import group_key_param as _group_key_param

from fastapi import APIRouter
from ..context import WebContext


def build_router(ctx: WebContext) -> APIRouter:
    _enqueue = ctx.enqueue
    router = APIRouter()

    @router.post("/api/torrents/{hash}/pause")
    def api_t_pause(hash: str):
        return _enqueue("pause_torrent", {"hash": hash})

    @router.post("/api/torrents/{hash}/resume")
    def api_t_resume(hash: str):
        return _enqueue("resume_torrent", {"hash": hash})

    @router.post("/api/torrents/{hash}/reannounce")
    def api_t_reannounce(hash: str):
        return _enqueue("reannounce_torrent", {"hash": hash})

    @router.post("/api/torrents/{hash}/delete")
    def api_t_delete(hash: str, body: dict = None):
        delete_files = bool((body or {}).get("delete_files", False))
        result = _enqueue("delete_torrent", {"hash": hash, "delete_files": delete_files})
        result["delete_files"] = delete_files
        return result

    # ---- 种子控制写端点(WEB UI 替代 qB 界面二轮: 全部 POST + _enqueue, 主循环线程执行) ----
    # 除 bulk 外, hash 不在快照时主循环侧静默跳过(照 pause_torrent 样板); 参数错误由
    # _cmd_* 抛 ValueError -> 命令分发层写 error 回执。qB 写后的快照同步策略见 QbApi。

    @router.post("/api/torrents/{hash}/recheck")
    def api_t_recheck(hash: str):
        return _enqueue("recheck_torrent", {"hash": hash})

    @router.post("/api/torrents/{hash}/super-seeding")
    def api_t_super_seeding(hash: str, body: dict = None):
        enable = bool((body or {}).get("enable", False))
        return _enqueue("super_seeding", {"hash": hash, "enable": enable})

    @router.post("/api/torrents/{hash}/force-start")
    def api_t_force_start(hash: str, body: dict = None):
        enable = bool((body or {}).get("enable", False))
        return _enqueue("force_start", {"hash": hash, "enable": enable})

    @router.post("/api/torrents/{hash}/limits")
    def api_t_limits(hash: str, body: dict = None):
        """种子传输限速(bytes/s, 0=不限); 两方向均可缺省(缺省的方向不下发)"""
        b = body or {}
        payload = {"hash": hash}
        if b.get("up_limit") is not None:
            payload["up_limit"] = int(b["up_limit"])
        if b.get("dl_limit") is not None:
            payload["dl_limit"] = int(b["dl_limit"])
        return _enqueue("set_torrent_limits", payload)

    @router.post("/api/torrents/{hash}/share-limits")
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

    @router.post("/api/torrents/{hash}/location")
    def api_t_location(hash: str, body: dict = None):
        location = str((body or {}).get("location") or "")
        return _enqueue("set_torrent_location", {"hash": hash, "location": location})

    @router.post("/api/torrents/{hash}/rename")
    def api_t_rename(hash: str, body: dict = None):
        name = str((body or {}).get("name") or "")
        return _enqueue("rename_torrent", {"hash": hash, "name": name})

    @router.post("/api/torrents/{hash}/queue")
    def api_t_queue(hash: str, body: dict = None):
        action = str((body or {}).get("action") or "")
        return _enqueue("queue_torrent", {"hash": hash, "action": action})

    @router.post("/api/torrents/{hash}/auto-tmm")
    def api_t_auto_tmm(hash: str, body: dict = None):
        enable = bool((body or {}).get("enable", False))
        return _enqueue("set_auto_tmm", {"hash": hash, "enable": enable})

    @router.post("/api/torrents/{hash}/trackers/add")
    def api_t_trackers_add(hash: str, body: dict = None):
        urls = [str(u) for u in ((body or {}).get("urls") or []) if u]
        return _enqueue("add_trackers", {"hash": hash, "urls": urls})

    @router.post("/api/torrents/{hash}/trackers/edit")
    def api_t_trackers_edit(hash: str, body: dict = None):
        b = body or {}
        payload = {"hash": hash, "orig_url": str(b.get("orig_url") or ""), "new_url": str(b.get("new_url") or "")}
        return _enqueue("edit_tracker", payload)

    @router.post("/api/torrents/{hash}/trackers/remove")
    def api_t_trackers_remove(hash: str, body: dict = None):
        url = str((body or {}).get("url") or "")
        return _enqueue("remove_tracker", {"hash": hash, "url": url})

    @router.post("/api/torrents/{hash}/files/priority")
    def api_t_file_priority(hash: str, body: dict = None):
        b = body or {}
        payload = {
            "hash": hash,
            "indices": [int(i) for i in (b.get("indices") or [])],
            "priority": int(b.get("priority") or 0),
        }
        return _enqueue("set_file_priority", payload)

    @router.post("/api/torrents/{hash}/rename-fs")
    def api_t_rename_fs(hash: str, body: dict = None):
        b = body or {}
        payload = {
            "hash": hash,
            "old_path": str(b.get("old_path") or ""),
            "new_path": str(b.get("new_path") or ""),
            "is_folder": bool(b.get("is_folder", False)),
        }
        return _enqueue("rename_fs", payload)

    @router.post("/api/torrents/bulk")
    def api_t_bulk(body: dict = None):
        """批量操作(平铺视图多选): 单命令批量, 主循环侧一次 API 调用传全部目标

        两种模式(DLG-02): hashes=种子 hash 列表; keys=分组 key 列表(URL 编码态, 与
        /api/groups/{key}/delete 同一编解码), 可混合。主循环侧展开组成员并与 hashes
        合并去重后一次调用; 回执结构与纯 hash 模式一致(queued/cmd_id + 聚合回执)。
        """
        b = body or {}
        payload = {
            "hashes": [str(h) for h in (b.get("hashes") or []) if h],
            "action": str(b.get("action") or ""),
            "delete_files": bool(b.get("delete_files", False)),
        }
        # 组键模式(DLG-02): 非空才入 payload, 纯 hash 调用的队列载荷与历史形态完全一致
        keys = [_group_key_param(str(k)) for k in (b.get("keys") or []) if k]
        if keys:
            payload["keys"] = keys
        return _enqueue("bulk_torrents", payload)

    @router.post("/api/torrents/add")
    def api_torrents_add(body: dict = None):
        """添加种子(JSON): .torrent 文件由前端 FileReader 读取为 base64 随 JSON 提交,
        后端解码后经命令队列内存直传 qB(qbittorrent-api 原生支持 bytes) ——
        零临时文件、零额外依赖(multipart 需要 python-multipart, 不引入); 布尔字段为真布尔"""
        import base64

        b = body or {}
        file_payload: List[bytes] = []
        for item in b.get("files_b64") or []:
            try:
                data = base64.b64decode(str(item), validate=False)
            except Exception:
                raise HTTPException(status_code=400, detail="torrent 文件 base64 解码失败")
            if data:
                file_payload.append(data)
        url_list = [u.strip() for u in (b.get("urls") or []) if str(u).strip()]
        if not file_payload and not url_list:
            raise HTTPException(status_code=400, detail="未提供 .torrent 文件或 magnet/URL")
        return _enqueue(
            "add_torrents", {
                "files": file_payload,
                "urls": url_list,
                "save_path": str(b.get("save_path") or "").strip(),
                "category": str(b.get("category") or "").strip(),
                "tags": [str(t).strip() for t in (b.get("tags") or []) if str(t).strip()],
                "paused": bool(b.get("paused")),
                "skip_checking": bool(b.get("skip_checking")),
                "sequential": bool(b.get("sequential")),
                "first_last_piece_prio": bool(b.get("first_last_piece_prio")),
                "auto_tmm": bool(b.get("auto_tmm")),
            }
        )

    return router
