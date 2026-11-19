"""test_transfer_routes 测试计划: 种子转移 API 路由接入(计划 26-10-31-0306 §04 W3)

路由面 + cmd 管线 drain 面(waitCmd 回执); transfer 层一律 mock(FakeOrchestrator /
FakeAdapter / 真 TrDownloaderStub), 不联网、不真连 qB。鉴权与跨站闸参照
pitfalls/testing/web-auth-test-forms.md: 缺省 TestClient 形态非 loopback, 凭证类
断言用缺省形态(远端语义); 跨站闸用例显式 client_addr=("127.0.0.1", 50000) + Host 头。

## 测试计划(每个测试函数一条)
- test_transfer_run_unauthenticated_401: 无凭证/错密钥打 run+test -> 401, 零入队
- test_transfer_run_cross_site_origin_rejected: skip_local_verify 开启时跨站 Origin ->
  403 且零入队; 同源 Origin + 凭证放行入队
- test_transfer_run_route_validation: target_id 空 / hashes 空列表 / hashes 非数组
  (字符串/dict, issue 26-11-03-0901) / 目标不存在 / 目标未启用 -> 400 且零入队; 合法
  请求 200 入队 cmd=transfer_run, 载荷 {target_id, hashes}(hash 清洗去空 + 去重保序),
  keep_source 提供才透传
- test_transfer_run_drain_receipt: mock 生产段(produce_transfer_job 全批已结算),
  [成功, 跳过, 失败] 混合批次走快路径 -> 回执 ok 当轮即写(时机与同步路径一致),
  truth.results 逐条 {hash, 状态(中文三态), 原因} 与 orchestrator 分类一致
  (to_receipt 直出), summary 三态计数; 单种子失败不中断批次(3 条全结); 快路径零
  线程零递交(判据单点 = 生产段无验证作业); keep_source 透传生产段; 目标未启用/
  在投递-执行之间消失 -> error 回执零执行
- test_transfer_run_submit_path_mixed_batch: 递交路径(S3) —— 生产段产出混合列
  (跳过已结算 + 验证作业 + 失败已结算)递交 center, 回执延后到批次齐; 槽位按入参
  顺序(已结算结果作初值), truth 形状逐字节同形(D5), summary 聚合口径不变;
  验证成功槽位按 source_hash 删源(qbapi.torrents_delete delete_files=False)
- test_transfer_run_slow_target_does_not_block_command_line: 慢目标桩(find_torrent
  阻塞)下命令线程不被占住 —— 转移命令 exec_ms < 500(CMD_SLOW_MS 埋点口径, 验证
  等待在 worker), 回执延后; 放行后批次照常齐写回执
- test_web_stop_sequence_with_inflight_verify_does_not_block: web 停止序列整段不阻塞
  (S4/S5 验收「关停 < N s, 不 join, Event 即时醒」) —— 慢目标在途验证钉在 find 闸上,
  WebUIModule.stop()(center.stop -> 订阅注销 -> 服务退出位)秒级内完成; 关停面若退化成
  join worker(在途验证等满闸超时 10s)本用例当场红; 在途结论 stop 后照常回灌但回执不写
  (主循环不再 drain 即作废, D4a), 全程零删源
- test_transfer_test_route_and_drain: test 路由空/缺失 target_id 400 不入队(T2a2); 目标不存在 400 不入队; 未启用目标可测
  (只要求存在, 设置页先行测连通); drain 成功 -> ok truth={info}; 适配器抛
  TransferAdapterError -> error 回执回显文案
- test_transfer_test_tr_stub: tr 目标走真 stub(test_connection 恒返回「暂未实现」文案,
  零网络) -> error 回执带「暂未实现」文案
"""
from __future__ import annotations

import re
import threading
import time

import pytest

import auto_qb.webui.commands as commands_module
from auto_qb.config import TransferConfig, TransferTargetConfig
from auto_qb.transfer import TransferAdapterError
from auto_qb.transfer.adapters import AddResult
from auto_qb.transfer.orchestrator import (
    TorrentTransferResult,
    TransferOutcomeCode,
    TransferStatus,
    TransferVerifyJob,
    _SeedPlan,
)

