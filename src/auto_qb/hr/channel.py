"""取数通道协议与安全边界(计划 §6/§7 · M2): 「扩展要什么 / 回传什么」的唯一口径。

三段职责(端点线程 / 取数线程 / 浏览器扩展)靠本模块对齐:

- `HrTask` / `HrResult` —— 后端与扩展之间的**唯一**数据契约(JSON 往返, 只经 127.0.0.1 loopback);
- `resolve_token` / `origin_allowed` / `UrlPolicy` —— 三道边界。**真鉴权是 token**, origin 白名单
  只是第二道(扩展形态不影响能力, 但 id 未必定得住), URL 白名单(SSRF)保证端点不会退化成
  「带登录态的任意站代理」;
- 纯函数、零网络 I/O(只有 token 落盘), 便于 pytest 直接钉死。

❗**凭据面归零**(计划 §6): 协议里没有 cookie / passkey 字段 —— 后端既不接收也不转发浏览器凭据,
  登录态只存在于浏览器上下文; 扩展取到的只有「HTML 文本」与「.torrent 二进制」。
"""
import base64
import binascii
import json
import logging
import os
import re
import secrets
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Tuple

from ..config.models import SiteHrCheckConfig
from ..infra.errors import AutoQbError

logger = logging.getLogger(__name__)

# ---------- 端点契约 ----------

#: 扩展拉清单(GET) / 回传结果(POST)
API_TASKS = "/api/hr/tasks"
API_RESULT = "/api/hr/result"
#: 鉴权头(扩展逐实例填自己的 token)
TOKEN_HEADER = "X-Hr-Token"
ORIGIN_HEADER = "Origin"

#: 任务类型: page = HR 统计页(取渲染后 DOM); torrent = .torrent 二进制
TASK_PAGE = "page"
TASK_TORRENT = "torrent"
TASK_KINDS = (TASK_PAGE, TASK_TORRENT)

#: 建议的扩展轮询节奏(秒); 扩展侧用 chrome.alarms(最小 1 分钟), 这里只作提示回传给扩展
DEFAULT_POLL_HINT = 300.0

#: 单次请求体上限(含 base64 膨胀) —— 防任意网页 JS 向 loopback 灌大体积数据打爆内存
MAX_BODY_BYTES = 12 * 1024 * 1024
#: 单次拉清单最多拿走的任务数(扩展并发上限; 后端不限总量, 防一次拉走整轮翻页)
MAX_BATCH = 16

#: 扩展 origin 前缀: 只有扩展页面/service worker 会带它; 普通网页一律拒
EXTENSION_ORIGIN_PREFIX = "chrome-extension://"
#: Chrome 扩展 id: 32 位 a~p(配置里写了就按它钉死 origin)
EXTENSION_ID_RE = re.compile(r"^[a-p]{32}$")

#: 结果 kind: 扩展侧**硬上限**挡下了这次请求
#: ❗扩展有自己的独立计数(第二道闸: 访问 10/时·50/天, 下种 50/时·200/天), 超限即拒发。
#: 它与「取数失败」必须分开: 频控让位不是故障, 计成失败会把站点推进熔断、把「后端频控失效」
#: 这个真问题掩盖成「站点坏了」。
KIND_EXT_QUOTA = "ext-quota"


class HrChannelError(RuntimeError):
    """通道层面的错误(畸形回传 / 非法 URL / 任务不匹配)"""


class HrChannelBindError(AutoQbError, HrChannelError):
    """端点启动失败(端口被占用 / 监听失败)。**启动即报错**, 不静默降级(计划 §7)。

    同时是 AutoQbError ⇒ 由 CLI 单点捕获、stderr 干净输出、退出码 1(不带堆栈)。
    """


# ---------- 密钥 ----------


def token_path(data_dir: str) -> str:
    """通道密钥文件路径(与 web.token 同处境, 便于用户一处管理)"""
    return os.path.join(data_dir, "hr.token")


def resolve_token(configured: str, data_dir: str) -> str:
    """确定通道密钥: 显式配置优先; 否则随机生成并持久化到 data_dir/hr.token(0600)(同 web.token 口径)"""
    if configured:
        return configured
    path = token_path(data_dir)
    if os.path.exists(path):
        with open(path, "r", encoding="ascii") as f:
            token = f.read().strip()
        if token:
            return token
    token = secrets.token_hex(32)
    os.makedirs(data_dir, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="ascii") as f:
        f.write(token)
    # 密钥内容**不进日志**: 日志会被 notify 处理器推到系统通知, 也被 /api/log 读回 ——
    # 拿到密钥等于拿到「驱动本机浏览器带登录态请求站点」的能力。只提示文件路径。
    logger.info(f"HR 取数通道密钥已生成: {path}(密钥内容只存该文件、不打印到日志, 需查看请打开它)")
    return token


