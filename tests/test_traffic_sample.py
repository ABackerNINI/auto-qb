"""test_traffic_sample 测试计划: qB 口径流量采样器(plan 26-10-03-0946 方案C P1 采样器核心 + §06 配置键 + plan 26-10-04-1957 S2a 写侧翻转 v3)

## 测试计划(每个测试函数一条)
- test_qb_traffic_config_absent_means_disabled: 键组缺省 -> config.qb_traffic 为 None(未启用)
- test_qb_traffic_config_parses_sample: 完整样例解析(enabled/四个时间键换算成秒, 含 v3 flush_interval)
- test_qb_traffic_config_partial_falls_back_to_defaults: 部分键缺省回退 QbTraffic 默认值
- test_qb_traffic_config_rejects_bad_section: 段非 dict / 未知键 / enabled 非布尔
- test_qb_traffic_config_bounds_matrix: 各时间/布尔键边界矩阵(1.5S 需 main_tick 配合 / 60S~1H / 1H~90D / 7D~无上限 恰好压线收, 压线外拒)
- test_qb_traffic_sample_interval_below_main_tick_rejected: v3 下限硬校验(26-10-04-1957 §06.1) ——
  sample_interval < main_tick 加载期拒(1.5s 档在 main_tick=2s 下被拒), 恰等于压线收
- test_qb_traffic_sample_interval_multiple_mismatch_not_an_error: 裁决 D5 —— 非 main_tick 整数倍校验层不报错
- test_qb_traffic_flush_interval_bounds: v3 新键 flush_interval —— dataclass 缺省 600 /
  60~3600s 整数秒压线收 / 越界与非整数秒与坏格式聚合报错
- test_sample_task_registered_when_enabled: enabled=true -> start 创建 qb_traffic_sample 全局任务(interval=采样间隔)
- test_sample_task_not_registered_when_disabled: enabled=false 与键组缺省(None)两种情形均不建任务
- test_sample_task_reregisters_on_queue_rebuilt: L2 队列重建 -> 按新配置重入队(换 interval/启用/停用三向)
- test_sampling_runs_on_caller_thread: 采样在调用 run_due 的线程(主循环线程)内同步执行, 模块不建线程(单写线程不变式)
- test_first_sample_only_establishes_baseline: 首个采样只立基线不出增量(首窗 null), 次轮出正常增量
- test_counter_rollback_records_reset_no_negative: 模拟 qB 重启(计数器回落) -> 不产负增量、增量记 null、基线更新为 cur、INFO 记重置
- test_disconnect_produces_null_point: qB 断连(store.client None) -> 全局 n 游程槽 + latest 镜像 null 点、单种本轮不采样、基线不动
- test_missing_fields_produce_null_point_not_zero: server_state 关键字段缺失/空值 -> null 处理(不写 0)且基线不推进
- test_torrent_active_filter_zero_rows_when_idle: 活跃种子照常产 r; 空闲种子零 r(v3: 零样本按游程纪律压缩, 从未传输者无游程)
- test_disabled_at_runtime_handler_noop: 任务已注册后运行期关闭 -> handler 短路不采样(任务保留)
- test_enabled_false_creates_zero_files_or_dirs: enabled=false/键组缺省 -> start+采样全程零文件零目录(保守默认验收)
- test_enabled_true_persists_under_data_dir: enabled=true -> v3 天文件 <data_dir>/qb-traffic-v3/<系列>/<date>.dat
  (头行 v3 + key 行 + B 块头 + r 行 5 列零 dt); 会话快照不落盘
- test_module_contract: name/sections 声明正确且被装配清单认领
- test_flush_driver_interval_and_deferred_first_round: flush 驱动(§3.3) —— 进程首轮只记时不提前 flush;
  now-last_flush >= flush_interval 才批量落盘; 缓冲清空后块状态延续(块头只写一次)
- test_global_idle_run_seals_on_time_r1: 触发 (3): 全局空闲 600s 封口成 buffer 记录(v3 不单独落盘);
  flush 后 z 行 run_len/totals 正确且零 dt(标称跨度); 封口移除游程, 下个零样本开新游程
- test_torrent_idle_run_snapshot_fixed_at_open: 单种动过->停: z 记录 totals 快照固定在开启时刻
  (两个不同 totals 的零样本不刷新)
- test_never_transferred_torrent_zero_files_runs_entries: 从未传输种子: 零文件零游程(目录判定门 + 缓存)
- test_nonzero_arrival_seals_z_before_raw_same_round: 触发 (1): 非零到达同轮先 z 后 r(buffer 记录序 = 文件序 = 时间序)
- test_disconnect_seals_run_before_null_r2: 触发 (2)(R2): null 到达先封 z 再记 n —— z 覆盖不横跨断连期
- test_cap_samples_seals_before_time_flush: 触发 (4): 120 样本上限封口(interval 1s 场景先于 600s, span < ZRUN_FLUSH_S)
- test_zero_run_requires_valid_totals_snapshot: 开 z 游程需 totals 快照: 缺失不开新游程; 已开游程只推进无需重读
- test_global_always_opens_run_vs_torrent_gated: 全局零样本恒开游程(无门) vs 单种数据门拦截(对照)
- test_restart_loses_at_most_one_open_run: 重建 sampler 实例(重启)丢开放游程 <=1(纯零信息), 已落盘块不受影响,
  零样本按纪律重新开游程(重启后首个封口游程成为新块首)
- test_zero_samples_do_not_touch_baselines_or_latest: 零样本不动 baselines/latest(镜像冻结在最后活跃点)
- test_dry_run_no_disk_but_memory_runs_advance: dry_run 零落盘; 缓冲游程内存照常推进, flush 静默跳过写
- test_dt_drift_boundary_family: tol 边界族(§2.3 判据=累积漂移) —— 压线行(恰 250ms)不写 dt / 超线行写实测 dt 并
  自然复位 / 稳态小漂移(150ms/行)退化周期写 / 空载(等间隔)零 dt 行; roundtrip 游标推算与实测一致
- test_clock_rollback_clamped_dt_min_1: 时钟回拨单调钳制 dt_ms = max(1, 实测) >= 1
- test_interval_change_hot_reload_new_block_and_task_interval: 热重载改采样率即时生效(§3.5):
  task.interval 回写 + 旧块落盘(旧 interval) + 新块带新 interval(新旧数据分块各有 interval)
- test_interval_mismatch_ceils_and_warns_once: 运行期失配(D5): 向上取整到下一倍数(task.interval=取整值) +
  告警一次(防重复), 配置再变记忆复位; 不拒采
- test_day_boundary_cut: 跨天切块(00:00 硬切, §3.3): 23:59 块落旧日期文件 + 00:00 新块新日期文件, 各带正确块头
- test_day_boundary_seals_open_run: 跨天封游程: 游程不跨天(00:00 样本先封旧游程); 块首单槽游程不写 dt
- test_buffer_slot_cap_3600_early_flush: Q3 保险闸: 缓冲槽 >= 3600 提前单独 flush(不关块, 块头只写一次)
- test_stop_flushes_all_and_seals_open_runs: stop() 钩子(§3.4): 封全部开放游程 + 全量 flush; 幂等
- test_stop_dry_run_short_circuit: stop() dry_run 短路零落盘
- test_flush_oserror_discards_block_warns_once: 落盘失败(OSError)不上抛、连续失败只告警一次;
  失败块丢弃并复位块状态(dt 链卫生: 下次成功写起新块)
- test_flush_all_drops_shell_buffers: 内存卫生: 无开放块无待写记录无游程且未采样的 shell 缓冲被清除

时钟/落盘纪律: 需要确定时刻的用例经 monkeypatch 固定模块 time 引用(_Clock 逐轮推进); flush 时点
除专项驱动用例外用 mod._flush_all_series() 直调(绕开驱动计时, 驱动时序由专项用例钉住)。
"""
import io
import logging
import threading
from datetime import datetime, time as _time

