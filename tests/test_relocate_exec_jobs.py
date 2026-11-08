"""test_relocate_exec_jobs 测试计划: 整组迁移执行体 / 对账 / 收尾 guardian / 三入口接线
(计划 26-10-18-1604 §04 P3/P5/P6)

验收判据(plan §04):
- P3: Fake qB 集成覆盖五场景 —— 正常、停滞判失败(不搬回)、长耗时转 watching(不判失败)、
  第 3 条链接失败 ⇒ 删已建链接 + 转收尾、qB 中途断连(不重复下发); 主循环零阻塞(单步 < 50ms)。
- P5: 关闭时调用序列与今日一致(守阵); 开启时三入口(单件/批量/规则)都产生 job。
- P6: 对账表 8 行逐行(纯函数层在 test_relocate_units)、撤销回滚、guardian 三证后删链接。
- 真机 qB 验证留待他人在有 qB 的环境执行(本轮 Fake qB 全替身)。

## 测试计划(每个测试函数一条)
- test_cancel_requires_cost_confirmation_then_rolls_back: 撤销先给成本, 确认后删链接 + 搬回
- test_jobs_persist_and_reload: job 账落 state 并能重启恢复(非终态重挂 relocating 登记)
- test_entry_single_and_bulk_create_jobs: 开关开: 单件/批量都产生 job(回执 truth 计数)
- test_entry_bulk_missing_hashes_in_receipt: 批量移动(整组迁移开)缺失计数进回执(issue 26-11-07-0536 #3)
  —— 仍有缺失时 error 带「N/M 个种子不存在或已被删除」+ relocate 非零桶计数段(「已发起 M 项 / 另有 N 项待确认」),
  truth 明细照常带出(与 handler 缺失契约/其余动作同口径)
### P1-T1.1 守卫与容错簇(计划 26-10-20-2101)
- test_persist_noop_when_state_box_unavailable: state 账不可用时 _persist 静默返回
### 收口 / 退避守卫(issues 26-10-30-0616 批A: resume_hashes 失败路径 / dry_run 短路 / 重试退避)
- test_cancel_failed_resumes_members: 撤销搬回被拒 ⇒ failed(cancel_failed) 且恢复成员
- test_cancel_dry_run_is_blocked: dry-run 撤销零动作(不删链接不搬回)
### W8(R32) S5 补测(变异审计真洞守阵, 分类: tmp-analysis/w8-r32/classify-mod-{a,b}.md)
- test_group_facts_gate_inputs_block_gates: 事实包字段丢失/损坏仍拦闸(incomplete/moving/third_party_link/hardlink 四闸) + reparse 非零 tag/缺省 tag 判别
- test_group_facts_same_fs_free_space_retired: P3 free-space 代理退出 proved(吻合只作参考 note,
  proved/negative 不随它变)
- test_group_facts_weak_positive_degrades_to_note: 弱证据任何方向都不一锤定音(R1#35)——
  B′/dst visibility_only 的 positive 不置 same_fs_proved、B′ 级 negative 不置
  same_fs_negative(降 note 照走执行链一次性强探测, E1 缓存 passed 凭缓存放行);
  src 侧 D 级 positive 直接证明、D 级 negative 硬拦(判定序两面守阵)
- test_group_facts_fact_sources_faces: 文件表/目标卷剩余/listing 失败三事实源的单点行为
- test_group_facts_platform_and_unc_faces: 未证明不撞 platform 闸 + 跨 OS 行拦 multi / cap 崩溃面 / UNC dir 形态 / file_alias_kind 实参
  + 同卷硬链接兜底(same_volume 实参丢失 ⇒ capability_ok 翻假)
- test_group_facts_long_path_and_start_plan_faces: 长路径校正(260) + 执行入口 plan 同参 + file_link_error 文案 + hard_max 配置
- test_group_facts_multi_root_and_hard_max_faces: 多首段内容根回落 + 硬上限拒绝
- test_group_facts_dir_link_note_faces: 目录级链接 note(OSError 与 realpath 两段拼接)
- test_start_job_ids_and_receipt_contract: job_id 三分量进键 + started 回执契约
- test_start_job_inflight_guard: 在途拦截(非终态拦/终态放)与拦截回执契约
- test_start_job_pause_issue_args_and_crash_window: 暂停/下发实参钉死 + 崩溃窗补发
  + 补发 setLocation 入参(只发 mover) + 发起 rt 初值(stall_since/last_size/sample_ts)
- test_start_job_plan_faces: plan 消费 file_link_error 与 hard_max 配置
- test_start_wiring_and_load_jobs: start 接线(ctx/dry/enabled)与 _load_jobs rt 账
- test_cancel_write_intent_faces: 撤销写意图(删链接/搬回实参/reason/回执)
### 撤销安全守卫(issue 26-11-07-0527 R1#23/R1#24)
- test_cancel_blocked_when_alias_left_behind: 删链接失败有残留 ⇒ blocked 留现场(不搬回不终态
  不恢复成员), 修好后重试撤销照常搬回(校验式不卡死重试)
- test_cancel_proceeds_when_links_all_removed: 删净 ⇒ 照常搬回; 账面链接已被外部先行删掉的
  幂等面不误判残留(「已消失 ≠ 残留」, 计数式校验会把撤销永久卡死)
- test_cancel_rejected_in_moving_and_watching_phases: MOVING/WATCHING 在途搬迁拒绝取消
  (连成本确认面都不给), 不下发回搬指令、不终态、不恢复成员, 文案写明相位与可选动作
### 生命周期账闸(issue 26-11-07-0527)
- test_stop_skips_persist_when_ledger_not_loaded: enabled=false 启动(本会话未接管账)——
  stop 跳过补写, state 既有在途账原样保留(无条件 _persist = 整段重写清账, 优雅退出
  紧跟 ctx.state.save() 落盘后未收尾 job 永久失账)
- test_stop_persists_after_ledger_touched_this_session: 本会话接管过账(enabled=true 恢复
  或 register_job 动过)—— stop 照常补写(不动内容 = 同值重写; 仅动内存的变更靠补写落盘),
  不得矫枉过正把合法落盘也禁了
- test_apply_hot_enable_restores_ledger_and_interception: 热启用(enabled 假->真)补
  _load_jobs: state 里的历史在途 job 灌回内存 + relocating_hashes/别名根登记重建;
  持续启用下的段变化不重灌(不重置在途 job 的运行期账 _rt)
"""

import os

import time

import types

import pytest

from dataclasses import replace

from auto_qb.core.modules import relocate_units as ru

from auto_qb.infra import relocate_journal

from helpers import pin_disk_usage, relocate_env

from auto_qb.config.models import Config, RelocateConfig

from auto_qb.core.modules.grouping_mod import group_key_of

from auto_qb.core.modules.relocate_mod import RelocateModule
from auto_qb.core.modules.relocate_common import _native as _mod_native

from auto_qb.infra import alias_fs as afs

from auto_qb.infra import file_access as fa_mod

from auto_qb.infra import utils as infra_utils

from helpers import FakeClient, FakeTorrent, _fake_file, capture_logs

from relocate_exec_support import (
    _armed_env,
    _bare_mod,
    _facts_mod,
    _fake_fs,
    _job,
    _rec,
    _run_ticks,
    _simulate_moved,
    _solo_member,
    _spy_spawn,
    _stub_cap,
    _stub_lstat,
    _stub_probe_pass,
)


@pytest.fixture(autouse=True)
def _exec_probe_pass(monkeypatch):
    """执行链 E1 强探测默认放行(issue 26-11-07-0527 R1#35 拆桩面)

    弱证据(B′/visibility_only)positive 不再置 same_fs_proved 后, 多成员组执行链必走
    一次 run_probe —— FakeClient 替身无列目录端点且 recheck 不推进度, 真跑必然证读超时
    (实测 10s)判 blocked。本文件用例不关心探测本身(决策表单点在
    test_relocate_exec_probe_gate.py), 统一经 _stub_probe_pass 放行。
    """
    _stub_probe_pass(monkeypatch)


