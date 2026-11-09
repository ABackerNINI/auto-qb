"""test_traffic_sample_store 测试计划: qB 口径流量采样器(plan 26-10-03-0946 方案C P1 采样器核心 + §06 配置键
+ plan 26-10-04-1957 S2a 写侧/S2b 聚合与恢复 + plan 26-10-05-2200 v4 换代 B2 写侧状态机与结算)

## 测试计划(每个测试函数一条)
- test_zrun_cap_safety_valve_seals_at_day_level: 天级保险闸(N4): 86400 样本(1s 档)触闸封口防溢出,
  正常空闲段不应触闸; 游程 dt 链跨度 = 全天 < ZRUN_FLUSH_S
- test_dt_drift_boundary_family: tol 边界族(§2.3 判据=累积漂移) —— 压线行(恰 250ms)不写 dt / 超线行写实测 dt 并
  自然复位 / 稳态小漂移(150ms/行)退化周期写 / 空载(等间隔)零 dt 行; 单块全序列 roundtrip 与实测一致
  (v4 关块谓词下块随 flush 关闭会重锚游标, 故中途断言读缓冲、末尾一次 flush 落盘)
- test_buffer_slot_cap_3600_early_flush: Q3 保险闸: 缓冲槽 >= 3600 提前单独 flush(v4 带 r 行的块随闸值关闭)
- test_flush_oserror_discards_block_warns_once: 落盘失败(OSError)不上抛、连续失败只告警一次;
  失败块丢弃并复位块状态(dt 链卫生: 下次成功写起新块)
- test_flush_all_drops_shell_buffers: 内存卫生: 无开放块无待写记录无游程且未采样的 shell 缓冲被清除

聚合分层与恢复(plan 26-10-04-1957 S2b §04):
- test_agg_hour_row_dt_weighted_across_hour_boundary: hour 行产出 —— 前向记账逐区间入账,
  信用区间跨小时界自然拆分; avg = dt 加权 / max 逐记录取大 / totals 级末快照 / cov_s = Σ桶内覆盖;
  未完结小时留累计器; hour 行并入 day 累计器(严格逐级)
- test_agg_flush_subsecond_hour_rolls_up_without_raise: 亚秒小时桶的日封口(2026-10-13 真机
  「逐级聚合无有效覆盖」回归)—— 迟到补记重建的小时桶只带亚秒残余覆盖时 cov_s 下限 1,
  day 封口不再抛异常(修复前 Σcov_s = 0 -> _agg_flush_series 每轮 flush 抛且整批 agg 行丢弃)
- test_agg_reseal_merges_late_credit_keeps_full_coverage: 已封小时被迟到补记重建后再封走**合流**
  (2026-10-13 真机「重封替换丢覆盖」回归)—— 末行 cov 回到整小时、avg 按两段 cov 加权,
  day 累计器同持合流行; 修复前替换语义只留残余(真机日行 cov_s 44712 vs 全量 86400)
- test_agg_closed_day_reseal_merges_via_closed_stub: 已关日的 hour 迟到重封走**已关日存根**合流
  (issue 26-11-07-0527 R1#63)—— 日关闭复位累计器后残余行不再替换全量行(hour cov 回 3600,
  avg/max/totals 合流口径), 日行由存根重建, 背日行不重开日累计器
- test_agg_month_boundary_reseal_rebuilds_day_and_month_rows: 月界同构面(R1#63)—— 日/月双层
  同批复位后 hour 迟到重封, hour/day/month 三行全部经存根合流/重建(修复前全塌到残余 cov 1),
  月行重建不丢其他天(1/30 行原样)
- test_agg_backdated_reseal_leaves_open_day_accumulator_alone: 背日重封不碰开放日累计器(R1#63
  修法面)—— 开放日照常自然封口出完整日行, 不被背日行提前级联误关(修复前会写缺日行)
- test_agg_flush_all_isolates_series_error_and_resets: 逐系列隔离与善后(单系列封口抛错只告警
  该系列 + 重置其累计器, 其余系列照常落盘; 同系列恢复前只告警一次)
- test_agg_z_n_runs_and_block_gap_vacuum: z 游程槽速率恒 0 + totals 无末端列 = 显式退化(恒快照);
  n 游程 null 期不贡献且清空信用; 新块首 gap 超容差(条件结算) —— 块间 gap = 真空不虚记覆盖
- test_agg_z_end_anchor_interpolates_via_online: 形态 D 在线 —— z 行带末端对时游程内小时间隔
  摊配「开启快照 -> 末端快照」, 右端小时 = 末端快照、无单桶台阶; rate lane 不受影响
- test_agg_z_end_anchor_two_paths_same_hours: 形态 D 两路同源 —— 同一 z 行分别走在线 _agg_feed
  与离线 _agg_credit_day_file, 小时桶逐样本逐位一致(摊配共用 v4_z_totals_ramp)
- test_agg_day_month_rollup_and_month_boundary: 逐级派生(hour→day→month)数值 = v4_rollup_agg;
  翻本地日产 day 行 / 翻自然月产 month 行; 跨月后累计器开新
- test_flush_seals_completed_hours_only_and_no_duplicate: 水位封口(§4.2) —— 30s 连续采样跨小时界
  (v4 条件结算下连续采样覆盖不丢), flush 只封完结整小时; 重复 flush 不重 append(字节级不变)
- test_live_tail_published_per_round_and_cleared_by_flush: (S6 验收追加)活尾快照发布 —— 每轮 handler 末尾
  整体替换 live_tail(未落盘 buffer 记录 + 开放游程冻结副本); flush 后 records 清空(磁盘接管); 断连轮 n 游程入快照;
  运行期关闭(enabled=false)不发布
- test_recovery_catchup_equivalent_to_uninterrupted: catch-up 补算等价(§4.3) —— 停机数小时
  重启, hour/day/month 行补齐且与不停机等价序列逐列一致(停机真空两侧同形)
- test_recovery_hard_order_catchup_before_trim: 硬序(§4.3) —— hour 到龄/day 未封: 重启先由
  到龄 hour 行补出 day/month 行, 之后才裁剪(先裁后补 = 永久丢 day 行)
- test_recovery_idempotent_watermark_torn_and_duplicate: 幂等(§4.4) —— 水位从文件尾推,
  已有行不重算; 同 epoch 重复行取最后一行; 撕裂残行按坏行纪律跳过; 二次重启字节级零追加
- test_evict_at_flush_throttle_and_memory_cleanup: 淘汰新口径(§4.5) —— flush 时点触发 +
  EVICT_CHECK_INTERVAL_S 节流; 超龄删系列目录且内存缓存全清; 全局豁免; dry_run 跳过
- test_agg_trim_piggyback_on_hour_seal: hour 裁剪 piggyback(§4.5) —— hour 封口时点触发,
  判据用内存最老行; 到龄重写并回写 earliest_hour; 无到龄只追加不重写
- test_agg_trim_engages_for_runtime_created_series: 守阵(26-10-06-0028 C-01) —— 运行期新建系列
  (未经 _recover_series)earliest_hour 随 hour 行入账初始化/min 更新, 满窗后裁剪生效(agg.dat hour 行有界)
- test_agg_defensive_paths_cascades_and_write_failure: 防御面与失败口径 —— 无累计器 flush /
  零长区间 / 空桶不产行 / 跨日滞留级联封前一日 + 月级联 / agg append 与裁剪与淘汰扫描
  OSError 告警不上抛(连续失败只告警一次)

启动恢复按需读集(plan 26-10-12-2010, 读集下界 now - rollup_window -> agg 水位所在日):
- test_recovery_read_set_bounded_to_watermark_day: 读集有界(D1) —— 24 系列 x 30 天天文件 +
  水位在昨日的 agg -> 逐系列只读 [水位日, 今日] 至多 2 个天文件(recovery_reads 计数机检),
  不随 rollup_window=1000000D 放大; 封口小时不重算, 补算只覆盖水位之后; 二次重启零追加
- test_recovery_fallback_full_read_when_agg_missing: 兜底(D5) —— agg.dat 缺失(无水位)->
  退回保留窗全量读(诚实兜底不猜不静默), 读集 = 窗内全部天文件, hour 行照常补齐 + INFO 留痕
- test_recovery_instrumentation_logs_counts: 埋点(§7-B4) —— 起止 INFO(系列数/天文件数/
  补算小时数/耗时) + 读集 >2 天留下界来源; 计数落模块属性(机检面)
- test_read_side_view_contract_table: 读侧契约逐档机检(§3.2, 表驱动 13 档 x 时钟冻结) ——
  raw 段只开涉及日期天文件(窗外 decoy 零 open) / 3d+ 恒 1 个 agg.dat(天文件零 open) /
  限速注解面 = [t0-86400, t1] 日期集
- test_read_side_no_poll_when_traffic_tab_closed: 「不打开 = 0 请求」—— 前端轮询门控单点
  (关抽屉/形态切换/登出 -> _qbPollStop clearInterval, 重开幂等不叠加)

v4 定约用例(plan 26-10-05-2200 §04 表 3/5/6/7, B2 落地):
- test_v4_counter_reset_forces_block_reopen: 3. 计数器重置强制关块 —— 重置后块内负 delta 不出现,
  新块基线 = 重置后 totals(首记录 delta = 0)
- test_v4_cross_block_settlement_online_offline_same_source: 5. 跨块覆盖结算两路同源 —— 在线 _agg_feed
  与离线 _agg_credit_day_file 复用判定单点, 对连续边界/崩溃间隙/00:00 跨天边界产出逐桶一致 cov_s

时钟/落盘纪律: 需要确定时刻的用例经构造期 clock=FakeClock 注入(采样模块经 qbmanager 装配链透传, S3 后不再按模块换假钟)逐轮推进; flush 时点
除专项驱动用例外用 mod._flush_all_series() 直调(绕开驱动计时, 驱动时序由专项用例钉住)。

形态 D 封口末端锚点(plan 26-10-16-1509 §04, z 行扩列; 五条封口路径):
- test_zrun_cap_safety_valve_seals_at_day_level: 路径 5 保险闸封口同样写末端对
- test_zrun_end_anchor_counter_reset_degrades_to_open: 游程内计数器重置 -> 末端按开启快照
  退化(末端列 delta 非负, 文件零坏行)

P1-T1.2 守卫与容错簇(计划 26-10-20-2101, 覆盖率缺口清偿):
- test_hour_spans_splits_on_hour_boundary: 小时界切段纯函数 —— 跨整点出 3 段, 退化/空区间出 ()
- test_open_run_hour_samples_null_run_leaves_tail_null: n 游程只合成 credit 段到 run.start, 之后留
  null(断连不可归因为 0)
- test_open_run_hour_samples_without_credit_is_empty: 无观测信用 -> 不合成任何样本(不猜)
- test_pending_agg_rows_keeps_totals_monotonic_against_disk_row: 合成行 totals = 末端锚点 ->
  与磁盘行合流「totals 取后封行」不回退(反证: 带开启快照会回退)
- test_pending_agg_rows_cross_midnight_keeps_day_row_on_new_day: 跨本地日界 -> hour 行落两天,
  开放日行只取新一天的小时(前一日已封口小时不并进新日行)
- test_advance_run_z_requires_totals_snapshot: 开 z 游程需 totals 快照(缺失零操作, 不出 null 槽)
- test_resolve_run_end_falls_back_to_open_snapshot: 末端锚点三级兜底(显式 > 游程跟踪值 >
  开启快照)的最后一档
- test_null_prefix_split_block_on_raw_arrival: n-only 前缀拆块 —— 无基线块内到达带 totals 的
  记录先落 3 列 B 无基线块, 本记录开新块立基线(块首 n 游程不立基线)
- test_flush_series_no_buffer_and_header_once_across_flushes: 无缓冲系列零操作; 纯 z 块跨
  flush 开放且块头只写一次(第二批 header = None, header_written 不复位)
- test_recovery_missing_day_file_breaks_tail_context: 读集内天文件缺失 -> 末槽上下文断链
  (其后间隙由 gap 判定兜底真空)
- test_recovery_open_hour_rebuilds_pending_bucket: catch-up 遇未完结小时 -> 重建 pending 桶
  (不产 hour 行), 空桶跳过
- test_agg_credit_day_file_empty_block_and_null_slots: 空块零槽跳过 / n 槽 null 期不贡献
  (_slot_agg_obs 返回 None 的两条同源出口)
- test_agg_credit_hours_never_creates_empty_bucket (issue 26-11-01-0050): 入账恒
  setdefault+append 且 end<=start 直接返回 —— pending 空桶生产点不存在
- test_live_tail_pending_agg_published_and_cleared_by_seal

W5(R29) S5 补测守阵(mutcore 审计 core/modules/traffic_sample_mod.py; 三分类/红验对应单点
tmp-analysis/mut-core-w5-classify.md, 中危真洞全盖 + 低危按簇代表, bug 面不入此列):
- test_w5_blockhead_run_drift_dt_and_cursor: 块首游程显式 dt = 实测跨度且游标复位实测点; run_len==2
  不走单槽支、游程内部零覆盖入账(_append_record_116/117/124/125/126 + _append_record_93)
- test_w5_blockhead_run_drift_boundary_exact_tol: 块首游程漂移判据恰 250ms 压线不写 dt(_append_record_107)
- test_w5_zrun_time_valve_seals_at_exact_86400: 时间支保险闸恰 86400s 封口(_advance_run_76)
- test_w5_q3_slot_accounting_runs_and_flush_reset: Q3 槽计数 r=1/游程=run_len/flush 复位
  (_append_record_96/97/175 + _flush_series_37)
- test_w5_persist_warn_cycle_resets_after_success: 落盘告警节流成功复位/首败 WARNING/连败一次
  (_flush_series_29 / __init___8 / _agg_append_12/16/17)
- test_w5_agg_append_empty_false_nonempty_true: _agg_append 空批 False 契约(_agg_append_2)
- test_w5_main_tick1_quantize_and_warn_once: main_tick=1 档量化 ceil + 失配告警一次(_apply_interval_17/40)
- test_w5_live_tail_empty_shell_no_truncation: 活尾空信息键不截断其后系列(_publish_live_tail_37)
- test_w5_live_tail_head_pending_false_chain: head_pending=False 活尾游标链倒推(_publish_live_tail_65)
- test_w5_counter_reset_audit_logs: 重置审计 INFO 键/方向/关块留痕(sample_series_14/15/22/26/27/34 /
  _close_block_and_reopen_1 / _append_record_66/71)
- test_w5_latest_mirror_fields_complete: latest 镜像字段契约含 null 点(sample_series_43/47/49 /
  _touch_null_run_2)
- test_w5_init_sentinels_and_disabled_recovery: 恢复哨兵初值 + 未启用零恢复(__init___23/24 /
  _recover_aggregates_2)
- test_w5_pending_agg_rows_day_partition: 活尾日行跨日分片(_pending_agg_rows_27/34/37)
- test_w5_pending_agg_rows_month_partition: 活尾月行归档(_pending_agg_rows_63/55)
- test_w5_recover_single_month_row_no_reappend: 恰 1 个月行恢复不崩 + 水位幂等(_recover_series_22/23/19/20/114)
- test_w5_ingest_acc_same_day_multi_hour: day 累计器同日多 hour 追加(_ingest_acc_10)
- test_w5_day_reseal_merges_into_month: day 重封月级合流行(_agg_ingest_day_3)
- test_w5_credit_day_file_null_slots_then_raw_credited: 离线记账 n 槽不截断后继(_agg_credit_day_file_52)
- test_w5_credit_day_file_z_tail_end_anchor_cross_file: 离线 z 尾槽末端摊配 + 跨文件边界
  (_agg_credit_day_file_64 / _recover_series_57)
- test_w5_evict_audit_log: 按龄淘汰审计 INFO(_maybe_evict_32)
- test_w5_recover_oserror_warning_carries_key: 恢复失败 WARNING 含系列键(_recover_aggregates_37)
- test_w5_recovery_stats_elapsed_bounded: 恢复埋点 elapsed_s 有界(_recover_aggregates_39)
- test_w5_agg_error_log_type_and_rewarn_after_recovery: 封口失败 ERROR 类型 + 恢复后再告警
  (_agg_flush_all_7/10 / _agg_reset_after_error_4)
- test_w5_recover_diag_watermark_bound_log: 读集诊断 INFO 水位来源(_recover_series_67/69/71/72)
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
    _AUTH_HEADER_KEY,
    _agg_text,
    _build_tail_fixture,
    _feed_30s,
    _flush,
    _idle_state,
    _local_epoch,
    _mgr_with_traffic,
    _run_sample,
    _v4_open_paths,
    _v4_path,
    _v4_read,
    _w5_mgr,
    _w5_ts,
    _write_day_file,
)
from clock import FakeClock


def test_zrun_cap_safety_valve_seals_at_day_level(tmp_path, monkeypatch):
    """天级保险闸(N4): 开放 z 游程样本数 >= ZRUN_CAP_SAMPLES(86400 = ceil(86400/1s))
    强制封口防溢出 —— 正常空闲段任何路径都不应触闸(触闸即测试 bug), 本用例直灌游程
    推到闸值验证保险闸本身(z 游程 dt 链推算核对: 跨度 = 全天 < ZRUN_FLUSH_S)"""
    clock = FakeClock()
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=1), clock=clock)
    mgr.store.server_state = server_state()
    mod = mgr.host.get("qb_traffic")
    mod._effective_interval = 1.0  # 直灌游程: 块头游程的标称口径取 1s
    day0 = int(datetime(2026, 5, 10).timestamp())  # 本地午夜起: 86400 槽恰一天不跨天
    for i in range(ZRUN_CAP_SAMPLES):  # 86400 个零样本 @1s: 第 86400 个触闸封口
        mod._advance_run(GLOBAL_SERIES_KEY, day0 + i, "z", 10_000_000, 20_000_000)
    assert GLOBAL_SERIES_KEY not in mod._open_runs
    # 封口当刻 Q3 保险闸(86400 槽 >= 3600)提前 flush: 纯空闲块(z 行)照常落盘不关块
    parsed = _v4_read(tmp_path, GLOBAL_SERIES_KEY, day0 + ZRUN_CAP_SAMPLES - 1)
    z = parsed.blocks[0].records[0]
    assert isinstance(z, V4ZeroRun) and z.run_len == ZRUN_CAP_SAMPLES
    assert (z.dl_total_end, z.up_total_end) == (10_000_000, 20_000_000)  # 形态 D 路径 5 同样写末端对(此几何下 = 开启快照)
    slots = v4_block_slots(parsed.blocks[0])
    assert len(slots) == ZRUN_CAP_SAMPLES
    span = slots[-1].ts - slots[0].ts  # 块首游程: [首零样本, 第 86400 零样本] 端点含
    assert span == ZRUN_CAP_SAMPLES - 1
    assert span < ZRUN_FLUSH_S  # 保险闸阈值天级(N4)


# ---------- 累积漂移触发 dt_ms(§2.3 写侧, S2a 验收 tol 边界族) ----------
def test_dt_drift_boundary_family(tmp_path, monkeypatch):
    """tol 边界族(判据必须用「累积漂移」而非「本行偏差」):
    - 压线行: 恒定 250ms 偏差(累积漂移恰在容差上)不写 dt;
    - 超线行: 累积漂移 > 250ms 写实测 dt 并自然复位(游标推到实测点);
    - 稳态小漂移(150ms/行)退化周期写(约每 2 行一 dt);
    - 空载(等间隔)零 dt 行(稀疏);
    - roundtrip: v4_block_slots 推算时刻与实测逐一相等(误差 <= 取整)。
    v4 关块谓词下块随 flush 关闭、新块游标重锚(B.start 截断)—— 全序列保持单块以守护
    连续游标链: 中途断言读缓冲内存形态, 末尾一次 flush 落盘做 roundtrip。"""
    clock = FakeClock()
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30), clock=clock)
    mgr.store.server_state = server_state()
    mod = mgr.host.get("qb_traffic")

    def buf_dts():
        return [r.dt_ms for r in mod._buffers[GLOBAL_SERIES_KEY].records]

    # 空载: 等间隔 3 轮 -> 零 dt 行
    _run_sample(mgr)
    for _ in range(3):
        clock.advance(30)
        _run_sample(mgr)
    assert buf_dts() == [None, None, None, None]
    # 压线: 恒定 250ms 偏差(不累积: 首步 +0.25, 之后整间隔) -> 永不触发
    clock.advance(30.25)
    _run_sample(mgr)
    for _ in range(2):
        clock.advance(30)
        _run_sample(mgr)
    assert all(d is None for d in buf_dts()[-3:]), buf_dts()[-3:]
    # 超线: 单次 300ms 突跳 -> 该行写实测 dt(从链上锚点起算)并复位, 次行回标称
    clock.advance(30.3)
    _run_sample(mgr)
    clock.advance(30)
    _run_sample(mgr)
    dts = buf_dts()
    assert dts[-2] is not None and dts[-1] is None
    # 稳态小漂移 150ms/行(< tol, 逐行判永不触发): 误差累积至超线 -> 周期性 dt 行(退化逐行写的离散形态)
    for _ in range(4):
        clock.advance(30.15)
        _run_sample(mgr)
    dts = buf_dts()[-4:]
    assert dts[0] is None and dts[1] is not None and dts[2] is None and dts[3] is not None, dts
    # roundtrip: 末尾一次 flush(单块全序列)后, 推算时刻与实测逐一对照 —— 标称行差 <= tol
    # (漂移在容差内如实保留), 显式 dt 行差 <= dt_ms 取整 1ms; 链无累积误差
    _flush(mod)
    parsed = _v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now())
    assert len(parsed.blocks) == 1  # 单块: 游标链跨全序列连续(v4 块首重锚不发生)
    slots = v4_block_slots(parsed.blocks[0])
    assert slots[0].ts == 1_700_000_000.0  # 块首槽 = B.start
    actuals = [0, 30, 60, 90, 120.25, 150.25, 180.25, 210.55, 240.55, 270.7, 300.85, 331.0, 361.15]
    for i, slot in enumerate(slots[1:], start=1):
        assert abs(slot.ts - (1_700_000_000.0 + actuals[i])) <= 0.251, (i, slot.ts, actuals[i])
    for i, slot in enumerate(slots[1:], start=1):
        rec = parsed.blocks[0].records[i]
        if rec.dt_ms is not None:  # 显式 dt 行: 严格按实测推进(取整 1ms)
            assert abs(slot.ts - (1_700_000_000.0 + actuals[i])) <= 0.001, (i, slot.ts, actuals[i])


def test_buffer_slot_cap_3600_early_flush(tmp_path, monkeypatch):
    """Q3 保险闸(§3.1): 单系列缓冲槽 >= 3600 提前单独 flush(防 ~60MB 滞留); 不关块,
    块头只写一次, 后续记录续写同块"""
    clock = FakeClock()
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=1, flush_interval=10**9), clock=clock)
    mgr.store.server_state = server_state()
    mod = mgr.host.get("qb_traffic")
    for _ in range(V4_BUFFER_SLOT_CAP):  # 3600 轮活跃: 第 3600 槽触发提前 flush(驱动永不触发)
        clock.advance(1)
        mod.handle_traffic_sample(dry_run=False)
    parsed = _v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now())
    assert parsed is not None and len(parsed.blocks) == 1
    assert len(parsed.blocks[0].records) == V4_BUFFER_SLOT_CAP  # 恰在闸值落盘
    buf = mod._buffers[GLOBAL_SERIES_KEY]
    assert buf.records == [] and buf.start_epoch is None  # v4: 带 r 行的块随闸值 flush 关闭
    for _ in range(3):
        clock.advance(1)
        mod.handle_traffic_sample(dry_run=False)
    _flush(mod)
    parsed = _v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now())
    assert len(parsed.blocks) == 2 and len(parsed.blocks[1].records) == 3  # 新块续采(自带新块头)


def test_zrun_end_anchor_counter_reset_degrades_to_open(tmp_path, monkeypatch):
    """形态 D 游程内计数器重置(qB 重启): 末端实测低于开启快照 -> 末端锚点按开启快照退化
    (重置落差不是增长); z 行末端列 delta 非负、文件零坏行, 随后 r 照常触发重置关块"""
    clock = FakeClock()
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30), clock=clock)
    mgr.store.server_state = server_state()
    rec = active_torrent("HASH123")
    seed_store(mgr, [rec])
    mod = mgr.host.get("qb_traffic")
    key = "torrent:HASH123"
    _run_sample(mgr)  # t0: 活跃 -> r(块基线 5,000,000/3,000,000)
    rec.dlspeed = 0
    rec.upspeed = 0
    rec.downloaded, rec.uploaded = 5_000_500, 3_000_200
    clock.advance(30)
    _run_sample(mgr)  # t0+30: 零样本开游程(快照 5,000,500/3,000,200)
    rec.dlspeed = 512
    rec.downloaded, rec.uploaded = 900_000, 700_000  # qB 重启: all-time 回落
    clock.advance(30)
    _run_sample(mgr)  # t0+60: 恢复传输 -> 封游程(末端低于开启, 按开启退化) + r(重置关块)
    _flush(mod)
    parsed = _v4_read(tmp_path, key, clock.now())
    assert parsed.bad_lines == 0
    z = parsed.blocks[0].records[1]
    assert isinstance(z, V4ZeroRun)
    assert (z.dl_total_end, z.up_total_end) == (z.dl_total, z.up_total) == (5_000_500, 3_000_200)
    text = _v4_path(tmp_path, key, clock.now()).read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("z,"):
            assert all(int(col) >= 0 for col in line.split(",")[2:6]), line


def test_flush_oserror_discards_block_warns_once(tmp_path, monkeypatch):
    """落盘失败(OSError, §01.1): 不上抛、连续失败只告警一次; 失败块丢弃并复位块状态
    (dt 链卫生: 下次成功写起新块, 游标不错位)"""
    clock = FakeClock()
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30), clock=clock)
    mgr.store.server_state = server_state()
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)
    from auto_qb.core.traffic_store import TrafficV4Store

    failing = {"on": True}
    real_append = TrafficV4Store.append_records

    def flaky_append(self, key, date_str, header, records, block_base):
        if failing["on"]:
            raise OSError("disk full")
        return real_append(self, key, date_str, header, records, block_base)

    monkeypatch.setattr(TrafficV4Store, "append_records", flaky_append)
    with capture_logs("auto_qb.core.modules.traffic_sample_mod") as cap:
        _flush(mod)  # 失败 1: 告警一次, 块复位
    assert "批量落盘失败" in cap.text
    assert mod._buffers[GLOBAL_SERIES_KEY].start_epoch is None  # 块状态复位
    _run_sample(mgr)
    with capture_logs("auto_qb.core.modules.traffic_sample_mod") as cap2:
        _flush(mod)  # 失败 2: 持续失败降级 DEBUG(措辞「持续」), 不再 WARNING
    assert "(持续)" in cap2.text and "(本批数据丢失" not in cap2.text
    failing["on"] = False
    clock.advance(30)
    _run_sample(mgr)
    _flush(mod)  # 恢复: 新块成功落盘(B.start = 新块首)
    parsed = _v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now())
    assert len(parsed.blocks) == 1 and parsed.blocks[0].start_epoch == int(clock.now())
    assert len(parsed.blocks[0].records) == 1


def test_flush_all_drops_shell_buffers(tmp_path, monkeypatch):
    """内存卫生: 无开放块、无待写记录、无开放游程且本轮未采样的 shell 缓冲被清除
    (采样率变化关块后系列被删除的场景)"""
    clock = FakeClock()
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30), clock=clock)
    mgr.store.server_state = server_state()
    seed_store(mgr, [active_torrent()])
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)  # t0: r -> 块开放
    mgr.store.by_hash.pop("HASH123")  # 系列删除(不再采样)
    mgr.config.qb_traffic.sample_interval = 10
    clock.advance(60)
    _run_sample(mgr)  # 采样率变化关块: 旧块落盘复位 -> shell(系列已删无新记录)
    assert mod._buffers["torrent:HASH123"].start_epoch is None  # shell(无开放块)
    _flush(mod)
    assert "torrent:HASH123" not in mod._buffers  # shell 清除
    assert GLOBAL_SERIES_KEY in mod._buffers  # 活跃系列缓冲保留


def test_agg_hour_row_dt_weighted_across_hour_boundary(tmp_path):
    """hour 行产出(§4.1): 前向记账逐区间入账, 信用区间跨小时界自然拆分 —— avg = dt
    加权 / cov_s = Σ桶内覆盖 / max 逐记录取大 / totals 取级末快照; 未完结小时留累计器;
    hour 行同步并入 day 累计器(严格逐级)"""
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mod = mgr.host.get("qb_traffic")
    key = GLOBAL_SERIES_KEY
    h0 = _AGG_H0
    r1, r2, r3 = V4Sample(100, 50, 1000, 2000), V4Sample(200, 60, 2000, 3000), V4Sample(300, 70, 3000, 4000)
    mod._agg_feed(key, r1, h0 + 10, h0 + 10, True, 30.0)  # 块首 r@h0+10: 信用开立(首块无前块上下文)
    mod._agg_feed(key, r2, h0 + 10, h0 + 40, False, 30.0)  # 结算 [h0+10, h0+40) @ r1 (30s)
    mod._agg_feed(key, r3, h0 + 40, h0 + 100, False, 30.0)  # 结算 [h0+40, h0+100) @ r2 (60s)
    mod._agg_feed(key, r1, h0 + 100, h0 + 3605, False, 30.0)  # 结算 [h0+100, h1) 3500s @ r3 + [h1, h1+5) 5s
    assert mod._agg_flush_series(key, now=h0 + 3605) is True  # h0 完结, h1 未完结
    row = parse_v4_agg_text(_agg_text(tmp_path, key)).hours[0]
    assert row.dl_avg == int(round((100 * 30 + 200 * 60 + 300 * 3500) / 3590))  # dt 加权
    assert row.up_avg == int(round((50 * 30 + 60 * 60 + 70 * 3500) / 3590))
    assert row.dl_max == 300 and row.up_max == 70  # 逐记录取大
    assert (row.dl_total, row.up_total) == (3000, 4000)  # totals = 桶内级末快照(r3)
    assert row.cov_s == 3590  # Σdt = 30 + 60 + 3500
    agg = mod._agg_states[key]
    assert [h for h in agg.pending] == [h0 + HOUR_SECONDS]  # h1 未完结留累计器, h0 已弹出
    assert len(agg.pending[h0 + HOUR_SECONDS]) == 1 and agg.pending[h0 + HOUR_SECONDS][0].dt_s == 5.0
    assert agg.day_epoch == v4_day_epoch(h0) and len(agg.day_hours) == 1  # 严格逐级: hour 并入 day
    assert agg.month_epoch is None and agg.month_days == []


def test_agg_flush_subsecond_hour_rolls_up_without_raise(tmp_path):
    """亚秒小时桶的日封口(2026-10-13 真机「逐级聚合无有效覆盖」回归): 迟到补记重建的
    小时桶只带跨小时界亚秒残余覆盖时, cov_s 下限 1 让 day 封口不再抛异常 —— 修复前
    v4_hour_agg 折 0 -> Σcov_s = 0 -> _agg_flush_series 抛 ValueError(且异常在落盘前
    抛出, 于是每轮 flush 复现、整批 agg 行丢弃); day 行既出, 数值仍按 float cov 加权"""
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mod = mgr.host.get("qb_traffic")
    key = GLOBAL_SERIES_KEY
    day1 = int(datetime(2026, 3, 2).timestamp())  # 本地 3 月 2 日 00:00(hour 对齐)
    r1, r2 = V4Sample(100, 50, 1000, 2000), V4Sample(200, 60, 2000, 3000)
    mod._agg_feed(key, r1, day1, day1, True, 30.0)  # 块首 r: 开信用(首块无前块上下文)
    mod._agg_feed(key, r2, day1, day1 + 0.263, False, 30.0)  # 亚秒残余: 只结算 [day1, day1+0.263)
    assert mod._agg_flush_series(key, now=day1 + 86400 + 600) is True  # 跨本地日 -> hour + day 两行一批
    parsed = parse_v4_agg_text(_agg_text(tmp_path, key))
    assert parsed.hours == (AggRow("hour", day1, 100, 100, 50, 50, 1000, 2000, 1), )
    assert parsed.days == (AggRow("day", day1, 100, 100, 50, 50, 1000, 2000, 1), )
    assert mod._agg_states[key].month_epoch == v4_month_epoch(day1)  # day 行已并入 month 累计器(严格逐级)


def test_agg_reseal_merges_late_credit_keeps_full_coverage(tmp_path):
    """已封小时被迟到补记重建后再封时走合流(2026-10-13 真机「重封替换丢覆盖」回归): 长空闲
    z 游程可延迟到 ZRUN_FLUSH_S 才封口, 其信用落在早已封口的小时桶上 —— 合流后小时行 cov
    回到整小时、avg 按两段 cov 加权, 落批末行 = 合流行(解析取末行), day 累计器同持合流行。
    修复前(替换语义): 末行只留残余(cov 1762), 真机日行 cov_s 44712 vs 全量 86400"""
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mod = mgr.host.get("qb_traffic")
    key = GLOBAL_SERIES_KEY
    h0 = _AGG_H0
    mod._agg_feed(key, V4Sample(100, 50, 1000, 2000), h0, h0, True, 30.0)  # 块首 r: 开信用
    mod._agg_feed(key, V4Sample(200, 60, 2000, 3000), h0, h0 + 1838, False, 30.0)  # 结算 [h0, h0+1838)
    assert mod._agg_flush_series(key, now=h0 + HOUR_SECONDS) is True  # 小时封口(桶随即被弹出)
    first = parse_v4_agg_text(_agg_text(tmp_path, key)).hours[0]
    assert first.cov_s == 1838 and first.dl_avg == 100
    # 迟到补记: 同一小时桶被重建(只带残余 1762s) -> 再封 = 与原行合流
    mod._agg_feed(key, V4ZeroRun(1, 3000, 4000), h0 + 1838, h0 + HOUR_SECONDS, False, 30.0)
    assert mod._agg_flush_series(key, now=h0 + HOUR_SECONDS + 30) is True
    rows_text = _agg_text(tmp_path, key)
    assert rows_text.count(f"hour,{h0},") == 2  # 文件里同 epoch 两行(首封行 + 重封合流行)
    rows = parse_v4_agg_text(rows_text).hours
    assert len(rows) == 1 and rows[0].cov_s == 3600  # 解析取末行 = 合流行(修复前 = 1762 残余)
    assert rows[0].dl_avg == int(round((100 * 1838 + 200 * 1762) / 3600)) == 149  # cov 加权, 非任一侧
    assert rows[0].dl_max == 200 and (rows[0].dl_total, rows[0].up_total) == (2000, 3000)
    assert mod._agg_states[key].day_hours[0] == rows[0]  # day 累计器持合流行(逐级链覆盖完整)


def _feed_day_last_hour_full(mod, key, day_midnight, rate):
    """day 的末小时(hour23)灌满 3599s 覆盖(速率 rate, 块首 r + 结算), 信用立在末槽"""
    h23 = day_midnight + 23 * HOUR_SECONDS
    mod._agg_feed(key, V4Sample(rate, rate // 2, 1000, 2000), h23, h23, True, 30.0)
    mod._agg_feed(key, V4Sample(rate + 100, 60, 2000, 3000), h23, h23 + 3599, False, 30.0)


def _feed_late_credit_1s(mod, key, day_midnight):
    """午夜后迟到信用: 结算 [h23+3599, 午夜) = 1s 残余(速率 300), 不触及次日桶"""
    h23 = day_midnight + 23 * HOUR_SECONDS
    mid = day_midnight + 86400
    mod._agg_feed(key, V4Sample(300, 70, 3000, 4000), h23 + 3599, h23 + 3599, False, 30.0)
    mod._agg_feed(key, V4Sample(300, 70, 3000, 4000), mid, mid, False, 30.0)


def test_agg_closed_day_reseal_merges_via_closed_stub(tmp_path):
    """已关日的 hour 迟到重封走已关日存根合流(issue 26-11-07-0527 R1#63): 日关闭(复位
    day_epoch/day_hours)后该日 hour 再被迟到信用重封时, 修复前残余行未经 v4_merge_agg
    直接落盘、解析按「同 epoch 取最后一行」让残余行替换已写全量行(hour cov 3599 -> 1,
    avg/max 同被腐蚀), 且重启恢复以最后一行为水位不会再重算修复。真机形态: 午夜跨天
    空闲 z 游程在 00:00 后首个样本封口, 而 flush 恰落在 00:00 与封口记录之间。合流后
    hour 行 cov 回整小时、avg 按 cov 加权、totals 取后封行; 日行由存根重建(完整重算),
    开放累计器不被背日行重开"""
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mod = mgr.host.get("qb_traffic")
    key = GLOBAL_SERIES_KEY
    day1 = int(datetime(2026, 3, 2).timestamp())  # 本地 3 月 2 日 00:00(非月界)
    h23 = day1 + 23 * HOUR_SECONDS
    _feed_day_last_hour_full(mod, key, day1, 200)  # hour23 全量 3599s @ 200
    assert mod._agg_flush_series(key, now=day1 + 86400) is True  # 午夜 flush: hour23 封口 + 日关闭
    parsed = parse_v4_agg_text(_agg_text(tmp_path, key))
    assert parsed.hours[0].cov_s == 3599 and parsed.days[0].cov_s == 3599
    agg = mod._agg_states[key]
    assert agg.day_epoch is None and agg.closed_day[0] == day1  # 日已关, 存根在
    assert agg.closed_day[1][0] == parsed.hours[0]  # 存根持已写行(与文件有效行同值)

    _feed_late_credit_1s(mod, key, day1)  # 迟到信用重封 hour23(残余 1s @ 300)
    assert mod._agg_flush_series(key, now=day1 + 86400 + 60) is True
    rows = parse_v4_agg_text(_agg_text(tmp_path, key))
    hour = next(h for h in rows.hours if h.epoch == h23)
    assert hour.cov_s == 3600  # 合流行(修复前 = 1 残余)
    assert hour.dl_avg == int(round((200 * 3599 + 300 * 1) / 3600)) == 200  # cov 加权, 非任一侧
    assert hour.dl_max == 300 and (hour.dl_total, hour.up_total) == (3000, 4000)  # totals 取后封行
    day = next(d for d in rows.days if d.epoch == day1)
    assert day.cov_s == 3600 and day.dl_avg == 200  # 日行由存根重建(完整重算), 非残余
    assert (day.dl_total, day.up_total) == (3000, 4000)  # 级末快照随合流推进
    assert agg.day_epoch is None  # 背日行不重开日累计器(后续背日重封继续走存根)
    assert agg.closed_day[1][0] == hour  # 存根同持合流行(再重封时链式合流)


def test_agg_month_boundary_reseal_rebuilds_day_and_month_rows(tmp_path):
    """月界同构面(issue 26-11-07-0527 R1#63): 日关闭与月关闭同批复位两级累计器后, 该日
    hour 迟到重封 —— 修复前 hour/day/month 三行全被残余行替换(cov 全塌到 1); 修复后
    hour 走存根合流, 日行由已关日存根重建, 月行由已关月存根重建(其他天(1/30)的行不丢)"""
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mod = mgr.host.get("qb_traffic")
    key = GLOBAL_SERIES_KEY
    day30 = int(datetime(2026, 1, 30).timestamp())
    day31 = int(datetime(2026, 1, 31).timestamp())
    feb1 = int(datetime(2026, 2, 1).timestamp())
    _feed_day_last_hour_full(mod, key, day30, 100)  # 1/30 末小时 @ 100(与 1/31 异值: 钉月行重建不丢天)
    mod._agg_flush_series(key, now=day30 + 86400)  # 1/30 日关闭(月仍开放)
    _feed_day_last_hour_full(mod, key, day31, 200)  # 1/31 末小时 @ 200
    assert mod._agg_flush_series(key, now=feb1) is True  # 月界 flush: 1/31 日关闭 + 1 月关闭
    parsed = parse_v4_agg_text(_agg_text(tmp_path, key))
    assert [d.cov_s for d in parsed.days] == [3599, 3599]
    assert parsed.months[0].cov_s == 7198  # 两天各 3599
    agg = mod._agg_states[key]
    assert agg.day_epoch is None and agg.month_epoch is None  # 日/月双层已复位
    assert agg.closed_month[0] == v4_month_epoch(day31) and len(agg.closed_month[1]) == 2  # 月存根持两天

    _feed_late_credit_1s(mod, key, day31)  # 迟到信用重封 1/31 的 hour23(残余 1s @ 300)
    assert mod._agg_flush_series(key, now=feb1 + 60) is True
    rows = parse_v4_agg_text(_agg_text(tmp_path, key))
    hour31 = next(h for h in rows.hours if h.epoch == day31 + 23 * HOUR_SECONDS)
    assert hour31.cov_s == 3600 and hour31.dl_avg == 200  # 合流行(修复前 cov 1)
    day31_row = next(d for d in rows.days if d.epoch == day31)
    assert day31_row.cov_s == 3600 and day31_row.dl_avg == 200  # 日行重建(修复前 cov 1)
    assert next(d for d in rows.days if d.epoch == day30).cov_s == 3599  # 其他天(1/30)不受背日重封影响
    month = rows.months[0]
    assert month.cov_s == 3599 + 3600  # 月行重建: 1/30 的 3599 不丢(修复前塌到 1)
    assert month.dl_avg == int(round((100 * 3599 + 200 * 3600) / (3599 + 3600)))  # 按各天 cov 加权
    assert month.dl_max == 300  # max 取大(1/31 残余样本抬到 300)


def test_agg_backdated_reseal_leaves_open_day_accumulator_alone(tmp_path):
    """背日重封不碰开放日累计器(issue 26-11-07-0527 R1#63 修法面): 开放日已有封口小时
    (day_epoch=次日)时, 已关日的迟到重封走存根, 开放累计器不得被复位或提前级联误关
    (修复前背日行走 _ingest_acc 会把开放日提前关成缺日行); 开放日照常自然封口出完整日行"""
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mod = mgr.host.get("qb_traffic")
    key = GLOBAL_SERIES_KEY
    day1 = int(datetime(2026, 3, 2).timestamp())
    day2 = day1 + 86400
    h23 = day1 + 23 * HOUR_SECONDS
    _feed_day_last_hour_full(mod, key, day1, 200)
    mod._agg_flush_series(key, now=day2)  # 午夜 flush: day1 关闭, 存根立
    _feed_30s(mod, key, day2 + 60, [(300, 70, 3000, 4000)] * 2)  # 次日 hour0 采样(首间隔 61s 真空, 无跨午夜结算)
    mod._agg_flush_series(key, now=day2 + HOUR_SECONDS + 60)  # hour0 封口 -> 开放日累计器 = day2
    agg = mod._agg_states[key]
    assert agg.day_epoch == day2 and len(agg.day_hours) == 1

    _feed_late_credit_1s(mod, key, day1)  # 已关日(day1)的迟到重封
    assert mod._agg_flush_series(key, now=day2 + HOUR_SECONDS + 120) is True
    rows = parse_v4_agg_text(_agg_text(tmp_path, key))
    assert next(h for h in rows.hours if h.epoch == h23).cov_s == 3600  # 存根合流生效
    assert [d.epoch for d in rows.days] == [day1]  # day2 未被提前误关(修复前此处已多出缺日行)
    assert agg.day_epoch == day2 and len(agg.day_hours) == 1  # 开放累计器原样
    # 开放日照常自然封口: day2 行含其全部小时(hour0 60s + hour1 60s, 非提前误关的缺日行)
    _feed_30s(mod, key, day2 + HOUR_SECONDS + 130, [(300, 70, 3000, 4000)] * 2)
    mod._agg_flush_series(key, now=day2 + 86400)  # 次日午夜 flush: 日界过了才关日(L263 判据)
    rows = parse_v4_agg_text(_agg_text(tmp_path, key))
    day2_row = next(d for d in rows.days if d.epoch == day2)
    assert day2_row.cov_s == 120  # hour0 60s + hour1 60s
    assert agg.day_epoch is None  # 自然关闭(非背日级联)


def test_agg_flush_all_isolates_series_error_and_resets(tmp_path, monkeypatch):
    """逐系列隔离与善后(2026-10-13 真机「单系列异常阻断全批 agg 落盘」回归): 某系列封口抛错
    只告警该系列 + 重置该系列累计器, 其余系列照常落盘(修复前异常上抛 -> 全系列 agg 静默停写,
    且抛点在状态复位之前 -> 同一错每轮 flush 复现); 同系列恢复前只告警一次(免刷屏)"""
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mod = mgr.host.get("qb_traffic")
    bad, good = GLOBAL_SERIES_KEY, "torrent:" + "0" * 40
    h0 = _AGG_H0
    for k in (bad, good):
        mod._agg_state(k).pending[h0] = [V4HourSample(100, 50, 1000, 2000, 3600.0)]
    real = mod._agg_flush_series

    def boom(key, now):
        if key == bad:
            raise ValueError("注入: 逐级聚合无有效覆盖")
        return real(key, now)

    monkeypatch.setattr(mod, "_agg_flush_series", boom)
    with capture_logs("auto_qb.core.modules.traffic_sample_mod") as cap:
        mod._agg_flush_all(now=h0 + HOUR_SECONDS)
        mod._agg_state(bad).pending[h0] = [V4HourSample(1, 1, 1, 1, 3600.0)]  # 下一轮重试
        mod._agg_flush_all(now=h0 + HOUR_SECONDS + 600)
    # 隔离: 健康系列照常落盘(修复前异常一路上抛, 这里一行都不会有)
    assert parse_v4_agg_text(_agg_text(tmp_path, good)).hours[0].cov_s == 3600
    # 善后: 出错系列累计器已重置 + 告警只一次(节流)
    assert bad not in mod._agg_states and bad in mod._agg_warned
    assert cap.text.count("聚合封口失败") == 1


def test_agg_z_n_runs_and_block_gap_vacuum(tmp_path):
    """游程与真空(§4.1): z 游程内部槽区间速率恒 0 + totals 无末端列时按开启快照恒定
    (显式退化 = 旧语义; 带末端列的摊配见 test_agg_z_end_anchor_* 两条), 信用链在游程两端
    正确结算; n 游程 null 期不贡献且清空信用; 新块首清信用 —— 块间 gap = 真空不虚记"""
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mod = mgr.host.get("qb_traffic")
    key = GLOBAL_SERIES_KEY
    t0 = _AGG_H0
    r1, r2, r3 = V4Sample(100, 50, 1000, 2000), V4Sample(200, 70, 2000, 3000), V4Sample(300, 80, 3000, 4000)
    z, n = V4ZeroRun(3, 7000, 8000), V4NullRun(2)
    mod._agg_feed(key, r1, t0, t0, True, 30.0)
    mod._agg_feed(key, z, t0, t0 + 90, False, 30.0)  # 结算 [t0,t0+30)@r1; z 内部 2x30s @0; 信用 (t0+90, 0)
    mod._agg_feed(key, r2, t0 + 90, t0 + 120, False, 30.0)  # 结算 [t0+90,t0+120)@0(z 尾信用)
    mod._agg_feed(key, n, t0 + 120, t0 + 180, False, 30.0)  # 结算 [t0+120,t0+150)@r2; n 期不记, 信用清空
    mod._agg_feed(key, r3, t0 + 180, t0 + 210, False, 30.0)  # 信用 None: 无结算
    mod._agg_feed(key, r1, t0 + 1000, t0 + 1000, True, 30.0)  # 新块首: gap 790s 超容差 -> 真空不结算 [t0+210, t0+1000)
    mod._agg_flush_series(key, now=t0 + HOUR_SECONDS)
    row = parse_v4_agg_text(_agg_text(tmp_path, key)).hours[0]
    assert row.cov_s == 150  # 5 个 30s 区间(r1 + z 内 2 + z 尾 + r2 尾), n 期与块间 gap 不计
    assert row.dl_avg == int(round((100 * 30 + 200 * 30) / 150)) == 60  # z 区间速率恒 0
    assert row.dl_max == 200 and row.up_max == 70  # z/n 不抬 max
    assert (row.dl_total, row.up_total) == (2000, 3000)  # 级末快照 = r2


def test_agg_z_end_anchor_interpolates_via_online(tmp_path):
    """形态 D 在线(plan 26-10-16-1509 §04/§05): z 行带末端对时, 游程内各小时间隔摊配
    「开启快照 -> 末端快照」—— 逐小时 totals 递增、右端小时 = 末端快照(不再单桶台阶),
    区间累加严格守恒(Σ 增量 = S1 - S0, 取整余量归末端槽); 速率 lane 不受影响(z 区间恒 0)"""
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mod = mgr.host.get("qb_traffic")
    key = GLOBAL_SERIES_KEY
    h0 = _AGG_H0
    s0, s1 = (1_000_500, 2_000_300), (1_014_500, 2_018_300)
    z = V4ZeroRun(120, s0[0], s0[1], dl_total_end=s1[0], up_total_end=s1[1])  # 2 小时游程跨小时界
    mod._agg_feed(key, V4Sample(100, 50, 1_000_000, 2_000_000), h0, h0, True, 30.0)  # 块首 r: 开信用
    mod._agg_feed(key, z, h0, h0 + 3600, False, 30.0)
    mod._agg_feed(key, V4Sample(300, 90, s1[0], s1[1]), h0 + 3600, h0 + 3630, False, 30.0)
    assert mod._agg_flush_series(key, now=h0 + 2 * HOUR_SECONDS + 60) is True
    rows = {r.epoch: r for r in parse_v4_agg_text(_agg_text(tmp_path, key)).hours}
    ramp = v4_z_totals_ramp(s0[0], s0[1], s1[0], s1[1], 120)
    assert ramp[0] == s0 and ramp[-1] == s1  # 端点精确
    assert ramp[118] == (1_014_382, 2_018_149)  # 取整口径钉住(整数四舍五入)
    r1, r2 = rows[h0], rows[h0 + HOUR_SECONDS]
    assert (r1.dl_total, r1.up_total) == ramp[118]  # 游程内小时 = 末槽摊配值(非冻结快照)
    assert (r2.dl_total, r2.up_total) == s1  # 右端对齐: 游程结束所落小时 = 末端快照
    assert (r2.dl_total - r1.dl_total) == s1[0] - ramp[118][0]  # 剩余增长只余末段(消除单桶台阶)
    assert r1.cov_s == 3600 and r2.cov_s == 30  # 覆盖面不变(z 尾部信用仅一间隔)
    assert r1.dl_max == 100 and r2.dl_max == 0  # rate lane 不受影响(z 区间速率恒 0)


def test_agg_z_end_anchor_two_paths_same_hours(tmp_path):
    """形态 D 两路同源(plan §05 判据 4): 同一 z 行(带末端对)分别走在线 _agg_feed 与离线
    _agg_credit_day_file, 小时桶逐样本逐位一致(槽位两路同源 + 摊配共用 v4_z_totals_ramp)"""
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mod = mgr.host.get("qb_traffic")
    key = GLOBAL_SERIES_KEY
    h0 = _AGG_H0
    s0, s1 = (1_000_500, 2_000_300), (1_014_500, 2_018_300)
    blk = V4Block(
        h0,
        30,
        1_000_000,
        2_000_000,
        (
            V4Sample(100, 50, 1_000_000, 2_000_000),
            V4ZeroRun(120, s0[0], s0[1], dl_total_end=s1[0], up_total_end=s1[1]),
            V4Sample(300, 90, s1[0], s1[1]),
        ),
    )
    slots = v4_block_slots(blk)
    idx = 0
    for i, rec in enumerate(blk.records):  # 在线: 按写侧游标推进口径回放
        n = 1 if isinstance(rec, V4Sample) else rec.run_len
        anchor = float(blk.start_epoch) if i == 0 else slots[idx - 1].ts
        mod._agg_feed(key, rec, anchor, slots[idx + n - 1].ts, i == 0, blk.interval_s)
        idx += n
    pending_off = {}
    TrafficSampleModule._agg_credit_day_file(
        pending_off, parse_v4_day_text(format_v4_day_text("global", (blk, ))), None
    )
    assert {h: tuple(s) for h, s in mod._agg_states[key].pending.items()} == {h: tuple(s) for h, s in pending_off.items()}
    ramp = v4_z_totals_ramp(s0[0], s0[1], s1[0], s1[1], 120)
    assert pending_off[h0][-1] == V4HourSample(0, 0, ramp[118][0], ramp[118][1], 30.0)
    assert pending_off[h0 + HOUR_SECONDS] == [V4HourSample(0, 0, s1[0], s1[1], 30.0)]


def test_agg_day_month_rollup_and_month_boundary(tmp_path):
    """逐级派生与翻月(§4.1/§4.2): hour 封口并入 day 累计器, day 并入 month 累计器
    (day 不从 raw 直聚); 完结本地日 -> day 行, 完结自然月 -> month 行, 数值 =
    v4_rollup_agg(avg 按 cov 加权 / max 取大 / totals 级末快照 / cov 求和)"""
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mod = mgr.host.get("qb_traffic")
    key = GLOBAL_SERIES_KEY
    day31 = int(datetime(2026, 1, 31).timestamp())  # 本地 1 月 31 日 00:00
    jan1 = int(datetime(2026, 1, 1).timestamp())
    feb1 = int(datetime(2026, 2, 1).timestamp())
    obs = [(100, 50, 1000, 2000), (200, 60, 2000, 3000), (300, 70, 3000, 4000)]
    _feed_30s(mod, key, day31 + 5 * HOUR_SECONDS, obs)
    mod._agg_flush_series(key, now=feb1 + 600)  # 跨本地日 + 跨自然月: hour/day/month 三行一批
    parsed = parse_v4_agg_text(_agg_text(tmp_path, key))
    assert len(parsed.hours) == 1 and len(parsed.days) == 1 and len(parsed.months) == 1
    hour_expected = v4_hour_agg(day31 + 5 * HOUR_SECONDS, tuple(V4HourSample(d, u, t, s, 30.0) for d, u, t, s in obs))
    assert parsed.hours[0] == hour_expected
    day_expected = v4_rollup_agg("day", day31, (hour_expected, ))
    assert parsed.days[0] == day_expected
    assert parsed.months[0] == v4_rollup_agg("month", jan1, (day_expected, ))
    # 跨月后新月份: day/month 累计器开新, 旧月行不再追加
    _feed_30s(mod, key, feb1 + 2 * HOUR_SECONDS, obs)
    mod._agg_flush_series(key, now=feb1 + 3 * HOUR_SECONDS + 10)
    parsed = parse_v4_agg_text(_agg_text(tmp_path, key))
    assert len(parsed.hours) == 2 and len(parsed.days) == 1 and len(parsed.months) == 1  # 2 月日/月未完结
    agg = mod._agg_states[key]
    assert agg.day_epoch == feb1 and agg.month_epoch is None  # 当日累计器开放; 月累计器待首个完整日封口


def test_flush_seals_completed_hours_only_and_no_duplicate(tmp_path, monkeypatch):
    """水位封口(§4.2): flush 时点只封完结整小时; 未完结留累计器; 重复 flush 不重
    append(水位 = agg 文件尾, 字节级不变)"""
    clock = FakeClock(start=_local_epoch(10, 0, 10))
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30), clock=clock)
    mgr.store.server_state = server_state()
    mod = mgr.host.get("qb_traffic")
    h0 = int(clock.now()) // HOUR_SECONDS * HOUR_SECONDS
    _run_sample(mgr)  # 首样 r@h0+10(块 A 首, 信用开立)
    _flush(mod)
    assert _agg_text(tmp_path, GLOBAL_SERIES_KEY) is None  # 小时未完结: 零 agg 行
    for _ in range(120):  # 30s 连续采样跨过小时界(v4 条件结算: 块间 gap 恰一间隔, 覆盖连续)
        clock.advance(30)
        _run_sample(mgr)
    text = _agg_text(tmp_path, GLOBAL_SERIES_KEY)  # 完结小时已在途中 flush 时点封口
    parsed = parse_v4_agg_text(text)
    assert len(parsed.hours) == 1 and parsed.hours[0].epoch == h0  # 完结小时封口
    assert parsed.hours[0].cov_s == 3590  # [h0+10, h1) 覆盖(采样断档才会真空, 连续采样不丢)
    assert len(parsed.days) == 0 and len(parsed.months) == 0  # 日/月未完结
    _flush(mod)  # 重复 flush: 无新完结层级
    assert _agg_text(tmp_path, GLOBAL_SERIES_KEY) == text  # 字节级不变(不重 append)


def test_recovery_catchup_equivalent_to_uninterrupted(tmp_path, monkeypatch):
    """catch-up 补算等价(§4.3): 停机(崩溃无 stop)数小时后重启, 重启侧 hour/day/month
    行补齐且与不停机等价序列逐列一致 —— 停机期真空两侧同形(块间 gap), 补算源 = 窗口内
    天文件 raw 逐槽前向记账"""
    base = int(datetime(2026, 1, 31, 22, 0, 0).timestamp())  # 月末 22:00(跨日 + 跨月)
    t1, t2, t3 = base + 10, base + 40, base + 70
    flush1 = base + 90  # 22:01:30: 天文件落盘(小时未完结)
    t4 = int(datetime(2026, 2, 1, 0, 0, 10).timestamp())  # 次日 00:00:10
    flush_end = t4 + 30
    clock = FakeClock(start=t1)

    def _run(mgr, times):
        for t in times:
            clock.freeze(t)
            mgr.store.server_state = server_state(
                alltime_dl=1_000_000 + t, alltime_ul=2_000_000 + t, dl_info_speed=100, up_info_speed=50
            )
            _run_sample(mgr)

    # 不停机序列: 3 样 + flush + 次日首样 + 末日 flush
    mgr_a = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30), clock=clock)
    mod_a = mgr_a.host.get("qb_traffic")
    _run(mgr_a, [t1, t2, t3])
    clock.freeze(flush1)
    _flush(mod_a)
    _run(mgr_a, [t4])
    clock.freeze(flush_end)
    _flush(mod_a)
    parsed_a = parse_v4_agg_text(_agg_text(tmp_path, GLOBAL_SERIES_KEY))
    assert len(parsed_a.hours) == 1 and len(parsed_a.days) == 1 and len(parsed_a.months) == 1

    # 停机序列: 同样 3 样 + flush 后崩溃(无 stop), 重启于次日 00:00:10
    tmp_b = tmp_path / "b"
    tmp_b.mkdir()
    mgr_b1 = _mgr_with_traffic(tmp_b, QbTraffic(enabled=True, sample_interval=30), clock=clock)
    mod_b1 = mgr_b1.host.get("qb_traffic")
    _run(mgr_b1, [t1, t2, t3])
    clock.freeze(flush1)
    _flush(mod_b1)
    mgr_b2 = _mgr_with_traffic(tmp_b, QbTraffic(enabled=True, sample_interval=30), clock=clock)  # 重启: 全新模块实例
    mod_b2 = mgr_b2.host.get("qb_traffic")
    clock.freeze(t4)
    mod_b2.start(mgr_b2.ctx, dry_run=False)  # 恢复 + catch-up(先于一切采样)
    recovered = parse_v4_agg_text(_agg_text(tmp_b, GLOBAL_SERIES_KEY))
    assert len(recovered.hours) == 1 and recovered.hours[0].cov_s == 60  # 补算行与在线封口一致
    _run(mgr_b2, [t4])
    clock.freeze(flush_end)
    _flush(mod_b2)
    parsed_b = parse_v4_agg_text(_agg_text(tmp_b, GLOBAL_SERIES_KEY))
    assert parsed_b.hours == parsed_a.hours  # 补算 = 在线(停机真空两侧同形)
    assert parsed_b.days == parsed_a.days and parsed_b.months == parsed_a.months


def test_recovery_hard_order_catchup_before_trim(tmp_path, monkeypatch):
    """硬序(§4.3 验收): hour 行已到龄而其 day 行未封 —— 重启恢复必须先由到龄 hour 行
    补出 day/month 行, 之后才裁剪 hour 行; 若先裁后补, day 行将永久丢失(测试钉住)"""
    window = 30 * 86400.0
    now = v4_date_str_epoch("2026-03-20") + 12 * HOUR_SECONDS
    h_old = now - int(window) - 2 * HOUR_SECONDS
    aged = AggRow("hour", h_old, 7, 9, 3, 4, 500, 600, 3600)
    TrafficV4Store(str(tmp_path)).append_agg_rows("torrent:OLD", (aged, ))  # 只有到龄 hour 行, 无 day 行
    clock = FakeClock(start=now)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30), clock=clock)
    mgr.host.get("qb_traffic").start(mgr.ctx, dry_run=False)  # 恢复(catch-up -> 裁剪)
    parsed = parse_v4_agg_text(_agg_text(tmp_path, "torrent:OLD"))
    assert parsed.hours == ()  # 到龄 hour 行最终被裁
    day_expected = v4_rollup_agg("day", v4_day_epoch(h_old), (aged, ))
    assert parsed.days == (day_expected, )  # day 行由到龄 hour 行补出(catch-up 先于裁剪的铁证)
    assert parsed.months == (v4_rollup_agg("month", v4_month_epoch(h_old), (day_expected, )), )


def test_recovery_idempotent_watermark_torn_and_duplicate(tmp_path, monkeypatch):
    """幂等与坏行(§4.4): 重启从文件尾恢复水位 —— 已有 hour 行不重算; 同 epoch 重复行
    取最后一行; 撕裂残行按坏行纪律跳过; 二次重启零追加(字节级不变, 不重 append)"""
    now = v4_date_str_epoch("2026-03-05") + 12 * HOUR_SECONDS
    d4 = v4_date_str_epoch("2026-03-04")
    h1 = d4 + 10 * HOUR_SECONDS
    st = TrafficV4Store(str(tmp_path))
    st.append_agg_rows(
        "global",
        (
            AggRow("hour", h1, 1, 1, 1, 1, 1, 1, 3600),
            AggRow("hour", h1, 2, 3, 4, 5, 6, 7, 3600),  # 同 epoch 重复: 后值胜
        )
    )
    path = v4_agg_file_path(str(tmp_path), "global")
    with open(path, "a", encoding="utf-8", newline="") as f:  # 撕裂残行(无换行, 畸形)
        f.write("hour,not,a,valid,row")
    clock = FakeClock(start=now)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30), clock=clock)
    mgr.host.get("qb_traffic").start(mgr.ctx, dry_run=False)
    parsed = parse_v4_agg_text(_agg_text(tmp_path, "global"))
    assert [h.dl_avg for h in parsed.hours] == [2] and [h.epoch for h in parsed.hours] == [h1]
    text1 = _agg_text(tmp_path, "global")
    assert "hour,not,a,valid,row" in text1  # 撕裂行跳过不崩溃(按坏行纪律留原样)
    assert len(parsed.days) == 1  # day 行由文件内 hour 行补出(catch-up: day <- agg 内 hour 行)
    mgr2 = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30), clock=clock)
    mgr2.host.get("qb_traffic").start(mgr2.ctx, dry_run=False)  # 二次重启: 水位从文件尾推
    assert _agg_text(tmp_path, "global") == text1  # 零追加(不重 append, 字节级不变)


def test_evict_at_flush_throttle_and_memory_cleanup(tmp_path):
    """淘汰触发点(§4.5): flush 时点触发, 扫描节流 EVICT_CHECK_INTERVAL_S; 超龄系列整
    目录删除且内存缓存(累计器/数据门/基线/镜像/缓冲/游程)同步清理; 全局豁免;
    dry_run 静默跳过"""
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mod = mgr.host.get("qb_traffic")
    conf = mgr.config.qb_traffic
    now = 1_760_000_000.0
    old_d = v4_epoch_date_str(now - 40 * 86400)
    for key in ("torrent:OLD", "torrent:OLD2"):
        _write_day_file(tmp_path, key, old_d)
    _write_day_file(tmp_path, "global", old_d)  # 全局豁免
    key = "torrent:OLD"
    mod._agg_state(key)  # 预置内存缓存(淘汰须全清)
    mod._has_data.add(key)
    mod._no_data.add(key)
    mod._baselines[key] = {"dl_total": 1, "up_total": 2}
    mod.latest[key] = "stale"
    mod._buffers[key] = "stale"
    mod._open_runs[key] = "stale"
    mod._maybe_evict(conf, now)  # 首扫: OLD 淘汰
    assert not os.path.exists(v4_series_dir(str(tmp_path), key))
    assert key not in mod._agg_states and key not in mod._has_data and key not in mod._no_data
    assert key not in mod._baselines and key not in mod.latest
    assert key not in mod._buffers and key not in mod._open_runs
    assert os.path.exists(v4_series_dir(str(tmp_path), "global"))
    _write_day_file(tmp_path, "torrent:OLD2", old_d)
    mod._maybe_evict(conf, now + 100)  # 节流窗内: 不重扫
    assert os.path.exists(v4_series_dir(str(tmp_path), "torrent:OLD2"))
    mod._maybe_evict(conf, now + EVICT_CHECK_INTERVAL_S)  # 节流窗过: 淘汰
    assert not os.path.exists(v4_series_dir(str(tmp_path), "torrent:OLD2"))
    _write_day_file(tmp_path, "torrent:OLD3", old_d)
    mod._persistence_on = False  # dry_run: 淘汰写操作静默跳过
    mod._maybe_evict(conf, now + 2 * EVICT_CHECK_INTERVAL_S)
    assert os.path.exists(v4_series_dir(str(tmp_path), "torrent:OLD3"))


def test_agg_trim_piggyback_on_hour_seal(tmp_path):
    """hour 裁剪 piggyback(§4.5): hour 封口时点触发, 判据用内存最老行(earliest_hour,
    零常规文件读); 到龄行重写并回写新最老; 无到龄行只追加不重写"""
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mod = mgr.host.get("qb_traffic")
    key = GLOBAL_SERIES_KEY
    window = 30 * 86400
    base = _AGG_H0
    now = base + 3 * HOUR_SECONDS + 100
    h_old = base - window - 2 * HOUR_SECONDS
    TrafficV4Store(str(tmp_path)).append_agg_rows(key, (AggRow("hour", h_old, 9, 9, 9, 9, 9, 9, 3600), ))
    agg = mod._agg_state(key)
    agg.earliest_hour = h_old  # 恢复预置的内存最老行判据
    obs = [(100, 50, 1, 2), (200, 60, 3, 4), (300, 70, 5, 6)]
    _feed_30s(mod, key, base, obs)
    mod._agg_flush_series(key, now=now)  # hour 封口 + piggyback 裁剪
    parsed = parse_v4_agg_text(_agg_text(tmp_path, key))
    assert [x.epoch for x in parsed.hours] == [base]  # 到龄行裁掉, 新行在
    assert agg.earliest_hour == base  # 裁剪结果回写内存判据
    text1 = _agg_text(tmp_path, key)
    _feed_30s(mod, key, base + HOUR_SECONDS, obs)
    mod._agg_flush_series(key, now=now)  # 第二个完结小时: 无到龄行
    parsed = parse_v4_agg_text(_agg_text(tmp_path, key))
    assert [x.epoch for x in parsed.hours] == [base, base + HOUR_SECONDS] and agg.earliest_hour == base
    assert _agg_text(tmp_path, key).startswith(text1)  # 只追加, 无重写


def test_agg_trim_engages_for_runtime_created_series(tmp_path):
    """守阵(26-10-06-0028 C-01): 运行期新建系列(全新安装 global / 新种子 / 热重载启用,
    不经 _recover_series)满窗后裁剪生效 —— earliest_hour 在 _agg_ingest_hour 入账时
    初始化 + min 更新, hour 行数有界(修复前判据恒 None, _agg_trim 恒早退, 无界增长)"""
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mod = mgr.host.get("qb_traffic")
    key = GLOBAL_SERIES_KEY
    window = 30 * 86400
    base = _AGG_H0
    now = base + 3 * HOUR_SECONDS + 100
    obs = [(100, 50, 1, 2), (200, 60, 3, 4), (300, 70, 5, 6)]
    agg = mod._agg_state(key)
    assert agg.earliest_hour is None  # 运行期新建: 无恢复判据
    _feed_30s(mod, key, base, obs)
    mod._agg_flush_series(key, now=now)  # 首个完结小时入账: 判据就地初始化
    assert agg.earliest_hour == base
    assert [x.epoch for x in parse_v4_agg_text(_agg_text(tmp_path, key)).hours] == [base]
    # 时间推进到首行到龄: 运行期继续产数据并封口
    later = base + window + 5 * HOUR_SECONDS
    _feed_30s(mod, key, base + window + 3 * HOUR_SECONDS, obs)
    mod._agg_flush_series(key, now=later)
    parsed = parse_v4_agg_text(_agg_text(tmp_path, key))
    assert [x.epoch for x in parsed.hours] == [base + window + 3 * HOUR_SECONDS], "到龄首行被裁, hour 行有界"
    assert agg.earliest_hour == base + window + 3 * HOUR_SECONDS, "裁剪结果回写内存判据"


def test_agg_defensive_paths_cascades_and_write_failure(tmp_path, monkeypatch):
    """S2b 防御面与级联: 空 key flush / 零长区间 / 空桶不产行 / 跨日滞留单次 flush 级联
    封前一日(_agg_ingest_hour else)/ 月级联(_agg_ingest_day else); agg append 与裁剪
    OSError 告警不上抛(连续失败只告警一次); 淘汰扫描 OSError 下轮重试"""
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mod = mgr.host.get("qb_traffic")
    key = GLOBAL_SERIES_KEY
    assert mod._agg_flush_series("unknown", now=0) is False  # 无累计器系列: 零操作
    empty = {}
    TrafficSampleModule._agg_credit_hours(empty, 5.0, 5.0, 1, 1, 1, 1)  # 零长区间: 不入账
    assert empty == {}
    # 空桶(全 null 覆盖小时): 弹出不产行
    agg = mod._agg_state(key)
    agg.pending[_AGG_H0] = []
    mod._agg_flush_series(key, now=_AGG_H0 + HOUR_SECONDS)
    assert _AGG_H0 not in agg.pending and _agg_text(tmp_path, key) is None
    # 跨日滞留(暂停恢复): 单次 flush 内前一日经 day 级联封口, 跨月月行经月检查封口
    day31, feb1 = int(datetime(2026, 1, 31).timestamp()), int(datetime(2026, 2, 1).timestamp())
    for h, dl in ((day31 + 22 * HOUR_SECONDS, 100), (day31 + 23 * HOUR_SECONDS, 200), (feb1, 300)):
        agg.pending[h] = [V4HourSample(dl, dl, dl, dl, 3600.0)]
    mod._agg_flush_series(key, now=feb1 + HOUR_SECONDS + 1800)
    parsed = parse_v4_agg_text(_agg_text(tmp_path, key))
    assert len(parsed.hours) == 3 and len(parsed.days) == 1 and len(parsed.months) == 1
    assert parsed.days[0].epoch == day31 and agg.day_epoch == feb1  # 前一日级联封口, 新日累计器开
    # 月级联(_agg_ingest_day else): 开放月内到达下一月 day 行 -> 级联封前一月
    day_jan = ts_mod.v4_rollup_agg("day", day31, (AggRow("hour", day31, 1, 1, 1, 1, 1, 1, 3600), ))
    day_feb = ts_mod.v4_rollup_agg("day", feb1, (AggRow("hour", feb1, 2, 2, 2, 2, 2, 2, 3600), ))
    agg.month_epoch, agg.month_days = v4_month_epoch(day31), [day_jan]
    out = []
    TrafficSampleModule._agg_ingest_day(agg, day_feb, out)
    assert len(out) == 2 and out[0] == day_feb  # 本行(day)随批落盘 + 级联月行
    assert out[1].kind == "month" and out[1].epoch == v4_month_epoch(day31)
    assert agg.month_epoch == v4_month_epoch(feb1)

    # agg append OSError: 告警不上抛, 连续失败只告警一次(第二条走 debug)
    def _raise(self, key, rows):
        raise OSError(28, "disk full")

    monkeypatch.setattr(TrafficV4Store, "append_agg_rows", _raise)
    agg.pending[_AGG_H0 + 5 * HOUR_SECONDS] = [V4HourSample(100, 50, 1, 2, 3600.0)]
    with capture_logs("auto_qb.core.modules.traffic_sample_mod") as cap:
        assert mod._agg_flush_series(key, now=_AGG_H0 + 6 * HOUR_SECONDS) is False
        agg.pending[_AGG_H0 + 6 * HOUR_SECONDS] = [V4HourSample(100, 50, 1, 2, 3600.0)]
        assert mod._agg_flush_series(key, now=_AGG_H0 + 7 * HOUR_SECONDS) is False
    assert cap.text.count("agg 行落盘失败") == 2  # 首次 WARNING + 持续期 DEBUG(防刷屏)
    # 裁剪 OSError: 告警, 内存判据不变(下轮重试); 淘汰扫描 OSError: 告警不上抛
    agg.earliest_hour = _AGG_H0
    monkeypatch.setattr(TrafficV4Store, "trim_agg_hours", lambda s, k, n, w: (_ for _ in ()).throw(OSError(1, "x")))
    with capture_logs("auto_qb.core.modules.traffic_sample_mod") as cap2:
        mod._agg_trim(key, agg, _AGG_H0 + 40 * 86400, 30 * 86400)
    assert "裁剪失败" in cap2.text and agg.earliest_hour == _AGG_H0
    monkeypatch.setattr(TrafficV4Store, "evict_expired_series", lambda s, n, w: (_ for _ in ()).throw(OSError(1, "x")))
    mod._last_evict_check = None
    with capture_logs("auto_qb.core.modules.traffic_sample_mod") as cap3:
        mod._maybe_evict(mgr.config.qb_traffic, 1_760_000_000.0)
    assert "淘汰扫描失败" in cap3.text
    # 同月新日并入 month 累计器(_agg_ingest_day 同月追加支); 裁剪判据 earliest None 零操作
    day_feb2 = ts_mod.v4_rollup_agg("day", feb1 + 86400, (AggRow("hour", feb1, 3, 3, 3, 3, 3, 3, 3600), ))
    out2 = []
    TrafficSampleModule._agg_ingest_day(agg, day_feb2, out2)
    assert len(agg.month_days) == 2 and out2 == [day_feb2]
    agg.earliest_hour = None
    mod._agg_trim(key, agg, _AGG_H0 + 40 * 86400, 30 * 86400)  # 无判据: 不读不写
    # dry_run: agg append 静默跳过(_agg_append False 支)
    mod._persistence_on = False
    agg.pending[_AGG_H0 + 8 * HOUR_SECONDS] = [V4HourSample(100, 50, 1, 2, 3600.0)]
    assert mod._agg_flush_series(key, now=_AGG_H0 + 9 * HOUR_SECONDS) is False
    assert _AGG_H0 + 8 * HOUR_SECONDS not in agg.pending  # 封口内存照常推进, 写跳过


def test_live_tail_published_per_round_and_cleared_by_flush(tmp_path, monkeypatch):
    """(S6)活尾快照发布: 每轮 handler 末尾整体替换 live_tail —— 非零轮 = 未落盘 buffer
    记录(block_open/head_pending 如实)+ 开放游程冻结副本; flush 后 records 清空(磁盘接管);
    断连轮 n 游程入快照; 运行期关闭不发布(引用保持旧值, 端点由 feature 判定兜底)"""
    from auto_qb.core.traffic_store import LiveTail

    clock = FakeClock()
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30, flush_interval=60), clock=clock)
    mod = mgr.host.get("qb_traffic")
    assert mod.live_tail == {}  # 初始空表
    # 首轮(非零): r 进缓冲未落盘 -> head_pending=True, records 恰为 buffer 内容
    mgr.store.server_state = server_state()
    _run_sample(mgr)
    tail = mod.live_tail.get(GLOBAL_SERIES_KEY)
    assert isinstance(tail, LiveTail) and tail.block_open and tail.head_pending
    assert tail.records == tuple(mod._buffers[GLOBAL_SERIES_KEY].records)
    assert tail.start_epoch == mod._buffers[GLOBAL_SERIES_KEY].start_epoch
    assert tail.open_run is None and tail.interval_s == 30
    # 次轮(零速): z 游程开启 -> 快照携冻结副本(records 不变, 游程随样本推进)
    mgr.store.server_state = server_state(dl_info_speed=0, up_info_speed=0)
    _run_sample(mgr)
    tail = mod.live_tail[GLOBAL_SERIES_KEY]
    assert tail.open_run is not None and tail.open_run.kind == "z" and tail.open_run.samples == 1
    run_before = tail.open_run
    clock.advance(30)
    _run_sample(mgr)
    tail = mod.live_tail[GLOBAL_SERIES_KEY]
    assert tail.open_run.samples == 2 and tail.open_run is not run_before  # 冻结副本非原对象
    assert tail.records == tuple(mod._buffers[GLOBAL_SERIES_KEY].records)
    # flush 到点: 记录落盘 -> 快照 records 清空(磁盘接管), 开放游程照常携带
    clock.advance(60)
    mgr.store.server_state = server_state(dl_info_speed=0, up_info_speed=0)
    _run_sample(mgr)
    tail = mod.live_tail[GLOBAL_SERIES_KEY]
    assert tail.records == () and mod._buffers[GLOBAL_SERIES_KEY].records == []
    assert _v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now()) is not None
    # 断连轮: n 游程入快照
    mgr.client = None
    clock.advance(30)
    _run_sample(mgr)
    tail = mod.live_tail[GLOBAL_SERIES_KEY]
    assert tail.open_run is not None and tail.open_run.kind == "n"
    # 运行期关闭: handler 短路不发布(live_tail 保持旧值, 端点按 feature 判定兜底)
    mgr.client = FakeClient()
    mgr.config.qb_traffic = QbTraffic(enabled=False, sample_interval=30, flush_interval=60)
    clock.advance(30)
    _run_sample(mgr)
    assert mod.live_tail[GLOBAL_SERIES_KEY].open_run.kind == "n"  # 未被本轮改写


def test_live_tail_pending_agg_published_and_cleared_by_seal(tmp_path, monkeypatch):
    """(S7)活尾 pending_agg 发布(agg 段窗图尾真空修复, 2026-10-14 用户报「3 天及以上
    视图只显示到 14 日 0 点, 实际已到 1 点」): 未封口当前小时部分行随快照发布(hour 行
    dt 加权口径与封口行同函数); 开放日/月部分行随累计器层级产出(严格逐级); 小时封口后
    该桶 hour 部分行消失(磁盘接管)而开放日部分行仍在; flush 清空 records 后系列凭
    pending_agg 继续进快照(raw 面磁盘接管, agg 面继续增益 —— 修复前无记录无游程的
    系列整个不进快照); 无累计器/空 pending 不出行; 跨日残余 pending 不进当日部分行"""
    from auto_qb.core.modules.traffic_sample_mod import SeriesAgg, _pending_agg_rows
    from auto_qb.core.traffic_store import V4HourSample

    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30, flush_interval=600))
    mod = mgr.host.get("qb_traffic")
    key = GLOBAL_SERIES_KEY
    h0 = _AGG_H0
    # 累计器直喂(与 handler 内 _agg_feed 同口径): r1 开信用 -> r2 结算 [h0, h0+1838)
    # -> r3 结算 [h0+1838, h0+3600); now 落在小时界上(已完结未 flush)
    mod._agg_feed(key, V4Sample(100, 50, 1000, 2000), h0, h0, True, 30.0)
    mod._agg_feed(key, V4Sample(200, 60, 2000, 3000), h0, h0 + 1838, False, 30.0)
    mod._agg_feed(key, V4Sample(300, 70, 3000, 4000), h0 + 1838, h0 + 3600, False, 30.0)
    now = h0 + HOUR_SECONDS
    rows = _pending_agg_rows(mod._agg_states[key], None, now)
    hours = [r for r in rows if r.kind == "hour"]
    assert hours == [AggRow("hour", h0, 149, 200, 55, 60, 2000, 3000, 3600)]  # dt 加权 + 级末快照
    day = [r for r in rows if r.kind == "day"]
    assert day == [AggRow("day", v4_day_epoch(h0), 149, 200, 55, 60, 2000, 3000, 3600)]  # 开放日 = 当日 pending
    month = [r for r in rows if r.kind == "month"]
    assert month == [AggRow("month", v4_month_epoch(h0), 149, 200, 55, 60, 2000, 3000, 3600)]  # 开放月逐级
    # 小时封口: hour 部分行消失(磁盘接管), 开放日部分行仍在(日未封)
    assert mod._agg_flush_series(key, now=now) is True
    rows = _pending_agg_rows(mod._agg_states[key], None, now)
    assert [r for r in rows if r.kind == "hour"] == []
    assert [r for r in rows if r.kind == "day"] == day  # 日累计器持已封 hour 行, 部分行照发
    # 无累计器/空 pending: 不出行
    assert _pending_agg_rows(SeriesAgg(), None, h0) == ()
    # 跨日残余: 前一日的 pending 小时不进当日 day 部分行(hour 部分行照发, 读侧与磁盘行合流)
    agg2 = SeriesAgg()
    prev_h = v4_day_epoch(h0) - HOUR_SECONDS
    agg2.pending[prev_h] = [V4HourSample(100, 50, 1000, 2000, 1800.0)]
    agg2.day_epoch = v4_day_epoch(h0)
    rows2 = _pending_agg_rows(agg2, None, h0 + 1800)
    assert [r.epoch for r in rows2 if r.kind == "hour"] == [prev_h]
    assert [r for r in rows2 if r.kind == "day"] == []  # 当日无 pending 无已封小时 -> 不出日行

    # 端到端发布面: handler 两轮后 pending_agg 非空; flush 清空 records 后系列仍在快照里
    clock = FakeClock(start=h0 + 1800)
    pub = tmp_path / "pub"
    pub.mkdir()
    mgr2 = _mgr_with_traffic(pub, QbTraffic(enabled=True, sample_interval=30, flush_interval=600), clock=clock)
    mgr2.store.server_state = server_state(dl_info_speed=100, up_info_speed=50, alltime_dl=1000, alltime_ul=2000)
    mod2 = mgr2.host.get("qb_traffic")
    _run_sample(mgr2)  # t=h0+1800: r 开信用(pending 尚空)
    clock.advance(30)
    _run_sample(mgr2)  # t=h0+1830: 结算 [h0+1800, h0+1830) -> pending[h0] 有样本
    tail = mod2.live_tail[GLOBAL_SERIES_KEY]
    assert [r for r in tail.pending_agg if r.kind == "hour"] == [AggRow("hour", h0, 100, 100, 50, 50, 1000, 2000, 30)]
    assert [r for r in tail.pending_agg if r.kind == "day"] == [
        AggRow("day", v4_day_epoch(h0), 100, 100, 50, 50, 1000, 2000, 30)
    ]
    mod2._flush_all_series()  # raw 面落盘: records 清空 + 块复位(h0 未封口)
    mod2._publish_live_tail()
    tail = mod2.live_tail[GLOBAL_SERIES_KEY]
    assert tail.records == () and tail.block_open is False  # raw 面磁盘接管
    assert [r for r in tail.pending_agg if r.kind == "hour"]  # agg 面未封口照常发布(修复前整个键消失)


# ---------- v4 定约用例(plan 26-10-05-2200 §04 表 3/5/6/7, B2 落地) ----------
def test_v4_counter_reset_forces_block_reopen(tmp_path, monkeypatch):
    """3. 计数器重置强制关块(v4 §01 关块状态机): 重置(cur < 块内最近 totals)后块内负
    delta 不出现, 新块基线 = 重置后 totals(首记录 delta = 0); 旧块以重置前观测收尾"""
    clock = FakeClock()
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30, flush_interval=10**9), clock=clock)
    mgr.store.server_state = server_state(alltime_dl=1000, alltime_ul=500, dl_info_speed=100, up_info_speed=50)
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)  # t0: r(totals 1000/500, 块 A 首立基线)
    clock.advance(30)
    mgr.store.server_state = server_state(alltime_dl=1600, alltime_ul=900, dl_info_speed=100, up_info_speed=50)
    _run_sample(mgr)  # t0+30: r(totals 1600/900)
    clock.advance(30)
    mgr.store.server_state = server_state(alltime_dl=800, alltime_ul=900, dl_info_speed=100, up_info_speed=50)
    _run_sample(mgr)  # t0+60: dl 回落(qB 重置) -> 强制关块重开, 新块基线 = (800, 900)
    clock.advance(30)
    mgr.store.server_state = server_state(alltime_dl=1200, alltime_ul=1300, dl_info_speed=100, up_info_speed=50)
    _run_sample(mgr)  # t0+90: 新块内正常增量
    _flush(mod)
    parsed = _v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now())
    assert parsed.bad_lines == 0 and len(parsed.blocks) == 2  # 重置点拆两块
    b1, b2 = parsed.blocks
    assert (b1.dl_base, b1.up_base) == (1000, 500)
    assert [(r.dl_total, r.up_total) for r in b1.records] == [(1000, 500), (1600, 900)]
    assert (b2.dl_base, b2.up_base) == (800, 900)  # 新块基线 = 重置后 totals
    assert [(r.dl_total, r.up_total) for r in b2.records] == [(800, 900), (1200, 1300)]
    # 块内负 delta 不出现: 全部 r 行 delta 列非负(解析零坏行 + 文本逐行核对双保险)
    text = _v4_path(tmp_path, GLOBAL_SERIES_KEY, clock.now()).read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("r,"):
            assert all(int(col) >= 0 for col in line.split(",")[3:5]), line


def test_v4_cross_block_settlement_online_offline_same_source(tmp_path):
    """5. 跨块覆盖结算两路同源(v4 §01「覆盖结算」): 在线 _agg_feed 与离线
    _agg_credit_day_file 复用同一判定单点 v4_block_gap_continuous —— 对同一 v4 天文件
    (连续边界 / 崩溃间隙 / 00:00 跨天边界)产出逐桶一致 cov_s; 间隙真空两侧同形不虚记"""
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mod = mgr.host.get("qb_traffic")
    key = GLOBAL_SERIES_KEY
    day1 = int(datetime(2026, 6, 1).timestamp())
    day2 = day1 + 86400
    h0 = day1 + HOUR_SECONDS  # hour 对齐桶(块 1-3 全落此桶)
    t0 = h0 + 10
    # 块 1: r@t0 / r@t0+30; 块 2 连续(B.start = t0+60, gap 30 <= interval+DRIFT_TOL);
    # 块 3 崩溃间隙(B.start = t0+1000, gap >> interval -> 真空); 块 4 末日末槽 = day2-30
    b1 = V4Block(t0, 30, 100, 200, (V4Sample(100, 50, 100, 200), V4Sample(100, 50, 160, 260)))
    b2 = V4Block(t0 + 60, 30, 300, 400, (V4Sample(200, 80, 300, 400), ))
    b3 = V4Block(t0 + 1000, 30, 500, 600, (V4Sample(300, 90, 500, 600), ))
    b4 = V4Block(day2 - 60, 30, 700, 800, (V4Sample(100, 50, 700, 800), V4Sample(100, 50, 760, 860)))
    c1 = V4Block(day2, 30, 900, 1000, (V4Sample(200, 80, 900, 1000), ))  # 次日首块(gap 30, 跨天连续)
    text1 = format_v4_day_text("global", (b1, b2, b3, b4))
    text2 = format_v4_day_text("global", (c1, ))

    def feed_block(blk) -> None:
        """把单个块按写侧游标推进口径回放进线 _agg_feed(槽位与 v4_block_slots 同源)"""
        slots = v4_block_slots(blk)
        idx = 0
        for i, rec in enumerate(blk.records):
            n = 1 if isinstance(rec, V4Sample) else rec.run_len
            anchor = float(blk.start_epoch) if i == 0 else slots[idx - 1].ts
            mod._agg_feed(key, rec, anchor, slots[idx + n - 1].ts, i == 0, blk.interval_s)
            idx += n

    for blk in (b1, b2, b3, b4, c1):
        feed_block(blk)
    pending_off = {}
    tail = TrafficSampleModule._agg_credit_day_file(pending_off, parse_v4_day_text(text1), None)
    TrafficSampleModule._agg_credit_day_file(pending_off, parse_v4_day_text(text2), tail)

    def cov_map(pending):
        return {h: round(sum(s.dt_s for s in samples), 6) for h, samples in pending.items()}

    # 两路逐桶一致(核心断言: 同一判定单点 -> 镜像保证)
    assert cov_map(mod._agg_states[key].pending) == cov_map(pending_off)
    # 连续边界: 两段各 30s 入账; 崩溃间隙: 真空零入账; 00:00 跨天边界: 连续结算
    assert cov_map(pending_off) == {h0: 60.0, day2 - HOUR_SECONDS: 60.0}
    assert all(s.dl_rate == 100 and s.up_rate == 50 for s in pending_off[h0])  # 按上一记录速率结算


# ---------- 启动恢复按需读集(plan 26-10-12-2010, D1/D4/D5) ----------
def test_recovery_read_set_bounded_to_watermark_day(tmp_path, monkeypatch):
    """恢复读集按需(D1 验收): 24 系列 x 30 天天文件 + 水位在昨日的 agg -> start() 后逐系列
    只读 [水位日, 今日] 至多 2 个天文件(recovery_reads 计数属性机检, 不随
    rollup_window=1000000D 放大), agg.dat 按系列照读(D4); 水位封口小时不重算, 补算只
    覆盖水位之后小时; 二次重启零追加(水位推进后读集缩到当日)"""
    window = 1000000 * 86400.0  # 生产口径: 永久保留(恢复读集必须与它解耦, D2 不动)
    now = _local_epoch(13, 0, 30)  # 今日 13:00:30(本地)
    clock = FakeClock(start=now)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30, rollup_window=window), clock=clock)
    st = TrafficV4Store(str(tmp_path))
    today_str = v4_epoch_date_str(now)
    y_str = v4_epoch_date_str(now - 86400)
    wm = v4_date_str_epoch(y_str) + 10 * HOUR_SECONDS  # 昨日 10:00 封口水位(agg 文件尾)
    keys = [GLOBAL_SERIES_KEY] + [f"torrent:K{i:02d}" for i in range(1, 24)]  # 24 系列
    for key in keys:
        st.append_agg_rows(key, (AggRow("hour", wm, 7, 9, 3, 4, 500, 600, 3600), ))
        for i in range(30):  # 30 天天文件(今日-29d .. 今日): 更早日历文件在场, 但不该被读
            d = v4_epoch_date_str(now - i * 86400)
            if d == y_str:  # 水位日: 12:00 块(水位之后 -> 补算)
                st.append_records(
                    key,
                    d,
                    (v4_date_str_epoch(d) + 12 * HOUR_SECONDS + 10, 30),
                    (V4Sample(100, 50, 1000, 2000), V4Sample(200, 60, 2000, 3000), V4Sample(300, 70, 3000, 4000)),
                    (1000, 2000),
                )
            elif d == today_str:  # 今日: 00:30 块(已封口小时 -> 补算)
                st.append_records(
                    key,
                    d,
                    (v4_date_str_epoch(d) + 30 * 60 + 10, 30),
                    (V4Sample(10, 5, 100, 200), V4Sample(20, 6, 200, 300)),
                    (100, 200),
                )
            else:  # 更早日期: 空壳天文件(只占目录, 证明恢复不碰)
                _write_day_file(tmp_path, key, d)
    mod = mgr.host.get("qb_traffic")
    mod.start(mgr.ctx, dry_run=False)  # 恢复 + catch-up(先于一切采样)
    reads, stats = mod.recovery_reads, mod.recovery_stats
    assert stats["series"] == 24
    assert stats["day_files"] == 48  # 24 系列 x [水位日, 今日](旧口径此处为 ~29 x 24)
    assert stats["hours"] == 48  # 每系列补算 2 个小时(昨日 12:00 + 今日 00:00)
    assert stats["slots"] == 120  # 每系列 3 + 2 槽
    for key in keys:
        r = reads[key]
        assert r["bound"] == "watermark"
        assert r["day_dates"] == (y_str, today_str)  # 读集 = 水位日 -> 今日, 至多 2 个
        assert r["new_hours"] == 2 and r["slots"] == 5
    # 正确性: 水位行不重算 + 水位之后两个 hour 行补齐(逐系列)
    for key in keys:
        parsed = parse_v4_agg_text(_agg_text(tmp_path, key))
        assert [h.epoch for h in parsed.hours] == [wm, wm + 2 * HOUR_SECONDS, v4_date_str_epoch(today_str)]
        assert parsed.hours[1].cov_s == 60 and parsed.hours[2].cov_s == 30  # 昨日块 3 条记录 2 区间 60s / 今日块 2 条 30s(末槽待后续到达)
    # 幂等: 二次重启零追加(字节级不变), 水位推进后读集缩到当日 1 个
    text = _agg_text(tmp_path, GLOBAL_SERIES_KEY)
    mgr2 = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30, rollup_window=window), clock=clock)
    mod2 = mgr2.host.get("qb_traffic")
    mod2.start(mgr2.ctx, dry_run=False)
    assert _agg_text(tmp_path, GLOBAL_SERIES_KEY) == text
    assert mod2.recovery_reads[GLOBAL_SERIES_KEY]["day_dates"] == (today_str, )
    assert mod2.recovery_stats["day_files"] == 24  # 每系列只读当日


def test_recovery_fallback_full_read_when_agg_missing(tmp_path, monkeypatch):
    """恢复兜底(D5, §5): agg.dat 缺失(无 hour 行 -> 无可用水位)-> 退回现口径
    now - rollup_window 全量读(诚实兜底不猜不静默), 读集 = 窗内全部天文件, catch-up
    补算与现行为照常(hour 行逐日补齐); bound=fallback 且 INFO 留痕"""
    window = 3 * 86400.0
    now = _local_epoch(13, 0, 30)
    clock = FakeClock(start=now)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30, rollup_window=window), clock=clock)
    st = TrafficV4Store(str(tmp_path))
    key = GLOBAL_SERIES_KEY
    dates = [v4_epoch_date_str(now - i * 86400) for i in range(3)]  # 今日-2d .. 今日, 全在窗内
    for i, d in enumerate(dates):
        st.append_records(
            key,
            d,
            (v4_date_str_epoch(d) + 30 * 60 + 10, 30),
            (V4Sample(10 + i, 5, 100, 200), V4Sample(20, 6, 200, 300)),
            (100, 200),
        )
    with capture_logs("auto_qb.core.modules.traffic_sample_mod") as logs:
        mgr.host.get("qb_traffic").start(mgr.ctx, dry_run=False)
    r = mgr.host.get("qb_traffic").recovery_reads[key]
    assert r["bound"] == "fallback"
    assert set(r["day_dates"]) == set(dates)  # 全量兜底: 不收敛(与现口径逐字一致)
    parsed = parse_v4_agg_text(_agg_text(tmp_path, key))
    # 三日 hour 行照常补齐(new_hours 按 epoch 升序 append; 每日 2 条记录 -> 1 区间 30s)
    assert [h.epoch for h in parsed.hours] == [v4_date_str_epoch(d) for d in reversed(dates)]
    assert all(h.cov_s == 30 for h in parsed.hours)
    text = logs.text
    assert "agg 无可用水位(缺失/损坏/无 hour 行)" in text and "全量兜底(D5)" in text
    assert f"读集 {len(dates)} 天(>2): 下界来源 = fallback 保留窗全量" in text


def test_recovery_instrumentation_logs_counts(tmp_path, monkeypatch):
    """埋点(报告 §7-B4 / plan 26-10-12-2010 §4.2): 恢复起止 INFO —— 开始行(启用态/系列数)
    + 完成行(系列数/读入天文件数/补算小时数/耗时), 单系列读集 >2 天留下界来源说明;
    启动死区从此不再静默(计数另落模块属性, 由读集守阵机检)"""
    now = _local_epoch(13, 0, 30)
    clock = FakeClock(start=now)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30), clock=clock)
    st = TrafficV4Store(str(tmp_path))
    y_str, t_str = v4_epoch_date_str(now - 86400), v4_epoch_date_str(now)
    # 系列 A: 水位昨日 + 昨日/今日两文件(读集 2, 不触 >2 行)
    st.append_agg_rows(
        "torrent:AA", (AggRow("hour",
                              v4_date_str_epoch(y_str) + 10 * HOUR_SECONDS, 1, 1, 1, 1, 1, 1, 3600), )
    )
    _write_day_file(tmp_path, "torrent:AA", y_str)
    _write_day_file(tmp_path, "torrent:AA", t_str)
    # 系列 B: 无 agg -> fallback 全量 + 3 文件(读集 3 > 2 -> 留下界来源行)
    for i in range(3):
        _write_day_file(tmp_path, "torrent:BB", v4_epoch_date_str(now - i * 86400))
    with capture_logs("auto_qb.core.modules.traffic_sample_mod") as logs:
        mgr.host.get("qb_traffic").start(mgr.ctx, dry_run=False)
    text = logs.text
    assert "启动恢复开始: 启用态, 2 个现存系列(读集 = agg 水位日 -> 今日, 按需口径)" in text
    assert "启动恢复完成: 2 系列 / 读入天文件 5 个" in text  # A 2 + B 3
    assert "补算小时 0 个 / 入账槽 0 个 / 耗时" in text  # 空壳文件零入账(计数形状齐全)
    assert "agg 无可用水位(缺失/损坏/无 hour 行)" in text  # B 的 D5 兜底说明
    assert "读集 3 天(>2): 下界来源 = fallback 保留窗全量" in text  # B 的下界来源
    stats = mgr.host.get("qb_traffic").recovery_stats
    assert stats == {"series": 2, "day_files": 5, "hours": 0, "slots": 0, "elapsed_s": stats["elapsed_s"]}


@pytest.mark.parametrize("window", ("1m", "5m", "30m", "3h", "6h", "12h", "24h", "3d", "7d", "30d", "6mo", "1y", "all"))
def test_read_side_view_contract_table(web_env, monkeypatch, window):
    """读侧契约逐档机检(§3.2, 表驱动 13 档, 端点时钟冻结): 一次 GET 的读集 —— raw 段
    (1m-24h)只开窗口涉及日期天文件(集 = 窗首种子外扩后日期集, 窗外 decoy 零 open) /
    hour/day/month 段(3d-all)恒恰 1 个 agg.dat + 天文件零 open / 限速注解面打开集 =
    [grid.t0-86400, grid.t1] 日期集(与数据面分开计数); 「不打开 = 0 请求」由前端
    轮询门控单点保证(all 档同用例静态钉住: 关抽屉/形态切换/登出 -> clearInterval)"""
    from types import SimpleNamespace

    from auto_qb.core import traffic_grid as tg
    from auto_qb.core.traffic_limits import limits_day_path

    mgr, client = web_env
    auth = {_AUTH_HEADER_KEY: f"Bearer {mgr.web.token}"}
    frozen = float(int(time.time()))  # 冻结端点时钟: 期望集与请求同一 now(免午夜竞态)
    # S3 收敛: 单点置换统一走 FakeClock(不再 SimpleNamespace 手拼 now 单方法替身)
    monkeypatch.setattr("auto_qb.webui.server.traffic_qb.SYSTEM_CLOCK", FakeClock(start=frozen))
    _enable_qb_traffic(mgr)  # sample_interval 缺省 30s(raw 段桶宽 = 30)
    store = _qb_v4(mgr)
    key = "global"
    span, seg = tg.WINDOW_SPECS[window]
    if seg == "month":
        month_epochs = tuple(v4_month_epoch(frozen) - i * 28 * 86400 for i in range(6, 0, -1))
        grid = tg.build_month_grid(month_epochs, frozen)
    else:
        grid = tg.build_grid(window, frozen, 30.0)
    # decoy: 窗外天文件(昨日/3 日前/400 日前)与远古限速文件 —— 在场, 证明任何视图都不扫目录
    decoys = [v4_epoch_date_str(frozen - d * 86400) for d in (1, 3, 400)]
    lim_decoy = v4_epoch_date_str(frozen - 700 * 86400)
    # 造数: 本档读集范围内的天/限速文件 + 本档消费的 agg 行
    if seg == "raw":
        involved = sorted(v4_window_dates(grid.t0 - grid.interval, grid.t1))  # 镜像端点窗首种子外扩
        exp_days, exp_agg = involved, 0
        for d in involved + decoys:
            if not os.path.exists(v4_day_file_path(mgr.config.data_dir, key, d)):
                _write_day_file(mgr.config.data_dir, key, d)
    else:
        exp_days = []
        if seg == "hour":
            rows = tuple(AggRow("hour", grid.t0 + i * HOUR_SECONDS, 1, 1, 1, 1, 1, 1, 3600) for i in range(72))
        elif seg == "day":
            rows = tuple(
                AggRow("day", v4_date_str_epoch(d), 1, 1, 1, 1, 1, 1, 86400)
                for d in sorted(v4_window_dates(grid.t0, grid.t1 - 1))
            )
        else:
            rows = tuple(AggRow("month", e, 1, 1, 1, 1, 1, 1, 2419200) for e in month_epochs)
        store.append_agg_rows(key, rows)
        exp_agg = 1
        for d in decoys:
            if not os.path.exists(v4_day_file_path(mgr.config.data_dir, key, d)):
                _write_day_file(mgr.config.data_dir, key, d)
    lim_dates = sorted(v4_window_dates(grid.t0 - 86400, grid.t1))
    for d in lim_dates + [lim_decoy]:
        p = limits_day_path(mgr.config.data_dir, d)
        if not os.path.exists(p):
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8", newline="\n") as f:
                f.write("100,0,0\n")
    opened = _v4_open_paths(monkeypatch)
    body = client.get(f"/api/traffic/qb/{key}", headers=auth, params={"window": window})
    assert body.status_code == 200 and body.json()["meta"]["window"] == window
    got_days = sorted(
        os.path.basename(p)[:-4] for p in opened if p.endswith(".dat") and "agg.dat" not in p and "/limits/" not in p
    )
    got_agg = len([p for p in opened if p.endswith("agg.dat")])
    got_lim = sorted(os.path.basename(p)[:-4] for p in opened if "/limits/" in p)
    assert got_days == exp_days, f"{window} 天文件读集: {got_days} != {exp_days}"
    assert got_agg == exp_agg, f"{window} agg.dat 打开数: {got_agg} != {exp_agg}"
    assert got_lim == lim_dates, f"{window} 限速面读集: {got_lim} != {lim_dates}"


def test_read_side_no_poll_when_traffic_tab_closed():
    """「不打开 = 0 请求」(§3.2 末行): 前端轮询只在流量页签打开期间挂 —— 关抽屉/形态切换/
    登出经 _qbTeardown 单点收三挂点(_qbPollStop -> 骨架 stopPoll 清句柄), _qbPollStart 幂等
    不叠加; 关闭后无任何请求路径(读侧零 open 的另一半契约由端点逐档机检钉住)"""
    chart = open(
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "auto_qb", "webui", "static", "shared",
            "qb_traffic_chart.js"
        ),
        encoding="utf-8",
    ).read()
    stop_body = chart.split("_qbPollStop(scope) {", 1)[1].split("},", 1)[0]
    assert "stopPoll(" in stop_body  # 停轮询单点: 经骨架清句柄(关闭后零请求路径)
    teardown = chart.split("_qbTeardown() {", 1)[1][:400]
    assert "_qbPollStop(s)" in teardown  # 关抽屉/形态切换/登出 -> 三挂点轮询全收
    assert "_qbPollStop(scope);" in chart.split("_qbPollStart(scope) {", 1)[1][:200]  # 重开幂等(不叠加)


def test_hour_spans_splits_on_hour_boundary():
    """_hour_spans: 按小时界切段(与 _agg_credit_hours 同源) —— 跨 2 个整点出 3 段;
    退化/空区间出 (); 段数 = 跨的小时数(活尾合成 O(小时数) 而非 O(槽数) 的根据)"""
    from auto_qb.core.modules.traffic_sample_mod import _hour_spans

    h0 = _AGG_H0
    assert _hour_spans(h0 + 300, h0 + 2 * HOUR_SECONDS + 600) == (
        (h0 + 300, h0 + HOUR_SECONDS),
        (h0 + HOUR_SECONDS, h0 + 2 * HOUR_SECONDS),
        (h0 + 2 * HOUR_SECONDS, h0 + 2 * HOUR_SECONDS + 600),
    )
    assert _hour_spans(h0, h0) == ()
    assert _hour_spans(h0 + 10, h0 + 5) == ()


def test_open_run_hour_samples_null_run_leaves_tail_null():
    """断连(n 游程)只合成 credit 段到 run.start, 之后不出样本(留 null)—— 断连不可归因
    为 0(裁定 D3); 与 z 游程「整段 0」形成对照"""
    from auto_qb.core.modules.traffic_sample_mod import OpenRun, SeriesAgg, _open_run_hour_samples

    h0 = _AGG_H0
    agg = SeriesAgg()
    agg.open_credit = (float(h0 + 60), 100, 50, 1000, 2000)
    run = OpenRun("n", h0 + 600, h0 + 2 * HOUR_SECONDS, 0, 0, 120, 0, 0)
    out = _open_run_hour_samples(agg, run)
    assert out == {h0: [V4HourSample(100, 50, 1000, 2000, 540.0)]}  # 只到 run.start


def test_open_run_hour_samples_without_credit_is_empty():
    """无观测信用(open_credit is None: null 期后 / 首样前)-> 不合成任何样本(不猜);
    有信用但无开放游程 -> 同样不出样本(没有「仍在采样」的证据, 把信用推到 now 会在
    系列已不再被采样的退化形态下凭空造覆盖)"""
    from auto_qb.core.modules.traffic_sample_mod import OpenRun, SeriesAgg, _open_run_hour_samples

    run = OpenRun("z", _AGG_H0, _AGG_H0 + HOUR_SECONDS, 0, 0, 60, 0, 0)
    assert _open_run_hour_samples(SeriesAgg(), run) == {}
    agg = SeriesAgg()
    agg.open_credit = (float(_AGG_H0), 100, 50, 1000, 2000)
    assert _open_run_hour_samples(agg, None) == {}


def test_pending_agg_rows_keeps_totals_monotonic_against_disk_row(tmp_path):
    """totals 不变量(计划 §01 不变量 2 / S3): 合成行 totals = 游程末端锚点 —— 与磁盘已封
    行同 epoch 合流时「totals 取后封行」拿到更晚快照, 累计链不回退; 反证: 若带开启快照
    合流后 totals 会回退(< 磁盘行)"""
    from auto_qb.core.modules.traffic_sample_mod import OpenRun, _pending_agg_rows
    from auto_qb.core.traffic_store import v4_merge_agg

    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mod = mgr.host.get("qb_traffic")
    agg = mod._agg_state(GLOBAL_SERIES_KEY)
    h0 = v4_day_epoch(_AGG_H0) + 2 * HOUR_SECONDS
    agg.open_credit = (float(h0), 0, 0, 1000, 2000)
    run = OpenRun("z", h0, h0 + HOUR_SECONDS, 1000, 2000, 60, 5000, 9000)
    live = [r for r in _pending_agg_rows(agg, run, now=h0 + HOUR_SECONDS) if r.kind == "hour"][0]
    assert (live.dl_total, live.up_total) == (5000, 9000)  # 末端锚点, 非开启快照
    disk = AggRow("hour", h0, 0, 0, 0, 0, 2000, 4000, 1200)  # 已封段: 更早快照
    merged = v4_merge_agg(disk, live)
    assert merged.cov_s == HOUR_SECONDS  # 相加截到桶宽
    assert (merged.dl_total, merged.up_total) == (5000, 9000)  # 取更晚快照, 不回退
    # 反证: 合成行若带开启快照, 合流后 totals 回退到 1000/2000(< 磁盘行)
    naive = AggRow("hour", h0, 0, 0, 0, 0, 1000, 2000, HOUR_SECONDS)
    assert v4_merge_agg(disk, naive).dl_total == 1000 < disk.dl_total


def test_pending_agg_rows_cross_midnight_keeps_day_row_on_new_day(tmp_path):
    """跨天合成(用户报「特别是跨天后」): 游程跨本地日界 -> hour 行落两天, 开放日行只取
    新一天的小时(前一日已封口小时不并进新日行); 新一天从 00:00 起就有 0 行"""
    from auto_qb.core.modules.traffic_sample_mod import OpenRun, _pending_agg_rows

    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mod = mgr.host.get("qb_traffic")
    agg = mod._agg_state(GLOBAL_SERIES_KEY)
    d0 = v4_day_epoch(_AGG_H0)
    start, end = d0 - 2 * HOUR_SECONDS, d0 + 2 * HOUR_SECONDS
    agg.open_credit = (float(start), 0, 0, 1000, 2000)
    run = OpenRun("z", start, end, 1000, 2000, 4, 1000, 2000)
    rows = _pending_agg_rows(agg, run, now=end)
    assert [r.epoch for r in rows if r.kind == "hour"] == [start + k * HOUR_SECONDS for k in range(4)]
    assert [r for r in rows if r.kind == "day"] == [
        AggRow("day", d0, 0, 0, 0, 0, 1000, 2000, 2 * HOUR_SECONDS)
    ]  # 只新一天的两个小时
    assert [r.epoch for r in rows if r.kind == "month"] == [v4_month_epoch(d0)]


def test_advance_run_z_requires_totals_snapshot(tmp_path):
    """开 z 游程需 totals 快照(缺失零操作 —— 空闲不出 null 槽, null 走 n 游程); n 游程无此
    要求(无观测不携带 totals)"""
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mod = mgr.host.get("qb_traffic")
    key = GLOBAL_SERIES_KEY
    mod._advance_run(key, 1000.0, "z")  # 无 totals 快照
    assert key not in mod._open_runs
    mod._advance_run(key, 1000.0, "n")
    assert mod._open_runs[key].kind == "n" and mod._open_runs[key].samples == 1


def test_resolve_run_end_falls_back_to_open_snapshot():
    """z 游程封口末端锚点三级兜底(形态 D 单点): 显式传入 > 游程内最后一条零样本读数 >
    开启快照; 低于开启快照按开启快照钳制(游程内计数器重置的落差不是增长)"""
    def _run(last_dl, last_up):
        return ts_mod.OpenRun(
            kind="z",
            start=1000.0,
            last_seen=1030.0,
            dl_total=500,
            up_total=600,
            samples=2,
            last_dl_total=last_dl,
            last_up_total=last_up,
        )

    assert TrafficSampleModule._resolve_run_end(_run(None, None), None, None) == (500, 600)  # 末档: 开启快照
    tracked = _run(520, 610)
    assert TrafficSampleModule._resolve_run_end(tracked, None, None) == (520, 610)  # 跟踪值
    assert TrafficSampleModule._resolve_run_end(tracked, 530, 640) == (530, 640)  # 显式样本优先
    assert TrafficSampleModule._resolve_run_end(tracked, 100, 100) == (500, 600)  # 低于开启快照: 钳制


def test_null_prefix_split_block_on_raw_arrival(tmp_path, monkeypatch):
    """n-only 前缀拆块(§01「基线立点」): 无基线块(块首 n 游程)内到达带 totals 的记录 ->
    前缀先落盘成 3 列 B 无基线块并关块, 本记录开新块立基线(块首 n 游程不立基线)"""
    clock = FakeClock()
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30), clock=clock)
    mgr.store.server_state = {}  # 关键字段缺失 -> null 点
    mod = mgr.host.get("qb_traffic")
    key = GLOBAL_SERIES_KEY
    _run_sample(mgr)
    clock.advance(30)
    _run_sample(mgr)
    assert mod._open_runs[key].kind == "n" and mod._open_runs[key].samples == 2
    mgr.store.server_state = server_state()
    clock.advance(30)
    _run_sample(mgr)  # 恢复传输: n 游程封口成块首(无基线), r 到达即拆块
    _flush(mod)
    parsed = _v4_read(tmp_path, key, clock.now())
    assert parsed is not None and parsed.bad_lines == 0
    assert len(parsed.blocks) == 2
    assert parsed.blocks[0].dl_base is None and [type(r) for r in parsed.blocks[0].records] == [V4NullRun]
    assert parsed.blocks[1].dl_base is not None and [type(r) for r in parsed.blocks[1].records] == [V4Sample]
    text = _v4_path(tmp_path, key, clock.now()).read_text(encoding="utf-8")
    assert len([ln for ln in text.splitlines() if ln.startswith("B,")]) == 2  # 3 列 + 5 列二态并存


def test_flush_series_no_buffer_and_header_once_across_flushes(tmp_path):
    """_flush_series 两条边界: 无缓冲系列零操作(不建文件); 纯 z 块跨 flush 开放且块头只写
    一次 —— 第二批 header = None(header_written 不复位), 盘上仍恰一个 B 行"""
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mod = mgr.host.get("qb_traffic")
    key = GLOBAL_SERIES_KEY
    assert mod._flush_series("torrent:NOPE") is None  # 无缓冲系列: 零操作
    mod._append_record(key, V4ZeroRun(2, 10, 20), float(_AGG_H0), float(_AGG_H0 + 30))
    mod._flush_series(key)
    buf = mod._buffers[key]
    assert buf.header_written is True and buf.records == []
    assert buf.start_epoch == _AGG_H0  # 纯空闲块跨 flush 开放不关(无 r 行)
    mod._append_record(key, V4ZeroRun(2, 10, 20), float(_AGG_H0 + 60), float(_AGG_H0 + 90))
    mod._flush_series(key)  # 第二批: 块头已写过 -> header None
    parsed = _v4_read(tmp_path, key, float(_AGG_H0))
    assert parsed is not None and len(parsed.blocks) == 1 and parsed.blocks[0].start_epoch == _AGG_H0
    assert [type(r) for r in parsed.blocks[0].records] == [V4ZeroRun, V4ZeroRun]
    assert parsed.bad_lines == 0


def test_recovery_missing_day_file_breaks_tail_context(tmp_path, monkeypatch):
    """恢复跨天末槽上下文接力: 读集内文件在场 -> [昨日末槽, 今日首槽) 连续段结算进覆盖
    (23 点成行); 文件缺失(竞态/手工清理)-> 上下文断链, 该段按真空处理(23 点无观测不出行),
    今日开放小时照常重建 pending 桶"""
    now = _local_epoch(0, 30, 30)
    clock = FakeClock(start=now)
    conf = QbTraffic(enabled=True, sample_interval=30, rollup_window=3 * 86400.0)
    ctl, drop = tmp_path / "ctl", tmp_path / "drop"
    os.makedirs(ctl)
    os.makedirs(drop)
    y_date = _build_tail_fixture(ctl, now)
    _build_tail_fixture(drop, now)
    mgr = _mgr_with_traffic(ctl, conf, clock=clock)
    mod = mgr.host.get("qb_traffic")
    mod.start(mgr.ctx, dry_run=False)
    assert mod.recovery_stats["slots"] == 4  # 两文件各 2 槽
    assert mod.recovery_stats["hours"] == 1  # 昨日 23 点: 槽间 30s + 跨文件连续段 20s
    # 读集内昨日文件缺失 -> 末槽上下文断链
    real_read_day = TrafficV4Store.read_day

    def _drop_yesterday(self, key, date_str):
        if key == GLOBAL_SERIES_KEY and date_str == y_date:
            return None
        return real_read_day(self, key, date_str)

    monkeypatch.setattr(TrafficV4Store, "read_day", _drop_yesterday)
    mgr2 = _mgr_with_traffic(drop, conf, clock=clock)
    mod2 = mgr2.host.get("qb_traffic")
    mod2.start(mgr2.ctx, dry_run=False)
    assert mod2.recovery_stats["slots"] == 2  # 只有今日文件贡献槽
    assert mod2.recovery_stats["hours"] == 0  # 23 点无观测: 不虚记覆盖
    assert v4_date_str_epoch(v4_epoch_date_str(now)) in mod2._agg_state(GLOBAL_SERIES_KEY).pending


def test_recovery_open_hour_rebuilds_pending_bucket(tmp_path, monkeypatch):
    """catch-up 遇未完结小时 -> 重建 pending 桶(不产 hour 行, 等封口); 空桶跳过(防御:
    桶存在但无样本时不留行)"""
    now = _local_epoch(13, 0, 30)
    clock = FakeClock(start=now)
    mgr = _mgr_with_traffic(
        tmp_path, QbTraffic(enabled=True, sample_interval=30, rollup_window=3 * 86400.0), clock=clock
    )
    st = TrafficV4Store(str(tmp_path))
    today0 = v4_date_str_epoch(v4_epoch_date_str(now))
    y0 = v4_date_str_epoch(v4_epoch_date_str(now - 86400))
    wm = y0 + 10 * HOUR_SECONDS
    st.append_agg_rows(GLOBAL_SERIES_KEY, (AggRow("hour", wm, 7, 9, 3, 4, 500, 600, 3600), ))
    _write_day_file(tmp_path, GLOBAL_SERIES_KEY, v4_epoch_date_str(now))
    cur_hour, empty_hour = today0 + 13 * HOUR_SECONDS, today0 + 12 * HOUR_SECONDS

    def _fake_credit(hour_samples, parsed_day, prev_tail=None, slot_counter=None):
        hour_samples[cur_hour] = [V4HourSample(100, 50, 1, 2, 30.0)]  # 开放小时(未完结)
        hour_samples[empty_hour] = []  # 空桶: 不留行
        return None

    monkeypatch.setattr(TrafficSampleModule, "_agg_credit_day_file", staticmethod(_fake_credit))
    mod = mgr.host.get("qb_traffic")
    mod.start(mgr.ctx, dry_run=False)
    agg = mod._agg_state(GLOBAL_SERIES_KEY)
    assert cur_hour in agg.pending and empty_hour not in agg.pending
    parsed = parse_v4_agg_text(_agg_text(tmp_path, GLOBAL_SERIES_KEY))
    assert [h.epoch for h in parsed.hours] == [wm]  # 开放小时不产行(封口时才写)


def test_agg_credit_day_file_empty_block_and_null_slots():
    """离线记账两条跳过出口: 空块零槽(解析层不会产出空块, 直接构造防御支)与 n 槽(null
    期不贡献) —— 末槽 null 观测的上下文 obs = None, 调用方结算侧自然跳过"""
    import types

    empty_block = V4Block(1000, 30, None, None, ())
    hour_samples: dict = {}
    TrafficSampleModule._agg_credit_day_file(hour_samples, types.SimpleNamespace(blocks=(empty_block, )))
    assert hour_samples == {}
    null_day = parse_v4_day_text(f"{HEADER_LINE_V4}\nkey,global\nB,1000,30\nn,3\n")
    hour_samples = {}
    tail = TrafficSampleModule._agg_credit_day_file(hour_samples, null_day)
    assert hour_samples == {}  # n 槽 null 期零入账
    assert tail is not None and tail[1] is None and tail[0] == pytest.approx(1060.0)


def test_agg_credit_hours_never_creates_empty_bucket():
    """pending 空桶生产点不存在(issue 26-11-01-0050): 入账恒 setdefault+append

    end <= start 直接返回(不建桶), 有效区间每桶至少 append 一条 ——
    「空桶留空」在 _agg_flush_series 是防御支(空桶支 continue->break 判等价)。
    """
    pending: dict = {}
    TrafficSampleModule._agg_credit_hours(pending, 100.0, 100.0, 1, 2, 3, 4)
    assert pending == {}  # 退化区间不建桶
    TrafficSampleModule._agg_credit_hours(pending, 100.0, 101.0, 1, 2, 3, 4)
    assert all(samples for samples in pending.values())  # 生产的桶恒非空


def test_w5_blockhead_run_drift_dt_and_cursor(tmp_path, monkeypatch):
    """块首游程显式 dt 支: dt_ms = 实测跨度(span*1000)且游标推到实测点; run_len==2 不走
    单槽支、游程内部零覆盖入账 —— _append_record_116/117/124/125/126 + _append_record_93"""
    clock = FakeClock()
    mgr = _w5_mgr(tmp_path, monkeypatch, clock)
    mgr.store.server_state = server_state()
    mod = mgr.host.get("qb_traffic")
    t0 = clock.now()
    _run_sample(mgr)
    _flush(mod)
    mgr.store.server_state = _idle_state()
    clock.advance(30)
    _run_sample(mgr)  # z@t0+30
    clock.advance(62)
    _run_sample(mgr)  # z@t0+92(游程内实测间隔 62s -> 块首游程 span 62 vs 标称 30 -> 显式 dt)
    clock.advance(30)
    mgr.store.server_state = server_state()
    _run_sample(mgr)  # t0+122: r 封 z -> dt 62000, 游标 = anchor+62 = t0+92; r 零漂移
    buf = mod._buffers[GLOBAL_SERIES_KEY]
    z, r = buf.records
    assert isinstance(z, V4ZeroRun) and z.dt_ms == 62000  # dt = 实测跨度(run_len 2 不走单槽支)
    assert isinstance(r, V4Sample) and r.dt_ms is None  # 游标已复位实测点: r 零漂移
    assert buf.projected_ts == t0 + 122.0
    h0 = int(t0) // HOUR_SECONDS * HOUR_SECONDS
    samples = mod._agg_states[GLOBAL_SERIES_KEY].pending[h0]
    assert [round(s.dt_s, 6) for s in samples] == [30.0, 62.0, 30.0]  # r 信用 + 游程内部 62s + 末端结算


def test_w5_blockhead_run_drift_boundary_exact_tol(tmp_path, monkeypatch):
    """块首游程漂移判据边界: |span-标称| 恰 250ms 不写 dt(判据为 > 非 >=)—— _append_record_107"""
    clock = FakeClock()
    mgr = _w5_mgr(tmp_path, monkeypatch, clock)
    mgr.store.server_state = server_state()
    mod = mgr.host.get("qb_traffic")
    t0 = clock.now()
    _run_sample(mgr)
    _flush(mod)
    mgr.store.server_state = _idle_state()
    clock.advance(30)
    _run_sample(mgr)  # z@t0+30
    clock.advance(30.25)
    _run_sample(mgr)  # z@t0+60.25(游程内 30.25s: span 30.25 vs 标称 30 -> 恰压线)
    clock.advance(30)
    mgr.store.server_state = server_state()
    _run_sample(mgr)  # t0+90.25: r 封 z: 恰 250ms 不写 dt
    buf = mod._buffers[GLOBAL_SERIES_KEY]
    z, r = buf.records
    assert isinstance(z, V4ZeroRun) and z.dt_ms is None  # 压线不写 dt
    assert isinstance(r, V4Sample) and r.dt_ms is None
    assert buf.projected_ts == t0 + 90.0  # 零漂移支: 游标标称推进(漂移余量保留)


def test_w5_zrun_time_valve_seals_at_exact_86400(tmp_path, monkeypatch):
    """时间支保险闸边界: ts-start 恰 86400s 必须封口(游程跨度不超天级)—— _advance_run_76;
    跨天判据与闸判据同函数, 钉边界须隔离日期支(monkeypatch 日期串恒定)"""
    clock = FakeClock()
    mgr = _w5_mgr(tmp_path, monkeypatch, clock)
    monkeypatch.setattr(ts_mod, "v4_epoch_date_str", lambda ts: "D")  # 隔离跨天支, 只钉闸边界
    mod = mgr.host.get("qb_traffic")
    t0 = clock.now()
    mod._advance_run(GLOBAL_SERIES_KEY, t0, "z", 100, 200)
    for i in range(1, 2881):  # 30s 步进至恰 86400s
        mod._advance_run(GLOBAL_SERIES_KEY, t0 + i * 30, "z")
    assert GLOBAL_SERIES_KEY not in mod._open_runs  # 恰 86400s 已封口
    z = mod._buffers[GLOBAL_SERIES_KEY].records[0]
    assert isinstance(z, V4ZeroRun) and z.run_len == 2881


def test_w5_q3_slot_accounting_runs_and_flush_reset(tmp_path, monkeypatch):
    """Q3 槽计数: r=1/游程=run_len/块首单槽游程=1, flush 复位 0 —— _append_record_96/97/175
    + _flush_series_37(直查 buf.slots)"""
    clock = FakeClock()
    mgr = _w5_mgr(tmp_path, monkeypatch, clock)
    mgr.store.server_state = server_state()
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)  # 块首 r: slots 1
    assert mod._buffers[GLOBAL_SERIES_KEY].slots == 1
    mgr.store.server_state = _idle_state()
    for _ in range(5):
        clock.advance(30)
        _run_sample(mgr)
    mgr.store.server_state = server_state()
    clock.advance(30)
    _run_sample(mgr)  # 非块首 z 游程 run_len 5 + 封口 r: slots 1+5+1 = 7
    assert mod._buffers[GLOBAL_SERIES_KEY].slots == 7
    _flush(mod)  # 落盘成功: 槽计数复位 0
    assert mod._buffers[GLOBAL_SERIES_KEY].slots == 0
    mgr.store.server_state = _idle_state()
    clock.advance(30)
    _run_sample(mgr)  # 单样本空闲
    mgr.store.server_state = server_state()
    clock.advance(30)
    _run_sample(mgr)  # 块首单槽游程(z run_len 1) + r: slots 0+1+1 = 2
    assert mod._buffers[GLOBAL_SERIES_KEY].slots == 2


def test_w5_persist_warn_cycle_resets_after_success(tmp_path, monkeypatch):
    """落盘告警节流记忆: 成功即复位(原始与 agg 两侧)/首败 WARNING/连败只一次 ——
    _flush_series_29 / __init___8 / _agg_append_12/16/17"""
    class _FlakyV4Store:
        def __init__(self):
            self.raw_ok = False
            self.agg_ok = False

        def append_records(self, *a):
            if not self.raw_ok:
                raise OSError("raw boom")

        def append_agg_rows(self, *a):
            if not self.agg_ok:
                raise OSError("agg boom")

    clock = FakeClock()
    mgr = _w5_mgr(tmp_path, monkeypatch, clock)
    mgr.store.server_state = server_state()
    mod = mgr.host.get("qb_traffic")
    mod._v4store = _FlakyV4Store()
    row = AggRow("hour", int(clock.now()) // HOUR_SECONDS * HOUR_SECONDS, 1, 1, 1, 1, 1, 1, 30)
    with capture_logs("auto_qb.core.modules.traffic_sample_mod") as cap:
        _run_sample(mgr)
        _flush(mod)  # 首败: WARNING(非「持续」降级)
        mod._v4store.raw_ok = True
        clock.advance(30)
        _run_sample(mgr)
        _flush(mod)  # 成功: 复位
        mod._v4store.raw_ok = False
        clock.advance(30)
        _run_sample(mgr)
        _flush(mod)  # 再败: 又是 WARNING(成功复位)
        mod._v4store.raw_ok = True
        clock.advance(30)
        _run_sample(mgr)
        _flush(mod)  # 再成功: 复位(agg 面共用同一记忆, 先归零)
        mod._agg_append(GLOBAL_SERIES_KEY, (row, ))  # agg 首败: WARNING
        mod._agg_append(GLOBAL_SERIES_KEY, (row, ))  # agg 连败: DEBUG「持续」
        mod._v4store.agg_ok = True
        mod._agg_append(GLOBAL_SERIES_KEY, (row, ))  # agg 成功: 复位
        mod._v4store.agg_ok = False
        mod._agg_append(GLOBAL_SERIES_KEY, (row, ))  # agg 再败: WARNING
    warns = [r for r in cap.records if r.levelno == logging.WARNING and "落盘失败" in r.getMessage()]
    raw_warns = [r for r in warns if "批量落盘失败" in r.getMessage()]
    agg_warns = [r for r in warns if "agg 行落盘失败" in r.getMessage()]
    assert len(raw_warns) == 2 and len(agg_warns) == 2
    sustained = [r for r in cap.records if "持续" in r.getMessage()]
    assert len(sustained) == 1 and all(r.levelno == logging.DEBUG for r in sustained)


def test_w5_agg_append_empty_false_nonempty_true(tmp_path):
    """_agg_append 返回契约(docstring 明文「测试用」): 空批 False / 实写 True —— _agg_append_2"""
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mod = mgr.host.get("qb_traffic")
    row = AggRow("hour", 1699999200, 1, 1, 1, 1, 1, 1, 30)
    assert mod._agg_append(GLOBAL_SERIES_KEY, ()) is False  # 空批: 未写文件
    assert mod._agg_append(GLOBAL_SERIES_KEY, (row, )) is True  # 反向对照: 实写返回 True


def test_w5_main_tick1_quantize_and_warn_once(tmp_path, monkeypatch):
    """main_tick=1.0 合法档量化口径: 1.5s 档 ceil 到 2.0 且失配告警恰一次(D5)——
    _apply_interval_17(量化) / _apply_interval_40(告警门)"""
    clock = FakeClock()
    mgr = _w5_mgr(tmp_path, monkeypatch, clock)
    mgr.config.main_tick = 1.0
    mgr.config.qb_traffic = QbTraffic(enabled=True, sample_interval=1.5, flush_interval=10**9)
    mgr.store.server_state = server_state()
    mod = mgr.host.get("qb_traffic")
    with capture_logs("auto_qb.core.modules.traffic_sample_mod") as cap:
        _run_sample(mgr)
        assert mod._effective_interval == 2.0  # ceil(1.5/1.0) = 2(非 1.5 原样)
        clock.advance(2)
        _run_sample(mgr)
    assert sum(1 for r in cap.records if "非 main_tick" in r.getMessage()) == 1  # 失配只告警一次


def test_w5_live_tail_empty_shell_no_truncation(tmp_path, monkeypatch):
    """活尾发布空信息键(shell 缓冲)不截断其后系列: 多空壳 + 信息键共存,
    信息键 tail 恒在 —— _publish_live_tail_37(continue->break 截断)"""
    clock = FakeClock()
    mgr = _w5_mgr(tmp_path, monkeypatch, clock)
    tors = [active_torrent(f"H{i:02d}") for i in range(60)]
    seed_store(mgr, tors)
    mgr.store.server_state = server_state()
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)  # 全部出 r
    _flush(mod)  # 全部落盘: 60 个 torrent shell 缓冲滞留(round_keys 未清)
    for tor in tors:  # 转为「缺字段空闲」: 本轮被跳过, shell 键仍留在键集且无活尾信息
        tor.dlspeed = 0
        tor.upspeed = 0
        tor.downloaded = None
    clock.advance(30)
    _run_sample(mgr)  # global 出 r(信息键); 发布时键集 = 1 信息键 + 60 空壳
    tail = mod.live_tail
    assert GLOBAL_SERIES_KEY in tail and len(tail[GLOBAL_SERIES_KEY].records) == 1  # 信息键不被截断
    assert not any(k.startswith("torrent:") for k in tail)  # 空壳不留快照


def test_w5_live_tail_head_pending_false_chain(tmp_path, monkeypatch):
    """活尾 head_pending=False(块头已落盘)+ 开放游程: 槽位从写侧游标链倒推(非 0 起点均摊)
    —— _publish_live_tail_65(projected_ts 强制 0); 快照与落盘重算恒等"""
    clock = FakeClock()
    mgr = _w5_mgr(tmp_path, monkeypatch, clock)
    mgr.store.server_state = server_state()
    mod = mgr.host.get("qb_traffic")
    t0 = clock.now()
    _run_sample(mgr)
    _flush(mod)  # 块 A 关闭
    mgr.store.server_state = _idle_state()
    for _ in range(2):  # z1(t0+30, t0+60)
        clock.advance(30)
        _run_sample(mgr)
    mod._seal_run(GLOBAL_SERIES_KEY)  # 封 z1 -> 纯空闲块块首游程(游标 t0+60)
    for _ in range(2):  # z2 开放游程(t0+90, t0+120)
        clock.advance(30)
        _run_sample(mgr)
    _flush(mod)  # 块 [z1] 落盘(块头已写), 块开放不关
    clock.advance(30)
    _run_sample(mgr)  # t0+150: z2 推进 + 发布(head_pending=False)
    tail = mod.live_tail[GLOBAL_SERIES_KEY]
    assert tail.block_open and not tail.head_pending
    tail_slots = v4_live_tail_slots(tail)
    assert [s.ts for s in tail_slots] == [t0 + 90.0, t0 + 120.0, t0 + 150.0]  # 链锚点 = 游标
    mgr.store.server_state = server_state()
    clock.advance(30)
    _run_sample(mgr)  # t0+180: r 封 z2
    _flush(mod)
    parsed = _v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now())
    blk = [b for b in parsed.blocks if b.start_epoch == int(t0 + 30)][0]  # 块 [z1, z2, r](块 A 是此前 r)
    file_slots = v4_block_slots(blk)
    assert tuple(tail_slots) == file_slots[2:5]  # 快照(开放游程段) == 落盘重算(恒等口径)


def test_w5_counter_reset_audit_logs(tmp_path, monkeypatch):
    """计数器重置审计面: 增量重置 INFO 带系列键+方向(下载/上传)+ 强制关块重立基线 INFO
    —— sample_series_14/15/22/26/27/34 / _close_block_and_reopen_1 / _append_record_66/71"""
    clock = FakeClock()
    mgr = _w5_mgr(tmp_path, monkeypatch, clock)
    tor = active_torrent("HASH9")
    seed_store(mgr, [tor])
    mgr.store.server_state = _idle_state()  # 全局保持空闲(隔离单种面)
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)  # r(totals 5M/3M)
    tor.downloaded, tor.uploaded = 1000, 500  # 计数器回落(两方向同时)
    with capture_logs("auto_qb.core.modules.traffic_sample_mod") as cap:
        clock.advance(30)
        _run_sample(mgr)
    assert "torrent:HASH9 下载累计计数器回落" in cap.text  # 键+方向丢真/乱码在此断言破
    assert "torrent:HASH9 上传累计计数器回落" in cap.text
    assert "强制关块重立基线" in cap.text  # 关块审计 INFO 丢失在此断言破


def test_w5_latest_mirror_fields_complete(tmp_path, monkeypatch):
    """latest 排障镜像字段契约: ts/up_total/up_session 全真(含 null 点 ts)——
    sample_series_43/47/49 / _touch_null_run_2"""
    clock = FakeClock()
    mgr = _w5_mgr(tmp_path, monkeypatch, clock)
    mod = mgr.host.get("qb_traffic")
    t0 = clock.now()
    mgr.store.server_state = server_state()
    _run_sample(mgr)
    pt = mod.latest[GLOBAL_SERIES_KEY]
    assert pt.ts == t0 and pt.up_total == 20_000_000 and pt.up_session == 2_000_000
    assert pt.dl_total == 10_000_000 and pt.dl_session == 1_000_000
    mgr.store.server_state = server_state(alltime_dl=None)  # 关键字段缺失 -> null 点
    clock.advance(30)
    _run_sample(mgr)
    null_pt = mod.latest[GLOBAL_SERIES_KEY]
    assert null_pt.ts == t0 + 30  # null 点时刻不失真
    assert null_pt.dl_rate is None and null_pt.dl_total is None


def test_w5_init_sentinels_and_disabled_recovery(tmp_path):
    """恢复哨兵契约(「None = 未启用/未恢复」)+ 未启用零恢复零目录 ——
    __init___23/24 / _recover_aggregates_2"""
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=False))
    mod = mgr.host.get("qb_traffic")
    assert mod.recovery_reads is None and mod.recovery_stats is None  # 哨兵初值
    mod.start(mgr.ctx, dry_run=False)
    assert mod.recovery_reads is None and mod.recovery_stats is None  # 关闭态: 恢复不跑
    assert not (tmp_path / "qb-traffic-v4").exists()  # 未启用零文件零目录
    mgr2 = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True))  # 反向对照: 启用态恢复落属性
    mod2 = mgr2.host.get("qb_traffic")
    mod2.start(mgr2.ctx, dry_run=False)
    assert mod2.recovery_reads == {} and isinstance(mod2.recovery_stats, dict)


def test_w5_pending_agg_rows_day_partition(tmp_path):
    """活尾日行跨日分片(纯函数探针): 昨日残值发布昨日日行 / 今日 partial 提日且
    前一日已封口小时不并入 —— _pending_agg_rows_27/34/37"""
    now = _w5_ts(2026, 6, 2, 0, 10, 0)
    y_day, y_hour = int(_w5_ts(2026, 6, 1, 0, 0, 0)), int(_w5_ts(2026, 6, 1, 10, 0, 0))
    t_day = int(_w5_ts(2026, 6, 2, 0, 0, 0))
    y_row = AggRow("hour", y_hour, 100, 200, 50, 80, 1000, 2000, 3600)
    # 场景 a: 昨日残值且无今日合成段 -> 昨日日行照常发布(累计器+残值)
    agg_a = ts_mod.SeriesAgg(day_epoch=y_day, day_hours=[y_row])
    rows_a = ts_mod._pending_agg_rows(agg_a, None, now)
    assert any(r.kind == "day" and r.epoch == y_day for r in rows_a)
    # 场景 b: 今日 pending partial + day_epoch 停昨日 -> 提日到今日, 昨日已封口小时不并入
    agg_b = ts_mod.SeriesAgg(day_epoch=y_day, day_hours=[y_row])
    agg_b.pending[t_day] = [V4HourSample(100, 50, 1000, 2000, 60.0)]
    rows_b = ts_mod._pending_agg_rows(agg_b, None, now)
    day_rows = [r for r in rows_b if r.kind == "day"]
    assert len(day_rows) == 1 and day_rows[0].epoch == t_day  # 提日(不出 None epoch 空日行)
    assert day_rows[0].cov_s == 60  # 只含今日 partial(昨日 3600s 不并入)


def test_w5_pending_agg_rows_month_partition(tmp_path):
    """活尾月行归档(纯函数探针): day 部分行并入当月月行 / 月界窗口上月月行照常发布
    —— _pending_agg_rows_63 / _pending_agg_rows_55"""
    now = _w5_ts(2026, 6, 2, 0, 10, 0)
    june, may = int(_w5_ts(2026, 6, 1, 0, 0, 0)), int(_w5_ts(2026, 5, 1, 0, 0, 0))
    t_day = int(_w5_ts(2026, 6, 2, 0, 0, 0))
    june_day_row = AggRow("day", june, 100, 200, 50, 80, 1000, 2000, 3600)
    # 场景 a: 当月已有封口 day 行 + 今日 pending hour -> 月行含今日 day 部分行
    agg_a = ts_mod.SeriesAgg(month_epoch=june, month_days=[june_day_row])
    agg_a.pending[t_day] = [V4HourSample(100, 50, 1000, 2000, 60.0)]
    rows_a = ts_mod._pending_agg_rows(agg_a, None, now)
    month_a = [r for r in rows_a if r.kind == "month"]
    assert len(month_a) == 1 and month_a[0].epoch == june
    assert month_a[0].cov_s == 3660  # 3600(已封 day) + 60(今日 day 部分行并入)
    # 场景 b: 月界窗口: month_epoch 停上月 -> 上月月行照常发布(本月日行不混入)
    may_day_row = AggRow("day", int(_w5_ts(2026, 5, 15, 0, 0, 0)), 100, 200, 50, 80, 1000, 2000, 3600)
    agg_b = ts_mod.SeriesAgg(month_epoch=may, month_days=[may_day_row])
    agg_b.pending[t_day] = [V4HourSample(100, 50, 1000, 2000, 60.0)]
    rows_b = ts_mod._pending_agg_rows(agg_b, None, now)
    months_b = [r for r in rows_b if r.kind == "month"]
    assert [r.epoch for r in months_b] == [may]  # 上月行在, 本月行不抢归档
    assert months_b[0].cov_s == 3600  # 只含上月子行


def test_w5_recover_single_month_row_no_reappend(tmp_path, monkeypatch):
    """恢复水位幂等: 恰 1 个月行恢复不崩(运营进入第二月常态)且已有月不重 append
    —— _recover_series_22/23 / 19/20/114"""
    month_row = AggRow("month", int(_w5_ts(2026, 6, 1, 0, 0, 0)), 100, 200, 50, 80, 1000, 2000, 3600)
    day_row = AggRow("day", int(_w5_ts(2026, 6, 15, 0, 0, 0)), 100, 200, 50, 80, 1000, 2000, 3600)
    hour_row = AggRow("hour", int(_w5_ts(2026, 6, 15, 10, 0, 0)), 100, 200, 50, 80, 1000, 2000, 3600)
    st = TrafficV4Store(str(tmp_path))
    st.append_agg_rows(GLOBAL_SERIES_KEY, (hour_row, day_row, month_row))
    text = _agg_text(tmp_path, GLOBAL_SERIES_KEY)
    clock = FakeClock(start=_w5_ts(2026, 7, 2, 12, 0, 0))
    mgr = _w5_mgr(tmp_path, monkeypatch, clock, rollup_window=1000000 * 86400.0)
    mod = mgr.host.get("qb_traffic")
    mod.start(mgr.ctx, dry_run=False)  # 恰 1 个月行: 变异(months[+1]/[-2])在此 IndexError
    assert _agg_text(tmp_path, GLOBAL_SERIES_KEY) == text  # 水位幂等: 零追加(月水位不丢)
    assert mod.recovery_reads[GLOBAL_SERIES_KEY]["day_dates"] == ()


def test_w5_ingest_acc_same_day_multi_hour(tmp_path, monkeypatch):
    """day 累计器同日多 hour 追加(常态每日): 两个完结小时逐级并入, 日行 cov 全量
    —— _ingest_acc_10"""
    # 时钟钉在本地正午: 默认 epoch 在 UTC 下是 22:13, h2+3610 会跨午夜触发日封口, 与本用例前提相悖
    clock = FakeClock(start=_w5_ts(2026, 6, 15, 12, 0, 0))
    mgr = _w5_mgr(tmp_path, monkeypatch, clock)
    mod = mgr.host.get("qb_traffic")
    key = GLOBAL_SERIES_KEY
    h1 = int(clock.now()) // HOUR_SECONDS * HOUR_SECONDS
    h2 = h1 + HOUR_SECONDS
    agg = mod._agg_state(key)
    agg.pending[h1] = [V4HourSample(100, 50, 1000, 2000, 1800.0)]
    agg.pending[h2] = [V4HourSample(80, 40, 1100, 2100, 1800.0)]
    mod._agg_flush_series(key, h2 + 3610)  # 两个完结小时封口 -> day 累计器
    assert len(agg.day_hours) == 2  # 同日追加(第二 hour 不被丢)
    assert agg.day_epoch == v4_day_epoch(h1)
    mod._agg_flush_series(key, h1 + 90000)  # 翻日: 日行落盘
    parsed = parse_v4_agg_text(_agg_text(tmp_path, key))
    assert [h.epoch for h in parsed.hours] == [h1, h2]
    assert len(parsed.days) == 1 and parsed.days[0].cov_s == 3600  # 日行 cov = 两 hour 全量
    assert parsed.days[0].dl_avg == 90  # 逐级 cov 加权 (100*1800+80*1800)/3600


def test_w5_day_reseal_merges_into_month(tmp_path):
    """day 重封月级合流(docstring 明文, 2026-10-13 真机 bug 形态): 同 epoch 迟到补记再封
    落批为合流行(cov 全量)—— _agg_ingest_day_3"""
    d = int(_w5_ts(2026, 6, 15, 0, 0, 0))
    full = AggRow("day", d, 100, 200, 50, 80, 1000, 2000, 86400)
    partial = AggRow("day", d, 500, 700, 300, 400, 1500, 2500, 60)
    agg = ts_mod.SeriesAgg(month_epoch=v4_month_epoch(d), month_days=[full])
    rows_out = []
    TrafficSampleModule._agg_ingest_day(agg, partial, rows_out)
    assert rows_out[0].cov_s == 86400  # 合流行(非残余 60)
    assert rows_out[0].dl_total == 1500  # totals 取后封行
    assert len(agg.month_days) == 1 and agg.month_days[0].cov_s == 86400  # 月累计器持合流行


def test_w5_credit_day_file_null_slots_then_raw_credited(tmp_path):
    """离线恢复逐槽记账: n 槽(null 期)不贡献但**不截断**其后槽位入账 ——
    _agg_credit_day_file_52(continue->break; 断连恢复常态)"""
    h0 = int(1_700_000_000) // HOUR_SECONDS * HOUR_SECONDS
    start = h0 + 600
    blk = V4Block(
        start,
        30,
        1000,
        2000,
        (V4Sample(100, 50, 1000, 2000), V4NullRun(2), V4Sample(100, 50, 1000, 2000), V4Sample(100, 50, 1000, 2000)),
    )
    pending = {}
    TrafficSampleModule._agg_credit_day_file(pending, parse_v4_day_text(format_v4_day_text("global", (blk, ))), None)
    samples = pending[h0]
    assert [round(s.dt_s, 6) for s in samples] == [30.0, 30.0]  # n 前只首区间 + n 后 r-r 区间
    assert all(s.dl_rate == 100 for s in samples)


def test_w5_credit_day_file_z_tail_end_anchor_cross_file(tmp_path, monkeypatch):
    """恢复跨天文件结算: z 尾槽上下文取**末端摊配值**(非开启快照)且跨文件连续边界
    照常入账(00:00 边界信用不丢)—— _agg_credit_day_file_64 / _recover_series_57"""
    st = TrafficV4Store(str(tmp_path))
    st.append_agg_rows(
        GLOBAL_SERIES_KEY, (AggRow("hour", int(_w5_ts(2026, 6, 1, 10, 0, 0)), 100, 200, 50, 80, 1000, 2000, 3600), )
    )
    st.append_records(
        GLOBAL_SERIES_KEY,
        "2026-06-01",
        (int(_w5_ts(2026, 6, 1, 23, 58, 30)), 30),
        (V4ZeroRun(3, 1000, 2000, None, 1300, 2300), ),
        (1000, 2000),
    )  # 23:58:30..23:59:30(3 槽), 末端摊配 1300/2300
    st.append_records(
        GLOBAL_SERIES_KEY,
        "2026-06-02",
        (int(_w5_ts(2026, 6, 2, 0, 0, 0)), 30),
        (V4Sample(100, 50, 1400, 2400), ),
        (1400, 2400),
    )  # 次日 00:00:00(跨文件连续边界 gap 30s)
    clock = FakeClock(start=_w5_ts(2026, 6, 2, 12, 0, 0))
    mgr = _w5_mgr(tmp_path, monkeypatch, clock)
    mod = mgr.host.get("qb_traffic")
    mod.start(mgr.ctx, dry_run=False)
    parsed = parse_v4_agg_text(_agg_text(tmp_path, GLOBAL_SERIES_KEY))
    assert [h.epoch for h in parsed.hours] == [int(_w5_ts(2026, 6, 1, 10, 0, 0)), int(_w5_ts(2026, 6, 1, 23, 0, 0))]
    tail_hour = parsed.hours[1]
    assert tail_hour.cov_s == 90  # 游程内 2 区间 + 跨文件边界 1 区间(变异断链在此 60)
    assert (tail_hour.dl_total, tail_hour.up_total) == (1300, 2300)  # 末端摊配值(变异退化开启快照在此 1000/2000)
    assert tail_hour.dl_avg == 0  # z 游程速率恒 0


def test_w5_evict_audit_log(tmp_path, monkeypatch):
    """按龄淘汰审计 INFO(删文件动作唯一留痕)—— _maybe_evict_32"""
    clock = FakeClock()
    mgr = _w5_mgr(tmp_path, monkeypatch, clock, rollup_window=7 * 86400.0)
    conf = mgr.config.qb_traffic
    st = TrafficV4Store(str(tmp_path))
    old = v4_epoch_date_str(clock.now() - 30 * 86400)
    os.makedirs(os.path.dirname(st.series_day_path("torrent:OLD", old)), exist_ok=True)
    with open(st.series_day_path("torrent:OLD", old), "w", encoding="utf-8", newline="\n") as f:
        f.write(f"{HEADER_LINE_V4}\nkey,torrent:OLD\n")
    mod = mgr.host.get("qb_traffic")
    mod._persistence_on = True
    mod._last_evict_check = None
    with capture_logs("auto_qb.core.modules.traffic_sample_mod") as cap:
        mod._maybe_evict(conf, clock.now())
    assert "按龄淘汰" in cap.text  # 淘汰留痕(变异 logger.info(None) 在此破)
    assert not os.path.exists(st.series_day_path("torrent:OLD", old))


def test_w5_recover_oserror_warning_carries_key(tmp_path, monkeypatch):
    """聚合恢复失败 WARNING(排障归因面): 内容含系列键与异常 —— _recover_aggregates_37"""
    clock = FakeClock()
    mgr = _w5_mgr(tmp_path, monkeypatch, clock)
    _write_day_file(tmp_path, GLOBAL_SERIES_KEY, v4_epoch_date_str(clock.now()))
    monkeypatch.setattr(TrafficV4Store, "read_agg", lambda self, key: (_ for _ in ()).throw(OSError("disk dead")))
    mod = mgr.host.get("qb_traffic")
    with capture_logs("auto_qb.core.modules.traffic_sample_mod") as cap:
        mod.start(mgr.ctx, dry_run=False)
    assert "聚合恢复失败" in cap.text and "global" in cap.text and "disk dead" in cap.text


def test_w5_recovery_stats_elapsed_bounded(tmp_path, monkeypatch):
    """恢复埋点 elapsed_s 有界(机检指标与「耗时 Ns」留痕不失真)—— _recover_aggregates_39"""
    clock = FakeClock()
    mgr = _w5_mgr(tmp_path, monkeypatch, clock)
    mod = mgr.host.get("qb_traffic")
    mod.start(mgr.ctx, dry_run=False)
    assert 0 <= mod.recovery_stats["elapsed_s"] < 5  # 变异(-> +t0)在此 ~3.4e9


def test_w5_agg_error_log_type_and_rewarn_after_recovery(tmp_path, monkeypatch):
    """聚合封口失败善后: ERROR 含原异常类型名 + 恢复健康后再错重新告警 ——
    _agg_flush_all_7 / _agg_reset_after_error_4 / _agg_flush_all_10"""
    clock = FakeClock()
    mgr = _w5_mgr(tmp_path, monkeypatch, clock)
    mod = mgr.host.get("qb_traffic")
    orig = TrafficSampleModule._agg_flush_series
    state = {"boom": True}

    def flaky(self, key, now):
        if state["boom"]:
            raise RuntimeError("agg boom")
        return orig(self, key, now)

    monkeypatch.setattr(TrafficSampleModule, "_agg_flush_series", flaky)
    with capture_logs("auto_qb.core.modules.traffic_sample_mod") as cap1:
        mod._agg_states[GLOBAL_SERIES_KEY] = ts_mod.SeriesAgg()
        mod._agg_flush_all(clock.now())
    assert sum(1 for r in cap1.records if r.levelno == logging.ERROR) == 1
    assert "RuntimeError" in cap1.text  # 异常类型不失真(变异记 NoneType 在此破)
    state["boom"] = False
    with capture_logs("auto_qb.core.modules.traffic_sample_mod") as cap2:
        mod._agg_states[GLOBAL_SERIES_KEY] = ts_mod.SeriesAgg()
        mod._agg_flush_all(clock.now())  # 恢复健康: 零 ERROR 且记忆清除
    assert sum(1 for r in cap2.records if r.levelno == logging.ERROR) == 0
    state["boom"] = True
    with capture_logs("auto_qb.core.modules.traffic_sample_mod") as cap3:
        mod._agg_flush_all(clock.now())  # 再错: 重新告警一次
    assert sum(1 for r in cap3.records if r.levelno == logging.ERROR) == 1


def test_w5_recover_diag_watermark_bound_log(tmp_path, monkeypatch):
    """恢复读集 >2 天诊断 INFO: 下界来源 = 水位日(非 fallback)且日期为读集首日 ——
    _recover_series_67/69/71/72"""
    base = _w5_ts(2026, 6, 10, 12, 0, 0)
    clock = FakeClock(start=base)
    mgr = _w5_mgr(tmp_path, monkeypatch, clock, rollup_window=30 * 86400.0)
    st = TrafficV4Store(str(tmp_path))
    st.append_agg_rows(
        GLOBAL_SERIES_KEY, (AggRow("hour", int(_w5_ts(2026, 6, 5, 10, 0, 0)), 100, 200, 50, 80, 1000, 2000, 3600), )
    )
    for i in range(6):  # 6 个天文件(读集 >2: 诊断 INFO 触发)
        _write_day_file(tmp_path, GLOBAL_SERIES_KEY, v4_epoch_date_str(base - i * 86400))
    mod = mgr.host.get("qb_traffic")
    with capture_logs("auto_qb.core.modules.traffic_sample_mod") as cap:
        mod.start(mgr.ctx, dry_run=False)
    assert "水位日 2026-06-05" in cap.text and "陈旧" in cap.text  # 来源=水位日(非 fallback)
