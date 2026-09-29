"""HR 在线核实状态路由: `/api/hr/status`(只读)。

回答的问题: **每个站点的 HR 数据现在到哪一步了** —— 通道通不通、数据多新、覆盖证明成不成立、
索引与回填进度、配额与熔断、以及「为什么现在不放行」。

!与 `--hr-status` 同一口径: 字段全部来自 `hr.status` 层(单一事实源), 本端点**只读** ——
不取数、不加锁、不写盘, 不碰取数线程的任何状态(那是唯一写者)。要看「现在能不能取到数」得跑
`--hr-once`; 界面只回答「已落盘的数据是什么样」。
"""
import time
from typing import Dict, List

from fastapi import APIRouter, HTTPException

from ....hr.report import run_hr_confirm_empty
from ....hr.status import build_site_statuses
from ..context import WebContext


def build_router(ctx: WebContext) -> APIRouter:
    manager = ctx.manager
    router = APIRouter()

    @router.post("/api/hr/confirm-empty")
    def api_hr_confirm_empty(body: dict = None):
        """人工对账戳(§5.3): 确认站点账号 HR 清单确实为空(零行波恢复签发放行, 非零行自动失效)

        复用 CLI `--hr-confirm-empty` 的实现(run_hr_confirm_empty, 单点): 锁内写站点文件的
        empty_confirmed_at。写操作与正常实例靠站点锁互斥; 站点名必须已启用 hr_check。
        """
        manager.touch_web_client()
        b = body or {}
        site = str(b.get("site") or "").strip()
        if not site:
            raise HTTPException(status_code=400, detail="缺少 site 参数")
        conf = getattr(manager.config, "hr_check", None)
        if conf is None or not conf.enabled:
            raise HTTPException(status_code=400, detail="HR 在线核实未启用")
        enabled = {
            name
            for name, tc in manager.config.trackers.items() if tc.hr_check is not None and tc.hr_check.enabled
        }
        if site not in enabled:
            raise HTTPException(status_code=400, detail=f"站点 {site} 未启用 hr_check(已启用: {sorted(enabled)})")
        code = run_hr_confirm_empty(manager.config, [site])
        if code != 0:
            raise HTTPException(status_code=409, detail="写入失败(站点锁被占用或锁自检失败), 稍后再试")
        return {"ok": True, "site": site}

    @router.get("/api/hr/status")
    def api_hr_status():
        """HR 站点级状态快照(只读; 未启用时返回 enabled=false 供前端显示空态)

        `limit` 不设: 站点数是配置量(个位到十位数), 一次全给比让前端分页简单得多。
        """
        manager.touch_web_client()
        conf = getattr(manager.config, "hr_check", None)
        runtime = getattr(manager, "hr", None)
        service = getattr(runtime, "service", None)
        if conf is None or not conf.enabled or service is None:
            return {
                "enabled": False,
                "sites": [],
                "channel": {},
                "note": "HR 在线核实未启用(config.hr_check.enabled=false)" if conf is None or not conf.enabled else "取数线程未启动",
                "now": time.time(),
            }
        now = time.time()
        sites: List[Dict] = [st.to_dict() for st in build_site_statuses(service, now)]
        run = runtime.status()
        channel = run.channel
        return {
            "enabled": True,
            "sites": sites,
            "note": run.note,
            "now": now,
            "fetch_enabled": run.fetch_enabled,  # 本实例能不能主动抓(没有浏览器时只读别人抓的)
            "worker_running": run.worker_running,
            "poll_interval": run.poll_interval,
            "sites_dir": run.sites_dir,
            "shared_dir": run.shared_dir,
            "writer": run.writer,
            "view_revision": run.view_revision,
            "channel":
                {
                    "enabled": channel.enabled,
                    "listening": channel.listening,
                    "port": channel.port,
                    "endpoint": channel.endpoint,
                    "token_source": channel.token_source,
                    "last_contact_ts": channel.last_contact_ts,
                    "silent_for": channel.silent_for,
                    "pending": channel.pending,
                    "extensions_seen": list(channel.extensions_seen),
                    "note": channel.note,
                } if channel is not None else {},
        }

    return router