def test_cancel_requires_cost_confirmation_then_rolls_back(tmp_path, monkeypatch):
    """撤销: 未确认只回成本; 确认后删链接 + 搬回 + cancelled + 恢复运行态"""
    mgr, client, mod, job_id, spawned, src, dst, content = _armed_env(tmp_path, monkeypatch)
    first = mod.relocate_cancel(job_id)
    assert first["cls"] == "confirm" and first["cost"]["bytes"] > 0
    assert os.path.exists(mod.get_job(job_id).alias_paths[0]), "未确认时不得动链接"

    client.calls.clear()
    r = mod.relocate_cancel(job_id, cost_confirmed=True)
    assert r["cls"] == "ok" and mod.get_job(job_id).phase == ru.PHASE_CANCELLED
    assert mod.get_job(job_id).alias_paths == ()
    assert ("set_location", src) in client.calls, client.calls
    assert any(c[0] == "resume" for c in client.calls), client.calls


def test_jobs_persist_and_reload(tmp_path, monkeypatch):
    """job 账落 state; 重启恢复非终态 job 并重挂 relocating 登记"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, state="uploading")
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    items = mod.relocate_execute(["HA"], dst)
    assert items[0]["cls"] == "started", items
    job_id = items[0]["job_id"]
    assert job_id in (mgr.state.get("relocate") or {}).get("jobs", {})

    mod2 = type(mod)(mgr.ctx)
    n = mod2._load_jobs()
    assert n == 1 and mod2.get_job(job_id).phase == ru.PHASE_MOVING
    assert {"HA", "HB"} <= mgr.store.relocating_hashes


def test_entry_single_and_bulk_create_jobs(tmp_path, monkeypatch):
    """开关开: 单件与批量都产生 job, 回执 truth 计数可读"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, file_count=2, state="uploading")
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    mgr.web.commands.put(("set_torrent_location", {"hash": "HA", "location": dst, "cmd_id": "c1"}))
    mgr.web.consume_commands()
    rec = mgr.web.results["c1"]
    assert rec["status"] == "ok" and rec["truth"]["summary"]["started"] == 1, rec
    assert len(mod.jobs_view()) == 1

    # 批量: 同一组再选一个成员 -> 幂等 skip(同组同目标的 job 在途, 不新建第二条账)
    mgr.web.commands.put(("bulk_torrents", {"hashes": ["HB"], "action": "location", "location": dst, "cmd_id": "c2"}))
    mgr.web.consume_commands()
    rec2 = mgr.web.results["c2"]
    assert rec2["status"] == "ok" and rec2["truth"]["summary"]["skip"] == 1, rec2
    assert len(mod.jobs_view()) == 1


def test_entry_bulk_missing_hashes_in_receipt(tmp_path, monkeypatch):
    """批量移动(整组迁移开)缺失计数进回执(issue 26-11-07-0536 #3): 与其余动作同契约

    handler 文档自订契约「不在快照中的 hash 跳过, 仍有缺失时回执 error 带缺失计数」:
    整组迁移分支此前提前 return, missing/missing_groups 不进回执 —— 批量移 2 个(1 个已被
    删)只看到 1 个的结果, 缺失零提示。修后与既有 location 路径(recheck/skip_check/其余
    动作共用 _bulk_missing_msgs 单点)同口径: error 回执带「N/M 个种子不存在或已被删除」,
    且 relocate 侧非零桶计数以「; 已发起 M 项 / 另有 N 项待确认」形态追加进文案(批C评审:
    缺失强制 error 后前端确认门控读 r.ok 不再开框, 用户可见层不丢事实),
    truth 照常带 items+summary(在册成员照常发起迁移, 明细不因缺失报错而丢失)。
    """
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, file_count=2, state="uploading")
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    # HA 在册, GONE 不在快照(已被删): 1/2 缺失
    mgr.web.commands.put(
        ("bulk_torrents", {
            "hashes": ["HA", "GONE"],
            "action": "location",
            "location": dst,
            "cmd_id": "c1"
        })
    )
    mgr.web.consume_commands()
    rec = mgr.web.results["c1"]
    assert rec["status"] == "error", rec
    assert rec["error"] == "1/2 个种子不存在或已被删除; 已发起 1 项", rec
    # truth 明细不丢: 在册成员照常发起(与既有 location 路径回执共用同一缺失文案单点)
    assert rec["truth"]["summary"]["started"] == 1, rec
    assert mod.jobs_view(), "在册成员照常发起迁移"
    # 缺失+待确认混合(直驱回执单点, 仿 test_web_commands_bulk 直驱模式): confirm 门控被
    # error 状态关掉后, 待确认计数必须仍在文案里可见
    mgr._relocate_receipt(
        "c2",
        [{
            "cls": "confirm",
            "reasons": []
        }],
        "批量移动位置(整组迁移)",
        missing_msgs=["1/2 个种子不存在或已被删除"],
    )
    rec2 = mgr.web.results["c2"]
    assert rec2["status"] == "error", rec2
    assert rec2["error"] == "1/2 个种子不存在或已被删除; 另有 1 项待确认", rec2
    assert rec2["truth"]["summary"]["confirm"] == 1, rec2


def test_persist_noop_when_state_box_unavailable(monkeypatch):
    """state 账不可用(容器非 dict)时 _persist 静默返回, 不炸主循环"""
    mod = _bare_mod()
    monkeypatch.setattr(mod, "_state_jobs", lambda: None)
    mod._persist()  # 不抛


def test_cancel_failed_resumes_members(tmp_path):
    """撤销搬回被拒 ⇒ failed(cancel_failed) 且恢复成员(搬回没成, 组不该继续被按住)"""
    resumed = []
    mod = _bare_mod(
        api=types.SimpleNamespace(
            torrents_set_location=lambda **kw: (_ for _ in ()).throw(RuntimeError("409")),
            torrents_resume=lambda **kw: resumed.append(list(kw["torrent_hashes"])),
        ),
        data_dir=str(tmp_path),
    )
    mod._jobs["j1"] = _job(phase=ru.PHASE_ARMED, resume_hashes=("HA", ))
    out = mod.relocate_cancel("j1", cost_confirmed=True)
    assert out["cls"] == "blocked" and out["reasons"][0]["gate"] == "cancel_failed", out
    assert mod._jobs["j1"].phase == ru.PHASE_FAILED and mod._jobs["j1"].reason == "cancel_failed"
    assert resumed == [["HA"]], f"撤销失败必须恢复成员: {resumed}"


def test_cancel_dry_run_is_blocked(tmp_path, monkeypatch):
    """dry-run 撤销零动作: 回执 blocked(dry_run), 不删链接不搬回(搬回要再复制全量数据)"""
    mgr, client, mod, job_id, spawned, src, dst, content = _armed_env(tmp_path, monkeypatch)
    links = list(mod.get_job(job_id).alias_paths)
    assert links, "armed 现场应有链接(撤销要删的对象)"
    mod._dry = True
    out = mod.relocate_cancel(job_id, cost_confirmed=True)
    assert out["cls"] == "blocked" and out["reasons"][0]["gate"] == "dry_run", out
    assert mod.get_job(job_id).phase == ru.PHASE_ARMED, "撤销不得改相位"
    assert [c for c in client.calls if c[0] == "set_location"][-1][1] == dst, "不得搬回源路径"
    assert any(os.path.exists(p) for p in links), "链接必须还在"


