"""test_relocate_startup_reconcile 测试计划: relocate 启动对账自愈(计划 26-11-10-0721 S1/S2)

机制(计划 §03): 每次进程启动后首轮 qB 连接成功的 tick, 对 phase==failed 的 job 按物理
现状重推相位 —— 判定表(§03.1)前置闸 armed_at>0 一律保持 failed, armed_at==0 才按双
证据(§03.2: mover save_path==dst ∧ dst 内容全量在位)分流: 成立 => 重入 moved(重入
落账即置 armed_at, §03.3), 否则保守保持 failed。flag 在 _load_jobs 按 phase==failed
无态推导(§03.4, 运行期 flag 零持久状态), 消费点 = on_task_line tick(与 rt["recover"]
的消费窗同窗), 消费即清(每进程每笔至多一次), qB 未连上时 flag 保持留待首连。
热启用(apply 假->真)经同一 _load_jobs 推导, 同口径。范围排除: cancelled/done 不对账,
运行期新失败不重判。

## 测试计划(每个测试函数一条)
### 判定表四行(§03.1; S1 红验口径: 行 1/2 红, 行 3/4 现行代码即绿)
- test_row1_mover_at_dst_content_in_place_reenters_moved: 行 1 —— mover save_path==dst
  且 dst 内容全量在位 => 重入 moved + 重入落账同步置 armed_at(§03.3)+ rt stage=verify
  (既有链入口)+ flag 消费即清 + 一行对账日志(重入 1 / 保留 0)
- test_row2_all_members_at_dst_reenters_moved: 行 2 —— 全员 save_path==dst(armed_at==0,
  qB 侧手工补完形态) => 同行 1 重入(全员==dst 蕴含证据一)
- test_row3_all_at_src_keeps_failed: 行 3 —— 全员==src(82f6 搬迁段未完成形态) =>
  保持 failed, armed_at 不动(账面=现实)
- test_row4_dst_content_mismatch_keeps_failed: 行 4 —— mover==dst 但 dst 内容 size 不等
  (混合态由证据二排除) => 保持 failed(保守); 证据不可得(mover 不在快照)同格
### 证据二全量真值(§03.2; 不复用 B′ any-hit 口径)
- test_evidence2_partial_missing_file_blocks_reentry: 部分文件缺失即不在位(缺文件不放行)
  —— any-hit 语义会放走的「部分在位」态必须被拦下
### armed_at 前置闸(A1/§03.3; S1 红验口径: 闸类用例在无机制时属真空绿)
- test_gate_armed_at_blocks_reentry: armed_at>0 的 failed 一律保持 failed(自动链运行
  配额已用掉), 即使双证据全成立也不重入, armed_at 原值不动
- test_gate_closes_after_reentry_sets_armed_at: 重入落账置位后闸关 —— 重入后的再次
  失败(armed_at 已 >0)不随第二次推导(热启用口径)再重入, 出路 = 人审 re-issue
### flag 无态推导与消费幂等(§03.4)
- test_load_jobs_derives_reconcile_flag_for_failed_only: _load_jobs 按 phase==failed
  推导 rt["reconcile"](仿 rt["recover"] 既有模式), moving/done 不推导, recover 键不回归
- test_load_jobs_reconcile_adopts_terminal_and_cleans_foreign_entries: 启动对账采纳支补挂
  B2 终态清理(评审 major, journal 失窗恢复面)—— state 非终态 + 盘上 journal 终相位
  (ts 锚定本世)回写终态后, 陈旧 kind=A/mismatch 通知条目随回写清理、kind=B 保留, 随
  _load_jobs 尾部单次 _persist 同窗落盘; 无 foreign 段的采纳支零建键(黄金法则 2)
### 启动守阵(S2, 阶段 2: _load_jobs 尾部接线; 逐 job 采纳支清理之后跑全表兜底)
- test_load_jobs_cleans_stale_notified_entries_on_startup: 启动扫全表 —— job 不在/已终态的
  A+mismatch 清, B 与活跃 job 的 A/mismatch 留; 与上面的 journal 采纳支逐 job 清理并存
  (逐 job 先跑, 本守阵兜底全表, 幂等不冲突)
- test_load_jobs_dry_run_zero_writes: dry-run 零写账 —— 账内容不变, 不调清理/换代, 不写盘
- test_load_jobs_repeat_idempotent: 重复 _load_jobs 零副作用 —— 第二轮零删除零日志,
  发布视图引用恒稳(内容相等不换代)
- test_load_jobs_foreign_off_no_account_no_materialize: foreign_torrent=false 且无账 ——
  启动不 materialize relocate.foreign.notified(黄金法则 2; 换代仅账已在时跑)
- test_load_jobs_publishes_view_after_cleanup: 清理后 WebUI 只读视图换代 —— 陈旧条目从
  foreign_notified_view() 消失 + mark_dirty(full) 通知; 与逐 job 采纳支清理不冲突
- test_flag_consumed_once_no_runtime_rejudgment: flag 消费即清 —— 首轮判「保留 failed」
  后, 运行期物理现状变好(qB 现值改到 dst)也不重判(运行期新失败/新现状都不属于本口)
- test_qb_down_defers_reconcile_until_first_connect: qB 探不活(未连上)=> flag 保持不
  判不日志; 首连后的 tick 消费(§07: 无超时, qB 恒离线则账维持 failed 现状)
- test_hot_enable_derives_reconcile_flag: 热启用(enabled 假->真)经同一 _load_jobs
  推导 failed flag, 与 start() 启用分支同口径(§03.4)
### 端到端(生产 jr-a2ce556d0165 同型: pre-arm 自检 NEGATIVE 失败 -> 重启对账 -> 既有链)
覆盖率补测(2026-11-17, 消费窗/残留清理剩余分支; 补测轮到闸门绿):
- test_reconcile_tick_skips_job_changed_after_flag: 消费窗内账已变(flag 推导后相位被改/账被清)
  以账上现值为准不重判, 消费即清照常
- test_reconcile_tick_survives_rt_mutation_mid_consume: 消费循环内 rt 被动的防御形态(rt 缺失
  不炸, 账面判定照走; 替身直驱)
- test_reset_stale_terminal_journal_ts_unparseable_kept: 残留重置锚定面 —— journal 终相位但
  ts 不可解析: 锚定不上保守不清账不武装, 存疑告警限频一次
- test_consume_failed_journal_guards: journal failed 消费守卫 —— 相位已变/ reason 空都不转终态
- test_clear_stale_failed_journal_phase_changed_returns_false: 陈旧 failed 清理落手前再核 ——
  盘上现相位已不是 failed 不删返回 False

- test_prearm_failed_job_reenters_and_reruns_chain: pre-arm 失败(qb_side_check_failed,
  armed_at 恒 0)的 job 重启后对账重入 moved, 走既有链建链/穿透/武装收口(零新增逻辑)
"""

