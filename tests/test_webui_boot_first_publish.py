"""test_webui_boot_first_publish: 启动首轮提前发布基础视图(plan 26-11-18-0259 S1/S2)

钉 S1 验收判据(plan §04 S1 行): 启动首轮(落库前 store.rounds_applied == 0)在 apply_sync
落库后、full_round/归组之前, 经同一 on_sync_line hook(qbmanager._refresh_torrents 内
host.run_sync_line 复用发布单点 flush_views -> _publish_locked)先落一代"基础视图";
管线照常继续, 结束时既有收尾发布点落补全代。两形态全覆盖(S0 实测): 首请求抢先发布
空代(竞态形态)后判据仍为真、提前发布照常触发。

## 测试计划(每个测试函数一条)
- test_startup_first_round_publishes_base_generation_mid_pipeline: 启动首轮管线中恰一次发布,
  且该代已含落库种子(flat 全量 / singles 全量超集 / groups 空 / site=HHan 为基础代纯内存
  推断名, 真 conf 未绑 + HR 派生字段空才证明早于 full_round 的 tracker 匹配); 管线照常
  跑完(归组落 store), 客户端消费后收尾发布点落补全代(groups 落位 / singles 收缩 /
  site=HHan / ver 严格 +1)。
- test_preempting_empty_generation_does_not_skip_early_publish: 首请求抢先发布空代后,
  提前发布不因空代已存在而跳过(R3 竞态形态), 基础代照常落位且 rid 序列 +1。
- test_non_startup_full_rounds_keep_publish_rhythm: 非启动全量轮零行为变化 —— qB 重启补
  形态(reset_sync)与热重载 L2 形态(reset_runtime, 不清 rounds_applied)的刷新不产生
  提前发布, 收尾发布节奏与现状一致。
- test_early_publish_failure_does_not_break_pipeline: 提前发布失败只记 WARNING 不打断
  首轮管线(full_round/归组不丢), 收尾发布点照常落代(权威发布不被加速器拖累)。
### S2 守阵补齐(plan §04 S2 行: 只补 S1 未钉的缺面, 已钉面不重复)
- test_base_generation_lacks_site_derived_fields_completion_fills_them: 两代语义细面 ——
  基础代站点名走廉价解析推断(site=HHan / site_provisional=True / site_alert=""), 但真 conf
  未绑故 HR 派生面全空(hr_tag="" / hr_triggered=False / hr_req_time=0)—— "早于 full_round"
  的证明从 site=Unknown 转移到 HR 空 + 临时态; 补全代 HR 派生字段落位(tracker_conf 匹配后
  现算: hr_tag 文本 / hr_triggered / hr_req_time);
  tracker 错误原因取数器在任务线(module.on_task_line advance_error_reasons -> flush_views),
  同步线两代里错误种子只有笼统回退「错误」(views._error_reason 兜底), 具体原因由任务线
  一代补齐(各占一代, ver 逐代 +1)。
- test_delta_client_two_generation_sequence_compatibility: delta 客户端"多吃一代"兼容面
  (R2) —— 两代序列下协商语义不破: 时间线恰两代 ver 严格连续(不跳不重, 管线中无中间代);
  rid==ver 零回传(带协商也不回数组); rid<ver 的补全代经组键迁移(R11)降级 full,
  协商客户端回 full=true + 数组(协议合法回退, 不含 delta/removed 键), 载荷 json 可序列化;
  未协商客户端历史形状逐键兼容(无 full/delta/removed); 补全代消费后一拍行级变化
  (delta_fields 速度字段)照常回增量(R5 键集) —— "rid<ver 回增量"在两代序列存活的时间线内成立。
- test_base_generation_provisional_site_inference: 基础代站点临时态分支(plan 26-11-23-1339 S1) ——
  纯内存从 rec.tracker 推断站点名: 命中已配 host 取 conf.tags[0]、tags 空走 conf.name、
  未配 host 保留 Unknown、虚拟 tracker 前缀跳过; 命中/未命中都清空 site_alert 且
  site_provisional=True(「尚未评估」而非「未配置」)。
- test_non_startup_round_site_provisional_false: 非启动轮(补全代)站点名由真 tracker_conf
  派生, site_provisional=False(临时态不串味)。
### S3 语义守阵收口(plan 26-11-23-1339 §04 S3 行: 补 S1/S2 尚未覆盖的语义面)
- test_unconfigured_site_alert_only_at_completion_generation: 真未配置站(域名不在 config)
  基础代临时态压 alert(空), 二拍真 match 仍 None 时按 _site_alert 报 no_site_conf;
  由另一枚已配种子绑定 conf 置脏驱动补全代发布。
- test_backup_tracker_site_residual_self_heals_at_completion: R1 备用 tracker 残差自愈 ——
  首 tracker host 未配 + 备条 hhan: 基础代只用 rec.tracker 落 Unknown + 临时态不告警,
  二拍真 match 用全量 tracker_urls 补齐 HHan。
- test_member_rows_consistent_across_four_views_under_provisional: R5 四视图成员行同代一致
  —— flat/singles/groups 成员/shows 剧行 e.members 经 memberByHash(flat 索引等价)解析行,
  逐视角断 site_provisional=True + 推断名一致; shows 剧行本体聚合字段不断言。
- test_base_generation_cheap_parse_never_binds_tracker_conf: R4 廉价解析只算展示值 —— 基础代
  site=HHan 但 rec.tracker_conf is None(HR 派生空见 :256-257 同族断言)。
- test_base_generation_makes_zero_qb_tracker_calls: R7 零 qB 调用计数桩 —— 基础代发布期
  torrents_trackers 调用数 0; 真 match 在前拍之后才拉 qB。
### 缺口修复守阵(26-11-23-1339 缺口: 全未配库/无 group_key_migrations 时临时态滞留)
- test_all_unconfigured_library_completion_clears_provisional: 两枚种子 trackers_map 全映射到
  未配域名 -> 无 matched_added / 无 torrents_added / 无 group_key_migrations, 非提前发布拍靠
  行字段判据补一次 full 重建: 两行翻 False + 真告警 no_site_conf; 静默拍不再多发布一代。
- test_provisional_settle_reaches_grouped_rows: 归组场景下主动 rebuild 出临时态代后, 结算拍
  的 full 重建覆盖到已归组种子的成员行(flat_view 判据不漏 groups 视角)。
- test_provisional_settlement_with_concurrent_delta_forces_full: 结算拍与行级增量同拍时 full
  必需 —— partial 只重建脏行, 未脏行原样复用(True 滞留且每拍重触发), full 才四视图整体翻假。
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


def _inject_trackers(mgr, url_by_hash):
    """apply_sync 后、启动首轮提前发布前, 给落库记录注入 rec.tracker

    tracker 是快照扩展字段(_EXTENSION_FIELDS), 不在 REQUIRED_TORRENT_FIELDS, 故
    FakeClient.sync_maindata 的字段表不带它 —— 直接注入 store 记录, 驱动真启动路径
    (_refresh_torrents -> run_sync_line -> flush_views -> _publish_locked -> _member_view)。
    """
    real_apply = mgr.store.apply_sync

    def apply_with_trackers(api):
        added, removed = real_apply(api)
        for h, url in url_by_hash.items():
            rec = mgr.store.by_hash.get(h)
            if rec is not None:
                rec.tracker = url
        return added, removed

    mgr.store.apply_sync = apply_with_trackers


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

    def spy(*args, **kwargs):
        orig(*args, **kwargs)
        snaps.append(_snapshot(mgr))

    return snaps, mock.patch.object(mgr.web, "_publish_locked", spy)


def test_startup_first_round_publishes_base_generation_mid_pipeline():
    """启动首轮: apply_sync 后即有含落库数据的基础代; 管线照常, 第二跳补全"""
    hhan_url = "https://tracker.hhanclub.net/announce.php"
    with tempfile.TemporaryDirectory() as td:
        mgr, _client = _boot_env(td)
        _inject_trackers(mgr, {"H1": hhan_url, "H2": hhan_url})
        snaps, patcher = _spy_publishes(mgr)
        with patcher:
            mgr._refresh_torrents()  # 启动首轮(rounds_applied 落库前 == 0)
            assert len(snaps) == 1, f"管线中恰一次发布(提前发布; 收尾发布点在 _sync_line 尾段): {len(snaps)}"
            base = snaps[0]
            assert base["flat"] == ["H1", "H2"], "基础代 flat 全量(落库数据已可取)"
            assert base["singles"] == ["H1", "H2"], "基础代 singles 为全量超集(归组前全体未归组)"
            assert base["group_rows"] == [], "基础代 groups 空(组键依赖文件表, 内容问题非结构问题)"
            assert len(base["show_keys"]) == 1, "shows 按名称解析可给(两集同剧一行)"
            assert base["sites"] == ["HHan", "HHan"], (
                "基础代纯内存推断名(命中已配 host 取 conf.tags[0]), 仍证明早于 full_round —— "
                "真 conf 未绑, 见 test_base_generation_lacks_site_derived_fields_completion_fills_them "
                "的 site_provisional=True / HR 派生全空断言"
            )
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

        def flaky(*args, **kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("early publish boom")
            orig(*args, **kwargs)

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
    """两代语义细面(S2 + 26-11-23-1339 S3 改写): 基础代站点名走廉价解析推断(site=HHan /
    site_provisional=True / site_alert=""), 但真 conf 未绑故 HR 派生面全空; 补全代 HR 派生
    字段落位; tracker 错误原因取数器在任务线 —— 两代里错误种子只有笼统回退「错误」(状态
    自明面), 具体原因由任务线一代补齐

    机制: site 在基础代由 rec.tracker 纯内存推断(plan 26-11-23-1339 S1), 补全代才由真
    tracker_conf 派生; HR 展示字段仍只由 rec.tracker_conf 派生(views.hr_view_fields 在
    conf=None 时回全空值), 基础代发布点在 full_round/added 匹配之前 -> HR 全空是内容问题
    非结构问题 —— "早于 full_round" 的证明从 site=Unknown 转移到 HR 空 + 临时态, 不再依赖
    Unknown; 错误原因(tracker_error_msg)的唯一写点是 WebviewMixin.refresh_tracker_health,
    挂在 module.on_task_line(advance_error_reasons -> flush_views), 不在同步线管线内 ——
    _error_reason 在预取未跑时回退状态文本「错误」(views._error_reason 兜底),
    具体原因补齐自占一代, ver 逐代 +1。
    """
    hhan_url = "https://tracker.hhanclub.net/announce.php"
    with tempfile.TemporaryDirectory() as td:
        mgr, _client = _boot_env(td, hr_tag="HR-3D", errored=True)
        _inject_trackers(mgr, {"H1": hhan_url, "H2": hhan_url})
        mgr._refresh_torrents()  # 提前发布后管线照常跑完; 此刻当前代 = 基础代(收尾发布在 sync 线尾段)
        base = _rows(mgr)
        ver_base = mgr.web.group_view_ver
        assert base["H1"]["site"] == "HHan", "基础代站点名由 rec.tracker 廉价解析推断(非 conf 派生)"
        assert base["H1"]["site_provisional"] is True, "基础代站点名为临时态(供前端压暗)"
        assert base["H1"]["site_alert"] == "" and base["H1"]["site_alert_msg"] == "", "临时态告警清空(尚未评估)"
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


def test_base_generation_provisional_site_inference():
    """基础代站点临时态分支(plan 26-11-23-1339 S1): 纯内存从 rec.tracker 推断站点名

    views_row._member_view 在 site_provisional=True 时不绑 rec.tracker_conf、不调 qB, 只按
    rec.tracker 的 hostname 精确匹配 config.trackers: 命中取 conf.tags[0](tags 空则 conf.name),
    未命中/虚拟 tracker 前缀("**"/"[DHT]"/"[PeX]"/"[LSD]")保留 r.tracker_name=Unknown;
    命中与否都清空 site_alert(「尚未评估」而非「未配置」), 且 site_provisional=True 供前端压暗。
    用 _inject_trackers 驱动真启动路径(_refresh_torrents 提前发布), 断言发布出的真实行值。
    """
    hhan_url = "https://tracker.hhanclub.net/announce.php"
    with tempfile.TemporaryDirectory() as td:
        # 1)已配 host 命中 -> conf.tags[0]=HHan, alert 空, 临时态标记 True
        mgr, _client = _boot_env(td)
        _inject_trackers(mgr, {"H1": hhan_url})
        mgr._refresh_torrents()  # 启动首轮: 基础代经真发布路径落位
        row = _rows(mgr)["H1"]
        assert row["site"] == "HHan", "命中已配 host: 纯内存推断取 conf.tags[0]=HHan"
        assert row["site_provisional"] is True, "基础代站点名是临时推断值(供前端压暗)"
        assert row["site_alert"] == "" and row["site_alert_msg"] == "", "临时态告警清空(尚未评估)"

    with tempfile.TemporaryDirectory() as td:
        # 2)未配 host -> 匹配未命中, 保留 Unknown, alert 空, 临时态标记 True
        mgr, _client = _boot_env(td)
        _inject_trackers(mgr, {"H1": "https://tracker.unconfigured.example/announce.php"})
        mgr._refresh_torrents()
        row = _rows(mgr)["H1"]
        assert row["site"] == "Unknown", "未配 host: 保留 rec.tracker_name=Unknown, 不臆造站点名"
        assert row["site_provisional"] is True
        assert row["site_alert"] == "" and row["site_alert_msg"] == "", "未命中同样清空告警"

    with tempfile.TemporaryDirectory() as td:
        # 3)虚拟 tracker 前缀 -> 跳过匹配, 保留 Unknown
        mgr, _client = _boot_env(td)
        _inject_trackers(mgr, {"H1": "[DHT]9abc"})
        mgr._refresh_torrents()
        row = _rows(mgr)["H1"]
        assert row["site"] == "Unknown", "虚拟 tracker 跳过 match, 保留 Unknown"
        assert row["site_provisional"] is True
        assert row["site_alert"] == ""

    with tempfile.TemporaryDirectory() as td:
        # 4)tags 空 -> conf.name(命中但无 tags 时回退站点配置名)
        mgr, _client = _boot_env(td)
        mgr.config.trackers["HHan"].tags = []
        _inject_trackers(mgr, {"H1": hhan_url})
        mgr._refresh_torrents()
        row = _rows(mgr)["H1"]
        assert row["site"] == "HHan", "tags 空: 推断名回退 conf.name=HHan"
        assert row["site_provisional"] is True


def test_non_startup_round_site_provisional_false():
    """非启动轮(补全代): 站点名由真 tracker_conf 派生, site_provisional=False(临时态不串味)"""
    with tempfile.TemporaryDirectory() as td:
        mgr, _client = _boot_env(td)
        _inject_trackers(mgr, {"H1": "https://tracker.hhanclub.net/announce.php"})
        mgr._refresh_torrents()  # 启动轮基础代: 临时态
        base = _rows(mgr)["H1"]
        assert base["site_provisional"] is True and base["site"] == "HHan", "基础代走临时态"
        # 消费基础代 -> 同步线尾段常规调用(不带 site_provisional)落补全代
        mgr.web.ensure_state(rid=None)
        mgr.host.run_sync_line(False)
        final = _rows(mgr)["H1"]
        assert final["site_provisional"] is False, "补全代临时态标记复位(False)"
        assert final["site"] == "HHan", "补全代站点名由真 tracker_conf 派生"


def test_unconfigured_site_alert_only_at_completion_generation():
    """真未配置站: 基础代临时态压告警(空), 第二拍真 match 仍 None 才报 no_site_conf

    域名 tracker.unconfigured.example 不在 config.trackers —— 廉价解析未命中, 基础代保留
    Unknown 但 site_provisional=True 且告警清空(「尚未评估」); 补全代真 match 用全量
    tracker_urls 仍匹配不到 -> rec.tracker_conf is None, _site_alert(views.py:334-337)见
    conf=None + 真实 tracker URL(非虚拟前缀) -> no_site_conf /「站点未在配置中」。
    补全代的发布由另一枚已配种子 H2 绑定 conf 置 view_changed 驱动 —— 若全库皆未配则无
    视图字段变化, 收尾 flush 不重建(见交付报告的实施发现), 故用混合场景钉真实守阵面。
    """
    hhan_url = "https://tracker.hhanclub.net/announce.php"
    unconf_url = "https://tracker.unconfigured.example/announce.php"
    with tempfile.TemporaryDirectory() as td:
        mgr, client = _boot_env(td)
        client.trackers_map["H1"] = [{"url": unconf_url}]
        client.trackers_map["H2"] = [{"url": hhan_url}]
        _inject_trackers(mgr, {"H1": unconf_url, "H2": hhan_url})
        mgr._refresh_torrents()
        base = _rows(mgr)
        ver_base = mgr.web.group_view_ver
        assert base["H1"]["site"] == "Unknown", "未配域名: 基础代保留 Unknown, 不臆造站点名"
        assert base["H1"]["site_provisional"] is True
        assert base["H1"]["site_alert"] == "" and base["H1"]["site_alert_msg"] == "", "基础代临时态压告警"
        assert base["H2"]["site"] == "HHan" and base["H2"]["site_alert"] == "", "已配站基础代同样无假告警"
        assert mgr.store.by_hash["H1"].tracker_conf is None, "基础代不绑 conf(廉价解析只算展示值)"

        mgr.web.ensure_state(rid=None)
        mgr.host.run_sync_line(False)
        final = _rows(mgr)
        assert mgr.web.group_view_ver == ver_base + 1, "补全代恰 +1"
        assert final["H1"]["site"] == "Unknown", "未配站补全代仍 Unknown(真 match 也未命中)"
        assert final["H1"]["site_provisional"] is False, "补全代临时态复位"
        assert final["H1"]["site_alert"] == "no_site_conf", "第二拍真告警: 未配置站报 no_site_conf"
        assert final["H1"]["site_alert_msg"] == "站点未在配置中", "告警文案按既有词表"
        assert final["H2"]["site"] == "HHan" and final["H2"]["site_alert"] == "", "已配站补全代常态无告警"


def test_backup_tracker_site_residual_self_heals_at_completion():
    """R1 备用 tracker 残差自愈: 首 host 未配 + 备条 hhan, 二拍用全量 URLs 补齐真名

    基础代 _member_view 只把 rec.tracker(首个 URL)喂 match_tracker_confs -> 未命中落 Unknown
    + 临时态不告警(接受基础代残差, 与 0269 两跳语义一致); 补全代 tracker_mod.match 用
    rec.tracker_urls(client)(trackers_map 全量两条) -> 备条 hhan 命中, 站点名 HHan、
    site_provisional 复位。
    """
    first_url = "https://tracker.unconfigured-first.example/announce.php"
    backup_url = "https://tracker.hhanclub.net/announce.php"
    with tempfile.TemporaryDirectory() as td:
        mgr, client = _boot_env(td)
        client.trackers_map["H1"] = [{"url": first_url}, {"url": backup_url}]
        client.trackers_map["H2"] = [{"url": first_url}, {"url": backup_url}]
        _inject_trackers(mgr, {"H1": first_url, "H2": first_url})
        mgr._refresh_torrents()
        base = _rows(mgr)["H1"]
        assert base["site"] == "Unknown", "基础代只用首 tracker(未配) -> Unknown 残差"
        assert base["site_provisional"] is True
        assert base["site_alert"] == "", "残差也不告警(临时态压)"

        mgr.web.ensure_state(rid=None)
        mgr.host.run_sync_line(False)
        final = _rows(mgr)["H1"]
        assert final["site"] == "HHan", "二拍真 match 用全量 tracker_urls, 备条 hhan 命中补齐"
        assert final["site_provisional"] is False
        assert final["site_alert"] == "", "备条已配 -> 无 no_site_conf"


def test_member_rows_consistent_across_four_views_under_provisional():
    """R5 四视图成员行同代一致: 逐视角断 site_provisional 与推断名一致

    flat/singles 行本身即 _member_view; groups 成员 / shows 剧行 e.members 只带 hash, 经
    memberByHash(前端 decorate.js:549-554 从 groups U singles U torrents 建索引; 此处以
    flat_view = torrents 全量 SEED_ITEM 作等价索引)解析出同一份 _member_view 行。shows 剧行
    本体的 node['sites'] 聚合字段前端未消费(views_episodes.py:45-46), 按 plan R5 不断言。
    真启动路径基础代 groups 空(组键依赖文件表, 归组在 full_round 后), 另在归组落位后经
    rebuild_views(site_provisional=True)再取一代临时态, 覆盖 groups 成员视角。
    """
    hhan_url = "https://tracker.hhanclub.net/announce.php"

    def collect(mgr, index):
        views = {"flat": [], "singles": [], "groups": [], "shows": []}
        for r in mgr.web.flat_view:
            views["flat"].append(index[r["hash"]])
        for r in mgr.web.singles_view:
            views["singles"].append(index[r["hash"]])
        for g in mgr.web.group_view:
            for h in g["members"]:
                views["groups"].append(index[h])
        for show in mgr.web.shows_view["list"]:
            for season in show["seasons"]:
                for ep in season["episodes"]:
                    for h in ep["members"]:
                        views["shows"].append(index[h])
        return views

    with tempfile.TemporaryDirectory() as td:
        mgr, _client = _boot_env(td)
        _inject_trackers(mgr, {"H1": hhan_url, "H2": hhan_url})
        mgr._refresh_torrents()  # 当前代 = 真启动路径基础代(临时态)

        base = collect(mgr, _rows(mgr))
        assert base["groups"] == [], "基础代 groups 空(归组在 full_round 后)"
        for name in ("flat", "singles", "shows"):
            assert base[name], f"基础代 {name} 视角应有成员行"
            for row in base[name]:
                assert row["site_provisional"] is True, f"基础代 {name} 成员行临时态一致"
                assert row["site"] == "HHan", f"基础代 {name} 成员行推断名一致"
        # shows 剧行本体的 node['sites'] 聚合(此时代仍为 ['Unknown'])按 R5 不断言

        mgr.web.ensure_state(rid=None)
        mgr.host.run_sync_line(False)  # 补全代: 归组落位
        mgr.web.rebuild_views(site_provisional=True)  # 归组后再取一代临时态, 覆盖 groups 成员视角
        provisional = collect(mgr, _rows(mgr))
        assert provisional["flat"] and provisional["groups"] and provisional["shows"], "临时态代四视角成员行齐备"
        # singles 在归组落位后恒空(全体已归组), 无成员行可查 —— 非空视角逐行断同代一致
        for name, rows in provisional.items():
            for row in rows:
                assert row["site_provisional"] is True, f"临时态代 {name} 成员行临时态一致"
                assert row["site"] == "HHan", f"临时态代 {name} 成员行推断名一致"


def test_base_generation_cheap_parse_never_binds_tracker_conf():
    """R4 廉价解析不误绑 conf: 基础代 site=HHan 但 rec.tracker_conf is None

    设计底线只算展示值 —— 若把 match_tracker_confs 结果写回 rec.tracker_conf, 会带上规则 /
    HR / 限速副作用, 且等于把真匹配挪前抵消提前发布。这里在基础代发布后直接查 store 记录:
    推断名已出、conf 仍未绑(HR 派生字段全空见
    test_base_generation_lacks_site_derived_fields_completion_fills_them 的同族断言)。
    """
    hhan_url = "https://tracker.hhanclub.net/announce.php"
    with tempfile.TemporaryDirectory() as td:
        mgr, _client = _boot_env(td)
        _inject_trackers(mgr, {"H1": hhan_url, "H2": hhan_url})
        state_at_publish = []
        real_publish = mgr.web._publish_locked

        def spy(*args, **kwargs):
            real_publish(*args, **kwargs)
            # 必须在此刻采: full_round 在提前发布之后跑, 到 _refresh_torrents 返回时 conf 早已绑上
            state_at_publish.append((_rows(mgr)["H1"]["site"], mgr.store.by_hash["H1"].tracker_conf))

        with mock.patch.object(mgr.web, "_publish_locked", spy):
            mgr._refresh_torrents()
        assert state_at_publish == [("HHan", None)], "基础代发布当刻: 推断名已出但 rec.tracker_conf 仍 None"


def test_base_generation_makes_zero_qb_tracker_calls():
    """R7 基础代零 qB tracker 调用: 纯内存廉价解析不触发 torrents_trackers

    计数桩包 client.torrents_trackers, 在 _publish_locked 出口采当前累计调用数: 启动首轮
    管线中唯一一次发布(基础代)时计数必须为 0; 真 match 发生在提前发布之后的 full_round,
    此时才拉 qB —— 只钉「基础代 = 0」不变量, 不钉补全代具体调用次数(随实现变化)。
    """
    hhan_url = "https://tracker.hhanclub.net/announce.php"
    with tempfile.TemporaryDirectory() as td:
        mgr, client = _boot_env(td)
        _inject_trackers(mgr, {"H1": hhan_url, "H2": hhan_url})
        tracker_calls = []
        calls_at_publish = []
        real_trackers = client.torrents_trackers

        def counting(h):
            tracker_calls.append(h)
            return real_trackers(h)

        real_publish = mgr.web._publish_locked

        def spy(*args, **kwargs):
            real_publish(*args, **kwargs)
            calls_at_publish.append(len(tracker_calls))

        with mock.patch.object(client, "torrents_trackers",
                               counting), mock.patch.object(mgr.web, "_publish_locked", spy):
            mgr._refresh_torrents()
            assert len(calls_at_publish) == 1, "启动首轮管线中恰一次发布(基础代)"
            assert calls_at_publish[0] == 0, "基础代纯内存推断, 零 torrents_trackers 调用"
            assert tracker_calls, "真 match 在提前发布之后的 full_round 才拉 qB"


def test_all_unconfigured_library_completion_clears_provisional():
    """全未配库结算缺口(26-11-23-1339 缺口修复): 所有种子 tracker 都不在 config 时,
    基础代 site_provisional=True + 空告警不会因 view_changed/组键迁移而滞留 —— flush 的
    非提前发布拍用行字段判据补一次 full 重建, 把行翻 False 并按真 conf 重算 no_site_conf。

    FakeClient.torrents_trackers 未命中 trackers_map 时默认回 HHan URL(helpers.py:122-125),
    故必须显式把 H1/H2 的 trackers_map 都映射到未配域名 —— 否则真 match 会绑上 conf、
    缺陷被掩盖, 测试假绿。根因链: 全未配 -> conf 全 None -> matched_added 空 -> 无
    torrents_added 广播 -> 无 group_key_migrations -> flush 的 view_changed 已被提前发布
    消费 -> _pending_full_reasons 空 -> 不置脏 -> 不重建 -> 临时态与空告警永久滞留。
    """
    unconf_url = "https://tracker.unconfigured.example/announce.php"
    with tempfile.TemporaryDirectory() as td:
        mgr, client = _boot_env(td)
        # 显式覆盖**所有**种子: full_round 真 match 也全部落 None(无 matched_added/迁移)
        client.trackers_map["H1"] = [{"url": unconf_url}]
        client.trackers_map["H2"] = [{"url": unconf_url}]
        _inject_trackers(mgr, {"H1": unconf_url, "H2": unconf_url})
        mgr._refresh_torrents()  # 启动首轮: 提前发布基础代, 之后 full_round 全未配

        base = _rows(mgr)
        base_ver = mgr.web.group_view_ver
        for h in ("H1", "H2"):
            assert base[h]["site"] == "Unknown", f"{h} 基础代未配域名保留 Unknown, 不臆造站点名"
            assert base[h]["site_provisional"] is True, f"{h} 基础代临时态"
            assert base[h]["site_alert"] == "" and base[h]["site_alert_msg"] == "", f"{h} 基础代临时态压告警"
        assert mgr.store.by_hash["H1"].tracker_conf is None, "基础代不绑 conf(廉价解析只算展示值)"

        # 客户端取走基础代 -> 非提前发布拍: 无 view_changed / 无迁移, 全靠结算判据补 full
        mgr.web.ensure_state(rid=None)
        mgr.host.run_sync_line(False)
        final = _rows(mgr)
        assert mgr.web.group_view_ver == base_ver + 1, "结算恰补一代(不多发布)"
        for h in ("H1", "H2"):
            assert final[h]["site_provisional"] is False, f"{h} 补全代临时态复位"
            assert final[h]["site_alert"] == "no_site_conf", f"{h} 补全代真告警"
            assert final[h]["site_alert_msg"] == "站点未在配置中", f"{h} 告警文案按既有词表"
        assert all(mgr.store.by_hash[h].tracker_conf is None for h in ("H1", "H2")), \
            "真告警源自 conf=None(非误绑)—— 证明是真告警而非假绑定"

        # 反向风险: 再跑一拍静默同步, 判据翻 False 后自灭, 不应每拍多发布一代
        mgr.web.ensure_state(rid=None)
        mgr.host.run_sync_line(False)
        assert mgr.web.group_view_ver == base_ver + 1, "静默拍不再发布(判据自灭, 幂等)"


def test_provisional_settle_reaches_grouped_rows():
    """归组场景结算面: 已配种子驱动 group_key_migrations 正常落组后, 主动 rebuild 出
    临时态代, 结算拍的 full 重建必须覆盖到已归组种子的成员行(flat_view 判据不漏
    groups 视角 —— 归组后 singles 空, 若误用 singles 作判据会假阴性)。
    """
    hhan_url = "https://tracker.hhanclub.net/announce.php"
    with tempfile.TemporaryDirectory() as td:
        mgr, _client = _boot_env(td)
        _inject_trackers(mgr, {"H1": hhan_url, "H2": hhan_url})
        mgr._refresh_torrents()
        mgr.web.ensure_state(rid=None)
        mgr.host.run_sync_line(False)  # 补全代: 归组落位
        assert len(mgr.web.group_view) == 1, "hhan 种子已归组(H2 绑 conf 驱动迁移)"

        # 归组后主动取一代临时态(参考 :536 写法), host 侧标记 True 写进四视图成员行
        mgr.web.rebuild_views(site_provisional=True)
        provisional = _rows(mgr)
        assert all(r["site_provisional"] is True for r in provisional.values()), "临时态代全部行 True"
        assert all(r["hash"] in mgr.store.member_to_key for r in provisional.values()), \
            "两枚种子均已归组(flat 行即组行成员行的同源对象)"

        # 结算拍: 非提前发布 flush 见 flat_view 有 True 行 -> full 重建, 翻 False
        mgr.web.ensure_state(rid=None)
        mgr.host.run_sync_line(False)
        settled = _rows(mgr)
        assert all(r["site_provisional"] is False for r in settled.values()), "结算后已归组行全部翻 False"
        assert len(mgr.web.group_view) == 1, "结算 full 重建后组行仍在(不丢归组)"
        assert all(r["site"] == "HHan" for r in settled.values()), "结算后站点名由真 conf 派生"


def test_provisional_settlement_with_concurrent_delta_forces_full():
    """结算拍与行级增量同拍: 必须 full, 不能 mark_dirty()(partial)

    partial 路径只重建脏行, 未脏行对象原样复用(_merge_rows 的引用稳定契约)—— 这里只让
    H1 速度变化成为脏行, H2 未脏: 若结算只 mark_dirty() 走 partial, H2 的 site_provisional
    仍是 True(判据不灭, 每拍重触发); full=True 强制四视图整体重建才把 H2 也翻 False。
    """
    hhan_url = "https://tracker.hhanclub.net/announce.php"
    with tempfile.TemporaryDirectory() as td:
        mgr, client = _boot_env(td)
        _inject_trackers(mgr, {"H1": hhan_url, "H2": hhan_url})
        mgr._refresh_torrents()
        mgr.web.ensure_state(rid=None)
        mgr.host.run_sync_line(False)  # 补全代: 归组落位 + 临时态 False
        mgr.web.rebuild_views(site_provisional=True)  # 主动取一代临时态(仅 H1 后续会脏)
        assert all(r["site_provisional"] is True for r in _rows(mgr).values())
        mgr.web.ensure_state(rid=None)  # 消费, 放开门控

        client.torrents["H1"].dlspeed = 512  # 只有 H1 产生行级增量键, H2 未脏
        mgr._refresh_torrents()  # 非启动轮: 无提前发布, 仅 apply
        mgr.host.run_sync_line(False)  # 结算拍: 同带 H1 行级键(partial 与 full 的分叉点)
        settled = _rows(mgr)
        assert settled["H1"]["site_provisional"] is False, "脏行翻 False(partial 也会重建它)"
        assert settled["H2"]["site_provisional"] is False, \
            "未脏行也必须翻 False —— 证明确实走了 full 而非 partial(partial 原样复用 True 行)"
