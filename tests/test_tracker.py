"""test_tracker 测试计划: tracker 配置匹配/单种限速(tracker 模块, plan P3 迁入)

经 QbManager 旧名单行委托调用(plan §7.2), 实现单点在 core/modules/tracker_mod.py。

## 测试计划(每个测试函数一条)
- test_match_tracker_domain: 域名匹配(hostname 精确匹配)
- test_match_tracker_no_match: 无匹配返回 None
- test_match_tracker_multi_domain: 多域名配置匹配
- test_match_tracker_subdomain: 配置主域匹配子域 tracker hostname
- test_match_tracker_no_substring_match: 子串不再误匹配(如 hhanclub.net 不匹配 fakehhanclub.net)
- test_match_tracker_conf_multi_match_warning_log: 匹配到多个 tracker 配置返回第一个并打印 WARNING 日志(等级整改 26-09-27-1126: 自动降级属排障语义)
- test_apply_speed_limit_sets_both_directions: 未设限速时写入上传+下载
- test_apply_speed_limit_skips_when_equal: 当前值==目标值不重复写
- test_apply_speed_limit_odd_manual_skip: 当前为奇数 KiB 手动限速不覆盖(仅另一方向写)
- test_apply_speed_limit_dry_run_no_api: dry_run 只记日志不调 API
- test_apply_rebinds_existing_records_on_trackers_change: trackers 段变即重绑存量记录(hr_check 就位, 回执含 rebound); tracker_conf 为 None 的记录不动(归 full_round)
- test_apply_skips_rebind_when_client_disconnected: qB 断开(client=None)跳过重绑不抛异常, 照常返回
- test_apply_equal_trackers_short_circuits: trackers 段按值相等即短路(回执 none, 记录引用不变)
"""
import copy
import io
import logging
import os
import tempfile

from auto_qb.config import TrackerConfig
from auto_qb.config.models import SiteHrCheckConfig  # 包 __init__ 未导出 HR 在线核实配置类
from helpers import FakeClient, FakeTorrent, make_manager


def _conf(name, domains):
    # 其余字段使用 TrackerConfig 字段默认(tags=[] / 限速 0=不限速 / rules=[])
    return TrackerConfig(name=name, domains=domains)


def test_match_tracker_domain():
    """域名精确匹配(URL hostname 与配置域名一致)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        mgr.config.trackers = {"HHan": _conf("HHan", ["tracker.hhanclub.net"])}
        tor = FakeTorrent(hash="H1")
        conf = mgr.ctx.trackers.match(tor)
        assert conf is not None and conf.name == "HHan"


def test_match_tracker_no_match():
    """无匹配域名返回 None"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        mgr.config.trackers = {"Kufirc": _conf("Kufirc", ["kufirc.com"])}
        tor = FakeTorrent(hash="H1")
        assert mgr.ctx.trackers.match(tor) is None


def test_match_tracker_multi_domain():
    """多域名配置: 任一命中即可"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        mgr.config.trackers = {"Kufirc": _conf("Kufirc", ["kufirc.com", "tracker.hhanclub.net"])}
        tor = FakeTorrent(hash="H1")
        assert mgr.ctx.trackers.match(tor).name == "Kufirc"


def test_match_tracker_subdomain():
    """配置主域 hhanclub.net 可匹配子域 tracker.hhanclub.net(hostname 精确匹配含子域名)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        client.torrents_trackers = lambda h: [{"url": "https://tracker.hhanclub.net/announce.php"}]
        mgr.client = client
        mgr.config.trackers = {"HHan": _conf("HHan", ["hhanclub.net"])}
        tor = FakeTorrent(hash="H1")
        assert mgr.ctx.trackers.match(tor).name == "HHan"