import os

import types

from dataclasses import replace

from auto_qb.core.modules import relocate_units as ru

from auto_qb.config.models import Config, RelocateConfig

from auto_qb.core.modules.relocate_mod import RelocateModule

from auto_qb.infra import relocate_journal as rj

from helpers import pin_disk_usage, relocate_env

from helpers import capture_logs

from relocate_exec_support import (
    _bare_mod,
    _fake_fs,
    _job,
    _run_ticks,
    _simulate_moved,
    _spy_spawn,
    _stub_probe_pass,
)

_PLAN_FILES = (("e00.mkv", 64), ("e01.mkv", 64))


def _failed_env(
    tmp_path,
    monkeypatch,
    *,
    mover_save="R:/dst",
    sizes={
        "e00.mkv": 64,
        "e01.mkv": 64
    },
    present=("e00.mkv", "e01.mkv"),
    armed_at=0.0,
    job_id="j1",
    qb_up=True,
    hashes=("HA", ),
):
    """启动对账用例的标准环境: failed job + store 快照/本机 stat 全替身 + qB 在线面

    mover_save 控制证据一(qB 现值 save_path); present/sizes 控制证据二(_fake_fs:
    present 之外的文件 exists 判 False, sizes 缺名/不等即 size 失配); qb_up=False 时
    _qb_up 探不活(缓存假值) —— 消费窗不开。job/rt flag 已登记, 判定走 on_task_line。
    """
    # _dst_ready 走 _native(dst, rel) 的本机拼接形, 前缀必须给全路径(裸文件名匹配不上)
    _fake_fs(
        monkeypatch,
        exists=False,
        exists_true_prefixes=tuple(os.path.join("R:/dst", name) for name in present),
        sizes=sizes,
    )
    by_hash = {h: types.SimpleNamespace(hash=h, save_path=mover_save, state="pausedUP") for h in hashes}
    mod = _bare_mod(
        store=types.SimpleNamespace(by_hash=by_hash),
        api=types.SimpleNamespace(client=types.SimpleNamespace(app_preferences=lambda **kw: None)),
        data_dir=str(tmp_path / "data"),
    )
    if not qb_up:
        mod._qb_up_cache = (mod._clock.monotonic(), False)
    job = _job(
        job_id,
        phase=ru.PHASE_FAILED,
        plan={
            "form": ru.FORM_FILE_LINKS,
            "files": [[rel, size] for rel, size in _PLAN_FILES]
        },
        armed_at=armed_at,
        hashes=hashes,
    )
    mod.register_job(job)
    mod._rt[job_id] = {"reconcile": True}
    return mod, job


# ---------------------------------------------------------------- 判定表四行(§03.1)


