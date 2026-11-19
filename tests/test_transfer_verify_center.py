"""test_transfer_verify_center 测试计划: transfer 验证中心(计划 26-11-20-0127 S2)

## 测试计划(每个测试函数一条)
- test_batch_receipt_written_when_all_slots_filled: 回灌结算 + 槽位聚合 + 回执按批齐写 ——
  3 作业批次(成功删源 / keep_source 成功不删源 / 验证失败在途), 前两轮无回执, 批次齐才
  写; payload {results(按入参顺序), summary, target} 与命令面 handler 逐字节同形; 删源只
  对成功且未保留源的槽位发生, 操作键 = source_hash(与回执键分置)
- test_multi_batches_fifo_coexistence: 多批次 FIFO 共存(D3a) —— 两批先后递交, 单 worker
  严格按递交顺序处理(A1,A2 -> B1,B2), 两批各自齐写回执, adapter 批次级各建一个
- test_stop_event_exits_promptly_without_join: 空闲等待中 stop, 线程秒级内退出(不 join);
  已 stop 后递交作业被丢弃(关停期新批次不入账, 保守默认)
- test_stop_wakes_inflight_verify_poll_immediately: 在途验证轮询等待中 stop 即时醒(D4a) ——
  默认 runner + 恒查无目标, 验证早期 stop, 剩余轮询预算(约 2s 的 Event.wait 节拍)在 1s 内
  跑完退出(sleep 注入若退化成真 time.sleep 则本用例红); 在途作业自然结算、结论仍回灌
  (stop 只保证队列余量不再处理, 见 stop() docstring), 主循环再 drain 回执照写
- test_seed_exception_synth_unexpected: 单种子异常(worker runner 抛) -> 合成 UNEXPECTED
  结果回灌, 批次不挂死、照常齐写回执(§03/§07 行 1 第一道兜底)
- test_loop_level_exception_synth_unexpected: 循环级异常(回灌 push 首次抛) -> 循环级兜底
  合成 UNEXPECTED 回灌, 结论必达(线程保活)
- test_adapter_exclusive_worker_thread_only: adapter 独占断言(D1) —— 工厂在 worker 线程
  调用, adapter 方法全部 worker 线程调用, 主循环线程零调用; 每批恰建一个 adapter
- test_adapter_factory_failure_retried_and_not_cached: 守卫「工厂调用先于缓存改写」——
  批 B 首作业工厂抛异常 -> B1 结算 UNEXPECTED 且缓存原样, B2 重试工厂成功、跑在 B 的
  新实例上; 旧顺序(键先写)下 B2 静默复用批 A 旧 adapter, 本用例当场红
- test_worker_runs_orchestrator_run_verify_job: 默认 runner = orchestrator.run_verify_job
  (作业进结果出): add -> 验证轮询 -> SUCCESS; 删源不在 worker 侧, 由 drain 端口按
  source_hash 执行; 跳检决策随 plan 透传
- test_same_hash_cross_batch_silent_delete: 同 hash 双批次异目标(反序交错钉面, D3/R2) ——
  两批都验证成功, 后结算者删源是静默无操作(qB 对未知 hash 回 200 / store.remove_torrent
  pop-None / _delete_source 返 True 口径), 回执纯 SUCCESS 无注记
- test_drain_result_exception_isolated_and_slot_retried: drain 逐结果异常隔离(§07 行 5) ——
  中间结果的删源抛异常不影响前后结果结算, 下轮重试同一槽位后批次齐写回执
- test_delete_port_false_appends_source_kept_note: 删源端口返 False -> 状态仍成功, 注记
  「源删除失败, 源已保留」(与 run_batch 同口径, issue 26-11-03-0824)
- test_receipt_port_failure_retried_next_drain: 回执端口写失败 -> 批次保留, 下轮 drain
  重试写回执(§07 行 5 回执面)
- test_aged_batch_force_settled_verify_timeout_with_warning: 全局无结论产出超预算的未结算
  槽位按 VERIFY_TIMEOUT 口径兜底结算 + WARNING, 兜底不删源(§07 行 1 最后防线; 预算注入
  收紧窗口, 假钟推进不真等)
- test_progress_refresh_defers_overage_settle: 超龄判定信号 = 全局最近结论产出(每次成功
  填槽刷新)—— 批次推进途中的无进展窗口不触发兜底(按「入队以来」计口径会误判, 钉住
  新信号), 结论补齐后照常齐写回执
- test_idle_gap_reset_on_submit_after_drain: 空闲后新批次不被立即兜底(修 1 分支一)——
  递交前容器无未结算工作 -> 判定起点重置为递交时刻, 空闲间隔不计入 stalled; 递交后真
  无产出超预算时防挂死照样触发
- test_submit_second_batch_keeps_waiting_start: 容器已有未结算工作时不重置判定起点
  (修 1 分支二)—— 旧槽位等待起点不变, 全局无产出超预算 x 深度时两批一起兜底
- test_unwired_default_ports_placeholders: S2 默认端口占位语义(构造默认, 测试替身面;
  生产真实端口已接线) —— 删源端口占位返回 False(源保留 + 注记「源删除失败, 源已
  保留」), 回执端口占位落 WARNING 不写回执
- test_submit_empty_jobs_raises: 空条目/全已结算条目 fail-fast(ValueError; 应走生产段快路径,
  不入中心)
- test_submit_success_settled_entry_raises: SUCCESS 状态的已结算条目 fail-fast —— 已结算
  条目恒是未验证成功终态, SUCCESS 作槽位初值会被 keep_source 闸静默禁删源(不变量钉成
  机器可查)
- test_runtime_wiring_center_and_consume_tail_drain: runtime 持有 center(WebUIRuntime 构造
  即有); consume_commands 尾部调 drain(空命令队列轮次也调, D6 命令线尾部)
- test_submit_mixed_entries_slots_initial_values: S3 混列递交(已结算结果作槽位初值) ——
  槽位按入参顺序, 剩余计数只算验证作业; 已结算槽位 keep_source 置 True 永不删源(未验证
  成功不碰源); 批次齐写回执 truth 按入参顺序(D5), summary 聚合口径不变; 递交日志带
  「生产段已结算 N 个随槽位初值」计数
- test_drain_returns_true_on_successful_delete: drain 返回本轮是否有删源成功(D6: 并入
  cmd_changed_state 白享 P0-5) —— 删源成功轮 True, 纯回执轮/删源失败轮 False
- test_stop_discards_delete_intent_with_warning_no_delete_after_stop: S4 关停(D4a/§07 行 4)
  —— 验证成功后、drain 删源前 stop: 丢弃清单逐条 WARNING(hash + 「目标已建, 源未删, 请
  手动处置」+ 合计行); stop 后 drain 任何路径零删源(源种子零误删守阵), 槽位照常填、
  回执照常齐(是否落取决于是否再 drain)
- test_stop_discard_list_covers_delete_retry_entry: 丢弃清单覆盖删源重试中的槽位 ——
  删源端口抛异常进重试列表后 stop: WARNING 落日志; stop 后重试不再删源
- test_stop_discard_list_covers_delete_port_false_slot: 丢弃清单覆盖「槽位已填且删源端口
  返 False」面(源删除失败=删源未完成): stop 告警、合计计数正确、stop 后不再删源
- test_stop_discard_list_covers_late_success_with_batch_gone: 丢弃清单覆盖「批次已被超龄
  兜底结算摘除、SUCCESS 结论仍在队列」面 —— 批次不在容器不拦告警(keep_source 不可考,
  SUCCESS 保守告警宁多勿漏)
- test_stop_idempotent_discard_list_warned_once: stop 幂等 —— 丢弃清单 WARNING 首次 stop
  落一次, 重复 stop 不再枚举再记
- test_stop_submit_discard_and_worker_lifecycle_logs: S4 生命周期日志 —— 递交(批次大小,
  INFO)/结算(批次口径三态计数, INFO)/递交丢弃(已停止后递交, WARNING)
"""
from __future__ import annotations

