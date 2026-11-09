"""test_hr_config_misc 测试计划: hr_check 配置段(v3 15 键口径, 计划 26-09-28-1932 §6/§7 + 26-09-30-0240)

配置是 fail-fast 的第一道闸门: 站点启用(enabled)却没配 hr 段时, 保护会**静默失效**
(check_hr_condition 第一行 `if not self.tracker_conf.hr: return False`), 故必须在配置期拦下。

v3 收敛: 判定语义硬编码(四行判定表), 配置只留「用户身份类」事实 —— 全局 6 键 +
channel 9 键(26-10-14-1241 去端口+跨机: host/port:0/discovery_port/pairing 三新键;
26-11-10-0515 S3/D7 + name 标签键: 空 = 回落 data_dir 目录名) +
sites 条目 4 键(enabled/tracker/refresh_interval/idle_refresh_interval,
末者为稳态降频间隔, 计划 26-10-05-0555 S1, 拍板默认 24H 默认启用)。旧 v2 键 26 个由
config v2→v3 迁移(config/migrations.py)一次性删除或改名, 无常驻兼容层。绑定机制不变
(26-09-27-1930 映射制): 默认绑定 = 档案已知 announce 域在用户 domains 查表, 未命中/歧义
用显式键 `tracker` 直取; 页面事实五键(含 listing)一律由档案填充。

## 测试计划(每个测试函数一条)
- test_explicit_tracker_missing_key_errors: 显式 tracker 键不存在 -> 报错
- test_bound_site_requires_hr_section: 绑定站点缺 hr 段 -> 报错
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
    _site,
    _validate,
)


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
