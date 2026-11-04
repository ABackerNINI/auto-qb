"""test_fuse_mod 测试计划: 已完成种子下载保险丝三态状态机(S2) + 触发标签(S3), 不连接真实 qB

## 测试计划(每个测试函数一条)
- test_fuse_arm_writes_fence_once: 完成+dl_limit==0 -> 一次批量写哨兵; 再扫零写(幂等)
- test_fuse_armed_transient_zero_limit_recovers: 偶发 0 一拍 -> 补齐一次回流后计数清零不升级
- test_fuse_armed_zero_limit_yields_after_rearm_ticks: 哨兵持续 0 连续 3 拍 -> 让位转 released 不再互写
- test_fuse_arm_only_complete_zero_limit: 未完成/校验中/已有非零限速 -> 不写不建条目
- test_fuse_trigger_after_confirm_ticks: 连续 N 拍 dlspeed>0 -> 一次批量 pause, 状态 triggered 带原因
- test_fuse_zero_speed_never_triggers: 恒 0 连击不累积、不暂停(不误伤)
- test_fuse_triggered_repause_on_external_start: triggered 被外部启动且 own_write 已回流 -> 再暂停一次
- test_fuse_triggered_no_duplicate_within_own_write: own_write 未回流期间不重复下发暂停(幂等)
- test_fuse_release_cas_restores_pre_limit: 放行 CAS 成立 -> 恢复 orig_limit(0) 且标 released, 不 resume
- test_fuse_release_cas_failed_only_marks: 放行时限速已被外部改 -> 零写只标 released
- test_fuse_release_all_batches: release(None) 批量放行全部条目并恢复限速; 触发拍汇总 WARNING 恰一条
- test_fuse_release_unknown_hash_noop: 放行不存在的 hash -> 0 且零写
- test_fuse_release_dry_run_zero_writes: release(dry_run=True) -> 返回命中数但零 qB 调用、状态不变
- test_fuse_release_then_rearm_after_refill: released 不立即重武装; 离开完成态再完成后才武装
- test_fuse_enabled_false_zero_side_effect: enabled=false -> 零 qB 写、不建 state 域
- test_fuse_dry_run_zero_writes: dry-run -> 零 qB 写、不建 state 域
- test_fuse_state_lost_adopt: 条目缺失但 dl_limit==fence+完成 -> adopt armed 零写(orig_limit 假定 0)
- test_fuse_state_lost_no_adopt_other_limit: 条目缺失且非 fence 非零限速 -> 只监控不写
- test_fuse_removed_torrent_drops_entry: 种子消失 -> 条目删除
- test_fuse_monitor_only_pauses_without_entry: 非零限速完成种子无条目, N 拍后暂停并建 triggered 条目
- test_fuse_sections_and_kernel_migration: sections 认领 download_fuse 且已从 KERNEL_SECTIONS 迁出
- test_fuse_trigger_adds_tag_batch_once: 同拍触发 2 个 -> 加标签仅 1 次批量请求, 二拍零调用
- test_fuse_release_removes_tag_after_limit_write: 放行先恢复限速再摘标签, 单次批量请求
- test_fuse_release_all_removes_tags_and_idempotent: 批量放行一次摘标签; 二次放行零请求
- test_fuse_external_tag_removal_not_readded: 标签被外部移除只记日志, 不重加, 条目仍 triggered
- test_fuse_adopt_tagged_paused_is_triggered: 完成+fence+暂停+标签 -> adopt 重建 triggered 零写
- test_fuse_adopt_fence_without_tag_is_armed: 完成+fence 无标签 -> 仍重建 armed(标签不重加)
- test_fuse_tag_reuse_warns_once_without_extra_request: 同名标签已被使用 -> 启动一条 WARNING, 不建标签定义
- test_fuse_release_cli_syncs_snapshot_before_cas: CLI 放行先同步 store 快照再调 release(CAS 才读得到当前限速); 非 dry-run 落盘、dry-run 不落盘; 显式列表 0 命中返回 False
- test_fuse_start_sets_dry_run_and_stop_clears_streak: start 记模块级 dry-run(零动作零 state), stop 清连击缓存
- test_fuse_dependency_missing_early_return: api 依赖缺失 -> 整拍早退, 零写零 state 域
- test_fuse_armed_refence_idempotent_after_external_clear: armed 下 dl_limit 被外部清零 -> 幂等补写哨兵
- test_fuse_armed_external_limit_change_released_no_writeback: armed 下限速被外部改值 -> 转 released 不写回
- test_fuse_unknown_status_entry_dropped: 条目状态未知(历史脏数据) -> 丢弃后按无条目重新判定
- test_fuse_release_state_service_none_returns_zero: state 服务缺失 -> release 返回 0
- test_fuse_release_no_entries_return_zero: state 域缺失/entries 空/域非 dict -> release 返回 0
- test_fuse_release_without_connection_marks_only_with_warning: 放行时未连接 qB -> 告警且只标 released 不写限速
- test_fuse_release_dry_run_prints_plan_only: dry-run 放行 -> 打印计划, 零写零改状态
- test_fuse_release_untag_skipped_when_tag_gone: 放行时标签已被外部移除 -> 不发摘标签请求, 无汇总日志
- test_fuse_release_untag_skipped_when_client_none: 放行时 api.client 已断 -> 摘标签路径安全降级(零请求/告警/只标 released), 不 AttributeError
- test_fuse_monitor_trigger_already_tagged_zero_requests: 触发时快照已带标签 -> 加标签零请求且无打标签日志
- test_fuse_tag_apply_helpers_tolerate_missing_entries: 标签批量助手直驱 entries 缺 hash/rec 无标签 -> 防御假两侧不炸
"""

