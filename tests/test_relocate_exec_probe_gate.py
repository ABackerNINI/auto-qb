"""test_relocate_exec_probe_gate 测试计划: 执行链一次性同机强探测闸(P3b)
(计划 26-11-04-0055 §04 P3 行后半 + §06 D1/D4/D5/D6/D7 —— relocate_exec.ExecMixin._ensure_probe)

位置契约(D5): 探测闸在 evaluate 判定通过后、_start_job 与任何 torrents_set_location 之前,
探测失败 => 零建账、零 setLocation。回执 blocked 与 evaluate_group 现行 blocked item 同形
(reasons 元素 gate/cls/text), 前端 truth 结构不变。

## 测试计划(每个测试函数一条)
- test_first_multi_member_migration_probes_then_starts: 首次多成员迁移触发 run_probe(src/dst 实参钉死),
  passed 后缓存写 passed 且 job 正常建立、setLocation 下发
- test_probe_fs_unreachable_blocks_without_job_or_setlocation: run_probe env=False => 无 job、
  零 setLocation、缓存里是 failed(带 reason)
- test_second_migration_hits_failed_cache_without_reprobe: 二次迁移命中 failed 缓存 =>
  run_probe 不再被调、直接 blocked(文案带「已缓存」语义 + path_map/assume_shared 两条出路)
- test_env_failure_not_cached_and_retried_next_time: env=True 失败 => 无缓存写入、下次迁移再探
  (blocked 文案区分环境性语义并带两条出路)
- test_cached_passed_hits_with_zero_probe_calls: 缓存 passed 命中 => 零 run_probe 调用(D4 组合口径;
  预检层凭缓存证 proved 短路, note「凭机器级强证明(E1 缓存)放行」随 same_fs_note 带出)
- test_gate_cached_passed_direct_hit_appends_note: 预检层缓存读失败(证明面不可判定)而执行闸
  直读缓存 passed => 放行 + note「同机强探测: 命中缓存(指纹 …)」
- test_single_member_assume_shared_and_dry_run_skip_probe: 单成员组(D2)/assume_shared(D7)/
  dry-run 三面零探测调用
- test_fingerprint_change_reprobes: qB 配置 host/port 变更 => 指纹变化 => 重新探测(D3)
- test_missing_qb_config_blocks_without_caching: qbittorrent 连接配置缺失 => 按环境性失败
  短路 blocked(gate same_fs, 文案「qB 连接配置缺失, 无法执行同机探测」), 不触发探测、不写缓存
  (经 _ensure_probe 直测 —— 无 qbittorrent 段的 config 在执行体现在先被部署闸 D 格拦下,
  S1 部署闸在前是正确顺序, 本用例聚焦探测闸自身分支)
- test_weak_positive_still_probes_and_strong_d_positive_skips: 弱证据任何方向都不短路探测闸
  —— src B′ positive / dst visibility_only positive / src B′ negative(+dst visibility
  positive)三种桩面 run_probe 都照走一次(R1#35, issue 26-11-07-0527);
  src 侧 D 级 positive 维持 same_fs_proved 短路(零探测直接建账)
"""

import types
from pathlib import Path

from auto_qb.config.models import RelocateConfig

from auto_qb.core.modules import relocate_exec as rex

from auto_qb.core.modules import relocate_units as ru

from auto_qb.core.modules.grouping_mod import group_key_of

from auto_qb.core.modules.relocate_mod import RelocateModule

from auto_qb.core.modules.relocate_probe import ProbeResult, probe_fingerprint

from auto_qb.infra import utils as infra_utils

from helpers import _fake_file

from relocate_exec_support import _fake_fs, _stub_cap


