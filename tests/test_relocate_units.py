"""test_relocate_units 测试计划: 别名单元 plan() 与迁移闸门纯判定(计划 26-10-18-1604 §04 P2)

验收判据(plan §04 P2): 表驱动测试覆盖 §3.2 五行 x 阈值边界(7/8/9) + §3.6 第 1/3/8/14/15 行;
纯函数层不触盘、不读 qB —— 全部判定经注入事实驱动。

## 测试计划(每个测试函数一条)
- test_plan_table_rows_and_threshold_boundary: §3.2 五行 x 阈值边界 7/8/9(F<thr 逐文件链接 /
  F>=thr+专属子目录 目录别名 / 平铺 逐文件 / 目录不专属 逐文件 / F>hard_max 拒绝)
- test_plan_single_member_never_alias: 单成员组恒 direct(qB 自搬, 阈值与链接能力不参与)
- test_plan_hard_max_bypassed_by_dir_alias: F>hard_max 且目录别名可行 -> 目录别名(不拒绝)
- test_plan_long_path_correction: 文件级 symlink 不可建 -> 提议目录别名(需确认); 平铺/不专属/
  内容根也超长 -> 拒绝(绝不静默降级)
- test_plan_file_link_error_carried: 文件级链接不可建的原因(提权/allow_uac)进拒绝文案
- test_layout_of: 平铺 / 单一子目录 / 混合顶层段 三布局
- test_evaluate_group_idempotent_skip: 全组已在目标位置 -> ok + 幂等 note(不再跑目标冲突闸门)
- test_evaluate_group_unfinished_job_blocks: 非终态 job 碰本组 -> blocked(unfinished);
  终态 job 不拦(§3.6 第 14 行 / S10)
- test_evaluate_group_gates_table: 闸门表驱动(incomplete/moving/target_conflict/qb_temp/
  space 不足/space 不可判定/target_unknown/same_fs 多成员/platform 多成员/第三方文件链接/硬链接)
- test_evaluate_group_single_member_remote_allows: 单成员 + 证明不过/能力不支持 -> ok + note
  (独占情形由 qB 自搬)
- test_evaluate_group_dir_alias_confirms: F>=thr + 专属 -> confirm(dir_alias, needs_confirm)
- test_evaluate_group_external_files_force_file_links: 组外文件 -> exclusive=False ->
  file_links + note 列出组外条目(不动别人的文件)
- test_evaluate_add_rows: §3.6 第 1/3/8/15 行 + 第三方链接落点(无 job 登记)
- test_same_volume_proof_table: 相等 True / 任一侧 None False / 不等 False(§2.4 硬证据口径)
"""
import os

from auto_qb.core.modules import relocate_units as ru

S = "R:/Download/Testing"
T = "H:/Download/Testing-relocated"


def _files(count, prefix="Show/e"):
    return tuple((f"{prefix}{i:02d}.mkv", 100) for i in range(count))


def _ok_facts(**kw):
    """一组「全过闸门」的基线事实(多成员/已完成/暂停/无冲突/空间足/证明过/能力可用)"""
    base = dict(
        hashes=("HA", "HB"),
        mover="HA",
        name="Show",
        save_path=S,
        target=T,
        files=_files(2),
        progresses=(1.0, 1.0),
        states=("pausedUP", "pausedUP"),
        content_root_exclusive=True,
        target_conflicts=(),
        same_volume=True,
        target_free=10**9,
        same_fs_proved=True,
        capability_ok=True,
        file_link_kind="hardlink",
        dir_link_kind="junction",
        link_path_limit=None,
        threshold=8,
        hard_max=2000,
    )
    base.update(kw)
    return ru.GroupFacts(**base)


def _gates(item):
    return [r["gate"] for r in item["reasons"]]


# ---------- plan(): §3.2 五行 x 阈值边界 ----------


