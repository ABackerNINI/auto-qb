"""test_relocate_migration 测试计划: S1b 旧账迁移器(D8 + R1, 计划 26-11-15-2340 §03.5/§07-R1)

重构版上线时自动迁移存量账: 在途任务由既有启动对账接管跑完(迁移器不改变其相位语义);
历史终态/改道前任转新格式保留, 一条不丢; 迁移失败 fail-fast 启动拦截 + 回滚备份。

## 测试计划(每个测试函数一条)
- test_migration_converts_legacy_redirect_chain_zero_loss: 旧改道链样本(祖父辈 J0 +
  前任 J1 携带 plan.superseded_from, 在途链顶 J2 混合) -> _load_jobs 迁移: 三账一条不丢,
  前任转 superseded 历史(原始落点还原进 dst, superseded_from 摘除), 移交条目展平归集到
  链顶 plan.inherited, 前任成员并入 extra_members, journal 投影翻 superseded(已终态的
  不动), 在途链顶相位语义原样(交既有启动对账接管), model_version 盖章, 备份目录落盘。
- test_migration_armed_successor_spec_rewritten_and_daemon_converges: 继任已 armed
  (旧机器时代 spec 已落盘, 不含前任成员/extra_srcs)迁移后断言继任 spec 被重写
  (members 并入前任成员、extra_srcs 取移交条目 src 根), 且 daemon 续跑按重写后的
  spec 把前任未完成改写收敛(成员 fastresume 落到继任 dst)—— armed 不重走 _arm,
  不重写则前任改写失主、继任删移交别名后成员断粮(评审轮 2 major-1)。
- test_migration_failure_rolls_back_and_blocks_startup: journal 翻相注入失败(第一笔
  真实落盘、第二笔抛) -> RuntimeError 穿透 _load_jobs(start_all 无捕获, fail-fast
  契约), 已真实翻相的 jr-0 journal 字节级还原(回滚承压断言), 内存 jobs_box 还原
  迁移前快照(无半迁移残留), state.json 未被半迁移态覆盖。
- test_hot_enable_migration_failure_rejected_and_state_consistent: 热启用(apply)路径
  注入失败 -> 回执 action=rejected 明示重启, 配置缓存回退旧段(禁用现场), 内存态与
  盘面一致(无半迁移残留), stop() 补写闸未开(评审轮 2 major-2); 且模拟内核 L0 已换
  ctx.config 的形态断言拒绝后 relocate_execute 被禁用闸收口, 成功 _load_jobs 清标志
  (评审轮 3 major-R2-1)。
- test_migration_backup_failure_blocks_startup_without_writes: 备份阶段 OSError 注入
  -> 统一包成 RuntimeError(启动拦截 + apply 路径 rejected 回执), 无转换写面(journal/
  state 原样, 仅内存快照还原)(评审轮 3 minor-R2-2)。
- test_migration_successor_cycle_orphans_both: 环形继任(J0<->J1 互为继任)按孤儿收口:
  条目不归集(无 inherited)、无 superseded_by=自身、两账零丢失转 superseded
  (评审轮 2 minor-5)。
- test_migration_marked_state_skips: model_version 已盖章的 state 不再迁移(幂等),
  legacy 字段残留原样(新代码不读)。
- test_migration_no_legacy_stamps_marker_without_backup: 有账无 legacy 标记 -> 只盖章,
  不建备份目录。
- test_migration_dry_run_skips: dry-run 启动不动手(迁移留给下一次真启动)。
"""

import json
import os
import types

import pytest

from auto_qb.config.models import RelocateConfig

from auto_qb.core import fastresume as frmod

from auto_qb.infra import relocate_journal as rj

from auto_qb.core.modules import relocate_units as ru

from test_recycle_daemon import HOST, PORT, _fr_path, _member_fixture, _run, _stub_qb

from relocate_exec_support import _bare_mod