from unittest import mock

from auto_qb.config.impact import KERNEL_SECTIONS

from auto_qb.config.models import DownloadFuseConfig

from helpers import FakeClient, FakeTorrent, capture_logs, make_manager, seed_store

FENCE = 13 * 1024
TICKS = 3


def _mgr(tmp_path, **fuse_kw):
    """装配只带保险丝段的管理器(bool 默认开, 其余与生产默认一致)"""
    fuse_kw.setdefault("enabled", True)
    fuse_kw.setdefault("download_limit", FENCE)
    fuse_kw.setdefault("confirm_ticks", TICKS)
    client = FakeClient()
    mgr = make_manager(
        str(tmp_path / "state.json"), bare=True, download_fuse=DownloadFuseConfig(**fuse_kw), client=client
    )
    return mgr, client


def _tor(h, **kw):
    """完成态种子替身(默认: 已下完/空闲/不限速)"""
    base = dict(hash=h, name=h, state="stalledUP", progress=1.0, amount_left=0, dl_limit=0, dlspeed=0)
    base.update(kw)
    return FakeTorrent(**base)


def _tick(mgr, dry_run=False):
    mgr.events.emit("post", {"dry_run": dry_run})


def _set_calls(client):
    return [c for c in client.calls if c[0] == "set_download_limit"]


def _pause_calls(client):
    return [c for c in client.calls if c[0] == "pause"]


def _entries(mgr):
    return mgr.ctx.state.data.get("download_fuse", {}).get("entries", {})


def test_fuse_arm_writes_fence_once(tmp_path):
    mgr, client = _mgr(tmp_path)
    tor = _tor("a" * 40)
    seed_store(mgr, [tor])
    _tick(mgr)
    calls = _set_calls(client)
    assert len(calls) == 1 and calls[0][1] == FENCE
    ent = _entries(mgr)["a" * 40]
    assert ent["status"] == "armed" and ent["fence"] == FENCE and ent["orig_limit"] == 0
    assert tor.dl_limit == FENCE, "Facade 写后应回写快照, 下轮据 dl_limit==fence 短路"
    _tick(mgr)
    assert len(_set_calls(client)) == 1, "值未变不重复写(幂等)"


def test_fuse_armed_transient_zero_limit_recovers(tmp_path):
    """偶发 0(上一拍写失败未回流) -> 补齐一次, 哨兵回流后计数清零, 不升级 released"""
    mgr, client = _mgr(tmp_path)
    tor = _tor("y" * 40)
    seed_store(mgr, [tor])
    _tick(mgr)
    tor.dl_limit = 0  # 模拟写失败: 快照没回流哨兵
    with capture_logs("auto_qb.core.modules.fuse_mod") as cap:
        _tick(mgr)
    assert len(_set_calls(client)) == 2 and tor.dl_limit == FENCE, "补齐一次成功回流"
    assert [m for m in cap.messages if "dl_limit==0" in m], "补齐留 WARNING 痕迹(不与外部静默互写)"
    _tick(mgr)  # 哨兵已在场: 计数清零, 零写
    assert len(_set_calls(client)) == 2
    ent = _entries(mgr)["y" * 40]
    assert ent["status"] == "armed" and ent["rearm"] == 0


def test_fuse_armed_zero_limit_yields_after_rearm_ticks(tmp_path):
    """哨兵持续为 0 连续 _REARM_YIELD 拍(写失败或被外部清零) -> 让位转 released, 不再互写"""
    mgr, client = _mgr(tmp_path)
    tor = _tor("x" * 40)
    seed_store(mgr, [tor])
    _tick(mgr)
    assert tor.dl_limit == FENCE, "首次武装写入(facade 回写快照)"
    with capture_logs("auto_qb.core.modules.fuse_mod") as cap:
        for _ in range(3):
            tor.dl_limit = 0  # 模拟用户每拍把哨兵清回不限速
            _tick(mgr)
    assert len(_set_calls(client)) == 3, "武装 1 次 + 补齐 2 次; 第 3 拍让位零写"
    assert tor.dl_limit == 0, "让位后不再回写哨兵(不与用户操作打架)"
    assert _entries(mgr)["x" * 40]["status"] == "released"
    assert [m for m in cap.messages if "让位转 released" in m], "让位留 WARNING 痕迹"


