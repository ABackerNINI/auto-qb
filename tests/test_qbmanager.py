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
- test_run_loop_expect_landing_pulls_sync_forward: 添加种子后的有界追平(issue 26-10-30-0626) —— store 有待落地 hash 时同步线被提前到 ~80ms(不等 sync_interval), 追平轮带 force, 次数用尽后自动放弃
- test_drain_web_commands_reports_resync_needed: P0-5 门控——只有改种子状态的命令置 changed
- test_command_batch_triggers_single_resync: P0-5 一批命令后补**一次**完整刷新(整批合单)
- test_sync_moved_proxy: S4(26-10-21-2323) —— 「本轮是否有变化」代理判据: delta/新增/删除任一非空即为真
- test_cmd_resync_keeps_schedule_when_nothing_moved: S4(26-10-21-2323) —— 补刷新没拿到变化时不推后下一次同步(否则校正反而更晚)
- test_drain_web_commands_bumps_write_seq: P1-4 失效接线——写命令自增 web.write_seq, 自投递不自增
- test_drain_bumps_write_seq_before_writing_receipt: BUG-5 顺序——回执写入时写序号须已自增
- test_run_due_requeues: handler 成功 -> run_due 收尾重入队(run_count+1, 回 PENDING)
- test_run_due_dies: handler 返回 False -> 不重入(消亡)
- test_own_write_defer_gate_targets_group_members: A 系 S2 D-1 队列闸门判据 —— 目标 hash 或其组任一成员 ∈ own_writes 即让位
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
- test_run_client_none_reconnects_without_error_spam: 守阵(26-10-31-1029)——断连稳态(client=None+_last_conn_ok=False)跳过请求线走 _reconnect_due 重连, 成功即补同步并记「已重新连接」, 不得落「主循环异常」逐拍刷屏且 connect() 不再被调
- test_execute_due_respects_max: 每 tick 最多执行 max_tasks_per_tick 个, 超额留队列
- test_tick_no_due_task_empty_queue: 任务队列空时 tick 不执行任何任务
- test_refresh_added_no_tracker_match_skips: 新增种子未匹配 tracker 配置 -> 警告并跳过
- test_refresh_removed_grouping_disabled: 删除种子且分组关闭 -> 只移除任务不扫描
- test_refresh_suppress_window_exception_closes_window_in_finally: 守阵(26-10-06-0028 A-01)——suppress 窗内异常上抛后 live 旗标不残留, 下一成功轮 full_round 相位照常广播不被吞
- test_refresh_schema_validation_missing_raises: 首次拉到非空种子信息时校验字段, 缺失抛 QbCompatError
- test_refresh_schema_validation_passes_once: 全字段通过置 flag 不再重复校验
- test_export_torrents_info: export_torrents_info 写种子信息到文件(编码恒 utf-8, GBK 外字符不崩)
- test_view_rebuild_waits_for_client_consume: 节拍对齐门控 —— 上一版没被 /api/state 取走就不生产下一版(>3000 种子时约一半 rebuild 无人消费), 且**脏标记必须保留**; 命令驱动的那一轮 force=True **必须绕过**(P0-5 要求真值几十毫秒内进快照, 不能等客户端轮询)
- test_tick_rebuilds_all_views_when_changed: 视图变化且 Web 活跃 -> 四份视图同一入口**同次**重建
- test_tick_rebuilds_views_when_grouping_disabled: 分组未启用时脏标记不被吞, 视图照样重建
- test_qbmanager_source_has_no_web_state_fields: 静态守阵(2026-09-20 解耦, W3 起名单读分诊清单)——主循环源码不得直接读写表现层旧字段(别名层已删, 写回即静默造第二份真相, 只能靠扫描抓回潮)
- test_hr_anchors_from_store: HR 判定桥在构造时挂上 + 锚点按站点分组给出(QB 侧给取数线程的交接面)
- test_p2a_init_with_lock_cleans_orphan_tmp_and_releases: 持锁构造清孤儿 tmp; 释放后可再持锁 (P2-a)
- test_p2a_run_with_lock_releases_in_finally: run() finally 释放锁 (P2-a)
- test_p2a_run_managed_stop_event_exits_during_connect_retry: 托管模式连接失败遇停止信号干净返回 (P2-a)
- test_a07_connect_non_api_error_transition_throttled: 守阵(26-10-06-0028 A-07)——非 API 连接异常(凭据错)与连接类同用转换节流, 失败态重复 connect 不重复 ERROR
- test_a07_managed_first_connect_retry_warns_once: 守阵(A-07)——托管首连重试 WARNING 只说明白一次, 停止信号仍即时响应
- test_p2a_run_materializes_schema_migration_dry_run_then_write: run() 启动物化 dry-run 不落盘 / 非 dry-run 迁移+备份 (P2-a)
- test_p2a_sync_line_flush_propagates_to_host: _sync_line flush=True 经 host.run_sync_line; False 不调 (P2-a)
- test_p2a_refresh_added_pipeline_skips_ghost_and_unmatched: added 管线幽灵 hash / 未匹配 tracker 跳过 (P2-a)
- test_connect_recovery_logged
- test_connect_throttle_repeated_failures
- test_w6_wait_next_waits_full_timeout: 守阵(W6)——托管等待必须睡满 timeout(等待归零=CPU 空转回归)
- test_w6_init_signature_and_field_contracts: 守阵(W6)——签名默认值与构造期字段契约(no_lock/dry_run 默认 False、api.store 绑定、初始值)
- test_w6_init_loads_config_from_path: 守阵(W6)——config 未传时必须以 config_path 加载配置
- test_w6_init_wires_fs_notify_relocate: 守阵(W6)——fs.path_map 产出 Mapped 映射访问层 + notify/relocate 模块挂真 ctx
- test_w6_init_creates_state_dir_console_only: 守阵(W6)——console-only 配置下数据目录必须显式创建
- test_w6_connect_false_on_api_connection_error: 守阵(W6)——APIConnectionError 分支必须报失败(fail-fast 契约)
- test_w6_connect_error_detail_logged: 守阵(W6)——连接失败 ERROR 必须带异常详情(两分支)
- test_w6_pause_branch_keeps_looping: 守阵(W6)——暂停分支等待实参契约 + 暂停不退化为停机 + 停止 INFO
- test_w6_next_flush_at_respects_save_interval: 守阵(W6)——周期落盘到期点 = now+interval(0=关闭不得强转)
- test_w6_task_line_receives_dry_run: 守阵(W6)——任务线必须收到 dry_run 位置实参(缺参=TypeError 退避环)
- test_w6_periodic_flush_gate_and_migration_arg: 守阵(W6)——周期落盘 not dry_run 门 + materialize_migration 实参
- test_w6_truth_pending_drives_retry_arc: 守阵(W6)——真值未落地按 0.2s 重试弧持续补同步且 force=True
- test_w6_truth_pending_one_shot_no_extra_sync: 守阵(W6)——真值落地(flush 清空)后不得继续重试弧
- test_w6_cmd_forced_and_t_line_contract: 守阵(W6)——cmd_forced 门控契约 + 命令线计时弧恰发一次
- test_w6_micro_deadline_merged_into_wait: 守阵(W6)——微步到期必须并入等待超时
- test_w6_micro_deadline_does_not_delay_lines: 守阵(W6)——更晚的微步到期不得推迟同步/任务线
- test_w6_flush_fallback_once_per_round: 守阵(W6)——回执 flush 每轮恰一次(异常轮兜底/正常轮不重复) + KI 停止 INFO
- test_w6_conn_recovery_flag_flip: 守阵(W6)——线跑通后连接状态必须翻回已连接
- test_w6_conn_failed_error_detail: 守阵(W6)——断连 ERROR 必须带异常详情
- test_w6_stopiteration_error_detail: 守阵(W6)——StopIteration ERROR 消息与堆栈不得丢真
- test_w6_generic_exception_error_detail: 守阵(W6)——主循环异常 ERROR 消息与堆栈不得丢真
- test_w6_migration_and_start_stop_logs: 守阵(W6)——迁移/启动/停止 INFO 审计面 + desc 空不打迁移日志
- test_w6_apply_new_config_contract: 守阵(W6)——热重载回执契约 + qbittorrent 段变重连(双向) + 汇总日志
- test_w6_apply_new_config_restart_gate: 守阵(W6)——R 级闸返回需重启段且日志保留提示
- test_w6_apply_new_config_unclaimed_fallback: 守阵(W6)——未认领段兜底: WARNING + rebuild_runtime 相位 + 回执条目契约
- test_w6_sync_line_contract: 守阵(W6)——同步线默认 flush/force 与 dry_run 传递契约
- test_w6_task_line_contract: 守阵(W6)——任务线 run_due 实参契约(defer_gate 身份) + 收尾 force 默认
- test_w6_tick_contract: 守阵(W6)——_tick 双线合轮实参契约(sync flush=False / task force 直传)
- test_w6_refresh_transitions_phase_payload: 守阵(W6)——transitions 相位与载荷契约
- test_w6_refresh_events_removed_and_scan_phase: 守阵(W6)——events_removed/removed_scan 相位载荷契约(含删除前快照)
- test_w6_refresh_suppression_window_opens: 守阵(W6)——抑制请求位必须真正开窗(两事件相位不派发)
- test_w6_refresh_events_added_phase_payload: 守阵(W6)——events_added 相位载荷契约
- test_w6_refresh_torrents_added_phase_payload: 守阵(W6)——torrents_added 逐种子相位载荷契约
- test_w6_refresh_post_phase_payload: 守阵(W6)——post 相位载荷契约
- test_w6_refresh_matching_loop_continues_past_skips: 守阵(W6)——匹配循环跳过(幽灵/未匹配)不截断后续种子
- test_w6_refresh_fs_selfcheck_once: 守阵(W6)——映射自检一次性闸门: 恰好首轮全量跑一次且实参为 save_path 清单
- test_w6_refresh_search_index_dirty_on_add_only: 守阵(W6)——单边新增/删除都必须标搜索索引脏
- test_w6_refresh_added_logging_domains: 守阵(W6)——新增 INFO/未匹配 WARNING 审计面 + 诊断域名来自真实拉取
- test_w6_export_torrents_info_pins_utf8_encoding: 守阵(W6, 平台相关)——导出 open 探针钉 encoding="utf-8"
"""
import json
import logging
import os
import tempfile
import threading
import time
from unittest import mock

from auto_qb.core.taskqueue import FINISHED, PENDING, REQUEUE, Task, TaskQueue
import pytest

from qbittorrentapi import APIConnectionError, Client

from auto_qb.config import QbittorrentConfig
from auto_qb.config import PathMapEntry
from auto_qb.config.models import FsConfig
from auto_qb.infra.errors import AutoQbError
from auto_qb.infra import file_access
from auto_qb.infra.file_access import MappedFileAccess
from auto_qb.core.module import ApplyResult
from auto_qb.core import qbmanager as _qbm
from auto_qb.core.qbclient import REQUESTS_TIMEOUT, LocalQbClient, new_client
from auto_qb.core.qbmanager import RECONNECT_MAX_INTERVAL, QbConnectError, QbManager, _throttle, _wait_next
from auto_qb.torrents import QbCompatError
from helpers import LEGACY_V1, FakeClient, FakeConfig, FakeTorrent, capture_logs, make_manager, seed_store


def _daemon_timer(seconds, fn):
    """后台兜底停止定时器(变异环/挂起防呆): 到点置 stop, 正常路径自行 cancel"""
    t = threading.Timer(seconds, fn)
    t.daemon = True
    t.start()
    return t


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


def test_run_loop_expect_landing_pulls_sync_forward():
    """添加种子后的有界追平: store 有待落地 hash 时, 同步线被提前到 ~80ms 而不是等节拍

    issue 26-10-30-0626 候选 A: qB 的 add 是四跳异步管线, 命令后那次补刷新必然只拿到一部分,
    剩下的原本要等 sync_interval(1.5s)。登记待落地后主循环应按 store 给的到期时刻再问一次;
    本用例把 sync_interval 设成 5s —— 没有追平, 观测窗口内根本不会有第二次同步。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=True)
        mgr.config.sync_interval = 5.0
        mgr.config.main_tick = 5.0
        stamps, forces = [], []

        def sync_line(dry_run, flush=True, force=False):
            stamps.append(time.time())
            forces.append(force)
            if len(stamps) == 1:
                mgr.store.expect_hashes(["H1"])  # 模拟 add 命令受理后登记
                return
            # 同步跑了但这一批还没进 session: 零变化轮(走 _apply 早退分支, 结算同样生效)
            mgr.store._apply({}, [], full=False)
            if len(stamps) >= 4:
                raise KeyboardInterrupt

        mgr._sync_line = sync_line
        mgr._task_line = mock.Mock()
        mgr.run(dry_run=False)

        assert len(stamps) == 4, f"应有首次补刷新 + 3 次追平, 实际 {len(stamps)} 次"
        gaps = [b - a for a, b in zip(stamps, stamps[1:])]
        assert all(g < 1.0 for g in gaps), f"追平间隔应 ~80ms 而非 5s 节拍, 实际 {gaps}"
        assert forces[1:] == [True] * 3, "追平轮必须 force(否则被「上一版已取走」门控挡掉)"
        assert mgr.store._expect_pending == {"H1"}, "次数未用尽前应保留待办"


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