from clock import wait_until
from helpers import FakeClient, FakeTorrent, capture_logs, make_manager

# 等价形态常量单点: 请求头名字面量不直接连写赋值符(工作区写入判据误判族, 见
# memory-bank/pitfalls/ops/agent-write-guard-secret-false-positive.md; 与 test_web_auth 同款)
_AUTH_HEADER = "Authorization"

TARGET_A = TransferTargetConfig(
    name="目标A", type="qb", base_url="http://127.0.0.1:8081", username="u", password="p", enabled=True
)
TARGET_OFF = TransferTargetConfig(
    name="目标B", type="qb", base_url="http://127.0.0.1:8082", username="u", password="p", enabled=False
)


def _install_targets(mgr, *targets) -> None:
    """给 manager 挂 web.transfer 段(FakeConfig.web / SimpleNamespace 均实例属性, 无跨测泄漏)"""
    mgr.config.web.transfer = TransferConfig(targets=tuple(targets))


def _drain_manager(tmp_path, *targets):
    """drain 级用真 QbManager(make_manager 单点): runtime 的 host._web_command_handlers
    只在真 manager 上有; FakeClient 替身客户端(transfer 层照样 mock, 不真连)"""
    mgr = make_manager(str(tmp_path / "state.json"), client=FakeClient())
    _install_targets(mgr, *targets)
    return mgr


def _auth(mgr) -> dict:
    return {_AUTH_HEADER: f"Bearer {mgr.web.token}"}


def _drain(mgr, cmd: str, payload: dict) -> dict:
    """直投命令队列 + drain 一轮, 返回该 cmd_id 的回执(drain 级测试样板, 同 test_web_skip_check)"""
    mgr.web.commands.put((cmd, dict(payload)))
    mgr.web.consume_commands()
    return mgr.web.results[payload["cmd_id"]]


def test_transfer_run_unauthenticated_401(web_env):
    """无凭证/错密钥 -> 401, 两端点一致, 零入队"""
    mgr, client = web_env
    _install_targets(mgr, TARGET_A)
    cases = [
        ("/api/transfer/run", {
            "target_id": "目标A",
            "hashes": ["HA"]
        }),
        ("/api/transfer/test", {
            "target_id": "目标A"
        }),
    ]
    for path, body in cases:
        assert client.post(path, json=body).status_code == 401, path
        wrong = {_AUTH_HEADER: "Bearer definitely-not-the-token"}
        assert client.post(path, headers=wrong, json=body).status_code == 401, path
    assert mgr.web.commands.empty(), "401 路径不得入队"


@pytest.mark.parametrize("web_env", [{"client_addr": ("127.0.0.1", 50000)}], indirect=True)
def test_transfer_run_cross_site_origin_rejected(web_env):
    """skip_local_verify 开启: 跨站 Origin -> 403 且零入队; 同源 Origin + 凭证放行"""
    mgr, client = web_env
    mgr.config.web.skip_local_verify = True
    _install_targets(mgr, TARGET_A)
    evil = {"Host": "127.0.0.1:8080", "Origin": "http://evil.com"}
    assert client.post(
        "/api/transfer/run", headers=evil, json={
            "target_id": "目标A",
            "hashes": ["HA"]
        }
    ).status_code == 403
    assert client.post("/api/transfer/test", headers=evil, json={"target_id": "目标A"}).status_code == 403
    assert mgr.web.commands.empty(), "跨站 403 不得入队(闸在全局依赖, 先于处理器)"
    same = {"Host": "127.0.0.1:8080", "Origin": "http://127.0.0.1:8080"}
    resp = client.post("/api/transfer/run", headers={**_auth(mgr), **same}, json={"target_id": "目标A", "hashes": ["HA"]})
    assert resp.status_code == 200 and resp.json()["queued"] is True, resp.text
    assert mgr.web.commands.qsize() == 1


