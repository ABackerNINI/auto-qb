"""取数通道抽象: 「拿到 HR 页 HTML / .torrent 字节」的唯一出口。

硬约束(计划 §6): **后端自己不发起站点请求, 也不持有 cookie** —— 取数由浏览器扩展在真实
登录态下完成, 后端只收数据。故本模块只定义协议与错误类型:

- `HrFetcher` 是 Protocol(结构性类型): 任何提供 `get_text` / `get_bytes` 的对象都能当通道,
  于是轮询拉取式通道(M2 的本地端点 + 扩展)、测试用的假通道、离线 fixture 通道可以互换。
- `NullFetcher` 用于「本实例没有可用通道」(channel.enabled=false): 调用即抛 `HrChannelUnavailable`,
  由 service 转成「未核实 + 通道静默」, **绝不静默降级为后端直连**(那会破坏零 cookie 边界)。
- `ChannelFetcher`(M2)是**真通道**: 把请求变成一条任务投给浏览器扩展, 阻塞等回传(有上限)。
"""
import time
from typing import Callable, Optional, Protocol, runtime_checkable

from .channel import KIND_EXT_QUOTA, KIND_LOGIN_PAGE, TASK_PAGE, TASK_TORRENT, HrResult, UrlPolicy
from .queue import HrTaskQueue


class HrFetchError(RuntimeError):
    """取数失败(超时 / HTTP 失败 / 返回非预期内容)。由 service 计入失败退避与熔断。"""
    def __init__(self, message: str, *, retry_after: float = 0.0) -> None:
        super().__init__(message)
        #: 站点给出的 Retry-After(秒); 0 = 未给出, 走指数退避
        self.retry_after = retry_after


class HrChannelUnavailable(HrFetchError):
    """本实例没有可用取数通道(未启用 channel / 浏览器未开 / 扩展被停用)"""


class HrChannelStopped(HrChannelUnavailable):
    """取数被**叫停**(关停进程 / 热重挂端点时的主动放弃)

    ❗与「没通道」分开: 这是程序自己决定的非事件 —— 若按「无可用取数通道」告警, 每次关停 (和每次改
    端口) 都会弹一条系统通知, 而那明明是预期行为(2026-09-24 用户实报「一开/一关就弹 warning」)。
    也不计失败次数: 叫停不是取数失败, 不该推进熔断。
    """


class HrChannelQuota(HrChannelUnavailable):
    """**扩展侧硬上限**挡下了这次请求(第二道闸)

    后端自己有频控(间隔 + 配额 + 熔断), 扩展再独立计一层数(访问 10/时·50/天, 下种 50/时·200/天)
    —— 这是为了「后端代码写错 / 配置被改坏」时也打不爆站点。

    ❗由此触发说明**后端频控失效了**, 但**不能计成取数失败**: 那会把站点推进熔断、把一个配置/
    逻辑问题掩盖成「站点坏了」。故 service 把它归到「本轮让位」——不计失败、不推进熔断、
    告警只报一次(否则超限期内每轮一条, 变成刷屏)。
    """


class HrLoginExpired(HrFetchError):
    """站点页面是**登录页** ⇒ 浏览器里的登录态失效(M4 四类事件之一)

    ❗与其它取数失败分开的理由(与 `HrChannelStopped` / `HrChannelQuota` 同一套判据: **能不能靠重试解决**):
    - 超时 / HTTP 失败可以重试, 所以计失败 + 退避熔断;
    - 登录失效**重试一万次也一样** —— 只有人去浏览器登录才会好。若把它计入熔断, 用户只会看到
      「连续失败达阈值, 熔断至 …」, 而真正的动作要求(「去登录」)被埋掉; 反过来, 熔断冷却还会让
      用户登录完继续白等一个冷却周期才恢复。

    故 service 对它: **不计失败、不推进熔断**, 只报一次 WARNING(文案直接给动作), 并把原因写进
    站点文件的 `refresh.reason`(失败路径里唯一持久可见的痕迹) —— 不碰 fetched_at / 覆盖证明 /
    新鲜度基准, 所以证据链不会被动。
    """


@runtime_checkable
class HrFetcher(Protocol):
    """取数通道协议: 只负责「按 URL 取内容」, 无策略、无解析、不碰 cookie"""
    def get_text(self, url: str) -> str:
        """取文本(HR 统计页 HTML)"""

    def get_bytes(self, url: str) -> bytes:
        """取二进制(.torrent)"""


class NullFetcher:
    """无通道占位: 任何请求都报「通道不可用」, 让上层的语义退化为保守而非静默直连"""
    def __init__(self, reason: str = "本实例未启用取数通道 (hr_check.channel.enabled=false)") -> None:
        self._reason = reason

    def get_text(self, url: str) -> str:
        raise HrChannelUnavailable(f"{self._reason}: {url}")

    def get_bytes(self, url: str) -> bytes:
        raise HrChannelUnavailable(f"{self._reason}: {url}")


def is_available(fetcher: HrFetcher) -> bool:
    """通道是否为真通道(供报告与展示; NullFetcher 视为不可用)"""
    return not isinstance(fetcher, NullFetcher)


