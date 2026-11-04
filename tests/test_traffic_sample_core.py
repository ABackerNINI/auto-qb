"""test_traffic_sample_core 测试计划: qB 口径流量采样器(plan 26-10-03-0946 方案C P1 采样器核心 + §06 配置键
+ plan 26-10-04-1957 S2a 写侧/S2b 聚合与恢复 + plan 26-10-05-2200 v4 换代 B2 写侧状态机与结算)

## 测试计划(每个测试函数一条)
- test_sample_task_registered_when_enabled: enabled=true -> **队列零任务** + 时钟线钩子首拍即采(issue 26-10-16-0954)
- test_sample_not_starved_by_immediate_task_backlog: 数百立即到期任务占满队列(重启补建同形)时采样节拍不中断(回归主判据)
- test_sample_clock_line_gate_and_hot_reload_enable: 未到 effective interval 不重复采; 停用零采样零任务; 热重载 enabled=true 不经队列重建即开采
- test_sampling_runs_on_caller_thread: 采样在调用任务线钩子的线程(主循环线程)内同步执行, 模块不建线程(单写线程不变式)
- test_first_sample_only_establishes_baseline: 首个采样只立基线不出增量(首窗 null), 次轮出正常增量
- test_counter_rollback_records_reset_no_negative: 模拟 qB 重启(计数器回落) -> 不产负增量、增量记 null、基线更新为 cur、INFO 记重置
- test_disconnect_produces_null_point: qB 断连(store.client None) -> 全局 n 游程槽 + latest 镜像 null 点、单种本轮不采样、基线不动
- test_missing_fields_produce_null_point_not_zero: server_state 关键字段缺失/空值 -> null 处理(不写 0)且基线不推进
- test_torrent_active_filter_zero_rows_when_idle: 活跃种子照常产 r; 空闲种子零 r(零样本按游程纪律压缩, 从未传输者无游程)
- test_enabled_false_creates_zero_files_or_dirs: enabled=false/键组缺省 -> start+采样全程零文件零目录(保守默认验收)
- test_enabled_true_persists_under_data_dir: enabled=true -> v4 天文件 <data_dir>/qb-traffic-v4/<系列>/<date>.dat
  (头行 v4 + key 行 + B 块头携块基线 + r 行 delta 形态零 dt); 会话快照不落盘
- test_module_contract: name/sections 声明正确且被装配清单认领
- test_flush_driver_interval_and_deferred_first_round: flush 驱动(§3.3) —— 进程首轮只记时不提前 flush;
  now-last_flush >= flush_interval 才批量落盘; v4 带 r 行的块随 flush 关闭(每块头恰一次)
- test_global_idle_run_stays_open_across_flush_and_seals_on_resume: 空闲块不关(v4 §01): 全局空闲开放 z 游程
  跨 flush 滞留内存(N4 天级保险闸, 600s 不再常态触发); 恢复传输(非 z 事件)封口, z 游程成新块首,
  恢复 r 行 delta <= flush 窗 x 速率
- test_torrent_idle_run_snapshot_fixed_at_open: 单种动过->停: z 记录 totals 快照固定在开启时刻
  (两个不同 totals 的零样本不刷新)
- test_never_transferred_torrent_zero_files_runs_entries: 从未传输种子: 零文件零游程(目录判定门 + 缓存)
- test_nonzero_arrival_seals_z_before_raw_same_round: 触发 (1): 非零到达同轮先 z 后 r(buffer 记录序 = 文件序 = 时间序)
- test_disconnect_seals_run_before_null_r2: 触发 (2)(R2): null 到达先封 z 再记 n —— z 覆盖不横跨断连期
- test_zero_run_requires_valid_totals_snapshot: 开 z 游程需 totals 快照: 缺失不开新游程; 已开游程只推进无需重读
- test_global_always_opens_run_vs_torrent_gated: 全局零样本恒开游程(无门) vs 单种数据门拦截(对照)
- test_restart_loses_at_most_one_open_run: 重建 sampler 实例(重启)丢开放游程 <=1(纯零信息), 已落盘块不受影响,
  零样本按纪律重新开游程(重启后首个封口游程成为新块首)
- test_zero_samples_do_not_touch_baselines_or_latest: 零样本不动 baselines/latest(镜像冻结在最后活跃点)
- test_dry_run_no_disk_but_memory_runs_advance: dry_run 零落盘; 缓冲游程内存照常推进, flush 静默跳过写
- test_clock_rollback_clamped_dt_min_1: 时钟回拨单调钳制 dt_ms = max(1, 实测) >= 1
- test_interval_change_hot_reload_new_block_and_effective_interval: 热重载改采样率即时生效(§3.5):
  _effective_interval 更新 + 旧块落盘(旧 interval) + 新块带新 interval(新旧数据分块各有 interval)
- test_interval_mismatch_ceils_and_warns_once: 运行期失配(D5): 向上取整到下一倍数(_effective_interval=取整值) +
  告警一次(防重复), 配置再变记忆复位; 不拒采
- test_interval_decimal_match_kept_not_ceiled: 整数倍匹配的小数档(1.5 配 main_tick=1.5)原样生效 ——
  _effective_interval/块头 B 行均 1.5, 失配告警不触发, 同块零漂移(2026-10-05 修复)
- test_day_boundary_cut: 跨天切块(00:00 硬切, §3.3): 23:59 块落旧日期文件 + 00:00 新块新日期文件, 各带正确块头
- test_day_boundary_seals_open_run: 跨天封游程: 游程不跨天(00:00 样本先封旧游程); 块首单槽游程不写 dt
- test_stop_flushes_all_and_seals_open_runs: stop() 钩子(§3.4): 封全部开放游程 + 全量 flush; 幂等
- test_stop_dry_run_short_circuit: stop() dry_run 短路零落盘

聚合分层与恢复(plan 26-10-04-1957 S2b §04):
- test_agg_hour_degenerate_equal_interval_matches_v2: dt_i ≡ interval_s 时 hour 行与现行 v2
  等间隔均值公式 round(Σrate/n)(v2 纯活跃桶口径, 内联对照)逐列一致, 且等于 v4_hour_agg 标称输入
- test_stop_seals_aggregates_and_dry_run_short_circuit: stop() 聚合封口 —— 完结层级落 agg,
  幂等; dry_run 短路(累计器内存照常推进, 零落盘)

启动恢复按需读集(plan 26-10-12-2010, 读集下界 now - rollup_window -> agg 水位所在日):

v4 定约用例(plan 26-10-05-2200 §04 表 ③⑤⑥⑦, B2 落地):
- test_v4_idle_block_stays_open_single_b_row_and_live_tail_identity: ⑥ 空闲块不关 —— 纯空闲系列
  (数据门有数据 + 零速)主文件零写入, 封口后恰 1 条 B 行 + 1 条长 z 行; 跨 flush 开放 z 游程的
  LiveTail 复原与落盘重算恒等; 恢复传输后 r 行 delta <= flush 窗 x 速率
- test_v4_non_z_seal_midnight_materializes_idle_b_z_batch: ⑦ 非 z 事件封口 —— 长空闲段恰 1 条长 z 行,
  00:00 物化进当日天文件(B + z 一批 append); 次日 LiveTail 开放游程跨天接力与落盘重算恒等
- test_v4_crash_restart_idle_window_is_vacuum: ⑦ 崩溃重启该时段 = 真空 —— 空闲段 cov_s 缺失,
  hour 行 avg 不被零速稀释(无偏)

时钟/落盘纪律: 需要确定时刻的用例经构造期 clock=FakeClock 注入(采样模块经 qbmanager 装配链透传, S3 后不再按模块换假钟)逐轮推进; flush 时点
除专项驱动用例外用 mod._flush_all_series() 直调(绕开驱动计时, 驱动时序由专项用例钉住)。

形态 D 封口末端锚点(plan 26-10-16-1509 §04, z 行扩列; 五条封口路径):
- test_torrent_idle_run_snapshot_fixed_at_open: 路径 ① 末端列 = 封口触发样本读数(冻结列不变)
- test_zrun_end_anchor_tracked_reading_on_stop: 路径 ③ 无样本在手 -> 末端锚点 = 游程内最后
  一条零样本读数(跟踪字段)
- test_zrun_end_anchor_tracked_reading_on_interval_change: 路径 ④ 改间隔关块同口径

P1-T1.2 守卫与容错簇(计划 26-10-20-2101, 覆盖率缺口清偿):
- test_pending_agg_rows_skips_empty_and_zero_coverage_buckets: 活尾 pending 行 —— 空桶不留行 /
  零有效覆盖桶 ValueError 逐一跳过(不出行 = null 语义), 无子行时 day/month 两级不出行
- test_open_run_hour_samples_idle_z_run_emits_zero_hours: 空闲 z 游程合成 —— credit 段按上一记录
  速率 + 游程内恒 0, totals 摊配到末端锚点, 末端取 last_seen 不推 now
- test_pending_agg_rows_idle_z_run_fills_tail_hours: 空闲 8 小时 z 游程 -> 活尾快照里 8 条 hour
  部分行(avg 0 / cov 3600, 内存行不落盘)+ 当日 day 行 + 当月 month 行; 累计器本体不动(副本语义)
- test_live_tail_idle_run_publishes_zero_hour_rows_end_to_end: 端到端 —— 先一笔非零(立信用)再
  一路空闲, z 游程未封口时活尾快照已带 0 值 hour 行(整小时 avg 0 / cov 3600), 3d+ 不再画「无采样」
- test_apply_interval_without_main_tick_uses_raw_interval: main_tick 未配置(0) -> 生效间隔
  = sample_interval 原值(不取整, 无失配告警)
- test_close_blocks_for_interval_change_skips_runless_and_unopened: 改间隔关块只封「有开放块」
  的游程与缓冲 —— 无缓冲的游程 / 未开块的 shell 缓冲零操作(不误封、不误 flush)
- test_torrent_active_missing_fields_takes_null_run: 活跃种子缺字段 -> n 游程(不写 0 不吞样本)
- test_torrent_zero_speed_readings_drift_defensive_raw_row: 零速过滤与字段读数口径漂移的防御支
  —— 读数非零时按 r 记录处理, 绝不把活跃读数吞进游程
- test_parser_never_emits_zero_slot_block (issue 26-11-01-0050): 解析器 `_close` 仅在
  有记录时产块 —— 零记录 B 块(空块)投产后不可达, 空块支改判防御死码
- test_stop_early_return_when_disabled_or_no_data_dir: stop() 在 qb_traffic 段缺失/未启用/
- test_v4_write_io_full_day_2s_interval
- test_v4_write_io_full_day_30s_interval
  data_dir 为空时零操作(不封游程不 flush)

W5(R29) S5 补测守阵(mutcore 审计 core/modules/traffic_sample_mod.py; 三分类/红验对应单点
tmp-analysis/mut-core-w5-classify.md, 中危真洞全盖 + 低危按簇代表, bug 面不入此列):
- test_w5_blockhead_zero_drift_run_cursor_roundtrip_and_agg: 块首游程零漂移支游标标称推进 + 块首游程
  槽位端点含(agg 逐区间 dt 断言)(_append_record_128 / _record_slots_9/12 / _agg_feed_8)
- test_w5_blockhead_run_rollback_clamp_dt_min_1: 块首游程回拨钳制 dt_ms=1(_append_record_113)
- test_w5_nonhead_zero_drift_run_no_dt: 非块首多槽游程零漂移不写 dt(_append_record_142)
- test_w5_n_prefix_split_zero_run_no_crash: n 前缀拆块实参带 end_ts, z 游程新块首不崩(_append_record_54)
- test_w5_counter_reset_split_zero_run_no_crash: 计数器重置关块实参带 end_ts 不崩(_append_record_65)
- test_w5_day_boundary_seal_uses_current_readings: 跨天封口末端锚点 = 本轮读数(_advance_run_10/11/13/14)
- test_w5_dry_run_full_chain_zero_write: dry-run 全链路零落盘 + 数据门不开(on_task_line_5 /
  _sample_global_24 / _torrent_has_data_8/9 / _agg_append_3 / _agg_trim_1)
- test_w5_problem_torrents_do_not_truncate_round: 问题种子不截断采样轮 + 连续 null 不崩
  (_sample_torrents_44/41/25/57/22)
- test_w5_single_direction_global_records_raw: 单方向活跃全局轮出 r 不进 z 游程(_sample_global_25)
- test_w5_active_filter_1bps_boundary: 活跃过滤 1 B/s 边界(_sample_torrents_5/7)
- test_w5_interval_change_closes_idle_block: 改间隔关纯空闲块, 新旧 interval 分块
  (_close_blocks_for_interval_change_11/13/14)
- test_w5_interval_change_audit_log_and_first_round_silent: 采样率变化审计 INFO / 首轮不虚假
  (_apply_interval_52 / __init___12)
- test_w5_live_tail_no_buffer_interval_contract: 无块活尾 interval_s 契约(_publish_live_tail_63)
- test_w5_live_tail_interval_change_reset_window_uses_effective: 改间隔复位窗口内无块活尾
  interval_s 取当前生效间隔(非陈旧旧块值, 违约守护; 变异 _publish_live_tail_59 方向与此一致, 疑等价变异待复核)
- test_w5_recover_midday_restart_catchup_and_open_hour: 午间重启补算/开放小时/当日累计器
  (_recover_series_81/93 / _catch_up_level_11/18)
"""

import logging

import os

import threading

import time

from datetime import datetime, time as _time

import pytest

import yaml

from auto_qb.config import QbTraffic, load_config

from auto_qb.config.validation import validate_config

from auto_qb.core.modules import traffic_sample_mod as ts_mod

from auto_qb.core.modules.traffic_sample_mod import (
    EVICT_CHECK_INTERVAL_S,
    GLOBAL_SERIES_KEY,
    V4_BUFFER_SLOT_CAP,
    ZRUN_CAP_SAMPLES,
    ZRUN_FLUSH_S,
    TrafficSampleModule,
)

from auto_qb.core.taskqueue import Task

from auto_qb.core.traffic_store import (
    AggRow,
    HEADER_LINE_V4,
    HOUR_SECONDS,
    TrafficV4Store,
    V4Block,
    V4HourSample,
    V4NullRun,
    V4Sample,
    V4ZeroRun,
    format_agg_row,
    format_v4_day_text,
    parse_v4_agg_text,
    parse_v4_day_text,
    v4_agg_file_path,
    v4_block_slots,
    v4_day_epoch,
    v4_day_file_path,
    v4_date_str_epoch,
    v4_epoch_date_str,
    v4_hour_agg,
    v4_live_tail_slots,
    v4_month_epoch,
    v4_rollup_agg,
    v4_series_dir,
    v4_window_dates,
    v4_z_totals_ramp,
)

