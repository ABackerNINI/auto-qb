"""test_webui_boot_first_publish: 启动首轮提前发布基础视图(plan 26-11-18-0259 S1/S2)

钉 S1 验收判据(plan §04 S1 行): 启动首轮(落库前 store.rounds_applied == 0)在 apply_sync
落库后、full_round/归组之前, 经同一 on_sync_line hook(qbmanager._refresh_torrents 内
host.run_sync_line 复用发布单点 flush_views -> _publish_locked)先落一代"基础视图";
管线照常继续, 结束时既有收尾发布点落补全代。两形态全覆盖(S0 实测): 首请求抢先发布
空代(竞态形态)后判据仍为真、提前发布照常触发。

## 测试计划(每个测试函数一条)
- test_startup_first_round_publishes_base_generation_mid_pipeline: 启动首轮管线中恰一次发布,
  且该代已含落库种子(flat 全量 / singles 全量超集 / groups 空 / site=Unknown 证明早于
  full_round 的 tracker 匹配); 管线照常跑完(归组落 store), 客户端消费后收尾发布点落补全代
  (groups 落位 / singles 收缩 / site=HHan / ver 严格 +1)。
- test_preempting_empty_generation_does_not_skip_early_publish: 首请求抢先发布空代后,
  提前发布不因空代已存在而跳过(R3 竞态形态), 基础代照常落位且 rid 序列 +1。
- test_non_startup_full_rounds_keep_publish_rhythm: 非启动全量轮零行为变化 —— qB 重启补
  形态(reset_sync)与热重载 L2 形态(reset_runtime, 不清 rounds_applied)的刷新不产生
  提前发布, 收尾发布节奏与现状一致。
- test_early_publish_failure_does_not_break_pipeline: 提前发布失败只记 WARNING 不打断
  首轮管线(full_round/归组不丢), 收尾发布点照常落代(权威发布不被加速器拖累)。
### S2 守阵补齐(plan §04 S2 行: 只补 S1 未钉的缺面, 已钉面不重复)
- test_base_generation_lacks_site_derived_fields_completion_fills_them: 两代语义细面 ——
  基础代 site 派生面全空(site=Unknown / hr_tag="" / hr_triggered=False / hr_req_time=0);
  补全代 HR 派生字段落位(tracker_conf 匹配后现算: hr_tag 文本 / hr_triggered / hr_req_time);
  tracker 错误原因取数器在任务线(module.on_task_line advance_error_reasons -> flush_views),
  同步线两代里错误种子只有笼统回退「错误」(views._error_reason 兜底), 具体原因由任务线
  一代补齐(各占一代, ver 逐代 +1)。
- test_delta_client_two_generation_sequence_compatibility: delta 客户端"多吃一代"兼容面
  (R2) —— 两代序列下协商语义不破: 时间线恰两代 ver 严格连续(不跳不重, 管线中无中间代);
  rid==ver 零回传(带协商也不回数组); rid<ver 的补全代经组键迁移(R11)降级 full,
  协商客户端回 full=true + 数组(协议合法回退, 不含 delta/removed 键), 载荷 json 可序列化;
  未协商客户端历史形状逐键兼容(无 full/delta/removed); 补全代消费后一拍行级变化
  (delta_fields 速度字段)照常回增量(R5 键集) —— "rid<ver 回增量"在两代序列存活的时间线内成立。
"""

import json
import os
import tempfile
from unittest import mock

from helpers import FakeClient, FakeTorrent, _fake_file, _hr_rule, capture_logs, grouping_cfg, make_manager


