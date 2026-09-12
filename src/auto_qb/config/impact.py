"""配置变更影响分析: 递归 diff 新旧配置并判定每项变更的热重载级别

级别模型(热重载分层应用, 见 ai/03 与计划):
- L0 即时生效: 运行时每轮/每次执行时动态读取, 替换 Config 对象字段即生效
  (main_tick/max_tasks_per_tick/remove_similar_tags/skip_checking_tag/grouping.*/add_episode_tags.*/)
- L1 轻量应用: 需毫秒级副动作(logging 重挂/通知 handler 重挂/qbittorrent 重连/web 重启)
- L2 结构重建: 读取时机在创建/绑定时固化(规则/任务/tracker 匹配), 需重建任务队列与规则
  并对全部记录重匹配 tracker(store 记录/分组/执行历史保留)
- R 重启进程: 进程身份/路径派生类(state_file/data_dir), 热重载拒绝该项

分级用表驱动: 未列出的配置项默认 L2(保守——重建保证生效); 显式声明的 L0/L1 为
"运行时动态读取"的例外白名单(新增配置项时按读取时机补表)。
"""
import ctypes
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

LEVEL_R = "R"
LEVEL_L2 = "L2"
LEVEL_L1 = "L1"
LEVEL_L0 = "L0"

# 顶层配置项级别表(未列出 = L2 保守重建)
SECTION_LEVELS = {
    # L0: 运行时动态读取
    "main_tick": LEVEL_L0,
    "max_tasks_per_tick": LEVEL_L0,
    "remove_similar_tags": LEVEL_L0,
    "skip_checking_tag": LEVEL_L0,
    "grouping": LEVEL_L0,
    "add_episode_tags": LEVEL_L0,
    # L1: 轻量应用
    "logging": LEVEL_L1,
    "notify": LEVEL_L1,
    "qbittorrent": LEVEL_L1,
    "web": LEVEL_L1,
    # L2: 结构重建
    "interval": LEVEL_L2,
    "rules_config": LEVEL_L2,
    "delete_tags": LEVEL_L2,
    "delete_tags_if_has_no_torrents": LEVEL_L2,
    "global_speed_limit_curve": LEVEL_L2,
    # R: 进程身份
    "state_file": LEVEL_R,
    "data_dir": LEVEL_R,
    # trackers: 特殊处理(字段级), 见 _tracker_field_level
    "trackers": None,
}

# trackers.X.<field> 字段级别(tags/移除/限速/hr 运行时动态读; domains/rules 绑定固化)
TRACKER_FIELD_LEVELS = {
    "tags": LEVEL_L0,
    "remove_tags": LEVEL_L0,
    "remove_similar_tags": LEVEL_L0,
    "upload_speed_limit": LEVEL_L0,
    "download_speed_limit": LEVEL_L0,
    "hr": LEVEL_L0,
    "domains": LEVEL_L2,
    "rules": LEVEL_L2,
}


@dataclass
class ConfigChange:
    """一项配置变更: 字段路径 + 热重载级别 + 新旧值"""

    path: str
    level: str
    old: Any
    new: Any


def _diff_flat(old: Any, new: Any, prefix: str, changes: List[ConfigChange], level: str) -> None:
    """对齐两个 mapping 的键做逐字段 diff(仅比较两侧均存在的嵌套, 其余按整体)"""
    for name in sorted(set(old) | set(new)):
        path = f"{prefix}.{name}"
        old_v, new_v = old.get(name), new.get(name)
        if old_v == new_v:
            continue
        if isinstance(old_v, dict) and isinstance(new_v, dict):
            _diff_flat(old_v, new_v, path, changes, level)
        else:
            changes.append(ConfigChange(path, level, old_v, new_v))


def _diff_trackers(old_t: dict, new_t: dict, changes: List[ConfigChange]) -> None:
    """trackers 段: tracker 增删为 L2; 同名 tracker 逐字段按 TRACKER_FIELD_LEVELS"""
    for name in sorted(set(old_t) | set(new_t)):
        path = f"trackers.{name}"
        old_conf, new_conf = old_t.get(name), new_t.get(name)
        if old_conf is None or new_conf is None:
            changes.append(ConfigChange(path, LEVEL_L2, old_conf, new_conf))
            continue
        if old_conf == new_conf:
            continue
        old_d, new_d = vars(old_conf), vars(new_conf)
        for fname in sorted(set(old_d) | set(new_d)):
            if old_d.get(fname) == new_d.get(fname):
                continue
            level = TRACKER_FIELD_LEVELS.get(fname, LEVEL_L2)
            changes.append(ConfigChange(f"{path}.{fname}", level, old_d.get(fname), new_d.get(fname)))


def _flatten_config(config: Any) -> dict:
    """Config(普通类) -> {段名: 值} 的浅层字典(嵌套 dataclass 保持对象, 由级别表处理)"""
    return {name: getattr(config, name) for name in vars(config)}


def diff_config_impacts(old: Any, new: Any) -> List[ConfigChange]:
    """递归 diff 新旧配置, 返回变更列表(含热重载级别), 按路径排序

    嵌套结构(trackers dict of dataclass / 普通段 dataclass)按级别表展开到字段级;
    未在级别表中声明的项默认 L2(保守: 重建保证生效)。
    """
    changes: List[ConfigChange] = []
    old_d, new_d = _flatten_config(old), _flatten_config(new)
    for name in sorted(set(old_d) | set(new_d)):
        old_v, new_v = old_d.get(name), new_d.get(name)
        if old_v == new_v:
            continue
        if name == "trackers":
            old_t = old_v if isinstance(old_v, dict) else {}
            new_t = new_v if isinstance(new_v, dict) else {}
            _diff_trackers(old_t, new_t, changes)
            continue
        level = SECTION_LEVELS.get(name, LEVEL_L2)
        if isinstance(old_v, dict) and isinstance(new_v, dict) and level == LEVEL_L0:
            # L0 段(grouping 等)内字段级 diff, 仅变更字段计入级别
            _diff_flat(old_v, new_v, name, changes, level)
        else:
            changes.append(ConfigChange(name, level, old_v, new_v))
    changes.sort(key=lambda c: c.path)
    return changes


def max_level(changes: List[ConfigChange]) -> str:
    """变更列表中的最高影响级别(无变更返回 L0)"""
    order = {LEVEL_L0: 0, LEVEL_L1: 1, LEVEL_L2: 2, LEVEL_R: 3}
    return max((c.level for c in changes), key=lambda lv: order.get(lv, 99), default=LEVEL_L0)


def restart_required_paths(changes: List[ConfigChange]) -> List[str]:
    return [c.path for c in changes if c.level == LEVEL_R]
