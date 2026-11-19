"""test_relocate_probe_consume 测试计划: verdict 消费与 pending 启动恢复(S3, 计划 26-11-10-2350
§03 落点段「verdict 消费」/ §04 S3 / §06 D9/D7 / §07 风险表 1/3/5 行, 并轨 26-11-15-2340 刀4)。

消费面 = RelocateModule.on_task_line 在 lifecycle 步进之前调 ExecMixin._consume_probe_verdict:
每 tick 至多消费一条结果队列 verdict(空队列 O(1) 跳过, 单步预算面), 消费四步 = (1)probe_put
(D7 原语义三态: passed 写 / failed env=False 写 / failed env=True 不写) (2)重放队首条目
(re-invoke relocate_execute 幂等面全新鲜, D6 只存意图) (3)probe_pending_pop 清条目 (4)槽释放
-> kick 下一条。次序钉死 = 清条目 -> 释放槽 -> kick 下一条; 重放在释放槽之前(此刻槽仍被本
指纹占)。防自环 = 重放回执带 PROBE_GATE_PROBING_KEY 时按 T2 天然路径识别终止(条目丢弃,
不再自动链, 下次真实触发再试)。启动/热启用面 = _probe_pending_recover: 超龄条目
(> PROBE_PENDING_MAX_AGE_S)清扫 + 审计留痕(风险表第 1 行), 队首重 kick 探测重启自动续跑(D7)。

环境复用 test_relocate_exec_probe_gate._gate_env(多成员组执行面)与
test_relocate_probe_gate_async 的注入形态(独立 runner: 独立结果队列/单飞槽/透传 factory/
替身 probe_fn, 隔离全局单例); 消费用例直接 mod._consume_probe_verdict()(单点面), D9 挂点与
重启恢复走 on_task_line/start()/apply() 全链。槽预置 try_acquire(fp) 模拟「verdict 是本指纹
在飞探测的结论」的自然路径前提; 指纹一律先 probe_salt_ensure(真实流在 _ensure_probe 内先
保盐后取指纹, 条目指纹与重放重算指纹才能同键)。

## 测试计划(每个测试函数一条)

- test_consume_throttle_one_verdict_per_tick: 节流 —— 队列两条 verdict 分两 tick 各消费一条
  (qsize 2->1->0), 各按 D7 处置缓存(passed 写 / failed 覆盖写); 空队列 tick 零动作
- test_consume_passed_replays_to_start_job: 重放命中 passed 缓存续跑到 _start_job —— 缓存写
  passed、job 建立(phase=moving, origin/dst 透传)、setLocation 下发、条目清、槽释放、
  pending 空则不 kick
- test_consume_fs_failure_cached_and_blocked: env=False 失败 verdict -> 缓存写 failed(evidence
  补 reason, 与内联收尾同形)且重放命中 failed 缓存 blocked(零建账零 setLocation), 条目清
- test_consume_env_failure_terminates_without_loop: 防自环 —— env=True 失败未缓存 -> 重放走
  T2 天然路径(merge_intent 命中自己条目 + try_start False)返回探测中回执 -> 条目被清、替身
  probe 零调用(不再 kick 不再重放)、槽释放、队列无新 verdict、零建账
- test_consume_release_then_kick_next_order: 槽释放与 kick 次序(清条目 -> 释放 -> kick):
  pop/release/try_start 三面插桩记事件序, kick 恰一次且指向等位下一条(src/dst 取自条目);
  重放走缓存不触 try_start
- test_consume_fingerprint_mismatch_defense: verdict 指纹与队首不一致(重启 desync/孤儿形态)
  —— 不重放防错位、条目保留、按 D7 写缓存、槽归属释放后队首孤儿意图被重 kick(自愈: 重新
  探测, head==in-flight 不变量恢复)
- test_consume_rearm_keeps_entry_when_replay_restarts_probe: 重武装 —— 槽空闲时消费线程启动
  失败合成的 runner_crashed verdict(env=True), 重放的 try_start 重起真探测: 条目保留、槽不
  释放, 新 verdict 到达后正常消费续跑到 _start_job
- test_on_task_line_consumes_verdict_before_stepping: D9 挂点 —— on_task_line 一拍内先消费
  (条目清/缓存写/job 建立)后步进; 空队列二拍既有相位推进照常(强制采样窗到期, _rt.sample_ts
  采样点被更新)
- test_recover_sweeps_stale_keeps_fresh: 超龄清扫(假钟) —— >120s 条目与坏 ts 条目清且审计
  留痕(条数+指纹), <=120s 边界保留; 清扫后队首重 kick 探测(恢复链); 槽被占时守卫跳过清扫
  零 kick 留痕
- test_recover_skips_sweep_when_verdict_pending_or_slot_held: 热停用窗守卫 —— 槽占/verdict
  在队时整段跳过(超龄条目存活不清、零 kick), 既有 verdict 经正常消费链接续(条目清+缓存写)
- test_consume_replay_exception_keeps_rearm_slot: 重放中途异常不丢重武装(槽跃迁判据与
  probing 解耦) —— 重放已 kick 起的在飞探测的槽不被放跑(D3)、条目保留不成孤儿, 新 verdict
  到达后正常续跑, 全程恰一次探测
- test_start_recovers_pending_and_chain_continues: 重启恢复端到端 —— pending 落盘(超龄+新鲜
  两笔) -> 新实例 start 重载(队列空/槽空闲/缓存无 verdict) -> 超龄清扫+审计、队首重 kick ->
  verdict 到达 -> on_task_line 消费链重放续跑建账 setLocation
- test_apply_hot_enable_recovers_pending: 热启用(假->真)同款恢复(与 start 分支口径对称):
  disabled 启动不 kick, apply 热启用后队首重 kick + verdict 到达消费链续跑
"""

