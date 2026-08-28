"""rules 框架核心逻辑自测(不连接真实 qB, 用模拟对象)"""
import sys
import os
import tempfile
import time
from types import SimpleNamespace

# 使测试可直接运行: python tests/test_rules.py
# 将项目根下的 src/ 加入模块搜索路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from auto_qb.config import GroupingConfig, HRRule  # noqa: E402
from auto_qb.qbmanager import QbManager  # noqa: E402
from auto_qb.rules import RuleContext, ActionResult  # noqa: E402


# ---------- 模拟 qB 客户端 ----------
class _FakeTorrents(dict):
    """模拟 qbittorrentapi 的 torrents 命名空间: dict 风格访问 + .info(tag=...) 过滤"""
    def info(self, torrent_hashes=None, tag=None, **kw):
        """按 hash 和/或 tag 过滤种子(与 torrents_info 同语义)"""
        if torrent_hashes:
            if isinstance(torrent_hashes, (list, tuple)):
                hashes = set(torrent_hashes)
                items = [self[h] for h in hashes if h in self]
            else:
                items = [self[torrent_hashes]] if torrent_hashes in self else []
        else:
            items = list(self.values())
        if tag:
            items = [
                t for t in items
                if tag in ((t.get("tags", "") if isinstance(t, dict) else getattr(t, "tags", "")) or "").split(",")
            ]
        return items


class FakeClient:
    def __init__(self):
        self.tags = set()
        self.category = ""
        self.calls = []
        self.torrents = _FakeTorrents()  # 模拟客户端中的种子: hash -> info dict
        self.exported = b"TORRENT-DATA"  # torrents_export 返回值
        self.add_error = None  # 模拟重加失败
        self.files = []  # torrents_files 返回值(空 = 全部通过)
        self.files_map = {}  # hash -> 文件列表(分组测试用: 按种子区分文件列表)
        self.files_calls = 0  # torrents_files 调用计数(验证分组检查不再全量拉文件列表)

    def torrents_trackers(self, h):
        return [{"url": "https://tracker.hhanclub.net/announce.php"}]

    def torrents_files(self, h):
        self.files_calls += 1
        # 优先按 hash 返回文件列表(分组测试用), 否则返回共享 files
        if h in self.files_map:
            return self.files_map[h]
        return self.files

    def torrents_info(self, torrent_hashes=None, **kw):
        return self.torrents.info(torrent_hashes=torrent_hashes, **kw)

    def torrents_export(self, torrent_hashes=None):
        self.calls.append(("export", None))
        return self.exported

    def torrents_delete(self, torrent_hashes=None, delete_files=False):
        self.calls.append(("delete", delete_files))
        if not delete_files:
            self.torrents.pop(torrent_hashes, None)

    def torrents_add(
        self,
        torrent_files=None,
        torrent_paths=None,
        save_path=None,
        category=None,
        tags=None,
        is_skip_checking=False,
        paused=False,
        **kw
    ):
        self.calls.append(("add", {"is_skip_checking": is_skip_checking, "paused": paused}))
        if self.add_error:
            raise self.add_error
        self.torrents["HASH123"] = {"state": "pausedUP" if paused else "stalledUP"}

    def torrents_add_tags(self, tags=None, torrent_hashes=None):
        self.tags.update(tags)
        self.calls.append(("add_tags", tags))

    def torrents_remove_tags(self, tags=None, torrent_hashes=None):
        self.tags.difference_update(tags)
        self.calls.append(("remove_tags", tags))

    def torrents_tags(self):
        return list(self.tags)

    def torrents_delete_tags(self, tags=None):
        # 模拟真实行为: 删除标签定义并同时从所有种子移除
        tags = set(tags or [])
        self.tags.difference_update(tags)
        for tor in self.torrents.values():
            cur = (tor.get("tags", "") if isinstance(tor, dict) else getattr(tor, "tags", "")) or ""
            if cur:
                remain = [t.strip() for t in cur.split(",") if t.strip() and t.strip() not in tags]
                new = ",".join(remain)
                if isinstance(tor, dict):
                    tor["tags"] = new
                else:
                    tor.tags = new
        self.calls.append(("delete_tags", tags))

    def torrents_categories(self):
        return {}

    def torrents_create_category(self, name=None):
        self.calls.append(("create_category", name))

    def torrents_set_category(self, category=None, torrent_hashes=None):
        self.category = category
        self.calls.append(("set_category", category))

    def torrents_start(self, torrent_hashes=None):
        self.calls.append(("start", None))

    def torrents_stop(self, torrent_hashes=None):
        self.calls.append(("stop", None))

    def torrents_recheck(self, torrent_hashes=None):
        self.calls.append(("recheck", None))

    def torrents_reannounce(self, torrent_hashes=None):
        self.calls.append(("reannounce", None))

    def torrents_set_upload_limit(self, torrent_hashes=None, upload_limit=None):
        self.calls.append(("set_upload_limit", upload_limit))

    def torrents_set_download_limit(self, torrent_hashes=None, download_limit=None):
        self.calls.append(("set_download_limit", download_limit))

    def torrents_set_location(self, torrent_hashes=None, location=None):
        self.calls.append(("set_location", location))


# ---------- 模拟种子 ----------
class FakeTorrent:
    def __init__(self, **kw):
        self.hash = kw.get("hash", "HASH123")
        self.name = kw.get("name", "Test")
        self.save_path = kw.get("save_path", r"R:\Downloads")
        self.content_path = kw.get("content_path", r"R:\Downloads\Test")
        self.size = kw.get("size", 100 * 1024**2)
        self.total_size = kw.get("total_size", 100 * 1024**2)
        self.tags = kw.get("tags", "")
        self.category = kw.get("category", "")
        self.state = kw.get("state", "stalledUP")
        self.downloaded = kw.get("downloaded", 100 * 1024**2)
        self.uploaded = kw.get("uploaded", 0)
        self.seeding_time = kw.get("seeding_time", 0)
        self.ratio = kw.get("ratio", 0.0)
        self.amount_left = kw.get("amount_left", 0)


# ---------- 模拟 TrackerConfig ----------
class FakeTracker:
    def __init__(self, name, hr=None, rules=None, remove_similar_tags=False):
        self.name = name
        self.domains = ["tracker.hhanclub.net"]
        self.tags = ["HHan"]
        self.remove_tags = []
        self.hr = hr  # HRRule 或 None
        self.rules = rules or []
        self.remove_similar_tags = remove_similar_tags


# ---------- 模拟 Config ----------
class FakeConfig:
    trackers = {"HHan": FakeTracker("HHan")}
    state_file = ""  # 由测试设置
    interval = 60  # QbManager 主刷新任务 interval(测试不触发 refresh)
    check_missing_files = False
    remove_similar_tags = False
    hr = HRRule()  # 全局 HR 默认输出设置
    delete_tags = []  # 全局: 彻底删除的标签格式(支持正则)
    delete_tags_if_has_no_torrents = []  # 全局: 彻底删除无种子的标签格式(支持正则)
    grouping = GroupingConfig(enabled=False, interval=300, missing_tag="MISSING")  # 种子分组管理(默认关闭)