def test_sync_moved_proxy():
    """S4: `_sync_moved()` 只看本轮是否真有变化(delta/新增/删除任一非空)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        assert mgr._sync_moved() is False, "空库/无变化轮应为假"
        mgr.store.delta_fields = {"HA": frozenset({"progress"})}
        assert mgr._sync_moved() is True, "有字段变化应为真"
        mgr.store.delta_fields = {}
        mgr.store.last_added = ["HA"]
        assert mgr._sync_moved() is True, "有新增应为真"
        mgr.store.last_added = []
        mgr.store.last_removed = ["HA"]
        assert mgr._sync_moved() is True, "有删除应为真"


def test_cmd_resync_keeps_schedule_when_nothing_moved():
    """S4: 补刷新没拿到变化时**不推后**下一次同步

    时间线: sync_interval=1.0s, 首轮(t≈0)按时同步 -> 下次到期 1.0s; t≈0.9s 一条改状态命令触发
    补刷新, 但它读到同一份节流缓存(delta 全空) -> 到期点必须仍是 1.0s(旧行为会推到 1.9s)。
    判据: 观测到 3 次刷新, 且第 3 次与首轮的间隔 ≈1.0s(阈值 1.4s, 旧行为约 1.9s)。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=True)
        mgr.config.main_tick = 10.0
        mgr.config.sync_interval = 1.0
        stamps = []

        def refresh(dry_run=False):
            stamps.append(time.time())
            if len(stamps) >= 3:
                raise KeyboardInterrupt  # 观测到第 3 次即退出(不必等满窗口)

        mgr._refresh_torrents = refresh
        mgr._task_line = lambda dry_run, force=False: None
        mgr._cmd_pause_torrent = mock.Mock()
        stop = threading.Event()

        def poster():
            time.sleep(0.9)
            mgr.web.commands.put(("pause_torrent", {"cmd_id": "c1", "hash": "HA"}))
            mgr.wake()
            time.sleep(1.5)  # 兜底: 第 3 次没来时不挂死
            stop.set()
            mgr.wake()

        threading.Thread(target=poster, daemon=True).start()
        mgr.run(dry_run=False, stop_event=stop)
        assert len(stamps) >= 3, f"应观测到 3 次刷新(按时/补刷新/下一个按时): {len(stamps)}"
        gap = stamps[2] - stamps[0]
        assert gap < 1.4, f"补刷新无变化时不得推后节拍(第 3 次应 ≈1.0s, 实得 {gap:.2f}s)"


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


