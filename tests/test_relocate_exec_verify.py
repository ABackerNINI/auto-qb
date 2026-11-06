"""test_relocate_exec_verify 测试计划: S4 后半核验+删链门 + D16 删种拦截(计划 26-11-05-0808
§3.1「qB 重启 → 主循环核验」段 / §2.3 N5 教训 / §06 D16)

## 测试计划(每个测试函数一条)
### 纯函数层(relocate_units)
- test_under_alias_root_dual_criteria: 等值 OR 前缀双判据(N5: save_path 恰等于根必须命中);
  前缀同串兄弟目录不误伤; 门外不命中; 空路径 None
- test_chain_gate_hits_scan: 门外共享者零依赖 / 等值+前缀命中混合 / 空 save_path 跳过
- test_alias_roots_of_filters: 终态 / direct(无别名) / 无链接记录的 job 不进拦截根集
### 核验三分(_step_verify)
- test_step_verify_all_pass_zero_deps_finalizes: 全员 save_path == dst + 删链门零依赖 →
  在线删别名 + 终态 done + journal 落 done + alias_paths 清空
- test_step_verify_member_not_at_dst_hangs_and_replays: 一成员仍在旧路径 → 不终态不判 failed,
  journal settled 记录被清回 pending(相位翻 armed, verify_replays 计 1), job 镜像回 armed
- test_step_verify_partial_members_fail: 部分成员不过 → 悬挂且告警文案点名未过成员
- test_step_verify_member_gone_hangs: 成员已不在客户端 → 同悬挂(良性态, FAILED_GONE 已退役)
- test_step_verify_replay_only_once: 重放一轮后仍不过 → 不再清账(rewrites 保持 settled),
  job 停 rewritten + reason=verify_failed(防无限改写循环)
### 删链门(_step_verify 依赖扫描)
- test_step_verify_deps_block_then_release: 门外共享者 save_path 恰等于旧根(N5 形态)→
  reason=chain_deps 别名不删; 依赖消失后重跑 → 收尾完成
- test_step_verify_deps_prefix_hit: 前缀命中(组外种子落旧根之下)同为依赖, 别名不删
### D16 删种拦截(qbapi.torrents_delete 单点, 两条删除路径共用判据)
- test_qbapi_delete_guard_blocks_delete_files: 目录别名形态(junction 根=src)——等值与前缀
  成员都拦(整批不发 qB, 文案带解法); delete_files=False(纯删除)放行
- test_qbapi_delete_guard_file_links_form: 文件级形态(scope==src)同判据拦截(文件级 symlink
  deleteFiles 跟随直删)
- test_qbapi_delete_guard_allows_outside_and_unregistered: 门外种子放行; 无活动别名登记放行
- test_qbapi_delete_guard_allows_probe_tagged_seeds: 探测种子(tag 含 TAG_PROBE)落在活动别名
  根下也放行(评审 #5, 自造探针非组成员数据; 拦截会让探测清理 deleteFiles 恒失败)/ 普通种子
  同根仍拦
### WebUI 删除命令面(第二条路径, 经命令队列全链)
- test_webui_delete_blocked_receipt_single_and_group: delete_torrent / delete_group 撞拦截 →
  error 回执带解法文案 + qB 客户端未收到 delete; 纯删除照常发

覆盖率缺口清偿(26-11-07, test.full 99.31% -> 99.5% 闸):
- test_webui_delete_blocked_receipt_bulk_and_no_cmd_id: 批量删除拦截 error 回执 + 单发/组发无
  cmd_id 静默回执(拦截不依赖结果页)
- test_verify_hang_unchanged_state_is_debug_only: 悬挂同参重放只落 DEBUG(不重复清账/刷警告)
- test_qb_side_check_self_failure_is_skipped: qB 侧自检自身炸 => skipped 不挡武装
"""

import types
from dataclasses import replace

import pytest

from auto_qb.core.modules import relocate_units as ru
from auto_qb.core.qbapi import DeleteBlockedError, QbApi
from auto_qb.infra import relocate_journal as rj

from helpers import FakeClient, capture_logs
from relocate_exec_support import _bare_mod, _job

# ---------------------------------------------------------------- 纯函数层