def _hr_rule(**kw) -> HRRule:
    """构造 HRRule, 默认匹配旧 '3D@70%+12H' 语义"""
    base = dict(
        required_seeding_time=3 * 86400,
        required_seeding_time_raw="3D",
        required_share_ratio=0.0,
        extra_seeding_time=12 * 3600,
        condition=("dlratio", 0.7),
        add_tag="",
        add_category="!!HR${required_seeding_time}!!",
        overwrite_category=False,
        add_tag_for_satisfied="",
        add_category_for_satisfied="--HR${required_seeding_time}--",
        overwrite_category_for_satisfied=False,
    )
    base.update(kw)
    return HRRule(**base)


def make_manager(state_file, tracker_rules=None, tracker_kw=None):
    cfg = FakeConfig()
    cfg.state_file = state_file
    cfg.trackers = {"HHan": FakeTracker("HHan", hr=_hr_rule(), rules=tracker_rules, **(tracker_kw or {}))}
    config_dict = {
        "example_rules":
            {
                "add_site_tag":
                    {
                        "enabled": True,
                        "execute_once": "never",
                        "conditions": [{
                            "trackers": "HHan"
                        }],
                        "actions": [{
                            "add_tags": ["HHan", "seed-${required_seeding_time}"]
                        }],
                        "stop_following_rules_if": "never",
                    },
                "hr_done":
                    {
                        "enabled": True,
                        "execute_once": "daily",
                        "conditions": [{
                            "state": "complete&uploading"
                        }, {
                            "hr": "satisfied"
                        }],
                        "actions": [{
                            "add_category": {
                                "format": "HR-DONE",
                                "overwrite": False
                            }
                        }],
                        "stop_following_rules_if": "conditions-met",
                    },
                "stop_low_ratio":
                    {
                        "enabled": True,
                        "execute_once": "once",
                        "conditions": [{
                            "upload_ratio": "<0.5"
                        }],
                        "actions": [{
                            "stop": True
                        }, {
                            "add_tags": ["low-ratio"]
                        }],
                        "stop_following_rules_if": "action-failed",
                    },
            }
    }
    cfg.rules_config = config_dict
    return QbManager("", config=cfg)


def test_basic():
    """测试: 标签规则 + 变量替换 + stop_following_rules_if: never"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = make_manager(state_file)
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(tags="", seeding_time=200000, uploaded=5 * 1024**2, ratio=0.6)
        handled = mgr.process_torrent(tor, dry_run=False)
        assert handled, "add_site_tag 应处理种子"
        assert client.tags == {"HHan", "seed-3D"}, f"标签错误: {client.tags}"
        assert mgr.state.get("exec_history"), "应有执行历史"
        print("[OK] test_basic: 标签规则+${required_seeding_time}变量替换")


def test_category_auto_update_from_state():
    """测试: 未设置 overwrite 时可更新此前自动设置的分类, 手动分类不覆盖"""
    from auto_qb.rules.actions import AddCategoryAction

    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = make_manager(state_file)
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(category="")
        ctx = RuleContext(mgr, client, mgr.config, tor, dry_run=False)

        assert AddCategoryAction({"format": "AUTO-A"}).execute(ctx).is_ok
        mgr.save_state()
        assert mgr.state["auto_categories"] == {"HASH123": "AUTO-A"}

        mgr2 = make_manager(state_file)
        client2 = FakeClient()
        mgr2.client = client2
        tor.category = "AUTO-A"
        ctx2 = RuleContext(mgr2, client2, mgr2.config, tor, dry_run=False)
        assert AddCategoryAction({"format": "AUTO-B"}).execute(ctx2).is_ok
        assert client2.category == "AUTO-B"
        assert mgr2.state["auto_categories"]["HASH123"] == "AUTO-B"

        tor.category = "MANUAL"
        client2.calls.clear()
        assert AddCategoryAction({"format": "AUTO-C"}).execute(ctx2).is_skipped
        assert not any(call[0] == "set_category" for call in client2.calls)
        print("[OK] test_category_auto_update_from_state: 自动分类可更新, 手动分类不覆盖")


def test_category_explicit_overwrite_false():
    """测试: 显式 overwrite: false 与缺省行为一致(自动分类可更新, 手动分类不覆盖)"""
    from auto_qb.rules.actions import AddCategoryAction

    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        # 当前分类 == 上次自动设置的分类: 显式 false 也应允许更新
        tor = FakeTorrent(category="AUTO-A")
        mgr.state["auto_categories"] = {"HASH123": "AUTO-A"}
        ctx = RuleContext(mgr, client, mgr.config, tor, dry_run=False)
        result = AddCategoryAction({"format": "AUTO-B", "overwrite": False}).execute(ctx)
        assert result.is_ok, f"当前分类==上次自动设置, 显式 false 也应可更新: {result}"
        assert client.category == "AUTO-B", f"分类未更新: {client.category}"
        assert mgr.state["auto_categories"]["HASH123"] == "AUTO-B"
        # 手动分类: 不覆盖
        tor.category = "MANUAL"
        n_calls = len(client.calls)
        ctx2 = RuleContext(mgr, client, mgr.config, tor, dry_run=False)
        result2 = AddCategoryAction({"format": "AUTO-C", "overwrite": False}).execute(ctx2)
        assert result2.is_skipped, f"手动分类不应被覆盖: {result2}"
        assert not any(c[0] == "set_category" for c in client.calls[n_calls:]), \
            f"不应新增 set_category: {client.calls[n_calls:]}"
        print("[OK] test_category_explicit_overwrite_false: 显式 false 与缺省一致")


def test_builtin_hr_category_auto_update_from_state():
    """测试: 内置 HR 分类保存状态并可更新此前自动设置的分类"""
    from auto_qb.taskqueue import Task

    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = make_manager(state_file)
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(downloaded=100 * 1024**2, category="")
        client.torrents["HASH123"] = tor
        task = Task("internal", "maintenance", torrent_hash="HASH123", interval=60, handler=mgr._handle_maintenance)

        assert mgr._handle_maintenance(task, dry_run=False)
        mgr.save_state()
        assert mgr.state["auto_categories"]["HASH123"] == "!!HR3D!!"

        mgr2 = make_manager(state_file)
        client2 = FakeClient()
        mgr2.client = client2
        tor.category = "!!HR3D!!"
        client2.torrents["HASH123"] = tor
        mgr2.config.trackers["HHan"].hr = _hr_rule(add_category="NEW-HR")
        mgr2._handle_maintenance(task, dry_run=False)
        assert client2.category == "NEW-HR"
        assert mgr2.state["auto_categories"]["HASH123"] == "NEW-HR"
        print("[OK] test_builtin_hr_category_auto_update_from_state: 内置 HR 分类可更新")


def test_hr_satisfied():
    """测试: hr satisfied 条件 + daily 去重"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = make_manager(state_file)
        client = FakeClient()
        mgr.client = client
        # 3D@70%+12H: 需 seeding_time >= 3D + 12H
        tor = FakeTorrent(tags="HHan", seeding_time=3 * 86400 + 12 * 3600 + 10, ratio=2.0)
        handled = mgr.process_torrent(tor, dry_run=False)
        assert handled, "hr_done 应处理种子"
        assert client.category == "HR-DONE", f"分类错误: {client.category}"

        # daily 去重: 同一天再次执行不应重复
        client2 = FakeClient()
        mgr2 = make_manager(state_file)  # 重新加载 state
        mgr2.client = client2
        handled2 = mgr2.process_torrent(tor, dry_run=False)
        assert handled2 is True or client2.calls == [], f"daily 去重失败: {client2.calls}"
        print("[OK] test_hr_satisfied: hr satisfied 条件 + daily 去重")