import yaml

from auto_qb.config import QbTraffic, load_config
from auto_qb.config.validation import validate_config
from auto_qb.core.modules import traffic_sample_mod as ts_mod
from auto_qb.core.modules.traffic_sample_mod import (
    GLOBAL_SERIES_KEY,
    TASK_NAME,
    V3_BUFFER_SLOT_CAP,
    ZRUN_CAP_SAMPLES,
    ZRUN_FLUSH_S,
    TrafficSampleModule,
)
from auto_qb.core.taskqueue import Task, TaskQueue
from auto_qb.core.traffic_store import (
    V3NullRun,
    V3Sample,
    V3ZeroRun,
    parse_v3_day_text,
    v3_block_slots,
    v3_day_file_path,
    v3_epoch_date_str,
)
from helpers import FakeClient, FakeTorrent, make_manager, seed_store


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


def _run_sample(mgr, dry_run: bool = False, task: Task = None) -> bool:
    """直调采样 handler(与 test_speed_curve._run_curve 同款, 不经队列); 可传 task 断言回写"""
    mod = mgr.host.get("qb_traffic")
    task = task or Task("internal", TASK_NAME, interval=30, handler=mod.handle_traffic_sample)
    return mod.handle_traffic_sample(task, dry_run=dry_run)


def _flush(mod) -> None:
    """强制全系列批量 flush(绕开驱动计时; 驱动时序由专项用例钉住)"""
    mod._flush_all_series()


