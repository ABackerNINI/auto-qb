"""test_relocate_exec_misc 测试计划: 整组迁移执行体 / 对账 / 收尾 guardian / 三入口接线
(计划 26-10-18-1604 §04 P3/P5/P6)

验收判据(plan §04):
- P3: Fake qB 集成覆盖五场景 —— 正常、停滞判失败(不搬回)、长耗时转 watching(不判失败)、
  第 3 条链接失败 ⇒ 删已建链接 + 转收尾、qB 中途断连(不重复下发); 主循环零阻塞(单步 < 50ms)。
- P5: 关闭时调用序列与今日一致(守阵); 开启时三入口(单件/批量/规则)都产生 job。
- P6: 对账表 8 行逐行(纯函数层在 test_relocate_units)、撤销回滚、guardian 三证后删链接。
- 真机 qB 验证留待他人在有 qB 的环境执行(本轮 Fake qB 全替身)。

## 测试计划(每个测试函数一条)
- test_entry_single_location_disabled_unchanged: 开关关: 单件移动调用序列与今日逐字节一致
### P1-T1.1 守卫与容错簇(计划 26-10-20-2101)
- test_resolve_physical_falls_back_on_resolver_error: 物理位置解析异常退回原路径(组判定绝不因迁移崩)
- test_sync_relocating_builds_registry_on_legacy_store: 老 store 替身无 relocating_hashes -> 自建并登记非终态成员
- test_on_task_line_noop_without_ctx: ctx/store 缺失(停机路径)零动作
- test_advance_ignores_terminal_phase: 终态相位不再推进(相位机兜底)
- test_penetration_ok_rejects_missing_or_unstatable: 穿透校验三态(不存在/stat 抛/齐备)
- test_qb_up_caches_negative_probe: 「qB 在?」探测异常判不在并缓存 10s
- test_restart_does_not_reissue_setlocation
- test_restart_reissues_setlocation_when_never_issued: 崩溃窗口(账已落/未下发) ⇒ 重启补发一次
  setLocation(issue 26-10-30-0616; 旧实现一律 issue=False, 600s 后按 move_stalled 误判)
- test_restart_issued_without_evidence_keeps_polling: 已下发但无现场 ⇒ 不重发不立刻判失败
- test_skip_check_skips_during_relocation
### 收口 / 退避守卫(issues 26-10-30-0616 批A: resume_hashes 失败路径 / dry_run 短路 / 重试退避)
- test_fail_path_resumes_paused_members: 失败出口消费 resume_hashes(旧实现只在成功路径恢复)
- test_fail_path_resume_rejected_still_fails_and_names_paused: 恢复被拒: 失败照落 + 告警点名仍被暂停
### W8(R32) S5 补测(变异审计真洞守阵, 分类: tmp-analysis/w8-r32/classify-mod-{a,b}.md)
  + 同卷硬链接兜底(same_volume 实参丢失 ⇒ capability_ok 翻假)
  + 补发 setLocation 入参(只发 mover) + 发起 rt 初值(stall_since/last_size/sample_ts)
- test_spawn_args_pinned: guardian 进程拉起参数(--job/平台支/stdio)
- test_recover_dispatch_faces: 恢复四分派(moving/补发/不补发/RESUME)
- test_misc_low_contract_faces: on_task_line 守卫/异常账面/_fail 文案/武装与收口实参/纵深单层
- test_precheck_receipt_contract_and_add_param: 预检拒收回执契约 + 添加预检空参
  (26-11-05-0808 S1 起 happy-path 前须配置可达 bt_backup, 见用例内注)

覆盖率第三轮 T2b 补测(26-11-05):
- test_arm_and_finish_direct_without_grouping_ctx: ctx 无 grouping 模块 -> 重归组段整段跳过, 落账/guardian/恢复照旧(260->266/278->283)
- test_remove_links_skips_non_alias_paths: 非别名/空条目跳过不删不计(709->705)
"""

import os

import time

import types

import pytest

from auto_qb.core.modules import relocate_units as ru

