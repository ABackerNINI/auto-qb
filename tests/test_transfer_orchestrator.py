"""test_transfer_orchestrator 测试计划: 转移执行层编排器(状态门/跳检/验证/删源, 全 mock 不联网)

## 测试计划(每个测试函数一条)
- test_gate_blocks_download_pipeline_states: 7 个下载管线态逐条拦截 -> 跳过 + BLOCKED_STATE, 不发起添加不删源
- test_gate_blocks_missing_files: 源 missingFiles -> 跳过 + MISSING_FILES
- test_gate_blocks_unknown_state: 白名单外状态(moving/空)保守拦截 -> BLOCKED_STATE
- test_gate_allows_up_family: UP 家族 7 态全放行 -> 走到添加且删除源
- test_gate_allows_paused_dl_states: pausedDL/stoppedDL 放行(未完成走非跳检通路, skip_check=False)
- test_gate_allows_error_state_by_progress: error 态按完成度走通用规则(100% 放行)
- test_skip_check_degrades_incomplete: 未完成 + 跳检开 -> 降级 skip_check=False 且结果注明
- test_skip_check_kept_for_complete: progress==1.0 且跳检开 -> skip_check=True
- test_skip_check_disabled_always_false: 跳检关 -> 完成与否恒 skip_check=False 且无降级注明
- test_verify_success_on_hash_appearance: 第 N 轮才查到 + 正常态 -> 成功并删源(轮询生效, 期间有 sleep)
- test_verify_timeout_keeps_source: 目标恒查无 -> 验证超时失败, 源保留, sleep 按 poll_interval 节拍
- test_verify_target_error_state: 目标 error / missingFiles 态 -> TARGET_ERROR 失败, 源保留
- test_verify_unsupported_adapter: 适配器无 find_torrent 扩展点 -> VERIFY_UNSUPPORTED, 不删源
- test_duplicate_skips_and_keeps_source: 已存在(SKIPPED) -> 结果跳过 + DUPLICATE, 源保留
- test_delete_source_only_removes_task: 删源调用恒 delete_files=False(只删任务不删文件)
- test_keep_source_flag_skips_delete: 仅本次保留源种子 -> 不删源且原因注明
- test_path_map_first_rule_wins: 两条规则都命中前缀 -> 只第一条生效
- test_path_map_no_match_or_empty_passthrough: 空映射/无命中 -> 保存路径原样
- test_batch_continues_after_skipped_seed: [成功, 被门拦, 成功] -> 3 条结果顺序完整
- test_batch_unexpected_exception_does_not_interrupt: 单种子添加抛未预期异常 -> 本条失败其余照常
- test_after_state_paused_pauses_before_delete: after_state=paused -> 暂停目标且发生在删源之前
- test_after_state_paused_failure_noted: 暂停失败 -> 仍成功但原因注明
- test_after_state_keep_never_pauses: 默认 keep -> 不调用暂停
- test_export_failure_keeps_source: export 抛异常 -> EXPORT_FAILED, 不发起添加不删源
- test_source_read_failure: maindata 查无/查询故障 -> SOURCE_READ_FAILED, 不删源
- test_field_collection_respects_switches: 字段开关逐键生效(关的键不下发), save_path 锁死恒采集, infohash 探针在
- test_field_collection_maps_maindata_keys: 字段键 -> 源 maindata 键映射(ratio_limit/dl_limit 等)
- test_result_receipt_shape: to_receipt() = {hash, 状态(中文三态), 原因}; label 单点
- test_empty_hashes_skips_adapter: 空 hashes -> 空结果且不实例化适配器
- test_auth_failure_classified: 添加失败原因含"登录失败" -> AUTH_FAILED; 其余 -> ADD_FAILED
"""
from __future__ import annotations

from typing import Dict, List, Optional

import pytest

import auto_qb.transfer.orchestrator as orchestrator_module
from auto_qb.config import TRANSFER_FIELD_KEYS, TransferPathMapEntry, TransferTargetConfig
from auto_qb.transfer.adapters import AddResult
from auto_qb.transfer.orchestrator import (
    TorrentTransferResult,
    TransferOutcomeCode,
    TransferOrchestrator,
    TransferStatus,
)

HASH_A = "a" * 40
HASH_B = "b" * 40
HASH_C = "c" * 40
EXPORT_BYTES = b"torrent-bytes"

