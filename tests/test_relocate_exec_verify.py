"""test_relocate_exec_verify 测试计划: S4 后半核验+删链门 + D16 删种拦截(计划 26-11-05-0808
§3.1「qB 重启 → 主循环核验」段 / §2.3 N5 教训 / §06 D16)

## 测试计划(每个测试函数一条)
### 纯函数层(relocate_units)
- test_under_alias_root_dual_criteria: 等值 OR 前缀双判据(N5: save_path 恰等于根必须命中);
  前缀同串兄弟目录不误伤; 门外不命中; 空路径 None
- test_chain_gate_hits_scan: 门外共享者零依赖 / 等值+前缀命中混合 / 空 save_path 跳过
- test_alias_roots_of_filters: 终态 / direct(无别名) / 无链接记录的 job 不进拦截根集;
  R3 条目随带形态与链接账(四元组单点产出, 计划 26-11-13-0448 §03 R3)
### 核验三分(_step_verify)
- test_step_verify_all_pass_zero_deps_finalizes: 全员 save_path == dst + 删链门零依赖 →
  在线删别名 + 终态 done + journal 落 done + alias_paths 清空
- test_step_verify_member_not_at_dst_hangs_and_replays: 一成员仍在旧路径 → 不终态不判 failed,
  journal settled 记录被清回 pending(相位翻 armed, verify_replays 计 1), job 镜像回 armed
- test_step_verify_partial_members_fail: 部分成员不过 → 悬挂且告警文案点名未过成员
- test_step_verify_member_gone_hangs: 成员已不在客户端 → 同悬挂(良性态, FAILED_GONE 已退役)
- test_step_verify_replay_only_once: 重放一轮后仍不过 → 不再清账(rewrites 保持 settled),
  job 停 rewritten + reason=verify_failed(防无限改写循环)
### S4 收尾守卫(计划 26-11-20-0434 R1: 悬挂不再被纳入成员触发)
- test_verify_hang_included_inflight_waits_without_replay: 纳入成员改写在途(无账 + 在
  spec.members)—— 核验按 WAIT: 不清账不重放相位不抖, 不写 verify_failed(红绿主测)
- test_verify_hang_included_orphan_waits_without_replay: 纳入成员改写从未落账(T3 遗留:
  无账 + 不在 spec.members)—— 同按 WAIT 挂起不清账不判失败, 告警带人工出路(收缩自愈)
- test_verify_hang_inflight_spec_missing_conservative_wait: spec 不可读 —— 无账成员保守按
  在途 WAIT(不误报孤儿文案), 不清账
- test_verify_hang_inflight_after_gate_exhausted_stays_wait: 重放闸已用尽后纳入成员才变坏
  —— 同按 WAIT, 不得把 verify_failed 落到纳入成员头上(R1 永久悬挂面)
- test_verify_hang_mixed_recorded_and_inflight_keeps_replay: 混批(有账真失败 + 无账在途)
  —— 既有重放面照走(有账成员语义不变)
- test_verify_hang_inflight_wait_warning_deduped_per_text: WAIT 支告警按文本 rt 去重
  (同参重入只 WARNING 一次, 不逐拍刷屏)
- test_rewrite_cover_hybrid_v2_ledger_key_resolves_and_replays: v2/hybrid 键向(评审 minor
  修)—— 改写账按 hash_v2 记键 + qB hash 给 hash_v1: 成员判 recorded(候选账键序解析),
  混批真失败走既有重放面且 reset 只清 settled(failed 记录不动)
### 删链门(_step_verify 依赖扫描)
- test_step_verify_deps_block_then_release: 门外共享者 save_path 恰等于旧根(N5 形态)→
  reason=chain_deps 别名不删; 依赖消失后重跑 → 收尾完成
- test_step_verify_deps_prefix_hit: 前缀命中(组外种子落旧根之下)同为依赖, 别名不删
### 删链门重锚(R7, 计划 26-11-07-1300 D9)
- test_chain_gate_deps_scope_anchor_and_member_exempt: 本组成员豁免(嵌套放行形态 dst ⊆ scope
  不再自锁)/ 组外 scope 内保守计数(等值+前缀双向)/ scope 外不计(旧根兄弟停车假依赖修)/
  旧账 scope 缺失回落 job.src
### 删链门 R2 形态感知 verdict(计划 26-11-13-0448 §03 R2, D4)
- test_chain_gate_deps_file_kind_intersection_verdict: 文件级 job verdict 换「文件清单 x
  alias_paths 交集」—— 相交(同名撞链接路径/等值面平铺同名 E3 形态) = 依赖 / 不相交
  (组外异名, 等值面+前缀面候选) = 豁免(误拦1 修正面) / 不可得(取数抛错/空清单) =
  保守计依赖(宁拦勿漏 E8) / 目录级命中即依赖原样 / direct 自有面短路(0711b) / 本组 hash
  豁免不变
### 删链门 0535 祖先方向候选格(issue 26-11-13-0535, 计划 26-11-15-2340 刀2)
- test_chain_gate_deps_ancestor_savepath_grid: 组外种子 save_path 为 job.src 严格祖先且
  内容根恰覆盖旧根 -> 计入依赖(文件级过 file_alias_intersects 精判 / 目录级命中即依赖 /
  祖先不覆盖旧根或清单不可得 -> 不命中, 候选面不猜)
### direct 自有面短路(0711 修法 b, issue 26-11-13-0711, 计划 26-11-15-2340 刀2)
- test_step_verify_direct_no_alias_finalizes: direct 收尾窗组外落点(前缀/等值)不再悬挂
  chain_deps, 核验过即收尾(direct 无别名无链可删); 对照: dir 形态同落点仍悬挂
### 删链门反馈面文案分型(R5(2), 计划 26-11-13-0448 §03 R5)
- test_chain_deps_text_form_aware_wording: 文件级 job 文案随 R2 语义改措辞「N 个种子的文件
  与别名链接重叠」+ 出路带立即收尾加速器(依赖清零即自动收尾); 目录级/direct 保留现行
  save_path 面措辞(scope 前缀 + src 等值), 不带立即收尾句
### D16 删种拦截(qbapi.torrents_delete 单点, 两条删除路径共用判据)
- test_qbapi_delete_guard_blocks_delete_files: 目录别名形态(junction 根=src)——等值与前缀
  成员都拦(整批不发 qB, R5(1) 成员文案: 收缩自愈出路); delete_files=False(纯删除)放行
- test_qbapi_delete_guard_message_member_vs_out_group: R5(1) D16 文案按拦截对象分型 ——
  成员出路 = 仅删种子 -> 组账自动收缩自愈 + 立即收尾; 组外撞根出路 = 迁出旧根或仅删种子
  (其本身即删链门依赖, 「等收尾」循环句退场) + 立即收尾降为次选(加速改写窗);
  混批分型各一句; 成员集缺省空 = 全部按组外文案分型(替身兼容面)
- test_qbapi_delete_guard_file_links_form: 文件级形态(成员/同名撞链接)相交拦(文件级
  symlink deleteFiles 跟随直删; R3 后放行面单测在 file_kind_intersection 行)
- test_qbapi_delete_guard_allows_outside_and_unregistered: 门外种子放行; 无活动别名登记放行
- test_qbapi_delete_guard_file_kind_intersection_verdict: R3 文件级 verdict(计划
  26-11-13-0448 §03 R3)—— 不相交(组外异名带文件)放行 / 相交(成员/同名撞链接根)拦 /
  不可得(取数抛错/空清单)保守拦 / 目录级全量拦原样 / 多根重叠两序仍拦(file 豁免根
  不短路 dir 全量拦, 评审轮 1 修 1)(S5: 登记旧形(str)兼容面随派生查询退役 —— 只产四元组)
- test_qbapi_delete_guard_allows_probe_tagged_seeds: 探测种子(tag 含 TAG_PROBE)落在活动别名
  根下也放行(评审 #5, 自造探针非组成员数据; 拦截会让探测清理 deleteFiles 恒失败)/ 普通种子
  同根仍拦
- test_qbapi_delete_guard_ancestor_savepath_grid: 0535 祖先方向候选格 D16 半边 —— 组外
  种子 save_path 为登记根严格祖先且内容根恰覆盖 -> 带文件删除拦(文件级相交/目录级即拦/
  异名不相交精判放行/清单不可得该格不命中候选面不猜/祖先不覆盖不拦), 候选面单点复用
  chain_gate_hits
### WebUI 删除命令面(第二条路径, 经命令队列全链)
- test_webui_delete_blocked_receipt_single_and_group: delete_torrent / delete_group 撞拦截 →
  error 回执带解法文案(R5(1) 成员出路句: 仅删种子 + 组账收缩)+ qB 客户端未收到 delete;
  纯删除照常发

覆盖率缺口清偿(26-11-07, test.full 99.31% -> 99.5% 闸):
- test_webui_delete_blocked_receipt_bulk_and_no_cmd_id: 批量删除拦截 error 回执 + 单发/组发无
  cmd_id 静默回执(拦截不依赖结果页)
- test_verify_hang_unchanged_state_is_debug_only: 悬挂同参重放只落 DEBUG(不重复清账/刷警告)
- test_qb_side_check_self_failure_is_skipped: qB 侧自检自身炸 => skipped 不挡武装
"""

