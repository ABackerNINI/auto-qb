"""外部旧路径种子侦测与处置面(ForeignMixin, 计划 26-11-20-0434; T2/S2 侦测, T3/S3 纳入, T5/S5 场景 B 通知)

侦测 = 每拍消费同步层原始 added 差集(store.pending_added_diff 经 take_added_diff 消费即排空,
T1 批地基: 未过 tracker 匹配门)
+ 四时机全量兜底(启动首轮 / job arm / foreign_torrent 翻 true / qB 重连首轮), 无周期兜底(D13)。
候选 = save_path 归一恰等活跃 job 旧根(场景 A)或终态账 done 直连边旧根(场景 B); 命中后
比对文件清单(D4, 单点复用 _file_map/_plan_files 口径), **一致才记账分类, 不一致只告警**。
场景 A 接缝(T3)= 零破坏纳入收尾: job.hashes 追加 + 收尾窗读-改-写 spec.members(journal
零写)+ pre-armed 暂停挂恢复账(D10)+ pending_tag 增量补打。
场景 B 接缝(T5)= 只通知(D8): 清单一致命中即 WARNING(D14, 文案钉 旧路径/数据现位置/种子名
/hash 短形/手动处置指引), 重复命中零重复告警(notified 账去重); R7「映射已过期」= 重解析
失败 + kind=B 条目在账 -> 降级文案 + 条目 location 置空(去重位 + 呈现层「已过期」信号面),
首次命中即解析失败按「从来不是旧根」口径静默。
已通知账记 state relocate.foreign.notified(种子消失清理; job 翻终态时该 job 的 A/mismatch
条目随终态单点清理, kind=B 保留 —— B2, 计划 26-11-21-1600), 单拍处理有界 FIFO(R4);
WebUI 呈现出口 = foreign_notified_view 只读发布视图(内容不变不换代, 变化 mark_dirty(full))。

环境口径: 裸 RelocateModule(仿 relocate_exec_support._bare_mod)+ 真 TorrentStore —— 差集
语义(基线轮不算/first-seen/零变化轮累积保留/take 消费即排空)由 test_sync.py 的 S2a+F2
十测承重, 本文件只消费。
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
- test_foreign_full_scan_accounted_skip_debug_two_reasons: F4(计划 26-11-22-1714)—— 全量兜底
  扫在账/在管跳过逐条 DEBUG, 原因二分(已入账 notified / 相位机在管 members)各恰一条,
  前缀对齐预筛 DEBUG 纪律; 计数行不做(D6 既有拍板维持)
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

场景 B 通知面(T5/S5):

- test_scenario_b_notification_warning_and_dedup: 清单一致命中即 WARNING(D14)—— 文案钉
  种子名/hash 短形/旧路径/数据现位置/手动处置指引(D8 零自动动作); 重复拍 + 全量兜底扫
  不产生第二条场景 B WARNING(notified 账去重), 账条目不重复
- test_scenario_b_expired_mapping_warning_and_dedup: R7 —— kind=B 条目在账 + 终态账滚动
  (del done job)后重加(差集重入) -> WARNING 含「映射已过期」+ 条目 location 置空;
  同 hash 再次重加不重复告警(空 location = 去重位); 结构不变(键集钉扎)
- test_scenario_b_readd_other_path_no_expired_false_alarm: 重加路径守卫(评审 major 1)——
  同 hash 落非旧根位置重加(按文案指引照现位置重加) -> 静默出队, 不误报已过期,
  location 不被置空
- test_scenario_b_expired_location_restored_on_new_edge: 空位回填(评审 minor 3)—— 置空后
  新 done job 重建同根边, 重加解析成功 -> 静默回填新现位置且零重复告警
- test_scenario_b_first_hit_resolve_fail_silent: 首次命中即解析失败(条目已随种子消失清理)
  -> 静默出队, 无告警无记账(「从来不是旧根」口径, D2 判据面不可区分)
- test_foreign_view_published_and_dirty: foreign_notified_view 发布视图 —— 条目形状/字段与
  账一致; 内容变化才 mark_dirty(full=True, reason=relocate_foreign), 无变化拍零调用;
  种子消失清理 -> 视图同步; R7 置空 -> 视图同步(location ""); 闸关时视图冻结不炸
  (foreign_torrent 翻 false 后 on_task_line 视图引用恒稳, 评审 nit 7 关断步)
- test_foreign_resolve_old_root_picks_newest_done_edge: 旧根反查单点 —— 同根多条 done 按
  updated_at 新->旧取最新; failed 不产边(失败不搬回, 旧根落种合法); 未命中返回 None
- test_foreign_resolve_closure_chain_two_done_hops: 链式闭包(T4/S4)—— A->B->C 两代 done
  边拼成传递闭包, resolve(A) 报现位置 C(job_id/phase 取末跳); 中间代旧根仍是查询起点
- test_foreign_resolve_closure_via_inherited_entry: 移交条目(plan.inherited)并入边集 ——
  最老代 done 账滚出后继承条目仍供边接链; 继承条目作末跳时 phase 随 owner 现相位
- test_foreign_resolve_closure_cycle_no_hang: 环保护 —— 脏数据 A->B->A 行走到已访根即停,
  回报已走到的最后一条真边, 双向查询都不挂死
- test_foreign_resolve_closure_depth_cap_partial: 深度上限(_FOREIGN_CLOSURE_MAX_HOPS 压到
  2)—— 超限停走回报已走到的部分位置(尽力而为 D2), 不挂死不抛
- test_foreign_resolve_same_root_rank_owner_newest_and_own_beats_inherited: 同根多条边取新
  口径 —— owner (updated_at, job_id) 最新优先; 同 owner 平手自身边压过携带的移交条目
- test_foreign_resolve_expired_mapping_is_none: R7 映射过期语义 —— 终态账滚动(载体滚出)后
  解析不出 -> None(与「非旧根」同形, 不加持久账; T5 文案按 None 降级「映射已过期」)
- test_foreign_resolve_purged_pred_falls_back_to_owner_and_matchable: 边身份回落(评审 minor
  修)—— 继承条目指向已滚出/清账的前任(_jobs 无此 id)时 edge.job_id 回落携带 owner,
  消费面 get_job 命中 + _foreign_files_match 出判定(场景 B 命中在 owner 收官前能记账)
- test_foreign_member_of_other_active_job_skipped: 命中他 job 旧根但自身是另一活跃 job 成员
  -> 幂等跳过(relocating_hashes 并集口径)
- test_foreign_diff_consumption_is_o_new: 差集消费 O(本拍新增) —— 分类调用次数 = 新到条数,
  与库内存量总数无关(结构性断言: spy 计数)
- test_foreign_fifo_bounded_split_across_ticks: 单拍有界 FIFO —— 25 条候选按预算(10/拍)
  分三拍消化, 池内余量跨拍续; 逐拍「新入账 keys == 捕获池序最前一段」断言钉死「最老先
  处理」(差集是散布序 frozenset, 池序跨拍消费才是 FIFO 承重面); 游标消费即排空(F2),
  无同差集残值重入, notified 去重兜底保留
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

覆盖率缺口清偿(26-11-21 接缝终审 + test.full 闸门收敛):

- test_foreign_scan_bad_record_skipped: 全量兜底扫逐记录护栏 —— 单记录分类炸 DEBUG 跳过,
  不炸不拖垮同扫其它候选(好候选照常入池)
- test_foreign_classify_empty_save_path_is_no_hit: 分类预门 —— save_path 为空(快照退化
  形态)不判定不炸, 按 None 出
- test_foreign_resolve_empty_query_root_is_none: 反查预门 —— 空查询根无边可走返回 None
  (不出假边)
- test_foreign_resolve_self_loop_first_hop_rejected_single_edge: 脏数据自环(done job
  src == dst)—— 首跳被拒不挂死, 单边尽力而为仍回报该边位置
- test_foreign_inherited_entries_non_matching_skipped_in_classify: 多继承条目分类 ——
  不命中条目跳过继续走, 命中条目照常产出场景 A
- test_foreign_closure_skips_inherited_entry_without_dst: 边集构建 —— dst 为空的移交
  条目不产边, 自身直连边不受影响
- test_foreign_drain_candidate_joined_active_job_pops: 排队期间成为活跃 job 成员 ——
  出队不记账(去重面在分类之后仍生效)
- test_foreign_drain_undecidable_file_table_pops_without_account: 文件表读空而账面非空
  = 不可判定 —— 出队不记账不误报, DEBUG 记「文件表不可判定」
- test_foreign_files_match_undecidable_guards: 文件表比对预门 —— qB API 缺席与账面 job
  已不在均按不可判定 None 出(事实缺失不误报成清单不一致)
- test_include_hold_member_api_missing_no_account: pre-armed 纳入按住步 —— qB API 缺席
  不暂停不挂账不炸(纳入覆盖面不依赖暂停位)
- test_include_prearm_pause_failure_still_incorporates: pre-armed 纳入暂停失败 —— 不堵
  纳入照常转正, 只少一条恢复账
- test_include_extend_spec_member_already_listed_is_noop: spec 已含该成员(job 账竞态
  落后形态)—— 幂等返回, 不产生重复 members 条目
- test_include_extend_spec_write_failure_warns_and_keeps_disk: spec 落盘失败 —— 告警不炸
  不堵纳入, 盘面 spec 保持原形
- test_include_tag_member_api_missing_skips_incremental: 增量补打预门 —— qB API 缺席不
  单发不炸, 镜像态不翻动(全量补写面接管)
- test_foreign_restore_location_only_b_entries: 空位回填只认 kind=B 条目 —— 场景 A hit
  不回填, 异物条目不炸
- test_foreign_publish_view_skips_non_dict_entries: 发布视图投影 —— notified 账异物条目
  (非 dict)跳过不炸, dict 条目照常投影
- test_state_foreign_readers_tolerate_missing_state: state 上下文缺失(data 非 dict)——
  notified 读写两 reader 都回空 dict 不炸, 零 materialize

内容根预筛(B1, 计划 26-11-21-1600 S1):

- test_foreign_gate_sibling_dir_seeds_dropped_no_mismatch: 预筛接线(场景 A, issue
  26-11-21-1500 形态)—— 同 save_path 多个子目录种子仅内容根匹配 job.scope 的进 D4 并照常
  纳入(接缝零改动); 兄弟目录种子 DEBUG 静默丢弃不入账, 零 mismatch/零 WARNING, 丢弃
  DEBUG 一条/候选(D6)
- test_foreign_gate_scenario_b_content_root_gate: 预筛接线(场景 B 直连边)—— done 边上同
  内容根种子照常进 D4 记账; 兄弟目录种子静默丢弃
- test_foreign_gate_scenario_b_entry_edge_uses_entry_scope: 预筛 scope 取数(场景 B 移交
  条目边)—— 前任已滚出、边身份回落携带 owner 时, scope 取条目自带前任内容根(entry.scope;
  缺失不可判定恒过), 原内容种子不被 owner.scope 误丢; 兄弟目录种子仍丢弃
- test_foreign_gate_helpers_undeterminable_scope_passes: 预筛不可判定面 —— scope 解析不出
  (job 账不在/命中根两面兜不上/条目 scope 缺失恒过不回落 entry.src)与 qB 缺席(api=None)
  一律恒过回落 D4, 不丢候选

终态账面清理(B2, 计划 26-11-21-1600 S2):

- test_foreign_job_terminal_cleans_a_and_mismatch_keeps_b: 终态清理单点(D4)—— armed job
  经 _set_job 翻 done 边沿, 该 job 的 kind=A 与 kind=mismatch 条目删除(1326 收口); kind=B
  一律保留(含他 job 条目, job_id 分流); 清理纯 DEBUG 零 WARNING; 非终态推进零清理动作
- test_foreign_terminal_cleanup_idempotent: 幂等守阵(黄金法则 1)—— 终态重放(_set_job 以
  终态相位再落账)不触发边沿, 清理单点直呼重复执行零副作用, 账面零变化零重复 DEBUG
- test_foreign_terminal_transition_off_config_no_materialize: 黄金法则 2 —— foreign 侦测关
  (账不在)时 job 翻终态零建键, state 不出现 relocate.foreign 空壳键(done/failed 两路同钉)
- test_foreign_superseded_direct_write_cleans_entries: superseded 直写点接线 —— 前任翻终态
  不经 _set_job(_handover_predecessors 直写), A/mismatch 随收官清理 kind=B 保留, 重复执行
  (前任已终态跳过)零副作用
- test_foreign_terminal_cleanup_then_rescan_rejudges_scenario_b: 端到面(收尾后正确语义)——
  收尾窗纳入(kind=A) -> 翻 done(A 条目随终态清理) -> 同根种子重现重扫命中 done 终态账边
  自然重判场景 B
- test_foreign_terminal_cleanup_mismatch_rescan_rerecords_and_rewarns: B2 第三形态钉档
  (接缝终审 minor, 用户拍板 a = 接受现状不抑制重发)—— mismatch 条目随终态清理后种子仍在
  旧根: 重连时机扫重判穿过 S1 内容根预筛进 D4 判异, 重落 mismatch 条目(同 job_id,
  phase/first_seen 按命中现值刷新)并恰重发一次 WARNING(总两条: 收官前 + 重判);
  notified 去重位仍在 —— 条目重入池的重复拍零再发
- test_foreign_terminal_cleanup_failed_no_edge_silent_dismissal: B2 钉档补面(failed/
  cancelled 无边形态, 与重落形态对照)—— mismatch 落账 -> _fail 翻 failed(条目随终态
  清理)-> 种子仍挂旧根: 时机扫 classify 无边可走, 「从来不是旧根」静默口径(零账零告警
  零重落, 候选出队不重试)
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


def _hold_phase_machine(mod):
    """裸环境相位机让位桩(B2 起): 分类/记账面用例只测 foreign 面 —— 裸环境同拍推进
    (moving 停滞判失败 / moved 核验不符判失败)会把 job 翻终态, 而终态边沿现在会清该 job
    的 kind=A/mismatch 条目(B2, 计划 26-11-21-1600), 本测主体的记账形状断言需要相位机
    让位(B2 端到面另有 test_foreign_terminal_cleanup_then_rescan_rejudges_scenario_b)"""
    mod._advance = lambda job: None


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


def test_foreign_full_scan_accounted_skip_debug_two_reasons(tmp_path):
    """F4(计划 26-11-22-1714): 全量兜底扫对在账/在管 hash 的静默 continue 补逐条 DEBUG,
    原因二分(已入账 notified / 相位机在管 members)且各恰一条; 前缀对齐预筛 DEBUG 纪律,
    计数行不做(D6 既有拍板维持)"""
    mod, store, client = _env(data_dir=str(tmp_path))
    _hold_phase_machine(mod)  # 裸环境同拍推进判失败会清 A 条目(B2), 本测只钉跳过留痕面
    mod._jobs["ja"] = _job(
        "ja", phase=ru.PHASE_MOVING, src=OLD, dst=NEW, hashes=("MEM", ), plan={"files": list(PLAN_FILES)}
    )
    client.files_map["MEM"] = _seed()
    client.files_map["EXT"] = _seed()
    store.refresh(
        [
            FakeTorrent(hash="MEM", name="member", save_path=OLD),  # 相位机在管(pre-arm 成员)
            FakeTorrent(hash="EXT", name="foreign", save_path=OLD),
        ]
    )
    mod.on_task_line()  # activation 全量扫: EXT 命中入账(notified), MEM 相位机在管跳过
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:  # logger 名单点在 relocate_common(沿用原模块名)
        mod._foreign_full_scan("test")
    dbg = [r.getMessage() for r in cap.records if r.levelno == logging.DEBUG]
    notified_skips = [m for m in dbg if "已入账(notified)" in m]
    member_skips = [m for m in dbg if "相位机在管(members)" in m]
    assert len(notified_skips) == 1 and "EXT" in notified_skips[0], dbg
    assert len(member_skips) == 1 and "MEM" in member_skips[0], dbg
    assert all(m.startswith("relocate | foreign |") for m in notified_skips + member_skips), dbg


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
    added, _removed = store.refresh([t])  # 重连式全量: 游标累积 = {NT}
    assert added == ["NT"] and store.pending_added_diff == frozenset({"NT"})
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
    """清单一致才记账; 不一致只告警(D4)恰一次 + mismatch 账; 重复拍不重告; 消失清理; 重现重处理
    (T5: 一致命中自带通知 WARNING, 与 D4 判定面告警分面计数)"""
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

        def _mismatch_n():
            # D4 判定面文案单点(_foreign_record_mismatch): 只数不一致告警(B2 新口径字面)
            return len([m for m in cap.records if m.levelno == logging.WARNING and "同内容根目录下内容不一致" in m.getMessage()])

        def _notice_n():
            # T5 场景 B 通知文案单点(_foreign_on_scenario_b): 只数通知告警
            return len([m for m in cap.records if m.levelno == logging.WARNING and "旧路径外部种子" in m.getMessage()])

        mod.on_task_line()  # 命中: OK 一致记账 + 通知一次(T5); MX 不一致只告警一次
        notified = mod._state_foreign_notified()
        assert notified["OK"]["kind"] == "B"
        assert notified["MX"]["kind"] == "mismatch"
        assert _mismatch_n() == 1 and _notice_n() == 1
        # B2 新口径钉扎(计划 26-11-21-1600 D3): 文案 = 同内容根异内容准确语义
        mx_msg = next(
            m.getMessage() for m in cap.records if m.levelno == logging.WARNING and "同内容根目录下内容不一致" in m.getMessage()
        )
        assert "同内容根目录下内容不一致, 疑似外部工具重加了不同版本" in mx_msg
        assert "同目录异内容" not in mx_msg  # 旧口径字面退役
        mod.on_task_line()  # 游标已排空(F2 消费即排空): 无重入, notified 去重兜底保留, 不重告
        assert _mismatch_n() == 1 and _notice_n() == 1
        old_first_seen = notified["OK"]["first_seen"]
        store.refresh([])  # 种子全部消失
        mod.on_task_line()
        assert "OK" not in notified
        assert "MX" not in notified
        # 重现 = 重新 first-seen 重处理重告警: 原种子带回 -> 条目重现(新 first_seen),
        # mismatch 再告一次(WARNING +1), 一致种子重记账 + 重通知(重现 = 重新 first-seen)
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
        assert _mismatch_n() == 2  # 恰再告一次(仅 mismatch)
        assert _notice_n() == 2  # 通知随重现重新首发(消失清理 -> 重新 first-seen 重处理)


# ---------- 分类(A/B/继承/成员幂等/反查单点) ----------


def test_foreign_scenario_a_with_phase_and_member_skip(tmp_path):
    """场景 A 分类正确且相位随 job 现值; 活跃 job 成员 hash 幂等跳过"""
    mod, store, client = _env(data_dir=str(tmp_path))
    _hold_phase_machine(mod)  # 裸环境同拍推进判失败会清 A 条目(B2), 本测只钉记账面
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
    _hold_phase_machine(mod)  # 裸环境同拍推进判失败会清 A 条目(B2), 本测只钉记账面
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


# ---------- 内容根预筛(B1, 计划 26-11-21-1600 S1) ----------


def test_foreign_gate_sibling_dir_seeds_dropped_no_mismatch():
    """B1 预筛(issue 26-11-21-1500 形态, 场景 A): 同 save_path 多个子目录种子, 仅内容根匹配
    job.scope 的进后续面; 兄弟目录种子 DEBUG 静默丢弃 —— 不产生 mismatch 记录/告警不入账;
    纳入接缝零改动(匹配种子照常转正)"""
    mod, store, client = _env()
    _hold_phase_machine(mod)  # 裸环境同拍推进判失败会清 A 条目(B2), 本测只钉记账/预筛面
    plan = {"files": [["Show/f.bin", 10]]}
    mod._jobs["ja"] = _job("ja", phase=ru.PHASE_MOVING, src=OLD, dst=NEW, scope=OLD + "/Show", plan=plan)
    client.files_map["HIT"] = [_fake_file("Show/f.bin", 10)]  # 内容根 = OLD/Show == scope
    client.files_map["SIB1"] = [_fake_file("Other1/x.bin", 7)]  # 兄弟目录: 内容根 = OLD/Other1
    client.files_map["SIB2"] = [_fake_file("Other2/y.bin", 9)]  # 兄弟目录: 内容根 = OLD/Other2
    store.refresh(
        [
            FakeTorrent(hash="HIT", name="same-root", save_path=OLD),
            FakeTorrent(hash="SIB1", name="sib1", save_path=OLD),
            FakeTorrent(hash="SIB2", name="sib2", save_path=OLD),
        ]
    )
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod.on_task_line()
    notified = mod._state_foreign_notified()
    assert notified["HIT"]["kind"] == "A"  # 内容根匹配: 进 D4 并纳入(接缝零改动)
    assert "HIT" in mod._jobs["ja"].hashes
    assert "SIB1" not in notified and "SIB2" not in notified  # 静默丢弃: 不入账不呈现
    assert not [m for m in cap.records if m.levelno == logging.WARNING]  # 零 mismatch/零告警
    drops = [m for m in cap.records if m.levelno == logging.DEBUG and "预筛丢弃" in m.getMessage()]
    assert len(drops) == 2  # D6: 丢弃纯 DEBUG, 一条/候选


def test_foreign_gate_scenario_b_content_root_gate():
    """B1 预筛(场景 B 直连边): done 边上同内容根种子照常进 D4 记账; 兄弟目录种子静默丢弃"""
    mod, store, client = _env()
    mod._jobs["jd"] = _job(
        "jd", phase=ru.PHASE_DONE, src=OLD, dst=NEW, scope=OLD + "/Show", plan={"files": [["Show/f.bin", 10]]}
    )
    client.files_map["HIT"] = [_fake_file("Show/f.bin", 10)]  # 内容根 = OLD/Show == scope
    client.files_map["SIB"] = [_fake_file("Other/x.bin", 7)]  # 兄弟目录: 内容根 = OLD/Other
    store.refresh(
        [
            FakeTorrent(hash="HIT", name="same-root", save_path=OLD),
            FakeTorrent(hash="SIB", name="sib", save_path=OLD),
        ]
    )
    mod.on_task_line()
    notified = mod._state_foreign_notified()
    assert notified["HIT"]["kind"] == "B"
    assert "SIB" not in notified


def test_foreign_gate_scenario_b_entry_edge_uses_entry_scope():
    """B1 预筛(场景 B 移交条目边): scope 取条目自带前任内容根(entry.scope; 缺失不可判定恒过)
    —— 链式迁移最老代旧根上的原内容种子照常进 D4, 不被携带 owner 的 scope 误丢; 兄弟目录
    种子仍丢弃"""
    mod, store, client = _env()
    plan = {
        "files": [["Show/f.bin", 10]],
        "inherited":
            [
                {
                    "job_id": "jp",  # 前任已滚出终态账(不在 _jobs): 边身份回落携带 owner(既有口径)
                    "src": OLD,
                    "dst": "R:/mid",
                    "scope": OLD + "/Show",
                    "alias_kind": "dir",
                    "alias_paths": [OLD + "/Show"],
                    "link_kind": "junction",
                }
            ],
    }
    # owner 终态(done): 场景 A 继承面只扫活跃 job, 该形态必落 B 路(条目边供 B 解析)
    mod._jobs["j2"] = _job("j2", phase=ru.PHASE_DONE, src="R:/z", dst="R:/w", plan=plan)
    client.files_map["HIT"] = [_fake_file("Show/f.bin", 10)]  # 前任内容结构: 内容根 = OLD/Show == entry.scope
    client.files_map["SIB"] = [_fake_file("Other/x.bin", 7)]  # 兄弟目录: 内容根 = OLD/Other
    store.refresh(
        [
            FakeTorrent(hash="HIT", name="old-root", save_path=OLD),
            FakeTorrent(hash="SIB", name="sib", save_path=OLD),
        ]
    )
    mod.on_task_line()
    notified = mod._state_foreign_notified()
    assert notified["HIT"]["kind"] == "B"  # entry.scope 解析: 原内容种子不被 owner.scope(R:/z)误丢
    assert "SIB" not in notified


def test_foreign_gate_helpers_undeterminable_scope_passes():
    """B1 预筛不可判定面: scope 解析不出(job 账不在/命中根两面兜不上/条目 scope 缺失恒过
    不回落 entry.src)与 qB 缺席(api=None)一律恒过回落 D4, 不丢候选"""
    mod, _store, _client = _env()
    hit = rf.ForeignHit(
        hash="HX", save_path=OLD, scenario="A", job_id="gone", phase="moving", old_root=OLD, location=NEW
    )
    assert mod._foreign_hit_scope(hit) is None  # job 账已不在 -> None
    assert mod._foreign_gate_pass(object(), hit) is True  # 不可判定保守放行(回落 D4)
    mod._jobs["jx"] = _job("jx", src="R:/elsewhere", plan={"files": list(PLAN_FILES)})
    hit2 = rf.ForeignHit(
        hash="HX", save_path=OLD, scenario="B", job_id="jx", phase="moving", old_root=OLD, location=NEW
    )
    assert mod._foreign_hit_scope(hit2) is None  # 命中根既非 job.src 也非任何继承条目 -> None
    assert mod._foreign_gate_pass(object(), hit2) is True
    # 评审 minor: 条目 scope 缺失(空串/缺键, 反序列化同形 "")= 不可靠 -> None 恒过 —— 恰等门
    # 不回落 entry.src(回落先例服务 _within 包含门放宽向; 恰等判定下回落会把目录形态前任
    # (真实内容根 = src/<段>)的真命中误丢)
    plan = {
        "files":
            list(PLAN_FILES),
        "inherited":
            [
                {
                    "job_id": "jp",
                    "src": OLD,
                    "dst": "R:/mid",
                    "scope": "",
                    "alias_kind": "dir"
                },
                {
                    "job_id": "jp2",
                    "src": OLD + "2",
                    "dst": "R:/mid2",
                    "alias_kind": "dir"
                },  # 无 scope 键
            ],
    }
    mod._jobs["jy"] = _job("jy", phase=ru.PHASE_DONE, src="R:/z", dst="R:/w", plan=plan)
    for old_root in (OLD, OLD + "2"):
        hit_n = rf.ForeignHit(
            hash="HX",
            save_path=old_root,
            scenario="B",
            job_id="jy",
            phase="done",
            old_root=old_root,
            location="R:/mid"
        )
        assert mod._foreign_hit_scope(hit_n) is None  # 条目 scope 缺失 -> None(不回落 entry.src)
        assert mod._foreign_gate_pass(object(), hit_n) is True
    # 评审 nit: qB 缺席守卫(api/client 缺失)恒过 —— 与 D4 同款不可判定口径
    mod._ctx.api = None
    assert mod._foreign_gate_pass(object(), hit_n) is True


# ---------- 终态账面清理(B2, 计划 26-11-21-1600 S2) ----------


def _plant_entry(notified, h, kind, job_id, phase="armed"):
    """通知账条目植入(形状与 _foreign_record_hit 同构; 测试钉清理分流用)"""
    notified[h] = {
        "root": ru._norm(OLD),
        "kind": kind,
        "job_id": job_id,
        "phase": phase,
        "location": NEW,
        "first_seen": 1.0
    }


def test_foreign_job_terminal_cleans_a_and_mismatch_keeps_b():
    """B2 终态清理单点(D4): armed job 经 _set_job 翻 done 的边沿上, 该 job 的 kind=A 与
    kind=mismatch 条目删除; kind=B 一律保留(含他 job 的 B 条目, job_id 分流); 清理纯
    DEBUG(零 WARNING, 不入告警门槛面); 非 B2 涉面的非终态推进零清理动作"""
    mod, store, _client = _env()
    mod._jobs["ja"] = _job("ja", phase=ru.PHASE_ARMED, src=OLD, dst=NEW)
    mod._jobs["jd"] = _job("jd", phase=ru.PHASE_DONE, src="R:/o2", dst="R:/n2", updated_at=100.0)
    notified = mod._state_foreign_notified()
    _plant_entry(notified, "EA", "A", "ja")
    _plant_entry(notified, "EM", "mismatch", "ja")
    _plant_entry(notified, "EB", "B", "ja", phase="done")  # 合成形态: 钉 kind 分流(D4: B 一律保留)
    _plant_entry(notified, "EB2", "B", "jd", phase="done")
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod._set_job(replace(mod._jobs["ja"], phase=ru.PHASE_DONE))
    notified = mod._state_foreign_notified()
    assert "EA" not in notified and "EM" not in notified  # A/mismatch 随终态清理(1326 收口)
    assert notified["EB"]["kind"] == "B" and notified["EB"]["job_id"] == "ja"  # kind=B 保留
    assert notified["EB2"]["kind"] == "B" and notified["EB2"]["job_id"] == "jd"  # 他 job 条目不动
    assert not [m for m in cap.records if m.levelno >= logging.WARNING]  # 清理纯 DEBUG
    assert any("翻终态" in m.getMessage() for m in cap.records if m.levelno == logging.DEBUG)
    # 非终态推进零清理动作(真钉): 另植 armed job 走 armed->armed 的 _set_job(armed 内账面
    # 更新, 相位不动), 边沿判据只认 非终态->终态 —— 零「翻终态」DEBUG 且条目原样
    mod._jobs["jw"] = _job("jw", phase=ru.PHASE_ARMED, src="R:/o4", dst="R:/n4")
    _plant_entry(notified, "EW", "A", "jw")
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap2:
        mod._set_job(replace(mod._jobs["jw"], reason="touch"))
    assert not [m for m in cap2.records if m.levelno == logging.DEBUG and "翻终态" in m.getMessage()]
    assert notified["EW"]["kind"] == "A"  # 非终态推进不清理: 条目原样


def test_foreign_terminal_cleanup_idempotent():
    """B2 幂等守阵(黄金法则 1): 终态重放(_set_job 以终态相位再落账)不触发边沿、清理单点
    直呼重复执行零副作用 —— 账面零变化, 无重复 DEBUG"""
    mod, _store, _client = _env()
    mod._jobs["ja"] = _job("ja", phase=ru.PHASE_ARMED, src=OLD, dst=NEW)
    notified = mod._state_foreign_notified()
    _plant_entry(notified, "EA", "A", "ja")
    _plant_entry(notified, "EB", "B", "ja", phase="done")
    mod._set_job(replace(mod._jobs["ja"], phase=ru.PHASE_DONE))  # 边沿: A 清, B 留
    assert "EA" not in notified and notified["EB"]["kind"] == "B"
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod._set_job(replace(mod._jobs["ja"], phase=ru.PHASE_DONE))  # 终态重放: 非边沿, 不触发
        mod._foreign_cleanup_job_terminal("ja")  # 清理单点直呼(重复执行)
        mod._foreign_cleanup_job_terminal("ja")
    assert "EA" not in notified and notified["EB"]["kind"] == "B"  # 账面零变化
    assert not [m for m in cap.records if "翻终态" in m.getMessage()]  # 重放零动作零日志


def test_foreign_terminal_transition_off_config_no_materialize():
    """B2 黄金法则 2: foreign 侦测关(foreign_torrent=False, 账不在)时 job 翻终态零建键
    —— state 里不出现 relocate.foreign 空壳键(done/failed 两路终态同钉)"""
    mod, _store, _client = _env(foreign=False)
    mod._jobs["ja"] = _job("ja", phase=ru.PHASE_ARMED, src=OLD, dst=NEW)
    mod._jobs["jb"] = _job("jb", phase=ru.PHASE_ARMED, src="R:/o3", dst="R:/n3")
    mod._set_job(replace(mod._jobs["ja"], phase=ru.PHASE_DONE))
    mod._set_job(replace(mod._jobs["jb"], phase=ru.PHASE_FAILED, reason="x"))
    relocate_box = mod._ctx.state.data.get("relocate")
    assert isinstance(relocate_box, dict) and "jobs" in relocate_box  # job 账照常落(既有机制)
    assert "foreign" not in relocate_box  # 零 materialize(清理面只读视图判存在)


def test_foreign_superseded_direct_write_cleans_entries():
    """B2 superseded 直写点接线: 前任翻终态不经 _set_job(_handover_predecessors 直写
    _jobs), 清理在翻相位处同判据触发 —— A/mismatch 条目随收官清理, kind=B 保留; 已终态
    前任(重复执行)跳过不重复进账"""
    mod, _store, _client = _env()
    mod._jobs["jp"] = _job("jp", phase=ru.PHASE_ARMED, src=OLD, dst=NEW)
    mod._jobs["j2"] = _job("j2", phase=ru.PHASE_MOVED, src=NEW, dst="R:/c")
    notified = mod._state_foreign_notified()
    _plant_entry(notified, "EA", "A", "jp")
    _plant_entry(notified, "EM", "mismatch", "jp")
    _plant_entry(notified, "EB", "B", "jp", phase="done")
    mod._handover_predecessors([mod._jobs["jp"]], mod._jobs["j2"])
    assert mod._jobs["jp"].phase == ru.PHASE_SUPERSEDED
    notified = mod._state_foreign_notified()
    assert "EA" not in notified and "EM" not in notified
    assert notified["EB"]["kind"] == "B"  # kind=B 一律保留(D4)
    # 重复执行(前任已终态, 循环顶守卫跳过): 幂等零副作用
    mod._handover_predecessors([mod._jobs["jp"]], mod._jobs["j2"])
    assert set(notified) == {"EB"}


def test_foreign_terminal_cleanup_then_rescan_rejudges_scenario_b():
    """B2 端到面(收尾后正确语义): 收尾窗纳入(kind=A) -> job 翻 done(A 条目随终态清理)
    -> 同根种子重现重扫, 命中 done 终态账边自然重判场景 B(job_id 指向产出 job)"""
    mod, store, client = _env()
    mod._jobs["ja"] = _job("ja", phase=ru.PHASE_ARMED, src=OLD, dst=NEW, hashes=(), plan={"files": list(PLAN_FILES)})
    client.files_map["EX"] = _seed()
    store.refresh([FakeTorrent(hash="EX", name="ext", save_path=OLD)])
    mod.on_task_line()  # 场景 A: 记账 + 纳入(收尾窗 spec 双写)
    notified = mod._state_foreign_notified()
    assert notified["EX"]["kind"] == "A" and "EX" in mod._jobs["ja"].hashes
    mod._set_job(replace(mod._jobs["ja"], phase=ru.PHASE_DONE))  # 收官: A 条目随终态清理
    assert "EX" not in mod._state_foreign_notified_view()
    store.refresh([])  # 种子消失一拍(重现 = 重新 first-seen 重处理的既有机制)
    client.files_map["EX"] = _seed()
    store.refresh([FakeTorrent(hash="EX", name="ext", save_path=OLD)])
    mod.on_task_line()  # 重现: 差集重入 -> done 终态账边命中 -> 场景 B
    notified = mod._state_foreign_notified()
    assert notified["EX"]["kind"] == "B" and notified["EX"]["job_id"] == "ja"
    assert notified["EX"]["location"] == NEW


def test_foreign_terminal_cleanup_mismatch_rescan_rerecords_and_rewarns():
    """B2 第三形态钉档(接缝终审 minor, 用户拍板 a = 接受现状不抑制重发): mismatch 条目随
    终态清理后种子仍在旧根 -> 下个时机扫重判穿过 S1 内容根预筛(同内容根恒放行)进 D4 判异,
    重新落 mismatch 条目(同 job_id, phase/first_seen 按命中现值刷新)并恰重发一次 WARNING
    (总两条同内容告警: 收官前一次 + 重判一次); 去重位仍在 notified 账 —— 条目重入池的
    重复拍零再发, 条目随后滞留到种子消失"""
    mod, store, client = _env()
    _hold_phase_machine(mod)  # 裸环境同拍推进会把 armed job 快路径收官(边沿即清), 本测显式翻终态
    mod._jobs["ja"] = _job("ja", phase=ru.PHASE_ARMED, src=OLD, dst=NEW, hashes=(), plan={"files": list(PLAN_FILES)})
    client.files_map["MX"] = _seed(match=False)
    store.refresh([FakeTorrent(hash="MX", name="diff", save_path=OLD)])
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap1:
        mod.on_task_line()  # 收官前: D4 判异 -> mismatch 条目 + WARNING 恰一次
    notified = mod._state_foreign_notified()
    assert notified["MX"]["kind"] == "mismatch" and notified["MX"]["job_id"] == "ja"
    assert notified["MX"]["phase"] == "armed"  # 命中现值(armed 活跃 job)
    old_first_seen = notified["MX"]["first_seen"]
    assert len([m for m in cap1.records if m.levelno == logging.WARNING and "同内容根目录下内容不一致" in m.getMessage()]) == 1
    mod._set_job(replace(mod._jobs["ja"], phase=ru.PHASE_DONE))  # 收官: mismatch 条目随终态清理
    assert "MX" not in mod._state_foreign_notified_view()
    mod._clock.advance(30.0)
    # 种子仍在旧根: 重连时机扫重判(同内容根恒过预筛) -> D4 判异 -> 重落 mismatch + 重发一次
    store.reset_sync()
    mod.on_task_line()  # 观测 epoch 变化, 记重连锚(尚无应用轮不扫)
    store.refresh([FakeTorrent(hash="MX", name="diff", save_path=OLD)])  # 重连后首轮(全量)
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap2:
        mod.on_task_line()  # rounds 越锚: reconnect 时机扫 -> 重判
    notified = mod._state_foreign_notified()
    assert notified["MX"]["kind"] == "mismatch" and notified["MX"]["job_id"] == "ja"
    assert notified["MX"]["phase"] == "done"  # 字段按命中现值刷新(收官后 B 命中相位)
    assert notified["MX"]["first_seen"] > old_first_seen  # first_seen 刷新(假钟推进过)
    assert len([m for m in cap2.records if m.levelno == logging.WARNING and "同内容根目录下内容不一致" in m.getMessage()]) == 1, \
        "恰重发一次(拍板 a: 不抑制重发)"
    # 去重位仍在 notified 账: 条目重入池(消失重现形态)的重复拍零再发
    store.refresh([])  # 移除 + 重加不打 tick: 差集 = {MX}(重现 = 重入池, 既有机制)
    client.files_map["MX"] = _seed(match=False)
    store.refresh([FakeTorrent(hash="MX", name="diff", save_path=OLD)])
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap3:
        mod.on_task_line()
    assert notified["MX"]["kind"] == "mismatch"  # 在账去重: 条目不被重判覆盖(零新告警零新首见)
    assert len([m for m in cap3.records if m.levelno == logging.WARNING and "同内容根目录下内容不一致" in m.getMessage()]) == 0


def test_foreign_terminal_cleanup_failed_no_edge_silent_dismissal():
    """B2 钉档补面(failed/cancelled 无边形态, 与 mismatch 重落形态对照): mismatch 落账 ->
    _fail 翻 failed(条目随终态清理)-> 种子仍挂旧根 -> 时机扫 classify 无边可走(failed/
    cancelled 不产自身边, 旧根也不在任何条目边源)-> 「从来不是旧根」静默口径(D2):
    零账零告警零重落, 候选出队不重试 —— 呈现静默消失"""
    mod, store, client = _env()
    _hold_phase_machine(mod)  # 相位机让位: 终态翻转走显式 _fail(本测主体), 收官前条目不被同拍清掉
    mod._jobs["ja"] = _job("ja", phase=ru.PHASE_ARMED, src=OLD, dst=NEW, hashes=(), plan={"files": list(PLAN_FILES)})
    client.files_map["MX"] = _seed(match=False)
    store.refresh([FakeTorrent(hash="MX", name="diff", save_path=OLD)])
    mod.on_task_line()  # D4 判异 -> mismatch 条目(armed 活跃 job 命中)
    notified = mod._state_foreign_notified()
    assert notified["MX"]["kind"] == "mismatch" and notified["MX"]["job_id"] == "ja"
    mod._fail(mod._jobs["ja"], "verify_mismatch", "目标侧文件数/大小不符")  # 翻 failed: 条目随终态清理
    assert mod.get_job("ja").phase == ru.PHASE_FAILED
    assert "MX" not in mod._state_foreign_notified_view()
    # 种子仍挂旧根: 重连时机扫 classify 无边可走 -> 连池不入, 出队静默(零账零告警零重落)
    store.reset_sync()
    mod.on_task_line()  # 观测 epoch 变化, 记重连锚(尚无应用轮不扫)
    store.refresh([FakeTorrent(hash="MX", name="diff", save_path=OLD)])  # 重连后首轮(全量)
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap_scan:
        mod.on_task_line()  # rounds 越锚: reconnect 时机扫 -> classify None -> 静默出队
    assert "MX" not in mod._state_foreign_notified_view(), "failed 无自身边: 不重落不误报"
    assert not mod._foreign_pending, "classify None 候选出队不重试(不占池位不空转)"
    assert not [m for m in cap_scan.records if m.levelno >= logging.WARNING], "静默口径: 零告警"


# ---------- 场景 B 通知面(T5/S5: 只通知 D8, R7 映射已过期, 发布视图) ----------


def _warn_texts(cap):
    return [m.getMessage() for m in cap.records if m.levelno == logging.WARNING]


def test_scenario_b_notification_warning_and_dedup():
    """场景 B 命中即 WARNING(D14); 重复拍 + 全量兜底扫不重复告警(notified 账去重)"""
    mod, store, client = _env()
    _done_job(mod)
    client.files_map["BX"] = _seed()
    t = FakeTorrent(hash="BX", name="IYUU-辅种", save_path=OLD)
    store.refresh([t])
    with capture_logs() as cap:
        mod.on_task_line()
    warns = _warn_texts(cap)
    # 文案钉扎(D14 面向用户): 种子名 + hash 短形 + 旧路径 + 数据现位置 + 手动处置(D8)
    assert any("旧路径外部种子" in w and "IYUU-辅种" in w for w in warns), warns
    assert any("BX" in w and OLD in w and NEW in w for w in warns), warns
    assert any("手动处置" in w for w in warns), warns
    n_first = len([w for w in warns if "旧路径外部种子" in w])
    assert n_first == 1
    assert mod._state_foreign_notified()["BX"]["kind"] == "B"
    # 重复拍(种子仍在库, 差集清空): 零新告警零重复记账
    with capture_logs() as cap2:
        mod.on_task_line()
    assert not [w for w in _warn_texts(cap2) if "旧路径外部种子" in w]
    assert len(mod._state_foreign_notified()) == 1
    # 全量兜底扫(时机拍同款路径): 在账 hash 幂等跳过, 零新告警
    with capture_logs() as cap3:
        mod._foreign_full_scan("test")
    assert not [w for w in _warn_texts(cap3) if "旧路径外部种子" in w]
    assert len(mod._state_foreign_notified()) == 1


def test_scenario_b_expired_mapping_warning_and_dedup():
    """R7: kind=B 条目在账 + 映射滚出终态账后重加 -> 「映射已过期」+ location 置空; 去重"""
    mod, store, client = _env()
    _done_job(mod)
    client.files_map["BX"] = _seed()
    t = FakeTorrent(hash="BX", name="IYUU-辅种", save_path=OLD)
    store.refresh([t])
    mod.on_task_line()  # 首次命中: 记账 + WARNING(数据现位置 NEW)
    assert mod._state_foreign_notified()["BX"]["location"] == NEW
    del mod._jobs["jd"]  # 终态账滚动(R7): 旧根映射移出
    # 同拍窗内重加(外部工具删后重加; 不给 cleanup 机会删条目): 差集重入
    store.refresh([])
    store.refresh([t])
    with capture_logs() as cap:
        mod.on_task_line()
    warns = _warn_texts(cap)
    expired = [w for w in warns if "映射已过期" in w]
    assert len(expired) == 1, warns
    # root 记的是账面条目值(归一形): 与判定口径一致(通知首告的 hit.old_root 才是原形)
    assert ru._norm(OLD) in expired[0] and "IYUU-辅种" in expired[0], expired
    entry = mod._state_foreign_notified()["BX"]
    assert entry["location"] == ""  # 已过期信号面(呈现层) + 告警去重位
    assert set(entry) == {"root", "kind", "job_id", "phase", "location", "first_seen"}  # 结构不变
    assert entry["kind"] == "B" and entry["root"] == ru._norm(OLD)
    # 再次重加(映射仍不在): 空 location = 去重位, 零重复告警
    store.refresh([])
    store.refresh([t])
    with capture_logs() as cap2:
        mod.on_task_line()
    assert not [w for w in _warn_texts(cap2) if "映射已过期" in w]


def test_scenario_b_readd_other_path_no_expired_false_alarm():
    """重加路径守卫(评审 major 1): 同 hash 落非旧根位置重加 -> 静默, 不误报不置空

    用户照首告文案指引「按现位置重新添加」(同 hash 落新位置): 重解析对新路径必然失败
    (新位置不是任何旧根), 守卫按 save_path 归一 != 账面 root 判定非「映射过期」语义,
    静默出队 —— 误报会把 location 永久锁空, 面板永远显示已过期。
    """
    mod, store, client = _env()
    _done_job(mod)
    client.files_map["BX"] = _seed()
    store.refresh([FakeTorrent(hash="BX", name="IYUU-辅种", save_path=OLD)])
    mod.on_task_line()  # 首告(location=NEW)
    entry = mod._state_foreign_notified()["BX"]
    assert entry["location"] == NEW
    del mod._jobs["jd"]  # 映射滚出(对旧根已解析不出)
    t2 = FakeTorrent(hash="BX", name="IYUU-辅种", save_path="R:/elsewhere")  # 照新位置重加
    client.files_map["BX"] = _seed()
    store.refresh([])
    store.refresh([t2])
    with capture_logs() as cap:
        mod.on_task_line()
    assert not [w for w in _warn_texts(cap) if "映射已过期" in w or "旧路径外部种子" in w]
    assert mod._state_foreign_notified()["BX"]["location"] == NEW  # 不被置空


def test_scenario_b_expired_location_restored_on_new_edge():
    """空位回填(评审 minor 3): 置空后新 done job 重建同根边 -> 静默回填不重告警"""
    mod, store, client = _env()
    _done_job(mod)
    client.files_map["BX"] = _seed()
    t = FakeTorrent(hash="BX", name="IYUU-辅种", save_path=OLD)
    store.refresh([t])
    mod.on_task_line()  # 首告(location=NEW)
    del mod._jobs["jd"]
    store.refresh([])
    store.refresh([t])
    mod.on_task_line()  # 过期告警 + 置空
    assert mod._state_foreign_notified()["BX"]["location"] == ""
    # 新 done job 重建同根边(终态账重新收录映射): 重加解析成功
    mod._jobs["jd2"] = _job(
        "jd2", phase=ru.PHASE_DONE, src=OLD, dst="R:/new2", plan={"files": list(PLAN_FILES)}, updated_at=200.0
    )
    store.refresh([])
    store.refresh([t])
    with capture_logs() as cap:
        mod.on_task_line()
    assert not [w for w in _warn_texts(cap) if "映射已过期" in w or "旧路径外部种子" in w], \
        "回填是数据恢复不是重新告警(同一 hash 不重复告警纪律不变)"
    assert mod._state_foreign_notified()["BX"]["location"] == "R:/new2"  # 按当前 hit 回填


def test_scenario_b_first_hit_resolve_fail_silent():
    """首次命中即解析失败(条目已随消失清理) -> 静默: 无告警无记账(「从来不是旧根」口径)"""
    mod, store, client = _env()
    _done_job(mod)
    client.files_map["BX"] = _seed()
    t = FakeTorrent(hash="BX", name="IYUU-辅种", save_path=OLD)
    store.refresh([t])
    mod.on_task_line()
    assert "BX" in mod._state_foreign_notified()
    del mod._jobs["jd"]  # 映射滚出
    store.refresh([])  # 种子先消失: cleanup 删条目(重现后无「此前已通知过」信号面)
    mod.on_task_line()
    assert "BX" not in mod._state_foreign_notified()
    store.refresh([t])  # 重加: 差集重入, 解析失败且无条目
    with capture_logs() as cap:
        mod.on_task_line()
    assert not [w for w in _warn_texts(cap) if "映射已过期" in w or "旧路径外部种子" in w]
    assert "BX" not in mod._state_foreign_notified()  # 不记账(非旧根口径)


def test_foreign_view_published_and_dirty():
    """foreign_notified_view 发布视图: 形状/换代/mark_dirty 单点; 清理与 R7 置空同步"""
    mod, store, client = _env()
    dirty = []
    mod._ctx.web = SimpleNamespace(mark_dirty=lambda full=False, reason="": dirty.append((full, reason)))
    _done_job(mod)
    client.files_map["BX"] = _seed()
    t = FakeTorrent(hash="BX", name="IYUU-辅种", save_path=OLD)
    store.refresh([t])
    mod.on_task_line()
    view = mod.foreign_notified_view()
    assert set(view) == {"BX"}
    entry = view["BX"]
    assert entry["kind"] == "B" and entry["root"] == ru._norm(OLD) and entry["location"] == NEW
    assert entry["job_id"] == "jd" and entry["phase"] == "done"
    assert entry["first_seen"] == mod._state_foreign_notified()["BX"]["first_seen"]
    assert dirty == [(True, "relocate_foreign")]  # 首次发布: 换代 + 通知 Web 刷视图
    # 无变化拍: 引用恒稳(不换代), 零 mark_dirty
    mod.on_task_line()
    assert mod.foreign_notified_view() is view
    assert dirty == [(True, "relocate_foreign")]
    # 种子消失清理 -> 视图同步换代
    store.refresh([])
    mod.on_task_line()
    assert set(mod.foreign_notified_view()) == set()
    assert dirty == [(True, "relocate_foreign"), (True, "relocate_foreign")]
    # R7 置空 -> 视图同步(呈现层按空 location 显示已过期)
    mod._jobs["jd"] = _job(
        "jd", phase=ru.PHASE_DONE, src=OLD, dst=NEW, plan={"files": list(PLAN_FILES)}, updated_at=100.0
    )
    client.files_map["BX"] = _seed()
    store.refresh([t])
    mod.on_task_line()  # 重新记账(location=NEW)
    del mod._jobs["jd"]
    store.refresh([])
    store.refresh([t])
    mod.on_task_line()  # 重解析失败 -> 置空
    assert mod.foreign_notified_view()["BX"]["location"] == ""
    assert len(dirty) == 4
    # 闸关冻结(nit 7): foreign_torrent 翻 false -> 侦测面早退, 发布视图引用恒稳不炸
    mod._ctx.config.relocate.foreign_torrent = False
    frozen = mod.foreign_notified_view()
    mod.on_task_line()
    assert mod.foreign_notified_view() is frozen
    assert len(dirty) == 4  # 关断拍零换代零 mark_dirty


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


# ---------- 链式闭包解析器(T4/S4: 直连边 -> 传递闭包 A->B->C, 计划 D2/R7) ----------


def test_foreign_resolve_closure_chain_two_done_hops():
    """链式 A->B->C: 两代 done 终态账边拼成闭包 —— resolve(A) 报现位置 C(job_id/phase 取末跳)"""
    mod, _store, _client = _env()
    mod._jobs = {
        "j1": _job("j1", phase=ru.PHASE_DONE, src="R:/a", dst="R:/b", updated_at=100.0),
        "j2": _job("j2", phase=ru.PHASE_DONE, src="R:/b", dst="R:/c", updated_at=200.0),
    }
    edge = mod._foreign_resolve_old_root("R:/a")
    assert (edge.src, edge.dst, edge.job_id, edge.phase) == ("R:/a", "R:/c", "j2", "done")
    # 中间代旧根仍是合法查询起点: B -> C 单跳
    edge_b = mod._foreign_resolve_old_root("R:/b")
    assert (edge_b.src, edge_b.dst, edge_b.job_id) == ("R:/b", "R:/c", "j2")


def test_foreign_resolve_closure_via_inherited_entry():
    """移交条目(plan.inherited)并入边集: 最老代 done 账滚出后, 继承条目仍供 A->B 边接链"""
    mod, _store, _client = _env()
    plan = {
        "files":
            list(PLAN_FILES),
        "inherited":
            [
                {
                    "job_id": "j1",
                    "src": "R:/a",
                    "dst": "R:/b",
                    "scope": "R:/a",
                    "alias_kind": "dir",
                    "alias_paths": ["R:/a"],
                    "link_kind": "junction",
                }
            ],
    }
    mod._jobs = {
        # j1 已滚出终态账(不在 _jobs); j2 done 携带其移交条目 + 自身 B->C 边
        "j2": _job("j2", phase=ru.PHASE_DONE, src="R:/b", dst="R:/c", plan=plan, updated_at=200.0),
    }
    edge = mod._foreign_resolve_old_root("R:/a")
    assert (edge.src, edge.dst, edge.job_id, edge.phase) == ("R:/a", "R:/c", "j2", "done")
    # 继承条目作末跳(携带 owner 无自身边, 如 owner 未收官): 边照走, phase 随 owner 现相位;
    # 条目 job_id 指向已滚出的前任(_jobs 无 j1) -> 边身份回落携带 owner(评审 minor 修,
    # 消费面 get_job/files_match 可解析)
    mod._jobs["j2"] = _job("j2", phase=ru.PHASE_ARMED, src="R:/z", dst="R:/w", plan=plan, updated_at=200.0)
    edge2 = mod._foreign_resolve_old_root("R:/a")
    assert (edge2.src, edge2.dst, edge2.job_id, edge2.phase) == ("R:/a", "R:/b", "j2", "armed")


def test_foreign_resolve_closure_cycle_no_hang():
    """环保护: 脏数据 A->B->A 不得死循环 —— 行走到已访根即停, 回报已走到的最后一条真边"""
    mod, _store, _client = _env()
    mod._jobs = {
        "j1": _job("j1", phase=ru.PHASE_DONE, src="R:/a", dst="R:/b", updated_at=100.0),
        "j2": _job("j2", phase=ru.PHASE_DONE, src="R:/b", dst="R:/a", updated_at=200.0),
    }
    edge = mod._foreign_resolve_old_root("R:/a")
    assert (edge.src, edge.dst, edge.job_id) == ("R:/a", "R:/b", "j1")
    # 反向查询同样收在自身首跳(visited 集, 双向都不挂死)
    edge_b = mod._foreign_resolve_old_root("R:/b")
    assert (edge_b.src, edge_b.dst, edge_b.job_id) == ("R:/b", "R:/a", "j2")


def test_foreign_resolve_closure_depth_cap_partial(monkeypatch):
    """深度上限: 超限停走回报已走到的部分位置(尽力而为, D2), 不挂死不抛"""
    monkeypatch.setattr(rf, "_FOREIGN_CLOSURE_MAX_HOPS", 2)
    mod, _store, _client = _env()
    mod._jobs = {
        "j1": _job("j1", phase=ru.PHASE_DONE, src="R:/a", dst="R:/b", updated_at=100.0),
        "j2": _job("j2", phase=ru.PHASE_DONE, src="R:/b", dst="R:/c", updated_at=200.0),
        "j3": _job("j3", phase=ru.PHASE_DONE, src="R:/c", dst="R:/d", updated_at=300.0),
    }
    edge = mod._foreign_resolve_old_root("R:/a")
    assert (edge.src, edge.dst, edge.job_id) == ("R:/a", "R:/c", "j2"), "上限 2 跳: 走到 C 即停"


def test_foreign_resolve_same_root_rank_owner_newest_and_own_beats_inherited():
    """同根多条边取新口径: 按 owner (updated_at, job_id) 取最新; 同 owner 平手时自身边压过继承条目"""
    mod, _store, _client = _env()
    plan_old = {
        "files":
            list(PLAN_FILES),
        "inherited":
            [
                {
                    "job_id": "jp",
                    "src": OLD,
                    "dst": "R:/stale",
                    "scope": OLD,
                    "alias_kind": "dir",
                    "alias_paths": [OLD],
                    "link_kind": "junction",
                }
            ]
    }
    mod._jobs = {
        # 同 owner(j2)自身 done 边与携带的继承条目同根: 自身边优先(自身收官压过继承史);
        # jp 在账(done, 无关根)—— 条目身份可解析时照报条目 job_id(悬空回落是另一支, 专属测钉)
        "jp": _job("jp", phase=ru.PHASE_DONE, src="R:/unrelated", dst="R:/u", updated_at=50.0),
        "j2": _job("j2", phase=ru.PHASE_DONE, src=OLD, dst="R:/own", plan=plan_old, updated_at=200.0),
        "j1": _job("j1", phase=ru.PHASE_DONE, src=OLD, dst="R:/older", updated_at=100.0),
    }
    edge = mod._foreign_resolve_old_root(OLD)
    assert (edge.job_id, edge.dst) == ("j2", "R:/own")
    # 更新 owner 的继承条目压过更老 done 自身边(取新 = owner 时刻序, 与 ru.job_rank 终态分支同序)
    plan_new = {
        "files":
            list(PLAN_FILES),
        "inherited":
            [
                {
                    "job_id": "jp2",
                    "src": OLD,
                    "dst": "R:/fresh",
                    "scope": OLD,
                    "alias_kind": "dir",
                    "alias_paths": [OLD],
                    "link_kind": "junction",
                }
            ]
    }
    # jp2 同样入账(done, 无关根): 条目身份可解析 -> 照报条目 job_id(悬空回落支不在此测)
    mod._jobs["jp2"] = _job("jp2", phase=ru.PHASE_DONE, src="R:/unrelated2", dst="R:/u2", updated_at=50.0)
    mod._jobs["j3"] = _job("j3", phase=ru.PHASE_ARMED, src="R:/x", dst="R:/y", plan=plan_new, updated_at=300.0)
    edge2 = mod._foreign_resolve_old_root(OLD)
    assert (edge2.job_id, edge2.dst, edge2.phase) == ("jp2", "R:/fresh", "armed")


def test_foreign_resolve_expired_mapping_is_none():
    """R7 映射过期语义: 终态账滚动(载体 job 全部滚出)后解析不出 -> None(与「非旧根」同形,
    判据面不加持久账不可区分 —— D2; T5 通知文案按 None 口径降级「映射已过期」)"""
    mod, _store, _client = _env()
    mod._jobs = {"jx": _job("jx", phase=ru.PHASE_DONE, src="R:/other", dst="R:/z", updated_at=100.0)}
    assert mod._foreign_resolve_old_root(OLD) is None
    mod._jobs = {}
    assert mod._foreign_resolve_old_root(OLD) is None


def test_foreign_resolve_purged_pred_falls_back_to_owner_and_matchable():
    """边身份回落(评审 minor 修): 继承条目指向已滚出/清账的前任(_jobs 无此 id)时
    edge.job_id 回落携带 owner —— 消费面 get_job 命中、_foreign_files_match 出判定
    (不再判「不可判定」出队), 场景 B 命中在 owner 收官前能记账"""
    mod, store, client = _env()
    plan = {
        "files":
            list(PLAN_FILES),
        "inherited":
            [
                {
                    "job_id": "jp",
                    "src": OLD,
                    "dst": "R:/mid",
                    "scope": OLD,
                    "alias_kind": "dir",
                    "alias_paths": [OLD],
                    "link_kind": "junction",
                }
            ],
    }
    mod._jobs = {
        # 前任 jp 已被清账/滚出(不在 _jobs); owner j2 未收官(armed), 边来自其移交条目
        "j2": _job("j2", phase=ru.PHASE_ARMED, src="R:/z", dst="R:/w", plan=plan, updated_at=200.0),
    }
    edge = mod._foreign_resolve_old_root(OLD)
    assert (edge.src, edge.dst, edge.job_id, edge.phase) == (OLD, "R:/mid", "j2", "armed")
    assert mod.get_job(edge.job_id) is not None, "回落后的 job_id 必须在账可解析"
    client.files_map["BX"] = _seed()
    store.refresh([FakeTorrent(hash="BX", name="done-root", save_path=OLD)])
    rec = store.get("BX")
    hit = rf.ForeignHit(
        hash="BX",
        save_path=OLD,
        scenario="B",
        job_id=edge.job_id,
        phase=edge.phase,
        old_root=edge.src,
        location=edge.dst
    )
    assert mod._foreign_files_match(rec, hit) is True, "清单一致 -> 可判定(不再因 get_job 未命中出队)"


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
    """单拍有界 FIFO: 25 条候选按预算分三拍消化, 池内余量跨拍续; 游标消费即排空(F2)无残值重入

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
    mod.on_task_line()  # tick3: 游标已排空(F2), 池余量续消费恰池序最前 10 条
    new3 = set(notified) - processed2
    assert len(new3) == _FOREIGN_TICK_BUDGET and new3 == set(remaining[:_FOREIGN_TICK_BUDGET])
    mod.on_task_line()  # tick4: 清尾(remaining[10:] 5 条真候选), 池清空
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
        # 计数按文案分面(T5 起 GOOD 命中自带通知 WARNING): 护栏告警恰一次 + 通知告警恰一次
        guard = [m.getMessage() for m in cap.records if m.levelno == logging.WARNING and "处理异常" in m.getMessage()]
        notice = [m.getMessage() for m in cap.records if m.levelno == logging.WARNING and "旧路径外部种子" in m.getMessage()]
        assert len(guard) == 1 and any("BAD" in w for w in guard), guard
        assert len(notice) == 1 and any("GOOD" in w for w in notice), notice
        mod.on_task_line()  # tick3: 留池候选重试, 重复异常转 DEBUG 不重告
        assert _warn_count(cap) == 2  # 零新增(BAD 重复异常转 DEBUG; GOOD 通知不重复)
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