def test_cancel_blocked_when_alias_left_behind(tmp_path, monkeypatch):
    """撤销删链接数不齐(残留别名仍指向 dst) ⇒ blocked 留现场: 不搬回不终态; 修好后重试照常搬回(R1#23)

    残留别名在场时下发 setLocation(src) 搬回, 路径会穿过别名指回 dst(copy-onto-self),
    且 CANCELLED 清空 alias_paths 后残留链接脱离 job 账失管 —— 必须先拦下。
    """
    mgr, client, mod, job_id, spawned, src, dst, content = _armed_env(tmp_path, monkeypatch)
    links = list(mod.get_job(job_id).alias_paths)
    assert len(links) >= 1, "armed 现场应有链接(撤销要删的对象)"
    victim = links[0]
    real_remove = afs.remove_alias

    def _fail_one(p):
        if os.path.normcase(os.path.abspath(p)) == os.path.normcase(os.path.abspath(victim)):
            raise PermissionError(32, "另一个程序正在使用此文件(句柄占用)")
        return real_remove(p)

    monkeypatch.setattr(afs, "remove_alias", _fail_one)
    client.calls.clear()
    out = mod.relocate_cancel(job_id, cost_confirmed=True)
    assert out["cls"] == "blocked" and out["reasons"][0]["gate"] == "cancel_alias_left", out
    text = out["reasons"][0]["text"]
    assert victim in text and dst in text and "重试" in text, text
    # 留现场: 相位/账面/链接都原样, 不搬回不恢复成员不落取消终态(对账照常看到活别名)
    job = mod.get_job(job_id)
    assert job.phase == ru.PHASE_ARMED and job.alias_paths == tuple(links), (job.phase, job.alias_paths)
    assert os.path.exists(victim), "删除失败的残留别名必须留在现场"
    assert not any(c[0] == "set_location" for c in client.calls), client.calls
    assert not any(c[0] == "resume" for c in client.calls), client.calls
    assert (relocate_journal.read_journal(str(tmp_path / "data"), job_id) or {}).get("phase") != ru.PHASE_CANCELLED

    # 修好后重试: 残留删净、账面里已先行消失的链接幂等跳过, 照常搬回(校验式不卡死重试)
    monkeypatch.undo()
    r = mod.relocate_cancel(job_id, cost_confirmed=True)
    assert r["cls"] == "ok" and mod.get_job(job_id).phase == ru.PHASE_CANCELLED, r
    assert ("set_location", src) in client.calls, client.calls
    assert any(c[0] == "resume" for c in client.calls), client.calls


def test_cancel_proceeds_when_links_all_removed(tmp_path, monkeypatch):
    """撤销删净 ⇒ 照常搬回(新守卫不误伤正常撤销); 账面链接已被外部先行删掉不误判残留(R1#23)

    「已消失 ≠ 残留」: 校验式看的是删后还有没有认得出的别名留在现场, 不看删除计数 ——
    账面里被先行删掉的链接(外部删除/上次撤销半途)永远数不齐, 计数式会把撤销永久卡死。
    """
    mgr, client, mod, job_id, spawned, src, dst, content = _armed_env(tmp_path, monkeypatch)
    links = list(mod.get_job(job_id).alias_paths)
    os.remove(links[0])  # 外部先行删掉一条(账面仍记)
    client.calls.clear()
    out = mod.relocate_cancel(job_id, cost_confirmed=True)
    assert out["cls"] == "ok", out
    saved = mod.get_job(job_id)
    assert saved.phase == ru.PHASE_CANCELLED and saved.alias_paths == (), saved
    assert ("set_location", src) in client.calls, client.calls
    assert not any(os.path.exists(p) for p in links), "账面链接必须删净再搬回(残留 = 回搬穿别名)"


def test_cancel_rejected_in_moving_and_watching_phases(tmp_path):
    """MOVING/WATCHING 期取消拒绝(R1#24): qB 在途搬迁时不下发回搬指令、不终态、不恢复成员, 文案写明相位与可选动作"""
    locs, resumed = [], []
    mod = _bare_mod(
        api=types.SimpleNamespace(
            torrents_set_location=lambda **kw: locs.append(dict(kw)),
            torrents_resume=lambda **kw: resumed.append(list(kw["torrent_hashes"])),
        ),
        data_dir=str(tmp_path),
    )
    for phase in (ru.PHASE_MOVING, ru.PHASE_WATCHING):
        mod._jobs["j1"] = _job("j1", phase=phase, resume_hashes=("HA", ))
        out = mod.relocate_cancel("j1", cost_confirmed=True)
        assert out["cls"] == "blocked" and out["reasons"][0]["gate"] == ru.GATE_MOVING, (phase, out)
        text = out["reasons"][0]["text"]
        assert phase in text and "在途搬迁" in text and "armed" in text, (phase, text)
        assert mod._jobs["j1"].phase == phase, "拒绝取消不得改相位"
        assert not locs and not resumed, (phase, locs, resumed)
    # 在途搬迁连成本确认面都不给(与 settled 检查同原则: 不误导可撤)
    mod._jobs["j1"] = _job("j1", phase=ru.PHASE_MOVING, resume_hashes=("HA", ))
    first = mod.relocate_cancel("j1")
    assert first["cls"] == "blocked" and first["reasons"][0]["gate"] == ru.GATE_MOVING, first
    assert "cost" not in first, "硬拒绝不给成本面板"


def test_group_facts_gate_inputs_block_gates(monkeypatch):
    """事实包字段丢失/损坏必须仍能拦闸(incomplete/moving/third_party_link/hardlink 四闸)

    盖 classify-mod-a 中危簇①(gf_293/294/329/331~340: progresses/states 丢失 → 闸门漏判)
    与 gf_284/314/230/232/233/237(第三方链接/硬链接代表文件失真): 任一字段被 None 化/
    键漂移/切片错位, 这里全部当场红。
    """
    client = FakeClient()
    client.files_map["HA"] = [_fake_file("Show/e00.mkv", 64), _fake_file("Show/e01.mkv", 64)]
    client.files_map["HB"] = client.files_map["HA"]

    def _facts(progress=1.0, state="pausedUP"):
        mod = _facts_mod()
        _fake_fs(monkeypatch, exists=False, scandir_boom=True)
        _stub_cap(monkeypatch, file_kind="hardlink")
        return mod, mod._group_facts([_rec("HA", progress=progress, state=state), _rec("HB")], "R:/dst", client)

    for p in (0.0, 0.5):  # progress=0.0 是常态入口(刚加种子), or 1.0 变异专门打它
        mod, facts = _facts(progress=p)
        assert facts.progresses[0] == p, facts.progresses
        v = ru.evaluate_group(facts)
        assert v["cls"] == "blocked" and any(r["gate"] == "incomplete" for r in v["reasons"]), (p, v)

    mod, facts = _facts(state="moving")
    assert facts.states[0] == "moving", facts.states
    v = ru.evaluate_group(facts)
    assert v["cls"] == "blocked" and any(r["gate"] == "moving" for r in v["reasons"]), v

    _stub_lstat(monkeypatch, islnk=True)
    mod, facts = _facts()
    assert facts.third_party_link_files == (facts.files[0][0], ), facts.third_party_link_files
    v = ru.evaluate_group(facts)
    tp = next(r for r in v["reasons"] if r["gate"] == "third_party_link")
    assert facts.files[0][0] in tp["text"], tp  # 文案必须点名首文件(names[1] 错位当场红)

    _stub_lstat(monkeypatch, islnk=False, nlink=2)
    mod, facts = _facts()
    assert facts.hardlink_files == (facts.files[0][0], ), facts.hardlink_files
    v = ru.evaluate_group(facts)
    hl = next(r for r in v["reasons"] if r["gate"] == "hardlink")
    assert facts.files[0][0] in hl["text"], hl

    # reparse 点非零 tag(Windows junction/目录链接, 非 S_ISLNK)也必须判第三方链接:
    # `or tag` 被 and 化/反化会漏判(gf_220/221/227/228 簇)。
    _stub_lstat(monkeypatch, islnk=False, tag=0xA0000003)  # IO_REPARSE_TAG_MOUNT_POINT
    mod, facts = _facts()
    assert facts.third_party_link_files == (facts.files[0][0], ), facts.third_party_link_files
    v = ru.evaluate_group(facts)
    assert any(r["gate"] == "third_party_link" for r in v["reasons"]), v

    # tag 缺省(POSIX stat 形态): getattr 默认值必须为假值, 否则每个普通文件都会被误判链接。
    _stub_lstat(monkeypatch, islnk=False, nlink=1, omit_tag=True)
    mod, facts = _facts()
    assert facts.third_party_link_files == () and facts.hardlink_files == (), (
        facts.third_party_link_files,
        facts.hardlink_files,
    )

    assert facts.name == "Show" and facts.target == "R:/dst"  # 事实包身份面不得 None 化