import types
from dataclasses import replace

import pytest

from auto_qb.core.modules import relocate_units as ru
from auto_qb.core.qbapi import DeleteBlockedError, QbApi
from auto_qb.infra import relocate_journal as rj

from helpers import FakeClient, capture_logs
from relocate_exec_support import FakeRelocateQueries, _bare_mod, _job

# ---------------------------------------------------------------- 纯函数层


def test_under_alias_root_dual_criteria():
    """等值 OR 前缀双判据(N5): 恰等于根的 save_path 必须命中, 纯前缀判据会漏"""
    root = r"R:\media"
    norm_root = ru._norm(root)  # 归一形按宿主平台折叠(Win 折小写 / POSIX 恒等), 断言不绑平台
    assert ru.under_alias_root(r"R:\media", (root, )) == norm_root  # 等值(N5 漏拦形态)
    assert ru.under_alias_root(r"R:\media\sub", (root, )) == norm_root  # 前缀
    assert ru.under_alias_root(r"R:\mediax", (root, )) is None  # 前缀同串兄弟目录: 不误伤
    assert ru.under_alias_root(r"R:\other", (root, )) is None  # 门外
    assert ru.under_alias_root("", (root, )) is None  # 空路径不可判
    assert ru.under_alias_root(r"R:\media", ()) is None  # 无根


def test_chain_gate_hits_scan():
    """删链门扫描纯函数: 门外共享者零依赖 / 等值+前缀命中混合 / 空 save_path 跳过"""
    hits = ru.chain_gate_hits([r"R:\media", r"R:\media\g2", r"R:\elsewhere", "", r"R:\mediax"], r"R:\media")
    assert hits == (r"R:\media", r"R:\media\g2"), hits
    assert ru.chain_gate_hits([r"R:\elsewhere"], r"R:\media") == (), "门外共享者零依赖"


def test_alias_roots_of_filters():
    """活动别名根集只收「非终态 + 有别名形态 + 账上有链接记录」的 job; R3 条目随带形态与链接账"""
    jobs = [
        _job("j1", phase=ru.PHASE_ARMED, alias_kind="dir", alias_paths=("R:/src/l", )),
        _job("j2", phase=ru.PHASE_DONE, alias_kind="dir", alias_paths=("R:/x", )),  # 终态: 不拦
        _job("j3", phase=ru.PHASE_ARMED, alias_kind="", alias_paths=()),  # direct: 无别名
        _job("j4", phase=ru.PHASE_MOVING, alias_kind="file", alias_paths=()),  # 链接未建: 不拦
    ]
    assert ru.alias_roots_of(jobs) == (("R:/src", "j1", "dir", ("R:/src/l", )), ), ru.alias_roots_of(jobs)


# ---------------------------------------------------------------- 核验三分(_step_verify)


def _rec(h, save_path):
    return types.SimpleNamespace(hash=h, save_path=save_path, state="pausedUP")


def _rec_files(h, save_path, names=(), files_error=False):
    """带文件清单替身的记录(R2/R3 交集判据取数面): files(client) 回 canned 清单
    (name/size SimpleNamespace 形, 同 helpers._fake_file)或抛错(取数失败 -> 判据按不可得
    保守计依赖/拦)。log_repr 与生产 TorrentRecord 对齐(_file_map 失败日志引用它)。"""
    rec = types.SimpleNamespace(hash=h, save_path=save_path, state="pausedUP", log_repr=h)
    if files_error:

        def _boom(client):
            raise RuntimeError("files api down")

        rec.files = _boom
    else:
        rec.files = lambda client: [types.SimpleNamespace(name=n, size=1) for n in names]
    return rec


def _rewritten_env(tmp_path, members, *, extra=(), alias_paths=("R:/src/l", ), replays=0):
    """rewritten 相位 job + journal settled 账 + store 成员账(核验/删链门用例的公共底座)

    members/extra = [(hash, save_path)]; journal 预写全体 settled + 相位 rewritten
    (replays 可预置重放计数, 供「重放闸已用尽」用例), spec 省略(_step_verify 不读 spec)。
    返回 (mod, job, rt, removed_删链spy)。
    """
    by_hash = {}
    for h, sp in list(members) + list(extra):
        by_hash[h] = _rec(h, sp)
    mod = _bare_mod(store=types.SimpleNamespace(by_hash=by_hash), data_dir=str(tmp_path))
    rewrites = {h: {"status": "rewritten", "ts": 1.0} for h, _sp in members}
    body = {"phase": ru.PHASE_REWRITTEN, "rewrites": rewrites, "ts": 1.0}
    if replays:
        body[rj.VERIFY_REPLAYS_KEY] = replays
    rj.write_journal(str(tmp_path), "j1", body)
    job = _job(
        "j1",
        phase=ru.PHASE_REWRITTEN,
        hashes=tuple(h for h, _sp in members),
        alias_paths=alias_paths,
        alias_kind="dir"
    )
    mod.register_job(job)
    removed = []
    mod._remove_links = lambda paths: (removed.extend(list(paths)), len(removed))[1]
    return mod, job, {}, removed


def test_step_verify_all_pass_zero_deps_finalizes(tmp_path):
    """全员到目标 + 零依赖 → 在线删别名 + 终态 done(journal 同步落 done, alias_paths 清空)"""
    mod, job, rt, removed = _rewritten_env(tmp_path, [("HA", "R:/dst"), ("HB", "R:/dst")])
    mod._step_verify(job, rt)
    saved = mod.get_job("j1")
    assert saved.phase == ru.PHASE_DONE and saved.reason == ru.REASON_FINALIZED, (saved.phase, saved.reason)
    assert saved.alias_paths == (), "终态 job 不再背别名账"
    assert removed == ["R:/src/l"], removed
    assert rj.read_journal(str(tmp_path), "j1")["phase"] == "done", "journal 必须同步落终态(daemon 据此退休)"


def test_step_verify_member_not_at_dst_hangs_and_replays(tmp_path):
    """一成员仍在旧路径 → 悬挂不判 failed; settled 账被清回 pending(相位翻 armed)+ job 镜像回 armed"""
    mod, job, rt, removed = _rewritten_env(tmp_path, [("HA", "R:/dst"), ("HB", "R:/src")])
    mod._step_verify(job, rt)
    saved = mod.get_job("j1")
    assert not saved.is_terminal and saved.phase == ru.PHASE_ARMED, (saved.phase, saved.reason)
    assert removed == [], "核验不过绝不删别名"
    j = rj.read_journal(str(tmp_path), "j1")
    assert j["phase"] == ru.PHASE_ARMED, j
    assert j[rj.VERIFY_REPLAYS_KEY] == 1, j
    assert all(
        m["status"] == rj.REWRITE_RESET_STATUS and m["prev_status"] == "rewritten" for m in j["rewrites"].values()
    ), j
    assert rj.pending_members({"members": [{"hash_v1": "HA"}, {"hash_v1": "HB"}]}, j["rewrites"]), \
        "清账后全体成员必须重回 pending"


def test_step_verify_partial_members_fail(tmp_path):
    """部分成员不过: 悬挂回 armed 请求重放, 告警文案点名未过成员(过者不入文案)"""
    mod, job, rt, _removed = _rewritten_env(tmp_path, [("HA", "R:/dst"), ("HB", "R:/src")])
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod._step_verify(job, rt)
    saved = mod.get_job("j1")
    assert saved.phase == ru.PHASE_ARMED and not saved.is_terminal, (saved.phase, saved.reason)
    warn = " ".join(cap.messages)
    assert "HB" in warn and "HA" not in warn, warn


def test_step_verify_member_gone_hangs(tmp_path):
    """成员已不在客户端 → 同悬挂(良性态; FAILED_GONE 已退役, 现场处置并入依赖扫描口径)"""
    mod, job, rt, removed = _rewritten_env(tmp_path, [("HA", "R:/dst"), ("HB", "R:/dst")], replays=1)
    del mod._ctx.store.by_hash["HB"]
    mod._step_verify(job, rt)
    saved = mod.get_job("j1")
    assert not saved.is_terminal and saved.phase == ru.PHASE_REWRITTEN, (saved.phase, saved.reason)
    assert saved.reason == ru.REASON_VERIFY_FAILED and "已不在客户端" in saved.last_error, saved.last_error
    assert removed == [], removed
    j = rj.read_journal(str(tmp_path), "j1")
    assert all(m["status"] == "rewritten" for m in j["rewrites"].values()), "重放闸已用尽: 账不被清"


