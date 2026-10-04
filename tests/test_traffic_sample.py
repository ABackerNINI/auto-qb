"""test_traffic_sample 测试计划: qB 口径流量采样器(plan 26-10-03-0946 方案C P1 采样器核心 + §06 配置键 + S2 落盘接线 + plan 26-10-04-0721 P2 开放行程)

## 测试计划(每个测试函数一条)
- test_qb_traffic_config_absent_means_disabled: 键组缺省 -> config.qb_traffic 为 None(未启用)
- test_qb_traffic_config_parses_sample: 完整样例解析(enabled/三个时间键换算成秒)
- test_qb_traffic_config_partial_falls_back_to_defaults: 部分键缺省回退 QbTraffic 默认值
- test_qb_traffic_config_rejects_bad_section: 段非 dict / 未知键 / enabled 非布尔
- test_qb_traffic_config_bounds_matrix: 四时间/布尔键边界矩阵(1.5S~10M / 1H~90D / 7D~无上限 恰好压线收, 压线外拒)
- test_sample_task_registered_when_enabled: enabled=true -> start 创建 qb_traffic_sample 全局任务(interval=采样间隔)
- test_sample_task_not_registered_when_disabled: enabled=false 与键组缺省(None)两种情形均不建任务
- test_sample_task_reregisters_on_queue_rebuilt: L2 队列重建 -> 按新配置重入队(换 interval/启用/停用三向)
- test_sampling_runs_on_caller_thread: 采样在调用 run_due 的线程(主循环线程)内同步执行, 模块不建线程(单写线程不变式)
- test_first_sample_only_establishes_baseline: 首个采样只立基线不出增量(首窗 null), 次轮出正常增量
- test_counter_rollback_records_reset_no_negative: 模拟 qB 重启(计数器回落) -> 不产负增量、增量记 null、基线更新为 cur、INFO 记重置
- test_disconnect_produces_null_point: qB 断连(store.client None) -> 全局 null 点、单种不产点、基线不动
- test_missing_fields_produce_null_point_not_zero: server_state 关键字段缺失/空值 -> null 点(不写 0)且基线不推进
- test_torrent_active_filter_zero_rows_when_idle: 活跃种子照常采 raw 行; 空闲种子零 raw 行(v2: 零样本按开放行程纪律压缩, 从未传输者无行程)
- test_disabled_at_runtime_handler_noop: 任务已注册后运行期关闭 -> handler 短路不采样(任务保留)
- test_enabled_false_creates_zero_files_or_dirs: enabled=false/键组缺省 -> start+采样全程零文件零目录(S2 保守默认验收)
- test_enabled_true_persists_under_data_dir: enabled=true -> 采样点落 <data_dir>/qb-traffic/, raw 逐列 + 会话快照不落盘
- test_module_contract: name/sections 声明正确且被装配清单认领
- test_global_idle_flushes_z_row_on_time_r1: 全局空闲 600s(R1)刷新出 z 行而非逐行零行; 区间与 totals 快照正确; 封口后下个零样本开新行程
- test_torrent_idle_run_snapshot_fixed_at_open: 单种动过->停: 行程行出现且 totals 快照固定在开启时刻(两个不同 totals 的零样本不刷新)
- test_never_transferred_torrent_zero_files_runs_entries: 从未传输种子: 零文件零行程零 index 条目(has_entry 拦截)
- test_nonzero_arrival_seals_z_before_raw_same_round: 非零样本到达同轮先 z 后 raw(文件序断言)
- test_disconnect_seals_run_before_null_r2: 断连 null 前先封口(R2): z 覆盖不横跨断连期
- test_hourly_seal_flush_all_then_sweep_with_real_interval: 小时封口先 flush-all 再 seal_sweep; seal_sweep 收到真实 interval_s
- test_cap_samples_seals_before_time_flush: 120 样本上限封口(interval 1s 场景先于 600s 触发, span < ZRUN_FLUSH_S)
- test_restart_loses_at_most_one_open_run: 重建 sampler 实例(重启)丢开放行程 <=1, 已落盘行不受影响, 零样本重新开行程
- test_zero_samples_do_not_touch_baselines_or_latest: 零样本不动 baselines/latest(镜像冻结在最后活跃点)
- test_dry_run_no_disk_but_memory_runs_advance: dry_run 零落盘; 行程内存照常推进/封口移除
- test_zero_run_requires_valid_totals_snapshot: 行程开启需 totals 快照合法: totals 缺失的零样本不开新行程
- test_global_always_opens_run_vs_torrent_gated: 全局零样本恒开行程(无 index 不拦截) vs 单种 has_entry 拦截(对照)
"""
import io
import logging
import threading

