"""test_relocate_probe_gate_async 测试计划: 探测闸未命中分支异步化(S2, 计划 26-11-10-2350
§03 落点段「_ensure_probe 改造」/ §04 S2 / §06 D1-D10, 并轨 26-11-15-2340 刀4)——
意图入队 + 单飞 kick + 「探测中」gate 回执 + 同步语义注入内联保留。

环境复用 test_relocate_exec_probe_gate._gate_env(多成员组 + 证据不可判定的最小执行面,
探测闸必然消费未命中分支); 异步用例经 mod._probe_runner 注入独立 ProbeRunner(独立结果
队列/独立单飞槽/透传 factory/替身 probe_fn)隔离全局单例(T1 测试口径), 时序确定性靠
替身 probe_fn 的 event 门(线程在 release 前持槽不退场)。

「探测中」回执形态(S2 钉死, 2350 §05 实现细节非用户决策面): cls 仍 "blocked"(与
evaluate_group blocked item 同形, 走 blocked 通道 —— 本轮零建账零 setLocation, D5 位置
契约不破), item[PROBE_GATE_PROBING_KEY] is True 为机器判别键(reasons 元素 gate/cls/text
同形, gate=same_fs), notes 追加「同机探测已入队」。F5(计划 26-11-22-1714 D8)起 blocked
text 与 note 各补预告「续跑重新过全闸链, 出现需确认态会再次询问(不代用户点头)」—— 重放
不带 confirm 位是安全设计, 行为不改只改回执文案。T3 重放防自环/T4 web 两段回执按
该键分流; 与闸内其余 blocked(缓存 failed / env=True 失败 / qb_conf 缺失, 均无此键)可区分。

## 测试计划(每个测试函数一条)
- test_probe_miss_enqueues_intent_and_kicks_delivers_verdict: 未命中 => 意图条目落 state
  (六键/全组成员/origin 透传)+ kick(槽受理 in_flight=指纹 + 探测线程恰 1 个)+「探测中」
  回执且零建账零 setLocation(D5); 释放替身后 verdict (指纹, 结论) 原样进注入队列
  (生产由 T3 消费, 此处只验交付面), 线程 daemon 自然退场
- test_probe_miss_same_intent_merges_hashes_without_second_kick: 同指纹同源同目标的再次
  到达(组扩员后重发) => hashes 去重并入既有条目(队列仍 1 条, 不重复入队), 槽仍被首个
  在飞请求持有(无第二线程不抢槽), 再发一次纯重复也零增量
- test_probe_miss_other_intent_appends_to_waiting_tail: 同指纹异目标(另一迁移意图) =>
  独立条目追加等位队尾(FIFO 序), 异意图绝不合并(合并会吞掉后来条目的目标, 重放错位),
  槽被占不 kick
- test_probe_miss_other_fingerprint_appends_and_waits: 异指纹(qB 连接配置变更) =>
  独立条目按指纹追加等位队尾, 槽仍被首个指纹持有(单飞互斥), 无第二线程
- test_probe_slot_busy_blocks_kick_and_keeps_slot_untouched: 槽被异指纹预先占用 => 第一条
  请求也只入队等位(条目落 state), 槽不被抢(in_flight 保持占位者), 替身 probe 零调用
  (不起探针线程), 回执与 kick 成功情形同形(不以 kick 结果区分)
- test_probe_receipt_key_distinguishes_probing_from_other_blocked: 可区分性四面: 异步
  「探测中」带 PROBE_GATE_PROBING_KEY=True; 内联 env=True 失败 blocked 无键; 内联缓存
  failed blocked 无键; qb_conf 缺失 blocked 无键(直测 _ensure_probe, 该分支先于未命中)
- test_probe_inline_seam_keeps_sync_semantics_default_async: 注入 seam 双面钉死: 类属性
  缺省 _probe_inline=False/_probe_runner=None(生产异步零布线); _stub_run_probe 形态
  (类级开内联 + monkeypatch rex.run_probe)下 relocate_execute 同步 started/建账/
  setLocation, pending 恒空(内联不入队), 全局单飞槽与结果队列零触碰(run_inline 解耦)
- test_probe_pending_merge_intent_matches_normalized_triple_only: 容器面 merge_intent:
  三元组归一匹配(斜杠归一, 大小写不折叠)才合并且条目真身存原文; 异目标/异指纹/异源/
  大小写变体一律 False 零动手; 字符串 hashes 按单 hash 容错

## 既有用例处置表(2350 §07「既有测试语义漂移」行: 任何用例语义变化必须逐条说明)

S2 异步化后既有用例**零改写零断言变更**, 全部原样绿: 替身 helper 加一行类级内联开关
(`monkeypatch.setattr(rex.ExecMixin, "_probe_inline", True)`), 走未命中分支的用例经
run_inline 同步拿 verdict 走原收尾三态, 其余分支本就不经未命中。逐条证据如下。

tests/test_relocate_exec_probe_gate.py 10 条(替身面 = _stub_run_probe):

- test_first_multi_member_migration_probes_then_starts: 未改动, 经 _stub_run_probe 类级内联开关保同步语义(未命中分支, run_inline passed 原收尾)
- test_probe_fs_unreachable_blocks_without_job_or_setlocation: 未改动, 经 _stub_run_probe 类级内联开关保同步语义(未命中分支, env=False 原收尾)
- test_second_migration_hits_failed_cache_without_reprobe: 未改动, 经 _stub_run_probe 类级内联开关保同步语义(缓存 failed 命中分支, 不经未命中)
- test_env_failure_not_cached_and_retried_next_time: 未改动, 经 _stub_run_probe 类级内联开关保同步语义(未命中分支, env=True 原收尾, 两次迁移)
- test_cached_passed_hits_with_zero_probe_calls: 未改动, 经 _stub_run_probe 类级内联开关保同步语义(缓存 passed 命中 + same_fs_proved 短路, 不经未命中)
- test_gate_cached_passed_direct_hit_appends_note: 未改动, 经 _stub_run_probe 类级内联开关保同步语义(缓存 passed 直读命中, 不经未命中)
- test_single_member_assume_shared_and_dry_run_skip_probe: 未改动, 经 _stub_run_probe 类级内联开关保同步语义(单成员/assume_shared/dry-run 三面短路, 不经未命中)
- test_missing_qb_config_blocks_without_caching: 未改动, 经 _stub_run_probe 类级内联开关保同步语义(qb_conf 缺失短路分支, 直测 _ensure_probe, 先于未命中)
- test_fingerprint_change_reprobes: 未改动, 经 _stub_run_probe 类级内联开关保同步语义(未命中分支 x2, run_inline passed 原收尾)
- test_weak_positive_still_probes_and_strong_d_positive_skips: 未改动, 经 _stub_run_probe 类级内联开关保同步语义(未命中分支 x3 内联 + D 级 positive 短路 x1)

tests/relocate_exec_support.py 消费面 10 文件(替身面 = _stub_probe_pass, 直接调用或经
同文件 _armed_env 转介; 用例本体零改动):

- test_relocate_exec_run.py: 未改动, 经 _stub_probe_pass 内联开关保同步语义(autouse 夹具 _exec_probe_pass; 用例内 :976 自设 run_probe 桩晚于夹具生效不受影响)
- test_relocate_exec_jobs.py: 未改动, 经 _stub_probe_pass 内联开关保同步语义(autouse 夹具直调 x1 + _armed_env 转介 x4)
- test_relocate_exec_misc.py: 未改动, 经 _stub_probe_pass 内联开关保同步语义(autouse 夹具直调 x1)
- test_relocate_paths.py: 未改动, 经 _stub_probe_pass 内联开关保同步语义(autouse 夹具 _exec_probe_pass 直调 x1)
- test_relocate_tag_mirror.py: 未改动, 经 _stub_probe_pass 内联开关保同步语义(用例级直调 x2)
- test_relocate_resume_confirm.py: 未改动, 经 _stub_probe_pass 内联开关保同步语义(用例级直调 x5)
- test_relocate_startup_reconcile.py: 未改动, 经 _stub_probe_pass 内联开关保同步语义(用例级直调 x2)
- test_relocate_supersede.py: 未改动, 经 _stub_probe_pass 内联开关保同步语义(_armed_env 转介 x21 + 用例级直调 x1, 合计 22)
- test_relocate_exec_reconcile.py: 未改动, 经 _stub_probe_pass 内联开关保同步语义(_armed_env 转介 x1)
- test_web_relocate.py: 未改动, 经 _stub_probe_pass 内联开关保同步语义(用例级直调 x1, 撤销链面)
"""