def test_step_verify_replay_only_once(tmp_path):
    """重放一轮后仍不过 → 不再清账(rewrites 保持 settled), 停 rewritten + verify_failed(防无限改写循环)"""
    mod, job, rt, _removed = _rewritten_env(tmp_path, [("HA", "R:/dst"), ("HB", "R:/src")])
    mod._step_verify(job, rt)  # 第一轮: 清账 + 回 armed
    assert rj.verify_replays_of(str(tmp_path), "j1") == 1
    # 模拟 daemon 重放收口 + qB 再重启仍不过: rewrites 重回 settled, 相位翻 rewritten
    # (daemon 的 record_rewrites 整包合并, verify_replays 计数原样保留 —— 测试按同形写)
    rewrites = {h: {"status": "rewritten", "ts": 2.0} for h in ("HA", "HB")}
    rj.write_journal(
        str(tmp_path),
        "j1",
        {
            "phase": ru.PHASE_REWRITTEN,
            "rewrites": rewrites,
            "ts": 2.0,
            rj.VERIFY_REPLAYS_KEY: 1
        },
    )
    job2 = mod.get_job("j1")
    mod._set_job(replace(job2, phase=ru.PHASE_REWRITTEN, reason=""))
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod._step_verify(mod.get_job("j1"), rt)  # 第二轮核验不过
    j = rj.read_journal(str(tmp_path), "j1")
    assert j[rj.VERIFY_REPLAYS_KEY] == 1, "重放闸: 不得二次清账"
    assert all(m["status"] == "rewritten" for m in j["rewrites"].values()), j
    saved = mod.get_job("j1")
    assert saved.phase == ru.PHASE_REWRITTEN and saved.reason == ru.REASON_VERIFY_FAILED, (saved.phase, saved.reason)
    assert "维持悬挂" in " ".join(cap.messages), cap.messages


# ---------------------------------------------------------------- S4 收尾守卫(计划 26-11-20-0434 R1)
# 纳入成员(收尾窗纳入)的改写来源是 spec.members 不是 journal(journal 零写, 改写账唯一写者是
# daemon)—— daemon 改写前纳入成员恒无改写账记录。守卫按「有无改写账」分流: 有账成员走既有
# 重放/悬挂面(语义不变), 无账成员一律核验按 WAIT 良性挂起: 不清账重放(防重放闸被纳入成员
# 空耗 + 相位抖动)不写 verify_failed 反馈位(悬挂不再被纳入成员触发)。


def _included_env(tmp_path, *, in_spec=True, replays=0):
    """rewritten job + settled 原成员 HA(已到 dst) + 纳入成员 HF(无改写账, 仍在旧路径)底座

    in_spec=True 时 spec.members 含 HF(改写在途形态); False 时 spec 不含 HF(T3 纳入落账时
    spec 追加失败遗留的「改写从未落账」形态); spec 文件不给 = 不可读形态。replays 预置重放计数。
    """
    by_hash = {"HA": _rec("HA", "R:/dst"), "HF": _rec("HF", "R:/src")}
    mod = _bare_mod(store=types.SimpleNamespace(by_hash=by_hash), data_dir=str(tmp_path))
    body = {
        "phase": ru.PHASE_REWRITTEN,
        "rewrites": {
            "HA": {
                "status": "rewritten",
                "ts": 1.0
            }
        },
        "ts": 1.0,
    }
    if replays:
        body[rj.VERIFY_REPLAYS_KEY] = replays
    rj.write_journal(str(tmp_path), "j1", body)
    if in_spec is not None:
        members = [{"hash_v1": "HA", "hash_v2": ""}]
        if in_spec:
            members.append({"hash_v1": "HF", "hash_v2": ""})
        rj.write_spec(str(tmp_path), "j1", {"members": members})
    job = _job("j1", phase=ru.PHASE_REWRITTEN, hashes=("HA", "HF"), alias_paths=("R:/src/l", ), alias_kind="dir")
    mod.register_job(job)
    removed = []
    mod._remove_links = lambda paths: (removed.extend(list(paths)), len(removed))[1]
    return mod, job, {}, removed


def test_verify_hang_included_inflight_waits_without_replay(tmp_path):
    """纳入成员改写在途(无账 + 在 spec.members): 核验按 WAIT —— 不清账不重放相位不抖,
    不写 verify_failed(悬挂不再被纳入成员触发, R1 红绿主测; 修前此形触发放闸 + 相位回 armed)"""
    mod, job, rt, removed = _included_env(tmp_path, in_spec=True)
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod._step_verify(job, rt)
    j = rj.read_journal(str(tmp_path), "j1")
    assert rj.verify_replays_of(str(tmp_path), "j1") == 0, "纳入成员在途改写不得触发重放(reset_rewrites 不被调用)"
    assert j["rewrites"]["HA"]["status"] == "rewritten", "原成员 settled 账不得被清回 pending"
    saved = mod.get_job("j1")
    assert saved.phase == ru.PHASE_REWRITTEN and not saved.is_terminal, (saved.phase, saved.reason)
    assert saved.reason != ru.REASON_VERIFY_FAILED, saved.reason
    assert removed == [], "核验不过绝不删别名"
    assert "WAIT" in " ".join(cap.messages) or "等待" in " ".join(cap.messages), cap.messages


def test_verify_hang_included_orphan_waits_without_replay(tmp_path):
    """纳入成员改写从未落账(无账 + 不在 spec.members, T3 遗留): 同按 WAIT 挂起不清账不判失败,
    告警给人工出路(删除该种子组账收缩自愈)—— 机械面无法自愈也不得用重放闸空转"""
    mod, job, rt, _removed = _included_env(tmp_path, in_spec=False)
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod._step_verify(job, rt)
    assert rj.verify_replays_of(str(tmp_path), "j1") == 0, "改写从未落账的成员同样不得触发重放"
    saved = mod.get_job("j1")
    assert saved.phase == ru.PHASE_REWRITTEN and saved.reason != ru.REASON_VERIFY_FAILED, (saved.phase, saved.reason)
    warn = " ".join(cap.messages)
    assert "未落账" in warn or "未含" in warn, cap.messages
    assert "收缩" in warn, "告警必须带人工出路(组账收缩自愈)"


def test_verify_hang_inflight_spec_missing_conservative_wait(tmp_path):
    """spec 不可读(缺失/坏形): 无账成员无法证明孤儿 —— 保守按在途 WAIT(不误报孤儿文案), 不清账"""
    mod, job, rt, _removed = _included_env(tmp_path, in_spec=None)
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod._step_verify(job, rt)
    assert rj.verify_replays_of(str(tmp_path), "j1") == 0
    saved = mod.get_job("j1")
    assert saved.phase == ru.PHASE_REWRITTEN and saved.reason != ru.REASON_VERIFY_FAILED, (saved.phase, saved.reason)
    warn = " ".join(cap.messages)
    assert "未落账" not in warn, "spec 不可读不得断言孤儿(无法证明)"


def test_verify_hang_inflight_after_gate_exhausted_stays_wait(tmp_path):
    """重放闸已用尽(replays=1)后纳入成员才变坏: 同按 WAIT —— 不得把 verify_failed 反馈位
    落到纳入成员头上(R1 永久悬挂面; 修前此形被记 verify_failed 悬挂标签)"""
    mod, job, rt, _removed = _included_env(tmp_path, in_spec=True, replays=1)
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod._step_verify(job, rt)
    saved = mod.get_job("j1")
    assert saved.phase == ru.PHASE_REWRITTEN and saved.reason != ru.REASON_VERIFY_FAILED, (saved.phase, saved.reason)
    assert rj.verify_replays_of(str(tmp_path), "j1") == 1, "闸已用尽: 不得二次清账"
    assert "WAIT" in " ".join(cap.messages) or "等待" in " ".join(cap.messages), cap.messages


def test_verify_hang_mixed_recorded_and_inflight_keeps_replay(tmp_path):
    """混批(有账真失败成员 + 无账在途纳入成员): 既有重放面照走 —— 有账成员语义不变
    (重放为真失败成员服务, 在途成员无账不受 reset 影响, daemon 经 spec 照常接管)"""
    mod, _job, rt, _removed = _included_env(tmp_path, in_spec=True)
    mod._ctx.store.by_hash["HA"].save_path = "R:/src"  # HA 真失败: 改写落账却未回流
    with capture_logs("auto_qb.core.modules.relocate_mod"):
        mod._step_verify(mod.get_job("j1"), rt)
    assert rj.verify_replays_of(str(tmp_path), "j1") == 1, "有账成员未回流: 既有重放面照走"
    j = rj.read_journal(str(tmp_path), "j1")
    assert j["rewrites"]["HA"]["status"] == rj.REWRITE_RESET_STATUS, "真失败成员照常清回 pending"
    assert mod.get_job("j1").phase == ru.PHASE_ARMED, "重放期相位回 armed(既有语义)"


def test_verify_hang_inflight_wait_warning_deduped_per_text(tmp_path):
    """WAIT 支告警按文本去重(同参重入只 WARNING 一次, 不逐拍刷屏 —— 与既有 changed 门同纪律)"""
    mod, job, rt, _removed = _included_env(tmp_path, in_spec=True)
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap1:
        mod._step_verify(job, rt)
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap2:
        mod._step_verify(mod.get_job("j1"), rt)
    warn1 = [m for m in cap1.messages if "WAIT" in m or "等待" in m]
    warn2 = [m for m in cap2.messages if "WAIT" in m or "等待" in m]
    assert len(warn1) == 1, cap1.messages
    assert len(warn2) == 0, "同文本重入转 DEBUG 静默(不逐拍刷屏)"