def _gate_env(monkeypatch, *, host="127.0.0.1", port=8080):
    """多成员组 + 路径级同机证据不可判定(未证明)的最小执行环境(仿 mod9 骨架)

    R:/ 桩路径本机不可 stat => B' 不可判定; client=object() 无列目录端点 => D 不可判定;
    于是 same_fs_proved=False, 执行闸必然消费探测缓存/触发 run_probe(替身)。
    """
    # 0808 S1 源侧三态起: 桩路径下声明的源文件按「在」呈现(exists_true_prefixes),
    # 否则三态判「缺失」抢在探测闸前拒绝 —— 本文件验证的是探测闸, 不是三态
    _fake_fs(monkeypatch, free=1 << 40, exists_true_prefixes=("R:/src", ))
    _stub_cap(monkeypatch, file_kind="hardlink")
    recs = {}
    for h in ("HA", "HB"):
        recs[h] = types.SimpleNamespace(
            hash=h,
            save_path="R:/src",
            name="Show",
            log_repr=h,
            progress=1.0,
            state="pausedUP",
            state_enum=None,
            files=lambda c: [_fake_file("Show/e00.mkv", 64),
                             _fake_file("Show/e01.mkv", 64)],
        )
    store = types.SimpleNamespace(
        get=lambda h: recs.get(h),
        groups={},
        by_hash=recs,
        relocating_hashes=set(),
        server_state={"free_space_on_disk": 1 << 40},
    )
    locs = []
    mod = RelocateModule()
    mod._ctx = types.SimpleNamespace(
        store=store,
        # 部署闸放行面替身(S1 执行体同拦): 偏好无 resume_data_storage_type 键 = Legacy;
        # 其余端点照旧缺省(裸 object 的「无端点=不可判定」语义不变)
        api=types.SimpleNamespace(
            client=types.SimpleNamespace(app_preferences=lambda **kw: {}),
            torrents_set_location=lambda **kw: locs.append(kw)
        ),
        config=types.SimpleNamespace(
            # 部署闸 D 格放行面(S1 执行体同拦): bt_backup 指向真实存在目录(本文件所在 tests/)
            relocate=RelocateConfig(enabled=True, bt_backup=str(Path(__file__).resolve().parent)),
            qbittorrent=types.SimpleNamespace(host=host, port=port, username="", password="", api_key=""),
        ),
        state=types.SimpleNamespace(data={}),
    )
    # 登记全组成员: HA/HB 同 save_path 同文件表 => _buckets 按组键取 store.groups 全组
    # (不登记则回退选中集合, 组塌成单成员, 探测闸被 D2 短路)
    fmap = {
        infra_utils.path_normalize(f.name): f.size
        for f in (_fake_file("Show/e00.mkv", 64), _fake_file("Show/e01.mkv", 64))
    }
    root = ru.content_root_of("R:/src", list(fmap))
    store.groups[group_key_of(mod.resolve_physical("R:/src", root), fmap)] = ["HA", "HB"]
    return mod, locs


def _stub_run_probe(monkeypatch, results):
    """替身 run_probe: 按调用序返回 results(超出末位复用最后一个); 返回调用台账"""
    calls = []

    def _fake(ctx, src, dst):
        calls.append({"src": src, "dst": dst})
        return results[len(calls) - 1] if len(calls) <= len(results) else results[-1]

    monkeypatch.setattr(rex, "run_probe", _fake)
    return calls


def _passed():
    return ProbeResult("passed", "ok", False, {"method": "e1", "read_ok": True, "write_ok": True})


def _fs_failed(reason="read_proof_timeout"):
    return ProbeResult("failed", reason, False, {"method": "e1"})


def _env_failed(reason="add_rejected"):
    return ProbeResult("failed", reason, True, {"method": "e1"})


def test_first_multi_member_migration_probes_then_starts(monkeypatch):
    """首次多成员迁移触发 run_probe; passed 后缓存写 passed, 建账 + setLocation 正常走完"""
    mod, locs = _gate_env(monkeypatch)
    calls = _stub_run_probe(monkeypatch, [_passed()])
    items = mod.relocate_execute(["HA"], "R:/dst")
    assert items[0]["cls"] == "started", items
    assert len(calls) == 1, calls
    assert calls[0]["src"] == "R:/src" and calls[0]["dst"] == "R:/dst", calls
    assert len(locs) == 1 and locs[0]["location"] == "R:/dst", locs
    fp = probe_fingerprint(mod._ctx.config.qbittorrent, mod.probe_salt())
    assert mod.probe_get(fp)["status"] == "passed"
    assert len(mod.active_jobs()) == 1