from helpers import FakeClient, FakeTorrent, active_torrent, capture_logs, make_manager, seed_store, server_state

from webui_helpers import _enable_qb_traffic, _qb_v4

from traffic_sample_support import (
    _AGG_H0,
    _FlipSpeedTorrent,
    _add_backlog,
    _agg_text,
    _dat_text,
    _drive_full_day,
    _feed_30s,
    _flush,
    _idle_state,
    _local_epoch,
    _mgr_with_traffic,
    _run_sample,
    _spy_sample_rounds,
    _v4_path,
    _v4_read,
    _v4_series_dir,
    _w5_mgr,
    _w5_ts,
)
from clock import FakeClock


def test_sample_task_registered_when_enabled(tmp_path):
    """采样**不进队列**: enabled=true / enabled=false / 键组缺省(None) 三种情形启动后队列零任务"""
    for qb in (QbTraffic(enabled=True, sample_interval=45), QbTraffic(enabled=False), None):
        mgr = _mgr_with_traffic(tmp_path, qb)
        mgr.host.get("qb_traffic").start(mgr.ctx, dry_run=False)
        assert mgr.task_queue._fast == [], (qb, [t.name for t in mgr.task_queue._fast])


def test_sample_not_starved_by_immediate_task_backlog(tmp_path, monkeypatch):
    """回归主判据(issue 26-10-16-0954): 数百个立即到期任务占满队列(重启/热重载补建同形,
    配额 20 个/拍)时, 采样**每拍照常产样** —— 修复前它排在队列里, 排水窗内一次都轮不到
    (实测 7/7 复现 37~55s 静默, 1.5s 档丢约 36 轮)。判据走真实任务线入口, 排水未完成期间
    每一拍都必须采到。"""
    clock = FakeClock()
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30), clock=clock)
    mgr.config.main_tick = 30.0  # 采样节拍 = 1 个主循环拍(每拍都该采到)
    mgr.store.server_state = server_state()
    mod = mgr.host.get("qb_traffic")
    mod.start(mgr.ctx, dry_run=False)
    rounds = _spy_sample_rounds(monkeypatch, clock)
    executed = _add_backlog(mgr, 500, clock=clock)  # 500 个立即到期任务: 20/拍 -> 25 拍才排空
    for _ in range(20):  # 排水窗全程(20 拍只排掉 400 个)
        clock.advance(30)
        mgr._task_line(dry_run=False)
    assert len(rounds) == 20, f"排水窗内采样被饿死: 只采到 {len(rounds)} 轮(期望 20)"
    # 判据自检: 积压确实尚未排空(否则本用例没落在被饿死的窗口里)
    assert len(executed) == 400, f"本拍排空量偏离配额: {len(executed)}"


def test_sample_clock_line_gate_and_hot_reload_enable(tmp_path, monkeypatch):
    """时钟线到期闸门 + 启停: 未到 effective interval 不重复采; 停用零采样; 热重载
    enabled=true **不经 queue_rebuilt 相位**即开采(采样已与队列解耦)"""
    clock = FakeClock()
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30), clock=clock)
    mgr.config.main_tick = 2.0  # 时钟线每 2s 一拍, 采样间隔 30s -> 闸门只在到点放行
    mgr.store.server_state = server_state()
    mod = mgr.host.get("qb_traffic")
    mod.start(mgr.ctx, dry_run=False)
    rounds = _spy_sample_rounds(monkeypatch, clock)
    mod.on_task_line(False)
    assert len(rounds) == 1 and mod._effective_interval == 30  # 首拍即采(启动语义)
    mod.on_task_line(False)  # 同秒再拍两次: 未到点
    mod.on_task_line(False)
    assert len(rounds) == 1
    clock.advance(30)
    mod.on_task_line(False)
    assert len(rounds) == 2  # 到点再采
    # 停用: 零采样(到期点不动 -> 重新启用后首拍即采)
    mgr.config.qb_traffic.enabled = False
    clock.advance(30)
    mod.on_task_line(False)
    assert len(rounds) == 2 and mgr.task_queue._fast == []
    # 热重载启用: 直接改配置即开采(不依赖队列重建相位)
    mgr.config.qb_traffic.enabled = True
    mod.on_task_line(False)
    assert len(rounds) == 3


# ---------- 采样语义(P1 验收判据) ----------
def test_sampling_runs_on_caller_thread(tmp_path, monkeypatch):
    """单写线程不变式: 采样在调用时钟线钩子的线程(= 主循环线程)内同步完成, 模块不创建线程"""
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = server_state()
    mod = mgr.host.get("qb_traffic")
    mod.start(mgr.ctx, dry_run=False)
    seen = {}
    orig = TrafficSampleModule.sample_series

    def spy(self, key, ts, *readings):
        seen["ident"] = threading.get_ident()
        return orig(self, key, ts, *readings)

    monkeypatch.setattr(TrafficSampleModule, "sample_series", spy)
    threads_before = threading.active_count()
    mod.on_task_line(force=False)  # 宿主经任务线钩子调采样(首拍即采)
    assert seen["ident"] == threading.get_ident()  # 采样点产出线程 == 跑钩子的线程
    assert threading.active_count() == threads_before  # 模块未创建任何线程


def test_first_sample_only_establishes_baseline(tmp_path):
    """首个采样只立基线不出增量(首窗 null); 次轮增量 = cur - last(§03.4)"""
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = server_state()
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)  # 采样体无返回值(已非队列 handler; issue 26-10-16-0954)
    g1 = mod.latest[GLOBAL_SERIES_KEY]
    assert g1.dl_inc is None and g1.up_inc is None  # 首窗 null
    assert g1.dl_rate == 1024 and g1.up_rate == 2048  # 速率直采
    assert g1.dl_total == 10_000_000 and g1.dl_session == 1_000_000  # 累计快照照存
    assert mod._baselines[GLOBAL_SERIES_KEY] == {"dl_total": 10_000_000, "up_total": 20_000_000}
    # 次轮: 累计推进 -> 正常增量; 会话累计照存快照(不差分)
    mgr.store.server_state = server_state(alltime_dl=10_000_500, alltime_ul=20_001_000, dl_info_data=1_000_300)
    _run_sample(mgr)
    g2 = mod.latest[GLOBAL_SERIES_KEY]
    assert g2.dl_inc == 500 and g2.up_inc == 1000
    assert g2.dl_session == 1_000_300


def test_counter_rollback_records_reset_no_negative(tmp_path):
    """模拟 qB 重启(计数器回落): 不产负增量、增量记 null、基线更新为 cur、INFO 记重置"""
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = server_state()
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)  # 立基线
    mgr.store.server_state = server_state(alltime_dl=9_000_000, alltime_ul=20_000_000)  # dl 回落(qB 重启), ul 不变
    with capture_logs("auto_qb.core.modules.traffic_sample_mod") as cap:
        _run_sample(mgr)
    g = mod.latest[GLOBAL_SERIES_KEY]
    assert g.dl_inc is None  # 重置: 该点增量记 null
    assert g.up_inc == 0  # 未回落方向: 正常差分(0 增量合法)
    assert g.dl_total == 9_000_000  # 快照照存(消费侧可见回落事实)
    assert mod._baselines[GLOBAL_SERIES_KEY]["dl_total"] == 9_000_000  # 基线更新为 cur
    assert "判重置" in cap.text and "回落" in cap.text  # 重置有 INFO 记录


def test_disconnect_produces_null_point(tmp_path):
    """qB 断连(store.client None) -> 全局记 n 游程槽 + latest 镜像 null 点、单种本轮不采样、
    基线不推进(§03.5; v3 落盘形态为 n 游程, 断连期历史照常随 flush 落盘)"""
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = server_state()
    seed_store(mgr, [active_torrent()])
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)  # 正常一轮: 立基线
    baseline_before = dict(mod._baselines[GLOBAL_SERIES_KEY])
    t_before = mod.latest["torrent:HASH123"]
    mgr.client = None  # 断连(重连退避期同款: qbmanager 置 client=None)
    _run_sample(mgr)
    g = mod.latest[GLOBAL_SERIES_KEY]
    assert g.dl_rate is None and g.dl_total is None and g.dl_inc is None  # 全字段 null(镜像)
    assert mod._open_runs[GLOBAL_SERIES_KEY].kind == "n" and mod._open_runs[GLOBAL_SERIES_KEY].samples == 1
    assert mod.latest["torrent:HASH123"] is t_before  # 单种本轮不采样(停机洞由全局系列表达)
    assert mod._baselines[GLOBAL_SERIES_KEY] == baseline_before  # null 点不推进基线


def test_missing_fields_produce_null_point_not_zero(tmp_path):
    """server_state 缺字段 / 显式 None -> 该轮 null 处理(不写 0)且基线不推进(§03.5)"""
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mod = mgr.host.get("qb_traffic")
    # 降级路径: server_state 为 None
    mgr.store.server_state = None
    _run_sample(mgr)
    assert mod.latest[GLOBAL_SERIES_KEY].dl_rate is None
    # 增量轮部分键空值(qB 增量响应可带空值): 缺 dl_info_speed -> 整点 null
    mgr.store.server_state = server_state()
    del mgr.store.server_state["dl_info_speed"]
    _run_sample(mgr)
    g = mod.latest[GLOBAL_SERIES_KEY]
    assert g.dl_inc is None and g.up_rate is None and g.dl_total is None
    assert GLOBAL_SERIES_KEY not in mod._baselines  # 无读数 => 基线不立
    # 显式 None 同样按空值处理
    mgr.store.server_state = server_state(alltime_dl=None)
    _run_sample(mgr)
    assert mod.latest[GLOBAL_SERIES_KEY].up_rate is None
    assert GLOBAL_SERIES_KEY not in mod._baselines


def test_torrent_active_filter_zero_rows_when_idle(tmp_path):
    """活跃过滤(v3 §3.2 口径): 活跃(dlspeed>0 or upspeed>0)照常产 r; 空闲种子零 r
    —— 从未传输者(数据门拦截)连游程都不开, latest 无其采样点"""
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = server_state()
    seed_store(
        mgr,
        [
            active_torrent("DL_ACTIVE", dlspeed=100, upspeed=0),  # 仅下载活跃
            active_torrent("UL_ACTIVE", dlspeed=0, upspeed=200),  # 仅上传活跃
            FakeTorrent(hash="IDLE1"),  # 全空闲(从未传输: 无数据)
            active_torrent("IDLE2", dlspeed=0, upspeed=0),  # 显式 0 = 空闲
        ],
    )
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)
    assert "torrent:DL_ACTIVE" in mod.latest and "torrent:UL_ACTIVE" in mod.latest
    assert "torrent:IDLE1" not in mod.latest and "torrent:IDLE2" not in mod.latest  # 空闲零 r
    assert "torrent:IDLE1" not in mod._open_runs and "torrent:IDLE2" not in mod._open_runs  # 无数据不开游程
    t = mod.latest["torrent:DL_ACTIVE"]
    assert t.dl_rate == 100 and t.dl_total == 5_000_000 and t.dl_inc is None  # 单种首窗同样只立基线


def test_enabled_false_creates_zero_files_or_dirs(tmp_path):
    """enabled=false 与键组缺省两种情形: start + 采样全程零新建文件/目录(保守默认验收, 黄金法则 2)"""
    for qb in (QbTraffic(enabled=False), None):
        mgr = _mgr_with_traffic(tmp_path, qb)
        mgr.store.server_state = server_state()
        seed_store(mgr, [active_torrent()])
        mod = mgr.host.get("qb_traffic")
        mod.start(mgr.ctx, dry_run=False)
        _run_sample(mgr)
        _run_sample(mgr)
        assert sorted(str(p) for p in tmp_path.rglob("*")) == [], qb


def test_enabled_true_persists_under_data_dir(tmp_path, monkeypatch):
    """enabled=true: 采样点落 v3 天文件 <data_dir>/qb-traffic-v4/{global,torrents/<h>}/<date>.dat
    (头行 v3 + key 行 + B 块头 + r 行); 时钟整间隔步进 -> 零漂移零 dt 行; 会话快照列不落盘"""
    clock = FakeClock()
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30), clock=clock)
    mgr.store.server_state = server_state()
    seed_store(mgr, [active_torrent()])
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)  # t0
    clock.advance(30)
    _run_sample(mgr)  # t0+30
    _flush(mod)
    gpath = _v4_path(tmp_path, GLOBAL_SERIES_KEY, clock.now())
    tpath = _v4_path(tmp_path, "torrent:HASH123", clock.now())
    assert gpath.is_file() and tpath.is_file()
    lines = gpath.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "# auto-qb qb-traffic v4" and lines[1] == "key,global"
    parsed = parse_v4_day_text(gpath.read_text(encoding="utf-8"))
    assert parsed.key == "global" and len(parsed.blocks) == 1
    block = parsed.blocks[0]
    assert block.start_epoch == int(clock.now()) - 30 and block.interval_s == 30  # B 块头
    assert len(block.records) == 2 and all(isinstance(r, V4Sample) for r in block.records)
    r0 = block.records[0]
    assert (r0.dl_rate, r0.up_rate, r0.dl_total, r0.up_total) == (1024, 2048, 10_000_000, 20_000_000)
    assert all(r.dt_ms is None for r in block.records)  # 等间隔采样: 空载稀疏零 dt 行
    # r 行 5 列: delta 相对块基线(块首 r 立基线 -> 首行 delta 0,0); 会话快照不落任何列
    assert lines[2].split(",") == ["B", str(block.start_epoch), "30", "10000000", "20000000"]
    assert lines[3].split(",") == ["r", "1024", "2048", "0", "0"]


def test_module_contract(tmp_path):
    """模块契约: name=qb_traffic / sections 声明 qb_traffic 且被装配清单认领"""
    mgr = _mgr_with_traffic(tmp_path, None)
    mod = mgr.host.get("qb_traffic")
    assert mod is not None and mod.name == "qb_traffic"
    assert mod.sections() == ("qb_traffic", )
    assert "qb_traffic" in mgr.host.claimed_sections()


