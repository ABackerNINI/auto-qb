"""test_hr_config_bindings 测试计划: hr_check 配置段(v3 15 键口径, 计划 26-09-28-1932 §6/§7 + 26-09-30-0240)

配置是 fail-fast 的第一道闸门: 站点启用(enabled)却没配 hr 段时, 保护会**静默失效**
(check_hr_condition 第一行 `if not self.tracker_conf.hr: return False`), 故必须在配置期拦下。

v3 收敛: 判定语义硬编码(四行判定表), 配置只留「用户身份类」事实 —— 全局 6 键 +
channel 8 键(26-10-14-1241 去端口+跨机: host/port:0/discovery_port/pairing 三新键) +
sites 条目 4 键(enabled/tracker/refresh_interval/idle_refresh_interval,
末者为稳态降频间隔, 计划 26-10-05-0555 S1, 拍板默认 24H 默认启用)。旧 v2 键 26 个由
config v2→v3 迁移(config/migrations.py)一次性删除或改名, 无常驻兼容层。绑定机制不变
(26-09-27-1930 映射制): 默认绑定 = 档案已知 announce 域在用户 domains 查表, 未命中/歧义
用显式键 `tracker` 直取; 页面事实五键(含 listing)一律由档案填充。

## 测试计划(每个测试函数一条)
- test_carpt_default_mapping_binds_without_web_domain: CarPT 回归锚 —— domains 只配 announce 域也能绑定
- test_preset_id_must_be_registered: 未登记档案 id 报错 + 文案含已支持清单
- test_default_mapping_zero_hits_errors: 默认映射零命中 -> 报错并附档案 announce 域与两条出路
- test_default_mapping_ambiguous: 默认映射 >=2 命中 -> 报歧义错, 要求显式指定
- test_binding_uniqueness_conflict: 两个站点条目绑到同一 tracker -> 报唯一性错
- test_explicit_tracker_mapping_direct_and_wins: 显式 tracker 直取成功且优先于默认映射
- test_site_bindings_reports_all_entries: 站点绑定逐条校验不被前一条跳过分支截断(continue 而非 break)
- test_disabled_site_does_not_require_hr_section: enabled=false(默认)不要求 hr 段
- test_impact_hr_check_is_single_section_change: hr_check 段变更 -> 整段一条(W4 级别表退役后粒度 = 段, 无字段级展开)
- test_impact_trackers_whole_section_change: trackers 段变更(含派生站点 hr_check) -> 整段一条; 重匹配语义归 tracker 模块 full_round
- test_hr_check_sites_reports_all_entries: hr_check.sites 未登记档案条目的跳过分支不得中断后续条目校验(continue 而非 break)
- test_site_bindings_reports_all_after_non_dict_tracker: 非字典 tracker 条目不得中断后续 tracker 的登记(continue 而非 break)
- test_site_bindings_reports_all_after_disabled_entry: 未启用站点条目不得中断后续条目的绑定校验(continue 而非 break)
- test_site_bindings_reports_all_after_explicit_missing: 显式 tracker 键不存在的跳过分支不得中断后续条目(continue 而非 break)
- test_site_bindings_reports_all_after_default_zero_hit: 默认映射零命中的跳过分支不得中断后续条目(continue 而非 break)
- test_site_bindings_reports_all_after_ambiguous_mapping: 默认映射歧义的跳过分支不得中断后续条目(continue 而非 break)
- test_site_bindings_reports_all_after_duplicate_binding: 重复绑定的跳过分支不得中断后续条目(continue 而非 break; 合成第三档案)
- test_resolve_hr_site_bindings_after_disabled_site: 绑定派生(loader)未启用条目不得中断后续条目的绑定(continue 而非 break)
- test_site_binding_takes_preset_page_facts: 派生视图的页面事实键取档案值(非 SiteHrCheckConfig 字段默认; 合成非默认档案)
- test_resolve_hr_site_bindings_skips_unresolvable_entries: _resolve_hr_site_bindings 三条保守 continue(未登记档案/显式键不存在/默认映射非唯一命中) + hr=None 派生 0.0 纵深(直接喂非法输入不得外抛; 唯一命中对照照常派生)
"""

import logging

import os

import pytest

import yaml

from auto_qb.config import ConfigError, load_config

from auto_qb.config.impact import diff_config_impacts, restart_required_paths

from auto_qb.config.migrations import _migrate_config_1_2, _migrate_config_2_3

from auto_qb.config.models import Config

from auto_qb.config.validation import validate_config

from hr_config_support import (
    _bts_site,
    _site,
    _validate,
    _write,
)


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


