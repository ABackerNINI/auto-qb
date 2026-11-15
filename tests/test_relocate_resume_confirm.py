"""test_relocate_resume_confirm 测试计划: relocate 恢复成员运行态的确认契约
(issue 26-11-14-1744: resume 单发即弃 -> 有界退避重试 + 终态出口恢复确认 + 余量挂账)

验收判据(issue §06 (1)+(2); (3)「待恢复余量进面板展示」属下一批, 本批只备数据面):
- (1) resume 调用异常不再单发即弃: 登记跨拍重试(仿 _TAG_RETRY_SECONDS 退避形态),
  退避点补发, 补发有界(常数上界, 不新增配置键), 穷尽后计数告警 + 余量记进 job 账;
- (2) 终态出口恢复确认: 快照回流后(store 为 qB 镜像)核对 resume_hashes 成员回到
  非 stopped 态, 未回去的补发; 全员回去即闭合(对照 qB 真实态判定, 幂等);
- 确认账挂 job 账(resume_pending/resume_retries)随 state 走, 重启续跑不丢;
- job 照常走终态(照常终态+余量挂账): 恢复问题绝不改相位/终态判定(与标签镜像同纪律);
- 黄金法则 5: 重试跨拍推进, 拍内零等待零重发; dry-run 零写。

## 测试计划(每个测试函数一条)
- test_resume_issue_failure_books_pending_and_reissues: 出口 resume 异常 -> 计数告警 +
  挂账(resume_pending=resume_hashes) -> 退避窗内不重发 -> 退避点补发成功 -> 成员回
  运行态 -> 确认闭合清账((1)+(2) 主链)
- test_resume_reissue_only_still_stopped_members: 部分成员已回来时补发只含仍停着的成员
- test_resume_retries_exhausted_books_surplus_then_self_heals: 补发穷尽(3 次)后不再补发
  + 穷尽告警每开账回合一笔 + 余量留存账上; 双成员部分自愈 -> 账面收敛为仍停着的子集
  (零补发零新告警), 全员恢复 -> 自愈清空(幂等: 重复拍无副作用)
- test_resume_budget_shared_across_exits: 补发预算跨出口共享 —— armed 期耗 1 次补发后
  同 job 再走 _fail 二次开账, resume_retries 延续不清零(armed->failed 生产可达双开账链)
- test_resume_issue_failure_at_exhausted_budget_no_empty_promise: 预算穷尽后出口首发
  失败 -> 文案如实写「不再补发」(不承诺不会发生的退避补发), 确认循环零补发; 穷尽
  告警按新开账回合重挂一笔(出口重开账有意重新武装, 防新回合穷尽被旧去重吞掉)
- test_exit_arm_resume_confirmed_closed: 武装出口(成功确认): armed 时恢复已下发且确认闭合
- test_exit_arm_resume_pending_reissues_until_confirmed: 武装出口(失败补发): qB 收了但
  成员仍停着 -> 挂账跨拍退避补发, 退避窗内零重发(黄金法则 5)
- test_exit_arm_resume_exhausted_keeps_phase_and_books: 武装出口(穷尽告警): resume 一路
  异常 -> 补发穷尽 -> 余量挂账 + 计数告警, 相位保持 armed(恢复问题不改终态判定)
- test_exit_cancel_books_pending_and_closes: 撤销出口: CANCELLED 后确认账开账并随确认闭合
- test_exit_fail_books_pending_on_failed: 失败出口: FAILED 后挂账(失败补发面, 单元形态)
- test_finish_direct_books_after_done: 单成员收口: 挂账在 done 落账之后(次序守卫 ——
  挂账若在终态 _set_job 之前会被旧对象 replace 整体覆盖丢失)
- test_resume_fields_roundtrip_and_restart: resume_pending/resume_retries 随 job_to_dict/
  job_from_dict 往返(旧账缺字段 = 空账)+ 重启(_load_jobs)后续跑不丢
- test_no_resume_hashes_is_noop: 无暂停成员(豁免/直接形态)零 API 调用零挂账
- test_dry_run_reconcile_never_writes: dry-run 下确认核对零动作(不补发不落盘)
- test_resuming_registry_tracks_account_no_lag: resuming 登记 = 账窗口 —— 挂账拍即登记
  (随 _note_resume_state 即时重算, 不等 _set_job 不滞后), 账闭合拍即撤登记; 老 store
  替身无该字段自建不炸(issue 26-11-15-0441)
### job_id 复用结转(issue 26-11-15-0344, 计划 26-11-15-0914 S1)
- test_carried_resume_pending_reopens_account_via_arm_chain: 旧账结转成员并入新账 resume_hashes 后,
  经 _arm 开账面(_resume_members)挂账全量 + retries 从 0 重计, 退避点补发仍停着的结转成员,
  快照回流后确认闭合(走正常补发确认链)
- test_resuming_registry_keeps_terminal_job_and_exhausted_members: 终态挂账 job 仍登记
  (不沿用 active_jobs 过滤); 穷尽收敛(pending 只剩仍停者)登记保持, 自愈闭合即撤
- test_resuming_registry_rebuilt_on_load_jobs: 启动加载面 —— state 恢复的挂账 job(终态与否)
  经 _load_jobs 重建登记(resume_pending 随 state 持久, 让路窗口在第一次账面变更前就在场)
### 已删成员闭账(issue 26-11-15-0345, 计划 26-11-15-0914 S2)
- test_resume_deleted_member_confirmed_closes_account: 连续 3 拍不在 store -> 判真删除闭账
  (pending/resume_hashes 双清 + 闭账日志一行, 零 qB 写)
- test_resume_snapshot_gap_resets_deleted_streak: 1-2 拍缺失后成员重现 -> streak 重置不闭
  (快照空窗防误闭, 保守原则正面钉); 断续缺失再多也不闭, 重新连续 3 拍才闭
- test_resume_all_deleted_closes_via_existing_close_path: 全员删除 -> 闭账后既有闭合路径
  INFO 接管(退避表/穷尽去重清掉, 账面双清归零)
- test_resume_mixed_deleted_and_stopped_only_deleted_closed: 混合(部分删部分停) -> 只闭已删,
  余量停着成员继续走补发链(预算/退避不乱)
- test_resume_closure_adds_no_exhaustion_warning: 闭账不新增穷尽告警(穷尽告警仍每开账回合
  一笔, 闭账拍与闭账后零新增零重复)
- test_resume_closure_recomputes_registries: 闭账后 relocating/resuming 登记即时重算正确
  (已删成员撤出两面, 停着的余量保留)
- test_resume_closure_idempotent: 幂等: 闭账后重复拍无副作用(账面/登记零变化, 零新日志)
- test_resume_deleted_closure_keeps_non_pending_member: 闭账只删 pending 里确认真删的成员,
  resume_hashes 上非 pending(已闭合)成员保留(kept 过滤, issue 26-11-15-1433); 把闭账口径
  改成全账扫 resume_hashes 或把账面收敛成 remaining pending 都必红
### 计数器停机摘要(issue 26-11-15-0345-feat, 计划 26-11-15-0914 S4)
- test_stop_logs_failure_counters_zero: stop() 停机摘要一行, 全 0 也打(D12)
- test_stop_logs_failure_counters_nonzero: 非 0 形态如实带出两个绝对计数(不建分母, D13)
"""

