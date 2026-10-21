"""test_traffic_sample 测试计划: qB 口径流量采样器(plan 26-10-03-0946 方案C P1 采样器核心 + §06 配置键
+ plan 26-10-04-1957 S2a 写侧/S2b 聚合与恢复 + plan 26-10-05-2200 v4 换代 B2 写侧状态机与结算)

## 测试计划(每个测试函数一条)
- test_qb_traffic_config_absent_means_disabled: 键组缺省 -> config.qb_traffic 为 None(未启用)
- test_qb_traffic_config_parses_sample: 完整样例解析(enabled/四个时间键换算成秒, 含 flush_interval)
- test_qb_traffic_config_partial_falls_back_to_defaults: 部分键缺省回退 QbTraffic 默认值
- test_qb_traffic_config_rejects_bad_section: 段非 dict / 未知键 / enabled 非布尔
- test_qb_traffic_config_bounds_matrix: 各时间/布尔键边界矩阵(1.5S 需 main_tick 配合 / 60S~1H / 1H~90D / 7D~无上限 恰好压线收, 压线外拒)
- test_qb_traffic_sample_interval_below_main_tick_rejected: 下限硬校验(26-10-04-1957 §06.1) ——
  sample_interval < main_tick 加载期拒(1.5s 档在 main_tick=2s 下被拒), 恰等于压线收
- test_qb_traffic_sample_interval_multiple_mismatch_not_an_error: 裁决 D5 —— 非 main_tick 整数倍校验层不报错
- test_qb_traffic_flush_interval_bounds: flush_interval —— dataclass 缺省 600 /
  60~3600s 整数秒压线收 / 越界与非整数秒与坏格式聚合报错
- test_sample_task_registered_when_enabled: enabled=true -> **队列零任务** + 时钟线钩子首拍即采(issue 26-10-16-0954)
- test_sample_not_starved_by_immediate_task_backlog: 数百立即到期任务占满队列(重启补建同形)时采样节拍不中断(回归主判据)
- test_sample_clock_line_gate_and_hot_reload_enable: 未到 effective interval 不重复采; 停用零采样零任务; 热重载 enabled=true 不经队列重建即开采
- test_sampling_runs_on_caller_thread: 采样在调用任务线钩子的线程(主循环线程)内同步执行, 模块不建线程(单写线程不变式)
- test_first_sample_only_establishes_baseline: 首个采样只立基线不出增量(首窗 null), 次轮出正常增量
- test_counter_rollback_records_reset_no_negative: 模拟 qB 重启(计数器回落) -> 不产负增量、增量记 null、基线更新为 cur、INFO 记重置
- test_disconnect_produces_null_point: qB 断连(store.client None) -> 全局 n 游程槽 + latest 镜像 null 点、单种本轮不采样、基线不动
- test_missing_fields_produce_null_point_not_zero: server_state 关键字段缺失/空值 -> null 处理(不写 0)且基线不推进
- test_torrent_active_filter_zero_rows_when_idle: 活跃种子照常产 r; 空闲种子零 r(零样本按游程纪律压缩, 从未传输者无游程)
- test_disabled_at_runtime_handler_noop: 运行期关闭 -> 采样体短路不采样不动内存(队列无关)
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
- test_zrun_cap_safety_valve_seals_at_day_level: 天级保险闸(N4): 86400 样本(1s 档)触闸封口防溢出,
  正常空闲段不应触闸; 游程 dt 链跨度 = 全天 < ZRUN_FLUSH_S
- test_zero_run_requires_valid_totals_snapshot: 开 z 游程需 totals 快照: 缺失不开新游程; 已开游程只推进无需重读
- test_global_always_opens_run_vs_torrent_gated: 全局零样本恒开游程(无门) vs 单种数据门拦截(对照)
- test_restart_loses_at_most_one_open_run: 重建 sampler 实例(重启)丢开放游程 <=1(纯零信息), 已落盘块不受影响,
  零样本按纪律重新开游程(重启后首个封口游程成为新块首)
- test_zero_samples_do_not_touch_baselines_or_latest: 零样本不动 baselines/latest(镜像冻结在最后活跃点)
- test_dry_run_no_disk_but_memory_runs_advance: dry_run 零落盘; 缓冲游程内存照常推进, flush 静默跳过写
- test_dt_drift_boundary_family: tol 边界族(§2.3 判据=累积漂移) —— 压线行(恰 250ms)不写 dt / 超线行写实测 dt 并
  自然复位 / 稳态小漂移(150ms/行)退化周期写 / 空载(等间隔)零 dt 行; 单块全序列 roundtrip 与实测一致
  (v4 关块谓词下块随 flush 关闭会重锚游标, 故中途断言读缓冲、末尾一次 flush 落盘)
- test_clock_rollback_clamped_dt_min_1: 时钟回拨单调钳制 dt_ms = max(1, 实测) >= 1
- test_interval_change_hot_reload_new_block_and_effective_interval: 热重载改采样率即时生效(§3.5):
  _effective_interval 更新 + 旧块落盘(旧 interval) + 新块带新 interval(新旧数据分块各有 interval)
- test_interval_mismatch_ceils_and_warns_once: 运行期失配(D5): 向上取整到下一倍数(_effective_interval=取整值) +
  告警一次(防重复), 配置再变记忆复位; 不拒采
- test_interval_decimal_match_kept_not_ceiled: 整数倍匹配的小数档(1.5 配 main_tick=1.5)原样生效 ——
  _effective_interval/块头 B 行均 1.5, 失配告警不触发, 同块零漂移(2026-10-05 修复)
- test_day_boundary_cut: 跨天切块(00:00 硬切, §3.3): 23:59 块落旧日期文件 + 00:00 新块新日期文件, 各带正确块头
- test_day_boundary_seals_open_run: 跨天封游程: 游程不跨天(00:00 样本先封旧游程); 块首单槽游程不写 dt
- test_buffer_slot_cap_3600_early_flush: Q3 保险闸: 缓冲槽 >= 3600 提前单独 flush(v4 带 r 行的块随闸值关闭)
- test_stop_flushes_all_and_seals_open_runs: stop() 钩子(§3.4): 封全部开放游程 + 全量 flush; 幂等
- test_stop_dry_run_short_circuit: stop() dry_run 短路零落盘
- test_flush_oserror_discards_block_warns_once: 落盘失败(OSError)不上抛、连续失败只告警一次;
  失败块丢弃并复位块状态(dt 链卫生: 下次成功写起新块)
- test_flush_all_drops_shell_buffers: 内存卫生: 无开放块无待写记录无游程且未采样的 shell 缓冲被清除

聚合分层与恢复(plan 26-10-04-1957 S2b §04):
- test_agg_hour_row_dt_weighted_across_hour_boundary: hour 行产出 —— 前向记账逐区间入账,
  信用区间跨小时界自然拆分; avg = dt 加权 / max 逐记录取大 / totals 级末快照 / cov_s = Σ桶内覆盖;
  未完结小时留累计器; hour 行并入 day 累计器(严格逐级)
- test_agg_hour_degenerate_equal_interval_matches_v2: dt_i ≡ interval_s 时 hour 行与现行 v2
  等间隔均值公式 round(Σrate/n)(v2 纯活跃桶口径, 内联对照)逐列一致, 且等于 v4_hour_agg 标称输入
- test_agg_flush_subsecond_hour_rolls_up_without_raise: 亚秒小时桶的日封口(2026-10-13 真机
  「逐级聚合无有效覆盖」回归)—— 迟到补记重建的小时桶只带亚秒残余覆盖时 cov_s 下限 1,
  day 封口不再抛异常(修复前 Σcov_s = 0 -> _agg_flush_series 每轮 flush 抛且整批 agg 行丢弃)
- test_agg_reseal_merges_late_credit_keeps_full_coverage: 已封小时被迟到补记重建后再封走**合流**
  (2026-10-13 真机「重封替换丢覆盖」回归)—— 末行 cov 回到整小时、avg 按两段 cov 加权,
  day 累计器同持合流行; 修复前替换语义只留残余(真机日行 cov_s 44712 vs 全量 86400)
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
- test_stop_seals_aggregates_and_dry_run_short_circuit: stop() 聚合封口 —— 完结层级落 agg,
  幂等; dry_run 短路(累计器内存照常推进, 零落盘)
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

v4 定约用例(plan 26-10-05-2200 §04 表 ③⑤⑥⑦, B2 落地):
- test_v4_counter_reset_forces_block_reopen: ③ 计数器重置强制关块 —— 重置后块内负 delta 不出现,
  新块基线 = 重置后 totals(首记录 delta = 0)
- test_v4_cross_block_settlement_online_offline_same_source: ⑤ 跨块覆盖结算两路同源 —— 在线 _agg_feed
  与离线 _agg_credit_day_file 复用判定单点, 对连续边界/崩溃间隙/00:00 跨天边界产出逐桶一致 cov_s
- test_v4_idle_block_stays_open_single_b_row_and_live_tail_identity: ⑥ 空闲块不关 —— 纯空闲系列
  (数据门有数据 + 零速)主文件零写入, 封口后恰 1 条 B 行 + 1 条长 z 行; 跨 flush 开放 z 游程的
  LiveTail 复原与落盘重算恒等; 恢复传输后 r 行 delta <= flush 窗 x 速率
- test_v4_non_z_seal_midnight_materializes_idle_b_z_batch: ⑦ 非 z 事件封口 —— 长空闲段恰 1 条长 z 行,
  00:00 物化进当日天文件(B + z 一批 append); 次日 LiveTail 开放游程跨天接力与落盘重算恒等
- test_v4_crash_restart_idle_window_is_vacuum: ⑦ 崩溃重启该时段 = 真空 —— 空闲段 cov_s 缺失,
  hour 行 avg 不被零速稀释(无偏)

时钟/落盘纪律: 需要确定时刻的用例经 monkeypatch 固定模块 time 引用(_Clock 逐轮推进); flush 时点
除专项驱动用例外用 mod._flush_all_series() 直调(绕开驱动计时, 驱动时序由专项用例钉住)。

形态 D 封口末端锚点(plan 26-10-16-1509 §04, z 行扩列; 五条封口路径):
- test_torrent_idle_run_snapshot_fixed_at_open: 路径 ① 末端列 = 封口触发样本读数(冻结列不变)
- test_zrun_cap_safety_valve_seals_at_day_level: 路径 ⑤ 保险闸封口同样写末端对
- test_zrun_end_anchor_tracked_reading_on_stop: 路径 ③ 无样本在手 -> 末端锚点 = 游程内最后
  一条零样本读数(跟踪字段)
- test_zrun_end_anchor_tracked_reading_on_interval_change: 路径 ④ 改间隔关块同口径
- test_zrun_end_anchor_counter_reset_degrades_to_open: 游程内计数器重置 -> 末端按开启快照
  退化(末端列 delta 非负, 文件零坏行)

P1-T1.2 守卫与容错簇(计划 26-10-20-2101, 覆盖率缺口清偿):
- test_pending_agg_rows_skips_empty_and_zero_coverage_buckets: 活尾 pending 行 —— 空桶不留行 /
  零有效覆盖桶 ValueError 逐一跳过(不出行 = null 语义), 无子行时 day/month 两级不出行
- test_apply_interval_without_main_tick_uses_raw_interval: main_tick 未配置(0) -> 生效间隔
  = sample_interval 原值(不取整, 无失配告警)
- test_close_blocks_for_interval_change_skips_runless_and_unopened: 改间隔关块只封「有开放块」
  的游程与缓冲 —— 无缓冲的游程 / 未开块的 shell 缓冲零操作(不误封、不误 flush)
- test_torrent_active_missing_fields_takes_null_run: 活跃种子缺字段 -> n 游程(不写 0 不吞样本)
- test_torrent_zero_speed_readings_drift_defensive_raw_row: 零速过滤与字段读数口径漂移的防御支
  —— 读数非零时按 r 记录处理, 绝不把活跃读数吞进游程
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
- test_stop_early_return_when_disabled_or_no_data_dir: stop() 在 qb_traffic 段缺失/未启用/
  data_dir 为空时零操作(不封游程不 flush)
"""
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
from helpers import FakeClient, FakeTorrent, capture_logs, make_manager, seed_store
from webui_helpers import _enable_qb_traffic, _qb_v4

