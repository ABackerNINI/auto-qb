"""test_qbmanager 测试计划: qbmanager 全局任务/种子查询/连接/主循环

## 测试计划(每个测试函数一条)
- test_create_global_tasks: 按配置创建 delete_tags 等全局任务
- test_connect_failure: 连接失败返回 False 且 client 为 None
- test_connect_success: 连接成功返回 True 并登录(客户端经 new_client 构造)
- test_new_client_local_disables_trust_env: 本地地址用 LocalQbClient, Session(含重建)trust_env 恒为 False
- test_new_client_sets_request_timeout: P1-5 守卫——客户端必须带请求超时(否则 qB 假死时界面永久假死)
- test_new_client_local_host_variants: localhost/IPv6 本机写法同样判定为本地
- test_new_client_remote_keeps_default_trust_env: 远程地址用原生 Client 且保留 trust_env 默认
- test_throttle_sleeps_without_stop_event: 非托管模式节流真实睡眠且返回 False
- test_throttle_waits_stop_event: 托管模式节流走 Event.wait 并回传停止信号
- test_run_loop_throttles_without_stop_event: 非托管模式主循环每轮 sleep(main_tick)(回归守卫)
- test_run_loop_managed_never_sleeps: 传 stop_event 时不 sleep(托盘模式停止信号即时响应)
- test_run_loop_layered_cadence: 分层节拍——同步线按 sync_interval、任务线按 main_tick, 两线次数不等
- test_wake_drains_commands_without_extra_ticks: 命令唤醒只走命令线, 命令风暴下 tick 次数不增加
- test_drain_web_commands_reports_resync_needed: P0-5 门控——只有改种子状态的命令置 changed
- test_command_batch_triggers_single_resync: P0-5 一批命令后补**一次**完整刷新(整批合单)
- test_drain_web_commands_bumps_write_seq: P1-4 失效接线——写命令自增 web.write_seq, 自投递不自增
- test_drain_bumps_write_seq_before_writing_receipt: BUG-5 顺序——回执写入时写序号须已自增
- test_run_due_requeues: handler 成功 -> run_due 收尾重入队(run_count+1, 回 PENDING)
- test_run_due_dies: handler 返回 False -> 不重入(消亡)
- test_run_connect_failure: 非托管首连失败抛 QbConnectError(fail-fast -> CLI 退出码 1), 不进入主循环
- test_reconnect_backoff_and_reset: 重连指数退避(间隔翻倍、上限 30s、未到点不重试)且连接成功后归零
- test_run_main_loop: 主循环: _tick 异常被捕获, KeyboardInterrupt 停止, finally 清理
- test_tick_full_flow: 快速队列到期任务执行全流程(含 check 轮询任务首轮发送)
- test_create_torrent_tasks_tor_missing: 种子不在快照 -> 直接返回
- test_create_torrent_tasks_with_rules: 匹配 tracker -> 创建 maintenance + 规则任务
- test_handle_maintenance_tor_missing: 种子不存在 -> False(任务消亡)
- test_run_save_state_on_exit: run 退出后保存状态文件且为有效 JSON dict
- test_run_dry_run_no_save: dry_run=True 退出后不写状态文件
- test_periodic_flush_is_wired_in_run_loop: 接线守阵——周期落盘必须挂在主循环(not dry_run 门内), run() 加载状态后重置到期点
- test_tick_refresh_error_continues: 主循环内 _refresh_torrents 抛异常被捕获, 下一 tick 继续
- test_run_stopiteration_from_tick_not_swallowed: 守阵(26-10-02-0442)——_tick 的 StopIteration 在 except Exception 之前单独接住并重抛, 不得吞掉后继续下一拍
- test_run_exception_backs_off_next_tick: 守阵(26-10-02-0728)——主循环 except Exception 路径必须把 next_*_at 推到 max(原值, now+main_tick) 退避, 不得 wait_for=0 快速重试
- test_execute_due_respects_max: 每 tick 最多执行 max_tasks_per_tick 个, 超额留队列
- test_tick_no_due_task_empty_queue: 任务队列空时 tick 不执行任何任务
- test_refresh_added_no_tracker_match_skips: 新增种子未匹配 tracker 配置 -> 警告并跳过
- test_refresh_removed_grouping_disabled: 删除种子且分组关闭 -> 只移除任务不扫描
- test_refresh_suppress_window_exception_closes_window_in_finally: 守阵(26-10-06-0028 A-01)——suppress 窗内异常上抛后 live 旗标不残留, 下一成功轮 full_round 相位照常广播不被吞
- test_refresh_schema_validation_missing_raises: 首次拉到非空种子信息时校验字段, 缺失抛 QbCompatError
- test_refresh_schema_validation_passes_once: 全字段通过置 flag 不再重复校验
- test_export_torrents_info: export_torrents_info 写种子信息到文件
- test_view_rebuild_waits_for_client_consume: 节拍对齐门控 —— 上一版没被 /api/state 取走就不生产下一版(>3000 种子时约一半 rebuild 无人消费), 且**脏标记必须保留**; 命令驱动的那一轮 force=True **必须绕过**(P0-5 要求真值几十毫秒内进快照, 不能等客户端轮询)
- test_tick_rebuilds_all_views_when_changed: 视图变化且 Web 活跃 -> 四份视图同一入口**同次**重建
- test_tick_rebuilds_views_when_grouping_disabled: 分组未启用时脏标记不被吞, 视图照样重建
- test_qbmanager_source_has_no_web_state_fields: 静态守阵(2026-09-20 解耦, W3 起名单读分诊清单)——主循环源码不得直接读写表现层旧字段(别名层已删, 写回即静默造第二份真相, 只能靠扫描抓回潮)
- test_hr_anchors_from_store: HR 判定桥在构造时挂上 + 锚点按站点分组给出(QB 侧给取数线程的交接面)
- test_p2a_init_with_lock_cleans_orphan_tmp_and_releases: 持锁构造清孤儿 tmp; 释放后可再持锁 (P2-a)
- test_p2a_run_with_lock_releases_in_finally: run() finally 释放锁 (P2-a)
- test_p2a_run_managed_stop_event_exits_during_connect_retry: 托管模式连接失败遇停止信号干净返回 (P2-a)
- test_p2a_run_materializes_schema_migration_dry_run_then_write: run() 启动物化 dry-run 不落盘 / 非 dry-run 迁移+备份 (P2-a)
- test_p2a_sync_line_flush_propagates_to_host: _sync_line flush=True 经 host.run_sync_line; False 不调 (P2-a)
- test_p2a_refresh_added_pipeline_skips_ghost_and_unmatched: added 管线幽灵 hash / 未匹配 tracker 跳过 (P2-a)
"""
import json
import os
import tempfile
import threading
import time
from unittest import mock

from auto_qb.core.taskqueue import FINISHED, PENDING, REQUEUE, Task, TaskQueue
import pytest

from qbittorrentapi import APIConnectionError, Client

from auto_qb.config import QbittorrentConfig
from auto_qb.infra.errors import AutoQbError
from auto_qb.core.qbclient import REQUESTS_TIMEOUT, LocalQbClient, new_client
from auto_qb.core.qbmanager import RECONNECT_MAX_INTERVAL, QbConnectError, QbManager, _throttle
from auto_qb.torrents import QbCompatError
from helpers import FakeClient, FakeConfig, FakeTorrent, make_manager, seed_store