def test_row1_mover_at_dst_content_in_place_reenters_moved(tmp_path, monkeypatch):
    """行 1: mover save_path==dst 且 dst 内容全量在位 => 重入 moved(重入置 armed_at +
    rt stage=verify 既有链入口)+ flag 消费即清 + 一行对账日志"""
    mod, _job0 = _failed_env(tmp_path, monkeypatch)
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod.on_task_line()
    saved = mod.get_job("j1")
    assert saved.phase == ru.PHASE_MOVED, f"行 1 必须重入 moved: {saved.phase}"
    assert saved.armed_at > 0.0, "重入落账必须同步置 armed_at(§03.3: 闸对所有失败形态闭环)"
    assert saved.reason == _job0.reason and saved.last_error == _job0.last_error, "原文案保留供追溯(§07)"
    assert mod._rt["j1"].get("stage") == "verify", mod._rt["j1"]
    assert "reconcile" not in mod._rt["j1"], "flag 消费后必须清(每进程至多一次)"
    assert any("启动对账 1 笔: 重入 1 / 保留 0" in m for m in cap.messages), cap.messages


def test_row2_all_members_at_dst_reenters_moved(tmp_path, monkeypatch):
    """行 2: 全员 save_path==dst(armed_at==0, qB 侧手工补完形态)=> 重入 moved
    (全员==dst 蕴含证据一; 重入资格仍要过证据二全量在位)"""
    mod, _job0 = _failed_env(tmp_path, monkeypatch, hashes=("HA", "HB"))
    mod.on_task_line()
    saved = mod.get_job("j1")
    assert saved.phase == ru.PHASE_MOVED, f"行 2 必须重入 moved: {saved.phase}"
    assert saved.armed_at > 0.0, saved.armed_at


def test_row3_all_at_src_keeps_failed(tmp_path, monkeypatch):
    """行 3: 全员==src(搬迁段未完成形态)=> 保持 failed, armed_at 不动(账面=现实)"""
    mod, _job0 = _failed_env(tmp_path, monkeypatch, mover_save="R:/src")
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod.on_task_line()
    saved = mod.get_job("j1")
    assert saved.phase == ru.PHASE_FAILED, f"行 3 必须保持 failed: {saved.phase}"
    assert saved.armed_at == 0.0, saved.armed_at
    assert any("启动对账 1 笔: 重入 0 / 保留 1" in m for m in cap.messages), cap.messages


def test_row4_dst_content_mismatch_keeps_failed(tmp_path, monkeypatch):
    """行 4: mover==dst 但 dst 内容 size 不等(混合态由证据二排除)=> 保持 failed;
    证据不可得(mover 已不在 qB 快照)同格 —— 保守默认不改账"""
    mod, _job0 = _failed_env(tmp_path, monkeypatch, sizes={"e00.mkv": 64, "e01.mkv": 63})
    mod.on_task_line()
    saved = mod.get_job("j1")
    assert saved.phase == ru.PHASE_FAILED, f"size 失配必须保持 failed: {saved.phase}"
    assert saved.armed_at == 0.0, saved.armed_at

    mod2, _job1 = _failed_env(tmp_path, monkeypatch)
    del mod2._ctx.store.by_hash["HA"]  # 证据一取不到: mover 不在快照
    mod2.on_task_line()
    saved2 = mod2.get_job("j1")
    assert saved2.phase == ru.PHASE_FAILED, f"证据不可得必须保持 failed: {saved2.phase}"


# ---------------------------------------------------------------- 证据二全量真值(§03.2)


def test_evidence2_partial_missing_file_blocks_reentry(tmp_path, monkeypatch):
    """证据二部分缺失不放行: 一颗文件在位、另一颗缺失 => 保持 failed
    (B′ any-hit 口径会在 e00 命中即 positive —— 对账要全量真值, 不复用)"""
    mod, _job0 = _failed_env(tmp_path, monkeypatch, present=("e00.mkv", ))
    mod.on_task_line()
    saved = mod.get_job("j1")
    assert saved.phase == ru.PHASE_FAILED, f"部分在位必须保持 failed: {saved.phase}"
    assert saved.armed_at == 0.0, saved.armed_at


# ---------------------------------------------------------------- armed_at 前置闸(A1)


def test_gate_armed_at_blocks_reentry(tmp_path, monkeypatch):
    """前置闸: armed_at>0 的 failed 一律保持 failed(本生命周期自动链运行配额已用掉),
    即使双证据全成立也不重入 —— 不进判定表(防跨重启 churn, 出路 = 人审 re-issue)"""
    mod, _job0 = _failed_env(tmp_path, monkeypatch, armed_at=123.0)
    mod.on_task_line()
    saved = mod.get_job("j1")
    assert saved.phase == ru.PHASE_FAILED, f"armed_at>0 必须保持 failed: {saved.phase}"
    assert saved.armed_at == 123.0, "闸内不动账(armed_at 原值保留)"