def test_rewrite_cover_hybrid_v2_ledger_key_resolves_and_replays(tmp_path):
    """v2/hybrid 键向(评审 minor 修): 改写账按 hash_v2 记键、qB hash 给 hash_v1 —— 成员仍判
    recorded(候选账键序解析), 混批真失败走既有重放面且 reset 只清 settled(键映射错向不得
    把真失败 hybrid 成员误判 WAIT 支、重放面不触发)"""
    hybrid_v1, hybrid_v2 = "V" * 40, "W" * 40
    by_hash = {
        "HA": _rec("HA", "R:/src"),  # 真失败: 有账(settled)未回流
        hybrid_v1: _rec(hybrid_v1, "R:/src"),  # hybrid 真失败: 账按 hash_v2 记键(夹具形态)
        "HP": _rec("HP", "R:/src"),  # 有账但未收口(failed): reset 不得动(只清 settled)
        "HF": _rec("HF", "R:/dst"),  # 在途纳入成员(无账在 spec): 已到 dst 不进 bad
    }
    mod = _bare_mod(store=types.SimpleNamespace(by_hash=by_hash), data_dir=str(tmp_path))
    rj.write_journal(
        str(tmp_path),
        "j1",
        {
            "phase": ru.PHASE_REWRITTEN,
            "rewrites":
                {
                    "HA": {
                        "status": "rewritten",
                        "ts": 1.0
                    },
                    hybrid_v2: {
                        "status": "rewritten",
                        "ts": 1.0
                    },
                    "HP": {
                        "status": "failed",
                        "ts": 1.0
                    },
                },
            "ts": 1.0,
        },
    )
    rj.write_spec(
        str(tmp_path),
        "j1",
        {
            "members":
                [
                    {
                        "hash_v1": "HA",
                        "hash_v2": ""
                    },
                    {
                        "hash_v1": hybrid_v1,
                        "hash_v2": hybrid_v2
                    },
                    {
                        "hash_v1": "HP",
                        "hash_v2": ""
                    },
                    {
                        "hash_v1": "HF",
                        "hash_v2": ""
                    },
                ]
        },
    )
    job = _job(
        "j1",
        phase=ru.PHASE_REWRITTEN,
        hashes=("HA", hybrid_v1, "HP", "HF"),
        alias_paths=("R:/src/l", ),
        alias_kind="dir",
    )
    mod.register_job(job)
    cover = mod._rewrite_cover_of("j1", [hybrid_v1])
    assert cover[hybrid_v1] == "recorded", f"v2 键向账必须解析到 recorded: {cover}"
    with capture_logs("auto_qb.core.modules.relocate_mod"):
        mod._step_verify(mod.get_job("j1"), {})
    assert rj.verify_replays_of(str(tmp_path), "j1") == 1, "真失败混批: 既有重放面触发(不落 WAIT 支)"
    j = rj.read_journal(str(tmp_path), "j1")
    assert j["rewrites"][hybrid_v2]["status"] == rj.REWRITE_RESET_STATUS, "hybrid 账(v2 键)被清回 pending"
    assert j["rewrites"]["HA"]["status"] == rj.REWRITE_RESET_STATUS
    assert j["rewrites"]["HP"]["status"] == "failed", "reset 只清 settled: failed 记录不动"
    assert mod.get_job("j1").phase == ru.PHASE_ARMED, "重放期相位回 armed(既有语义)"


# ---------------------------------------------------------------- 删链门(_step_verify 依赖扫描)


def test_step_verify_deps_block_then_release(tmp_path):
    """N5 形态: 门外共享者 save_path 恰等于旧根 → chain_deps 别名不删; 依赖消失 → 收尾完成"""
    mod, job, rt, removed = _rewritten_env(
        tmp_path,
        [("HA", "R:/dst")],
        extra=[("HZ", "R:/src")],  # Z: 组外共享者, 等值命中
    )
    mod._step_verify(job, rt)
    saved = mod.get_job("j1")
    assert not saved.is_terminal and saved.phase == ru.PHASE_REWRITTEN, (saved.phase, saved.reason)
    assert saved.reason == ru.REASON_CHAIN_DEPS and removed == [], (saved.reason, removed)
    assert "1 个种子" in saved.last_error and "HZ" in saved.last_error, saved.last_error

    del mod._ctx.store.by_hash["HZ"]  # 依赖消失(迁移或删除后)
    mod._step_verify(mod.get_job("j1"), rt)
    saved = mod.get_job("j1")
    assert saved.phase == ru.PHASE_DONE and removed == ["R:/src/l"], (saved.phase, removed)


def test_step_verify_deps_prefix_hit(tmp_path):
    """前缀命中: 组外种子落旧根之下(save_path = src/sub)同为依赖, 别名不删"""
    mod, job, rt, removed = _rewritten_env(
        tmp_path,
        [("HA", "R:/dst")],
        extra=[("HZ", r"R:\src\g2")],
    )
    mod._step_verify(job, rt)
    saved = mod.get_job("j1")
    assert saved.reason == ru.REASON_CHAIN_DEPS and removed == [], (saved.reason, removed)


def test_chain_gate_deps_scope_anchor_and_member_exempt(tmp_path):
    """R7 删链门重锚(计划 26-11-07-1300 D9): 锚 job.scope + 本组成员豁免(调用侧按 hash 过滤)
    - 本组豁免: 成员 save_path=dst(嵌套放行形态 dst ⊆ scope)不再顶进依赖集(T1a 自锁修);
      成员是否到位由核验步先行把关, 依赖集只关组外种子
    - 组外 scope 内保守计数: 等值(恰等 scope)与前缀(scope 之下)双向照算(N5 双判据保留)
    - scope 外不计: 组外种子停旧根(src)兄弟目录不算依赖(T1b/E7 假依赖修)
    - 旧账 scope 缺失: 回落 job.src(保守, 与旧锚同口径)
    - direct 自有面短路(0711 修法 b): 无别名 job 不开门(对照面)
    (面测试 job 带 alias_kind="dir" —— 刀2 前这些用例隐式依赖「direct 也开门」的旧口径,
    0711b 后开门前提 = 确有别名形态)
    """
    mod = _bare_mod(data_dir=str(tmp_path / "data"))

    def _deps(job, records):
        mod._ctx.store = types.SimpleNamespace(by_hash={h: _rec(h, sp) for h, sp in records})
        return [h for h, _sp in mod._chain_gate_deps(job)]

    # 本组豁免 + scope 外不计: 成员停在嵌套落点(dst ⊆ scope, 豁免承重), 组外种子停旧根兄弟目录
    job = _job("j1", src="R:/src", dst="R:/src/Show/待删", scope="R:/src/Show", hashes=("HA", "HB"), alias_kind="dir")
    assert _deps(job, [("HA", "R:/src/Show/待删"), ("HB", "R:/src/Show/待删"), ("HZ", "R:/src/停车")]) == [], \
        "成员豁免(R7)+ 组外 scope 外不计(E7 假依赖修)"
    # 组外 scope 内保守计数: 等值与前缀双向照算
    job2 = _job("j2", src="R:/src", dst="R:/dst", scope="R:/src/Show", hashes=("HA", ), alias_kind="dir")
    assert _deps(job2, [("HZ", "R:/src/Show"), ("HY", r"R:\src\Show\g2")]) == ["HZ", "HY"], \
        "组外种子在作用域等值/之下仍算依赖(N5 双判据保留)"
    # 成员与组外同处 scope 内: 只有组外计入(豁免按 hash 身份, 不误伤同路径组外种子语义)
    assert _deps(job2, [("HA", "R:/src/Show/inner"), ("HZ", "R:/src/Show")]) == ["HZ"], "成员豁免不误伤组外计数"
    # 旧根仅等值并列面(equal_root, R7 评审修复): dir_alias 收尾窗内经别名落进作用域的组外
    # 种子账面 save_path 恰等 job.src —— ⊄ scope, 只按 scope 判会漏计(D16 契约对齐)
    assert _deps(job2, [("HZ", "R:/src")]) == ["HZ"], "组外 save_path 恰等旧根仍算依赖(equal_root 等值面)"
    # 旧账 scope 缺失: 回落 job.src(保守)
    legacy = _job("j3", src="R:/src", dst="R:/dst", scope="", hashes=("HA", ), alias_kind="dir")
    assert _deps(legacy, [("HZ", "R:/src/停车")]) == ["HZ"], "scope 缺失回落 src(旧账兼容)"
    # direct 自有面短路(0711 修法 b): 无别名 job 组外落点不开门(旧口径恒悬挂 REASON_CHAIN_DEPS)
    direct = _job("j4", src="R:/src", dst="R:/dst", scope="R:/src", hashes=("HA", ), alias_kind="")
    assert _deps(direct, [("HZ", "R:/src"), ("HY", r"R:\src\deep")]) == [], "direct 自有面短路(0711b)"


