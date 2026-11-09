"""test_traffic_sample_interval_point 测试计划: 生效采样间隔单点(plan 26-11-10-0252 S3 / D10 / D11)

## 测试计划(每个测试函数一条)
- test_effective_sample_interval_pure_multiplication: 纯函数直乘 —— (1, 2.0)=2.0 / (15, 2.0)=30.0 / (85, 7.0)=595.0, 无取整
- test_apply_interval_beat_is_multiplier_times_main_tick: 采样器节拍 = multiplier x main_tick(小数 main_tick 亦直乘,
  旧失配 ceil + 告警语义已删, D10)
- test_apply_interval_main_tick_hot_change_closes_blocks: main_tick 热改 -> 生效值变化 -> 关块重开(签名 (multiplier,
  main_tick) 联动); multiplier 热改同判
- test_apply_interval_first_round_only_sets_baseline: 进程首轮只立基线不关块; 同配置重复调用不关块
- test_webui_raw_bucket_width_follows_effective_interval: webui raw 段栅格桶宽 = 生效间隔(与采样器同调单点)
- test_webui_disabled_empty_state_keeps_default_30s: 未启用空态仍走 DEFAULT_SAMPLE_INTERVAL_S=30.0(D11 保留)
"""
from types import SimpleNamespace

from auto_qb.config import QbTraffic
from auto_qb.core import traffic_grid as tg
from auto_qb.core.modules.traffic_sample_mod import TrafficSampleModule
from auto_qb.webui.server.traffic_qb import QbTrafficChartApi

from clock import FakeClock

from helpers import make_manager


def _mgr_with_traffic(tmp_path, main_tick: float, multiplier: int):
    """最小装配: 真实 manager(模块已注册) + 只覆盖 qb_traffic 与 main_tick 两处配置"""
    mgr = make_manager(str(tmp_path / "state.json"), clock=FakeClock(start=1_760_000_000))
    mgr.config.data_dir = str(tmp_path)
    mgr.config.main_tick = main_tick
    mgr.config.qb_traffic = QbTraffic(enabled=True, sample_interval_multiplier=multiplier)
    return mgr


def _spy_close(monkeypatch) -> list:
    """关块联动探针: 记录 _close_blocks_for_interval_change 调用次数"""
    calls = []
    orig = TrafficSampleModule._close_blocks_for_interval_change

    def spy(self):
        calls.append(True)
        return orig(self)

    monkeypatch.setattr(TrafficSampleModule, "_close_blocks_for_interval_change", spy)
    return calls


def test_effective_sample_interval_pure_multiplication():
    """生效间隔 = multiplier x main_tick 直乘, 无 ceil/无告警(D10 单点)"""
    assert tg.effective_sample_interval(1, 2.0) == 2.0
    assert tg.effective_sample_interval(15, 2.0) == 30.0
    assert tg.effective_sample_interval(85, 7.0) == 595.0
    assert tg.effective_sample_interval(1, 1.5) == 1.5  # 小数 main_tick 原样生效, 不取整


def test_apply_interval_beat_is_multiplier_times_main_tick(tmp_path):
    """采样器 _apply_interval 返回值即节拍: multiplier x main_tick"""
    mod = _mgr_with_traffic(tmp_path, main_tick=2.0, multiplier=15).host.get("qb_traffic")
    conf = mod._ctx.config.qb_traffic
    assert mod._apply_interval(conf) == 30.0
    assert mod._interval_signature == (15, 2.0)

    mod2 = _mgr_with_traffic(tmp_path / "b", main_tick=1.5, multiplier=1).host.get("qb_traffic")
    assert mod2._apply_interval(mod2._ctx.config.qb_traffic) == 1.5


def test_apply_interval_main_tick_hot_change_closes_blocks(tmp_path, monkeypatch):
    """main_tick / multiplier 热改 -> 生效值变化 -> 关块重开(签名 (multiplier, main_tick))"""
    mgr = _mgr_with_traffic(tmp_path, main_tick=2.0, multiplier=1)
    mod = mgr.host.get("qb_traffic")
    conf = mgr.config.qb_traffic
    calls = _spy_close(monkeypatch)

    assert mod._apply_interval(conf) == 2.0  # 首轮: 只立基线
    assert calls == []

    mgr.config.main_tick = 7.0  # 仅 main_tick 热改
    assert mod._apply_interval(conf) == 7.0
    assert calls == [True]
    assert mod._interval_signature == (1, 7.0)

    mgr.config.qb_traffic = QbTraffic(enabled=True, sample_interval_multiplier=3)  # 仅倍数热改
    assert mod._apply_interval(mgr.config.qb_traffic) == 21.0
    assert calls == [True, True]


def test_apply_interval_first_round_only_sets_baseline(tmp_path, monkeypatch):
    """进程首轮只立基线; 同配置重复调用不关块(生效值未变)"""
    mod = _mgr_with_traffic(tmp_path, main_tick=2.0, multiplier=15).host.get("qb_traffic")
    conf = mod._ctx.config.qb_traffic
    calls = _spy_close(monkeypatch)

    assert mod._apply_interval(conf) == 30.0
    assert mod._effective_interval == 30.0
    assert mod._apply_interval(conf) == 30.0
    assert calls == []


def _api(multiplier: int, main_tick: float) -> QbTrafficChartApi:
    """webui 读侧最小装配(只需 config.qb_traffic / config.main_tick / config.data_dir)"""
    cfg = SimpleNamespace(
        qb_traffic=QbTraffic(enabled=True, sample_interval_multiplier=multiplier),
        main_tick=main_tick,
        data_dir="",
    )
    return QbTrafficChartApi(SimpleNamespace(config=cfg))


def test_webui_raw_bucket_width_follows_effective_interval():
    """raw 段栅格桶宽 = 生效间隔(采样器与 webui 同调单点); 24h 窗受 MAX_RAW_BUCKETS 下限 30s"""
    api = _api(15, 2.0)
    assert api._grid("5m").interval == 30  # 5m 窗不受桶数上限影响
    assert api._meta(api._grid("5m"), stale=False)["interval_s"] == 30

    assert _api(1, 2.0)._grid("5m").interval == 2
    assert _api(85, 7.0)._grid("5m").interval == 595
    assert _api(15, 2.0)._grid("24h").interval == 30  # 86400/2880 = 30 下限, 恰等生效值
    assert _api(85, 7.0)._grid("24h").interval == 595


def test_webui_disabled_empty_state_keeps_default_30s():
    """未启用空态(qb_traffic 缺省 None): raw 桶宽仍为 DEFAULT_SAMPLE_INTERVAL_S=30.0(D11 保留)"""
    cfg = SimpleNamespace(qb_traffic=None, main_tick=7.0, data_dir="")
    api = QbTrafficChartApi(SimpleNamespace(config=cfg))
    assert api._grid("5m").interval == 30
    assert api._meta(api._grid("5m"), stale=False)["interval_s"] == 30