def _v3_path(tmp_path, key: str, ts: float):
    """系列键 + 时刻 -> 当天 v3 天文件路径(Path)"""
    from pathlib import Path

    return Path(v3_day_file_path(str(tmp_path), key, v3_epoch_date_str(ts)))


def _v3_read(tmp_path, key: str, ts: float):
    """读系列当天 v3 天文件并解析(不存在返回 None)"""
    p = _v3_path(tmp_path, key, ts)
    return parse_v3_day_text(p.read_text(encoding="utf-8")) if p.exists() else None


def _v3_series_dir(tmp_path, infohash: str):
    return tmp_path / "qb-traffic-v3" / "torrents" / infohash


class _ModuleLogCapture:
    """捕获 qb_traffic 模块 logger(QbManager 构造清空 root handlers, caplog 失效 —— 惯例见 test_speed_curve)"""
    def __init__(self, level=logging.DEBUG):
        self._level = level
        self.buf = io.StringIO()

    def __enter__(self):
        self._lg = logging.getLogger("auto_qb.core.modules.traffic_sample_mod")
        self._handler = logging.StreamHandler(self.buf)
        self._handler.setLevel(self._level)
        self._old_level = self._lg.level
        self._lg.setLevel(self._level)
        self._lg.addHandler(self._handler)
        return self

    def __exit__(self, *exc):
        self._lg.removeHandler(self._handler)
        self._lg.setLevel(self._old_level)
        return False

    @property
    def text(self) -> str:
        return self.buf.getvalue()


# ---------- 配置键全链(§06) ----------
def _cfg_dict(qb_traffic_spec, main_tick=None) -> dict:
    """配置 dict 样例; main_tick 可选(v3 下限语义: sample_interval >= main_tick 硬校验要现取它)"""
    top = {
        "qbittorrent": {
            "host": "127.0.0.1",
            "port": 8080,
            "username": "u",
            "password": "p"
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
                            "password": "p"
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


# ---------- 任务注册(P1 验收: enabled=false 不注册任务) ----------
def test_sample_task_registered_when_enabled(tmp_path):
    """enabled=true -> start 创建 qb_traffic_sample 全局任务, interval = 采样间隔"""
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=45))
    mgr.host.get("qb_traffic").start(mgr.ctx, dry_run=False)
    tasks = [t for t in mgr.task_queue._fast if t.name == TASK_NAME]
    assert len(tasks) == 1
    assert tasks[0].kind == "internal" and tasks[0].interval == 45
    # 黄金法则 1: 重复 start 幂等(has_named), 不重复入队
    mgr.host.get("qb_traffic").start(mgr.ctx, dry_run=False)
    assert len([t for t in mgr.task_queue._fast if t.name == TASK_NAME]) == 1


def test_sample_task_not_registered_when_disabled(tmp_path):
    """enabled=false 与键组缺省(None)两种情形 -> start 均不建任务(零开销)"""
    for qb in (QbTraffic(enabled=False), None):
        mgr = _mgr_with_traffic(tmp_path, qb)
        mgr.host.get("qb_traffic").start(mgr.ctx, dry_run=False)
        assert all(t.name != TASK_NAME for t in mgr.task_queue._fast), qb


def test_sample_task_reregisters_on_queue_rebuilt(tmp_path):
    """L2 队列整体重建 -> queue_rebuilt 相位按新配置重入队: 换 interval / 停用 / 启用三向"""
    # 已启用 -> 重建后 interval 取新值(新任务对象)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mod = mgr.host.get("qb_traffic")
    mod.start(mgr.ctx, dry_run=False)
    old = next(t for t in mgr.task_queue._fast if t.name == TASK_NAME)
    mgr.config.qb_traffic.sample_interval = 60
    mgr.task_queue = TaskQueue()  # 模拟 L2: 队列整体替换(setter 落回 ctx)
    mgr.events.emit("queue_rebuilt")
    tasks = [t for t in mgr.task_queue._fast if t.name == TASK_NAME]
    assert len(tasks) == 1 and tasks[0].interval == 60 and tasks[0] is not old
    # 停用 -> 重建后不回到新队列
    mgr.config.qb_traffic.enabled = False
    mgr.task_queue = TaskQueue()
    mgr.events.emit("queue_rebuilt")
    assert all(t.name != TASK_NAME for t in mgr.task_queue._fast)
    # 未启用 -> 重建后起任务(热重载改 enabled=true 后经相位自然启用, plan §03.1)
    mgr2 = _mgr_with_traffic(tmp_path, None)
    mgr2.config.qb_traffic = QbTraffic(enabled=True, sample_interval=30)
    mgr2.task_queue = TaskQueue()
    mgr2.events.emit("queue_rebuilt")
    assert [t.name for t in mgr2.task_queue._fast] == [TASK_NAME]


