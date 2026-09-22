"""表达式取值面(env): 名字 -> 取值器 + 静态类型 + 昂贵标记; 函数表; 语义静态校验

**单一事实源**: schema 暴露、前端提示、文档生成、静态校验都从 NAME_TABLE / FUNC_TABLE 派生,
不在别处再写一份名字清单。

名字可用性三态(见计划第 04 节):
- **恒定可用** —— 配置期只校验名字存在: tor.* / tracker.* / sys 的时间与计数 / 全部函数
- **运行期不可用** —— 数据源当时拿不到, getter 直接抛 ExprError, 由「出错即停规则」兜住。
  ⚠ **绝不降级成假值**: `sys.dl_speed` 拿不到就是报错, **不返回 0** —— 返回 0 会让
  「全局速度低于阈值」在数据源失效时**静默成真**, 进而批量触发限速/停止动作
- **「值不存在」≠「求值出错」** —— 未匹配站点 `tracker.name` = "Unknown"、无 HR 配置
  `tor.hr_condition_met` = false, 都是有定义的缺省, 正常参与求值, 不报错不停规则

昂贵标记(expensive): 有系统调用 / API 调用 / 遍历全库的取值, 求值侧按 ctx 缓存(见 eval.py),
并靠 and/or 短路避免无谓调用。时间类名字也标昂贵 —— 缓存后同一规则执行内时间一致。
"""
import os
import shutil
from dataclasses import dataclass, fields as dc_fields
from datetime import datetime
from typing import Any, Callable, Dict, Tuple

from ... import curves
from ...infra import utils
from ...torrents import TorrentRecord
from ...torrents.compat import _SNAPSHOT_FIELDS
from .errors import ExprError, ExprSyntaxError
from .parser import Binary, Call, ListLit, Lit, Name, Unary
from .types import (
    ANY,
    BOOL,
    LIST,
    NUM,
    STR,
    check_op_types,
    check_unary_types,
    label,
    result_type,
    type_name,
)

_SNAPSHOT_SET = frozenset(_SNAPSHOT_FIELDS)
_PY_KIND = {"str": STR, "int": NUM, "float": NUM, "bool": BOOL}

# 状态类别属性(与 qB TorrentState 语义一致, 取代旧 state 条件)
_STATE_ATTRS = ("is_downloading", "is_uploading", "is_complete", "is_checking", "is_stopped", "is_paused", "is_errored")


@dataclass(frozen=True)
class NameInfo:
    """一个可取值的名字

    type:      静态类型(num/bool/str/list/any), 供编译期类型检查
    getter:    ctx(RuleContext) -> 值; 数据源不可用时抛 ExprError
    expensive: 有 I/O / API / 全库遍历, 或需要同轮一致的时变值(时间) —— 求值侧按 ctx 缓存
    """

    name: str
    type: str
    getter: Callable[[Any], Any]
    expensive: bool = False
    help: str = ""


@dataclass(frozen=True)
class FuncInfo:
    """一个白名单函数

    arity:     允许的参数个数
    arg_types: 各参数位置的静态类型(ANY = 不检查)
    call:      (ctx, args已求值的 tuple) -> 值
    """

    name: str
    type: str
    arity: Tuple[int, ...]
    arg_types: Tuple[str, ...]
    call: Callable[[Any, tuple], Any]
    expensive: bool = False
    help: str = ""


# ---------- 取值器 ----------


def _attr(name: str):
    def get(ctx):
        return getattr(ctx.torrent, name)

    return get


def _state(attr: str):
    def get(ctx):
        enum = ctx.torrent.state_enum
        return bool(getattr(enum, attr, False)) if enum is not None else False

    return get


def _hr(method: str):
    """HR 判定: 无 tracker_conf 或无 HR 配置 -> false(有定义的缺省, 不是错误)"""
    def get(ctx):
        tor = ctx.torrent
        if tor.tracker_conf is None or not tor.tracker_conf.hr:
            return False
        return bool(getattr(tor, method)())

    return get


