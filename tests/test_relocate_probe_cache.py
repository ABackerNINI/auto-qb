"""test_relocate_probe_cache 测试计划: 同机强探测缓存(E1)的 state 读写单点
(计划 26-11-04-0055 §04 P1 —— relocate_mod 的 _state_probes/probe_get/probe_put/probe_drop)

数据形状: state.data["relocate"]["probes"][指纹哈希] = {"status": "passed"|"failed",
"evidence": {...}, "at": <epoch秒>}。新增顶层键, 不做 state 版本 bump(无迁移)。
模块只提供读写单点: 未命中/坏条目一律按未命中返回 None 不抛异常(缓存的失败要能被
覆盖写修复), 落盘节奏交给 state 服务的周期落盘(与 relocate.jobs 同口径)。

## 测试计划(每个测试函数一条)
- test_probe_put_get_roundtrip: put -> get 往返相等(at 为 epoch 秒), 且真身落 state.data
- test_probe_put_overwrites: 同指纹二次 put 覆盖写(status/evidence/at 全换新)
- test_probe_drop_removes_single_fingerprint: drop 只删目标指纹(别的保留); 重复 drop 幂等返回 False
- test_probe_get_miss_returns_none: 未命中指纹 / state 缺失 / 上下文缺失 都返回 None 不炸
- test_probe_bad_entries_treated_as_miss: 坏条目(非 dict/缺字段/status 非法/evidence 非 dict/at 非法)按未命中
- test_probe_get_returns_copy: get 返回副本, 改动不穿透缓存真身
- test_probe_write_goes_through_state_box: put/drop 直接作用于 state.data(无内存镜像旁路)
"""

import time

import types

from auto_qb.core.modules.relocate_mod import RelocateModule


def _mod(state_data=None):
    """不落盘的裸模块: ctx 用 SimpleNamespace 拼(仿 relocate_exec_support._bare_mod 的最小面)"""
    mod = RelocateModule()
    mod._ctx = types.SimpleNamespace(state=types.SimpleNamespace(data=state_data if state_data is not None else {}), )
    return mod


def test_probe_put_get_roundtrip():
    """put -> get 往返相等; at 是 epoch 秒; 真身写进 state.data["relocate"]["probes"]"""
    mod = _mod()
    entry = mod.probe_put("fp1", "passed", {"method": "e1", "sha_ok": True})
    assert entry == {"status": "passed", "evidence": {"method": "e1", "sha_ok": True}, "at": entry["at"]}
    assert 0 < entry["at"] <= int(time.time()) + 1  # epoch 秒量级, 不该是单调钟
    got = mod.probe_get("fp1")
    assert got == entry
    assert mod._ctx.state.data["relocate"]["probes"]["fp1"] == entry


def test_probe_put_overwrites():
    """同指纹二次 put 覆盖写: status/evidence/at 全部换新(缓存失效后重探的修复路径)"""
    mod = _mod()
    first = mod.probe_put("fp1", "failed", {"reason": "fs_unreachable"})
    time.sleep(0.01)  # 保证 at 有机会前进(同秒也算覆盖, 这里只验证字段换新)
    second = mod.probe_put("fp1", "passed", {"method": "e1"})
    assert mod.probe_get("fp1") == second
    assert second["status"] == "passed" and second["evidence"] == {"method": "e1"}
    assert second["at"] >= first["at"]
    assert len(mod._ctx.state.data["relocate"]["probes"]) == 1  # 不新增键


def test_probe_drop_removes_single_fingerprint():
    """drop 只删目标指纹, 其它指纹保留; 本就没有时返回 False(幂等不抛)"""
    mod = _mod()
    mod.probe_put("fp1", "passed", {})
    mod.probe_put("fp2", "failed", {})
    assert mod.probe_drop("fp1") is True
    assert mod.probe_get("fp1") is None
    assert mod.probe_get("fp2") is not None  # 邻居不受牵连
    assert mod.probe_drop("fp1") is False  # 二次 drop 幂等
    assert mod.probe_drop("nope") is False


def test_probe_get_miss_returns_none():
    """未命中返回 None: 无此指纹 / relocate 段缺失 / state 上下文整体缺失, 都不炸"""
    assert _mod().probe_get("fp1") is None  # 空 state
    assert _mod(state_data={"relocate": {}}).probe_get("fp1") is None  # probes 容器未建
    bare = RelocateModule()  # 连 ctx 都没有(P1 前的模块形态)
    assert bare.probe_get("fp1") is None
    assert bare.probe_drop("fp1") is False  # drop 在无 state 时同样静默


def test_probe_bad_entries_treated_as_miss():
    """坏条目按未命中(不抛不删): 非 dict / 缺字段 / status 非法 / evidence 非 dict / at 非法"""
    bad_entries = [
        "passed",  # 非 dict
        {
            "status": "passed",
            "evidence": {}
        },  # 缺 at
        {
            "status": "passed",
            "at": 1
        },  # 缺 evidence
        {
            "evidence": {},
            "at": 1
        },  # 缺 status
        {
            "status": "skipped",
            "evidence": {},
            "at": 1
        },  # status 非法
        {
            "status": None,
            "evidence": {},
            "at": 1
        },  # status 非法(None)
        {
            "status": "passed",
            "evidence": "ok",
            "at": 1
        },  # evidence 非 dict
        {
            "status": "passed",
            "evidence": {},
            "at": "yesterday"
        },  # at 非数值
        {
            "status": "passed",
            "evidence": {},
            "at": True
        },  # at 是 bool(数值伪装)
    ]
    for bad in bad_entries:
        mod = _mod(state_data={"relocate": {"probes": {"fp1": bad}}})
        assert mod.probe_get("fp1") is None, bad  # 按未命中, 不抛异常
        assert "fp1" in mod._ctx.state.data["relocate"]["probes"]  # 留在原地, 不顺手删


def test_probe_get_returns_copy():
    """get 返回条目副本: 调用方改 evidence 不穿透缓存真身"""
    mod = _mod()
    mod.probe_put("fp1", "passed", {"n": 1})
    got = mod.probe_get("fp1")
    got["evidence"]["n"] = 999
    got["status"] = "failed"
    assert mod.probe_get("fp1")["evidence"] == {"n": 1}
    assert mod.probe_get("fp1")["status"] == "passed"


def test_probe_write_goes_through_state_box():
    """put/drop 直接作用于 state.data(relocate.probes 单点), 无内存镜像旁路 ——
    换一个指向同一 state 的模块实例也能读到(跨轮次/重启语义由 state 周期落盘保证)"""
    shared = {}
    a, b = _mod(shared), _mod(shared)
    a.probe_put("fp1", "failed", {"reason": "fs_unreachable"})
    assert b.probe_get("fp1")["status"] == "failed"
    assert b.probe_drop("fp1") is True
    assert a.probe_get("fp1") is None