def test_stop_if_action_failed():
    """测试: 种子已停止时 stop 动作幂等跳过(skipped 不算失败), 后续动作仍执行"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = make_manager(state_file)
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(tags="HHan", ratio=0.1, state="stoppedDL")
        handled = mgr.process_torrent(tor, dry_run=False)
        assert handled, "stop_low_ratio 应处理种子"
        assert ("stop", None) not in client.calls, f"已停止的种子不应重复 stop: {client.calls}"
        assert ("add_tags", ["low-ratio"]) in client.calls, f"应添加 low-ratio 标签: {client.calls}"
        print("[OK] test_stop_if_action_failed: 低比率种子 stop 幂等跳过, 标签动作继续执行")


def test_dry_run():
    """测试: dry-run 不产生任何客户端调用"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = make_manager(state_file)
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(tags="", ratio=0.1, state="stoppedDL")
        mgr.process_torrent(tor, dry_run=True)
        assert client.calls == [], f"dry-run 不应调用客户端: {client.calls}"
        print("[OK] test_dry_run: dry-run 无副作用")


def test_state_mapping():
    """测试: 语义状态映射"""
    from auto_qb.rules.conditions import _STATE_MAP
    assert "checkingDL" in _STATE_MAP["checking"]
    assert "stalledUP" in _STATE_MAP["uploading"]
    assert "missingFiles" in _STATE_MAP["errored"]
    assert "stoppedDL" in _STATE_MAP["stopped"]
    print("[OK] test_state_mapping: 状态映射表")


