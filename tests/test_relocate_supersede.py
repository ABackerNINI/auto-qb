"""test_relocate_supersede 测试计划: 单活任务模型「续迁即收官 + 移交 + 统一改指」
(计划 26-11-15-2340 §03.2 D4/D5 / §04-S1a, 取代 26-11-05-0808 S5 的原地改道语义)

收尾窗(armed/rewritten)对同组再迁移的全链 mock 面(真机 N10-N12 口径留批次收尾):
- 续迁即收官(D4): 三入口(web/rule/预检后的执行体)对同组发起新一轮时, 旧任务**立即**
  落只读历史态(superseded), 不再原地改道(不翻 dst/spec/journal retarget);
- 移交 + 统一改指(I2): 旧任务的别名工作整体移交新任务, 新任务把全部旧路径(前任别名)
  统一改指自己的终位置 —— 别名始终直指物理数据, 不存在 A→B→C 链;
- 只读历史表示: superseded ∈ 终态(不可推进/不可撤销/无删除入口), 重启经 _load_jobs
  恢复仍保持历史态, 记录随新任务存在而保留;
- 继承面保护: 移交后旧根的作用域解析/删种拦截登记/删链门依赖/添加预检由活任务的
  继承条目承接; arm spec 带 extra_srcs, 回收 daemon 按多旧根改写到新终位置;
- 失败分段(D20 沿用): 搬前预检(alias_busy/形态x卷位)整体拒绝零副作用, 搬后改指
  失败重试至收敛不回滚不判失败。

## 测试计划(每个测试函数一条)
### 续迁即收官(D4 / I1)
- test_supersede_start_closes_predecessor_to_history: armed A→B 后发起 B→C 的**瞬间**
  旧 job 即落 superseded 只读历史 —— phase 立即变更(无需等搬移)、dst/别名/alias_paths
  账面冻结不动(不再原地改道)、组内至多一个活任务(I1)、撤销被终态守卫拒绝
- test_supersede_history_survives_reload: 收官后的历史 job 清空内存账后经 _load_jobs
  恢复仍保持 superseded 历史态(不入 active、不进相位机)
- test_supersede_start_journals_predecessor_retired: 收官同时写 journal 相位 superseded
  (daemon 即时退休: 前任 spec 不再驱动改写); spec.dst 原样保留(零改道痕迹)
### 移交 + 统一改指(D4 / I2)
- test_supersede_unified_repoint_chain_end_to_end: armed A→B 后发起 B→C 全链 —— 新 job
  接管移交条目(plan.inherited), 搬移完成后把前任 A 侧别名统一改指 C; B 侧新建别名
  直指 C; 前任账面零改道(dst 仍 B / spec.dst 仍 B / journal 无 retarget 字段); 新 spec
  members 覆盖前任成员; relocating 登记连续; I2: 所有别名直指 C 无 A→B→C 链
- test_supersede_rewritten_predecessor_handed_over: rewritten 前任同样在发起瞬间收官,
  移交别名统一改指(两条重启序的必要件由单一活任务的 spec 承载)
- test_supersede_handover_failure_retries_until_converged: 改指失败注入 = 不回滚不判失败
  —— 前任保持 superseded 历史、J2 停 moved 重试; 解除注入后幂等续跑收敛(retarget_alias
  的 skipped 幂等面), journal 无改道残留
### 整链一个清理单元(D5)与继承面
- test_supersede_all_old_paths_direct_and_chain_finalizes: 成员账面到 C 后 J2 核验过 +
  继承面(旧根 A)依赖清零 → 终态删除**双方**别名(A 侧移交别名 + B 侧自有别名), 全链
  消亡于新任务终态; 前任历史记录保留(superseded 账面原样)
- test_supersede_chain_depth3_flattens_grandparent_entries: 链深 3(J1→J2→J3 两次续迁
  收官, minor-R3-1)—— J3.plan.inherited 展平归集 J1+J2 条目(各 job_id 恰一条, 不丢
  祖父辈; 祖父辈 dst 刷新为现任终位置 C, minor-R4-1, 非冻结的 B), 改指收敛后三代别名
  (A/B/C 侧)全部直指 D, 成员账面到 D 后终态整链删净(整链一个清理单元, 计划 §03.2)
- test_supersede_inherited_chain_gate_blocks_finalize: 组外种子落在旧根 A(等值面)时
  J2 删链门计依赖(继承面承接前任的门), 依赖不清永不删别名
- test_supersede_inherited_surfaces_registered: 继承条目接入三个消费面 ——
  resolve_physical 把旧根账面解析到新终位置(组键不裂)、_sync_relocating 登记继承别名根
  (删种拦截 D16 连续)、blocks_relocation 拦截落进继承目录别名作用域的别组
- test_supersede_inherited_add_confirm_phase_split: 移交面添加预检按改指收敛与否分流
  (评审 should2/minor-4)—— 收敛判据 = plan.handover_done 持久标记(非相位近似):
  标记缺席 actual 按前任终位置建模且文案注明未收敛, 标记在(含「收敛后仍 moved」窗)
  actual 按接管 job 终位置建模, 收敛前不按新终位置谎报落点
- test_supersede_predecessor_members_fuse_covered: 前任成员(不在新 job 分桶的混合态)
  在发起瞬间并入 plan.extra_members(D19 语义移交至收官点), arm spec members 覆盖
- test_supersede_spec_carries_extra_srcs: 移交后 J2 的 arm spec 带 extra_srcs=[旧根 A]
  (daemon 多旧根改写的规格面); 无移交时零新键(旧 spec 形状不变)
### 失败分段(D20 沿用)
- test_supersede_alias_busy_blocks_before_move: 搬前预检(alias_busy)失败 = 整体拒绝零
  副作用 —— 无新 job、无 setLocation、旧 job 保持 armed 现场原样(未收官)
- test_supersede_alias_form_volume_gate: 形态 x 卷位预检 —— hardlink 前任别名 + 跨卷
  + symlink 不可用 = 整体拒绝; symlink 回落可行 = 放行不出此闸
### 撤销面(D6 停手语义: 撤销不搬回, 计划 26-11-15-2340 §03.3; D5 历史无撤销入口)
- test_supersede_cancel_keeps_inherited_aliases: 继承别名不在撤销清理面 —— 撤销活任务
  只删自己已建的链接, 继承别名(前任的、已统一改指 C)不删不撤, 旧根路径仍解析直指 C;
  零 setLocation(数据与下载器路径不动)、成员恢复、前任历史零触碰(旧 cancel_inherited
  过渡守卫随搬回能力退役)
- test_supersede_cancel_settled_rewrites_no_longer_frozen: rewritten settled 改写账不再
  拦撤销(旧 cancel_rewritten 冻结守卫的核心动因 = 搬回破坏 fastresume, 随搬回退役);
  撤销照常删自有链接清账, 零 setLocation, journal 撕态残账(garbage)容忍
- test_supersede_cancel_mixed_rewrite_account_not_blocked: 混合改写账(rewritten +
  member_gone)不构成撤销障碍(旧「唯一人工出口」随守卫退役自然豁免); 未确认先见
  三段式确认面(D7 guide)
- test_supersede_cancel_chain_live_task_no_moveback: 链式撤销断粮面(issue 26-11-07-0528
  关闭面, D10 real 的替身版): A→B→C 后撤销活任务 —— 旧路径仍解析直指 C、setLocation
  零下发 + 成员 save_path 原样、C 侧数据原样、账面 cancelled、前任历史不改写
### 同键重发与启动对账(评审 major-3/minor-6/major-R2-1)
- test_supersede_same_key_reissue_carries_inheritance: 携带移交条目的 job 失败后同键
  重发, 新账结转 plan.inherited/extra_members(_carry_prev_state, 移交义务不失主);
  重发生命周期改指幂等收敛, 别名仍直指 C
- test_supersede_load_jobs_adopts_journal_terminal: journal 写完终相位而 state 刷盘滞后
  的失窗(minor-6)—— _load_jobs 按 journal 终相位回写(armed 陈旧账 -> superseded),
  落账收敛不悬挂, 不入活集
- test_supersede_load_jobs_skips_stale_terminal_journal: 采纳带生命周期锚定(R2-1)——
  上一世终相位 journal(ts < 本世 created_at)不采纳, 账面保持在途(误终态化无恢复面),
  残留交 _arm 侧既有清理口
### 单元边角
- test_supersede_handover_stray_alias_skipped: 移交别名不在声明源下 = 跳过重定向只计数
  (账不自洽留痕, 不猜不动); _rel_under 三支(等值/根下/根外 None)
- test_supersede_handover_dedupes_carried_entry_by_job_id: 结转条目与活集认领同 id 相撞
  (major-R2-2 其一)—— 当前账面值原位替换, plan.inherited 同 job_id 恒恰一条
- test_supersede_repoint_cursor_isolated_per_entry: 改指进度游标按条目独立
  (major-R2-2 其二)—— 桶键 job_id#seq, 双条目同 id 形态下不共享 pos
- test_supersede_handover_member_merge_idempotent: 收官合并幂等 —— 同一前任重复进账
  不重复(extra_members 去重、inherited 不翻倍)
- test_build_links_skips_twin_links_already_pointing_at_target: 链式孪生(已指向目标的
  硬链接)建链幂等跳过不重建
"""