def test_fuse_arm_only_complete_zero_limit(tmp_path):
    mgr, client = _mgr(tmp_path)
    seed_store(
        mgr, [
            _tor("b" * 40, progress=0.5, amount_left=1024),
            _tor("c" * 40, state="checkingDL"),
            _tor("d" * 40, dl_limit=512 * 1024),
        ]
    )
    _tick(mgr)
    assert _set_calls(client) == []
    assert _entries(mgr) == {}


def test_fuse_trigger_after_confirm_ticks(tmp_path):
    mgr, client = _mgr(tmp_path)
    tor = _tor("e" * 40, dlspeed=1000)
    seed_store(mgr, [tor])
    _tick(mgr)  # 本轮只武装, 不计连击
    assert _pause_calls(client) == []
    for _ in range(TICKS):
        _tick(mgr)
    assert _pause_calls(client) == [("pause", ["e" * 40])]
    ent = _entries(mgr)["e" * 40]
    assert ent["status"] == "triggered" and ent["confirm_count"] == TICKS
    assert ent.get("reason"), "触发要记原因"


def test_fuse_zero_speed_never_triggers(tmp_path):
    mgr, client = _mgr(tmp_path)
    tor = _tor("f" * 40)
    seed_store(mgr, [tor])
    for _ in range(10):
        _tick(mgr)
    assert _pause_calls(client) == []
    assert _entries(mgr)["f" * 40]["confirm_count"] == 0


def test_fuse_triggered_repause_on_external_start(tmp_path):
    mgr, client = _mgr(tmp_path)
    tor = _tor("g" * 40, dlspeed=1000)
    seed_store(mgr, [tor])
    _tick(mgr)
    for _ in range(TICKS):
        _tick(mgr)
    assert len(_pause_calls(client)) == 1
    # 模拟同步回流清空 own_write + 外部启动(state 回活跃/有速度)
    mgr.store.own_writes.clear()
    tor.state = "stalledUP"
    tor.dlspeed = 2000
    _tick(mgr)
    assert len(_pause_calls(client)) == 2, "被外部启动应再暂停一次"


def test_fuse_triggered_no_duplicate_within_own_write(tmp_path):
    mgr, client = _mgr(tmp_path)
    tor = _tor("h" * 40, dlspeed=1000)
    seed_store(mgr, [tor])
    _tick(mgr)
    for _ in range(TICKS):
        _tick(mgr)
    first = len(_pause_calls(client))
    assert first == 1
    _tick(mgr)
    assert len(_pause_calls(client)) == first, "own_write 未回流期间不重复下发"


def test_fuse_release_cas_restores_pre_limit(tmp_path):
    mgr, client = _mgr(tmp_path)
    tor = _tor("i" * 40)
    seed_store(mgr, [tor])
    _tick(mgr)
    assert mgr.ctx.fuse.release(["i" * 40]) == 1
    assert _set_calls(client)[-1][1] == 0, "CAS 成立应写回 orig_limit(0)"
    assert _entries(mgr)["i" * 40]["status"] == "released"
    assert [c for c in client.calls if c[0] == "resume"] == [], "放行不自动 resume"


def test_fuse_release_cas_failed_only_marks(tmp_path):
    mgr, client = _mgr(tmp_path)
    tor = _tor("j" * 40)
    seed_store(mgr, [tor])
    _tick(mgr)
    before = len(_set_calls(client))
    tor.dl_limit = 512 * 1024  # 模拟外部接管限速(当前值已不是哨兵)
    assert mgr.ctx.fuse.release(["j" * 40]) == 1
    assert len(_set_calls(client)) == before, "CAS 不成立只标记不覆盖"
    assert _entries(mgr)["j" * 40]["status"] == "released"


def test_fuse_release_all_batches(tmp_path):
    mgr, client = _mgr(tmp_path)
    tori = [_tor("k" * 40, dlspeed=1000), _tor("l" * 40, dlspeed=1000)]
    seed_store(mgr, tori)
    _tick(mgr)
    with capture_logs("auto_qb.core.modules.fuse_mod") as cap:
        for _ in range(TICKS):
            _tick(mgr)
    assert len(_pause_calls(client)) == 1 and len(_pause_calls(client)[0][1]) == 2
    assert len([m for m in cap.messages if "paused 2 torrents (batch)" in m]) == 1, \
        "批量触发汇总 WARNING 每拍最多一条(§3.5, 不逐条刷屏)"
    assert mgr.ctx.fuse.release(None) == 2
    last = _set_calls(client)[-1]
    assert last[1] == 0
    hashes = [h for kind, h in client.limit_location_hashes_calls if kind == "set_download_limit"][-1]
    assert set(hashes) == {"k" * 40, "l" * 40}
    assert {ent["status"] for ent in _entries(mgr).values()} == {"released"}


