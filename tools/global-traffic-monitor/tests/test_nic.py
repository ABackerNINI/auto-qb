"""nic 守阵: 布局守卫 / 名称解码 / 名单映射与拓扑刷新 / 启动交叉校验 / 轮内单读与运行期回退.

设计单点: issue 26-10-20-2345 (方案 E: Windows 原生 GetIfTable2 整表 + psutil 回退).
除 live 用例 (skipif 非 Windows) 外全部 hermetic: 表行 / 名单 / psutil 读数一律注入替身.

## 测试计划

- 布局守卫: sizeof == 1352; OperStatus/AdminStatus/InOctets/OutOctets 偏移双平台同值
- decode_alias: utf-16-le + NUL 尾 / 空名 / 中文名
- row_views: isup 同式 (OperStatus==Up 且 AdminStatus==Up), LUID 集合, Out->sent / In->recv 映射
- NicMapper: 只出名单键 (表内多余行不收编) / 别名缺行刷新重试自愈 / LUID 集合变化触发名单刷新 /
  名单名撞多行 MappingError / 刷新后仍缺行 MappingError
- _pair_consistent: 键集差 / isup 差 / 单调违背 / 无界增量 / 容差内通过
- _NativePair: counters 先读 stats 复用同拍 (整表只读一次) / 单独 stats 自读 /
  读取异常当轮回退 psutil / 告警首错必发 + 限频 + 成功清零
- _resolve: 非 win32 直接 psutil / win32 原生可用用原生 / 原生不可用回退 + WARNING
- default_providers: 懒决议 (构造不解析, 首次调用才解析且进程内只一次)
- live (win32): 真机默认对 + Sampler().sample_once() 全链可用 (只读, 不断言走哪条路径)
"""

from __future__ import annotations

import ctypes
import logging
import sys
from types import SimpleNamespace
from typing import Mapping

import pytest

from gtm import nic
from gtm.nic import IoRow, MappingError, NicMapper, NicSnapshot, StatsRow, decode_alias, row_views
from gtm.sampler import SampleResult, Sampler


def fake_row(luid: int, name: str, out: int, inn: int, oper: int = 1, admin: int = 1) -> SimpleNamespace:
    """表行替身 (row_views 只做属性访问; Alias 按 utf-16-le 定长字节编码)."""
    alias = name.encode("utf-16-le")
    return SimpleNamespace(
        InterfaceLuid=luid,
        Alias=alias + b"\x00" * (514 - len(alias)),
        OperStatus=oper,
        AdminStatus=admin,
        OutOctets=out,
        InOctets=inn,
    )


def ps_nic(sent: int, recv: int) -> SimpleNamespace:
    return SimpleNamespace(bytes_sent=sent, bytes_recv=recv)


def native_snap(counters: Mapping[str, tuple[int, int]], stats: Mapping[str, bool]) -> NicSnapshot:
    return NicSnapshot(
        counters={
            k: IoRow(bytes_sent=v[0], bytes_recv=v[1])
            for k, v in counters.items()
        },
        stats={
            k: StatsRow(isup=v)
            for k, v in stats.items()
        },
        luids=frozenset(),
    )


class ListHandler(logging.Handler):
    """模块 logger 直挂捕获器 (pitfalls/testing/log-capture: 不用 caplog)."""
    def __init__(self) -> None:
        super().__init__()
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


class _HandlerGuard:
    def __init__(self) -> None:
        self.handler = ListHandler()

    def __enter__(self) -> ListHandler:
        log = logging.getLogger("gtm.nic")
        self.log = log
        self.old_level = log.level
        log.addHandler(self.handler)
        log.setLevel(logging.WARNING)
        return self.handler

    def __exit__(self, *exc: object) -> None:
        self.log.removeHandler(self.handler)
        self.log.setLevel(self.old_level)


# ---- 布局守卫 ----


def test_mib_if_row2_layout_is_platform_invariant():
    # noqa 起见直接探私有结构: 布局是本模块的全部风险面, 守双平台同值
    assert ctypes.sizeof(nic._MibIfRow2) == 1352  # noqa: SLF001
    assert nic._MibIfRow2.OperStatus.offset == 1156  # noqa: SLF001
    assert nic._MibIfRow2.AdminStatus.offset == 1160  # noqa: SLF001
    assert nic._MibIfRow2.InOctets.offset == 1208  # noqa: SLF001
    assert nic._MibIfRow2.OutOctets.offset == 1280  # noqa: SLF001


# ---- 名称解码与表行视图 ----


def test_decode_alias_strips_nul_tail():
    raw = "以太网".encode("utf-16-le") + b"\x00" * (514 - len("以太网".encode("utf-16-le")))
    assert decode_alias(raw) == "以太网"