def _legacy_job(jid, src, dst, phase, updated, hashes=("HA", "HB"), extra_hashes=()):
    """旧改道机器的账面形状: dst 已被翻转, plan.superseded_from 记原始落点"""
    return {
        "job_id": jid,
        "hashes": list(hashes) + list(extra_hashes),
        "mover": "HA",
        "src": src,
        "dst": dst,
        "scope": src,
        "alias_kind": "dir",
        "alias_paths": [f"{src}/alias"],
        "phase": phase,
        "reason": "",
        "created_at": 1000.0,
        "armed_at": 0.0,
        "updated_at": updated,
        "resume_hashes": [],
        "resume_pending": [],
        "resume_retries": 0,
        "attempts": 0,
        "last_error": "",
        "plan": {
            "form": "dir_alias",
            "link_kind": "junction"
        },
        "move_issued": True,
        "tag_on": False,
        "origin": "web",
        "absent_counts": [],
    }


def _legacy_box():
    """旧改道链样本: J0(S0->A) 与 J1(A->B) 均被改道机器翻转到 C, J2(B->C) 在途链顶

    J0 是祖父辈(J1 的前任, 被 J2 的改道波及二次翻转), J1 是 J2 的直接前任;
    J0 额外携带一个混合成员 HX(改写义务归集的断言面)。
    """
    j0 = _legacy_job("jr-0", "R:/s0", "R:/dstC", "rewritten", 100.0, extra_hashes=("HX", ))
    j0["plan"]["superseded_from"] = "R:/dstA"
    j1 = _legacy_job("jr-1", "R:/dstA", "R:/dstC", "armed", 200.0)
    j1["plan"]["superseded_from"] = "R:/dstB"
    j2 = _legacy_job("jr-2", "R:/dstB", "R:/dstC", "armed", 300.0)
    return {"jr-0": j0, "jr-1": j1, "jr-2": j2}


def _migration_env(tmp_path, box, journals=None):
    """真实盘面环境: state.json 落盘 + relocate 目录 journal 预置; 返回 (mod, data_dir, state_path)"""
    data_dir = str(tmp_path / "data")
    os.makedirs(os.path.join(data_dir, "relocate"), exist_ok=True)
    state_path = tmp_path / "state.json"
    payload = {"relocate": {"jobs": box, "probe_salt": "s1"}}
    state_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    for jid, body in (journals or {}).items():
        rj.write_journal(data_dir, jid, body)
    mod = _bare_mod(data_dir=data_dir)
    mod._ctx.state = types.SimpleNamespace(
        data=json.loads(state_path.read_text(encoding="utf-8")), state_file=str(state_path)
    )
    return mod, data_dir, state_path


def test_migration_converts_legacy_redirect_chain_zero_loss(tmp_path):
    """旧改道链 -> 单活模型表示: 零丢失 + 展平归集 + journal 翻相 + 在途可接管"""
    box = _legacy_box()
    journals = {
        "jr-0": {
            "phase": "rewritten",
            "rewrites": {
                "HA": {
                    "status": "rewritten"
                }
            },
            "ts": 1500.0
        },
        "jr-1": {
            "phase": "done",
            "ts": 1400.0
        },  # 已终态投影: 迁移不动
    }
    mod, data_dir, state_path = _migration_env(tmp_path, box, journals)

    n = mod._load_jobs()

    assert n == 3, "一条不丢: 三账全部恢复"
    data = mod._ctx.state.data["relocate"]
    assert data["model_version"] == ru.MODEL_VERSION, "版本标记盖章"
    # 前任账转 superseded 历史: 原始落点还原, 改道字段摘除
    j0 = data["jobs"]["jr-0"]
    j1 = data["jobs"]["jr-1"]
    for d, old in ((j0, "R:/dstA"), (j1, "R:/dstB")):
        assert d["phase"] == ru.PHASE_SUPERSEDED, d["job_id"]
        assert d["reason"] == "migrated_superseded"
        assert d["dst"] == old, "原始落点还原进账面 dst"
        assert "superseded_from" not in (d.get("plan") or {}), "改道字段摘除"
    # 移交条目展平归集到链顶 J2(祖父辈不失主), 前任成员并入改写清单
    j2 = data["jobs"]["jr-2"]
    entries = {e["job_id"]: e for e in j2["plan"]["inherited"]}
    assert set(entries) == {"jr-0", "jr-1"}, "展平归集: 祖父辈 + 前任都在链顶"
    assert entries["jr-0"]["dst"] == "R:/dstA" and entries["jr-1"]["dst"] == "R:/dstB"
    assert entries["jr-1"]["alias_paths"] == ["R:/dstA/alias"], "前任别名清单随条目移交"
    assert j2["plan"].get("extra_members") == ["HX"], "前任成员改写义务随链归集"
    # 前任账不再持有自己的条目(已上提)
    assert not (j0.get("plan") or {}).get("inherited")
    assert not (j1.get("plan") or {}).get("inherited")
    # journal 投影: 非终态翻 superseded(+superseded_by), 已终态不动
    flipped = rj.read_journal(data_dir, "jr-0")
    assert flipped["phase"] == ru.PHASE_SUPERSEDED and flipped["superseded_by"] == "jr-2"
    assert flipped["rewrites"]["HA"]["status"] == "rewritten", "读-改-写保留既有账"
    assert rj.read_journal(data_dir, "jr-1")["phase"] == "done", "已终态投影不动"
    # 在途链顶相位语义原样(交既有启动对账接管), 不入迁移面
    assert mod.get_job("jr-2").phase == ru.PHASE_ARMED
    # 备份目录落盘(R1)
    backup_root = os.path.join(data_dir, "relocate-migration-backup")
    assert os.path.isdir(backup_root) and os.listdir(backup_root), "迁移前备份落盘"


