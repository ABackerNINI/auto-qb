"""test_rule_engine 测试计划: mixins/rule_engine 规则加载/状态/引用/种子级任务

架构说明(任务队列驱动): process_torrent/_tracker_rule_refs 兼容入口已删除,
规则绑定由 _rules_for_torrent(tor) 承担(匹配 tracker 的 rules 引用解析), 执行
经种子级规则任务(_create_rule_task + _handle_rule + 队列移除)驱动。

## 测试计划(每个测试函数一条)
- test_load_rules_from_config: 从配置加载规则
- test_load_state_missing_or_broken: 状态文件缺失或损坏(且无备份) -> 空状态
- test_load_state_valid: 有效状态加载
- test_load_state_corrupt_falls_back_to_bak: 主文件损坏 -> 用 .bak 恢复并自愈写回主文件(备份不被损坏内容盖掉)
- test_load_state_corrupt_without_backup_warns: 主文件损坏且备份不可用 -> 空状态 + 两条 WARNING(损坏/备份不可用)留痕
- test_load_state_missing_file_is_silent: 首启(文件不存在)不告警 —— 与"损坏"区分
- test_load_state_recovered_writeback_failure_is_nonfatal: 自愈写回失败(磁盘满)仍返回备份恢复出的状态, 只告警不抛
- test_cleanup_orphan_tmp_removes_only_state_leftovers: 启动清理只删 `<state_file>.<随机>.tmp`; .bak / 别人的 .tmp / 空随机段不碰
- test_cleanup_orphan_tmp_missing_dir_is_nonfatal: 状态目录不可列 -> 只告警不抛
- test_cleanup_orphan_tmp_delete_failure_is_nonfatal: 单个文件删不掉(被占用) -> 只告警并继续清其余, 不抛
- test_cleanup_orphan_tmp_is_wired_after_lock: 接线守阵: 清理必须挂在 `self._lock.acquire()` 之后(未持锁时别的实例可能正在写)
- test_save_state_error_swallowed: 保存状态错误被吞掉
- test_record_and_get_exec_record: 执行记录写入与读取
- test_begin_round_and_upload_delta: 本轮开始与上传增量
- test_resolve_refs_exact_and_prefix: 引用精确与前缀解析
- test_tracker_rule_refs: tracker rules 引用 -> _rules_for_torrent 精确绑定单规则
- test_rule_task_executes_only_refs: 规则任务只执行被引用的规则(不再全量执行)
- test_handle_rule_missing_torrent: 种子不存在 -> 返回 False 任务消亡(清理由 run_due 自然承担)
- test_handle_rule_process_ok: _handle_rule 正常执行动作
- test_handle_rule_process_error: 规则处理异常被捕获 -> True
- test_load_rules_skips_non_dict_group: 非 dict 规则组 -> 跳过
- test_rules_for_torrent_uninitialized_conf_raises: 上游未走 refresh (tracker_conf=None) 早暴露 AttributeError (不静默兜底)
- test_rule_task_no_enabled_rules: 无启用规则 -> 无绑定
- test_rules_for_torrent_all_refs: 引用整个规则集 -> 绑定全部启用规则
- test_rules_for_torrent_unresolved_refs: 引用规则不存在 -> 无绑定
- test_rules_for_torrent_ignores_non_ref: tracker rules 非 @ 项(旧 ignore 标志)被忽略
- test_maybe_flush_state_periodic: 周期落盘到期触发/间隔内不重复(状态丢失窗口压到 interval 内)
- test_maybe_flush_state_disabled_zero: state_save_interval=0(关闭)恒不落盘 —— 旧行为逃生口
- test_dirty_exit_keeps_exec_history_after_periodic_flush: 验收阵: 模拟脏退出(不走 finally), 周期落盘已把 exec_history 写上盘
- test_dirty_exit_interval_zero_loses_runtime_state: 对照: 关闭周期落盘时脏退出丢运行期状态(0 = 旧行为)
"""
import json
import os
import tempfile
import time
from unittest import mock

import pytest

from auto_qb.infra import utils
from auto_qb.mixins import rule_engine
from auto_qb.rules.base import Rule
from auto_qb.taskqueue import FINISHED, REQUEUE, Task
from helpers import FakeClient, FakeTorrent, make_manager, seed_store


