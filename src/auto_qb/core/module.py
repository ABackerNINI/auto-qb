"""内核地基: 模块契约 / 应用上下文 / 模块宿主 / 事件总线(plan kernel-module-refactor P0)

目标模型(plan §3/§4): QbManager 瘦身为纯调度内核 —— 只知「何时」(节拍/相位/生命周期),
不知「何事」(标签/归组/规则语义); 业务各自成模块, 经统一契约被宿主编排。本文件是契约与
编排机制的**单点定义**: P0 立骨架(注册零个模块), P1 起装配清单(core/qbmanager)逐段
挂入模块 —— logging/notify 先行, 清单见 qbmanager 构造期(plan §3.3)。

三件东西的学名与出处(plan §2):
- AppContext        IoC 服务定位器变体 —— 服务(store/api/state)挂上下文, 模块经 ctx 取能力,
                    不依赖内核; 「宿主不知道模块是什么」的法理保障是依赖倒置。
- ModuleHost        微内核的插件注册表 + 生命周期编排(参照 Home Assistant 集成生命周期);
                    装配清单(注册顺序)是全项目单点, 顺序 = 相位内消费序 = 生命周期序。
- EventBus          调停者退化为 broker 的 Pub/Sub 形态 —— 相位广播按注册序同步调用
                    (参照 pluggy 注册序), 内核做路由不做解释。

P0 边界: 本文件不 import 任何业务包(rules/tags/...), 契约层不背实现依赖 —— 只允许
TYPE_CHECKING 下的类型标注。
"""
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Optional, Protocol, runtime_checkable

if TYPE_CHECKING:
    from ..config import Config
    from ..torrents import TorrentStore
    from ..webui.runtime import WebUIRuntime
    from .modules.notify_mod import NotifyModule
    from .modules.ops_mod import OpsModule
    from .modules.maintenance_mod import MaintenanceModule
    from .modules.tracker_mod import TrackerModule
    from .qbapi import QbApi
    from .state import StateService

logger = logging.getLogger(__name__)

# ---------- 应用上下文(IoC 服务定位器变体) ----------


class AppContext:
    """应用上下文: 内核构造, 能力服务挂其上, 模块经它取能力(plan §3.1)

    服务不是模块: 无生命周期、无启用开关、被内核与模块共同消费。
    - config 用属性对托管: 热重载整体替换 Config 对象(L0), ctx 是单一真相 ——
      manager.config 自 P0 起只是这里的委托, 测试整对象替换(mgr.config = ...)同样经此生效。
    - store / api / state 由 QbManager.__init__ 按构造序挂入(同一对象, manager 同名属性
      全部委托这里; P0 守阵断言 ctx.store is manager.store)。
    - notify(P1 起)是模块句柄而非服务: 托盘等外围运行形态经 ctx.notify 调模块**公开方法**
      (plan §3.2), 不再直写内核私有字段 —— 模块对外暴露面单点在这里。
    - task_queue(P3 起)挂入: 任务自注册(SpeedCurve/MaintenanceModule start/queue_rebuilt)
      要往当前队列入队 —— manager.task_queue 是这里的委托(L2 整体重建也经 setter 落回),
      模块侧现取 ctx.task_queue, 不缓存队列引用。
    - web(P3 起)挂入: speed_curve 模块经 ctx.web.set_traffic_view 服务方法推送流量快照,
      不再跨层直写 _traffic_view 字段(plan §5); manager.web 同为这里的委托(测试整对象
      替换 mgr.web 也经 setter 生效)。
    - trackers(P3 起, 决策点 D3)是模块句柄而非服务: tracker 匹配升 ctx.trackers.match(),
      规则上下文与全量轮重匹配都消费 —— 服务化避免事件回传的时序绕弯。
    - maintenance / ops(P4 起)是模块句柄: grouping 打标经 ctx.maintenance.add_tags(不
      import 兄弟模块); 规则动作与 WEB 命令经 ctx.ops 调危险操作层 —— 模块对外暴露面
      单点在 ctx(与 notify 同口径), ops 与 rules 的 import 单向化见 ops_mod 头注。
    """
    def __init__(self, config) -> None:
        self._config = config
        self.store: Optional["TorrentStore"] = None
        self.api: Optional["QbApi"] = None
        self.state: Optional["StateService"] = None
        self.notify: Optional["NotifyModule"] = None
        self.web: Optional["WebUIRuntime"] = None
        self.task_queue: Optional[Any] = None  # TaskQueue(内核机械, 不引入以保契约层零依赖)
        self.trackers: Optional["TrackerModule"] = None
        self.maintenance: Optional["MaintenanceModule"] = None
        self.ops: Optional["OpsModule"] = None

    @property
    def config(self):
        """当前生效配置(热重载时被整体替换; 消费方每轮现读, 不缓存对象引用)"""
        return self._config

    @config.setter
    def config(self, value) -> None:
        self._config = value