# 写入侧凭据判据的测试 idiom 消误报(2026-10-16 形态 D 轮用户拍板, 样板与缘由见
# pitfalls/testing/credential-shape-write-guard.md): 键名程序化拆写, 判据按「键名标识符 +
# 赋值形态」匹配 —— 拆写后键名不再出现在赋值位; 行为零变化(字典键值/YAML 输出逐位一致)。
_PW_KEY = "pass" + "word"  # qB 配置夹具键名
_AUTH_HEADER_KEY = "Auth" + "orization"  # 测试鉴权头键名


# ---------- 构造辅助 ----------
def _ss(**overrides) -> dict:
    """合法 server_state 样例(六字段齐全, 与 qB sync 响应同键名)"""
    base = {
        "dl_info_speed": 1024,
        "up_info_speed": 2048,
        "alltime_dl": 10_000_000,
        "alltime_ul": 20_000_000,
        "dl_info_data": 1_000_000,
        "up_info_data": 2_000_000,
    }
    base.update(overrides)
    return base


def _active_torrent(hash="HASH123", **kw) -> FakeTorrent:
    """活跃种子(默认 dlspeed>0); 字段可覆盖"""
    kw.setdefault("dlspeed", 512)
    kw.setdefault("upspeed", 256)
    kw.setdefault("downloaded", 5_000_000)
    kw.setdefault("uploaded", 3_000_000)
    kw.setdefault("downloaded_session", 500_000)
    kw.setdefault("uploaded_session", 300_000)
    return FakeTorrent(hash=hash, **kw)


def _mgr_with_traffic(tmp_path, qb_traffic) -> object:
    mgr = make_manager(str(tmp_path / "state.json"))
    mgr.config.data_dir = str(tmp_path)  # v3 天文件落盘根目录(真实配置恒非空, loaders 默认 auto-qb-data)
    mgr.client = FakeClient()
    if qb_traffic is not None:
        mgr.config.qb_traffic = qb_traffic
    return mgr


def _run_sample(mgr, dry_run: bool = False) -> None:
    """直调一轮采样(时钟线钩子的执行体, 与 test_speed_curve._run_curve 同款: 不经队列,
    也不经到期闸门 —— 闸门/节拍由 test_sample_clock_line_* 两条专测钉住)"""
    mgr.host.get("qb_traffic").handle_traffic_sample(dry_run=dry_run)


def _flush(mod) -> None:
    """强制全系列批量 flush(绕开驱动计时; 驱动时序由专项用例钉住)"""
    mod._flush_all_series()


def _v4_path(tmp_path, key: str, ts: float):
    """系列键 + 时刻 -> 当天 v3 天文件路径(Path)"""
    from pathlib import Path

    return Path(v4_day_file_path(str(tmp_path), key, v4_epoch_date_str(ts)))


def _v4_read(tmp_path, key: str, ts: float):
    """读系列当天 v3 天文件并解析(不存在返回 None)"""
    p = _v4_path(tmp_path, key, ts)
    return parse_v4_day_text(p.read_text(encoding="utf-8")) if p.exists() else None


def _v4_series_dir(tmp_path, infohash: str):
    return tmp_path / "qb-traffic-v4" / "torrents" / infohash


# ---------- 配置键全链(§06) ----------
def _cfg_dict(qb_traffic_spec, main_tick=None) -> dict:
    """配置 dict 样例; main_tick 可选(v3 下限语义: sample_interval >= main_tick 硬校验要现取它)"""
    top = {
        "qbittorrent": {
            "host": "127.0.0.1",
            "port": 8080,
            "username": "u",
            _PW_KEY: "p"
        },
        "trackers": {},
        "qb_traffic": qb_traffic_spec,
    }
    if main_tick is not None:
        top["main_tick"] = main_tick
    return {"config": top}


def _load(tmp_path, qb_traffic_spec):
    p = tmp_path / "config.yml"
    p.write_text(yaml.dump(_cfg_dict(qb_traffic_spec), allow_unicode=True), encoding="utf-8")
    return load_config(str(p))


def test_qb_traffic_config_absent_means_disabled(tmp_path):
    """键组缺省 -> qb_traffic 为 None(未启用); 全默认实例同样为 None"""
    p = tmp_path / "config.yml"
    p.write_text(
        yaml.dump(
            {
                "config":
                    {
                        "qbittorrent": {
                            "host": "127.0.0.1",
                            "port": 8080,
                            "username": "u",
                            _PW_KEY: "p"
                        },
                        "trackers": {}
                    }
            },
            allow_unicode=True
        ),
        encoding="utf-8"
    )
    assert load_config(str(p)).qb_traffic is None


def test_qb_traffic_config_parses_sample(tmp_path):
    """完整样例解析: enabled 布尔化 + 各时间键换算成秒(含 v3 新键 flush_interval)"""
    cfg = _load(
        tmp_path, {
            "enabled": "true",
            "sample_interval": "1M",
            "flush_interval": "10M",
            "raw_window": "48H",
            "rollup_window": "60D",
        }
    ).qb_traffic
    assert cfg.enabled is True
    assert cfg.sample_interval == 60.0
    assert cfg.flush_interval == 600.0
    assert cfg.raw_window == 48 * 3600.0
    assert cfg.rollup_window == 60 * 86400.0


def test_qb_traffic_config_partial_falls_back_to_defaults(tmp_path):
    """部分键缺省回退默认值(30S/10M/24H/30D, enabled 缺省 false)"""
    cfg = _load(tmp_path, {"enabled": "true"}).qb_traffic
    assert cfg.enabled is True
    d = QbTraffic()
    assert cfg.sample_interval == d.sample_interval == 30.0
    assert cfg.flush_interval == d.flush_interval == 600.0
    assert cfg.raw_window == d.raw_window == 86400.0
    assert cfg.rollup_window == d.rollup_window == 30 * 86400.0


def test_qb_traffic_config_rejects_bad_section():
    """段非 dict / 未知键 / enabled 非布尔 -> 聚合报错(fail-fast)"""
    errors = validate_config(_cfg_dict("nope"))
    assert any("config.qb_traffic" in e and "字典" in e for e in errors)
    errors = validate_config(_cfg_dict({"unknown_key": "1", "enabled": "maybe"}))
    assert any("未知键" in e and "qb_traffic" in e for e in errors)
    assert any("config.qb_traffic.enabled" in e for e in errors)


def test_qb_traffic_config_bounds_matrix():
    """边界矩阵: 恰好压线合法(含等价秒数), 压线外拒绝; 各时间键独立校验"""
    # 合法: 上下边界恰好压线(1.5S 需 main_tick <= 1.5s 才过下限硬校验 / 1H~90D / 7D~无上限)
    ok = validate_config(
        _cfg_dict(
            {
                "enabled": "true",
                "sample_interval": "1.5S",
                "flush_interval": "10M",
                "raw_window": "1H",
                "rollup_window": "7D",
            },
            main_tick="1S",  # 1.5S >= main_tick: 下限语义自证(默认 main_tick=2 时 1.5S 已非法, 见下方专项用例)
        )
    )
    assert ok == [], ok
    ok = validate_config(
        _cfg_dict(
            {
                "enabled": "false",
                "sample_interval": "10M",
                "flush_interval": "1H",  # 3600s 恰好压上边界
                "raw_window": "90D",
                "rollup_window": "36500D",  # 保留窗无上限: 100 年也合法(等效永久保留)
            }
        )
    )
    assert ok == [], ok
    # 越界: 各键压线外一秒即拒
    bad = validate_config(_cfg_dict({"sample_interval": "601S"}))
    assert any("sample_interval" in e for e in bad), bad
    bad = validate_config(_cfg_dict({"raw_window": "30M"}))
    assert any("raw_window" in e for e in bad), bad
    bad = validate_config(_cfg_dict({"raw_window": "91D"}))
    assert any("raw_window" in e for e in bad), bad
    bad = validate_config(_cfg_dict({"rollup_window": "6D"}))
    assert any("rollup_window" in e for e in bad), bad


def test_qb_traffic_sample_interval_below_main_tick_rejected():
    """v3 下限语义(plan 26-10-04-1957 §06.1): sample_interval < main_tick 加载期硬拒

    回归锚: 1.5s 档在校验放宽时曾合法, main_tick=2s 下必须被拒(采样任务由主循环节拍驱动)。
    """
    errors = validate_config(_cfg_dict({"sample_interval": "1.5S"}, main_tick="2S"))
    assert any("sample_interval" in e and "main_tick" in e for e in errors), errors
    # 压线即合法: 恰等于 main_tick 收
    assert validate_config(_cfg_dict({"sample_interval": "2S"}, main_tick="2S")) == []


def test_qb_traffic_sample_interval_multiple_mismatch_not_an_error():
    """裁决 D5: 非 main_tick 整数倍只是精度损耗, 校验层不报错(告警落采样模块检测点, S4 不落)"""
    assert validate_config(_cfg_dict({"sample_interval": "3S"}, main_tick="2S")) == []


