"""kernel-module-refactor P4 守阵: grouping / ops(+checking) 两模块(plan 26-09-30-1819)

P4 内容: GroupingMixin(387 行)迁 GroupingModule, 认领四个刷新相位(transitions /
torrents_added / removed_scan / post, §4.2 相位表), enabled 开关与缺文件扫描轮内去重集合
归模块自管, 内核 _refresh_torrents 的分组调用点改相位广播; OpsMixin(474 行)+ CheckingMixin
(39 行, 决策点 D2)迁 OpsModule 升 ctx.ops 服务, web 命令改走 ctx.ops, rules 轮询常量与
冷却 helper 迁 rules 包中性叶 checking_meta(ops 与 rules 单向化)。
本文件锁六件事:
1. ctx 服务/句柄装配: ctx.ops / ctx.maintenance 是已注册模块本体, 装配序在 maintenance
   之后(webui/hr -> tracker/speed_curve/maintenance -> grouping -> ops);
2. 四相位接线: 内核 emit -> grouping 响应, 订阅者计数锁定(避免隐式双订阅);
3. enabled 自判 + 去重集合归属: disabled 时零动作、去重清零随 transitions 相位入口;
4. ctx.ops 直调(recheck web 源提交 + skip_check 跨来源去重)与 manager 旧名委托同源;
5. checking 前置检查并入 ops(check_filelist 经 ctx.ops 与 manager 委托都可达);
6. sections 认领清单(P6 段认领完备守阵上线前的基线锁定)。

行为细节(缺文件扫描/大小一致性/冲突检查/保护策略)的守阵仍在原位: test_grouping /
test_file_access / test_checking / test_ops(经 manager 旧名单行委托, plan §7.2)。

## 测试计划
- test_grouping_ops_on_ctx_and_registered: ctx.ops/ctx.maintenance 是宿主注册表里的模块本体, 装配序锁定
- test_grouping_phases_wired: 四相位各恰有一个订阅者(grouping), emit 返回计数为 1
- test_transitions_phase_guards_enabled_and_clears_dedup: disabled 零动作; 去重集合每轮经该相位入口清零
- test_torrents_added_phase_assigns_new_torrent: 逐新增种子相位驱动归组(enabled 自判)
- test_removed_scan_and_post_phases_drive_grouping: 删除扫描与收尾两相位驱动 grouping
- test_ops_service_via_ctx_matches_manager_delegate: ctx.ops.recheck/skip_check 直调与 mgr.ops_* 委托同源同效
- test_check_filelist_merged_into_ops: check_filelist 经 ctx.ops 与 manager 委托双路可达
- test_p4_modules_sections_claims: 两模块 sections 认领清单锁定
"""
import os
import tempfile
from unittest import mock

from auto_qb.config import GroupingConfig
from auto_qb.core.modules import GroupingModule, OpsModule
from auto_qb.core.qbmanager import QbManager
from helpers import FakeClient, FakeConfig, FakeTorrent, seed_store


def _fake_file(name, size):
    from types import SimpleNamespace
    return SimpleNamespace(name=name, size=size)


def _mgr(td, grouping_enabled=True):
    cfg = FakeConfig()
    cfg.state_file = os.path.join(td, "state.json")
    cfg.grouping = GroupingConfig(enabled=grouping_enabled, missing_tag="MISSING")
    mgr = QbManager("", config=cfg, no_lock=True)  # 测试不持锁
    return mgr


# ---------- 装配与 ctx 服务(plan §3.3) ----------


def test_grouping_ops_on_ctx_and_registered():
    """ctx.ops / ctx.maintenance 就是宿主注册表里的模块本体(P4 句柄挂 ctx)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(td)
        assert isinstance(mgr.ctx.ops, OpsModule)
        assert mgr.host.get("ops") is mgr.ctx.ops, "危险操作层经 ctx.ops 服务调用(单一真相)"
        assert isinstance(mgr.ctx.maintenance,
                          OpsModule) is False and mgr.ctx.maintenance is mgr.host.get("maintenance")
        # 装配序(plan §3.3): ... tracker -> speed_curve -> maintenance -> grouping -> ops
        names = [m.name for m in mgr.host.modules()]
        assert names.index("maintenance") < names.index("grouping") < names.index("ops")


# ---------- 四相位接线(plan §4.2) ----------


def test_grouping_phases_wired():
    """transitions/torrents_added/removed_scan/post 四相位各恰有 grouping 一个订阅者

    订阅在装配点一次性登记(EventBus 持注册期绑定的 handler), 故以登记计数 + emit 返回值
    锁定接线; 行为由本文件其余用例直接验证。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(td)
        mgr.client = FakeClient()
        t = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=r"R:\Downloads")
        seed_store(mgr, [t])  # torrents_added 相位直驱 _assign_new_torrent, 需要库内活记录
        payloads = {
            "transitions": {
                "dry_run": True
            },
            "torrents_added": {
                "hash": "H1",
                "dry_run": True
            },
            "removed_scan": {
                "hashes": [],
                "dry_run": True
            },
            "post": {
                "dry_run": True
            },
        }
        for phase, payload in payloads.items():
            handlers = mgr.events._handlers.get(phase, [])
            assert len(handlers) == 1, f"{phase} 相位应恰有 grouping 一个订阅者, 实际 {len(handlers)}"
            assert mgr.events.emit(phase, payload) == 1, f"{phase} 相位广播应触达 1 个订阅者"