from auto_qb.infra import relocate_journal

from helpers import pin_disk_usage, relocate_env

from auto_qb.config.models import RelocateConfig

from auto_qb.core.modules.grouping_mod import group_key_of

from auto_qb.core.modules.relocate_mod import RelocateModule, _native as _mod_native

from auto_qb.infra import alias_fs as afs

from auto_qb.infra import file_access as fa_mod

from auto_qb.infra import utils as infra_utils

from helpers import FakeClient, FakeTorrent, _fake_file, capture_logs

from relocate_exec_support import (
    _bare_mod,
    _job,
    _spy_spawn,
    _stub_cap,
)


def test_entry_single_location_disabled_unchanged(tmp_path, monkeypatch):
    """开关关: 单件移动仍是「一次 setLocation」—— 调用序列与今日逐字节一致"""
    mgr, client, src, dst, content, files = relocate_env(tmp_path, state="uploading")
    mgr.config.relocate.enabled = False
    mgr.web.commands.put(("set_torrent_location", {"hash": "HA", "location": dst, "cmd_id": "c1"}))
    mgr.web.consume_commands()
    assert client.calls == [("set_location", dst)], client.calls
    assert mgr.host.get("relocate").jobs_view() == [], "关时不得产生 job"


def test_restart_does_not_reissue_setlocation(tmp_path, monkeypatch):
    """重启恢复: 账里 phase=moving 的 job 继续轮询, **不重复下发** setLocation"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, state="uploading")
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    job_id = mod.relocate_execute(["HA"], dst)[0]["job_id"]
    mgr.store.by_hash["HA"].state = "moving"
    client.calls.clear()

    mod2 = type(mod)(mgr.ctx)
    mod2._conf = mgr.config.relocate
    assert mod2._load_jobs() == 1
    mod2.on_task_line()
    assert [c for c in client.calls if c[0] == "set_location"] == [], "重启不得重发 setLocation"
    assert mod2.get_job(job_id).phase in (ru.PHASE_MOVING, ru.PHASE_WATCHING)


def test_restart_reissues_setlocation_when_never_issued(tmp_path, monkeypatch):
    """崩溃窗口(账已落、setLocation 未发出): 重启据 move_issued=False 补发一次, 不再静默等停滞超时

    旧实现 _load_jobs 对 MOVING job 一律 issue=False ⇒ 补发永不发生, dst 恒空且 qB 不在
    moving, 只会在 move_stall_timeout(600s)后按 move_stalled 误判失败(issue 26-10-30-0616)。
    """
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, state="uploading")
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    job_id = mod.relocate_execute(["HA"], dst)[0]["job_id"]
    mod._state_jobs()[job_id]["move_issued"] = False  # 模拟「落账与下发之间」中断
    client.calls.clear()
    mgr.store.own_writes.clear()

    mod2 = type(mod)(mgr.ctx)
    mod2._conf = mgr.config.relocate
    assert mod2._load_jobs() == 1
    mod2.on_task_line()  # 第一个 tick 只定夺现场
    assert [c for c in client.calls if c[0] == "set_location"] == [], "定夺现场这一 tick 不下发"
    mod2.on_task_line()  # 第二个 tick 才真的补发
    assert [c for c in client.calls if c[0] == "set_location"] == [("set_location", dst)], "必须补发一次"
    job = mod2.get_job(job_id)
    assert job.move_issued is True, "补发成功必须落账「已下发」"
    assert job.phase == ru.PHASE_MOVING, job


def test_restart_issued_without_evidence_keeps_polling(tmp_path, monkeypatch):
    """重启恢复: 已下发但 qB 不在 moving 且 dst 无数据 ⇒ 不重发、也不立刻判失败(交停滞判据)

    快照滞后会让「刚下发还没动」与真停滞同形, 立刻判失败会误杀正常迁移 —— 保守默认。
    """
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, state="uploading")
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    job_id = mod.relocate_execute(["HA"], dst)[0]["job_id"]
    mgr.store.by_hash["HA"].state = "pausedUP"
    client.calls.clear()

    mod2 = type(mod)(mgr.ctx)
    mod2._conf = mgr.config.relocate
    mod2._load_jobs()
    mod2.on_task_line()
    job = mod2.get_job(job_id)
    assert [c for c in client.calls if c[0] == "set_location"] == [], "已下发过不得重发"
    assert job.phase in (ru.PHASE_MOVING, ru.PHASE_WATCHING) and job.reason == "", job
    assert mod2._rt[job_id].get("recover") is None, "现场判据只判一次, 之后交常规轮询"


def test_skip_check_skips_during_relocation(tmp_path, monkeypatch):
    """搬迁窗口: relocating 登记内的种子跳检直接 skip(不删除/不重加)"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, state="uploading")
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    mod.relocate_execute(["HA"], dst)
    assert "HA" in mgr.store.relocating_hashes
    mgr.store.own_writes.clear()  # 自有暂停登记先清掉, 单独验证搬迁窗口闸门
    client.calls.clear()
    r = mgr.ctx.ops.skip_check("HA", source="web")
    assert r.is_skipped and "整组迁移" in r.message, r
    assert client.calls == [], client.calls