def test_chain_gate_deps_file_kind_intersection_verdict(tmp_path):
    """R2 文件级删链门 verdict 交集判据(计划 26-11-13-0448 §03 R2, D4)

    命中面(scope 等值/前缀 + src 等值面)只是候选; 文件级 job(alias_kind="file")最终判定 =
    「文件清单 x job.alias_paths 交集」: 相交 = 依赖 / 不相交(组外异名) = 豁免(误拦1 修正面) /
    不可得(取数抛错/空清单) = 保守计依赖(宁拦勿漏, E8 口径); 本组 hash 豁免不变。
    """
    mod = _bare_mod(data_dir=str(tmp_path / "data"))

    def _deps(job, records):
        mod._ctx.store = types.SimpleNamespace(by_hash={h: r for h, r in records})
        return [h for h, _sp in mod._chain_gate_deps(job)]

    # 文件级 job: src=R:/src, scope=R:/src/Show, 链接账 = 内容根下 e00.mkv(嵌套成员形)
    fjob = _job(
        "j1",
        phase=ru.PHASE_REWRITTEN,
        hashes=("HA", ),
        alias_kind="file",
        alias_paths=("R:/src/Show/e00.mkv", ),
        scope="R:/src/Show",
    )
    # 相交(同名撞链接路径): 组外种子停 scope 等值面, 清单含链接同名文件 -> 依赖
    assert _deps(fjob, [("HZ", _rec_files("HZ", "R:/src/Show", ("e00.mkv", )))]) == ["HZ"], "同名撞链接 = 依赖"
    # 相交(E3 同名跨种形态): 组外种子恰等 src(等值面候选), 平铺同名文件 landing 撞链接 -> 依赖
    assert _deps(fjob, [("HZ", _rec_files("HZ", "R:/src", ("Show/e00.mkv", )))]) == ["HZ"], "E3 同名跨种 = 依赖"
    # 不相交(组外异名, 误拦1 修正面): 恰等 src + 清单与链接无交集 -> 豁免(R2 前 = 恒依赖)
    assert _deps(fjob, [("HZ", _rec_files("HZ", "R:/src", ("other.bin", )))]) == [], "组外异名(等值面) = 豁免"
    # 不相交: 前缀面候选(scope 之下)同样过交集精判, 异名豁免
    assert _deps(fjob, [("HZ", _rec_files("HZ", "R:/src/Show/g2", ("deep.bin", )))]) == [], "组外异名(前缀面) = 豁免"
    # 不可得(取数抛错): 候选命中 + 清单拿不到 -> 保守计依赖(宁拦勿漏, E8)
    assert _deps(fjob, [("HZ", _rec_files("HZ", "R:/src", files_error=True))]) == ["HZ"], "取数失败 = 保守计依赖"
    # 不可得(空清单): 同保守
    assert _deps(fjob, [("HZ", _rec_files("HZ", "R:/src", ()))]) == ["HZ"], "空清单 = 保守计依赖"
    # 本组豁免不变: 成员 hash 即使清单不相交也先按 hash 豁免(身份语义, 与路径无关)
    assert _deps(fjob, [("HA", _rec_files("HA", "R:/src", ("other.bin", )))]) == [], "成员 hash 豁免承重"
    # 目录级零变化: 命中即依赖, 不看文件清单(异名也拦, D16 契约面)
    djob = _job("j2", phase=ru.PHASE_REWRITTEN, hashes=("HA", ), alias_kind="dir", scope="R:/src/Show")
    assert _deps(djob, [("HZ", _rec_files("HZ", "R:/src/Show", ("other.bin", )))]) == ["HZ"], "目录级命中即依赖"
    assert _deps(djob, [("HZ", _rec_files("HZ", "R:/src", ("other.bin", )))]) == ["HZ"], "目录级等值面保留"
    # direct 自有面短路(0711 修法 b, 计划 26-11-15-2340 刀2): 无别名 job 无链可删,
    # 组外落点(等值/前缀)不再顶进依赖集 —— 旧口径下该形态收尾恒悬挂 REASON_CHAIN_DEPS
    # 且文案「维持别名」失实(direct 根本没有别名); 放行扩张如实钉扎(R4)
    direct = _job("j3", phase=ru.PHASE_REWRITTEN, hashes=("HA", ), alias_kind="", scope="R:/src/Show")
    assert _deps(direct, [("HZ", _rec_files("HZ", "R:/src/Show", ("other.bin", )))]) == [], "direct 自有面短路(0711b)"


def test_chain_gate_deps_ancestor_savepath_grid(tmp_path):
    """0535 祖先方向候选格(issue 26-11-13-0535, 计划 26-11-15-2340 刀2): 组外种子
    save_path 为 job.src 的严格祖先且其内容根恰覆盖旧根 -> 计入依赖(修复前该形态
    前缀/等值两头都不命中, 删链门误清零 -> 收尾删别名断粮)

    - 文件级: 祖先覆盖 + 清单撞链接 -> 依赖(交集精判复用 file_alias_intersects);
    - 文件级: 祖先覆盖但清单与链接不相交(异名) -> 豁免(不造新谓词, 精判不放宽);
    - 目录级: 祖先覆盖 -> 依赖(数据落 junction 树, 命中即依赖);
    - 祖先但内容根不覆盖旧根(name 换了) -> 不命中(候选面不扩面到不相关祖先);
    - 祖先但文件清单不可得 -> 该格不命中(候选面不猜; 候选面外形态与旧口径一致)。
    """
    mod = _bare_mod(data_dir=str(tmp_path / "data"))

    def _deps(job, records):
        mod._ctx.store = types.SimpleNamespace(by_hash={r.hash: r for r in records})
        return [h for h, _sp in mod._chain_gate_deps(job)]

    # 0535 issue 原形: 组 src = R:/Download/PTing, 组外种子 save_path = R:/Download、
    # name = PTing -> 内容根 = R:/Download/PTing == src(祖先方向, 生产布局真实可达)
    fjob = _job(
        "j1",
        phase=ru.PHASE_REWRITTEN,
        hashes=("HA", ),
        alias_kind="file",
        alias_paths=("R:/Download/PTing/e00.mkv", ),
        src="R:/Download/PTing",
        scope="R:/Download/PTing",
    )
    ancestor_hit = _rec_files("HZ", "R:/Download", ("PTing/e00.mkv", ))  # 清单撞链接 -> 相交
    ancestor_miss = _rec_files("HY", "R:/Download", ("PTing/other.bin", ))  # 覆盖但异名 -> 不相交
    assert _deps(fjob, [ancestor_hit]) == ["HZ"], "祖先方向依赖(文件级相交)必须计入(0535 红->绿)"
    assert _deps(fjob, [ancestor_miss]) == [], "祖先覆盖但异名不相交: 精判豁免(不放宽)"
    # 目录级: 祖先覆盖 -> 依赖(数据落 junction 树)
    djob = _job(
        "j2",
        phase=ru.PHASE_REWRITTEN,
        hashes=("HA", ),
        alias_kind="dir",
        src="R:/Download/PTing",
        scope="R:/Download/PTing"
    )
    assert _deps(djob, [_rec_files("HZ", "R:/Download", ("PTing/e00.mkv", ))]) == ["HZ"], "祖先方向依赖(目录级)"
    # 祖先但内容根不覆盖旧根: 候选面不收(不扩面到不相关祖先)
    assert _deps(fjob, [_rec_files("HZ", "R:/Download", ("OtherStuff/e00.mkv", ))]) == [], \
        "祖先不覆盖旧根 = 不相关, 不命中"
    # 祖先但清单不可得(空表): 内容根不可判, 该格不命中(候选面不猜)
    assert _deps(fjob, [_rec_files("HZ", "R:/Download", ())]) == [], "清单不可得: 候选面不猜, 该格不命中"


def test_step_verify_direct_no_alias_finalizes(tmp_path):
    """0711 修法 b(issue 26-11-13-0711, 计划 26-11-15-2340 刀2): direct(无别名)收尾窗
    组外种子落旧根前缀/等值面 -> 删链门自有面短路, 核验通过即收尾 —— 修复前该形态
    deps>0 恒悬挂 REASON_CHAIN_DEPS 且文案「维持别名等依赖消失」失实(direct 无别名)
    (R4 放行扩张如实钉扎; direct + 继承条目带别名时继承面照开门, 见 chain_gate_deps 用例)
    """
    mod, job, rt, removed = _rewritten_env(tmp_path, [("HA", "R:/dst")], alias_paths=())
    job = mod.get_job("j1")
    mod._set_job(replace(job, alias_kind="", alias_paths=(), scope="R:/src"))
    mod._ctx.store.by_hash["HZ"] = _rec("HZ", r"R:\src\deep")  # 组外种子落旧根前缀(0711 注入形态)
    mod._ctx.store.by_hash["HZ2"] = _rec("HZ2", "R:/src")  # 组外种子恰等旧根(等值面)
    mod._step_verify(mod.get_job("j1"), rt)
    saved = mod.get_job("j1")
    assert saved.phase == ru.PHASE_DONE and saved.reason == ru.REASON_FINALIZED, \
        ("direct 无别名: 核验过即收尾, 不悬挂 chain_deps", saved.phase, saved.reason)
    assert removed == [], "direct 无别名无链可删"
    # 对照: 同落点在 dir 形态下仍悬挂(开门前提 = 确有别名)
    mod2, job2, rt2, removed2 = _rewritten_env(tmp_path / "d2", [("HA", "R:/dst")])
    mod2._ctx.store.by_hash["HZ"] = _rec("HZ", r"R:\src\deep")
    mod2._step_verify(mod2.get_job("j1"), rt2)
    saved2 = mod2.get_job("j1")
    assert saved2.reason == ru.REASON_CHAIN_DEPS and removed2 == [], (saved2.reason, removed2)