# ---------- 覆盖率缺口清偿(26-11-21 接缝终审 + test.full 闸门收敛): 防御分支与退化形态的真语义面 ----------


def test_foreign_scan_bad_record_skipped(monkeypatch):
    """全量兜底扫逐记录护栏: 单记录分类炸(DEBUG 跳过)不得拖垮整次扫描, 同扫其它候选照常入池
    (store 层已把快照记录归一, 护栏防的是判定管线内部的脏账形态)"""
    mod, store, client = _env()
    _done_job(mod)
    orig = mod._foreign_classify

    def _classify(rec):
        if rec.hash == "BAD":
            raise RuntimeError("dirty account shape")
        return orig(rec)

    monkeypatch.setattr(mod, "_foreign_classify", _classify)
    client.files_map["G1"] = _seed()
    store.refresh(
        [FakeTorrent(hash="BAD", name="bad", save_path=OLD),
         FakeTorrent(hash="G1", name="good", save_path=OLD)]
    )
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        n = mod._foreign_full_scan("test")
    assert n == 1 and list(mod._foreign_pending) == ["G1"], "坏记录不得拦好候选入池"
    assert any("扫描跳过坏记录" in m and "BAD" in m for m in cap.messages), cap.messages


def test_foreign_classify_empty_save_path_is_no_hit():
    """分类预门: save_path 为空(快照退化形态)不判定不炸, 按 None(未命中)出"""
    mod, _store, _client = _env()
    assert mod._foreign_classify(FakeTorrent(hash="E1", name="empty", save_path="")) is None