# ---------- 替身(不联网) ----------


def _make_target(**overrides) -> TransferTargetConfig:
    values = dict(
        name="目标A",
        type="qb",
        base_url="http://127.0.0.1:8081",
        username="user",
        password="pass",
        enabled=True,
    )
    values.update(overrides)
    return TransferTargetConfig(**values)


def _source_record(hash_: str = HASH_A, state: str = "stalledUP", progress: float = 1.0, **extra) -> Dict[str, object]:
    record: Dict[str, object] = {
        "hash": hash_,
        "state": state,
        "progress": progress,
        "save_path": "D:/data/Torrents",
        "category": "tv",
        "tags": ["zE01", "grp"],
        "ratio_limit": 2.0,
        "seeding_time_limit": 0,
        "up_limit": -1,
        "dl_limit": -1,
        "super_seeding": False,
    }
    record.update(extra)
    return record


class _FakeQbApi:
    """主 qB QbApi 替身: 只实现 orchestrator 消费的三个方法(读源/导出/删源)"""
    def __init__(self, torrents: Optional[Dict[str, Dict[str, object]]] = None, export_error=None, info_error=None):
        self.torrents = dict(torrents or {})
        self.export_error = export_error
        self.info_error = info_error
        self.deletions: List[tuple] = []  # (torrent_hashes, delete_files)

    def torrents_info(self, torrent_hashes=None, **kwargs):
        if self.info_error is not None:
            raise self.info_error
        record = self.torrents.get(str(torrent_hashes).lower())
        return [record] if record is not None else []

    def torrents_export(self, torrent_hash, **kwargs):
        if self.export_error is not None:
            raise self.export_error
        return EXPORT_BYTES

    def torrents_delete(self, torrent_hashes=None, delete_files=False, **kwargs):
        self.deletions.append((torrent_hashes, delete_files))


class _FakeAdapter:
    """目标适配器替身: 脚本化 add 结果 / find_torrent 出现序列 / 暂停成败"""
    def __init__(
        self,
        add_results: Optional[List] = None,
        find_sequence: Optional[List] = None,
        pause_ok: bool = True,
        add_error: Optional[Exception] = None,
        with_find: bool = True,
    ):
        self.add_calls: List[Dict[str, object]] = []
        self.pause_calls: List[str] = []
        self.find_calls: List[str] = []
        self._add_results = list(add_results or [])
        self._add_error = add_error
        self._find_sequence = list(find_sequence) if find_sequence is not None else None
        self._pause_ok = pause_ok
        if with_find:
            self.find_torrent = self._find_torrent  # 无该属性 = 不支持验证(VERIFY_UNSUPPORTED 用例)

    def capabilities(self) -> set:
        return set(TRANSFER_FIELD_KEYS)

    def add_torrent(self, data: bytes, fields: Dict[str, object], skip_check: bool) -> AddResult:
        self.add_calls.append({"data": data, "fields": dict(fields), "skip_check": skip_check})
        if self._add_error is not None:
            raise self._add_error
        if self._add_results:
            return self._add_results.pop(0)
        return AddResult.added("目标已受理", infohash=str(fields.get("infohash", "")))

    def _find_torrent(self, infohash: str):
        self.find_calls.append(infohash)
        if self._find_sequence is None:
            return {"hash": infohash, "state": "stoppedUP"}
        if not self._find_sequence:
            return None
        return self._find_sequence.pop(0)

    def pause_torrent(self, infohash: str) -> bool:
        self.pause_calls.append(infohash)
        return self._pause_ok


def _run(
    monkeypatch,
    qb_api: _FakeQbApi,
    target: TransferTargetConfig,
    hashes,
    keep_source=False,
    adapter=None,
    sleeps=None
):
    """构造编排器 + 注入替身 adapter, 跑一批; sleeps 列表收集验证轮询的 sleep 节拍"""
    fake_adapter = adapter if adapter is not None else _FakeAdapter()
    monkeypatch.setattr(orchestrator_module, "create_adapter", lambda target: fake_adapter)
    orchestrator = TransferOrchestrator(
        qb_api,
        sleep=(lambda s: sleeps.append(s)) if sleeps is not None else (lambda s: None),
        verify_timeout=1.0,
        poll_interval=0.25,
    )
    results = orchestrator.run_batch(target, hashes, keep_source=keep_source)
    return results, fake_adapter


