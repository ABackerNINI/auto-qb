"""test_checking 测试计划: checking 动作详细自测(不连接真实 qB, 用模拟对象)

## 测试计划(每个测试函数一条)
- test_checking_config_missing_section: with/without 段缺省合法(默认不启用)
- test_checking_config_defaults: 缺省配置项取默认值
- test_download_conflict_multi_dl: 多成员下载中 -> 冲突, 不发起校验
- test_download_conflict_mixed: 下载中与暂停混合 -> 冲突
- test_download_conflict_no_repeat: 已发起的校验不重复提交
- test_download_conflict_resolve_recur: 冲突消除后恢复校验(递归决策)
- test_download_conflict_single_dl: 单下载中不冲突
- test_download_conflict_grouping_disabled: 分组未启用不检查冲突
- test_checking_group_downloading_skips: 组内有下载中成员 -> 跳过校验
- test_checking_paused_incomplete_not_skip: 暂停未完成不能作为参考 -> 不跳过
- test_checking_no_group_uses_without_reference: 未归组无参考 -> 直接校验
- test_checking_paused_completed_reference: 暂停已完成亦是参考种子(is_complete 判定)
- test_checking_complete_skipped: 已完成做种中(progress=1) -> 跳过, 不校验
- test_checking_paused_complete_skipped: 暂停已完成(pausedUP+progress=1) -> 跳过
- test_checking_active_downloading_skipped: 活跃下载中(downloading+progress=0.5) -> 跳过
- test_checking_complete_no_repeat: 完成种子反复触发不重复校验(bug 回归)
- test_checking_filelist_reference_skip_checking: filelist 参考匹配 -> 跳检
- test_checking_no_reference_full_checking: 无参考 -> 全量校验流程
- test_checking_no_reference_skip_checking_warns: 无参考但 skip 配置 -> 警告跳过
- test_checking_piecehashes_same: piecehashes 一致 -> 跳检
- test_checking_piecehashes_diff: piecehashes 不一致 -> 全检
- test_checking_piecehashes_api_error: piecehashes API 错误 -> 降级处理
- test_checking_custom_rc0: custom 校验 rc0 -> 完成
- test_checking_custom_rc1: custom 校验 rc1 -> 失败
- test_checking_verified_reference_used: verified 参考种子被使用
- test_checking_verified_references_not_persisted: verified 参考不持久化(仅内存)
- test_checking_skip_guard_file_missing: 跳检前置文件检查失败
- test_checking_skip_guard_file_size_mismatch: 跳检前置文件大小不符
- test_checking_skip_guard_add_fail_backup: 重加标签失败回退
- test_checking_skip_dedup_same_day: 同日跳检去重
- test_checking_skip_partial_download_forbidden: 部分下载(0<progress<1)禁止跳检
- test_checking_recheck_fail_cooldown: 校验连续失败达上限 -> 当日不再重试(防 recheck 死循环)
- test_checking_skip_dedup_across_rules: 跨规则同日去重(同种子当日只跳检一次)
- test_checking_dry_run: dry-run 不发送请求
- test_checking_full_checking_pending: 全检任务 pending 保留
- test_checking_full_checking_dup_ignore: 全检重复提交忽略
- test_checking_full_checking_auto_start_false: auto_start=false 不自动开始
- test_checking_full_checking_send_error: 发送失败处理
- test_checking_full_checking_defer_resume: 任务队列驱动: 触发任务让位 -> 成功 resume 恢复
- test_checking_full_checking_resume_continues_actions: 断点续跑: 校验成功后执行断点后的剩余动作
- test_checking_full_checking_resume_skips_conditions: 断点续跑跳过条件评估(条件变化不影响续跑)
- test_checking_full_checking_resume_skips_dedup: 断点续跑跳过去重(execute_once=once 不拦截续跑)
- test_checking_full_checking_defer_fail_retry: 任务队列驱动: 校验未通过 -> 触发任务 reschedule 重试
- test_checking_group_full_checking_serialized: 组内校验串行(决策链 1.5): B 让位等待, A 成功晋升参考后 B 重走决策链走跳检
- test_checking_group_skip_on_same_data_fail: 组内校验失败推断(决策链 1.6): 文件映射一致 -> B 不再校验
- test_checking_group_no_infer_when_sizes_differ: 组内文件映射不一致 -> 不推断, B 照常校验
- test_checking_group_wait_external_entry_skip: 组内校验中且无任务驱动 -> skip
- test_checking_group_wait_timeout_force_resume: 等待超时强制恢复重判(防在途登记泄漏活锁)
"""
import os
import tempfile
import time
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from auto_qb.qbmanager import QbManager
from auto_qb.rules.actions import RECHECK_FAIL_LIMIT, CheckAction
from auto_qb.rules.actions.full_checking import _recheck_fail_count
from auto_qb.taskqueue import DEFERRED, PENDING, TaskQueue
from helpers import FakeClient, FakeConfig, FakeTorrent, make_ctx, seed_store


# ---------- 增强模拟客户端(piece hashes API / recheck 失败注入) ----------
class CheckingFakeClient(FakeClient):
    def __init__(self):
        super().__init__()
        self.piece_hashes_map = {}  # hash -> piece hash 列表(参考判定用)
        self.piece_hashes_error = False  # 模拟 API 异常
        self.recheck_error = None  # 模拟 recheck 请求失败

    def torrents_piece_hashes(self, torrent_hashes=None):
        """模拟 qbittorrentapi 的 torrents_piece_hashes(直接返回列表, 无需导出 .torrent)"""
        self.calls.append(("piece_hashes", torrent_hashes))
        if self.piece_hashes_error:
            raise RuntimeError("simulated piece hashes api error")
        return self.piece_hashes_map.get(torrent_hashes, [])

    def torrents_recheck(self, torrent_hashes=None):
        if self.recheck_error:
            raise self.recheck_error
        super().torrents_recheck(torrent_hashes=torrent_hashes)


# ---------- 测试辅助 ----------
def make_check_cfg(
    basic_check="filelist",
    with_mode="skip-checking",
    with_start=True,
    without_mode="full-checking",
    without_start=True,
    custom_program=None,
    extra_actions=None,
    execute_once="never"
):
    """构造 checking 规则配置(条件: 标签含"需校验"); extra_actions 追加到动作序列(续跑测试用)"""
    cfg = FakeConfig()
    action = {
        "checking":
            {
                "basic_check": basic_check,
                "with_reference": {
                    "enabled": True,
                    "mode": with_mode,
                    "auto_start": with_start
                },
                "without_reference": {
                    "enabled": True,
                    "mode": without_mode,
                    "auto_start": without_start
                },
            }
    }
    if custom_program:
        action["checking"]["custom_basic_check_program_path"] = custom_program
    actions = [action] + (extra_actions or [])
    cfg.rules_config = {
        "example_rules":
            {
                "check_rule":
                    {
                        "enabled": True,
                        "execute_once": execute_once,
                        "conditions": [{
                            "tags": "需校验"
                        }],
                        "actions": actions,
                        "stop_following_rules_if": "never",
                    },
            }
    }
    return cfg


def make_mgr(cfg, with_tq=False):
    """构造 QbManager(可选任务队列)"""
    mgr = QbManager("", config=cfg, no_lock=True)  # 测试不持锁
    mgr._load_rules()  # run() 中才自动加载; 测试直接构造后需手动加载规则
    if with_tq:
        mgr.task_queue = TaskQueue()
    return mgr