def test_qb_traffic_flush_interval_bounds():
    """flush_interval(v3 新键): 60~3600s 整数秒压线收; 越界 / 非整数秒 / 坏格式聚合报错"""
    assert QbTraffic().flush_interval == 600.0  # dataclass 缺省 600
    for good in ("60S", "600S", "1H", "10M"):  # 压线 + 等价写法
        assert validate_config(_cfg_dict({"flush_interval": good})) == [], good
    bad = validate_config(_cfg_dict({"flush_interval": "30S"}))
    assert any("flush_interval" in e and ">= 60" in e for e in bad), bad
    bad = validate_config(_cfg_dict({"flush_interval": "7200S"}))
    assert any("flush_interval" in e and "<= 3600" in e for e in bad), bad
    bad = validate_config(_cfg_dict({"flush_interval": "90.5S"}))
    assert any("flush_interval" in e and "整数秒" in e for e in bad), bad
    bad = validate_config(_cfg_dict({"flush_interval": "abc"}))
    assert any("config.qb_traffic.flush_interval" in e for e in bad), bad


# ---------- 时钟线挂载(issue 26-10-16-0954: 采样移出队列, 挂任务线钩子) ----------
def _add_backlog(mgr, n: int) -> list:
    """模拟重启/热重载的种子级补建: n 个立即到期的种子级任务占满队列(interval 60s)。
    返回执行记录列表 —— 积压被弹走一份就会 requeue(不再是「队列剩多少」), 故判「排水
    是否完成」只看执行计数。"""
    now = time.time()
    done = []

    def handler(task, dry_run):
        done.append(task.hash)
        return True  # REQUEUE: 回到队列等下一个 interval(本用例不推进真实时钟 -> 不再到期)

    for i in range(n):
        mgr.task_queue.add_task(
            Task("internal", "maintenance", hash=f"h{i:04d}", interval=60.0, handler=handler), now=now
        )
    return done


def _spy_sample_rounds(monkeypatch, clock) -> list:
    """给「一轮采样落定」的单点(活尾发布, 采样体两条出口各一次)挂 spy, 返回每轮时刻列表"""
    rounds = []
    orig = TrafficSampleModule._publish_live_tail

    def spy(self):
        rounds.append(clock.now)
        return orig(self)

    monkeypatch.setattr(TrafficSampleModule, "_publish_live_tail", spy)
    return rounds


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
    clock = _Clock()
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.config.main_tick = 30.0  # 采样节拍 = 1 个主循环拍(每拍都该采到)
    mgr.store.server_state = _ss()
    mod = mgr.host.get("qb_traffic")
    mod.start(mgr.ctx, dry_run=False)
    rounds = _spy_sample_rounds(monkeypatch, clock)
    executed = _add_backlog(mgr, 500)  # 500 个立即到期任务: 20/拍 -> 25 拍才排空
    for _ in range(20):  # 排水窗全程(20 拍只排掉 400 个)
        clock.advance(30)
        mgr._task_line(dry_run=False)
    assert len(rounds) == 20, f"排水窗内采样被饿死: 只采到 {len(rounds)} 轮(期望 20)"
    # 判据自检: 积压确实尚未排空(否则本用例没落在被饿死的窗口里)
    assert len(executed) == 400, f"本拍排空量偏离配额: {len(executed)}"


def test_sample_clock_line_gate_and_hot_reload_enable(tmp_path, monkeypatch):
    """时钟线到期闸门 + 启停: 未到 effective interval 不重复采; 停用零采样; 热重载
    enabled=true **不经 queue_rebuilt 相位**即开采(采样已与队列解耦)"""
    clock = _Clock()
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.config.main_tick = 2.0  # 时钟线每 2s 一拍, 采样间隔 30s -> 闸门只在到点放行
    mgr.store.server_state = _ss()
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
    mgr.store.server_state = _ss()
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
    mgr.store.server_state = _ss()
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)  # 采样体无返回值(已非队列 handler; issue 26-10-16-0954)
    g1 = mod.latest[GLOBAL_SERIES_KEY]
    assert g1.dl_inc is None and g1.up_inc is None  # 首窗 null
    assert g1.dl_rate == 1024 and g1.up_rate == 2048  # 速率直采
    assert g1.dl_total == 10_000_000 and g1.dl_session == 1_000_000  # 累计快照照存
    assert mod._baselines[GLOBAL_SERIES_KEY] == {"dl_total": 10_000_000, "up_total": 20_000_000}
    # 次轮: 累计推进 -> 正常增量; 会话累计照存快照(不差分)
    mgr.store.server_state = _ss(alltime_dl=10_000_500, alltime_ul=20_001_000, dl_info_data=1_000_300)
    _run_sample(mgr)
    g2 = mod.latest[GLOBAL_SERIES_KEY]
    assert g2.dl_inc == 500 and g2.up_inc == 1000
    assert g2.dl_session == 1_000_300


def test_counter_rollback_records_reset_no_negative(tmp_path):
    """模拟 qB 重启(计数器回落): 不产负增量、增量记 null、基线更新为 cur、INFO 记重置"""
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)  # 立基线
    mgr.store.server_state = _ss(alltime_dl=9_000_000, alltime_ul=20_000_000)  # dl 回落(qB 重启), ul 不变
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
    mgr.store.server_state = _ss()
    seed_store(mgr, [_active_torrent()])
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
    mgr.store.server_state = _ss()
    del mgr.store.server_state["dl_info_speed"]
    _run_sample(mgr)
    g = mod.latest[GLOBAL_SERIES_KEY]
    assert g.dl_inc is None and g.up_rate is None and g.dl_total is None
    assert GLOBAL_SERIES_KEY not in mod._baselines  # 无读数 => 基线不立
    # 显式 None 同样按空值处理
    mgr.store.server_state = _ss(alltime_dl=None)
    _run_sample(mgr)
    assert mod.latest[GLOBAL_SERIES_KEY].up_rate is None
    assert GLOBAL_SERIES_KEY not in mod._baselines


def test_torrent_active_filter_zero_rows_when_idle(tmp_path):
    """活跃过滤(v3 §3.2 口径): 活跃(dlspeed>0 or upspeed>0)照常产 r; 空闲种子零 r
    —— 从未传输者(数据门拦截)连游程都不开, latest 无其采样点"""
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    seed_store(
        mgr,
        [
            _active_torrent("DL_ACTIVE", dlspeed=100, upspeed=0),  # 仅下载活跃
            _active_torrent("UL_ACTIVE", dlspeed=0, upspeed=200),  # 仅上传活跃
            FakeTorrent(hash="IDLE1"),  # 全空闲(从未传输: 无数据)
            _active_torrent("IDLE2", dlspeed=0, upspeed=0),  # 显式 0 = 空闲
        ],
    )
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)
    assert "torrent:DL_ACTIVE" in mod.latest and "torrent:UL_ACTIVE" in mod.latest
    assert "torrent:IDLE1" not in mod.latest and "torrent:IDLE2" not in mod.latest  # 空闲零 r
    assert "torrent:IDLE1" not in mod._open_runs and "torrent:IDLE2" not in mod._open_runs  # 无数据不开游程
    t = mod.latest["torrent:DL_ACTIVE"]
    assert t.dl_rate == 100 and t.dl_total == 5_000_000 and t.dl_inc is None  # 单种首窗同样只立基线


def test_disabled_at_runtime_handler_noop(tmp_path):
    """运行期关闭(L0 换对象): 采样体入口现读判据 -> 短路不采样不动内存(与队列无关)"""
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    mod = mgr.host.get("qb_traffic")
    mod.start(mgr.ctx, dry_run=False)
    mgr.config.qb_traffic = QbTraffic(enabled=False)
    _run_sample(mgr)
    assert mod.latest == {} and mod._baselines == {}  # 零采样零内存变更


def test_enabled_false_creates_zero_files_or_dirs(tmp_path):
    """enabled=false 与键组缺省两种情形: start + 采样全程零新建文件/目录(保守默认验收, 黄金法则 2)"""
    for qb in (QbTraffic(enabled=False), None):
        mgr = _mgr_with_traffic(tmp_path, qb)
        mgr.store.server_state = _ss()
        seed_store(mgr, [_active_torrent()])
        mod = mgr.host.get("qb_traffic")
        mod.start(mgr.ctx, dry_run=False)
        _run_sample(mgr)
        _run_sample(mgr)
        assert sorted(str(p) for p in tmp_path.rglob("*")) == [], qb


def test_enabled_true_persists_under_data_dir(tmp_path, monkeypatch):
    """enabled=true: 采样点落 v3 天文件 <data_dir>/qb-traffic-v4/{global,torrents/<h>}/<date>.dat
    (头行 v3 + key 行 + B 块头 + r 行); 时钟整间隔步进 -> 零漂移零 dt 行; 会话快照列不落盘"""
    clock = _Clock()
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    seed_store(mgr, [_active_torrent()])
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)  # t0
    clock.advance(30)
    _run_sample(mgr)  # t0+30
    _flush(mod)
    gpath = _v4_path(tmp_path, GLOBAL_SERIES_KEY, clock.now)
    tpath = _v4_path(tmp_path, "torrent:HASH123", clock.now)
    assert gpath.is_file() and tpath.is_file()
    lines = gpath.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "# auto-qb qb-traffic v4" and lines[1] == "key,global"
    parsed = parse_v4_day_text(gpath.read_text(encoding="utf-8"))
    assert parsed.key == "global" and len(parsed.blocks) == 1
    block = parsed.blocks[0]
    assert block.start_epoch == int(clock.now) - 30 and block.interval_s == 30  # B 块头
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


# ---------- 开放游程 + 批量落盘(plan 26-10-04-1957 S2a §3.2/§3.3) ----------
class _Clock:
    """可控时钟: 替换采样模块内的 time 名(monkeypatch 只换 traffic_sample_mod 的引用,
    不影响 store 等其它模块), 逐轮推进采样时刻"""
    def __init__(self, now: float = 1_700_000_000.0):
        self.now = now

    def time(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _idle_state(**overrides) -> dict:
    """速率 (0,0) 的合法 server_state(totals 照常在 all-time 对上)"""
    return _ss(dl_info_speed=0, up_info_speed=0, **overrides)


def test_flush_driver_interval_and_deferred_first_round(tmp_path, monkeypatch):
    """flush 驱动(§3.3): 进程首轮只记时不提前 flush(批量优先); now - last_flush >=
    flush_interval 才全系列批量落盘; v4 关块谓词(flush ∧ has_r_row)下带 r 行的块随
    flush 关闭, 之后的记录开新块(每块块头恰写一次)"""
    clock = _Clock()
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30, flush_interval=60))
    mgr.store.server_state = _ss()
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)  # t0: r 进缓冲; 首轮只记 flush 时点
    assert _v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now) is None
    assert mod._buffers[GLOBAL_SERIES_KEY].records
    clock.advance(30)
    _run_sample(mgr)  # 30 < 60: 未到点, 缓冲滞留
    assert _v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now) is None
    clock.advance(30)
    _run_sample(mgr)  # 60 >= 60: 批量落盘(本轮记录含在内; 块头随批)+ 关块(has_r_row)
    parsed = _v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now)
    assert parsed is not None and len(parsed.blocks) == 1 and len(parsed.blocks[0].records) == 3
    buf = mod._buffers[GLOBAL_SERIES_KEY]
    assert buf.records == [] and buf.start_epoch is None  # v4: 带 r 行的块随 flush 关闭
    clock.advance(30)
    _run_sample(mgr)  # 30 < 60: 缓冲滞留(新块已开)
    assert len(_v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now).blocks[0].records) == 3
    clock.advance(30)
    _run_sample(mgr)  # 60 >= 60: 新块落盘(自带新块头)
    parsed = _v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now)
    assert len(parsed.blocks) == 2 and len(parsed.blocks[1].records) == 2  # 两块两 B 行, 每块头恰一次


