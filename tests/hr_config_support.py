"""`hr_config_support` 支撑: 从 `test_hr_config.py` 拆出的模块级辅助/常量(move-only 搬迁, 未改语义)."""

import logging

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