def test_load_rules_from_config():
    """从 config rules_config 加载规则, 规则名带规则集前缀, enabled 过滤"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        names = {r.name for r in mgr.rules}
        assert names == {
            "example_rules.add_site_tag",
            "example_rules.hr_done",
            "example_rules.stop_low_ratio",
        }
        assert len(mgr.enabled_rules) == 3


def test_load_state_missing_or_broken():
    """状态文件缺失/损坏 JSON 均返回空 dict"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "missing.json")
        mgr = make_manager(state_file)
        assert mgr._load_state() == {}
        # 损坏 JSON
        with open(state_file, "w", encoding="utf-8") as f:
            f.write("{not json")
        assert mgr._load_state() == {}
        # 非 dict JSON 也返回 {}
        with open(state_file, "w", encoding="utf-8") as f:
            f.write("[1,2,3]")
        assert mgr._load_state() == {}


def test_load_state_valid():
    """合法状态文件返回 dict"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump({"exec_history": {"k": 1}}, f)
        mgr = make_manager(state_file)
        assert mgr._load_state() == {"exec_history": {"k": 1}}


def test_load_state_corrupt_falls_back_to_bak():
    """主文件损坏 -> 用 .bak 恢复, 并把恢复出的内容写回主文件(自愈)

    写回是关键: 不写回的话, 下一次 save_state 的 keep_backup 会把损坏的主文件复制成新的
    .bak —— 唯一一份好备份被盖掉, 这次恢复等于白做。
    """
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        bak_file = state_file + utils.BACKUP_SUFFIX
        mgr = make_manager(state_file)
        first = {"exec_history": {"r:h": {"ts": 1.0}}}
        mgr.state = dict(first)
        mgr.save_state()  # 第一版: state.json=first, 无 .bak(无旧文件不凭空造)
        mgr.state = {"exec_history": {"r:h": {"ts": 2.0}}, "skip_check_day": "2026-09-21"}
        mgr.save_state()  # 第二版: .bak=first, state.json=second
        assert json.loads(open(bak_file, encoding="utf-8").read()) == first

        with open(state_file, "w", encoding="utf-8") as f:
            f.write("{not json")  # 模拟磁盘/外部改写造成的损坏
        with mock.patch.object(rule_engine.logger, "warning") as warn, \
             mock.patch.object(rule_engine.logger, "info") as info:
            got = mgr._load_state()

        assert got == first, "损坏时应回退到 .bak 的内容, 而不是静默清空"
        assert any("损坏" in c[0][0] for c in warn.call_args_list), "损坏必须留 WARNING(此前是完全静默)"
        assert any("备份" in c[0][0] for c in info.call_args_list), "用了备份要记 INFO 便于事后核对"
        # 自愈: 主文件已修好, 且 .bak 仍是那份好备份(没被损坏内容盖掉)
        assert json.loads(open(state_file, encoding="utf-8").read()) == first
        assert json.loads(open(bak_file, encoding="utf-8").read()) == first


def test_load_state_corrupt_without_backup_warns():
    """主文件损坏且备份不可用 -> 仍是空状态(不阻塞启动), 但两条 WARNING 留痕"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = make_manager(state_file)
        with open(state_file, "w", encoding="utf-8") as f:
            f.write("{not json")
        with mock.patch.object(rule_engine.logger, "warning") as warn:
            assert mgr._load_state() == {}
        msgs = [c[0][0] for c in warn.call_args_list]
        assert any("损坏" in m for m in msgs), "损坏必须有告警(修复前静默清空, 无任何线索)"
        assert any("备份" in m and "不可用" in m for m in msgs), "备份也不可用时必须说清后果"


