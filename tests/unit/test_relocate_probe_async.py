"""test_relocate_probe_async 测试计划: 探测异步化 S1 基础设施(计划 26-11-10-2350 §03/§04 S1,
并轨 26-11-15-2340 刀4)—— 探测 runner(daemon 线程 + 全异常合成 verdict + 可注入)、
state relocate.probe_pending 容器、探测线程独立 qB client、全局单飞槽。

接线前不改变任何既有调用行为(_ensure_probe 仍同步调 run_probe, 归 T2 改造); 本文件只钉
基础设施自身语义。数据形状: state.data["relocate"]["probe_pending"] = [{fingerprint, hashes,
src, dst, origin, ts}...](FIFO, 只存意图不存快照 D6, 持久化 D7, 补键类新容器不走版本链)。

## 测试计划(每个测试函数一条)

- test_probe_thread_ctx_isolates_client_session_store: 探测线程 ctx 的 api/client/Session/store 全部非主循环共享实例(S1 验收隔离断言), 仍 QbApi 门面 + 本地地址走 LocalQbClient; QbApi 不注入 ctx(D16 派生面不进线程)
- test_probe_thread_ctx_without_qb_config_degrades_to_api_unavailable: qbittorrent 配置缺失 => 线程侧 client=None, 真 run_probe 按 api_unavailable 环境性失败收口(与主循环同语义)
- test_runner_try_start_delivers_verdict_and_slot_lifecycle: 正常路径 verdict 原样投递队列; 线程 daemon=True(D4); 槽被占时同/异指纹一律拒收; 槽的释放只在主循环消费面, 释放后可再 kick(T3 流量)
- test_runner_synthesizes_failed_verdict_on_probe_exception: 线程内抛异常 => 合成 failed verdict(reason=runner_crashed, env=True, evidence 带异常), 不挂死
- test_runner_synthesizes_failed_verdict_on_ctx_factory_exception: 线程侧连接构造失败 => 同款合成 verdict(受理即兑现, 不存在 kick 成功但 verdict 永不到)
- test_runner_try_start_thread_start_failure_synthesizes_verdict_and_releases_slot: 线程 start 失败(OS 线程资源耗尽等) => 槽当场释放 + 合成 runner_crashed verdict 投递队列, 仍返回 True(受理即兑现不在启动缝破口)
- test_runner_run_inline_returns_verdict_without_queue_or_slot: 内联注入形态同步返回 verdict, 不投递队列不碰槽(与单飞解耦, 既有同步语义的注入 seam)
- test_probe_single_flight_slot_mutex_unit: 单飞槽单测: 占槽/在飞指纹/任一指纹拒收(同指纹也不二次占槽)/幂等释放/释放后再占
- test_probe_runner_defaults_wire_module_singletons: 缺省协作面 = 模块级单例 PROBE_SLOT/PROBE_VERDICT_QUEUE + 本模块 run_probe/probe_thread_ctx(生产路径)
- test_probe_pending_roundtrip_fifo_and_state_materialization: append->list round-trip: FIFO 序/条目 6 键面/ts 跟注入钟/真身落 state 惰性物化(补键不走版本链)/副本不穿透
- test_probe_pending_append_tolerates_string_hashes: append 入参字符串按单 hash 容错(append 侧 isinstance 分支, 与 merge 侧同口径钉住): hashes 落为 [该串] 而非逐字符拆分
- test_probe_pending_merge_hashes_dedupes_in_place: 同指纹合并去重并入(FIFO 位不动)/字符串按单 hash 容错/无此指纹返回 False
- test_probe_pending_corrupted_hashes_values_tolerated: 条目 hashes 值损坏(外部手改/漂移)读/合并面容错: str 按 [该串] 单 hash、非可迭代按空 list, 合并把坏值真身原位修复为规范列表
- test_probe_pending_pop_drop_clear_fifo_semantics: pop 队首 FIFO/drop 按指纹摘除幂等/clear 整箱清空返条数
- test_probe_pending_survives_restart_via_shared_state: 重启重载: 共享 state 上新模块实例原样读到条目(序/ts 不变, 无内存镜像旁路)
- test_probe_pending_bad_shapes_tolerated: 坏箱(非 list)读空 + 写路径原位修复; 上下文整体缺失全静默; 坏条目(非 dict)读跳过/pop 丢弃续弹
- test_probe_pending_receipt_ids_optional_field: T4 可选回执提示字段(relocate_execute receipt_cmd_id 的容器落点) —— 无 id 键不出现(6 键面不变); 带 id 落 receipt_ids=[id]; merge_intent 同意图并入去重/异意图不串/空 id 只并 hashes; 副本与真身 receipts 列表不别名; state 真身含键
- test_probe_pending_receipt_ids_bad_values_tolerated: receipt_ids 值级容错(R5 评审修复 #2) —— 真身坏值(int/str)读/合并/弹出按空处理不炸; 容器迭代 str 归一+空白丢弃; merge 直读真身顺带修复; 出站面 ids 推导非容器零动作
- test_probe_receipt_outbox_take_and_drop_oldest: 出站面(T4 补发通道) —— publish 空 ids 零动作; FIFO 排空式 take; 超 PROBE_RECEIPT_OUTBOX_MAX drop-oldest 封顶不破
- test_probe_pending_max_age_constant_groundwork: 超龄兜底常量位(T3 清扫接线前置): >= 探测预算上界(证读x2+证写+清理)x2, 钉 120.0 文档值
"""

