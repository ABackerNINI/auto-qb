"""kernel-module-refactor P4 守阵: grouping / ops(+checking) 两模块(plan 26-09-30-1819)

P4 内容: GroupingMixin(387 行)迁 GroupingModule, 认领四个刷新相位(transitions /
torrents_added / removed_scan / post, §4.2 相位表), enabled 开关与缺文件扫描轮内去重集合
归模块自管, 内核 _refresh_torrents 的分组调用点改相位广播; OpsMixin(474 行)+ CheckingMixin
(39 行, 决策点 D2)迁 OpsModule 升 ctx.ops 服务, web 命令改走 ctx.ops, rules 轮询常量与
冷却 helper 迁 rules 包中性叶 checking_meta(ops 与 rules 单向化)。
本文件锁六件事:
1. ctx 服务/句柄装配: ctx.ops / ctx.maintenance 是已注册模块本体, 装配序在 maintenance
   之后(webui/hr -> tracker/speed_curve/maintenance -> grouping -> ops);
2. 相位接线: transitions/removed_scan/post 三相位内核 emit -> grouping 响应, 订阅者计数
   锁定(避免隐式双订阅); torrents_added 自 P5 起四家认领, 订阅面在 test_modules_p5 锁定;
3. enabled 自判 + 去重集合归属: disabled 时零动作、去重清零随 transitions 相位入口;
4. ctx.ops 直调: web 源 recheck 提交登记在途, 重复提交受在途互斥(同一 _active_checks);
5. checking 前置检查并入 ops(决策点 D2): ctx.ops.check_filelist 是唯一入口;
6. sections 认领清单(P6 段认领完备守阵上线前的基线锁定)。

行为细节(缺文件扫描/大小一致性/冲突检查/保护策略)的守阵仍在原位: test_grouping /
test_file_access / test_checking / test_ops(W3 起 manager 旧名委托已内联删除, 经
ctx.ops / host.get("<模块>") 模块入口驱动, plan §7.2)。

## 测试计划
- test_grouping_ops_on_ctx_and_registered: ctx.ops/ctx.maintenance 是宿主注册表里的模块本体, 装配序锁定
- test_grouping_phases_wired: transitions/removed_scan/post 三相位各恰有 grouping 一个订阅者, emit 返回计数为 1(torrents_added 四家订阅面在 test_modules_p5 锁定)
- test_transitions_phase_guards_enabled_and_clears_dedup: disabled 零动作; 去重集合每轮经该相位入口清零
- test_torrents_added_phase_assigns_new_torrent: 逐新增种子相位驱动归组(enabled 自判), disabled 时同一 emit 零归组
- test_torrents_added_single_failure_does_not_abort_batch: 批内单条 files 取数抛错只影响本条(issue 26-11-14-0745), 失败条入待归组补偿清单, post 相位重试补归组并出清单
- test_pending_assign_retry_drops_removed_seed: 补偿清单中种子已删, post 重试出清单不抛错
- test_removed_scan_and_post_phases_drive_grouping: 删除扫描与收尾两相位驱动 grouping(调用点与原 _refresh_torrents 同序)
- test_ops_service_direct_call_and_inflight_mutex: ctx.ops.recheck 直调提交登记在途(web 源), 重复提交受在途互斥
- test_check_filelist_merged_into_ops: check_filelist 并入 ops(决策点 D2), ctx.ops.check_filelist 是唯一入口
- test_p4_modules_sections_claims: 两模块 sections 认领清单锁定
"""
import os
import tempfile
from unittest import mock

from auto_qb.core.modules import GroupingModule, OpsModule
from helpers import FakeClient, FakeTorrent, _fake_file, grouping_cfg, make_manager, seed_store


