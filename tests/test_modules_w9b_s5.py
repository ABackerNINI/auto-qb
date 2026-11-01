"""test_modules_w9b_s5 测试计划: W9b(R34, modules 小件) S5 真洞守阵补写

覆盖面(对齐 tmp-analysis/w9b-r34/classify-rules.md + classify-small.md 的真洞簇):
- 高危: facade hashes=None 全库面(de16/at20/22/rt21/23/rst22/24/sc23/25/sl13/15)+
  Task 构造功能灭(ct7/9/13/14/15/18/19/20/22/23/24)+ _handle_rule 定向(no tests hr 族)+
  rule-event 续跑链(ae/he 族)+ 断点协议(rr2/hr9/hr16/mk6/ae29/he5)。
- 中危: 事件入口 payload 键 pin(rm/ad/ta 族)+ 三段触发关断(de 守卫/快照/tor/trigger)+
  dry-run 击穿 + 分派参数互换崩溃 + watch 过滤(tr 族)+ 双分派负例(de1/2/29/56)+
  反转(de36)+ 维护节奏(maintenance_tag_mode 表)+ added 管线(维护/集数/限速三步)+
  _unmount 卸载面(nt3-8)+ watch 集推导(lr 族)+ 引用解析(rf 族)+ rebuild 相位注册(sub 族)+
  speed_curve 方向早退(hc62/104/129)与 ND 标签界(pl16/17)。
- 等价翻案: ae1/ae3/ae4/ae15/ae16(tr19 顺带)由行为断言钉死, 如实记入台账。

## 测试计划(每个测试函数一条)
- test_s5_rules_deleted_dispatch_hash_scope: deleted 分派 ctx.hash 直传 qbapi(全库面)
- test_s5_tracker_speed_limit_hash_scope: 单种限速 torrent_hashes 钉死
- test_s5_maintenance_add_tags_hash_scope: 加标签 torrent_hashes 钉死
- test_s5_maintenance_remove_tags_hash_scope: 删标签 torrent_hashes 钉死
- test_s5_maintenance_similar_tags_hash_scope: 相似标签 torrent_hashes 钉死
- test_s5_maintenance_hr_category_hash_scope: HR 分类 set_category torrent_hashes 钉死
- test_s5_maintenance_hr_tag_template_resolved: HR 标签/分类模板占位符必须解析(错写面)
- test_s5_rule_task_construction_pins: 规则任务 Task 构造面(handler/store/interval/torrent)
- test_s5_rule_task_deleted_torrent_finishes: 种子已删任务消亡(FINISHED)
- test_s5_rule_task_executes_actions_with_hash: 活种子任务执行动作且 hash 直传
- test_s5_rule_task_pending_breakpoint_protocol: pending 断点记录 + FINISHED 协议
- test_s5_torrent_tasks_creation_pins: added 建任务面(维护任务属性 + 节拍)
- test_s5_full_round_rebuild_immediate: full_round 补建立即到期
- test_s5_load_rules_watch_fields_field_rules: field 规则 watch_fields 并集注入
- test_s5_load_rules_watch_tags_on_change: on_change 模式 tags 必须进 watch 集
- test_s5_load_rules_watch_empty_interval: interval 模式无 field 规则时 watch 为空
- test_s5_events_removed_deleted_segment: removed 相位 deleted 段分派(快照/守卫/参数面)
- test_s5_events_removed_state_segment: removed 相位 state 段分派(反转/截断面)
- test_s5_events_removed_field_segment: removed 相位 field 段分派(watch 过滤面)
- test_s5_events_removed_dry_run_no_write: removed 相位 dry-run 闸门
- test_s5_events_added_payload_pin_no_double_dispatch: added 相位 payload pin + 双分派负例
- test_s5_rule_event_resume_executes: rule-event 任务构造面 + 断点续跑执行
- test_s5_rule_event_pending_records_breakpoint: rule-event 首跑即记断点 + 续跑断点推进
- test_s5_maintenance_interval_mode_steps: interval 模式添加/删除/相似标签三步全跑
- test_s5_maintenance_on_change_gate: on_change 模式无 force 不重检 + 登记消费
- test_s5_added_pipeline_maintenance_step: added 管线维护步执行
- test_s5_added_pipeline_force_tags_on_change: added 管线 force_tags(on_change 收敛)
- test_s5_added_pipeline_dry_run_no_write: added 管线 dry-run 闸门
- test_s5_added_pipeline_episode_tags_multi: added 管线集数标签(多集)
- test_s5_added_pipeline_episode_tags_single: added 管线集数标签(单集)
- test_s5_notify_remount_replaces_handler: notify 重挂先摘旧 handler(auto_qb logger)
- test_s5_notify_unmount_gate: _unmount 复位挂载闸 + start 重挂
- test_s5_small_modules_sections_pin: logging/notify sections 段名 pin
- test_s5_rules_subscribe_rebuild_runtime: rebuild_runtime 相位注册 pin
- test_s5_resolve_refs_binding: @规则集/@规则集.规则名 引用解析
- test_s5_rule_manager_dedup_wired: Rule.manager 宿主面(带 cooldown 规则可执行)
- test_s5_rules_apply_receipts: rules.apply 回执(module/action)
- test_s5_tracker_apply_rebind_receipt: tracker.apply 重绑回执计数
- test_s5_curve_download_only_still_manages: 仅下载曲线仍写下载限速(方向早退/崩溃面)
- test_s5_curve_idempotent_upload_still_writes_download: 上传幂等不阻断下载
- test_s5_curve_period_label_nd_bounds: ND period 标签 N 无上界(100D 合法)
- test_s5_tracker_added_dry_run_no_write: tracker added 管线 dry-run 闸门
- test_s5_make_ctx_pins_construction: RuleContext 构造单点参数直传
- test_s5_tracker_match_single_no_warning: 单匹配不告警
"""
import copy
import logging
import os
import tempfile
import time
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from auto_qb.config import NotifyConfig
from auto_qb.config.models import AddEpisodeTagsConfig
from auto_qb.core.module import AppContext
from auto_qb.core.modules import notify_mod as notify_mod
from auto_qb.core.taskqueue import FINISHED, REQUEUE
from auto_qb.rules import Rule
from auto_qb.rules.base import ActionResult
from helpers import FakeClient, FakeTorrent, _hr_rule, make_manager, seed_store, write_dat