def test_decode_alias_empty():
    assert decode_alias(b"\x00" * 514) == ""


def test_row_views_isup_matches_psutil_semantics():
    # psutil net_if_stats: OperStatus == Up 且 AdminStatus == Up 才算 isup
    views, luids = row_views(
        [
            fake_row(1, "a", 10, 20, oper=1, admin=1),
            fake_row(2, "b", 11, 21, oper=1, admin=2),
            fake_row(3, "c", 12, 22, oper=2, admin=1),
        ]
    )
    assert [v.isup for v in views] == [True, False, False]
    assert luids == {1, 2, 3}


def test_row_views_maps_out_to_sent_in_to_recv():
    views, _ = row_views([fake_row(7, "eth0", out=100, inn=200)])
    assert views[0].out_octets == 100
    assert views[0].in_octets == 200


# ---- NicMapper: 名单口径映射与拓扑刷新 ----


def test_mapper_maps_universe_only_extra_table_rows_not_adopted():
    universe = {"eth0": SimpleNamespace(isup=True), "wlan": SimpleNamespace(isup=False)}
    mapper = NicMapper(lambda: universe)
    rows, luids = row_views(
        [
            fake_row(1, "eth0", 10, 20),
            fake_row(2, "wlan", 30, 40, oper=2),  # down 网卡: isup 来自表行, 名单值只供键集
            fake_row(3, "eth0-WFP Filter-0000", 999, 999),  # 过滤层行: 不在名单, 不收编
        ]
    )
    snap = mapper.read(rows, luids)
    assert set(snap.counters) == {"eth0", "wlan"}
    assert snap.counters["eth0"] == IoRow(bytes_sent=10, bytes_recv=20)
    assert snap.stats["wlan"].isup is False


def test_mapper_missing_name_self_heals_when_row_appears():
    universe = {"eth0": SimpleNamespace(isup=True), "usb0": SimpleNamespace(isup=True)}
    mapper = NicMapper(lambda: universe)
    rows_a, luids_a = row_views([fake_row(1, "eth0", 5, 6)])
    with pytest.raises(MappingError, match="usb0"):
        mapper.read(rows_a, luids_a)
    # usb0 的表行随后出现 (拓扑推进, LUID 集变化) -> 刷新名单 -> 映射成功
    rows_b, luids_b = row_views([fake_row(1, "eth0", 5, 6), fake_row(2, "usb0", 7, 8)])
    snap = mapper.read(rows_b, luids_b)
    assert snap.counters["usb0"] == IoRow(bytes_sent=7, bytes_recv=8)


def test_mapper_missing_name_after_refresh_still_raises():
    universe = {"eth0": SimpleNamespace(isup=True), "ghost": SimpleNamespace(isup=True)}
    mapper = NicMapper(lambda: universe)
    rows, luids = row_views([fake_row(1, "eth0", 5, 6)])
    with pytest.raises(MappingError, match="ghost"):
        mapper.read(rows, luids)


def test_mapper_refreshes_on_luid_set_change():
    calls: list[int] = []
    universe = {"eth0": SimpleNamespace(isup=True)}

    def provider():
        calls.append(1)
        return universe

    mapper = NicMapper(provider)
    rows1, luids1 = row_views([fake_row(1, "eth0", 0, 0)])
    mapper.read(rows1, luids1)
    first = len(calls)
    rows2, luids2 = row_views([fake_row(1, "eth0", 0, 0), fake_row(2, "usb0", 0, 0)])
    snap = mapper.read(rows2, luids2)
    assert len(calls) == first + 1  # LUID 集变化 -> 名单刷新一次
    assert set(snap.counters) == {"eth0"}  # 新行不在 psutil 名单 -> 不收编 (真实刷新会带入)


def test_mapper_duplicate_alias_for_universe_name_is_untrustworthy():
    universe = {"eth0": SimpleNamespace(isup=True)}
    mapper = NicMapper(lambda: universe)
    rows, luids = row_views([fake_row(1, "eth0", 1, 1), fake_row(2, "eth0", 2, 2)])
    with pytest.raises(MappingError, match="重复"):
        mapper.read(rows, luids)


def test_mapper_retry_after_refresh_succeeds_same_topology():
    # 首选名单含 ghost (缺表行) -> 刷新后名单缩到 eth0 -> 同一轮重试成功
    universe_versions = [
        {
            "eth0": SimpleNamespace(isup=True),
            "ghost": SimpleNamespace(isup=True)
        },
        {
            "eth0": SimpleNamespace(isup=True)
        },
    ]
    mapper = NicMapper(lambda: universe_versions.pop(0))
    rows, luids = row_views([fake_row(1, "eth0", 5, 6)])
    snap = mapper.read(rows, luids)
    assert set(snap.counters) == {"eth0"}


