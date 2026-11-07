"""内置条件插件: path, size, tags, category, trackers, tracker_group, state, hr, date_time,
seedtime, upload_ratio, freespace, expr(表达式)"""
from datetime import datetime
from datetime import time as dtime
from typing import Any

from ..config.schema.fields import HR_MODES
from ..infra import utils
from .base import BaseCondition, RuleContext
from .expr import compile_expr, evaluate, validate
from .expr.env import disk_usage_value
from .expr.errors import ExprError
from .registry import register_condition


def _parse_range_bounds(value: Any, label: str) -> tuple[int, int] | None:
    """date_time 的 day_of_month / day_of_week 区间/单值串 -> (lo, hi) 端点(单值 v 即 (v, v));
    空值/falsy(None/''/0/False) -> None = 未配置(与旧 match 真值门同口径, 刻意保留)。

    解析边界(R2#20): 串的格式解析(区间切分 / int 转换)不依赖运行期上下文, 前移到构造期
    fail-fast(黄金法则 4, 与 SizeCondition/FreespaceCondition 的构造期解析同模式)——此前
    非法串(如 '1,15' / 'abc')推迟到每轮 match 才抛 ValueError, 被兜成 verdict:error,
    规则永久失效只留节流 ERROR 日志; 现在构造失败即异常, 经 _build_condition_node 包装成
    ConfigError 携带规则名。与「当天日期」的比较依赖运行期 now, 留在 match(见 DateTimeCondition)。
    """
    if not value:
        return None
    s = str(value).strip()
    try:
        if "-" in s:
            a, b = s.split("-", 1)
            return int(a), int(b)
        v = int(s)
        return v, v
    except ValueError as e:
        raise ValueError(f"{label} 区间串非法: {value!r}") from e


def _parse_time_bounds(value: Any) -> tuple[dtime, dtime] | None:
    """date_time 的 time 时段串 -> (start, end) 端点时刻; 空值/falsy(None/''/0/False) -> None = 未配置(与旧 match 真值门同口径, 刻意保留)。

    解析走单点 utils.parse_time_range(与通知 quiet_hours / HR 限速窗口共用), 构造期完成;
    与「当前时刻」的比较依赖运行期 now, 留在 match(见 DateTimeCondition)。
    """
    if not value:
        return None
    try:
        return utils.parse_time_range(value)
    except ValueError as e:
        raise ValueError(f"time 时段串非法: {value!r}: {e}") from e


def _within(value: int, bounds: tuple[int, int]) -> bool:
    """预解析端点的区间判定: "a-b" 含端点, 单值 v 即 (v, v) 退化为等值(语义与旧 _in_range 一致)"""
    lo, hi = bounds
    return lo <= value <= hi


def _in_range(value: int, spec: str) -> bool:
    """区间/单值串判定(解析单点 _parse_range_bounds): "3-8" 含端点, 单值即等值。

    DateTimeCondition.match 用构造期预解析端点走 _within; 本函数保留为同一份语义的
    纯函数直测入口(test_conditions 的 C40 守阵等), 生产路径不再逐轮调用。
    """
    bounds = _parse_range_bounds(spec, "spec")
    if bounds is None:
        raise ValueError(f"区间串非法: {spec!r}")
    return _within(value, bounds)


@register_condition
class PathCondition(BaseCondition):
    """路径条件: 匹配 save_path/content_path 前缀, 支持 regex: 前缀, 列表为或关系"""
    name = "path"

    def __init__(self, spec: Any) -> None:
        self.patterns = spec if isinstance(spec, list) else [spec]

    def match(self, ctx: RuleContext) -> bool:
        candidates = [ctx.torrent.save_path, ctx.torrent.content_path]
        for path in candidates:
            if utils.match_path_patterns(path, self.patterns):
                return True
        return False


@register_condition
class SizeCondition(BaseCondition):
    """种子总大小条件, 如 '>=100MiB'"""
    name = "size"

    def __init__(self, spec: Any) -> None:
        self.op, self.value = utils.parse_compare(str(spec), utils.parse_fsize)

    def match(self, ctx: RuleContext) -> bool:
        return utils.compare(self.op, ctx.torrent.size, self.value)


@register_condition(validator="tags", watchable_field="tags")
class TagsCondition(BaseCondition):
    """标签条件: 每组内逗号分隔为与, 组间为或, 支持 regex:/:ignore_case 和 ${required_seeding_time}"""
    name = "tags"

    def __init__(self, spec: Any) -> None:
        spec = spec if isinstance(spec, list) else [spec]
        self.groups = [[p.strip() for p in g.split(",") if p.strip()] for g in spec]

    def match(self, ctx: RuleContext) -> bool:
        current = ctx.torrent.tags_set
        for group in self.groups:
            ok = True
            for pat in group:
                pat = utils.replace_vars(pat, ctx.torrent.tracker_conf)
                if not pat:
                    continue
                # 单模式包列表复用 utils.match_value(语法解析/regex:/:ignore_case 唯一实现)
                if not any(utils.match_value(t, [pat]) for t in current):
                    ok = False
                    break
            if ok:
                return True
        return False