import queue
import threading
import types

from auto_qb.core.modules.relocate_mod import RelocateModule

from auto_qb.core.modules.relocate_probe import (
    PROBE_CLEANUP_TIMEOUT_S,
    PROBE_PENDING_MAX_AGE_S,
    PROBE_READ_TIMEOUT_S,
    PROBE_RECEIPT_OUTBOX_MAX,
    PROBE_RUNNER_CRASHED_REASON,
    PROBE_SLOT,
    PROBE_VERDICT_QUEUE,
    PROBE_WRITE_TIMEOUT_S,
    ProbeResult,
    ProbeRunner,
    ProbeSingleFlight,
    STATUS_FAILED,
    probe_thread_ctx,
    run_probe,
)

from auto_qb.core.qbapi import QbApi

from auto_qb.core.qbclient import LocalQbClient, new_client

from auto_qb.torrents import TorrentStore

from clock import wait_until


def _qb_conf():
    """线程侧/主循环侧共用的假 qB 连接配置(base_url 与 QbittorrentConfig 同形; 不发真实请求)"""
    return types.SimpleNamespace(
        host="127.0.0.1",
        port=18080,
        username="",
        password="",
        api_key="",
        base_url="http://127.0.0.1:18080",
    )


def _mod(state_data=None, clock=None):
    """不落盘的裸模块: ctx 用 SimpleNamespace 拼(仿 test_relocate_probe_cache._mod 最小面)"""
    mod = RelocateModule(clock=clock)
    mod._ctx = types.SimpleNamespace(state=types.SimpleNamespace(data=state_data if state_data is not None else {}))
    return mod


def _passed():
    return ProbeResult("passed", "ok", False, {"method": "e1", "read_ok": True, "write_ok": True})


def test_probe_thread_ctx_isolates_client_session_store():
    """探测线程 ctx 独立面: api/client/Session/store 全部非主循环共享实例(S1 验收隔离断言)

    构造路径与主循环同款(new_client, 本地地址走 LocalQbClient)但实例全新 —— 风险表 S1 行
    钉死处置「独立 client 实例, 不共享 Session」。QbApi 不注入 ctx: D16 删种拦截的派生查询
    经 ctx.relocate 现取, 探测线程不读共享 relocate 派生面。
    """
    qb = _qb_conf()
    main_client = new_client(qb)
    main_api = QbApi(main_client, TorrentStore())
    ctx = types.SimpleNamespace(config=types.SimpleNamespace(qbittorrent=qb), api=main_api)
    probe_ctx = probe_thread_ctx(ctx)
    assert isinstance(probe_ctx.api, QbApi), "线程侧仍经 QbApi 门面(不裸散 client 调用)"
    assert probe_ctx.api is not main_api
    assert probe_ctx.api.client is not main_client
    assert probe_ctx.api.store is not main_api.store, "线程侧全新 store, 探测线程零共享 store 写"
    # Session 级隔离(各自惰性物化一次后比对身份; 构造期不发任何网络请求)
    assert isinstance(probe_ctx.api.client, LocalQbClient)
    assert probe_ctx.api.client._session is not main_client._session
    assert getattr(probe_ctx.api, "ctx", None) is None


