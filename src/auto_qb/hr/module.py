"""HrModule: HR 在线核实运行时的模块契约封装(plan kernel-module-refactor P2 门面转正)

HrRuntime 已是目标形态(端点 + 取数线程 + 只读视图 + apply 自判短路, 2026-09-29 修复即
统一挂载口的样板), 本模块只做契约对齐: start/stop 透传, apply 把整份新旧配置降为旧
hr_check 段传给门面 —— 门面内部的短路/重建判据(服务在 + 全局段与派生站点表相等)不变。

!apply 每次热重载都会被调, **不限 L1**(plan §4.3; 2026-09-29 实报「取数线程未启动」):
  站点接入(hr_check.sites / trackers.X.hr_check)是 L0 级变更, 「启动时无站点、热接入
  第一个站点」全靠 apply 补启动取数线程与端点 —— 短路由门面自判, 无关配置的保存不会
  重启取数线程。

!门面对象经 manager.hr **现取**(不缓存引用): manager.hr 是单一真相属性(与 WebUIModule
  同款)。sections 同时认领 hr_check 与 trackers —— 站点绑定派生自 trackers.X.hr_check,
  只认领 hr_check 会漏掉绑定结果变化(entry 守阵 P6 上线时按认领表核对)。
"""
from ..core.module import AppContext, ApplyResult, BaseModule


class HrModule(BaseModule):
    """hr 模块: sections 认领 hr_check/trackers; 短路/重建判据单点在 HrRuntime.apply"""

    name = "hr"

    def __init__(self, manager) -> None:
        self._manager = manager

    def sections(self) -> tuple[str, ...]:
        return ("hr_check", "trackers")

    def start(self, ctx: AppContext, dry_run: bool) -> None:
        if dry_run:
            # dry-run 只打日志不建端点/线程(原 run() 调用点口径); 未启用由 start 内部判
            return None
        self._manager.hr.start()

    def stop(self) -> None:
        self._manager.hr.stop()

    def apply(self, old, new) -> ApplyResult:
        self._manager.hr.apply(old.hr_check)
        return ApplyResult(self.name)
