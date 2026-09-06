"""full-checking 执行与组内校验串行化(FullCheckingMixin)

包含: 校验常量(轮询间隔/失败上限/等待上限)、当日失败计数 helper、
full-checking 提交+轮询(_execute_full_checking)、组内串行闸门
(_wait_for_group_checking, 决策链 1.5)与失败推断闸门
(_skip_on_group_check_failed, 决策链 1.6)。
"""
import logging
import time
from datetime import date
from typing import Optional

from ...taskqueue import Task
from ..base import ActionResult, RuleContext

logger = logging.getLogger(__name__)

# full-checking 校验结果轮询间隔(秒): 与主循环 MAIN_TICK 对齐, 需求指定 2s
CHECK_RESULT_INTERVAL = 2.0

# 同一种子当日连续校验失败上限: 防止损坏文件导致 recheck 死循环(次日重置)
RECHECK_FAIL_LIMIT = 3

# 组内校验等待上限(秒): 防在途标记异常泄漏导致等待任务活锁(大种子全量校验可超 1h, 取宽松值)
GROUP_CHECK_WAIT_LIMIT = 2 * 3600.0


def _recheck_fail_count(manager, hash: str) -> int:
    """同一种子当日连续校验失败次数(按自然日重置, 与 upload_size_today 口径一致)"""
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
    return rec["count"]