# ---------- 采样语义(P1 验收判据) ----------
def test_sampling_runs_on_caller_thread(tmp_path, monkeypatch):
    """单写线程不变式: 采样在调用 run_due 的线程(= 主循环线程)内同步完成, 模块不创建线程"""
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    mod = mgr.host.get("qb_traffic")
    mod.start(mgr.ctx, dry_run=False)  # 新任务立即到期
    seen = {}
    orig = TrafficSampleModule.sample_series

    def spy(self, key, ts, *readings):
        seen["ident"] = threading.get_ident()
        return orig(self, key, ts, *readings)

    monkeypatch.setattr(TrafficSampleModule, "sample_series", spy)
    threads_before = threading.active_count()
    assert mgr.task_queue.run_due(max_tasks=10) == 1
    assert seen["ident"] == threading.get_ident()  # 采样点产出线程 == 跑队列的线程
    assert threading.active_count() == threads_before  # 模块未创建任何线程


def test_first_sample_only_establishes_baseline(tmp_path):
    """首个采样只立基线不出增量(首窗 null); 次轮增量 = cur - last(§03.4)"""
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    mod = mgr.host.get("qb_traffic")
    p1 = _run_sample(mgr)
    assert p1 is True
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
    with _ModuleLogCapture() as cap:
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
    """运行期关闭(L0 换对象, 队列未重建): handler 短路不采样不动内存, 任务保留"""
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    mod = mgr.host.get("qb_traffic")
    mod.start(mgr.ctx, dry_run=False)
    mgr.config.qb_traffic = QbTraffic(enabled=False)
    assert _run_sample(mgr) is True  # 任务保留(REQUEUE)
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
    """enabled=true: 采样点落 v3 天文件 <data_dir>/qb-traffic-v3/{global,torrents/<h>}/<date>.dat
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
    gpath = _v3_path(tmp_path, GLOBAL_SERIES_KEY, clock.now)
    tpath = _v3_path(tmp_path, "torrent:HASH123", clock.now)
    assert gpath.is_file() and tpath.is_file()
    lines = gpath.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "# auto-qb qb-traffic v3" and lines[1] == "key,global"
    parsed = parse_v3_day_text(gpath.read_text(encoding="utf-8"))
    assert parsed.key == "global" and len(parsed.blocks) == 1
    block = parsed.blocks[0]
    assert block.start_epoch == int(clock.now) - 30 and block.interval_s == 30  # B 块头
    assert len(block.records) == 2 and all(isinstance(r, V3Sample) for r in block.records)
    r0 = block.records[0]
    assert (r0.dl_rate, r0.up_rate, r0.dl_total, r0.up_total) == (1024, 2048, 10_000_000, 20_000_000)
    assert all(r.dt_ms is None for r in block.records)  # 等间隔采样: 空载稀疏零 dt 行
    # r 行 5 列(无 dt); 会话快照(1_000_000/2_000_000)不落任何列
    assert lines[3].split(",") == ["r", "1024", "2048", "10000000", "20000000"]


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
    flush_interval 才全系列批量落盘; 缓冲清空后块状态延续(header_written/游标), 块头只写一次"""
    clock = _Clock()
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30, flush_interval=60))
    mgr.store.server_state = _ss()
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)  # t0: r 进缓冲; 首轮只记 flush 时点
    assert _v3_read(tmp_path, GLOBAL_SERIES_KEY, clock.now) is None
    assert mod._buffers[GLOBAL_SERIES_KEY].records
    clock.advance(30)
    _run_sample(mgr)  # 30 < 60: 未到点, 缓冲滞留
    assert _v3_read(tmp_path, GLOBAL_SERIES_KEY, clock.now) is None
    clock.advance(30)
    _run_sample(mgr)  # 60 >= 60: 批量落盘(本轮记录含在内; 块头随批)
    parsed = _v3_read(tmp_path, GLOBAL_SERIES_KEY, clock.now)
    assert parsed is not None and len(parsed.blocks) == 1 and len(parsed.blocks[0].records) == 3
    buf = mod._buffers[GLOBAL_SERIES_KEY]
    assert buf.records == [] and buf.header_written and buf.start_epoch is not None  # 块状态延续
    clock.advance(30)
    _run_sample(mgr)  # 30 < 60: 缓冲滞留
    assert len(_v3_read(tmp_path, GLOBAL_SERIES_KEY, clock.now).blocks[0].records) == 3
    clock.advance(30)
    _run_sample(mgr)  # 同块续写: 不重复写块头
    parsed = _v3_read(tmp_path, GLOBAL_SERIES_KEY, clock.now)
    assert len(parsed.blocks) == 1 and len(parsed.blocks[0].records) == 5