import yaml

from auto_qb.config import QbTraffic, load_config
from auto_qb.config.validation import validate_config
from auto_qb.core.modules import traffic_sample_mod as ts_mod
from auto_qb.core.modules.traffic_sample_mod import (
    GLOBAL_SERIES_KEY,
    TASK_NAME,
    ZRUN_CAP_SAMPLES,
    ZRUN_FLUSH_S,
    TrafficSampleModule,
)
from auto_qb.core.taskqueue import Task, TaskQueue
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
    mgr.config.data_dir = str(tmp_path)  # S2: dat 落盘根目录(真实配置恒非空, loaders 默认 auto-qb-data)
    mgr.client = FakeClient()
    if qb_traffic is not None:
        mgr.config.qb_traffic = qb_traffic
    return mgr


def _run_sample(mgr, dry_run: bool = False) -> bool:
    """直调采样 handler(与 test_speed_curve._run_curve 同款, 不经队列)"""
    mod = mgr.host.get("qb_traffic")
    task = Task("internal", TASK_NAME, interval=30, handler=mod.handle_traffic_sample)
    return mod.handle_traffic_sample(task, dry_run=dry_run)


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
def _cfg_dict(qb_traffic_spec) -> dict:
    return {
        "config":
            {
                "qbittorrent": {
                    "host": "127.0.0.1",
                    "port": 8080,
                    "username": "u",
                    "password": "p"
                },
                "trackers": {},
                "qb_traffic": qb_traffic_spec,
            }
    }


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
    """完整样例解析: enabled 布尔化 + 三个时间键换算成秒"""
    cfg = _load(
        tmp_path, {
            "enabled": "true",
            "sample_interval": "1M",
            "raw_window": "48H",
            "rollup_window": "60D",
        }
    ).qb_traffic
    assert cfg.enabled is True
    assert cfg.sample_interval == 60.0
    assert cfg.raw_window == 48 * 3600.0
    assert cfg.rollup_window == 60 * 86400.0


def test_qb_traffic_config_partial_falls_back_to_defaults(tmp_path):
    """部分键缺省回退默认值(30S/24H/30D, enabled 缺省 false)"""
    cfg = _load(tmp_path, {"enabled": "true"}).qb_traffic
    assert cfg.enabled is True
    d = QbTraffic()
    assert cfg.sample_interval == d.sample_interval == 30.0
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
    """边界矩阵: 恰好压线合法(含等价秒数), 压线外拒绝; 三时间键各自独立校验"""
    # 合法: 上下边界恰好压线(1.5S~10M / 1H~90D / 7D~无上限)
    ok = validate_config(
        _cfg_dict({
            "enabled": "true",
            "sample_interval": "1.5S",
            "raw_window": "1H",
            "rollup_window": "7D",
        })
    )
    assert ok == [], ok
    ok = validate_config(
        _cfg_dict(
            {
                "enabled": "false",
                "sample_interval": "10M",
                "raw_window": "90D",
                "rollup_window": "36500D",  # 保留窗无上限: 100 年也合法(等效永久保留)
            }
        )
    )
    assert ok == [], ok
    # 越界: 各键压线外一秒即拒
    bad = validate_config(_cfg_dict({"sample_interval": "1.4S"}))
    assert any("sample_interval" in e for e in bad), bad
    bad = validate_config(_cfg_dict({"sample_interval": "601S"}))
    assert any("sample_interval" in e for e in bad), bad
    bad = validate_config(_cfg_dict({"raw_window": "30M"}))
    assert any("raw_window" in e for e in bad), bad
    bad = validate_config(_cfg_dict({"raw_window": "91D"}))
    assert any("raw_window" in e for e in bad), bad
    bad = validate_config(_cfg_dict({"rollup_window": "6D"}))
    assert any("rollup_window" in e for e in bad), bad


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
    """qB 断连(store.client None) -> 全局出 null 点、单种不产新点、基线不推进(§03.5)"""
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
    assert g.dl_rate is None and g.dl_total is None and g.dl_inc is None  # 全字段 null
    assert mod.latest["torrent:HASH123"] is t_before  # 单种不产新点(停机洞由全局系列表达)
    assert mod._baselines[GLOBAL_SERIES_KEY] == baseline_before  # null 点不推进基线


