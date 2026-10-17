"""gtm(全局流量监视小工具)控制面客户端 + 订阅生命周期(计划 26-10-16-0541 S6/S7)。

一个契约(工具控制面, Bearer = 工具 monitor.token), 两个消费方向:

- **代理调用**(S6, 消费方 `server/routes/traffic_monitor.py`): 设置页经本模块的 HTTP 与
  密钥定位单点转发读写到工具; 域映射(展示端点恒 200 空态 / 写端点错误收口 / 401·400·501
  语义)留在路由层, 本模块只报事实。
- **订阅客户端**(S7, 消费方 `webui/module.py`): auto-qb 作为**订阅者**向工具注册
  (回调 endpoint + 回调凭证)并周期心跳续租, 关停时注销 —— 工具据此把累计流量阈值事件
  推回 `POST /api/traffic/monitor/notify`(见 routes/traffic_monitor.py 的接收面)。

S16: 订阅方向不再从配置读 url/token —— **密钥与端口全部来自发现指针**(D6), 编排挂在既有
订阅线程里: 每轮期望态为真时先经 `core.traffic_source.agent` 确保工具可达(探测 / 缺席拉起),
再注册订阅。代理方向的 url/token 解析仍待 S17 随设置页合并一起收编。

auto-qb 与工具是两个进程、两个 venv: 两个方向都只经 HTTP 契约说话, **不 import 工具包**。

订阅线程模型(对齐 pitfalls/backend/concurrency.md 的「主循环单写线程」与「带超时的阻塞等待
必须配叫停口」两条):

- 控制面 I/O(注册 / 心跳 / 注销)只发生在**订阅线程**里 —— 主循环侧只置期望态并唤醒它,
  工具假死时主循环不会被控制面超时拖住;
- 期望态每轮**现读配置**(热重载即时生效; 不按值持有旧 Config, 见 pitfalls/backend/
  hot-reload-held-config.md), 故「配置变了」不需要额外的状态同步代码: sync() 只是「现在就
  跑一轮」;
- `stop()` 先叫停再**有界 join**(超时只 WARNING): 关停不被工具拖住; 没注销干净的订阅由
  工具侧租约(lease_ttl, 默认 180s)自然剔除。

回调凭证复用**本实例的 WEB 访问密钥**(`manager.web.token`, 订阅时登记给工具): 工具推送时
按登记值出示, 接收端点因此直接复用既有 `make_require_token` 那道闸, 不新开鉴权面。
"""
from __future__ import annotations

import json
import logging
import os
import threading
import urllib.error
import urllib.request
from typing import Optional, Tuple

from ..core.traffic_source import agent
from ..infra.utils import is_mac, is_windows

logger = logging.getLogger(__name__)

#: 工具控制面调用超时(秒): 本机回环调用, 正常亚毫秒级; 给足余量但不无限等(工具假死)
_TOOL_TIMEOUT_S = 5.0

#: 心跳周期缺省(秒): 真值由工具在 /subscribe 响应里给(heartbeat_interval_s), 拿不到才用它。
#: 与工具侧 lease_ttl(180s)/heartbeat(60s) 缺省配套 —— 三次心跳机会用满一条租约。
_DEFAULT_HEARTBEAT_S = 60.0

#: 工具未就绪时的轮询间隔(秒, S16): 探测 / 拉起窗口内短轮询(D14「拉起后短等待探活」),
#: 探活失败不发控制面请求(只发一次本机 GET), 故短轮询不会刷屏也不会放大负载。
_NOT_READY_POLL_S = 3.0

#: 关停时等订阅线程退出的上限(秒): 必须大于单次控制面超时, 否则「叫停了还在等」= 关停白等
_STOP_JOIN_TIMEOUT_S = 6.0

#: 通知端点路径: 工具推送回调的落点(订阅时登记给工具的那个 endpoint 的尾巴)。
#: 与 routes/traffic_monitor.py 注册的路由路径同源 —— 改这里必须同步那处(有守阵钉住)。
NOTIFY_PATH = "/api/traffic/monitor/notify"

#: 控制面鉴权头的键名: **拆写常量**而非字面量 —— 工作区写入判据把「凭据键名 + 赋值形态」当
#: 凭据字面量拦整文件(见 pitfalls/testing/credential-shape-write-guard.md), 键名拆写是
#: 2026-10-15 用户拍板的收敛样板。值恒为运行期变量, 本文件不含任何凭据。
_AUTH_HEADER_KEY = "Auth" + "orization"