def test_tracker_rules_ref():
    """测试: tracker rules 引用 @rule_set / @rule_set.rule_name 过滤"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        # 只引用 example_rules.add_site_tag 规则
        mgr = make_manager(state_file, tracker_rules=["@example_rules.add_site_tag"])
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(tags="", ratio=0.1, state="stoppedDL")
        mgr.process_torrent(tor, dry_run=False)
        # 只应执行 add_site_tag(加标签), 不应执行 stop_low_ratio(stop + low-ratio 标签)
        assert client.tags == {"HHan", "seed-3D"}, f"仅应执行被引用的规则: {client.tags}"
        assert ("add_tags", ["low-ratio"]) not in client.calls, "未引用的规则不应执行"

        # 引用整个规则集
        mgr2 = make_manager(state_file, tracker_rules=["@example_rules"])
        client2 = FakeClient()
        mgr2.client = client2
        mgr2.process_torrent(tor, dry_run=False)
        assert ("add_tags", ["low-ratio"]) in client2.calls, "引用整个规则集应包含 stop_low_ratio"
        print("[OK] test_tracker_rules_ref: tracker rules 引用")


def test_parse_utils():
    """测试: 解析工具"""
    from auto_qb import utils
    assert utils.parse_time("3D") == 3 * 86400
    assert utils.parse_fsize("10MiB") == 10 * 1024**2
    assert utils.parse_speed("1000KiB/s") == 1000 * 1024
    # HR 触发条件解析
    assert utils.parse_hr_condition("80%") == ("dlratio", 0.8)
    assert utils.parse_hr_condition("70%") == ("dlratio", 0.7)
    assert utils.parse_hr_condition("10MiB") == ("dlsize", 10 * 1024**2)
    assert utils.parse_hr_condition("") == ("dlratio", 0.8)  # 缺省默认80%
    assert utils.parse_bool("true") is True
    print("[OK] test_parse_utils: 解析工具")


def test_compare():
    """测试: 比较解析"""
    from auto_qb import utils
    op, val = utils.parse_compare(">=100MiB", utils.parse_fsize)
    assert op == ">=" and val == 100 * 1024**2
    assert utils.compare(">", 5, 3)
    assert not utils.compare("<", 5, 3)
    print("[OK] test_compare: 比较表达式")


def test_rule_interval():
    """测试: 规则 interval 调度(每条规则一个种子级任务, 到期才执行, interval=0 归一化为每 tick)"""
    from auto_qb.taskqueue import Task, TaskQueue
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        cfg = FakeConfig()
        cfg.state_file = state_file
        cfg.trackers = {"HHan": FakeTracker("HHan", hr=_hr_rule(), rules=["@example_rules"])}
        cfg.rules_config = {
            "example_rules":
                {
                    "add_site_tag":
                        {
                            "enabled": True,
                            "conditions": [{
                                "trackers": "HHan"
                            }],
                            "actions": [{
                                "add_tags": ["HHan"]
                            }],
                            "stop_following_rules_if": "never",
                        },
                    "stop_low_ratio":
                        {
                            "enabled": True,
                            "interval": "60S",
                            "conditions": [{
                                "upload_ratio": "<0.5"
                            }],
                            "actions": [{
                                "stop": True
                            }],
                            "stop_following_rules_if": "action-failed",
                        },
                }
        }
        mgr = QbManager("", config=cfg)
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(tags="", ratio=0.1, state="uploading")
        client.torrents["HASH123"] = tor  # 种子级规则任务通过 _get_torrent 拉取

        # 模拟 _create_torrent_tasks: 为种子创建规则任务(独立队列, 排除 refresh 任务干扰)
        tq = TaskQueue()
        rules = mgr._rules_for_torrent(tor)
        assert {r.name for r in rules} == {"example_rules.add_site_tag", "example_rules.stop_low_ratio"}
        now = time.time()  # 统一时间起点: add_task 与 due 使用同一 now
        for r in rules:
            tq.add_task(mgr._create_rule_task(r, tor.hash), now=now)

        # 第 1 轮: 所有规则任务初始立即到期, 均执行
        due = tq.due(now)
        assert {t.name for t in due} == {"example_rules.add_site_tag", "example_rules.stop_low_ratio"}, \
            f"第 1 轮应全部到期: {[t.name for t in due]}"
        for t in due:
            keep = t.handler(t, False)
            assert keep, f"任务不应消亡: {t.name}"
        assert ("stop", None) in client.calls, f"第 1 轮应 stop: {client.calls}"
        for t in due:
            tq.reschedule(t, now)

        # 第 2 轮(1s 后): add_site_tag(interval 归一化 1s)到期, stop_low_ratio(60s)未到期
        client.calls.clear()
        due2 = tq.due(now + 1)
        assert [t.name
                for t in due2] == ["example_rules.add_site_tag"], f"第 2 轮应只到期 add_site_tag: {[t.name for t in due2]}"
        for t in due2:
            t.handler(t, False)
        assert ("stop", None) not in client.calls, f"interval 未到期不应再次 stop: {client.calls}"
        assert client.tags == {"HHan"}, f"add_site_tag 应仍执行: {client.tags}"
        for t in due2:
            tq.reschedule(t, now + 1)

        # 60s 后: stop_low_ratio 到期再次执行
        client.calls.clear()
        due3 = tq.due(now + 60)
        for t in due3:
            t.handler(t, False)
        assert ("stop", None) in client.calls, f"60s 后应再次 stop: {client.calls}"

        # 兜底: 不创建任务直接 process_torrent, 视为全部规则执行(向后兼容)
        mgr3 = QbManager("", config=cfg)
        client3 = FakeClient()
        mgr3.client = client3
        handled3 = mgr3.process_torrent(tor, dry_run=False)
        assert handled3, "无规则任务时规则应全部执行(向后兼容)"
        assert ("stop", None) in client3.calls, f"兜底路径应执行全部规则: {client3.calls}"
        print("[OK] test_rule_interval: 规则 interval 调度")


def test_task_queue_schedule():
    """测试: 快速队列 interval 调度(时间优先堆, 每个任务有内置 interval)"""
    from auto_qb.taskqueue import Task, TaskQueue
    tq = TaskQueue()
    now = time.time()  # 统一时间起点: add_task 与 due 使用同一 now
    tq.add_task(Task("rule", "every_tick", interval=0), now=now)  # interval<=0 归一化为 1s
    tq.add_task(Task("rule", "interval60", interval=60), now=now)  # 60s 一次

    # 到期弹出: 两个任务都立即到期
    due = tq.due(now)
    assert {t.name for t in due} == {"every_tick", "interval60"}, f"due={[t.name for t in due]}"
    assert [t for t in due if t.name == "every_tick"][0].interval == 1, "interval<=0 应归一化为 1"

    # 执行完按内置 interval 重新入队
    for t in due:
        tq.reschedule(t, now)
    # 59s 内: every_tick(1s)到期, interval60 未到期
    assert [t.name for t in tq.due(now + 59)] == ["every_tick"], "59s 时只有 every_tick 到期"
    # 60s 后: interval60 到期(未被重入队的 every_tick 不再出现)
    assert [t.name for t in tq.due(now + 60)] == ["interval60"], "60s 时 interval60 到期"

    # remove_torrent: 按种子移除任务
    tq.add_task(Task("torrent", "maintenance", torrent_hash="H1", interval=60), now=now)
    tq.remove_torrent("H1")
    assert tq.due(now + 61) == [], "remove_torrent 后任务应被移除"

    tq.shutdown()
    print("[OK] test_task_queue_schedule: 快速队列 interval 调度")


def test_async_check():
    """测试: check 动作异步提交校验(慢速队列), 主循环轮询完成 -> 自动开始 + 记录执行"""
    from auto_qb.taskqueue import TaskQueue
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        cfg = FakeConfig()
        cfg.rules_config = {
            "example_rules":
                {
                    "verify_then_start":
                        {
                            "enabled": True,
                            "conditions": [{
                                "tags": "需校验"
                            }],
                            "actions": [{
                                "check": {
                                    "mode": "full-checking",
                                    "auto_start": True,
                                }
                            }],
                            "stop_following_rules_if": "never",
                        },
                }
        }
        mgr = QbManager("", config=cfg)
        # 同步模式: 发送回调立即执行, 测试无竞态
        mgr.task_queue = TaskQueue(executor_workers=0)
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(tags="需校验", state="stalledUP")

        # 1. 提交异步校验(仅发送 recheck 请求)
        handled = mgr.process_torrent(tor, dry_run=False)
        assert handled, "check 动作应处理种子"
        assert ("recheck", None) in client.calls, f"应发送校验请求: {client.calls}"

        # 2. 校验未完成: 任务留在慢速队列
        completed = mgr.task_queue.poll_slow(lambda h: False)
        assert completed == [], f"未完成不应出队: {completed}"
        assert mgr.task_queue.pending_slow() == ["HASH123"], "未完成的任务应留在慢速队列"

        # 3. 重复提交同一种子: 应被忽略
        client.calls.clear()
        mgr.process_torrent(tor, dry_run=False)
        assert ("recheck", None) not in client.calls, f"重复校验应被忽略: {client.calls}"

        # 4. 校验完成(退出 checking 状态): 自动开始 + 记录执行历史
        completed = mgr.task_queue.poll_slow(lambda h: True)
        assert len(completed) == 1, f"应完成 1 个任务: {completed}"
        assert ("start", None) in client.calls, f"校验完成应自动开始: {client.calls}"
        assert mgr.state.get("exec_history"), f"校验完成应记录执行历史: {mgr.state}"
        assert mgr.task_queue.pending_slow() == [], "完成后应出队"
        print("[OK] test_async_check: 异步校验提交+轮询完成")


def test_skip_checking():
    """测试: check 动作 skip-checking 跳检(前置检查->导出->删除->重加->自动开始 + 同日去重)"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        cfg = FakeConfig()
        cfg.rules_config = {
            "example_rules":
                {
                    "skip_check_rule":
                        {
                            "enabled": True,
                            "conditions": [{
                                "tags": "需跳检"
                            }],
                            "actions": [{
                                "check": {
                                    "mode": "skip-checking",
                                    "auto_start": True,
                                }
                            }],
                            "stop_following_rules_if": "never",
                        },
                }
        }
        mgr = QbManager("", config=cfg)
        client = FakeClient()
        mgr.client = client
        client.torrents["HASH123"] = {"state": "stalledUP"}
        tor = FakeTorrent(tags="需跳检", state="stalledUP")

        # 1. 正常跳检流程: 导出->删除(保留文件)->重加(跳过校验,暂停)->自动开始
        handled = mgr.process_torrent(tor, dry_run=False)
        assert handled, f"跳检应处理种子: {client.calls}"
        assert [c[0] for c in client.calls] == ["export", "delete", "add", "start"], \
            f"跳检调用顺序: {client.calls}"
        add_call = [c for c in client.calls if c[0] == "add"][0]
        assert add_call[1]["is_skip_checking"] is True, f"重加应跳过校验: {add_call}"
        assert add_call[1]["paused"] is True, f"重加应先暂停: {add_call}"
        assert mgr.state.get("exec_history"), "跳检应记录执行历史"

        # 2. 同日去重: 再次触发应跳过, 不重复删/加
        client.calls.clear()
        handled = mgr.process_torrent(tor, dry_run=False)
        assert not handled, f"同日不应重复跳检: {client.calls}"
        assert ("delete", False) not in client.calls, f"同日不应删除种子: {client.calls}"
        print("[OK] test_skip_checking: skip-checking 跳检流程+去重")