def test_global_idle_run_seals_on_time_r1(tmp_path, monkeypatch):
    """触发 (3): 全局空闲 600s 封口成 buffer 记录(v3 不单独落盘); flush 后 z 行
    run_len/totals 快照正确且零 dt(标称跨度); 封口移除游程, 下个零样本开新游程"""
    clock = _Clock()
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)  # t0: 活跃 -> r 记录进缓冲
    mgr.store.server_state = _idle_state()
    for _ in range(19):  # t0+30 .. t0+570: 零样本只推进游程
        clock.advance(30)
        _run_sample(mgr)
    assert GLOBAL_SERIES_KEY in mod._open_runs  # 游程在内存(未到 600s)
    assert _v3_read(tmp_path, GLOBAL_SERIES_KEY, clock.now) is None  # 未到 flush 时点零落盘
    clock.advance(30)  # t0+600: flush 时点(r 落盘); 游程 570s 仍未封口
    _run_sample(mgr)
    assert GLOBAL_SERIES_KEY in mod._open_runs
    clock.advance(30)  # t0+630: 时长 600s >= ZRUN_FLUSH_S -> 封口成 buffer 记录
    _run_sample(mgr)
    assert GLOBAL_SERIES_KEY not in mod._open_runs  # 封口即移除
    z = mod._buffers[GLOBAL_SERIES_KEY].records[-1]
    assert isinstance(z, V3ZeroRun) and z.run_len == 21  # [t0+30, t0+630] 共 21 个零样本
    assert (z.dl_total, z.up_total) == (10_000_000, 20_000_000)  # totals 快照 = all-time 对
    assert z.dt_ms is None  # 标称跨度(run_len x interval), 零漂移不写 dt
    _flush(mod)
    parsed = _v3_read(tmp_path, GLOBAL_SERIES_KEY, clock.now)
    recs = parsed.blocks[0].records
    assert [type(r) for r in recs] == [V3Sample, V3ZeroRun]  # 文件序 = 时间序
    clock.advance(30)  # t0+660: 下个零样本开新游程
    _run_sample(mgr)
    run = mod._open_runs[GLOBAL_SERIES_KEY]
    assert run.start == clock.now and run.samples == 1


def test_torrent_idle_run_snapshot_fixed_at_open(tmp_path, monkeypatch):
    """单种动过->停: z 记录 totals 快照固定在开启时刻(首个零样本的 all-time 对);
    空闲期两个不同 totals 的零样本不刷新快照(§3.4 沿用)"""
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
    for _ in range(19):  # t0+60 .. t0+600: 零样本只推进(未到 600s)
        clock.advance(30)
        _run_sample(mgr)
    clock.advance(30)  # t0+630: 触发 (3) 封口, 封 [start, 触发样本]
    _run_sample(mgr)
    z = mod._buffers[rel_key].records[-1]
    assert isinstance(z, V3ZeroRun)
    assert (z.dl_total, z.up_total) == (5_000_500, 3_000_200)  # 快照 = 首零样本对, 非后续零样本
    assert rel_key not in mod._open_runs
    _flush(mod)
    parsed = _v3_read(tmp_path, rel_key, clock.now)
    assert isinstance(parsed.blocks[0].records[-1], V3ZeroRun)


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
    assert not _v3_series_dir(tmp_path, "NEVER").exists()  # 零文件零目录
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
    parsed = _v3_read(tmp_path, key, clock.now)
    recs = parsed.blocks[0].records
    assert [type(r) for r in recs] == [V3Sample, V3ZeroRun, V3Sample]  # 文件序 = 时间序
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
    parsed = _v3_read(tmp_path, GLOBAL_SERIES_KEY, clock.now)
    recs = parsed.blocks[0].records
    assert [type(r) for r in recs] == [V3Sample, V3ZeroRun, V3NullRun, V3Sample]  # z 行在 n 之前
    assert recs[1].run_len == 2  # z 封 [t0+30, t0+60], 末日早于断连轮
    assert recs[2].run_len == 1  # n 槽 = 断连轮(重连非零样本封口)


