"""test_hr_config 测试计划: hr_check 配置段(解析 / 校验 / 站点绑定 / 热重载分级)

配置是 fail-fast 的第一道闸门: 站点启用(mode != off)却没配 hr 段时, 保护会**静默失效**
(check_hr_condition 第一行 `if not self.tracker_conf.hr: return False`), 故必须在配置期拦下。

站点配置收敛(计划 26-09-27-1318 REV2)后: 站点启用与微调的唯一配置源是 `hr_check.sites.<档案 id>`
(键 = 内置站点档案 id, 见 config/site_presets.py); 旧键 `trackers.<站点>.hr_check` 兼容接受并
等价迁移 —— 本文件同时是**生产兼容回归锚**(现网 BTSchool 旧键形态不改一字, 加载结果与迁移前一致)。

## 测试计划(每个测试函数一条)
- test_defaults_when_absent: 整段缺省 -> 全默认(功能关闭), 不报错
- test_global_section_parsed: 全局段解析(时间串 -> 秒 / 枚举归一 / channel 子段)
- test_verified_ttl_default_is_none: verified_ttl 缺省为 None(由站点 refresh_interval 解算, 不在此处固化)
- test_sites_entry_parsed: sites 条目解析 + 绑定派生(scope 归一 / 微调覆盖 / 档案四键来自档案)
- test_page_url_derived_from_preset: HR 页地址按命中域名 + 档案 page_path 推算(btschool / carpt 两档)
- test_completed_age_limit_range: 超龄豁免线 0(关闭)或 1D~3650D; 单位写错配置期拦下
- test_scopes_restricted_to_known_lanes: 档位只允许 A/B/C/D 且不能为空
- test_scopes_minimum_is_a_b_c: A+B+C 是最小合法集合(少抓一档 = 该档会被误放行), D 可加可不加
- test_preset_id_must_be_registered: 未登记档案 id 报错 + 文案含已支持清单
- test_unbound_site_errors: 已启用但域名绑不上任何站点 -> 报错并指路
- test_binding_must_be_unique: 域名重叠绑到多个站点 -> 报错
- test_bound_site_requires_hr_section: 新位置启用但绑定站点缺 hr 段 -> 报错
- test_legacy_mode_requires_hr_section: 旧键 mode != off 且缺 hr 段 -> 同口径报错(兼容路径)
- test_mode_off_does_not_require_hr_section: mode=off 时不要求 hr 段(两个位置都不要求)
- test_legacy_equivalent_migration: 生产兼容回归锚 —— 现网 BTSchool 旧键形态加载结果与迁移前一致
- test_legacy_preset_keys_are_discarded: 旧键四个档案键读取后丢弃, 值一律以档案为准
- test_new_position_wins_over_legacy: 新旧并存 -> 新位置获胜
- test_legacy_unsupported_site_errors: 旧键启用但域名绑不上档案 -> 报未支持 + 已支持清单
- test_legacy_unknown_subkeys_accepted: 旧键未知子键兼容接受(仅校 mode)
- test_unknown_keys_aggregated: hr_check / channel / sites 条目的未知键一次性报错
- test_unknown_policy_enum: unknown_policy 只允许 hr / not-hr
- test_ranges_and_formats: 间隔下限 / 端口范围 / 时间窗格式 / 缺失率范围等聚合报错
- test_channel_extension_id_format: extension_id 只接受 32 位 a~p(形态错 = 写了也不会生效, 必须配置期拦下)
- test_channel_request_timeout_range: request_timeout 上下限(太短误杀正常取数 / 太长挂死取数线程)
- test_impact_hr_check_field_is_l0: hr_check 字段变更 -> L0 字段级路径
- test_impact_channel_field_is_l1: channel 子段变更 -> L1(端点监听身份, 要重挂)
- test_impact_shared_dir_is_l1: shared_dir 变更 -> L1(站点文件目录变了, 服务与线程要重建)
- test_impact_sites_is_l0: sites 子段变更 -> hr_check.sites 一条 L0(随 hr_check 走动态应用)
- test_impact_site_hr_check_is_l0: 派生站点 hr_check 变更 -> trackers.<站点>.hr_check 一条 L0
- test_config_error_message_points_to_section: 校验失败经 ConfigError 抛出, 消息里带具体路径
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


def _bts_site(**extra) -> dict:
    """BTSchool 站点(域名命中内置档案 btschool), 带 hr 段; extra 追加站点级键"""
    site = {"domains": ["pt.btschool.club"], "hr": {"required_seeding_time": "3D"}}
    site.update(extra)
    return site


def _site(**hr_check) -> dict:
    """普通站点(域名不命中任何档案)+ 可选旧键 hr_check(兼容形态)"""
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
    assert cfg.hr_check.sites == {}
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


def test_sites_entry_parsed(tmp_path):
    """sites 条目解析 + 绑定派生: mode/微调来自配置, 档案四键(adapter/URL/下载路径/翻页参数)来自档案"""
    cfg = load_config(
        _write(
            tmp_path, {
                "hr_check":
                    {
                        "enabled": "true",
                        "sites":
                            {
                                "btschool":
                                    {
                                        "mode": "PARTIAL",
                                        "hr_page_scopes": ["a", "b", "c", "d"],
                                        "max_torrents_per_hour": "3",
                                        "completed_age_limit": "365D",
                                        "refresh_interval": "6H",
                                    }
                            },
                    },
                "trackers": {
                    "btschool": _bts_site()
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
    assert site.refresh_interval == 6 * 3600.0
    # 档案四键: 配置里根本没写, 全部由内置档案填充
    assert site.adapter == "nexusphp"
    assert site.hr_page_url == "https://pt.btschool.club/myhr.php"
    assert site.download_path == "/download.php?id={id}"
    assert site.page_param == "page"
    # 配置真相在 hr_check.sites, trackers.*.hr_check 只是派生视图
    assert set(cfg.hr_check.sites) == {"btschool"}
    assert cfg.hr_check.sites["btschool"].mode == "partial"

    # 未配微调项时走字段默认: max_torrents_per_hour None(回退全局) / completed_age_limit 0(关闭)
    cfg2 = load_config(
        _write(
            tmp_path, {
                "hr_check": {
                    "sites": {
                        "btschool": {
                            "mode": "partial"
                        }
                    }
                },
                "trackers": {
                    "btschool": _bts_site()
                },
            }
        )
    )
    assert cfg2.trackers["btschool"].hr_check.max_torrents_per_hour is None
    assert cfg2.trackers["btschool"].hr_check.completed_age_limit == 0.0


def test_page_url_derived_from_preset(tmp_path):
    """HR 页地址 = https://{命中域名}{档案 page_path}; carpt 档案带出 carpt adapter"""
    cfg = load_config(
        _write(
            tmp_path, {
                "hr_check": {
                    "sites": {
                        "btschool": {
                            "mode": "partial"
                        }
                    }
                },
                "trackers": {
                    "btschool": _bts_site()
                },
            }
        )
    )
    assert cfg.trackers["btschool"].hr_check.hr_page_url == "https://pt.btschool.club/myhr.php"

    # 站点域名精确命中后, carpt 档案的 adapter / 页面地址随之而来
    cfg2 = load_config(
        _write(
            tmp_path, {
                "hr_check": {
                    "sites": {
                        "carpt": {
                            "mode": "all"
                        }
                    }
                },
                "trackers": {
                    "carpt": {
                        "domains": ["carpt.net"],
                        "hr": {
                            "required_seeding_time": "3D"
                        }
                    }
                },
            }
        )
    )
    carpt = cfg2.trackers["carpt"].hr_check
    assert carpt.mode == "all"
    assert carpt.adapter == "carpt"
    assert carpt.hr_page_url == "https://carpt.net/myhr.php"