import threading
from types import SimpleNamespace

import pytest

from clock import FakeClock, wait_until
from helpers import capture_logs

from auto_qb.config.models import TransferTargetConfig
from auto_qb.transfer.adapters import AddResult
from auto_qb.transfer.orchestrator import (
    TorrentTransferResult,
    TransferOutcomeCode,
    TransferStatus,
    TransferVerifyJob,
    _SeedPlan,
)
from auto_qb.webui.runtime import WebUIRuntime
from auto_qb.webui.runtime_transfer import TransferVerifyCenter

HASH_A = "a" * 40
HASH_B = "b" * 40
HASH_C = "c" * 40
HASH_D = "d" * 40
SRC_A = "s" * 40  # 与入参 hash 不同的源 hash(双 hash 分置: 回执键 = 入参, 删源键 = 源)
SRC_B = "t" * 40  # 同上, 混列递交用例的作业源 hash

LOG_NAME = "auto_qb.webui.runtime_transfer"

# ---------- 替身与助手(不联网) ----------


def _job(h: str, *, keep_source: bool = False, source_hash: str = "") -> TransferVerifyJob:
    src = source_hash or h
    plan = _SeedPlan(
        data=b"torrent-bytes",
        fields={
            "infohash": src,
            "save_path": "D:/seeds"
        },
        skip_check=False,
        degraded_note="",
        source_hash=src,
    )
    return TransferVerifyJob(hash=h, source_hash=src, plan=plan, keep_source=keep_source, after_state="keep")


def _target(name: str = "目标A") -> TransferTargetConfig:
    return TransferTargetConfig(
        name=name, type="qb", base_url="http://127.0.0.1:8081", username="u", password="p", enabled=True
    )


def _ok(job: TransferVerifyJob) -> TorrentTransferResult:
    return TorrentTransferResult(job.hash, TransferStatus.SUCCESS, "", None)


class _RecordingAdapter:
    """目标 adapter 替身(runner 注入用): 只带身份标记, runner 不调它的方法"""
    def __init__(self, tag: str):
        self.tag = tag


class _ThreadRecordingAdapter:
    """目标 adapter 替身(默认 runner 路径用): 脚本化 add/find 并记录调用线程(独占断言数据源)"""
    def __init__(self, tag: str, find_sequence=None):
        self.tag = tag
        self.created_thread = threading.get_ident()  # 工厂调用时刻的线程(应为 worker)
        self.call_threads = []  # (方法名, 线程id) 按调用序
        self.add_calls = []
        self.find_calls = []
        self._find_sequence = list(find_sequence) if find_sequence is not None else None

    def capabilities(self) -> set:
        return set()

    def add_torrent(self, data: bytes, fields: dict, skip_check: bool) -> AddResult:
        self.call_threads.append(("add", threading.get_ident()))
        self.add_calls.append({"data": data, "fields": dict(fields), "skip_check": skip_check})
        return AddResult.added("目标已受理")

    def find_torrent(self, infohash: str):
        self.call_threads.append(("find", threading.get_ident()))
        self.find_calls.append(infohash)
        if self._find_sequence is None:
            return {"hash": infohash, "state": "stoppedUP"}
        if not self._find_sequence:
            return None
        return self._find_sequence.pop(0)

    def pause_torrent(self, infohash: str) -> bool:
        self.call_threads.append(("pause", threading.get_ident()))
        return True


@pytest.fixture
def center_factory():
    """造中心(poll_interval 缩短提速)并统一收尾: stop + join, 不给进程留空闲线程"""
    made = []

    def _make(**kwargs) -> TransferVerifyCenter:
        center = TransferVerifyCenter(poll_interval=0.02, **kwargs)
        assert center._worker is None  # 懒启动: 构造后零线程(回归成构造即拉线程当场红)
        made.append(center)
        return center

    yield _make
    for center in made:
        center.stop()
        worker = center._worker
        if worker is not None and worker.is_alive():
            worker.join(timeout=2.0)


def _drain_until(center: TransferVerifyCenter, pred, timeout: float = 3.0) -> None:
    """反复 drain(模拟命令线尾部节拍)直到条件成立; 超时断言失败"""
    def step() -> bool:
        center.drain()
        return pred()

    assert wait_until(step, timeout=timeout), "drain 未在超时内达成预期状态"


# ---------- 回灌结算 / 槽位聚合 / 回执按批齐写 ----------


