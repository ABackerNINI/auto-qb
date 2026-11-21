"""relocate 可见性纯投影层(plan 26-11-04-1042 P0)

输入: 主循环发布的只读 job 快照/成员视图; 输出: 成员 `relocate` 标注与组级聚合。
**零触盘**: 本文件不 lstat/readlink, 不做任何文件系统探测 —— 列表渲染期只读内存快照。
**零 _jobs 遍历**: 成员判定走快照的 `by_hash` O(1) 查找; 组级聚合只扫成员视图,
不遍历 job 表。组级状态在后端算好, 前端不得取首成员推断。
"""
from typing import Optional, Sequence

from ..core.modules import relocate_units as ru
# 恢复确认账的补发上界(issue 26-11-14-1744 §06 (3) 展示面): 穷尽态判定单点在账的机制侧
# (relocate_lifecycle), 常数以公开名 ru.RESUME_RETRY_MAX 住 units(S5-2: 原跨层私有
# import _RESUME_RETRY_MAX 已清), 这里只借同一常数做「恢复确认中 / 不再补发」的展示区分
# —— 不复制数值(漂移即展示谎报), 上界改名/改值由 test_webui_relocate_visibility 的钉扎兜住。

# 相位 -> 展示状态归并已收敛为单点派生函数(I3, 计划 26-11-15-2340 §03.4): 归并表
# (MOVING_PHASES/PENDING_PHASES)与判定体单点在 units.display_state_of_phase, 本文件
# 只保留 state_of_phase 这个 webui 消费面旧入口作薄委托 —— 不再各自维护第二份归并逻辑。
_ACTIVE_STATES = frozenset({ru.DISPLAY_MOVING, ru.DISPLAY_PENDING_FINALIZE})
# 组级优先序: failed > moving > pending_finalize > done > superseded = foreign。cancelled 不进
# 组级标注(已撤销 = 无迁移在进行, 不挂徽标); superseded 只读历史不进活跃集, 但组级聚合仍给它
# 最低优先序(前任专属成员的标注不被当作未知相位误判成 moving); foreign(T5 通知态)与 superseded
# 同垫底 —— 它是「零破坏通知」信息面, 组内有真迁移态时永远让位。
_PRIORITY = {
    ru.DISPLAY_FAILED: 4,
    ru.DISPLAY_MOVING: 3,
    ru.DISPLAY_PENDING_FINALIZE: 2,
    ru.DISPLAY_DONE: 1,
    ru.DISPLAY_SUPERSEDED: 0,
    ru.DISPLAY_FOREIGN: 0,
}
# T5 呈现分流面(notified 账 kind 字段): 面板只列 B/mismatch(A = 已纳入收尾的成员, 由 job
# 标注面接管, 不走外部种子投影)。词值单点在 units FOREIGN_KIND_*, 与侦测落账共用。
_FOREIGN_PANEL_KINDS = frozenset({ru.FOREIGN_KIND_B, ru.FOREIGN_KIND_MISMATCH})

# 收尾窗行状态细化档位(B3-4, 计划 26-11-21-1600 D8): 纯派生的**细分 token**(非展示词)
# —— 展示词单点在前端 decorate.js(RELOCATE_FINALIZE_TEXT), 与 state/tone 的分工同构:
# 后端给区分位, 前端给词。输入 = 相位(journal 合并态; armed->rewritten 单向跟进后的
# job.phase, 投影零触盘不读 journal) + qB 连接态最后已知值, 零新 state 键。
FINALIZE_AWAIT_WINDOW = "await_window"  # armed 收尾窗 + qB 最后已知离线: 等 qB 下线改写窗
FINALIZE_AWAIT_RECHECK = "await_recheck"  # rewritten 收尾窗: 改写已落账, 等成员回连核验


def state_of_phase(phase: str) -> str:
    """job 相位 -> 展示状态(派生单点 = units.display_state_of_phase, 本入口薄委托)"""
    return ru.display_state_of_phase(phase)