def test_completed_age_limit_range():
    """超龄豁免线: 0(关闭)与 1D~3650D 合法; 单位写错(<1D, 如 365S)与离谱大值在配置期拦下

    <1D 几乎必然是单位笔误 —— 那等于把整站刚完成的种子集体豁免, 必须 fail-fast 而不是静默生效。
    """
    def errors_for(age) -> list:
        return _validate({"hr_check": {"sites": {"btschool": {"mode": "partial", "completed_age_limit": age}}}})

    assert errors_for("365D") == []
    assert errors_for("0S") == [], "显式 0 = 关闭, 合法"
    assert errors_for("1D") == []
    assert any("completed_age_limit" in e for e in errors_for("365S")), errors_for("365S")
    assert any("completed_age_limit" in e for e in errors_for("4000D"))
    assert any("completed_age_limit" in e for e in errors_for("abc"))


@pytest.mark.parametrize(
    "scopes",
    [["A"], ["A", "B"], ["A", "B", "C", "X"], [], "A"],
)
def test_scopes_restricted_to_known_lanes(scopes):
    """档位只允许 A/B/C/D, 不能为空, 且**必须含 A+B+C**

    少抓一档会让该档种子在「完整刷新」里未列出而被误放行 —— 这一条是漏 HR 的直接来源。
    """
    errors = _validate({"hr_check": {"sites": {"btschool": {"mode": "partial", "hr_page_scopes": scopes}}}})
    assert any("hr_page_scopes" in e for e in errors), errors