def test_fuse_release_unknown_hash_noop(tmp_path):
    mgr, client = _mgr(tmp_path)
    seed_store(mgr, [_tor("m" * 40)])
    _tick(mgr)
    before = len(_set_calls(client))
    assert mgr.ctx.fuse.release(["n" * 40]) == 0
    assert len(_set_calls(client)) == before


def test_fuse_release_dry_run_zero_writes(tmp_path):
    """release(dry_run=True) -> 返回命中数但零 qB 调用、不置 released(§10 所有 fuse 方法零写)"""
    mgr, client = _mgr(tmp_path)
    tor = _tor("w" * 40, dlspeed=1000)
    seed_store(mgr, [tor])
    _tick(mgr)
    for _ in range(TICKS):
        _tick(mgr)
    ent = _entries(mgr)["w" * 40]
    assert ent["status"] == "triggered"
    before = len(client.calls)
    assert mgr.ctx.fuse.release(["w" * 40], dry_run=True) == 1
    assert len(client.calls) == before, "dry-run 放行零 qB 调用(不写限速/不摘标签)"
    assert _entries(mgr)["w" * 40]["status"] == "triggered", "dry-run 不置 released"
    assert _entries(mgr)["w" * 40]["tagged"] == ent["tagged"], "dry-run 不改任何条目字段"


def test_fuse_release_then_rearm_after_refill(tmp_path):
    mgr, client = _mgr(tmp_path)
    tor = _tor("o" * 40)
    seed_store(mgr, [tor])
    _tick(mgr)
    assert mgr.ctx.fuse.release(["o" * 40]) == 1
    _tick(mgr)
    assert _entries(mgr)["o" * 40]["status"] == "released"
    assert len(_set_calls(client)) == 2, "放行后仍完成且空闲 -> 不立即重武装"
    # 离开完成态(补齐缺口) -> 再次完成且 dlspeed==0 才 re-arm
    tor.progress = 0.99
    tor.amount_left = 4096
    _tick(mgr)
    assert _entries(mgr)["o" * 40]["status"] == "released"
    assert len(_set_calls(client)) == 2
    tor.progress = 1.0
    tor.amount_left = 0
    tor.dlspeed = 0
    _tick(mgr)
    assert _entries(mgr)["o" * 40]["status"] == "armed"
    assert _set_calls(client)[-1][1] == FENCE
    assert len(_set_calls(client)) == 3


def test_fuse_enabled_false_zero_side_effect(tmp_path):
    mgr, client = _mgr(tmp_path, enabled=False)
    seed_store(mgr, [_tor("p" * 40, dlspeed=1000)])
    _tick(mgr)
    assert client.calls == []
    assert "download_fuse" not in mgr.ctx.state.data


def test_fuse_dry_run_zero_writes(tmp_path):
    mgr, client = _mgr(tmp_path)
    seed_store(mgr, [_tor("q" * 40, dlspeed=1000)])
    _tick(mgr, dry_run=True)
    assert client.calls == []
    assert "download_fuse" not in mgr.ctx.state.data


def test_fuse_state_lost_adopt(tmp_path):
    mgr, client = _mgr(tmp_path)
    tor = _tor("r" * 40, dl_limit=FENCE)
    seed_store(mgr, [tor])
    _tick(mgr)
    assert _set_calls(client) == [], "adopt 只重建条目, 不写 qB"
    ent = _entries(mgr)["r" * 40]
    assert ent["status"] == "armed" and ent["fence"] == FENCE and ent["orig_limit"] == 0
    assert mgr.ctx.fuse.release(["r" * 40]) == 1
    assert _set_calls(client)[-1][1] == 0, "adopt 条目放行按哨兵语义恢复 0"


def test_fuse_state_lost_no_adopt_other_limit(tmp_path):
    mgr, client = _mgr(tmp_path)
    seed_store(mgr, [_tor("s" * 40, dl_limit=512 * 1024)])
    _tick(mgr)
    assert _set_calls(client) == []
    assert _entries(mgr) == {}, "非哨兵非零限速: 不建条目(只在触发时建)"


def test_fuse_removed_torrent_drops_entry(tmp_path):
    mgr, client = _mgr(tmp_path)
    seed_store(mgr, [_tor("t" * 40)])
    _tick(mgr)
    assert "t" * 40 in _entries(mgr)
    seed_store(mgr, [])
    _tick(mgr)
    assert _entries(mgr) == {}


def test_fuse_monitor_only_pauses_without_entry(tmp_path):
    mgr, client = _mgr(tmp_path)
    tor = _tor("u" * 40, dl_limit=512 * 1024, dlspeed=1000)
    seed_store(mgr, [tor])
    for _ in range(TICKS - 1):
        _tick(mgr)
    assert _pause_calls(client) == []
    _tick(mgr)
    assert _pause_calls(client) == [("pause", ["u" * 40])]
    ent = _entries(mgr)["u" * 40]
    assert ent["status"] == "triggered" and ent["fence"] == 0 and ent["orig_limit"] == 512 * 1024
    assert _set_calls(client) == [], "监控路径不写限速"


