"""取数通道抽象: 「拿到 HR 页 HTML / .torrent 字节」的唯一出口。

硬约束(计划 §6): **后端自己不发起站点请求, 也不持有 cookie** —— 取数由浏览器扩展在真实
登录态下完成, 后端只收数据。故本模块只定义协议与错误类型:

- `HrFetcher` 是 Protocol(结构性类型): 任何提供 `get_text` / `get_bytes` 的对象都能当通道,
  于是轮询拉取式通道(M2 的本地端点 + 扩展)、测试用的假通道、离线 fixture 通道可以互换。
- `NullFetcher` 用于「本实例没有可用通道」(channel.enabled=false): 调用即抛 `HrChannelUnavailable`,
  由 service 转成「未核实 + 通道静默」, **绝不静默降级为后端直连**(那会破坏零 cookie 边界)。
"""
from typing import Protocol, runtime_checkable


class HrFetchError(RuntimeError):
    """取数失败(超时 / HTTP 失败 / 返回非预期内容)。由 service 计入失败退避与熔断。"""
    def __init__(self, message: str, *, retry_after: float = 0.0) -> None:
        super().__init__(message)
        #: 站点给出的 Retry-After(秒); 0 = 未给出, 走指数退避
        self.retry_after = retry_after


class HrChannelUnavailable(HrFetchError):
    """本实例没有可用取数通道(未启用 channel / 浏览器未开 / 扩展被停用)"""


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