def finalize_state(phase: str, qb_connected: Optional[bool]) -> str:
    """收尾窗行状态细分档位(B3-4 纯派生; 计划 26-11-21-1600 D8)

    输入 = job 相位(journal 合并态 —— _step_reconcile 对 armed->rewritten 单向跟进后的
    job.phase, Web 构建期零触盘不读 journal 文件)+ qB 连接态**最后已知值**(None=未知/
    连接中, True=在线, False=离线; 读既有 status 快照面, 不新造状态源):

    - rewritten -> await_recheck: 改写已落账是 journal 合并的**账面事实**, 相位本身即
      权威, 不再要求 qB 态 —— qB 回连中/快照滞后一拍都不降级回 coarse 词(降级 = 回连
      核验窗里「已改写」信息丢失, qB 上下线翻转还会让词面来回抖动);
    - armed + qB 离线(False) -> await_window: 等 qB 下线改写窗; qB 在线/未知时不给
      (armed + 在线 = 别名在场正常做种, 回落 coarse「待收尾」现行为);
    - 其余(moved/moving/终态/未知) -> "": 非收尾窗 armed/rewritten 相位, 消费方回落
      coarse 词表。
    """
    p = str(phase or "")
    if p == ru.PHASE_REWRITTEN:
        return FINALIZE_AWAIT_RECHECK
    if p == ru.PHASE_ARMED and qb_connected is False:
        return FINALIZE_AWAIT_WINDOW
    return ""


def member_relocate(job: Optional[dict], torrent_hash: str, qb_connected: Optional[bool] = None) -> Optional[dict]:
    """单个成员(或种子页条目)的迁移标注; 无 job 返回 None(字段恒在/值为 null 的契约)

    mover / alias_paths / origin 全部来自 job 快照, 不做路径归属猜测:
    「是否 auto-qb 设置」严格按 job 的 hash 覆盖与 mover 精确匹配判定。

    恢复确认账展示面(issue 26-11-14-1744 §06 (3) 展示面, 账字段随 job_to_dict 下发):
    - resume_pending_count / resume_pending_hashes: 未确认回到运行态的成员余量(计数+hash
      列表)。账是 job 级的, 同 job 各成员标注带同一份(与 alias_count 同形); 已删成员可能
      在账(保守挂账), 如实显示不过滤不特殊标注。
    - resume_retries: 已消耗的补发次数(在途文案里的进度); resume_exhausted: 账面 retries
      达补发上界(穷尽后不再补发 —— 与在途态的展示区分单点; 展示文案不作时点承诺,
      成员仍可能自行回流, 该行随后消失)。
    空账(含旧 state 条目缺字段)计数 0, 前端按空不出行(零噪音)。

    收尾窗行状态细化(B3-4, 计划 26-11-21-1600 D8): finalize 档位由 finalize_state 纯派生
    (phase + qb_connected), qb_connected = 调用方读既有 status 快照面的 qB 连接态最后已知
    值(缺省 None = 未知, 与快照滞后同语义: 消费展示按「最后已知」, 不新造状态源)。
    字段恒在(空串 = 不适用), 与 resume_* 字段同契约。
    """
    if not job:
        return None
    phase = str(job.get("phase") or ru.PHASE_MOVING)
    alias_paths = tuple(job.get("alias_paths") or ())
    resume_pending = tuple(str(h) for h in (job.get("resume_pending") or ()))
    resume_retries = int(job.get("resume_retries") or 0)
    return {
        "state": state_of_phase(phase),
        "phase": phase,
        "job_id": str(job.get("job_id") or ""),
        "mover": str(job.get("mover") or "") == torrent_hash,
        "src": str(job.get("src") or ""),
        "dst": str(job.get("dst") or ""),
        "alias_kind": str(job.get("alias_kind") or ""),
        "alias_count": len(alias_paths),
        "created_at": float(job.get("created_at") or 0.0),
        "armed_at": float(job.get("armed_at") or 0.0),
        "updated_at": float(job.get("updated_at") or 0.0),
        "origin": str(job.get("origin") or "unknown"),
        "reason": str(job.get("reason") or ""),
        "resume_pending_count": len(resume_pending),
        "resume_pending_hashes": list(resume_pending),
        "resume_retries": resume_retries,
        "resume_exhausted": bool(resume_pending) and resume_retries >= ru.RESUME_RETRY_MAX,
        # 收尾窗细分档位(B3-4): 空串 = 不适用(非收尾窗 armed/rewritten), 前端回落 coarse 词表
        "finalize": finalize_state(phase, qb_connected),
    }