def run_queue(mgr, now=None, dry_run=False):
    """驱动快速队列一轮: 弹出所有到期任务并执行(校验轮询任务状态机推进)
    now: 显式时间点(校验任务 interval=2s, 多轮推进需递增 now)
    """
    now = time.time() if now is None else now
    due = mgr.task_queue.due(now)
    if due:
        mgr._execute_due(due, dry_run, now)
    return due


def process_rule(mgr, client, tor, dry_run=False):
    """同步执行 example_rules.check_rule 于种子(等价旧 process_torrent 入口)

    新架构规则由任务队列驱动(process_torrent 兼容入口已删); 测试为同步确定性, 这里用
    无任务上下文直接执行规则: 动作内部 full-checking 仍会把轮询任务注册到 task_queue
    (由 run_queue 推进); pending 分支在无任务时按成功继续, 与队列驱动的 defer 系列测试
    互不冲突。skip-checking 的删除-重加流程需要删除后快照仍可用(真实 qB 中重加立即以同
    hash 出现; 与 test_actions._skip_ctx 同思路): 包装 torrents_delete, 真实删除后恢复
    快照记录(不改 src)。
    """
    rule = next(r for r in mgr.enabled_rules if r.name == "example_rules.check_rule")
    store = mgr.store
    ctx = make_ctx(mgr, tor, client, dry_run=dry_run)  # ① 注入 by_hash(make_ctx 后捕获, 覆盖未 seed_store 的测试)
    prev = dict(store.by_hash)
    orig_delete = mgr.api.torrents_delete

    def wrapped_delete(torrent_hashes=None, delete_files=False, **kw):
        orig_delete(torrent_hashes=torrent_hashes, delete_files=delete_files, **kw)
        hashes = [torrent_hashes] if isinstance(torrent_hashes, str) else list(torrent_hashes or [])
        for h in hashes:
            if h in prev and store.by_hash.get(h) is not prev[h]:
                store.by_hash[h] = prev[h]  # 重加后同 tick 快照恢复(对象身份直写)
                if store._known_hashes is not None:
                    store._known_hashes.add(h)

    mgr.api.torrents_delete = wrapped_delete
    try:
        return rule.process(ctx)
    finally:
        mgr.api.torrents_delete = orig_delete


def inject_group(mgr, *hashes, key=("KEY", )):
    """把 hashes 注入同一组(绕过归组流程, 直接构造 store 分组结构) """
    mgr.store.groups[key] = list(hashes)
    for h in hashes:
        mgr.store.member_to_key[h] = key


def make_target(state="pausedDL", hash="HASH123", progress=0.0, tags="需校验"):
    return FakeTorrent(hash=hash, name="T", tags=tags, state=state, progress=progress)


def _seg(mode, start=True):
    return {"mode": mode, "auto_start": start}


# ============================================================
# A. 配置解析(spec 正确性 fail-fast 在 config 校验阶段, 见 test_config.py)
# ============================================================
def test_checking_config_missing_section():
    """测试: with/without 段可缺省(该段默认不启用), 显式段未写 enabled 默认不启用"""
    a = CheckAction({"basic_check": "filelist", "without_reference": _seg("full-checking")})
    assert a.with_reference == {"enabled": False, "mode": "", "auto_start": False}, "缺 with 段应默认不启用"
    b = CheckAction({"basic_check": "filelist", "with_reference": _seg("skip-checking")})
    assert b.without_reference == {"enabled": False, "mode": "", "auto_start": False}, "缺 without 段应默认不启用"
    assert a.without_reference["enabled"] is False, "显式段未写 enabled 默认不启用"
    assert b.with_reference["enabled"] is False, "显式段未写 enabled 默认不启用"


def test_checking_config_defaults():
    """测试: auto_start 缺省 false; 非 custom 时提供 custom_basic_check_program_path 不报错(忽略)"""
    a = CheckAction(
        {
            "basic_check": "filelist",
            "with_reference": {
                "mode": "skip-checking"
            },  # 无 auto_start
            "without_reference": {
                "mode": "full-checking"
            },
            "custom_basic_check_program_path": "/ignored/check.exe",  # 非 custom, 应忽略
        }
    )
    assert a.with_reference["auto_start"] is False
    assert a.without_reference["auto_start"] is False
    assert a.custom_program == "/ignored/check.exe"  # 不报错且保留
    assert a.basic_check == "filelist"


# ============================================================
# B. 分组下载冲突(6)
# ============================================================
def test_download_conflict_multi_dl():
    """测试: 同组两个及以上种子同时下载 -> 警告 + 整组暂停(一次); dry-run 不暂停"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    seed_store(
        mgr,
        [
            FakeTorrent(hash="D1", name="D1", state="downloading", amount_left=1),  # 未完成
            FakeTorrent(hash="D2", name="D2", state="downloading", amount_left=1),
        ]
    )
    inject_group(mgr, "D1", "D2")
    mgr._check_download_conflicts(dry_run=True)
    assert ("stop", None) not in client.calls, f"dry-run 不应暂停: {client.calls}"
    mgr._check_download_conflicts(dry_run=False)
    assert client.calls.count(("stop", None)) == 1, f"整组应暂停一次: {client.calls}"


def test_download_conflict_mixed():
    """测试: 已完成与下载中并存 -> 警告 + 整组暂停"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    seed_store(
        mgr,
        [
            FakeTorrent(hash="U1", name="U1", state="stalledUP", amount_left=0),
            FakeTorrent(hash="D1", name="D1", state="downloading", amount_left=1),  # 未完成
        ]
    )
    inject_group(mgr, "U1", "D1")
    mgr._check_download_conflicts(dry_run=False)
    assert client.calls.count(("stop", None)) == 1, f"混合并存应整组暂停: {client.calls}"


def test_download_conflict_no_repeat():
    """测试: 冲突持续 -> 不重复暂停(幂等去重)"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    seed_store(
        mgr,
        [
            FakeTorrent(hash="D1", name="D1", state="downloading", amount_left=1),  # 未完成
            FakeTorrent(hash="D2", name="D2", state="downloading", amount_left=1),
        ]
    )
    inject_group(mgr, "D1", "D2")
    mgr._check_download_conflicts(dry_run=False)
    mgr._check_download_conflicts(dry_run=False)
    mgr._check_download_conflicts(dry_run=False)
    assert client.calls.count(("stop", None)) == 1, f"冲突持续不应重复暂停: {client.calls}"


def test_download_conflict_resolve_recur():
    """测试: 冲突消除后清除去重, 重现时再次警告+暂停"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    d1 = FakeTorrent(hash="D1", name="D1", state="downloading", amount_left=1)
    d2 = FakeTorrent(hash="D2", name="D2", state="downloading", amount_left=1)
    seed_store(mgr, [d1, d2])
    inject_group(mgr, "D1", "D2")
    mgr._check_download_conflicts(dry_run=False)
    assert client.calls.count(("stop", None)) == 1

    # 冲突消除(全组完成, 无下载中): 不再暂停, 去重记录清除
    d1.state = "stalledUP"
    d1.amount_left = 0
    d2.state = "stalledUP"
    d2.amount_left = 0
    seed_store(mgr, [d1, d2])
    mgr._check_download_conflicts(dry_run=False)
    assert client.calls.count(("stop", None)) == 1, f"冲突消除后不应暂停: {client.calls}"

    # 冲突重现(D2 重新下载): 再次暂停(记录已清除, 新冲突类型 mixed)
    d2.state = "downloading"
    d2.amount_left = 1
    seed_store(mgr, [d1, d2])
    mgr._check_download_conflicts(dry_run=False)
    assert client.calls.count(("stop", None)) == 2, f"冲突重现应再次暂停: {client.calls}"