def test_migration_armed_successor_spec_rewritten_and_daemon_converges(tmp_path, monkeypatch):
    """已 armed 继任: 迁移重写其 spec(members+extra_srcs), daemon 续跑收敛前任改写(评审轮 2 major-1)"""
    backup = tmp_path / "BT_backup"
    root_a, root_b, root_c, root_d = (str(tmp_path / n) for n in ("rootA", "rootB", "rootC", "rootD"))
    h_a = _member_fixture(backup, b"m-a", root_a)  # 前任成员, fastresume 指向 A
    h_b = _member_fixture(backup, b"m-b", root_b)  # 继任自有成员, fastresume 指向 B
    h_x = _member_fixture(backup, b"m-x", root_a)  # 前任混合成员(不在继任 hashes)
    box = {
        # 旧机器形态: J0(A->B) 与 J1(B->C) 均被翻转到 D
        "jr-0": _legacy_job("jr-0", root_a, root_d, "rewritten", 100.0, hashes=(h_a, h_b, h_x)),
        "jr-1": _legacy_job("jr-1", root_b, root_d, "armed", 200.0, hashes=(h_a, h_b, h_x)),
        "jr-2": _legacy_job("jr-2", root_c, root_d, "armed", 300.0, hashes=(h_a, h_b)),
    }
    box["jr-0"]["plan"]["superseded_from"] = root_b
    box["jr-1"]["plan"]["superseded_from"] = root_c
    data_dir = str(tmp_path / "data")
    os.makedirs(os.path.join(data_dir, "relocate"), exist_ok=True)
    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps({"relocate": {"jobs": box}}, ensure_ascii=False), encoding="utf-8")
    rj.write_journal(data_dir, "jr-0", {"phase": "rewritten", "ts": 1500.0})
    rj.write_journal(data_dir, "jr-1", {"phase": "armed", "ts": 1500.0})
    # 继任已 armed: 旧机器时代 _arm 落盘的 spec(members 只有自有成员, 无 extra_srcs)
    rj.write_spec(
        data_dir, "jr-2", {
            "job_id": "jr-2",
            "src": root_c,
            "dst": root_d,
            "scope": root_c,
            "hashes": [h_a, h_b],
            "host": HOST,
            "port": PORT,
            "alias_paths": [],
            "files": [],
            "bt_backup": str(backup),
            "members": [{
                "hash_v1": h_a,
                "hash_v2": ""
            }, {
                "hash_v1": h_b,
                "hash_v2": ""
            }],
        }
    )
    mod = _bare_mod(data_dir=data_dir)
    mod._ctx.state = types.SimpleNamespace(
        data=json.loads(state_path.read_text(encoding="utf-8")), state_file=str(state_path)
    )
    mod._ctx.config = types.SimpleNamespace(relocate=RelocateConfig(enabled=True), data_dir=data_dir)

    mod._load_jobs()

    # 继任 spec 被重写: members 并入前任成员(h_x), extra_srcs 取移交条目 src 根(A/B 根)
    spec = rj.read_spec(data_dir, "jr-2")
    member_v1 = {m["hash_v1"] for m in spec["members"] if isinstance(m, dict)}
    assert {h_a, h_b, h_x} <= member_v1, "前任成员并入继任 spec 改写清单"
    assert set(spec["extra_srcs"]) == {root_a, root_b}, "extra_srcs = 移交条目 src 根"
    # 账面照常: 前任转历史, 继任在途原样
    assert mod.get_job("jr-0").phase == ru.PHASE_SUPERSEDED
    assert mod.get_job("jr-2").phase == ru.PHASE_ARMED
    # daemon 续跑(qB 下线窗口)按重写后的 spec 收敛前任未完成改写
    state = {"up": False}
    _stub_qb(monkeypatch, state)
    assert _run(data_dir) == "idle"
    rw = rj.read_rewrites(data_dir, "jr-2")
    for h in (h_a, h_b, h_x):
        assert rw[h]["status"] == "rewritten", f"{h} 改写收敛"
    fr_x = _fr_path(tmp_path, h_x)
    val, _pos = frmod.bdecode(fr_x.read_bytes())
    assert val[b"save_path"] == (root_d + "\\m-x").encode("utf-8"), "前任混合成员落到继任 dst"


