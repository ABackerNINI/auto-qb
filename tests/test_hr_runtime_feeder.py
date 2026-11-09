"""test_hr_runtime_feeder 测试计划: 运行时门面(端点 + 取数线程 + 热重载重挂 + 启动引导)

用最小假 manager 驱动门面(它只读 `manager.config` 与可选的 `_hr_anchors`),
不构造真 QbManager —— 那要连 qB 且持单实例锁, 与本模块的职责无关。

## 测试计划(每个测试函数一条)
- test_view_snapshot_and_wake_are_safe_when_not_started: 未启动时读视图/唤醒都安全
- test_judge_is_none_when_disabled: 总开关关 -> judge 返回 None(消费方回落本地字段逻辑)
- test_judge_reads_published_view: 启用时按**当前已发布**视图现算(命中清单 -> 受管束 + 站点达标结论)
- test_judge_without_published_view_falls_back: 还没发布过视图(启动窗口) -> None, 不是"未核实"- test_sleeper_is_interruptible_by_stop: 锁内等待可中断 —— 关停/热重挂不必等它把间隔睡完
- test_sleeper_returns_after_the_wait: 没被打断时按秒数返回(不提前也不卡住)
- test_production_service_gets_a_sleeper: 生产服务必须带 sleeper(2026-09-25 实报: 不等待 ⇒ 下载被页面饿死)
- test_fetcher_fails_fast_when_endpoint_stops_listening: 端点不在监听 -> 取数立刻报无通道, 不白等 request_timeout
- test_runtime_uses_anchors_provider: 取数线程经主循环提供的锚点提供者取锚点(M3 的交接面)
- test_site_origins_served_live_for_extension: /api/hr/sites 按配置现派生授权清单, 热加站点即生效且 mode=off 不出现

### P1 覆盖率提升轮: 运行时门面长尾
- test_sleeper_raises_immediately_when_stop_already_set: 关停标记已置 -> 进等待前即抛 HrChannelStopped
- test_wake_is_safe_and_forwards_to_worker: wake 转发线程(未启动空转; 已启动断言真转发到 worker.wake)
- test_events_summaries_direct: events 连续失效文案与站点稳定排序直调

### hr 首轮变异审计轮: 运行时门面长尾(issue 26-10-10-1108-runtime-worker)
- test_init_defaults_fetcher_and_token: 门面初始 fetcher 是空通道(带可读 reason)、token 为空串
- test_web_active_reads_manager_web_live: WebUI 活跃现读回调(无 web 面/异常都保守 False)
- test_judge_forwards_anchor_and_now: judge 把 anchor/now 原样转交 judge_record(缺省 now=0.0)
- test_sleeper_zero_seconds_returns_immediately: sleeper(0.0) 立刻返回(不得被抬成最短 1s)
- test_sleeper_stop_message_is_precise: 中断抛的 HrChannelStopped 文案带「停止」
- test_anchors_collects_enabled_sites_only: 锚点表只收启用站点的非空 hash, 逐条跳过(不是遇阻即停)
- test_request_refresh_accepts_only_named_sites: 指定站点只受理该站(不是全量)
- test_request_refresh_note_is_precise: 受理回执 note 精确
- test_site_origins_skips_without_stopping: 授权清单逐条跳过 disabled / 无 host 的站点(不是遇阻即停)

### 端口隔离守卫(issue 26-10-16-0348)
- test_judge_site_view_lane_a_managed
- test_request_refresh_delegates_to_worker_and_accepts
- test_request_refresh_without_worker_reports_note
- test_request_refresh_notes_when_no_fetchable_sites: 线程在跑但无可取数站点 => 「没有可取数站点」
- test_request_refresh_notes_when_named_site_not_fetchable: 点名不在可取数集合 => 如实文案
- test_sleeper_interrupt_during_wait_message_is_precise
  不绑共享固定端口 18788-18795 —— 防「并行占满 ⇒ 发现 WARNING 污染 INFO 断言」复发
"""

import logging

import socket

import threading

import time

import pytest

from clock import wait_until  # noqa: E402  (单一实现单点, 计划 26-11-05-0118 S3: 调用点一律直连 clock 模块)