import os

from dataclasses import replace

import pytest

from auto_qb.core.modules import relocate_units as ru

from auto_qb.infra import alias_fs as afs

from auto_qb.infra import relocate_journal as rj

from helpers import FakeTorrent, pin_disk_usage

from relocate_exec_support import _armed_env, _bare_mod, _job, _run_ticks


def _c_root(tmp_path):
    """链式第三根 C(目标卷真实存在, 与 relocate_env 的 dst 同等待遇)"""
    dst_c = os.path.join(str(tmp_path), "dstC")
    os.makedirs(dst_c, exist_ok=True)
    return dst_c


def _points_at_c(mod, job, root, dst_c):
    """job 的每条别名经 rel 换算后恰指向 C 对应路径"""
    for link in job.alias_paths:
        rel = mod._rel_under(root, link)
        assert rel is not None, link
        assert afs.alias_points_to(link, os.path.join(dst_c, *rel.split("/"))), (link, rel)


def _inherited_aliases(job):
    """job 移交条目里的全部别名(扁平)"""
    out = []
    for e in (job.plan or {}).get("inherited") or []:
        out.extend(e.get("alias_paths") or [])
    return out


def test_supersede_start_closes_predecessor_to_history(tmp_path, monkeypatch):
    """续迁即收官(D4): 发起瞬间旧 job 落 superseded 只读历史, 账面冻结, I1 单活"""
    pin_disk_usage(monkeypatch)
    mgr, client, mod, j1, spawned, src, dst, content = _armed_env(tmp_path, monkeypatch)
    dst_c = _c_root(tmp_path)
    items = mod.relocate_execute(["HA"], dst_c)
    assert items[0]["cls"] == "started", str(items[0].get("reasons")) + " /// " + str(items[0].get("notes"))
    j2 = items[0]["job_id"]
    assert j2 != j1, "再迁移是新的 job(同组同目标幂等 skip 不适用: 目标不同)"
    job1, job2 = mod.get_job(j1), mod.get_job(j2)
    # 收官瞬间生效(未跑任何 tick): 旧 job 已是只读历史
    assert job1.phase == ru.PHASE_SUPERSEDED, job1.phase
    assert job1.is_terminal and job1 not in mod.active_jobs(), "历史不入活集(I1: 组内至多一个活任务)"
    assert len(mod.active_jobs()) == 1 and mod.active_jobs()[0].job_id == j2, "I1: 单活"
    # 账面冻结(不再原地改道): dst/别名/别名账原样 —— 改道机器退役的账面证据
    assert mod._norm(job1.dst) == mod._norm(dst), "旧 dst 不翻转(原地改道已退役)"
    assert job1.alias_paths and all(afs.alias_kind_of(p) is not None for p in job1.alias_paths), "别名账原样在位"
    # 撤销面: 历史无撤销入口(终态守卫)
    out = mod.relocate_cancel(j1, cost_confirmed=False)
    assert out["cls"] == "blocked" and out["reasons"][0]["gate"] == "cancel_terminal", out
    # 移交已登记在新任务账上(重启可重建的持久面)
    inherited = (job2.plan or {}).get("inherited") or []
    assert inherited and inherited[0]["job_id"] == j1, job2.plan
    assert set(inherited[0]["alias_paths"]) == set(job1.alias_paths), "移交条目携带前任全部别名"


def test_supersede_history_survives_reload(tmp_path, monkeypatch):
    """只读历史跨重启: 清空内存账后 _load_jobs 恢复仍保持 superseded 历史态"""
    pin_disk_usage(monkeypatch)
    mgr, client, mod, j1, spawned, src, dst, content = _armed_env(tmp_path, monkeypatch)
    dst_c = _c_root(tmp_path)
    items = mod.relocate_execute(["HA"], dst_c)
    assert items[0]["cls"] == "started", items
    j2 = items[0]["job_id"]
    mod._jobs.clear()
    mod._rt.clear()
    n = mod._load_jobs()
    assert n >= 2, n
    job1 = mod.get_job(j1)
    assert job1.phase == ru.PHASE_SUPERSEDED, "重启后历史态保持(LEGACY 透传之外的显式恢复面)"
    assert job1.is_terminal and job1 not in mod.active_jobs(), "历史不入活集不进相位机"
    assert mod.get_job(j2).phase == ru.PHASE_MOVING, "活任务照常恢复"


def test_supersede_start_journals_predecessor_retired(tmp_path, monkeypatch):
    """收官同时写 journal 相位 superseded(daemon 即时退休, 前任 spec 不再驱动改写);
    前任 spec.dst 原样保留(零改道痕迹, journal 无 retarget 字段)"""
    pin_disk_usage(monkeypatch)
    mgr, client, mod, j1, spawned, src, dst, content = _armed_env(tmp_path, monkeypatch)
    dd = mgr.config.data_dir
    dst_c = _c_root(tmp_path)
    items = mod.relocate_execute(["HA"], dst_c)
    assert items[0]["cls"] == "started", items
    j2 = items[0]["job_id"]
    journal1 = rj.read_journal(dd, j1) or {}
    assert journal1.get("phase") == ru.PHASE_SUPERSEDED, journal1
    assert "superseded" in rj.STOP_PHASES, "superseded 入 daemon 停止词表(即时退休)"
    spec1 = rj.read_spec(dd, j1)
    assert spec1 and mod._norm(spec1["dst"]) == mod._norm(dst), "前任 spec.dst 原样(零改道)"
    assert "retarget" not in journal1, "journal 无 retarget 字段(改道账面机器退役)"


def test_supersede_unified_repoint_chain_end_to_end(tmp_path, monkeypatch):
    """移交 + 统一改指(D4/I2): armed A→B 后发起 B→C 全链 —— 前任别名统一改指 C,
    新建别名直指 C, 前任账面零改道, I2 无 A→B→C 链"""
    pin_disk_usage(monkeypatch)
    mgr, client, mod, j1, spawned, src, dst, content = _armed_env(tmp_path, monkeypatch)
    dd = mgr.config.data_dir
    files = client.files_map["HA"]
    dst_c = _c_root(tmp_path)
    items = mod.relocate_execute(["HA"], dst_c)
    assert items[0]["cls"] == "started", str(items[0].get("reasons")) + " /// " + str(items[0].get("notes"))
    j2 = items[0]["job_id"]
    _simulate_moved_at = os.path.join(dst, "Show")
    from relocate_exec_support import _simulate_moved

    _simulate_moved(mgr, dst_c, files, _simulate_moved_at)
    _run_ticks(mod, 8)
    job1, job2 = mod.get_job(j1), mod.get_job(j2)
    assert job2.phase == ru.PHASE_ARMED, job2.phase
    assert job1.phase == ru.PHASE_SUPERSEDED, "前任保持只读历史(全程不复活不改道)"
    # 前任账面零改道(改道机器退役的核心断言)
    assert mod._norm(job1.dst) == mod._norm(dst), "dst 不翻转"
    spec1 = rj.read_spec(dd, j1)
    assert spec1 and mod._norm(spec1["dst"]) == mod._norm(dst), "spec.dst 不改道"
    journal1 = rj.read_journal(dd, j1) or {}
    assert "retarget" not in journal1, "journal 无 retarget"
    # 统一改指(I2): A 侧移交别名与 B 侧新建别名全部直指 C —— 无 A→B→C 链
    _points_at_c(mod, job1, src, dst_c)
    _points_at_c(mod, job2, dst, dst_c)
    assert job2.plan.get("handover_done") is True, "改指收敛持久标记落盘(评审 minor-4)"
    with open(_inherited_aliases(job2)[0], "rb") as f:  # 穿透校验: 经旧根链接读到 C 的数据
        assert f.read() == b"x" * 64
    # 新 spec 覆盖前任成员(daemon 按 {B→C} 与 {A→C}(extra_srcs) 改写到 C)
    spec2 = rj.read_spec(dd, j2)
    assert mod._norm(spec2["src"]) == mod._norm(dst) and mod._norm(spec2["dst"]) == mod._norm(dst_c), spec2
    assert {"HA", "HB"} <= {m["hash_v1"] for m in spec2["members"]}, spec2
    # relocating 登记连续: 组成员都在账(_sync_relocating 整表重算)
    assert {"HA", "HB"} <= mgr.store.relocating_hashes
    assert spawned, "移交后 pending 仍在, 回收 daemon 对账在位(下一窗口改写到 C)"