def test_fuse_sections_and_kernel_migration(tmp_path):
    mgr, _client = _mgr(tmp_path)
    assert mgr.ctx.fuse.sections() == ("download_fuse", )
    assert "download_fuse" not in KERNEL_SECTIONS
    assert "download_fuse" in mgr.host.claimed_sections()


# ---------- S3: 触发标签(§3.8) ----------

FUSE_TAG = "zFusePaused"


def _tag_add_calls(client):
    return [c for c in client.calls if c[0] == "add_tags"]


def _tag_remove_calls(client):
    return [c for c in client.calls if c[0] == "remove_tags"]


def test_fuse_trigger_adds_tag_batch_once(tmp_path):
    mgr, client = _mgr(tmp_path)
    tori = [_tor("v1" + "a" * 38, dlspeed=1000), _tor("v2" + "b" * 38, dlspeed=1000)]
    seed_store(mgr, tori)
    _tick(mgr)
    for _ in range(TICKS):
        _tick(mgr)
    adds = _tag_add_calls(client)
    assert adds == [("add_tags", [FUSE_TAG])], "同拍触发 2 个 -> 仅一次批量加标签请求"
    for tor in tori:
        assert FUSE_TAG in tor.tags_set, "facade 合并快照: 二拍照到标签"
        assert _entries(mgr)[tor.hash]["status"] == "triggered"
        assert _entries(mgr)[tor.hash]["tagged"] is True
    _tick(mgr)
    assert _tag_add_calls(client) == adds, "状态未迁移动 -> 二拍零调用"


def test_fuse_release_removes_tag_after_limit_write(tmp_path):
    mgr, client = _mgr(tmp_path)
    tor = _tor("v3" + "c" * 38, dlspeed=1000)
    seed_store(mgr, [tor])
    _tick(mgr)
    for _ in range(TICKS):
        _tick(mgr)
    assert _tag_add_calls(client) == [("add_tags", [FUSE_TAG])]
    assert mgr.ctx.fuse.release([tor.hash]) == 1
    removes = _tag_remove_calls(client)
    assert removes == [("remove_tags", [FUSE_TAG])], "放行摘标签一次批量请求"
    assert FUSE_TAG not in tor.tags_set
    set_idx = max(i for i, c in enumerate(client.calls) if c[0] == "set_download_limit")
    remove_idx = next(i for i, c in enumerate(client.calls) if c[0] == "remove_tags")
    assert set_idx < remove_idx, "释放顺序: 先写限速、后清标签"
    assert _entries(mgr)[tor.hash]["tagged"] is False
    assert _entries(mgr)[tor.hash]["was_incomplete"] is False, "清标签不重置 was_incomplete 之外额外语义"


def test_fuse_release_all_removes_tags_and_idempotent(tmp_path):
    mgr, client = _mgr(tmp_path)
    tori = [_tor("v4" + "d" * 38, dlspeed=1000), _tor("v5" + "e" * 38, dlspeed=1000)]
    seed_store(mgr, tori)
    _tick(mgr)
    for _ in range(TICKS):
        _tick(mgr)
    assert mgr.ctx.fuse.release(None) == 2
    assert _tag_remove_calls(client) == [("remove_tags", [FUSE_TAG])], "2 个种子一次批量摘标签"
    for tor in tori:
        assert FUSE_TAG not in tor.tags_set
    assert mgr.ctx.fuse.release(None) == 0, "已 released 无目标"
    assert _tag_remove_calls(client) == [("remove_tags", [FUSE_TAG])], "二次放行零请求"


def test_fuse_external_tag_removal_not_readded(tmp_path):
    mgr, client = _mgr(tmp_path)
    tor = _tor("v6" + "f" * 38, dlspeed=1000)
    seed_store(mgr, [tor])
    _tick(mgr)
    for _ in range(TICKS):
        _tick(mgr)
    assert _tag_add_calls(client) == [("add_tags", [FUSE_TAG])]
    # 模拟外部(规则/清理/用户)摘掉标签: 快照同步回流后 trigger 条目仍在
    tor.tags = ""
    tor._tags_set = None
    with capture_logs("auto_qb.core.modules.fuse_mod") as cap:
        _tick(mgr)
        _tick(mgr)
    assert _tag_add_calls(client) == [("add_tags", [FUSE_TAG])], "外部删除不自动重加"
    assert _entries(mgr)[tor.hash]["status"] == "triggered", "标签丢失不影响 triggered(state+暂停事实)"
    assert _entries(mgr)[tor.hash]["tagged"] is False
    hits = [m for m in cap.messages if "已被外部移除" in m]
    assert len(hits) == 1, "只记一条日志(不刷屏)"