def test_own_write_defer_gate_targets_group_members():
    """守阵(A 系 S2 D-1): 队列级 deferral 闸门判据 —— 目标 hash 或其组任一成员 ∈ own_writes 即让位

    红验: 去掉 _own_write_defer_gate 的组维度(只判 hash ∈ own_writes) -> `HC` 断言红。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        seed_store(mgr, [FakeTorrent(hash="HD"), FakeTorrent(hash="HC"), FakeTorrent(hash="HX")])
        mgr.store.groups["K"] = ["HD", "HC"]
        mgr.store.member_to_key["HD"] = "K"
        mgr.store.member_to_key["HC"] = "K"
        gate = mgr._own_write_defer_gate

        assert gate(Task("rule", "r", hash="HX")) is None, "无登记时不拦"
        assert gate(Task("rule", "r", hash="")) is None, "无 hash 全局任务不拦"
        mgr.store.note_own_write("HD")
        assert gate(Task("rule", "r", hash="HD")) is not None, "自身命中"
        assert gate(Task("rule", "r", hash="HC")) is not None, "同组成员命中(组维度)"
        assert gate(Task("rule", "r", hash="HX")) is None, "非同组不拦"


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


def test_run_client_none_reconnects_without_error_spam():
    """回归守阵(issue 26-10-31-1029): 断连稳态必须走重连判定, 不得落进请求线

    修复前: except APIConnectionError 分支置 client=None 后, 未到 _reconnect_due 时下一拍
    照常跑同步线 —— store 把 AttributeError(None client 误入 _SYNC_UNAVAILABLE)当「qB 不
    支持 sync/maindata」降级, 回退 torrents_info 再次 AttributeError, 穿到 except Exception
    记「主循环异常」逐拍 ERROR; 且该路径不调 connect(), qB 恢复后永不回连。
    修法: 主循环加断连稳态守卫(client=None 且 _last_conn_ok=False)——跳过请求线, 直接
    _reconnect_due → connect(), 成功后本轮立即补同步并记「已重新连接 qBittorrent」。
    红验(修复前): AttributeError 路径逐拍炸「主循环异常」, connect() 首连后再不被调,
    无回连 INFO —— 本用例当时判红(红验兜底 60 拍后置位停止信号, 防用例挂死)。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.config.main_tick = 0.05
        mgr.config.sync_interval = 0.05
        stop_event = threading.Event()
        connect_attempts: list = []

        def fake_connect():
            connect_attempts.append(1)
            n = len(connect_attempts)
            if n == 1:
                # 启动首连成功(与真 connect 同语义: 成功即留下非 None client)
                mgr.client = mock.Mock()
                return True
            if n == 2:
                # 首次重连仍失败(真实现中 new_client 抛 APIConnectionError: client 保持 None)
                return False
            # 第二次重连成功(qB 恢复): 真 connect 成功路径 = 落 client + _note_conn_ok
            stop_event.set()
            mgr.client = mock.Mock()
            mgr._note_conn_ok()
            return True

        tick_calls: list = []

        def boom_tick(dry_run, force=False):
            # 模拟 issue 现场态: 断连转换早已记录(_last_conn_ok=False), client 停在 None,
            # 同步线误入 None client 炸 AttributeError(修复前从这里逐拍刷「主循环异常」)
            tick_calls.append(1)
            if len(tick_calls) >= 60:  # 红验兜底: 修复前 AttributeError 路径无出口, 防用例挂死
                stop_event.set()
            mgr._last_conn_ok = False
            mgr.client = None
            raise AttributeError("'NoneType' object has no attribute 'torrents_info'")

        mgr.connect = fake_connect
        mgr._tick = mock.Mock(side_effect=boom_tick)
        mgr._sync_line = mock.Mock()
        mgr._task_line = mock.Mock()
        with mock.patch("auto_qb.core.qbmanager.logger") as mock_logger:
            mgr.run(dry_run=True, stop_event=stop_event)
        assert mgr._tick.call_count == 1, (f"断连后请求线必须被守卫跳过, _tick 只应首轮执行一次, 实际 {mgr._tick.call_count}")
        assert len(connect_attempts) == 3, f"应走到第 3 次 connect(重连成功): {len(connect_attempts)}"
        assert mgr._sync_line.call_count == 1, "重连成功后守卫应立即补一次同步, 不等下一节拍"
        errors = [str(c.args[0]) for c in mock_logger.error.call_args_list]
        spam = [m for m in errors if "主循环异常" in m]
        assert len(spam) == 1, f"「主循环异常」只应首轮一条(断连后由守卫接管), 实际 {len(spam)}: {errors}"
        infos = [str(c.args[0]) for c in mock_logger.info.call_args_list]
        assert any("已重新连接 qBittorrent" in m for m in infos), f"重连成功必须记 INFO 收尾: {infos}"


def test_connect_throttle_repeated_failures():
    """连接失败节流: 主循环内 _tick 多次抛 APIConnectionError 只记录一次错误, 断开期间静默不刷屏"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = make_manager(state_file)

        # connect 替身与真实现同语义(26-10-31-1029): 成功必须留下非 None client ——
        # 否则断连稳态守卫会把 None client 拦在请求线之外, 三次线级失败序列走不到
        def fake_connect():
            mgr.client = mock.Mock()
            return True

        mgr.connect = mock.Mock(side_effect=fake_connect)
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
    """export_torrents_info: 全量种子逐条写入文件(debug 用); 编码恒 utf-8 —— 含 GBK 外
    字符的种子名不崩(Windows 默认 cp936 会 UnicodeEncodeError 中途崩; issue
    26-10-06-0028 chore-export-torrents-info-encoding)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
        client.torrents["H2"] = FakeTorrent(hash="H2", name="T2")
        # U+20000 不在 GBK 内: 无显式 encoding 时 cp936 环境写到该种子即崩
        # (FakeTorrent 无 __str__, 落盘是对象 repr; 这里用带名字 __str__ 的桩验证编码)
        client.torrents["H3"] = type("NamedStub", (), {"name": "种子𠀀X", "__str__": lambda self: self.name})()
        out = os.path.join(td, "torrents.txt")
        mgr.export_torrents_info(out)
        text = open(out, encoding="utf-8").read()
        lines = [ln for ln in text.splitlines() if ln.strip()]
        assert len(lines) == 3, f"每个种子一行, 共 3 条: {lines}"
        assert text.count("\n\n") == 3  # 每条种子后空行分隔
        assert "种子𠀀X" in text, "GBK 外字符按 utf-8 如实落盘"
        # 静态钉: 本机默认编码恰为 utf-8 时行为面红验不可达(与 O_TRUNC 守阵同判), 源码级
        # 断言 export_torrents_info 必须显式 encoding="utf-8" —— 还原 open(path, "w") 即红
        import inspect

        src = inspect.getsource(type(mgr).export_torrents_info)
        assert 'encoding="utf-8"' in src, "export_torrents_info 必须显式 encoding=utf-8(禁 open(path, 'w'))"


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
        mgr = make_manager(cfg=cfg, no_lock=False)
        try:
            assert not os.path.exists(orphan), "持锁后应清掉孤儿 tmp 文件"
            assert mgr._lock is not None
        finally:
            mgr._lock.release()
        # 锁已释放: 第二个实例可再次持锁(证明第一个真的持有过)
        mgr2 = make_manager(cfg=cfg, no_lock=False)
        mgr2._lock.release()


def test_p2a_run_with_lock_releases_in_finally():
    """run() 正常退出路径(finally): 持锁构造下锁必须被释放(停机后其他实例可接管)"""
    with tempfile.TemporaryDirectory() as td:
        cfg = FakeConfig()
        cfg.state_file = os.path.join(td, "state.json")
        mgr = make_manager(cfg=cfg, no_lock=False)
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


def test_a07_connect_non_api_error_transition_throttled():
    """守阵(26-10-06-0028 A-07): 非 API 类连接异常(典型凭据错 LoginError)与连接类同用转换节流

    修复前 connect() 的 except Exception 无条件 ERROR —— 托管模式首连重试循环每 main_tick
    调一次 connect(), 凭据错误场景逐拍 ERROR 刷屏。守阵: 失败态下重复 connect 不再重复
    ERROR(同因只说明白一次); 连接恢复后再失败重新报一次(状态转换)。
    (日志断言用 capture_logs 不用 caplog: QbManager 构造链清 root handlers, 见 helpers。)
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        with mock.patch("auto_qb.core.qbmanager.new_client", side_effect=Exception("Login failed")):
            with capture_logs("auto_qb.core.qbmanager") as cap:
                assert mgr.connect() is False  # 首次失败: ERROR 一次
                assert mgr.connect() is False  # 失败态再失败: 静默
        errors = [r for r in cap.records if r.levelno == logging.ERROR]
        assert len(errors) == 1, f"同因失败只说明白一次, 实际 {len(errors)} 条 ERROR"
        # 状态转换: 连接成功(翻转 _last_conn_ok)后再失败, 重新报一次
        with mock.patch("auto_qb.core.qbmanager.new_client", return_value=mock.Mock()):
            assert mgr.connect() is True
        with mock.patch("auto_qb.core.qbmanager.new_client", side_effect=Exception("Login failed")):
            with capture_logs("auto_qb.core.qbmanager") as cap:
                assert mgr.connect() is False
        assert len([r for r in cap.records if r.levelno == logging.ERROR]) == 1


def test_a07_managed_first_connect_retry_warns_once():
    """守阵(A-07): 托管模式首连重试循环的 WARNING 只说明白一次, 停止信号仍即时响应"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.config.main_tick = 0.01
        stop = threading.Event()
        calls = {"n": 0}

        def fake_connect():
            calls["n"] += 1
            if calls["n"] >= 5:
                stop.set()  # 重试数次后置位停止: 验证循环仍即时退出
            return False

        mgr.connect = fake_connect
        with capture_logs("auto_qb.core.qbmanager", level=logging.WARNING) as cap:
            mgr.run(dry_run=False, stop_event=stop)  # 不抛即通过(停止即时响应)
        warns = [m for m in cap.messages if "重试" in m]
        assert len(warns) == 1, f"重试 WARNING 只说明白一次, 实际 {len(warns)} 条"
        assert calls["n"] >= 5