def test_gate_closes_after_reentry_sets_armed_at(tmp_path, monkeypatch):
    """重入落账置位后闸关: 重入后再次失败(armed_at 已 >0)不随第二次推导再重入
    (第二次推导 = 热启用口径) —— A1 闭环, 单生命周期至多一次自动链运行"""
    mod, _job0 = _failed_env(tmp_path, monkeypatch)
    mod.on_task_line()
    first = mod.get_job("j1")
    assert first.phase == ru.PHASE_MOVED and first.armed_at > 0.0, (first.phase, first.armed_at)
    # 重入后自检再次真失败(未知形态): _fail 的 replace 不动 armed_at
    mod._fail(first, "qb_side_check_failed", "重入后再次失败")
    refailed = mod.get_job("j1")
    assert refailed.phase == ru.PHASE_FAILED and refailed.armed_at > 0.0, (refailed.phase, refailed.armed_at)
    # 第二次推导(模拟热启用重灌): 闸关, 不再自动重入
    mod._rt["j1"]["reconcile"] = True
    mod.on_task_line()
    saved = mod.get_job("j1")
    assert saved.phase == ru.PHASE_FAILED, f"重入置位后闸必须关: {saved.phase}"
    assert saved.armed_at == refailed.armed_at, "闸内不动账"


# ---------------------------------------------------------------- flag 无态推导与消费幂等(§03.4)


def test_load_jobs_derives_reconcile_flag_for_failed_only(tmp_path, monkeypatch):
    """_load_jobs 按 phase==failed 无态推导 rt["reconcile"](仿 rt["recover"] 既有模式):
    failed 推导 True, moving 推导 recover、done/cancelled 两者皆无; 既有 recover 键不回归"""
    mod = _bare_mod(data_dir=str(tmp_path / "data"))
    mod._ctx.state.data = {
        "relocate":
            {
                "jobs":
                    {
                        "jf": ru.job_to_dict(_job("jf", phase=ru.PHASE_FAILED)),
                        "jm": ru.job_to_dict(_job("jm", phase=ru.PHASE_MOVING)),
                        "jd": ru.job_to_dict(_job("jd", phase=ru.PHASE_DONE)),
                        "jc": ru.job_to_dict(_job("jc", phase=ru.PHASE_CANCELLED)),
                    }
            }
    }
    mod._load_jobs()
    assert mod._rt["jf"]["reconcile"] is True, mod._rt["jf"]
    assert mod._rt["jm"]["reconcile"] is False and mod._rt["jd"]["reconcile"] is False, \
        "只对 failed 推导为真(仿 recover 模式: 键恒在, 值按相位)"
    assert mod._rt["jc"]["reconcile"] is False, mod._rt["jc"]  # cancelled 不对账(G5(4))
    assert mod._rt["jm"]["recover"] is True, mod._rt["jm"]  # 既有恢复判据键不回归


def test_load_jobs_reconcile_adopts_terminal_and_cleans_foreign_entries(tmp_path):
    """_load_jobs 启动对账采纳支补挂 B2 终态清理(评审 major, journal 失窗恢复面):
    journal 即时落盘先于 state 周期刷盘 —— 失窗内盘上 state = 非终态 job + 陈旧
    kind=A/mismatch 通知条目; 重启按 journal 终相位回写(不经 _set_job), 采纳支清理该 job
    的 A/mismatch 条目、kind=B 保留, 随 _load_jobs 尾部单次 _persist 同窗落盘;
    无 foreign 段的采纳支零建键(黄金法则 2)"""
    mod = _bare_mod(data_dir=str(tmp_path / "data"))
    mod._ctx.state.data = {
        "relocate":
            {
                "jobs": {"ja": ru.job_to_dict(_job("ja", phase=ru.PHASE_ARMED, src="R:/old", dst="R:/new", created_at=100.0))},
                "foreign":
                    {
                        "notified":
                            {
                                # 形状与 _foreign_record_hit 同构(失窗前已记账)
                                "EA": {
                                    "root": "r:/old",
                                    "kind": "A",
                                    "job_id": "ja",
                                    "phase": "armed",
                                    "location": "R:/new",
                                    "first_seen": 1.0
                                },
                                "EM": {
                                    "root": "r:/old",
                                    "kind": "mismatch",
                                    "job_id": "ja",
                                    "phase": "armed",
                                    "location": "R:/new",
                                    "first_seen": 1.0
                                },
                                "EB": {  # 合成形态: 钉 kind 分流(D4: B 一律保留)
                                    "root": "r:/old",
                                    "kind": "B",
                                    "job_id": "ja",
                                    "phase": "done",
                                    "location": "R:/new",
                                    "first_seen": 1.0
                                },
                            }
                    },
            }
    }
    # 盘上 journal 已即时落终相位(ts >= created_at: 本世锚定采纳; state 刷盘前的失窗现场)
    rj.write_journal(mod._data_dir(), "ja", {"phase": "done", "ts": 200.0})
    mod._load_jobs()
    assert mod.get_job("ja").phase == ru.PHASE_DONE, "journal 终相位回写(采纳支)"
    notified = mod._state_foreign_notified()
    assert "EA" not in notified and "EM" not in notified, "陈旧 A/mismatch 条目随回写清理(1326 恢复面)"
    assert notified["EB"]["kind"] == "B", "kind=B 一律保留(D4)"
    assert mod._ctx.state.data["relocate"]["jobs"]["ja"]["phase"] == ru.PHASE_DONE, \
        "清理与回写随 _load_jobs 尾部单次 _persist 同窗落盘"
    # 黄金法则 2: 账不在(无 foreign 段)的采纳支零建键
    mod2 = _bare_mod(data_dir=str(tmp_path / "data2"))
    mod2._ctx.state.data = {
        "relocate": {
            "jobs": {
                "jb": ru.job_to_dict(_job("jb", phase=ru.PHASE_ARMED, created_at=50.0))
            }
        }
    }
    rj.write_journal(mod2._data_dir(), "jb", {"phase": "cancelled", "ts": 60.0})
    mod2._load_jobs()
    assert mod2.get_job("jb").phase == ru.PHASE_CANCELLED
    assert "foreign" not in mod2._ctx.state.data["relocate"], "采纳支不得 materialize relocate.foreign"