def test_fuse_adopt_tagged_paused_is_triggered(tmp_path):
    mgr, client = _mgr(tmp_path)
    tor = _tor("v7" + "g" * 38, dl_limit=FENCE, state="pausedUP", tags=FUSE_TAG)
    seed_store(mgr, [tor])
    _tick(mgr)
    assert client.calls == [], "adopt 重建 triggered 零 qB 写"
    ent = _entries(mgr)[tor.hash]
    assert ent["status"] == "triggered" and ent["tagged"] is True
    assert ent["fence"] == FENCE and ent["orig_limit"] == 0
    assert "标签" in ent["reason"]
    assert mgr.ctx.fuse.release([tor.hash]) == 1
    assert _set_calls(client)[-1][1] == 0
    assert FUSE_TAG not in tor.tags_set, "放行离开 triggered 时摘标签"


def test_fuse_adopt_fence_without_tag_is_armed(tmp_path):
    mgr, client = _mgr(tmp_path)
    tor = _tor("v8" + "h" * 38, dl_limit=FENCE, state="pausedUP")
    seed_store(mgr, [tor])
    _tick(mgr)
    assert client.calls == [], "无标签只重建 armed, 零写"
    ent = _entries(mgr)[tor.hash]
    assert ent["status"] == "armed" and ent["tagged"] is False
    assert mgr.ctx.fuse.release([tor.hash]) == 1
    assert _tag_remove_calls(client) == [], "armed 不带标签 -> 放行不发摘标签请求"


def test_fuse_tag_reuse_warns_once_without_extra_request(tmp_path):
    mgr, client = _mgr(tmp_path)
    other = _tor("v9" + "i" * 38, progress=0.5, amount_left=1024, state="downloading", tags=FUSE_TAG)
    tor = _tor("va" + "j" * 38, dlspeed=1000)
    seed_store(mgr, [other, tor])
    with capture_logs("auto_qb.core.modules.fuse_mod") as cap:
        _tick(mgr)
        for _ in range(TICKS):
            _tick(mgr)
    assert not [c for c in client.calls if c[0] == "create_tags"], "复用已有定义, 不额外建标签"
    hits = [m for m in cap.messages if "复用该定义" in m]
    assert len(hits) == 1, "启动只记一条复用 WARNING"
    assert _tag_add_calls(client) == [("add_tags", [FUSE_TAG])], "正常加标签请求不变"


def test_fuse_release_cli_syncs_snapshot_before_cas():
    """CLI 是一次性进程: 必须先 apply_sync 填快照, release 的 CAS 才读得到当前 dl_limit;
    非 dry-run 必须落盘(漏调则放行重启后遇 0 限速被重新武装), dry-run 不落盘;
    显式 hash 列表 0 命中返回 False(退出码 1), 不无声成功"""
    from auto_qb.cli import fuse_release

    mgr = mock.MagicMock()
    mgr.connect.return_value = True
    order = []
    mgr.store.apply_sync.side_effect = lambda api: order.append("sync") or ([], [])
    mgr.ctx.fuse.release.side_effect = lambda hashes, dry_run: order.append("release") or 1
    assert fuse_release(mgr, ["abc"], False, False) is True
    assert order == ["sync", "release"], "先快照后放行, 顺序不可颠倒"
    assert mgr.ctx.state.save.called, "放行结果必须落盘(state 主通道)"

    mgr_dry = mock.MagicMock()
    mgr_dry.connect.return_value = True
    mgr_dry.store.apply_sync.side_effect = lambda api: ([], [])
    mgr_dry.ctx.fuse.release.side_effect = lambda hashes, dry_run: 1
    assert fuse_release(mgr_dry, ["abc"], False, True) is True
    assert not mgr_dry.ctx.state.save.called, "dry-run 不落盘"

    mgr_zero = mock.MagicMock()
    mgr_zero.connect.return_value = True
    mgr_zero.store.apply_sync.side_effect = lambda api: ([], [])
    mgr_zero.ctx.fuse.release.side_effect = lambda hashes, dry_run: 0
    assert fuse_release(mgr_zero, ["a" * 40], False, False) is False, "显式列表 0 命中要报错, 不无声 exit 0"


# ---------- T0b 补测: 生命周期 / 早退分支 / armed 推进 / release 兜底 ----------


def test_fuse_start_sets_dry_run_and_stop_clears_streak(tmp_path):
    """start 记模块级 dry-run(之后整拍零动作零 state); stop 清空连击缓存"""
    mgr, client = _mgr(tmp_path)
    fuse = mgr.ctx.fuse
    tor = _tor("w9" + "i" * 38)
    mon = _tor("wa" + "j" * 38, dl_limit=512 * 1024, dlspeed=1000)
    fuse.start(mgr.ctx, True)
    assert fuse._dry_run is True
    seed_store(mgr, [tor, mon])
    _tick(mgr)
    assert client.calls == [] and "download_fuse" not in mgr.ctx.state.data, "模块级 dry-run 零动作零 state"
    fuse.start(mgr.ctx, False)
    _tick(mgr)
    assert len(_set_calls(client)) == 1, "恢复后正常武装"
    assert mon.hash in fuse._streak, "监控连击已累计"
    fuse.stop()
    assert fuse._streak == {}, "stop 清空连击缓存"


