"""test_hr_config 测试计划: hr_check 配置段(v3 15 键口径, 计划 26-09-28-1932 §6/§7 + 26-09-30-0240)

配置是 fail-fast 的第一道闸门: 站点启用(enabled)却没配 hr 段时, 保护会**静默失效**
(check_hr_condition 第一行 `if not self.tracker_conf.hr: return False`), 故必须在配置期拦下。

v3 收敛: 判定语义硬编码(四行判定表), 配置只留「用户身份类」事实 —— 全局 6 键 +
channel 5 键 + sites 条目 4 键(enabled/tracker/refresh_interval/idle_refresh_interval,
末者为稳态降频间隔, 计划 26-10-05-0555 S1, 拍板默认 24H 默认启用)。旧 v2 键 26 个由
config v2→v3 迁移(config/migrations.py)一次性删除或改名, 无常驻兼容层。绑定机制不变
(26-09-27-1930 映射制): 默认绑定 = 档案已知 announce 域在用户 domains 查表, 未命中/歧义
用显式键 `tracker` 直取; 页面事实五键(含 listing)一律由档案填充。

## 测试计划(每个测试函数一条)
- test_defaults_when_absent: 整段缺省 -> 全默认(功能关闭), 不报错
- test_global_section_parsed: 全局段解析(时间串 -> 秒 / channel 子段)
- test_reuse_window_default_and_parsed: 数据复用窗(26-09-30-0240)默认 2H / 自定义时间串解析
- test_reuse_window_range: 复用窗边界 —— 60s 下限与 7d 上限, 之外报错
- test_sites_entry_parsed: sites 条目解析 + 绑定派生(三键来自配置 / 页面事实来自档案 / tracker 回填)
- test_idle_refresh_interval_default_and_parsed: 稳态降频间隔(26-10-05-0555 S1)缺省 24H / 自定义解析 / 派生视图透传
- test_idle_refresh_interval_below_refresh_errors: 交叉校验 —— idle < refresh 报「降频不能比常态还快」
- test_idle_refresh_interval_cross_check_uses_defaults: 交叉校验按缺省补齐比较 —— refresh 配 >24H 而未配 idle 照样报错
- test_idle_refresh_interval_range: 60s 下限 / 30d 上限(与 refresh_interval 同款口径), 之外报错
- test_idle_refresh_interval_equal_to_refresh_valid: idle == refresh 合法(等效关闭降频)
- test_page_url_derived_from_web_domain: HR 页地址恒为档案 web 域派生, 与用户 domains 写法无关
- test_carpt_default_mapping_binds_without_web_domain: CarPT 回归锚 —— domains 只配 announce 域也能绑定
- test_preset_id_must_be_registered: 未登记档案 id 报错 + 文案含已支持清单
- test_default_mapping_zero_hits_errors: 默认映射零命中 -> 报错并附档案 announce 域与两条出路
- test_default_mapping_ambiguous: 默认映射 >=2 命中 -> 报歧义错, 要求显式指定
- test_binding_uniqueness_conflict: 两个站点条目绑到同一 tracker -> 报唯一性错
- test_explicit_tracker_mapping_direct_and_wins: 显式 tracker 直取成功且优先于默认映射
- test_explicit_tracker_missing_key_errors: 显式 tracker 键不存在 -> 报错
- test_bound_site_requires_hr_section: 绑定站点缺 hr 段 -> 报错
- test_disabled_site_does_not_require_hr_section: enabled=false(默认)不要求 hr 段
- test_legacy_v1_key_migrates_to_v3: 生产兼容回归锚 —— 旧键形态不改一字, 加载即沿链迁移到 v3 enabled
- test_migration_2_3_drops_v2_keys: v2→v3 迁移单测 —— 废弃键删除 / min_torrent_interval 改名 / mode→enabled / idle_refresh_interval 原样保留(无章新写法不丢键)
- test_migration_2_3_keeps_binding_essentials: v2→v3 迁移单测 —— tracker/refresh 保留, off 条目删除
- test_migration_2_3_drops_tracker_hr_check: v2→v3 迁移单测 —— trackers.*.hr_check 残留直接删除
- test_migration_1_2_then_2_3_chain: v1→v2→v3 沿链迁移结果一致(链式正确性)
- test_v3_stamp_with_tracker_hr_check_still_migrates: 手写 v3 章且带旧键 -> 迁移照样删除(无兼容层)
- test_unknown_keys_aggregated: hr_check / channel / sites 条目的未知键一次性报错
- test_ranges_and_formats: 间隔下限 / 日额范围 / 页上限 / 时间窗格式聚合报错
- test_channel_extension_id_format: extension_id 只接受 32 位 a~p
- test_channel_request_timeout_range: request_timeout 上下限
- test_impact_hr_check_is_single_section_change: hr_check 段变更 -> 整段一条(W4 级别表退役后粒度 = 段, 无字段级展开)
- test_impact_trackers_whole_section_change: trackers 段变更(含派生站点 hr_check) -> 整段一条; 重匹配语义归 tracker 模块 full_round
- test_config_error_message_points_to_section: 校验失败经 ConfigError 抛出, 消息里带具体路径
"""
import os