def test_resolve_physical_falls_back_on_resolver_error(monkeypatch):
    """物理位置解析异常退回原路径(§3.4 第 1 层: 组判定绝不因迁移功能崩)"""
    from auto_qb.core.modules import relocate_units as ru_mod

    mod = _bare_mod()
    assert mod.resolve_physical("") == "", "空路径原样返回"
    monkeypatch.setattr(ru_mod, "resolve_physical", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("解析炸了")))
    assert mod.resolve_physical("R:/x") == "R:/x", "解析失败必须退回原路径"


def test_sync_relocating_builds_registry_on_legacy_store():
    """老 store 替身没有 relocating_hashes: 自建一份并登记非终态 job 的成员并集"""
    mod = _bare_mod()
    store = types.SimpleNamespace(by_hash={})  # 无 relocating_hashes 字段
    mod._ctx = types.SimpleNamespace(
        store=store, config=types.SimpleNamespace(relocate=None), state=types.SimpleNamespace(data={})
    )
    mod.register_job(_job())
    mod._sync_relocating()
    assert store.relocating_hashes == {"HA"}, "登记必须落在自建集合上"


def test_on_task_line_noop_without_ctx():
    """ctx/store 缺失(停机路径)时 on_task_line 零动作, 不碰任何 job"""
    from auto_qb.config.models import RelocateConfig
    from auto_qb.core.modules.relocate_mod import RelocateModule

    mod = RelocateModule()  # ctx=None
    mod._conf = RelocateConfig(enabled=True)  # 开关开: 不走 enabled 早退, 必须走 ctx 守卫
    mod.on_task_line()  # 不抛
    assert mod.jobs_view() == []


def test_advance_ignores_terminal_phase():
    """终态相位不再推进(相位机兜底: done/failed/cancelled 落到 elif 链之外)"""
    mod = _bare_mod()
    mod._advance(_job(phase=ru.PHASE_DONE))
    mod._advance(_job("j2", phase=ru.PHASE_CANCELLED))
    assert mod._rt == {"j1": {}, "j2": {}}, "只建运行态槽, 不改 job"


def test_penetration_ok_rejects_missing_or_unstatable(monkeypatch):
    """穿透校验: 原路径不存在/大小不符 -> False; stat 抛异常 -> False(一律保守)"""
    from auto_qb.infra import file_access as fa_mod

    mod = _bare_mod()
    job = _job(plan={"files": [["a.mkv", 10]]})

    class _FA:
        def __init__(self, exists, size, boom=False):
            self._exists, self._size, self._boom = exists, size, boom

        def exists(self, p):
            if self._boom:
                raise OSError("盘掉线")
            return self._exists

        def getsize(self, p):
            return self._size

    monkeypatch.setattr(fa_mod, "get_file_access", lambda: _FA(False, 0))
    assert mod._penetration_ok(job) is False, "原路径不存在 = 穿透失败"
    monkeypatch.setattr(fa_mod, "get_file_access", lambda: _FA(True, 10, boom=True))
    assert mod._penetration_ok(job) is False, "stat 抛异常 = 穿透失败"
    monkeypatch.setattr(fa_mod, "get_file_access", lambda: _FA(True, 10))
    assert mod._penetration_ok(job) is True