def test_global_idle_run_stays_open_across_flush_and_seals_on_resume(tmp_path, monkeypatch):
    """空闲块不关(v4 §01 关块谓词 + 「空闲封口」): 全局空闲开放 z 游程跨 flush 时点滞留
    内存(N4 天级保险闸, 600s 不再常态触发), 空闲段不落盘; 恢复传输(非 z 事件)封口,
    z 游程成为新块首(基线 = 该快照, delta = 0); 恢复 r 行 delta <= flush 窗 x 速率"""
    clock = _Clock()
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)  # t0: 活跃 -> r 记录进缓冲
    mgr.store.server_state = _idle_state()
    for _ in range(21):  # t0+30 .. t0+630: 零样本只推进游程, 跨 600s flush 时点
        clock.advance(30)
        _run_sample(mgr)
    assert GLOBAL_SERIES_KEY in mod._open_runs  # 空闲块不关: 游程仍开放(天级保险闸未触)
    parsed = _v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now)
    assert len(parsed.blocks) == 1 and [type(r) for r in parsed.blocks[0].records] == [V4Sample]
    # 恢复传输(非 z 事件): 封 z 游程成新块首 + r 记录; 下一 flush 关块重开
    mgr.store.server_state = _ss(alltime_dl=10_000_400, alltime_ul=20_000_200)
    clock.advance(30)  # t0+660
    _run_sample(mgr)
    assert GLOBAL_SERIES_KEY not in mod._open_runs  # 封口即移除
    _flush(mod)
    parsed = _v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now)
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
    clock = _Clock()
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    rec = _active_torrent("HASH123", downloaded=5_000_000, uploaded=3_000_000)
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
    parsed = _v4_read(tmp_path, rel_key, clock.now)
    recs = parsed.blocks[0].records
    assert [type(r) for r in recs] == [V4Sample, V4ZeroRun, V4Sample]  # 文件序 = 时间序


def test_never_transferred_torrent_zero_files_runs_entries(tmp_path, monkeypatch):
    """从未传输的种子: 零文件、零游程(数据门 = 目录判定 + 进程内缓存, §3.2)"""
    clock = _Clock()
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
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
    clock = _Clock()
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    rec = _active_torrent("HASH123")
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
    parsed = _v4_read(tmp_path, key, clock.now)
    recs = parsed.blocks[0].records
    assert [type(r) for r in recs] == [V4Sample, V4ZeroRun, V4Sample]  # 文件序 = 时间序
    z = recs[1]
    assert z.run_len == 1  # 封 [start, last_seen](单零样本游程)
    assert (z.dl_total, z.up_total) == (5_000_000, 3_000_000)  # 快照 = 零样本 all-time 对(种子 totals)
    assert all(r.dt_ms is None for r in recs)  # 整间隔步进: 零漂移


def test_disconnect_seals_run_before_null_r2(tmp_path, monkeypatch):
    """触发 (2)(R2): null 到达先封开放 z 游程再记 n 游程 —— z 覆盖不横跨断连期
    (把「未知」虚标成「观测到 0」的 v3 形态 = z 与 n 各占各的槽)"""
    clock = _Clock()
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
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
    mgr.store.server_state = _ss()
    clock.advance(30)
    _run_sample(mgr)  # t0+120: 重连且活跃 -> 封 n 游程(触发 (1)) + r
    _flush(mod)
    parsed = _v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now)
    recs = parsed.blocks[0].records
    assert [type(r) for r in recs] == [V4Sample, V4ZeroRun, V4NullRun, V4Sample]  # z 行在 n 之前
    assert recs[1].run_len == 2  # z 封 [t0+30, t0+60], 末日早于断连轮
    assert recs[2].run_len == 1  # n 槽 = 断连轮(重连非零样本封口)


def test_zrun_cap_safety_valve_seals_at_day_level(tmp_path, monkeypatch):
    """天级保险闸(N4): 开放 z 游程样本数 >= ZRUN_CAP_SAMPLES(86400 = ceil(86400/1s))
    强制封口防溢出 —— 正常空闲段任何路径都不应触闸(触闸即测试 bug), 本用例直灌游程
    推到闸值验证保险闸本身(z 游程 dt 链推算核对: 跨度 = 全天 < ZRUN_FLUSH_S)"""
    clock = _Clock()
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=1))
    mgr.store.server_state = _ss()
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
    assert (z.dl_total_end, z.up_total_end) == (10_000_000, 20_000_000)  # 形态 D 路径 ⑤ 同样写末端对(此几何下 = 开启快照)
    slots = v4_block_slots(parsed.blocks[0])
    assert len(slots) == ZRUN_CAP_SAMPLES
    span = slots[-1].ts - slots[0].ts  # 块首游程: [首零样本, 第 86400 零样本] 端点含
    assert span == ZRUN_CAP_SAMPLES - 1
    assert span < ZRUN_FLUSH_S  # 保险闸阈值天级(N4)


def test_zero_run_requires_valid_totals_snapshot(tmp_path, monkeypatch):
    """零样本读数口径: 开 z 游程需要合法 totals 快照 —— totals 缺失的零样本不开新游程
    (空闲不出 null 槽); 已开游程的零样本只推进 last_seen 无需重读 totals"""
    clock = _Clock()
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    rec = _active_torrent("HASH123")
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
    assert run.samples == 2 and run.last_seen == clock.now  # 只推进, 不因 totals 缺失断游程


def test_global_always_opens_run_vs_torrent_gated(tmp_path, monkeypatch):
    """两系列零样本纪律对照(§3.2): 全局恒开游程(无数据门); 单种目录判定门拦截
    (从未传输不开游程不建文件)"""
    clock = _Clock()
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
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
    clock = _Clock()
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)  # t0: 活跃 -> r 进缓冲
    _flush(mod)  # 优雅落盘 r(块 1)
    mgr.store.server_state = _idle_state()
    clock.advance(30)
    _run_sample(mgr)  # t0+30: 开游程
    clock.advance(30)
    _run_sample(mgr)  # t0+60: 推进(未封口, 随进程消失)
    mod2 = TrafficSampleModule(mgr.ctx)  # 重启: 新实例, buffers/_open_runs 全空
    for _ in range(3):  # t0+90..t0+150: 零样本重新开游程(跨 flush 时点不封 —— 空闲块不关)
        clock.advance(30)
        mod2.handle_traffic_sample(dry_run=False)
    assert GLOBAL_SERIES_KEY in mod2._open_runs
    mgr.store.server_state = _ss(alltime_dl=10_000_100, alltime_ul=20_000_100)  # 恢复传输(非 z 事件)
    clock.advance(30)  # t0+180: 封 z(4 槽) + r
    mod2.handle_traffic_sample(dry_run=False)
    mod2._flush_all_series()
    parsed = _v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now)
    assert len(parsed.blocks) == 2  # 重启前后各一块(重启 = 新块首)
    assert [type(r) for r in parsed.blocks[0].records] == [V4Sample]  # 已落盘块不受重启影响
    z = parsed.blocks[1].records[0]
    assert isinstance(z, V4ZeroRun) and z.run_len == 3  # 重启后游程如期封口(t0+90..t0+150)
    assert parsed.blocks[1].start_epoch == int(clock.now) - 90  # 块首 = 游程首零样本(t0+90)


def test_zero_samples_do_not_touch_baselines_or_latest(tmp_path, monkeypatch):
    """零样本不动 baselines/latest(§3.4): 基线只在 r 采样点推进, 镜像冻结在最后活跃点"""
    clock = _Clock()
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    rec = _active_torrent("HASH123")
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
    clock = _Clock()
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30, flush_interval=60))
    mgr.store.server_state = _ss()
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
    mgr.store.server_state = _ss()  # 恢复传输(非 z 事件) -> 封口(内存照常)
    clock.advance(30)
    _run_sample(mgr, dry_run=True)
    assert GLOBAL_SERIES_KEY not in mod._open_runs
    assert not (tmp_path / "qb-traffic-v4").exists()


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
    clock = _Clock()
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
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
    parsed = _v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now)
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


def test_clock_rollback_clamped_dt_min_1(tmp_path, monkeypatch):
    """时钟回拨(§2.3): 单调钳制 dt_ms = max(1, 实测) —— 回拨行 dt_ms 恒 >= 1, 链不产负推进"""
    clock = _Clock()
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)  # t0
    clock.advance(30)
    _run_sample(mgr)  # t0+30(标称, 游标 t0+30)
    clock.now -= 10  # 回拨 10s: 实测 t0+20
    _run_sample(mgr)
    recs = mod._buffers[GLOBAL_SERIES_KEY].records
    assert recs[-1].dt_ms == 1  # max(1, round((t0+20 - (t0+30)) x 1000)) = 1
    _flush(mod)
    parsed = _v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now)
    assert parsed.blocks[0].records[-1].dt_ms == 1  # 落盘形态一致


