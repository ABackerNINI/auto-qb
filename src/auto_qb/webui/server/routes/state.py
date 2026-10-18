"""状态聚合读路由: /api/status · /api/state · /api/groups · /api/search · /api/stats · /api/traffic/history · /api/traffic/qb/global.

端点体逐字平移(plan 26-09-22-1857 W2); 仅 @app.* → @router.* 与共享件别名(原闭包名不变)。
鉴权由 factory 的全局 dependencies 单点覆盖, 本模块不另挂依赖。
日志命名空间见包 __init__(K3)。"""

from fastapi.responses import JSONResponse

from ...runtime import public_traffic_view
from ..common import app_version as _app_version
from ..traffic_qb import QbTrafficChartApi as _QbTrafficChartApi

from fastapi import APIRouter
from ..context import WebContext


def _status_payload(manager, snap: dict) -> dict:
    """status 子字典单点(issue webui-status-payload-dup): /api/status 与 /api/state 共用前 6 字段

    此前两个端点各拼一份(逐字同), 新增/改名状态字段要记得改两处, 漏一处即两接口口径漂移。
    !调用时机: `groups`/`traffic` 读的是 Web 运行时视图, `snap` 由调用方**先**取好再传进来 ——
      /api/state 侧必须先跑 `ensure_state`(真正触发视图发布的地方)再进本函数, 否则读到上一轮旧值
      (求值顺序口径见 api_state 内的注释)。
    !`traffic` 经 public_traffic_view 摘掉 history(计划 26-10-18-0813 A5/D5): 历史行走
      /api/traffic/history 专用端点, 轮询每轮背几百行纯浪费。
    """
    return {
        "connected": snap["connected"],
        "paused": snap["paused"],
        "torrents": snap["torrents"],
        "groups": len(manager.web.group_view),
        "version": _app_version(),
        "traffic": public_traffic_view(manager.web.traffic_view),
    }


