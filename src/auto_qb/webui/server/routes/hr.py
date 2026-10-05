"""HR 在线核实状态路由: `/api/hr/status`(只读) / `/api/hr/refresh`(立即拉取, 计划 26-09-30-0240)
/ `/api/hr/history`(拉取历史, 计划 26-10-04-0312 §3.4)。

回答的问题: **每个站点的 HR 数据现在到哪一步了** —— 通道通不通、数据多新、覆盖证明成不成立、
索引与回填进度、配额与熔断、以及「为什么现在不放行」。

!与 `--hr-status` 同一口径: 字段全部来自 `hr.status` 层(单一事实源), 本端点**只读** ——
不取数、不加锁、不写盘, 不碰取数线程的任何状态(那是唯一写者)。要看「现在能不能取到数」得跑
`--hr-once`; 界面只回答「已落盘的数据是什么样」。
`/api/hr/refresh` 是唯一的写通路, 但也只到「置一次性 force 旗标 + 唤醒取数线程」为止
(manager.hr.request_refresh 单点, 与插件端点同一实现) —— 取数仍由取数线程串行执行。
"""
import time
from typing import Any, Dict, List, Mapping

from fastapi import APIRouter, HTTPException

from ....hr.model import HISTORY_CAP, HrSiteData
from ....hr.report import run_hr_confirm_empty
from ....hr.status import build_site_statuses, entry_details, history_rows
from ..context import WebContext


def mark_local_present(rows: List[Dict], by_hash: Mapping[str, Any]) -> None:
    """给明细行追加只读布尔字段 `local_present`(计划 26-10-02-1936 §3.3, 决策点③a) —— join 口径钉在本路由层

    - `local_present` = **本地库存在该种子**(不区分 state 细类): 暂停/异常的 HR 种子仍是
      义务对象, 折进「已删除」会造成「已无义务」错觉; 本地不存在 = 已删除(含本地从未下载的清单行);
      (前端可见文案 = 「显示已删除种子 / 只看本地仍在列」, 2026-10-03 §8 B1 二次修订定)
    - 键探测按 infohash_v1 -> v2 顺序(任一命中即算), 大小写无关(站点清单与 qB hash 的书写
      形态可能不同, hex 语义等价);
    - 纯响应层展示标记: 不落盘、不进 /api/state 轮询载荷, 不影响任何判定/取数调度;
      `entry_details()` 本体保持纯站点口径(不加本地字段)。
    """
    # 读侧快照(同 views._build_group_view 处说明, issue 26-10-06-0028 E-01): 本函数在
    # /api/hr/* Web 请求线程上执行, 迭代 store.by_hash 与主循环原地增删并发, 取快照后再迭代
    local = {h.casefold() for h in tuple(by_hash)}
    for row in rows:
        row["local_present"] = any(
            h and h.casefold() in local for h in (row.get("infohash_v1") or "", row.get("infohash_v2") or "")
        )