class ToolUnreachable(RuntimeError):
    """工具控制面不可达 / 响应非法(网络错、连接拒绝、非 JSON)."""


def tool_default_data_dir() -> str:
    """工具数据目录默认值(镜像 gtm.storage.default_data_dir 的平台惯例; 环境变量优先)

    镜像而非 import: 工具是独立包/venv, auto-qb 不 import 它。仅用于 tool_token_path 留空时
    定位缺省密钥文件; 用户在配置里显式给 tool_token_path 即覆盖本推断。平台判定走 utils 单点。

    !S16 后**订阅方向**不再走本推断(密钥与端口全来自发现指针, 见 core.traffic_source.agent);
    本函数只剩设置页代理路由(S7/S17)在用, 待 S17 一并收编。
    """
    env = os.environ.get("GTM_DATA_DIR")
    if env:
        return env
    if is_windows():
        base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
        return os.path.join(base, "gtm")
    if is_mac():
        return os.path.join(os.path.expanduser("~"), "Library", "Application Support", "gtm")
    base = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
    return os.path.join(base, "gtm")


def resolve_token_path(conf) -> str:
    """工具 monitor.token 路径: 显式 tool_token_path 优先, 否则工具平台默认数据目录下"""
    explicit = str(conf.tool_token_path or "").strip()
    if explicit:
        return os.path.abspath(os.path.expanduser(explicit))
    return os.path.join(tool_default_data_dir(), "monitor.token")


