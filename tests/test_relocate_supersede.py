"""test_relocate_supersede 测试计划: S5 未收尾再迁移(计划 26-11-05-0808 §3.4, D15/D19/D20)

收尾窗(armed/rewritten)相位对同组再迁移的全链 mock 面(真机 N10-N12 留痕延后 S6):
闸门放行(D15, S4a 已收窄)之后的执行侧 —— supersede 重定向(armed 重心)、链式独立双门
(rewritten 近零新逻辑)、失败分段(D20: 搬前整体拒绝零副作用 / 搬后重试至收敛不回滚)、
D19 旧 mover 通用补条目、搬前别名重建可行性预检(alias_busy)、relocating_hashes 登记
连续性(_sync_relocating 整表重算)与同目标撤销护栏。

## 测试计划(每个测试函数一条)
### armed 态 supersede(N10 mock 面)
- test_supersede_armed_chain_end_to_end: armed A→B 后发起 B→C 全链 —— 新 job 锚物理根 B/
  旧 job 账面改道(dst 翻 C + superseded_from 留痕 + spec {A→B}→{A→C} + journal retarget)/
  A 侧别名重指向 C(成员经新链穿透读)/ B 侧新别名→C / 旧条目零残留 / relocating 登记
  两 job 并集连续 / 回收 daemon 对账在位
- test_supersede_anchor_resolves_physical_and_mover_preference: 经别名做种成员(HB 账面在 A)
  发起再迁移 —— _physical_anchor 解析到前任 dst; _start_job 的 src 取锚点且 mover 优先选
  账面已在锚点根的成员(免经别名搬迁留硬链接孪生)
### rewritten 态链式双门(N11 mock 面)
- test_supersede_rewritten_chain_dual_gates: rewritten 前任同样改道(两条重启序都收敛的必要件)
  -> A 侧与 B 侧双别名独立各指 C / 各删链门各自判依赖(B 根账面只算新门)/ 旧门先删不扰新门
  (成员账面到 C 后 J1 先 done 删 A 侧, J2 因 B 根依赖维持)/ 依赖清零后双别名全清 +
  relocating 登记整表迁出
### 失败分段(D20)
- test_supersede_alias_busy_blocks_before_move: 搬前预检(alias_busy)失败 = 整体拒绝零副作用 ——
  无新 job、无 setLocation、旧 job 现场指纹原样(armed + dst 不变 + 别名在位)
- test_supersede_alias_form_volume_gate: 形态 x 卷位预检(评审 #2)—— hardlink 前任别名 + 跨卷
  目标 + symlink 不可用 = 整体拒绝零副作用; symlink 回落可行 = 放行不出此闸
- test_supersede_post_move_redirect_retries_until_converged: 搬后重定向失败注入 = 不回滚不判
  失败 —— 账面改道已提交(先账后链)、J1 保持 armed、J2 停 moved 重试; 解除注入后幂等续跑
  收敛(J1 别名指 C / J2 武装), journal retarget 在账
### D19 通用补条目
- test_supersede_d19_mixed_state_extra_members: 前任成员账面落在被搬离根且不在新 job 分桶
  (混合态) -> 并入 plan.extra_members + arm spec members 覆盖(daemon 按 {B→C} 改写),
  不动新 job 的核验集合(hashes)
### 撤销护栏(S5 改道态的新暴露面)
- test_supersede_cancel_guard_blocks_codestination: 存在改道到同一目标的在途前任时撤销新 job
  = 拒绝(cancel_chain)且零 qB 写(撤销会把共享数据搬回源, 掏空已改道前任的成员服务)
- test_supersede_cancel_refuses_settled_rewrites: journal 已有 settled 改写记录 = 拒绝撤销
  (评审 #3, 成员 fastresume 已指向 dst, 撤销留 0420 同款冻结态)/ 成本确认前即拒(无 confirm
  面)/ 无 settled 记录(pending/无账)撤销行为不变

覆盖率缺口清偿(26-11-07, test.full 99.31% -> 99.5% 闸):
- test_supersede_stage_tick_failure_keeps_retrying_without_link: 重定向失败落在 supersede stage
  拍(verify 拍已失败过) -> 停 moved 不建链, 注入解除后幂等续跑收敛
- test_retarget_predecessor_journal_refused_and_stray_alias: journal 拒记 retarget(诊断面不承重,
  只 DEBUG)/ 别名不在声明源下跳过重定向只计数
- test_rel_under_equivalence_and_outside: _rel_under 三支(等值/根下/根外 None)
- test_supersede_cover_movers_idempotent_replay: D19 补条目(前任成员+被搬离根命中成员)与幂等重放早退
- test_build_links_skips_twin_links_already_pointing_at_target: 链式孪生(已指向目标的硬链接)
  建链幂等跳过不重建
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


def test_supersede_armed_chain_end_to_end(tmp_path, monkeypatch):
    """armed A→B 后发起 B→C 全链(N10 断言 mock 面): 改道/重指向/零残留/登记连续"""
    pin_disk_usage(monkeypatch)
    mgr, client, mod, j1, spawned, src, dst, content = _armed_env(tmp_path, monkeypatch)
    dd = mgr.config.data_dir
    files = client.files_map["HA"]
    dst_c = _c_root(tmp_path)
    items = mod.relocate_execute(["HA"], dst_c)
    assert items[0]["cls"] == "started", str(items[0].get("reasons")) + " /// " + str(items[0].get("notes"))
    j2 = items[0]["job_id"]
    assert j2 != j1, "再迁移是新的 job(同组同目标幂等 skip 不适用: 目标不同)"
    _simulate_moved_content = os.path.join(dst, "Show")
    _simulate(mgr, dst_c, files, _simulate_moved_content)
    _run_ticks(mod, 8)

    job1, job2 = mod.get_job(j1), mod.get_job(j2)
    assert job2.phase == ru.PHASE_ARMED, job2.phase
    assert job1.phase == ru.PHASE_ARMED, "前任不翻终态: 改写账 {A→C} 仍由它承载(收尾者各管各的别名)"
    # 账面改道: dst 翻 C + superseded_from 留痕; spec {A→B}→{A→C}; journal 记 retarget
    assert mod._norm(job1.dst) == mod._norm(dst_c)
    assert mod._norm((job1.plan or {}).get("superseded_from") or "") == mod._norm(dst)
    spec1 = rj.read_spec(dd, j1)
    assert spec1 and mod._norm(spec1["dst"]) == mod._norm(dst_c) and mod._norm(spec1["src"]) == mod._norm(src), spec1
    journal1 = rj.read_journal(dd, j1) or {}
    assert mod._norm(journal1["retarget"]["from"]) == mod._norm(dst), journal1
    assert mod._norm(journal1["retarget"]["to"]) == mod._norm(dst_c), journal1
    # 别名重指向: A 侧(成员经新链做种)与 B 侧(新 job 自建)各指 C
    _points_at_c(mod, job1, src, dst_c)
    _points_at_c(mod, job2, dst, dst_c)
    with open(job1.alias_paths[0], "rb") as f:  # 穿透校验: 经旧根链接读到 C 的数据
        assert f.read() == b"x" * 64
    # 旧条目零残留: J1 的改写映射已无 B; daemon 下一窗口按 spec 改写到 C
    assert {"HA", "HB"} <= {m["hash_v1"] for m in spec1["members"]}
    spec2 = rj.read_spec(dd, j2)
    assert mod._norm(spec2["src"]) == mod._norm(dst) and mod._norm(spec2["dst"]) == mod._norm(dst_c), spec2
    # relocating_hashes 登记连续: 两 job 并集都在账(_sync_relocating 整表重算, S5-6 接线确认)
    assert {"HA", "HB"} <= mgr.store.relocating_hashes
    assert spawned, "改道后 pending 仍在, 回收 daemon 对账在位(下一窗口改写到 C)"


def _simulate(mgr, dst, files, content):
    """_simulate_moved 的按参数转发(独立命名避免与导入 helper 混淆)"""
    from relocate_exec_support import _simulate_moved

    _simulate_moved(mgr, dst, files, content)


def test_supersede_anchor_resolves_physical_and_mover_preference(tmp_path, monkeypatch):
    """经别名做种成员发起再迁移: 锚点解析到前任 dst; mover 优先选账面已在锚点根的成员"""
    pin_disk_usage(monkeypatch)
    mgr, client, mod, j1, spawned, src, dst, content = _armed_env(tmp_path, monkeypatch)
    dst_c = _c_root(tmp_path)
    hb, ha = mgr.store.by_hash["HB"], mgr.store.by_hash["HA"]
    assert mod._norm(hb.save_path) == mod._norm(src), "HB 经前任别名做种, 账面还在 A"
    assert mod._norm(ha.save_path) == mod._norm(dst), "HA 是前任 mover, 账面已在 B"
    recs = [hb, ha]  # HB(账面在 A)排前 —— 旧实现会拿它当 mover 且 src 锚到 A
    facts = mod._group_facts(recs, dst_c, client)
    assert mod._norm(mod._physical_anchor(src, facts.files)) == mod._norm(dst), "A 账面经作用域解析到物理根 B"
    assert mod._norm(mod._physical_anchor(dst, facts.files)) == mod._norm(dst), "B 账面无命中原样(零行为差)"
    item = mod._start_job(recs, dst_c, facts, {"cls": "ok", "notes": [], "reasons": []}, client)
    assert item["cls"] == "started", item
    job = mod.get_job(item["job_id"])
    assert mod._norm(job.src) == mod._norm(dst), "新 job 锚在物理根(别名/spec/删链门不撞前任别名根)"
    assert job.mover == "HA", "mover 优先选账面已在锚点根的成员(免经别名搬迁留硬链接孪生)"


def test_supersede_rewritten_chain_dual_gates(tmp_path, monkeypatch):
    """rewritten 态链式双门(N11 断言 mock 面): 双别名独立/各门各判/旧门先删不扰新门/终态全清"""
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
    _simulate(mgr, dst_c, files, os.path.join(dst, "Show"))
    _run_ticks(mod, 8)
    job1, job2 = mod.get_job(j1), mod.get_job(j2)
    assert job2.phase == ru.PHASE_ARMED and job1.phase == ru.PHASE_REWRITTEN
    # rewritten 前任同样改道(核心收敛件: J2 的窗口先到时成员直接落到 C, J1 核验必须对 C)
    assert mod._norm(job1.dst) == mod._norm(dst_c)
    # 双别名独立: A 侧(J1)与 B 侧(J2)不同链、各指 C
    a_links, b_links = list(job1.alias_paths), list(job2.alias_paths)
    assert a_links and b_links and not (set(a_links) & set(b_links))
    _points_at_c(mod, job1, src, dst_c)
    _points_at_c(mod, job2, dst, dst_c)
    # 各删链门各自判依赖(R7 锚口径 = 别名作用域 + 本组成员豁免, 计划 26-11-07-1300 D9):
    # HZ 停在恰等 J2 作用域的位置(dst/Show = 别名落点, N5 等值形态) = 真依赖, 只算 J2 的门;
    # J1 的门不再数本组成员(账面仍挂 A 的 HB 由核验步把关, 成员豁免), HZ 的 B 账面也不漏进
    # J1 的门(双门各判各的作用域)
    hz = FakeTorrent(hash="HZ", name="Show", save_path=os.path.join(dst, "Show"), progress=1.0, state="pausedUP")
    client.torrents["HZ"] = hz
    mgr.store.by_hash["HZ"] = hz
    assert [h for h, _sp in mod._chain_gate_deps(job2)] == ["HZ"], "B 作用域账面 = 新门依赖"
    assert [h for h, _sp in mod._chain_gate_deps(job1)] == [], "A 门户内零依赖: 锚窄化(HB 账面在 src 不在 A 作用域), 成员到位由核验步把关"
    assert "HZ" not in [h for h, _sp in mod._chain_gate_deps(job1)], "B 根账面不漏进旧门(双门独立)"
    # 旧门先删不扰新门: 成员重启加载到 C(账面全到 C) -> J1 核验过 + 根 A 依赖清零 -> done 删 A 侧;
    # HZ 账面仍在 B -> J2 删链门依赖未清, 别名维持(删旧门不扰新门)
    for h in ("HA", "HB"):
        mgr.store.by_hash[h].save_path = dst_c
    _run_ticks(mod, 3)
    job1, job2 = mod.get_job(j1), mod.get_job(j2)
    assert job1.phase == ru.PHASE_DONE and job1.reason == ru.REASON_FINALIZED, (job1.phase, job1.reason)
    assert all(not os.path.lexists(p) for p in a_links), "A 侧别名已随 J1 终态删除"
    assert job2.phase in ru.FINALIZE_WINDOW_PHASES and all(os.path.lexists(p) for p in b_links), \
        "J2 别名仍在(HZ 依赖未清, 旧门收尾不扰新门)"
    # HZ 离场 -> J2 门清 -> 终态双别名全清 + relocating 登记整表迁出
    del mgr.store.by_hash["HZ"]
    del client.torrents["HZ"]
    _run_ticks(mod, 4)
    job2 = mod.get_job(j2)
    assert job2.phase == ru.PHASE_DONE and job2.reason == ru.REASON_FINALIZED
    assert all(not os.path.lexists(p) for p in b_links), "终态双别名全清"
    assert not mgr.store.relocating_hashes, "终态后 relocating 登记随 _sync_relocating 整表迁出"


def test_supersede_alias_busy_blocks_before_move(tmp_path, monkeypatch):
    """搬前预检(alias_busy)失败 = 整体拒绝零副作用: 无新 job / 无 setLocation / 旧现场指纹原样"""
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
    assert job1.phase == ru.PHASE_ARMED and mod._norm(job1.dst) == mod._norm(dst), "旧 job 现场指纹原样(D15)"
    assert all(afs.alias_kind_of(p) is not None for p in job1.alias_paths), "别名在位未动"


def test_supersede_alias_form_volume_gate(tmp_path, monkeypatch):
    """形态 x 卷位预检(评审 #2): hardlink 形态前任别名 + 跨卷目标 + symlink 不可用 = 整体拒绝
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


def test_supersede_post_move_redirect_retries_until_converged(tmp_path, monkeypatch):
    """搬后重定向失败注入(D20): 不回滚不判失败 —— 账面已提交(先账后链), 重试至收敛"""
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
    _simulate(mgr, dst_c, files, os.path.join(dst, "Show"))
    mod.on_task_line()  # moving -> moved
    mod.on_task_line()  # verify -> supersede: 账面改道提交, 别名重指向首链即失败
    job1, job2 = mod.get_job(j1), mod.get_job(j2)
    assert job1.phase == ru.PHASE_ARMED, "搬后失败不判失败(D20: 回滚无法恢复成员服务)"
    assert mod._norm(job1.dst) == mod._norm(dst_c), "账面改道已提交(提交点先于别名)"
    spec1 = rj.read_spec(dd, j1)
    assert mod._norm(spec1["dst"]) == mod._norm(dst_c), "spec {A→B}→{A→C} 已落"
    first_link = job1.alias_paths[0]
    assert not afs.alias_points_to(first_link, os.path.join(dst_c, "Show", os.path.basename(first_link))), \
        "失败链未改指(现场保留待重试)"
    assert job2.phase == ru.PHASE_MOVED, "J2 停在 supersede stage(反馈面: 重试中)"
    # 解除注入: 下一拍幂等续跑(进度账在 rt), 收敛后照常建链武装
    _run_ticks(mod, 7)
    job1, job2 = mod.get_job(j1), mod.get_job(j2)
    assert job2.phase == ru.PHASE_ARMED, job2.phase
    _points_at_c(mod, job1, src, dst_c)
    journal1 = rj.read_journal(dd, j1) or {}
    assert mod._norm(journal1["retarget"]["to"]) == mod._norm(dst_c), "journal retarget 在账(零残留证据面)"
    assert job1.phase == ru.PHASE_ARMED, "全程未回滚未终态"


def test_supersede_d19_mixed_state_extra_members(tmp_path, monkeypatch):
    """D19 通用补条目(混合态): 被搬离根上的前任成员并入改写清单, 不动核验集合"""
    pin_disk_usage(monkeypatch)
    mgr, client, mod, j1, spawned, src, dst, content = _armed_env(tmp_path, monkeypatch)
    dd = mgr.config.data_dir
    files = client.files_map["HA"]
    # HC: 前任成员, 账面落在被搬离根 B, 但不在本次再迁移的分桶(模拟分桶遗漏的混合态)
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
    _simulate(mgr, dst_c, files, os.path.join(dst, "Show"))
    _run_ticks(mod, 8)
    job2 = mod.get_job(j2)
    assert job2.phase == ru.PHASE_ARMED, job2.phase
    assert job2.plan.get("extra_members") == ["HC"], "D19: HC 并入改写清单"
    spec2 = rj.read_spec(dd, j2)
    assert "HC" in {m["hash_v1"] for m in spec2["members"]}, "arm spec members 覆盖补条目(daemon 按 {B→C} 改写)"
    assert "HC" not in job2.hashes, "补条目成员只进改写清单, 不动核验集合(收敛由删链门托底)"
    # 账面扫描面: HC 的 save_path 恰在被搬离根(under_alias_root 等值形态) -> 命中补条目
    assert ru.under_alias_root(hc.save_path, (dst, )) is not None


def test_supersede_cancel_guard_blocks_codestination(tmp_path, monkeypatch):
    """撤销护栏: 有改道到同一目标的在途前任时拒绝撤销(cancel_chain)且零 qB 写"""
    pin_disk_usage(monkeypatch)
    mgr, client, mod, j1, spawned, src, dst, content = _armed_env(tmp_path, monkeypatch)
    files = client.files_map["HA"]
    dst_c = _c_root(tmp_path)
    items = mod.relocate_execute(["HA"], dst_c)
    j2 = items[0]["job_id"]
    _simulate(mgr, dst_c, files, os.path.join(dst, "Show"))
    _run_ticks(mod, 8)
    assert mod.get_job(j2).phase == ru.PHASE_ARMED and mod._norm(mod.get_job(j1).dst) == mod._norm(dst_c)
    before = list(client.calls)
    out = mod.relocate_cancel(j2, cost_confirmed=True)
    assert out["cls"] == "blocked" and out["reasons"][0]["gate"] == "cancel_chain", out
    assert "改道" in out["reasons"][0]["text"]
    assert client.calls == before, "护栏拒绝 = 零 qB 写(不删链不搬回)"
    assert mod.get_job(j2).phase != ru.PHASE_CANCELLED
    assert mod.get_job(j1).phase == ru.PHASE_ARMED, "前任现场未动"
    # 无同目标同伴时护栏不触发(常规撤销照旧): 前任落终态离场(active_jobs 只看非终态)后撤 J2 放行
    # —— 直接落终态而非连跑 6 拍: 同拍会把 J2 也推进收尾窗落 DONE, 撤销就先撞终态守卫了
    # (issue 26-11-08-1608 面 1: 终态无撤销面), 放行支需要 J2 保持 armed 可撤
    for h in ("HA", "HB"):
        mgr.store.by_hash[h].save_path = dst_c
    mod._set_job(replace(mod.get_job(j1), phase=ru.PHASE_DONE, alias_paths=()))
    assert mod.get_job(j1).phase == ru.PHASE_DONE, "前任已收尾(同目标同伴清零)"
    out2 = mod.relocate_cancel(j2, cost_confirmed=True)
    assert out2["cls"] == "ok", out2
    assert mod.get_job(j2).phase == ru.PHASE_CANCELLED


def test_supersede_cancel_refuses_settled_rewrites(tmp_path, monkeypatch):
    """撤销护栏(评审 #3): journal 已有 settled 改写记录 = 拒绝撤销(成员 fastresume 已指向
    dst, 撤销留冻结态且 cancelled 终态后 daemon 不再管); 无 settled 记录撤销行为不变"""
    pin_disk_usage(monkeypatch)
    mgr, client, mod, j1, spawned, src, dst, content = _armed_env(tmp_path, monkeypatch)
    dd = mgr.config.data_dir
    files = client.files_map["HA"]
    dst_c = _c_root(tmp_path)
    items = mod.relocate_execute(["HA"], dst_c)
    j2 = items[0]["job_id"]
    _simulate(mgr, dst_c, files, os.path.join(dst, "Show"))
    _run_ticks(mod, 8)
    assert mod.get_job(j2).phase == ru.PHASE_ARMED, mod.get_job(j2).phase
    # 拒绝支: daemon 已在窗口把成员改写 settled(rewrites 账在) -> 撤销拒绝且零 qB 写
    # (4 个 settled 触发文案「等共 N 个」截断支; 另塞一条非 dict 残账记录验证守卫跳过)
    assert rj.record_rewrites(dd, j2, {h: {"status": "rewritten", "path": "x"} for h in ("HA", "HB", "HC", "HD")})
    j_body = rj.read_journal(dd, j2) or {}
    rj.write_journal(
        dd,
        j2,
        {
            **j_body,
            "rewrites": {
                **(j_body.get("rewrites") or {}),
                "HBAD": "garbage"  # 跨进程账面的撕态形态
            }
        }
    )
    before = list(client.calls)
    out = mod.relocate_cancel(j2, cost_confirmed=True)
    assert out["cls"] == "blocked" and out["reasons"][0]["gate"] == "cancel_rewritten", out
    assert "收尾" in out["reasons"][0]["text"] and "fastresume" in out["reasons"][0]["text"]
    assert client.calls == before, "拒绝撤销 = 零 qB 写(不删链不搬回)"
    assert mod.get_job(j2).phase == ru.PHASE_ARMED, "现场指纹原样"
    # 成本未确认同样直接拒(检查在成本确认之前, 不给 confirm 面误导可撤)
    out_dry = mod.relocate_cancel(j2, cost_confirmed=False)
    assert out_dry["cls"] == "blocked" and out_dry["reasons"][0]["gate"] == "cancel_rewritten", out_dry
    assert "cost" not in out_dry, "拒绝面不出成本单(不可撤的形态谈成本是误导)"
    # 放行支: settled 记录清回 pending(reset_rewrites 重放入口同款; 非 dict 残账原样保留)
    # + 前任收尾(同目标同伴清零, 不踩 cancel_chain) -> 撤销行为不变(删链 + 搬回 + cancelled)
    # —— 前任直接落终态而非连跑 6 拍: 同拍会把 J2 也推进收尾窗落 DONE, 撤销就先撞终态守卫了
    # (issue 26-11-08-1608 面 1: 终态无撤销面), 放行支需要 J2 保持 armed 可撤
    assert rj.reset_rewrites(dd, j2) == 4
    assert rj.read_rewrites(dd, j2)["HBAD"] == "garbage"
    for h in ("HA", "HB"):
        mgr.store.by_hash[h].save_path = dst_c
    mod._set_job(replace(mod.get_job(j1), phase=ru.PHASE_DONE, alias_paths=()))
    assert mod.get_job(j1).phase == ru.PHASE_DONE, "前任已收尾(同目标同伴清零)"
    calls_before_ok = list(client.calls)
    out2 = mod.relocate_cancel(j2, cost_confirmed=True)
    assert out2["cls"] == "ok", out2
    assert mod.get_job(j2).phase == ru.PHASE_CANCELLED
    assert any("set_location" in str(c) for c in client.calls[len(calls_before_ok):]), "搬回已下发"


# ---------------------------------------------------------------------------
# 覆盖率缺口清偿(26-11-07): supersede stage 拍的重试支 / 账面单点边角
# ---------------------------------------------------------------------------


def test_supersede_stage_tick_failure_keeps_retrying_without_link(tmp_path, monkeypatch):
    """重定向失败落在 supersede stage 拍(verify 拍已失败过一次): 停 moved 不建链, 注入解除后续跑收敛"""
    pin_disk_usage(monkeypatch)
    mgr, client, mod, j1, spawned, src, dst, content = _armed_env(tmp_path, monkeypatch)
    files = client.files_map["HA"]
    dst_c = _c_root(tmp_path)
    real = afs.retarget_alias
    calls = {"n": 0}

    def flaky(link, target, kind=None):
        calls["n"] += 1
        if calls["n"] <= 2:  # verify 拍 + supersede 拍各失败一次
            raise RuntimeError("占用注入(WinError 32)")
        return real(link, target, kind)

    monkeypatch.setattr(afs, "retarget_alias", flaky)
    items = mod.relocate_execute(["HA"], dst_c)
    j2 = items[0]["job_id"]
    _simulate(mgr, dst_c, files, os.path.join(dst, "Show"))
    mod.on_task_line()  # moving -> moved(verify 拍: 首链失败, stage 翻 supersede)
    mod.on_task_line()  # supersede 拍: 再失败 -> 不进建链 stage(下一拍重试)
    mod.on_task_line()  # 仍停在 supersede(注入第二链生效于本拍)
    job2 = mod.get_job(j2)
    assert job2.phase == ru.PHASE_MOVED, job2.phase
    assert mod.get_job(j1).alias_paths, "前任别名维持(重试至收敛, 不回滚)"
    assert calls["n"] == 2
    _run_ticks(mod, 8)  # 注入只挡前两链: 幂等续跑收敛
    assert mod.get_job(j2).phase == ru.PHASE_ARMED
    _points_at_c(mod, mod.get_job(j1), src, dst_c)


def test_retarget_predecessor_journal_refused_and_stray_alias(tmp_path, monkeypatch):
    """账面单点双边角: journal 拒记 retarget(诊断面不承重, 只 DEBUG 不回滚)/ 别名不在声明源下
    (跳过重定向计数, 不猜测不动); spec 缺失同拍回落(retarget_spec False)"""
    import types as _types

    from helpers import FakeTorrent

    mod = _bare_mod(data_dir=str(tmp_path / "data"))
    pred = _job("j1", phase=ru.PHASE_ARMED, src="R:/src", dst="R:/dstB", alias_paths=("R:/elsewhere/l.bin", ))
    job = _job("j2", phase=ru.PHASE_MOVED, src="R:/dstB", dst="R:/dstC", hashes=("HZ", ))
    mod._ctx.store = _types.SimpleNamespace(
        by_hash={"HZ": FakeTorrent(hash="HZ", save_path="R:/dstC/e00.mkv")}, relocating_hashes=set()
    )
    monkeypatch.setattr(rj, "mark_journal_retarget", lambda *a, **kw: False)  # 拒写注入
    rt = {}
    assert mod._retarget_predecessor(pred, job, rt) is True
    assert rt["supersede"]["j1"]["pos"] == 1, "不在声明源下的别名: 跳过重定向只计数(账不自洽留痕)"
    # 账面改道仍已提交(spec 缺失回落 + pred.dst 翻新值): journal 拒记不承重
    assert mod.get_job("j1").dst == job.dst or mod._norm(mod.get_job("j1").dst) == mod._norm("R:/dstC")


def test_rel_under_equivalence_and_outside(tmp_path):
    """_rel_under 三支: 等值(空段)/ 根下(相对段)/ 根外(None, 账不自洽)"""
    mod = _bare_mod(data_dir=str(tmp_path / "data"))
    assert mod._rel_under("R:/src", "R:/src") == ""
    assert mod._rel_under("R:/src", "R:/src/Sub/e00.mkv") == "Sub/e00.mkv"
    assert mod._rel_under("R:/src", "R:/other/e00.mkv") is None


def test_supersede_cover_movers_idempotent_replay(tmp_path):
    """D19 补条目: 前任成员并入 + 被搬离根上的命中成员并入(不在本 job 核验集);
    幂等重放并入集与现值相同 => 早退(不重复落账不刷日志)"""
    import types as _types

    from helpers import FakeTorrent

    mod = _bare_mod(data_dir=str(tmp_path / "data"))
    mod._ctx.store = _types.SimpleNamespace(
        by_hash={
            "HX": FakeTorrent(hash="HX", save_path="R:/dstB/sub/e00.mkv"),  # 前任成员, 账面已落被搬离根
            "HA": FakeTorrent(hash="HA", save_path="R:/dstC/e00.mkv"),
        },
        relocating_hashes=set(),
    )
    pred = _job("j1", hashes=("H1", "HX"), src="R:/src", dst="R:/dstB")
    job = _job("j2", hashes=("HZ", ), src="R:/dstB", dst="R:/dstC")
    mod._supersede_cover_movers(pred, job, "R:/dstB")
    first = mod.get_job("j2").plan["extra_members"]
    assert first == ["H1", "HX"], first  # 前任成员 + 命中被搬离根的组成员(HZ 本 job 已有, 不进)
    mod._supersede_cover_movers(pred, mod.get_job("j2"), "R:/dstB")  # 幂等重放: 早退支
    assert mod.get_job("j2").plan["extra_members"] == first


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