def test_probe_fs_unreachable_blocks_without_job_or_setlocation(monkeypatch):
    """run_probe 判 FS 不可达(env=False) => blocked(same_fs 闸)、零建账、零 setLocation、缓存 failed"""
    mod, locs = _gate_env(monkeypatch)
    calls = _stub_run_probe(monkeypatch, [_fs_failed("read_proof_timeout")])
    items = mod.relocate_execute(["HA"], "R:/dst")
    it = items[0]
    assert it["cls"] == "blocked", it
    assert it["reasons"][-1]["gate"] == "same_fs" and it["reasons"][-1]["cls"] == "blocked", it["reasons"]
    assert "qB 读不到本机 src 或写不进 dst" in it["reasons"][-1]["text"], it["reasons"]
    assert "path_map" in it["reasons"][-1]["text"] and "assume_shared" in it["reasons"][-1]["text"], it["reasons"]
    assert not mod.active_jobs(), "探测失败不得建账"
    assert locs == [], "探测失败不得下发 setLocation"
    assert len(calls) == 1, calls
    fp = probe_fingerprint(mod._ctx.config.qbittorrent, mod.probe_salt())
    hit = mod.probe_get(fp)
    assert hit is not None and hit["status"] == "failed", hit
    assert hit["evidence"]["reason"] == "read_proof_timeout", hit


def test_second_migration_hits_failed_cache_without_reprobe(monkeypatch):
    """二次迁移命中 failed 缓存 => run_probe 不再被调, 直接 blocked(缓存语义文案)"""
    mod, _locs = _gate_env(monkeypatch)
    calls = _stub_run_probe(monkeypatch, [_fs_failed("write_proof_timeout")])
    first = mod.relocate_execute(["HA"], "R:/dst")
    assert first[0]["cls"] == "blocked" and len(calls) == 1, (first, calls)
    second = mod.relocate_execute(["HA"], "R:/dst")
    it = second[0]
    assert it["cls"] == "blocked", it
    assert it["reasons"][-1]["gate"] == "same_fs", it["reasons"]
    assert "上次同机探测失败(write_proof_timeout)" in it["reasons"][-1]["text"], it["reasons"]
    assert "已缓存" in it["reasons"][-1]["text"] and "state.relocate.probes" in it["reasons"][-1]["text"], it["reasons"]
    assert "path_map" in it["reasons"][-1]["text"] and "assume_shared" in it["reasons"][-1]["text"], it["reasons"]
    assert len(calls) == 1, "缓存 failed 命中不得再探(D7-1 同指纹不重试)"


def test_env_failure_not_cached_and_retried_next_time(monkeypatch):
    """env=True 失败 => blocked 但不写缓存, 下次迁移重新探测(D7-2)"""
    mod, _locs = _gate_env(monkeypatch)
    calls = _stub_run_probe(monkeypatch, [_env_failed("add_rejected"), _env_failed("add_rejected")])
    first = mod.relocate_execute(["HA"], "R:/dst")
    it = first[0]
    assert it["cls"] == "blocked" and it["reasons"][-1]["gate"] == "same_fs", it
    assert "探测环境性失败: add_rejected" in it["reasons"][-1]["text"], it["reasons"]
    assert "未缓存, 下次迁移将重试" in it["reasons"][-1]["text"], it["reasons"]
    assert "fs.path_map" in it["reasons"][-1]["text"] and "assume_shared" in it["reasons"][-1]["text"], it["reasons"]
    assert "由用户承担" in it["reasons"][-1]["text"], it["reasons"]
    fp = probe_fingerprint(mod._ctx.config.qbittorrent, mod.probe_salt())
    assert mod.probe_get(fp) is None, "环境性失败不得写缓存"
    second = mod.relocate_execute(["HA"], "R:/dst")
    assert second[0]["cls"] == "blocked" and len(calls) == 2, (second, calls)


