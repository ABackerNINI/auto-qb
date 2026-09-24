"""test_hr_config 测试计划: hr_check 配置段(解析 / 校验 / 热重载分级)

配置是 fail-fast 的第一道闸门: 站点配了 hr_check 却没配 hr 段时, 保护会**静默失效**
(check_hr_condition 第一行 `if not self.tracker_conf.hr: return False`), 故必须在配置期拦下。

## 测试计划(每个测试函数一条)
- test_defaults_when_absent: 整段缺省 -> 全默认(功能关闭), 不报错
- test_global_section_parsed: 全局段解析(时间串 -> 秒 / 枚举归一 / channel 子段含 M2 新键)
- test_verified_ttl_default_is_none: verified_ttl 缺省为 None(由站点 refresh_interval 解算, 不在此处固化)
- test_site_section_parsed: 站点段解析(scope 归一为大写 / 覆盖键生效 / 超龄豁免线)
- test_completed_age_limit_range: 超龄豁免线 0(关闭)或 1D~3650D; 单位写错配置期拦下
- test_unknown_keys_aggregated: hr_check / channel / 站点 hr_check 的未知键一次性报错
- test_mode_requires_hr_section: mode != off 但缺 hr 段 -> 配置期直接报错(否则整站保护静默失效)
- test_mode_off_does_not_require_hr_section: mode=off 时不要求 hr 段(该站就是不走 HR)
- test_hr_page_url_required_and_absolute: 启用后 hr_page_url 必填且须为 http(s) 绝对地址
- test_download_path_requires_id_placeholder: download_path 缺 {id} 占位符报错
- test_scopes_restricted_to_known_lanes: 档位只允许 A/B/C/D 且不能为空
- test_scopes_minimum_is_a_b_c: A+B+C 是最小合法集合(少抓一档 = 该档会被误放行), D 可加可不加
- test_unknown_policy_enum: unknown_policy 只允许 hr / not-hr
- test_ranges_and_formats: 间隔下限 / 端口范围 / 时间窗格式 / 缺失率范围等聚合报错
- test_channel_extension_id_format: extension_id 只接受 32 位 a~p(形态错 = 写了也不会生效, 必须配置期拦下)
- test_channel_request_timeout_range: request_timeout 上下限(太短误杀正常取数 / 太长挂死取数线程)
- test_impact_hr_check_field_is_l0: hr_check 字段变更 -> L0 字段级路径
- test_impact_channel_field_is_l1: channel 子段变更 -> L1(端点监听身份, 要重挂)
- test_impact_shared_dir_is_l1: shared_dir 变更 -> L1(站点文件目录变了, 服务与线程要重建)
- test_impact_site_hr_check_is_l0: 站点 hr_check 变更 -> trackers.<站点>.hr_check 一条 L0
"""
import os

import pytest
import yaml

from auto_qb.config import ConfigError, load_config
from auto_qb.config.impact import LEVEL_L0, LEVEL_L1, diff_config_impacts
from auto_qb.config.models import Config
from auto_qb.config.validation import validate_config


def _write(tmp_path, cfg: dict) -> str:
    path = os.path.join(str(tmp_path), "config.yml")
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump({"config": cfg}, f, allow_unicode=True)
    return path


def _site(**hr_check) -> dict:
    site = {"domains": ["pt.example.com"], "hr": {"required_seeding_time": "3D"}}
    if hr_check:
        site["hr_check"] = hr_check
    return site


def _validate(cfg: dict) -> list:
    return validate_config({"config": cfg})


def test_defaults_when_absent(tmp_path):
    """整段缺省 -> 全默认(功能关闭), 不报错"""
    cfg = load_config(_write(tmp_path, {"trackers": {"s": {"domains": ["a.example"]}}}))
    assert cfg.hr_check.enabled is False
    assert cfg.hr_check.min_torrent_interval == 90.0
    assert cfg.hr_check.max_torrents_per_day == 60
    assert cfg.hr_check.unknown_policy == "hr"
    assert cfg.hr_check.channel.enabled is False
    assert cfg.hr_check.channel.port == 8788
    assert cfg.trackers["s"].hr_check is None


