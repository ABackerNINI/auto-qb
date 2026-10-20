"""全局流量来源(工具 gtm)联动路由(计划 26-10-16-0541 S6 代理面 + S7 接收面; 26-10-17-0339 S17 收编到来源单点).

端点(路径沿用既有 `/api/traffic/monitor/*`; 语义已从「一段独立联动配置」收编为「traffic_source 的
global_traffic_monitor 来源面」, 设置页里合并进同一张「全局流量来源」卡):
  GET  /api/traffic/monitor/status    工具状态区(只读): 五态(agent 指针探测) + 就绪时附工具 /status 回显
  PUT  /api/traffic/monitor/config    工具 PUT /config 代理(全量覆盖 -> 前端「读后写」)
  POST /api/traffic/monitor/autostart 工具 POST /autostart 代理(幂等注册/卸载开机自启)
  POST /api/traffic/monitor/relaunch  「立即拉起/重试」: 促订阅线程立刻重跑一轮并忽略失败退避
  POST /api/traffic/monitor/claim    「以本安装重登记」(D4/D5): 有界前台跑安装内 claim 启动器(人工易主)
  POST /api/traffic/monitor/shutdown  停止工具: 代理工具 POST /shutdown(S3, 26-10-17-1737)
  POST /api/traffic/monitor/notify    **接收面**(S7): 工具推送的累计流量阈值事件
    (26-10-21 起: 事件自带权威累计 -> 主循环零读盘补丁今日流量, 不再触发读盘)

auto-qb 与工具是两个进程、两个 venv: 本模块是唯一桥 —— 用 stdlib urllib 带 Bearer token
调工具控制面(地址/密钥不再来自配置, 而是 **agent 读工具指针**得的 host/port/token_path)。
HTTP 与密钥定位的单点在 `...tool_client` 与 `...core.traffic_source.agent`(与订阅客户端共用),
**不 import 工具包**, 只经 HTTP 契约通信(与架构图一致)。

S17(计划 26-10-17-0339)收编要点:
- 配置单点从旧顶层过渡桩段 `global_traffic_monitor` 改读 `manager.config.traffic_source.global_traffic_monitor`
  (该桩段已随 S17 退休, D2/D17);
- 地址/密钥改由 `manager.host.get("webui").agent`(与订阅客户端同一实例)给出 —— 与订阅同源, 不各算各的。

错误口径(两段不同, 各有理由):
- `GET /status` 是**展示端点** —— 工具没在跑也要能显示「为什么」, 故恒 200 + 结构化空态
  (`reachable=false` + `state`/`error`), 不抛 5xx(否则设置页只能看到一片红)。
- `PUT /config` / `POST /autostart` / `POST /relaunch` 是**写端点** —— 失败必须真报错(前端据此提示),
  工具 400 原样透传(校验错误逐条可见), 上游 5xx / 不可达收口为 502, 平台不支持透传 501;
  工具未就绪时写端点收口为 502 并附 `state`(控制面是工具进程内的, 不在跑就没得写)。
- `POST /notify` 的对话方是**工具进程**而非浏览器(见端点内注释): 鉴权仍复用全局
  `make_require_token`(订阅时给工具的凭证 = 本实例 WEB 访问密钥), 但响应一律 200 + action,
  只有事件体本身非法才 400 —— 工具侧把非 2xx 记成推送失败并 WARNING, 闸门拦下的通知不该
  伪装成故障。
"""
from __future__ import annotations

import logging
import math
import threading
from datetime import date

from fastapi import APIRouter, HTTPException

# 工具控制面客户端单点(与订阅客户端 webui/tool_client.py 共用; 别名保持本模块既有名字,
# 既有的路由守阵按 `tm_routes._call_tool` / `tm_routes.ToolUnreachable` 打桩)
from ....core.traffic_source import paths as traffic_paths
from ....core.traffic_source.agent import resolve_claim_target as _resolve_claim_target
from ....core.traffic_source.agent import run_claim as _run_claim
from ...tool_client import NOTIFY_PATH
from ...tool_client import ToolUnreachable
from ...tool_client import call_tool as _call_tool
from ...tool_client import error_text as _error_text
from ...tool_client import read_token as _read_token
from ..context import WebContext

logger = logging.getLogger("auto_qb.web")  # K3: server 包内 logger 名冻结


def _tm_conf(manager):
    """来源参数读取单点(S17): traffic_source.global_traffic_monitor(段恒在, 缺省 enabled=false)"""
    return manager.config.traffic_source.global_traffic_monitor