def _mgr(td, grouping_enabled=True):
    return make_manager(os.path.join(td, "state.json"), bare=True, grouping=grouping_cfg(enabled=grouping_enabled))


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
    """transitions 恰有 grouping 一个订阅者; removed_scan 为 grouping+maintenance 两家; post 自 S2 起为 grouping+fuse 两家

    订阅在装配点一次性登记(EventBus 持注册期绑定的 handler), 故以登记计数 + emit 返回值
    锁定接线; 行为由本文件其余用例直接验证。torrents_added 相位自 P5 起由四家认领
    (tracker/maintenance/grouping/rules, plan §4.2), 订阅面在 test_modules_p5 锁定。
    post 相位 S2(计划 26-11-03-0456)追加 fuse(下载保险丝); removed_scan 相位自
    issue 26-11-07-0527 追加 maintenance(清 state.auto_categories 残留), 故按 phase 给定期望订阅数。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(td)
        mgr.client = FakeClient()
        t = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=r"R:\Downloads")
        seed_store(mgr, [t])  # torrents_added 相位直驱 _assign_new_torrent, 需要库内活记录
        payloads = {
            "transitions": ({
                "dry_run": True
            }, 1),
            "removed_scan": ({
                "hashes": [],
                "dry_run": True
            }, 2),  # grouping + maintenance(26-11-07-0527)
            "post": ({
                "dry_run": True
            }, 2),  # grouping + fuse(S2)
        }
        for phase, (payload, expected) in payloads.items():
            handlers = mgr.events._handlers.get(phase, [])
            assert len(handlers) == expected, f"{phase} 相位订阅数应为 {expected}, 实际 {len(handlers)}"
            assert any(getattr(h, "__self__", None) is mgr.host.get("grouping") for h in handlers), \
                f"{phase} 相位缺 grouping 订阅"
            assert mgr.events.emit(phase, payload) == expected, f"{phase} 相位广播应触达 {expected} 个订阅者"


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
        t.tracker_conf = mgr.config.trackers["HHan"]  # 相位契约: conf 已就位(内核 added 循环先行匹配)
        client = mgr.client
        client.torrents["H1"] = t
        client.files_map["H1"] = [_fake_file("movie.mkv", 100)]
        seed_store(mgr, [t])
        n = mgr.events.emit("torrents_added", {"hash": "H1", "dry_run": True})
        assert n == 4, f"torrents_added 相位应有四家订阅(tracker/maintenance/grouping/rules): {n}"
        assert len(mgr.store.groups) == 1, f"相位应驱动增量归组: {mgr.store.groups}"

        # disabled: 相位仍广播, 模块自判零动作
        mgr.config.grouping.enabled = False
        t2 = FakeTorrent(hash="H2", name="T2", state="stalledUP", save_path=r"R:\Downloads")
        t2.tracker_conf = mgr.config.trackers["HHan"]  # 同上: conf 已就位
        client.torrents["H2"] = t2
        client.files_map["H2"] = [_fake_file("movie.mkv", 100)]
        seed_store(mgr, [t2])
        mgr.events.emit("torrents_added", {"hash": "H2", "dry_run": True})
        assert [len(v) for v in mgr.store.groups.values()] == [1], "disabled 时不得归组新种子"


def test_torrents_added_single_failure_does_not_abort_batch():
    """issue 26-11-14-0745: 批内单条 files 取数抛错只影响本条, 其余种子照常归组

    失败条转入待归组补偿清单, post 相位重试成功后补归组并出清单(rid 已推进、账本已
    upsert, 失败轮种子下轮不再判 added —— 补偿只能靠显式清单, 不能承诺自动重放)。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(td)
        mgr.client = FakeClient()
        client = mgr.client
        mod = mgr.host.get("grouping")
        ts = []
        for i, h in enumerate(("H1", "H2", "H3")):
            t = FakeTorrent(hash=h, name=f"T{i+1}", state="stalledUP", save_path=r"R:\Downloads")
            t.tracker_conf = mgr.config.trackers["HHan"]  # 相位契约: conf 已就位(内核 added 循环先行匹配)
            client.torrents[h] = t
            client.files_map[h] = [_fake_file(f"movie{i+1}.mkv", 100)]
            ts.append(t)
        seed_store(mgr, ts)

        real_files = client.torrents_files

        def flaky_files(h):
            if h == "H2":
                raise RuntimeError("files 取数断连注入(issue 26-11-14-0745)")
            return real_files(h)

        with mock.patch.object(client, "torrents_files", side_effect=flaky_files):
            for h in ("H1", "H2", "H3"):  # T6 同款批处理: H2 中段抛错
                mgr.events.emit("torrents_added", {"hash": h, "dry_run": True})
        assert len(mgr.store.groups) == 2, f"H2 失败不得中断 H1/H3 归组: {mgr.store.groups}"
        assert not any("H2" in members for members in mgr.store.groups.values()), "失败条不得进任何组"
        assert mod._pending_assign == {"H2"}, f"失败条必须入待归组补偿清单: {mod._pending_assign}"

        # 断连恢复: post 相位每轮重试补偿清单, H2 补归组并出清单
        with mock.patch.object(mod, "_handle_save_path_changes"), \
                mock.patch.object(mod, "_check_cross_group_file_conflicts"), \
                mock.patch.object(mod, "_check_download_conflicts"):
            mgr.events.emit("post", {"dry_run": True})
        assert mod._pending_assign == set(), "补偿成功必须出清单"
        assert len(mgr.store.groups) == 3, f"post 重试应补归组 H2: {mgr.store.groups}"


