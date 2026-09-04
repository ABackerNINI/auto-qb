"""rules 框架基础: 动作结果, 条件/动作基类, 规则上下文, Rule 插件"""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List, Optional
from qbittorrentapi import TorrentDictionary, Client

from . import registry
from .. import utils
from ..torrents import TorrentRecord
from ..config import Config, ConfigError
# from ..qbmanager import QbManager
from ..qbapi import QbApi

logger = logging.getLogger(__name__)


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

    def __init__(self, spec: Any, ignore_error: bool = False):
        self.spec = spec
        self.ignore_error = ignore_error  # 由前一个 ignore_next_action_error 设置

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

    _tracker_urls: Optional[List[str]] = field(default=None)
    _tracker_confs: Optional[List] = field(default=None)
    _files: Optional[List] = field(default=None)

    @property
    def api(self) -> QbApi | Client:
        """qB API 门面: manager.api 已绑定客户端时优先; 否则(外部传入种子/测试)退化到 client"""
        api = getattr(self.manager, "api", None)
        if api is not None:
            return api
        return self.client

    # TODO: 当一个torrent匹配到多个tracker时, warning, 跳过

    @property
    def required_seeding_time(self) -> str:
        """第一个匹配 tracker 的 HR 时间部分, 如 '3D', 用于 ${required_seeding_time} 变量替换"""
        conf = self.torrent.tracker_conf
        if conf and conf.hr:
            return conf.hr.required_seeding_time_raw
        return ""

    @property
    def torrent(self) -> TorrentRecord:
        return self.manager.store.get(self.hash)

    def replace_vars(self, text: str) -> str:
        """替换标签/分类格式中的变量, 当前支持 ${required_seeding_time}"""
        return str(text).replace("${required_seeding_time}", self.required_seeding_time)

    # TODO: 移动到actions.py
    def check_hr_condition(self, conf) -> bool:
        """是否满足 HR 触发条件(下载比例或下载量), 用于排除辅种"""
        if not conf.hr:
            return False
        hr = conf.hr
        cond_type, cond_value = hr.condition
        if cond_type == "dlratio":
            total = self.torrent.total_size or 1
            if (self.torrent.downloaded / total) < cond_value:
                return False
        elif cond_type == "dlsize":
            if self.torrent.downloaded < cond_value:
                return False
        return True

    # TODO: 移动到actions.py
    def check_hr_satisfied(self, conf) -> bool:
        """是否满足 HR 要求: 触发条件 + (做种时长 >= 要求时间 + 额外时间 或 分享率达标)"""
        if not conf.hr:
            return False
        hr = conf.hr
        if not self.check_hr_condition(conf):
            return False
        seeding_ok = self.torrent.seeding_time >= (hr.required_seeding_time + hr.extra_seeding_time)
        ratio_ok = hr.required_share_ratio > 0 and (self.torrent.ratio or 0) >= hr.required_share_ratio
        return seeding_ok or ratio_ok