def test_chain_deps_text_form_aware_wording(tmp_path):
    """R5(2) 删链门反馈面文案分型(计划 26-11-13-0448 §03 R5): 文件级随 R2 语义改措辞
    「N 个种子的文件与别名链接重叠」+ 出路带立即收尾加速器; 目录级/direct 保留现行
    save_path 面(scope/save_path 语义仍真), 不带立即收尾句"""
    mod = _bare_mod(data_dir=str(tmp_path / "data"))
    deps = [
        ("HZ" + "0" * 32, "R:/src"), ("HY" + "0" * 32, "R:/src/g2"), ("HX" + "0" * 32, "R:/src/g3"),
        ("HW" + "0" * 32, "R:/src/g4")
    ]
    # 文件级: 重叠语义 + 收尾出路(依赖清零即自动收尾 / 立即收尾), 无 save_path 面旧句
    fjob = _job(
        "j1", phase=ru.PHASE_REWRITTEN, alias_kind="file", alias_paths=("R:/src/Show/e00.mkv", ), scope="R:/src/Show"
    )
    ftext = mod._chain_deps_text(fjob, deps)
    assert "4 个种子的文件与别名链接重叠 等共 4 个" in ftext, ftext
    assert "迁移到新位置或删除后自动重判" in ftext, ftext
    assert "依赖清零即自动收尾, 也可用「立即收尾」按钮加速收尾" in ftext, ftext
    assert "保存路径在别名作用域" not in ftext, "文件级不再用 save_path 面措辞"
    # 目录级: 现行面原样(scope 前缀 + src 等值), 无立即收尾句
    djob = _job("j2", phase=ru.PHASE_REWRITTEN, alias_kind="dir", scope="R:/src/Show")
    dtext = mod._chain_deps_text(djob, deps)
    assert "4 个种子的保存路径在别名作用域 R:/src/Show 之下或恰在旧根 R:/src(等值) 等共 4 个" in dtext, dtext
    assert "迁移到新位置或删除后自动重判" in dtext and "立即收尾" not in dtext, dtext
    # direct: 与目录级同一文案(判据面零变化, 不造第二份格式)
    direct = _job("j3", phase=ru.PHASE_REWRITTEN, alias_kind="", scope="R:/src/Show")
    assert mod._chain_deps_text(direct, deps) == dtext, "direct 与目录级同文案"


# ---------------------------------------------------------------- D16 删种拦截(qbapi 单点)


class _GuardStore:
    """QbApi 拦截判定的最小 store 替身: get/remove_torrent(S5 起登记集不在 store 上)"""
    def __init__(self, records):
        self._records = dict(records)
        self.removed = []

    def get(self, h):
        return self._records.get(h)

    def remove_torrent(self, h):
        self.removed.append(h)


def _guard_api(records, roots=None, members=()):
    """QbApi + ctx 假 relocate 模块(S5 派生查询替身): roots 入参沿用旧 dict 形
    {src: (job_id, kind, alias_paths)}(调用点零改), 此处转 (src, job_id, kind, alias_paths)
    四元组序列(ru.alias_roots_of 同形)喂替身; members = relocating 成员面(R5(1) 文案分型,
    计划 26-11-13-0448); 缺省空 = 全部按组外文案分型(拦截判定不受影响)。"""
    client = FakeClient()
    root_items = tuple((src, jid, kind, paths) for src, (jid, kind, paths) in (roots or {}).items())
    api = QbApi(
        client,
        _GuardStore(records),
        ctx=types.SimpleNamespace(relocate=FakeRelocateQueries(roots=root_items, members=members)),
    )
    return api, client


def test_qbapi_delete_guard_blocks_delete_files():
    """目录别名形态(根=src): 等值与前缀命中都拦(整批不发 qB); 纯删除(delete_files=False)放行
    (R3 后目录级全量拦原样, D6; 登记值 = (job_id, alias_kind, alias_paths) 新形;
    R5(1) 成员文案: 出路 = 仅删种子 -> 组账收缩自愈 + 立即收尾加速器)"""
    records = {
        "HA": _rec("HA", r"R:\src"),  # 等值(N5 形态)
        "HB": _rec("HB", r"R:\src\sub"),  # 前缀
        "HZ": _rec("HZ", r"R:\elsewhere"),  # 门外
    }
    api, client = _guard_api(records, {r"R:\src": ("j1", "dir", ())}, members={"HA", "HB"})
    with pytest.raises(DeleteBlockedError) as ei:
        api.torrents_delete(torrent_hashes=["HA", "HB", "HZ"], delete_files=True)
    assert [b[0] for b in ei.value.blocked] == ["HA", "HB"], ei.value.blocked
    assert ei.value.blocked[0][2] == "j1", "命中根必须能追到 job"
    msg = str(ei.value)
    assert "2 个种子是迁移收尾窗口中活动迁移组的成员" in msg, msg
    assert "仅删除种子(不含文件)" in msg and "组账自动收缩" in msg, "文案必须给出收缩自愈出路"
    assert "数据留新位置待收尾后清理" in msg and "立即收尾" in msg, msg
    assert "等迁移收尾完成后重试" not in msg, "成员出路已是收缩自愈, 旧「等收尾重试」句必须退场"
    assert not any(c[0] == "delete" for c in client.calls), "拦截必须整批不发 qB"
    api.torrents_delete(torrent_hashes=["HZ"], delete_files=True)  # 门外照删
    assert ("delete", True) in client.calls
    api.torrents_delete(torrent_hashes=["HA"], delete_files=False)  # 纯删除 = 去文件化出口
    assert ("delete", False) in client.calls
    assert api.store.removed == ["HZ", "HA"], api.store.removed


def test_qbapi_delete_guard_ancestor_savepath_grid():
    """0535 祖先方向候选格 D16 半边(issue 26-11-13-0535, 计划 26-11-15-2340 刀2):
    组外种子 save_path 为登记根严格祖先且内容根恰覆盖登记根 -> 带文件删除拦(修复前
    该形态两头不命中不拦 = D16 空窗, deleteFiles 穿链接删 dst 数据); verdict 与既有
    形态分流同构 —— 文件级过 file_alias_intersects 精判(异名不相交放行, 不放宽) /
    目录级祖先覆盖即拦(junction 树) / 清单不可得该格不命中(候选面不猜) / 祖先不覆盖
    登记根(name 换了)不拦。候选面单点复用 chain_gate_hits, 不造第二份祖先口径。"""
    # 红->绿主行(0535 issue 原形): 登记根 R:/Download/PTing, HZ save_path = R:/Download
    # 且 name=PTing -> 内容根恰覆盖登记根, 清单 PTing/e00.mkv 撞链接
    records = {"HZ": _rec_files("HZ", "R:/Download", ("PTing/e00.mkv", ))}
    api, client = _guard_api(records, {"R:/Download/PTing": ("j1", "file", ("R:/Download/PTing/e00.mkv", ))})
    with pytest.raises(DeleteBlockedError) as ei:
        api.torrents_delete(torrent_hashes=["HZ"], delete_files=True)
    assert [b[0] for b in ei.value.blocked] == ["HZ"] and ei.value.blocked[0][2] == "j1", ei.value.blocked
    assert not any(c[0] == "delete" for c in client.calls), "祖先方向依赖的带文件删除必须拦(0535 红->绿)"
    # 文件级精判豁免面: 祖先覆盖但清单与链接不相交(异名) -> 放行(不因祖先格放宽)
    client.calls.clear()
    api.store._records["HY"] = _rec_files("HY", "R:/Download", ("PTing/other.bin", ))
    api.torrents_delete(torrent_hashes=["HY"], delete_files=True)
    assert ("delete", True) in client.calls, "祖先覆盖但异名不相交: 精判放行(R3 契约)"
    # 目录级: 祖先覆盖即拦(数据落 junction 树)
    client.calls.clear()
    api.ctx.relocate.roots = (("R:/Download/PTing", "j2", "dir", ()), )
    with pytest.raises(DeleteBlockedError):
        api.torrents_delete(torrent_hashes=["HZ"], delete_files=True)
    assert not any(c[0] == "delete" for c in client.calls)
    # 清单不可得(空表): 内容根不可判 -> 该格不命中, 候选面不猜(放行; 精判面保守拦只
    # 作用于路径面候选, 祖先格无清单即无覆盖事实)
    client.calls.clear()
    api.ctx.relocate.roots = (("R:/Download/PTing", "j1", "file", ("R:/Download/PTing/e00.mkv", )), )
    api.store._records["HN"] = _rec_files("HN", "R:/Download", ())
    api.torrents_delete(torrent_hashes=["HN"], delete_files=True)
    assert ("delete", True) in client.calls, "清单不可得: 祖先格不命中(候选面不猜)"
    # 祖先但内容根不覆盖登记根: 不相关祖先不拦
    client.calls.clear()
    api.store._records["HM"] = _rec_files("HM", "R:/Download", ("OtherStuff/x.bin", ))
    api.torrents_delete(torrent_hashes=["HM"], delete_files=True)
    assert ("delete", True) in client.calls, "祖先不覆盖登记根 = 不相关, 不拦"