# ---------------------------------------------------------------- 启动守阵(S2, 阶段 2: _load_jobs 尾部接线)


def _foreign_entry(kind, job_id, phase="armed", root="r:/old", location="R:/new"):
    """通知账条目(形状与 _foreign_record_hit 同构; 键名在用例里自定, 不一定是真实 hash)"""
    return {
        "root": root,
        "kind": kind,
        "job_id": job_id,
        "phase": phase,
        "location": location,
        "first_seen": 1.0,
    }


def _startup_mod(tmp_path, *, jobs, notified=None, foreign_torrent=True, dry_run=False):
    """裸模块 + 内存直写 state 账: foreign 段按 notified 是否在决定建不建(无账守阵的前提)"""
    mod = _bare_mod(
        relocate=RelocateConfig(enabled=True, foreign_torrent=foreign_torrent),
        data_dir=str(tmp_path / "data"),
    )
    data = {"relocate": {"jobs": {jid: ru.job_to_dict(job) for jid, job in jobs.items()}}}
    if notified is not None:
        data["relocate"]["foreign"] = {"notified": dict(notified)}
    mod._ctx.state.data = data
    if dry_run:
        mod._dry = True
    return mod


def test_load_jobs_cleans_stale_notified_entries_on_startup(tmp_path):
    """启动扫全表: job 不在/已终态的 A+mismatch 清, B 与活跃 job 的 A/mismatch 留;
    与上面 journal 采纳支逐 job 清理并存(逐 job 先跑, 本守阵兜底全表)"""
    mod = _startup_mod(
        tmp_path,
        jobs={
            "ja": _job("ja", phase=ru.PHASE_ARMED),
            "jd": _job("jd", phase=ru.PHASE_DONE),
        },
        notified={
            "OA": _foreign_entry("A", "gone"),
            "OM": _foreign_entry("mismatch", "gone"),
            "DA": _foreign_entry("A", "jd"),
            "DM": _foreign_entry("mismatch", "jd"),
            "OB": _foreign_entry("B", "gone", phase="done"),
            "AA": _foreign_entry("A", "ja"),
            "AM": _foreign_entry("mismatch", "ja"),
        },
    )
    mod._load_jobs()
    notified = mod._ctx.state.data["relocate"]["foreign"]["notified"]
    assert "OA" not in notified and "OM" not in notified, "job 不在 _jobs: A/mismatch 清"
    assert "DA" not in notified and "DM" not in notified, "job 已终态: A/mismatch 清"
    assert notified["OB"]["kind"] == "B", "kind=B 一律保留(D4)"
    assert "AA" in notified and "AM" in notified, "活跃 job 的 A/mismatch 保留(前提仍在途)"
    assert mod.get_job("ja").phase == ru.PHASE_ARMED, "清理不碰 job 账"


def test_load_jobs_dry_run_zero_writes(tmp_path, monkeypatch):
    """dry-run 零写账: 账内容不变, 不调清理/换代, 不写盘(与 _migrate_legacy_accounts 同判)"""
    mod = _startup_mod(
        tmp_path,
        jobs={"ja": _job("ja", phase=ru.PHASE_ARMED)},
        notified={"OA": _foreign_entry("A", "gone")},
        dry_run=True,
    )
    calls = []
    monkeypatch.setattr(mod, "_foreign_cleanup_stale_notified", lambda: calls.append("cleanup"))
    monkeypatch.setattr(mod, "_foreign_publish_view", lambda: calls.append("publish"))
    saves = []
    mod._ctx.state.save = lambda: saves.append("save")
    before = dict(mod._state_foreign_notified_view())
    mod._load_jobs()
    assert mod._state_foreign_notified_view() == before, "dry-run 账内容不变"
    assert calls == [], "dry-run 不调清理/换代"
    assert saves == [], "dry-run 不写盘"