from test_speed_curve import FULL_DOWNLOAD, _gslc, _make_mgr, _pc, _points, _run_curve

GIB = 1024**3


def _conf(name, domains):
    """TrackerConfig 构造(其余字段取默认: tags=[]/限速 0/rules=[])"""
    from auto_qb.config import TrackerConfig

    return TrackerConfig(name=name, domains=domains)


class HashSpyClient(FakeClient):
    """记录标签/分类写操作的 torrent_hashes 作用范围(facade hashes=None 全库面守阵)"""
    def __init__(self):
        super().__init__()
        self.tag_hash_calls = []

    def torrents_add_tags(self, tags=None, torrent_hashes=None):
        super().torrents_add_tags(tags=tags, torrent_hashes=torrent_hashes)
        self.tag_hash_calls.append(("add_tags", list(tags or []), torrent_hashes))

    def torrents_remove_tags(self, tags=None, torrent_hashes=None):
        super().torrents_remove_tags(tags=tags, torrent_hashes=torrent_hashes)
        self.tag_hash_calls.append(("remove_tags", list(tags or []), torrent_hashes))

    def torrents_set_category(self, category=None, torrent_hashes=None):
        super().torrents_set_category(category=category, torrent_hashes=torrent_hashes)
        self.tag_hash_calls.append(("set_category", category, torrent_hashes))


class _StubNotifyHandler(logging.Handler):
    """可挂 logger 的通知 handler 替身(enabled 热开关面)"""

    enabled = True

    def emit(self, record):
        pass


class _PendingAction:
    """恒 pending 的桩动作(断点协议守阵用)"""

    name = "stub-pending"
    ignore_error = False

    def execute(self, ctx):
        return ActionResult.pending("等待异步")


def _ev_mgr(state_file, rules_cfg):
    """事件分派守阵用 manager: tracker 绑定 @ev 引用 + 指定规则集"""
    mgr = make_manager(state_file, tracker_rules=["@ev"])
    mgr.config.rules_config = rules_cfg
    mgr.host.get("rules").load_rules()
    return mgr


def _interval_rule(mgr, name, tags=("x", ), **spec_kw):
    spec = {"trigger": "interval", "actions": [{"add_tags": list(tags)}]}
    spec.update(spec_kw)
    return Rule(name, spec, mgr)


# ============================================================
# 高危簇 1: facade torrent_hashes=None 全库面
# ============================================================
def test_s5_rules_deleted_dispatch_hash_scope():
    """deleted 分派: 动作以 ctx.hash(真实 hash)直传 qbapi, 不得是 None(全库面)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _ev_mgr(
            os.path.join(td, "state.json"),
            {"ev": {
                "d1": {
                    "trigger": "on_torrent_deleted",
                    "actions": [{
                        "remove_tags": ["old"]
                    }]
                }
            }}
        )
        client = HashSpyClient()
        mgr.client = client
        conf = mgr.config.trackers["HHan"]
        snap = FakeTorrent(hash="HDEL", tags="old,keep")
        snap.tracker_conf = conf
        triggered = mgr.host.get("rules")._dispatch_events(
            added=[], removed=["HDEL"], dry_run=False, removed_snapshots={"HDEL": snap}
        )
        assert triggered == ["HDEL"]
        assert client.tag_hash_calls == [("remove_tags", ["old"], "HDEL")]


def test_s5_tracker_speed_limit_hash_scope():
    """单种限速: torrent_hashes 必须是种子自身 hash(全库限速面)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = HashSpyClient()
        mgr.client = client
        tor = FakeTorrent(hash="H1")
        conf = _conf("HHan", ["hhanclub.net"])
        conf.upload_speed_limit = 5 * 1024 * 1024
        conf.download_speed_limit = 2 * 1024 * 1024
        mgr.ctx.trackers.apply_speed_limit(tor, conf, dry_run=False)
        assert client.limit_location_hashes_calls == [
            ("set_upload_limit", "H1"),
            ("set_download_limit", "H1"),
        ]


def test_s5_maintenance_add_tags_hash_scope():
    """维护加标签: torrent_hashes 钉死为种子 hash(全库加标签面)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = HashSpyClient()
        mgr.client = client
        conf = mgr.config.trackers["HHan"]
        conf.tags = ["HHan"]
        tor = FakeTorrent(hash="HM1", tags="")
        tor.tracker_conf = conf
        mgr.ctx.maintenance.handle_maintenance(tor, dry_run=False)
        assert ("add_tags", ["HHan"], "HM1") in client.tag_hash_calls


def test_s5_maintenance_remove_tags_hash_scope():
    """维护删标签: torrent_hashes 钉死为种子 hash(全库删标签面)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = HashSpyClient()
        mgr.client = client
        conf = mgr.config.trackers["HHan"]
        conf.remove_tags = ["regex:^seed-"]
        tor = FakeTorrent(hash="HM2", tags="seed-3D")
        tor.tracker_conf = conf
        mgr.ctx.maintenance.handle_maintenance(tor, dry_run=False)
        assert ("remove_tags", ["seed-3D"], "HM2") in client.tag_hash_calls