def _full_torrent(h: str = HASH_A, **extra) -> Dict[str, object]:
    return _source_record(hash_=h, **extra)


def _added_with_found(find_state: str = "stoppedUP") -> tuple:
    """默认可成功的一批: qb 有源记录 + adapter 默认 ADDED + 目标立即查得正常态"""
    return _FakeQbApi(torrents={HASH_A.lower(): _full_torrent()}
                     ), _FakeAdapter(find_sequence=[{
                         "hash": HASH_A,
                         "state": find_state
                     }])


# ---------- 状态门矩阵 ----------


@pytest.mark.parametrize(
    "state", ["metaDL", "downloading", "stalledDL", "queuedDL", "checkingDL", "allocating", "forcedDL"]
)
def test_gate_blocks_download_pipeline_states(monkeypatch, state):
    qb = _FakeQbApi(torrents={HASH_A.lower(): _full_torrent(state=state)})
    results, adapter = _run(monkeypatch, qb, _make_target(), [HASH_A])
    assert len(results) == 1
    result = results[0]
    assert result.status is TransferStatus.SKIPPED
    assert result.code is TransferOutcomeCode.BLOCKED_STATE
    assert state in result.reason
    assert adapter.add_calls == []  # 不发起添加
    assert qb.deletions == []  # 不碰源


def test_gate_blocks_missing_files(monkeypatch):
    qb = _FakeQbApi(torrents={HASH_A.lower(): _full_torrent(state="missingFiles")})
    results, adapter = _run(monkeypatch, qb, _make_target(), [HASH_A])
    assert results[0].status is TransferStatus.SKIPPED
    assert results[0].code is TransferOutcomeCode.MISSING_FILES
    assert adapter.add_calls == [] and qb.deletions == []


@pytest.mark.parametrize("state", ["moving", ""])
def test_gate_blocks_unknown_state(monkeypatch, state):
    qb = _FakeQbApi(torrents={HASH_A.lower(): _full_torrent(state=state)})
    results, adapter = _run(monkeypatch, qb, _make_target(), [HASH_A])
    assert results[0].status is TransferStatus.SKIPPED
    assert results[0].code is TransferOutcomeCode.BLOCKED_STATE
    assert adapter.add_calls == []


@pytest.mark.parametrize(
    "state", ["uploading", "stalledUP", "pausedUP", "stoppedUP", "queuedUP", "forcedUP", "checkingUP"]
)
def test_gate_allows_up_family(monkeypatch, state):
    qb = _FakeQbApi(torrents={HASH_A.lower(): _full_torrent(state=state)})
    adapter = _FakeAdapter(find_sequence=[{"hash": HASH_A, "state": "stoppedUP"}])
    results, _ = _run(monkeypatch, qb, _make_target(), [HASH_A], adapter=adapter)
    assert results[0].status is TransferStatus.SUCCESS
    assert len(adapter.add_calls) == 1
    assert qb.deletions == [(HASH_A, False)]


@pytest.mark.parametrize("state", ["pausedDL", "stoppedDL"])
def test_gate_allows_paused_dl_states(monkeypatch, state):
    # 未完成但暂停: 放行, 且因未完成被降级为校验添加(D8)
    qb = _FakeQbApi(torrents={HASH_A.lower(): _full_torrent(state=state, progress=0.5)})
    adapter = _FakeAdapter(find_sequence=[{"hash": HASH_A, "state": "stoppedUP"}])
    results, _ = _run(monkeypatch, qb, _make_target(), [HASH_A], adapter=adapter)
    assert results[0].status is TransferStatus.SUCCESS
    assert adapter.add_calls[0]["skip_check"] is False
    assert "未完成, 已自动改为校验添加" in results[0].reason


def test_gate_allows_error_state_by_progress(monkeypatch):
    qb = _FakeQbApi(torrents={HASH_A.lower(): _full_torrent(state="error", progress=1.0)})
    adapter = _FakeAdapter(find_sequence=[{"hash": HASH_A, "state": "stoppedUP"}])
    results, _ = _run(monkeypatch, qb, _make_target(), [HASH_A], adapter=adapter)
    assert results[0].status is TransferStatus.SUCCESS
    assert len(adapter.add_calls) == 1


# ---------- 跳检决策 ----------