def test_create_global_tasks():
    """delete_tags 配置存在时创建 internal 全局任务并入队"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        # 无 delete_tags 配置: 不创建
        mgr._create_global_tasks()
        names = [t.name for t in mgr.task_queue._fast]
        assert "delete_tags" not in names
        # 配置 delete_tags: 创建任务
        mgr.config.delete_tags = ["regex:^seed-"]
        mgr.config.delete_tags_if_has_no_torrents = ["regex:^orphan-"]
        mgr._create_global_tasks()
        names = [t.name for t in mgr.task_queue._fast]
        assert "delete_tags" in names
        assert "delete_tags_if_has_no_torrents" in names


def test_connect_failure():
    """连接失败返回 False 且 client 保持 None"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        with mock.patch("auto_qb.core.qbmanager.new_client", side_effect=Exception("conn refused")):
            assert mgr.connect() is False
        assert mgr.client is None


def test_connect_success():
    """连接成功返回 True 并登录(客户端经 new_client 构造: 本地地址由它选 LocalQbClient)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        fake = mock.Mock()
        with mock.patch("auto_qb.core.qbmanager.new_client", return_value=fake) as new_client:
            assert mgr.connect() is True
        new_client.assert_called_once_with(mgr.config.qbittorrent)
        fake.auth_log_in.assert_called_once()
        assert mgr.client is fake


def test_new_client_local_disables_trust_env():
    """本地地址: LocalQbClient 使 trust_env 在**每次(重)建 Session** 后都为 False

    旧实现(连上后给 client._session.trust_env 赋 False)会在库重建 Session 时静默失效 ——
    此处用 _trigger_session_initialization() 显式复现该重建(库在 build_base_url()/
    _initialize_context() 中就是这样丢弃旧 Session 的)。
    """
    cfg = QbittorrentConfig(host="127.0.0.1", port=1, username="u", password="p")
    client = new_client(cfg)
    assert type(client) is LocalQbClient
    first = client._session
    assert first.trust_env is False
    client._trigger_session_initialization()
    second = client._session
    assert second is not first, "库应已重建 Session(证明控制点在 property 上而非一次性赋值)"
    assert second.trust_env is False


def test_new_client_sets_request_timeout():
    """P1-5 守卫: 客户端必须带请求超时(连接 3s / 读 10s)

    不设超时时 qB 假死(进程还在但不再响应)会让请求**无限期挂起**: 主循环线程被命令执行占住 ⇒
    连重连退避都跑不起来, 表现为"点一下之后整个界面再也不动"。
    读超时刻意宽松(10s): /files 在几千文件的种子上响应体很大, 截窄会把它误判成断连。
    """
    cfg = QbittorrentConfig(host="127.0.0.1", port=1, username="u", password="p")
    client = new_client(cfg)
    assert client._REQUESTS_ARGS.get("timeout"
                                    ) == REQUESTS_TIMEOUT, (f"客户端缺少请求超时, 实际 {client._REQUESTS_ARGS} —— qB 假死时请求会无限期挂起")
    # 远程地址同样要带(企业代理下连接阶段更可能卡住)
    remote = new_client(QbittorrentConfig(host="qb.example.com", port=8080))
    assert remote._REQUESTS_ARGS.get("timeout") == REQUESTS_TIMEOUT


def test_new_client_local_host_variants():
    """localhost / IPv6 本机写法同样判定为本地(取 base_url 的 hostname, 容忍带端口/带协议)"""
    for host in ("localhost", "[::1]", "127.0.0.1"):
        client = new_client(QbittorrentConfig(host=host, port=8080))
        assert type(client) is LocalQbClient, host


def test_new_client_remote_keeps_default_trust_env():
    """远程地址: 用原生 Client 且 trust_env 保持 requests 默认(企业代理/netrc 可能真实需要)"""
    client = new_client(QbittorrentConfig(host="qb.example.com", port=8080))
    assert type(client) is Client
    assert client._session.trust_env is True


def test_throttle_sleeps_without_stop_event():
    """非托管模式(stop_event=None): 真实阻塞 main_tick 秒且返回 False(不当作停止信号)"""
    with mock.patch("auto_qb.core.qbmanager.time.sleep") as fake_sleep:
        assert _throttle(None, 2.0) is False
    fake_sleep.assert_called_once_with(2.0)


def test_throttle_waits_stop_event():
    """托管模式: 走 Event.wait(保持对停止信号的即时响应), 原样回传其停止信号"""
    ev = mock.Mock()
    ev.wait.return_value = True
    assert _throttle(ev, 3.0) is True
    ev.wait.assert_called_once_with(3.0)


def test_run_loop_throttles_without_stop_event():
    """回归守卫: 非托管模式下主循环每轮必须真实阻塞到"下一条时间线", 不得空转

    曾因 `if stop_event is not None and stop_event.wait(main_tick)` 的短路使非托管模式
    完全不阻塞 -> 满速空转(py-spy 实证约 2800 tick/s), CPU 打满且 sync/maindata 请求量放大数千倍。

    分层节拍后阻塞原语换成了 `_wait_next`(非托管模式走 wake_event.wait(剩余时间)),
    故判据改为**真实经过时间**: 循环若不阻塞, 两次 _tick 会在微秒内连续发生。
    下界留 sleep 精度余量(见断言处注释)。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=True)
        main_tick = 0.05
        # 两条线同拍 -> 每轮走完整 _tick(与改造前"单一 cadence"的循环结构等价)
        mgr.config.main_tick = main_tick
        mgr.config.sync_interval = main_tick
        mgr._tick = mock.Mock(side_effect=[None, KeyboardInterrupt()])
        start = time.monotonic()
        mgr.run(dry_run=False)
        elapsed = time.monotonic() - start
        assert mgr._tick.call_count == 2
        # 下界 -20ms 余量: Windows 等待粒度按 15.6ms 定时器刻度取整, 50ms 等待可提前到
        # 46.8ms(3 刻度, 2026-09-22 实测假红) —— 空转是微秒级, 余量不损失判别力
        assert elapsed >= main_tick - 0.02, f"每轮循环后应阻塞到下一条时间线, 实际 {elapsed:.3f}s —— 主循环在空转"


def test_run_loop_managed_never_sleeps():
    """托管模式(传 stop_event): 阻塞走 Event.wait, 绝不调用 time.sleep(托盘停止信号即时响应)

    分层节拍后停止信号与命令唤醒是两个独立事件(Python 无多事件等待原语), `_wait_next`
    按 STOP_POLL_INTERVAL 分段 wait(stop_event) 并在段间检查唤醒 —— 分段不影响本用例
    的判据: 只要没走 time.sleep, 停止信号就仍是即时响应的。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=True)
        # 两条线同拍 -> 每轮走完整 _tick
        mgr.config.main_tick = 0.05
        mgr.config.sync_interval = 0.05
        mgr._tick = mock.Mock(side_effect=[None, KeyboardInterrupt()])
        stop_event = threading.Event()
        with mock.patch("auto_qb.core.qbmanager.time.sleep") as fake_sleep:
            mgr.run(dry_run=True, stop_event=stop_event)
        fake_sleep.assert_not_called()
        assert mgr._tick.call_count == 2


def test_run_loop_layered_cadence():
    """分层节拍: 同步线按 sync_interval、任务线按 main_tick, 两条线各有各的节拍

    这是"状态新鲜度不再被任务节拍拖累"的直接判据 —— 若退化成单一 cadence, 两线次数会相等。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=True)
        mgr.config.sync_interval = 0.05
        mgr.config.main_tick = 0.2
        calls = {"sync": 0, "task": 0}

        def sync_line(dry_run, flush=True, force=False):
            calls["sync"] += 1
            if calls["sync"] >= 12:
                raise KeyboardInterrupt  # 同步线 12 次 ≈ 0.6s 后退出

        def task_line(dry_run, force=False):
            calls["task"] += 1

        mgr._sync_line = sync_line
        mgr._task_line = task_line
        mgr.run(dry_run=False)
        assert calls["sync"] == 12
        # 0.6s / 0.2s ≈ 3 次(允许调度抖动); 关键是远小于同步线的 12 次
        assert 2 <= calls["task"] <= 4, f"任务线不应跟同步线同频, 实际 {calls['task']}"