def test_foreign_resolve_empty_query_root_is_none():
    """反查预门: 空查询根无边可走返回 None(与「非旧根」同 None 出队口径, 空串不出假边)"""
    mod, _store, _client = _env()
    _done_job(mod)
    assert mod._foreign_resolve_old_root("") is None


def test_foreign_resolve_self_loop_first_hop_rejected_single_edge():
    """脏数据自环(done job src == dst): 首跳即被拒(dst 已在 visited)不挂死,
    单边尽力而为 —— 仍回报该边自身位置, 不得 None"""
    mod, _store, _client = _env()
    mod._jobs = {"j1": _job("j1", phase=ru.PHASE_DONE, src="R:/loop", dst="R:/loop", updated_at=100.0)}
    edge = mod._foreign_resolve_old_root("R:/loop")
    assert edge is not None, "首跳被拒仍回报单边(尽力而为)"
    assert (edge.src, edge.dst, edge.job_id, edge.phase) == ("R:/loop", "R:/loop", "j1", "done")


def test_foreign_inherited_entries_non_matching_skipped_in_classify():
    """多继承条目分类: 不命中条目跳过继续走, 命中条目照常产出场景 A(old_root 记命中条目 src)"""
    mod, store, client = _env()
    _hold_phase_machine(mod)  # 裸环境同拍推进判失败会清 A 条目(B2), 本测只钉分类面
    plan = {
        "files":
            list(PLAN_FILES),
        "inherited":
            [
                {
                    "job_id": "jp1",
                    "src": "R:/zzz",
                    "dst": "R:/mid",
                    "scope": "R:/zzz",
                    "alias_kind": "dir"
                },
                {
                    "job_id": "jp2",
                    "src": "R:/old2",
                    "dst": "R:/mid2",
                    "scope": "R:/old2",
                    "alias_kind": "dir"
                },
            ],
    }
    mod._jobs["ja"] = _job("ja", phase=ru.PHASE_MOVED, src="R:/main", dst=NEW, plan=plan)
    client.files_map["IN2"] = _seed()
    store.refresh([FakeTorrent(hash="IN2", name="inh", save_path="R:/old2")])
    mod.on_task_line()
    notified = mod._state_foreign_notified()
    assert notified["IN2"]["kind"] == "A"
    assert notified["IN2"]["root"] == ru._norm("R:/old2") and notified["IN2"]["job_id"] == "ja"