def test_load_state_missing_file_is_silent():
    """首启(文件不存在)属正常, 不得告警 —— 与"损坏"必须分开处置"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "nope.json"))
        with mock.patch.object(rule_engine.logger, "warning") as warn:
            assert mgr._load_state() == {}
        assert warn.call_count == 0, "首次启动不该报 WARNING"


def test_load_state_recovered_writeback_failure_is_nonfatal():
    """自愈写回失败(磁盘满/只读)不得影响本次启动 —— 内存里已是备份恢复出的状态, 只告警

    这条专门钉 `_write_back_recovered` 的异常分支: 它一旦把异常放出去, "有备份可恢复"的场景
    反而比"没备份"更糟(启动直接崩), 与本次修复的意图正好相反。
    """
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = make_manager(state_file)
        mgr.state = {"exec_history": {"r:h": {"ts": 1.0}}}
        mgr.save_state()
        mgr.state = {"exec_history": {"r:h": {"ts": 2.0}}}
        mgr.save_state()
        with open(state_file, "w", encoding="utf-8") as f:
            f.write("{not json")
        with mock.patch.object(rule_engine.utils, "atomic_write", side_effect=OSError("disk full")), \
             mock.patch.object(rule_engine.logger, "warning") as warn:
            got = mgr._load_state()
        assert got == {"exec_history": {"r:h": {"ts": 1.0}}}, "写回失败不能把已恢复出的状态也搭进去"
        assert any("写回" in c[0][0] for c in warn.call_args_list), "写回失败要留痕"


def test_cleanup_orphan_tmp_removes_only_state_leftovers():
    """启动清理只认 `<state_file>.<随机>.tmp`; `.bak` / 别人的 `.tmp` / 空随机段一律不碰

    `.bak` 那条是关键反例 —— 它是恢复凭据(见 test_load_state_corrupt_falls_back_to_bak),
    清理一旦放宽成"同目录所有 .tmp/-like 文件", 就会把唯一的退路删掉。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        orphans = [os.path.join(td, "state.json.ab12cd34.tmp"), os.path.join(td, "state.json.zz99.tmp")]
        keeps = [
            os.path.join(td, "state.json.bak"),  # 恢复凭据
            os.path.join(td, "web.token.tmp"),  # 别人的临时文件
            os.path.join(td, "state.json..tmp"),  # 空随机段: 不是 mkstemp 的产物
        ]
        for p in orphans + keeps:
            with open(p, "w", encoding="utf-8") as f:
                f.write("x")
        mgr._cleanup_orphan_tmp()
        for p in orphans:
            assert not os.path.exists(p), f"孤儿临时文件应被清理: {p}"
        for p in keeps:
            assert os.path.exists(p), f"不该被清理: {p}"
        # 幂等: 再跑一次(已无孤儿)不得误伤任何保留项
        mgr._cleanup_orphan_tmp()
        for p in keeps:
            assert os.path.exists(p), f"二次清理后不该消失: {p}"


def test_cleanup_orphan_tmp_missing_dir_is_nonfatal():
    """状态目录列不出来 -> 只告警不抛(启动清场不该成为新的启动失败点)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        # 目录"列不出来"用打桩模拟: 真造一个不可列目录跨平台不可靠(Windows 上 chmod 无效)
        with mock.patch.object(rule_engine.os, "listdir", side_effect=OSError("denied")), \
             mock.patch.object(rule_engine.logger, "warning") as warn:
            mgr._cleanup_orphan_tmp()  # 不应抛
        assert warn.call_count == 1


def test_cleanup_orphan_tmp_delete_failure_is_nonfatal():
    """单个文件删不掉(被占用) -> 只告警并**继续清其余**, 不抛

    钉的是循环内 `os.remove` 的异常分支: 它若向外抛, 一个被占用的文件就能让启动清场整段失效
    (顺带把后面的删除也一起带走)。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        locked = os.path.join(td, "state.json.aaaa.tmp")
        other = os.path.join(td, "state.json.bbbb.tmp")
        for p in (locked, other):
            with open(p, "w", encoding="utf-8") as f:
                f.write("x")
        real_remove = os.remove

        def flaky(path):
            if path == locked:
                raise OSError("locked")
            real_remove(path)

        with mock.patch.object(rule_engine.os, "remove", side_effect=flaky), \
             mock.patch.object(rule_engine.logger, "warning") as warn:
            mgr._cleanup_orphan_tmp()  # 不应抛
        assert os.path.exists(locked)
        assert not os.path.exists(other), "一个删不掉不该挡住其余"
        assert any("删除孤儿临时文件失败" in c[0][0] for c in warn.call_args_list)


