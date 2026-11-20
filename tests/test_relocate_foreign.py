"""外部旧路径种子侦测面(ForeignMixin, 计划 26-11-20-0434 T2/S2)

侦测 = 每拍消费同步层原始 added 差集(store.last_added_diff, T1 批地基: 未过 tracker 匹配门)
+ 四时机全量兜底(启动首轮 / job arm / foreign_torrent 翻 true / qB 重连首轮), 无周期兜底(D13)。
候选 = save_path 归一恰等活跃 job 旧根(场景 A)或终态账 done 直连边旧根(场景 B); 命中后
比对文件清单(D4, 单点复用 _file_map/_plan_files 口径), **一致才记账分类, 不一致只告警**。
本批(T2)只分类不处置: 场景 A/B 接缝为 DEBUG 空操作(T3/T5 落点), 已通知账记 state
relocate.foreign.notified(种子消失清理), 单拍处理有界 FIFO(R4)。

环境口径: 裸 RelocateModule(仿 relocate_exec_support._bare_mod)+ 真 TorrentStore —— 差集
语义(基线轮不算/first-seen/零变化轮清空)由 test_sync.py 的 S2a 五测承重, 本文件只消费。
job 登记直写 mod._jobs(与 test_relocate_history 同款); on_task_line 驱动(含相位机空转,
无 job / 无 rt flag / pending_tag 空 = 零副作用, 与 test_relocate_exec_* 的裸模块同判)。

## 测试计划(每个测试函数一条)

- test_foreign_startup_scan_waits_for_baseline: 时机 1 —— 门激活即置待扫, 基线轮(rounds_applied
  >0)在位才触发; 一次性(不重扫)
- test_foreign_flip_triggers_scan: 时机 2 —— foreign_torrent 假->真翻转(热重载真实信号)触发
  一次; enabled 假->真同信号面(重启用不漏启动首轮, 门激活观测在 enabled 早退之前)
- test_foreign_arm_scan: 时机 3 —— 活跃 job 进收尾窗(armed)下一拍触发一次, 不重复
- test_foreign_reconnect_scan_after_first_round: 时机 4 —— reset_sync(重连单点信号,
  store.sync_epoch)后待首个成功应用轮(rounds_applied 越锚)触发一次
- test_foreign_diff_consumes_unmatched_tracker_torrent: 原始差集直达 —— 无任何 tracker 配置的
  新种子经差集被侦测消费(侦测面不触 tracker 门, D6)
- test_foreign_forms_all_detected: skip 形态(seq_dl/f_l_piece_prio 置位)/非 skip/stopped 状态/
  带分类(category)各形态一律侦测(判定只看 save_path+文件清单)
- test_foreign_forms_consistent_list_required: 清单一致才记账; 不一致只 WARNING(恰一次)+
  mismatch 账; 重复拍不重告警(notified 去重); 种子消失清理条目; 重现 = 重新 first-seen
  重处理(新 first_seen)重告警(mismatch WARNING 恰 +1, 一致面不重告)
- test_foreign_scenario_a_with_phase_and_member_skip: 场景 A 分类正确且相位随 job 现值
  (moving/armed); 活跃 job 成员 hash 幂等跳过(pre-arm 成员 save_path 仍记旧根, 相位机在管)
- test_foreign_inherited_root_hits_scenario_a: 活跃 job 的 plan.inherited 继承根同算场景 A
  (与 scope_hit 继承面同口径), old_root 记继承条目 src
- test_foreign_scenario_b_location_and_state_shape: 场景 B 分类正确(直连边现位置入账);
  notified 条目形状 = root/kind/job_id/phase/location/first_seen(容器 relocate.foreign.notified,
  T5 面板直接消费不改结构)
- test_foreign_resolve_old_root_picks_newest_done_edge: 旧根反查单点 —— 同根多条 done 按
  updated_at 新->旧取最新; failed 不产边(失败不搬回, 旧根落种合法); 未命中返回 None
- test_foreign_member_of_other_active_job_skipped: 命中他 job 旧根但自身是另一活跃 job 成员
  -> 幂等跳过(relocating_hashes 并集口径)
- test_foreign_diff_consumption_is_o_new: 差集消费 O(本拍新增) —— 分类调用次数 = 新到条数,
  与库内存量总数无关(结构性断言: spy 计数)
- test_foreign_fifo_bounded_split_across_ticks: 单拍有界 FIFO —— 25 条候选按预算(10/拍)
  分三拍消化, 池内余量跨拍续; 逐拍「新入账 keys == 捕获池序最前一段」断言钉死「最老先
  处理」(差集是散布序 frozenset, 池序跨拍消费才是 FIFO 承重面); 残值重入池的重复候选由
  notified 去重兜住(零 API 成本)
- test_foreign_pending_vanish_skipped: 池内候选排队期间消失 -> 出队跳过不炸
- test_foreign_pending_cap_drops_oldest: 候选池上限钉测 —— _FOREIGN_PENDING_MAX 压到 3 灌
  5 候选: 池恒 <= 上限, 被丢的是插入序最老者, 逐条带 WARNING(T2 评审钉测)
- test_foreign_bad_candidate_isolated_and_retained: 单候选护栏 —— 畸形 plan.files 候选
  (state 恢复畸形账, _plan_files int() 抛)异常被吞 + WARNING 一次 + 原位留池每拍重试
  (重复异常转 DEBUG), 同拍其它候选照常入账(T2 评审护栏回归)
- test_foreign_dry_run_noop: dry-run 侦测面整体不启动(无扫描/无记账)
- test_foreign_gate_off_noop: 开关关(enabled=false 或 foreign_torrent=false)零动作零记账
- test_foreign_no_periodic_backstop: 无周期兜底(D13) —— 稳态无变化拍不触发全量扫(四时机外零扫描)
"""
import logging
from types import SimpleNamespace