def _webui_module(manager):
    """工具发现/拉起单点的宿主模块(与订阅客户端同实例); 缺失 -> 502(不静默空转)"""
    mod = manager.host.get("webui")
    if mod is None:
        raise HTTPException(status_code=502, detail="webui 模块未注册(读不到工具状态/拉起通道)")
    return mod


def _provider(manager) -> str:
    """当前生效来源(D1 单一开关): traffic_source.provider; 取不到时回退 traffic_monitor

    S17 退休了旧的 global_traffic_monitor.enabled 键 —— 「联动是否启用」不再是独立配置键,
    而是由 provider 指向谁决定(严格互斥)。
    """
    ts = getattr(manager.config, "traffic_source", None)
    return (getattr(ts, "provider", None) or "traffic_monitor")


def _source_status(manager) -> dict:
    """状态区载荷组装单点: 五态(agent 指针探测) + 就绪时附工具 /status 回显

    - `endpoint` 是 agent 内部对象, 对外换成扁平的 tool_url/token_path;
    - state==ready 但拿不到密钥 / 控制面 502 -> 降级为 not_running(展示端点不抛 5xx)。
    """
    conf = _tm_conf(manager)
    st = _webui_module(manager).agent.status(conf)
    ep = st.pop("endpoint", None)
    base = {
        "enabled": _provider(manager) == "global_traffic_monitor",
        "state": st["state"],
        "reachable": st["state"] == "ready",
        "tool_url": ep.base_url if ep else "",
        "token_path": ep.token_path if ep else "",
        "version": st["version"],
        "pid": st["pid"],
        "data_dir": st["data_dir"],
        "autostart_registered": st["autostart_registered"],
        "autostart_error": st["autostart_error"],
        "error": st["error"],
        "retry_s": st["retry_s"],
        # 让位/被拒注记(D7): 工具侧书写, auto-qb 只读展示; 缺失 -> null
        "claim_note": st["claim_note"],
        "status": None,
    }
    if not base["reachable"]:
        return base
    token = _read_token(base["token_path"])
    if not token:
        base.update(reachable=False, state="not_running", error=f"工具密钥文件不存在或为空: {base['token_path']}(工具未启动过?)")
        return base
    try:
        code, payload = _call_tool(base["tool_url"], "/status", "GET", token)
    except ToolUnreachable as e:
        base.update(reachable=False, state="not_running", error=str(e))
        return base
    if code == 200:
        base["status"] = payload
    else:
        base["error"] = f"工具 /status 返回 {code}: {_error_text(payload, code)}"
    return base


def _ready_endpoint(manager):
    """写端点前置: 工具就绪才谈得上写控制面 -> (base_url, token) 或抛 502(附 state/原因)"""
    st = _source_status(manager)
    if not st["reachable"]:
        raise HTTPException(status_code=502, detail=f"工具未在运行({st['state']}): {st['error'] or '先在卡片点「立即拉起」'}")
    token = _read_token(st["token_path"])
    if not token:
        raise HTTPException(status_code=502, detail=f"工具密钥文件不存在或为空: {st['token_path']}")
    return st["tool_url"], token


class NotifyGate:
    """通知接收闸: 事件号单调去重(计划 26-10-16-0541 S7; 26-10-21 冷却退役)

    状态是 **per app 实例**的(与 auth 的「免鉴权只记一次」同款: 测试会对同一 manager
    多次 create_app, 不得提升为模块级全局):

    - **事件号**: 记「已接受的最大事件号」, 小于等于它的一律丢(重复投递 / 乱序到达)。
      重启后归零 —— 工具的下一条事件即放行, 冷启动后的第一次补丁不会被自己挡住。

    **为什么退役了冷却**(原 notify_cooldown_s, 26-10-21 用户拍板「读盘本身就是副作用, 要尽量
    减少读盘; 事件基本无副作用应立即刷新」): 事件不再触发任何读盘 —— 它只把自带权威累计
    补丁进快照(traffic_snapshot.publish_event, 一次内存发布), 无成本可节流; 冷却防的
    「刷新风暴」在零读盘下并不存在, 留下的只有滞后(状态栏「今日流量」曾因此比设置页工具
    状态旧数分钟)。配置键 notify_cooldown_s 保留(校验/读入照旧)仅为兼容旧配置, 取值不再
    被读取。

    纯内存、不落盘: 丢了通知只等于「晚一次兜底读盘」—— 文件一直在写, refresh_interval
    定时任务兜底, 与工具侧「推送失败不阻断落盘」互为冗余(§03 核心不变量)。Web 线程池
    并发调用 -> 加锁。
    """
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._last_event_id = -1

    def verdict(self, event_id: int) -> tuple:
        """-> (是否放行补丁, 原因: "" = 放行 / duplicate)"""
        with self._lock:
            if event_id <= self._last_event_id:
                return False, "duplicate"
            self._last_event_id = event_id
            return True, ""