def _boot_env(td, hr_tag="", errored=False):
    """启动轮环境: 2 枚同剧种子(同 save_path + 同文件名 -> 同组键), web 活跃

    hr_tag 非空 = 给 HHan 配 HR 规则(add_tag=hr_tag; FakeTorrent 默认字段 dlratio=1.0
    满足触发条件、seeding_time=0 未达标); errored = 追加一枚 error 态种子 H3
    (独立文件键成独立组, trackers_map 带报错条目 —— 供错误原因补齐面观察)。
    """
    client = FakeClient()
    client.torrents["H1"] = FakeTorrent(hash="H1", name="Boot Show 001 S01E01 1080p.bin", state="stalledUP")
    client.torrents["H2"] = FakeTorrent(hash="H2", name="Boot Show 001 S01E02 1080p.bin", state="stalledUP")
    client.files_map["H1"] = [_fake_file("movie.mkv", 100)]
    client.files_map["H2"] = [_fake_file("movie.mkv", 100)]
    if errored:
        client.torrents["H3"] = FakeTorrent(hash="H3", name="Boot Show 002 S01E01 1080p.bin", state="error")
        client.files_map["H3"] = [_fake_file("other.mkv", 100)]
        client.trackers_map["H3"] = [
            {
                "url": "https://tracker.hhanclub.net/announce.php",
                "status": 4,
                "msg": "torrent not registered",
            }
        ]
    mgr = make_manager(os.path.join(td, "state.json"), bare=True, grouping=grouping_cfg(), client=client)
    if hr_tag:
        mgr.config.trackers["HHan"].hr = _hr_rule(add_tag=hr_tag, add_category="", add_category_for_satisfied="")
    mgr.web.touch()  # Web 活跃(否则 flush_views 门控不发布, 提前发布无从观察)
    return mgr, client


def _snapshot(mgr):
    """一次发布后的四视图形状快照(同代同临界区, 「四视图同轮发布」铁律的观察面)"""
    return {
        "ver": mgr.web.group_view_ver,
        "flat": sorted(r["hash"] for r in mgr.web.flat_view),
        "singles": sorted(r["hash"] for r in mgr.web.singles_view),
        "group_rows": [r["key"] for r in mgr.web.group_view],
        "show_keys": sorted(r["key"] for r in mgr.web.shows_view["list"]),
        "sites": sorted(r["site"] for r in mgr.web.flat_view),
    }


def _spy_publishes(mgr):
    """包住 _publish_locked 记录每次发布后的形状快照(发布本身走真路径)"""
    snaps = []
    orig = mgr.web._publish_locked

    def spy():
        orig()
        snaps.append(_snapshot(mgr))

    return snaps, mock.patch.object(mgr.web, "_publish_locked", spy)


def test_startup_first_round_publishes_base_generation_mid_pipeline():
    """启动首轮: apply_sync 后即有含落库数据的基础代; 管线照常, 第二跳补全"""
    with tempfile.TemporaryDirectory() as td:
        mgr, _client = _boot_env(td)
        snaps, patcher = _spy_publishes(mgr)
        with patcher:
            mgr._refresh_torrents()  # 启动首轮(rounds_applied 落库前 == 0)
            assert len(snaps) == 1, f"管线中恰一次发布(提前发布; 收尾发布点在 _sync_line 尾段): {len(snaps)}"
            base = snaps[0]
            assert base["flat"] == ["H1", "H2"], "基础代 flat 全量(落库数据已可取)"
            assert base["singles"] == ["H1", "H2"], "基础代 singles 为全量超集(归组前全体未归组)"
            assert base["group_rows"] == [], "基础代 groups 空(组键依赖文件表, 内容问题非结构问题)"
            assert len(base["show_keys"]) == 1, "shows 按名称解析可给(两集同剧一行)"
            assert base["sites"] == ["Unknown", "Unknown"], ("早于 full_round 的 tracker 匹配(证明发布点在 need_validate 分支之前)")
            assert mgr.store.rounds_applied == 1
            # 管线照常继续: 归组在提前发布之后跑完(store 面)
            assert len(mgr.store.groups) == 1, "归组管线不被提前发布打断"
            assert sorted(next(iter(mgr.store.groups.values()))) == ["H1", "H2"]
            # 客户端取走基础代(消费即清) -> 收尾发布点(= _sync_line 尾段同款)落补全代
            mgr.web.ensure_state(rid=None)
            mgr.host.run_sync_line(False)
        assert len(snaps) == 2, "管线结束时既有发布点照常落第二跳"
        final = snaps[1]
        assert final["ver"] == base["ver"] + 1, "rid 序列正常 +1(每发布恰一代)"
        assert len(final["group_rows"]) == 1, "补全代归组行落位"
        assert final["singles"] == [], "补全代 singles 收缩(全量超集自愈)"
        assert final["sites"] == ["HHan", "HHan"], "tracker 字段补齐"
        assert final["flat"] == ["H1", "H2"], "flat 恒全量"


