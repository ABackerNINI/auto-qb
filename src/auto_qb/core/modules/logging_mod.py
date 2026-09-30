"""LoggingModule: 日志初始化与热重载重挂的模块化封装(plan kernel-module-refactor P1 契约样板)

统一挂载口(hot-reload-simplify 方向一)的第一个落地模块: 「怎么重挂日志」的知识从
apply_new_config 的 L1 分支迁入本模块 —— 每次热重载无条件 apply, logging 段整段相等
即短路返回(过度重启族的模块化防线: 改无关配置不再清掉在用 handler)。
"""
import logging
from typing import Optional

from ...infra.logging import setup_logging
from ..module import AppContext, ApplyResult, BaseModule

logger = logging.getLogger(__name__)


class LoggingModule(BaseModule):
    """日志模块: sections 认领 logging 段; 段相等短路, 变化才重挂 handler"""

    name = "logging"

    def __init__(self) -> None:
        self._ctx: Optional[AppContext] = None
        self._configured = False

    def sections(self) -> tuple[str, ...]:
        return ("logging", )

    def start(self, ctx: AppContext, dry_run: bool) -> None:
        """初始化日志(dry_run 不影响: 构造期即建是现口径, dry-run/导出模式同样要日志)"""
        self._ctx = ctx
        if self._configured:
            # start 幂等(黄金法则 1): 重复初始化会清掉在用 handler 并重复启动行,
            # 构造期接线(qbmanager.__init__)与 run() 的 start_all 双入口靠本闸合流
            return None
        self._configure(ctx.config.logging)

    def stop(self) -> None:
        return None  # 日志随进程终灭, 无可停(现行退出路径也不拆 handler)

    def apply(self, old, new) -> ApplyResult:
        if old.logging == new.logging:
            return ApplyResult(self.name)
        self._configure(new.logging)
        return ApplyResult(self.name, "remounted")

    def _configure(self, conf) -> None:
        setup_logging(conf.file, conf.level, conf.max_bytes, conf.format)
        self._configured = True