def test_missing_fields_produce_null_point_not_zero(tmp_path):
    """server_state 缺字段 / 显式 None -> 该轮 null 点(不写 0)且基线不推进(§03.5)"""
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
    """活跃过滤(v2 §3.2 口径): 活跃(dlspeed>0 or upspeed>0)照常出 raw 行; 空闲种子零 raw 行
    —— 从未传输者(has_entry 拦截)连行程都不开, latest 无其采样点"""
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    seed_store(
        mgr,
        [
            _active_torrent("DL_ACTIVE", dlspeed=100, upspeed=0),  # 仅下载活跃
            _active_torrent("UL_ACTIVE", dlspeed=0, upspeed=200),  # 仅上传活跃
            FakeTorrent(hash="IDLE1"),  # 全空闲(从未传输: 无 index 条目)
            _active_torrent("IDLE2", dlspeed=0, upspeed=0),  # 显式 0 = 空闲
        ],
    )
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)
    assert "torrent:DL_ACTIVE" in mod.latest and "torrent:UL_ACTIVE" in mod.latest
    assert "torrent:IDLE1" not in mod.latest and "torrent:IDLE2" not in mod.latest  # 空闲零 raw 行
    assert "torrent:IDLE1" not in mod._open_runs and "torrent:IDLE2" not in mod._open_runs  # 无条目不开行程
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
    """enabled=false 与键组缺省两种情形: start + 采样全程零新建文件/目录(S2 落盘接线后的
    保守默认验收, 黄金法则 2; S1 的「enabled=true 纯内存」边界已被 P2 接线取代,
    落盘形态断言在 test_traffic_store.py)"""
    for qb in (QbTraffic(enabled=False), None):
        mgr = _mgr_with_traffic(tmp_path, qb)
        mgr.store.server_state = _ss()
        seed_store(mgr, [_active_torrent()])
        mod = mgr.host.get("qb_traffic")
        mod.start(mgr.ctx, dry_run=False)  # 对账同样零动作(存储目录不存在 -> 不创建)
        _run_sample(mgr)
        _run_sample(mgr)
        assert sorted(str(p) for p in tmp_path.rglob("*")) == [], qb


def test_enabled_true_persists_under_data_dir(tmp_path):
    """enabled=true: 采样点落盘到 <data_dir>/qb-traffic/(global.dat + 单种惰建文件);
    会话快照列不落盘(§02.3: 只落速率对 + all-time 累计对)"""
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    seed_store(mgr, [_active_torrent()])
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)
    _run_sample(mgr)
    root = tmp_path / "qb-traffic"
    assert (root / "global.dat").is_file()
    assert (root / "torrents" / "HASH123.dat").is_file()
    text = (root / "global.dat").read_text(encoding="utf-8")
    lines = text.splitlines()
    assert lines[0] == "# auto-qb qb-traffic v1" and lines[1] == "key,global"
    assert all(line.startswith("raw,") for line in lines[2:])
    # 六列恰为 raw/时间/速率对/all-time 累计对; 会话快照(1_000_000/2_000_000)不落任何列(§02.3)
    first_raw = lines[2].split(",")
    assert len(first_raw) == 6
    assert first_raw[0] == "raw" and first_raw[2] == "1024" and first_raw[3] == "2048"
    assert first_raw[4] == "10000000" and first_raw[5] == "20000000"