def test_match_tracker_no_substring_match():
    """子串不再误匹配: 配置 hhanclub.net 不匹配 fakehhanclub.net(修复旧包含匹配语义)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        client.torrents_trackers = lambda h: [{"url": "https://fakehhanclub.net/announce.php"}]
        mgr.client = client
        mgr.config.trackers = {"HHan": _conf("HHan", ["hhanclub.net"])}
        tor = FakeTorrent(hash="H1")
        assert mgr.ctx.trackers.match(tor) is None


def test_match_tracker_conf_multi_match_warning_log():
    """匹配到多个 tracker 配置: 返回第一个并打印 WARNING 日志(等级整改 26-09-27-1126 表 D1: 自动降级属排障语义)

    注: QbManager 构造时 setup_logging 清空 root handlers(caplog 捕获失效),
    故直接给模块 logger 挂 StringIO 捕获 handler(同 test_speed_curve 模式)。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        # 两个配置均能命中 FakeClient 的 tracker.hhanclub.net(一个主域一个完整域)
        mgr.config.trackers = {
            "HHan": _conf("HHan", ["hhanclub.net"]),
            "HHanTracker": _conf("HHanTracker", ["tracker.hhanclub.net"]),
        }
        tor = FakeTorrent(hash="H1")
        lg = logging.getLogger("auto_qb.core.modules.tracker_mod")
        buf = io.StringIO()
        handler = logging.StreamHandler(buf)
        handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        lg.addHandler(handler)
        try:
            conf = mgr.ctx.trackers.match(tor)
        finally:
            lg.removeHandler(handler)
        assert conf is not None and conf.name == "HHan"  # 返回配置序中第一个
        text = buf.getvalue()
        # 等级整改 26-09-27-1126 表 D1: 配置歧义自动降级是排障语义, ERROR -> WARNING
        assert "WARNING" in text and "多个 tracker 配置" in text, f"缺少 WARNING 日志: {text}"
        assert "HHan" in text and "HHanTracker" in text  # 日志列出所有命中配置


# ---------- 热重载重绑(plan 26-10-03-0436 Step 1: TrackerModule.apply) ----------


def _old_new(mgr, old_trackers, new_trackers):
    """构造热重载的新旧配置对: 整对象替换模拟生产「重新加载出全新对象」(原地改 ≠ 热重载)"""
    old = copy.copy(mgr.config)
    new = copy.copy(mgr.config)
    old.trackers = old_trackers
    new.trackers = new_trackers
    return old, new


def test_apply_rebinds_existing_records_on_trackers_change():
    """trackers 段变化: 存量记录(tracker_conf 非 None)立即重绑到新配置对象, 回执含 rebound

    根因面(plan §2): L2 重建判据只比较绑定三元组(domains/rules/groups), hr_check 从无到有
    不触发重建; full_round 只补 tracker_conf is None 的记录 —— 不重绑则 hr_judgement() 读旧
    对象的 hr_check=None 恒走「站点未接入」本地兜底(WebUI 停留「本地·达标」)。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.client = FakeClient()
        old_conf = TrackerConfig(name="HHan", domains=["tracker.hhanclub.net"])
        new_conf = TrackerConfig(
            name="HHan", domains=["tracker.hhanclub.net"], hr_check=SiteHrCheckConfig(tracker="HHan", enabled=True)
        )
        old, new = _old_new(mgr, {"HHan": old_conf}, {"HHan": new_conf})
        tor = FakeTorrent(hash="H1", tracker_conf=old_conf)  # 存量记录持旧配置对象
        fresh = FakeTorrent(hash="H2")  # tracker_conf None: 重匹配归 full_round, apply 不动
        mgr.store.by_hash["H1"] = tor
        mgr.store.by_hash["H2"] = fresh
        mgr.config = new  # 生产时序: apply_new_config 先换配置对象再广播 apply
        res = mgr.ctx.trackers.apply(old, new)
        assert res.module == "tracker" and "rebound" in res.action
        assert tor.tracker_conf is new_conf, "存量记录必须重绑到新配置的对象"
        assert tor.tracker_conf.hr_check is not None and tor.tracker_conf.hr_check.enabled, "hr_check 派生视图就位"
        assert fresh.tracker_conf is None


def test_apply_skips_rebind_when_client_disconnected():
    """qB 断开(client=None): 跳过重绑、不抛异常、照常返回(留给下轮 full_round / L2 兑现)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))  # 不绑 client = qB 断开
        old_conf = TrackerConfig(name="HHan", domains=["tracker.hhanclub.net"])
        new_conf = TrackerConfig(
            name="HHan", domains=["tracker.hhanclub.net"], hr_check=SiteHrCheckConfig(tracker="HHan", enabled=True)
        )
        old, new = _old_new(mgr, {"HHan": old_conf}, {"HHan": new_conf})
        tor = FakeTorrent(hash="H1", tracker_conf=old_conf)
        mgr.store.by_hash["H1"] = tor
        mgr.config = new
        res = mgr.ctx.trackers.apply(old, new)  # 不得抛异常打断热重载广播
        assert res.module == "tracker" and res.action == "none"
        assert tor.tracker_conf is old_conf, "断开时不得重绑"