import pytest

from auto_qb.config.models import RelocateConfig
from auto_qb.core.modules import relocate_foreign as rf
from auto_qb.core.modules import relocate_units as ru
from auto_qb.core.modules.relocate_foreign import _FOREIGN_TICK_BUDGET
from auto_qb.core.modules.relocate_mod import RelocateModule
from auto_qb.torrents import TorrentStore

from clock import FakeClock
from helpers import FakeClient, FakeTorrent, _fake_file, capture_logs
from relocate_exec_support import _job

OLD = "R:/old"
NEW = "R:/new"
PLAN_FILES = [["f.bin", 10]]  # job 计划文件清单(相对路径, 大小)


def _env(*, enabled=True, foreign=True, dry_run=False):
    """裸模块 + 真 store + FakeClient 的侦测面环境(仿 relocate_exec_support._bare_mod)

    api 只带 .client(侦测面唯一消费面 = rec.files 经 client 拉文件表); state.data 挂空 dict
    (relocate.foreign.notified 容器由侦测面惰性创建)。ctx.dry_run 可选(dry-run 用例)。
    """
    client = FakeClient()
    store = TorrentStore(client)
    mod = RelocateModule(clock=FakeClock())
    mod._ctx = SimpleNamespace(
        store=store,
        api=SimpleNamespace(client=client),
        config=SimpleNamespace(relocate=RelocateConfig(enabled=enabled, foreign_torrent=foreign)),
        state=SimpleNamespace(data={}),
        dry_run=dry_run,
    )
    return mod, store, client


def _seed(match=True, h="HX"):
    """命中旧根的种子文件表(默认与 PLAN_FILES 一致; match=False 给不一致清单)"""
    if match:
        return [_fake_file("f.bin", 10)]
    return [_fake_file("other.bin", 99)]


def _done_job(mod, jid="jd", src=OLD, dst=NEW, updated_at=100.0):
    """终态账 done job(直连边 src->dst + 计划文件清单)"""
    mod._jobs[jid] = _job(
        jid, phase=ru.PHASE_DONE, src=src, dst=dst, plan={"files": list(PLAN_FILES)}, updated_at=updated_at
    )
    return mod._jobs[jid]


def _spy_scan(mod):
    """_foreign_full_scan 替身: 记录每次触发的 reason(原方法照跑, 池面行为不变)"""
    seen = []
    orig = mod._foreign_full_scan
    mod._foreign_full_scan = lambda reason: (seen.append(reason), orig(reason))[0]
    return seen


def _warn_count(cap):
    return len([m for m in cap.records if m.levelno == logging.WARNING])


# ---------- 四时机全量兜底(D12; 无周期兜底 D13) ----------