def _upload_delta(kind: str):
    def get(ctx):
        return ctx.manager.upload_delta(ctx.torrent, kind)

    return get


def _age(ctx):
    return datetime.now().timestamp() - (ctx.torrent.added_on or 0)


def _idle(ctx):
    """距上次活动秒数; last_activity = -1(从未传输)按无穷大处理 —— 从未活动即无限久"""
    last = ctx.torrent.last_activity
    if last is None or last < 0:
        return float("inf")
    return datetime.now().timestamp() - last


def _server_state(ctx) -> dict:
    """qB 全局状态; 未同步即不可用(报错, 不返回假值)"""
    store = getattr(ctx.manager, "store", None)
    ss = getattr(store, "server_state", None) if store is not None else None
    if not isinstance(ss, dict) or not ss:
        raise ExprError("数据源不可用: qB 全局状态(server_state)尚未同步, 该值当前不能用于判断")
    return ss


def _server_value(key: str, kind: str):
    def get(ctx):
        ss = _server_state(ctx)
        if key not in ss:
            raise ExprError(f"数据源缺失字段: qB 全局状态(server_state)没有 '{key}'")
        value = ss[key]
        if kind is BOOL:
            return bool(value)
        return value

    return get


def _count(pred=None):
    """全局种子计数; 带谓词的需要遍历全库 -> 昂贵(按 ctx 缓存)"""
    def get(ctx):
        records = list(ctx.manager.store.by_hash.values())
        if pred is None:
            return len(records)
        return sum(1 for t in records if pred(t))

    return get


def _pred_state(attr: str):
    def pred(rec) -> bool:
        enum = getattr(rec, "state_enum", None)
        return bool(getattr(enum, attr, False)) if enum is not None else False

    return pred


def _tracker_names(ctx):
    """该种子所有 tracker URL 命中的站点配置名集合(一拖多站的种子用这个)"""
    tor = ctx.torrent
    confs = utils.match_tracker_confs(ctx.config.trackers, tor.tracker_urls(ctx.client))
    return frozenset(c.name for c in confs)


def _traffic(period: str, index: int):
    """全局流量口径(数据源 = Traffic Monitor 的 history_traffic.dat)

    ⚠ 未配置数据源 -> 报错(该名字被禁用), **不返回 0**: 返回 0 会让「今日上传已达标」
    这类条件在没配数据源时静默成假、在配了但文件不可读时同样失真, 两头都不可接受。
    读文件是 I/O -> 标昂贵(按 ctx 缓存), 建议只在低频规则里用。
    """
    def get(ctx):
        conf = getattr(ctx.config, "global_speed_limit_curve", None)
        dat_path = getattr(conf, "dat_path", "") if conf is not None else ""
        if not dat_path or not getattr(conf, "enabled", True):
            raise ExprError(
                "数据源未配置: 该值需要配置 global_speed_limit_curve.traffic_source"
                "(Traffic Monitor 的 history_traffic.dat)"
            )
        try:
            with open(dat_path, "r", encoding="utf-8", errors="replace") as f:
                rows, _bad = curves.parse_history_dat(f.read())
        except OSError as e:
            raise ExprError(f"数据源不可读: '{dat_path}': {e}") from e
        return curves.aggregate(rows, period)[index]

    return get


def _freespace(ctx, args):
    path = str(args[0])
    try:
        return shutil.disk_usage(path).free
    except (OSError, ValueError) as e:
        raise ExprError(f"磁盘不可用: '{path}': {e}") from e


def _disk_total(ctx, args):
    path = str(args[0])
    try:
        return shutil.disk_usage(path).total
    except (OSError, ValueError) as e:
        raise ExprError(f"磁盘不可用: '{path}': {e}") from e


