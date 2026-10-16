"""HR 取数发现服务(计划 26-10-14-1241 §04 S2/S3): 「去端口 + 跨机」的注册与配对面。

与数据端点(hr/server.py)平行的独立小服务(不进 server.py, 避免其继续膨胀):

- `GET /api/hr/discover`: 返回本机全部存活实例的数据端点与 token —— 扩展只配一个发现地址
  就能拿到全部实例(「token 自动分发」); 它本身就是发 token 的, 所以**免 token**,
  两道关是 origin 白名单(与数据端点第二道防线同一机制) + 配对码(仅非回环可达时强制, S3);
- `InstanceRegistry`: 本机实例注册表(平台 app-data 的 instances.json), 心跳 upsert(写时剪枝超龄) + TTL 聚合;
- 候选表先绑先得(discovery_port 起 +0/+1/+2, C7)+ 绑定失败后台退避重试(占用者退出自动
  接管, 翻转旧「归属者退出不接管」限制 —— R6)+ 校验期临时端口段告警(S1 ⑥, 在 config 层);
- 发现不可用**永不**影响数据端点: 三个候选全占 ⇒ 明确日志 + 数据端点照常服务(扩展退手动)。

!线程纪律(与 hr/server.py 同款): 发现端点线程只做 HTTP 应答与注册表读写, 不碰任务队列、
state_file 与站点文件; 后台重试线程只做绑定尝试与端点启停 —— 单一写线程假设不破。
!不杀占用进程、不用 SO_REUSEADDR/SO_REUSEPORT 抢绑(Windows 双绑语义未定义 / Linux 会分流)。
"""
import json
import logging
import os
import secrets
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..infra.utils import atomic_write, is_loopback_host
from .channel import ORIGIN_HEADER, origin_allowed, pairing_credential, pairing_display_code, pairing_needed
from .server import (
    HrEndpointHandle,
    RejectThrottle,
    _EndpointServer,
    _content_length,
    _header,
    _json,
    make_endpoint_handler,
)
from .threadlifecycle import HrThreadHandle

logger = logging.getLogger(__name__)

#: 发现端点路径(与扩展 discovery.js 同源, 协议守阵双向钉住)
API_DISCOVER = "/api/hr/discover"
#: 配对码头(扩展侧配对码随它上来; 缺失 ⇒ 401 pairing_required, 不符 ⇒ 401 pairing_invalid)
PAIRING_HEADER = "X-Hr-Pairing"
#: 发现端口默认值(用户现产 18788 转正为发现端口; 数据端口默认 0 = 随机, 计划 §01 派生口径)
DISCOVERY_DEFAULT_PORT = 18788
#: 候选表大小(C7): 固定连号 3 个, 不加配置键; 扩展并行探测同一张表
DISCOVERY_CANDIDATES = 3
#: 实例注册表目录/文件名(C5): 平台 app-data 下的 auto-qb-hr/instances.json
REGISTRY_DIRNAME = "auto-qb-hr"
REGISTRY_FILENAME = "instances.json"
#: 心跳间隔 / 条目 TTL(C1): 发现失败有手动退路, 不需要更激进的 TTL
HEARTBEAT_INTERVAL_S = 30.0
INSTANCE_TTL_S = 120.0
#: 注册表**读取**的退避重试: 读者与写者(含别的进程)在 Windows 上会互相瞬时拒绝, 而「读不到」
#: 必须与「内容损坏」「空表」分开对待(坑档 pitfalls/backend/platform-fs「Windows 原子写与
#: 并发读者的双向瞬时拒绝」; 2026-10-16 心跳实报)。数字与 utils.REPLACE_RETRY_* 同口径。
REGISTRY_READ_ATTEMPTS = 5
REGISTRY_READ_RETRY_DELAY_S = 0.05
#: 绑定失败的后台重试退避(C8): 60s 起步、上限 10 分钟; 接管延迟 <= 一个间隔, 可接受
RETRY_MIN_S = 60.0
RETRY_MAX_S = 600.0
DISCOVERY_STOP_TIMEOUT = 5.0
#: 配对失败每来源简单计数上限(C3 防枚举): 60s 窗口内超过即临时静默(响应照常 401, 不再逐条记日志)
PAIRING_FAIL_LIMIT_PER_MIN = 5