import queue

import threading

import types

from auto_qb.config.models import Config, RelocateConfig

from auto_qb.core.modules import relocate_units as ru

from auto_qb.core.modules.relocate_mod import RelocateModule

from auto_qb.core.modules.relocate_probe import (
    PROBE_PENDING_MAX_AGE_S,
    PROBE_RUNNER_CRASHED_REASON,
    ProbeResult,
    ProbeRunner,
    ProbeSingleFlight,
    probe_fingerprint,
)

from clock import wait_until

from helpers import capture_logs, pin_disk_usage, relocate_env

from relocate_exec_support import _spy_spawn

from test_relocate_exec_probe_gate import _env_failed, _fs_failed, _gate_env, _passed


def _wire_async(mod: RelocateModule, probe) -> tuple:
    """独立 runner 注入(与 test_relocate_probe_gate_async._wire_async 同形态): 返回 (queue, slot)"""
    q = queue.Queue()
    slot = ProbeSingleFlight()
    mod._probe_runner = ProbeRunner(queue=q, slot=slot, thread_ctx_factory=lambda c: c, probe_fn=probe)
    return q, slot


def _fp_of(mod: RelocateModule) -> str:
    """当前环境连接身份指纹(与 _ensure_probe 同式: 先保盐再取指纹, 保证与重放重算同键)"""
    return probe_fingerprint(mod._ctx.config.qbittorrent, mod.probe_salt_ensure())


def _recording_probe(calls: list, result=None):
    """替身 probe_fn: 记 (src, dst) 调用并返回 result(缺省 passed —— verdict 随即投递注入队列)"""
    def _probe(ctx, src, dst):
        calls.append({"src": src, "dst": dst})
        return result if result is not None else _passed()

    return _probe


# ---------------------------------------------------------------- 消费四步(D9 原序)