def test_qbapi_delete_guard_message_member_vs_out_group():
    """R5(1) D16 文案按拦截对象分型(计划 26-11-13-0448 §03 R5, D6): 成员出路 = 仅删种子 ->
    组账自动收缩自愈 + 立即收尾; 组外撞根出路 = 迁出旧根或仅删种子(其本身即删链门依赖,
    「等收尾」不收敛 —— 循环句退场) + 立即收尾降为次选(只加速改写窗);
    混批分型各给一句; 成员集缺省空 = 全部按组外文案分型(替身兼容面, 拦截判定不受影响)"""
    records = {
        "HA": _rec_files("HA", "R:/src", ("rlfn.bin", )),  # 成员(清单与链接全等, 相交)
        "HB": _rec_files("HB", "R:/src", ("rlfn.bin", )),  # 组外同名撞链接(相交, E3 形态)
    }
    roots = {"R:/src": ("j9", "file", ("R:/src/rlfn.bin", ))}
    api, client = _guard_api(records, roots, members={"HA"})
    # 混批: 成员句 + 组外句并存(分型各一)
    with pytest.raises(DeleteBlockedError) as ei:
        api.torrents_delete(torrent_hashes=["HA", "HB"], delete_files=True)
    msg = str(ei.value)
    assert "1 个种子是迁移收尾窗口中活动迁移组的成员" in msg, msg
    assert "组账自动收缩" in msg and "数据留新位置待收尾后清理" in msg, msg
    assert "1 个种子位于迁移收尾窗口的活动别名之下" in msg and "不是该迁移组的成员" in msg, msg
    assert "请把这些种子迁出旧根" in msg and "或改用「仅删除种子(不含文件)」" in msg, msg
    assert "依赖清零收尾自动完成后, 带文件删除自然可重试" in msg and "「立即收尾」按钮加速改写窗" in msg, msg
    assert "请等迁移收尾完成后重试" not in msg, "组外「等收尾」循环句必须退场(被拦组外种子自身即删链门依赖)"
    assert not any(c[0] == "delete" for c in client.calls), "整批不发 qB"
    # 纯成员批: 只有成员句(组外句与旧「等收尾重试」出路退场)
    client.calls.clear()
    with pytest.raises(DeleteBlockedError) as ei2:
        api.torrents_delete(torrent_hashes=["HA"], delete_files=True)
    m2 = str(ei2.value)
    assert "活动迁移组的成员" in m2 and "不是该迁移组的成员" not in m2, m2
    assert "等迁移收尾完成后重试" not in m2, m2
    # 纯组外批: 只有组外句(成员分型语义不出现; 出路可落地: 迁出/仅删种子 -> 依赖清零自动收尾)
    client.calls.clear()
    with pytest.raises(DeleteBlockedError) as ei3:
        api.torrents_delete(torrent_hashes=["HB"], delete_files=True)
    m3 = str(ei3.value)
    assert "不是该迁移组的成员" in m3, m3
    assert "请把这些种子迁出旧根" in m3 and "或改用「仅删除种子(不含文件)」" in m3, m3
    assert "依赖清零收尾自动完成后, 带文件删除自然可重试" in m3, m3
    assert "「立即收尾」按钮加速改写窗" in m3, "立即收尾保留为次选(只加速改写窗)"
    assert "请等迁移收尾完成后重试" not in m3 and "等迁移收尾完成后重试" not in m3, m3
    assert "组账自动收缩" not in m3 and "活动迁移组的成员" not in m3, "组外句不得带成员收缩语义"
    # 成员集缺省空(替身未带成员账): 全部按组外文案分型(兼容面), 拦截本身不松动
    api2, _client2 = _guard_api({"HA": records["HA"]}, roots)
    with pytest.raises(DeleteBlockedError) as ei4:
        api2.torrents_delete(torrent_hashes=["HA"], delete_files=True)
    assert "不是该迁移组的成员" in str(ei4.value), str(ei4.value)


def test_qbapi_delete_guard_file_links_form():
    """文件级形态(成员/同名撞链接): 相交拦(文件级 symlink deleteFiles 跟随直删, D16);
    R3 后的放行面(组外异名不相交)单测在 test_qbapi_delete_guard_file_kind_intersection_verdict"""
    records = {"HA": _rec_files("HA", "R:/src", ("l", ))}
    api, client = _guard_api(records, {"R:/src": ("j9", "file", ("R:/src/l", ))})
    with pytest.raises(DeleteBlockedError):
        api.torrents_delete(torrent_hashes=["HA"], delete_files=True)
    assert not any(c[0] == "delete" for c in client.calls)


def test_qbapi_delete_guard_file_kind_intersection_verdict():
    """R3 文件级 D16 verdict 交集判据(计划 26-11-13-0448 §03 R3, D4/D6)

    候选面不变(save_path 在登记根等值/前缀面); 文件级 verdict 换「文件清单 x alias_paths
    交集」—— 不相交(组外异名带文件, 误拦2 修正面)放行 / 相交(成员身份面/同名撞链接根
    E3 形态)拦 / 清单不可得(取数抛错/空清单)保守拦(宁拦勿漏, E8) / 目录级全量拦原样
    (N5 junction 通路) / 多根重叠两序仍拦(任一后根命中即拦, 目录级全量拦不被先扫到的
    file 豁免根短路, 评审轮 1 修 1) / 登记旧形(str)按目录级保守拦(兼容面)。
    """
    # 放行: 组外异名带文件, 清单与链接不相交(R3 修正面 —— R3 前该形态被拦)
    records = {"HZ": _rec_files("HZ", "R:/src", ("other.bin", ))}
    api, client = _guard_api(records, {"R:/src": ("j9", "file", ("R:/src/rlfn.bin", ))})
    api.torrents_delete(torrent_hashes=["HZ"], delete_files=True)
    assert ("delete", True) in client.calls, "组外异名带文件删除必须放行(R3)"
    # 拦: 成员身份面(清单与链接全等)
    client.calls.clear()
    api.store._records["HA"] = _rec_files("HA", "R:/src", ("rlfn.bin", ))
    with pytest.raises(DeleteBlockedError) as ei:
        api.torrents_delete(torrent_hashes=["HA"], delete_files=True)
    assert [b[0] for b in ei.value.blocked] == ["HA"] and ei.value.blocked[0][2] == "j9", ei.value.blocked
    assert not any(c[0] == "delete" for c in client.calls), "整批不发 qB"
    # 拦: 同名撞链接根(E3 同名跨种形态, 嵌套成员形)
    client.calls.clear()
    api.store._records["HB"] = _rec_files("HB", "R:/src", ("Show/e00.mkv", ))
    api.ctx.relocate.roots = (("R:/src", "j9", "file", ("R:/src/Show/e00.mkv", )), )
    with pytest.raises(DeleteBlockedError):
        api.torrents_delete(torrent_hashes=["HB"], delete_files=True)
    assert not any(c[0] == "delete" for c in client.calls)
    # 保守拦: 清单不可得(取数抛错 / 空清单) -> 宁拦勿漏(E8)
    for bad in (_rec_files("HX", "R:/src", files_error=True), _rec_files("HX", "R:/src", ())):
        client.calls.clear()
        api.store._records["HX"] = bad
        with pytest.raises(DeleteBlockedError):
            api.torrents_delete(torrent_hashes=["HX"], delete_files=True)
        assert not any(c[0] == "delete" for c in client.calls), "清单不可得必须保守拦"
    # 目录级原样: 全量拦(清单不相交也拦, N5 junction 通路)
    client.calls.clear()
    api.store._records["HD"] = _rec_files("HD", "R:/src", ("other.bin", ))
    api.ctx.relocate.roots = (("R:/src", "j1", "dir", ()), )
    with pytest.raises(DeleteBlockedError):
        api.torrents_delete(torrent_hashes=["HD"], delete_files=True)
    assert not any(c[0] == "delete" for c in client.calls)
    # 多根重叠(评审轮 1 修 1): save_path 同时落在 file 根(不相交)与 dir 根(前缀)之下,
    # file 根在前 -> 豁免只跳过该根, 后面的 dir 根仍必须拦(评审员实复现的序敏感放行洞)
    client.calls.clear()
    api.store._records["HZ"] = _rec_files("HZ", "R:/src/d1/z.bin", ("z.bin", ))
    api.ctx.relocate.roots = (
        ("R:/src", "jA", "file", ("R:/src/rlfn.bin", )),
        ("R:/src/d1", "jB", "dir", ()),
    )
    with pytest.raises(DeleteBlockedError) as ei:
        api.torrents_delete(torrent_hashes=["HZ"], delete_files=True)
    assert ei.value.blocked[0][1:] == ("R:/src/d1", "jB"), ei.value.blocked
    assert not any(c[0] == "delete" for c in client.calls)
    # 反序: dir 根在前(file 根在后) -> 同样拦(两序钉死, 防序敏感回归)
    client.calls.clear()
    api.ctx.relocate.roots = (
        ("R:/src/d1", "jB", "dir", ()),
        ("R:/src", "jA", "file", ("R:/src/rlfn.bin", )),
    )
    with pytest.raises(DeleteBlockedError) as ei2:
        api.torrents_delete(torrent_hashes=["HZ"], delete_files=True)
    assert ei2.value.blocked[0][1:] == ("R:/src/d1", "jB"), ei2.value.blocked
    assert not any(c[0] == "delete" for c in client.calls)
    # 登记值旧形(str job_id)兼容面用例已退役(S5 派生查询只产四元组, 旧形分支结构性消失,
    # 计划 26-11-15-2340 刀3) —— 拦截判定面不再有「形态不可判」输入形态。