# ---------- 边界: origin 与 URL ----------


def origin_allowed(origin: str, extension_id: str = "") -> bool:
    """CORS origin 白名单(纵深防御, 非唯一防线)

    - 无 Origin: 放行 —— 扩展 service worker 的请求未必带 Origin, 且**真鉴权是 token**;
    - 非扩展 origin(普通网页 JS): 一律拒 —— 否则任意站点都能向 localhost 投伪造数据;
    - 配了 `channel.extension_id`: 只认那一个扩展 id(推荐); 留空则放行任意扩展 origin。
    """
    if not origin:
        return True
    if not origin.startswith(EXTENSION_ORIGIN_PREFIX):
        return False
    if not extension_id:
        return True
    return origin == EXTENSION_ORIGIN_PREFIX + extension_id


class UrlPolicy:
    """URL 白名单(SSRF 边界): **只允许配置里声明的站点域名与受限路径**

    后端自己不取数, 但扩展会带着登录态去取 —— 若端点能被诱导下发任意 URL, 它就变成了
    「任意站代理」。故任务 URL 只能由后端按配置拼出, 且发放前必须过这里。
    """
    def __init__(self, site_confs: Mapping[str, SiteHrCheckConfig]) -> None:
        self._hosts: Dict[str, Tuple[str, Tuple[str, ...]]] = {}
        for site, conf in site_confs.items():
            host = host_of(conf.hr_page_url)
            if not host:
                continue
            paths = {path_of(conf.hr_page_url)}
            dl = path_of(_absolute_download(conf))
            if dl:
                paths.add(dl)
            self._hosts[site] = (host, tuple(sorted(p for p in paths if p)))

    def site_of(self, url: str) -> str:
        """URL 属于哪个站点(未登记返回空串)"""
        host = host_of(url)
        if not host:
            return ""
        for site, (site_host, _paths) in self._hosts.items():
            if site_host == host:
                return site
        return ""

    def allows(self, site: str, url: str) -> bool:
        """该站点的任务 URL 是否在白名单内(域名一致 + 路径受限 + scheme 合法)"""
        got = self._hosts.get(site)
        if got is None:
            return False
        host, paths = got
        if host_of(url) != host or path_of(url) not in paths:
            return False
        return _scheme_of(url) in ("http", "https")

    def require(self, url: str) -> str:
        """校验并返回该 URL 的站点名; 不合法抛 HrChannelError(发任务前调用 = fail-fast)"""
        site = self.site_of(url)
        if not site or not self.allows(site, url):
            raise HrChannelError(f"URL 不在站点白名单内, 拒绝下发(SSRF 边界): {url}")
        return site


def _absolute_download(conf: SiteHrCheckConfig) -> str:
    """把相对 download_path 拼成绝对 URL(只用于取路径与域名; {id} 占位不解析)"""
    base = conf.hr_page_url
    if not base:
        return conf.download_path
    root = base.split("://", 1)[-1]
    root = root.split("/", 1)[0]
    scheme = base.split("://", 1)[0] if "://" in base else "https"
    return f"{scheme}://{root}{conf.download_path}"


def _scheme_of(url: str) -> str:
    return url.split("://", 1)[0].lower() if "://" in url else ""


def host_of(url: str) -> str:
    """URL 的 host(不含端口; 无 scheme 返回空串)"""
    if not _scheme_of(url):
        return ""
    rest = url.split("://", 1)[1]
    return rest.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0].split(":", 1)[0].lower()


def path_of(url: str) -> str:
    """URL 的路径(无 scheme 或无路径返回空串; 尾斜杠算根路径 `/`)"""
    if not _scheme_of(url):
        return ""
    rest = url.split("://", 1)[1]
    if "/" not in rest:
        return ""
    path = rest.split("/", 1)[1].split("?", 1)[0].split("#", 1)[0]
    return "/" + path if path else "/"


# ---------- 任务与结果 ----------


