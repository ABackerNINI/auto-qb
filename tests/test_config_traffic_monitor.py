"""test_config_traffic_monitor 测试计划: global_traffic_monitor 段(计划 26-10-16-0541 S6)

## 测试计划(每个测试函数一条)
- test_validate_absent_section_ok: 整段缺省(None)合法 -> 走默认值(enabled=false)
- test_validate_empty_dict_ok: 空段 {} 合法(全默认)
- test_validate_unknown_key_rejected: 未知键被拒(黄金法则 4)
- test_validate_bool_keys_reject_non_bool: enabled/subscribe/autostart 非 bool 聚合报错
- test_validate_tool_url_shape: tool_url 必须是非空、带主机名的 http(s) URL(空串/裸主机/非 http 均拒)
- test_validate_tool_token_path_must_be_str: tool_token_path 非字符串报错(空串合法)
- test_validate_notify_cooldown_bounds: notify_cooldown_s 须可解析为时间且 0~24H(负/超界拒, 0 合法)
- test_validate_valid_section_ok: 全键合法值一次通过
- test_loader_parses_explicit_values: 显式值按类型解析(bool/time), 与字段默认不同的值真正进入 Config
- test_loader_defaults_when_absent: 段缺省 -> 全部字段默认
- test_loader_non_dict_spec_defaults: 段值非字典(如字符串) -> 全默认(不抛)
"""
from pathlib import Path

import yaml

from auto_qb.config.loaders import load_global_traffic_monitor_config
from auto_qb.config.models import Config, GlobalTrafficMonitorConfig
from auto_qb.config.validation import KNOWN_GLOBAL_TRAFFIC_MONITOR_KEYS, validate_config


def _errors(section) -> list:
    return validate_config({"config": {"global_traffic_monitor": section}})


def test_validate_absent_section_ok():
    assert validate_config({"config": {}}) == []
    assert validate_config({"config": {"global_traffic_monitor": None}}) == []


def test_validate_empty_dict_ok():
    assert _errors({}) == []


def test_validate_unknown_key_rejected():
    errs = _errors({"enabled": "true", "bogus": "1"})
    assert any("未知键" in e and "bogus" in e for e in errs), errs
    # 已知键集合与 schema 单点一致(7 键口径的姊妹: 本段 6 键)
    assert KNOWN_GLOBAL_TRAFFIC_MONITOR_KEYS == {
        "enabled", "tool_url", "tool_token_path", "subscribe", "notify_cooldown_s", "autostart"
    }


def test_validate_bool_keys_reject_non_bool():
    errs = _errors({"enabled": "maybe", "subscribe": "x", "autostart": "y"})
    for key in ("enabled", "subscribe", "autostart"):
        assert any(f"config.global_traffic_monitor.{key}" in e for e in errs), (key, errs)


def test_validate_tool_url_shape():
    assert _errors({"tool_url": "http://127.0.0.1:8099"}) == []
    assert _errors({"tool_url": "https://gtm.local:9000"}) == []
    for bad in ("", "127.0.0.1:8099", "ftp://host/x", "http://"):
        errs = _errors({"tool_url": bad})
        assert any("config.global_traffic_monitor.tool_url" in e for e in errs), (bad, errs)


def test_validate_tool_token_path_must_be_str():
    assert _errors({"tool_token_path": ""}) == []
    assert _errors({"tool_token_path": "/tmp/monitor.token"}) == []
    errs = _errors({"tool_token_path": ["x"]})
    assert any("tool_token_path" in e for e in errs), errs


def test_validate_notify_cooldown_bounds():
    assert _errors({"notify_cooldown_s": "0S"}) == []
    assert _errors({"notify_cooldown_s": "10M"}) == []
    assert _errors({"notify_cooldown_s": "24H"}) == []
    assert any("notify_cooldown_s" in e for e in _errors({"notify_cooldown_s": "-1S"}))
    assert any("notify_cooldown_s" in e for e in _errors({"notify_cooldown_s": "48H"}))
    assert any("notify_cooldown_s" in e for e in _errors({"notify_cooldown_s": "abc"}))


def test_validate_valid_section_ok():
    assert _errors(
        {
            "enabled": "true",
            "tool_url": "http://127.0.0.1:8099",
            "tool_token_path": "/x/monitor.token",
            "subscribe": "false",
            "notify_cooldown_s": "5M",
            "autostart": "true",
        }
    ) == []


def test_loader_parses_explicit_values():
    cfg = load_global_traffic_monitor_config(
        {
            "enabled": "true",
            "tool_url": "http://192.0.2.1:9000",
            "tool_token_path": "/probe/monitor.token",
            "subscribe": "false",
            "notify_cooldown_s": "90S",
            "autostart": "true",
        }
    )
    assert cfg.enabled is True
    assert cfg.tool_url == "http://192.0.2.1:9000"
    assert cfg.tool_token_path == "/probe/monitor.token"
    assert cfg.subscribe is False
    assert cfg.notify_cooldown_s == 90.0
    assert cfg.autostart is True


def test_loader_defaults_when_absent():
    d = GlobalTrafficMonitorConfig()
    assert load_global_traffic_monitor_config(None) == d
    assert load_global_traffic_monitor_config({}) == d
    assert Config().global_traffic_monitor == d
    assert d.enabled is False and d.subscribe is True and d.autostart is False
    assert d.tool_url == "http://127.0.0.1:8099" and d.tool_token_path == ""
    assert d.notify_cooldown_s == 600.0


def test_loader_non_dict_spec_defaults():
    assert load_global_traffic_monitor_config("nonsense") == GlobalTrafficMonitorConfig()


def test_round_trip_through_load_config(tmp_path):
    """整段经 load_config 真链路(读文件 -> 剥空 -> 迁移 -> 校验 -> 解析)回读一致"""
    from auto_qb.config import load_config

    probe = {
        "config":
            {
                "global_traffic_monitor":
                    {
                        "enabled": "true",
                        "tool_url": "http://192.0.2.9:9100",
                        "tool_token_path": "/probe/t.token",
                        "subscribe": "false",
                        "notify_cooldown_s": "3M",
                        "autostart": "true",
                    }
            }
    }
    path = Path(tmp_path) / "cfg.yml"
    path.write_text(yaml.safe_dump(probe, allow_unicode=True), encoding="utf-8")
    cfg = load_config(str(path)).global_traffic_monitor
    assert (cfg.enabled, cfg.tool_url, cfg.tool_token_path) == (True, "http://192.0.2.9:9100", "/probe/t.token")
    assert (cfg.subscribe, cfg.notify_cooldown_s, cfg.autostart) == (False, 180.0, True)
