"""full-checking 执行与组内校验串行化(FullCheckingMixin)

包含: 校验常量(轮询间隔/失败上限/启动宽限/等待上限)、当日失败计数 helper、
full-checking 提交+轮询(_execute_full_checking)、组内串行闸门
(_wait_for_group_checking, 决策链 1.5)与失败推断闸门
(_skip_on_group_check_failed, 决策链 1.6, 含假失败自愈)。
"""
import logging
import time
from datetime import date
from typing import Optional

from ...core.taskqueue import FINISHED, REQUEUE, Task
from ..base import ActionResult, RuleContext

logger = logging.getLogger(__name__)

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
    manager.save_state()  # 冷却计数即时落盘: 丢了会对同一损坏文件多试 recheck(当日上限闸门失效一次); 上界 3 次/日/种, 频率天然低
    return rec["count"]


class FullCheckingMixin:
    """full-checking 执行与组内校验串行化: 由 CheckAction 组合, 依赖 self 的
    basic_check/with_reference/without_reference(checking.py 解析)"""
    def _execute_full_checking(self, ctx: RuleContext, segment: dict):
        """full-checking: 先登记校验结果轮询子任务(快速队列, interval=CHECK_RESULT_INTERVAL), 再同步发送 recheck

        触发流程:
          1) 先 add_task 登记轮询子任务(在途去重: 已在途则 skip, 不重复发 recheck),
             再同步发送 torrents_recheck(API 同步返回, 校验后台异步); 发送失败返回 fail
             (不返回 pending, 规则不留断点; 已登记的子任务下轮见「未发送」标记直接消亡,
             释放在途登记 —— 发送失败不得遗留等待中的轮询)
          2) 发送成功动作返回 pending(规则断点), 规则任务本轮不重入队(_handle_rule 检测断点) ——
             origin 的恢复完全由轮询子任务负责: 队列对"暂停/恢复"无感知
          3) 轮询子任务每 CHECK_RESULT_INTERVAL 秒检查 store 快照, 退出 checking* 即完成:
             成功(progress>=1) -> on_success()(晋升 verified_references + auto_start) +
               add_task(origin, keep_progress=True) 重新入队(断点续跑后续动作)
             失败(曾见 checking 后落回未完成, 或 CHECK_START_GIVEUP 宽限耗尽仍未开检)/
               异常/种子删除 -> add_task(origin)(默认重置, 重走完整决策链; 种子删除时由
               origin 的删除守卫判死); 宽限窗口内「未见 checking」的样本只 REQUEUE 不计败
               (首样本竞态修复: 不把快照滞后当校验失败)
          4) 子任务经 add_task 自动登记在途(_active_checks, 决策链 1.5 组内串行化依赖),
             消亡时释放
        """
        manager = ctx.manager
        hash = ctx.hash

        # 失败冷却: 当日连续校验失败达上限后不再重试(防损坏文件导致 recheck 死循环), 次日重置
        # (INFO 提级: 这是在拒绝校验, 生产 INFO 日志下必须可见 —— 2026-09-25 排障时 skip 全是 DEBUG 盲区)
        if _recheck_fail_count(manager, hash) >= RECHECK_FAIL_LIMIT:
            logger.info(f"规则[{ctx.rule_name}] {ctx.torrent.log_repr} | 校验连续失败 {RECHECK_FAIL_LIMIT} 次, 今日不再重试")
            return ActionResult.skip(f"校验连续失败 {RECHECK_FAIL_LIMIT} 次, 今日不再重试")

        tq = ctx.manager.task_queue
        origin = getattr(ctx, "task", None)  # 触发本次校验的规则任务(任务队列驱动); 外部入口为 None
        rule_name = ctx.rule_name
        api = ctx.api
        auto_start = segment["auto_start"]

        def on_success():
            """校验成功完成处理: 晋升参考(仅内存, 不写 state_file) + auto_start
            执行历史由 origin 重新入队后的续跑(Rule.process 断点续跑)统一记录
            """
            manager.store.verified_references.add(hash)
            manager.state.get("recheck_fails", {}).pop(hash, None)  # 校验通过: 清除失败冷却计数
            if auto_start and not ctx.dry_run:
                api.torrents_start(torrent_hashes=hash)
                logger.info(f"规则[{rule_name}] {ctx.torrent.log_repr} | 校验成功自动开始")

        def poll(task: Task, dry_run: bool) -> bool:
            nonlocal seen_checking
            try:
                if not submitted:
                    return FINISHED  # recheck 发送失败: 登记的轮询直接消亡(释放在途登记)
                if manager.store.get(hash) is None:
                    # 种子已删除: 默认重置重新入队 origin, 由其删除守卫(_handle_rule)判死
                    logger.warning(f"规则[{rule_name}] {hash[:8]} | 校验轮询: 种子已删除")
                    manager.state.get("recheck_fails", {}).pop(hash, None)
                    if origin is not None:
                        tq.add_task(origin)
                    return FINISHED
                if ctx.torrent.state_enum.is_checking:
                    seen_checking = True
                    return REQUEUE  # 仍在校验中, 下一轮轮询
                if ctx.torrent.progress >= 1.0:
                    logger.info(f"规则[{rule_name}] {ctx.torrent.log_repr} | 校验成功")
                    on_success()
                    if origin is not None:
                        tq.add_task(origin, keep_progress=True)  # 显式保存进度: 断点续跑后续动作
                elif seen_checking:
                    # 曾见 checking 后落回未完成: 真实校验未通过
                    fail_count = _bump_recheck_fail(manager, hash)
                    logger.warning(
                        f"规则[{rule_name}] {ctx.torrent.log_repr} | "
                        f"校验未通过(第{fail_count}次, progress={ctx.torrent.progress})"
                    )
                    if origin is not None:
                        tq.add_task(origin)  # 默认重置: 重走完整决策链(重新校验)
                elif time.time() - submitted_at >= CHECK_START_GIVEUP:
                    # 宽限耗尽仍未见校验启动: 判败防轮询活锁(qB 重启丢请求等极端情形);
                    # 判败后 origin 重走决策链会重新提交, 请求恢复生效后自然续上
                    fail_count = _bump_recheck_fail(manager, hash)
                    logger.warning(
                        f"规则[{rule_name}] {ctx.torrent.log_repr} | "
                        f"校验启动超时({CHECK_START_GIVEUP:.0f}s 未见 checking, "
                        f"第{fail_count}次, progress={ctx.torrent.progress})"
                    )
                    if origin is not None:
                        tq.add_task(origin)  # 默认重置: 重走完整决策链(重新校验)
                else:
                    # 未见 checking 且宽限未耗尽: recheck 尚未被 qB 应用(异步应用 + 快照滞后)
                    # 或排队未开检 —— 继续轮询, 不计失败(首样本竞态修复)
                    return REQUEUE
                return FINISHED  # 轮询子任务消亡(释放在途登记)
            except Exception as e:
                logger.warning(f"规则[{rule_name}] {hash[:8]} | 校验轮询异常: {e}")
                if origin is not None:
                    tq.add_task(origin)  # 默认重置: 重走完整决策链
                return FINISHED

        submitted = False  # recheck 是否发送成功(先登记后发送; 失败时轮询子任务据此消亡)
        submitted_at = time.time()  # 校验启动宽限窗口起点(recheck 发送成功时刻)
        seen_checking = False  # 本轮询周期内是否观察到过 checking 态(失败判定前提)

        task = Task(
            "check",
            "check-checking-result",
            hash=hash,
            store=manager.store,
            interval=CHECK_RESULT_INTERVAL,
            handler=poll,
        )
        if not tq.add_task(task):
            return ActionResult.skip("该校验任务已在队列中")
        try:
            api.torrents_recheck(torrent_hashes=hash)
            submitted = True
            submitted_at = time.time()
        except Exception as e:
            return ActionResult.fail(f"发送 recheck 失败: {e}")
        logger.info(f"规则[{rule_name}] {ctx.torrent.log_repr} | full-checking 校验已提交")
        # pending: 规则记录断点, 规则任务本轮不重入队 —— 恢复由轮询子任务负责
        return ActionResult.pending("full-checking 校验已提交")

    def _wait_for_group_checking(self, ctx: RuleContext, members: list) -> Optional[ActionResult]:
        """决策链 1.5: 组内已有其它成员 full-checking 在途 -> 推迟执行(组内共享同一物理文件, 并行全量校验只有重复 I/O)

        等待与 full-checking 同模式: 返回 pending(规则断点, 规则任务本轮不重入队), 等待子任务
        轮询组内其它成员的 checking 态与在途登记, 清空后 add_task(origin) 默认重置重走完整
        决策链 —— 此时成功者已晋升 verified_references(决策链 2 命中有参考分流), 失败者由
        决策链 1.6 拦截。无任务驱动(外部入口)无法推迟, 直接 skip; 超时强制恢复重判
        (防在途登记泄漏导致活锁)。
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
            """恢复触发任务重走完整决策链(add_task 默认重置)"""
            tq.add_task(origin)

        def wait_poll(task: Task, dry_run: bool) -> bool:
            try:
                if manager.store.get(hash) is None:
                    # 种子已删除: 默认重置重新入队 origin, 由其删除守卫(_handle_rule)判死
                    logger.warning(f"规则[{rule_name}] {hash[:8]} | 组内校验等待: 自身种子已删除")
                    tq.add_task(origin)
                    return FINISHED
                if others_checking():
                    if time.time() - start > GROUP_CHECK_WAIT_LIMIT:
                        logger.warning(f"规则[{rule_name}] {hash[:8]} | 组内校验等待超时({GROUP_CHECK_WAIT_LIMIT:.0f}s), 强制恢复重判")
                        revive()
                        return FINISHED
                    return REQUEUE  # 仍在等待, 下一轮轮询
                # 组内校验已清: 恢复触发任务重走决策链(成功者已晋升参考 / 失败者由决策链 1.6 拦截)
                logger.debug(f"规则[{rule_name}] {hash[:8]} | 组内校验已完成, 恢复决策")
                revive()
                return FINISHED
            except Exception as e:
                logger.warning(f"规则[{rule_name}] {hash[:8]} | 组内校验等待异常: {e}")
                revive()
                return FINISHED

        # 等待任务用独立 kind(check-wait): 不占用 _active_checks 在途登记,
        # 否则多个等待成员会经由登记互相视为"校验中"而互等(仅超时才能解开)
        task = Task(
            "check-wait",
            "check-group-wait",
            hash=hash,
            store=manager.store,
            interval=CHECK_RESULT_INTERVAL,
            handler=wait_poll
        )
        tq.add_task(task)
        logger.debug(f"规则[{rule_name}] {ctx.torrent.log_repr} | 组内有种子校验进行中, 推迟等待")
        return ActionResult.pending("等待同组种子校验完成")

    def _skip_on_group_check_failed(self, ctx: RuleContext, members: list) -> Optional[ActionResult]:
        """决策链 1.6: 组内其它成员校验失败且文件映射一致(共享同一物理数据) -> 校验结果必然相同, 直接跳过

        失败计数当日有效(次日重置), 数据不随重试改变; 文件映射不一致(组内大小有差异,
        校验的是不同数据)时不推断, 照常校验。
        假失败自愈(2026-09-25 误判故障解毒): 记录指向的成员已完成(progress>=1)或已不在库
        -> 该「失败」与数据无关(误判/陈旧残留), 清除记录且不参与推断(记录只在成功/删除路径
        清除的话, 误判记录会毒化全组直至次日)。
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
            rec = manager.store.get(h)
            if rec is None or rec.progress >= 1.0:
                manager.state.get("recheck_fails", {}).pop(h, None)
                continue
            if sizes.get(h) == mine:
                # INFO 提级: 生产 INFO 日志下必须能看到「谁因推断被拒检」(2026-09-25 排障盲区)
                logger.info(f"规则[{ctx.rule_name}] {ctx.torrent.log_repr} | "
                            f"同组种子 {h[:8]} 校验失败且文件映射一致(同一物理数据), 不再校验")
                return ActionResult.skip(f"同组种子 {h[:8]} 校验失败且文件映射一致(同一物理数据), 不再校验")
        return None