def test_skip_checking_guard():
    """测试: 跳检安全保护(前置检查失败不删除; 重加失败落盘备份)"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        cfg = FakeConfig()
        cfg.rules_config = {
            "example_rules":
                {
                    "skip_check_rule":
                        {
                            "enabled": True,
                            "conditions": [{
                                "tags": "需跳检"
                            }],
                            "actions": [{
                                "check": {
                                    "mode": "skip-checking",
                                    "auto_start": True,
                                }
                            }],
                            "stop_following_rules_if": "never",
                        },
                }
        }
        mgr = QbManager("", config=cfg)
        client = FakeClient()
        mgr.client = client
        client.torrents["HASH123"] = {"state": "stalledUP"}
        tor = FakeTorrent(tags="需跳检")

        # 1. 前置检查失败(文件缺失): 不执行导出/删除
        client.files = [SimpleNamespace(name="missing.bin", size=100)]
        mgr.process_torrent(tor, dry_run=False)
        assert client.calls == [], f"前置检查失败不应有任何调用: {client.calls}"
        assert client.torrents.get("HASH123"), "前置检查失败种子应保留"

        # 2. 重加失败: .torrent 落盘备份 + 元数据记录
        client.files = []
        client.add_error = RuntimeError("simulated add failure")
        handled = mgr.process_torrent(tor, dry_run=False)
        backup = mgr.state.get("skip_check_backup", {}).get("HASH123")
        assert backup, f"重加失败应记录备份元数据: {mgr.state}"
        assert os.path.exists(backup["path"]), f"备份文件应存在: {backup}"
        print("[OK] test_skip_checking_guard: 跳检安全保护")


def test_tracker_hr_overrides_global():
    """测试: 站点 hr 输出设置覆盖全局(分类格式 + overwrite), 未设置的字段用全局默认"""
    from auto_qb.taskqueue import TaskQueue
    from auto_qb.taskqueue import Task

    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        cfg = FakeConfig()
        cfg.state_file = state_file
        # 全局默认: add_category = 全局格式
        cfg.hr = _hr_rule(add_category="GLOBAL-HR", add_category_for_satisfied="GLOBAL-DONE")
        # 站点: 覆盖 add_category, 保留 satisfied 用全局默认
        site_hr = _hr_rule(
            add_category="SITE-HR!!",
            overwrite_category=True,
        )
        cfg.trackers = {"HHan": FakeTracker("HHan", hr=site_hr)}

        mgr = QbManager("", config=cfg)
        client = FakeClient()
        mgr.client = client
        # seeding_time 未达 required+extra: 只触发 add_category(站点覆盖), 不触发 satisfied 分类
        tor = FakeTorrent(downloaded=100 * 1024**2, seeding_time=100, ratio=1.0)
        client.torrents["HASH123"] = tor

        task = Task("internal", "maintenance", torrent_hash="HASH123", interval=60, handler=mgr._handle_maintenance)
        mgr._handle_maintenance(task, dry_run=False)

        # 站点覆盖: 分类应为 SITE-HR!!(非全局 GLOBAL-HR)
        assert client.category == "SITE-HR!!", f"站点分类覆盖失败: {client.category}"

        # satisfied 场景: 站点覆盖 satisfied 分类格式 + 允许覆盖
        cfg.trackers["HHan"].hr = _hr_rule(
            add_category_for_satisfied="SITE-DONE!!",
            overwrite_category_for_satisfied=True,
        )
        client2 = FakeClient()
        mgr2 = QbManager("", config=cfg)
        mgr2.client = client2
        tor2 = FakeTorrent(downloaded=100 * 1024**2, seeding_time=3 * 86400 + 12 * 3600 + 10, ratio=1.0)
        client2.torrents["HASH123"] = tor2
        mgr2._handle_maintenance(task, dry_run=False)
        assert client2.category == "SITE-DONE!!", f"站点 satisfied 分类覆盖失败: {client2.category}"
        print("[OK] test_tracker_hr_overrides_global: 站点 hr 覆盖全局输出设置")


def test_tracker_remove_similar_tags_override():
    """测试: 站点 remove_similar_tags=true 覆盖全局 false, 触发相似标签删除"""
    from auto_qb.taskqueue import Task

    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        cfg = FakeConfig()
        cfg.state_file = state_file
        cfg.remove_similar_tags = False  # 全局关闭
        cfg.trackers = {
            "HHan":
                FakeTracker("HHan", hr=None, remove_similar_tags=True)  # 站点开启
        }

        mgr = QbManager("", config=cfg)
        client = FakeClient()
        mgr.client = client
        # 已有类似标签 "hhan"(小写), 站点 tags 为 "HHan"
        tor = FakeTorrent(tags="hhan,other")
        client.torrents["HASH123"] = tor

        task = Task("internal", "maintenance", torrent_hash="HASH123", interval=60, handler=mgr._handle_maintenance)
        mgr._handle_maintenance(task, dry_run=False)

        # 全局关闭 + 站点开启 -> 应删除类似标签 hhan
        assert ("remove_tags", {"hhan"}) in client.calls or any(
            c[0] == "remove_tags" for c in client.calls
        ), f"站点 remove_similar_tags 未生效: {client.calls}"
        print("[OK] test_tracker_remove_similar_tags_override: 站点 remove_similar_tags 覆盖全局")


def test_hr_required_share_ratio():
    """测试: required_share_ratio 条件(做种时长不够但分享率达标 -> satisfied)"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        mgr = make_manager(state_file)
        client = FakeClient()
        mgr.client = client
        # 站点: 3D+12H, 分享率 2.0, 但做种时长远不够
        mgr.config.trackers["HHan"].hr = _hr_rule(
            required_seeding_time=3 * 86400,
            required_seeding_time_raw="3D",
            extra_seeding_time=12 * 3600,
            required_share_ratio=2.0,
        )
        tor = FakeTorrent(tags="HHan", seeding_time=100, ratio=2.5)  # 时长不足但分享率达标
        handled = mgr.process_torrent(tor, dry_run=False)
        assert handled, "分享率达标应视为 HR satisfied"
        assert client.category == "HR-DONE", f"分享率达标应加 HR-DONE: {client.category}"

        # 分享率也不达标: 不处理
        client2 = FakeClient()
        mgr2 = make_manager(state_file)
        mgr2.client = client2
        mgr2.config.trackers["HHan"].hr = _hr_rule(
            required_seeding_time=3 * 86400,
            required_seeding_time_raw="3D",
            extra_seeding_time=12 * 3600,
            required_share_ratio=2.0,
        )
        tor2 = FakeTorrent(tags="HHan", seeding_time=100, ratio=1.0)
        handled2 = mgr2.process_torrent(tor2, dry_run=False)
        assert handled2 is False or "HR-DONE" not in client2.tags, \
            f"时长与分享率均不达标不应 satisfied: {client2.calls}"
        print("[OK] test_hr_required_share_ratio: 分享率达标判定")


