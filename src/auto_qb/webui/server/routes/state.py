"""状态聚合读路由: /api/status · /api/state · /api/groups · /api/search · /api/stats · /api/traffic/history.

端点体逐字平移(plan 26-09-22-1857 W2); 仅 @app.* → @router.* 与共享件别名(原闭包名不变)。
鉴权由 factory 的全局 dependencies 单点覆盖, 本模块不另挂依赖。
日志命名空间见包 __init__(K3)。"""

from fastapi.responses import JSONResponse

from ..common import app_version as _app_version

from fastapi import APIRouter
from ..context import WebContext


def build_router(ctx: WebContext) -> APIRouter:
    manager = ctx.manager
    router = APIRouter()

    @router.get("/api/status")
    def api_status():
        manager.touch_web_client()
        snap = manager.status_snapshot()
        return {
            "connected": snap["connected"],
            "paused": snap["paused"],
            "torrents": snap["torrents"],
            "groups": len(manager._group_view),
            "version": _app_version(),
            "traffic": manager._traffic_view,
        }

    @router.get("/api/state")
    def api_state(rid: int = -1, view: str = ""):
        """合并端点: status + groups 一次返回(前端单请求轮询, 请求数减半)

        rid 为前端已持有的分组视图版本: 版本一致时只回 status(体积极小), 数组不回传,
        前端据此跳过整表替换与重渲染; rid 缺省/不匹配时回传全量分组数据。

        view(P1-1): 当前视图名(group/torrent/show), 只回传该视图需要的数组 —— 大库下
        响应体降到约 1/4(序列化/网络/JSON.parse 与重渲染成本同步下降)。
        缺省或未知值 ⇒ 回传四份(保守默认, 老客户端不受影响)。
        """
        manager.touch_web_client()
        snap = manager.status_snapshot()
        # ❗**先**取分组状态再拼 status: ensure_group_state 才是真正触发"视图发布"的地方
        # (脏则重建四视图 + 速度合计)。若把它写在 status 字典之后(作为 `**` 展开项),
        # 字典字面量会**先**求值 ⇒ 读到的是上一轮的旧值: 首次请求拿到全 0, 之后每轮慢一拍。
        group_state = manager.ensure_group_state(rid, view or None)
        payload = {
            "status":
                {
                    "connected": snap["connected"],
                    "paused": snap["paused"],
                    "torrents": snap["torrents"],
                    "groups": len(manager._group_view),
                    "version": _app_version(),
                    # 限速/流量快照: 恒回传(不受 rid 门控) —— 数据源是限速曲线任务而非分组视图,
                    # 若参与版本门控会与 groups 的脏语义耦合, 反而可能长时间不刷新
                    "traffic": manager._traffic_view,
                    # qB 全局状态(server_state: 连接状态/全局速度/累计流量/磁盘剩余等)。
                    # 与 traffic 同为"恒回传"口径: 数据源是 sync 快照而非分组视图, 不参与
                    # rid 门控。此前前端状态栏要为此**单独再打一次 /api/stats**, 两条链路
                    # 刷新频率不同 ⇒ 出现"状态栏速度正常、种子行速度滞后"的错位观测;
                    # 合并后每轮只剩 1 条请求, 且两者同源同轮。
                    "server": manager.store.server_state,
                    # 全量种子的上传/下载速度合计(状态栏常显统计): 与 traffic / server 同为
                    # "恒回传"口径 —— ❗**不参与 VIEW_ARRAYS 视图分片、不受 rid 门控**。
                    # 状态栏是跨视图的常驻显示, 一旦让它去读按视图裁剪的数组(旧实现对 groups
                    # 求和), 种子页就会恒显示 0(issue 26-09-20-1646); 服务端算好标量再回传,
                    # 前端只读这一个值, 彻底与视图分片解耦。
                    "totals": manager.web.speed_totals,
                },
            **group_state,
        }
        # ⚡ 直接返回 JSONResponse, **不要**返回裸 dict: FastAPI 对普通返回值会先跑一遍
        # `jsonable_encoder` 递归遍历整个响应体 —— 实测 3000 种子 `view=torrent` 时它要
        # **161 ms**, 占端点总耗时 189 ms 的 85%(中间件实测), 而我们的视图本来就是 JSON 原生
        # 类型(str/int/float/bool/None/dict/list), 这趟遍历纯属白跑, 还全程占着 GIL
        # (与主循环抢 CPU ⇒ 大库下"点了没反应"的一个真实来源)。
        # 返回 Response 实例会被 FastAPI 短路(fastapi/routing.py: `isinstance(raw_response, Response)`
        # ⇒ 跳过 serialize_response), 只付 json.dumps 的钱(实测 25~50 ms)。**输出字节完全一致**。
        # ⚠ 代价: 若日后往 payload 里塞了非 JSON 原生类型(datetime/set/Decimal), 这里会**直接
        # 抛 TypeError 变 500**(fail-fast), 而不是被静默转成字符串 —— 加字段时注意。
        return JSONResponse(content=payload)

    @router.get("/api/groups")
    def api_groups():
        manager.touch_web_client()
        # 同 /api/state: 返回裸 dict 会让 FastAPI 白跑一遍 jsonable_encoder(见那里的注释)
        return JSONResponse(content={"groups": manager.ensure_group_view()})

    @router.get("/api/search")
    def api_search(q: str = ""):
        """按种子名/文件列表搜索种子(主循环构建的缓存索引, Web 线程只读; 索引脏时投递构建命令)"""
        manager.touch_web_client()
        return JSONResponse(content=manager.search_torrents(q))

    @router.get("/api/stats")
    def api_stats():
        """qB 全局状态(sync/maindata 的 server_state: 会话/累计流量/DHT 节点/连接状态等)

        数据源是主循环增量同步时原子替换的只读引用; 降级全量(无 sync 端点)或
        尚未同步到响应时为 null, 前端按空态渲染。
        """
        manager.touch_web_client()
        return {"server": manager.store.server_state}

    @router.get("/api/traffic/history")
    def api_traffic_history():
        """历史流量按日行(dat 原始数据, 升序): 供前端历史流量柱状图按天/月/年聚合

        数据源是限速曲线任务每轮发布的只读快照(_traffic_view["history"]), Web 线程只读;
        未启用限速曲线或数据源不可用时 history 为空数组, state 供前端判断展示分支。
        """
        manager.touch_web_client()
        view = manager._traffic_view
        return {"state": view.get("state"), "history": view.get("history") or []}

    return router
