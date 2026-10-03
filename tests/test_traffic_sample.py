"""test_traffic_sample 测试计划: qB 口径流量采样器(plan 26-10-03-0946 方案C P1 采样器核心 + §06 配置键)

## 测试计划(每个测试函数一条)
- test_qb_traffic_config_absent_means_disabled: 键组缺省 -> config.qb_traffic 为 None(未启用)
- test_qb_traffic_config_parses_sample: 完整样例解析(enabled/三个时间键换算成秒)
- test_qb_traffic_config_partial_falls_back_to_defaults: 部分键缺省回退 QbTraffic 默认值
- test_qb_traffic_config_rejects_bad_section: 段非 dict / 未知键 / enabled 非布尔
- test_qb_traffic_config_bounds_matrix: 四时间/布尔键边界矩阵(15S~10M / 1H~72H / 7D~90D 恰好压线收, 压线外拒)
- test_sample_task_registered_when_enabled: enabled=true -> start 创建 qb_traffic_sample 全局任务(interval=采样间隔)
- test_sample_task_not_registered_when_disabled: enabled=false 与键组缺省(None)两种情形均不建任务
- test_sample_task_reregisters_on_queue_rebuilt: L2 队列重建 -> 按新配置重入队(换 interval/启用/停用三向)
- test_sampling_runs_on_caller_thread: 采样在调用 run_due 的线程(主循环线程)内同步执行, 模块不建线程(单写线程不变式)
- test_first_sample_only_establishes_baseline: 首个采样只立基线不出增量(首窗 null), 次轮出正常增量
- test_counter_rollback_records_reset_no_negative: 模拟 qB 重启(计数器回落) -> 不产负增量、增量记 null、基线更新为 cur、INFO 记重置
- test_disconnect_produces_null_point: qB 断连(store.client None) -> 全局 null 点、单种不产点、基线不动
- test_missing_fields_produce_null_point_not_zero: server_state 关键字段缺失/空值 -> null 点(不写 0)且基线不推进
- test_torrent_active_filter_zero_rows_when_idle: 空闲种子零采样行; 活跃种子照常采样
- test_disabled_at_runtime_handler_noop: 任务已注册后运行期关闭 -> handler 短路不采样(任务保留)
- test_sampling_creates_no_files_or_dirs: enabled=true 采样全程零新建文件/目录(P1 纯内存)
- test_module_contract: name/sections 声明正确且被装配清单认领
"""
import io
import logging
import threading

import yaml

from auto_qb.config import QbTraffic, load_config
from auto_qb.config.validation import validate_config
from auto_qb.core.modules.traffic_sample_mod import GLOBAL_SERIES_KEY, TASK_NAME, TrafficSampleModule
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
    # 合法: 上下边界恰好压线(15S~10M / 1H~72H / 7D~90D)
    ok = validate_config(
        _cfg_dict({
            "enabled": "true",
            "sample_interval": "15S",
            "raw_window": "1H",
            "rollup_window": "7D",
        })
    )
    assert ok == [], ok
    ok = validate_config(
        _cfg_dict({
            "enabled": "false",
            "sample_interval": "10M",
            "raw_window": "72H",
            "rollup_window": "90D",
        })
    )
    assert ok == [], ok
    # 越界: 各键压线外一秒即拒
    bad = validate_config(_cfg_dict({"sample_interval": "14S"}))
    assert any("sample_interval" in e for e in bad), bad
    bad = validate_config(_cfg_dict({"sample_interval": "601S"}))
    assert any("sample_interval" in e for e in bad), bad
    bad = validate_config(_cfg_dict({"raw_window": "30M"}))
    assert any("raw_window" in e for e in bad), bad
    bad = validate_config(_cfg_dict({"raw_window": "73H"}))
    assert any("raw_window" in e for e in bad), bad
    bad = validate_config(_cfg_dict({"rollup_window": "6D"}))
    assert any("rollup_window" in e for e in bad), bad
    bad = validate_config(_cfg_dict({"rollup_window": "91D"}))
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
    """活跃过滤: 空闲种子零采样行; 活跃(dlspeed>0 or upspeed>0)才采(§03.2)"""
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    seed_store(
        mgr,
        [
            _active_torrent("DL_ACTIVE", dlspeed=100, upspeed=0),  # 仅下载活跃
            _active_torrent("UL_ACTIVE", dlspeed=0, upspeed=200),  # 仅上传活跃
            FakeTorrent(hash="IDLE1"),  # 全空闲
            _active_torrent("IDLE2", dlspeed=0, upspeed=0),  # 显式 0 = 空闲
        ],
    )
    mod = mgr.host.get("qb_traffic")
    _run_sample(mgr)
    assert "torrent:DL_ACTIVE" in mod.latest and "torrent:UL_ACTIVE" in mod.latest
    assert "torrent:IDLE1" not in mod.latest and "torrent:IDLE2" not in mod.latest  # 空闲零采样行
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


def test_sampling_creates_no_files_or_dirs(tmp_path):
    """enabled=true 采样全程零新建文件/目录(P1 纯内存, 黄金法则 2)"""
    mgr = _mgr_with_traffic(tmp_path, QbTraffic(enabled=True, sample_interval=30))
    mgr.store.server_state = _ss()
    seed_store(mgr, [_active_torrent()])
    before = sorted(str(p) for p in tmp_path.rglob("*"))
    _run_sample(mgr)
    _run_sample(mgr)
    after = sorted(str(p) for p in tmp_path.rglob("*"))
    assert before == after


def test_module_contract(tmp_path):
    """模块契约: name=qb_traffic / sections 声明 qb_traffic 且被装配清单认领"""
    mgr = _mgr_with_traffic(tmp_path, None)
    mod = mgr.host.get("qb_traffic")
    assert mod is not None and mod.name == "qb_traffic"
    assert mod.sections() == ("qb_traffic", )
    assert "qb_traffic" in mgr.host.claimed_sections()