class ChannelFetcher:
    """真通道(M2): 把取数请求交给浏览器扩展, 阻塞等回传。

    为什么是**阻塞**的: 本对象只在取数线程里被调用, 而取数线程持站点锁、与主循环 2s 节拍
    完全解耦(计划 §8) —— 「抓数据等几分钟」只发生在该线程内, 卡不住主循环。

    `request_timeout` 必须有: 扩展中途被关掉时, 若无人叫停, 持锁的取数线程会永久挂住,
    该站点就再也不会被刷新(而且锁也永远不释放)—— 超时即按一次失败计, 交给退避熔断处理。

    ❗URL 先过 `UrlPolicy`(域名 + 路径白名单)再下发: 端点绝不成为「带登录态的任意站代理」。
    """
    def __init__(
        self,
        queue: HrTaskQueue,
        *,
        policy: UrlPolicy,
        request_timeout: float = 180.0,
        now_fn: Callable[[], float] = time.time,
    ) -> None:
        self.queue = queue
        self.policy = policy
        self.request_timeout = float(request_timeout)
        self._now = now_fn
        #: 便于报告与排障: 本实例实际下发的任务数(不代表配额)
        self.requests = 0

    def get_text(self, url: str) -> str:
        return self._fetch(url, TASK_PAGE, scope=_scope_of(url)).text

    def get_bytes(self, url: str) -> bytes:
        return self._fetch(url, TASK_TORRENT, tid=_tid_of(url)).body

    def _fetch(self, url: str, kind: str, *, scope: str = "", tid: int = 0) -> HrResult:
        if self.queue.cancel_reason:
            # 通道已叫停(关停路径): 连任务都不下发, 直接如实上报「被叫停」(不是「没通道」)
            raise HrChannelStopped(f"取数通道已停止({self.queue.cancel_reason}): {url}")
        site = self.policy.require(url)  # 白名单外直接抛 HrChannelError -> service 记失败
        task = self.queue.put(site, kind, url, scope=scope, tid=tid)
        self.requests += 1
        result = self.queue.wait(task.task_id, self.request_timeout)
        if result is None:
            # 区分「被叫停」与「等超时」: 前者是关停路径(不该算一次失败), 后者才计入退避熔断
            if self.queue.cancel_reason:
                raise HrChannelStopped(f"取数通道已停止({self.queue.cancel_reason}), 本轮放弃: {url}")
            raise HrFetchError(f"等待浏览器扩展取数超时({self.request_timeout:.0f}s): {url}"
                               "(浏览器是否在运行 / 扩展是否启用 / 是否已登录站点?)")
        if not result.ok:
            detail = result.error or f"HTTP {result.status}"
            if result.kind == KIND_LOGIN_PAGE:
                # 扩展取 .torrent 拿到的是 HTML(登录页 / 未登录): 与页面命中登录页同一语义 ——
                # 只有人工登录才会好, 不计取数失败(HrLoginExpired 分支: 不推熔断、每站报一次)
                raise HrLoginExpired(f"扩展取到登录页而非内容({detail}): {url}")
            if result.kind == KIND_EXT_QUOTA:
                raise HrChannelQuota(f"扩展侧硬上限挡下取数({detail}): {url}", retry_after=result.retry_after)
            raise HrFetchError(f"扩展取数失败({detail}): {url}", retry_after=result.retry_after)
        if not result.body:
            raise HrFetchError(f"扩展回传内容为空: {url}")
        return result


def _scope_of(url: str) -> str:
    """从 URL 取档位(`hrtype=A`)—— 仅供排障展示, 解析不看它"""
    for part in url.split("?", 1)[-1].split("&"):
        if part.startswith("hrtype="):
            return part.split("=", 1)[1]
    return ""


def _tid_of(url: str) -> int:
    """从 URL 取种子 id(`id=123`)—— 仅供排障展示"""
    for part in url.split("?", 1)[-1].split("&"):
        if part.startswith("id="):
            try:
                return int(part.split("=", 1)[1])
            except ValueError:
                return 0
    return 0


def build_channel_fetcher(
    *,
    channel_conf,
    enabled: bool,
    queue: HrTaskQueue,
    site_confs,
) -> HrFetcher:
    """按配置决定「真通道」还是「空通道」——**唯一**的分支点

    `channel.enabled=false`(未装扩展 / 未启用)时返回 `NullFetcher`: 上层如实报「无可用
    取数通道」并保守回落未核实, 而不是偷偷改成后端直连。
    """
    if not enabled or not channel_conf.enabled:
        return NullFetcher("本实例未启用取数通道 (hr_check.channel.enabled=false): 装上浏览器扩展并开启后才会在线核实")
    return ChannelFetcher(
        queue, policy=UrlPolicy(site_confs), request_timeout=getattr(channel_conf, "request_timeout", 180.0)
    )


__all__ = [
    "ChannelFetcher", "HrChannelQuota", "HrChannelStopped", "HrChannelUnavailable", "HrFetchError", "HrFetcher",
    "HrLoginExpired", "NullFetcher", "build_channel_fetcher", "is_available"
]