def test_qb_up_caches_negative_probe():
    """「qB 在?」三证之一: 探测异常判「不在」并缓存 10s(免得每 tick 一次请求)"""
    calls = []

    class _Client:
        def app_preferences(self):
            calls.append(1)
            raise RuntimeError("连不上")

    mod = _bare_mod(api=types.SimpleNamespace(client=_Client()))
    assert mod._qb_up() is False
    assert mod._qb_up() is False
    assert len(calls) == 1, "10s 内必须命中缓存(负结论同样缓存)"


def test_fail_path_resumes_paused_members():
    """失败出口消费 resume_hashes: 迁移没成 ⇒ 把发起时暂停的成员放回运行态

    旧实现只在成功路径(武装 / 单成员收口 / 撤销成功)恢复, 失败出口一律漏掉 —— 整组
    成员永久停在暂停态且日志一字不提, 用户只能观察到「莫名暂停」。
    """
    resumed = []
    store = types.SimpleNamespace(by_hash={"HA": types.SimpleNamespace(state="pausedUP")}, relocating_hashes=set())
    mod = _bare_mod(
        store=store,
        api=types.SimpleNamespace(
            torrents_set_location=lambda **kw: (_ for _ in ()).throw(RuntimeError("qB 拒绝 setLocation")),
            torrents_resume=lambda **kw: resumed.append(list(kw["torrent_hashes"])),
        ),
    )
    mod._step_move(_job(resume_hashes=("HA", "HB")), {"issue": True})
    saved = mod._jobs["j1"]
    assert saved.phase == ru.PHASE_FAILED and saved.reason == "move_rejected", (saved.phase, saved.reason)
    assert resumed == [["HA", "HB"]], f"失败必须把被暂停的成员放回运行态: {resumed}"


def test_fail_path_resume_rejected_still_fails_and_names_paused():
    """恢复被拒: 失败照落(数据面保留现场), 只告警并点名「仍被暂停」(用户可照单手动恢复)"""
    from helpers import capture_logs

    mod = _bare_mod(api=types.SimpleNamespace(torrents_resume=lambda **kw: (_ for _ in ()).throw(RuntimeError("拒了"))))
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod._fail(_job(resume_hashes=("HA", )), "move_stalled", "停滞")
    saved = mod._jobs["j1"]
    assert saved.phase == ru.PHASE_FAILED and saved.reason == "move_stalled"
    assert any("仍被暂停" in m and "HA" in m for m in cap.messages), cap.messages


def test_spawn_args_pinned(monkeypatch):
    """guardian 进程拉起参数: --job 逐字(sp_8/9)/平台支(sp_20/24/26/32~35)/stdio 与 close_fds(sp_13~19)"""
    import subprocess

    seen = []
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: seen.append((a, k)))
    mod = RelocateModule()
    monkeypatch.setattr(infra_utils, "is_windows", lambda: True)
    mod._spawn("D:/dd", "jr-x")
    argv, kwargs = seen[-1][0][0], seen[-1][1]
    assert "--job" in argv and argv[-1] == "jr-x", argv
    # CREATE_NO_WINDOW 只在 Windows 侧存在; 用例强制走 Windows 分支时按实现同款兜底取常量
    assert kwargs["creationflags"] == getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000), kwargs
    assert kwargs["stdout"] == subprocess.DEVNULL and kwargs["stderr"] == subprocess.DEVNULL, kwargs
    assert kwargs["close_fds"] is True, kwargs

    monkeypatch.setattr(infra_utils, "is_windows", lambda: False)
    mod._spawn("D:/dd", "jr-y")
    argv, kwargs = seen[-1][0][0], seen[-1][1]
    assert "--job" in argv and argv[-1] == "jr-y", argv
    assert kwargs["start_new_session"] is True, kwargs  # guardian 不随 auto-qb 进程组消亡