def test_flush_driver_interval_and_deferred_first_round(tmp_path, monkeypatch):
    """flush 驱动(§3.3): 进程首轮只记时不提前 flush(批量优先); now - last_flush >=
    flush_interval 才全系列批量落盘; v4 关块谓词(flush ∧ has_r_row)下带 r 行的块随
    flush 关闭, 之后的记录开新块(每块块头恰写一次)"""
    clock = FakeClock()
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30, flush_interval=60), clock=clock)
    mgr.store.server_state = server_state()
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)  # t0: r 进缓冲; 首轮只记 flush 时点
    assert _v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now()) is None
    assert mod._buffers[GLOBAL_SERIES_KEY].records
    clock.advance(30)
    _run_sample(mgr)  # 30 < 60: 未到点, 缓冲滞留
    assert _v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now()) is None
    clock.advance(30)
    _run_sample(mgr)  # 60 >= 60: 批量落盘(本轮记录含在内; 块头随批)+ 关块(has_r_row)
    parsed = _v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now())
    assert parsed is not None and len(parsed.blocks) == 1 and len(parsed.blocks[0].records) == 3
    buf = mod._buffers[GLOBAL_SERIES_KEY]
    assert buf.records == [] and buf.start_epoch is None  # v4: 带 r 行的块随 flush 关闭
    clock.advance(30)
    _run_sample(mgr)  # 30 < 60: 缓冲滞留(新块已开)
    assert len(_v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now()).blocks[0].records) == 3
    clock.advance(30)
    _run_sample(mgr)  # 60 >= 60: 新块落盘(自带新块头)
    parsed = _v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now())
    assert len(parsed.blocks) == 2 and len(parsed.blocks[1].records) == 2  # 两块两 B 行, 每块头恰一次


def test_global_idle_run_stays_open_across_flush_and_seals_on_resume(tmp_path, monkeypatch):
    """空闲块不关(v4 §01 关块谓词 + 「空闲封口」): 全局空闲开放 z 游程跨 flush 时点滞留
    内存(N4 天级保险闸, 600s 不再常态触发), 空闲段不落盘; 恢复传输(非 z 事件)封口,
    z 游程成为新块首(基线 = 该快照, delta = 0); 恢复 r 行 delta <= flush 窗 x 速率"""
    clock = FakeClock()
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30), clock=clock)
    mgr.store.server_state = server_state()
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)  # t0: 活跃 -> r 记录进缓冲
    mgr.store.server_state = _idle_state()
    for _ in range(21):  # t0+30 .. t0+630: 零样本只推进游程, 跨 600s flush 时点
        clock.advance(30)
        _run_sample(mgr)
    assert GLOBAL_SERIES_KEY in mod._open_runs  # 空闲块不关: 游程仍开放(天级保险闸未触)
    parsed = _v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now())
    assert len(parsed.blocks) == 1 and [type(r) for r in parsed.blocks[0].records] == [V4Sample]
    # 恢复传输(非 z 事件): 封 z 游程成新块首 + r 记录; 下一 flush 关块重开
    mgr.store.server_state = server_state(alltime_dl=10_000_400, alltime_ul=20_000_200)
    clock.advance(30)  # t0+660
    _run_sample(mgr)
    assert GLOBAL_SERIES_KEY not in mod._open_runs  # 封口即移除
    _flush(mod)
    parsed = _v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now())
    assert len(parsed.blocks) == 2  # 空闲块不关 -> 恢复块 = 新块(块首 z)
    z, r2 = parsed.blocks[1].records
    assert isinstance(z, V4ZeroRun) and z.run_len == 21  # [t0+30, t0+630] 共 21 个零样本
    assert (z.dl_total, z.up_total) == (10_000_000, 20_000_000)  # totals 快照 = all-time 对
    assert z.dt_ms is None  # 标称跨度(run_len x interval), 零漂移不写 dt
    assert isinstance(r2, V4Sample)  # 文件序 = 时间序(z 块首 + 恢复 r)
    assert 0 <= r2.dl_total - z.dl_total <= 600 * 1024  # delta <= flush 窗 x 速率(v4 §01 封顶)


def test_torrent_idle_run_snapshot_fixed_at_open(tmp_path, monkeypatch):
    """单种动过->停: z 记录 totals 快照固定在开启时刻(首个零样本的 all-time 对);
    空闲期两个不同 totals 的零样本不刷新快照(§3.4 沿用); 形态 D: 末端列落封口触发
    样本的读数(路径 ①, 冻结列不受影响)"""
    clock = FakeClock()
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30), clock=clock)
    mgr.store.server_state = server_state()
    rec = active_torrent("HASH123", downloaded=5_000_000, uploaded=3_000_000)
    seed_store(mgr, [rec])
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)  # t0: 活跃 -> r 记录(数据门经缓冲翻真)
    rel_key = "torrent:HASH123"
    rec.dlspeed = 0
    rec.upspeed = 0
    rec.downloaded, rec.uploaded = 5_000_500, 3_000_200  # 首个零样本: 游程开启, 快照取此对
    clock.advance(30)
    _run_sample(mgr)
    rec.downloaded, rec.uploaded = 5_000_900, 3_000_400  # 次个零样本: 只推进, 快照不刷新
    clock.advance(30)
    _run_sample(mgr)  # t0+60
    clock.advance(30)  # t0+90: 第三个零样本(跨 flush 时点也不封 —— 空闲块不关)
    _run_sample(mgr)
    assert rel_key in mod._open_runs  # v4: 游程跨 flush 滞留内存
    rec.dlspeed = 512  # 恢复传输(非 z 事件) -> 封口
    rec.upspeed = 256
    rec.downloaded, rec.uploaded = 5_001_000, 3_000_600
    clock.advance(30)
    _run_sample(mgr)  # t0+120: 封 z(3 槽) + r
    z = mod._buffers[rel_key].records[1]  # 同块续写: [r(t0), z, r(t0+120)]
    assert isinstance(z, V4ZeroRun) and z.run_len == 3
    assert (z.dl_total, z.up_total) == (5_000_500, 3_000_200)  # 快照 = 首零样本对, 非后续零样本
    assert (z.dl_total_end, z.up_total_end) == (5_001_000, 3_000_600)  # 形态 D 末端列 = 封口触发样本(路径 ①)
    assert rel_key not in mod._open_runs
    _flush(mod)
    parsed = _v4_read(tmp_path, rel_key, clock.now())
    recs = parsed.blocks[0].records
    assert [type(r) for r in recs] == [V4Sample, V4ZeroRun, V4Sample]  # 文件序 = 时间序


def test_never_transferred_torrent_zero_files_runs_entries(tmp_path, monkeypatch):
    """从未传输的种子: 零文件、零游程(数据门 = 目录判定 + 进程内缓存, §3.2)"""
    clock = FakeClock()
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30), clock=clock)
    mgr.store.server_state = server_state()
    seed_store(mgr, [FakeTorrent(hash="NEVER")])  # 全零速且从无流量
    mod = mgr.host.get("qb_traffic")
    for _ in range(3):
        clock.advance(30)
        _run_sample(mgr)
    assert not _v4_series_dir(tmp_path, "NEVER").exists()  # 零文件零目录
    assert "torrent:NEVER" not in mod._open_runs and "torrent:NEVER" not in mod.latest
    assert "torrent:NEVER" in mod._no_data  # 门缓存: 确认无数据后稳态零目录 IO


def test_nonzero_arrival_seals_z_before_raw_same_round(tmp_path, monkeypatch):
    """触发 (1): 非零样本到达同轮先封 z 游程再出 r —— buffer 记录序 = 文件序 = 时间序"""
    clock = FakeClock()
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30), clock=clock)
    mgr.store.server_state = server_state()
    rec = active_torrent("HASH123")
    seed_store(mgr, [rec])
    mod = mgr.host.get("qb_traffic")
    key = "torrent:HASH123"
    _run_sample(mgr)  # t0: 活跃 -> r
    rec.dlspeed = 0
    rec.upspeed = 0
    clock.advance(30)
    _run_sample(mgr)  # t0+30: 零样本 -> 开游程(不落盘)
    rec.dlspeed = 512
    clock.advance(30)
    _run_sample(mgr)  # t0+60: 再活跃 -> 同轮先 z 后 r
    assert key not in mod._open_runs  # 封口即移除
    _flush(mod)
    parsed = _v4_read(tmp_path, key, clock.now())
    recs = parsed.blocks[0].records
    assert [type(r) for r in recs] == [V4Sample, V4ZeroRun, V4Sample]  # 文件序 = 时间序
    z = recs[1]
    assert z.run_len == 1  # 封 [start, last_seen](单零样本游程)
    assert (z.dl_total, z.up_total) == (5_000_000, 3_000_000)  # 快照 = 零样本 all-time 对(种子 totals)
    assert all(r.dt_ms is None for r in recs)  # 整间隔步进: 零漂移


def test_disconnect_seals_run_before_null_r2(tmp_path, monkeypatch):
    """触发 (2)(R2): null 到达先封开放 z 游程再记 n 游程 —— z 覆盖不横跨断连期
    (把「未知」虚标成「观测到 0」的 v3 形态 = z 与 n 各占各的槽)"""
    clock = FakeClock()
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30), clock=clock)
    mgr.store.server_state = server_state()
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)  # t0: 活跃
    mgr.store.server_state = _idle_state()
    clock.advance(30)
    _run_sample(mgr)  # t0+30: 零样本开游程
    clock.advance(30)
    _run_sample(mgr)  # t0+60: 推进 [t0+30, t0+60]
    mgr.client = None  # 断连(重连退避期同款)
    clock.advance(30)
    _run_sample(mgr)  # t0+90: null -> 先封 z 再记 n(n 游程开启)
    assert mod.latest[GLOBAL_SERIES_KEY].dl_rate is None  # 镜像 null 点(断连轮)
    mgr.client = FakeClient()
    mgr.store.server_state = server_state()
    clock.advance(30)
    _run_sample(mgr)  # t0+120: 重连且活跃 -> 封 n 游程(触发 (1)) + r
    _flush(mod)
    parsed = _v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now())
    recs = parsed.blocks[0].records
    assert [type(r) for r in recs] == [V4Sample, V4ZeroRun, V4NullRun, V4Sample]  # z 行在 n 之前
    assert recs[1].run_len == 2  # z 封 [t0+30, t0+60], 末日早于断连轮
    assert recs[2].run_len == 1  # n 槽 = 断连轮(重连非零样本封口)


def test_zero_run_requires_valid_totals_snapshot(tmp_path, monkeypatch):
    """零样本读数口径: 开 z 游程需要合法 totals 快照 —— totals 缺失的零样本不开新游程
    (空闲不出 null 槽); 已开游程的零样本只推进 last_seen 无需重读 totals"""
    clock = FakeClock()
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30), clock=clock)
    mgr.store.server_state = server_state()
    rec = active_torrent("HASH123")
    seed_store(mgr, [rec])
    mod = mgr.host.get("qb_traffic")
    key = "torrent:HASH123"
    _run_sample(mgr)  # t0: 活跃 -> r 记录(缓冲存在 => 数据门经进程内缓冲翻真)
    rec.dlspeed = 0
    rec.upspeed = 0
    rec.downloaded = None  # all-time 对缺失 -> 不开新游程
    clock.advance(30)
    _run_sample(mgr)
    assert key not in mod._open_runs  # 无新游程(无 z 也无 n)
    assert all(not isinstance(r, (V4ZeroRun, V4NullRun)) for r in mod._buffers[key].records)
    # 对照: 已开游程的零样本无需重读 totals, 照常推进
    rec.downloaded, rec.uploaded = 5_000_000, 3_000_000
    clock.advance(30)
    _run_sample(mgr)
    assert mod._open_runs[key].samples == 1
    rec.downloaded = None
    clock.advance(30)
    _run_sample(mgr)
    run = mod._open_runs[key]
    assert run.samples == 2 and run.last_seen == clock.now()  # 只推进, 不因 totals 缺失断游程


def test_global_always_opens_run_vs_torrent_gated(tmp_path, monkeypatch):
    """两系列零样本纪律对照(§3.2): 全局恒开游程(无数据门); 单种目录判定门拦截
    (从未传输不开游程不建文件)"""
    clock = FakeClock()
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30), clock=clock)
    mgr.store.server_state = _idle_state()
    seed_store(mgr, [FakeTorrent(hash="NEVER")])
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)  # t0: 全局零样本恒开游程
    assert GLOBAL_SERIES_KEY in mod._open_runs and mod._open_runs[GLOBAL_SERIES_KEY].samples == 1
    assert not _v4_series_dir(tmp_path, "NEVER").exists()  # 单种被数据门拦截
    assert "torrent:NEVER" not in mod._open_runs
    clock.advance(30)
    _run_sample(mgr)  # t0+30: 次轮全局游程推进(样本 2, 未到封口)
    assert mod._open_runs[GLOBAL_SERIES_KEY].samples == 2
    assert "torrent:NEVER" not in mod._open_runs


def test_restart_loses_at_most_one_open_run(tmp_path, monkeypatch):
    """崩溃/重启语义: 重建 sampler 实例 -> 内存游程与缓冲消失(丢 <=1 个未封口游程, 纯零
    信息), 已落盘块不受影响; 零样本按纪律重新开游程(重启后首个封口游程成为新块首)"""
    clock = FakeClock()
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30), clock=clock)
    mgr.store.server_state = server_state()
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)  # t0: 活跃 -> r 进缓冲
    _flush(mod)  # 优雅落盘 r(块 1)
    mgr.store.server_state = _idle_state()
    clock.advance(30)
    _run_sample(mgr)  # t0+30: 开游程
    clock.advance(30)
    _run_sample(mgr)  # t0+60: 推进(未封口, 随进程消失)
    mod2 = TrafficSampleModule(mgr.ctx, clock=clock)  # 重启: 新实例(buffers/_open_runs 全空), 同钟注入
    for _ in range(3):  # t0+90..t0+150: 零样本重新开游程(跨 flush 时点不封 —— 空闲块不关)
        clock.advance(30)
        mod2.handle_traffic_sample(dry_run=False)
    assert GLOBAL_SERIES_KEY in mod2._open_runs
    mgr.store.server_state = server_state(alltime_dl=10_000_100, alltime_ul=20_000_100)  # 恢复传输(非 z 事件)
    clock.advance(30)  # t0+180: 封 z(4 槽) + r
    mod2.handle_traffic_sample(dry_run=False)
    mod2._flush_all_series()
    parsed = _v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now())
    assert len(parsed.blocks) == 2  # 重启前后各一块(重启 = 新块首)
    assert [type(r) for r in parsed.blocks[0].records] == [V4Sample]  # 已落盘块不受重启影响
    z = parsed.blocks[1].records[0]
    assert isinstance(z, V4ZeroRun) and z.run_len == 3  # 重启后游程如期封口(t0+90..t0+150)
    assert parsed.blocks[1].start_epoch == int(clock.now()) - 90  # 块首 = 游程首零样本(t0+90)