def test_cached_passed_hits_with_zero_probe_calls(monkeypatch):
    """缓存 passed 命中 => 零 run_probe 调用直接放行(D4: 一次性机器级证明 + 预检 D 复查)"""
    mod, locs = _gate_env(monkeypatch)
    calls = _stub_run_probe(monkeypatch, [_passed()])
    fp = probe_fingerprint(mod._ctx.config.qbittorrent, mod.probe_salt_ensure())
    mod.probe_put(fp, "passed", {"method": "e1"})
    items = mod.relocate_execute(["HA"], "R:/dst")
    assert items[0]["cls"] == "started", items
    assert calls == [], "缓存 passed 命中不得触发探测"
    # 预检层已凭缓存证 proved(same_fs_note 带出), 执行闸在 same_fs_proved 短路, 零增量 note
    assert any("凭机器级强证明" in n for n in items[0]["notes"]), items[0]["notes"]
    assert len(locs) == 1, locs


def test_gate_cached_passed_direct_hit_appends_note(monkeypatch):
    """预检层缓存读失败(证明面不可判定)而执行闸直读缓存 passed => 放行 + note「同机强探测: 命中缓存(指纹 …)」"""
    mod, locs = _gate_env(monkeypatch)
    calls = _stub_run_probe(monkeypatch, [_passed()])
    fp = probe_fingerprint(mod._ctx.config.qbittorrent, mod.probe_salt_ensure())
    mod.probe_put(fp, "passed", {"method": "e1"})
    orig = mod.probe_get
    seq = {"n": 0}

    def flaky(fp_):
        seq["n"] += 1
        if seq["n"] == 1:
            raise RuntimeError("预检层缓存读失败(演练)")
        return orig(fp_)

    monkeypatch.setattr(mod, "probe_get", flaky)
    items = mod.relocate_execute(["HA"], "R:/dst")
    assert items[0]["cls"] == "started", items
    assert calls == [], "执行闸缓存 passed 直读命中不得触发探测"
    assert any("同机强探测: 命中缓存" in n and fp in n for n in items[0]["notes"]), items[0]["notes"]
    assert len(locs) == 1, locs


def test_single_member_assume_shared_and_dry_run_skip_probe(monkeypatch):
    """三面零探测: 单成员组(D2 零动作)/ assume_shared(D7 跳过+note)/ dry-run(零副作用+note)"""
    # 单成员组: 完全跳过, 零探测零 note
    mod, locs = _gate_env(monkeypatch)
    calls = _stub_run_probe(monkeypatch, [_passed()])
    del mod._ctx.store.by_hash["HB"]
    items = mod.relocate_execute(["HA"], "R:/dst")
    assert items[0]["cls"] == "started" and items[0]["form"] == "direct", items
    assert calls == [] and len(locs) == 1, (calls, locs)

    # assume_shared=true: 跳过探测, note 注明未经验证
    mod, locs = _gate_env(monkeypatch)
    calls = _stub_run_probe(monkeypatch, [_passed()])
    mod._ctx.config.relocate.assume_shared = True
    items = mod.relocate_execute(["HA"], "R:/dst")
    assert items[0]["cls"] == "started", items
    assert calls == [], "assume_shared 不得触发探测"
    assert len(locs) == 1, locs
    assert any("assume_shared" in n and "未经" in n and "由用户承担" in n for n in items[0]["notes"]), items[0]["notes"]

    # dry-run: 不执行探测(零副作用), note「dry-run: 跳过强探测」
    mod, locs = _gate_env(monkeypatch)
    calls = _stub_run_probe(monkeypatch, [_passed()])
    mod._dry = True
    items = mod.relocate_execute(["HA"], "R:/dst")
    assert items[0]["cls"] == "ok", items
    assert calls == [] and locs == [], (calls, locs)
    assert any("dry-run: 跳过强探测" in n for n in items[0]["notes"]), items[0]["notes"]


