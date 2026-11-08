"""test_checking_skip 测试计划: checking 动作详细自测(不连接真实 qB, 用模拟对象)

## 测试计划(每个测试函数一条)
- test_checking_group_downloading_skips: 组内有下载中成员 -> 跳过校验
- test_checking_paused_incomplete_not_skip: 暂停未完成不能作为参考 -> 不跳过
- test_checking_complete_skipped: 已完成做种中(progress=1) -> 跳过, 不校验
- test_checking_paused_complete_skipped: 暂停已完成(pausedUP+progress=1) -> 跳过
- test_checking_active_downloading_skipped: 活跃下载中(downloading+progress=0.5) -> 跳过
- test_checking_filelist_reference_skip_checking: filelist 参考匹配 -> 跳检
- test_checking_no_reference_skip_checking_warns: 无参考但 skip 配置 -> 警告跳过
- test_checking_skip_guard_file_missing: 跳检前置文件检查失败
- test_checking_skip_guard_file_size_mismatch: 跳检前置文件大小不符
- test_checking_skip_guard_add_fail_backup: 重加标签失败回退
- test_checking_skip_readd_unconfirmed_backs_up: 重加已发出但轮询确认不到种子 -> 同样备份 .torrent(否则种子已从客户端移除、data 只存内存随即丢弃)
- test_checking_skip_backup_precedes_delete_and_cleared_on_success: 备份先于删除落盘(崩溃窗口), 重加确认成功后清理备份文件与元数据
- test_checking_skip_delete_unconfirmed_keeps_backup: 删除未生效(种子仍在) -> 放弃跳检但保留删除前的备份并在失败文案指明备份路径(R1#98: 删除异步未定, 备份是唯一恢复凭据宁可留着)
- test_checking_skip_backup_failure_aborts_before_delete: 备份写不进去 -> 不删除(无损失)直接 fail
- test_checking_skip_dedup_same_day: 同日跳检去重
- test_checking_skip_partial_download_forbidden: 部分下载(0<progress<1)禁止跳检
- test_checking_skip_dedup_across_rules: 跨规则同日去重(同种子当日只跳检一次)
- test_checking_skip_gone_fails_at_export_with_clear_message: S3(26-10-21-2323) —— 提交前不直查: 种子已不在时失败在导出步(文案点明), 撤掉快照残留记录, 不删除/重加(修 C2 复活竞态)
- test_checking_full_checking_resume_skips_conditions: 断点续跑跳过条件评估(条件变化不影响续跑)
- test_checking_full_checking_resume_skips_dedup: 断点续跑跳过去重(execute_once=once 不拦截续跑)
- test_checking_group_skip_on_same_data_fail: 组内校验失败推断(决策链 1.6): 文件映射一致 -> B 不再校验
- test_checking_group_wait_external_entry_skip: 组内校验中且无任务驱动 -> skip
- test_checking_skip_day_flushed_immediately: 跳检完成标记即时落盘(崩溃后不重复跳检)
- test_skip_check_success_applies_tag
- test_skip_check_tag_empty_disables
- test_skip_check_tag_failure_doesnt_fail_skip
- test_skip_check_tag_uses_global_config
- test_skip_check_tagged_member_excluded_as_reference
- test_skip_check_tagged_verified_reference_excluded
- test_skip_checking_forwards_origin_task: C22 守阵 —— 跳检委托把 ctx.task 原样交给 ops origin
  (丢失则终态后规则任务永不回队)
"""

import json

import os

import tempfile

import time

import uuid

from datetime import date

from types import SimpleNamespace

from unittest.mock import patch

from auto_qb.config import Config

from auto_qb.rules.actions import RECHECK_FAIL_LIMIT, CheckAction

from auto_qb.rules.actions.full_checking import bump_recheck_fail, recheck_fail_count

from auto_qb.rules.base import VERDICT_EXECUTED, VERDICT_PENDING

from auto_qb.rules.checking_meta import PieceCheckingStates, PollVerdict, is_piece_checking, poll_verdict

from auto_qb.core.taskqueue import FINISHED, PENDING, REQUEUE, TaskQueue

