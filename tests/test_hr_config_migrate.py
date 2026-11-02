"""test_hr_config_migrate 测试计划: hr_check 配置段(v3 15 键口径, 计划 26-09-28-1932 §6/§7 + 26-09-30-0240)

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
- test_legacy_v1_key_migrates_to_v3: 生产兼容回归锚 —— 旧键形态不改一字, 加载即沿链迁移到 v3 enabled
- test_migration_2_3_drops_v2_keys: v2→v3 迁移单测 —— 废弃键删除 / min_torrent_interval 改名 / mode→enabled / idle_refresh_interval 原样保留(无章新写法不丢键)
- test_migration_2_3_keeps_binding_essentials: v2→v3 迁移单测 —— tracker/refresh 保留, off 条目删除
- test_migration_2_3_drops_tracker_hr_check: v2→v3 迁移单测 —— trackers.*.hr_check 残留直接删除
- test_migration_1_2_then_2_3_chain: v1→v2→v3 沿链迁移结果一致(链式正确性)
- test_migration_1_2_processes_every_tracker: v1→v2 逐个 tracker 迁移不被前一个的跳过分支中断(continue 而非 break)
- test_v3_stamp_with_tracker_hr_check_still_migrates: 手写 v3 章且带旧键 -> 迁移照样删除(无兼容层)
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
    _write,
)


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


def test_migration_1_2_processes_every_tracker():
    """v1→v2 逐个 tracker 迁移: 前一个 tracker 命中跳过分支不得中断循环(continue 而非 break)

    四种跳过分支各放一个在前(无 hr_check / 形状烂 / mode=off / 定位不到档案), 再放一个可迁移的
    tracker —— 单 tracker 用例只有一次迭代, 看不出 continue 与 break 的区别。
    """
    raw = {
        "trackers":
            {
                "NoHrKey": {
                    "domains": ["a.example"]
                },
                "BadShape": {
                    "domains": ["b.example"],
                    "hr_check": "oops"
                },
                "OffSite": {
                    "domains": ["c.example"],
                    "hr_check": {
                        "mode": "off"
                    }
                },
                "UnknownHost":
                    {
                        "domains": ["d.example"],
                        "hr_check": {
                            "mode": "partial",
                            "hr_page_url": "https://nope.invalid/x"
                        },
                    },
                "BTSchool":
                    {
                        "domains": ["pt.btschool.club"],
                        "hr_check": {
                            "mode": "partial",
                            "hr_page_url": "https://pt.btschool.club/myhr.php"
                        },
                    },
            }
    }
    cfg = _migrate_config_1_2(raw)
    assert "hr_check" not in cfg["trackers"]["NoHrKey"]
    assert "hr_check" not in cfg["trackers"]["BadShape"]  # 形状烂到读不出 mode: 直接删
    assert "hr_check" not in cfg["trackers"]["OffSite"]  # 新口径下 off = 键不存在
    # 定位不到档案: 旧键原地保留(交校验层报废除错)
    assert cfg["trackers"]["UnknownHost"]["hr_check"]["mode"] == "partial"
    # 关键断言: 最后一个 tracker 照样被迁移(前四个 continue 若退化成 break 则此处失败)
    assert cfg["hr_check"]["sites"]["btschool"] == {"mode": "partial"}


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