def _disk_used(ctx, args):
    path = str(args[0])
    try:
        return shutil.disk_usage(path).used
    except (OSError, ValueError) as e:
        raise ExprError(f"磁盘不可用: '{path}': {e}") from e


def _exists(ctx, args):
    return os.path.exists(str(args[0]))


def _file_count(ctx, args):
    return len(ctx.torrent.files(ctx.client))


def _raw(ctx, args):
    """读前向兼容字段(_raw / 未声明字段); 字段不存在 -> 报错(不静默给 0)"""
    name = str(args[0])
    try:
        return getattr(ctx.torrent, name)
    except AttributeError as e:
        raise ExprError(f"种子上没有字段 '{name}'") from e


def _len_of(ctx, args):
    value = args[0]
    try:
        return len(value)
    except TypeError as e:
        raise ExprError(f"'len' 的参数不可计长: {label(type_name(value))}") from e


def _num_unary(fn):
    def call(ctx, args):
        value = args[0]
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ExprError(f"该函数的参数必须是数值, 得到 {label(type_name(value))}")
        return fn(value)

    return call


def _min_max(fn):
    def call(ctx, args):
        for a in args:
            if not isinstance(a, (int, float)) or isinstance(a, bool):
                raise ExprError(f"该函数的参数必须是数值, 得到 {label(type_name(a))}")
        return fn(args)

    return call


# ---------- 名字表 ----------


def _ann_name(t) -> str:
    return t if isinstance(t, str) else getattr(t, "__name__", "")