def test_under_alias_root_dual_criteria():
    """等值 OR 前缀双判据(N5): 恰等于根的 save_path 必须命中, 纯前缀判据会漏"""
    root = r"R:\media"
    assert ru.under_alias_root(r"R:\media", (root, )) == "r:/media"  # 等值(N5 漏拦形态)
    assert ru.under_alias_root(r"R:\media\sub", (root, )) == "r:/media"  # 前缀
    assert ru.under_alias_root(r"R:\mediax", (root, )) is None  # 前缀同串兄弟目录: 不误伤
    assert ru.under_alias_root(r"R:\other", (root, )) is None  # 门外
    assert ru.under_alias_root("", (root, )) is None  # 空路径不可判
    assert ru.under_alias_root(r"R:\media", ()) is None  # 无根


def test_chain_gate_hits_scan():
    """删链门扫描纯函数: 门外共享者零依赖 / 等值+前缀命中混合 / 空 save_path 跳过"""
    hits = ru.chain_gate_hits([r"R:\media", r"R:\media\g2", r"R:\elsewhere", "", r"R:\mediax"], r"R:\media")
    assert hits == (r"R:\media", r"R:\media\g2"), hits
    assert ru.chain_gate_hits([r"R:\elsewhere"], r"R:\media") == (), "门外共享者零依赖"


def test_alias_roots_of_filters():
    """活动别名根集只收「非终态 + 有别名形态 + 账上有链接记录」的 job"""
    jobs = [
        _job("j1", phase=ru.PHASE_ARMED, alias_kind="dir", alias_paths=("R:/src/l", )),
        _job("j2", phase=ru.PHASE_DONE, alias_kind="dir", alias_paths=("R:/x", )),  # 终态: 不拦
        _job("j3", phase=ru.PHASE_ARMED, alias_kind="", alias_paths=()),  # direct: 无别名
        _job("j4", phase=ru.PHASE_MOVING, alias_kind="file", alias_paths=()),  # 链接未建: 不拦
    ]
    assert ru.alias_roots_of(jobs) == (("R:/src", "j1"), ), ru.alias_roots_of(jobs)


# ---------------------------------------------------------------- 核验三分(_step_verify)


def _rec(h, save_path):
    return types.SimpleNamespace(hash=h, save_path=save_path, state="pausedUP")


def _rewritten_env(tmp_path, members, *, extra=(), alias_paths=("R:/src/l", ), replays=0):
    """rewritten 相位 job + journal settled 账 + store 成员账(核验/删链门用例的公共底座)

    members/extra = [(hash, save_path)]; journal 预写全体 settled + 相位 rewritten
    (replays 可预置重放计数, 供「重放闸已用尽」用例), spec 省略(_step_verify 不读 spec)。
    返回 (mod, job, rt, removed_删链spy)。
    """
    by_hash = {}
    for h, sp in list(members) + list(extra):
        by_hash[h] = _rec(h, sp)
    mod = _bare_mod(store=types.SimpleNamespace(by_hash=by_hash, relocating_hashes=set()), data_dir=str(tmp_path))
    rewrites = {h: {"status": "rewritten", "ts": 1.0} for h, _sp in members}
    body = {"phase": ru.PHASE_REWRITTEN, "rewrites": rewrites, "ts": 1.0}
    if replays:
        body[rj.VERIFY_REPLAYS_KEY] = replays
    rj.write_journal(str(tmp_path), "j1", body)
    job = _job("j1", phase=ru.PHASE_REWRITTEN, hashes=tuple(h for h, _sp in members), alias_paths=alias_paths)
    mod.register_job(job)
    removed = []
    mod._remove_links = lambda paths: (removed.extend(list(paths)), len(removed))[1]
    return mod, job, {}, removed


def test_step_verify_all_pass_zero_deps_finalizes(tmp_path):
    """全员到目标 + 零依赖 → 在线删别名 + 终态 done(journal 同步落 done, alias_paths 清空)"""
    mod, job, rt, removed = _rewritten_env(tmp_path, [("HA", "R:/dst"), ("HB", "R:/dst")])
    mod._step_verify(job, rt)
    saved = mod.get_job("j1")
    assert saved.phase == ru.PHASE_DONE and saved.reason == ru.REASON_FINALIZED, (saved.phase, saved.reason)
    assert saved.alias_paths == (), "终态 job 不再背别名账"
    assert removed == ["R:/src/l"], removed
    assert rj.read_journal(str(tmp_path), "j1")["phase"] == "done", "journal 必须同步落终态(daemon 据此退休)"