def test_transfer_run_route_validation(web_env):
    """路由层校验: 空 target_id / 空 hashes / 目标不存在 / 未启用 -> 400 零入队; 合法载荷形状"""
    mgr, client = web_env
    auth = _auth(mgr)
    _install_targets(mgr, TARGET_A, TARGET_OFF)
    bad = [
        ("/api/transfer/run", {
            "target_id": "",
            "hashes": ["HA"]
        }),  # target_id 空
        ("/api/transfer/run", {
            "hashes": ["HA"]
        }),  # target_id 缺失
        ("/api/transfer/run", {
            "target_id": "目标A",
            "hashes": []
        }),  # hashes 空列表
        ("/api/transfer/run", {
            "target_id": "目标A",
            "hashes": "HA"
        }),  # hashes 非数组(字符串会被逐字符拆成伪 hash, issue 26-11-03-0901)
        ("/api/transfer/run", {
            "target_id": "目标A",
            "hashes": {
                "HA": 1
            }
        }),  # hashes 非数组(dict 可迭代, 同样必须拒收)
        ("/api/transfer/run", {
            "target_id": "目标A"
        }),  # hashes 缺失 = 空
        ("/api/transfer/run", {
            "target_id": "不存在",
            "hashes": ["HA"]
        }),  # 目标不存在
        ("/api/transfer/run", {
            "target_id": "目标B",
            "hashes": ["HA"]
        }),  # 目标未启用
    ]
    for path, body in bad:
        resp = client.post(path, headers=auth, json=body)
        assert resp.status_code == 400, (body, resp.text)
    assert mgr.web.commands.empty(), "400 拒收不得入队"
    # 合法: 200 入队, 载荷形状 {target_id, hashes}(清洗去空), cmd_id/埋点由 post_command 注入
    resp = client.post("/api/transfer/run", headers=auth, json={"target_id": "目标A", "hashes": ["HA", "", "HB"]})
    assert resp.status_code == 200 and resp.json()["queued"] is True, resp.text
    cmd, payload = mgr.web.commands.get_nowait()
    assert cmd == "transfer_run", (cmd, payload)
    assert payload["cmd_id"], "waitCmd 回执 ID 必须生成"
    payload.pop("cmd_id")
    payload.pop("_queued_ts", None)
    assert payload == {"target_id": "目标A", "hashes": ["HA", "HB"]}, payload
    # 重复 hash 去重保序(路由层顺手去重, 不放大主循环批次)
    resp = client.post(
        "/api/transfer/run",
        headers=auth,
        json={
            "target_id": "目标A",
            "hashes": ["HB", "HA", "HB", "HA"]
        },
    )
    assert resp.status_code == 200, resp.text
    cmd, payload = mgr.web.commands.get_nowait()
    payload.pop("cmd_id")
    payload.pop("_queued_ts", None)
    assert payload == {"target_id": "目标A", "hashes": ["HB", "HA"]}, payload
    # keep_source: 提供才透传
    resp = client.post(
        "/api/transfer/run", headers=auth, json={
            "target_id": "目标A",
            "hashes": ["HA"],
            "keep_source": True
        }
    )
    assert resp.status_code == 200, resp.text
    cmd, payload = mgr.web.commands.get_nowait()
    payload.pop("cmd_id")
    payload.pop("_queued_ts", None)
    assert payload == {"target_id": "目标A", "hashes": ["HA"], "keep_source": True}, payload