def test_supersede_rewritten_predecessor_handed_over(tmp_path, monkeypatch):
    """rewritten 前任同样在发起瞬间收官并移交(改写已落 B 的成员由单一活任务的
    spec {B→C}+extra_srcs 承载, 改指同样收敛)"""
    pin_disk_usage(monkeypatch)
    mgr, client, mod, j1, spawned, src, dst, content = _armed_env(tmp_path, monkeypatch)
    dd = mgr.config.data_dir
    files = client.files_map["HA"]
    # 驱动 J1 到 rewritten: daemon 改写账全员 settled + 相位翻转(S3 协议), 对账镜像合并
    assert rj.record_rewrites(
        dd, j1, {h: {
            "status": "rewritten",
            "path": "x"
        }
                 for h in ("HA", "HB")}, phase=rj.PHASE_REWRITTEN
    )
    _run_ticks(mod, 2)
    assert mod.get_job(j1).phase == ru.PHASE_REWRITTEN
    dst_c = _c_root(tmp_path)
    items = mod.relocate_execute(["HA"], dst_c)
    assert items[0]["cls"] == "started", items
    j2 = items[0]["job_id"]
    assert mod.get_job(j1).phase == ru.PHASE_SUPERSEDED, "rewritten 前任发起瞬间即收官"
    from relocate_exec_support import _simulate_moved

    _simulate_moved(mgr, dst_c, files, os.path.join(dst, "Show"))
    _run_ticks(mod, 8)
    job1, job2 = mod.get_job(j1), mod.get_job(j2)
    assert job2.phase == ru.PHASE_ARMED and job1.phase == ru.PHASE_SUPERSEDED
    # 双别名独立: A 侧(移交)与 B 侧(J2 自建)不同链、各直指 C(I2)
    a_links, b_links = _inherited_aliases(job2), list(job2.alias_paths)
    assert a_links and b_links and not (set(a_links) & set(b_links))
    for link in a_links:
        rel = mod._rel_under(src, link)
        assert rel is not None and afs.alias_points_to(link, os.path.join(dst_c, *rel.split("/"))), link
    _points_at_c(mod, job2, dst, dst_c)
    # 单一活任务的改写规格覆盖两个旧根(own src B + extra_srcs A)
    spec2 = rj.read_spec(dd, j2)
    roots = {mod._norm(spec2["src"])} | {mod._norm(s) for s in spec2.get("extra_srcs") or []}
    assert mod._norm(src) in roots and mod._norm(dst) in roots, spec2


def test_supersede_handover_failure_retries_until_converged(tmp_path, monkeypatch):
    """改指失败注入(D20 沿用): 不回滚不判失败 —— 前任保持 superseded 历史, J2 停 moved
    重试; 解除注入后幂等续跑收敛, journal 无改道残留"""
    pin_disk_usage(monkeypatch)
    mgr, client, mod, j1, spawned, src, dst, content = _armed_env(tmp_path, monkeypatch)
    dd = mgr.config.data_dir
    files = client.files_map["HA"]
    dst_c = _c_root(tmp_path)
    real = afs.retarget_alias
    calls = {"n": 0}

    def flaky(link, target, kind=None):
        calls["n"] += 1
        if calls["n"] <= 1:
            raise RuntimeError("占用注入(WinError 32)")
        return real(link, target, kind)

    monkeypatch.setattr(afs, "retarget_alias", flaky)
    items = mod.relocate_execute(["HA"], dst_c)
    j2 = items[0]["job_id"]
    assert mod.get_job(j1).phase == ru.PHASE_SUPERSEDED, "收官在发起瞬间, 失败不回滚收官"
    from relocate_exec_support import _simulate_moved

    _simulate_moved(mgr, dst_c, files, os.path.join(dst, "Show"))
    mod.on_task_line()  # moving -> moved
    mod.on_task_line()  # verify -> handover: 改指首链即失败
    job1, job2 = mod.get_job(j1), mod.get_job(j2)
    assert job1.phase == ru.PHASE_SUPERSEDED, "历史态不受改指失败影响"
    spec1 = rj.read_spec(dd, j1)
    assert mod._norm(spec1["dst"]) == mod._norm(dst), "前任 spec 零改道(不因失败补改道)"
    first_link = _inherited_aliases(job2)[0]
    assert not afs.alias_points_to(first_link, os.path.join(dst_c, "Show", os.path.basename(first_link))), \
        "失败链未改指(现场保留待重试)"
    assert job2.phase == ru.PHASE_MOVED, "J2 停在 handover stage(反馈面: 重试中)"
    # 解除注入: 下一拍幂等续跑(进度账在 rt), 收敛后照常建链武装
    _run_ticks(mod, 7)
    job1, job2 = mod.get_job(j1), mod.get_job(j2)
    assert job2.phase == ru.PHASE_ARMED, job2.phase
    _points_at_c(mod, job1, src, dst_c)
    journal1 = rj.read_journal(dd, j1) or {}
    assert "retarget" not in journal1, "journal 无改道残留"
    assert job1.phase == ru.PHASE_SUPERSEDED, "全程保持历史态"


def test_supersede_all_old_paths_direct_and_chain_finalizes(tmp_path, monkeypatch):
    """整链一个清理单元(D5) + I2 直达: 成员账面到 C 后 J2 核验过 + 继承面依赖清零 ->
    终态删除双方别名(移交的 A 侧 + 自有 B 侧); 前任历史记录保留"""
    pin_disk_usage(monkeypatch)
    mgr, client, mod, j1, spawned, src, dst, content = _armed_env(tmp_path, monkeypatch)
    files = client.files_map["HA"]
    dst_c = _c_root(tmp_path)
    items = mod.relocate_execute(["HA"], dst_c)
    j2 = items[0]["job_id"]
    from relocate_exec_support import _simulate_moved

    _simulate_moved(mgr, dst_c, files, os.path.join(dst, "Show"))
    _run_ticks(mod, 8)
    job1, job2 = mod.get_job(j1), mod.get_job(j2)
    assert job2.phase == ru.PHASE_ARMED, job2.phase
    a_links, b_links = _inherited_aliases(job2), list(job2.alias_paths)
    assert a_links and b_links
    # 成员账面到 C(改写生效 + qB 重启加载后的模拟)
    for h in ("HA", "HB"):
        mgr.store.by_hash[h].save_path = dst_c
    _run_ticks(mod, 3)
    job2 = mod.get_job(j2)
    assert job2.phase == ru.PHASE_DONE and job2.reason == ru.REASON_FINALIZED, (job2.phase, job2.reason)
    assert all(not os.path.lexists(p) for p in b_links), "自有别名已删"
    assert all(not os.path.lexists(p) for p in a_links), "移交别名随新任务终态一并删除(整链一个清理单元)"
    # 前任历史记录保留(D5: 随新任务存在而保留; 物理清理在终态分级清理面)
    job1 = mod.get_job(j1)
    assert job1.phase == ru.PHASE_SUPERSEDED and job1.alias_paths, "历史账面原样保留"