def test_load_jobs_repeat_idempotent(tmp_path):
    """重复 _load_jobs 零副作用: 第二轮零删除零日志, 发布视图引用恒稳(内容相等不换代)"""
    mod = _startup_mod(
        tmp_path,
        jobs={"ja": _job("ja", phase=ru.PHASE_ARMED)},
        notified={
            "OA": _foreign_entry("A", "gone"),
            "OB": _foreign_entry("B", "gone", phase="done"),
        },
    )
    mod._load_jobs()
    after_first = dict(mod._ctx.state.data["relocate"]["foreign"]["notified"])
    view = mod.foreign_notified_view()
    assert set(after_first) == {"OB"}, "首轮清掉孤儿 A"
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod._load_jobs()
    assert mod._ctx.state.data["relocate"]["foreign"]["notified"] == after_first, "第二轮零改动"
    assert not [m for m in cap.messages if "启动接管清理孤儿账" in m], "第二轮零命中零日志"
    assert mod.foreign_notified_view() is view, "内容相等不换代(引用恒稳)"


def test_load_jobs_foreign_off_no_account_no_materialize(tmp_path):
    """黄金法则 2: foreign_torrent=false 且无账时启动不 materialize relocate.foreign.notified"""
    mod = _startup_mod(
        tmp_path,
        jobs={"ja": _job("ja", phase=ru.PHASE_ARMED)},
        foreign_torrent=False,
    )
    mod._load_jobs()
    assert "foreign" not in mod._ctx.state.data["relocate"], "无账不建键(只读视图守卫)"
    assert set(mod.foreign_notified_view()) == set()
    # 对照: 账真已在时 foreign_torrent=false 仍照清(清理函数不受 foreign_torrent 限制)
    mod2 = _startup_mod(
        tmp_path,
        jobs={"ja": _job("ja", phase=ru.PHASE_ARMED)},
        notified={"OA": _foreign_entry("A", "gone")},
        foreign_torrent=False,
    )
    mod2._load_jobs()
    assert not mod2._state_foreign_notified_view(), "foreign 关但账已在: 清理照跑"


def test_load_jobs_publishes_view_after_cleanup(tmp_path):
    """清理后 WebUI 只读视图换代: 陈旧条目从 foreign_notified_view() 消失 + mark_dirty(full)"""
    mod = _startup_mod(
        tmp_path,
        jobs={"ja": _job("ja", phase=ru.PHASE_ARMED)},
        notified={
            "OA": _foreign_entry("A", "gone"),
            "OB": _foreign_entry("B", "gone", phase="done"),
        },
    )
    mod._foreign_publish_view()  # 预发布含陈旧条目的旧视图(模拟上一拍)
    before = mod.foreign_notified_view()
    assert "OA" in before, "旧视图确有陈旧条目"
    dirty = []
    mod._ctx.web = types.SimpleNamespace(mark_dirty=lambda full=False, reason="": dirty.append((full, reason)))
    mod._load_jobs()
    view = mod.foreign_notified_view()
    assert view is not before, "清完换代(引用变化)"
    assert "OA" not in view and "OB" in view, "陈旧条目消失, B 保留"
    assert (True, "relocate_foreign") in dirty, "换代通知 Web 刷视图"


def test_flag_consumed_once_no_runtime_rejudgment(tmp_path, monkeypatch):
    """flag 消费即清: 首轮判「保留 failed」后, 运行期物理现状变好(qB 现值改到 dst)
    也不重判 —— 每进程每笔至多消费一次(幂等, 黄金法则 1)"""
    mod, _job0 = _failed_env(tmp_path, monkeypatch, mover_save="R:/src")
    mod.on_task_line()
    assert mod.get_job("j1").phase == ru.PHASE_FAILED
    assert "reconcile" not in mod._rt["j1"], "保留支同样消费即清"
    mod._ctx.store.by_hash["HA"].save_path = "R:/dst"  # 运行期现状变好
    mod.on_task_line()
    mod.on_task_line()
    assert mod.get_job("j1").phase == ru.PHASE_FAILED, "flag 已消费: 运行期不重判"