def test_transfer_run_drain_receipt(tmp_path, monkeypatch):
    """drain 级快路径(生产段全批已结算): 逐种子结果与 orchestrator 分类一致(to_receipt
    直出), 失败不中断批次, keep_source 透传生产段; 回执当轮即写(与同步路径同形), 零线程
    零递交; 目标未启用/消失 -> error 回执零执行"""
    mgr = _drain_manager(tmp_path, TARGET_A, TARGET_OFF)
    # 逐种子结果直接用真 orchestrator 结果结构: 分类与回执形态的单一出处
    results = [
        TorrentTransferResult("HA", TransferStatus.SUCCESS, ""),
        TorrentTransferResult("HB", TransferStatus.SKIPPED, "目标已存在", TransferOutcomeCode.DUPLICATE),
        TorrentTransferResult("HC", TransferStatus.FAILED, "源 .torrent 导出失败", TransferOutcomeCode.EXPORT_FAILED),
    ]
    calls: list = []

    class FakeOrchestrator:
        def __init__(self, qb_api):
            calls.append(("init", qb_api is mgr.api))

        def produce_transfer_job(self, target, hash_, keep_source):
            calls.append(("produce", target.name, hash_, keep_source))
            return next(r for r in results if r.hash == hash_)

    monkeypatch.setattr(commands_module, "TransferOrchestrator", FakeOrchestrator)
    rec = _drain(
        mgr, "transfer_run", {
            "target_id": "目标A",
            "hashes": ["HA", "HB", "HC"],
            "keep_source": True,
            "cmd_id": "tr1"
        }
    )
    assert rec["status"] == "ok", rec
    truth = rec["truth"]
    assert set(truth) == {"results", "summary", "target"}, truth
    assert truth["target"] == "目标A"
    # 单种子失败不中断批次: 3 条全结, 顺序 = 入参顺序
    assert [r["hash"] for r in truth["results"]] == ["HA", "HB", "HC"], truth["results"]
    # 逐种子结果结构与 orchestrator 分类一致(to_receipt 直出: {hash, 状态中文三态, 原因})
    assert truth["results"][0] == {"hash": "HA", "状态": "成功", "原因": ""}
    assert truth["results"][1]["状态"] == "跳过" and "已存在" in truth["results"][1]["原因"]
    assert truth["results"][2]["状态"] == "失败" and "导出失败" in truth["results"][2]["原因"]
    assert truth["summary"] == {"success": 1, "skipped": 1, "failed": 1}, truth["summary"]
    assert ("produce", "目标A", "HA", True) in calls, calls
    assert sum(1 for c in calls if c[0] == "produce") == 3, calls
    assert all(c[3] is True for c in calls if c[0] == "produce"), "keep_source 逐种子全量透传生产段"
    assert sum(1 for c in calls if c[0] == "init") == 1, calls
    # 快路径回归钉面(§07): 判据单点 = 生产段无验证作业 -> 现场写回执, 零递交零线程
    # (worker 懒启动: 本批未入中心, 恒无线程; 批次容器恒空)
    assert mgr.web.transfer_center._batches == {}
    assert mgr.web.transfer_center._worker is None
    # 命令层兜底: 目标未启用 -> error 回执, orchestrator 零执行
    rec2 = _drain(mgr, "transfer_run", {"target_id": "目标B", "hashes": ["HA"], "cmd_id": "tr2"})
    assert rec2["status"] == "error" and "未启用" in rec2["error"], rec2
    # 目标在投递-执行之间消失(热重载窗口) -> error 回执, orchestrator 零执行
    rec3 = _drain(mgr, "transfer_run", {"target_id": "不存在", "hashes": ["HA"], "cmd_id": "tr3"})
    assert rec3["status"] == "error" and "不存在" in rec3["error"], rec3
    assert sum(1 for c in calls if c[0] == "produce") == 3, calls