import types

from dataclasses import replace

from auto_qb.core.modules import relocate_units as ru

from clock import FakeClock

from helpers import capture_logs, pin_disk_usage, relocate_env

from relocate_exec_support import _bare_mod, _job, _rec, _run_ticks, _simulate_moved, _spy_spawn, _stub_probe_pass

RESUME_BACKOFF = 30.0
RESUME_MAX = 3
DELETED_TICKS = 3  # 镜像 relocate_lifecycle._DELETED_CONFIRM_TICKS(闭账确认拍数)
LOG_NAME = "auto_qb.core.modules.relocate_mod"


def _stopped(h="HA"):
    return _rec(h=h, state="pausedUP")


def _running(h="HA"):
    return _rec(h=h, state="stalledUP")


def _resume_mod(api, store=None):
    """裸模块 + 假钟: 恢复确认机制的单元形态(不落真盘, state 用 SimpleNamespace 箱)"""
    mod = _bare_mod(api=api, store=store)
    mod._clock = FakeClock()
    return mod


def test_resume_issue_failure_books_pending_and_reissues():
    """出口 resume 异常: 计数告警 + 挂账 -> 退避窗内不重发 -> 退避点补发 -> 确认闭合((1)+(2) 主链)"""
    issues = []
    state = {"first": True}

    def _resume(**kw):
        if state["first"]:
            state["first"] = False
            raise RuntimeError("qB 失联")
        return issues.append(list(kw["torrent_hashes"]))

    mod = _resume_mod(
        api=types.SimpleNamespace(torrents_resume=_resume),
        store=types.SimpleNamespace(by_hash={"HA": _stopped()}, relocating_hashes=set()),
    )
    mod._fail(_job(resume_hashes=("HA", )), "move_stalled", "停滞")  # 失败出口触发恢复, 首发即异常

    job = mod._jobs["j1"]
    assert job.phase == ru.PHASE_FAILED
    assert job.resume_pending == ("HA", ), "首发异常必须开确认账(等快照回流核对)"
    assert job.resume_retries == 0 and mod._resume_failures == 1
    # 退避窗内: 不重发(跨拍退避, 黄金法则 5)
    mod._reconcile_resume_pending()
    assert issues == [] and mod._jobs["j1"].resume_retries == 0

    # 退避点已到 + 成员仍停着: 补发一次(计入预算), 这次成功
    mod._clock.advance(RESUME_BACKOFF)
    mod._reconcile_resume_pending()
    assert issues == [["HA"]], issues
    assert mod._jobs["j1"].resume_retries == 1

    # 成员回到运行态(快照回流): 确认闭合清账
    mod._ctx.store.by_hash["HA"] = _running()
    mod._clock.advance(RESUME_BACKOFF)
    mod._reconcile_resume_pending()
    assert mod._jobs["j1"].resume_pending == ()
    assert "j1" not in mod._resume_next_try


def test_resume_reissue_only_still_stopped_members():
    """补发只发仍停着的成员: 已回运行态的成员不再重复下发(对照 qB 实况, 幂等)"""
    issues = []
    mod = _resume_mod(
        api=types.SimpleNamespace(torrents_resume=lambda **kw: issues.append(list(kw["torrent_hashes"]))),
        store=types.SimpleNamespace(by_hash={
            "HA": _stopped("HA"),
            "HB": _running("HB")
        }, relocating_hashes=set()),
    )
    mod._jobs["j1"] = _job("j1", phase=ru.PHASE_FAILED, resume_hashes=("HA", "HB"))
    mod._note_resume_state("j1", ("HA", "HB"), 0)
    mod._clock.advance(RESUME_BACKOFF)
    mod._reconcile_resume_pending()
    assert issues == [["HA"]], "已恢复的 HB 不得重复下发"
    assert mod._jobs["j1"].resume_pending == ("HA", )


def test_resume_retries_exhausted_books_surplus_then_self_heals():
    """补发穷尽(3 次)后不再补发 + 穷尽告警每开账回合一笔 + 余量挂账; 部分自愈 -> 账面收敛为
    仍停着的子集(零补发零新告警), 全员恢复 -> 自愈清空(幂等: 重复拍无副作用)"""
    issues = []

    def _boom(**kw):
        issues.append(list(kw["torrent_hashes"]))
        raise RuntimeError("qB 失联")

    mod = _resume_mod(
        api=types.SimpleNamespace(torrents_resume=_boom),
        store=types.SimpleNamespace(by_hash={
            "HA": _stopped("HA"),
            "HB": _stopped("HB")
        }, relocating_hashes=set()),
    )
    mod._fail(_job(resume_hashes=("HA", "HB")), "move_stalled", "停滞")
    issues.clear()

    for i in range(RESUME_MAX):  # 首发(出口)后 3 次退避补发, 全部异常
        mod._clock.advance(RESUME_BACKOFF)
        mod._reconcile_resume_pending()
        assert mod._jobs["j1"].resume_retries == i + 1
    mod._clock.advance(RESUME_BACKOFF)
    with capture_logs(LOG_NAME) as cap:
        mod._reconcile_resume_pending()  # 穷尽面: 告警 + 挂账
    job = mod._jobs["j1"]
    assert job.resume_retries == RESUME_MAX, "三次补发后预算穷尽"
    assert len(issues) == RESUME_MAX, f"首发之后只补发 {RESUME_MAX} 次: {issues}"
    assert job.resume_pending == ("HA", "HB"), "穷尽后余量留存账上(待恢复余量, 面板下一批接线)"
    assert any("恢复确认穷尽" in m and "HA" in m for m in cap.messages), cap.messages

    # 部分自愈(HB 回来了, HA 仍停着): 穷尽面只收敛账面 —— 零补发、零新告警
    failures_at_exhaustion = mod._resume_failures
    mod._ctx.store.by_hash["HB"] = _running("HB")
    mod._clock.advance(RESUME_BACKOFF)
    with capture_logs(LOG_NAME) as cap2:
        mod._reconcile_resume_pending()
    assert mod._jobs["j1"].resume_pending == ("HA", ), "账面收敛为仍停着的子集(部分自愈)"
    assert len(issues) == RESUME_MAX, "穷尽后不得再消耗 qB 写"
    assert mod._resume_failures == failures_at_exhaustion, "部分自愈不新增计数"
    assert not any("恢复确认穷尽" in m for m in cap2.messages), "穷尽告警本回合内不重复"

    # 重复拍: 账面已收敛, 零动作(幂等)
    mod._clock.advance(RESUME_BACKOFF)
    mod._reconcile_resume_pending()
    assert mod._jobs["j1"].resume_pending == ("HA", ) and len(issues) == RESUME_MAX

    # 全员回来(用户手动/qB 自愈): 账面按实况自愈清空 —— 挂账不是永久判决
    mod._ctx.store.by_hash["HA"] = _running()
    mod._reconcile_resume_pending()
    assert mod._jobs["j1"].resume_pending == ()
    assert mod._resume_failures == 1 + RESUME_MAX + 1, "首发 1 + 补发 3 + 穷尽 1"