def test_migration_failure_rolls_back_and_blocks_startup(tmp_path, monkeypatch):
    """迁移注入失败(第一笔真实落盘、第二笔抛): fail-fast + 已翻相 journal 字节级还原"""
    box = _legacy_box()
    journals = {"jr-0": {"phase": "rewritten", "ts": 1500.0}, "jr-1": {"phase": "armed", "ts": 1500.0}}
    mod, data_dir, state_path = _migration_env(tmp_path, box, journals)
    state_before = state_path.read_bytes()
    journal0_before = open(rj.journal_path(data_dir, "jr-0"), "rb").read()
    journal1_before = open(rj.journal_path(data_dir, "jr-1"), "rb").read()

    real = rj.write_journal
    calls = {"n": 0}

    def _flaky(*a, **k):
        calls["n"] += 1
        if calls["n"] >= 2:
            raise RuntimeError("boom")  # jr-0 已真实翻相落盘后, jr-1 失败
        return real(*a, **k)

    monkeypatch.setattr(rj, "write_journal", _flaky)
    with pytest.raises(RuntimeError, match="旧账迁移失败"):
        mod._load_jobs()
    monkeypatch.setattr(rj, "write_journal", real)

    assert calls["n"] >= 2, "注入点在第二笔盘面写(第一笔已真实落盘)"
    assert open(rj.journal_path(data_dir, "jr-0"), "rb").read() == journal0_before, \
        "已真实翻相的 jr-0 journal 被回滚字节级还原(承压断言)"
    assert open(rj.journal_path(data_dir, "jr-1"), "rb").read() == journal1_before
    # 内存 jobs_box 还原迁移前快照(热启用吞异常面的分叉洞, major-2)
    mem = mod._ctx.state.data["relocate"]["jobs"]
    assert mem["jr-0"]["phase"] == "rewritten" and mem["jr-0"]["plan"]["superseded_from"] == "R:/dstA", \
        "内存账还原迁移前形态(无半迁移残留)"
    assert "model_version" not in mod._ctx.state.data["relocate"], "失败路径不盖章"
    # state.json 未被半迁移态覆盖(迁移写盘只发生在 state 服务周期, 失败路径无写)
    assert state_path.read_bytes() == state_before
    backup_root = os.path.join(data_dir, "relocate-migration-backup")
    stamps = os.listdir(backup_root)
    assert stamps, "失败前已落备份(回滚依据)"
    backup_state = json.loads(open(os.path.join(backup_root, stamps[0], "state.json"), encoding="utf-8").read())
    assert backup_state["relocate"]["jobs"]["jr-0"]["plan"]["superseded_from"] == "R:/dstA", "备份携带迁移前账"