def test_consume_throttle_one_verdict_per_tick(monkeypatch):
    """节流: 两条 verdict 分两 tick 各消费一条(qsize 2->1->0), 各按 D7 处置; 空队列零动作"""
    mod, _locs = _gate_env(monkeypatch)
    calls = []
    q, slot = _wire_async(mod, _recording_probe(calls))
    fp = _fp_of(mod)
    q.put((fp, _passed()))
    q.put((fp, _fs_failed("read_proof_timeout")))
    mod._consume_probe_verdict()
    assert q.qsize() == 1, "每 tick 至多消费一条(节流, D9)"
    assert (mod.probe_get(fp) or {}).get("status") == "passed", "第 1 条按 D7 写 passed"
    mod._consume_probe_verdict()
    assert q.qsize() == 0
    assert (mod.probe_get(fp) or {}).get("status") == "failed", "第 2 条按 D7 写 failed(覆盖写幂等)"
    mod._consume_probe_verdict()  # 空队列: O(1) 跳过
    assert q.qsize() == 0 and mod.probe_pending_list() == () and slot.in_flight() is None
    assert calls == [], "pending 空: 无 kick 无重放"


def test_consume_passed_replays_to_start_job(monkeypatch):
    """重放命中 passed 缓存续跑到 _start_job: 建账 + setLocation + 条目清 + 槽释放(pending 空不 kick)"""
    mod, locs = _gate_env(monkeypatch)
    calls = []
    q, slot = _wire_async(mod, _recording_probe(calls))
    fp = _fp_of(mod)
    mod.probe_pending_append(fp, ["HA", "HB"], "R:/src", "R:/dst", "web")
    slot.try_acquire(fp)  # 自然路径: 槽被本指纹在飞探测占着, verdict 是它的结论
    q.put((fp, _passed()))
    mod._consume_probe_verdict()
    hit = mod.probe_get(fp)
    assert hit is not None and hit["status"] == "passed", "(1) probe_put 写 passed(D7)"
    jobs = mod.active_jobs()
    assert len(jobs) == 1 and jobs[0].phase == ru.PHASE_MOVING, "(2) 重放命中 passed 缓存 -> 闸门放行 -> _start_job"
    assert jobs[0].origin == "web" and jobs[0].dst == "R:/dst", "重放透传条目 origin/dst(D6 意图重放)"
    assert locs and locs[0]["location"] == "R:/dst", "setLocation 已下发(自动续跑)"
    assert mod.probe_pending_list() == (), "(3) 条目已清"
    assert slot.in_flight() is None and calls == [], "(4) 槽已释放; pending 空 -> 不 kick"


def test_consume_fs_failure_cached_and_blocked(monkeypatch):
    """env=False 失败: 缓存写 failed(evidence 补 reason) + 重放命中 failed 缓存 blocked(零建账)"""
    mod, locs = _gate_env(monkeypatch)
    calls = []
    q, slot = _wire_async(mod, _recording_probe(calls))
    fp = _fp_of(mod)
    mod.probe_pending_append(fp, ["HA", "HB"], "R:/src", "R:/dst", "web")
    slot.try_acquire(fp)
    q.put((fp, _fs_failed("read_proof_timeout")))
    mod._consume_probe_verdict()
    hit = mod.probe_get(fp)
    assert hit is not None and hit["status"] == "failed", "D7 1: FS 不可达方向写缓存"
    assert (hit.get("evidence") or {}).get("reason") == "read_proof_timeout", "evidence 补 reason(与内联收尾同形)"
    assert mod.active_jobs() == () and locs == [], "重放命中 failed 缓存 blocked: 零建账零 setLocation"
    assert mod.probe_pending_list() == () and slot.in_flight() is None, "条目清 + 槽释放"


