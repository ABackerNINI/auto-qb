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
from ..config.compat import (
    CONDITION_TREE_MAX_DEPTH,
    normalize_action_entry,
    normalize_conditions,
)
from ..config.schema.fields import ON_ERROR_DEFAULTS
# from ..qbmanager import QbManager
from ..core.qbapi import QbApi

logger = logging.getLogger(__name__)

# 条件求值出错日志的节流窗口(秒): 同规则同原因在此窗口内只报一次 ERROR
_COND_ERR_THROTTLE = 300.0

# process 返回契约(W1 收口, plan 26-11-01-0106 G1/G12; W2 扩 retry 档): 单值 verdict, 由引擎
# (core/modules/rules_mod._run_rule)显式消费 —— 记 DEBUG 结论供排障; W2 起按 error/retry 档
# 驱动 per-step 错误语义, W4 起进 per-run trace。旧 (handled, stop) 元组的 stop 档是死配置
# (唯一调用点整体丢弃返回值), 已随 stop_following_rules_if 退役一并删除。
VERDICT_NO_MATCH = "no_match"  # 条件不满足(含种子已删): 本轮未执行
VERDICT_ERROR = "error"  # 条件求值出错: 本条规则本轮跳过, 不影响其它规则
VERDICT_DEDUPED = "deduped"  # execute_once/cooldown 去重拦下
VERDICT_NO_OP = "no_op"  # 条件满足且未被去重, 但无动作产生效果(空动作表/全 skip)
VERDICT_PENDING = "pending"  # 动作等待异步完成: 断点已记录, 本轮中断待恢复
VERDICT_EXECUTED = "executed"  # 本轮执行了动作(成功/失败均计; 续跑完成同)
# 动作失败且 on_error.policy=retry(W2): 断点挂失败动作 + task.retry_delay=backoff, 引擎按
# 任务级 requeue 处理(_handle_rule 返回 REQUEUE, 队列收尾按 backoff 推迟下次到期)—— 无 run 内
# sleep(黄金法则 3/5)。重试上限 retries 由 process 按 task.attempt 判定, 耗尽后按 stop 收场。
VERDICT_RETRY = "retry"

# on_error 三档取值(与 schema.fields.ON_ERROR_POLICIES 同值; 取值合法性唯一入口是 config
# 校验, 此处常量只作逐档分派与注释锚点)
_POLICY_STOP = "stop"
_POLICY_CONTINUE = "continue"
_POLICY_RETRY = "retry"


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


# ---------------------------------------------------------------------------
# 条件组合树(W3-A, plan 26-11-01-0106 §3.2/G4)
#
# 规范化形态(config/compat.normalize_conditions 建树单点): conditions 是**一个节点** —
#   组合节点 {all: [节点...]} / {any: [节点...]} / {not: 节点} 或叶子 {条件名: spec}。
# 引擎只认树形(防漂移铁律: 没有「读 legacy 扁平列表」的第二语义分支); 旧扁平列表由
# normalize 包隐式 all(语义 = 现行 matches 的 all(...)), 各条件的行内分组/OR 语义全部
# 留在叶子内(逗号分组逐条件映射表见 compat.CONDITION_GROUPING_MAP)。
#
# 内存表示: ("all"|"any", [子节点...]) / ("not", 子节点) / ("leaf", 条件实例)。
# 求值递归 + 天然短路(all/any 用生成器, 首个定性结果即停); 叶子 .match 异常上抛,
# 由 Rule.process 兜成 verdict:error 本条本轮不命中(W2 语义, 不影响其它规则)。
# ---------------------------------------------------------------------------