def test_global_section_parsed(tmp_path):
    """全局段解析: 时间串 -> 秒 / 枚举归一 / channel 子段"""
    cfg = load_config(
        _write(
            tmp_path, {
                "hr_check":
                    {
                        "enabled": "true",
                        "min_torrent_interval": "2M",
                        "max_torrents_per_hour": "6",
                        "max_torrents_per_day": "30",
                        "failure_threshold": "3",
                        "failure_cooldown": "6H",
                        "allow_window": "01:00-06:00",
                        "unknown_policy": "NOT-HR",
                        "verified_ttl": "8H",
                        "index_retention": "7D",
                        "max_download_retries": "2",
                        "channel_silence_warn": "3H",
                        "shared_dir": "//nas/share",
                        "lock_timeout": "5S",
                        "poll_interval": "2M",
                        "parse_missing_rate_max": "0.3",
                        "channel":
                            {
                                "enabled": "true",
                                "port": "8899",
                                "token": "abc",
                                "extension_id": "a" * 32,
                                "request_timeout": "90S",
                            },
                    },
            }
        )
    )
    hr_check = cfg.hr_check
    assert hr_check.enabled is True
    assert hr_check.min_torrent_interval == 120.0
    assert (hr_check.max_torrents_per_hour, hr_check.max_torrents_per_day) == (6, 30)
    assert hr_check.failure_cooldown == 6 * 3600.0
    assert hr_check.allow_window == "01:00-06:00"
    assert hr_check.unknown_policy == "not-hr"  # 枚举归一为小写
    assert hr_check.verified_ttl == 8 * 3600.0
    assert hr_check.index_retention == 7 * 86400.0
    assert hr_check.max_download_retries == 2
    assert hr_check.channel_silence_warn == 3 * 3600.0
    assert hr_check.shared_dir == "//nas/share"
    assert hr_check.lock_timeout == 5.0
    assert hr_check.poll_interval == 120.0
    assert hr_check.parse_missing_rate_max == 0.3
    assert (hr_check.channel.enabled, hr_check.channel.port, hr_check.channel.token) == (True, 8899, "abc")
    assert hr_check.channel.extension_id == "a" * 32
    assert hr_check.channel.request_timeout == 90.0


def test_verified_ttl_default_is_none(tmp_path):
    """verified_ttl 缺省为 None —— 由站点 refresh_interval 解算(单点见 HrRefreshService.verified_ttl_for)"""
    cfg = load_config(_write(tmp_path, {"hr_check": {"enabled": "true"}}))
    assert cfg.hr_check.verified_ttl is None


def test_site_section_parsed(tmp_path):
    """站点段解析: scope 归一为大写 / 站点覆盖键生效"""
    cfg = load_config(
        _write(
            tmp_path, {
                "hr_check": {
                    "enabled": "true"
                },
                "trackers":
                    {
                        "btschool":
                            _site(
                                mode="PARTIAL",
                                hr_page_url="https://pt.example.com/myhr.php",
                                hr_page_scopes=["a", "b", "c", "d"],
                                max_torrents_per_hour="3",
                                completed_age_limit="365D",
                            )
                    },
            }
        )
    )
    site = cfg.trackers["btschool"].hr_check
    assert site is not None
    assert site.mode == "partial"
    assert site.enabled is True
    assert site.hr_page_scopes == ["A", "B", "C", "D"]
    assert site.max_torrents_per_hour == 3
    assert site.completed_age_limit == 365 * 86400.0
    assert site.refresh_interval == 12 * 3600.0
    assert site.download_path == "/download.php?id={id}"
    assert site.adapter == "nexusphp"

    # 未配 max_torrents_per_hour 时保持 None(回退全局); 未配 completed_age_limit 时保持 0(关闭)
    cfg2 = load_config(
        _write(tmp_path, {
            "trackers": {
                "s": _site(mode="partial", hr_page_url="https://pt.example.com/myhr.php")
            },
        })
    )
    assert cfg2.trackers["s"].hr_check.max_torrents_per_hour is None
    assert cfg2.trackers["s"].hr_check.completed_age_limit == 0.0