def test_preempting_empty_generation_does_not_skip_early_publish():
    """竞态形态(S0 探测轮): 首请求抢先发布空代 -> 提前发布照常触发落基础代"""
    with tempfile.TemporaryDirectory() as td:
        mgr, _client = _boot_env(td)
        # 首请求早于落库到达: ensure_state 发布 0 行空代并压住 dirty(S0 §02.2 第 3 点)
        empty = mgr.web.ensure_state(rid=None)
        assert empty["torrents"] == [] and empty["singles"] == [], "抢先请求拿到空代"
        ver_empty = mgr.web.group_view_ver
        snaps, patcher = _spy_publishes(mgr)
        with patcher:
            mgr._refresh_torrents()
            assert len(snaps) == 1, f"空代已存在不跳过提前发布(R3: 判据为真, 发布照常触发): {len(snaps)}"
            base = snaps[0]
            assert base["flat"] == ["H1", "H2"], "基础代含落库数据"
            assert base["ver"] == ver_empty + 1, "rid 序列正常 +1(空代与基础代各一代)"
            # 第二跳照常
            mgr.web.ensure_state(rid=None)
            mgr.host.run_sync_line(False)
            assert len(snaps) == 2 and len(snaps[1]["group_rows"]) == 1, "补全代照常落位"


def test_non_startup_full_rounds_keep_publish_rhythm():
    """非启动全量轮零行为变化: reset_sync / reset_runtime 形态都不提前发布"""
    with tempfile.TemporaryDirectory() as td:
        mgr, client = _boot_env(td)
        snaps, patcher = _spy_publishes(mgr)
        with patcher:
            mgr._refresh_torrents()  # 启动轮
            assert len(snaps) == 1
            mgr.web.ensure_state(rid=None)
            mgr.host.run_sync_line(False)  # 补全代
            boot_publishes = len(snaps)
            assert boot_publishes == 2

            # qB 重启补形态: rid 失效 -> 下轮全量, 但 rounds_applied 已 > 0
            client.torrents["H1"].state = "pausedUP"
            mgr.store.reset_sync()
            mgr._refresh_torrents()
            assert len(snaps) == boot_publishes, "非启动全量轮不产生提前发布"
            mgr.web.ensure_state(rid=None)
            mgr.host.run_sync_line(False)
            assert len(snaps) == boot_publishes + 1, "变化轮收尾发布照常(节奏与现状一致)"

            # 热重载 L2 形态: reset_runtime 不清 rounds_applied -> 仍不提前发布
            mgr.store.reset_runtime()
            mgr.store.reset_sync()
            mgr._refresh_torrents()
            assert len(snaps) == boot_publishes + 1, "热重载 L2 全量轮不产生提前发布"
            mgr.web.ensure_state(rid=None)
            mgr.host.run_sync_line(False)
            assert len(snaps) == boot_publishes + 2, "收尾发布照常"