def test_module_contract(tmp_path):
    """模块契约: name=qb_traffic / sections 声明 qb_traffic 且被装配清单认领"""
    mgr = _mgr_with_traffic(tmp_path, None)
    mod = mgr.host.get("qb_traffic")
    assert mod is not None and mod.name == "qb_traffic"
    assert mod.sections() == ("qb_traffic", )
    assert "qb_traffic" in mgr.host.claimed_sections()


# ---------- 开放行程(plan 26-10-04-0721 P2, v2 §3.1-§3.4) ----------
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


def _dat_lines(tmp_path, rel="global.dat"):
    """读系列 dat 全部行(不存在返回空表)"""
    p = tmp_path / "qb-traffic" / rel
    return p.read_text(encoding="utf-8").splitlines() if p.exists() else []


def _z_parts(lines):
    """z 行按列拆分(z,<start>,<end>,<dl_total>,<up_total>)"""
    return [line.split(",") for line in lines if line.startswith("z,")]


def _raw_ts_set(lines):
    """raw 行时间戳集合(null 行含内, 按 ts 列)"""
    return {int(line.split(",")[1]) for line in lines if line.startswith("raw,")}


def test_global_idle_flushes_z_row_on_time_r1(tmp_path, monkeypatch):
    """全局空闲 600s 刷新(R1): 触发 (3) 出 z 行而非逐行零行; 区间 = [首零样本, 触发样本];
    totals 快照 = all-time 对; 封口移除行程, 下个零样本开新行程"""
    clock = _Clock()
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)  # t0: 活跃 -> raw 行
    mgr.store.server_state = _idle_state()
    for _ in range(20):  # t0+30 .. t0+600: 零样本只推进行程, 零落盘
        clock.advance(30)
        _run_sample(mgr)
    assert GLOBAL_SERIES_KEY in mod._open_runs  # 行程在内存(未到 600s)
    assert len(_z_parts(_dat_lines(tmp_path))) == 0 and len(_raw_ts_set(_dat_lines(tmp_path))) == 1
    clock.advance(30)  # t0+630: 时长 600s >= ZRUN_FLUSH_S -> 封口
    _run_sample(mgr)
    lines = _dat_lines(tmp_path)
    zs = _z_parts(lines)
    assert len(zs) == 1  # 空闲段压缩为一行 z
    assert zs[0][1] == str(int(clock.now - 600)) and zs[0][2] == str(int(clock.now))
    assert zs[0][3] == "10000000" and zs[0][4] == "20000000"  # totals 快照 = all-time 对
    assert _raw_ts_set(lines) == {int(clock.now) - 630}  # 空闲期无新增 raw 行
    assert GLOBAL_SERIES_KEY not in mod._open_runs  # 封口即移除
    clock.advance(30)  # t0+660: 下个零样本开新行程
    _run_sample(mgr)
    run = mod._open_runs[GLOBAL_SERIES_KEY]
    assert run.start == clock.now and run.samples == 1


def test_torrent_idle_run_snapshot_fixed_at_open(tmp_path, monkeypatch):
    """单种动过->停: 行程行出现且 totals 快照固定在开启时刻(首个零样本的 all-time 对);
    空闲期两个不同 totals 的零样本不刷新快照(§3.4)"""
    clock = _Clock()
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    rec = _active_torrent("HASH123", downloaded=5_000_000, uploaded=3_000_000)
    seed_store(mgr, [rec])
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)  # t0: 活跃 -> raw 行 + 建文件建条目
    rel = "torrents/HASH123.dat"
    rec.dlspeed = 0
    rec.upspeed = 0
    rec.downloaded, rec.uploaded = 5_000_500, 3_000_200  # 首个零样本: 行程开启, 快照取此对
    clock.advance(30)
    _run_sample(mgr)
    rec.downloaded, rec.uploaded = 5_000_900, 3_000_400  # 次个零样本: 只推进, 快照不刷新
    for _ in range(19):  # t0+60 .. t0+600: 零样本只推进(未到 600s)
        clock.advance(30)
        _run_sample(mgr)
    clock.advance(30)  # t0+630: 触发 (3) 封口, 封 [start, 触发样本 ts]
    _run_sample(mgr)
    lines = _dat_lines(tmp_path, rel)
    zs = _z_parts(lines)
    assert len(zs) == 1
    assert zs[0][1] == str(int(clock.now - 600)) and zs[0][2] == str(int(clock.now))
    assert zs[0][3] == "5000500" and zs[0][4] == "3000200"  # 快照 = 首零样本对, 非后续零样本
    assert "torrent:HASH123" not in mod._open_runs