def test_foreign_startup_scan_waits_for_baseline():
    """时机 1: 门激活置待扫, 基线轮在位才触发; 一次性不重扫"""
    mod, store, _client = _env()
    seen = _spy_scan(mod)
    mod.on_task_line()  # 门激活但 store 无基线(rounds_applied=0): 不扫
    assert seen == []
    store.refresh([FakeTorrent(hash="H1", name="T", save_path="R:/other")])
    mod.on_task_line()  # 基线在位: 启动首轮扫描一次
    assert seen == ["activation"]
    mod.on_task_line()  # 稳态: 不重扫
    assert seen == ["activation"]


def test_foreign_flip_triggers_scan():
    """时机 2: foreign_torrent 假->真翻转触发一次; enabled 假->真同信号面(重启用不漏扫)"""
    mod, store, _client = _env(foreign=False)
    store.refresh([FakeTorrent(hash="H1", name="T", save_path="R:/other")])
    seen = _spy_scan(mod)
    mod.on_task_line()  # 门关: 无
    assert seen == []
    mod._ctx.config.relocate = RelocateConfig(enabled=True, foreign_torrent=True)  # 热重载换段
    mod.on_task_line()  # 翻转 -> activation 扫
    assert seen == ["activation"]
    mod._ctx.config.relocate = RelocateConfig(enabled=False, foreign_torrent=True)  # 整模块停用
    mod.on_task_line()
    assert seen == ["activation"]
    mod._ctx.config.relocate = RelocateConfig(enabled=True, foreign_torrent=True)  # 重启用
    mod.on_task_line()  # 门激活观测在 enabled 早退之前: 重启用不漏启动首轮
    assert seen == ["activation", "activation"]


def test_foreign_arm_scan():
    """时机 3: 活跃 job 进收尾窗(armed)下一拍触发一次, 不重复"""
    mod, store, _client = _env()
    store.refresh([FakeTorrent(hash="H1", name="T", save_path="R:/other")])
    seen = _spy_scan(mod)
    mod.on_task_line()  # tick1: activation + 收尾窗集合初始化(首拍只记不比对)
    assert seen == ["activation"]
    mod._jobs["j1"] = _job("j1", phase=ru.PHASE_ARMED, src=OLD, dst=NEW)
    mod.on_task_line()  # tick2: 新进收尾窗 -> arm 扫
    assert seen == ["activation", "arm"]
    mod.on_task_line()  # tick3: 窗集合无新进 -> 不重触发
    assert seen == ["activation", "arm"]


def test_foreign_reconnect_scan_after_first_round():
    """时机 4: reset_sync(重连单点信号)后待首个成功应用轮触发一次"""
    mod, store, _client = _env()
    store.refresh([FakeTorrent(hash="H1", name="T", save_path="R:/other")])
    mod.on_task_line()  # tick1: activation
    seen = _spy_scan(mod)
    store.reset_sync()  # 重连(client setter 同款单点): sync_epoch +1, 差集清空
    mod.on_task_line()  # 复位后尚无应用轮: 不扫(重连首轮 = 首个成功应用轮之后)
    assert "reconnect" not in seen
    store.refresh([FakeTorrent(hash="H1", name="T", save_path="R:/other")])  # 重连后首轮(全量)
    mod.on_task_line()  # 首轮已应用: reconnect 扫
    assert seen == ["reconnect"]
    mod.on_task_line()  # 一次性
    assert seen == ["reconnect"]


def test_foreign_no_periodic_backstop():
    """D13: 稳态无变化拍零扫描(四时机之外无周期兜底)"""
    mod, store, _client = _env()
    store.refresh([FakeTorrent(hash="H1", name="T", save_path="R:/other")])
    seen = _spy_scan(mod)
    for _ in range(3):
        mod.on_task_line()
    assert seen == ["activation"]  # 仅启动首轮一次, 之后稳态零扫描


# ---------- 侦测消费面(原始差集直达 + 各形态) ----------