def test_wake_drains_commands_without_extra_ticks():
    """P0-1 命令唤醒: 只走命令线 —— 命令风暴下 tick/同步线次数**不增加**, 但命令被立即消费

    反过来若退化成"投递即跑一轮 tick", 本用例的 task 计数会随唤醒次数一起涨。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=True)
        # 两条线都设成 5s: 若没有唤醒, 观测窗口内一次 drain 都不会发生
        mgr.config.main_tick = 5.0
        mgr.config.sync_interval = 5.0
        calls = {"drain": 0, "task": 0, "sync": 0}
        real_drain = mgr.web.consume_commands

        def drain():
            calls["drain"] += 1
            return real_drain()

        mgr.web.consume_commands = drain  # 命令线入口(门面), 主循环每轮调用它
        mgr._sync_line = lambda dry_run, flush=True, force=False: calls.__setitem__("sync", calls["sync"] + 1)
        mgr._task_line = lambda dry_run, force=False: calls.__setitem__("task", calls["task"] + 1)
        stop = threading.Event()

        def waker():
            for _ in range(3):
                time.sleep(0.15)
                mgr.wake()  # 模拟 Web 线程连续投递 3 条命令
            stop.set()
            mgr.wake()

        threading.Thread(target=waker, daemon=True).start()
        mgr.run(dry_run=False, stop_event=stop)
        # 命令线: 首轮 + 3 次唤醒(第 4 次唤醒与停止同时, 可能不再 drain)
        assert calls["drain"] >= 3, f"唤醒后应立即消费命令, 实际 drain {calls['drain']} 次"
        # 任务线/同步线: 只有首轮, 不因唤醒而增加
        assert calls["task"] == 1, f"唤醒不应触发任务线, 实际 {calls['task']}"
        assert calls["sync"] == 1, f"唤醒不应触发同步线, 实际 {calls['sync']}"


def test_drain_web_commands_reports_resync_needed():
    """P0-5 门控: 只有"改 qB 种子状态"的命令(RESYNC_COMMANDS)才置 changed"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        # handler 用替身(不碰 qB), 只验证 changed 判定
        mgr._cmd_pause_torrent = mock.Mock()
        mgr._cmd_reload_config = mock.Mock()
        mgr._cmd_build_search_index = mock.Mock()
        mgr.web.commands.put(("reload_config", {"cmd_id": "c1"}))
        mgr.web.commands.put(("build_search_index", {"cmd_id": "c2"}))
        assert mgr.web.consume_commands() is False, "配置热重载/索引构建改的不是种子状态, 不补刷新"
        mgr.web.commands.put(("pause_torrent", {"cmd_id": "c3", "hash": "HA"}))
        assert mgr.web.consume_commands() is True


def test_command_batch_triggers_single_resync():
    """P0-5: 一批改状态命令后补**一次**完整刷新(整批合单), 而不是每条一次

    判据: 同步线设成 5s(观测窗口内本不会再同步), 一批 5 条命令后刷新应恰好 +1。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=True)
        mgr.config.main_tick = 5.0
        mgr.config.sync_interval = 5.0  # 无补刷新时观测窗口内不会再次同步
        calls = {"refresh": 0}

        def refresh(dry_run=False):
            calls["refresh"] += 1
            if calls["refresh"] >= 2:
                raise KeyboardInterrupt  # 观测到"补的那一次"即退出

        mgr._refresh_torrents = refresh
        mgr._task_line = lambda dry_run, force=False: None
        mgr._cmd_pause_torrent = mock.Mock()
        stop = threading.Event()

        def poster():
            time.sleep(0.15)
            for i in range(5):
                mgr.web.commands.put(("pause_torrent", {"cmd_id": f"c{i}", "hash": "HA"}))
            mgr.wake()
            # 兜底: 补刷新缺失时循环不会自行退出(刷新停在 1 次), 这里兜住避免用例挂死
            time.sleep(0.8)
            stop.set()
            mgr.wake()

        threading.Thread(target=poster, daemon=True).start()
        mgr.run(dry_run=False, stop_event=stop)
        # 首轮(两条线都到期)一次 + 命令批一次 = 2; 5 条命令不产生 5 次
        assert calls["refresh"] == 2, f"一批 5 条命令应只补一次刷新, 实际 {calls['refresh']}"


def test_drain_web_commands_bumps_write_seq():
    """P1-4 只读缓存**失效接线**: 写命令执行后 `_web_write_seq` 必须自增; 自投递命令不得自增

    缓存以 `(key, write_seq)` 组键 ⇒ 序号不自增则缓存**永不失效**(改完分类仍看到旧列表);
    而自投递命令(build_search_index)频次高, 计进去会让缓存在建索引期间完全失效。
    此前全仓只测了缓存机制本身, 没有任何用例断言这条接线 —— 字段改名或把自增挪走
    都会让测试全绿而缓存静默失效。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr._cmd_reload_config = mock.Mock()
        mgr._cmd_build_search_index = mock.Mock()
        before = mgr.web.write_seq

        mgr.web.commands.put(("reload_config", {"cmd_id": "c1"}))
        mgr.web.consume_commands()
        assert mgr.web.write_seq == before + 1, "写命令执行后写序号必须自增(否则只读缓存永不失效)"

        mgr.web.commands.put(("build_search_index", {"cmd_id": "c2"}))
        mgr.web.consume_commands()
        assert mgr.web.write_seq == before + 1, "自投递命令不得自增(否则建索引期间缓存全废)"


def test_drain_bumps_write_seq_before_writing_receipt():
    """BUG-5: 先让缓存失效, 再宣布命令成功 —— 回执写入时写序号必须**已经**自增

    前端拿到回执会立刻重取只读端点(如改完分类重取 /api/categories); 若回执先写, 那一瞬的
    读会命中旧写序号的缓存键。用 spy 在 _set_web_result 内部观察当时看到的序号, 把顺序钉死。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr._cmd_reload_config = mock.Mock()
        seen = {}
        real_set = mgr.web.set_result

        def spy(cmd_id, status, error="", timing=None, truth=None):
            seen["seq"] = mgr.web.write_seq  # 回执写入那一刻的序号
            return real_set(cmd_id, status, error, timing, truth)

        mgr.web.set_result = spy  # 回执的唯一落点在门面(见 WebUIRuntime.set_result)
        before = mgr.web.write_seq
        mgr.web.commands.put(("reload_config", {"cmd_id": "c1"}))
        mgr.web.consume_commands()
        assert seen.get("seq") == before + 1, (f"回执写入时写序号应已自增(先失效缓存再宣布成功), 实际 {seen.get('seq')} vs 期望 {before + 1}")


def test_run_due_requeues():
    """run_due: handler 返回 True -> 收尾按 interval 重入队(run_count+1, 回 PENDING)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        task = Task("rule", "t", interval=60, handler=lambda t, d: REQUEUE)
        now = time.time()
        mgr.task_queue.add_task(task, now=now)
        assert mgr.task_queue.run_due(dry_run=False, now=now) == 1
        assert task.run_count == 1
        assert task.state == PENDING