def test_site_bindings_reports_all_entries():
    """站点绑定逐条校验: 前一条的跳过分支(未登记档案)不得中断后续条目(continue 而非 break)

    单条目用例看不出 continue/break 的区别; 这里把"未登记档案"放前面, 再放一条会报
    「未配置 hr 段」的合法档案条目 —— 循环若 break, 后者的错就丢了。
    """
    errors = _validate(
        {
            "hr_check": {
                "sites": {
                    "not-registered": {
                        "enabled": "true"
                    },
                    "btschool": {
                        "enabled": "true"
                    },
                }
            },
            "trackers": {
                "btschool": {
                    "domains": ["pt.btschool.club"]
                }
            },
        }
    )
    assert any("未支持的站点档案" in e for e in errors), errors
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


def test_hr_check_sites_reports_all_entries():
    """hr_check.sites 逐条校验: 未登记档案条目的跳过分支不得中断后续条目(continue 而非 break, mutmut_237)

    未登记档案放前, 后置的合法档案条目带未知键 —— 循环若 break, 后者的「未知键」就丢了。
    """
    errors = _validate(
        {
            "hr_check":
                {
                    "sites": {
                        "not-registered": {
                            "enabled": "true"
                        },
                        "btschool": {
                            "enabled": "true",
                            "bogus": "1"
                        },
                    }
                },
            "trackers": {
                "btschool": {
                    "domains": ["pt.btschool.club"],
                    "hr": {
                        "required_seeding_time": "3D"
                    }
                }
            },
        }
    )
    assert any("未支持的站点档案" in e for e in errors), errors
    assert any("sites.btschool: 未知键 ['bogus']" in e for e in errors), errors


def test_site_bindings_reports_all_after_non_dict_tracker():
    """站点绑定: trackers 里非字典条目不得中断后续 tracker 的登记(continue 而非 break, mutmut_10)

    前置 Bad 非字典 -> 若 break, 后面的 btschool 不进 tracker_names/domains_by_tracker/hr_sections,
    默认映射变零命中(误报)。断言: 合法配置不产生"默认映射未命中"。
    """
    errors = _validate(
        {
            "hr_check": {
                "sites": {
                    "btschool": {
                        "enabled": "true"
                    }
                }
            },
            "trackers":
                {
                    "Bad": "oops",
                    "btschool": {
                        "domains": ["pt.btschool.club"],
                        "hr": {
                            "required_seeding_time": "3D"
                        }
                    },
                },
        }
    )
    assert not any("默认映射未命中" in e for e in errors), errors
    assert not any("未配置 hr 段" in e for e in errors), errors


def test_site_bindings_reports_all_after_disabled_entry():
    """站点绑定: 未启用条目不得中断后续条目的绑定校验(continue 而非 break, mutmut_50)

    未启用的 btschool 放前, 后置 carpt 绑定到缺 hr 段的 CarPT —— 循环若 break, 后者的
    「未配置 hr 段」就丢了。
    """
    errors = _validate(
        {
            "hr_check": {
                "sites": {
                    "btschool": {
                        "enabled": "false"
                    },
                    "carpt": {
                        "enabled": "true"
                    },
                }
            },
            "trackers": {
                "CarPT": {
                    "domains": ["tracker.carpt.net"]
                }
            },
        }
    )
    assert any("未配置 hr 段" in e for e in errors), errors


def test_site_bindings_reports_all_after_explicit_missing():
    """站点绑定: 显式 tracker 键不存在的跳过分支不得中断后续条目(continue 而非 break, mutmut_65)"""
    errors = _validate(
        {
            "hr_check":
                {
                    "sites":
                        {
                            "btschool": {
                                "enabled": "true",
                                "tracker": "nope"
                            },
                            "carpt": {
                                "enabled": "true",
                                "tracker": "CarPT"
                            },
                        }
                },
            "trackers": {
                "CarPT": {
                    "domains": ["tracker.carpt.net"]
                }
            },
        }
    )
    assert any("站点配置 'nope' 不存在" in e for e in errors), errors
    assert any("未配置 hr 段" in e for e in errors), errors


def test_site_bindings_reports_all_after_default_zero_hit():
    """站点绑定: 默认映射零命中的跳过分支不得中断后续条目(continue 而非 break, mutmut_76)"""
    errors = _validate(
        {
            "hr_check": {
                "sites": {
                    "btschool": {
                        "enabled": "true"
                    },
                    "carpt": {
                        "enabled": "true",
                        "tracker": "CarPT"
                    },
                }
            },
            "trackers": {
                "CarPT": {
                    "domains": ["tracker.carpt.net"]
                }
            },
        }
    )
    assert any("默认映射未命中" in e for e in errors), errors
    assert any("未配置 hr 段" in e for e in errors), errors