def test_supersede_chain_depth3_flattens_grandparent_entries(tmp_path, monkeypatch):
    """链深 3(minor-R3-1): J1(A→B)→J2(B→C)→J3(C→D) 两次续迁收官 —— J3 收官 J2 时把
    J2 账上已结转的 J1 条目一并**展平归集**(各 job_id 恰一条, 祖父辈不失主); 改指收敛
    后三代别名(A/B/C 侧)全部直指 D(I2), 成员账面到 D 后终态整链删净(整链一个清理单元)"""
    pin_disk_usage(monkeypatch)
    mgr, client, mod, j1, spawned, src, dst, content = _armed_env(tmp_path, monkeypatch)
    files = client.files_map["HA"]
    dst_c = _c_root(tmp_path)
    dst_d = os.path.join(str(tmp_path), "dstD")
    os.makedirs(dst_d, exist_ok=True)
    from relocate_exec_support import _simulate_moved

    # 第二跳: J2(B→C) 收官 J1, 改指收敛后 J2 账上 = J1 条目(A 侧) + 自有 B 侧别名
    items = mod.relocate_execute(["HA"], dst_c)
    j2 = items[0]["job_id"]
    _simulate_moved(mgr, dst_c, files, os.path.join(dst, "Show"))
    _run_ticks(mod, 8)
    assert mod.get_job(j2).phase == ru.PHASE_ARMED, mod.get_job(j2).phase
    assert mod.get_job(j1).phase == ru.PHASE_SUPERSEDED
    j2_inherited = mod.get_job(j2).plan.get("inherited") or []
    assert [e["job_id"] for e in j2_inherited] == [j1], "前置: J2 账上含 J1 条目"
    a_links = _inherited_aliases(mod.get_job(j2))
    # 第三跳: J3(C→D) 收官 J2 —— 展平归集后 J3 账上同时含 J2 与 J1 条目(祖父辈不失主)
    items3 = mod.relocate_execute(["HA"], dst_d)
    assert items3[0]["cls"] == "started", items3
    j3 = items3[0]["job_id"]
    j3_inherited = mod.get_job(j3).plan.get("inherited") or []
    ids = [e["job_id"] for e in j3_inherited]
    assert ids == [j2, j1], f"展平归集: J2 自有条目 + J1 祖父辈条目, 各恰一条(实得 {ids})"
    j2_entry = next(e for e in j3_inherited if e["job_id"] == j2)
    j1_entry = next(e for e in j3_inherited if e["job_id"] == j1)
    assert j2_entry["src"] == dst and j1_entry["src"] == src, "两代作用域各自保留(A 根不被 B 根顶掉)"
    # 落点锚刷新(minor-R4-1): 祖父辈条目 dst = 现任终位置 C(J1 自己冻结的 B 已失真 ——
    # pred 收尾窗即改指收敛, J1 侧别名物理指向 C), 未收敛窗 actual 建模与现场一致
    assert mod._norm(j1_entry["dst"]) == mod._norm(dst_c), "祖父辈 dst 刷新为现任终位置(非冻结的 B)"
    assert mod._norm(j2_entry["dst"]) == mod._norm(dst_c), "父辈条目 dst = 现任终位置"
    assert mod.get_job(j2).phase == ru.PHASE_SUPERSEDED, "J2 照常收官"
    _simulate_moved(mgr, dst_d, files, os.path.join(dst_c, "Show"))
    _run_ticks(mod, 8)
    job3 = mod.get_job(j3)
    assert job3.phase == ru.PHASE_ARMED, job3.phase
    assert job3.plan.get("handover_done") is True, "改指收敛标记落盘"
    # I2: 三代别名(A 侧祖父辈 / B 侧父辈 / C 侧自有)全部直指 J3 终位置 D —— 无链式间接
    for link in _inherited_aliases(job3) + list(job3.alias_paths):
        rel = mod._rel_under(src, link) or mod._rel_under(dst, link) or mod._rel_under(dst_c, link)
        assert rel is not None, link
        assert afs.alias_points_to(link, os.path.join(dst_d, *rel.split("/"))), (link, rel)
    # 整链一个清理单元: 成员账面到 D -> 核验过 + 继承面(A/B 根)依赖清零 -> 终态删净三代别名
    for h in ("HA", "HB"):
        mgr.store.by_hash[h].save_path = dst_d
    _run_ticks(mod, 4)
    job3 = mod.get_job(j3)
    assert job3.phase == ru.PHASE_DONE and job3.reason == ru.REASON_FINALIZED, (job3.phase, job3.reason)
    assert all(not os.path.lexists(p) for p in _inherited_aliases(job3) + list(job3.alias_paths) if p), \
        "三代别名随 J3 终态整链删净"
    assert mod.get_job(j1).phase == ru.PHASE_SUPERSEDED and mod.get_job(j2).phase == ru.PHASE_SUPERSEDED, \
        "前任历史记录保留"


def test_supersede_inherited_chain_gate_blocks_finalize(tmp_path, monkeypatch):
    """继承面删链门: 组外种子落在旧根 A(等值面)时 J2 计依赖(前任的门由活任务承接),
    依赖不清永不删别名; 依赖消失后恢复收尾"""
    pin_disk_usage(monkeypatch)
    mgr, client, mod, j1, spawned, src, dst, content = _armed_env(tmp_path, monkeypatch)
    files = client.files_map["HA"]
    dst_c = _c_root(tmp_path)
    items = mod.relocate_execute(["HA"], dst_c)
    j2 = items[0]["job_id"]
    from relocate_exec_support import _simulate_moved

    _simulate_moved(mgr, dst_c, files, os.path.join(dst, "Show"))
    _run_ticks(mod, 8)
    assert mod.get_job(j2).phase == ru.PHASE_ARMED
    a_links = _inherited_aliases(mod.get_job(j2))
    # HZ: 组外种子, save_path 恰等旧声明根 A(N5 等值形态) —— 继承面的删链门依赖
    hz = FakeTorrent(hash="HZ", name="Elsewhere", save_path=src, progress=1.0, state="pausedUP")
    client.torrents["HZ"] = hz
    mgr.store.by_hash["HZ"] = hz
    for h in ("HA", "HB"):
        mgr.store.by_hash[h].save_path = dst_c
    _run_ticks(mod, 3)
    job2 = mod.get_job(j2)
    assert job2.phase == ru.PHASE_ARMED and job2.reason == ru.REASON_CHAIN_DEPS, (job2.phase, job2.reason)
    assert all(os.path.lexists(p) for p in a_links), "继承依赖未清, 移交别名永不删"
    # 依赖离场 -> 门清 -> 收尾删除双方别名
    del mgr.store.by_hash["HZ"]
    del client.torrents["HZ"]
    _run_ticks(mod, 4)
    job2 = mod.get_job(j2)
    assert job2.phase == ru.PHASE_DONE and job2.reason == ru.REASON_FINALIZED
    assert all(not os.path.lexists(p) for p in a_links)


def test_supersede_inherited_surfaces_registered(tmp_path, monkeypatch):
    """继承条目接入三个消费面: resolve_physical 把旧根账面解析到新终位置(组键不裂);
    _sync_relocating 登记继承别名根(删种拦截 D16 连续); blocks_relocation 拦别组落进
    继承目录别名作用域"""
    pin_disk_usage(monkeypatch)
    mgr, client, mod, j1, spawned, src, dst, content = _armed_env(tmp_path, monkeypatch)
    dst_c = _c_root(tmp_path)
    items = mod.relocate_execute(["HA"], dst_c)
    j2 = items[0]["job_id"]
    job2 = mod.get_job(j2)
    # 收官后前任即终态: 旧根解析改由 J2 的继承条目承接(组键不裂)
    assert mod.get_job(j1).is_terminal
    hb_root = ru.content_root_of(mgr.store.by_hash["HB"].save_path, ["Show/e00.mkv", "Show/e01.mkv"])
    assert mod._norm(mod.resolve_physical(mgr.store.by_hash["HB"].save_path, hb_root)) == mod._norm(dst_c), \
        "旧根账面经继承条目解析到新终位置"
    # 删种拦截登记: 继承别名根(A)在 roots 表(旧根路径的删除仍被 D16 拦); J2 自有根
    # 在建链后(moved/armed)同样入表 —— 收官不造成拦截空窗
    roots = mgr.store.relocating_alias_roots
    assert mod._norm(src) in {mod._norm(k) for k in roots}, roots
    from relocate_exec_support import _simulate_moved

    _simulate_moved(mgr, dst_c, client.files_map["HA"], os.path.join(dst, "Show"))
    _run_ticks(mod, 8)
    roots = mgr.store.relocating_alias_roots
    assert mod._norm(dst) in {mod._norm(k) for k in roots}, roots
    assert mod._norm(src) in {mod._norm(k) for k in roots}, roots
    # blocks_relocation: 别组落进继承作用域被拦(目录别名形态); 文件级继承不拦别组
    dir_job = replace(
        job2,
        alias_kind="dir",
        plan={
            **(job2.plan or {}), "form":
                ru.FORM_DIR_ALIAS,
            "inherited":
                [
                    {
                        "job_id": j1,
                        "src": src,
                        "scope": os.path.join(src, "Show"),
                        "alias_kind": "dir",
                        "alias_paths": ["R:/x/alias"],
                        "link_kind": "",
                    }
                ]
        },
    )
    assert dir_job.blocks_relocation(("HZZ", ), os.path.join(src, "Show", "Sub")), "继承目录别名作用域拦截别组"
    assert not job2.blocks_relocation(("HZZ", ), os.path.join(src, "Show", "Sub")), "文件级继承不拦别组(无重定向面)"