def test_probe_thread_ctx_without_qb_config_degrades_to_api_unavailable():
    """qbittorrent 配置缺失 => 线程侧 client=None, 真 run_probe 按 api_unavailable 收口

    与主循环同语义(环境性失败 env=True); 真 run_probe 走 client 非空检查即返回, 零轮询零触盘。
    """
    ctx = types.SimpleNamespace(config=types.SimpleNamespace())  # 无 qbittorrent 段
    probe_ctx = probe_thread_ctx(ctx)
    assert probe_ctx.api.client is None
    verdict = run_probe(probe_ctx, "R:/src", "R:/dst")
    assert verdict.status == STATUS_FAILED and verdict.reason == "api_unavailable" and verdict.env is True


def test_runner_try_start_delivers_verdict_and_slot_lifecycle():
    """正常路径: verdict 原样投递队列; daemon 线程(D4); 槽被占拒收; 消费面释放槽后可再 kick"""
    q = queue.Queue()
    slot = ProbeSingleFlight()
    gate = threading.Event()
    release = threading.Event()
    verdict_sent = _passed()

    def probe(ctx, src, dst):
        gate.set()
        release.wait(10)
        return verdict_sent

    runner = ProbeRunner(queue=q, slot=slot, thread_ctx_factory=lambda c: c, probe_fn=probe)
    pre = {t for t in threading.enumerate() if t.name == "relocate-probe"}  # 用例启动前快照(差集过滤残留)
    assert runner.try_start(object(), "fp1", "R:/src", "R:/dst") is True
    assert slot.busy() is True and slot.in_flight() == "fp1"
    assert gate.wait(10), "探测线程未启动"

    def fresh_probes():
        return [t for t in threading.enumerate() if t.name == "relocate-probe" and t not in pre]

    # 按快照差集轮询「本用例新起的探针线程恰 1 个」: 乱序巡检下上一用例的探针线程可能恰处
    # 退场窗, 进程级按名快照 len==1 会偶发多计(wait_until 单点, 计划 26-11-05-0118 S1/S3)
    assert wait_until(lambda: len(fresh_probes()) == 1), "本用例新起探针线程恰 1 个(差集过滤退场窗残留)"
    threads = fresh_probes()
    assert threads[0].daemon is True, "D4: daemon=True, 优雅退出不 join"
    # 单飞互斥(验收 4): 第二探测在飞时被拒 —— 同指纹也不二次占槽(合并语义归容器, T2)
    assert runner.try_start(object(), "fp1", "R:/src", "R:/dst") is False
    assert runner.try_start(object(), "fp2", "R:/src", "R:/dst") is False
    release.set()
    fp, verdict = q.get(timeout=10)
    assert fp == "fp1" and verdict is verdict_sent, "verdict 原样投递(同一对象, 零改动透传)"
    threads[0].join(timeout=5)
    assert not threads[0].is_alive()
    assert slot.busy() is True, "线程完成不释放槽: 在飞窗口到 verdict 被消费为止"
    slot.release()  # 主循环消费面(T3: 清条目 -> 释放槽 -> kick 下一条)
    assert slot.busy() is False
    assert runner.try_start(object(), "fp2", "R:/src", "R:/dst") is True
    fp2, verdict2 = q.get(timeout=10)
    assert fp2 == "fp2" and verdict2.status == "passed"
    threads = [t for t in threading.enumerate() if t.name == "relocate-probe"]
    for t in threads:
        t.join(timeout=5)
        assert not t.is_alive(), "用例收尾不留活线程(全局线程快照不污染其它用例)"


def test_runner_synthesizes_failed_verdict_on_probe_exception():
    """线程内抛异常 => 合成 failed verdict(reason=runner_crashed, env=True 不缓存, evidence 带异常)"""
    q = queue.Queue()

    def boom(ctx, src, dst):
        raise RuntimeError("boom-in-probe")

    runner = ProbeRunner(queue=q, slot=ProbeSingleFlight(), thread_ctx_factory=lambda c: c, probe_fn=boom)
    assert runner.try_start(object(), "fpX", "R:/src", "R:/dst") is True
    fp, verdict = q.get(timeout=10)
    assert fp == "fpX"
    assert verdict.status == STATUS_FAILED and verdict.reason == PROBE_RUNNER_CRASHED_REASON
    assert verdict.env is True, "合成失败按环境性(不缓存): 与 FS 可达性无关"
    assert "boom-in-probe" in str(verdict.evidence.get("error"))