def test_zero_samples_do_not_touch_baselines_or_latest(tmp_path, monkeypatch):
    """零样本不动 baselines/latest(§3.4): 基线只在 r 采样点推进, 镜像冻结在最后活跃点"""
    clock = FakeClock()
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30), clock=clock)
    mgr.store.server_state = server_state()
    rec = active_torrent("HASH123")
    seed_store(mgr, [rec])
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)  # t0: 活跃
    g_point = mod.latest[GLOBAL_SERIES_KEY]
    t_point = mod.latest["torrent:HASH123"]
    g_base = dict(mod._baselines[GLOBAL_SERIES_KEY])
    t_base = dict(mod._baselines["torrent:HASH123"])
    mgr.store.server_state = _idle_state(alltime_dl=10_000_100, alltime_ul=20_000_100)
    rec.dlspeed = 0
    rec.upspeed = 0
    rec.downloaded, rec.uploaded = 5_000_500, 3_000_500
    for _ in range(3):
        clock.advance(30)
        _run_sample(mgr)
    assert mod.latest[GLOBAL_SERIES_KEY] is g_point  # 镜像冻结(同一对象, 未被零样本替换)
    assert mod.latest["torrent:HASH123"] is t_point
    assert mod._baselines[GLOBAL_SERIES_KEY] == g_base and mod._baselines["torrent:HASH123"] == t_base


def test_dry_run_no_disk_but_memory_runs_advance(tmp_path, monkeypatch):
    """dry_run: 全程零落盘; 缓冲与游程内存照常推进, flush 触发静默跳过写(记录照常清空)"""
    clock = FakeClock()
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30, flush_interval=60), clock=clock)
    mgr.store.server_state = server_state()
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr, dry_run=True)  # t0: 活跃(仅内存)
    mgr.store.server_state = _idle_state()
    clock.advance(30)
    _run_sample(mgr, dry_run=True)  # t0+30: 开游程
    assert GLOBAL_SERIES_KEY in mod._open_runs
    assert mod._buffers[GLOBAL_SERIES_KEY].records  # 缓冲照常推进
    clock.advance(30)  # t0+60: flush 时点 -> 静默跳过写, 记录照常清空
    _run_sample(mgr, dry_run=True)
    assert not (tmp_path / "qb-traffic-v4").exists()  # 零目录零文件
    assert mod._buffers[GLOBAL_SERIES_KEY].records == []
    clock.advance(600)  # t0+660: 长空闲跨 flush 时点 —— v4 空闲块不关, 游程仍开放(内存照常)
    _run_sample(mgr, dry_run=True)
    assert GLOBAL_SERIES_KEY in mod._open_runs
    assert not (tmp_path / "qb-traffic-v4").exists()
    mgr.store.server_state = server_state()  # 恢复传输(非 z 事件) -> 封口(内存照常)
    clock.advance(30)
    _run_sample(mgr, dry_run=True)
    assert GLOBAL_SERIES_KEY not in mod._open_runs
    assert not (tmp_path / "qb-traffic-v4").exists()


def test_clock_rollback_clamped_dt_min_1(tmp_path, monkeypatch):
    """时钟回拨(§2.3): 单调钳制 dt_ms = max(1, 实测) —— 回拨行 dt_ms 恒 >= 1, 链不产负推进"""
    clock = FakeClock()
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30), clock=clock)
    mgr.store.server_state = server_state()
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)  # t0
    clock.advance(30)
    _run_sample(mgr)  # t0+30(标称, 游标 t0+30)
    clock.freeze(clock.now() - 10)  # 回拨 10s: 实测 t0+20
    _run_sample(mgr)
    recs = mod._buffers[GLOBAL_SERIES_KEY].records
    assert recs[-1].dt_ms == 1  # max(1, round((t0+20 - (t0+30)) x 1000)) = 1
    _flush(mod)
    parsed = _v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now())
    assert parsed.blocks[0].records[-1].dt_ms == 1  # 落盘形态一致


# ---------- C1 热重载联动 + 跨天切块 + 缓冲闸 + stop 钩子(§3.4/§3.5) ----------
def test_interval_change_hot_reload_new_block_and_effective_interval(tmp_path, monkeypatch):
    """热重载改采样率即时生效(§3.5): 采样体现读 -> _effective_interval 更新 + 旧块落盘(旧
    interval) + 新块带新 interval —— 新旧数据分块各有 interval(A3 根因闭合)。
    !节拍表达已随 issue 26-10-16-0954 从「回写 task.interval」改为时钟线自持
    (_next_sample_at), 故断言 _effective_interval(节拍与块头共用同一单点)"""
    clock = FakeClock()
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30), clock=clock)
    mgr.store.server_state = server_state()
    mod = mgr.host.get("qb_traffic")
    mod.handle_traffic_sample(dry_run=False)  # t0: r 进缓冲(interval 30)
    clock.advance(30)
    mgr.config.qb_traffic.sample_interval = 10
    mod.handle_traffic_sample(dry_run=False)  # t0+30: 检测变化 -> 关旧块 + 记新节拍
    assert mod._effective_interval == 10  # A3: 现读生效
    assert mod._next_sample_at == clock.now() + 10  # 下一到期点随新节拍推进
    parsed = _v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now())
    assert len(parsed.blocks) == 1 and parsed.blocks[0].interval_s == 30  # 旧块随关块落盘(旧 interval)
    assert [type(r) for r in parsed.blocks[0].records] == [V4Sample]
    clock.advance(10)
    mod.handle_traffic_sample(dry_run=False)  # t0+40: 新块(新 interval)
    _flush(mod)
    parsed = _v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now())
    assert len(parsed.blocks) == 2
    assert parsed.blocks[1].interval_s == 10 and parsed.blocks[1].start_epoch == int(clock.now()) - 10
    # 变化轮自身记录落在新块首(关块先行于本轮采样), 下轮续写同块
    assert [type(r) for r in parsed.blocks[1].records] == [V4Sample, V4Sample]


def test_interval_mismatch_ceils_and_warns_once(tmp_path, monkeypatch):
    """运行期失配(D5): 向上取整到下一倍数(main_tick=2 配 3s -> 4s, _effective_interval=取整值)
    + 告警一次(防重复); 配置再变记忆复位; 不拒采"""
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=3))
    mgr.config.main_tick = 2.0  # FakeConfig 缺省 1.0; 显式置 2 构造失配场景
    mgr.store.server_state = server_state()
    mod = mgr.host.get("qb_traffic")
    with capture_logs("auto_qb.core.modules.traffic_sample_mod") as cap:
        mod.handle_traffic_sample(dry_run=False)  # 不拒采
    assert mod._effective_interval == 4  # ceil(3/2) x 2 = 4(颗粒变粗不断线)
    assert "取整" in cap.text and "整数倍" in cap.text  # 恰一次告警
    with capture_logs("auto_qb.core.modules.traffic_sample_mod") as cap2:
        mod.handle_traffic_sample(dry_run=False)
    assert "取整" not in cap2.text  # 同一失配不重复告警
    # 配置变化 -> 记忆复位: 新失配再告警一次
    mgr.config.qb_traffic.sample_interval = 5  # ceil(2.5) x 2 = 6
    with capture_logs("auto_qb.core.modules.traffic_sample_mod") as cap3:
        mod.handle_traffic_sample(dry_run=False)
    assert mod._effective_interval == 6 and "取整" in cap3.text


def test_interval_decimal_match_kept_not_ceiled(tmp_path, monkeypatch):
    """整数倍匹配的小数档原样生效(2026-10-05 修复): main_tick=1.5 配 1.5s ->
    _effective_interval == 1.5(不再被整数秒口径静默抬到 2), 块头 interval_s == 1.5(B 行写
    1.5), 失配告警不触发; 同块两记录标称 1.5s 推进零漂移(r 行不写显式 dt)"""
    clock = FakeClock()
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=1.5), clock=clock)
    mgr.config.main_tick = 1.5  # FakeConfig 缺省 1.0; 显式对齐构造匹配小数档
    mgr.store.server_state = server_state()
    mod = mgr.host.get("qb_traffic")
    with capture_logs("auto_qb.core.modules.traffic_sample_mod") as cap:
        mod.handle_traffic_sample(dry_run=False)  # t0: 块首 r
    assert mod._effective_interval == 1.5
    assert "取整" not in cap.text  # 整数倍匹配: 失配告警不触发
    clock.advance(1.5)
    mod.handle_traffic_sample(dry_run=False)  # t0+1.5: 同块续写
    _flush(mod)
    parsed = _v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now())
    assert len(parsed.blocks) == 1 and parsed.blocks[0].interval_s == 1.5
    text = _v4_path(tmp_path, GLOBAL_SERIES_KEY, clock.now()).read_text(encoding="utf-8")
    b_rows = [ln for ln in text.splitlines() if ln.startswith("B,")]
    assert len(b_rows) == 1 and b_rows[0].split(",")[2] == "1.5"  # B 行 interval 列如实带小数
    recs = parsed.blocks[0].records
    assert [type(r) for r in recs] == [V4Sample, V4Sample] and recs[1].dt_ms is None  # 零漂移


def test_day_boundary_cut(tmp_path, monkeypatch):
    """跨天切块(00:00 硬切, 本地时区, §3.3): 跨界记录使旧块落旧日期文件、新记录开新块落
    新日期文件 —— 23:59 块与 00:00 新块各带正确块头(interval 不变)"""
    clock = FakeClock(start=_local_epoch(23, 59, 50))
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30), clock=clock)
    mgr.store.server_state = server_state()
    mod = mgr.host.get("qb_traffic")
    t_before = clock.now()
    _run_sample(mgr)  # 23:59:50: 块 A(今日)
    clock.advance(20)  # 00:00:10(次日): 跨界 -> 旧块落盘 + 新块
    _run_sample(mgr)
    _flush(mod)
    today = v4_epoch_date_str(t_before)
    p_today = _v4_path(tmp_path, GLOBAL_SERIES_KEY, t_before)
    p_tomorrow = _v4_path(tmp_path, GLOBAL_SERIES_KEY, clock.now())
    assert p_today.is_file() and p_tomorrow.is_file()
    d1 = parse_v4_day_text(p_today.read_text(encoding="utf-8"))
    d2 = parse_v4_day_text(p_tomorrow.read_text(encoding="utf-8"))
    assert len(d1.blocks) == 1 and d1.blocks[0].start_epoch == int(t_before)  # 23:59 块
    assert d1.blocks[0].interval_s == 30 and len(d1.blocks[0].records) == 1
    assert len(d2.blocks) == 1 and d2.blocks[0].start_epoch == int(clock.now())  # 00:00 新块
    assert d2.blocks[0].interval_s == 30 and len(d2.blocks[0].records) == 1


def test_day_boundary_seals_open_run(tmp_path, monkeypatch):
    """跨天封游程(块不跨天的必要触发): 00:00 样本先封旧日游程(记录入旧块), 本样本开新
    游程; 封口后换型记录跨天 -> 旧块落盘 + 单槽游程成为新块首(不写 dt, 无引导间隔)"""
    clock = FakeClock(start=_local_epoch(23, 59, 20))
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30), clock=clock)
    mgr.store.server_state = server_state()
    mod = mgr.host.get("qb_traffic")
    t_before = clock.now()
    _run_sample(mgr)  # 23:59:20: 活跃 -> 块 A 首 r
    mgr.store.server_state = _idle_state()
    clock.advance(30)
    _run_sample(mgr)  # 23:59:50: 零样本 -> 开 z 游程
    clock.advance(20)  # 00:00:10(次日): 零样本 -> 先封旧游程(不跨天)再开新游程
    _run_sample(mgr)
    assert GLOBAL_SERIES_KEY in mod._open_runs  # 新游程已开
    mgr.store.server_state = server_state()
    clock.advance(30)  # 00:00:40: 再活跃 -> 封新游程(单槽) + 跨天切块
    _run_sample(mgr)
    _flush(mod)
    p_today = _v4_path(tmp_path, GLOBAL_SERIES_KEY, t_before)
    p_tomorrow = _v4_path(tmp_path, GLOBAL_SERIES_KEY, clock.now())
    d1 = parse_v4_day_text(p_today.read_text(encoding="utf-8"))
    d2 = parse_v4_day_text(p_tomorrow.read_text(encoding="utf-8"))
    assert [type(r) for r in d1.blocks[0].records] == [V4Sample, V4ZeroRun]  # 旧块: r + 跨天前封的 z
    assert d1.blocks[0].records[1].run_len == 1
    assert [type(r) for r in d2.blocks[0].records] == [V4ZeroRun, V4Sample]  # 新块首 = 单槽游程
    z2 = d2.blocks[0].records[0]
    assert z2.run_len == 1 and z2.dt_ms is None  # 块首单槽游程: dt 无消费者不写
    assert d2.blocks[0].start_epoch == int(clock.now()) - 30  # B.start = 游程首槽(00:00:10)


def test_stop_flushes_all_and_seals_open_runs(tmp_path, monkeypatch):
    """stop() 钩子(§3.4): 封全部开放游程 + 全量 flush(优雅退出零丢失); 幂等(重复调用零副作用)"""
    clock = FakeClock()
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30, flush_interval=10**9), clock=clock)
    mgr.store.server_state = server_state()
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)  # t0: 活跃 -> r 进缓冲
    mgr.store.server_state = _idle_state()
    clock.advance(30)
    _run_sample(mgr)  # t0+30: 开游程
    clock.advance(30)
    _run_sample(mgr)  # t0+60: 推进(未封口)
    mod.stop()
    assert GLOBAL_SERIES_KEY not in mod._open_runs  # 游程全封
    parsed = _v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now())
    recs = parsed.blocks[0].records
    assert [type(r) for r in recs] == [V4Sample, V4ZeroRun]  # 全量落盘
    assert recs[1].run_len == 2
    before = parsed.blocks[0].records
    mod.stop()  # 幂等: 缓冲游程已空, 零副作用
    assert _v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now()).blocks[0].records == before


def test_zrun_end_anchor_tracked_reading_on_stop(tmp_path, monkeypatch):
    """形态 D 封口路径 ③(无样本在手 = stop()): 末端锚点 = 游程内最后一条零样本读数
    (全局系列每轮现读 totals, 跟踪字段随读刷新); 冻结列不变, 末端列落盘该读数"""
    clock = FakeClock()
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30, flush_interval=10**9), clock=clock)
    mgr.store.server_state = server_state()
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)  # t0: 活跃 -> r 进缓冲
    for i in (1, 2, 3):  # 空闲三轮: alltime 逐轮增长(全局系列每轮现读 -> 跟踪字段刷新)
        mgr.store.server_state = _idle_state(alltime_dl=10_000_000 + i * 400, alltime_ul=20_000_000 + i * 200)
        clock.advance(30)
        _run_sample(mgr)
    mod.stop()
    parsed = _v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now())
    z = parsed.blocks[0].records[1]
    assert isinstance(z, V4ZeroRun) and z.run_len == 3
    assert (z.dl_total, z.up_total) == (10_000_400, 20_000_200)  # 冻结列 = 开启快照(首零样本对)
    assert (z.dl_total_end, z.up_total_end) == (10_001_200, 20_000_600)  # 末端列 = 最后零样本读数


