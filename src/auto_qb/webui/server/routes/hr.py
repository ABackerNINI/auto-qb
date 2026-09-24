"""HR 在线核实状态路由: `/api/hr/status`(只读)。

回答的问题: **每个站点的 HR 数据现在到哪一步了** —— 通道通不通、数据多新、覆盖证明成不成立、
索引与回填进度、配额与熔断、以及「为什么现在不放行」。

❗与 `--hr-status` 同一口径: 字段全部来自 `hr.status` 层(单一事实源), 本端点**只读** ——
不取数、不加锁、不写盘, 不碰取数线程的任何状态(那是唯一写者)。要看「现在能不能取到数」得跑
`--hr-once`; 界面只回答「已落盘的数据是什么样」。
"""
import time
from typing import Dict, List

from fastapi import APIRouter

from ....hr.status import build_site_statuses
from ..context import WebContext


def build_router(ctx: WebContext) -> APIRouter:
    manager = ctx.manager
    router = APIRouter()

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