def test_transfer_run_submit_path_mixed_batch(tmp_path, monkeypatch):
    """递交路径(S3): 生产段混合列(跳过已结算 + 验证作业 + 失败已结算)递交 center ——
    回执延后到批次齐, 槽位按入参顺序(已结算结果作初值), truth 形状逐字节同形(D5);
    验证成功槽位按 source_hash 删源(delete_files=False 恒定, 只删任务)"""
    mgr = _drain_manager(tmp_path, TARGET_A)
    mgr.client.torrents["HSRC"] = FakeTorrent(hash="HSRC", state="pausedUP", progress=1.0)
    job = TransferVerifyJob(
        hash="HB",
        source_hash="HSRC",
        plan=_SeedPlan(
            data=b"t",
            fields={
                "infohash": "HSRC",
                "save_path": "D:/x"
            },
            skip_check=False,
            degraded_note="",
            source_hash="HSRC"
        ),
        keep_source=False,
        after_state="keep",
    )
    produces: list = []

    class FakeOrchestrator:
        def __init__(self, qb_api):
            pass

        def produce_transfer_job(self, target, hash_, keep_source):
            produces.append((hash_, keep_source))
            if hash_ == "HA":  # 生产段已结算: 跳过(已存在)
                return TorrentTransferResult("HA", TransferStatus.SKIPPED, "目标已存在", TransferOutcomeCode.DUPLICATE)
            if hash_ == "HB":  # 生产段放行: 验证作业
                return job
            return TorrentTransferResult(
                "HC", TransferStatus.FAILED, "源 .torrent 导出失败", TransferOutcomeCode.EXPORT_FAILED
            )

    monkeypatch.setattr(commands_module, "TransferOrchestrator", FakeOrchestrator)
    # worker 侧注入: 验证成功(不真等), 其余走真实端口链(删源 = orchestrator._delete_source)
    mgr.web.transfer_center._verify_runner = lambda adapter, job_: TorrentTransferResult(
        job_.hash, TransferStatus.SUCCESS, "目标已受理", None
    )
    mgr.web.commands.put(
        ("transfer_run", {
            "target_id": "目标A",
            "hashes": ["HA", "HB", "HC"],
            "keep_source": False,
            "cmd_id": "tr1"
        })
    )
    mgr.web.consume_commands()
    assert "tr1" not in mgr.web.results, "递交路径: 回执延后, 生产段完成不当轮写"
    assert ("HB", False) in produces
    batch = mgr.web.transfer_center._batches["tr1"]
    assert batch.remaining == 1, "剩余计数只算验证作业槽位"
    # 槽位按入参顺序: 已结算结果作初值占位, 验证作业槽位待结论
    assert batch.slots[0].result is not None and batch.slots[0].result.status is TransferStatus.SKIPPED
    assert batch.slots[2].result is not None and batch.slots[2].result.status is TransferStatus.FAILED
    assert batch.slots[1].result is None
    assert batch.slots[0].keep_source and batch.slots[2].keep_source, "已结算槽位永不删源(未验证成功不碰源)"
    assert wait_until(lambda: mgr.web.transfer_center._results.qsize() == 1, timeout=3.0)
    changed = mgr.web.consume_commands()  # 命令线尾部 drain: 删源 + 填槽 + 批次齐写回执
    assert changed is True, "删源成功并入 cmd_changed_state(D6: 白享 P0-5 立即补刷新通路)"
    rec = mgr.web.results["tr1"]
    assert rec["status"] == "ok", rec
    truth = rec["truth"]
    assert [r["hash"] for r in truth["results"]] == ["HA", "HB", "HC"], "truth 按入参顺序(D5)"
    assert truth["results"][0] == {"hash": "HA", "状态": "跳过", "原因": "目标已存在"}
    assert truth["results"][1] == {"hash": "HB", "状态": "成功", "原因": "目标已受理"}
    assert truth["results"][2]["状态"] == "失败" and "导出失败" in truth["results"][2]["原因"]
    assert truth["summary"] == {"success": 1, "skipped": 1, "failed": 1}
    assert truth["target"] == "目标A"
    assert mgr.web.transfer_center._batches == {}
    # 删源走真实端口: 验证成功的 HB 按 source_hash 删, 只删任务(delete_files=False)
    assert ("delete", False) in mgr.client.calls, mgr.client.calls
    assert "HSRC" not in mgr.client.torrents, "验证成功未保留源: 源任务已删"