def test_batch_receipt_written_when_all_slots_filled(center_factory):
    gate = threading.Event()
    entered = threading.Event()

    def runner(adapter, job):
        if job.hash == HASH_C:
            entered.set()
            gate.wait(timeout=5.0)  # 钉住前两条已回灌、第三条在途的中间态
        if job.hash == HASH_A:
            return TorrentTransferResult(HASH_A, TransferStatus.SUCCESS, "目标已受理", None)
        if job.hash == HASH_B:
            return TorrentTransferResult(HASH_B, TransferStatus.SUCCESS, "按勾选保留源种子", None)
        return TorrentTransferResult(
            HASH_C, TransferStatus.FAILED, "验证超时(10s 内目标未出现该种子)", TransferOutcomeCode.VERIFY_TIMEOUT
        )

    deletes, receipts = [], []
    center = center_factory(
        verify_runner=runner,
        delete_port=lambda src: deletes.append(src) or True,
        receipt_port=lambda cmd, payload: receipts.append((cmd, payload)),
    )
    center.submit_batch(
        "cmd-1", _target("目标A"),
        [_job(HASH_A, source_hash=SRC_A), _job(HASH_B, keep_source=True),
         _job(HASH_C)]
    )
    assert wait_until(lambda: center._results.qsize() == 2 and entered.is_set, timeout=3.0)
    center.drain()
    assert deletes == [SRC_A]  # 成功且未保留源的槽位才删源, 操作键 = source_hash
    assert receipts == []  # 批次未齐: 回执不写(按批齐写)

    gate.set()
    assert wait_until(lambda: center._results.qsize() == 1, timeout=3.0)
    center.drain()
    assert len(receipts) == 1
    cmd, payload = receipts[0]
    assert cmd == "cmd-1"
    assert payload == {
        "results":
            [
                {
                    "hash": HASH_A,
                    "状态": "成功",
                    "原因": "目标已受理"
                },
                {
                    "hash": HASH_B,
                    "状态": "成功",
                    "原因": "按勾选保留源种子"
                },
                {
                    "hash": HASH_C,
                    "状态": "失败",
                    "原因": "验证超时(10s 内目标未出现该种子)"
                },
            ],
        "summary": {
            "success": 2,
            "skipped": 0,
            "failed": 1
        },
        "target": "目标A",
    }
    assert deletes == [SRC_A]  # 失败槽位不删源
    assert center._batches == {}  # 批次结算完毕摘除


def test_multi_batches_fifo_coexistence(center_factory):
    order = []  # (adapter 标记, 作业 hash) 按处理序
    made = []

    def factory(target):
        adapter = _RecordingAdapter(target.name)
        made.append(target.name)
        return adapter

    receipts = []

    def runner(adapter, job):
        order.append((adapter.tag, job.hash))
        return _ok(job)

    center = center_factory(
        adapter_factory=factory,
        verify_runner=runner,
        delete_port=lambda src: True,
        receipt_port=lambda cmd, payload: receipts.append((cmd, payload)),
    )
    center.submit_batch("cmd-a", _target("目标A"), [_job(HASH_A), _job(HASH_B)])
    center.submit_batch("cmd-b", _target("目标B"), [_job(HASH_C), _job(HASH_D)])
    _drain_until(center, lambda: len(receipts) == 2)
    # 单 worker FIFO: 严格按递交顺序处理, 批内再按入参顺序(D3a: 批次=任务分组, 最终语义与
    # 今天命令串行等价 —— 两个批次各自完整结算, 谁也不吃掉谁)
    assert order == [("目标A", HASH_A), ("目标A", HASH_B), ("目标B", HASH_C), ("目标B", HASH_D)]
    assert dict(receipts)["cmd-a"]["target"] == "目标A"
    assert dict(receipts)["cmd-b"]["target"] == "目标B"
    assert dict(receipts)["cmd-a"]["summary"] == {"success": 2, "skipped": 0, "failed": 0}
    assert dict(receipts)["cmd-b"]["summary"] == {"success": 2, "skipped": 0, "failed": 0}
    assert made == ["目标A", "目标B"]  # adapter 批次级: 每批恰建一个
    assert center._batches == {}


# ---------- 关停(D4a) ----------


def test_stop_event_exits_promptly_without_join(center_factory):
    center = center_factory()
    center.start()
    assert wait_until(lambda: center._worker is not None and center._worker.is_alive(), timeout=3.0)
    center.stop()  # 实现面只置 Event, 不 join —— 调用即刻返回
    center._worker.join(timeout=2.0)  # 测试侧 join 仅用于断言「秒级内退出」
    assert not center._worker.is_alive()
    # 已停止后递交: 作业丢弃(WARNING), 不再记账(关停期新批次不入账; 在途语义见下例)
    assert center.submit_batch("cmd-x", _target(), [_job(HASH_A)]) == ""
    assert center._batches == {}


def test_stop_wakes_inflight_verify_poll_immediately(center_factory):
    made, receipts = [], []
    center = center_factory(
        # 默认 runner(真 orchestrator.run_verify_job)+ 恒查无目标: 验证在途轮询
        adapter_factory=lambda target: made.append(_ThreadRecordingAdapter(tag=target.name, find_sequence=[])) or made[
            -1],
        verify_timeout=2.0,
        receipt_port=lambda cmd, payload: receipts.append((cmd, payload)),
    )
    center.submit_batch("cmd-1", _target(), [_job(HASH_A)])
    # 验证早期就停(waited 仅 1~2 拍): 剩余轮询预算 ~2s(近百拍 Event.wait 节拍)
    assert wait_until(lambda: bool(made) and len(made[0].find_calls) >= 2, timeout=3.0)
    center.stop()
    # 即时醒: 剩余预算在 1s 内跑完退出 —— sleep 注入若退化成真 time.sleep, 退出要 ~2s, 本断言红
    assert wait_until(lambda: center._worker is not None and not center._worker.is_alive(), timeout=1.0)
    # 在途作业自然结算、结论仍回灌(stop 只保证队列余量不再处理, 见 stop() docstring)
    assert wait_until(lambda: center._results.qsize() == 1, timeout=3.0)
    center.drain()  # 主循环再 drain: 回执照写(是否落取决于是否再 drain)
    assert len(receipts) == 1
    assert receipts[0][1]["results"][0]["状态"] == "失败"
    assert "验证超时" in receipts[0][1]["results"][0]["原因"]


# ---------- worker 全异常兜底(§07 行 1 第一道) ----------


def test_seed_exception_synth_unexpected(center_factory):
    def runner(adapter, job):
        if job.hash == HASH_B:
            raise RuntimeError("boom")
        return _ok(job)

    deletes, receipts = [], []
    center = center_factory(
        verify_runner=runner,
        delete_port=lambda src: deletes.append(src) or True,
        receipt_port=lambda cmd, payload: receipts.append((cmd, payload)),
    )
    center.submit_batch("cmd-1", _target(), [_job(HASH_A), _job(HASH_B), _job(HASH_C)])
    _drain_until(center, lambda: len(receipts) == 1)
    results = receipts[0][1]["results"]
    assert results[0] == {"hash": HASH_A, "状态": "成功", "原因": ""}
    assert results[1]["hash"] == HASH_B and results[1]["状态"] == "失败"
    assert "未预期异常(boom)" in results[1]["原因"]
    assert results[2] == {"hash": HASH_C, "状态": "成功", "原因": ""}
    assert receipts[0][1]["summary"] == {"success": 2, "skipped": 0, "failed": 1}
    assert deletes == [HASH_A, HASH_C]  # 异常条目不删源, 其余照常