def test_resume_budget_shared_across_exits():
    """补发预算跨出口共享: armed 期耗 1 次补发后同 job 再走 _fail 二次开账, resume_retries
    延续不清零(armed->failed 生产可达双开账链: journal failed 消费/核验失败都会走 _fail)"""
    issues = []
    mod = _resume_mod(
        api=types.SimpleNamespace(torrents_resume=lambda **kw: issues.append(list(kw["torrent_hashes"]))),
        store=types.SimpleNamespace(by_hash={"HA": _stopped()}, relocating_hashes=set()),
    )
    mod._jobs["j1"] = _job(phase=ru.PHASE_ARMED, resume_hashes=("HA", ))
    mod._resume_members(mod._jobs["j1"])  # armed 出口首发(成功下发, 确认未过)
    mod._clock.advance(RESUME_BACKOFF)
    mod._reconcile_resume_pending()  # 补发一次 -> retries=1
    assert mod._jobs["j1"].resume_retries == 1

    # 同一 job 再走失败出口(armed->failed): 二次开账不清零 —— 预算跨出口共享
    out = mod._fail(mod._jobs["j1"], "verify_mismatch", "不符")
    assert out.phase == ru.PHASE_FAILED
    assert mod._jobs["j1"].resume_retries == 1, "二次开账延续已耗补发次数(开账不清零)"
    assert mod._jobs["j1"].resume_pending == ("HA", ), "失败出口重开账(挂账随 resume_hashes 重挂)"

    # 退避点后继续补发: 预算接着走(retries=2, 不是从头计)
    mod._clock.advance(RESUME_BACKOFF)
    mod._reconcile_resume_pending()
    assert mod._jobs["j1"].resume_retries == 2
    assert len(issues) == 4, "armed 首发 + armed 补发 + failed 首发 + failed 补发"


def test_resume_issue_failure_at_exhausted_budget_no_empty_promise():
    """预算穷尽后出口首发失败: 文案如实写「不再补发」(不承诺不会发生的退避补发),
    随后的确认循环零补发; 穷尽告警按新开账回合重挂一笔(nit#5/#6)"""
    issues = []

    def _boom(**kw):
        issues.append(list(kw["torrent_hashes"]))
        raise RuntimeError("qB 失联")

    mod = _resume_mod(
        api=types.SimpleNamespace(torrents_resume=_boom),
        store=types.SimpleNamespace(by_hash={"HA": _stopped()}, relocating_hashes=set()),
    )
    mod._jobs["j1"] = _job(phase=ru.PHASE_ARMED, resume_hashes=("HA", ))
    mod._resume_members(mod._jobs["j1"])  # armed 首发(异常)
    for _ in range(RESUME_MAX):  # 3 次退避补发, 全部异常 -> 预算穷尽
        mod._clock.advance(RESUME_BACKOFF)
        mod._reconcile_resume_pending()
    assert mod._jobs["j1"].resume_retries == RESUME_MAX
    assert mod._jobs["j1"].phase == ru.PHASE_ARMED

    # armed->failed 双开账链: 出口首发再次异常, 此时 retries 已达上界
    with capture_logs(LOG_NAME) as cap:
        mod._fail(mod._jobs["j1"], "verify_mismatch", "不符")
    assert mod._jobs["j1"].resume_retries == RESUME_MAX, "穷尽后的出口开账不再消耗预算"
    assert any("不再补发" in m and "恢复成员运行态失败" in m for m in cap.messages), cap.messages
    assert not any("将按退避补发" in m for m in cap.messages), "不得承诺不会发生的退避补发"

    # 后续确认循环: 零补发; 穷尽告警按新开账回合重挂一笔(出口重开账重新武装了去重)
    mod._clock.advance(RESUME_BACKOFF)
    with capture_logs(LOG_NAME) as cap2:
        mod._reconcile_resume_pending()
    assert len(issues) == 1 + RESUME_MAX + 1, "只有各次出口下发 + 3 次补发, 穷尽面零 qB 写"
    assert any("恢复确认穷尽" in m for m in cap2.messages), "新开账回合的穷尽不被旧去重吞掉"


def test_exit_arm_resume_confirmed_closed(tmp_path, monkeypatch):
    """武装出口(成功确认): armed 时恢复下发, 快照回流后确认闭合(成功面)"""
    pin_disk_usage(monkeypatch)
    _stub_probe_pass(monkeypatch)
    clock = FakeClock()
    mgr, client, src, dst, content, files = relocate_env(tmp_path, state="uploading", clock=clock)
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    job_id = mod.relocate_execute(["HA"], dst)[0]["job_id"]
    _simulate_moved(mgr, dst, files, content)
    _run_ticks(mod, 6)
    assert mod.get_job(job_id).phase == ru.PHASE_ARMED
    assert any(c[0] == "resume" for c in client.calls), "armed 出口必须恢复成员"
    assert mod.get_job(job_id).resume_pending == (), "成员已回运行态(stalledUP): 确认闭合"
    assert mod.get_job(job_id).resume_retries == 0


