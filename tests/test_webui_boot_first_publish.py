"""test_webui_boot_first_publish: 启动首轮提前发布基础视图(plan 26-11-18-0259 S1)

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
"""

import os
import tempfile
from unittest import mock

from helpers import FakeClient, FakeTorrent, _fake_file, capture_logs, grouping_cfg, make_manager


def _boot_env(td):
    """启动轮环境: 2 枚同剧种子(同 save_path + 同文件名 -> 同组键), web 活跃"""
    client = FakeClient()
    client.torrents["H1"] = FakeTorrent(hash="H1", name="Boot Show 001 S01E01 1080p.bin", state="stalledUP")
    client.torrents["H2"] = FakeTorrent(hash="H2", name="Boot Show 001 S01E02 1080p.bin", state="stalledUP")
    client.files_map["H1"] = [_fake_file("movie.mkv", 100)]
    client.files_map["H2"] = [_fake_file("movie.mkv", 100)]
    mgr = make_manager(os.path.join(td, "state.json"), bare=True, grouping=grouping_cfg(), client=client)
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