def _build_condition_node(node, rule_name: str, depth: int = 1):
    """构造期建树: 规范化节点 dict -> 内存节点; 名称/结构合法性由 config 校验保证
    (黄金法则 4), 此处只对「程序内直接构造 Rule 的内存 spec」做形状兜底(ConfigError)。

    容错口径与 W2-A 前一致(P2-a): all/any 列表里的非 dict 项跳过(不崩溃不误建);
    not 的孩子必须是节点; 叶子构造异常包装 ConfigError 携带规则名。
    """
    if depth > CONDITION_TREE_MAX_DEPTH:
        raise ConfigError(f"规则 {rule_name}: 条件组合树嵌套超过上限 {CONDITION_TREE_MAX_DEPTH} 层")
    if not isinstance(node, dict) or len(node) != 1:
        raise ConfigError(f"规则 {rule_name}: 条件节点必须是单键字典: {node!r}")
    key, value = next(iter(node.items()))
    if key in ("all", "any"):
        if not isinstance(value, list):
            raise ConfigError(f"规则 {rule_name}: 条件组合节点 {key}: 必须是列表")
        children = []
        for child in value:
            if not isinstance(child, dict):
                continue  # P2-a: 非 dict 项跳过(与旧扁平列表容错同口径)
            children.append(_build_condition_node(child, rule_name, depth + 1))
        return (key, children)
    if key == "not":
        return ("not", _build_condition_node(value, rule_name, depth + 1))
    try:
        return ("leaf", registry.create_condition(node))
    except Exception as e:
        raise ConfigError(f"规则 {rule_name}: 条件 {node}: {e}") from e


def _eval_condition_node(node, ctx: "RuleContext") -> bool:
    """组合树递归求值: all/any 生成器短路, not 取反, 叶子交插件 match(异常上抛)"""
    kind, payload = node
    if kind == "all":
        return all(_eval_condition_node(c, ctx) for c in payload)
    if kind == "any":
        return any(_eval_condition_node(c, ctx) for c in payload)
    if kind == "not":
        return not _eval_condition_node(payload, ctx)
    return payload.match(ctx)


# ---------------------------------------------------------------------------
# choose 编排块(W3-B, plan 26-11-01-0106 G6/D3)
#
# 动作列表项可为 {choose: [{when, then}...], default?: [...]}, 与普通动作项混排:
#   - when 与 conditions 同款组合树节点(经 compat.normalize_conditions 建树单点 +
#     _build_condition_node 构造, 深度复用 CONDITION_TREE_MAX_DEPTH 从 1 起独立计);
#   - then/default 内是普通动作项(含 on_error), 经 normalize_action_entry 同一单点漏斗;
#   - 嵌套约束 = choose 内不再允许 choose(编排块只允许一层, 防递归爆炸; 校验器 fail-fast
#     在先, 此处构造期同口径兜底)。求值口径见 Rule.process 与 _pick_choose_branch。
# ---------------------------------------------------------------------------


class ChooseBranch:
    """choose 单个分支的运行时形态: when 条件树 + then 动作步(插件实例与 on_error 对齐)"""

    __slots__ = ("tree", "actions", "on_error")

    def __init__(self, tree, actions: list, on_error: list):
        self.tree = tree
        self.actions = actions
        self.on_error = on_error


class ChooseBlock:
    """choose 块运行时形态: 分支列表(按序求 when, 首个命中执行其 then)+ 可选 default 动作步"""

    __slots__ = ("branches", "default_actions", "default_on_error")

    def __init__(self, branches: list, default_actions: list, default_on_error: list):
        self.branches = branches
        self.default_actions = default_actions
        self.default_on_error = default_on_error