def test_supersede_inherited_add_confirm_phase_split(tmp_path):
    """移交面添加预检按改指收敛与否分流(评审 should2/minor-4): 收敛判据 = plan.
    handover_done 持久标记(非相位近似 —— 改指在 moved 内完成, 「收敛后仍 moved」窗
    不得按前任终位置失真): 标记缺席 actual 按前任终位置(entry.dst)建模且文案注明
    未收敛; 标记在 actual 按接管 job 终位置建模 —— 收敛前不按新终位置谎报真实落点"""
    entry = {
        "job_id": "j1",
        "src": "R:/src",
        "dst": "R:/dstB",
        "scope": "R:/src/Show",
        "alias_kind": "dir",
        "alias_paths": [],
        "link_kind": "",
    }

    def _confirm(phase, plan_extra=None):
        plan = {"inherited": [entry], **(plan_extra or {})}
        job = _job("j2", phase=phase, src="R:/dstB", dst="R:/dstC", plan=plan)
        facts = ru.AddFacts(save_path="R:/src", name="New", jobs=(job, ))
        return ru.evaluate_add(facts)

    # 未收敛(moving, 无标记): actual = 前任终位置侧镜像根(B 侧), 不按 C 谎报; 文案注明未收敛
    out = _confirm(ru.PHASE_MOVING)
    assert out["cls"] == ru.CLS_CONFIRM and out["reasons"][0]["gate"] == "finalize_window", out
    assert out["actual_path"] == "R:/dstB/Show", out
    assert "尚未收敛" in out["reasons"][0]["text"] and "统一指向 R:/dstC" in out["reasons"][0]["text"], out
    assert "R:/dstC/Show" not in out["reasons"][0]["text"], "收敛前不得按新终位置展示落点"
    # minor-4 钉扎: 收敛后仍 moved(handover_done 标记在) —— 不得再用相位近似回落 B 侧
    out_moved = _confirm(ru.PHASE_MOVED, {"handover_done": True})
    assert out_moved["cls"] == ru.CLS_CONFIRM, out_moved
    assert out_moved["actual_path"] == "R:/dstC/Show", out_moved
    assert "统一改指" in out_moved["reasons"][0]["text"], out_moved
    # armed(真实链收敛后标记在): actual = 接管 job 终位置侧(C)
    out2 = _confirm(ru.PHASE_ARMED, {"handover_done": True})
    assert out2["cls"] == ru.CLS_CONFIRM, out2
    assert out2["actual_path"] == "R:/dstC/Show", out2
    assert "统一改指" in out2["reasons"][0]["text"], out2


def test_supersede_predecessor_members_fuse_covered(tmp_path, monkeypatch):
    """前任成员(不在新 job 分桶的混合态)在发起瞬间并入 plan.extra_members(D19 语义
    移交至收官点), arm spec members 覆盖, 不动新 job 的核验集合"""
    pin_disk_usage(monkeypatch)
    mgr, client, mod, j1, spawned, src, dst, content = _armed_env(tmp_path, monkeypatch)
    files = client.files_map["HA"]
    # HC: 前任成员, 账面落在旧根 B, 但不在本次再迁移的分桶(模拟分桶遗漏的混合态)
    hc = FakeTorrent(hash="HC", name="Show", save_path=dst, progress=1.0, state="pausedUP")
    client.torrents["HC"] = hc
    mgr.store.by_hash["HC"] = hc
    client.files_map["HC"] = list(files)
    mod._jobs[j1] = replace(mod.get_job(j1), hashes=("HA", "HB", "HC"))
    dst_c = _c_root(tmp_path)
    items = mod.relocate_execute(["HA"], dst_c)
    assert items[0]["cls"] == "started", items
    j2 = items[0]["job_id"]
    assert "HC" not in mod.get_job(j2).hashes, "分桶遗漏形态: HC 不在新 job 成员"
    # 收官瞬间即完成移交合并(D19 补条目不再等搬移后的扫描面)
    assert mod.get_job(j2).plan.get("extra_members") == ["HC"], mod.get_job(j2).plan
    from relocate_exec_support import _simulate_moved

    _simulate_moved(mgr, dst_c, files, os.path.join(dst, "Show"))
    _run_ticks(mod, 8)
    job2 = mod.get_job(j2)
    assert job2.phase == ru.PHASE_ARMED, job2.phase
    spec2 = rj.read_spec(mgr.config.data_dir, j2)
    assert "HC" in {m["hash_v1"] for m in spec2["members"]}, "arm spec members 覆盖补条目(daemon 改写)"
    assert "HC" not in job2.hashes, "补条目成员只进改写清单, 不动核验集合"


def test_supersede_spec_carries_extra_srcs(tmp_path, monkeypatch):
    """移交后 J2 的 arm spec 带 extra_srcs=[旧根](daemon 多旧根改写的规格面);
    无移交的常规迁移 spec 不出新键(形状不变)"""
    pin_disk_usage(monkeypatch)
    mgr, client, mod, j1, spawned, src, dst, content = _armed_env(tmp_path, monkeypatch)
    dd = mgr.config.data_dir
    # 常规首迁(无前任): spec 无 extra_srcs 键
    spec1 = rj.read_spec(dd, j1)
    assert "extra_srcs" not in spec1, spec1
    dst_c = _c_root(tmp_path)
    items = mod.relocate_execute(["HA"], dst_c)
    j2 = items[0]["job_id"]
    from relocate_exec_support import _simulate_moved

    _simulate_moved(mgr, dst_c, client.files_map["HA"], os.path.join(dst, "Show"))
    _run_ticks(mod, 8)
    assert mod.get_job(j2).phase == ru.PHASE_ARMED
    spec2 = rj.read_spec(dd, j2)
    assert [mod._norm(s) for s in spec2.get("extra_srcs") or ()] == [mod._norm(src)], spec2


def test_supersede_alias_busy_blocks_before_move(tmp_path, monkeypatch):
    """搬前预检(alias_busy)失败 = 整体拒绝零副作用: 无新 job / 无 setLocation / 旧现场
    指纹原样(未收官 —— 收官只发生在 committed 点之后)"""
    pin_disk_usage(monkeypatch)
    mgr, client, mod, j1, spawned, src, dst, content = _armed_env(tmp_path, monkeypatch)
    dst_c = _c_root(tmp_path)
    monkeypatch.setattr(afs, "probe_alias_rebuild_busy", lambda link: "链接本体被其它进程占用(注入)")
    client.calls.clear()
    items = mod.relocate_execute(["HA"], dst_c)
    item = items[0]
    assert item["cls"] == "blocked", item
    assert item["reasons"][0]["gate"] == ru.GATE_ALIAS_BUSY, item
    assert "占用" in item["reasons"][0]["text"]
    assert len(mod.jobs_view()) == 1, "未建新 job(整体拒绝)"
    assert client.calls == [], "零副作用: 未暂停成员、未下发 setLocation"
    job1 = mod.get_job(j1)
    assert job1.phase == ru.PHASE_ARMED and mod._norm(job1.dst) == mod._norm(dst), "旧 job 现场指纹原样(未收官)"
    assert all(afs.alias_kind_of(p) is not None for p in job1.alias_paths), "别名在位未动"