def test_never_transferred_torrent_zero_files_runs_entries(tmp_path, monkeypatch):
    """从未传输的种子: 零文件、零行程、零 index 条目(has_entry 拦截, §3.3)"""
    clock = _Clock()
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    seed_store(mgr, [FakeTorrent(hash="NEVER")])  # 全零速且从无流量
    mod = mgr.host.get("qb_traffic")
    for _ in range(3):
        clock.advance(30)
        _run_sample(mgr)
    st = mod._get_store(mgr.ctx)
    assert not st.has_entry("NEVER")
    assert not (tmp_path / "qb-traffic" / "torrents" / "NEVER.dat").exists()
    assert "torrent:NEVER" not in mod._open_runs and "torrent:NEVER" not in mod.latest


def test_nonzero_arrival_seals_z_before_raw_same_round(tmp_path, monkeypatch):
    """触发 (1): 非零样本到达同轮先 z 后 raw(文件序 = 时间序), 封 [start, last_seen]"""
    clock = _Clock()
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    rec = _active_torrent("HASH123")
    seed_store(mgr, [rec])
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)  # t0: 活跃 -> raw
    rel = "torrents/HASH123.dat"
    rec.dlspeed = 0
    rec.upspeed = 0
    clock.advance(30)
    _run_sample(mgr)  # t0+30: 零样本 -> 开行程(不落盘)
    rec.dlspeed = 512
    clock.advance(30)
    _run_sample(mgr)  # t0+60: 再活跃 -> 同轮先 z 后 raw
    lines = _dat_lines(tmp_path, rel)
    kinds = [line.split(",")[0] for line in lines if line.startswith(("raw,", "z,"))]
    assert kinds == ["raw", "z", "raw"]  # 文件序 = 时间序
    zs = _z_parts(lines)
    assert zs[0][1] == zs[0][2] == str(int(clock.now) - 30)  # 封 [start, last_seen](单零样本行程)
    assert "torrent:HASH123" not in mod._open_runs  # 封口即移除


def test_disconnect_seals_run_before_null_r2(tmp_path, monkeypatch):
    """触发 (2)(R2): 断连 null 前先封口 —— z 覆盖不横跨断连期(把「未知」虚标成 0)"""
    clock = _Clock()
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)  # t0: 活跃
    mgr.store.server_state = _idle_state()
    clock.advance(30)
    _run_sample(mgr)  # t0+30: 零样本开行程
    clock.advance(30)
    _run_sample(mgr)  # t0+60: 推进 [t0+30, t0+60]
    mgr.client = None  # 断连(重连退避期同款)
    clock.advance(30)
    _run_sample(mgr)  # t0+90: null 点
    lines = _dat_lines(tmp_path)
    kinds = [line.split(",")[0] for line in lines if line.startswith(("raw,", "z,"))]
    assert kinds == ["raw", "z", "raw"]  # z 行在 null 行之前
    zs = _z_parts(lines)
    assert zs[0][2] == str(int(clock.now) - 30)  # z 末日 = 最后零样本, 早于 null 点
    null_line = next(line for line in lines if line.startswith("raw,") and line.endswith(",,,"))
    assert int(null_line.split(",")[1]) == int(clock.now)  # null 行 ts = 断连轮
    assert mod.latest[GLOBAL_SERIES_KEY].dl_rate is None


