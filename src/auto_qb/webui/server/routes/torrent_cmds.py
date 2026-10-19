"""种子写命令路由: /api/torrents/{hash}/*(POST 18 条)+ /api/torrents/bulk + /api/torrents/add
+ /api/torrents/relocate/precheck + /api/relocate/precheck-add(整组迁移预检, 计划 26-10-18-1604 P2).

端点体逐字平移(plan 26-09-22-1857 W3); 仅 @app.* → @router.* 与共享件别名(原闭包名不变)。
单行透传端点的 mechanics 已收敛到 build_router 内四个形状 helper 与 _require_skip_check
门控单点(issue route-cmd-boilerplate-dup), 复杂端点仍逐字平移。
鉴权由 factory 的全局 dependencies 单点覆盖, 本模块不另挂依赖。
日志命名空间见包 __init__(K3)。"""
from typing import List

from fastapi import HTTPException

from ..common import group_key_param as _group_key_param

from fastapi import APIRouter
from ..context import WebContext


def _require_skip_check(ctx: WebContext) -> None:
    """跳检菜单 403 门控单点(fail-closed; 计划 26-10-02-1955 W1, D2=是)

    issue route-cmd-boilerplate-dup: 单发 skip-check 与批量预检两端点此前逐字各写一遍
    「配置关 -> 403(detail 注明键名)」—— 改文案 / 改键名要记得改两处, 是真实漂移点。
    读实时配置(ctx.manager.config 引用现取, 热重载后立即生效, 不按值持有旧 Config)。
    """
    if not ctx.manager.config.web.skip_check_menu:
        raise HTTPException(status_code=403, detail="跳检菜单未启用(配置键 web.skip_check_menu)")


def _require_relocate(ctx: WebContext) -> None:
    """整组迁移 403 门控单点(fail-closed; 计划 26-10-18-1604 §3.6, 与跳检门控同口径)

    relocate.enabled=false(缺省)时三个入口(WebUI 移动位置/规则 move_to/添加对话框)
    逐字节保持现状 —— 预检端点也一并封禁: 预检是给「启用后的迁移确认框/添加对话框」
    摊开后果用的, 功能关着时前端根本不该发起, 直调 API 同样拒绝(键名进 detail)。
    读实时配置(ctx.manager.config 引用现取, 热重载后立即生效, 不按值持有旧 Config)。
    """
    if not getattr(ctx.manager.config.relocate, "enabled", False):
        raise HTTPException(status_code=403, detail="整组迁移未启用(配置键 relocate.enabled)")