def test_plan_table_rows_and_threshold_boundary():
    """§3.2 五行 x 阈值边界(7/8/9): 表驱动"""
    cases = [
        # (files 数, exclusive, threshold, hard_max, 期望形态, 行说明)
        (7, True, 8, 2000, ru.FORM_FILE_LINKS, "行1: F=7 < 8 逐文件链接"),
        (8, True, 8, 2000, ru.FORM_DIR_ALIAS, "行2: F=8 >= 8 且专属 -> 目录别名(边界命中)"),
        (9, True, 8, 2000, ru.FORM_DIR_ALIAS, "行2: F=9 > 8 同上"),
        (7, True, 7, 2000, ru.FORM_DIR_ALIAS, "行2 边界: F=7 == threshold 7 命中目录别名"),
        (8, True, 9, 2000, ru.FORM_FILE_LINKS, "行1 边界: F=8 < threshold 9 逐文件链接"),
        (9, False, 8, 2000, ru.FORM_FILE_LINKS, "行4: 目录不专属 -> 逐文件链接"),
        (9, None, 8, 2000, ru.FORM_FILE_LINKS, "行4': 专属不可判定 -> 按不专属(保守)"),
        (2001, False, 8, 2000, ru.FORM_REJECT, "行5: F>hard_max 且不能用目录别名 -> 拒绝"),
    ]
    for count, excl, thr, hard_max, expect, label in cases:
        p = ru.plan(
            S,
            _files(count),
            thr,
            hard_max,
            multi_member=True,
            content_root_exclusive=excl,
            file_link_kind="hardlink",
            dir_link_kind="junction",
        )
        assert p.form == expect, (label, p.form, p.reason)
    # 行3: 平铺(NoSubfolder)即使 exclusive=True 也逐文件链接(整目录别名不提供, D8)
    p = ru.plan(
        S,
        _files(9, prefix=""),
        8,
        2000,
        content_root_exclusive=True,
        file_link_kind="hardlink",
        dir_link_kind="junction"
    )
    assert p.form == ru.FORM_FILE_LINKS, (p.form, p.reason)
    assert p.flat and p.link_count == 9


def test_plan_single_member_never_alias():
    """单成员组恒 direct: F 再大/阈值再小/链接能力再差都不建别名(§3.2 阈值只对多成员组生效)"""
    p = ru.plan(
        S,
        _files(99),
        8,
        2000,
        multi_member=False,
        content_root_exclusive=True,
        file_link_kind=None,
        dir_link_kind=None
    )
    assert p.form == ru.FORM_DIRECT and p.link_count == 0 and not p.needs_confirm


def test_plan_hard_max_bypassed_by_dir_alias():
    """F=2001 > hard_max 但目录别名可行 -> 目录别名(1 条链接), 不触发拒绝(行5 只拦逐文件路径)"""
    p = ru.plan(
        S, _files(2001), 8, 2000, content_root_exclusive=True, file_link_kind="hardlink", dir_link_kind="junction"
    )
    assert p.form == ru.FORM_DIR_ALIAS and p.link_count == 1 and p.needs_confirm


def test_plan_long_path_correction():
    """长路径能力校正先于阈值: symlink 建不出来 -> 提议目录别名(需确认); 否则拒绝"""
    long_save = "R:/D/" + "x" * 150
    files = _files(3, prefix="Show/" + "y" * 100)
    # 专属子目录 + 目录别名可建 -> 校正提议目录别名(确认)
    p = ru.plan(
        long_save,
        files,
        8,
        2000,
        content_root_exclusive=True,
        file_link_kind="symlink",
        dir_link_kind="junction",
        link_path_limit=260
    )
    assert p.form == ru.FORM_DIR_ALIAS and p.needs_confirm
    assert "路径过长" in p.reason and "目录别名" in p.reason
    # 平铺: 无内容根可挂目录别名 -> 拒绝(文件全路径须真的超长: save 250 + 文件名 8 >= 260)
    p = ru.plan(
        "R:/D/" + "x" * 250,
        _files(3, prefix=""),
        8,
        2000,
        content_root_exclusive=True,
        file_link_kind="symlink",
        dir_link_kind="junction",
        link_path_limit=260
    )
    assert p.form == ru.FORM_REJECT and "路径过长" in p.reason
    # 目录不专属: 目录别名硬前提不成立 -> 拒绝(出处可解释, 不是猜测)
    p = ru.plan(
        long_save,
        files,
        8,
        2000,
        content_root_exclusive=False,
        file_link_kind="symlink",
        dir_link_kind="junction",
        link_path_limit=260
    )
    assert p.form == ru.FORM_REJECT
    # 内容根路径本身也超长 -> 目录别名也建不出来 -> 拒绝
    p = ru.plan(
        long_save,
        _files(3, prefix="z" * 200 + "/e"),
        8,
        2000,
        content_root_exclusive=True,
        file_link_kind="symlink",
        dir_link_kind="junction",
        link_path_limit=260
    )
    assert p.form == ru.FORM_REJECT and "内容根路径过长" in p.reason
    # POSIX(无 limit): 同样路径照常逐文件链接
    p = ru.plan(
        long_save,
        files,
        8,
        2000,
        content_root_exclusive=True,
        file_link_kind="symlink",
        dir_link_kind="symlink",
        link_path_limit=None
    )
    assert p.form == ru.FORM_FILE_LINKS


