"""实例注册表 —— 端口的唯一来源(免鉴权口径, 2026-11-04 起)。

端口/镜像路径/EXE 全部从 `lib/env_registry.py` 派生(双环境: D盘机 36595/36596,
C盘机 56589/56590; 见 env_registry docstring)。

**四实例本地一律免鉴权**: 主副实例均已开启 WebUI「跳过本地验证」
(bypass_local_auth), 本机直连不需要任何 token/凭据 —— 用户永不需要提供 token。
(历史机制 `QBT_TEST_<端口>` 环境变量注入与 instances.local.json 已于 2026-11-04 退役删除。)
(历史备注: 环境1 36596 出厂即 LocalHostAuth=false, plan 26-10-31-0705 D2;
环境2 56590 由用户拍板 `bypass_local_auth=True`, 2026-11-01 —— RM03 轮 401 封禁
连环事故见切片 26-11-01-1214 §04-1。)

若哪天收到 401/403(如 qB 升级/重装重置了该设置), `lib/qb.py` 按 fail-closed 报错
停手, 错误信息直指「去 qB WebUI 重新勾选跳过本地验证」—— 修环境, 不加绕行机制。
"""
from __future__ import annotations

from . import env_registry
from .qb import Qb

_ENV = env_registry.active()
PRIMARY = _ENV["primary"]  # 主实例: L2 的做种端
SECONDARY = _ENV["secondary"]  # 副实例: 空库, L2 的下载端 / 草稿本


def make(port: int) -> Qb:
    return Qb(port)
