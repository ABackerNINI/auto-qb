"""S3 终态分级保留(D3 + Q11, 计划 26-11-15-2340 §03.4; 关联 issue 26-11-10-0326)

分级规则: 成功(done)自动滚动保留最近 DONE_HISTORY_KEEP=20 条, 更老经整链清理基元
purge_terminal_chain 消亡(整链消亡: superseded 前任连带, 不受计数影响); failed/cancelled
永不自动清(Q11: 批量搬迁不得冲掉失败账), 只能手动清空(relocate_clear_history, I1 缓行
的账保留并在回执说明剩余)。

## 测试计划(每个测试函数一条)
- test_prune_keeps_recent_done_rolls_out_older: 25 条 done(旧->新)滚出最老 5 条, 账/journal/
  spec 三面同删; 最新 20 条保留
- test_prune_batch_migration_spares_failures_and_cancels: 批量搬迁 25 组 done + 5 failed +
  2 cancelled -> done 滚到 20, 失败与取消全部保留(Q11 修正面)
- test_prune_spares_held_done_rolls_after_closure: 带恢复确认挂账(resume_pending 非空)的
  done 即使最老也不被滚出(评审 major-2: 静默删账会带走挂账/resuming 登记/前端余量行);
  挂账闭合(账面清空)后下一拍自然补滚
- test_clear_history_spares_jobs_with_resume_pending: 清空历史对挂账账缓行且回执 note
  点名「恢复确认挂账」(与 I1 缓行分开说明)
- test_prune_superseded_not_counted_dies_with_chain: superseded 不进 20 条计数; 被滚出的
  done 链头引用的前任随整链消亡(被接管旧任务记录的消亡面)
- test_prune_dry_run_noop: dry-run 不动手(清理是真写盘)
- test_set_job_done_triggers_prune: _set_job 落 done 即滚出超限旧账(触发面接线钉扎)
- test_clear_history_clears_all_terminal_and_reports_deferred: 清空历史遍历终态账全清;
  被活任务引用的账 I1 缓行保留, 回执 note 说明剩余
- test_clear_history_spares_inflight: 在途账(armed)无清空面, 撤销走 relocate_cancel 不在本入口
- test_clear_history_done_chain_and_failed_share_upstream_i1_deferred: 分级保留组合面 ——
  done 链头(带 superseded 上游)与挂账 failed 账引用同一上游共存时清空: done 链头照清
  (引用随记录消亡), 上游被挂账 failed(缓行账)引用 = I1 缓行不删; 回执 note 双归因
  (挂账缓行 + I1 兜底)与 remaining 逐条点名; 挂账闭合前重复清空幂等零动作
- test_clear_history_dry_run_blocked: dry-run 回 blocked 不执行
- test_web_relocate_history_clear_route: 路由级 403(关)/ 两步确认(confirm 缺省零动作回
  现场说明, confirm=true 入队 relocate_clear_history)/ 命令登记(deferred 回执族 + handler 表)
"""
import os

from auto_qb.infra import relocate_journal as rj

from auto_qb.core.modules import relocate_units as ru

from helpers import capture_logs

from relocate_exec_support import _bare_mod, _job


def _entry(jid, alias_paths=("R:/src/alias", ), dst="R:/mid", src="R:/src"):
    """plan.inherited 条目(移交条目最小形状, 与 test_relocate_chain_purge 同款)"""
    return {
        "job_id": jid,
        "src": src,
        "dst": dst,
        "scope": src,
        "alias_kind": "dir",
        "alias_paths": list(alias_paths),
        "link_kind": "junction",
    }


def _mod(tmp_path, jobs):
    """裸模块 + state 盒 + 真实 data_dir(盘面断言用; 与 test_relocate_chain_purge 同款)"""
    data_dir = str(tmp_path / "data")
    mod = _bare_mod(data_dir=data_dir)
    for job in jobs:
        mod._jobs[job.job_id] = job
    mod._ctx.state.data = {"relocate": {"jobs": {jid: ru.job_to_dict(j) for jid, j in ((j.job_id, j) for j in jobs)}}}
    return mod, data_dir


def _seed_disk(data_dir, jid, phase):
    rj.write_journal(data_dir, jid, {"phase": phase, "ts": 123.0})
    rj.write_spec(data_dir, jid, {"job_id": jid, "src": "R:/src", "dst": "R:/mid", "host": "h", "port": 1})


