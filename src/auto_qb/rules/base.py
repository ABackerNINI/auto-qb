"""rules 框架基础: 动作结果, 条件/动作基类, 规则上下文, Rule 插件"""
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from qbittorrentapi import Client

from . import registry
from ..infra import utils
from ..torrents import TorrentRecord
from ..config import Config, ConfigError
from ..config.compat import normalize_action_entry
# from ..qbmanager import QbManager
from ..core.qbapi import QbApi

logger = logging.getLogger(__name__)

# 条件求值出错日志的节流窗口(秒): 同规则同原因在此窗口内只报一次 ERROR
_COND_ERR_THROTTLE = 300.0

# process 返回契约(W1 收口, plan 26-11-01-0106 G1/G12): 单值 verdict, 由引擎
# (core/modules/rules_mod._run_rule)显式消费 —— 记 DEBUG 结论供排障; W2 起按 error 档
# 驱动 per-step 错误语义, W4 起进 per-run trace。旧 (handled, stop) 元组的 stop 档是死配置
# (唯一调用点整体丢弃返回值), 已随 stop_following_rules_if 退役一并删除。
VERDICT_NO_MATCH = "no_match"  # 条件不满足(含种子已删): 本轮未执行
VERDICT_ERROR = "error"  # 条件求值出错: 本条规则本轮跳过, 不影响其它规则
VERDICT_DEDUPED = "deduped"  # execute_once/cooldown 去重拦下
VERDICT_NO_OP = "no_op"  # 条件满足且未被去重, 但无动作产生效果(空动作表/全 skip)
VERDICT_PENDING = "pending"  # 动作等待异步完成: 断点已记录, 本轮中断待恢复
VERDICT_EXECUTED = "executed"  # 本轮执行了动作(成功/失败均计; 续跑完成同)


class ActionResult:
    """动作执行结果: success / failed / skipped / pending

    pending: 动作已提交等待异步完成(如 full-checking 校验), 规则执行中断待恢复;
    仅任务队列驱动时有效(规则任务记录断点 resume_index), 外部入口视为成功继续。
    """
    def __init__(self, status: str = "success", message: str = ""):
        self.status = status
        self.message = message

    @classmethod
    def ok(cls, message: str = "") -> "ActionResult":
        return cls("success", message)

    @classmethod
    def fail(cls, message: str = "") -> "ActionResult":
        return cls("failed", message)

    @classmethod
    def skip(cls, message: str = "") -> "ActionResult":
        return cls("skipped", message)

    @classmethod
    def pending(cls, message: str = "") -> "ActionResult":
        return cls("pending", message)

    @property
    def is_ok(self) -> bool:
        return self.status == "success"

    @property
    def is_failed(self) -> bool:
        return self.status == "failed"

    @property
    def is_skipped(self) -> bool:
        return self.status == "skipped"

    @property
    def is_pending(self) -> bool:
        return self.status == "pending"

    def __repr__(self) -> str:
        return f"ActionResult({self.status}, {self.message})"


class BaseCondition(ABC):
    """条件插件基类: 子类定义 name 并实现 match(ctx)"""

    name: str = ""

    def __init__(self, spec: Any):
        self.spec = spec

    @abstractmethod
    def match(self, ctx: "RuleContext") -> bool:
        ...


class BaseAction(ABC):
    """动作插件基类: 子类定义 name 并实现 execute(ctx)"""

    name: str = ""

    def __init__(self, spec: Any):
        self.spec = spec

    @abstractmethod
    def execute(self, ctx: "RuleContext") -> ActionResult:
        ...


@dataclass
class RuleContext:
    """一次规则处理上下文, 惰性缓存 tracker/文件等数据"""

    manager: Any  # QbManager(规则调度/状态持久化/任务队列)
    client: Client  # qbittorrent Client(兼容入口: 外部传入种子时直接拉取)
    config: Config
    hash: str
    dry_run: bool
    rule_name: str = ""
    task: Any = None  # 触发本次规则执行的任务(任务队列驱动); process_torrent 外部入口为 None
    snapshot: Any = None  # on_torrent_deleted 删除前快照副本(TorrentRecord); 种子已从 store 移除时供 ctx.torrent 读取

    _tracker_urls: Optional[List[str]] = field(default=None)
    _tracker_confs: Optional[List] = field(default=None)
    _files: Optional[List] = field(default=None)

    # 表达式取值的昂贵值缓存(见 rules/expr/eval.py): 生命周期 = 本次规则执行,
    # 保证同一轮内 freespace(path) 只查一次、sys.now 等时变值前后一致。
    expr_cache: Dict[str, Any] = field(default_factory=dict)

    @property
    def api(self) -> QbApi | Client:
        """qB API Facade: manager.api 已绑定客户端时优先; 否则(外部传入种子/测试)退化到 client"""
        api = getattr(self.manager, "api", None)
        if api is not None:
            return api
        return self.client

    @property
    def torrent(self) -> TorrentRecord | None:
        """规则处理的种子记录: 实时 store 优先; 种子已从客户端移除(storage 已删, on_torrent_deleted)
        时回退到删除前快照副本(snapshot), 供只读动作(print_torrent_details)留档"""
        rec = self.manager.store.get(self.hash)
        return rec if rec is not None else self.snapshot