def test_runner_synthesizes_failed_verdict_on_ctx_factory_exception():
    """线程侧连接构造失败 => 同款合成 verdict(受理即兑现, 不存在 kick 成功但 verdict 永不到)"""
    q = queue.Queue()

    def broken_factory(ctx):
        raise RuntimeError("conn-build-failed")

    runner = ProbeRunner(queue=q, slot=ProbeSingleFlight(), thread_ctx_factory=broken_factory)
    assert runner.try_start(object(), "fpY", "R:/src", "R:/dst") is True
    fp, verdict = q.get(timeout=10)
    assert fp == "fpY"
    assert verdict.status == STATUS_FAILED and verdict.reason == PROBE_RUNNER_CRASHED_REASON and verdict.env is True
    assert "conn-build-failed" in str(verdict.evidence.get("error"))


def test_runner_try_start_thread_start_failure_synthesizes_verdict_and_releases_slot(monkeypatch):
    """线程 start 失败(OS 线程资源耗尽等) => 槽当场释放 + 合成 runner_crashed verdict 投递队列, 仍返回 True

    占槽成功后 Thread(...).start() 抛异常时槽已占但无线程无 verdict —— 单飞槽会被永久占用
    到重启, 受理即兑现不变量在启动缝上不许破口: 槽当场释放, 结论照常经队列兑现。
    """
    q = queue.Queue()
    slot = ProbeSingleFlight()
    start_called = threading.Event()

    def explode(self):
        start_called.set()
        raise RuntimeError("os-thread-resource-exhausted")

    monkeypatch.setattr(threading.Thread, "start", explode)
    runner = ProbeRunner(queue=q, slot=slot, thread_ctx_factory=lambda c: c, probe_fn=lambda c, s, d: _passed())
    assert runner.try_start(object(), "fpZ", "R:/src", "R:/dst") is True, "受理面不因线程启动失败改口径"
    assert start_called.is_set(), "Thread.start 确被调用(注入面命中)"
    assert slot.busy() is False, "启动失败当场释放槽, 不留单飞槽永久占用"
    fp, verdict = q.get(timeout=10)
    assert fp == "fpZ"
    assert verdict.status == STATUS_FAILED and verdict.reason == PROBE_RUNNER_CRASHED_REASON and verdict.env is True
    assert "os-thread-resource-exhausted" in str(verdict.evidence.get("error"))
    assert slot.try_acquire("fp-next") is True and slot.in_flight() == "fp-next", "槽已释放可再 kick"
    slot.release()


def test_runner_run_inline_returns_verdict_without_queue_or_slot():
    """内联注入形态: 同步返回 verdict; 不投递队列、不碰槽(既有同步语义的注入 seam)"""
    q = queue.Queue()
    slot = ProbeSingleFlight()
    assert slot.try_acquire("other") is True  # 预占槽: 内联执行与单飞槽解耦
    seen = {}

    def probe(ctx, src, dst):
        seen["src"], seen["dst"] = src, dst
        return _passed()

    runner = ProbeRunner(queue=q, slot=slot, thread_ctx_factory=lambda c: c, probe_fn=probe)
    verdict = runner.run_inline(object(), "fpI", "R:/src", "R:/dst")
    assert verdict.status == "passed"
    assert seen == {"src": "R:/src", "dst": "R:/dst"}, "src/dst 实参原样透传"
    assert q.empty(), "内联形态不投递队列(同步形态没有第二通道)"
    assert slot.in_flight() == "other", "内联不碰槽"
    slot.release()


def test_probe_single_flight_slot_mutex_unit():
    """单飞槽单测: 占槽/在飞指纹/任一指纹拒收/幂等释放/释放后再占"""
    slot = ProbeSingleFlight()
    assert slot.busy() is False and slot.in_flight() is None
    assert slot.try_acquire("fp1") is True
    assert slot.busy() is True and slot.in_flight() == "fp1"
    assert slot.try_acquire("fp2") is False, "任一指纹在飞都拒收"
    assert slot.try_acquire("fp1") is False, "同指纹也不二次占槽"
    slot.release()
    assert slot.busy() is False and slot.in_flight() is None
    slot.release()  # 幂等
    assert slot.try_acquire("fp2") is True, "释放后异指纹可占"
    slot.release()


