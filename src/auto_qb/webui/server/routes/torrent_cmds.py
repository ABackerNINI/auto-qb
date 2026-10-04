"""种子写命令路由: /api/torrents/{hash}/*(POST 18 条)+ /api/torrents/bulk + /api/torrents/add.

端点体逐字平移(plan 26-09-22-1857 W3); 仅 @app.* → @router.* 与共享件别名(原闭包名不变)。
鉴权由 factory 的全局 dependencies 单点覆盖, 本模块不另挂依赖。
日志命名空间见包 __init__(K3)。"""
from typing import List

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

    @router.post("/api/torrents/{hash}/skip-check")
    def api_t_skip_check(hash: str, body: dict = None):
        """右键跳检(高风险): 删除并以跳过校验方式重加, 清空本地统计 —— 前端另有危险确认框

        R2 gate(计划 26-10-02-1955 W1, D2=是 · fail-closed): 菜单隐藏只是 UX, 直调 API
        必须同样封禁 —— 配置 web.skip_check_menu 关闭时 403(detail 注明键名);
        rule 源跳检(ops 层 skip_check)不受影响。读实时配置(ctx.manager.config 引用现取,
        热重载后立即生效, 不按值持有旧 Config —— pitfalls/backend/hot-reload-held-config.md)。

        force 透传(计划 26-10-05-0314 S2): body.force=true 时进队列载荷, ops 层只豁越
        cls=force 的未过闸门(G5/G7 瞬态), cls=blocked 照旧硬拒 —— 服务端裁决, 前端绕不过;
        缺省不传(载荷不带 force 键, 队列形态与历史一致), ops 缺省 False 行为零变化。
        """
        if not ctx.manager.config.web.skip_check_menu:
            raise HTTPException(status_code=403, detail="跳检菜单未启用(配置键 web.skip_check_menu)")
        payload = {"hash": hash}
        if (body or {}).get("force"):
            payload["force"] = True  # 提供才透传(真值才入载荷, 缺省队列形态不变)
        return _enqueue("skip_check_torrent", payload)

    @router.post("/api/torrents/skip-check/precheck")
    def api_t_skip_check_precheck(body: dict = None):
        """跳检预检(只读 dry-run, 计划 26-10-05-0314 S2): 批量给出三分流判定, 供确认框在用户
        确认之前摊开「该不该跳检、赌什么」—— 执行路径闸门原样全跑, 预检-执行无信任传递

        挂与单发跳检**同一 403 门控**(web.skip_check_menu, fail-closed); 经 _enqueue 走
        主循环线程执行 ops.skip_check_precheck(与写命令串行化, 快照无撕裂; 复用 cmd_id +
        waitCmd 既有通道, 不开第二套请求-响应机制)。body {hashes: [...]}(单发 = 单元素数组
        由前端拼, 端点不关心); 空 hashes 400 拒收不入队(同文件 bulk/limits/location 的
        路由层参数校验先例: 参数错误在路由层 400, 前端即时可见)。回执(经 cmd 通道):
        status=ok + truth={results: [{hash, name, cls, reasons}], summary: {ok, force, blocked}}
        (summary 按单 hash 总 cls 计数), 未知 hash 透传 ops 的 gone/blocked verdict。
        """
        if not ctx.manager.config.web.skip_check_menu:
            raise HTTPException(status_code=403, detail="跳检菜单未启用(配置键 web.skip_check_menu)")
        hashes = [str(h) for h in ((body or {}).get("hashes") or []) if h]
        if not hashes:
            raise HTTPException(status_code=400, detail="未提供任何 hash(预检目标不能为空)")
        return _enqueue("skip_check_precheck", {"hashes": hashes})

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

        limits/location 扩展动作(计划 26-10-02-1955 W2): up_limit/dl_limit 非负 int
        (bytes/s, 0=qB 语义的"无限制", 允许), location 非空 str —— 均按"提供才透传"
        (队列载荷不带多余键, 纯 pause 调用的历史形态不变)。参数错误(负数 / limits
        两方向全空 / location 空路径)在路由层 400 拒收: 不入队, 前端即时可见。

        skip_check 批量动作(计划 26-10-02-1955 W3): 无额外参数(hashes/keys 即全部载荷),
        路由层不设独立 gate —— 分派处在 drain 时读实时配置拒单(D2=是·fail-closed,
        见 commands._cmd_bulk_torrents), 与单发端点的路由层 403 双层并存。
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
        # 标签/分类动作: 同样"提供才透传"(queue 载荷不带多余键)。
        # tags 非空才入; category 按键存在性入(payload 允许空串 = qB 语义的"清除分类")
        tags = [str(t).strip() for t in (b.get("tags") or []) if str(t).strip()]
        if tags:
            payload["tags"] = tags
        if b.get("category") is not None:
            payload["category"] = str(b["category"]).strip()
        # force 豁越(计划 26-10-05-0314 S2, 仅 skip_check 动作消费): 提供才透传 ——
        # 缺省队列载荷形态与历史完全一致(既有载荷形态守阵依赖); ops 层只豁越 cls=force 闸门
        if b.get("force"):
            payload["force"] = True
        # 批量限速/移动(W2): 提供才透传; 0 = 不限速合法, 负数路由层拒收
        if b.get("up_limit") is not None:
            v = int(b["up_limit"])
            if v < 0:
                raise HTTPException(status_code=400, detail="up_limit 不能为负数(0 = 不限速)")
            payload["up_limit"] = v
        if b.get("dl_limit") is not None:
            v = int(b["dl_limit"])
            if v < 0:
                raise HTTPException(status_code=400, detail="dl_limit 不能为负数(0 = 不限速)")
            payload["dl_limit"] = v
        location = str(b.get("location") or "").strip()
        if location:
            payload["location"] = location
        # 按 action 校验: limits 至少一项有值; location 必带非空路径
        action = payload["action"]
        if action == "limits" and "up_limit" not in payload and "dl_limit" not in payload:
            raise HTTPException(status_code=400, detail="批量限速至少提供 up_limit / dl_limit 一项(留空 = 不修改)")
        if action == "location" and not location:
            raise HTTPException(status_code=400, detail="批量移动必须提供非空 location")
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