def test_s5_maintenance_similar_tags_hash_scope():
    """维护删相似标签: torrent_hashes 钉死为种子 hash(全库面)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = HashSpyClient()
        mgr.client = client
        conf = mgr.config.trackers["HHan"]
        conf.tags = ["HHan"]
        conf.remove_similar_tags = True
        tor = FakeTorrent(hash="HM3", tags="hhan,HHan")
        tor.tracker_conf = conf
        mgr.ctx.maintenance.handle_maintenance(tor, dry_run=False)
        assert ("remove_tags", ["hhan"], "HM3") in client.tag_hash_calls


def test_s5_maintenance_hr_category_hash_scope():
    """HR 达标分类: set_category 的 torrent_hashes 钉死为种子 hash(全库改分类面)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = HashSpyClient()
        mgr.client = client
        conf = mgr.config.trackers["HHan"]
        conf.hr = _hr_rule()
        tor = FakeTorrent(hash="HM4", tags="", seeding_time=4 * 86400)
        tor.tracker_conf = conf
        mgr.ctx.maintenance.handle_maintenance(tor, dry_run=False)
        assert ("set_category", "--HR3D--", "HM4") in client.tag_hash_calls


def test_s5_maintenance_hr_tag_template_resolved():
    """HR 标签/分类模板占位符必须按站点 conf 解析, 不得原文/None 真写 qB"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = HashSpyClient()
        mgr.client = client
        conf = mgr.config.trackers["HHan"]
        # 达标路径: satisfied 标签模板解析
        conf.hr = _hr_rule(
            add_tag="",
            add_category="",
            add_tag_for_satisfied="DONE-${required_seeding_time}",
            add_category_for_satisfied="",
        )
        tor = FakeTorrent(hash="HM5", tags="", seeding_time=4 * 86400)
        tor.tracker_conf = conf
        mgr.ctx.maintenance.handle_maintenance(tor, dry_run=False)
        assert ("add_tags", ["DONE-3D"], "HM5") in client.tag_hash_calls
        # 未达标路径: HR 标签模板解析 + HR 分类模板解析
        client.tag_hash_calls.clear()
        conf.hr = _hr_rule(
            add_tag="HR-${required_seeding_time}",
            add_category="!!HR${required_seeding_time}!!",
            add_tag_for_satisfied="",
            add_category_for_satisfied="",
        )
        tor2 = FakeTorrent(hash="HM6", tags="", seeding_time=0)
        tor2.tracker_conf = conf
        mgr.ctx.maintenance.handle_maintenance(tor2, dry_run=False)
        assert ("add_tags", ["HR-3D"], "HM6") in client.tag_hash_calls
        assert ("set_category", "!!HR3D!!", "HM6") in client.tag_hash_calls


# ============================================================
# 高危簇 2: Task 构造功能灭 + _handle_rule 定向(no tests 面)
# ============================================================
def test_s5_rule_task_construction_pins():
    """规则任务 Task 构造面: handler/store/interval/torrent 全部钉死 + handler 可执行"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = HashSpyClient()
        mgr.client = client
        tor = FakeTorrent(hash="HB1", tags="")
        seed_store(mgr, [tor])
        rules = mgr.host.get("rules")
        rule = _interval_rule(mgr, "t5.b1", tags=("g1", ), interval="10M")
        task = rules._create_rule_task(rule, "HB1")
        assert task is not None
        assert task.handler is not None, "handler 不得为空(空则恒 REQUEUE 空转)"
        assert task._store is mgr.store, "store 缺失则 task.torrent 恒 None(任务首轮消亡)"
        assert task.interval == 600, "interval 必须用规则自身 interval(缺失归一 1s = API 风暴)"
        assert task.torrent is tor
        rc = task.handler(task, False)
        assert rc == REQUEUE, "无断点成功执行应周期重入队(返 None = 消亡)"
        assert ("add_tags", ["g1"], "HB1") in client.tag_hash_calls


def test_s5_rule_task_deleted_torrent_finishes():
    """种子已删(task.torrent None)-> 任务 FINISHED 消亡, 不得进入执行路径"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = HashSpyClient()
        mgr.client = client
        rules = mgr.host.get("rules")
        rule = _interval_rule(mgr, "t5.b2")
        task = rules._create_rule_task(rule, "HMISS")
        assert task.torrent is None
        assert task.handler(task, False) == FINISHED


def test_s5_rule_task_executes_actions_with_hash():
    """活种子任务: 动作执行且 ctx.hash/task 直传(ctx=None/rule=None/hash=None 面全灭)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = HashSpyClient()
        mgr.client = client
        tor = FakeTorrent(hash="HB3", tags="")
        seed_store(mgr, [tor])
        rules = mgr.host.get("rules")
        rule = _interval_rule(mgr, "t5.b3")
        task = rules._create_rule_task(rule, "HB3")
        assert task.handler(task, False) == REQUEUE
        assert client.tag_hash_calls == [("add_tags", ["x"], "HB3")]


