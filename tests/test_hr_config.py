"""test_hr_config 测试计划: hr_check 配置段(解析 / 校验 / 站点绑定 / 热重载分级)

配置是 fail-fast 的第一道闸门: 站点启用(mode != off)却没配 hr 段时, 保护会**静默失效**
(check_hr_condition 第一行 `if not self.tracker_conf.hr: return False`), 故必须在配置期拦下。

站点配置收敛(计划 26-09-27-1318 REV2; 绑定机制被 26-09-27-1930 重写为**映射制**)后:
站点启用与微调的唯一配置源是 `hr_check.sites.<档案 id>`(键 = 内置站点档案 id, 见
config/site_presets.py); web 域与 announce 域是两个命名空间, **永不互相比对** —— 默认绑定 =
档案已知 announce 域(tracker_domain)在用户 domains(同命名空间)查表, 未命中/歧义用显式键
`tracker` 按 trackers 条目名直取。旧键 `trackers.<站点>.hr_check` 由 schema 迁移链 v1→v2
(config/migrations.py)一次性改写, 无常驻兼容层 —— 本文件同时是**生产兼容回归锚**
(现网 BTSchool 旧键形态不改一字, 加载即被迁移链自动搬到新位置)。

## 测试计划(每个测试函数一条)
- test_defaults_when_absent: 整段缺省 -> 全默认(功能关闭), 不报错(max_torrents_per_day=None 按模型取默认)
- test_quota_model_and_split_keys_validated: quota_model 枚举与 split 覆盖键校验
- test_split_rate_interval_consistency_check: 桶速率 × 最小间隔自洽机检(§2 3.6)
- test_global_section_parsed: 全局段解析(时间串 -> 秒 / 枚举归一 / channel 子段)
- test_verified_ttl_default_is_none: verified_ttl 缺省为 None(由站点 refresh_interval 解算, 不在此处固化)
- test_sites_entry_parsed: sites 条目解析 + 绑定派生(scope 归一 / 微调覆盖 / 档案四键来自档案 / 派生 tracker 回填)
- test_page_url_derived_from_web_domain: HR 页地址恒为档案 web 域派生, 与用户 domains 写法无关
- test_carpt_default_mapping_binds_without_web_domain: CarPT 回归锚 —— domains 只配 announce 域也能绑定(双向子域容错)
- test_completed_age_limit_range: 超龄豁免线 0(关闭)或 1D~3650D; 单位写错配置期拦下
- test_scopes_restricted_to_known_lanes: 档位只允许 A/B/C/D 且不能为空
- test_scopes_minimum_is_a_b_c: A+B+C 是最小合法集合(少抓一档 = 该档会被误放行), D 可加可不加
- test_preset_id_must_be_registered: 未登记档案 id 报错 + 文案含已支持清单
- test_default_mapping_zero_hits_errors: 默认映射零命中 -> 报错并附档案 announce 域与两条出路
- test_default_mapping_ambiguous: 默认映射 >=2 命中 -> 报歧义错, 要求显式指定
- test_binding_uniqueness_conflict: 两个站点条目绑到同一 tracker -> 报唯一性错
- test_explicit_tracker_mapping_direct_and_wins: 显式 tracker 直取成功且优先于默认映射
- test_explicit_tracker_missing_key_errors: 显式 tracker 键不存在 -> 报错
- test_bound_site_requires_hr_section: 绑定站点缺 hr 段 -> 报错
- test_legacy_migrated_entry_requires_hr_section: 旧键经迁移函数搬入新位置后, 缺 hr 段同口径报错
- test_mode_off_does_not_require_hr_section: mode=off 时不要求 hr 段(旧键 off 形态被迁移链删除)
- test_legacy_equivalent_migration: 生产兼容回归锚 —— 现网 BTSchool 旧键形态不改一字, 加载即迁移且结果与迁移前一致
- test_legacy_preset_keys_are_discarded: 旧键档案键迁移时丢弃(adapter/download_path/page_param 写错也以档案为准; hr_page_url 的 host 承担迁移定位)
- test_migration_moves_legacy_key_to_sites: v1→v2 迁移单测 —— 旧键搬入 sites(微调随迁/四键与未知键丢弃/旧键删除)
- test_migration_drops_off_and_malformed_legacy_keys: 迁移单测 —— off/非字典旧键直接删除
- test_migration_new_position_wins: 迁移单测 —— 新旧并存时新位置获胜
- test_migration_keeps_unlocatable_legacy_key: 迁移单测 —— host 定位不到档案的旧键原地保留(交校验报废除错)
- test_migration_idempotent_and_no_version_stamp: 迁移单测 —— 幂等, 函数体不碰 schema_version(盖章归框架)
- test_orphan_legacy_key_rejected: 定位不到档案的旧键走完加载 -> 校验报废除错(附已支持清单)
- test_legacy_key_with_v2_stamp_is_rejected: 手写 schema_version=2 且带旧键 -> 校验报废除错
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
import copy
import os

import pytest
import yaml

from auto_qb.config import ConfigError, load_config
from auto_qb.config.impact import LEVEL_L0, LEVEL_L1, diff_config_impacts
from auto_qb.config.migrations import _migrate_config_1_2
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
    assert cfg.hr_check.max_torrents_per_day is None, "未配置 = None, 按配额模型取默认(legacy 60 / split 200)"
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
    # 派生视图的 tracker 字段回填解析出的条目名(默认映射命中)
    assert site.tracker == "btschool"
    # 配置真相在 hr_check.sites, trackers.*.hr_check 只是派生视图
    assert set(cfg.hr_check.sites) == {"btschool"}
    assert cfg.hr_check.sites["btschool"].mode == "partial"
    assert cfg.hr_check.sites["btschool"].tracker == ""

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


def test_page_url_derived_from_web_domain(tmp_path):
    """HR 页地址 = https://{档案 web_domain}{page_path}, 与用户 domains 写法完全无关(26-09-27-1930 §3.2)"""
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