def test_cap_samples_seals_before_time_flush(tmp_path, monkeypatch):
    """触发 (4): 游程样本数 >= ZRUN_CAP_SAMPLES(120) 即封口 —— interval 1s 场景下
    先于 600s 时间刷新 (3), span < ZRUN_FLUSH_S(v3 游程 dt 链推算核对)"""
    clock = _Clock()
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=1))
    mgr.store.server_state = _ss()
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)  # t0: 活跃
    mgr.store.server_state = _idle_state()
    for _ in range(ZRUN_CAP_SAMPLES):  # 120 个零样本 @1s: 第 120 个触发 (4)
        clock.advance(1)
        _run_sample(mgr)
    z = mod._buffers[GLOBAL_SERIES_KEY].records[-1]
    assert isinstance(z, V3ZeroRun) and z.run_len == ZRUN_CAP_SAMPLES
    assert GLOBAL_SERIES_KEY not in mod._open_runs
    _flush(mod)
    parsed = _v3_read(tmp_path, GLOBAL_SERIES_KEY, clock.now)
    slots = v3_block_slots(parsed.blocks[0])
    span = slots[-1].ts - slots[1].ts  # 游程首槽(块首 r 后)到末槽
    assert span == ZRUN_CAP_SAMPLES - 1  # [首零样本, 第 120 零样本]
    assert span < ZRUN_FLUSH_S  # 样本上限先于时间刷新触发


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
    assert all(not isinstance(r, (V3ZeroRun, V3NullRun)) for r in mod._buffers[key].records)
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
    assert not _v3_series_dir(tmp_path, "NEVER").exists()  # 单种被数据门拦截
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
    task2 = Task("internal", TASK_NAME, interval=30, handler=mod2.handle_traffic_sample)
    for _ in range(21):  # t0+90..t0+690: 零样本重新开游程, 至 t0+690 触发 (3) 封口
        clock.advance(30)
        mod2.handle_traffic_sample(task2, dry_run=False)
    mod2._flush_all_series()
    parsed = _v3_read(tmp_path, GLOBAL_SERIES_KEY, clock.now)
    assert len(parsed.blocks) == 2  # 重启前后各一块(重启 = 新块首)
    assert [type(r) for r in parsed.blocks[0].records] == [V3Sample]  # 已落盘块不受重启影响
    z = parsed.blocks[1].records[0]
    assert isinstance(z, V3ZeroRun) and z.run_len == 21  # 重启后游程如期封口
    assert parsed.blocks[1].start_epoch == int(clock.now) - 600  # 块首 = 游程首零样本(t0+90)


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
    assert not (tmp_path / "qb-traffic-v3").exists()  # 零目录零文件
    assert mod._buffers[GLOBAL_SERIES_KEY].records == []
    clock.advance(600)  # t0+660: 触发 (3) 封口(内存照常)
    _run_sample(mgr, dry_run=True)
    assert GLOBAL_SERIES_KEY not in mod._open_runs
    assert not (tmp_path / "qb-traffic-v3").exists()


# ---------- 累积漂移触发 dt_ms(§2.3 写侧, S2a 验收 tol 边界族) ----------
def test_dt_drift_boundary_family(tmp_path, monkeypatch):
    """tol 边界族(判据必须用「累积漂移」而非「本行偏差」):
    - 压线行: 恒定 250ms 偏差(累积漂移恰在容差上)不写 dt;
    - 超线行: 累积漂移 > 250ms 写实测 dt 并自然复位(游标推到实测点);
    - 稳态小漂移(150ms/行)退化周期写(约每 2 行一 dt);
    - 空载(等间隔)零 dt 行(稀疏);
    - roundtrip: v3_block_slots 推算时刻与实测逐一相等(误差 <= 取整)。"""
    clock = _Clock()
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    mod = mgr.host.get("qb_traffic")

    def rd():
        _flush(mod)
        return _v3_read(tmp_path, GLOBAL_SERIES_KEY, clock.now)

    # 空载: 等间隔 3 轮 -> 零 dt 行
    _run_sample(mgr)
    for _ in range(3):
        clock.advance(30)
        _run_sample(mgr)
    recs = rd().blocks[0].records
    assert [r.dt_ms for r in recs] == [None, None, None, None]
    # 压线: 恒定 250ms 偏差(不累积: 首步 +0.25, 之后整间隔) -> 永不触发
    clock.advance(30.25)
    _run_sample(mgr)
    for _ in range(2):
        clock.advance(30)
        _run_sample(mgr)
    recs = rd().blocks[0].records
    assert all(r.dt_ms is None for r in recs[-3:]), recs[-3:]
    # 超线: 单次 300ms 突跳 -> 该行写实测 dt(从链上锚点起算)并复位, 次行回标称
    clock.advance(30.3)
    _run_sample(mgr)
    clock.advance(30)
    _run_sample(mgr)
    recs = rd().blocks[0].records
    assert recs[-2].dt_ms is not None and recs[-1].dt_ms is None
    # 稳态小漂移 150ms/行(< tol, 逐行判永不触发): 误差累积至超线 -> 周期性 dt 行(退化逐行写的离散形态)
    for _ in range(4):
        clock.advance(30.15)
        _run_sample(mgr)
    recs = rd().blocks[0].records
    dts = [r.dt_ms for r in recs[-4:]]
    assert dts[0] is None and dts[1] is not None and dts[2] is None and dts[3] is not None, dts
    # roundtrip: 推算时刻与实测逐一对照 —— 标称行差 <= tol(漂移在容差内如实保留),
    # 显式 dt 行差 <= dt_ms 取整 1ms; 链无累积误差(无 0.001 以上的系统性漂移)
    parsed = _v3_read(tmp_path, GLOBAL_SERIES_KEY, clock.now)
    slots = v3_block_slots(parsed.blocks[0])
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
    parsed = _v3_read(tmp_path, GLOBAL_SERIES_KEY, clock.now)
    assert parsed.blocks[0].records[-1].dt_ms == 1  # 落盘形态一致