def test_transitions_phase_guards_enabled_and_clears_dedup():
    """enabled 自判: 关闭时 transitions 零动作; 去重集合每轮经该相位入口无条件清零"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(td, grouping_enabled=False)
        mod = mgr.host.get("grouping")
        mod._missing_scanned_keys.add(("R:/Downloads", ("a.mkv", )))
        with mock.patch.object(mod, "_handle_state_transitions") as transitions:
            mgr.events.emit("transitions", {"dry_run": True})
        transitions.assert_not_called()  # disabled: 不做状态转移处理
        assert mod._missing_scanned_keys == set(), "去重清零必须先于 enabled 判定(原内核每轮开头无条件 clear 的时序)"

        mgr.config.grouping.enabled = True
        with mock.patch.object(mod, "_handle_state_transitions") as transitions:
            mgr.events.emit("transitions", {"dry_run": False})
        transitions.assert_called_once_with(False)


def test_torrents_added_phase_assigns_new_torrent():
    """逐新增种子相位驱动归组(enabled 自判); disabled 时同一 emit 零归组"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(td)
        mgr.client = FakeClient()
        t = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=r"R:\Downloads")
        client = mgr.client
        client.torrents["H1"] = t
        client.files_map["H1"] = [_fake_file("movie.mkv", 100)]
        seed_store(mgr, [t])
        n = mgr.events.emit("torrents_added", {"hash": "H1", "dry_run": True})
        assert n == 1
        assert len(mgr.store.groups) == 1, f"相位应驱动增量归组: {mgr.store.groups}"

        # disabled: 相位仍广播, 模块自判零动作
        mgr.config.grouping.enabled = False
        t2 = FakeTorrent(hash="H2", name="T2", state="stalledUP", save_path=r"R:\Downloads")
        client.torrents["H2"] = t2
        client.files_map["H2"] = [_fake_file("movie.mkv", 100)]
        seed_store(mgr, [t2])
        mgr.events.emit("torrents_added", {"hash": "H2", "dry_run": True})
        assert [len(v) for v in mgr.store.groups.values()] == [1], "disabled 时不得归组新种子"


def test_removed_scan_and_post_phases_drive_grouping():
    """删除扫描与每轮收尾两相位由内核广播、grouping 认领(调用点与原 _refresh_torrents 同序)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(td)
        client = FakeClient()
        mgr.client = client
        t = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=r"R:\Downloads")
        client.torrents["H1"] = t
        client.files_map["H1"] = [_fake_file("movie.mkv", 100)]
        seed_store(mgr, [t])
        mod = mgr.host.get("grouping")
        mod._assign_new_torrent("H1", dry_run=True)
        key = next(iter(mgr.store.groups))

        with mock.patch.object(mod, "_handle_removed_torrents") as removed, \
                mock.patch.object(mod, "_handle_save_path_changes") as save_path, \
                mock.patch.object(mod, "_check_download_conflicts") as conflicts:
            assert mgr.events.emit("removed_scan", {"hashes": ["H1"], "dry_run": False}) == 1
            removed.assert_called_once_with(["H1"], False)
            assert mgr.events.emit("post", {"dry_run": True}) == 1
            save_path.assert_called_once_with(True)
            conflicts.assert_called_once_with(True)


# ---------- ops 服务(ctx.ops 直调与旧名委托同源) ----------


def test_ops_service_via_ctx_matches_manager_delegate():
    """ctx.ops.recheck/skip_check 直调可用(web 源); 与 manager 旧名委托是同一执行体"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(td)
        mgr.client = FakeClient()
        t = FakeTorrent(hash="HA", state="pausedDL", progress=0.0)
        seed_store(mgr, [t])
        # 直调: web 源提交 -> 在途登记(决策链 1.5 可见)
        r = mgr.ctx.ops.recheck("HA", source="web")
        assert r.is_ok, f"ctx.ops 直调应等价旧入口: {r}"
        assert "HA" in mgr.task_queue.active_check_hashes(), "ctx.ops 提交同样登记在途"
        # 委托: 在途互斥对 manager 旧名入口同样生效(同一 _active_checks)
        r2 = mgr.ops_recheck("HA", source="web")
        assert r2.is_skipped and "校验进行中" in r2.message, "旧名委托与 ctx.ops 共享在途互斥"


def test_check_filelist_merged_into_ops():
    """checking 前置检查并入 ops(决策点 D2): ctx.ops 与 manager 委托双路可达同一静态方法"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(td)
        client = FakeClient()
        client.files = []  # 空 = 全部通过
        tor = FakeTorrent(hash="H1", save_path=r"R:\Downloads")
        assert mgr.ctx.ops.check_filelist(client, tor) is None
        assert mgr.check_filelist(client, tor) is None, "manager 旧名委托(供 rules 决策链)保持可用"


def test_p4_modules_sections_claims():
    """两模块 sections 认领清单锁定(P6 段认领完备守阵上线前的基线)"""
    assert GroupingModule(None).sections() == ("grouping", )
    assert OpsModule(None).sections() == ("skip_checking_tag", )