def build_router(ctx: WebContext) -> APIRouter:
    _enqueue = ctx.enqueue
    router = APIRouter()

    # ---- 「路由→命令」透传形状单点(issue route-cmd-boilerplate-dup) ----
    # 下列端点体此前逐字重复(仅命令名 / 字段名不同): mechanics(取参 / 构造载荷 / 投递)
    # 收敛到四个形状 helper, 端点本身只剩「路径 -> 命令」一行声明; 新增同类端点加一行
    # 调用, 不再照抄载荷构造。行为逐字不变(既有表驱动用例逐端点钉 cmd / payload)。

    def _cmd_hash(cmd: str, hash: str) -> dict:
        """hash 单参透传: pause / resume / reannounce / recheck 四端点同一形状"""
        return _enqueue(cmd, {"hash": hash})

    def _cmd_enable(cmd: str, hash: str, body: dict) -> dict:
        """enable 布尔透传: super_seeding / force_start / set_auto_tmm 三端点同一形状"""
        enable = bool((body or {}).get("enable", False))
        return _enqueue(cmd, {"hash": hash, "enable": enable})

    def _cmd_field(cmd: str, hash: str, body: dict, field: str, confirm: bool = False) -> dict:
        """单字符串字段透传: location / rename / queue / trackers-remove 四端点同一形状

        confirm=True 的端点(整组迁移的 location)才读 body.confirm —— 且仍按「提供才透传」,
        其余端点载荷形状与历史逐字节一致。
        """
        payload = {"hash": hash, field: str((body or {}).get(field) or "")}
        if confirm and (body or {}).get("confirm"):
            payload["confirm"] = True
        return _enqueue(cmd, payload)

    def _cmd_str_list(cmd: str, hash: str, body: dict, field: str) -> dict:
        """字符串列表字段透传: trackers/add(urls)"""
        return _enqueue(cmd, {"hash": hash, field: [str(u) for u in ((body or {}).get(field) or []) if u]})

    @router.post("/api/torrents/{hash}/pause")
    def api_t_pause(hash: str):
        return _cmd_hash("pause_torrent", hash)

    @router.post("/api/torrents/{hash}/resume")
    def api_t_resume(hash: str):
        return _cmd_hash("resume_torrent", hash)

    @router.post("/api/torrents/{hash}/reannounce")
    def api_t_reannounce(hash: str):
        return _cmd_hash("reannounce_torrent", hash)

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
        return _cmd_hash("recheck_torrent", hash)

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
        _require_skip_check(ctx)
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
        _require_skip_check(ctx)
        hashes = [str(h) for h in ((body or {}).get("hashes") or []) if h]
        if not hashes:
            raise HTTPException(status_code=400, detail="未提供任何 hash(预检目标不能为空)")
        return _enqueue("skip_check_precheck", {"hashes": hashes})

    # ---- 整组迁移预检(计划 26-10-18-1604 §3.6/P2, 只读) ----

    @router.post("/api/torrents/relocate/precheck")
    def api_relocate_precheck(body: dict = None):
        """整组迁移预检(只读 dry-run): 多选按组拆开逐组判定, 三分流(ok/confirm/blocked)
        供迁移确认框在用户确认前摊开「怎么迁、要确认什么、为什么拒」—— 执行路径(P3)
        闸门原样全跑, 预检-执行无信任传递

        挂 relocate.enabled 403 门控(fail-closed, 与跳检预检同口径); 经 _enqueue 走主循环
        线程执行 ctx.relocate.relocate_precheck(与写命令串行化, 快照无撕裂; 复用 cmd_id +
        waitCmd 既有通道)。body {hashes: [...], location: "..."}; 空 hashes / 空 location
        400 拒收不入队(同 skip-check 预检的路由层参数校验先例)。回执(经 cmd 通道):
        status=ok + truth={results: [逐组 item / gone 种子逐条], summary: {ok, confirm, blocked}}
        (summary 由命令层按单条 cls 计数)。
        """
        _require_relocate(ctx)
        hashes = [str(h) for h in ((body or {}).get("hashes") or []) if h]
        location = str((body or {}).get("location") or "").strip()
        if not hashes:
            raise HTTPException(status_code=400, detail="未提供任何 hash(预检目标不能为空)")
        if not location:
            raise HTTPException(status_code=400, detail="未提供目标位置(location 不能为空)")
        return _enqueue("relocate_precheck", {"hashes": hashes, "location": location})

    @router.post("/api/relocate/precheck-add")
    def api_relocate_precheck_add(body: dict = None):
        """添加种子落点预检(计划 26-10-18-1604 §3.6.1, 只读): 落点命中别名作用域时返回
        「请求路径 -> 实际落点 -> 目标卷剩余」供添加对话框二次确认; 无影响时静默放行

        body {save_path: "...", name: "<种子名>"}; 任一为空 400 拒收。回执(经 cmd 通道):
        status=ok + truth={cls, requested_path, actual_path, volume_free, reasons, notes}。
        """
        _require_relocate(ctx)
        save_path = str((body or {}).get("save_path") or "").strip()
        name = str((body or {}).get("name") or "").strip()
        if not save_path or not name:
            raise HTTPException(status_code=400, detail="save_path 与 name 均不能为空")
        return _enqueue("relocate_precheck_add", {"save_path": save_path, "name": name})

    @router.post("/api/relocate/cancel")
    def api_relocate_cancel(body: dict = None):
        """撤销迁移(计划 26-10-18-1604 §3.5.1): 删链接 + qB 搬回 —— 两步同口径,
        **不确认不动数据**(成本提示是模块内建契约, 不是前端自觉)

        挂 relocate.enabled 403 门控(fail-closed, 同预检端点); 经 _enqueue 走主循环线程
        执行 ctx.relocate.relocate_cancel(与写命令串行化)。body {job_id: "...", confirm: bool};
        job_id 空 400 拒收; confirm 缺省 = 只回成本(cls=confirm, cost 带字节数与搬回方向),
        confirm=true 才真正删链接 + setLocation(mover, src)。回执(经 cmd 通道):
        status=ok + truth=模块返回 item({cls, cost, job_id, phase} / blocked 带 reasons)。
        """
        _require_relocate(ctx)
        job_id = str((body or {}).get("job_id") or "").strip()
        if not job_id:
            raise HTTPException(status_code=400, detail="未提供 job_id(撤销目标不能为空)")
        return _enqueue("relocate_cancel", {"job_id": job_id, "confirm": bool((body or {}).get("confirm"))})

    @router.post("/api/torrents/{hash}/super-seeding")
    def api_t_super_seeding(hash: str, body: dict = None):
        return _cmd_enable("super_seeding", hash, body)

    @router.post("/api/torrents/{hash}/force-start")
    def api_t_force_start(hash: str, body: dict = None):
        return _cmd_enable("force_start", hash, body)

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
        """移动保存位置(整组迁移开时走闸门 + 别名执行体, 计划 26-10-18-1604 P5)

        confirm(目录别名的显式确认)按「提供才透传」入载荷 —— 缺省时队列形态与历史
        逐字节一致(既有载荷形态守阵依赖)。
        """
        return _cmd_field("set_torrent_location", hash, body, "location", confirm=True)

    @router.post("/api/torrents/{hash}/rename")
    def api_t_rename(hash: str, body: dict = None):
        return _cmd_field("rename_torrent", hash, body, "name")

    @router.post("/api/torrents/{hash}/queue")
    def api_t_queue(hash: str, body: dict = None):
        return _cmd_field("queue_torrent", hash, body, "action")

    @router.post("/api/torrents/{hash}/auto-tmm")
    def api_t_auto_tmm(hash: str, body: dict = None):
        return _cmd_enable("set_auto_tmm", hash, body)

    @router.post("/api/torrents/{hash}/trackers/add")
    def api_t_trackers_add(hash: str, body: dict = None):
        return _cmd_str_list("add_trackers", hash, body, "urls")

    @router.post("/api/torrents/{hash}/trackers/remove")
    def api_t_trackers_remove(hash: str, body: dict = None):
        # url = 前端所持 mask 值(详情 API 只回 mask); 后端 _cmd_remove_tracker 当场重取原文比对
        return _cmd_field("remove_tracker", hash, body, "url")

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
        # 整组迁移的目录别名确认(计划 26-10-18-1604 P5): 仅 location 动作透传 confirm,
        # 且同样「提供才透传」—— 缺省队列载荷与历史一致
        if action == "location" and b.get("confirm"):
            payload["confirm"] = True
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