def test_qb_down_defers_reconcile_until_first_connect(tmp_path, monkeypatch):
    """qB 探不活(未连上)=> flag 保持不判(§07: 无超时, 首连后执行); 首连后的 tick
    消费 —— qB 恒离线则账维持 failed(现状不变)"""
    mod, _job0 = _failed_env(tmp_path, monkeypatch, qb_up=False)
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod.on_task_line()
    assert mod.get_job("j1").phase == ru.PHASE_FAILED
    assert mod._rt["j1"].get("reconcile") is True, "未连上不得消费 flag"
    assert not any("启动对账" in m for m in cap.messages), "未连上不出对账日志"
    mod._qb_up_cache = None  # 模拟首连(缓存作废, 下一探活成功)
    mod.on_task_line()
    assert mod.get_job("j1").phase == ru.PHASE_MOVED, "首连后的 tick 必须消费"


def test_hot_enable_derives_reconcile_flag(tmp_path, monkeypatch):
    """热启用(enabled 假->真)经同一 _load_jobs 推导 failed flag, 与 start() 启用分支
    同口径(§03.4) —— disabled 启动不恢复账, 热启用补灌后对账待判"""
    pin_disk_usage(monkeypatch)
    _stub_probe_pass(monkeypatch)
    mgr, _client, _src, dst, _content, files = relocate_env(tmp_path, state="uploading")
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    job_id = mod.relocate_execute(["HA"], dst)[0]["job_id"]
    _simulate_moved(mgr, dst, files, _content)
    # 直接把账改成 pre-arm 失败终态(不必真跑失败链): 模拟历史 failed 残留
    mod._set_job(replace(mod.get_job(job_id), phase=ru.PHASE_FAILED, reason="qb_side_check_failed", armed_at=0.0))

    mgr.config.relocate = RelocateConfig(enabled=False)
    mod2 = RelocateModule(mgr.ctx)
    mod2.start(mgr.ctx, dry_run=False)
    assert mod2.get_job(job_id) is None, "开关关启动不恢复账(R15)"

    old, new = Config(), Config()
    new.relocate = RelocateConfig(enabled=True)
    res = mod2.apply(old, new)
    assert res.action == "reloaded" and "恢复 job 1 条" in res.detail, res
    assert mod2._rt[job_id]["reconcile"] is True, "热启用同口径推导对账 flag"
    assert mod2.get_job(job_id).phase == ru.PHASE_FAILED, mod2.get_job(job_id).phase


# ---------------------------------------------------------------- 端到端(生产 jr-a2ce556d0165 同型)


def test_prearm_failed_job_reenters_and_reruns_chain(tmp_path, monkeypatch):
    """端到端: pre-arm 失败(qb_side_check_failed, armed_at 恒 0)的 job 重启后对账重入
    moved, 走既有链建链(幂等)/穿透/武装收口 —— 零新增逻辑(生产 Blood 账收敛路径)"""
    pin_disk_usage(monkeypatch)
    _stub_probe_pass(monkeypatch)
    mgr, _client, _src, dst, content, files = relocate_env(tmp_path, state="uploading")
    mod = mgr.host.get("relocate")
    _spy_spawn(mod, [])
    job_id = mod.relocate_execute(["HA"], dst)[0]["job_id"]
    _simulate_moved(mgr, dst, files, content)
    # 造 pre-arm 失败形态: qB 侧自检 NEGATIVE -> failed, armed_at 恒 0(_fail 不置它)
    mod._qb_side_check = lambda job, rt: "failed"
    _run_ticks(mod, 8)
    failed = mod.get_job(job_id)
    assert failed.phase == ru.PHASE_FAILED and failed.reason == "qb_side_check_failed", (failed.phase, failed.reason)
    assert failed.armed_at == 0.0, "pre-arm 失败 armed_at 恒 0(重入置位才能让闸闭环的前提)"

    # 重启: 新会话恢复账 -> flag 推导 -> 首个 qB 在线 tick 对账重入 -> 既有链走到武装
    mod2 = RelocateModule(mgr.ctx)
    mod2._spawn_daemon = lambda *a, **k: None
    mod2.start(mgr.ctx, dry_run=False)
    assert mod2._rt[job_id]["reconcile"] is True, "启动恢复必须推导对账 flag"
    _run_ticks(mod2, 8)
    armed = mod2.get_job(job_id)
    assert armed.phase == ru.PHASE_ARMED, f"重入后必须经既有链武装收口: {armed.phase}"
    assert armed.armed_at > 0.0, armed.armed_at


# ---------- 覆盖率补测(2026-11-17, 启动对账消费窗/残留清理剩余分支): 行为有意义面 ----------


def test_reconcile_tick_skips_job_changed_after_flag(tmp_path, monkeypatch):
    """消费窗内账已变(flag 推导后、消费前相位被改/账被清): 以账上现值为准不重判,
    消费即清照常执行(119/123/128 面)"""
    mod, job = _failed_env(tmp_path, monkeypatch)
    # 形态一: flag 在但账相位已不是 failed(撤销/re-issue 改相位) -> 跳过重判
    mod._set_job(replace(job, phase=ru.PHASE_MOVING))
    mod._startup_reconcile_tick()
    assert mod.get_job(job.job_id).phase == ru.PHASE_MOVING, "账已变: 不凭旧 flag 重判"
    assert mod._rt[job.job_id].get("reconcile") is None, "消费即清照常"
    # 形态二: 账已不在 _jobs(rt 还挂着) -> 跳过不炸
    mod._rt[job.job_id] = {"reconcile": True}
    mod._jobs.pop(job.job_id)
    mod._startup_reconcile_tick()