from auto_qb.config.models import Config, HrChannelConfig, HrCheckConfig, SiteHrCheckConfig, TrackerConfig

from auto_qb.hr.channel import HrChannelBindError

from auto_qb.hr.fetcher import HrChannelStopped, HrChannelUnavailable, NullFetcher

from auto_qb.hr.model import HrEntry

from auto_qb.hr.resolve import HrAnchor, HrIdentity, HrSiteView, HrViewSet

from auto_qb.hr.runtime import HrRuntime

from auto_qb.hr.service import POLL_INTERVAL

import auto_qb.hr.runtime as rt_module

from _test_ports import free_port as _free_port  # noqa: E402  端口单点(防散落守卫: tests/test_free_port.py); 取当前空闲端口

from hr_runtime_support import (
    _FakeManager,
    _FakeStore,
    _two_site_config,
    make_config,
    make_runtime,
)

H1 = "aa" * 20


class _WaitProbe(threading.Event):
    """wait() 入口探针: 线程一进可中断等待就置 entered —— 替代「睡一拍赌它进去了」的固定睡等

    sleeper 的可中断语义钉在 `_sleep_stop.wait()` 这一位上: 探针子类只记入口不改行为,
    set()/clear()/is_set() 全部走 Event 原实现(stop() 直接可用)。用例等 entered 命中后再
    打断, 打断必然落在等待**内**(sleeper 已越过循环顶的 is_set 检查), 不再依赖真睡步长。
    """
    def __init__(self) -> None:
        super().__init__()
        self.entered = threading.Event()

    def wait(self, timeout=None):
        self.entered.set()
        return super().wait(timeout)


def test_view_snapshot_and_wake_are_safe_when_not_started(tmp_path):
    runtime = make_runtime(tmp_path, enabled=True, channel=True)
    assert runtime.revision == 0
    rev, views = runtime.view_snapshot()
    assert rev == 0 and views.views == {}
    runtime.wake()  # 未启动: 不得抛异常
    runtime.stop()  # 幂等


def test_judge_is_none_when_disabled(tmp_path):
    """总开关关 -> judge 返回 None = 消费方回落既有本地判断(零静默变更的另一个方向)"""
    runtime = make_runtime(tmp_path, enabled=False, channel=False)
    runtime.publisher.publish(HrViewSet(views={"pt.example.com": HrSiteView(site="pt.example.com", listing="list")}))
    assert runtime.judge("pt.example.com", (H1, ), now=1.0) is None


def test_judge_reads_published_view(tmp_path):
    """启用时按**当前已发布**视图现算: 命中清单 -> 受管束, 并把站点侧达标结论一并带出"""
    runtime = make_runtime(tmp_path, enabled=True, channel=False)
    view = HrSiteView(
        site="pt.example.com",
        listing="list",
        lane_terminal={H1: HrEntry(tid=7, infohash_v1=H1, lane="B")},
    )
    runtime.publisher.publish(HrViewSet(views={"pt.example.com": view}))
    got = runtime.judge("pt.example.com", (H1, ""), anchor=HrAnchor(added_on=1, downloaded=0), now=1.0)
    assert got is not None and got.is_hr is False
    assert got.identity is HrIdentity.RELEASED and got.site_satisfied is True


def test_judge_without_published_view_falls_back(tmp_path):
    """启用了但还没发布过视图(启动窗口) -> None: 站点侧没数据就回落本地

    若把"没数据"当"未核实", mode=all 站点会在启动窗口里让整站种子集体触发打标(千级标签风暴)。
    """
    runtime = make_runtime(tmp_path, enabled=True, channel=False, site_enabled=False)
    assert runtime.judge("pt.example.com", (H1, ), now=1.0) is None


def test_sleeper_is_interruptible_by_stop(tmp_path):
    """锁内等待必须可中断: 关停(含热重挂)不能等它把这次间隔睡完 —— 那期间还持着站点锁

    生产路径现在会在锁内等满频控间隔(最多几分钟), 所以这条必须成立, 否则一次关停要等好几分钟,
    共享目录下其它实例也一直被挡在锁外。
    """
    runtime = make_runtime(tmp_path, enabled=True, channel=False)
    probe = _WaitProbe()
    runtime._sleep_stop = probe  # 打断点必须落在等待内: 探针在 wait() 入口置 entered
    errs: list = []

    def run():
        try:
            runtime.sleeper(30.0)
        except HrChannelStopped as e:
            errs.append(e)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    assert probe.entered.wait(5.0), "用例前提: 线程已睡进可中断等待"
    started = time.monotonic()
    runtime.stop()
    thread.join(5.0)

    assert errs and "停止" in str(errs[0]), "被打断要抛 HrChannelStopped(service 据此记「本轮让位」)"
    assert time.monotonic() - started < 2.0, "关停是秒级的事, 不能等它睡完"


