"""test_relocate_chain_purge 测试计划: S1b 整链清理基元(D5, 计划 26-11-15-2340 §03.2/D5)

单活任务模型语义: 旧任务(superseded 历史)记录不可单独删除, 随新任务整链消亡 —— 本文件
钉扎清理基元 purge_terminal_chain 的三面: 链上溯带走 / I1 引用保护 / 保守缓行。

## 测试计划(每个测试函数一条)
- test_purge_chain_depth3_takes_whole_upstream: 链深 3(J3 <- J2 <- J1)清最下游终态 job,
  三代全带走(账 + journal + spec 三面同删, state 盒同步); 盘面先 spec 后 journal。
- test_purge_spares_upstream_referenced_by_active_job: 链上游 J1 被另一活任务 J4 的
  plan.inherited 引用时, J1 缓行不误删(J4 是活任务, I1); 无悬空引用风险的 J2/J3 照常
  带走(J3 的引用随记录一起消失, 不悬空)。
- test_purge_refuses_inflight_head: 头部在途(非终态)= 无清理入口(D5), 返回空清单,
  账与盘面零触碰。
- test_purge_keeps_non_superseded_terminal_upstream: 上游是 done/failed/cancelled 记录
  (非移交历史)不属整链消亡面, 保留(分级保留是 S3 面); 头部照常清除。
覆盖率补测(2026-11-17, 整链清理防御面; 补测轮到闸门绿):
- test_purge_chain_bad_and_self_referencing_entries: 链上溯防御面 —— 坏形条目(缺 job_id)/
  指向自身/无账条目跳过, 链照常收敛
- test_purge_blocked_propagation_spares_referenced_upstream: 引用保护不动点 —— 活任务引用的
  上游缓行, 其自身引用的上游随不动点一并缓行(悬空引用闭包), 其余照常带走
- test_purge_unlink_oserror_keeps_account_for_retry: 盘面删除失败 —— 空清单账保留待重试,
  告警落日志; 恢复后重试放行

- test_purge_spares_head_with_resume_pending: 头部带恢复确认挂账(resume_pending 非空)
  缓行(评审 major-2) —— 账/盘面零触碰; 挂账清空后同一调用放行(闭合后可清)。
"""

import os

from auto_qb.infra import relocate_journal as rj

from auto_qb.core.modules import relocate_units as ru

from relocate_exec_support import _bare_mod, _job


def _entry(jid, alias_paths=("R:/src/alias", ), dst="R:/mid", src="R:/src"):
    """plan.inherited 条目(移交条目最小形状)"""
    return {
        "job_id": jid,
        "src": src,
        "dst": dst,
        "scope": src,
        "alias_kind": "dir",
        "alias_paths": list(alias_paths),
        "link_kind": "junction",
    }


def _chain_mod(tmp_path, jobs):
    """裸模块 + state 盒 + 真实 data_dir(journal/spec 盘面断言用)"""
    data_dir = str(tmp_path / "data")
    mod = _bare_mod(data_dir=data_dir)
    for job in jobs:
        mod._jobs[job.job_id] = job
    mod._ctx.state.data = {"relocate": {"jobs": {jid: ru.job_to_dict(j) for jid, j in ((j.job_id, j) for j in jobs)}}}
    return mod, data_dir


def _seed_disk(data_dir, jid, phase):
    """盘面三件套中的两件(journal + spec)预置, 断言清理面用"""
    rj.write_journal(data_dir, jid, {"phase": phase, "ts": 123.0})
    rj.write_spec(data_dir, jid, {"job_id": jid, "src": "R:/src", "dst": "R:/mid", "host": "h", "port": 1})