def test_p2a_run_materializes_schema_migration_dry_run_then_write():
    """run() 启动物化: dry-run 只探测不落盘(425); 非 dry-run 迁移+备份落盘(427)"""
    from auto_qb.config import load_config

    legacy = LEGACY_V1
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
            assert "schema_version: 5" in f.read(), "磁盘应落当前版本章"
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


# ==================================================================
# W6(R30) S5 补测第二块(qbmanager 变异审计守阵): 以下用例按簇整族杀变异
# ==================================================================


def test_w6_wait_next_waits_full_timeout():
    """守阵(W6, 中): _wait_next 必须睡满 timeout 再返回

    deadline 排进过去 / while False / remaining<=1 三类变异都把等待归零 —— 托管模式
    主循环变 CPU 空转(_throttle 2026-09-14 回归同型, 请求/CPU 放大面)。
    """
    stop = threading.Event()
    wake = threading.Event()
    t0 = time.monotonic()
    ret = _wait_next(stop, wake, 0.3)
    elapsed = time.monotonic() - t0
    assert ret is False, "未收到停止信号必须返回 False(不是 None/True)"
    assert elapsed >= 0.25, f"必须睡满 timeout 再返回(等待归零=空转回归): {elapsed:.3f}s"
    assert elapsed <= 1.5, f"不得超时过久(分段轮询粒度 0.5s): {elapsed:.3f}s"


def test_w6_init_signature_and_field_contracts():
    """守阵(W6, 极低/契约面): 构造与入口签名默认值 + 构造期字段初始值契约

    no_lock/dry_run 默认翻 True 会把缺省调用变成"跳过锁/静默 dry-run"; QbApi 不带 store、
    next_flush_at 初值漂移、_pause_event 非 None 都是仅契约面可区分的极低危。
    """
    import inspect

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        sig = inspect.signature(QbManager.__init__)
        assert sig.parameters["no_lock"].default is False, "no_lock 缺省必须 False(锁是保守默认)"
        rsig = inspect.signature(QbManager.run)
        assert rsig.parameters["dry_run"].default is False, "run 的 dry_run 缺省必须 False(真写是默认语义)"
        fsig = inspect.signature(QbManager._refresh_torrents)
        assert fsig.parameters["dry_run"].default is False, "_refresh_torrents 的 dry_run 缺省必须 False"
        assert mgr.api.store is mgr.store, "QbApi 必须在构造期绑定 store"
        assert mgr.ctx.state.next_flush_at == 0.0, "周期落盘到期点初值 0.0(run() 会重置)"
        assert mgr._pause_event is None, "_pause_event 构造期必须为 None(run() 注入前无暂停态)"


def test_w6_init_loads_config_from_path():
    """守阵(W6, 中): config 未传时必须以 config_path 调 load_config(open(None) 即构造崩溃)"""
    with tempfile.TemporaryDirectory() as td:
        cfg = FakeConfig()
        cfg.state_file = os.path.join(td, "state.json")
        with mock.patch("auto_qb.core.qbmanager.load_config", return_value=cfg) as lc:
            make_manager(cfg=cfg, pass_config_none=True, qb_config_path=os.path.join(td, "config.yml"))
        lc.assert_called_once_with(os.path.join(td, "config.yml"))


def test_w6_init_wires_fs_notify_relocate():
    """守阵(W6, 中/低): fs.path_map 必须产出 MappedFileAccess; notify/relocate 模块必须挂真 ctx

    init_file_access(None) 让映射静默整体退回 Local(缺文件扫描/搬家的路径面);
    NotifyModule/RelocateModule(None) 后写路径读 _ctx 即 AttributeError(可选特性面)。
    """
    with tempfile.TemporaryDirectory() as td:
        cfg = FakeConfig()
        cfg.state_file = os.path.join(td, "state.json")
        cfg.fs = FsConfig(path_map=(PathMapEntry(src="R:/Downloads", dst="/downloads"), ))
        mgr = make_manager(cfg=cfg)
        fa = file_access.get_file_access()
        assert isinstance(fa, MappedFileAccess), "fs.path_map 配置必须产出 MappedFileAccess(退回 Local=映射整体失效)"
        assert fa.entries == cfg.fs.path_map, "映射表必须原样进访问层"
        assert mgr.ctx.notify._ctx is mgr.ctx, "NotifyModule 必须挂真 ctx"
        assert mgr.ctx.relocate._ctx is mgr.ctx, "RelocateModule 必须挂真 ctx"


def test_w6_init_creates_state_dir_console_only():
    """守阵(W6, 中): 构造必须显式建数据目录(console-only 无日志文件代建, 不建则首次落盘崩)"""
    with tempfile.TemporaryDirectory() as td:
        sub = os.path.join(td, "statedir")
        make_manager(os.path.join(sub, "state.json"))
        assert os.path.isdir(sub), "数据目录必须在构造期创建(console-only 时无日志代建兜底)"


def test_w6_connect_false_on_api_connection_error():
    """守阵(W6, 中): APIConnectionError 分支必须报 False(True 会破非托管 fail-fast 契约)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        with mock.patch("auto_qb.core.qbmanager.new_client", side_effect=APIConnectionError("conn refused")):
            assert mgr.connect() is False, "连接失败报成功=主循环无客户端带病运行"
        assert mgr.client is None


def test_w6_connect_error_detail_logged():
    """守阵(W6, 低): 两个连接失败分支的 ERROR 都必须带异常详情(丢 None=审计丢真)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        with mock.patch("auto_qb.core.qbmanager.new_client", side_effect=APIConnectionError("boom-net")):
            with capture_logs("auto_qb.core.qbmanager") as cap:
                mgr.connect()
        assert any("boom-net" in m for m in cap.messages), "APIConnectionError 分支 ERROR 必须带详情"
        mgr._last_conn_ok = None  # 复位转换节流(断开期间静默是另一条纪律)
        with mock.patch("auto_qb.core.qbmanager.new_client", side_effect=Exception("boom-cred")):
            with capture_logs("auto_qb.core.qbmanager") as cap2:
                mgr.connect()
        assert any("boom-cred" in m for m in cap2.messages), "通用异常分支 ERROR 必须带详情"


def test_w6_pause_branch_keeps_looping():
    """守阵(W6, 中/低): 暂停分支等待实参契约 + 暂停不退化为停机(continue) + 停止 INFO

    _wait_next 实参错位/缺参 → TypeError 即崩; continue→break 让暂停语义退化为停机;
    _pause_event 未挂载则状态快照 paused 恒 False。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=True)
        mgr.config.main_tick = 0.1
        mgr.config.sync_interval = 0.1
        pause = threading.Event()
        pause.set()
        stop = threading.Event()
        real_wait = _qbm._wait_next
        calls = []
        pause_seen = []

        def spy(stop_event, wake_event, timeout):
            calls.append((stop_event, wake_event, timeout))
            pause_seen.append(mgr._pause_event is pause)
            if len(calls) >= 3:
                stop_event.set()
            return real_wait(stop_event, wake_event, timeout)

        with mock.patch.object(_qbm, "_wait_next", spy):
            with capture_logs("auto_qb.core.qbmanager") as cap:
                mgr.run(dry_run=False, stop_event=stop, pause_event=pause)
        assert len(calls) == 3, f"暂停期间主循环必须继续轮询(continue 语义), 实际 {len(calls)} 次"
        assert all(se is stop for se, _, _ in calls), "暂停等待必须传 stop_event"
        assert all(we is mgr._wake_event for _, we, _ in calls), "暂停等待必须传唤醒事件"
        assert all(t == 0.1 for *_, t in calls), "暂停等待超时 = main_tick"
        assert all(pause_seen), "run() 必须把 pause_event 挂到 _pause_event(状态快照依赖)"
        assert "收到停止信号, 退出主循环" in cap.text, "暂停分支停止 INFO 不得丢"


def test_w6_next_flush_at_respects_save_interval():
    """守阵(W6, 中/低): 周期落盘到期点 = now+max(interval, 0.0)

    interval=0(显式关闭)被强转 1s = 关闭语义反转(保守默认面); +max 变 -max = 到期点排进
    过去, 启动即冗余写一次。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=True)
        mgr.config.state_save_interval = 0  # 显式关闭周期落盘
        stop = threading.Event()
        stop.set()
        mgr.run(dry_run=False, stop_event=stop)
        assert mgr.ctx.state.next_flush_at <= time.time() + 0.5, "state_save_interval=0 必须保持 0 间隔(不得强转 1s 周期写盘)"

        mgr2 = make_manager(os.path.join(td, "state2.json"))
        mgr2.connect = mock.Mock(return_value=True)
        mgr2.config.state_save_interval = 30.0
        stop2 = threading.Event()
        stop2.set()
        mgr2.run(dry_run=False, stop_event=stop2)
        assert mgr2.ctx.state.next_flush_at >= time.time() + 25, "到期点必须排向未来 now+interval(排进过去=启动即冗余写)"