def test_site_bindings_reports_all_after_ambiguous_mapping():
    """站点绑定: 默认映射歧义的跳过分支不得中断后续条目(continue 而非 break, mutmut_82)"""
    errors = _validate(
        {
            "hr_check": {
                "sites": {
                    "btschool": {
                        "enabled": "true"
                    },
                    "carpt": {
                        "enabled": "true",
                        "tracker": "CarPT"
                    },
                }
            },
            "trackers":
                {
                    "T1": {
                        "domains": ["pt.btschool.club"]
                    },
                    "T2": {
                        "domains": ["pt.btschool.club"]
                    },
                    "CarPT": {
                        "domains": ["tracker.carpt.net"]
                    },
                },
        }
    )
    assert any("默认映射命中多个站点" in e for e in errors), errors
    assert any("未配置 hr 段" in e for e in errors), errors


def test_site_bindings_reports_all_after_duplicate_binding(monkeypatch):
    """站点绑定: 重复绑定的跳过分支不得中断后续条目(continue 而非 break, mutmut_88)

    现网只有两个内置档案, 无法凑出「前两条撞绑定 + 第三条待处理」—— 用 monkeypatch 加一个合成
    档案作第三条, 让 break 的后果(第三条的「未配置 hr 段」丢失)可观测。
    """
    from auto_qb.config import site_presets
    from auto_qb.config.site_presets import SiteHrPreset

    monkeypatch.setitem(
        site_presets.SITE_PRESETS,
        "zsite",
        SiteHrPreset(
            preset_id="zsite",
            adapter="btschool",
            web_domain="z.example",
            tracker_domain="z.example",
            page_path="/myhr.php",
            download_path="/download.php?id={id}",
            page_param="page",
        ),
    )
    errors = _validate(
        {
            "hr_check":
                {
                    "sites":
                        {
                            "btschool": {
                                "enabled": "true",
                                "tracker": "T1"
                            },
                            "carpt": {
                                "enabled": "true",
                                "tracker": "T1"
                            },
                            "zsite": {
                                "enabled": "true",
                                "tracker": "T2"
                            },
                        }
                },
            "trackers":
                {
                    "T1": {
                        "domains": ["pt.btschool.club"],
                        "hr": {
                            "required_seeding_time": "3D"
                        }
                    },
                    "T2": {
                        "domains": ["z.example"]
                    },
                },
        }
    )
    assert any("已被条目" in e for e in errors), errors
    assert any("未配置 hr 段" in e for e in errors), errors


def test_resolve_hr_site_bindings_after_disabled_site(tmp_path):
    """绑定派生(loader)未启用条目不得中断后续条目的绑定(continue 而非 break, loaders mutmut_2)

    _resolve_hr_site_bindings 与校验器同款遍历; 未启用条目放前, 后置启用条目必须照常派生
    trackers.*.hr_check(循环若 break, 派生视图恒为 None)。
    """
    cfg = load_config(
        _write(
            tmp_path, {
                "hr_check": {
                    "sites": {
                        "btschool": {
                            "enabled": "false"
                        },
                        "carpt": {
                            "enabled": "true"
                        },
                    }
                },
                "trackers": {
                    "CarPT": {
                        "domains": ["tracker.carpt.net"],
                        "hr": {
                            "required_seeding_time": "3D"
                        }
                    }
                },
            }
        )
    )
    site = cfg.trackers["CarPT"].hr_check
    assert site is not None and site.enabled is True
    assert site.tracker == "CarPT"


def test_site_binding_takes_preset_page_facts(monkeypatch, tmp_path):
    """派生视图的页面事实键取**档案值**, 不是 SiteHrCheckConfig 字段默认(合成非默认档案)

    变异面: _resolve_hr_site_bindings 里 download_path=/page_param=/listing= 实参被删 -> 落回
    字段默认。现网两个内置档案的这三个值恰好与字段默认同值, 删了看不出差别 —— 故用
    monkeypatch 挂一个**三项都非默认**的合成档案, 让删除的后果可观测。
    """
    from auto_qb.config import site_presets
    from auto_qb.config.site_presets import SiteHrPreset

    monkeypatch.setitem(
        site_presets.SITE_PRESETS,
        "zsite",
        SiteHrPreset(
            preset_id="zsite",
            adapter="btschool",
            web_domain="z.example",
            tracker_domain="z.example",
            page_path="/myhr.php",
            download_path="/dl.php?id={id}&k=1",  # 字段默认 /download.php?id={id}
            page_param="p",  # 字段默认 page
            listing="none",  # 字段默认 list
        ),
    )
    cfg = load_config(
        _write(
            tmp_path, {
                "hr_check": {
                    "sites": {
                        "zsite": {
                            "enabled": "true"
                        }
                    }
                },
                "trackers":
                    {
                        "T1":
                            {
                                "domains": ["z.example"],
                                "hr": {
                                    "required_seeding_time": "3D",
                                    "extra_seeding_time": "1D"
                                }
                            }
                    },
            }
        )
    )
    site = cfg.trackers["T1"].hr_check
    assert site is not None and site.enabled is True
    assert site.download_path == "/dl.php?id={id}&k=1"
    assert site.page_param == "p"
    assert site.listing == "none"
    assert site.adapter == "btschool"  # 字段默认 nexusphp
    assert site.hr_page_url == "https://z.example/myhr.php"  # 字段默认 ""
    assert site.required_seeding_time == 4 * 86400.0  # required + extra(字段默认 0.0)
    # 条目未配的两键 -> 走 SiteHrCheckConfig 字段默认并透传到派生视图
    assert site.refresh_interval == 12 * 3600.0
    assert site.idle_refresh_interval == 24 * 3600.0
    assert cfg.hr_check.sites["zsite"].refresh_interval == 12 * 3600.0


