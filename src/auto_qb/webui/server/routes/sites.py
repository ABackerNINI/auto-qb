"""站点导入路由: `/api/sites/missing`(只读扫描)。

回答的问题: **qB 里有哪些种子来自还没配置的站点** —— 与 CLI `--export-yaml --only-missing`
同一套构件(`collect_torrent_tracker_hostnames` / `find_missing_domains` / `build_tracker_entry`),
把缺失域名连同默认条目一并返回, 前端填入配置编辑器**待审**(不落盘、不投递热重载;
保存仍走既有 PUT /api/config 的校验/备份/热重载路径, 示例值不未经审阅生效)。

响应在逐域名 `sites` 之外追加 `groups`(计划 26-11-03-2337 M3): 与 CLI 合并导出同一套
分组构件(`group_missing_domains` / `build_merged_entry`), 同一颗种子共现的缺失域名并成
一组, name=代表站点名(与 CLI 同规则), domains=组内全域名 sorted, entry=合并默认条目
(与 sites 条目同源, 前端合并模式直接用); `sites` 保持逐域名
原形(加字段向后兼容, 前端按是否存在多域名组自适应引导)。

只读: 只调 qB 查询接口, 不碰任务队列与 state_file, 不违反单一写线程假设。
"""

from fastapi import HTTPException
from fastapi import APIRouter

from ....core.exporter import (
    build_merged_entry,
    build_tracker_entry,
    collect_configured_domains,
    collect_torrent_tracker_hostnames_with_failures,
    find_missing_domains,
    gen_tracker_name,
    group_missing_domains,
    tracker_scan_batch_failed,
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
        - groups 与 CLI 合并导出同规则: 同一颗种子共现的缺失域名并成一组, 代表名与合并
          entry 由 build_merged_entry 单点生成; sites 保持逐域名原形, 前端按组形态自适应引导
        - 批量失败(逐种 tracker 查询过半报错, qB 断连/重启等) -> 502 拒出结果, 不拿空集
          冒充「无缺失站点」误导前端分支1(issue 26-11-04-2347); 单种失败仍容忍为空集
        - 种子量大时本端点耗时随种子数线性增长(逐种查 tracker), 前端按钮置 loading
        """
        manager.web.touch()
        _require_client()  # 断连即 503: 绝不能拿空扫描结果冒充"没有缺失站点"
        try:
            torrents = manager.api.torrents_info()
            # 逐种集合保留(单种失败=空集), 并集就地算 —— 共现分组复用同一次逐种遍历;
            # 失败数一并带回, 过半失败的 502 在 try 外单列(不折进下方 except 二次包一层)
            torrent_sets, failed_count = collect_torrent_tracker_hostnames_with_failures(manager.api)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"扫描 qB tracker 失败: {e}")
        if tracker_scan_batch_failed(failed_count, len(torrent_sets)):
            raise HTTPException(
                status_code=502,
                detail=f"扫描 qB tracker 批量失败({failed_count}/{len(torrent_sets)} 颗种子查询报错), "
                f"结果不可信: 请检查 qB 状态后重试",
            )
        all_domains = set()
        for host_set in torrent_sets:
            all_domains |= host_set
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
        # groups: 与 CLI 合并导出同一套分组构件; 代表名按 CLI 同规则单独查重
        # (sites 与 groups 是两种互斥的导入形态, 不把 sites 占用的逐域名名带进组名查重),
        # 组内/组间均 sorted; entry 一并带上(build_merged_entry 单点产出, 前端合并模式直接用,
        # 不在 JS 复刻代表规则); 无缺失域名时 groups 为空数组
        groups = []
        taken_groups = set(manager.config.trackers)
        for group in group_missing_domains(torrent_sets, missing):
            name, entry = build_merged_entry(group, taken_groups)
            groups.append({"name": name, "domains": group, "entry": entry})
        return {"torrents": len(torrents), "domains": len(all_domains), "sites": sites, "groups": groups}

    return router
