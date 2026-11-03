"""test_hr_runtime_apply 测试计划: 运行时门面(端点 + 取数线程 + 热重载重挂 + 启动引导)

用最小假 manager 驱动门面(它只读 `manager.config` 与可选的 `_hr_anchors`),
不构造真 QbManager —— 那要连 qB 且持单实例锁, 与本模块的职责无关。

## 测试计划(每个测试函数一条)
- test_apply_remounts_on_channel_change: 改端口 -> 重挂(新端口在听, 旧端口释放)
- test_apply_keeps_endpoint_on_l0_change: 只改 L0 字段(轮询节奏) -> 端点不重绑
- test_apply_stops_when_disabled: 关掉功能 -> 线程与端点都停
- test_apply_starts_worker_when_never_started: 站点接入热重载(启动时无站点) -> apply 必须把服务/线程/端点都带起来
  (旧版「未启动时 apply 不得拉起线程」是 2026-09-29「取数线程未启动」bug 的成因之一, 已随修复反转;
  端点「从无到有」同为该族缺陷 —— 只建对象不绑端口 ⇒ 扩展连不上端点)
- test_apply_rebinds_endpoint_after_all_sites_hot_disabled: 站点全关收掉端点后重新启用 -> 必须重新监听
- test_apply_no_change_short_circuits: HR 侧无变化 -> apply 短路, 服务/线程对象原样保留不重启
- test_apply_adds_site_while_running: 已运行时热接入新站点 -> 服务站点表长出新站点且线程仍在跑
- test_apply_remount_message_is_info: 热重载重挂端点也是预期动作, 同样只记 INFO

### P1 覆盖率提升轮: 运行时门面长尾

### hr 首轮变异审计轮: 运行时门面长尾(issue 26-10-10-1108-runtime-worker)
- test_apply_l0_rebuilds_without_remounting_endpoint: 换全新站点配置对象走 L0 重建 -> 不重绑端点 + 精确 INFO
- test_apply_close_message_precise_when_sites_disabled: 站点全关(仅线程)时关停也要说一声「已关闭」
- test_apply_remount_message_is_precise: 重挂端点的 INFO 钉首尾(松匹配会被 service 的「重挂端点」文案顶替)

### 端口隔离守卫(issue 26-10-16-0348)

### 覆盖率第三轮 T1b: apply 长尾分支
- test_apply_l0_rebuild_channel_off_keeps_readonly_shape: 无通道实例的 L0 热重载 —— 不建端点, 线程照常重建并启动
- test_apply_l0_rebuild_keeps_started_discovery_object: 有发现服务的实例走 L0 重建 —— 发现对象原样保留
"""

import logging

import socket

import threading

import time

import pytest

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
    make_config,
    make_runtime,
)


def test_apply_remount_message_is_info(tmp_path, caplog):
    """改端口导致重挂端点: 这是热重载的预期动作, 同样只记 INFO"""
    runtime = make_runtime(tmp_path, enabled=True, channel=True)
    runtime.start()
    try:
        old = runtime.global_conf
        runtime.config.hr_check = make_config(tmp_path, enabled=True, channel=True, port=_free_port()).hr_check
        with caplog.at_level(logging.INFO, logger="auto_qb.hr"):
            runtime.apply(old)
        noisy = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
        assert not noisy, f"热重载消息不得用 WARNING: {noisy}"
        assert any("重挂" in r.getMessage() for r in caplog.records), "重挂这事该说一声"
    finally:
        runtime.stop()


def test_apply_remounts_on_channel_change(tmp_path):
    runtime = make_runtime(tmp_path, enabled=True, channel=True)
    runtime.start()
    try:
        old_endpoint = runtime.endpoint
        want = _free_port()
        old = runtime.global_conf
        runtime.config.hr_check = make_config(tmp_path, enabled=True, channel=True, port=want).hr_check
        runtime.apply(old)
        assert runtime.endpoint is not old_endpoint, "监听身份变了必须重挂(先停旧再启新)"
        assert runtime.status().channel.port == want, "新端点要绑到新端口"
        assert runtime.worker is not None and runtime.worker.started
    finally:
        runtime.stop()


def test_apply_keeps_endpoint_on_l0_change(tmp_path):
    runtime = make_runtime(tmp_path, enabled=True, channel=True)
    runtime.start()
    try:
        same = runtime.endpoint
        old = runtime.global_conf
        runtime.config.hr_check = make_config(tmp_path, enabled=True, channel=True).hr_check
        runtime.config.trackers["pt.example.com"].hr_check.refresh_interval = 6 * 3600.0
        runtime.apply(old)
        assert runtime.endpoint is same, "只改 L0 字段不该白重绑端口"
        assert runtime.service.site_confs["pt.example.com"].refresh_interval == 6 * 3600.0, "服务要用新配置重建"
        assert runtime.worker is not None and runtime.worker.started
    finally:
        runtime.stop()