def test_run_due_dies():
    """run_due: handler 返回 False -> 不重入(任务消亡)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        task = Task("rule", "t", interval=60, handler=lambda t, d: FINISHED)
        now = time.time()
        mgr.task_queue.add_task(task, now=now)
        assert mgr.task_queue.run_due(dry_run=False, now=now) == 1
        assert task.run_count == 0, "消亡任务不应重入队"


def test_run_connect_failure():
    """run: 非托管首连失败抛 QbConnectError(fail-fast, 经 finally 清理后穿透到 CLI 退出码 1), 不进入主循环"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=False)
        with pytest.raises(QbConnectError):
            mgr.run(dry_run=False)  # 抛错前 finally 应已清理; 不应调用 _tick
        mgr.connect.assert_called_once()


def test_reconnect_backoff_and_reset():
    """重连指数退避: 未到点不重试 / 间隔翻倍 / 上限 30s / 连接成功后归零

    修复前主循环每 tick 都 `client = None; connect()` —— qB 长时间宕机时每 2s 重建一次
    Client(含 netrc / 代理解析), 纯空转。退避后重试间隔逐步拉长到 30s, 恢复即归零。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        tick = 2.0
        clock = {"t": 1000.0}

        def _monotonic():
            return clock["t"]

        with mock.patch("auto_qb.core.qbmanager.time.monotonic", _monotonic):
            assert mgr._reconnect_due(tick) is True, "首次应立即重试"
            assert mgr._reconnect_at == pytest.approx(1000.0 + tick)
            # 未到点: 不重试
            clock["t"] += tick - 0.01
            assert mgr._reconnect_due(tick) is False
            # 到点: 重试, 间隔翻倍
            clock["t"] = 1000.0 + tick
            assert mgr._reconnect_due(tick) is True
            assert mgr._reconnect_at == pytest.approx(1000.0 + tick + 2 * tick)
            # 连续失败推到上限 30s 后不再增长
            for _ in range(12):
                clock["t"] = mgr._reconnect_at
                mgr._reconnect_due(tick)
            assert mgr._reconnect_interval == pytest.approx(RECONNECT_MAX_INTERVAL), (
                f"退避应封顶 {RECONNECT_MAX_INTERVAL}s: {mgr._reconnect_interval}"
            )
            # 连接成功(走真实 connect)后归零: 下次断开从最短间隔重新开始
            with mock.patch("auto_qb.core.qbmanager.new_client", return_value=mock.Mock()):
                assert mgr.connect() is True
            assert mgr._reconnect_interval == 0.0 and mgr._reconnect_at == 0.0
            assert mgr._reconnect_due(tick) is True, "归零后应能立即重试"


def test_run_main_loop():
    """run: 连接成功进入主循环; _tick 异常被捕获; KeyboardInterrupt 停止; finally 清理+保存"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = make_manager(state_file)
        mgr.connect = mock.Mock(return_value=True)
        # !节拍调小(26-10-02-0728): 异常路径现在会推进 next_*_at 退避, 第一次异常后主循环
        # 真等一个 main_tick 才进下一拍 —— 默认 1.0s 会让本用例多挂 1s。
        mgr.config.main_tick = 0.05
        mgr.config.sync_interval = 0.05
        mgr._tick = mock.Mock(side_effect=[RuntimeError("boom"), KeyboardInterrupt()])
        with mock.patch("auto_qb.core.qbmanager.time.sleep"):
            mgr.run(dry_run=False)
        assert mgr._tick.call_count == 2, "异常应被捕获继续循环, KeyboardInterrupt 退出"
        assert os.path.exists(state_file), "finally 应保存状态"


def test_tick_full_flow():
    """_tick: 快速队列到期任务执行(含 check 轮询任务首轮执行 + 常规任务 reschedule)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.torrents["HASH123"] = FakeTorrent(hash="HASH123", state="pausedUP")
        mgr.task_queue = TaskQueue()
        # check 轮询任务: 首轮执行后消亡(handler 返回 False)
        check_calls = []

        def check_poll(t, d):
            check_calls.append(1)
            return FINISHED

        mgr.task_queue.add_task(
            Task("check", "check-checking-result", hash="HASH123", interval=2.0, handler=check_poll)
        )
        # 常规到期任务
        due_task = Task("rule", "t", interval=0, handler=lambda t, d: REQUEUE)
        due_task.next_run = time.time() - 1
        mgr.task_queue._fast.append(due_task)
        mgr._refresh_torrents = mock.Mock()
        mgr._tick(dry_run=False)
        assert check_calls == [1], "check 任务应执行"
        assert due_task.run_count == 1, "到期任务应执行并 reschedule"


def test_create_torrent_tasks_tor_missing():
    """_create_torrent_tasks: 种子不在快照 -> 直接返回 False, 不建任务"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.client = FakeClient()
        assert mgr.host.get("rules")._create_torrent_tasks("NOPE") is False
        assert mgr.task_queue._fast == []


def test_create_torrent_tasks_with_rules():
    """_create_torrent_tasks: 匹配 tracker -> 创建 maintenance + 全部规则任务"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"), tracker_rules=["@example_rules.add_site_tag"])
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(hash="HASH123", tags="")
        tor.tracker_conf = mgr.config.trackers["HHan"]  # 显式 setUp: 模拟 _refresh_torrents 匹配
        client.torrents["HASH123"] = tor
        seed_store(mgr)
        mgr.host.get("rules")._create_torrent_tasks("HASH123")
        names = [t.name for t in mgr.task_queue._fast]
        assert "maintenance" in names, f"应创建内置任务: {names}"
        assert "example_rules.add_site_tag" in names, f"应创建规则任务: {names}"


def test_handle_maintenance_tor_missing():
    """_handle_maintenance_task_interface: 种子不存在 -> False(任务消亡, 不重入队)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.client = FakeClient()
        task = Task("internal", "maintenance", hash="NOPE", store=mgr.store)
        assert mgr.host.get("maintenance").handle_maintenance(task.torrent, dry_run=False) is False


def test_run_save_state_on_exit():
    """run: 非 dry_run 退出后保存状态文件, 且内容为有效 JSON dict"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = make_manager(state_file)
        mgr.connect = mock.Mock(return_value=True)
        mgr._tick = mock.Mock(side_effect=KeyboardInterrupt())
        with mock.patch("auto_qb.core.qbmanager.time.sleep"):
            mgr.run(dry_run=False)
        with open(state_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict), "状态文件应为 JSON dict"


def test_run_dry_run_no_save():
    """run: dry_run=True 退出后不写状态文件"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = make_manager(state_file)
        mgr.connect = mock.Mock(return_value=True)
        mgr._tick = mock.Mock(side_effect=KeyboardInterrupt())
        with mock.patch("auto_qb.core.qbmanager.time.sleep"):
            mgr.run(dry_run=True)
        assert not os.path.exists(state_file), "dry_run 不应写状态文件"