def test_sleeper_returns_after_the_wait(tmp_path):
    """没被打断时按秒数返回(不提前也不卡住)"""
    runtime = make_runtime(tmp_path, enabled=True, channel=False)
    started = time.monotonic()
    runtime.sleeper(0.2)
    elapsed = time.monotonic() - started
    assert 0.15 <= elapsed < 2.0, elapsed


def test_production_service_gets_a_sleeper(tmp_path):
    """生产服务必须拿到 sleeper —— 2026-09-25 实报: 不等待 ⇒ 一次刷新只发出第一个请求, 下载被饿死"""
    runtime = make_runtime(tmp_path, enabled=True, channel=False)
    runtime.start()
    try:
        assert runtime.service is not None
        assert runtime.service._sleeper is not None
        assert runtime.service._sleeper == runtime.sleeper, "接的必须是门面那个可中断的等待"
    finally:
        runtime.stop()


def test_runtime_uses_anchors_provider(tmp_path):
    """取数线程经门面 _anchors 提供者拿本地锚点(M3 的交接面; plan §05 后实现自持在门面)"""
    calls = []

    config = make_config(tmp_path, enabled=True, channel=False)
    runtime = HrRuntime(_FakeManager(config))
    real = runtime._anchors

    def counting():
        calls.append(1)
        return real()

    runtime._anchors = counting  # 实例属性遮蔽: HrWorker 构造时绑定的就是这个包装
    runtime.start()
    try:
        assert wait_until(lambda: calls, timeout=3.0), "取数线程应经门面 _anchors 拿本地锚点(M3 的交接面)"
    finally:
        runtime.stop()


def test_fetcher_fails_fast_when_endpoint_stops_listening(tmp_path):
    """门面把「端点是否在监听」接进了取数通道: 端点被收掉后取数立刻报无通道, 不白等超时

    2026-09-29 实报的另一半: 端点没绑端口时取数线程照样派发任务, 每页白等满 request_timeout
    (一个站点一轮白占 3 分钟锁, 日志只留下会把人引向浏览器的「等扩展超时」)。
    """
    runtime = make_runtime(tmp_path, enabled=True, channel=True, request_timeout=5.0)
    runtime.start()
    try:
        assert runtime.endpoint is not None and runtime.endpoint.started
        runtime.endpoint.stop()  # 端口不再绑定(热重载整站关停 / 端点异常收掉)
        started = time.monotonic()
        with pytest.raises(HrChannelUnavailable):
            runtime.fetcher.get_text("https://pt.example.com/myhr.php?hrtype=A")
        assert time.monotonic() - started < 2.0, "端点没在监听就不该白等满 request_timeout"
    finally:
        runtime.stop()


def test_judge_site_view_lane_a_managed(tmp_path):
    """判定收口: 命中考察中 -> 管束(判定语义硬编码, 无豁免配置参数)"""
    runtime = make_runtime(tmp_path, enabled=True, channel=False)
    view = HrSiteView(site="pt.example.com", listing="list", lane_a={H1: HrEntry(tid=7, infohash_v1=H1, lane="A")})
    runtime.publisher.publish(HrViewSet(views={"pt.example.com": view}))
    got = runtime.judge("pt.example.com", (H1, ""), anchor=HrAnchor(added_on=1, downloaded=0), now=1.0)
    assert got is not None and got.identity is HrIdentity.HR and got.is_hr is True