def _done_batch(n, *, t0=100.0):
    """n 条 done 账, updated_at 递增(旧->新); 盘面由用例按需预置"""
    return [
        _job(f"jr-done-{i:02d}", phase=ru.PHASE_DONE, updated_at=t0 + i, src=f"R:/s{i}", dst=f"R:/d{i}")
        for i in range(n)
    ]


def _disk_gone(data_dir, jid):
    return (not os.path.exists(rj.journal_path(data_dir, jid)) and not os.path.exists(rj.spec_path(data_dir, jid)))


def test_prune_keeps_recent_done_rolls_out_older(tmp_path):
    """25 条 done 滚出最老 5 条(账+盘面三面同删), 最新 20 条保留"""
    jobs = _done_batch(25)
    mod, data_dir = _mod(tmp_path, jobs)
    for j in jobs:
        _seed_disk(data_dir, j.job_id, "done")

    purged = mod.prune_success_history()

    assert purged == [f"jr-done-{i:02d}" for i in range(5)], "滚出的恰是最老 5 条"
    for i in range(5):
        jid = f"jr-done-{i:02d}"
        assert mod.get_job(jid) is None and _disk_gone(data_dir, jid)
    for i in range(5, 25):
        jid = f"jr-done-{i:02d}"
        assert mod.get_job(jid) is not None, jid
        assert os.path.exists(rj.journal_path(data_dir, jid)), jid
    assert sum(1 for j in mod._jobs.values() if j.phase == ru.PHASE_DONE) == ru.DONE_HISTORY_KEEP
    # 幂等: 再滚一次零动作(黄金法则 1)
    assert mod.prune_success_history() == []


def test_prune_batch_migration_spares_failures_and_cancels(tmp_path):
    """批量搬迁 >20 组(Q11 修正面): done 滚到 20, failed/cancelled 一条不冲"""
    jobs = _done_batch(25) + [
        _job(f"jr-fail-{i}", phase=ru.PHASE_FAILED, updated_at=50.0 + i, src=f"R:/f{i}", dst=f"R:/df{i}")
        for i in range(5)
    ] + [
        _job("jr-cancel-a", phase=ru.PHASE_CANCELLED, updated_at=40.0),
        _job("jr-cancel-b", phase=ru.PHASE_CANCELLED, updated_at=41.0),
    ]
    mod, data_dir = _mod(tmp_path, jobs)
    for j in jobs:
        _seed_disk(data_dir, j.job_id, j.phase)

    mod.prune_success_history()

    assert sum(1 for j in mod._jobs.values() if j.phase == ru.PHASE_DONE) == ru.DONE_HISTORY_KEEP
    for i in range(5):
        assert mod.get_job(f"jr-fail-{i}") is not None, "失败账永不自动清(Q11)"
        assert os.path.exists(rj.journal_path(data_dir, f"jr-fail-{i}"))
    assert mod.get_job("jr-cancel-a") is not None and mod.get_job("jr-cancel-b") is not None
    assert all(mod.get_job(f"jr-done-{i:02d}") is None for i in range(5)), "滚出的仍是最老 done"


def test_prune_spares_held_done_rolls_after_closure(tmp_path):
    """带恢复确认挂账的 done 不被滚出(即使最老); 挂账闭合后可滚(评审 major-2 双向面)"""
    held = _job("jr-held-done", phase=ru.PHASE_DONE, updated_at=50.0, resume_hashes=("HZ", ), resume_pending=("HZ", ))
    jobs = [held] + _done_batch(ru.DONE_HISTORY_KEEP)
    mod, data_dir = _mod(tmp_path, jobs)
    for j in jobs:
        _seed_disk(data_dir, j.job_id, "done")

    new_done = _job("jr-new", phase=ru.PHASE_DONE, updated_at=999.0)
    mod._set_job(new_done)

    assert mod.get_job("jr-held-done") is not None, "挂账 done 不被滚出(候选过滤 + 基元守卫双落)"
    assert mod.get_job("jr-held-done").resume_pending == ("HZ", ), "挂账账面零触碰"
    assert os.path.exists(rj.journal_path(data_dir, "jr-held-done"))
    assert mod.get_job("jr-done-00") is None, "滚出的仍是非挂账里最老的 done"
    assert sum(1 for j in mod._jobs.values() if j.phase == ru.PHASE_DONE) == ru.DONE_HISTORY_KEEP + 1

    # 挂账闭合(_reconcile_resume_pending 确认/闭账后账面清空): 下一拍 done 落账自然补滚
    from dataclasses import replace

    mod._jobs["jr-held-done"] = replace(mod._jobs["jr-held-done"], resume_pending=(), resume_hashes=())
    mod._set_job(_job("jr-newer", phase=ru.PHASE_DONE, updated_at=1000.0))
    assert mod.get_job("jr-held-done") is None, "挂账闭合后恢复可滚"