def test_zrun_end_anchor_tracked_reading_on_interval_change(tmp_path, monkeypatch):
    """形态 D 封口路径 ④(采样间隔热重载关块): 关块前封开放游程, 末端锚点 = 跟踪的最后
    零样本读数; 旧块以旧 interval 落盘、新数据新块新 interval(A3 口径不变)"""
    clock = FakeClock()
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30), clock=clock)
    mgr.store.server_state = server_state()
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)  # t0: 活跃 -> 开块
    for i in (1, 2):  # 空闲两轮(alltime 增长 -> 跟踪字段刷新)
        mgr.store.server_state = _idle_state(alltime_dl=10_000_000 + i * 400, alltime_ul=20_000_000 + i * 200)
        clock.advance(30)
        _run_sample(mgr)
    mgr.config.qb_traffic.sample_interval = 10  # 热重载: 下一轮关块
    clock.advance(30)
    _run_sample(mgr)  # t0+90: 检测变化 -> 封游程 + 旧块落盘
    assert mod._effective_interval == 10
    parsed = _v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now())
    assert parsed.blocks[0].interval_s == 30
    z = parsed.blocks[0].records[1]
    assert isinstance(z, V4ZeroRun) and z.run_len == 2
    assert (z.dl_total, z.up_total) == (10_000_400, 20_000_200)  # 冻结列 = 开启快照
    assert (z.dl_total_end, z.up_total_end) == (10_000_800, 20_000_400)  # 末端列 = 最后零样本读数


def test_stop_dry_run_short_circuit(tmp_path, monkeypatch):
    """stop() dry_run 短路: 不落盘不建目录(观测写盘属真实副作用)"""
    clock = FakeClock()
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30), clock=clock)
    mgr.store.server_state = server_state()
    mod = mgr.host.get("qb_traffic")
    mod.start(mgr.ctx, dry_run=True)
    _run_sample(mgr, dry_run=True)
    mod.stop()
    assert not (tmp_path / "qb-traffic-v4").exists()


def test_agg_hour_degenerate_equal_interval_matches_v2(tmp_path):
    """dt_i ≡ interval_s 退化(§4.1 验收): 等间隔无漂移序列产出的 hour 行与等间隔均值
    公式 round(Σrate/n)(v2 纯活跃桶口径)逐列一致(对照钉住), 且等于 v4_hour_agg 标称输入"""
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mod = mgr.host.get("qb_traffic")
    key = GLOBAL_SERIES_KEY
    h0 = _AGG_H0
    obs = [(100 + 50 * i, 40 + 10 * i, 1000 + 100 * i, 2000 + 100 * i) for i in range(4)]
    _feed_30s(mod, key, h0, obs)
    mod._agg_flush_series(key, now=h0 + HOUR_SECONDS)
    row = parse_v4_agg_text(_agg_text(tmp_path, key)).hours[0]
    # 等间隔均值公式对照(v2 纯活跃桶口径 round(Σrate/n), 内联计算 —— v2 解析已随 S5 退役)
    assert row.dl_avg == int(round(sum(d for d, _, _, _ in obs) / len(obs)))
    assert row.up_avg == int(round(sum(u for _, u, _, _ in obs) / len(obs)))
    assert (row.dl_max, row.up_max) == (max(d for d, _, _, _ in obs), max(u for _, u, _, _ in obs))
    assert (row.dl_total, row.up_total) == (1300, 2300)  # totals = 级末快照
    manual = v4_hour_agg(h0, tuple(V4HourSample(d, u, t, s, 30.0) for d, u, t, s in obs))
    assert row.dl_avg == manual.dl_avg and row.cov_s == manual.cov_s == 120


def test_stop_seals_aggregates_and_dry_run_short_circuit(tmp_path, monkeypatch):
    """stop() 聚合封口(§3.4): 完结层级照常落 agg; 幂等; dry_run 短路(累计器内存照常
    推进, 零落盘)"""
    base = _AGG_H0
    # 时钟钉在测试 hour 附近: stop() 封口用真实 time.time() 时, 该 hour 行已到龄会被
    # rollup_window 裁剪(C-01 修复后运行期新建系列裁剪生效, 数据降级进 day 行) —— 本用例
    # 验的是封口语义, 与裁剪无关, 故注入时钟。注入须先于模块构造(缺省钟构造期解析)
    clock = FakeClock(start=base + 2 * HOUR_SECONDS)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30), clock=clock)
    mod = mgr.host.get("qb_traffic")
    key = GLOBAL_SERIES_KEY
    obs = [(100, 50, 1, 2), (200, 60, 3, 4), (300, 70, 5, 6)]
    _feed_30s(mod, key, base, obs)
    mod.stop()  # 聚合封口: 完结 hour 落 agg(now 钉在 base+2h, 必然完结)
    parsed = parse_v4_agg_text(_agg_text(tmp_path, key))
    assert len(parsed.hours) == 1 and parsed.hours[0].cov_s == 90
    text = _agg_text(tmp_path, key)
    mod.stop()  # 幂等: 无新行
    assert _agg_text(tmp_path, key) == text
    # dry_run: stop() 短路, 零落盘; 累计器内存照常推进
    mgr2 = _mgr_with_traffic(tmp_path / "dry", QbTraffic(enabled=True, sample_interval=30), clock=clock)
    mod2 = mgr2.host.get("qb_traffic")
    mod2.start(mgr2.ctx, dry_run=True)
    mod2._agg_feed(key, V4Sample(100, 50, 1, 2), base, base, True, 30.0)
    mod2._agg_feed(key, V4Sample(200, 60, 3, 4), base + 30, base + 60, False, 30.0)
    assert mod2._agg_states[key].pending  # 内存累计器照常推进
    mod2.stop()
    assert not os.path.exists(v4_agg_file_path(str(tmp_path / "dry"), key))  # 零落盘


def test_v4_write_io_full_day_2s_interval(tmp_path, monkeypatch):
    """写 IO 实测(2s 档, §09.1): 全局系列一整天 43200 样本, 天文件 append open 恰 144 次/天
    (v2 逐行追加为 43200 次 -> 300x 下降), agg append 恰 24 次(每小时封口 1 次);
    计数器断言防回归。"""
    from datetime import datetime

    day0 = int(datetime(2026, 5, 10).timestamp())
    _mod, c = _drive_full_day(tmp_path, monkeypatch, 2, day0)
    assert c["day0"] == 144  # 86400s / 600s flush = 144(含午夜硬切的收尾落盘)
    assert c["day1"] == 1  # 次日首样本: 1 次
    assert c["agg"] == 24  # 24 个整点小时封口
    assert 43200 // 144 == 300  # 对照 v2 逐行追加 43200 次/天: 300x 下降
    # 数据面抽查: day0 天文件 43200 条 r 记录(interval_s=2, v4 每 flush 一块共 144 块);
    # agg 24 hour 行 + 1 day 行
    parsed = parse_v4_day_text(_dat_text(tmp_path, GLOBAL_SERIES_KEY, v4_epoch_date_str(day0)))
    assert len(parsed.blocks) == 144  # v4 关块谓词: 带 r 行的块每 flush 关闭
    assert all(b.interval_s == 2 for b in parsed.blocks)
    assert sum(len(b.records) for b in parsed.blocks) == 43200
    agg_rows = parse_v4_agg_text(_agg_text(tmp_path, GLOBAL_SERIES_KEY))
    assert len(agg_rows.hours) == 24 and len(agg_rows.days) == 1 and agg_rows.months == ()


def test_v4_write_io_full_day_30s_interval(tmp_path, monkeypatch):
    """写 IO 实测(30s 档, §09.1 对照): flush 次数由 flush_interval 驱动, 同样 144 次/天
    (2880 样本 -> 144 append, 20x 下降于 v2 逐行 2880 次); 采样密度不影响写 IO 面量级
    —— v3 的写 IO 与采样率解耦(批量缓冲), 只与 flush_interval 相关。"""
    from datetime import datetime

    day0 = int(datetime(2026, 5, 10).timestamp())
    _mod, c = _drive_full_day(tmp_path, monkeypatch, 30, day0)
    assert c["day0"] == 144 and c["day1"] == 1 and c["agg"] == 24
    assert 2880 // 144 == 20  # 对照 v2 逐行追加 2880 次/天: 20x 下降(§09.1 口径)
    parsed = parse_v4_day_text(_dat_text(tmp_path, GLOBAL_SERIES_KEY, v4_epoch_date_str(day0)))
    assert len(parsed.blocks) == 144 and all(b.interval_s == 30 for b in parsed.blocks)
    assert sum(len(b.records) for b in parsed.blocks) == 2880


def test_v4_idle_block_stays_open_single_b_row_and_live_tail_identity(tmp_path, monkeypatch):
    """⑥ 空闲块不关(v4 §04 用例 ⑥): 纯空闲系列(数据门有数据 + 零速)跨 flush 时点
    主文件零写入, 封口后天文件恰 1 条 B 行 + 1 条长 z 行; 跨 flush 开放 z 游程的
    LiveTail 复原与落盘重算恒等(块首封口形态); 恢复传输后 r 行 delta <= flush 窗 x 速率"""
    clock = FakeClock()
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30, flush_interval=600), clock=clock)
    mgr.store.server_state = server_state(dl_info_speed=1024, up_info_speed=512)  # 全局保持活跃(隔离单种面)
    seed_store(mgr, [active_torrent("HASH123")])
    st = TrafficV4Store(str(tmp_path))  # 数据门: 预置系列目录含 .dat(有过历史数据)
    day = v4_epoch_date_str(clock.now())
    os.makedirs(os.path.dirname(st.series_day_path("torrent:HASH123", day)), exist_ok=True)
    with open(st.series_day_path("torrent:HASH123", day), "w", encoding="utf-8", newline="\n") as f:
        f.write(f"{HEADER_LINE_V4}\nkey,torrent:HASH123\n")
    rec = mgr.store.by_hash["HASH123"]
    rec.dlspeed = 0
    rec.upspeed = 0  # 纯空闲(零速, totals 照常在)
    mod = mgr.host.get("qb_traffic")
    for _ in range(25):  # t0+30 .. t0+750: 纯空闲系列跨 flush 时点
        clock.advance(30)
        _run_sample(mgr)
    tpath = _v4_path(tmp_path, "torrent:HASH123", clock.now())
    assert tpath.read_text(encoding="utf-8").splitlines() == [HEADER_LINE_V4, "key,torrent:HASH123"]
    # 空闲期主文件零写入; 跨 flush 开放 z 游程的 LiveTail 快照
    tail = mod.live_tail["torrent:HASH123"]
    assert tail.open_run is not None and tail.open_run.kind == "z" and tail.open_run.samples == 25
    tail_slots = v4_live_tail_slots(tail)
    assert len(tail_slots) == 25
    # 恢复传输(非 z 事件) -> 封 z 游程(恰 1 条长 z 行)+ r; flush 落盘
    rec.dlspeed = 512
    rec.downloaded, rec.uploaded = 5_000_300, 3_000_100
    clock.advance(30)  # t0+780
    _run_sample(mgr)
    _flush(mod)
    parsed = parse_v4_day_text(tpath.read_text(encoding="utf-8"))
    assert parsed.bad_lines == 0 and len(parsed.blocks) == 1
    z, r2 = parsed.blocks[0].records
    assert isinstance(z, V4ZeroRun) and z.run_len == 25  # 空闲段恰 1 条长 z 行
    assert (z.dl_total, z.up_total) == (5_000_000, 3_000_000)  # 块首 z 立基线(totals 快照)
    assert isinstance(r2, V4Sample) and r2.dl_total == 5_000_300
    assert 0 <= r2.dl_total - z.dl_total <= 600 * 512  # delta <= flush 窗 x 速率(v4 §01 封顶)
    # LiveTail 复原与落盘重算恒等: z 游程槽逐槽相等
    file_slots = v4_block_slots(parsed.blocks[0])
    assert file_slots[:25] == tuple(tail_slots)
    # 天文件恰 1 条 B 行(纯空闲系列的整段历史 = 单块)
    assert sum(1 for ln in tpath.read_text(encoding="utf-8").splitlines() if ln.startswith("B,")) == 1


def test_v4_non_z_seal_midnight_materializes_idle_b_z_batch(tmp_path, monkeypatch):
    """⑦ 非 z 事件封口(v4 §04 用例 ⑦): 长空闲段恰 1 条长 z 行, 00:00 物化进当日天文件
    (B + z 一批 append, 空闲期主文件零写入); 次日 LiveTail 开放游程跨天接力与落盘重算恒等"""
    clock = FakeClock(start=_local_epoch(23, 57, 40))
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30, flush_interval=10**9), clock=clock)
    mgr.store.server_state = server_state()
    mod = mgr.host.get("qb_traffic")
    t_before = clock.now()
    _run_sample(mgr)  # 23:57:40: 活跃 -> r 进缓冲(块 A)
    _flush(mod)  # 手动 flush: 块 A 落盘(此后空闲期主文件零写入)
    today_file = _v4_path(tmp_path, GLOBAL_SERIES_KEY, t_before)
    base_lines = today_file.read_text(encoding="utf-8")
    mgr.store.server_state = _idle_state()
    for _ in range(4):  # 23:58:10 .. 23:59:40: 空闲(开放 z 游程, 零写入)
        clock.advance(30)
        _run_sample(mgr)
    assert today_file.read_text(encoding="utf-8") == base_lines  # 空闲期主文件零写入
    clock.advance(30)  # 00:00:10(次日): 跨天 -> 封旧日 z 游程(非 z 事件)+ 开新游程
    _run_sample(mgr)
    clock.advance(30)  # 00:00:40: 次日再空闲一轮(新游程推进)
    _run_sample(mgr)
    _flush(mod)  # 旧日 B + z 一批物化 append
    d1 = parse_v4_day_text(today_file.read_text(encoding="utf-8"))
    assert len(d1.blocks) == 2
    assert [type(r) for r in d1.blocks[1].records] == [V4ZeroRun]  # 长空闲段恰 1 条长 z 行
    assert d1.blocks[1].records[0].run_len == 4  # 23:58:10..23:59:40 恰 4 槽
    assert (d1.blocks[1].dl_base, d1.blocks[1].up_base) == (10_000_000, 20_000_000)  # 块首 z 立基线
    # 次日 LiveTail 开放游程(跨天接力)与落盘重算恒等: 快照 = 已封口 z4(records, 已在
    # 当日天文件)+ 开放游程 z2(未来封口形态); 后者与封口落盘后的重算逐槽恒等
    tail = mod.live_tail[GLOBAL_SERIES_KEY]
    assert tail.open_run is not None and tail.open_run.kind == "z" and tail.open_run.samples == 2
    tail_slots = v4_live_tail_slots(tail)
    assert len(tail_slots) == 6
    assert tail_slots[:4] == tuple(v4_block_slots(d1.blocks[1]))  # 已封口 z4: 活尾倒推复原 == 当日文件重算
    mgr.store.server_state = server_state(alltime_dl=10_000_200, alltime_ul=20_000_100)  # 次日恢复传输
    clock.advance(30)  # 00:01:20: 封新 z 游程(2 槽)+ r
    _run_sample(mgr)
    _flush(mod)
    d2 = parse_v4_day_text(_v4_path(tmp_path, GLOBAL_SERIES_KEY, clock.now()).read_text(encoding="utf-8"))
    assert len(d2.blocks) == 1
    z2 = d2.blocks[0].records[0]
    assert isinstance(z2, V4ZeroRun) and z2.run_len == 2
    assert v4_block_slots(d2.blocks[0])[:2] == tuple(tail_slots[-2:])  # 跨天接力: 活尾复原 == 落盘重算


