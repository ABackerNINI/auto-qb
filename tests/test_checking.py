"""test_checking 测试计划: checking 动作详细自测(不连接真实 qB, 用模拟对象)

## 测试计划(每个测试函数一条)
- test_checking_config_string_rejected: 配置 fail-fast: basic_check 为字符串时报错
- test_checking_config_missing_basic_check: 缺 basic_check 报错
- test_checking_config_invalid_basic_check: 非法 basic_check 值报错
- test_checking_config_missing_section: 缺 checking 配置段报错
- test_checking_config_invalid_mode: 非法 mode 值报错
- test_checking_config_unknown_keys: 未知配置键报错
- test_checking_config_custom_without_program: custom 模式缺 program 报错
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
- test_checking_paused_completed_not_reference: 暂停已完成不算参考种子
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
- test_checking_dry_run: dry-run 不发送请求
- test_checking_full_checking_pending: 全检任务 pending 保留
- test_checking_full_checking_dup_ignore: 全检重复提交忽略
- test_checking_full_checking_auto_start_false: auto_start=false 不自动开始
- test_checking_full_checking_send_error: 发送失败处理
- test_checking_no_task_queue_direct_recheck: 无任务队列时直接 recheck
"""
import os
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from auto_qb.qbmanager import QbManager
from auto_qb.rules.actions import CheckAction
from auto_qb.taskqueue import TaskQueue
from helpers import FakeClient, FakeConfig, FakeTorrent


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
    custom_program=None
):
    """构造 checking 规则配置(条件: 标签含"需校验")"""
    cfg = FakeConfig()
    action = {
        "checking":
            {
                "basic_check": basic_check,
                "with_reference": {
                    "mode": with_mode,
                    "auto_start": with_start
                },
                "without_reference": {
                    "mode": without_mode,
                    "auto_start": without_start
                },
            }
    }
    if custom_program:
        action["checking"]["custom_basic_check_program_path"] = custom_program
    cfg.rules_config = {
        "example_rules":
            {
                "check_rule":
                    {
                        "enabled": True,
                        "conditions": [{
                            "tags": "需校验"
                        }],
                        "actions": [action],
                        "stop_following_rules_if": "never",
                    },
            }
    }
    return cfg


def make_mgr(cfg, with_tq=False):
    """构造 QbManager(可选同步模式任务队列)"""
    mgr = QbManager("", config=cfg)
    if with_tq:
        mgr.task_queue = TaskQueue(executor_workers=0)
    return mgr


def inject_group(mgr, *hashes, key=("KEY", )):
    """把 hashes 注入同一组(绕过归组流程, 直接构造内部结构)"""
    mgr._groups[key] = list(hashes)
    for h in hashes:
        mgr._group_member_to_key[h] = key


def make_target(state="stalledUP", hash="HASH123"):
    return FakeTorrent(hash=hash, name="T", tags="需校验", state=state)


def _seg(mode, start=True):
    return {"mode": mode, "auto_start": start}


# ============================================================
# A. 配置 fail-fast(8)
# ============================================================
def test_checking_config_string_rejected():
    """测试: checking 只接受 dict, 旧字符串形式直接报错(无需兼容)"""
    for bad in ("skip-checking", "full-checking", "filelist"):
        try:
            CheckAction(bad)
            assert False, f"字符串配置 {bad} 应报错"
        except ValueError:
            pass


def test_checking_config_missing_basic_check():
    """测试: 缺 basic_check -> 报错"""
    try:
        CheckAction({"with_reference": _seg("skip-checking"), "without_reference": _seg("full-checking")})
        assert False, "缺 basic_check 应报错"
    except ValueError:
        pass


def test_checking_config_invalid_basic_check():
    """测试: basic_check 取值非法 -> 报错"""
    try:
        CheckAction(
            {
                "basic_check": "xxx",
                "with_reference": _seg("skip-checking"),
                "without_reference": _seg("full-checking")
            }
        )
        assert False, "非法 basic_check 应报错"
    except ValueError:
        pass


def test_checking_config_missing_section():
    """测试: with_reference/without_reference 缺段或非 dict -> 报错"""
    cases = [
        {
            "basic_check": "filelist",
            "without_reference": _seg("full-checking")
        },  # 缺 with
        {
            "basic_check": "filelist",
            "with_reference": _seg("skip-checking")
        },  # 缺 without
        {
            "basic_check": "filelist",
            "with_reference": "skip-checking",
            "without_reference": _seg("full-checking")
        },  # with 非 dict
        {
            "basic_check": "filelist",
            "with_reference": _seg("skip-checking"),
            "without_reference": "full-checking"
        },  # without 非 dict
    ]
    for spec in cases:
        try:
            CheckAction(spec)
            assert False, f"非法段配置应报错: {spec}"
        except ValueError:
            pass


