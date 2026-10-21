"""skip-checking 委托入口(SkipCheckingMixin)

跳检四阶段执行体(前置闸门/导出准备/删除-重加/收尾, 含 R2 实时复核与备份/清理)已迁入
ops 模块(core/modules/ops_mod.OpsModule, rules → ops ← web, plan 26-09-30-0109 P2'),
本模块只保留 CheckAction 决策链 4 的委托入口 —— 风险控制语义(部分下载禁止/同日去重/
备份先于删除等)随执行体迁入 ops 层 docstring, 规则侧行为等价不变。
"""
import logging

from ..base import RuleContext

logger = logging.getLogger(__name__)


class SkipCheckingMixin:
    """skip-checking 委托入口: 由 CheckAction 组合, 执行体在 ctx.ops.skip_check(ops 层)"""
    def _execute_skip_checking(self, ctx: RuleContext, segment: dict, has_reference: bool):
        """辅种跳检: ctx 字段 -> ops 异步入口, 一行委托(闸门/备份/重加等语义全部在 ops 层)

        has_reference 只用于规则侧「无参考跳检(高风险)」告警 —— 该告警是规则语义,
        WEB 源不产生(前端危险确认框已承担风险告知), 由 ops 层按 source 区分。

        异步契约(计划 26-10-21-1857 S4): ops 只做前置与建 job, 返回 pending —— 规则任务记录
        断点并让出队列; 相位由主循环微步线推进, 终态由 `OpsModule._skip_settle` 把 origin
        重新入队(成功 keep_progress 续跑后续动作 / 失败默认重置重走决策链, 与 recheck 同构)。
        """
        return ctx.manager.ctx.ops.skip_submit(
            ctx.hash,
            source="rule",
            auto_start=segment["auto_start"],
            has_reference=has_reference,
            origin=getattr(ctx, "task", None),
        )