def test_w6_task_line_receives_dry_run():
    """守阵(W6, 中): 任务线分派必须传 dry_run 位置实参(丢参 = 每轮 TypeError 退避环)且真值等待轮 force=True

    elif tick_due 分派点: dry_run 缺参即 TypeError; force 丢失/None 化 = 表现层收尾门控失效
    (真值等待轮必须绕"上一版是否被取走"门控)。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=True)
        mgr.config.main_tick = 0.05
        mgr.config.sync_interval = 5.0
        mgr.web.truth_pending = {"c1": {"cmd": "pause", "args": {"hashes": ["H1"]}, "ts": time.time()}}
        mgr.web.flush_truths = lambda: None  # 真值恒未落地: 每轮 cmd_forced=True
        stop = threading.Event()
        timer = _daemon_timer(4.0, stop.set)
        task_calls = []
        sync_calls = []

        def task_line(dry_run, force=False):
            task_calls.append((dry_run, force))
            if len(task_calls) >= 2:
                stop.set()

        def sync_line(dry_run, flush=True, force=False):
            sync_calls.append(dry_run)

        mgr._task_line = task_line
        mgr._sync_line = sync_line
        with capture_logs("auto_qb.core.qbmanager") as cap:
            mgr.run(dry_run=False, stop_event=stop)
        timer.cancel()
        assert task_calls == [(False, True), (False, True)], f"任务线必须收到 dry_run 位置实参且 force=True: {task_calls}"
        assert not [r for r in cap.records if r.levelname == "ERROR"], \
            "任务线分派不得抛 TypeError 缺参进退避环(主循环异常 ERROR 即红)"


def test_w6_periodic_flush_gate_and_migration_arg():
    """守阵(W6, 中/低): 周期落盘挂在 not dry_run 门内(反转=正常轮全停) + materialize_migration 实参"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=True)
        mgr._sync_line = lambda dry_run, flush=True, force=False: None
        mgr._task_line = lambda dry_run, force=False: None
        stop = threading.Event()
        timer = _daemon_timer(3.0, stop.set)
        flush_calls = []
        mgr.ctx.state.materialize_migration = mock.Mock()

        def maybe_flush(now, interval):
            flush_calls.append((now, interval))
            stop.set()

        mgr.ctx.state.maybe_flush = maybe_flush
        mgr.run(dry_run=False, stop_event=stop)
        timer.cancel()
        assert len(flush_calls) == 1, "非 dry-run 轮必须走周期落盘(gate 反转=状态丢失窗口回归)"
        assert mgr.ctx.state.materialize_migration.call_args == mock.call(
            False
        ), "materialize_migration 必须收到 dry_run 实参(None≠False, 变异后 dry-run 会话也落盘)"

        mgr2 = make_manager(os.path.join(td, "state2.json"))
        mgr2.connect = mock.Mock(return_value=True)
        mgr2._sync_line = lambda dry_run, flush=True, force=False: None
        mgr2._task_line = lambda dry_run, force=False: None
        stop2 = threading.Event()
        timer2 = _daemon_timer(2.0, stop2.set)
        flush2 = []
        mgr2.ctx.state.maybe_flush = lambda *a, **k: flush2.append(a)
        mgr2.run(dry_run=True, stop_event=stop2)
        timer2.cancel()
        assert flush2 == [], "dry-run 会话不得周期落盘"


def test_w6_truth_pending_drives_retry_arc():
    """守阵(W6, 中/低): 真值未落地(pending 常驻)必须按 0.2s 重试弧持续补同步, 且各线 force=True

    重试弧断(属性名/求值变异)→ 真值落地等满 sync_interval; cmd_forced/_tick/_sync_line 的
    force/dry_run 实参契约同轮锁定; 弧内 next_sync_at=None 会在下拍 now>=None TypeError 崩溃。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=True)
        mgr.config.main_tick = 0.5
        mgr.config.sync_interval = 5.0
        mgr.web.truth_pending = {"c1": {"cmd": "pause", "args": {"hashes": ["H1"]}, "ts": time.time()}}
        mgr.web.flush_truths = lambda: None  # 真值恒未落地: pending 常驻
        stop = threading.Event()
        timer = _daemon_timer(1.8, stop.set)
        tick_calls, sync_calls = [], []

        def tick(dry_run, force=False):
            tick_calls.append((dry_run, force))

        def sync_line(dry_run, flush=True, force=False):
            sync_calls.append((dry_run, flush, force))

        mgr._tick = tick
        mgr._sync_line = sync_line
        with capture_logs("auto_qb.core.qbmanager") as cap:
            mgr.run(dry_run=False, stop_event=stop)
        timer.cancel()
        assert tick_calls == [(False, True)], f"真值等待轮 _tick force 必须为 True: {tick_calls}"
        assert len(sync_calls) >= 3, f"真值未落地必须按 0.2s 重试弧持续补同步: {len(sync_calls)} 次"
        assert all(f is True for _, _, f in sync_calls), "重试弧同步线 force 必须为 True"
        assert all(d is False for d, _, _ in sync_calls), "同步线 dry_run 实参不得为 None"
        assert all(fl is True for _, fl, _ in sync_calls), "独立同步线 flush 必须保持开启"
        assert "收到停止信号, 退出主循环" in cap.text, "主循环停止 INFO 不得丢"


def test_w6_truth_pending_one_shot_no_extra_sync():
    """守阵(W6, 低): 真值已落地(flush 清空 pending)后不得继续 0.2s 重试弧(and 不得退化成 or)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=True)
        mgr.config.main_tick = 5.0
        mgr.config.sync_interval = 5.0
        mgr.web.truth_pending = {"c1": {"cmd": "pause", "args": {"hashes": ["H1"]}, "ts": time.time()}}

        def drain_once():
            mgr.web.truth_pending = {}

        mgr.web.flush_truths = drain_once
        stop = threading.Event()
        timer = _daemon_timer(1.5, stop.set)
        sync_calls = []
        mgr._sync_line = lambda dry_run, flush=True, force=False: sync_calls.append(dry_run)
        mgr._task_line = lambda dry_run, force=False: None
        mgr.run(dry_run=False, stop_event=stop)
        timer.cancel()
        assert len(sync_calls) == 1, f"真值落地后不得继续重试弧(and 退化成 or = 0.2s 白刷): {len(sync_calls)} 次"