def test_carpt_default_mapping_binds_without_web_domain(tmp_path):
    """本轮 CarPT 事故回归锚: 用户 domains 只配 announce 域(tracker.carpt.net, 不含 web 域)也能自动绑定;
    配主域 carpt.net 同样命中(同命名空间双向子域容错) —— 两种写法 URL 恒为档案 web 域派生值"""
    for domains in (["tracker.carpt.net"], ["carpt.net"]):
        cfg = load_config(
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
                            "domains": domains,
                            "hr": {
                                "required_seeding_time": "3D"
                            }
                        }
                    },
                }
            )
        )
        carpt = cfg.trackers["carpt"].hr_check
        assert carpt is not None, domains
        assert carpt.mode == "all"
        assert carpt.tracker == "carpt", domains
        assert carpt.adapter == "carpt"
        assert carpt.hr_page_url == "https://carpt.net/myhr.php", "URL 恒为档案 web 域, 不随用户 domains 写法变化"


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


def test_default_mapping_zero_hits_errors():
    """默认映射零命中 -> 报错并附档案已知 announce 域 + 两条出路(补域名 / 显式指定)"""
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
    assert "默认映射未命中" in text, text
    assert "pt.btschool.club" in text, "文案必须给出档案已知 announce 域"
    assert "tracker" in text, "文案必须给出显式指定的出路"


def test_default_mapping_ambiguous():
    """默认映射 >=2 命中(两站点 domains 都含档案 announce 域) -> 报歧义错, 要求显式指定"""
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
    assert "默认映射命中多个站点" in text, text
    assert "x" in text and "y" in text, "文案必须指出命中的两个站点名"
    assert "显式填 tracker" in text, text


def test_binding_uniqueness_conflict():
    """同一 tracker 条目被两个启用中的站点绑定(显式/默认混合) -> 报唯一性错"""
    errors = _validate(
        {
            "hr_check": {
                "sites": {
                    "btschool": {
                        "mode": "partial"
                    },
                    "carpt": {
                        "mode": "partial",
                        "tracker": "x",
                    },
                }
            },
            "trackers": {
                "x": {
                    "domains": ["pt.btschool.club"],
                    "hr": {
                        "required_seeding_time": "3D"
                    }
                },
            },
        }
    )
    text = "\n".join(errors)
    assert "站点配置 x 已被条目 btschool 绑定" in text, text


