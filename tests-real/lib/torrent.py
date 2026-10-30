"""构造单文件 .torrent —— 真机实测的「假种子」来源。

要点: announce 指到本地伪 tracker, 内容由我们自己写进临时目录 ⇒ qB 能完成校验并进入做种,
但**没有任何真实 tracker 被联系**, 所以流量物理上出不了本机。
"""
from __future__ import annotations

import hashlib
import os

from . import bencode

PIECE_LEN = 16384


def build(name: str, payload: bytes, announce: str, piece_len: int = PIECE_LEN) -> tuple[bytes, str]:
    """返回 (.torrent 字节, infohash 十六进制)。"""
    pieces = b"".join(hashlib.sha1(payload[i:i + piece_len]).digest() for i in range(0, len(payload), piece_len))
    info = {"name": name, "length": len(payload), "piece length": piece_len, "pieces": pieces, "private": 1}
    infohash = hashlib.sha1(bencode.encode(info)).hexdigest()
    torrent = {"announce": announce, "info": info, "comment": "auto-qb real-machine test (RM00)"}
    return bencode.encode(torrent), infohash


def write_payload(directory: str, name: str, payload: bytes) -> str:
    """把内容落到目录里(单文件种子), 返回文件绝对路径。"""
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, name)
    with open(path, "wb") as f:
        f.write(payload)
    return path


def payload(size: int = 256 * 1024, seed: bytes = b"auto-qb-rm00") -> bytes:
    """确定性内容(可复跑): 反复扩写 seed 到目标大小。"""
    out = bytearray()
    i = 0
    while len(out) < size:
        out += hashlib.sha256(seed + i.to_bytes(4, "big")).digest()
        i += 1
    return bytes(out[:size])
