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
- test_flag_consumed_once_no_runtime_rejudgment: flag 消费即清 —— 首轮判「保留 failed」
  后, 运行期物理现状变好(qB 现值改到 dst)也不重判(运行期新失败/新现状都不属于本口)
- test_qb_down_defers_reconcile_until_first_connect: qB 探不活(未连上)=> flag 保持不
  判不日志; 首连后的 tick 消费(§07: 无超时, qB 恒离线则账维持 failed 现状)
- test_hot_enable_derives_reconcile_flag: 热启用(enabled 假->真)经同一 _load_jobs
  推导 failed flag, 与 start() 启用分支同口径(§03.4)
### 端到端(生产 jr-a2ce556d0165 同型: pre-arm 自检 NEGATIVE 失败 -> 重启对账 -> 既有链)
- test_prearm_failed_job_reenters_and_reruns_chain: pre-arm 失败(qb_side_check_failed,
  armed_at 恒 0)的 job 重启后对账重入 moved, 走既有链建链/穿透/武装收口(零新增逻辑)
"""

import os

import types

from dataclasses import replace

from auto_qb.core.modules import relocate_units as ru

from auto_qb.config.models import Config, RelocateConfig

from auto_qb.core.modules.relocate_mod import RelocateModule

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
        store=types.SimpleNamespace(by_hash=by_hash, relocating_hashes=set()),
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