def test_explicit_tracker_mapping_direct_and_wins(tmp_path):
    """显式 tracker 直取成功且优先于默认映射; 派生视图 tracker 回填显式条目名"""
    cfg = load_config(
        _write(
            tmp_path, {
                "hr_check": {
                    "sites": {
                        "btschool": {
                            "mode": "partial",
                            "tracker": "alt",
                        }
                    }
                },
                "trackers":
                    {
                        "alt": {
                            "domains": ["other.example"],
                            "hr": {
                                "required_seeding_time": "3D"
                            }
                        },
                        "bts": _bts_site(),
                    },
            }
        )
    )
    assert cfg.trackers["alt"].hr_check is not None, "显式指定胜过默认映射(alt 域名并不命中档案)"
    assert cfg.trackers["alt"].hr_check.tracker == "alt"
    assert cfg.trackers["alt"].hr_check.hr_page_url == "https://pt.btschool.club/myhr.php"
    assert cfg.trackers["bts"].hr_check is None, "默认映射可命中的站点未被占用(显式优先, 不再查表)"


def test_explicit_tracker_missing_key_errors():
    """显式 tracker 指向不存在的条目名 -> 报错并指路"""
    errors = _validate(
        {
            "hr_check": {
                "sites": {
                    "btschool": {
                        "mode": "partial",
                        "tracker": "ghost",
                    }
                }
            },
            "trackers": {
                "s": _site()
            },
        }
    )
    text = "\n".join(errors)
    assert "config.hr_check.sites.btschool.tracker" in text, text
    assert "站点配置 'ghost' 不存在" in text, text


def test_bound_site_requires_hr_section():
    """绑定站点(默认映射)缺 hr 段 -> 报错(原「mode != off 必须配 hr 段」约束随绑定保留)"""
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


def test_legacy_migrated_entry_requires_hr_section():
    """旧键经迁移函数搬入新位置后, 缺 hr 段同口径报错(迁移不放松任何防线)"""
    cfg = {
        "trackers":
            {
                "s":
                    {
                        "domains": ["pt.btschool.club"],
                        "hr_check": {
                            "mode": "partial",
                            "hr_page_url": "https://pt.btschool.club/myhr.php",
                        },
                    },
            },
    }
    errors = validate_config({"config": _migrate_config_1_2(cfg)})
    assert any("hr 段" in e for e in errors), errors


def test_mode_off_does_not_require_hr_section(tmp_path):
    """mode=off 时不要求 hr 段; 旧键 off 形态被迁移链直接删除(新口径下 off = 键不存在)"""
    cfg = load_config(
        _write(
            tmp_path, {
                "hr_check": {
                    "sites": {
                        "btschool": {
                            "mode": "off"
                        }
                    }
                },
                "trackers": {
                    "s": _site(),
                    "b": _bts_site(hr_check={"mode": "off"}),
                },
            }
        )
    )
    assert cfg.trackers["b"].hr_check is None
    assert cfg.trackers["s"].hr_check is None
    assert cfg.hr_check.sites["btschool"].mode == "off"