def discovery_candidates(discovery_port: int) -> List[int]:
    """发现端口候选表(C7): discovery_port 起连号 3 个(+0/+1/+2), 上限 65535 截断

    推导与扩展侧 discovery.js 的 discoveryCandidates **同源**(协议守阵双向钉住):
    后端按表「先绑先得」顺延, 扩展按表「并行探测」。
    """
    base = int(discovery_port)
    if base < 1:
        return []  # 0 = 关闭发现(运行期不会走到, 防御性): 不产生候选
    return [p for p in (base + i for i in range(DISCOVERY_CANDIDATES)) if 1 <= p <= 65535]


def default_registry_path() -> str:
    """实例注册表路径(C5): 平台 app-data 的 auto-qb-hr/instances.json

    Windows = %LOCALAPPDATA%; 类 Unix = XDG_DATA_HOME(~/.local/share 兜底)。
    !不得放云同步盘(与 hr_check.shared_dir 同一条纪律: 锁与原子替换都不保证)。
    """
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
    return os.path.join(base, REGISTRY_DIRNAME, REGISTRY_FILENAME)


def _entry_fresh(entry: Dict[str, Any], *, now: float, ttl: float) -> bool:
    """条目是否落在 TTL 窗口内(ts 可解析且未超龄)

    !读路径(`alive` 的过滤)与写路径(`upsert` 的剪枝)**共用这一条判据** —— 两处各写一份必然
    漂移, 而漂移的后果正是「读时看不见、写时不剪」: 文件仍无界增长(2026-10-16 用户实报
    「发现产生很多无关条目」的成因之一, 累积到 684 条)。
    ts 缺失 / 非数值 ⇒ 不可判活, 一律当超龄 —— 与「不给扩展半条」同口径。
    """
    try:
        return now - float(entry.get("ts") or 0) <= ttl
    except (TypeError, ValueError):
        return False


def _read_registry_text(path: str) -> str:
    """读注册表**原文**: 打开被瞬时拒绝时退避重试, 重试耗尽才把原异常抛给调用方

    !为什么单独一层: Windows 的替换事务窗口内, 读者的 `open()` 会被瞬时拒绝(`WinError 5/32`),
    而 `open()` 失败既不是「内容损坏」也不是「空表」—— 坑档 `pitfalls/backend/platform-fs.md`
    的处置是**读侧也要重试**, 「看不到内容 ≠ 看到半截内容」。缺文件(`FileNotFoundError`)不重试:
    它是有明确语义的稳定状态。POSIX 上不会触发。
    """
    last: Optional[OSError] = None
    for attempt in range(REGISTRY_READ_ATTEMPTS):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            raise
        except PermissionError as e:
            last = e
            if attempt < REGISTRY_READ_ATTEMPTS - 1:
                time.sleep(REGISTRY_READ_RETRY_DELAY_S)
    assert last is not None
    raise last