def test_exit_arm_resume_pending_reissues_until_confirmed(tmp_path, monkeypatch):
    """武装出口(失败补发): qB 收了但成员仍停着 -> 挂账 + 退避窗内零重发 + 退避点补发"""
    pin_disk_usage(monkeypatch)
    _stub_probe_pass(monkeypatch)
    clock = FakeClock()
    mgr, client, src, dst, content, files = relocate_env(tmp_path, state="uploading", clock=clock)
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    real_resume = client.torrents_resume
    resumes = []
    client.torrents_resume = lambda torrent_hashes=None: resumes.append(list(torrent_hashes or []))
    job_id = mod.relocate_execute(["HA"], dst)[0]["job_id"]
    _simulate_moved(mgr, dst, files, content)
    _run_ticks(mod, 6)
    job = mod.get_job(job_id)
    assert job.phase == ru.PHASE_ARMED
    assert job.resume_pending == ("HA", "HB"), "resume 未生效(替身不翻 state): 确认账保持开"
    assert mod._resume_failures == 0, "API 没抛错: 只有确认未过, 不计失败"

    _run_ticks(mod, 2)  # 退避窗内: 零重发(黄金法则 5)
    assert mod.get_job(job_id).resume_retries == 0
    assert len(resumes) == 1, "只有 armed 首发一次"

    clock.advance(RESUME_BACKOFF)
    _run_ticks(mod, 1)
    assert mod.get_job(job_id).resume_retries == 1
    assert len(resumes) == 2, "首发(armed) + 一次补发"

    # 快照回流: 成员真回运行态 -> 下一拍确认闭合
    client.torrents_resume = real_resume
    client.torrents_resume(torrent_hashes=["HA", "HB"])
    _run_ticks(mod, 1)
    assert mod.get_job(job_id).resume_pending == ()


def test_exit_arm_resume_exhausted_keeps_phase_and_books(tmp_path, monkeypatch):
    """武装出口(穷尽告警): resume 一路异常 -> 补发穷尽 -> 余量挂账 + 计数告警, 相位保持 armed"""
    pin_disk_usage(monkeypatch)
    _stub_probe_pass(monkeypatch)
    clock = FakeClock()
    mgr, client, src, dst, content, files = relocate_env(tmp_path, state="uploading", clock=clock)
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])

    def _boom(**kw):
        raise RuntimeError("qB 失联")

    monkeypatch.setattr(client, "torrents_resume", _boom, raising=False)
    job_id = mod.relocate_execute(["HA"], dst)[0]["job_id"]
    _simulate_moved(mgr, dst, files, content)
    _run_ticks(mod, 6)
    assert mod.get_job(job_id).phase == ru.PHASE_ARMED, "恢复失败绝不改相位/终态判定"
    assert mod.get_job(job_id).resume_pending == ("HA", "HB")

    for i in range(RESUME_MAX):
        clock.advance(RESUME_BACKOFF)
        _run_ticks(mod, 1)
        assert mod.get_job(job_id).resume_retries == i + 1
    clock.advance(RESUME_BACKOFF)
    with capture_logs(LOG_NAME) as cap:
        _run_ticks(mod, 1)
    assert any("恢复确认穷尽" in m for m in cap.messages), cap.messages
    job = mod.get_job(job_id)
    assert job.phase == ru.PHASE_ARMED and job.resume_pending == ("HA", "HB"), "余量挂账, 相位不动"
    assert mod._resume_failures >= 1 + RESUME_MAX + 1

    # 穷尽后再推进: 计数不再增长(有界), 告警不重复
    failures_before = mod._resume_failures
    clock.advance(RESUME_BACKOFF)
    with capture_logs(LOG_NAME) as cap2:
        _run_ticks(mod, 1)
    assert mod._resume_failures == failures_before
    assert not any("恢复确认穷尽" in m for m in cap2.messages)


def test_exit_cancel_books_pending_and_closes(tmp_path, monkeypatch):
    """撤销出口: CANCELLED 后确认账开账并随确认闭合(成员已回运行态)"""
    pin_disk_usage(monkeypatch)
    _stub_probe_pass(monkeypatch)
    clock = FakeClock()
    mgr, client, src, dst, content, files = relocate_env(tmp_path, state="uploading", clock=clock)
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    job_id = mod.relocate_execute(["HA"], dst)[0]["job_id"]
    _simulate_moved(mgr, dst, files, content)
    _run_ticks(mod, 6)
    r = mod.relocate_cancel(job_id, cost_confirmed=True)
    assert r["cls"] == "ok" and mod.get_job(job_id).phase == ru.PHASE_CANCELLED
    assert mod.get_job(job_id).resume_pending == ("HA", "HB"), "撤销出口必须开确认账(本用例自证)"
    _run_ticks(mod, 1)
    assert mod.get_job(job_id).resume_pending == (), "撤销出口的恢复确认随实况闭合"


def test_exit_fail_books_pending_on_failed():
    """失败出口(单元形态): FAILED 后确认账挂账(失败补发面; API 正常时等快照回流核对)"""
    issues = []
    mod = _resume_mod(
        api=types.SimpleNamespace(torrents_resume=lambda **kw: issues.append(list(kw["torrent_hashes"]))),
        store=types.SimpleNamespace(by_hash={"HA": _stopped()}, relocating_hashes=set()),
    )
    mod._jobs["j1"] = _job(phase=ru.PHASE_ARMED, resume_hashes=("HA", ))
    out = mod._fail(mod._jobs["j1"], "verify_mismatch", "不符")
    assert out.phase == ru.PHASE_FAILED
    assert mod._jobs["j1"].resume_pending == ("HA", ) and mod._resume_failures == 0
    assert issues == [["HA"]]


def test_finish_direct_books_after_done():
    """单成员收口: 确认账挂账必须在 done 落账之后 —— 否则被旧对象 replace 覆盖丢失(次序守卫)"""
    issues = []
    mod = _resume_mod(
        api=types.SimpleNamespace(
            client=None,
            torrents_resume=lambda **kw: issues.append(list(kw["torrent_hashes"])),
        )
    )
    mod._ctx.grouping = types.SimpleNamespace(regroup_scope=lambda *a: None)
    mod._finish_direct(_job("j8", src="R:/src8", resume_hashes=("HA", )))
    saved = mod._jobs["j8"]
    assert saved.phase == ru.PHASE_DONE and saved.reason == "direct"
    assert saved.resume_pending == ("HA", ), "done 落账后挂账必须留存(次序守卫)"
    assert issues == [["HA"]]