def test_download_conflict_single_dl():
    """测试: 单下载中(无已完成)不冲突; 多组互不影响"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    seed_store(
        mgr,
        [
            FakeTorrent(hash="D1", name="D1", state="downloading", amount_left=1),  # 未完成
            FakeTorrent(hash="U1", name="U1", state="stalledUP", amount_left=0),
        ]
    )
    inject_group(mgr, "D1", key=("K1", ))
    inject_group(mgr, "U1", key=("K2", ))
    mgr._check_download_conflicts(dry_run=False)
    assert ("stop", None) not in client.calls, f"单下载中不应暂停: {client.calls}"


def test_download_conflict_grouping_disabled():
    """测试: 分组未启用 -> 整轮刷新不触发下载冲突检查(无 stop)"""
    with tempfile.TemporaryDirectory() as td:
        cfg = FakeConfig()  # grouping.enabled = False
        mgr = make_mgr(cfg)
        client = FakeClient()
        mgr.client = client
        t1 = FakeTorrent(hash="D1", name="D1", state="downloading", save_path=r"R:\Downloads")
        t2 = FakeTorrent(hash="D2", name="D2", state="downloading", save_path=r"R:\Downloads")
        client.torrents["D1"] = t1
        client.torrents["D2"] = t2
        mgr._refresh_torrents()
        assert ("stop", None) not in client.calls, f"分组未启用不应检查冲突: {client.calls}"
        assert mgr.store.groups == {}, f"分组未启用不应有分组: {mgr.store.groups}"


# ============================================================
# C. 决策链(4)
# ============================================================
def test_checking_group_downloading_skips():
    """测试: 组内有活跃下载种子 -> 整组未完成, 跳过(不进行任何校验, 包括跳检)"""
    cfg = make_check_cfg()
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    t = make_target()
    d = FakeTorrent(hash="D1", name="D1", state="downloading")
    inject_group(mgr, "HASH123", "D1")
    seed_store(mgr, [t, d])
    handled, _stop = process_rule(mgr, client, t, dry_run=False)
    assert not handled, "组内下载中应跳过"
    assert client.calls == [], f"不应有任何客户端调用: {client.calls}"


def test_checking_paused_incomplete_not_skip():
    """测试: 暂停中的未完成(pausedDL)不算活跃下载, 不触发跳过; 且不算参考(无参考 -> full-checking)"""
    cfg = make_check_cfg(without_mode="full-checking", without_start=True)
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    t = make_target()
    pd = FakeTorrent(hash="PD1", name="PD1", state="pausedDL")  # 暂停未完成
    inject_group(mgr, "HASH123", "PD1")
    seed_store(mgr, [t, pd])
    handled, _stop = process_rule(mgr, client, t, dry_run=False)
    assert handled, "暂停未完成不应跳过"
    run_queue(mgr)  # 首轮: 发送 recheck
    assert ("recheck", None) in client.calls, f"无参考应走 full-checking: {client.calls}"


def test_checking_no_group_uses_without_reference():
    """测试: 分组未启用/未归组 -> 视为单种子组, 无参考 -> without_reference 段"""
    cfg = make_check_cfg(without_mode="full-checking", without_start=True)
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    t = make_target()
    seed_store(mgr, [t])
    handled, _stop = process_rule(mgr, client, t, dry_run=False)
    assert handled
    run_queue(mgr)  # 首轮: 发送 recheck
    assert ("recheck", None) in client.calls, f"无参考应走 full-checking: {client.calls}"


def test_checking_paused_completed_reference():
    """测试: 暂停中的已完成(pausedUP)亦是参考候选(is_complete 判定, 参考用元数据与暂停无关) -> with_reference 段跳检"""
    cfg = make_check_cfg(basic_check="filelist", with_mode="skip-checking", with_start=True)
    mgr = make_mgr(cfg)
    client = CheckingFakeClient()
    mgr.client = client
    client.torrents["HASH123"] = {"state": "stalledUP"}
    t = make_target()
    p = FakeTorrent(hash="P1", name="P1", state="pausedUP")  # 暂停已完成: 有效参考
    inject_group(mgr, "HASH123", "P1")
    seed_store(mgr, [t, p])
    handled, _stop = process_rule(mgr, client, t, dry_run=False)
    assert handled, f"暂停完成参考应可用: {client.calls}"
    assert [c[0] for c in client.calls] == ["export", "delete", "add", "start"], f"跳检调用顺序: {client.calls}"
    add_call = [c for c in client.calls if c[0] == "add"][0]
    assert add_call[1]["is_skip_checking"] is True, f"重加应跳过校验: {add_call}"


# ============================================================
# C1. 只校验暂停中未完成(决策链 0, 4)
# ============================================================
def test_checking_complete_skipped():
    """测试: 已完成做种中(stalledUP+progress=1) -> 跳过, 不进行任何校验(修复重复校验 bug)"""
    cfg = make_check_cfg(without_mode="full-checking", without_start=True)
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    t = make_target(state="stalledUP", progress=1.0)  # 已完成做种中
    seed_store(mgr, [t])
    handled, _stop = process_rule(mgr, client, t, dry_run=False)
    assert not handled, "已完成种子应跳过"
    assert client.calls == [], f"不应有任何客户端调用: {client.calls}"


def test_checking_paused_complete_skipped():
    """测试: 暂停已完成(pausedUP+progress=1) -> 跳过(暂停但已完成仍无需校验)"""
    cfg = make_check_cfg(without_mode="full-checking", without_start=True)
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    t = make_target(state="pausedUP", progress=1.0)
    seed_store(mgr, [t])
    handled, _stop = process_rule(mgr, client, t, dry_run=False)
    assert not handled, "暂停已完成种子应跳过"
    assert client.calls == [], f"不应有任何客户端调用: {client.calls}"


def test_checking_active_downloading_skipped():
    """测试: 活跃下载中(downloading+progress=0.5) -> 跳过(正在运行, 无需校验)"""
    cfg = make_check_cfg(without_mode="full-checking", without_start=True)
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    t = make_target(state="downloading", progress=0.5)
    seed_store(mgr, [t])
    handled, _stop = process_rule(mgr, client, t, dry_run=False)
    assert not handled, "活跃下载中种子应跳过"
    assert client.calls == [], f"不应有任何客户端调用: {client.calls}"


def test_checking_complete_no_repeat():
    """测试(bug 回归): 已完成种子反复触发 -> 不重复 recheck/跳检"""
    cfg = make_check_cfg(with_mode="skip-checking", without_mode="full-checking", without_start=True)
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    t = make_target(state="pausedUP", progress=1.0)
    seed_store(mgr, [t])
    for _ in range(3):
        process_rule(mgr, client, t, dry_run=False)
    assert client.calls == [], f"已完成种子不应有任何校验调用: {client.calls}"


# ============================================================
# D. 参考确定 + 模式执行(10)
# ============================================================
def test_checking_filelist_reference_skip_checking():
    """测试: filelist 基础检查确定同组已完成且未校验成员为参考 -> with_reference 段跳检全流程"""
    cfg = make_check_cfg(basic_check="filelist", with_mode="skip-checking", with_start=True)
    mgr = make_mgr(cfg)
    client = CheckingFakeClient()
    mgr.client = client
    client.torrents["HASH123"] = {"state": "stalledUP"}
    t = make_target()
    r = FakeTorrent(hash="R1", name="R1", state="stalledUP")
    inject_group(mgr, "HASH123", "R1")
    seed_store(mgr, [t, r])
    handled, _stop = process_rule(mgr, client, t, dry_run=False)
    assert handled, f"有参考应处理: {client.calls}"
    assert [c[0] for c in client.calls] == ["export", "delete", "add", "start"], f"跳检调用顺序: {client.calls}"
    add_call = [c for c in client.calls if c[0] == "add"][0]
    assert add_call[1]["is_skip_checking"] is True, f"重加应跳过校验: {add_call}"
    assert mgr.state.get("exec_history"), "跳检应记录执行历史"


def test_checking_no_reference_full_checking():
    """测试: 无参考 -> without_reference full-checking 完整流程(提交即发送->轮询续延->完成->start+记录+晋升) """
    cfg = make_check_cfg(without_mode="full-checking", without_start=True)
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    t = make_target()
    t0 = time.time()
    handled, _stop = process_rule(mgr, client, t, dry_run=False)
    assert handled, "应提交校验"
    assert ("recheck", None) in client.calls, f"提交时即应同步发送 recheck: {client.calls}"

    # 重复提交同一种子: 忽略(不再发送)
    client.calls.clear()
    process_rule(mgr, client, t, dry_run=False)
    assert ("recheck", None) not in client.calls, f"重复校验应被忽略: {client.calls}"

    # 模拟客户端进入校验状态 -> 续延(任务保留)
    seed_store(mgr, [make_target(state="checkingDL")])
    run_queue(mgr, t0 + 0.5)
    assert ("start", None) not in client.calls, "校验中不应完成"
    assert len(mgr.task_queue._fast) == 1, "校验中任务应续延保留"

    # 模拟校验完成(退出 checking 状态) -> 自动开始 + 记录 + 晋升
    seed_store(mgr, [make_target(state="pausedUP", progress=1.0)])
    run_queue(mgr, t0 + 2.5)
    assert ("start", None) in client.calls, f"校验完成应自动开始: {client.calls}"
    assert mgr.state.get("exec_history"), "校验完成应记录执行历史"
    assert mgr.store.verified_references == {"HASH123"}, "校验通过应晋升为参考"
    assert mgr.task_queue._fast == [], "完成后任务应消亡"


def test_checking_recheck_fail_cooldown():
    """任务队列驱动: 校验连续失败达上限 -> 冷却当日不再重试(防损坏文件的 recheck 死循环), 次日重置"""
    cfg = make_check_cfg(without_mode="full-checking", without_start=True)
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    # progress 恒 0.5(<1): 每轮轮询都判失败(概括损坏文件); stoppedDL 满足闸门 0
    t = make_target(state="stoppedDL", progress=0.5)
    seed_store(mgr, [t])
    t0 = time.time()
    rule = next(r for r in mgr.enabled_rules if r.name == "example_rules.check_rule")
    origin = mgr._create_rule_task(rule, "HASH123", None)
    origin.interval = 60.0
    mgr.task_queue.add_task(origin, t0)

    # 第 1 次执行: 提交 recheck -> 让位; 轮询(+0.5)判失败(count=1) -> origin reschedule(+60s)
    run_queue(mgr, t0)
    run_queue(mgr, t0 + 0.5)
    assert client.calls.count(("recheck", None)) == 1
    assert mgr.state["recheck_fails"]["HASH123"]["count"] == 1

    # 第 2 次: gate(1<3) -> 再提交; 轮询失败 count=2
    run_queue(mgr, t0 + 61.0)
    run_queue(mgr, t0 + 61.5)
    assert client.calls.count(("recheck", None)) == 2
    assert mgr.state["recheck_fails"]["HASH123"]["count"] == 2

    # 第 3 次: gate(2<3) -> 再提交; 轮询失败 count=3
    run_queue(mgr, t0 + 121.5)
    run_queue(mgr, t0 + 122.0)
    assert client.calls.count(("recheck", None)) == 3
    assert mgr.state["recheck_fails"]["HASH123"]["count"] == 3

    # 第 4 次执行: 冷却生效 -> skip, 不再提交(失败计数保留, 次日重置)
    run_queue(mgr, t0 + 182.0)
    assert client.calls.count(("recheck", None)) == 3, "冷却期内不应再提交"
    assert _recheck_fail_count(mgr, "HASH123") == 3


def test_checking_skip_dedup_across_rules():
    """测试: 跨规则同日去重 —— 规则A跳检后, 规则B同日对同种子跳检被拒(统计只丢一次)"""
    cfg = make_check_cfg(with_mode="skip-checking", without_mode="skip-checking", without_start=False)
    mgr = make_mgr(cfg)
    client = CheckingFakeClient()
    mgr.client = client
    client.torrents["HASH123"] = {"state": "pausedUP"}
    t = make_target()  # pausedDL: 不自动开始, 重加后仍暂停, 规则B才能走到跨规则去重
    handled, _stop = process_rule(mgr, client, t, dry_run=False)
    assert handled and mgr.state["skip_check_day"]["HASH123"], "规则A应完成跳检并记录"

    # 模拟另一条规则B: 换规则名但同种子, 同日再跳检
    rule_b = next(r for r in mgr.enabled_rules if r.name == "example_rules.check_rule")
    client.calls.clear()
    ctx = make_ctx(mgr, t, client, dry_run=False)
    from auto_qb.rules.actions import CheckAction
    action = CheckAction({"basic_check": "filelist", "without_reference": {"enabled": True, "mode": "skip-checking"}})
    ctx.rule_name = "example_rules.rule_b"
    r = action.execute(ctx)
    assert r.is_skipped and "跨规则去重" in r.message, f"规则B应被跨规则去重拒绝: {r}"
    assert client.calls == [], "被拒后不应发生导出/删除/重加"


def test_checking_no_reference_skip_checking_warns():
    """测试: 无参考跳检 -> 执行但记录高风险警告(不降级为 full-checking)"""
    cfg = make_check_cfg(with_mode="skip-checking", without_mode="skip-checking", without_start=True)
    mgr = make_mgr(cfg)
    client = CheckingFakeClient()
    mgr.client = client
    client.torrents["HASH123"] = {"state": "stalledUP"}
    t = make_target()
    with patch("auto_qb.rules.actions.skip_checking.logger.warning") as mw:
        handled, _stop = process_rule(mgr, client, t, dry_run=False)
        assert handled
        assert [c[0] for c in client.calls] == ["export", "delete", "add", "start"], f"{client.calls}"
        assert any("无参考跳检" in str(c) for c in mw.call_args_list), f"应有高风险警告: {mw.call_args_list}"


def test_checking_piecehashes_same():
    """测试: piecehashes 一致 -> 确定参考 -> with_reference 段执行(使用 torrents_piece_hashes API)"""
    cfg = make_check_cfg(basic_check="piecehashes", with_mode="skip-checking", with_start=False)
    mgr = make_mgr(cfg)
    client = CheckingFakeClient()
    mgr.client = client
    client.piece_hashes_map = {"HASH123": ["a", "b"], "R1": ["a", "b"]}  # 一致
    client.torrents["HASH123"] = {"state": "stalledUP"}
    t = make_target()
    r = FakeTorrent(hash="R1", name="R1", state="stalledUP")
    inject_group(mgr, "HASH123", "R1")
    seed_store(mgr, [t, r])
    handled, _stop = process_rule(mgr, client, t, dry_run=False)
    assert handled
    assert ("piece_hashes", "HASH123") in client.calls, f"应获取目标 piece hashes: {client.calls}"
    assert ("piece_hashes", "R1") in client.calls, f"应获取候选 piece hashes: {client.calls}"
    assert [c[0] for c in client.calls] == ["piece_hashes", "piece_hashes", "export", "delete", "add"], \
        f"有参考应走 with_reference 跳检(无 start): {client.calls}"


def test_checking_piecehashes_diff():
    """测试: piecehashes 不一致 -> 无参考 -> without_reference 段"""
    cfg = make_check_cfg(basic_check="piecehashes", without_mode="full-checking", without_start=True)
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    client.piece_hashes_map = {"HASH123": ["a", "b"], "R1": ["a", "c"]}  # 不一致
    t = make_target()
    r = FakeTorrent(hash="R1", name="R1", state="stalledUP")
    inject_group(mgr, "HASH123", "R1")
    seed_store(mgr, [t, r])
    handled, _stop = process_rule(mgr, client, t, dry_run=False)
    assert handled
    assert ("recheck", None) in client.calls, f"无参考应走 full-checking: {client.calls}"
    assert ("export", None) not in client.calls, f"不应跳检: {client.calls}"


def test_checking_piecehashes_api_error():
    """测试: piece hashes API 异常 -> 视为无参考(不中断) -> without_reference 段"""
    cfg = make_check_cfg(basic_check="piecehashes", without_mode="full-checking", without_start=True)
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    client.piece_hashes_error = True
    t = make_target()
    r = FakeTorrent(hash="R1", name="R1", state="stalledUP")
    inject_group(mgr, "HASH123", "R1")
    seed_store(mgr, [t, r])
    handled, _stop = process_rule(mgr, client, t, dry_run=False)
    assert handled, "API 错误不应中断"
    assert ("recheck", None) in client.calls, f"应降级为 full-checking: {client.calls}"


def test_checking_custom_rc0():
    """测试: custom 基础检查 rc=0 -> 候选为参考; 程序参数 = <候选hash> <保存路径>"""
    cfg = make_check_cfg(
        basic_check="custom", custom_program=r"C:\check.exe", with_mode="skip-checking", with_start=False
    )
    mgr = make_mgr(cfg)
    client = CheckingFakeClient()
    mgr.client = client
    client.torrents["HASH123"] = {"state": "stalledUP"}
    t = make_target()
    r = FakeTorrent(hash="R1", name="R1", state="stalledUP")
    inject_group(mgr, "HASH123", "R1")
    seed_store(mgr, [t, r])
    with patch("subprocess.run") as mrun:
        mrun.return_value = SimpleNamespace(returncode=0, stdout="ok", stderr="")
        handled, _stop = process_rule(mgr, client, t, dry_run=False)
        assert handled
        args = mrun.call_args.args[0]
        assert args == [r"C:\check.exe", "R1", r"R:\Downloads"], f"程序参数: {args}"
        assert ("export", "HASH123") in client.calls, f"有参考应走 with_reference 段: {client.calls}"


def test_checking_custom_rc1():
    """测试: custom 基础检查 rc!=0 -> 非参考 -> without_reference 段"""
    cfg = make_check_cfg(
        basic_check="custom", custom_program=r"C:\check.exe", without_mode="full-checking", without_start=True
    )
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    t = make_target()
    r = FakeTorrent(hash="R1", name="R1", state="stalledUP")
    inject_group(mgr, "HASH123", "R1")
    seed_store(mgr, [t, r])
    with patch("subprocess.run") as mrun:
        mrun.return_value = SimpleNamespace(returncode=1, stdout="", stderr="bad")
        handled, _stop = process_rule(mgr, client, t, dry_run=False)
        assert handled
    assert ("recheck", None) in client.calls, f"无参考应走 full-checking: {client.calls}"
    assert ("export", None) not in client.calls, f"不应跳检: {client.calls}"


def test_checking_verified_reference_used():
    """测试: 内存 verified_references 与 basic_check 并集作参考(即使成员非上传状态)"""
    cfg = make_check_cfg(with_mode="skip-checking", with_start=False)
    mgr = make_mgr(cfg)
    client = CheckingFakeClient()
    mgr.client = client
    client.torrents["HASH123"] = {"state": "stalledUP"}
    mgr.store.verified_references = {"R1"}  # 历史 full-checking 通过
    t = make_target()
    r = FakeTorrent(hash="R1", name="R1", state="pausedUP")  # 非上传候选, 仅靠 verified
    inject_group(mgr, "HASH123", "R1")
    seed_store(mgr, [t, r])
    handled, _stop = process_rule(mgr, client, t, dry_run=False)
    assert handled
    assert ("export", "HASH123") in client.calls, f"verified 参考应走 with_reference 段: {client.calls}"


def test_checking_verified_references_not_persisted():
    """测试: verified_references 仅内存, 重启后重新积累(不写 state_file)"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        cfg = make_check_cfg(without_mode="full-checking", without_start=True)
        cfg.state_file = state_file
        mgr = QbManager("", config=cfg, no_lock=True)  # 测试不持锁
        mgr._load_rules()  # run() 中才自动加载; 测试直接构造后需手动加载规则
        mgr.task_queue = TaskQueue()
        client = CheckingFakeClient()
        mgr.client = client
        t = make_target()
        t0 = time.time()
        process_rule(mgr, client, t, dry_run=False)  # 提交即发送 recheck
        seed_store(mgr, [make_target(state="checkingDL")])  # 校验中
        run_queue(mgr, t0 + 0.5)
        seed_store(mgr, [make_target(state="pausedUP", progress=1.0)])  # 完成
        run_queue(mgr, t0 + 2.5)
        assert mgr.store.verified_references == {"HASH123"}, "完成后应晋升"
        mgr.save_state()

        mgr2 = QbManager("", config=cfg, no_lock=True)  # 测试不持锁  # 重新加载同一 state 文件
        assert mgr2.store.verified_references == set(), "verified 参考不应持久化"


