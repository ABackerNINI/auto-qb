"""test_relocate_tag_mirror 测试计划: qB 待收尾标签镜像(计划 26-11-04-1042 P3, opt-in, 只写不读)

验收判据(plan §04 P3-1 / §07 风险表):
- 默认配置(空)零 qB 写; 开启后 armed/待收尾窗口加标签, 终态(撤销/失败/完成)摘标签;
- 标签只写不读: 运行时绝不调用 torrents_tags, 用户手删标签不影响 state/WebUI 结论;
- 独立命名空间: 所有写请求只用配置的 zRelocate 前缀标签, 不碰用户自定义标签;
- 失败降级: qB 超时/版本不支持等异常只告警计数, 迁移相位与收尾判定不变;
- 重启补写: 失联期间错过的 armed 标签在恢复后由 reconcile 补上, 缺失不视为错误。

## 测试计划(每个测试函数一条)
- test_pending_tag_default_off_zero_qb_writes: 默认空配置跑完整迁移到 armed, 零 add/remove 请求
- test_pending_tag_added_at_armed_only: 搬到目标后 armed 时加标签(搬运中不加), 只写命名空间内标签
- test_pending_tag_removed_on_terminal: 终态(撤销)时摘标签, 命名空间不被误清
- test_pending_tag_never_read_back: 运行时路径不调用 torrents_tags(monkeypatch 抛错也不影响)
- test_pending_tag_user_delete_keeps_state: 用户手删标签后不再重加, 相位与视图结论不变
- test_pending_tag_failure_degrades: qB 写失败只计数告警, 相位保持 armed, 按退避不每 tick 重撞
- test_pending_tag_remove_failure_retried: 终态摘标签失败后由 reconcile 退避重试, 不永久残留
- test_pending_tag_reconcile_after_restart: 重启后非终态 job 的标签由 reconcile 补写
- test_pending_tag_dry_run_never_writes: dry-run 不发任何 qB 标签写
"""

import types

from auto_qb.core.modules import relocate_units as ru

from auto_qb.config.models import RelocateConfig

from helpers import pin_disk_usage, relocate_env

from relocate_exec_support import _bare_mod, _job, _run_ticks, _simulate_moved, _spy_spawn

TAG = "zRelocatePending"


def _tag_env(tmp_path, monkeypatch, tag=TAG):
    """真临时目录 + 已开启标签镜像的 relocate 环境(HA/HB 双成员组, 起步 uploading)"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, state="uploading")
    mgr.config.relocate.pending_tag = tag
    mod = mgr.host.get("relocate")
    spawned = []
    _spy_spawn(mod, spawned)
    job_id = mod.relocate_execute(["HA"], dst)[0]["job_id"]
    return mgr, client, mod, job_id, dst, content, files


def _to_armed(mgr, mod, job_id, dst, content, files):
    """推进到 armed(目标侧齐备), 断言相位"""
    _simulate_moved(mgr, dst, files, content)
    _run_ticks(mod, 6)
    assert mod.get_job(job_id).phase == ru.PHASE_ARMED


def _tag_calls(client, kind):
    return [c for c in client.calls if c[0] == kind]


def test_pending_tag_default_off_zero_qb_writes(tmp_path, monkeypatch):
    """默认空配置(标签镜像关闭): 全流程到 armed 零 add/remove 请求(黄金法则 2)"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, state="uploading")
    assert mgr.config.relocate.pending_tag == ""
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    job_id = mod.relocate_execute(["HA"], dst)[0]["job_id"]
    _to_armed(mgr, mod, job_id, dst, content, files)
    assert _tag_calls(client, "add_tags") == []
    assert _tag_calls(client, "remove_tags") == []
    assert mod._tag_applied == {}


def test_pending_tag_added_at_armed_only(tmp_path, monkeypatch):
    """搬运中不加标签; 进入 armed 才加, 且只写命名空间内标签"""
    mgr, client, mod, job_id, dst, content, files = _tag_env(tmp_path, monkeypatch)
    assert mod.get_job(job_id).phase == ru.PHASE_MOVING
    assert _tag_calls(client, "add_tags") == []  # moving 阶段不动 qB 标签

    _to_armed(mgr, mod, job_id, dst, content, files)
    adds = _tag_calls(client, "add_tags")
    assert len(adds) == 1, client.calls
    assert adds[0][1] == TAG
    assert mod._tag_applied[job_id] == "add"
    # 命名空间约束: 除配置标签外没有写别人的标签
    assert {c[1] for c in adds + _tag_calls(client, "remove_tags")} == {TAG}


def test_pending_tag_removed_on_terminal(tmp_path, monkeypatch):
    """终态(撤销)时摘标签; 只摘自己的命名空间标签"""
    mgr, client, mod, job_id, dst, content, files = _tag_env(tmp_path, monkeypatch)
    _to_armed(mgr, mod, job_id, dst, content, files)
    assert mod._tag_applied[job_id] == "add"

    r = mod.relocate_cancel(job_id, cost_confirmed=True)
    assert r["cls"] == "ok" and mod.get_job(job_id).phase == ru.PHASE_CANCELLED
    removes = _tag_calls(client, "remove_tags")
    assert len(removes) == 1, client.calls
    assert removes[0][1] == TAG
    assert mod._tag_applied[job_id] == "remove"


