"""测试环境注册表 —— 端口 / 镜像路径 / EXE 的唯一来源(双环境)。

背景: 真机实测轨配置了两套物理环境(不同机器), 各带一对 portable qBittorrent-testing 实例:
  环境1 = D盘机: 主 36595 / 副 36596, exe 在 D:\\Programs\\qBittorrent-testing*;
  环境2 = C盘机: 主 56589 / 副 56590, exe 在 C:\\Programs\\qBittorrent-testing*。
同一时刻代码只对**一套**生效(当前环境), 由 `active()` 选出:
  1. 环境变量 `QBT_REAL_ENV`("1"/"2") 显式指定 —— 两套 exe 都存在的机器必须用它;
  2. 否则按 EXE 存在性自动探测(按 1→2 序, 第一个主实例 exe 在盘上的环境胜出);
  3. 都探测不到 → 报错(fail-closed), 不猜。

选定结果在进程内缓存一次 —— guard / instances / runner / 用例全部从这里派生,
不再各自硬编码端口或路径(此前单环境时代的做法, 换机即碎)。

多 clone 注意: 本机常有多个平行 clone, 但**物理测试实例(端口/进程)全机只有一套** ——
真机轨同一时刻只允许一个 clone 在跑 `real.*`, 端口与进程不共享。

免鉴权口径(2026-11-04 起): 四实例均已开 WebUI「跳过本地验证」, 本机直连零凭据,
token 注入机制(`QBT_TEST_<端口>` / instances.local.json)已退役删除 —— 见 lib/instances.py。
"""
from __future__ import annotations

import os
from pathlib import Path

_ENV_VAR = "QBT_REAL_ENV"

# EXE 键 = WebUI 端口; bt_listen 键 = WebUI 端口, 值 = 该实例的 BT 监听端口(RM00 实测,
# 两环境均已于 2026-11-01 实测回填; 用例拿它做"禁用端口"黑名单, 留空 = 只查 WebUI 白名单端口)。
ENVIRONMENTS: dict[str, dict] = {
    "1":
        {
            "machine": "D盘机",
            "primary": 36595,
            "secondary": 36596,
            "image_prefix": "D:\\Programs\\qBittorrent-testing",
            "exe":
                {
                    36595: "D:\\Programs\\qBittorrent-testing\\qbittorrent.exe",
                    36596: "D:\\Programs\\qBittorrent-testing2\\qbittorrent.exe",
                },
            "bt_listen": {
                36595: 26803,
                36596: 60539
            },
        },
    "2":
        {
            "machine": "C盘机",
            "primary": 56589,
            "secondary": 56590,
            "image_prefix": "C:\\Programs\\qBittorrent-testing",
            "exe":
                {
                    56589: "C:\\Programs\\qBittorrent-testing\\qbittorrent.exe",
                    56590: "C:\\Programs\\qBittorrent-testing2\\qbittorrent.exe",
                },
            "bt_listen": {
                56589: 27049,
                56590: 32719
            },  # 2026-11-01 首轮实测回填(规程 §2.5.2)
        },
}

_CACHE: dict | None = None


def _detect() -> dict:
    """按 EXE 存在性探测(1→2 序)。一个都没命中 → 报错不猜。"""
    for env in ENVIRONMENTS.values():
        if Path(env["exe"][env["primary"]]).is_file():
            return env
    raise RuntimeError(
        "探测不到测试环境(两套环境的 EXE 都不在盘上) —— 设 QBT_REAL_ENV=1|2 显式指定, "
        f"或核对 env_registry.ENVIRONMENTS 里的路径; 可选环境: {sorted(ENVIRONMENTS)}"
    )


def active() -> dict:
    """当前环境(进程内缓存): QBT_REAL_ENV 显式 > EXE 存在性探测。"""
    global _CACHE
    if _CACHE is None:
        raw = os.environ.get(_ENV_VAR, "").strip()
        if raw:
            if raw not in ENVIRONMENTS:
                raise RuntimeError(f"{_ENV_VAR}={raw!r} 不是合法环境 id, 可选: {sorted(ENVIRONMENTS)}")
            _CACHE = ENVIRONMENTS[raw]
        else:
            _CACHE = _detect()
    return _CACHE
