"""实例注册表 —— 端口与凭据的唯一来源。

端口/镜像路径/EXE 全部从 `lib/env_registry.py` 派生(双环境: D盘机 36595/36596,
C盘机 56589/56590; 见 env_registry docstring), 本文件只管**凭据**:

token **不保存不落盘**, 由用户每轮会话给出, 经环境变量 `QBT_TEST_<端口>` 注入
(如 `QBT_TEST_36595` / `QBT_TEST_56589` —— 键按端口, 两环境端口不同天然不冲突)。
(历史机制)本地文件 `tests-real/config/instances.local.json`(已 gitignore)仍被读取,
形如 `{"36595": {"token": "qbt_..."}}` —— 但当前口径是**不创建它**, 别把 token 写进盘。

副实例(testing2)在本机常为免鉴权(LocalHostAuth=false), 见 plan 26-10-31-0705 D2;
`lib/qb.py` 的鉴权降级会自动处理两种情况。
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from . import env_registry
from .qb import Qb

_ENV = env_registry.active()
PRIMARY = _ENV["primary"]  # 主实例: 有真实种子, 也是 L2 的做种端
SECONDARY = _ENV["secondary"]  # 副实例: 空库, L2 的下载端 / 草稿本
TOKEN_ENV = {PRIMARY: f"QBT_TEST_{PRIMARY}", SECONDARY: f"QBT_TEST_{SECONDARY}"}
LOCAL_FILE = Path(__file__).resolve().parents[1] / "config" / "instances.local.json"


def _local_tokens() -> dict[str, str]:
    if not LOCAL_FILE.is_file():
        return {}
    try:
        raw = json.loads(LOCAL_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return {str(k): (v or {}).get("token", "") for k, v in raw.items()}


def token_for(port: int) -> str | None:
    return os.environ.get(TOKEN_ENV[port]) or _local_tokens().get(str(port)) or None


def make(port: int) -> Qb:
    return Qb(port, token=token_for(port))