def test_completed_age_limit_range():
    """超龄豁免线: 0(关闭)与 1D~3650D 合法; 单位写错(<1D, 如 365S)与离谱大值在配置期拦下

    <1D 几乎必然是单位笔误 —— 那等于把整站刚完成的种子集体豁免, 必须 fail-fast 而不是静默生效。
    """
    site = {"mode": "partial", "hr_page_url": "https://pt.example.com/x"}

    def errors_for(age) -> list:
        return _validate({"trackers": {"s": {**_site(), "hr_check": {**site, "completed_age_limit": age}}}})

    assert errors_for("365D") == []
    assert errors_for("0S") == [], "显式 0 = 关闭, 合法"
    assert errors_for("1D") == []
    assert any("completed_age_limit" in e for e in errors_for("365S")), errors_for("365S")
    assert any("completed_age_limit" in e for e in errors_for("4000D"))
    assert any("completed_age_limit" in e for e in errors_for("abc"))


def test_unknown_keys_aggregated():
    """hr_check / channel / 站点 hr_check 的未知键一次性报错(带着配置路径)"""
    errors = _validate(
        {
            "hr_check": {
                "bogus": "1",
                "channel": {
                    "bogus2": "1"
                }
            },
            "trackers":
                {
                    "s":
                        {
                            **_site(mode="partial", hr_page_url="https://pt.example.com/x"), "hr_check":
                                {
                                    "mode": "partial",
                                    "hr_page_url": "https://pt.example.com/x",
                                    "bogus3": "1"
                                }
                        }
                },
        }
    )
    text = "\n".join(errors)
    assert "config.hr_check: 未知键" in text and "bogus" in text
    assert "config.hr_check.channel: 未知键" in text and "bogus2" in text
    assert "config.trackers.s.hr_check: 未知键" in text and "bogus3" in text


def test_mode_requires_hr_section():
    """mode != off 但缺 hr 段 -> 配置期直接报错(否则 check_hr_condition 恒 False, 整站保护静默失效)"""
    for mode in ("partial", "all"):
        errors = _validate(
            {
                "trackers":
                    {
                        "s":
                            {
                                "domains": ["a.example"],
                                "hr_check": {
                                    "mode": mode,
                                    "hr_page_url": "https://pt.example.com/myhr.php"
                                }
                            }
                    },
            }
        )
        assert any("必须同时配置 hr 段" in e for e in errors), errors


def test_mode_off_does_not_require_hr_section():
    """mode=off 时不要求 hr 段(该站就是不走 HR)"""
    assert _validate({
        "trackers": {
            "s": {
                "domains": ["a.example"],
                "hr_check": {
                    "mode": "off"
                }
            }
        },
    }) == []


def test_hr_page_url_required_and_absolute():
    """启用后 hr_page_url 必填且须为 http(s) 绝对地址"""
    errors = _validate({"trackers": {"s": {**_site(), "hr_check": {"mode": "partial"}}}})
    assert any("缺少必填键 hr_page_url" in e for e in errors)
    errors = _validate(
        {"trackers": {
            "s": {
                **_site(), "hr_check": {
                    "mode": "partial",
                    "hr_page_url": "pt.example.com/myhr.php"
                }
            }
        }}
    )
    assert any("须为 http(s) 绝对地址" in e for e in errors)


def test_download_path_requires_id_placeholder():
    """download_path 缺 {id} 占位符报错(拼不出下载地址 = 永远取不到 infohash)"""
    errors = _validate(
        {
            "trackers":
                {
                    "s":
                        {
                            **_site(), "hr_check":
                                {
                                    "mode": "partial",
                                    "hr_page_url": "https://pt.example.com/x",
                                    "download_path": "/download.php"
                                }
                        }
                },
        }
    )
    assert any("必须包含 {id} 占位符" in e for e in errors)