def test_cleanup_orphan_tmp_is_wired_after_lock():
    """接线守阵: 清理必须挂在 `self._lock.acquire()` 之后, 且在 `no_lock` 分支内

    **持锁才清**是这个方法的安全前提: 没拿到锁说明有别的实例在跑, 它的临时文件正在使用中,
    删掉等于破坏别人的写盘(而且 atomic_write 的 os.replace 会失败 ⇒ 状态丢一次更新)。
    只读模式(`--export-yaml` 等 no_lock=True)也不该有这次磁盘副作用。
    """
    import inspect

    from auto_qb.qbmanager import QbManager

    src = inspect.getsource(QbManager.__init__)
    i_lock = src.find("self._lock.acquire()")
    i_clean = src.find("_cleanup_orphan_tmp")
    assert i_lock >= 0 and i_clean > i_lock, "清理必须在 acquire() 之后"
    assert "if not no_lock" in src[:i_clean], "清理必须只在持锁(非 no_lock)分支内"


def test_save_state_error_swallowed():
    """保存失败仅告警不抛异常"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.state = {"a": 1}
        with mock.patch("builtins.open", side_effect=OSError("disk full")):
            mgr.save_state()  # 不应抛异常


def test_maybe_flush_state_periodic():
    """周期落盘: 到期触发一次并顺延到下个周期; 间隔内不重复(丢失窗口 = interval + 1 tick)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.config.state_save_interval = 120.0
        mgr._next_state_flush_at = 1000.0
        with mock.patch.object(mgr, "save_state") as m_save:
            mgr._maybe_flush_state(999.0)
            assert m_save.call_count == 0, "未到期不落盘"
            mgr._maybe_flush_state(1000.0)
            assert m_save.call_count == 1, "到期落盘"
            mgr._maybe_flush_state(1119.0)
            assert m_save.call_count == 1, "间隔内不重复"
            mgr._maybe_flush_state(1120.0)
            assert m_save.call_count == 2, "新周期到期再落盘"


def test_maybe_flush_state_disabled_zero():
    """state_save_interval=0(关闭)恒不落盘 —— 旧行为(仅优雅退出落盘)的逃生口不被误改"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.config.state_save_interval = 0.0
        mgr._next_state_flush_at = 0.0
        with mock.patch.object(mgr, "save_state") as m_save:
            mgr._maybe_flush_state(10**12)
            assert m_save.call_count == 0, "关闭时即使远超任何到期点也不落盘"


def test_dirty_exit_keeps_exec_history_after_periodic_flush():
    """验收阵(issue 26-09-21-1347): 模拟脏退出 —— 记录执行历史 → 周期落盘触发 → 实例被弃

    (不走 finally, 等价 taskkill /F) → 新实例重启加载, exec_history 必须已在盘上。
    """
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "state.json")
        mgr = make_manager(path)
        mgr.config.state_save_interval = 30.0
        mgr._next_state_flush_at = 0.0  # 立即到期
        mgr.record_execution("example_rules.add_site_tag", "HASH1")
        mgr._maybe_flush_state(time.time())  # 真实写盘(非 mock)
        mgr2 = make_manager(path)  # 新实例 = 重启; 旧实例的 finally 从未执行
        assert mgr2.state["exec_history"]["example_rules.add_site_tag:HASH1"], "周期落盘后脏退出不得丢执行历史"


def test_dirty_exit_interval_zero_loses_runtime_state():
    """对照: interval=0(关闭周期落盘)时同样的脏退出丢运行期状态 —— 钉住 0 的语义 = 旧行为"""
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "state.json")
        mgr = make_manager(path)
        mgr.config.state_save_interval = 0.0
        mgr._next_state_flush_at = 0.0
        mgr.record_execution("example_rules.add_site_tag", "HASH1")
        mgr._maybe_flush_state(time.time())  # 关闭: no-op
        mgr2 = make_manager(path)
        assert "exec_history" not in mgr2.state, "关闭周期落盘时运行期状态不上盘(旧行为)"


def test_record_and_get_exec_record():
    """记录/查询执行历史: key = '规则名:hash'"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.record_execution("example_rules.add_site_tag", "HASH123")
        rec = mgr.get_exec_record("example_rules.add_site_tag", "HASH123")
        assert rec is not None and "ts" in rec and "date" in rec and "hour" in rec
        assert mgr.get_exec_record("other.rule", "HASH123") is None