def test_s5_rule_task_pending_breakpoint_protocol():
    """pending 中断: 断点记在任务上且本轮 FINISHED(断点协议面)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.client = FakeClient()
        rules = mgr.host.get("rules")
        rule = _interval_rule(mgr, "t5.b4")
        # W3-B 起执行单元是构造期派生的 rule.steps; rule.actions 只是兼容视图(改它不影响执行)
        rule.steps = [("action", _PendingAction(), Rule._resolve_on_error(None))]
        seed_store(mgr, [FakeTorrent(hash="HB4", tags="")])
        task = rules._create_rule_task(rule, "HB4")
        rc = task.handler(task, False)
        assert rc == FINISHED, "有断点本轮不重入(恒 FINISHED/恒 REQUEUE 都破协议)"
        assert task.resume_index == 1, "pending 应记录断点(ctx.task 注入面)"


def test_s5_torrent_tasks_creation_pins():
    """added 建任务面: 维护任务属性(handler/store/interval/torrent)与节拍钉死"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.client = FakeClient()
        conf = mgr.config.trackers["HHan"]
        tor = FakeTorrent(hash="HB5", tags="")
        tor.tracker_conf = conf
        seed_store(mgr, [tor])
        mgr.host.get("rules")._on_torrents_added(SimpleNamespace(payload={"hash": "HB5"}))
        tasks = [t for t in mgr.task_queue._fast if t.kind == "internal" and t.hash == "HB5"]
        assert len(tasks) == 1, "added 管线应建内置维护任务"
        t = tasks[0]
        assert t.name == "maintenance"
        assert t._store is mgr.store
        assert t.handler is not None
        assert t.interval == mgr.config.interval, "interval 缺失归一 1s = API 风暴"
        assert t.torrent is tor
        assert t.next_run >= time.time() + mgr.config.interval - 5, "非补建路径不得立即到期"


def test_s5_full_round_rebuild_immediate():
    """full_round 补建: 任务立即到期(下一 tick 兑现一次维护)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.client = FakeClient()
        tor = FakeTorrent(hash="HB6", tags="")
        tor.tracker_conf = mgr.config.trackers["HHan"]
        seed_store(mgr, [tor])
        mgr.host.get("rules")._on_full_round(None)
        tasks = [t for t in mgr.task_queue._fast if t.kind == "internal" and t.hash == "HB6"]
        assert len(tasks) == 1
        assert tasks[0].name == "maintenance"
        assert tasks[0].next_run <= time.time() + 5, "补建任务应立即到期"


# ============================================================
# watch 集推导(load_rules)
# ============================================================
def test_s5_load_rules_watch_fields_field_rules():
    """field 规则的 watch_fields 并集注入 store(watch 集推导: field 检测关面)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"), bare=True)
        mgr.config.rules_config = {
            "g":
                {
                    "f1":
                        {
                            "trigger": "on_torrent_field_changed",
                            "watch_fields": ["tags"],
                            "actions": [{
                                "add_tags": ["x"]
                            }]
                        }
                }
        }
        mgr.host.get("rules").load_rules()
        assert mgr.store.watch_fields == frozenset({"tags"})


def test_s5_load_rules_watch_tags_on_change():
    """on_change 模式: tags 必须进 watch 集(B 路径外部 tags 变化检测)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"), bare=True)
        mgr.config.maintenance_tag_mode = "on_change"
        mgr.config.rules_config = {"g": {"i1": {"trigger": "interval", "actions": [{"add_tags": ["x"]}]}}}
        mgr.host.get("rules").load_rules()
        assert "tags" in mgr.store.watch_fields


def test_s5_load_rules_watch_empty_interval():
    """interval 模式且无 field 规则: watch 集必须为空(检测整体关闭, 不得误开 tags)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"), bare=True)
        mgr.config.rules_config = {"g": {"i1": {"trigger": "interval", "actions": [{"add_tags": ["x"]}]}}}
        mgr.host.get("rules").load_rules()
        assert mgr.store.watch_fields == frozenset()


# ============================================================
# 事件入口 payload pin + 三段分派(removed 相位)
# ============================================================
def test_s5_events_removed_deleted_segment():
    """removed 相位 deleted 段: payload removed/snapshots 键 pin + 快照/守卫/参数面"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _ev_mgr(
            os.path.join(td, "state.json"),
            {"ev": {
                "d1": {
                    "trigger": "on_torrent_deleted",
                    "actions": [{
                        "remove_tags": ["old"]
                    }]
                }
            }}
        )
        client = HashSpyClient()
        mgr.client = client
        conf = mgr.config.trackers["HHan"]
        snap = FakeTorrent(hash="HDEL", tags="old")
        snap.tracker_conf = conf
        # HDX 无快照: continue 跳过不截断后续
        mgr.host.get("rules")._on_events_removed(
            SimpleNamespace(payload={
                "removed": ["HDX", "HDEL"],
                "snapshots": {
                    "HDEL": snap
                },
                "dry_run": False
            })
        )
        assert client.tag_hash_calls == [("remove_tags", ["old"], "HDEL")]


def test_s5_events_removed_state_segment():
    """removed 相位 state 段: state_changed 键 pin + 反转/截断/参数面"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _ev_mgr(
            os.path.join(td, "state.json"),
            {"ev": {
                "s1": {
                    "trigger": "on_torrent_state_enum_changed",
                    "actions": [{
                        "add_tags": ["st"]
                    }]
                }
            }},
        )
        client = HashSpyClient()
        mgr.client = client
        conf = mgr.config.trackers["HHan"]
        tor = FakeTorrent(hash="HST", tags="")
        tor.tracker_conf = conf
        seed_store(mgr, [tor])
        mgr.store.by_hash["HNC"] = FakeTorrent(hash="HNC", tags="")  # 无 tracker 配置: continue
        cur = FakeTorrent(state="pausedUP").state_enum
        old = FakeTorrent(state="stalledUP").state_enum
        mgr.store.state_changed = [("HMISS", cur), ("HNC", cur), ("HST", cur)]
        mgr.store.state_snapshot = {"HST": old, "HNC": old}  # HNC 在册且确有变化, 走到 tor 守卫(conf None)
        mgr.host.get("rules")._on_events_removed(SimpleNamespace(payload={"removed": [], "dry_run": False}))
        assert client.tag_hash_calls == [("add_tags", ["st"], "HST")]