def build_router(ctx: WebContext) -> APIRouter:
    manager = ctx.manager
    router = APIRouter()

    @router.post("/api/hr/confirm-empty")
    def api_hr_confirm_empty(body: dict = None):
        """人工对账戳(§5.3): 确认站点账号 HR 清单确实为空(零行波恢复签发放行, 非零行自动失效)

        复用 CLI `--hr-confirm-empty` 的实现(run_hr_confirm_empty, 单点): 锁内写站点文件的
        empty_confirmed_at。写操作与正常实例靠站点锁互斥; 站点名必须已启用 hr_check。
        """
        manager.web.touch()
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

    @router.post("/api/hr/refresh")
    def api_hr_refresh(body: dict = None):
        """立即拉取(计划 26-09-30-0240): 请求后端跳过复用窗与拉取间隔立即开波(频控仍生效)

        body 可带 site 单站触发; 缺省 = 全部启用站点。与插件端点同一实现
        (manager.hr.request_refresh 单点); 线程未启动回 409(不是错误形态, 是「现在拉不了」)。
        """
        manager.web.touch()
        runtime = getattr(manager, "hr", None)
        if runtime is None:
            raise HTTPException(status_code=409, detail="HR 取数线程未启动")
        conf = getattr(manager.config, "hr_check", None)
        if conf is None or not conf.enabled:
            raise HTTPException(status_code=400, detail="HR 在线核实未启用")
        b = body or {}
        site = str(b.get("site") or "").strip()
        sites = None
        if site:
            enabled = {
                name
                for name, tc in manager.config.trackers.items() if tc.hr_check is not None and tc.hr_check.enabled
            }
            if site not in enabled:
                raise HTTPException(status_code=400, detail=f"站点 {site} 未启用 hr_check(已启用: {sorted(enabled)})")
            sites = [site]
        outcome = runtime.request_refresh(sites)
        requested = list(outcome.get("requested") or [])
        if not requested and outcome.get("note"):
            # 线程未启动 / 受理清单为空: 如实回 409, 让按钮亮出原因而不是假装成功
            raise HTTPException(status_code=409, detail=str(outcome["note"]))
        return {"ok": True, "requested": requested, "note": outcome.get("note") or ""}

    @router.get("/api/hr/status")
    def api_hr_status():
        """HR 站点级状态快照(只读; 未启用时返回 enabled=false 供前端显示空态)

        `limit` 不设: 站点数是配置量(个位到十位数), 一次全给比让前端分页简单得多。
        """
        manager.web.touch()
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

    @router.get("/api/hr/sites/{site}/entries")
    def api_hr_site_entries(site: str):
        """站点种子明细(只读; 计划 26-10-01-2216 §7 阶段1, 表① 全量详情表的数据源)

        决策点②(b): 新端点按站点按需拉 —— 逐种子明细是「打开才需要」的数据, 不进 /api/state
        轮询载荷也不塞进 /api/hr/status 全量响应。校验与 confirm-empty 同款(总开关未启用 400);
        站点未接入是路径层面的不存在, 回 404 并点名已接入清单。数据读取与 --hr-status 同款
        只读口径(store.read_unlocked), 字段全部来自 hr.status.entry_details 单点(含失踪行,
        排序与人话均由后端算好); 站点文件读坏不抛, read_error 原样带出。
        local_present 为响应层追加的只读标记(mark_local_present 单点, 计划 26-10-02-1936
        决策点③a), entry_details 本体保持纯站点口径。
        """
        manager.web.touch()
        conf = getattr(manager.config, "hr_check", None)
        if conf is None or not conf.enabled:
            raise HTTPException(status_code=400, detail="HR 在线核实未启用")
        enabled = {
            name
            for name, tc in manager.config.trackers.items() if tc.hr_check is not None and tc.hr_check.enabled
        }
        if site not in enabled:
            raise HTTPException(status_code=404, detail=f"站点 {site} 未接入 hr_check(已接入: {sorted(enabled)})")
        runtime = getattr(manager, "hr", None)
        service = getattr(runtime, "service", None)
        if service is None:
            raise HTTPException(status_code=409, detail="HR 取数线程未启动")
        data, err = service.store(site).read_unlocked()
        rows = [d.to_dict() for d in entry_details(data)]
        mark_local_present(rows, manager.store.by_hash)
        return {
            "site": site,
            "entries": rows,
            "read_error": err or "",
            "now": time.time(),
        }

    @router.get("/api/hr/history")
    def api_hr_history(limit: int = 300, site: str = ""):
        """拉取历史时间轴(只读; 计划 26-10-04-0312 §3.4, 表③ 的数据源)

        校验与 /api/hr/sites/{site}/entries 同款: 总开关未启用 400、取数线程未启动 409;
        site 可选过滤(给了就只回该站; 未接入是路径层面的不存在, 404 点名已接入清单)。
        数据读取与 --hr-status 同款只读口径(逐站 store.read_unlocked 无锁只读): 写入是
        原子替换, 无锁读到的必然是完整一份; 读坏不抛, read_errors{site: err} 原样带出
        (坏文件本身就是要人看的信息, 表① 同款)。行字段全部来自 hr.status.history_rows
        单点 —— 跨站合并 / ts 降序 / 截 limit 与全部人话徽章都由后端算好, 前端只展示。
        limit 钳进 [1, HISTORY_CAP]: 查询参数卫生, 空页与不设防的全量都没意义。
        """
        manager.web.touch()
        conf = getattr(manager.config, "hr_check", None)
        if conf is None or not conf.enabled:
            raise HTTPException(status_code=400, detail="HR 在线核实未启用")
        runtime = getattr(manager, "hr", None)
        service = getattr(runtime, "service", None)
        if service is None:
            raise HTTPException(status_code=409, detail="HR 取数线程未启动")
        site = str(site or "").strip()
        if site:
            enabled = {
                name
                for name, tc in manager.config.trackers.items() if tc.hr_check is not None and tc.hr_check.enabled
            }
            if site not in enabled:
                raise HTTPException(status_code=404, detail=f"站点 {site} 未接入 hr_check(已接入: {sorted(enabled)})")
            names: List[str] = [site]
        else:
            names = list(service.enabled_sites())
        datas: Dict[str, HrSiteData] = {}
        read_errors: Dict[str, str] = {}
        for name in names:
            data, err = service.store(name).read_unlocked()
            if err:
                read_errors[name] = err
            else:
                datas[name] = data
        now = time.time()
        rows = [row.to_dict() for row in history_rows(datas, max(1, min(int(limit), HISTORY_CAP)), now)]
        return {"enabled": True, "rows": rows, "read_errors": read_errors, "now": now}

    return router