def test_resume_fields_roundtrip_and_restart(tmp_path, monkeypatch):
    """resume_pending/resume_retries 随 job_to_dict/job_from_dict 往返 + 重启续跑(黄金法则 3)"""
    pin_disk_usage(monkeypatch)
    _stub_probe_pass(monkeypatch)
    clock = FakeClock()
    mgr, client, src, dst, content, files = relocate_env(tmp_path, state="uploading", clock=clock)
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])

    def _boom(**kw):
        raise RuntimeError("qB 失联")

    monkeypatch.setattr(client, "torrents_resume", _boom, raising=False)
    job_id = mod.relocate_execute(["HA"], dst)[0]["job_id"]
    _simulate_moved(mgr, dst, files, content)
    _run_ticks(mod, 6)
    clock.advance(RESUME_BACKOFF)
    _run_ticks(mod, 1)
    before = mod.get_job(job_id)
    assert before.resume_pending == ("HA", "HB") and before.resume_retries == 1

    # 序列化往返: 新字段随账走
    back = ru.job_from_dict(ru.job_to_dict(before))
    assert back.resume_pending == ("HA", "HB") and back.resume_retries == 1
    # 旧账(缺新字段)= 空账, 不进确认循环(历史 job 行为不变)
    legacy = ru.job_from_dict({**ru.job_to_dict(before), "resume_pending": None, "resume_retries": None})
    assert legacy.resume_pending == () and legacy.resume_retries == 0

    # 重启: 新模块 _load_jobs 恢复确认账, 续跑不丢(退避点后照常补发)
    mod2 = type(mod)(mgr.ctx, clock=clock)
    assert mod2._load_jobs() == 1
    restored = mod2.get_job(job_id)
    assert restored.resume_pending == ("HA", "HB") and restored.resume_retries == 1
    clock.advance(RESUME_BACKOFF)
    resumes = []
    mod2._ctx.api = types.SimpleNamespace(torrents_resume=lambda **kw: resumes.append(list(kw["torrent_hashes"])))
    mod2._reconcile_resume_pending()
    assert resumes == [["HA", "HB"]], "重启后确认循环续跑: 退避点补发"
    assert mod2.get_job(job_id).resume_retries == 2


def test_no_resume_hashes_is_noop():
    """无暂停成员(豁免路径/直接形态): 零 API 调用零挂账(既有幂等 no-op 口径不变)"""
    issues = []
    mod = _resume_mod(api=types.SimpleNamespace(torrents_resume=lambda **kw: issues.append(kw)))
    mod._jobs["j1"] = _job(phase=ru.PHASE_ARMED, resume_hashes=())
    mod._resume_members(mod._jobs["j1"])
    assert issues == [] and mod._jobs["j1"].resume_pending == ()
    mod._reconcile_resume_pending()  # 空账不进确认循环, 零动作不炸
    assert mod._jobs["j1"].resume_pending == ()


def test_dry_run_reconcile_never_writes():
    """dry-run: 确认核对零动作(不补发不落盘) —— 与 on_task_line 同闸, 直调面也稳"""
    issues = []
    mod = _resume_mod(api=types.SimpleNamespace(torrents_resume=lambda **kw: issues.append(kw)))
    mod._dry = True
    mod._jobs["j1"] = _job(phase=ru.PHASE_FAILED, resume_hashes=("HA", ))
    mod._note_resume_state("j1", ("HA", ), 2)
    mod._clock.advance(RESUME_BACKOFF)
    mod._reconcile_resume_pending()
    assert issues == [] and mod._jobs["j1"].resume_retries == 2, "dry-run 不推进确认循环"
    assert mod._jobs["j1"].resume_pending == ("HA", )


# ---------- resuming 登记(fuse 让路口径, issue 26-11-15-0441): 生命周期 = 账窗口 ----------
# 口径: fuse 让路 = resume_pending 非空的账窗口(store.resuming_hashes, _sync_resuming 单点
# 重算), 不再消费 job 级的 relocating_hashes —— 挂账拍登记在场, 闭合拍撤登记, 终态挂账
# job 与穷尽仍停者都不漏。登记本身保留 relocating(grouping/ops_skip/qbapi 仍消费)。


def test_resuming_registry_tracks_account_no_lag():
    """登记随落账即时重算不滞后: 挂账拍即登记(不等 _set_job —— 挂账单点不走它), 账闭合拍
    即撤登记; 老 store 替身无 resuming_hashes 字段自建一份不炸(getattr 缺省口径)"""
    mod = _resume_mod(
        api=types.SimpleNamespace(torrents_resume=lambda **kw: None),
        store=types.SimpleNamespace(by_hash={"HA": _running()}),
    )
    assert not hasattr(mod._ctx.store, "resuming_hashes"), "替身无该字段(老形状)"
    mod._jobs["j1"] = _job(phase=ru.PHASE_ARMED, resume_hashes=("HA", ))
    mod._note_resume_state("j1", ("HA", ), 0)  # 挂账(落账单点): 不经 _set_job
    assert mod._ctx.store.resuming_hashes == {"HA"}, "挂账即登记(同一落账点内重算, 不滞后一拍)"
    mod._reconcile_resume_pending()  # 成员已回运行态(stalledUP): 确认闭合清账
    assert mod._jobs["j1"].resume_pending == ()
    assert mod._ctx.store.resuming_hashes == set(), "账闭合即撤登记"


def test_resuming_registry_keeps_terminal_job_and_exhausted_members():
    """终态挂账 job 仍登记(不沿用 relocating 的 active_jobs 过滤 —— reconcile 对账口径就是
    终态也扫); 穷尽收敛(pending 只剩仍停者)登记保持, 全员自愈回运行态即闭合撤登记"""
    issues = []

    def _boom(**kw):
        issues.append(list(kw["torrent_hashes"]))
        raise RuntimeError("qB 失联")

    mod = _resume_mod(
        api=types.SimpleNamespace(torrents_resume=_boom), store=types.SimpleNamespace(by_hash={"HA": _stopped()})
    )
    mod._fail(_job(resume_hashes=("HA", )), "move_stalled", "停滞")
    assert mod._jobs["j1"].phase == ru.PHASE_FAILED, "job 已终态"
    assert mod._ctx.store.resuming_hashes == {"HA"}, "终态挂账 job 仍登记(armed 期穷尽后同 job 终态仍挂账)"
    for _ in range(RESUME_MAX):  # 补发穷尽(全部异常): pending 收敛到仍停者, 登记保持
        mod._clock.advance(RESUME_BACKOFF)
        mod._reconcile_resume_pending()
    assert mod._jobs["j1"].resume_retries == RESUME_MAX
    assert mod._jobs["j1"].resume_pending == ("HA", )
    assert mod._ctx.store.resuming_hashes == {"HA"}, "穷尽仍停者继续登记(triggered 分支不补暂停口径保持)"
    mod._ctx.store.by_hash["HA"] = _running()  # 用户手动恢复/qB 自愈
    mod._reconcile_resume_pending()
    assert mod._ctx.store.resuming_hashes == set(), "自愈闭合即撤登记"