def test_consume_env_failure_terminates_without_loop(monkeypatch):
    """防自环: env=True 失败 -> 重放走 T2 天然路径返回探测中回执 -> 条目丢弃终止自动链不循环"""
    mod, _locs = _gate_env(monkeypatch)
    calls = []
    q, slot = _wire_async(mod, _recording_probe(calls))
    fp = _fp_of(mod)
    mod.probe_pending_append(fp, ["HA", "HB"], "R:/src", "R:/dst", "web")
    slot.try_acquire(fp)  # 槽仍被本指纹占(重放未到释放槽) —— try_start 必 False 的天然前提
    q.put((fp, _env_failed("add_rejected")))
    mod._consume_probe_verdict()
    assert mod.probe_get(fp) is None, "D7 2: env=True 不写缓存(下次真实触发重试)"
    assert mod.probe_pending_list() == (), "防自环: 条目被清(丢弃终止自动链)"
    assert slot.in_flight() is None, "槽已释放(本探测已完结, 释放归消费面)"
    assert q.qsize() == 0, "队列无新 verdict(不再重放)"
    assert calls == [], "替身 probe 零调用: 不再 kick 本指纹(自动链终止)"
    assert mod.active_jobs() == (), "自动链终止: 零建账"


def test_consume_release_then_kick_next_order(monkeypatch):
    """次序钉死 = 清条目 -> 释放槽 -> kick 下一条; kick 恰一次指向等位条目; 重放走缓存不触 try_start"""
    mod, locs = _gate_env(monkeypatch)
    calls = []
    q, slot = _wire_async(mod, _recording_probe(calls))
    fp = _fp_of(mod)
    mod.probe_pending_append(fp, ["HA", "HB"], "R:/src", "R:/dst", "web")
    mod.probe_pending_append(fp, ["HA", "HB"], "R:/src", "R:/dst2", "web")  # 异意图等位队尾(同指纹)
    events = []
    real_pop, real_release, real_try = mod.probe_pending_pop, slot.release, mod._probe_runner.try_start
    monkeypatch.setattr(mod, "probe_pending_pop", lambda: events.append("pop") or real_pop())
    monkeypatch.setattr(slot, "release", lambda: events.append("release") or real_release())

    def _spy_try(ctx, fingerprint, src, dst):
        events.append(("kick", src, dst))
        return real_try(ctx, fingerprint, src, dst)

    monkeypatch.setattr(mod._probe_runner, "try_start", _spy_try)
    slot.try_acquire(fp)
    q.put((fp, _passed()))
    mod._consume_probe_verdict()
    assert events[0] == "pop" and events[1] == "release", f"次序 = 清条目 -> 释放槽 -> kick: {events}"
    assert events[2] == ("kick", "R:/src", "R:/dst2"), f"kick 下一条取队首条目 (fingerprint, src, dst): {events}"
    assert len(events) == 3, f"重放走缓存不触 try_start, kick 恰一次: {events}"
    assert locs and locs[0]["location"] == "R:/dst", "队首条目重放续跑建账(setLocation)"
    assert wait_until(lambda: len(calls) == 1), "kick 下一条起了探测线程"
    assert calls == [{"src": "R:/src", "dst": "R:/dst2"}], calls
    assert slot.in_flight() == fp, "kick 占槽(单飞续跑)"
    assert mod.probe_pending_list()[0]["dst"] == "R:/dst2", "等位条目原位等待自己的 verdict"


def test_consume_fingerprint_mismatch_defense(monkeypatch):
    """verdict 指纹与队首不一致: 不重放防错位、条目保留、按 D7 写缓存、槽释放后队首重 kick 自愈"""
    mod, _locs = _gate_env(monkeypatch)
    calls = []
    q, slot = _wire_async(mod, _recording_probe(calls))
    fp_head = _fp_of(mod)
    mod.probe_pending_append(fp_head, ["HA", "HB"], "R:/src", "R:/dst", "web")  # 队首孤儿(它的 verdict 已丢)
    fp_v = "foreign-fingerprint"  # verdict 指纹与队首不一致(desync 形态)
    slot.try_acquire(fp_v)  # 槽被本 verdict 的探测占着(它已完结)
    q.put((fp_v, _passed()))
    mod._consume_probe_verdict()
    assert (mod.probe_get(fp_v) or {}).get("status") == "passed", "缓存按 verdict 指纹写(D7, 结论真实)"
    entries = mod.probe_pending_list()
    assert len(entries) == 1 and entries[0]["fingerprint"] == fp_head, "队首条目原样保留(不重放防错位)"
    assert mod.active_jobs() == (), "异指纹 verdict 不续跑队首意图(零建账)"
    assert wait_until(lambda: len(calls) == 1), "槽释放后队首孤儿意图被重 kick(自愈: 重新探测)"
    assert calls == [{"src": "R:/src", "dst": "R:/dst"}], calls
    assert slot.in_flight() == fp_head, "kick 占槽: head==in-flight 不变量恢复"