def test_apply_equal_trackers_short_circuits():
    """trackers 段按值相等(分别构造的等值 TrackerConfig): 短路零动作, 记录引用不变"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.client = FakeClient()
        old, new = _old_new(
            mgr,
            {"HHan": TrackerConfig(name="HHan", domains=["tracker.hhanclub.net"])},
            {"HHan": TrackerConfig(name="HHan", domains=["tracker.hhanclub.net"])},
        )
        tor = FakeTorrent(hash="H1", tracker_conf=old.trackers["HHan"])
        mgr.store.by_hash["H1"] = tor
        mgr.config = new
        res = mgr.ctx.trackers.apply(old, new)
        assert res.action == "none", "整段按值相等必须短路(无关保存零动作)"
        assert tor.tracker_conf is old.trackers["HHan"], "短路不得换记录的绑定对象"


# ---------- tracker 单种限速 _apply_speed_limit ----------


def test_apply_speed_limit_sets_both_directions():
    """未设限速的种子: 上传+下载按 tracker 配置写入(字节/秒)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(hash="H1")
        conf = _conf("HHan", ["hhanclub.net"])
        conf.upload_speed_limit = 5 * 1024 * 1024
        conf.download_speed_limit = 2 * 1024 * 1024
        mgr.ctx.trackers.apply_speed_limit(tor, conf, dry_run=False)
        assert client.calls == [
            ("set_upload_limit", 5 * 1024 * 1024),
            ("set_download_limit", 2 * 1024 * 1024),
        ]


def test_apply_speed_limit_skips_when_equal():
    """当前限速已等于目标值: 幂等跳过不重复写"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(hash="H1", up_limit=5 * 1024 * 1024, dl_limit=5 * 1024 * 1024)
        conf = _conf("HHan", ["hhanclub.net"])
        conf.upload_speed_limit = 5 * 1024 * 1024
        conf.download_speed_limit = 5 * 1024 * 1024
        mgr.ctx.trackers.apply_speed_limit(tor, conf, dry_run=False)
        assert client.calls == []


def test_apply_speed_limit_odd_manual_skip():
    """当前为手动限速(奇数 KiB): 不覆盖该方向; 另一方向仍正常写入"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        # up_limit=2001*1024B = 2001KiB(奇数 -> 视为手动设置), dl_limit=0
        tor = FakeTorrent(hash="H1", up_limit=2001 * 1024, dl_limit=0)
        conf = _conf("HHan", ["hhanclub.net"])
        conf.upload_speed_limit = 5 * 1024 * 1024
        conf.download_speed_limit = 5 * 1024 * 1024
        mgr.ctx.trackers.apply_speed_limit(tor, conf, dry_run=False)
        assert client.calls == [("set_download_limit", 5 * 1024 * 1024)]


def test_apply_speed_limit_dry_run_no_api():
    """dry_run: 只打日志不调用任何 API"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        client = FakeClient()
        mgr.client = client
        tor = FakeTorrent(hash="H1")
        conf = _conf("HHan", ["hhanclub.net"])
        conf.upload_speed_limit = 5 * 1024 * 1024
        conf.download_speed_limit = 2 * 1024 * 1024
        mgr.ctx.trackers.apply_speed_limit(tor, conf, dry_run=True)
        assert client.calls == []