def test_resuming_registry_rebuilt_on_load_jobs():
    """启动加载面: state 恢复的挂账 job(终态与否)经 _load_jobs 重建登记 —— resume_pending
    随 state 持久, 重启后账还活着, 让路窗口在第一次账面变更前就在场(走 _sync_relocating 漏斗)"""
    mod = _resume_mod(api=types.SimpleNamespace(torrents_resume=lambda **kw: None))
    mod._ctx.state.data = {
        "relocate":
            {
                "jobs":
                    {
                        "j1":
                            ru.job_to_dict(
                                _job(
                                    "j1", phase=ru.PHASE_ARMED, resume_hashes=("HA", "HB"), resume_pending=("HA", "HB")
                                )
                            ),
                        "j2":
                            ru.job_to_dict(
                                _job("j2", phase=ru.PHASE_FAILED, resume_hashes=("HC", ), resume_pending=("HC", ))
                            ),
                    }
            }
    }
    assert mod._load_jobs() == 2
    assert mod._ctx.store.resuming_hashes == {"HA", "HB", "HC"}, "挂账 job(含终态 j2)的成员全部重建进登记"


def test_carried_resume_pending_reopens_account_via_arm_chain():
    """旧账结转成员经 _arm 开账后走正常补发确认链(issue 26-11-15-0344, S1 用例(5))

    同 id 重发把 prev.resume_pending 结转进新账 resume_hashes(现场在前/结转在后), _arm 的
    开账面(_resume_members)按新生命周期挂账全量 + retries 从 0 重计; 退避点补发仍停着的
    结转成员, 快照回流后确认闭合 —— 结转余量重获补发预算, 不因旧生命周期穷尽而失明。
    """
    issues = []
    mod = _resume_mod(
        api=types.SimpleNamespace(torrents_resume=lambda **kw: issues.append(list(kw["torrent_hashes"]))),
        store=types.SimpleNamespace(by_hash={
            "HC": _running("HC"),
            "HB": _stopped("HB")
        }, relocating_hashes=set()),
    )
    # 上一生命周期: 终态 + 穷尽挂账(HB 未恢复, retries 已耗尽)
    mod._jobs["j1"] = _job(
        "j1", phase=ru.PHASE_FAILED, resume_hashes=("HA", "HB"), resume_pending=("HB", ), resume_retries=RESUME_MAX
    )
    fresh = _job("j1", resume_hashes=("HC", ))
    carried = mod._carry_prev_state("j1", fresh)
    assert carried.resume_hashes == ("HC", "HB"), carried.resume_hashes

    armed = replace(carried, phase=ru.PHASE_ARMED)
    mod._jobs["j1"] = armed
    mod._resume_members(armed)  # _arm 的开账面
    assert issues == [["HC", "HB"]], issues  # 现场 + 结转余量一次下发
    assert mod._jobs["j1"].resume_pending == ("HC", "HB"), "开账挂全量, 等快照回流核对"
    assert mod._jobs["j1"].resume_retries == 0, "新生命周期 retries 从 0 重计(旧账穷尽不结转)"

    # HC 已回运行态 -> 账面收敛; 退避点补发仍停着的结转成员 HB(预算从 0 重获, 第 1/3 次)
    mod._clock.advance(RESUME_BACKOFF)
    mod._reconcile_resume_pending()
    assert issues[-1] == ["HB"], issues
    assert mod._jobs["j1"].resume_pending == ("HB", )
    assert mod._jobs["j1"].resume_retries == 1

    # 结转成员回运行态(快照回流): 确认闭合清账
    mod._ctx.store.by_hash["HB"] = _running("HB")
    mod._clock.advance(RESUME_BACKOFF)
    mod._reconcile_resume_pending()
    assert mod._jobs["j1"].resume_pending == ()
    assert "j1" not in mod._resume_next_try


# ---------- 已删成员闭账(issue 26-11-15-0345, 计划 26-11-15-0914 S2) ----------
# 口径: _member_stopped 的保守二态(不在 store 按停着, 宁挂账勿漏恢复)保留, 第三态
# 「确认真删除」= 连续 DELETED_TICKS 拍不在 store 才闭账(双面同删, D4/D9/D10);
# 快照空窗(未达 N 拍)不误闭, 闭账零 qB 写、零 job 新增字段, 幂等(黄金法则 1)。


def test_resume_deleted_member_confirmed_closes_account():
    """连续 3 拍不在 store -> 判真删除闭账: pending/resume_hashes 双清 + 闭账日志一行(零 qB 写)"""
    issues = []
    mod = _resume_mod(
        api=types.SimpleNamespace(torrents_resume=lambda **kw: issues.append(list(kw["torrent_hashes"]))),
        store=types.SimpleNamespace(by_hash={}, relocating_hashes=set()),
    )
    mod._jobs["j1"] = _job(
        "j1", phase=ru.PHASE_FAILED, resume_hashes=("HA", ), resume_pending=("HA", ), resume_retries=RESUME_MAX
    )
    with capture_logs(LOG_NAME) as cap:
        mod._reconcile_resume_pending()  # 拍 1: 缺失 1 拍, 未达 N, 按停着走既有面
        assert mod._jobs["j1"].resume_pending == ("HA", ), "未达 N 拍不闭账"
        mod._reconcile_resume_pending()  # 拍 2: 缺失 2 拍, 仍未闭
        assert mod._jobs["j1"].resume_pending == ("HA", )
        mod._reconcile_resume_pending()  # 拍 3: 连续 3 拍 -> 真删除, 闭账
    job = mod._jobs["j1"]
    assert job.resume_pending == () and job.resume_hashes == (), "双面同删"
    assert any("成员已删除, 恢复账闭账" in m and "HA" in m for m in cap.messages), cap.messages
    assert issues == [], "闭账零 qB 写(已删成员不再补发)"