@dataclass(slots=True)
class HrTask:
    """一条取数任务(后端 -> 扩展): 只含「取哪个 URL」, 不含任何凭据与策略"""

    task_id: str
    kind: str
    url: str
    site: str
    scope: str = ""
    tid: int = 0
    #: 便于排障与展示: 任务在队列里排到的时刻(扩展不据此决策, 频控唯一权威在后端)
    dispatched_at: float = 0.0

    def to_json(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {"id": self.task_id, "kind": self.kind, "url": self.url, "site": self.site}
        if self.scope:
            out["scope"] = self.scope
        if self.tid:
            out["tid"] = self.tid
        return out


@dataclass(slots=True)
class HrResult:
    """扩展回传的一条结果。`body` 是**原样字节**(HTML 或 .torrent), 后端自己解析。"""

    task_id: str
    ok: bool = False
    status: int = 0
    url: str = ""
    body: bytes = b""
    error: str = ""
    retry_after: float = 0.0
    received_at: float = 0.0
    #: 扩展侧的错误分类(空 = 普通取数失败); 目前只有 KIND_EXT_QUOTA
    kind: str = ""

    @property
    def text(self) -> str:
        """按 UTF-8 解码(容错): 页面编码异常不该让整轮刷新失败"""
        return self.body.decode("utf-8", "replace")

    def to_json(self) -> Dict[str, Any]:
        """序列化为线上格式(仅测试与自检用; 生产只由扩展生成)"""
        out: Dict[str, Any] = {
            "id": self.task_id,
            "ok": self.ok,
            "status": self.status,
            "url": self.url,
            "body_b64": base64.b64encode(self.body).decode("ascii"),
        }
        if self.error:
            out["error"] = self.error
        if self.retry_after:
            out["retry_after"] = self.retry_after
        if self.kind:
            out["kind"] = self.kind
        return out

    @classmethod
    def from_json(cls, raw: Any) -> "HrResult":
        """解析扩展回传(畸形输入一律抛 HrChannelError => 端点回 400, 不入库、不崩)"""
        if not isinstance(raw, dict):
            raise HrChannelError("结果项不是 JSON 对象")
        task_id = str(raw.get("id") or "").strip()
        if not task_id:
            raise HrChannelError("结果项缺少 id")
        ok = bool(raw.get("ok"))
        result = cls(
            task_id=task_id,
            ok=ok,
            status=_as_int(raw.get("status")),
            url=str(raw.get("url") or ""),
            error=str(raw.get("error") or ""),
            retry_after=_as_float(raw.get("retry_after")),
            kind=str(raw.get("kind") or ""),
        )
        body_b64 = raw.get("body_b64")
        text = raw.get("text")
        if body_b64 is not None:
            if not isinstance(body_b64, str):
                raise HrChannelError("body_b64 必须是 base64 字符串")
            try:
                result.body = base64.b64decode(body_b64, validate=True)
            except (binascii.Error, ValueError) as e:
                raise HrChannelError(f"body_b64 不是合法 base64: {e}") from e
        elif text is not None:
            if not isinstance(text, str):
                raise HrChannelError("text 必须是字符串")
            result.body = text.encode("utf-8")
        elif ok:
            raise HrChannelError("成功结果必须带 body_b64(二进制)或 text(HTML)")
        return result


def parse_results(payload: Any) -> List[HrResult]:
    """解析 POST /api/hr/result 请求体: 接受单条或 `{"results": [...]}` 批量"""
    if isinstance(payload, dict) and "results" in payload:
        items = payload["results"]
        if not isinstance(items, list):
            raise HrChannelError("results 必须是数组")
    elif isinstance(payload, list):
        items = payload
    else:
        items = [payload]
    return [HrResult.from_json(item) for item in items]


def decode_json(body: bytes) -> Any:
    """请求体 -> JSON(畸形一律 HrChannelError)"""
    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise HrChannelError(f"请求体不是合法 JSON: {e}") from e


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@dataclass(slots=True)
class ChannelStatus:
    """通道自检快照(供 hr.once 报告与展示; 不含密钥内容)"""

    enabled: bool = False
    listening: bool = False
    port: int = 0
    endpoint: str = ""
    token_source: str = "none"  # none | config | file
    last_contact_ts: float = 0.0
    pending: int = 0
    extensions_seen: List[str] = field(default_factory=list)
    note: str = ""

    @property
    def silent_for(self) -> float:
        return 0.0 if not self.last_contact_ts else max(0.0, time.time() - self.last_contact_ts)


def describe_token_source(configured: str, data_dir: str) -> str:
    """密钥来源(只报来源, 不报内容)"""
    if configured:
        return "config"
    return "file" if os.path.exists(token_path(data_dir)) else "none"


__all__ = [
    "API_RESULT",
    "API_TASKS",
    "DEFAULT_POLL_HINT",
    "EXTENSION_ID_RE",
    "EXTENSION_ORIGIN_PREFIX",
    "MAX_BATCH",
    "MAX_BODY_BYTES",
    "ORIGIN_HEADER",
    "TASK_KINDS",
    "TASK_PAGE",
    "TASK_TORRENT",
    "TOKEN_HEADER",
    "ChannelStatus",
    "HrChannelBindError",
    "HrChannelError",
    "HrResult",
    "HrTask",
    "UrlPolicy",
    "decode_json",
    "describe_token_source",
    "host_of",
    "origin_allowed",
    "parse_results",
    "path_of",
    "resolve_token",
    "token_path",
]