def test_pending_tag_never_read_back(tmp_path, monkeypatch):
    """只写不读: 运行期把 torrents_tags 换成抛错替身也不影响迁移与标签写入"""
    mgr, client, mod, job_id, dst, content, files = _tag_env(tmp_path, monkeypatch)

    def _boom(*a, **kw):
        raise AssertionError("relocate 不得读取 qB 标签作为状态来源")

    monkeypatch.setattr(mgr.ctx.api, "torrents_tags", _boom, raising=False)
    _to_armed(mgr, mod, job_id, dst, content, files)
    assert len(_tag_calls(client, "add_tags")) == 1


def test_pending_tag_user_delete_keeps_state(tmp_path, monkeypatch):
    """用户手删标签后: 不读回、不重加, 相位与视图结论不变(标签不是事实源)"""
    mgr, client, mod, job_id, dst, content, files = _tag_env(tmp_path, monkeypatch)
    _to_armed(mgr, mod, job_id, dst, content, files)
    before = len(_tag_calls(client, "add_tags"))

    # 模拟用户在 qB 里手工删掉该标签(模块不应因此重加, 也不应改变任何状态)
    client.torrents_remove_tags(tags=TAG, torrent_hashes=["HA", "HB"])
    _run_ticks(mod, 3)

    assert mod.get_job(job_id).phase == ru.PHASE_ARMED
    assert [j["phase"] for j in mod.jobs_view()] == [ru.PHASE_ARMED]
    assert len(_tag_calls(client, "add_tags")) == before  # 没有重加
    assert mod._tag_failures == 0


def test_pending_tag_failure_degrades(tmp_path, monkeypatch):
    """qB 写失败(超时/版本不支持): 只计数告警, 相位保持 armed, 退避期内不每 tick 重撞"""
    mgr, client, mod, job_id, dst, content, files = _tag_env(tmp_path, monkeypatch)

    def _boom(**kw):
        raise RuntimeError("qB 版本不支持标签")

    monkeypatch.setattr(mgr.ctx.api, "torrents_add_tags", _boom, raising=False)
    _to_armed(mgr, mod, job_id, dst, content, files)

    assert mod.get_job(job_id).phase == ru.PHASE_ARMED  # 迁移主流程不受影响
    assert mod._tag_failures == 1
    assert mod._tag_applied == {}

    _run_ticks(mod, 3)  # 退避期内不重复撞 qB
    assert mod._tag_failures == 1
    assert mod.get_job(job_id).phase == ru.PHASE_ARMED


def test_pending_tag_remove_failure_retried(tmp_path, monkeypatch):
    """终态摘标签失败: reconcile 必须重试 — 否则一次 qB 抖动就让标签永久残留"""
    mgr, client, mod, job_id, dst, content, files = _tag_env(tmp_path, monkeypatch)
    _to_armed(mgr, mod, job_id, dst, content, files)
    assert mod._tag_applied[job_id] == "add"

    original = mgr.ctx.api.torrents_remove_tags

    def _boom(**kw):
        raise RuntimeError("qB 摘除失败")

    monkeypatch.setattr(mgr.ctx.api, "torrents_remove_tags", _boom, raising=False)
    mod.relocate_cancel(job_id, cost_confirmed=True)
    assert mod.get_job(job_id).phase == ru.PHASE_CANCELLED
    assert mod._tag_applied[job_id] == "add", "摘除未成功, 不能记成已摘"
    assert mod._tag_failures == 1

    # qB 恢复 + 跳过 30s 退避窗口(等价于下一次重试 tick)
    monkeypatch.setattr(mgr.ctx.api, "torrents_remove_tags", original, raising=False)
    mod._tag_next_try.pop(job_id, None)
    client.calls.clear()
    mod._reconcile_pending_tags()
    removes = _tag_calls(client, "remove_tags")
    assert len(removes) == 1 and removes[0][1] == TAG
    assert mod._tag_applied[job_id] == "remove"

    # 已摘除的终态 job 不参与 reconcile —— 不对历史 job 写放大
    client.calls.clear()
    mod._reconcile_pending_tags()
    assert _tag_calls(client, "remove_tags") == []


def test_pending_tag_reconcile_after_restart(tmp_path, monkeypatch):
    """重启: 账上新模块重新加载 armed job 后由 reconcile 补写标签(缺失不视为错误)"""
    mgr, client, mod, job_id, dst, content, files = _tag_env(tmp_path, monkeypatch)
    _to_armed(mgr, mod, job_id, dst, content, files)

    mod2 = type(mod)(mgr.ctx)
    n = mod2._load_jobs()
    assert n == 1 and mod2.get_job(job_id).phase == ru.PHASE_ARMED
    assert mod2._tag_applied == {}  # 新进程初始无「已写过」记忆

    client.calls.clear()
    mod2._reconcile_pending_tags()
    adds = _tag_calls(client, "add_tags")
    assert len(adds) == 1 and adds[0][1] == TAG
    assert mod2._tag_applied[job_id] == "add"
    assert mod2.get_job(job_id).phase == ru.PHASE_ARMED


def test_pending_tag_dry_run_never_writes():
    """dry-run 感知: 即使 job 在 armed、配置开启, 也不发任何标签写"""
    calls = []
    api = types.SimpleNamespace(
        torrents_add_tags=lambda **kw: calls.append(("add", kw)),
        torrents_remove_tags=lambda **kw: calls.append(("remove", kw)),
    )
    mod = _bare_mod(
        api=api,
        relocate=RelocateConfig(enabled=True, pending_tag=TAG),
        data_dir="",
    )
    mod._dry = True
    mod._sync_pending_tag(_job(phase=ru.PHASE_ARMED))
    mod._sync_pending_tag(_job(phase=ru.PHASE_DONE))
    assert calls == []
    assert mod._tag_applied == {}