# ============================================================
# E. 跳检保护 + 异步细节(9)
# ============================================================
def test_checking_skip_guard_file_missing():
    """测试: 跳检前置 filelist 检查失败(文件缺失) -> 不执行导出/删除"""
    cfg = make_check_cfg(with_mode="skip-checking", without_mode="skip-checking")
    mgr = make_mgr(cfg)
    client = CheckingFakeClient()
    mgr.client = client
    client.files = [SimpleNamespace(name="missing.bin", size=100)]
    t = make_target()
    handled, _stop = process_rule(mgr, client, t, dry_run=False)
    assert not handled, "前置检查失败应跳过(不执行任何 API)"
    assert client.calls == [], f"前置失败不应有任何调用: {client.calls}"


def test_checking_skip_guard_file_size_mismatch():
    """测试: 跳检前置 filelist 检查失败(文件存在但大小不符) -> 不执行导出/删除"""
    with tempfile.TemporaryDirectory() as td:
        cfg = make_check_cfg(with_mode="skip-checking", without_mode="skip-checking")
        mgr = make_mgr(cfg)
        client = CheckingFakeClient()
        mgr.client = client
        real = os.path.join(td, "movie.mkv")
        with open(real, "wb") as f:
            f.write(b"x" * 10)
        client.files = [SimpleNamespace(name="movie.mkv", size=999)]  # 期望 999, 实际 10
        t = make_target()
        t.save_path = td
        handled, _stop = process_rule(mgr, client, t, dry_run=False)
        assert not handled, "前置检查失败应跳过(不执行任何 API)"
        assert client.calls == [], f"大小不符不应有任何调用: {client.calls}"


