"""外部旧路径种子侦测与场景 A 纳入面(ForeignMixin, 计划 26-11-20-0434; T2/S2 侦测, T3/S3 纳入)

侦测 = 每拍消费同步层原始 added 差集(store.last_added_diff, T1 批地基: 未过 tracker 匹配门)
+ 四时机全量兜底(启动首轮 / job arm / foreign_torrent 翻 true / qB 重连首轮), 无周期兜底(D13)。
候选 = save_path 归一恰等活跃 job 旧根(场景 A)或终态账 done 直连边旧根(场景 B); 命中后
比对文件清单(D4, 单点复用 _file_map/_plan_files 口径), **一致才记账分类, 不一致只告警**。
场景 A 接缝(T3)= 零破坏纳入收尾: job.hashes 追加 + 收尾窗读-改-写 spec.members(journal
零写)+ pre-armed 暂停挂恢复账(D10)+ pending_tag 增量补打; 场景 B 接缝仍空操作(T5 落点)。
已通知账记 state relocate.foreign.notified(种子消失清理), 单拍处理有界 FIFO(R4)。

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

场景 A 纳入(T3/S3):

- test_include_armed_appends_job_hashes: 收尾窗(armed)纳入 = job.hashes 追加(_set_job 落账
  + relocating 并集即时含新成员), notified 记账不变; spec 不在只告警不造账
- test_include_armed_extends_spec_and_rewrite_list: 收尾 spec 读-改-写 members 同形追加;
  改写清单(pending_members)含新成员; journal 零写(盘上无 <job>.json); armed 到达不暂停(D10)
- test_include_spec_dual_hash_v2: 新成员 hash_v1/v2 双 hash(arm_members_of 单点口径,
  BT_backup <hash>.torrent 现算); bt_backup 取 spec 在场值
- test_include_spec_idempotent_on_repeat: 重复纳入(直接重调接缝)无重复 hashes/members
  条目、无重复动作(黄金法则 1)
- test_include_delete_chain_gate_exempts_member: 删链门成员豁免 —— 纳入前新种子是删链门
  依赖, 纳入后 job.hashes 成员豁免(_chain_gate_deps 读 job.hashes 派生)
- test_include_verify_covers_member: 核验覆盖 —— 纳入后 _all_at_dst 要求新成员到位
  (实时派生自 job.hashes, 零额外接线)
- test_include_prearm_pause_and_resume_account: pre-armed(moved)到达运行态种子纳入即暂停
  + 入 resume_hashes; _resume_members 随既有出口恢复并开确认账(D10)
- test_include_prearm_stopped_not_paused: pre-armed 到达已停种子: 不暂停不挂恢复账
  (保守默认: 用户停的种子不因纳入被 arm 拉起), 纳入照做
- test_include_prearm_arm_spec_covers_new_member: pre-armed 纳入后 arm 侧 _write_arm_spec
  按 job.hashes 现算落盘, 新成员自动进改写清单(pre-arm 相位无 spec, arm 时自动覆盖)
- test_include_pending_tag_incremental: 镜像已在 add 态时新成员单点补打待收尾标签恰一次
  (既有 _sync_pending_tag 一次性缓存缺口); 镜像态不翻动
- test_include_pending_tag_off_no_qb_write: 标签镜像关闭(缺省空标签): 纳入确实发生且
  零标签 qB 写(评审 nit 5: 钉住纳入前提)
- test_include_pending_tag_failure_resets_mirror: 补打失败摘镜像缓存 + 计数告警, 交每拍
  补写面按退避自愈(不自建重试回路)
- test_include_job_gone_or_terminal_noop: job 不在/已终态(竞态面)接缝零动作不炸
- test_include_two_members_same_tick: 同拍多候选纳入同一 job: 逐个在最新账上追加,
  无互相覆盖无重复

评审修复回归(26-11-21 T3 首轮评审):

- test_include_prearm_resume_account_merges_held_members: pre-armed 纳入的按住账**并入**
  不覆盖(blocker 回归)—— _start_job 按住的原成员账保留, arm 时新旧成员一并恢复进确认账
- test_include_armed_absence_shrinks_included_member: R9 收缩集成(minor)—— 纳入成员被删,
  连续 ABSENCE_SHRINK_ROUNDS 拍权威缺席后从 job.hashes 收缩, 不计失败, 让路面随收缩撤出
- test_include_pending_tag_restart_single_full_add: 重启后镜像缓存空(nit 3)—— _set_job
  内联补写面对全成员统一 add 恰一次, 接缝(was_add 门控)不再单发, 同拍零双写
"""
import logging
from dataclasses import replace
from types import SimpleNamespace

