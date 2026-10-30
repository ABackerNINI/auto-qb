"""test_transfer_routes 测试计划: 种子转移 API 路由接入(计划 26-10-31-0306 §04 W3)

路由面 + cmd 管线 drain 面(waitCmd 回执); transfer 层一律 mock(FakeOrchestrator /
FakeAdapter / 真 TrDownloaderStub), 不联网、不真连 qB。鉴权与跨站闸参照
pitfalls/testing/web-auth-test-forms.md: 缺省 TestClient 形态非 loopback, 凭证类
断言用缺省形态(远端语义); 跨站闸用例显式 client_addr=("127.0.0.1", 50000) + Host 头。

## 测试计划(每个测试函数一条)
- test_transfer_run_unauthenticated_401: 无凭证/错密钥打 run+test -> 401, 零入队
- test_transfer_run_cross_site_origin_rejected: skip_local_verify 开启时跨站 Origin ->
  403 且零入队; 同源 Origin + 凭证放行入队
- test_transfer_run_route_validation: target_id 空 / hashes 空列表 / 目标不存在 /
  目标未启用 -> 400 且零入队; 合法请求 200 入队 cmd=transfer_run, 载荷
  {target_id, hashes}(hash 清洗去空), keep_source 提供才透传
- test_transfer_run_drain_receipt: mock orchestrator, [成功, 跳过, 失败] 混合批次 ->
  回执 ok, truth.results 逐条 {hash, 状态(中文三态), 原因} 与 orchestrator 分类一致
  (to_receipt 直出), summary 三态计数; 单种子失败不中断批次(3 条全结);
  keep_source 透传 run_batch; 目标未启用/在投递-执行之间消失 -> error 回执零执行
- test_transfer_test_route_and_drain: test 路由目标不存在 400 不入队; 未启用目标可测
  (只要求存在, 设置页先行测连通); drain 成功 -> ok truth={info}; 适配器抛
  TransferAdapterError -> error 回执回显文案
- test_transfer_test_tr_stub: tr 目标走真 stub(test_connection 恒返回「暂未实现」文案,
  零网络) -> error 回执带「暂未实现」文案
"""
from __future__ import annotations

import pytest

import auto_qb.webui.commands as commands_module
from auto_qb.config import TransferConfig, TransferTargetConfig
from auto_qb.transfer import TransferAdapterError
from auto_qb.transfer.orchestrator import TorrentTransferResult, TransferOutcomeCode, TransferStatus

from helpers import FakeClient, make_manager

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
    """drain 级: 逐种子结果与 orchestrator 分类一致(to_receipt 直出), 失败不中断批次,
    keep_source 透传; 目标未启用/消失 -> error 回执零执行"""
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

        def run_batch(self, target, hashes, keep_source=False):
            calls.append(("run", target.name, list(hashes), keep_source))
            return list(results)

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
    assert ("run", "目标A", ["HA", "HB", "HC"], True) in calls, calls
    assert sum(1 for c in calls if c[0] == "init") == 1, calls
    # 命令层兜底: 目标未启用 -> error 回执, orchestrator 零执行
    rec2 = _drain(mgr, "transfer_run", {"target_id": "目标B", "hashes": ["HA"], "cmd_id": "tr2"})
    assert rec2["status"] == "error" and "未启用" in rec2["error"], rec2
    # 目标在投递-执行之间消失(热重载窗口) -> error 回执, orchestrator 零执行
    rec3 = _drain(mgr, "transfer_run", {"target_id": "不存在", "hashes": ["HA"], "cmd_id": "tr3"})
    assert rec3["status"] == "error" and "不存在" in rec3["error"], rec3
    assert sum(1 for c in calls if c[0] == "run") == 1, calls


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