def test_s5_events_removed_field_segment():
    """removed 相位 field 段: field_changed 键 pin + watch 交集过滤(过滤反转/截断面)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _ev_mgr(
            os.path.join(td, "state.json"),
            {
                "ev":
                    {
                        "f2":
                            {
                                "trigger": "on_torrent_field_changed",
                                "watch_fields": ["category"],
                                "actions": [{
                                    "add_tags": ["f2"]
                                }]
                            },
                        "f1":
                            {
                                "trigger": "on_torrent_field_changed",
                                "watch_fields": ["tags"],
                                "actions": [{
                                    "add_tags": ["fld"]
                                }]
                            },
                    }
            },
        )
        client = HashSpyClient()
        mgr.client = client
        conf = mgr.config.trackers["HHan"]
        tor = FakeTorrent(hash="HFLD", tags="")
        tor.tracker_conf = conf
        seed_store(mgr, [tor])
        mgr.store.by_hash["HFNC"] = FakeTorrent(hash="HFNC", tags="")
        mgr.store.field_changed = [("HFM", {"tags"}), ("HFNC", {"tags"}), ("HFLD", {"tags"})]
        mgr.host.get("rules")._on_events_removed(SimpleNamespace(payload={"removed": [], "dry_run": False}))
        assert client.tag_hash_calls == [("add_tags", ["fld"], "HFLD")], "只该触发 watch 交集命中的 f1"


def test_s5_events_removed_dry_run_no_write():
    """removed 相位 dry-run 闸门: payload dry_run=True 不得真写 qB"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _ev_mgr(
            os.path.join(td, "state.json"),
            {"ev": {
                "d1": {
                    "trigger": "on_torrent_deleted",
                    "actions": [{
                        "remove_tags": ["old"]
                    }]
                }
            }}
        )
        client = HashSpyClient()
        mgr.client = client
        conf = mgr.config.trackers["HHan"]
        snap = FakeTorrent(hash="HDEL", tags="old")
        snap.tracker_conf = conf
        mgr.host.get("rules")._on_events_removed(
            SimpleNamespace(payload={
                "removed": ["HDEL"],
                "snapshots": {
                    "HDEL": snap
                },
                "dry_run": True
            })
        )
        assert client.tag_hash_calls == []
        assert client.calls == []


def test_s5_events_added_payload_pin_no_double_dispatch():
    """added 相位: dry_run 键 pin + state/field 段不得被 added 调用双分派"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _ev_mgr(
            os.path.join(td, "state.json"),
            {
                "ev":
                    {
                        "a1": {
                            "trigger": "on_torrent_added",
                            "actions": [{
                                "add_tags": ["ad"]
                            }]
                        },
                        "s1": {
                            "trigger": "on_torrent_state_enum_changed",
                            "actions": [{
                                "add_tags": ["st"]
                            }]
                        },
                        "f1":
                            {
                                "trigger": "on_torrent_field_changed",
                                "watch_fields": ["tags"],
                                "actions": [{
                                    "add_tags": ["fld"]
                                }]
                            },
                    }
            },
        )
        client = HashSpyClient()
        mgr.client = client
        conf = mgr.config.trackers["HHan"]
        tor = FakeTorrent(hash="HAD", tags="")
        tor.tracker_conf = conf
        tor_hst = FakeTorrent(hash="HST", tags="")
        tor_hst.tracker_conf = conf
        tor_fld = FakeTorrent(hash="HFLD", tags="")
        tor_fld.tracker_conf = conf
        seed_store(mgr, [tor, tor_hst, tor_fld])
        cur = FakeTorrent(state="pausedUP").state_enum
        old = FakeTorrent(state="stalledUP").state_enum
        mgr.store.state_changed = [("HST", cur)]
        mgr.store.state_snapshot = {"HST": old}
        mgr.store.field_changed = [("HFLD", {"tags"})]
        rules = mgr.host.get("rules")
        rules._on_events_added(SimpleNamespace(payload={"added": ["HAD"], "dry_run": False}))
        assert client.tag_hash_calls == [("add_tags", ["ad"], "HAD")], "added 相位不得双分派 state/field 段"
        client.tag_hash_calls.clear()
        tor.tags = ""  # 复位: 防「标签已加过」短路掩盖 dry-run 击穿
        rules._on_events_added(SimpleNamespace(payload={"added": ["HAD"], "dry_run": True}))
        assert client.tag_hash_calls == [], "added 相位 dry-run 不得真写"


# ============================================================
# rule-event 续跑链 + 断点协议
# ============================================================
def test_s5_rule_event_resume_executes():
    """rule-event 任务构造面(store/hash/kind/name) + 断点续跑再执行 + 恒 FINISHED"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = HashSpyClient()
        mgr.client = client
        tor = FakeTorrent(hash="HE1", tags="")
        seed_store(mgr, [tor])
        rules = mgr.host.get("rules")
        rule = _interval_rule(mgr, "t5.e1")
        task = rules._apply_event_rule(rule, "HE1")
        assert task._store is mgr.store
        assert task.hash == "HE1"
        assert task.kind == "rule-event"
        assert task.name == "t5.e1"
        assert client.tag_hash_calls == [("add_tags", ["x"], "HE1")], "首跑应同步执行"
        tor.tags = ""  # 复位: 续跑应再次产生写动作
        rc = task.handler(task, False)
        assert rc == FINISHED, "rule-event 续跑 handler 恒 FINISHED"
        assert client.tag_hash_calls == [("add_tags", ["x"], "HE1")] * 2, "续跑应再次执行(恢复半边)"