def test_step_verify_member_not_at_dst_hangs_and_replays(tmp_path):
    """一成员仍在旧路径 → 悬挂不判 failed; settled 账被清回 pending(相位翻 armed)+ job 镜像回 armed"""
    mod, job, rt, removed = _rewritten_env(tmp_path, [("HA", "R:/dst"), ("HB", "R:/src")])
    mod._step_verify(job, rt)
    saved = mod.get_job("j1")
    assert not saved.is_terminal and saved.phase == ru.PHASE_ARMED, (saved.phase, saved.reason)
    assert removed == [], "核验不过绝不删别名"
    j = rj.read_journal(str(tmp_path), "j1")
    assert j["phase"] == ru.PHASE_ARMED, j
    assert j[rj.VERIFY_REPLAYS_KEY] == 1, j
    assert all(
        m["status"] == rj.REWRITE_RESET_STATUS and m["prev_status"] == "rewritten" for m in j["rewrites"].values()
    ), j
    assert rj.pending_members({"members": [{"hash_v1": "HA"}, {"hash_v1": "HB"}]}, j["rewrites"]), \
        "清账后全体成员必须重回 pending"


def test_step_verify_partial_members_fail(tmp_path):
    """部分成员不过: 悬挂回 armed 请求重放, 告警文案点名未过成员(过者不入文案)"""
    mod, job, rt, _removed = _rewritten_env(tmp_path, [("HA", "R:/dst"), ("HB", "R:/src")])
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod._step_verify(job, rt)
    saved = mod.get_job("j1")
    assert saved.phase == ru.PHASE_ARMED and not saved.is_terminal, (saved.phase, saved.reason)
    warn = " ".join(cap.messages)
    assert "HB" in warn and "HA" not in warn, warn


def test_step_verify_member_gone_hangs(tmp_path):
    """成员已不在客户端 → 同悬挂(良性态; FAILED_GONE 已退役, 现场处置并入依赖扫描口径)"""
    mod, job, rt, removed = _rewritten_env(tmp_path, [("HA", "R:/dst"), ("HB", "R:/dst")], replays=1)
    del mod._ctx.store.by_hash["HB"]
    mod._step_verify(job, rt)
    saved = mod.get_job("j1")
    assert not saved.is_terminal and saved.phase == ru.PHASE_REWRITTEN, (saved.phase, saved.reason)
    assert saved.reason == ru.REASON_VERIFY_FAILED and "已不在客户端" in saved.last_error, saved.last_error
    assert removed == [], removed
    j = rj.read_journal(str(tmp_path), "j1")
    assert all(m["status"] == "rewritten" for m in j["rewrites"].values()), "重放闸已用尽: 账不被清"


def test_step_verify_replay_only_once(tmp_path):
    """重放一轮后仍不过 → 不再清账(rewrites 保持 settled), 停 rewritten + verify_failed(防无限改写循环)"""
    mod, job, rt, _removed = _rewritten_env(tmp_path, [("HA", "R:/dst"), ("HB", "R:/src")])
    mod._step_verify(job, rt)  # 第一轮: 清账 + 回 armed
    assert rj.verify_replays_of(str(tmp_path), "j1") == 1
    # 模拟 daemon 重放收口 + qB 再重启仍不过: rewrites 重回 settled, 相位翻 rewritten
    # (daemon 的 record_rewrites 整包合并, verify_replays 计数原样保留 —— 测试按同形写)
    rewrites = {h: {"status": "rewritten", "ts": 2.0} for h in ("HA", "HB")}
    rj.write_journal(
        str(tmp_path),
        "j1",
        {
            "phase": ru.PHASE_REWRITTEN,
            "rewrites": rewrites,
            "ts": 2.0,
            rj.VERIFY_REPLAYS_KEY: 1
        },
    )
    job2 = mod.get_job("j1")
    mod._set_job(replace(job2, phase=ru.PHASE_REWRITTEN, reason=""))
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod._step_verify(mod.get_job("j1"), rt)  # 第二轮核验不过
    j = rj.read_journal(str(tmp_path), "j1")
    assert j[rj.VERIFY_REPLAYS_KEY] == 1, "重放闸: 不得二次清账"
    assert all(m["status"] == "rewritten" for m in j["rewrites"].values()), j
    saved = mod.get_job("j1")
    assert saved.phase == ru.PHASE_REWRITTEN and saved.reason == ru.REASON_VERIFY_FAILED, (saved.phase, saved.reason)
    assert "维持悬挂" in " ".join(cap.messages), cap.messages