# ---------- C1 热重载联动 + 跨天切块 + 缓冲闸 + stop 钩子(§3.4/§3.5) ----------
def test_interval_change_hot_reload_new_block_and_effective_interval(tmp_path, monkeypatch):
    """热重载改采样率即时生效(§3.5): 采样体现读 -> _effective_interval 更新 + 旧块落盘(旧
    interval) + 新块带新 interval —— 新旧数据分块各有 interval(A3 根因闭合)。
    !节拍表达已随 issue 26-10-16-0954 从「回写 task.interval」改为时钟线自持
    (_next_sample_at), 故断言 _effective_interval(节拍与块头共用同一单点)"""
    clock = _Clock()
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    mod = mgr.host.get("qb_traffic")
    mod.handle_traffic_sample(dry_run=False)  # t0: r 进缓冲(interval 30)
    clock.advance(30)
    mgr.config.qb_traffic.sample_interval = 10
    mod.handle_traffic_sample(dry_run=False)  # t0+30: 检测变化 -> 关旧块 + 记新节拍
    assert mod._effective_interval == 10  # A3: 现读生效
    assert mod._next_sample_at == clock.now + 10  # 下一到期点随新节拍推进
    parsed = _v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now)
    assert len(parsed.blocks) == 1 and parsed.blocks[0].interval_s == 30  # 旧块随关块落盘(旧 interval)
    assert [type(r) for r in parsed.blocks[0].records] == [V4Sample]
    clock.advance(10)
    mod.handle_traffic_sample(dry_run=False)  # t0+40: 新块(新 interval)
    _flush(mod)
    parsed = _v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now)
    assert len(parsed.blocks) == 2
    assert parsed.blocks[1].interval_s == 10 and parsed.blocks[1].start_epoch == int(clock.now) - 10
    # 变化轮自身记录落在新块首(关块先行于本轮采样), 下轮续写同块
    assert [type(r) for r in parsed.blocks[1].records] == [V4Sample, V4Sample]


def test_interval_mismatch_ceils_and_warns_once(tmp_path, monkeypatch):
    """运行期失配(D5): 向上取整到下一倍数(main_tick=2 配 3s -> 4s, _effective_interval=取整值)
    + 告警一次(防重复); 配置再变记忆复位; 不拒采"""
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=3))
    mgr.config.main_tick = 2.0  # FakeConfig 缺省 1.0; 显式置 2 构造失配场景
    mgr.store.server_state = _ss()
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
    clock = _Clock()
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=1.5))
    mgr.config.main_tick = 1.5  # FakeConfig 缺省 1.0; 显式对齐构造匹配小数档
    mgr.store.server_state = _ss()
    mod = mgr.host.get("qb_traffic")
    with capture_logs("auto_qb.core.modules.traffic_sample_mod") as cap:
        mod.handle_traffic_sample(dry_run=False)  # t0: 块首 r
    assert mod._effective_interval == 1.5
    assert "取整" not in cap.text  # 整数倍匹配: 失配告警不触发
    clock.advance(1.5)
    mod.handle_traffic_sample(dry_run=False)  # t0+1.5: 同块续写
    _flush(mod)
    parsed = _v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now)
    assert len(parsed.blocks) == 1 and parsed.blocks[0].interval_s == 1.5
    text = _v4_path(tmp_path, GLOBAL_SERIES_KEY, clock.now).read_text(encoding="utf-8")
    b_rows = [ln for ln in text.splitlines() if ln.startswith("B,")]
    assert len(b_rows) == 1 and b_rows[0].split(",")[2] == "1.5"  # B 行 interval 列如实带小数
    recs = parsed.blocks[0].records
    assert [type(r) for r in recs] == [V4Sample, V4Sample] and recs[1].dt_ms is None  # 零漂移


def _local_epoch(hour: int, minute: int, second: int) -> float:
    """今天本地 时:分:秒 的 epoch 秒(跨天切块用例的确定性本地时刻)"""
    return datetime.combine(datetime.now().date(), _time(hour, minute, second)).timestamp()


def test_day_boundary_cut(tmp_path, monkeypatch):
    """跨天切块(00:00 硬切, 本地时区, §3.3): 跨界记录使旧块落旧日期文件、新记录开新块落
    新日期文件 —— 23:59 块与 00:00 新块各带正确块头(interval 不变)"""
    clock = _Clock(now=_local_epoch(23, 59, 50))
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    mod = mgr.host.get("qb_traffic")
    t_before = clock.now
    _run_sample(mgr)  # 23:59:50: 块 A(今日)
    clock.advance(20)  # 00:00:10(次日): 跨界 -> 旧块落盘 + 新块
    _run_sample(mgr)
    _flush(mod)
    today = v4_epoch_date_str(t_before)
    p_today = _v4_path(tmp_path, GLOBAL_SERIES_KEY, t_before)
    p_tomorrow = _v4_path(tmp_path, GLOBAL_SERIES_KEY, clock.now)
    assert p_today.is_file() and p_tomorrow.is_file()
    d1 = parse_v4_day_text(p_today.read_text(encoding="utf-8"))
    d2 = parse_v4_day_text(p_tomorrow.read_text(encoding="utf-8"))
    assert len(d1.blocks) == 1 and d1.blocks[0].start_epoch == int(t_before)  # 23:59 块
    assert d1.blocks[0].interval_s == 30 and len(d1.blocks[0].records) == 1
    assert len(d2.blocks) == 1 and d2.blocks[0].start_epoch == int(clock.now)  # 00:00 新块
    assert d2.blocks[0].interval_s == 30 and len(d2.blocks[0].records) == 1


def test_day_boundary_seals_open_run(tmp_path, monkeypatch):
    """跨天封游程(块不跨天的必要触发): 00:00 样本先封旧日游程(记录入旧块), 本样本开新
    游程; 封口后换型记录跨天 -> 旧块落盘 + 单槽游程成为新块首(不写 dt, 无引导间隔)"""
    clock = _Clock(now=_local_epoch(23, 59, 20))
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    mod = mgr.host.get("qb_traffic")
    t_before = clock.now
    _run_sample(mgr)  # 23:59:20: 活跃 -> 块 A 首 r
    mgr.store.server_state = _idle_state()
    clock.advance(30)
    _run_sample(mgr)  # 23:59:50: 零样本 -> 开 z 游程
    clock.advance(20)  # 00:00:10(次日): 零样本 -> 先封旧游程(不跨天)再开新游程
    _run_sample(mgr)
    assert GLOBAL_SERIES_KEY in mod._open_runs  # 新游程已开
    mgr.store.server_state = _ss()
    clock.advance(30)  # 00:00:40: 再活跃 -> 封新游程(单槽) + 跨天切块
    _run_sample(mgr)
    _flush(mod)
    p_today = _v4_path(tmp_path, GLOBAL_SERIES_KEY, t_before)
    p_tomorrow = _v4_path(tmp_path, GLOBAL_SERIES_KEY, clock.now)
    d1 = parse_v4_day_text(p_today.read_text(encoding="utf-8"))
    d2 = parse_v4_day_text(p_tomorrow.read_text(encoding="utf-8"))
    assert [type(r) for r in d1.blocks[0].records] == [V4Sample, V4ZeroRun]  # 旧块: r + 跨天前封的 z
    assert d1.blocks[0].records[1].run_len == 1
    assert [type(r) for r in d2.blocks[0].records] == [V4ZeroRun, V4Sample]  # 新块首 = 单槽游程
    z2 = d2.blocks[0].records[0]
    assert z2.run_len == 1 and z2.dt_ms is None  # 块首单槽游程: dt 无消费者不写
    assert d2.blocks[0].start_epoch == int(clock.now) - 30  # B.start = 游程首槽(00:00:10)


def test_buffer_slot_cap_3600_early_flush(tmp_path, monkeypatch):
    """Q3 保险闸(§3.1): 单系列缓冲槽 >= 3600 提前单独 flush(防 ~60MB 滞留); 不关块,
    块头只写一次, 后续记录续写同块"""
    clock = _Clock()
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=1, flush_interval=10**9))
    mgr.store.server_state = _ss()
    mod = mgr.host.get("qb_traffic")
    for _ in range(V4_BUFFER_SLOT_CAP):  # 3600 轮活跃: 第 3600 槽触发提前 flush(驱动永不触发)
        clock.advance(1)
        mod.handle_traffic_sample(dry_run=False)
    parsed = _v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now)
    assert parsed is not None and len(parsed.blocks) == 1
    assert len(parsed.blocks[0].records) == V4_BUFFER_SLOT_CAP  # 恰在闸值落盘
    buf = mod._buffers[GLOBAL_SERIES_KEY]
    assert buf.records == [] and buf.start_epoch is None  # v4: 带 r 行的块随闸值 flush 关闭
    for _ in range(3):
        clock.advance(1)
        mod.handle_traffic_sample(dry_run=False)
    _flush(mod)
    parsed = _v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now)
    assert len(parsed.blocks) == 2 and len(parsed.blocks[1].records) == 3  # 新块续采(自带新块头)


def test_stop_flushes_all_and_seals_open_runs(tmp_path, monkeypatch):
    """stop() 钩子(§3.4): 封全部开放游程 + 全量 flush(优雅退出零丢失); 幂等(重复调用零副作用)"""
    clock = _Clock()
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30, flush_interval=10**9))
    mgr.store.server_state = _ss()
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)  # t0: 活跃 -> r 进缓冲
    mgr.store.server_state = _idle_state()
    clock.advance(30)
    _run_sample(mgr)  # t0+30: 开游程
    clock.advance(30)
    _run_sample(mgr)  # t0+60: 推进(未封口)
    mod.stop()
    assert GLOBAL_SERIES_KEY not in mod._open_runs  # 游程全封
    parsed = _v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now)
    recs = parsed.blocks[0].records
    assert [type(r) for r in recs] == [V4Sample, V4ZeroRun]  # 全量落盘
    assert recs[1].run_len == 2
    before = parsed.blocks[0].records
    mod.stop()  # 幂等: 缓冲游程已空, 零副作用
    assert _v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now).blocks[0].records == before


def test_zrun_end_anchor_tracked_reading_on_stop(tmp_path, monkeypatch):
    """形态 D 封口路径 ③(无样本在手 = stop()): 末端锚点 = 游程内最后一条零样本读数
    (全局系列每轮现读 totals, 跟踪字段随读刷新); 冻结列不变, 末端列落盘该读数"""
    clock = _Clock()
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30, flush_interval=10**9))
    mgr.store.server_state = _ss()
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)  # t0: 活跃 -> r 进缓冲
    for i in (1, 2, 3):  # 空闲三轮: alltime 逐轮增长(全局系列每轮现读 -> 跟踪字段刷新)
        mgr.store.server_state = _idle_state(alltime_dl=10_000_000 + i * 400, alltime_ul=20_000_000 + i * 200)
        clock.advance(30)
        _run_sample(mgr)
    mod.stop()
    parsed = _v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now)
    z = parsed.blocks[0].records[1]
    assert isinstance(z, V4ZeroRun) and z.run_len == 3
    assert (z.dl_total, z.up_total) == (10_000_400, 20_000_200)  # 冻结列 = 开启快照(首零样本对)
    assert (z.dl_total_end, z.up_total_end) == (10_001_200, 20_000_600)  # 末端列 = 最后零样本读数