def test_supersede_alias_form_volume_gate(tmp_path, monkeypatch):
    """形态 x 卷位预检: hardlink 形态前任别名 + 跨卷目标 + symlink 不可用 = 整体拒绝
    (指纹级回滚 = 此刻零副作用); symlink 回落可行时放行(不再出此闸)"""
    pin_disk_usage(monkeypatch)
    mgr, client, mod, j1, spawned, src, dst, content = _armed_env(tmp_path, monkeypatch)
    dst_c = _c_root(tmp_path)
    hb, ha = mgr.store.by_hash["HB"], mgr.store.by_hash["HA"]
    recs = [hb, ha]
    # 前任别名按 hardlink 形态注入(闸门只对 hardlink 形态设防; 真实卷位由 facts 注入控制);
    # 名册扩到 4 条触发文案「等共 N 条」截断支(假链接路径不触盘: busy 探测对缺失路径放行)。
    # 另挂一条 junction 形态前任: 非 hardlink 形态不设此闸(天然跨卷可建, continue 支)
    monkeypatch.setattr(
        afs, "alias_kind_of", lambda p: afs.KIND_HARDLINK if "R:/x/" in str(p).replace("\\", "/") else afs.KIND_JUNCTION
    )
    mod._jobs[j1] = replace(mod.get_job(j1), alias_paths=("R:/x/1", "R:/x/2", "R:/x/3", "R:/x/4"))
    mod._jobs["j0"] = _job(
        "j0", phase=ru.PHASE_ARMED, src="R:/src0", dst=dst, hashes=("HA", ), alias_paths=("Q:/elsewhere/alias", )
    )
    facts = replace(mod._group_facts(recs, dst_c, client), same_volume=False, file_link_kind=None)
    client.calls.clear()
    item = mod._start_job(recs, dst_c, facts, {"cls": "ok", "notes": [], "reasons": []}, client)
    assert item["cls"] == "blocked", item
    assert item["reasons"][0]["gate"] == ru.GATE_ALIAS_BUSY, item
    assert "卷位" in item["reasons"][0]["text"]
    assert len(mod.jobs_view()) == 2, "未建新 job(j1+j0 在账, 整体拒绝账面/文件指纹原样)"
    assert client.calls == [], "零副作用: 未暂停成员、未下发 setLocation"
    # 放行支: symlink 回落可行(file_link_kind=symlink) -> 不再出形态 x 卷位闸
    # (后续按真实 facts 面走 started/其它闸, 均与本报文无关)
    facts_ok = replace(facts, file_link_kind=afs.KIND_SYMLINK)
    item2 = mod._start_job(recs, dst_c, facts_ok, {"cls": "ok", "notes": [], "reasons": []}, client)
    assert not any(r.get("gate") == ru.GATE_ALIAS_BUSY for r in item2.get("reasons", [])), item2
    assert item2["cls"] == "started", item2


def test_supersede_cancel_keeps_inherited_aliases(tmp_path, monkeypatch):
    """撤销 x 继承面(D6 新语义, 计划 26-11-15-2340 §03.3): 继承别名不在撤销清理面 ——
    撤销活任务只删自己已建的链接; 继承别名是前任的、handover 已统一改指本任务终位置 C,
    数据留在新位置后别名与服务连续性成立, 不删不撤; 旧根路径仍解析(别名直指 C),
    前任历史零触碰; 全程零 setLocation(数据与下载器路径一律不动)。
    旧语义(cancel_inherited 过渡守卫 + 搬回)下本用例红: 继承别名在盘即拦截撤销。"""
    pin_disk_usage(monkeypatch)
    mgr, client, mod, j1, spawned, src, dst, content = _armed_env(tmp_path, monkeypatch)
    files = client.files_map["HA"]
    dst_c = _c_root(tmp_path)
    j2 = mod.relocate_execute(["HA"], dst_c)[0]["job_id"]
    from relocate_exec_support import _simulate_moved

    _simulate_moved(mgr, dst_c, files, os.path.join(dst, "Show"))
    _run_ticks(mod, 8)
    job2 = mod.get_job(j2)
    assert job2.phase == ru.PHASE_ARMED, job2.phase
    a_links = _inherited_aliases(job2)
    own_links = list(job2.alias_paths)
    assert a_links and own_links, "继承条目与自有链接都在账(撤销清理面的两个不同集合)"
    # I2: 继承别名已直指 C(统一改指收敛), 数据经旧根别名可读
    for link in a_links:
        rel = mod._rel_under(src, link)
        assert rel is not None and afs.alias_points_to(link, os.path.join(dst_c, *rel.split("/"))), link

    client.calls.clear()
    out = mod.relocate_cancel(j2, cost_confirmed=True)
    assert out["cls"] == "ok" and mod.get_job(j2).phase == ru.PHASE_CANCELLED, out
    assert not any(c[0] == "set_location" for c in client.calls), f"撤销零 setLocation(D6): {client.calls}"
    assert any(c[0] == "resume" for c in client.calls), "成员恢复运行态(缺件由下载器自行补下)"
    # 继承别名不删不撤: 仍在盘且仍直指 C(旧根路径解析成立)
    for link in a_links:
        assert afs.alias_kind_of(link) is not None, link
        rel = mod._rel_under(src, link)
        assert afs.alias_points_to(link, os.path.join(dst_c, *rel.split("/"))), link
    with open(a_links[0], "rb") as f:  # 穿透校验: 经旧根链接仍读到 C 的数据
        assert f.read() == b"x" * 64
    # 自己的链接已删净(清理面 = 自己已建的链接)
    assert all(not os.path.lexists(p) for p in own_links), own_links
    # 账面: CANCELLED 清自有别名账; 继承条目保留(历史事实, 不改写)
    saved = mod.get_job(j2)
    assert saved.alias_paths == () and (saved.plan or {}).get("inherited"), (saved.alias_paths, saved.plan)
    # 前任历史零触碰
    job1 = mod.get_job(j1)
    assert job1.phase == ru.PHASE_SUPERSEDED and mod._norm(job1.dst) == mod._norm(dst), job1


def test_supersede_cancel_settled_rewrites_no_longer_frozen(tmp_path, monkeypatch):
    """撤销 x 改写账(cancel_rewritten 守卫退役): 撤销不搬回后「改写已落账不能撤销」的
    核心动因(删别名 + 搬回 src 会留下指向 dst 的 fastresume 而数据已回源, 冻结态无人兜底)
    消失 —— rewritten settled 账不再拦撤销; 撤销照常停手清账删自有链接, 零 setLocation,
    journal 撕态残账(garbage)原样容忍"""
    pin_disk_usage(monkeypatch)
    mgr, client, mod, j1, spawned, src, dst, content = _armed_env(tmp_path, monkeypatch)
    dd = mgr.config.data_dir
    files = client.files_map["HA"]
    dst_c = _c_root(tmp_path)
    j2 = mod.relocate_execute(["HA"], dst_c)[0]["job_id"]
    from relocate_exec_support import _simulate_moved

    _simulate_moved(mgr, dst_c, files, os.path.join(dst, "Show"))
    _run_ticks(mod, 8)
    assert mod.get_job(j2).phase == ru.PHASE_ARMED, mod.get_job(j2).phase
    own_links = list(mod.get_job(j2).alias_paths)
    assert rj.record_rewrites(dd, j2, {h: {"status": "rewritten", "path": "x"} for h in ("HA", "HB")})
    j_body = rj.read_journal(dd, j2) or {}
    rj.write_journal(dd, j2, {**j_body, "rewrites": {**(j_body.get("rewrites") or {}), "HBAD": "garbage"}})
    client.calls.clear()
    out = mod.relocate_cancel(j2, cost_confirmed=True)
    assert out["cls"] == "ok" and mod.get_job(j2).phase == ru.PHASE_CANCELLED, out
    assert not any(c[0] == "set_location" for c in client.calls), f"撤销零 setLocation(D6): {client.calls}"
    assert all(not os.path.lexists(p) for p in own_links), "自有链接删净"
    assert (rj.read_journal(dd, j2) or {}).get("phase") == ru.PHASE_CANCELLED


def test_supersede_cancel_mixed_rewrite_account_not_blocked(tmp_path, monkeypatch):
    """member_gone 边界随守卫退役自然豁免: 混合账(rewritten + member_gone)不再构成撤销
    障碍 —— 旧「member_gone 不冻结 = 卡死悬挂 job 的唯一人工出口」语义不需要专门豁免面
    (守卫整体不在场, 无可误伤); 未确认成本先见三段式确认面(D7)"""
    pin_disk_usage(monkeypatch)
    mgr, client, mod, j1, spawned, src, dst, content = _armed_env(tmp_path, monkeypatch)
    dd = mgr.config.data_dir
    files = client.files_map["HA"]
    dst_c = _c_root(tmp_path)
    j2 = mod.relocate_execute(["HA"], dst_c)[0]["job_id"]
    from relocate_exec_support import _simulate_moved

    _simulate_moved(mgr, dst_c, files, os.path.join(dst, "Show"))
    _run_ticks(mod, 8)
    assert mod.get_job(j2).phase == ru.PHASE_ARMED, mod.get_job(j2).phase
    assert rj.record_rewrites(
        dd, j2, {
            "HA": {
                "status": rj.REWRITE_MEMBER_GONE
            },
            "HB": {
                "status": "rewritten",
                "path": "x"
            }
        }
    )
    first = mod.relocate_cancel(j2, cost_confirmed=False)
    assert first["cls"] == "confirm" and "guide" in first, first
    assert "不会搬回" in first["guide"]["consequence"], first["guide"]
    client.calls.clear()
    out = mod.relocate_cancel(j2, cost_confirmed=True)
    assert out["cls"] == "ok" and mod.get_job(j2).phase == ru.PHASE_CANCELLED, out
    assert not any(c[0] == "set_location" for c in client.calls), f"撤销零 setLocation(D6): {client.calls}"