# ---------------------------------------------------------------- 删链门(_step_verify 依赖扫描)


def test_step_verify_deps_block_then_release(tmp_path):
    """N5 形态: 门外共享者 save_path 恰等于旧根 → chain_deps 别名不删; 依赖消失 → 收尾完成"""
    mod, job, rt, removed = _rewritten_env(
        tmp_path,
        [("HA", "R:/dst")],
        extra=[("HZ", "R:/src")],  # Z: 组外共享者, 等值命中
    )
    mod._step_verify(job, rt)
    saved = mod.get_job("j1")
    assert not saved.is_terminal and saved.phase == ru.PHASE_REWRITTEN, (saved.phase, saved.reason)
    assert saved.reason == ru.REASON_CHAIN_DEPS and removed == [], (saved.reason, removed)
    assert "1 个种子" in saved.last_error and "HZ" in saved.last_error, saved.last_error

    del mod._ctx.store.by_hash["HZ"]  # 依赖消失(迁移或删除后)
    mod._step_verify(mod.get_job("j1"), rt)
    saved = mod.get_job("j1")
    assert saved.phase == ru.PHASE_DONE and removed == ["R:/src/l"], (saved.phase, removed)


def test_step_verify_deps_prefix_hit(tmp_path):
    """前缀命中: 组外种子落旧根之下(save_path = src/sub)同为依赖, 别名不删"""
    mod, job, rt, removed = _rewritten_env(
        tmp_path,
        [("HA", "R:/dst")],
        extra=[("HZ", r"R:\src\g2")],
    )
    mod._step_verify(job, rt)
    saved = mod.get_job("j1")
    assert saved.reason == ru.REASON_CHAIN_DEPS and removed == [], (saved.reason, removed)


# ---------------------------------------------------------------- D16 删种拦截(qbapi 单点)


class _GuardStore:
    """QbApi 拦截判定的最小 store 替身: get/remove_torrent + relocating_alias_roots 登记"""
    def __init__(self, records, roots=None):
        self._records = dict(records)
        self.removed = []
        if roots is not None:
            self.relocating_alias_roots = dict(roots)

    def get(self, h):
        return self._records.get(h)

    def remove_torrent(self, h):
        self.removed.append(h)


def _guard_api(records, roots=None):
    client = FakeClient()
    api = QbApi(client, _GuardStore(records, roots))
    return api, client


def test_qbapi_delete_guard_blocks_delete_files():
    """目录别名形态(根=src): 等值与前缀命中都拦(整批不发 qB); 纯删除(delete_files=False)放行"""
    records = {
        "HA": _rec("HA", r"R:\src"),  # 等值(N5 形态)
        "HB": _rec("HB", r"R:\src\sub"),  # 前缀
        "HZ": _rec("HZ", r"R:\elsewhere"),  # 门外
    }
    api, client = _guard_api(records, {r"R:\src": "j1"})
    with pytest.raises(DeleteBlockedError) as ei:
        api.torrents_delete(torrent_hashes=["HA", "HB", "HZ"], delete_files=True)
    assert [b[0] for b in ei.value.blocked] == ["HA", "HB"], ei.value.blocked
    assert ei.value.blocked[0][2] == "j1", "命中根必须能追到 job"
    assert "仅删除种子" in str(ei.value), "文案必须给出去文件化出路"
    assert not any(c[0] == "delete" for c in client.calls), "拦截必须整批不发 qB"
    api.torrents_delete(torrent_hashes=["HZ"], delete_files=True)  # 门外照删
    assert ("delete", True) in client.calls
    api.torrents_delete(torrent_hashes=["HA"], delete_files=False)  # 纯删除 = 去文件化出口
    assert ("delete", False) in client.calls
    assert api.store.removed == ["HZ", "HA"], api.store.removed