def test_begin_round_and_upload_delta():
    """周期快照: 首次建立基线, 同日幂等, 增量计算下限 0"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        tor = FakeTorrent(hash="H1", uploaded=100)
        mgr.begin_round([tor])
        snaps = mgr.state["upload_snapshots"]
        assert snaps["daily"]["baseline"]["H1"] == 100
        assert snaps["weekly"]["baseline"]["H1"] == 100
        assert snaps["monthly"]["baseline"]["H1"] == 100
        # 同日再次 begin_round: 基线不变
        tor.uploaded = 200
        mgr.begin_round([tor])
        assert snaps["daily"]["baseline"]["H1"] == 100
        # 增量
        assert mgr.upload_delta(tor, "daily") == 100
        # 客户端重启归零: 下限 0
        tor.uploaded = 10
        assert mgr.upload_delta(tor, "daily") == 0
        # 未在基线中的种子: 增量 = 当前上传量(基线按 0 计)
        assert mgr.upload_delta(FakeTorrent(hash="NEW", uploaded=999), "daily") == 999


def test_resolve_refs_exact_and_prefix():
    """规则引用解析: 精确 '集合.规则' / 前缀 '集合' / 去重"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        exact = mgr._resolve_refs(["example_rules.add_site_tag"])
        assert [r.name for r in exact] == ["example_rules.add_site_tag"]
        prefix = mgr._resolve_refs(["example_rules"])
        assert len(prefix) == 3
        # 前缀+精确去重
        both = mgr._resolve_refs(["example_rules", "example_rules.add_site_tag"])
        assert len(both) == 3
        # 未知引用 -> 空
        assert mgr._resolve_refs(["nope"]) == []


def test_tracker_rule_refs():
    """tracker rules 引用 -> 种子绑定规则: 精确 '@set.rule' -> 只绑定该规则"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"), tracker_rules=["@example_rules.add_site_tag"])
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(tags="")
        tor.tracker_conf = mgr.config.trackers["HHan"]  # 显式 setUp: 模拟 _refresh_torrents 匹配结果
        bound = mgr._rules_for_torrent(tor)
        assert [r.name for r in bound] == ["example_rules.add_site_tag"]


def test_rule_task_executes_only_refs():
    """种子级规则任务只执行 tracker 引用的规则(不再全量执行; 含 set_category 不会被触发)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"), tracker_rules=["@example_rules.add_site_tag"])
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(tags="")
        seed_store(mgr, [tor])
        tor.tracker_conf = mgr._match_tracker_conf(tor)  # 等效 _refresh_torrents 对新增种子的处理
        rules = mgr._rules_for_torrent(tor)
        assert [r.name for r in rules] == ["example_rules.add_site_tag"], "只应绑定被引用的规则"
        for rule in rules:
            task = mgr._create_rule_task(rule, tor.hash)
            assert mgr._handle_rule(rule, task, dry_run=False) is True
        # 只应执行 add_site_tag(加标签); 未引用的 hr_done(设分类)/stop_low_ratio 不执行
        assert ("add_tags", ["HHan", "seed-3D"]) in client.calls
        assert all(c[0] != "set_category" for c in client.calls), f"未引用规则不应执行: {client.calls}"


def test_handle_rule_missing_torrent():
    """store 无该种子: _handle_rule 返回 False 任务消亡(清理由 run_due 自然承担, 不崩溃)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        task = Task("rule", "t", hash="H1", store=mgr.store, interval=0)
        real = Rule("t", {"conditions": [{"state": "is_complete&is_uploading"}], "actions": []}, mgr)
        assert mgr._handle_rule(real, task, dry_run=False) is False
        assert client.calls == [], "种子不存在不应执行动作"
        # 任务清理: 种子删除后任务由 run_due 到期执行时自然消亡(handler 返回 False), 不再显式移除
        tq = mgr.task_queue
        r1 = Task("rule", "r1", hash="H1", interval=60, handler=lambda t, d: FINISHED)
        r2 = Task("rule", "r2", hash="H1", interval=60, handler=lambda t, d: FINISHED)
        r3 = Task("rule", "r3", hash="H2", interval=60, handler=lambda t, d: REQUEUE)
        tq.add_task(r1, now=1000.0)
        tq.add_task(r2, now=1000.0)
        tq.add_task(r3, now=1000.0)
        assert tq.run_due(False, now=1000.0) == 3, "删除种子的任务到期执行一轮"
        assert [t.hash for t in tq._fast] == ["H2"], "H1 任务应自然消亡, H2 保留"


def test_handle_rule_process_ok():
    """_handle_rule: 正常执行规则 -> True 任务保留"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        # 显式给 FakeTorrent 配 conf: 模拟 _refresh_torrents 阶段的 tracker_conf 匹配结果
        # (不依赖隐式 make_ctx, 让 setUp 显式)
        tor = FakeTorrent(tags="")
        tor.tracker_conf = mgr.config.trackers["HHan"]
        client.torrents["HASH123"] = tor
        seed_store(mgr)
        rule = Rule("t", {"actions": [{"add_tags": ["X"]}]}, mgr)
        task = Task("rule", "t", hash="HASH123", store=mgr.store, interval=0)
        assert mgr._handle_rule(rule, task, dry_run=False) is True
        assert ("add_tags", ["X"]) in client.calls