def test_apply_stops_when_disabled(tmp_path):
    runtime = make_runtime(tmp_path, enabled=True, channel=True)
    runtime.start()
    try:
        old = runtime.global_conf
        runtime.config.hr_check = make_config(tmp_path, enabled=False, channel=True).hr_check
        runtime.apply(old)
        assert runtime.worker is None and runtime.endpoint is None
    finally:
        runtime.stop()


def test_apply_starts_worker_when_never_started(tmp_path):
    """站点接入热重载(2026-09-29 实报「取数线程未启动」): 启动时无站点 => 线程从未建过;
    热接入第一个站点后 apply 必须把服务与线程带起来(enabled => 在跑)。
    !本用例旧版钉的是反语义(「未启动时 apply 不得拉起线程」), 正是本 bug 的成因之一 —— 已随修复反转。"""
    runtime = make_runtime(tmp_path, enabled=True, channel=True)
    old = runtime.global_conf
    runtime.config.hr_check = make_config(tmp_path, enabled=True, channel=True).hr_check
    runtime.config.trackers["pt.example.com"].hr_check.refresh_interval = 3 * 3600.0
    runtime.apply(old)
    assert runtime.service is not None, "站点接入后服务必须建出来(否则 /api/hr/status 报「取数线程未启动」)"
    assert runtime.service.site_confs["pt.example.com"].refresh_interval == 3 * 3600.0
    assert runtime.worker is not None and runtime.worker.started, "enabled 时 apply 必须把取数线程带起来"
    assert runtime.endpoint is not None and runtime.endpoint.started, \
        "端点「从无到有」也必须拉起: 只建对象不绑端口 ⇒ 扩展连不上端点(2026-09-29 实报)"
    try:
        assert runtime.status().worker_running is True
        assert runtime.status().channel is not None and runtime.status().channel.listening
    finally:
        runtime.stop()


def test_apply_rebinds_endpoint_after_all_sites_hot_disabled(tmp_path):
    """站点全关(总开关仍开) ⇒ 端点与线程被收掉; 再启用必须重新监听

    `enabled` 取决于「总开关 + 至少一个站点」, 而**监听身份**只看总开关/channel 那几个 ——
    站点全关时 identity 不变, apply 走的是 L0 重建路径, 端点靠「从无到有」分支补启动。
    缺了这一步: 端口从未绑定, 扩展连不上, 而取数线程照样派发任务白等满 request_timeout。
    """
    runtime = make_runtime(tmp_path, enabled=True, channel=True)
    runtime.start()
    try:
        assert runtime.endpoint is not None and runtime.endpoint.started
        old = runtime.global_conf
        runtime.config.trackers = make_config(tmp_path, enabled=True, channel=True, site_enabled=False).trackers
        runtime.apply(old)
        assert runtime.endpoint is None and runtime.worker is None, "站点全关 ⇒ 收掉端点与线程"
        old2 = runtime.global_conf
        runtime.config.trackers = make_config(tmp_path, enabled=True, channel=True).trackers
        runtime.apply(old2)
        assert runtime.endpoint is not None and runtime.endpoint.started, "重新启用必须重新监听"
        assert runtime.worker is not None and runtime.worker.started
    finally:
        runtime.stop()


def test_apply_no_change_short_circuits(tmp_path):
    """HR 侧配置无实质变化 => apply 短路: 服务与线程对象原样保留(不重启)。

    apply 现在每次热重载都会被调到(qbmanager 不再只挂 L1 分支), 无关配置的保存不能拿取数线程陪葬。
    """
    runtime = make_runtime(tmp_path, enabled=True, channel=True)
    runtime.start()
    try:
        old = runtime.global_conf
        worker_before, service_before, endpoint_before = runtime.worker, runtime.service, runtime.endpoint
        runtime.apply(old)  # old 与当前完全一致
        assert runtime.worker is worker_before, "无变化不得重建线程"
        assert runtime.service is service_before, "无变化不得重建服务"
        assert runtime.endpoint is endpoint_before
        assert runtime.worker.started
    finally:
        runtime.stop()


def test_apply_adds_site_while_running(tmp_path):
    """已运行时热接入第二个站点: 服务站点表要长出新站点(服务按值持站点表, 只换 config 对象不够)"""
    runtime = make_runtime(tmp_path, enabled=True, channel=True)
    runtime.start()
    try:
        old = runtime.global_conf
        runtime.config.trackers["pt2.example.com"] = TrackerConfig(
            name="pt2.example.com",
            domains=["pt2.example.com"],
            hr_check=SiteHrCheckConfig(
                enabled=True,
                tracker="pt2.example.com",
                hr_page_url="https://pt2.example.com/myhr.php",
            ),
        )
        runtime.apply(old)
        assert "pt2.example.com" in runtime.service.site_confs, "新站点必须进入服务的站点表"
        assert runtime.worker.started, "重建后线程仍在跑"
    finally:
        runtime.stop()