def test_hot_enable_migration_failure_rejected_and_state_consistent(tmp_path, monkeypatch):
    """热启用路径注入失败: 回执 rejected 明示重启, 内存态与盘面一致, 主循环不带半迁移态(评审轮 2 major-2)"""
    box = _legacy_box()
    mod, data_dir, state_path = _migration_env(
        tmp_path,
        box,
        journals={
            "jr-0": {
                "phase": "rewritten",
                "ts": 1500.0
            },
            "jr-1": {
                "phase": "armed",
                "ts": 1500.0
            }
        },
    )
    state_before = state_path.read_bytes()
    old_cfg = types.SimpleNamespace(relocate=RelocateConfig(enabled=False))
    new_cfg = types.SimpleNamespace(relocate=RelocateConfig(enabled=True))
    mod._conf = old_cfg.relocate
    monkeypatch.setattr("auto_qb.infra.alias_fs.get_capability", lambda refresh=False: None)
    real = rj.write_journal
    calls = {"n": 0}

    def _flaky(*a, **k):
        calls["n"] += 1
        if calls["n"] >= 2:
            raise RuntimeError("boom")
        return real(*a, **k)

    monkeypatch.setattr(rj, "write_journal", _flaky)
    result = mod.apply(old_cfg, new_cfg)
    monkeypatch.setattr(rj, "write_journal", real)

    assert result.action == "rejected", "热启用被拒绝(不吞异常继续主循环)"
    assert "重启" in result.detail and "回滚" in result.detail, "回执明示重启与回滚"
    assert mod._conf is old_cfg.relocate, "配置缓存回退旧段(保持禁用现场)"
    assert not mod._jobs_loaded, "stop() 补写闸未开(半迁移态不随 stop 落盘)"
    mem = mod._ctx.state.data["relocate"]["jobs"]
    assert mem["jr-0"]["phase"] == "rewritten" and mem["jr-0"]["plan"]["superseded_from"] == "R:/dstA", \
        "内存态还原迁移前快照(与盘面一致, 无半迁移残留)"
    assert state_path.read_bytes() == state_before, "盘面未被覆盖"
    # R2-1: 内核 apply_new_config 在调 apply 前已换 ctx.config(L0 换对象, rejected 无人回滚)
    # —— 直接置 ctx.config 模拟换对象后的形态, 断言执行入口真被闸(relocate_execute)
    mod._ctx.config.relocate = RelocateConfig(enabled=True)
    items = mod.relocate_execute(["HA"], "R:/somewhere")
    assert items and items[0]["cls"] == "blocked" and items[0]["reasons"][0]["gate"] == ru.GATE_DISABLED, \
        "拒绝后迁移执行入口按禁用收口(_live_conf 闸)"
    # 重试成功(_load_jobs 通过)清标志: 执行入口恢复按现配置放行(替身 api 不再走禁用闸)
    result2 = mod.apply(old_cfg, new_cfg)
    assert result2.action == "reloaded" and mod._hot_enable_rejected is False, "成功 _load_jobs 清被拒标志"
    assert getattr(mod._live_conf(), "enabled", False) is True, "标志清位后 _live_conf 不再按禁用收口"


def test_migration_backup_failure_blocks_startup_without_writes(tmp_path, monkeypatch):
    """备份阶段 OSError 注入: 统一包成 RuntimeError, 无转换写面盘面原样(评审轮 3 minor-R2-2)"""
    box = _legacy_box()
    mod, data_dir, state_path = _migration_env(tmp_path, box, journals={"jr-0": {"phase": "rewritten", "ts": 1500.0}})
    state_before = state_path.read_bytes()
    journal_before = open(rj.journal_path(data_dir, "jr-0"), "rb").read()

    def _boom(*a, **k):
        raise OSError("disk full")

    monkeypatch.setattr("auto_qb.core.modules.relocate_mod.shutil.copy2", _boom)
    with pytest.raises(RuntimeError, match="备份未完成"):
        mod._load_jobs()
    monkeypatch.setattr("auto_qb.core.modules.relocate_mod.shutil.copy2", lambda *a, **k: None)
    mem = mod._ctx.state.data["relocate"]["jobs"]
    assert mem["jr-0"]["phase"] == "rewritten" and mem["jr-0"]["plan"]["superseded_from"] == "R:/dstA", \
        "内存快照还原(无半迁移残留)"
    assert "model_version" not in mod._ctx.state.data["relocate"], "失败路径不盖章"
    assert state_path.read_bytes() == state_before, "state.json 原样(备份阶段无转换写)"
    assert open(rj.journal_path(data_dir, "jr-0"), "rb").read() == journal_before, "journal 零写(未进转换面)"
    # 热启用路径同因: OSError 不再裸抛漏过 apply 的 except RuntimeError, 得 rejected 回执
    old_cfg = types.SimpleNamespace(relocate=RelocateConfig(enabled=False))
    new_cfg = types.SimpleNamespace(relocate=RelocateConfig(enabled=True))
    mod._conf = old_cfg.relocate
    monkeypatch.setattr("auto_qb.infra.alias_fs.get_capability", lambda refresh=False: None)
    monkeypatch.setattr("auto_qb.core.modules.relocate_mod.shutil.copy2", _boom)
    result = mod.apply(old_cfg, new_cfg)
    assert result.action == "rejected" and "重启" in result.detail, "备份失败同样走拒绝回执"