def _parse_notify_event(body) -> dict:
    """校验工具事件体(六键, 计划 §04 S4 拍板结论) -> 归一化事件; 非法 -> 400 逐条报错

    全键校验的理由是**契约漂移必须响亮**: 工具换了键名/单位(如把 KB 当 bytes)时, 少键或形状
    不对要在接收面直接报错, 而不是按缺省 0 静默记账(那会让刷新链路「看起来正常但永远不触发」)。
    """
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="事件体必须是 JSON 对象")
    bad = []
    event_id = body.get("event_id")
    if isinstance(event_id, bool) or not isinstance(event_id, int) or event_id < 0:
        bad.append("event_id: 期望非负整数")
    day = body.get("day")
    if not isinstance(day, str) or not day.strip():
        bad.append("day: 期望非空字符串(YYYY-MM-DD)")
    numbers = {}
    for key in ("up_bytes", "down_bytes", "total_bytes"):
        value = body.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            bad.append(f"{key}: 期望非负数字")
        else:
            numbers[key] = value
    ts = body.get("ts")
    if isinstance(ts, bool) or not isinstance(ts, (int, float)) or not math.isfinite(ts) or ts <= 0:
        bad.append("ts: 期望正数(epoch 秒)")
    if bad:
        raise HTTPException(status_code=400, detail="; ".join(bad))
    return {"event_id": event_id, "day": day.strip(), "ts": ts, **numbers}