def test_clear_history_spares_jobs_with_resume_pending(tmp_path):
    """清空历史: 挂账账缓行且回执 note 单独点名「恢复确认挂账」(与 I1 缓行分开说明)"""
    held = _job("jr-hold", phase=ru.PHASE_DONE, updated_at=1.0, resume_hashes=("HZ", ), resume_pending=("HZ", ))
    jobs = [held, _job("jr-d", phase=ru.PHASE_DONE, updated_at=2.0)]
    mod, data_dir = _mod(tmp_path, jobs)
    for j in jobs:
        _seed_disk(data_dir, j.job_id, "done")

    result = mod.relocate_clear_history()

    assert result["cls"] == "ok" and result["cleared"] == 1 and result["remaining"] == 1, result
    assert mod.get_job("jr-d") is None
    assert mod.get_job("jr-hold") is not None and mod.get_job("jr-hold").resume_pending == ("HZ", )
    assert os.path.exists(rj.journal_path(data_dir, "jr-hold"))
    assert "恢复确认挂账" in result["note"] and "1" in result["note"], result["note"]


def test_prune_superseded_not_counted_dies_with_chain(tmp_path):
    """superseded 不进 20 条计数; 被滚出 done 链头引用的前任随整链消亡(D5)"""
    j0 = _job("jr-pred", phase=ru.PHASE_SUPERSEDED, updated_at=10.0, src="R:/s0", dst="R:/mid")
    j1 = _job(
        "jr-head-00",
        phase=ru.PHASE_DONE,
        updated_at=100.0,
        src="R:/mid",
        dst="R:/d0",
        plan={"inherited": [_entry("jr-pred", dst="R:/d0")]},
    )
    jobs = [j0, j1] + _done_batch(24, t0=101.0)  # 共 25 条 done(最老的是 j1, 挂着前任)
    mod, data_dir = _mod(tmp_path, jobs)
    for j in jobs:
        _seed_disk(data_dir, j.job_id, j.phase)

    purged = mod.prune_success_history()

    assert purged[:2] == ["jr-head-00", "jr-pred"], "链头滚出时前任随整链带走"
    assert len(purged) == 6 and purged[2:] == [f"jr-done-{i:02d}" for i in range(0, 4)]
    assert mod.get_job("jr-pred") is None and _disk_gone(data_dir, "jr-pred"), "被接管旧任务随整链消亡"
    assert mod.get_job("jr-head-00") is None
    assert sum(1 for j in mod._jobs.values() if j.phase == ru.PHASE_DONE) == ru.DONE_HISTORY_KEEP


def test_prune_dry_run_noop(tmp_path):
    """dry-run 不动手: 超限账原样(清理是真写盘, 与相位机同闸)"""
    jobs = _done_batch(22)
    mod, data_dir = _mod(tmp_path, jobs)
    mod._dry = True
    for j in jobs:
        _seed_disk(data_dir, j.job_id, "done")

    assert mod.prune_success_history() == []
    assert len(mod._jobs) == 22
    assert all(os.path.exists(rj.journal_path(data_dir, j.job_id)) for j in jobs)


def test_set_job_done_triggers_prune(tmp_path):
    """触发面接线: _set_job 落 done 即滚出超限旧账(自动面挂在账变更收敛点)"""
    held = _job("jr-held-done", phase=ru.PHASE_DONE, updated_at=50.0, resume_hashes=("HZ", ), resume_pending=("HZ", ))
    jobs = [held] + _done_batch(ru.DONE_HISTORY_KEEP)
    mod, data_dir = _mod(tmp_path, jobs)
    for j in jobs:
        _seed_disk(data_dir, j.job_id, "done")

    # 落一条新的 done(updated_at 最新): 非挂账 done 共 21 条 -> 非挂账最老滚出(挂账的更老也不滚)
    new_done = _job("jr-new", phase=ru.PHASE_DONE, updated_at=999.0, src="R:/sN", dst="R:/dN")
    mod._set_job(new_done)

    assert mod.get_job("jr-new") is not None
    assert mod.get_job("jr-done-00") is None, "非挂账最老 done 随新 done 落账滚出"
    assert mod.get_job("jr-held-done") is not None, "挂账 done 即使最老也不被滚出(major-2)"
    assert sum(1 for j in mod._jobs.values() if j.phase == ru.PHASE_DONE) == ru.DONE_HISTORY_KEEP + 1
    # 非 done 落账不触发(失败账落账不清别人)
    mod._set_job(_job("jr-f", phase=ru.PHASE_FAILED, updated_at=1000.0))
    assert mod.get_job("jr-f") is not None
    assert sum(1 for j in mod._jobs.values() if j.phase == ru.PHASE_DONE) == ru.DONE_HISTORY_KEEP + 1


