"""`config_writer_support` 支撑: 从 `test_config_writer.py` 拆出的模块级辅助/常量(move-only 搬迁, 未改语义)."""

import copy

import os

import pytest

from auto_qb.config.errors import ConfigError

from auto_qb.config.loaders import load_config

from auto_qb.config.writer import materialize_schema_migration, preview_tree, read_tree, write_tree

from helpers import LEGACY_V1

# 「天生当前版本的干净文件」锚(当前 = v5): BASE 供各写盘用例当无 hr 的最小合法配置
BASE = "config:\n  qbittorrent:\n    host: h\n    port: 1\n    username: u\n    password: p\n  schema_version: 5\n"


def _make(tmp_path, text: str) -> str:
    path = tmp_path / "config.yml"
    path.write_text(text, encoding="utf-8")
    return str(path)


def _text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _bak(tmp_path) -> str:
    """测试用备份路径: 与生产同形落在独立 data 目录下(`<data_dir>/<配置名>.bak`)"""
    return str(tmp_path / "data" / "config.yml.bak")


# v4 形态: 站点 '' = 覆盖为空(合法稀疏条目, 迁移不得误杀)
V4_SITE_EMPTY = (
    "config:\n"
    "  schema_version: 4\n"
    "  hr:\n"
    "    add_tag: zGlobal\n"
    "  trackers:\n"
    "    A:\n"
    "      domains: [a.com]\n"
    "      hr:\n"
    "        required_seeding_time: 3D\n"
    "        add_tag: ''\n"
)