def test_checking_skip_guard_add_fail_backup():
    """测试: 重加失败 -> .torrent 落盘备份 + skip_check_backup 元数据"""
    with tempfile.TemporaryDirectory() as td:
        cfg = make_check_cfg(with_mode="skip-checking", without_mode="skip-checking")
        cfg.state_file = os.path.join(td, "state.json")
        mgr = make_mgr(cfg)
        client = CheckingFakeClient()
        mgr.client = client
        client.torrents["HASH123"] = {"state": "stalledUP"}
        client.add_error = RuntimeError("simulated add failure")
        t = make_target()
        process_rule(mgr, client, t, dry_run=False)
        backup = mgr.state.get("skip_check_backup", {}).get("HASH123")
        assert backup, f"重加失败应记录备份元数据: {mgr.state}"
        assert os.path.exists(backup["path"]), f"备份文件应存在: {backup}"
        assert ("export", "HASH123") in client.calls, "应先导出"
        assert ("delete", False) in client.calls, "应先删除种子"


def test_checking_skip_partial_download_forbidden():
    """测试: 部分下载(0<progress<1)禁止跳检 —— 预分配零块会被当作有效数据上传(垃圾数据)"""
    cfg = make_check_cfg(with_mode="skip-checking", without_mode="skip-checking", without_start=True)
    mgr = make_mgr(cfg)
    client = CheckingFakeClient()
    mgr.client = client
    client.torrents["HASH123"] = {"state": "pausedDL"}
    t = make_target(progress=0.4)
    handled, _stop = process_rule(mgr, client, t, dry_run=False)
    assert handled, "拒检以 fail 返回(fail 视为已处理), 非 skip"
    assert client.calls == [], f"不应发生导出/删除/重加: {client.calls}"