# ---------- C1 热重载联动 + 跨天切块 + 缓冲闸 + stop 钩子(§3.4/§3.5) ----------
def test_interval_change_hot_reload_new_block_and_task_interval(tmp_path, monkeypatch):
    """热重载改采样率即时生效(§3.5): handler 现读 -> task.interval 回写 + 旧块落盘(旧
    interval) + 新块带新 interval —— 新旧数据分块各有 interval(A3 根因闭合)"""
    clock = _Clock()
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    mod = mgr.host.get("qb_traffic")
    task = Task("internal", TASK_NAME, interval=30, handler=mod.handle_traffic_sample)
    mod.handle_traffic_sample(task, dry_run=False)  # t0: r 进缓冲(interval 30)
    clock.advance(30)
    mgr.config.qb_traffic.sample_interval = 10
    mod.handle_traffic_sample(task, dry_run=False)  # t0+30: 检测变化 -> 关旧块 + 回写 task.interval
    assert task.interval == 10  # A3: 直接改运行中任务的间隔
    parsed = _v3_read(tmp_path, GLOBAL_SERIES_KEY, clock.now)
    assert len(parsed.blocks) == 1 and parsed.blocks[0].interval_s == 30  # 旧块随关块落盘(旧 interval)
    assert [type(r) for r in parsed.blocks[0].records] == [V3Sample]
    clock.advance(10)
    mod.handle_traffic_sample(task, dry_run=False)  # t0+40: 新块(新 interval)
    _flush(mod)
    parsed = _v3_read(tmp_path, GLOBAL_SERIES_KEY, clock.now)
    assert len(parsed.blocks) == 2
    assert parsed.blocks[1].interval_s == 10 and parsed.blocks[1].start_epoch == int(clock.now) - 10
    # 变化轮自身记录落在新块首(关块先行于本轮采样), 下轮续写同块
    assert [type(r) for r in parsed.blocks[1].records] == [V3Sample, V3Sample]


