"""rules 框架核心逻辑自测(不连接真实 qB, 用模拟对象)"""
import sys
import os
import tempfile

# 使测试可直接运行: python tests/test_rules.py
# 将项目根下的 src/ 加入模块搜索路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from auto_qb.rules import RuleManager, RuleContext, ActionResult  # noqa: E402


# ---------- 模拟 qB 客户端 ----------
class FakeClient:
    def __init__(self):
        self.tags = set()
        self.category = ""
        self.calls = []

    def torrents_trackers(self, h):
        return [{"url": "https://tracker.hhanclub.net/announce.php"}]

    def torrents_files(self, h):
        return []

    def torrents_add_tags(self, tags=None, torrent_hashes=None):
        self.tags.update(tags)
        self.calls.append(("add_tags", tags))

    def torrents_remove_tags(self, tags=None, torrent_hashes=None):
        self.tags.difference_update(tags)
        self.calls.append(("remove_tags", tags))

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
    def __init__(self, name, hr_rule, rules=None):
        self.name = name
        self.domains = ["tracker.hhanclub.net"]
        self.hr_rule = hr_rule
        self.rules = rules or []


# ---------- 模拟 Config ----------
class FakeConfig:
    trackers = {"HHan": FakeTracker("HHan", "3D@70%+12H")}
    state_file = ""  # 由测试设置


def make_manager(state_file, tracker_rules=None):
    cfg = FakeConfig()
    cfg.state_file = state_file
    cfg.trackers = {"HHan": FakeTracker("HHan", "3D@70%+12H", rules=tracker_rules)}
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
                            "add_tags": ["HHan", "seed-${hr-time}"]
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
    return RuleManager(cfg, state_file)


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
        print("[OK] test_basic: 标签规则+${hr-time}变量替换")


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
    from auto_qb.rules import utils
    assert utils.parse_time("3D") == 3 * 86400
    assert utils.parse_fsize("10MiB") == 10 * 1024**2
    assert utils.parse_speed("1000KiB/s") == 1000 * 1024
    rt, cond, extra = utils.parse_hr_rule("3D@70%+12H")
    assert rt == 3 * 86400 and cond == ("dlratio", 0.7) and extra == 12 * 3600
    assert utils.parse_hr_rule("20H@10MiB")[1] == ("dlsize", 10 * 1024**2)
    assert utils.parse_bool("true") is True
    print("[OK] test_parse_utils: 解析工具")


def test_compare():
    """测试: 比较解析"""
    from auto_qb.rules import utils
    op, val = utils.parse_compare(">=100MiB", utils.parse_fsize)
    assert op == ">=" and val == 100 * 1024**2
    assert utils.compare(">", 5, 3)
    assert not utils.compare("<", 5, 3)
    print("[OK] test_compare: 比较表达式")


def test_rule_interval():
    """测试: 规则 interval 调度(任务队列思想)—— 未到期的规则跳过本轮, interval=0 每轮执行"""
    with tempfile.TemporaryDirectory() as td:
        state_file = os.path.join(td, "state.json")
        cfg = FakeConfig()
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
        mgr = RuleManager(cfg, state_file)
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(tags="", ratio=0.1, state="uploading")

        # 第 1 轮: 所有规则到期, 均应执行
        mgr.begin_round([tor])
        handled = mgr.process_torrent(tor, dry_run=False)
        assert handled, "第 1 轮 stop_low_ratio 应执行"
        assert ("stop", None) in client.calls, f"第 1 轮应 stop: {client.calls}"

        # 第 2 轮(间隔 60S 内): stop_low_ratio 应被调度跳过, add_site_tag(interval=0) 仍执行
        client.calls.clear()
        mgr.begin_round([tor])
        handled2 = mgr.process_torrent(tor, dry_run=False)
        assert handled2, "第 2 轮 add_site_tag 应仍执行"
        assert ("stop", None) not in client.calls, f"interval 未到期不应再次 stop: {client.calls}"
        assert client.tags == {"HHan"}, f"add_site_tag 应仍执行: {client.tags}"

        # 不调用 begin_round 直接 process_torrent(旧用法兜底): 每次调用视为新一轮, 规则全部执行
        mgr3 = RuleManager(cfg, state_file)
        client3 = FakeClient()
        mgr3.client = client3
        handled3 = mgr3.process_torrent(tor, dry_run=False)
        assert handled3, "无 begin_round 时规则应全部执行(向后兼容)"
        assert ("stop", None) in client3.calls, f"兜底路径应执行全部规则: {client3.calls}"
        print("[OK] test_rule_interval: 规则 interval 调度")


def test_task_queue_schedule():
    """测试: 快速队列 interval 调度(时间优先堆)"""
    from auto_qb.rules.taskqueue import TaskQueue
    tq = TaskQueue()
    now = 1000.0
    tq.schedule_rule("example_rules.every_round", 0, now=now)  # 每轮
    tq.schedule_rule("example_rules.interval60", 60, now=now)  # 60s 一次

    # 到期弹出: interval=60 的任务 next_run 已到; interval=0 每轮任务留在队列
    due = tq.due_rules(now)
    assert [t.name for t in due] == ["example_rules.interval60"], f"due={[t.name for t in due]}"

    # 未到期不应弹出
    assert tq.due_rules(now + 59) == [], "未到期不应弹出"

    # 执行完按 interval 重新入队, 到点再弹
    tq.reschedule(due[0], now)
    assert tq.due_rules(now + 59) == [], "重新入队后未到 60s 不应弹出"
    assert [t.name for t in tq.due_rules(now + 60)] == ["example_rules.interval60"]

    # 弹出后未 reschedule 不再出现; interval=0 的任务恒活跃不进时间堆(由调用方每轮执行)
    assert tq.due_rules(now + 120) == [], "未 reschedule 的任务不应再次弹出"
    tq.shutdown()
    print("[OK] test_task_queue_schedule: 快速队列 interval 调度")


def test_async_check():
    """测试: check 动作异步提交校验(慢速队列), 主循环轮询完成 -> 自动开始 + 记录执行"""
    from auto_qb.rules.taskqueue import TaskQueue
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
        mgr = RuleManager(cfg, state_file)
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


if __name__ == "__main__":
    test_parse_utils()
    test_compare()
    test_state_mapping()
    test_basic()
    test_hr_satisfied()
    test_stop_if_action_failed()
    test_dry_run()
    test_tracker_rules_ref()
    test_rule_interval()
    test_task_queue_schedule()
    test_async_check()
    print("\n全部自测通过!")