def test_scopes_minimum_is_a_b_c():
    """A+B+C 是最小合法集合; 加不加 D(已免罪)都合法"""
    for scopes in (["A", "B", "C"], ["a", "b", "c"], ["A", "B", "C", "D"]):
        errors = _validate({"hr_check": {"sites": {"btschool": {"mode": "partial", "hr_page_scopes": scopes}}}})
        assert errors == [], (scopes, errors)


def test_preset_id_must_be_registered():
    """未登记档案 id 报错, 文案含已支持清单(未入档案的站点不允许启用)"""
    errors = _validate({"hr_check": {"sites": {"foobar": {"mode": "partial"}}}})
    assert any("未支持的站点档案 'foobar'" in e for e in errors), errors
    text = "\n".join(errors)
    assert "btschool" in text and "carpt" in text, "文案必须给出已支持清单"


def test_unbound_site_errors():
    """已启用但没有任何站点的 domains 命中档案域名 -> 报错并指路(补域名)"""
    errors = _validate({
        "hr_check": {
            "sites": {
                "btschool": {
                    "mode": "partial"
                }
            }
        },
        "trackers": {
            "s": _site()
        },
    })
    text = "\n".join(errors)
    assert "config.hr_check.sites.btschool" in text, text
    assert "pt.btschool.club" in text, "文案必须给出档案域名"


def test_binding_must_be_unique():
    """域名重叠导致绑到多个站点 -> 报错(绑定必须唯一)"""
    errors = _validate(
        {
            "hr_check": {
                "sites": {
                    "btschool": {
                        "mode": "partial"
                    }
                }
            },
            "trackers":
                {
                    "x": _bts_site(),
                    "y": {
                        "domains": ["pt.btschool.club"],
                        "hr": {
                            "required_seeding_time": "3D"
                        }
                    },
                },
        }
    )
    text = "\n".join(errors)
    assert "绑定必须唯一" in text, text
    assert "x" in text and "y" in text, "文案必须指出重叠的两个站点名"


def test_bound_site_requires_hr_section():
    """新位置启用但绑定站点缺 hr 段 -> 报错(原「mode != off 必须配 hr 段」约束随绑定搬家)"""
    errors = _validate(
        {
            "hr_check": {
                "sites": {
                    "btschool": {
                        "mode": "partial"
                    }
                }
            },
            "trackers": {
                "btschool": {
                    "domains": ["pt.btschool.club"]
                }
            },
        }
    )
    text = "\n".join(errors)
    assert "config.hr_check.sites.btschool" in text and "hr 段" in text, text