def test_site_origins_served_live_for_extension(tmp_path):
    """扩展的「勾选站点」数据源: /api/hr/sites 按配置现派生站点授权清单, 热加站点不用重绑端点"""
    from auto_qb.hr.channel import TOKEN_HEADER
    runtime = make_runtime(tmp_path, enabled=True, channel=True, port=0)
    runtime.start()
    try:
        assert runtime._site_origins() == [("pt.example.com", "https://pt.example.com/*")]
        # 热重载加站点不改端点监听身份(不重绑) => 清单必须每次现读, 否则新站点漏在授权清单外
        runtime.config.trackers["pt2.example.com"] = TrackerConfig(
            name="pt2.example.com",
            domains=["pt2.example.com"],
            hr_check=SiteHrCheckConfig(
                enabled=True, tracker="pt2.example.com", hr_page_url="http://pt2.example.com/myhr.php"
            ),
        )
        got = dict(runtime._site_origins())
        assert got == {
            "pt.example.com": "https://pt.example.com/*",
            "pt2.example.com": "http://pt2.example.com/*",
        }
        # 走端点路由同样拿到(鉴权/白名单由 server 层自己钉, 这里只验数据接上了)
        status, _headers, body = runtime.endpoint.route("GET", "/api/hr/sites", {TOKEN_HEADER: runtime.token})
        import json as _json
        assert status == 200
        payload = _json.loads(body)
        assert payload["error"] == ""
        assert {s["site"] for s in payload["sites"]} == {"pt.example.com", "pt2.example.com"}
        # disabled 的站点不该出现在授权清单里(扩展取不到它, 也不需要它的权限)
        runtime.config.trackers["pt2.example.com"].hr_check.enabled = False
        assert [s for s, _o in runtime._site_origins()] == ["pt.example.com"]
    finally:
        runtime.stop()


def test_request_refresh_without_worker_reports_note(tmp_path):
    """取数线程未启动时: 不顺手拉起线程, 如实返回提示(启动语义归 start/apply 管)"""
    runtime = make_runtime(tmp_path, enabled=True, channel=False)
    outcome = runtime.request_refresh()
    assert outcome == {"requested": [], "note": "取数线程未启动"}


def test_request_refresh_delegates_to_worker_and_accepts(tmp_path):
    """线程在跑: 受理全部启用站点(返回清单), 由取数线程串行消费"""
    runtime = make_runtime(tmp_path, enabled=True, channel=False)
    runtime.start()
    try:
        outcome = runtime.request_refresh()
        assert outcome["requested"] == ["pt.example.com"] and "已受理" in outcome["note"]
    finally:
        runtime.stop()


def test_sleeper_raises_immediately_when_stop_already_set(tmp_path):
    """关停标记已置位时进入 sleeper -> 立刻抛 HrChannelStopped(不进入等待循环)"""
    runtime = make_runtime(tmp_path, enabled=True, channel=False)
    runtime._sleep_stop.set()
    with pytest.raises(HrChannelStopped):
        runtime.sleeper(30.0)


def test_wake_is_safe_and_forwards_to_worker(tmp_path, monkeypatch):
    """wake 转发给取数线程(未启动时也安全不抛; 已启动必须真转发到 worker.wake())"""
    runtime = make_runtime(tmp_path, enabled=True, channel=False)
    runtime.wake()  # 未启动: worker 为 None, 空转
    runtime.start()
    try:
        forwarded = []
        monkeypatch.setattr(runtime.worker, "wake", lambda: forwarded.append(True))
        runtime.wake()  # 已启动: 必须转发 worker.wake()
        assert forwarded == [True]  # 弱断言修复(issue 26-11-03-1209): 只验证不抛 = 转发丢了也绿
    finally:
        runtime.stop()


def test_events_summaries_direct():
    """events 文案单点直调: 连续失效升级文案 / 站点清单稳定排序"""
    from auto_qb.hr import events

    text = events.lane_persistent_failure("example", "A", 3, "表头缺失")
    assert "已连续 3 波失效" in text and "example" in text
    assert events.summarize_sites(["beta", "alpha"]) == "alpha, beta"


def test_init_defaults_fetcher_and_token(tmp_path):
    runtime = make_runtime(tmp_path, enabled=False)
    assert isinstance(runtime.fetcher, NullFetcher)
    assert runtime.token == ""
    with pytest.raises(HrChannelUnavailable) as err:
        runtime.fetcher.get_text("https://pt.example.com/myhr.php")
    assert str(err.value).startswith("HR 在线核实未启动")