def test_early_publish_failure_does_not_break_pipeline():
    """提前发布失败(构建抛错): 只记 WARNING, 首轮管线照常, 收尾发布点兜底"""
    with tempfile.TemporaryDirectory() as td:
        mgr, _client = _boot_env(td)
        orig = mgr.web._publish_locked
        calls = {"n": 0}

        def flaky():
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("early publish boom")
            orig()

        with mock.patch.object(mgr.web, "_publish_locked", flaky):
            with capture_logs("auto_qb.core.qbmanager") as logs:
                mgr._refresh_torrents()
            assert "提前发布视图失败" in logs.text, "失败要有 WARNING(可观测)"
            assert calls["n"] == 1, "管线内只有失败的提前发布一次尝试"
            assert len(mgr.store.groups) == 1, "归组管线不被提前发布失败打断(full_round/归组整段不丢)"
            # 收尾发布点照常兜底(权威发布不被加速器拖累; 失败后 dirty 仍为 True, 收尾照常落代)
            mgr.host.run_sync_line(False)
            assert calls["n"] == 2, "管线结束的既有发布点照常落代"
            assert len(mgr.web.group_view) == 1, "补全代内容完整"
            mgr.web.ensure_state(rid=None)  # 客户端取走该代(不触发新发布: dirty 已复位)
            assert calls["n"] == 2


def _rows(mgr):
    """当前已发布 flat 视图的 hash -> 行字典索引(行是发布期新建对象, 读值安全)"""
    return {r["hash"]: r for r in mgr.web.flat_view}