# ---------- 模块契约(plan §4.1) ----------


@dataclass(frozen=True)
class ApplyResult:
    """单模块热重载 apply 的回执(骨架): action 取 none / reloaded / restarted 等, 由模块自定义

    host.apply_all 汇总各模块回执供 apply_new_config 汇报(现返回 dict 的 actions 字段,
    P5 收口时对齐); P0 阶段无调用方, 结构先立。
    """

    module: str
    action: str = "none"
    detail: str = ""


@runtime_checkable
class Module(Protocol):
    """模块契约: 自治单元对宿主的全部义务(plan §4.1)

    - 模块之间不互相 import, 需要别人能力时经 ctx 取服务或经事件相位协作;
    - start/stop 必须幂等(重复调用无副作用, 黄金法则 1); stop 先叫停后 join
      (pitfalls/backend/concurrency.md 第 1 条);
    - apply 每次热重载**无条件**被调, 相关配置段整段相等才短路返回 —— 「统一挂载口」
      语义(hot-reload-simplify 方向一; hr.apply 已是此形态, 2026-09-29 修复即样板);
    - sections() 声明消费的配置顶层段, 守阵保证每段至少被一个模块认领(P6 上线)。

    loop hooks 是**可选**扩展点(不在 Protocol 内): on_command_line() -> bool /
    on_sync_line(force) / on_task_line(force), 有则被宿主按装配序调用, 无则跳过 ——
    用 getattr 探测, 故基类/实现不声明即不存在。
    """

    name: str

    def sections(self) -> tuple[str, ...]:
        ...

    def start(self, ctx: AppContext, dry_run: bool) -> None:
        ...

    def stop(self) -> None:
        ...

    def apply(self, old: "Config", new: "Config") -> ApplyResult:
        ...

    def subscribe(self, phases: "PhaseRegistry") -> None:
        ...


class BaseModule:
    """模块基类(可选样板): 子类必给 name, 其余动词默认无操作 —— 只减样板, 不引入隐藏行为

    !刻意**不**定义 loop hooks: 契约里它们是「有则调用, 无则跳过」, 基类若给默认实现
    等于把所有子类都变成 hook 提供者。需要 hook 的子类自己定义同名方法。
    """

    name: str = ""

    def sections(self) -> tuple[str, ...]:
        return ()

    def start(self, ctx: AppContext, dry_run: bool) -> None:
        return None

    def stop(self) -> None:
        return None

    def apply(self, old: "Config", new: "Config") -> ApplyResult:
        return ApplyResult(self.name)

    def subscribe(self, phases: "PhaseRegistry") -> None:
        return None


# ---------- 事件总线(相位广播, plan §4.2) ----------

PhaseHandler = Callable[["PhaseEvent"], Any]


@dataclass(frozen=True)
class PhaseEvent:
    """相位事件: phase 是 §4.2 相位表里的键, payload 由发射方定义(删除前快照等, P5 定稿)"""

    phase: str
    payload: dict = field(default_factory=dict)


@runtime_checkable
class PhaseRegistry(Protocol):
    """相位认领口: Module.subscribe(phases) 拿到的就是它(EventBus 实现该协议)"""
    def on(self, phase: str, handler: PhaseHandler) -> None:
        ...