def test_group_facts_same_fs_free_space_retired(monkeypatch):
    """P3 判据替换(计划 26-11-04-0055 §03.1): free-space 代理退出 proved ——
    qB 上报与任一侧吻合/不吻合都不再改变 proved; 证据不可判定时 proved=False +
    negative=False(待执行链强探测), 吻合侧只作参考 note(函数本体与单测保留)"""
    client = FakeClient()
    client.files_map["HA"] = [_fake_file("Show/e00.mkv", 64)]
    client.files_map["HB"] = client.files_map["HA"]
    qb_free = 1 << 40

    def _facts(free_by_path):
        mod = _facts_mod(server_free=qb_free)
        _fake_fs(monkeypatch, free_by_path=free_by_path)
        _stub_cap(monkeypatch, file_kind="hardlink")
        return mod._group_facts([_rec("HA"), _rec("HB")], "R:/dst", client)

    # 源侧吻合(正向迁移: qB 报的就是源卷; 旧判据会 proved=True): 现在只是参考 note
    facts = _facts(lambda p: qb_free if p == "R:/src" else (1 << 39))
    assert facts.target_free == 1 << 39, facts.target_free
    assert facts.same_fs_proved is False and facts.same_fs_negative is False
    assert "free-space 代理参考吻合" in facts.same_fs_note, facts.same_fs_note
    v = ru.evaluate_group(facts)
    assert all(r["gate"] != "same_fs" for r in v["reasons"]), v  # 未证明不再硬拦多成员组

    # 目标侧吻合(反向迁移/复位场景: 源是 T, qB 报 S): 同样只作参考 note
    facts2 = _facts(lambda p: qb_free if p == "R:/dst" else (1 << 39))
    assert facts2.same_fs_proved is False and facts2.same_fs_negative is False
    assert "free-space 代理参考吻合" in facts2.same_fs_note, facts2.same_fs_note

    # 两侧都不吻合: proved/negative 不变, note 不含 free-space 参考位
    facts3 = _facts(lambda p: 1 << 39)
    assert facts3.same_fs_proved is False and facts3.same_fs_negative is False
    assert "free-space" not in facts3.same_fs_note, facts3.same_fs_note
    v3 = ru.evaluate_group(facts3)
    assert all(r["gate"] != "same_fs" for r in v3["reasons"]), v3


def test_group_facts_weak_positive_degrades_to_note(monkeypatch):
    """弱证据任何方向都不一锤定音(R1#35, issue 26-11-07-0527): 只有 src 侧 D 级
    (实时 size+mtime 比对)positive 置 same_fs_proved、D 级 negative 置 same_fs_negative;
    B′(种子元数据 size)与 dst 侧 visibility_only(qB 能列出目标祖先, 证不了共享命名
    空间)两面正/负都降为 note —— 多成员组照走执行链一次性强探测; E1 缓存 passed 时
    凭缓存放行。"""
    from auto_qb.core.modules import relocate_proof as rp_mod
    from auto_qb.core.modules.relocate_probe import probe_fingerprint

    client = FakeClient()
    client.files_map["HA"] = [_fake_file("Show/e00.mkv", 64), _fake_file("Show/e01.mkv", 64)]
    client.files_map["HB"] = client.files_map["HA"]

    def _stub_evidence(src_ev, dst_ev):
        """path_evidence 判定层替身: src 侧(visibility_only=False)回 src_ev, dst 侧回 dst_ev"""
        def _fake(ctx, qb_dir, local_dir, files=(), visibility_only=False, sample_k=3):
            return dst_ev if visibility_only else src_ev

        monkeypatch.setattr(rp_mod, "path_evidence", _fake)

    def _mod():
        mod = _facts_mod()
        _fake_fs(monkeypatch, exists=False, scandir_boom=True)
        _stub_cap(monkeypatch, file_kind="hardlink")
        return mod

    # 1. src 侧 B′ positive: 不证明 —— note 点名弱证据与强探测去向, 闸门不硬拦多成员组
    mod = _mod()
    _stub_evidence(
        rp_mod.Evidence(rp_mod.POSITIVE, rp_mod.LEVEL_BPRIME, "本机 e00.mkv 的 size 与 qB 元数据相等(弱证据)"),
        rp_mod.Evidence(rp_mod.UNAVAILABLE, "", "目标链路本机不可读"),
    )
    facts = mod._group_facts([_rec("HA"), _rec("HB")], "R:/dst", client)
    assert facts.same_fs_proved is False and facts.same_fs_negative is False, facts.same_fs_note
    assert "仅弱证据吻合" in facts.same_fs_note and "B′" in facts.same_fs_note, facts.same_fs_note
    v = ru.evaluate_group(facts)
    assert all(r["gate"] != "same_fs" for r in v["reasons"]), v
    assert any("一次性强探测" in n for n in v["notes"]), v["notes"]

    # 2. dst 侧 visibility_only positive(src 不可判定): 同样只作弱证据
    mod = _mod()
    _stub_evidence(
        rp_mod.Evidence(rp_mod.UNAVAILABLE, "", "qB 列目录端点不可用"),
        rp_mod.Evidence(rp_mod.POSITIVE, rp_mod.LEVEL_D, "qB 列目录成功, qB 看得见该目录"),
    )
    facts2 = mod._group_facts([_rec("HA"), _rec("HB")], "R:/dst", client)
    assert facts2.same_fs_proved is False and facts2.same_fs_negative is False, facts2.same_fs_note
    assert "仅弱证据吻合" in facts2.same_fs_note and "visibility_only" in facts2.same_fs_note, facts2.same_fs_note

    # 3. 弱证据 + E1 缓存 passed: 机器级强证明在先, 凭缓存放行(proved=True, note 注明)
    mod = _mod()
    mod._ctx.config.qbittorrent = types.SimpleNamespace(
        host="127.0.0.1", port=8080, username="", password="", api_key=""
    )
    # 预播种带盐: ensure 先生成并持久化盐, plan 只读面读同盐 => 覆盖「带盐预检读」形态
    # (无盐预播种在 fresh state 下只碰巧覆盖「双方都无盐」退化形态)
    mod.probe_put(probe_fingerprint(mod._ctx.config.qbittorrent, mod.probe_salt_ensure()), "passed", {"method": "e1"})
    _stub_evidence(
        rp_mod.Evidence(rp_mod.UNAVAILABLE, "", "qB 列目录端点不可用"),
        rp_mod.Evidence(rp_mod.POSITIVE, rp_mod.LEVEL_D, "qB 列目录成功, qB 看得见该目录"),
    )
    facts3 = mod._group_facts([_rec("HA"), _rec("HB")], "R:/dst", client)
    assert facts3.same_fs_proved is True, facts3.same_fs_note
    assert "E1 缓存" in facts3.same_fs_note and "弱证据" in facts3.same_fs_note, facts3.same_fs_note

    # 4. src 侧 D 级 positive(唯一强证据面): 维持直接证明(守阵防收窄过头)
    mod = _mod()
    _stub_evidence(
        rp_mod.Evidence(rp_mod.POSITIVE, rp_mod.LEVEL_D, "代表文件 e00.mkv 的 size+mtime 与本机完全相等"),
        rp_mod.Evidence(rp_mod.UNAVAILABLE, "", "目标链路本机不可读"),
    )
    facts4 = mod._group_facts([_rec("HA"), _rec("HB")], "R:/dst", client)
    assert facts4.same_fs_proved is True and "D 级" in facts4.same_fs_note, facts4.same_fs_note
    assert "弱证据" not in facts4.same_fs_note, facts4.same_fs_note

    # 5. src B′ 判负 + dst visibility positive(弱证据互搏): 不判死 —— negative=False,
    #    note 同时带出「弱证据吻合」与「弱证据判负」两面, 交执行链强探测定夺
    #    (R1#35 评审: 同机场景 qB<5.0 无列目录端点走 B′, 文件改过 size 判负属正常漂移,
    #    旧 proved 经 dst 可见性放行结果正确; B′ 判负硬拒会对同机用户失真)
    mod = _mod()
    _stub_evidence(
        rp_mod.Evidence(rp_mod.NEGATIVE, rp_mod.LEVEL_BPRIME, "本机 2 个文件的 size 与 qB 元数据全不等"),
        rp_mod.Evidence(rp_mod.POSITIVE, rp_mod.LEVEL_D, "qB 列目录成功, qB 看得见该目录"),
    )
    facts5 = mod._group_facts([_rec("HA"), _rec("HB")], "R:/dst", client)
    assert facts5.same_fs_proved is False and facts5.same_fs_negative is False, facts5.same_fs_note
    assert "仅弱证据吻合" in facts5.same_fs_note and "visibility_only" in facts5.same_fs_note, facts5.same_fs_note
    assert "弱证据判负" in facts5.same_fs_note and "不作确定性结论" in facts5.same_fs_note, facts5.same_fs_note
    v5 = ru.evaluate_group(facts5)
    assert all(r["gate"] != "same_fs" for r in v5["reasons"]), v5
    assert any("一次性强探测" in n for n in v5["notes"]), v5["notes"]

    # 6. src D 级 negative(唯一决定性判负面): 硬拦不变(same_fs_negative=True + gate blocked)
    mod = _mod()
    _stub_evidence(
        rp_mod.Evidence(rp_mod.NEGATIVE, rp_mod.LEVEL_D, "抽中的 2 个代表文件 size/mtime 与本机全不等"),
        rp_mod.Evidence(rp_mod.UNAVAILABLE, "", "目标链路本机不可读"),
    )
    facts6 = mod._group_facts([_rec("HA"), _rec("HB")], "R:/dst", client)
    assert facts6.same_fs_proved is False and facts6.same_fs_negative is True, facts6.same_fs_note
    assert "判负详情" in facts6.same_fs_note, facts6.same_fs_note
    v6 = ru.evaluate_group(facts6)
    gate6 = next(r for r in v6["reasons"] if r["gate"] == "same_fs")
    assert v6["cls"] == "blocked" and gate6["cls"] == "blocked", v6