def test_loop_level_exception_synth_unexpected(center_factory, monkeypatch):
    center = center_factory(
        verify_runner=lambda adapter, job: _ok(job),
        delete_port=lambda src: True,
        receipt_port=lambda cmd, payload: receipts.append((cmd, payload)),
    )
    receipts = []
    orig_push = center._push_result
    pushes = []

    def flaky_push(batch_key, slot_idx, result):
        pushes.append(result.hash)
        if len(pushes) == 1:
            raise RuntimeError("push boom")  # 首次回灌失败 -> 循环级兜底接管
        return orig_push(batch_key, slot_idx, result)

    monkeypatch.setattr(center, "_push_result", flaky_push)
    center.submit_batch("cmd-1", _target(), [_job(HASH_A)])
    _drain_until(center, lambda: len(receipts) == 1)
    # 循环级兜底合成了 UNEXPECTED 结论(原文结论随 push 失败丢失, 合成面接管):
    assert len(pushes) == 2
    assert pushes[0] == HASH_A and pushes[1] == HASH_A
    result = receipts[0][1]["results"][0]
    assert result["hash"] == HASH_A and result["状态"] == "失败"
    assert "worker 循环级异常(push boom)" in result["原因"]
    assert center._batches == {}  # 批次照常齐写回执, 不挂死


# ---------- adapter 独占(D1) ----------


def test_adapter_exclusive_worker_thread_only(center_factory):
    made = []

    def factory(target):
        adapter = _ThreadRecordingAdapter(tag=target.name)
        made.append(adapter)
        return adapter

    receipts = []
    center = center_factory(adapter_factory=factory, receipt_port=lambda cmd, payload: receipts.append((cmd, payload)))
    center.submit_batch("cmd-a", _target("目标A"), [_job(HASH_A), _job(HASH_B)])
    _drain_until(center, lambda: len(receipts) == 1)
    worker_id = center._worker.ident
    assert worker_id is not None and worker_id != threading.get_ident()
    # 批次级: 同批两作业共享一个 adapter, 且工厂在 worker 线程被调
    assert len(made) == 1
    assert made[0].created_thread == worker_id
    # add/find 全部发生在 worker 线程 —— 主循环线程零 adapter 调用面(D1 隔离断言)
    assert [name for name, _ in made[0].call_threads] == ["add", "find", "add", "find"]
    assert all(tid == worker_id for _, tid in made[0].call_threads)
    # 下一批次换新 adapter(批次切换即换新, 旧引用交 GC)
    center.submit_batch("cmd-b", _target("目标B"), [_job(HASH_C)])
    _drain_until(center, lambda: len(receipts) == 2)
    assert len(made) == 2
    assert made[1].created_thread == worker_id
    assert made[0] is not made[1]


def test_adapter_factory_failure_retried_and_not_cached(center_factory):
    """守卫「工厂调用先于缓存改写」(runtime_transfer._adapter_for): 工厂异常不得被缓存

    回归回旧顺序(键先写、工厂后调)时, 批 B 首作业工厂抛异常会把缓存键写成 B 而
    adapter 仍是批 A 旧实例 —— B2 键相等即不重调, 静默复用 A 的 adapter 把种子 add 到
    错误目标; 本用例在旧顺序下: attempts 只有 2 次、A 的 adapter add_calls 变 3 条, 当场红。
    """
    attempts, created = [], []

    def factory(target):
        attempts.append(target.name)
        if target.name == "目标B" and len(attempts) == 2:
            raise RuntimeError("factory boom")  # 批 B 首作业的工厂调用失败(仅一次)
        adapter = _ThreadRecordingAdapter(tag=target.name)
        created.append(adapter)
        return adapter

    receipts = []
    center = center_factory(
        adapter_factory=factory,
        delete_port=lambda src: True,
        receipt_port=lambda cmd, payload: receipts.append((cmd, payload)),
    )
    center.submit_batch("cmd-a", _target("目标A"), [_job(HASH_A), _job(HASH_B)])
    center.submit_batch("cmd-b", _target("目标B"), [_job(HASH_C), _job(HASH_D)])
    _drain_until(center, lambda: len(receipts) == 2)
    # 工厂被调恰 3 次: A 一次 + B1 失败一次 + B2 重试成功一次; B2 拿到的是 B 的新实例
    assert attempts == ["目标A", "目标B", "目标B"]
    assert [a.tag for a in created] == ["目标A", "目标B"]
    # adapter 归属: 批 A 两作业跑在 A 实例, 批 B2 跑在 B 实例(旧顺序下 B2 会混进 A 实例)
    assert [f["fields"]["infohash"] for f in created[0].add_calls] == [HASH_A, HASH_B]
    assert [f["fields"]["infohash"] for f in created[1].add_calls] == [HASH_D]
    # 批 B 不挂死: B1 按单种子兜底结算 UNEXPECTED, B2 重试工厂后正常成功
    payload_b = dict(receipts)["cmd-b"]
    assert payload_b["results"][0]["hash"] == HASH_C
    assert payload_b["results"][0]["状态"] == "失败"
    assert "未预期异常(factory boom)" in payload_b["results"][0]["原因"]
    assert payload_b["results"][1] == {"hash": HASH_D, "状态": "成功", "原因": "目标已受理"}
    assert dict(receipts)["cmd-a"]["summary"] == {"success": 2, "skipped": 0, "failed": 0}
    assert center._batches == {}


# ---------- 默认 runner = orchestrator.run_verify_job ----------


def test_worker_runs_orchestrator_run_verify_job(center_factory):
    deletes, receipts = [], []
    made = []
    center = center_factory(
        adapter_factory=lambda target: made.append(_ThreadRecordingAdapter(tag=target.name)) or made[-1],
        delete_port=lambda src: deletes.append(src) or True,
        receipt_port=lambda cmd, payload: receipts.append((cmd, payload)),
    )
    job = _job(HASH_A, source_hash=SRC_A)
    center.submit_batch("cmd-1", _target(), [job])
    _drain_until(center, lambda: len(receipts) == 1)
    # 作业进结果出: worker 走的是 orchestrator.run_verify_job —— add 透传 plan 字段与
    # 跳检决策, 验证轮询查到正常态即 SUCCESS; 删源不在 worker 侧, 由 drain 按 source_hash 补
    adapter = made[0]
    assert len(adapter.add_calls) == 1
    assert adapter.add_calls[0]["fields"]["infohash"] == SRC_A
    assert adapter.add_calls[0]["skip_check"] is False
    assert adapter.find_calls == [SRC_A]  # 首轮查到, 无空转轮询
    # run_verify_job 的 SUCCESS 回执带 add 受理详情(与 run_batch 语义一致)
    assert receipts[0][1]["results"] == [{"hash": HASH_A, "状态": "成功", "原因": "目标已受理"}]
    assert deletes == [SRC_A]


# ---------- 同 hash 双批次反序交错(D3/R2 钉面) ----------