def test_consume_rearm_keeps_entry_when_replay_restarts_probe(monkeypatch):
    """重武装: 槽空闲时消费 runner_crashed verdict, 重放的 try_start 重起真探测 —— 条目保留续跑"""
    mod, _locs = _gate_env(monkeypatch)
    calls = []
    q, slot = _wire_async(mod, _recording_probe(calls))
    fp = _fp_of(mod)
    mod.probe_pending_append(fp, ["HA", "HB"], "R:/src", "R:/dst", "web")
    crash = ProbeResult("failed", PROBE_RUNNER_CRASHED_REASON, True, {"method": "e1", "error": "boom"})
    q.put((fp, crash))  # 线程启动失败形态: 槽空闲(启动失败路径已释放) + 合成 verdict 在队
    mod._consume_probe_verdict()
    entries = mod.probe_pending_list()
    assert len(entries) == 1 and entries[0]["fingerprint"] == fp, "重武装: 条目保留(重放重起了探测)"
    assert slot.in_flight() == fp, "新探测占槽(不释放, 待它的 verdict 正常消费)"
    assert mod.probe_get(fp) is None, "runner_crashed env=True 不写缓存"
    assert wait_until(lambda: q.qsize() == 1 and len(calls) == 1), "重放重起了探测线程且 verdict 到达"
    assert calls == [{"src": "R:/src", "dst": "R:/dst"}], calls
    mod._consume_probe_verdict()  # 第二拍: 新 verdict 走正常消费链
    assert (mod.probe_get(fp) or {}).get("status") == "passed", "新 verdict 按 D7 写缓存"
    assert mod.probe_pending_list() == () and len(mod.active_jobs()) == 1, "重放命中缓存 -> _start_job 续跑"
    assert slot.in_flight() is None and len(calls) == 1, "槽释放(pending 空不 kick), 无第二次探测"


def test_on_task_line_consumes_verdict_before_stepping(monkeypatch):
    """D9 挂点: on_task_line 先消费(条目清/缓存写/建账)后步进; 空队列二拍相位推进照常"""
    mod, locs = _gate_env(monkeypatch)
    calls = []
    q, slot = _wire_async(mod, _recording_probe(calls))
    fp = _fp_of(mod)
    mod.probe_pending_append(fp, ["HA", "HB"], "R:/src", "R:/dst", "rule")
    slot.try_acquire(fp)
    q.put((fp, _passed()))
    mod.on_task_line()
    assert mod.probe_pending_list() == () and (mod.probe_get(fp) or {}).get("status") == "passed"
    assert len(mod.active_jobs()) == 1 and locs, "消费先于步进: 一拍内条目清/缓存写/job 建立"
    # 空队列二拍: 消费面 O(1) 跳过, 既有相位推进照常 —— 强制采样窗到期, 二拍后采样点被更新
    jid = mod.active_jobs()[0].job_id
    mod._rt[jid]["sample_ts"] = 0.0
    mod.on_task_line()
    assert mod._rt[jid]["sample_ts"] > 0, "空队列二拍: 既有相位推进照常(_step_move 采样点已更新)"
    assert len(mod.active_jobs()) == 1 and mod.probe_pending_list() == () and q.qsize() == 0