def test_foreign_closure_skips_inherited_entry_without_dst():
    """边集构建: dst 为空的移交条目(坏形记录)不产边, 自身直连边不受影响"""
    mod, _store, _client = _env()
    plan = {
        "files": list(PLAN_FILES),
        "inherited": [{
            "job_id": "jp",
            "src": "R:/ghost",
            "dst": "",
            "scope": "R:/ghost",
            "alias_kind": "dir"
        }],
    }
    mod._jobs["jd"] = _job("jd", phase=ru.PHASE_DONE, src=OLD, dst=NEW, plan=plan, updated_at=100.0)
    assert mod._foreign_resolve_old_root("R:/ghost") is None, "空 dst 条目不进边集"
    edge = mod._foreign_resolve_old_root(OLD)
    assert edge is not None and edge.dst == NEW, "自身直连边不受坏条目影响"


def test_foreign_drain_candidate_joined_active_job_pops():
    """排队期间成为活跃 job 成员(相位机接管): 出队不记账 —— 去重面在分类之后仍生效"""
    mod, store, client = _env()
    _done_job(mod)  # 旧根边在场: 分类命中场景 B, 计账被成员门拦下
    mod._jobs["ja"] = _job("ja", phase=ru.PHASE_ARMED, src="R:/elsewhere", dst="R:/elsewhere2", hashes=("QX", ))
    client.files_map["QX"] = _seed()
    store.refresh([FakeTorrent(hash="QX", name="late", save_path=OLD)])
    mod._foreign_enqueue("QX")  # 直接入池(模拟「入池后才被纳入」的竞态窗)
    mod._foreign_drain()
    assert "QX" not in mod._state_foreign_notified(), "相位机在管的成员不入外部账"
    assert "QX" not in mod._foreign_pending, "候选出队"


