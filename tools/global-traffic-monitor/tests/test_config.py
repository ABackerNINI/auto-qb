"""S3 配置守阵: 加载 / 校验 (黄金法则 4 聚合) / 范围 / bool 陷阱 / round-trip.

设计单点: memory-bank/plans/26-10-16-0541-plan-global-traffic-monitor.html (S3).
全部用例 hermetic: tmp_path 落盘, 不碰真实工具数据目录。
"""

from __future__ import annotations

import pytest

from gtm.config import (
    Config,
    ConfigHolder,
    load_config,
    save_config,
    validate_payload,
)


def test_defaults_match_plan_section_05() -> None:
    """默认值与计划 §05 参数表逐项一致 (sample 5s / flush 1MiB+30s / notify 100MiB /
    http_port 0 随机 (S13/D9) / lease 180s / heartbeat 60s / notify_timeout 3s /
    适配器空列表 / autostart true (S14/D13))."""
    c = Config()
    assert c.sample_interval == 5.0
    assert c.flush_delta_bytes == 1024 * 1024
    assert c.flush_interval_s == 30.0
    assert c.notify_threshold_bytes == 100 * 1024 * 1024
    assert c.http_host == "127.0.0.1"
    assert c.http_port == 0
    assert c.lease_ttl_s == 180.0
    assert c.heartbeat_interval_s == 60.0
    assert c.notify_timeout_s == 3.0
    assert c.adapter_include == () and c.adapter_exclude == ()
    assert c.autostart is True  # 未显式关过 = 默认真 (run --autostart 会注册)


def test_load_missing_file_returns_defaults(tmp_path) -> None:
    """config.yml 不存在 = 空载荷 = 默认配置 (全新安装语义, 不报错)."""
    config, errors = load_config(str(tmp_path / "nope.yml"))
    assert errors == ()
    assert config == Config()


def test_load_empty_file_returns_defaults(tmp_path) -> None:
    """空文件 (yaml None) = 默认配置."""
    p = tmp_path / "config.yml"
    p.write_text("", encoding="utf-8")
    config, errors = load_config(str(p))
    assert errors == ()
    assert config == Config()


def test_load_valid_yaml(tmp_path) -> None:
    p = tmp_path / "config.yml"
    p.write_text(
        "sample_interval: 2.5\nhttp_port: 9100\nadapter_exclude:\n  - 'vmnet.*'\n  - 'vethernet.*'\n",
        encoding="utf-8",
    )
    config, errors = load_config(str(p))
    assert errors == ()
    assert config is not None
    assert config.sample_interval == 2.5
    assert config.http_port == 9100
    assert config.adapter_exclude == ("vmnet.*", "vethernet.*")


def test_load_bad_yaml_reports_error(tmp_path) -> None:
    p = tmp_path / "config.yml"
    p.write_text("sample_interval: [unclosed\n", encoding="utf-8")
    config, errors = load_config(str(p))
    assert config is None
    assert len(errors) == 1 and "YAML" in errors[0]


def test_validate_unknown_key_rejected() -> None:
    """未知键拒绝 (黄金法则 4: 不静默忽略拼写错误/过期键)."""
    config, errors = validate_payload({"sample_interavl": 5})
    assert config is None
    assert len(errors) == 1 and "sample_interavl" in errors[0]


def test_validate_bool_is_not_number() -> None:
    """bool 是 int 子类陷阱: sample_interval: true 必须拒绝 (不是 5)."""
    config, errors = validate_payload({"sample_interval": True})
    assert config is None
    assert any("布尔" in e for e in errors)


def test_validate_autostart_bool_field() -> None:
    """布尔字段 autostart (S14/D13): 只收真 bool —— 0/1/"true" 一律拒。

    反向对称于数值字段拒 bool: 「用户显式关过」是语义事件, 写成 0/1 会让读侧
    猜不透 (黄金法则 4: 不静默猜测), 故只认 YAML 真布尔。
    """
    assert validate_payload({"autostart": False})[0].autostart is False
    assert validate_payload({"autostart": True})[0].autostart is True
    for bad in (1, 0, "true", None):
        config, errors = validate_payload({"autostart": bad})
        assert config is None and any("autostart" in e and "布尔" in e for e in errors)


def test_validate_type_mismatch() -> None:
    config, errors = validate_payload({"http_port": "8099"})
    assert config is None
    assert any("期望整数" in e for e in errors)


def test_validate_non_positive_rejected() -> None:
    config, errors = validate_payload({"sample_interval": 0, "flush_interval_s": -1})
    assert config is None
    assert len(errors) == 2  # 聚合: 两个错一次报齐


def test_validate_port_range() -> None:
    """端口区间 0-65535: 0 合法 = 内核分配随机端口 (S13/D9); 负/超上限拒绝."""
    assert validate_payload({"http_port": 0})[0] is not None  # 0 合法 (随机端口)
    assert validate_payload({"http_port": 65536})[0] is None
    assert validate_payload({"http_port": -1})[0] is None
    assert validate_payload({"http_port": 8099})[0] is not None


def test_validate_aggregates_all_errors() -> None:
    """黄金法则 4: 全量校验聚合 —— 未知键 + 类型 + 范围 + bool 陷阱一次报齐."""
    config, errors = validate_payload(
        {
            "unknown_key": 1,
            "sample_interval": True,
            "http_port": 99999,
            "lease_ttl_s": 0,
        }
    )
    assert config is None
    assert len(errors) == 4


def test_validate_adapter_lists() -> None:
    config, errors = validate_payload({"adapter_include": ["eth.*"]})
    assert errors == () and config is not None
    assert config.adapter_include == ("eth.*", )
    # 非字符串元素拒绝
    assert validate_payload({"adapter_include": [1]})[0] is None


def test_validate_invalid_regex_rejected() -> None:
    """非法正则 (未闭合括号) 聚合拒绝 —— 到不了采样循环杀线程 (S3 实测坑)."""
    config, errors = validate_payload({"adapter_exclude": ["vmnet.*", "[unclosed"]})
    assert config is None
    assert any("非法正则" in e for e in errors)


def test_validate_float_from_int_ok() -> None:
    """整数载荷给浮点字段合法 (YAML 里 30 就是 int)."""
    config, errors = validate_payload({"flush_interval_s": 30})
    assert errors == () and config is not None
    assert config.flush_interval_s == 30.0


def test_save_load_round_trip(tmp_path) -> None:
    config = Config(sample_interval=2.5, http_port=9100, adapter_exclude=("vmnet.*", ))
    p = str(tmp_path / "config.yml")
    save_config(p, config)
    loaded, errors = load_config(p)
    assert errors == ()
    assert loaded == config


def test_save_is_atomic_no_tmp_leftover(tmp_path) -> None:
    """save 走 atomic_write_text: 成功后无临时文件残留."""
    save_config(str(tmp_path / "config.yml"), Config())
    leftovers = [q.name for q in tmp_path.iterdir() if q.name != "config.yml"]
    assert leftovers == []


def test_config_holder_replace() -> None:
    holder = ConfigHolder(Config())
    assert holder.current.sample_interval == 5.0
    holder.replace(Config(sample_interval=1.0))
    assert holder.current.sample_interval == 1.0