def test_plan_file_link_error_carried():
    """文件级链接不可建时, 注入的原因(提权/allow_uac=false)必须进拒绝文案(自解释)"""
    p = ru.plan(
        S,
        _files(3),
        8,
        2000,
        content_root_exclusive=True,
        file_link_kind=None,
        file_link_error="需提权(UAC)且 allow_uac=false: 直接拒绝",
        dir_link_kind=None
    )
    assert p.form == ru.FORM_REJECT and "提权" in p.reason


def test_layout_of():
    """三种布局: 平铺 / 单一子目录 / 混合顶层段"""
    assert ru.layout_of(S, ("a.mkv", "b.mkv")) == (True, "")
    assert ru.layout_of(S, ("Show/a.mkv", "Show/sub/b.mkv")) == (False, "Show")
    assert ru.layout_of(S, ("Show/a.mkv", "Other/b.mkv")) == (False, "")  # 混合: 无单一内容根
    assert ru.layout_of(S, ()) == (True, "")


# ---------- evaluate_group(): 闸门 ----------


def test_evaluate_group_idempotent_skip():
    """全组已在目标位置 -> ok + 幂等 note; 目标冲突闸门对同路径无意义(直接返回)"""
    item = ru.evaluate_group(_ok_facts(target=S))
    assert item["cls"] == ru.CLS_OK and item["form"] == ru.FORM_DIRECT
    assert any("幂等" in n for n in item["notes"])
    assert item["reasons"] == []


def test_evaluate_group_unfinished_job_blocks():
    """非终态 job 碰本组 -> blocked(unfinished); 终态 job 不拦(§3.6 第 14 行 / S10)"""
    job = ru.RelocateJob(
        job_id="j1",
        hashes=("HA", "HB"),
        mover="HA",
        src=S,
        dst=T,
        scope=os.path.join(S, "Show"),
        alias_kind="dir",
        phase=ru.PHASE_ARMED,
    )
    item = ru.evaluate_group(_ok_facts(jobs=(job, )))
    assert item["cls"] == ru.CLS_BLOCKED and "unfinished" in _gates(item)
    done = ru.RelocateJob(
        job_id="j2", hashes=("HA", ), mover="HA", src=S, dst=T, scope=os.path.join(S, "Show"), phase=ru.PHASE_DONE
    )
    item2 = ru.evaluate_group(_ok_facts(jobs=(done, )))
    assert item2["cls"] == ru.CLS_OK and "unfinished" not in _gates(item2)
    # hash 不相交但作用域覆盖内容根 -> 同样拦(别名是作用域不是快照, D7)
    other = ru.RelocateJob(
        job_id="j3", hashes=("HZ", ), mover="HZ", src=S, dst=T, scope=os.path.join(S, "Show"), phase=ru.PHASE_MOVING
    )
    item3 = ru.evaluate_group(_ok_facts(jobs=(other, )))
    assert "unfinished" in _gates(item3)


def test_evaluate_group_gates_table():
    """闸门表驱动: 每行一个 gate id, blocked 一票否决"""
    cases = [
        (_ok_facts(progresses=(1.0, 0.5)), "incomplete", "未完成成员"),
        (_ok_facts(states=("moving", "pausedUP")), "moving", "qB 搬迁态"),
        (_ok_facts(target_conflicts=("Show/e00.mkv", )), "target_conflict", "目标同名内容"),
        (_ok_facts(qb_temp_entries=("e00.mkv.!qB", )), "qb_temp", ".!qB 临时文件"),
        (_ok_facts(target_free=None), "space", "空间不可判定"),
        (_ok_facts(target_free=50), "space", "空间不足"),
        (_ok_facts(target_unknown=True), "target_unknown", "目标存在性不可判定"),
        (_ok_facts(same_fs_proved=False), "same_fs", "同卷证明不过(多成员)"),
        (_ok_facts(capability_ok=False, capability_reason="跨 OS 容器"), "platform", "能力矩阵不支持(多成员)"),
        (_ok_facts(third_party_link_files=("Show/e00.mkv", )), "third_party_link", "第三方文件级链接"),
        (_ok_facts(hardlink_files=("Show/e00.mkv", )), "hardlink", "第三方硬链接"),
        (_ok_facts(target_free=50, same_fs_proved=False), "space", "多闸门并发: 首个 blocked 即定 cls"),
    ]
    for facts, gate, label in cases:
        item = ru.evaluate_group(facts)
        assert item["cls"] == ru.CLS_BLOCKED, (label, item["cls"], item["reasons"])
        assert gate in _gates(item), (label, _gates(item))


