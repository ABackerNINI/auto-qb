"""全局流量监视器工具联动路由(计划 26-10-16-0541 S6 代理面 + S7 接收面).

端点:
  GET  /api/traffic/monitor/status    工具 GET /status 代理(只读; 设置页状态区 + 工具参数回显)
  PUT  /api/traffic/monitor/config    工具 PUT /config 代理(全量覆盖 -> 前端「读后写」)
  POST /api/traffic/monitor/autostart 工具 POST /autostart 代理(幂等注册/卸载开机自启)
  POST /api/traffic/monitor/notify    **接收面**(S7): 工具推送的累计流量阈值事件

auto-qb 与工具是两个进程、两个 venv: 本模块是唯一桥 —— 用 stdlib urllib 带 Bearer token
调工具控制面(缺省 127.0.0.1:8099)。HTTP 与密钥定位的单点在 `...tool_client`(与订阅客户端
共用), **不 import 工具包**, 只经 HTTP 契约通信(与架构图一致)。

错误口径(两段不同, 各有理由):
- `GET /status` 是**展示端点** —— 工具没在跑也要能显示「为什么」, 故恒 200 + 结构化空态
  (`reachable=false` + `error`), 不抛 5xx(否则设置页只能看到一片红)。
- `PUT /config` / `POST /autostart` 是**写端点** —— 失败必须真报错(前端据此提示), 工具 400
  原样透传(校验错误逐条可见), 上游 5xx / 不可达收口为 502, 平台不支持透传 501。
- `POST /notify` 的对话方是**工具进程**而非浏览器(见端点内注释): 鉴权仍复用全局
  `make_require_token`(订阅时给工具的凭证 = 本实例 WEB 访问密钥), 但响应一律 200 + action,
  只有事件体本身非法才 400 —— 工具侧把非 2xx 记成推送失败并 WARNING, 闸门拦下的通知不该
  伪装成故障。

token 解析(单点, 实现在 `...tool_client.resolve_token_path`): `global_traffic_monitor.tool_token_path`
非空则用它, 否则取工具平台默认数据目录下的 `monitor.token`。真值仍以工具 `/status` 回显的
`paths.token` 为准, 供排障对照。
"""
from __future__ import annotations

import logging
import math
import threading
import time

from fastapi import APIRouter, HTTPException

# 工具控制面客户端单点(与订阅客户端 webui/tool_client.py 共用; 别名保持本模块既有名字,
# 既有的路由守阵按 `tm_routes._call_tool` / `tm_routes.ToolUnreachable` 打桩)
from ...tool_client import NOTIFY_PATH
from ...tool_client import ToolUnreachable
from ...tool_client import call_tool as _call_tool
from ...tool_client import error_text as _error_text
from ...tool_client import read_token as _read_token
from ...tool_client import resolve_token_path as _resolve_token_path
from ...tool_client import tool_default_data_dir as _tool_default_data_dir
from ..context import WebContext

logger = logging.getLogger("auto_qb.web")  # K3: server 包内 logger 名冻结


def _tm_conf(manager):
    """global_traffic_monitor 配置读取单点(段恒在, 缺省 enabled=false)"""
    return manager.config.global_traffic_monitor