def test_same_hash_cross_batch_silent_delete(center_factory):
    deletes, receipts = [], []
    center = center_factory(
        verify_runner=lambda adapter, job: _ok(job),  # 异目标: 两批各自验证成功
        delete_port=lambda src: deletes.append(src) or True,  # 真实删源语义: 已删 hash 再删 = 静默成功
        receipt_port=lambda cmd, payload: receipts.append((cmd, payload)),
    )
    # 反序交错: 两批同 hash 异目标; 后结算者的删源命中「qB 对未知 hash 回 200 /
    # store.remove_torrent pop-None / _delete_source 返 True」的静默无操作口径
    center.submit_batch("cmd-a", _target("目标A"), [_job(HASH_A)])
    center.submit_batch("cmd-b", _target("目标B"), [_job(HASH_A)])
    _drain_until(center, lambda: len(receipts) == 2)
    assert deletes == [HASH_A, HASH_A]  # 两批都发起删源, 第二次是静默无操作
    payload_a, payload_b = dict(receipts)["cmd-a"], dict(receipts)["cmd-b"]
    assert payload_a["results"] == [{"hash": HASH_A, "状态": "成功", "原因": ""}]
    assert payload_b["results"] == [{"hash": HASH_A, "状态": "成功", "原因": ""}]
    # 已拍板 R2: 不做注记 —— 回执纯 SUCCESS, 无「源删除失败」也无任何交错说明
    assert all("源删除失败" not in r["原因"] for r in payload_a["results"] + payload_b["results"])
    assert center._batches == {}


# ---------- drain 逐结果异常隔离(§07 行 5) ----------


def test_drain_result_exception_isolated_and_slot_retried(center_factory):
    delete_calls = []

    def delete_port(src):
        delete_calls.append(src)
        if len(delete_calls) == 2:
            raise RuntimeError("delete boom")  # 中间结果的删源抛异常
        return True

    receipts = []
    center = center_factory(
        verify_runner=lambda adapter, job: _ok(job),
        delete_port=delete_port,
        receipt_port=lambda cmd, payload: receipts.append((cmd, payload)),
    )
    center.submit_batch("cmd-1", _target(), [_job(HASH_A), _job(HASH_B), _job(HASH_C)])
    assert wait_until(lambda: center._results.qsize() == 3, timeout=3.0)
    center.drain()  # 第一轮: A 结算 / B 删源抛异常留待重试 / C 结算(单条失败不影响其余)
    assert receipts == []  # 批次未齐
    assert delete_calls == [HASH_A, HASH_B, HASH_C]
    assert center._batches["cmd-1"].remaining == 1
    center.drain()  # 第二轮: 重试同一槽位, 端口已恢复 -> 批次齐写回执
    assert len(receipts) == 1
    assert receipts[0][1]["results"] == [
        {
            "hash": HASH_A,
            "状态": "成功",
            "原因": ""
        },
        {
            "hash": HASH_B,
            "状态": "成功",
            "原因": ""
        },  # 重试成功, 无失败注记
        {
            "hash": HASH_C,
            "状态": "成功",
            "原因": ""
        },
    ]
    assert delete_calls == [HASH_A, HASH_B, HASH_C, HASH_B]  # 重试按原槽位的 source_hash 再删一次
    assert center._batches == {}


def test_delete_port_false_appends_source_kept_note(center_factory):
    receipts = []
    center = center_factory(
        verify_runner=lambda adapter, job: _ok(job),
        delete_port=lambda src: False,  # 删源失败(端口契约: True 已删 / False 失败)
        receipt_port=lambda cmd, payload: receipts.append((cmd, payload)),
    )
    center.submit_batch("cmd-1", _target(), [_job(HASH_A)])
    _drain_until(center, lambda: len(receipts) == 1)
    result = receipts[0][1]["results"][0]
    assert result["hash"] == HASH_A
    assert result["状态"] == "成功"  # 删源失败不翻已成功的转移
    assert result["原因"] == "源删除失败, 源已保留"  # 注记与 run_batch 同口径(issue 26-11-03-0824)
    assert center._batches == {}


def test_receipt_port_failure_retried_next_drain(center_factory):
    receipt_calls = []

    def receipt_port(cmd, payload):
        receipt_calls.append((cmd, payload))
        if len(receipt_calls) == 1:
            raise RuntimeError("receipt boom")  # 首写抛异常

    center = center_factory(
        verify_runner=lambda adapter, job: _ok(job),
        delete_port=lambda src: True,
        receipt_port=receipt_port,
    )
    center.submit_batch("cmd-1", _target(), [_job(HASH_A)])
    _drain_until(center, lambda: len(receipt_calls) >= 2)
    assert receipt_calls[0][0] == "cmd-1"  # 首写抛异常
    assert receipt_calls[1][0] == "cmd-1"  # 下轮重试
    assert receipt_calls[1][1] == receipt_calls[0][1]  # payload 同形(单段终态形状不变)
    assert center._batches == {}  # 写成后批次摘除


# ---------- 超龄批次兜底(§07 行 1 最后防线) ----------


def test_aged_batch_force_settled_verify_timeout_with_warning(center_factory, fake_clock):
    gate = threading.Event()
    entered = threading.Event()

    def blocked_runner(adapter, job):
        entered.set()
        gate.wait(timeout=5.0)  # 模拟 worker 永不产出(线程假死 / 结论回灌全失败)
        return _ok(job)

    deletes, receipts = [], []
    center = center_factory(
        verify_runner=blocked_runner,
        delete_port=lambda src: deletes.append(src) or True,
        receipt_port=lambda cmd, payload: receipts.append((cmd, payload)),
        overage_seed_budget=40.0,  # 注入收紧预算窗口(生产默认按轮询口径自算)
        clock=fake_clock,
    )
    center.submit_batch("cmd-1", _target(), [_job(HASH_A)])
    assert wait_until(entered.is_set, timeout=3.0)  # 作业已在 worker 在途(结论永不到)
    fake_clock.advance(200.0)  # 全局无产出 200s > 预算 40 x 深度 1
    with capture_logs(LOG_NAME) as cap:
        center.drain()
    assert any("无结论产出" in m for m in cap.messages)  # WARNING 落日志
    assert len(receipts) == 1
    results = receipts[0][1]["results"]
    assert results[0]["hash"] == HASH_A and results[0]["状态"] == "失败"
    assert results[0]["原因"] == "验证超时(10s 内目标未出现该种子)"  # 与 orchestrator 超时口径同形
    assert receipts[0][1]["summary"] == {"success": 0, "skipped": 0, "failed": 1}
    assert deletes == []  # 兜底结算不删源(不成功路径不碰源)
    assert center._batches == {}
    gate.set()  # 清理: 放行假死的 runner(迟到结论会被下轮 drain 丢弃)