def test_reconcile_tick_survives_rt_mutation_mid_consume(tmp_path, monkeypatch):
    """消费循环内 rt 被动的防御形态(119->121 / 128->130): rt 缺失不炸, 账面判定照走。
    替身直驱: _qb_up 探活后/判定返回前摘走 rt(并发外的单写线程下不应发生, 真发生不炸)"""
    mod, job = _failed_env(tmp_path, monkeypatch)
    mod._rt["j2"] = {"reconcile": True}
    mod._jobs["j2"] = replace(job, job_id="j2")
    orig_qb_up = mod._qb_up

    def _qb_up_pop():
        orig_qb_up()
        mod._rt.pop("j2", None)  # 消费循环开始后 j2 的 rt 被摘走 -> 119 rt None
        return True

    monkeypatch.setattr(mod, "_qb_up", _qb_up_pop)
    mod._startup_reconcile_tick()  # j2: rt None 走 121 -> job failed -> 判定; 不炸
    # 形态二: 判定通过后 rt 被摘走 -> 128 rt None 不炸, 重入落账照常
    mod2, job2 = _failed_env(tmp_path, monkeypatch, mover_save="R:/dst")
    monkeypatch.setattr(mod2, "_startup_reconcile_one", lambda j: mod2._rt.pop(j.job_id, None) or True)
    mod2._startup_reconcile_tick()
    assert mod2.get_job(job2.job_id).phase == ru.PHASE_MOVED, "rt 缺失不挡重入落账"


def test_reset_stale_terminal_journal_ts_unparseable_kept(tmp_path):
    """残留重置锚定面: journal 终相位但 ts 不可解析 -> 锚定不上保守不清账不武装
    (返回 False, 证据行不落, journal 原样)"""
    data_dir = str(tmp_path / "data")
    os.makedirs(data_dir, exist_ok=True)
    rj.write_journal(data_dir, "j1", {"phase": "done", "ts": "not-a-number"})
    mod = _bare_mod(data_dir=data_dir)
    job = _job("j1", phase=ru.PHASE_ARMED, created_at=1000.0)
    rt = {}
    assert mod._reset_stale_terminal_journal(job, rt) is False, "锚定不上: 本拍不清"
    assert rt.get("journal_terminal_suspect_warned") is True, "存疑告警一次"
    assert (rj.read_journal(data_dir, "j1") or {}).get("phase") == "done", "journal 原样"
    # 幂等: 告警限频, 二次不再刷
    with capture_logs() as cap:
        mod._reset_stale_terminal_journal(job, rt)
    assert not [x for x in cap.records if "无法确证" in x.message], "限频一次"


def test_consume_failed_journal_guards(tmp_path):
    """journal failed 消费守卫: 相位已不是 failed(盘上现值为准)与 reason 空(证据形变)
    都不转终态(job 原样)"""
    data_dir = str(tmp_path / "data")
    os.makedirs(data_dir, exist_ok=True)
    mod = _bare_mod(data_dir=data_dir)
    job = _job("j1", phase=ru.PHASE_ARMED)
    mod._jobs["j1"] = job
    # 相位已变: 消费瞬间账已变, 不凭旧读误判
    rj.write_journal(data_dir, "j1", {"phase": "armed", "ts": 1.0})
    mod._consume_failed_journal(job)
    assert mod.get_job("j1").phase == ru.PHASE_ARMED
    # failed 但 reason 空: 证据形变, 回下拍重判
    rj.write_journal(data_dir, "j1", {"phase": "failed", "reason": "", "ts": 1.0})
    mod._consume_failed_journal(job)
    assert mod.get_job("j1").phase == ru.PHASE_ARMED, "证据形变不转终态"


def test_clear_stale_failed_journal_phase_changed_returns_false(tmp_path):
    """陈旧 failed 清理落手前再核: 盘上现相位已不是 failed -> 不删返回 False(下拍重判)"""
    data_dir = str(tmp_path / "data")
    os.makedirs(data_dir, exist_ok=True)
    rj.write_journal(data_dir, "j1", {"phase": "armed", "ts": 1.0})
    mod = _bare_mod(data_dir=data_dir)
    assert mod._clear_stale_failed_journal(_job("j1", phase=ru.PHASE_ARMED), {}) is False
    assert (rj.read_journal(data_dir, "j1") or {}).get("phase") == "armed", "journal 原样"
