"""relocate 可见性纯投影层(plan 26-11-04-1042 P0)

输入: 主循环发布的只读 job 快照/成员视图; 输出: 成员 `relocate` 标注与组级聚合。
**零触盘**: 本文件不 lstat/readlink, 不做任何文件系统探测 —— 列表渲染期只读内存快照。
**零 _jobs 遍历**: 成员判定走快照的 `by_hash` O(1) 查找; 组级聚合只扫成员视图,
不遍历 job 表。组级状态在后端算好, 前端不得取首成员推断。
"""
from typing import Optional, Sequence

from ..core.modules import relocate_units as ru

# 相位 -> 展示状态归并(plan 数据契约):
#   moving / watching                         -> moving(进行中)
#   moved / armed / removing / removed / finalizing -> pending_finalize(待收尾, armed)
#   done / failed / cancelled                 -> 同名终态
MOVING_PHASES = frozenset({ru.PHASE_MOVING, ru.PHASE_WATCHING})
PENDING_PHASES = frozenset(
    {
        ru.PHASE_MOVED,
        ru.PHASE_ARMED,
        ru.PHASE_REMOVING,
        ru.PHASE_REMOVED,
        ru.PHASE_FINALIZING,
    }
)
_ACTIVE_STATES = frozenset({"moving", "pending_finalize"})
# 组级优先序: failed > moving > pending_finalize > done。cancelled 不进组级标注
# (已撤销 = 无迁移在进行, 不挂徽标)。
_PRIORITY = {"failed": 4, "moving": 3, "pending_finalize": 2, "done": 1}


def state_of_phase(phase: str) -> str:
    """job 相位 -> 展示状态(未知/缺相位按 moving: 旧 state 条目补丁口径)"""
    p = str(phase or ru.PHASE_MOVING)
    if p in MOVING_PHASES:
        return "moving"
    if p in PENDING_PHASES:
        return "pending_finalize"
    if p == ru.PHASE_DONE:
        return "done"
    if p == ru.PHASE_FAILED:
        return "failed"
    if p == ru.PHASE_CANCELLED:
        return "cancelled"
    return "moving"


def member_relocate(job: Optional[dict], torrent_hash: str) -> Optional[dict]:
    """单个成员(或种子页条目)的迁移标注; 无 job 返回 None(字段恒在/值为 null 的契约)

    mover / alias_paths / origin 全部来自 job 快照, 不做路径归属猜测:
    「是否 auto-qb 设置」严格按 job 的 hash 覆盖与 mover 精确匹配判定。
    """
    if not job:
        return None
    phase = str(job.get("phase") or ru.PHASE_MOVING)
    alias_paths = tuple(job.get("alias_paths") or ())
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
    }


def group_relocate(members: Sequence[dict]) -> Optional[dict]:
    """组级迁移聚合(后端算, 前端只渲染)

    - state: 成员标注的最高优先级状态; 同一优先级出现多个不同 job_id -> "mixed"
    - pending / total: 非终态成员数 / 组内成员总数(按成员计, 同一 job 覆盖多个成员时逐成员计入)
    - job_ids / dst: 全组涉及的非撤销 job 去重排序
    全组无标注(无 job / 全部 cancelled / relocate 关) -> None。
    """
    annotations = [m.get("relocate") for m in members if m.get("relocate")]
    annotations = [a for a in annotations if a.get("state") != "cancelled"]
    if not annotations:
        return None
    top_priority = max(_PRIORITY.get(a.get("state"), 0) for a in annotations)
    top = [a for a in annotations if _PRIORITY.get(a.get("state"), 0) == top_priority]
    state = str(top[0]["state"]) if len({a.get("job_id") for a in top}) == 1 else "mixed"
    return {
        "state": state,
        "pending": sum(1 for a in annotations if a.get("state") in _ACTIVE_STATES),
        "total": len(members),
        "job_ids": sorted({str(a.get("job_id") or "")
                           for a in annotations}),
        "dst": sorted({str(a.get("dst") or "")
                       for a in annotations if a.get("dst")}),
        "updated_at": max(float(a.get("updated_at") or 0.0) for a in annotations),
    }