class Rule:
    """一条规则插件: 条件列表 + 动作列表 + 执行语义, 由 QbManager 统一加载与调度"""
    def __init__(self, name: str, spec: dict, manager: Any):
        self.name = name
        self.spec = spec
        self.manager = manager
        self.enabled = utils.parse_bool(spec.get("enabled", True))
        # 触发时机: interval(默认, 周期轮询) / on_torrent_added / on_torrent_deleted /
        # on_torrent_state_enum_changed / on_torrent_field_changed(事件触发, 一次性分派)。
        # 取值合法性由 config 校验保证, 此处不自查。
        self.trigger = str(spec.get("trigger", "interval"))
        # 监听字段(on_torrent_field_changed 专用; 出现在其它 trigger 下 config 校验已拒绝):
        # 非空字符串元组, 取值域 FIELD_WATCH_ALLOWED(v1: tags / category), 合法性同样信任校验。
        self.watch_fields = tuple(str(f).strip() for f in (spec.get("watch_fields") or []) if str(f).strip())
        self.interval = utils.parse_time(str(spec.get("interval", "0S")))  # 规则扫描间隔, 0 = 每轮
        self.execute_once = str(spec.get("execute_once", "never"))
        self.cooldown = utils.parse_time(str(spec.get("cooldown", "0S")))
        # 条件求值出错日志的节流状态(见 _log_condition_error)
        self._cond_err_key: Optional[str] = None
        self._cond_err_ts: float = 0.0

        self.conditions = []
        for cond_spec in spec.get("conditions") or []:
            if not isinstance(cond_spec, dict):
                continue
            try:
                self.conditions.append(registry.create_condition(cond_spec))
            except Exception as e:
                raise ConfigError(f"规则 {self.name}: 条件 {cond_spec}: {e}") from e

        # 解析动作序列(规范化形态 {type, params}, plan 26-11-01-0106 §3.2 W2-A): 载入链
        # (load_config -> normalize_legacy_rules)已把旧扁平单键 dict 翻译成规范形; 这里对每项
        # 再过一次单点漏斗(config.compat.normalize_action_entry, 幂等) —— 引擎只认规范形,
        # 没有「读 legacy 键」的第二语义分支, 兼容层唯一容身在 config/compat.py。
        # 伪动作 ignore_next_action_error 已退役(D1): 载入层(rules_mod.load_rules)识别后
        # 转未启用并在内存副本里剔除, 引擎不再消费 —— 绕过载入层直接构造 Rule 遇伪动作
        # 按未知动作 ConfigError。
        self.actions = []
        for act_spec in spec.get("actions") or []:
            if not isinstance(act_spec, dict):
                continue
            act = normalize_action_entry(act_spec)
            name, value = act.get("type"), act.get("params")
            try:
                self.actions.append(registry.create_action(name, value))
            except Exception as e:
                raise ConfigError(f"规则 {self.name}: 动作 {name}: {e}") from e

        # 高风险动作静态提醒: reannounce 高频触发会被 tracker 封号, 未配去重时给出告警
        # (动作内另有最小间隔运行时保护兜底)
        if any(a.name == "reannounce" for a in self.actions) and self.execute_once == "never" and self.cooldown <= 0:
            logger.error(f"规则[{self.name}] 含 reannounce 动作但未配置 execute_once/cooldown, 高频触发有封号风险")

    def matches(self, ctx: RuleContext) -> bool:
        """所有条件必须全部满足(AND)"""
        return all(c.match(ctx) for c in self.conditions)

    def process(self, ctx: RuleContext) -> str:
        """
        处理一个种子, 返回单值 verdict(模块级 VERDICT_* 常量, 消费方见常量区注释)。

        断点契约(与 taskqueue 的默认重置语义配合):
        - 读:   进入时只读 task.resume_index 判定续跑(不清零)
        - 写:   动作返回 pending 时记录断点并中断, 由校验轮询子任务按结果重新入队
        - 清:   正常完成时清零; 异常路径不清零 —— 由 taskqueue 收尾默认重置兜底(下轮从头)
        """
        if ctx.torrent is None:
            return VERDICT_NO_MATCH

        ctx.rule_name = self.name
        task = ctx.task

        # 断点只读: 有断点 -> 续跑(跳过条件评估与去重)
        resume_index = task.resume_index if task is not None else None
        fresh = resume_index is None

        if fresh:
            try:
                matched = self.matches(ctx)
            except Exception as e:
                # 条件求值出错: 本条规则本轮跳过, 其它规则照常(per-rule 任务模型里不存在
                # 「后续规则」链 —— 旧日志「停止后续规则」是死语义, W1 话术修正, plan G1)
                self._log_condition_error(ctx, e)
                return VERDICT_ERROR
            if not matched:
                return VERDICT_NO_MATCH
            # 去重: execute_once / cooldown
            if not self._dedup_allowed(ctx):
                return VERDICT_DEDUPED

        log_repr = ctx.torrent.log_repr
        start = 0 if fresh else resume_index
        # 断点前动作已成功(校验通过才续跑): 续跑轮 ok_action 起点 True; 全新执行从 False 累计
        ok_action = not fresh
        executed = False  # 本轮执行了非 skip 动作(ok/failed)
        result = None
        for i, action in enumerate(self.actions):
            if i < start:
                continue  # 跳过断点前已执行的动作
            try:
                result = action.execute(ctx)
            except Exception as e:
                result = ActionResult.fail(f"异常: {e}")
            if result.is_pending:
                # 异步等待: 记录断点并中断本规则, 由轮询子任务按结果重新入队恢复
                if task is not None:
                    task.resume_index = i + 1
                    logger.debug(f"规则[{self.name}] {log_repr} | 动作[{action.name}] 等待异步: {result.message}")
                    return VERDICT_PENDING  # 动作已提交, 断点已记录, 本轮中断待恢复
                ok_action = True  # 无任务(外部入口, 不应发生): 视为成功继续
                executed = True
                logger.info(f"规则[{self.name}] {log_repr} | 动作[{action.name}] 成功: {result.message}")
                continue
            if result.is_ok:
                ok_action = True
                executed = True
                logger.info(f"规则[{self.name}] {log_repr} | 动作[{action.name}] 成功: {result.message}")
            elif result.is_failed:
                executed = True
                logger.error(f"规则[{self.name}] {log_repr} | 动作[{action.name}] 失败: {result.message}")
                # 动作失败即中断本条动作链(per-step on_error 错误策略 W2 引入, plan G5)
                break
            elif result.is_skipped:
                logger.debug(f"规则[{self.name}] {log_repr} | 动作[{action.name}] 跳过: {result.message}")

        # 正常完成(含续跑完成): 消费断点(异常路径不清, 由 taskqueue 收尾默认重置兜底)
        if task is not None:
            task.resume_index = None

        if self.actions and not ctx.dry_run and ok_action:
            self.manager.ctx.state.record_execution(self.name, ctx.hash)

        return VERDICT_EXECUTED if (executed or ok_action) else VERDICT_NO_OP

    def _log_condition_error(self, ctx: RuleContext, e: Exception) -> None:
        """条件求值出错的日志(ERROR 级 + 同因节流, 避免每 tick × 每种子刷屏)

        与连接异常日志节流同一套路: 同一规则同一类错误 5 分钟内只报一次, 其后转 DEBUG 计数;
        换原因或冷却过后重新报。话术只宣称真实语义: 本条规则本轮跳过, 不涉及任何「后续规则」。
        """
        now = time.time()
        key = f"{type(e).__name__}:{e}"
        if key != self._cond_err_key or now - self._cond_err_ts > _COND_ERR_THROTTLE:
            logger.error(f"规则[{self.name}] {ctx.torrent.log_repr} | 本条规则本轮跳过(条件求值出错): {e}")
            self._cond_err_key = key
            self._cond_err_ts = now
        else:
            logger.debug(f"规则[{self.name}] {ctx.torrent.log_repr} | 条件求值出错(已节流): {e}")

    def _dedup_allowed(self, ctx: RuleContext) -> bool:
        """execute_once/cooldown 去重判断"""
        if self.execute_once == "never" and self.cooldown <= 0:
            return True
        rec = self.manager.ctx.state.get_exec_record(self.name, ctx.torrent.hash)
        now = datetime.now()
        if rec is not None:
            if self.cooldown > 0 and (now.timestamp() - rec.get("ts", 0)) < self.cooldown:
                return False
            if self.execute_once == "once":
                return False
            if self.execute_once == "daily" and rec.get("date") == now.date().isoformat():
                return False
            if (
                self.execute_once == "hourly" and rec.get("date") == now.date().isoformat() and
                rec.get("hour") == now.hour
            ):
                return False
        return True