def test_checking_skip_dedup_same_day():
    """测试: 同日去重 -> 同一天不重复跳检"""
    cfg = make_check_cfg(with_mode="skip-checking", without_mode="skip-checking", with_start=True)
    mgr = make_mgr(cfg)
    client = CheckingFakeClient()
    mgr.client = client
    client.torrents["HASH123"] = {"state": "stalledUP"}
    t = make_target()
    handled, _stop = process_rule(mgr, client, t, dry_run=False)
    assert handled
    assert [c[0] for c in client.calls] == ["export", "delete", "add", "start"]

    client.calls.clear()
    handled, _stop = process_rule(mgr, client, t, dry_run=False)
    assert not handled, "同日不应重复跳检"
    assert ("delete", False) not in client.calls, f"同日不应删除种子: {client.calls}"


def test_checking_dry_run():
    """测试: dry-run -> 不调用任何客户端 API(含校验/跳检)"""
    cfg = make_check_cfg(with_mode="skip-checking", without_mode="full-checking")
    mgr = make_mgr(cfg)
    client = CheckingFakeClient()
    mgr.client = client
    t = make_target()
    handled, _stop = process_rule(mgr, client, t, dry_run=True)
    assert handled, "dry-run 应正常返回"
    assert client.calls == [], f"dry-run 不应调用客户端: {client.calls}"


def test_checking_full_checking_pending():
    """测试: 校验未完成 -> 轮询任务续延保留(不丢失) """
    cfg = make_check_cfg(without_mode="full-checking")
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    t = make_target()
    t0 = time.time()
    process_rule(mgr, client, t, dry_run=False)
    assert ("recheck", None) in client.calls, f"提交时即应发送 recheck: {client.calls}"
    # 模拟校验中 -> 任务续延保留
    seed_store(mgr, [make_target(state="checkingDL")])
    run_queue(mgr, t0 + 0.5)
    assert len(mgr.task_queue._fast) == 1, "任务应保留(续延)"


def test_checking_full_checking_dup_ignore():
    """测试: 同一种子重复提交校验 -> 忽略(仅一次 recheck) """
    cfg = make_check_cfg(without_mode="full-checking")
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    t = make_target()
    process_rule(mgr, client, t, dry_run=False)
    process_rule(mgr, client, t, dry_run=False)  # 重复 -> 忽略
    n_recheck = sum(1 for c in client.calls if c[0] == "recheck")
    assert n_recheck == 1, f"recheck 应只发送一次: {client.calls}"


def test_checking_full_checking_auto_start_false():
    """测试: auto_start=false -> 校验完成不自动开始, 仍记录执行 + 晋升参考 """
    cfg = make_check_cfg(without_mode="full-checking", without_start=False)
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    t = make_target()
    t0 = time.time()
    process_rule(mgr, client, t, dry_run=False)  # 提交即发送
    seed_store(mgr, [make_target(state="checkingDL")])  # 校验中
    run_queue(mgr, t0 + 0.5)
    seed_store(mgr, [make_target(state="pausedUP", progress=1.0)])  # 完成
    run_queue(mgr, t0 + 2.5)
    assert ("start", None) not in client.calls, f"auto_start=false 不应自动开始: {client.calls}"
    assert mgr.state.get("exec_history"), "仍应记录执行历史"
    assert mgr.store.verified_references == {"HASH123"}, "仍应晋升参考"


def test_checking_full_checking_send_error():
    """测试: 校验请求发送失败 -> 动作失败(不晋升/不开始), 轮询任务自然消亡 """
    cfg = make_check_cfg(without_mode="full-checking", without_start=True)
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    client.recheck_error = RuntimeError("simulated recheck failure")
    t = make_target()
    t0 = time.time()
    with patch("auto_qb.rules.base.logger.warning") as mw:
        handled, _stop = process_rule(mgr, client, t, dry_run=False)
        assert handled, "发送失败应返回失败结果(动作已执行)"
        assert any("发送 recheck 失败" in str(c) for c in mw.call_args_list), \
            f"应有失败警告: {mw.call_args_list}"
        run_queue(mgr, t0 + 0.5)  # 轮询任务: 种子无快照 -> 消亡
    assert ("start", None) not in client.calls, "发送失败不应自动开始"
    assert ("recheck", None) not in client.calls, f"发送失败不应产生 recheck 调用: {client.calls}"
    assert mgr.store.verified_references == set(), "发送失败不应晋升参考"
    assert mgr.task_queue._fast == [], "发送失败任务应消亡"
    assert mgr.task_queue._active_checks == set(), "消亡应释放校验标记"


def test_checking_full_checking_defer_resume():
    """任务队列驱动: 触发任务让位(pending+断点) -> 校验成功 -> resume 续跑(记录执行历史) """
    cfg = make_check_cfg(without_mode="full-checking", without_start=True)
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    t = make_target()
    seed_store(mgr, [t])
    t0 = time.time()
    rule = next(r for r in mgr.enabled_rules if r.name == "example_rules.check_rule")
    origin = mgr._create_rule_task(rule, "HASH123", None)
    origin.interval = 60.0
    mgr.task_queue.add_task(origin, t0)
    # 首次执行: checking 提交 -> pending 中断 + 让位 + 记录断点
    run_queue(mgr, t0)
    assert origin.state == DEFERRED, "触发任务应让位"
    assert origin in mgr.task_queue._deferred, "让位任务应挂起"
    assert origin.resume_index == 1, "应记录断点(下一个动作索引)"
    assert ("recheck", None) in client.calls, "提交时即应同步发送 recheck"
    # 校验中 -> 轮询续延, 触发任务保持让位, 断点保留
    seed_store(mgr, [make_target(state="checkingDL")])
    run_queue(mgr, t0 + 0.5)
    assert origin.state == DEFERRED, "校验中触发任务保持让位"
    assert origin.resume_index == 1, "校验中断点保留"
    # 校验完成(progress=1.0) -> resume: 完成处理(晋升) + 重新入队(断点保留)
    seed_store(mgr, [make_target(state="pausedUP", progress=1.0)])
    run_queue(mgr, t0 + 2.5)
    assert origin.state == PENDING, "成功后应 resume 重新入队"
    assert origin not in mgr.task_queue._deferred, "恢复后应移出让位集合"
    assert mgr.store.verified_references == {"HASH123"}, "成功应晋升参考"
    assert origin.resume_index == 1, "resume 应保留断点(续跑语义)"
    assert not mgr.state.get("exec_history"), "执行历史应由续跑完成时记录"
    # 续跑: origin 到期 -> 跳过条件/去重 -> 从断点继续(单动作规则: 空循环) -> 记录执行
    run_queue(mgr, t0 + 60.5)
    assert mgr.state.get("exec_history"), "续跑完成应记录执行历史"
    assert origin.resume_index is None, "断点应已消费清零"


