"""构造单文件 .torrent —— 真机实测的「假种子」来源。

要点: announce 指到本地伪 tracker(或干脆不带 announce), 内容由我们自己写进临时目录 ⇒
qB 能完成校验并进入做种, 但**没有任何真实 tracker 被联系**, 所以流量物理上出不了本机。

两种造法:
  - `build(name, payload, ...)` —— 内容在内存里(用例用, 几 MB 以内);
  - `build_from_path(path, ...)` —— 内容已在磁盘上(CLI 用, 支持 GB 级, 内存恒定)。
"""
from __future__ import annotations

import hashlib
import os
import random

from .bencode import encode

PIECE_LEN = 16384
COMMENT = "auto-qb real-machine test (fake seed)"
CHUNK = 1024 * 1024  # 生成/落盘的分块大小


def _make_torrent(name: str, length: int, pieces: bytes, announce: str | None,
                  piece_len: int, comment: str) -> tuple[bytes, str]:
    info = {"name": name, "length": length, "piece length": piece_len, "pieces": pieces, "private": 1}
    infohash = hashlib.sha1(encode(info)).hexdigest()
    torrent = {"info": info, "comment": comment}
    if announce:  # 不给 announce ⇒ 纯本地做种, qB 不会去联系任何站点
        torrent["announce"] = announce
    return encode(torrent), infohash


def build(name: str, payload: bytes, announce: str | None = None, piece_len: int = PIECE_LEN,
          comment: str = COMMENT) -> tuple[bytes, str]:
    """返回 (.torrent 字节, infohash 十六进制)。"""
    pieces = b"".join(hashlib.sha1(payload[i:i + piece_len]).digest() for i in range(0, len(payload), piece_len))
    return _make_torrent(name, len(payload), pieces, announce, piece_len, comment)


class _ChunkReader:
    """把「块迭代器」包装成 `read(n)` —— 让 piece 计算与来源(内存/磁盘/生成器)解耦。"""

    def __init__(self, blocks):
        self._it = iter(blocks)
        self._buf = b""

    def read(self, n: int) -> bytes:
        while len(self._buf) < n:
            try:
                self._buf += next(self._it)
            except StopIteration:
                break
        out, self._buf = self._buf[:n], self._buf[n:]
        return out


def _pieces(read, piece_len: int) -> bytes:
    """按 piece_len 逐块 sha1, 返回拼接后的 pieces 字段。"""
    pieces = bytearray()
    while True:
        chunk = read(piece_len)
        if not chunk:
            break
        pieces += hashlib.sha1(chunk).digest()
    return bytes(pieces)


def build_from_path(path: str, name: str | None = None, announce: str | None = None,
                    piece_len: int = PIECE_LEN, comment: str = COMMENT) -> tuple[bytes, str]:
    """按磁盘上已有的文件造种子(流式读, 内存不随文件大小涨)。"""
    name = name or os.path.basename(path)
    with open(path, "rb") as f:
        pieces = _pieces(f.read, piece_len)
    return _make_torrent(name, os.path.getsize(path), pieces, announce, piece_len, comment)


def build_stream(name: str, size: int, pattern: str = "random", salt: str = "auto-qb",
                 announce: str | None = None, piece_len: int = PIECE_LEN,
                 comment: str = COMMENT) -> tuple[bytes, str]:
    """不落盘直接算 piece —— 给"只造种子不造数据"(--no-data)用, 内存恒定。"""
    pieces = _pieces(_ChunkReader(chunks(size, pattern, salt)).read, piece_len)
    return _make_torrent(name, size, pieces, announce, piece_len, comment)


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


# ---------------------------------------------------------------- 生成方式(CLI 用, 流式)
PATTERNS = ("random", "zeros", "text")


def chunks(size: int, pattern: str = "random", salt: str = "auto-qb"):
    """按块产出内容。**同 (size, pattern, salt) ⇒ 同内容 ⇒ 同 infohash**, 便于幂等重跑。

    - `random`: 由 salt 播种的伪随机(确定性, 不同块互不相同, 速度接近磁盘上限);
    - `zeros`:  全零(最快, 用来造"只看大小"的种子);
    - `text`:   可读文本行(便于人眼看文件、手工改几行做破坏性试验)。
    """
    if pattern not in PATTERNS:
        raise ValueError(f"未知生成方式 {pattern!r}, 可选 {PATTERNS}")
    left = size
    if pattern == "zeros":
        while left > 0:
            n = min(CHUNK, left)
            yield b"\0" * n
            left -= n
        return
    if pattern == "text":
        i = 0
        salt_b = salt.encode()
        while left > 0:
            want = min(CHUNK, left)
            buf = bytearray()
            while len(buf) < want:
                buf += b"auto-qb fake seed line %08d salt=%s\n" % (i, salt_b)
                i += 1
            yield bytes(buf[:want])
            left -= want
        return
    rng = random.Random(f"auto-qb:{salt}")
    while left > 0:
        n = min(CHUNK, left)
        yield rng.randbytes(n)
        left -= n


def write_file(path: str, size: int, pattern: str = "random", salt: str = "auto-qb") -> str:
    """流式把内容写到 path(父目录自动建), 返回绝对路径。"""
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    with open(path, "wb") as f:
        for block in chunks(size, pattern, salt):
            f.write(block)
    return os.path.abspath(path)