def test_skip_check_degrades_incomplete(monkeypatch):
    qb = _FakeQbApi(torrents={HASH_A.lower(): _full_torrent(progress=0.5)})
    adapter = _FakeAdapter(find_sequence=[{"hash": HASH_A, "state": "stoppedUP"}])
    results, _ = _run(monkeypatch, qb, _make_target(), [HASH_A], adapter=adapter)
    assert adapter.add_calls[0]["skip_check"] is False
    assert "未完成, 已自动改为校验添加" in results[0].reason


def test_skip_check_kept_for_complete(monkeypatch):
    qb = _FakeQbApi(torrents={HASH_A.lower(): _full_torrent(progress=1.0)})
    adapter = _FakeAdapter(find_sequence=[{"hash": HASH_A, "state": "stoppedUP"}])
    results, _ = _run(monkeypatch, qb, _make_target(), [HASH_A], adapter=adapter)
    assert adapter.add_calls[0]["skip_check"] is True
    assert "未完成" not in results[0].reason


@pytest.mark.parametrize("progress", [1.0, 0.5])
def test_skip_check_disabled_always_false(monkeypatch, progress):
    qb = _FakeQbApi(torrents={HASH_A.lower(): _full_torrent(progress=progress)})
    adapter = _FakeAdapter(find_sequence=[{"hash": HASH_A, "state": "stoppedUP"}])
    results, _ = _run(monkeypatch, qb, _make_target(skip_check=False), [HASH_A], adapter=adapter)
    assert adapter.add_calls[0]["skip_check"] is False
    assert "未完成" not in results[0].reason


# ---------- 验证轮询三态 ----------


def test_verify_success_on_hash_appearance(monkeypatch):
    # 前 3 轮查无, 第 4 轮出现且正常态 -> 成功并删源; 期间按 poll_interval 节拍 sleep
    qb = _FakeQbApi(torrents={HASH_A.lower(): _full_torrent()})
    adapter = _FakeAdapter(find_sequence=[None, None, None, {"hash": HASH_A, "state": "stoppedUP"}], )
    sleeps: List[float] = []
    results, _ = _run(monkeypatch, qb, _make_target(), [HASH_A], adapter=adapter, sleeps=sleeps)
    assert results[0].status is TransferStatus.SUCCESS
    assert qb.deletions == [(HASH_A, False)]
    assert sleeps == [0.25] * 3


def test_verify_timeout_keeps_source(monkeypatch):
    qb = _FakeQbApi(torrents={HASH_A.lower(): _full_torrent()})
    adapter = _FakeAdapter(find_sequence=[])  # 恒查无
    sleeps: List[float] = []
    results, _ = _run(monkeypatch, qb, _make_target(), [HASH_A], adapter=adapter, sleeps=sleeps)
    assert results[0].status is TransferStatus.FAILED
    assert results[0].code is TransferOutcomeCode.VERIFY_TIMEOUT
    assert "超时" in results[0].reason and "源已保留" in results[0].reason
    assert qb.deletions == []  # 源保留
    # verify_timeout=1.0 / poll_interval=0.25 -> 恰 4 拍后判超时(不真等)
    assert sleeps == [0.25] * 4


@pytest.mark.parametrize("state", ["error", "missingFiles"])
def test_verify_target_error_state(monkeypatch, state):
    qb = _FakeQbApi(torrents={HASH_A.lower(): _full_torrent()})
    adapter = _FakeAdapter(find_sequence=[{"hash": HASH_A, "state": state}])
    results, _ = _run(monkeypatch, qb, _make_target(), [HASH_A], adapter=adapter)
    assert results[0].status is TransferStatus.FAILED
    assert results[0].code is TransferOutcomeCode.TARGET_ERROR
    assert state in results[0].reason
    assert qb.deletions == []


def test_verify_unsupported_adapter(monkeypatch):
    qb = _FakeQbApi(torrents={HASH_A.lower(): _full_torrent()})
    adapter = _FakeAdapter(with_find=False)  # 无 find_torrent 扩展点
    results, _ = _run(monkeypatch, qb, _make_target(), [HASH_A], adapter=adapter)
    assert results[0].status is TransferStatus.FAILED
    assert results[0].code is TransferOutcomeCode.VERIFY_UNSUPPORTED
    assert qb.deletions == []  # 绝不无验证删源


# ---------- 已存在 / 删源语义 ----------


