"""test_hr_fetcher_channel 测试计划: ChannelFetcher(真通道)与 build_channel_fetcher 的选择口径

## 测试计划(每个测试函数一条)
- test_build_returns_null_when_channel_disabled: channel.enabled=false 或功能未启用 -> NullFetcher
- test_build_returns_channel_fetcher_when_enabled: 都启用 -> ChannelFetcher(不是 NullFetcher)
- test_get_text_dispatches_task_and_returns_body: 取数线程发起 -> 任务上队 -> 回传后拿到文本
- test_get_bytes_returns_binary: .torrent 走二进制路径, 任务带 tid
- test_timeout_raises_fetch_error: 无人回传 => 超时抛 HrFetchError(不能让持锁线程永久挂住)
- test_extension_failure_becomes_fetch_error: 扩展报失败(含 Retry-After) -> HrFetchError 带 retry_after
- test_extension_quota_refusal_is_not_a_fetch_failure: 扩展侧硬上限拒发(kind=ext-quota) -> HrChannelQuota
  (子类, 与「取数失败」分开: 不计失败/不推熔断)
- test_login_page_result_is_not_a_fetch_failure: 扩展取 .torrent 拿到登录页(kind=login-page) -> HrLoginExpired
  (只有人工登录才会好, 不计失败/不推熔断 —— 2026-09-25 实报: SameSite 剥 cookie 时 download.php 返回 HTML,
  若按普通失败计数会烧掉该 tid 的重试额度)
- test_empty_body_is_failure: 回传成功但内容为空 -> 失败(不给解析器喂空页面)
- test_unlisted_url_raises_before_dispatch: 白名单外 URL 直接拒, **任务都不下发**(SSRF 边界)
- test_cancelled_queue_reports_channel_unavailable: 通道被叫停 -> HrChannelStopped(可区分, 不计失败/熔断)
- test_requests_counter: 排障用的下发计数
"""
import threading

import pytest

from auto_qb.config.models import HrChannelConfig
from auto_qb.hr.channel import KIND_EXT_QUOTA, KIND_LOGIN_PAGE, HrChannelError, HrResult, UrlPolicy
from auto_qb.hr.fetcher import (
    ChannelFetcher,
    HrChannelQuota,
    HrChannelStopped,
    HrChannelUnavailable,
    HrFetchError,
    HrLoginExpired,
    NullFetcher,
    build_channel_fetcher,
    is_available,
)
from auto_qb.hr.queue import HrTaskQueue
from hr_helpers import site_conf

URL = "https://pt.example.com/myhr.php?hrtype=A"
DL = "https://pt.example.com/download.php?id=313852"


class _Auto:
    """自动应答的假扩展: 后台线程把队列里的任务取走并回传(模拟真扩展的拉取式行为)"""
    def __init__(self, queue, *, answer=b"<html>ok</html>", ok=True, error="", retry_after=0.0, delay=0.0, kind=""):
        self.queue = queue
        self.answer = answer
        self.ok = ok
        self.error = error
        self.retry_after = retry_after
        self.kind = kind
        self.delay = delay
        self._stop = threading.Event()
        self.seen = []
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        while not self._stop.is_set():
            for task in self.queue.take_batch():
                self.seen.append(task)
                if self.delay:
                    self._stop.wait(self.delay)
                body = self.answer if task.kind == "page" else b"d4:infod4:name1:xee"
                self.queue.submit(
                    HrResult(
                        task_id=task.task_id,
                        ok=self.ok,
                        url=task.url,
                        body=body,
                        error=self.error,
                        retry_after=self.retry_after,
                        kind=self.kind,
                    )
                )
            self._stop.wait(0.005)

    def close(self):
        self._stop.set()
        self._thread.join(1.0)


def make_fetcher(*, queue=None, timeout=2.0):
    """取数通道 + 其队列(策略只声明一个站点, 便于测白名单)"""
    queue = queue or HrTaskQueue()
    fetcher = ChannelFetcher(queue, policy=UrlPolicy({"pt.example.com": site_conf()}), request_timeout=timeout)
    return queue, fetcher


def test_build_returns_null_when_channel_disabled():
    conf = HrChannelConfig(enabled=False)
    null = build_channel_fetcher(channel_conf=conf, enabled=True, queue=HrTaskQueue(), site_confs={"s": site_conf()})
    assert isinstance(null, NullFetcher) and not is_available(null)
    also_null = build_channel_fetcher(
        channel_conf=HrChannelConfig(enabled=True), enabled=False, queue=HrTaskQueue(), site_confs={}
    )
    assert isinstance(also_null, NullFetcher)


def test_build_returns_channel_fetcher_when_enabled():
    got = build_channel_fetcher(
        channel_conf=HrChannelConfig(enabled=True, request_timeout=99.0),
        enabled=True,
        queue=HrTaskQueue(),
        site_confs={"pt.example.com": site_conf()},
    )
    assert isinstance(got, ChannelFetcher) and is_available(got)
    assert got.request_timeout == 99.0


