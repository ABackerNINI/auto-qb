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
- test_evaluate_group_gates_table: 闸门表驱动(incomplete/moving/target_conflict/target_type/qb_temp/
  space 不足/space 不可判定/target_unknown/same_fs 判负多成员/platform 多成员/第三方文件链接/硬链接)
- test_evaluate_group_single_member_remote_allows: 单成员 + 证明不过/能力不支持 -> ok + note
  (独占情形由 qB 自搬)
- test_evaluate_group_same_fs_semantics_p3: P3 闸门重排 —— 未证明多成员转 note(执行链强探测兜底)/
  判负多成员硬拦(fs.path_map + assume_shared 两条出路)/单成员判负维持 note/same_fs_note 入 notes
- test_evaluate_group_same_volume_space_exempt: 同卷 rename 不占额外空间 -> 空间预检不适用(R2 #1);
  跨卷不足/不可读仍拦
- test_within_empty_scope_false: _within 空 scope -> False(端到端退化行为; 守卫支由替身直驱用例覆盖)
- test_evaluate_group_dir_alias_confirms: F>=thr + 专属 -> confirm(dir_alias, needs_confirm)
- test_evaluate_group_external_files_force_file_links: 组外文件 -> exclusive=False ->
  file_links + note 列出组外条目(不动别人的文件)
- test_evaluate_add_rows: §3.6 第 1/3/8/15 行 + 第三方链接落点(无 job 登记)
- test_same_volume_proof_table: 相等 True / 任一侧 None False / 不等 False(§2.4 硬证据口径)
- test_evaluate_add_skips_terminal_and_unmatched_jobs
- test_evaluate_group_confirm_not_downgraded_by_later_block
- test_evaluate_group_cross_volume_note
- test_evaluate_group_form_reject_gate
- test_job_dict_roundtrip: job 落账 roundtrip(含 move_issued 往返 + 老账缺位按未下发)
- test_job_from_dict_type_error_and_legacy_phase_map: 旧账相位前向映射(S4)+ 新对账兜底
- test_plan_empty_files_reject
- test_plan_hard_max_dir_kind_none_suffix
- test_reconcile_table_rows
- test_finalize_window_phase_set_redefined: S4 相位集 {armed, rewritten}+ 旧三相位退役
- test_blocks_relocation_finalize_window_release: D15 收窄直测(收尾窗放行/前段仍拦)
- test_ensure_daemon_action_three_way: S3 新链对账判据三分(pending 空/daemon 健康/pending+stale
  -> ensure_daemon)+ 新动作不在 reconcile 旧表(本期两链并存, 计划 26-11-05-0808 §3.2)
- test_recover_exec_phase
- test_resolve_physical_layer1
- test_job_from_dict_type_error_and_legacy_phase_map
- test_scope_hit_flat_does_not_cover_subdirs
- test_stall_verdict_boundaries
- test_within_empty_scope_never_matches

W8(R32) S5a 守阵追加(变异测试 classify-units 真洞簇钉面):
- test_norm_backslash_bridge_and_within_guard: _norm 反斜杠归一桥(平台盲区)+ 空 scope 守卫
- test_join_slash_normalization_faces: _join 拼接契约(反斜杠归一/尾斜杠剥离/相对段剥离)
- test_plan_long_path_exact_boundaries: 长路径校正恰 260 边界(内容根/最长文件)+ link_path_limit 透传
- test_same_volume_proof_tolerance_band: 同卷证明容差带(1GiB 绝对带不翻倍 + 恰等边界)
- test_job_dict_full_roundtrip_values: 落账往返保值(非默认字段全量)+ 坏 plan 形状拒收
- test_scope_hit_src_guard_and_resolve_order: src 守卫 + 解析序(终态跳过不中断)+ 收尾去重 + 历史账兜底链
- test_stall_verdict_grow_and_late_warn_branches: 停滞 WARN 侧支(增长/末支/moving 恰等边界)
- test_plan_layout_filter_and_last_mile_contract: 空名过滤 + 末段 link_kind + 缺省实参契约
- test_plan_dir_link_error_long_path_text: 目录错误前段拼进长路径拒绝文案(不炸/不丢/不伪空格)
- test_evaluate_group_receipt_contract_keys: 回执契约键面(幂等/主回执/添加预检三张 dict)
- test_evaluate_group_text_faces_representatives: 文案代表面(空间/未完成/硬上限)与恰等边界
- test_evaluate_add_flow_faces: 添加预检流面(终态不中断/作用域外/rel 切片各形态)

2026-11-02 issue 26-11-02-1208 追加(L490 跨卷空间不足分支红验):
- test_evaluate_group_space_cross_volume_branch: 严格小于才拒 / 恰等放行 / same_volume=None 按跨卷保守拒 / 同卷豁免

覆盖率第三轮 T2b 补测(26-11-05):
- test_within_empty_scope_guard_via_norm_empty: 空 scope 守卫(归一化空串防御弧, 经 _norm 替身直驱)永不匹配(98->99)
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
    """搬迁在途 job 碰本组 -> blocked(unfinished); 终态不拦; 收尾窗放行(D15 收窄)

    S4(D15): blocks_relocation 的同组拦截收窄到前段相位(moving/watching/moved) ——
    armed/rewritten 放行同组再迁(未收尾再迁移支线, supersede 重定向本体在 S5);
    终态 job 照旧不拦。
    """
    moving = ru.RelocateJob(
        job_id="j1",
        hashes=("HA", "HB"),
        mover="HA",
        src=S,
        dst=T,
        scope=os.path.join(S, "Show"),
        alias_kind="dir",
        phase=ru.PHASE_MOVING,
    )
    item = ru.evaluate_group(_ok_facts(jobs=(moving, )))
    assert item["cls"] == ru.CLS_BLOCKED and "unfinished" in _gates(item)
    done = ru.RelocateJob(
        job_id="j2", hashes=("HA", ), mover="HA", src=S, dst=T, scope=os.path.join(S, "Show"), phase=ru.PHASE_DONE
    )
    item2 = ru.evaluate_group(_ok_facts(jobs=(done, )))
    assert item2["cls"] == ru.CLS_OK and "unfinished" not in _gates(item2)
    # 收尾窗(armed/rewritten)放行同组再迁: D15 放行集(S5 supersede 的闸门前提)
    for ph in (ru.PHASE_ARMED, ru.PHASE_REWRITTEN):
        fin = ru.RelocateJob(
            job_id="jf",
            hashes=("HA", "HB"),
            mover="HA",
            src=S,
            dst=T,
            scope=os.path.join(S, "Show"),
            alias_kind="dir",
            phase=ph,
        )
        itemf = ru.evaluate_group(_ok_facts(jobs=(fin, )))
        assert itemf["cls"] == ru.CLS_OK and "unfinished" not in _gates(itemf), ph
    # hash 不相交但作用域覆盖内容根 -> 同样拦(别名是作用域不是快照, D7) —— 仅目录别名,
    # 且**全部非终态相位保留**(armed/rewritten 期间别名在位, 别组写入照样穿链接进旧 job 目标)
    other = ru.RelocateJob(
        job_id="j3",
        hashes=("HZ", ),
        mover="HZ",
        src=S,
        dst=T,
        scope=os.path.join(S, "Show"),
        phase=ru.PHASE_ARMED,
        plan={"form": ru.FORM_DIR_ALIAS},
    )
    item3 = ru.evaluate_group(_ok_facts(jobs=(other, )))
    assert "unfinished" in _gates(item3)
    # P7 S14b 回归: 逐文件链接组(平铺内容根 scope=save_path)在途时, 同 save_path 下的
    # **别组**不被拦 —— 逐文件链接无目录重定向危害, §08 要求多选按组拆开各迁各的
    flat = ru.RelocateJob(
        job_id="j4",
        hashes=("HZ", ),
        mover="HZ",
        src=S,
        dst=T,
        scope=S,
        phase=ru.PHASE_ARMED,
        alias_kind="file",
        plan={"form": ru.FORM_FILE_LINKS},
    )
    item4 = ru.evaluate_group(_ok_facts(jobs=(flat, )))
    assert item4["cls"] == ru.CLS_OK and "unfinished" not in _gates(item4)
    # 同组(hash 相交)在前段相位仍拦: 搬迁在途叠加 setLocation 会互相覆盖
    same_member = ru.RelocateJob(
        job_id="j5",
        hashes=("HA", ),
        mover="HA",
        src=S,
        dst=T,
        scope=S,
        phase=ru.PHASE_MOVING,
        plan={"form": ru.FORM_FILE_LINKS},
    )
    item5 = ru.evaluate_group(_ok_facts(jobs=(same_member, )))
    assert "unfinished" in _gates(item5)


def test_evaluate_group_gates_table():
    """闸门表驱动: 每行一个 gate id, blocked 一票否决"""
    cases = [
        (_ok_facts(progresses=(1.0, 0.5)), "incomplete", "未完成成员"),
        (_ok_facts(states=("moving", "pausedUP")), "moving", "qB 搬迁态"),
        (_ok_facts(target_conflicts=("Show/e00.mkv", )), "target_conflict", "目标同名内容"),
        (_ok_facts(target_not_dir=True), "target_type", "目标存在但不是目录"),
        (_ok_facts(qb_temp_entries=("e00.mkv.!qB", )), "qb_temp", ".!qB 未落定文件"),
        (_ok_facts(target_free=None, same_volume=False), "space", "空间不可判定"),
        (_ok_facts(target_free=50, same_volume=False), "space", "空间不足"),
        (_ok_facts(target_unknown=True), "target_unknown", "目标存在性不可判定"),
        (_ok_facts(same_fs_negative=True), "same_fs", "同机证据判负(多成员, P3)"),
        (_ok_facts(capability_ok=False, capability_reason="跨 OS 容器"), "platform", "能力矩阵不支持(多成员)"),
        (_ok_facts(third_party_link_files=("Show/e00.mkv", )), "third_party_link", "第三方文件级链接"),
        (_ok_facts(hardlink_files=("Show/e00.mkv", )), "hardlink", "第三方硬链接"),
        (_ok_facts(target_free=50, same_volume=False, same_fs_proved=False), "space", "多闸门并发: 首个 blocked 即定 cls"),
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


def test_evaluate_group_same_fs_semantics_p3():
    """P3 闸门重排(计划 26-11-04-0055 §03.1): 未证明多成员不再硬拦(note 转执行链强探测);
    判负(same_fs_negative)多成员硬拦且文案给 fs.path_map / assume_shared 两条出路;
    单成员判负维持 note 不拦; same_fs_note 原样入 notes"""
    # 未证明 + 非判负(多成员): ok + note「一次性强探测」(旧行为是 GATE_SAME_FS 硬拦)
    item = ru.evaluate_group(_ok_facts(same_fs_proved=False))
    assert item["cls"] == ru.CLS_OK and "same_fs" not in _gates(item)
    assert any("一次性强探测" in n for n in item["notes"]), item["notes"]
    # 判负(多成员): blocked + same_fs + 两条出路
    item2 = ru.evaluate_group(_ok_facts(same_fs_proved=False, same_fs_negative=True))
    assert item2["cls"] == ru.CLS_BLOCKED and "same_fs" in _gates(item2)
    text = next(r["text"] for r in item2["reasons"] if r["gate"] == "same_fs")
    assert "fs.path_map" in text and "assume_shared" in text
    # 单成员判负: 维持 note 不拦(独占情形 qB 自搬)
    item3 = ru.evaluate_group(
        _ok_facts(
            hashes=("HA", ),
            mover="HA",
            progresses=(1.0, ),
            states=("pausedUP", ),
            same_fs_proved=False,
            same_fs_negative=True
        )
    )
    assert item3["cls"] == ru.CLS_OK and "same_fs" not in _gates(item3)
    assert any("独占" in n for n in item3["notes"])
    # same_fs_note 原样入 notes(proved 与否都带)
    note = "同机判定: relocate.assume_shared=true —— 未经 auto-qb 验证, 由用户承担"
    item4 = ru.evaluate_group(_ok_facts(same_fs_note=note))
    assert note in item4["notes"]
    item5 = ru.evaluate_group(_ok_facts(same_fs_proved=False, same_fs_note="判负详情: x"))
    assert "判负详情: x" in item5["notes"]


def test_evaluate_group_same_volume_space_exempt():
    """同卷 rename 不占额外空间: 空间预检不适用(R2 #1); 跨卷同数值仍拦"""
    item = ru.evaluate_group(_ok_facts(same_volume=True, target_free=100))
    assert "space" not in _gates(item), _gates(item)
    item2 = ru.evaluate_group(_ok_facts(same_volume=False, target_free=100))
    assert "space" in _gates(item2)
    # 同卷 + 卷剩余不可读: rename 语义下同样不拦
    item3 = ru.evaluate_group(_ok_facts(same_volume=True, target_free=None))
    assert "space" not in _gates(item3)
    # 跨卷 + 不可读: 照拦(不可判定一律拒绝)
    item4 = ru.evaluate_group(_ok_facts(same_volume=False, target_free=None))
    assert "space" in _gates(item4)


def test_evaluate_group_space_cross_volume_branch():
    """GATE_SPACE 跨卷空间不足分支(relocate_units.py:490): 严格小于才拒; 恰等放行;
    same_volume=None 按跨卷保守拒; 同卷 rename 豁免(R2 #1)"""
    # needed = 2 x 100 = 200; 跨卷 + 剩余 199 < 200 -> 第二条拒绝分支命中(隔离: 无其他闸门)
    item = ru.evaluate_group(_ok_facts(target_free=199, same_volume=False))
    assert item["cls"] == ru.CLS_BLOCKED
    assert _gates(item) == ["space"], _gates(item)
    text = item["reasons"][0]["text"]
    assert "目标卷剩余 199 字节" in text and "本组数据 200 字节" in text and "空间不足" in text
    # 恰等所需 -> 不拒(判据是严格小于, 不是 <=)
    item = ru.evaluate_group(_ok_facts(target_free=200, same_volume=False))
    assert item["cls"] == ru.CLS_OK and "space" not in _gates(item)
    # 卷关系不可判定(None)按跨卷保守处理 -> 照拦(不得因 None 放行)
    item = ru.evaluate_group(_ok_facts(target_free=199, same_volume=None))
    assert item["cls"] == ru.CLS_BLOCKED and "space" in _gates(item)
    # 同卷 rename 不占额外空间 -> 空间预检不适用
    item = ru.evaluate_group(_ok_facts(target_free=199, same_volume=True))
    assert item["cls"] == ru.CLS_OK and "space" not in _gates(item)


def test_within_empty_scope_false():
    """_within 空 scope -> False(端到端退化行为; 守卫支现实不可达、经 _norm 替身直驱用例
    test_within_empty_scope_guard_via_norm_empty 覆盖, 本例实际由前缀比较返回 False)"""
    assert ru._within("", "R:/any/path") is False


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
    """§3.6 第 1/3/8/15 行(S4/D16 重排: 收尾窗分支先行且承重) + 第三方链接落点(无 job 登记)"""
    # 行 1': 收尾窗 + 目录别名(D16 变更承重) -> confirm(finite_window) + 实际落点(在 dst 下) + 卷剩余
    r = ru.evaluate_add(ru.AddFacts(save_path=S, name="Show", jobs=(_dir_job(), ), target_free=5000))
    assert r["cls"] == ru.CLS_CONFIRM
    assert r["actual_path"] and r["actual_path"].replace("\\", "/").startswith(T)
    assert r["volume_free"] == 5000 and r["reasons"][0]["gate"] == "finalize_window"
    assert any("删链门" in r["reasons"][0]["text"] for _ in (0, ))
    # 行 1: 前段相位(moved)+ 逐文件链接作用域 + 异名落点 -> 原盘真实目录, 无影响
    r = ru.evaluate_add(ru.AddFacts(save_path=S, name="Show", jobs=(_file_job(phase=ru.PHASE_MOVED), )))
    assert r["cls"] == ru.CLS_OK and r["reasons"] == []
    # 行 1'': 收尾窗 + 逐文件链接 + 异名落点(D16): 账面记旧根 -> 删链门永久依赖 -> confirm
    r = ru.evaluate_add(ru.AddFacts(save_path=S, name="Show", jobs=(_file_job(), )))
    assert r["cls"] == ru.CLS_CONFIRM and r["reasons"][0]["gate"] == "finalize_window"
    # 行 3: 前段相位 + 落点本身是链接(同名) -> confirm + 覆盖警示
    r = ru.evaluate_add(
        ru.AddFacts(
            save_path=S,
            name="Show",
            jobs=(_file_job(phase=ru.PHASE_MOVED), ),
            landing_is_link=True,
            landing_link_kind="hardlink",
            landing_link_target="H:/reloc/S01E01.mkv",
        )
    )
    assert r["cls"] == ru.CLS_CONFIRM and r["reasons"][0]["gate"] == "alias_file"
    assert r["actual_path"] == "H:/reloc/S01E01.mkv" and "覆盖" in r["reasons"][0]["text"]
    # 行 8: 收尾窗口(armed/rewritten, D16 变更承重) -> confirm 警示删链门永久依赖
    r = ru.evaluate_add(ru.AddFacts(save_path=S, name="Whatever", jobs=(_dir_job(phase=ru.PHASE_REWRITTEN), )))
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
    assert r["cls"] == ru.CLS_CONFIRM and r["reasons"][0]["gate"] == "finalize_window", r
    assert r["actual_path"] and r["actual_path"].replace("\\", "/").startswith(T)


# ---------------------------------------------------------------- P3/P6 纯判定(P3 执行期, P6 对账)


def _job(**kw):
    base = dict(
        job_id="jr-1",
        hashes=("HA", "HB"),
        mover="HA",
        src=S,
        dst=T,
        scope=os.path.join(S, "Show"),
        alias_kind="file",
        phase=ru.PHASE_ARMED,
        alias_paths=(os.path.join(S, "Show", "e00.mkv"), ),
    )
    base.update(kw)
    return ru.RelocateJob(**base)


def test_reconcile_table_rows():
    """S4 新对账表逐行(判据面): 全员到 dst -> verify / 别名丢失+qB 在 -> rebuild / 其余 wait"""
    job = _job()
    # armed 做种中(别名在, 未全员到 dst) -> wait
    assert ru.reconcile(job, alias_present=True, qb_up=True, all_at_dst=False) == ru.ACT_WAIT
    # qB 不在(等下线窗口/等重启加载) -> wait(journal 悬挂是良性态, D10)
    assert ru.reconcile(job, alias_present=True, qb_up=False, all_at_dst=False) == ru.ACT_WAIT
    assert ru.reconcile(job, alias_present=False, qb_up=False, all_at_dst=False) == ru.ACT_WAIT
    # 别名丢失 + qB 在 -> rebuild(rebuild-from-journal 判据面)
    assert ru.reconcile(job, alias_present=False, qb_up=True, all_at_dst=False) == ru.ACT_REBUILD
    # 全员已在目标位置(qB 在) -> verify(核验+删链推进单点; 别名在否不影响判据)
    assert ru.reconcile(job, alias_present=True, qb_up=True, all_at_dst=True) == ru.ACT_VERIFY
    assert ru.reconcile(job, alias_present=False, qb_up=True, all_at_dst=True) == ru.ACT_VERIFY
    # qB 不在即使已到 dst -> wait(qB 回来核验; 下线窗口是 daemon 现场)
    assert ru.reconcile(job, alias_present=True, qb_up=False, all_at_dst=True) == ru.ACT_WAIT


def test_finalize_window_phase_set_redefined():
    """S4 相位模型: FINALIZE_WINDOW_PHASES == {armed, rewritten}(D16 变更承重);
    旧收尾窗三相位常量退役; PENDING_TAG_PHASES 与收尾窗同集(标签镜像窗口自动跟随);
    rewritten 非终态(终态集不变)"""
    assert ru.FINALIZE_WINDOW_PHASES == frozenset({ru.PHASE_ARMED, ru.PHASE_REWRITTEN})
    assert ru.PENDING_TAG_PHASES == ru.FINALIZE_WINDOW_PHASES
    assert ru.PHASE_REWRITTEN == "rewritten"
    assert not hasattr(ru, "PHASE_REMOVING") and not hasattr(ru,
                                                             "PHASE_REMOVED") and not hasattr(ru, "PHASE_FINALIZING")
    assert ru.PHASE_REWRITTEN not in ru.TERMINAL_PHASES


def test_blocks_relocation_finalize_window_release():
    """D15 收窄直测: 收尾窗(armed/rewritten)同组不拦; 前段(moving/watching/moved)仍拦"""
    for ph, expect in (
        (ru.PHASE_ARMED, False), (ru.PHASE_REWRITTEN, False), (ru.PHASE_MOVING, True), (ru.PHASE_WATCHING, True),
        (ru.PHASE_MOVED, True)
    ):
        job = _job(phase=ph)
        assert job.blocks_relocation(("HA", ), os.path.join(S, "Show")) is expect, ph


def test_stall_verdict_boundaries():
    """停滞判据: moving 永不判失败(长耗时只 warn); 不 moving 且不增长超时 -> stalled"""
    assert ru.stall_verdict(False, True, 10, 7200, 600, 0) == ru.STALL_OK
    assert ru.stall_verdict(False, True, 8000, 7200, 600, 9999) == ru.STALL_WARN  # moving 期间再久也不失败
    assert ru.stall_verdict(True, False, 10, 7200, 600, 0) == ru.STALL_OK  # 体积在长
    assert ru.stall_verdict(False, False, 10, 7200, 600, 599) == ru.STALL_OK
    assert ru.stall_verdict(False, False, 10, 7200, 600, 600) == ru.STALL_FAILED


def test_recover_exec_phase():
    """执行期崩溃恢复: moving -> 继续轮询(不重发); 到 dst -> 补做; 否则按停滞失败"""
    assert ru.recover_exec_phase(True, False, False) == ru.RECOVER_POLL
    assert ru.recover_exec_phase(False, True, False) == ru.RECOVER_RESUME
    assert ru.recover_exec_phase(False, False, True) == ru.RECOVER_RESUME
    assert ru.recover_exec_phase(False, False, False) == ru.RECOVER_STALLED


def test_resolve_physical_layer1():
    """物理位置解析(第 1 层): 作用域命中 -> dst; 未命中原样; 终态不解析"""
    job = _job(phase=ru.PHASE_ARMED)
    root = os.path.join(S, "Show")
    assert ru.resolve_physical(S, root, (job, )) == T  # 作用域命中 -> dst
    assert ru.resolve_physical(S, os.path.join(S, "Other"), (job, )) == S  # 未命中 -> 原样
    assert ru.resolve_physical(S, root, (_job(phase=ru.PHASE_DONE), )) == S  # 终态不解析
    assert ru.resolve_physical(S, root, (_job(phase=ru.PHASE_REWRITTEN), )) == T  # 收尾窗两相位都解析


def test_scope_hit_flat_does_not_cover_subdirs():
    """P7 回归: 平铺 job 的 scope_hit 只认「landing == scope」, 不覆盖同 save_path 子目录

    旧实现在 scope = save_path(平铺组的内容根)时, 把同目录别组的组键解析到 T ——
    job 结束后 _buckets 用 S 键查不到组, 退化为「仅选中成员」, 单成员 direct 误判
    (真机实测: 组① 被当单成员直搬, 数据走了却不建链接)。
    """
    flat = _job(phase=ru.PHASE_MOVING, scope=S, plan={"form": ru.FORM_FILE_LINKS})
    assert flat.scope_hit(S, S) is True  # 平铺组自己的成员(内容根 == save_path)
    assert flat.scope_hit(S, os.path.join(S, "Show")) is False  # 同 save_path 子目录里的别组
    assert flat.scope_covers_dir is False
    # 直搬: 无别名 => 作用域恒不命中(真机: 组② 直搬 scope=恶女目录, 曾把同目录组① 解析走)
    direct = _job(phase=ru.PHASE_MOVING, scope=os.path.join(S, "Show"), alias_kind="", plan={"form": ru.FORM_DIRECT})
    assert direct.scope_hit(S, os.path.join(S, "Show")) is False
    # 目录别名: 作用域覆盖整目录(含子目录), 与旧行为一致
    dir_job = _job(phase=ru.PHASE_ARMED, plan={"form": ru.FORM_DIR_ALIAS})
    assert dir_job.scope_hit(S, os.path.join(S, "Show")) is True
    assert dir_job.scope_covers_dir is True


def test_job_dict_roundtrip():
    """job 落账 roundtrip + 坏条目跳过(不炸); move_issued 必须随账往返(重启恢复判据消费)"""
    job = _job(plan={"form": "file_links", "link_kind": "hardlink", "files": [["Show/e00.mkv", 7]]})
    back = ru.job_from_dict(ru.job_to_dict(job))
    assert back == job
    issued = _job(move_issued=True)
    assert ru.job_from_dict(ru.job_to_dict(issued)).move_issued is True, "「已下发」不能丢(否则重启会重发)"
    assert ru.job_from_dict({"job_id": "x"}).move_issued is False, "老账无该位 -> 按未下发处理"
    assert ru.job_from_dict(None) is None
    assert ru.job_from_dict({"hashes": []}) is None
    assert ru.job_from_dict("x") is None
    assert ru.job_id_for("HA", T, S) == ru.job_id_for("HA", T, S)
    assert ru.job_id_for("HA", T, S) != ru.job_id_for("HB", T, S)


def test_job_from_dict_type_error_and_legacy_phase_map():
    """落账坏类型 -> None; 旧账相位前向映射(S4 迁移口径): removing/removed/finalizing ->
    armed(非终态不丢现场); 终态/新相位/未知值原样; 未知值不炸(推进分派静默跳过)"""
    assert ru.job_from_dict({"job_id": "x", "hashes": 5}) is None
    for legacy, expect in (("removing", "armed"), ("removed", "armed"), ("finalizing", "armed")):
        assert ru.job_from_dict({"job_id": "x", "phase": legacy}).phase == expect, legacy
    assert ru.job_from_dict({"job_id": "x", "phase": "done"}).phase == "done"
    assert ru.job_from_dict({"job_id": "x", "phase": "armed"}).phase == "armed"
    assert ru.job_from_dict({"job_id": "x", "phase": "rewritten"}).phase == "rewritten"
    assert ru.job_from_dict({"job_id": "x", "phase": "moving"}).phase == "moving"
    assert ru.job_from_dict({"job_id": "x", "phase": "whatever-unknown"}).phase == "whatever-unknown"
    assert ru.job_from_dict({"job_id": "x"}).phase == ru.PHASE_MOVING  # 缺相位按 moving
    # 新对账兜底: 别名丢失 + qB 在 -> rebuild(与 seed_state/finalize_timeout 解耦, 旧输入已退役)
    job = _job()
    assert ru.reconcile(job, alias_present=False, qb_up=True) == ru.ACT_REBUILD
    assert ru.reconcile(job, alias_present=True, qb_up=False) == ru.ACT_WAIT


# ---------------------------------------------------------------- W8(R32) S5a 守阵追加


def test_norm_backslash_bridge_and_within_guard():
    """_norm 反斜杠归一桥: qB 回报反斜杠与正斜杠 scope 混合比较恒等(Windows 生产口径); 空 scope 恒不命中"""
    assert ru._norm("R:\\Download\\Testing") == ru._norm("R:/Download/Testing")
    dir_job = _job(alias_kind="dir", plan={"form": ru.FORM_DIR_ALIAS})
    # 目录别名作用域含子路径: 归一桥断链(反斜杠形态漏折回)会让 _within 前缀比较恒 miss
    assert dir_job.scope_hit(S, os.path.join(S, "Show", "sub", "deep")) is True
    assert ru._within("", "R:/anywhere") is False


def test_join_slash_normalization_faces():
    """_join 拼接契约: 反斜杠归一/尾斜杠剥离/相对段首尾斜杠剥离(平台无关字符串契约)"""
    assert ru._join("R:\\Download", "Show") == "R:/Download/Show"
    assert ru._join("R:/Download/", "Show") == "R:/Download/Show"
    assert ru._join("R:/BoX", "Show") == "R:/BoX/Show"  # 剥字符集只含 / 与大写 X, 尾 X 不得多剥
    assert ru._join("R:/D", "XSub") == "R:/D/XSub"  # 名首 X 不得被剥
    assert ru._join("R:/D", "/lead/") == "R:/D/lead"


def test_plan_long_path_exact_boundaries():
    """长路径校正恰 260 边界(实测 259 可建、260 起 WinError 1314): 恰达上限即校正, 不放过"""
    save = "R:/D/" + "a" * 200  # len 205
    # 内容根恰 260(=limit)且文件更长 -> 目录别名也建不出来 -> 拒绝
    files = tuple(f"{'b' * 54}/e{i:02d}" for i in range(3))  # 文件路径 264
    p = ru.plan(
        save,
        files,
        8,
        2000,
        content_root_exclusive=True,
        file_link_kind="symlink",
        dir_link_kind="junction",
        link_path_limit=260
    )
    assert p.form == ru.FORM_REJECT and "内容根路径过长" in p.reason, (p.form, p.reason)
    # 最长文件路径恰 260、内容根 256 < 260 -> 能力校正提议目录别名(需确认)
    files2 = tuple(f"{'b' * 50}/e{i:02d}" for i in range(3))  # 文件路径 205+1+54=260
    p = ru.plan(
        save,
        files2,
        8,
        2000,
        content_root_exclusive=True,
        file_link_kind="symlink",
        dir_link_kind="junction",
        link_path_limit=260
    )
    assert p.form == ru.FORM_DIR_ALIAS and p.needs_confirm and "路径过长" in p.reason, (p.form, p.reason)
    # 事实包 link_path_limit 必须透传进 plan(丢实参 -> 校正失效 -> 长路径逐文件链接误放行)
    facts = _ok_facts(
        save_path=save,
        files=tuple((f, 100) for f in files2),
        content_root_exclusive=True,
        file_link_kind="symlink",
        dir_link_kind="junction",
        link_path_limit=260,
    )
    item = ru.evaluate_group(facts)
    assert item["cls"] == ru.CLS_CONFIRM and item["form"] == ru.FORM_DIR_ALIAS, item


def test_same_volume_proof_tolerance_band():
    """同卷证明容差带: 差 1.5GiB(超出 1GiB 绝对带)不得证明同盘; 恰等容差边界仍同盘"""
    gib = 1 << 30
    local = 10 * gib  # 2% 相对容差(204MiB) < 1GiB -> 绝对带生效
    assert ru.same_volume_proof(local + int(1.5 * gib), local) is False  # 容差不得翻倍
    assert ru.same_volume_proof(local + gib, local) is True  # 恰等边界(<=)


def test_job_dict_full_roundtrip_values():
    """落账往返保值: 非默认字段全量往返(断键/丢实参=重启恢复丢字段, resume_hashes 断链=成员滞留); 坏 plan 形状拒收"""
    job = _job(
        reason="测试原因",
        created_at=3.5,
        armed_at=1.5,
        updated_at=2.5,
        resume_hashes=("HA", "HB"),
        attempts=2,
        last_error="boom",
        tag_on=True
    )
    back = ru.job_from_dict(ru.job_to_dict(job))
    assert back == job
    assert back.resume_hashes == ("HA", "HB") and back.attempts == 2 and back.last_error == "boom"
    assert back.created_at == 3.5 and back.tag_on is True, "设置时间源/曾加标签账不得在重启恢复时丢失"
    assert ru.job_from_dict({"job_id": "x", "plan": "not-a-dict"}).plan is None  # 防御面: 非 dict plan 不透传


def test_scope_hit_src_guard_and_resolve_order():
    """src 不匹配恒不命中(嵌套 src 别组不得被误纳); 解析按登记序跳过终态不中断; 收尾去重; 历史账兜底链"""
    job = _job(plan={"form": ru.FORM_DIR_ALIAS})
    assert job.scope_hit("R:/elsewhere", "R:/elsewhere/Show") is False
    # 解析序: 终态 job 在前只跳过不中断, 后面的活动 job 仍要查到
    done = _job(job_id="d", phase=ru.PHASE_DONE, dst="T:/one")
    active = _job(job_id="a", phase=ru.PHASE_ARMED, dst="T:/two")
    root = os.path.join(S, "Show")
    assert ru.resolve_physical(S, root, (done, active)) == "T:/two"
    # 历史账(无 alias_kind)靠 plan.form 兜底链解析形态
    legacy_dir = ru.RelocateJob(
        job_id="lg",
        hashes=("HA", ),
        mover="HA",
        src=S,
        dst=T,
        scope=root,
        alias_kind="",
        plan={"form": ru.FORM_DIR_ALIAS}
    )
    assert legacy_dir.scope_hit(S, root) is True
    legacy_file = ru.RelocateJob(
        job_id="lf",
        hashes=("HA", ),
        mover="HA",
        src=S,
        dst=T,
        scope=root,
        alias_kind="",
        plan={"form": ru.FORM_FILE_LINKS}
    )
    assert legacy_file.scope_hit(S, root) is True  # 逐文件: landing 恰等于 scope


def test_stall_verdict_grow_and_late_warn_branches():
    """停滞 WARN 侧支: 体积增长超时转 warn; 非 moving 非增长超时(未到 stall_timeout)也 warn; 恰等边界算超"""
    assert ru.stall_verdict(True, False, 7200, 7200, 600, 0) == ru.STALL_WARN  # 增长恰等边界
    assert ru.stall_verdict(True, False, 8000, 7200, 600, 0) == ru.STALL_WARN
    assert ru.stall_verdict(False, False, 8000, 7200, 600, 100) == ru.STALL_WARN  # 末支 warn
    assert ru.stall_verdict(False, False, 7200, 7200, 600, 100) == ru.STALL_WARN  # 末支恰等边界
    assert ru.stall_verdict(False, True, 7200, 7200, 600, 0) == ru.STALL_WARN  # moving 恰等边界


def test_plan_layout_filter_and_last_mile_contract():
    """空名条目必须过滤(布局/计数不塌); 末段逐文件链接的 link_kind 契约; 缺省实参即契约"""
    p = ru.plan(S, ("", "Show/e00.mkv", "Show/e01.mkv"), 8, 2000, file_link_kind="hardlink", dir_link_kind="junction")
    assert p.flat is False and p.content_root == S + "/Show" and p.file_count == 2
    assert ru.layout_of(S, ("", "Show/a.mkv")) == (False, "Show")
    assert ru.layout_of(S, ("/a.mkv", )) == (True, "")
    # 末段(平铺/不专属超阈值逐文件链接): link_kind 必须带上(执行期建链形态消费)
    p = ru.plan(
        S,
        tuple(f"e{i:02d}.mkv" for i in range(9)),
        8,
        2000,
        content_root_exclusive=False,
        file_link_kind="hardlink",
        dir_link_kind="junction"
    )
    assert p.form == ru.FORM_FILE_LINKS and p.link_kind == "hardlink" and p.link_count == 9
    # 缺省 threshold=8 / hard_max=2000 / 兜底文案(不出现占位符)
    p = ru.plan(
        S,
        _files(8),
        multi_member=True,
        content_root_exclusive=True,
        file_link_kind="hardlink",
        dir_link_kind="junction"
    )
    assert p.form == ru.FORM_DIR_ALIAS
    p = ru.plan(S, _files(2001), 8, multi_member=True, content_root_exclusive=False, file_link_kind="hardlink")
    assert p.form == ru.FORM_REJECT and "2000" in p.reason
    # 兜底文案在「能力校正提议」分支: 文件级不可建但目录别名可行 -> 提议文案带兜底原因
    p = ru.plan(S, _files(3), 8, 2000, content_root_exclusive=True, file_link_kind=None, dir_link_kind="junction")
    assert p.form == ru.FORM_DIR_ALIAS and "文件级链接不可建 ——" in p.reason and "XXXX" not in p.reason
    # 两个能力探测错误都缺省(拒绝分支): 不出现占位符
    p = ru.plan(S, _files(3), 8, 2000, file_link_kind=None, dir_link_kind=None)
    assert p.form == ru.FORM_REJECT and "XXXX" not in p.reason
    # 空表 reject: link_count=0(回执契约)
    assert ru.plan(S, (), 8, 2000).link_count == 0


def test_plan_dir_link_error_long_path_text():
    """目录别名过长且已有探测错误: 前段错误拼进拒绝文案(不炸/不丢/不伪空格/无占位符)"""
    save = "R:/D/" + "a" * 200
    files = tuple(f"{'b' * 54}/e{i:02d}" for i in range(3))  # 内容根恰 260
    p = ru.plan(
        save,
        files,
        8,
        2000,
        content_root_exclusive=True,
        file_link_kind=None,
        file_link_error="文件级不可建",
        dir_link_kind="junction",
        dir_link_error="未探测到可用形态",
        link_path_limit=260
    )
    assert p.form == ru.FORM_REJECT
    assert "未探测到可用形态 内容根路径过长" in p.reason, p.reason
    p = ru.plan(
        save,
        files,
        8,
        2000,
        content_root_exclusive=True,
        file_link_kind=None,
        file_link_error="文件级不可建",
        dir_link_kind="junction",
        dir_link_error="",
        link_path_limit=260
    )
    assert p.form == ru.FORM_REJECT and "文件级不可建; 内容根路径过长" in p.reason and "XXXX" not in p.reason
    # 目录不专属: why 列表不得混入伪条目
    p = ru.plan(
        save,
        files,
        8,
        2000,
        content_root_exclusive=False,
        file_link_kind=None,
        file_link_error="文件级不可建",
        dir_link_kind="junction",
        link_path_limit=260
    )
    assert p.form == ru.FORM_REJECT and "XXXX" not in p.reason


def test_evaluate_group_receipt_contract_keys():
    """回执契约键面: 幂等/主回执/添加预检三张 dict 的键名与取值即前端契约(改名/丢键/值翻转都算断)"""
    keys = {
        "hashes", "mover", "name", "save_path", "target", "file_count", "form", "alias_kind", "link_count",
        "needs_confirm", "cls", "reasons", "notes", "target_free", "same_volume"
    }
    item = ru.evaluate_group(_ok_facts(target=S))  # 幂等分支
    assert set(item) == keys, set(item) ^ keys
    assert item["file_count"] == 2 and item["link_count"] == 0
    assert item["needs_confirm"] is False and item["alias_kind"] is None and item["cls"] == ru.CLS_OK
    item = ru.evaluate_group(_ok_facts(files=_files(9), same_volume=False, target_free=1234))
    assert set(item) == keys, set(item) ^ keys
    assert item["form"] == ru.FORM_DIR_ALIAS and item["needs_confirm"] is True
    assert item["alias_kind"] == "junction" and item["link_count"] == 1
    assert item["cls"] == ru.CLS_CONFIRM and item["reasons"][0]["gate"] == "form"
    assert item["reasons"][0]["cls"] == ru.CLS_CONFIRM
    assert "提议目录别名" in item["reasons"][0]["text"]  # confirm 文案不丢
    assert item["target_free"] == 1234 and item["same_volume"] is False
    assert item["hashes"] == ["HA", "HB"] and item["mover"] == "HA" and item["name"] == "Show"
    assert item["save_path"] == S and item["target"] == T
    assert any("目标卷剩余 1234 字节" in n for n in item["notes"])
    # 添加预检: 基座键随分支透传
    r = ru.evaluate_add(
        ru.AddFacts(save_path=S, name="Show", jobs=(_file_job(phase=ru.PHASE_MOVED), ), target_free=5000)
    )
    assert r["save_path"] == S and r["name"] == "Show" and r["volume_free"] is None  # 非 dir 分支不透卷剩余
    assert r["notes"] == ["落在原盘真实目录, 与别名作用域无交叉"]
    r = ru.evaluate_add(ru.AddFacts(save_path=S, name="Whatever", jobs=(_dir_job(phase=ru.PHASE_REWRITTEN), )))
    assert r["actual_path"] and r["actual_path"].replace("\\", "/").startswith(T)  # 收尾窗 dir 分支给实际落点
    r = ru.evaluate_add(
        ru.AddFacts(
            save_path=S,
            name="Show",
            landing_is_link=True,
            landing_link_kind="symlink",
            landing_link_target="D:/elsewhere",
            target_free=777
        )
    )
    assert r["actual_path"] == "D:/elsewhere" and r["volume_free"] == 777


def test_evaluate_group_text_faces_representatives():
    """文案代表面(全量文案留池): 空间/未完成/硬上限闸门的判定性片段 + 恰等边界不误拒"""
    item = ru.evaluate_group(_ok_facts(target_free=50, same_volume=False))
    assert item["reasons"][0]["cls"] == ru.CLS_BLOCKED  # blocked 侧 cls 不得塌 None
    text = " | ".join(r["text"] for r in item["reasons"] if r["gate"] == "space")
    assert "空间不足" in text and "50" in text, text
    item = ru.evaluate_group(_ok_facts(target_free=200))  # 剩余恰等所需(2x100) -> 不误拒
    assert item["cls"] == ru.CLS_OK, item["reasons"]
    item = ru.evaluate_group(_ok_facts(target_free=None, same_volume=None))
    assert all("目标卷剩余" not in n for n in item["notes"])  # 不可判定时不伪字节文案
    sp_text = " | ".join(r["text"] for r in item["reasons"] if r["gate"] == "space")
    assert sp_text.startswith("目标卷剩余空间不可判定"), sp_text
    item = ru.evaluate_group(_ok_facts(progresses=(1.0, 0.5)))
    text = " | ".join(r["text"] for r in item["reasons"] if r["gate"] == "incomplete")
    assert "尚未完成" in text and "辅种组 (未完成成员的进度" in text, text
    # hard_max 拒绝: 配置上限与目录别名具体错误都进文案
    item = ru.evaluate_group(
        _ok_facts(files=_files(2001), hard_max=1500, content_root_exclusive=False, file_link_kind="hardlink")
    )
    text = " | ".join(r["text"] for r in item["reasons"] if r["gate"] == "form")
    assert "1500" in text, text
    item = ru.evaluate_group(
        _ok_facts(
            files=_files(2001),
            content_root_exclusive=True,
            file_link_kind="hardlink",
            dir_link_kind=None,
            dir_link_error="boom 提权失败"
        )
    )
    text = " | ".join(r["text"] for r in item["reasons"] if r["gate"] == "form")
    assert "boom 提权失败" in text, text


def test_evaluate_add_flow_faces():
    """添加预检流面: 终态在前不中断收尾窗检查; 作用域外落点不进分支; rel 切片各形态(尾斜杠/反斜杠/尾x/名首x/空名)"""
    done = _dir_job(phase=ru.PHASE_DONE)
    rewritten = _dir_job(phase=ru.PHASE_REWRITTEN)
    r = ru.evaluate_add(ru.AddFacts(save_path=S, name="Show", jobs=(done, rewritten)))
    assert r["reasons"][0]["gate"] == "finalize_window"
    r = ru.evaluate_add(ru.AddFacts(save_path=S, name="Other", jobs=(_dir_job(), )))
    assert r["cls"] == ru.CLS_CONFIRM and r["reasons"][0]["gate"] == "finalize_window"  # D16: 账面记旧根即依赖
    r = ru.evaluate_add(ru.AddFacts(save_path=S, name="Other", jobs=(_dir_job(phase=ru.PHASE_MOVED), )))
    assert r["cls"] == ru.CLS_OK  # 前段相位 + 落点不在作用域内 -> 不进分支
    for sp in (S + "/", "R:\\Download\\Testing"):
        r = ru.evaluate_add(ru.AddFacts(save_path=sp, name="Show", jobs=(_dir_job(), ), target_free=5000))
        assert r["cls"] == ru.CLS_CONFIRM and r["actual_path"] == T + "/Show", (sp, r["actual_path"])
    root_job = ru.RelocateJob(
        job_id="jx",
        hashes=("HA", "HB"),
        mover="HA",
        src="R:/BoX",
        dst=T,
        scope="R:/BoX",
        alias_kind="dir",
        phase=ru.PHASE_ARMED
    )
    r = ru.evaluate_add(ru.AddFacts(save_path="R:/BoX", name="Show", jobs=(root_job, )))
    assert r["actual_path"] == T + "/Show" and r["notes"] == ["目标卷剩余不可判定"]
    r = ru.evaluate_add(ru.AddFacts(save_path="R:/BoX", name="XSub", jobs=(root_job, )))
    assert r["actual_path"] == T + "/XSub"  # 名首 X 不得被剥(剥字符集只含大写 X 与 /)
    scope_all = ru.RelocateJob(
        job_id="ja", hashes=("HA", "HB"), mover="HA", src=S, dst=T, scope=S, alias_kind="dir", phase=ru.PHASE_ARMED
    )
    r = ru.evaluate_add(ru.AddFacts(save_path=S, name="", jobs=(scope_all, )))
    assert r["actual_path"] == T  # 空名: rel 为空 -> actual = dst(不伪段)


def test_within_empty_scope_guard_via_norm_empty(monkeypatch):
    """(T2b)空 scope 守卫(98->99): 归一化器退化为返回空串时(现实 normpath 恒返回'.',
    守卫属防御弧, 经 _norm 替身直驱)空 scope 永不匹配; 非空 scope 语义不变"""
    real_norm = ru._norm
    monkeypatch.setattr(ru, "_norm", lambda p: "" if p == "" else real_norm(p))
    assert ru._within("", "R:/any/path") is False
    assert ru._within("", "") is False
    assert ru._within("R:/scope", "R:/scope/a") is True
    assert ru._within("R:/scope", "R:/other") is False


# ---------------------------------------------------------------- S3 新链对账(计划 26-11-05-0808 §3.2「对账与生命周期」行)


def test_ensure_daemon_action_three_way():
    """ACT_ENSURE_DAEMON 判据三分(死/活/心跳过期收口成 daemon_stale 一位):
    pending 空 -> wait(无事不拉); daemon 健康 -> wait(至多一个 watcher, D12);
    pending 非空 + stale -> ensure_daemon(重拉 recycle_daemon, 独立于 reconcile 旧表)"""
    assert ru.ensure_daemon_action(pending=0, daemon_stale=True) == ru.ACT_WAIT
    assert ru.ensure_daemon_action(pending=3, daemon_stale=False) == ru.ACT_WAIT
    assert ru.ensure_daemon_action(pending=0, daemon_stale=False) == ru.ACT_WAIT
    assert ru.ensure_daemon_action(pending=2, daemon_stale=True) == ru.ACT_ENSURE_DAEMON
    # 新动作集: reconcile 新表(wait/rebuild/verify)不含 ensure_daemon —— 判据独立成单点
    job = _dir_job()
    assert ru.reconcile(job, alias_present=True, qb_up=True, all_at_dst=False) == ru.ACT_WAIT
    assert ru.ACT_ENSURE_DAEMON not in {ru.ACT_WAIT, ru.ACT_REBUILD, ru.ACT_VERIFY}