def test_foreign_diff_consumes_unmatched_tracker_torrent():
    """原始差集直达: 无任何 tracker 配置的新种子被侦测消费(面不触 tracker 门, D6)"""
    mod, store, client = _env()
    _done_job(mod)  # 终态账: OLD -> NEW
    store.refresh([])  # 空基线
    mod.on_task_line()  # tick1: activation(空命中)
    # 新种子无任何 tracker 环境(client.trackers_map 空 = 未匹配任何 tracker 配置; qbmanager
    # 的 tracker 门在 tracker_conf 缺失时会跳过它, 但差集在门之前现算(T1), 侦测面照常消费)
    t = FakeTorrent(hash="NT", name="IYUU", save_path=OLD, category="iyuu", state="stoppedUP")
    client.files_map["NT"] = _seed()
    added, _removed = store.refresh([t])  # 重连式全量: diff = {NT}
    assert added == ["NT"] and store.last_added_diff == frozenset({"NT"})
    mod.on_task_line()  # tick2: 差集 -> 池 -> 命中 -> 记账
    notified = mod._state_foreign_notified()
    assert notified["NT"]["kind"] == "B" and notified["NT"]["location"] == NEW


def test_foreign_forms_all_detected():
    """skip 形态/非 skip/stopped/带分类各形态一律侦测(判定只看 save_path + 文件清单)"""
    mod, store, client = _env()
    _done_job(mod)
    forms = [
        FakeTorrent(hash="F1", name="skip-like", save_path=OLD, state="stoppedUP", seq_dl=True, f_l_piece_prio=True),
        FakeTorrent(hash="F2", name="non-skip", save_path=OLD, state="stalledUP"),
        FakeTorrent(hash="F3", name="stopped-dl", save_path=OLD, state="stoppedDL"),
        FakeTorrent(hash="F4", name="categorized", save_path=OLD, state="pausedUP", category="iyuu"),
    ]
    for t in forms:
        client.files_map[t.hash] = _seed()
    store.refresh(forms)
    mod.on_task_line()
    notified = mod._state_foreign_notified()
    assert set(notified) == {"F1", "F2", "F3", "F4"}


# ---------- 文件清单比对(D4)与告警去重 ----------


def test_foreign_forms_consistent_list_required():
    """清单一致才记账; 不一致只 WARNING 恰一次 + mismatch 账; 重复拍不重告; 消失清理; 重现重处理"""
    mod, store, client = _env()
    _done_job(mod)
    client.files_map["OK"] = _seed(match=True)
    client.files_map["MX"] = _seed(match=False)
    store.refresh(
        [
            FakeTorrent(hash="OK", name="same", save_path=OLD),
            FakeTorrent(hash="MX", name="diff", save_path=OLD),
        ]
    )
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod.on_task_line()  # 命中: OK 一致记账; MX 不一致只告警
        notified = mod._state_foreign_notified()
        assert notified["OK"]["kind"] == "B"
        assert notified["MX"]["kind"] == "mismatch"
        assert _warn_count(cap) == 1
        mod.on_task_line()  # 差集残值重入池: notified 去重, 不重告
        assert _warn_count(cap) == 1
        old_first_seen = notified["OK"]["first_seen"]
        store.refresh([])  # 种子全部消失
        mod.on_task_line()
        assert "OK" not in notified
        assert "MX" not in notified
        # 重现 = 重新 first-seen 重处理重告警: 原种子带回 -> 条目重现(新 first_seen),
        # mismatch 再告一次(WARNING +1), 一致种子重记账不重告
        mod._clock.advance(30.0)
        store.refresh(
            [
                FakeTorrent(hash="OK", name="same", save_path=OLD),
                FakeTorrent(hash="MX", name="diff", save_path=OLD),
            ]
        )
        mod.on_task_line()
        notified = mod._state_foreign_notified()
        assert notified["OK"]["kind"] == "B"
        assert notified["MX"]["kind"] == "mismatch"
        assert notified["OK"]["first_seen"] > old_first_seen  # 新首见时刻(假钟推进过)
        assert _warn_count(cap) == 2  # 恰再告一次(仅 mismatch; OK 一致面不告警)


# ---------- 分类(A/B/继承/成员幂等/反查单点) ----------