# ---------------------------------------------------------------- 启动恢复(D7 + 超龄兜底)


def test_recover_sweeps_stale_keeps_fresh(fake_clock, monkeypatch):
    """超龄清扫(假钟): >120s 与坏 ts 条目清且审计留痕, <=120s 边界保留; 清扫后队首重 kick; 槽被占时守卫跳过"""
    mod = RelocateModule(clock=fake_clock)
    mod._ctx = types.SimpleNamespace(state=types.SimpleNamespace(data={}))
    calls = []
    q, slot = _wire_async(mod, _recording_probe(calls))
    mod.probe_pending_append("fpOld", ["HA"], "R:/s1", "R:/d1", "web")
    fake_clock.advance(PROBE_PENDING_MAX_AGE_S + 1.0)  # 首条年龄 121s(超龄)
    mod.probe_pending_append("fpNew", ["HB"], "R:/s2", "R:/d2", "rule")
    fake_clock.advance(PROBE_PENDING_MAX_AGE_S - 1.0)  # 次条年龄 119s(边界内保留)
    mod._ctx.state.data["relocate"]["probe_pending"].append({"fingerprint": "fpBad"})  # 坏 ts 条目
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod._probe_pending_recover()
    entries = mod.probe_pending_list()
    assert [e["fingerprint"] for e in entries] == ["fpNew"], "超龄(121s)与坏 ts 条目清, 119s 边界内保留"
    swept = [m for m in cap.messages if "启动清扫" in m]
    assert len(swept) == 1 and "2 条" in swept[0] and "fpOld" in swept[0], "审计留痕: 条数(含坏 ts 条目) + 指纹"
    assert wait_until(lambda: len(calls) == 1), "队首重 kick 探测(D7 重启恢复)"
    assert calls == [{"src": "R:/s2", "dst": "R:/d2"}], calls
    assert slot.in_flight() == "fpNew", "kick 占槽"
    # 边界补拍: 恰 120s(<= 超龄线)不清; 槽被占 -> 热停用窗守卫整段跳过(零清扫零 kick)
    fake_clock.advance(1.0)  # fpNew 年龄 119 -> 120s
    calls2 = []
    mod2 = RelocateModule(clock=fake_clock)
    mod2._ctx = types.SimpleNamespace(state=mod._ctx.state)
    _q2, slot2 = _wire_async(mod2, _recording_probe(calls2))
    slot2.try_acquire("other-fp")  # 槽被异指纹占: 守卫命中, 整段跳过
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap2:
        mod2._probe_pending_recover()
    assert calls2 == [], "槽被占: 守卫跳过, 零 kick"
    assert any("跳过超龄清扫" in m for m in cap2.messages), "守卫留痕"
    assert not [m for m in cap2.messages if "启动清扫" in m], "清扫被跳过(不动条目)"
    assert [e["fingerprint"] for e in mod2.probe_pending_list()] == ["fpNew"], "恰 120s(<=)不清"