def test_legacy_equivalent_migration(tmp_path):
    """生产兼容回归锚: 现网 BTSchool 旧键形态(mode partial + hr_page_url)不改一字, 加载即被
    迁移链 v1→v2 自动搬到 hr_check.sites.btschool, 派生结果与迁移前一致 —— mode / URL / 微调项"""
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
    assert site.hr_page_url == old_url, "档案 web 域派生的 URL 必须与旧配置写的值一致(生产实证)"
    assert site.refresh_interval == 6 * 3600.0, "旧键微调项原样搬进派生值"
    assert site.adapter == "nexusphp"
    assert site.download_path == "/download.php?id={id}"
    assert site.tracker == "BTSchool", "派生视图回填解析出的条目名"
    # 迁移: 配置真相已并入 hr_check.sites(旧键按 hr_page_url 的 host 定位档案)
    assert set(cfg.hr_check.sites) == {"btschool"}
    assert cfg.hr_check.sites["btschool"].mode == "partial"
    assert cfg.hr_check.sites["btschool"].refresh_interval == 6 * 3600.0
    # 迁移后的内存结构全量合法(直接校验旧键会报废除错, 见 test_legacy_key_with_v2_stamp_is_rejected)
    with open(str(tmp_path / "config.yml"), encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    assert validate_config({"config": _migrate_config_1_2(raw["config"])}) == []


def test_legacy_preset_keys_are_discarded(tmp_path):
    """旧键档案键迁移时丢弃 —— adapter/download_path/page_param 写对写错行为一致(值一律以档案为准,
    这正是档案化要消灭的易错面); hr_page_url 例外: 它的 host 承担迁移定位(26-09-27-1930 §3.4),
    指到别的站会定位不到档案而报废除错(见 test_orphan_legacy_key_rejected)"""
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
                                        "hr_page_url": "https://pt.btschool.club/myhr.php",  # host 定位档案
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


def test_migration_moves_legacy_key_to_sites():
    """v1→v2 迁移单测: 旧键搬入 hr_check.sites.<档案 id> —— mode/微调项直搬, 页面事实四键与
    未知键丢弃, 旧键删除; host 按档案 web 域(web↔web 同命名空间)定位, 不触碰 tracker 域"""
    cfg = {
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
                                "download_path": "/download.php?id={id}",
                                "page_param": "page",
                                "refresh_interval": "6H",
                                "max_torrents_per_hour": "3",
                                "bogus": "1",
                            },
                    },
            },
    }
    out = _migrate_config_1_2(cfg)
    assert out["hr_check"]["sites"] == {
        "btschool": {
            "mode": "partial",
            "refresh_interval": "6H",
            "max_torrents_per_hour": "3",
        }
    }, "微调项随迁, 页面事实四键与未知键丢弃"
    assert "hr_check" not in out["trackers"]["BTSchool"], "旧键删除"


def test_migration_drops_off_and_malformed_legacy_keys():
    """v1→v2 迁移单测: mode=off 与非字典形状的旧键直接删除(新口径下 off = 键不存在)"""
    cfg = {
        "trackers":
            {
                "a": {
                    "domains": ["x.example"],
                    "hr_check": {
                        "mode": "off"
                    },
                },
                "b": {
                    "domains": ["x.example"],
                    "hr_check": "junk",
                },
            },
    }
    out = _migrate_config_1_2(cfg)
    assert all("hr_check" not in t for t in out["trackers"].values())
    assert "hr_check" not in out


def test_migration_new_position_wins():
    """v1→v2 迁移单测: 新旧并存(同档案已写 sites 条目)时新位置获胜, 旧键仅删除不并入"""
    cfg = {
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
                        "domains": ["pt.btschool.club"],
                        "hr_check":
                            {
                                "mode": "partial",
                                "hr_page_url": "https://pt.btschool.club/myhr.php",
                                "refresh_interval": "6H",
                            },
                    },
            },
    }
    out = _migrate_config_1_2(cfg)
    assert out["hr_check"]["sites"]["btschool"] == {"mode": "all"}
    assert "hr_check" not in out["trackers"]["BTSchool"]


def test_migration_keeps_unlocatable_legacy_key():
    """v1→v2 迁移单测: 缺 hr_page_url / host 陌生的旧键原地保留 —— 交给校验层报废除错,
    迁移函数不做任何猜测(宁可报错也不迁错站)"""
    for legacy in (
        {
            "mode": "partial"
        },
        {
            "mode": "partial",
            "hr_page_url": "https://pt.example.com/myhr.php",
        },
    ):
        cfg = {"trackers": {"s": {"domains": ["pt.example.com"], "hr_check": dict(legacy)}}}
        out = _migrate_config_1_2(cfg)
        assert out["trackers"]["s"]["hr_check"] == legacy, legacy
        assert "hr_check" not in out