def test_w6_cmd_forced_and_t_line_contract():
    """守阵(W6, 低): cmd_forced 门控契约(命令轮 True/非命令轮 False) + 命令线计时弧恰发一次

    force 门控反转 → 每轮绕"上一版是否被取走"门控(视图强制重建放大); _t_line 计时弧
    反转/恒真/else 1.0 → 遥测噪声或丢真。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=True)
        mgr.config.main_tick = 0.05
        mgr.config.sync_interval = 5.0
        n = {"c": 0}

        def fake_cmd():
            n["c"] += 1
            return n["c"] == 1  # 仅首轮有命令

        mgr.host.run_command_line = fake_cmd
        resync = []
        mgr.web.resync_elapsed_ms = lambda t0: resync.append(t0)
        stop = threading.Event()
        timer = _daemon_timer(4.0, stop.set)
        task_calls = []
        sync_calls = []

        def task_line(dry_run, force=False):
            task_calls.append((dry_run, force))
            if len(task_calls) >= 4:
                stop.set()

        def sync_line(dry_run, flush=True, force=False):
            sync_calls.append((dry_run, flush, force))

        mgr._task_line = task_line
        mgr._sync_line = sync_line
        mgr.run(dry_run=False, stop_event=stop)
        timer.cancel()
        assert task_calls == [(False, True), (False, False), (False, False), (False, False)], \
            f"命令轮 force=True, 非命令轮必须 False: {task_calls}"
        assert len(resync) == 1, f"命令线计时弧必须在命令轮恰发一次: {len(resync)} 次"
        assert isinstance(resync[0], float) and resync[0] > 0, "计时弧实参必须是真实时间戳"
        assert sync_calls == [(False, False, False)] * 4, f"每轮双线合轮经 _tick(压 flush): {sync_calls}"


def test_w6_micro_deadline_merged_into_wait():
    """守阵(W6, 中): 微步到期必须并入等待超时(退化=跳检步进从 10~50ms 劣化到 main_tick)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=True)
        mgr.config.main_tick = 2.0
        mgr.config.sync_interval = 5.0
        mgr.host.next_micro_run_at = lambda: time.time() + 0.05
        stop = threading.Event()
        timer = _daemon_timer(5.0, stop.set)
        micro = []

        def micro_line(dry_run):
            micro.append(dry_run)
            if len(micro) >= 5:
                stop.set()

        mgr.host.run_micro_line = micro_line
        mgr._sync_line = lambda dry_run, flush=True, force=False: None
        mgr._task_line = lambda dry_run, force=False: None
        mgr.run(dry_run=False, stop_event=stop)
        timer.cancel()
        assert len(micro) == 5, f"微步到期必须并入等待超时(按 0.05s 节拍推进): 实际 {len(micro)} 步"
        assert all(d is False for d in micro), "微步线 dry_run 实参不得为 None"


def test_w6_micro_deadline_does_not_delay_lines():
    """守阵(W6, 中): 更晚的微步到期不得推迟同步/任务线(min 压缩变异=min(单参))"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=True)
        mgr.config.main_tick = 2.0
        mgr.config.sync_interval = 0.1
        mgr.host.next_micro_run_at = lambda: time.time() + 1.0  # 微步退避晚于同步线
        stop = threading.Event()
        timer = _daemon_timer(0.8, stop.set)
        sync_calls = []
        mgr._sync_line = lambda dry_run, flush=True, force=False: sync_calls.append(dry_run)
        mgr._task_line = lambda dry_run, force=False: None
        mgr.run(dry_run=False, stop_event=stop)
        timer.cancel()
        assert len(sync_calls) >= 4, f"同步线节拍不得被更晚的微步到期推迟: {len(sync_calls)} 次"


def test_w6_flush_fallback_once_per_round():
    """守阵(W6, 低): 回执 flush 每轮恰一次 —— 异常轮走兜底、正常轮不重复(_flushed 旗标契约)

    旗标恒真 → 异常轮不补回执(waitCmd 干等); 旗标恒假/None → 正常轮双 flush;
    兜底判据反转 → 轮归属错乱。KI 退出必须落"停止" INFO。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=True)
        mgr.config.main_tick = 0.05
        mgr.config.sync_interval = 0.05
        mgr._refresh_torrents = mock.Mock(side_effect=[None, RuntimeError("refresh boom")])
        mgr.web.flush_truths = mock.Mock(side_effect=[None, KeyboardInterrupt()])
        with capture_logs("auto_qb.core.qbmanager") as cap:
            mgr.run(dry_run=False)
        assert mgr._refresh_torrents.call_count == 2, "两轮: 正常轮 + 异常轮"
        assert mgr.web.flush_truths.call_count == 2, "每轮恰一次回执 flush(异常轮兜底补, 正常轮不双发)"
        assert "停止" in cap.text, "KeyboardInterrupt 退出必须落'停止' INFO"


def test_w6_conn_recovery_flag_flip():
    """守阵(W6, 低): 线跑通后连接状态必须翻回已连接(is False 门反转/改 True = UI 永显断开)

    connect 替身与真实现同构(成功即落非 None client, 见 pitfalls/testing/manager-connect-stub.md):
    否则断连稳态守卫(client is None + _last_conn_ok is False)命中, 请求线整段被跳过, 本用例
    测的就不再是「线跑通后翻转」而是守卫轮。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))

        def fake_connect():
            mgr.client = mock.Mock()
            return True

        mgr.connect = fake_connect
        mgr._last_conn_ok = False  # 断开态进入主循环
        mgr.config.main_tick = 0.05
        mgr.config.sync_interval = 0.05
        stop = threading.Event()
        timer = _daemon_timer(3.0, stop.set)
        mgr._sync_line = lambda dry_run, flush=True, force=False: None

        def task_line(dry_run, force=False):
            stop.set()

        mgr._task_line = task_line
        mgr.run(dry_run=False, stop_event=stop)
        timer.cancel()
        assert mgr._last_conn_ok is True, "线跑通后必须 _note_conn_ok(否则 UI 永显断开)"


def test_w6_conn_failed_error_detail():
    """守阵(W6, 低): 主循环断连 ERROR 必须带异常详情(丢 None=审计丢真)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=True)
        mgr._tick = mock.Mock(side_effect=APIConnectionError("detail-net-down"))
        mgr.config.main_tick = 0.05
        stop = threading.Event()
        timer = _daemon_timer(0.8, stop.set)
        with capture_logs("auto_qb.core.qbmanager") as cap:
            mgr.run(dry_run=False, stop_event=stop)
        timer.cancel()
        assert any("detail-net-down" in m for m in cap.messages), "断连 ERROR 必须带异常详情"


def test_w6_stopiteration_error_detail():
    """守阵(W6, 低): StopIteration ERROR 的消息与堆栈不得丢真(仍重抛不变)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=True)
        mgr._tick = mock.Mock(side_effect=StopIteration("gen-misuse-marker"))
        with capture_logs("auto_qb.core.qbmanager") as cap:
            with pytest.raises(StopIteration):
                mgr.run(dry_run=False)
        errs = [r for r in cap.records if r.levelname == "ERROR"]
        assert errs and "gen-misuse-marker" in errs[-1].getMessage(), "StopIteration ERROR 必须带异常详情"
        assert errs[-1].exc_info, "StopIteration ERROR 必须带堆栈(exc_info=None/False 均丢真)"


def test_w6_generic_exception_error_detail():
    """守阵(W6, 低): 主循环异常 ERROR 的消息与堆栈不得丢真"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.connect = mock.Mock(return_value=True)
        mgr.config.main_tick = 0.05
        mgr._tick = mock.Mock(side_effect=[RuntimeError("boom-marker"), KeyboardInterrupt()])
        with capture_logs("auto_qb.core.qbmanager") as cap:
            mgr.run(dry_run=False)
        errs = [r for r in cap.records if r.levelname == "ERROR" and "主循环异常" in r.getMessage()]
        assert errs and "boom-marker" in errs[-1].getMessage(), "主循环异常 ERROR 必须带异常详情"
        assert errs[-1].exc_info, "主循环异常 ERROR 必须带堆栈(exc_info=None/False 均丢真)"