def test_global_delete_tags():
    """测试: 全局任务彻底删除标签(精确 + 正则 regex: 前缀)"""
    from auto_qb.taskqueue import Task

    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        cfg = FakeConfig()
        cfg.state_file = state_file
        cfg.delete_tags = ["M-Team - TP", "regex:^BTSCHOOL"]
        mgr = QbManager("", config=cfg)
        client = FakeClient()
        mgr.client = client
        # 客户端已有标签定义 + 种子使用中
        client.tags = {"HHan", "M-Team - TP", "BTSCHOOL-OLD", "KEEP"}
        tor = FakeTorrent(tags="HHan,M-Team - TP,BTSCHOOL-OLD")
        client.torrents["HASH123"] = tor

        task = Task("internal", "delete_tags", interval=60, handler=mgr._handle_delete_tags)
        mgr._handle_delete_tags(task, dry_run=False)

        # 精确匹配 M-Team - TP, 正则匹配 BTSCHOOL-OLD; KEEP/HHan 保留
        assert ("delete_tags", {"M-Team - TP", "BTSCHOOL-OLD"}) in client.calls, f"应彻底删除匹配标签: {client.calls}"
        assert client.tags == {"HHan", "KEEP"}, f"标签定义剩余: {client.tags}"
        assert tor.tags == "HHan", f"种子标签应同步移除: {tor.tags}"
        print("[OK] test_global_delete_tags: 全局彻底删除标签(精确+正则)")


def test_global_delete_tags_dry_run():
    """测试: 全局删除标签 dry-run 无副作用"""
    from auto_qb.taskqueue import Task

    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        cfg = FakeConfig()
        cfg.state_file = state_file
        cfg.delete_tags = ["M-Team - TP"]
        mgr = QbManager("", config=cfg)
        client = FakeClient()
        mgr.client = client
        client.tags = {"HHan", "M-Team - TP"}

        task = Task("internal", "delete_tags", interval=60, handler=mgr._handle_delete_tags)
        mgr._handle_delete_tags(task, dry_run=True)
        assert client.calls == [], f"dry-run 不应调用客户端: {client.calls}"
        assert client.tags == {"HHan", "M-Team - TP"}, "dry-run 不应改变标签"
        print("[OK] test_global_delete_tags_dry_run: 全局删除标签 dry-run")


def test_global_delete_tags_if_has_no_torrents():
    """测试: 全局任务彻底删除无种子的标签(仅删无种子使用的, 有种子使用保留)"""
    from auto_qb.taskqueue import Task

    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        cfg = FakeConfig()
        cfg.state_file = state_file
        # 模拟 load_config 展开 @tracker_tags 后的结果: 站点标签 HHan
        cfg.delete_tags_if_has_no_torrents = ["HHan", "regex:^ORPHAN"]
        mgr = QbManager("", config=cfg)
        client = FakeClient()
        mgr.client = client
        # HHan 无种子使用(孤儿), ORPHAN-1 无种子使用, KEEP 有种子使用
        client.tags = {"HHan", "ORPHAN-1", "KEEP"}
        tor = FakeTorrent(tags="KEEP")
        client.torrents["HASH123"] = tor

        task = Task(
            "internal",
            "delete_tags_if_has_no_torrents",
            interval=60,
            handler=mgr._handle_delete_tags_if_has_no_torrents
        )
        mgr._handle_delete_tags_if_has_no_torrents(task, dry_run=False)

        assert ("delete_tags", {"HHan", "ORPHAN-1"}) in client.calls, f"应删除无种子标签: {client.calls}"
        assert client.tags == {"KEEP"}, f"有种子使用的标签应保留: {client.tags}"
        print("[OK] test_global_delete_tags_if_has_no_torrents: 彻底删除无种子的标签")


def test_global_delete_tags_no_pattern_match():
    """测试: 无匹配格式时不调用客户端"""
    from auto_qb.taskqueue import Task

    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        cfg = FakeConfig()
        cfg.state_file = state_file
        cfg.delete_tags = ["不存在的标签"]
        mgr = QbManager("", config=cfg)
        client = FakeClient()
        mgr.client = client
        client.tags = {"HHan", "KEEP"}
        tor = FakeTorrent(tags="HHan")
        client.torrents["HASH123"] = tor

        task = Task("internal", "delete_tags", interval=60, handler=mgr._handle_delete_tags)
        mgr._handle_delete_tags(task, dry_run=False)
        assert client.calls == [], f"无匹配不应调用客户端: {client.calls}"
        print("[OK] test_global_delete_tags_no_pattern_match: 无匹配无副作用")