def test_foreign_drain_undecidable_file_table_pops_without_account():
    """文件表读空而账面非空 = 不可判定(D4): 出队不记账不误报, 重试靠时机兜底扫(不占池位)"""
    mod, store, client = _env()
    _done_job(mod)
    client.files_map["UD"] = []  # 种子侧文件表空, 账面 plan.files 非空
    store.refresh([FakeTorrent(hash="UD", name="undecidable", save_path=OLD)])
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod.on_task_line()
    assert "UD" not in mod._state_foreign_notified() and "UD" not in mod._foreign_pending
    assert any("文件表不可判定" in m for m in cap.messages), cap.messages


def test_foreign_files_match_undecidable_guards():
    """文件表比对预门: qB API 缺席(断连窗)与账面 job 已不在(撤销竞态)均按不可判定 None 出
    —— 不把事实缺失误报成清单不一致"""
    mod, _store, client = _env()
    _done_job(mod)
    rec = FakeTorrent(hash="M1", name="m", save_path=OLD)
    hit = rf.ForeignHit(hash="M1", save_path=OLD, scenario="B", job_id="jd", phase="done", old_root=OLD, location=NEW)
    api = mod._ctx.api
    mod._ctx.api = None
    assert mod._foreign_files_match(rec, hit) is None, "client 缺: 不可判定"
    mod._ctx.api = api
    assert mod._foreign_files_match(rec, replace(hit, job_id="nope")) is None, "job 账不在: 不可判定"