def group_relocate(members: Sequence[dict]) -> Optional[dict]:
    """组级迁移聚合(后端算, 前端只渲染)

    - state: 成员标注的最高优先级状态; 同一优先级出现多个不同 job_id -> "mixed"
    - pending / total: 非终态成员数 / 组内成员总数(按成员计, 同一 job 覆盖多个成员时逐成员计入)
    - job_ids / dst: 全组涉及的非撤销 job 去重排序
    - src: 成员标注 src 的去重唯一值 —— 全组一致(恰 1 个非空去重值)为该值; 不一致(>1)
      或全缺失(0)为 ""。mixed(state)时 src 语义上不被消费(前端回落单排), 仍按同一规则给值。
    全组无标注(无 job / 全部 cancelled / relocate 关) -> None。
    """
    annotations = [m.get("relocate") for m in members if m.get("relocate")]
    annotations = [a for a in annotations if a.get("state") != "cancelled"]
    if not annotations:
        return None
    top_priority = max(_PRIORITY.get(a.get("state"), 0) for a in annotations)
    top = [a for a in annotations if _PRIORITY.get(a.get("state"), 0) == top_priority]
    top_states = {a.get("state") for a in top}
    if ru.DISPLAY_FOREIGN in top_states and top_states <= {ru.DISPLAY_FOREIGN, ru.DISPLAY_SUPERSEDED}:
        # foreign(T5)通知组不套「多任务」混态: 产出 job 可以有多个(多代迁移各自的旧根命中),
        # 但通知态只表达「这些种子落在外部旧路径上」一件事, job_id 只是元数据不是在途任务。
        # 豁免放宽到 {foreign, superseded} 混合(评审 minor 4): 两者同垫底序, 在时通知面压过
        # 历史态 —— 组里有真实在时迁移(moving 等)时 top 优先序已把它们顶上, 本支不进。
        state = ru.DISPLAY_FOREIGN
    else:
        state = str(top[0]["state"]) if len({a.get("job_id") for a in top}) == 1 else "mixed"
    srcs = {str(a.get("src") or "") for a in annotations}
    srcs.discard("")
    return {
        "state": state,
        "pending": sum(1 for a in annotations if a.get("state") in _ACTIVE_STATES),
        "total": len(members),
        "job_ids": sorted({str(a.get("job_id") or "")
                           for a in annotations}),
        "dst": sorted({str(a.get("dst") or "")
                       for a in annotations if a.get("dst")}),
        "src": next(iter(srcs)) if len(srcs) == 1 else "",
        "updated_at": max(float(a.get("updated_at") or 0.0) for a in annotations),
    }


def foreign_member(entry: Optional[dict]) -> Optional[dict]:
    """外部旧路径种子(T5/S5 通知态)的迁移标注; 无条目/非呈现类别返回 None

    数据源 = relocate.foreign.notified 账的**只读发布视图**(模块侧 foreign_notified_view,
    主循环单写线程整表发布; Web 构建期 O(1) 按hash 取, 与 jobs_snapshot.by_hash 同纪律)。
    分流单点 _FOREIGN_PANEL_KINDS: 只投影 B(终态账旧根命中)/mismatch(清单不一致)两类 ——
    A(已纳入收尾)由 job 标注面接管(该 hash 已是成员, job_for 命中, 本投影不参与)。

    字段契约与 member_relocate 同形(decorate/relocate_pop/drawer_rows 消费面零分支成本,
    只认 state 分流出 foreign 专属块), 另带两个通知态专属字段:
    - first_seen: 账面首见时刻(浮窗「首见」kv / 抽屉「首见」行; 同时占 updated_at 槽 ——
      标注签名 _relocateSig 覆盖 updated_at, 首见变化自然进指纹);
    - expired: R7「映射已过期」位 = location 已被侦测面置空(终态账滚动后重解析失败,
      relocate_foreign._foreign_notify_expired)—— 浮窗/抽屉按它显示降级文案, 前端不重算。
    - kind: 账条目类别透传(B/mismatch, B2 计划 26-11-21-1600)—— 呈现档位词表不扩面,
      前端 mismatch 说明行的区分位(判据只认后端, 与 expired 位同纪律)。
    finalize 恒空串(通知态不在收尾窗, 与 member_relocate 字段契约同形: 字段恒在)。
    """
    if not entry:
        return None
    kind = str(entry.get("kind") or "")
    if kind not in _FOREIGN_PANEL_KINDS:
        return None
    location = str(entry.get("location") or "")
    first_seen = float(entry.get("first_seen") or 0.0)
    return {
        "state": ru.DISPLAY_FOREIGN,
        "phase": str(entry.get("phase") or ""),
        "job_id": str(entry.get("job_id") or ""),
        "mover": False,
        "src": str(entry.get("root") or ""),
        "dst": location,
        "alias_kind": "",
        "alias_count": 0,
        "created_at": 0.0,
        "armed_at": 0.0,
        "updated_at": first_seen,
        "origin": "",
        "reason": "",
        "resume_pending_count": 0,
        "resume_pending_hashes": [],
        "resume_retries": 0,
        "resume_exhausted": False,
        "finalize": "",
        "first_seen": first_seen,
        "expired": not location,
        # kind 透传(B2, 计划 26-11-21-1600): 前端 mismatch 说明行的区分位(与 expired 位同
        # 纪律: 区分位只认后端投影, 前端不重推)—— 呈现档位词表不扩面, 只加数据位。
        "kind": kind,
    }