@pytest.mark.parametrize(
    "scopes",
    [["A"], ["A", "B"], ["A", "B", "C", "X"], [], "A"],
)
def test_scopes_restricted_to_known_lanes(scopes):
    """档位只允许 A/B/C/D, 不能为空, 且**必须含 A+B+C**

    少抓一档会让该档种子在「完整刷新」里未列出而被误放行 —— 这一条是漏 HR 的直接来源。
    """
    errors = _validate(
        {
            "trackers":
                {
                    "s":
                        {
                            **_site(), "hr_check":
                                {
                                    "mode": "partial",
                                    "hr_page_url": "https://pt.example.com/x",
                                    "hr_page_scopes": scopes
                                }
                        }
                },
        }
    )
    assert any("hr_page_scopes" in e for e in errors), errors


def test_scopes_minimum_is_a_b_c():
    """A+B+C 是最小合法集合; 加不加 D(已免罪)都合法"""
    for scopes in (["A", "B", "C"], ["a", "b", "c"], ["A", "B", "C", "D"]):
        errors = _validate(
            {
                "trackers":
                    {
                        "s":
                            {
                                **_site(), "hr_check":
                                    {
                                        "mode": "partial",
                                        "hr_page_url": "https://pt.example.com/x",
                                        "hr_page_scopes": scopes
                                    }
                            }
                    },
            }
        )
        assert errors == [], (scopes, errors)


def test_unknown_policy_enum():
    """unknown_policy 只允许 hr / not-hr"""
    assert _validate({"hr_check": {"unknown_policy": "hr"}}) == []
    assert _validate({"hr_check": {"unknown_policy": "not-hr"}}) == []
    errors = _validate({"hr_check": {"unknown_policy": "maybe"}})
    assert any("unknown_policy" in e for e in errors)


def test_ranges_and_formats():
    """间隔下限 / 端口范围 / 时间窗格式 / 缺失率范围 / 重试上限 等聚合报错"""
    errors = _validate(
        {
            "hr_check":
                {
                    "min_torrent_interval": "1S",
                    "max_torrents_per_hour": "0",
                    "failure_threshold": "0",
                    "allow_window": "25:00-08:00",
                    "verified_ttl": "10S",
                    "index_retention": "1H",
                    "max_download_retries": "99",
                    "poll_interval": "0S",
                    "parse_missing_rate_max": "1.5",
                    "channel": {
                        "port": "99999",
                        "extension_id": "not-an-id",
                        "request_timeout": "1S",
                    },
                },
        }
    )
    text = "\n".join(errors)
    for needle in (
        "min_torrent_interval", "max_torrents_per_hour", "failure_threshold", "allow_window", "verified_ttl",
        "index_retention", "max_download_retries", "poll_interval", "parse_missing_rate_max", "channel.port",
        "channel.extension_id", "channel.request_timeout"
    ):
        assert needle in text, f"缺少 {needle} 的报错: {text}"


def test_channel_extension_id_format():
    """extension_id 只接受 32 位 a~p —— 形态错等于「配了也不生效」, 必须配置期拦下"""
    assert _validate({"hr_check": {"channel": {"extension_id": ""}}}) == [], "留空合法 = 靠 token 鉴权"
    assert _validate({"hr_check": {"channel": {"extension_id": "a" * 32}}}) == []
    for bad in ("q" * 32, "a" * 31, "A" * 32, "1" * 32):
        text = "\n".join(_validate({"hr_check": {"channel": {"extension_id": bad}}}))
        assert "extension_id" in text, f"{bad} 应被拦下"