from helpers import drive_skip, FakeClient, FakeConfig, FakeTorrent, make_ctx, make_manager, seed_store

from checking_support import (
    CheckingFakeClient,
    _TMP_STATE_DIR,
    _seg,
    inject_group,
    make_check_cfg,
    make_mgr,
    make_target,
    process_rule,
    run_queue,
)


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
    handled = process_rule(mgr, client, t, dry_run=False)
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
    client.torrents["HASH123"] = t  # 客户端里要有该种子: 跳检的重加确认与轮询仲裁直查都读它(提交前不再复核)
    handled = process_rule(mgr, client, t, dry_run=False)
    assert handled, "暂停未完成不应跳过"
    run_queue(mgr)  # 首轮: 发送 recheck
    assert ("recheck", None) in client.calls, f"无参考应走 full-checking: {client.calls}"


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
    handled = process_rule(mgr, client, t, dry_run=False)
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
    handled = process_rule(mgr, client, t, dry_run=False)
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
    handled = process_rule(mgr, client, t, dry_run=False)
    assert not handled, "活跃下载中种子应跳过"
    assert client.calls == [], f"不应有任何客户端调用: {client.calls}"


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
    handled = process_rule(mgr, client, t, dry_run=False)
    assert handled, f"有参考应处理: {client.calls}"
    assert [c[0] for c in client.calls] == ["export", "delete", "add", "add_tags", "start"], f"跳检调用顺序: {client.calls}"
    add_call = [c for c in client.calls if c[0] == "add"][0]
    assert add_call[1]["is_skip_checking"] is True, f"重加应跳过校验: {add_call}"
    assert mgr.state.get("exec_history"), "跳检应记录执行历史"


def test_checking_skip_dedup_across_rules():
    """测试: 跨规则同日去重 —— 规则A跳检后, 规则B同日对同种子跳检被拒(统计只丢一次)"""
    cfg = make_check_cfg(with_mode="skip-checking", without_mode="skip-checking", without_start=False)
    mgr = make_mgr(cfg)
    client = CheckingFakeClient()
    mgr.client = client
    client.torrents["HASH123"] = {"state": "pausedUP"}
    t = make_target()  # pausedDL: 不自动开始, 重加后仍暂停, 规则B才能走到跨规则去重
    handled = process_rule(mgr, client, t, dry_run=False)
    assert handled and mgr.state["skip_check_day"]["HASH123"], "规则A应完成跳检并记录"

    # 模拟另一条规则B: 换规则名但同种子, 同日再跳检
    rule_b = next(r for r in mgr.host.get("rules").enabled_rules if r.name == "example_rules.check_rule")
    client.calls.clear()
    # 保真现场(26-11-05-0019): 真机跳检成功 ⇒ 种子必为已完成(progress=1)。替身不会自动反映
    #   这一点(跳检流程不改写 t), 故显式置 1 —— 旧代码下链 0 先以「非暂停中未完成」遮蔽,
    #   走不到规则侧 dedup 前插, 本用例必红(旧绕行 t.progress=0.0 是空操作: 替身默认就是 0,
    #   用例从未复现过真机遮蔽链路, 见任务档案 26-11-05-backend-rule-skipcheck-dedup)
    t.progress = 1.0
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
    with patch("auto_qb.core.modules.ops_mod.logger.warning") as mw:
        handled = process_rule(mgr, client, t, dry_run=False)
        assert handled
        assert [c[0] for c in client.calls] == ["export", "delete", "add", "add_tags", "start"], f"{client.calls}"
        assert any("无参考跳检" in str(c) for c in mw.call_args_list), f"应有高风险警告: {mw.call_args_list}"