def test_evaluate_group_single_member_remote_allows():
    """单成员 + 同卷证明不过/能力不支持 -> ok + note(独占情形由 qB 自搬, §3.3)"""
    facts = _ok_facts(
        hashes=("HA", ),
        mover="HA",
        progresses=(1.0, ),
        states=("pausedUP", ),
        same_fs_proved=False,
        capability_ok=False,
        capability_reason="远程 qB",
        same_volume=None,
    )
    item = ru.evaluate_group(facts)
    assert item["cls"] == ru.CLS_OK and item["form"] == ru.FORM_DIRECT
    assert any("same_fs" == r["gate"] for r in item["reasons"]) or item["reasons"] == []
    joined = " ".join(item["notes"])
    assert "同一块盘" in joined and "独占" in joined
    assert any("不可判定" in n for n in item["notes"])  # same_volume=None -> 按跨卷保守处理


def test_evaluate_group_dir_alias_confirms():
    """F>=阈值 + 目录专属 -> confirm + dir_alias + needs_confirm(确认框摊开)"""
    facts = _ok_facts(files=_files(9))
    item = ru.evaluate_group(facts)
    assert item["cls"] == ru.CLS_CONFIRM
    assert item["form"] == ru.FORM_DIR_ALIAS and item["needs_confirm"] is True
    assert item["alias_kind"] == "junction" and item["link_count"] == 1


def test_evaluate_group_external_files_force_file_links():
    """组外文件 -> exclusive=False -> file_links + note 列出组外条目(只链自己的文件)"""
    facts = _ok_facts(
        files=_files(9),
        content_root_exclusive=False,
        external_entries=("S01E02.mkv", ),
        misc_entries=("E01.torrent", ),
    )
    item = ru.evaluate_group(facts)
    assert item["cls"] == ru.CLS_OK and item["form"] == ru.FORM_FILE_LINKS and item["link_count"] == 9
    assert any("S01E02.mkv" in n for n in item["notes"])
    assert any("E01.torrent" in n for n in item["notes"])


# ---------- evaluate_add(): §3.6 第 1/3/8/15 行 ----------


def _dir_job(phase=ru.PHASE_ARMED):
    return ru.RelocateJob(
        job_id="j1",
        hashes=("HA", "HB"),
        mover="HA",
        src=S,
        dst=T,
        scope=os.path.join(S, "Show"),
        alias_kind="dir",
        phase=phase,
    )


def _file_job(phase=ru.PHASE_ARMED, paths=("Show/S01E01.mkv", )):
    return ru.RelocateJob(
        job_id="j1",
        hashes=("HA", "HB"),
        mover="HA",
        src=S,
        dst=T,
        scope=os.path.join(S, "Show"),
        alias_kind="file",
        alias_paths=paths,
        phase=phase,
    )


def test_evaluate_add_rows():
    """§3.6 第 1/3/8/15 行 + 第三方链接落点(无 job 登记)"""
    # 行 15: 目录别名作用域命中 -> confirm + 实际落点(在 dst 下) + 卷剩余
    r = ru.evaluate_add(ru.AddFacts(save_path=S, name="Show", jobs=(_dir_job(), ), target_free=5000))
    assert r["cls"] == ru.CLS_CONFIRM
    assert r["actual_path"] and r["actual_path"].replace("\\", "/").startswith(T)
    assert r["volume_free"] == 5000 and r["reasons"][0]["gate"] == "alias_scope"
    # 行 1: 逐文件链接作用域 + 异名落点 -> 原盘真实目录, 无影响
    r = ru.evaluate_add(ru.AddFacts(save_path=S, name="Show", jobs=(_file_job(), )))
    assert r["cls"] == ru.CLS_OK and r["reasons"] == []
    # 行 3: 逐文件链接作用域 + 落点本身是链接(同名) -> confirm + 覆盖警示
    r = ru.evaluate_add(
        ru.AddFacts(
            save_path=S,
            name="Show",
            jobs=(_file_job(), ),
            landing_is_link=True,
            landing_link_kind="hardlink",
            landing_link_target="H:/reloc/S01E01.mkv",
        )
    )
    assert r["cls"] == ru.CLS_CONFIRM and r["reasons"][0]["gate"] == "alias_file"
    assert r["actual_path"] == "H:/reloc/S01E01.mkv" and "覆盖" in r["reasons"][0]["text"]
    # 行 8: 收尾窗口(链接已删未 finalize) -> confirm 警示重复落盘
    r = ru.evaluate_add(ru.AddFacts(save_path=S, name="Whatever", jobs=(_dir_job(phase=ru.PHASE_REMOVED), )))
    assert r["cls"] == ru.CLS_CONFIRM and r["reasons"][0]["gate"] == "finalize_window"
    # 无 job + 落点是第三方链接 -> confirm 警示
    r = ru.evaluate_add(
        ru.AddFacts(
            save_path=S,
            name="Show",
            landing_is_link=True,
            landing_link_kind="symlink",
            landing_link_target="D:/elsewhere",
        )
    )
    assert r["cls"] == ru.CLS_CONFIRM and r["reasons"][0]["gate"] == "alias_path"
    # 基线: 无 job 无链接 -> ok(第 1 行的反面: 完全无交叉)
    r = ru.evaluate_add(ru.AddFacts(save_path=S, name="Other"))
    assert r["cls"] == ru.CLS_OK and r["requested_path"].endswith("Other")