def test_base_generation_lacks_site_derived_fields_completion_fills_them():
    """两代语义细面(S2): 基础代 site 派生面全空(早于 full_round 的 tracker 匹配),
    补全代 HR 派生字段落位; tracker 错误原因取数器在任务线 —— 两代里错误种子只有笼统
    回退「错误」(状态自明面), 具体原因由任务线一代补齐

    机制: HR 展示字段与 site 都由 rec.tracker_conf 派生(views.hr_view_fields 在 conf=None
    时回全空值), 基础代发布点在 full_round/added 匹配之前 -> 全空是内容问题非结构问题;
    错误原因(tracker_error_msg)的唯一写点是 WebviewMixin.refresh_tracker_health, 挂在
    module.on_task_line(advance_error_reasons -> flush_views), 不在同步线管线内 ——
    _error_reason 在预取未跑时回退状态文本「错误」(views._error_reason 兜底),
    具体原因补齐自占一代, ver 逐代 +1。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr, _client = _boot_env(td, hr_tag="HR-3D", errored=True)
        mgr._refresh_torrents()  # 提前发布后管线照常跑完; 此刻当前代 = 基础代(收尾发布在 sync 线尾段)
        base = _rows(mgr)
        ver_base = mgr.web.group_view_ver
        assert base["H1"]["site"] == "Unknown", "基础代 tracker 未匹配(S1 已钉形状, 此处钉派生字段面)"
        assert base["H1"]["hr_tag"] == "" and base["H1"]["hr_triggered"] is False, "HR 展示字段全空(tracker_conf=None)"
        assert base["H1"]["hr_req_time"] == 0, "HR 要求值未派生(全空值字段的 0 哨兵)"
        assert base["H3"]["error_reason"] == "错误", "错误种子基础代只有笼统回退(预取未跑, tracker_error_msg 空)"
        # 补全代(同步线尾段既有发布点): HR 派生字段落位(先消费基础代 —— 「已取走」门控语义)
        mgr.web.ensure_state(rid=None)
        mgr.host.run_sync_line(False)
        final = _rows(mgr)
        assert final["H1"]["site"] == "HHan", "tracker 匹配后 site 补齐"
        assert final["H1"]["hr_tag"] == "HR-3D", "HR 标签文本按站点规则现算(与打标流程同源)"
        assert final["H1"]["hr_triggered"] is True, "本机触发判据落地(FakeTorrent 默认 dlratio=1.0 达线)"
        assert final["H1"]["hr_req_time"] == 3 * 86400 + 12 * 3600, "要求做种时长 = req + extra(_hr_rule 默认语义)"
        assert final["H3"]["error_reason"] == "错误", "同步线管线不预取错误原因(仍笼统回退; 取数器在任务线)"
        assert mgr.web.group_view_ver == ver_base + 1, "补全代恰 +1"
        # 任务线(生产 on_task_line 次序: 预取 -> 发布): 错误原因补齐, 又恰一代
        mgr.host.run_task_line(True)
        tasked = _rows(mgr)
        assert tasked["H3"]["error_reason"] == "torrent not registered", "错误原因经任务线预取补齐"
        assert mgr.web.group_view_ver == ver_base + 2, "任务线发布恰再 +1(rid 序列逐代单调)"


def test_delta_client_two_generation_sequence_compatibility():
    """delta 客户端"多吃一代"兼容面(R2): 两代序列下协商语义不破

    轮询消费面经 ensure_state(rid, view, delta=1) 钉三点: rid==ver 零回传; rid<ver 的
    补全代因组键迁移(R11)降级 full -> 协商客户端回 full=true + 数组(协议合法回退);
    其后一拍行级变化照常回增量。另钉: 时间线恰两代且 ver 严格连续(不跳不重)、
    未协商客户端历史形状逐键兼容、载荷 json 可序列化(端点 JSONResponse 直出同款)。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr, _client = _boot_env(td)
        mgr.web.touch()
        mgr._refresh_torrents()
        ver_base = mgr.web.group_view_ver
        # 启动首拉(协商客户端): rid=None -> 全量, 持基础代 rid(时间线只有基础代, 窗外必全量)
        first = mgr.web.ensure_state(None, "torrent", True)
        assert first["full"] is True and "torrents" in first, "首拉全量(协商客户端标 full)"
        assert "delta" not in first and "removed" not in first, "全量载荷不含增量键(R10)"
        assert first["rid"] == ver_base
        json.dumps(first, ensure_ascii=False)
        # 补全代落位: 时间线恰两代, ver 严格连续(管线中无中间代 —— rid 序列不跳不重)
        mgr.host.run_sync_line(False)
        ver_final = mgr.web.group_view_ver
        assert [e["ver"] for e in mgr.web._delta_timeline] == [ver_base, ver_final], "两代各恰一条目"
        assert ver_final == ver_base + 1
        # rid==ver 零回传: 版本一致只回 rid/updated, 带协商也不回数组(两代序列下语义不变)
        assert mgr.web.ensure_state(ver_final, "torrent", True) == {"rid": ver_final, "updated": False}
        # rid<ver: 窗口 = [补全代]; 归组新键登记迁移(R11) -> 本代 full -> 协商客户端回全量
        # (「多吃一代」的实际代价 = 补全代一次全量载荷, 协议兼容不破)
        second = mgr.web.ensure_state(ver_base, "torrent", True)
        assert second["rid"] == ver_final and second["updated"] is True
        assert second["full"] is True and "torrents" in second, "full 降级回数组"
        assert "delta" not in second and "removed" not in second
        json.dumps(second, ensure_ascii=False)
        # 未协商客户端(老前端): 历史形状逐键兼容 —— 无 full/delta/removed 键, 数组原样
        legacy = mgr.web.ensure_state(ver_base, "torrent")
        assert set(legacy.keys()) == {"rid", "updated", "torrents"}
        assert legacy["torrents"] == second["torrents"], "与协商全量同一份已发布视图"
        # 消费补全代后一拍**真实增量轮**(H1 速度变化经增量同步 -> _apply 推 delta_fields,
        # last_added 残值同轮被覆盖) -> rid<ver 回增量: "rid<ver 回增量"在两代序列存活的
        # 时间线内照常成立(补全代 full 条目只挡它之前的窗口)
        mgr.web.ensure_state(None, "torrent")  # 取走补全代(清「已取走」门控欠账)
        mgr.client.torrents["H1"].dlspeed = 512
        mgr._refresh_torrents()
        mgr.host.run_sync_line(False)
        ver_row = mgr.web.group_view_ver
        assert ver_row == ver_final + 1, "行级代仍严格 +1"
        third = mgr.web.ensure_state(ver_final, "torrent", True)
        assert third["full"] is False and third["rid"] == ver_row, "行级代归约命中"
        assert {r["hash"] for r in third["delta"]["torrents"]} == {"H1"}, "增量桶 = 变化行"
        assert third["removed"] == {"torrents": []}
        json.dumps(third, ensure_ascii=False)