def test_legacy_mode_requires_hr_section():
    """旧键 mode != off 且缺 hr 段 -> 同口径报错(兼容路径上防线不松)"""
    errors = _validate(
        {
            "trackers":
                {
                    "s":
                        {
                            "domains": ["pt.btschool.club"],
                            "hr_check": {
                                "mode": "partial",
                                "hr_page_url": "https://pt.btschool.club/myhr.php"
                            },
                        },
                },
        }
    )
    assert any("hr 段" in e for e in errors), errors


def test_mode_off_does_not_require_hr_section():
    """mode=off 时不要求 hr 段(两个位置都不要求)"""
    assert _validate(
        {
            "hr_check": {
                "sites": {
                    "btschool": {
                        "mode": "off"
                    }
                }
            },
            "trackers": {
                "s": _site(),
                "b": _bts_site(hr_check={"mode": "off"})
            },
        }
    ) == []


def test_legacy_equivalent_migration(tmp_path):
    """生产兼容回归锚: 现网 BTSchool 旧键形态(mode partial + hr_page_url)不改一字,
    加载结果与迁移前一致 —— mode / URL / 微调项逐一对照, 并等价并入 hr_check.sites"""
    old_url = "https://pt.btschool.club/myhr.php"
    cfg = load_config(
        _write(
            tmp_path, {
                "trackers":
                    {
                        "BTSchool":
                            {
                                "domains": ["pt.btschool.club"],
                                "hr": {
                                    "required_seeding_time": "3D"
                                },
                                "hr_check":
                                    {
                                        "mode": "partial",
                                        "adapter": "nexusphp",
                                        "hr_page_url": old_url,
                                        "refresh_interval": "6H",
                                    },
                            },
                    },
            }
        )
    )
    site = cfg.trackers["BTSchool"].hr_check
    assert site is not None
    assert site.mode == "partial"
    assert site.hr_page_url == old_url, "推算 URL 必须与旧配置写的值一致(生产实证)"
    assert site.refresh_interval == 6 * 3600.0, "旧键微调项原样搬进派生值"
    assert site.adapter == "nexusphp"
    assert site.download_path == "/download.php?id={id}"
    # 等价迁移: 配置真相已并入 hr_check.sites(域名交集找档案)
    assert set(cfg.hr_check.sites) == {"btschool"}
    assert cfg.hr_check.sites["btschool"].mode == "partial"
    assert cfg.hr_check.sites["btschool"].refresh_interval == 6 * 3600.0
    # 兼容迁移不报错(校验层放行)
    with open(str(tmp_path / "config.yml"), encoding="utf-8") as f:
        assert validate_config(yaml.safe_load(f)) == []


def test_legacy_preset_keys_are_discarded(tmp_path):
    """旧键四个档案键(adapter/hr_page_url/download_path/page_param)读取后丢弃 —— 值一律以档案为准,
    配置里写对写错行为一致(这正是本次收敛要消灭的易错面)"""
    cfg = load_config(
        _write(
            tmp_path,
            {
                "trackers":
                    {
                        "BTSchool":
                            {
                                **_bts_site(),
                                "hr_check":
                                    {
                                        "mode": "partial",
                                        "adapter": "carpt",  # 写错: 值以档案为准
                                        "hr_page_url": "https://wrong.example.com/myhr.php",  # 指到别的站: 以档案为准
                                        "download_path": "/get.php",  # 缺 {id}: 以档案为准
                                        "page_param": "p",
                                    },
                            },
                    },
            }
        )
    )
    site = cfg.trackers["BTSchool"].hr_check
    assert site.adapter == "nexusphp"
    assert site.hr_page_url == "https://pt.btschool.club/myhr.php"
    assert site.download_path == "/download.php?id={id}"
    assert site.page_param == "page"


