"""`config_write_support` 支撑: 从 `test_config.py` 拆出的模块级辅助/常量(move-only 搬迁, 未改语义)."""

import logging

import os

import tempfile

from pathlib import Path

import pytest

import yaml

from auto_qb.config import (
    Config,
    ConfigError,
    HRRule,
    NotifyConfig,
    QbittorrentConfig,
    TrackerConfig,
    load_config,
    load_global_hr,
    load_tracker_hr,
)

from auto_qb.core.traffic_source import paths as traffic_paths

from auto_qb.infra.errors import AutoQbError


def _write_config(td, **extra_cfg):
    cfg = {
        "config":
            {
                "qbittorrent": {
                    "host": "127.0.0.1",
                    "port": 16585,
                    "username": "u",
                    "password": "p",
                },
                "trackers":
                    {
                        "HHan": {
                            "domains": ["tracker.hhanclub.net"],
                            "tags": ["HHan"]
                        },
                        "Kufirc": {
                            "domains": ["kufirc.com"],
                            "tags": ["Kufirc"]
                        },
                    },
            }
    }
    cfg["config"].update(extra_cfg)
    cfg_path = os.path.join(td, "config.yml")
    with open(cfg_path, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False)
    return cfg_path


def _write_raw(td, text: str) -> str:
    """写入原始 yaml 文本(BaseLoader 语义: 全部标量为字符串, 留空为 None)"""
    path = os.path.join(td, "raw.yml")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def _load_errors(td, text: str) -> str:
    """加载配置并返回聚合错误文本(不抛错则返回空串)"""
    try:
        load_config(_write_raw(td, text))
        return ""
    except ConfigError as e:
        return str(e)


ROOT = Path(__file__).resolve().parents[1]


def _errs(cfg: dict) -> list:
    from auto_qb.config.validation import validate_config

    return validate_config({"config": cfg})