def test_recover_skips_sweep_when_verdict_pending_or_slot_held(fake_clock):
    """热停用窗守卫(评审 fix1): 槽占/verdict 在队时整段跳过 —— 超龄条目存活不清(否则 verdict
    变孤儿、迁移意图静默丢失), 既有 verdict 经正常消费链接续(条目清 + 缓存写)"""
    mod = RelocateModule(clock=fake_clock)
    mod._ctx = types.SimpleNamespace(
        state=types.SimpleNamespace(data={}),
        config=types.SimpleNamespace(relocate=RelocateConfig(enabled=True)),
        store=None,  # 消费链接续面: relocate_execute 按 unavailable blocked 收口(条目照常清)
        api=None,
    )
    calls = []
    q, slot = _wire_async(mod, _recording_probe(calls))
    fp = "fpHot"
    mod.probe_pending_append(fp, ["HA"], "R:/s1", "R:/d1", "web")
    fake_clock.advance(PROBE_PENDING_MAX_AGE_S + 30.0)  # 热停用窗内条目 ts 老化到超龄
    slot.try_acquire(fp)  # 槽被占(热停用窗: on_task_line 因 conf 闸停消费, 槽冻结)
    q.put((fp, _passed()))  # verdict 已入队未消费
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod._probe_pending_recover()
    entries = mod.probe_pending_list()
    assert len(entries) == 1 and entries[0]["fingerprint"] == fp, "verdict 在途: 超龄条目不清(意图不丢)"
    assert not [m for m in cap.messages if "启动清扫" in m], "清扫被跳过"
    assert any("跳过超龄清扫" in m for m in cap.messages), "守卫留痕"
    assert calls == [], "零 kick(交由既有 verdict 的消费链接续)"
    mod._consume_probe_verdict()  # 既有 verdict 的正常消费链接续
    assert mod.probe_pending_list() == () and (mod.probe_get(fp) or {}).get("status") == "passed"
    assert slot.in_flight() is None, "消费面释放槽(pending 空, 无 kick)"


def test_consume_replay_exception_keeps_rearm_slot(monkeypatch):
    """重放中途异常不丢重武装(评审 fix2, 槽跃迁判据与 probing 解耦): 重放内部已 kick 起探测后
    才抛异常 —— 槽不放跑(D3 单飞不破)、条目保留不成孤儿, 新 verdict 到达后正常续跑"""
    mod, _locs = _gate_env(monkeypatch)
    calls = []
    q, slot = _wire_async(mod, _recording_probe(calls))
    fp = _fp_of(mod)
    mod.probe_pending_append(fp, ["HA", "HB"], "R:/src", "R:/dst", "web")

    def _boom(items):
        raise RuntimeError("replay 中途故障(组2 形态)")

    monkeypatch.setattr(mod, "_summ", _boom)  # relocate_execute 尾部汇总位抛异常 = kick 之后的故障点
    crash = ProbeResult("failed", PROBE_RUNNER_CRASHED_REASON, True, {"method": "e1", "error": "boom"})
    q.put((fp, crash))  # 槽空闲(线程启动失败形态: 槽已释放 + 合成 verdict 在队)
    mod._consume_probe_verdict()  # 重放: 闸未命中 -> try_start 重起探测 -> _summ 抛异常
    entries = mod.probe_pending_list()
    assert len(entries) == 1 and entries[0]["fingerprint"] == fp, "重放异常不丢重武装: 条目保留(意图不成孤儿)"
    assert slot.in_flight() == fp, "重放刚 kick 起的在飞探测的槽未被放跑(D3 单飞不破)"
    assert wait_until(lambda: q.qsize() == 1 and len(calls) == 1), "重放重起的探测 verdict 到达"
    mod._consume_probe_verdict()  # 第二拍: 新 verdict 走正常消费链
    assert (mod.probe_get(fp) or {}).get("status") == "passed", "新 verdict 按 D7 写缓存"
    assert len(mod.active_jobs()) == 1, "新 verdict 到达后正常续跑(_start_job 建账)"
    assert mod.probe_pending_list() == () and slot.in_flight() is None, "条目清 + 槽释放"
    assert len(calls) == 1, "全程恰一次探测(无双探测并发)"