def test_group_facts_fact_sources_faces(monkeypatch):
    """三事实源单点: 文件表来自 client(gf_9)/目标卷剩余可读(gf_101)/listing 失败=不可判定(gf_53)"""
    client = FakeClient()
    client.files_map["HA"] = [_fake_file("Show/e00.mkv", 64)]
    client.files_map["HB"] = client.files_map["HA"]
    mod = _facts_mod()
    _fake_fs(monkeypatch, exists=False, scandir_boom=True)
    _stub_cap(monkeypatch, file_kind="hardlink")
    facts = mod._group_facts([_rec("HA"), _rec("HB")], "R:/dst", client)
    assert facts.files == (("Show/e00.mkv", 64), ), facts.files  # 丢 client = 全组误拒面
    assert facts.target_free == 1 << 40, facts.target_free  # disk_usage(None) 化 = space 误拒面
    assert facts.content_root_exclusive is None, facts.content_root_exclusive  # listing 失败只许「不可判定」


def test_group_facts_platform_and_unc_faces(monkeypatch, tmp_path):
    """平台判定面: remote 拦 platform 闸(gf_139)/cap None 崩溃面(gf_142)/UNC dir 形态(gf_186~188)/
    file_alias_kind 实参 = bool(same_volume)(gf_151/152)"""
    client = FakeClient()
    client.files_map["HA"] = [_fake_file("Show/e00.mkv", 64)]
    client.files_map["HB"] = client.files_map["HA"]

    # P3: platform_verdict 的 remote 实参喂 same_fs_negative(确定性不共享)而非「未证明」
    # —— 未证明(两侧证据不可判定)不再让多成员组撞 platform 闸(执行链强探测兜底);
    # 平台闸的多成员拦截面改由跨 OS 容器行(link_visible_to_host=False)验证
    mod = _facts_mod(server_free=12345)
    _fake_fs(monkeypatch, free=1 << 40)
    _stub_cap(monkeypatch, link_visible=False)
    facts = mod._group_facts([_rec("HA"), _rec("HB")], "R:/dst", client)
    assert facts.same_fs_proved is False and facts.same_fs_negative is False, facts
    v = ru.evaluate_group(facts)
    assert any(r["gate"] == "platform" for r in v["reasons"]), v
    assert all(r["gate"] != "same_fs" for r in v["reasons"]), v

    # 健康能力包: platform_verdict 必须拿到 cap(None 化 = AttributeError 崩溃面)
    mod2 = _facts_mod(server_free=1 << 40)
    _stub_cap(monkeypatch, file_kind="hardlink")
    facts2 = mod2._group_facts([_rec("HA"), _rec("HB")], "R:/dst", client)
    assert facts2.capability_ok is True, facts2.capability_reason

    # UNC 目标: dir 形态严格随 dir_symlink.ok 走
    mod3 = _facts_mod(server_free=1 << 40)
    _stub_cap(monkeypatch, file_kind="hardlink", dir_symlink_ok=True)
    facts3 = mod3._group_facts([_rec("HA"), _rec("HB")], r"\\server\share", client)
    assert facts3.dir_link_kind == afs.KIND_SYMLINK, facts3.dir_link_kind
    _stub_cap(monkeypatch, file_kind="hardlink", dir_symlink_ok=False, dir_symlink_error="不可建")
    facts4 = mod3._group_facts([_rec("HA"), _rec("HB")], r"\\server\share", client)
    assert facts4.dir_link_kind is None, facts4.dir_link_kind

    # file_alias_kind 的实参必须是真 bool(same_volume): 真实同卷目录上应传 True
    mgr, client2, src, dst, content, files = relocate_env(tmp_path / "sv", state="pausedUP")
    cap, seen = _stub_cap(monkeypatch, file_kind="hardlink")
    facts5 = mgr.host.get("relocate")._group_facts([mgr.store.by_hash["HA"], mgr.store.by_hash["HB"]], dst, client2)
    assert seen["arg"] is True, seen
    assert facts5.file_link_kind == "hardlink", facts5.file_link_kind

    # 同卷 + 文件符号链接不可用、硬链接可用(Windows 同卷唯一可建文件别名的组合):
    # `same_volume=bool(same_vol)` 被 None 化 / 实参删除 / 内层 bool(None) 都会让
    # platform_verdict 走不到硬链接兜底 => capability_ok 翻假(gf_140/144/147)。
    mgr2, client3, src3, dst3, content3, files3 = relocate_env(tmp_path / "hl", state="pausedUP")
    _stub_cap(monkeypatch, hardlink_ok=True)
    facts6 = mgr2.host.get("relocate")._group_facts([mgr2.store.by_hash["HA"], mgr2.store.by_hash["HB"]], dst3, client3)
    assert facts6.same_volume is True, facts6.same_volume
    assert facts6.capability_ok is True, facts6.capability_reason
    assert facts6.file_link_kind == afs.KIND_HARDLINK, facts6.file_link_kind