def test_s5_rule_event_pending_records_breakpoint():
    """rule-event 首跑遇 pending 记断点; 续跑推进断点(ctx.task 注入面)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.client = FakeClient()
        rules = mgr.host.get("rules")
        rule = _interval_rule(mgr, "t5.e2")
        # 同上: 断点索引以 rule.steps 为单位(W3-B), 两个 pending 占两步
        rule.steps = [("action", _PendingAction(), Rule._resolve_on_error(None)) for _ in range(2)]
        seed_store(mgr, [FakeTorrent(hash="HE2", tags="")])
        task = rules._apply_event_rule(rule, "HE2")
        assert task.resume_index == 1, "首跑 pending 应记断点(ctx.task=None 则断点不记)"
        rc = task.handler(task, False)
        assert rc == FINISHED
        assert task.resume_index == 2, "续跑应从断点推进到下一动作"


# ============================================================
# 维护节奏(maintenance_tag_mode)
# ============================================================
def test_s5_maintenance_interval_mode_steps():
    """interval 模式: 添加/删除/相似标签三步全跑(维护灭/参数互换面)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = HashSpyClient()
        mgr.client = client
        conf = mgr.config.trackers["HHan"]
        conf.tags = ["HHan"]
        conf.remove_tags = ["regex:^seed-"]
        conf.remove_similar_tags = True
        tor = FakeTorrent(hash="HF1", tags="seed-3D,hhan")
        tor.tracker_conf = conf
        mgr.ctx.maintenance.handle_maintenance(tor, dry_run=False)
        assert ("add_tags", ["HHan"], "HF1") in client.tag_hash_calls
        assert ("remove_tags", ["seed-3D"], "HF1") in client.tag_hash_calls
        assert ("remove_tags", ["hhan"], "HF1") in client.tag_hash_calls


def test_s5_maintenance_on_change_gate():
    """on_change 模式: 无 force/无登记不重检; 有登记重检一次且登记被消费"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = HashSpyClient()
        mgr.client = client
        mgr.config.maintenance_tag_mode = "on_change"
        conf = mgr.config.trackers["HHan"]
        conf.tags = ["HHan"]
        conf.hr = None
        tor = FakeTorrent(hash="HF2", tags="")
        tor.tracker_conf = conf
        mgr.ctx.maintenance.handle_maintenance(tor, dry_run=False)
        assert client.tag_hash_calls == [], "on_change 无 force/登记不得重检"
        mgr.store.external_tag_changes.add("HF2")
        mgr.ctx.maintenance.handle_maintenance(tor, dry_run=False)
        assert ("add_tags", ["HHan"], "HF2") in client.tag_hash_calls
        assert "HF2" not in mgr.store.external_tag_changes, "登记应消费一次"


# ============================================================
# added 管线(维护/集数两步)
# ============================================================
def test_s5_added_pipeline_maintenance_step():
    """added 管线维护步: handle_maintenance 收到真实 torrent(不得 None 早退)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = HashSpyClient()
        mgr.client = client
        conf = mgr.config.trackers["HHan"]
        conf.tags = ["HHan"]
        tor = FakeTorrent(hash="HG1", tags="")
        tor.tracker_conf = conf
        seed_store(mgr, [tor])
        mgr.host.get("maintenance")._on_torrent_added(SimpleNamespace(payload={"hash": "HG1", "dry_run": False}))
        assert ("add_tags", ["HHan"], "HG1") in client.tag_hash_calls


def test_s5_added_pipeline_force_tags_on_change():
    """added 管线 force_tags=True: on_change 模式添加路径收敛一次"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = HashSpyClient()
        mgr.client = client
        mgr.config.maintenance_tag_mode = "on_change"
        conf = mgr.config.trackers["HHan"]
        conf.tags = ["HHan"]
        tor = FakeTorrent(hash="HG2", tags="")
        tor.tracker_conf = conf
        seed_store(mgr, [tor])
        mgr.host.get("maintenance")._on_torrent_added(SimpleNamespace(payload={"hash": "HG2", "dry_run": False}))
        assert ("add_tags", ["HHan"], "HG2") in client.tag_hash_calls, "添加路径必须强制重检一次"


def test_s5_added_pipeline_dry_run_no_write():
    """added 管线 dry-run 闸门: dry_run=True 不真写 qB"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = HashSpyClient()
        mgr.client = client
        conf = mgr.config.trackers["HHan"]
        conf.tags = ["HHan"]
        tor = FakeTorrent(hash="HG3", tags="")
        tor.tracker_conf = conf
        seed_store(mgr, [tor])
        mgr.host.get("maintenance")._on_torrent_added(SimpleNamespace(payload={"hash": "HG3", "dry_run": True}))
        assert client.tag_hash_calls == []
        assert client.calls == []


def test_s5_added_pipeline_episode_tags_multi():
    """added 管线集数步(多集): 解析 EP01~05 添加 zE1-5"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = HashSpyClient()
        mgr.client = client
        mgr.config.add_episode_tags = AddEpisodeTagsConfig(enabled=True)
        client.files_map["HG4"] = [SimpleNamespace(name=f"EP{i:02d}.mkv") for i in range(1, 6)]
        tor = FakeTorrent(hash="HG4", tags="")
        tor.tracker_conf = mgr.config.trackers["HHan"]
        seed_store(mgr, [tor])
        mgr.host.get("maintenance")._on_torrent_added(SimpleNamespace(payload={"hash": "HG4", "dry_run": False}))
        assert ("add_tags", ["zE1-5"], "HG4") in client.tag_hash_calls


def test_s5_added_pipeline_episode_tags_single():
    """added 管线集数步(单集): single 模板分支可用"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = HashSpyClient()
        mgr.client = client
        mgr.config.add_episode_tags = AddEpisodeTagsConfig(enabled=True)
        client.files_map["HG5"] = [SimpleNamespace(name="EP01.mkv")]
        tor = FakeTorrent(hash="HG5", tags="")
        tor.tracker_conf = mgr.config.trackers["HHan"]
        seed_store(mgr, [tor])
        mgr.host.get("maintenance")._on_torrent_added(SimpleNamespace(payload={"hash": "HG5", "dry_run": False}))
        assert ("add_tags", ["zE1"], "HG5") in client.tag_hash_calls