def test_clear_history_clears_all_terminal_and_reports_deferred(tmp_path):
    """清空历史: 终态账全清(done/failed/cancelled/superseded 各态); 被活任务引用的账
    未能清除(I1 缓行; note 兜底口径不点名单一原因, 评审 minor-R2-2), 回执 note 说明剩余
    (清空不是强删)"""
    j_active = _job(
        "jr-live", phase=ru.PHASE_ARMED, src="R:/sKeep", dst="R:/dKeep", plan={"inherited": [_entry("jr-held")]}
    )
    j_held = _job("jr-held", phase=ru.PHASE_SUPERSEDED, updated_at=10.0, src="R:/sKeep", dst="R:/mid")
    jobs = [
        j_active,
        j_held,
        _job("jr-d", phase=ru.PHASE_DONE, updated_at=100.0),
        _job("jr-f", phase=ru.PHASE_FAILED, updated_at=101.0),
        _job("jr-c", phase=ru.PHASE_CANCELLED, updated_at=102.0),
        _job("jr-sup", phase=ru.PHASE_SUPERSEDED, updated_at=103.0),  # 无活引用的前任
    ]
    mod, data_dir = _mod(tmp_path, jobs)
    for j in jobs:
        _seed_disk(data_dir, j.job_id, j.phase)

    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        result = mod.relocate_clear_history()

    assert result["cls"] == "ok"
    assert result["cleared"] == 4, result
    assert mod.get_job("jr-d") is None and mod.get_job("jr-f") is None
    assert mod.get_job("jr-c") is None and mod.get_job("jr-sup") is None
    assert _disk_gone(data_dir, "jr-f"), "失败账随清空消亡(手动面)"
    # I1: 被活任务引用的前任缓行, 回执说明剩余
    assert mod.get_job("jr-held") is not None, "被活任务引用的账缓行(I1 保护)"
    assert result["remaining"] == 1
    assert "1" in result["note"] and "未能清除" in result["note"], result["note"]
    # 活任务零触碰
    assert mod.get_job("jr-live").phase == ru.PHASE_ARMED


def test_clear_history_spares_inflight(tmp_path):
    """在途账无清空面: armed 账清空后原样(撤销语义走 relocate_cancel, D5 口径)"""
    jobs = [
        _job("jr-run", phase=ru.PHASE_MOVING, updated_at=1.0),
        _job("jr-arm", phase=ru.PHASE_ARMED, updated_at=2.0),
        _job("jr-d", phase=ru.PHASE_DONE, updated_at=3.0),
    ]
    mod, data_dir = _mod(tmp_path, jobs)
    for j in jobs:
        _seed_disk(data_dir, j.job_id, j.phase)

    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        result = mod.relocate_clear_history()

    assert result["cleared"] == 1 and result["remaining"] == 0
    assert mod.get_job("jr-run").phase == ru.PHASE_MOVING
    assert mod.get_job("jr-arm").phase == ru.PHASE_ARMED
    assert os.path.exists(rj.journal_path(data_dir, "jr-arm")), "在途账盘面零触碰"


def test_clear_history_dry_run_blocked(tmp_path):
    """dry-run 回 blocked 不执行(真写盘面同闸)"""
    mod, _data_dir = _mod(tmp_path, [_job("jr-d", phase=ru.PHASE_DONE, updated_at=1.0)])
    mod._dry = True

    result = mod.relocate_clear_history()

    assert result["cls"] == "blocked"
    assert mod.get_job("jr-d") is not None