def _build_name_table() -> Dict[str, NameInfo]:
    table: Dict[str, NameInfo] = {}

    # A. 种子快照字段(70 个, 类型从 TorrentRecord 注解派生, 与 qB 字段同名)
    for f in dc_fields(TorrentRecord):
        if f.name not in _SNAPSHOT_SET or f.name == "tags":
            continue
        kind = _PY_KIND.get(_ann_name(f.type))
        if kind is None:
            continue
        table["tor." + f.name] = NameInfo("tor." + f.name, kind, _attr(f.name))

    # tor.tags 取集合(供 in 与"任一元素命中"的 ~), 原始逗号串另给 tags_raw
    table["tor.tags"] = NameInfo("tor.tags", LIST, lambda ctx: ctx.torrent.tags_set)
    table["tor.tags_raw"] = NameInfo("tor.tags_raw", STR, _attr("tags"))

    # B. 派生值
    for attr in _STATE_ATTRS:
        table["tor." + attr] = NameInfo("tor." + attr, BOOL, _state(attr))
    table["tor.progress_pct"] = NameInfo("tor.progress_pct", NUM, lambda ctx: ctx.torrent.progress * 100)
    table["tor.tags_count"] = NameInfo("tor.tags_count", NUM, lambda ctx: len(ctx.torrent.tags_set))
    table["tor.hr_condition_met"] = NameInfo("tor.hr_condition_met", BOOL, _hr("check_hr_condition"))
    table["tor.hr_satisfied"] = NameInfo("tor.hr_satisfied", BOOL, _hr("check_hr_satisfied"))
    for suffix, kind in (("today", "daily"), ("week", "weekly"), ("month", "monthly")):
        table[f"tor.upload_{suffix}"] = NameInfo(f"tor.upload_{suffix}", NUM, _upload_delta(kind))
    table["tor.age"] = NameInfo("tor.age", NUM, _age)
    table["tor.idle"] = NameInfo("tor.idle", NUM, _idle)

    # C. 站点配置(主站点 = TorrentRecord.tracker_conf, 见计划第 04 节 C)
    table["tracker.name"] = NameInfo(
        "tracker.name",
        STR,
        lambda ctx: ctx.torrent.tracker_conf.name if ctx.torrent.tracker_conf is not None else "Unknown",
        help="主站点配置名; 未匹配站点 = Unknown"
    )
    table["tracker.groups"] = NameInfo(
        "tracker.groups",
        LIST,
        lambda ctx: list(ctx.torrent.tracker_conf.groups) if ctx.torrent.tracker_conf is not None else [],
        help="主站点声明的分组; 未匹配站点 = 空列表"
    )
    table["tracker.names"] = NameInfo(
        "tracker.names", LIST, _tracker_names, expensive=True, help="该种子所有 tracker URL 命中的站点名集合"
    )
    table["tracker.url"] = NameInfo("tracker.url", STR, _attr("tracker"))

    # D. 环境与全局(时间类标昂贵 -> 同一规则执行内取值一致)
    table["sys.now"] = NameInfo("sys.now", NUM, lambda ctx: datetime.now().timestamp(), expensive=True)
    table["sys.hour"] = NameInfo("sys.hour", NUM, lambda ctx: datetime.now().hour, expensive=True)
    table["sys.minute"] = NameInfo("sys.minute", NUM, lambda ctx: datetime.now().minute, expensive=True)
    table["sys.time_of_day"] = NameInfo(
        "sys.time_of_day", NUM, lambda ctx: datetime.now().hour * 60 + datetime.now().minute, expensive=True
    )
    table["sys.dow"] = NameInfo("sys.dow", NUM, lambda ctx: datetime.now().isoweekday(), expensive=True)
    table["sys.dom"] = NameInfo("sys.dom", NUM, lambda ctx: datetime.now().day, expensive=True)
    table["sys.torrent_count"] = NameInfo("sys.torrent_count", NUM, _count())
    table["sys.downloading_count"] = NameInfo(
        "sys.downloading_count", NUM, _count(_pred_state("is_downloading")), expensive=True
    )
    table["sys.seeding_count"] = NameInfo("sys.seeding_count", NUM, _count(_pred_state("is_uploading")), expensive=True)
    # 全局流量: 依赖配置的数据源(见 GATED_NAMES, 配置期即禁用)
    table["sys.upload_today"] = NameInfo(
        "sys.upload_today", NUM, _traffic("day", 0), expensive=True, help="全局今日上传(需 traffic_source)"
    )
    table["sys.download_today"] = NameInfo(
        "sys.download_today", NUM, _traffic("day", 1), expensive=True, help="全局今日下载(需 traffic_source)"
    )
    table["sys.upload_month"] = NameInfo(
        "sys.upload_month", NUM, _traffic("month", 0), expensive=True, help="全局本月上传(需 traffic_source)"
    )
    # 依赖 qB server_state: 未同步即不可用(报错, 不返回假 0)
    for name, key, kind in (
        ("sys.dl_speed", "dl_info_speed", NUM),
        ("sys.up_speed", "up_info_speed", NUM),
        ("sys.dl_limit", "dl_rate_limit", NUM),
        ("sys.up_limit", "up_rate_limit", NUM),
        ("sys.alt_speed_on", "use_alt_speed_limits", BOOL),
    ):
        table[name] = NameInfo(name, kind, _server_value(key, kind), help="数据源: qB 全局状态 server_state")
    return table


def _build_func_table() -> Dict[str, FuncInfo]:
    return {
        "freespace": FuncInfo("freespace", NUM, (1, ), (STR, ), _freespace, expensive=True, help="该路径所在盘剩余字节"),
        "disk_total": FuncInfo("disk_total", NUM, (1, ), (STR, ), _disk_total, expensive=True, help="该路径所在盘总容量"),
        "disk_used": FuncInfo("disk_used", NUM, (1, ), (STR, ), _disk_used, expensive=True, help="该路径所在盘已用字节"),
        "exists": FuncInfo("exists", BOOL, (1, ), (STR, ), _exists, expensive=True, help="路径是否存在"),
        "file_count": FuncInfo("file_count", NUM, (0, ), (), _file_count, expensive=True, help="种子文件数(需拉文件列表)"),
        "raw": FuncInfo("raw", ANY, (1, ), (STR, ), _raw, help="读前向兼容字段, 仅用于 qB 新字段"),
        "len": FuncInfo("len", NUM, (1, ), (ANY, ), _len_of),
        "abs": FuncInfo("abs", NUM, (1, ), (NUM, ), _num_unary(abs)),
        "round": FuncInfo("round", NUM, (1, ), (NUM, ), _num_unary(round)),
        "min": FuncInfo("min", NUM, (2, ), (NUM, NUM), _min_max(min)),
        "max": FuncInfo("max", NUM, (2, ), (NUM, NUM), _min_max(max)),
        "days": FuncInfo("days", NUM, (1, ), (NUM, ), _num_unary(lambda n: n * 86400)),
        "hours": FuncInfo("hours", NUM, (1, ), (NUM, ), _num_unary(lambda n: n * 3600)),
    }


