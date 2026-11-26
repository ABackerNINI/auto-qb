"""`qbmanager_support` 支撑: 从 `test_qbmanager.py` 拆出的模块级辅助/常量(move-only 搬迁, 未改语义)."""

import json

import logging

import os

import tempfile

import threading

import time

from unittest import mock

from auto_qb.core.taskqueue import FINISHED, PENDING, REQUEUE, Task, TaskQueue

import pytest

from qbittorrentapi import APIConnectionError, Client

from auto_qb.config import QbittorrentConfig

from auto_qb.config import PathMapEntry

from auto_qb.config.models import FsConfig

from auto_qb.infra.errors import AutoQbError

from auto_qb.infra import file_access

from auto_qb.infra.file_access import MappedFileAccess

from auto_qb.core.module import ApplyResult

from auto_qb.core import qbmanager as _qbm

from auto_qb.core.qbclient import REQUESTS_TIMEOUT, LocalQbClient, new_client

from auto_qb.core.qbmanager import RECONNECT_MAX_INTERVAL, QbConnectError, QbManager, _wait_next

from auto_qb.torrents import QbCompatError

from helpers import LEGACY_V1, FakeClient, FakeConfig, FakeTorrent, capture_logs, make_manager, seed_store


def _daemon_timer(seconds, fn):
    """后台兜底停止定时器(变异环/挂起防呆): 到点置 stop, 正常路径自行 cancel"""
    t = threading.Timer(seconds, fn)
    t.daemon = True
    t.start()
    return t