def test_foreign_scenario_a_with_phase_and_member_skip():
    """场景 A 分类正确且相位随 job 现值; 活跃 job 成员 hash 幂等跳过"""
    mod, store, client = _env()
    mod._jobs["ja"] = _job(
        "ja", phase=ru.PHASE_MOVING, src=OLD, dst=NEW, hashes=("MEM", ), plan={"files": list(PLAN_FILES)}
    )
    client.files_map["MEM"] = _seed()
    client.files_map["EXT"] = _seed()
    store.refresh(
        [
            FakeTorrent(hash="MEM", name="member", save_path=OLD),  # pre-arm 成员: save_path 仍记旧根
            FakeTorrent(hash="EXT", name="foreign", save_path=OLD),
        ]
    )
    mod.on_task_line()
    notified = mod._state_foreign_notified()
    assert "MEM" not in notified  # 相位机在管: 幂等跳过
    assert notified["EXT"]["kind"] == "A" and notified["EXT"]["phase"] == "moving"
    assert notified["EXT"]["location"] == NEW
    mod._jobs["ja"] = _job(
        "ja", phase=ru.PHASE_ARMED, src=OLD, dst=NEW, hashes=("MEM", ), plan={"files": list(PLAN_FILES)}
    )
    client.files_map["EXT2"] = _seed()
    store.refresh(
        [
            FakeTorrent(hash="MEM", name="member", save_path=OLD),
            FakeTorrent(hash="EXT", name="foreign", save_path=OLD),
            FakeTorrent(hash="EXT2", name="foreign2", save_path=OLD),
        ]
    )
    mod.on_task_line()
    notified = mod._state_foreign_notified()
    assert notified["EXT2"]["kind"] == "A" and notified["EXT2"]["phase"] == "armed"


def test_foreign_inherited_root_hits_scenario_a():
    """活跃 job 的 plan.inherited 继承根同算场景 A(old_root 记继承条目 src)"""
    mod, store, client = _env()
    plan = {
        "files":
            list(PLAN_FILES),
        "inherited":
            [
                {
                    "job_id": "jp",
                    "src": "R:/prev",
                    "dst": "R:/mid",
                    "scope": "R:/prev",
                    "alias_kind": "dir",
                    "alias_paths": ["R:/prev/alias"],
                    "link_kind": "junction",
                }
            ],
    }
    mod._jobs["ja"] = _job("ja", phase=ru.PHASE_MOVED, src=OLD, dst=NEW, plan=plan)
    client.files_map["INH"] = _seed()
    store.refresh([FakeTorrent(hash="INH", name="prev-root", save_path="R:/prev")])
    mod.on_task_line()
    notified = mod._state_foreign_notified()
    assert notified["INH"]["kind"] == "A"
    assert notified["INH"]["job_id"] == "ja" and notified["INH"]["phase"] == "moved"
    assert notified["INH"]["root"] == ru._norm("R:/prev")


def test_foreign_scenario_b_location_and_state_shape():
    """场景 B 分类正确(直连边现位置入账); 条目形状与容器路径(T5 消费面钉扎)"""
    mod, store, client = _env()
    _done_job(mod)
    client.files_map["BX"] = _seed()
    store.refresh([FakeTorrent(hash="BX", name="done-root", save_path=OLD)])
    mod.on_task_line()
    notified = mod._state_foreign_notified()
    assert notified["BX"] == {
        "root": ru._norm(OLD),
        "kind": "B",
        "job_id": "jd",
        "phase": "done",
        "location": NEW,
        "first_seen": mod._ctx.state.data["relocate"]["foreign"]["notified"]["BX"]["first_seen"],
    }
    assert isinstance(notified["BX"]["first_seen"], float)  # 挂钟首见时刻(展示用)
    # 容器路径钉扎: state.data["relocate"]["foreign"]["notified"](T5 面板数据源)
    assert mod._ctx.state.data["relocate"]["foreign"]["notified"] is notified


def test_foreign_resolve_old_root_picks_newest_done_edge():
    """旧根反查单点: 同根多条 done 按 updated_at 新->旧取最新; failed 不产边; 未命中 None"""
    mod, _store, _client = _env()
    mod._jobs = {
        "j1": _job("j1", phase=ru.PHASE_DONE, src=OLD, dst="R:/b1", updated_at=100.0),
        "j2": _job("j2", phase=ru.PHASE_DONE, src=OLD, dst="R:/b2", updated_at=200.0),
        "jf": _job("jf", phase=ru.PHASE_FAILED, src=OLD, dst="R:/x"),
    }
    edge = mod._foreign_resolve_old_root(OLD)
    assert (edge.job_id, edge.dst, edge.phase) == ("j2", "R:/b2", "done")
    assert mod._foreign_resolve_old_root("R:/nowhere") is None
    assert mod._foreign_resolve_old_root("") is None