def _build_action_steps(entries, rule_name: str, allow_choose: bool = True) -> List[tuple]:
    """动作列表 -> 执行步列表(Rule 构造期, W3-B): ("action", 插件实例, on_error) / ("choose", ChooseBlock)

    - 每项过 normalize_action_entry 单点漏斗(幂等, 与载入链同源; choose 项内部归一到
      normalize_choose_block, 键面 {choose, default} 保留);
    - choose 项: 各分支 when 过 normalize_conditions + _build_condition_node 建树(深度复用
      CONDITION_TREE_MAX_DEPTH, 从 1 起独立计), then/default 递归本函数(allow_choose=False
      拦嵌套 choose —— 编排块只允许一层, 校验器 fail-fast 在先, 此处构造期兜底);
    - 非 dict 项跳过(与旧扁平列表容错同口径 P2-a); 动作构造异常包装 ConfigError 携带规则名。
    """
    steps: List[tuple] = []
    for act_spec in entries or []:
        if not isinstance(act_spec, dict):
            continue
        act = normalize_action_entry(act_spec)
        if isinstance(act, dict) and "choose" in act:
            if not allow_choose:
                raise ConfigError(f"规则 {rule_name}: choose 内不允许嵌套 choose(编排块只允许一层)")
            steps.append(("choose", _build_choose_block(act, rule_name)))
            continue
        name, value = act.get("type"), act.get("params")
        try:
            plugin = registry.create_action(name, value)
            on_error = Rule._resolve_on_error(act.get("on_error"))
        except Exception as e:
            raise ConfigError(f"规则 {rule_name}: 动作 {name}: {e}") from e
        steps.append(("action", plugin, on_error))
    return steps