def test_fuse_dependency_missing_early_return(tmp_path):
    """api 依赖缺失(未连接) -> _scan 整拍早退: 零写、不建 state 域(直调 _scan 避开同相位其它模块)"""
    mgr, client = _mgr(tmp_path)
    seed_store(mgr, [_tor("wb" + "k" * 38, dlspeed=1000)])
    mgr.ctx.api = None
    mgr.ctx.fuse._scan(False)
    assert client.calls == []
    assert "download_fuse" not in mgr.ctx.state.data, "依赖缺失不建 state 域"


def test_fuse_armed_refence_idempotent_after_external_clear(tmp_path):
    """armed 下 dl_limit 被外部清零(上次写失败/外部干预) -> 幂等补写哨兵"""
    mgr, client = _mgr(tmp_path)
    tor = _tor("wc" + "l" * 38)
    seed_store(mgr, [tor])
    _tick(mgr)
    assert len(_set_calls(client)) == 1
    tor.dl_limit = 0
    _tick(mgr)
    calls = _set_calls(client)
    assert len(calls) == 2 and calls[-1][1] == FENCE, "armed 下 dl_limit==0 应幂等补齐哨兵"


def test_fuse_armed_external_limit_change_released_no_writeback(tmp_path):
    """armed 下限速被外部改为非哨兵值 -> 不写回, 条目转 released(确认计数/补齐标记一并复位)"""
    mgr, client = _mgr(tmp_path)
    tor = _tor("wd" + "m" * 38)
    seed_store(mgr, [tor])
    _tick(mgr)
    assert len(_set_calls(client)) == 1
    tor.dl_limit = 512 * 1024
    with capture_logs("auto_qb.core.modules.fuse_mod") as cap:
        _tick(mgr)
    assert len(_set_calls(client)) == 1, "外部改限速不写回(之后由显式放行兜底)"
    ent = _entries(mgr)[tor.hash]
    assert ent["status"] == "released" and ent["confirm_count"] == 0 and ent["was_incomplete"] is False
    assert any("转 released" in m for m in cap.messages)


def test_fuse_unknown_status_entry_dropped(tmp_path):
    """条目状态为未知值(历史脏数据) -> 本拍丢弃, 下拍按无条目重新判定"""
    mgr, client = _mgr(tmp_path)
    tor = _tor("we" + "n" * 38)
    seed_store(mgr, [tor])
    _tick(mgr)
    assert tor.hash in _entries(mgr)
    _entries(mgr)[tor.hash]["status"] = "bogus"
    _tick(mgr)
    assert tor.hash not in _entries(mgr), "未知状态条目被丢弃"


def test_fuse_release_state_service_none_returns_zero(tmp_path):
    """state 服务缺失 -> release 直接返回 0(无条目可放行)"""
    mgr, _client = _mgr(tmp_path)
    mgr.ctx.state = None
    assert mgr.ctx.fuse.release(None) == 0


def test_fuse_release_no_entries_return_zero(tmp_path):
    """state 域缺失 / entries 为空 / 域非 dict 三形态 -> release 都返回 0"""
    mgr, _client = _mgr(tmp_path)
    assert mgr.ctx.fuse.release(["x" * 40]) == 0, "无 download_fuse 域"
    mgr.ctx.state.data["download_fuse"] = {"entries": {}}
    assert mgr.ctx.fuse.release(None) == 0, "entries 为空"
    mgr.ctx.state.data["download_fuse"] = "junk"
    assert mgr.ctx.fuse.release(None) == 0, "域非 dict"


def test_fuse_release_without_connection_marks_only_with_warning(tmp_path):
    """放行时未连接 qB -> 告警一条, 条目只标 released, 零限速写"""
    mgr, client = _mgr(tmp_path)
    tor = _tor("wf" + "o" * 38)
    seed_store(mgr, [tor])
    _tick(mgr)
    before = len(_set_calls(client))
    mgr.ctx.api = None
    with capture_logs("auto_qb.core.modules.fuse_mod") as cap:
        assert mgr.ctx.fuse.release([tor.hash]) == 1
    assert len(_set_calls(client)) == before, "无连接零写"
    assert _entries(mgr)[tor.hash]["status"] == "released"
    assert any("未连接 qB" in m for m in cap.messages), "断连放行要有告警"


