"""站点导入路由: `/api/sites/missing`(只读扫描)。

回答的问题: **qB 里有哪些种子来自还没配置的站点** —— 与 CLI `--export-yaml --only-missing`
同一套构件(`collect_all_tracker_hostnames` / `find_missing_domains` / `build_tracker_entry`),
把缺失域名连同默认条目一并返回, 前端填入配置编辑器**待审**(不落盘、不投递热重载;
保存仍走既有 PUT /api/config 的校验/备份/热重载路径, 示例值不未经审阅生效)。

只读: 只调 qB 查询接口, 不碰任务队列与 state_file, 不违反单一写线程假设。
"""

from fastapi import HTTPException
from fastapi import APIRouter

from ....core.exporter import (
    build_tracker_entry,
    collect_all_tracker_hostnames,
    collect_configured_domains,
    find_missing_domains,
    gen_tracker_name,
)
from ..context import WebContext


def build_router(ctx: WebContext) -> APIRouter:
    manager = ctx.manager
    _require_client = ctx.require_client
    router = APIRouter()

    @router.get("/api/sites/missing")
    def api_sites_missing():
        """扫描 qB 全部种子的 tracker 域名, 返回未配置站点与默认条目(只读)

        - 匹配口径与 CLI 导出一致: tracker 域名与已配置 domains 双向包含即视为已覆盖
        - 默认条目含占位限速(0KiB/s)与 hr 示例值, 与 --export-yaml 同源; 前端负责
          填入编辑器并提示用户核对后保存
        - 种子量大时本端点耗时随种子数线性增长(逐种查 tracker), 前端按钮置 loading
        """
        manager.touch_web_client()
        _require_client()  # 断连即 503: 绝不能拿空扫描结果冒充"没有缺失站点"
        try:
            torrents = manager.api.torrents_info()
            all_domains = collect_all_tracker_hostnames(manager.api)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"扫描 qB tracker 失败: {e}")
        missing = find_missing_domains(all_domains, collect_configured_domains(manager.config))

        taken = set(manager.config.trackers)
        sites = []
        for domain in sorted(missing):
            sites.append(
                {
                    "name": gen_tracker_name(domain, taken),
                    "domain": domain,
                    "entry": build_tracker_entry(domain)
                }
            )
        return {"torrents": len(torrents), "domains": len(all_domains), "sites": sites}

    return router