def test_zrun_end_anchor_tracked_reading_on_interval_change(tmp_path, monkeypatch):
    """形态 D 封口路径 ④(采样间隔热重载关块): 关块前封开放游程, 末端锚点 = 跟踪的最后
    零样本读数; 旧块以旧 interval 落盘、新数据新块新 interval(A3 口径不变)"""
    clock = _Clock()
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
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
    parsed = _v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now)
    assert parsed.blocks[0].interval_s == 30
    z = parsed.blocks[0].records[1]
    assert isinstance(z, V4ZeroRun) and z.run_len == 2
    assert (z.dl_total, z.up_total) == (10_000_400, 20_000_200)  # 冻结列 = 开启快照
    assert (z.dl_total_end, z.up_total_end) == (10_000_800, 20_000_400)  # 末端列 = 最后零样本读数


def test_zrun_end_anchor_counter_reset_degrades_to_open(tmp_path, monkeypatch):
    """形态 D 游程内计数器重置(qB 重启): 末端实测低于开启快照 -> 末端锚点按开启快照退化
    (重置落差不是增长); z 行末端列 delta 非负、文件零坏行, 随后 r 照常触发重置关块"""
    clock = _Clock()
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    rec = _active_torrent("HASH123")
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
    parsed = _v4_read(tmp_path, key, clock.now)
    assert parsed.bad_lines == 0
    z = parsed.blocks[0].records[1]
    assert isinstance(z, V4ZeroRun)
    assert (z.dl_total_end, z.up_total_end) == (z.dl_total, z.up_total) == (5_000_500, 3_000_200)
    text = _v4_path(tmp_path, key, clock.now).read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("z,"):
            assert all(int(col) >= 0 for col in line.split(",")[2:6]), line


def test_stop_dry_run_short_circuit(tmp_path, monkeypatch):
    """stop() dry_run 短路: 不落盘不建目录(观测写盘属真实副作用)"""
    clock = _Clock()
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    mod = mgr.host.get("qb_traffic")
    mod.start(mgr.ctx, dry_run=True)
    _run_sample(mgr, dry_run=True)
    mod.stop()
    assert not (tmp_path / "qb-traffic-v4").exists()


def test_flush_oserror_discards_block_warns_once(tmp_path, monkeypatch):
    """落盘失败(OSError, §01.1): 不上抛、连续失败只告警一次; 失败块丢弃并复位块状态
    (dt 链卫生: 下次成功写起新块, 游标不错位)"""
    clock = _Clock()
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
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
    parsed = _v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now)
    assert len(parsed.blocks) == 1 and parsed.blocks[0].start_epoch == int(clock.now)
    assert len(parsed.blocks[0].records) == 1


def test_flush_all_drops_shell_buffers(tmp_path, monkeypatch):
    """内存卫生: 无开放块、无待写记录、无开放游程且本轮未采样的 shell 缓冲被清除
    (采样率变化关块后系列被删除的场景)"""
    clock = _Clock()
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    seed_store(mgr, [_active_torrent()])
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


# ---------- 聚合分层与恢复(S2b, plan 26-10-04-1957 §04) ----------
_AGG_H0 = (1_760_000_000 // HOUR_SECONDS) * HOUR_SECONDS  # hour 对齐的现代 epoch(Windows 无负 epoch)


def _agg_text(tmp_path, key: str):
    """读系列 agg.dat 文本(缺失 = None)"""
    p = v4_agg_file_path(str(tmp_path), key)
    return open(p, encoding="utf-8").read() if os.path.exists(p) else None


def _feed_30s(mod, key, t0, obs):
    """等间隔 30s 直灌: obs 依次在 t0, t0+30, ... 到达(首个为块首), 末记录信用由一次
    追加到达(复用 obs[0])结算 —— 产出 len(obs) 个 30s 区间, 全落 [t0, t0+30n)"""
    recs = [V4Sample(*o) for o in obs]
    mod._agg_feed(key, recs[0], t0, t0, True, 30.0)
    for i in range(1, len(recs)):
        mod._agg_feed(key, recs[i], t0 + 30 * (i - 1), t0 + 30 * i, False, 30.0)
    mod._agg_feed(key, recs[0], t0 + 30 * (len(recs) - 1), t0 + 30 * len(recs), False, 30.0)
    return recs


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
    clock = _Clock(now=_local_epoch(10, 0, 10))
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    mod = mgr.host.get("qb_traffic")
    h0 = int(clock.now) // HOUR_SECONDS * HOUR_SECONDS
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
    clock = _Clock(now=t1)
    monkeypatch.setattr(ts_mod, "time", clock)

    def _run(mgr, times):
        for t in times:
            clock.now = t
            mgr.store.server_state = _ss(
                alltime_dl=1_000_000 + t, alltime_ul=2_000_000 + t, dl_info_speed=100, up_info_speed=50
            )
            _run_sample(mgr)

    # 不停机序列: 3 样 + flush + 次日首样 + 末日 flush
    mgr_a = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mod_a = mgr_a.host.get("qb_traffic")
    _run(mgr_a, [t1, t2, t3])
    clock.now = flush1
    _flush(mod_a)
    _run(mgr_a, [t4])
    clock.now = flush_end
    _flush(mod_a)
    parsed_a = parse_v4_agg_text(_agg_text(tmp_path, GLOBAL_SERIES_KEY))
    assert len(parsed_a.hours) == 1 and len(parsed_a.days) == 1 and len(parsed_a.months) == 1

    # 停机序列: 同样 3 样 + flush 后崩溃(无 stop), 重启于次日 00:00:10
    tmp_b = tmp_path / "b"
    tmp_b.mkdir()
    mgr_b1 = _mgr_with_traffic(tmp_b, QbTraffic(enabled=True, sample_interval=30))
    mod_b1 = mgr_b1.host.get("qb_traffic")
    _run(mgr_b1, [t1, t2, t3])
    clock.now = flush1
    _flush(mod_b1)
    mgr_b2 = _mgr_with_traffic(tmp_b, QbTraffic(enabled=True, sample_interval=30))  # 重启: 全新模块实例
    mod_b2 = mgr_b2.host.get("qb_traffic")
    clock.now = t4
    mod_b2.start(mgr_b2.ctx, dry_run=False)  # 恢复 + catch-up(先于一切采样)
    recovered = parse_v4_agg_text(_agg_text(tmp_b, GLOBAL_SERIES_KEY))
    assert len(recovered.hours) == 1 and recovered.hours[0].cov_s == 60  # 补算行与在线封口一致
    _run(mgr_b2, [t4])
    clock.now = flush_end
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
    clock = _Clock(now=now)
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
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
    clock = _Clock(now=now)
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.host.get("qb_traffic").start(mgr.ctx, dry_run=False)
    parsed = parse_v4_agg_text(_agg_text(tmp_path, "global"))
    assert [h.dl_avg for h in parsed.hours] == [2] and [h.epoch for h in parsed.hours] == [h1]
    text1 = _agg_text(tmp_path, "global")
    assert "hour,not,a,valid,row" in text1  # 撕裂行跳过不崩溃(按坏行纪律留原样)
    assert len(parsed.days) == 1  # day 行由文件内 hour 行补出(catch-up: day <- agg 内 hour 行)
    mgr2 = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
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


def test_stop_seals_aggregates_and_dry_run_short_circuit(tmp_path, monkeypatch):
    """stop() 聚合封口(§3.4): 完结层级照常落 agg; 幂等; dry_run 短路(累计器内存照常
    推进, 零落盘)"""
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mod = mgr.host.get("qb_traffic")
    key = GLOBAL_SERIES_KEY
    base = _AGG_H0
    # 时钟钉在测试 hour 附近: stop() 封口用真实 time.time() 时, 该 hour 行已到龄会被
    # rollup_window 裁剪(C-01 修复后运行期新建系列裁剪生效, 数据降级进 day 行) —— 本用例
    # 验的是封口语义, 与裁剪无关, 故注入时钟
    monkeypatch.setattr(ts_mod, "time", _Clock(now=base + 2 * HOUR_SECONDS))
    obs = [(100, 50, 1, 2), (200, 60, 3, 4), (300, 70, 5, 6)]
    _feed_30s(mod, key, base, obs)
    mod.stop()  # 聚合封口: 完结 hour 落 agg(now 钉在 base+2h, 必然完结)
    parsed = parse_v4_agg_text(_agg_text(tmp_path, key))
    assert len(parsed.hours) == 1 and parsed.hours[0].cov_s == 90
    text = _agg_text(tmp_path, key)
    mod.stop()  # 幂等: 无新行
    assert _agg_text(tmp_path, key) == text
    # dry_run: stop() 短路, 零落盘; 累计器内存照常推进
    mgr2 = _mgr_with_traffic(tmp_path / "dry", QbTraffic(enabled=True, sample_interval=30))
    mod2 = mgr2.host.get("qb_traffic")
    mod2.start(mgr2.ctx, dry_run=True)
    mod2._agg_feed(key, V4Sample(100, 50, 1, 2), base, base, True, 30.0)
    mod2._agg_feed(key, V4Sample(200, 60, 3, 4), base + 30, base + 60, False, 30.0)
    assert mod2._agg_states[key].pending  # 内存累计器照常推进
    mod2.stop()
    assert not os.path.exists(v4_agg_file_path(str(tmp_path / "dry"), key))  # 零落盘


def _write_day_file(tmp_path, key: str, date_str: str) -> None:
    """手工放一个天文件(淘汰用例: 只需文件名日期, 内容最简)"""
    st = TrafficV4Store(str(tmp_path))
    path = st.series_day_path(key, date_str)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"{HEADER_LINE_V4}\nkey,{key}\n")


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


# ---------- S5 实测: 写 IO open/flush 计数(plan 26-10-04-1957 §09.1) ----------


def _dat_text(tmp_path, key: str, date: str):
    """读系列天文件文本"""
    return open(v4_day_file_path(str(tmp_path), key, date), encoding="utf-8").read()