def test_w6_migration_and_start_stop_logs():
    """守阵(W6, 低): 迁移/启动/停止 INFO 审计面 + desc 空时不得打迁移日志(or 反转恒打"落后(None)")"""
    with tempfile.TemporaryDirectory() as td:
        with mock.patch("auto_qb.core.qbmanager.materialize_schema_migration", return_value=("desc-v2", "bak")):
            mgr = make_manager(os.path.join(td, "state.json"))
            mgr.connect = mock.Mock(return_value=True)
            mgr.ctx.state.materialize_migration = mock.Mock()
            stop = threading.Event()
            stop.set()
            with capture_logs("auto_qb.core.qbmanager") as cap:
                mgr.run(dry_run=True, stop_event=stop)
            assert "dry-run 仅内存生效" in cap.text, "dry-run 迁移提示 INFO 不得丢"
            assert "启动 qB 管理器" in cap.text, "启动 INFO 不得丢"
            assert "收到停止信号, 退出主循环" in cap.text, "停止 INFO 不得丢"
            assert mgr.ctx.state.materialize_migration.call_args == mock.call(True)

        with mock.patch("auto_qb.core.qbmanager.materialize_schema_migration", return_value=("", None)):
            mgr2 = make_manager(os.path.join(td, "state2.json"))
            mgr2.connect = mock.Mock(return_value=True)
            stop2 = threading.Event()
            stop2.set()
            with capture_logs("auto_qb.core.qbmanager") as cap2:
                mgr2.run(dry_run=True, stop_event=stop2)
            assert "schema 落后" not in cap2.text, "无迁移时不得打迁移 INFO"

        with mock.patch("auto_qb.core.qbmanager.materialize_schema_migration", return_value=("desc-v3", "bak3")):
            mgr3 = make_manager(os.path.join(td, "state3.json"))
            mgr3.connect = mock.Mock(return_value=True)
            stop3 = threading.Event()
            stop3.set()
            with capture_logs("auto_qb.core.qbmanager") as cap3:
                mgr3.run(dry_run=False, stop_event=stop3)
            assert "已迁移" in cap3.text and "desc-v3" in cap3.text, "已迁移 INFO 不得丢"


def test_w6_apply_new_config_contract():
    """守阵(W6, 中/低): 热重载回执契约 + qbittorrent 段变重连(双向) + 完成 INFO 汇总过滤"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.reconnect = mock.Mock()
        mgr.host.apply_all = mock.Mock(return_value=[ApplyResult("alpha", "reloaded", "ok"), ApplyResult("beta")])
        cfg2 = FakeConfig()
        # 与现配置共享可变段(FakeTracker 无 __eq__, 身份比较会误判为变更), 只改 qbittorrent 段
        cfg2.trackers = mgr.config.trackers
        cfg2.rules_config = mgr.config.rules_config
        cfg2.state_file = mgr.config.state_file
        cfg2.qbittorrent = QbittorrentConfig(host="127.0.0.1", port=16586, username="u", **{"pass" + "word": "p"})
        with capture_logs("auto_qb.core.qbmanager") as cap:
            result = mgr.apply_new_config(cfg2)
        assert result["applied"] is True
        assert set(result) == {"applied", "actions", "changes", "restart_required"}, f"回执键面契约: {set(result)}"
        assert result["changes"] == 1
        assert result["restart_required"] == []
        assert result["actions"] == [
            {
                "module": "alpha",
                "action": "reloaded",
                "detail": "ok"
            },
            {
                "module": "beta",
                "action": "none",
                "detail": ""
            },
        ], f"回执条目契约: {result['actions']}"
        assert mgr.reconnect.call_count == 1, "qbittorrent 段变必须重连"
        text = cap.text
        assert "配置热重载完成" in text, "完成 INFO 不得丢"
        assert "alpha:reloaded" in text, "完成 INFO 必须列真实动作"
        assert "beta:none" not in text, "no-op 动作不得混入汇总"
        assert "需重启进程" not in text, "无重启项不得误报需重启"
        assert "XXXX" not in text, "非重启轮不得拼噪声后缀"
        # 段相同: 不得重连(== 反转会在段同时重连)
        mgr.host.apply_all = mock.Mock(return_value=[])
        mgr.apply_new_config(cfg2)
        assert mgr.reconnect.call_count == 1, "qbittorrent 段相同不得重连"


def test_w6_apply_new_config_restart_gate():
    """守阵(W6, 中/低): R 级闸必须返回需重启段(None=闸失效照常热应用)且日志保留提示"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.reconnect = mock.Mock()
        mgr.host.apply_all = mock.Mock(return_value=[ApplyResult("alpha")])
        cfg2 = FakeConfig()
        cfg2.state_file = os.path.join(td, "other.json")
        with capture_logs("auto_qb.core.qbmanager") as cap:
            result = mgr.apply_new_config(cfg2)
        assert result["restart_required"] == ["state_file"], "R 级闸(state_file 变更)必须进需重启回执"
        assert "需重启进程才能生效" in cap.text, "需重启 INFO 不得丢"
        assert "需重启进程: ['state_file']" in cap.text, "完成 INFO 必须带需重启后缀"


def test_w6_apply_new_config_unclaimed_fallback():
    """守阵(W6, 中/低): 未认领段兜底 —— WARNING + rebuild_runtime 相位载荷 + 回执条目逐字契约

    相位失联/载荷缺失 → 兜底重建静默失效; join(None) 直接崩; 回执条目字段/值变异即损坏。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.reconnect = mock.Mock()
        mgr.host.apply_all = mock.Mock(return_value=[ApplyResult("alpha", "reloaded", "ok")])
        rebuilds = []
        mgr.events.on("rebuild_runtime", lambda event: rebuilds.append((event.phase, event.payload)))
        cfg2 = FakeConfig()
        # 与现配置共享可变段(FakeTracker 无 __eq__), 只动未认领段 —— 两段才能观察 join 分隔符
        cfg2.trackers = mgr.config.trackers
        cfg2.rules_config = mgr.config.rules_config
        cfg2.state_file = mgr.config.state_file
        cfg2.check_missing_files = True  # 无模块认领的顶层段
        cfg2.custom_unknown_section = {"probe": 1}  # 仅存在于新配置的幽灵段(同样无认领)
        with capture_logs("auto_qb.core.qbmanager") as cap:
            result = mgr.apply_new_config(cfg2)
        assert "check_missing_files" in cap.text and "未被任何模块认领" in cap.text, "未认领段 WARNING 不得丢"
        assert rebuilds == [("rebuild_runtime", {"sections": ["check_missing_files", "custom_unknown_section"]})], \
            f"兜底重建必须广播 rebuild_runtime 相位并带未认领段: {rebuilds}"
        assert result["actions"][-1] == {
            "module": "kernel",
            "action": "rebuild_fallback",
            "detail": "未认领段: check_missing_files, custom_unknown_section",
        }, f"兜底回执条目契约: {result['actions'][-1]}"


def test_w6_sync_line_contract():
    """守阵(W6, 中/低): 同步线默认 flush 开/force 关, dry_run 直传刷新(生产调用不传 flush)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr._refresh_torrents = mock.Mock()
        mgr.host.run_sync_line = mock.Mock()
        mgr._sync_line(False)
        assert mgr._refresh_torrents.call_args == mock.call(False), "同步线必须把 dry_run 原样传刷新(None≈False=dry-run 真写)"
        mgr.host.run_sync_line.assert_called_once_with(False), "flush 缺省必须收尾 on_sync_line 且 force=False"
        mgr._sync_line(False, flush=False)
        assert mgr.host.run_sync_line.call_count == 1, "flush=False 不收尾"


def test_w6_task_line_contract():
    """守阵(W6, 中/低): 任务线 run_due 实参契约(defer_gate 身份直传) + 收尾 force 默认 False"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.task_queue.run_due = mock.Mock()
        mgr.host.run_task_line = mock.Mock()
        mgr._task_line(True)
        call = mgr.task_queue.run_due.call_args
        assert call.args == (True, ), f"run_due 必须收到 dry_run 位置实参: {call}"
        assert call.kwargs["defer_gate"] == mgr._own_write_defer_gate, "defer_gate 必须接到队列级闸门(None=闸失效)"
        assert call.kwargs["max_tasks"] == mgr.config.max_tasks_per_tick
        mgr.host.run_task_line.assert_called_once_with(False), "收尾 force 缺省 False 且不得为 None"


def test_w6_tick_contract():
    """守阵(W6, 低): _tick 双线合轮实参契约 —— sync 收 flush=False, task 直传 force"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr._sync_line = mock.Mock()
        mgr._task_line = mock.Mock()
        mgr._tick(True, force=True)
        mgr._sync_line.assert_called_once_with(True, flush=False), "_tick 合轮必须压 flush(视图只重建一次)"
        mgr._task_line.assert_called_once_with(True, force=True), "_tick 必须把 force 直传任务线"