def build_router(ctx: WebContext) -> APIRouter:
    manager = ctx.manager
    _qb_traffic = _QbTrafficChartApi(manager)
    router = APIRouter()

    @router.get("/api/status")
    def api_status():
        manager.web.touch()
        snap = manager.status_snapshot()
        return _status_payload(manager, snap)

    @router.get("/api/state")
    def api_state(rid: int = -1, view: str = "", delta: int = 0):
        """合并端点: status + groups 一次返回(前端单请求轮询, 请求数减半)

        rid 为前端已持有的分组视图版本: 版本一致时只回 status(体积极小), 数组不回传,
        前端据此跳过整表替换与重渲染; rid 缺省/不匹配时回传全量分组数据。

        view(P1-1): 当前视图名(group/torrent/show), 只回传该视图需要的数组 —— 大库下
        响应体降到约 1/4(序列化/网络/JSON.parse 与重渲染成本同步下降)。
        缺省或未知值 ⇒ 回传四份(保守默认, 老客户端不受影响)。

        delta(plan 26-10-07-0414 S3 协商参数, P-01 定案): 请求带 delta=1 声明客户端懂
        增量协议 —— rid 落在服务端时间线窗口内时回增量载荷(full=false + delta/removed),
        否则回全量并标 full=true; **不带或非 1 恒回历史形状的全量**(无 full 键), 未升级
        前端逐字节兼容, S3/S4 各自独立提交/回滚。启用矩阵 group/torrent, show 恒全量。
        """
        manager.web.touch()
        snap = manager.status_snapshot()
        # !**先**取分组状态再拼 status: ensure_state 才是真正触发"视图发布"的地方
        # (脏则重建四视图 + 速度合计)。若把它写在 status 字典之后(作为 `**` 展开项),
        # 字典字面量会**先**求值 ⇒ 读到的是上一轮的旧值: 首次请求拿到全 0, 之后每轮慢一拍。
        group_state = manager.web.ensure_state(rid, view or None, delta == 1)
        payload = {
            "status":
                {
                    # 前 6 字段(含 traffic: 限速/流量快照, 恒回传 —— 数据源是限速曲线任务而非
                    # 分组视图, 若参与版本门控会与 groups 的脏语义耦合, 反而可能长时间不刷新)
                    # 与 /api/status 同源(单点 _status_payload); 下面是 /api/state 专属段
                    **_status_payload(manager, snap),
                    # qB 全局状态(server_state: 连接状态/全局速度/累计流量/磁盘剩余等)。
                    # 与 traffic 同为"恒回传"口径: 数据源是 sync 快照而非分组视图, 不参与
                    # rid 门控。此前前端状态栏要为此**单独再打一次 /api/stats**, 两条链路
                    # 刷新频率不同 ⇒ 出现"状态栏速度正常、种子行速度滞后"的错位观测;
                    # 合并后每轮只剩 1 条请求, 且两者同源同轮。
                    "server":
                        manager.store.server_state,
                    # 全量种子的上传/下载速度合计(状态栏常显统计): 与 traffic / server 同为
                    # "恒回传"口径 —— !**不参与 VIEW_ARRAYS 视图分片、不受 rid 门控**。
                    # 状态栏是跨视图的常驻显示, 一旦让它去读按视图裁剪的数组(旧实现对 groups
                    # 求和), 种子页就会恒显示 0(issue 26-09-20-1646); 服务端算好标量再回传,
                    # 前端只读这一个值, 彻底与视图分片解耦。
                    "totals":
                        manager.web.speed_totals,
                },
            **group_state,
        }
        # [!] 直接返回 JSONResponse, **不要**返回裸 dict: FastAPI 对普通返回值会先跑一遍
        # `jsonable_encoder` 递归遍历整个响应体 —— 实测 3000 种子 `view=torrent` 时它要
        # **161 ms**, 占端点总耗时 189 ms 的 85%(中间件实测), 而我们的视图本来就是 JSON 原生
        # 类型(str/int/float/bool/None/dict/list), 这趟遍历纯属白跑, 还全程占着 GIL
        # (与主循环抢 CPU ⇒ 大库下"点了没反应"的一个真实来源)。
        # 返回 Response 实例会被 FastAPI 短路(fastapi/routing.py: `isinstance(raw_response, Response)`
        # ⇒ 跳过 serialize_response), 只付 json.dumps 的钱(实测 25~50 ms)。**输出字节完全一致**。
        # WARN: 代价: 若日后往 payload 里塞了非 JSON 原生类型(datetime/set/Decimal), 这里会**直接
        # 抛 TypeError 变 500**(fail-fast), 而不是被静默转成字符串 —— 加字段时注意。
        return JSONResponse(content=payload)

    @router.get("/api/groups")
    def api_groups():
        manager.web.touch()
        # 同 /api/state: 返回裸 dict 会让 FastAPI 白跑一遍 jsonable_encoder(见那里的注释)
        return JSONResponse(content={"groups": manager.web.ensure_view()})

    @router.get("/api/search")
    def api_search(q: str = ""):
        """按种子名/文件列表搜索种子(主循环构建的缓存索引, Web 线程只读; 索引脏时投递构建命令)"""
        manager.web.touch()
        return JSONResponse(content=manager.search_torrents(q))

    @router.get("/api/stats")
    def api_stats():
        """qB 全局状态(sync/maindata 的 server_state: 会话/累计流量/DHT 节点/连接状态等)

        数据源是主循环增量同步时原子替换的只读引用; 降级全量(无 sync 端点)或
        尚未同步到响应时为 null, 前端按空态渲染。
        """
        manager.web.touch()
        return {"server": manager.store.server_state}

    @router.get("/api/traffic/history")
    def api_traffic_history():
        """历史流量按日行(dat 原始数据, 升序): 供前端历史流量柱状图按天/月/年聚合

        数据源是 traffic_snapshot 模块按来源节奏发布的只读快照(history 段), Web 线程只读;
        数据源不可用时 history 为空数组(来源态 stale), 来源关闭时为空且 state="off" ——
        state 供前端判断空态文案分支。**本端点是 history 的唯一出口**: 轮询载荷里的 traffic
        已被 public_traffic_view 摘掉该键(计划 26-10-18-0813 A5)。
        """
        manager.web.touch()
        view = manager.web.traffic_view
        return {"state": view.get("state"), "history": view.get("history") or []}

    @router.get("/api/traffic/qb/global")
    def api_traffic_qb_global(window: str = "24h"):
        """qB 口径全局流量时序(plan 26-10-03-0946 §08, P4; v3 翻转 plan 26-10-04-1957 S3b):
        qb-traffic-v4/global/ 天文件 + agg.dat 读侧栅格离散

        与 /api/traffic/history(TM 口径按日聚合)同域对照; 窗口 WINDOW_NAMES 十三档
        (1m-30d + 6mo/1y/all, D4; 缺省 24h), 响应形状与单种/分组端点一致
        (装配单点在 server/traffic_qb.py)。
        JSONResponse 直出(24h 窗 ≈2880 点, 跳过 jsonable_encoder 遍历 —— 同 /api/state 的口径)。
        """
        manager.web.touch()
        return JSONResponse(content=_qb_traffic.payload_global(window))

    return router