class InstanceRegistry:
    """本机实例注册表(跨进程共享文件): 心跳 upsert + TTL 过滤聚合(S2 ①)

    !写 = 临时文件原子替换(infra.utils.atomic_write); 读容忍(缺文件/坏 JSON ⇒ 当空, 不抛) ——
    注册表是「尽力而为」的发现面, 任何损坏都不该打断数据端点(R5); 多进程并发写由
    os.replace 的原子性兜底(瞬时互覆盖由 30s 心跳自愈, 聚合侧再过 TTL)。
    条目形态: {"id", "name", "endpoint", "token", "ts"}; id = sha1(data_dir)[:12](runtime 算)
    —— 同 data_dir 重启复用同一条目, 天然 upsert; ts 是该条目最近一次心跳时刻。
    !upsert 顺手剪掉超龄条目(见该方法): 注册表是**长期**文件, 只增不减会让死实例永久堆积。
    """
    def __init__(self, path: str) -> None:
        self.path = path
        self._lock = threading.Lock()

    def upsert(
        self, *, entry_id: str, name: str, endpoint: str, token: str, ts: float, ttl: float = INSTANCE_TTL_S
    ) -> None:
        """登记/刷新本实例条目(启动期与心跳线程都走这里; 同 id 覆盖)

        !顺手剪掉超龄条目 —— 写路径是**唯一**的写入口, 剪枝放这里最省(有活实例心跳就一定有
        剪枝; 全死时文件留着也无害, 没人读它)。只读时过滤(alive)不够: 那样死实例只是
        「看不见」, 文件仍无界增长, 且每次心跳都要整份读 + 整份写。
        剪枝基准 = 本次 upsert 的 ts(生产所有写者都用 time.time()); 读不到(读侧瞬时拒绝且重试
        耗尽)时**本轮不写**并抛 RuntimeError —— 拿不到别家条目却写回只含自己的表, 等于静默抹掉
        其它实例(只靠对端 30s 心跳才回来); 心跳线程容错为「下一周期重试」, 与写侧一致。
        """
        with self._lock:
            loaded = self._load()
            if loaded is None:
                raise RuntimeError(
                    f"HR 实例注册表当前读不到(瞬时拒绝, 已退避重试 {REGISTRY_READ_ATTEMPTS} 次), "
                    f"本轮不写以免覆盖其它实例条目: {self.path}"
                )
            entries = [e for e in loaded if e.get("id") != entry_id and _entry_fresh(e, now=ts, ttl=ttl)]
            entries.append({"id": entry_id, "name": name, "endpoint": endpoint, "token": token, "ts": ts})
            self._save(entries)

    def alive(self, *, ttl: float, now: float) -> List[Dict[str, Any]]:
        """TTL 过滤后的存活实例(缺 endpoint / 缺 token 的残条目一并剔除, 不给扩展半条)

        读不到(瞬时拒绝且重试耗尽)时当**空列表**: 只读面, 一次空响应比中断发现安全 ——
        扩展下一轮再问即可(S2 ③「发现不可用不影响数据端点」)。
        """
        with self._lock:
            entries = self._load() or []
        return [e for e in entries if _entry_fresh(e, now=now, ttl=ttl) and e.get("endpoint") and e.get("token")]

    def _load(self) -> Optional[List[Dict[str, Any]]]:
        """读注册表; `None` = **读不到**(与"空表"两件事), 其余容忍口径不变

        - 缺文件 → `[]`;坏 JSON / 非列表 → WARNING + `[]`(R5: 注册表是尽力而为的发现面,
          任何损坏都不该打断数据端点, 下次心跳写回合法内容即自愈);
        - **瞬时拒绝**(`PermissionError`, 退避重试耗尽)→ `None`: 看不到内容 ≠ 看到坏内容,
          调用方按"不知道别家有什么"处理(upsert 本轮不写, alive 当空列表)。
        """
        try:
            text = _read_registry_text(self.path)
        except FileNotFoundError:
            return []
        except PermissionError as e:
            logger.warning(f"HR 实例注册表读取被瞬时拒绝(退避重试耗尽), 本轮按读不到处理: {self.path} ({e})")
            return None
        except OSError as e:
            logger.warning(f"HR 实例注册表无法读取, 按空表处理(下次心跳自愈): {self.path} ({e})")
            return []
        try:
            data = json.loads(text)
        except ValueError:
            logger.warning(f"HR 实例注册表无法解析, 按空表处理(下次心跳自愈): {self.path}")
            return []
        if not isinstance(data, list):
            return []
        return [e for e in data if isinstance(e, dict)]

    def _save(self, entries: List[Dict[str, Any]]) -> None:
        atomic_write(self.path, lambda f: json.dump(entries, f, ensure_ascii=False), keep_backup=False)


def _is_wildcard_host(host: str) -> bool:
    """「监听全部地址」形态: 自述端点的主机部分须按请求 Host 头替换(只影响响应文本)"""
    return str(host or "").strip() in ("", "0.0.0.0", "::")


def _host_of_hostport(hostport: str) -> str:
    """请求 Host 头的主机部分(去端口; 带 [] 的 IPv6 字面量原样保留括号)"""
    hostport = str(hostport or "").strip()
    if not hostport:
        return ""
    if hostport.startswith("["):
        return hostport.split("]", 1)[0] + "]" if "]" in hostport else hostport
    return hostport.split(":", 1)[0]


def _replace_url_host(url: str, host: str) -> str:
    """把 URL 的**主机部分**换成请求 Host 头的主机部分(0.0.0.0 自述用)

    端口保留条目自己的(那是数据端点的实绑端口 —— Host 头带的是发现端口的端口, 不能跟换);
    只影响响应文本, 不进任何判据(计划 S2 ④)。
    """
    if "://" not in url or not host:
        return url
    scheme, rest = url.split("://", 1)
    netloc = rest.split("/", 1)[0]
    port = f":{netloc.rsplit(':', 1)[1]}" if ":" in netloc else ""
    path = "/" + rest.split("/", 1)[1] if "/" in rest else ""
    return f"{scheme}://{host}{port}{path}"