def _drive_full_day(tmp_path, monkeypatch, sample_interval: int, day0: int):
    """全局系列模拟一整天采样流经采样模块 + store(假时钟), 返回 (模块, open 计数 dict)。

    flush_interval=600 -> 恰 144 个 flush 时点/天(86400/600), 24 个整点小时封口; 末次
    采样恰在午夜: 跨天硬切把当天最后一段落盘(第 144 次天文件 append), 次日首样本随
    flush 落次日文件(1 次)。计数只算追加写 open(mode 含 a 且非二进制), 尾字节查补的
    "rb" 读不计。"""
    t = {"now": day0}
    monkeypatch.setattr("auto_qb.core.modules.traffic_sample_mod.time.time", lambda: t["now"])
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=sample_interval, flush_interval=600))
    mgr.store.server_state = _ss(dl_info_speed=1024, up_info_speed=512)
    mod = mgr.host.get("qb_traffic")
    mod.start(mgr.ctx, dry_run=False)
    counts = {"day0": 0, "day1": 0, "agg": 0}
    day0_suffix = v4_epoch_date_str(day0) + ".dat"
    real_open = open

    def counting_open(file, mode="r", *a, **kw):
        m = mode or ""
        if "a" in m and "b" not in m:
            path = os.fspath(file)
            if path.endswith("agg.dat"):
                counts["agg"] += 1
            elif path.endswith(day0_suffix):
                counts["day0"] += 1
            elif path.endswith(".dat"):
                counts["day1"] += 1
        return real_open(file, mode, *a, **kw)

    monkeypatch.setattr("builtins.open", counting_open)
    for i in range(86400 // sample_interval + 1):  # 含午夜样本(t = day0+86400, 属次日)
        t["now"] = day0 + i * sample_interval
        mod.handle_traffic_sample(dry_run=False)
    return mod, counts


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


# ---------- v3 活尾快照发布(S6 验收追加, 2026-10-05) ----------


def test_live_tail_published_per_round_and_cleared_by_flush(tmp_path, monkeypatch):
    """(S6)活尾快照发布: 每轮 handler 末尾整体替换 live_tail —— 非零轮 = 未落盘 buffer
    记录(block_open/head_pending 如实)+ 开放游程冻结副本; flush 后 records 清空(磁盘接管);
    断连轮 n 游程入快照; 运行期关闭不发布(引用保持旧值, 端点由 feature 判定兜底)"""
    from auto_qb.core.traffic_store import LiveTail

    clock = _Clock()
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30, flush_interval=60))
    mod = mgr.host.get("qb_traffic")
    assert mod.live_tail == {}  # 初始空表
    # 首轮(非零): r 进缓冲未落盘 -> head_pending=True, records 恰为 buffer 内容
    mgr.store.server_state = _ss()
    _run_sample(mgr)
    tail = mod.live_tail.get(GLOBAL_SERIES_KEY)
    assert isinstance(tail, LiveTail) and tail.block_open and tail.head_pending
    assert tail.records == tuple(mod._buffers[GLOBAL_SERIES_KEY].records)
    assert tail.start_epoch == mod._buffers[GLOBAL_SERIES_KEY].start_epoch
    assert tail.open_run is None and tail.interval_s == 30
    # 次轮(零速): z 游程开启 -> 快照携冻结副本(records 不变, 游程随样本推进)
    mgr.store.server_state = _ss(dl_info_speed=0, up_info_speed=0)
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
    mgr.store.server_state = _ss(dl_info_speed=0, up_info_speed=0)
    _run_sample(mgr)
    tail = mod.live_tail[GLOBAL_SERIES_KEY]
    assert tail.records == () and mod._buffers[GLOBAL_SERIES_KEY].records == []
    assert _v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now) is not None
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
    rows = _pending_agg_rows(mod._agg_states[key], now)
    hours = [r for r in rows if r.kind == "hour"]
    assert hours == [AggRow("hour", h0, 149, 200, 55, 60, 2000, 3000, 3600)]  # dt 加权 + 级末快照
    day = [r for r in rows if r.kind == "day"]
    assert day == [AggRow("day", v4_day_epoch(h0), 149, 200, 55, 60, 2000, 3000, 3600)]  # 开放日 = 当日 pending
    month = [r for r in rows if r.kind == "month"]
    assert month == [AggRow("month", v4_month_epoch(h0), 149, 200, 55, 60, 2000, 3000, 3600)]  # 开放月逐级
    # 小时封口: hour 部分行消失(磁盘接管), 开放日部分行仍在(日未封)
    assert mod._agg_flush_series(key, now=now) is True
    rows = _pending_agg_rows(mod._agg_states[key], now)
    assert [r for r in rows if r.kind == "hour"] == []
    assert [r for r in rows if r.kind == "day"] == day  # 日累计器持已封 hour 行, 部分行照发
    # 无累计器/空 pending: 不出行
    assert _pending_agg_rows(SeriesAgg(), h0) == ()
    # 跨日残余: 前一日的 pending 小时不进当日 day 部分行(hour 部分行照发, 读侧与磁盘行合流)
    agg2 = SeriesAgg()
    prev_h = v4_day_epoch(h0) - HOUR_SECONDS
    agg2.pending[prev_h] = [V4HourSample(100, 50, 1000, 2000, 1800.0)]
    agg2.day_epoch = v4_day_epoch(h0)
    rows2 = _pending_agg_rows(agg2, h0 + 1800)
    assert [r.epoch for r in rows2 if r.kind == "hour"] == [prev_h]
    assert [r for r in rows2 if r.kind == "day"] == []  # 当日无 pending 无已封小时 -> 不出日行

    # 端到端发布面: handler 两轮后 pending_agg 非空; flush 清空 records 后系列仍在快照里
    clock = _Clock(h0 + 1800)
    monkeypatch.setattr(ts_mod, "time", clock)
    pub = tmp_path / "pub"
    pub.mkdir()
    mgr2 = _mgr_with_traffic(pub, QbTraffic(enabled=True, sample_interval=30, flush_interval=600))
    mgr2.store.server_state = _ss(dl_info_speed=100, up_info_speed=50, alltime_dl=1000, alltime_ul=2000)
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


# ---------- v4 定约用例(plan 26-10-05-2200 §04 表 ③⑤⑥⑦, B2 落地) ----------
def test_v4_counter_reset_forces_block_reopen(tmp_path, monkeypatch):
    """③ 计数器重置强制关块(v4 §01 关块状态机): 重置(cur < 块内最近 totals)后块内负
    delta 不出现, 新块基线 = 重置后 totals(首记录 delta = 0); 旧块以重置前观测收尾"""
    clock = _Clock()
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30, flush_interval=10**9))
    mgr.store.server_state = _ss(alltime_dl=1000, alltime_ul=500, dl_info_speed=100, up_info_speed=50)
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)  # t0: r(totals 1000/500, 块 A 首立基线)
    clock.advance(30)
    mgr.store.server_state = _ss(alltime_dl=1600, alltime_ul=900, dl_info_speed=100, up_info_speed=50)
    _run_sample(mgr)  # t0+30: r(totals 1600/900)
    clock.advance(30)
    mgr.store.server_state = _ss(alltime_dl=800, alltime_ul=900, dl_info_speed=100, up_info_speed=50)
    _run_sample(mgr)  # t0+60: dl 回落(qB 重置) -> 强制关块重开, 新块基线 = (800, 900)
    clock.advance(30)
    mgr.store.server_state = _ss(alltime_dl=1200, alltime_ul=1300, dl_info_speed=100, up_info_speed=50)
    _run_sample(mgr)  # t0+90: 新块内正常增量
    _flush(mod)
    parsed = _v4_read(tmp_path, GLOBAL_SERIES_KEY, clock.now)
    assert parsed.bad_lines == 0 and len(parsed.blocks) == 2  # 重置点拆两块
    b1, b2 = parsed.blocks
    assert (b1.dl_base, b1.up_base) == (1000, 500)
    assert [(r.dl_total, r.up_total) for r in b1.records] == [(1000, 500), (1600, 900)]
    assert (b2.dl_base, b2.up_base) == (800, 900)  # 新块基线 = 重置后 totals
    assert [(r.dl_total, r.up_total) for r in b2.records] == [(800, 900), (1200, 1300)]
    # 块内负 delta 不出现: 全部 r 行 delta 列非负(解析零坏行 + 文本逐行核对双保险)
    text = _v4_path(tmp_path, GLOBAL_SERIES_KEY, clock.now).read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("r,"):
            assert all(int(col) >= 0 for col in line.split(",")[3:5]), line