def test_progress_refresh_defers_overage_settle(center_factory, fake_clock):
    gate = threading.Event()

    def runner(adapter, job):
        if job.hash == HASH_B:
            gate.wait(timeout=5.0)  # 第二条在途: 钉住「批内尚有未结算槽位」的推进中间态
        return _ok(job)

    receipts = []
    center = center_factory(
        verify_runner=runner,
        delete_port=lambda src: True,
        receipt_port=lambda cmd, payload: receipts.append((cmd, payload)),
        overage_seed_budget=60.0,
        clock=fake_clock,
    )
    center.submit_batch("cmd-1", _target(), [_job(HASH_A), _job(HASH_B)])
    assert wait_until(lambda: center._results.qsize() == 1, timeout=3.0)  # 第一条已产出
    # 第一段: 无产出 50s < 预算 60 x 深度 1(首槽已在本轮填掉)—— 不触发;
    # drain 填槽刷新「最近产出」信号
    fake_clock.advance(50.0)
    center.drain()
    assert receipts == [] and center._batches["cmd-1"].remaining == 1
    # 第二段: 再无产出 50s —— 按全局信号 age=50s(被上一轮填槽刷新过)< 60 不触发;
    # 按「入队以来」计的旧口径 age=100s > 60 会误判 —— 本段钉住新信号
    fake_clock.advance(50.0)
    center.drain()
    assert receipts == [] and center._batches["cmd-1"].remaining == 1
    # 收尾: 第二条结论回灌, 批次照常齐写回执, 全程无兜底结算
    gate.set()
    assert wait_until(lambda: center._results.qsize() == 1, timeout=3.0)
    center.drain()
    assert len(receipts) == 1
    assert receipts[0][1]["results"] == [
        {
            "hash": HASH_A,
            "状态": "成功",
            "原因": ""
        },
        {
            "hash": HASH_B,
            "状态": "成功",
            "原因": ""
        },
    ]
    assert center._batches == {}


def test_idle_gap_reset_on_submit_after_drain(center_factory, fake_clock):
    """空闲后新批次不被立即兜底(修 1 分支一): 递交前容器无未结算工作 -> 判定起点重置

    空闲间隔不计入 stalled —— 否则距上次结论产出超过预算的下一次递交(默认预算 299s/槽位,
    两次转移命令间隔约 5 分钟即触发)会在首个 drain 被整体兜底成 VERIFY_TIMEOUT, worker
    随后产出的真实结论被当迟到丢弃, 违背宁晚勿早。
    """
    gate = threading.Event()

    def runner(adapter, job):
        if job.hash == HASH_C:
            gate.wait(timeout=5.0)  # 批 2 永不产出(卡死形态), 兜底与否只看信号起点
        return _ok(job)

    receipts = []
    center = center_factory(
        verify_runner=runner,
        delete_port=lambda src: True,
        receipt_port=lambda cmd, payload: receipts.append((cmd, payload)),
        overage_seed_budget=60.0,
        clock=fake_clock,
    )
    center.submit_batch("cmd-1", _target(), [_job(HASH_A)])  # 批 1 正常走完, 容器清空
    assert wait_until(lambda: center._results.qsize() == 1, timeout=3.0)
    center.drain()
    assert len(receipts) == 1 and center._batches == {}
    fake_clock.advance(300.0)  # 空闲远超预算 —— 不重置的话 stalled=300 > 60 会立即误兜底
    center.submit_batch("cmd-2", _target(), [_job(HASH_C)])  # 容器空 -> 判定起点重置为递交时刻
    center.drain()
    assert len(receipts) == 1  # 仍只有批 1 的回执
    assert center._batches["cmd-2"].remaining == 1  # 批 2 未被立即兜底
    fake_clock.advance(100.0)  # 递交后真无产出 100s > 60 —— 防挂死照样按期触发
    center.drain()
    assert len(receipts) == 2
    assert receipts[1][1]["results"][0]["状态"] == "失败"
    assert "验证超时" in receipts[1][1]["results"][0]["原因"]
    assert center._batches == {}
    gate.set()  # 清理: 放行卡死的 runner(迟到结论会被下轮 drain 丢弃)


def test_submit_second_batch_keeps_waiting_start(center_factory, fake_clock):
    """容器已有未结算工作时不重置判定起点(修 1 分支二): 旧槽位的等待起点不变

    批 1 在途无产出 50s(未过单批预算 30)后递交批 2(不触发重置), 再等 20s 后全局无产出
    70s > 预算 30 x 深度 2 = 60 -> 兜底触发; 若递交被错误地重置起点, stalled 只有 20s,
    兜底不会出现 —— 本用例当场红。
    """
    gate1, gate2 = threading.Event(), threading.Event()

    def runner(adapter, job):
        if job.hash == HASH_A:
            gate1.wait(timeout=5.0)
        else:
            gate2.wait(timeout=5.0)
        return _ok(job)

    receipts = []
    center = center_factory(
        verify_runner=runner,
        delete_port=lambda src: True,
        receipt_port=lambda cmd, payload: receipts.append((cmd, payload)),
        overage_seed_budget=30.0,
        clock=fake_clock,
    )
    center.submit_batch("cmd-1", _target(), [_job(HASH_A)])  # 起点重置为 t0(容器原本为空)
    fake_clock.advance(50.0)  # 刻意不 drain: 否则批 1 会在递交批 2 前就被单批兜底(50 > 30)
    center.submit_batch("cmd-2", _target(), [_job(HASH_C)])  # 容器有未结算 -> 不重置
    fake_clock.advance(20.0)
    center.drain()  # stalled = 70(自 t0)> 预算 30 x 深度 2 = 60 -> 两批一起兜底
    assert len(receipts) == 2
    assert all(r[1]["results"][0]["状态"] == "失败" for r in receipts)
    assert all("验证超时" in r[1]["results"][0]["原因"] for r in receipts)
    assert center._batches == {}
    gate1.set()  # 清理: 放行两个卡死的 runner
    gate2.set()


# ---------- S2 默认端口占位语义 ----------


def test_unwired_default_ports_placeholders(center_factory):
    center = center_factory(verify_runner=lambda adapter, job: _ok(job))
    center.submit_batch("cmd-1", _target(), [_job(HASH_A)])
    with capture_logs(LOG_NAME) as cap:
        _drain_until(center, lambda: center._batches == {})
    # 占位回执端口不写回执(无 receipts 可取) —— 语义经 WARNING + 容器摘除断言
    assert any("删源端口为构造默认占位" in m for m in cap.messages)
    assert any("回执端口为构造默认占位" in m for m in cap.messages)
    assert center._batches == {}


# ---------- API 契约 ----------


def test_submit_empty_jobs_raises(center_factory):
    center = center_factory()
    with pytest.raises(ValueError):
        center.submit_batch("cmd-1", _target(), [])
    # 全已结算条目(无验证作业)同面 fail-fast: 应走命令面快路径, 不入中心(判据单点在命令面)
    with pytest.raises(ValueError):
        center.submit_batch(
            "cmd-1", _target(),
            [TorrentTransferResult(HASH_A, TransferStatus.SKIPPED, "目标已存在", TransferOutcomeCode.DUPLICATE)]
        )


