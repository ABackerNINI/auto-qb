"""test_qbapi_wire 测试计划: qB WebAPI 请求体级守阵(真 qbittorrent-api Client + 真 requests/urllib3
栈经 FakeQbServer 走完整 HTTP 往返, 按线上原文断言字段在位 —— 单元替身 FakeClient 只见 kwargs,
看不见 requests 编码层的 None 丢弃与 multipart 形态, 那层事实只有这里能钉)

背景(issue 26-10-31-0711-bug-qbapi-share-limits-mode / 26-10-31-0716-chore-qbittorrentapi-bump-dual-version):
qB 5.3 把 torrents/setShareLimits 的 shareLimitsMode 列为必填(缺失 400), 跳检免校验的 5.3 兼容
完全依赖库对 torrents/add 的 skip_checking/seedMode 双发 —— 两者都是"库/请求编码层"契约,
库降版或编码行为回归时本文件先红。

## 测试计划(每个测试函数一条)
- test_set_share_limits_wire_body_carries_share_limits_mode: setShareLimits 请求体含
  shareLimitsMode=Default(facade 恒传, 5.3 必填参守阵)
- test_set_share_limits_none_mode_not_sent: share_limits_mode=None 时请求体无 shareLimitsMode 键
  (requests 对 None 值键一律丢弃 —— facade docstring 修正后的真实语义; 也是 5.2 重加 wire 不变的依据)
- test_torrents_add_wire_body_dual_send_and_camel_case_kwarg: torrents/add 请求体同时含
  skip_checking 与 seedMode(双发守阵, 库降版先红)且 camelCase kwarg shareLimitsMode 透传
  (2026.8.1 无具名参, 经 _format_payload kwargs 并入 POST data; snake_case 会发错键名被 5.3 静默忽略)
- test_torrents_add_none_mode_part_absent: torrents/add 传 shareLimitsMode=None 时 multipart
  请求体无 shareLimitsMode 字段(multipart None 丢弃)
"""
from urllib.parse import parse_qs

from qbittorrentapi import Client

from helpers import FakeQbServer


def _client(srv) -> Client:
    client = Client(host=f"http://127.0.0.1:{srv.port}", username="u", password="p")
    client.auth_log_in()
    return client


def _bodies(srv, route: str) -> list:
    return [raw for r, raw in srv.bodies if r == route]


def test_set_share_limits_wire_body_carries_share_limits_mode():
    """setShareLimits 请求体含 shareLimitsMode=Default(qB 5.3 必填参, 缺失 400)"""
    with FakeQbServer() as srv:
        client = _client(srv)
        client.torrents_set_share_limits(
            ratio_limit="1.0",
            seeding_time_limit=-1,
            inactive_seeding_time_limit=-2,
            torrent_hashes="a" * 40,
            share_limits_mode="Default",
        )
        bodies = _bodies(srv, "torrents/setShareLimits")
        assert bodies, "应命中 setShareLimits 端点"
        qs = parse_qs(bodies[-1])
        assert qs.get("shareLimitsMode") == ["Default"], f"请求体须含 shareLimitsMode=Default: {qs}"
        assert qs.get("ratioLimit") == ["1.0"], "哨兵语义其余维度照发"


def test_set_share_limits_none_mode_not_sent():
    """share_limits_mode=None 时请求体无 shareLimitsMode 键(requests 对 None 值键一律丢弃)"""
    with FakeQbServer() as srv:
        client = _client(srv)
        client.torrents_set_share_limits(
            ratio_limit="1.0",
            seeding_time_limit=-1,
            inactive_seeding_time_limit=-2,
            torrent_hashes="a" * 40,
            share_limits_mode=None,
        )
        bodies = _bodies(srv, "torrents/setShareLimits")
        assert bodies, "应命中 setShareLimits 端点"
        qs = parse_qs(bodies[-1])
        assert "shareLimitsMode" not in qs, f"None 值键应被 requests 丢弃而不是发出: {qs}"


def test_torrents_add_wire_body_dual_send_and_camel_case_kwarg():
    """torrents/add 请求体同时含 skip_checking 与 seedMode(库双发, 降版先红);
    camelCase kwarg shareLimitsMode 透传(snake_case 会发错键名被 5.3 静默忽略)"""
    with FakeQbServer() as srv:
        client = _client(srv)
        client.torrents_add(
            torrent_files=[b"d4:infod6:lengthi1e4:name1:t6:pieceslee"],
            is_skip_checking=True,
            shareLimitsMode="MatchAny",
        )
        bodies = _bodies(srv, "torrents/add")
        assert bodies, "应命中 add 端点"
        raw = bodies[-1]
        assert 'name="skip_checking"' in raw, f"双发守阵: skip_checking 须在请求体: {raw[:400]}"
        assert 'name="seedMode"' in raw, f"双发守阵: seedMode 须在请求体(5.3 只读它): {raw[:400]}"
        assert 'name="shareLimitsMode"' in raw and "MatchAny" in raw, \
            f"camelCase kwarg 须并入 multipart 请求体: {raw[:400]}"


def test_torrents_add_none_mode_part_absent():
    """torrents/add 传 shareLimitsMode=None 时 multipart 请求体无该字段"""
    with FakeQbServer() as srv:
        client = _client(srv)
        client.torrents_add(
            torrent_files=[b"d4:infod6:lengthi1e4:name1:t6:pieceslee"],
            is_skip_checking=True,
            shareLimitsMode=None,
        )
        bodies = _bodies(srv, "torrents/add")
        assert bodies, "应命中 add 端点"
        assert 'name="shareLimitsMode"' not in bodies[-1], \
            f"None 值键在 multipart 下也应丢弃: {bodies[-1][:400]}"