def test_include_hold_member_api_missing_no_account(tmp_path):
    """pre-armed 纳入按住步: qB API 缺席(重连窗)不暂停不挂账不炸 —— 纳入的收尾覆盖面不依赖暂停位"""
    mod, store, client = _env(data_dir=str(tmp_path))
    mod._jobs["ja"] = _armed_job(phase=ru.PHASE_MOVED)
    store.refresh([_foreign_rec(client, state="stalledUP")])
    mod._ctx.api = None
    assert mod._foreign_hold_member("EXT") == ()
    assert ("pause", ["EXT"]) not in client.calls


def test_include_prearm_pause_failure_still_incorporates(tmp_path, monkeypatch):
    """pre-armed 纳入暂停失败(qB 拒/断): 不堵纳入照常转正, 只少一条恢复账(种子保持原态)"""
    mod, store, client = _env(data_dir=str(tmp_path))
    mod._jobs["ja"] = _armed_job(phase=ru.PHASE_MOVED)

    def _boom(**kw):
        raise RuntimeError("qb rejected")

    monkeypatch.setattr(mod._ctx.api, "torrents_pause", _boom)
    store.refresh([_foreign_rec(client, state="stalledUP")])
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod._foreign_on_scenario_a(_hit(phase=ru.PHASE_MOVED))
    job = mod.get_job("ja")
    assert job.hashes == ("MEM", "EXT"), "纳入不受暂停失败影响"
    assert job.resume_hashes == (), "暂停失败不挂恢复账"
    assert any("纳入暂停失败" in m.getMessage() for m in cap.records if m.levelno == logging.WARNING)