def test_purge_chain_depth3_takes_whole_upstream(tmp_path):
    """链深 3 清最下游: 三代全带走(账 + journal + spec + state 盒)"""
    j1 = _job("jr-1", phase=ru.PHASE_SUPERSEDED, src="R:/src", dst="R:/mid")
    j2 = _job("jr-2", phase=ru.PHASE_SUPERSEDED, src="R:/mid", dst="R:/mid2", plan={"inherited": [_entry("jr-1")]})
    j3 = _job(
        "jr-3", phase=ru.PHASE_DONE, src="R:/mid2", dst="R:/end", plan={"inherited": [_entry("jr-2", dst="R:/mid2")]}
    )
    mod, data_dir = _chain_mod(tmp_path, [j1, j2, j3])
    for jid, phase in (("jr-1", "superseded"), ("jr-2", "superseded"), ("jr-3", "done")):
        _seed_disk(data_dir, jid, phase)

    purged = mod.purge_terminal_chain("jr-3")

    assert sorted(purged) == ["jr-1", "jr-2", "jr-3"], purged
    for jid in ("jr-1", "jr-2", "jr-3"):
        assert mod.get_job(jid) is None, jid
        assert jid not in mod._ctx.state.data["relocate"]["jobs"], jid
        assert not rj.journal_path(data_dir, jid) or not os.path.exists(rj.journal_path(data_dir, jid)), jid
        assert not os.path.exists(rj.spec_path(data_dir, jid)), jid


def test_purge_spares_upstream_referenced_by_active_job(tmp_path):
    """I1 引用保护: 上游 J1 被活任务 J4 引用 -> J1 缓行; J2/J3 无悬空风险照常带走"""
    j1 = _job("jr-1", phase=ru.PHASE_SUPERSEDED, src="R:/src", dst="R:/mid")
    j2 = _job("jr-2", phase=ru.PHASE_SUPERSEDED, src="R:/mid", dst="R:/mid2", plan={"inherited": [_entry("jr-1")]})
    j3 = _job(
        "jr-3", phase=ru.PHASE_DONE, src="R:/mid2", dst="R:/end", plan={"inherited": [_entry("jr-2", dst="R:/mid2")]}
    )
    # 活任务 J4: 自己接管了 J1(另一条链共享同一前任)
    j4 = _job("jr-4", phase=ru.PHASE_ARMED, src="R:/src", dst="R:/other", plan={"inherited": [_entry("jr-1")]})
    mod, data_dir = _chain_mod(tmp_path, [j1, j2, j3, j4])
    for jid, phase in (("jr-1", "superseded"), ("jr-2", "superseded"), ("jr-3", "done"), ("jr-4", "armed")):
        _seed_disk(data_dir, jid, phase)

    purged = mod.purge_terminal_chain("jr-3")

    assert sorted(purged) == ["jr-2", "jr-3"], purged
    kept = mod.get_job("jr-1")
    assert kept is not None and kept.phase == ru.PHASE_SUPERSEDED, "被活任务引用的上游不误删(I1)"
    assert mod.get_job("jr-4").phase == ru.PHASE_ARMED, "活任务零触碰"
    assert os.path.exists(rj.journal_path(data_dir, "jr-1")), "缓行账的盘面原样"
    assert os.path.exists(rj.spec_path(data_dir, "jr-1")), "缓行账的盘面原样"


def test_purge_refuses_inflight_head(tmp_path):
    """头部在途 = 无清理入口(D5): 空清单, 账与盘面零触碰"""
    j1 = _job("jr-1", phase=ru.PHASE_SUPERSEDED, src="R:/src", dst="R:/mid")
    j2 = _job("jr-2", phase=ru.PHASE_ARMED, src="R:/mid", dst="R:/end", plan={"inherited": [_entry("jr-1")]})
    mod, data_dir = _chain_mod(tmp_path, [j1, j2])
    _seed_disk(data_dir, "jr-1", "superseded")

    assert mod.purge_terminal_chain("jr-2") == []
    assert mod.get_job("jr-1").phase == ru.PHASE_SUPERSEDED
    assert mod.get_job("jr-2").phase == ru.PHASE_ARMED
    assert os.path.exists(rj.journal_path(data_dir, "jr-1"))