def test_probe_runner_defaults_wire_module_singletons():
    """缺省协作面 = 模块级单例(生产路径): PROBE_SLOT/PROBE_VERDICT_QUEUE + run_probe/probe_thread_ctx"""
    runner = ProbeRunner()
    assert runner._slot is PROBE_SLOT and runner._queue is PROBE_VERDICT_QUEUE
    assert runner._probe_fn is run_probe
    assert runner._thread_ctx_factory is probe_thread_ctx


def test_probe_pending_roundtrip_fifo_and_state_materialization(fake_clock):
    """append -> list round-trip: FIFO 序/条目 6 键面/ts 跟注入钟/真身落 state 惰性物化/副本不穿透"""
    mod = _mod(clock=fake_clock)
    assert mod.probe_pending_list() == (), "未入队前读为空"
    e1 = mod.probe_pending_append("fp1", ["HA", "HB"], "R:/src", "R:/dst", "web")
    fake_clock.advance(3.0)
    e2 = mod.probe_pending_append("fp2", ["HC"], "R:/src2", "R:/dst2", "rule")
    box = mod._ctx.state.data["relocate"]["probe_pending"]
    assert isinstance(box, list) and len(box) == 2, "setdefault 惰性物化(补键类新容器, 不走版本链)"
    assert mod.probe_pending_list() == (e1, e2), "FIFO: 先进先出"
    assert list(e1) == ["fingerprint", "hashes", "src", "dst", "origin", "ts"], "条目键面钉死(只存意图 D6)"
    assert e1["hashes"] == ["HA", "HB"] and e1["origin"] == "web" and e2["origin"] == "rule"
    assert e1["ts"] == int(fake_clock.now()) - 3 and e2["ts"] == int(fake_clock.now()), "ts 为入队 epoch 秒(跟注入钟)"
    e1["hashes"].append("HX")
    e1["src"] = "X"
    assert box[0]["hashes"] == ["HA", "HB"] and box[0]["src"] == "R:/src", "副本口径: 改副本不穿透真身"


def test_probe_pending_append_tolerates_string_hashes():
    """append 入参字符串按单 hash 容错(append 侧 isinstance 分支, 与 merge 侧同口径钉住)"""
    mod = _mod()
    entry = mod.probe_pending_append("fpS", "HS", "R:/src", "R:/dst", "web")
    assert entry["hashes"] == ["HS"], "字符串按单 hash 入队(逐字符拆分是真实 footgun)"
    assert mod.probe_pending_list()[0]["hashes"] == ["HS"], "真身与读面一致落单 hash"


def test_probe_pending_merge_hashes_dedupes_in_place():
    """同指纹合并: hashes 去重并入既有条目(FIFO 位不动); 字符串按单 hash 容错; 无此指纹 False"""
    mod = _mod()
    mod.probe_pending_append("fp1", ["HA", "HB"], "R:/src", "R:/dst", "web")
    mod.probe_pending_append("fp2", ["HC"], "R:/src2", "R:/dst2", "rule")
    assert mod.probe_pending_merge_hashes("fp2", ["HC", "HD", ""]) is True, "去重 + 空白 hash 丢弃"
    assert mod.probe_pending_merge_hashes("fp1", "HE") is True, "字符串按单 hash 容错"
    entries = mod.probe_pending_list()
    assert [e["fingerprint"] for e in entries] == ["fp1", "fp2"], "合并不动 FIFO 位"
    assert entries[0]["hashes"] == ["HA", "HB", "HE"]
    assert entries[1]["hashes"] == ["HC", "HD"]
    assert mod.probe_pending_merge_hashes("nope", ["HX"]) is False


def test_probe_pending_corrupted_hashes_values_tolerated():
    """条目 hashes 值损坏(外部手改/漂移)读/合并面容错: str 按 [该串] 单 hash、非可迭代按空 list"""
    mod = _mod(
        state_data={
            "relocate":
                {
                    "probe_pending":
                        [
                            {
                                "fingerprint": "fpB",
                                "hashes": "HS",
                                "ts": 1
                            },
                            {
                                "fingerprint": "fpC",
                                "hashes": 7,
                                "ts": 2
                            },
                        ]
                }
        }
    )
    entries = mod.probe_pending_list()
    assert entries[0]["hashes"] == ["HS"], "str 坏值按 [该串] 单 hash(不逐字符拆分)"
    assert entries[1]["hashes"] == [], "非可迭代坏值按空 list(不炸 TypeError)"
    assert mod.probe_pending_merge_hashes("fpB", ["HX"]) is True, "str 坏值合并按单 hash 并入"
    assert mod.probe_pending_merge_hashes("fpC", ["HY"]) is True, "非可迭代坏值合并不炸"
    assert [e["hashes"] for e in mod.probe_pending_list()] == [["HS", "HX"], ["HY"]], "合并把坏值真身原位修复为规范列表"