# ---- 启动交叉校验 ----


def test_pair_consistent_passes_within_tolerance():
    snap = native_snap({"eth0": (110, 220)}, {"eth0": True})
    assert nic._pair_consistent(snap, {"eth0": ps_nic(100, 200)}, {"eth0": SimpleNamespace(isup=True)})  # noqa: SLF001


def test_pair_consistent_key_set_mismatch():
    snap = native_snap({"eth0": (110, 220), "extra": (0, 0)}, {"eth0": True, "extra": True})
    assert not nic._pair_consistent(
        snap, {"eth0": ps_nic(100, 200)}, {"eth0": SimpleNamespace(isup=True)}
    )  # noqa: SLF001


def test_pair_consistent_isup_mismatch():
    snap = native_snap({"eth0": (110, 220)}, {"eth0": False})
    assert not nic._pair_consistent(
        snap, {"eth0": ps_nic(100, 200)}, {"eth0": SimpleNamespace(isup=True)}
    )  # noqa: SLF001


def test_pair_consistent_monotonic_violation():
    # 原生读在 psutil 之后, 计数倒退即布局/来源不可信
    snap = native_snap({"eth0": (90, 220)}, {"eth0": True})
    assert not nic._pair_consistent(
        snap, {"eth0": ps_nic(100, 200)}, {"eth0": SimpleNamespace(isup=True)}
    )  # noqa: SLF001


def test_pair_consistent_unbounded_delta():
    # 增量超过 max(16MiB, 2%): 布局错位读出天文数字的形态
    snap = native_snap({"eth0": (100 + 256 * 1024 * 1024, 200)}, {"eth0": True})
    assert not nic._pair_consistent(
        snap, {"eth0": ps_nic(100, 200)}, {"eth0": SimpleNamespace(isup=True)}
    )  # noqa: SLF001


def test_pair_consistent_stats_key_mismatch():
    snap = native_snap({"eth0": (110, 220)}, {"eth0": True})
    assert not nic._pair_consistent(snap, {"eth0": ps_nic(100, 200)}, {})  # noqa: SLF001


# ---- _native_pair: 构建/校验失败 -> None (调用方回退) ----


def test_native_pair_returns_none_when_table_read_raises(monkeypatch):
    def boom():
        raise OSError("GetIfTable2 失败")

    monkeypatch.setattr(nic, "read_table_rows", boom)  # noqa: SLF001
    assert nic._native_pair((lambda: {}, lambda: {})) is None  # noqa: SLF001


def test_native_pair_returns_none_when_validation_fails(monkeypatch):
    # 原生读 0 < psutil 读 100: 单调违背 -> 校验不过 -> 回退
    rows, luids = row_views([fake_row(1, "eth0", 0, 0)])
    monkeypatch.setattr(nic, "read_table_rows", lambda: (rows, luids))  # noqa: SLF001
    ps_pair = (lambda: {"eth0": ps_nic(100, 200)}, lambda: {"eth0": SimpleNamespace(isup=True)})
    assert nic._native_pair(ps_pair) is None  # noqa: SLF001


def test_read_table_rows_raises_on_nonzero_rc(monkeypatch):
    class FakeLib:
        def GetIfTable2(self, byref_arg):
            return 5

    monkeypatch.setattr(nic, "_iph", lambda: FakeLib())  # noqa: SLF001
    with pytest.raises(OSError, match="rc=5"):
        nic.read_table_rows()


# ---- _NativePair: 轮内单读 + 运行期回退 ----


class FlakySource:
    """按脚本弹快照/异常的整表读替身."""
    def __init__(self, script: list) -> None:
        self.script = list(script)
        self.calls = 0

    def __call__(self) -> NicSnapshot:
        self.calls += 1
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def make_pair(script: list, ps_counters=None, ps_stats=None):
    ps_counters = ps_counters or (lambda: {"eth0": ps_nic(1, 2)})
    ps_stats = ps_stats or (lambda: {"eth0": SimpleNamespace(isup=True)})
    return nic._NativePair(FlakySource(script), (ps_counters, ps_stats))  # noqa: SLF001


def snap_of(counters: Mapping[str, tuple[int, int]]) -> NicSnapshot:
    return NicSnapshot(
        counters={
            k: IoRow(bytes_sent=v[0], bytes_recv=v[1])
            for k, v in counters.items()
        },
        stats={k: StatsRow(isup=True)
               for k in counters},
        luids=frozenset(range(len(counters))),
    )