class NotifyGate:
    """通知接收闸: 事件号单调去重 + 冷却(计划 26-10-16-0541 S7)

    两个判据互补(§01「通知」行 / §05 默认参数), 状态是 **per app 实例**的(与 auth 的
    「免鉴权只记一次」同款: 测试会对同一 manager 多次 create_app, 不得提升为模块级全局):

    - **事件号**: 记「已接受的最大事件号」, 小于等于它的一律丢(重复投递 / 乱序到达)。
      重启后归零 —— 工具的下一条事件即放行, 冷启动后的第一次刷新不会被自己挡住;
    - **冷却** `notify_cooldown_s`: 距上次**刷新**的间隔, 窗口内的新事件不再触发刷新(工具侧
      阈值事件可能连续来, 一次刷新已覆盖中间所有增量), 也不推进事件号(它没被接受)。

    纯内存、不落盘: 丢了通知只等于「晚一次刷新」—— 文件一直在写, 订阅方慢轮询兜底, 与工具侧
    「推送失败不阻断落盘」互为冗余(§03 核心不变量)。Web 线程池并发调用 -> 加锁。
    """
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._last_event_id = -1
        self._last_refresh_at = 0.0

    def verdict(self, event_id: int, now: float, cooldown_s: float) -> tuple:
        """-> (是否放行刷新, 原因: "" = 放行 / duplicate / cooldown)"""
        with self._lock:
            if event_id <= self._last_event_id:
                return False, "duplicate"
            if self._last_refresh_at and (now - self._last_refresh_at) < cooldown_s:
                return False, "cooldown"
            self._last_event_id = event_id
            self._last_refresh_at = now
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
        """工具 /status 代理(只读, 展示端点): 恒 200 + 结构化结果

        - enabled=false 也照查(设置页要能在启用前先验证工具是否在跑);
        - 工具不可达 / 密钥缺失 -> reachable=false + error 文案, 不抛 5xx。
        """
        manager.web.touch()
        conf = _tm_conf(manager)
        token_path = _resolve_token_path(conf)
        base = {
            "enabled": bool(conf.enabled),
            "tool_url": conf.tool_url,
            "token_path": token_path,
            "reachable": False,
            "error": "",
            "status": None,
        }
        token = _read_token(token_path)
        if not token:
            base["error"] = f"工具密钥文件不存在或为空: {token_path}(工具未启动过? 或 tool_token_path 配置有误)"
            return base
        try:
            code, payload = _call_tool(conf.tool_url, "/status", "GET", token)
        except ToolUnreachable as e:
            base["error"] = str(e)
            return base
        if code != 200:
            base["error"] = f"工具 /status 返回 {code}: {_error_text(payload, code)}"
            return base
        base["reachable"] = True
        base["status"] = payload
        return base

    @router.put("/api/traffic/monitor/config")
    def api_tm_put_config(body: dict = None):
        """工具 /config 代理(写端点): 载荷 = {"config": {...全量...}}

        `PUT /config` 是**全量覆盖**(last-writer-wins): 前端必须「读后写」(先取 /status 的
        配置回显, 改字段后整体提交), 只发要改的键会把其余键打回默认值。
        """
        manager.web.touch()
        conf = _tm_conf(manager)
        payload = (body or {}).get("config")
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="config 必须是对象(工具配置全量载荷)")
        token = _read_token(_resolve_token_path(conf))
        if not token:
            raise HTTPException(status_code=502, detail="工具密钥文件不存在或为空(工具未启动过? 或 tool_token_path 配置有误)")
        try:
            code, resp = _call_tool(conf.tool_url, "/config", "PUT", token, payload)
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
        conf = _tm_conf(manager)
        action = str((body or {}).get("action") or "").strip()
        if action not in ("install", "uninstall"):
            raise HTTPException(status_code=400, detail="action 必须是 install 或 uninstall")
        token = _read_token(_resolve_token_path(conf))
        if not token:
            raise HTTPException(status_code=502, detail="工具密钥文件不存在或为空(工具未启动过? 或 tool_token_path 配置有误)")
        try:
            code, resp = _call_tool(conf.tool_url, "/autostart", "POST", token, {"action": action})
        except ToolUnreachable as e:
            raise HTTPException(status_code=502, detail=str(e))
        if code == 200:
            return resp
        if code == 400:
            raise HTTPException(status_code=400, detail=_error_text(resp, code))
        if code == 501:
            raise HTTPException(status_code=501, detail=_error_text(resp, code))
        raise HTTPException(status_code=502, detail=f"工具返回 {code}: {_error_text(resp, code)}")

    @router.post(NOTIFY_PATH)
    def api_tm_notify(body: dict = None):
        """工具通知接收面(S7): 累计流量阈值事件 -> 主循环重读历史文件并重发流量快照

        链路(§04 S7): 校验 -> 事件号/冷却双闸 -> `_enqueue` 投递主循环命令(**黄金法则 5**:
        读盘与快照发布都归主循环线程, 本端点只投递意图) -> 主循环重读 `dat_path` 指向的历史
        文件 -> 重发限速/流量快照 -> 既有 `/api/state` 轮询与 SSE 通道自然把新值带给历史流量图
        与顶栏(不新开推送链路)。

        对话方是**工具进程**, 不是浏览器: 工具在订阅时登记的回调凭证 = 本实例 WEB 访问密钥,
        鉴权因此复用全局 `make_require_token`(见 webui/tool_client.py 的订阅客户端)。

        响应语义(全部 200, action 区分; 只事件体非法才 400):
        - `refresh_queued` 已投递刷新(工具侧记「推送成功」);
        - `skipped` + reason(duplicate / cooldown): 闸门拦下 —— 不是错误, 工具无需重试;
        - `disabled`: 联动总开关关(保守默认, §07 黄金法则 2);
        - 400: 事件体非法(工具契约漂移必须响亮报错, 不静默按 0 记账)。
        """
        manager.web.touch()
        conf = _tm_conf(manager)
        event = _parse_notify_event(body)
        if not conf.enabled:
            return {
                "ok": True,
                "action": "disabled",
                "event_id": event["event_id"],
                "reason": "global_traffic_monitor.enabled=false",
            }
        allowed, reason = notify_gate.verdict(event["event_id"], time.time(), float(conf.notify_cooldown_s))
        if not allowed:
            logger.debug(f"全局流量监视器通知: 事件 #{event['event_id']} 未触发刷新({reason})")
            return {"ok": True, "action": "skipped", "event_id": event["event_id"], "reason": reason}
        queued = ctx.enqueue("refresh_traffic", {"event_id": event["event_id"], "day": event["day"]})
        logger.info(f"全局流量监视器通知: 事件 #{event['event_id']}({event['day']}, "
                    f"累计 {event['total_bytes']}B) -> 已投递历史流量刷新")
        return {
            "ok": True,
            "action": "refresh_queued",
            "event_id": event["event_id"],
            "reason": "",
            "cmd_id": str(queued.get("cmd_id") or ""),
        }

    return router