import queue
import threading
import types

from auto_qb.config.models import RelocateConfig

from auto_qb.core.modules import relocate_exec as rex

from auto_qb.core.modules import relocate_units as ru

from auto_qb.core.modules.relocate_mod import RelocateModule

from auto_qb.core.modules.relocate_probe import (
    PROBE_SLOT,
    PROBE_VERDICT_QUEUE,
    ProbeResult,
    ProbeRunner,
    ProbeSingleFlight,
    probe_fingerprint,
)

from clock import wait_until

from test_relocate_exec_probe_gate import _env_failed, _fs_failed, _gate_env, _passed, _stub_run_probe


def _wire_async(mod: RelocateModule, probe) -> tuple:
    """异步形态 + 全替身协作面: 注入独立 runner(独立结果队列/单飞槽/透传 factory/替身 probe_fn)

    返回 (queue, slot) 断言面; 缺省 _probe_inline=False(类属性)下 _ensure_probe 未命中
    分支走 try_start —— 线程体 = 透传 factory(单测 ctx 不重建) + 替身 probe_fn。
    """
    q = queue.Queue()
    slot = ProbeSingleFlight()
    mod._probe_runner = ProbeRunner(queue=q, slot=slot, thread_ctx_factory=lambda c: c, probe_fn=probe)
    return q, slot