def test_group_facts_long_path_and_start_plan_faces(tmp_path, monkeypatch):
    """长路径校正(gf_281/311/347/348) + 执行入口 plan 同参(sj_39/50) + file_link_error 文案(sj_36/47/49)
    + hard_max 配置进 plan(sj_32/43)"""
    client = FakeClient()

    def _facts(conf=None, cap_kw=None, save_path="R:/src", target="R:/dst"):
        _fake_fs(monkeypatch, free=1 << 40)
        _stub_cap(monkeypatch, **(cap_kw or {"file_kind": "symlink"}))
        mod = _facts_mod(server_free=1 << 40, conf=conf)
        recs = [_rec("HA", save_path=save_path), _rec("HB", save_path=save_path)]
        return mod, recs, mod._group_facts(recs, target, client)

    # Windows 长路径: symlink 形态 + >= 260 => 拒绝且文案带实测数字
    monkeypatch.setattr(infra_utils, "is_windows", lambda: True)
    long_name = "n" * 250 + ".mkv"
    client.files_map["HA"] = [_fake_file("Show/" + long_name, 64)]
    client.files_map["HB"] = client.files_map["HA"]
    mod, recs, facts = _facts()
    assert facts.link_path_limit == afs.WIN_MAX_PATH, facts.link_path_limit
    v = ru.evaluate_group(facts)
    assert v["cls"] == "blocked" and any(r["gate"] == "form" and "路径过长" in r["text"] for r in v["reasons"]), v
    item = mod._start_job(recs, "R:/dst", facts, v, client)
    assert item["cls"] == "blocked" and any("路径过长" in r["text"] for r in item["reasons"]), item

    # POSIX 面: 无上限(恒 260 = 误拒长路径组)
    monkeypatch.setattr(infra_utils, "is_windows", lambda: False)
    _, _, facts2 = _facts()
    assert facts2.link_path_limit is None, facts2.link_path_limit

    # file_link_error 进拒绝文案(能力不可用 + 多成员)
    client.files_map["HA"] = [_fake_file("Show/e00.mkv", 64), _fake_file("Show/e01.mkv", 64)]
    client.files_map["HB"] = client.files_map["HA"]
    mod, recs, facts3 = _facts(cap_kw={"file_kind": None, "file_symlink_error": "需提权"})
    assert "文件级链接不可建" in facts3.file_link_error, facts3.file_link_error
    v3 = ru.evaluate_group(facts3)
    assert v3["cls"] == "blocked" and any("文件级链接不可建" in r["text"] for r in v3["reasons"]), v3

    # hard_max 从配置进 plan(2 > 1 => 硬上限拒绝; None 化/落缺省 2000 当场红)
    mod, recs, facts4 = _facts(
        conf=RelocateConfig(enabled=True, alias_file_threshold=1, hard_max_links=1), cap_kw={"file_kind": "hardlink"}
    )
    v4 = ru.evaluate_group(facts4)
    item4 = mod._start_job(recs, "R:/dst", facts4, v4, client)
    assert item4["cls"] == "blocked" and any("硬上限" in r["text"] for r in item4["reasons"]), item4


def test_group_facts_multi_root_and_hard_max_faces(tmp_path, monkeypatch):
    """多首段 -> 内容根回落 save_path 且 listing 必须有结论(gf_27); 硬上限拒绝可达(gf_283)"""
    client = FakeClient()
    content = tmp_path / "src"
    (content / "Show").mkdir(parents=True)
    (content / "Movie").mkdir()
    (content / "Show" / "e00.mkv").write_bytes(b"x" * 64)
    (content / "Movie" / "e01.mkv").write_bytes(b"x" * 64)
    dst = tmp_path / "dst"
    dst.mkdir()
    client.files_map["HA"] = [_fake_file("Show/e00.mkv", 64), _fake_file("Movie/e01.mkv", 64)]
    client.files_map["HB"] = client.files_map["HA"]
    _stub_cap(monkeypatch, file_kind="hardlink")
    mod = _facts_mod(server_free=1 << 40)
    facts = mod._group_facts([_rec("HA", save_path=str(content)), _rec("HB", save_path=str(content))], str(dst), client)
    assert facts.content_root_exclusive is False, facts.content_root_exclusive
    v = ru.evaluate_group(facts)
    assert all(r["gate"] != "target_unknown" for r in v["reasons"]), v  # content_root None 化 => 误判不可判定

    # 单文件平铺: 内容根 = save_path 本身, listing 同样必须有结论(gf_27: None 化 = 事实全丢)
    flat = tmp_path / "flat"
    flat.mkdir()
    (flat / "e00.mkv").write_bytes(b"x" * 64)
    (flat / "misc").mkdir()
    client.files_map["HD"] = [_fake_file("e00.mkv", 64)]
    hd = FakeTorrent(hash="HD", name="Flat", save_path=str(flat), progress=1.0, state="pausedUP")
    facts3 = mod._group_facts([hd], str(dst), client)
    assert facts3.content_root_exclusive is False, facts3.content_root_exclusive


def test_group_facts_dir_link_note_faces(monkeypatch):
    """目录级链接 note: 两段拼接(gf_240~256) —— 前缀/分隔/丢失全当场红"""
    client = FakeClient()
    client.files_map["HA"] = [_fake_file("Show/e00.mkv", 64)]
    client.files_map["HB"] = client.files_map["HA"]
    mod = _facts_mod(server_free=1 << 40)
    _stub_cap(monkeypatch, file_kind="hardlink")
    _fake_fs(monkeypatch, exists=True, realpath="Z:/elsewhere/Show")
    _stub_lstat(monkeypatch, islnk=False, nlink=1)  # 代表文件可读且非链接: note 只剩 realpath 一段
    facts = mod._group_facts([_rec("HA"), _rec("HB")], "R:/dst", client)
    cr = os.path.join("R:/src", "Show")  # 内容根经 os.path.join, 分隔符随平台
    assert facts.third_party_dir_note.startswith("检测到目录级链接("), facts.third_party_dir_note
    assert f"({cr} -> Z:/elsewhere/Show)" in facts.third_party_dir_note, facts.third_party_dir_note

    _stub_lstat(monkeypatch, boom=True)  # 代表文件不可读 + realpath 差异: 两段必须都在且单空格连接
    facts2 = mod._group_facts([_rec("HA"), _rec("HB")], "R:/dst", client)
    assert facts2.third_party_dir_note.startswith("代表文件不可读(远程/容器未映射?): 第三方链接与硬链接未识别"), \
        facts2.third_party_dir_note
    assert "未识别 检测到目录级链接" in facts2.third_party_dir_note, facts2.third_party_dir_note