# ============================================================
# notify _unmount 卸载面
# ============================================================
def _notify_mod(monkeypatch, created):
    """NotifyModule + setup_notify 替身(挂到 auto_qb logger, 记录创建序)"""
    pkg = logging.getLogger("auto_qb")

    def fake_setup(config, force=False):
        h = _StubNotifyHandler()
        pkg.addHandler(h)
        created.append(h)
        return h

    monkeypatch.setattr(notify_mod, "setup_notify", fake_setup)
    ctx = AppContext(SimpleNamespace(notify=NotifyConfig(enabled=True, min_level="WARNING")))
    return notify_mod.NotifyModule(ctx), pkg


def test_s5_notify_remount_replaces_handler(monkeypatch):
    """notify 重挂: 先摘旧 handler(auto_qb logger 上不残留孤儿)再挂新"""
    with tempfile.TemporaryDirectory() as td:
        created = []
        mod, pkg = _notify_mod(monkeypatch, created)
        old = SimpleNamespace(notify=NotifyConfig(enabled=True, min_level="INFO"))
        new = SimpleNamespace(notify=NotifyConfig(enabled=True, min_level="ERROR"))
        try:
            mod.start(mod._ctx, dry_run=False)
            assert len(created) == 1
            res = mod.apply(old, new)
            assert res.module == "notify"
            assert len(created) == 2, "应重挂一次新 handler"
            assert created[0] not in pkg.handlers, "旧 handler 必须被摘除(孤儿 = 重复通知)"
            assert mod._handler is created[1] and created[1] in pkg.handlers
        finally:
            for h in created:
                pkg.removeHandler(h)


def test_s5_notify_unmount_gate(monkeypatch):
    """_unmount: 复位挂载闸(_handler is None)+ start 可重挂(通知不得死)"""
    created = []
    mod, pkg = _notify_mod(monkeypatch, created)
    try:
        mod.start(mod._ctx, dry_run=False)
        assert mod.is_enabled() is True
        mod._unmount()
        assert mod._handler is None, "卸载后挂载闸必须复位为 None"
        assert mod.enabled_state() is None
        assert mod.is_enabled() is False
        mod.start(mod._ctx, dry_run=False)
        assert mod.is_enabled() is True, "卸载后 start 必须能重挂"
    finally:
        for h in created:
            pkg.removeHandler(h)


def test_s5_small_modules_sections_pin():
    """logging/notify sections 段名 pin(段认领漂移 = 误全量重建)"""
    from auto_qb.core.modules import logging_mod

    assert logging_mod.LoggingModule().sections() == ("logging", )
    ctx = AppContext(SimpleNamespace(notify=NotifyConfig()))
    assert notify_mod.NotifyModule(ctx).sections() == ("notify", )


def test_s5_rules_subscribe_rebuild_runtime():
    """rebuild_runtime 相位注册 pin(通道错位/订阅者 None 面全灭)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        rules = mgr.host.get("rules")

        class RecPhases:
            def __init__(self):
                self.registered = []

            def on(self, channel, handler):
                self.registered.append((channel, handler))

        ph = RecPhases()
        rules.subscribe(ph)
        assert ("rebuild_runtime", rules._on_rebuild_runtime) in ph.registered
        assert len(ph.registered) == 5


# ============================================================
# 引用解析 + Rule 宿主面 + 回执
# ============================================================
def test_s5_resolve_refs_binding():
    """@规则集 / @规则集.规则名 引用解析: 前缀与点引用绑定 + 去重"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"), bare=True)
        spec = {"trigger": "interval", "actions": [{"add_tags": ["a"]}]}
        mgr.config.rules_config = {"g": {"r1": dict(spec), "r2": dict(spec)}, "h": {"x": dict(spec)}}
        rules = mgr.host.get("rules")
        rules.load_rules()
        assert [r.name for r in rules._resolve_refs(["g"])] == ["g.r1", "g.r2"], "前缀绑定不含他组"
        assert [r.name for r in rules._resolve_refs(["g.r2"])] == ["g.r2"], "点引用精确绑定"
        assert [r.name for r in rules._resolve_refs(["g", "g.r1"])] == ["g.r1", "g.r2"], "按名称去重"
        assert [r.name for r in rules._resolve_refs(["g.r1", "g.r1"])] == ["g.r1"], "点引用重复去重"
        assert rules._resolve_refs(["a.b.c"]) == [], "多点引用不崩溃不误绑"
        assert all(r is not None for r in rules._resolve_refs(["g"]))