def test_v4_crash_restart_idle_window_is_vacuum(tmp_path, monkeypatch):
    """⑦ 崩溃重启该时段 = 真空(v4 §04 用例 ⑦): 开放 z 游程是空闲期唯一副本, 崩溃即丢
    「在场证明」—— 重启 catch-up 后空闲段 cov_s 缺失, hour 行 avg 不被零速稀释(无偏)"""
    base_t = _local_epoch(10, 0, 0)
    clock = FakeClock(start=base_t)
    mgr1 = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30), clock=clock)
    mgr1.store.server_state = server_state()
    mod1 = mgr1.host.get("qb_traffic")
    _run_sample(mgr1)  # 10:00:00: 活跃 r(rate 1024/2048)
    _flush(mod1)  # 块落盘(hour 未完结)
    mgr1.store.server_state = _idle_state()
    for _ in range(20):  # 10:00:30..10:10:30: 空闲(开放 z 游程滞留内存 = 唯一副本)
        clock.advance(30)
        _run_sample(mgr1)
    # 崩溃: 无 stop(), 模块实例直接丢弃(开放游程与内存信用随之消失)
    mgr2 = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30), clock=clock)
    mod2 = mgr2.host.get("qb_traffic")
    clock.advance(30)  # 10:10:30
    mod2.start(mgr2.ctx, dry_run=False)  # 重启恢复: catch-up 从天文件 raw 补算(空闲段无 raw)
    mgr2.store.server_state = server_state()
    _run_sample(mgr2)  # 10:10:30: 活跃 r —— 块首 gap 630s 超容差 -> 空闲段真空不结算
    clock.freeze(_local_epoch(11, 0, 10))  # 跨到下一小时首样
    mgr2.store.server_state = server_state(alltime_dl=10_100_000, alltime_ul=20_100_000)
    _run_sample(mgr2)  # 11:00:10: 结算 [10:10:30, 11:00:10)(10:00 桶内 2970s)
    _flush(mod2)
    parsed = parse_v4_agg_text(_agg_text(tmp_path, GLOBAL_SERIES_KEY))
    hour_epoch = (int(base_t) // HOUR_SECONDS) * HOUR_SECONDS
    assert len(parsed.hours) == 1 and parsed.hours[0].epoch == hour_epoch
    assert parsed.hours[0].cov_s == 2970  # 空闲段(10:00:30..10:10:00)真空缺失, 不虚记覆盖
    assert parsed.hours[0].dl_avg == 1024  # avg 无偏: 只按有效覆盖加权, 不被零速/缺覆盖稀释


def test_pending_agg_rows_skips_empty_and_zero_coverage_buckets(tmp_path):
    """活尾 pending 行(S7): 空桶不留行 / 零有效覆盖桶 ValueError 逐一跳过(不出行 = null
    语义, 与 _agg_flush_series 同); 无子行时 day/month 两级同样不出行; 合法桶照常产
    hour 行并由它逐级上卷"""
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mod = mgr.host.get("qb_traffic")
    agg = mod._agg_state(GLOBAL_SERIES_KEY)
    agg.pending[_AGG_H0] = []  # 空桶(全 null 覆盖的小时)
    agg.pending[_AGG_H0 + HOUR_SECONDS] = [V4HourSample(100, 50, 1, 2, 0.0)]  # 零有效覆盖
    assert ts_mod._pending_agg_rows(agg, None, now=_AGG_H0 + 2 * HOUR_SECONDS) == ()
    # 对照: 合法桶照常产 hour 行, day/month 两级由它上卷(无子行时两级不出行)
    agg.pending[_AGG_H0 + 2 * HOUR_SECONDS] = [V4HourSample(100, 50, 1, 2, 1800.0)]
    rows = ts_mod._pending_agg_rows(agg, None, now=_AGG_H0 + 3 * HOUR_SECONDS)
    assert [r.kind for r in rows] == ["hour", "day", "month"]
    assert rows[0].cov_s == 1800 and rows[1].epoch == v4_day_epoch(_AGG_H0)


def test_open_run_hour_samples_idle_z_run_emits_zero_hours():
    """开放游程合成(D2/D3): 空闲 z 游程 = credit 段按上一记录速率 + 游程内恒 0;
    totals 逐段摊配到**末端锚点**(不是开启快照); 末端取 last_seen 不推 now(now 再晚
    也不多出段); 每段恰 1 条样本"""
    from auto_qb.core.modules.traffic_sample_mod import OpenRun, SeriesAgg, _open_run_hour_samples

    h0 = _AGG_H0
    agg = SeriesAgg()
    agg.open_credit = (float(h0 + 120), 100, 50, 1000, 2000)  # 上一记录末槽 + 速率 + 快照
    run = OpenRun(
        kind="z",
        start=h0 + 300,
        last_seen=h0 + 3 * HOUR_SECONDS + 600,
        dl_total=1000,
        up_total=2000,
        samples=100,
        last_dl_total=3000,
        last_up_total=4000,
    )
    out = _open_run_hour_samples(agg, run)  # 不接收 now: 末端恒为 last_seen(不推当前时刻)
    # h0 桶: credit 段 180s@100 + 游程首段 3300s@0
    assert out[h0] == [V4HourSample(100, 50, 1000, 2000, 180.0), V4HourSample(0, 0, 1000, 2000, 3300.0)]
    # 整小时游程段: rate 0, totals 沿开启->末端线性摊配(k = 1 / 2)
    assert out[h0 + HOUR_SECONDS] == [V4HourSample(0, 0, 1667, 2667, 3600.0)]
    assert out[h0 + 2 * HOUR_SECONDS] == [V4HourSample(0, 0, 2333, 3333, 3600.0)]
    # 末段 600s: totals 恰为末端锚点(不是开启快照 1000/2000)
    assert out[h0 + 3 * HOUR_SECONDS] == [V4HourSample(0, 0, 3000, 4000, 600.0)]
    assert set(out) == {h0, h0 + HOUR_SECONDS, h0 + 2 * HOUR_SECONDS, h0 + 3 * HOUR_SECONDS}


def test_pending_agg_rows_idle_z_run_fills_tail_hours(tmp_path):
    """活尾合成接线(S2): 空闲 8 小时 z 游程 -> 活尾快照里 8 条 hour 部分行(avg 0 / cov 3600,
    内存行不落盘)+ 当日 day 行 + 当月 month 行; 累计器本体不动(合成只进 pending 副本)"""
    from auto_qb.core.modules.traffic_sample_mod import OpenRun, _pending_agg_rows

    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mod = mgr.host.get("qb_traffic")
    agg = mod._agg_state(GLOBAL_SERIES_KEY)
    h0 = v4_day_epoch(_AGG_H0) + 2 * HOUR_SECONDS  # 当日 02:00 起, 8 小时不跨本地日界
    agg.open_credit = (float(h0), 0, 0, 1000, 2000)
    run = OpenRun("z", h0, h0 + 8 * HOUR_SECONDS, 1000, 2000, 8, 1000, 2000)
    rows = _pending_agg_rows(agg, run, now=h0 + 8 * HOUR_SECONDS)
    hours = [r for r in rows if r.kind == "hour"]
    assert [r.epoch for r in hours] == [h0 + k * HOUR_SECONDS for k in range(8)]
    assert all(r.dl_avg == 0 and r.up_avg == 0 and r.cov_s == HOUR_SECONDS for r in hours)
    assert agg.pending == {}  # 副本语义: 合成段不进累计器
    assert [r for r in rows if r.kind == "day"] == [
        AggRow("day", v4_day_epoch(h0), 0, 0, 0, 0, 1000, 2000, 8 * HOUR_SECONDS)
    ]
    assert [r for r in rows if r.kind == "month"] == [
        AggRow("month", v4_month_epoch(h0), 0, 0, 0, 0, 1000, 2000, 8 * HOUR_SECONDS)
    ]


def test_live_tail_idle_run_publishes_zero_hour_rows_end_to_end(tmp_path, monkeypatch):
    """端到端(S2 出口判据): 全局先出一笔非零(立信用)再一路空闲 2 小时 —— z 游程始终未
    封口, 但 handler 发布的活尾快照里已有 2 条 hour 行(整小时那条 avg 0 / cov 3600),
    即 3d+ 视图不再把空闲段画成「无采样」; 同一快照的 raw 面开放游程照旧在(两面同构)"""
    d0 = v4_day_epoch(_AGG_H0)
    h0 = d0 + 2 * HOUR_SECONDS
    clock = FakeClock(start=h0)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30, flush_interval=600), clock=clock)
    mgr.store.server_state = server_state(dl_info_speed=100, up_info_speed=50, alltime_dl=1000, alltime_ul=2000)
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)  # t=h0: r 记录(立信用, 尚无游程)
    mgr.store.server_state = server_state(dl_info_speed=0, up_info_speed=0, alltime_dl=1000, alltime_ul=2000)
    clock.advance(30)
    _run_sample(mgr)  # t=h0+30: 零样本 -> 开 z 游程(此后一直不封口)
    clock.advance(HOUR_SECONDS)
    _run_sample(mgr)  # t=h0+1h30s
    clock.advance(HOUR_SECONDS)
    _run_sample(mgr)  # t=h0+2h30s
    tail = mod.live_tail[GLOBAL_SERIES_KEY]
    assert tail.open_run is not None and tail.open_run.kind == "z"  # 游程确实没封口
    hours = [r for r in tail.pending_agg if r.kind == "hour"]
    assert [r.epoch for r in hours] == [h0, h0 + HOUR_SECONDS, h0 + 2 * HOUR_SECONDS]
    # 整小时那条: 全程空闲 -> avg 0, cov 满桶(修复前它整条不存在 = 图面 null)
    assert (hours[1].dl_avg, hours[1].up_avg, hours[1].cov_s) == (0, 0, HOUR_SECONDS)
    assert (hours[2].dl_avg, hours[2].cov_s) == (0, 30)  # 尾部 30s 部分桶照常出 0 行
    # 首小时: credit 段 30s@100 摊进满桶 -> round(3000/3600) = 1, cov 仍是满桶
    assert (hours[0].dl_avg, hours[0].cov_s) == (1, HOUR_SECONDS)
    assert [r.epoch for r in tail.pending_agg if r.kind == "day"] == [d0]


def test_apply_interval_without_main_tick_uses_raw_interval(tmp_path):
    """main_tick 未配置(0 / 缺省)-> 生效间隔 = sample_interval 原值: 不做倍数取整也不告警
    (取整语义只在主循环节拍存在时成立)"""
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.config.main_tick = 0.0
    mod = mgr.host.get("qb_traffic")
    assert mod._apply_interval(mgr.config.qb_traffic) == 30.0
    assert mod._effective_interval == 30.0  # 首轮只立基线, 不开关块


def test_close_blocks_for_interval_change_skips_runless_and_unopened(tmp_path):
    """改间隔关块(§3.5): 只封「有开放块」的游程与缓冲 —— 无缓冲的开放游程不封(将成为新块
    首记录), 未开块的 shell 缓冲不 flush(零记录零块状态, 关块无对象)"""
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mod = mgr.host.get("qb_traffic")
    run_only, shell = "torrent:RUNONLY", "torrent:SHELL"
    mod._open_runs[run_only] = ts_mod.OpenRun(
        kind="z",
        start=1000.0,
        last_seen=1030.0,
        dl_total=1,
        up_total=2,
        samples=2,
        last_dl_total=1,
        last_up_total=2,
    )
    mod._buffers[shell] = ts_mod.BlockBuffer(
        start_epoch=None,
        interval_s=0,
        date_str=None,
        records=[],
        slots=0,
        prev_actual_ts=None,
        projected_ts=0.0,
        header_written=False,
        dl_base=None,
        up_base=None,
        has_r_row=False,
        last_dl_total=None,
        last_up_total=None,
    )
    mod._close_blocks_for_interval_change()
    assert run_only in mod._open_runs  # 无缓冲: 不封口(留作新块首记录)
    assert mod._buffers[shell].records == []  # shell 缓冲零操作


def test_torrent_active_missing_fields_takes_null_run(tmp_path, monkeypatch):
    """活跃种子关键字段缺失(活跃过滤已过) -> n 游程槽(不写 0 不吞样本): 缓冲里零记录,
    游程记 n; DEBUG 留痕说明本轮按 null 处理"""
    clock = FakeClock()
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30), clock=clock)
    mgr.store.server_state = server_state()
    seed_store(mgr, [active_torrent("HASH123", uploaded=None)])
    mod = mgr.host.get("qb_traffic")
    key = "torrent:HASH123"
    with capture_logs("auto_qb.core.modules.traffic_sample_mod") as cap:
        _run_sample(mgr)
    run = mod._open_runs[key]
    assert run.kind == "n" and run.samples == 1
    assert "按 n 游程槽处理" in cap.text
    assert key not in mod._buffers  # null 点不产记录(绝不用 0 充数)


