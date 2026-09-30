"""NotifyModule: 主动通知 handler 挂载 / 热重载重挂 / 托盘会话开关的模块化封装(plan P1)

三个挂载触发源收拢到本模块: run() 启动挂载(start, 配置驱动) / 热重载重挂(apply, 整段
短路) / 托盘会话级开关(set_enabled, force 挂载, 重启后回到配置状态)。托盘经
ctx.notify 调这里的公开方法, 不再直写 manager._notify_handler 私有字段(plan §3.2,
外围绕过边界直写内核私有面清零)。
"""
import logging
from typing import Optional

from ...infra.notify import NotifyHandler, setup_notify
from ..module import AppContext, ApplyResult, BaseModule

logger = logging.getLogger(__name__)


class NotifyModule(BaseModule):
    """通知模块: sections 认领 notify 段; 段相等短路, 变化才重挂 handler"""

    name = "notify"

    def __init__(self, ctx: AppContext) -> None:
        # ctx 构造期注入: 托盘的会话级开关(set_enabled)可能早于 run() 的 start 到达,
        # 而 force 挂载要读现行 config.notify —— 不等 start 才拿 ctx
        self._ctx = ctx
        self._handler: Optional[NotifyHandler] = None

    def sections(self) -> tuple[str, ...]:
        return ("notify", )

    def start(self, ctx: AppContext, dry_run: bool) -> None:
        if dry_run or self._handler is not None:
            # dry-run 只打日志不挂通知(原 run() 调用点口径); 已挂载则幂等跳过(黄金法则 1)
            return None
        self._mount(ctx.config.notify, force=False)

    def stop(self) -> None:
        return None  # 派发线程是 daemon 随进程退出; 现行退出路径也不摘 handler, 保持

    def apply(self, old, new) -> ApplyResult:
        if old.notify == new.notify:
            return ApplyResult(self.name)
        # 重挂保留原 L1 分支语义: 先摘旧 handler, force=True 重挂(挂载即 enabled=True,
        # 与托盘会话开关同源 —— force 对配置未启用也挂, 会话级, 重启后回到配置状态)
        self._unmount()
        self._mount(new.notify, force=True)
        return ApplyResult(self.name, "remounted")

    # ---------- 托盘/外围公开口(plan §3.2: ctx.notify.*) ----------

    def enabled_state(self) -> Optional[bool]:
        """None=未挂载(配置未启用且未会话挂载); True/False=handler 热开关状态"""
        return None if self._handler is None else self._handler.enabled

    def is_enabled(self) -> bool:
        """是否在推通知(未挂载 = False)"""
        return self._handler is not None and self._handler.enabled

    def set_enabled(self, on: bool) -> None:
        """托盘开关: 已挂载 -> 翻转热开关; 未挂载且 on=True -> 会话级 force 挂载

        平台不支持时 setup_notify 抛 AutoQbError 原样上抛(UI 弹窗提示, 开关由调用方回弹)。
        """
        if self._handler is not None:
            self._handler.enabled = bool(on)
            return
        if not on:
            return None
        self._mount(self._ctx.config.notify, force=True)

    # ---------- 内部 ----------

    def _mount(self, config, force: bool) -> None:
        self._handler = setup_notify(config, force=force)

    def _unmount(self) -> None:
        if self._handler is not None:
            logging.getLogger("auto_qb").removeHandler(self._handler)
            self._handler = None