def test_checking_config_invalid_mode():
    """测试: with/without 段 mode 取值非法 -> 报错"""
    cases = [
        {
            "basic_check": "filelist",
            "with_reference": _seg("xxx"),
            "without_reference": _seg("full-checking")
        },
        {
            "basic_check": "filelist",
            "with_reference": _seg("skip-checking"),
            "without_reference": _seg("yyy")
        },
    ]
    for spec in cases:
        try:
            CheckAction(spec)
            assert False, f"非法 mode 应报错: {spec}"
        except ValueError:
            pass


def test_checking_config_unknown_keys():
    """测试: 已移除的键(always_check_first_one/poll_timeout/顶层 mode)报错"""
    base = {
        "basic_check": "filelist",
        "with_reference": _seg("skip-checking"),
        "without_reference": _seg("full-checking")
    }
    for key, val in (("always_check_first_one", True), ("poll_timeout", "60S"), ("mode", "full-checking")):
        spec = dict(base)
        spec[key] = val
        try:
            CheckAction(spec)
            assert False, f"未知键 {key} 应报错"
        except ValueError:
            pass


def test_checking_config_custom_without_program():
    """测试: basic_check=custom 缺 custom_basic_check_program_path(含空白)-> 报错"""
    for path in (None, "", "  "):
        spec = {
            "basic_check": "custom",
            "with_reference": _seg("skip-checking"),
            "without_reference": _seg("full-checking")
        }
        if path is not None:
            spec["custom_basic_check_program_path"] = path
        try:
            CheckAction(spec)
            assert False, f"custom 缺路径应报错: {path!r}"
        except ValueError:
            pass


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
    inject_group(mgr, "D1", "D2")
    by_hash = {
        "D1": FakeTorrent(hash="D1", name="D1", state="downloading"),
        "D2": FakeTorrent(hash="D2", name="D2", state="downloading"),
    }
    mgr._check_download_conflicts(by_hash, dry_run=True)
    assert ("stop", None) not in client.calls, f"dry-run 不应暂停: {client.calls}"
    mgr._check_download_conflicts(by_hash, dry_run=False)
    assert client.calls.count(("stop", None)) == 1, f"整组应暂停一次: {client.calls}"


def test_download_conflict_mixed():
    """测试: 已完成与下载中并存 -> 警告 + 整组暂停"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    inject_group(mgr, "U1", "D1")
    by_hash = {
        "U1": FakeTorrent(hash="U1", name="U1", state="stalledUP", amount_left=0),
        "D1": FakeTorrent(hash="D1", name="D1", state="downloading"),
    }
    mgr._check_download_conflicts(by_hash, dry_run=False)
    assert client.calls.count(("stop", None)) == 1, f"混合并存应整组暂停: {client.calls}"


def test_download_conflict_no_repeat():
    """测试: 冲突持续 -> 不重复暂停(幂等去重)"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    inject_group(mgr, "D1", "D2")
    by_hash = {
        "D1": FakeTorrent(hash="D1", name="D1", state="downloading"),
        "D2": FakeTorrent(hash="D2", name="D2", state="downloading"),
    }
    mgr._check_download_conflicts(by_hash, dry_run=False)
    mgr._check_download_conflicts(by_hash, dry_run=False)
    mgr._check_download_conflicts(by_hash, dry_run=False)
    assert client.calls.count(("stop", None)) == 1, f"冲突持续不应重复暂停: {client.calls}"