@dataclass(slots=True)
class HrDiscoveryStatus:
    """发现端点自检快照(供上层报告与排障; 不含密钥内容)"""

    enabled: bool = False
    listening: bool = False
    port: int = 0
    bound_port: int = 0
    candidates: Tuple[int, ...] = field(default_factory=tuple)
    pairing_required: bool = False
    note: str = ""


class HrDiscoveryServer:
    """发现端点(origin 门 + 配对门 + 实例聚合); 与 HrChannelServer 同形(start/stop/status/route())

    线程形态与数据端点同款: serve 线程 + 心跳线程(+ 绑定失败时的重试线程), 全部 daemon;
    route() 纯逻辑可单测。!发现不可用**永不**影响数据端点: 绑定失败只记日志 + 后台重试,
    start() 返回 False 而不抛 —— 扩展退手动配置(R2/S2)。
    """
    def __init__(
        self,
        *,
        host: str,
        port: int,
        entry_id: str,
        entry_name: str,
        endpoint_fn: Callable[[], str],
        token: str,
        registry: Optional[InstanceRegistry] = None,
        pairing: str = "auto",
        pairing_secret: str = "",
        extension_id: str = "",
        now_fn: Callable[[], float] = time.time,
    ) -> None:
        self.host = host
        self.port = int(port)
        self.entry_id = entry_id
        self.entry_name = entry_name
        #: 当前数据端点自述 URL(现读: port=0 的实绑值要等数据端点 start 后才知道)
        self.endpoint_fn = endpoint_fn
        self.token = token
        self.registry = registry
        self.pairing = pairing
        self.pairing_secret = pairing_secret
        self.extension_id = extension_id
        self._now = now_fn
        self._reject = RejectThrottle(now_fn=now_fn)
        self._pair_fail_lock = threading.Lock()
        self._pair_fail_times: Dict[str, Dict[str, Any]] = {}
        self._handle: Optional[HrEndpointHandle] = None
        self._bound_port = 0
        self._lifecycle_lock = threading.Lock()
        self._heartbeat_thread = HrThreadHandle()
        self._heartbeat_stop = threading.Event()
        self._retry_thread = HrThreadHandle()
        self._retry_stop = threading.Event()
        #: 退避区间(实例属性便于测试注入短间隔; 生产默认 C8: 60s 起步、上限 10 分钟)
        self.retry_min_s = RETRY_MIN_S
        self.retry_max_s = RETRY_MAX_S

    # ---------- 生命周期 ----------

    @property
    def candidates(self) -> List[int]:
        return discovery_candidates(self.port)

    @property
    def bound_port(self) -> int:
        """实绑端口(候选非首位时与配置端口不同; 未绑定 = 0)"""
        return self._bound_port

    @property
    def pairing_required(self) -> bool:
        """配对码是否生效(单点在 channel.pairing_needed: on 恒要 / off 恒不要 / auto 非回环)"""
        return pairing_needed(self.pairing, self.host)

    @property
    def started(self) -> bool:
        with self._lifecycle_lock:
            return self._handle is not None and self._handle.started

    def start(self) -> bool:
        """启动发现端点(候选表先绑先得); 全占 ⇒ 明确日志 + 后台退避重试, 返回 False 不抛(R2/S2)"""
        if self._try_bind():
            self._after_bind()
            return True
        logger.warning(
            f"HR 发现端点候选端口 {self._candidates_text()} 全部被占 —— 发现不可用"
            "(数据端点照常服务, 扩展可退手动配置); 将按 "
            f"{RETRY_MIN_S:g}s 起步、上限 {RETRY_MAX_S:g}s 退避重试, 占用者退出后自动接管"
        )
        self._retry_thread.start(self._retry_loop, "auto-qb-hr-discovery-retry")
        return False

    def stop(self, timeout: float = DISCOVERY_STOP_TIMEOUT) -> bool:
        """停止发现端点与全部附属线程(重试/心跳); 幂等"""
        self._retry_stop.set()
        self._retry_thread.stop(log=logger, subject="HR 发现端点重试线程", timeout=timeout, request_stop=self._retry_stop.set)
        ok = True
        with self._lifecycle_lock:
            handle, self._handle = self._handle, None
            self._bound_port = 0
        if handle is not None:
            ok = handle.stop(timeout)
        self._heartbeat_stop.set()
        self._heartbeat_thread.stop(
            log=logger, subject="HR 发现端点心跳线程", timeout=timeout, request_stop=self._heartbeat_stop.set
        )
        return ok

    def status(self, *, enabled: bool = True) -> HrDiscoveryStatus:
        """自检快照; note 只在未监听时给一句话(监听态的发现/配对/数据组合由数据端点 note 承载)"""
        listening = self.started
        return HrDiscoveryStatus(
            enabled=enabled,
            listening=listening,
            port=self.port,
            bound_port=self._bound_port,
            candidates=tuple(self.candidates),
            pairing_required=self.pairing_required,
            note="" if listening else "发现端点未在监听(候选端口被占时后台重试中)",
        )

    # ---------- 路由(纯逻辑, 不碰 socket) ----------

    def route(self,
              method: str,
              path: str,
              headers: Any,
              body: bytes = b"",
              source: str = "") -> Tuple[int, Dict[str, str], bytes]:
        """HTTP 请求 -> (状态码, 响应头, 响应体)。origin 门 + 配对门全在这里, 便于直接钉死。

        !它本身就是发 token 的端点, 所以**免 token**(先有鸡还是先有蛋); 两道关:
        ① origin 白名单(与数据端点第二道防线同一机制, 配了 extension_id 只认那一个);
        ② 配对码(仅非回环可达时强制, S3)。
        """
        del body
        origin = _header(headers, ORIGIN_HEADER)
        cors: Dict[str, str] = {}
        if not origin_allowed(origin, self.extension_id):
            self._reject.note("origin", f"发现端点拒绝非白名单 origin: {origin or '(空)'}")
            return 403, {}, _json({"error": "origin not allowed"})
        if origin:
            cors["Access-Control-Allow-Origin"] = origin
            cors["Vary"] = "Origin"
        route_path = path.split("?", 1)[0]
        if method == "OPTIONS":
            # 预检与数据端点同口径(浏览器预检不带自定义头, 配对门不能拦它)
            return 204, {
                **cors,
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": f"{PAIRING_HEADER}, Content-Type",
                "Access-Control-Max-Age": "600",
            }, b""
        if self.pairing_required:
            given = _header(headers, PAIRING_HEADER).strip()
            if not given:
                self._note_pairing_fail(source, "缺配对码")
                return 401, {**cors}, _json({"error": "pairing_required"})
            if not self._pairing_ok(given):
                self._note_pairing_fail(source, "配对码不符")
                return 401, {**cors}, _json({"error": "pairing_invalid"})
        if method != "GET" or route_path != API_DISCOVER:
            return 404, cors, _json({"error": "not found"})
        return 200, {**cors, "Cache-Control": "no-store"}, self._discover_response(headers)

    # ---------- 内部 ----------

    def _pairing_ok(self, given: str) -> bool:
        """常数时间比对展示码与凭证两种等价形态(S3); 密钥未生成 = 永不通过(不该发生)"""
        if not self.pairing_secret:
            return False
        return secrets.compare_digest(given, pairing_display_code(
            self.pairing_secret
        )) or secrets.compare_digest(given, pairing_credential(self.pairing_secret))

    def _note_pairing_fail(self, source: str, detail: str) -> None:
        """配对失败记账(C3 防枚举): 节流日志 + 每来源 60s 窗口简单计数, 超阈临时静默

        静默 = 超阈窗口内不再打日志(响应照常 401) —— 10^6 空间 × 5 次/分钟 ⇒ 爆破在量级上
        不可行, 日志面也不给逐条刷屏; 与 RejectThrottle 的长周期节流叠加。
        """
        now = self._now()
        flooded = False
        first_flood = False
        with self._pair_fail_lock:
            rec = self._pair_fail_times.setdefault(source, {"times": [], "warned": False})
            rec["times"] = [t for t in rec["times"] if now - t < 60.0]
            rec["times"].append(now)
            flooded = len(rec["times"]) > PAIRING_FAIL_LIMIT_PER_MIN
            if flooded and not rec["warned"]:
                rec["warned"] = True
                first_flood = True
            elif not flooded:
                rec["warned"] = False
        if first_flood:
            self._reject.note(
                "pairing-flood",
                f"发现端点配对失败频率超限(来源 {source or '未知'}), 60s 窗口内临时静默",
            )
        elif not flooded:
            self._reject.note("pairing", f"发现端点配对失败({detail}), 来源 {source or '未知'}")
        else:
            logger.debug(f"HR 取数通道 | 发现端点配对失败(已静默): {detail}, 来源 {source or '未知'}")

    def _discover_response(self, headers: Any) -> bytes:
        """实例聚合(心跳 + TTL 过滤); host=0.0.0.0 时按请求 Host 头替换自述主机部分(S2 ④)"""
        now = self._now()
        entries = self.registry.alive(ttl=INSTANCE_TTL_S, now=now) if self.registry is not None else []
        wildcard = _is_wildcard_host(self.host)
        host = _host_of_hostport(_header(headers, "Host")) if wildcard else ""
        instances = []
        for e in entries:
            endpoint = str(e.get("endpoint") or "")
            if wildcard and host:
                endpoint = _replace_url_host(endpoint, host)
            instances.append(
                {
                    "id": str(e.get("id") or ""),
                    "name": str(e.get("name") or ""),
                    "endpoint": endpoint,
                    "token": str(e.get("token") or ""),
                }
            )
        return _json({"instances": instances, "server_time": round(now, 3)})

    # ---------- 绑定 / 心跳 / 重试 ----------

    def _candidates_text(self) -> str:
        return "/".join(str(p) for p in self.candidates)

    def _try_bind(self) -> bool:
        """依次试绑候选表, 取第一个空位; 独占口径与数据端点同款(allow_reuse_address=False)"""
        for port in self.candidates:
            try:
                server = _EndpointServer((self.host, port), self._make_handler())
            except OSError as e:
                logger.debug(f"HR 发现端点候选端口 {port} 绑定失败: {e}")
                continue
            thread = HrThreadHandle()
            thread.start(server.serve_forever, "auto-qb-hr-discovery")
            with self._lifecycle_lock:
                self._handle = HrEndpointHandle(server, thread, server.server_address[1])
                self._bound_port = server.server_address[1]
            return True
        return False

    def _after_bind(self) -> None:
        """绑定成功后的公共收尾: 日志 + 心跳线程 + 立即登记一次(扩展不必等满一个心跳周期)"""
        logger.info(
            f"HR 发现端点已启动: {API_DISCOVER} @ http://{self.host}:{self._bound_port}"
            f"(候选 {self._candidates_text()}, 实绑 {self._bound_port})"
        )
        self._heartbeat_stop.clear()
        self._heartbeat_thread.start(self._heartbeat_loop, "auto-qb-hr-discovery-heartbeat")
        self._heartbeat_once()

    def _retry_loop(self) -> None:
        """后台退避重试(C8): 占用者退出后自动接管(翻转旧「归属者退出不接管」限制, R6)

        只做绑定尝试与端点启停, 不碰任务队列与 state_file(单一写线程假设不破);
        不杀占用进程、不抢绑(见模块 docstring)。
        """
        delay = self.retry_min_s
        while not self._retry_stop.is_set():
            if self._retry_stop.wait(delay):
                return
            if self._try_bind():
                logger.info(f"HR 发现端点已接管候选端口: 实绑 {self._bound_port}(原占用者已退出)")
                self._after_bind()
                return
            delay = min(delay * 2, self.retry_max_s)

    def _heartbeat_loop(self) -> None:
        while not self._heartbeat_stop.wait(HEARTBEAT_INTERVAL_S):
            self._heartbeat_once()

    def _heartbeat_once(self) -> None:
        """登记/刷新自身条目(30s 心跳, C1); 注册表任何异常都不打断发现服务"""
        if self.registry is None:
            return
        try:
            self.registry.upsert(
                entry_id=self.entry_id,
                name=self.entry_name,
                endpoint=self.endpoint_fn() or "",
                token=self.token,
                ts=self._now(),
            )
        except Exception as e:
            logger.error(f"HR 实例注册表心跳失败(下一周期重试): {e}", exc_info=True)

    def _make_handler(self):
        # 经 self 现取 route(不绑死方法对象): 测试期 monkeypatch 实例属性才拦得住
        return make_endpoint_handler(
            lambda *args, **kwargs: self.route(*args, **kwargs),
            banner="auto-qb-hr-discovery/1.0",
            access_log_prefix="HR 发现端点",
            error_tag="HR 发现端点"
        )


__all__ = [
    "API_DISCOVER",
    "DISCOVERY_CANDIDATES",
    "DISCOVERY_DEFAULT_PORT",
    "HEARTBEAT_INTERVAL_S",
    "HrDiscoveryServer",
    "HrDiscoveryStatus",
    "INSTANCE_TTL_S",
    "InstanceRegistry",
    "PAIRING_FAIL_LIMIT_PER_MIN",
    "PAIRING_HEADER",
    "RETRY_MAX_S",
    "RETRY_MIN_S",
    "default_registry_path",
    "discovery_candidates",
]