def test_recover_dispatch_faces(tmp_path):
    """恢复四分派: moving=POLL(rv_6~20/39)/未下发补发(rv_55/56)/已下发不补发(rv_48)/数据在 dst=RESUME(rv_23~40)"""
    # qB 在搬: 继续轮询, 不补发
    store = types.SimpleNamespace(by_hash={"HA": types.SimpleNamespace(state="moving", save_path="R:/src")})
    mod = _bare_mod(store=store)
    job = _job()
    rt = {"recover": True, "issue": False, "started": time.monotonic()}
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod._recover(job, rt, store.by_hash["HA"])
    assert rt.get("recover") is None and rt.get("issue") is False, rt
    assert any("继续轮询" in m for m in cap.messages), cap.messages

    # 未下发 + 无现场: 补发一次(issue=True)+ warning 点名 mover(哈希截断必须 [:8], rv_56)
    store = types.SimpleNamespace(by_hash={"HS": types.SimpleNamespace(state="pausedUP", save_path="R:/src")})
    mod = _bare_mod(store=store)
    job = _job(mover="HASHABCDEFGHI", move_issued=False)
    rt = {"recover": True, "issue": False, "started": time.monotonic()}
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod._recover(job, rt, store.by_hash["HS"])
    assert rt["issue"] is True, rt
    assert any("补发" in m and "(mover HASHABCD ->" in m for m in cap.messages), cap.messages

    # 已下发 + 无现场: 不重发(保守默认, 交停滞判据)
    store = types.SimpleNamespace(by_hash={"HA": types.SimpleNamespace(state="pausedUP", save_path="R:/src")})
    mod = _bare_mod(store=store)
    job = _job(move_issued=True)
    rt = {"recover": True, "issue": False, "started": time.monotonic()}
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod._recover(job, rt, store.by_hash["HA"])
    assert rt.get("issue") is False, rt
    assert any("未见搬迁现场" in m for m in cap.messages), cap.messages

    # 数据已在 dst: RESUME 直进 moved 校验
    store = types.SimpleNamespace(by_hash={"HA": types.SimpleNamespace(state="pausedUP", save_path="R:/dst")})
    mod = _bare_mod(store=store)
    job = _job()
    rt = {"recover": True, "issue": False, "started": time.monotonic()}
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod._recover(job, rt, store.by_hash["HA"])
    assert mod._jobs["j1"].phase == ru.PHASE_MOVED, mod._jobs["j1"]
    assert rt["stage"] == "verify", rt
    assert any("补做" in m for m in cap.messages), cap.messages

    # 分派入口: _step_move 的 recover 分支必须把**真 mover**递给判据(sm_19: 传 None = 误补发)
    store = types.SimpleNamespace(by_hash={"HA": types.SimpleNamespace(state="moving", save_path="R:/src")})
    mod = _bare_mod(store=store)
    rt = {"recover": True, "issue": False, "started": time.monotonic()}
    mod._step_move(_job(), rt)
    assert rt.get("issue") is False, rt