def test_start_job_ids_and_receipt_contract(tmp_path, monkeypatch):
    """job_id 三分量(mover/target/src)各自进键(sj_5/6/8/9/10) + started 回执契约(sj_179~193)"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, state="pausedUP")
    src2 = _solo_member(mgr, client, tmp_path)
    mod = mgr.host.get("relocate")
    verdict = {"cls": "ok", "notes": [], "reasons": []}

    recs_a = [mgr.store.by_hash["HA"]]
    item_a = mod._start_job(recs_a, dst, mod._group_facts(recs_a, dst, client), verdict, client)
    recs_c = [mgr.store.by_hash["HC"]]
    item_c = mod._start_job(recs_c, dst, mod._group_facts(recs_c, dst, client), verdict, client)

    assert item_a["job_id"] == ru.job_id_for("HA", dst, src), item_a["job_id"]
    assert item_c["job_id"] == ru.job_id_for("HC", dst, src2), item_c["job_id"]
    assert item_a["job_id"] != item_c["job_id"], (item_a["job_id"], item_c["job_id"])

    assert item_a["cls"] == "started" and item_a["phase"] == ru.PHASE_MOVING, item_a
    assert set(item_a) >= {"job_id", "phase", "alias_kind", "link_count", "notes", "cls"}, set(item_a)
    assert item_a["notes"][-1] == "qB 正在搬迁, 完成后自动建别名并武装收尾", item_a["notes"]


def test_start_job_inflight_guard(tmp_path, monkeypatch):
    """在途拦截: 非终态拦(sj_11/12)、终态放(sj_15)、拦截回执契约(sj_16~27)"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, state="pausedUP")
    mod = mgr.host.get("relocate")
    recs = [mgr.store.by_hash["HA"]]
    facts = mod._group_facts(recs, dst, client)
    verdict = {"cls": "ok", "notes": [], "reasons": []}
    jid = ru.job_id_for("HA", dst, src)

    mod._jobs[jid] = ru.RelocateJob(job_id=jid, hashes=("HA", "HB"), mover="HA", src=src, dst=dst, scope=content)
    item = mod._start_job(recs, dst, facts, verdict, client)
    assert item["cls"] == "blocked" and item["job_id"] == jid, item
    assert set(item) >= {"cls", "job_id", "reasons"}, set(item)
    assert item["reasons"][0]["gate"] == "unfinished", item
    assert "已有在途迁移" in item["reasons"][0]["text"], item

    mod._jobs[jid] = ru.RelocateJob(
        job_id=jid, hashes=("HA", "HB"), mover="HA", src=src, dst=dst, scope=content, phase=ru.PHASE_FAILED
    )
    client.calls.clear()
    item2 = mod._start_job(recs, dst, facts, verdict, client)
    assert item2["cls"] == "started", item2
    assert ("set_location", dst) in client.calls, client.calls