def _probe_threads(pre: set) -> list:
    """本用例新起的探针线程(按名差集过滤其它用例的退场窗残留, T1 先例)"""
    return [t for t in threading.enumerate() if t.name == "relocate-probe" and t not in pre]


def _gated_probe(gate_ev: threading.Event, release: threading.Event, calls: list):
    """确定性时序替身 probe_fn: 记调用、置 gate、持 release 门直到放行(线程期内槽保持被占)"""
    def _probe(ctx, src, dst):
        calls.append({"src": src, "dst": dst})
        gate_ev.set()
        release.wait(10)
        return _passed()

    return _probe


def _silent_probe(calls: list):
    """不应被调用的替身 probe_fn: 一旦被调立即记下并放行(断言面用 calls == [])"""
    def _probe(ctx, src, dst):
        calls.append({"src": src, "dst": dst})
        return _passed()

    return _probe


def test_probe_miss_enqueues_intent_and_kicks_delivers_verdict(monkeypatch):
    """未命中 => 意图入队 + kick + 「探测中」回执(零建账零 setLocation); 释放后 verdict 进队列"""
    mod, locs = _gate_env(monkeypatch)
    gate_ev, release, calls = threading.Event(), threading.Event(), []
    q, slot = _wire_async(mod, _gated_probe(gate_ev, release, calls))
    pre = set(threading.enumerate())
    items = mod.relocate_execute(["HA"], "R:/dst", origin="web")
    it = items[0]
    # 「探测中」回执形态: 与 evaluate_group blocked item 同形 + 机器判别键 + note
    assert it["cls"] == "blocked", it
    assert it[ru.PROBE_GATE_PROBING_KEY] is True, it
    assert it["reasons"][-1]["gate"] == "same_fs" and it["reasons"][-1]["cls"] == "blocked", it["reasons"]
    assert "同机探测已入队" in it["reasons"][-1]["text"], it["reasons"]
    # F5(计划 26-11-22-1714 D8): 回执补预告 —— 重放重新过全闸链, 需确认态会再次询问
    # (重放不带 confirm 位是安全设计, 行为不改只改文案; blocked text 与 note 两处都在)
    assert "续跑重新过全闸链" in it["reasons"][-1]["text"] and "不代用户点头" in it["reasons"][-1]["text"], it["reasons"]
    assert any("同机探测已入队" in n for n in it["notes"]), it["notes"]
    assert any("续跑重新过全闸链" in n and "不代用户点头" in n for n in it["notes"]), it["notes"]
    assert it["target"] == "R:/dst" and it["hashes"] == ["HA", "HB"], f"verdict 形态随散展开带出: {it}"
    # D5 位置契约: 「探测中」回执走 blocked 通道, 本轮零建账零 setLocation
    assert "job_id" not in it, it
    assert not mod.active_jobs() and locs == [], (mod.active_jobs(), locs)
    # 意图入队: 条目六键面 + 全组成员 + src/dst/origin 透传
    fp = probe_fingerprint(mod._ctx.config.qbittorrent, mod.probe_salt())
    entries = mod.probe_pending_list()
    assert len(entries) == 1, entries
    e = entries[0]
    assert list(e) == ["fingerprint", "hashes", "src", "dst", "origin", "ts"], e
    assert e["fingerprint"] == fp and e["hashes"] == ["HA", "HB"] and e["origin"] == "web", e
    assert e["src"] == "R:/src" and e["dst"] == "R:/dst", e
    # kick: 单飞槽受理 + 探测线程恰 1 个(替身 probe 经透传 factory 收到原 ctx)
    assert slot.busy() is True and slot.in_flight() == fp, slot.in_flight()
    assert wait_until(lambda: len(_probe_threads(pre)) == 1), "kick 必须起探针线程"
    assert gate_ev.wait(5) and calls == [{"src": "R:/src", "dst": "R:/dst"}], calls
    threads = _probe_threads(pre)  # 释放前抓线程引用(release 后线程即刻退场, enumerate 不再可见)
    # 兑现: 释放替身 -> verdict (指纹, 结论) 原样进注入队列(生产由 T3 消费, 此处验交付面)
    release.set()
    got_fp, verdict = q.get(timeout=10)
    assert got_fp == fp and isinstance(verdict, ProbeResult) and verdict.status == "passed", (got_fp, verdict)
    threads[0].join(timeout=5)
    assert not threads[0].is_alive() and threads[0].daemon, "daemon 线程自然退场(D4: 优雅退出不 join)"
    slot.release()