def test_torrent_zero_speed_readings_drift_defensive_raw_row(tmp_path, monkeypatch):
    """零速过滤与字段读数口径漂移的防御支: 过滤判零但读数非零 -> 按 r 记录处理(绝不把活跃
    读数吞进游程, 否则该段速率永久丢失)"""
    clock = FakeClock()
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30), clock=clock)
    mgr.store.server_state = server_state()
    seed_store(mgr, [_FlipSpeedTorrent()])
    mod = mgr.host.get("qb_traffic")
    key = "torrent:HASH123"
    mod._has_data.add(key)  # 数据门放行(本用例不落盘造目录)
    _run_sample(mgr)
    assert key not in mod._open_runs  # 不误开游程
    recs = mod._buffers[key].records
    assert [type(r) for r in recs] == [V4Sample] and recs[0].dl_rate == 512


def test_parser_never_emits_zero_slot_block():
    """零槽块生产可达性实测(issue 26-11-01-0050): 解析器只在块内有记录时产块

    _close() 的 `cur_start is not None and cur_records` 双闸让「B 行后无任何记录」
    的零记录块不进入 V4ParsedDay.blocks —— 空块支 `if not slots: continue` 是防御
    死码(continue->break 在解析产物上恒等价), 不是可补守阵的真洞。
    """
    text = "\n".join([HEADER_LINE_V4, "key,global", "B,1000,30", "B,2000,30,100,200", "r,10,20,0,0"]) + "\n"
    parsed = parse_v4_day_text(text)
    assert parsed.bad_lines == 0
    assert len(parsed.blocks) == 1  # 首个零记录 B 块被丢弃, 只余有记录块
    assert parsed.blocks[0].start_epoch == 2000
    assert all(block.records for block in parsed.blocks)
    # 文件尾的 B 行(无记录)同样不产块
    assert parse_v4_day_text(f"{HEADER_LINE_V4}\nB,3000,30\n").blocks == ()


def test_stop_early_return_when_disabled_or_no_data_dir(tmp_path):
    """stop() 前置闸(§3.4): qb_traffic 段缺失 / data_dir 为空 -> 零操作(不封游程不 flush);
    dry_run 短路由 test_stop_dry_run_short_circuit 钉住"""
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mod = mgr.host.get("qb_traffic")
    mod._persistence_on = True
    mod._open_runs[GLOBAL_SERIES_KEY] = ts_mod.OpenRun(
        kind="z",
        start=1000.0,
        last_seen=1030.0,
        dl_total=1,
        up_total=2,
        samples=2,
        last_dl_total=1,
        last_up_total=2,
    )
    mgr.config.qb_traffic = None
    mod.stop()
    assert GLOBAL_SERIES_KEY in mod._open_runs  # 段缺失: 零操作
    mgr.config.qb_traffic = QbTraffic(enabled=True, sample_interval=30)
    mgr.config.data_dir = ""
    mod.stop()
    assert GLOBAL_SERIES_KEY in mod._open_runs  # data_dir 为空: 零操作


def test_w5_blockhead_zero_drift_run_cursor_roundtrip_and_agg(tmp_path, monkeypatch):
    """块首游程零漂移支(常态形态): 游标标称推进(不反向/不塌缩) + 块首游程槽位端点含
    (agg 逐区间 dt 断言) —— _append_record_128 / _record_slots_9/12 / _agg_feed_8"""
    clock = FakeClock()
    mgr = _w5_mgr(tmp_path, monkeypatch, clock)
    mgr.store.server_state = server_state(alltime_dl=5_000_000, alltime_ul=3_000_000)
    mod = mgr.host.get("qb_traffic")
    t0 = clock.now()
    _run_sample(mgr)  # r@t0(块 A)
    _flush(mod)  # 块 A 落盘关块, 信用滞留
    mgr.store.server_state = _idle_state(alltime_dl=5_000_000, alltime_ul=3_000_000)
    for _ in range(3):  # 空闲 z 游程 3 样本(t0+30..t0+90)
        clock.advance(30)
        _run_sample(mgr)
    mod._seal_run(GLOBAL_SERIES_KEY)  # 封 z -> 块首 z(run_len 3, 零漂移: span 60 = 标称)
    assert mod._buffers[GLOBAL_SERIES_KEY].projected_ts == t0 + 90.0  # 游标 = anchor+(run_len-1)*interval
    mgr.store.server_state = server_state(alltime_dl=5_000_300, alltime_ul=3_000_100)
    clock.advance(30)
    _run_sample(mgr)  # t0+120: r 零漂移(游标标称推进 -> 不写 dt)
    _flush(mod)
    parsed = _v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now())
    assert parsed.bad_lines == 0
    blocks = [b for b in parsed.blocks if b.start_epoch == int(t0 + 30)]
    assert len(blocks) == 1
    z, r2 = blocks[0].records
    assert isinstance(z, V4ZeroRun) and z.run_len == 3 and z.dt_ms is None
    assert isinstance(r2, V4Sample) and r2.dt_ms is None
    # agg 面: 块首游程槽位 [anchor..cursor] 端点含 -> 游程内恰 2 个 30s 零速区间; 逐区间 dt 断言
    h0 = int(t0) // HOUR_SECONDS * HOUR_SECONDS
    samples = mod._agg_states[GLOBAL_SERIES_KEY].pending[h0]
    assert [round(s.dt_s, 6) for s in samples] == [30.0, 30.0, 30.0, 30.0]  # r 信用+2 游程区间+r 引导
    assert round(sum(s.dt_s for s in samples), 6) == 120.0


def test_w5_blockhead_run_rollback_clamp_dt_min_1(tmp_path, monkeypatch):
    """块首游程回拨钳制: 末端仅高出 B.start 亚毫秒 -> dt_ms = max(1, 实测) = 1 —— _append_record_113"""
    clock = FakeClock()
    mgr = _w5_mgr(tmp_path, monkeypatch, clock)
    mgr.store.server_state = server_state()
    mod = mgr.host.get("qb_traffic")
    t0 = clock.now()
    _run_sample(mgr)
    _flush(mod)
    mgr.store.server_state = _idle_state()
    clock.advance(30.0002)
    _run_sample(mgr)  # z@t0+30.0002(B.start = t0+30, 末端仅 +0.2ms)
    clock.advance(0.0002)
    _run_sample(mgr)  # z@t0+30.0004(run_len 2)
    clock.advance(30)
    mgr.store.server_state = server_state()
    _run_sample(mgr)  # r 封 z: span = 0.4ms -> dt_ms = max(1, round(0.4)) = 1
    z = mod._buffers[GLOBAL_SERIES_KEY].records[0]
    assert isinstance(z, V4ZeroRun) and z.dt_ms == 1


def test_w5_nonhead_zero_drift_run_no_dt(tmp_path, monkeypatch):
    """非块首多槽游程标称 = run_len*interval: 零漂移不写 dt —— _append_record_142"""
    clock = FakeClock()
    mgr = _w5_mgr(tmp_path, monkeypatch, clock)
    mgr.store.server_state = server_state()
    mod = mgr.host.get("qb_traffic")
    t0 = clock.now()
    _run_sample(mgr)
    _flush(mod)
    mgr.store.server_state = _idle_state()
    for _ in range(2):  # z1(t0+30, t0+60)
        clock.advance(30)
        _run_sample(mgr)
    clock.advance(30)
    mgr.store.server_state = server_state()
    _run_sample(mgr)  # t0+90: r 封 z1 -> 块首游程(dt 60000, 游标复位)
    mgr.store.server_state = _idle_state()
    for _ in range(3):  # z2(t0+120..t0+180) 非块首
        clock.advance(30)
        _run_sample(mgr)
    clock.advance(30)
    mgr.store.server_state = server_state()
    _run_sample(mgr)  # t0+210: r 封 z2(非块首: 标称 90, 零漂移)
    z1, r1, z2, r2 = mod._buffers[GLOBAL_SERIES_KEY].records
    assert isinstance(z1, V4ZeroRun) and z1.dt_ms is None  # 块首零漂移(常规采样间隔)
    assert isinstance(z2, V4ZeroRun) and z2.dt_ms is None  # 非块首零漂移: 不写 dt(变异在此破)
    assert isinstance(r2, V4Sample) and r2.dt_ms is None  # 游标标称推进


def test_w5_n_prefix_split_zero_run_no_crash(tmp_path, monkeypatch):
    """n-only 前缀拆块: 拆块实参携带 end_ts —— 新块首为 run_len>=2 z 游程不崩
    (_append_record_54; 真实序列: 断连 -> 重连空闲 -> 恢复传输)"""
    clock = FakeClock()
    mgr = _w5_mgr(tmp_path, monkeypatch, clock)
    mod = mgr.host.get("qb_traffic")
    t0 = clock.now()
    mgr.store.server_state = server_state(alltime_dl=None)  # 关键字段缺失 -> n 游程
    for _ in range(2):
        clock.advance(30)
        _run_sample(mgr)
    mgr.store.server_state = _idle_state()  # 重连空闲: n->z 换型封 n(run_len 2), z 游程开
    for _ in range(2):
        clock.advance(30)
        _run_sample(mgr)
    mgr.store.server_state = server_state()  # 恢复传输: r 封 z -> n 前缀拆块, z 成新块首
    clock.advance(30)
    _run_sample(mgr)  # 变异(end_ts=None)在新块首游程 span 处 TypeError
    _flush(mod)
    parsed = _v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now())
    assert parsed.bad_lines == 0 and len(parsed.blocks) == 2
    b1, b2 = parsed.blocks
    assert (b1.dl_base, b1.up_base) == (None, None)  # n 前缀 3 列 B 无基线块
    assert [r.run_len for r in b1.records] == [2] and isinstance(b1.records[0], V4NullRun)
    assert len(b2.records) == 2 and isinstance(b2.records[0], V4ZeroRun) and b2.records[0].run_len == 2
    assert isinstance(b2.records[1], V4Sample)


def test_w5_counter_reset_split_zero_run_no_crash(tmp_path, monkeypatch):
    """计数器重置关块: 拆块实参携带 end_ts —— 重置记录为 run_len>=2 z 游程不崩
    (_append_record_65; 真实序列: z 开启快照低于块内最近 totals)"""
    clock = FakeClock()
    mgr = _w5_mgr(tmp_path, monkeypatch, clock)
    mod = mgr.host.get("qb_traffic")
    mgr.store.server_state = server_state(alltime_dl=5_000_000, alltime_ul=3_000_000)
    _run_sample(mgr)
    clock.advance(30)
    mgr.store.server_state = server_state(alltime_dl=5_100_000, alltime_ul=3_100_000)
    _run_sample(mgr)  # 块内最近 totals 5.1M/3.1M
    mgr.store.server_state = _idle_state(alltime_dl=100, alltime_ul=50)  # 空闲期计数器回落
    for _ in range(2):  # z 游程(开启快照 100/50)
        clock.advance(30)
        _run_sample(mgr)
    mgr.store.server_state = server_state(alltime_dl=200, alltime_ul=60)
    clock.advance(30)
    _run_sample(mgr)  # r 封 z -> z 记录 totals 100 < 5.1M -> 强制关块重开(变异在拆块实参)
    _flush(mod)
    parsed = _v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now())
    assert parsed.bad_lines == 0 and len(parsed.blocks) == 2
    b2 = parsed.blocks[1]
    assert (b2.dl_base, b2.up_base) == (100, 50)  # 新块基线 = 重置后 totals
    assert isinstance(b2.records[0], V4ZeroRun) and b2.records[0].run_len == 2
    assert isinstance(b2.records[1], V4Sample)


def test_w5_day_boundary_seal_uses_current_readings(tmp_path, monkeypatch):
    """跨天封口末端锚点用本轮读数(docstring 明文): 增长 totals 的全局 z 游程跨 00:00 封口
    -> z 行末端列 = 本轮读数 —— _advance_run_10/11/13/14"""
    clock = FakeClock(start=_w5_ts(2026, 6, 1, 23, 58, 0))
    mgr = _w5_mgr(tmp_path, monkeypatch, clock)
    mod = mgr.host.get("qb_traffic")
    mgr.store.server_state = _idle_state(alltime_dl=1000, alltime_ul=5000)
    for i in range(1, 6):  # 23:58:00..00:00:00(5 样本, 末样本跨 0 点): totals 逐轮增长(合法形态)
        if i > 1:
            clock.advance(30)
        mgr.store.server_state = _idle_state(alltime_dl=1000 + i * 400, alltime_ul=5000 + i * 200)
        _run_sample(mgr)
    _flush(mod)
    parsed = _v4_read(tmp_path, GLOBAL_SERIES_KEY, _w5_ts(2026, 6, 1, 23, 59, 0))
    assert parsed.bad_lines == 0 and len(parsed.blocks) == 1
    z = parsed.blocks[0].records[0]
    assert isinstance(z, V4ZeroRun) and z.run_len == 4
    assert z.dl_total_end == 1000 + 5 * 400  # 本轮(00:00:00)读数, 非上一轮跟踪值
    assert z.up_total_end == 5000 + 5 * 200


def test_w5_dry_run_full_chain_zero_write(tmp_path, monkeypatch):
    """dry-run 全链路零落盘(观测写盘属真实副作用): 主文件/agg/裁剪/限速历史全静默,
    单种数据门不开(不开游程) —— on_task_line_5 / _sample_global_24 / _torrent_has_data_8/9
    / _agg_append_3 / _agg_trim_1"""
    h0 = int(1_700_000_000) // HOUR_SECONDS * HOUR_SECONDS
    clock = FakeClock(start=h0 - 7200 + 10)
    # data_dir 先于模块构造注入: _limits_rec 构造期取值(observe 的 persistence_on 面才可达)
    mgr = make_manager(str(tmp_path / "state.json"), data_dir=str(tmp_path), clock=clock)
    mgr.client = FakeClient()
    mgr.config.qb_traffic = QbTraffic(enabled=True, sample_interval=30, flush_interval=60, rollup_window=60.0)
    st = TrafficV4Store(str(tmp_path))
    st.append_agg_rows(GLOBAL_SERIES_KEY, (AggRow("hour", h0 - 10800, 7, 9, 3, 4, 500, 600, 3600), ))
    day = v4_epoch_date_str(clock.now())
    os.makedirs(os.path.dirname(st.series_day_path("torrent:A1", day)), exist_ok=True)
    with open(st.series_day_path("torrent:A1", day), "w", encoding="utf-8", newline="\n") as f:
        f.write(f"{HEADER_LINE_V4}\nkey,torrent:A1\n")  # A1 有历史数据: 数据门在真实运行会开
    mgr.store.by_hash["A1"] = active_torrent("A1", dlspeed=0, upspeed=0)
    mgr.store.by_hash["A2"] = active_torrent("A2")  # 活跃种子: 内存照常推进
    mod = mgr.host.get("qb_traffic")
    mod.start(mgr.ctx, dry_run=True)

    def snapshot():
        root = tmp_path / "qb-traffic-v4"
        out = {}
        for dirpath, _dirs, files in os.walk(root):
            for name in files:
                p = os.path.join(dirpath, name)
                out[os.path.relpath(p, root)] = open(p, "rb").read()
        return out

    before = snapshot()
    mgr.store.server_state = server_state(up_rate_limit=100, dl_rate_limit=50)
    mod.on_task_line(False)  # t0: r(时钟线首拍即采)
    clock.advance(30)
    mod.on_task_line(False)  # t0+30: r(信用结算)
    clock.freeze(h0 - 3600 + 30)  # 跳到 hour(h0-7200) 完结之后
    mod.on_task_line(False)  # 采样 + flush 驱动: hour 封口(agg append/trim 门)+ 内存推进
    assert snapshot() == before  # 零新文件零改写(agg append/裁剪/主文件/限速历史全静默)
    assert "torrent:A1" not in mod._open_runs  # 数据门 dry-run 不开(不开游程)
    assert "torrent:A2" in mod.latest and mod.latest["torrent:A2"].dl_rate == 512  # 内存照常


