"""WebUI 迁移可见性 P0(plan 26-11-04-1042): 快照/标注/组级聚合/指纹/零触盘

## 测试计划
- test_state_of_phase_merges: 相位归并到 moving / pending_finalize / done / failed / cancelled(未知按 moving)
- test_member_relocate_origin_mover_and_contract: 成员标注字段、mover 精确归属、origin 来自 job、save_path 不变
- test_origin_roundtrip_and_legacy_unknown: web/rule/cli origin 落账回读; 旧 state 条目缺 origin 回落 unknown
- test_snapshot_prefers_active_job_over_old_terminal: 同 hash 活跃新 job 取代终态旧 job, 快照换代并置 full 脏
- test_group_relocate_priority_mixed_and_order_independent: 组级 failed>moving>pending_finalize>done、同优先级多 job 记 mixed、pending/total/job_ids/dst、成员顺序无关、全 cancelled 为 None
- test_relocate_null_when_disabled_or_no_jobs: relocate 关 / 无 job(含旧 state 无 relocate 段) => relocate 字段 null
- test_view_build_does_not_probe_filesystem_or_iterate_jobs: 列表构建期不 lstat/stat/readlink/islink, 不遍历 _jobs
- test_decorate_fingerprint_includes_relocate: decorate.js 成员/组 relocate 签名进指纹且槽位长度同步
"""
from __future__ import annotations

import os

import pytest

from auto_qb.core.modules import relocate_units as ru
from auto_qb.core.modules.relocate_units import RelocateJob
from helpers import relocate_env


def _job(
    job_id: str,
    hashes=("HA", "HB"),
    *,
    mover: str = "HA",
    phase: str = ru.PHASE_MOVING,
    origin: str = "web",
    updated_at: float = 1.0,
    alias_paths=(),
) -> RelocateJob:
    return RelocateJob(
        job_id=job_id,
        hashes=tuple(hashes),
        mover=mover,
        src=r"R:\src",
        dst=r"R:\dst",
        scope=r"R:\src",
        alias_kind="file" if alias_paths else "",
        alias_paths=tuple(alias_paths),
        phase=phase,
        origin=origin,
        updated_at=updated_at,
    )


def _row(env, recs=None):
    key = next(iter(env.mgr.store.groups))
    if recs is None:
        recs = [env.mgr.store.by_hash[h] for h in env.mgr.store.groups[key]]
    return env.mgr._build_group_row(key, recs, set())


@pytest.mark.parametrize(
    "phase,state",
    [
        (ru.PHASE_MOVING, "moving"),
        (ru.PHASE_WATCHING, "moving"),
        (ru.PHASE_MOVED, "pending_finalize"),
        (ru.PHASE_ARMED, "pending_finalize"),
        (ru.PHASE_REMOVING, "pending_finalize"),
        (ru.PHASE_REMOVED, "pending_finalize"),
        (ru.PHASE_FINALIZING, "pending_finalize"),
        (ru.PHASE_DONE, "done"),
        (ru.PHASE_FAILED, "failed"),
        (ru.PHASE_CANCELLED, "cancelled"),
        ("", "moving"),
        ("legacy_unknown", "moving"),
    ],
)
def test_state_of_phase_merges(phase, state):
    from auto_qb.webui.views_relocate import state_of_phase

    assert state_of_phase(phase) == state


def test_member_relocate_origin_mover_and_contract(tmp_path):
    env = relocate_env(tmp_path)
    env.mgr.ctx.relocate.register_job(
        _job("j1", phase=ru.PHASE_MOVING, origin="rule", alias_paths=["a", "b"], updated_at=5.0)
    )
    ha = env.mgr._member_view(env.mgr.store.by_hash["HA"])["relocate"]
    hb = env.mgr._member_view(env.mgr.store.by_hash["HB"])["relocate"]
    assert ha and hb
    assert ha["state"] == "moving" and ha["phase"] == ru.PHASE_MOVING
    assert ha["mover"] is True, "mover 必须按 job.mover 精确匹配"
    assert hb["mover"] is False
    assert ha["origin"] == "rule", "origin 必须来自 job, 不得按调用路径猜"
    assert ha["alias_kind"] == "file" and ha["alias_count"] == 2
    assert ha["job_id"] == "j1" and ha["updated_at"] == 5.0
    # 不改 save_path: 迁移可见性只加标注, 路径筛选仍按 qB save_path 语义
    assert env.mgr._member_view(env.mgr.store.by_hash["HA"])["save_path"] == env.src


def test_origin_roundtrip_and_legacy_unknown():
    for origin in ("web", "rule", "cli"):
        d = ru.job_to_dict(_job("j", origin=origin))
        assert d["origin"] == origin
        assert ru.job_from_dict(d).origin == origin
    legacy = ru.job_to_dict(_job("j", origin="web"))
    legacy.pop("origin")
    assert ru.job_from_dict(legacy).origin == "unknown", "旧 state 条目缺 origin 必须回落 unknown"


def test_snapshot_prefers_active_job_over_old_terminal(tmp_path):
    env = relocate_env(tmp_path)
    mod = env.mgr.ctx.relocate
    mod.register_job(_job("j_old", phase=ru.PHASE_DONE, updated_at=100.0))
    assert mod.jobs_snapshot().job_for("HA")["job_id"] == "j_old"
    mod.register_job(_job("j_new", phase=ru.PHASE_MOVING, updated_at=1.0))
    snap = mod.jobs_snapshot()
    assert snap.job_for("HA")["job_id"] == "j_new", "同一 hash 必须取活跃 job, 即使终态 job 更新更晚"
    assert env.mgr._member_view(env.mgr.store.by_hash["HA"])["relocate"]["state"] == "moving"
    assert snap.generation >= 2
    assert env.mgr.web.group_view_dirty is True
    assert "relocate_jobs" in env.mgr.web._pending_full_reasons