def test_checking_full_checking_resume_continues_actions():
    """断点续跑: 规则 [checking, start] 校验成功 -> resume 后续跑执行剩余动作 start """
    cfg = make_check_cfg(without_mode="full-checking", without_start=False, extra_actions=[{"start": True}])
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    t = make_target()
    seed_store(mgr, [t])
    t0 = time.time()
    rule = next(r for r in mgr.enabled_rules if r.name == "example_rules.check_rule")
    origin = mgr._create_rule_task(rule, "HASH123", None)
    origin.interval = 60.0
    mgr.task_queue.add_task(origin, t0)
    run_queue(mgr, t0)
    assert origin.state == DEFERRED and origin.resume_index == 1, "checking pending 应中断并记录断点"
    assert ("recheck", None) in client.calls, "应发送 recheck"
    assert ("start", None) not in client.calls, "pending 中断, 后续动作未执行"
    # 校验完成 -> resume
    seed_store(mgr, [make_target(state="checkingDL")])
    run_queue(mgr, t0 + 0.5)
    seed_store(mgr, [make_target(state="pausedUP", progress=1.0)])
    run_queue(mgr, t0 + 2.5)
    assert origin.state == PENDING and origin.resume_index == 1
    assert mgr.store.verified_references == {"HASH123"}
    assert not mgr.state.get("exec_history"), "续跑完成前不记录执行历史"
    # 续跑: 执行断点后的 start(最新快照 pausedUP -> 暂停 -> 执行 start)
    run_queue(mgr, t0 + 60.5)
    assert ("start", None) in client.calls, f"续跑应执行后续动作 start: {client.calls}"
    assert mgr.state.get("exec_history"), "续跑完成应记录执行历史"
    assert origin.resume_index is None, "断点应已消费清零"


def test_checking_full_checking_resume_skips_conditions():
    """续跑跳过条件评估: 首次条件匹配 -> pending; 校验完成后条件不再匹配, 续跑仍执行后续动作 """
    cfg = make_check_cfg(without_mode="full-checking", without_start=False, extra_actions=[{"start": True}])
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    t = make_target()
    seed_store(mgr, [t])
    t0 = time.time()
    rule = next(r for r in mgr.enabled_rules if r.name == "example_rules.check_rule")
    origin = mgr._create_rule_task(rule, "HASH123", None)
    origin.interval = 60.0
    mgr.task_queue.add_task(origin, t0)
    run_queue(mgr, t0)
    assert origin.state == DEFERRED and origin.resume_index == 1
    # 校验完成后条件不再匹配(标签已变), 但续跑应跳过条件评估仍执行 start
    seed_store(mgr, [make_target(state="checkingDL")])
    run_queue(mgr, t0 + 0.5)
    seed_store(mgr, [make_target(state="pausedUP", progress=1.0, tags="已处理")])
    run_queue(mgr, t0 + 2.5)
    assert origin.state == PENDING, "resume 不应受条件变化影响"
    run_queue(mgr, t0 + 60.5)
    assert ("start", None) in client.calls, f"续跑应跳过条件评估执行 start: {client.calls}"
    assert mgr.state.get("exec_history"), "续跑完成应记录执行历史"


def test_checking_full_checking_resume_skips_dedup():
    """续跑跳过去重: execute_once=once 规则校验成功续跑不被 dedup 拦截(执行历史在续跑完成才记录) """
    cfg = make_check_cfg(
        without_mode="full-checking", without_start=False, extra_actions=[{
            "start": True
        }], execute_once="once"
    )
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    t = make_target()
    seed_store(mgr, [t])
    t0 = time.time()
    rule = next(r for r in mgr.enabled_rules if r.name == "example_rules.check_rule")
    origin = mgr._create_rule_task(rule, "HASH123", None)
    origin.interval = 60.0
    mgr.task_queue.add_task(origin, t0)
    run_queue(mgr, t0)
    assert origin.state == DEFERRED and origin.resume_index == 1, "首次执行 dedup 通过 -> pending"
    # 校验完成 -> resume
    seed_store(mgr, [make_target(state="checkingDL")])
    run_queue(mgr, t0 + 0.5)
    seed_store(mgr, [make_target(state="pausedUP", progress=1.0)])
    run_queue(mgr, t0 + 2.5)
    assert origin.state == PENDING and origin.resume_index == 1
    # 续跑: 若重走决策链则 execute_once=once 拦截; 断点续跑应跳过 dedup 执行 start
    run_queue(mgr, t0 + 60.5)
    assert ("start", None) in client.calls, f"续跑应跳过去重执行 start: {client.calls}"
    assert mgr.state.get("exec_history"), "续跑完成应记录执行历史"
    assert origin.resume_index is None


def test_checking_full_checking_defer_fail_retry():
    """任务队列驱动: 校验未通过(progress<1) -> 清断点 + reschedule 重新入队重试(重走决策链) """
    cfg = make_check_cfg(without_mode="full-checking", without_start=True)
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    t = make_target()
    seed_store(mgr, [t])
    t0 = time.time()
    rule = next(r for r in mgr.enabled_rules if r.name == "example_rules.check_rule")
    origin = mgr._create_rule_task(rule, "HASH123", None)
    origin.interval = 60.0
    mgr.task_queue.add_task(origin, t0)
    run_queue(mgr, t0)
    assert origin.state == DEFERRED and origin.resume_index == 1, "首次执行应让位并记录断点"
    # 校验完成但 progress<1(文件不完整) -> 失败 -> 清断点 + reschedule
    seed_store(mgr, [make_target(state="pausedDL", progress=0.5)])
    run_queue(mgr, t0 + 2.5)
    assert origin.state == PENDING, "失败后应 reschedule 重新入队重试"
    assert origin not in mgr.task_queue._deferred, "重试后应移出让位集合"
    assert origin.resume_index is None, "失败应清断点(重走完整决策链)"
    assert mgr.store.verified_references == set(), "失败不应晋升参考"
    assert not mgr.state.get("exec_history"), "失败不应记录执行历史"
    # 重走决策链: origin 到期 -> 重新 full-checking(再次让位 + 再发 recheck)
    run_queue(mgr, t0 + 60.5)
    assert origin.state == DEFERRED, "重走决策链应再次校验(再次让位)"
    assert origin.resume_index == 1, "重新校验应再次记录断点"