def test_qbapi_delete_guard_file_links_form():
    """文件级形态(scope==src): 同一根判据拦截(文件级 symlink deleteFiles 跟随直删, D16)"""
    records = {"HA": _rec("HA", "R:/src")}
    api, client = _guard_api(records, {"R:/src": "j9"})
    with pytest.raises(DeleteBlockedError):
        api.torrents_delete(torrent_hashes=["HA"], delete_files=True)
    assert not any(c[0] == "delete" for c in client.calls)


def test_qbapi_delete_guard_allows_outside_and_unregistered():
    """无活动别名登记(未启用迁移/全部终态)与快照缺席的种子: 不拦(fail-open, 判据只判事实)"""
    records = {"HA": _rec("HA", r"R:\src")}
    api, client = _guard_api(records, None)  # 无登记
    api.torrents_delete(torrent_hashes=["HA"], delete_files=True)
    assert ("delete", True) in client.calls
    api2, client2 = _guard_api({}, {r"R:\src": "j1"})  # 有登记但种子不在快照: 不可判, 放行
    api2.torrents_delete(torrent_hashes=["HX"], delete_files=True)
    assert ("delete", True) in client2.calls


def test_qbapi_delete_guard_allows_probe_tagged_seeds():
    """探测种子(tag 含 TAG_PROBE)落在活动别名根下也放行(评审 #5): 自造探针非组成员数据,
    拦截会让 _cleanup/启动残留扫描的 deleteFiles 恒失败(探针滞留每次启动重复告警);
    普通种子(无探测标签)同根仍拦(拦截面对成员数据不松动)"""
    from auto_qb.core.modules.relocate_probe import TAG_PROBE

    probe = types.SimpleNamespace(hash="HP", save_path=r"R:\src\probe-x", tags_set=frozenset({TAG_PROBE}))
    normal = _rec("HA", r"R:\src")  # 无 tags_set 属性(旧形态替身也判得出: 非探针)
    api, client = _guard_api({"HP": probe, "HA": normal}, {r"R:\src": "j1"})
    api.torrents_delete(torrent_hashes=["HP"], delete_files=True)  # 探针: 放行
    assert ("delete", True) in client.calls
    with pytest.raises(DeleteBlockedError) as ei:  # 普通成员种子同根: 照拦
        api.torrents_delete(torrent_hashes=["HA"], delete_files=True)
    assert [b[0] for b in ei.value.blocked] == ["HA"]
    # 混批: 探针不进拦截名单, 拦截只点名普通种子
    client.calls.clear()
    with pytest.raises(DeleteBlockedError) as ei2:
        api.torrents_delete(torrent_hashes=["HP", "HA"], delete_files=True)
    assert [b[0] for b in ei2.value.blocked] == ["HA"], ei2.value.blocked
    assert not any(c[0] == "delete" for c in client.calls), "整批仍不发 qB(同批有被拦种子)"


# ---------------------------------------------------------------- WebUI 删除命令面(第二条路径)


def test_webui_delete_blocked_receipt_single_and_group(tmp_path):
    """delete_torrent / delete_group 撞 D16 拦截 → error 回执带解法文案 + qB 未收到 delete;
    纯删除(delete_files=False)照常发(两条 WebUI 删除命令路径共用 qbapi 单点判)"""
    from webui_helpers import _make_grouped_manager

    mgr, client, key = _make_grouped_manager(str(tmp_path))
    mgr.store.relocating_alias_roots = {r"R:\Downloads": "j1"}
    # 单发路径
    mgr.web.commands.put(("delete_torrent", {"hash": "HA", "delete_files": True, "cmd_id": "d1"}))
    mgr.web.consume_commands()
    r1 = mgr.web.results["d1"]
    assert r1["status"] == "error" and "仅删除种子" in r1["error"], r1
    assert not any(c[0] == "delete" for c in client.calls), "拦截不得发 qB"
    # 组路径
    mgr.web.commands.put(("delete_group", {"key": key, "delete_files": True, "cmd_id": "d2"}))
    mgr.web.consume_commands()
    r2 = mgr.web.results["d2"]
    assert r2["status"] == "error" and "仅删除种子" in r2["error"], r2
    assert not any(c[0] == "delete" for c in client.calls)
    # 纯删除: 放行(去文件化出口)
    mgr.web.commands.put(("delete_torrent", {"hash": "HA", "delete_files": False, "cmd_id": "d3"}))
    mgr.web.consume_commands()
    assert mgr.web.results["d3"]["status"] == "ok", mgr.web.results["d3"]
    assert ("delete", False) in client.calls