import pytest
import yaml

from auto_qb.config import ConfigError, load_config
from auto_qb.config.impact import diff_config_impacts, restart_required_paths
from auto_qb.config.migrations import _migrate_config_1_2, _migrate_config_2_3
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
    assert cfg.hr_check.min_interval == 90.0
    assert cfg.hr_check.max_requests_per_day == 240
    assert cfg.hr_check.max_pages_per_wave == 30
    assert cfg.hr_check.allow_window == ""
    assert cfg.hr_check.shared_dir == ""
    assert cfg.hr_check.reuse_window == 2 * 3600.0
    assert cfg.hr_check.channel.enabled is False
    assert cfg.hr_check.channel.port == 8788
    assert cfg.hr_check.sites == {}
    assert cfg.trackers["s"].hr_check is None


def test_global_section_parsed(tmp_path):
    """全局段解析: 时间串 -> 秒 / channel 子段"""
    cfg = load_config(
        _write(
            tmp_path, {
                "hr_check":
                    {
                        "enabled": "true",
                        "min_interval": "2M",
                        "max_requests_per_day": "300",
                        "max_pages_per_wave": "40",
                        "allow_window": "01:00-06:00",
                        "shared_dir": "//nas/share",
                        "reuse_window": "3H",
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
    assert hr_check.min_interval == 120.0
    assert hr_check.max_requests_per_day == 300
    assert hr_check.max_pages_per_wave == 40
    assert hr_check.allow_window == "01:00-06:00"
    assert hr_check.shared_dir == "//nas/share"
    assert hr_check.reuse_window == 3 * 3600.0
    assert (hr_check.channel.enabled, hr_check.channel.port, hr_check.channel.token) == (True, 8899, "abc")
    assert hr_check.channel.extension_id == "a" * 32
    assert hr_check.channel.request_timeout == 90.0


def test_sites_entry_parsed(tmp_path):
    """sites 条目解析 + 绑定派生: 三键来自配置, 页面事实五键(含 listing)来自档案"""
    cfg = load_config(
        _write(
            tmp_path, {
                "hr_check":
                    {
                        "enabled": "true",
                        "sites": {
                            "btschool": {
                                "enabled": "true",
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
    assert site.enabled is True
    assert site.refresh_interval == 6 * 3600.0
    # 页面事实: 配置里根本没写, 全部由内置档案填充
    assert site.adapter == "btschool"  # 标准 myhr 表格 + 页头 H&R 计数(M2 起, 见 adapters/btschool.py)
    assert site.hr_page_url == "https://pt.btschool.club/myhr.php"
    assert site.download_path == "/download.php?id={id}"
    assert site.page_param == "page"
    assert site.listing == "list"
    # 超额线判据从绑定站点的 hr 规则派生(required + extra)
    assert site.required_seeding_time == 3 * 86400.0
    # 派生视图的 tracker 字段回填解析出的条目名(默认映射命中)
    assert site.tracker == "btschool"
    # 配置真相在 hr_check.sites, trackers.*.hr_check 只是派生视图
    assert set(cfg.hr_check.sites) == {"btschool"}
    assert cfg.hr_check.sites["btschool"].tracker == ""

    # required_seeding_time 派生含 extra
    cfg2 = load_config(
        _write(
            tmp_path, {
                "hr_check": {
                    "sites": {
                        "btschool": {
                            "enabled": "true"
                        }
                    }
                },
                "trackers":
                    {
                        "btschool":
                            {
                                "domains": ["pt.btschool.club"],
                                "hr": {
                                    "required_seeding_time": "3D",
                                    "extra_seeding_time": "1D"
                                }
                            }
                    },
            }
        )
    )
    assert cfg2.trackers["btschool"].hr_check.required_seeding_time == 4 * 86400.0


def test_page_url_derived_from_web_domain(tmp_path):
    """HR 页地址 = https://{档案 web_domain}{page_path}, 与用户 domains 写法完全无关"""
    cfg = load_config(
        _write(
            tmp_path, {
                "hr_check": {
                    "sites": {
                        "btschool": {
                            "enabled": "true"
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


def test_carpt_default_mapping_binds_without_web_domain(tmp_path):
    """CarPT 回归锚: 用户 domains 只配 announce 域(tracker.carpt.net, 不含 web 域)也能自动绑定;
    配主域 carpt.net 同样命中(同命名空间双向子域容错) —— 两种写法 URL 恒为档案 web 域派生值"""
    for domains in (["tracker.carpt.net"], ["carpt.net"]):
        cfg = load_config(
            _write(
                tmp_path, {
                    "hr_check": {
                        "sites": {
                            "carpt": {
                                "enabled": "true"
                            }
                        }
                    },
                    "trackers": {
                        "CarPT": {
                            "domains": domains,
                            "hr": {
                                "required_seeding_time": "3D"
                            }
                        }
                    },
                }
            )
        )
        site = cfg.trackers["CarPT"].hr_check
        assert site is not None and site.tracker == "CarPT"
        assert site.hr_page_url == "https://carpt.net/myhr.php"
        assert site.adapter == "carpt"


def test_preset_id_must_be_registered(tmp_path):
    """未登记档案 id -> 报错 + 已支持清单(未入档案的站点不允许启用)"""
    errors = _validate({
        "hr_check": {
            "sites": {
                "nosuch": {
                    "enabled": "true"
                }
            }
        },
        "trackers": {
            "s": _site()
        },
    })
    assert any("nosuch" in e and "已支持" in e for e in errors), errors


def test_default_mapping_zero_hits_errors(tmp_path):
    """默认映射零命中 -> 报错并附档案 announce 域与两条出路"""
    errors = _validate(
        {
            "hr_check": {
                "sites": {
                    "btschool": {
                        "enabled": "true"
                    }
                }
            },
            "trackers": {
                "other": {
                    "domains": ["other.example"],
                    "hr": {
                        "required_seeding_time": "3D"
                    }
                }
            },
        }
    )
    assert any("默认映射未命中" in e and "pt.btschool.club" in e and "tracker" in e for e in errors), errors


def test_default_mapping_ambiguous(tmp_path):
    """默认映射 >=2 命中 -> 报歧义错, 要求显式指定"""
    errors = _validate(
        {
            "hr_check": {
                "sites": {
                    "btschool": {
                        "enabled": "true"
                    }
                }
            },
            "trackers": {
                "a": _bts_site(),
                "b": _bts_site(),
            },
        }
    )
    assert any("命中多个站点" in e for e in errors), errors


def test_binding_uniqueness_conflict(tmp_path):
    """两个站点条目绑到同一 tracker -> 报唯一性错(一个站点配置只服务一个档案)"""
    errors = _validate(
        {
            "hr_check":
                {
                    "sites":
                        {
                            "btschool": {
                                "enabled": "true",
                                "tracker": "bt"
                            },
                            "carpt": {
                                "enabled": "true",
                                "tracker": "bt"
                            },
                        }
                },
            "trackers": {
                "bt": _site()
            },
        }
    )
    assert any("只能服务一个站点档案" in e for e in errors), errors


def test_explicit_tracker_mapping_direct_and_wins(tmp_path):
    """显式 tracker 直取成功且优先于默认映射"""
    cfg = load_config(
        _write(
            tmp_path,
            {
                "hr_check": {
                    "sites": {
                        "btschool": {
                            "enabled": "true",
                            "tracker": "bt"
                        }
                    }
                },
                "trackers": {
                    "bt": _bts_site(),
                    "bt2": _bts_site(),  # 若走默认映射会歧义; 显式键直取不受影响
                },
            }
        )
    )
    assert cfg.trackers["bt"].hr_check is not None
    assert cfg.trackers["bt2"].hr_check is None, "显式映射只绑一个"


def test_explicit_tracker_missing_key_errors(tmp_path):
    """显式 tracker 键不存在 -> 报错"""
    errors = _validate(
        {
            "hr_check": {
                "sites": {
                    "btschool": {
                        "enabled": "true",
                        "tracker": "ghost"
                    }
                }
            },
            "trackers": {
                "s": _site()
            },
        }
    )
    assert any("ghost" in e and "不存在" in e for e in errors), errors


def test_bound_site_requires_hr_section(tmp_path):
    """绑定站点缺 hr 段 -> 报错(否则保护静默失效)"""
    errors = _validate(
        {
            "hr_check": {
                "sites": {
                    "btschool": {
                        "enabled": "true"
                    }
                }
            },
            "trackers": {
                "btschool": {
                    "domains": ["pt.btschool.club"]  # 没有 hr 段
                }
            },
        }
    )
    assert any("未配置 hr 段" in e for e in errors), errors


def test_disabled_site_does_not_require_hr_section(tmp_path):
    """enabled=false(默认)时不要求 hr 段(与旧 mode=off 同口径)"""
    errors = _validate(
        {
            "hr_check": {
                "sites": {
                    "btschool": {}
                }
            },
            "trackers": {
                "btschool": {
                    "domains": ["pt.btschool.club"]
                }
            },
        }
    )
    assert errors == [], errors


def test_legacy_v1_key_migrates_to_v3(tmp_path):
    """生产兼容回归锚: 现网旧键形态不改一字, 加载即沿链迁移到 v3(enabled 取代 mode)"""
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
                                        "hr_page_url": "https://pt.btschool.club/myhr.php",
                                        "refresh_interval": "6H",
                                    },
                            }
                    }
            }
        )
    )
    site = cfg.trackers["BTSchool"].hr_check
    assert site is not None and site.enabled is True
    assert site.refresh_interval == 6 * 3600.0
    assert site.hr_page_url == "https://pt.btschool.club/myhr.php"
    assert cfg.hr_check.sites["btschool"].enabled is True


def test_migration_2_3_drops_v2_keys():
    """v2→v3 迁移单测: 全局废弃键删除 / min_torrent_interval 改名 min_interval / mode→enabled;
    idle_refresh_interval 原样保留 —— 「缺版本章 = 按 v1 处理」的存量口径下, 无章新写法也会
    走到本迁移, 重建白名单必须携带 v4 期新增键(计划 26-10-05-0555 S1), 否则静默丢键"""
    cfg = _migrate_config_2_3(
        {
            "hr_check":
                {
                    "min_torrent_interval": "60S",
                    "max_torrents_per_hour": 12,
                    "unknown_policy": "hr",
                    "verified_ttl": "12H",
                    "quota_model": "split",
                    "failure_threshold": 3,
                    "parse_missing_rate_max": 0.5,
                    "poll_interval": "1M",
                    "sites":
                        {
                            "btschool":
                                {
                                    "mode": "partial",
                                    "completed_age_limit": "365D",
                                    "tracker": "bt",
                                    "refresh_interval": "6H",
                                    "idle_refresh_interval": "24H",
                                }
                        },
                }
        }
    )
    hr = cfg["hr_check"]
    assert hr["min_interval"] == "60S", "min_torrent_interval 改名保留值"
    for gone in (
        "max_torrents_per_hour", "unknown_policy", "verified_ttl", "quota_model", "failure_threshold",
        "parse_missing_rate_max", "poll_interval", "min_torrent_interval"
    ):
        assert gone not in hr, gone
    entry = hr["sites"]["btschool"]
    assert entry == {"enabled": True, "tracker": "bt", "refresh_interval": "6H", "idle_refresh_interval": "24H"}


def test_migration_2_3_keeps_binding_essentials():
    """v2→v3 迁移单测: off 条目整体删除; all 条目只剩 enabled(其余语义归档案/代码)"""
    cfg = _migrate_config_2_3({"hr_check": {
        "sites": {
            "btschool": {
                "mode": "off"
            },
            "carpt": {
                "mode": "all"
            },
        }
    }})
    assert "btschool" not in cfg["hr_check"]["sites"]
    assert cfg["hr_check"]["sites"]["carpt"] == {"enabled": True}


def test_migration_2_3_drops_tracker_hr_check():
    """v2→v3 迁移单测: trackers.*.hr_check 残留直接删除(v3 无旧位置兼容)"""
    cfg = _migrate_config_2_3(
        {
            "trackers":
                {
                    "BTSchool":
                        {
                            "domains": ["pt.btschool.club"],
                            "hr_check": {
                                "mode": "partial",
                                "hr_page_url": "https://pt.btschool.club/myhr.php",
                            },
                        }
                }
        }
    )
    assert "hr_check" not in cfg["trackers"]["BTSchool"]


def test_migration_1_2_then_2_3_chain():
    """v1→v2→v3 沿链迁移: 1_2 把旧键搬入 sites(mode=partial), 2_3 再翻成 enabled —— 结果一致"""
    raw = {
        "trackers":
            {
                "BTSchool":
                    {
                        "domains": ["pt.btschool.club"],
                        "hr_check":
                            {
                                "mode": "partial",
                                "adapter": "nexusphp",
                                "hr_page_url": "https://pt.btschool.club/myhr.php",
                                "refresh_interval": "6H",
                            },
                    }
            }
    }
    v2 = _migrate_config_1_2(raw)
    assert "hr_check" not in v2["trackers"]["BTSchool"]
    v3 = _migrate_config_2_3(v2)
    assert v3["hr_check"]["sites"]["btschool"] == {"enabled": True, "refresh_interval": "6H"}


def test_v3_stamp_with_tracker_hr_check_still_migrates():
    """手写 v3 章且带旧键 -> 无「报废除错」残留: v2→v3 迁移无条件删除 trackers.*.hr_check(无兼容层)"""
    migrated = _migrate_config_2_3(
        {
            "trackers":
                {
                    "BTSchool":
                        {
                            "domains": ["pt.btschool.club"],
                            "hr_check": {
                                "mode": "partial",
                                "hr_page_url": "https://pt.btschool.club/myhr.php",
                            },
                        }
                }
        }
    )
    assert "hr_check" not in migrated["trackers"]["BTSchool"]


def test_unknown_keys_aggregated():
    """hr_check / channel / sites 条目的未知键一次性报错(聚合, 不打地鼠)"""
    errors = _validate(
        {
            "hr_check": {
                "typo_key": 1,
                "channel": {
                    "typo_channel": 1
                },
                "sites": {
                    "btschool": {
                        "typo_site": 1
                    }
                },
            },
            "trackers": {
                "btschool": _bts_site()
            },
        }
    )
    joined = "; ".join(errors)
    assert "config.hr_check: 未知键 ['typo_key']" in joined
    assert "config.hr_check.channel" in joined and "typo_channel" in joined
    assert "config.hr_check.sites.btschool: 未知键 ['typo_site']" in joined


def test_ranges_and_formats():
    """间隔下限 / 日额范围 / 页上限 / 时间窗格式聚合报错"""
    errors = _validate(
        {
            "hr_check":
                {
                    "min_interval": "1S",  # 低于 5s 下限
                    "max_requests_per_day": 0,
                    "max_pages_per_wave": -1,
                    "allow_window": "25:00-99:00",
                    "shared_dir": 123,
                },
        }
    )
    joined = "; ".join(errors)
    assert "min_interval" in joined
    assert "max_requests_per_day" in joined
    assert "max_pages_per_wave" in joined
    assert "allow_window" in joined
    assert "shared_dir" in joined


def test_reuse_window_default_and_parsed(tmp_path):
    """数据复用窗(26-09-30-0240): 缺省 2H, 自定义时间串正常解析(节奏归 refresh_interval, 新鲜度归本键)"""
    cfg = load_config(_write(tmp_path, {"hr_check": {"enabled": "true", "reuse_window": "30M"}}))
    assert cfg.hr_check.reuse_window == 30 * 60.0


def test_reuse_window_range():
    """复用窗边界: 60s 下限 / 7d 上限(调大只影响数据新鲜度, 但过大会让陈旧数据长期存活)"""
    assert _validate({"hr_check": {"reuse_window": "1M"}}) == []
    assert _validate({"hr_check": {"reuse_window": "7D"}}) == []
    for bad in ("59S", "7D1S", "8D"):
        errors = _validate({"hr_check": {"reuse_window": bad}})
        assert any("reuse_window" in e for e in errors), (bad, errors)


def test_idle_refresh_interval_default_and_parsed(tmp_path):
    """稳态降频间隔(26-10-05-0555 S1): 缺省 24H(拍板默认启用降频), 自定义时间串解析, 派生视图透传"""
    cfg = load_config(
        _write(
            tmp_path, {
                "hr_check": {
                    "sites": {
                        "btschool": {
                            "enabled": "true"
                        }
                    }
                },
                "trackers": {
                    "btschool": _bts_site()
                },
            }
        )
    )
    assert cfg.hr_check.sites["btschool"].idle_refresh_interval == 24 * 3600.0
    # 派生视图(trackers.*.hr_check)同值透传, 下游只读派生视图
    assert cfg.trackers["btschool"].hr_check.idle_refresh_interval == 24 * 3600.0

    cfg2 = load_config(
        _write(
            tmp_path, {
                "hr_check": {
                    "sites": {
                        "btschool": {
                            "enabled": "true",
                            "idle_refresh_interval": "2D",
                        }
                    }
                },
                "trackers": {
                    "btschool": _bts_site()
                },
            }
        )
    )
    assert cfg2.hr_check.sites["btschool"].idle_refresh_interval == 2 * 86400.0
    assert cfg2.trackers["btschool"].hr_check.idle_refresh_interval == 2 * 86400.0


def test_idle_refresh_interval_below_refresh_errors():
    """交叉校验(26-10-05-0555 S1): idle < refresh 报「降频不能比常态还快」; 互换后合法"""
    errors = _validate(
        {"hr_check": {
            "sites": {
                "btschool": {
                    "idle_refresh_interval": "6H",
                    "refresh_interval": "12H"
                }
            }
        }}
    )
    assert any("idle_refresh_interval" in e and "降频不能比常态还快" in e for e in errors), errors
    assert _validate({"hr_check": {
        "sites": {
            "btschool": {
                "idle_refresh_interval": "12H",
                "refresh_interval": "6H"
            }
        }
    }}) == []


def test_idle_refresh_interval_cross_check_uses_defaults():
    """交叉校验按缺省补齐比较(26-10-05-0555 S1): refresh 配 >24H 而未配 idle(有效 idle = 默认 24H)照样报错;
    反之 idle 配 >24H 而 refresh 缺省(12H)合法"""
    errors = _validate({"hr_check": {"sites": {"btschool": {"refresh_interval": "25H"}}}})
    assert any("降频不能比常态还快" in e for e in errors), errors
    assert _validate({"hr_check": {"sites": {"btschool": {"idle_refresh_interval": "25H"}}}}) == []


def test_idle_refresh_interval_range():
    """idle_refresh_interval 边界: 60s 下限 / 30d 上限(与 refresh_interval 同款口径), 之外报错"""
    # 边界内合法(与 refresh 同值配对, 避免踩缺省补齐的交叉校验)
    assert _validate(
        {"hr_check": {
            "sites": {
                "btschool": {
                    "idle_refresh_interval": "60S",
                    "refresh_interval": "60S"
                }
            }
        }}
    ) == []
    assert _validate(
        {"hr_check": {
            "sites": {
                "btschool": {
                    "idle_refresh_interval": "30D",
                    "refresh_interval": "30D"
                }
            }
        }}
    ) == []
    for bad in ("59S", "30D1S", "31D"):
        errors = _validate({"hr_check": {"sites": {"btschool": {"idle_refresh_interval": bad}}}})
        assert any("idle_refresh_interval" in e and ("须 >=" in e or "须 <=" in e or "无效时间格式" in e)
                   for e in errors), (bad, errors)


def test_idle_refresh_interval_equal_to_refresh_valid():
    """idle == refresh 合法(拍板口径: 相等 = 等效关闭降频)"""
    errors = _validate(
        {"hr_check": {
            "sites": {
                "btschool": {
                    "idle_refresh_interval": "12H",
                    "refresh_interval": "12H"
                }
            }
        }}
    )
    assert errors == [], errors


def test_channel_extension_id_format():
    """extension_id 只接受 32 位 a~p(形态错 = 写了也不会生效, 必须配置期拦下)"""
    errors = _validate({"hr_check": {"channel": {"extension_id": "z" * 32}}})
    assert any("32 位 Chrome 扩展 id" in e for e in errors), errors
    assert _validate({"hr_check": {"channel": {"extension_id": "a" * 32}}}) == []


def test_channel_request_timeout_range():
    """request_timeout 上下限(太短误杀正常取数 / 太长挂死取数线程)"""
    errors = _validate({"hr_check": {"channel": {"request_timeout": "1S"}}})
    assert any("request_timeout" in e for e in errors), errors
    errors = _validate({"hr_check": {"channel": {"request_timeout": "2H"}}})
    assert any("request_timeout" in e for e in errors), errors


def test_impact_hr_check_is_single_section_change():
    """hr_check 段变更 -> 整段一条(W4 级别表退役后粒度 = 段, 无字段级展开)

    段内的「重挂/现读」语义(channel/shared_dir 重挂端点, min_interval 等运行时现读)
    由 HrRuntime.apply 自判(其行为守阵在 test_hr_runtime), diff 只负责「变没变」。
    """
    old, new = Config(), Config()
    old.hr_check.channel.port = 8788
    new.hr_check.channel.port = 8899
    changes = diff_config_impacts(old, new)
    assert [c.path for c in changes] == ["hr_check"]
    assert restart_required_paths(changes) == [], "hr_check 不在 R 闸内, 可热应用"


def test_impact_trackers_whole_section_change():
    """trackers 段变更(含派生站点 hr_check) -> 整段一条; 重匹配语义归 tracker 模块 full_round"""
    from auto_qb.config.models import SiteHrCheckConfig, TrackerConfig
    old, new = Config(), Config()
    old.trackers["s"] = TrackerConfig(
        name="s", domains=["a.example"], hr_check=SiteHrCheckConfig(enabled=True, refresh_interval=12 * 3600.0)
    )
    new.trackers["s"] = TrackerConfig(
        name="s", domains=["a.example"], hr_check=SiteHrCheckConfig(enabled=True, refresh_interval=6 * 3600.0)
    )
    changes = diff_config_impacts(old, new)
    assert [c.path for c in changes] == ["trackers"]
    assert restart_required_paths(changes) == [], "trackers 不在 R 闸内, 可热应用"


def test_config_error_message_points_to_section(tmp_path):
    """校验失败经 ConfigError 抛出, 消息里带具体路径"""
    path = _write(tmp_path, {"hr_check": {"min_interval": "1S"}})
    with pytest.raises(ConfigError) as ei:
        load_config(path)
    assert "hr_check.min_interval" in str(ei.value)