def test_resume_snapshot_gap_resets_deleted_streak():
    """1-2 拍缺失后成员重现 -> streak 重置不闭(快照空窗防误闭, 保守原则正面钉);
    断续缺失累计再多也不闭, 重新连续 3 拍才判真删除"""
    issues = []
    mod = _resume_mod(
        api=types.SimpleNamespace(torrents_resume=lambda **kw: issues.append(list(kw["torrent_hashes"]))),
        store=types.SimpleNamespace(by_hash={"HA": _stopped()}, relocating_hashes=set()),
    )
    mod._jobs["j1"] = _job(
        "j1", phase=ru.PHASE_FAILED, resume_hashes=("HA", ), resume_pending=("HA", ), resume_retries=RESUME_MAX
    )
    mod._resume_exhausted_warned.add("j1")  # 穷尽告警去重预挂: 本用例只盯闭账面
    mod._reconcile_resume_pending()
    mod._reconcile_resume_pending()  # 缺失 2 拍(未达 N)
    assert mod._jobs["j1"].resume_pending == ("HA", ), "未达 N 拍: 快照空窗不闭账"
    mod._ctx.store.by_hash["HA"] = _stopped()  # 重现(空窗结束)
    mod._reconcile_resume_pending()
    assert mod._jobs["j1"].resume_pending == ("HA", ) and ("j1", "HA") not in mod._deleted_streak, "重现即作废缺失计数"
    for _ in range(3):  # 断续缺失(每次只缺 2 拍)交替重现, 永不达连续 3 拍
        del mod._ctx.store.by_hash["HA"]
        mod._reconcile_resume_pending()
        mod._reconcile_resume_pending()
        mod._ctx.store.by_hash["HA"] = _stopped()
        mod._reconcile_resume_pending()
        assert mod._jobs["j1"].resume_pending == ("HA", ), "断续缺失不闭账(空窗不误闭)"
    del mod._ctx.store.by_hash["HA"]
    with capture_logs(LOG_NAME) as cap:
        for _ in range(DELETED_TICKS):  # 连续 3 拍 -> 闭账
            mod._reconcile_resume_pending()
    assert mod._jobs["j1"].resume_pending == () and mod._jobs["j1"].resume_hashes == ()
    assert any("成员已删除, 恢复账闭账" in m for m in cap.messages), cap.messages


def test_resume_all_deleted_closes_via_existing_close_path():
    """全员删除 -> 连续 3 拍后闭账(双清归零), 既有闭合路径接管: 退避表/穷尽去重清掉"""
    mod = _resume_mod(
        api=types.SimpleNamespace(torrents_resume=lambda **kw: None),
        store=types.SimpleNamespace(by_hash={}, relocating_hashes=set()),
    )
    mod._jobs["j1"] = _job(
        "j1",
        phase=ru.PHASE_ARMED,
        resume_hashes=("HA", "HB"),
        resume_pending=("HA", "HB"),
        resume_retries=RESUME_MAX,
    )
    mod._resume_next_try["j1"] = 1e18  # 退避表挂账(穷尽态常驻), 闭账应清掉
    mod._resume_exhausted_warned.add("j1")
    with capture_logs(LOG_NAME) as cap:
        for _ in range(DELETED_TICKS):
            mod._reconcile_resume_pending()
    job = mod._jobs["j1"]
    assert job.resume_pending == () and job.resume_hashes == (), "全员删除: 账面双清归零"
    assert "j1" not in mod._resume_next_try, "既有闭合路径清退避表"
    assert "j1" not in mod._resume_exhausted_warned, "既有闭合路径清穷尽去重"
    assert any("成员已删除, 恢复账闭账" in m for m in cap.messages), cap.messages
    assert any("恢复确认闭合" in m for m in cap.messages), "既有闭合路径 INFO 接管"


def test_resume_mixed_deleted_and_stopped_only_deleted_closed():
    """混合(部分删部分停) -> 只闭已删的, 余量停着成员继续走补发链(预算/退避不乱)"""
    issues = []
    mod = _resume_mod(
        api=types.SimpleNamespace(torrents_resume=lambda **kw: issues.append(list(kw["torrent_hashes"]))),
        store=types.SimpleNamespace(by_hash={"HB": _stopped("HB")}, relocating_hashes=set()),
    )
    mod._jobs["j1"] = _job("j1", phase=ru.PHASE_FAILED, resume_hashes=("HA", "HB"), resume_pending=("HA", "HB"))
    with capture_logs(LOG_NAME) as cap:
        mod._reconcile_resume_pending()  # 拍 1: HA 缺失 1 拍(未达 N 按停着), HB 停着 -> 补发含 HA+HB(现状行为)
        assert mod._jobs["j1"].resume_pending == ("HA", "HB")
        mod._clock.advance(RESUME_BACKOFF)
        mod._reconcile_resume_pending()  # 拍 2: HA 缺失 2 拍, 未达 N
        assert mod._jobs["j1"].resume_pending == ("HA", "HB")
        mod._clock.advance(RESUME_BACKOFF)
        mod._reconcile_resume_pending()  # 拍 3: HA 连续 3 拍 -> 闭账; HB 继续补发
    job = mod._jobs["j1"]
    assert job.resume_pending == ("HB", ) and job.resume_hashes == ("HB", ), "只闭已删的 HA, HB 留账"
    assert job.resume_retries == 3, "HB 的补发预算照常消耗"
    assert issues == [["HA", "HB"], ["HA", "HB"], ["HB"]], "第 3 拍补发只含仍停着的 HB"
    assert any("成员已删除, 恢复账闭账" in m and "HA" in m for m in cap.messages), cap.messages
    assert not any("成员已删除" in m and "HB" in m for m in cap.messages), "HB 仍停着, 不误闭"