def test_duplicate_skips_and_keeps_source(monkeypatch):
    qb = _FakeQbApi(torrents={HASH_A.lower(): _full_torrent()})
    adapter = _FakeAdapter(add_results=[AddResult.skipped("目标已存在(响应: Fails.)")])
    results, _ = _run(monkeypatch, qb, _make_target(), [HASH_A], adapter=adapter)
    assert results[0].status is TransferStatus.SKIPPED
    assert results[0].code is TransferOutcomeCode.DUPLICATE
    assert "源已保留" in results[0].reason
    assert qb.deletions == []


def test_delete_source_only_removes_task(monkeypatch):
    qb = _FakeQbApi(torrents={HASH_A.lower(): _full_torrent()})
    adapter = _FakeAdapter(find_sequence=[{"hash": HASH_A, "state": "stoppedUP"}])
    results, _ = _run(monkeypatch, qb, _make_target(), [HASH_A], adapter=adapter)
    assert results[0].status is TransferStatus.SUCCESS
    # 不变量: 只删任务, delete_files 恒 False
    assert qb.deletions == [(HASH_A, False)]


def test_keep_source_flag_skips_delete(monkeypatch):
    qb = _FakeQbApi(torrents={HASH_A.lower(): _full_torrent()})
    adapter = _FakeAdapter(find_sequence=[{"hash": HASH_A, "state": "stoppedUP"}])
    results, _ = _run(monkeypatch, qb, _make_target(), [HASH_A], keep_source=True, adapter=adapter)
    assert results[0].status is TransferStatus.SUCCESS
    assert "保留源种子" in results[0].reason
    assert qb.deletions == []


# ---------- 路径映射 ----------


def test_path_map_first_rule_wins(monkeypatch):
    rules = (
        TransferPathMapEntry(src="D:/data", dst="E:/seed"),
        TransferPathMapEntry(src="D:/data/Torrents", dst="F:/other"),
    )
    qb = _FakeQbApi(torrents={HASH_A.lower(): _full_torrent()})
    adapter = _FakeAdapter(find_sequence=[{"hash": HASH_A, "state": "stoppedUP"}])
    results, _ = _run(monkeypatch, qb, _make_target(path_map=rules), [HASH_A], adapter=adapter)
    assert adapter.add_calls[0]["fields"]["save_path"] == "E:/seed/Torrents"


@pytest.mark.parametrize(
    "rules",
    [
        (),  # 空映射 = 原样
        (TransferPathMapEntry(src="X:/elsewhere", dst="Y:"), ),  # 无命中 = 原样
    ],
)
def test_path_map_no_match_or_empty_passthrough(monkeypatch, rules):
    qb = _FakeQbApi(torrents={HASH_A.lower(): _full_torrent()})
    adapter = _FakeAdapter(find_sequence=[{"hash": HASH_A, "state": "stoppedUP"}])
    _run(monkeypatch, qb, _make_target(path_map=rules), [HASH_A], adapter=adapter)
    assert adapter.add_calls[0]["fields"]["save_path"] == "D:/data/Torrents"


# ---------- 批次行为(D6) ----------


def test_batch_continues_after_skipped_seed(monkeypatch):
    qb = _FakeQbApi(
        torrents={
            HASH_A.lower(): _full_torrent(HASH_A),
            HASH_B.lower(): _full_torrent(HASH_B, state="downloading"),  # 门拦
            HASH_C.lower(): _full_torrent(HASH_C),
        }
    )
    adapter = _FakeAdapter(
        find_sequence=[{
            "hash": HASH_A,
            "state": "stoppedUP"
        }, None, {
            "hash": HASH_C,
            "state": "stoppedUP"
        }]
    )
    results, _ = _run(monkeypatch, qb, _make_target(), [HASH_A, HASH_B, HASH_C], adapter=adapter)
    assert [r.hash for r in results] == [HASH_A, HASH_B, HASH_C]
    assert [r.status for r in results] == [TransferStatus.SUCCESS, TransferStatus.SKIPPED, TransferStatus.SUCCESS]
    assert qb.deletions == [(HASH_A, False), (HASH_C, False)]


