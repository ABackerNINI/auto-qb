"""实例注册表 —— 端口与凭据的唯一来源。

凭据**不进仓库**(它是测试实例的 API key, 但也别养成提交密钥的习惯), 两级来源:
  1. 环境变量 `QBT_TEST_36595` / `QBT_TEST_36596`;
  2. 本地文件 `tests-real/config/instances.local.json`(已 gitignore), 形如
     `{"36595": {"token": "qbt_..."}}` —— 换机器时照 `instances.example.json` 抄一份即可。

36596 现在是本机免鉴权(见 plan 26-10-31-0705 D2), 不给凭据也能用; 36595 仍需 token。
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from .qb import Qb

TOKEN_ENV = {36595: "QBT_TEST_36595", 36596: "QBT_TEST_36596"}
PRIMARY = 36595  # 主实例: 有真实种子, 也是 L2 的做种端
SECONDARY = 36596  # 副实例: 空库, L2 的下载端
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