def test_handle_rule_process_error():
    """_handle_rule: 规则执行抛异常 -> 捕获并返回 True"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        client.torrents["HASH123"] = FakeTorrent(tags="")
        seed_store(mgr)
        rule = mock.MagicMock()
        rule.process.side_effect = RuntimeError("boom")
        task = Task("rule", "t", hash="HASH123", store=mgr.store, interval=0)
        assert mgr._handle_rule(rule, task, dry_run=False) is True


def test_load_rules_skips_non_dict_group():
    """_load_rules: 非 dict 规则组 -> 跳过该组不崩溃"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.rules = []
        mgr.config.rules_config = {
            "bad_group": ["not", "a", "dict"],
            "example_rules": {
                "only_rule": {
                    "actions": []
                }
            },
        }
        mgr._load_rules()
        assert [r.name for r in mgr.rules] == ["example_rules.only_rule"]
        assert [r.name for r in mgr.enabled_rules] == ["example_rules.only_rule"]


def test_rules_for_torrent_uninitialized_conf_raises():
    """_rules_for_torrent: 上游未走 refresh (tracker_conf=None) 早暴露 AttributeError, 不静默兜底

    哲学: 防御性 fallback 隐藏调用路径错误, 这里反之让 NoneType.rules 早崩溃
    暴露"种子入 store 后未走 _match_tracker_conf"的设计错误。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        with pytest.raises(AttributeError):
            mgr._rules_for_torrent(FakeTorrent(tags=""))


def test_rule_task_no_enabled_rules():
    """无启用规则: 引用解析空 -> 种子不绑定规则任务"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"), tracker_rules=["@example_rules"])
        client = FakeClient()
        mgr.client = client
        mgr.enabled_rules = []
        tor = FakeTorrent(tags="")
        tor.tracker_conf = mgr.config.trackers["HHan"]
        assert mgr._rules_for_torrent(tor) == []


def test_rules_for_torrent_all_refs():
    """tracker rules 引用整个规则集(@example_rules) -> 绑定全部启用规则; 无引用 -> 不绑定"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"), tracker_rules=["@example_rules"])
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(tags="")
        tor.tracker_conf = mgr.config.trackers["HHan"]
        bound = mgr._rules_for_torrent(tor)
        names = {r.name for r in bound}
        assert names == {"example_rules.add_site_tag", "example_rules.hr_done", "example_rules.stop_low_ratio"}
        # 无 tracker 引用: 种子不绑定任何规则(不再回退执行全部启用规则)
        mgr2 = make_manager(os.path.join(td, "state.json"))  # tracker_rules=None -> conf.rules=[]
        client2 = FakeClient()
        mgr2.client = client2
        tor2 = FakeTorrent(tags="")
        tor2.tracker_conf = mgr2.config.trackers["HHan"]
        assert mgr2._rules_for_torrent(tor2) == []


def test_rules_for_torrent_unresolved_refs():
    """tracker 引用存在但规则解析为空 -> 种子不绑定规则不执行任何动作"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"), tracker_rules=["@nonexistent.rule"])
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(tags="")
        tor.tracker_conf = mgr.config.trackers["HHan"]
        assert mgr._rules_for_torrent(tor) == []


def test_rules_for_torrent_ignores_non_ref():
    """tracker rules 中非 @ 前缀项(旧 ignore_next_rule_error 标志)不被收集为规则引用"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(
            os.path.join(td, "state.json"),
            tracker_rules=["@example_rules.add_site_tag", "ignore_next_rule_error: true"],
        )
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(tags="")
        tor.tracker_conf = mgr.config.trackers["HHan"]
        bound = mgr._rules_for_torrent(tor)
        assert [r.name for r in bound] == ["example_rules.add_site_tag"]