def test_apply_l0_rebuilds_without_remounting_endpoint(tmp_path, caplog):
    """换一份**全新**的站点配置对象(与 service 持有的不是同一批) -> 短路不成立, 真走 L0 重建路径"""
    runtime = make_runtime(tmp_path, enabled=True, channel=True)
    runtime.start()
    try:
        same = runtime.endpoint
        old = runtime.global_conf
        fresh = make_config(tmp_path, enabled=True, channel=True)
        fresh.trackers["pt.example.com"].hr_check.refresh_interval = 6 * 3600.0
        runtime.config.hr_check = fresh.hr_check
        runtime.config.trackers = fresh.trackers
        with caplog.at_level(logging.INFO, logger="auto_qb.hr"):
            runtime.apply(old)
        assert runtime.endpoint is same, "监听身份未变 -> 不重绑端口"
        assert runtime.service.site_confs["pt.example.com"].refresh_interval == 6 * 3600.0, "服务要用新配置重建"
        assert runtime.worker is not None and runtime.worker.started
        msgs = [r.getMessage() for r in caplog.records]
        assert "HR 在线核实配置已热应用(L0 字段; 端点监听身份未变, 未重绑)" in msgs, msgs
    finally:
        runtime.stop()


def test_apply_close_message_precise_when_sites_disabled(tmp_path, caplog):
    """站点全关(总开关仍开): 监听身份不变, 走关停分支 —— 只有线程(无端点)时也要说一声"""
    runtime = make_runtime(tmp_path, enabled=True, channel=False)
    runtime.start()
    try:
        assert runtime.worker is not None and runtime.endpoint is None
        old = runtime.global_conf
        runtime.config.trackers = make_config(tmp_path, enabled=True, channel=False, site_enabled=False).trackers
        with caplog.at_level(logging.INFO, logger="auto_qb.hr"):
            runtime.apply(old)
        msgs = [r.getMessage() for r in caplog.records]
        assert "HR 在线核实已关闭: 停止端点与取数线程" in msgs, msgs
    finally:
        runtime.stop()


def test_apply_remount_message_is_precise(tmp_path, caplog):
    """重挂端点的 INFO 要报出「旧身份 -> 新身份」与动作

    !松匹配会被顶替: service 的节流原因里也带「重挂端点」四个字(等待被叫停的文案),
    故必须钉首尾, 否则这条 INFO 被改成 None 也照样绿。
    """
    runtime = make_runtime(tmp_path, enabled=True, channel=True)
    runtime.start()
    try:
        old = runtime.global_conf
        runtime.config.hr_check = make_config(tmp_path, enabled=True, channel=True, port=_free_port()).hr_check
        with caplog.at_level(logging.INFO, logger="auto_qb.hr"):
            runtime.apply(old)
        msgs = [r.getMessage() for r in caplog.records]
        assert any(m.startswith("HR 取数通道监听身份变化 ") and m.endswith(": 重挂端点与取数线程") for m in msgs), msgs
    finally:
        runtime.stop()


def test_apply_l0_rebuild_channel_off_keeps_readonly_shape(tmp_path):
    """无通道实例(只读共享)的 L0 热重载: 不建端点, 服务与线程照常重建并启动(整份换配置对象防短路)"""
    runtime = make_runtime(tmp_path, enabled=True, channel=False)
    runtime.start()
    try:
        assert runtime.worker is not None and runtime.endpoint is None
        service_before = runtime.service
        old = runtime.global_conf
        fresh = make_config(tmp_path, enabled=True, channel=False)
        fresh.trackers["pt.example.com"].hr_check.refresh_interval = 6 * 3600.0
        runtime.config.hr_check = fresh.hr_check
        runtime.config.trackers = fresh.trackers
        runtime.apply(old)
        assert runtime.service is not service_before, "L0 变更必须真走重建路径(短路会让本用例放空)"
        assert runtime.service.site_confs["pt.example.com"].refresh_interval == 6 * 3600.0, "服务要用新配置重建"
        assert runtime.endpoint is None and runtime.discovery is None, "无通道: 端点与发现都不建"
        assert runtime.worker is not None and runtime.worker.started, "重建后线程收敛到「enabled ⇒ 在跑」"
    finally:
        runtime.stop()


def test_apply_l0_rebuild_keeps_started_discovery_object(tmp_path):
    """有发现服务的实例走 L0 重建: 发现对象原样保留不重建不重绑(监听身份未变)"""
    base = _free_port()
    runtime = make_runtime(tmp_path, enabled=True, channel=True, discovery_port=base)
    runtime.start()
    try:
        discovery_before = runtime.discovery
        endpoint_before = runtime.endpoint
        assert discovery_before is not None and discovery_before.started
        old = runtime.global_conf
        fresh = make_config(tmp_path, enabled=True, channel=True, discovery_port=base)
        fresh.trackers["pt.example.com"].hr_check.refresh_interval = 6 * 3600.0
        runtime.config.hr_check = fresh.hr_check
        runtime.config.trackers = fresh.trackers
        runtime.apply(old)
        assert runtime.service.site_confs["pt.example.com"].refresh_interval == 6 * 3600.0, \
            "L0 重建真发生(整份换配置对象防短路)"
        assert runtime.discovery is discovery_before, "监听身份未变 ⇒ 发现对象不重建"
        assert runtime.discovery.started, "发现服务保持监听"
        assert runtime.endpoint is endpoint_before
    finally:
        runtime.stop()