def test_channel_request_timeout_range():
    """request_timeout 上下限: 太短会误杀正常取数(分钟级), 太长会让持锁线程长期挂住"""
    assert _validate({"hr_check": {"channel": {"request_timeout": "60S"}}}) == []
    for bad in ("1S", "2H"):
        text = "\n".join(_validate({"hr_check": {"channel": {"request_timeout": bad}}}))
        assert "request_timeout" in text, f"{bad} 应被拦下"


def test_allow_window_accepts_cross_midnight():
    """跨午夜时间窗合法(与 notify.quiet_hours 同款语法, 但语义相反)"""
    assert _validate({"hr_check": {"allow_window": "23:00-08:00"}}) == []


def test_impact_hr_check_field_is_l0():
    """hr_check 字段变更 -> 字段级 L0 路径(取数线程每轮现读, 替换 Config 对象即生效)"""
    old, new = Config(), Config()
    new.hr_check.min_torrent_interval = 30.0
    changes = diff_config_impacts(old, new)
    assert [(c.path, c.level) for c in changes] == [("hr_check.min_torrent_interval", LEVEL_L0)]

    old, new = Config(), Config()
    new.hr_check.enabled = True
    assert [(c.path, c.level) for c in diff_config_impacts(old, new)] == [("hr_check.enabled", LEVEL_L0)]
    assert diff_config_impacts(Config(), Config()) == []


def test_impact_channel_field_is_l1():
    """channel 子段变更 -> L1(端点监听身份变了, 必须「先停旧、等线程退出、再启新」重挂)

    整段一条(不拆子字段): `hr_check.channel` 里任一字段变都意味着要重绑端口。
    """
    old, new = Config(), Config()
    new.hr_check.channel.port = 9999
    assert [(c.path, c.level) for c in diff_config_impacts(old, new)] == [("hr_check.channel", LEVEL_L1)]

    old, new = Config(), Config()
    new.hr_check.channel.enabled = True
    assert [(c.path, c.level) for c in diff_config_impacts(old, new)] == [("hr_check.channel", LEVEL_L1)]

    old, new = Config(), Config()
    new.hr_check.channel.token = "given"
    assert [(c.path, c.level) for c in diff_config_impacts(old, new)] == [("hr_check.channel", LEVEL_L1)]


def test_impact_shared_dir_is_l1():
    """shared_dir 变更 -> L1: 站点文件目录变了, 服务与取数线程得用新目录重建"""
    old, new = Config(), Config()
    new.hr_check.shared_dir = "//nas/share"
    assert [(c.path, c.level) for c in diff_config_impacts(old, new)] == [("hr_check.shared_dir", LEVEL_L1)]


def test_impact_site_hr_check_is_l0():
    """站点 hr_check 变更 -> trackers.<站点>.hr_check 一条 L0; 新增站点仍为整项 L2"""
    changes = diff_config_impacts(Config(), _config_with("partial"))
    assert [(c.path, c.level) for c in changes] == [("trackers.s", "L2")]

    other = diff_config_impacts(_config_with("partial"), _config_with("all"))
    assert [(c.path, c.level) for c in other] == [("trackers.s.hr_check", LEVEL_L0)]


def _tracker_with_hr_check(mode: str):
    from auto_qb.config.models import SiteHrCheckConfig, TrackerConfig

    return TrackerConfig(
        name="s",
        domains=["a.example"],
        hr_check=SiteHrCheckConfig(mode=mode, hr_page_url="https://pt.example.com/x"),
    )


def _config_with(mode: str) -> Config:
    cfg = Config()
    cfg.trackers["s"] = _tracker_with_hr_check(mode)
    return cfg


def test_config_error_message_points_to_section(tmp_path):
    """校验失败经 ConfigError 抛出, 消息里带具体路径(便于用户定位)"""
    with pytest.raises(ConfigError) as excinfo:
        load_config(_write(tmp_path, {
            "trackers": {
                "s": {
                    **_site(), "hr_check": {
                        "mode": "partial"
                    }
                }
            },
        }))
    assert "config.trackers.s.hr_check" in str(excinfo.value)