def test_download_conflict_resolve_recur():
    """测试: 冲突消除后清除去重, 重现时再次警告+暂停"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    inject_group(mgr, "D1", "D2")
    by_hash = {
        "D1": FakeTorrent(hash="D1", name="D1", state="downloading"),
        "D2": FakeTorrent(hash="D2", name="D2", state="downloading"),
    }
    mgr._check_download_conflicts(by_hash, dry_run=False)
    assert client.calls.count(("stop", None)) == 1

    # 冲突消除(全组完成, 无下载中): 不再暂停, 去重记录清除
    by_hash["D1"].state = "stalledUP"
    by_hash["D1"].amount_left = 0
    by_hash["D2"].state = "stalledUP"
    by_hash["D2"].amount_left = 0
    mgr._check_download_conflicts(by_hash, dry_run=False)
    assert client.calls.count(("stop", None)) == 1, f"冲突消除后不应暂停: {client.calls}"

    # 冲突重现(D2 重新下载): 再次暂停(记录已清除, 新冲突类型 mixed)
    by_hash["D2"].state = "downloading"
    by_hash["D2"].amount_left = 1
    mgr._check_download_conflicts(by_hash, dry_run=False)
    assert client.calls.count(("stop", None)) == 2, f"冲突重现应再次暂停: {client.calls}"


def test_download_conflict_single_dl():
    """测试: 单下载中(无已完成)不冲突; 多组互不影响"""
    mgr = make_mgr(FakeConfig())
    client = FakeClient()
    mgr.client = client
    inject_group(mgr, "D1", key=("K1", ))
    inject_group(mgr, "U1", key=("K2", ))
    by_hash = {
        "D1": FakeTorrent(hash="D1", name="D1", state="downloading", amount_left=1),  # 未完成
        "U1": FakeTorrent(hash="U1", name="U1", state="stalledUP", amount_left=0),
    }
    mgr._check_download_conflicts(by_hash, dry_run=False)
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
        assert mgr._groups == {}, f"分组未启用不应有分组: {mgr._groups}"


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
    mgr._snapshot = [t, d]
    handled = mgr.process_torrent(t, dry_run=False)
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
    mgr._snapshot = [t, pd]
    handled = mgr.process_torrent(t, dry_run=False)
    assert handled, "暂停未完成不应跳过"
    assert ("recheck", None) in client.calls, f"无参考应走 full-checking: {client.calls}"


def test_checking_no_group_uses_without_reference():
    """测试: 分组未启用/未归组 -> 视为单种子组, 无参考 -> without_reference 段"""
    cfg = make_check_cfg(without_mode="full-checking", without_start=True)
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    t = make_target()
    mgr._snapshot = [t]
    handled = mgr.process_torrent(t, dry_run=False)
    assert handled
    assert ("recheck", None) in client.calls, f"无参考应走 full-checking: {client.calls}"


def test_checking_paused_completed_not_reference():
    """测试: 暂停中的已完成(pausedUP)不算参考候选 -> 无参考 -> without_reference 段"""
    cfg = make_check_cfg(with_mode="skip-checking", without_mode="full-checking", without_start=True)
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    t = make_target()
    p = FakeTorrent(hash="P1", name="P1", state="pausedUP")  # 暂停已完成, 非上传
    inject_group(mgr, "HASH123", "P1")
    mgr._snapshot = [t, p]
    handled = mgr.process_torrent(t, dry_run=False)
    assert handled
    assert ("recheck", None) in client.calls, f"无参考应走 without_reference: {client.calls}"
    assert [c[0] for c in client.calls] == ["recheck"], f"不应走跳检: {client.calls}"


# ============================================================
# D. 参考确定 + 模式执行(10)
# ============================================================
def test_checking_filelist_reference_skip_checking():
    """测试: filelist 基础检查确定同组已完成+上传中成员为参考 -> with_reference 段跳检全流程"""
    cfg = make_check_cfg(basic_check="filelist", with_mode="skip-checking", with_start=True)
    mgr = make_mgr(cfg)
    client = CheckingFakeClient()
    mgr.client = client
    client.torrents["HASH123"] = {"state": "stalledUP"}
    t = make_target()
    r = FakeTorrent(hash="R1", name="R1", state="stalledUP")
    inject_group(mgr, "HASH123", "R1")
    mgr._snapshot = [t, r]
    handled = mgr.process_torrent(t, dry_run=False)
    assert handled, f"有参考应处理: {client.calls}"
    assert [c[0] for c in client.calls] == ["export", "delete", "add", "start"], f"跳检调用顺序: {client.calls}"
    add_call = [c for c in client.calls if c[0] == "add"][0]
    assert add_call[1]["is_skip_checking"] is True, f"重加应跳过校验: {add_call}"
    assert add_call[1]["paused"] is True, f"重加应先暂停: {add_call}"
    assert mgr.state.get("exec_history"), "跳检应记录执行历史"


def test_checking_no_reference_full_checking():
    """测试: 无参考 -> without_reference full-checking 异步全流程(提交->pending->重复忽略->完成->start+记录+晋升)"""
    cfg = make_check_cfg(without_mode="full-checking", without_start=True)
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    t = make_target()
    handled = mgr.process_torrent(t, dry_run=False)
    assert handled, "应提交校验"
    assert ("recheck", None) in client.calls, f"应发送校验请求: {client.calls}"

    # 未完成: 任务留在慢速队列
    completed = mgr.task_queue.poll_slow(lambda h: False)
    assert completed == [], f"未完成不应出队: {completed}"
    assert mgr.task_queue.pending_slow() == ["HASH123"], "未完成应留在慢速队列"

    # 重复提交同一种子: 忽略
    client.calls.clear()
    mgr.process_torrent(t, dry_run=False)
    assert ("recheck", None) not in client.calls, f"重复校验应被忽略: {client.calls}"

    # 完成: 自动开始 + 记录执行 + 晋升 verified_references(仅内存)
    completed = mgr.task_queue.poll_slow(lambda h: True)
    assert len(completed) == 1, f"应完成 1 个任务: {completed}"
    assert ("start", None) in client.calls, f"校验完成应自动开始: {client.calls}"
    assert mgr.state.get("exec_history"), "校验完成应记录执行历史"
    assert mgr.verified_references == {"HASH123"}, "校验通过应晋升为参考"
    assert mgr.task_queue.pending_slow() == [], "完成后应出队"


def test_checking_no_reference_skip_checking_warns():
    """测试: 无参考跳检 -> 执行但记录高风险警告(不降级为 full-checking)"""
    cfg = make_check_cfg(with_mode="skip-checking", without_mode="skip-checking", without_start=True)
    mgr = make_mgr(cfg)
    client = CheckingFakeClient()
    mgr.client = client
    client.torrents["HASH123"] = {"state": "stalledUP"}
    t = make_target()
    with patch("auto_qb.rules.actions.logger.warning") as mw:
        handled = mgr.process_torrent(t, dry_run=False)
        assert handled
        assert [c[0] for c in client.calls] == ["export", "delete", "add", "start"], f"{client.calls}"
        assert any("无参考种子跳检" in str(c) for c in mw.call_args_list), f"应有高风险警告: {mw.call_args_list}"


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
    mgr._snapshot = [t, r]
    handled = mgr.process_torrent(t, dry_run=False)
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
    mgr._snapshot = [t, r]
    handled = mgr.process_torrent(t, dry_run=False)
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
    mgr._snapshot = [t, r]
    handled = mgr.process_torrent(t, dry_run=False)
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
    mgr._snapshot = [t, r]
    with patch("subprocess.run") as mrun:
        mrun.return_value = SimpleNamespace(returncode=0, stdout="ok", stderr="")
        handled = mgr.process_torrent(t, dry_run=False)
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
    mgr._snapshot = [t, r]
    with patch("subprocess.run") as mrun:
        mrun.return_value = SimpleNamespace(returncode=1, stdout="", stderr="bad")
        handled = mgr.process_torrent(t, dry_run=False)
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
    mgr.verified_references = {"R1"}  # 历史 full-checking 通过
    t = make_target()
    r = FakeTorrent(hash="R1", name="R1", state="pausedUP")  # 非上传候选, 仅靠 verified
    inject_group(mgr, "HASH123", "R1")
    mgr._snapshot = [t, r]
    handled = mgr.process_torrent(t, dry_run=False)
    assert handled
    assert ("export", "HASH123") in client.calls, f"verified 参考应走 with_reference 段: {client.calls}"


def test_checking_verified_references_not_persisted():
    """测试: verified_references 仅内存, 重启后重新积累(不写 state_file)"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        cfg = make_check_cfg(without_mode="full-checking", without_start=True)
        cfg.state_file = state_file
        mgr = QbManager("", config=cfg)
        mgr.task_queue = TaskQueue(executor_workers=0)
        client = CheckingFakeClient()
        mgr.client = client
        t = make_target()
        mgr.process_torrent(t, dry_run=False)
        mgr.task_queue.poll_slow(lambda h: True)
        assert mgr.verified_references == {"HASH123"}, "完成后应晋升"
        mgr.save_state()

        mgr2 = QbManager("", config=cfg)  # 重新加载同一 state 文件
        assert mgr2.verified_references == set(), "verified 参考不应持久化"


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
    handled = mgr.process_torrent(t, dry_run=False)
    assert handled, "前置检查失败应返回失败结果(动作已执行)"
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
        handled = mgr.process_torrent(t, dry_run=False)
        assert handled, "前置检查失败应返回失败结果(动作已执行)"
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
        handled = mgr.process_torrent(t, dry_run=False)
        backup = mgr.state.get("skip_check_backup", {}).get("HASH123")
        assert backup, f"重加失败应记录备份元数据: {mgr.state}"
        assert os.path.exists(backup["path"]), f"备份文件应存在: {backup}"
        assert ("export", "HASH123") in client.calls, "应先导出"
        assert ("delete", False) in client.calls, "应先删除种子"