@register_condition(validator="pattern_list", watchable_field="category")
class CategoryCondition(BaseCondition):
    """分类条件: 列表为或关系, 支持 regex:/:ignore_case"""
    name = "category"

    def __init__(self, spec: Any) -> None:
        self.patterns = spec if isinstance(spec, list) else [spec]

    def match(self, ctx: RuleContext) -> bool:
        category = (ctx.torrent.category or "").strip()
        return any(utils.match_value(category, [str(pat)]) for pat in self.patterns)


@register_condition(validator="pattern_list")
class TrackersCondition(BaseCondition):
    """tracker 条件: 匹配 tracker 配置名, 列表为或关系, 支持 regex:/:ignore_case"""
    name = "trackers"

    def __init__(self, spec: Any) -> None:
        self.patterns = spec if isinstance(spec, list) else [spec]

    def match(self, ctx: RuleContext) -> bool:
        conf = ctx.torrent.tracker_conf
        names = [conf.name] if conf is not None else []
        return any(any(utils.match_value(n, [str(pat)]) for n in names) for pat in self.patterns)


@register_condition(validator="pattern_list")
class TrackerGroupCondition(BaseCondition):
    """站点分组条件: 匹配站点 groups 字段声明的分组, 列表为或关系, 支持 regex:/:ignore_case

    分组是站点配置层的声明(不写种子), 与 grouping 段的辅种种子分组无关;
    无 tracker_conf(未匹配站点)的种子恒不匹配, 与 trackers 条件同语义。
    """
    name = "tracker_group"

    def __init__(self, spec: Any) -> None:
        self.patterns = spec if isinstance(spec, list) else [spec]

    def match(self, ctx: RuleContext) -> bool:
        conf = ctx.torrent.tracker_conf
        groups = conf.groups if conf is not None else []
        return any(any(utils.match_value(g, [str(pat)]) for g in groups) for pat in self.patterns)


@register_condition(validator="state")
class StateCondition(BaseCondition):
    """状态条件: qB TorrentState 枚举类别属性(is_downloading/is_uploading/is_complete/
    is_checking/is_stopped/is_paused/is_errored), 与 qB 官方语义一致, 每组内 & 连接为与,
    组间为或。spec 合法性由 config 校验阶段保证(仅 is_* 类别属性), 此处直接使用"""
    name = "state"

    def __init__(self, spec: Any) -> None:
        spec = spec if isinstance(spec, list) else [spec]
        self.groups = [str(g).split("&") for g in spec]

    def match(self, ctx: RuleContext) -> bool:
        for group in self.groups:
            if all(getattr(ctx.torrent.state_enum, s) for s in group):
                return True
        return False


@register_condition
class HrCondition(BaseCondition):
    """HR 条件: condition-met(需管束) / condition-not-met / satisfied(义务已了)

    condition-met / condition-not-met 走 hr_managed(需管束, 与打标/管束同源, 计划 26-09-30-0559 §6);
    satisfied = check_hr_satisfied 单条件 —— 修掉旧「check_hr_condition and check_hr_satisfied」
    在无证据+已达标时恒 False 的拧巴。
    """
    name = "hr"

    def __init__(self, spec: Any) -> None:
        self.mode = str(spec)
        if self.mode not in HR_MODES:
            # 未知 mode 旧实现静默落 condition-met 分支: 行为随站点是否配 HR 漂移且全程零诊断
            # (拼写错误如 'satified' 能过加载, 违反黄金法则 4)。config 层无 hr 深度校验
            # (registry 条目未声明 validator), 这里是唯一闸口 —— 构造期 fail-fast; 规则建树
            # 经 _build_condition_node 包装成 ConfigError 携带规则名。
            raise ValueError(f"hr 条件 mode 非法: {self.mode!r} (合法取值: {', '.join(HR_MODES)})")

    def match(self, ctx: RuleContext) -> bool:
        torrent = ctx.torrent
        conf = torrent.tracker_conf
        # 无 HR 可判定的两种情形**必须显式分支**: 直接读 conf.hr 会在 conf=None 时抛
        # AttributeError, 被上层吞掉后故障表现为"规则没匹配"而不是报错 —— 极难定位。
        if conf is None:
            # 未匹配站点: 拿不到站点配置, 无从判定 ⇒ 保守按"未管束/未满足"处理
            # (与 trackers / tracker_group 的"无 tracker_conf 恒不匹配"同语义)
            return self.mode == "condition-not-met"
        if conf.hr is None:
            # 站点已匹配但没配 HR = 没有 HR 要求 ⇒ "已满足"与"未管束"同为真
            # (表达式侧 tor.hr_satisfied 同场景恒 false —— 那里答「可打标/可删」达标语义,
            #  本处答「有无义务」; 有意分歧勿单边改齐, 见 rules/expr/env.py _hr 注释)
            return self.mode != "condition-met"
        if self.mode == "condition-not-met":
            return not torrent.hr_managed()
        if self.mode == "satisfied":
            return torrent.check_hr_satisfied()
        # condition-met
        return torrent.hr_managed()