def test_periodic_flush_is_wired_in_run_loop():
    """接线守阵: 周期落盘必须挂在主循环正常路径(not dry_run 门内), 到期点在加载状态后重置

    maybe_flush 只在主循环线程调用是单一写线程约束的一部分; dry_run 门保证观察
    模式零磁盘写入(与退出路径 `if not dry_run` 口径一致); 启动即到期会造成无意义重写。
    """
    import inspect

    from auto_qb.core.qbmanager import QbManager

    src = inspect.getsource(QbManager.run)
    i_hook = src.find("maybe_flush")
    assert i_hook >= 0, "run() 必须接线周期落盘"
    assert "not dry_run" in src[max(0, i_hook - 200):i_hook], "周期落盘必须在 not dry_run 门内(dry-run 零磁盘写入)"
    assert "self.ctx.state.next_flush_at = time.time()" in src, "run() 加载状态后必须重置周期落盘到期点"


def test_tick_refresh_error_continues():
    """run 主循环: _refresh_torrents 抛异常被捕获, 循环继续到下一 tick"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = make_manager(state_file)
        mgr.connect = mock.Mock(return_value=True)
        # !节拍调小(26-10-02-0728): 异常路径现在会推进 next_*_at 退避, 第一次异常后主循环
        # 真等一个 main_tick 才进下一拍 —— 默认 1.0s 会让本用例多挂 1s。
        mgr.config.main_tick = 0.05
        mgr.config.sync_interval = 0.05
        # 第一次抛普通异常(被内层 except Exception 捕获), 第二次抛 KeyboardInterrupt(退出循环)
        mgr._refresh_torrents = mock.Mock(side_effect=[RuntimeError("refresh boom"), KeyboardInterrupt()])
        with mock.patch("auto_qb.core.qbmanager.time.sleep"):
            mgr.run(dry_run=False)
        assert mgr._refresh_torrents.call_count == 2, "第一次异常应被捕获, 第二次 tick 继续执行"


def test_run_stopiteration_from_tick_not_swallowed():
    """回归守阵(issue 26-10-02-0442): _tick 抛 StopIteration 不得被 except Exception 吞掉后继续下一拍

    StopIteration 是 Exception 子类, 修复前被吞后本轮 next_sync_at/next_tick_at 未推进,
    wait_for=0, while True 立即进下一拍 —— 「无 sleep、无工作」的静默空转死循环。修法:
    主循环在 except Exception 之前单独接住, ERROR 落日志后重抛(PEP 479 精神: StopIteration
    逃出 _tick 调用链 = 生成器误用 bug, 显式失败优于静默空转)。红验(修复前): StopIteration
    被吞, run() 正常返回, _tick 被调到第 2 个兜底退出点 —— 本用例当时判红。
    """
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = make_manager(state_file)
        mgr.connect = mock.Mock(return_value=True)
        # 连续 StopIteration: 修复前每一拍都被吞下去(第 2 个 KeyboardInterrupt 只是红验时的兜底退出点)
        mgr._tick = mock.Mock(side_effect=[StopIteration(), KeyboardInterrupt()])
        with mock.patch("auto_qb.core.qbmanager.time.sleep"):
            with pytest.raises(StopIteration):
                mgr.run(dry_run=False)
        assert mgr._tick.call_count == 1, "StopIteration 必须当场穿透 run(), 不得进入下一拍"


def test_run_exception_backs_off_next_tick():
    """守阵(26-10-02-0728): 主循环异常路径必须推进 next_*_at 退避, 不得 wait_for=0 快速重试

    except Exception 只记日志不推进 next_sync_at/next_tick_at —— 首轮两者是 0.0, 非首轮是
    已到期的过去值, wait_for 恒算出 0, while True 立即进下一拍重跑同一条线再炸一次, 形成
    无退避的快速重试循环(ERROR 刷屏 + CPU 空转)。StopIteration 已重抛(26-10-02-0442)、
    APIConnectionError 走 _reconnect_due 退避, 均不在此列; 修法: 异常分支把两条时间线推到
    max(原值, now + main_tick), 失败的线最早下个节拍重试(退避起步与 _reconnect_due 一致)。
    三条线都替换成炸点: 异常发生在哪条线(双到期走 _tick / 单到期走 _sync_line/_task_line)
    取决于浮点时间边界, 全替换保证判据与分支选择解耦。
    红验(修复前): 异常拍之间间隔 ≈ 0(wait_for=0), gaps 断言当时判红。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=True)
        mgr.config.main_tick = 0.2
        mgr.config.sync_interval = 0.2
        stop_event = threading.Event()
        tick_at: list = []

        def boom(dry_run, flush=True, force=False):
            tick_at.append(time.monotonic())
            if len(tick_at) >= 3:
                stop_event.set()
            raise RuntimeError("tick boom")

        mgr._tick = boom
        mgr._sync_line = boom
        mgr._task_line = boom
        mgr.run(dry_run=True, stop_event=stop_event)
        assert len(tick_at) == 3, f"应恰好 3 拍后停: {len(tick_at)}"
        gaps = [b - a for a, b in zip(tick_at, tick_at[1:])]
        assert all(g >= 0.15 for g in gaps), f"异常拍之间必须退避 >= main_tick(0.2s): {gaps}"


def test_connect_throttle_repeated_failures():
    """连接失败节流: 主循环内 _tick 多次抛 APIConnectionError 只记录一次错误, 断开期间静默不刷屏"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = make_manager(state_file)
        mgr.connect = mock.Mock(return_value=True)
        # 第一次失败记录, 第二次失败静默, 第三次抛 KeyboardInterrupt 退出循环
        mgr._refresh_torrents = mock.Mock(
            side_effect=[APIConnectionError("conn down"),
                         APIConnectionError("conn down"),
                         KeyboardInterrupt()]
        )
        with mock.patch("auto_qb.core.qbmanager.logger") as mock_logger:
            with mock.patch("auto_qb.core.qbmanager.time.sleep"):
                mgr.run(dry_run=False)
        errors = [c for c in mock_logger.error.call_args_list]
        assert len(errors) == 1, f"连接失败应只记录一条(节流), 实际 {len(errors)}: {errors}"
        assert "连接 qBittorrent 失败" in errors[0][0][0], f"应记录连接失败: {errors[0]}"
        assert mgr._last_conn_ok is False, "连接失败后状态应为断开"
        # 确认 _tick 确实被调用了 3 次(第一次记录错误, 第二次静默, 第三次退出)
        assert mgr._refresh_torrents.call_count == 3


def test_connect_recovery_logged():
    """连接恢复: 断开后重新连接成功记录'已重新连接'

    !必须 patch `new_client`(不是 `Client`): `connect()` 走的是 `qbclient.new_client`,
    patch `qbmanager.Client` 根本不生效 ⇒ 会真的去连 `127.0.0.1:16585`。那条路径是否抛异常
    **取决于机器/网络环境**(2026-09-19 Linux CI 上 connect() 返回 False, Windows 本地却绿),
    用例因此时好时坏。换成 patch 真正被调用的那个名字, 用例与网络彻底解耦。
    """
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = make_manager(state_file)
        mgr._last_conn_ok = False  # 模拟此前断开
        fake = mock.Mock()
        with mock.patch("auto_qb.core.qbmanager.new_client", return_value=fake):
            with mock.patch("auto_qb.core.qbmanager.logger") as mock_logger:
                assert mgr.connect() is True
        assert mgr._last_conn_ok is True, "重连成功后状态应为已连接"
        infos = [c for c in mock_logger.info.call_args_list]
        assert any("已重新连接" in c[0][0] for c in infos), f"应记录重新连接日志: {infos}"


def test_execute_due_respects_max():
    """_tick: 每 tick 最多执行 max_tasks_per_tick 个到期任务, 超额留在队列"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.client = FakeClient()
        mgr.task_queue = TaskQueue()
        mgr.config.max_tasks_per_tick = 2
        for i in range(3):
            t = Task("rule", f"t{i}", interval=60, handler=lambda t, d: REQUEUE)
            mgr.task_queue.add_task(t)  # next_run=now, 全部到期
        mgr._refresh_torrents = mock.Mock()
        mgr._tick(dry_run=False)
        executed = [t.name for t in mgr.task_queue._fast if t.run_count == 1]
        remaining = [t.name for t in mgr.task_queue._fast if t.run_count == 0]
        assert len(executed) == 2, f"每 tick 最多执行 max_tasks_per_tick=2: {executed}"
        assert len(remaining) == 1, f"超额任务应留在队列: {remaining}"