def test_foreign_member_of_other_active_job_skipped():
    """命中他 job 旧根但自身是另一活跃 job 成员 -> 幂等跳过(relocating_hashes 并集口径)"""
    mod, store, client = _env()
    _done_job(mod)  # 旧根 OLD
    mod._jobs["jb"] = _job("jb", phase=ru.PHASE_MOVING, src="R:/elsewhere", dst="R:/x", hashes=("MB", ))
    client.files_map["MB"] = _seed()
    store.refresh([FakeTorrent(hash="MB", name="other-job-member", save_path=OLD)])
    mod.on_task_line()
    assert "MB" not in mod._state_foreign_notified()


# ---------- 差集消费成本与有界 FIFO(R4) ----------


def test_foreign_diff_consumption_is_o_new():
    """差集消费 O(本拍新增): 分类调用次数 = 新到条数, 与库内存量无关(结构性断言)"""
    mod, store, client = _env()
    _done_job(mod)
    baseline = [FakeTorrent(hash=f"B{i:03d}", name=f"T{i}", save_path=f"R:/lib/t{i}") for i in range(200)]
    store.refresh(baseline)
    mod.on_task_line()  # tick1: activation 扫(存量 200 条全判定, spy 未装)
    calls = []
    orig = mod._foreign_classify
    mod._foreign_classify = lambda rec: (calls.append(rec.hash), orig(rec))[1]
    client.files_map["NEW1"] = _seed()
    store.refresh(baseline + [FakeTorrent(hash="NEW1", name="new", save_path=OLD)])  # 新到 1 条
    mod.on_task_line()  # tick2: 差集 {NEW1} -> 恰分类 1 次(存量零遍历)
    assert calls == ["NEW1"]


def test_foreign_fifo_bounded_split_across_ticks():
    """单拍有界 FIFO: 25 条候选按预算分三拍消化, 池内余量跨拍续; 残值重入池由 notified 去重兜住

    「最老先处理」钉法: 差集是 frozenset(散布序, 跨进程不定), 单批内的先后无业务语义 ——
    FIFO 的承重面是**池序跨拍消费**: 池(dict)保插入序, 每拍恰消费池序最前一段, 后进者
    不得插队(消费退化 LIFO 时下方逐拍 keys 断言必红)。散布序由捕获的池序现算, 不手抄。
    """
    mod, store, client = _env()
    _done_job(mod)
    store.refresh([])  # 空基线
    mod.on_task_line()  # tick1: activation(空命中)
    batch = [FakeTorrent(hash=f"N{i:02d}", name=f"n{i}", save_path=OLD) for i in range(25)]
    for t in batch:
        client.files_map[t.hash] = _seed()
    store.refresh(batch)  # diff = 25
    mod.on_task_line()  # tick2: 预算 10 -> 池序最前 10 条入账, 余 15 按原序留池
    notified = mod._state_foreign_notified()
    assert len(notified) == _FOREIGN_TICK_BUDGET and len(mod._foreign_pending) == 15
    processed2 = set(notified)
    remaining = list(mod._foreign_pending)  # 入池序去头后的余量(老->新, dict 保序)
    assert len(remaining) == 15 and not (processed2 & set(remaining))
    mod.on_task_line()  # tick3: 残值重入池(dup 由去重兜住), 恰消费池序最前 10 条
    new3 = set(notified) - processed2
    assert len(new3) == _FOREIGN_TICK_BUDGET and new3 == set(remaining[:_FOREIGN_TICK_BUDGET])
    mod.on_task_line()  # tick4: 清尾(remaining[10:] 5 条真候选)+ 重入池 dup 免费出队
    assert set(notified) == processed2 | set(remaining) and not mod._foreign_pending


def test_foreign_pending_vanish_skipped():
    """池内候选排队期间消失 -> 出队跳过不炸(存活面由 notified 清理兜底)"""
    mod, store, client = _env()
    _done_job(mod)
    store.refresh([])
    mod.on_task_line()
    batch = [FakeTorrent(hash=f"V{i:02d}", name=f"v{i}", save_path=OLD) for i in range(15)]
    for t in batch:
        client.files_map[t.hash] = _seed()
    store.refresh(batch)
    mod.on_task_line()  # 预算 10, 池余 5(V10..V14)
    assert len(mod._foreign_pending) == 5
    store.refresh([t for t in batch if t.hash not in {"V10", "V11"}])  # 排队期间消失 2 条
    mod.on_task_line()  # 消失候选出队跳过, 其余入账
    notified = mod._state_foreign_notified()
    assert set(notified) == {t.hash for t in batch} - {"V10", "V11"}
    assert not mod._foreign_pending