def test_checking_skip_readd_unconfirmed_backs_up():
    """测试: 重加已发出但轮询确认不到种子 -> 同样备份 .torrent

    原实现只在 `torrents_add` 抛异常时备份: add 成功但 _poll_until 三次确认不到(大种子/磁盘忙
    时 qB 重加可能慢于 0.9s)就直接返回失败 —— 此时种子已从客户端删除、data 字节只存在于内存
    随即丢弃, 用户得回站点重新下载; store 也无该记录, 下轮不会执行 restore_torrent。

    场景构造: FakeClient.torrents_add 总会把种子登记进客户端(正常语义), 故这里在 add 之后
    把它从客户端摘掉, 精确模拟"add 返回成功、但客户端迟迟不出现该种子"。
    """
    import os

    class _NotAppearedClient(CheckingFakeClient):
        def torrents_add(self, **kw):
            ret = super().torrents_add(**kw)
            self.torrents.pop("HASH123", None)  # add 成功但客户端里查不到
            return ret

    # !R2 实时复核(跳检前)读客户端: 初始必须放一个, add 时才由上面的 pop 摘掉

    with tempfile.TemporaryDirectory() as td:  # state_file 必须给真实路径: 留空会让 atomic_write 往 CWD 的父目录写临时文件
        cfg = make_check_cfg(with_mode="skip-checking", without_mode="skip-checking", without_start=True)
        cfg.state_file = os.path.join(td, "state.json")
        mgr = make_mgr(cfg)
        client = _NotAppearedClient()
        mgr.client = client
        client.torrents["HASH123"] = {"state": "pausedUP"}
        t = make_target()
        process_rule(mgr, client, t, dry_run=False)

        assert any(c[0] == "add" for c in client.calls), f"前置: 应已发出重加: {client.calls}"
        # 断言必须在 td 内: 备份文件本身就落在临时目录里, 出了 with 目录已被清理
        meta = mgr.state.get("skip_check_backup", {}).get("HASH123")
        assert meta, f"未确认到种子也必须备份 .torrent: {mgr.state}"
        assert os.path.exists(meta["path"]), f"备份文件应真实落盘: {meta}"
        assert not mgr.state.get("skip_check_day", {}).get("HASH123"), "未成功跳检不应记录跨日去重"


def test_checking_skip_backup_precedes_delete_and_cleared_on_success():
    """测试: 备份**先于**删除落盘(崩溃安全), 重加确认成功后清理备份文件与元数据

    跳检的删除是链上第一个不可逆步骤: 备份若只挂在重加的失败路径上, 那么「删除已生效 →
    重加未被 qB 接受」这个缝隙(含删除确认轮询的约 5s)内崩溃/强杀, 种子从客户端消失、
    .torrent 只在内存、state 无在途标记 —— 重启后无任何恢复凭据(issue 26-09-21-1347)。
    故顺序必须是 备份 → 删除 → 重加 → 清理。

    断言"先于删除"的办法: 在客户端的 torrents_delete 里快照一次备份文件的存在性 —— 这正是
    崩溃窗口的起点, 只查最终结果(跳检成功)无法区分备份是之前写的还是之后补的。
    """
    cfg = make_check_cfg(with_mode="skip-checking", without_mode="skip-checking", without_start=False)
    mgr = make_mgr(cfg)
    client = CheckingFakeClient()
    mgr.client = client
    client.torrents["HASH123"] = {"state": "pausedUP"}
    t = make_target()

    seen = {}
    orig_delete = client.torrents_delete

    def spy_delete(torrent_hashes=None, delete_files=False):
        meta = mgr.state.get("skip_check_backup", {}).get("HASH123")
        seen["meta"] = meta
        seen["file_at_delete"] = bool(meta) and os.path.exists(meta["path"])
        return orig_delete(torrent_hashes=torrent_hashes, delete_files=delete_files)

    client.torrents_delete = spy_delete
    handled = process_rule(mgr, client, t, dry_run=False)
    assert handled, "前置: 跳检应完成"
    assert seen.get("file_at_delete"), f"备份必须先于删除落盘(否则缝隙内崩溃无凭据): {seen}"
    assert not mgr.state.get("skip_check_backup"), f"重加成功后应清理备份元数据: {mgr.state}"
    assert not os.path.exists(seen["meta"]["path"]), "重加成功后应删除备份文件(不留孤儿)"