def test_new_position_wins_over_legacy(tmp_path):
    """新旧并存(同站既写旧键又写 sites.<id>) -> 新位置获胜, 旧键忽略"""
    cfg = load_config(
        _write(
            tmp_path, {
                "hr_check": {
                    "sites": {
                        "btschool": {
                            "mode": "all"
                        }
                    }
                },
                "trackers":
                    {
                        "BTSchool":
                            {
                                **_bts_site(),
                                "hr_check": {
                                    "mode": "partial",
                                    "hr_page_url": "https://pt.btschool.club/myhr.php"
                                },
                            },
                    },
            }
        )
    )
    assert cfg.trackers["BTSchool"].hr_check.mode == "all"


def test_legacy_unsupported_site_errors():
    """旧键启用但域名绑不上档案 -> 报未支持 + 已支持清单 + 迁移指路"""
    errors = _validate(
        {
            "trackers":
                {
                    "s":
                        {
                            **_site(),
                            "hr_check": {
                                "mode": "partial",
                                "hr_page_url": "https://pt.example.com/myhr.php"
                            },
                        },
                },
        }
    )
    text = "\n".join(errors)
    assert "config.trackers.s.hr_check" in text, text
    assert "btschool" in text and "carpt" in text, "文案必须给出已支持清单"


def test_legacy_unknown_subkeys_accepted():
    """旧键未知子键兼容接受(仅校 mode)—— 迁移语义: 值以档案为准, 不为新键集卡存量配置"""
    assert _validate(
        {
            "trackers": {
                "s": {
                    **_site(),
                    "hr_check": {
                        "mode": "off",
                        "bogus": "1",
                        "adapter": "nexusphp"
                    },
                },
            },
        }
    ) == []


def test_unknown_keys_aggregated():
    """hr_check / channel / sites 条目的未知键一次性报错(带着配置路径)"""
    errors = _validate(
        {
            "hr_check":
                {
                    "bogus": "1",
                    "channel": {
                        "bogus2": "1"
                    },
                    "sites": {
                        "btschool": {
                            "mode": "partial",
                            "bogus3": "1"
                        }
                    },
                },
        }
    )
    text = "\n".join(errors)
    assert "config.hr_check: 未知键" in text and "bogus" in text
    assert "config.hr_check.channel: 未知键" in text and "bogus2" in text
    assert "config.hr_check.sites.btschool: 未知键" in text and "bogus3" in text


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


def test_impact_sites_is_l0():
    """sites 子段变更 -> hr_check.sites 一条 L0(随 hr_check 走动态应用)"""
    from auto_qb.config.models import SiteHrCheckConfig

    old, new = Config(), Config()
    new.hr_check.sites["btschool"] = SiteHrCheckConfig(mode="partial")
    changes = diff_config_impacts(old, new)
    assert [(c.path, c.level) for c in changes] == [("hr_check.sites", LEVEL_L0)]

    new.hr_check.sites["btschool"] = SiteHrCheckConfig(mode="all")
    assert [(c.path, c.level) for c in diff_config_impacts(old, new)] == [("hr_check.sites", LEVEL_L0)]


def test_impact_site_hr_check_is_l0():
    """派生站点 hr_check 变更 -> trackers.<站点>.hr_check 一条 L0; 新增站点仍为整项 L2"""
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
        load_config(_write(tmp_path, {"hr_check": {"sites": {"btschool": {"mode": "fast"}}}}))
    assert "config.hr_check.sites.btschool" in str(excinfo.value)

    with pytest.raises(ConfigError) as excinfo:
        load_config(
            _write(
                tmp_path, {
                    "trackers":
                        {
                            "s":
                                {
                                    **_site(),
                                    "hr_check": {
                                        "mode": "partial",
                                        "hr_page_url": "https://pt.example.com/myhr.php"
                                    },
                                },
                        },
                }
            )
        )
    assert "config.trackers.s.hr_check" in str(excinfo.value)