def test_pair_counters_then_stats_single_table_read():
    source_script = [snap_of({"eth0": (10, 20)})]
    pair = make_pair(source_script)
    counters = pair.counters()
    stats = pair.stats()
    assert counters["eth0"].bytes_sent == 10
    assert stats["eth0"].isup is True
    assert pair._source.calls == 1  # noqa: SLF001


def test_pair_stats_alone_reads_table():
    pair = make_pair([snap_of({"eth0": (10, 20)})])
    assert pair.stats()["eth0"].isup is True
    assert pair._source.calls == 1  # noqa: SLF001


def test_pair_two_rounds_two_reads():
    pair = make_pair([snap_of({"eth0": (1, 1)}), snap_of({"eth0": (2, 2)})])
    pair.counters()
    pair.stats()
    pair.counters()
    pair.stats()
    assert pair._source.calls == 2  # noqa: SLF001


def test_pair_falls_back_to_psutil_on_error():
    ps_counters_calls: list[int] = []
    pair = make_pair(
        [RuntimeError("表读失败"), RuntimeError("表读失败")],
        ps_counters=lambda: ps_counters_calls.append(1) or {"eth0": ps_nic(5, 6)},
    )
    assert pair.counters()["eth0"].bytes_sent == 5
    assert pair.stats()["eth0"].isup is True
    assert len(ps_counters_calls) == 1  # stats 回退走 ps_stats, 不再碰 ps_counters


def test_pair_warning_first_then_throttled_then_reset():
    with _HandlerGuard() as messages:
        pair = make_pair([RuntimeError("x")] * 3 + [snap_of({"eth0": (1, 1)})] + [RuntimeError("x")])
        pair._REPEAT_WARNING_EVERY = 2  # noqa: SLF001
        pair.counters()  # 败 1: 告警
        pair.counters()  # 败 2: 限频间隔=2 -> 告警
        pair.counters()  # 败 3: 不告警
        pair.counters()  # 成功: 清零
        pair.counters()  # 败 1: 首错再告警
    assert len(messages.messages) == 3


# ---- 平台决议与懒加载 ----


def test_resolve_non_win_returns_psutil_pair():
    ps_pair = (lambda: {}, lambda: {})
    assert nic._resolve(False, ps_pair) is ps_pair  # noqa: SLF001


def test_resolve_win_uses_native_when_available(monkeypatch):
    native_pair = (lambda: {}, lambda: {})
    monkeypatch.setattr(nic, "_native_pair", lambda p: native_pair)  # noqa: SLF001
    ps_pair = (lambda: {}, lambda: {})
    assert nic._resolve(True, ps_pair) is native_pair  # noqa: SLF001


def test_resolve_win_falls_back_with_warning_when_native_unavailable(monkeypatch):
    monkeypatch.setattr(nic, "_native_pair", lambda p: None)  # noqa: SLF001
    ps_pair = (lambda: {}, lambda: {})
    with _HandlerGuard() as messages:
        assert nic._resolve(True, ps_pair) is ps_pair  # noqa: SLF001
    assert any("回退 psutil" in m for m in messages.messages)


def test_default_providers_lazy_and_resolved_once(monkeypatch):
    c_mark, s_mark = object(), object()
    resolve_calls: list[bool] = []

    def fake_resolve(win32: bool, pair: tuple):
        resolve_calls.append(win32)
        return (lambda: c_mark, lambda: s_mark)

    monkeypatch.setattr(nic, "_resolve", fake_resolve)  # noqa: SLF001
    monkeypatch.setattr(nic, "_RESOLVED", None)  # noqa: SLF001
    ps_pair = (lambda: {}, lambda: {})

    counters, stats = nic.default_providers(ps_pair)
    assert resolve_calls == []  # 构造/取包装不决议

    assert counters() is c_mark  # 首次调用才决议
    assert stats() is s_mark
    assert resolve_calls == [sys.platform.startswith("win")]

    counters2, stats2 = nic.default_providers(ps_pair)
    assert counters2() is c_mark  # 进程内缓存: 不再决议
    assert stats2() is s_mark
    assert len(resolve_calls) == 1


# ---- 真机全链 (只读) ----


@pytest.mark.skipif(not sys.platform.startswith("win"), reason="win32 原生路径")
def test_live_default_pair_sampling():
    """真机默认对决议 + 采样走通; 校验不过会自动回退, 故不断言走哪条路径."""
    sampler = Sampler()
    result = sampler.sample_once()
    assert isinstance(result, SampleResult)
    assert result.day_total_bytes >= 0
    # 第二个 Sampler 复用进程内决议结果 (缓存不重建)
    result2 = Sampler().sample_once()
    assert isinstance(result2, SampleResult)
