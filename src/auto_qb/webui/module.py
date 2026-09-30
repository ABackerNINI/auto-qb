"""WebUIModule: WEB UI 表现层的模块契约封装(plan kernel-module-refactor P2 门面转正)

WebUIRuntime 仍是表现层门面(状态/判据/命令编排单点), 本模块只把它接入 Module 契约:
- start:      服务器启动(启用时) —— 密钥确定 + 服务线程拉起, 生命周期自 P2 起内聚 webui 包
              (run() 的 web 启动块退役, start_web_server 也不再直写 manager._web_token);
- stop:       进程关停路径只请求退出不等线程(与原 run() finally 口径一致);
- apply:      热重载语义(qbmanager._apply_web_config 迁入) —— 有差异即置脏 + 仅"监听身份"
              (enabled/host/port)变化才重启服务器(plan §4.3);
- loop hooks: 主循环五个语义调用中的四个经宿主按装配序调用 —— consume_commands /
              check_pending -> on_command_line, flush_views -> on_sync_line/on_task_line,
              advance_* -> on_task_line; flush_truths 的「刷新后落回执」次序语义留在内核
              (它必须每轮无条件跑 + 异常兜底路径也要跑, 不属于任何一条线的收尾)。

!门面对象经 manager.web **现取**(不缓存引用): manager.web 是单一真相属性, 测试与外围
  都可能整体替换单个门面 —— 模块只固定「从 manager 取 webui 门面」这一件事。
"""
import logging

from ..core.module import AppContext, ApplyResult, BaseModule

logger = logging.getLogger(__name__)


class WebUIModule(BaseModule):
    """webui 模块: sections 认领 web 段; 热重载有差异即置脏, 仅监听身份变化才重启服务器"""

    name = "webui"

    def __init__(self, manager) -> None:
        self._manager = manager

    def sections(self) -> tuple[str, ...]:
        return ("web", )

    # ---------- 生命周期 ----------

    def start(self, ctx: AppContext, dry_run: bool) -> None:
        web = self._manager.web
        if dry_run or not ctx.config.web.enabled:
            # dry-run 只观察不对外服务(原 run() 调用点口径); 未启用无操作
            return None
        if web.handle is not None:
            # start 幂等(黄金法则 1): 已在跑不重复拉起(与 LoggingModule 的 _configured 闸同款)
            return None
        web.start_server()

    def stop(self) -> None:
        self._manager.web.stop_server()

    # ---------- 热重载(_apply_web_config 语义迁入, plan P2) ----------

    def apply(self, old, new) -> ApplyResult:
        # ① 视图置脏: 视图含配置派生展示值(HR 标签模板如 ${required_seeding_time} 等),
        #    任何配置差异都可能改变展示内容 —— 有差异即置脏, 不限于本模块认领的 web 段
        #    (plan §4.3「webui.apply 不能完全短路」); 零差异保存无需重建
        if old is not new and old != new:
            self._manager.web.mark_dirty()
        # ② 服务器: 仅"监听身份"(enabled/host/port)变化才重启 —— 改个日志级别也拆服务器
        #    会白白放大端口竞态窗口; 重启必须"先停旧服务并等其线程退出"再启新(uvicorn 的
        #    should_exit 是异步生效的, 直接重启会与新服务竞抢端口 -> WinError 10048)
        old_web, new_web = old.web, new.web
        want = (bool(new_web.enabled), new_web.host, new_web.port)
        have = (bool(old_web.enabled), old_web.host, old_web.port)
        web = self._manager.web
        if want == have:
            if web.handle is not None:
                web.ensure_token()  # 鉴权每请求实时读 token, 即时刷新无需重启
            return ApplyResult(self.name)
        from . import stop_web_server

        if web.handle is not None:
            stop_web_server(web.handle)
            web.handle = None
        if new_web.enabled:
            web.start_server()
            return ApplyResult(self.name, "restarted")
        logger.info("WEB UI 已停止(web.enabled=false)")
        return ApplyResult(self.name, "stopped")

    # ---------- loop hooks(主循环按装配序调用) ----------

    def on_command_line(self) -> bool:
        """命令线: 消费控制命令 + 检查在途汇报确认; 返回本批是否改了 qB 种子状态(P0-5 判据)

        命令表分发/回执/写序号/自投递判据都在门面; SELF_POSTED_COMMANDS 不唤醒的语义
        也由门面 post_command 承担 —— 内核只取"是否改了状态"这一个结果。
        """
        web = self._manager.web
        changed = web.consume_commands()
        web.check_pending()
        return changed

    def on_sync_line(self, force: bool) -> None:
        """同步线收尾: 视图发布(「要不要重建」门控在门面, 内核不判表现层细节)"""
        self._manager.web.flush_views(force=force)

    def on_task_line(self, force: bool) -> None:
        """任务线收尾: 错误原因预取 -> 视图发布 -> 搜索索引推进(慢路径门控都在门面)

        错误原因预取的变更会显式置脏, 紧随其后的视图发布同轮可见(与预取放任务执行前
        的旧序相比, 同轮可见性不变、本轮任务造成的状态变化反而能被预取覆盖到)。
        """
        web = self._manager.web
        web.advance_error_reasons()
        web.flush_views(force=force)
        web.advance_search_index()