def test_migration_idempotent_and_no_version_stamp():
    """v1→v2 迁移单测: 同输入重放同输出(幂等); schema_version 盖章由框架负责, 函数体不碰"""
    cfg = {
        "trackers":
            {
                "BTSchool":
                    {
                        "domains": ["pt.btschool.club"],
                        "hr_check":
                            {
                                "mode": "partial",
                                "hr_page_url": "https://pt.btschool.club/myhr.php",
                                "refresh_interval": "6H",
                            },
                    },
            },
    }
    once = _migrate_config_1_2(copy.deepcopy(cfg))
    twice = _migrate_config_1_2(copy.deepcopy(once))
    assert twice == once
    assert "schema_version" not in twice


def test_orphan_legacy_key_rejected(tmp_path):
    """host 定位不到档案的旧键走完加载 -> 校验报废除错, 文案附已支持清单与新位置指路"""
    with pytest.raises(ConfigError) as exc:
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
                                        "hr_page_url": "https://pt.example.com/myhr.php",
                                    },
                                },
                        },
                }
            )
        )
    text = str(exc.value)
    assert "schema v2 废除" in text, text
    assert "btschool" in text and "carpt" in text, "文案必须给出已支持清单"
    assert "config.hr_check.sites" in text, "文案必须指路到新位置"


def test_legacy_key_with_v2_stamp_is_rejected():
    """兜底分支: 手写 schema_version=2 却仍写旧键 -> 校验报废除错(正常流迁移链已把旧键迁走)"""
    errors = _validate(
        {
            "schema_version": "2",
            "trackers":
                {
                    "s":
                        {
                            **_site(),
                            "hr_check": {
                                "mode": "partial",
                                "hr_page_url": "https://pt.btschool.club/myhr.php",
                            },
                        },
                },
        }
    )
    text = "\n".join(errors)
    assert "config.trackers.s.hr_check" in text, text
    assert "schema v2 废除" in text, text
    assert "btschool" in text and "carpt" in text, "文案必须给出已支持清单"


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


# ---------- M5.3 配额模型拆分(计划 26-09-27-1815 §2 3.1/3.6) ----------


def test_quota_model_and_split_keys_validated():
    """quota_model 枚举与 split 覆盖键校验: 非法值报错, 合法值通过"""
    ok = _validate({"hr_check": {"sites": {"btschool": {"mode": "partial", "quota_model": "split"}}}})
    assert ok == []
    bad = _validate({"hr_check": {"sites": {"btschool": {"mode": "partial", "quota_model": "turbo"}}}})
    assert any("quota_model" in e for e in bad)
    bad2 = _validate({"hr_check": {"sites": {"btschool": {"mode": "partial", "page_rate_per_hour": 0}}}})
    assert any("page_rate_per_hour" in e for e in bad2)
    ok2 = _validate(
        {
            "hr_check":
                {
                    "sites": {
                        "btschool": {
                            "mode": "partial",
                            "quota_model": "split",
                            "torrent_rate_per_hour": 15
                        }
                    },
                }
        }
    )
    assert ok2 == []


def test_split_rate_interval_consistency_check():
    """参数自洽机检(§2 3.6): 桶速率超过最小间隔允许的物理上限 => 聚合报错"""
    bad = _validate({"hr_check": {"page_rate_per_hour": 60, "min_page_interval": "90S"}})
    assert any("page_rate_per_hour" in e and "上限" in e for e in bad), bad
    ok = _validate({"hr_check": {"page_rate_per_hour": 40, "min_page_interval": "90S"}})
    assert ok == [], "40/时 恰好 = 3600/90 的物理上限 => 自洽"
    bad2 = _validate({"hr_check": {"torrent_rate_per_hour": 60, "min_torrent_interval": "90S"}})
    assert any("torrent_rate_per_hour" in e for e in bad2)