def test_transfer_run_slow_target_does_not_block_command_line(tmp_path, monkeypatch):
    """慢目标桩(S3 验收: [cmd] 排队 < 500ms 口径): find_torrent 慢回的假 adapter 下
    命令线程不被验证等待占住 —— 转移命令当轮返回(exec 只含生产段, CMD_SLOW_MS 埋点),
    回执延后; 放行后批次照常齐写回执"""
    mgr = _drain_manager(tmp_path, TARGET_A)
    mgr.client.torrents["HA"] = FakeTorrent(hash="HA", state="pausedUP", progress=1.0)
    release = threading.Event()
    finds: list = []

    class SlowFindAdapter:
        def add_torrent(self, data, fields, skip_check):
            return AddResult.added("目标已受理")

        def find_torrent(self, infohash):
            finds.append(infohash)
            release.wait(timeout=10.0)  # 慢目标: 验证轮询被钉住(旧同步路径会把命令占死在这里)
            return {"hash": infohash, "state": "stoppedUP"}

    mgr.web.transfer_center._adapter_factory = lambda target: SlowFindAdapter()
    # 走真实投递面(post_command 注入埋点), 排队/执行耗时才进 [cmd] 埋点日志
    resp = mgr.web.post_command("transfer_run", {"target_id": "目标A", "hashes": ["HA"]})
    cmd_id = resp["cmd_id"]
    with capture_logs("auto_qb.webui.runtime") as cap:
        t0 = time.perf_counter()
        mgr.web.consume_commands()  # 命令线消费转移命令: 生产段(读源+导出)后即返回
        elapsed_ms = (time.perf_counter() - t0) * 1000
    assert elapsed_ms < 500, f"验证等待期间命令线程被占住({elapsed_ms:.0f}ms)"
    line = next(m for m in cap.messages if "[cmd] transfer_run" in m)
    wait_ms = float(re.search(r"排队 ([\d.]+)ms", line).group(1))
    exec_ms = float(re.search(r"执行 ([\d.]+)ms", line).group(1))
    assert wait_ms < 500 and exec_ms < 500, line
    assert cmd_id not in mgr.web.results, "验证在途: 回执延后"
    assert wait_until(lambda: bool(finds), timeout=3.0), "验证作业已进 worker(与命令线程解耦)"
    release.set()
    assert wait_until(lambda: mgr.web.transfer_center._results.qsize() == 1, timeout=3.0)
    mgr.web.consume_commands()
    rec = mgr.web.results[cmd_id]
    assert rec["status"] == "ok" and rec["truth"]["results"][0]["状态"] == "成功", rec


def test_web_stop_sequence_with_inflight_verify_does_not_block(tmp_path):
    """web 停止序列整段不阻塞钉面(S4/S5 验收「关停 < N s, 不 join, Event 即时醒」):
    慢目标在途验证钉在 find_torrent 闸上时, WebUIModule.stop() 整段(center.stop() ->
    订阅注销 -> 服务退出位, 生产序列逐字)秒级内完成 —— 关停面若退化成 join worker
    (在途验证要等满闸超时 10s), 本用例当场红; 在途结论 stop 后照常回灌, 但主循环不再
    drain -> 回执不写(作废面, D4a), 全程零删源(源不误删)"""
    mgr = _drain_manager(tmp_path, TARGET_A)
    mgr.client.torrents["HA"] = FakeTorrent(hash="HA", state="pausedUP", progress=1.0)
    gate = threading.Event()
    finds: list = []

    class SlowFindAdapter:
        def add_torrent(self, data, fields, skip_check):
            return AddResult.added("目标已受理")

        def find_torrent(self, infohash):
            finds.append(infohash)
            gate.wait(timeout=10.0)  # 在途验证钉住: worker 阻塞在这里(唯一能拖住 join 的点)
            return {"hash": infohash, "state": "stoppedUP"}

    mgr.web.transfer_center._adapter_factory = lambda target: SlowFindAdapter()
    resp = mgr.web.post_command("transfer_run", {"target_id": "目标A", "hashes": ["HA"]})
    cmd_id = resp["cmd_id"]
    mgr.web.consume_commands()  # 生产段+递交即返回(递交路径, 回执延后)
    assert wait_until(lambda: bool(finds), timeout=3.0), "在途验证已进 worker(阻塞在 find 闸)"
    mod = mgr.host.get("webui")
    t0 = time.perf_counter()
    try:
        mod.stop()  # 整段关停序列: center.stop() 先叫停(Event 即时醒, 不 join)
        elapsed_s = time.perf_counter() - t0
        assert elapsed_s < 2.0, f"web 停止序列被在途验证拖住({elapsed_s:.1f}s, 闸超时 10s)"
        assert mgr.web.transfer_center._stop_event.is_set(), "stop Event 已置位"
    finally:
        gate.set()  # 放行在途验证: 结论照常回灌(stop 不拦回灌); 失败路径也不留阻塞线程
    # 在途结论回灌后主循环不再 drain: 回执不写(作废面, 与今天进程崩溃同形)
    assert wait_until(lambda: mgr.web.transfer_center._results.qsize() == 1, timeout=3.0)
    assert cmd_id not in mgr.web.results, "stop 后不再 drain: 回执不写(在途作废)"
    assert all(c[0] != "delete" for c in mgr.client.calls), "全程零删源(源不误删)"
    worker = mgr.web.transfer_center._worker
    worker.join(timeout=2.0)  # 测试侧 join 仅作收尾: worker 已被 stop Event 放行, 秒级自然退出
    assert not worker.is_alive(), "worker 已被 stop Event 即时醒退出"