def test_tick_no_due_task_empty_queue():
    """任务队列为空: tick 刷新后无到期任务, 不执行任何任务"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.client = FakeClient()  # 无种子
        mgr._tick(dry_run=True)
        assert mgr.task_queue.run_due(time.time(), max_tasks=10) == 0


def test_refresh_added_no_tracker_match_skips():
    """新增种子未匹配任何 tracker 配置: 警告并跳过, 不写限速/不建任务"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.torrents["U1"] = FakeTorrent(hash="U1", name="T1")
        mgr.config.trackers = {}  # 无任何 tracker 配置
        mgr._refresh_torrents()
        assert client.calls == []
        assert mgr.task_queue.run_due(time.time(), max_tasks=10) == 0


def test_refresh_schema_validation_missing_raises():
    """首次拉到非空种子信息时校验必需字段: 缺失抛 QbCompatError(qB 版本漂移早暴露)"""
    from types import SimpleNamespace

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        # 模拟 qB 版本不兼容: torrent info 缺少 ratio/seeding_time 等字段
        client.torrents["H1"] = SimpleNamespace(hash="H1", name="T1", state="stalledUP")
        with pytest.raises(QbCompatError) as excinfo:
            mgr._refresh_torrents()
        assert "缺少字段" in str(excinfo.value)


def test_refresh_schema_validation_passes_once():
    """全字段样本通过校验并置 flag; 后续 refresh 不再重复校验(qB 版本运行期不变)"""
    from types import SimpleNamespace

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
        mgr._refresh_torrents()  # 首次: 校验通过
        assert mgr._schema_validated is True
        # 第二轮: flag 已置, 即使出现缺字段对象也不再校验(防御性断言 flag 语义)
        client.torrents["H1"] = SimpleNamespace(hash="H1", name="T1", state="stalledUP")
        mgr._refresh_torrents()  # 不抛


def test_refresh_removed_grouping_disabled():
    """检测到删除种子且分组功能关闭: 移除任务但不触发组内缺文件扫描"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
        seed_store(mgr)  # 首轮快照已同步
        del client.torrents["H1"]  # 种子被删除
        mgr._refresh_torrents()
        assert mgr.store.get("H1") is None
        assert mgr.config.grouping.enabled is False  # 分组关闭: 跳过组内扫描


def test_refresh_suppress_window_exception_closes_window_in_finally():
    """守阵(26-10-06-0028 A-01): suppress 窗内异常上抛后 live 旗标不残留, 下一成功轮相位不被吞

    事件分派两相位窗口(events_removed 前 arm -> events_added 后 close)内异常原样上抛
    (issue 取证源: ctx.trackers.match 网络异常; emit 无逐订阅者隔离), 关窗点必须在
    finally 兜底: 残留 live 旗标会把下一成功刷新轮的 full_round / events_* 全吞
    (emit 返回 0), 边沿驱动事件不可重放。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
        seen: list = []
        mgr.events.on("full_round", lambda event: seen.append("full_round"))
        # match 异常只注入 added 循环调用点(窗内), full_round 订阅者(_on_full_round)同方法
        # 需照常成功 —— 按调用序给效果: R1 全量轮(成功) / R1 added 循环(炸) / R2 全量轮(成功) / R2 added 循环(炸)
        mgr.ctx.trackers.match = mock.Mock(
            side_effect=[None, RuntimeError("match boom"), None,
                         RuntimeError("match boom")]
        )
        mgr.events.request_suppression()  # 热重载首轮: 挂请求位, take 即 arm
        with pytest.raises(RuntimeError, match="match boom"):
            mgr._refresh_torrents()
        assert not mgr.events.suppressed, "异常路径关窗: live 旗标不得残留(try/finally 兜底)"
        # 下一成功刷新轮(强制全量同步触发 full_round): 相位照常广播, 不被残留旗标吞掉
        # (本轮无新增种子, added 循环不跑, 刷新完整走完)
        seen.clear()
        mgr.store.rid = 0
        mgr._refresh_torrents()
        assert seen == ["full_round"], "下一成功轮 full_round 相位照常广播(修复前被吞)"


def test_export_torrents_info():
    """export_torrents_info: 全量种子逐条写入文件(debug 用)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
        client.torrents["H2"] = FakeTorrent(hash="H2", name="T2")
        out = os.path.join(td, "torrents.txt")
        mgr.export_torrents_info(out)
        text = open(out, encoding="utf-8").read()
        lines = [ln for ln in text.splitlines() if ln.strip()]
        assert len(lines) == 2, f"每个种子一行, 共 2 条: {lines}"
        assert text.count("\n\n") == 2  # 每条种子后空行分隔


def test_tick_rebuilds_all_views_when_changed():
    """视图惰性重建: 仅视图变化且 Web 活跃时重建 —— **四份视图同一入口同次重建**

    历史缺陷(2026-09-18, 症状"种子页速度冻结、状态栏正常"): 主循环曾**只**重建
    `_group_view` 就把共享的 `_group_view_dirty` 清掉 ⇒ Web 线程的兜底重建永不触发,
    singles/shows/flat 三份视图长期停留在旧快照, 而版本号照常自增 ⇒ 前端判
    `updated=true` 把**陈旧数组整表换上去**; 状态栏"速度合计"因取 groups 求和反而一直新鲜。

    故本用例断言的是"四份视图**同次**重建", 而不是"某一份被重建" —— 只断言其中一份
    会漏掉这个缺陷(原用例正是只 spy 了 `_build_group_view`, 把缺陷固化成了预期行为)。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.client = FakeClient()
        mgr.config.grouping.enabled = True
        mgr.web.touch()  # Web 活跃
        with mock.patch.object(mgr, "_refresh_torrents"), \
             mock.patch.object(mgr, "_build_group_view", return_value=[]) as g, \
             mock.patch.object(mgr, "_build_singles_view", return_value=[]) as s, \
             mock.patch.object(mgr, "_build_shows_view", return_value={"list": [], "unrecognized": []}) as sh, \
             mock.patch.object(mgr, "_build_flat_view", return_value=[]) as f:
            counts = lambda: (g.call_count, s.call_count, sh.call_count, f.call_count)  # noqa: E731
            mgr.store.view_changed = True
            mgr._tick(dry_run=False)
            assert counts() == (1, 1, 1, 1)  # 视图变化 -> 四份同次重建
            mgr._tick(dry_run=False)
            assert counts() == (1, 1, 1, 1)  # 标记已消费且无新变化 -> 不重建
            # WARN: 新增前提: 上面那一版**还没被任何 /api/state 请求取走**(pending 未清) ⇒
            # 即便又脏了也不生产新版本(节拍对齐门控)。这里模拟客户端取走一次再继续。
            mgr.store.view_changed = True
            mgr._tick(dry_run=False)
            assert counts() == (1, 1, 1, 1)  # 上一版没人取 -> 不重建(脏标记保留)
            mgr.web.ensure_state(mgr.web.group_view_ver)  # 客户端取走当前版本
            mgr._tick(dry_run=False)
            assert counts() == (2, 2, 2, 2)  # 已取走 + 仍脏 -> 重建, 且四份同次
            mgr.store.view_changed = True
            mgr.web.last_seen = 0.0  # Web 不活跃(超过 TTL)
            mgr._tick(dry_run=False)
            assert counts() == (2, 2, 2, 2)  # 不重建
            assert mgr.web.group_view_dirty is True  # 脏标记保留, 待 Web 恢复后重建