def test_include_extend_spec_member_already_listed_is_noop(tmp_path):
    """spec 已含该成员(job 账竞态落后形态): 幂等返回, 不产生重复 members 条目"""
    mod, _store, _client = _env(data_dir=str(tmp_path))
    mod._jobs["ja"] = _armed_job()
    relocate_journal.write_spec(str(tmp_path), "ja", {"members": [{"hash_v1": "EXT", "hash_v2": ""}]})
    mod._foreign_extend_spec(_hit())
    spec = relocate_journal.read_spec(str(tmp_path), "ja")
    assert [m["hash_v1"] for m in spec["members"]] == ["EXT"], "重放面幂等: 不重复追加"


def test_include_extend_spec_write_failure_warns_and_keeps_disk(tmp_path, monkeypatch):
    """spec 落盘失败(磁盘/IO): 告警不炸不堵纳入, 盘面 spec 保持原形(改写未回流面交 T4 守卫)"""
    mod, _store, _client = _env(data_dir=str(tmp_path))
    mod._jobs["ja"] = _armed_job()
    assert mod._write_arm_spec(mod.get_job("ja"))

    def _boom(*a, **kw):
        raise OSError("disk full")

    monkeypatch.setattr(relocate_journal, "write_spec", _boom)
    with capture_logs("auto_qb.core.modules.relocate_mod") as cap:
        mod._foreign_extend_spec(_hit())
    assert any("spec 追加成员失败" in m.getMessage() for m in cap.records if m.levelno == logging.WARNING)
    assert [m["hash_v1"] for m in relocate_journal.read_spec(str(tmp_path), "ja")["members"]] == ["MEM"]