def test_evaluate_group_cross_volume_note():
    """跨卷 note: same_volume=False -> 「跨卷: qB 走复制; 逐文件别名用符号链接」"""
    item = ru.evaluate_group(_ok_facts(same_volume=False))
    assert any("跨卷" in n for n in item["notes"])


def test_same_volume_proof_table():
    """§2.4 同卷证明: 同量级算同盘(带写盘抖动容差); 任一侧读不到 -> False"""
    assert ru.same_volume_proof(48196329472, 48196329472) is True
    assert ru.same_volume_proof(None, 1) is False
    assert ru.same_volume_proof(1, None) is False
    assert ru.same_volume_proof(10**9, 10**12) is False  # 差数量级(超出相对+绝对容差带)
    assert ru.same_volume_proof(1, 1000) is True  # 差 < 绝对容差(1GiB 带)


# ---------- 边角分支(覆盖补齐) ----------


def test_plan_empty_files_reject():
    """空文件列表 -> reject(无法判定内容布局)"""
    p = ru.plan(S, (), 8, 2000)
    assert p.form == ru.FORM_REJECT and "文件列表为空" in p.reason


def test_plan_hard_max_dir_kind_none_suffix():
    """F>hard_max 且目录专属但目录别名形态未探测到 -> 拒绝文案带「目录别名不可用」"""
    p = ru.plan(
        S,
        _files(2001),
        8,
        2000,
        content_root_exclusive=True,
        file_link_kind="hardlink",
        dir_link_kind=None,
        dir_link_error="未探测到可用形态"
    )
    assert p.form == ru.FORM_REJECT and "目录别名不可用" in p.reason


def test_within_empty_scope_never_matches():
    """scope 为空的 job 永不命中作用域/内容根(防御)"""
    job = ru.RelocateJob(job_id="j", hashes=("HA", ), mover="HA", src=S, dst=T, scope="")
    assert job.scope_hit(S, os.path.join(S, "Show")) is False
    assert job.blocks_relocation(("HA", ), os.path.join(S, "Show")) is True  # hash 相交仍拦


def test_evaluate_group_form_reject_gate():
    """plan 拒绝经 form 闸门产出 blocked(空文件列表场景); 杂项 note 同时出现"""
    item = ru.evaluate_group(_ok_facts(files=()))
    assert item["cls"] == ru.CLS_BLOCKED and "form" in _gates(item)


def test_evaluate_group_confirm_not_downgraded_by_later_block():
    """先 confirm(目录别名)后被硬闸门否决 -> 整体 blocked, confirm 项保留在 reasons(不降级不丢失)"""
    item = ru.evaluate_group(_ok_facts(files=_files(9), target_conflicts=("Show/e00.mkv", )))
    assert item["cls"] == ru.CLS_BLOCKED
    assert "target_conflict" in _gates(item)
    assert any(r["cls"] == ru.CLS_CONFIRM and r["gate"] == "form" for r in item["reasons"])


def test_evaluate_add_skips_terminal_and_unmatched_jobs():
    """添加预检: 终态 job 与未命中作用域的 job 都跳过, 命中的才判定"""
    done = ru.RelocateJob(
        job_id="d",
        hashes=("HA", ),
        mover="HA",
        src=S,
        dst=T,
        scope=os.path.join(S, "Show"),
        alias_kind="dir",
        phase=ru.PHASE_DONE
    )
    other = ru.RelocateJob(
        job_id="o",
        hashes=("HZ", ),
        mover="HZ",
        src="R:/elsewhere",
        dst=T,
        scope="R:/elsewhere/Show",
        alias_kind="dir",
        phase=ru.PHASE_ARMED
    )
    hit = _dir_job()
    r = ru.evaluate_add(ru.AddFacts(save_path=S, name="Show", jobs=(done, other, hit), target_free=7))
    assert r["cls"] == ru.CLS_CONFIRM and r["reasons"][0]["gate"] == "alias_scope"