def test_web_active_reads_manager_web_live(tmp_path):
    """WebUI 是否活跃: 现读 manager.web; 无 web 面 / 抛异常都保守返回 False(少提醒)"""
    runtime = make_runtime(tmp_path, enabled=False)
    assert runtime._web_active() is False

    class _Web:
        def __init__(self, active):
            self._active = active

        def is_active(self):
            return self._active

    runtime._manager.web = _Web(True)
    assert runtime._web_active() is True
    runtime._manager.web = _Web(False)
    assert runtime._web_active() is False

    class _Boom:
        def is_active(self):
            raise RuntimeError("web 面炸了")

    runtime._manager.web = _Boom()
    assert runtime._web_active() is False


def test_judge_forwards_anchor_and_now(tmp_path, monkeypatch):
    """judge 必须把 anchor / now **原样**转交 judge_record(缺省 now=0.0), 不吞不改"""
    captured = {}

    def fake_judge(view, infohashes, *, anchor=None, now=0.0):
        captured["view"] = view
        captured["infohashes"] = infohashes
        captured["anchor"] = anchor
        captured["now"] = now
        return None

    monkeypatch.setattr(rt_module, "judge_record", fake_judge)
    runtime = make_runtime(tmp_path, enabled=True, channel=False)
    runtime.judge("pt.example.com", ("h1", ), anchor=HrAnchor(added_on=5), now=7.0)
    assert captured["anchor"] == HrAnchor(added_on=5)
    assert captured["now"] == 7.0
    runtime.judge("pt.example.com", ("h1", ))
    assert captured["now"] == 0.0, "now 缺省是 0.0"


def test_sleeper_zero_seconds_returns_immediately(tmp_path):
    """sleeper(0.0) 立刻返回 —— 下界是 max(0.0, ...), 不得被抬成最短 1s"""
    runtime = make_runtime(tmp_path, enabled=True, channel=False)
    started = time.monotonic()
    runtime.sleeper(0.0)
    assert time.monotonic() - started < 0.5


def test_sleeper_stop_message_is_precise(tmp_path):
    runtime = make_runtime(tmp_path, enabled=True, channel=False)
    runtime._sleep_stop.set()
    with pytest.raises(HrChannelStopped) as err:
        runtime.sleeper(30.0)
    assert str(err.value) == "取数通道已停止(正在关停或重挂): 放弃本轮剩余的等待", str(err.value)


def test_sleeper_interrupt_during_wait_message_is_precise(tmp_path):
    """等待循环**内**被打断(第二处 raise)的文案同样要精确 —— 两处 raise 各是一条独立变异"""
    runtime = make_runtime(tmp_path, enabled=True, channel=False)
    probe = _WaitProbe()
    runtime._sleep_stop = probe  # 打断点必须落在等待内: 探针在 wait() 入口置 entered
    errs: list = []

    def run():
        try:
            runtime.sleeper(30.0)
        except HrChannelStopped as e:
            errs.append(e)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    assert probe.entered.wait(5.0), "用例前提: 线程已睡进可中断等待"
    runtime._sleep_stop.set()
    thread.join(5.0)
    assert errs, "等待中被打断必须抛 HrChannelStopped"
    assert str(errs[0]) == "取数通道已停止(正在关停或重挂): 放弃本轮剩余的等待", str(errs[0])


class _TC:
    def __init__(self, name, hr_check):
        self.name = name
        self.hr_check = hr_check


class _Rec:
    def __init__(self, conf, h1="", h2=""):
        self.tracker_conf = conf
        self.infohash_v1 = h1
        self.infohash_v2 = h2

    def hr_anchor(self):
        return HrAnchor(added_on=7, downloaded=9)


class _Store:
    def __init__(self, recs):
        self._recs = recs

    def all(self):
        return list(self._recs)