def test_misc_low_contract_faces(monkeypatch):
    """低危代表: 未启用零动作(ot_3)/异常账面(ot_22/25/28/31)/_fail 文案(fl_*, sm_7/200)/
    verify_mismatch 文案(mv_16)/武装与收口实参(am_*, fd_*)/纵深单层(pn_8/dr_11)/删链告警(rl_13)"""
    # 未启用: 相位机零动作(即便 _jobs 非空 —— 热重载关闭场景)
    mod = _bare_mod(relocate=RelocateConfig(enabled=False))
    advanced = []
    monkeypatch.setattr(mod, "_advance", lambda job: advanced.append(job.job_id))
    mod.register_job(_job("j1"))
    mod.on_task_line()
    assert advanced == [], advanced

    # 推进异常: internal_error 账面带异常文本
    mod2 = _bare_mod()
    mod2.register_job(_job("j2"))

    def _boom(job):
        raise RuntimeError("boom")

    monkeypatch.setattr(mod2, "_advance", _boom)
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod2.on_task_line()
    saved = mod2._jobs["j2"]
    assert (saved.phase, saved.reason, saved.last_error) == (ru.PHASE_FAILED, "internal_error", "boom"), saved
    assert any("推进异常" in m and "boom" in m for m in cap.messages), cap.messages

    # _fail: 缺省空串 + 显式文本
    mod3 = _bare_mod()
    assert mod3._fail(_job("j3"), "r1").last_error == ""
    assert mod3._fail(_job("j4"), "r1", "boom").last_error == "boom"

    # 停滞失败与 mover 消失的失败文案
    store = types.SimpleNamespace(by_hash={"HA": types.SimpleNamespace(state="pausedUP", save_path="R:/src")})
    mod4 = _bare_mod(store=store)
    now = time.monotonic()
    rt = {"issue": False, "started": now - 100, "sample_ts": 0.0, "last_size": 10, "stall_since": now - 700}
    mod4._step_move(_job(plan={"files": [["a.mkv", 10]]}), rt)
    saved = mod4._jobs["j1"]
    assert (saved.phase, saved.reason) == (ru.PHASE_FAILED, "move_stalled"), (saved.phase, saved.reason)
    assert saved.last_error == "搬迁停滞(dst 不再增长且 qB 已不在 moving)", saved.last_error

    mod5 = _bare_mod(store=types.SimpleNamespace(by_hash={}))
    mod5._step_move(_job("j5"), {})
    saved = mod5._jobs["j5"]
    assert (saved.phase, saved.reason, saved.last_error) == (ru.PHASE_FAILED, "torrent_gone", "搬迁中种子已不存在"), \
        saved

    # verify_mismatch 文案
    mod6 = _bare_mod()
    mod6._step_moved(_job("j6", phase=ru.PHASE_MOVED, plan={"files": [["a.mkv", 10]]}), {})
    saved = mod6._jobs["j6"]
    assert (saved.phase, saved.reason, saved.last_error) == (ru.PHASE_FAILED, "verify_mismatch", "目标侧文件数/大小不符"), \
        saved

    # 武装: 相位/reason 清账/重归组实参/审计日志
    rg_args = []
    mod7 = _bare_mod()
    mod7._ctx.grouping = types.SimpleNamespace(regroup_scope=lambda *a: rg_args.append(a))
    monkeypatch.setattr(mod7, "_spawn_guardian", lambda job: True)
    job7 = _job("j7", phase=ru.PHASE_MOVED, alias_kind="")  # direct 形态: or 分支才可达(am_34/35/36)
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod7._arm(job7, {})
    saved = mod7._jobs["j7"]
    assert saved.phase == ru.PHASE_ARMED and saved.reason == "" and saved.attempts == 0, saved
    assert rg_args == [(job7.scope, job7.src, job7.hashes)], rg_args
    assert any("已武装收尾" in m and "形态 direct" in m for m in cap.messages), cap.messages

    # 单成员收口: 重归组实参 + 恢复成员 + done
    resumed = []
    mod8 = _bare_mod(
        api=types.SimpleNamespace(client=None, torrents_resume=lambda **kw: resumed.append(list(kw["torrent_hashes"])))
    )
    mod8._ctx.grouping = types.SimpleNamespace(regroup_scope=lambda *a: rg_args.append(a))
    job8 = _job("j8", src="R:/src8", resume_hashes=("HA", ))  # src 独立: 重归组实参断言才区分得了缺参变异
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap8:
        mod8._finish_direct(job8)
    saved = mod8._jobs["j8"]
    assert saved.phase == ru.PHASE_DONE and saved.reason == "direct", saved
    assert rg_args[-1] == (job8.scope, job8.src, job8.hashes), rg_args
    assert resumed == [["HA"]], resumed
    assert any("单成员组迁移完成" in m for m in cap8.messages), cap8.messages

    # 重归组失败: 只告警不阻断收口落账(am_16/fd_16)
    def _rg_boom(*a):
        raise RuntimeError("归组炸了")

    mod7b = _bare_mod()
    mod7b._ctx.grouping = types.SimpleNamespace(regroup_scope=_rg_boom)
    monkeypatch.setattr(mod7b, "_spawn_guardian", lambda job: True)
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap7b:
        mod7b._arm(_job("j7b", phase=ru.PHASE_MOVED), {})
    assert mod7b._jobs["j7b"].phase == ru.PHASE_ARMED, mod7b._jobs["j7b"]
    assert any("重归组失败" in m for m in cap7b.messages), cap7b.messages

    # 单成员收口的重归组失败同样只告警不阻断(fd_16)
    mod8b = _bare_mod(api=types.SimpleNamespace(client=None, torrents_resume=lambda **kw: None))
    mod8b._ctx.grouping = types.SimpleNamespace(regroup_scope=_rg_boom)
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap8b:
        mod8b._finish_direct(_job("j8b", src="R:/src8b"))
    assert mod8b._jobs["j8b"].phase == ru.PHASE_DONE and mod8b._jobs["j8b"].reason == "direct"
    assert any("重归组失败" in m for m in cap8b.messages), cap8b.messages

    # 纵深单层: exists 不可判时不得因 getsize 报对就放行
    class _FA2:
        def exists(self, p):
            return False

        def getsize(self, p):
            return 10

    monkeypatch.setattr(fa_mod, "get_file_access", lambda: _FA2())
    mod9 = _bare_mod()
    job9 = _job("j9", plan={"files": [["a.mkv", 10]]})
    assert mod9._penetration_ok(job9) is False
    assert mod9._dst_ready(job9) is False

    # 删链失败必须留告警(残链排障线索)
    monkeypatch.setattr(afs, "alias_kind_of", lambda p: (_ for _ in ()).throw(RuntimeError("炸")))
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod._remove_links(["R:/x"])
    assert any("删链接失败" in m for m in cap.messages), cap.messages