def test_probe_miss_same_intent_merges_hashes_without_second_kick(monkeypatch):
    """同指纹同源同目标再次到达 => hashes 去重并入既有条目; 槽不抢不重复 kick"""
    mod, locs = _gate_env(monkeypatch)
    gate_ev, release, calls = threading.Event(), threading.Event(), []
    q, slot = _wire_async(mod, _gated_probe(gate_ev, release, calls))
    pre = set(threading.enumerate())
    assert mod.relocate_execute(["HA"], "R:/dst")[0][ru.PROBE_GATE_PROBING_KEY] is True
    assert wait_until(lambda: len(_probe_threads(pre)) == 1)
    fp = slot.in_flight()
    # 组扩员(HC 入组)后再发同一目标: 同一迁移意图的再次到达(规则 move_to 每轮重复发起形态)
    mod._ctx.store.by_hash["HC"] = types.SimpleNamespace(
        hash="HC",
        save_path="R:/src",
        name="Show",
        log_repr="HC",
        progress=1.0,
        state="pausedUP",
        state_enum=None,
        files=lambda c: mod._ctx.store.by_hash["HA"].files(c),
    )
    key = next(iter(mod._ctx.store.groups))
    mod._ctx.store.groups[key] = ["HA", "HB", "HC"]
    second = mod.relocate_execute(["HA"], "R:/dst")
    assert second[0][ru.PROBE_GATE_PROBING_KEY] is True and second[0]["cls"] == "blocked", second
    entries = mod.probe_pending_list()
    assert len(entries) == 1, f"同意图合并: 不重复入队 {entries}"
    assert entries[0]["hashes"] == ["HA", "HB", "HC"], entries
    assert entries[0]["dst"] == "R:/dst", f"条目 src/dst 保持首达原文 {entries}"
    # 纯重复再发(成员面不变): 合并去重零增量
    assert mod.relocate_execute(["HA"], "R:/dst")[0][ru.PROBE_GATE_PROBING_KEY] is True
    assert mod.probe_pending_list()[0]["hashes"] == ["HA", "HB", "HC"], "重复 hashes 去重, 不叠加"
    # 单飞互斥: 槽仍被首个在飞请求持有, 无第二线程(第二请求等位, try_start False)
    assert slot.in_flight() == fp, slot.in_flight()
    assert len(_probe_threads(pre)) == 1, "同指纹合并不得二次 kick"
    threads = _probe_threads(pre)
    release.set()
    q.get(timeout=10)
    threads[0].join(timeout=5)
    assert not threads[0].is_alive()
    slot.release()


