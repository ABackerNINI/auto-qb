"""test_traffic_source_paths 测试计划: 取数路径解析单点(计划 26-10-17-0339 R2/D20)

> 旧 `TrafficSourceConfig.active_dat_path()` 已随 R2 退休: 工具来源的 dat 路径不再是配置事实,
> 而是工具运行期报在发现指针里的 data_dir。本文件覆盖唯一入口
> `core.traffic_source.paths.dat_path(config)` 的两条分支与报错文案。

## 测试计划(每个测试函数一条)
- test_dat_file_name_is_cross_package_contract: 文件名常量为 history_traffic.dat(工具侧 storage 同源)
- test_dat_path_traffic_monitor: provider=traffic_monitor -> traffic_monitor.dat_path(去空白)
- test_dat_path_global_joins_pointer_data_dir: provider=global -> 指针 data_dir + 契约文件名
- test_dat_path_global_without_pointer: 指针缺失 -> ""(不猜、不回退 TM 文件)
- test_dat_path_global_pointer_without_data_dir: 指针在但 data_dir 空 -> ""
- test_dat_path_provider_is_exclusive: 两来源参数并存时只认 provider 选中那个(D1 严格互斥)
- test_dat_path_tolerates_missing_section: 段缺失(桩配置) -> ""(不抛)
- test_unavailable_reason_branches: 文案按 provider 分支, 与取数分支同源
"""
import json
import os
from types import SimpleNamespace

from auto_qb.core.traffic_source import agent, paths
from auto_qb.config.models import TrafficSourceConfig


def _cfg(ts) -> SimpleNamespace:
    """把 traffic_source 段包成"像 Config"的最小对象(dat_path 只读 .traffic_source)"""
    return SimpleNamespace(traffic_source=ts)


def _write_pointer(tmp_path, monkeypatch, payload: dict) -> None:
    path = tmp_path / agent.ENDPOINT_FILE_NAME
    path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(agent, "endpoint_path", lambda: str(path))


def _pointer_payload(data_dir: str) -> dict:
    """最小合法指针(schema 匹配 + 三关键字段非空)"""
    return {
        "schema": agent.ENDPOINT_SCHEMA,
        "host": "127.0.0.1",
        "port": 14300,
        "token_path": "/tmp/monitor.token",
        "data_dir": data_dir,
    }


def test_dat_file_name_is_cross_package_contract():
    # 跨包契约: 与 tools/global-traffic-monitor/src/gtm/storage.py 的历史文件名同源
    assert paths.DAT_FILE_NAME == "history_traffic.dat"


def test_dat_path_traffic_monitor():
    ts = TrafficSourceConfig(provider="traffic_monitor")
    ts.traffic_monitor.dat_path = "  /x/history_traffic.dat  "
    assert paths.dat_path(_cfg(ts)) == "/x/history_traffic.dat"
    assert paths.dat_path(_cfg(TrafficSourceConfig())) == ""


def test_dat_path_global_joins_pointer_data_dir(tmp_path, monkeypatch):
    _write_pointer(tmp_path, monkeypatch, _pointer_payload("/opt/gtm/data"))
    ts = TrafficSourceConfig(provider="global_traffic_monitor")
    assert paths.dat_path(_cfg(ts)) == os.path.join("/opt/gtm/data", "history_traffic.dat")


def test_dat_path_global_without_pointer(tmp_path, monkeypatch):
    """指针缺失(工具优雅退出会删它) -> 空; 绝不回退到并存的 TM 文件(D1 不静默回退)"""
    monkeypatch.setattr(agent, "endpoint_path", lambda: str(tmp_path / "absent.json"))
    ts = TrafficSourceConfig(provider="global_traffic_monitor")
    ts.traffic_monitor.dat_path = "/tm/history_traffic.dat"
    assert paths.dat_path(_cfg(ts)) == ""


def test_dat_path_global_pointer_without_data_dir(tmp_path, monkeypatch):
    _write_pointer(tmp_path, monkeypatch, _pointer_payload(""))
    ts = TrafficSourceConfig(provider="global_traffic_monitor")
    assert paths.dat_path(_cfg(ts)) == ""


def test_dat_path_provider_is_exclusive(tmp_path, monkeypatch):
    """两来源参数并存是常态(切来源不丢另一侧), 互斥必须落在取数单点上"""
    _write_pointer(tmp_path, monkeypatch, _pointer_payload("/tool/data"))
    ts = TrafficSourceConfig(provider="traffic_monitor")
    ts.traffic_monitor.dat_path = "/tm/history_traffic.dat"
    assert paths.dat_path(_cfg(ts)) == "/tm/history_traffic.dat"

    ts.provider = "global_traffic_monitor"
    assert paths.dat_path(_cfg(ts)) == os.path.join("/tool/data", "history_traffic.dat")


def test_dat_path_tolerates_missing_section():
    # 桩配置/轻量调用方没有 traffic_source 段 -> 按"未配置"处理, 不抛
    assert paths.dat_path(SimpleNamespace()) == ""
    assert paths.unavailable_reason(SimpleNamespace()).startswith("数据源未配置")


def test_unavailable_reason_branches():
    tm = _cfg(TrafficSourceConfig(provider="traffic_monitor"))
    assert paths.unavailable_reason(tm).startswith("数据源未配置")
    assert "traffic_monitor.dat_path" in paths.unavailable_reason(tm)

    tool = _cfg(TrafficSourceConfig(provider="global_traffic_monitor"))
    reason = paths.unavailable_reason(tool)
    assert "全局流量监视器" in reason and "指针" in reason
    # 工具来源的文案不许再提 data_dir(该键已删, 提到就会把人指到不存在的配置项)
    assert "data_dir" not in reason