import pytest

from auto_qb.config.models import RelocateConfig
from auto_qb.core import fastresume as frmod
from auto_qb.core.qbapi import QbApi
from auto_qb.hr.bencode import compute_infohashes
from auto_qb.core.modules import relocate_foreign as rf
from auto_qb.core.modules import relocate_units as ru
from auto_qb.core.modules.relocate_foreign import _FOREIGN_TICK_BUDGET
from auto_qb.core.modules.relocate_mod import RelocateModule
from auto_qb.infra import relocate_journal
from auto_qb.torrents import TorrentStore

from clock import FakeClock
from helpers import FakeClient, FakeTorrent, _fake_file, capture_logs
from relocate_exec_support import _job

OLD = "R:/old"
NEW = "R:/new"
PLAN_FILES = [["f.bin", 10]]  # job 计划文件清单(相对路径, 大小)

# 每用例的兜底 data_dir(_foreign_data_dir autouse 夹具注入; _env 缺省取用, 显式传参恒优先)
_ENV_DATA_DIR: str = ""


@pytest.fixture(autouse=True)
def _foreign_data_dir(tmp_path):
    """每用例给 _env() 缺省钉一个 tmp data_dir(红线卫生; 计划 26-11-20-0434 T3 补修)

    本文件的盘面写点只有一处入口 = 模块侧 `self._data_dir()`(读 config.data_dir; journal/
    spec 落盘、daemon 心跳/对账读全部经它): T2 的 armed 驱动用例(on_task_line 推进相位机)
    在对账 ACT_REBUILD 时 write_journal(self._data_dir(), ...), T3 纳入面 read/write_spec
    同走该点 —— data_dir 落空串会触发 _data_dir() 的 auto-qb-data 兜底 = 测试写进生产红线
    目录(T2 起既有, 残留 j1.json/ja.json 即此来)。本夹具把缺省钉到 tmp_path, 全部用例
    (含 armed 驱动 / write_journal 路径)永不落兜底; 显式传 data_dir 的用例不受影响。
    函数级 autouse + 模块级游标复位: xdist 每 worker 独立进程, 无跨 worker 状态。
    """
    global _ENV_DATA_DIR
    _ENV_DATA_DIR = str(tmp_path)
    yield
    _ENV_DATA_DIR = ""


