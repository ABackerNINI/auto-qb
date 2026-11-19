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
- test_takeover_write_through_stamp_and_ledger_converge_disk: 接管面写穿(真机缺陷1)——
  盖章+转换后盘面(state.json)已是迁移后真相; 模拟 run() 的 _reload_state 整体重读章仍在;
  落一笔 job 账 + 周期刷盘后章仍在; 二启迁移器幂等跳过(无第二份备份)。
- test_prune_write_through_periodic_flush_disk_matches_memory: 接管面写穿(真机缺陷2)——
  _load_jobs -> prune 滚出超限 done 后盘面与内存一致; 模拟 reload 整体重读 + 多次周期
  刷盘, 滚出账不复活(真机曾三次刷盘仍写滚出前账面)。
- test_migrated_successor_cancel_semantics_moving_window: 迁移器产物 x 撤销语义 —— 迁移器
  建账(dst 自 superseded_from 还原、带 plan.inherited)的 MOVING job 撤销: 未确认先回
  三段式 guide; 确认后清理面 = 自建链接, inherited 不删不撤(改指收敛前的撤销窗, 继承
  别名仍指前任 dst, 悬空为已接受遗留风险), 零 qB 写, 前任历史零触碰。目录别名建链走
  _DIR_ALIAS_KIND(Windows junction / POSIX symlink, 不绑平台)。

覆盖率补测(2026-11-17, 迁移器/写穿/对账回写剩余分支; 补测轮到闸门绿):
- test_probe_salt_and_stamp_degenerate_state_shapes: 退化 state 形态 —— probe_salt_ensure
  上下文缺失返回空串不生成 / model_version 坏形按未盖章 / jobs 箱非 dict 直接盖章零备份 /
  store 为 None 的登记面空转
- test_migration_successor_matching_skips_and_prefers: 继任判定跳过面(哈希不交集/dst 不等)
  与多候选择优(非终态优先, 同分取 updated_at 最新; 落选候选让位回环)
- test_migration_rerun_replaces_entry_and_lifts_sub_inherited: 幂等重跑(半程崩溃残留同 id
  条目原位替换不叠加)/ 前任自带移交条目展平上提链顶(坏形条目逐条跳过, 同 id 不重复)
- test_migration_rewrite_spec_no_change_skips_write: spec 重写无增量不写盘(成员全在账 +
  src 与既有 extra_srcs 重合)/ 仅 extra_srcs 增量仍写盘(members 不重复并入)
- test_migration_backup_without_journal_dir: data_dir 无 relocate 目录时备份不含镜像,
  迁移照常完成
- test_migration_rollback_disk_restore_shapes: 回滚盘面四形态(无内存快照只盘面还原 /
  备份缺 state 文件撤走窗口新产物 / 镜像重建现目录缺失 / 无镜像整目录撤走 / 双缺空转 /
  state_file 缺失跳过 state 还原 / 回滚自身异常如实暴露不抛)
- test_load_jobs_terminal_journal_ts_unparseable_shelved: 启动对账锚定面 —— journal 终相位
  ts 不可解析: 锚定不上搁置不采纳, state 相位原样