def read_token(path: str) -> str:
    """读工具密钥文件(去空白); 缺失/读失败 -> 空串(由调用方决定报错口径)"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def call_tool(base_url: str, path: str, method: str, credential: str, payload=None, timeout: float = _TOOL_TIMEOUT_S):
    """调工具控制面: 返回 (status_code, payload_dict); 不可达/非 JSON -> ToolUnreachable

    只经 HTTP 契约; 4xx/5xx 也正常返回(交给调用方按域映射), 网络层失败才抛。
    credential = 出示给工具的访问密钥(读自工具 monitor.token); 值恒为运行期变量。
    """
    url = base_url.rstrip("/") + path
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        url,
        method=method,
        data=data,
        headers={
            _AUTH_HEADER_KEY: f"Bearer {credential}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            code = resp.status
    except urllib.error.HTTPError as e:
        raw = e.read()
        code = e.code
    except (urllib.error.URLError, OSError) as e:
        raise ToolUnreachable(f"工具控制面不可达({url}): {e}") from e
    try:
        return code, (json.loads(raw.decode("utf-8")) if raw else {})
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise ToolUnreachable(f"工具响应非法 JSON: {e}") from e


def error_text(payload: dict, code: int) -> str:
    """从工具响应里抽人读错误: errors 列表优先(校验聚合), 否则 error 字段"""
    errors = payload.get("errors")
    if isinstance(errors, list) and errors:
        return "; ".join(str(x) for x in errors)
    return str(payload.get("error") or f"工具返回 {code}")


class TrafficMonitorSubscriber:
    """auto-qb 作为工具订阅者的生命周期(启动 / 热重载 / 关停只经 sync() 与 stop() 两个口)

    幂等(黄金法则 1): `sync()` 可任意次调用, 只把「期望订阅态」与「线程当前状态」收敛到一致;
    注册/心跳/注销本身也是「已达期望态即 no-op」。

    状态归属: 订阅 id / 注册键 / 心跳周期**只在订阅线程内读写**(单写者, 无锁); 主循环侧只
    调 sync()/stop() 这两个非阻塞口。本组件不碰任务队列与 state_file(黄金法则 5 不受影响)。
    """
    def __init__(self, manager) -> None:
        self._manager = manager
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        # 工具发现/拉起单点(S16): 状态内聚在它自己身上; UI 可经 self.agent 读状态区
        self._agent = agent.TrafficSourceAgent()
        # ---- 以下状态只在订阅线程内读写 ----
        self._sub_id = ""  # 工具侧分配的订阅 id; 空 = 当前未注册
        self._reg_key: Optional[tuple] = None  # 注册时的 (工具基地址, endpoint, 回调凭证)
        self._reg_tool: Optional[tuple] = None  # 注册时的 (工具基地址, 密钥路径) —— 注销寻址用
        self._heartbeat_s = _DEFAULT_HEARTBEAT_S
        self._wait_s = _DEFAULT_HEARTBEAT_S  # 本轮结束后的等待节拍(未就绪时短轮询)
        self._last_error = ""  # 最近一次失败原因(同一原因只 WARNING 一次, 见 _note_error)

    @property
    def agent(self) -> agent.TrafficSourceAgent:
        """工具发现单点(设置页状态区读它; 见 S16/S17)"""
        return self._agent

    # ---------------- 主循环侧(非阻塞) ----------------

    def sync(self) -> None:
        """按当前配置收敛期望态(非阻塞, 幂等; 启动与每次热重载后调用)

        应订阅 -> 确保订阅线程在跑, 并促它立刻跑一轮; 不应订阅 -> 在跑的线程自己读到
        「期望订阅」为假后注销并收线(线程内现读配置, 不做跨线程状态传递)。
        """
        if self._desired()[0]:
            self._ensure_thread()
        self._wake.set()

    def stop(self, timeout: float = _STOP_JOIN_TIMEOUT_S) -> None:
        """关停: 叫停订阅线程并等它退出(有界); 线程退出前会把订阅注销掉

        !超时只 WARNING 不阻塞更久 —— 守护线程随进程终灭, 残留订阅由工具侧租约兜底清;
        配对语义要求: `timeout` 必须大于单次控制面调用超时, 否则就是「叫停了还在等」。

        !超时时**不摘线程引用**(与「已退出才置 None」区分开): 摘了就再也没人能 join 它,
        而下一次 sync() 会因「看不到线程」再起一条 —— 变成双订阅双心跳。保留引用后,
        _ensure_thread 见 is_alive 为真不会重起, 后续 stop() 也还能补 join。
        """
        self._stop.set()
        self._wake.set()
        thread = self._thread
        if thread is None:
            return
        thread.join(timeout)
        if thread.is_alive():
            logger.warning(f"全局流量监视器订阅线程在 {timeout:g}s 内未退出(守护线程, 随进程终灭)")
            return
        self._thread = None

    # ---------------- 订阅线程 ----------------

    def _ensure_thread(self) -> None:
        """确保订阅线程在跑(幂等: 已存活不重复起; stop 过再 sync 也复用同一入口)"""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        thread = threading.Thread(target=self._run, name="auto-qb-gtm-sub", daemon=True)
        self._thread = thread
        thread.start()

    def _run(self) -> None:
        """订阅线程主循环: 每轮按期望态收敛一次, 期望态转假即收线

        !单轮异常不杀线程(下轮重试)—— 与工具侧「单轮落盘失败不杀守护进程」同纪律。
        """
        while not self._stop.is_set():
            try:
                want = self._pass()
            except Exception:
                logger.warning("全局流量监视器订阅轮异常(不杀线程, 下轮重试)", exc_info=True)
                want = True
            if not want:
                break
            self._wake.wait(self._wait_s)  # 心跳节拍; 未就绪时是短轮询; sync()/stop() 会提前叫醒
            self._wake.clear()
        try:
            self._unregister("线程收线")
        except Exception:
            logger.warning("全局流量监视器订阅注销异常(守护线程, 随进程终灭)", exc_info=True)

    def _pass(self) -> bool:
        """一轮收敛 -> 是否应继续订阅(False = 期望态为假, 已注销, 该收线)

        四步: 期望态为假 -> 注销并收线; 工具不可达 -> 先确保可达(探测 / 缺席拉起, S16, 本轮
        不发控制面请求); 已注册且注册键未变 -> 心跳; 其余(未注册 / 注册键变化 / 心跳判定注册
        失效) -> 先注销(no-op 安全)再重新注册。
        """
        want, why = self._desired()
        if not want:
            self._wait_s = _DEFAULT_HEARTBEAT_S
            self._unregister(why)
            return False
        endpoint = self._agent.ensure_running(self._conf())
        if endpoint is None:
            # 工具未就绪(拉起中 / 退避中 / 未安装): 不发控制面请求, 也不逐轮 WARNING
            # —— 原因由 agent 侧节流说明(未就绪时短轮询探活, D14)
            self._wait_s = _NOT_READY_POLL_S
            return True
        if self._sub_id and self._reg_key == self._reg_key_now(endpoint):
            if self._heartbeat(endpoint):
                self._wait_s = self._heartbeat_s
                return True
            self._sub_id, self._reg_key = "", None  # 心跳判定注册在工具侧已失效 -> 重注册
        self._unregister("重新注册")
        self._register(endpoint)
        self._wait_s = self._heartbeat_s
        return True

    # ---------------- 期望态(每轮现读配置) ----------------

    def _conf(self):
        """traffic_source.global_traffic_monitor 来源参数段(段恒在; 每轮现读 -> 热重载即时生效)

        !读取面在 S16 从过渡桩段(top-level global_traffic_monitor)迁到顶层 traffic_source 段
        (D1/D2): 是否联动只看 provider, 工具安装/数据参数在来源子段。
        """
        return self._manager.config.traffic_source.global_traffic_monitor

    def _credential(self) -> str:
        """本实例 WEB 访问密钥(工具推送回调时出示; 也是订阅注册键之一)

        !非字符串一律当空(未就绪): 桩配置(mock.MagicMock)的属性拿到的是 Mock 对象, `str()` 一包装
        就变成"非空" — 同 `_desired` 的恒等判据一条道理(见那里注释)。
        """
        value = getattr(self._manager.web, "token", "")
        return value if isinstance(value, str) else ""

    def _endpoint(self) -> str:
        """登记给工具的回调 endpoint: 本机回环 + 本实例 WEB 端口(工具与 WebUI 必须同机)"""
        return f"http://127.0.0.1:{int(self._manager.config.web.port)}{NOTIFY_PATH}"

    def _reg_key_now(self, endpoint) -> tuple:
        """注册键: 任一维变化都要按新值重注册(工具侧按 endpoint + 回调凭证存条目)

        工具基地址进键: 工具重启换随机端口(D9)后键变 -> 自动按新端点重注册。
        """
        return (endpoint.base_url, self._endpoint(), self._credential())

    def _desired(self) -> Tuple[bool, str]:
        """期望订阅态 -> (是否应订阅, 不订阅的原因文案; 用于日志与人读)

        !provider 与 WEB 开关一律按「**不等/恒等**」判, 而非真值判: 真配置里 provider 就是 str
        (已过 validate_config, 黄金法则 4); 而**桩配置**(mock.MagicMock / 替身段对象)的属性是
        Mock —— 真值判会把桩段当成「已启用且要订阅」, 真起一条订阅线程持续到进程结束
        (2026-10-16 实测: 热重载守阵的 MagicMock 新配置漏出一条常驻订阅线程对着假 URL 空转;
        同族形态见 pitfalls/testing/hot-reload-mock-sections.md)。类型/字面判据把这条路堵死在
        开线程之前。
        """
        provider = getattr(self._manager.config.traffic_source, "provider", None)
        if provider != "global_traffic_monitor":
            return False, "当前流量来源不是全局流量监视器(traffic_source.provider != global_traffic_monitor)"
        if self._manager.config.web.enabled is not True:
            return False, "WEB UI 未启用(通知端点不存在)"
        if not self._credential():
            return False, "WEB 访问密钥未就绪"
        return True, ""

    # ---------------- 控制面动作(只在订阅线程内调用) ----------------

    def _register(self, endpoint) -> None:
        """注册订阅: 200 -> 记住 id / 心跳周期 / 注册键; 其余(含不可达)只记一条, 下轮重试

        !寻址与密钥全部来自发现指针(S16/D6): `_register` 只在 agent 已探活成功后被调用,
        endpoint 就是工具此刻的真实监听端点。
        """
        tool_key = read_token(endpoint.token_path)
        if not tool_key:
            self._note_error(f"工具密钥文件不存在或为空: {endpoint.token_path}(工具刚拉起还没写出密钥?)")
            return
        payload = {"endpoint": self._endpoint(), "token": self._credential()}
        try:
            code, resp = call_tool(endpoint.base_url, "/subscribe", "POST", tool_key, payload)
        except ToolUnreachable as e:
            self._note_error(f"注册订阅失败: {e}")
            return
        if code != 200:
            self._note_error(f"注册订阅被拒: 工具返回 {code}: {error_text(resp, code)}")
            return
        sub_id = str(resp.get("id") or "")
        if not sub_id:
            self._note_error(f"注册订阅响应缺 id: {resp}")
            return
        self._sub_id = sub_id
        self._reg_key = self._reg_key_now(endpoint)
        self._reg_tool = (endpoint.base_url, endpoint.token_path)
        self._heartbeat_s = _heartbeat_interval(resp)
        self._clear_error()
        logger.info(
            f"全局流量监视器订阅已注册: id={sub_id} -> {payload['endpoint']}"
            f"(心跳 {self._heartbeat_s:g}s, 工具 {endpoint.base_url})"
        )

    def _heartbeat(self, endpoint) -> bool:
        """心跳续租 -> 注册是否仍有效(False = 工具报未知 id, 调用方据此重新注册)

        !工具不可达**不算失效**: 租约 180s 给三次机会, 期间订阅仍可能有效(工具侧剔除是懒的);
        真过期后下一次心跳会拿到 404, 那时才重注册。
        """
        tool_key = read_token(endpoint.token_path)
        if not tool_key:
            self._note_error(f"工具密钥文件不存在或为空: {endpoint.token_path}(心跳跳过)")
            return True
        try:
            code, resp = call_tool(endpoint.base_url, "/heartbeat", "POST", tool_key, {"id": self._sub_id})
        except ToolUnreachable as e:
            self._note_error(f"心跳失败(工具不可达, 订阅由租约兜底): {e}")
            return True
        if code == 200:
            self._clear_error()
            logger.debug(f"全局流量监视器订阅心跳续租: id={self._sub_id}")
            return True
        if code == 404:
            logger.info(f"全局流量监视器订阅心跳: 工具报未知 id({self._sub_id}), 立刻重新注册")
            return False
        self._note_error(f"心跳被拒: 工具返回 {code}: {error_text(resp, code)}")
        return True

    def _unregister(self, reason: str) -> None:
        """注销当前订阅(无订阅时 no-op); 失败只记 INFO —— 工具侧租约到期自会剔除

        !寻址用**注册时**的工具端点与密钥路径(不是现读的指针): 工具重启换了随机端口(D9)或
        用户改了 tool_dir 时, 现读值指向的很可能是**另一个**端点, 拿它去注销只会白白报错并把
        订阅留在旧工具上(直到租约到期)。
        """
        sub_id, self._sub_id, self._reg_key = self._sub_id, "", None
        reg_tool, self._reg_tool = self._reg_tool, None
        if not sub_id:
            return
        if reg_tool is None:  # 纯防御: sub_id 与 reg_tool 同生同灭, 正常到不了这里
            logger.info(f"全局流量监视器订阅注销跳过(缺注册时寻址信息): id={sub_id}")
            return
        base_url, token_path = reg_tool
        tool_key = read_token(token_path)
        if not tool_key:
            logger.info(f"全局流量监视器订阅注销跳过(工具密钥不可读): id={sub_id} ({token_path})")
            return
        try:
            code, resp = call_tool(base_url, "/unsubscribe", "POST", tool_key, {"id": sub_id})
        except ToolUnreachable as e:
            logger.info(f"全局流量监视器订阅注销失败(工具不可达, 由租约过期兜底): {e}")
            return
        if code in (200, 404):  # 404 = 工具侧已经没了(租约剔除/工具重启), 等价于已注销
            logger.info(f"全局流量监视器订阅已注销: id={sub_id}({reason})")
        else:
            logger.info(f"全局流量监视器订阅注销被拒: 工具返回 {code}: {error_text(resp, code)}")

    # ---------------- 日志节流(同一原因只说明白一次) ----------------

    def _note_error(self, msg: str) -> None:
        """失败: 同一原因首次 WARNING, 之后同因降 DEBUG

        工具没起是**常态**(坑档 ops/alert-levels.md 2.: 同一根因只说明白一次), 逐轮 WARNING
        会刷屏; 原因变了或恢复后再次失败 -> 重新记一条可见的 WARNING。
        """
        if msg != self._last_error:
            self._last_error = msg
            logger.warning(f"全局流量监视器订阅: {msg}")
        else:
            logger.debug(f"全局流量监视器订阅: {msg}")

    def _clear_error(self) -> None:
        """成功: 清失败记忆; 从失败中恢复时补一条 INFO(失败不静默消失)"""
        if self._last_error:
            logger.info(f"全局流量监视器订阅已恢复(先前: {self._last_error})")
            self._last_error = ""


def _heartbeat_interval(resp: dict) -> float:
    """取工具给的心跳周期(秒): 缺/非法回缺省 —— 别让一次响应格式变化把节拍打成 0(紧循环)"""
    try:
        value = float(resp.get("heartbeat_interval_s"))
    except (TypeError, ValueError):
        return _DEFAULT_HEARTBEAT_S
    return value if value > 1.0 else _DEFAULT_HEARTBEAT_S