def test_probe_miss_other_intent_appends_to_waiting_tail(monkeypatch):
    """同指纹异目标(另一迁移意图) => 独立条目追加等位队尾, 不合并不 kick"""
    mod, locs = _gate_env(monkeypatch)
    gate_ev, release, calls = threading.Event(), threading.Event(), []
    q, slot = _wire_async(mod, _gated_probe(gate_ev, release, calls))
    pre = set(threading.enumerate())
    assert mod.relocate_execute(["HA"], "R:/dst")[0][ru.PROBE_GATE_PROBING_KEY] is True
    assert wait_until(lambda: len(_probe_threads(pre)) == 1)
    fp = slot.in_flight()
    # 同指纹(同一 qB 连接)异目标: 异意图追加等位队尾 —— 合并会吞掉后来条目的 dst, 重放错位
    second = mod.relocate_execute(["HA"], "R:/dst2")
    assert second[0][ru.PROBE_GATE_PROBING_KEY] is True and second[0]["cls"] == "blocked", second
    entries = mod.probe_pending_list()
    assert [e["dst"] for e in entries] == ["R:/dst", "R:/dst2"], f"异意图追加队尾(FIFO 序) {entries}"
    assert [e["hashes"] for e in entries] == [["HA", "HB"], ["HA", "HB"]], f"异意图不并 hashes {entries}"
    assert all(e["fingerprint"] == fp for e in entries), entries
    assert len(_probe_threads(pre)) == 1 and slot.in_flight() == fp, "槽被占: 不 kick 不抢槽"
    threads = _probe_threads(pre)
    release.set()
    q.get(timeout=10)
    threads[0].join(timeout=5)
    assert not threads[0].is_alive()
    slot.release()


def test_probe_miss_other_fingerprint_appends_and_waits(monkeypatch):
    """异指纹(qB 连接配置变更) => 独立条目按指纹追加等位队尾; 单飞互斥槽不换手"""
    mod, locs = _gate_env(monkeypatch)
    gate_ev, release, calls = threading.Event(), threading.Event(), []
    q, slot = _wire_async(mod, _gated_probe(gate_ev, release, calls))
    pre = set(threading.enumerate())
    assert mod.relocate_execute(["HA"], "R:/dst")[0][ru.PROBE_GATE_PROBING_KEY] is True
    assert wait_until(lambda: len(_probe_threads(pre)) == 1)
    fp1 = slot.in_flight()
    mod._ctx.config.qbittorrent = types.SimpleNamespace(
        host="127.0.0.1", port=8081, username="", password="", api_key=""
    )
    second = mod.relocate_execute(["HA"], "R:/dst")
    assert second[0][ru.PROBE_GATE_PROBING_KEY] is True, second
    fp2 = probe_fingerprint(mod._ctx.config.qbittorrent, mod.probe_salt())
    assert fp2 != fp1, (fp1, fp2)
    entries = mod.probe_pending_list()
    assert [e["fingerprint"] for e in entries] == [fp1, fp2], f"异指纹追加等位队尾(FIFO 序) {entries}"
    assert slot.in_flight() == fp1, "单飞互斥: 槽保持首个指纹, 不被异指纹换手"
    assert len(_probe_threads(pre)) == 1, "槽被占: 不 kick"
    threads = _probe_threads(pre)
    release.set()
    q.get(timeout=10)
    threads[0].join(timeout=5)
    assert not threads[0].is_alive()
    slot.release()