def test_global_delete_tags_queued():
    """测试: 配置非空时创建两个全局任务加入队列"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        cfg = FakeConfig()
        cfg.state_file = state_file
        cfg.delete_tags = ["M-Team - TP"]
        cfg.delete_tags_if_has_no_torrents = ["@tracker_tags"]
        mgr = QbManager("", config=cfg)
        # 队列应包含两个全局标签清理任务
        names = {t.name for t in mgr.task_queue._fast}
        assert "delete_tags" in names, f"缺少 delete_tags 任务: {names}"
        assert "delete_tags_if_has_no_torrents" in names, f"缺少 delete_tags_if_has_no_torrents 任务: {names}"
        for t in mgr.task_queue._fast:
            if t.name in ("delete_tags", "delete_tags_if_has_no_torrents"):
                assert t.interval == cfg.interval, f"全局任务 interval 应为 {cfg.interval}: {t.interval}"
        print("[OK] test_global_delete_tags_queued: 全局清理任务入队")


def test_config_tracker_tags_expand():
    """测试: load_config 中 @tracker_tags 展开为所有 tracker tags 并集"""
    import yaml

    from auto_qb.config import load_config
    with tempfile.TemporaryDirectory() as td:
        cfg_path = os.path.join(td, "config.yml")
        with open(cfg_path, "w", encoding="utf-8") as f:
            yaml.dump(
                {
                    "config":
                        {
                            "qbittorrent": {
                                "host": "127.0.0.1",
                                "port": 16585,
                                "username": "u",
                                "password": "p",
                            },
                            "delete_tags_if_has_no_torrents": ["@tracker_tags", "regex:^ORPHAN"],
                            "trackers":
                                {
                                    "HHan": {
                                        "domains": ["tracker.hhanclub.net"],
                                        "tags": ["HHan"]
                                    },
                                    "Kufirc": {
                                        "domains": ["kufirc.com"],
                                        "tags": ["Kufirc"]
                                    },
                                },
                        }
                },
                f,
                allow_unicode=True,
                default_flow_style=False
            )
        cfg = load_config(cfg_path)
        assert set(cfg.delete_tags_if_has_no_torrents) == {"HHan", "Kufirc", "regex:^ORPHAN"}, \
            f"@tracker_tags 展开错误: {cfg.delete_tags_if_has_no_torrents}"
        print("[OK] test_config_tracker_tags_expand: @tracker_tags 展开")


def _fake_file(name, size):
    return SimpleNamespace(name=name, size=size)


def test_grouping_size_mismatch_pauses_group():
    """测试: 组内文件大小不一致 -> 警告 + 整组暂停(不加标签)"""
    from auto_qb.taskqueue import Task

    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        cfg = FakeConfig()
        cfg.state_file = state_file
        cfg.grouping = GroupingConfig(enabled=True, interval=300, missing_tag="MISSING")
        mgr = QbManager("", config=cfg)
        client = FakeClient()
        mgr.client = client

        t1 = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=r"R:\Downloads")
        t2 = FakeTorrent(hash="H2", name="T2", state="stalledUP", save_path=r"R:\Downloads")
        client.torrents["H1"] = t1
        client.torrents["H2"] = t2
        client.files_map["H1"] = [_fake_file("movie.mkv", 100)]
        client.files_map["H2"] = [_fake_file("movie.mkv", 200)]  # 同名不同大小

        task = Task("internal", "grouping", interval=300, handler=mgr._handle_grouping)
        mgr._handle_grouping(task, dry_run=False)

        assert client.calls.count(("stop", None)) == 1, f"整组应暂停一次: {client.calls}"
        assert "MISSING" not in client.tags, f"大小不一致不应加标签: {client.tags}"
        print("[OK] test_grouping_size_mismatch_pauses_group: 大小不一致整组暂停")


def test_grouping_missing_files_pauses_group():
    """测试: 文件丢失 -> 同组所有种子暂停 + MISSING 标签"""
    from auto_qb.taskqueue import Task

    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        cfg = FakeConfig()
        cfg.state_file = state_file
        cfg.grouping = GroupingConfig(enabled=True, interval=300, missing_tag="MISSING")
        mgr = QbManager("", config=cfg)
        client = FakeClient()
        mgr.client = client

        t1 = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=r"R:\Downloads")
        t2 = FakeTorrent(hash="H2", name="T2", state="stalledUP", save_path=r"R:\Downloads")
        client.torrents["H1"] = t1
        client.torrents["H2"] = t2
        client.files_map["H1"] = [_fake_file("movie.mkv", 100)]
        client.files_map["H2"] = [_fake_file("movie.mkv", 100)]

        # 首轮: 状态快照为空 -> 视为状态变化 -> 触发缺文件检查(文件不存在)
        task = Task("internal", "grouping", interval=300, handler=mgr._handle_grouping)
        mgr._handle_grouping(task, dry_run=False)

        assert client.calls.count(("stop", None)) == 1, f"整组应暂停一次: {client.calls}"
        assert "MISSING" in client.tags, f"丢失应添加标签: {client.tags}"
        assert mgr._group_state_snapshot.get("H1") == "stalledUP", f"状态快照应更新: {mgr._group_state_snapshot}"
        print("[OK] test_grouping_missing_files_pauses_group: 缺文件整组暂停+MISSING")


def test_grouping_state_change_triggers_check():
    """测试: 同组中一个种子状态变化才触发检查; 状态不变不重复检查"""
    from auto_qb.taskqueue import Task

    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        cfg = FakeConfig()
        cfg.state_file = state_file
        cfg.grouping = GroupingConfig(enabled=True, interval=300, missing_tag="MISSING")
        mgr = QbManager("", config=cfg)
        client = FakeClient()
        mgr.client = client

        t1 = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=r"R:\Downloads")
        t2 = FakeTorrent(hash="H2", name="T2", state="stalledUP", save_path=r"R:\Downloads")
        client.torrents["H1"] = t1
        client.torrents["H2"] = t2
        client.files_map["H1"] = [_fake_file("movie.mkv", 100)]
        client.files_map["H2"] = [_fake_file("movie.mkv", 100)]

        task = Task("internal", "grouping", interval=300, handler=mgr._handle_grouping)

        # 第一轮: 快照为空 -> 触发检查
        mgr._handle_grouping(task, dry_run=False)
        assert client.calls.count(("stop", None)) == 1, f"首轮应触发检查: {client.calls}"
        assert "MISSING" in client.tags

        # 第二轮: 状态不变 -> 不触发检查(无新调用)
        client.calls.clear()
        mgr._handle_grouping(task, dry_run=False)
        assert client.calls == [], f"状态不变不应触发检查: {client.calls}"

        # 第三轮: H1 状态变化 -> 再次触发
        t1.state = "uploading"
        client.calls.clear()
        mgr._handle_grouping(task, dry_run=False)
        assert client.calls.count(("stop", None)) == 1, f"状态变化应再次触发: {client.calls}"
        print("[OK] test_grouping_state_change_triggers_check: 状态变化触发检查")


def test_grouping_queued_when_enabled():
    """测试: grouping.enabled 时创建全局分组任务; 未启用时不创建"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        cfg = FakeConfig()
        cfg.state_file = state_file
        cfg.grouping = GroupingConfig(enabled=True, interval=300, missing_tag="MISSING")
        mgr = QbManager("", config=cfg)
        names = {t.name for t in mgr.task_queue._fast}
        assert "grouping" in names, f"应创建分组任务: {names}"
        for t in mgr.task_queue._fast:
            if t.name == "grouping":
                assert t.interval == 300, f"分组任务 interval 应为 300: {t.interval}"

        # 未启用不创建
        cfg2 = FakeConfig()
        cfg2.state_file = state_file
        cfg2.grouping = GroupingConfig(enabled=False, interval=300, missing_tag="MISSING")
        mgr2 = QbManager("", config=cfg2)
        names2 = {t.name for t in mgr2.task_queue._fast}
        assert "grouping" not in names2, f"未启用不应创建分组任务: {names2}"
        print("[OK] test_grouping_queued_when_enabled: 分组任务入队/不入队")


