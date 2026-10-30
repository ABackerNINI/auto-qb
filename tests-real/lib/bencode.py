"""bencode 编解码(只覆盖造种子与读 tracker 响应需要的最小子集)。"""
from __future__ import annotations


def encode(obj) -> bytes:
    if isinstance(obj, int):
        return b"i%de" % obj
    if isinstance(obj, str):
        obj = obj.encode()
    if isinstance(obj, (bytes, bytearray)):
        return b"%d:%s" % (len(obj), bytes(obj))
    if isinstance(obj, (list, tuple)):
        return b"l" + b"".join(encode(x) for x in obj) + b"e"
    if isinstance(obj, dict):
        items = sorted((k.encode() if isinstance(k, str) else k, v) for k, v in obj.items())
        return b"d" + b"".join(encode(k) + encode(v) for k, v in items) + b"e"
    raise TypeError(f"bencode 不支持的类型: {type(obj)!r}")


def decode(data: bytes, pos: int = 0):
    """返回 (值, 新位置)。"""
    c = data[pos:pos + 1]
    if c == b"i":
        end = data.index(b"e", pos)
        return int(data[pos + 1:end]), end + 1
    if c == b"l":
        pos += 1
        out = []
        while data[pos:pos + 1] != b"e":
            v, pos = decode(data, pos)
            out.append(v)
        return out, pos + 1
    if c == b"d":
        pos += 1
        out = {}
        while data[pos:pos + 1] != b"e":
            k, pos = decode(data, pos)
            v, pos = decode(data, pos)
            out[k] = v
        return out, pos + 1
    colon = data.index(b":", pos)
    n = int(data[pos:colon])
    start = colon + 1
    return data[start:start + n], start + n


def decode_all(data: bytes):
    return decode(data)[0]