def test_probe_slot_busy_blocks_kick_and_keeps_slot_untouched(monkeypatch):
    """槽被异指纹预先占用 => 只入队等位: 槽不被抢、替身 probe 零调用、回执与 kick 成功同形"""
    mod, locs = _gate_env(monkeypatch)
    calls = []
    q, slot = _wire_async(mod, _silent_probe(calls))
    assert slot.try_acquire("other-fp") is True  # 预占槽(异指纹在飞形态)
    items = mod.relocate_execute(["HA"], "R:/dst")
    it = items[0]
    assert it["cls"] == "blocked" and it[ru.PROBE_GATE_PROBING_KEY] is True, it
    assert "同机探测已入队" in it["reasons"][-1]["text"], it["reasons"]
    entries = mod.probe_pending_list()
    assert len(entries) == 1 and entries[0]["dst"] == "R:/dst", "槽被占也必须落意图(等位), entries"
    assert slot.in_flight() == "other-fp", "槽不被后来请求抢走"
    assert calls == [], "等位不得起探针线程(替身 probe 零调用)"
    assert not mod.active_jobs() and locs == [], (mod.active_jobs(), locs)
    slot.release()


def test_probe_receipt_key_distinguishes_probing_from_other_blocked(monkeypatch):
    """可区分性四面: 异步「探测中」带键; env=True 失败/缓存 failed/qb_conf 缺失 blocked 均无键"""
    # (a) 异步「探测中」: 键在场(槽预占形态, 零线程面)
    mod, _locs = _gate_env(monkeypatch)
    calls = []
    _wire_async(mod, _silent_probe(calls))
    slot = mod._probe_runner._slot
    slot.try_acquire("other-fp")
    probing = mod.relocate_execute(["HA"], "R:/dst")[0]
    assert probing.get(ru.PROBE_GATE_PROBING_KEY) is True and probing["cls"] == "blocked", probing
    slot.release()
    # (b) 内联注入 env=True 失败: blocked 无键(T3 防自环要认的就是这个形态)
    mod2, _locs2 = _gate_env(monkeypatch)
    _stub_run_probe(monkeypatch, [_env_failed("add_rejected")])
    env_fail = mod2.relocate_execute(["HA"], "R:/dst")[0]
    assert env_fail["cls"] == "blocked" and ru.PROBE_GATE_PROBING_KEY not in env_fail, env_fail
    assert "探测环境性失败" in env_fail["reasons"][-1]["text"], env_fail["reasons"]
    # (c) 内联注入缓存 failed 命中: blocked 无键(D7 1 同指纹不重试)
    mod3, _locs3 = _gate_env(monkeypatch)
    _stub_run_probe(monkeypatch, [_fs_failed("write_proof_timeout")])
    fp = probe_fingerprint(mod3._ctx.config.qbittorrent, mod3.probe_salt_ensure())
    mod3.probe_put(fp, "failed", {"reason": "write_proof_timeout"})
    cached = mod3.relocate_execute(["HA"], "R:/dst")[0]
    assert cached["cls"] == "blocked" and ru.PROBE_GATE_PROBING_KEY not in cached, cached
    assert "上次同机探测失败" in cached["reasons"][-1]["text"], cached["reasons"]
    # (d) qb_conf 缺失(直测 _ensure_probe): 分支先于未命中, 与形态开关无关, blocked 无键
    mod4, _locs4 = _gate_env(monkeypatch)
    _stub_run_probe(monkeypatch, [_passed()])
    mod4._ctx.config = types.SimpleNamespace(relocate=RelocateConfig(enabled=True))  # 无 qbittorrent 段
    gate = mod4._ensure_probe(
        [types.SimpleNamespace(hash="HA"), types.SimpleNamespace(hash="HB")],
        types.SimpleNamespace(same_fs_proved=False),
        {
            "cls": "ok",
            "reasons": [],
            "notes": []
        },
    )
    assert gate["cls"] == "blocked" and ru.PROBE_GATE_PROBING_KEY not in gate, gate


