"""test_hr_runtime_lifecycle 测试计划: 运行时门面(端点 + 取数线程 + 热重载重挂 + 启动引导)

用最小假 manager 驱动门面(它只读 `manager.config` 与可选的 `_hr_anchors`),
不构造真 QbManager —— 那要连 qB 且持单实例锁, 与本模块的职责无关。

## 测试计划(每个测试函数一条)
- test_disabled_builds_nothing: 总开关关 -> 不建服务/线程/端点, start() 返回 False
- test_readonly_instance_without_channel: 无 channel 的实例仍跑取数线程, 但只读不抓(能力即角色)
- test_starts_endpoint_and_worker: 有 channel -> 端点真的在监听 + 线程在跑
- test_token_persisted_and_reused: 密钥落 <data_dir>/hr.token, 重启复用同一值
- test_port_conflict_is_fail_fast: 同端口第二个实例启动即报错(不静默降级)
- test_stop_releases_endpoint: stop() 后端口释放, 能再启动
- test_shared_dir_guidance_logged: shared_dir 留空 -> 一条 INFO 引导(不阻断启动)
- test_shared_dir_used_for_site_files: 配了 shared_dir -> 站点文件落在该目录
- test_status_reports_paths_and_channel: 自检快照字段齐全(路径/写者/端点/密钥来源)
- test_stop_is_prompt_while_waiting_for_extension: 取数线程正等扩展回传时 stop 也要立刻返回(不等满 request_timeout)
- test_restart_after_stop_works: 关停再启动能重新正常工作(叫停标记不得残留)
- test_start_stop_messages_are_info_not_warning: 启动/关闭类消息一律 INFO(它们会被 notify 推成系统通知)

### P1 覆盖率提升轮: 运行时门面长尾

### hr 首轮变异审计轮: 运行时门面长尾(issue 26-10-10-1108-runtime-worker)
- test_start_disabled_logs_debug_message: 未启用时一条 DEBUG 说明为何不启动(精确文案)
- test_startup_message_reports_mode_sites_and_dir: 启动 INFO 报出模式/站点(多站按 ", " 拼接)/目录
- test_startup_message_readonly_mode: 无通道实例的启动文案是「只读共享」(不是「端点 + 取数」)
- test_extension_id_warning_message_is_precise: 纵深提示 WARNING 全文(前缀 + 四段引导)
- test_build_wires_service_endpoint_and_worker: _build 的实参接线(service 目录/owner/persist, 端点 extension_id/force_fn, worker endpoint/poll/回调)
- test_build_clears_endpoint_and_token_when_no_channel: 切到无通道配置重启 -> 端点与 token 都清掉
- test_identity_tracks_enabled_and_channel_flags: 监听身份包含 enabled 与 channel.enabled 两位
- test_status_snapshot_fields_with_channel: 有端点时自检快照各字段(enabled/listening/port/token 来源/poll/revision/note)
- test_status_reports_endpoint_not_started: fetch_enabled 但端点未起 -> 合成快照(listening False / note「端点未启动」)
- test_status_snapshot_without_channel: 无端点且未启用通道 -> channel 为 None 且 note 提示只读
- test_shared_dir_guidance_message_is_precise: shared_dir 留空引导 INFO 全文

### 端口隔离守卫(issue 26-10-16-0348)
- test_channel_runtime_leaves_discovery_unbound: 本文件 channel 用例默认关发现(discovery_port=0),
- test_extension_id_empty_warns
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
    _two_site_config,
    make_config,
    make_runtime,
)


def test_disabled_builds_nothing(tmp_path):
    runtime = make_runtime(tmp_path, enabled=False, channel=True)
    assert runtime.enabled is False
    assert runtime.fetch_enabled is False
    assert runtime.start() is False
    assert runtime.service is None and runtime.worker is None and runtime.endpoint is None
    assert runtime.view_set().views == {}


def test_readonly_instance_without_channel(tmp_path):
    runtime = make_runtime(tmp_path, enabled=True, channel=False)
    assert runtime.start() is True
    try:
        assert runtime.service is not None and runtime.service.allow_fetch is False, "无端点实例只读共享数据"
        assert runtime.endpoint is None, "没装扩展就不该占端口"
        assert runtime.worker is not None and runtime.worker.started
        assert runtime.fetcher_available is False
        st = runtime.status()
        assert st.enabled and st.fetch_enabled is False and st.worker_running
        assert st.sites == ("pt.example.com", )
        assert "只读" in st.note
    finally:
        runtime.stop()


def test_starts_endpoint_and_worker(tmp_path):
    runtime = make_runtime(tmp_path, enabled=True, channel=True)
    assert runtime.start() is True
    try:
        assert runtime.endpoint is not None and runtime.endpoint.started
        assert runtime.service.allow_fetch is True
        assert runtime.fetcher_available is True
        status = runtime.status()
        assert status.channel is not None and status.channel.listening
        assert status.channel.port > 0
        assert status.token_source == "file"
    finally:
        runtime.stop()


def test_token_persisted_and_reused(tmp_path):
    first = make_runtime(tmp_path, enabled=True, channel=True)
    first.start()
    token = first.token
    first.stop()
    assert (tmp_path / "hr.token").read_text(encoding="ascii").strip() == token
    second = make_runtime(tmp_path, enabled=True, channel=True)
    second.start()
    try:
        assert second.token == token, "重启复用同一密钥(否则扩展侧要反复改配置)"
    finally:
        second.stop()


def test_port_conflict_is_fail_fast(tmp_path):
    first = make_runtime(tmp_path, enabled=True, channel=True)
    first.start()
    try:
        busy = first.status().channel.port
        other_dir = tmp_path / "second"
        other_dir.mkdir()
        second = make_runtime(other_dir, enabled=True, channel=True, port=busy)
        with pytest.raises(HrChannelBindError):
            second.start()
    finally:
        first.stop()


def test_start_stop_messages_are_info_not_warning(tmp_path, caplog):
    """启动 / 关闭 / 热重挂都是程序自己决定要发生的事 ⇒ INFO

    本仓 WARNING 以上会被 notify 推成**系统通知** —— 用 WARNING 的后果是每次重启都吃几条通知,
    用户看到的就是「一开就弹 warning」(2026-09-24 实报)。
    """
    runtime = make_runtime(tmp_path, enabled=True, channel=True)
    with caplog.at_level(logging.INFO, logger="auto_qb.hr"):
        runtime.start()
        runtime.stop()

    noisy = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
    assert not noisy, f"生命周期消息不得用 WARNING: {noisy}"  # extension_id 已填 ⇒ 也不触发纵深提示
    assert any("已启动" in r.getMessage() and r.levelno == logging.INFO for r in caplog.records)
    assert any("端点已启动" in r.getMessage() and r.levelno == logging.INFO for r in caplog.records)


def test_stop_releases_endpoint(tmp_path):
    runtime = make_runtime(tmp_path, enabled=True, channel=True)
    runtime.start()
    port = runtime.status().channel.port
    runtime.stop()
    assert runtime.endpoint is None and runtime.worker is None
    again = HrRuntime(_FakeManager(make_config(tmp_path, enabled=True, channel=True, port=port)))
    again.start()
    try:
        assert again.status().channel.listening
    finally:
        again.stop()


def test_extension_id_empty_warns(tmp_path, caplog):
    """端点纵深提示(计划 26-09-27-1815 §2 5.2, P3): extension_id 留空 ⇒ 启动 WARNING(不阻断启动)

    有意用 WARNING(会推系统通知): 这是**需要用户行动**的安全提示, 配好即不再出现 ——
    与「生命周期动作只记 INFO」的口径不冲突(它不是程序自己决定要发生的事)。
    """
    runtime = make_runtime(tmp_path, enabled=True, channel=True, extension_id="")
    with caplog.at_level(logging.WARNING, logger="auto_qb.hr.runtime"):
        runtime.start()
    try:
        warns = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
        assert any("extension_id 未配置" in w for w in warns), warns
    finally:
        runtime.stop()

    caplog.clear()  # 清掉第一段的记录, 隔离验证「配了就不再提示」
    filled = make_runtime(tmp_path, enabled=True, channel=True)
    with caplog.at_level(logging.WARNING, logger="auto_qb.hr.runtime"):
        filled.start()
    try:
        warns = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
        assert not any("extension_id" in w for w in warns), "配了 extension_id 就不再提示"
    finally:
        filled.stop()


def test_shared_dir_guidance_logged(tmp_path, caplog):
    runtime = make_runtime(tmp_path, enabled=True, channel=False)
    with caplog.at_level(logging.INFO, logger="auto_qb.hr.runtime"):
        runtime.start()
    try:
        assert any("shared_dir" in r.getMessage() for r in caplog.records), "留空要给一条引导(不阻断启动)"
    finally:
        runtime.stop()


def test_shared_dir_used_for_site_files(tmp_path, caplog):
    shared = tmp_path / "shared"
    shared.mkdir()
    runtime = make_runtime(tmp_path, enabled=True, channel=False, shared_dir=str(shared))
    with caplog.at_level(logging.INFO, logger="auto_qb.hr.runtime"):
        runtime.start()
    try:
        assert runtime.status().shared_dir is True
        assert runtime.status().sites_dir == str(shared / "hr")
        assert not [r for r in caplog.records if "未配置" in r.getMessage()], "配了就不再吶叨"
    finally:
        runtime.stop()


def test_status_reports_paths_and_channel(tmp_path):
    runtime = make_runtime(tmp_path, enabled=True, channel=True)
    st = runtime.status()
    assert st.data_dir == str(tmp_path)
    assert st.sites_dir == str(tmp_path / "hr")
    assert st.writer, "要能看出是谁在写(多实例排障的唯一线索)"
    assert st.token_path.endswith("hr.token")
    assert st.view_revision == 0


def test_stop_is_prompt_while_waiting_for_extension(tmp_path):
    """取数线程正卡在「等扩展回传」时, stop 也要立刻返回 —— 否则关停白等 request_timeout 且持着站点锁

    场景真实: 浏览器被关掉/扩展被停用, 线程正阻塞在 queue.wait(180s)。若关停不叫停它,
    QbManager.run 的 finally 会跟着多等几分钟, 该站点的锁也一直不放。
    """
    config = make_config(tmp_path, enabled=True, channel=True, request_timeout=120.0)
    runtime = HrRuntime(_FakeManager(config))
    runtime.start()
    try:
        deadline = time.monotonic() + 3.0
        while runtime.queue.pending() == 0 and time.monotonic() < deadline:
            time.sleep(0.02)
        assert runtime.queue.pending() > 0, "线程应已下发任务并在等回传"
        started = time.monotonic()
        runtime.stop()
        elapsed = time.monotonic() - started
        assert elapsed < 3.0, f"关停不该等满 request_timeout(实测 {elapsed:.1f}s)"
    finally:
        runtime.stop()


def test_restart_after_stop_works(tmp_path):
    """关停再启动要能重新正常工作: 叫停标记不得残留(否则新一轮一上来就「通道已停止」)"""
    runtime = make_runtime(tmp_path, enabled=True, channel=True)
    runtime.start()
    first_token = runtime.token
    runtime.stop()
    assert runtime.queue is not None and runtime.queue.cancel_reason, "关停会留下叫停标记"
    runtime.start()
    try:
        assert runtime.queue.cancel_reason == "", "重启要清掉它"
        assert runtime.token == first_token
        assert runtime.worker is not None and runtime.worker.started
        assert runtime.status().channel.listening
    finally:
        runtime.stop()


def test_start_disabled_logs_debug_message(tmp_path, caplog):
    runtime = make_runtime(tmp_path, enabled=False)
    with caplog.at_level(logging.DEBUG, logger="auto_qb.hr"):
        assert runtime.start() is False
    msgs = [r.getMessage() for r in caplog.records]
    assert "HR 在线核实未启用(总开关关或没有站点 enabled), 不启动取数线程" in msgs, msgs


def test_startup_message_reports_mode_sites_and_dir(tmp_path, caplog):
    runtime = HrRuntime(_FakeManager(_two_site_config(tmp_path, enabled=True, channel=True)))
    with caplog.at_level(logging.INFO, logger="auto_qb.hr"):
        runtime.start()
    try:
        msgs = [r.getMessage() for r in caplog.records]
        assert any(m.startswith("HR 在线核实已启动(端点 + 取数): 站点 pt.example.com, pt2.example.com; 站点文件目录 ") for m in msgs), msgs
    finally:
        runtime.stop()


def test_startup_message_readonly_mode(tmp_path, caplog):
    runtime = make_runtime(tmp_path, enabled=True, channel=False)
    with caplog.at_level(logging.INFO, logger="auto_qb.hr"):
        runtime.start()
    try:
        msgs = [r.getMessage() for r in caplog.records]
        assert any(m.startswith("HR 在线核实已启动(只读共享(本实例无取数通道)): 站点 pt.example.com; ") for m in msgs), msgs
    finally:
        runtime.stop()


def test_extension_id_warning_message_is_precise(tmp_path, caplog):
    runtime = make_runtime(tmp_path, enabled=True, channel=True, extension_id="")
    with caplog.at_level(logging.WARNING, logger="auto_qb.hr"):
        runtime.start()
    try:
        warns = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
        assert len(warns) == 1, warns
        assert warns[0].startswith("HR 取数端点的 extension_id 未配置: 任意扩展 origin 都能携带正确 token 调用本实例端点")
        assert warns[0].endswith(
            "(token 是第一道鉴权, 本项是第二道)。建议在浏览器扩展管理页复制本扩展的固定 id 填入 "
            "hr_check.channel.extension_id; 若配置里写了示例 token(如 123456), 请改为留空让程序自动生成到 "
            "<data_dir>/hr.token 并把新值填进扩展"
        )
    finally:
        runtime.stop()


def test_build_wires_service_endpoint_and_worker(tmp_path):
    """_build 的实参接线: 少传/传错会让服务、端点或线程行为静默错位"""
    runtime = make_runtime(tmp_path, enabled=True, channel=True)
    runtime.config.hr_check.channel.token = "abc123"
    runtime.start()
    try:
        assert runtime.service.data_dir == str(tmp_path)
        assert runtime.service.persist is True
        assert runtime.service._owner, "实例标识必须带上(心跳自检的唯一线索)"
        assert runtime.token == "abc123", "显式配置的密钥优先"
        assert runtime.status().token_source == "config"
        assert runtime.endpoint.extension_id == "a" * 32
        assert runtime.endpoint.force_fn == runtime.request_refresh
        assert runtime.worker.endpoint is runtime.endpoint
        assert runtime.worker.poll_interval == POLL_INTERVAL
        assert runtime.worker._web_active_fn == runtime._web_active
    finally:
        runtime.stop()


def test_build_clears_endpoint_and_token_when_no_channel(tmp_path):
    """从有通道切到无通道重启: 端点与 token 都要清掉(不留旧密钥)"""
    runtime = make_runtime(tmp_path, enabled=True, channel=True)
    runtime.start()
    assert runtime.token
    runtime.stop()
    runtime.config.hr_check = make_config(tmp_path, enabled=True, channel=False).hr_check
    runtime.start()
    try:
        assert runtime.endpoint is None and runtime.token == ""
    finally:
        runtime.stop()


def test_identity_tracks_enabled_and_channel_flags(tmp_path):
    on = make_config(tmp_path, enabled=True, channel=True).hr_check
    off = make_config(tmp_path, enabled=False, channel=False).hr_check
    ident = HrRuntime._identity(on)
    assert ident[0] is True and ident[1] is True
    assert ident != HrRuntime._identity(off)


def test_status_snapshot_fields_with_channel(tmp_path):
    runtime = make_runtime(tmp_path, enabled=True, channel=True, port=_free_port())
    runtime.start()
    try:
        runtime.publisher.publish(
            HrViewSet(views={"pt.example.com": HrSiteView(site="pt.example.com", listing="list")})
        )
        st = runtime.status()
        assert st.enabled is True and st.fetch_enabled is True and st.worker_running is True
        assert st.poll_interval == POLL_INTERVAL
        # 取数线程并发发布, 版本号是活的 —— 只钉「非 0」(发布器版本随时可能再抬)
        assert st.view_revision >= 1
        assert st.channel is not None
        assert st.channel.enabled is True and st.channel.listening is True
        assert st.channel.port == runtime.endpoint.port
        assert st.token_source == "file"
        assert st.note == ""
    finally:
        runtime.stop()


def test_status_reports_endpoint_not_started(tmp_path):
    """fetch_enabled 但端点未起(未 start): 合成一份「端点未启动」快照, 不让 channel 变 None"""
    port = _free_port()
    runtime = make_runtime(tmp_path, enabled=True, channel=True, port=port)
    st = runtime.status()
    assert st.fetch_enabled is True
    assert st.channel is not None
    assert st.channel.enabled is True and st.channel.listening is False
    assert st.channel.port == port
    assert st.channel.note == "端点未启动"


def test_status_snapshot_without_channel(tmp_path):
    runtime = make_runtime(tmp_path, enabled=True, channel=False)
    runtime.start()
    try:
        st = runtime.status()
        assert st.fetch_enabled is False
        assert st.channel is None
        assert st.note == "取数通道未启用(只读共享数据)"
    finally:
        runtime.stop()


def test_shared_dir_guidance_message_is_precise(tmp_path, caplog):
    runtime = make_runtime(tmp_path, enabled=True, channel=False)
    with caplog.at_level(logging.INFO, logger="auto_qb.hr"):
        runtime.start()
    try:
        want = (
            "hr_check.shared_dir 未配置: HR 站点文件落在 <data_dir>/hr/(单实例足够)。"
            "!若同一账号还跑了其它实例而没共享目录, 各实例的频控账本各一份 ⇒ 站点访问翻倍; "
            "多实例共享时请把它指向所有实例都能看到的同一目录(网络盘可以, 云同步盘不可用 —— "
            "锁与原子替换都不保证), 并让各实例用不同的 hr_check.channel.port"
        )
        msgs = [r.getMessage() for r in caplog.records]
        assert want in msgs, msgs
    finally:
        runtime.stop()


def test_channel_runtime_leaves_discovery_unbound(tmp_path):
    """本文件的 channel 用例必须默认关发现: 不绑共享固定端口 18788-18790(issue 26-10-16-0348)

    发现候选端口是固定连号(discovery_candidates): 并行(-n 8)下多个 worker 加上用户真实实例
    (实测正占着 18788)会把三个候选占满 ⇒ HrDiscoveryServer.start() 记 WARNING「全部被占」
    ⇒ 污染「生命周期/热重载消息只记 INFO」一族断言(该 issue 的两条偶发判红即此)。
    发现服务的行为单测在 test_hr_discovery.py(自选 _free_port 基底), 本文件没有一条测发现。
    """
    runtime = make_runtime(tmp_path, enabled=True, channel=True)
    runtime.start()
    try:
        assert runtime.discovery is None, "测试配置必须关发现: make_config 的 discovery_port 默认 0"
        assert runtime.endpoint is not None and runtime.endpoint.started, "数据端点不受影响(照常监听)"
    finally:
        runtime.stop()