NAME_TABLE: Dict[str, NameInfo] = _build_name_table()
FUNC_TABLE: Dict[str, FuncInfo] = _build_func_table()

# ---------- 语义静态校验(配置期) ----------


def static_type(node) -> str:
    """推导节点的静态类型, 顺带做名字/函数/参数/类型的静态检查(失败抛 ExprSyntaxError)"""
    if isinstance(node, Lit):
        return type_name(node.value)
    if isinstance(node, Name):
        info = NAME_TABLE.get(node.name)
        if info is None:
            raise ExprSyntaxError(f"未知取值 '{node.name}'", node.pos)
        return info.type
    if isinstance(node, Call):
        info = FUNC_TABLE.get(node.name)
        if info is None:
            raise ExprSyntaxError(f"未知函数 '{node.name}'", node.pos)
        if len(node.args) not in info.arity:
            want = "/".join(str(a) for a in info.arity)
            raise ExprSyntaxError(f"函数 '{node.name}' 参数个数应为 {want}, 得到 {len(node.args)}", node.pos)
        for arg, want in zip(node.args, info.arg_types):
            got = static_type(arg)
            if want != ANY and got not in (want, ANY):
                raise ExprSyntaxError(
                    f"函数 '{node.name}' 的参数类型应为 {label(want)}, 得到 {label(got)}",
                    arg.pos if isinstance(arg, (Name, Call)) else None
                )
        return info.type
    if isinstance(node, ListLit):
        for item in node.items:
            static_type(item)
        return LIST
    if isinstance(node, Unary):
        check_unary_types(node.op, static_type(node.operand))
        return result_type(node.op)
    if isinstance(node, Binary):
        left = static_type(node.left)
        right = static_type(node.right)
        check_op_types(node.op, left, right)
        return result_type(node.op)
    return ANY


def validate(node) -> None:
    """语义校验(配置期): 名字/函数/参数/类型 + **顶层结果必须是布尔**"""
    kind = static_type(node)
    if kind != BOOL:
        raise ExprSyntaxError(f"条件表达式的结果必须是布尔, 得到 {label(kind)}")


# ---------- 数据源门控(配置期禁用) ----------

# 需要"配置了数据源"才可用的名字: 没配 = 该名字禁用(配置期即拒绝, 见 config/validation/rules.py)
GATED_NAMES = frozenset({"sys.upload_today", "sys.download_today", "sys.upload_month"})


def used_names(node) -> set:
    """AST 中用到的取值名(供数据源门控与文档生成)"""
    found = set()
    if isinstance(node, Name):
        found.add(node.name)
    elif isinstance(node, Unary):
        found |= used_names(node.operand)
    elif isinstance(node, Binary):
        found |= used_names(node.left) | used_names(node.right)
    elif isinstance(node, Call):
        for arg in node.args:
            found |= used_names(arg)
    elif isinstance(node, ListLit):
        for item in node.items:
            found |= used_names(item)
    return found


def gated_names_in(node) -> list:
    """AST 里用到、但当前配置无数据源的名字(空 = 无问题)"""
    return sorted(used_names(node) & GATED_NAMES)
