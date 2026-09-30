"""checking 域共用常量与冷却计数 helper 的中性单点(plan kernel-module-refactor P4)

轮询常量 / 冷却 helper 自 actions/full_checking.py 迁入本模块(plan §5: 「迁到 rules 包
中性位置; ops 与 rules 单向依赖」) —— 中性指: 本模块是 rules 包内的**叶子**, 不 import
actions / core 任何模块, ops 层(core/modules/ops_mod)经它取常量不会拖入动作插件注册,
也不再依赖某个动作实现模块的内部细节。

依赖方向(单向, 防环):
- core/modules/ops_mod -> 本模块: 取轮询常量与冷却 helper(消费方);
- actions/full_checking -> 本模块: 决策链 1.5/1.6 同源取用;
- 本模块**不得** import 任何一侧 —— 否则 ops -> rules 包初始化 -> actions -> 本模块成环。

冷却 helper 的宿主参数按鸭子类型收敛为「有 .state dict 与 .save_state() 的对象」:
manager(QbManager 委托)与 ops 模块(ctx.state 门面)都满足, 测试直传 mgr 亦然。
"""
from datetime import date

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


def _recheck_fail_count(manager, hash: str) -> int:
    """同一种子当日连续校验失败次数(按自然日重置)"""
    rec = manager.state.get("recheck_fails", {}).get(hash)
    if rec and rec.get("date") == date.today().isoformat():
        return rec.get("count", 0)
    return 0


def _bump_recheck_fail(manager, hash: str) -> int:
    """累加当日校验失败次数并返回当前次数"""
    fails = manager.state.setdefault("recheck_fails", {})
    rec = fails.setdefault(hash, {"date": "", "count": 0})
    today = date.today().isoformat()
    if rec.get("date") != today:
        rec["date"] = today
        rec["count"] = 0
    rec["count"] += 1
    manager.save_state()  # 冷却计数即时落盘: 丢了会对同一损坏文件多试 recheck(当日上限闸门失效一次); 上界 3 次/日/种, 频率天然低
    return rec["count"]