def test_checking_skip_delete_unconfirmed_keeps_backup():
    """测试(R1#98): 删除未生效(种子仍在客户端) -> 放弃跳检但**保留**删除前的备份并在失败
    文案里指明备份路径

    旧口径(「种子没删掉时那份备份已无意义, 留着只剩孤儿文件 + 误导性元数据」)被 R1#98
    推翻: 删除是异步的且重试路径刚重发过删除 —— 此刻「种子还在」不代表删除不会在备份清理
    之后才落地, 那会种子被删而 .torrent 恢复凭据已丢。备份保留(唯一恢复凭据宁可留着),
    交对账/用户按 skip_check_backup 账本收尾。
    """
    cfg = make_check_cfg(with_mode="skip-checking", without_mode="skip-checking", without_start=False)
    mgr = make_mgr(cfg)
    client = CheckingFakeClient()
    mgr.client = client
    client.torrents["HASH123"] = {"state": "pausedUP"}  # 删除后仍在 -> 确认消失必然失败
    t = make_target()

    def noop_delete(torrent_hashes=None, delete_files=False):
        client.calls.append(("delete", delete_files))  # 只记调用, 不真删

    client.torrents_delete = noop_delete
    handled = process_rule(mgr, client, t, dry_run=False)
    assert handled, "放弃跳检以 fail 返回(fail 视为已处理)"
    assert not any(c[0] == "add" for c in client.calls), f"未确认消失前不得重加: {client.calls}"
    backup_file = os.path.join(os.path.dirname(mgr.state_file), "skip-check-backup", "HASH123.torrent")
    meta = mgr.state.get("skip_check_backup", {}).get("HASH123")
    assert meta and meta["path"] == backup_file and os.path.exists(backup_file), \
        f"GONE 相位失败(删除仍会异步落地)备份必须保留(唯一恢复凭据): {meta}"
    res = mgr.ctx.ops.skip_result("HASH123")
    assert res is not None and res.is_failed, f"GONE 相位失败应有终态结果: {res}"
    assert "已备份" in res.message and backup_file in res.message, f"失败文案必须指明备份路径: {res.message}"


def test_checking_skip_backup_failure_aborts_before_delete():
    """测试: 备份写不进去 -> 不删除(无损失), 直接 fail —— 备份是删除的前置条件"""
    from auto_qb.core.modules.ops_mod import OpsModule

    cfg = make_check_cfg(with_mode="skip-checking", without_mode="skip-checking", without_start=False)
    mgr = make_mgr(cfg)
    client = CheckingFakeClient()
    mgr.client = client
    client.torrents["HASH123"] = {"state": "pausedUP"}
    t = make_target()
    with patch.object(OpsModule, "_backup_torrent", side_effect=OSError("disk full")):
        handled = process_rule(mgr, client, t, dry_run=False)
    assert handled
    assert [c[0] for c in client.calls] == ["export"], f"备份失败不得删除/重加: {client.calls}"
    assert not mgr.state.get("skip_check_backup"), "备份失败不应留下元数据"


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
    handled = process_rule(mgr, client, t, dry_run=False)
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
        handled = process_rule(mgr, client, t, dry_run=False)
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
    handled = process_rule(mgr, client, t, dry_run=False)
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
    handled = process_rule(mgr, client, t, dry_run=False)
    assert handled
    assert [c[0] for c in client.calls] == ["export", "delete", "add", "add_tags", "start"]

    client.calls.clear()
    handled = process_rule(mgr, client, t, dry_run=False)
    assert not handled, "同日不应重复跳检"
    assert ("delete", False) not in client.calls, f"同日不应删除种子: {client.calls}"


# ============================================================
# C4. 跳检打标与参考排除(skip_checking_tag)
# ============================================================
def test_skip_check_tag_uses_global_config():
    """测试: 跳检标签名运行时读全局 config.skip_checking_tag(自定义全局名生效)"""
    cfg = make_check_cfg(basic_check="filelist", with_mode="skip-checking", with_start=True)
    cfg.skip_checking_tag = "zGlobalTag"  # 全局自定义标签名
    mgr = make_mgr(cfg)
    client = CheckingFakeClient()
    mgr.client = client
    client.torrents["HASH123"] = {"state": "stalledUP"}
    t = make_target()
    r = FakeTorrent(hash="R1", name="R1", state="stalledUP")
    inject_group(mgr, "HASH123", "R1")
    seed_store(mgr, [t, r])
    handled = process_rule(mgr, client, t, dry_run=False)
    assert handled
    assert ("add_tags", ["zGlobalTag"]) in client.calls, f"应使用全局 config 标签名: {client.calls}"