def test_missing_qb_config_blocks_without_caching(monkeypatch):
    """qbittorrent 连接配置缺失 => 环境性失败短路: blocked(gate same_fs)、零探测、零缓存写入

    经 _ensure_probe 直测: 无 qbittorrent 段的 config 在执行体现在先被部署闸 D 格拦下
    (bt_backup 未配置) —— 部署闸在前是 S1 fail-fast 的正确顺序,
    本用例聚焦探测闸自身的 qb_conf=None 分支, 不再经 relocate_execute 全链。
    """
    mod, _locs = _gate_env(monkeypatch)
    calls = _stub_run_probe(monkeypatch, [_passed()])
    mod._ctx.config = types.SimpleNamespace(relocate=RelocateConfig(enabled=True))  # 无 qbittorrent 段
    records = [types.SimpleNamespace(hash="HA"), types.SimpleNamespace(hash="HB")]
    facts = types.SimpleNamespace(same_fs_proved=False)
    verdict = {"cls": "ok", "reasons": [], "notes": []}
    gate = mod._ensure_probe(records, facts, verdict)
    assert gate is not None and gate["cls"] == "blocked", gate
    assert gate["reasons"][-1]["gate"] == "same_fs" and gate["reasons"][-1]["cls"] == "blocked", gate["reasons"]
    assert "qB 连接配置缺失, 无法执行同机探测" in gate["reasons"][-1]["text"], gate["reasons"]
    assert calls == [], "配置缺失不得触发探测"
    assert mod._ctx.state.data == {}, "环境性失败不得写探测缓存"


def test_fingerprint_change_reprobes(monkeypatch):
    """qB 配置 host/port 变更 => 指纹变化 => 缓存失效重新探测(D3)"""
    mod, _locs = _gate_env(monkeypatch, port=8080)
    calls = _stub_run_probe(monkeypatch, [_passed(), _passed()])
    assert mod.relocate_execute(["HA"], "R:/dst")[0]["cls"] == "started"
    assert len(calls) == 1, calls
    mod._jobs.clear()  # 摘掉在途账: 只钉指纹面, 不混入未收尾闸
    mod._ctx.config.qbittorrent = types.SimpleNamespace(
        host="127.0.0.1", port=8081, username="", password="", api_key=""
    )
    # bt_backup 已收编为 relocate.bt_backup 标量(26-11-11-0259 S1): 与实例身份解耦,
    # 换实例无需再同步路径表 —— 只钉指纹面
    assert mod.relocate_execute(["HA"], "R:/dst2")[0]["cls"] == "started"
    assert len(calls) == 2, "指纹变更必须重新探测"
    # 同配置二次: 指纹未变, 命中 passed 缓存, 不再探
    mod._jobs.clear()
    assert mod.relocate_execute(["HA"], "R:/dst3")[0]["cls"] == "started"
    assert len(calls) == 2, calls