def test_s5_rule_manager_dedup_wired():
    """Rule.manager 宿主面: load_rules 装载的带 cooldown 规则可完整执行(去重判定走 manager)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"), tracker_rules=["@g"])
        client = HashSpyClient()
        mgr.client = client
        tor = FakeTorrent(hash="HJ2", tags="")
        seed_store(mgr, [tor])
        mgr.config.rules_config = {
            "g":
                {
                    "cd":
                        {
                            "trigger": "interval",
                            "interval": "60S",
                            "cooldown": "10M",
                            "actions": [{
                                "add_tags": ["cd"]
                            }]
                        }
                }
        }
        rules = mgr.host.get("rules")
        rules.load_rules()
        rule = next(r for r in rules.enabled_rules if r.name == "g.cd")
        assert rule.cooldown > 0, "前置: 该规则必须走 manager 去重判定"
        task = rules._create_rule_task(rule, "HJ2")
        rc = task.handler(task, False)
        assert rc == REQUEUE
        assert ("add_tags", ["cd"], "HJ2") in client.tag_hash_calls, "manager=None 时去重判定崩(规则死)"


def test_s5_rules_apply_receipts():
    """rules.apply 回执: 短路与重建都带 module 名"""
    from unittest import mock

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.client = FakeClient()
        rules = mgr.host.get("rules")
        old = mgr.config
        same = mock.MagicMock()
        for attr in (
            "rules_config", "delete_tags", "delete_tags_if_has_no_torrents", "global_speed_limit_curve", "trackers"
        ):
            setattr(same, attr, getattr(old, attr))
        same.interval = old.interval
        res = rules.apply(old, same)
        assert res.module == "rules" and res.action == "none"
        changed = mock.MagicMock()
        for attr in (
            "rules_config", "delete_tags", "delete_tags_if_has_no_torrents", "global_speed_limit_curve", "trackers"
        ):
            setattr(changed, attr, getattr(old, attr))
        changed.interval = 999.0
        mgr.connect = mock.MagicMock(return_value=True)
        res2 = rules.apply(old, changed)
        assert res2.module == "rules", "重建回执 module 名不得丢"
        assert res2.action == "rebuilt"


def test_s5_tracker_apply_rebind_receipt():
    """tracker.apply 回执: 段相等短路 module 名 + 重绑计数(2 条记录)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.client = FakeClient()
        from auto_qb.config import TrackerConfig

        t1 = FakeTorrent(hash="HJ4")
        t1.tracker_conf = TrackerConfig(name="HHan", domains=["tracker.hhanclub.net"])
        t2 = FakeTorrent(hash="HJ5")
        t2.tracker_conf = t1.tracker_conf
        seed_store(mgr, [t1, t2])
        trackers = {"HHan": t1.tracker_conf}
        # 段值相等 -> 短路, module 名不得丢
        res0 = mgr.ctx.trackers.apply(SimpleNamespace(trackers=trackers), SimpleNamespace(trackers=dict(trackers)))
        assert res0.module == "tracker" and res0.action == "none"
        old = SimpleNamespace(trackers=trackers)
        new = SimpleNamespace(
            trackers={"HHan": TrackerConfig(name="HHan", domains=["tracker.hhanclub.net", "extra.example.net"])}
        )
        res = mgr.ctx.trackers.apply(old, new)
        assert res.module == "tracker"
        assert res.action == "rebound 2", "重绑计数钉死(2 条存量)"


# ============================================================
# speed_curve 方向早退 / ND 标签界
# ============================================================
def test_s5_curve_download_only_still_manages():
    """仅下载曲线: 上传无曲线不得阻断/炸掉下载方向管理"""
    with tempfile.TemporaryDirectory() as td:
        today = date.today()
        dat = write_dat(Path(td), [(today, 0, 15 * GIB)])
        gslc = _gslc(dat, _pc("day", down=_points(FULL_DOWNLOAD)))
        mgr, client = _make_mgr(Path(td), gslc)
        assert _run_curve(mgr)
        assert client.transfer.calls == [("set_download_limit", 11264 * 1024)]


def test_s5_curve_idempotent_upload_still_writes_download():
    """上传方向幂等(目标==当前)不得提前退出双方向循环"""
    with tempfile.TemporaryDirectory() as td:
        today = date.today()
        dat = write_dat(Path(td), [(today, 15 * GIB, 15 * GIB)])
        gslc = _gslc(dat, _pc("day", up=_points([(10, 6)]), down=_points(FULL_DOWNLOAD)))
        mgr, client = _make_mgr(Path(td), gslc)
        client.transfer.limits["upload_limit"] = 6144 * 1024  # 已是上传目标 -> 幂等
        assert _run_curve(mgr)
        assert client.transfer.calls == [("set_download_limit", 11264 * 1024)], "上传幂等不得阻断下载写入"


def test_s5_curve_period_label_nd_bounds():
    """ND period 标签: N 无上界("100D" 配置合法), 100 走数字直出"""
    from auto_qb.core.modules.speed_curve_mod import _period_label

    assert _period_label("100D") == "100日"
    assert _period_label("7D") == "七日"


# ============================================================
# tracker added 管线 dry-run + ctx 构造 + 散点
# ============================================================
def test_s5_tracker_added_dry_run_no_write():
    """tracker added 管线: dry_run=True 不写真限速"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = HashSpyClient()
        mgr.client = client
        conf = _conf("HHan", ["hhanclub.net"])
        conf.upload_speed_limit = 5 * 1024 * 1024
        conf.download_speed_limit = 2 * 1024 * 1024
        tor = FakeTorrent(hash="HL1")
        tor.tracker_conf = conf
        seed_store(mgr, [tor])
        mgr.host.get("tracker")._on_torrent_added(SimpleNamespace(payload={"hash": "HL1", "dry_run": True}))
        assert client.limit_location_hashes_calls == []


def test_s5_make_ctx_pins_construction():
    """RuleContext 构造单点: manager/config/task/snapshot 直传(不得 None 顶替)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.client = FakeClient()
        rules = mgr.host.get("rules")
        from auto_qb.core.taskqueue import Task

        task = Task("rule", "t", hash="HM", store=mgr.store)
        snap = FakeTorrent(hash="HM")
        ctx = rules._make_ctx("HM", False, task=task, snapshot=snap)
        assert ctx.manager is mgr
        assert ctx.config is mgr.config, "config 缺失则条件/动作面崩"
        assert ctx.task is task, "task 缺失则断点不记"
        assert ctx.snapshot is snap
        assert ctx.hash == "HM"


def test_s5_tracker_match_single_no_warning():
    """单匹配不打「匹配到多个」告警"""
    with tempfile.TemporaryDirectory() as td:
        import io

        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.client = FakeClient()
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        lg = logging.getLogger("auto_qb.core.modules.tracker_mod")
        lg.addHandler(handler)
        try:
            conf = mgr.ctx.trackers.match(FakeTorrent(hash="H1"))
            assert conf is not None and conf.name == "HHan"
        finally:
            lg.removeHandler(handler)
        assert "多个" not in stream.getvalue()