def test_resolve_hr_site_bindings_skips_unresolvable_entries():
    """_resolve_hr_site_bindings 三条保守 continue + hr=None 派生 0.0(纵深, 不得外抛)

    校验层(fail-fast)已拦下的三种不可解析形态, 直接喂给 loader 的绑定派生:
    未登记档案 / 显式 tracker 键不存在 / 默认映射非唯一命中(零命中与歧义) —— 每条都必须
    静静 continue(派生视图保持 None), 而不是 KeyError/IndexError 外抛。变异面: 某条
    continue 删掉 -> `None.adapter` / `trackers["ghost"]` / `matched[0]` 直接炸。

    另含 hr=None 纵深: 绑定站点的 hr 规则为 None 时 required_seeding_time 落 0.0
    (校验层要求绑定点配 hr 段, 此分支正常路径不可达, 但 `if hr_rule is not None else 0.0`
    的 None 侧必须被钉住); 同时充当「唯一命中照常派生」的正对照。
    """
    from auto_qb.config.loaders import _resolve_hr_site_bindings
    from auto_qb.config.models import HrCheckConfig, SiteHrCheckConfig, TrackerConfig

    def _trk(name: str, domains) -> TrackerConfig:
        return TrackerConfig(name=name, domains=list(domains))

    bt_domains = ["pt.btschool.club"]

    # 1. 未登记档案 id: find_preset 返 None -> continue
    trackers = {"bt": _trk("bt", bt_domains), "bt2": _trk("bt2", bt_domains)}
    _resolve_hr_site_bindings(HrCheckConfig(sites={"nosuch": SiteHrCheckConfig(enabled=True)}), trackers)
    assert trackers["bt"].hr_check is None and trackers["bt2"].hr_check is None

    # 2. 显式 tracker 键不存在 -> continue(不去猜默认映射)
    trackers = {"bt": _trk("bt", bt_domains), "bt2": _trk("bt2", bt_domains)}
    _resolve_hr_site_bindings(
        HrCheckConfig(sites={"btschool": SiteHrCheckConfig(enabled=True, tracker="ghost")}), trackers
    )
    assert trackers["bt"].hr_check is None and trackers["bt2"].hr_check is None

    # 3. 默认映射零命中(档案域与用户 domains 无交集) -> continue
    trackers = {"bt": _trk("bt", bt_domains), "bt2": _trk("bt2", bt_domains)}
    _resolve_hr_site_bindings(HrCheckConfig(sites={"carpt": SiteHrCheckConfig(enabled=True)}), trackers)
    assert trackers["bt"].hr_check is None and trackers["bt2"].hr_check is None

    # 4. 默认映射歧义(两条 tracker 同域命中) -> continue(不武断挑第一条)
    trackers = {"bt": _trk("bt", bt_domains), "bt2": _trk("bt2", bt_domains)}
    _resolve_hr_site_bindings(HrCheckConfig(sites={"btschool": SiteHrCheckConfig(enabled=True)}), trackers)
    assert trackers["bt"].hr_check is None and trackers["bt2"].hr_check is None

    # 5. 正对照 + hr=None 纵深: 唯一命中照常派生; hr=None(校验层已拦)时超额线落 0.0
    trackers = {"bt": TrackerConfig(name="bt", domains=bt_domains, hr=None)}
    _resolve_hr_site_bindings(HrCheckConfig(sites={"btschool": SiteHrCheckConfig(enabled=True)}), trackers)
    site = trackers["bt"].hr_check
    assert site is not None and site.enabled is True
    assert site.tracker == "bt"  # 派生视图回填解析出的条目名
    assert site.required_seeding_time == 0.0, "hr=None 时超额线必须落 0.0(不得 None 下溢)"
    assert site.adapter == "btschool" and site.hr_page_url == "https://pt.btschool.club/myhr.php"