def test_checking_skip_dedup_same_day():
    """测试: 同日去重 -> 同一天不重复跳检"""
    cfg = make_check_cfg(with_mode="skip-checking", without_mode="skip-checking", with_start=True)
    mgr = make_mgr(cfg)
    client = CheckingFakeClient()
    mgr.client = client
    client.torrents["HASH123"] = {"state": "stalledUP"}
    t = make_target()
    handled = mgr.process_torrent(t, dry_run=False)
    assert handled
    assert [c[0] for c in client.calls] == ["export", "delete", "add", "start"]

    client.calls.clear()
    handled = mgr.process_torrent(t, dry_run=False)
    assert not handled, "同日不应重复跳检"
    assert ("delete", False) not in client.calls, f"同日不应删除种子: {client.calls}"


def test_checking_dry_run():
    """测试: dry-run -> 不调用任何客户端 API(含校验/跳检)"""
    cfg = make_check_cfg(with_mode="skip-checking", without_mode="full-checking")
    mgr = make_mgr(cfg)
    client = CheckingFakeClient()
    mgr.client = client
    t = make_target()
    handled = mgr.process_torrent(t, dry_run=True)
    assert handled, "dry-run 应正常返回"
    assert client.calls == [], f"dry-run 不应调用客户端: {client.calls}"


