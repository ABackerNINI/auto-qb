# -*- coding: utf-8 -*-
"""S3: 用例随「提交前不直查」翻面(用完即删)"""
import io

P = "tests/test_ops.py"
s = io.open(P, encoding="utf-8").read()

# ---------- 1) 两条"提交点复核"用例改写 ----------
old1 = '''def test_ops_recheck_live_recheck_rejects_when_gone():
    """测试: live 空(种子已从客户端移除, 快照尚在) -> skip(R2 同族文案), 未发送 recheck、未登记"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    t = FakeTorrent(hash="HA", state="pausedDL", progress=0.0)
    seed_store(mgr, [t])  # 快照仍在; client.torrents 留空 = qB 侧已无(live 空)
    r = mgr.ctx.ops.recheck("HA", source="web")
    assert r.is_skipped and "种子已被移除" in r.message, f"live 空应放弃: {r}"
    assert not any(c[0] == "recheck" for c in client.calls), f"不得发送 recheck: {client.calls}"
    assert "HA" not in mgr.task_queue.active_check_hashes(), "放弃不得留下在途登记"'''
new1 = '''def test_ops_recheck_submits_without_live_query():
    """测试(S3): 提交前**不直查** qB —— 快照有记录即提交, 零 info 调用

    26-10-21-2323 S3: 运行状态按 RefreshInterval(默认 1500ms)节流刷新, 命令后直查与快照读的是
    同一份缓存; 不存在的种子提交 recheck 本就是 no-op, 故整条"提交前复核"通道移除。
    """
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    t = FakeTorrent(hash="HA", state="pausedDL", progress=0.0)
    seed_store(mgr, [t])  # 快照有记录; client.torrents 留空 —— 提交前不再关心 qB 是否真有
    r = mgr.ctx.ops.recheck("HA", source="web")
    assert r.is_ok, f"快照有记录即提交: {r}"
    assert client.info_calls == 0, f"提交前不得直查(实得 {client.info_calls} 次)"
    assert any(c[0] == "recheck" for c in client.calls), f"应已发送 recheck: {client.calls}"'''
assert old1 in s
s = s.replace(old1, new1, 1)

old2 = '''def test_ops_recheck_live_recheck_error_fails_closed():
    """测试: 提交点实时复核 API 异常 -> fail-closed 拒绝提交(零副作用: 未登记未发送)"""'''
new2 = '''def test_ops_recheck_ignores_info_error_before_submit():
    """测试(S3): 提交前不直查, 故 qB info 故障不影响提交(轮询期的仲裁直查才 fail-closed)"""'''
assert old2 in s
s = s.replace(old2, new2, 1)

# 该用例体: 原来断言 fail + 未发送, 现在应 ok + 已发送
old3 = '''    client.torrents_info = boom
    r = mgr.ctx.ops.recheck("HA", source="web")
    assert r.is_failed and "实时复核失败" in r.message, f"复核异常应 fail: {r}"
    assert not any(c[0] == "recheck" for c in client.calls), f"拒绝时零副作用: {client.calls}"
    assert "HA" not in mgr.task_queue.active_check_hashes(), "拒绝时不得登记在途"'''
new3 = '''    client.torrents_info = boom
    r = mgr.ctx.ops.recheck("HA", source="web")
    assert r.is_ok and "校验已提交" in r.message, f"info 故障不影响提交(不直查): {r}"
    assert any(c[0] == "recheck" for c in client.calls), f"应已发送 recheck: {client.calls}"
    assert "HA" in mgr.task_queue.active_check_hashes(), "提交后应登记在途"'''
assert old3 in s
s = s.replace(old3, new3, 1)

# ---------- 2) 跳检那条: 复核异常 -> 导出失败口径 ----------
old4 = '''def test_ops_skip_check_live_recheck_api_error():
    """测试: 跳检前实时复核 API 异常 -> fail 且零副作用(未导出/删除/重加)"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    seed_paused(mgr, client, hash="HASH123")

    def boom(**kw):
        raise RuntimeError("api down")

    client.torrents_info = boom
    r = mgr.ctx.ops.skip_check("HASH123", source="web")
    assert r.is_failed and "实时复核失败" in r.message, f"复核异常应 fail: {r}"
    assert not any(c[0] in ("export", "delete", "add") for c in client.calls), "复核失败零副作用"'''
new4 = '''def test_ops_skip_check_export_error_mentions_gone():
    """测试(S3): 提交前不直查; 种子真不在时失败在导出步, 文案点明"可能已不在客户端", 零删除/重加"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    seed_paused(mgr, client, hash="HASH123")

    def boom(**kw):
        raise RuntimeError("api down")

    client.torrents_export = boom
    r = mgr.ctx.ops.skip_check("HASH123", source="web")
    assert r.is_failed and "可能已不在客户端" in r.message, f"导出失败应带定位提示: {r}"
    assert not any(c[0] in ("delete", "add") for c in client.calls), "导出失败后不得删除/重加"'''
assert old4 in s
s = s.replace(old4, new4, 1)

# ---------- 3) 仲裁用例: 少一次提交前直查 ----------
s = s.replace(
    '    assert client.info_calls == 2, f"提交点 live 1 次 + 仲裁直查恰 1 次: {client.info_calls}"',
    '    assert client.info_calls == 1, f"提交前不直查 + 仲裁直查恰 1 次: {client.info_calls}"', 1
)
s = s.replace(
    '    assert client.info_calls == 2, f"仲裁后快照观测仍零 API: {client.info_calls}"',
    '    assert client.info_calls == 1, f"仲裁后快照观测仍零 API: {client.info_calls}"', 1
)
s = s.replace(
    '    assert client.info_calls == 2, f"提交点 live 1 次(P1) + 仲裁直查恰 1 次: {client.info_calls}"',
    '    assert client.info_calls == 1, f"提交前不直查 + 仲裁直查恰 1 次: {client.info_calls}"', 1
)
s = s.replace(
    '    assert client.info_calls == 2, f"提交点 live 1 次(P1) + 仲裁直查恰一次(fail-closed 落判败): {client.info_calls}"',
    '    assert client.info_calls == 1, f"提交前不直查 + 仲裁直查恰一次(fail-closed 落判败): {client.info_calls}"', 1
)

io.open(P, "w", encoding="utf-8").write(s)
print("test_ops patched")