def test_precheck_receipt_contract_and_add_param(tmp_path, monkeypatch):
    """预检拒收回执契约(rp_23~101) + 正常预检事实面(rp_108/114) + 添加预检空参(pa_4/12~18)"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, state="pausedUP", data_dir=False)
    mod = mgr.host.get("relocate")
    mgr.config.relocate.enabled = False
    it = mod.relocate_precheck(["HA"], dst)[0]
    assert set(it) == {"hashes", "cls", "reasons"}, set(it)
    assert it["cls"] == "blocked" and it["hashes"] == ["HA"], it
    assert it["reasons"][0]["gate"] == "disabled", it
    assert it["reasons"][0]["text"] == "整组迁移未启用(配置键 relocate.enabled) —— 路由层已 fail-closed, 此处为纵深防御", it

    mgr.config.relocate.enabled = True
    it = mod.relocate_precheck([], dst)[0]
    assert it["hashes"] == [] and it["reasons"][0]["gate"] == "param", it
    assert it["reasons"][0]["text"] == "未提供任何 hash(预检目标不能为空)", it
    it = mod.relocate_precheck(["HA"], "")[0]
    assert it["hashes"] == ["HA"] and it["reasons"][0]["gate"] == "param", it
    assert it["reasons"][0]["text"] == "未提供目标位置(location 不能为空)", it

    from auto_qb.core.modules.relocate_mod import RelocateModule as _RM
    m2 = _RM()
    m2._ctx = types.SimpleNamespace(config=types.SimpleNamespace(relocate=RelocateConfig(enabled=True)), store=None)
    it = m2.relocate_precheck(["HA"], dst)[0]
    assert it["hashes"] == ["HA"] and it["reasons"][0]["text"] == "模块上下文或种子存储不可用, 无法预检", it
    m2._ctx = types.SimpleNamespace(
        config=types.SimpleNamespace(relocate=RelocateConfig(enabled=True)),
        store=types.SimpleNamespace(by_hash={}),
        api=None,
    )
    it = m2.relocate_precheck(["HA"], dst)[0]
    assert it["hashes"] == ["HA"] and it["reasons"][0]["text"] == "qB 客户端未连接, 无法只读预检", it

    # 正常预检: 文件表必须进事实(读空 = 形态判定失真) + 汇总审计;
    # 换对 None client 真抛的记录 —— FakeTorrent 惰性缓存会让 client=None 变异不可区分(rp_108)
    # (计划 26-11-05-0808 S1 起, 预检前置部署闸: bt_backup 须指到真实目录才放行;
    # FakeClient 偏好无 resume_data_storage_type = SQLite 选项出现前的 qB, 按 Legacy 放行)
    _stub_cap(monkeypatch, file_kind="hardlink")
    mgr.config.bt_backup[f"{mgr.config.qbittorrent.host}:{mgr.config.qbittorrent.port}"] = str(tmp_path)
    for h in ("HA", "HB"):
        mgr.store.by_hash[h] = types.SimpleNamespace(
            hash=h,
            save_path=src,
            name="Show",
            log_repr=h,
            progress=1.0,
            state="pausedUP",
            state_enum=None,
            files=lambda c: [_fake_file("Show/e00.mkv", 64),
                             _fake_file("Show/e01.mkv", 64)]
            if c is not None else (_ for _ in ()).throw(RuntimeError("no client"))
        )
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        items = mod.relocate_precheck(["HA"], dst)
    assert items[0]["cls"] == "ok" and items[0]["file_count"] == 2, items
    assert any("迁移预检" in m for m in cap.messages), cap.messages

    # 添加预检: 空参拒收回执契约
    out = mod.precheck_add("", "n")
    assert out["cls"] == "blocked" and out["reasons"][0]["gate"] == "param", out
    assert set(out) >= {"save_path", "name", "requested_path", "reasons"}, set(out)
    assert out["save_path"] == "" and out["name"] == "n" and out["requested_path"] == "", out


# ---------- 覆盖率第三轮 T2b 补测(26-11-05): ctx 无 grouping 装配面 / 非别名路径删除 ----------


def test_arm_and_finish_direct_without_grouping_ctx(monkeypatch):
    """(T2b)ctx 没挂 grouping 模块(装配裁剪/裸替身) -> 重归组段整段跳过(260->266/278->283),
    落账/guardian/恢复成员照旧 —— grouping 是可选协作方, 不是硬依赖"""
    spawned = []
    mod = _bare_mod(api=types.SimpleNamespace(client=None, torrents_resume=lambda **kw: None))
    monkeypatch.setattr(mod, "_spawn_guardian", lambda job: spawned.append(job.job_id) or True)
    mod._arm(_job("j1", phase=ru.PHASE_MOVED), {})
    assert mod._jobs["j1"].phase == ru.PHASE_ARMED and mod._jobs["j1"].attempts == 0, mod._jobs["j1"]
    assert spawned == ["j1"], "guardian 照拉"

    mod2 = _bare_mod(api=types.SimpleNamespace(client=None, torrents_resume=lambda **kw: None))
    mod2._finish_direct(_job("j2", src="R:/src2"))
    assert mod2._jobs["j2"].phase == ru.PHASE_DONE and mod2._jobs["j2"].reason == "direct", mod2._jobs["j2"]


def test_remove_links_skips_non_alias_paths(tmp_path):
    """(T2b)非别名路径(709->705): alias_kind_of 为 None -> 跳过不删不计; 空串条目同轮跳过
    —— 幂等重删只对真别名生效, 普通文件不得被 remove_alias 波及"""
    plain = tmp_path / "plain.txt"
    plain.write_text("x")
    mod = _bare_mod()
    assert mod._remove_links([str(plain), "", None]) == 0
    assert plain.exists(), "非别名路径不得被删"
