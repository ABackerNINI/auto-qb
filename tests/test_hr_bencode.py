"""test_hr_bencode 测试计划: HR 对账用的 bencode 解码与 infohash 计算

## 测试计划(每个测试函数一条)
- test_bdecode_basic_types: 字节串/整数/列表/字典解码与位置推进
- test_infohash_matches_pinned_vectors: 实验脚本带来的钉死向量(base64)得到同一组 v1/v2
- test_infohash_uses_raw_info_slice_not_reencode: **核心坑** —— hash 必须取 info 的原始字节切片,
  重编码(键序/整数表示漂移)会算出不同的 hash
- test_info_span_handles_trailing_top_level_keys: info 之后还有顶层键(如 private)时切片边界仍正确
- test_compute_infohashes_returns_info_dict: 返回的 info 字段可读(取展示名)
- test_torrent_display_name: 名字解码与缺失兜底
- test_rejects_malformed_input: 非字典开头 / 缺 info / 长度越界 / 截断 / 非法整数 / 嵌套过深
- test_rejects_non_canonical_integers: 前导零与 -0 一律拒(避免算出与站点不一致的 hash)
"""
import base64
import hashlib

import pytest

from auto_qb.hr.bencode import bdecode, compute_infohashes, info_span, torrent_display_name
from hr_helpers import torrent_blob

# 与 scripts/hr_fetch_experiment.py 完全一致的钉死向量(由独立编码器生成后 base64 装载,
# 避开 repr 里的 \t/\n 经工具层被变成真实控制字符)
_PINNED = [
    (
        "ZDg6YW5ub3VuY2UyNTpodHRwOi8vdC5leGFtcGxlL2Fubm91bmNlNDppbmZvZDY6bGVuZ3RoaTVlNDpuYW1lNTphLmJp"
        "bjEyOnBpZWNlIGxlbmd0aGkxNjM4NGU2OnBpZWNlczIwOgAAAAAAAAAAAAAAAAAAAAAAAAAAZWU=",
        "3cc95307628a6ee049939b7fe016c05785e95bf7",
        "d3fa2e18585e3be68da3c9bd54bd8abc47d48e18b54644b965b0c95a8d4fa033",
        b"a.bin",
    ),
    (
        "ZDg6YW5ub3VuY2UyNTpodHRwOi8vdC5leGFtcGxlL2Fubm91bmNlNzpjb21tZW50MjI6aHItZXhwZXJpbWVudCBz"
        "ZWxmdGVzdDQ6aW5mb2Q2Omxlbmd0aGkxMDQ4NTc2ZTQ6bmFtZTEwOua1i+ivlS5iaW4xMjpwaWVjZSBsZW5ndGhpMjYy"
        "MTQ0ZTY6cGllY2VzMjA6AAECAwQFBgcICQoLDA0ODxAREhNlNzpwcml2YXRlaTFlZQ==",
        "786b051887df6be782953b6d43ec9da57525bad5",
        "5a45147916aa9f8920c5737a65e54a4363a9cac397427d108a851bc78838ce93",
        "测试.bin".encode(),
    ),
]


def test_bdecode_basic_types():
    """字节串/整数/列表/字典解码与位置推进"""
    value, pos = bdecode(b"i42e")
    assert (value, pos) == (42, 4)
    value, pos = bdecode(b"5:hello")
    assert (value, pos) == (b"hello", 7)
    value, pos = bdecode(b"li1e3:abce")
    assert value == [1, b"abc"]
    assert pos == 10
    value, _ = bdecode(b"d1:ai1e1:bl1:xee")
    assert value == {b"a": 1, b"b": [b"x"]}


def test_infohash_matches_pinned_vectors():
    """实验脚本的钉死向量得到同一组 v1/v2(回归保护: 换实现不得漂移)"""
    for b64, want_v1, want_v2, want_name in _PINNED:
        data = base64.b64decode(b64)
        v1, v2, info = compute_infohashes(data)
        assert v1 == want_v1
        assert v2 == want_v2
        assert info[b"name"] == want_name


def test_infohash_uses_raw_info_slice_not_reencode():
    """hash 取 info 的原始字节切片; 重编码(键序不同)会算出不同 hash —— 钉死计划 §5 的坑"""
    raw = torrent_blob(name="order.bin")
    start, end = info_span(raw)
    span = raw[start:end]
    v1, v2, _ = compute_infohashes(raw)
    assert v1 == hashlib.sha1(span).hexdigest()
    assert v2 == hashlib.sha256(span).hexdigest()

    # 同一份 info 内容, 键序被重排 => 切片不同 => hash 不同(证明「不能 decode 再 re-encode」)
    reordered = raw.replace(b"6:lengthi1024e4:name9:order.bin", b"4:name9:order.bin6:lengthi1024e", 1)
    assert reordered != raw and len(reordered) == len(raw)
    v1b, _, info_b = compute_infohashes(reordered)
    assert info_b == {b"length": 1024, b"name": b"order.bin", b"piece length": 16384, b"pieces": b"\x00" * 20}
    assert v1b != v1


def test_info_span_handles_trailing_top_level_keys():
    """info 之后还有顶层键(如 private)时切片边界仍正确(切片不能粗切到结尾)"""
    with_tail = torrent_blob(name="tail.bin", private=True)
    without_tail = torrent_blob(name="tail.bin", private=False)
    start, end = info_span(with_tail)
    assert with_tail[start:end] == without_tail[info_span(without_tail)[0]:info_span(without_tail)[1]]
    assert not with_tail[end:].startswith(b"e")  # info 之后仍有内容(private 键)


def test_compute_infohashes_returns_info_dict():
    """返回的 info 字段可读(取展示名 / 诊断), 且是真正解码后的对象"""
    _, _, info = compute_infohashes(torrent_blob(name="doc.bin", length=777))
    assert info[b"length"] == 777
    assert torrent_display_name(info) == "doc.bin"


def test_torrent_display_name():
    """名字解码与缺失兜底"""
    assert torrent_display_name({b"name": b"a.bin"}) == "a.bin"
    assert torrent_display_name({b"name": "中文.bin".encode("utf-8")}) == "中文.bin"
    assert torrent_display_name({}) == ""
    assert torrent_display_name({b"name": 123}) == ""


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"i1e",  # 不是字典
        b"d4:infoxe",  # info 不是字典
        b"d1:a5:abce",  # 没有 info
        b"d4:info9:abcde",  # 字节串长度越界
        b"d4:infoi1",  # 截断(整数未闭合)
        b"d4:infoli1e",  # 截断(列表未闭合)
        b"d4:infoi01ee",  # 前导零
        b"d4:infoi-0ee",  # -0
        b"x",  # 非法首字节
    ],
)
def test_rejects_malformed_input(data):
    """畸形输入一律抛 ValueError, 不静默产出错误 hash"""
    with pytest.raises(ValueError):
        compute_infohashes(data)


def test_rejects_non_canonical_integers():
    """前导零 / -0 在 bdecode 层就被拒(信息更早暴露, 不等到算 hash)"""
    with pytest.raises(ValueError):
        bdecode(b"i007e")
    with pytest.raises(ValueError):
        bdecode(b"i-0e")
    with pytest.raises(ValueError):
        bdecode(b"03:abc")
    with pytest.raises(ValueError):
        bdecode(b"i-e")
    assert bdecode(b"i-17e")[0] == -17


def test_rejects_deep_nesting():
    """嵌套过深直接拒(畸形/恶意输入不得拖垮进程)"""
    deep = b"l" * 200 + b"e" * 200
    with pytest.raises(ValueError):
        bdecode(deep)