def test_pending_assign_retry_drops_removed_seed():
    """补偿清单中种子已删: post 重试出清单, 不重试不抛错(幂等 pop)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(td)
        mgr.client = FakeClient()
        client = mgr.client
        t = FakeTorrent(hash="H1", name="T1", state="stalledUP", save_path=r"R:\Downloads")
        client.torrents["H1"] = t
        client.files_map["H1"] = [_fake_file("movie.mkv", 100)]
        seed_store(mgr, [t])
        mod = mgr.host.get("grouping")
        mod._pending_assign.add("H1")
        mgr.store.by_hash.pop("H1")  # 种子已删(store 对账)
        with mock.patch.object(mod, "_handle_save_path_changes"), \
                mock.patch.object(mod, "_check_cross_group_file_conflicts"), \
                mock.patch.object(mod, "_check_download_conflicts"):
            mgr.events.emit("post", {"dry_run": True})
        assert mod._pending_assign == set(), "已删种子的补偿条目必须出清单"


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
            # removed_scan 自 26-11-07-0527 起为 grouping+maintenance 两家(后者清 auto_categories 残留)
            assert mgr.events.emit("removed_scan", {"hashes": ["H1"], "dry_run": False}) == 2
            removed.assert_called_once_with(["H1"], False)
            # post 自 S2 起 grouping+fuse 两家; dry_run=True 时 fuse 零动作
            assert mgr.events.emit("post", {"dry_run": True}) == 2
            save_path.assert_called_once_with(True)
            conflicts.assert_called_once_with(True)


# ---------- ops 服务(ctx.ops 直调) ----------


def test_ops_service_direct_call_and_inflight_mutex():
    """ctx.ops.recheck 直调可用(web 源); 重复提交受在途互斥(同一 _active_checks)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(td)
        mgr.client = FakeClient()
        t = FakeTorrent(hash="HA", state="pausedDL", progress=0.0)
        seed_store(mgr, [t])
        mgr.client.torrents["HA"] = t  # P1 提交点实时复核读客户端: 提交前种子必须在客户端(非 checking 态)
        # 直调: web 源提交 -> 在途登记(决策链 1.5 可见)
        r = mgr.ctx.ops.recheck("HA", source="web")
        assert r.is_ok, f"ctx.ops 直调应登记在途: {r}"
        assert "HA" in mgr.task_queue.active_check_hashes(), "ctx.ops 提交同样登记在途"
        # 重复提交: 在途互斥生效(同一 _active_checks)
        r2 = mgr.ctx.ops.recheck("HA", source="web")
        assert r2.is_skipped and "校验进行中" in r2.message, "重复提交受在途互斥"


def test_check_filelist_merged_into_ops():
    """checking 前置检查并入 ops(决策点 D2): ctx.ops.check_filelist 是唯一入口(实现本体)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(td)
        client = FakeClient()
        client.files = []  # 空 = 全部通过
        tor = FakeTorrent(hash="H1", save_path=r"R:\Downloads")
        assert mgr.ctx.ops.check_filelist(client, tor) is None


def test_p4_modules_sections_claims():
    """两模块 sections 认领清单锁定(P6 段认领完备守阵上线前的基线)"""
    assert GroupingModule(None).sections() == ("grouping", )
    assert OpsModule(None).sections() == ("skip_checking_tag", )