def test_resume_deleted_closure_keeps_non_pending_member():
    """闭账只删 pending 里确认真删的成员: resume_hashes 上非 pending(已闭合)成员保留
    (kept 过滤, issue 26-11-15-1433)。生产形态 = 成员 HC 已回运行态从确认账闭合但仍在
    resume_hashes, 此后 HC 快照空窗不在 store; 无账可闭就不扩面。把 deleted 来源改成全账扫
    resume_hashes, 或把 kept 写成 remaining pending, 本例必红"""
    mod = _resume_mod(
        api=types.SimpleNamespace(torrents_resume=lambda **kw: None),
        store=types.SimpleNamespace(by_hash={}, relocating_hashes=set()),
    )
    mod._jobs["j1"] = _job(
        "j1",
        phase=ru.PHASE_FAILED,
        resume_hashes=("HC", "HA"),  # HC 已闭账出 pending(仍在账上), HA 还在确认账上
        resume_pending=("HA", ),
        resume_retries=RESUME_MAX,
    )
    mod._resume_exhausted_warned.add("j1")  # 穷尽告警去重预挂: 本例只盯闭账面
    with capture_logs(LOG_NAME) as cap:
        for _ in range(DELETED_TICKS):  # HA 连续 3 拍不在 store -> 确认真删除闭账
            mod._reconcile_resume_pending()
    job = mod._jobs["j1"]
    assert job.resume_hashes == ("HC", ), "非 pending 的 HC 不被闭账扩面清掉(kept 过滤)"
    assert job.resume_pending == (), "确认账上已删的 HA 撤出"
    closed = [m for m in cap.messages if "成员已删除, 恢复账闭账" in m]
    assert len(closed) == 1 and "HA" in closed[0] and "HC" not in closed[0], f"闭账只点名 HA: {closed}"


def test_resume_closure_adds_no_exhaustion_warning():
    """闭账不新增穷尽告警: 穷尽告警仍每开账回合一笔, 闭账拍与闭账后零新增零重复"""
    mod = _resume_mod(
        api=types.SimpleNamespace(torrents_resume=lambda **kw: None),
        store=types.SimpleNamespace(by_hash={}, relocating_hashes=set()),
    )
    mod._jobs["j1"] = _job(
        "j1", phase=ru.PHASE_FAILED, resume_hashes=("HA", ), resume_pending=("HA", ), resume_retries=RESUME_MAX
    )
    with capture_logs(LOG_NAME) as cap:
        for _ in range(DELETED_TICKS + 1):  # 3 拍闭账 + 1 拍幂等复查
            mod._reconcile_resume_pending()
    exhausted = [m for m in cap.messages if "恢复确认穷尽" in m]
    assert len(exhausted) == 1, "只拍 1 一笔(缺失未达 N 按停着走穷尽面), 闭账不新增"
    closure = [m for m in cap.messages if "成员已删除, 恢复账闭账" in m]
    assert len(closure) == 1, "闭账 INFO 一行, 重复拍不重复"
    assert mod._resume_failures == 1, "穷尽计数只在拍 1 计一笔"


def test_resume_closure_recomputes_registries():
    """闭账后 relocating/resuming 登记即时重算: 已删成员撤出两面, 停着的余量保留"""
    mod = _resume_mod(
        api=types.SimpleNamespace(torrents_resume=lambda **kw: None),
        store=types.SimpleNamespace(by_hash={"HB": _stopped("HB")}, relocating_hashes=set()),
    )
    mod._jobs["j1"] = _job(
        "j1",
        phase=ru.PHASE_ARMED,
        hashes=("HM", ),
        mover="HM",
        resume_hashes=("HA", "HB"),
        resume_pending=("HA", "HB"),
        resume_retries=RESUME_MAX,
    )
    mod._sync_relocating()  # 预挂登记: relocating = hashes ∪ resume_hashes
    assert mod._ctx.store.relocating_hashes == {"HM", "HA", "HB"}
    assert mod._ctx.store.resuming_hashes == {"HA", "HB"}
    for _ in range(DELETED_TICKS):  # HA 连续 3 拍不在 store -> 闭账
        mod._reconcile_resume_pending()
    assert mod._ctx.store.relocating_hashes == {"HM", "HB"}, "已删 HA 撤出 relocating, 现场成员 HM 与余量 HB 保留"
    assert mod._ctx.store.resuming_hashes == {"HB"}, "已删 HA 撤出 resuming; 停着的 HB 保留"


def test_resume_closure_idempotent():
    """幂等(黄金法则 1): 闭账后重复拍无副作用 —— 账面/登记零变化, 零新日志"""
    mod = _resume_mod(
        api=types.SimpleNamespace(torrents_resume=lambda **kw: None),
        store=types.SimpleNamespace(by_hash={}, relocating_hashes=set()),
    )
    mod._jobs["j1"] = _job(
        "j1", phase=ru.PHASE_FAILED, resume_hashes=("HA", ), resume_pending=("HA", ), resume_retries=RESUME_MAX
    )
    for _ in range(DELETED_TICKS):
        mod._reconcile_resume_pending()
    job = mod._jobs["j1"]
    assert job.resume_pending == () and job.resume_hashes == (), "闭账已完成(用例自证)"
    resuming_before = set(mod._ctx.store.resuming_hashes)
    with capture_logs(LOG_NAME) as cap:
        for _ in range(3):  # 重复拍
            mod._reconcile_resume_pending()
    assert mod._jobs["j1"] is job, "重复拍不重建账面对象"
    assert mod._jobs["j1"].resume_pending == () and mod._jobs["j1"].resume_hashes == ()
    assert set(mod._ctx.store.resuming_hashes) == resuming_before, "登记零变化"
    assert ("j1", "HA") not in mod._deleted_streak, "streak 已随闭账清掉"
    assert cap.messages == [], f"重复拍零新日志: {cap.messages}"


# ---------- 计数器停机摘要(issue 26-11-15-0345-feat, 计划 26-11-15-0914 S4) ----------
# 口径: stop() 收尾一行「relocate | 停机: tag_failures=N resume_failures=M」, 全 0 也打
# (D12); 绝对计数不建 attempts 分母(D13); 不进 state_file/webui(D6), 一行落位无第二挂点。


def test_stop_logs_failure_counters_zero():
    """stop() 停机摘要一行: 全 0 也打(D12)"""
    mod = _resume_mod(api=types.SimpleNamespace(torrents_resume=lambda **kw: None))
    assert mod._tag_failures == 0 and mod._resume_failures == 0
    with capture_logs(LOG_NAME) as cap:
        mod.stop()
    assert any("停机: tag_failures=0 resume_failures=0" in m for m in cap.messages), cap.messages


def test_stop_logs_failure_counters_nonzero():
    """stop() 停机摘要: 非 0 形态如实带出两个绝对计数(不建 attempts 分母, D13)"""
    mod = _resume_mod(api=types.SimpleNamespace(torrents_resume=lambda **kw: None))
    mod._tag_failures = 2
    mod._resume_failures = 5
    with capture_logs(LOG_NAME) as cap:
        mod.stop()
    assert any("停机" in m and "tag_failures=2" in m and "resume_failures=5" in m for m in cap.messages), cap.messages