# ============================================================
# G. 组内校验串行化(决策链 1.5/1.6)
# ============================================================
def test_checking_group_full_checking_serialized():
    """同组 full-checking 串行: A 提交后 B 让位等待(不提交 recheck); A 成功晋升参考 -> B 恢复走 with_reference 跳检"""
    cfg = make_check_cfg(without_mode="full-checking", without_start=True)
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    a = make_target(hash="HA")
    b = make_target(hash="HB")
    seed_store(mgr, [a, b])
    inject_group(mgr, "HA", "HB")
    rule = next(r for r in mgr.enabled_rules if r.name == "example_rules.check_rule")
    t0 = time.time()
    ta = mgr._create_rule_task(rule, "HA", None)
    tb = mgr._create_rule_task(rule, "HB", None)
    ta.interval = 60.0
    tb.interval = 60.0
    # A 先执行: 提交 recheck(在途登记) + 让位; HA 进入校验态后 B 再执行
    mgr.task_queue.add_task(ta, t0)
    run_queue(mgr, t0)
    seed_store(mgr, [make_target(hash="HA", state="checkingDL"), b])
    mgr.task_queue.add_task(tb, t0 + 0.1)
    run_queue(mgr, t0 + 0.1)
    assert ("recheck", None) in client.calls, "A 应提交 recheck"
    assert client.calls.count(("recheck", None)) == 1, f"B 不应提交 recheck: {client.calls}"
    assert mgr.task_queue.active_check_hashes() == {"HA"}, "A 应登记在途(等待任务不占用登记)"
    assert ta.state == DEFERRED and tb.state == DEFERRED, "A/B 均应让位"
    assert tb.resume_index == 1, "B 应记录断点(pending)"
    # HA 校验中: A 轮询续延, B 等待任务续等(间距放大避开真实时钟重排的边界)
    run_queue(mgr, t0 + 10.0)
    assert tb.state == DEFERRED, "HA 校验中 B 保持等待"
    # HA 校验成功 -> 晋升参考; B 等待任务发现组内已清 -> resume B 重走决策链
    seed_store(mgr, [make_target(hash="HA", state="pausedUP", progress=1.0), b])
    run_queue(mgr, t0 + 20.0)
    assert mgr.store.verified_references == {"HA"}, "成功应晋升参考"
    assert mgr.task_queue.active_check_hashes() == set(), "轮询消亡应释放在途登记"
    # B 的恢复重走发生在等待任务 resume 之后(下一批到期): 命中 verified 参考 -> with_reference 跳检
    run_queue(mgr, t0 + 90.0)
    assert mgr.task_queue.active_check_hashes() == set(), "等待任务不登记在途"
    run_queue(mgr, t0 + 150.0)
    names = [c[0] for c in client.calls]
    assert names.count("recheck") == 1, f"B 恢复后不应再提交 recheck: {client.calls}"
    assert "export" in names and "delete" in names, f"B 应走跳检流程: {client.calls}"
    add_call = [c for c in client.calls if c[0] == "add"][0]
    assert add_call[1]["is_skip_checking"] is True, "B 应以跳检方式重加"


def test_checking_group_skip_on_same_data_fail():
    """决策链 1.6: 同组 A 校验失败且文件映射一致(同一物理数据) -> B 直接 skip, 不提交 recheck"""
    cfg = make_check_cfg(without_mode="full-checking", without_start=True)
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    a = make_target(hash="HA")
    b = make_target(hash="HB")
    seed_store(mgr, [a, b])
    inject_group(mgr, "HA", "HB")
    key = mgr.store.member_to_key["HA"]
    mgr.store.group_sizes.setdefault(key, {})["HA"] = {"movie.mkv": 100}
    mgr.store.group_sizes[key]["HB"] = {"movie.mkv": 100}
    mgr.state.setdefault("recheck_fails", {})["HA"] = {"date": date.today().isoformat(), "count": 1}
    rule = next(r for r in mgr.enabled_rules if r.name == "example_rules.check_rule")
    tb = mgr._create_rule_task(rule, "HB", None)
    mgr.task_queue.add_task(tb, time.time())
    run_queue(mgr)
    assert client.calls.count(("recheck", None)) == 0, f"同数据失败推断: B 不应提交 recheck: {client.calls}"
    assert tb.state == PENDING and tb.resume_index is None, "B 应正常完成(非让位)"


def test_checking_group_no_infer_when_sizes_differ():
    """决策链 1.6 不推断: 组内文件映射不一致(校验的是不同数据) -> B 照常提交 full-checking"""
    cfg = make_check_cfg(without_mode="full-checking", without_start=True)
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    a = make_target(hash="HA")
    b = make_target(hash="HB")
    seed_store(mgr, [a, b])
    inject_group(mgr, "HA", "HB")
    key = mgr.store.member_to_key["HA"]
    mgr.store.group_sizes.setdefault(key, {})["HA"] = {"movie.mkv": 100}
    mgr.store.group_sizes[key]["HB"] = {"movie.mkv": 200}  # 大小不一致
    mgr.state.setdefault("recheck_fails", {})["HA"] = {"date": date.today().isoformat(), "count": 1}
    rule = next(r for r in mgr.enabled_rules if r.name == "example_rules.check_rule")
    tb = mgr._create_rule_task(rule, "HB", None)
    mgr.task_queue.add_task(tb, time.time())
    run_queue(mgr)
    assert ("recheck", None) in client.calls, "映射不一致不应推断, B 照常校验"
    assert mgr.task_queue.active_check_hashes() == {"HB"}, "B 提交后应登记在途"
    assert tb.state == DEFERRED, "B 应让位等待校验结果"


def test_checking_group_wait_external_entry_skip():
    """决策链 1.5: 组内其它成员校验中且无任务驱动(外部入口) -> skip 不等待"""
    cfg = make_check_cfg(without_mode="full-checking", without_start=True)
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    a = make_target(hash="HA", state="checkingDL")  # 组内其它成员校验中(store 快照可见)
    b = make_target(hash="HB")
    seed_store(mgr, [a, b])
    inject_group(mgr, "HA", "HB")
    handled, _stop = process_rule(mgr, client, b, dry_run=False)
    assert not handled, "组内有校验进行时应跳过"
    assert ("recheck", None) not in client.calls, "外部入口不等待也不提交"


def test_checking_group_wait_timeout_force_resume():
    """等待超时兜底: 超时强制恢复重走决策链(防在途登记泄漏活锁), 组内仍在校验则再次让位"""
    cfg = make_check_cfg(without_mode="full-checking", without_start=True)
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    a = make_target(hash="HA", state="checkingDL")
    b = make_target(hash="HB")
    seed_store(mgr, [a, b])
    inject_group(mgr, "HA", "HB")
    rule = next(r for r in mgr.enabled_rules if r.name == "example_rules.check_rule")
    tb = mgr._create_rule_task(rule, "HB", None)
    tb.interval = 60.0
    t0 = time.time()
    mgr.task_queue.add_task(tb, t0)
    run_queue(mgr, t0)
    assert tb.state == DEFERRED, "B 应让位等待"
    with patch("auto_qb.rules.actions.full_checking.GROUP_CHECK_WAIT_LIMIT", 0.0):
        seed_store(mgr, [a, b])  # HA 持续校验中
        run_queue(mgr, t0 + 60.5)  # 等待任务超时 -> 强制 resume -> B 重走决策链 -> 仍在校验 -> 再次让位
    assert tb.state == DEFERRED, "超时强制恢复后应重走决策链并再次让位"
    assert tb.resume_index == 1, "再次让位应保留断点"
    assert client.calls.count(("recheck", None)) == 0, f"B 全程不应提交 recheck: {client.calls}"