def test_purge_keeps_non_superseded_terminal_upstream(tmp_path):
    """上游是 done(非移交历史)记录: 保留(分级保留是 S3 面), 头部照常清除"""
    j1 = _job("jr-1", phase=ru.PHASE_DONE, src="R:/src", dst="R:/mid")
    j2 = _job("jr-2", phase=ru.PHASE_DONE, src="R:/mid", dst="R:/end", plan={"inherited": [_entry("jr-1")]})
    mod, data_dir = _chain_mod(tmp_path, [j1, j2])
    _seed_disk(data_dir, "jr-1", "done")

    assert mod.purge_terminal_chain("jr-2") == ["jr-2"]
    assert mod.get_job("jr-1") is not None, "done 记录不随链带走"
    assert os.path.exists(rj.journal_path(data_dir, "jr-1"))


def test_purge_spares_head_with_resume_pending(tmp_path):
    """挂账缓行(评审 major-2): 头部 resume_pending 非空 = 「需手动恢复」常驻提示态,
    整链删除会把挂账/resuming 登记/前端余量行一起静默带走 —— 账/盘面零触碰; 挂账
    清空(闭合)后同一基元放行(「闭合后可清」面)。"""
    j1 = _job("jr-1", phase=ru.PHASE_SUPERSEDED, src="R:/src", dst="R:/mid")
    j2 = _job(
        "jr-2",
        phase=ru.PHASE_DONE,
        src="R:/mid",
        dst="R:/end",
        resume_hashes=("HZ", ),
        resume_pending=("HZ", ),
        plan={"inherited": [_entry("jr-1")]},
    )
    mod, data_dir = _chain_mod(tmp_path, [j1, j2])
    for jid, phase in (("jr-1", "superseded"), ("jr-2", "done")):
        _seed_disk(data_dir, jid, phase)

    assert mod.purge_terminal_chain("jr-2") == []
    assert mod.get_job("jr-2") is not None and mod.get_job("jr-2").resume_pending == ("HZ", )
    assert os.path.exists(rj.journal_path(data_dir, "jr-2")), "挂账账盘面原样"
    assert os.path.exists(rj.spec_path(data_dir, "jr-2"))
    assert mod.get_job("jr-1") is not None, "挂账缓行连带前任保留(整链一个清理单元)"

    # 挂账闭合(确认/闭账后 resume_pending 清空): 同一基元放行, 整链照常带走
    from dataclasses import replace

    mod._jobs["jr-2"] = replace(mod._jobs["jr-2"], resume_pending=())
    assert mod.purge_terminal_chain("jr-2") == ["jr-2", "jr-1"]
    assert mod.get_job("jr-2") is None and mod.get_job("jr-1") is None


# ---------- 覆盖率补测(2026-11-17, 整链清理防御面): 行为有意义面 ----------


def test_purge_chain_bad_and_self_referencing_entries(tmp_path):
    """链上溯防御面: 坏形移交条目(缺 job_id)与指向自身的条目跳过(不自吞), 链照常收敛;
    不存在的上游账(条目 job_id 无账)同样跳过"""
    j3 = _job(
        "jr-3",
        phase=ru.PHASE_DONE,
        src="R:/mid2",
        dst="R:/end",
        plan={
            "inherited":
                [
                    {
                        "src": "R:/no-id",
                        "scope": "R:/no-id",
                        "alias_kind": "dir",
                        "alias_paths": []
                    },  # 缺 id
                    _entry("jr-3"),  # 指向自身: 跳过(不自吞)
                    _entry("jr-2", dst="R:/mid2"),
                    _entry("jr-ghost", dst="R:/ghost"),  # 无账条目: 跳过
                ]
        },
    )
    j2 = _job("jr-2", phase=ru.PHASE_SUPERSEDED, src="R:/mid", dst="R:/mid2", plan={"inherited": [_entry("jr-1")]})
    j1 = _job("jr-1", phase=ru.PHASE_SUPERSEDED, src="R:/src", dst="R:/mid")
    mod, data_dir = _chain_mod(tmp_path, [j1, j2, j3])
    for jid, phase in (("jr-1", "superseded"), ("jr-2", "superseded"), ("jr-3", "done")):
        _seed_disk(data_dir, jid, phase)

    purged = mod.purge_terminal_chain("jr-3")

    assert sorted(purged) == ["jr-1", "jr-2", "jr-3"], "坏形/自指/无账条目不挡正常上溯"
    for jid in ("jr-1", "jr-2", "jr-3"):
        assert mod.get_job(jid) is None, jid


