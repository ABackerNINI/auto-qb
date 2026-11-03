"""S3 配置守阵: 加载 / 校验 (黄金法则 4 聚合) / 范围 / bool 陷阱 / round-trip.

+ S7 (计划 26-10-17-1737 / D13): 时间/大小为复合串 —— 写侧只写 "30S"/"10MiB", 读侧兼容
  旧式裸数值 (按秒/字节平移), 旧值一次性迁移不丢语义、不误碰无旧值的文件。
+ T-02 (issue 26-10-30-0624): http_host 回环约束 —— 127.0.0.0/8 与 ::1 (及 localhost)
  放行, 非回环地址 (0.0.0.0/局域网/域名) 拒绝, 启动加载与 PUT /config 两入口共用。
全部用例 hermetic: tmp_path 落盘, 不碰真实工具数据目录。
"""

from __future__ import annotations

import hashlib
import os

import pytest
import yaml

from gtm.config import (
    Config,
    ConfigHolder,
    _KNOWN_FIELDS,
    _V2_FIELDS,
    config_to_payload,
    ensure_v2_overlay,
    load_config,
    migrate_legacy_config,
    save_config,
    v2_overlay_path,
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
    assert c.sample_rate_warn_bps == 1024**3  # S5: 默认 1GiB/s
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
    """旧式裸数值给时间字段仍合法 (D13 读侧兼容: 30 按「秒」平移)."""
    config, errors = validate_payload({"flush_interval_s": 30})
    assert errors == () and config is not None
    assert config.flush_interval_s == 30.0


# ---- S7/D13: 复合串契约 (写侧只写串, 读侧兼容旧值) ----


def test_validate_accepts_compound_strings() -> None:
    """时间/大小字段收复合串, 换算成运行期物理量 (秒 / 字节)."""
    config, errors = validate_payload(
        {
            "sample_interval": "2.5S",
            "flush_delta_bytes": "2MiB",
            "flush_interval_s": "1M",
            "lease_ttl_s": "3M",
            "heartbeat_interval_s": "1M",
            "notify_timeout_s": "500S",
            "notify_threshold_bytes": "512KiB",
            "sample_rate_warn_bps": "500MiB/s",
        }
    )
    assert errors == ()
    assert config is not None
    assert config.sample_interval == 2.5
    assert config.flush_delta_bytes == 2 * 1024**2
    assert config.flush_interval_s == 60.0
    assert config.lease_ttl_s == 180.0
    assert config.notify_threshold_bytes == 512 * 1024
    assert config.sample_rate_warn_bps == 500 * 1024**2


def test_validate_rate_field_requires_compound_string() -> None:
    """S5: sample_rate_warn_bps 只收 "数字+二进制单位/s"; 裸数值/缺 /s/十进制/0 一律聚合报错."""
    config, errors = validate_payload({"sample_rate_warn_bps": "1GiB/s"})
    assert errors == ()
    assert config is not None and config.sample_rate_warn_bps == 1024**3
    for bad in (1024**3, "1GiB", "1MB/s", "0MiB/s", "-1MiB/s", True, None):
        cfg, errs = validate_payload({"sample_rate_warn_bps": bad})
        assert cfg is None
        assert len(errs) == 1 and "sample_rate_warn_bps" in errs[0]


def test_validate_legacy_numbers_shift_by_semantics() -> None:
    """D13 之前盘上是裸数值: 5.0 -> 5 秒, 1048576 -> 1MiB (不是当成默认值/0)."""
    config, errors = validate_payload({"sample_interval": 5.0, "flush_delta_bytes": 1048576})
    assert errors == ()
    assert config is not None
    assert config.sample_interval == 5.0
    assert config.flush_delta_bytes == 1024**2


def test_validate_bad_unit_strings_aggregate() -> None:
    """串解析失败也要**聚合**报齐 (黄金法则 4), 且文案指出期望形态."""
    config, errors = validate_payload(
        {
            "sample_interval": "abc",
            "flush_delta_bytes": "10MB",  # 十进制单位不在白名单
            "lease_ttl_s": "5",
        }
    )
    assert config is None
    assert len(errors) == 3
    assert any("sample_interval" in e and "时间串" in e for e in errors)
    assert any("flush_delta_bytes" in e and "二进制单位" in e for e in errors)
    assert any("lease_ttl_s" in e for e in errors)


def test_validate_zero_duration_string_rejected() -> None:
    """0S 是合法串但语义上「必须为正」, 与旧数值 0 同一判决."""
    config, errors = validate_payload({"lease_ttl_s": "0S"})
    assert config is None
    assert any("期望正数" in e for e in errors)


def test_payload_only_contains_compound_strings(tmp_path) -> None:
    """写侧只写复合串: 盘上不得出现「数值 + 独立单位」的第二形态."""
    p = tmp_path / "config.yml"
    save_config(str(p), Config(sample_interval=2.5, flush_delta_bytes=2 * 1024**2))
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    assert raw["sample_interval"] == "2.5S"
    assert raw["flush_delta_bytes"] == "2MiB"
    assert raw["notify_threshold_bytes"] == "100MiB"
    assert raw["sample_rate_warn_bps"] == "1GiB/s"  # S5: 速率同样只写复合串
    assert raw["http_port"] == 0  # 非时间/大小字段保持原形态
    # 回显 (= PUT /config 与 GET /status 的 config) 与盘上同源: 取「能整除的最大单位」
    assert config_to_payload(Config())["lease_ttl_s"] == "3M"  # 180 秒
    assert config_to_payload(Config())["heartbeat_interval_s"] == "1M"  # 60 秒
    assert config_to_payload(Config())["sample_rate_warn_bps"] == "1GiB/s"


def test_migrate_legacy_config_rewrites_once(tmp_path) -> None:
    """旧式裸数值一次性改写为复合串, 语义不变; 再跑一次已无旧值 -> 不碰文件."""
    p = tmp_path / "config.yml"
    p.write_text("sample_interval: 2.5\nflush_delta_bytes: 1048576\n", encoding="utf-8")
    message = migrate_legacy_config(str(p))
    assert message and "sample_interval" in message and "flush_delta_bytes" in message
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    assert raw["sample_interval"] == "2.5S"
    assert raw["flush_delta_bytes"] == "1MiB"
    loaded, errors = load_config(str(p))
    assert errors == () and loaded is not None
    assert loaded.sample_interval == 2.5 and loaded.flush_delta_bytes == 1024**2
    # 幂等: 第二次不再改写 (没有旧值就不该动文件)
    before = p.read_bytes()
    assert migrate_legacy_config(str(p)) is None
    assert p.read_bytes() == before


def test_migrate_legacy_config_skips_canonical_file(tmp_path) -> None:
    """已经全是复合串 (或压根没这几个键) 的文件一个字节都不改."""
    p = tmp_path / "config.yml"
    p.write_text("sample_interval: 5S\nhttp_port: 9100\n", encoding="utf-8")
    before = p.read_bytes()
    assert migrate_legacy_config(str(p)) is None
    assert p.read_bytes() == before


def test_migrate_legacy_config_leaves_bad_values_to_fail_fast(tmp_path) -> None:
    """旧值解析不出来 -> 不改写, 让启动路径聚合报错 (不静默"修好"成默认值)."""
    p = tmp_path / "config.yml"
    p.write_text("sample_interval: [broken\n", encoding="utf-8")
    before = p.read_bytes()
    assert migrate_legacy_config(str(p)) is None
    assert p.read_bytes() == before


def test_migrate_legacy_config_missing_file(tmp_path) -> None:
    """没有 config.yml = 全新安装, 迁移是 no-op (不凭空造文件)."""
    p = tmp_path / "config.yml"
    assert migrate_legacy_config(str(p)) is None
    assert not p.exists()


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


# ---- 类型/边界出口 (26-10-21 覆盖率门禁 P2-T2.4) ----


def test_validate_payload_rejects_non_mapping() -> None:
    """载荷顶层不是映射 (list/str): 直接拒并说明收到的类型 (不做属性猜测)."""
    config, errors = validate_payload([("sample_interval", 5)])
    assert config is None
    assert len(errors) == 1 and "配置载荷必须是映射" in errors[0]
    assert "list" in errors[0]


@pytest.mark.parametrize(
    "payload,expect",
    [
        ({
            "http_port": True
        }, "期望数值, 收到布尔"),
        ({
            "flush_delta_bytes": False
        }, "期望数值, 收到布尔"),
        ({
            "sample_interval": True
        }, "期望数值, 收到布尔"),
    ],
)
def test_validate_rejects_bool_on_every_numeric_field(payload, expect) -> None:
    """bool 是 int 子类: 三类数值字段 (整数/大小/时间) 都必须显式拒绝 True/False."""
    config, errors = validate_payload(payload)
    assert config is None
    assert any(expect in e for e in errors), errors


def test_validate_rejects_non_finite_duration() -> None:
    """时间字段收到 inf: 拒绝 (有限数值才可调度; 否则 sleep(inf) 会永久挂住循环)."""
    config, errors = validate_payload({"sample_interval": float("inf")})
    assert config is None
    assert any("期望有限数值" in e for e in errors)


def test_validate_rejects_non_positive_size() -> None:
    """大小字段非正 (0/-1): 拒绝 (0 字节节流阈值等于每次采样都落盘, 语义上不成立)."""
    config, errors = validate_payload({"flush_delta_bytes": 0})
    assert config is None
    assert any("期望正数" in e for e in errors)


@pytest.mark.parametrize("value", ["", "   ", 123, None])
def test_validate_rejects_bad_string_fields(value) -> None:
    """字符串字段空/非串: 拒绝 (http_host 空串会让 bind 落到 0.0.0.0, 属安全事故)."""
    config, errors = validate_payload({"http_host": value})
    assert config is None
    assert any("期望非空字符串" in e for e in errors)


@pytest.mark.parametrize("value", ["127.0.0.1", "127.255.255.254", "::1", "localhost", "LocalHost"])
def test_validate_accepts_loopback_http_host(value) -> None:
    """http_host 回环约束放行面: 127.0.0.0/8 全段 + ::1 + 保留名 localhost (T-02)."""
    config, errors = validate_payload({"http_host": value})
    assert errors == ()
    assert config is not None and config.http_host == value


@pytest.mark.parametrize("value", ["0.0.0.0", "192.168.1.10", "10.0.0.2", "::", "::ffff:192.168.1.1", "example.com"])
def test_validate_rejects_non_loopback_http_host(value) -> None:
    """http_host 非回环: 拒绝 —— 放开即对 LAN 暴露单因素 Bearer 控制面 (token 明文落盘),
    「控制面强制绑定回环地址」的声明必须由校验层兑现, 不静默回落默认值."""
    config, errors = validate_payload({"http_host": value})
    assert config is None
    assert any("回环" in e for e in errors)


def test_load_config_rejects_non_loopback_http_host(tmp_path) -> None:
    """启动加载路径同样受约束: config.yml 写 0.0.0.0 -> fail-fast 聚合报错 (两入口共用校验)."""
    p = tmp_path / "config.yml"
    p.write_text("http_host: 0.0.0.0\n", encoding="utf-8")
    config, errors = load_config(str(p))
    assert config is None
    assert any("回环" in e for e in errors)


def test_load_config_oserror_reports_read_failure(tmp_path) -> None:
    """读配置遇 OSError (路径是目录): 返回读取失败而不是当「文件缺失」给默认值."""
    path = tmp_path / "config.yml"
    path.mkdir()
    config, errors = load_config(str(path))
    assert config is None
    assert len(errors) == 1 and "读取失败" in errors[0]


def test_migrate_legacy_config_ignores_non_mapping(tmp_path) -> None:
    """顶层是列表的 config.yml: 迁移不猜结构, 直接 no-op (留给启动路径报错)."""
    p = tmp_path / "config.yml"
    p.write_text("- sample_interval\n- 5\n", encoding="utf-8")
    assert migrate_legacy_config(str(p)) is None
    assert p.read_text(encoding="utf-8").startswith("- sample_interval")


def test_migrate_legacy_config_skips_rewrite_when_validation_fails(tmp_path) -> None:
    """旧值存在但校验不过 (端口越界): 不改写磁盘 (坏配置不在迁移路径里被"修好")."""
    p = tmp_path / "config.yml"
    p.write_text("sample_interval: 5.0\nhttp_port: 70000\n", encoding="utf-8")
    before = p.read_bytes()
    assert migrate_legacy_config(str(p)) is None
    assert p.read_bytes() == before


# ---- S6/D6: config.v2.yml overlay 配置升级 (§07, T23-T26) ----


def test_v2_overlay_path_is_same_directory() -> None:
    """overlay 与主配置同目录 (同卷 os.replace 才原子); 无扩展名也落到 config.v2.yml."""
    assert v2_overlay_path("config.yml") == "config.v2.yml"
    assert v2_overlay_path("config") == "config.v2.yml"


def test_ensure_overlay_creates_default_and_never_writes_main(tmp_path) -> None:
    """T23 首次缺失: 用默认值生成 overlay; 主 config.yml 不生成 (零改写)."""
    main = tmp_path / "config.yml"
    overlay = tmp_path / "config.v2.yml"
    message, errors = ensure_v2_overlay(str(main), str(overlay))
    assert errors == () and message and "创建" in message
    raw = yaml.safe_load(overlay.read_text(encoding="utf-8"))
    assert raw == {"sample_rate_warn_bps": "1GiB/s"}
    text = overlay.read_text(encoding="utf-8")
    assert "旧版本不会读取本文件" in text  # 文件头注释说明用途
    assert not main.exists()


def test_ensure_overlay_second_start_is_noop(tmp_path) -> None:
    """T23 重复启动幂等: 键齐全且相等 -> 不写盘, 内容与 mtime 都不变; 不产生 .bak."""
    main = tmp_path / "config.yml"
    overlay = tmp_path / "config.v2.yml"
    assert ensure_v2_overlay(str(main), str(overlay))[0]
    before_mtime = os.stat(overlay).st_mtime_ns
    before_bytes = overlay.read_bytes()
    message, errors = ensure_v2_overlay(str(main), str(overlay))
    assert message is None and errors == ()
    assert os.stat(overlay).st_mtime_ns == before_mtime
    assert overlay.read_bytes() == before_bytes
    assert not (tmp_path / "config.v2.yml.bak").exists()


def test_ensure_overlay_keeps_custom_value_across_startup(tmp_path) -> None:
    """启动路径 (config=None) 以合并后的内存值为准: 用户在 overlay 里调高的阈值不被默认值覆盖."""
    main = tmp_path / "config.yml"
    overlay = tmp_path / "config.v2.yml"
    overlay.write_text('sample_rate_warn_bps: "2GiB/s"\n', encoding="utf-8")
    before = overlay.read_bytes()
    message, errors = ensure_v2_overlay(str(main), str(overlay))
    assert message is None and errors == ()
    assert overlay.read_bytes() == before


def test_ensure_overlay_rewrites_mismatch_with_single_generation_backup(tmp_path) -> None:
    """值不等 -> 按内存值改写并留单世代 .bak (旧内容可恢复)."""
    main = tmp_path / "config.yml"
    overlay = tmp_path / "config.v2.yml"
    overlay.write_text('sample_rate_warn_bps: "500MiB/s"\n', encoding="utf-8")
    desired = Config(sample_rate_warn_bps=2 * 1024**3)
    message, errors = ensure_v2_overlay(str(main), str(overlay), desired)
    assert errors == () and message and "更新" in message
    assert yaml.safe_load(overlay.read_text(encoding="utf-8")) == {"sample_rate_warn_bps": "2GiB/s"}
    assert "500MiB/s" in (tmp_path / "config.v2.yml.bak").read_text(encoding="utf-8")


def test_ensure_overlay_fills_missing_key_and_backs_up_empty_file(tmp_path) -> None:
    """overlay 存在但缺键 (空文件): 补齐默认值, 改写前留 .bak."""
    main = tmp_path / "config.yml"
    overlay = tmp_path / "config.v2.yml"
    overlay.write_text("", encoding="utf-8")
    message, errors = ensure_v2_overlay(str(main), str(overlay))
    assert errors == () and message and "更新" in message
    assert yaml.safe_load(overlay.read_text(encoding="utf-8"))["sample_rate_warn_bps"] == "1GiB/s"
    assert (tmp_path / "config.v2.yml.bak").exists()


def test_ensure_overlay_unknown_key_fail_fast(tmp_path) -> None:
    """T26: overlay 未知键 -> fail-fast (带文件名与键名), 不写盘、不改原文件."""
    main = tmp_path / "config.yml"
    overlay = tmp_path / "config.v2.yml"
    overlay.write_text("foo: 1\n", encoding="utf-8")
    before = overlay.read_bytes()
    message, errors = ensure_v2_overlay(str(main), str(overlay))
    assert message is None
    assert any("config.v2.yml 未知键" in e and "foo" in e for e in errors)
    assert overlay.read_bytes() == before


def test_ensure_overlay_invalid_value_fail_fast(tmp_path) -> None:
    """overlay 值非法 (裸数值不符合速率复合串) -> 聚合 fail-fast, 不静默忽略."""
    main = tmp_path / "config.yml"
    overlay = tmp_path / "config.v2.yml"
    overlay.write_text("sample_rate_warn_bps: 1073741824\n", encoding="utf-8")
    message, errors = ensure_v2_overlay(str(main), str(overlay), Config())
    assert message is None
    assert len(errors) == 1 and "config.v2.yml" in errors[0] and "sample_rate_warn_bps" in errors[0]


def test_ensure_overlay_bad_yaml_or_unreadable_fail_fast(tmp_path) -> None:
    """T26: overlay 非法 YAML / 读失败 (路径是目录) -> fail-fast, 错误含文件名."""
    main = tmp_path / "config.yml"
    overlay = tmp_path / "config.v2.yml"
    overlay.write_text("sample_rate_warn_bps: [broken\n", encoding="utf-8")
    _, errors = ensure_v2_overlay(str(main), str(overlay))
    assert any("config.v2.yml 解析失败" in e for e in errors)
    overlay.unlink()
    overlay.mkdir()
    _, errors = ensure_v2_overlay(str(main), str(overlay), Config())
    assert any("config.v2.yml 读取失败" in e for e in errors)


def test_ensure_overlay_non_mapping_payload_fail_fast(tmp_path) -> None:
    """overlay 顶层非映射 (列表) -> fail-fast, 不猜结构."""
    main = tmp_path / "config.yml"
    overlay = tmp_path / "config.v2.yml"
    overlay.write_text("- sample_rate_warn_bps\n", encoding="utf-8")
    _, errors = ensure_v2_overlay(str(main), str(overlay), Config())
    assert any("载荷必须是映射" in e and "list" in e for e in errors)


def test_ensure_overlay_bad_main_config_fail_fast_without_writing(tmp_path) -> None:
    """主配置解析失败时 ensure 也 fail-fast, 不凭默认值先造 overlay."""
    main = tmp_path / "config.yml"
    overlay = tmp_path / "config.v2.yml"
    main.write_text("sample_interval: [broken\n", encoding="utf-8")
    message, errors = ensure_v2_overlay(str(main), str(overlay))
    assert message is None and any("config.yml 解析失败" in e for e in errors)
    assert not overlay.exists()


def test_ensure_overlay_write_failure_degrades_without_blocking(tmp_path, caplog) -> None:
    """目录缺失/只读: 写入失败只 WARNING, 返回 (None, ()) 让调用方用内存值继续."""
    main = tmp_path / "config.yml"
    overlay = tmp_path / "missing" / "config.v2.yml"
    message, errors = ensure_v2_overlay(str(main), str(overlay))
    assert message is None and errors == ()
    assert "config.v2.yml 写入失败" in caplog.text
    assert not overlay.exists()


def test_atomic_overlay_write_failure_cleans_tmp_and_keeps_old_file(tmp_path, monkeypatch, caplog) -> None:
    """写入中途失败 (fsync): 清理 <path>.tmp.<pid>, 旧 overlay 原样保留, 只 WARNING 降级."""
    import gtm.config as config_module

    main = tmp_path / "config.yml"
    overlay = tmp_path / "config.v2.yml"
    overlay.write_text('sample_rate_warn_bps: "500MiB/s"\n', encoding="utf-8")

    def boom(fd):
        raise OSError("fsync 模拟失败")

    monkeypatch.setattr(config_module.os, "fsync", boom)
    message, errors = ensure_v2_overlay(str(main), str(overlay), Config())
    assert message is None and errors == ()
    assert "config.v2.yml 写入失败" in caplog.text
    assert list(tmp_path.glob("config.v2.yml.tmp.*")) == []
    assert "500MiB/s" in overlay.read_text(encoding="utf-8")


def test_atomic_overlay_write_cleanup_failure_still_degrades(tmp_path, caplog) -> None:
    """临时路径被目录占住: open 失败 -> 清理也失败, 但 ensure 仍降级不抛."""
    main = tmp_path / "config.yml"
    overlay = tmp_path / "config.v2.yml"
    overlay.write_text('sample_rate_warn_bps: "500MiB/s"\n', encoding="utf-8")
    blocker = tmp_path / f"config.v2.yml.tmp.{os.getpid()}"
    blocker.mkdir()
    try:
        message, errors = ensure_v2_overlay(str(main), str(overlay), Config())
        assert message is None and errors == ()
        assert "config.v2.yml 写入失败" in caplog.text
        assert "500MiB/s" in overlay.read_text(encoding="utf-8")
    finally:
        blocker.rmdir()


def test_ensure_overlay_never_touches_existing_main(tmp_path) -> None:
    """主 config.yml 已存在时 ensure 一个字节都不改 (内容哈希与 mtime 不变, 无新键)."""
    main = tmp_path / "config.yml"
    overlay = tmp_path / "config.v2.yml"
    main.write_text("sample_interval: 5S\nhttp_port: 9100\n", encoding="utf-8")
    before_hash = hashlib.sha256(main.read_bytes()).hexdigest()
    before_mtime = os.stat(main).st_mtime_ns
    assert ensure_v2_overlay(str(main), str(overlay))[0]
    assert hashlib.sha256(main.read_bytes()).hexdigest() == before_hash
    assert os.stat(main).st_mtime_ns == before_mtime
    assert "sample_rate_warn_bps" not in main.read_text(encoding="utf-8")


def test_load_config_merges_overlay_and_overlay_wins(tmp_path) -> None:
    """load_config(path, overlay): overlay 同名键覆盖主配置, 其余键照常生效."""
    main = tmp_path / "config.yml"
    overlay = tmp_path / "config.v2.yml"
    main.write_text("http_port: 9100\nsample_rate_warn_bps: \"3GiB/s\"\n", encoding="utf-8")
    overlay.write_text('sample_rate_warn_bps: "1GiB/s"\n', encoding="utf-8")
    loaded, errors = load_config(str(main), str(overlay))
    assert errors == () and loaded is not None
    assert loaded.http_port == 9100
    assert loaded.sample_rate_warn_bps == 1024**3  # overlay 为准


def test_load_config_overlay_bad_yaml_or_non_mapping_fail_fast(tmp_path) -> None:
    """overlay 解析失败/顶层非映射都在 load 面 fail-fast (与主配置同级)."""
    main = tmp_path / "config.yml"
    overlay = tmp_path / "config.v2.yml"
    overlay.write_text("sample_rate_warn_bps: [broken\n", encoding="utf-8")
    loaded, errors = load_config(str(main), str(overlay))
    assert loaded is None and any("config.v2.yml 解析失败" in e for e in errors)
    overlay.write_text("- x\n", encoding="utf-8")
    loaded, errors = load_config(str(main), str(overlay))
    assert loaded is None and any("config.v2.yml 载荷必须是映射" in e for e in errors)


def test_load_config_overlay_non_mapping_main_still_fails(tmp_path) -> None:
    """主配置顶层非映射 + 给定 overlay: 仍按单文件路径的「必须是映射」报错."""
    main = tmp_path / "config.yml"
    overlay = tmp_path / "config.v2.yml"
    main.write_text("- sample_interval\n", encoding="utf-8")
    overlay.write_text('sample_rate_warn_bps: "1GiB/s"\n', encoding="utf-8")
    loaded, errors = load_config(str(main), str(overlay))
    assert loaded is None and any("配置载荷必须是映射" in e for e in errors)


def test_save_config_split_keeps_v2_keys_out_of_main(tmp_path) -> None:
    """T24 保存拆分: 先 overlay 后主配置; 主文件不含 sample_rate_warn_bps, 合并加载正确."""
    main = tmp_path / "config.yml"
    overlay = tmp_path / "config.v2.yml"
    cfg = Config(sample_interval=2.5, sample_rate_warn_bps=500 * 1024**2)
    save_config(str(main), cfg, str(overlay))
    main_raw = yaml.safe_load(main.read_text(encoding="utf-8"))
    assert "sample_rate_warn_bps" not in main_raw
    assert main_raw["sample_interval"] == "2.5S"
    overlay_raw = yaml.safe_load(overlay.read_text(encoding="utf-8"))
    assert overlay_raw == {"sample_rate_warn_bps": "500MiB/s"}
    loaded, errors = load_config(str(main), str(overlay))
    assert errors == () and loaded == cfg


def test_split_save_main_payload_passes_v1_known_fields(tmp_path) -> None:
    """T25 旧版本读取模拟: 主文件键集落在 v1 已知字段内 (无未知键 -> 退回旧二进制可启动)."""
    main = tmp_path / "config.yml"
    overlay = tmp_path / "config.v2.yml"
    save_config(str(main), Config(), str(overlay))
    main_raw = yaml.safe_load(main.read_text(encoding="utf-8"))
    v1_known = set(_KNOWN_FIELDS) - set(_V2_FIELDS)
    assert set(main_raw) == v1_known  # 全量回显里唯独缺本轮新增键
    assert "sample_rate_warn_bps" not in main_raw
    assert validate_payload(main_raw)[0] is not None  # 旧载荷按现行校验仍合法


def test_migrate_legacy_config_backs_up_before_rewrite(tmp_path) -> None:
    """D13 迁移改写主文件前留 config.yml.bak; 主文件仍不含新键 (回滚可读)."""
    p = tmp_path / "config.yml"
    p.write_text("sample_interval: 2.5\n", encoding="utf-8")
    message = migrate_legacy_config(str(p))
    assert message
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    assert raw["sample_interval"] == "2.5S"
    assert "sample_rate_warn_bps" not in raw
    bak = yaml.safe_load((tmp_path / "config.yml.bak").read_text(encoding="utf-8"))
    assert bak["sample_interval"] == 2.5  # 单世代备份保留改写前原文


def test_migrate_legacy_config_backup_failure_warns_but_rewrites(tmp_path, caplog) -> None:
    """备份目标被目录占住: 备份失败只 WARNING, 迁移仍完成 (不因备份阻断配置规范化)."""
    p = tmp_path / "config.yml"
    p.write_text("sample_interval: 2.5\n", encoding="utf-8")
    (tmp_path / "config.yml.bak").mkdir()
    message = migrate_legacy_config(str(p))
    assert message
    assert "配置备份失败" in caplog.text
    assert yaml.safe_load(p.read_text(encoding="utf-8"))["sample_interval"] == "2.5S"


def test_save_config_split_skips_overlay_rewrite_when_unchanged(tmp_path) -> None:
    """26-11-03 review 修 3: overlay 已存在且解析值与内存值相等 -> 跳过改写 (mtime 不变, 无新 .bak).

    与启动路径 ensure_v2_overlay 的「相等不写盘」(I3) 对齐: PUT /config 全量覆写时,
    用户只改主配置字段不应让 overlay 陪跑重写。值变了仍照常改写 (留单世代 .bak)。
    """
    main = tmp_path / "config.yml"
    overlay = tmp_path / "config.v2.yml"
    cfg = Config(sample_rate_warn_bps=500 * 1024**2)
    save_config(str(main), cfg, str(overlay))
    first_mtime = overlay.stat().st_mtime_ns
    bak = tmp_path / "config.v2.yml.bak"
    assert not bak.exists()  # 首次创建: 改写前无旧文件, 不产生 .bak
    save_config(str(main), cfg, str(overlay))
    assert overlay.stat().st_mtime_ns == first_mtime  # 幂等: 值未变不重写
    assert not bak.exists()  # 跳过改写连 .bak 都不陪跑
    changed = Config(sample_rate_warn_bps=1024**3)
    save_config(str(main), changed, str(overlay))
    assert overlay.stat().st_mtime_ns != first_mtime  # 值变了照常改写
    assert yaml.safe_load(overlay.read_text(encoding="utf-8")) == {"sample_rate_warn_bps": "1GiB/s"}
    loaded, errors = load_config(str(main), str(overlay))
    assert errors == () and loaded == changed