def build_router(ctx: WebContext) -> APIRouter:
    manager = ctx.manager
    router = APIRouter()
    # 接收闸 per app 实例(auth 的「只记一次」标志同款口径: 不提升为模块级全局)
    notify_gate = NotifyGate()

    @router.get("/api/traffic/monitor/status")
    def api_tm_status():
        """工具状态区(只读, 展示端点): 恒 200 + 结构化结果

        - 五态来自 agent 的指针探测(S17 起与订阅客户端同源): ready / launching / launch_failed /
          not_running / not_installed; enabled=false 也照查(设置页要能在启用前先验证工具是否在跑);
        - state==ready 时附工具 `GET /status` 回显(工具自身参数表单 + 排障对照真值);
        - 工具不可达 / 密钥缺失 -> reachable=false + state/error, 不抛 5xx。
        """
        manager.web.touch()
        return _source_status(manager)

    @router.put("/api/traffic/monitor/config")
    def api_tm_put_config(body: dict = None):
        """工具 /config 代理(写端点): 载荷 = {"config": {...全量...}}

        `PUT /config` 是**全量覆盖**(last-writer-wins): 前端必须「读后写」(先取 /status 的
        配置回显, 改字段后整体提交), 只发要改的键会把其余键打回默认值。工具未就绪 -> 502。
        """
        manager.web.touch()
        payload = (body or {}).get("config")
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="config 必须是对象(工具配置全量载荷)")
        base_url, token = _ready_endpoint(manager)
        try:
            code, resp = _call_tool(base_url, "/config", "PUT", token, payload)
        except ToolUnreachable as e:
            raise HTTPException(status_code=502, detail=str(e))
        if code == 200:
            return resp
        if code == 400:  # 工具侧校验失败: 逐条错误原样透传(前端展示)
            raise HTTPException(status_code=400, detail=_error_text(resp, code))
        raise HTTPException(status_code=502, detail=f"工具返回 {code}: {_error_text(resp, code)}")

    @router.post("/api/traffic/monitor/autostart")
    def api_tm_autostart(body: dict = None):
        """工具 /autostart 代理(写端点): 载荷 = {"action": "install"|"uninstall"}

        幂等注册/卸载开机自启; 退出码语义由工具侧承载(200 达成期望态含 no-op /
        501 平台不支持 / 5xx 命令失败), 本层原样映射。⚠ 工具与 WebUI 必须同机。
        """
        manager.web.touch()
        action = str((body or {}).get("action") or "").strip()
        if action not in ("install", "uninstall"):
            raise HTTPException(status_code=400, detail="action 必须是 install 或 uninstall")
        base_url, token = _ready_endpoint(manager)
        try:
            code, resp = _call_tool(base_url, "/autostart", "POST", token, {"action": action})
        except ToolUnreachable as e:
            raise HTTPException(status_code=502, detail=str(e))
        if code == 200:
            return resp
        if code == 400:
            raise HTTPException(status_code=400, detail=_error_text(resp, code))
        if code == 501:
            raise HTTPException(status_code=501, detail=_error_text(resp, code))
        raise HTTPException(status_code=502, detail=f"工具返回 {code}: {_error_text(resp, code)}")

    @router.post("/api/traffic/monitor/relaunch")
    def api_tm_relaunch():
        """「立即拉起/重试」(写端点, 幂等): 促订阅线程立刻重跑一轮并忽略失败退避

        只置一个跨线程标志 + 唤醒订阅线程(拉起仍由订阅线程执行, 单写者法则); 返回后前端轮询
        `GET /status` 的 `state` 观察进度(launching -> ready / launch_failed)。
        409 = 无可促的订阅线程(当前来源不是工具 / WEB 未启用/未就绪)。
        """
        manager.web.touch()
        if not _webui_module(manager).request_relaunch():
            raise HTTPException(status_code=409, detail="当前来源不是工具或 WEB 未就绪, 无订阅线程可促拉起")
        return {"ok": True, "accepted": True}

    @router.post("/api/traffic/monitor/shutdown")
    def api_tm_shutdown():
        """停止工具(写端点, S3 26-10-17-1737): 代理工具 `POST /shutdown`

        工具侧收到后**先回 200 再触发自身停止**(gtm/server.py: 响应先写回, 退出走 cmd_run 的
        finally —— 最终落盘 + 释放锁 + 停控制面 + 删发现指针)。200 原样透传(前端据此提示
        「已通知停止」, 随后指针删除, 状态区自然翻成 not_running); 工具未就绪 -> 502;
        其余非 200 -> 502(工具自己的 4xx/5xx 原样收口, 不猜)。
        ⚠ 工具与 WebUI 必须同机(控制面是本机回环)。
        """
        manager.web.touch()
        base_url, token = _ready_endpoint(manager)
        try:
            code, resp = _call_tool(base_url, "/shutdown", "POST", token, {})
        except ToolUnreachable as e:
            raise HTTPException(status_code=502, detail=str(e))
        if code == 200:
            return resp
        raise HTTPException(status_code=502, detail=f"工具返回 {code}: {_error_text(resp, code)}")

    @router.post("/api/traffic/monitor/claim")
    def api_tm_claim():
        """「以本安装重登记」(D4/D5, 计划 26-10-20-1316 §03): 有界前台跑 claim 启动器

        与其它写端点不同: **不经工具 HTTP 控制面** —— claim 时工具可能正在跑(「工具
        在跑就拒绝」正是护栏之一, 走 HTTP 反而够不到), 而是直接前台执行安装内
        claim.cmd / claim.sh(零参数, 意图在脚本里, D19 同族), timeout 30s。
        退出码 0 = 已重登记为正主; 非 0 = 被拒绝(工具在跑 / 数据归属异), 工具侧的
        人话输出原样回传(409), auto-qb 不解释只转述; 入口缺失(旧安装) -> 502 提示升级。
        """
        manager.web.touch()
        conf = _tm_conf(manager)
        target = _resolve_claim_target(conf)
        if target is None:
            raise HTTPException(
                status_code=502,
                detail="未找到 claim 启动器(claim.cmd/claim.sh): 当前工具安装缺人工易主入口, 请升级工具后重试",
            )
        result = _run_claim(target)
        if not result.ok:
            raise HTTPException(status_code=409, detail=result.output or f"重登记被拒绝(退出码 {result.exit_code})")
        return {"ok": True, "exit_code": result.exit_code, "output": result.output}

    @router.post(NOTIFY_PATH)
    def api_tm_notify(body: dict = None):
        """工具通知接收面(S7): 累计流量阈值事件 -> 主循环零读盘补丁今日流量(26-10-21 改制)

        链路(§04 S7; 26-10-21 事件零读盘补丁): 校验 -> 事件号去重 -> 当日判定 -> `_enqueue`
        投递主循环命令(**黄金法则 5**: 快照发布归主循环线程, 本端点只投递意图) -> 主循环把
        事件自带的当日权威累计(up_bytes/down_bytes)补丁进快照 periods 的 day 行 -> 既有
        `/api/state` 主轮询(1.5~3s)自然把新值带给顶栏「今日流量」pill(不新开推送链路)。

        **为什么事件路径零读盘**(26-10-21 用户拍板「读盘本身就是副作用, 要尽量减少读盘;
        事件基本无副作用应立即刷新」): 文件读盘全部收拢在 `traffic_source.refresh_interval`
        一个闸门(定时任务 / 配置切源 / 兜底), 事件一次读盘都不触发 —— 六键里的累计值就是
        权威数据(工具推送前已强制落盘, dat 与事件值一致), 补丁只是一次内存发布, 命令投递
        即唤醒主循环(`post_command` -> `host.wake`, 亚秒级)。旧的冷却判据随之退役(见
        NotifyGate): 它防的「刷新风暴」在零读盘下不存在, 留下的只有滞后。

        对话方是**工具进程**, 不是浏览器: 工具在订阅时登记的回调凭证 = 本实例 WEB 访问密钥,
        鉴权因此复用全局 `make_require_token`(见 webui/tool_client.py 的订阅客户端)。

        响应语义(全部 200, action 区分; 只事件体非法才 400):
        - `refresh_queued` 已投递补丁命令(工具侧记「推送成功」)—— 每个新事件号都直达;
        - `skipped` + reason(duplicate / stale_day): 闸门拦下 —— 不是错误, 工具无需重试;
        - `disabled`: 联动总开关关(保守默认, §07 黄金法则 2) —— 含来源总开关
          `traffic_source.enabled=false`(S1/D1, 26-10-17-1737: 关源即停一切取数, 通知不触发刷新);
        - 400: 事件体非法(工具契约漂移必须响亮报错, 不静默按 0 记账)。
        """
        manager.web.touch()
        event = _parse_notify_event(body)
        # 来源总开关(S1/D1): 判定优先于 provider —— 关源时 provider 指向谁都不取数
        if not traffic_paths.source_enabled(manager.config):
            return {
                "ok": True,
                "action": "disabled",
                "event_id": event["event_id"],
                "reason": "traffic_source.enabled=false: 流量来源已关闭",
            }
        if _provider(manager) != "global_traffic_monitor":
            return {
                "ok": True,
                "action": "disabled",
                "event_id": event["event_id"],
                "reason": "traffic_source.provider != global_traffic_monitor",
            }
        allowed, reason = notify_gate.verdict(event["event_id"])
        if not allowed:
            logger.debug(f"全局流量监视器通知: 事件 #{event['event_id']} 未触发补丁({reason})")
            return {"ok": True, "action": "skipped", "event_id": event["event_id"], "reason": reason}
        if event["day"] != date.today().isoformat():
            # 非当日事件(跨天边界 / 时钟偏差): 不补丁也不读盘 —— 那天的累计文件里早有,
            # 由 refresh_interval 兜底读盘覆盖, 事件路径保持零读盘
            logger.debug(f"全局流量监视器通知: 事件 #{event['event_id']} 非当日({event['day']}), 不补丁(兜底读盘覆盖)")
            return {"ok": True, "action": "skipped", "event_id": event["event_id"], "reason": "stale_day"}
        queued = ctx.enqueue(
            "refresh_traffic",
            {
                "event_id": event["event_id"],
                "day": event["day"],
                "up_bytes": event["up_bytes"],
                "down_bytes": event["down_bytes"],
            },
        )
        # DEBUG 而非 INFO: 阈值事件随流量密度来(工具侧默认每 100MiB 一个, 大流量日可达数百个),
        # 且每事件还会带出主循环/快照补丁两条同类日志 —— INFO 会刷屏(26-10-18 用户要求降级)。
        # 与上面 skipped 分支(本就 DEBUG)口径一致: 放行/拦下都只在 DEBUG 可见。
        logger.debug(
            f"全局流量监视器通知: 事件 #{event['event_id']}({event['day']}, "
            f"累计 {event['total_bytes']}B) -> 已投递今日流量补丁(零读盘)"
        )
        return {
            "ok": True,
            "action": "refresh_queued",
            "event_id": event["event_id"],
            "reason": "",
            "cmd_id": str(queued.get("cmd_id") or ""),
        }

    return router