def _env(*, enabled=True, foreign=True, dry_run=False, data_dir=None):
    """裸模块 + 真 store + FakeClient 的侦测/纳入面环境(仿 relocate_exec_support._bare_mod)

    api = .client + 纳入面的 qB 写方法直通(见下方注释); state.data 挂空 dict
    (relocate.foreign.notified 容器由侦测面惰性创建)。ctx.dry_run 可选(dry-run 用例)。
    data_dir 缺省(None)= 取 autouse 夹具钉的 tmp_path —— 本文件盘面写点全走模块侧
    _data_dir()(journal/spec/对账读), 缺省即保证零 auto-qb-data 兜底触碰(红线目录);
    显式传参恒优先(与夹具同值或自定路径均可)。
    """
    client = FakeClient()
    store = TorrentStore(client)
    mod = RelocateModule(clock=FakeClock())
    # api 包装面 = 侦测面(.client) + T3 纳入面的 qB 写方法(pause/resume/add_tags, 与生产
    # QbApi 同名直通 client —— client.calls 照记, 断言面不变)
    api = SimpleNamespace(
        client=client,
        torrents_pause=client.torrents_pause,
        torrents_resume=client.torrents_resume,
        torrents_add_tags=client.torrents_add_tags,
        torrents_remove_tags=client.torrents_remove_tags,
    )
    mod._ctx = SimpleNamespace(
        store=store,
        api=api,
        config=SimpleNamespace(
            relocate=RelocateConfig(enabled=enabled, foreign_torrent=foreign),
            data_dir=data_dir if data_dir is not None else _ENV_DATA_DIR,
        ),
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


def test_foreign_scenario_a_with_phase_and_member_skip(tmp_path):
    """场景 A 分类正确且相位随 job 现值; 活跃 job 成员 hash 幂等跳过"""
    mod, store, client = _env(data_dir=str(tmp_path))
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


# ---------- 场景 A 纳入(T3/S3) ----------


def _hit(h="EXT", job_id="ja", phase=ru.PHASE_ARMED, old_root=OLD, location=NEW):
    """场景 A 接缝入参构造(判定面产出的 ForeignHit 同形; 直调接缝用例用)"""
    return rf.ForeignHit(
        hash=h, save_path=old_root, scenario="A", job_id=job_id, phase=phase, old_root=old_root, location=location
    )


def _armed_job(jid="ja", phase=ru.PHASE_ARMED, hashes=("MEM", ), alias_kind="", alias_paths=(), resume_hashes=()):
    """收尾窗 job(与命中旧根同根, 计划文件清单与 _seed 一致)"""
    return _job(
        jid,
        phase=phase,
        src=OLD,
        dst=NEW,
        hashes=hashes,
        alias_kind=alias_kind,
        alias_paths=alias_paths,
        resume_hashes=resume_hashes,
        plan={"files": list(PLAN_FILES)}
    )


def _foreign_rec(client, h="EXT", state="stalledUP"):
    """命中旧根且清单一致的外部种子(rec + 文件表)"""
    client.files_map[h] = _seed()
    return FakeTorrent(hash=h, name="foreign", save_path=OLD, state=state)


def test_include_armed_appends_job_hashes(tmp_path):
    """收尾窗纳入: job.hashes 追加落账, relocating 并集即时含新成员; spec 不在只告警不造账"""
    mod, store, client = _env(data_dir=str(tmp_path))
    mod._jobs["ja"] = _armed_job()
    store.refresh([FakeTorrent(hash="MEM", name="member", save_path=OLD), _foreign_rec(client)])
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod.on_task_line()  # activation 扫 -> 命中 -> 纳入(armed, 收尾窗)
    job = mod.get_job("ja")
    assert job.hashes == ("MEM", "EXT") and not job.is_terminal
    assert mod._state_foreign_notified()["EXT"]["kind"] == "A"
    assert "EXT" in mod.relocating_hashes()  # 让路/拦截成员面派生即时覆盖
    assert mod._data_dir() == str(tmp_path)
    assert not (tmp_path / "relocate" / "ja.spec.json").exists()  # spec 不在: 只告警不造账
    assert any("收尾 spec 不在" in m.getMessage() for m in cap.records if m.levelno == logging.WARNING)


def test_include_armed_extends_spec_and_rewrite_list(tmp_path):
    """收尾 spec 读-改-写 members 同形追加; 改写清单含新成员; journal 零写; armed 到达不暂停

    直调接缝(侦测->接缝的管线接线由 test_include_armed_appends_job_hashes 钉): on_task_line
    的相位机推进会同拍走对账(ACT_REBUILD 写 journal 到 tmp), 会污染「journal 零写」断言面。
    """
    mod, store, client = _env(data_dir=str(tmp_path))
    mod._jobs["ja"] = _armed_job()
    assert mod._write_arm_spec(mod.get_job("ja"))  # arm 侧既有落盘: members = [MEM]
    store.refresh([_foreign_rec(client)])
    mod._foreign_on_scenario_a(_hit())
    spec = relocate_journal.read_spec(str(tmp_path), "ja")
    assert spec["members"] == [{"hash_v1": "MEM", "hash_v2": ""}, {"hash_v1": "EXT", "hash_v2": ""}]
    # 改写清单 = spec.members - 已收口(journal.rewrites 现算): 旧成员已收口, 新成员在列
    pending = relocate_journal.pending_members(spec, {"MEM": {"status": "rewritten", "ts": 1.0}})
    assert [relocate_journal.member_key(m) for m in pending] == ["EXT"]
    assert not (tmp_path / "relocate" / "ja.json").exists()  # journal 零写(R8)
    assert ("pause", ["EXT"]) not in client.calls  # armed/rewritten 到达不动(D10)
    assert mod.get_job("ja").hashes == ("MEM", "EXT")


def test_include_spec_dual_hash_v2(tmp_path):
    """新成员双 hash: hash_v2 经 BT_backup <hash>.torrent 现算(arm_members_of 单点口径)"""
    mod, store, client = _env(data_dir=str(tmp_path))
    mod._ctx.config.relocate = RelocateConfig(enabled=True, foreign_torrent=True, bt_backup=str(tmp_path / "backup"))
    info = {b"name": b"foreignmember", b"piece length": 16384, b"pieces": b"\x00" * 20, b"length": 1}
    blob = frmod.bencode({b"announce": b"http://tracker.example/ann", b"info": info})
    v1, v2, _info = compute_infohashes(blob)
    (tmp_path / "backup").mkdir()
    (tmp_path / "backup" / f"{v1}.torrent").write_bytes(blob)
    mod._jobs["ja"] = _armed_job()
    assert mod._write_arm_spec(mod.get_job("ja"))  # spec 带 bt_backup 字段
    store.refresh([FakeTorrent(hash=v1, name="foreign", save_path=OLD)])
    client.files_map[v1] = _seed()
    mod._foreign_on_scenario_a(_hit(h=v1))
    spec = relocate_journal.read_spec(str(tmp_path), "ja")
    assert spec["members"][-1] == {"hash_v1": v1, "hash_v2": v2}
    assert mod.get_job("ja").hashes == ("MEM", v1)


def test_include_spec_idempotent_on_repeat(tmp_path):
    """重复纳入(直接重调接缝, 状态恢复重放同形): 零重复条目零重复动作(黄金法则 1)"""
    mod, store, client = _env(data_dir=str(tmp_path))
    mod._jobs["ja"] = _armed_job()
    assert mod._write_arm_spec(mod.get_job("ja"))
    store.refresh([_foreign_rec(client)])
    mod.on_task_line()
    spec1 = relocate_journal.read_spec(str(tmp_path), "ja")
    calls1 = list(client.calls)
    mod._foreign_on_scenario_a(_hit())  # 直接重调: 幂等收口
    assert relocate_journal.read_spec(str(tmp_path), "ja") == spec1
    assert mod.get_job("ja").hashes == ("MEM", "EXT")
    assert client.calls == calls1  # 无第二笔动作(pause/spec/tag 均不重发)


def test_include_delete_chain_gate_exempts_member(tmp_path):
    """删链门成员豁免: 纳入前新种子是删链门依赖(收尾卡死根因), 纳入后按成员豁免"""
    mod, store, client = _env(data_dir=str(tmp_path))
    mod._jobs["ja"] = _armed_job(alias_kind="dir", alias_paths=("R:/old/l", ))
    store.refresh([FakeTorrent(hash="MEM", name="member", save_path=NEW), _foreign_rec(client)])
    job = mod.get_job("ja")
    assert mod._chain_gate_deps(job) == [("EXT", OLD)]  # 纳入前: 第三方依赖(收尾被卡)
    mod._foreign_on_scenario_a(_hit())
    job = mod.get_job("ja")  # 接缝落账换代, 重取最新账(_chain_gate_deps 读入参 job.hashes)
    assert mod._chain_gate_deps(job) == []  # 纳入后: 成员豁免(members 集 = job.hashes)


def test_include_verify_covers_member(tmp_path):
    """核验覆盖: 纳入后 _all_at_dst 要求新成员到位(实时派生自 job.hashes, 零额外接线)"""
    mod, store, client = _env(data_dir=str(tmp_path))
    mod._jobs["ja"] = _armed_job()
    store.refresh([FakeTorrent(hash="MEM", name="member", save_path=NEW), _foreign_rec(client)])
    assert mod._all_at_dst(mod.get_job("ja")) is True  # 纳入前: 新种子不在核验集合
    mod._foreign_on_scenario_a(_hit())
    assert mod._all_at_dst(mod.get_job("ja")) is False  # 纳入后: 新成员未到位, 核验等它
    store.by_hash["EXT"].save_path = NEW
    assert mod._all_at_dst(mod.get_job("ja")) is True


def test_include_prearm_pause_and_resume_account(tmp_path):
    """pre-armed(moved)到达运行态种子: 纳入即暂停 + 入 resume_hashes; 既有恢复面随成员恢复"""
    mod, store, client = _env(data_dir=str(tmp_path))
    mod._jobs["ja"] = _armed_job(phase=ru.PHASE_MOVED)
    store.refresh([_foreign_rec(client, state="stalledUP")])
    mod._foreign_on_scenario_a(_hit(phase=ru.PHASE_MOVED))
    job = mod.get_job("ja")
    assert ("pause", ["EXT"]) in client.calls
    assert job.hashes == ("MEM", "EXT") and job.resume_hashes == ("EXT", )
    assert "EXT" in mod.relocating_hashes()
    mod._resume_members(job)  # arm/fail/cancel 共用的既有恢复出口
    assert ("resume", ["EXT"]) in client.calls
    assert mod.get_job("ja").resume_pending == ("EXT", )  # 恢复确认账开账(_reconcile_resume_pending 接管)


def test_include_prearm_stopped_not_paused(tmp_path):
    """pre-armed 到达已停种子: 不暂停不挂恢复账(用户停的不被 arm 拉起), 纳入照做"""
    mod, store, client = _env(data_dir=str(tmp_path))
    mod._jobs["ja"] = _armed_job(phase=ru.PHASE_MOVED)
    store.refresh([_foreign_rec(client, state="stoppedUP")])
    mod._foreign_on_scenario_a(_hit(phase=ru.PHASE_MOVED))
    job = mod.get_job("ja")
    assert ("pause", ["EXT"]) not in client.calls
    assert job.hashes == ("MEM", "EXT") and job.resume_hashes == ()


def test_include_prearm_arm_spec_covers_new_member(tmp_path):
    """pre-armed 纳入后 arm 侧 spec 按 job.hashes 现算落盘: 新成员自动进改写清单与恢复名单"""
    mod, store, client = _env(data_dir=str(tmp_path))
    mod._jobs["ja"] = _armed_job(phase=ru.PHASE_MOVED)
    store.refresh([_foreign_rec(client)])
    mod._foreign_on_scenario_a(_hit(phase=ru.PHASE_MOVED))
    mod._set_job(replace(mod.get_job("ja"), phase=ru.PHASE_ARMED, armed_at=mod._clock.now()))
    assert mod._write_arm_spec(mod.get_job("ja"))
    spec = relocate_journal.read_spec(str(tmp_path), "ja")
    assert [m["hash_v1"] for m in spec["members"]] == ["MEM", "EXT"]
    mod._resume_members(mod.get_job("ja"))  # _arm 同位: resume_hashes 含纳入成员
    assert ("resume", ["EXT"]) in client.calls


def test_include_pending_tag_incremental(tmp_path):
    """镜像已在 add 态: 新成员单点补打待收尾标签恰一次(一次性缓存缺口的增量面)"""
    mod, store, client = _env(data_dir=str(tmp_path))
    mod._ctx.config.relocate = RelocateConfig(enabled=True, foreign_torrent=True, pending_tag="aqb-finalize")
    mod._jobs["ja"] = replace(_armed_job(), tag_on=True)
    mod._tag_applied["ja"] = "add"  # 模拟 armed 时已加过标签(缓存一次性: 不含后到成员)
    store.refresh([_foreign_rec(client)])
    mod._foreign_on_scenario_a(_hit())
    assert client.calls == [("add_tags", "aqb-finalize")]  # 恰一次, 只补新成员(不重打旧成员)
    assert mod.get_job("ja").tag_on is True and mod._tag_applied["ja"] == "add"  # 镜像态不翻动


def test_include_pending_tag_off_no_qb_write(tmp_path):
    """标签镜像关闭(缺省空标签): 纳入确实发生且零标签 qB 写(评审 nit 5: 钉住纳入前提)"""
    mod, store, client = _env(data_dir=str(tmp_path))
    mod._jobs["ja"] = _armed_job()
    store.refresh([_foreign_rec(client)])
    mod.on_task_line()
    assert mod.get_job("ja").hashes == ("MEM", "EXT")  # 纳入确实发生(零 qB 写才有意义)
    assert not [c for c in client.calls if c[0].startswith(("add_tags", "remove_tags"))]


def test_include_pending_tag_failure_resets_mirror(tmp_path, monkeypatch):
    """补打失败: 摘镜像缓存 + 计数告警, 交每拍补写面按退避自愈(不自建重试回路)"""
    mod, store, client = _env(data_dir=str(tmp_path))
    mod._ctx.config.relocate = RelocateConfig(enabled=True, foreign_torrent=True, pending_tag="aqb-finalize")
    mod._jobs["ja"] = _armed_job()
    mod._tag_applied["ja"] = "add"

    def _boom(**kw):
        raise RuntimeError("qb down")

    monkeypatch.setattr(mod._ctx.api, "torrents_add_tags", _boom)  # 桩打在 api 包装面(生产消费面)
    store.refresh([_foreign_rec(client)])
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod._foreign_on_scenario_a(_hit())
    assert mod.get_job("ja").hashes == ("MEM", "EXT")  # 纳入不受补打失败影响
    assert "ja" not in mod._tag_applied and mod._tag_failures == 1
    assert any("补打失败" in m.getMessage() for m in cap.records if m.levelno == logging.WARNING)


def test_include_job_gone_or_terminal_noop(tmp_path):
    """job 不在(撤销竞态)/已终态: 接缝零动作不炸"""
    mod, store, client = _env(data_dir=str(tmp_path))
    mod._foreign_on_scenario_a(_hit(job_id="nope"))  # 账不在: 静默收口
    assert mod._jobs == {} and mod._state_foreign_notified() == {}
    mod._jobs["jd"] = _armed_job(jid="jd", phase=ru.PHASE_DONE)
    mod._foreign_on_scenario_a(_hit(job_id="jd"))  # 已终态: 不往终态账写成员
    assert mod.get_job("jd").hashes == ("MEM", )


def test_include_two_members_same_tick(tmp_path):
    """同拍多候选纳入同一 job: 逐个在最新账上追加, 无互相覆盖无重复"""
    mod, store, client = _env(data_dir=str(tmp_path))
    mod._jobs["ja"] = _armed_job()
    assert mod._write_arm_spec(mod.get_job("ja"))
    store.refresh([_foreign_rec(client, h="E1"), _foreign_rec(client, h="E2")])
    mod.on_task_line()
    job = mod.get_job("ja")
    assert len(job.hashes) == 3 and set(job.hashes) == {"MEM", "E1", "E2"}  # 差集散布序, 只断集合
    spec = relocate_journal.read_spec(str(tmp_path), "ja")
    assert {m["hash_v1"] for m in spec["members"]} == {"MEM", "E1", "E2"}


# ---------- 评审修复回归(26-11-21 T3 首轮评审) ----------


def test_include_prearm_resume_account_merges_held_members(tmp_path):
    """pre-armed 纳入的按住账**并入**不覆盖(评审 blocker 回归)

    _start_job 按住的原成员账(resume_hashes=("MEM", ), 挂到 arm 经 _resume_members 消费)
    不得被新成员挤掉 —— 覆盖会让原被按住成员在 arm 时无人恢复且无确认账(永久暂停)。
    """
    mod, store, client = _env(data_dir=str(tmp_path))
    mod._jobs["ja"] = _armed_job(phase=ru.PHASE_MOVED, resume_hashes=("MEM", ))
    store.refresh([FakeTorrent(hash="MEM", name="member", save_path=OLD, state="pausedUP"), _foreign_rec(client)])
    mod._foreign_on_scenario_a(_hit(phase=ru.PHASE_MOVED))
    job = mod.get_job("ja")
    assert job.hashes == ("MEM", "EXT")
    assert job.resume_hashes == ("MEM", "EXT")  # 并入: 原按住账保留 + 新成员追加
    mod._resume_members(job)  # arm 同位: 两者都必须被恢复
    assert ("resume", ["MEM", "EXT"]) in client.calls
    assert mod.get_job("ja").resume_pending == ("MEM", "EXT")  # 确认账覆盖两者


def test_include_armed_absence_shrinks_included_member(tmp_path):
    """R9 收缩集成(评审 minor): 纳入成员被用户删 -> 连续 N 拍权威缺席后从 job.hashes 收缩,
    不计失败(非终态), 让路面随收缩撤出 —— 纳入成员无收缩特殊化

    同步轮走真机器(store.apply_sync + FakeClient.sync_maindata 增量语义): 删除拍 =
    torrents_removed 权威证据(need_validate False), 其后零变化增量轮 rounds+1 且
    last_removed 清(确认延续靠计数>0) —— 与生产 apply_sync 轮语义一致。
    """
    mod, store, client = _env(data_dir=str(tmp_path))
    mod._jobs["ja"] = _armed_job()
    assert mod._write_arm_spec(mod.get_job("ja"))
    client.torrents["MEM"] = FakeTorrent(hash="MEM", name="member", save_path=NEW)
    client.torrents["EXT"] = _foreign_rec(client)
    store.apply_sync(QbApi(client, store))  # 首轮全量基线(真同步机器)
    mod._foreign_on_scenario_a(_hit())
    assert mod.get_job("ja").hashes == ("MEM", "EXT")
    # 用户删除纳入成员: 增量轮权威删除证据, 连续 ABSENCE_SHRINK_ROUNDS 拍确认后收缩
    del client.torrents["EXT"]
    store.apply_sync(QbApi(client, store))
    assert store.last_removed == ["EXT"] and not store.need_validate  # 增量轮形态(判定可用)
    rt = mod._rt.setdefault("ja", {})
    mod._step_absence_shrink(mod.get_job("ja"), rt, qb_up=True)
    for _ in range(ru.ABSENCE_SHRINK_ROUNDS - 1):
        store.apply_sync(QbApi(client, store))  # 零变化增量轮: rounds+1 且 last_removed 清
        mod._step_absence_shrink(mod.get_job("ja"), rt, qb_up=True)
    job = mod.get_job("ja")
    assert job.hashes == ("MEM", )  # 纳入成员已收缩
    assert not job.is_terminal and job.reason == ru.REASON_MEMBERS_GONE  # 收缩事件, 非失败终态
    assert "EXT" not in mod.relocating_hashes()  # 让路/拦截成员面随收缩撤出


def test_include_pending_tag_restart_single_full_add(tmp_path):
    """重启后镜像缓存空(评审 nit 3): _set_job 内联补写面对全成员(含新)统一 add 恰一次,
    接缝不再单发 —— 同拍零双写"""
    mod, store, client = _env(data_dir=str(tmp_path))
    mod._ctx.config.relocate = RelocateConfig(enabled=True, foreign_torrent=True, pending_tag="aqb-finalize")
    mod._jobs["ja"] = _armed_job()  # tag_on=False + 缓存空 = 重启后首次纳入形态
    store.refresh([_foreign_rec(client)])
    mod._foreign_on_scenario_a(_hit())  # was_add=False: 接缝不再单点补打
    assert client.calls == [("add_tags", "aqb-finalize")]  # 恰一次(全成员统一 add, 无第二笔单发)
    assert mod.get_job("ja").tag_on is True  # 补写面已把镜像落 add(tag_on 挂账)
