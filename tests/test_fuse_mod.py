"""test_fuse_mod 测试计划: 已完成种子下载保险丝三态状态机(S2) + 触发标签(S3), 不连接真实 qB

## 测试计划(每个测试函数一条)
- test_fuse_arm_writes_fence_once: 完成+dl_limit==0 -> 一次批量写哨兵; 再扫零写(幂等)
- test_fuse_arm_only_complete_zero_limit: 未完成/校验中/已有非零限速 -> 不写不建条目
- test_fuse_trigger_after_confirm_ticks: 连续 N 拍 dlspeed>0 -> 一次批量 pause, 状态 triggered 带原因
- test_fuse_zero_speed_never_triggers: 恒 0 连击不累积、不暂停(不误伤)
- test_fuse_triggered_repause_on_external_start: triggered 被外部启动且 own_write 已回流 -> 再暂停一次
- test_fuse_triggered_no_duplicate_within_own_write: own_write 未回流期间不重复下发暂停(幂等)
- test_fuse_release_cas_restores_pre_limit: 放行 CAS 成立 -> 恢复 orig_limit(0) 且标 released, 不 resume
- test_fuse_release_cas_failed_only_marks: 放行时限速已被外部改 -> 零写只标 released
- test_fuse_release_all_batches: release(None) 批量放行全部条目并恢复限速
- test_fuse_release_unknown_hash_noop: 放行不存在的 hash -> 0 且零写
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
"""

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
    for _ in range(TICKS):
        _tick(mgr)
    assert len(_pause_calls(client)) == 1 and len(_pause_calls(client)[0][1]) == 2
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