def test_hourly_seal_flush_all_then_sweep_with_real_interval(tmp_path, monkeypatch):
    """触发 (5): 小时封口先 flush-all(z 行先落盘)再调 seal_sweep; 且 sweep 收到真实
    interval_s = config.qb_traffic.sample_interval(P2 起不再落缺省 30 兜底口径)"""
    clock = _Clock()
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)  # t0: 活跃(首轮触发小时封口扫描, 无行程可 flush)
    mgr.store.server_state = _idle_state()
    clock.advance(30)
    _run_sample(mgr)  # t0+30: 零样本开行程
    mod._sealed_hour = int(clock.now // 3600) * 3600 - 3600  # 强制下轮触发小时封口
    st = mod._get_store(mgr.ctx)
    captured = {}

    def fake_sweep(current_bucket, now, raw_window, rollup_window, interval_s=None):
        captured["interval_s"] = interval_s
        captured["z_before_sweep"] = any(line.startswith("z,") for line in _dat_lines(tmp_path))
        return 0

    monkeypatch.setattr(st, "seal_sweep", fake_sweep)
    clock.advance(30)
    _run_sample(mgr)  # t0+60: flush-all 后 seal_sweep
    assert captured["z_before_sweep"] is True  # flush-all 先于 seal_sweep(hour 归并见全部行程)
    assert captured["interval_s"] == 30  # 真实配置值
    assert len(_z_parts(_dat_lines(tmp_path))) == 1 and not mod._open_runs  # 行程已封口落盘


def test_cap_samples_seals_before_time_flush(tmp_path, monkeypatch):
    """触发 (4): 行程样本数 >= ZRUN_CAP_SAMPLES(120) 即封口 —— interval 1s 场景下
    先于 600s 时间刷新 (3), span < ZRUN_FLUSH_S"""
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
    zs = _z_parts(_dat_lines(tmp_path))
    assert len(zs) == 1
    span = int(zs[0][2]) - int(zs[0][1])
    assert span == ZRUN_CAP_SAMPLES - 1  # [首零样本, 第 120 零样本]
    assert span < ZRUN_FLUSH_S  # 样本上限先于时间刷新触发
    assert GLOBAL_SERIES_KEY not in mod._open_runs


def test_restart_loses_at_most_one_open_run(tmp_path, monkeypatch):
    """崩溃/重启语义: 重建 sampler 实例 -> 内存开放行程消失(丢 <=1 行程, 纯零信息),
    已落盘行不受影响; 零样本按纪律重新开行程"""
    clock = _Clock()
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)  # t0: 活跃 -> raw 落盘
    mgr.store.server_state = _idle_state()
    clock.advance(30)
    _run_sample(mgr)  # t0+30: 开行程
    clock.advance(30)
    _run_sample(mgr)  # t0+60: 推进(未封口, 随进程消失)
    mod2 = TrafficSampleModule(mgr.ctx)  # 重启: 新实例, baselines/_open_runs 全空
    # 隔离触发 (5): 新实例 _sealed_hour 为空 -> 首轮必触发 catch-up 封口, 会把首轮刚开的
    # 行程同轮 flush(end = last_seen) —— 该行为由 test_hourly_seal 族钉住; 此处置为当前桶
    # 以聚焦触发 (3) 的「重启后零样本重新开行程 + 600s 时间刷新」
    mod2._sealed_hour = int(clock.now // 3600) * 3600
    task2 = Task("internal", TASK_NAME, interval=30, handler=mod2.handle_traffic_sample)
    for _ in range(21):  # t0+90..t0+690: 零样本重新开行程, 至 t0+690 触发 (3) 封口
        clock.advance(30)
        mod2.handle_traffic_sample(task2, dry_run=False)
    lines = _dat_lines(tmp_path)
    assert _raw_ts_set(lines) == {int(clock.now) - 690}  # 已落盘 raw 行不受重启影响
    zs = _z_parts(lines)
    assert len(zs) == 1  # 重启前未封口行程恰丢 1 个(未落盘), 重启后行程如期封口
    assert zs[0][1] == str(int(clock.now) - 600) and zs[0][2] == str(int(clock.now))


def test_zero_samples_do_not_touch_baselines_or_latest(tmp_path, monkeypatch):
    """零样本不动 baselines/latest(§3.4): 基线只在 raw 采样点推进, 镜像冻结在最后活跃点"""
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
    """dry_run: 全程零落盘; 行程内存照常推进, flush 触发静默跳过 append(行程照常移除)"""
    clock = _Clock()
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr, dry_run=True)  # t0: 活跃(仅内存)
    mgr.store.server_state = _idle_state()
    clock.advance(30)
    _run_sample(mgr, dry_run=True)  # t0+30: 开行程
    assert GLOBAL_SERIES_KEY in mod._open_runs
    for _ in range(19):  # t0+60 .. t0+600: 只推进
        clock.advance(30)
        _run_sample(mgr, dry_run=True)
    assert GLOBAL_SERIES_KEY in mod._open_runs
    clock.advance(30)  # t0+630: flush 触发 -> 静默跳过 append, 行程照常移除
    _run_sample(mgr, dry_run=True)
    assert not (tmp_path / "qb-traffic").exists()  # 零目录零文件
    assert GLOBAL_SERIES_KEY not in mod._open_runs


