"""rules 框架基础: 动作结果, 条件/动作基类, 规则上下文, Rule 插件"""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List, Optional

from . import registry
from .. import utils
from ..torrents import TorrentRecord

logger = logging.getLogger(__name__)


class ActionResult:
    """动作执行结果: success / failed / skipped"""
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

    @property
    def is_ok(self) -> bool:
        return self.status == "success"

    @property
    def is_failed(self) -> bool:
        return self.status == "failed"

    @property
    def is_skipped(self) -> bool:
        return self.status == "skipped"

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
    client: Any  # qbittorrent Client
    config: Any  # Config
    torrent: Any  # TorrentDictionary
    dry_run: bool
    rule_name: str = ""
    _tracker_urls: Optional[List[str]] = field(default=None)
    _tracker_confs: Optional[List] = field(default=None)
    _files: Optional[List] = field(default=None)

    # TODO: 当一个torrent匹配到多个tracker时, warning, 跳过

    @property
    def required_seeding_time(self) -> str:
        """第一个匹配 tracker 的 HR 时间部分, 如 '3D', 用于 ${required_seeding_time} 变量替换"""
        for conf in self.matched_tracker_confs():
            if conf.hr:
                return conf.hr.required_seeding_time_raw
        return ""

    @property
    def torrent_record(self) -> TorrentRecord:
        return self.manager.store.get(self.torrent.hash)

    def replace_vars(self, text: str) -> str:
        """替换标签/分类格式中的变量, 当前支持 ${required_seeding_time}"""
        return str(text).replace("${required_seeding_time}", self.required_seeding_time)

    def tracker_urls(self) -> List[str]:
        if self._tracker_urls is None:
            store = getattr(self.manager, "store", None)
            if store is not None and store.client is not None and self.torrent.hash in store:
                # 快照种子: 走 store 惰性缓存(每 tick 一次拉取, 不重复调 API)
                self._tracker_urls = store.tracker_urls(self.torrent.hash)
            else:
                # 外部传入种子(process_torrent 兼容入口): 直接拉取
                self._tracker_urls = [
                    t["url"] for t in self.client.torrents_trackers(self.torrent.hash) if t.get("url")
                ]
        return self._tracker_urls

    def matched_tracker_confs(self) -> List[Any]:
        """匹配到的 TrackerConfig 列表(可能多个)"""
        if self._tracker_confs is None:
            self._tracker_confs = utils.match_tracker_confs(self.config.trackers, self.tracker_urls())
        return self._tracker_confs

    def matched_tracker_names(self) -> List[str]:
        return [c.name for c in self.matched_tracker_confs()]

    def describe(self) -> str:
        """多行种子信息摘要, 用于动作日志: 名称/站点/状态/hash"""
        try:
            sites = ", ".join(self.matched_tracker_names()) or "未匹配"
        except Exception:
            sites = "未知"
        return (
            f"  - 种子: {self.torrent.name}\n"
            f"  - 站点: {sites}\n"
            f"  - 状态: {self.torrent.state}\n"
            f"  - 哈希: {self.torrent.hash}"
        )

    def files(self) -> List[Any]:
        if self._files is None:
            store = getattr(self.manager, "store", None)
            if store is not None and store.client is not None and self.torrent.hash in store:
                # 快照种子: 走 store 惰性缓存(每 tick 一次拉取, 不重复调 API)
                self._files = store.files(self.torrent.hash)
            else:
                # 外部传入种子(process_torrent 兼容入口): 直接拉取
                self._files = self.client.torrents_files(self.torrent.hash)
        return self._files

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
        for cond_spec in spec.get("conditions", []):
            if isinstance(cond_spec, dict):
                self.conditions.append(registry.create_condition(cond_spec))

        # 解析动作序列, 处理 ignore_next_action_error 标志
        self.actions = []
        ignore_next = False
        for act_spec in spec.get("actions", []):
            if not isinstance(act_spec, dict):
                continue
            if "ignore_next_action_error" in act_spec:
                ignore_next = utils.parse_bool(act_spec["ignore_next_action_error"])
                continue
            name, value = next(iter(act_spec.items()))
            self.actions.append(registry.create_action(name, value, ignore_next))
            ignore_next = False

    def matches(self, ctx: RuleContext) -> bool:
        """所有条件必须全部满足(AND)"""
        return all(c.match(ctx) for c in self.conditions)

    def process(self, ctx: RuleContext):
        """
        处理一个种子. 返回 (handled, stop)
        handled: 规则是否执行了动作
        stop:    是否停止后续规则(stop_following_rules_if)
        """
        ctx.rule_name = self.name
        try:
            matched = self.matches(ctx)
        except Exception as e:
            logger.warning(f"规则 {self.name}: 条件匹配异常: {e}")
            return False, False

        if not matched:
            return False, self.stop_if == "conditions-not-met"

        # 去重: execute_once / cooldown
        if not self._dedup_allowed(ctx):
            return False, False

        failed = False
        ok_action = False  # 至少一个动作成功才算"实际执行", 失败/跳过不记录执行历史(否则挡住当日重试)
        for action in self.actions:
            try:
                result = action.execute(ctx)
            except Exception as e:
                result = ActionResult.fail(f"异常: {e}")
            if result.is_ok:
                ok_action = True
            if result.is_failed:
                logger.warning(f"规则: {self.name} | 动作: {action.name} 失败 | 结果: {result.message}")
                failed = True
                if not action.ignore_error:
                    break
            elif result.is_ok:
                logger.info(f"规则: {self.name} | 动作: {action.name} 成功 | 结果: {result.message}")

        if self.actions and not ctx.dry_run and ok_action:
            self.manager.record_execution(self.name, ctx.torrent.hash)

        stop = False
        if self.stop_if in ("conditions-met", "always"):
            stop = True
        elif self.stop_if == "action-failed" and failed:
            stop = True
        elif self.stop_if == "all-actions-succeed" and not failed:
            stop = True

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
