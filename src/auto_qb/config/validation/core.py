"""validation 核心: 通用校验助手 + validate_config 入口(各段校验器延迟导入防环)"""
import re
from typing import List

from ...utils import MatchPattern, parse_bool, parse_time

# config 顶层已知键
KNOWN_CONFIG_KEYS = {
    "qbittorrent",
    "main_tick",
    "sync_interval",
    "state_save_interval",
    "max_tasks_per_tick",
    "interval",
    "data_dir",
    "state_file",
    "log",
    "remove_similar_tags",
    "add_episode_tags",
    "hr",
    "skip_checking_tag",
    "delete_tags",
    "delete_tags_if_has_no_torrents",
    "grouping",
    "notify",
    "web",
    "trackers",
    "global_speed_limit_curve",
}


def _strip_none(value):
    """递归剔除空值(None/空串): 显式留空的键/列表项视为未配置(走默认值)

    yaml.BaseLoader 将 `key:` 留空解析为 ''(而非 None), 与显式 "" 无法区分, 统一视为未配置;
    默认值本为空串的键(如 hr.add_tag)行为不变。
    """
    if isinstance(value, dict):
        return {k: _strip_none(v) for k, v in value.items() if v is not None and v != ""}
    if isinstance(value, list):
        return [_strip_none(v) for v in value if v is not None and v != ""]
    return value


def _check_unknown_keys(spec: dict, known: set, where: str, errors: List[str]) -> None:
    unknown = set(spec) - set(known)
    if unknown:
        errors.append(f"{where}: 未知键 {sorted(unknown)}, 可用键: {sorted(known)}")


def _try(parse_fn, value, where: str, errors: List[str]) -> None:
    """用解析函数校验值格式(复用 utils.parse_* 单一事实来源), 失败记录错误"""
    try:
        parse_fn(value)
    except ValueError as e:
        errors.append(f"{where}: {e}")


def _try_time(value, where: str, errors: List[str], positive: bool = False) -> None:
    """时间格式校验; positive=True 时要求 > 0(如 main_tick, 防止 0 忙循环)"""
    try:
        seconds = parse_time(value)
    except ValueError as e:
        errors.append(f"{where}: {e}")
        return
    if positive and seconds <= 0:
        errors.append(f"{where}: 必须为正时间: {value}")


# state_save_interval 下限: 状态的真实变更频率是小时~天级, 更激进的间隔只会白白放大磁盘
# 写入, 换不来等比例的有效丢失窗口(issue 26-09-21-1347 拍板: 防误配置写放大)。0 = 关闭
# 周期落盘, 不受限。
STATE_SAVE_INTERVAL_MIN = 30.0


def _validate_state_save_interval(value, errors: List[str]) -> None:
    """state_save_interval: 合法时间格式, 且为 0(=关闭)或 >= 30s(防误配置写放大)"""
    where = "config.state_save_interval"
    try:
        seconds = parse_time(value)
    except ValueError as e:
        errors.append(f"{where}: {e}")
        return
    if seconds != 0 and seconds < STATE_SAVE_INTERVAL_MIN:
        errors.append(f"{where}: 须为 0(关闭)或 >= {STATE_SAVE_INTERVAL_MIN:g}S(防误配置写放大): {value}")


def _check_str_list(value, where: str, errors: List[str]) -> bool:
    """值必须是字符串列表(空列表合法); 返回是否通过"""
    if not isinstance(value, list):
        errors.append(f"{where}: 必须是列表")
        return False
    bad = [i for i, v in enumerate(value) if not isinstance(v, str) or not v.strip()]
    if bad:
        errors.append(f"{where}: 第 {bad} 项必须是非空字符串")
        return False
    return True


def _check_regex_patterns(patterns: list, where: str, errors: List[str]) -> None:
    """regex: 前缀模式须可编译(经 MatchPattern 解析出主体与 ignore_case 标志后编译, 与运行时一致;
    否则运行时会静默跳过匹配, 错误被掩盖)"""
    for i, pat in enumerate(patterns):
        if isinstance(pat, str) and pat.startswith("regex:"):
            try:
                MatchPattern.parse(pat).compile()
            except re.error as e:
                errors.append(f"{where}[{i}]: 非法正则: {e}")