def test_zero_run_requires_valid_totals_snapshot(tmp_path, monkeypatch):
    """零样本读数口径: 行程开启需要合法 totals 快照 —— totals 缺失的零样本不开新行程
    (空闲不出 null 行); 已开行程的零样本只推进 last_seen 无需重读 totals"""
    clock = _Clock()
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    rec = _active_torrent("HASH123")
    seed_store(mgr, [rec])
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)  # t0: 活跃 -> 建文件建条目
    rel = "torrents/HASH123.dat"
    before = _dat_lines(tmp_path, rel)
    rec.dlspeed = 0
    rec.upspeed = 0
    rec.downloaded = None  # all-time 对缺失 -> 不开新行程
    clock.advance(30)
    _run_sample(mgr)
    assert "torrent:HASH123" not in mod._open_runs
    assert _dat_lines(tmp_path, rel) == before  # 无新行(无 z 也无 null)
    # 对照: 已开行程的零样本无需重读 totals, 照常推进
    rec.downloaded, rec.uploaded = 5_000_000, 3_000_000
    clock.advance(30)
    _run_sample(mgr)
    assert mod._open_runs["torrent:HASH123"].samples == 1
    rec.downloaded = None
    clock.advance(30)
    _run_sample(mgr)
    run = mod._open_runs["torrent:HASH123"]
    assert run.samples == 2 and run.last_seen == clock.now  # 只推进, 不因 totals 缺失断行程


def test_global_always_opens_run_vs_torrent_gated(tmp_path, monkeypatch):
    """两系列零样本纪律对照(§3.2): 全局恒开行程(无 index 也不拦截, 文件由首次封口创建);
    单种 has_entry 拦截(从未传输不开行程不建文件)"""
    clock = _Clock()
    monkeypatch.setattr(ts_mod, "time", clock)
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _idle_state()
    seed_store(mgr, [FakeTorrent(hash="NEVER")])
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)  # t0: 首轮(小时封口扫描触发 -> 全局行程同轮 flush, 文件由此创建)
    lines = _dat_lines(tmp_path)
    zs = _z_parts(lines)
    assert len(zs) == 1 and zs[0][1] == zs[0][2] == str(int(clock.now))  # 全局零样本恒开 -> 首封口即建文件
    assert not (tmp_path / "qb-traffic" / "torrents" / "NEVER.dat").exists()  # 单种被 has_entry 拦截
    st = mod._get_store(mgr.ctx)
    assert not st.has_entry("NEVER")
    clock.advance(30)
    _run_sample(mgr)  # t0+30: 次轮无封口触发 -> 全局行程驻留内存, 单种仍无行程
    assert GLOBAL_SERIES_KEY in mod._open_runs and mod._open_runs[GLOBAL_SERIES_KEY].samples == 1
    assert "torrent:NEVER" not in mod._open_runs