class Rule:
    """一条规则插件: 条件列表 + 动作列表 + 执行语义, 由 QbManager 统一加载与调度"""
    def __init__(self, name: str, spec: dict, manager: Any):
        self.name = name
        self.spec = spec
        self.manager = manager
        self.enabled = utils.parse_bool(spec.get("enabled", True))
        self.interval = utils.parse_time(str(spec.get("interval", "0S")))  # 规则扫描间隔, 0 = 每轮
        self.execute_once = str(spec.get("execute_once", "never"))
        self.cooldown = utils.parse_time(str(spec.get("cooldown", "0S")))
        self.stop_if = str(spec.get("stop_following_rules_if", "conditions-met"))

        self.conditions = []
        for cond_spec in spec.get("conditions") or []:
            if not isinstance(cond_spec, dict):
                continue
            try:
                self.conditions.append(registry.create_condition(cond_spec))
            except Exception as e:
                raise ConfigError(f"规则 {self.name}: 条件 {cond_spec}: {e}") from e

        # 解析动作序列, 处理 ignore_next_action_error 标志
        self.actions = []
        ignore_next = False
        for act_spec in spec.get("actions") or []:
            if not isinstance(act_spec, dict):
                continue
            if "ignore_next_action_error" in act_spec:
                ignore_next = utils.parse_bool(act_spec["ignore_next_action_error"])
                continue
            name, value = next(iter(act_spec.items()))
            try:
                self.actions.append(registry.create_action(name, value, ignore_next))
            except Exception as e:
                raise ConfigError(f"规则 {self.name}: 动作 {name}: {e}") from e
            ignore_next = False

    def matches(self, ctx: RuleContext) -> bool:
        """所有条件必须全部满足(AND)"""
        return all(c.match(ctx) for c in self.conditions)

    def process(self, ctx: RuleContext):
        """
        处理一个种子. 返回 (handled, stop)
        handled: 规则是否执行了动作
        stop:    是否停止后续规则(stop_following_rules_if)

        断点续跑(resume 语义): 任务队列驱动的规则任务在动作返回 pending(如 full-checking
        已提交校验)时记录 resume_index 并中断; 校验完成后任务被 resume 重新入队, 下次执行
        检测到 resume_index -> 跳过条件评估与去重, 从断点动作继续执行后续动作。
        """
        if ctx.torrent is None:
            return False, False

        ctx.rule_name = self.name
        task = getattr(ctx, "task", None)

        # 断点: 一次性读取并清零; 有断点 -> 续跑(跳过条件评估与去重)
        resume_index = None
        if task is not None and getattr(task, "resume_index", None) is not None:
            resume_index = task.resume_index
            task.resume_index = None

        if resume_index is None:
            try:
                matched = self.matches(ctx)
            except Exception as e:
                logger.warning(f"规则[{self.name}] {ctx.torrent.log_repr} | 条件匹配异常: {e}")
                return False, False
            if not matched:
                return False, self.stop_if == "conditions-not-met"
            # 去重: execute_once / cooldown
            if not self._dedup_allowed(ctx):
                return False, False

        log_repr = ctx.torrent.log_repr
        failed = False
        # 断点前动作已成功(校验通过才续跑): ok_action 起点 True; 全新执行从 False 累计
        ok_action = resume_index is not None
        result = None
        for i, action in enumerate(self.actions):
            if resume_index is not None and i < resume_index:
                continue  # 跳过断点前已执行的动作
            try:
                result = action.execute(ctx)
            except Exception as e:
                result = ActionResult.fail(f"异常: {e}")
            if result.is_pending:
                # 异步等待: 记录断点并中断本规则, 由外部 resume/reschedule 决定恢复
                if task is not None:
                    task.resume_index = i + 1
                    logger.info(f"规则[{self.name}] {log_repr} | 动作[{action.name}] 等待异步: {result.message}")
                    return True, True  # handled=True(动作已提交), stop=True(中断后续规则)
                ok_action = True  # 无任务(外部入口, 不应发生): 视为成功继续
                logger.info(f"规则[{self.name}] {log_repr} | 动作[{action.name}] 成功: {result.message}")
                continue
            if result.is_ok:
                ok_action = True
            if result.is_failed:
                logger.warning(f"规则[{self.name}] {log_repr} | 动作[{action.name}] 失败: {result.message}")
                failed = True
                if not action.ignore_error:
                    break
            elif result.is_ok:
                logger.info(f"规则[{self.name}] {log_repr} | 动作[{action.name}] 成功: {result.message}")
            elif result.is_skipped:
                logger.debug(f"规则[{self.name}] {log_repr} | 动作[{action.name}] 跳过: {result.message}")

        if self.actions and not ctx.dry_run and ok_action:
            self.manager.record_execution(self.name, ctx.hash)

        stop = False
        if self.stop_if in ("conditions-met", "always"):
            stop = True
        elif self.stop_if == "action-failed" and failed:
            stop = True
        elif self.stop_if == "all-actions-succeed" and not failed:
            stop = True

        if result is None:
            return ok_action, stop  # 空循环(续跑且断点后无动作): 断点前动作已成功
        return not result.is_skipped, stop

    def _dedup_allowed(self, ctx: RuleContext) -> bool:
        """execute_once/cooldown 去重判断"""
        if self.execute_once == "never" and self.cooldown <= 0:
            return True
        rec = self.manager.get_exec_record(self.name, ctx.torrent.hash)
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