def test_anchors_collects_enabled_sites_only(tmp_path):
    """锚点表: 逐条跳过(无 tracker_conf / 无 hr_check / 未启用), 只收启用站点的非空 hash"""
    enabled = SiteHrCheckConfig(enabled=True, tracker="pt.example.com", hr_page_url="https://pt.example.com/myhr.php")
    disabled = SiteHrCheckConfig(
        enabled=False, tracker="pt2.example.com", hr_page_url="https://pt2.example.com/myhr.php"
    )
    recs = [
        _Rec(None, h1="zz"),  # 无 tracker_conf -> 跳过(且不得中断后面的条目)
        _Rec(_TC("pt3.example.com", None), h1="yy"),  # 无 hr_check -> 跳过
        _Rec(_TC("pt2.example.com", disabled), h1="xx"),  # 站点未启用 -> 跳过
        _Rec(_TC("pt.example.com", enabled), h1="aa", h2="bb"),
        _Rec(_TC("pt.example.com", enabled), h1=""),  # 空 hash -> 不入表
    ]
    runtime = HrRuntime(_FakeManager(make_config(tmp_path), store=_Store(recs)))
    got = runtime._anchors()
    assert set(got) == {"pt.example.com"}
    assert set(got["pt.example.com"]) == {"aa", "bb"}
    assert got["pt.example.com"]["aa"] == HrAnchor(added_on=7, downloaded=9)


def test_request_refresh_accepts_only_named_sites(tmp_path):
    """指定站点 -> 只受理该站(不得回落成全量)"""
    runtime = HrRuntime(_FakeManager(_two_site_config(tmp_path, enabled=True, channel=False)))
    runtime.start()
    try:
        assert runtime.request_refresh(["pt2.example.com"])["requested"] == ["pt2.example.com"]
    finally:
        runtime.stop()


def test_request_refresh_note_is_precise(tmp_path):
    runtime = make_runtime(tmp_path, enabled=True, channel=False)
    runtime.start()
    try:
        outcome = runtime.request_refresh()
        assert outcome["note"] == "已受理, 取数由取数线程执行"
    finally:
        runtime.stop()


def test_site_origins_skips_without_stopping(tmp_path):
    """授权清单逐条跳过(disabled / 无 host), 不得遇阻即停(否则后面的站点全漏)"""
    runtime = make_runtime(tmp_path, enabled=True, channel=False)
    runtime.config.trackers = {
        "off.example.com":
            TrackerConfig(
                name="off.example.com",
                domains=["off.example.com"],
                hr_check=SiteHrCheckConfig(
                    enabled=False, tracker="off.example.com", hr_page_url="https://off.example.com/myhr.php"
                ),
            ),
        "nohost.example.com":
            TrackerConfig(
                name="nohost.example.com",
                domains=["nohost.example.com"],
                hr_check=SiteHrCheckConfig(enabled=True, tracker="nohost.example.com", hr_page_url=""),
            ),
        "pt.example.com":
            TrackerConfig(
                name="pt.example.com",
                domains=["pt.example.com"],
                hr_check=SiteHrCheckConfig(
                    enabled=True, tracker="pt.example.com", hr_page_url="https://pt.example.com/myhr.php"
                ),
            ),
    }
    assert runtime._site_origins() == [("pt.example.com", "https://pt.example.com/*")]


# ---------------------------------------------------------------------------
# 覆盖率缺口清偿(26-11-07): 点名取数两支拒绝文案(全站型空集 / 点名不在集合)
# ---------------------------------------------------------------------------


def test_request_refresh_notes_when_no_fetchable_sites(tmp_path):
    """线程在跑但无可取数站点(全站型/未绑定)且未点名 => 「没有可取数站点」文案"""
    runtime = make_runtime(tmp_path, enabled=True, channel=False)
    runtime.config.trackers["pt.example.com"].hr_check.listing = ""  # 空 = 未绑定, fetchable 不收
    runtime.start()
    try:
        outcome = runtime.request_refresh()
        assert outcome["requested"] == [] and "没有可取数站点" in outcome["note"], outcome
    finally:
        runtime.stop()


def test_request_refresh_notes_when_named_site_not_fetchable(tmp_path):
    """点名站点不在可取数集合 => 「点名站点不在可取数集合」文案(不虚报已受理)"""
    runtime = make_runtime(tmp_path, enabled=True, channel=False)
    runtime.start()
    try:
        outcome = runtime.request_refresh(["nosuch.example.com"])
        assert outcome["requested"] == [] and "不在可取数集合" in outcome["note"], outcome
    finally:
        runtime.stop()