def test_supersede_cancel_chain_live_task_no_moveback(tmp_path, monkeypatch):
    """链式撤销断粮面(issue 26-11-07-0528 关闭面; D10 real 口径的真机项留批次收尾,
    本用例是替身版): A→B→C 链式迁移后撤销活任务 —— 旧路径(A 侧继承别名)仍解析且直指 C、
    数据与下载器路径未动(setLocation 零下发 + 成员 save_path 原样)、C 侧数据文件原样、
    账面落 cancelled、前任历史不改写。旧语义下本用例红: cancel_inherited 拦截(继承别名
    未消化), 消化后撤销还会下发 setLocation 搬回。"""
    pin_disk_usage(monkeypatch)
    mgr, client, mod, j1, spawned, src, dst, content = _armed_env(tmp_path, monkeypatch)
    dd = mgr.config.data_dir
    files = client.files_map["HA"]
    dst_c = _c_root(tmp_path)
    j2 = mod.relocate_execute(["HA"], dst_c)[0]["job_id"]
    from relocate_exec_support import _simulate_moved

    _simulate_moved(mgr, dst_c, files, os.path.join(dst, "Show"))
    _run_ticks(mod, 8)
    assert mod.get_job(j2).phase == ru.PHASE_ARMED, mod.get_job(j2).phase
    a_links = _inherited_aliases(mod.get_job(j2))
    assert a_links, "继承条目在账(A 侧旧路径的解析面)"
    saves_before = {h: rec.save_path for h, rec in mgr.store.by_hash.items() if h in ("HA", "HB")}
    client.calls.clear()
    out = mod.relocate_cancel(j2, cost_confirmed=True)
    assert out["cls"] == "ok" and mod.get_job(j2).phase == ru.PHASE_CANCELLED, out
    # 旧路径仍解析: 继承别名直指 C, 数据可读
    for link in a_links:
        rel = mod._rel_under(src, link)
        assert rel is not None and afs.alias_points_to(link, os.path.join(dst_c, *rel.split("/"))), link
    with open(a_links[0], "rb") as f:
        assert f.read() == b"x" * 64
    # 数据与下载器路径未动: setLocation 零下发 + 成员 save_path 原样 + C 侧数据原样
    assert not any(c[0] == "set_location" for c in client.calls), client.calls
    saves_after = {h: rec.save_path for h, rec in mgr.store.by_hash.items() if h in ("HA", "HB")}
    assert saves_after == saves_before, (saves_before, saves_after)
    assert os.path.exists(os.path.join(dst_c, "Show", "e00.mkv")), "C 侧数据留新位置"
    # 账面 cancelled + journal 落终态(daemon 退休信号); 前任历史不改写
    assert (rj.read_journal(dd, j2) or {}).get("phase") == ru.PHASE_CANCELLED
    job1 = mod.get_job(j1)
    assert job1.phase == ru.PHASE_SUPERSEDED and mod._norm(job1.dst) == mod._norm(dst)


def test_supersede_same_key_reissue_carries_inheritance(tmp_path, monkeypatch):
    """同键重发失继承(评审 major-3): 携带移交条目的 job 失败后同键重发, 新账结转
    plan.inherited(_carry_prev_state, 移交别名与前任成员改写义务不失主 ——
    _predecessors_of 只扫活集, 收官后的前任只能从同键旧账认领); 重发生命周期改指幂等
    收敛, 别名仍直指 C"""
    pin_disk_usage(monkeypatch)
    mgr, client, mod, j1, spawned, src, dst, content = _armed_env(tmp_path, monkeypatch)
    files = client.files_map["HA"]
    dst_c = _c_root(tmp_path)
    items = mod.relocate_execute(["HA"], dst_c)
    j2 = items[0]["job_id"]
    assert mod.get_job(j2).plan.get("inherited"), "前置: 移交条目在账"
    # 注入搬迁期失败(终态; mover 账面仍在旧根 B, 同键重发才成立) + extra_members 义务
    mod._set_job(replace(mod.get_job(j2), plan={**mod.get_job(j2).plan, "extra_members": ["HC"]}))
    mod._set_job(replace(mod.get_job(j2), phase=ru.PHASE_FAILED, reason="boom"))
    # 同键重发: 同 mover/源/目标 -> 同 job_id; 前任已终态, _predecessors_of 扫不到
    items2 = mod.relocate_execute(["HA"], dst_c)
    assert items2[0]["cls"] == "started", items2
    assert items2[0]["job_id"] == j2, "同键重发(同 mover/源/目标 幂等复用同 id)"
    job2b = mod.get_job(j2)
    assert [e["job_id"] for e in job2b.plan.get("inherited") or ()] == [j1], "继承条目结转(义务不失主)"
    assert job2b.plan.get("extra_members") == ["HC"], "extra_members 义务结转"
    assert "handover_done" not in job2b.plan, "收敛标记不结转(新生命周期重走改指)"
    # 重发生命周期: 搬迁 -> 改指(幂等收敛) -> 武装, 继承别名仍直指 C
    from relocate_exec_support import _simulate_moved

    _simulate_moved(mgr, dst_c, files, os.path.join(dst, "Show"))
    _run_ticks(mod, 8)
    job2c = mod.get_job(j2)
    assert job2c.phase == ru.PHASE_ARMED, job2c.phase
    assert job2c.plan.get("handover_done") is True, "改指收敛标记落盘"
    for link in _inherited_aliases(job2c):
        rel = mod._rel_under(src, link)
        assert rel is not None and afs.alias_points_to(link, os.path.join(dst_c, *rel.split("/"))), link


def test_supersede_load_jobs_adopts_journal_terminal(tmp_path, monkeypatch):
    """journal 写完终相位而 state 刷盘滞后的失窗(评审 minor-6): _load_jobs 按 journal
    终相位回写陈旧前段账(armed -> superseded), 收敛为终态不悬挂, 不入活集; 回写落账"""
    pin_disk_usage(monkeypatch)
    mgr, client, mod, j1, spawned, src, dst, content = _armed_env(tmp_path, monkeypatch)
    dst_c = _c_root(tmp_path)
    items = mod.relocate_execute(["HA"], dst_c)
    assert items[0]["cls"] == "started", items
    dd = mgr.config.data_dir
    assert (rj.read_journal(dd, j1) or {}).get("phase") == ru.PHASE_SUPERSEDED, "前置: journal 已退休"
    # 复现失窗: state 盒相位回拨到 armed(模拟 journal 写后 state 刷前硬崩的陈旧刷盘)
    mod._state_jobs()[j1]["phase"] = ru.PHASE_ARMED
    mod._jobs.clear()
    mod._rt.clear()
    mod._load_jobs()
    job1 = mod.get_job(j1)
    assert job1.phase == ru.PHASE_SUPERSEDED, "按 journal 终相位回写(不再按陈旧 state 复活为活账)"
    assert job1.is_terminal and job1 not in mod.active_jobs(), "终态收敛不入相位机(不悬挂)"
    assert mod._state_jobs()[j1]["phase"] == ru.PHASE_SUPERSEDED, "回写已落账(状态盒)"


# ---------------------------------------------------------------------------
# 单元边角: 移交改指的账面异常支 / 收官合并幂等 / 孪生链接
# ---------------------------------------------------------------------------


def test_supersede_handover_stray_alias_skipped(tmp_path, monkeypatch):
    """移交改指双边角: 别名不在移交声明源下 = 跳过重定向只计数(账不自洽留痕, 不猜不动);
    _rel_under 三支(等值/根下/根外 None)"""
    mod = _bare_mod(data_dir=str(tmp_path / "data"))
    job = _job(
        "j2",
        phase=ru.PHASE_MOVED,
        src="R:/dstB",
        dst="R:/dstC",
        hashes=("HZ", ),
        plan={
            "inherited":
                [
                    {
                        "job_id": "j1",
                        "src": "R:/src",
                        "scope": "R:/src",
                        "alias_kind": "file",
                        "alias_paths": ("R:/elsewhere/l.bin", ),
                        "link_kind": "",
                    }
                ]
        },
    )
    rt = {}
    assert mod._handover_redirect(job, rt) is True
    assert rt["handover"]["j1#0"]["pos"] == 1, "不在声明源下的移交别名: 跳过重定向只计数(账不自洽留痕)"
    assert mod._rel_under("R:/src", "R:/src") == ""
    assert mod._rel_under("R:/src", "R:/src/Sub/e00.mkv") == "Sub/e00.mkv"
    assert mod._rel_under("R:/src", "R:/other/e00.mkv") is None