# ---------- S3 混列递交(已结算结果作槽位初值) ----------


def test_submit_mixed_entries_slots_initial_values(center_factory):
    deletes, receipts = [], []
    center = center_factory(
        verify_runner=lambda adapter, job: _ok(job),
        delete_port=lambda src: deletes.append(src) or True,
        receipt_port=lambda cmd, payload: receipts.append((cmd, payload)),
    )
    settled_skip = TorrentTransferResult(HASH_A, TransferStatus.SKIPPED, "目标已存在", TransferOutcomeCode.DUPLICATE)
    settled_fail = TorrentTransferResult(
        HASH_C, TransferStatus.FAILED, "源 .torrent 导出失败", TransferOutcomeCode.EXPORT_FAILED
    )
    with capture_logs(LOG_NAME) as cap:
        center.submit_batch("cmd-1", _target("目标A"), [settled_skip, _job(HASH_B, source_hash=SRC_B), settled_fail])
    assert any("生产段已结算 2 个随槽位初值" in m for m in cap.messages), "递交日志带已结算槽位初值计数"
    batch = center._batches["cmd-1"]
    assert batch.remaining == 1, "剩余计数只算验证作业槽位"
    # 槽位按入参顺序: 已结算结果作初值占位, 验证作业槽位待结论
    assert batch.slots[0].result is settled_skip and batch.slots[2].result is settled_fail
    assert batch.slots[1].result is None
    # 已结算槽位永不删源(未验证成功不碰源, 不变量 2): keep_source 闸复用
    assert batch.slots[0].keep_source and batch.slots[2].keep_source
    assert batch.slots[0].source_hash == "" and batch.slots[2].source_hash == ""
    assert not batch.slots[1].keep_source
    _drain_until(center, lambda: len(receipts) == 1)
    payload = receipts[0][1]
    assert [r["hash"] for r in payload["results"]] == [HASH_A, HASH_B, HASH_C], "truth 按入参顺序(D5)"
    assert payload["summary"] == {"success": 1, "skipped": 1, "failed": 1}
    assert deletes == [SRC_B], "只有验证成功且未保留源的槽位删源"


def test_drain_returns_true_on_successful_delete(center_factory):
    deletes, receipts = [], []
    center = center_factory(
        verify_runner=lambda adapter, job: _ok(job),
        delete_port=lambda src: deletes.append(src) or (len(deletes) > 1),  # 首次删源失败, 之后成功
        receipt_port=lambda cmd, payload: receipts.append((cmd, payload)),
    )
    center.submit_batch("cmd-a", _target(), [_job(HASH_A)])
    center.submit_batch("cmd-b", _target(), [_job(HASH_B)])
    assert wait_until(lambda: center._results.qsize() == 2, timeout=3.0)
    assert center.drain() is True, "删源成功轮: cmd_changed_state 并入面"
    assert len(receipts) == 2
    assert center.drain() is False, "纯回执轮(无删源): False"
    # 删源失败(端口 False)轮: 不并入(未改 qB 种子状态) —— 先清容器再造一轮删源失败
    center.submit_batch("cmd-c", _target(), [_job(HASH_C)])
    assert wait_until(lambda: center._results.qsize() == 1, timeout=3.0)
    deletes.clear()
    assert center.drain() is False, "删源失败轮(端口 False): 不算改状态"
    assert deletes == [HASH_C]
    assert len(receipts) == 3  # 删源失败不翻已成功的转移, 回执照写(注记面见既有用例)


# ---------- S4 关停: 丢弃删除意图 + 丢弃清单 WARNING(D4a/§07 行 4) ----------


def test_stop_discards_delete_intent_with_warning_no_delete_after_stop(center_factory):
    deletes, receipts = [], []
    center = center_factory(
        verify_runner=lambda adapter, job: _ok(job),
        delete_port=lambda src: deletes.append(src) or True,
        receipt_port=lambda cmd, payload: receipts.append((cmd, payload)),
    )
    center.submit_batch("cmd-1", _target(), [_job(HASH_A, source_hash=SRC_A)])
    # §07 行 4 触发窗口: 验证成功(结论已回灌)、drain 删源前 stop
    assert wait_until(lambda: center._results.qsize() == 1, timeout=3.0)
    with capture_logs(LOG_NAME) as cap:
        center.stop()
    assert any("关停丢弃删除意图" in m and HASH_A in m and "目标已建, 源未删, 请手动处置" in m for m in cap.messages)
    assert any("关停共丢弃删除意图 1 条" in m for m in cap.messages), "合计行落日志"
    assert deletes == [], "stop 本身绝不删源(丢弃删除意图)"
    # stop 后任何路径不得删源(源种子零误删守阵): drain 重试/回灌消费全走一遍
    center.drain()
    center.drain()
    assert deletes == []
    # 槽位照常填、回执照常齐(是否落取决于是否再 drain)
    assert len(receipts) == 1
    assert receipts[0][1]["results"][0] == {"hash": HASH_A, "状态": "成功", "原因": ""}
    assert center._batches == {}


def test_stop_discard_list_covers_delete_retry_entry(center_factory):
    delete_calls, receipts = [], []

    def delete_port(src):
        delete_calls.append(src)
        raise RuntimeError("delete boom")  # 删源端口抛异常 -> 进重试列表(删源未完成)

    center = center_factory(
        verify_runner=lambda adapter, job: _ok(job),
        delete_port=delete_port,
        receipt_port=lambda cmd, payload: receipts.append((cmd, payload)),
    )
    center.submit_batch("cmd-1", _target(), [_job(HASH_A)])
    assert wait_until(lambda: center._results.qsize() == 1, timeout=3.0)
    center.drain()  # 第一轮: 删源抛异常, 槽位进重试列表
    assert center._batches["cmd-1"].retry and receipts == []
    with capture_logs(LOG_NAME) as cap:
        center.stop()
    assert any("关停丢弃删除意图" in m and HASH_A in m and "目标已建, 源未删, 请手动处置" in m for m in cap.messages), "删源重试中的槽位在清单"
    center.drain()  # stop 后重试: 删除意图已丢弃, 不再删源
    assert delete_calls == [HASH_A], "重试不再调删源端口"
    assert len(receipts) == 1 and center._batches == {}