def test_w6_refresh_transitions_phase_payload():
    """守阵(W6, 中/低): transitions 相位与载荷逐字契约(相位失联/载荷键变异即红)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
        mgr.config.trackers = {}
        seen = []
        mgr.events.on("transitions", lambda event: seen.append((event.phase, event.payload)))
        mgr._refresh_torrents(False)
        assert seen == [("transitions", {"dry_run": False})], f"transitions 相位与载荷契约: {seen}"


def test_w6_refresh_events_removed_and_scan_phase():
    """守阵(W6, 中/低): events_removed/removed_scan 相位载荷契约(含删除前快照留档)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1", save_path="R:/Downloads/T1")
        mgr._refresh_torrents(False)  # 首轮: 种子入库
        tor = mgr.store.get("H1")
        removed_seen, scan_seen = [], []
        mgr.events.on("events_removed", lambda e: removed_seen.append((e.phase, e.payload)))
        mgr.events.on("removed_scan", lambda e: scan_seen.append((e.phase, e.payload)))
        del client.torrents["H1"]
        with capture_logs("auto_qb.core.qbmanager") as cap:
            mgr._refresh_torrents(False)
        assert len(removed_seen) == 1, f"events_removed 必须派发: {removed_seen}"
        phase, payload = removed_seen[0]
        assert phase == "events_removed"
        assert payload["removed"] == ["H1"], "删除清单键/值契约"
        assert payload["snapshots"]["H1"] is tor, "删除前快照必须带原记录对象(留档面)"
        assert set(payload) == {"removed", "snapshots", "dry_run"}, f"events_removed 载荷键面: {set(payload)}"
        assert scan_seen == [("removed_scan", {"hashes": ["H1"], "dry_run": False})], f"removed_scan 载荷契约: {scan_seen}"
        assert "检测到删除种子 1 个" in cap.text, "删除 INFO 不得丢"


def test_w6_refresh_suppression_window_opens():
    """守阵(W6, 中): 抑制请求位必须真正开窗 —— 窗口内两事件相位不派发(不开窗=热重载首轮全库重放)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
        mgr.config.trackers = {}
        events_seen = []
        mgr.events.on("events_removed", lambda e: events_seen.append(e.phase))
        mgr.events.on("events_added", lambda e: events_seen.append(e.phase))
        trans_seen = []
        mgr.events.on("transitions", lambda e: trans_seen.append(e.phase))
        mgr.events.request_suppression()
        mgr._refresh_torrents(False)
        assert events_seen == [], "抑制窗口内 events_removed/events_added 不得派发"
        assert trans_seen, "transitions 不受抑制窗口影响(仅两事件相位)"
        assert not mgr.events.suppressed, "窗口必须在 finally 关闭(不残留)"


def test_w6_refresh_events_added_phase_payload():
    """守阵(W6, 中/低): events_added 相位与载荷契约(相位失联=事件规则不触发)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.torrents["U1"] = FakeTorrent(hash="U1", name="T1")
        seen = []
        mgr.events.on("events_added", lambda e: seen.append((e.phase, e.payload)))
        mgr._refresh_torrents(False)
        assert seen == [("events_added", {"added": ["U1"], "dry_run": False})], f"events_added 载荷契约: {seen}"


def test_w6_refresh_torrents_added_phase_payload():
    """守阵(W6, 低): torrents_added 逐种子相位载荷契约"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.torrents["U1"] = FakeTorrent(hash="U1", name="T1")
        seen = []
        mgr.events.on("torrents_added", lambda e: seen.append((e.phase, e.payload)))
        mgr._refresh_torrents(False)
        assert seen == [("torrents_added", {"hash": "U1", "dry_run": False})], f"torrents_added 载荷契约: {seen}"


def test_w6_refresh_post_phase_payload():
    """守阵(W6, 中/低): post 相位载荷契约(收尾重归组/冲突检查的判据面)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
        seen = []
        mgr.events.on("post", lambda e: seen.append((e.phase, e.payload)))
        mgr._refresh_torrents(False)
        assert seen == [("post", {"dry_run": False})], f"post 载荷契约: {seen}"


def test_w6_refresh_matching_loop_continues_past_skips():
    """守阵(W6, 中): 匹配循环跳过(幽灵/未匹配)不得截断后续种子(continue→break 家族)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        client.trackers_map["H1"] = [{"url": "http://unknown.example.com/announce"}]  # H1 匹配不到
        mgr.client = client
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
        mgr._refresh_torrents(False)  # H1 入库但未匹配
        # 第二轮新增: 幽灵(hash 缺快照) + 未匹配(H9) + 可匹配(H2, 默认 hhanclub URL) —— 排序覆盖两类 break
        client.trackers_map["H9"] = [{"url": "http://unknown2.example.com/announce"}]
        client.torrents["HGHOST"] = FakeTorrent(hash="HGHOST", name="G")
        client.torrents["H9"] = FakeTorrent(hash="H9", name="T9")
        client.torrents["H2"] = FakeTorrent(hash="H2", name="T2")
        orig_get = mgr.store.get

        def ghost_get(h):
            return None if h == "HGHOST" else orig_get(h)

        added_seen = []
        mgr.events.on("events_added", lambda e: added_seen.append(e.payload.get("added")))
        with mock.patch.object(mgr.store, "get", side_effect=ghost_get):
            mgr._refresh_torrents(False)
        assert added_seen and added_seen[-1] == ["H2"], \
            f"匹配循环跳过后必须继续处理后续种子(幽灵/未匹配不得截断): {added_seen}"


def test_w6_refresh_fs_selfcheck_once():
    """守阵(W6, 中/低): 映射自检一次性闸门 —— 恰好首轮全量跑一次, 实参 = 现存 save_path 清单"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1", save_path="R:/Downloads/T1")
        with mock.patch("auto_qb.infra.file_access.path_map_selfcheck") as sc:
            mgr._refresh_torrents(False)
            mgr.store.rid = 0  # 强制下一轮全量(need_validate 重新置位)
            mgr._refresh_torrents(False)
        assert sc.call_count == 1, f"映射自检必须恰好跑一次(闸门失效=每全量轮重跑): {sc.call_count}"
        assert sc.call_args == mock.call(["R:/Downloads/T1"]), f"自检实参 = save_path 清单(不得为 None): {sc.call_args}"


def test_w6_refresh_search_index_dirty_on_add_only():
    """守阵(W6, 中): 单边新增或单边删除都必须标搜索索引脏(and 收紧=索引陈旧)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        mgr.web.mark_search_index_dirty = mock.Mock()
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
        mgr._refresh_torrents(False)  # 仅新增
        assert mgr.web.mark_search_index_dirty.call_count == 1, "单边新增必须标索引脏"
        mgr.web.mark_search_index_dirty.reset_mock()
        del client.torrents["H1"]
        mgr._refresh_torrents(False)  # 仅删除
        assert mgr.web.mark_search_index_dirty.call_count == 1, "单边删除必须标索引脏"


def test_w6_refresh_added_logging_domains():
    """守阵(W6, 低): 新增 INFO/未匹配 WARNING 审计面 + 诊断域名来自**本次** tracker 拉取

    trackers_info 实参变异(trackers_info(None)/=None/extract(None))必须让域名清单丢失;
    match 桩掉避免它先拉一次 tracker 把记录级缓存焐热(热缓存会掩盖实参变异)。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.config.trackers = {}  # 全部匹配不到
        mgr.ctx.trackers.match = mock.Mock(return_value=None)  # 不预热记录级 trackers 缓存
        client = FakeClient()
        client.torrents_trackers = lambda h: [{"url": "https://tracker.hhanclub.net/announce.php"}]
        mgr.client = client
        client.torrents["U1"] = FakeTorrent(hash="U1", name="T1")
        with capture_logs("auto_qb.core.qbmanager") as cap:
            mgr._refresh_torrents(False)
        assert any("检测到新增种子 1 个" in m for m in cap.messages), "新增 INFO 不得丢"
        warn = [m for m in cap.messages if "未匹配 tracker 配置" in m]
        assert warn, "未匹配 WARNING 不得丢"
        assert any("tracker.hhanclub.net" in m for m in warn), "诊断域名清单必须来自真实 tracker 拉取"


def test_w6_export_torrents_info_pins_utf8_encoding(monkeypatch):
    """守阵(W6, 中, 平台相关): 导出 open 探针钉 encoding="utf-8"(Windows cp936 平台面, 全平台可观测)"""
    import builtins

    real_open = builtins.open
    seen = {}

    def spy(file, mode="r", *args, **kwargs):
        seen[os.fspath(file)] = (mode, kwargs.get("encoding"))
        return real_open(file, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", spy)
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.torrents["H1"] = FakeTorrent(hash="H1", name="T1")
        out = os.path.join(td, "torrents.txt")
        mgr.export_torrents_info(out)
        assert seen[out] == ("w", "utf-8"), f"导出必须显式 encoding=utf-8(Windows cp936 mojibake 面): {seen}"