def test_probe_pending_pop_drop_clear_fifo_semantics():
    """pop 队首 FIFO; drop 按指纹摘除(邻居不动, 幂等 False); clear 整箱清空返条数"""
    mod = _mod()
    mod.probe_pending_append("fp1", ["HA"], "s1", "d1", "web")
    mod.probe_pending_append("fp2", ["HB"], "s2", "d2", "rule")
    mod.probe_pending_append("fp3", ["HC"], "s3", "d3", "web")
    head = mod.probe_pending_pop()
    assert head["fingerprint"] == "fp1", "pop 恒队首(FIFO 单出口)"
    assert mod.probe_pending_drop("fp3") is True
    assert [e["fingerprint"] for e in mod.probe_pending_list()] == ["fp2"], "drop 只摘目标, 邻居不动"
    assert mod.probe_pending_drop("fp3") is False, "幂等"
    assert mod.probe_pending_pop()["fingerprint"] == "fp2"
    assert mod.probe_pending_pop() is None
    mod.probe_pending_append("fp4", ["HD"], "s4", "d4", "web")
    assert mod.probe_pending_clear() == 1
    assert mod.probe_pending_list() == () and mod.probe_pending_clear() == 0


def test_probe_pending_survives_restart_via_shared_state(fake_clock):
    """重启重载: 共享 state 上新模块实例原样读到条目(序/ts 不变, 无内存镜像旁路)"""
    shared = {}
    a = _mod(shared, clock=fake_clock)
    a.probe_pending_append("fp1", ["HA"], "R:/src", "R:/dst", "web")
    a.probe_pending_append("fp2", ["HB", "HC"], "R:/src2", "R:/dst2", "rule")
    b = _mod(shared, clock=fake_clock)  # 重启后的模块: 从 state 重载(容器无内存镜像)
    assert b.probe_pending_list() == a.probe_pending_list()
    assert [e["fingerprint"] for e in b.probe_pending_list()] == ["fp1", "fp2"]
    assert b.probe_pending_list()[1]["hashes"] == ["HB", "HC"]


def test_probe_pending_bad_shapes_tolerated():
    """坏形容错: 坏箱(非 list)读空 + 写路径原位修复; 上下文缺失全静默; 坏条目读跳过/pop 丢弃续弹"""
    mod = _mod(state_data={"relocate": {"probe_pending": {"bad": "box"}}})
    assert mod.probe_pending_list() == (), "坏箱读空不炸"
    mod.probe_pending_append("fp1", ["HA"], "s", "d", "web")
    box = mod._ctx.state.data["relocate"]["probe_pending"]
    assert isinstance(box, list) and len(box) == 1 and box[0]["fingerprint"] == "fp1", "写路径原位修复坏箱"

    bare = RelocateModule()  # 连 ctx 都没有(P1 前的模块形态): 全部静默不炸
    assert bare.probe_pending_list() == () and bare.probe_pending_pop() is None
    assert bare.probe_pending_drop("fp") is False and bare.probe_pending_merge_hashes("fp", ["H"]) is False
    assert bare.probe_pending_clear() == 0

    mod2 = _mod(state_data={"relocate": {"probe_pending": ["junk", {"fingerprint": "fpA", "hashes": ["HA"], "ts": 1}]}})
    assert [e["fingerprint"] for e in mod2.probe_pending_list()] == ["fpA"], "坏条目读跳过(留原地)"
    popped = mod2.probe_pending_pop()
    assert popped is not None and popped["fingerprint"] == "fpA", "坏队首丢弃续弹"
    assert mod2.probe_pending_pop() is None, "弹到空返回 None"