class EventBus:
    """刷新管线相位广播(骨架): 模块认领相位, 内核 emit 按注册序同步调用(plan §4.2)

    - 相位清单与次序 = 现 _refresh_torrents 调用顺序的忠实编码(transitions 先于规则事件、
      事件分派先于内置动作……), 不是重设计; P5 收口时 _refresh_torrents 的「内核点名」
      改为 emit, 本骨架即生效点。
    - suppress: 热重载首轮全量重建的 added 事件重放保护 —— 总线级开关, 置位期间 emit
      直接跳过(语义等价现 manager._suppress_events, P5 收口时迁移到此处)。
    - 分发是**同步**的: 相位消费都在主循环线程内(单一写线程, 黄金法则 5), 无锁。
    """
    def __init__(self) -> None:
        self._handlers: dict[str, list[PhaseHandler]] = {}
        self._suppressed = False

    def on(self, phase: str, handler: PhaseHandler) -> None:
        """登记相位订阅者(注册序即调用序; 同名相位重复登记合法, 依次调用)"""
        self._handlers.setdefault(phase, []).append(handler)

    def emit(self, phase: str, payload: Optional[dict] = None) -> int:
        """广播相位: 按注册序同步调用订阅者, 返回实际触发的订阅者数(测试/日志用)

        抑制期返回 0 且不调用任何订阅者 —— 热重载首轮全量重建的 added 重放保护语义。
        """
        if self._suppressed:
            return 0
        n = 0
        event = PhaseEvent(phase, payload or {})
        for handler in tuple(self._handlers.get(phase, ())):  # 快照: 订阅者内再登记也安全
            handler(event)
            n += 1
        return n

    @property
    def suppressed(self) -> bool:
        return self._suppressed

    def set_suppressed(self, value: bool) -> None:
        """置位/解除总线级抑制(热重载首轮: 置位 -> 全量重建一轮 -> 解除)"""
        self._suppressed = bool(value)


# ---------- 模块宿主(注册表 + 生命周期编排, plan §3.1) ----------


class ModuleHost:
    """模块宿主: 注册表 + 生命周期编排 —— 内核唯一「知道模块名字」的地方是装配清单本身

    - 注册即装配: modules 列表顺序 = 相位内消费序 = 生命周期序(plan §3.3), 全项目单点;
    - register 时回调 module.subscribe(events) —— 相位认领发生在装配点, 宿主不追认;
    - start_all / apply_all 按装配序, stop_all 逆序(后建的先拆);
    - loop hooks 按「有则调用无则跳过」的 getattr 探测执行(见 Module 契约注释);
    - P0 守阵期曾注册零模块锁编排语义; P1 起装配清单挂入真实模块(守阵同时锁两者)。
    """
    def __init__(self, ctx: AppContext, events: EventBus) -> None:
        self._ctx = ctx
        self._events = events
        self._modules: list[Module] = []

    def register(self, module: Module) -> None:
        """装配一个模块(幂等性由调用方保证: 同一模块注册两次按 bug 处理, 直接 fail-fast)"""
        name = getattr(module, "name", "")
        if not name:
            raise ValueError("模块必须有非空 name(QbManager 装配清单)")
        if self.get(name) is not None:
            raise ValueError(f"模块名重复: {name}")
        self._modules.append(module)
        module.subscribe(self._events)

    def modules(self) -> tuple[Module, ...]:
        """已装配模块(装配序, 只读视图)"""
        return tuple(self._modules)

    def get(self, name: str) -> Optional[Module]:
        for m in self._modules:
            if m.name == name:
                return m
        return None

    # ---------- 生命周期编排 ----------

    def start_all(self, dry_run: bool) -> None:
        """按装配序启用全部模块; dry_run 全量透传(模块自判「只观察不落盘」口径)"""
        for m in self._modules:
            m.start(self._ctx, dry_run)

    def stop_all(self) -> None:
        """按装配**逆序**停用全部模块(后建的先拆); stop 自身幂等, 重复调用安全"""
        for m in reversed(self._modules):
            m.stop()

    def apply_all(self, old: "Config", new: "Config") -> list[ApplyResult]:
        """热重载广播: 每模块**无条件** apply(自判整段短路), 返回各模块回执(装配序)

        这是 hot-reload-simplify 方向一的落地形态: 级别分派表退役, 消费方自认领。
        """
        return [m.apply(old, new) for m in self._modules]

    # ---------- loop hooks(可选, 按装配序) ----------

    def run_command_line(self) -> bool:
        """命令线 hook: 各模块消费控制命令; 任一报告「本批改了 qB 状态」即 True"""
        changed = False
        for m in self._modules:
            hook = getattr(m, "on_command_line", None)
            if hook is not None:
                changed = bool(hook()) or changed
        return changed

    def run_sync_line(self, force: bool) -> None:
        """同步线收尾 hook(webui: 视图发布)"""
        for m in self._modules:
            hook = getattr(m, "on_sync_line", None)
            if hook is not None:
                hook(force)

    def run_task_line(self, force: bool) -> None:
        """任务线收尾 hook(webui: 错误原因预取 / 搜索索引)"""
        for m in self._modules:
            hook = getattr(m, "on_task_line", None)
            if hook is not None:
                hook(force)


__all__ = [
    "AppContext",
    "ApplyResult",
    "Module",
    "BaseModule",
    "PhaseEvent",
    "PhaseHandler",
    "PhaseRegistry",
    "EventBus",
    "ModuleHost",
]