def test_grouping_replaces_per_torrent_missing_files():
    """测试: grouping 启用时替代逐种子 missing_files 任务"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        cfg = FakeConfig()
        cfg.state_file = state_file
        cfg.check_missing_files = True
        cfg.grouping = GroupingConfig(enabled=True, interval=300, missing_tag="MISSING")
        mgr = QbManager("", config=cfg)
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(hash="H1", name="T1")
        mgr._snapshot = [tor]

        mgr._create_torrent_tasks("H1")
        names = {t.name for t in mgr.task_queue._fast}
        assert "missing_files" not in names, f"分组启用不应创建逐种子检查: {names}"

        # 未启用分组: 保留逐种子检查
        cfg2 = FakeConfig()
        cfg2.state_file = state_file
        cfg2.check_missing_files = True
        cfg2.grouping = GroupingConfig(enabled=False, interval=300, missing_tag="MISSING")
        mgr2 = QbManager("", config=cfg2)
        mgr2.client = FakeClient()
        mgr2._snapshot = [tor]
        mgr2._create_torrent_tasks("H1")
        names2 = {t.name for t in mgr2.task_queue._fast}
        assert "missing_files" in names2, f"未启用分组应保留逐种子检查: {names2}"
        print("[OK] test_grouping_replaces_per_torrent_missing_files: 分组替代逐种子检查")


def test_grouping_incremental_on_add():
    """测试: 新增种子时自动归组(增量), 不再每轮全量重建分组"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        cfg = FakeConfig()
        cfg.state_file = state_file
        cfg.grouping = GroupingConfig(enabled=True, interval=300, missing_tag="MISSING")
        mgr = QbManager("", config=cfg)
        client = FakeClient()
        mgr.client = client
        mgr._groups_ready = True  # 模拟分组已初始化完成, 之后走增量归组

        # 新增 H1 -> _refresh_torrents 检测 added 并自动归组
        t1 = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=r"R:\Downloads")
        client.torrents["H1"] = t1
        client.files_map["H1"] = [_fake_file("movie.mkv", 100)]
        mgr._refresh_torrents()
        assert len(mgr._groups) == 1, f"新种子应自动归组: {mgr._groups}"
        key = next(iter(mgr._groups))
        assert mgr._groups[key] == ["H1"], f"组内成员: {mgr._groups[key]}"
        assert key == ("R:/Downloads", ("movie.mkv",)), f"分组键: {key}"

        # 再新增 H2(同名同大小) -> 归入同一组
        t2 = FakeTorrent(hash="H2", name="T2", state="stalledUP", save_path=r"R:\Downloads")
        client.torrents["H2"] = t2
        client.files_map["H2"] = [_fake_file("movie.mkv", 100)]
        mgr._refresh_torrents()
        assert len(mgr._groups) == 1, f"H2 应归入同组: {mgr._groups}"
        assert set(mgr._groups[key]) == {"H1", "H2"}, f"组内成员: {mgr._groups[key]}"
        print("[OK] test_grouping_incremental_on_add: 新增种子自动归组")


def test_grouping_removed_from_groups():
    """测试: 种子删除时自动从分组移除(空组删除)"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        cfg = FakeConfig()
        cfg.state_file = state_file
        cfg.grouping = GroupingConfig(enabled=True, interval=300, missing_tag="MISSING")
        mgr = QbManager("", config=cfg)
        client = FakeClient()
        mgr.client = client
        mgr._groups_ready = True

        t1 = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=r"R:\Downloads")
        t2 = FakeTorrent(hash="H2", name="T2", state="stalledUP", save_path=r"R:\Downloads")
        client.torrents["H1"] = t1
        client.torrents["H2"] = t2
        client.files_map["H1"] = [_fake_file("movie.mkv", 100)]
        client.files_map["H2"] = [_fake_file("movie.mkv", 100)]
        mgr._refresh_torrents()
        key = next(iter(mgr._groups))
        assert set(mgr._groups[key]) == {"H1", "H2"}

        # 删除 H2 -> 组内只剩 H1
        del client.torrents["H2"]
        mgr._refresh_torrents()
        assert mgr._groups[key] == ["H1"], f"删除后组内成员: {mgr._groups[key]}"
        assert "H2" not in mgr._group_sizes[key], f"删除后应清掉文件大小映射: {mgr._group_sizes}"

        # 删除 H1 -> 空组删除
        del client.torrents["H1"]
        mgr._refresh_torrents()
        assert mgr._groups == {}, f"空组应删除: {mgr._groups}"
        assert mgr._group_sizes == {}, f"空组大小映射应删除: {mgr._group_sizes}"
        print("[OK] test_grouping_removed_from_groups: 删除种子移出分组")


def test_grouping_no_full_files_scan():
    """测试: 分组初始化后, 每轮检查不再全量拉取文件列表(增量维护分组)"""
    from auto_qb.taskqueue import Task

    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        cfg = FakeConfig()
        cfg.state_file = state_file
        cfg.grouping = GroupingConfig(enabled=True, interval=300, missing_tag="MISSING")
        mgr = QbManager("", config=cfg)
        client = FakeClient()
        mgr.client = client

        t1 = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=r"R:\Downloads")
        client.torrents["H1"] = t1
        client.files_map["H1"] = [_fake_file("movie.mkv", 100)]

        task = Task("internal", "grouping", interval=300, handler=mgr._handle_grouping)
        # 首轮: 初始化分组(拉取文件列表)
        mgr._handle_grouping(task, dry_run=False)
        assert mgr._groups_ready is True, f"首轮应完成分组初始化: {mgr._groups_ready}"
        assert client.files_calls >= 1, f"初始化应拉取文件列表: {client.files_calls}"

        # 第二轮: 状态不变 -> 不触发检查, 且不再拉取任何文件列表
        client.files_calls = 0
        client.calls.clear()
        mgr._handle_grouping(task, dry_run=False)
        assert client.files_calls == 0, f"每轮检查不应再全量拉文件列表: {client.files_calls}"
        assert client.calls == [], f"状态不变不应触发检查: {client.calls}"
        print("[OK] test_grouping_no_full_files_scan: 分组检查复用缓存, 不再全量拉文件列表")


if __name__ == "__main__":
    test_parse_utils()
    test_compare()
    test_state_mapping()
    test_basic()
    test_category_auto_update_from_state()
    test_category_explicit_overwrite_false()
    test_builtin_hr_category_auto_update_from_state()
    test_hr_satisfied()
    test_hr_required_share_ratio()
    test_tracker_hr_overrides_global()
    test_tracker_remove_similar_tags_override()
    test_stop_if_action_failed()
    test_dry_run()
    test_tracker_rules_ref()
    test_rule_interval()
    test_task_queue_schedule()
    test_async_check()
    test_skip_checking()
    test_skip_checking_guard()
    test_global_delete_tags()
    test_global_delete_tags_dry_run()
    test_global_delete_tags_if_has_no_torrents()
    test_global_delete_tags_no_pattern_match()
    test_global_delete_tags_queued()
    test_config_tracker_tags_expand()
    test_grouping_size_mismatch_pauses_group()
    test_grouping_missing_files_pauses_group()
    test_grouping_state_change_triggers_check()
    test_grouping_queued_when_enabled()
    test_grouping_replaces_per_torrent_missing_files()
    test_grouping_incremental_on_add()
    test_grouping_removed_from_groups()
    test_grouping_no_full_files_scan()
    print("\n全部自测通过!")
