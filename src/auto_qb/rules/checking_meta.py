"""checking 域共用常量与冷却计数 helper 的中性单点(plan kernel-module-refactor P4)

轮询常量 / 冷却 helper 自 actions/full_checking.py 迁入本模块(plan §5: 「迁到 rules 包
中性位置; ops 与 rules 单向依赖」) —— 中性指: 本模块是 rules 包内的**叶子**, 不 import
actions / core 任何模块, ops 层(core/modules/ops_mod)经它取常量不会拖入动作插件注册,
也不再依赖某个动作实现模块的内部细节。

依赖方向(单向, 防环):
- core/modules/ops_mod -> 本模块: 取轮询常量与冷却 helper(消费方);
- actions/full_checking -> 本模块: 决策链 1.5/1.6 同源取用;
- 本模块**不得** import 任何一侧 —— 否则 ops -> rules 包初始化 -> actions -> 本模块成环。

冷却 helper 的宿主参数自 P0 起收敛为 StateService(ctx.state 服务): 计数读写走 .data,
即时落盘走 .save() —— manager(QbManager)侧传 manager.ctx.state, ops 模块传 self._ctx.state,
测试直传 mgr.ctx.state 亦然。

判定纯函数(plan 26-10-04-1824 S1): poll_verdict 是 recheck 轮询单跳判定的唯一出口,
「无证据成功」在签名层面不可表达; PieceCheckingStates / is_piece_checking 提供生效证据谓词。
"""
from datetime import date
from enum import Enum

# full-checking 校验结果轮询间隔(秒): 与主循环 MAIN_TICK 对齐, 需求指定 2s
CHECK_RESULT_INTERVAL = 2.0

# 同一种子当日连续校验失败上限: 防止损坏文件导致 recheck 死循环(次日重置)
RECHECK_FAIL_LIMIT = 3

# 组内校验等待上限(秒): 防在途标记异常泄漏导致等待任务活锁(大种子全量校验可超 1h, 取宽松值)
GROUP_CHECK_WAIT_LIMIT = 2 * 3600.0

# 校验启动宽限上限(秒): recheck 提交后 qB 异步应用 + 同步快照按 sync_interval 节拍滞后,
# 首个轮询样本常落在「尚未开检」窗口内 —— 未见 checking 态不计失败(2026-09-25 首样本
# 竞态误判故障: progress=0.0 被记当日失败, 经决策链 1.6 毒化全组); 宽限耗尽仍未见开检
# 才判败(qB 重启丢请求等极端情形的活锁保险丝, 判败后经 origin 重走决策链自然重试)
CHECK_START_GIVEUP = 600.0

# ============================================================
# recheck 轮询单跳判定纯函数(plan 26-10-04-1824 S1)
# ============================================================

# 真全量校验态集合: qB 正在重读/重验数据。checkingResumeData 是 qB 启动期的简历校验
# (恢复上次中断的校验进度), 不代表本轮 recheck 已生效, 必须排除在生效证据之外。
PieceCheckingStates = frozenset({"checkingDL", "checkingUP"})


def is_piece_checking(state: str) -> bool:
    """是否处于真正的全量校验态(生效证据谓词)

    排除 qB 启动期的 checkingResumeData(简历校验): 它是恢复历史校验进度的伪证据别名,
    与本轮 recheck 是否生效无关, 不得作为 seen_checking 的证据来源。
    """
    return state in PieceCheckingStates


class PollVerdict(Enum):
    """recheck 轮询单跳判定的唯一出口集: WAITING 之外的成员都是终局(轮询任务据此续延或落定)"""

    WAITING = "waiting"  # 歧义 -> 继续等(唯一非终局)
    SUCCESS = "success"  # 生效已确认且 progress>=1.0
    FAILED = "failed"  # 生效后未完成; 或未见生效证据而 progress 回落(数据缺损签名)
    START_TIMEOUT = "start_timeout"  # 宽限耗尽仍无生效证据(活锁保险丝)


def poll_verdict(
    *,
    seen_checking: bool,
    progress: float,
    baseline_progress: float,
    elapsed: float,
    giveup: float = CHECK_START_GIVEUP
) -> PollVerdict:
    """轮询单跳判定: 「无证据成功」在签名层面不可表达(成功结论必须有 seen_checking 背书)

    判定顺序语义(自上而下短路):
    - seen_checking 立起(生效已确认) -> 结果判定: progress>=1.0 即 SUCCESS, 否则 FAILED;
      不再看 baseline(成功结论只认生效证据之后的进度)。
    - 未见生效证据时 progress 回落(progress < baseline_progress)即 FAILED: 暂停/做种中的
      种子 progress 只会因校验发现坏块而回落, 回落是标签准确的辅助失败证据; 先于超时判定。
    - 宽限耗尽仍无生效证据(elapsed >= giveup) -> START_TIMEOUT; 仲裁直查在闭包侧, 不入本函数。
    - 其余歧义情形 -> WAITING 继续等。

    事故行对照(issue 26-10-03-1140): 线上现状的成功分支对陈旧快照直接下结论 —— seen=F,
    progress=1.0(=baseline) 被误判「校验成功」; 本函数把该情形钉为 WAITING(未超宽限)或
    START_TIMEOUT(超宽限), 无证据成功不再可表达。
    """
    if seen_checking:  # 生效已确认 -> 结果判定
        return PollVerdict.SUCCESS if progress >= 1.0 else PollVerdict.FAILED
    if progress < baseline_progress:  # 辅助失败证据: 数据缺损签名(暂停/做种中的种子 progress 只会因校验发现坏块而回落); 状态位 delta 不作为证据(拍板 D4)
        return PollVerdict.FAILED
    if elapsed >= giveup:  # 宽限耗尽仍无生效证据; 仲裁直查在闭包侧
        return PollVerdict.START_TIMEOUT
    return PollVerdict.WAITING  # 歧义 -> 继续等


def recheck_fail_count(state, hash: str) -> int:
    """同一种子当日连续校验失败次数(按自然日重置)"""
    rec = state.data.get("recheck_fails", {}).get(hash)
    if rec and rec.get("date") == date.today().isoformat():
        return rec.get("count", 0)
    return 0


def bump_recheck_fail(state, hash: str) -> int:
    """累加当日校验失败次数并返回当前次数"""
    fails = state.data.setdefault("recheck_fails", {})
    rec = fails.setdefault(hash, {"date": "", "count": 0})
    today = date.today().isoformat()
    if rec.get("date") != today:
        rec["date"] = today
        rec["count"] = 0
    rec["count"] += 1
    state.save()  # 冷却计数即时落盘: 丢了会对同一损坏文件多试 recheck(当日上限闸门失效一次); 上界 3 次/日/种, 频率天然低
    return rec["count"]