def test_include_tag_member_api_missing_skips_incremental(tmp_path):
    """增量补打预门: qB API 缺席不单发不炸, 镜像态不翻动(全量补写面按退避接管)"""
    mod, _store, client = _env(data_dir=str(tmp_path))
    mod._ctx.config.relocate = RelocateConfig(enabled=True, foreign_torrent=True, pending_tag="aqb-finalize")
    mod._jobs["ja"] = _armed_job()
    mod._tag_applied["ja"] = "add"
    mod._ctx.api = None
    mod._foreign_tag_member("ja", "EXT", was_add=True)
    assert mod._tag_applied["ja"] == "add", "镜像态不翻动(交补写面自愈)"
    assert not [c for c in client.calls if c[0].startswith("add_tags")]


def test_foreign_restore_location_only_b_entries():
    """空位回填只认 kind=B 条目: 场景 A hit 不回填(B 面板不遮蔽), 异物条目不炸"""
    mod, _store, _client = _env()
    hit = _hit(job_id="ja", phase=ru.PHASE_ARMED)
    entry_a = {"root": ru._norm(OLD), "kind": "A", "job_id": "ja", "phase": "armed", "location": "", "first_seen": 1.0}
    mod._foreign_restore_location(entry_a, hit)
    assert entry_a["location"] == "", "非场景 B 条目不回填"
    mod._foreign_restore_location("garbage", hit)  # 账面异物: 不炸


def test_foreign_publish_view_skips_non_dict_entries():
    """发布视图投影: notified 账异物条目(非 dict)跳过不炸, dict 条目照常投影"""
    mod, _store, _client = _env()
    notified = mod._state_foreign_notified()
    notified["VX"] = {
        "root": ru._norm(OLD),
        "kind": "B",
        "job_id": "jd",
        "phase": "done",
        "location": NEW,
        "first_seen": 1.0,
    }
    notified["W"] = "garbage"
    mod._foreign_publish_view()
    view = mod.foreign_notified_view()
    assert set(view.keys()) == {"VX"}, "异物不投影"
    assert view["VX"]["kind"] == "B" and view["VX"]["location"] == NEW


def test_state_foreign_readers_tolerate_missing_state():
    """state 上下文缺失(data 非 dict): notified 读写两 reader 都回空 dict 不炸, 零 materialize"""
    mod, _store, _client = _env()
    mod._ctx.state = SimpleNamespace(data=None)
    assert mod._state_foreign_notified() == {}
    assert mod._state_foreign_notified_view() == {}