def test_fuse_release_dry_run_prints_plan_only(tmp_path):
    """dry-run 放行 -> 打印计划行, 零 qB 写、条目状态不动"""
    mgr, client = _mgr(tmp_path)
    tor = _tor("wg" + "p" * 38)
    seed_store(mgr, [tor])
    _tick(mgr)
    before = len(_set_calls(client))
    with capture_logs("auto_qb.core.modules.fuse_mod") as cap:
        assert mgr.ctx.fuse.release([tor.hash], dry_run=True) == 1
    assert len(_set_calls(client)) == before, "dry-run 零写"
    assert _entries(mgr)[tor.hash]["status"] == "armed", "dry-run 不改 state"
    assert any("[dry-run] 将放行" in m for m in cap.messages)


def test_fuse_release_untag_skipped_when_tag_gone(tmp_path):
    """放行 triggered 条目但标签已被外部移除 -> 不发摘标签请求, removed==0 无汇总日志"""
    mgr, client = _mgr(tmp_path)
    tor = _tor("wh" + "q" * 38, dlspeed=1000)
    seed_store(mgr, [tor])
    _tick(mgr)
    for _ in range(TICKS):
        _tick(mgr)
    assert _tag_add_calls(client) == [("add_tags", [FUSE_TAG])]
    tor.tags = ""
    tor._tags_set = None
    with capture_logs("auto_qb.core.modules.fuse_mod") as cap:
        assert mgr.ctx.fuse.release([tor.hash]) == 1
    assert _tag_remove_calls(client) == [], "快照里已无标签: 摘标签零请求"
    assert _entries(mgr)[tor.hash]["status"] == "released"
    assert not any("摘除标签" in m for m in cap.messages), "removed==0 不打摘标签汇总日志"


def test_fuse_release_untag_skipped_when_client_none(tmp_path):
    """放行 triggered 条目时 api.client 已断(None) -> 摘标签路径安全降级: 零请求、告警、只标 released(26-11-05-0200)"""
    mgr, client = _mgr(tmp_path)
    tor = _tor("wn" + "u" * 38, dlspeed=1000)
    seed_store(mgr, [tor])
    _tick(mgr)
    for _ in range(TICKS):
        _tick(mgr)
    assert _tag_add_calls(client) == [("add_tags", [FUSE_TAG])]
    before = len(client.calls)
    mgr.ctx.api.bind(None, mgr.ctx.store)
    with capture_logs("auto_qb.core.modules.fuse_mod") as cap:
        assert mgr.ctx.fuse.release([tor.hash]) == 1
    assert len(client.calls) == before, "断连放行零 qB 请求(含摘标签)"
    assert _entries(mgr)[tor.hash]["status"] == "released"
    assert FUSE_TAG in tor.tags_set, "标签保留未动"
    assert any("跳过摘标签" in m for m in cap.messages), "断连跳过摘标签要有告警"


def test_fuse_monitor_trigger_already_tagged_zero_requests(tmp_path):
    """监控路径触发时快照已带同名标签 -> 加标签零请求(集合幂等), added==0 无打标签汇总日志"""
    mgr, client = _mgr(tmp_path)
    tor = _tor("wi" + "r" * 38, dl_limit=512 * 1024, dlspeed=1000, tags=FUSE_TAG)
    seed_store(mgr, [tor])
    with capture_logs("auto_qb.core.modules.fuse_mod") as cap:
        for _ in range(TICKS):
            _tick(mgr)
    assert _pause_calls(client) == [("pause", [tor.hash])]
    assert _tag_add_calls(client) == [], "快照已带标签: 加标签零请求"
    ent = _entries(mgr)[tor.hash]
    assert ent["status"] == "triggered" and ent["tagged"] is True
    assert not any("打标签" in m for m in cap.messages), "added==0 无打标签汇总日志"


def test_fuse_tag_apply_helpers_tolerate_missing_entries(tmp_path):
    """标签批量助手直驱: entries 缺该 hash(防御假 ent is None)与 rec 无标签(continue)两侧都不炸

    经 _scan/release 真流 ent 恒存在、rec 恒带标签, 防御假只能直驱 _apply_tag_add/_apply_tag_remove
    补齐(348-350/365-366 语句 + ent is None / continue 分支); api 用 MagicMock 隔离 facade 的快照回写。
    """
    mgr, _client = _mgr(tmp_path)
    fuse = mgr.ctx.fuse
    tagged = _tor("wj" + "s" * 38, tags=FUSE_TAG)
    untagged = _tor("wk" + "t" * 38)
    store = mock.MagicMock()
    store.get = lambda h: tagged if h == tagged.hash else untagged
    api = mock.MagicMock()
    assert fuse._apply_tag_add(api, [tagged.hash, untagged.hash], FUSE_TAG, entries={}, store=store) == 1
    api.torrents_add_tags.assert_called_once_with(tags=[FUSE_TAG], torrent_hashes=[untagged.hash])
    assert fuse._apply_tag_remove(api, [tagged.hash, untagged.hash], FUSE_TAG, entries={}, store=store) == 1
    api.torrents_remove_tags.assert_called_once_with(tags=[FUSE_TAG], torrent_hashes=[tagged.hash])