def test_group_relocate_priority_mixed_and_order_independent(tmp_path):
    env = relocate_env(tmp_path)
    mod = env.mgr.ctx.relocate
    key = next(iter(env.mgr.store.groups))
    members = [env.mgr.store.by_hash[h] for h in env.mgr.store.groups[key]]

    mod.register_job(_job("j_fail", hashes=("HA", ), phase=ru.PHASE_FAILED, updated_at=2.0))
    mod.register_job(_job("j_move", hashes=("HB", ), phase=ru.PHASE_MOVING, updated_at=3.0))
    row = env.mgr._build_group_row(key, members, set())
    assert row["relocate"]["state"] == "failed", "failed 优先于 moving"
    assert row["relocate"]["pending"] == 1 and row["relocate"]["total"] == 2
    assert row["relocate"]["job_ids"] == ["j_fail", "j_move"]

    # 同一 hash 的活跃新 job 取代终态 failed: 组成员标注取活跃者, failed 不再挂出
    mod.register_job(_job("j_armed_a", hashes=("HA", ), phase=ru.PHASE_ARMED, updated_at=4.0))
    row = env.mgr._build_group_row(key, members, set())
    assert row["relocate"]["state"] == "moving", "moving(HB) 优先于 pending_finalize(HA)"
    assert "j_fail" not in row["relocate"]["job_ids"], "被活跃 job 取代的终态 job 不进组级标注"

    # 同优先级两个不同 job => mixed
    mod.register_job(_job("j_move_a2", hashes=("HA", ), phase=ru.PHASE_MOVING, updated_at=5.0))
    row = env.mgr._build_group_row(key, members, set())
    assert row["relocate"]["state"] == "mixed", "同优先级两个 job 必须 mixed"
    assert row["relocate"]["pending"] == 2

    # 顺序无关
    assert env.mgr._build_group_row(key, list(reversed(members)), set())["relocate"] == row["relocate"]

    # dst 去重排序
    assert row["relocate"]["dst"] == [r"R:\dst"]

    # 先撤销在途 job, 再登记单个全组 done => done(非 mixed)
    for jid, hashes in (("j_move_a2", ("HA", )), ("j_armed_a", ("HA", )), ("j_move", ("HB", ))):
        mod.register_job(_job(jid, hashes=hashes, phase=ru.PHASE_CANCELLED, updated_at=7.0))
    mod.register_job(_job("j_done", phase=ru.PHASE_DONE, updated_at=8.0))
    row2 = env.mgr._build_group_row(key, members, set())
    assert row2["relocate"]["state"] == "done" and row2["relocate"]["pending"] == 0

    # 全 cancelled => 无组级标注
    mod.register_job(_job("j_done", phase=ru.PHASE_CANCELLED, updated_at=9.0))
    assert env.mgr._build_group_row(key, members, set())["relocate"] is None


def test_relocate_null_when_disabled_or_no_jobs(tmp_path):
    env = relocate_env(tmp_path)
    # 无 job(等价旧 state.json 没有 relocate 段) => null
    assert env.mgr._member_view(env.mgr.store.by_hash["HA"])["relocate"] is None
    assert _row(env)["relocate"] is None

    env.mgr.ctx.relocate.register_job(_job("j1", phase=ru.PHASE_MOVING))
    assert env.mgr._member_view(env.mgr.store.by_hash["HA"])["relocate"] is not None

    # relocate 关: 即使内存仍有 job 也必须 null
    env.mgr.config.relocate.enabled = False
    assert env.mgr._member_view(env.mgr.store.by_hash["HA"])["relocate"] is None
    assert _row(env)["relocate"] is None


def test_view_build_does_not_probe_filesystem_or_iterate_jobs(tmp_path, monkeypatch):
    env = relocate_env(tmp_path)
    mod = env.mgr.ctx.relocate
    mod.register_job(_job("j1", phase=ru.PHASE_MOVING, alias_paths=["a"]))
    members = env.mgr.store.by_hash["HA"]

    calls = []

    def _boom(*a, **k):
        calls.append((a, k))
        raise AssertionError("列表构建期禁止文件系统探测")

    for name in ("lstat", "stat", "readlink"):
        monkeypatch.setattr(os, name, _boom)
    monkeypatch.setattr(os.path, "islink", _boom)

    class _NoIterJobs(dict):
        def __iter__(self):
            raise AssertionError("Web 构建期禁止遍历 _jobs")

        def values(self):
            raise AssertionError("Web 构建期禁止遍历 _jobs")

        def items(self):
            raise AssertionError("Web 构建期禁止遍历 _jobs")

    monkeypatch.setattr(mod, "_jobs", _NoIterJobs(mod._jobs))
    env.mgr._member_view(members)
    row = _row(env)
    assert row["members"][0]["relocate"]["state"] == "moving"
    assert not calls


def test_decorate_fingerprint_includes_relocate():
    from pathlib import Path

    js = (Path(__file__).resolve().parents[1] /
          "src/auto_qb/webui/static/shared/decorate.js").read_text(encoding="utf-8")
    assert "function _relocateSig(" in js and "function _groupRelocateSig(" in js
    assert "_relocateSig(m.relocate)" in js
    assert "fp.length !== ms.length * 8 + 3" in js, "成员 relocate 槽 + 组 relocate 槽必须同步长度"
    assert "_groupRelocateSig(g.relocate)" in js