def test_start_job_pause_issue_args_and_crash_window(tmp_path, monkeypatch):
    """暂停/下发实参钉死(sj_82/162/164) + 发起审计(sj_171/172) + 崩溃窗补发(sj_133)"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, state="uploading")
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    pauses, issues = [], []
    real_set = client.torrents_set_location
    monkeypatch.setattr(client, "torrents_pause", lambda **kw: pauses.append(list(kw["torrent_hashes"])))
    client.torrents_set_location = lambda **kw: issues.append((list(kw["torrent_hashes"]), kw["location"])
                                                             ) or real_set(**kw)
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        items = mod.relocate_execute(["HA"], dst)
    assert items[0]["cls"] == "started", items
    assert pauses == [["HA", "HB"]], pauses  # 暂停必须按住全组
    assert issues == [(["HA"], dst)], issues  # 下发只发 mover、目标不得空
    assert any("迁移发起" in m and "mover HA)" in m for m in cap.messages), cap.messages

    # 发起审计的哈希截断必须 [:8](两字符 mover 区分不了 [:9], 用长 hash 钉)
    mgr3, client3, src3, dst3, content3, files3 = relocate_env(tmp_path / "lg", state="pausedUP")
    _solo_member(mgr3, client3, tmp_path / "lg", h="HASHABCDEFGHI")
    mod3 = mgr3.host.get("relocate")
    _spy_spawn(mod3, [])
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap3:
        mod3.relocate_execute(["HASHABCDEFGHI"], dst3)
    assert any("迁移发起" in m and "mover HASHABCD)" in m for m in cap3.messages), cap3.messages

    # 崩溃窗: 账已落、setLocation 未发出 -> 相位机必须补发一次
    mgr2, client2, src2, dst2, content2, files2 = relocate_env(tmp_path / "cw", state="uploading")
    mod2 = mgr2.host.get("relocate")
    _spy_spawn(mod2, [])
    real2 = client2.torrents_set_location

    def _boom(**kw):
        raise RuntimeError("qB 拒了")

    client2.torrents_set_location = _boom
    with pytest.raises(RuntimeError):
        mod2.relocate_execute(["HA"], dst2)
    jid = next(iter(mod2._jobs))
    assert mod2._rt[jid]["issue"] is True, mod2._rt[jid]
    # 发起时的 rt 初值必须干净: 键名大小写漂移 / stall_since 非零 = 停滞时钟先手开跑
    # (sj_140/144/145; 先手开跑会让 `elif not rt.get("stall_since")` 分支永远轮不到)
    assert mod2._rt[jid]["last_size"] == -1 and mod2._rt[jid]["sample_ts"] == 0.0, mod2._rt[jid]
    assert mod2._rt[jid]["stall_since"] == 0.0, mod2._rt[jid]
    client2.torrents_set_location = real2
    mgr2.store.own_writes.clear()  # 暂停快照已回流(崩溃窗现场: 暂停早已生效)
    mod2.on_task_line()
    assert [c for c in client2.calls if c[0] == "set_location"] == [("set_location", dst2)], client2.calls
    # 补发路径的入参同样必须是 mover(且实参键在场): 缺省 None = qB 全局改路径(sm_41/43)
    assert client2.limit_location_hashes_calls == [("set_location", ["HA"])], client2.limit_location_hashes_calls


def test_start_job_plan_faces(tmp_path, monkeypatch):
    """plan 消费面: file_link_error 进拒绝文案(sj_36/47/49) + hard_max 从配置进 plan(sj_32/43)"""
    client = FakeClient()
    client.files_map["HA"] = [_fake_file("Show/e00.mkv", 64), _fake_file("Show/e01.mkv", 64)]
    client.files_map["HB"] = client.files_map["HA"]

    def _facts(cap_kw, conf=None, fs_kw=None):
        _fake_fs(monkeypatch, free=1 << 40, **(fs_kw or {}))
        _stub_cap(monkeypatch, **cap_kw)
        mod = _facts_mod(server_free=1 << 40, conf=conf)
        recs = [_rec("HA"), _rec("HB")]
        return mod, recs, mod._group_facts(recs, "R:/dst", client)

    mod, recs, facts = _facts({"file_kind": None, "file_symlink_error": "需提权"})
    assert "文件级链接不可建" in facts.file_link_error, facts.file_link_error
    v = ru.evaluate_group(facts)
    item = mod._start_job(recs, "R:/dst", facts, v, client)
    assert item["cls"] == "blocked" and any("文件级链接不可建" in r["text"] for r in item["reasons"]), item

    mod, recs, facts2 = _facts(
        {"file_kind": "hardlink"}, conf=RelocateConfig(enabled=True, alias_file_threshold=1, hard_max_links=1)
    )
    v2 = ru.evaluate_group(facts2)
    item2 = mod._start_job(recs, "R:/dst", facts2, v2, client)
    assert item2["cls"] == "blocked" and any("硬上限" in r["text"] for r in item2["reasons"]), item2

    # dir_link_error 进拒绝文案(文件级与目录级都不可建 + 内容根专属, sj_49)
    mod, recs, facts5 = _facts(
        {
            "file_kind": None,
            "file_symlink_error": "需提权",
            "hardlink_error": "x"
        },
        fs_kw={"scandir": [types.SimpleNamespace(name="e00.mkv"),
                           types.SimpleNamespace(name="e01.mkv")]}
    )
    assert "目录别名不可建" in facts5.dir_link_error, facts5.dir_link_error
    v5 = ru.evaluate_group(facts5)
    assert any("目录别名不可建" in r["text"] for r in v5["reasons"]), v5
    item5 = mod._start_job(recs, "R:/dst", facts5, v5, client)
    assert item5["cls"] == "blocked" and any("目录别名不可建" in r["text"] for r in item5["reasons"]), item5


def test_start_wiring_and_load_jobs(tmp_path, monkeypatch):
    """start 接线(ctx/dry/enabled: st_2/4/5/6/8/14/15) + _load_jobs rt 账逐键(lj_11~25)"""
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, state="uploading")
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    job_id = mod.relocate_execute(["HA"], dst)[0]["job_id"]

    fresh = RelocateModule()
    fresh.start(mgr.ctx, dry_run=False)
    assert fresh._ctx is mgr.ctx, "ctx 必须接线(丢失 = 相位机全停)"

    fresh2 = RelocateModule()
    fresh2.start(mgr.ctx, dry_run=True)
    assert fresh2._dry is True, "干跑标志必须透传(丢失 = --dry-run 真写)"
    assert fresh2.get_job(job_id) is not None, "enabled 时必须恢复 job 账"

    rt = fresh2._rt[job_id]
    assert rt["issue"] is False, rt  # 键漂移/值反转 = 恢复后必重发 setLocation
    assert rt["started"] > 0 and rt["sample_ts"] == 0.0, rt
    assert rt["last_size"] == -1 and rt["stall_since"] == 0.0, rt  # 停滞起点真值 = 首采样误判 FAILED


# ---- 生命周期账闸(issue 26-11-07-0527: stop 补写闸 / 热启用补恢复账) ----


def test_stop_skips_persist_when_ledger_not_loaded(tmp_path, monkeypatch):
    """enabled=false 启动(本会话未接管账)-> stop 跳过补写, state 既有在途账原样保留(条目1)

    _persist 是整段重写(内存表覆盖 state 的 relocate.jobs): 前一会话留下的在途 job 在
    state 里, 本会话没 _load_jobs 过(内存 _jobs 为空) —— 无条件补写等于清账, 且优雅退出
    紧随 stop_all 的 ctx.state.save() 落盘, 清账即永久失账(别名链接无人收口、拦截失明)。
    """
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, state="uploading")
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    job_id = mod.relocate_execute(["HA"], dst)[0]["job_id"]
    assert job_id in mgr.state["relocate"]["jobs"]

    # 下一会话 enabled=false 启动: 不恢复账(开关关零副作用, R15), 优雅退出不得清既有账
    mgr.config.relocate = RelocateConfig(enabled=False)
    mod2 = RelocateModule(mgr.ctx)
    mod2.start(mgr.ctx, dry_run=False)
    assert mod2.get_job(job_id) is None, "开关关启动不恢复账(R15)"
    mod2.stop()
    assert job_id in mgr.state["relocate"]["jobs"], "stop 不得清本会话未接管的既有账"


def test_stop_persists_after_ledger_touched_this_session(tmp_path, monkeypatch):
    """本会话接管过账 -> stop 照常补写(不得矫枉过正把合法落盘也禁了)(条目1)

    enabled=true 启动经 _load_jobs 接管账后: 未动内容时补写为同值重写(账不丢); 仅动
    内存不经 _set_job 的变更(register_job 落内存不落盘)靠 stop 补写带进 state。
    """
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, state="uploading")
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    job_id = mod.relocate_execute(["HA"], dst)[0]["job_id"]

    mod2 = RelocateModule(mgr.ctx)  # enabled 会话: start 恢复账 = 接管
    mod2.start(mgr.ctx, dry_run=False)
    assert mod2._jobs_loaded and mod2.get_job(job_id) is not None
    mod2.stop()  # 未动内容: 同值重写, 账不丢
    assert job_id in mgr.state["relocate"]["jobs"]

    mod2.register_job(replace(mod2.get_job(job_id), reason="touched"))  # 只落内存
    mod2.stop()
    assert mgr.state["relocate"]["jobs"][job_id]["reason"] == "touched", "动过账的会话退出必须补写落盘"


def test_apply_hot_enable_restores_ledger_and_interception(tmp_path, monkeypatch):
    """热启用(enabled 假->真)补 _load_jobs: 历史在途 job 灌回 + relocating_hashes 重建(条目2)

    disabled 启动的会话(state 里有崩溃/停用期残留)热启用后不补恢复: on_task_line 只推
    内存账, job 永久休眠; _sync_relocating 不重建, 未收尾拦截对这批成员失明。补灌后与
    start 的启用分支同口径; 持续启用下的段变化不重灌(不重置在途 job 的运行期账 _rt)。
    """
    pin_disk_usage(monkeypatch)
    mgr, client, src, dst, content, files = relocate_env(tmp_path, state="uploading")
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    job_id = mod.relocate_execute(["HA"], dst)[0]["job_id"]

    # 下一会话 disabled 启动: 账不恢复; 拦截登记为空(重启后 store 全新, 这里显式清出同形)
    mgr.config.relocate = RelocateConfig(enabled=False)
    mod2 = RelocateModule(mgr.ctx)
    mod2.start(mgr.ctx, dry_run=False)
    mod2._sync_relocating()
    assert mod2.get_job(job_id) is None and not mgr.store.relocating_hashes

    old = Config()
    new = Config()
    new.relocate = RelocateConfig(enabled=True)
    res = mod2.apply(old, new)
    # 文案不带「在途」(nit, issue 26-11-07-0527): 计数含终态 job, 说「在途」长期部署必然多报
    assert res.action == "reloaded" and "恢复 job 1 条" in res.detail and "在途" not in res.detail, res
    assert mod2.get_job(job_id) is not None and mod2.get_job(job_id).phase == ru.PHASE_MOVING
    assert {"HA", "HB"} <= mgr.store.relocating_hashes, "未收尾拦截登记必须随热启用重建"

    # 持续启用下的段变化不重灌: rt 账不重置(重灌会让在途 job 无谓回到恢复判据)
    mod2._rt[job_id]["sample_ts"] = 123.0
    newer = Config()
    newer.relocate = RelocateConfig(enabled=True, verify="sample")
    res2 = mod2.apply(new, newer)
    assert res2.action == "reloaded" and "恢复 job" not in res2.detail, res2
    assert mod2._rt[job_id]["sample_ts"] == 123.0


def test_cancel_write_intent_faces(tmp_path):
    """撤销写意图: 删链接(rc_65)/搬回实参(rc_67/69)/reason 与回执契约(rc_99/121~126/gone)"""
    dd = str(tmp_path)
    target = tmp_path / "data.mkv"
    target.write_bytes(b"x" * 64)
    link = str(tmp_path / "link.mkv")
    os.link(str(target), link)
    resumed, locs = [], []
    mod = _bare_mod(
        api=types.SimpleNamespace(
            client=None,
            torrents_set_location=lambda **kw: locs.append(dict(kw)),
            torrents_resume=lambda **kw: resumed.append(list(kw["torrent_hashes"])),
        ),
        data_dir=dd,
    )
    job = _job(
        "j1",
        phase=ru.PHASE_ARMED,
        alias_paths=(link, ),
        resume_hashes=("HA", ),
        plan={
            "form": ru.FORM_FILE_LINKS,
            "files": [["data.mkv", 64]]
        }
    )
    mod._jobs["j1"] = job

    first = mod.relocate_cancel("j1")
    assert first["cls"] == "confirm" and first["cost"]["job_id"] == "j1" and first["cost"]["bytes"] == 64, first
    assert os.path.exists(link), "未确认不得动链接"

    out = mod.relocate_cancel("j1", cost_confirmed=True)
    assert out["cls"] == "ok", out
    assert set(out) >= {"cls", "cost", "job_id", "phase"}, set(out)
    assert not os.path.exists(link), "撤销必须删链接(链接不删即搬回 = 残链孤现场)"
    assert locs and locs[0]["torrent_hashes"] == ["HA"] and locs[0]["location"] == job.src, locs
    saved = mod.get_job("j1")
    assert saved.phase == ru.PHASE_CANCELLED and saved.reason == "cancelled", (saved.phase, saved.reason)
    assert resumed == [["HA"]], resumed
    assert relocate_journal.read_journal(dd, "j1")["phase"] == ru.PHASE_CANCELLED

    gone = mod.relocate_cancel("nope")
    assert gone["cls"] == "blocked" and gone["reasons"][0]["gate"] == "gone", gone
    assert "未找到迁移任务" in gone["reasons"][0]["text"], gone