def test_view_rebuild_waits_for_client_consume():
    """节拍对齐: 上一版没被 /api/state 取走就不生产下一版; 命令驱动的那轮必须绕过

    服务端 `sync_interval` 固定 1.5s, 而前端 `basePollMs()` 按种子量取 1.5/2/3s ⇒
    >3000 种子时服务端每 3s 产 2 版、客户端只取最后一版, 中间那版的重建 CPU 无人消费
    (issues/26-09-19-1900-webui-poll-cadence-mismatch, 方案 B)。
    这里让"生产"等"消费": `_web_pending_ver` 未清(没人取)就不重建, 但**脏标记必须保留**
    (否则这次变化会被丢掉) —— 客户端一取走立刻补上。

    WARN: `force=True`(本轮有命令改了种子状态)**必须绕过** —— P0-5 要求用户操作后真值几十毫秒内
    进快照; 若被门控挡住, 真值要等客户端下一次轮询才可见, 与 P0-5 相悖。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.client = FakeClient()
        mgr.web.touch()  # Web 活跃
        with mock.patch.object(mgr, "_refresh_torrents"), mock.patch.object(
            mgr, "_build_group_view", return_value=[]
        ) as g, mock.patch.object(mgr, "_build_singles_view", return_value=[]), mock.patch.object(
            mgr, "_build_shows_view", return_value={
                "list": [],
                "unrecognized": []
            }
        ), mock.patch.object(mgr, "_build_flat_view", return_value=[]):
            # 1. 首版: 无 pending -> 重建, 并登记"这一版还没人取走"
            mgr.store.view_changed = True
            mgr.web.flush_views()
            assert g.call_count == 1
            assert mgr.web.pending_ver == mgr.web.group_view_ver

            # 2. 又脏了但上一版还没人取 -> **不生产**(这就是省掉的那一次)
            mgr.store.view_changed = True
            mgr.web.flush_views()
            assert g.call_count == 1, "上一版没人取就再产一版 = 白烧 CPU(节拍错配的症状)"
            assert mgr.web.group_view_dirty is True, "脏标记必须保留, 否则这次变化会被丢掉"

            # 3. 命令驱动: force=True 必须绕过门控(P0-5: 真值不能等客户端轮询)
            mgr.web.flush_views(force=True)
            assert g.call_count == 2, "命令改了状态就必须立刻重建, 不能等客户端轮询"
            assert mgr.web.group_view_dirty is False

            # 4. 客户端取走当前版本(此时不脏, 不会顺带重建) -> pending 清空
            mgr.web.ensure_state(mgr.web.group_view_ver)
            assert mgr.web.pending_ver is None
            assert g.call_count == 2

            # 5. 已被取走 -> 门控重新打开, 再脏就能重建
            mgr.store.view_changed = True
            mgr.web.flush_views()
            assert g.call_count == 3


def test_tick_rebuilds_views_when_grouping_disabled():
    """分组未启用: 视图**仍须**重建(种子页平铺视图与"辅种分组是否启用"无关)

    历史缺陷: 整个重建块曾被 `if grouping.enabled` 包住 —— 而 `consume_view_changed()`
    在块**外**已把脏标记读走复位 ⇒ 分组关闭时标记无处落地、永久丢失 ⇒ 版本号不再变化
    ⇒ 前端 `updated=false` 并退避轮询, 四份视图全部冻住。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.client = FakeClient()
        mgr.config.grouping.enabled = False
        mgr.web.touch()
        with mock.patch.object(mgr, "_refresh_torrents"), \
             mock.patch.object(mgr, "_build_group_view", return_value=[]) as g, \
             mock.patch.object(mgr, "_build_singles_view", return_value=[]) as s, \
             mock.patch.object(mgr, "_build_shows_view", return_value={"list": [], "unrecognized": []}) as sh, \
             mock.patch.object(mgr, "_build_flat_view", return_value=[]) as f:
            mgr.store.view_changed = True
            mgr._tick(dry_run=False)
            assert (g.call_count, s.call_count, sh.call_count, f.call_count) == (1, 1, 1, 1)
            assert mgr.web.group_view_dirty is False  # 标记被真正消费(不是被吞掉)


def test_qbmanager_source_has_no_web_state_fields():
    """静态守阵: 主循环源码不得直接读写表现层旧字段(防回潮)

    2026-09-20 解耦后 19 个表现层字段归 WebUIRuntime, QbManager 只经 `self.web` 的门面方法
    交互; 兼容代理曾把旧字段名**静默转发** —— 代码照样能跑, 状态归属却散回核心域。别名层处置
    W3 已把代理删除, 现在写 `self._group_view = ...` 会在实例上直接造出第二份真相(与 runtime
    那份互不可见且不报错), 比转发期更隐蔽, 仍只能靠扫描源码抓住。旧字段名单以分诊清单为准
    (退役名单永久留档, 守阵 tests/test_qbmanager_alias_freeze.py 同源); 别名表已不存在, 无需豁免。
    """
    import json
    import re

    src = open(
        os.path.join(os.path.dirname(__file__), "..", "src", "auto_qb", "core", "qbmanager.py"), encoding="utf-8"
    ).read()
    triage = json.loads(
        open(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "memory-bank",
                "plans",
                "26-10-01-0350-plan-web-state-alias-disposal.triage.json",
            ),
            encoding="utf-8",
        ).read()
    )
    hits = [old for old in triage["alias_layer"]["fields"] if re.search(rf"self\.{re.escape(old)}\b", src)]
    assert not hits, (
        f"主循环源码又直接引用了表现层旧字段 {hits} —— 应改用 self.web 的门面方法"
        "(consume_commands / flush_views / flush_receipts / mark_dirty …)"
    )


def test_hr_anchors_from_store():
    """HR 判定桥在构造时挂上 + 锚点提供者(主循环给取数线程的交接面, 计划 §9)

    锚点形状/站点键必须与取数侧一致(`refresh_site(site, anchors)` 取 infohash -> HrAnchor),
    否则「本实例二次下载 ⇒ 放行立即作废」永远发现不了 —— 而且不会报错。
    """
    from auto_qb.config.models import SiteHrCheckConfig
    from auto_qb.hr.resolve import HrAnchor

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        assert mgr.store.hr_link is mgr.hr, "判定桥必须构造时就挂上(记录读取时现算, 不靠遍历刷新)"
        assert mgr.hr._anchors() == {}, "站点未接入 hr_check -> 不上交任何锚点"

        site = mgr.config.trackers["HHan"]
        site.hr_check = SiteHrCheckConfig(
            enabled=True, tracker="hhan", hr_page_url="https://hhan/myhr.php", required_seeding_time=86400.0
        )
        # 用真记录(store.refresh), 不用 seed_store 的对象身份注入: 锚点由 record.hr_anchor() 派生
        mgr.store.refresh([FakeTorrent(hash="H1"), FakeTorrent(hash="H2")])
        got = mgr.store.get("H1")
        got.tracker_conf = site
        got.infohash_v1 = "aa" * 20
        got.added_on = 11
        got.downloaded = 123
        anchors = mgr.hr._anchors()  # H2 未匹配 tracker_conf -> 不进锚点
        assert set(anchors) == {"HHan"} and set(anchors["HHan"]) == {"aa" * 20}
        assert anchors["HHan"]["aa" * 20
                              ] == HrAnchor(added_on=11, downloaded=123, completion_on=-1, progress=0.0, name="Test")

        site.hr_check = SiteHrCheckConfig(enabled=False)  # 站点关掉 -> 同样不上交
        assert mgr.hr._anchors() == {}