"""

import json
import os
import shutil
import types
from dataclasses import replace

import pytest

from auto_qb.config.models import RelocateConfig

from auto_qb.core import fastresume as frmod

from auto_qb.core.state import StateService

from auto_qb.infra import alias_fs as afs

from auto_qb.infra import relocate_journal as rj

from auto_qb.core.modules import relocate_units as ru

from test_recycle_daemon import HOST, PORT, _fr_path, _member_fixture, _run, _stub_qb

from relocate_exec_support import _bare_mod

# 平台中立的目录别名形态: junction 仅 Windows(POSIX 上 ctypes.WinDLL 不存在),
# POSIX 侧目录 symlink 等价(建/识/穿透/删四件套 alias_fs 单点全覆盖);
# 撤销语义用例只关心链接在不在/指不指, 与具体形态无关
_DIR_ALIAS_KIND = afs.KIND_JUNCTION if os.name == "nt" else afs.KIND_SYMLINK


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


def _svc_env(tmp_path, box, journals=None):
    """真实 StateService 盘面环境(接管面写穿断言用): state.json 落盘 + journal 预置

    返回 (mod, svc, data_dir, state_path) —— svc 是真 StateService(save/maybe_flush 可用),
    盘面断言一律重读 state.json 文件(不信任内存)。
    """
    data_dir = str(tmp_path / "data")
    os.makedirs(os.path.join(data_dir, "relocate"), exist_ok=True)
    state_path = tmp_path / "state.json"
    payload = {"relocate": {"jobs": box, "probe_salt": "s1"}}
    state_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    for jid, body in (journals or {}).items():
        rj.write_journal(data_dir, jid, body)
    svc = StateService(str(state_path))
    svc.data = svc.load()
    mod = _bare_mod(data_dir=data_dir)
    mod._ctx.state = svc
    return mod, svc, data_dir, state_path


def _disk(state_path):
    """盘面真值(重读文件, 不经任何内存态)"""
    return json.loads(state_path.read_text(encoding="utf-8"))


class _ApiSpy:
    """全方法记账的 api 替身(撤销面「零 qB 写」断言用)"""
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def _rec(*a, **k):
            self.calls.append((name, a, k))

        return _rec


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


def test_takeover_write_through_stamp_and_ledger_converge_disk(tmp_path):
    """接管面写穿(真机缺陷1): 盖章+转换后盘面已是迁移后真相; 模拟 run() 的
    _reload_state 整体重读章仍在; 落一笔 job 账 + 周期刷盘后章仍在; 二启幂等跳过"""
    mod, svc, data_dir, state_path = _svc_env(tmp_path, _legacy_box())

    mod._load_jobs()

    # 写穿: 接管收敛即落盘(在任何周期刷盘之前), 盘面已是迁移后真相
    disk = _disk(state_path)
    assert disk["relocate"]["model_version"] == ru.MODEL_VERSION, "版本标记随接管写穿落盘"
    assert disk["relocate"]["jobs"]["jr-0"]["phase"] == ru.PHASE_SUPERSEDED, "转换账随写穿落盘"
    assert "superseded_from" not in (disk["relocate"]["jobs"]["jr-0"].get("plan") or {}), "改道字段已摘除"
    # 模拟 run() 启动序列的 _reload_state: state.data 从磁盘整体重读替换(启动期突变曾在此被丢弃)
    svc.data = svc.load()
    assert svc.data["relocate"]["model_version"] == ru.MODEL_VERSION, "reload 重读后章仍在"
    assert svc.data["relocate"]["jobs"]["jr-1"]["dst"] == "R:/dstB", "原始落点还原随重读保持"
    # 二启(新模块同一 state 服务): 迁移器幂等跳过, 不建第二份备份
    mod2 = _bare_mod(data_dir=data_dir)
    mod2._ctx.state = svc
    backup_root = os.path.join(data_dir, "relocate-migration-backup")
    stamps_before = os.listdir(backup_root)
    mod2._load_jobs()
    assert os.listdir(backup_root) == stamps_before, "二启不再迁移(幂等跳过)"
    # 落一笔 job 账(_persist 整段重写 jobs 箱)+ 周期刷盘: 盘面章仍在、账一致
    mod2._set_job(replace(mod2.get_job("jr-2"), phase=ru.PHASE_WATCHING))
    svc.maybe_flush(svc.next_flush_at + 10.0, 30.0)
    disk2 = _disk(state_path)
    assert disk2["relocate"]["model_version"] == ru.MODEL_VERSION, "落账+刷盘后章仍在(_persist 不抹章)"
    assert disk2["relocate"]["jobs"]["jr-2"]["phase"] == ru.PHASE_WATCHING, "账面动作照常落盘"


def test_prune_write_through_periodic_flush_disk_matches_memory(tmp_path, monkeypatch):
    """接管面写穿(真机缺陷2): _load_jobs -> prune 滚出超限 done 后盘面与内存一致;
    模拟 reload 整体重读 + 多次周期刷盘, 滚出账不复活(真机曾三次刷盘仍写滚出前账面)"""
    monkeypatch.setattr(ru, "DONE_HISTORY_KEEP", 2)
    box = {f"jr-done-{i}": _legacy_job(f"jr-done-{i}", f"R:/s{i}", f"R:/d{i}", "done", 100.0 + i) for i in range(4)}
    box["jr-live"] = _legacy_job("jr-live", "R:/sl", "R:/dl", "armed", 500.0)
    mod, svc, data_dir, state_path = _svc_env(tmp_path, box)

    mod._load_jobs()

    mem = set(mod._jobs)
    assert mem == {"jr-live", "jr-done-2", "jr-done-3"}, "内存账已滚出最老 2 条 done"
    disk = _disk(state_path)
    assert set(disk["relocate"]["jobs"]) == mem, "写穿: 盘面与内存一致(不写滚出前账面)"
    assert disk["relocate"]["model_version"] == ru.MODEL_VERSION, "章随写穿落盘"
    # 模拟 run() reload 整体重读 + 三次周期刷盘: 盘面不回滚到滚出前
    svc.data = svc.load()
    for _ in range(3):
        svc.maybe_flush(svc.next_flush_at + 40.0, 40.0)
        disk = _disk(state_path)
        assert set(disk["relocate"]["jobs"]) == mem, "周期刷盘不再写回滚出前账面"
        assert disk["relocate"]["model_version"] == ru.MODEL_VERSION, "章随每次刷盘保留"


def test_migrated_successor_cancel_semantics_moving_window(tmp_path):
    """迁移器产物 x 撤销语义(D6/D7): 迁移器建账(dst 自 superseded_from 还原、带
    plan.inherited)的 MOVING job 撤销 —— 未确认先回三段式 guide; 确认后清理面 =
    自建链接, inherited 不删不撤(改指收敛前的撤销窗, 继承别名仍指前任 dst, 悬空为
    已接受遗留风险), 全程零 qB 写, 前任历史零触碰"""
    src_root = str(tmp_path / "srcRoot")  # 前任 src(继承别名所在旧根)
    old_root = str(tmp_path / "oldRoot")  # 前任原始落点(迁移器还原进 dst)
    flipped = str(tmp_path / "flippedRoot")  # 改道机器翻转值(继任 dst)
    os.makedirs(os.path.join(old_root, "Show"))
    with open(os.path.join(old_root, "Show", "file.bin"), "wb") as f:
        f.write(b"x" * 8)
    own_link = os.path.join(old_root, "own-alias")  # 继任自建链接(MOVING 期, src 侧)
    inh_link = os.path.join(src_root, "pred-alias")  # 前任别名(继承条目, 指前任 dst)
    os.makedirs(src_root)
    afs.create_dir_alias(own_link, os.path.join(old_root, "Show"), _DIR_ALIAS_KIND)
    afs.create_dir_alias(inh_link, os.path.join(old_root, "Show"), _DIR_ALIAS_KIND)
    pred = _legacy_job("jr-p", src_root, flipped, "rewritten", 100.0)
    pred["plan"]["superseded_from"] = old_root
    pred["alias_paths"] = [inh_link]
    succ = _legacy_job("jr-s", old_root, flipped, "moving", 200.0)
    succ["alias_paths"] = [own_link]
    mod, svc, data_dir, state_path = _svc_env(tmp_path, {"jr-p": pred, "jr-s": succ})
    mod._ctx.api = _ApiSpy()

    mod._load_jobs()

    job_s = mod.get_job("jr-s")
    assert job_s.phase == ru.PHASE_MOVING, "在途继任零触碰(迁移器不改变相位)"
    entries = (job_s.plan or {}).get("inherited") or []
    assert [e["job_id"] for e in entries] == ["jr-p"], "移交条目归集进继任"
    assert entries[0]["dst"] == old_root, "条目 dst = 原始落点(superseded_from 还原)"
    assert entries[0]["alias_paths"] == [inh_link], "前任别名随条目移交"
    job_p = mod.get_job("jr-p")
    assert job_p.phase == ru.PHASE_SUPERSEDED and job_p.dst == old_root, "前任转历史, 原始落点还原"
    # 未确认: 三段式 guide 下发(D7), 不动任何东西
    out0 = mod.relocate_cancel("jr-s", cost_confirmed=False)
    assert out0["cls"] == "confirm" and set(out0["guide"]) == {"consequence", "halfway", "manual"}, out0
    assert os.path.lexists(own_link) and os.path.lexists(inh_link), "确认面零盘面动作"
    assert mod.get_job("jr-s").phase == ru.PHASE_MOVING, "确认面零账面动作"
    # 确认撤销: 清理面 = 自建链接; 继承别名不删不撤
    out = mod.relocate_cancel("jr-s", cost_confirmed=True)
    assert out["cls"] == "ok", out
    saved = mod.get_job("jr-s")
    assert saved.phase == ru.PHASE_CANCELLED and saved.alias_paths == (), "撤销落 CANCELLED 清自有链接账"
    assert (saved.plan or {}).get("inherited"), "inherited 不删不撤(账面保留)"
    assert not os.path.lexists(own_link), "自建链接删净(清理面 = 自己已建的链接)"
    assert afs.alias_kind_of(inh_link) is not None, "继承别名仍在盘(不删不撤)"
    assert afs.alias_points_to(inh_link, os.path.join(old_root, "Show")), "继承别名指向原样(前任 dst)"
    assert mod._ctx.api.calls == [], f"撤销链零 qB 写(零 setLocation/零 resume): {mod._ctx.api.calls}"
    svc.save()
    disk = _disk(state_path)
    assert disk["relocate"]["jobs"]["jr-p"]["phase"] == ru.PHASE_SUPERSEDED, "前任历史零触碰"
    assert disk["relocate"]["jobs"]["jr-s"]["phase"] == ru.PHASE_CANCELLED, "撤销账落盘"
    assert disk["relocate"]["model_version"] == ru.MODEL_VERSION, "章保留"


# ---------- 覆盖率补测(2026-11-17, 迁移器/写穿/对账回写剩余分支): 行为有意义面 ----------


def test_probe_salt_and_stamp_degenerate_state_shapes(tmp_path):
    """退化 state 形态不炸: probe_salt_ensure 上下文缺失返回空串 / model_version 坏形按
    未盖章处理(尝试迁移) / jobs 箱非 dict 直接盖章零备份(store 为 None 的登记面同样空转)"""
    # 上下文缺失(state.data 非 dict): 读盐/保盐返回空串, 绝不生成不落盘
    mod = _bare_mod(data_dir=str(tmp_path))
    mod._ctx.state = types.SimpleNamespace(data=None)
    assert mod.probe_salt_ensure() == ""
    # 派生查询零 store 依赖(S5 登记集退役): ctx 无 store 字段也能算 —— 原「store 为 None
    # resuming 登记面空转」的同族退化面随登记面消失, 派生只读内存账
    mod._ctx = types.SimpleNamespace(state=types.SimpleNamespace(data=None))
    assert mod.resuming_hashes() == frozenset() and mod.relocating_hashes() == frozenset()
    assert mod.alias_roots() == ()
    # model_version 坏形(list)+ jobs 箱非 dict: 按未盖章 -> 尝试迁移 -> 无账可迁直接盖章
    # (直调迁移器: _load_jobs 的账恢复循环按 dict 箱为前提, 坏形箱的容错收口在迁移器)
    data_dir = str(tmp_path / "data")
    state_path = tmp_path / "state.json"
    payload = {"relocate": {"model_version": ["bad"], "jobs": "oops"}}
    state_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    svc = StateService(str(state_path))
    svc.data = svc.load()
    mod2 = _bare_mod(data_dir=data_dir)
    mod2._ctx.state = svc
    mod2._migrate_legacy_accounts()
    assert svc.data["relocate"]["model_version"] == ru.MODEL_VERSION, "坏形版本号按未盖章, 空账直接盖章"
    assert not os.path.isdir(os.path.join(data_dir, "relocate-migration-backup")), "盖章路径零备份目录"


def test_migration_successor_matching_skips_and_prefers(tmp_path):
    """继任判定跳过面与择优: 哈希不交集跳过 / dst 不等跳过 / 多候选按(非终态, updated_at)
    择优 —— 条目归集到择优继任, 被跳过账零触碰"""
    box = {
        "jr-0": _legacy_job("jr-0", "R:/s0", "R:/dstC", "armed", 100.0, hashes=("HA", )),
        "jr-x": _legacy_job("jr-x", "R:/sx", "R:/dstC", "armed", 900.0, hashes=("HB", )),  # 哈希不交集: 跳过
        "jr-y": _legacy_job("jr-y", "R:/sy", "R:/dstD", "armed", 800.0, hashes=("HA", )),  # dst 不等: 跳过
        "jr-z": _legacy_job("jr-z", "R:/sz", "R:/dstC", "done", 100.0, hashes=("HA", )),  # 终态候选(分低)
        "jr-v": _legacy_job("jr-v", "R:/sv", "R:/dstC", "done", 50.0, hashes=("HA", )),  # 落选候选(更差)
        "jr-w": _legacy_job("jr-w", "R:/sw", "R:/dstC", "armed", 200.0, hashes=("HA", )),  # 在途候选(择优)
    }
    box["jr-0"]["plan"]["superseded_from"] = "R:/dstA"
    mod, data_dir, state_path = _migration_env(tmp_path, box)

    n = mod._load_jobs()

    assert n == 6, "六账一条不丢"
    data = mod._ctx.state.data["relocate"]
    # 条目归集到择优继任 jr-w(在途优先于终态; 同分才比 updated_at)
    inherited = {e["job_id"] for e in (data["jobs"]["jr-w"].get("plan") or {}).get("inherited") or ()}
    assert inherited == {"jr-0"}, f"归集到择优继任: {inherited}"
    # 被跳过账(哈希不交集/dst 不等/落选候选)零触碰
    for jid in ("jr-x", "jr-y", "jr-z"):
        assert data["jobs"][jid]["phase"] == box[jid]["phase"], jid
        assert not (data["jobs"][jid].get("plan") or {}).get("inherited"), jid


def test_migration_rerun_replaces_entry_and_lifts_sub_inherited(tmp_path):
    """幂等重跑与展平上提面: 半程崩溃重跑(继任已有同 id 条目)原位替换不重复 / 前任自带的
    移交条目一并上提链顶(前任账不再持有)/ 空 src 的条目不进 spec 重写清单"""
    box = {
        "jr-1": _legacy_job("jr-1", "", "R:/dstC", "armed", 200.0, hashes=("HA", )),
        "jr-2": _legacy_job("jr-2", "R:/s2", "R:/dstC", "moving", 300.0, hashes=("HA", )),
    }
    box["jr-1"]["plan"]["superseded_from"] = "R:/dstB"
    # 半程崩溃残留: 继任已有 jr-1 的旧条目(重跑须原位替换, 不叠加)
    box["jr-2"]["plan"]["inherited"] = [
        {
            "job_id": "jr-1",
            "src": "R:/stale",
            "dst": "R:/stale-dst",
            "scope": "R:/stale",
            "alias_kind": "dir",
            "alias_paths": [],
            "link_kind": "junction",
        }
    ]
    # 前任自带的移交条目(旧机器时代展平遗留): 迁移时一并上提链顶; 坏形条目逐条跳过不炸
    box["jr-1"]["plan"]["inherited"] = [
        42,  # 非 dict: 跳过
        {
            "src": "R:/no-id"
        },  # 缺 job_id: 跳过
        {
            "job_id": "jr-1",
            "src": "R:/dup"
        },  # 与主条目同 id(已在链顶): 不重复上提
        {
            "job_id": "jr-0",
            "src": "R:/s0",
            "dst": "R:/dstA",
            "scope": "R:/s0",
            "alias_kind": "dir",
            "alias_paths": ["R:/dstA/alias"],
            "link_kind": "junction",
        },
    ]
    mod, data_dir, state_path = _migration_env(tmp_path, box)

    mod._load_jobs()

    data = mod._ctx.state.data["relocate"]
    j2_plan = data["jobs"]["jr-2"]["plan"]
    entries = {e["job_id"]: e for e in j2_plan["inherited"]}
    assert set(entries) == {"jr-1", "jr-0"}, f"替换 + 上提: {set(entries)}"
    assert entries["jr-1"]["dst"] == "R:/dstB" and entries["jr-1"]["src"] == "", "原位替换为本次归集值"
    assert entries["jr-0"]["dst"] == "R:/dstA", "前任自带条目上提保留"
    assert not (data["jobs"]["jr-1"].get("plan") or {}).get("inherited"), "前任账不再持有"


def test_migration_rewrite_spec_no_change_skips_write(tmp_path):
    """spec 重写无增量不写盘: 前任成员已在继任 spec(members 不变)+ 移交 src 与既有
    extra_srcs 重合(无新根) -> added 恒 False, spec 字节不变(473->476 / 476->exit 面);
    新 src 根且成员全在账(465->467: members 不加, 仅 extra_srcs 增量)-> 仍写盘"""
    def _env(name, legacy_src):
        backup = tmp_path / f"BT_backup-{name}"
        root_a, root_c, root_d = str(tmp_path / f"a-{name}"), str(tmp_path / f"c-{name}"), str(tmp_path / f"d-{name}")
        h_a = _member_fixture(backup, b"m-a", root_a)
        box = {
            "jr-1": _legacy_job("jr-1", legacy_src, root_d, "armed", 200.0, hashes=(h_a, )),
            "jr-2": _legacy_job("jr-2", root_c, root_d, "armed", 300.0, hashes=(h_a, )),
        }
        box["jr-1"]["plan"]["superseded_from"] = root_a
        data_dir = str(tmp_path / f"data-{name}")
        os.makedirs(os.path.join(data_dir, "relocate"), exist_ok=True)
        state_path = tmp_path / f"state-{name}.json"
        state_path.write_text(json.dumps({"relocate": {"jobs": box}}, ensure_ascii=False), encoding="utf-8")
        rj.write_spec(
            data_dir, "jr-2", {
                "job_id": "jr-2",
                "src": root_c,
                "dst": root_d,
                "scope": root_c,
                "hashes": [h_a],
                "host": HOST,
                "port": PORT,
                "alias_paths": [],
                "files": [],
                "bt_backup": str(backup),
                "members": [{
                    "hash_v1": h_a,
                    "hash_v2": ""
                }],
                "extra_srcs": [root_a],
            }
        )
        mod = _bare_mod(data_dir=data_dir)
        mod._ctx.state = types.SimpleNamespace(
            data=json.loads(state_path.read_text(encoding="utf-8")), state_file=str(state_path)
        )
        mod._ctx.config = types.SimpleNamespace(relocate=RelocateConfig(enabled=True), data_dir=data_dir)
        spec_before = rj.read_spec(data_dir, "jr-2")
        return mod, data_dir, spec_before

    # 场景一: 全部增量重合(前任 src 与既有 extra_srcs 重合, 成员已在账) -> spec 零写(内容不变)
    mod1, data_dir1, spec1 = _env("same", str(tmp_path / "a-same"))
    mod1._load_jobs()
    assert rj.read_spec(data_dir1, "jr-1") is None, "前任无 spec(只有继任有)"
    spec_after = rj.read_spec(data_dir1, "jr-2")
    assert spec_after == spec1, "无增量不重写 spec"

    # 场景二: 成员已在账 + 新 src 根 -> 仅 extra_srcs 增量, 仍写盘
    mod2, data_dir2, _ = _env("newsrc", "R:/s2")
    mod2._load_jobs()
    spec2 = rj.read_spec(data_dir2, "jr-2")
    member_v1 = {m["hash_v1"] for m in spec2["members"] if isinstance(m, dict)}
    assert len(member_v1) == 1, "成员全在账不重复并入"
    assert len(spec2["extra_srcs"]) == 2, "新 src 根并入 extra_srcs"


def test_migration_backup_without_journal_dir(tmp_path):
    """迁移前备份面: data_dir 尚无 relocate 目录(journal 未启用) -> 备份目录不含 relocate
    镜像, 迁移照常完成(journal 投影空转)"""
    box = {"jr-1": _legacy_job("jr-1", "R:/s1", "R:/dstC", "armed", 200.0, hashes=("HA", ))}
    box["jr-1"]["plan"]["superseded_from"] = "R:/dstB"
    data_dir = str(tmp_path / "data")  # 不建 relocate 子目录
    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps({"relocate": {"jobs": box}}, ensure_ascii=False), encoding="utf-8")
    svc = StateService(str(state_path))
    svc.data = svc.load()
    mod = _bare_mod(data_dir=data_dir)
    mod._ctx.state = svc

    mod._load_jobs()

    backup_root = os.path.join(data_dir, "relocate-migration-backup")
    backups = os.listdir(backup_root)
    assert backups, "备份目录落盘"
    assert not os.path.exists(os.path.join(backup_root, backups[0], "relocate")), "无 journal 目录则不镜像"
    assert mod._ctx.state.data["relocate"]["jobs"]["jr-1"]["phase"] == ru.PHASE_SUPERSEDED


def test_migration_rollback_disk_restore_shapes(tmp_path, monkeypatch, caplog):
    """回滚盘面形态: 无内存快照参数只做盘面还原 / 备份缺 state 文件撤走迁移窗口新产物 /
    备份有 relocate 镜像而现目录缺失(重建)/ 备份无镜像而现目录在(整目录撤走)/
    state_file 缺失跳过 state 还原 / 回滚自身异常如实暴露不抛"""
    def _shape(backup_has_relocate, current_has_relocate, state_file_name="state.json"):
        data_dir = str(tmp_path / ("d-%s-%s-%s" % (backup_has_relocate, current_has_relocate, state_file_name)))
        os.makedirs(data_dir, exist_ok=True)
        if current_has_relocate:
            os.makedirs(os.path.join(data_dir, "relocate"))
            rj.write_journal(data_dir, "jr-x", {"phase": "armed", "ts": 1.0})
        backup_dir = os.path.join(data_dir, "backup")
        os.makedirs(backup_dir, exist_ok=True)
        state_path = os.path.join(data_dir, state_file_name)
        open(state_path, "w", encoding="utf-8").write("{}")
        shutil.copy2(state_path, os.path.join(backup_dir, "state.json"))
        if backup_has_relocate:
            os.makedirs(os.path.join(backup_dir, "relocate"))
            rj.write_journal(backup_dir, "jr-x", {"phase": "armed", "ts": 1.0})
        open(os.path.join(data_dir, "state.json.bak"), "w", encoding="utf-8").write("{}")
        mod = _bare_mod(data_dir=data_dir)
        mod._ctx.state = types.SimpleNamespace(data={}, state_file=state_path)
        return mod, data_dir, backup_dir

    # 形态一: 无内存快照(备份阶段失败面) + 备份缺 .bak(迁移窗口新产物) -> 撤走;
    # 备份无 relocate 镜像而现目录在 -> 整目录撤走
    mod, data_dir, backup_dir = _shape(False, True)
    mod._migration_rollback(data_dir, backup_dir)
    assert not os.path.exists(os.path.join(data_dir, "state.json.bak")), "备份缺该文件 = 迁移窗口新产物, 撤走"
    assert not os.path.isdir(os.path.join(data_dir, "relocate")), "备份时无 relocate 目录 -> 现目录全为迁移产物, 撤走"

    # 形态四: 备份与现目录都无 relocate -> 面全空转, 只还原 state
    mod, data_dir, backup_dir = _shape(False, False)
    mod._migration_rollback(data_dir, backup_dir)
    assert not os.path.isdir(os.path.join(data_dir, "relocate"))
    assert os.path.isfile(os.path.join(data_dir, "state.json"))

    # 形态二: 备份有 relocate 镜像而现目录缺失 -> 重建; state_file 空 -> 跳过 state 还原
    mod, data_dir, backup_dir = _shape(True, False, state_file_name="other.json")
    mod._ctx.state.state_file = ""
    mod._migration_rollback(data_dir, backup_dir)
    assert os.path.isfile(os.path.join(data_dir, "relocate", "jr-x.json")), "现目录缺失由备份镜像重建"
    assert not os.path.exists(os.path.join(data_dir, "state.json")), "state_file 缺失: state 还原面跳过"

    # 形态三: 回滚自身异常 -> logger.error 如实暴露, 不上抛
    mod, data_dir, backup_dir = _shape(False, True)

    def _boom(src, dst, *a, **k):
        raise OSError("boom")

    monkeypatch.setattr(shutil, "copy2", _boom)
    mod._migration_rollback(data_dir, backup_dir)
    assert any("回滚失败" in r.message for r in caplog.records), "回滚异常如实暴露"
    assert os.path.isdir(os.path.join(data_dir, "relocate")), "异常后现场原样(不半撤)"


def test_load_jobs_terminal_journal_ts_unparseable_shelved(tmp_path):
    """启动对账锚定面: journal 终相位但 ts 不可解析 -> 锚定不上搁置不采纳(state 相位原样,
    上一世残留交 _arm 侧既有清理口)"""
    box = {"jr-1": _legacy_job("jr-1", "R:/s1", "R:/dstC", "moving", 200.0, hashes=("HA", ))}
    journals = {"jr-1": {"phase": "done", "ts": "not-a-number"}}
    mod, data_dir, state_path = _migration_env(tmp_path, box, journals)

    n = mod._load_jobs()

    assert n == 1
    assert mod.get_job("jr-1").phase == ru.PHASE_MOVING, "ts 不可解析: 锚定不上, 搁置不采纳"
    assert mod._ctx.state.data["relocate"]["jobs"]["jr-1"]["phase"] == "moving", "state 原样"