def test_start_recovers_pending_and_chain_continues(tmp_path, monkeypatch, fake_clock):
    """重启恢复端到端: pending 落盘 -> 新实例 start 重载 -> 超龄清扫+队首重 kick -> verdict 到达
    消费链重放续跑建账(队列空/槽空闲/缓存无 verdict 的重启前提)"""
    pin_disk_usage(monkeypatch)
    mgr, _client, src, dst, _content, _files = relocate_env(tmp_path, state="pausedUP", clock=fake_clock)
    mod1 = mgr.host.get("relocate")
    _spy_spawn(mod1, [])
    fp = probe_fingerprint(mgr.config.qbittorrent, mod1.probe_salt_ensure())
    mod1.probe_pending_append(fp, ["HA", "HB"], src, dst + "-never", "web")  # 队首: 超龄孤儿
    fake_clock.advance(PROBE_PENDING_MAX_AGE_S + 5.0)
    mod1.probe_pending_append(fp, ["HA", "HB"], src, dst, "rule")  # 新鲜: 恢复对象
    # 进程重启: 全新实例共享 state(结果队列必空、单飞槽必空闲、缓存无本批 verdict)
    mod2 = RelocateModule(mgr.ctx, clock=fake_clock)
    calls = []
    q, slot = _wire_async(mod2, _recording_probe(calls))
    mod2._spawn_daemon = lambda *a, **k: None
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod2.start(mgr.ctx, dry_run=False)
    swept = [m for m in cap.messages if "启动清扫" in m]
    assert len(swept) == 1 and "1 条" in swept[0] and dst + "-never" in swept[0], "超龄条目启动清扫留痕"
    assert [e["dst"] for e in mod2.probe_pending_list()] == [dst], "超龄条目清, 新鲜条目保留"
    assert wait_until(lambda: len(calls) == 1), "start 恢复: 队首意图重 kick 探测"
    assert calls == [{"src": src, "dst": dst}], calls
    assert slot.in_flight() == fp, "kick 占槽"
    assert wait_until(lambda: q.qsize() == 1), "verdict 到达(替身 passed 投递)"
    mod2.on_task_line()
    jobs = mod2.active_jobs()
    assert len(jobs) == 1 and jobs[0].dst == dst and jobs[0].phase == ru.PHASE_MOVING, "消费链重放续跑建账"
    assert (mod2.probe_get(fp) or {}).get("status") == "passed", "verdict 按 D7 写缓存"
    assert mod2.probe_pending_list() == () and slot.in_flight() is None, "条目清 + 槽释放"


def test_apply_hot_enable_recovers_pending(tmp_path, monkeypatch, fake_clock):
    """热启用(假->真)同款恢复(与 start 分支口径对称): disabled 启动不 kick, apply 后重 kick 续跑"""
    pin_disk_usage(monkeypatch)
    mgr, _client, src, dst, _content, _files = relocate_env(tmp_path, state="pausedUP", clock=fake_clock)
    mgr.config.relocate = RelocateConfig(enabled=False)
    mod1 = mgr.host.get("relocate")
    fp = probe_fingerprint(mgr.config.qbittorrent, mod1.probe_salt_ensure())
    mod1.probe_pending_append(fp, ["HA", "HB"], src, dst, "web")
    mod2 = RelocateModule(mgr.ctx, clock=fake_clock)
    calls = []
    q, slot = _wire_async(mod2, _recording_probe(calls))
    mod2._spawn_daemon = lambda *a, **k: None
    mod2.start(mgr.ctx, dry_run=False)
    assert calls == [] and len(mod2.probe_pending_list()) == 1, "disabled 启动: 零动作(R15), 条目原样"
    old, new = Config(), Config()
    new.relocate = RelocateConfig(enabled=True, bt_backup=str(tmp_path))
    res = mod2.apply(old, new)
    assert res.action == "reloaded", res
    assert wait_until(lambda: len(calls) == 1), "热启用恢复: 队首意图重 kick 探测"
    assert calls == [{"src": src, "dst": dst}], calls
    assert slot.in_flight() == fp
    mgr.config.relocate = new.relocate  # 内核在调 apply 前换 ctx.config(测试面同形补齐)
    assert wait_until(lambda: q.qsize() == 1), "verdict 到达(替身 passed 投递)"
    mod2.on_task_line()
    jobs = mod2.active_jobs()
    assert len(jobs) == 1 and jobs[0].dst == dst, "verdict 到达: 消费链重放续跑建账"
    assert mod2.probe_pending_list() == () and slot.in_flight() is None