def test_transfer_test_route_and_drain(web_env, tmp_path, monkeypatch):
    """test 路由: 目标不存在 400 不入队; 未启用目标可测(只要求存在); drain 成功 truth={info} /
    TransferAdapterError -> error 回显文案"""
    mgr, client = web_env
    auth = _auth(mgr)
    _install_targets(mgr, TARGET_A, TARGET_OFF)
    # 目标不存在: 400 零入队
    resp = client.post("/api/transfer/test", headers=auth, json={"target_id": "不存在"})
    assert resp.status_code == 400 and "不存在" in resp.json()["detail"], resp.text
    assert mgr.web.commands.empty()
    # T2a2: 空 target_id 路由层 400(先于目标查表, 不入队)
    resp = client.post("/api/transfer/test", headers=auth, json={})
    assert resp.status_code == 400 and "未提供 target_id" in resp.json()["detail"], resp.text
    assert mgr.web.commands.empty()
    # 未启用目标可测(设置页对未启用目标先行测连通): 200 入队, 载荷只有 target_id
    resp = client.post("/api/transfer/test", headers=auth, json={"target_id": "目标B"})
    assert resp.status_code == 200 and resp.json()["queued"] is True, resp.text
    cmd, payload = mgr.web.commands.get_nowait()
    assert cmd == "transfer_test", (cmd, payload)
    payload.pop("cmd_id")
    payload.pop("_queued_ts", None)
    assert payload == {"target_id": "目标B"}, payload
    # drain(真 manager): 成功 -> ok + truth={info}, 只做探测无其它调用
    mgr = _drain_manager(tmp_path, TARGET_A)
    probes: list = []

    class FakeAdapter:
        def test_connection(self):
            probes.append("test")
            return "qBittorrent v5.2.3"

    monkeypatch.setattr(commands_module, "create_adapter", lambda target: FakeAdapter())
    rec = _drain(mgr, "transfer_test", {"target_id": "目标A", "cmd_id": "tt1"})
    assert rec["status"] == "ok", rec
    assert rec["truth"] == {"info": "qBittorrent v5.2.3"}, rec
    assert probes == ["test"], "测试连接只做探测, 无其它调用"

    # drain 失败: error 回执回显适配器文案
    class FailAdapter:
        def test_connection(self):
            raise TransferAdapterError("目标A: 登录失败(检查用户名/密码)")

    monkeypatch.setattr(commands_module, "create_adapter", lambda target: FailAdapter())
    rec2 = _drain(mgr, "transfer_test", {"target_id": "目标A", "cmd_id": "tt2"})
    assert rec2["status"] == "error" and "登录失败" in rec2["error"], rec2


def test_transfer_test_tr_stub(tmp_path):
    """tr 目标走真 stub: test_connection 恒返回「暂未实现」文案(零网络) -> error 回执带原文"""
    tr_target = TransferTargetConfig(name="tr目标", type="tr", base_url="http://127.0.0.1:9091", enabled=True)
    mgr = _drain_manager(tmp_path, tr_target)
    rec = _drain(mgr, "transfer_test", {"target_id": "tr目标", "cmd_id": "tt3"})
    assert rec["status"] == "error", rec
    assert "暂未实现" in rec["error"], rec