def test_probe_pending_receipt_ids_optional_field(fake_clock):
    """T4 可选回执提示字段(receipt_ids): 无 id 键不出现 / 带 id 落单元素列表 / merge_intent 并入去重 / 副本不别名

    relocate_execute 的 receipt_cmd_id(web 命令 cmd_id)经 _ensure_probe 落到本容器: 规则
    路径(无 id)条目键面不变(D6 六键), 终态补发按 receipt_ids 判决(空 = 零动作)。
    """
    mod = _mod(clock=fake_clock)
    rule = mod.probe_pending_append("fp1", ["HA"], "R:/s", "R:/d", "rule")
    assert "receipt_ids" not in rule, "规则路径(无 id)条目不带键: 键的存在性 = 有无 web 受理回执"
    assert list(rule) == ["fingerprint", "hashes", "src", "dst", "origin", "ts"], "六键面不变(D6)"
    web = mod.probe_pending_append("fp2", ["HB"], "R:/s2", "R:/d2", "web", receipt_id="cmd-web-1")
    assert web["receipt_ids"] == ["cmd-web-1"], "带 id 条目落 receipt_ids=[id]"
    box = mod._ctx.state.data["relocate"]["probe_pending"]
    assert box[1]["receipt_ids"] == ["cmd-web-1"], "state 真身含键(持久面)"
    # 同意图合并: id 并入去重; 重复 id 不重复; 空 id 只并 hashes 不动 receipt_ids
    assert mod.probe_pending_merge_intent("fp2", "R:/s2", "R:/d2", ["HB", "HC"], receipt_id="cmd-web-2") is True
    assert mod.probe_pending_merge_intent("fp2", "R:/s2", "R:/d2", ["HC"], receipt_id="cmd-web-2") is True, "重复 id 去重"
    assert mod.probe_pending_merge_intent("fp2", "R:/s2", "R:/d2", ["HD"]) is True, "空 id(规则路径)只并 hashes"
    merged = mod.probe_pending_list()[1]
    assert merged["hashes"] == ["HB", "HC", "HD"] and merged["receipt_ids"] == ["cmd-web-1", "cmd-web-2"]
    # 异意图(同指纹异目标)不串: merge 不命中(调用方 _ensure_probe 改走 append), 各带各的 id
    assert mod.probe_pending_merge_intent("fp2", "R:/s2", "R:/other", ["HZ"], receipt_id="cmd-web-3") is False
    mod.probe_pending_append("fp2", ["HZ"], "R:/s2", "R:/other", "web", receipt_id="cmd-web-3")
    entries = mod.probe_pending_list()
    assert len(entries) == 3 and entries[2]["receipt_ids"] == ["cmd-web-3"], "异意图不合并(id 不串条目)"
    assert entries[1]["receipt_ids"] == ["cmd-web-1", "cmd-web-2"]
    # 副本口径: 改副本 receipts 不穿透真身
    web["receipt_ids"].append("mutated")
    assert box[1]["receipt_ids"] == ["cmd-web-1", "cmd-web-2"], "副本 receipts 列表与真身不别名"


def test_probe_pending_receipt_ids_bad_values_tolerated():
    """receipt_ids 值级容错(R5 评审修复 #2): 真身坏值读/合并/弹出/出站面全不炸按空处理

    容错单点 _probe_receipt_ids_as_list(与 _probe_hashes_as_list 同款口径): list/tuple/set
    容器原样迭代(str 归一+空白丢弃), 非容器(str/int/None)按空列表 —— cmd_id 关联是列表
    语义, 单串真身属漂移形态不猜。merge 直读真身(生产热路径)顺带把坏值修复为规范列表。
    """
    mod = _mod(
        state_data={
            "relocate":
                {
                    "probe_pending":
                        [
                            {
                                "fingerprint": "fpInt",
                                "hashes": ["HA"],
                                "ts": 1,
                                "receipt_ids": 7
                            },
                            {
                                "fingerprint": "fpStr",
                                "hashes": ["HB"],
                                "ts": 2,
                                "receipt_ids": "cmd-str"
                            },
                            {
                                "fingerprint": "fpList",
                                "hashes": ["HC"],
                                "ts": 3,
                                "receipt_ids": ["cmd-ok", "", 9]
                            },
                        ]
                }
        }
    )
    entries = mod.probe_pending_list()
    assert entries[0]["receipt_ids"] == [], "int 坏值按空列表(非容器)"
    assert entries[1]["receipt_ids"] == [], "str 非容器按空列表(cmd_id 关联是列表语义, 不猜单值)"
    assert entries[2]["receipt_ids"] == ["cmd-ok", "9"], "容器迭代: str 归一 + 空白丢弃(int 元素 coerce 保留)"
    assert mod.probe_pending_pop()["fingerprint"] == "fpInt", "坏值条目 pop 不炸"
    # merge 直读真身(生产热路径): 坏值不炸 + 顺带修复为规范列表 + 新 id
    assert mod.probe_pending_merge_intent("fpStr", "R:/s", "R:/d", ["HB"], receipt_id="cmd-fix") is False, \
        "src/dst 不匹配(种子数据缺字段)不命中 —— 容错面只在命中分支"
    box = mod._ctx.state.data["relocate"]["probe_pending"]
    box[0]["src"] = "R:/s"  # pop 后 fpStr 是队首(索引随 FIFO 位移)
    box[0]["dst"] = "R:/d"
    assert mod.probe_pending_merge_intent("fpStr", "R:/s", "R:/d", ["HB"], receipt_id="cmd-fix") is True
    assert box[0]["receipt_ids"] == ["cmd-fix"], "str 坏值真身被合并修复为规范列表"
    assert mod.probe_pending_merge_intent("fpInt", "R:/s", "R:/d", ["HA"], receipt_id="cmd-fix2") is False
    # 出站面 ids 推导: 非容器按空零动作; 容器内空白/falsy 丢弃
    assert mod._probe_receipt_publish(7, [], "") == 0, "int 形参按空零动作"
    assert mod._probe_receipt_publish("cmd-str", [], "") == 0, "str 形参按空零动作"
    assert mod._probe_receipt_publish(["c1", "", 0], [], "") == 1, "容器: 空白/falsy 元素丢弃"