def _build_choose_block(act: dict, rule_name: str) -> ChooseBlock:
    """choose 归一块 -> ChooseBlock 运行时形态(W3-B): when 建树 + then/default 动作步"""
    branches: List[ChooseBranch] = []
    for bi, br in enumerate(act.get("choose") or []):
        if not isinstance(br, dict):
            raise ConfigError(f"规则 {rule_name}: choose 分支[{bi}]: 必须是字典 {{when, then}}: {br!r}")
        try:
            tree = _build_condition_node(normalize_conditions(br.get("when")), rule_name)
        except Exception as e:
            raise ConfigError(f"规则 {rule_name}: choose 分支[{bi}].when: {e}") from e
        thens = br.get("then")
        if not isinstance(thens, list):
            raise ConfigError(f"规则 {rule_name}: choose 分支[{bi}].then: 必须是列表(动作项)")
        bsteps = _build_action_steps(thens, rule_name, allow_choose=False)
        branches.append(ChooseBranch(tree, [s[1] for s in bsteps], [s[2] for s in bsteps]))
    default_steps = _build_action_steps(act.get("default") or [], rule_name, allow_choose=False)
    return ChooseBlock(branches, [s[1] for s in default_steps], [s[2] for s in default_steps])


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

        # 条件组合树(W3-A): 载入链(load_config -> normalize_legacy_rules)已把旧扁平列表
        # 包成隐式 all 树; 这里再过一次单点漏斗(config.compat.normalize_conditions, 幂等,
        # 与动作 normalize_action_entry 同款)—— 引擎只认树形, 没有「读 legacy 扁平列表」
        # 的第二语义分支, 兼容层唯一容身在 config/compat.py。无条件(键缺省) = 直过(现行语义)。
        conds = normalize_conditions(spec.get("conditions"))
        if conds is None:
            self.condition_tree = None
        elif isinstance(conds, dict):
            self.condition_tree = _build_condition_node(conds, self.name)
        else:
            raise ConfigError(f"规则 {self.name}: conditions 必须是组合树字典: {conds!r}")

        # 解析动作序列(规范化形态 {type, params, on_error}, plan 26-11-01-0106 §3.2 W2-A/W2-B):
        # 载入链(load_config -> normalize_legacy_rules)已把旧扁平单键 dict 翻译成规范形并注入
        # 缺省 on_error; 这里对每项再过一次单点漏斗(config.compat.normalize_action_entry, 幂等)
        # —— 引擎只认规范形, 没有「读 legacy 键」的第二语义分支, 兼容层唯一容身在 config/compat.py。
        # 伪动作 ignore_next_action_error 已退役(D1): 载入层(rules_mod.load_rules)识别后
        # 转未启用并在内存副本里剔除, 引擎不再消费 —— 绕过载入层直接构造 Rule 遇伪动作
        # 按未知动作 ConfigError。
        # choose 编排块(W3-B): 动作项含 "choose" 键即编排块(经同一单点漏斗 normalize_choose_block
        # 归一), 与普通动作项混排进执行步列表; choose 内不允许嵌套 choose(校验器 fail-fast 在先,
        # 构造期同口径兜底)。
        self.steps: List[tuple] = _build_action_steps(spec.get("actions"), self.name, allow_choose=True)
        # 顶层普通动作插件实例(choose 步不进此列): 兼容既有消费面(测试/摘要); 执行循环走 steps
        self.actions = [s[1] for s in self.steps if s[0] == "action"]
        self.action_on_error: List[dict] = [s[2] for s in self.steps if s[0] == "action"]  # 与 self.actions 对齐(W2 G5)

        # 高风险动作静态提醒: reannounce 高频触发会被 tracker 封号, 未配去重时给出告警
        # (动作内另有最小间隔运行时保护兜底); choose 块内动作同样计入
        all_plugins = [s[1] for s in self.steps if s[0] == "action"]
        for s in self.steps:
            if s[0] == "choose":
                for br in s[1].branches:
                    all_plugins.extend(br.actions)
                all_plugins.extend(s[1].default_actions)
        if any(a.name == "reannounce" for a in all_plugins) and self.execute_once == "never" and self.cooldown <= 0:
            logger.error(f"规则[{self.name}] 含 reannounce 动作但未配置 execute_once/cooldown, 高频触发有封号风险")

    def matches(self, ctx: RuleContext) -> bool:
        """组合树求值(W3-A): 无条件 = 直过; 有条件 = 树形递归(旧扁平列表 = 隐式 all, 语义不变)"""
        if self.condition_tree is None:
            return True
        return _eval_condition_node(self.condition_tree, ctx)

    @staticmethod
    def _resolve_on_error(raw: Any) -> dict:
        """on_error 配置解析(构造期, plan W2/G5): config 校验是取值合法性的唯一入口, 此处
        假定已通过校验(fail-fast); 兜底仅对「程序内直接构造 Rule 的内存 spec」补缺省形状 ——
        缺键回 ON_ERROR_DEFAULTS(schema/fields 单点, 与 normalize 注入同源), 类型异常抛
        ConfigError 由动作构造包装统一报。"""
        oe = raw if isinstance(raw, dict) else {}
        try:
            return {
                "policy": str(oe.get("policy", ON_ERROR_DEFAULTS["policy"])),
                "retries": int(oe.get("retries", ON_ERROR_DEFAULTS["retries"])),
                "backoff": float(oe.get("backoff", ON_ERROR_DEFAULTS["backoff"])),
            }
        except (TypeError, ValueError) as e:
            raise ConfigError(f"on_error 取值非法: {raw}: {e}") from e

    def process(self, ctx: RuleContext) -> str:
        """
        处理一个种子, 返回单值 verdict(模块级 VERDICT_* 常量, 消费方见常量区注释)。

        断点契约(与 taskqueue 的默认重置语义配合):
        - 读:   进入时只读 task.resume_index 判定续跑(不清零); 索引单位 = 执行步(self.steps,
                W3-B 起 choose 块与普通动作同占一步 —— 无 choose 的规则 steps 与 actions 1:1,
                既有断点语义不变)
        - 写:   动作返回 pending 时记录断点并中断, 由校验轮询子任务按结果重新入队;
                动作失败且 on_error.policy=retry 时(W2/R3)同样挂断点(= 失败动作索引)并置
                task.retry_delay=backoff, 返回 VERDICT_RETRY —— 引擎按任务级 requeue 处理,
                队列收尾按 backoff 推迟下次到期(无 run 内 sleep)。续跑轮跳过条件评估与去重,
                重试计数 task.attempt 由引擎维护(上限 retries, 耗尽按 stop 收场)。
                choose 块内(W3-B 自定口径): pending 挂块后(块内不细粒度续跑), retry 挂块首
                (续跑轮整块重新求值重新分派)—— resume_index 是扁平整数, 块内不细编码
        - 清:   正常完成时清零(连同 attempt 归零); 异常路径不清零 —— 由 taskqueue 收尾
                默认重置兜底(下轮从头)
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
        stopped = False
        for si, step in enumerate(self.steps):
            if si < start:
                continue  # 跳过断点前已执行的步
            if step[0] == "action":
                action, on_error = step[1], step[2]
                result = self._execute_action(action, ctx)
                disp = self._dispatch_result(action, result, on_error, ctx, log_repr)
                if disp == "pending":
                    # 异步等待: 记录断点并中断本规则, 由轮询子任务按结果重新入队恢复
                    if task is not None:
                        task.resume_index = si + 1
                        logger.debug(f"规则[{self.name}] {log_repr} | 动作[{action.name}] 等待异步: {result.message}")
                        return VERDICT_PENDING  # 动作已提交, 断点已记录, 本轮中断待恢复
                    ok_action = True  # 无任务(外部入口, 不应发生): 视为成功继续
                    executed = True
                    continue
                if disp == "ok":
                    ok_action = True
                    executed = True
                elif disp in ("continue", "stop"):
                    executed = True  # 失败动作本身算已执行(W2 前语义, 与策略档无关)
                    if disp == "stop":
                        stopped = True
                        break
                elif disp == "retry":
                    # 断点挂失败动作: 续跑轮从本动作重试(跳过条件与去重);
                    # retry_delay 已由 _dispatch_result 置入 task(requeue 无 run 内 sleep)
                    task.resume_index = si
                    return VERDICT_RETRY
                # skip: 只记 DEBUG(_dispatch_result 单点已记), 不影响 ok/executed
            else:  # choose 编排块(W3-B, plan G6/D3)
                chosen = self._pick_choose_branch(step[1], ctx, log_repr)
                if chosen is None:
                    # when 求值异常: 与顶层条件求值异常同语义(保守: 求值出错不误入 default),
                    # 本条规则本轮按 error 收场, 不影响其它规则
                    return VERDICT_ERROR
                actions, on_errors = chosen
                for action, on_error in zip(actions, on_errors):
                    result = self._execute_action(action, ctx)
                    disp = self._dispatch_result(action, result, on_error, ctx, log_repr)
                    if disp == "pending":
                        if task is not None:
                            # choose 步粒度(W3-B 自定口径): 断点记块后(si + 1), 分支内已提交
                            # 动作视为完成, 同分支其后动作本轮中断后不续(块内不细粒度续跑)
                            task.resume_index = si + 1
                            logger.debug(f"规则[{self.name}] {log_repr} | 动作[{action.name}] 等待异步: {result.message}")
                            return VERDICT_PENDING
                        ok_action = True  # 无任务(外部入口, 不应发生): 视为成功继续
                        executed = True
                        continue
                    if disp == "ok":
                        ok_action = True
                        executed = True
                    elif disp in ("continue", "stop"):
                        executed = True  # 失败动作本身算已执行(与顶层同口径)
                        if disp == "stop":
                            stopped = True
                            break
                    elif disp == "retry":
                        # choose 块内 retry(W3-B 自定口径): 断点记块首(si) —— 续跑轮整块重新
                        # 执行, when 按当时现场重新求值重新分派(语义 = 重新分派); attempt/retries
                        # 计数与顶层同径(retry_delay 已由 _dispatch_result 置入 task)
                        task.resume_index = si
                        return VERDICT_RETRY
                if stopped:
                    break

        # 正常完成(含续跑完成): 消费断点(异常路径不清, 由 taskqueue 收尾默认重置兜底);
        # attempt 同步归零 —— 下轮全新执行不继承上一轮的 retry 计数
        if task is not None:
            task.resume_index = None
            task.attempt = 0

        if self.steps and not ctx.dry_run and ok_action:
            self.manager.ctx.state.record_execution(self.name, ctx.hash)

        return VERDICT_EXECUTED if (executed or ok_action) else VERDICT_NO_OP

    @staticmethod
    def _execute_action(action, ctx: "RuleContext") -> ActionResult:
        """单动作执行: 插件内异常兜成 failed 结果(与失败同径走 on_error 三档分派, W2 语义)"""
        try:
            return action.execute(ctx)
        except Exception as e:
            return ActionResult.fail(f"异常: {e}")

    def _dispatch_result(self, action, result: ActionResult, on_error: dict, ctx: "RuleContext", log_repr: str) -> str:
        """动作结果处置单点(W2 on_error 三档, plan G5; W3 起 choose 内外共用 —— 无第二语义分支)

        返回处置字: ok / skip / continue / stop / pending / retry。
        - stop(默认)= 现行失败即止; continue = 记账后继续后续动作(替代旧布尔 ignore);
        - retry = 任务级 requeue(上限 retries, 耗尽按 stop): 本方法置 task.retry_delay=backoff,
          断点(resume_index)由调用方按所在层写入(顶层动作步挂失败动作, choose 步挂块首 ——
          两层断点粒度不同, 见 process); 无任务(外部入口)时 retry 档退化按 stop 收场;
        - 日志(成功/失败/跳过/等待话术)也在此单点, 调用方不重复记。
        """
        if result.is_pending:
            return "pending"
        if result.is_ok:
            logger.info(f"规则[{self.name}] {log_repr} | 动作[{action.name}] 成功: {result.message}")
            return "ok"
        if result.is_failed:
            policy = str(on_error.get("policy", "stop"))
            if policy == _POLICY_CONTINUE:
                logger.warning(f"规则[{self.name}] {log_repr} | 动作[{action.name}] 失败(continue, 继续后续动作): {result.message}")
                return "continue"
            if policy == _POLICY_RETRY and ctx.task is not None:
                retries = int(on_error.get("retries", 3))
                if ctx.task.attempt < retries:
                    backoff = float(on_error.get("backoff", 60))
                    ctx.task.retry_delay = backoff  # 引擎 requeue 时按此推迟下次到期(无 run 内 sleep)
                    logger.warning(
                        f"规则[{self.name}] {log_repr} | 动作[{action.name}] 失败"
                        f"(retry {ctx.task.attempt + 1}/{retries}, {backoff:g}s 后重试): {result.message}"
                    )
                    return "retry"
                logger.error(
                    f"规则[{self.name}] {log_repr} | 动作[{action.name}] 失败"
                    f"(重试 {retries} 次仍失败, 中止本条动作链): {result.message}"
                )
                return "stop"
            logger.error(f"规则[{self.name}] {log_repr} | 动作[{action.name}] 失败: {result.message}")
            # 动作失败即中断本条动作链(stop 默认档; retry 耗尽同径)
            return "stop"
        logger.debug(f"规则[{self.name}] {log_repr} | 动作[{action.name}] 跳过: {result.message}")
        return "skip"

    def _pick_choose_branch(self, block: ChooseBlock, ctx: "RuleContext", log_repr: str):
        """choose 分支选择(W3-B, plan G6/D3): 按序求 when, 首个命中执行其 then; 无命中且有
        default 执行 default; 无命中且无 default = 空操作(返回空动作表, 与空动作表同语义)。

        when 求值异常: 记 ERROR(与顶层条件求值异常同款节流)并返回 None —— 调用方按
        VERDICT_ERROR 收场(保守: 求值出错不误入 default, 与「条件异常 -> 本条本轮不命中」
        同一失败哲学)。"""
        for br in block.branches:
            try:
                if _eval_condition_node(br.tree, ctx):
                    return br.actions, br.on_error
            except Exception as e:
                self._log_condition_error(ctx, e)
                return None
        if block.default_actions:
            return block.default_actions, block.default_on_error
        return [], []

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
