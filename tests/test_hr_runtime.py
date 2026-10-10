"""test_hr_runtime 测试计划: 运行时门面(端点 + 取数线程 + 热重载重挂 + 启动引导)

用最小假 manager 驱动门面(它只读 `manager.config` 与可选的 `_hr_anchors`),
不构造真 QbManager —— 那要连 qB 且持单实例锁, 与本模块的职责无关。

## 测试计划(每个测试函数一条)
- test_disabled_builds_nothing: 总开关关 -> 不建服务/线程/端点, start() 返回 False
- test_readonly_instance_without_channel: 无 channel 的实例仍跑取数线程, 但只读不抓(能力即角色)
- test_starts_endpoint_and_worker: 有 channel -> 端点真的在监听 + 线程在跑
- test_token_persisted_and_reused: 密钥落 <data_dir>/hr.token, 重启复用同一值
- test_port_conflict_is_fail_fast: 同端口第二个实例启动即报错(不静默降级)
- test_stop_releases_endpoint: stop() 后端口释放, 能再启动
- test_apply_remounts_on_channel_change: 改端口 -> 重挂(新端口在听, 旧端口释放)
- test_apply_keeps_endpoint_on_l0_change: 只改 L0 字段(轮询节奏) -> 端点不重绑
- test_apply_stops_when_disabled: 关掉功能 -> 线程与端点都停
- test_shared_dir_guidance_logged: shared_dir 留空 -> 一条 INFO 引导(不阻断启动)
- test_shared_dir_used_for_site_files: 配了 shared_dir -> 站点文件落在该目录
- test_status_reports_paths_and_channel: 自检快照字段齐全(路径/写者/端点/密钥来源)
- test_view_snapshot_and_wake_are_safe_when_not_started: 未启动时读视图/唤醒都安全
- test_judge_is_none_when_disabled: 总开关关 -> judge 返回 None(消费方回落本地字段逻辑)
- test_judge_reads_published_view: 启用时按**当前已发布**视图现算(命中清单 -> 受管束 + 站点达标结论)
- test_judge_without_published_view_falls_back: 还没发布过视图(启动窗口) -> None, 不是"未核实"- test_sleeper_is_interruptible_by_stop: 锁内等待可中断 —— 关停/热重挂不必等它把间隔睡完
- test_sleeper_returns_after_the_wait: 没被打断时按秒数返回(不提前也不卡住)
- test_production_service_gets_a_sleeper: 生产服务必须带 sleeper(2026-09-25 实报: 不等待 ⇒ 下载被页面饿死)
- test_apply_starts_worker_when_never_started: 站点接入热重载(启动时无站点) -> apply 必须把服务/线程/端点都带起来
  (旧版「未启动时 apply 不得拉起线程」是 2026-09-29「取数线程未启动」bug 的成因之一, 已随修复反转;
  端点「从无到有」同为该族缺陷 —— 只建对象不绑端口 ⇒ 扩展连不上端点)
- test_apply_rebinds_endpoint_after_all_sites_hot_disabled: 站点全关收掉端点后重新启用 -> 必须重新监听
- test_fetcher_fails_fast_when_endpoint_stops_listening: 端点不在监听 -> 取数立刻报无通道, 不白等 request_timeout
- test_apply_no_change_short_circuits: HR 侧无变化 -> apply 短路, 服务/线程对象原样保留不重启
- test_apply_adds_site_while_running: 已运行时热接入新站点 -> 服务站点表长出新站点且线程仍在跑
- test_runtime_uses_anchors_provider: 取数线程经主循环提供的锚点提供者取锚点(M3 的交接面)
- test_stop_is_prompt_while_waiting_for_extension: 取数线程正等扩展回传时 stop 也要立刻返回(不等满 request_timeout)
- test_restart_after_stop_works: 关停再启动能重新正常工作(叫停标记不得残留)
- test_start_stop_messages_are_info_not_warning: 启动/关闭类消息一律 INFO(它们会被 notify 推成系统通知)
- test_apply_remount_message_is_info: 热重载重挂端点也是预期动作, 同样只记 INFO
- test_site_origins_served_live_for_extension: /api/hr/sites 按配置现派生授权清单, 热加站点即生效且 mode=off 不出现

### P1 覆盖率提升轮: 运行时门面长尾
- test_sleeper_raises_immediately_when_stop_already_set: 关停标记已置 -> 进等待前即抛 HrChannelStopped
- test_wake_is_safe_and_forwards_to_worker: wake 转发线程(未启动空转)
- test_events_summaries_direct: events 连续失效文案与站点稳定排序直调

### hr 首轮变异审计轮: 运行时门面长尾(issue 26-10-10-1108-runtime-worker)
- test_init_defaults_fetcher_and_token: 门面初始 fetcher 是空通道(带可读 reason)、token 为空串
- test_start_disabled_logs_debug_message: 未启用时一条 DEBUG 说明为何不启动(精确文案)
- test_startup_message_reports_mode_sites_and_dir: 启动 INFO 报出模式/站点(多站按 ", " 拼接)/目录
- test_startup_message_readonly_mode: 无通道实例的启动文案是「只读共享」(不是「端点 + 取数」)
- test_extension_id_warning_message_is_precise: 纵深提示 WARNING 全文(前缀 + 四段引导)
- test_apply_l0_rebuilds_without_remounting_endpoint: 换全新站点配置对象走 L0 重建 -> 不重绑端点 + 精确 INFO
- test_apply_close_message_precise_when_sites_disabled: 站点全关(仅线程)时关停也要说一声「已关闭」
- test_apply_remount_message_is_precise: 重挂端点的 INFO 钉首尾(松匹配会被 service 的「重挂端点」文案顶替)
- test_web_active_reads_manager_web_live: WebUI 活跃现读回调(无 web 面/异常都保守 False)
- test_judge_forwards_anchor_and_now: judge 把 anchor/now 原样转交 judge_record(缺省 now=0.0)
- test_sleeper_zero_seconds_returns_immediately: sleeper(0.0) 立刻返回(不得被抬成最短 1s)
- test_sleeper_stop_message_is_precise: 中断抛的 HrChannelStopped 文案带「停止」
- test_build_wires_service_endpoint_and_worker: _build 的实参接线(service 目录/owner/persist, 端点 extension_id/force_fn, worker endpoint/poll/回调)
- test_build_clears_endpoint_and_token_when_no_channel: 切到无通道配置重启 -> 端点与 token 都清掉
- test_identity_tracks_enabled_and_channel_flags: 监听身份包含 enabled 与 channel.enabled 两位
- test_status_snapshot_fields_with_channel: 有端点时自检快照各字段(enabled/listening/port/token 来源/poll/revision/note)
- test_status_reports_endpoint_not_started: fetch_enabled 但端点未起 -> 合成快照(listening False / note「端点未启动」)
- test_status_snapshot_without_channel: 无端点且未启用通道 -> channel 为 None 且 note 提示只读
- test_anchors_collects_enabled_sites_only: 锚点表只收启用站点的非空 hash, 逐条跳过(不是遇阻即停)
- test_shared_dir_guidance_message_is_precise: shared_dir 留空引导 INFO 全文
- test_request_refresh_accepts_only_named_sites: 指定站点只受理该站(不是全量)
- test_request_refresh_note_is_precise: 受理回执 note 精确
- test_site_origins_skips_without_stopping: 授权清单逐条跳过 disabled / 无 host 的站点(不是遇阻即停)
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

H1 = "aa" * 20


class _FakeStore:
    """锚点构建只读 store.all()(plan §05: 实现迁门面后经 manager.store 只读取数)"""
    def all(self):
        return []


class _FakeManager:
    """门面只用到 config 与 store(锚点构建的只读数据源)"""
    def __init__(self, config, anchors=None, store=None):
        self.config = config
        self.store = store if store is not None else _FakeStore()  # anchors 参数已无消费方(P5 后 _anchors 自持实现), 留参兼容旧调用


def make_config(
    tmp_path,
    *,
    enabled=True,
    channel=False,
    port=0,
    shared_dir="",
    site_enabled=True,
    request_timeout=180.0,
    extension_id="a" * 32,
):
    # extension_id 默认填一个合法值: 端点纵深提示(extension_id 留空 = WARNING, 见
    # test_extension_id_empty_warns)不应打扰「测生命周期消息是 INFO」这类无关用例
    config = Config()
    config.data_dir = str(tmp_path)
    config.state_file = str(tmp_path / "state.json")
    config.hr_check = HrCheckConfig(
        enabled=enabled,
        channel=HrChannelConfig(enabled=channel, port=port, request_timeout=request_timeout, extension_id=extension_id),
        shared_dir=shared_dir,
    )
    config.trackers = {
        "pt.example.com":
            TrackerConfig(
                name="pt.example.com",
                domains=["pt.example.com"],
                hr_check=SiteHrCheckConfig(
                    enabled=site_enabled,
                    tracker="pt.example.com",
                    hr_page_url="https://pt.example.com/myhr.php",
                    required_seeding_time=2 * 86400.0,
                ),
            )
    }
    return config


def make_runtime(tmp_path, **kwargs):
    return HrRuntime(_FakeManager(make_config(tmp_path, **kwargs)))


def _free_port() -> int:
    """取一个当前空闲的端口(用于测「改端口要重挂」这类需要确定端口号的用例)"""
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


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


def test_view_snapshot_and_wake_are_safe_when_not_started(tmp_path):
    runtime = make_runtime(tmp_path, enabled=True, channel=True)
    assert runtime.revision == 0
    rev, views = runtime.view_snapshot()
    assert rev == 0 and views.views == {}
    runtime.wake()  # 未启动: 不得抛异常
    runtime.stop()  # 幂等


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
    errs: list = []

    def run():
        try:
            runtime.sleeper(30.0)
        except HrChannelStopped as e:
            errs.append(e)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    time.sleep(0.1)  # 让它真的睡进去
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
        deadline = time.monotonic() + 3.0
        while not calls and time.monotonic() < deadline:
            time.sleep(0.02)
        assert calls, "取数线程应经门面 _anchors 拿本地锚点(M3 的交接面)"
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


# ---------------- 立即拉取: runtime 汇合点(计划 26-09-30-0240) ----------------


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


# ==================== P1 覆盖率提升轮: 运行时门面长尾 ====================


def test_sleeper_raises_immediately_when_stop_already_set(tmp_path):
    """关停标记已置位时进入 sleeper -> 立刻抛 HrChannelStopped(不进入等待循环)"""
    runtime = make_runtime(tmp_path, enabled=True, channel=False)
    runtime._sleep_stop.set()
    with pytest.raises(HrChannelStopped):
        runtime.sleeper(30.0)


def test_wake_is_safe_and_forwards_to_worker(tmp_path):
    """wake 转发给取数线程(未启动时也安全不抛)"""
    runtime = make_runtime(tmp_path, enabled=True, channel=False)
    runtime.wake()  # 未启动: worker 为 None, 空转
    runtime.start()
    try:
        runtime.wake()  # 已启动: 转发 worker.wake()
    finally:
        runtime.stop()


def test_events_summaries_direct():
    """events 文案单点直调: 连续失效升级文案 / 站点清单稳定排序"""
    from auto_qb.hr import events

    text = events.lane_persistent_failure("example", "A", 3, "表头缺失")
    assert "已连续 3 波失效" in text and "example" in text
    assert events.summarize_sites(["beta", "alpha"]) == "alpha, beta"


# ==================== hr 首轮变异审计轮: 运行时门面长尾 ====================


def _two_site_config(tmp_path, **kwargs):
    """两站点配置: 站点清单的 ", " 拼接在多站点下才可辨"""
    config = make_config(tmp_path, **kwargs)
    config.trackers["pt2.example.com"] = TrackerConfig(
        name="pt2.example.com",
        domains=["pt2.example.com"],
        hr_check=SiteHrCheckConfig(
            enabled=True, tracker="pt2.example.com", hr_page_url="https://pt2.example.com/myhr.php"
        ),
    )
    return config


def test_init_defaults_fetcher_and_token(tmp_path):
    runtime = make_runtime(tmp_path, enabled=False)
    assert isinstance(runtime.fetcher, NullFetcher)
    assert runtime.token == ""
    with pytest.raises(HrChannelUnavailable) as err:
        runtime.fetcher.get_text("https://pt.example.com/myhr.php")
    assert str(err.value).startswith("HR 在线核实未启动")


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
    errs: list = []

    def run():
        try:
            runtime.sleeper(30.0)
        except HrChannelStopped as e:
            errs.append(e)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    time.sleep(0.2)  # 让它真的睡进 wait()
    runtime._sleep_stop.set()
    thread.join(5.0)
    assert errs, "等待中被打断必须抛 HrChannelStopped"
    assert str(errs[0]) == "取数通道已停止(正在关停或重挂): 放弃本轮剩余的等待", str(errs[0])


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
