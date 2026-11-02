"""`webui_dom_panel_support` 支撑: 从 `test_webui_static_dom_panel.py` 拆出的模块级辅助/常量(move-only 搬迁, 未改语义)."""

import json

import os

import re

import shutil

import subprocess

from pathlib import Path

from auto_qb.webui.commands import REANNOUNCE_BLOCKED_STATES as _PY_BLOCKED_STATES

from auto_qb.webui.commands import REANNOUNCE_INACTIVE_SKIP as _PY_INACTIVE_SKIP

from webui_helpers import (
    STATIC_ROOT,
    _UI_ALL,
    _ui_manifest,
    _ui_aggregate,
    _ui_css_aggregate,
    _ui_css_effective,
    _app_bundle_files,
    _app_bundle_text,
)


def _tpl_body(tpl_text: str, tpl_id: str) -> str:
    """取出 x-template 片段里某个 `<script type="text/x-template" id="...">` 的模板体。

    无构建链下 `shared/tpl/*.html` 是**裸字符串模板**(见 pitfalls/web-ui/frontend-split.md),
    结构断言只能在源文本上做 —— 本助手提供「拿到片段本体」这一步, 供 _tpl_top_level_tags 判根数。
    """
    m = re.search(r'<script type="text/x-template" id="' + re.escape(tpl_id) + r'">(.*?)</script>', tpl_text, re.S)
    assert m, f"模板片段 {tpl_id} 不在所给文本里(片段改名/换文件? 同步本守阵)"
    return m.group(1)