@register_condition
class DateTimeCondition(BaseCondition):
    """日期时间条件: day_of_month / day_of_week / time

    区间/时段串在构造期解析(R2#20, 黄金法则 4, 与 SizeCondition/FreespaceCondition 同模式):
    day_of_month/day_of_week -> (lo, hi) 端点(单值 v 即 (v, v)), time -> (start, end) 端点
    时刻(解析单点 utils.parse_time_range)。解析边界: 纯格式解析不依赖运行期上下文, 前移到
    构造期; 「当天日期/当前时刻」(now)是运行期值, 比较留在 match —— match 行为与解析前移前
    一致。非法串构造失败即 ValueError, 经 _build_condition_node 包装成 ConfigError 携带
    规则名(此前每轮 match 才抛, 被兜成 verdict:error, 规则永久失效只留节流 ERROR 日志)。
    """
    name = "date_time"

    def __init__(self, spec: Any) -> None:
        self.day_of_month = _parse_range_bounds(spec.get("day_of_month"), "day_of_month")
        self.day_of_week = _parse_range_bounds(spec.get("day_of_week"), "day_of_week")
        self.time_range = _parse_time_bounds(spec.get("time"))

    def match(self, ctx: RuleContext) -> bool:
        now = datetime.now()
        if self.day_of_month is not None and not _within(now.day, self.day_of_month):
            return False
        if self.day_of_week is not None and not _within(now.isoweekday(), self.day_of_week):
            return False
        if self.time_range is not None:
            start, end = self.time_range
            if not utils.time_within(now.time(), start, end):
                return False
        return True


@register_condition
class SeedtimeCondition(BaseCondition):
    """做种时长条件, 如 '<24H'"""
    name = "seedtime"

    def __init__(self, spec: Any) -> None:
        self.op, self.value = utils.parse_compare(str(spec), utils.parse_time)

    def match(self, ctx: RuleContext) -> bool:
        return utils.compare(self.op, ctx.torrent.seeding_time, self.value)


@register_condition
class UploadRatioCondition(BaseCondition):
    """上传比率条件, 如 '>1.5'"""
    name = "upload_ratio"

    def __init__(self, spec: Any) -> None:
        self.op, self.value = utils.parse_compare(str(spec), float)

    def match(self, ctx: RuleContext) -> bool:
        return utils.compare(self.op, ctx.torrent.ratio, self.value)


@register_condition(validator="expr")
class ExprCondition(BaseCondition):
    """表达式条件: 一行表达式, 自由组合种子字段与额外值(当前时间 / 盘空间 / 全局计数…)

    与旧条件**并存**: 旧条件行为不变, 本条件只是新增的一种写法(对照表见计划第 08 节)。
    编译期解析 + 语义校验(名字/函数/参数/类型/结果必须是布尔), 运行期纯读取求值;
    求值出错抛 ExprError, 由 Rule.process 兜成「本条规则本轮跳过, 不影响其它规则」(见 base.py)。
    """
    name = "expr"

    def __init__(self, spec: Any) -> None:
        self.text = str(spec)
        self.expr = compile_expr(self.text)
        validate(self.expr.root)

    def match(self, ctx: RuleContext) -> bool:
        value = evaluate(self.expr.root, ctx)
        if not isinstance(value, bool):  # 静态校验已挡, 运行期兜底(防止取值面类型与实际不一致)
            raise ExprError(f"条件表达式的结果必须是布尔, 得到 {type(value).__name__}: {self.text}")
        return value

    def __repr__(self) -> str:
        return f"ExprCondition({self.text})"


@register_condition
class FreespaceCondition(BaseCondition):
    """磁盘可用空间条件: path + amount, 如 {path: 'R:\\', amount: '<100GiB'}"""
    name = "freespace"

    def __init__(self, spec: Any) -> None:
        self.path = str(spec.get("path", ""))
        self.op, self.value = utils.parse_compare(str(spec.get("amount", "")), utils.parse_fsize)

    def match(self, ctx: RuleContext) -> bool:
        if not self.path:
            return False
        # 与 disk_* 表达式同口径(单点 disk_usage_value): 映射 miss / 盘不可读都显式报错,
        # 绝不降级成假值(拍板 P-07); ExprError 由 Rule.process 兜成「本条规则本轮跳过, 不影响其它规则」
        free = disk_usage_value(self.path, "free")
        return utils.compare(self.op, free, self.value)