def test_qbapi_delete_guard_allows_outside_and_unregistered():
    """无活动别名登记(未启用迁移/全部终态)与快照缺席的种子: 不拦(fail-open, 判据只判事实)"""
    records = {"HA": _rec("HA", r"R:\src")}
    api, client = _guard_api(records, None)  # 无登记
    api.torrents_delete(torrent_hashes=["HA"], delete_files=True)
    assert ("delete", True) in client.calls
    api2, client2 = _guard_api({}, {r"R:\src": ("j1", "dir", ())})  # 有登记但种子不在快照: 不可判, 放行
    api2.torrents_delete(torrent_hashes=["HX"], delete_files=True)
    assert ("delete", True) in client2.calls


def test_qbapi_delete_guard_allows_probe_tagged_seeds():
    """探测种子(tag 含 TAG_PROBE)落在活动别名根下也放行(评审 #5): 自造探针非组成员数据,
    拦截会让 _cleanup/启动残留扫描的 deleteFiles 恒失败(探针滞留每次启动重复告警);
    普通种子(无探测标签)同根仍拦(拦截面对成员数据不松动)"""
    from auto_qb.core.modules.relocate_probe import TAG_PROBE

    probe = types.SimpleNamespace(hash="HP", save_path=r"R:\src\probe-x", tags_set=frozenset({TAG_PROBE}))
    normal = _rec("HA", r"R:\src")  # 无 tags_set 属性(旧形态替身也判得出: 非探针)
    api, client = _guard_api({"HP": probe, "HA": normal}, {r"R:\src": ("j1", "dir", ())})  # 四元组形(S5 派生口径)
    # (评审轮 1 修 4)
    api.torrents_delete(torrent_hashes=["HP"], delete_files=True)  # 探针: 放行
    assert ("delete", True) in client.calls
    with pytest.raises(DeleteBlockedError) as ei:  # 普通成员种子同根: 照拦
        api.torrents_delete(torrent_hashes=["HA"], delete_files=True)
    assert [b[0] for b in ei.value.blocked] == ["HA"]
    # 混批: 探针不进拦截名单, 拦截只点名普通种子
    client.calls.clear()
    with pytest.raises(DeleteBlockedError) as ei2:
        api.torrents_delete(torrent_hashes=["HP", "HA"], delete_files=True)
    assert [b[0] for b in ei2.value.blocked] == ["HA"], ei2.value.blocked
    assert not any(c[0] == "delete" for c in client.calls), "整批仍不发 qB(同批有被拦种子)"


# ---------------------------------------------------------------- WebUI 删除命令面(第二条路径)


def test_webui_delete_blocked_receipt_single_and_group(tmp_path):
    """delete_torrent / delete_group 撞 D16 拦截 → error 回执带解法文案 + qB 未收到 delete;
    纯删除(delete_files=False)照常发(两条 WebUI 删除命令路径共用 qbapi 单点判;
    R5(1) 成员分型: HA 登记进成员账, 回执文案走成员出路句)"""
    from webui_helpers import _make_grouped_manager

    mgr, client, key = _make_grouped_manager(str(tmp_path))
    # S5 派生查询替身: 拦截数据面经 ctx.relocate 查询喂入(目录别名根 R:\Downloads + 成员 HA)
    mgr.ctx.relocate.alias_roots = lambda: ((r"R:\Downloads", "j1", "dir", (r"R:\Downloads", )), )
    mgr.ctx.relocate.relocating_hashes = lambda: frozenset({"HA"})
    # 单发路径
    mgr.web.commands.put(("delete_torrent", {"hash": "HA", "delete_files": True, "cmd_id": "d1"}))
    mgr.web.consume_commands()
    r1 = mgr.web.results["d1"]
    assert r1["status"] == "error" and "仅删除种子(不含文件)" in r1["error"], r1
    assert "组账自动收缩" in r1["error"], "成员出路句必须带收缩自愈语义(R5(1))"
    assert not any(c[0] == "delete" for c in client.calls), "拦截不得发 qB"
    # 组路径
    mgr.web.commands.put(("delete_group", {"key": key, "delete_files": True, "cmd_id": "d2"}))
    mgr.web.consume_commands()
    r2 = mgr.web.results["d2"]
    assert r2["status"] == "error" and "仅删除种子(不含文件)" in r2["error"], r2
    assert not any(c[0] == "delete" for c in client.calls)
    # 纯删除: 放行(去文件化出口)
    mgr.web.commands.put(("delete_torrent", {"hash": "HA", "delete_files": False, "cmd_id": "d3"}))
    mgr.web.consume_commands()
    assert mgr.web.results["d3"]["status"] == "ok", mgr.web.results["d3"]
    assert ("delete", False) in client.calls


# ---------------------------------------------------------------------------
# 覆盖率缺口清偿(26-11-07): 核验悬挂同参重放 / qB 侧自检异常
# ---------------------------------------------------------------------------


def test_verify_hang_unchanged_state_is_debug_only(tmp_path):
    """重放一轮后仍不过且反馈面无变化: 只落 DEBUG(不重复清账/不重复刷警告, 防每拍刷屏)

    S4 收尾守卫(计划 26-11-20-0434 R1)后有账成员才走重放/悬挂面 —— 夹具给成员预置改写
    账(recorded), 落既有 recorded 支: 闸已用尽 + 反馈面无变化 => DEBUG 静默。
    """
    import logging

    mod = _bare_mod(data_dir=str(tmp_path / "data"))
    rj.write_journal(
        mod._data_dir(),
        "j1",
        {
            "verify_replays": 1,
            "rewrites": {
                "a" * 40: {
                    "status": "rewritten",
                    "ts": 1.0
                }
            }
        },
    )
    bad = [("a" * 40, "已不在客户端")]
    detail = "; ".join(f"{h[:8]} {state}" for h, state in bad[:3])
    text = f"核验未过: {detail}(别名维持, 成员经别名可读)"
    job = _job("j1", phase=ru.PHASE_REWRITTEN, reason=ru.REASON_VERIFY_FAILED, last_error=text)
    with capture_logs("auto_qb.core.modules.relocate_mod", level=logging.DEBUG) as cap:
        mod._verify_hang(job, bad)
    assert any("悬挂维持" in m for m in cap.messages), cap.messages
    assert rj.verify_replays_of(mod._data_dir(), "j1") == 1, "同参重放不再清账"


def test_qb_side_check_self_failure_is_skipped(tmp_path, monkeypatch):
    """qB 侧自检自身炸 => skipped(保守默认不挡武装), rt 记异常供排查"""
    from auto_qb.core.modules import relocate_proof as rp_mod

    mod = _bare_mod(data_dir=str(tmp_path / "data"))
    job = _job("j1", phase=ru.PHASE_MOVED)

    def _boom(*a, **kw):
        raise RuntimeError("evidence broke")

    monkeypatch.setattr(rp_mod, "link_follow_evidence", _boom)
    rt = {}
    assert mod._qb_side_check(job, rt) == "skipped"
    assert "自检异常" in rt["qb_side_check"] and "RuntimeError" in rt["qb_side_check"]


# ---------------------------------------------------------------------------
# 覆盖率缺口清偿(26-11-07): 批量删除拦截回执 / 无 cmd_id 的拦截静默回执
# ---------------------------------------------------------------------------


def test_webui_delete_blocked_receipt_bulk_and_no_cmd_id(tmp_path):
    """D16 拦截回执全路径: 批量 delete 撞拦截 -> error 回执; 单发/组发无 cmd_id -> 静默回执
    (不炸不写结果页, qB 未收到 delete)"""
    from webui_helpers import _make_grouped_manager

    mgr, client, key = _make_grouped_manager(str(tmp_path))
    # S5 派生查询替身: 拦截数据面经 ctx.relocate 查询喂入(R5(1) 成员分型: 整批按成员出路句回显)
    mgr.ctx.relocate.alias_roots = lambda: ((r"R:\Downloads", "j1", "dir", (r"R:\Downloads", )), )
    mgr.ctx.relocate.relocating_hashes = lambda: frozenset({"HA", "HB"})
    # 批量路径(cmd_id 在场): 整批不发 qB, error 回执
    mgr.web.commands.put(
        ("bulk_torrents", {
            "hashes": ["HA", "HB"],
            "action": "delete",
            "delete_files": True,
            "cmd_id": "d-bulk",
        })
    )
    mgr.web.consume_commands()
    r1 = mgr.web.results["d-bulk"]
    assert r1["status"] == "error" and "仅删除种子" in r1["error"], r1
    assert not any(c[0] == "delete" for c in client.calls)
    # 单发无 cmd_id: 拦截仍生效, 静默返回(无结果页可写)
    mgr.web.commands.put(("delete_torrent", {"hash": "HA", "delete_files": True}))
    mgr.web.consume_commands()
    assert not any(c[0] == "delete" for c in client.calls), "无 cmd_id 也必须拦(防误删)"
    # 组发无 cmd_id: 同上
    mgr.web.commands.put(("delete_group", {"key": key, "delete_files": True}))
    mgr.web.consume_commands()
    assert not any(c[0] == "delete" for c in client.calls), "无 cmd_id 组发同样拦"
