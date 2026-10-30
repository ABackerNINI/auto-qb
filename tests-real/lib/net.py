"""本机地址与「本地 tracker」判定 —— 真机实测轨的网络前提。

为什么不用 127.0.0.1 做 announce: qB 这两个测试实例把出站 socket 绑在「以太网」接口上,
连 127.0.0.1 会直接失败(tracker 状态 4, 报文「该请求的地址无效」= WSAEADDRNOTAVAIL)。
改用**本机局域网地址**后 announce 正常(状态 2), 而目标仍是本机自己 —— 流量不出网卡, 也不出这台机器。
"""
from __future__ import annotations

import os
import socket
from urllib.parse import urlparse

_CACHE: dict[str, str] = {}


def local_host() -> str:
    """本机地址(可用 QBT_TEST_HOST 覆盖; 默认取主机名解析出的地址)。"""
    if "h" not in _CACHE:
        _CACHE["h"] = os.environ.get("QBT_TEST_HOST") or socket.gethostbyname(socket.gethostname())
    return _CACHE["h"]


def is_local_url(url: str) -> bool:
    """tracker 地址是否指向本机(127.0.0.1 / localhost / 本机局域网地址)。"""
    host = (urlparse(url).hostname or "").lower()
    return host in ("127.0.0.1", "localhost", "::1", local_host().lower())