def test_probe_receipt_outbox_take_and_drop_oldest():
    """出站面(T4 补发通道): 空 ids 零动作 / FIFO 排空式 take / drop-oldest 封顶

    正常面 = 消费面每 verdict 至多投 len(receipt_ids) 条 + webui 命令线每轮排空, 在飞常态
    0~几条; 上限只在 webui 消费面缺失的病态堆积下生效(对齐 WEB_RESULT_MAX 护栏精神)。
    """
    mod = _mod()
    assert mod.probe_receipts_take() == [], "空面 take 返回空"
    assert mod._probe_receipt_publish([], [], "") == 0, "空 receipt_ids 零动作(规则路径形态)"
    assert mod._probe_receipt_publish(["", "  "], [], "") == 0, "全空白 id 同样零动作"
    assert mod._probe_receipt_publish(["c1", "c2"], [{"cls": "started"}], "") == 2, "同批多 id 各投一条"
    out = mod.probe_receipts_take()
    assert [r["cmd_id"] for r in out] == ["c1", "c2"], "FIFO 序"
    assert out[0]["items"] == [{"cls": "started"}] and out[0]["error"] == "", "条目形状 (cmd_id, items, error)"
    assert mod.probe_receipts_take() == [], "排空式: take 后面空(不重复补发)"
    # drop-oldest 封顶: 超上限丢最旧, 面长恒 <= PROBE_RECEIPT_OUTBOX_MAX
    for i in range(PROBE_RECEIPT_OUTBOX_MAX + 5):
        mod._probe_receipt_publish([f"old-{i}"], [], "")
    out = mod.probe_receipts_take()
    assert len(out) == PROBE_RECEIPT_OUTBOX_MAX, f"封顶 {PROBE_RECEIPT_OUTBOX_MAX}"
    assert out[0]["cmd_id"] == "old-5" and out[-1]["cmd_id"] == f"old-{PROBE_RECEIPT_OUTBOX_MAX + 4}", "丢最旧(drop-oldest)"
    # error 形态: items 空带文案(防自环/重放异常的终态定形)
    assert mod._probe_receipt_publish(["c3"], [], "boom") == 1
    rec = mod.probe_receipts_take()[0]
    assert rec == {"cmd_id": "c3", "items": [], "error": "boom"}


def test_probe_pending_max_age_constant_groundwork():
    """超龄兜底常量位(T3 清扫接线前置): >= 探测预算上界 x2(裕度方向不许缩), 钉 120.0 文档值"""
    budget = PROBE_READ_TIMEOUT_S * 2 + PROBE_WRITE_TIMEOUT_S + PROBE_CLEANUP_TIMEOUT_S  # 证读 + 证读轮询 + 证写 + 清理
    assert PROBE_PENDING_MAX_AGE_S >= budget * 2, "超龄线必须 >= 预算上界的 2 倍(风险表 S1 行裕度)"
    assert PROBE_PENDING_MAX_AGE_S == 120.0