def test_get_text_dispatches_task_and_returns_body():
    queue, fetcher = make_fetcher()
    auto = _Auto(queue)
    try:
        assert fetcher.get_text(URL) == "<html>ok</html>"
        assert auto.seen[0].kind == "page" and auto.seen[0].scope == "A"
    finally:
        auto.close()


def test_get_bytes_returns_binary():
    queue, fetcher = make_fetcher()
    auto = _Auto(queue)
    try:
        assert fetcher.get_bytes(DL).startswith(b"d4:info")
        assert auto.seen[0].kind == "torrent" and auto.seen[0].tid == 313852
    finally:
        auto.close()


def test_timeout_raises_fetch_error():
    queue, fetcher = make_fetcher(timeout=0.05)  # 没有假扩展应答
    with pytest.raises(HrFetchError) as err:
        fetcher.get_text(URL)
    assert "超时" in str(err.value)
    assert queue.pending() == 0, "超时后任务即作废, 不残留"


def test_extension_failure_becomes_fetch_error():
    queue, fetcher = make_fetcher()
    auto = _Auto(queue, ok=False, error="HTTP 429", retry_after=42.0, answer=b"")
    try:
        with pytest.raises(HrFetchError) as err:
            fetcher.get_text(URL)
        assert err.value.retry_after == 42.0, "站点给的 Retry-After 要透传给退避逻辑"
        assert "429" in str(err.value)
    finally:
        auto.close()


def test_extension_quota_refusal_is_not_a_fetch_failure():
    """扩展侧硬上限拒发(kind='ext-quota') ⇒ `HrChannelQuota`: 与「取数失败」分开

    扩展有自己的独立计数(第二道闸: 访问 10/时·50/天, 下种 50/时·200/天), 超限就拒发。它触发
    说明**后端频控没拦住** —— 那要被看见, 但不能计成取数失败: 否则会把站点推进熔断, 把配置/逻辑
    问题掩盖成「站点坏了」。
    """
    queue, fetcher = make_fetcher()
    auto = _Auto(
        queue,
        ok=False,
        answer=b"",
        error="HR 页访问 本小时达硬上限 10 次(host=pt.example.com)",
        retry_after=1800.0,
        kind=KIND_EXT_QUOTA,
    )
    try:
        with pytest.raises(HrChannelQuota) as err:
            fetcher.get_text(URL)
        assert isinstance(err.value, HrChannelUnavailable), "父类语义成立(调用方兼容)"
        assert err.value.retry_after == 1800.0, "下一次可取的时刻要透传(让上层知道等多久)"
        assert "硬上限" in str(err.value)
    finally:
        auto.close()


def test_login_page_result_is_not_a_fetch_failure():
    """扩展取 .torrent 拿到登录页(kind='login-page') ⇒ `HrLoginExpired`: 不计取数失败

    SameSite 剥 cookie / 登录态失效会让 download.php 返回 HTML 登录页 —— 只有人工登录才会好,
    若按普通失败计数, 三次就把该 tid 送进 12h 冷却, 真因(去登录)被「种子坏了」掩盖。
    """
    queue, fetcher = make_fetcher()
    auto = _Auto(
        queue,
        ok=False,
        answer=b"",
        error="download.php 返回 HTML(疑似登录页/未登录 —— 请在浏览器里登录该站点)",
        kind=KIND_LOGIN_PAGE,
    )
    try:
        with pytest.raises(HrLoginExpired):
            fetcher.get_bytes(DL)
    finally:
        auto.close()


def test_empty_body_is_failure():
    queue, fetcher = make_fetcher()
    auto = _Auto(queue, answer=b"")
    try:
        with pytest.raises(HrFetchError):
            fetcher.get_text(URL)
    finally:
        auto.close()


def test_unlisted_url_raises_before_dispatch():
    queue, fetcher = make_fetcher()
    with pytest.raises(HrChannelError):
        fetcher.get_text("https://evil.example.com/myhr.php")
    assert queue.pending() == 0, "白名单外 URL 连任务都不下发(SSRF 边界)"


def test_cancelled_queue_reports_channel_unavailable():
    """通道被叫停(关停/热重挂路径) -> `HrChannelStopped`: 与「没通道」分开, 不该计入失败与熔断

    必须是**子类**而不能只是父类: service 靠它把关停从「无可用取数通道」里分出去 ——
    否则每次关停 (与每次改端口) 都要弹一条系统通知(2026-09-24 用户实报)。
    """
    queue, fetcher = make_fetcher(timeout=30.0)
    queue.cancel_all("停止中")
    with pytest.raises(HrChannelStopped) as err:
        fetcher.get_text(URL)
    assert isinstance(err.value, HrChannelUnavailable), "父类语义仍要成立(调用方兼容)"
    assert "停止" in str(err.value)


def test_requests_counter():
    queue, fetcher = make_fetcher()
    auto = _Auto(queue)
    try:
        fetcher.get_text(URL)
        fetcher.get_bytes(DL)
        assert fetcher.requests == 2
    finally:
        auto.close()