def test_migration_successor_cycle_orphans_both(tmp_path):
    """环形继任按孤儿收口: 条目不归集、无 superseded_by=自身、两账零丢失(评审轮 2 minor-5)"""
    j_a = _legacy_job("jr-a", "R:/ra", "R:/dstC", "rewritten", 100.0)
    j_a["plan"]["superseded_from"] = "R:/ra"
    j_b = _legacy_job("jr-b", "R:/rb", "R:/dstC", "armed", 200.0)
    j_b["plan"]["superseded_from"] = "R:/rb"
    mod, data_dir, state_path = _migration_env(
        tmp_path,
        {
            "jr-a": j_a,
            "jr-b": j_b
        },
        journals={
            "jr-a": {
                "phase": "rewritten",
                "ts": 1500.0
            },
            "jr-b": {
                "phase": "armed",
                "ts": 1500.0
            }
        },
    )

    n = mod._load_jobs()

    assert n == 2, "零丢失: 两账都保留"
    data = mod._ctx.state.data["relocate"]
    for jid, old in (("jr-a", "R:/ra"), ("jr-b", "R:/rb")):
        d = data["jobs"][jid]
        assert d["phase"] == ru.PHASE_SUPERSEDED and d["dst"] == old, "按孤儿收口(原始落点还原)"
        assert not (d.get("plan") or {}).get("inherited"), "环形无有效顶端: 条目不归集"
        body = rj.read_journal(data_dir, jid)
        assert body["phase"] == ru.PHASE_SUPERSEDED, "journal 照常退休"
        assert "superseded_by" not in body, "绝不写 superseded_by=自身"


def test_migration_marked_state_skips(tmp_path):
    """model_version 已盖章 = 幂等跳过, 不再迁移不再备份"""
    box = _legacy_box()
    mod, data_dir, state_path = _migration_env(tmp_path, box)
    mod._ctx.state.data["relocate"]["model_version"] = ru.MODEL_VERSION
    state_path.write_text(json.dumps(mod._ctx.state.data, ensure_ascii=False), encoding="utf-8")

    mod._load_jobs()

    assert mod._ctx.state.data["relocate"]["jobs"]["jr-0"]["plan"]["superseded_from"] == "R:/dstA", "原样不迁移"
    assert not os.path.exists(os.path.join(data_dir, "relocate-migration-backup")), "无备份(未触发迁移)"


def test_migration_no_legacy_stamps_marker_without_backup(tmp_path):
    """有账无 legacy 标记 -> 只盖章, 不建备份目录"""
    box = {"jr-x": _legacy_job("jr-x", "R:/src", "R:/dst", "armed", 100.0)}
    mod, data_dir, state_path = _migration_env(tmp_path, box)

    mod._load_jobs()

    assert mod._ctx.state.data["relocate"]["model_version"] == ru.MODEL_VERSION
    assert not os.path.exists(os.path.join(data_dir, "relocate-migration-backup"))
    assert mod.get_job("jr-x").phase == ru.PHASE_ARMED


def test_migration_dry_run_skips(tmp_path):
    """dry-run 启动不动手: legacy 账原样, 留给下一次真启动"""
    box = _legacy_box()
    mod, data_dir, state_path = _migration_env(tmp_path, box)
    mod._dry = True

    mod._load_jobs()

    assert mod._ctx.state.data["relocate"]["jobs"]["jr-0"]["phase"] == "rewritten", "账面原样"
    assert "model_version" not in mod._ctx.state.data["relocate"], "未盖章"
    assert not os.path.exists(os.path.join(data_dir, "relocate-migration-backup"))