def validate_config(data) -> List[str]:
    """全量校验配置(结构/未知键/必填项/值格式), 返回错误列表(空 = 通过)

    - 顶层仅允许 config 键; 各段未知键一律报错(含 tracker/HR/规则 spec)
    - 必填项: tracker 的 domains、站点 hr 的 required_seeding_time; 其余键有默认值可留空
    - 值格式复用 utils.parse_*; 规则集 spec 连同条件/动作名称一并校验
    - global_speed_limit_curve 由 _validate_global_speed_limit_curve 校验(结构最复杂)
    """
    # 各段校验器延迟导入: sections/rules/curves 均反向依赖本模块的通用助手,
    # 顶层导入会形成 core->sections->rules->core 循环(与 registry 延迟导入同模式)
    from .curves import _validate_global_speed_limit_curve
    from .rules import _validate_rules
    from .sections import (
        _validate_add_episode_tags,
        _validate_global_hr,
        _validate_grouping,
        _validate_log,
        _validate_notify,
        _validate_qbittorrent,
        _validate_tag_lists,
        _validate_trackers,
        _validate_web,
    )
    errors: List[str] = []
    if not isinstance(data, dict):
        errors.append("配置文件为空或根节点不是字典")
        return errors
    _check_unknown_keys(data, {"config"}, "根节点", errors)
    cfg = data.get("config")
    if cfg is None:
        return errors  # 空配置: 全部使用默认值
    if not isinstance(cfg, dict):
        errors.append("config: 必须是字典")
        return errors

    # ---- config 顶层 ----
    rules_config = {k: v for k, v in cfg.items() if k.endswith("_rules")}
    _check_unknown_keys(cfg, KNOWN_CONFIG_KEYS | set(rules_config), "config", errors)
    if "main_tick" in cfg:
        _try_time(cfg["main_tick"], "config.main_tick", errors, positive=True)
    if "sync_interval" in cfg:
        _try_time(cfg["sync_interval"], "config.sync_interval", errors, positive=True)
    if "state_save_interval" in cfg:
        _validate_state_save_interval(cfg["state_save_interval"], errors)
    if "max_tasks_per_tick" in cfg:
        _try(int, cfg["max_tasks_per_tick"], "config.max_tasks_per_tick(须为整数)", errors)
        # 范围必须显式校验: TaskQueue._pop_due 把 `max_tasks <= 0` 当作"不限量"(内部语义),
        # 若配置放行 0/负值, "每轮最多执行 N 个任务"就变成**一轮弹出全部到期任务** —— 与配置
        # 语义完全相反(单 tick 可能执行上千任务 ⇒ 卡顿 + API 风暴)。schema 声明的 min=1
        # 只作用于前端控件, 不进校验, 故这里必须补。
        try:
            if int(cfg["max_tasks_per_tick"]) < 1:
                errors.append("config.max_tasks_per_tick: 须 >= 1")
        except (TypeError, ValueError):
            pass  # 格式错误已由上面的 _try 记录, 不重复报错
    if "interval" in cfg:
        _try_time(cfg["interval"], "config.interval", errors)
    if "state_file" in cfg and not str(cfg["state_file"]).strip():
        errors.append("config.state_file: 不能为空")
    if "remove_similar_tags" in cfg:
        _try(parse_bool, cfg["remove_similar_tags"], "config.remove_similar_tags", errors)
    if "add_episode_tags" in cfg:
        _validate_add_episode_tags(cfg["add_episode_tags"], errors)

    _validate_log(cfg.get("log"), errors)
    _validate_qbittorrent(cfg.get("qbittorrent"), errors)
    _validate_global_hr(cfg.get("hr"), errors)
    _validate_grouping(cfg.get("grouping"), errors)
    _validate_notify(cfg.get("notify"), errors)
    _validate_web(cfg.get("web"), errors)
    _validate_tag_lists(cfg, errors)
    _validate_trackers(cfg.get("trackers"), rules_config, errors)
    # data(=cfg) 传给规则校验: expr 条件的"数据源门控"要看全局配置(如 traffic_source 有没有配)
    _validate_rules(rules_config, errors, cfg)

    gslc = cfg.get("global_speed_limit_curve")
    if gslc is not None:
        _validate_global_speed_limit_curve(gslc, errors)
    return errors