def test_batch_unexpected_exception_does_not_interrupt(monkeypatch):
    qb = _FakeQbApi(
        torrents={
            HASH_A.lower(): _full_torrent(HASH_A),
            HASH_B.lower(): _full_torrent(HASH_B),
            HASH_C.lower(): _full_torrent(HASH_C)
        }
    )
    adapter = _FakeAdapter(
        add_results=[AddResult.added("ok")],
        find_sequence=[{
            "hash": HASH_A,
            "state": "stoppedUP"
        }, None, {
            "hash": HASH_C,
            "state": "stoppedUP"
        }],
        add_error=None,
    )
    # 第二条 add 抛未预期异常 -> 本条失败, 第三条照常
    original_add = adapter.add_torrent

    def flaky_add(data, fields, skip_check):
        if fields.get("infohash") == HASH_B:
            raise RuntimeError("boom")
        return original_add(data, fields, skip_check)

    adapter.add_torrent = flaky_add
    results, _ = _run(monkeypatch, qb, _make_target(), [HASH_A, HASH_B, HASH_C], adapter=adapter)
    assert [r.status for r in results] == [TransferStatus.SUCCESS, TransferStatus.FAILED, TransferStatus.SUCCESS]
    assert results[1].code is TransferOutcomeCode.UNEXPECTED
    assert qb.deletions == [(HASH_A, False), (HASH_C, False)]  # 失败条目源保留


# ---------- after_state(D9) ----------


def test_after_state_paused_pauses_before_delete(monkeypatch):
    events: List[str] = []
    qb = _FakeQbApi(torrents={HASH_A.lower(): _full_torrent()})

    original_delete = qb.torrents_delete

    def noting_delete(torrent_hashes=None, delete_files=False, **kwargs):
        events.append("delete")
        original_delete(torrent_hashes=torrent_hashes, delete_files=delete_files, **kwargs)

    qb.torrents_delete = noting_delete

    adapter = _FakeAdapter(find_sequence=[{"hash": HASH_A, "state": "stoppedUP"}])
    original_pause = adapter.pause_torrent

    def noting_pause(infohash):
        events.append("pause")
        return original_pause(infohash)

    adapter.pause_torrent = noting_pause
    results, _ = _run(monkeypatch, qb, _make_target(after_state="paused"), [HASH_A], adapter=adapter)
    assert results[0].status is TransferStatus.SUCCESS
    assert adapter.pause_calls == [HASH_A]
    assert events == ["pause", "delete"]  # 验证成功后、删源前


def test_after_state_paused_failure_noted(monkeypatch):
    qb = _FakeQbApi(torrents={HASH_A.lower(): _full_torrent()})
    adapter = _FakeAdapter(find_sequence=[{"hash": HASH_A, "state": "stoppedUP"}], pause_ok=False)
    results, _ = _run(monkeypatch, qb, _make_target(after_state="paused"), [HASH_A], adapter=adapter)
    assert results[0].status is TransferStatus.SUCCESS  # 暂停失败不回滚已成功的转移
    assert "暂停失败" in results[0].reason
    assert qb.deletions == [(HASH_A, False)]


def test_after_state_keep_never_pauses(monkeypatch):
    qb = _FakeQbApi(torrents={HASH_A.lower(): _full_torrent()})
    adapter = _FakeAdapter(find_sequence=[{"hash": HASH_A, "state": "stoppedUP"}])
    results, _ = _run(monkeypatch, qb, _make_target(), [HASH_A], adapter=adapter)
    assert results[0].status is TransferStatus.SUCCESS
    assert adapter.pause_calls == []


# ---------- 源读取 / 导出失败 ----------


def test_export_failure_keeps_source(monkeypatch):
    qb = _FakeQbApi(torrents={HASH_A.lower(): _full_torrent()}, export_error=RuntimeError("export boom"))
    results, adapter = _run(monkeypatch, qb, _make_target(), [HASH_A])
    assert results[0].status is TransferStatus.FAILED
    assert results[0].code is TransferOutcomeCode.EXPORT_FAILED
    assert adapter.add_calls == [] and qb.deletions == []


def test_source_read_failure(monkeypatch):
    qb = _FakeQbApi(torrents={})  # 查无此 hash
    results, adapter = _run(monkeypatch, qb, _make_target(), [HASH_A])
    assert results[0].status is TransferStatus.FAILED
    assert results[0].code is TransferOutcomeCode.SOURCE_READ_FAILED
    assert adapter.add_calls == [] and qb.deletions == []

    qb_error = _FakeQbApi(torrents={HASH_A.lower(): _full_torrent()}, info_error=RuntimeError("net down"))
    results_error, _ = _run(monkeypatch, qb_error, _make_target(), [HASH_A])
    assert results_error[0].code is TransferOutcomeCode.SOURCE_READ_FAILED