# ---------------------------------------------------------------------------
# 覆盖率缺口清偿(26-11-07): 核验悬挂同参重放 / qB 侧自检异常
# ---------------------------------------------------------------------------


def test_verify_hang_unchanged_state_is_debug_only(tmp_path):
    """重放一轮后仍不过且反馈面无变化: 只落 DEBUG(不重复清账/不重复刷警告, 防每拍刷屏)"""
    import logging

    mod = _bare_mod(data_dir=str(tmp_path / "data"))
    rj.write_journal(mod._data_dir(), "j1", {"verify_replays": 1})
    bad = [("a" * 40, "已不在客户端")]
    detail = "; ".join(f"{h[:8]} {state}" for h, state in bad[:3])
    text = f"核验未过: {detail}(别名维持, 成员经别名可读)"
    job = _job("j1", phase=ru.PHASE_REWRITTEN, reason=ru.REASON_VERIFY_FAILED, last_error=text)
    with capture_logs("auto_qb.core.modules.relocate_mod", level=logging.DEBUG) as cap:
        mod._verify_hang(job, bad)
    assert any("悬挂维持" in m for m in cap.messages), cap.messages
    assert rj.verify_replays_of(mod._data_dir(), "j1") == 1, "同参重放不再清账"


def test_qb_side_check_self_failure_is_skipped(tmp_path, monkeypatch):
    """qB 侧自检自身炸 => skipped(保守默认不挡武装), rt 记异常供排查"""
    from auto_qb.core.modules import relocate_proof as rp_mod

    mod = _bare_mod(data_dir=str(tmp_path / "data"))
    job = _job("j1", phase=ru.PHASE_MOVED)

    def _boom(*a, **kw):
        raise RuntimeError("evidence broke")

    monkeypatch.setattr(rp_mod, "link_follow_evidence", _boom)
    rt = {}
    assert mod._qb_side_check(job, rt) == "skipped"
    assert "自检异常" in rt["qb_side_check"] and "RuntimeError" in rt["qb_side_check"]


# ---------------------------------------------------------------------------
# 覆盖率缺口清偿(26-11-07): 批量删除拦截回执 / 无 cmd_id 的拦截静默回执
# ---------------------------------------------------------------------------


def test_webui_delete_blocked_receipt_bulk_and_no_cmd_id(tmp_path):
    """D16 拦截回执全路径: 批量 delete 撞拦截 -> error 回执; 单发/组发无 cmd_id -> 静默回执
    (不炸不写结果页, qB 未收到 delete)"""
    from webui_helpers import _make_grouped_manager

    mgr, client, key = _make_grouped_manager(str(tmp_path))
    mgr.store.relocating_alias_roots = {r"R:\Downloads": "j1"}
    # 批量路径(cmd_id 在场): 整批不发 qB, error 回执
    mgr.web.commands.put(
        ("bulk_torrents", {
            "hashes": ["HA", "HB"],
            "action": "delete",
            "delete_files": True,
            "cmd_id": "d-bulk",
        })
    )
    mgr.web.consume_commands()
    r1 = mgr.web.results["d-bulk"]
    assert r1["status"] == "error" and "仅删除种子" in r1["error"], r1
    assert not any(c[0] == "delete" for c in client.calls)
    # 单发无 cmd_id: 拦截仍生效, 静默返回(无结果页可写)
    mgr.web.commands.put(("delete_torrent", {"hash": "HA", "delete_files": True}))
    mgr.web.consume_commands()
    assert not any(c[0] == "delete" for c in client.calls), "无 cmd_id 也必须拦(防误删)"
    # 组发无 cmd_id: 同上
    mgr.web.commands.put(("delete_group", {"key": key, "delete_files": True}))
    mgr.web.consume_commands()
    assert not any(c[0] == "delete" for c in client.calls), "无 cmd_id 组发同样拦"