def test_weak_positive_still_probes_and_strong_d_positive_skips(monkeypatch):
    """弱证据任何方向都不短路探测闸(R1#35): B′(种子元数据 size)与 dst visibility_only
    (qB 能列出目标祖先)两面正/负都证不了「qB 与 auto-qb 共享同一命名空间」——
    same_fs_proved/negative 都不成立, run_probe 照走一次(一次性、有指纹缓存);
    src 侧 D 级(实时 size+mtime 比对)positive 维持直接证明短路。"""
    from auto_qb.core.modules import relocate_proof as rp_mod

    # 弱证据(src B′ positive): 预检 proved 不成立 -> 探测闸照走, passed 后正常建账
    mod, locs = _gate_env(monkeypatch)
    monkeypatch.setattr(
        rp_mod,
        "path_evidence",
        lambda ctx, qb_dir, local_dir, files=(), visibility_only=False, sample_k=3: rp_mod.
        Evidence(rp_mod.POSITIVE, rp_mod.LEVEL_BPRIME, "本机 e00.mkv 的 size 与 qB 元数据相等(弱证据)")
        if not visibility_only else rp_mod.Evidence(rp_mod.UNAVAILABLE, "", "目标链路本机不可读"),
    )
    calls = _stub_run_probe(monkeypatch, [_passed()])
    items = mod.relocate_execute(["HA"], "R:/dst")
    assert items[0]["cls"] == "started", items
    assert len(calls) == 1, f"弱证据 positive 必须仍走执行链强探测: {calls}"
    assert len(locs) == 1, locs
    fp = probe_fingerprint(mod._ctx.config.qbittorrent, mod.probe_salt())
    assert mod.probe_get(fp)["status"] == "passed"

    # 强证据(src D 级 positive): 预检已 proved -> 探测闸短路, 零探测直接建账
    mod2, locs2 = _gate_env(monkeypatch)
    monkeypatch.setattr(
        rp_mod,
        "path_evidence",
        lambda ctx, qb_dir, local_dir, files=(), visibility_only=False, sample_k=3: rp_mod.
        Evidence(rp_mod.POSITIVE, rp_mod.LEVEL_D, "代表文件 e00.mkv 的 size+mtime 与本机完全相等")
        if not visibility_only else rp_mod.Evidence(rp_mod.UNAVAILABLE, "", "目标链路本机不可读"),
    )
    calls2 = _stub_run_probe(monkeypatch, [_passed()])
    items2 = mod2.relocate_execute(["HA"], "R:/dst")
    assert items2[0]["cls"] == "started", items2
    assert calls2 == [], "src 侧 D 级 positive 维持 same_fs_proved 短路, 不得重复探测"
    assert len(locs2) == 1, locs2

    # 弱证据判负(src B′ negative)+ dst visibility positive: 不判死 —— 探测闸照走一次
    # (R1#35 评审: 同机场景 qB<5.0 走 B′, 文件改过 size 判负属正常漂移, 交 E1 定夺)
    mod3, locs3 = _gate_env(monkeypatch)
    monkeypatch.setattr(
        rp_mod,
        "path_evidence",
        lambda ctx, qb_dir, local_dir, files=(), visibility_only=False, sample_k=3: rp_mod.
        Evidence(rp_mod.POSITIVE, rp_mod.LEVEL_D, "qB 列目录成功, qB 看得见该目录")
        if visibility_only else rp_mod.Evidence(rp_mod.NEGATIVE, rp_mod.LEVEL_BPRIME, "本机 2 个文件的 size 与 qB 元数据全不等"),
    )
    calls3 = _stub_run_probe(monkeypatch, [_passed()])
    items3 = mod3.relocate_execute(["HA"], "R:/dst")
    assert items3[0]["cls"] == "started", items3
    assert len(calls3) == 1, f"src B′ 判负(弱证据)不得硬拦, 执行链强探测定夺: {calls3}"
    assert len(locs3) == 1, locs3

    # 纯 dst visibility_only positive(src 不可判定): 正证面同样只作弱证据, 照走探测
    mod4, locs4 = _gate_env(monkeypatch)
    monkeypatch.setattr(
        rp_mod,
        "path_evidence",
        lambda ctx, qb_dir, local_dir, files=(), visibility_only=False, sample_k=3: rp_mod.
        Evidence(rp_mod.POSITIVE, rp_mod.LEVEL_D, "qB 列目录成功, qB 看得见该目录")
        if visibility_only else rp_mod.Evidence(rp_mod.UNAVAILABLE, "", "qB 列目录端点不可用"),
    )
    calls4 = _stub_run_probe(monkeypatch, [_passed()])
    items4 = mod4.relocate_execute(["HA"], "R:/dst")
    assert items4[0]["cls"] == "started", items4
    assert len(calls4) == 1, f"dst visibility_only positive 只是弱证据, 必须仍走强探测: {calls4}"
    assert len(locs4) == 1, locs4