# ---------- 字段采集 ----------


def test_field_collection_respects_switches(monkeypatch):
    qb = _FakeQbApi(torrents={HASH_A.lower(): _full_torrent()})
    adapter = _FakeAdapter(find_sequence=[{"hash": HASH_A, "state": "stoppedUP"}])
    fields_off = {key: (key in ("save_path", "category")) for key in TRANSFER_FIELD_KEYS}
    _run(monkeypatch, qb, _make_target(fields=fields_off), [HASH_A], adapter=adapter)
    sent = adapter.add_calls[0]["fields"]
    assert sent["save_path"] == "D:/data/Torrents"  # 锁死恒采集
    assert sent["category"] == "tv"
    assert "tags" not in sent and "share_ratio_limit" not in sent
    assert "seeding_time_limit" not in sent and "up_limit" not in sent
    assert "down_limit" not in sent and "super_seeding" not in sent
    assert sent["infohash"] == HASH_A  # 探针键恒在


def test_field_collection_maps_maindata_keys(monkeypatch):
    qb = _FakeQbApi(torrents={HASH_A.lower(): _full_torrent()})
    adapter = _FakeAdapter(find_sequence=[{"hash": HASH_A, "state": "stoppedUP"}])
    all_on = {key: True for key in TRANSFER_FIELD_KEYS}  # 模板默认关超级做种, 映射用例全开
    _run(monkeypatch, qb, _make_target(fields=all_on), [HASH_A], adapter=adapter)
    sent = adapter.add_calls[0]["fields"]
    assert sent["tags"] == ["zE01", "grp"]
    assert sent["share_ratio_limit"] == 2.0  # <- maindata ratio_limit
    assert sent["seeding_time_limit"] == 0
    assert sent["up_limit"] == -1
    assert sent["down_limit"] == -1  # <- maindata dl_limit
    assert sent["super_seeding"] is False


# ---------- 结果结构 / 杂项 ----------


def test_result_receipt_shape():
    ok = TorrentTransferResult(HASH_A, TransferStatus.SUCCESS, "目标已受理")
    skip = TorrentTransferResult(HASH_B, TransferStatus.SKIPPED, "目标已存在", TransferOutcomeCode.DUPLICATE)
    fail = TorrentTransferResult(HASH_C, TransferStatus.FAILED, "验证超时", TransferOutcomeCode.VERIFY_TIMEOUT)
    assert ok.to_receipt() == {"hash": HASH_A, "状态": "成功", "原因": "目标已受理"}
    assert skip.to_receipt() == {"hash": HASH_B, "状态": "跳过", "原因": "目标已存在"}
    assert fail.to_receipt() == {"hash": HASH_C, "状态": "失败", "原因": "验证超时"}
    assert [s.label for s in TransferStatus] == ["成功", "跳过", "失败"]


def test_empty_hashes_skips_adapter(monkeypatch):
    qb = _FakeQbApi()
    factory_calls: List[str] = []

    def spying_factory(target):
        factory_calls.append(target.name)
        return _FakeAdapter()

    monkeypatch.setattr(orchestrator_module, "create_adapter", spying_factory)
    orchestrator = TransferOrchestrator(qb, sleep=lambda s: None, verify_timeout=1.0, poll_interval=0.25)
    results = orchestrator.run_batch(_make_target(), [])
    assert results == []
    assert factory_calls == []  # 空批次连适配器都不实例化


def test_auth_failure_classified(monkeypatch):
    qb = _FakeQbApi(torrents={HASH_A.lower(): _full_torrent(), HASH_B.lower(): _full_torrent(HASH_B)})
    adapter = _FakeAdapter(add_results=[AddResult.failed("目标登录失败(检查用户名/密码)"), AddResult.failed("目标拒绝添加(响应: Fails.)")], )
    results, _ = _run(monkeypatch, qb, _make_target(), [HASH_A, HASH_B], adapter=adapter)
    assert results[0].code is TransferOutcomeCode.AUTH_FAILED
    assert results[1].code is TransferOutcomeCode.ADD_FAILED
    assert all(r.status is TransferStatus.FAILED for r in results)
    assert qb.deletions == []