def test_skip_check_success_applies_tag():
    """测试: 跳检成功后给种子打 zSkipChecked 标签(Facade 同步 store, 记录 tags_set 含该标签)"""
    cfg = make_check_cfg(basic_check="filelist", with_mode="skip-checking", with_start=True)
    mgr = make_mgr(cfg)
    client = CheckingFakeClient()
    mgr.client = client
    client.torrents["HASH123"] = {"state": "stalledUP"}
    t = make_target()
    r = FakeTorrent(hash="R1", name="R1", state="stalledUP")
    inject_group(mgr, "HASH123", "R1")
    seed_store(mgr, [t, r])
    handled = process_rule(mgr, client, t, dry_run=False)
    assert handled
    assert ("add_tags", ["zSkipChecked"]) in client.calls, f"跳检成功应打默认标签: {client.calls}"
    assert "zSkipChecked" in mgr.store.get("HASH123").tags_set, "Facade 应把标签同步到 store 记录"


def test_skip_check_tag_empty_disables():
    """测试: 全局标签名为空串(代码层直构) -> 跳检成功也不打标、不排除"""
    cfg = make_check_cfg(basic_check="filelist", with_mode="skip-checking", with_start=True)
    cfg.skip_checking_tag = ""  # 空标签名: 按值判空, 不打标(生产 YAML 无法配置空值, 仅代码层可达)
    mgr = make_mgr(cfg)
    client = CheckingFakeClient()
    mgr.client = client
    client.torrents["HASH123"] = {"state": "stalledUP"}
    t = make_target()
    r = FakeTorrent(hash="R1", name="R1", state="stalledUP")
    inject_group(mgr, "HASH123", "R1")
    seed_store(mgr, [t, r])
    handled = process_rule(mgr, client, t, dry_run=False)
    assert handled
    assert not any(c[0] == "add_tags" for c in client.calls), f"禁用打标时不应调用 add_tags: {client.calls}"


def test_skip_check_tag_failure_doesnt_fail_skip():
    """测试: 打标签异常不影响跳检成功结论(仅记 warning, 跳检本身已完成)"""
    cfg = make_check_cfg(basic_check="filelist", with_mode="skip-checking", with_start=False)
    mgr = make_mgr(cfg)
    client = CheckingFakeClient()
    mgr.client = client

    def _raise(*a, **k):
        raise RuntimeError("simulated add_tags failure")

    client.torrents_add_tags = _raise  # 打标始终失败
    client.torrents["HASH123"] = {"state": "stalledUP"}
    t = make_target()
    r = FakeTorrent(hash="R1", name="R1", state="stalledUP")
    inject_group(mgr, "HASH123", "R1")
    seed_store(mgr, [t, r])
    handled = process_rule(mgr, client, t, dry_run=False)
    assert handled, "打标失败不应使跳检失败"
    names = [c[0] for c in client.calls]
    assert "export" in names and "delete" in names and "add" in names, f"跳检四阶段应已完成: {client.calls}"


def test_skip_check_tagged_member_excluded_as_reference():
    """测试: 组内带跳检标签的已完成成员不作参考(未经哈希校验) -> 改走 without_reference 段"""
    cfg = make_check_cfg(
        basic_check="filelist", with_mode="skip-checking", without_mode="full-checking", without_start=False
    )
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    t = make_target()
    client.torrents["HASH123"] = t  # 客户端里要有该种子: 跳检的重加确认与轮询仲裁直查都读它(提交前不再复核)
    r = FakeTorrent(hash="R1", name="R1", state="stalledUP", tags="zSkipChecked")  # 已完成但带跳检标签
    inject_group(mgr, "HASH123", "R1")
    seed_store(mgr, [t, r])
    handled = process_rule(mgr, client, t, dry_run=False)
    assert handled, "无可用参考应走 without_reference 段"
    assert not any(c[0] == "export" for c in client.calls), f"带标成员不可作参考, 不应跳检: {client.calls}"
    assert ("recheck", None) in client.calls, f"应走 without_reference full-checking: {client.calls}"