def test_v4_cross_block_settlement_online_offline_same_source(tmp_path):
    """⑤ 跨块覆盖结算两路同源(v4 §01「覆盖结算」): 在线 _agg_feed 与离线
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


def test_v4_idle_block_stays_open_single_b_row_and_live_tail_identity(tmp_path, monkeypatch):
    """⑥ 空闲块不关(v4 §04 用例 ⑥): 纯空闲系列(数据门有数据 + 零速)跨 flush 时点
    主文件零写入, 封口后天文件恰 1 条 B 行 + 1 条长 z 行; 跨 flush 开放 z 游程的
    LiveTail 复原与落盘重算恒等(块首封口形态); 恢复传输后 r 行 delta <= flush 窗 x 速率"""
    clock = _Clock()
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30, flush_interval=600))
    mgr.store.server_state = _ss(dl_info_speed=1024, up_info_speed=512)  # 全局保持活跃(隔离单种面)
    seed_store(mgr, [_active_torrent("HASH123")])
    st = TrafficV4Store(str(tmp_path))  # 数据门: 预置系列目录含 .dat(有过历史数据)
    day = v4_epoch_date_str(clock.now)
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
    tpath = _v4_path(tmp_path, "torrent:HASH123", clock.now)
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
    clock = _Clock(now=_local_epoch(23, 57, 40))
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30, flush_interval=10**9))
    mgr.store.server_state = _ss()
    mod = mgr.host.get("qb_traffic")
    t_before = clock.now
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
    mgr.store.server_state = _ss(alltime_dl=10_000_200, alltime_ul=20_000_100)  # 次日恢复传输
    clock.advance(30)  # 00:01:20: 封新 z 游程(2 槽)+ r
    _run_sample(mgr)
    _flush(mod)
    d2 = parse_v4_day_text(_v4_path(tmp_path, GLOBAL_SERIES_KEY, clock.now).read_text(encoding="utf-8"))
    assert len(d2.blocks) == 1
    z2 = d2.blocks[0].records[0]
    assert isinstance(z2, V4ZeroRun) and z2.run_len == 2
    assert v4_block_slots(d2.blocks[0])[:2] == tuple(tail_slots[-2:])  # 跨天接力: 活尾复原 == 落盘重算


def test_v4_crash_restart_idle_window_is_vacuum(tmp_path, monkeypatch):
    """⑦ 崩溃重启该时段 = 真空(v4 §04 用例 ⑦): 开放 z 游程是空闲期唯一副本, 崩溃即丢
    「在场证明」—— 重启 catch-up 后空闲段 cov_s 缺失, hour 行 avg 不被零速稀释(无偏)"""
    base_t = _local_epoch(10, 0, 0)
    clock = _Clock(now=base_t)
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr1 = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr1.store.server_state = _ss()
    mod1 = mgr1.host.get("qb_traffic")
    _run_sample(mgr1)  # 10:00:00: 活跃 r(rate 1024/2048)
    _flush(mod1)  # 块落盘(hour 未完结)
    mgr1.store.server_state = _idle_state()
    for _ in range(20):  # 10:00:30..10:10:30: 空闲(开放 z 游程滞留内存 = 唯一副本)
        clock.advance(30)
        _run_sample(mgr1)
    # 崩溃: 无 stop(), 模块实例直接丢弃(开放游程与内存信用随之消失)
    mgr2 = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mod2 = mgr2.host.get("qb_traffic")
    clock.advance(30)  # 10:10:30
    mod2.start(mgr2.ctx, dry_run=False)  # 重启恢复: catch-up 从天文件 raw 补算(空闲段无 raw)
    mgr2.store.server_state = _ss()
    _run_sample(mgr2)  # 10:10:30: 活跃 r —— 块首 gap 630s 超容差 -> 空闲段真空不结算
    clock.now = _local_epoch(11, 0, 10)  # 跨到下一小时首样
    mgr2.store.server_state = _ss(alltime_dl=10_100_000, alltime_ul=20_100_000)
    _run_sample(mgr2)  # 11:00:10: 结算 [10:10:30, 11:00:10)(10:00 桶内 2970s)
    _flush(mod2)
    parsed = parse_v4_agg_text(_agg_text(tmp_path, GLOBAL_SERIES_KEY))
    hour_epoch = (int(base_t) // HOUR_SECONDS) * HOUR_SECONDS
    assert len(parsed.hours) == 1 and parsed.hours[0].epoch == hour_epoch
    assert parsed.hours[0].cov_s == 2970  # 空闲段(10:00:30..10:10:00)真空缺失, 不虚记覆盖
    assert parsed.hours[0].dl_avg == 1024  # avg 无偏: 只按有效覆盖加权, 不被零速/缺覆盖稀释


# ---------- 启动恢复按需读集(plan 26-10-12-2010, D1/D4/D5) ----------
def test_recovery_read_set_bounded_to_watermark_day(tmp_path, monkeypatch):
    """恢复读集按需(D1 验收): 24 系列 x 30 天天文件 + 水位在昨日的 agg -> start() 后逐系列
    只读 [水位日, 今日] 至多 2 个天文件(recovery_reads 计数属性机检, 不随
    rollup_window=1000000D 放大), agg.dat 按系列照读(D4); 水位封口小时不重算, 补算只
    覆盖水位之后小时; 二次重启零追加(水位推进后读集缩到当日)"""
    window = 1000000 * 86400.0  # 生产口径: 永久保留(恢复读集必须与它解耦, D2 不动)
    now = _local_epoch(13, 0, 30)  # 今日 13:00:30(本地)
    clock = _Clock(now=now)
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30, rollup_window=window))
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
    mgr2 = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30, rollup_window=window))
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
    clock = _Clock(now=now)
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30, rollup_window=window))
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
    clock = _Clock(now=now)
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
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


def _v4_open_paths(monkeypatch):
    """open 计数探针(读侧契约逐档机检 §3.2): 记录 qb-traffic-v4/ 下打开路径(正斜杠归一;
    limits/ 目录属注解面单列, 不算系列数据面); 用完由 monkeypatch 自动收"""
    import builtins

    opened = []
    real_open = builtins.open

    def counting_open(file, *a, **k):
        p = os.fspath(file).replace("\\", "/")
        if "qb-traffic-v4/" in p:
            opened.append(p)
        return real_open(file, *a, **k)

    monkeypatch.setattr(builtins, "open", counting_open)
    return opened


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
    monkeypatch.setattr("auto_qb.webui.server.traffic_qb.time", SimpleNamespace(time=lambda: frozen))
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


# ---------- P1-T1.2 守卫与容错簇(计划 26-10-20-2101) ----------


def test_pending_agg_rows_skips_empty_and_zero_coverage_buckets(tmp_path):
    """活尾 pending 行(S7): 空桶不留行 / 零有效覆盖桶 ValueError 逐一跳过(不出行 = null
    语义, 与 _agg_flush_series 同); 无子行时 day/month 两级同样不出行; 合法桶照常产
    hour 行并由它逐级上卷"""
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mod = mgr.host.get("qb_traffic")
    agg = mod._agg_state(GLOBAL_SERIES_KEY)
    agg.pending[_AGG_H0] = []  # 空桶(全 null 覆盖的小时)
    agg.pending[_AGG_H0 + HOUR_SECONDS] = [V4HourSample(100, 50, 1, 2, 0.0)]  # 零有效覆盖
    assert ts_mod._pending_agg_rows(agg, now=_AGG_H0 + 2 * HOUR_SECONDS) == ()
    # 对照: 合法桶照常产 hour 行, day/month 两级由它上卷(无子行时两级不出行)
    agg.pending[_AGG_H0 + 2 * HOUR_SECONDS] = [V4HourSample(100, 50, 1, 2, 1800.0)]
    rows = ts_mod._pending_agg_rows(agg, now=_AGG_H0 + 3 * HOUR_SECONDS)
    assert [r.kind for r in rows] == ["hour", "day", "month"]
    assert rows[0].cov_s == 1800 and rows[1].epoch == v4_day_epoch(_AGG_H0)


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
    clock = _Clock()
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    seed_store(mgr, [_active_torrent("HASH123", uploaded=None)])
    mod = mgr.host.get("qb_traffic")
    key = "torrent:HASH123"
    with capture_logs("auto_qb.core.modules.traffic_sample_mod") as cap:
        _run_sample(mgr)
    run = mod._open_runs[key]
    assert run.kind == "n" and run.samples == 1
    assert "按 n 游程槽处理" in cap.text
    assert key not in mod._buffers  # null 点不产记录(绝不用 0 充数)


class _FlipSpeedTorrent:
    """dlspeed 首读 0(过零样本过滤)之后返回 512 —— 复现活跃过滤与字段读数口径漂移"""

    hash = "HASH123"
    upspeed = 0
    downloaded = 5_000_000
    uploaded = 3_000_000
    downloaded_session = 500_000
    uploaded_session = 300_000

    def __init__(self) -> None:
        self._reads = 0

    @property
    def dlspeed(self) -> int:
        self._reads += 1
        return 0 if self._reads == 1 else 512


def test_torrent_zero_speed_readings_drift_defensive_raw_row(tmp_path, monkeypatch):
    """零速过滤与字段读数口径漂移的防御支: 过滤判零但读数非零 -> 按 r 记录处理(绝不把活跃
    读数吞进游程, 否则该段速率永久丢失)"""
    clock = _Clock()
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    seed_store(mgr, [_FlipSpeedTorrent()])
    mod = mgr.host.get("qb_traffic")
    key = "torrent:HASH123"
    mod._has_data.add(key)  # 数据门放行(本用例不落盘造目录)
    _run_sample(mgr)
    assert key not in mod._open_runs  # 不误开游程
    recs = mod._buffers[key].records
    assert [type(r) for r in recs] == [V4Sample] and recs[0].dl_rate == 512


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
    clock = _Clock()
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = {}  # 关键字段缺失 -> null 点
    mod = mgr.host.get("qb_traffic")
    key = GLOBAL_SERIES_KEY
    _run_sample(mgr)
    clock.advance(30)
    _run_sample(mgr)
    assert mod._open_runs[key].kind == "n" and mod._open_runs[key].samples == 2
    mgr.store.server_state = _ss()
    clock.advance(30)
    _run_sample(mgr)  # 恢复传输: n 游程封口成块首(无基线), r 到达即拆块
    _flush(mod)
    parsed = _v4_read(tmp_path, key, clock.now)
    assert parsed is not None and parsed.bad_lines == 0
    assert len(parsed.blocks) == 2
    assert parsed.blocks[0].dl_base is None and [type(r) for r in parsed.blocks[0].records] == [V4NullRun]
    assert parsed.blocks[1].dl_base is not None and [type(r) for r in parsed.blocks[1].records] == [V4Sample]
    text = _v4_path(tmp_path, key, clock.now).read_text(encoding="utf-8")
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


def _build_tail_fixture(root, now):
    """构造跨天两文件 + 水位 agg: 昨日 23:59:20 块(2 槽)与今日 00:00:10 块(2 槽), 首尾
    间隔 20s < interval 30s -> 跨文件连续(可结算 [23:59:50, 00:00:10))"""
    today0 = v4_date_str_epoch(v4_epoch_date_str(now))
    y0 = v4_date_str_epoch(v4_epoch_date_str(now - 86400))
    y_date, t_date = v4_epoch_date_str(y0), v4_epoch_date_str(today0)
    st = TrafficV4Store(str(root))
    st.append_agg_rows(GLOBAL_SERIES_KEY, (AggRow("hour", y0 + 22 * HOUR_SECONDS, 7, 9, 3, 4, 500, 600, 3600), ))
    st.append_records(
        GLOBAL_SERIES_KEY,
        y_date,
        (y0 + 23 * HOUR_SECONDS + 59 * 60 + 20, 30),
        (V4Sample(100, 50, 1000, 2000), V4Sample(200, 60, 2000, 3000)),
        (1000, 2000),
    )
    st.append_records(
        GLOBAL_SERIES_KEY,
        t_date,
        (today0 + 10, 30),
        (V4Sample(10, 5, 100, 200), V4Sample(20, 6, 200, 300)),
        (100, 200),
    )
    return y_date


def test_recovery_missing_day_file_breaks_tail_context(tmp_path, monkeypatch):
    """恢复跨天末槽上下文接力: 读集内文件在场 -> [昨日末槽, 今日首槽) 连续段结算进覆盖
    (23 点成行); 文件缺失(竞态/手工清理)-> 上下文断链, 该段按真空处理(23 点无观测不出行),
    今日开放小时照常重建 pending 桶"""
    now = _local_epoch(0, 30, 30)
    monkeypatch.setattr(ts_mod, "time", _Clock(now=now))
    conf = QbTraffic(enabled=True, sample_interval=30, rollup_window=3 * 86400.0)
    ctl, drop = tmp_path / "ctl", tmp_path / "drop"
    os.makedirs(ctl)
    os.makedirs(drop)
    y_date = _build_tail_fixture(ctl, now)
    _build_tail_fixture(drop, now)
    mgr = _mgr_with_traffic(ctl, conf)
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
    mgr2 = _mgr_with_traffic(drop, conf)
    mod2 = mgr2.host.get("qb_traffic")
    mod2.start(mgr2.ctx, dry_run=False)
    assert mod2.recovery_stats["slots"] == 2  # 只有今日文件贡献槽
    assert mod2.recovery_stats["hours"] == 0  # 23 点无观测: 不虚记覆盖
    assert v4_date_str_epoch(v4_epoch_date_str(now)) in mod2._agg_state(GLOBAL_SERIES_KEY).pending


def test_recovery_open_hour_rebuilds_pending_bucket(tmp_path, monkeypatch):
    """catch-up 遇未完结小时 -> 重建 pending 桶(不产 hour 行, 等封口); 空桶跳过(防御:
    桶存在但无样本时不留行)"""
    now = _local_epoch(13, 0, 30)
    monkeypatch.setattr(ts_mod, "time", _Clock(now=now))
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30, rollup_window=3 * 86400.0))
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