def test_checking_full_checking_pending():
    """测试: 校验未完成 -> 任务保留在慢速队列(不丢失)"""
    cfg = make_check_cfg(without_mode="full-checking")
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    t = make_target()
    mgr.process_torrent(t, dry_run=False)
    completed = mgr.task_queue.poll_slow(lambda h: False)
    assert completed == [], f"未完成不应出队: {completed}"
    assert mgr.task_queue.pending_slow() == ["HASH123"], "任务应保留"


def test_checking_full_checking_dup_ignore():
    """测试: 同一种子重复提交校验 -> 忽略(仅一次 recheck)"""
    cfg = make_check_cfg(without_mode="full-checking")
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    t = make_target()
    mgr.process_torrent(t, dry_run=False)
    mgr.process_torrent(t, dry_run=False)  # 重复
    n_recheck = sum(1 for c in client.calls if c[0] == "recheck")
    assert n_recheck == 1, f"recheck 应只发送一次: {client.calls}"


def test_checking_full_checking_auto_start_false():
    """测试: auto_start=false -> 校验完成不自动开始, 仍记录执行 + 晋升参考"""
    cfg = make_check_cfg(without_mode="full-checking", without_start=False)
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    t = make_target()
    mgr.process_torrent(t, dry_run=False)
    mgr.task_queue.poll_slow(lambda h: True)
    assert ("start", None) not in client.calls, f"auto_start=false 不应自动开始: {client.calls}"
    assert mgr.state.get("exec_history"), "仍应记录执行历史"
    assert mgr.verified_references == {"HASH123"}, "仍应晋升参考"


def test_checking_full_checking_send_error():
    """测试: 校验请求发送失败 -> 警告, 不自动开始/不记录/不晋升"""
    cfg = make_check_cfg(without_mode="full-checking", without_start=True)
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    client.recheck_error = RuntimeError("simulated recheck failure")
    t = make_target()
    with patch("auto_qb.rules.actions.logger.warning") as mw:
        handled = mgr.process_torrent(t, dry_run=False)
        assert handled, "提交本身不应失败"
        # 提交时 process 已记录一次(动作 ok); 记录 done 是否额外覆盖
        rec_key = f"{mgr.enabled_rules[0].name}:{t.hash}"
        ts_before = mgr.state["exec_history"][rec_key]["ts"]
        completed = mgr.task_queue.poll_slow(lambda h: True)
        assert len(completed) == 1, f"发送失败的任务应立即完成: {completed}"
        assert any("校验请求发送失败" in str(c) for c in mw.call_args_list), f"应有失败警告: {mw.call_args_list}"
        ts_after = mgr.state["exec_history"][rec_key]["ts"]
        assert ts_before == ts_after, "发送失败不应由完成回调重新记录"
    assert ("start", None) not in client.calls, "发送失败不应自动开始"
    assert mgr.verified_references == set(), "发送失败不应晋升参考"


def test_checking_no_task_queue_direct_recheck():
    """测试: 无任务队列(旧用法) -> full-checking 直接发送 recheck 请求"""
    cfg = make_check_cfg(without_mode="full-checking")
    mgr = make_mgr(cfg)
    mgr.task_queue = None  # 无任务队列
    client = CheckingFakeClient()
    mgr.client = client
    t = make_target()
    handled = mgr.process_torrent(t, dry_run=False)
    assert handled
    assert ("recheck", None) in client.calls, f"无队列应直接发送: {client.calls}"