def test_skip_check_tagged_verified_reference_excluded():
    """测试: 带跳检标签的成员即便在内存 verified_references 中也被排除(并集出口统一过滤)"""
    cfg = make_check_cfg(
        basic_check="filelist", with_mode="skip-checking", without_mode="full-checking", without_start=False
    )
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    t = make_target()
    client.torrents["HASH123"] = t  # 客户端里要有该种子: 跳检的重加确认与轮询仲裁直查都读它(提交前不再复核)
    r = FakeTorrent(hash="R1", name="R1", state="stalledUP", tags="zSkipChecked")
    inject_group(mgr, "HASH123", "R1")
    seed_store(mgr, [t, r])
    mgr.store.verified_references.add("R1")  # 即便历史 full-checking 晋升过, 带标仍排除
    handled = process_rule(mgr, client, t, dry_run=False)
    assert handled
    assert not any(c[0] == "export" for c in client.calls), f"带标 verified 参考应排除, 不应跳检: {client.calls}"
    assert ("recheck", None) in client.calls, f"应走 without_reference full-checking: {client.calls}"


def test_checking_full_checking_resume_skips_conditions():
    """续跑跳过条件评估: 首次条件匹配 -> pending; 校验完成后条件不再匹配, 续跑仍执行后续动作 """
    cfg = make_check_cfg(without_mode="full-checking", without_start=False, extra_actions=[{"start": True}])
    mgr = make_mgr(cfg, with_tq=True)
    client = CheckingFakeClient()
    mgr.client = client
    t = make_target()
    seed_store(mgr, [t])
    client.torrents["HASH123"] = t  # 客户端里要有该种子: 跳检的重加确认与轮询仲裁直查都读它(提交前不再复核)
    t0 = time.time()
    rule = next(r for r in mgr.host.get("rules").enabled_rules if r.name == "example_rules.check_rule")
    origin = mgr.host.get("rules")._create_rule_task(rule, "HASH123")
    origin.interval = 60.0
    mgr.task_queue.add_task(origin, t0)
    run_queue(mgr, t0)
    assert origin.resume_index == 1 and origin not in mgr.task_queue._fast
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
    client.torrents["HASH123"] = t  # 客户端里要有该种子: 跳检的重加确认与轮询仲裁直查都读它(提交前不再复核)
    t0 = time.time()
    rule = next(r for r in mgr.host.get("rules").enabled_rules if r.name == "example_rules.check_rule")
    origin = mgr.host.get("rules")._create_rule_task(rule, "HASH123")
    origin.interval = 60.0
    mgr.task_queue.add_task(origin, t0)
    run_queue(mgr, t0)
    assert origin.resume_index == 1 and origin not in mgr.task_queue._fast, "首次执行 dedup 通过 -> pending"
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
    rule = next(r for r in mgr.host.get("rules").enabled_rules if r.name == "example_rules.check_rule")
    tb = mgr.host.get("rules")._create_rule_task(rule, "HB")
    mgr.task_queue.add_task(tb, time.time())
    run_queue(mgr)
    assert client.calls.count(("recheck", None)) == 0, f"同数据失败推断: B 不应提交 recheck: {client.calls}"
    assert tb.state == PENDING and tb.resume_index is None, "B 应正常完成(周期重入队)"


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
    handled = process_rule(mgr, client, b, dry_run=False)
    assert not handled, "组内有校验进行时应跳过"
    assert ("recheck", None) not in client.calls, "外部入口不等待也不提交"