def test_w5_problem_torrents_do_not_truncate_round(tmp_path, monkeypatch):
    """单种采样轮不被问题种子截断: 从未传输/空闲游程/缺字段活跃/缺字段空闲在前,
    健康种子在后照常出 r; 连续两轮 null 不崩 —— _sample_torrents_44/41/25/57/22"""
    clock = FakeClock()
    mgr = _w5_mgr(tmp_path, monkeypatch, clock)
    st = TrafficV4Store(str(tmp_path))
    day = v4_epoch_date_str(clock.now())
    for h in ("A1", "A3"):  # 有历史数据(数据门开)
        os.makedirs(os.path.dirname(st.series_day_path(f"torrent:{h}", day)), exist_ok=True)
        with open(st.series_day_path(f"torrent:{h}", day), "w", encoding="utf-8", newline="\n") as f:
            f.write(f"{HEADER_LINE_V4}\nkey,torrent:{h}\n")
    t2 = active_torrent("A2")  # 活跃缺字段: null 游程(字段事后置 None, FakeTorrent 构造要数值)
    t2.downloaded = None
    t3 = active_torrent("A3", dlspeed=0, upspeed=0)  # 空闲有数据缺字段
    t3.downloaded = None
    seed_store(
        mgr,
        [
            active_torrent("A0", dlspeed=0, upspeed=0),  # 从未传输(无目录)
            active_torrent("A1", dlspeed=0, upspeed=0),  # 空闲有数据: 首轮开 z 游程
            t2,
            t3,
            active_torrent("A4"),  # 健康活跃
        ],
    )
    mgr.store.server_state = server_state()
    mod = mgr.host.get("qb_traffic")
    t0 = clock.now()
    _run_sample(mgr)
    assert "torrent:A4" in mod.latest and mod.latest["torrent:A4"].dl_rate == 512
    assert "torrent:A1" in mod._open_runs and mod._open_runs["torrent:A1"].kind == "z"
    clock.advance(30)
    _run_sample(mgr)  # 第二轮: A1 空闲推进/A2 连续 null(变异在 ts)/A4 照常
    assert mod.latest["torrent:A4"].ts == t0 + 30  # 健康种子每轮都被采到


def test_w5_single_direction_global_records_raw(tmp_path, monkeypatch):
    """零速判(方向性样本常态): 仅单方向活跃的全局轮出 r 不进 z 游程 —— _sample_global_25"""
    clock = FakeClock()
    mgr = _w5_mgr(tmp_path, monkeypatch, clock)
    mod = mgr.host.get("qb_traffic")
    mgr.store.server_state = server_state(dl_info_speed=0, up_info_speed=2048)
    _run_sample(mgr)
    mgr.store.server_state = server_state(dl_info_speed=1024, up_info_speed=0)
    clock.advance(30)
    _run_sample(mgr)
    recs = mod._buffers[GLOBAL_SERIES_KEY].records
    assert [(r.dl_rate, r.up_rate) for r in recs] == [(0, 2048), (1024, 0)]  # 两轮都出 r
    assert GLOBAL_SERIES_KEY not in mod._open_runs  # 不开 z 游程
    assert mod.latest[GLOBAL_SERIES_KEY].up_rate == 0  # latest 照常推进


def test_w5_active_filter_1bps_boundary(tmp_path, monkeypatch):
    """活跃过滤边界: dlspeed=1 / upspeed=1(1 B/s 合法读数)不被当空闲 ——
    _sample_torrents_5/7(已开游程形态: 应封口 + r)"""
    clock = FakeClock()
    mgr = _w5_mgr(tmp_path, monkeypatch, clock)
    st = TrafficV4Store(str(tmp_path))
    day = v4_epoch_date_str(clock.now())
    os.makedirs(os.path.dirname(st.series_day_path("torrent:HASHA", day)), exist_ok=True)
    with open(st.series_day_path("torrent:HASHA", day), "w", encoding="utf-8", newline="\n") as f:
        f.write(f"{HEADER_LINE_V4}\nkey,torrent:HASHA\n")
    tor = active_torrent("HASHA", dlspeed=0, upspeed=0)
    seed_store(mgr, [tor])
    mgr.store.server_state = server_state()
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)  # 空闲: z 游程开
    assert "torrent:HASHA" in mod._open_runs
    tor.dlspeed = 1  # 1 B/s 合法读数: 活跃 -> 封 z + r
    clock.advance(30)
    _run_sample(mgr)
    assert mod.latest["torrent:HASHA"].dl_rate == 1
    assert "torrent:HASHA" not in mod._open_runs
    tor.dlspeed = 0
    tor.upspeed = 0
    clock.advance(30)
    _run_sample(mgr)  # 再空闲: z 游程重开
    tor.upspeed = 1  # up 位 1 B/s: 同判据
    clock.advance(30)
    _run_sample(mgr)
    assert mod.latest["torrent:HASHA"].up_rate == 1


def test_w5_interval_change_closes_idle_block(tmp_path, monkeypatch):
    """改间隔关块覆盖纯空闲块(z/n): 旧块落盘 + 新块带新 interval(新旧数据分块各有 interval)
    —— _close_blocks_for_interval_change_11/13/14"""
    clock = FakeClock()
    mgr = _w5_mgr(tmp_path, monkeypatch, clock)
    mgr.store.server_state = server_state(alltime_dl=5_000_000, alltime_ul=3_000_000)
    mod = mgr.host.get("qb_traffic")
    t0 = clock.now()
    _run_sample(mgr)
    _flush(mod)
    mgr.store.server_state = _idle_state(alltime_dl=5_000_000, alltime_ul=3_000_000)
    for _ in range(2):
        clock.advance(30)
        _run_sample(mgr)
    mod._seal_run(GLOBAL_SERIES_KEY)  # 封 z1 -> 纯空闲块(块首 z, 无 r 行)
    mgr.config.qb_traffic = QbTraffic(enabled=True, sample_interval=45, flush_interval=10**9)
    mgr.store.server_state = _idle_state(alltime_dl=5_000_300, alltime_ul=3_000_100)
    for _ in range(2):  # 改间隔后空闲(45s 档)
        clock.advance(45)
        _run_sample(mgr)
    mgr.store.server_state = server_state(alltime_dl=5_000_600, alltime_ul=3_000_200)
    clock.advance(45)
    _run_sample(mgr)  # r 封 z2 -> 新块首(45s 档)
    _flush(mod)
    parsed = _v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now())
    assert parsed.bad_lines == 0
    assert [b.interval_s for b in parsed.blocks] == [30.0, 30.0, 45.0]  # 块A/纯空闲块(旧interval)/新块(新interval)
    assert [r.run_len for r in parsed.blocks[1].records] == [2]
    assert isinstance(parsed.blocks[2].records[0], V4ZeroRun)


def test_w5_interval_change_audit_log_and_first_round_silent(tmp_path, monkeypatch):
    """采样率变化审计 INFO: 首轮不虚假告「变化」/ 真变化必留痕 ——
    __init___12(_effective_interval 初值) / _apply_interval_52"""
    clock = FakeClock()
    mgr = _w5_mgr(tmp_path, monkeypatch, clock)
    mgr.store.server_state = server_state()
    mod = mgr.host.get("qb_traffic")
    with capture_logs("auto_qb.core.modules.traffic_sample_mod") as cap1:
        _run_sample(mgr)
    assert "采样率变化" not in cap1.text  # 首轮只立基线: 无虚假「变化」INFO
    mgr.config.qb_traffic = QbTraffic(enabled=True, sample_interval=45, flush_interval=10**9)
    with capture_logs("auto_qb.core.modules.traffic_sample_mod") as cap2:
        clock.advance(30)
        _run_sample(mgr)
    assert "采样率变化" in cap2.text  # 改间隔关块留痕口径


def test_w5_live_tail_no_buffer_interval_contract(tmp_path, monkeypatch):
    """无块时活尾 interval_s 取当前生效采样间隔(LiveTail 契约)—— _publish_live_tail_63"""
    clock = FakeClock()
    mgr = _w5_mgr(tmp_path, monkeypatch, clock)
    mgr.store.server_state = _idle_state()
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)  # 首轮空闲: 开放 z 游程、无任何记录(无缓冲)
    tail = mod.live_tail[GLOBAL_SERIES_KEY]
    assert not tail.block_open and tail.open_run is not None
    assert tail.interval_s == 30.0  # 契约: 无块取生效间隔(非退化 1)
    slots = v4_live_tail_slots(tail)
    assert slots[0].dt_s == 30.0  # 单槽 dt_s = interval(非 1)
    assert slots[0].ts == float(int(tail.open_run.start))


def test_w5_live_tail_interval_change_reset_window_uses_effective(tmp_path, monkeypatch):
    """改间隔复位窗口内无块活尾 interval_s 取当前生效间隔(非陈旧旧块值)——
    LiveTail.interval_s 契约(traffic_store.py:511); 变异 _publish_live_tail__mutmut_59 方向与此一致(疑等价变异, 复核销账)"""
    clock = FakeClock()
    mgr = _w5_mgr(tmp_path, monkeypatch, clock)
    mgr.store.server_state = server_state(alltime_dl=5_000_000, alltime_ul=3_000_000)
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)  # 首轮 r: 开块 interval=30
    buf = mod._buffers[GLOBAL_SERIES_KEY]
    assert buf.start_epoch is not None and buf.interval_s == 30.0
    mgr.config.qb_traffic = QbTraffic(enabled=True, sample_interval=45, flush_interval=10**9)
    mgr.store.server_state = _idle_state(alltime_dl=5_000_000, alltime_ul=3_000_000)
    clock.advance(30)
    _run_sample(mgr)  # 改间隔: 关块复位 -> 本轮 z 游程无块
    buf = mod._buffers[GLOBAL_SERIES_KEY]
    assert buf.start_epoch is None  # 复位窗口: 无开放块
    assert buf.interval_s == 30.0  # 残留旧块值(_reset_block 8 字段不含 interval_s)
    tail = mod.live_tail[GLOBAL_SERIES_KEY]
    assert not tail.block_open and tail.open_run is not None
    assert tail.interval_s == 45.0  # 契约: 无块取当前生效间隔(非陈旧 30)
    assert v4_live_tail_slots(tail)[0].dt_s == 45.0


def test_w5_recover_midday_restart_catchup_and_open_hour(tmp_path, monkeypatch):
    """午间重启恢复综合守阵: 水位前小时不重算不截断 / 完结小时补算 / 开放小时重建 pending
    / 当日累计器重建且当日不出补算行 —— _recover_series_81/93 / _catch_up_level_11/18"""
    now = _w5_ts(2026, 6, 3, 11, 50, 30)
    wm_hour = int(_w5_ts(2026, 6, 2, 10, 0, 0))
    st = TrafficV4Store(str(tmp_path))
    st.append_agg_rows(
        GLOBAL_SERIES_KEY,
        (
            AggRow("hour", wm_hour, 100, 200, 50, 80, 1000, 2000, 3600),
            AggRow("day", int(_w5_ts(2026, 6, 2, 0, 0, 0)), 100, 200, 50, 80, 1000, 2000, 3600),
        ),
    )
    st.append_records(
        GLOBAL_SERIES_KEY,
        "2026-06-02",
        (int(_w5_ts(2026, 6, 2, 9, 0, 10)), 30),
        (V4Sample(100, 50, 1000, 2000), V4Sample(100, 50, 1100, 2100)),
        (1000, 2000),
    )  # 水位前小时(09:00 <= wm 10:00): 不重算
    st.append_records(
        GLOBAL_SERIES_KEY,
        "2026-06-03",
        (int(_w5_ts(2026, 6, 3, 8, 0, 10)), 30),
        (V4Sample(100, 50, 1200, 2200), V4Sample(100, 50, 1300, 2300)),
        (1200, 2200),
    )  # 今日已完结小时 08:00: 补算
    st.append_records(
        GLOBAL_SERIES_KEY,
        "2026-06-03",
        (int(_w5_ts(2026, 6, 3, 11, 30, 10)), 30),
        (V4Sample(100, 50, 3000, 4000), V4Sample(100, 50, 3100, 4100)),
        (3000, 4000),
    )  # 今日开放小时 11:00: pending 重建
    clock = FakeClock(start=now)
    mgr = _w5_mgr(tmp_path, monkeypatch, clock)
    mod = mgr.host.get("qb_traffic")
    mod.start(mgr.ctx, dry_run=False)
    parsed = parse_v4_agg_text(_agg_text(tmp_path, GLOBAL_SERIES_KEY))
    assert [h.epoch for h in parsed.hours] == [wm_hour, int(_w5_ts(2026, 6, 3, 8, 0, 0))]  # 补算恰 1 小时
    assert [d.epoch for d in parsed.days] == [int(_w5_ts(2026, 6, 2, 0, 0, 0))]  # 当日不出补算日行
    assert mod.recovery_stats["hours"] == 1
    h11 = int(_w5_ts(2026, 6, 3, 11, 0, 0))
    pending = mod._agg_states[GLOBAL_SERIES_KEY].pending[h11]
    assert len(pending) == 1 and pending[0].dt_s == 30  # 开放小时数据保留
    assert mod._agg_states[GLOBAL_SERIES_KEY].day_epoch == int(_w5_ts(2026, 6, 3, 0, 0, 0))  # 当日累计器重建
    clock.advance(30)
    mgr.store.server_state = server_state()
    _run_sample(mgr)  # 恢复后首轮采样不崩(pending=None 变异在 publish 处 TypeError)