def test_supersede_handover_dedupes_carried_entry_by_job_id(tmp_path):
    """结转条目与活集认领同 id 相撞(评审 major-R2-2 其一): _handover_predecessors 追加前按
    job_id 查重 —— 已结转的前任条目被当前账面值**原位替换**, 不追加第二条目(不变量:
    plan.inherited 同 job_id 恒恰一条; 双条目会共享改指进度游标, 排前段链接被永久跳过)"""
    mod = _bare_mod(data_dir=str(tmp_path / "data"))
    # 上一世结转的 K 条目(旧账面值, alias_paths 已过期)
    stale = {
        "job_id": "K",
        "src": "R:/src",
        "dst": "R:/dstB",
        "scope": "R:/src",
        "alias_kind": "file",
        "alias_paths": ["R:/old/a.bin"],
        "link_kind": "",
    }
    job = _job("J", phase=ru.PHASE_FAILED, src="R:/dstB", dst="R:/dstC", plan={"inherited": [stale]})
    # K 被重发重新入活集(armed, 当前账面 alias_paths 已变) —— 收官认领与结转同 id 相撞
    pred_live = _job(
        "K", phase=ru.PHASE_ARMED, src="R:/src", dst="R:/dstB", alias_paths=("R:/src/a.bin", "R:/src/b.bin")
    )
    job = mod._handover_predecessors([pred_live], job)
    entries = [e for e in (job.plan or {}).get("inherited") or () if e.get("job_id") == "K"]
    assert len(entries) == 1, "同 id 恒恰一条(不追加第二条目)"
    assert entries[0]["alias_paths"] == ["R:/src/a.bin", "R:/src/b.bin"], "原位替换为当前账面值"
    assert entries[0]["dst"] == "R:/dstB" and entries[0]["src"] == "R:/src", "作用域三件套随现任账面刷新"
    assert mod.get_job("K").phase == ru.PHASE_SUPERSEDED, "现任前任照常收官"


def test_supersede_repoint_cursor_isolated_per_entry(tmp_path):
    """改指进度游标按条目独立(评审 major-R2-2 其二): 游标桶键 = job_id#seq —— 双条目同
    job_id 的相撞形态(双保险面)下各条目各自续切, 不共享 pos; 共享会令第二条目从
    pos=len(第一条目) 处续切, 排前段链接被永久跳过(I2 破坏)"""
    mod = _bare_mod(data_dir=str(tmp_path / "data"))
    e0 = {
        "job_id": "j9",
        "src": "R:/src",
        "scope": "R:/src",
        "alias_kind": "file",
        "alias_paths": ["R:/elsewhere/a.bin"],
        "link_kind": "",
    }
    e1 = {
        "job_id": "j9",
        "src": "R:/src",
        "scope": "R:/src",
        "alias_kind": "file",
        "alias_paths": ["R:/elsewhere/b.bin"],
        "link_kind": "",
    }
    job = _job(
        "J",
        phase=ru.PHASE_MOVED,
        src="R:/dstB",
        dst="R:/dstC",
        hashes=("HZ", ),
        plan={"inherited": [e0, e1]},
    )
    rt = {}
    assert mod._handover_redirect(job, rt) is True
    assert rt["handover"]["j9#0"]["pos"] == 1 and rt["handover"]["j9#1"]["pos"] == 1, \
        "各条目游标独立推进(两条目各一笔跳过计数, 不共享 pos)"


def test_supersede_load_jobs_skips_stale_terminal_journal(tmp_path, monkeypatch):
    """生命周期锚定(评审 major-R2-1): 同键重发后上一世的终相位 journal 仍在盘上
    (_arm 前不清), state 在途(本世 created_at 晚于 journal ts) -> 重启**不采纳**,
    账面保持在途(误终态化会让在途迁移无恢复面); 合法失窗(journal ts >= created_at)
    的采纳面由 test_supersede_load_jobs_adopts_journal_terminal 钉扎"""
    pin_disk_usage(monkeypatch)
    mgr, client, mod, j1, spawned, src, dst, content = _armed_env(tmp_path, monkeypatch)
    dst_c = _c_root(tmp_path)
    items = mod.relocate_execute(["HA"], dst_c)
    assert items[0]["cls"] == "started", items
    dd = mgr.config.data_dir
    assert (rj.read_journal(dd, j1) or {}).get("phase") == ru.PHASE_SUPERSEDED, "前置: 上一世终相位 journal 在盘"
    # 复现同键重发的前段窗: state 相位回拨在途(armed)且 created_at 推到 journal ts 之后
    # (= 新生命周期建账锚晚于旧 journal 落笔 —— 锚定不上, 属上一世残留)
    box = mod._state_jobs()[j1]
    box["phase"] = ru.PHASE_ARMED
    box["created_at"] = float((rj.read_journal(dd, j1) or {}).get("ts") or 0.0) + 100.0
    mod._jobs.clear()
    mod._rt.clear()
    mod._load_jobs()
    job1 = mod.get_job(j1)
    assert job1.phase == ru.PHASE_ARMED, "上一世残留不采纳: 账面保持在途(交 _arm 侧既有清理口)"
    assert job1 in mod.active_jobs(), "在途迁移不丢失(终态无恢复面, 宁保持原状)"


def test_supersede_handover_member_merge_idempotent(tmp_path):
    """收官合并幂等: extra_members 去重不重复; 重复调用不翻倍 inherited"""
    import types as _types

    from helpers import FakeTorrent

    mod = _bare_mod(data_dir=str(tmp_path / "data"))
    mod._ctx.store = _types.SimpleNamespace(
        by_hash={
            "HX": FakeTorrent(hash="HX", save_path="R:/dstB/sub/e00.mkv"),
            "HA": FakeTorrent(hash="HA", save_path="R:/dstC/e00.mkv"),
        },
        relocating_hashes=set(),
    )
    pred = _job("j1", phase=ru.PHASE_ARMED, hashes=("H1", "HX"), src="R:/src", dst="R:/dstB")
    job = _job("j2", hashes=("HZ", ), src="R:/dstB", dst="R:/dstC")
    job = mod._handover_predecessors([pred], job)
    assert mod.get_job("j1").phase == ru.PHASE_SUPERSEDED
    first = job.plan["extra_members"]
    assert first == ["H1", "HX"], first  # 前任成员并入(HZ 本 job 已有, 不进)
    inherited = job.plan["inherited"]
    assert len(inherited) == 1 and inherited[0]["job_id"] == "j1"
    # 幂等重放(同一前任再进账): 集合不变
    job2 = mod._handover_predecessors([mod.get_job("j1")], job)
    assert job2.plan["extra_members"] == first
    assert len(job2.plan["inherited"]) == 1, "inherited 不翻倍"


def test_build_links_skips_twin_links_already_pointing_at_target(tmp_path):
    """链式再迁移孪生: src 位已是指向目标的硬链接(经前任别名搬迁的形态) -> 幂等跳过不重建"""
    import types as _types

    from helpers import FakeTorrent

    mod = _bare_mod(data_dir=str(tmp_path / "data"))
    src = tmp_path / "src"
    dstc = tmp_path / "dstC"
    (dstc / "Show").mkdir(parents=True)
    target = dstc / "Show" / "e00.mkv"
    target.write_bytes(b"x" * 64)
    src_show = src / "Show"
    src_show.mkdir(parents=True)
    link = src_show / "e00.mkv"
    afs.create_file_alias(str(link), str(target), afs.KIND_HARDLINK)  # 孪生(同 inode)
    assert afs.alias_points_to(str(link), str(target))
    job = _job(
        "j2",
        phase=ru.PHASE_MOVED,
        src=str(src),
        dst=str(dstc),
        plan={
            "form": ru.FORM_FILE_LINKS,
            "link_kind": "hardlink",
            "files": [["Show/e00.mkv", 64]]
        },
    )
    mod._ctx.store = _types.SimpleNamespace(by_hash={}, relocating_hashes=set())
    rt = {"links": [], "link_pos": 0}
    assert mod._build_links(job, rt) is True
    assert rt["links"] == [str(link)], "孪生直接入账(不重建不报错)"
    assert mod.get_job("j2").alias_paths == (str(link), )