def test_checking_skip_day_flushed_immediately():
    """跳检完成标记即时落盘: 流程走完后磁盘上的 state.json 已含 skip_check_day

    skip_check_day 是同日跳检去重的唯一凭据 —— 只靠退出/周期落盘的话, 跳检后崩溃会重复
    跳检(PT 本地统计再丢一次)。注意 _clear_backup 在备份元数据为空时提前 return 不落盘,
    这里钉住的是 _skip_readd 里显式的那次 save_state(issue 26-09-21-1347)。
    """
    cfg = make_check_cfg(with_mode="skip-checking", without_mode="skip-checking", without_start=False)
    mgr = make_mgr(cfg)
    client = CheckingFakeClient()
    mgr.client = client
    client.torrents["HASH123"] = {"state": "pausedUP"}
    t = make_target()
    handled = process_rule(mgr, client, t, dry_run=False)
    assert handled and mgr.state["skip_check_day"]["HASH123"], "前置: 跳检应完成并记录"
    with open(mgr.state_file, "r", encoding="utf-8") as f:
        on_disk = json.load(f)
    assert on_disk.get("skip_check_day", {}).get("HASH123"), "跳检完成标记必须已写上盘(不等退出/周期)"


# ============================================================
# C5. R2 跳检实时复核(plan 26-09-30-0109): 闸门后、动手前重拉实时状态
# ============================================================
def test_checking_skip_gone_fails_at_export_with_clear_message():
    """测试(S3): 提交前不直查 —— 种子已不在时失败在导出步, 文案点明, 且撤掉快照里的残留记录

    修 C2 的机制换了但结论不变: 跳检任务按上一轮快照创建, 而种子可能已被删除。今天由
    「导出 .torrent」这一必经步天然发现(qB 对不存在的 hash 回 404), 失败路径据此撤残留记录
    —— 不会走到删除/重加, 也就不会把用户刚删的种子复活; 备份尚未写入, 无孤儿。
    """
    cfg = make_check_cfg(with_mode="skip-checking", without_mode="skip-checking", without_start=True)
    mgr = make_mgr(cfg)
    client = CheckingFakeClient()
    mgr.client = client
    t = make_target(progress=0.0)  # 暂停未完成: 闸门 0 / 部分下载闸门都通过
    seed_store(mgr, [t])  # 快照仍在(陈旧)
    # client.torrents 不灌该种子 = 客户端里已被删除; 替身按 qB 语义对未知 hash 抛 404
    orig_export = client.torrents_export

    def export_or_404(torrent_hashes=None, torrent_hash=None, **kw):
        h = torrent_hash if torrent_hash is not None else torrent_hashes
        if h not in client.torrents:
            raise RuntimeError("404 Not Found")
        return orig_export(torrent_hashes=torrent_hashes, torrent_hash=torrent_hash, **kw)

    client.torrents_export = export_or_404
    handled = process_rule(mgr, client, t, dry_run=False)
    assert handled, "导出失败按 fail 返回(fail 视为已处理)"
    assert not any(c[0] in ("delete", "add") for c in client.calls), f"不得删除/重加: {client.calls}"
    assert mgr.store.get("HASH123") is None, "失败路径应撤掉快照里的残留记录"
    assert not mgr.state.get("skip_check_day", {}).get("HASH123"), "未跳检不得记录同日去重"
    assert not mgr.state.get("skip_check_backup"), "不得留下孤儿备份元数据"


def test_skip_checking_forwards_origin_task():
    """C22 守阵: 跳检委托必须把 ctx.task 原样交给 ops 的 origin

    origin 丢失(置 None / 省略 / 取错属性名)后, 跳检终态结算找不到触发任务 ->
    规则任务永不回队, 后续动作整段丢失。
    """
    cfg = make_check_cfg()
    mgr = make_mgr(cfg)
    client = CheckingFakeClient()
    mgr.client = client
    tor = make_target()
    ctx = make_ctx(mgr, tor, client)
    origin = SimpleNamespace(kind="rule-task")
    ctx.task = origin
    seen = {}

    def fake_skip_submit(hash, **kw):
        seen.update(hash=hash, **kw)
        return "SENTINEL"

    mgr.ctx.ops.skip_submit = fake_skip_submit
    try:
        action = CheckAction({"basic_check": "filelist", "with_reference": _seg("skip-checking")})
        out = action._execute_skip_checking(ctx, {"mode": "skip-checking", "auto_start": True}, True)
    finally:
        del mgr.ctx.ops.skip_submit
    assert out == "SENTINEL"
    assert seen["origin"] is origin, f"origin 必须是 ctx.task 本身: {seen}"
    assert seen["hash"] == "HASH123" and seen["source"] == "rule" and seen["has_reference"] is True