class FullCheckingMixin:
    """full-checking 执行与组内校验串行化: 由 CheckAction 组合, 依赖 self 的
    basic_check/with_reference/without_reference(checking.py 解析)"""
    def _execute_full_checking(self, ctx: RuleContext, segment: dict):
        """full-checking: 同步发送 recheck 后创建校验结果轮询任务(快速队列, interval=CHECK_RESULT_INTERVAL)

        触发流程:
          1) 同步发送 torrents_recheck(API 同步返回, 校验后台异步), 失败则直接失败(不建任务)
          2) 触发任务(origin)让位(defer: 不入队不消亡), 动作返回 pending(规则断点), 由轮询任务
             在完成后决定恢复方式
          3) 轮询任务每 CHECK_RESULT_INTERVAL 秒检查 store 快照, 退出 checking* 即完成:
             成功(progress>=1) -> origin.resume(触发 resume_cb: 晋升 verified_references +
               auto_start; resume_index 保留 -> 规则续跑执行后续动作, 执行历史由 Rule.process 统一记录)
             失败(progress<1)/种子删除/异常 -> 清断点 + origin.reschedule(重走决策链再次校验)
          4) 提交经 add_check_task 登记在途(task_queue._active_checks, 决策链 1.5 组内串行化
             依赖), 轮询任务消亡时由 task_died 释放
        """
        manager = ctx.manager
        hash = ctx.hash

        # 失败冷却: 当日连续校验失败达上限后不再重试(防损坏文件导致 recheck 死循环), 次日重置
        if _recheck_fail_count(manager, hash) >= RECHECK_FAIL_LIMIT:
            return ActionResult.skip(f"校验连续失败 {RECHECK_FAIL_LIMIT} 次, 今日不再重试")

        tq = ctx.manager.task_queue
        origin = getattr(ctx, "task", None)  # 触发本次校验的规则任务(任务队列驱动); 外部入口为 None
        rule_name = ctx.rule_name
        api = ctx.api
        auto_start = segment["auto_start"]

        def on_success():
            """校验成功完成处理: 晋升参考(仅内存, 不写 state_file) + auto_start
            执行历史由恢复后的规则任务(Rule.process 续跑)统一记录
            """
            manager.store.verified_references.add(hash)
            manager.state.get("recheck_fails", {}).pop(hash, None)  # 校验通过: 清除失败冷却计数
            if auto_start and not ctx.dry_run:
                api.torrents_start(torrent_hashes=hash)
                logger.info(f"规则[{rule_name}] {ctx.torrent.log_repr} | 校验成功自动开始")

        def poll(task: Task, dry_run: bool) -> bool:
            try:
                if manager.store.get(hash) is None:
                    # 种子已删除: 让位任务清断点重新入队(下一轮规则执行时自然消亡)
                    logger.warning(f"规则[{rule_name}] {hash[:8]} | 校验轮询: 种子已删除")
                    manager.state.get("recheck_fails", {}).pop(hash, None)
                    if origin is not None:
                        origin.resume_index = None
                        tq.reschedule(origin, time.time())
                    return False
                if ctx.torrent.state_enum.is_checking:
                    return True  # 仍在校验中, 下一轮轮询
                if ctx.torrent.progress >= 1.0:
                    logger.info(f"规则[{rule_name}] {ctx.torrent.log_repr} | 校验成功")
                    if origin is not None:
                        origin.resume_cb = on_success
                        tq.resume(origin, time.time())  # resume_index 保留 -> 规则续跑后续动作
                    else:
                        on_success()  # 无触发任务(外部入口): 直接执行完成处理
                else:
                    fail_count = _bump_recheck_fail(manager, hash)
                    logger.warning(
                        f"规则[{rule_name}] {ctx.torrent.log_repr} | "
                        f"校验未通过(第{fail_count}次, progress={ctx.torrent.progress})"
                    )
                    if origin is not None:
                        origin.resume_index = None  # 失败: 清断点重走完整决策链(重新校验)
                        tq.reschedule(origin, time.time())
                return False
            except Exception as e:
                logger.warning(f"规则[{rule_name}] {hash[:8]} | 校验轮询异常: {e}")
                if origin is not None:
                    origin.resume_index = None
                    tq.reschedule(origin, time.time())
                return False

        task = Task(
            "check",
            "check-checking-result",
            hash=hash,
            interval=CHECK_RESULT_INTERVAL,
            handler=poll,
        )
        if not tq.add_check_task(task):
            return ActionResult.skip("该校验任务已在队列中")
        # 先登记成功再让位(顺序保证: 失败绝不 defer, 杜绝原任务永久让位)
        if origin is not None:
            tq.defer(origin)
        try:
            api.torrents_recheck(torrent_hashes=hash)
        except Exception as e:
            return ActionResult.fail(f"发送 recheck 失败: {e}")
        if origin is not None:
            # 任务队列驱动: 返回 pending, 规则记录断点中断, 由轮询任务 resume/reschedule 恢复
            return ActionResult.pending("full-checking 校验已提交")
        return ActionResult.ok("full-checking 校验已提交")

    def _wait_for_group_checking(self, ctx: RuleContext, members: list) -> Optional[ActionResult]:
        """决策链 1.5: 组内已有其它成员 full-checking 在途 -> 让位等待(组内共享同一物理文件, 并行全量校验只有重复 I/O)

        等待复用 full-checking 的 defer+轮询模式: 返回 pending(让位) + defer 触发任务, 等待任务
        轮询组内其它成员的 checking 态与在途登记, 清空后**清断点 + reschedule** 触发任务重走
        **完整决策链**(不能 resume 续跑: pending 断点指向 checking 动作之后, 会跳过重判) ——
        此时成功者已晋升 verified_references(决策链 2 命中有参考分流), 失败者由决策链 1.6 拦截。
        无任务驱动(外部入口)无法让位, 直接 skip; 超时强制恢复重判(防在途登记泄漏导致活锁)。
        """
        manager = ctx.manager
        hash = ctx.hash
        others = [h for h in members if h != hash]

        def others_checking() -> bool:
            inflight = manager.task_queue.active_check_hashes()
            by_hash = manager.store.by_hash
            return any(h in inflight or (h in by_hash and by_hash[h].state_enum.is_checking) for h in others)

        if not others or not others_checking():
            return None
        origin = getattr(ctx, "task", None)  # 触发本次校验的规则任务(任务队列驱动); 外部入口为 None
        if origin is None:
            return ActionResult.skip("组内有种子校验进行中(无任务驱动, 不等待)")
        tq = manager.task_queue
        rule_name = ctx.rule_name
        start = time.time()

        def revive():
            """恢复触发任务重走完整决策链(清断点, 与校验失败路径同语义)"""
            origin.resume_index = None
            tq.reschedule(origin, time.time())

        def wait_poll(task: Task, dry_run: bool) -> bool:
            try:
                if manager.store.get(hash) is None:
                    logger.warning(f"规则[{rule_name}] {hash[:8]} | 组内校验等待: 自身种子已删除")
                    return False
                if others_checking():
                    if time.time() - start > GROUP_CHECK_WAIT_LIMIT:
                        logger.warning(f"规则[{rule_name}] {hash[:8]} | 组内校验等待超时({GROUP_CHECK_WAIT_LIMIT:.0f}s), 强制恢复重判")
                        revive()
                        return False
                    return True  # 仍在等待, 下一轮轮询
                # 组内校验已清: 恢复触发任务重走决策链(成功者已晋升参考 / 失败者由决策链 1.6 拦截)
                logger.info(f"规则[{rule_name}] {hash[:8]} | 组内校验已完成, 恢复决策")
                revive()
                return False
            except Exception as e:
                logger.warning(f"规则[{rule_name}] {hash[:8]} | 组内校验等待异常: {e}")
                revive()
                return False

        # 等待任务用独立 kind + 普通入队(不经 add_check_task): 不占用 _active_checks 在途登记,
        # 否则多个等待成员会经由登记互相视为"校验中"而互等(仅超时才能解开)
        task = Task("check-wait", "check-group-wait", hash=hash, interval=CHECK_RESULT_INTERVAL, handler=wait_poll)
        tq.add_task(task)
        tq.defer(origin)
        logger.info(f"规则[{rule_name}] {ctx.torrent.log_repr} | 组内有种子校验进行中, 让位等待")
        return ActionResult.pending("等待同组种子校验完成")

    def _skip_on_group_check_failed(self, ctx: RuleContext, members: list) -> Optional[ActionResult]:
        """决策链 1.6: 组内其它成员校验失败且文件映射一致(共享同一物理数据) -> 校验结果必然相同, 直接跳过

        失败计数当日有效(次日重置), 数据不随重试改变; 文件映射不一致(组内大小有差异,
        校验的是不同数据)时不推断, 照常校验。
        """
        manager = ctx.manager
        hash = ctx.hash
        key = manager.store.member_to_key.get(hash)
        if key is None:
            return None
        sizes = manager.store.group_sizes.get(key, {})
        mine = sizes.get(hash)
        if not mine:
            return None
        for h in members:
            if h == hash or _recheck_fail_count(manager, h) <= 0:
                continue
            if sizes.get(h) == mine:
                return ActionResult.skip(f"同组种子 {h[:8]} 校验失败且文件映射一致(同一物理数据), 不再校验")
        return None