def test_web_relocate_history_clear_route(web_env):
    """路由级: 403(关, 零入队) / 两步确认(confirm 缺省零动作回现场说明) / 入队形状与命令登记"""
    mgr, client = web_env
    auth = {"Authorization": f"Bearer {mgr.web.token}"}
    # 关(缺省 enabled=False): 403 零入队
    resp = client.post("/api/relocate/history/clear", headers=auth, json={"confirm": True})
    assert resp.status_code == 403, resp.text
    assert "relocate.enabled" in resp.json()["detail"]
    assert mgr.web.commands.empty()
    # 开: 两步确认 —— confirm 缺省零动作, 不入队, 回现场说明(连失败记录一起清/不可恢复)
    mgr.config.relocate.enabled = True
    resp = client.post("/api/relocate/history/clear", headers=auth, json={})
    assert resp.status_code == 200 and resp.json()["cls"] == "confirm", resp.text
    assert mgr.web.commands.empty()
    assert "不可恢复" in resp.json()["note"]
    # confirm=true: 入队 relocate_clear_history
    resp = client.post("/api/relocate/history/clear", headers=auth, json={"confirm": True})
    assert resp.status_code == 200 and resp.json()["queued"] is True, resp.text
    cmd, payload = mgr.web.commands.get_nowait()
    assert cmd == "relocate_clear_history", (cmd, payload)
    assert mgr.web.commands.empty()
    # 命令登记(web_env 的 host 是替身, 表面走源码级守阵): handler 映射 + 延迟回执族
    # (handler 自写 truth 回执, drain 不补写)
    import io

    from auto_qb.webui.commands_common import is_deferred_receipt

    assert is_deferred_receipt("relocate_clear_history")
    src = io.open("src/auto_qb/webui/commands.py", encoding="utf-8").read()
    assert '"relocate_clear_history": self._cmd_relocate_clear_history' in src, "命令表漏挂"


def test_clear_history_done_chain_and_failed_share_upstream_i1_deferred(tmp_path):
    """清空历史 x 分级保留组合面: done 链头(带 superseded 上游)与挂账 failed 账引用
    同一上游共存 —— done 链头照清(其移交引用随记录消亡, 不悬空); 上游被挂账 failed
    引用 = I1 缓行不删(强删会让挂账账的移交条目悬空失主); 回执 note 双归因
    (挂账缓行 + I1 兜底), remaining 逐条点名; 挂账闭合前重复清空幂等零动作"""
    jobs = [
        _job("jr-sup", phase=ru.PHASE_SUPERSEDED, updated_at=10.0, src="R:/sUp", dst="R:/dUp"),
        _job(
            "jr-done",
            phase=ru.PHASE_DONE,
            updated_at=100.0,
            src="R:/sUp",
            dst="R:/dDone",
            plan={"inherited": [_entry("jr-sup")]},
        ),
        _job(
            "jr-fail",
            phase=ru.PHASE_FAILED,
            updated_at=101.0,
            src="R:/sUp",
            dst="R:/dFail",
            plan={"inherited": [_entry("jr-sup")]},
            resume_hashes=("HZ", ),
            resume_pending=("HZ", ),
        ),
    ]
    mod, data_dir = _mod(tmp_path, jobs)
    for j in jobs:
        _seed_disk(data_dir, j.job_id, j.phase)

    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        result = mod.relocate_clear_history()

    assert result["cls"] == "ok" and result["cleared"] == 1, result
    assert mod.get_job("jr-done") is None and _disk_gone(data_dir, "jr-done"), "done 链头照清(手动面)"
    # I1: 上游被挂账 failed(缓行账)引用 -> 不删, 引用不悬空
    assert mod.get_job("jr-sup") is not None and os.path.exists(
        rj.journal_path(data_dir, "jr-sup")
    ), "上游被缓行账引用: I1 缓行不删"
    assert mod.get_job("jr-fail") is not None, "挂账 failed 缓行(Q11/major-2: 挂账是常驻提示态)"
    assert mod.get_job("jr-fail").resume_pending, "挂账原样"
    # 回执双归因: 挂账缓行 + I1 兜底各占一句; remaining = 计数(逐条点名走程序日志)
    assert result["remaining"] == 2, result
    assert "恢复确认挂账" in result["note"], result["note"]
    assert "未能清除" in result["note"], "I1 兜底归因在 note(不点名单一原因, 明细交程序日志)"
    # 逐条点名走程序日志(note 只带计数, 评审 minor-R2-2 口径): 挂账行点 jr-fail, I1 行点 jr-sup
    assert any("缓行(恢复确认挂账)" in m and "jr-fail" in m for m in cap.messages), cap.text
    assert any("未清除(I1 引用保护或盘面删除失败)" in m and "jr-sup" in m for m in cap.messages), cap.text
    # 挂账未闭合: 重复清空幂等零动作(黄金法则 1)
    result2 = mod.relocate_clear_history()
    assert result2["cleared"] == 0 and result2["remaining"] == 2, result2
