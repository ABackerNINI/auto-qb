"""bencode 解码与 infohash 计算(零依赖, 服务于 .torrent 对账)。

为什么自写而不是引第三方: infohash 必须对 **info dict 在原文件中的原始字节切片** 取哈希 ——
decode 后 re-encode 会因键序/整数表示漂移算出错误 infohash (计划 §5)。自写解析器才能在遍历
顶层字典时同步记录 info 值的 [start, end) 字节跨度。

性能: 定位 info 跨度时**不解码 info 的值**(它可能含数 MB 的 pieces 串与上千条 files),
只做字节跳跃 `_skip` —— 大种子下这是数量级的差别。

正确性由 tests/test_hr_bencode.py 的钉死向量守住(向量由独立编码器生成)。
"""
import hashlib
from typing import Dict, List, Tuple, Union

# 解析深度上限: 合法 .torrent 嵌套极浅(顶层 d -> info d -> files l -> d), 深链只可能是畸形/恶意输入
MAX_DEPTH = 64

BValue = Union[bytes, int, List["BValue"], Dict[bytes, "BValue"]]


def _read_int(data: bytes, pos: int) -> Tuple[int, int]:
    """读 `i<n>e`; 返回 (值, 下一个位置)。规范要求无前导零(畸形直接拒, 免得算出错 hash)。"""
    end = data.find(b"e", pos + 1)
    if end < 0:
        raise ValueError(f"bencode 整数未闭合 @ {pos}")
    text = data[pos + 1:end]
    digits = text[1:] if text[:1] == b"-" else text
    if not digits or not digits.isdigit():
        raise ValueError(f"bencode 整数非法 @ {pos}: {text[:16]!r}")
    if (digits[:1] == b"0" and len(digits) > 1) or text == b"-0":
        raise ValueError(f"bencode 整数非规范(前导零 / -0) @ {pos}: {text[:16]!r}")
    return int(text), end + 1


def _read_bytes(data: bytes, pos: int) -> Tuple[bytes, int]:
    """读 `<len>:<bytes>`; 返回 (值, 下一个位置)"""
    colon = data.find(b":", pos)
    if colon < 0:
        raise ValueError(f"bencode 字节串缺少长度分隔符 @ {pos}")
    length_text = data[pos:colon]
    if not length_text.isdigit() or (length_text[:1] == b"0" and len(length_text) > 1):
        raise ValueError(f"bencode 字节串长度非法 @ {pos}: {length_text[:16]!r}")
    start = colon + 1
    end = start + int(length_text)
    if end > len(data):
        raise ValueError("bencode 字节串长度超出数据范围")
    return data[start:end], end


def bdecode(data: bytes, pos: int = 0, _depth: int = 0) -> Tuple[BValue, int]:
    """最小 bencode 解码: 返回 (value, next_pos)。

    字节串 -> bytes, 整数 -> int, 列表 -> list, 字典 -> dict(bytes -> value)。
    仅做解码; 畸形输入抛 ValueError (由调用方决定是丢弃还是上抛)。
    """
    if _depth > MAX_DEPTH:
        raise ValueError(f"bencode 嵌套过深 (> {MAX_DEPTH})")
    if pos >= len(data):
        raise ValueError("bencode 数据意外结束")
    c = data[pos:pos + 1]
    if c == b"i":
        return _read_int(data, pos)
    if c == b"l":
        pos += 1
        out: List[BValue] = []
        while True:
            if pos >= len(data):
                raise ValueError(f"bencode 列表未闭合 @ {pos}")
            if data[pos:pos + 1] == b"e":
                return out, pos + 1
            value, pos = bdecode(data, pos, _depth + 1)
            out.append(value)
    if c == b"d":
        pos += 1
        out: Dict[bytes, BValue] = {}
        while True:
            if pos >= len(data):
                raise ValueError(f"bencode 字典未闭合 @ {pos}")
            if data[pos:pos + 1] == b"e":
                return out, pos + 1
            key, pos = bdecode(data, pos, _depth + 1)
            if not isinstance(key, bytes):
                raise ValueError(f"bencode 字典键必须是字节串 @ {pos}")
            value, pos = bdecode(data, pos, _depth + 1)
            out[key] = value
    if c.isdigit():
        return _read_bytes(data, pos)
    raise ValueError(f"bencode 非法字节 @ {pos}: {data[pos : pos + 8]!r}")


def _skip(data: bytes, pos: int, _depth: int = 0) -> int:
    """跳过一段 bencode 值, 返回其后的位置(不构造对象)。定位 info 跨度时避免解码整个 info。"""
    if _depth > MAX_DEPTH:
        raise ValueError(f"bencode 嵌套过深 (> {MAX_DEPTH})")
    if pos >= len(data):
        raise ValueError("bencode 数据意外结束")
    c = data[pos:pos + 1]
    if c == b"i":
        return _read_int(data, pos)[1]
    if c == b"l":
        pos += 1
        while True:
            if pos >= len(data):
                raise ValueError(f"bencode 列表未闭合 @ {pos}")
            if data[pos:pos + 1] == b"e":
                return pos + 1
            pos = _skip(data, pos, _depth + 1)
    if c == b"d":
        pos += 1
        while True:
            if pos >= len(data):
                raise ValueError(f"bencode 字典未闭合 @ {pos}")
            if data[pos:pos + 1] == b"e":
                return pos + 1
            pos = _skip(data, pos, _depth + 1)  # 键
            pos = _skip(data, pos, _depth + 1)  # 值
    if c.isdigit():
        return _read_bytes(data, pos)[1]
    raise ValueError(f"bencode 非法字节 @ {pos}: {data[pos : pos + 8]!r}")


def info_span(data: bytes) -> Tuple[int, int]:
    """定位顶层 info 值的原始字节跨度, 返回 (start, end)。

    ❗这是 infohash 正确性的关键: **只接受原始切片**, 绝不 decode 后重编码。
    非 info 的顶层值正常跳过; info 的值只跳不建对象。
    """
    if not data.startswith(b"d"):
        raise ValueError("不是 bencode 字典 (应以 'd' 开头)")
    pos = 1
    while True:
        if pos >= len(data):
            raise ValueError("顶层字典未闭合")
        if data[pos:pos + 1] == b"e":
            raise ValueError("顶层字典里没有 info")
        key, pos = bdecode(data, pos)
        if key == b"info":
            return pos, _skip(data, pos)
        pos = _skip(data, pos)


def compute_infohashes(data: bytes) -> Tuple[str, str, Dict[bytes, BValue]]:
    """v1 = sha1(info 原始字节切片), v2 = sha256(同切片); 返回 (v1_hex, v2_hex, info_dict)。

    v2-only 种子同样由 sha256 得出 (qB >= 4.4 的 hash 字段即 v2 infohash); hybrid 双算双配。
    info_dict 用于取展示名等附加信息(仅此处解码一次)。
    """
    start, end = info_span(data)
    span = data[start:end]
    value, _ = bdecode(span)
    if not isinstance(value, dict):
        raise ValueError("info 不是字典")
    return hashlib.sha1(span).hexdigest(), hashlib.sha256(span).hexdigest(), value


def torrent_display_name(info: Dict[bytes, BValue]) -> str:
    """从 info dict 取展示名(仅日志/报告用; 与本地种子的匹配一律以 infohash 为准)"""
    raw = info.get(b"name")
    if isinstance(raw, bytes):
        return raw.decode("utf-8", "replace")
    return ""