# ---------------- P2-a 长尾清偿 (计划 26-10-01-2157 §3 P2, 2026-10-02) ----------------


def test_p2a_init_with_lock_cleans_orphan_tmp_and_releases():
    """持锁构造(no_lock=False): acquire 后清上次崩溃遗留的孤儿 tmp; 释放后可再次持锁"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        orphan = state_file + ".crashleft.tmp"
        with open(orphan, "w", encoding="utf-8") as f:
            f.write("{}")
        cfg = FakeConfig()
        cfg.state_file = state_file
        mgr = QbManager("", config=cfg, no_lock=False)
        try:
            assert not os.path.exists(orphan), "持锁后应清掉孤儿 tmp 文件"
            assert mgr._lock is not None
        finally:
            mgr._lock.release()
        # 锁已释放: 第二个实例可再次持锁(证明第一个真的持有过)
        mgr2 = QbManager("", config=cfg, no_lock=False)
        mgr2._lock.release()


def test_p2a_run_with_lock_releases_in_finally():
    """run() 正常退出路径(finally): 持锁构造下锁必须被释放(停机后其他实例可接管)"""
    with tempfile.TemporaryDirectory() as td:
        cfg = FakeConfig()
        cfg.state_file = os.path.join(td, "state.json")
        mgr = QbManager("", config=cfg, no_lock=False)
        mgr.connect = mock.Mock(return_value=True)
        mgr._tick = mock.Mock(side_effect=[None, KeyboardInterrupt()])
        mgr.run(dry_run=False)
        assert mgr.connect.call_count == 1
        # 锁已释放: 再次持锁应成功
        from auto_qb.infra.locking import SingleInstanceLock

        SingleInstanceLock(cfg.state_file).acquire()  # 不抛 = 已释放
        lock2 = SingleInstanceLock(cfg.state_file)
        lock2.acquire()
        lock2.release()


def test_p2a_run_managed_stop_event_exits_during_connect_retry():
    """托管模式: 连接失败且停止信号已置位 -> 等待中被唤醒, run 干净返回(不抛 QbConnectError)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=False)
        stop_event = threading.Event()
        stop_event.set()
        mgr.run(dry_run=False, stop_event=stop_event)  # 不抛即通过
        assert mgr.connect.call_count == 1, "停止信号生效: 不无限重试连接"


def test_p2a_run_materializes_schema_migration_dry_run_then_write():
    """run() 启动物化: dry-run 只探测不落盘(425); 非 dry-run 迁移+备份落盘(427)"""
    from auto_qb.config import load_config

    legacy = (
        "config:\n"
        "  qbittorrent:\n"
        "    host: h\n"
        "    port: 1\n"
        "    username: u\n"
        "    password: p\n"
        "  trackers:\n"
        "    BTSchool:\n"
        "      domains: [pt.btschool.club]\n"
        "      hr:\n"
        "        required_seeding_time: 3D\n"
        "      hr_check:\n"
        "        mode: partial\n"
        "        adapter: nexusphp\n"
        "        hr_page_url: https://pt.btschool.club/myhr.php\n"
        "        refresh_interval: 6H\n"
    )
    with tempfile.TemporaryDirectory() as td:
        cfg = FakeConfig()
        cfg.state_file = os.path.join(td, "state.json")
        cfg.data_dir = os.path.join(td, "data")
        config_path = os.path.join(td, "config.yml")
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(legacy)
        mgr = make_manager(cfg.state_file)
        mgr.config.data_dir = cfg.data_dir
        mgr.config_path = config_path
        mgr.connect = mock.Mock(return_value=True)
        mgr._tick = mock.Mock(side_effect=[None, KeyboardInterrupt()])
        # dry-run: 迁移只报内存生效, 磁盘一字不动
        mgr.run(dry_run=True)
        with open(config_path, encoding="utf-8") as f:
            assert "schema_version" not in f.read(), "dry-run 不得写盘"
        # 非 dry-run: 迁移落盘 + 版本号备份(重武装 _tick: 上一次的 side_effect 已耗尽,
        # StopIteration 会被主循环 except Exception 吞掉导致空转死循环)
        mgr._tick = mock.Mock(side_effect=[None, KeyboardInterrupt()])
        mgr.run(dry_run=False)
        with open(config_path, encoding="utf-8") as f:
            assert "schema_version: 4" in f.read(), "磁盘应落当前版本章"
        backup = os.path.join(cfg.data_dir, "config.yml.v1.bak")
        assert os.path.exists(backup), "迁移前备份应存在"
        load_config(config_path)  # 迁移后磁盘可原样通过加载


def test_p2a_sync_line_flush_propagates_to_host():
    """_sync_line flush=True: 视图收尾钩子经 host.run_sync_line 执行; flush=False 不调"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.client = FakeClient()
        with mock.patch.object(mgr.host, "run_sync_line") as hook:
            mgr._sync_line(dry_run=True, flush=True, force=True)
            hook.assert_called_once_with(True)
        with mock.patch.object(mgr.host, "run_sync_line") as hook2:
            mgr._sync_line(dry_run=True, flush=False, force=False)
            assert hook2.call_count == 0, "flush=False 不执行视图收尾钩子"


def test_p2a_refresh_added_pipeline_skips_ghost_and_unmatched():
    """added 管线守卫: 新增 hash 快照缺失(防御分支)与匹配不到 tracker 且域名拉取抖动 -> 跳过不崩溃"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        client.torrents_trackers = lambda h: [{"url": "http://unknown.example.com/announce"}]  # 匹配不到
        mgr.client = client
        t = FakeTorrent(hash="HB", name="T", state="stalledUP")
        client.torrents["HB"] = t
        client.torrents["HGONE"] = FakeTorrent(hash="HGONE", name="G", state="stalledUP")

        orig_get = mgr.store.get

        def ghost_get(h):
            if h == "HGONE":
                return None  # 模拟 added 里有但快照已取走(防御分支语义)
            return orig_get(h)

        from auto_qb.torrents import TorrentRecord

        with mock.patch.object(mgr.store, "get", side_effect=ghost_get), mock.patch.object(
            mgr.ctx.trackers, "match", return_value=None
        ), mock.patch.object(TorrentRecord, "trackers_info", side_effect=RuntimeError("api down")):
            mgr._refresh_torrents(False)  # 不崩溃: GHOST 跳过 / HB 匹配失败且域名拉取抖动 -> 空域名告警跳过
        assert orig_get("HB") is not None, "未匹配种子记录保留(告警由管线负责)"
        assert not any(c[0].startswith("set_") for c in client.calls), "未匹配种子不限速不建任务"