def test_purge_blocked_propagation_spares_referenced_upstream(tmp_path):
    """引用保护不动点: 活任务引用 J1 -> J1 缓行; J1 自身引用的 J0 随不动点一并缓行
    (悬空引用闭包), J2/J3 照常带走"""
    j0 = _job("jr-0", phase=ru.PHASE_SUPERSEDED, src="R:/root", dst="R:/src")
    j1 = _job("jr-1", phase=ru.PHASE_SUPERSEDED, src="R:/src", dst="R:/mid", plan={"inherited": [_entry("jr-0")]})
    j2 = _job("jr-2", phase=ru.PHASE_SUPERSEDED, src="R:/mid", dst="R:/mid2", plan={"inherited": [_entry("jr-1")]})
    j3 = _job(
        "jr-3", phase=ru.PHASE_DONE, src="R:/mid2", dst="R:/end", plan={"inherited": [_entry("jr-2", dst="R:/mid2")]}
    )
    j4 = _job("jr-4", phase=ru.PHASE_ARMED, src="R:/src", dst="R:/live", plan={"inherited": [_entry("jr-1")]})
    mod, data_dir = _chain_mod(tmp_path, [j0, j1, j2, j3, j4])
    for jid, phase in (("jr-0", "superseded"), ("jr-1", "superseded"), ("jr-2", "superseded"), ("jr-3", "done")):
        _seed_disk(data_dir, jid, phase)

    purged = mod.purge_terminal_chain("jr-3")

    assert sorted(purged) == ["jr-2", "jr-3"], purged
    for jid in ("jr-0", "jr-1", "jr-4"):
        assert mod.get_job(jid) is not None, f"{jid} 缓行(被引用闭包)"


def test_purge_unlink_oserror_keeps_account_for_retry(tmp_path, monkeypatch):
    """盘面删除失败(权限/占用): 账保留待重试, 清单为空, 告警落日志(不炸不带损)"""
    j1 = _job("jr-1", phase=ru.PHASE_SUPERSEDED, src="R:/src", dst="R:/mid")
    j2 = _job("jr-2", phase=ru.PHASE_DONE, src="R:/mid", dst="R:/end", plan={"inherited": [_entry("jr-1")]})
    mod, data_dir = _chain_mod(tmp_path, [j1, j2])
    for jid, phase in (("jr-1", "superseded"), ("jr-2", "done")):
        _seed_disk(data_dir, jid, phase)

    real_remove = os.remove

    def _denied(path, *a, **k):
        raise PermissionError(13, "拒绝访问", str(path))

    monkeypatch.setattr(os, "remove", _denied)
    from helpers import capture_logs

    with capture_logs() as cap:
        purged = mod.purge_terminal_chain("jr-2")
    monkeypatch.setattr(os, "remove", real_remove)
    assert purged == [], "盘面删不成: 空清单"
    for jid in ("jr-1", "jr-2"):
        assert mod.get_job(jid) is not None, f"{jid} 账保留待重试"
        assert os.path.exists(rj.journal_path(data_dir, jid)), f"{jid} journal 原样"
    assert any("盘面删除失败" in x.getMessage() for x in cap.records), "清理失败告警"
    # unlink 层 OSError 告警(路径级「删除失败(<errno>)」行, 与上面「盘面删除失败」汇总行区分)
    assert any("删除失败(" in x.getMessage() and "盘面删除失败" not in x.getMessage() for x in cap.records), "unlink OSError 告警"
    # 恢复后重试放行(闭包: 同一调用再清)
    assert sorted(mod.purge_terminal_chain("jr-2")) == ["jr-1", "jr-2"], "重试放行"