def test_probe_inline_seam_keeps_sync_semantics_default_async(monkeypatch):
    """注入 seam 双面: 类属性缺省 = 生产异步零布线; 内联形态同步收尾且不碰队列/全局槽"""
    # 生产缺省面: 未命中分支走异步(意图入队 + kick), 主循环零阻塞
    assert rex.ExecMixin._probe_inline is False and rex.ExecMixin._probe_runner is None
    # 内联形态(_stub_run_probe 先例: 类级开 _probe_inline + monkeypatch rex.run_probe):
    # 同步拿 verdict 走原收尾 —— started/建账/setLocation 与异步化前逐字一致
    mod, locs = _gate_env(monkeypatch)
    calls = _stub_run_probe(monkeypatch, [_passed()])
    items = mod.relocate_execute(["HA"], "R:/dst")
    assert items[0]["cls"] == "started", items
    assert len(calls) == 1 and calls[0] == {"src": "R:/src", "dst": "R:/dst"}, calls
    assert len(locs) == 1 and locs[0]["location"] == "R:/dst", locs
    assert len(mod.active_jobs()) == 1, "内联同步语义: verdict 当轮兑现建账"
    assert mod.probe_pending_list() == (), "内联形态不入队(没有第二通道)"
    fp = probe_fingerprint(mod._ctx.config.qbittorrent, mod.probe_salt())
    assert mod.probe_get(fp)["status"] == "passed", "缓存照常写入"
    # run_inline 与单飞解耦: 全局单飞槽与结果队列(T1 生产单例)零触碰
    assert PROBE_SLOT.busy() is False and PROBE_VERDICT_QUEUE.empty(), "内联不碰全局协作面"


def test_probe_pending_merge_intent_matches_normalized_triple_only(monkeypatch):
    """容器面 merge_intent: 三元组归一匹配才合并(条目真身存原文); 其余一律 False 零动手"""
    mod = RelocateModule()
    mod._ctx = types.SimpleNamespace(state=types.SimpleNamespace(data={}))
    mod.probe_pending_append("fp1", ["HA"], "R:/src", "R:/dst", "web")
    # 归一匹配: 反斜杠/冗余斜杠形态差异(ru._norm fold_case=False 执行侧等值口径;
    # 尾斜杠是 path_normalize 刻意保留的区分面, 不算差异面)
    assert mod.probe_pending_merge_intent("fp1", "R:\\src", "R://dst", ["HB", "HB", ""]) is True
    e = mod.probe_pending_list()[0]
    assert e["hashes"] == ["HA", "HB"], f"去重并入 + 空白丢弃 {e}"
    assert e["dst"] == "R:/dst", f"条目真身存首达原文(归一只用于匹配) {e}"
    # 异目标 / 异指纹 / 异源 / 大小写变体(不折叠口径): 一律 False 零动手
    assert mod.probe_pending_merge_intent("fp1", "R:/src", "R:/other", ["HX"]) is False
    assert mod.probe_pending_merge_intent("fp9", "R:/src", "R:/dst", ["HX"]) is False
    assert mod.probe_pending_merge_intent("fp1", "R:/src2", "R:/dst", ["HX"]) is False
    assert mod.probe_pending_merge_intent("fp1", "R:/SRC", "R:/dst", ["HX"]) is False
    assert mod.probe_pending_list()[0]["hashes"] == ["HA", "HB"], "未命中合并零动手"
    # 字符串 hashes 按单 hash 容错(与 append/merge_hashes 同口径)
    assert mod.probe_pending_merge_intent("fp1", "R:/src", "R:/dst", "HC") is True
    assert mod.probe_pending_list()[0]["hashes"] == ["HA", "HB", "HC"]