def test_stop_discard_list_covers_delete_port_false_slot(center_factory):
    """丢弃清单 face-1(容器槽位已填且删源端口返 False): 源删除失败->源已保留算「删源未完成」,
    stop 照常告警; 批次留容器(其余槽位在途)是该面的可枚举前提"""
    gate = threading.Event()
    deletes, receipts = [], []

    def runner(adapter, job):
        if job.hash == HASH_B:
            gate.wait(timeout=5.0)  # 第二槽位在途: 批次留容器, 回执未写
        return _ok(job)

    center = center_factory(
        verify_runner=runner,
        delete_port=lambda src: deletes.append(src) or False,  # 删源恒失败(端口契约: False)
        receipt_port=lambda cmd, payload: receipts.append((cmd, payload)),
    )
    center.submit_batch("cmd-1", _target(), [_job(HASH_A), _job(HASH_B)])
    assert wait_until(lambda: center._results.qsize() == 1, timeout=3.0)
    center.drain()  # A: 删源失败 -> 填槽(带注记); B 在途 -> 批次留容器
    assert receipts == [] and center._batches["cmd-1"].remaining == 1
    with capture_logs(LOG_NAME) as cap:
        center.stop()
    assert any("关停丢弃删除意图" in m and HASH_A in m and "目标已建, 源未删, 请手动处置" in m for m in cap.messages)
    assert any("关停共丢弃删除意图 1 条" in m for m in cap.messages), "合计行计数 = 1(在途的 B 不可考不误报)"
    assert deletes == [HASH_A], "删源只尝试过一次(stop 不重试删源)"
    gate.set()  # 清理 + B 结论 stop 后回灌: 槽位照填(删源跳过), 批次照常齐写回执
    assert wait_until(lambda: center._results.qsize() == 1, timeout=3.0)
    center.drain()
    assert len(receipts) == 1
    assert receipts[0][1]["results"][0]["原因"] == "源删除失败, 源已保留"
    assert deletes == [HASH_A], "stop 后 drain 不再删源(删除意图已丢弃)"


def test_stop_discard_list_covers_late_success_with_batch_gone(center_factory, fake_clock):
    """丢弃清单 face-3 补形(批次已被超龄兜底结算摘除、SUCCESS 结论仍在队列): 批次不在
    容器不拦告警 —— keep_source 不可考, SUCCESS 保守告警(宁多勿漏, 双份做种残留不得
    逃过 §07 行 4)"""
    gate = threading.Event()
    entered = threading.Event()

    def blocked_runner(adapter, job):
        entered.set()
        gate.wait(timeout=5.0)  # worker 永不产出(病理性形态: 超龄兜底最后防线接管)
        return _ok(job)  # 放行后真实结论 SUCCESS(验证实际已成功)

    deletes, receipts = [], []
    center = center_factory(
        verify_runner=blocked_runner,
        delete_port=lambda src: deletes.append(src) or True,
        receipt_port=lambda cmd, payload: receipts.append((cmd, payload)),
        overage_seed_budget=40.0,
        clock=fake_clock,
    )
    center.submit_batch("cmd-1", _target(), [_job(HASH_A)])
    assert wait_until(entered.is_set, timeout=3.0)
    fake_clock.advance(200.0)
    center.drain()  # 超龄兜底: 槽位按 VERIFY_TIMEOUT 结算, 回执写出后批次摘除
    assert len(receipts) == 1 and center._batches == {}
    gate.set()  # 真实结论(SUCCESS)迟回灌
    assert wait_until(lambda: center._results.qsize() == 1, timeout=3.0)
    with capture_logs(LOG_NAME) as cap:
        center.stop()
    assert any(
        "关停丢弃删除意图" in m and HASH_A in m and "目标已建, 源未删, 请手动处置" in m for m in cap.messages
    ), "批次已摘除不拦告警(keep_source 不可考, 保守口径)"
    assert any("关停共丢弃删除意图 1 条" in m for m in cap.messages)
    assert deletes == [], "超龄兜底与 stop 都不删源"


def test_stop_idempotent_discard_list_warned_once(center_factory):
    """stop 幂等(重复调用无副作用): 丢弃清单 WARNING 首次 stop 落一次, 重复 stop 不再枚举再记"""
    deletes, receipts = [], []
    center = center_factory(
        verify_runner=lambda adapter, job: _ok(job),
        delete_port=lambda src: deletes.append(src) or True,
        receipt_port=lambda cmd, payload: receipts.append((cmd, payload)),
    )
    center.submit_batch("cmd-1", _target(), [_job(HASH_A)])
    assert wait_until(lambda: center._results.qsize() == 1, timeout=3.0)
    with capture_logs(LOG_NAME) as cap:
        center.stop()
        center.stop()  # 重复 stop: warned-once
    assert sum(1 for m in cap.messages if "关停丢弃删除意图" in m) == 1, "逐条 WARNING 恰一次"
    assert sum(1 for m in cap.messages if "关停共丢弃删除意图" in m) == 1, "合计行恰一次"


def test_submit_success_settled_entry_raises(center_factory):
    """已结算条目恒非 SUCCESS(生产段终态都是未验证成功面): SUCCESS 条目作槽位初值会被
    keep_source 闸静默禁删源 —— fail-fast 把该不变量钉成机器可查"""
    center = center_factory()
    with pytest.raises(ValueError):
        center.submit_batch(
            "cmd-1",
            _target(),
            [TorrentTransferResult(HASH_A, TransferStatus.SUCCESS, "", None),
             _job(HASH_B)],
        )


def test_stop_submit_discard_and_worker_lifecycle_logs(center_factory):
    receipts = []
    center = center_factory(
        verify_runner=lambda adapter, job: _ok(job),
        delete_port=lambda src: True,
        receipt_port=lambda cmd, payload: receipts.append((cmd, payload)),
    )
    with capture_logs(LOG_NAME) as cap:
        center.submit_batch("cmd-1", _target(), [_job(HASH_A), _job(HASH_B)])
        _drain_until(center, lambda: len(receipts) == 1)
        center.stop()
        assert center.submit_batch("cmd-2", _target(), [_job(HASH_C)]) == ""  # 已停止后递交: 丢弃
    assert any("批次已递交后台验证 cmd=cmd-1(验证作业 2 个)" in m for m in cap.messages), "递交日志(批次大小)"
    assert any("批次结算完成 cmd=cmd-1 target=目标A: 成功 2 / 跳过 0 / 失败 0" in m for m in cap.messages), "结算日志(批次口径)"
    assert any("批次作业丢弃" in m and "cmd-2" in m for m in cap.messages), "递交丢弃日志"


# ---------- runtime 接线 ----------


def test_runtime_wiring_center_and_consume_tail_drain():
    runtime = WebUIRuntime(SimpleNamespace(_web_command_handlers=lambda: {}))
    assert isinstance(runtime.transfer_center, TransferVerifyCenter)
    drain_calls = []
    runtime.transfer_center = SimpleNamespace(drain=lambda: drain_calls.append(1))
    runtime.consume_commands()  # 空命令队列轮次: 命令消费零条, 尾部 drain 照跑(D6)
    assert drain_calls == [1]