def test_foreign_pending_cap_drops_oldest(monkeypatch):
    """候选池上限钉测(T2 评审): 池恒 <= 上限, 被丢的是插入序最老者且逐条带 WARNING"""
    monkeypatch.setattr(rf, "_FOREIGN_PENDING_MAX", 3)
    mod, _store, _client = _env()
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        for h in ("PA", "PB", "PC", "PD", "PE"):
            mod._foreign_enqueue(h)
    assert list(mod._foreign_pending) == ["PC", "PD", "PE"]  # 最老 PA/PB 被丢, 插入序保留
    assert len(mod._foreign_pending) == 3  # 恒 <= 上限
    warnings = [m.getMessage() for m in cap.records if m.levelno == logging.WARNING]
    assert len(warnings) == 2
    assert "PA" in warnings[0] and "PB" in warnings[1]  # 丢最老者, 各告警一条


def test_foreign_bad_candidate_isolated_and_retained():
    """单候选护栏(T2 评审): 畸形账候选异常被吞 + WARNING 一次 + 原位留池, 同拍其它候选照常处理

    现实触发面 = state 恢复畸形 plan.files(ExecMixin._plan_files 的 int(b) 抛 ValueError)。
    """
    mod, store, client = _env()
    # 畸形账(大小列非数字)与健康账并存: BAD 命中畸形账, GOOD 命中健康账
    mod._jobs["jd"] = _job("jd", phase=ru.PHASE_DONE, src=OLD, dst=NEW, plan={"files": [["f.bin", "not-a-number"]]})
    mod._jobs["jg"] = _job("jg", phase=ru.PHASE_DONE, src="R:/old2", dst="R:/new2", plan={"files": list(PLAN_FILES)})
    store.refresh([])  # 空基线
    mod.on_task_line()  # tick1: activation(空命中)
    client.files_map["BAD"] = _seed()
    client.files_map["GOOD"] = _seed()
    store.refresh(
        [
            FakeTorrent(hash="BAD", name="bad", save_path=OLD),
            FakeTorrent(hash="GOOD", name="good", save_path="R:/old2"),
        ]
    )
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod.on_task_line()  # tick2: BAD 异常被吞留池, GOOD 照常入账
        notified = mod._state_foreign_notified()
        assert set(notified) == {"GOOD"}  # 同拍其它候选不受拖累
        assert notified["GOOD"]["kind"] == "B" and notified["GOOD"]["job_id"] == "jg"
        assert list(mod._foreign_pending) == ["BAD"]  # 坏候选原位留池
        assert _warn_count(cap) == 1
        assert any("BAD" in m.getMessage() for m in cap.records if m.levelno == logging.WARNING)
        mod.on_task_line()  # tick3: 留池候选重试, 重复异常转 DEBUG 不重告
        assert _warn_count(cap) == 1
        assert list(mod._foreign_pending) == ["BAD"]  # 仍留池(账面没修, 每拍重试一次)


# ---------- 闸门与关闭面 ----------


def test_foreign_dry_run_noop():
    """dry-run 侦测面整体不启动(无扫描/无记账)"""
    mod, store, client = _env(dry_run=True)
    seen = _spy_scan(mod)
    _done_job(mod)
    client.files_map["DX"] = _seed()
    store.refresh([FakeTorrent(hash="DX", name="dry", save_path=OLD)])
    mod.on_task_line()
    assert seen == []
    assert mod._ctx.state.data == {}


@pytest.mark.parametrize("kw", [{"enabled": False}, {"foreign": False}])
def test_foreign_gate_off_noop(kw):
    """开关关(enabled=false / foreign_torrent=false)零动作零记账"""
    mod, store, client = _env(**kw)
    seen = _spy_scan(mod)
    _done_job(mod)
    client.files_map["GX"] = _seed()
    store.refresh([FakeTorrent(hash="GX", name="off", save_path=OLD)])
    mod.on_task_line()
    assert seen == []
    assert mod._ctx.state.data == {}