def test_interval_mismatch_ceils_and_warns_once(tmp_path, monkeypatch):
    """运行期失配(D5): 向上取整到下一倍数(main_tick=2 配 3s -> 4s, task.interval=取整值) +
    告警一次(防重复); 配置再变记忆复位; 不拒采"""
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=3))
    mgr.config.main_tick = 2.0  # FakeConfig 缺省 1.0; 显式置 2 构造失配场景
    mgr.store.server_state = _ss()
    mod = mgr.host.get("qb_traffic")
    task = Task("internal", TASK_NAME, interval=3, handler=mod.handle_traffic_sample)
    with _ModuleLogCapture() as cap:
        assert mod.handle_traffic_sample(task, dry_run=False) is True  # 不拒采
    assert task.interval == 4  # ceil(3/2) x 2 = 4(颗粒变粗不断线)
    assert "取整" in cap.text and "整数倍" in cap.text  # 恰一次告警
    with _ModuleLogCapture() as cap2:
        mod.handle_traffic_sample(task, dry_run=False)
    assert "取整" not in cap2.text  # 同一失配不重复告警
    # 配置变化 -> 记忆复位: 新失配再告警一次
    mgr.config.qb_traffic.sample_interval = 5  # ceil(2.5) x 2 = 6
    with _ModuleLogCapture() as cap3:
        mod.handle_traffic_sample(task, dry_run=False)
    assert task.interval == 6 and "取整" in cap3.text


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
    today = v3_epoch_date_str(t_before)
    p_today = _v3_path(tmp_path, GLOBAL_SERIES_KEY, t_before)
    p_tomorrow = _v3_path(tmp_path, GLOBAL_SERIES_KEY, clock.now)
    assert p_today.is_file() and p_tomorrow.is_file()
    d1 = parse_v3_day_text(p_today.read_text(encoding="utf-8"))
    d2 = parse_v3_day_text(p_tomorrow.read_text(encoding="utf-8"))
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
    p_today = _v3_path(tmp_path, GLOBAL_SERIES_KEY, t_before)
    p_tomorrow = _v3_path(tmp_path, GLOBAL_SERIES_KEY, clock.now)
    d1 = parse_v3_day_text(p_today.read_text(encoding="utf-8"))
    d2 = parse_v3_day_text(p_tomorrow.read_text(encoding="utf-8"))
    assert [type(r) for r in d1.blocks[0].records] == [V3Sample, V3ZeroRun]  # 旧块: r + 跨天前封的 z
    assert d1.blocks[0].records[1].run_len == 1
    assert [type(r) for r in d2.blocks[0].records] == [V3ZeroRun, V3Sample]  # 新块首 = 单槽游程
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
    task = Task("internal", TASK_NAME, interval=1, handler=mod.handle_traffic_sample)
    for _ in range(V3_BUFFER_SLOT_CAP):  # 3600 轮活跃: 第 3600 槽触发提前 flush(驱动永不触发)
        clock.advance(1)
        mod.handle_traffic_sample(task, dry_run=False)
    parsed = _v3_read(tmp_path, GLOBAL_SERIES_KEY, clock.now)
    assert parsed is not None and len(parsed.blocks) == 1
    assert len(parsed.blocks[0].records) == V3_BUFFER_SLOT_CAP  # 恰在闸值落盘
    buf = mod._buffers[GLOBAL_SERIES_KEY]
    assert buf.records == [] and buf.start_epoch is not None  # 块未关, 续写同块
    for _ in range(3):
        clock.advance(1)
        mod.handle_traffic_sample(task, dry_run=False)
    _flush(mod)
    parsed = _v3_read(tmp_path, GLOBAL_SERIES_KEY, clock.now)
    assert len(parsed.blocks) == 1 and len(parsed.blocks[0].records) == V3_BUFFER_SLOT_CAP + 3


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
    parsed = _v3_read(tmp_path, GLOBAL_SERIES_KEY, clock.now)
    recs = parsed.blocks[0].records
    assert [type(r) for r in recs] == [V3Sample, V3ZeroRun]  # 全量落盘
    assert recs[1].run_len == 2
    before = parsed.blocks[0].records
    mod.stop()  # 幂等: 缓冲游程已空, 零副作用
    assert _v3_read(tmp_path, GLOBAL_SERIES_KEY, clock.now).blocks[0].records == before


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
    assert not (tmp_path / "qb-traffic-v3").exists()


def test_flush_oserror_discards_block_warns_once(tmp_path, monkeypatch):
    """落盘失败(OSError, §01.1): 不上抛、连续失败只告警一次; 失败块丢弃并复位块状态
    (dt 链卫生: 下次成功写起新块, 游标不错位)"""
    clock = _Clock()
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)
    from auto_qb.core.traffic_store import TrafficV3Store

    failing = {"on": True}
    real_append = TrafficV3Store.append_records

    def flaky_append(self, key, date_str, header, records):
        if failing["on"]:
            raise OSError("disk full")
        return real_append(self, key, date_str, header, records)

    monkeypatch.setattr(TrafficV3Store, "append_records", flaky_append)
    with _ModuleLogCapture() as cap:
        _flush(mod)  # 失败 1: 告警一次, 块复位
    assert "批量落盘失败" in cap.text
    assert mod._buffers[GLOBAL_SERIES_KEY].start_epoch is None  # 块状态复位
    _run_sample(mgr)
    with _ModuleLogCapture() as cap2:
        _flush(mod)  # 失败 2: 持续失败降级 DEBUG(措辞「持续」), 不再 WARNING
    assert "(持续)" in cap2.text and "(本批数据丢失" not in cap2.text
    failing["on"] = False
    clock.advance(30)
    _run_sample(mgr)
    _flush(mod)  # 恢复: 新块成功落盘(B.start = 新块首)
    parsed = _v3_read(tmp_path, GLOBAL_SERIES_KEY, clock.now)
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
